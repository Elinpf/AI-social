"""日历臂（calendar / C1「今天是什么日子」）单测：

  * **OFF（默认）**：`_calendar_line` 返回空串、`_calendar` 为 None、两条提示词里不出现
    「今儿是什么日子」、`ctx` 不出现 `calendar` 键；
  * **ON 且只差一行**：把 ON 提示词里那一行**原样减掉**后，与 OFF 提示词**逐字节相等**；
  * **三态渲染**：workday / weekend / day_of_week 三个分支都渲染成中文人话，
    且**不泄漏** `workday` / `weekend` 这类内部 token（防 L-8c / L-13）；
  * **确定性**：同一 (agent|round) 两次渲染完全相同（可 replay）；
  * **审计键**：ON 时 `ctx.calendar` 带 day_of_week / day_type + 该行 sha256，
    且 sha256 与真正拼进提示词的那一行一致。
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from life import calendar as CAL
from life import dialogue_threads as DT
from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.tests.support.mini_kernel import MiniKernel

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"
CAL_MARK = "今儿是什么日子："


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


def _wv(*, day_of_week: int = 2, day_type: str = "workday", rnd: int = 12):
    """最小 WorldView 替身：只带日历臂读的两个字段（+ scene 臂不参与，故不设场所）。"""
    return SimpleNamespace(round=rnd, visible_events=[], location="market",
                           current_activity=None, inventory=(),
                           time=SimpleNamespace(slot="evening", day_of_week=day_of_week,
                                                day=day_of_week, day_type=day_type))


def _prompts(agent, wv):
    cfg = dict(DT.DEFAULTS)
    history = [("P007", "阿禾：今儿个有点乏。")]
    return (agent._dialogue_prompt("rel_maintain", ["P003", "P007"], cfg, wv=wv),
            agent._reply_prompt("P007", "rel_maintain", history, cfg, wv=wv, turn=1))


def _strip_calendar(prompt: str) -> str:
    """把 ON 提示词里「今儿是什么日子：……」那一行原样减掉（模拟"两态只差一行"）。"""
    return "\n".join(ln for ln in prompt.split("\n") if not ln.startswith(CAL_MARK))


# ---------------------------------------------------------------- 开关
def test_switch_default_off(monkeypatch):
    monkeypatch.delenv(CAL.CALENDAR_ENV, raising=False)
    assert CAL.enabled() is False


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "on", "yes", " on "])
def test_switch_env_on(monkeypatch, val):
    monkeypatch.setenv(CAL.CALENDAR_ENV, val)
    assert CAL.enabled() is True


@pytest.mark.parametrize("val", ["0", "false", "off", "no", "", "2", "enable"])
def test_switch_env_off(monkeypatch, val):
    monkeypatch.setenv(CAL.CALENDAR_ENV, val)
    assert CAL.enabled() is False


# ---------------------------------------------------------------- 纯函数：render
def test_render_off_returns_empty(monkeypatch):
    monkeypatch.delenv(CAL.CALENDAR_ENV, raising=False)
    assert CAL.render("P003", 12, 6, "weekend") == ""


def test_render_on_workday(monkeypatch):
    """分支 1：workday + 周几 都渲染成人话。"""
    monkeypatch.setenv(CAL.CALENDAR_ENV, "1")
    line = CAL.render("P003", 12, 2, "workday")
    assert CAL_MARK in line
    assert "周三" in line
    assert any(w in line for w in CAL.DAY_TYPE_WORDS["workday"])
    for bad in ("workday", "weekend", "day_of_week", "day_type"):
        assert bad not in line, f"内部 token 泄漏进提示词：{bad}"


def test_render_on_weekend(monkeypatch):
    """分支 2：weekend 与 workday 的措辞集合不相交。"""
    monkeypatch.setenv(CAL.CALENDAR_ENV, "1")
    line = CAL.render("P003", 62, 6, "weekend")
    assert CAL_MARK in line
    assert "周日" in line
    assert any(w in line for w in CAL.DAY_TYPE_WORDS["weekend"])
    assert not any(w in line for w in CAL.DAY_TYPE_WORDS["workday"])
    for bad in ("workday", "weekend"):
        assert bad not in line


def test_render_weekday_only_when_day_type_unknown(monkeypatch):
    """分支 3：day_type 缺失/未知 ⇒ 只写周几，不写日子类型，也不泄 token。"""
    monkeypatch.setenv(CAL.CALENDAR_ENV, "1")
    for dt in (None, "", "holiday"):
        line = CAL.render("P003", 12, 4, dt)
        assert CAL_MARK in line and "周五" in line
        assert "holiday" not in line
        assert not any(w in line for w in CAL.DAY_TYPE_WORDS["workday"])


def test_render_day_type_only_when_dow_missing(monkeypatch):
    """day_of_week 缺失但 day_type 有 ⇒ 仍能成句（宁缺不写周几）。"""
    monkeypatch.setenv(CAL.CALENDAR_ENV, "1")
    line = CAL.render("P003", 12, None, "weekend")
    assert CAL_MARK in line
    assert not any(w in line for w in CAL.WEEKDAY_WORDS.values())
    assert any(w in line for w in CAL.DAY_TYPE_WORDS["weekend"])


def test_render_all_empty_materials_returns_empty(monkeypatch):
    monkeypatch.setenv(CAL.CALENDAR_ENV, "1")
    assert CAL.render("P003", 12, None, None) == ""
    assert CAL.render("P003", 12, "", "") == ""


def test_render_deterministic(monkeypatch):
    monkeypatch.setenv(CAL.CALENDAR_ENV, "1")
    a = CAL.render("P003", 12, 2, "workday")
    b = CAL.render("P003", 12, 2, "workday")
    assert a == b
    # 不同 agent/round 允许措辞不同，但必须仍在冻结词表内
    c = CAL.render("P007", 13, 2, "workday")
    assert "周三" in c
    assert any(w in c for w in CAL.DAY_TYPE_WORDS["workday"])


def test_weekday_table_matches_five_workdays_two_weekends():
    """命名层自洽：0..4 上工日（周一..周五）、5..6 歇日（周六/周日）。"""
    assert [CAL.WEEKDAY_WORDS[i] for i in range(7)] == [
        "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    assert set(CAL.DAY_TYPE_WORDS) == {"workday", "weekend"}


def test_lexicon_sha_stable_and_versioned():
    sha = CAL.lexicon_sha256()
    assert len(sha) == 64
    assert CAL.lexicon_sha256() == sha
    assert CAL.LEXICON_VERSION.startswith("calendar")


# ---------------------------------------------------------------- agent 侧接线
def test_off_prompt_and_ctx_untouched(monkeypatch, tmp_path):
    monkeypatch.delenv(CAL.CALENDAR_ENV, raising=False)
    _, agent = _build(tmp_path)
    wv = _wv()
    assert agent._calendar_line(wv) == ""
    assert agent._calendar is None
    d, r = _prompts(agent, wv)
    assert CAL_MARK not in d and CAL_MARK not in r
    assert "calendar" not in agent._ctx_snapshot("P007", "rel_maintain")


def test_on_inserts_one_line_and_off_is_exact_prefix_removal(monkeypatch, tmp_path):
    _, agent = _build(tmp_path)
    wv = _wv(day_of_week=2, day_type="workday")
    monkeypatch.delenv(CAL.CALENDAR_ENV, raising=False)
    d_off, r_off = _prompts(agent, wv)
    monkeypatch.setenv(CAL.CALENDAR_ENV, "1")
    d_on, r_on = _prompts(agent, wv)
    assert d_on != d_off and r_on != r_off
    # 「只差那一行」：减掉该行后逐字节回到 OFF
    assert _strip_calendar(d_on) == d_off
    assert _strip_calendar(r_on) == r_off
    assert d_on.count(CAL_MARK) == 1 and r_on.count(CAL_MARK) == 1


def test_on_weekend_reaches_both_prompts(monkeypatch, tmp_path):
    monkeypatch.setenv(CAL.CALENDAR_ENV, "1")
    _, agent = _build(tmp_path)
    wv = _wv(day_of_week=6, day_type="weekend", rnd=62)
    d, r = _prompts(agent, wv)
    for p in (d, r):
        assert "周日" in p
        assert any(w in p for w in CAL.DAY_TYPE_WORDS["weekend"])
        assert "weekend" not in p


def test_on_audit_key_matches_prompt_line(monkeypatch, tmp_path):
    monkeypatch.setenv(CAL.CALENDAR_ENV, "1")
    _, agent = _build(tmp_path)
    wv = _wv(day_of_week=5, day_type="weekend")
    d, _ = _prompts(agent, wv)
    ctx = agent._ctx_snapshot("P007", "rel_maintain")
    cal = ctx.get("calendar")
    assert cal is not None
    assert cal["day_of_week"] == 5 and cal["day_type"] == "weekend"
    line = next(ln for ln in d.split("\n") if ln.startswith(CAL_MARK))
    assert cal["line_sha256"] == CAL._sha(line.strip())


def test_on_missing_time_fields_degrades_silently(monkeypatch, tmp_path):
    """世界视图缺 time / 字段 ⇒ 不加日历、不抛异常（不打断对话）。"""
    monkeypatch.setenv(CAL.CALENDAR_ENV, "1")
    _, agent = _build(tmp_path)
    wv = SimpleNamespace(round=12, visible_events=[], location="market",
                         current_activity=None, inventory=(), time=None)
    assert agent._calendar_line(wv) == ""
    assert agent._calendar is None
