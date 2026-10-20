"""R6-T2 · F-4「误会与和解」上下文机制（`life/dialogue_repair.py`）单测。

口径（Leader 裁决）：**词表层是唯一可进结论的证据层**；本机制只「只读识别 + 只给处境」，
**绝不改正文**。因此本文件的断言分三组：

  A. 词表镜像 / 消融臂措辞的极性（防漂移、防"注入不生效"）；
  B. 台账与"处境"文本（识别/和解/有界化/确定性；处境里**没有任何现成句子**）；
  C. 接线（关=零扰动、开=字段可读且 body 逐字节等于 LLM 原文；离线 mock 可跑可重放）
     + 消融臂 synthetic 的 F-4 敏感性（证明工具链能从 body 读到张力/修复）。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from life import dialogue_repair as DR
from life.agent import LifeLayerAgent
from life.llm import LLMResult
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas
from life.ports import EventView

CODE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = CODE_DIR.parent
D5 = REPO_ROOT / "tools" / "d5"
CONFIG = CODE_DIR / "config"


# ---------------------------------------------------------------- helpers
def _lexicon(path: Path) -> list:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def _emotion_words() -> dict:
    """{word: polarity}（读 tools/d5/emotion_lexicon.txt；缺失则跳过相关断言）。"""
    out = {}
    for line in _lexicon(D5 / "emotion_lexicon.txt"):
        parts = line.split("\t")
        if len(parts) == 2:
            out[parts[1].strip()] = int(parts[0])
    return out


def _repair_words() -> set:
    return {w.strip() for w in _lexicon(D5 / "repair_lexicon.txt") if w.strip()}


def _polarity(body: str, emo: dict) -> int:
    """与 tools/d5/dialogue_metrics.py 同规则（子串包含计数，正>负=+1，负>正=-1，否则 0）。"""
    pos = sum(1 for w, p in emo.items() if p > 0 and w in body)
    neg = sum(1 for w, p in emo.items() if p < 0 and w in body)
    return 1 if pos > neg else (-1 if neg > pos else 0)


def _f4(msgs: list, emo: dict, rep: set, window: int = 8) -> tuple:
    """F-4 局部复算：返回 (张力事件数, 已修复数)。msgs 按同线程顺序。"""
    tension = closed = 0
    for i in range(1, len(msgs)):
        prev, cur = _polarity(msgs[i - 1]["body"], emo), _polarity(msgs[i]["body"], emo)
        if not (prev * cur < 0 or cur < 0):
            continue
        tension += 1
        for j in range(i + 1, min(i + 1 + window, len(msgs))):
            if any(w in msgs[j]["body"] for w in rep):
                closed += 1
                break
    return tension, closed


def _ev(seq: int, rnd: int, body: str, author: str = "P002", to: str = "P003",
        thread_id: str | None = "TH-P002-P003-1", topic: str = "闲聊") -> EventView:
    payload = {"msg_id": f"D-{rnd}-{seq}", "msg_uid": f"7:{seq}", "from": author, "to": to,
               "body": body, "thread_id": thread_id, "topic": topic,
               "turn_index": 1, "day": 0, "slot": "morning", "tag_hints": [topic]}
    return EventView(seq=seq, round=rnd, phase=2, actor=author, type="MSG_DM", payload=payload)


def _params(**kw) -> dict:
    p = dict(DR.DEFAULTS)
    p.update({"enabled": True})
    p.update(kw)
    return p


# ---------------------------------------------------------------- A. 词表/措辞
def test_lexicon_mirror_is_subset():
    """镜像词表必须是上游词表的子集（不漂移；上游新增词不进镜像 = 已知保守方向）。"""
    emo = _emotion_words()
    rep = _repair_words()
    if not emo or not rep:
        pytest.skip("tools/d5 词表不可用（分支/打包场景），跳过镜像漂移检查")
    assert set(DR.NEG_WORDS) <= set(emo), sorted(set(DR.NEG_WORDS) - set(emo))
    assert all(emo[w] == -1 for w in DR.NEG_WORDS)
    assert set(DR.REPAIR_WORDS) <= rep, sorted(set(DR.REPAIR_WORDS) - rep)


def test_ablation_phrases_have_expected_polarity():
    """消融臂措辞：摩擦句极性 -1（≥2 个负词），和解句极性 0 且含修复词。"""
    from devtools import repair_ablation as RA
    emo = _emotion_words()
    rep = _repair_words()
    if not emo or not rep:
        pytest.skip("tools/d5 词表不可用")
    for ph in RA.FRICTION_PHRASES:
        negs = [w for w in emo if emo[w] < 0 and w in ph]
        assert len(negs) >= 2, (ph, negs)
        assert _polarity(ph, emo) == -1, ph
    for ph in RA.REPAIR_PHRASES:
        assert any(w in ph for w in rep), ph
        assert _polarity(ph, emo) == 0, (ph, "和解句必须极性 0（否则会额外判出翻转张力）")


# ---------------------------------------------------------------- B. 台账 / 处境
def test_rift_ingest_detects_and_resolves():
    rifts, seen = {}, set()
    p = _params()
    # 冷启动：正向话 → 无 rift
    DR.ingest(rifts, seen, [_ev(1, 0, "今天天气不错，真好。")], "P003", p, 0)
    assert rifts == {}
    # 听到负向话 → 记一条（with=说话人）
    DR.ingest(rifts, seen, [_ev(2, 1, "算了，你什么意思。")], "P003", p, 1)
    assert len(rifts) == 1
    only = next(iter(rifts.values()))
    assert only["with"] == "P002" and only["thread_id"] == "TH-P002-P003-1"
    # 幂等：重复吸收同一事件不再新增
    DR.ingest(rifts, seen, [_ev(2, 1, "算了，你什么意思。")], "P003", p, 1)
    assert len(rifts) == 1
    # 同线程后续出现修复词 → 和解注销
    DR.ingest(rifts, seen, [_ev(3, 2, "对不起，我不是那个意思。", author="P002")], "P003", p, 2)
    assert rifts == {}
    # 别的线程出现修复词不影响本线程旧账
    DR.ingest(rifts, seen,
              [_ev(4, 3, "我有点生气，算了。"), _ev(5, 3, "抱歉，误会了。", thread_id="TH-X")],
              "P003", p, 3)
    assert len(rifts) == 1 and next(iter(rifts.values()))["thread_id"] == "TH-P002-P003-1"


def test_rift_bounded_and_deterministic():
    p = _params(max_open=2, max_age_rounds=5)
    rifts, seen = {}, set()
    evs = [_ev(i, i, "我有点生气，算了。", thread_id=f"TH-{i}") for i in range(1, 5)]
    DR.ingest(rifts, seen, evs, "P003", p, 4)
    assert len(rifts) == 2                                   # max_open 截断（保留最近）
    assert sorted(v["seq"] for v in rifts.values()) == [3, 4]
    DR.prune(rifts, p, 100)                                  # 超龄淡忘
    assert rifts == {}
    # 确定性：同输入同输出
    a, b = {}, {}
    DR.ingest(a, set(), evs, "P003", p, 4)
    DR.ingest(b, set(), evs, "P003", p, 4)
    assert list(a) == list(b)


def test_context_line_is_situation_not_script():
    """处境里必须是「事实 + 选项」，**不得出现任何现成句式**（否则就变回模板注入）。"""
    p = _params()
    rifts, seen = {}, set()
    DR.ingest(rifts, seen, [_ev(9, 10, "你什么意思，我有点生气。", topic="借东西")],
              "P003", p, 10)
    line = DR.context_line(rifts, "P002", 12, name="老周", params=p)
    assert line and "没说开" in line and "借东西" in line
    assert "老周" in line and "还没放下" in line
    assert DR.TOOLBOX in line                                # 给选项
    for ph in DR.REPAIR_WORDS:
        assert ph not in line, f"处境里不得出现现成句式/修复词：{ph}"
    from devtools import repair_ablation as RA
    for ph in RA.FRICTION_PHRASES + RA.REPAIR_PHRASES:
        assert ph not in line
    # 无相关旧账 / 关闭 / 超龄 ⇒ None（提示词逐字节不变）
    assert DR.context_line(rifts, "P009", 12, params=p) is None
    assert DR.context_line(rifts, "P002", 12, params=_params(enabled=False)) is None
    assert DR.context_line(rifts, "P002", 10 + 999, params=p) is None


def test_audit_fields_empty_when_no_rift_or_off():
    assert DR.audit_fields({}, 1, "reply") is None
    rifts, seen = {}, set()
    p = _params()
    DR.ingest(rifts, seen, [_ev(1, 1, "算了，我有点生气。")], "P003", p, 1)
    f = DR.audit_fields(rifts, 3, "reply", peers=["P002"])
    assert f["v"] == "f4/1" and f["open"] == 1 and f["with"] == ["P002"]
    assert f["route"] == "reply" and f["age_rounds"] == [2] and f["prompted"] is True
    assert DR.audit_fields(rifts, 3, "reply", peers=["P999"]) is None
    assert DR.audit_fields(rifts, 3, "reply", peers=["P002"])["open"] == 1
    p2 = _params(enabled=False)
    rid2, seen2 = {}, set()
    DR.ingest(rid2, seen2, [_ev(1, 1, "算了，我有点生气。")], "P003", p2, 1)
    assert rid2 == {} and DR.audit_fields(rid2, 2, "reply") is None


# ---------------------------------------------------------------- C. 接线（agent 级）
class _StubKernel:
    def __init__(self) -> None:
        self.intents = []

    def submit_intent(self, agent_id, intent):
        self.intents.append((agent_id, intent))
        return SimpleNamespace(ok=True, reason=None, event_seqs=(len(self.intents),))


class _StubLLM:
    name = "stub"

    def __init__(self, text: str) -> None:
        self.text = text
        self.prompts: list = []

    def call(self, purpose, prompt, *, model=None, meta=None):
        self.prompts.append(prompt)
        return LLMResult(text=self.text)


def _agent(tmp: Path, llm_text: str = "（mock）今天可真热闹。"):
    places = {p["place_id"]: p for p in
              json.loads((CONFIG / "places.json").read_text(encoding="utf-8"))["places"]}
    persona = load_personas(CONFIG / "personas.json")["P003"]
    kernel = _StubKernel()
    llm = _StubLLM(llm_text)
    agent = LifeLayerAgent("P003", persona, kernel, llm=llm,
                           side_store=SideStore(tmp / "side"),
                           embedding=HashEmbeddingModel(), places=places,
                           peer_names={"P002": "老周"})
    return agent, kernel, llm


def _wv(round_no: int, evs: list):
    return SimpleNamespace(round=round_no, visible_events=tuple(evs), llm_permit=True,
                           time=SimpleNamespace(day_of_week=0, slot="morning"))


def test_send_reply_does_not_rewrite_body_but_records_field(monkeypatch, tmp_path):
    """**核心断言**：body 逐字节等于 LLM 原文（不下笔）；有旧账时才追加 `dialogue_rift` 字段。"""
    monkeypatch.setattr(DR, "load_params", lambda path=None: _params())
    agent, kernel, llm = _agent(tmp_path)
    agent._rifts, seen = {}, set()
    DR.ingest(agent._rifts, seen, [_ev(7, 4, "算了，你什么意思，我有点生气。")], "P003",
              _params(), 4)
    ev = _ev(7, 4, "算了，你什么意思，我有点生气。")
    cfg = agent._dlg_cfg()
    assert agent._send_reply(_wv(5, [ev]), ev, cfg, "day0-morning") is True
    _aid, intent = kernel.intents[-1]
    body = intent.payload["body"]
    assert body == llm.text, "机制不得改写正文（否则就等于模板注入）"
    assert intent.payload["dialogue_rift"]["with"] == ["P002"]
    assert intent.payload["dialogue_rift"]["prompted"] is True
    # 处境进了提示词，但里面没有任何现成句子
    assert "没说开" in llm.prompts[-1] and DR.TOOLBOX in llm.prompts[-1]
    for ph in DR.REPAIR_WORDS:
        assert ph not in llm.prompts[-1]


def test_send_reply_without_rift_has_no_field(monkeypatch, tmp_path):
    monkeypatch.setattr(DR, "load_params", lambda path=None: _params())
    agent, kernel, llm = _agent(tmp_path)
    ev = _ev(8, 4, "今天天气不错。")
    cfg = agent._dlg_cfg()
    assert agent._send_reply(_wv(5, [ev]), ev, cfg, "day0-morning") is True
    assert "dialogue_rift" not in kernel.intents[-1][1].payload
    assert "没说开" not in llm.prompts[-1]


def test_reply_priority_prefers_thread_with_open_rift(monkeypatch, tmp_path):
    """回复优先级：有旧账的线程优先接话（仍是同一套硬条件，只改挑选顺序）。"""
    monkeypatch.setattr(DR, "load_params", lambda path=None: _params())
    agent, _kernel, _llm = _agent(tmp_path)
    plain = _ev(11, 4, "今天天气不错。", thread_id="TH-A")
    rift_ev = _ev(12, 4, "算了，你什么意思。", thread_id="TH-B", author="P004")
    prefer = {"TH-B"}
    picked = agent._pick_reply_target(_wv(5, [plain, rift_ev]), agent._dlg_cfg(),
                                      prefer_threads=prefer)
    assert picked is not None and picked.payload["thread_id"] == "TH-B"
    picked2 = agent._pick_reply_target(_wv(5, [plain, rift_ev]), agent._dlg_cfg())
    assert picked2 is not None and picked2.payload["thread_id"] == "TH-B"   # 最近优先（基线）


# ---------------------------------------------------------------- C. 离线 mock 端到端
def _run_world(n: int = 6, rounds: int = 40, seed: int = 7):
    from engine.integration import build_world
    from engine.replay import replay_records
    from engine.state import state_hash
    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    for r in range(rounds):
        eng.run_round(r)
    recs = list(eng.ledger.records)
    ok = state_hash(replay_records(recs)) == state_hash(eng.state)
    return recs, ok


def _msgs(recs):
    return [r for r in recs if r["type"] in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")]


def test_gate_off_zero_perturbation_offline_mock(monkeypatch):
    """默认关（v0 语义）：日志里**没有任何** `dialogue_rift` 键；可重放。"""
    monkeypatch.setattr(DR, "load_params", lambda path=None: dict(DR.DEFAULTS))
    recs, replay_ok = _run_world()
    msgs = _msgs(recs)
    assert msgs, "离线 mock 批应产生 MSG_*（否则本断言无意义）"
    assert not [m for m in msgs if "dialogue_rift" in (m["payload"] or {})]
    assert replay_ok is True


def test_gate_on_offline_mock_runs_replays_and_never_injects(monkeypatch):
    """开：可跑、可重放；正文里**没有**任何消融臂措辞（机制不下笔）；字段 schema 合法。"""
    monkeypatch.setattr(DR, "load_params", lambda path=None: _params())
    recs, replay_ok = _run_world()
    msgs = _msgs(recs)
    assert replay_ok is True
    from devtools import repair_ablation as RA
    for m in msgs:
        body = m["payload"].get("body") or ""
        for ph in RA.FRICTION_PHRASES + RA.REPAIR_PHRASES:
            assert ph not in body, f"生产路径不得注入模板句：{ph}"
    for m in msgs:
        f = (m["payload"] or {}).get("dialogue_rift")
        if f is None:
            continue
        assert f["v"] == "f4/1"
        assert f["open"] >= 1 and f["with"] and f["route"] in ("reply", "initiate")
        assert isinstance(f["threads"], list) and isinstance(f["age_rounds"], list)
        assert isinstance(f["prompted"], bool)


def test_synthetic_ablation_arm_moves_f4(monkeypatch):
    """消融臂（synthetic）：证明 F-4 分子/分母确实由 body 词表驱动（管道通、词表敏感）。"""
    from devtools import repair_ablation as RA
    emo, rep = _emotion_words(), _repair_words()
    if not emo or not rep:
        pytest.skip("tools/d5 词表不可用")
    base = [{"thread_id": "T1", "body": "（闲聊）今天见到你真好，最近可好？"},
            {"thread_id": "T1", "body": "（回复）还行吧。"},
            {"thread_id": "T1", "body": "（回复）那就好，明天见。"}]
    den0, num0 = _f4(base, emo, rep)
    injected = RA.inject_scripted(base)
    den1, num1 = _f4(injected, emo, rep)
    assert (den1, num1) == (1, 1), (den1, num1)
    assert den0 == 0 and num0 == 0


def test_gate_off_agent_path_ignores_existing_rifts(monkeypatch, tmp_path):
    """开关关闭路径：即使台账里已有旧账，也不进提示词、不写字段（v0 逐字节不变）。"""
    monkeypatch.setattr(DR, "load_params", lambda path=None: dict(DR.DEFAULTS))
    agent, kernel, llm = _agent(tmp_path)
    ev = _ev(21, 4, "算了，你什么意思，我有点生气。")
    # 台账被人为塞满（模拟"另一批留下的状态"），关闭时也必须完全无效
    agent._rifts = {"R|x": {"rift_id": "R|x", "with": "P002", "thread_id": "TH-P002-P003-1",
                            "msg_uid": "7:21", "seq": 21, "round": 4, "day": 0,
                            "slot": "morning", "topic": "闲聊"}}
    assert agent._send_reply(_wv(5, [ev]), ev, agent._dlg_cfg(), "day0-morning") is True
    payload = kernel.intents[-1][1].payload
    assert "dialogue_rift" not in payload
    assert "没说开" not in llm.prompts[-1] and DR.TOOLBOX not in llm.prompts[-1]
    assert payload["body"] == llm.text


def test_synthetic_ablation_polarity_flip_artifact_quantified():
    """消融臂已知偏差量化：修复正文自带正向词 ⇒ 额外判出一次「翻转张力」且无后续修复。

    ⇒ 该臂的率会被**系统性拉低**（0.5 而不是 1.0）。这是保守方向的伪影，附录必须写明。
    """
    from devtools import repair_ablation as RA
    emo, rep = _emotion_words(), _repair_words()
    if not emo or not rep:
        pytest.skip("tools/d5 词表不可用")
    base = [{"thread_id": "T1", "body": "（闲聊）今天见到你真好，最近可好？"},
            {"thread_id": "T1", "body": "（回复）还行吧。"},
            {"thread_id": "T1", "body": "（回复）那就好，明天见。"}]
    injected = RA.inject_scripted(base)
    assert _f4(injected, emo, rep) == (1, 1)          # 干净臂：1 张力 / 1 闭环
    flip = [dict(m) for m in injected]
    flip[2]["body"] = "真好，谢谢你。" + flip[2]["body"]   # 修复正文自带正向词
    den, num = _f4(flip, emo, rep)
    assert den == 2 and num == 1, (den, num)          # 分子不变、分母 +1 ⇒ 率被拉低
