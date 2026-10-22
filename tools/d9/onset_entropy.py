#!/usr/bin/env python3
"""onset_entropy.py — 「句首熵」机制闸的**唯一判定实现**（冻结版，D12-B）

用途（D12 原预登记 §2 臂 D12-B 的**机制生效闸**）：
> 对每个 agent 取其全部台词的**前 4 字**，统计该 agent 内的经验熵；全体 agent 熵均值 = H；
> **H 相对 OFF 臂上升 ≥10% 才算机制生效**；未升 ≥10% ⇒ 判「机制未生效」，**不得判「无效」**。

判定语义（写死，不得另写一版参与判定）：
1. 单位：**per-agent**；agent 取其全部 `MSG_*` 的 `from`/`author`；
2. 句首：`body` 原文前 **4 个字符**（不足 4 字则取全部；空 body 跳过）；
3. 熵：该 agent 句首 4 字的**经验熵**（自然对数，`H = -Σ p ln p`）；
4. 全体值：`H_mean = 所有"有效 agent"(台词数≥1) 的熵的算术平均`；
5. 不做的：不规范化文本、不切词、不分渠道（DM/GROUP/PUBLIC 合并）、不使用 LLM。

用法：
  python3 tools/d9/onset_entropy.py --run <run.jsonl> [--json]
  # 两臂对比（判定用）：
  python3 tools/d9/onset_entropy.py --compare <OFF.jsonl> <ON.jsonl>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict

MSG_TYPES = ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC")
ONSET_LEN = 4
RISE_THRESHOLD = 0.10


def impl_sha256() -> str:
    spec = (
        "unit=per-agent\n"
        "onset=body_first_4_chars\n"
        "entropy=empirical_natural_log\n"
        "aggregate=mean_over_agents_with_at_least_1_message\n"
        "channels=" + ",".join(MSG_TYPES) + "\n"
        "rise_threshold=0.10\n"
    )
    return hashlib.sha256(spec.encode("utf-8")).hexdigest()


def onset_of(body: str) -> str:
    b = body or ""
    return b[:ONSET_LEN]


def _entropy(counter: Counter) -> float:
    total = sum(counter.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counter.values():
        p = c / total
        h -= p * math.log(p)
    return h


def onset_stats(path: str) -> dict:
    per_agent = defaultdict(Counter)
    bad = 0
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            bad += 1
            continue
        if r.get("type") not in MSG_TYPES:
            continue
        p = r.get("payload") or {}
        who = p.get("from") or p.get("author") or r.get("actor")
        o = onset_of(p.get("body") or "")
        if not who or not o:
            continue
        per_agent[who][o] += 1
    ents = {a: _entropy(c) for a, c in per_agent.items() if sum(c.values()) > 0}
    h_mean = round(sum(ents.values()) / len(ents), 6) if ents else 0.0
    return {
        "source": path,
        "n_agents": len(ents),
        "n_messages": sum(sum(c.values()) for c in per_agent.values()),
        "H_mean": h_mean,
        "H_by_agent": {a: round(v, 6) for a, v in sorted(ents.items())},
        "bad_lines": bad,
        "impl_sha256": impl_sha256(),
    }


def compare(off_path: str, on_path: str) -> int:
    off = onset_stats(off_path)
    on = onset_stats(on_path)
    rise = (on["H_mean"] - off["H_mean"]) / off["H_mean"] if off["H_mean"] else 0.0
    ok = rise >= RISE_THRESHOLD
    print(json.dumps({
        "OFF": {"H_mean": off["H_mean"], "n_agents": off["n_agents"], "n_messages": off["n_messages"]},
        "ON": {"H_mean": on["H_mean"], "n_agents": on["n_agents"], "n_messages": on["n_messages"]},
        "delta_H": round(on["H_mean"] - off["H_mean"], 6),
        "rise_ratio": round(rise, 4),
        "threshold": RISE_THRESHOLD,
        "verdict": "机制生效(PASS)" if ok else "机制未生效(FAIL：模型没按自己的脾气起句)",
        "impl_sha256": impl_sha256(),
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    ap.add_argument("--compare", nargs=2, metavar=("OFF", "ON"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.compare:
        return compare(a.compare[0], a.compare[1])
    if not a.run:
        ap.error("需要 --run 或 --compare")
    s = onset_stats(a.run)
    if a.json:
        print(json.dumps(s, ensure_ascii=False, sort_keys=True))
    else:
        print(f"{s['source']}  agents={s['n_agents']}  msgs={s['n_messages']}  H_mean={s['H_mean']}")
        print(f"impl_sha256={s['impl_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
