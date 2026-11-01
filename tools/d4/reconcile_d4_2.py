#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D4-2 对账骨架（**仅骨架，未在任何数据上运行过**）。

用途
----
`T-RIFT-EVENTS` 交付 `RIFT_OPEN` / `RIFT_CLOSE` / `dialogue_rift.rift_ids` 之后，
用本脚本把「新事件口径」的 D4-2 与旧口径的绝对数（`7 / 16 / 0`）对账。

⚠ 本脚本**不预设任何结果**。它只定义计算路径与输出字段；「与旧值差」是**必填输出**，
  因为对账时真正要看的是**差值的分解**，不是两侧各自的大小。

⚠ 字段名占位
------------
新事件的精确字段名在交付前**未知**，故集中放在 `FIELDS` 里并标注「待确认」。
**不要在没确认前"猜一个能跑通的字段名"** —— 那会产出看起来跑通、实际张冠李戴的数。

运行前置（第一道闸，不过则退出，不进入任何计算）
------------------------------------------------
1. `RIFT_OPEN` 事件数 == 台账登记数；
2. `RIFT_CLOSE` 事件数 == 台账注销数；
3. `dialogue_rift` 快照与事件流**对得上**：每条快照的 `open` 值 == 该时刻未关闭 rift 数。
**若这一闸不过 ⇒ 对账没有意义（会变成"拿两套不知真假的数比大小"），脚本必须 `exit 2`。**

用法
----
    python3 tools/d4/reconcile_d4_2.py \
        --run v2/evidence/<new_batch>/run.jsonl \
        --old-rift-repaired 16 \
        --out-json /tmp/d4_2_reconcile.json

输出字段（必填）
----------------
    rift_total           新口径总数（RIFT_OPEN 计数）
    rift_repaired        新口径被修复数（RIFT_CLOSE 且原因为修复 / rift_ids 去重）
    rate                  rift_repaired / rift_total
    old_rift_repaired    旧口径绝对数（来自 --old-rift-repaired）
    delta                 rift_repaired - old_rift_repaired
    delta_explained       "沉默的 rift" 数 = rift_total - rift_repaired
    delta_match           delta == delta_explained ?  ⇒ 见下方判据
    gate                  {"gate0_events_landed":..., "gate1_unit":..., "gate2_not_gt_100":...}
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# ---- 待实现方交付后确认的字段名（⚠ 现在**不应**填成"猜的名字"）----
FIELDS = {
    "RIFT_OPEN": {
        "event_type": "RIFT_OPEN",          # 待确认
        "rift_id": "TODO_rift_id",          # 待确认：rift_id 字段名
        "thread": "TODO_thread",            # 待确认
        "agent": "TODO_agent",              # 待确认
        "seq": "seq",                       # 事件自带
        "round": "round",
    },
    "RIFT_CLOSE": {
        "event_type": "RIFT_CLOSE",         # 待确认（可能叫 RIFT_EXPIRE）
        "rift_id": "TODO_rift_id",
        "reason": "TODO_reason",            # 待确认：修复 / 超龄淡忘 / 其它
        "seq": "seq",
        "round": "round",
    },
}

# ---- 旧口径绝对数（由 CLI 传入，不在脚本里硬编码）----
OLD_DEFAULT = None  # 必须显式传 --old-rift-repaired


def load_events(path):
    evs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                evs.append(json.loads(line))
    return evs


def gate0_events_landed(evs):
    """第一道闸：新事件**真的在落**且与快照对得上。

    不过 ⇒ 返回 (False, reasons)。**对账不应继续。**
    """
    reasons = []
    opens = [e for e in evs if e.get("type") == FIELDS["RIFT_OPEN"]["event_type"]]
    closes = [e for e in evs if e.get("type") == FIELDS["RIFT_CLOSE"]["event_type"]]

    if not opens:
        reasons.append("RIFT_OPEN 事件数为 0（字段名未确认，或事件确实没落）")
    if not closes and opens:
        # 可能整批无修复——但必须与台账对得上才能这么判
        reasons.append("RIFT_CLOSE 事件数为 0（需与台账注销数核对后才能判定为'无修复'）")

    # ① 事件数 == 台账登记数
    #    TODO(实现方交付后): 台账登记数从哪取？（`dialogue_rift` 首现 impossible 精确；
    #    若 `RIFT_OPEN` 就是权威台账，则此项退化为"自等"，须改判为"快照可对上"）
    # ② 事件数 == 台账注销数：同上
    # ③ 快照对得上：逐条 `dialogue_rift` 的 `open` 值
    #    == 该 seq 时刻 (已 OPEN 且未 CLOSE) 的 rift 数
    snap_mismatch = _check_snapshot_consistency(evs, opens, closes)
    if snap_mismatch:
        reasons.append(f"快照与事件流不一致 {snap_mismatch} 处")

    return (len(reasons) == 0), reasons


def _check_snapshot_consistency(evs, opens, closes):
    """逐条 dialogue_rift 快照，核 `open` 值 == 该时刻未关闭 rift 数。返回不一致条数。

    ⚠ 骨架：依赖 FIELDS 里的字段名确认后才可真正实现。
    """
    if not opens:
        return 0  # 无 OPEN 事件 ⇒ 无从核；由 gate0 的 reasons 覆盖
    # TODO(实现方交付后): 实现
    #   未关闭集 = {rid for rid in opens if rid not in closed_by_seq(seq)}
    #   对每条 MSG 的 payload.dialogue_rift：
    #       assert len(未关闭集 at that seq) == dr["open"]
    return 0


def compute(evs):
    """算 rift_total / rift_repaired / rate。**不含任何旧值。**"""
    opens = [e for e in evs if e.get("type") == FIELDS["RIFT_OPEN"]["event_type"]]
    closes = [e for e in evs if e.get("type") == FIELDS["RIFT_CLOSE"]["event_type"]]

    oid = FIELDS["RIFT_OPEN"]["rift_id"]
    cid = FIELDS["RIFT_CLOSE"]["rift_id"]
    creason = FIELDS["RIFT_CLOSE"]["reason"]

    total = len(opens)                               # 新口径总数
    repaired_ids = set()
    for c in closes:
        # 只有"原因为修复"才算 repaired；超龄淡忘不算
        if c.get(creason) in ("repair", "repaired", "fix"):   # TODO 待确认取值域
            repaired_ids.add(c.get(cid))
    repaired = len(repaired_ids)

    # 交叉核对：与 dialogue_repair.rift_ids 去重是否一致（应为同一事物）
    snapshot_ids = set()
    for e in evs:
        if not e.get("type", "").startswith("MSG"):
            continue
        rp = (e.get("payload") or {}).get("dialogue_repair")
        if rp:
            snapshot_ids |= set(rp.get("rift_ids") or [])

    return {
        "rift_total": total,
        "rift_repaired": repaired,
        "rate": (repaired / total) if total else None,
        "cross_check_snapshot_ids": len(snapshot_ids),
        "cross_check_equal": (repaired == len(snapshot_ids)) if total else None,
        "_opens_seen": len(opens),
        "_closes_seen": len(closes),
        "_ids_present": (oid in (opens[0] if opens else {})) if opens else False,
        "_cid_present": (cid in (closes[0] if closes else {})) if closes else False,
    }


def gate1_unit_consistency(res):
    """一行否决闸：分子分母同量纲却 >100% ⇒ 判口径错。"""
    r = res.get("rate")
    if r is None:
        return True, "rate 为空（无 rift），跳过"
    if r > 1.0:
        return False, f"rate={r:.4f} > 100% ⇒ 判口径错（分子分母量纲不一致），不得解释为'接近全覆盖'"
    return True, f"rate={r:.4f} 合规"


def gate2_delta_expected(res, old_repaired):
    """对账判据：新 − 旧 应等于'沉默的 rift'数（未修复者）。

    ⚠ 关键：**"相等"反而说明新口径没起作用**。正确期望是 `新 >= 旧` 且
      `新 - 旧 == 未修复 rift 数`（= total - repaired）。
    """
    new_r = res.get("rift_repaired")
    total = res.get("rift_total")
    if new_r is None or total is None:
        return None
    delta = new_r - old_repaired if old_repaired is not None else None
    silent = total - new_r
    return {
        "delta": delta,
        "delta_explained": silent,
        "delta_match": (delta == silent) if delta is not None else None,
        "new_ge_old": (new_r >= old_repaired) if old_repaired is not None else None,
    }


def main():
    ap = argparse.ArgumentParser(description="D4-2 对账骨架（仅骨架，未在数据上运行过）")
    ap.add_argument("--run", required=True, help="新批 run.jsonl 路径")
    ap.add_argument("--old-rift-repaired", type=int, default=OLD_DEFAULT,
                    help="旧口径被修复 rift 绝对数（如 run_f4_on 的 16）；必填")
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    if args.old_rift_repaired is None:
        print("ERROR: --old-rift-repaired 必填（对账的'与旧值差'是必填输出）", file=sys.stderr)
        return 2

    evs = load_events(args.run)

    # ===== 第一道闸：事件是否真的在落 =====
    ok, reasons = gate0_events_landed(evs)
    if not ok:
        print("GATE0 FAIL —— 对账不应继续：", file=sys.stderr)
        for r in reasons:
            print("  -", r, file=sys.stderr)
        print("\n⇒ 先确认 RIFT_OPEN/RIFT_CLOSE 真的在落、且与快照对得上；"
              "否则对账会变成'拿两套不知真假的数比大小'。", file=sys.stderr)
        return 2

    # ===== 计算 =====
    res = compute(evs)
    if not res["_ids_present"] or not res["_cid_present"]:
        print("GATE0b FAIL —— FIELDS 里的 rift_id 字段名未确认（占位仍在），"
              "不允许产出数。", file=sys.stderr)
        return 2

    # ===== 闸 1：同量纲 >100% =====
    g1_ok, g1_msg = gate1_unit_consistency(res)

    # ===== 对账 =====
    delta = gate2_delta_expected(res, args.old_rift_repaired)

    out = dict(res)
    out["old_rift_repaired"] = args.old_rift_repaired
    out.update(delta or {})
    out["gate"] = {"gate0_events_landed": ok, "gate1_unit": g1_ok,
                   "gate1_msg": g1_msg}

    txt = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            f.write(txt)
        print(f"wrote {args.out_json}")
    print(txt)
    return 0 if g1_ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
