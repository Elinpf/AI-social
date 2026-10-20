#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D5 LLM-as-judge 评测器（线程级抽样 + 原始输入输出落盘 + 一致性检查）。

协议（见 D5-评测方法.md §judge）：
- 抽样单位 = **线程**（非消息）；`|T|>=2` 优先，按 seed 确定性抽样；
- 每线程取「首条 + 随机 2 条」（线程 ≤3 条则全取）；
- temperature=0.0；同一批**重复 R 次**，报 exact agreement / Cohen's κ / Spearman ρ；
- 原始 system/user/output/prompt_hash 经 `freeze.capture.PromptCapture` 落盘（脱敏硬门）；
- 只评质量维度，不替代客观指标，也不替代原文样本。

用法：
    set -a; . code/.env.local; set +a
    python3 artifacts/code/dialogue_judge.py \
        --log v2/evidence/run_d2_before_n12_seed42/run.jsonl \
        --out-dir v2/evidence/judge_v0 \
        --n-threads 12 --repeat 2 --seed 20261020 --temperature 0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CODE = os.path.join(ROOT, "code")
sys.path.insert(0, CODE)

SCHEMA = "d5-judge/1.0"
DIMS = ["naturalness", "persona_fit", "specificity", "responsiveness", "flow"]
DIM_ZH = {
    "naturalness": "自然度",
    "persona_fit": "人设贴合",
    "specificity": "具体性",
    "responsiveness": "回应有效",
    "flow": "往复流畅",
}

SYSTEM_PROMPT = """你是「AI 小镇」对话质量评审员。你会看到一段居民之间的对话线程，按时间顺序排列，标注了说话人。
只评这段对话本身读起来是否像真人说话，不要评剧情设定、事件是否合理、角色是否做了该做的事。

请对 5 个维度各打一个 **1–7 的整数分**：
1. naturalness 自然度：像不像熟人之间随口说话。1=机械/书面/翻译腔/像模板；4=能读但明显是生成的；7=几乎像真人对话录音转写。
2. persona_fit 人设贴合：语气、用词、关心的事是否贴合说话人身份。1=换成谁都能说；4=部分贴合；7=明显只有这个角色会这么说。
3. specificity 具体性：是否有具体细节、情绪、处境。1=全是空泛客套；4=有一点细节；7=细节可感、有画面。
4. responsiveness 回应有效：每句是否在接上一句（回答/追问/反驳/共情/接梗），而不是各说各话。1=完全自说自话；4=部分接得上；7=环环相扣。
5. flow 往复流畅：整体是否像一段连续对话。1=碎片拼接；4=有来回但不连贯；7=一气呵成。

额外要求：
- `worst_line`：最不自然的一句，**原样摘录且不超过 40 字**（超出请截断到 40 字内，不要改写）。
- `reason`：扣分主因，**不超过 30 字**。
- 只输出一行 JSON，不要解释文字、不要 markdown 代码块、不要换行：
{"naturalness":n,"persona_fit":n,"specificity":n,"responsiveness":n,"flow":n,"worst_line":"...","reason":"..."}"""


# ---------------------------------------------------------------- 工具


def sha256_text(t: str) -> str:
    return "sha256:" + hashlib.sha256(t.encode("utf-8")).hexdigest()


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return "sha256:" + h.hexdigest()


def load_env_file(path: str) -> None:
    if not os.path.exists(path):
        return
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_personas() -> Dict[str, str]:
    p = os.path.join(CODE, "config", "personas.json")
    names = {}
    if os.path.exists(p):
        raw = json.load(open(p, encoding="utf-8"))
        items = raw.get("personas", raw) if isinstance(raw, dict) else raw
        for it in items:
            pid = it.get("persona_id") or it.get("id")
            dn = it.get("display_name") or it.get("name") or ""
            if pid:
                names[str(pid)] = dn.replace("青溪镇·", "").strip()
    return names


def load_messages(log_path: str) -> List[dict]:
    msgs = []
    for ln in open(log_path, encoding="utf-8"):
        ln = ln.strip()
        if not ln or '"MSG_' not in ln:
            continue
        r = json.loads(ln)
        if r.get("type") not in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
            continue
        p = r.get("payload") or {}
        msgs.append({
            "round": r.get("round"), "seq": r.get("seq"), "type": r.get("type"),
            "from": p.get("from") or r.get("actor"), "to": p.get("to"),
            "body": (p.get("body") or "").strip(),
            "day": p.get("day"), "slot": p.get("slot"), "place": p.get("place"),
            "thread_id": p.get("thread_id"), "msg_id": p.get("msg_id"),
            "turn_index": p.get("turn_index"),
        })
    msgs.sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                             m["seq"] if m["seq"] is not None else -1))
    return msgs


def group_threads(msgs: List[dict]) -> List[Tuple[str, List[dict]]]:
    th: Dict[str, List[dict]] = {}
    for m in msgs:
        if m.get("thread_id"):
            key = "T:" + str(m["thread_id"])
        else:
            pair = tuple(sorted({str(m["from"]), str(m["to"])}))
            key = "L:%s|%s|%s" % (m["day"], m["type"], "-".join(pair))
        th.setdefault(key, []).append(m)
    out = [(k, v) for k, v in th.items()]
    out.sort(key=lambda kv: kv[0])
    return out


def render_sample(thread_key: str, msgs: List[dict], names: Dict[str, str], rng: random.Random) -> Dict[str, Any]:
    take = msgs if len(msgs) <= 3 else [msgs[0]] + rng.sample(msgs[1:], 2)
    take = sorted({id(m): m for m in take}.values(), key=lambda m: (m["round"], m["seq"]))
    lines = []
    for m in take:
        spk = names.get(str(m["from"]), str(m["from"]))
        hear = names.get(str(m["to"]), str(m["to"])) if m["to"] else "（众人）"
        lines.append(f"[第{m['round']}回合 {m['slot'] or ''} {m['place'] or ''}] {spk} 对 {hear} 说：{m['body']}")
    user = ("下面是这段对话（共 %d 句，来自同一条对话线程）：\n\n" % len(take)) + "\n".join(lines)
    return {"thread_key": thread_key, "messages": take, "user": user,
            "transcript": "\n".join(lines)}


RE_JSON = re.compile(r"\{.*\}", re.S)
RE_FIELD = {k: re.compile(r'"%s"\s*:\s*(-?\d+)' % k) for k in DIMS}


def parse_judge(text: str) -> Optional[dict]:
    """先按 JSON 解析；截断/夹杂说明时退化为逐字段正则提取（结果标 parsed_by='regex'）。"""
    raw = text or ""
    m = RE_JSON.search(raw)
    d = None
    if m:
        try:
            d = json.loads(m.group(0))
        except Exception:
            d = None
    by = "json"
    if d is None:
        d = {}
        for k, rx in RE_FIELD.items():
            mm = rx.search(raw)
            if mm:
                d[k] = mm.group(1)
        if len(d) < len(DIMS):
            return None
        by = "regex"
        wl = re.search(r'"worst_line"\s*:\s*"([^"]*)"', raw)
        rs = re.search(r'"reason"\s*:\s*"([^"]*)"', raw)
        d["worst_line"] = wl.group(1) if wl else ""
        d["reason"] = rs.group(1) if rs else ""
    out = {}
    for k in DIMS:
        v = d.get(k)
        try:
            v = int(round(float(v)))
        except Exception:
            return None
        if not 1 <= v <= 7:
            return None
        out[k] = v
    out["worst_line"] = str(d.get("worst_line", ""))[:200]
    out["reason"] = str(d.get("reason", ""))[:200]
    out["parsed_by"] = by
    return out


def cohen_kappa(a: List[int], b: List[int], thr: int = 5) -> Optional[float]:
    ab = [(1 if x >= thr else 0, 1 if y >= thr else 0) for x, y in zip(a, b)]
    n = len(ab)
    if n == 0:
        return None
    pa = sum(1 for x, _ in ab if x) / n
    pb = sum(1 for _, y in ab if y) / n
    po = sum(1 for x, y in ab if x == y) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    if abs(1 - pe) < 1e-12:
        return None
    return round((po - pe) / (1 - pe), 6)


def spearman(a: List[float], b: List[float]) -> Optional[float]:
    n = len(a)
    if n < 3:
        return None

    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = sum((x - ma) ** 2 for x in ra) ** 0.5
    db = sum((y - mb) ** 2 for y in rb) ** 0.5
    if da == 0 or db == 0:
        return None
    return round(num / (da * db), 6)


def dist(vals: List[float]) -> Dict[str, Any]:
    if not vals:
        return {"n": 0}
    s = sorted(vals)
    def q(x):
        pos = (len(s) - 1) * x
        lo = int(pos); hi = min(lo + 1, len(s) - 1)
        return round(s[lo] + (s[hi] - s[lo]) * (pos - lo), 6)
    return {"n": len(s), "min": min(s), "p10": q(.1), "p50": q(.5), "p90": q(.9),
            "max": max(s), "mean": round(sum(s) / len(s), 6)}


# ---------------------------------------------------------------- 主流程


def build_provider(model: str):
    from freeze.providers import OpenAICompatProvider, MockProvider
    prov_kind = os.environ.get("HITT_LLM_PROVIDER", "").strip()
    llm_cfg = {}
    cfg_path = os.path.join(CODE, "config", "llm.json")
    if os.path.exists(cfg_path):
        llm_cfg = json.load(open(cfg_path, encoding="utf-8"))
    if prov_kind != "openai_compat":
        raise RuntimeError("HITT_LLM_PROVIDER 不是 openai_compat；judge 拒绝在 mock 上运行")
    endpoint = (os.environ.get("LLM_ENDPOINT") or llm_cfg.get("endpoint") or "").strip()
    key = os.environ.get("LLM_API_KEY", "").strip()
    if not endpoint or not key:
        raise RuntimeError("缺少 LLM_ENDPOINT / LLM_API_KEY（请 source code/.env.local）")
    return OpenAICompatProvider(endpoint, api_key=key, model=model, timeout=120, max_retries=2)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="D5 LLM-as-judge")
    ap.add_argument("--log", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--n-threads", type=int, default=24)
    ap.add_argument("--repeat", type=int, default=2)
    ap.add_argument("--seed", type=int, default=20261020)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--model", default="DeepSeek-Flash")
    ap.add_argument("--max-tokens", type=int, default=700)
    ap.add_argument("--thinking", type=int, default=0, help="0=关闭思考（默认，避免 reasoning 吃掉 max_tokens）")
    ap.add_argument("--round-range", default=None, help="固定 round 区间，如 0-83")
    ap.add_argument("--dry-run", action="store_true", help="只生成抽样与 prompt，不调用模型")
    args = ap.parse_args(argv)

    load_env_file(os.path.join(CODE, ".env.local"))
    names = load_personas()
    msgs = load_messages(args.log)
    if args.round_range:
        lo, hi = [int(x) for x in args.round_range.split("-")]
        msgs = [m for m in msgs if m["round"] is not None and lo <= m["round"] <= hi]

    threads = group_threads(msgs)
    multi = [t for t in threads if len(t[1]) >= 2]
    pool = multi if len(multi) >= args.n_threads else threads
    rng = random.Random(args.seed)
    picked_keys = sorted(pool, key=lambda kv: kv[0])
    picked = rng.sample(picked_keys, min(args.n_threads, len(picked_keys)))
    picked.sort(key=lambda kv: kv[0])

    samples = []
    for key, th in picked:
        s = render_sample(key, th, names, rng)
        s["sample_id"] = "S%03d" % (len(samples) + 1)
        samples.append(s)

    log_sha = sha256_file(args.log)
    os.makedirs(args.out_dir, exist_ok=True)
    plan = {
        "schema_version": SCHEMA,
        "protocol": {
            "sampling_unit": "thread", "n_threads": len(samples),
            "repeat": args.repeat, "seed": args.seed,
            "temperature": args.temperature, "model_requested": args.model,
            "max_tokens": args.max_tokens, "round_range": args.round_range,
            "dims": DIMS, "dim_zh": DIM_ZH,
            "system_prompt": SYSTEM_PROMPT,
            "system_prompt_sha256": sha256_text(SYSTEM_PROMPT),
            "pool_size": len(pool), "pool_multi_msg_threads": len(multi),
            "thread_pool_scheme": "multi|all",
        },
        "inputs": {"log": os.path.abspath(args.log), "log_sha256": log_sha,
                   "log_sha8": log_sha[7:15]},
        "samples": [{"sample_id": s["sample_id"], "thread_key": s["thread_key"],
                     "n_msgs": len(s["messages"]),
                     "msg_ids": [m.get("msg_id") for m in s["messages"]],
                     "rounds": [m["round"] for m in s["messages"]],
                     "user_prompt_sha256": sha256_text(s["user"]),
                     "transcript_sha256": sha256_text(s["transcript"])} for s in samples],
    }
    open(os.path.join(args.out_dir, "judge_plan.json"), "w", encoding="utf-8").write(
        json.dumps(plan, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    if args.dry_run:
        print(json.dumps({"dry_run": True, "n_samples": len(samples),
                          "out_dir": args.out_dir}, ensure_ascii=False, indent=1))
        return 0

    provider = build_provider(args.model)
    capture = None
    try:
        from freeze.capture import CaptureConfig, PromptCapture
        cfg = CaptureConfig(enabled=True, mode="purpose", purposes=frozenset({"judge"}),
                            compress=False,  # 不压缩：核验方要直接读 system/user 原文
                            dir=os.path.join(args.out_dir, "prompts"))
        capture = PromptCapture(cfg, root=args.out_dir)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] PromptCapture 不可用，回退自写 raw jsonl：{e}", file=sys.stderr)

    raw_path = os.path.join(args.out_dir, "judge_raw.jsonl")
    runs: List[Dict[str, Any]] = []
    with open(raw_path, "w", encoding="utf-8") as fraw:
        for rep in range(args.repeat):
            for s in samples:
                t0 = time.perf_counter()
                resp = provider.complete(system=SYSTEM_PROMPT, user=s["user"],
                                         model=args.model, temperature=args.temperature,
                                         max_tokens=args.max_tokens,
                                         extra={"thinking": bool(args.thinking)})
                dt = round(time.perf_counter() - t0, 3)
                parsed = parse_judge(resp.text)
                rec = {
                    "sample_id": s["sample_id"], "repeat": rep,
                    "thread_key": s["thread_key"],
                    "msg_ids": [m.get("msg_id") for m in s["messages"]],
                    "thread_input_sha256": sha256_text(s["transcript"]),
                    "source_log": os.path.abspath(args.log),
                    "source_log_sha256": log_sha,
                    "source_log_sha8": log_sha[7:15],
                    "system_sha256": sha256_text(SYSTEM_PROMPT),
                    "user_sha256": sha256_text(s["user"]),
                    "model_requested": args.model, "model_reported": resp.model,
                    "temperature": args.temperature,
                    "tokens_in": resp.tokens_in, "tokens_out": resp.tokens_out,
                    "latency_s": dt, "output": resp.text,
                    "parsed": parsed, "parse_ok": parsed is not None,
                }
                fraw.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
                fraw.flush()
                if capture is not None:
                    capture.write({"purpose": "judge", "prompt_hash": sha256_text(SYSTEM_PROMPT + s["user"]),
                                   "system": SYSTEM_PROMPT, "user": s["user"],
                                   "output": resp.text, "model": resp.model, "thinking": False,
                                   "cached": False})
                runs.append(rec)

    ok = [r for r in runs if r["parse_ok"]]
    agg: Dict[str, Any] = {
        "schema_version": SCHEMA,
        "inputs": plan["inputs"],
        "protocol": plan["protocol"],
        "n_calls": len(runs), "n_parse_ok": len(ok),
        "parse_fail_rate": round(1 - len(ok) / len(runs), 6) if runs else None,
        "provider": {"name": getattr(provider, "name", None), "model_requested": args.model,
                     "models_reported": sorted({r["model_reported"] for r in runs})},
        "scores": {}, "agreement": {}, "per_sample": [],
    }
    for k in DIMS:
        vals = [r["parsed"][k] for r in ok]
        agg["scores"][k] = dist(vals)
    for a in range(args.repeat):
        for b in range(a + 1, args.repeat):
            pa = {r["sample_id"]: r["parsed"] for r in ok if r["repeat"] == a}
            pb = {r["sample_id"]: r["parsed"] for r in ok if r["repeat"] == b}
            common = sorted(set(pa) & set(pb))
            for k in DIMS:
                xa = [pa[s][k] for s in common]
                xb = [pb[s][k] for s in common]
                exact = sum(1 for x, y in zip(xa, xb) if x == y)
                agg["agreement"][f"rep{a}_vs_rep{b}.{k}"] = {
                    "n": len(common), "exact_agreement": round(exact / len(common), 6) if common else None,
                    "mean_abs_diff": round(sum(abs(x - y) for x, y in zip(xa, xb)) / len(common), 6) if common else None,
                    "cohen_kappa_binary5": cohen_kappa(xa, xb),
                    "spearman": spearman(xa, xb),
                }
    for s in samples:
        rs = [r for r in ok if r["sample_id"] == s["sample_id"]]
        agg["per_sample"].append({
            "sample_id": s["sample_id"], "thread_key": s["thread_key"],
            "n_msgs": len(s["messages"]),
            "scores_per_repeat": [{k: r["parsed"][k] for k in DIMS} for r in rs],
            "worst_line": rs[0]["parsed"]["worst_line"] if rs else None,
            "reason": rs[0]["parsed"]["reason"] if rs else None,
            "transcript": s["transcript"],
        })

    out_json = os.path.join(args.out_dir, "judge_aggregate.json")
    open(out_json, "w", encoding="utf-8").write(
        json.dumps(agg, ensure_ascii=False, indent=1, sort_keys=True) + "\n")

    lines = ["# LLM-as-judge 读数\n",
             f"- 日志: `{agg['inputs']['log']}` (sha `{agg['inputs']['log_sha256']}`)",
             f"- 模型: {args.model}（reported {agg['provider']['models_reported']}）/ temperature={args.temperature}",
             f"- 抽样: 线程级 {len(samples)} 条 / 重复 {args.repeat} 次 / seed={args.seed}",
             f"- system prompt sha: `{plan['protocol']['system_prompt_sha256']}`",
             f"- 解析失败率: {agg['parse_fail_rate']}\n",
             "## 维度分布（1–7）\n", "| 维度 | n | min | p10 | p50 | p90 | max | mean |", "|---|---|---|---|---|---|---|---|"]
    for k in DIMS:
        d = agg["scores"][k]
        lines.append(f"| {DIM_ZH[k]} `{k}` | {d.get('n')} | {d.get('min')} | {d.get('p10')} | {d.get('p50')} | {d.get('p90')} | {d.get('max')} | {d.get('mean')} |")
    lines += ["\n## 一致性（重复评）\n", "| 键 | n | exact | mean_abs_diff | κ(≥5) | ρ |", "|---|---|---|---|---|---|"]
    for k, v in sorted(agg["agreement"].items()):
        lines.append(f"| `{k}` | {v['n']} | {v['exact_agreement']} | {v['mean_abs_diff']} | {v['cohen_kappa_binary5']} | {v['spearman']} |")
    lines += ["\n## 样本与最差句（原文，不替代客观读数）\n"]
    for p in agg["per_sample"]:
        lines.append(f"### {p['sample_id']} `{p['thread_key']}`（{p['n_msgs']} 条）")
        lines.append("```text\n" + p["transcript"] + "\n```")
        lines.append(f"- 打分（每轮）: {p['scores_per_repeat']}")
        lines.append(f"- worst_line: {p['worst_line']}")
        lines.append(f"- reason: {p['reason']}\n")
    open(os.path.join(args.out_dir, "judge_report.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(json.dumps({"n_calls": len(runs), "n_parse_ok": len(ok),
                      "out_dir": args.out_dir, "aggregate": out_json,
                      "capture_used": capture is not None}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
