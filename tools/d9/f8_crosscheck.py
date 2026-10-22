#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""f8_crosscheck.py — F-8t 独立复算（**交叉校验用，非指标真源**）

用途
----
跑批者（batch-runner）的**第二实现**，用于与指标真源 `tools/d5/dialogue_metrics.py`
的 F-8t 结果做并排交叉校验。真源永远是 `tools/d5/`；本脚本只做独立复核。

纪律
----
- 只读 run.jsonl + 冻结词表 `tools/d5/f8_lexicon.json`，不写任何结论性判断；
- 口径与真源保持一致：`narrow` 词表 + **本人当回合 slot 限定**；
- 输出 `F-8t_all`（含 slot_agnostic「这会儿」）与 `F-8t_core`（排除 slot_agnostic）两组，
  并给 `hits_by_token` / `hits_by_token_msgs` 便于逐条比对；
- **不得**用于替代真源产出报告数值；两实现不一致时应停下来查，而不是择一采用。

用法
----
  python3 tools/d9/f8_crosscheck.py --log v2/evidence/<run>/run.jsonl \
      --lexicon tools/d5/f8_lexicon.json [--out /tmp/f8_crosscheck.json]

退出码：0 正常；2 输入缺失/解析失败；3 与真源数值不一致（仅在给了 --expect-json 时）
"""
from __future__ import annotations

import argparse
import collections
import json
import sys


def _load_msgs(path):
    msgs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if str(d.get("type", "")).startswith("MSG_"):
                msgs.append(d)
    return msgs


def _tokens_for(narrow, slot):
    by = narrow.get("by_slot", {})
    agn = narrow.get("slot_agnostic", [])
    return list(by.get(slot, [])), list(agn)


def recompute(log_path, lexicon_path):
    lex = json.load(open(lexicon_path, encoding="utf-8"))
    narrow = lex["time"]["narrow"]
    msgs = _load_msgs(log_path)

    all_hits = []          # 含 slot_agnostic
    core_hits = []         # 仅档内词
    per_token_multi = collections.Counter()
    per_token_primary = collections.Counter()
    hit_msgs = {}
    n_slot_missing = 0

    for m in msgs:
        p = m.get("payload") or {}
        body = p.get("body") or ""
        slot = p.get("slot")
        if not slot:
            n_slot_missing += 1
            continue
        slot_toks, agn_toks = _tokens_for(narrow, slot)
        hit_slot = [t for t in slot_toks if t in body]
        hit_agn = [t for t in agn_toks if t in body]
        hit_all = hit_slot + hit_agn
        if hit_all:
            uid = p.get("msg_uid")
            all_hits.append(uid)
            hit_msgs[uid] = hit_all
            for t in hit_all:
                per_token_multi[t] += 1
            # primary：互斥归因，取最长匹配词（等长取档内词优先），使 primary 之和 == 分子
            best = max(hit_all, key=lambda t: (len(t), t in hit_slot))
            per_token_primary[best] += 1
        if hit_slot:
            core_hits.append(p.get("msg_uid"))

    n = len(msgs)
    out = {
        "source": "independent_crosscheck（非指标真源，仅交叉校验）",
        "log": log_path,
        "lexicon": lexicon_path,
        "n_msg": n,
        "n_slot_missing": n_slot_missing,
        "F-8t_all": {
            "num": len(all_hits),
            "den": n,
            "rate_pct": round(100.0 * len(all_hits) / n, 6) if n else None,
            "lexicon": "narrow",
            "scope": "own_slot",
        },
        "F-8t_core": {
            "num": len(core_hits),
            "den": n,
            "rate_pct": round(100.0 * len(core_hits) / n, 6) if n else None,
            "lexicon": "narrow_onslot",
            "scope": "own_slot",
            "excluded_agnostic_tokens": list(narrow.get("slot_agnostic", [])),
        },
        "hits_by_token": dict(sorted(per_token_multi.items())),
        "hits_by_token_primary": dict(sorted(per_token_primary.items())),
        "hits_by_token_msgs": {k: hit_msgs[k] for k in sorted(hit_msgs)},
    }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="F-8t 独立复算（交叉校验，非真源）")
    ap.add_argument("--log", required=True)
    ap.add_argument("--lexicon", default="tools/d5/f8_lexicon.json")
    ap.add_argument("--out", default=None)
    ap.add_argument("--expect-json", default=None,
                    help="给真源 metrics json 时，自动比对 F-8t_all/F-8t_core 分子分母，不一致 exit 3")
    a = ap.parse_args(argv)
    try:
        res = recompute(a.log, a.lexicon)
    except Exception as e:  # noqa: BLE001
        print(f"[f8_crosscheck] 解析失败: {e}", file=sys.stderr)
        return 2

    js = json.dumps(res, ensure_ascii=False, indent=2)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(js + "\n")
    print(js)

    if a.expect_json:
        src = json.load(open(a.expect_json, encoding="utf-8"))

        def find(o, k):
            if isinstance(o, dict):
                for kk, vv in o.items():
                    if kk == k:
                        return vv
                    r = find(vv, k)
                    if r is not None:
                        return r
            elif isinstance(o, list):
                for it in o:
                    r = find(it, k)
                    if r is not None:
                        return r
            return None

        node = find(src, "F-8_scene_anchor") or {}
        bad = []
        for key in ("F-8t_all", "F-8t_core"):
            tgt = node.get(key) or {}
            mine = res[key]
            if (tgt.get("num"), tgt.get("den")) != (mine["num"], mine["den"]):
                bad.append(f"{key}: 真源={tgt.get('num')}/{tgt.get('den')} 复算={mine['num']}/{mine['den']}")
        if bad:
            print("[f8_crosscheck] MISMATCH:\n  " + "\n  ".join(bad), file=sys.stderr)
            return 3
        print("[f8_crosscheck] MATCH: F-8t_all / F-8t_core 分子分母与真源一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
