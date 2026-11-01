#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R51 提示词指纹探针（只读、零 LLM）：证明 `HITT_NEED_SPEECH` OFF 态与改动前**逐字节等价**。

## 为什么需要它

提示词原文**不落盘**（`LLM_CALL.payload` 只有 `prompt_hash`/`meta_digest`），所以"OFF 与改动前逐字节等价"
不能从 run.jsonl 里读出来，只能**在函数目录上**独立证明。本探针在**固定夹具**（同一 agent、同一 needs、
同一 topic/history）上把 `_dialogue_prompt` / `_reply_prompt` 的正文取 sha256，并在同一份夹具上比对
`_mood_line()` 的输出 —— 只要三个指纹两两相等，OFF 态就是逐字节等价。

## 夹具（固定，不随机、不读墙钟）

  * agent = `personas.json` 的 `P001`（真实 persona，但不跑世界）
  * `needs` = 6 维同时给三组固定值：`urgent`（有一维 <40）/ `noise`（全维 ≥40 但仍有"最紧"）/ `empty`（空）
  * `_dialogue_prompt("tpl-1", ["P001","P002"])`、`_reply_prompt("P002","tpl-1",history)` 两处装配点都取指纹

用法:
  python3 tools/r51/prompt_hash_probe.py --out-json /tmp/probe.json --label pre-change
  python3 tools/r51/prompt_hash_probe.py --out-json /tmp/probe_off.json --label post-change-off
  cmp /tmp/probe.json /tmp/probe_off.json   # 除 label 外应逐字节相等
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CODE = REPO / "code"
sys.path.insert(0, str(CODE))

from life.agent import LifeLayerAgent                      # noqa: E402
from life.memory import HashEmbeddingModel, SideStore      # noqa: E402
from life.persona import load_personas                     # noqa: E402

CONFIG = CODE / "config"

#: 三组固定 needs 夹具（顺序固定，字典序即输出顺序）
NEEDS_FIXTURES = {
    "urgent": {"satiety": 12, "energy": 55, "social": 60, "esteem": 62, "mastery": 58, "leisure": 51},
    "noise": {"satiety": 52, "energy": 55, "social": 60, "esteem": 62, "mastery": 58, "leisure": 51},
    "empty": {},
}

#: 旁白通道钉死（本探针只量 `_mood_line()` 这一处；旁白默认值变化不应污染指纹）
os.environ.setdefault("LIFE_PROMPT_NARRATION", "0")


class _StubKernel:
    def submit_intent(self, *a, **kw):  # pragma: no cover
        pass


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _build(tmp: Path) -> LifeLayerAgent:
    places = {p["place_id"]: p for p in
              json.loads((CONFIG / "places.json").read_text(encoding="utf-8"))["places"]}
    persona = load_personas(CONFIG / "personas.json")["P001"]
    return LifeLayerAgent("P001", persona, _StubKernel(),
                          side_store=SideStore(tmp / "side"),
                          embedding=HashEmbeddingModel(), places=places,
                          peers=["P001", "P002"], peer_names={"P001": "沈砚", "P002": "赵四"})


def probe(label: str) -> dict:
    tmp = Path("/tmp/r51_prompt_probe")
    tmp.mkdir(parents=True, exist_ok=True)
    out: dict = {"label": label, "env": {
        "HITT_NEED_SPEECH": os.environ.get("HITT_NEED_SPEECH", "<unset>"),
        "LIFE_PROMPT_NARRATION": os.environ.get("LIFE_PROMPT_NARRATION", "<unset>"),
    }, "fixtures": {}}
    for name, needs in NEEDS_FIXTURES.items():
        agent = _build(tmp)
        agent.needs = dict(needs)
        history = [("赵四", "早上好。"), ("沈砚", "早啊。")]
        d = agent._dialogue_prompt("tpl-1", ["P001", "P002"])
        r = agent._reply_prompt("P002", "tpl-1", history)
        ctx = agent._ctx_snapshot("P002", "tpl-1")
        out["fixtures"][name] = {
            "needs": dict(needs),
            "mood_line": agent._mood_line(),
            "mood_line_sha256": _sha(agent._mood_line()),
            "dialogue_prompt_sha256": _sha(d),
            "reply_prompt_sha256": _sha(r),
            "dialogue_prompt_len": len(d),
            "reply_prompt_len": len(r),
            "ctx_keys": sorted(ctx.keys()),
            "ctx_sha256": _sha(json.dumps(ctx, ensure_ascii=False, sort_keys=True)),
        }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="R51 提示词指纹探针（只读、零 LLM）")
    ap.add_argument("--label", default="")
    ap.add_argument("--out-json", default="")
    args = ap.parse_args(argv)
    res = probe(args.label)
    text = json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out_json:
        Path(args.out_json).write_text(text + "\n", encoding="utf-8")
    for name, f in res["fixtures"].items():
        print("%-7s mood=%-4s mood_line=%r" % (name, "sha:" + f["mood_line_sha256"][:8],
                                               f["mood_line"]))
        print("        dialogue=%s reply=%s ctx=%s keys=%s"
              % (f["dialogue_prompt_sha256"][:12], f["reply_prompt_sha256"][:12],
                 f["ctx_sha256"][:12], ",".join(f["ctx_keys"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
