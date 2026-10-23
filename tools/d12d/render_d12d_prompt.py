#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-D 接线证明：固定输入下渲染 _dialogue_prompt / _reply_prompt（T0/T1/T2 三态），落文本+sha256。

态判定：LIFE_PROMPT_D12C_SPECIFIC=1 ⇒ C；LIFE_PROMPT_D12C_DEDUP=1 ⇒ D
  无/无 ⇒ T0；C/无 ⇒ T1；C/D ⇒ T2
用法（在 code/ 下，PYTHONPATH=$PWD）：python3 ../tools/d12d/render_d12d_prompt.py
"""
import hashlib, json, os

from orchestration.integration import build_world

w = build_world(seed=42, n=2)
ag = w["agents"][0]
pid = ag.agent_id
partner = [p for p in ag.peers if p != pid][0]

dlg = ag._dialogue_prompt("gift", [pid, partner])
rep = ag._reply_prompt(partner, "gift", [(partner, f"{partner}：来，尝尝这个。")])

c_on = ag._d12c_on() if hasattr(ag, "_d12c_on") else False
d_on = ag._d12d_on() if hasattr(ag, "_d12d_on") else False
state = {(False, False): "T0", (True, False): "T1", (True, True): "T2"}.get((c_on, d_on), "OTHER")

out = {"state": state, "d12c_on": c_on, "d12d_on": d_on,
       "env": {k: os.environ.get(k, "") for k in ("LIFE_PROMPT_D12C_SPECIFIC", "LIFE_PROMPT_D12C_DEDUP")},
       "dialogue_prompt": dlg, "reply_prompt": rep,
       "sha256_dialogue": hashlib.sha256(dlg.encode()).hexdigest(),
       "sha256_reply": hashlib.sha256(rep.encode()).hexdigest(),
       "prompt_fn_sha256": hashlib.sha256((dlg + "\n===\n" + rep).encode()).hexdigest()}
print(json.dumps(out, ensure_ascii=False, indent=2))
