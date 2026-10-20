"""M-S 睡眠离线窗口（sleep offline window）—— 固化 / 遗忘 / 人格漂移的**挂载点**（T205 §3，T224 第一批）。

设计要点（对齐 `v2/refs/persona-memory-engineering.md` §3）：
  * 睡眠 = **离线批处理窗口**：`night` 时段挂载「记忆固化 → 遗忘三级 → 人格漂移折叠」。
  * **纯函数**：`run_sleep_window()` 只读输入快照，产出**动作 + 待发事件**；**不写世界、不调 LLM**。
    （事件经调用方交中央裁决器落账——本模块不直接 emit。）
  * **默认关闭**（`config/life_v2.json`）；关闭时返回空计划。
  * **不新增决策类 LLM 调用**：固化摘要为确定性模板文本（见 `forgetting.summarize`）。

⚠️ 本文件**不含** `life/agent.py` 的接线（按 Leader 的"同文件单一改动者"规矩，挂载点接线待 T222 释放 `agent.py` 后另行协调）。
`run_sleep_window` 即为接线用的**稳定入口**。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from . import forgetting as F
from . import persona_drift as PD


def load_params(path: str | Path | None = None) -> dict[str, Any]:
    """加载 `config/life_v2.json` 的 `sleep`/`forgetting`/`persona_drift` 段（缺省→默认关）。"""
    p = Path(path) if path else (Path(__file__).resolve().parents[1] / "config" / "life_v2.json")
    forgetting = F.load_params(p)
    persona = dict(PD.DEFAULTS)
    sleep = {"enabled": False, "slot": "night"}
    if p.exists():
        import json
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for k, v in (data.get("persona_drift") or {}).items():
                if k in persona:
                    persona[k] = v
            for k, v in (data.get("sleep") or {}).items():
                if k in sleep:
                    sleep[k] = v
    # T297b: 运行时注入 hook —— 组合根可经 `config["life_v2"]` 覆盖（不落盘、不改指纹）。
    from . import config as _lcfg
    from . import dialogue_threads as _DT
    # D2：`dialogue`/`observe` 两段同属 `life_v2` 配置，作为**直通占位键**出现，
    # 否则 `--override life_v2.dialogue.*`（run_override 机制）会在此处 fail-loud
    # 报 unknown key。本模块不消费它们（由 `life/dialogue_threads.load_params` 读）。
    return _lcfg.apply("life_v2", {"sleep": sleep, "forgetting": forgetting,
                                   "persona_drift": persona,
                                   "dialogue": dict(_DT.DEFAULTS),
                                   "observe": dict(_DT.OBSERVE_DEFAULTS)})


def enabled(params: dict) -> bool:
    """睡眠窗口是否启用（sleep 与 forgetting 任一开关为真即视为启用流程；默认关）。"""
    return bool(params.get("sleep", {}).get("enabled")) or bool(params.get("forgetting", {}).get("enabled"))


def run_sleep_window(
    agent_id: str,
    memories: Iterable[dict],
    round_no: int,
    params: dict,
    *,
    day: int | None = None,
    slot: str | None = None,
    anchor: dict | None = None,
    p_state: dict | None = None,
    p0: dict | None = None,
    drift_events: list[dict] | None = None,
) -> dict:
    """睡眠离线窗口一次执行（纯函数）。

    输入：Agent 的记忆快照（只读）、当前回合、参数；可选人格锚/状态/漂移事件。
    输出：`{agent_id, day, slot, consolidate, forget, persona, events}`。
      - `consolidate`：固化候选（EM→SM，按 subject 分组）
      - `forget`：遗忘三级动作（保护记忆**只降级**）
      - `persona`：人格漂移结果（若提供 anchor）
      - `events`：**待发事件**（MEMORY_CONSOLIDATE / MEMORY_FORGET / PERSONA_DRIFT），交调用方落账
    关闭时：`{"...", "consolidate": [], "forget": [], "events": []}`（空计划、零副作用）。
    """
    mems = list(memories)
    sl = slot if slot is not None else str(params.get("sleep", {}).get("slot", "night"))
    out: dict[str, Any] = {
        "agent_id": agent_id, "day": day, "slot": sl,
        "consolidate": [], "forget": [], "persona": None, "events": [],
    }
    if not enabled(params):
        return out

    # 1) 固化：EM→SM（按 subject 分组，达阈值）
    fparams = params["forgetting"]
    groups = F.consolidation_groups(mems, fparams)
    for g in groups:
        text = F.summarize(g["subject"], g["count"])
        out["consolidate"].append({"subject": g["subject"],
                                   "source_mem_ids": g["source_mem_ids"],
                                   "count": g["count"], "text": text})
        out["events"].append({"type": "MEMORY_CONSOLIDATE", "payload": {
            "agent_id": agent_id, "subject": g["subject"],
            "source_mem_ids": g["source_mem_ids"],
            "produced_mem_id": f"M-{agent_id}-SM-{g['subject']}",
            "day": day, "slot": sl}})

    # 2) 遗忘三级（保护名单生效）
    actions = F.plan_forgetting(mems, round_no, fparams)
    for a in actions:
        out["forget"].append(a)
        out["events"].append({"type": "MEMORY_FORGET", "payload": {
            "agent_id": agent_id, "mem_id": a["mem_id"], "level": a["level"],
            "retention_permille": a["retention_permille"], "reason": a["reason"],
            "protected": bool(a.get("protected")),
            "protection_reason": a.get("protection_reason"),
            "day": day, "slot": sl}})

    # 3) 人格漂移折叠（可选）：锚定 + 有界更新 + 度量
    pparams = params["persona_drift"]
    if anchor is not None and p_state is not None:
        pp = dict(p_state)
        p0v = dict(p0) if p0 is not None else dict(p_state)
        changes = []
        for ev in (drift_events or []):
            before = int(pp.get(ev["dim"], 0))
            pp[ev["dim"]] = PD.bounded_update(pp, anchor, ev["dim"], int(ev.get("delta", 0)), pparams)
            changes.append((ev, before, pp[ev["dim"]]))
        pf0 = PD.persona_fingerprint(anchor)
        pft = PD.dynamic_fingerprint(agent_id, pp)
        drift = PD.drift_permille(pp, p0v)
        for ev, before, after in changes:
            out["events"].append({"type": "PERSONA_DRIFT", "payload": {
                "agent_id": agent_id, "dim": ev["dim"], "before": before, "after": after,
                "anchor": int(PD._anchor_dims(anchor)[ev["dim"]]),
                "cause_mem_id": ev.get("cause_mem_id"), "day": day, "slot": sl,
                "pf0": pf0, "pf_t": pft, "drift_permille": drift}})
        out["persona"] = {
            "pf0": pf0, "pf_t": pft, "drift_permille": drift,
            "drift_dims_permille": PD.drift_dims_permille(pp, anchor),
            "within_bounds": PD.within_bounds(pp, p0v, anchor, pparams),
        }
    return out
