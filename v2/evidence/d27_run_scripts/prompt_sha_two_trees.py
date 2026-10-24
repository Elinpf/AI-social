#!/usr/bin/env python3
"""prompt_sha_two_trees.py —— D2.7「接线证明」：对**任一棵代码树**渲染 `_dialogue_prompt` / `_reply_prompt`，
打印 sha256 与末尾 200 字，用于两树逐字对比（master=C 臂 vs feat/d27-narration=B 臂）。

与 `tools/d9/prompt_fn_sha.py` 的区别：那个工具靠**同一树内的 env 开关两态**证接线；
D2.7 的改动**不是 env 开关**（直接改两处字符串），所以只能跨树渲染对比。

用法（每次都在同一台机、同一 PYTHONHASHSEED、不写字节码）：
  PYTHONDONTWRITEBYTECODE=1 python3 v2/evidence/d27_run_scripts/prompt_sha_two_trees.py --code-root <code 绝对路径> --out <json 输出>
退出码 0=渲染成功；2=导入/渲染失败。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _render(code_root: str) -> dict:
    sys.path.insert(0, code_root)
    for m in [k for k in list(sys.modules)
              if k.split(".")[0] in ("life", "engine", "orchestration")]:
        sys.modules.pop(m, None)

    from pathlib import Path
    from life.agent import LifeLayerAgent
    from life.persona import load_personas
    from life.dialogue_threads import DEFAULTS as DT_DEFAULTS

    personas = load_personas(Path(code_root) / "config" / "personas.json")
    pid = sorted(personas)[0]
    other = sorted(personas)[1] if len(personas) > 1 else pid
    names = {pid: "老周", other: "秀娘"}

    def _mk():
        a = object.__new__(LifeLayerAgent)
        a.agent_id = pid
        a.persona = personas[pid]
        a.peers = [other]
        a._peer_names = names
        a._rel_cache = {(other, "familiarity"): 20, (other, "affinity"): 5}
        a.needs = {"energy": 55, "satiety": 60, "social": 40, "esteem": 50,
                   "mastery": 50, "leisure": 45}
        a._rifts = {}
        a._rifts_seen = set()
        a._thread_replied_turn = {}
        a._goals_set_weeks = set()
        return a

    cfg = dict(DT_DEFAULTS)
    history = [(other, f"{names[other]}：show me")]
    a = _mk()
    d = a._dialogue_prompt("rel_maintain", [pid, other], cfg)
    r = a._reply_prompt(other, "rel_maintain", history, cfg)
    return {
        "code_root": code_root,
        "dialogue_prompt_sha256": _sha(d),
        "reply_prompt_sha256": _sha(r),
        "dialogue_prompt_tail": d[-240:],
        "reply_prompt_tail": r[-240:],
        "dialogue_prompt_len": len(d),
        "reply_prompt_len": len(r),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code-root", required=True)
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    try:
        res = _render(os.path.abspath(a.code_root))
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] 渲染失败: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    js = json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True)
    print(js)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(js + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
