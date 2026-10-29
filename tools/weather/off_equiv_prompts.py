#!/usr/bin/env python3
"""天气臂 OFF 等价性对拍器（跨树、只读、零 LLM）。

用途：证明 `HITT_WEATHER` 缺省（OFF）时，`_dialogue_prompt` / `_reply_prompt`
两条提示词的**文本 sha256** 与本臂接入前的树（origin/master）逐字节相同；
顺带证明「同 seed 同 day 天气派生一致」（确定性）。

用法（两棵树各跑一次，PYTHONPATH 指向目标树的 `code/`）：

    PYTHONPATH=<树>/code python3 <本文件> --tree <树> --out <读数 json>

判据（脚本只输出，不判定）：
  * 两树两次运行的 `off.dialogue_prompt_sha256` 与 `off.reply_prompt_sha256` 必须逐位相等；
  * OFF 时两条提示词内不得出现天气标记行（`今儿天怎么样：`）；
  * ON（`HITT_WEATHER=1`）时该标记行出现 1 次，且**减掉该行后**回到 OFF 文本；
  * `determinism.day_weather_table_sha256` 两次运行必须相同（同 seed 同 day ⇒ 同天气）。

纪律：只用公开/半公开 API 构最小 agent，不写仓库内文件（`--out` 指向 /tmp 或证据目录），
不调 LLM、不发事件、不读墙钟。基线树用 `git archive origin/master | tar -x -C <dir>` 取，
**不建 worktree、不动仓库工作区**。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

WX_MARK = "今儿天怎么样："
#: 派生表覆盖的天数（1 天 = 12 回合；12 天覆盖 spring→summer 跨季边界）
TABLE_DAYS = 12
TABLE_SEED = 42


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git(tree: Path, *args: str) -> str | None:
    import subprocess
    try:
        return subprocess.check_output(["git", "-C", str(tree), *args],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:                              # noqa: BLE001
        return None


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
    return LifeLayerAgent("P003", persona, kernel, side_store=SideStore(tmp / "side"),
                          embedding=HashEmbeddingModel(), places=places,
                          peer_names={"P007": "阿禾"})


def _wv(*, day: int = 2, rnd: int = 29):
    """最小 WorldView 替身：只带天气臂读的 `round` / `time.day`（+ scene 臂的字段留空）。"""
    return SimpleNamespace(round=rnd, visible_events=[], location="market",
                           current_activity=None, inventory=(),
                           time=SimpleNamespace(slot="evening", day=day, day_of_week=day % 7,
                                                day_type="workday"))


def _prompts(agent, wv):
    from life import dialogue_threads as DT
    cfg = dict(DT.DEFAULTS)
    history = [("P007", "阿禾：今儿个有点乏。")]
    return (agent._dialogue_prompt("rel_maintain", ["P003", "P007"], cfg, wv=wv),
            agent._reply_prompt("P007", "rel_maintain", history, cfg, wv=wv, turn=1))


def _strip_weather(prompt: str) -> str:
    return "\n".join(ln for ln in prompt.split("\n") if not ln.startswith(WX_MARK))


def _determinism_table(tree: Path) -> dict:
    """同 seed 同 day 派生两遍，给出逐日表与表指纹（基线树无 weather 模块 ⇒ None）。"""
    try:
        from life import weather as WX
    except Exception as exc:                       # noqa: BLE001
        return {"available": False, "note": f"{type(exc).__name__}: {exc}"}
    pass1 = [WX.weather_of_day(d, seed=TABLE_SEED) for d in range(TABLE_DAYS)]
    pass2 = [WX.weather_of_day(d, seed=TABLE_SEED) for d in range(TABLE_DAYS)]
    seasons = [WX.season_of_day(d) for d in range(TABLE_DAYS)]
    return {
        "available": True,
        "lexicon_version": WX.LEXICON_VERSION,
        "lexicon_sha256": WX.lexicon_sha256(),
        "days_per_season": WX.DAYS_PER_SEASON,
        "seed": TABLE_SEED,
        "table_days": TABLE_DAYS,
        "weather_by_day": pass1,
        "season_by_day": seasons,
        "two_passes_identical": pass1 == pass2,
        "day_weather_table_sha256": _sha(json.dumps(pass1, ensure_ascii=False)),
    }


def run(tree: Path) -> dict:
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="wxequiv_"))
    env_switch = os.environ.get("HITT_WEATHER")
    env_seed = os.environ.get("HITT_WORLD_SEED")
    os.environ.pop("HITT_WEATHER", None)                  # 强制 OFF（未设置 == OFF）
    os.environ["HITT_WORLD_SEED"] = str(TABLE_SEED)
    wv = _wv()
    agent = _build_agent(tree, tmp)
    d_off, r_off = _prompts(agent, wv)
    ctx_off_has_weather = "weather" in agent._ctx_snapshot("P007", "rel_maintain")

    os.environ["HITT_WEATHER"] = "1"                      # 再取 ON
    agent2 = _build_agent(tree, tmp)
    d_on, r_on = _prompts(agent2, wv)
    ctx_on = agent2._ctx_snapshot("P007", "rel_maintain").get("weather")
    ctx_on_keys = sorted(ctx_on) if isinstance(ctx_on, dict) else None

    if env_switch is None:
        os.environ.pop("HITT_WEATHER", None)
    else:
        os.environ["HITT_WEATHER"] = env_switch
    if env_seed is None:
        os.environ.pop("HITT_WORLD_SEED", None)
    else:
        os.environ["HITT_WORLD_SEED"] = env_seed

    out = {
        "tree": str(tree),
        "tree_head": _git(tree, "rev-parse", "HEAD"),
        "env_HITT_WEATHER_at_entry": env_switch,
        "off": {
            "dialogue_prompt_sha256": _sha(d_off),
            "reply_prompt_sha256": _sha(r_off),
            "dialogue_len": len(d_off),
            "reply_len": len(r_off),
            "weather_mark_count_dialogue": d_off.count(WX_MARK),
            "weather_mark_count_reply": r_off.count(WX_MARK),
            "ctx_has_weather_key": ctx_off_has_weather,
        },
        "on": {
            "dialogue_prompt_sha256": _sha(d_on),
            "reply_prompt_sha256": _sha(r_on),
            "dialogue_len": len(d_on),
            "reply_len": len(r_on),
            "weather_mark_count_dialogue": d_on.count(WX_MARK),
            "weather_mark_count_reply": r_on.count(WX_MARK),
            "on_minus_mark_equals_off_dialogue": _strip_weather(d_on) == d_off,
            "on_minus_mark_equals_off_reply": _strip_weather(r_on) == r_off,
            "delta_len_dialogue": len(d_on) - len(d_off),
            "delta_len_reply": len(r_on) - len(r_off),
            "ctx_weather_keys": ctx_on_keys,
        },
        "determinism": _determinism_table(tree),
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True, help="目标树根（含 code/ 子目录）")
    ap.add_argument("--out", default=None, help="读数 json 输出路径（缺省打印到 stdout）")
    args = ap.parse_args()
    res = run(Path(args.tree).resolve())
    text = json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"[weather-equiv] wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
