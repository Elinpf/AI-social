"""M-P 人格抗漂移（persona anti-drift）—— 锚定不写回 + 有界更新 + 漂移度量 + 指纹（T205 §1，T224 第一批）。

设计要点（对齐 `v2/refs/persona-memory-engineering.md` §1）：
  * **锚定不写回**：人格卡（`persona.py`）运行期只读；只有"表达层"状态向量 `P(t)` 可变。
  * **有界更新 + 均值回归**：`P ← clamp(P + α·(anchor − P) + Δ, 0, 100)`，`Δ∈[−δ,δ]`。
  * **可复算指纹**：`PF0`（锚，身份不变则不变）与 `PF(t)`（当前表达）；漂移度量 `drift`。

本模块**纯整数函数**（α/漂移以 permille 表示）；不 import 内核、不调 LLM。
? 新增决策类 LLM 调用 = 0（漂移候选来自**已有**反思调用，不新增）。
"""

from __future__ import annotations

from .util import canonical_hash

BIG5_DIMS = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")

DEFAULTS: dict[str, int] = {
    "alpha_permille": 20,   # 每步回归系数 α = 0.02（越大越"弹回"锚点）
    "delta_max": 1,         # 单事件单维最大 ±δ（分）
    "drift_max_permille": 150,   # 全维归一化漂移上限（0.15）
    "drift_dim_max_permille": 200,  # 单维归一化漂移上限（0.20）
    # T323/T320：漂移候选阈值（原硬编码 7/2，现入键集使可配置；默认=现状）
    "min_importance": 7,      # 反思节点 importance ≥ 此值才算候选（0–10）
    "min_windows": 2,         # 需连续 N 个睡眠窗含候选才发 PERSONA_DRIFT（<N=抖动不发）
}


def persona_fingerprint(anchor: dict) -> str:
    """静态指纹 `PF0` = H(pid? + 大五 + 价值观 + 技能)。

    身份不变（锚不变）则 `PF0` 不变；用于"跑 1000 回合还是同一个人"的锚定校验。
    """
    payload = {
        "persona_id": anchor.get("persona_id"),
        "personality_big5": {d: int(anchor.get("personality_big5", {}).get(d, 0)) for d in BIG5_DIMS},
        "values": dict(sorted((anchor.get("values") or {}).items())),
        "skills": anchor.get("skills") or [],
    }
    return canonical_hash(payload)


def init_state(anchor: dict) -> dict:
    """表达层向量初值 `P(0) = anchor`（大五 5 维整数）。"""
    b5 = anchor.get("personality_big5", {})
    return {d: int(b5.get(d, 50)) for d in BIG5_DIMS}


def _anchor_dims(anchor: dict) -> dict:
    b5 = anchor.get("personality_big5", {})
    return {d: int(b5.get(d, 50)) for d in BIG5_DIMS}


def bounded_update(p: dict, anchor: dict, dim: str, delta: int, params: dict) -> int:
    """单维有界更新：`p' = clamp(p + α·(a−p)/1000 + clamp(Δ), 0, 100)`（整数）。"""
    if dim not in BIG5_DIMS:
        raise ValueError(f"unknown persona dim: {dim}")
    a = _anchor_dims(anchor)[dim]
    cur = int(p.get(dim, a))
    d = int(delta)
    dmax = int(params["delta_max"])
    d = max(-dmax, min(dmax, d))
    pull = (a - cur) * int(params["alpha_permille"]) // 1000
    val = cur + pull + d
    return max(0, min(100, val))


def apply_drift_events(p: dict, anchor: dict, events: list[dict], params: dict) -> dict:
    """按顺序折叠漂移事件（每条 `{dim, delta}`）；返回新的表达层向量。确定性。"""
    out = dict(p)
    for ev in events:
        dim = ev["dim"]
        out[dim] = bounded_update(out, anchor, dim, int(ev.get("delta", 0)), params)
    return out


def drift_permille(p: dict, p0: dict) -> int:
    """全维归一化漂移 `||P(t) − P(0)||_1 / (5·100) · 1000`（整数）。"""
    tot = sum(abs(int(p.get(d, 0)) - int(p0.get(d, 0))) for d in BIG5_DIMS)
    return tot * 1000 // (len(BIG5_DIMS) * 100)


def drift_dims_permille(p: dict, anchor: dict) -> dict:
    """逐维相对锚点的归一化漂移（permille）。"""
    a = _anchor_dims(anchor)
    return {d: abs(int(p.get(d, a[d])) - a[d]) * 1000 // 100 for d in BIG5_DIMS}


def within_bounds(p: dict, p0: dict, anchor: dict, params: dict) -> bool:
    """漂移是否在阈值内：全维 ≤ `drift_max`，逐维（相对锚）≤ `drift_dim_max`。"""
    if drift_permille(p, p0) > int(params["drift_max_permille"]):
        return False
    for v in drift_dims_permille(p, anchor).values():
        if v > int(params["drift_dim_max_permille"]):
            return False
    return True


def dynamic_fingerprint(pid: str, p: dict) -> str:
    """动态指纹 `PF(t)` = H(pid + 当前表达层向量)。"""
    return canonical_hash({"persona_id": pid,
                           "state": {d: int(p.get(d, 0)) for d in BIG5_DIMS}})
