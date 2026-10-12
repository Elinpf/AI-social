"""M6 降级：life 侧消费接口（T221b）。

红线：**life 不 import engine**。life 只通过 port 向内核询问：
  * `llm_permit(wv)`            —— M4 分片：本回合该 agent 是否获准调用 LLM；
  * `should_skip_judgment(...)` —— critical-only：本回合该判定是否应跳过。

**事件出口在 adapter/引擎侧**（"做决定的人负责让决定可见"）：adapter 判跳时自行落
`DEGRADE{action:"skip_judgment", skipped:[{dimension,parties,round}]}`；life 只读布尔返回。
**默认关 = 行为不变**：方法缺失 → 不跳；`llm_permit` 默认 True。
"""
from __future__ import annotations


def llm_permit(wv) -> bool:
    """本回合是否获准调用 LLM（M4）。默认 True（未启用 = 行为与现状一致）。"""
    return bool(getattr(wv, "llm_permit", True))


def should_skip_judgment(kernel, dimension: str, parties) -> bool:
    """critical-only 逐判定 gate。

    * 方法缺失（旧内核 / 未接线）→ **不跳**（向后兼容，默认不降级）；
    * 抛异常 → **不跳**（降级失败要偏保守：宁可多算，不可静默少算）；
    * 否则返回 adapter 的判定；adapter 已负责把跳过**落成可列事件**。
    """
    fn = getattr(kernel, "should_skip_judgment", None)
    if fn is None:
        return False
    try:
        return bool(fn(str(dimension), list(parties or [])))
    except Exception:
        return False
