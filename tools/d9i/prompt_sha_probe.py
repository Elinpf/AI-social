#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D9i 旁白通道臂：prompt 逐字节等价的可复算探针。

打印三条 prompt（`_dialogue_prompt` / `_reply_prompt`）在三种 env 状态下的 sha256：
  - env 未设（= 现状基线）
  - LIFE_PROMPT_NARRATION=0（显式关）
  - LIFE_PROMPT_NARRATION=1（开）

用法（仓库根目录）：
    python3 tools/d9i/prompt_sha_probe.py
    python3 tools/d9i/prompt_sha_probe.py --repo <另一份 checkout>   # 与改动前基线对比

判据：未设与 =0 两条输出必须完全相同；=1 只应改变收尾指令那一段。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[2]


def _pairs(repo: Path):
    sys.path.insert(0, str(repo / "code"))
    from life import dialogue_threads as DT  # noqa: E402
    from life.agent import LifeLayerAgent  # noqa: E402
    from life.memory import HashEmbeddingModel, SideStore  # noqa: E402
    from life.persona import load_personas  # noqa: E402
    from life.tests.support.mini_kernel import MiniKernel  # noqa: E402

    cfg_dir = repo / "code" / "config"
    places = {p["place_id"]: p for p in json.loads((cfg_dir / "places.json").read_text())["places"]}
    personas = load_personas(cfg_dir / "personas.json")
    persona = personas["P003"]
    tmp = Path(tempfile.mkdtemp())
    kernel = MiniKernel(seed=7, places=places)
    kernel._emit("AGENT_BORN", {"agent_id": "P003", "home_place": persona.home_place,
                                "needs_init": persona.needs_init}, phase=0, actor="SYSTEM")
    kernel._emit("AGENT_BORN", {"agent_id": "P007",
                                "home_place": personas["P007"].home_place,
                                "needs_init": personas["P007"].needs_init},
                 phase=0, actor="SYSTEM")
    agent = LifeLayerAgent("P003", persona, kernel, side_store=SideStore(tmp / "side"),
                           embedding=HashEmbeddingModel(), places=places,
                           peer_names={"P007": "阿禾"})
    wv = SimpleNamespace(round=12, visible_events=[], location="market",
                         current_activity={"activity_type": "trade", "place": "market"},
                         inventory=(), time=SimpleNamespace(slot="evening", day_of_week=3, day=3))
    cfg = dict(DT.DEFAULTS)
    hist = [("P007", "阿禾：今儿个有点乏。")]
    return (agent._dialogue_prompt("rel_maintain", ["P003", "P007"], cfg, wv=wv),
            agent._reply_prompt("P007", "rel_maintain", hist, cfg, wv=wv, turn=1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(REPO))
    args = ap.parse_args()
    repo = Path(args.repo).resolve()

    saved = os.environ.pop("LIFE_PROMPT_NARRATION", None)
    out = {}
    for label, val in (("unset", None), ("0", "0"), ("1", "1")):
        if val is None:
            os.environ.pop("LIFE_PROMPT_NARRATION", None)
        else:
            os.environ["LIFE_PROMPT_NARRATION"] = val
        p_init, p_reply = _pairs(repo)
        out[label] = {
            "initiate_sha256": hashlib.sha256(p_init.encode()).hexdigest(),
            "reply_sha256": hashlib.sha256(p_reply.encode()).hexdigest(),
            "initiate_len": len(p_init), "reply_len": len(p_reply),
        }
    if saved is not None:
        os.environ["LIFE_PROMPT_NARRATION"] = saved
    print(json.dumps({"repo": str(repo), "prompts": out}, ensure_ascii=False, indent=1))
    ok = (out["unset"] == out["0"]) and (out["unset"] != out["1"])
    print("VERDICT:", "PASS (unset == 0, 1 differs)" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
