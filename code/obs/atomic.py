"""原子事件聚合与普查前置校验（L1 层，15 §1/§5）。

- `atomic_freq`           按 type 计数（封闭 schema 内）；
- `coverage`              登记/观测/登记未用/未知类型；
- `preflight`             普查前置异常硬报错（未知类型 / 缺字段 / 观测锚点悬空）。

全部只读、纯函数、确定性。
"""

from __future__ import annotations

from engine.events import EVENT_TYPES

# 判定所需最小 payload 字段（15 §5「判定缺字段」硬报错）
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "RELATION_CHANGE": ("from", "to", "dim", "after"),
    "RELATION_ENCOUNTER": ("a", "b"),
    "NEEDS_UPDATE": ("agent_id", "dim"),
    "NEED_UPDATE": ("agent_id", "dim"),
    "ACTIVITY_STARTED": ("agent_id", "activity_type"),
    "ACTIVITY_COMPLETED": ("agent_id",),
    "SKILL_LEVEL_UP": ("agent_id", "skill_id"),
    "SKILL_PRACTICE": ("agent_id", "skill_id"),
    "TAG_EMITTED": ("agent_id", "tag"),
    "NORM_PROPOSED": ("norm_id",),
    "NORM_ADOPTED": ("norm_id",),
    "NORM_VIOLATED": ("norm_id",),
    "ROLE_CHANGE": ("agent_id", "from_role", "to_role"),
    "SEED_EVENT": ("seed_id",),
    "OBSERVATION": ("observer", "target_event_seq"),
    "TRANSFER": ("from", "to", "amount"),
    "MARKET_TRADE": ("buyer", "seller", "amount"),
    "LLM_JUDGMENT": ("judgment_id", "decision", "frozen"),
    "SCORE_POSTED": ("contest_id",),
    "RANKING_EMITTED": ("contest_id",),
    "CONFLICT_STARTED": ("conflict_id",),
    "CONFLICT_RESOLVED": ("conflict_id",),
    "OFFER_COUNTERED": ("offer_id",),
    "GOAL_ACHIEVED": ("goal_id",),
    "GOAL_SET": ("goal_id",),
    "MEMORY_WRITE": ("agent_id",),
    "MEMORY_RETRIEVE": ("agent_id",),
}


class CensusError(RuntimeError):
    """普查前置异常（未知类型 / 缺字段 / 锚点悬空 / 链断裂）。"""


def atomic_freq(log) -> dict[str, int]:
    """原子事件频次表（按 type 计数，键字典序）。"""
    counts = log.type_counts()
    return {k: counts[k] for k in sorted(counts)}


# 经济事件族（Leader 2026-10-10：本实验核心设定「货币经济激励成长」，须单列盯防）
ECONOMIC_EVENT_TYPES = (
    "MONEY_MINTED", "MONEY_BURNED", "INIT_ENDOW",
    "TRANSFER", "MARKET_TRADE",
    "LOAN_ISSUED", "LOAN_REPAY", "LOAN_DEFAULT",
    "INTEREST_CHARGED", "INTEREST_PAID",
    "DEPOSIT", "WITHDRAW",
    "TAX_LEVIED", "UBI_PAID", "METABOLISM", "PENALTY_APPLIED", "REVIVE_FEE_PAID",
)


def economic_family(log) -> dict:
    """经济事件族计数（含未出现的类型=0）+ 合计。

    `economic_family_total` 为去创世项后的「真实经济活动」计数（排除
    MONEY_MINTED/MONEY_BURNED/INIT_ENDOW），用于判断「经济是否真的在运转」。
    """
    counts = log.type_counts()
    per = {t: counts.get(t, 0) for t in ECONOMIC_EVENT_TYPES}
    genesis = per["MONEY_MINTED"] + per["MONEY_BURNED"] + per["INIT_ENDOW"]
    active = sum(v for t, v in per.items()
                 if t not in ("MONEY_MINTED", "MONEY_BURNED", "INIT_ENDOW"))
    return {
        "by_type": per,
        "total": sum(per.values()),
        "active_total": active,
        "genesis_total": genesis,
        "is_active": active > 0,
    }


def coverage(log) -> dict:
    """覆盖度 / 孤立检查（15 §3④）。"""
    registered = set(EVENT_TYPES)
    observed = set(log.distinct_types())
    unknown = sorted(observed - registered)
    unused = sorted(registered - observed)
    return {
        "atomic_types_registered": len(registered),
        "atomic_types_observed": len(observed),
        "atomic_registered_unused": unused,
        "unknown_types_seen": unknown,
    }


def preflight(log, strict: bool = True) -> list:
    """普查前置校验（15 §5）。

    `strict=True`（默认）：任一命中即**硬报错**（规格要求）。
    `strict=False`：`缺字段` / `锚点悬空` 降级为**记录异常并返回**（供证据包在
    如实记录问题的同时仍产出普查结果）；`哈希链断裂` / `未知类型` 仍硬报错（更严重）。
    """
    anomalies: list = []
    if not log.chain_ok:
        raise CensusError(f"哈希链断裂 / seq 非单调：{log.chain_error}")

    known = set(EVENT_TYPES)
    # ① 未知事件类型（始终硬报错）
    for r in log.records:
        if r["type"] not in known:
            raise CensusError(f"未知事件类型：seq={r['seq']} type={r['type']!r}")

    seqs = {int(r["seq"]) for r in log.records}
    # ② 判定缺字段
    for r in log.records:
        req = REQUIRED_FIELDS.get(r["type"])
        if not req:
            continue
        payload = r.get("payload") or {}
        for f in req:
            if f not in payload:
                msg = (f"判定缺字段：seq={r['seq']} type={r['type']} 缺 {f!r} "
                       f"（实际键={sorted(payload.keys())}）")
                if strict:
                    raise CensusError(msg)
                anomalies.append({"kind": "missing_field", "seq": int(r["seq"]),
                                  "type": r["type"], "field": f,
                                  "actual_keys": sorted(payload.keys())})

    # ③ 观测锚点悬空（OBSERVATION.target_event_seq 必须指向已存在事件）
    for r in log.of_type("OBSERVATION"):
        tgt = (r.get("payload") or {}).get("target_event_seq")
        if tgt is not None and int(tgt) not in seqs:
            msg = f"观测锚点悬空：seq={r['seq']} target_event_seq={tgt} 不存在"
            if strict:
                raise CensusError(msg)
            anomalies.append({"kind": "dangling_anchor", "seq": int(r["seq"]),
                              "type": "OBSERVATION", "target_event_seq": int(tgt)})
    # LLM_JUDGMENT.effect_ref 悬空（若给出）
    for r in log.of_type("LLM_JUDGMENT"):
        eff = (r.get("payload") or {}).get("effect_ref")
        if eff is not None and int(eff) not in seqs:
            msg = f"判定 effect_ref 悬空：seq={r['seq']} effect_ref={eff} 不存在"
            if strict:
                raise CensusError(msg)
            anomalies.append({"kind": "dangling_anchor", "seq": int(r["seq"]),
                              "type": "LLM_JUDGMENT", "effect_ref": int(eff)})
    return anomalies


__all__ = ["atomic_freq", "coverage", "preflight", "CensusError", "REQUIRED_FIELDS",
           "ECONOMIC_EVENT_TYPES", "economic_family"]
