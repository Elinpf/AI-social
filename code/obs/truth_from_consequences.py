"""「确定性后果」真值口径 —— 给判别式判定(T212)提供**可复算的 TRUE_label**。

**只读日志、纯函数、确定性**（无随机/无时钟）。**不把生成式 A 的标签当正确答案**：
本模块用**判定之后的确定性后果事件**（不需要 LLM）反推真值：

| 维度 | 后果事件 | TRUE_label 规则 |
|---|---|---|
| `rel_affinity` | `RELATION_CHANGE{dim:affinity,from:a,to:b}` | 窗口内`Δ>0` → `formed`；有事件但无正向 → `not_formed` |
| `rel_familiarity` | `RELATION_CHANGE{dim:familiarity}` | 同上 → `formed` / `not_formed` |
| `rel_trust` | `RELATION_CHANGE{dim:trust}` | 同上 → `formed` / `not_formed` |
| `respect` | `RELATION_CHANGE{dim:respect}` | `Δ>0` → `high`；有事件无正向 → `low` |
| `stance` | `OFFER_ACCEPTED/REJECTED`（`by=a` 且 offer creator=b） | 有 accept → `accept`；有 reject → `reject` |
| `affection` | —— | **默认剔除**（无「affection」关系维；疑似→affinity，**未验证**） |
| `weekly_focus` | —— | **默认剔除**（后果为活动模式，无干净口径，**未验证**） |

**三条硬约束（Leader 批准）**：
  (a) **窗口 W 参数化**（默认 12 回合 ≈ 1 仿真日；可 `dim_windows` 按维度覆盖）；
  (b) **被剔除的样本按维度计数并单列**（避免 ECE 样本数悄悄缩水）；
  (c) **人工核抽样规则确定**（按 `judgment_id` 排序，等距取 ≤20 条）。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

__all__ = [
    "CONSEQUENCE_RULES", "DEFAULT_WINDOW", "truth_from_consequences",
    "correct_from_truth", "human_sample",
]

DEFAULT_WINDOW = 12  # 回合

# 默认规则表（可传 rules 覆盖）。value = (kind, param)
#   kind="rc"    param=关系维名（RELATION_CHANGE.dim）
#   kind="offer" param=None（按 by/offer creator 配对）
#   kind=None    默认剔除（原因写 reason）
CONSEQUENCE_RULES = {
    "rel_affinity":   {"kind": "rc", "rc_dim": "affinity",
                       "pos": "formed", "neg": "not_formed"},
    "rel_familiarity": {"kind": "rc", "rc_dim": "familiarity",
                        "pos": "formed", "neg": "not_formed"},
    "rel_trust":      {"kind": "rc", "rc_dim": "trust",
                       "pos": "formed", "neg": "not_formed"},
    "respect":        {"kind": "rc", "rc_dim": "respect", "pos": "high", "neg": "low"},
    "stance":         {"kind": "offer", "pos": "accept", "neg": "reject"},
    "affection":      {"kind": None, "reason": "no_affection_dim(未验证; 疑似→affinity)"},
    "weekly_focus":   {"kind": None, "reason": "no_clean_consequence(未验证)"},
}


def _p(r):
    return r.get("payload") or {}


def _offer_creator(offer_id):
    """从 offer_id 取创建者：`O-<r>-<creator>` 或 `O-<r>-<from>-<to>` → 第 3 段。"""
    if not offer_id:
        return None
    parts = str(offer_id).split("-")
    return parts[2] if len(parts) >= 3 else None


def _index(records):
    """建索引：关系变化 / 成交接受 / 拒绝 / 判定。"""
    rc = []           # (round, from, to, dim, delta)
    acc, rej = [], []
    for r in records:
        t = r["type"]
        p = _p(r)
        if t == "RELATION_CHANGE":
            rc.append((int(r.get("round", 0)), p.get("from"), p.get("to"), p.get("dim"),
                       int(p.get("after", 0)) - int(p.get("before", 0))))
        elif t == "OFFER_ACCEPTED":
            acc.append((int(r.get("round", 0)), p.get("by"), _offer_creator(p.get("offer_id"))))
        elif t == "OFFER_REJECTED":
            rej.append((int(r.get("round", 0)), p.get("by"), _offer_creator(p.get("offer_id"))))
    return rc, acc, rej


def _rc_truth(rc, dim, a, b, r0, w):
    """窗口 [r0, r0+w] 内 (a→b, dim) 的关系变化：有事件→pos/neg，无事件→None(剔除)。"""
    hit = [d for (r, f, t, dm, d) in rc if dm == dim and f == a and t == b and r0 <= r <= r0 + w]
    if not hit:
        return None
    return "pos" if any(d > 0 for d in hit) else "neg"


def _offer_truth(acc, rej, a, b, r0, w):
    """窗口内 by=a 且 offer creator=b 的接受/拒绝：有 accept→pos，有 reject→neg，皆无→None。"""
    ok = any(r0 <= r <= r0 + w for (r, by, cr) in acc if by == a and cr == b)
    no = any(r0 <= r <= r0 + w for (r, by, cr) in rej if by == a and cr == b)
    if ok:
        return "pos"
    if no:
        return "neg"
    return None


def human_sample(judgment_ids, cap=20):
    """确定性人工核抽样：按 id 升序、等距取 ≤cap 条（不随输入顺序变）。"""
    ids = sorted(judgment_ids)
    n = len(ids)
    if n == 0:
        return []
    k = max(1, n // cap)
    return ids[::k][:cap]


def truth_from_consequences(records, pairs, window=DEFAULT_WINDOW, dim_windows=None,
                            rules=None) -> dict:
    """由日志反推每条 judge 请求的 TRUE_label。

    `pairs`: 每项 `{judgment_id, dimension, parties:[a,b], round}`（`round` 缺失时从日志
    `LLM_JUDGMENT.judgment_id` 反查）。返回 labels / 逐维 exclude 计数 / 覆盖率 / 抽样。
    """
    rules = dict(CONSEQUENCE_RULES if rules is None else rules)
    dim_windows = dim_windows or {}
    rc, acc, rej = _index(records)
    jround = {(_p(r).get("judgment_id")): int(r.get("round", 0))
              for r in records if r["type"] == "LLM_JUDGMENT"}

    labels, excluded, cov, excluded_detail = {}, {}, {}, []
    for pair in pairs:
        jid = pair.get("judgment_id")
        dim = pair.get("dimension")
        parties = pair.get("parties") or []
        r0 = pair.get("round")
        if r0 is None:
            r0 = jround.get(jid)
        cov.setdefault(dim, {"n": 0, "included": 0, "excluded": 0})
        cov[dim]["n"] += 1
        rule = rules.get(dim)
        if not jid or dim is None or len(parties) < 2 or r0 is None or rule is None \
                or rule.get("kind") is None:
            reason = (rule or {}).get("reason", "missing_fields")
            excluded[reason] = excluded.get(reason, 0) + 1
            cov[dim]["excluded"] += 1
            excluded_detail.append({"judgment_id": jid, "dimension": dim, "reason": reason})
            continue
        w = int(dim_windows.get(dim, window))
        a, b = parties[0], parties[1]
        if rule["kind"] == "rc":
            v = _rc_truth(rc, rule["rc_dim"], a, b, int(r0), w)
            lab = None if v is None else (rule["pos"] if v == "pos" else rule["neg"])
            reason = "no_rc_event_in_window"
        else:  # offer
            v = _offer_truth(acc, rej, a, b, int(r0), w)
            lab = None if v is None else (rule["pos"] if v == "pos" else rule["neg"])
            reason = "no_offer_event_in_window"
        if lab is None:
            excluded[reason] = excluded.get(reason, 0) + 1
            cov[dim]["excluded"] += 1
            excluded_detail.append({"judgment_id": jid, "dimension": dim, "reason": reason})
        else:
            labels[jid] = lab
            cov[dim]["included"] += 1

    return {
        "window_default": int(window),
        "dim_windows": {k: int(v) for k, v in sorted(dim_windows.items())},
        "labels": {k: labels[k] for k in sorted(labels)},
        "excluded_by_reason": {k: excluded[k] for k in sorted(excluded)},
        "coverage": {k: cov[k] for k in sorted(cov)},
        "excluded_detail": excluded_detail,
        "human_sample": human_sample(list(labels)),
        "rules": {k: rules[k] for k in sorted(rules)},
    }


def correct_from_truth(pairs, labels) -> tuple:
    """把 `(pairs, truth.labels)` 折成 `correct` 布尔序列（仅**有真值**的样本，保持 pairs 顺序）。"""
    pred = []
    corr = []
    for pair in pairs:
        jid = pair.get("judgment_id")
        if jid in labels and pair.get("predicted_label") is not None:
            pred.append(jid)
            corr.append(bool(pair["predicted_label"] == labels[jid]))
    return pred, corr


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="obs.truth_from_consequences",
                                 description="由日志反推 judge 请求的确定性后果真值")
    ap.add_argument("--log", required=True, help="运行日志 jsonl")
    ap.add_argument("--pairs", required=True, help="配对 JSONL（judgment_id/dimension/parties/round[/predicted_label]）")
    ap.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    recs = [json.loads(l) for l in open(a.log, encoding="utf-8") if l.strip()]
    pairs = [json.loads(l) for l in open(a.pairs, encoding="utf-8") if l.strip()]
    rep = truth_from_consequences(recs, pairs, window=a.window)
    txt = json.dumps(rep, ensure_ascii=False, indent=2, sort_keys=True)
    if a.out:
        Path(a.out).write_text(txt + "\n", encoding="utf-8")
        print(f"written: {a.out}")
    print(f"labels={len(rep['labels'])} excluded={sum(rep['excluded_by_reason'].values())} "
          f"human_sample={len(rep['human_sample'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
