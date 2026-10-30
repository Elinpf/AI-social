"""同场偶遇搭话（encounter chat）读数器 —— **纯只读 / 确定性 / 零 LLM / 零跑批**。

    cd code && python -m life.encounter_metrics <run.jsonl> [--expect-s2 1060/2400] [--check-arrivals]

## 两套口径，**并列呈现、互不替代**（引用时不许混）

| 口径 | 定义 | 是否预登记 | 能不能用来判定 |
|---|---|---|---|
| **S2_full** | R23 §1.2 的 S-2 原口径：全部（含夜）对×slot-cell 细胞中两居民重建地点相同的对数之和 ÷ `C(n,2)×全部slot细胞` | **是**（`R23:109`） | **能**（唯一可判定口径） |
| **S2d**（本文件新造） | 派生值：同上，但只看**日间槽**（`morning`/`afternoon`/`evening`），分母同步剔夜 `C(n,2)×日间slot细胞` | **否**（`R23:109` 明写禁止替代 44.17%） | **不能**，只作描述 |

`R23:109` 原文纪律：「该式不是预登记口径（口径卡分母恒为 2400），**不得替代表内 44.17%，不得据此改判**」。
因此本文件**同时**输出 `S2_full=1060/2400=44.17%` 与派生值 `S2d=460/1800=25.56%`，并逐字段标 `*_preregistered`。
`tools/f9/group_presence_metrics.py`（剔 `place=residence`、单位是三元组/人-槽）与
`tools/solitude/solitude_metrics.py:511`（只算伪影占比、不产出剔除版分母）**都不是本口径**，不可互换。

## 「460」的来路（两条路径，数值同一、路径不同）

- 路径 A（`R23:109` 的算术）：`S2_full 分子 − residence∧night 同场对 = 1060 − 600 = 460`。
- 路径 B（**本文件实际实现**）：按 **slot 过滤**——只累计非 `night` 槽的同场对，得 460。
- 两者相等的**前提**是「`night` ∧ 非 `residence` 的同场对 = 0」。本文件把这一类**显式计数**为
  `S2_night_nonresidence_num`（本批 = 0）；**若某批该值 > 0，两条路径会不相等**，届时以路径 B 为准，
  并在报告里同步该计数，不得用路径 A 的减法凑数。

## 在场重建规则（S2_full / S2d 共用，唯一实现 `_cells`）

1. 每个 `(day, slot, agent)` 细胞取该细胞内 `ACTIVITY_STARTED.place` 为重建地点（同 `R23 §1.3` 第 1 条）；
   没有 `ACTIVITY_STARTED` 的细胞记「无地点读数」，**不参与**同场判定、**不从分母剔除**。
2. `PLACE_ARRIVED.place` 只用于一致性校验（`--check-arrivals`），不改写地点。
3. 不插值、不估算 `travel_ticks` 窗口（与 R23 同源的有界误差）。

## 指标定义

| 代号 | 定义 | 单位 |
|---|---|---|
| **S2_full_num / S2_full_denom** | R23 S-2 原口径分子 / 分母（本批 `C(16,2)=120 × 20 = 2400`） | 对-时段 |
| **S2d_num** | 非 `night` 槽的同场对数（= 可作用池大小；**这是 E-1 的分母**） | 对-时段 |
| **S2d_denom** | `C(n,2) × 日间 slot 细胞数`（本批 `120 × 15 = 1800`；15 = 5 天 × `morning/afternoon/evening`） | 对-时段 |
| **E1_num** | 由 `ctx.trigger == "encounter"` 的 `MSG_DM` 反推的 `(day,slot,无向对)` **去重个数** | 对-时段 |
| **E1_over_S2d_bp** | `10000 × E1_num / S2d_num`（分母是 **S2d 分子**＝可作用池，非预登记派生） | bp |
| **E1_over_S2_full_bp** | `10000 × E1_num / S2_full_denom`（全池口径，非预登记派生） | bp |
| **E1msg** | `ctx.trigger == "encounter"` 的 `MSG_DM` **条数**（同一对-时段可能多条） | 条 |

纪律：E-1 的分子**必须**来自日志落盘的 `ctx.trigger`，不得由「本臂一定会发」反推；
OFF 臂 `ctx.trigger` 里不会出现 `encounter`（基线实测 0/455）。
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict

ENCOUNTER_TRIGGER = "encounter"
NIGHT_SLOT = "night"

#: R23 冻结口径常数（只用于自检，不参与计算）
R23_DENOMINATOR = 2400
R23_S2_NUMERATOR = 1060


def load(path: str) -> list:
    """按行读 `run.jsonl`（每行一个事件）。空行跳过。"""
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _payload(rec: dict) -> dict:
    return rec.get("payload") or {}


def _cells(records: list) -> tuple:
    """返回 (cells, agents, slot_cells, arrivals)。

    cells:      {(day, slot): {agent: place|None}}
    agents:     本批出现过的 agent 集合（由 `ACTIVITY_STARTED.agent_id` 收）
    slot_cells: 出现过的 (day, slot) 集合
    arrivals:   {(day, slot, agent): place}（`PLACE_ARRIVED`，仅作一致性校验）
    """
    cells: dict = defaultdict(dict)
    agents: set = set()
    arrivals: dict = {}
    for rec in records:
        t = rec.get("type")
        p = _payload(rec)
        day, slot = p.get("day"), p.get("slot")
        if day is None or slot is None:
            continue
        if t == "ACTIVITY_STARTED":
            aid = p.get("agent_id")
            if aid is None:
                continue
            agents.add(aid)
            cells[(int(day), slot)].setdefault(aid, p.get("place"))
        elif t == "PLACE_ARRIVED":
            aid = p.get("agent_id")
            if aid is None:
                continue
            arrivals[(int(day), slot, aid)] = p.get("place")
    return cells, agents, set(cells), arrivals


def s2_readings(records: list) -> dict:
    """S2_full / S2d / E-1 的全部读数（一次遍历，口径唯一、字段不二义）。"""
    cells, agents, slot_cells, arrivals = _cells(records)
    n = len(agents)
    pairs_per_cell = n * (n - 1) // 2 if n >= 2 else 0
    day_slot_cells = {c for c in slot_cells if c[1] != NIGHT_SLOT}

    s2_full_num = 0          # 预登记口径（全池，含夜）
    s2d_num = 0              # 派生口径（日间槽；路径 B：按 slot 过滤）
    s2_night_num = 0         # 夜里同场对（显式拆开，杜绝「未声明的第三类吞掉项」）
    s2_night_residence = 0
    s2_night_nonresidence = 0

    for (day, slot), places in sorted(cells.items()):
        ids = sorted(places)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                pa = places.get(ids[i])
                pb = places.get(ids[j])
                if pa is None or pb is None or pa != pb:
                    continue
                s2_full_num += 1
                if slot == NIGHT_SLOT:
                    s2_night_num += 1
                    if pa == "residence":
                        s2_night_residence += 1
                    else:
                        s2_night_nonresidence += 1
                else:
                    s2d_num += 1

    s2_full_denom = pairs_per_cell * len(slot_cells)
    s2d_denom = pairs_per_cell * len(day_slot_cells)

    # 一致性校验：重建地点与 PLACE_ARRIVED 不符的细胞（只报数，不改写）
    mismatch = []
    for (day, slot), places in cells.items():
        for aid, place in places.items():
            arr = arrivals.get((day, slot, aid))
            if arr is not None and place is not None and arr != place:
                mismatch.append({"day": day, "slot": slot, "agent": aid,
                                 "activity_place": place, "arrived_place": arr})
    started = Counter()
    for rec in records:
        p = _payload(rec)
        if rec.get("type") == "ACTIVITY_STARTED" and p.get("agent_id") and p.get("day") is not None:
            started[(int(p["day"]), p.get("slot"), p["agent_id"])] += 1
    multi_started = sum(1 for v in started.values() if v > 1)

    # ---- E-1：由日志落盘的 ctx.trigger 反推 ----
    trig = Counter()
    enc_pairs: set = set()
    enc_msgs = 0
    for rec in records:
        if rec.get("type") != "MSG_DM":
            continue
        p = _payload(rec)
        ctx = p.get("ctx") or {}
        t = ctx.get("trigger") or "(none)"
        trig[t] += 1
        if t != ENCOUNTER_TRIGGER:
            continue
        enc_msgs += 1
        day, slot = p.get("day"), p.get("slot")
        frm = p.get("from") or rec.get("actor")
        to = p.get("to")
        if day is None or slot is None or not frm or not to:
            continue
        enc_pairs.add((int(day), slot, tuple(sorted([frm, to]))))

    def _bp(num, den):
        return round(10000.0 * num / den, 2) if den else None

    return {
        "agents": n,
        "slot_cells": len(slot_cells),
        "day_slot_cells": len(day_slot_cells),
        "pairs_per_cell": pairs_per_cell,
        # ---- 预登记口径（唯一可判定）----
        "S2_full": f"{s2_full_num}/{s2_full_denom}",
        "S2_full_num": s2_full_num,
        "S2_full_denom": s2_full_denom,
        "S2_full_pct": round(100.0 * s2_full_num / s2_full_denom, 2) if s2_full_denom else None,
        "S2_full_preregistered": True,
        # ---- 夜里同场对拆解（伪影可见化）----
        "S2_night_num": s2_night_num,
        "S2_night_residence_num": s2_night_residence,
        "S2_night_nonresidence_num": s2_night_nonresidence,
        "night_share_of_denom_pct": round(
            100.0 * pairs_per_cell * (len(slot_cells) - len(day_slot_cells)) / s2_full_denom, 2
        ) if s2_full_denom else None,
        "night_share_of_num_pct": round(100.0 * s2_night_num / s2_full_num, 2) if s2_full_num else None,
        # ---- 派生口径（非预登记，只描述）----
        "S2d_num": s2d_num,
        "S2d_denom": s2d_denom,
        "S2d": f"{s2d_num}/{s2d_denom}",
        "S2d_pct": round(100.0 * s2d_num / s2d_denom, 2) if s2d_denom else None,
        "S2d_preregistered": False,
        "S2d_derivation": "path_B: 按 slot != 'night' 过滤累计（与 R23:109 的 1060-600 同值不同路径；"
                          "两者相等的前提是 S2_night_nonresidence_num == 0）",
        # ---- E-1：同场 → 搭话 ----
        "E1msg": enc_msgs,
        "E1_num": len(enc_pairs),
        "E1_over_S2d_bp": _bp(len(enc_pairs), s2d_num),
        "E1_over_S2_full_bp": _bp(len(enc_pairs), s2_full_denom),
        "E1_over_S2d_note": "分母 = S2d_num（可作用池大小），**非预登记派生**，只描述不判改",
        "E1_over_S2_full_note": "分母 = S2_full_denom（全池 2400），**非预登记派生**，只描述不判改",
        "encounter_cells": sorted([f"{d}|{s}|{a}-{b}" for (d, s, (a, b)) in enc_pairs]),
        "msg_dm_trigger_census": dict(sorted(trig.items())),
        # ---- 校验项 ----
        "S1_mismatch_cells": len(mismatch),
        "S1_mismatch_sample": mismatch[:5],
        "multi_started_cells": multi_started,
    }


def channel_census(records: list) -> dict:
    """消息通道普查（代价项：偶遇臂只应**新增** MSG_DM，不应改变模板通道的既有基数）。"""
    cnt = Counter(rec.get("type") for rec in records if str(rec.get("type", "")).startswith("MSG_"))
    return dict(sorted(cnt.items()))


def main(argv: list) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    path = argv[1]
    expect = None
    check_arrivals = "--check-arrivals" in argv
    for i, a in enumerate(argv):
        if a == "--expect-s2" and i + 1 < len(argv):
            num, _, den = argv[i + 1].partition("/")
            expect = (int(num), int(den))
    records = load(path)
    r = s2_readings(records)
    r["msg_channel_census"] = channel_census(records)
    r["source"] = path
    r["records"] = len(records)
    if not check_arrivals:
        r.pop("S1_mismatch_sample", None)
    print(json.dumps(r, ensure_ascii=False, indent=2, sort_keys=True))
    if expect is not None:
        ok = (r["S2_full_num"], r["S2_full_denom"]) == expect
        print(f"[selfcheck] S2_full={r['S2_full']} expect={expect[0]}/{expect[1]} -> "
              f"{'OK' if ok else 'MISMATCH'}", file=sys.stderr)
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
