#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D4 · judge 执行器（按 d4_judge_sampling_plan.md §2/§3）

用法（仓库根执行，需先 source code/.env.local）：
  python3 v2/evidence/d4_judge_run.py \
     --sample A0=v2/evidence/d4_judge_sample_A0.json \
     --sample A1=v2/evidence/d4_judge_sample_A1.json \
     --out v2/evidence/d4_judge_runs.jsonl \
     --model "$LLM_MODEL" --endpoint "$LLM_ENDPOINT" --repeats 2

设计约束：
  * temperature=0；prompt 模板 sha256 落盘；原始请求/响应逐条落 jsonl（可复核）；
  * 维度写死 5 项（naturalness / persona_fit / specificity / is_reply / free_text）；
  * **不喂模板 id**（避免内部 token 泄漏给 judge 造成偏差）：场景与话题都走中文映射；
  * 只读样本文件，不改任何世界层文件。
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys, time
from pathlib import Path

SCENE_CN = {"gift": "送东西给对方", "whisper": "压低声音说句私房话", "mentorship": "带一带新手",
            "combat_training": "一起练把式", "scarce_buy": "缺料想找人凑一凑", "savings": "盘算攒钱",
            "polite_reject": "婉拒对方", "counter_propose": "还个价换个法子", "rel_maintain": "维持老交情",
            "skill_practice": "手上的活计", "job_choice": "琢磨营生", "select_location": "挑地方",
            "contest": "比试", "ice_break": "搭话认识一下", "academic_collab": "合计个题目",
            "group_proposal": "当众提个议", "power_conflict": "起了争执", "rel_accept": "应下交情"}

SYSTEM = "你是一个严格的中文对话质量评审员。只按 rubric 打分，不要客套。"
RUBRIC = """请给下面这条台词打分（每项 1-7 的整数），并给一句理由。
1) naturalness：像不像真人在过日子时随口说的话（1=像手册或旁白，7=像真人随口说的）
2) persona_fit：是否符合说话人的身份、行当、说话习惯
3) specificity：是否带具体的人/物/数/由头（1=空泛，7=很具体）
4) is_reply：（仅当这是对上一句的回应）是否接住了对方上一句的具体内容（1=完全另起话题，7=紧接具体内容）；不是回应则填 0
只输出一行 JSON：{"naturalness":n,"persona_fit":n,"specificity":n,"is_reply":n,"reason":"..."}"""


def scene(t):
    return SCENE_CN.get(str(t), "闲聊")


def build_prompt(sample: dict, arm_msgs: dict) -> str:
    th = sample.get("thread_id")
    hist = arm_msgs.get(th, [])[:3]
    ctx = "\n".join(f"{h['from']}：{h['body'][:120]}" for h in hist) or "(无前序)"
    return (RUBRIC
            + f"\n\n场合：{scene(sample.get('topic'))}"
            + f"\n说话人：{sample.get('from')}　对象：{sample.get('to') or '（当众）'}"
            + f"\n前序对话：\n{ctx}"
            + f"\n待评台词：{sample.get('body')}")


def call(endpoint, key, model, prompt, temperature=0.0, timeout=90):
    import urllib.request
    body = json.dumps({"model": model, "temperature": temperature,
                       "messages": [{"role": "system", "content": SYSTEM},
                                    {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(endpoint.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode())
    return d["choices"][0]["message"]["content"], d.get("model")


def parse(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def load_samples(spec):
    name, _, path = spec.partition("=")
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return name, d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="append", required=True, help="ARM=sample_json")
    ap.add_argument("--run", action="append", default=[], help="ARM=run.jsonl（用于取前序，可选）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--endpoint", default=os.environ.get("LLM_ENDPOINT", ""))
    ap.add_argument("--key", default=os.environ.get("LLM_API_KEY", ""))
    ap.add_argument("--model", default=os.environ.get("LLM_MODEL", "DeepSeek-Flash"))
    ap.add_argument("--repeats", type=int, default=2)
    a = ap.parse_args()
    if not a.endpoint or not a.key:
        print("[FAIL] 缺 endpoint/key：请先 source code/.env.local", file=sys.stderr)
        return 2

    runs = {}
    for spec in a.run:
        name, _, path = spec.partition("=")
        by = {}
        for line in open(path, encoding="utf-8"):
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("type") not in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
                continue
            p = e.get("payload") or {}
            by.setdefault(p.get("thread_id"), []).append(
                {"round": e.get("round") or 0, "from": p.get("from") or p.get("author"), "body": p.get("body") or ""})
        for v in by.values():
            v.sort(key=lambda x: x["round"])
        runs[name] = by

    template_sha = hashlib.sha256((SYSTEM + RUBRIC).encode()).hexdigest()
    out = open(a.out, "w", encoding="utf-8")
    n = 0
    for spec in a.sample:
        arm, d = load_samples(spec)
        msgs = runs.get(arm, {})
        for s in d["samples"]:
            prompt = build_prompt(s, msgs)
            for rep in range(a.repeats):
                t0 = time.time()
                try:
                    text, model = call(a.endpoint, a.key, a.model, prompt)
                    parsed = parse(text)
                    err = None if parsed else "unparsable"
                except Exception as ex:  # noqa: BLE001
                    text, model, parsed, err = "", a.model, None, f"{type(ex).__name__}:{ex}"
                out.write(json.dumps({"arm": arm, "msg_uid": s.get("msg_uid"), "thread_id": s.get("thread_id"),
                                      "round": s.get("round"), "turn_index": s.get("turn_index"),
                                      "rep": rep, "model": model, "template_sha256": template_sha,
                                      "prompt": prompt, "raw": text, "parsed": parsed, "error": err,
                                      "latency_s": round(time.time() - t0, 2)}, ensure_ascii=False) + "\n")
                n += 1
                out.flush()
    out.close()
    print(f"[done] {n} calls -> {a.out} (template_sha256={template_sha[:16]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
