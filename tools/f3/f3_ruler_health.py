#!/usr/bin/env python3
"""F-3 尺子健康度诊断器（只读：不跑批、不调 LLM、不改 `tools/d5/emotion_lexicon.txt`）。

回答一个问题：**F-3 在 n16×r24 上「分母 3/4、机会密度 0.0157、分子全 0」到底是
「词表太小（尺子死）」还是「单批消息量太小（尺子活着但窗口不够）」。**

口径（与 `tools/d5/dialogue_metrics.py::F-3_emotion_echo` 同源，逐字镜像）：
  * 线程 = `mixed_key`（thread_id 优先；否则 day+channel+对端/场所），线程内按 (round, seq) 排序；
  * 极性 = 词表子串计数多数胜（`pos>neg → +1`，`neg>pos → −1`，否则 0）；
  * **分母** = 线程内相邻对 `(i−1, i)` 中「上一句极性 ≠ 0」的对数；
  * **主口径 = reply_path**：在上述分母上再要求当前句 `payload.reply_to` 非空（F-3 机制判定的是"对别人情绪的回应"）；
  * **分子** = 当前句极性 == 上一句极性，**或** 命中 `EMPATHY_MARKERS`。

输出：
  * 语料级机会密度（`Σ分母 / Σ消息`）+ 逐批密度的 p10/p50/p90 分布；
  * 分母 ≥30 所需跑批规模的算术链（含 msgs/agent-round 实测）；
  * 分母最大的若干批上的**接住率**（分子/分母），以及「强呼应」与「仅共情词」拆分；
  * 换词表（如 `tools/f3/emotion_lexicon_v2_candidate.txt`）后的密度与词表提升系数。

用法：
    python3 tools/f3/f3_ruler_health.py --root v2/evidence \
        --pin v2/evidence/r38_f4b_corpus_manifest.json \
        --lexicon main=tools/d5/emotion_lexicon.txt \
        --lexicon v2=tools/f3/emotion_lexicon_v2_candidate.txt \
        --run ref_on=v2/evidence/r38_f3_batch/on/run.jsonl \
        --json-out v2/evidence/r38_f3_ruler_health.json
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


d5 = _load("d5_metrics", REPO / "tools/d5/dialogue_metrics.py")
EMPATHY = tuple(d5.EMPATHY_MARKERS)


def sha8(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:8]


def r6(x):
    return None if x is None else round(float(x), 6)


def pct(vals, q):
    if not vals:
        return None
    s = sorted(vals)
    if len(s) == 1:
        return r6(s[0])
    pos = (len(s) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(s) - 1)
    return r6(s[lo] + (s[hi] - s[lo]) * (pos - lo))


def load_lexicon(path):
    emo = {}
    p = Path(path)
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split()
        if len(parts) >= 2:
            try:
                emo[" ".join(parts[1:])] = int(parts[0])
            except ValueError:
                continue
    return emo


def mixed_key(m):
    return d5_mixed_key(m)


def d5_mixed_key(m):
    """镜像 dialogue_metrics::mixed_key（该函数是闭包内定义，无法直接 import）。"""
    if m.get("thread_id"):
        return "m:T|%s" % m["thread_id"]
    if m["channel"] == "dm":
        k = "-".join(sorted({str(m["from"]), str(m["to"])}))
    elif m["channel"] == "public":
        k = "-"
    else:
        k = str(m.get("place") or "-")
    return "m:%s|%s|%s" % (m["day"], m["channel"], k)


def analyze(path, emo):
    recs, bad = d5.read_run(str(path))
    msgs = d5.extract_messages(recs)
    threads = defaultdict(list)
    for m in msgs:
        threads[mixed_key(m)].append(m)
    for k in threads:
        threads[k].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                       m["seq"] if m["seq"] is not None else -1))

    def pol(body):
        pos = sum(1 for w, p in emo.items() if p > 0 and w in body)
        neg = sum(1 for w, p in emo.items() if p < 0 and w in body)
        return 1 if pos > neg else (-1 if neg > pos else 0)

    n_msg = len(msgs)
    pol_nz = sum(1 for m in msgs if pol(m["body"]) != 0)
    den_all = den_reply = 0
    ok_all = ok_reply = 0
    strong_reply = marker_reply = 0
    for key in threads:
        th = threads[key]
        for i in range(1, len(th)):
            prev, cur = th[i - 1], th[i]
            p_prev, p_cur = pol(prev["body"]), pol(cur["body"])
            if p_prev == 0:
                continue
            hit_marker = any(w in cur["body"] for w in EMPATHY)
            hit_same = (p_cur == p_prev)
            hit = hit_same or hit_marker
            den_all += 1
            ok_all += 1 if hit else 0
            if cur.get("reply_to"):
                den_reply += 1
                ok_reply += 1 if hit else 0
                strong_reply += 1 if hit_same else 0
                marker_reply += 1 if hit_marker else 0

    agents = {str(m["from"]) for m in msgs}
    rounds = {m["round"] for m in msgs if m["round"] is not None}
    return {
        "n_messages": n_msg,
        "n_threads": len(threads),
        "n_agents": len(agents),
        "n_rounds": len(rounds),
        "agent_rounds": len(agents) * len(rounds),
        "msgs_per_agent_round": r6(n_msg / (len(agents) * len(rounds))) if agents and rounds else None,
        "polarity_nonzero_msgs": pol_nz,
        "polarity_nonzero_density": r6(pol_nz / n_msg) if n_msg else None,
        "den_all": den_all,
        "ok_all": ok_all,
        "den_reply_path": den_reply,
        "ok_reply_path": ok_reply,
        "ok_reply_path_strong": strong_reply,
        "ok_reply_path_marker": marker_reply,
        "echo_rate_reply_path": r6(ok_reply / den_reply) if den_reply else None,
        "echo_rate_all": r6(ok_all / den_all) if den_all else None,
        "density_reply_path": r6(den_reply / n_msg) if n_msg else None,
        "density_all": r6(den_all / n_msg) if n_msg else None,
        "bad_lines": bad,
    }


def band(den):
    if den == 0:
        return "denominator_zero"
    if den < 30:
        return "count_only"
    if den < 68:
        return "probe"
    return "ok"


def agg(rows, msgs_key="n_messages"):
    """在若干 run 上汇总（分母/分子相加，密度按消息量加权）。"""
    n_msg = sum(r["n_messages"] for r in rows)
    den_r = sum(r["den_reply_path"] for r in rows)
    ok_r = sum(r["ok_reply_path"] for r in rows)
    den_a = sum(r["den_all"] for r in rows)
    ok_a = sum(r["ok_all"] for r in rows)
    dens = [r["density_reply_path"] for r in rows if r["density_reply_path"] is not None]
    return {
        "n_runs": len(rows),
        "n_messages": n_msg,
        "den_reply_path": den_r,
        "ok_reply_path": ok_r,
        "echo_rate_reply_path": r6(ok_r / den_r) if den_r else None,
        "den_all": den_a,
        "ok_all": ok_a,
        "echo_rate_all": r6(ok_a / den_a) if den_a else None,
        "band_reply_path": band(den_r),
        "density_reply_path_weighted": r6(den_r / n_msg) if n_msg else None,
        "density_reply_path_per_run": {"p10": pct(dens, 0.10), "p50": pct(dens, 0.50),
                                       "p90": pct(dens, 0.90), "min": min(dens) if dens else None,
                                       "max": max(dens) if dens else None},
    }


def scale_chain(density, msgs_per_ar, target=30):
    """期望分母 ≈ MSG数 × 机会密度 ⇒ 反解所需 MSG / agent-round。"""
    if not density:
        return None
    msgs_needed = target / density
    ar_needed = msgs_needed / msgs_per_ar if msgs_per_ar else None
    out = {
        "formula": "期望分母 ≈ MSG数 × 机会密度；所需 MSG = 目标分母 / 机会密度",
        "target_denominator": target,
        "density_used": density,
        "msgs_needed": r6(msgs_needed),
        "msgs_per_agent_round_used": msgs_per_ar,
        "agent_rounds_needed": r6(ar_needed),
        "examples": [],
    }
    if ar_needed:
        for agents in (16, 24, 32):
            out["examples"].append({"agents": agents, "rounds": int(ar_needed / agents) + 1,
                                    "agent_rounds": int(ar_needed / agents) * agents + agents})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="F-3 尺子健康度诊断器（只读）")
    ap.add_argument("--root", default="v2/evidence")
    ap.add_argument("--pin", default=None, help="钉版清单（relpath+sha8）")
    ap.add_argument("--lexicon", action="append", default=None,
                    metavar="LABEL=PATH", help="可重复；默认 main=tools/d5/emotion_lexicon.txt")
    ap.add_argument("--run", action="append", default=None, metavar="LABEL=PATH",
                    help="额外单批（如 n16r24 参考批），可重复")
    ap.add_argument("--top-n", type=int, default=8)
    ap.add_argument("--live-window", type=int, default=900)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)

    root = Path(args.root)
    if not root.is_absolute():
        root = (Path.cwd() / root).resolve()
    lex_specs = args.lexicon or ["main=tools/d5/emotion_lexicon.txt"]
    lexicons = {}
    for spec in lex_specs:
        label, path = spec.split("=", 1)
        p = Path(path)
        if not p.is_absolute():
            p = (REPO / p).resolve()
        lexicons[label] = {"path": str(p.relative_to(REPO)) if str(p).startswith(str(REPO)) else str(p),
                           "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                           "n_words": len(load_lexicon(p)),
                           "n_pos": sum(1 for v in load_lexicon(p).values() if v > 0),
                           "n_neg": sum(1 for v in load_lexicon(p).values() if v < 0),
                           "emo": load_lexicon(p)}

    logs = sorted(root.rglob("run.jsonl")) if root.is_dir() else [root]
    pin_map = None
    if args.pin:
        pin_map = {e["log"]: e["sha8"] for e in json.loads(Path(args.pin).read_text(encoding="utf-8"))}
        logs = [lg for lg in logs if str(lg.relative_to(root)) in pin_map]
    excluded = {"invalid": [], "live": []}
    import time
    now = time.time()
    keep, manifest = [], []
    for lg in logs:
        rel = str(lg.relative_to(root))
        if pin_map is None:
            if re.search(r"INVALID|ABORTED", rel, re.I):
                excluded["invalid"].append(rel)
                continue
            if args.live_window > 0 and now - lg.stat().st_mtime < args.live_window:
                excluded["live"].append(rel)
                continue
        s8 = sha8(lg)
        if pin_map is not None and pin_map.get(rel) != s8:
            print(f"[FAIL] 钉版校验失败: {rel}", file=sys.stderr)
            return 3
        manifest.append({"log": rel, "sha8": s8})
        keep.append(lg)

    out = {
        "meta": {
            "generator": "tools/f3/f3_ruler_health.py",
            "root": str(root),
            "n_run_jsonl_read": len(keep),
            "excluded": excluded,
            "corpus_fingerprint": hashlib.sha256(
                "\n".join(sorted(f"{m['log']} {m['sha8']}" for m in manifest)).encode()).hexdigest()[:16],
            "caliber": {
                "denominator": "线程(mixed_key)内相邻对中『上一句极性≠0』的对数；reply_path 主口径再加『当前句 reply_to 非空』",
                "numerator": "当前句极性 == 上一句极性 或 命中 EMPATHY_MARKERS",
                "density": "den_reply_path / n_messages（逐批），语料级=Σden/Σmsg",
            },
            "lexicons": {k: {kk: vv for kk, vv in v.items() if kk != "emo"} for k, v in lexicons.items()},
        },
        "by_lexicon": {},
    }

    # 主扫
    for label, lx in lexicons.items():
        rows = []
        for lg in keep:
            r = analyze(lg, lx["emo"])
            r["log"] = str(lg.relative_to(root))
            r["log_sha8"] = sha8(lg)
            rows.append(r)
        a = agg(rows)
        spar = a["density_reply_path_weighted"]
        ar_rates = [r["msgs_per_agent_round"] for r in rows if r["msgs_per_agent_round"]]
        ar_med = pct(ar_rates, 0.5)
        top = sorted(rows, key=lambda r: -r["den_reply_path"])[: args.top_n]

        def sub(pred):
            s_ = [r for r in rows if pred(r)]
            return agg(s_) if s_ else None

        subsets = {
            "all": a,
            "non_mock": sub(lambda r: not re.search(r"mock|synth", r["log"], re.I)),
            "n16r24_scale(150<=msg<250)": sub(lambda r: 150 <= r["n_messages"] < 250),
            "mid(400<=msg<700)": sub(lambda r: 400 <= r["n_messages"] < 700),
            "den_ge_30": sub(lambda r: r["den_reply_path"] >= 30),
            "den_gt_0_lt_30": sub(lambda r: 0 < r["den_reply_path"] < 30),
        }
        out["by_lexicon"][label] = {
            "subsets": subsets,
            "overall": a,
            "scale_chain_weighted": scale_chain(spar, ar_med),
            "scale_chain_median_batch": scale_chain(a["density_reply_path_per_run"]["p50"], ar_med),
            "msgs_per_agent_round": {"p10": pct(ar_rates, 0.1), "p50": ar_med, "p90": pct(ar_rates, 0.9)},
            "top_den_batches": top,
            "runs": rows,
        }

    # 额外单批（参考批）
    if args.run:
        out["extra_runs"] = {}
        for spec in args.run:
            label, path = spec.split("=", 1)
            p = Path(path)
            if not p.is_absolute():
                p = (Path.cwd() / p).resolve()
            out["extra_runs"][label] = {"log": str(p), "log_sha8": sha8(p), "by_lexicon": {}}
            for lname, lx in lexicons.items():
                r = analyze(p, lx["emo"])
                r["band_reply_path"] = band(r["den_reply_path"])
                out["extra_runs"][label]["by_lexicon"][lname] = r

    if args.json_out:
        pj = Path(args.json_out)
        pj.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[OK] json -> {args.json_out}")

    # ---- 文本摘要
    print(f"# F-3 尺子健康度（语料 {out['meta']['n_run_jsonl_read']} 份, "
          f"fingerprint={out['meta']['corpus_fingerprint']}）")
    for label, blk in out["by_lexicon"].items():
        a = blk["overall"]
        print(f"\n== 词表 {label}（{lexicons[label]['n_words']} 词: "
              f"{lexicons[label]['n_pos']}正/{lexicons[label]['n_neg']}负）==")
        print(f"  消息={a['n_messages']} 分母(reply_path)={a['den_reply_path']} 分子={a['ok_reply_path']} "
              f"接住率={a['echo_rate_reply_path']} 档={a['band_reply_path']}")
        print(f"  语料级密度(Σden/Σmsg)={a['density_reply_path_weighted']}")
        d = a["density_reply_path_per_run"]
        print(f"  逐批密度分布: p10={d['p10']} p50={d['p50']} p90={d['p90']} min={d['min']} max={d['max']}")
        sc = blk["scale_chain_weighted"]
        if sc:
            print(f"  规模链: 需要 MSG≈{sc['msgs_needed']} "
                  f"(msgs/agent-round p50={sc['msgs_per_agent_round_used']}) ⇒ agent-round≈{sc['agent_rounds_needed']}")
            print(f"          示例: " + "; ".join(f"{e['agents']}×r{e['rounds']}" for e in sc["examples"]))
        print("  子集（分母/分子/接住率/密度）:")
        for name, v in blk["subsets"].items():
            if v is None:
                continue
            print(f"    {name}: runs={v['n_runs']} msg={v['n_messages']} den={v['den_reply_path']} "
                  f"ok={v['ok_reply_path']} rate={v['echo_rate_reply_path']} "
                  f"dens={v['density_reply_path_weighted']} 档={v['band_reply_path']}")
        print("  分母最大的批次（接住率）:")
        for r in blk["top_den_batches"]:
            print(f"    {r['log']}: msg={r['n_messages']} den={r['den_reply_path']} "
                  f"ok={r['ok_reply_path']} rate={r['echo_rate_reply_path']} "
                  f"strong={r['ok_reply_path_strong']} marker={r['ok_reply_path_marker']} "
                  f"dens={r['density_reply_path']}")
    if "extra_runs" in out:
        print("\n== 参考批（n16r24）==")
        for label, blk in out["extra_runs"].items():
            for lname, r in blk["by_lexicon"].items():
                print(f"  {label} / {lname}: msg={r['n_messages']} den_reply={r['den_reply_path']} "
                      f"ok={r['ok_reply_path']} rate={r['echo_rate_reply_path']} dens={r['density_reply_path']} "
                      f"档={r['band_reply_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
