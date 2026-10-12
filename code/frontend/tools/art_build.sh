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
python3 "$S/check_single_source.py"                    # 门禁：palette 单一真源（T246）
python3 "$SRC/tools/audit_event_cards.py"           # 事件卡机制区空槽门禁（有槽即非零退出）
python3 "$SRC/tools/char_game_size_check.py"        # 角色「游戏尺寸」两两剪影可辨性门禁
python3 "$SRC/tools/event_card_readability_check.py" # 事件卡「内联显示尺寸」可读性门禁

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
gs = json.load(open("frontend/tools/char_game_size.json"))["gate_pass"]
if not gs["pass"]:
    print("  FAIL char game-size gate_pass=false ->", gs); sys.exit(1)
print("  ok  - char game-size gate_pass=true (max_iou=%.3f)" % gs["max_iou"])
er = json.load(open("frontend/tools/event_card_readability.json"))["gate_pass"]
if not er["pass"]:
    print("  FAIL event-card readability gate_pass=false ->", er); sys.exit(1)
print("  ok  - event-card readability gate_pass=true (min_contrast=%.2f min_keep=%.2f)" % (er["min_contrast"], er["min_keep"]))
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
bid = roll.hexdigest()[:16]
import json as _json
rec = {"batch_id": bid, "total_files": n,
       "note": "美术资产批次指纹（治图旧资产新脱钩）；由 make art 生成，勿手改。"}
# 落盘到机检可读的单一真源（assets + skill references）
for dest in (os.path.join(os.path.dirname(root), "batch_id.json"),
             os.path.join(os.path.expanduser("~"), ".jiuwenswarm/agent/workspace/skills/qingxi-pixel-art/references/batch_id.json")):
    try:
        _json.dump(rec, open(dest, "w"), ensure_ascii=False, indent=2)
    except Exception as e:
        print("  warn batch_id.json write:", e)
print("[art] batch_id = %s  (%d files) -> frontend/assets/batch_id.json" % (bid, n))
PY
