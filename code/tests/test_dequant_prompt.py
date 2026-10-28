"""DEQUANT 臂（去量化词/回指模板）单测 —— 不依赖 LLM、不依赖跑批。

四条硬断言：
  A. 开关语义：未设 ⇒ **默认 OFF**（本仓范式）；`1/true/yes/on` ⇒ ON。
  B. **OFF 逐字节不变**：`LIFE_PROMPT_DEQUANT=0` 时两条提示词与「没有这一段」逐字相同，
     且 `_dequant_guard` 是空操作（返回 None、不建状态）。
  C. **ON 单变量**：ON 提示词 = OFF 提示词 + 恰好一处追加（`_dequant_line()`），
     且追加文本包含「半指宽/第三格/三钱」（固定量词禁止当默认填充）与
     「上回/上次」（回指不许当起手式）的显式约束。
  D. **黑名单/骨架去重逻辑生效**：`dequant_skeleton` 把人名与数字量词遮蔽后同骨架；
     `_dequant_guard` 在同一 `slot` 内第二次出现同骨架 ⇒ `repeated=True`，
     换 `slot` 则不误判；**guard 不改台词**（返回的 body 与入参逐字相同）。

另附：`tools/metrics/dequant_probe.py` 在基线日志上必须复算出报告 §7.1 的
79.8% / 29.8% / 23.7%（±0.4pp）——日志缺失则 skip。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from life import agent as AG
from life import l7_structural as L7S
from life.agent import LifeLayerAgent
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas

CODE_DIR = Path(__file__).resolve().parents[1]
REPO = CODE_DIR.parent
CONFIG = CODE_DIR / "config"
SELF_ID = "P003"
PARTNER_ID = "P002"
BASELINE_LOG = REPO / "v2" / "evidence" / "run_d12d_on_n16r60_seed42" / "run.jsonl"


class _StubKernel:
    def submit_intent(self, *a, **kw):  # pragma: no cover - 本测试不落事件
        pass


def _agent(tmp_path: Path) -> LifeLayerAgent:
    personas = load_personas(CONFIG / "personas.json")
    places = {p["place_id"]: p for p in
              json.loads((CONFIG / "places.json").read_text(encoding="utf-8"))["places"]}
    return LifeLayerAgent(SELF_ID, personas[SELF_ID], _StubKernel(),
                          side_store=SideStore(tmp_path / "side"),
                          embedding=HashEmbeddingModel(), places=places,
                          peers=sorted(personas),
                          peer_names={k: v.display_name for k, v in personas.items()})


# ---------------------------------------------------------------- A 开关语义
def test_env_default_off_and_on_values(monkeypatch):
    monkeypatch.delenv(AG.DEQUANT_ENV, raising=False)
    assert AG.dequant_enabled() is False         # 默认 OFF（本仓范式：OFF 逐字节不变）
    for v in ("1", "true", "YES", " on "):
        monkeypatch.setenv(AG.DEQUANT_ENV, v)
        assert AG.dequant_enabled() is True
    for v in ("0", "false", "no", "off"):
        monkeypatch.setenv(AG.DEQUANT_ENV, v)
        assert AG.dequant_enabled() is False


# ------------------------------------------------- B OFF 逐字节 / ON 单变量
def test_prompt_off_untouched_on_single_insert(monkeypatch, tmp_path):
    history = [("名2", "早上好。")]
    # OFF 臂：探针文本自证「关掉时就是空串」
    monkeypatch.setenv(AG.DEQUANT_ENV, "0")
    agent = _agent(tmp_path)
    assert agent._dequant_line() == ""
    d_off = agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID])
    r_off = agent._reply_prompt(PARTNER_ID, "tpl-1", history)

    # ON 臂：同一 agent、同一参数
    monkeypatch.setenv(AG.DEQUANT_ENV, "1")
    seg = agent._dequant_line()
    assert seg.startswith("\n") and "半指宽" in seg and "第三格" in seg and "上回" in seg
    d_on = agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID])
    r_on = agent._reply_prompt(PARTNER_ID, "tpl-1", history)
    # 单变量：ON = OFF + 恰好一处追加，且两处用的是同一段
    assert d_on.count(seg) == 1 and r_on.count(seg) == 1
    assert d_on.replace(seg, "", 1) == d_off
    assert r_on.replace(seg, "", 1) == r_off


# --------------------------------------- C 黑名单 / 骨架去重断言（无 LLM）
def test_lexicon_hits_and_skeleton_masking():
    """样例取自基线日志里**真实出现**的同模板句对（recon §7.1 病灶①/②）。"""
    names = ("老陈",)
    a = "把这份卷宗归到第三格后，我想起老陈上回漏填了日期，害得整批文书返工。"
    b = "把这份卷宗归到第三格后，我想起老陈上回漏填了日期，还是得按规矩补上。"
    assert AG.dequant_lexicon_hits(a) == ["第三格", "上回"]
    # 遮蔽人名 + 回指/度量词后，两句落回同一骨架（这正是要抓的模板）
    assert AG.dequant_skeleton(a, names) == AG.dequant_skeleton(b, names)
    # 人名不遮时两句仍同骨架（差异出现在第 16 字之后）——遮蔽只是锦上添花
    assert AG.dequant_skeleton(a) == AG.dequant_skeleton(b)
    # 不同骨架不误判
    c = "今早起来先喂了鸡，顺手把院里的水缸挑满。"
    assert AG.dequant_skeleton(c, names) != AG.dequant_skeleton(a, names)
    # 字面黑名单只用于断言：不改台词
    assert a != b and "第三格" in a


def test_guard_flags_repeat_per_slot_and_never_edits_body(monkeypatch, tmp_path):
    monkeypatch.setenv(AG.DEQUANT_ENV, "1")
    agent = _agent(tmp_path)
    body1 = "把这份卷宗归到第三格后，我想起老陈上回漏填了日期，害得整批文书返工。"
    body2 = "把这份卷宗归到第三格后，我想起老陈上回漏填了日期，还是得按规矩补上。"
    r1 = agent._dequant_guard(body1, "morning")
    r2 = agent._dequant_guard(body2, "morning")
    assert r1["repeated"] is False
    assert r2["repeated"] is True                     # 同 slot 同骨架 ⇒ 断言命中
    assert agent._dequant_stats["repeated"] == 1
    assert agent._dequant_stats["checked"] == 2
    assert agent._dequant_stats["lexicon_hit"] == 2   # 两句都命中字面黑名单
    assert "第三格" in r1["lexicon_hits"] and "上回" in r1["lexicon_hits"]
    # 换 slot ⇒ 不误判
    r3 = agent._dequant_guard(body2, "evening")
    assert r3["repeated"] is False
    # guard 只记账：不改台词（`_dequp_body` 在 L-7 结构臂下直接 return body）
    monkeypatch.setenv(L7S.STRUCT_ENV, "1")
    out = agent._dequp_body("prompt", body1, {"agent_id": SELF_ID}, slot="morning")
    assert out == body1


def test_guard_off_is_noop(monkeypatch, tmp_path):
    monkeypatch.setenv(AG.DEQUANT_ENV, "0")
    agent = _agent(tmp_path)
    assert agent._dequant_guard("刨到第三格，想起老陈上回那把椅子。", "morning") is None
    assert agent._dequant_stats == {"checked": 0, "lexicon_hit": 0, "repeated": 0}
    assert agent._dequant_slot_seen == {}


# --------------------------------------------- D 度量脚本自证（基线复算）
def test_probe_reproduces_recon_baseline():
    if not BASELINE_LOG.exists():
        pytest.skip("基线日志不可用（打包/分支场景）")
    path = REPO / "tools" / "metrics" / "dequant_probe.py"
    spec = importlib.util.spec_from_file_location("_dequant_probe", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    bodies, by_type = mod.load_bodies(BASELINE_LOG)
    res = mod.probe(bodies, by_type)
    assert res["n_msg"] == 510
    assert res["keywords"]["上回"]["pct"] == pytest.approx(79.8, abs=0.4)
    assert res["keywords"]["第三格"]["pct"] == pytest.approx(29.8, abs=0.4)
    assert res["keywords"]["半指"]["pct"] == pytest.approx(23.7, abs=0.4)
