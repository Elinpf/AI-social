#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""d27_mock_paren_inject.py —— 机制层替代测试（mock 链路里"旁白是否被保留/是否被剥落"）

## 为什么需要替代测试（这条是本节的核心事实）

跑真实的 mock 批（n=6 r=12，见 d27_mock_verification.md §3）得到 `paren_rate = 0.00%`，
但这**不能**说明"开关在 mock 链路没生效"，原因是结构性的：

- `code/freeze/providers.py:104-112` 的 `_NL_POOLS["dialogue"]` 指向 `_DIALOGUE_POOL`
  （`:85-90`）——**4 条固定句子，一条括号都没有**；
- `_mock_nl_text()`（`:115-121`）用 `sha256(purpose+system+user)` 从池里**按下标取一句**，
  prompt 的内容（包括本次新加的"句首可用一个括号…"）**完全不参与生成**。

⇒ mock 路径的 `paren_rate` 与提示词改动**结构性无关**，恒为 0。把它当"机制未生效"是假阴性。

## 本脚本验什么（mock 链路能验的那一半）

用一个**返回带括号台词**的 responder 驱动同一条 agent→MSG 落盘链路，回答一个可判定的问题：
**"括号码是否会被下游剥掉？"**
- 若 `paren_rate ≈ 100%` ⇒ 没有剥落环节，链条上游给什么就落什么；真实 B 臂 paren 100% 与此一致。
- 若 `paren_rate ≈ 0%` ⇒ 存在剥落/清洗环节，那么"放开旁白"在机制层就是失败的。

用法（在 B 臂树 code/ 下执行）：
  PYTHONPATH=. python3 /tmp/d27_mock_paren_inject.py <out.jsonl> <side_root>
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    out = sys.argv[1]
    side = sys.argv[2]
    sys.dont_write_bytecode = True
    sys.path.insert(0, os.getcwd())

    import freeze.providers as P

    _orig = P.MockProvider
    PAREN_LINE = "（把烟袋往桌上磕了磕）这话我记下了。"
    NL_PURPOSES = {"dialogue", "negotiation"}

    def _responder(system: str, user: str, extra):
        extra = extra or {}
        opts = extra.get("options")
        if opts:                                  # 软判定：确定性选一个合法选项
            h = int(P.sha256_hex(system + "\x00" + user)[:16], 16)
            return str(opts[h % len(opts)])
        purpose = str(extra.get("purpose") or "")
        if purpose in NL_PURPOSES:
            return PAREN_LINE
        nl = P._mock_nl_text(purpose, system, user)   # 其余用途沿用原池
        return nl if nl is not None else "mock::" + P.sha256_hex(system + "\x00" + user)[:16]

    class ParenMock(_orig):
        def __init__(self, *a, **k):
            k["responder"] = _responder
            super().__init__(*a, **k)

    P.MockProvider = ParenMock            # integration.py 在函数内 import，猴补生效

    sys.argv = ["orchestration", "run", "--life", "--seed", "42", "--agents", "6",
                "--rounds", "12", "--out", out, "--flush-every", "2", "--side-root", side]
    from orchestration.__main__ import main as orch_main
    return int(orch_main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
