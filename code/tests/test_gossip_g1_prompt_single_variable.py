"""G 系列 A1 臂 · 「闲话/第三方提及」提示词改动的**单变量**单测。

被测：(1) `LifeLayerAgent._gossip_hint`（可引用真人名单出口）；
      (2) `_dialogue_prompt` / `_reply_prompt` 的插入点。

三条硬断言（对应 DESIGN-preregistration.md §1.2/§2.1/§7）：
  A. **默认 OFF 时零扰动**：两个提示词里没有名单段，且行为与改前一致（逐字节）。
  B. **ON 时只插入一段**：`on.replace(seg, "", 1) == off` —— 换句话说，A0/A1 两臂
     的提示词**只差这一处插入**，既有段落（persona/场景/处境/历史/收尾指令）字节不变。
  C. **名单本身正确**：名字取自 personas.json 已有显示名词表，**排除自己与当前对话对象**
     （否则只是"称呼率"的别名，DESIGN §2.1 去噪第 1 条）。
"""
from __future__ import annotations

import json
from pathlib import Path

from life.agent import GOSSIP_G1_ENV, LifeLayerAgent, gossip_g1_enabled
from life.dialogue_threads import build_display_map, core_name
from life.memory import HashEmbeddingModel, SideStore
from life.persona import load_personas

CODE_DIR = Path(__file__).resolve().parents[1]
CONFIG = CODE_DIR / "config"

SEG_HEAD = "镇上还住着："
SELF_ID = "P003"
PARTNER_ID = "P002"


class _StubKernel:
    def submit_intent(self, *a, **kw):  # pragma: no cover - 本测试不落事件
        pass


def _agent(tmp_path: Path, peers: list, peer_names: dict) -> LifeLayerAgent:
    places = {p["place_id"]: p for p in
              json.loads((CONFIG / "places.json").read_text(encoding="utf-8"))["places"]}
    persona = load_personas(CONFIG / "personas.json")[SELF_ID]
    return LifeLayerAgent(SELF_ID, persona, _StubKernel(),
                          side_store=SideStore(tmp_path / "side"),
                          embedding=HashEmbeddingModel(), places=places,
                          peers=peers, peer_names=peer_names)


def _roster_names() -> set:
    """personas.json 的原始 display_name 主干名集合，用作"名单只能来自这里"的对照集。"""
    raw = json.loads((CONFIG / "personas.json").read_text(encoding="utf-8"))
    return {core_name(item.get("display_name") or "")
            for item in raw["personas"] if item.get("display_name")}


def _real_agent(tmp_path: Path) -> LifeLayerAgent:
    """用真实 personas.json 建 agent（名字表 = 生产注入的 build_display_map）。"""
    personas = load_personas(CONFIG / "personas.json")
    return _agent(tmp_path, sorted(personas), build_display_map(personas))


def _setup(tmp_path: Path):
    """5 个居民的小 run：自己 P003、对话对象 P002、可提的 P001/P004/P005。"""
    names = {pid: f"名{pid[-1]}" for pid in ("P001", "P002", "P003", "P004", "P005")}
    peers = ["P001", "P002", "P003", "P004", "P005"]
    return _agent(tmp_path, peers, names), names


def test_switch_default_off(monkeypatch):
    """A. 开关默认关（不设 env ⇒ False）。"""
    monkeypatch.delenv(GOSSIP_G1_ENV, raising=False)
    assert gossip_g1_enabled() is False
    for v in ("1", "true", "YES", " on "):
        monkeypatch.setenv(GOSSIP_G1_ENV, v)
        assert gossip_g1_enabled() is True
    monkeypatch.setenv(GOSSIP_G1_ENV, "0")
    assert gossip_g1_enabled() is False


def test_off_prompts_have_no_roster_and_are_byte_identical(monkeypatch, tmp_path):
    """A. OFF ⇒ 两个提示词里没有名单段，且与"去掉插入段后的 ON 提示词"逐字节相同。"""
    monkeypatch.setenv(GOSSIP_G1_ENV, "0")
    agent, _ = _setup(tmp_path)
    history = [(f"名{PARTNER_ID[-1]}", "早上好。")]
    d_off = agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID])
    r_off = agent._reply_prompt(PARTNER_ID, "tpl-1", history)
    assert SEG_HEAD not in d_off and SEG_HEAD not in r_off
    assert agent._gossip_hint([PARTNER_ID]) == ""

    monkeypatch.setenv(GOSSIP_G1_ENV, "1")
    d_on = agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID])
    r_on = agent._reply_prompt(PARTNER_ID, "tpl-1", history)
    seg_d = agent._gossip_hint([p for p in [SELF_ID, PARTNER_ID] if p != SELF_ID])
    seg_r = agent._gossip_hint([PARTNER_ID])
    assert seg_d == seg_r

    # B. 单变量核心：ON = OFF 的同一串 + 恰好一处插入
    assert d_on.count(seg_d) == 1 and r_on.count(seg_r) == 1
    assert d_on.replace(seg_d, "", 1) == d_off
    assert r_on.replace(seg_r, "", 1) == r_off
    assert len(d_on) - len(d_off) == len(seg_d)
    assert len(r_on) - len(r_off) == len(seg_r)


def test_on_roster_excludes_self_and_partner(monkeypatch, tmp_path):
    """C. 名单排除自己与当前对话对象；其余在场居民按确定性顺序全部列出。"""
    monkeypatch.setenv(GOSSIP_G1_ENV, "1")
    agent, names = _setup(tmp_path)
    seg = agent._gossip_hint([PARTNER_ID])
    assert SEG_HEAD in seg
    for pid in ("P001", "P004", "P005"):
        assert names[pid] in seg, f"应可提 {pid}"
    for pid in (SELF_ID, PARTNER_ID):
        assert names[pid] not in seg, f"不得把自己/对话对象列为可提对象（{pid}）"
    # 确定性：两次调用逐字节一致（同 run 同输入）
    assert seg == agent._gossip_hint([PARTNER_ID])


def test_roster_names_come_from_personas_json(monkeypatch, tmp_path):
    """C. 名单来源单一性：只用 personas.json 已有的显示名词表，不新造名字。"""
    monkeypatch.setenv(GOSSIP_G1_ENV, "1")
    personas = load_personas(CONFIG / "personas.json")
    peer_names = build_display_map(personas)
    agent = _agent(tmp_path, sorted(personas), peer_names)
    seg = agent._gossip_hint([])
    allowed = _roster_names() - {peer_names[SELF_ID]}
    body = seg.split("镇上还住着：", 1)[1].split("。", 1)[0]
    listed = [n for n in body.split("、") if n]
    assert listed, "名单不得为空"
    assert set(listed) <= allowed, f"出现了不在 personas.json 名字表里的名字：{set(listed) - allowed}"
    assert len(listed) == len(set(listed)), "名单内不得重名"


def test_no_switch_side_effects_beyond_prompt(monkeypatch, tmp_path):
    """B. 开关只影响提示词文本：OFF/ON 两态的 mood/关系行等既有片段仍然完全一致。"""
    monkeypatch.setenv(GOSSIP_G1_ENV, "0")
    agent, _ = _setup(tmp_path)
    d_off = agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID])
    tail = "\n只写台词本身（一句家常话）：不要用括号、方括号或星号写动作、神态或心理旁白，不要解释也不要总结；用口语短句，别反复用同一句口头禅。"
    head = d_off.split(tail, 1)[0]
    monkeypatch.setenv(GOSSIP_G1_ENV, "1")
    d_on = agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID])
    # 收尾指令逐字节未变，且前缀（persona+场景+情绪+处境）逐字节未变
    assert d_on.endswith(tail)
    assert d_on.startswith(head)


# ---------------------------------------------------------------------------
# 基线（commit d9391a3）冻结参照实现：**逐字复制改前两个函数的装配表达式**。
# 这段代码的唯一作用是把"改前的渲染结果"钉死在测试里，使 ① 号断言能红：
# 只要有人动了既有段落（哪怕加一个空格），OFF 态与基线就不再逐字节相等。
# ---------------------------------------------------------------------------
BASELINE_SHA = "d9391a3"
_BASE_DLG_TAIL = ("\n只写台词本身（一句家常话）：不要用括号、方括号或星号写动作、神态或心理旁白，"
                  "不要解释也不要总结；用口语短句，别反复用同一句口头禅。")
_BASE_RPY_TAIL = ("\n只写台词本身（接着刚才的话往下说一句）：不要用括号、方括号或星号写动作、神态或心理旁白，"
                  "不要解释也不要总结；用口语短句，别反复用同一句口头禅。")
_RIFT_SAMPLE = "\n【R6-T2 处境样张】上次你俩为他借锄头没还拌过嘴。选项：说开 / 不提。"


def _baseline_dialogue_prompt(agent, tid, parts, rift_line=None):
    """d9391a3 版 `_dialogue_prompt` 的逐字副本。"""
    partners = [p for p in parts if p != agent.agent_id]
    others = agent._relation_line(partners) or "(独自)"
    return (agent.persona.compressed_profile(agent._current_goal())
            + f"\n场景：{tid}；对象：{others}。{agent._mood_line()}。"
            + (rift_line or "")
            + _BASE_DLG_TAIL)


def _baseline_reply_prompt(agent, partner, topic, history, rift_line=None):
    """d9391a3 版 `_reply_prompt` 的逐字副本。"""
    lines = "\n".join(line for _, line in history) or "(还没说什么)"
    who = agent._name(partner) if partner else "在场的人"
    return (agent.persona.compressed_profile(agent._current_goal())
            + f"\n你正在和{who}聊「{topic}」。{agent._mood_line()}。"
            + (rift_line or "")
            + f"\n刚才的对话：\n{lines}"
            + _BASE_RPY_TAIL)


def test_off_is_byte_identical_to_baseline_d9391a3(monkeypatch, tmp_path):
    """① 硬断言：**不设 env**（生产默认 = OFF）时，两处渲染与基线 d9391a3 逐字节一致。

    覆盖 rift_line 有值/无值两态——既有段落一个字节都不许动（能红：改一个空格即失败）。
    """
    monkeypatch.delenv(GOSSIP_G1_ENV, raising=False)
    agent, _ = _setup(tmp_path)
    history = [(f"名{PARTNER_ID[-1]}", "早上好。"), (f"名{SELF_ID[-1]}", "早啊。")]
    for rift in (None, _RIFT_SAMPLE):
        assert agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID], rift_line=rift) == \
            _baseline_dialogue_prompt(agent, "tpl-1", [SELF_ID, PARTNER_ID], rift_line=rift), \
            f"OFF 态 _dialogue_prompt 与基线 {BASELINE_SHA} 不再逐字节一致（rift={rift!r}）"
        assert agent._reply_prompt(PARTNER_ID, "tpl-1", history, rift_line=rift) == \
            _baseline_reply_prompt(agent, PARTNER_ID, "tpl-1", history, rift_line=rift), \
            f"OFF 态 _reply_prompt 与基线 {BASELINE_SHA} 不再逐字节一致（rift={rift!r}）"


def test_on_diff_is_single_hint_line_only(monkeypatch, tmp_path):
    """② 硬断言：ON 态相对 OFF 的差异**只有一行 hint**，且该行名字全来自 personas.json。"""
    monkeypatch.setenv(GOSSIP_G1_ENV, "1")
    agent = _real_agent(tmp_path)          # 真实 personas 名字表（本条要验"名字来源"）
    history = [(agent._name(PARTNER_ID), "早上好。")]
    seg_d = agent._gossip_hint([PARTNER_ID])

    # 差异只在"一行"里：hint 恰好以换行开头、且自身只含一个换行（= 新增一行）
    assert seg_d.startswith("\n" + SEG_HEAD)
    assert seg_d.count("\n") == 1, f"hint 必须是一行，实际：{seg_d!r}"

    monkeypatch.delenv(GOSSIP_G1_ENV, raising=False)
    d_off = agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID])
    r_off = agent._reply_prompt(PARTNER_ID, "tpl-1", history)
    monkeypatch.setenv(GOSSIP_G1_ENV, "1")
    d_on = agent._dialogue_prompt("tpl-1", [SELF_ID, PARTNER_ID])
    r_on = agent._reply_prompt(PARTNER_ID, "tpl-1", history)

    # 逐行 diff：唯一新增行 == hint 去掉前导换行的内容
    added_d = [ln for ln in d_on.split("\n") if ln not in d_off.split("\n")]
    assert added_d == [seg_d.lstrip("\n")], f"新增行不止 hint：{added_d}"
    assert len(d_on.split("\n")) - len(d_off.split("\n")) == 1

    names_in_hint = [n for n in seg_d.split(SEG_HEAD, 1)[1].split("。", 1)[0].split("、") if n]
    allowed = _roster_names() - {agent._peer_names[SELF_ID]}
    assert set(names_in_hint) <= allowed, f"hint 用了 personas.json 之外的名字：{set(names_in_hint) - allowed}"
    # reply 侧同一条 hint 行（对象改为 partner，两侧 hint 因此相同：同样排除自己+对象）
    assert r_on.replace(agent._gossip_hint([PARTNER_ID]), "", 1) == r_off
