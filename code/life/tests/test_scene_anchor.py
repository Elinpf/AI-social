"""处境锚臂（scene-anchor）单测：OFF 不变 / ON 只插一行 / 人话不泄 id / 确定性 / 审计键。

覆盖五条硬要求（对应 dev-note 与简报 §5.1 的验收口径）：
  1. **OFF（默认）**：`_scene_line` 返回空串、`_scene` 为 None、两条提示词里不出现
     「你眼下的光景」、payload `ctx` 不出现 `scene` 键；
  2. **ON 是单变量插入**：把 ON 提示词里那一行**原样减掉**后，与 OFF 提示词**逐字节相等**；
  3. **人话不泄 id**：提示词里出现的是 `places.json::name_cn`（如「市集」），
     绝不出现 `market` / `plaza` / `workshop` 这类内部 id；`name_cn` 缺项时该片段不写；
  4. **确定性**：同一 (agent|round|slot) 两次渲染完全相同（可 replay）；
  5. **审计键**：ON 时 `ctx.scene` 带 slot/place/activity + 该行 sha256，且 sha256 与
     真正拼进提示词的那一行一致。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from life import dialogue_threads as DT
from life import scene_anchor as SA
from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.ports import EventView, IntentResult
from life.tests.support.mini_kernel import MiniKernel

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"
SCENE_MARK = "你眼下的光景："


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


def _wv(*, slot: str = "evening", location: str = "market",
        activity: str | None = "trade", rnd: int = 12):
    ca = {"activity_type": activity, "place": location} if activity else None
    return SimpleNamespace(round=rnd, visible_events=[], location=location,
                           current_activity=ca, inventory=(),
                           time=SimpleNamespace(slot=slot, day_of_week=3, day=3))


class _RecLLM:
    name = "rec-llm"

    def __init__(self, text: str = "嗯，天是不早了。"):
        self.text = text
        self.prompts: list[str] = []

    def call(self, purpose, prompt, *, model=None, meta=None):
        self.prompts.append(prompt)
        return SimpleNamespace(text=self.text)


def _prompts(agent, wv):
    cfg = dict(DT.DEFAULTS)
    history = [("P007", "阿禾：今儿个有点乏。")]
    return (agent._dialogue_prompt("rel_maintain", ["P003", "P007"], cfg, wv=wv),
            agent._reply_prompt("P007", "rel_maintain", history, cfg, wv=wv, turn=1))


def _strip_scene(prompt: str) -> str:
    """把 ON 提示词里「你眼下的光景：……」那一行原样减掉（模拟"两态只差一行"）。"""
    out = []
    for ln in prompt.split("\n"):
        if ln.startswith(SCENE_MARK + ""):
            continue
        out.append(ln)
    return "\n".join(out)


# ---------------------------------------------------------------- 开关
def test_switch_default_off(monkeypatch):
    monkeypatch.delenv(SA.SCENE_ENV, raising=False)
    assert SA.enabled() is False


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "on", "yes", " on "])
def test_switch_env_on(monkeypatch, val):
    monkeypatch.setenv(SA.SCENE_ENV, val)
    assert SA.enabled() is True


@pytest.mark.parametrize("val", ["0", "false", "off", "no", "", "2", "enable"])
def test_switch_env_off(monkeypatch, val):
    monkeypatch.setenv(SA.SCENE_ENV, val)
    assert SA.enabled() is False


# ---------------------------------------------------------------- 纯函数：render
def test_render_off_returns_empty(monkeypatch):
    monkeypatch.delenv(SA.SCENE_ENV, raising=False)
    assert SA.render("P003", 12, "evening", "市集", "trade") == ""


def test_render_on_contains_human_words_and_no_ids(monkeypatch):
    monkeypatch.setenv(SA.SCENE_ENV, "1")
    line = SA.render("P003", 12, "evening", "市集", "trade")
    assert SCENE_MARK in line
    assert "市集" in line
    for bad in ("market", "plaza", "workshop", "trade", "evening"):
        assert bad not in line, f"内部 id/token 泄漏进提示词：{bad}"
    # 时段措辞必须来自冻结词表之一
    assert any(w in line for w in SA.SLOT_WORDS["evening"])
    assert any(w in line for w in SA.ACTIVITY_WORDS["trade"])


def test_render_missing_place_name_omits_place_clause(monkeypatch):
    monkeypatch.setenv(SA.SCENE_ENV, "1")
    line = SA.render("P003", 12, "morning", None, "work")
    assert "你在" not in line
    assert SCENE_MARK in line


def test_render_unknown_slot_and_activity_still_grounded_by_place(monkeypatch):
    monkeypatch.setenv(SA.SCENE_ENV, "1")
    line = SA.render("P003", 12, "dawn", "农场", "farming")
    assert "你在农场" in line
    assert "dawn" not in line and "farming" not in line


def test_render_all_empty_materials_returns_empty(monkeypatch):
    monkeypatch.setenv(SA.SCENE_ENV, "1")
    assert SA.render("P003", 12, "dawn", None, None) == ""


def test_render_deterministic(monkeypatch):
    monkeypatch.setenv(SA.SCENE_ENV, "1")
    a = SA.render("P003", 12, "evening", "市集", "trade")
    b = SA.render("P003", 12, "evening", "市集", "trade")
    assert a == b
    # 不同 agent/round 允许措辞不同，但必须仍在冻结词表内
    c = SA.render("P007", 13, "evening", "市集", "trade")
    assert any(w in c for w in SA.SLOT_WORDS["evening"])


def test_lexicon_sha_stable_and_versioned():
    sha = SA.lexicon_sha256()
    assert len(sha) == 64
    assert SA.lexicon_sha256() == sha
    assert SA.LEXICON_VERSION.startswith("scene-anchor")


# ---------------------------------------------------------------- agent 侧接线
def test_off_prompt_and_ctx_untouched(monkeypatch, tmp_path):
    monkeypatch.delenv(SA.SCENE_ENV, raising=False)
    _, agent = _build(tmp_path)
    wv = _wv()
    assert agent._scene_line(wv) == ""
    assert agent._scene is None
    d, r = _prompts(agent, wv)
    assert SCENE_MARK not in d and SCENE_MARK not in r
    assert "scene" not in agent._ctx_snapshot("P007", "rel_maintain")


def test_on_inserts_one_line_and_off_is_exact_prefix_removal(monkeypatch, tmp_path):
    _, agent = _build(tmp_path)
    wv = _wv()
    monkeypatch.delenv(SA.SCENE_ENV, raising=False)
    d_off, r_off = _prompts(agent, wv)
    monkeypatch.setenv(SA.SCENE_ENV, "1")
    d_on, r_on = _prompts(agent, wv)
    # 两态必须不同
    assert d_on != d_off and r_on != r_off
    # 且「只差那一行」：减掉该行后逐字节回到 OFF
    assert _strip_scene(d_on) == d_off
    assert _strip_scene(r_on) == r_off
    assert d_on.count(SCENE_MARK) == 1 and r_on.count(SCENE_MARK) == 1


def test_on_uses_name_cn_never_place_id(monkeypatch, tmp_path):
    monkeypatch.setenv(SA.SCENE_ENV, "1")
    places = _places()
    _, agent = _build(tmp_path)
    for pid, spec in places.items():
        assert agent.places[pid]["name_cn"] == spec["name_cn"]
    wv = _wv(location="farm", activity="work")
    d, r = _prompts(agent, wv)
    assert "农场" in d and "农场" in r
    assert "你在farm" not in d and "你在farm" not in r   # 只查处境片段，persona 里的角色名 farmer 不算


def test_on_ctx_scene_audit_matches_line(monkeypatch, tmp_path):
    monkeypatch.setenv(SA.SCENE_ENV, "1")
    _, agent = _build(tmp_path)
    wv = _wv()
    d, _ = _prompts(agent, wv)
    ctx = agent._ctx_snapshot("P007", "rel_maintain")
    assert "scene" in ctx
    sc = ctx["scene"]
    assert sc["slot"] == "evening" and sc["place"] == "market" and sc["activity"] == "trade"
    line = next(ln for ln in d.split("\n") if ln.startswith(SCENE_MARK))
    assert sc["line_sha256"] == hashlib.sha256(line.encode("utf-8")).hexdigest()


def test_on_reply_end_to_end_payload_carries_scene(monkeypatch, tmp_path):
    """走真正的 `_send_reply`：MSG payload 的 ctx 里应带 scene，且提示词里有一行处境。"""
    monkeypatch.setenv(SA.SCENE_ENV, "1")
    kernel, agent = _build(tmp_path)
    payload = {"msg_id": "D-4-P007-P003", "msg_uid": "D-4-P007-P003-u1", "from": "P007",
               "to": "P003", "body": "今儿个有点乏。", "refs": [], "tag_hints": ["rel_maintain"],
               "thread_id": "TH-P007-P003-4", "turn_index": 0, "reply_to": None,
               "participants": ["P003", "P007"], "topic": "rel_maintain",
               "ctx": {"relation": 0, "topic": "rel_maintain", "mood": "平和"}}
    ev = EventView(seq=5, round=4, phase=2, actor="P007", type="MSG_DM",
                   payload=payload, place="residence")
    wv = SimpleNamespace(round=4, visible_events=[ev], location="cafe",
                         current_activity={"activity_type": "leisure"},
                         inventory=(), time=SimpleNamespace(slot="morning", day_of_week=0, day=0))
    rec = _RecLLM()
    agent.llm = rec
    captured: list[dict] = []
    kernel.submit_intent = lambda aid, intent: (captured.append(intent.payload)
                                                or IntentResult(ok=True, reason=None, event_seqs=()))
    ok = agent._send_reply(wv, ev, DT.DEFAULTS, "day0-morning")
    assert ok is True
    assert SCENE_MARK in rec.prompts[0]
    assert "咖啡馆" in rec.prompts[0]
    assert captured[0]["ctx"]["scene"]["place"] == "cafe"


def test_off_reply_end_to_end_payload_has_no_scene(monkeypatch, tmp_path):
    monkeypatch.delenv(SA.SCENE_ENV, raising=False)
    kernel, agent = _build(tmp_path)
    payload = {"msg_id": "D-4-P007-P003", "msg_uid": "D-4-P007-P003-u1", "from": "P007",
               "to": "P003", "body": "今儿个有点乏。", "refs": [], "tag_hints": ["rel_maintain"],
               "thread_id": "TH-P007-P003-4", "turn_index": 0, "reply_to": None,
               "participants": ["P003", "P007"], "topic": "rel_maintain",
               "ctx": {"relation": 0, "topic": "rel_maintain", "mood": "平和"}}
    ev = EventView(seq=5, round=4, phase=2, actor="P007", type="MSG_DM",
                   payload=payload, place="residence")
    wv = SimpleNamespace(round=4, visible_events=[ev], location="cafe",
                         current_activity={"activity_type": "leisure"},
                         inventory=(), time=SimpleNamespace(slot="morning", day_of_week=0, day=0))
    rec = _RecLLM()
    agent.llm = rec
    captured: list[dict] = []
    kernel.submit_intent = lambda aid, intent: (captured.append(intent.payload)
                                                or IntentResult(ok=True, reason=None, event_seqs=()))
    assert agent._send_reply(wv, ev, DT.DEFAULTS, "day0-morning") is True
    assert SCENE_MARK not in rec.prompts[0]
    assert "scene" not in captured[0]["ctx"]


def test_missing_worldview_degrades_silently(monkeypatch, tmp_path):
    """wv 缺字段/为 None ⇒ 不加处境、不抛异常（对话链路不受影响）。"""
    monkeypatch.setenv(SA.SCENE_ENV, "1")
    _, agent = _build(tmp_path)
    assert agent._scene_line(None) == ""
    broken = SimpleNamespace(round=1, location="", current_activity=None)
    assert agent._scene_line(broken) == ""     # 无 time 属性 ⇒ 时段缺失；又无场所 ⇒ 整行不写
    no_place = SimpleNamespace(round=1, location="", current_activity=None,
                               time=SimpleNamespace(slot="night"))
    out = agent._scene_line(no_place)
    assert SCENE_MARK in out and "你在" not in out   # 只有时段也要能成句
