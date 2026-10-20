#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R6-T2 · 证据探针：`HITT_DIALOGUE_REPAIR` env 是否真的具有**优先级**（两臂仅开关不同）。

只跑**离线 mock**（不联网、不调真 LLM）：真内核 + 一个确定性 stub LLM（人格无关，
"措辞"由 stub 按 prompt 哈希决定，其中一部分是负向话 ⇒ 让机制有旧账可记）。

两臂：
  off : 不设 env，config/dialogue_repair.json = enabled:false
  on  : HITT_DIALOGUE_REPAIR=1，**同一份 config**

输出（stdout，可逐字引用）：
  * 生效参数（证明 env 覆盖了 config）
  * MSG_* 条数、`dialogue_rift` **键出现次数**（不是 null，是键存在与否）
  * 样例字段
  * **body 逐字 ⊆ stub 输出集合**（证明机制没有向 body 拼任何模板文本）
  * bodies 的 sha256（两臂可对比）

用法（在仓库根执行，两臂各一次）：
    python3 v2/evidence/f4_env_priority_probe.py off
    HITT_DIALOGUE_REPAIR=1 python3 v2/evidence/f4_env_priority_probe.py on
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))

from life import dialogue_repair as DR                     # noqa: E402
from life.llm import LLMResult, RuleBasedLLM               # noqa: E402

#: stub LLM 的"措辞库"（**这是模型侧的输出**，不是机制拼接；机制只读不写）
NEG = "你这话我不太爱听，算了，我心里有点憋屈，也生气。"
REP = "抱歉，刚才是我误会了，说开了就好，别放在心上。"
NEU = "今儿天不错，晒得人舒服。"
POS = "街上可真热闹，大家伙都挺高兴。"
STUB_BODIES = (NEG, REP, NEU, POS)


class StubLLM:
    """确定性离线 stub：purpose=dialogue 时按 prompt 哈希选一句；其余交 RuleBasedLLM。"""

    name = "stub-offline"
    _rule = RuleBasedLLM()

    def call(self, purpose, prompt, *, model=None, meta=None):
        if purpose != "dialogue":
            return self._rule.call(purpose, prompt, model=model, meta=meta)
        k = int(hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8], 16) % 4
        text = STUB_BODIES[k]
        return LLMResult(text=text, tokens_in=len(prompt.split()), tokens_out=len(text.split()),
                         cache_key=f"stub:{purpose}:{hashlib.sha256(prompt.encode()).hexdigest()[:24]}",
                         model=self.name)


def main(arm: str) -> int:
    params = DR.load_params()
    from orchestration.integration import build_world
    out = {"arm": arm, "env_HITT_DIALOGUE_REPAIR": os.environ.get("HITT_DIALOGUE_REPAIR"),
           "config_file": str(ROOT / "code" / "config" / "dialogue_repair.json"),
           "effective_params": params}
    with tempfile.TemporaryDirectory() as d:
        w = build_world(seed=7, n=6, llm=StubLLM(), side_root=Path(d) / "side")
        eng = w["engine"]
        for r in range(40):
            eng.run_round(r)
        msgs = [rec for rec in eng.ledger.records
                if rec["type"] in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")]
        bodies = [m["payload"].get("body") or "" for m in msgs]
        out["n_msgs"] = len(msgs)
        out["n_dialogue_rift_key"] = sum(1 for m in msgs if "dialogue_rift" in (m["payload"] or {}))
        out["n_dialogue_rift_null"] = sum(1 for m in msgs
                                          if (m["payload"] or {}).get("dialogue_rift") is None
                                          and "dialogue_rift" in (m["payload"] or {}))
        samples = [m["payload"]["dialogue_rift"] for m in msgs
                   if "dialogue_rift" in (m["payload"] or {})][:3]
        out["samples"] = samples
        # body 逐字检查：每条都必须**恰好等于** stub 的某一句（⇒ 机制未拼接任何模板文本）
        bad = [b for b in bodies if b.strip() not in STUB_BODIES]
        out["n_body_not_in_stub_set"] = len(bad)
        out["examples_body_not_in_stub_set"] = bad[:3]
        out["bodies_sha256"] = hashlib.sha256(
            json.dumps(bodies, ensure_ascii=False).encode("utf-8")).hexdigest()
        out["body_contains_ablation_phrase"] = any(
            ph in b for b in bodies
            for ph in __import__("devtools.repair_ablation", fromlist=["x"]).FRICTION_PHRASES
            + __import__("devtools.repair_ablation", fromlist=["x"]).REPAIR_PHRASES)
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "off"))
