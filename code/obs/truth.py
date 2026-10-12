"""「确定性后果」真值（M2b 校准的 ground truth）—— 纯函数、只读、确定性。

**为什么需要它**：ECE 要求置信度能预测**正确**，而**生成式 A 的标签不是真值**。
拿 A 当答案只能测「两模式像不像」（`agreement_rate`），**测不出校准**。
本模块给每条 `LLM_JUDGMENT` 一个**由其后确定性后果导出**的真值（或判定为**无法定义**）。

**口径（提案，逐条标【未验证】）**：对每个 `LLM_JUDGMENT`（`parties=[A,T]`、`dimension`、`created_round=r`），
在**后续窗口** `(r, r+W]` 内查**确定性事件**（不调 LLM）：

| dimension | 预测选项 | 确定性后果（真值） | 状态 |
|---|---|---|---|
| `stance` | accept/reject | 该对 `RELATION_CHANGE`（dim∈{affinity,trust,respect}）**净变化符号**：accept⇒净>0、reject⇒净<0；无事件→**无法定义** | 提案 |
| `respect` | high/low | `RELATION_CHANGE{dim=respect}` 净符号（high⇒>0, low⇒<0） | 【未验证】 |
| `rel_trust` | （同 respect 式） | `RELATION_CHANGE{dim=trust}` 净符号 | 【未验证】 |
| `rel_affinity` | formed/not_formed | 窗口内 `RELATION_CHANGE{dim=affinity}.after ≥ THRESH_A` 是否成立 | 【未验证】 |
| `rel_familiarity` | formed/not_formed | 同上，`dim=familiarity`，`THRESH_F` | 【未验证】 |
| `affection` | high/low | **无对应关系维 → 无法定义**【未验证】 | 不覆盖 |
| `weekly_focus` | work/social/… | **无确定性后果 → 无法定义** | 不覆盖 |

**约束**：只读、确定性（无随机/时钟）；窗口/阈值均为**显式参数**；**无法定义的样本如实标 None 并计数**，不凑数。
所有语义映射均为**提案**，有效性**待人工抽样核验**（【未验证】）。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

__all__ = ["truth_from_consequences"]

_REL_DIMS_STANCE = ("affinity", "trust", "respect")
_FORMED_THRESH = {"affinity": 3, "familiarity": 12}  # 【未验证】提案阈值（=观测到的常见档位）


def _pair(a, b):
    return tuple(sorted([str(a), str(b)]))


def truth_from_consequences(records, window: int = 12,
                            afford_thresh: int | None = None,
                            familiarity_thresh: int | None = None) -> dict:
    """返回 `{"by_judgment_id": {...}, "coverage": {...}}`。

    每条：`{dimension, parties, decided_round, log_decision, true_label|None, defined, reason, evidence_round}`
    `true_label` 为 None ⇒ **无法定义**（下游须剔除，不得当 False）。
    """
    thresh_a = _FORMED_THRESH["affinity"] if afford_thresh is None else int(afford_thresh)
    thresh_f = _FORMED_THRESH["familiarity"] if familiarity_thresh is None else int(familiarity_thresh)

    # 索引 RELATION_CHANGE：{pair: {dim: [(round, delta)]}}
    rc = {}
    for r in records:
        if r.get("type") != "RELATION_CHANGE":
            continue
        p = r.get("payload") or {}
        f, t, d = p.get("from"), p.get("to"), p.get("dim")
        if f is None or t is None or d is None:
            continue
        try:
            delta = int(p.get("after", 0)) - int(p.get("before", 0))
            after = int(p.get("after", 0))
        except (TypeError, ValueError):
            continue
        rc.setdefault(_pair(f, t), {}).setdefault(d, []).append((int(r.get("round", 0)), delta, after))

    by = {}
    cov = {}
    for r in records:
        if r.get("type") != "LLM_JUDGMENT":
            continue
        p = r.get("payload") or {}
        jid = p.get("judgment_id")
        dim = p.get("dimension")
        parties = p.get("parties") or []
        if jid is None or dim is None or len(parties) != 2:
            continue
        rr = int(p.get("created_round", r.get("round", 0)))
        pr = _pair(parties[0], parties[1])
        win = [ev for evs in (rc.get(pr, {}) or {}).values()
               for ev in evs if rr < ev[0] <= rr + window]

        # 按维度取窗口内净变化
        def _net_dims(dims):
            total = 0
            for d in dims:
                for (_rd, dd, _a) in rc.get(pr, {}).get(d, []):
                    if rr < _rd <= rr + window:
                        total += dd
            return total

        true_label = None
        reason = ""
        ev_round = None
        if dim == "stance":
            dec = str(p.get("decision", "")).lower()
            net = _net_dims(_REL_DIMS_STANCE)
            if not win:
                reason = "no_consequence_in_window"
            elif net == 0:
                reason = "net_zero_ambiguous"
            else:
                true_label = "accept" if net > 0 else "reject"
                reason = "tie_net_sign"
        elif dim == "respect":
            net = _net_dims(("respect",))
            if net == 0:
                reason = "no_or_zero_respect_change"
            else:
                true_label = "high" if net > 0 else "low"
                reason = "respect_net_sign"
        elif dim == "rel_trust":
            net = _net_dims(("trust",))
            if net == 0:
                reason = "no_or_zero_trust_change"
            else:
                true_label = "high" if net > 0 else "low"
                reason = "trust_net_sign"
        elif dim in ("rel_affinity", "rel_familiarity"):
            d = "affinity" if dim == "rel_affinity" else "familiarity"
            th = thresh_a if d == "affinity" else thresh_f
            after = [a for (_rd, _dd, a) in rc.get(pr, {}).get(d, []) if rr < _rd <= rr + window]
            if not after:
                reason = "no_%s_change_in_window" % d
            else:
                true_label = "formed" if max(after) >= th else "not_formed"
                reason = "%s_after>=%d" % (d, th)
        else:
            reason = "dimension_uncovered_%s" % dim  # affection / weekly_focus / ...

        defined = true_label is not None
        by[jid] = {
            "judgment_id": jid, "dimension": dim, "parties": list(pr),
            "decided_round": rr, "log_decision": p.get("decision"),
            "true_label": true_label, "defined": defined, "reason": reason,
        }
        c = cov.setdefault(dim, {"n": 0, "defined": 0, "undefined": 0})
        c["n"] += 1
        c["defined" if defined else "undefined"] += 1

    return {"by_judgment_id": by, "coverage": {k: cov[k] for k in sorted(cov)},
            "params": {"window": window, "affinity_formed_thresh": thresh_a,
                       "familiarity_formed_thresh": thresh_f}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="obs.truth",
                                 description="确定性后果真值（提案口径，只读）")
    ap.add_argument("--log", required=True)
    ap.add_argument("--window", type=int, default=12)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    recs = [json.loads(l) for l in open(a.log, encoding="utf-8")]
    out = truth_from_consequences(recs, window=a.window)
    txt = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True)
    if a.out:
        Path(a.out).write_text(txt + "\n", encoding="utf-8")
        print(f"written: {a.out}")
    print(json.dumps(out["coverage"], ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
