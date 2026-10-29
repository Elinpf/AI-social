"""天气臂（weather / W-1「今儿天怎么样」）单测：

  * **OFF（默认）**：`_weather_line` 返回空串、`_weather` 为 None、两条提示词里不出现
    「今儿天怎么样」、`ctx` 不出现 `weather` 键；
  * **ON 且只差一行**：把 ON 提示词里那一行**原样减掉**后，与 OFF 提示词**逐字节相等**；
  * **确定性派生**：`weather_of_day(day, seed)` 同 seed 同 day 两次调用完全一致；
    换 seed 会变（天气确实由 seed 决定），且**不读墙钟、不引随机源**（源码层面断言）；
  * **季/天气自洽**：春/夏/秋 不出现雪；夏不出现「入冬」类措辞；
  * **不泄漏内部 token**：`clear` / `rain` / `spring` 这类 key 只进审计，**不进提示词**；
  * **审计键**：ON 时 `ctx.weather` 带 day/season/weather/seed + 该行 sha256，
    且 sha256 与真正拼进提示词的那一行一致。
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from life import dialogue_threads as DT
from life import weather as WX
from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.tests.support.mini_kernel import MiniKernel

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"
WX_MARK = "今儿天怎么样："


def _places() -> dict:
    return {p["place_id"]: p for p in json.loads((CONFIG / "places.json").read_text())["places"]}


def _build(tmp: Path):
    places = _places()
    personas = load_personas(CONFIG / "personas.json")
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
    return kernel, agent


def _wv(*, day: int = 2, rnd: int = 12):
    """最小 WorldView 替身：只带天气臂读的 `round` 与 `time.day`。"""
    return SimpleNamespace(round=rnd, visible_events=[], location="market",
                           current_activity=None, inventory=(),
                           time=SimpleNamespace(slot="evening", day=day, day_of_week=day % 7,
                                                day_type="workday"))


def _prompts(agent, wv):
    cfg = dict(DT.DEFAULTS)
    history = [("P007", "阿禾：今儿个有点乏。")]
    return (agent._dialogue_prompt("rel_maintain", ["P003", "P007"], cfg, wv=wv),
            agent._reply_prompt("P007", "rel_maintain", history, cfg, wv=wv, turn=1))


def _strip_weather(prompt: str) -> str:
    """把 ON 提示词里「今儿天怎么样：……」那一行原样减掉（模拟"两态只差一行"）。"""
    return "\n".join(ln for ln in prompt.split("\n") if not ln.startswith(WX_MARK))


# ---------------------------------------------------------------- 开关
def test_switch_default_off(monkeypatch):
    monkeypatch.delenv(WX.WEATHER_ENV, raising=False)
    assert WX.enabled() is False


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "on", "yes", " on "])
def test_switch_env_on(monkeypatch, val):
    monkeypatch.setenv(WX.WEATHER_ENV, val)
    assert WX.enabled() is True


@pytest.mark.parametrize("val", ["0", "false", "off", "no", "", "2", "enable"])
def test_switch_env_off(monkeypatch, val):
    monkeypatch.setenv(WX.WEATHER_ENV, val)
    assert WX.enabled() is False


# ---------------------------------------------------------------- 世界种子
def test_world_seed_default_and_invalid(monkeypatch):
    monkeypatch.delenv(WX.WORLD_SEED_ENV, raising=False)
    assert WX.world_seed() == 0
    monkeypatch.setenv(WX.WORLD_SEED_ENV, "42")
    assert WX.world_seed() == 42
    for bad in ("", "  ", "abc", "4.2"):
        monkeypatch.setenv(WX.WORLD_SEED_ENV, bad)
        assert WX.world_seed() == 0       # 非法 ⇒ 0，不抛、不读墙钟


# ---------------------------------------------------------------- 纯函数：季 / 天气
def test_season_of_day_mapping():
    assert [WX.season_of_day(d) for d in range(8)] == [
        "spring"] * 7 + ["summer"]
    assert WX.season_of_day(7 + 6) == "summer"
    assert WX.season_of_day(14) == "autumn"
    assert WX.season_of_day(21) == "winter"
    assert WX.season_of_day(28) == "spring"          # 4 季一循环
    assert WX.season_of_day(-1) in WX.SEASONS        # 负数不崩（对 int 取模仍合法）
    assert WX.season_of_day("bad") == "spring"       # 非法 ⇒ 退化为第一季


def test_weather_of_day_deterministic():
    """同 seed 同 day 两次派生完全一致（replay 纪律）。"""
    for day in range(0, 40):
        a = WX.weather_of_day(day, seed=42)
        b = WX.weather_of_day(day, seed=42)
        assert a == b, f"day={day} 两次派生不一致：{a} vs {b}"
        assert a in WX.WEATHER_KINDS


def test_weather_of_day_seed_sensitive():
    """不同 seed 在 40 天上至少有一天不同（天气确实由 seed 决定，不是常数）。"""
    diffs = sum(1 for day in range(40)
                if WX.weather_of_day(day, seed=42) != WX.weather_of_day(day, seed=43))
    assert diffs > 0, "换 seed 天气完全不变 ⇒ world_seed 未真正参与派生"


def test_weather_respects_season_table():
    """权重表是硬约束：某季权重为 0 的天气**永不出现**。"""
    for season in WX.SEASONS:
        allowed = {k for k, w in WX.WEATHER_WEIGHTS[season].items() if w > 0}
        days = [d for d in range(0, 28 * 12) if WX.season_of_day(d) == season]
        got = {WX.weather_of_day(d, seed=7) for d in days}
        assert got <= allowed, f"{season} 出现了权重为 0 的天气：{got - allowed}"
        assert got, f"{season} 一天天气都没派生出来"


def test_no_snow_outside_winter():
    """非冬季的 4 个季内所有天数（含未来回合）都不下雪。"""
    for d in range(0, 28 * 12):
        if WX.season_of_day(d) == "winter":
            continue
        assert WX.weather_of_day(d, seed=11) != "snow", f"day={d} 非冬季却下雪"


def test_pure_function_source_has_no_clock_or_randomness():
    """源码层硬断言：本模块不 import random / datetime / time（确定性可审计）。"""
    src = (CODE_DIR / "life" / "weather.py").read_text(encoding="utf-8")
    for bad in ("import random", "from random", "import datetime", "from datetime",
                "time.time(", "monotonic(", "time()"):
        assert bad not in src, f"确定性纪律被破坏：出现 {bad}"


# ---------------------------------------------------------------- 纯函数：render
def test_render_off_returns_empty(monkeypatch):
    monkeypatch.delenv(WX.WEATHER_ENV, raising=False)
    assert WX.render("P003", 12, 2) == ""


def test_render_on_contains_mark_and_human_words(monkeypatch):
    monkeypatch.setenv(WX.WEATHER_ENV, "1")
    line = WX.render("P003", 12, 2, seed=42)
    assert WX_MARK in line
    season = WX.season_of_day(2)
    kind = WX.weather_of_day(2, seed=42)
    words = WX.SEASON_WEATHER_WORDS.get((season, kind)) or WX.WEATHER_WORDS[kind]
    assert any(w in line for w in WX.SEASON_WORDS[season])
    assert any(w in line for w in words)
    for bad in WX.WEATHER_KINDS + WX.SEASONS:
        assert bad not in line, f"内部 token 泄漏进提示词：{bad}"
    assert "day" not in line and "seed" not in line


def test_render_deterministic(monkeypatch):
    monkeypatch.setenv(WX.WEATHER_ENV, "1")
    assert WX.render("P003", 12, 2, 42) == WX.render("P003", 12, 2, 42)
    # 同一天不同 agent/round：天气事实不变，措辞可从词表里变
    other = WX.render("P007", 13, 2, 42)
    assert WX_MARK in other
    assert WX.weather_of_day(2, 42) == WX.weather_of_day(2, 42)


def test_render_uses_env_seed_when_seed_omitted(monkeypatch):
    monkeypatch.setenv(WX.WEATHER_ENV, "1")
    monkeypatch.setenv(WX.WORLD_SEED_ENV, "42")
    assert WX.render("P003", 12, 2) == WX.render("P003", 12, 2, 42)


def test_lexicon_sha_stable_and_versioned():
    sha = WX.lexicon_sha256()
    assert len(sha) == 64
    assert WX.lexicon_sha256() == sha
    assert WX.LEXICON_VERSION.startswith("weather")


def test_audit_records_keys_not_human_words():
    line = "今儿天怎么样：开春了，阴着天。"
    a = WX.audit(2, "spring", "overcast", 42, line)
    assert a["day"] == 2 and a["season"] == "spring"
    assert a["weather"] == "overcast" and a["seed"] == 42
    assert a["line_sha256"] == WX._sha(line.strip())


# ---------------------------------------------------------------- agent 侧接线
def test_off_prompt_and_ctx_untouched(monkeypatch, tmp_path):
    monkeypatch.delenv(WX.WEATHER_ENV, raising=False)
    _, agent = _build(tmp_path)
    wv = _wv()
    assert agent._weather_line(wv) == ""
    assert agent._weather is None
    d, r = _prompts(agent, wv)
    assert WX_MARK not in d and WX_MARK not in r
    assert "weather" not in agent._ctx_snapshot("P007", "rel_maintain")


def test_on_inserts_one_line_and_off_is_exact_prefix_removal(monkeypatch, tmp_path):
    _, agent = _build(tmp_path)
    wv = _wv(day=2, rnd=12)
    monkeypatch.delenv(WX.WEATHER_ENV, raising=False)
    d_off, r_off = _prompts(agent, wv)
    monkeypatch.setenv(WX.WEATHER_ENV, "1")
    d_on, r_on = _prompts(agent, wv)
    assert d_on != d_off and r_on != r_off
    # 「只差那一行」：减掉该行后逐字节回到 OFF
    assert _strip_weather(d_on) == d_off
    assert _strip_weather(r_on) == r_off
    assert d_on.count(WX_MARK) == 1 and r_on.count(WX_MARK) == 1


def test_on_audit_key_matches_prompt_line(monkeypatch, tmp_path):
    monkeypatch.setenv(WX.WEATHER_ENV, "1")
    monkeypatch.setenv(WX.WORLD_SEED_ENV, "42")
    _, agent = _build(tmp_path)
    wv = _wv(day=9, rnd=108)          # day=9 ⇒ summer
    d, _ = _prompts(agent, wv)
    ctx = agent._ctx_snapshot("P007", "rel_maintain")
    wx = ctx.get("weather")
    assert wx is not None
    assert wx["day"] == 9 and wx["season"] == "summer" and wx["seed"] == 42
    assert wx["weather"] == WX.weather_of_day(9, 42)
    line = next(ln for ln in d.split("\n") if ln.startswith(WX_MARK))
    assert wx["line_sha256"] == WX._sha(line.strip())


def test_on_same_line_for_replay(monkeypatch, tmp_path):
    """同 (agent, round, day, seed) 两条提示词里的那一行逐字节相同（可 replay）。"""
    monkeypatch.setenv(WX.WEATHER_ENV, "1")
    monkeypatch.setenv(WX.WORLD_SEED_ENV, "42")
    _, agent = _build(tmp_path)
    wv = _wv(day=3, rnd=36)
    d1, r1 = _prompts(agent, wv)
    d2, r2 = _prompts(agent, wv)
    assert d1 == d2 and r1 == r2


def test_on_missing_time_fields_degrades_silently(monkeypatch, tmp_path):
    """世界视图缺 time ⇒ 不加天气、不抛异常（不打断对话）。"""
    monkeypatch.setenv(WX.WEATHER_ENV, "1")
    _, agent = _build(tmp_path)
    wv = SimpleNamespace(round=12, visible_events=[], location="market",
                         current_activity=None, inventory=(), time=None)
    assert agent._weather_line(wv) == ""
    assert agent._weather is None


# ---- T1 追加（life-dev, 2026-10-29）：跨进程确定性 = 真正的 replay 判据 -----------
# 注意：**不传 seed**，让派生走 env `HITT_WORLD_SEED`（这才是跑批实际路径）。
_DET_TABLE_SNIPPET = (
    "import json; from life import weather as WX; "
    "print(json.dumps({str(d): WX.weather_of_day(d) for d in range(12)}, "
    "ensure_ascii=False, sort_keys=True))"
)


def _derive_table_in_subprocess(env_extra: dict) -> str:
    """在**独立进程**里跑一次「同 seed 同 day 派生表」，返回 stdout。

    为什么要独立进程：`weather_of_day` 若不慎读了进程状态/墙钟/随机源，
    在同一进程内两次调用可能恰好相同（伪确定性）。只有**两个全新进程**给出逐字符
    相同的表，才等价于「重放/跨批可复现」（replay 纪律的硬判据）。
    """
    import os
    import subprocess
    import sys

    env = dict(os.environ)
    env.update(env_extra)
    env["PYTHONPATH"] = str(CODE_DIR)
    out = subprocess.run([sys.executable, "-c", _DET_TABLE_SNIPPET],
                         env=env, cwd=str(CODE_DIR), capture_output=True,
                         text=True, timeout=120)
    assert out.returncode == 0, f"子进程失败: {out.stderr}"
    return out.stdout.strip()


def test_weather_table_deterministic_across_processes():
    """同一 (world_seed=42, day) 在**两个独立进程**里必得同一天气表（可 replay）。"""
    a = _derive_table_in_subprocess({"HITT_WORLD_SEED": "42"})
    b = _derive_table_in_subprocess({"HITT_WORLD_SEED": "42"})
    assert a == b, f"跨进程派生不一致（非重新可复现）：\nA={a}\nB={b}"
    # 表里必须都是合法天气 key（空串 = 派生失败）
    table = json.loads(a)
    assert len(table) == 12 and all(v in WX.WEATHER_KINDS for v in table.values())


def test_weather_table_differs_with_other_seed_process():
    """换 world_seed（42 vs 43）在**独立进程**里 12 天内至少有一天不同。"""
    a = json.loads(_derive_table_in_subprocess({"HITT_WORLD_SEED": "42"}))
    c = json.loads(_derive_table_in_subprocess({"HITT_WORLD_SEED": "43"}))
    diff = [d for d in a if a[d] != c[d]]
    assert diff, "换 world_seed 天气表完全不变 ⇒ seed 未真正参与派生"
