#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_method_samples — thin wrapper（T86）。
单一真源：/root/.jiuwenswarm/agent/workspace/skills/qingxi-pixel-art/scripts/gen_method_samples.py
本包装仅把输出指向本项目 frontend/assets，随后运行 skill 脚本（不复制实现，避免双份口径）。"""
import os, runpy, sys
_SKILL = "/root/.jiuwenswarm/agent/workspace/skills/qingxi-pixel-art/scripts/gen_method_samples.py"
os.environ.setdefault("QINGXI_ASSETS",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets"))
sys.argv[0] = _SKILL
runpy.run_path(_SKILL, run_name="__main__")
