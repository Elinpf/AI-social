#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R52 提示词指纹探针（只读、零 LLM、零跑批）。

## 为什么需要它

R52 修的是 B-8「处境锚取移动前快照」的时序缺陷：`ctx.scene.place` 过去取自
`WorldView.location`（本轮 perceive 阶段的快照），而消息真正的 `payload.place`
是 COMMUNICATE 阶段落盘时的**当轮实时场所**（`orchestration/integration.py::_do_social`
读 `st.agents[id]["location"]`）。两者在同一轮内该居民搬过地方时不一致
（R46-A1 实测 87/191 = 45.55%）。

提示词原文**不落盘**（`LLM_CALL.payload` 只有 `prompt_hash`），所以
「OFF 臂与改动前逐字节等价」只能在**函数目录上**证明。本探针在固定夹具上把
`_dialogue_prompt` / `_reply_prompt` 的正文取 sha256：

  * 夹具固定：同一 persona（P001）、同一 `needs`、同一 topic/history、
    同一 `WorldView`（快照场所 = `residence`）、同一 stub kernel（实时场所 = `library`）。
  * 三组夹具：`no_move`（快照场所 == 实时场所，旧缺陷不发生）/ `stale`（快照 residence、实时 library）/
    `stale_no_act`（同上但无进行中活动）。
  * 两种开关态：
      - `legacy`（`LIFE_PROMPT_SCENE=1`，`HITT_SCENE_FRESH` 不设）＝ 改动前的取值路径；
      - `fresh`（`LIFE_PROMPT_SCENE=1`，`HITT_SCENE_FRESH=1`）＝ 修好后的取值路径。
  * 判定（报告 §4 引用）：
      - **OFF 逐字节等价**：`legacy` 指纹必须与「改动前代码」跑出的 `legacy` 指纹**完全相等**；
      - **ON 只差场所那一段**：`fresh` 与 `legacy` 的差别必须只在 `你在{场所名}` 这一处，
        其余（时段词、活动词、收尾句）逐字节相同。

用法:
  python3 tools/r52/prompt_hash_probe.py --label pre-change --out-json <path>
  python3 tools/r52/prompt_hash_probe.py --label post-change --out-json <path>
  # 两文件除 label 外应逐字节相等（改动前 legacy == 改动后 legacy）
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
from life.ports import TimeCoord, WorldView                # noqa: E402

CONFIG = CODE / "config"

#: 固定时段（不读墙钟）：时段词由 sha256(agent|round|slot|kind) 选，round/slot 固定即可复现
_SLOT = "afternoon"
_ROUND = 7

#: 三组夹具：(快照场所, 实时场所, 进行中活动)
FIXTURES = {
    "no_move": ("residence", "residence", "self_care"),
    "stale": ("residence", "library", "learn"),
    "stale_no_act": ("residence", "library", None),
}

#: 旁白通道钉死（本探针只量场景行与"场所那一段"，旁白默认值变化不应污染指纹）
os.environ.setdefault("LIFE_PROMPT_NARRATION", "0")


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class _StubKernel:
    """只实现 `perceive()`：返回**实时**场所（模拟 COMMUNICATE 阶段的状态）。

    改动前的代码**从不调用** `perceive()`（只看传进来的 wv 快照），
    所以同一夹具可以在改动前后各跑一次、指纹可比。
    """

    live_place = "residence"
    live_activity = None

    def perceive(self, agent_id):
        return WorldView(
            agent_id=agent_id, round=_ROUND, time=_time_coord(), status="alive",
            location=self.live_place, cash=100, net_worth=100, visible_events=(),
            memory_refs=(), inventory=(), transferable_goods=(),
            current_activity=({"activity_type": self.live_activity, "place": self.live_place}
                              if self.live_activity else None),
        )

    def submit_intent(self, *a, **kw):  # pragma: no cover
        pass


def _time_coord() -> TimeCoord:
    return TimeCoord(week=1, day=_ROUND // 2, day_of_week=1, day_type="workday",
                     slot=_SLOT, tick_in_slot=0)


def _snapshot_wv(place: str, activity: str | None) -> WorldView:
    return WorldView(
        agent_id="P001", round=_ROUND, time=_time_coord(), status="alive",
        location=place, cash=100, net_worth=100, visible_events=(), memory_refs=(),
        inventory=(), transferable_goods=(),
        current_activity=({"activity_type": activity, "place": place} if activity else None),
    )


def _build(tmp: Path, kernel: _StubKernel) -> LifeLayerAgent:
    places = {p["place_id"]: p for p in
              json.loads((CONFIG / "places.json").read_text(encoding="utf-8"))["places"]}
    persona = load_personas(CONFIG / "personas.json")["P001"]
    return LifeLayerAgent("P001", persona, kernel,
                          side_store=SideStore(tmp / "side"),
                          embedding=HashEmbeddingModel(), places=places,
                          peers=["P001", "P002"], peer_names={"P001": "沈砚", "P002": "赵四"})


def probe(label: str) -> dict:
    tmp = Path("/tmp/r52_prompt_probe")
    tmp.mkdir(parents=True, exist_ok=True)
    places = {p["place_id"]: p for p in
              json.loads((CONFIG / "places.json").read_text(encoding="utf-8"))["places"]}
    out: dict = {
        "label": label,
        "env": {
            "LIFE_PROMPT_SCENE": os.environ.get("LIFE_PROMPT_SCENE", "<unset>"),
            "HITT_SCENE_FRESH": os.environ.get("HITT_SCENE_FRESH", "<unset>"),
            "LIFE_PROMPT_NARRATION": os.environ.get("LIFE_PROMPT_NARRATION", "<unset>"),
        },
        "fixtures": {},
    }
    for name, (snap_place, live_place, activity) in FIXTURES.items():
        kernel = _StubKernel()
        kernel.live_place = live_place
        kernel.live_activity = activity
        agent = _build(tmp, kernel)
        agent.needs = {"satiety": 55, "energy": 60, "social": 58,
                       "esteem": 62, "mastery": 57, "leisure": 50}
        wv = _snapshot_wv(snap_place, activity)
        history = [("赵四", "早上好。"), ("沈砚", "早啊。")]
        d = agent._dialogue_prompt("tpl-1", ["P001", "P002"], wv=wv)
        r = agent._reply_prompt("P002", "tpl-1", history, wv=wv)
        scene_line = agent._scene_line(_snapshot_wv(snap_place, activity))
        ctx = agent._ctx_snapshot("P002", "tpl-1")
        out["fixtures"][name] = {
            "snapshot_place": snap_place,
            "live_place": live_place,
            "activity": activity,
            "snapshot_place_name_cn": str((places.get(snap_place) or {}).get("name_cn") or ""),
            "live_place_name_cn": str((places.get(live_place) or {}).get("name_cn") or ""),
            "scene_line": scene_line.strip(),
            "scene_line_sha256": _sha(scene_line),
            "scene_audit": agent._scene,
            "dialogue_prompt_sha256": _sha(d),
            "reply_prompt_sha256": _sha(r),
            "dialogue_prompt_len": len(d),
            "reply_prompt_len": len(r),
            "ctx_keys": sorted(ctx.keys()),
            "ctx_sha256": _sha(json.dumps(ctx, ensure_ascii=False, sort_keys=True)),
        }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="R52 提示词指纹探针（只读、零 LLM）")
    ap.add_argument("--label", default="")
    ap.add_argument("--out-json", default="")
    args = ap.parse_args(argv)
    res = probe(args.label)
    text = json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out_json:
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(text + "\n", encoding="utf-8")
    print("env: " + json.dumps(res["env"], ensure_ascii=False, sort_keys=True))
    for name, f in res["fixtures"].items():
        print("%-13s scene=%-28r dialogue=%s reply=%s ctx=%s"
              % (name, f["scene_line"], f["dialogue_prompt_sha256"][:12],
                 f["reply_prompt_sha256"][:12], f["ctx_sha256"][:12]))
        print("               audit=%s" % json.dumps(f["scene_audit"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
