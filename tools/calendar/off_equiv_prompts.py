#!/usr/bin/env python3
"""日历臂 OFF 等价性对拍器（跨树、只读、零 LLM）。

用途：证明 `LIFE_PROMPT_CALENDAR` 缺省（OFF）时，`_dialogue_prompt` / `_reply_prompt`
两条提示词的**文本 sha256** 与本臂接入前的树（master）逐字节相同。

用法（两棵树各跑一次，PYTHONPATH 指向目标树的 `code/`）：

    PYTHONPATH=<树>/code python3 <本文件> --tree <树> --out <读数 json>

判据（脚本只输出，不判定）：
  * 两树两次运行的 `dialogue_prompt_sha256` 与 `reply_prompt_sha256` 必须逐位相等；
  * OFF 时两条提示词内不得出现日历标记行（`今儿是什么日子：`）；
  * ON（`LIFE_PROMPT_CALENDAR=1`）时该标记行出现 1 次，且**减掉该行后**回到 OFF 文本。

纪律：只用公开/半公开 API 构最小 agent，不写仓库内文件（`--out` 指向 /tmp 或证据目录），
不调 LLM、不发事件、不读墙钟。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

CAL_MARK = "今儿是什么日子："


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _build_agent(tree: Path, tmp: Path):
    """按两棵树都存在的 API 构造一个最小 LifeLayerAgent（P003，同伴 P007=阿禾）。"""
    code = tree / "code"
    if str(code) not in sys.path:
        sys.path.insert(0, str(code))
    from life.agent import LifeLayerAgent
    from life.memory import HashEmbeddingModel, SideStore
    from life.persona import load_personas
    from life.tests.support.mini_kernel import MiniKernel

    cfg_dir = code / "config"
    places = {p["place_id"]: p for p in json.loads((cfg_dir / "places.json").read_text())["places"]}
    personas = load_personas(cfg_dir / "personas.json")
    persona = personas["P003"]
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
    return agent


def _wv(*, day_of_week: int = 2, day_type: str = "workday", rnd: int = 12):
    return SimpleNamespace(round=rnd, visible_events=[], location="market",
                           current_activity=None, inventory=(),
                           time=SimpleNamespace(slot="evening", day_of_week=day_of_week,
                                                day=day_of_week, day_type=day_type))


def _prompts(agent, wv):
    from life import dialogue_threads as DT
    cfg = dict(DT.DEFAULTS)
    history = [("P007", "阿禾：今儿个有点乏。")]
    return (agent._dialogue_prompt("rel_maintain", ["P003", "P007"], cfg, wv=wv),
            agent._reply_prompt("P007", "rel_maintain", history, cfg, wv=wv, turn=1))


def _strip_calendar(prompt: str) -> str:
    return "\n".join(ln for ln in prompt.split("\n") if not ln.startswith(CAL_MARK))


def run(tree: Path) -> dict:
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="calequiv_"))
    agent = _build_agent(tree, tmp)

    env_val = os.environ.get("LIFE_PROMPT_CALENDAR")
    os.environ.pop("LIFE_PROMPT_CALENDAR", None)          # 强制 OFF
    wv = _wv()
    d_off, r_off = _prompts(agent, wv)
    os.environ["LIFE_PROMPT_CALENDAR"] = "1"              # 再取 ON
    agent2 = _build_agent(tree, tmp)
    d_on, r_on = _prompts(agent2, wv)
    if env_val is None:
        os.environ.pop("LIFE_PROMPT_CALENDAR", None)
    else:
        os.environ["LIFE_PROMPT_CALENDAR"] = env_val

    out = {
        "tree": str(tree),
        "tree_head": _git(tree, "rev-parse", "HEAD"),
        "env_LIFE_PROMPT_CALENDAR_at_entry": env_val,
        "off": {
            "dialogue_prompt_sha256": _sha(d_off),
            "reply_prompt_sha256": _sha(r_off),
            "dialogue_len": len(d_off),
            "reply_len": len(r_off),
            "calendar_mark_count_dialogue": d_off.count(CAL_MARK),
            "calendar_mark_count_reply": r_off.count(CAL_MARK),
        },
        "on": {
            "dialogue_prompt_sha256": _sha(d_on),
            "reply_prompt_sha256": _sha(r_on),
            "dialogue_len": len(d_on),
            "reply_len": len(r_on),
            "calendar_mark_count_dialogue": d_on.count(CAL_MARK),
            "calendar_mark_count_reply": r_on.count(CAL_MARK),
            "on_minus_mark_equals_off_dialogue": _strip_calendar(d_on) == d_off,
            "on_minus_mark_equals_off_reply": _strip_calendar(r_on) == r_off,
            "delta_len_dialogue": len(d_on) - len(d_off),
            "delta_len_reply": len(r_on) - len(r_off),
        },
    }
    try:
        from life import calendar as CAL          # 仅本臂树有；master 树无 ⇒ 缺失即记 None
        out["lexicon_sha256"] = CAL.lexicon_sha256()
        out["lexicon_version"] = CAL.LEXICON_VERSION
    except Exception as exc:                       # noqa: BLE001
        out["lexicon_sha256"] = None
        out["lexicon_note"] = f"{type(exc).__name__}: {exc}"
    return out


def _git(tree: Path, *args: str) -> str | None:
    import subprocess
    try:
        return subprocess.check_output(["git", "-C", str(tree), *args],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:                              # noqa: BLE001
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True, help="目标树根（含 code/ 子目录）")
    ap.add_argument("--out", default=None, help="读数 json 输出路径（缺省打印到 stdout）")
    args = ap.parse_args()
    res = run(Path(args.tree).resolve())
    text = json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"[calendar-equiv] wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
