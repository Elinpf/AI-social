#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-C 接线证明：固定输入下渲染 _dialogue_prompt / _reply_prompt（OFF vs ON），落文本+sha256。"""
import hashlib, json, os, sys

from orchestration.integration import build_world

w = build_world(seed=42, n=2)
ag = w["agents"][0]
pid = ag.agent_id
partner = [p for p in ag.peers if p != pid][0]

dlg = ag._dialogue_prompt("gift", [pid, partner])
rep = ag._reply_prompt(partner, "gift", [(partner, f"{partner}：来，尝尝这个。")])
state = "ON" if ag._d12c_on() else "OFF"
out = {"state": state, "env": os.environ.get("LIFE_PROMPT_D12C_SPECIFIC", ""),
       "dialogue_prompt": dlg, "reply_prompt": rep,
       "sha256_dialogue": hashlib.sha256(dlg.encode()).hexdigest(),
       "sha256_reply": hashlib.sha256(rep.encode()).hexdigest(),
       "prompt_fn_sha256": hashlib.sha256((dlg + "\n===\n" + rep).encode()).hexdigest()}
print(json.dumps(out, ensure_ascii=False, indent=2))
