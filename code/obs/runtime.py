"""观测层运行时守卫：`llm_calls == 0` 硬校验（T9 R2 / 07 §0.2）。

铁律 R2：计算任何指标/判定时**不得发起任何 LLM 调用**（不重问模型、不重算嵌入）。
本模块提供一个全局单调计数器与上下文守卫：

  - `note_llm_call()`  供任何真实 LLM/嵌入路径在调用时递增（冻结层可选接线）；
  - `llm_calls()`      读取当前计数；
  - `LlmCallGuard`     with 块内计数发生变化即抛 `LlmCallDuringObserve`。

观测层自身绝不 import LLM/冻结层；该守卫既作运行时断言，也作可审计证据
（报告头 `llm_calls == 0`）。
"""

from __future__ import annotations

_LLM_CALLS = 0


class LlmCallDuringObserve(RuntimeError):
    """观测层计算过程中发起了 LLM 调用（违反铁律 R2）。"""


def note_llm_call(n: int = 1) -> int:
    """记录一次（或 n 次）LLM/嵌入调用，返回累计值。"""
    global _LLM_CALLS
    _LLM_CALLS += int(n)
    return _LLM_CALLS


def llm_calls() -> int:
    return _LLM_CALLS


def reset_llm_calls() -> None:
    global _LLM_CALLS
    _LLM_CALLS = 0


class LlmCallGuard:
    """上下文守卫：进入时快照计数，退出时要求计数不变。

    用法::

        with LlmCallGuard("metrics"):
            ...  # 纯计算

    退出若非零变化，抛 `LlmCallDuringObserve`。
    """

    def __init__(self, where: str = "observe", expected_delta: int = 0):
        self.where = where
        self.expected_delta = int(expected_delta)
        self._before = 0

    def __enter__(self) -> "LlmCallGuard":
        self._before = llm_calls()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        delta = llm_calls() - self._before
        if exc_type is None and delta != self.expected_delta:
            raise LlmCallDuringObserve(
                f"{self.where}: 观测计算中 llm_calls 变化 {delta}（应 {self.expected_delta}）"
            )
        return False


__all__ = [
    "note_llm_call", "llm_calls", "reset_llm_calls",
    "LlmCallGuard", "LlmCallDuringObserve",
]
