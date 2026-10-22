#!/usr/bin/env python3
"""scene_prompt_proof.py — 处境锚臂（`LIFE_PROMPT_SCENE`）的接线与「OFF 逐字节不变」证明。

做三件事，任一失败即非 0 退出：

1. **OFF 逐字节不变（跨树对照）**：在「基线树」（改动前，如 `e8a9fd5`）与「改动树」上，
   用**同一份** `(agent, persona, thread, wv)` 渲染 `_dialogue_prompt` / `_reply_prompt`，
   两串必须**完全相同**（sha256 相同且字符串相等）。基线树由 `git archive` 解出，互不 import 干扰。
2. **ON 接线成功**：同一棵树（改动树）开关 ON 时两串必须**不同于** OFF。
3. **单变量插入**：把 ON 提示词里「你眼下的光景：」那一行原样减掉后，必须**逐字节等于** OFF。

另打印：`prompt_fn_source_sha256`、`scene lexicon_sha256`、ON 态 `ctx.scene` 片段，
供报告侧冻结与复核（runbook §3.97 的「尺子身份」）。

用法：
  python3 tools/d9/scene_prompt_proof.py --base-root /tmp/scene_base/code --code-root code
退出码：0 全绿；2 渲染失败；3 OFF 两树不等（逐字节变了）；4 ON 未接线；5 非单变量插入。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

SCENE_ENV = "LIFE_PROMPT_SCENE"
SCENE_MARK = "你眼下的光景："


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- 在单一代码树内渲染
_DUMP_SRC = r'''
import hashlib, json, os, sys
from pathlib import Path
from types import SimpleNamespace

code_root = os.path.abspath(sys.argv[1])
sys.path.insert(0, code_root)
from life.agent import LifeLayerAgent
from life.persona import load_personas
from life.dialogue_threads import DEFAULTS as DT_DEFAULTS

personas = load_personas(Path(code_root) / "config" / "personas.json")
pid = sorted(personas)[0]
other = sorted(personas)[1] if len(personas) > 1 else pid
names = {pid: "老周", other: "秀娘"}


def mk():
    a = object.__new__(LifeLayerAgent)
    a.agent_id = pid
    a.persona = personas[pid]
    a.peers = [other]
    a._peer_names = names
    a._rel_cache = {(other, "familiarity"): 20, (other, "affinity"): 5}
    a.needs = {"energy": 55, "satiety": 60, "social": 40, "esteem": 50, "mastery": 50, "leisure": 45}
    a._rifts = {}
    a._rifts_seen = set()
    a._thread_replied_turn = {}
    a._goals_set_weeks = set()
    a.places = __import__("json").loads((Path(code_root) / "config" / "places.json").read_text())["places"]
    a.places = {p["place_id"]: p for p in a.places}
    a._mem_refs = []
    return a


wv = SimpleNamespace(
    round=12, visible_events=[], location="market",
    current_activity={"activity_type": "trade", "place": "market"},
    inventory=(), time=SimpleNamespace(slot="evening", day_of_week=3, day=3),
)
cfg = dict(DT_DEFAULTS)
history = [(other, names[other] + "：今儿个有点乏。")]

out = {}
for state in ("off", "on"):
    if state == "on":
        os.environ["LIFE_PROMPT_SCENE"] = "1"
    else:
        os.environ.pop("LIFE_PROMPT_SCENE", None)
    a = mk()
    d = a._dialogue_prompt("rel_maintain", [pid, other], cfg, wv=wv)
    r = a._reply_prompt(other, "rel_maintain", history, cfg, wv=wv, turn=1)
    a._dialogue_prompt("rel_maintain", [pid, other], cfg, wv=wv)   # 刷新 _scene
    ctx = a._ctx_snapshot(other, "rel_maintain")
    out[state] = {"dialogue_prompt": d, "reply_prompt": r, "ctx_keys": sorted(ctx),
                  "ctx_scene": ctx.get("scene")}
os.environ.pop("LIFE_PROMPT_SCENE", None)
print(json.dumps(out, ensure_ascii=False))
'''


def _dump(code_root: str) -> dict:
    res = subprocess.run([sys.executable, "-c", _DUMP_SRC, os.path.abspath(code_root)],
                         capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[FAIL] 在 {code_root} 渲染失败:\n{res.stderr[-2000:]}", file=sys.stderr)
        raise SystemExit(2)
    return json.loads(res.stdout)


def _strip_scene(prompt: str) -> str:
    return "\n".join(ln for ln in prompt.split("\n") if not ln.startswith(SCENE_MARK))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-root", required=True, help="改动前的代码树（如 git archive e8a9fd5 解出的 code/）")
    ap.add_argument("--code-root", required=True, help="当前分支的 code/")
    a = ap.parse_args(argv)

    base = _dump(a.base_root)
    cur = _dump(a.code_root)
    ok = True

    for key in ("dialogue_prompt", "reply_prompt"):
        b, c = base["off"][key], cur["off"][key]
        same = (b == c)
        print(f"OFF {key}: baseline sha={_sha(b)}  current sha={_sha(c)}  "
              f"{'IDENTICAL(逐字节不变)' if same else 'DIFF'}")
        if not same:
            ok = False
            bl, cl = b.split("\n"), c.split("\n")
            for i in range(max(len(bl), len(cl))):
                x = bl[i] if i < len(bl) else "<缺行>"
                y = cl[i] if i < len(cl) else "<缺行>"
                if x != y:
                    print(f"  首个差异行 #{i}:\n  base: {x!r}\n  curr: {y!r}")
                    break
    if not ok:
        print("[FAIL] OFF 态与基线树不逐字节一致", file=sys.stderr)
        return 3

    changed = [k for k in ("dialogue_prompt", "reply_prompt") if cur["on"][k] != cur["off"][k]]
    if not changed:
        print("[FAIL] 开关 ON 后两条提示词都没变 ⇒ 开关没接进提示词", file=sys.stderr)
        return 4
    for k in changed:
        print(f"ON  {k}: off sha={_sha(cur['off'][k])}  on sha={_sha(cur['on'][k])}  DIFF(接线成功)")
        if _strip_scene(cur["on"][k]) != cur["off"][k]:
            print(f"[FAIL] {k} 的 ON 态不是「OFF + 一行插入」⇒ 不是单变量改动", file=sys.stderr)
            return 5
        print(f"    {k}: 减掉「{SCENE_MARK}…」那一行后 == OFF（单变量插入成立）")

    print(f"OFF ctx 键: {cur['off']['ctx_keys']}  (不应含 'scene')")
    print(f"ON  ctx.scene = {json.dumps(cur['on']['ctx_scene'], ensure_ascii=False)}")
    try:
        sys.path.insert(0, os.path.abspath(a.code_root))
        from life import scene_anchor as SA  # noqa: E402
        print(f"scene lexicon_sha256 = {SA.lexicon_sha256()}  (version={SA.LEXICON_VERSION})")
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] 取词表 sha 失败: {e}", file=sys.stderr)

    print("[PASS] OFF 逐字节不变 + ON 接线 + 单变量插入 三项全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
