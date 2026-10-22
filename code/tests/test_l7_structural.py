"""L-7 结构臂（`life/l7_structural.py`）单测 —— R17 预注册口径的执行侧守门。

五条硬断言（对应 `docs/forensics/2026-10-22-l7-structural-prereg.md` §3）：
  A. **默认 ON / env 可关**：不设 env ⇒ `enabled()` 为 True；`0/false/no/off` ⇒ False，
     且关闭后 `plan()` None、`render()` 空串、`audit()` None（提示词与 payload 零扰动）。
  B. **单变量插入**：ON 的两个提示词 = OFF 的同一串 + **恰好一处**插入（既有段落、
     尤其 R15 的收尾指令，逐字节不变）。
  C. **确定性 + 分布**：`assign()` 同参恒等；在 agent×时段样本上开口/收束两种结构
     都能取到全部取值（不是常数指派）。
  D. **口径镜像**：`normalize` 与官方 `tools/d5/dialogue_metrics.py::normalize_body`
     逐字一致；`_dequp_body` 在结构臂开启时**零额外 LLM 调用**（重试已前移）。
  E. **无进程级状态（replay 安全）**：禁忌开头只从 `wv.visible_events` 现取，
     审计字段不含跨 run 计数器 ⇒ 同 seed 两次跑 / 续跑逐字节一致
     （由 `test_periodic_flush` / `test_resume_from_flush` 端到端兜底）。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from life import l7_structural as L7S
from life.agent import LifeLayerAgent
from life.llm import LLMResult
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas

CODE_DIR = Path(__file__).resolve().parents[1]
REPO = CODE_DIR.parent
CONFIG = CODE_DIR / "config"
SELF_ID = "P003"
PARTNER_ID = "P002"

SEG_HEAD = "\n这一句换个说法："
BAN_HEAD = "\n这几个开头镇上最近已经有人用过了，别再用："
_TAIL_D = ("\n只写台词本身（一句家常话）：不要用括号、方括号或星号写动作、神态或心理旁白，"
           "不要解释也不要总结；用口语短句，别反复用同一句口头禅。")
_TAIL_R = ("\n只写台词本身（接着刚才的话往下说一句）：不要用括号、方括号或星号写动作、神态或心理旁白，"
           "不要解释也不要总结；用口语短句，别反复用同一句口头禅。")


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


def _ev(body: str, typ: str = "MSG_DM"):
    return SimpleNamespace(type=typ, payload={"body": body})


def _wv(bodies=(), day: int = 3, round_no: int = 17, dow: int = 2, slot: str = "morning"):
    """最小世界视图替身：`_l7_struct_line` 要 day/round/time，`recent_bodies` 要 visible_events。"""
    return SimpleNamespace(day=day, round=round_no,
                           time=SimpleNamespace(day_of_week=dow, slot=slot),
                           visible_events=[_ev(b) for b in bodies])


def _official_normalize():
    path = REPO / "tools" / "d5" / "dialogue_metrics.py"
    if not path.exists():
        pytest.skip("tools/d5/dialogue_metrics.py 不可用（分支/打包场景）")
    spec = importlib.util.spec_from_file_location("_dm_official_l7s", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.normalize_body


@pytest.fixture(autouse=True)
def _clean_state():
    L7S.reset()
    yield
    L7S.reset()


# ---- A. 开关 ---------------------------------------------------------------
def test_default_on_and_env_off(monkeypatch):
    """A. 结构臂默认 ON（本分支即处理臂）；四个取值可关。"""
    monkeypatch.delenv(L7S.STRUCT_ENV, raising=False)
    assert L7S.enabled() is True, "本分支上结构臂必须默认 ON，否则取证方会白跑一条批"
    for v in ("0", "false", "NO", " off "):
        monkeypatch.setenv(L7S.STRUCT_ENV, v)
        assert L7S.enabled() is False
    monkeypatch.setenv(L7S.STRUCT_ENV, "1")
    assert L7S.enabled() is True


def test_off_means_no_plan_render_audit(monkeypatch):
    """A. 关闭 ⇒ plan None / render 空串 / audit None（零扰动）。"""
    monkeypatch.setenv(L7S.STRUCT_ENV, "0")
    assert L7S.plan(SELF_ID, [PARTNER_ID], 3, "2-morning", 17, 0, "initiate") is None
    assert L7S.render(None) == ""
    assert L7S.audit(None) is None


# ---- B. 单变量插入 ---------------------------------------------------------
def test_on_prompts_differ_by_exactly_one_segment(monkeypatch, tmp_path):
    """B. ON = OFF + 恰好一处插入；既有段落（含 R15 收尾指令）逐字节不变。"""
    agent = _agent(tmp_path)
    history = [("名2", "早上好。")]
    wv = _wv(["秀娘，你家的鸡又跑了。"])

    monkeypatch.setenv(L7S.STRUCT_ENV, "0")
    d_off = agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID], wv=wv)
    r_off = agent._reply_prompt(PARTNER_ID, "tpl-1", history, wv=wv)

    monkeypatch.setenv(L7S.STRUCT_ENV, "1")
    d_on = agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID], wv=wv)
    seg_d = L7S.render(agent._l7s)
    r_on = agent._reply_prompt(PARTNER_ID, "tpl-1", history, wv=wv)
    seg_r = L7S.render(agent._l7s)

    assert seg_d.startswith(SEG_HEAD) and seg_r.startswith(SEG_HEAD)
    assert d_on.count(seg_d) == 1 and r_on.count(seg_r) == 1
    assert d_on.replace(seg_d, "", 1) == d_off
    assert r_on.replace(seg_r, "", 1) == r_off

    # R15 收尾指令（A1 措辞臂）逐字节未变
    assert d_on.endswith(_TAIL_D) and r_on.endswith(_TAIL_R)


def test_audit_is_additive_and_absent_when_off(monkeypatch, tmp_path):
    """B. 审计只追加 `ctx.l7struct`（不含跨 run 计数器）；关闭时不出现该键。"""
    agent = _agent(tmp_path)
    wv = _wv(["秀娘，你家的鸡又跑了。"])
    monkeypatch.setenv(L7S.STRUCT_ENV, "1")
    agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID], wv=wv)
    ctx = agent._ctx_snapshot(PARTNER_ID, "tpl-1")
    assert ctx["l7struct"]["v"] == "l7-struct/1"
    assert ctx["l7struct"]["n_banned"] == 1
    assert set(ctx["l7struct"]) == {"v", "open", "open_name", "end", "end_name",
                                    "n_banned", "mode"}, "审计字段不得含跨 run 计数器"

    monkeypatch.setenv(L7S.STRUCT_ENV, "0")
    agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID], wv=wv)
    assert "l7struct" not in agent._ctx_snapshot(PARTNER_ID, "tpl-1")


def test_prompt_without_wv_stays_unconstrained(tmp_path):
    """B. `wv=None`（单测/降级路径）不加任何结构段，既有单测的逐字节断言不受影响。"""
    agent = _agent(tmp_path)
    assert agent._l7_struct_line(None, [PARTNER_ID], 0, "initiate") == ""
    assert agent._l7s is None


# ---- C. 确定性与分布 -------------------------------------------------------
def test_assign_is_deterministic():
    """C. 同参恒等（可复现），且不使用内置 hash（换 PYTHONHASHSEED 也一致）。"""
    a = L7S.assign(SELF_ID, [PARTNER_ID], 3, "2-morning", 17, 0, "initiate")
    b = L7S.assign(SELF_ID, [PARTNER_ID], 3, "2-morning", 17, 0, "initiate")
    assert a == b


def test_assign_covers_all_forms():
    """C. 不是常数指派：agent×时段样本上两种结构都取到全部取值。"""
    opens, ends = set(), set()
    for agent in ("P001", "P002", "P003", "P004"):
        for day in range(1, 6):
            for rnd in range(0, 60, 3):
                for turn in (0, 1):
                    oi, ei = L7S.assign(agent, ["P009"], day, f"{day}-morning", rnd, turn, "reply")
                    opens.add(oi)
                    ends.add(ei)
    assert opens == set(range(len(L7S.OPEN_FORMS)))
    assert ends == set(range(len(L7S.END_FORMS)))


# ---- E. 无进程级状态（replay 安全）-----------------------------------------
def test_banned_openers_come_from_visible_events():
    """E. 禁忌开头来自 `wv.visible_events`（新→旧），不依赖任何进程级状态。"""
    wv = _wv(["秀娘，你家的鸡又跑了。", "唉，这天气真闷。", "我去集市上转了一圈。",
              "秀娘，你今天看起来有点累。", "哦，是吗。"])
    bodies = L7S.recent_bodies(wv)
    assert bodies[0] == "哦，是吗。" and bodies[-1] == "秀娘，你家的鸡又跑了。"
    pl = L7S.plan(SELF_ID, [PARTNER_ID], 3, "2-morning", 17, 0, "initiate", recent=bodies)
    banned = pl["banned"]
    assert banned, "最近的台词应产出禁忌开头"
    assert len(banned) <= L7S.BAN_SAMPLES and len(banned) == len(set(banned))
    assert all(len(b) == L7S.OPENER_CHARS for b in banned)
    # 新→旧取头部：最近的「哦，是吗。」归一化后仅 3 字（< OPENER_CHARS）不参与，
    # 因此第一个禁忌开头来自下一条「秀娘，你今天看起来有点累。」
    assert banned[0] == L7S.normalize("秀娘，你今天看起来有点累。")[:L7S.OPENER_CHARS]
    seg = L7S.render(pl)
    assert BAN_HEAD in seg
    for b in banned:
        assert b in seg


def test_same_inputs_same_plan_twice():
    """E. 同一世界视图两次装配 ⇒ 提示词/审计逐字节一致（无隐藏状态）。"""
    wv = _wv(["秀娘，你家的鸡又跑了。"])
    p1 = L7S.plan(SELF_ID, [PARTNER_ID], 3, "2-morning", 17, 0, "initiate",
                  recent=L7S.recent_bodies(wv))
    p2 = L7S.plan(SELF_ID, [PARTNER_ID], 3, "2-morning", 17, 0, "initiate",
                  recent=L7S.recent_bodies(wv))
    assert L7S.render(p1) == L7S.render(p2)
    assert L7S.audit(p1) == L7S.audit(p2)


# ---- D. 口径镜像 + 零额外调用 ----------------------------------------------
def test_normalize_mirrors_official():
    """D. 口径镜像：与官方 normalize_body 逐字一致。"""
    official = _official_normalize()
    samples = [
        "今天这锅汤我少放了半勺盐，多搁了一小把干贝。",
        "老石啊，你尝尝这个新烤的桂花糕（2026-10-21）……",
        "  Mixed 大小写 ABC 123，带\t制表符  ",
        "“引号”‘单引号’【方括号】[中括号]",
        "",
    ]
    for s in samples:
        assert L7S.normalize(s) == official(s), s


def test_dequp_body_makes_no_extra_llm_call(monkeypatch, tmp_path):
    """D. 结构臂开启 ⇒ `_dequp_body` 不再撞车重试（零额外调用），原样返回。"""
    monkeypatch.delenv(L7S.STRUCT_ENV, raising=False)   # 默认 ON
    agent = _agent(tmp_path)
    calls = []

    class _FakeLLM:
        def call(self, purpose, prompt, *, model=None, meta=None):  # pragma: no cover
            calls.append(1)
            return LLMResult(text="x")

    agent.llm = _FakeLLM()
    body = "今天这锅汤我少放了半勺盐，多搁了一小把干贝，鲜得很"
    assert agent._dequp_body("BASE", body, {}) == body
    assert calls == [], "结构臂开启后禁止再走生成后重试"
