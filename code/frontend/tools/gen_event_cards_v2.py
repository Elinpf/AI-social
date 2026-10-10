#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_event_cards_v2 — thin wrapper（T86）。
单一真源：/root/.jiuwenswarm/agent/workspace/skills/qingxi-pixel-art/scripts/gen_event_cards_v2.py"""
import os, runpy, sys
_SKILL = "/root/.jiuwenswarm/agent/workspace/skills/qingxi-pixel-art/scripts/gen_event_cards_v2.py"
os.environ.setdefault("QINGXI_ASSETS",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets"))
sys.argv[0] = _SKILL
runpy.run_path(_SKILL, run_name="__main__")
