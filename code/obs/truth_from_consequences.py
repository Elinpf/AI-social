"""「确定性后果」真值口径 —— **单一真源**（T257 合并；`obs/truth.py` 已废弃并入）。

**只读日志、纯函数、确定性**（无随机/无时钟）。**不把生成式 A 的标签当正确答案**：
用**判定之后的确定性后果事件**（不需 LLM）反推 TRUE_label。

**口径权威 = 08 §4.x「确定性后果真值」（行 440，sim-engine-stats-architect 裁定）**：

| 维度族（`life/constants.py::JUDGMENT_OPTIONS`） | 后果事件 | TRUE_label | 无事件 |
|---|---|---|---|
| `rel_affinity`/`rel_familiarity`/`rel_trust`/`rel_respect`/`mentor_relation`（`formed`/`not_formed`） | 窗口内 `RELATION_CHANGE{dim}.after` | **`max(after) ≥ θ_dim` ⇒ `formed`；有事件但均 `<θ` ⇒ `not_formed`** | **undecidable（剔除）** |
| `respect`（`high`/`low`） | 同上（`dim=respect`） | `after ≥ θ_respect` ⇒ `high` 否则 `low` | 剔除 |
| `stance`（`accept`/`reject`） | **行为性** `OFFER_ACCEPTED`/`OFFER_REJECTED`（`by=a` 且 creator=b） | accept⇒`accept`；reject⇒`reject` | 剔除 |
| `affection` / `weekly_focus` / `importance` | —— | **无干净后果 ⇒ 剔除** | 剔除 |

**词表（依 `JUDGMENT_OPTIONS`，唯一权威）**：`rel_*`/`mentor_relation` 用 **`formed`/`not_formed`**；
`respect`/`affection` 用 **`high`/`low`**；**`respect` 与 `rel_respect` 不得归一**（不同维族）。

**三条硬约束（Leader 批准）**：
  (a) **窗口 W 参数化**（默认 12 回合 ≈ 1 仿真日；`dim_windows` 按维覆盖）；
  (b) **θ 参数化**（默认 ε=20，可 `dim_thresholds` 按维覆盖【待标定】）；
  (c) **被剔除样本按维计数并单列**；**人工核抽样规则确定**（`judgment_id` 升序等距 ≤20）。

**口径变更声明（T257）**：旧 `obs/truth.py` 的 `Δ>0`、`rel_trust→high/low`、`stance=关系净符号`
已被 08 弃用；本模块并入后**在变更处输出随之变**（"逐字节不变"只在**合并机制**层成立，跨口径不成立）。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

__all__ = [
    "CONSEQUENCE_RULES", "DEFAULT_WINDOW", "DEFAULT_THETA", "truth_from_consequences",
    "correct_from_truth", "human_sample",
]

DEFAULT_WINDOW = 12   # 回合
DEFAULT_THETA = 20    # ε（06/07 弱边阈）；按维可覆盖，【待标定】

# value = (kind, param)；kind="rc"→关系维; kind="offer"→offers; kind=None→剔除
CONSEQUENCE_RULES = {
    "rel_affinity":    {"kind": "rc", "rc_dim": "affinity",    "pos": "formed", "neg": "not_formed"},
    "rel_familiarity": {"kind": "rc", "rc_dim": "familiarity", "pos": "formed", "neg": "not_formed"},
    "rel_trust":       {"kind": "rc", "rc_dim": "trust",       "pos": "formed", "neg": "not_formed"},
    "rel_respect":     {"kind": "rc", "rc_dim": "respect",     "pos": "formed", "neg": "not_formed"},
    "mentor_relation": {"kind": "rc", "rc_dim": "mentor_relation", "pos": "formed", "neg": "not_formed"},
    "respect":         {"kind": "rc", "rc_dim": "respect",     "pos": "high", "neg": "low"},
    "stance":          {"kind": "offer", "pos": "accept", "neg": "reject"},
    "affection":       {"kind": None, "reason": "no_affection_consequence(剔除)"},
    "weekly_focus":    {"kind": None, "reason": "no_clean_consequence(剔除)"},
    "importance":      {"kind": None, "reason": "no_consequence(剔除)"},
}


def _p(r):
    return r.get("payload") or {}


def _pair(a, b):
    return tuple(sorted([str(a), str(b)]))


def _offer_creator(offer_id):
    """从 offer_id 取创建者：`O-<r>-<creator>[...]` → 第 3 段。"""
    if not offer_id:
        return None
    parts = str(offer_id).split("-")
    return parts[2] if len(parts) >= 3 else None


def _index(records):
    """建索引：关系变化 / 成交接受 / 拒绝 / 判定轮次。"""
    rc = []            # (round, pair, dim, after)
    acc, rej = [], []  # (round, by, creator)
    jround = {}
    for r in records:
        t = r["type"]
        p = _p(r)
        if t == "RELATION_CHANGE":
            f, to, d = p.get("from"), p.get("to"), p.get("dim")
            if f is None or to is None or d is None:
                continue
            try:
                after = int(p.get("after", 0))
            except (TypeError, ValueError):
                continue
            rc.append((int(r.get("round", 0)), _pair(f, to), d, after))
        elif t == "OFFER_ACCEPTED":
            acc.append((int(r.get("round", 0)), p.get("by"), _offer_creator(p.get("offer_id"))))
        elif t == "OFFER_REJECTED":
            rej.append((int(r.get("round", 0)), p.get("by"), _offer_creator(p.get("offer_id"))))
        elif t == "LLM_JUDGMENT":
            jid = p.get("judgment_id")
            if jid is not None:
                jround[jid] = int(r.get("round", 0))
    return rc, acc, rej, jround


def _rc_label(rc, rc_dim, pair, r0, w):
    """窗口 `(r0, r0+w]` 内 (pair, rc_dim) 的 `after` 列表；无事件→None。"""
    after = [a for (r, pr, d, a) in rc if d == rc_dim and pr == pair and r0 < r <= r0 + w]
    return after if after else None


def _offer_label(acc, rej, a, b, r0, w):
    """窗口内 `by=a` 且 creator=b：有 accept→pos，有 reject→neg，皆无→None（accept 优先）。"""
    if any(r0 < r <= r0 + w for (r, by, cr) in acc if by == a and cr == b):
        return "pos"
    if any(r0 < r <= r0 + w for (r, by, cr) in rej if by == a and cr == b):
        return "neg"
    return None


def human_sample(judgment_ids, cap=20):
    """确定性人工核抽样：按 id 升序、等距取 ≤cap 条。"""
    ids = sorted(judgment_ids)
    n = len(ids)
    if n == 0:
        return []
    return ids[:: max(1, n // cap)][:cap]


def truth_from_consequences(records, pairs, window=DEFAULT_WINDOW, dim_windows=None,
                            rules=None, dim_thresholds=None) -> dict:
    """由日志反推每条 judge 请求的 TRUE_label（见模块 docstring 的 08 口径表）。

    `pairs`: `{judgment_id, dimension, parties:[a,b], round?}`（round 缺失则从日志反查）。
    返回 `{labels, excluded_by_reason, coverage, excluded_detail, human_sample, rules, params}`。
    """
    rules = dict(CONSEQUENCE_RULES if rules is None else rules)
    dim_windows = dim_windows or {}
    dim_thresholds = dim_thresholds or {}
    rc, acc, rej, jround = _index(records)

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
        a, b = str(parties[0]), str(parties[1])
        pr = _pair(a, b)
        theta = int(dim_thresholds.get(dim, DEFAULT_THETA))

        if rule["kind"] == "rc":
            after = _rc_label(rc, rule["rc_dim"], pr, int(r0), w)
            if after is None:
                lab, reason = None, "no_rc_event_in_window"
            else:
                lab = rule["pos"] if max(after) >= theta else rule["neg"]
                reason = "after>=%d" % theta
        else:  # offer
            v = _offer_label(acc, rej, a, b, int(r0), w)
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
        "theta_default": int(DEFAULT_THETA),
        "dim_windows": {k: int(v) for k, v in sorted(dim_windows.items())},
        "dim_thresholds": {k: int(v) for k, v in sorted(dim_thresholds.items())},
        "labels": {k: labels[k] for k in sorted(labels)},
        "excluded_by_reason": {k: excluded[k] for k in sorted(excluded)},
        "coverage": {k: cov[k] for k in sorted(cov)},
        "excluded_detail": excluded_detail,
        "human_sample": human_sample(list(labels)),
        "rules": {k: rules[k] for k in sorted(rules)},
    }


def correct_from_truth(pairs, labels) -> tuple:
    """折成 `correct` 布尔序列（仅**有真值**的样本，保持 pairs 顺序）。"""
    pred, corr = [], []
    for pair in pairs:
        jid = pair.get("judgment_id")
        if jid in labels and pair.get("predicted_label") is not None:
            pred.append(jid)
            corr.append(bool(pair["predicted_label"] == labels[jid]))
    return pred, corr


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="obs.truth_from_consequences",
                                 description="确定性后果真值（08 口径，只读，单一真源）")
    ap.add_argument("--log", required=True)
    ap.add_argument("--pairs", required=True)
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
