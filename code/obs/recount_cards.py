"""T123 · 事件卡量复算（唯一口径，可复现）。

一条命令：
    cd code
    python -m obs.recount_cards --log ../v2/evidence/run_p1_final_n20_llm.jsonl \
        --out ../v2/evidence/event_card_counts.json

口径（**唯一权威**，与 `frontend/src/audit.js::eventCardSlug` 逐行一致）：
  - 输入：事件日志（JSONL）。**事件类型只取 `e.type`**（本日志 `payload.type` 从不出现）。
  - **一个事件最多出一张卡**；未映射事件不计入。
  - **现行（无门控）卡量**：对 `sprites.js` **原 EVENT_CARDS 的 26 条 type→slug 条目**逐事件计数之和。
    （同一 slug 的多个 type 各计一次——引擎按 `e.type` 逐事件渲染；这正是 **23,185** 的来由。）
  - **门控卡量**：对每个事件求 `gated_slug()`——优先级
    `payload.template ∈ BY_TEMPLATE` → `EVENT_CARDS[type]` → 语义 switch
    （`TRANSFER{gift}` / `DEPOSIT|WITHDRAW` / `STATE_CHANGE{exhausted}` /
     `MARKET_TRADE{scarce_buy 或 scarcity_index≥θ}` / `MSG_DM{private}`）。
  - 旧数 **22,987** =「每 slug 仅取一个 type」变体（少计双 type slugs 的第二项 = 198）→ **废弃**。
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

THETA_SCARCE = 0.5

# (0) 现行无门控映射 = sprites.js 原 EVENT_CARDS（26 条 type 条目）
ORIGINAL_MAPPING = {
    "SKILL_LEVEL_UP": "mentorship", "SKILL_OUTPUT": "academic-collab",
    "ACTIVITY_COMPLETED": "creative-collab", "ACTIVITY_STARTED": "combat-training",
    "TRANSFER": "gift-giving", "DEPOSIT": "saving-money", "WITHDRAW": "saving-money",
    "MSG_DM": "whispered-comm", "NEED_UPDATE": "emotion-burnout", "STATE_CHANGE": "emotion-burnout",
    "SCORE_POSTED": "diff-scoring", "RANKING_EMITTED": "diff-scoring",
    "MARKET_TRADE": "scarcity-buy", "SKILL_PRACTICE": "skill-practice",
    "OFFER_REJECTED": "polite-reject", "ROLE_CHANGE": "passion-salary", "OFFER_CREATED": "passion-salary",
    "NORM_PROPOSED": "group-proposal", "NORM_ADOPTED": "group-proposal",
    "OFFER_COUNTERED": "counter-propose", "PLACE_MOVE": "select-location",
    "CONFLICT_STARTED": "power-conflict", "CONFLICT_RESOLVED": "power-conflict",
    "LLM_JUDGMENT": "rel-acceptance", "RELATION_ENCOUNTER": "ice-breaking",
    "RELATION_CHANGE": "rel-maintain",
}

# (a) 门控：无条件映射（收敛后 7 条）
EVENT_CARDS = {
    "SKILL_PRACTICE": "skill-practice", "OFFER_REJECTED": "polite-reject",
    "ROLE_CHANGE": "passion-salary", "NORM_PROPOSED": "group-proposal",
    "OFFER_COUNTERED": "counter-propose",
    "CONFLICT_STARTED": "power-conflict", "CONFLICT_RESOLVED": "power-conflict",
}
# (b) 门控：活动 template → slug
EVENT_CARDS_BY_TEMPLATE = {
    "mentorship": "mentorship", "creative_collab": "creative-collab",
    "academic_collab": "academic-collab", "combat_training": "combat-training",
    "select_location": "select-location", "gift": "gift-giving",
    "savings": "saving-money", "whisper": "whispered-comm",
    "ice_break": "ice-breaking", "rel_maintain": "rel-maintain",
}


def gated_slug(r) -> str | None:
    """与 `audit.js::eventCardSlug` 等价。"""
    p = r.get("payload") or {}
    tpl = p.get("template")
    if tpl and tpl in EVENT_CARDS_BY_TEMPLATE:
        return EVENT_CARDS_BY_TEMPLATE[tpl]
    if r["type"] in EVENT_CARDS:
        return EVENT_CARDS[r["type"]]
    t = r["type"]
    if t == "TRANSFER":
        return "gift-giving" if p.get("reason") == "gift" else None
    if t in ("DEPOSIT", "WITHDRAW"):
        return "saving-money"
    if t == "STATE_CHANGE":
        return "emotion-burnout" if p.get("to") == "exhausted" else None
    if t == "MARKET_TRADE":
        si = p.get("scarcity_index")
        return "scarcity-buy" if (p.get("reason") == "scarce_buy" or (isinstance(si, (int, float)) and si >= THETA_SCARCE)) else None
    if t == "MSG_DM":
        return "whispered-comm" if p.get("visibility") == "private" else None
    return None


def recount(records) -> dict:
    by_current = collections.Counter()
    by_gated = collections.Counter()
    for r in records:
        slug = ORIGINAL_MAPPING.get(r["type"])
        if slug:
            by_current[slug] += 1
        g = gated_slug(r)
        if g:
            by_gated[g] += 1
    current_total = sum(by_current.values())
    gated_total = sum(by_gated.values())
    # 领导变体（每 slug 仅取第一个 type）：解释旧数 22,987（废弃）
    first_type = {}
    for t, s in ORIGINAL_MAPPING.items():
        first_type.setdefault(s, t)
    leader_variant = sum(sum(1 for r in records if r["type"] == t) for t in first_type.values())
    return {
        "current_total": current_total,
        "gated_total": gated_total,
        "by_card_current": {k: by_current[k] for k in sorted(by_current)},
        "by_card_gated": {k: by_gated[k] for k in sorted(by_gated)},
        "reduction_pct": round((current_total - gated_total) / current_total * 100, 2) if current_total else 0.0,
        "leader_variant": leader_variant,
        "deprecated": {
            "22987": "领导口径变体（每 slug 仅取一个 type；与引擎按 e.type 逐事件渲染不符）→ 废弃，以 current_total 为准",
            "567": "template-only（未含 TRANSFER{gift}/DEPOSIT 语义并集）→ 废弃",
            "546": "template-only 且 whispered-comm=0 → 废弃",
        },
        "caliber": {
            "field": "e.type", "one_card_per_event": True, "unmapped_counted": False,
            "current_rule": "sprites.js 原 EVENT_CARDS 的 26 条 type 条目逐事件计数",
            "gated_rule": "template→EVENT_CARDS→语义 switch（与 frontend audit.js 一致）",
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="obs.recount_cards")
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    recs = [json.loads(l) for l in open(a.log, encoding="utf-8")]
    out = recount(recs)
    txt = json.dumps(out, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(txt + "\n", encoding="utf-8")
        print(f"written: {a.out}")
    print(f"current_total={out['current_total']} gated_total={out['gated_total']} "
          f"reduction={out['reduction_pct']}% (leader_variant={out['leader_variant']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
