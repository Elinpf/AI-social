"""集日臂（market_day / 逢三赶集）单测：

  * **OFF（默认）**：`_market_line` 返回空串、`_market` 为 None、两条提示词里不出现
    「今儿镇上的日子」、`ctx` 不出现 `market` 键；
  * **ON 且只差一行（集日）**：把 ON 提示词里那一行**原样减掉**后，与 OFF 提示词**逐字节相等**；
  * **ON 但非集日**：提示词与 OFF **逐字节相等**、`ctx.market` 不出现
    （结构性保证"不外溢"：只有集日才有差异）；
  * **确定性派生**：`is_market_day(day)` / `render()` 同 (agent, round, day) 两次调用一致，
    跨进程也一致（可 replay）；源码层面不 import random/datetime/time；
  * **不泄漏内部 token**：`market_day` / `day` / `period` 这类 key 只进审计，**不进提示词**；
  * **剂量约束**：集日那一行必须带「顺带一句／说不着就别提／别每条都提」类约束，
    防止集日退化成复读机；
  * **审计键**：ON 时 `ctx.market` 带 day/is_market_day/period + 该行 sha256，
    且 sha256 与真正拼进提示词的那一行一致。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from life import dialogue_threads as DT
from life import market_day as MK
from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.tests.support.mini_kernel import MiniKernel

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"
MK_MARK = "今儿镇上的日子："
#: 剂量约束关键词（至少要出现其中两个，见 `test_render_has_dose_constraint`）。
DOSE_WORDS = ("顺口带半句", "说不着就别提", "别每条都提")


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


def _wv(*, day: int = 0, rnd: int = 0):
    """最小 WorldView 替身：只带集日臂读的 `round` 与 `time.day`（day=0 ⇒ 集日）。"""
    return SimpleNamespace(round=rnd, visible_events=[], location="market",
                           current_activity=None, inventory=(),
                           time=SimpleNamespace(slot="morning", day=day, day_of_week=day % 7,
                                                day_type="workday"))


def _prompts(agent, wv):
    cfg = dict(DT.DEFAULTS)
    history = [("P007", "阿禾：今儿个有点乏。")]
    return (agent._dialogue_prompt("rel_maintain", ["P003", "P007"], cfg, wv=wv),
            agent._reply_prompt("P007", "rel_maintain", history, cfg, wv=wv, turn=1))


def _strip_market(prompt: str) -> str:
    """把 ON 提示词里「今儿镇上的日子：……」那一行原样减掉（模拟"两态只差一行"）。"""
    return "\n".join(ln for ln in prompt.split("\n") if not ln.startswith(MK_MARK))


# ---------------------------------------------------------------- 开关
def test_switch_default_off(monkeypatch):
    monkeypatch.delenv(MK.MARKET_ENV, raising=False)
    assert MK.enabled() is False


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "on", "yes", " on "])
def test_switch_env_on(monkeypatch, val):
    monkeypatch.setenv(MK.MARKET_ENV, val)
    assert MK.enabled() is True


@pytest.mark.parametrize("val", ["0", "false", "off", "no", "", "2", "enable"])
def test_switch_env_off(monkeypatch, val):
    monkeypatch.setenv(MK.MARKET_ENV, val)
    assert MK.enabled() is False


# ---------------------------------------------------------------- 纯函数：集日判定
def test_is_market_day_period_three():
    """逢三、六、九：day % 3 == 0 为集日（周期 3，与 r24/r48 批次窗口对齐）。"""
    assert MK.MARKET_PERIOD_DAYS == 3
    flags = [MK.is_market_day(d) for d in range(9)]
    assert flags == [True, False, False] * 3
    assert MK.is_market_day(-3) is True          # 负数不崩（对 int 取模仍合法）
    assert MK.is_market_day("bad") is True       # 非法 ⇒ 按 day=0 处理


def test_batch_windows_have_market_and_non_market_days():
    """功效前提（本维度的立项理由，落成断言防回归）：
    r24 = day0–day1 ⇒ 集日 day0 + 非集日 day1 同批对照；
    r48 = day0–day3 ⇒ 集日 day0、day3。7 天周期（weekend day5/6）在两者内都覆盖不到。"""
    r24_days = range(0, 2)
    r48_days = range(0, 4)
    assert [d for d in r24_days if MK.is_market_day(d)] == [0]
    assert [d for d in r24_days if not MK.is_market_day(d)] == [1]
    assert [d for d in r48_days if MK.is_market_day(d)] == [0, 3]
    assert 5 not in r48_days and 6 not in r48_days      # weekend 在 r48 窗口外


def test_pure_function_source_has_no_clock_or_randomness():
    """源码层硬断言：本模块不 import random / datetime / time（确定性可审计）。"""
    src = (CODE_DIR / "life" / "market_day.py").read_text(encoding="utf-8")
    for bad in ("import random", "from random", "import datetime", "from datetime",
                "time.time(", "monotonic(", "time()"):
        assert bad not in src, f"确定性纪律被破坏：出现 {bad}"


# ---------------------------------------------------------------- 纯函数：render
def test_render_off_returns_empty(monkeypatch):
    monkeypatch.delenv(MK.MARKET_ENV, raising=False)
    assert MK.render("P003", 0, 0) == ""


def test_render_on_non_market_day_returns_empty(monkeypatch):
    """ON 但非集日 ⇒ 一行都不加（这是 ON 臂非集日与 OFF 逐字节相等的根源）。"""
    monkeypatch.setenv(MK.MARKET_ENV, "1")
    for day in (1, 2, 4, 5, 7, 8):
        assert MK.render("P003", 12, day) == ""


def test_render_on_market_day_contains_mark_and_human_words(monkeypatch):
    monkeypatch.setenv(MK.MARKET_ENV, "1")
    line = MK.render("P003", 0, 0)
    assert MK_MARK in line
    assert any(w in line for w in MK.MARKET_WORDS)
    for bad in ("market", "day", "period", "is_market_day"):
        assert bad not in line, f"内部 token 泄漏进提示词：{bad}"


def test_render_has_dose_constraint(monkeypatch):
    """剂量约束必须写进那一行：防集日变成复读机（宁可不提，不要硬提）。"""
    monkeypatch.setenv(MK.MARKET_ENV, "1")
    line = MK.render("P003", 0, 6)
    assert sum(1 for w in DOSE_WORDS if w in line) >= 2, line


def test_render_deterministic(monkeypatch):
    monkeypatch.setenv(MK.MARKET_ENV, "1")
    assert MK.render("P003", 0, 3) == MK.render("P003", 0, 3)
    assert MK.render("P003", 0, 3) == MK.render("P003", 0, 3)


def test_render_wording_varies_across_agents(monkeypatch):
    """同一天不同人：事实相同、措辞可从词表里变（抑制开口句式重复）。"""
    monkeypatch.setenv(MK.MARKET_ENV, "1")
    lines = {MK.render(f"P{i:03d}", 0, 0) for i in range(1, 21)}
    assert len(lines) > 1, "20 个居民在集日说法完全相同 ⇒ 词表没被用起来"


def test_render_has_no_action_imperative(monkeypatch):
    """措辞纪律：只表达**背景/感知**，不得写成行动指令（本轮不改可达性，见预登记 §3.1）。"""
    monkeypatch.setenv(MK.MARKET_ENV, "1")
    for i in range(1, 21):
        line = MK.render(f"P{i:03d}", 0, 0)
        for bad in ("该去", "去赶集", "你去", "你赶", "务必", "摆摊", "今天应该"):
            assert bad not in line, f"提示词出现行动指令「{bad}」：{line}"


def test_lexicon_sha_stable_and_versioned():
    sha = MK.lexicon_sha256()
    assert len(sha) == 64
    assert MK.lexicon_sha256() == sha
    assert MK.LEXICON_VERSION.startswith("market-day")


def test_audit_records_keys_not_human_words():
    line = "今儿镇上的日子：今儿逢集。" + MK._TAIL
    a = MK.audit(0, line)
    assert a["day"] == 0 and a["is_market_day"] is True and a["period"] == 3
    assert a["line_sha256"] == MK._sha(line.strip())


# ---------------------------------------------------------------- agent 侧接线
def test_off_prompt_and_ctx_untouched(monkeypatch, tmp_path):
    monkeypatch.delenv(MK.MARKET_ENV, raising=False)
    _, agent = _build(tmp_path)
    wv = _wv(day=0, rnd=0)               # 集日也不该产（开关 OFF 优先）
    assert agent._market_line(wv) == ""
    assert agent._market is None
    d, r = _prompts(agent, wv)
    assert MK_MARK not in d and MK_MARK not in r
    assert "market" not in agent._ctx_snapshot("P007", "rel_maintain")


def test_on_inserts_one_line_and_off_is_exact_prefix_removal(monkeypatch, tmp_path):
    _, agent = _build(tmp_path)
    wv = _wv(day=0, rnd=0)               # day0 = 集日
    monkeypatch.delenv(MK.MARKET_ENV, raising=False)
    d_off, r_off = _prompts(agent, wv)
    monkeypatch.setenv(MK.MARKET_ENV, "1")
    d_on, r_on = _prompts(agent, wv)
    assert d_on != d_off and r_on != r_off
    # 「只差那一行」：减掉该行后逐字节回到 OFF
    assert _strip_market(d_on) == d_off
    assert _strip_market(r_on) == r_off
    assert d_on.count(MK_MARK) == 1 and r_on.count(MK_MARK) == 1


def test_on_non_market_day_prompt_identical_to_off(monkeypatch, tmp_path):
    """ON 臂在非集日的两条提示词与 OFF **逐字节相等**（不外溢的结构性保证）。"""
    _, agent = _build(tmp_path)
    wv = _wv(day=1, rnd=12)              # day1 = 非集日
    monkeypatch.delenv(MK.MARKET_ENV, raising=False)
    d_off, r_off = _prompts(agent, wv)
    monkeypatch.setenv(MK.MARKET_ENV, "1")
    d_on, r_on = _prompts(agent, wv)
    assert d_on == d_off and r_on == r_off
    assert agent._market is None
    assert "market" not in agent._ctx_snapshot("P007", "rel_maintain")


def test_on_audit_key_matches_prompt_line(monkeypatch, tmp_path):
    monkeypatch.setenv(MK.MARKET_ENV, "1")
    _, agent = _build(tmp_path)
    wv = _wv(day=3, rnd=36)              # day3 = 集日
    d, _ = _prompts(agent, wv)
    ctx = agent._ctx_snapshot("P007", "rel_maintain")
    mk = ctx.get("market")
    assert mk is not None
    assert mk["day"] == 3 and mk["is_market_day"] is True and mk["period"] == 3
    line = next(ln for ln in d.split("\n") if ln.startswith(MK_MARK))
    assert mk["line_sha256"] == MK._sha(line.strip())


def test_on_same_line_for_replay(monkeypatch, tmp_path):
    """同 (agent, round, day) 两条提示词里的那一行逐字节相同（可 replay）。"""
    monkeypatch.setenv(MK.MARKET_ENV, "1")
    _, agent = _build(tmp_path)
    wv = _wv(day=0, rnd=0)
    d1, r1 = _prompts(agent, wv)
    d2, r2 = _prompts(agent, wv)
    assert d1 == d2 and r1 == r2


def test_on_missing_time_fields_degrades_silently(monkeypatch, tmp_path):
    """世界视图缺 time ⇒ 不加日子、不抛异常（不打断对话）。"""
    monkeypatch.setenv(MK.MARKET_ENV, "1")
    _, agent = _build(tmp_path)
    wv = SimpleNamespace(round=0, visible_events=[], location="market",
                         current_activity=None, inventory=(), time=None)
    assert agent._market_line(wv) == ""
    assert agent._market is None


# ---------------------------------------------------------------- 跨进程确定性（replay）
_DET_SNIPPET = (
    "import json; from life import market_day as MK; "
    "print(json.dumps({'flags': [MK.is_market_day(d) for d in range(12)], "
    "'lines': [MK.render('P003', d * 3, d) for d in range(12)]}, "
    "ensure_ascii=False, sort_keys=True))"
)


def _render_table_in_subprocess() -> str:
    """在**独立进程**里跑一次「集日表 + 12 天那一行」，返回 stdout。

    为什么要独立进程：同进程内两次调用可能恰好相同（伪确定性）；
    两个全新进程给出逐字符相同的表，才等价于「重放/跨批可复现」。
    """
    env = dict(os.environ)
    env[MK.MARKET_ENV] = "1"
    env["PYTHONPATH"] = str(CODE_DIR)
    out = subprocess.run([sys.executable, "-c", _DET_SNIPPET],
                         env=env, cwd=str(CODE_DIR), capture_output=True,
                         text=True, timeout=120)
    assert out.returncode == 0, f"子进程失败: {out.stderr}"
    return out.stdout.strip()


def test_market_table_deterministic_across_processes():
    a = _render_table_in_subprocess()
    b = _render_table_in_subprocess()
    assert a == b, f"跨进程派生不一致（非可重新复现）：\nA={a}\nB={b}"
    table = json.loads(a)
    assert table["flags"] == [MK.is_market_day(d) for d in range(12)]
    # 非集日那一行必须是空串（否则"不外溢"不成立）
    for d, line in enumerate(table["lines"]):
        assert (line == "") is (not MK.is_market_day(d)), f"day={d} 行与集日判定不一致"

# ---------------------------------------------------------------- 与判据读数器同规则（硬约束）
READINGS = CODE_DIR.parent / "tools" / "metrics" / "market_day_readings.py"


def _load_readings():
    import importlib.util
    spec = importlib.util.spec_from_file_location("market_day_readings_for_test", READINGS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.skipif(not READINGS.exists(), reason="判据读数器未落盘（tools/metrics/market_day_readings.py）")
def test_mechanism_rule_equals_readings_daily_set(tmp_path):
    """**机制集日集合 == 读数器集日集合**（逐日全等）。

    读数器把集日写死 `day % every == offset`（默认 every=3 / offset=0，来自外置词表
    `market_day_lexicon.json::market_day_rule`）；本臂写死 `day % 3 == 0`。
    两边若不同步（period 或 offset 不一致），两臂分母就会静默错位、对比直接作废。
    这里合成 day0..day47 的 run.jsonl，走读数器**真实 API 与真实默认参数**。
    """
    mod = _load_readings()
    run = tmp_path / "run.jsonl"
    with run.open("w", encoding="utf-8") as f:
        for d in range(48):
            f.write(json.dumps({"type": "MSG", "seq": d * 10, "actor": "P003",
                                "payload": {"day": d, "body": "今儿个天气不赖。",
                                            "msg_id": f"m{d}"}}, ensure_ascii=False) + "\n")

    lex = mod.Lexicon(mod.DEFAULT_LEXICON)
    # ① 外置词表里写死的集日规则必须与机制一致
    assert lex.market_every == MK.MARKET_PERIOD_DAYS == 3
    assert lex.market_offset == 0

    # ② 读数器扫描出的集日集合（走 scan_run 真路径）
    acc = mod.scan_run(run, lex, lex.market_every, lex.market_offset)
    tool_days = set(acc["market"]["by_day"].keys())

    # ③ 机制侧的集日集合
    mech_days = {d for d in range(48) if MK.is_market_day(d)}

    # ④ 逐日全等（并显式点名 day0/day3 是集日、day1/day2 不是）
    assert tool_days == mech_days, (
        f"机制与读数器的集日集合不一致：仅机制有 {sorted(mech_days - tool_days)}，"
        f"仅读数器有 {sorted(tool_days - mech_days)}")
    assert {0, 3} <= mech_days and not ({1, 2} & mech_days)
    assert set(acc["nonmarket"]["by_day"].keys()) == set(range(48)) - mech_days

    # ⑤ 命令行默认参数也必须是 3 / 0（防 main 的默认值与词表脱节）
    import contextlib
    import io as _io
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mod.main(["--arm", f"off={run}"])
    assert rc == 0, buf.getvalue()
    out = json.loads(buf.getvalue())
    assert out["subset"]["market_every"] == 3 and out["subset"]["market_offset"] == 0


# ---------------------------------------------------------------- 插行位置 / 仪器隔离（硬约束）
def test_insert_position_locked_in_prompt_assembly():
    """插行位置硬锁：`_market_line` 必须紧跟 `_weather_line`、在 `rift_line` 之前，
    且**先于同一条 prompt 里的 `l7_struct_line` 与 `narration_tail`**（末段必须是收尾指令）。
    """
    src = (CODE_DIR / "life" / "agent.py").read_text(encoding="utf-8").split("\n")
    idx = [i for i, ln in enumerate(src) if "_market_line(wv)" in ln]
    assert len(idx) == 2, f"_market_line 应恰有两处接线（dialogue/reply），实测 {len(idx)}"
    l7 = [i for i, ln in enumerate(src) if "_l7_struct_line(" in ln]
    narr = [i for i, ln in enumerate(src) if 'narration_tail("' in ln]
    for i in idx:
        assert "_weather_line(wv)" in src[i - 1], f"第 {i+1} 行上一行不是 _weather_line"
        assert "rift_line or" in src[i + 1], f"第 {i+1} 行下一行不是 rift_line"
        next_l7 = min(j for j in l7 if j > i)
        next_narr = min(j for j in narr if j > i)
        assert next_l7 < next_narr, f"第 {i+1} 行插入点之后 l7 不在 narration_tail 之前"
        assert i < next_l7, f"第 {i+1} 行插到了 l7_struct_line 之后"
        # 插入点之后、下一个 l7 之前不得夹着 narration_tail（否则等于插进收尾段）
        assert not any(i < j < next_l7 for j in narr), f"第 {i+1} 行插进收尾段"


def test_code_never_imports_judgment_instruments():
    """仪器隔离硬锁：`code/` 运行时**不得 import** `tools/metrics/` 下的判据仪器。

    读数器/词表只在跑完后做后处理；若被 `code/` 运行时 import，词表 bug 会同时污染两臂
    且无人察觉（词表 v1 的 `|` 优先级 bug 就是这么暴露的）。
    只扫**真实 import 语句**（注释/文档串里提到文件名不算），并跳过 `tests/` 自身。
    """
    import re as _re
    pat = _re.compile(r"^\s*(?:from|import)\s+([A-Za-z0-9_.]+)")
    bad_mods = ("market_day_readings", "market_day_lexicon", "market_day_labels",
                "tools.metrics", "tools")
    offenders = []
    for py in CODE_DIR.rglob("*.py"):
        if "__pycache__" in str(py) or "/tests/" in str(py).replace("\\", "/"):
            continue
        for lineno, line in enumerate(py.read_text(encoding="utf-8", errors="ignore").split("\n"), 1):
            m = pat.match(line)
            if not m:
                continue
            mod = m.group(1)
            if any(mod == b or mod.startswith(b + ".") for b in bad_mods):
                offenders.append(f"{py.relative_to(CODE_DIR)}:{lineno} ← {line.strip()}")
    assert not offenders, "code/ 运行时 import 了判据仪器：" + "; ".join(offenders)
