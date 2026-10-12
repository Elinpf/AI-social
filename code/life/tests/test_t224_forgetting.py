"""T224 遗忘（forgetting）单元测试 —— 保留度 / 三级处理 / **保护名单**。

最关键的一条：**重要记忆只降级、永不 merge/drop**（T205 §3.2，T224 硬要求）。
"""
from __future__ import annotations

from life import forgetting as F


def _params(enabled: bool = True) -> dict:
    p = dict(F.DEFAULTS)
    p["enabled"] = enabled
    return p


def _mem(mem_id: str, **kw) -> dict:
    base = {"mem_id": mem_id, "kind": "observation", "importance": 2, "last_access": 0,
            "access_count": 0, "subject": None, "emo": 0, "consolidated": False}
    base.update(kw)
    return base


# ---- 保留度：范围 / 单调 / 确定性 -------------------------------------------
def test_retention_range_and_monotonic():
    p = _params()
    s = F.strength_permille(_mem("M1", importance=5), p)
    prev = 1000
    for dt in range(0, 200, 3):
        r = F.retention_permille(dt, s, p["h0_slots"])
        assert 0 <= r <= 1000
        assert r <= prev, f"retention should not increase: dt={dt}"
        prev = r


def test_retention_deterministic():
    assert F.retention_permille(37, 2000, 14) == F.retention_permille(37, 2000, 14)


def test_strength_increases_with_importance_and_access():
    p = _params()
    low = F.strength_permille(_mem("M1", importance=1), p)
    high = F.strength_permille(_mem("M1", importance=9), p)
    acc = F.strength_permille(_mem("M1", importance=1, access_count=5), p)
    assert high > low and acc > low


# ---- 保护名单：只降级、永不 merge/drop（最关键） ----------------------------
def test_protected_high_importance_never_dropped_or_merged():
    p = _params()
    # 极老、且同 subject 有兄弟（未保护者本会被判 merge）
    m = _mem("M-HIGH", importance=9, last_access=0, subject="P007")
    sib = _mem("M-SIB", importance=9, last_access=0, subject="P007")
    acts = {a["mem_id"]: a for a in F.plan_forgetting([m, sib], round_no=10_000, params=p)}
    assert acts["M-HIGH"]["protected"] is True
    assert acts["M-HIGH"]["level"] == "demote"          # 只降级
    assert acts["M-HIGH"]["level"] not in ("merge", "drop")


def test_protected_variants_never_merge_or_drop():
    p = _params()
    cases = [
        _mem("A", importance=7, subject="X"),                     # importance 阈值
        _mem("B", access_count=3, subject="X"),                   # 访问次数阈值
        _mem("C", emo=6, subject="X"),                            # 情绪阈值
        _mem("D", kind="semantic", subject="X"),                  # 类型保护
        _mem("E", kind="reflection", subject="X"),
        _mem("F", referenced_by_reflection=True, subject="X"),
    ]
    for m in cases:
        m["last_access"] = 0
    acts = F.plan_forgetting(cases, round_no=100_000, params=p)
    for a in acts:
        assert a["protected"] is True, a
        assert a["level"] in ("keep", "demote"), f"protected must not drop/merge: {a}"


def test_unprotected_fades_to_drop_or_merge():
    p = _params()
    lonely = _mem("L", importance=1, last_access=0, subject=None)          # 无兄弟 → drop
    a1 = F.classify(lonely, round_no=100_000, params=p, has_sibling=False)
    assert a1["level"] == "drop" and a1["protected"] is False
    sib = _mem("S", importance=1, last_access=0, subject="Z")
    a2 = F.classify(sib, round_no=100_000, params=p, has_sibling=True)     # 有兄弟 → merge
    assert a2["level"] == "merge" and a2["protected"] is False


def test_recent_memory_kept():
    p = _params()
    fresh = _mem("F", importance=1, last_access=9999)
    a = F.classify(fresh, round_no=10_000, params=p, has_sibling=False)
    assert a["level"] == "keep"


def test_disabled_returns_empty():
    assert F.plan_forgetting([_mem("M1", importance=1)], 100_000, _params(enabled=False)) == []


def test_consolidation_groups_by_subject():
    p = _params()
    mems = [_mem("M1", subject="P007"), _mem("M2", subject="P007"),
            _mem("M3", subject="P008"), _mem("M4", subject=None)]
    groups = F.consolidation_groups(mems, p)
    subs = {g["subject"]: g["count"] for g in groups}
    assert subs == {"P007": 2}          # P008 只有 1 条、subject=None 不聚合


def test_plan_is_sorted_and_deterministic():
    p = _params()
    mems = [_mem("M2", importance=1, subject=None), _mem("M1", importance=1, subject=None)]
    a = F.plan_forgetting(mems, 100_000, p)
    assert [x["mem_id"] for x in a] == sorted(x["mem_id"] for x in a)
