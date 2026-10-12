"""M2 遗忘（forgetting）—— 定点保留度 + 三级处理 + 保护名单（T205 §3.2/§3.3，T224 第一批）。

设计要点（对齐 `v2/refs/persona-memory-engineering.md` §3）：
  * **定点保留度**：`retention_permille()` 为**纯整数**函数（无浮点、无墙钟、无随机），
    给定输入逐位一致；曲线形状是**工程近似**（`【未验证】`），非心理学结论。
  * **三级处理**：`keep` → `demote`(L1 降级/摘要化) → `merge`(L2 合并) / `drop`(L3 删除)。
  * **保护名单**：重要记忆**只降级，绝不 merge/drop**（T224 最关键的一条，见 §protection）。

本模块**纯函数**：不 import 内核、不写世界、不调 LLM。新增决策类 LLM 调用 = 0。
默认**关闭**（`config/life_v2.json`）；关闭时 `plan_forgetting` 恒返回空。

参数全部整数（permille 表示比例，1.0 = 1000）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

# ---- 默认参数（可被 config/life_v2.json 的 "forgetting" 段覆盖） -------------
DEFAULTS: dict[str, int | bool] = {
    "enabled": False,
    "h0_slots": 14,            # 基准半衰期（slot 数）
    "s_base_permille": 1000,   # 强度基准 1.0
    "w_access": 500,           # 每次访问 +0.5
    "w_importance": 300,       # 每点 importance +0.3
    "w_emo": 400,              # 每点 |emo| +0.4
    "w_consolidated": 500,     # 已固化 +0.5
    "s_min_permille": 1000,
    "s_max_permille": 6000,
    "theta_keep_importance": 7,   # >= 保护（永不 merge/drop）
    "theta_keep_access": 3,       # 访问次数 >= 保护
    "theta_keep_emo": 6,          # |emo| >= 保护
    "theta_demote_permille": 600, # R < 600 → 降级候选
    "theta_forget_permille": 300, # R < 300 → 合并/删除候选
    "consolidate_min": 2,         # 同 subject >= N 条 → 固化
}

#: 受保护（只降级、永不 merge/drop）的记忆类型
PROTECTED_KINDS = ("semantic", "reflection")


def load_params(path: str | Path | None = None) -> dict[str, Any]:
    """从 `config/life_v2.json` 读 `forgetting` 段；缺失/缺文件 → 用 DEFAULTS。

    不静默改变语义：缺文件时返回**默认（enabled=False）**，即不启用。
    """
    p = Path(path) if path else (Path(__file__).resolve().parents[1] / "config" / "life_v2.json")
    params = dict(DEFAULTS)
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        sect = data.get("forgetting", {}) if isinstance(data, dict) else {}
        for k, v in sect.items():
            if k in params:
                params[k] = v
    return params


# ---- 强度与保留度 ------------------------------------------------------------
def strength_permille(mem: dict, params: dict) -> int:
    """S(m)（强度，permille）。整数；越大越难忘。"""
    access = int(mem.get("access_count", 0))
    imp = int(mem.get("importance", 0))
    emo = abs(int(mem.get("emo", 0)))
    cons = 1 if mem.get("consolidated") else 0
    s = (int(params["s_base_permille"])
         + int(params["w_access"]) * access
         + int(params["w_importance"]) * imp
         + int(params["w_emo"]) * emo
         + int(params["w_consolidated"]) * cons)
    return max(int(params["s_min_permille"]), min(int(params["s_max_permille"]), s))


def retention_permille(dt_slots: int, s_permille: int, h0_slots: int) -> int:
    """定点保留度 R ∈ [0,1000]。**纯整数、单调不增**。

    半衰期 H = h0 * S / 1000（整数 slot）；每过一个半衰期折半，半衰期内线性插值。
    形状为工程近似（`【未验证】`）。
    """
    dt = max(0, int(dt_slots))
    h0 = max(1, int(h0_slots))
    s = max(1, int(s_permille))
    half_life = max(1, h0 * s // 1000)
    steps = dt // half_life
    if steps >= 16:
        return 0
    half = 1000 >> steps                       # 1000 / 2^steps
    frac = (dt % half_life) * 1000 // half_life  # 0..999 半衰期内进度
    # 在本半衰期内由 half 线性降到 half/2
    return int(half - (half * frac // 1000 // 2))


def is_protected(mem: dict, params: dict) -> bool:
    """保护名单（T205 §3.2）：任一命中即受保护 → **只降级、永不 merge/drop**。"""
    if mem.get("kind") in PROTECTED_KINDS:
        return True
    if int(mem.get("importance", 0)) >= int(params["theta_keep_importance"]):
        return True
    if int(mem.get("access_count", 0)) >= int(params["theta_keep_access"]):
        return True
    if abs(int(mem.get("emo", 0))) >= int(params["theta_keep_emo"]):
        return True
    if mem.get("referenced_by_reflection"):
        return True
    return False


def classify(mem: dict, round_no: int, params: dict, *, has_sibling: bool) -> dict:
    """单条记忆的遗忘判定 → 动作字典（确定性）。

    返回 `{mem_id, level, retention_permille, protected, reason}`；
    `level ∈ {"keep","demote","merge","drop"}`。受保护记忆**只可能** `keep`/`demote`。
    """
    last = int(mem.get("last_access", mem.get("written_round", 0)))
    dt = max(0, int(round_no) - last)
    r = retention_permille(dt, strength_permille(mem, params), int(params["h0_slots"]))
    protected = is_protected(mem, params)

    level = "keep"
    reason = "retained"
    if r < int(params["theta_demote_permille"]):
        if protected:
            level = "demote"          # 保护：**只降级**（绝不 drop/merge）
            reason = "protected_demote"
        elif r < int(params["theta_forget_permille"]):
            level = "merge" if has_sibling else "drop"
            reason = "faded_merge" if has_sibling else "faded_drop"
        else:
            level = "demote"
            reason = "faded_demote"
    return {"mem_id": mem.get("mem_id"), "level": level, "retention_permille": r,
            "protected": protected, "reason": reason}


def plan_forgetting(memories: Iterable[dict], round_no: int, params: dict) -> list[dict]:
    """批量遗忘计划（按 `mem_id` 升序，确定性）。

    - 关闭时返回 `[]`；
    - `has_sibling`：同 `subject` 且不同 `mem_id` 的可见记忆存在 → 合并而非删除。
    """
    if not params.get("enabled"):
        return []
    mems = sorted((m for m in memories if m.get("mem_id")), key=lambda m: str(m["mem_id"]))
    by_subject: dict[str, int] = {}
    for m in mems:
        subj = m.get("subject")
        if subj:
            by_subject[str(subj)] = by_subject.get(str(subj), 0) + 1
    out: list[dict] = []
    for m in mems:
        subj = m.get("subject")
        has_sibling = bool(subj) and by_subject.get(str(subj), 0) >= 2
        action = classify(m, round_no, params, has_sibling=has_sibling)
        if action["level"] != "keep":
            out.append(action)
    return out


def summarize(subject: str, count: int) -> str:
    """确定性摘要文本（固化用；**非 LLM 生成**）。"""
    return f"关于{subject}的印象（由{count}条经历聚合）"


# ---- 固化分组（供睡眠窗口调用） ----------------------------------------------
def consolidation_groups(memories: Iterable[dict], params: dict) -> list[dict]:
    """按 `subject` 分组、达到阈值且尚未固化的情节记忆 → 固化候选（确定性）。

    仅考虑 `kind == "observation"/"chat"`；按 subject 升序、mem_id 升序。
    """
    if not params.get("enabled"):
        return []
    groups: dict[str, list[str]] = {}
    for m in sorted((m for m in memories if m.get("mem_id")), key=lambda m: str(m["mem_id"])):
        if m.get("kind") not in ("observation", "chat"):
            continue
        if m.get("consolidated"):
            continue
        subj = m.get("subject")
        if not subj:
            continue
        groups.setdefault(str(subj), []).append(str(m["mem_id"]))
    out = []
    for subj in sorted(groups):
        ids = groups[subj]
        if len(ids) >= int(params["consolidate_min"]):
            out.append({"subject": subj, "source_mem_ids": ids, "count": len(ids)})
    return out
