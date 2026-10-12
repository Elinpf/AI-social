"""T247: `SKILL_OUTPUT` 正文 writer —— 作为引擎「emit 后监听」观察者（T253）的 **life 端口**。

分工（与 T253 契约对齐）：
  * 引擎只提供 `register_emit_observer(fn)` + 触发；**不认识 life / 盘格式**；
  * **注册方（orchestration/adapter）** 调本模块的工厂 `make_emit_observer(side_root)`，
    把返回的 `fn(records)` 注册进去 —— **盘格式/何时写全在 life**（红线：life 不 import engine）。
  * 观察者 **read-only**：只见本轮已提交事件的浅拷贝，**只往 side 写派生正文，不改事件/世界**；
    `run` 回调、`replay` 不回调（T253）。

开关：`policy.skill_persist_enabled()`（`life.skill.persist_body`，默认 true；关时不写）。
"""
from __future__ import annotations

from . import policy
from .memory import SideStore

#: 技能产出正文的确定性模板（无 LLM：内容由事件字段派生，可复算/可导出）。
_SKILL_BODY = "技能产出：{skill_id}（质量 {quality}）第{day}日-{slot}；agent={agent}。"


def make_emit_observer(side_root):
    """返回一个可注册到 `engine.register_emit_observer` 的 `fn(records)`。

    只处理 `SKILL_OUTPUT`：把 `output_ref` 指向的正文写入 side（`write_skill`）。
    开关关时不写；非 SKILL_OUTPUT 事件忽略；单条写入失败不阻断本回合（side 为派生可复生）。
    """
    store = SideStore(side_root)

    def _observe(records) -> None:
        if not policy.skill_persist_enabled():
            return
        for rec in records or ():
            if rec.get("type") != "SKILL_OUTPUT":
                continue
            p = rec.get("payload") or {}
            aid, sid = p.get("agent_id"), p.get("skill_id")
            if not aid or not sid:
                continue
            text = _SKILL_BODY.format(skill_id=sid, quality=p.get("quality"),
                                      day=p.get("day"), slot=p.get("slot"), agent=aid)
            try:
                store.write_skill(aid, sid, text)
            except Exception:                        # 派生正文；失败不阻断仿真（可复生）
                continue

    return _observe
