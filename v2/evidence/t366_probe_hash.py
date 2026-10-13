#!/usr/bin/env python3
"""T366 跨树 probe：跑同 seed/rounds/n，打印 state_hash（供跨 sha 恒等比较）。

用法（在目标树根的**父目录**执行，或传 code 目录绝对路径）：
  T366_CODE=/abs/code T366_PROPAGATE=0 python3 t366_probe_hash.py 42 24 6
- T366_CODE：该树的 code 目录（含 config/）
- T366_PROPAGATE：0/1 覆盖 world_director.propagate.enabled（HEAD 树无此键，忽略）
- time.ongoing 由该树 code/config/time.json 决定（跨树比较前**两边都置 false**）
"""
import os
import sys

os.environ.setdefault("N50_VEC", "0")
CODE = os.environ.get("T366_CODE") or os.path.join(os.getcwd(), "code")
sys.path.insert(0, CODE)

from orchestration.integration import build_world   # noqa: E402
from engine.runner import default_config            # noqa: E402
from engine.state import state_hash                 # noqa: E402

seed, rounds, n = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
cfg = default_config()
pg = os.environ.get("T366_PROPAGATE")
if pg is not None:
    cfg.setdefault("world_director", {})["propagate"] = {"enabled": pg == "1"}
w = build_world(seed=seed, config=cfg, n=n)
eng = w["engine"]
for r in range(rounds):
    eng.run_round(r)
print(state_hash(eng.state))
