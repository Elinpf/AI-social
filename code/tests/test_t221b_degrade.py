"""T221b: M6 降级 life 侧消费接口的单元测试（不依赖 engine）。"""
from __future__ import annotations

from dataclasses import dataclass

from life.degrade import llm_permit, should_skip_judgment


@dataclass
class _WV:
    llm_permit: bool = True


class _Kernel:
    def __init__(self, ret=None, raises=False, has=True):
        self._ret, self._raises, self._has = ret, raises, has
        if has:
            self.should_skip_judgment = self._impl

    def _impl(self, dimension, parties):
        if self._raises:
            raise RuntimeError("boom")
        return self._ret


def test_llm_permit_default_true_and_passthrough():
    assert llm_permit(_WV()) is True
    assert llm_permit(_WV(llm_permit=False)) is False
    assert llm_permit(object()) is True  # 缺字段 -> 默认 True（行为不变）


def test_should_skip_backward_compatible_when_absent():
    assert should_skip_judgment(object(), "rel_affinity", ["P1"]) is False


def test_should_skip_passthrough_and_fail_conservative():
    assert should_skip_judgment(_Kernel(ret=True), "rel_trust", ["P1", "P2"]) is True
    assert should_skip_judgment(_Kernel(ret=False), "rel_trust", ["P1", "P2"]) is False
    # 异常 -> 不跳（降级失败偏保守，绝不静默少算）
    assert should_skip_judgment(_Kernel(raises=True), "rel_trust", ["P1"]) is False
