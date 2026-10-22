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
import re
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

#: 保护名单规则（**单源**：obs 由事件 `protected` 标记 count，不复刻本表；
#: 若需引用规则本身，以此常量为准）。阈值由 params 注入（默认见 DEFAULTS）。
PROTECTION_RULES = (
    "kind in PROTECTED_KINDS('semantic','reflection')",
    "importance >= theta_keep_importance(7)",
    "access_count >= theta_keep_access(3)",
    "abs(emo) >= theta_keep_emo(6)",
    "referenced_by_reflection == true",
)


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


def protection_reason(mem: dict, params: dict) -> str | None:
    """命中保护名单的原因（单源）；未命中 → None。"""
    if mem.get("kind") in PROTECTED_KINDS:
        return f"kind:{mem.get('kind')}"
    if int(mem.get("importance", 0)) >= int(params["theta_keep_importance"]):
        return "importance"
    if int(mem.get("access_count", 0)) >= int(params["theta_keep_access"]):
        return "access"
    if abs(int(mem.get("emo", 0))) >= int(params["theta_keep_emo"]):
        return "emotion"
    if mem.get("referenced_by_reflection"):
        return "reflection_ref"
    return None


def is_protected(mem: dict, params: dict) -> bool:
    """保护名单（T205 §3.2）：任一命中即受保护 → **只降级、永不 merge/drop**。"""
    return protection_reason(mem, params) is not None


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
            "protected": protected,
            "protection_reason": protection_reason(mem, params) if protected else None,
            "reason": reason}


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


# ---- 固化摘要：口径声明 + 人话细节提取（D1 / 2026-10-23） ---------------------
#: 固化摘要的**确定性口径声明**（本轮 D1 改动的可审计锚）。
#:
#: 为什么需要它：本函数的输出正文会经 `life/agent.py::_maybe_sleep_window` 写进
#: side 存贮（`side://mem/<agent>/<mem_id>.txt`，见 `life/memory.py::SideStore.write`），
#: 并由 `MEMORY_WRITE.body_ref/embed_ref` 指向它；`MEMORY_CONSOLIDATE` 意图虽带 `text`，
#: 但组合根 `orchestration/integration.py::_do_memory` **不把它落进事件 payload**
#: （实测 `run_f6_on_n16r60_seed42` 的 1267 条 MEMORY_CONSOLIDATE 均无 text 字段），
#: 因此正文只在 side blob 里，`run.jsonl` 里没有。
#: 也就是说**代码改动会改变 side blob 正文与 SM 的冻结向量**，而 `engine_version` 指纹
#: 只覆盖 `config/*.json` 的复现输入常数（`engine/version.py::FINGERPRINT_FILES`），
#: **覆盖不到 `life/*.py`**。故本改动**不能**靠改指纹来「声明」，只能靠这里显式声明口径
#: + 报告登记：
#:
#:   * v1（改动前，`8a768f4` 及以前）：`关于{subject}的印象（由{count}条经历聚合）`
#:     ——空壳模板，无任何具体内容（即使被引用也不带生活气息）。
#:   * v2（本改动）：`关于{subject}的印象：{细节1}；{细节2}`，细节从**被聚合的那几条
#:     经历正文**里确定性提取（人物/地点/活动），提取不到时**逐字节回退 v1**。
#:
#: 跨口径可比性：v1 与 v2 的 SM 正文不同 ⇒ ① side blob 正文不同 ② SM 的冻结向量
#: （由正文词法算出）不同 ⇒ `MEMORY_RETRIEVE.scores` 与后续行为可能不同。
#: 故 OF/OFF 对照必须**同一口径（同一 sha、同一分支）**跑两臂；v2 的读数**不可**直接
#: 与 v1 口径（`8a768f4` 及以前的批次）横向比。本次**未改**任何 config，故
#: `engine_version` 指纹前后一致（这一点在下游跑批时应看到两臂同指纹）。
SEMANTIC_SUMMARY_SPEC = "f6-sem-impression-v2"

#: 场所 id → 人话（`code/config/topology.json` 的 17 个 place_id；不读盘、进不了指纹）
_PLACE_CN = {
    "residence": "住处", "farm": "田里", "workshop": "作坊", "kitchen": "厨房",
    "clinic": "医馆", "school": "学堂", "office": "铺子", "market": "市集",
    "bank": "钱庄", "plaza": "广场", "town_hall": "镇公所", "library": "藏书楼",
    "community_center": "公屋", "cafe": "茶棚", "park": "园子", "hall": "大堂",
    "gate": "镇口",
}

#: 活动类型 id → 人话（`activity_templates.json` 实测 6 类 + 常见别名兜底）
_ACTIVITY_CN = {
    "self_care": "照应自己", "rest": "歇一歇", "socialize": "和人说说话",
    "leisure": "闲逛", "civic": "忙镇上的事", "learn": "学手艺", "trade": "做买卖",
    "work": "干活",
}

#: 单条细节的字符上限 / 一次摘要最多挂几条细节（控 token；与 F-6 注入端 `ITEM_CHARS` 同量级）
SUMMARY_DETAIL_CHARS = 22
SUMMARY_DETAIL_MAX = 2


def _tokens_to_cn(text: str) -> str:
    """把已知的内部 token 换成中文说法（未登记的 token 原样留下，交给可读门判死）。"""
    def _sub(m):
        tok = m.group(0)
        return _PLACE_CN.get(tok) or _ACTIVITY_CN.get(tok) or tok
    pat = r"\b(?:" + "|".join(sorted(
        {*_PLACE_CN, *_ACTIVITY_CN}, key=lambda s: (-len(s), s))) + r")\b"
    return re.sub(pat, _sub, text)


def _humanize_detail(text: str, names: dict[str, str] | None = None) -> str | None:
    """把一条经历正文 → 一句可读的「细节」。**纯文本规则、无 LLM、无随机**。

    只认 `life/agent.py::_describe_event` 实际产出的几种句式，其余一律 `None`
    （宁缺毋滥：宁可退回空壳模板，也不把内部 token 混进居民的话里）。

    返回 None 表示这条经历提不出细节。
    """
    s = (text or "").strip().replace("\n", " ")
    if not s:
        return None
    nm = names or {}

    def _name(tok: str) -> str:
        return nm.get(tok) or "有人"          # 不把 Pxxx 这类内部 id 递给模型

    m = re.match(r"^(P\d{3})\s*说：(.+)$", s)
    if m:
        body = m.group(2).strip()
        if not body:
            return None
        return f"{_name(m.group(1))}说起：{body[:SUMMARY_DETAIL_CHARS]}"
    m = re.match(r"^(P\d{3})\s*与\s*(P\d{3})\s*在\s*([a-z_]+)\s*相遇。$", s)
    if m:
        return f"{_name(m.group(1))}在{_PLACE_CN.get(m.group(3), m.group(3))}碰上了{_name(m.group(2))}"
    m = re.match(r"^(P\d{3})\s*在\s*([a-z_]+)\s*开始\s*([a-z_]+)。$", s)
    if m:
        pl = _PLACE_CN.get(m.group(2))
        ac = _ACTIVITY_CN.get(m.group(3))
        if not pl or not ac:
            return None
        return f"{_name(m.group(1))}在{pl}{ac}"
    m = re.match(r"^(P\d{3})\s*完成了\s*([a-z_]+)（([a-z_]+)\|([a-z_]+)）。$", s)
    if m:
        ac = _ACTIVITY_CN.get(m.group(2))
        if not ac:
            return None
        return f"{_name(m.group(1))}把{ac}忙完了"
    m = re.match(r"^(P\d{3})\s*到达\s*([a-z_]+)。$", s)
    if m:
        pl = _PLACE_CN.get(m.group(2))
        if not pl:
            return None
        return f"{_name(m.group(1))}去了{pl}"
    # 兜底：先换 token，再走可读门（挡掉「P003 的 RELATION_CHANGE 事件。」这类机器话）
    t = _tokens_to_cn(re.sub(r"P\d{3}", lambda mo: _name(mo.group(0)), s))
    if "事件" in t or re.search(r"[A-Za-z]{3,}", t) or re.search(r"[A-Z]{2,}", t):
        return None
    if len(re.sub(r"\s+", "", t)) < 6:
        return None
    return t[:SUMMARY_DETAIL_CHARS]


def summarize(subject: str, count: int,
              sources: Iterable[str] | None = None,
              *, names: dict[str, str] | None = None) -> str:
    """确定性固化摘要文本（固化用；**非 LLM 生成**）。

    两种口径（见 `SEMANTIC_SUMMARY_SPEC`）：
      * 无 `sources`（或全提不出细节）⇒ **逐字节回退 v1**：
        `关于{subject}的印象（由{count}条经历聚合）`；
      * 有 `sources` 且至少一条提出细节 ⇒ v2：
        `关于{subject}的印象：{细节1}；{细节2}`。

    确定性：`sources` 按**给定顺序**（调用方须传 `source_mem_ids` 的升序，
    即 mem_id 升序）逐条提取，细节按出现顺序去重取前 `SUMMARY_DETAIL_MAX` 条；
    不读墙钟、不用随机、不依赖 dict 遍历序以外的任何进程态 ⇒ 同一输入**逐字节同输出**。

    `names`：内部 token → 人话（`Pxxx` → 显示名）；仅影响措辞，不进任何指纹。
    """
    text_v1 = f"关于{subject}的印象（由{count}条经历聚合）"
    if sources is None:
        return text_v1
    details: list[str] = []
    seen: set[str] = set()
    for src in sources:
        d = _humanize_detail(src, names)
        if not d:
            continue
        key = re.sub(r"\s+", "", d)
        if key in seen:
            continue
        seen.add(key)
        details.append(d)
        if len(details) >= SUMMARY_DETAIL_MAX:
            break
    if not details:
        return text_v1
    return f"关于{subject}的印象：{'；'.join(details)}"


# ---- 固化分组（供睡眠窗口调用） ----------------------------------------------
def consolidation_groups(memories: Iterable[dict], params: dict) -> list[dict]:
    """按 `subject` 分组、达到阈值且尚未固化的情节记忆 → 固化候选（确定性）。

    仅考虑 `kind == "observation"/"chat"`；按 subject 升序、mem_id 升序。

    D1（本轮）：额外带出 `source_texts` —— 与 `source_mem_ids` **同序**（mem_id 升序）
    的原始正文，供 `summarize` 从中提取可读细节。记忆字典里没有 `text` 键时
    `source_texts` 为空列表 ⇒ `summarize` 走 v1 兜底（行为与改动前一致）。
    """
    if not params.get("enabled"):
        return []
    groups: dict[str, list[str]] = {}
    texts: dict[str, dict[str, str]] = {}
    for m in sorted((m for m in memories if m.get("mem_id")), key=lambda m: str(m["mem_id"])):
        if m.get("kind") not in ("observation", "chat"):
            continue
        if m.get("consolidated"):
            continue
        subj = m.get("subject")
        if not subj:
            continue
        mid = str(m["mem_id"])
        groups.setdefault(str(subj), []).append(mid)
        t = m.get("text")
        if isinstance(t, str) and t:
            texts.setdefault(str(subj), {})[mid] = t
    out = []
    for subj in sorted(groups):
        ids = groups[subj]
        if len(ids) >= int(params["consolidate_min"]):
            by_id = texts.get(subj, {})
            out.append({"subject": subj, "source_mem_ids": ids, "count": len(ids),
                        "source_texts": [by_id[i] for i in ids if i in by_id]})
    return out
