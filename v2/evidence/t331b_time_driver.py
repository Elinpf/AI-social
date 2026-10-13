import os, sys
os.environ.setdefault("N50_VEC", "0")
from orchestration.integration import build_world
import life.visibility as LV

mode = sys.argv[1] if len(sys.argv) > 1 else "on"
w = build_world(seed=42, n=50)
e = w["engine"]
if mode == "off":
    LV.clear_indexes()          # 强制全扫，作为对照
for r in range(12):
    e.run_round(r)
print("done mode=", mode)
