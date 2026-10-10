"""类型化错误（蓝图 §2.6，B1）。

供 kernel / life / emergence 共用，避免下层为取错误类型而 import kernel。
"""

from __future__ import annotations


class KernelError(Exception):
    """所有内核域错误的基类。"""


class HashChainBroken(KernelError):
    """哈希链断裂（prev_hash 不连续 / hash 不匹配）。"""


class UnknownEventType(KernelError, KeyError):
    """重放/统计遇到未知事件类型（08 X4：立即报错，禁止静默忽略）。

    同时继承 KeyError，兼容既有 `except KeyError` / `pytest.raises(KeyError)` 用法。
    """


class RoundRollback(KernelError):
    """hook 异常 -> 整回合回滚（丢弃本回合待提交缓冲区 + SYSTEM_ERROR）。"""


class IllegalJudgment(KernelError):
    """`decision ∉ envelope.options`（IF-2b，不冻结，记 SYSTEM_ERROR）。"""
