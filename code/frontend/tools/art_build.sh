#!/usr/bin/env bash
# art_build.sh — 青溪镇美术管线「一键幂等」门禁（gen → check → copy）
#
# 结构对齐 frontend/tools/ci_gate.sh。**任一环节失败即非零退出**，
# 且内置「自洽断言」：JSON 的 distinct_colors 必须等于**刚生成的落盘 PNG** 实测值 ——
# 从结构上杜绝"数字与产物脱钩 / 假绿"（不依赖任何人记得重跑）。
#
# 用法：make art   或   bash frontend/tools/art_build.sh
set -euo pipefail

SK="/root/.jiuwenswarm/agent/workspace/skills/qingxi-pixel-art"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"      # .../code/frontend
ASSETS="$SRC/assets"
S="$SK/scripts"

echo "[art] 1/4 生成（手绘网格 → PNG；单一真源在 skill）"
python3 "$S/gen_hand_grids.py"
python3 "$S/gen_hand_buildings128.py"
python3 "$S/gen_hand_chars.py"
python3 "$S/gen_hand_props.py"
python3 "$SRC/tools/gen_assets_pixel.py" --set all    # 基础 tile/road/icon（含 Bayer 抖动）
python3 "$SRC/tools/gen_event_cards_hand.py"        # 事件卡 20 张（单一在用集）

echo "[art] 2/4 校验（剪影同一趟：色数/同形/门禁 + 角色差分）"
python3 "$S/silhouette_check.py" >/dev/null
python3 "$S/char_check.py" >/dev/null
python3 "$SRC/tools/audit_event_cards.py"           # 事件卡机制区空槽门禁（有槽即非零退出）

echo "[art] 3/4 自洽断言（JSON.distinct_colors == 落盘 PNG 实测）"
python3 - "$SK" <<'PY'
import sys, os, json
from PIL import Image
sk = sys.argv[1]
j = json.load(open(os.path.join(sk, "references/hand/silhouette_check.json")))["per_building"]
bd = os.path.join(sk, "references/hand/buildings128/_render")
bad = []
for pid, r in j.items():
    p = os.path.join(bd, pid + ".png")
    if not os.path.isfile(p): bad.append((pid, "missing")); continue
    im = Image.open(p).convert("RGBA"); px = im.load()
    n = len(set(px[x, y] for y in range(im.height) for x in range(im.width) if px[x, y][3] > 0))
    if n != r["distinct_colors"]: bad.append((pid, r["distinct_colors"], n))
if bad:
    print("  FAIL 自洽断言：JSON 与 PNG 不一致 ->", bad); sys.exit(1)
print("  ok  - 19/19 distinct_colors 与落盘 PNG 一致")
gate = json.load(open(os.path.join(sk, "references/hand/silhouette_check.json")))["gate_pass"]
if not gate["pass"]:
    print("  FAIL silhouette gate_pass=false ->", gate); sys.exit(1)
print("  ok  - silhouette gate_pass=true")
cc = json.load(open(os.path.join(sk, "references/hand/char_check.json")))["gate_pass"]
if not cc["pass"]:
    print("  FAIL char gate_pass=false ->", cc); sys.exit(1)
print("  ok  - char gate_pass=true")
PY

echo "[art] 4/4 落盘（copy → frontend/assets/hand）"
mkdir -p "$ASSETS/hand/buildings128" "$ASSETS/hand/chars" "$ASSETS/hand/props"
cp "$SK/references/hand/buildings128/_render/"*.png "$ASSETS/hand/buildings128/"
cp "$SK/references/hand/chars/_render/"*.png "$ASSETS/hand/chars/"
cp "$SK/references/hand/props/_render/"*.png "$ASSETS/hand/props/"
cp "$SK/references/hand/silhouette_check.json" "$ASSETS/hand/silhouette_check.json"
cp "$SK/references/hand/char_check.json" "$ASSETS/hand/char_check.json"
echo "[art] PASS  产物: $ASSETS/hand/  (buildings128 / chars / props + checks)"

# ---- 批次指纹 batch_id（治"图旧资产新"脱钩；art-director 出图时对照）----
python3 - "$ASSETS/hand" <<'PY'
import hashlib, glob, os, sys
root = sys.argv[1]
roll = hashlib.sha256()
n = 0
import glob as _g
_groot = os.path.dirname(root)
groups = [_g.glob(os.path.join(root, g, "*.png")) for g in ("buildings128", "chars", "props")] \
       + [_g.glob(os.path.join(_groot, "generated", d, "*.png")) for d in ("tiles", "roads", "icons", "event_cards_hand")]
for fs in groups:
    for f in sorted(fs):
        roll.update((os.path.relpath(f, os.path.dirname(root)) + ":" + hashlib.sha256(open(f, "rb").read()).hexdigest() + "\n").encode())
        n += 1
print("[art] batch_id = %s  (%d files: hand[19b+8c+13p] + tiles+roads+icons + event_cards)" % (roll.hexdigest()[:16], n))
PY
