"""Agent cognition main loop: perceive -> retrieve -> plan -> act -> reflect.

Generative Agents `Persona.move()` *structure* (persona/persona.py, Apache-2.0),
adapted to our deterministic kernel: every step reads ONLY from `kernel.perceive()`
(IF-1) and writes ONLY by handing an `Intent` to `kernel.submit_intent()` (IF-2).
The agent never mutates world state.

  perceive  : refresh local cache + track own needs + record salient observations
  retrieve  : three-factor memory retrieval (logged as MEMORY_RETRIEVE)
  plan      : weekly plan (deprivation-aware) -> INTENT.PLAN; seed goals -> INTENT.GOAL
  act       : move toward the planned place -> INTENT.MOVE
  reflect   : accumulated-importance / weekly trigger -> reflection memories
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import constants as C
from . import goals as G
from . import degrade as _degrade
from . import relations as R
from .llm import LLMClient, get_llm_client
from .memory import AssociativeMemory, EmbeddingModel, HashEmbeddingModel, SideStore
from .persona import Persona
from . import persona_drift as PD
from . import emotion as E
from . import emotion_echo as EE   # F-3：情绪呼应臂（env HITT_DIALOGUE_EMOTION_ECHO，默认 OFF）
from . import public_talk as PT   # R41：公开面接话臂（env HITT_DIALOGUE_PUBLIC_REPLY，默认 OFF）
from . import dialogue_threads as DT
from . import dialogue_repair as DR
from . import sleep_window as _sleep
from . import anti_repeat as AR   # R12：L-7 去重臂（env LIFE_PROMPT_MEMORY_F6_DEQUP，默认 OFF）
from . import l7_structural as L7S  # L-7 结构臂（env LIFE_PROMPT_L7_STRUCT，**默认 ON**）
from . import topic_breadth as TB  # R19 话题宽度臂（env LIFE_PROMPT_TOPIC_BREADTH，**默认 OFF**）
from . import scene_anchor as SA  # 处境锚臂（env LIFE_PROMPT_SCENE，**默认 OFF**）
from . import weather as WX  # 天气臂（env HITT_WEATHER，**默认 OFF**）：今儿的天进提示词
from .policy import (social_enabled, exchange_enabled, m2b_judge_mode, m2b_importance_mode,
                     narrative_persist_enabled)
from .ports import (
    INTENT_ECON_OFFER,
    INTENT_GOAL, INTENT_MEMORY, INTENT_MOVE, INTENT_OBSERVE, INTENT_PLAN, INTENT_RELATION,
    INTENT_SOCIAL, Intent, KernelPort,
)
from .soft import get_soft_layer, rng_branch
from .util import clamp, sha256_hex

# G 系列 A1 臂开关（闲话/第三方提及）：**只影响提示词文本**，默认 OFF。
# 目的（DESIGN-preregistration.md §7「开关化」）：A0 与 A1 用同一份代码跑，
# 两臂之间只剩「提示词里有没有这份名单」这一个差异，单变量可证。
GOSSIP_G1_ENV = "LIFE_PROMPT_GOSSIP_G1"


def gossip_g1_enabled() -> bool:
    """A1 臂开关（env `LIFE_PROMPT_GOSSIP_G1` ∈ {1,true,yes,on}）；默认关。"""
    return os.environ.get(GOSSIP_G1_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


# F-6 臂开关（跨天记忆进对话提示词）：**只影响提示词文本 + 一个附加审计字段**，默认 OFF。
# 目的：OFF/ON 用同一份代码跑，两臂之间只剩「提示词里有没有这段记忆」这一个差异。
MEMORY_F6_ENV = "LIFE_PROMPT_MEMORY_F6"
#: 每次装配最多注入几条跨天记忆（控 token；2 条≈60 token 量级）
MEMORY_F6_TOP_N = 2
#: 单条记忆正文截断长度（字符）
MEMORY_F6_ITEM_CHARS = 60
#: D1（本轮）：`TOP_N` 里留给「固化印象」（`kind=="semantic"`，即 `-SM-` 条目）的保底名额。
#: 改前：两个槽位由 observation 桶先占满 ⇒ 固化印象**基本排不进**（R20 静态定位的根因②）。
#: 改后：先给固化印象 1 个槽，剩余额度再按 observation → 其它 的顺序填。
#: `TOP_N` 本身**不变**（仍是 2），变的只是准入顺序；该常量可审计、可解释为
#: 「一次最多想起 1 件攒下来的印象 + 1 件具体的事」。设为 0 即退化为改动前的行为。
MEMORY_F6_SEMANTIC_QUOTA = 1


def memory_f6_enabled() -> bool:
    """F-6 臂开关（env `LIFE_PROMPT_MEMORY_F6` ∈ {1,true,yes,on}）；默认关。"""
    return os.environ.get(MEMORY_F6_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


# N-15 称呼演化臂开关（env `LIFE_PROMPT_ADDR_EVOLVE`）：**只影响对话提示词（`_dialogue_prompt`）一行文本**，默认 OFF。
# 预登记：`v2/refs/N15-prereg-addr-evolve-20261030.md`（主判据 `S-1 = addr_swing_pairs_rate`，可检出线 `Δ ≥ +20pp`）。
# 单变量约束（预登记 §8.1/§8.4）：**只**注入 `_dialogue_prompt`，**不**改 `_reply_prompt`；**不**做称呼替换表 /
# 轮换池 / 定时换称呼；**不**读关系值数值阈值做分支。缺省 / 空串 / 其它值 ⇒ OFF，且 OFF 态与改动前逐字节相同。
ADDR_EVOLVE_ENV = "LIFE_PROMPT_ADDR_EVOLVE"

#: 注入行（**实现时冻结**；≤1 句、无示例、无轮换、无多行模板）。其 sha256 记入回执与证据。
ADDR_EVOLVE_LINE = "\n跟一个人处得越熟，叫法就该跟着变一变——熟了以后别再一直用最初那个称呼。"


def addr_evolve_enabled() -> bool:
    """N-15 臂开关（env `LIFE_PROMPT_ADDR_EVOLVE` ∈ {1,true,yes,on}）；默认关。"""
    return os.environ.get(ADDR_EVOLVE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


# 旁白/动作神态通道开关：**只影响 prompt 收尾指令的文本**。
# D9i 阶段它是「仅靠 env 的实验开关、默认 0 = 禁旁白」；ROUND1（本分支 feat/narration-default-on）把它
# **默认化**：默认值改由 `config/life_v2.json` 的 `prompt.narration.enabled` 提供（文件内写 true）,
# env `LIFE_PROMPT_NARRATION` 仍是**显式覆盖**（`=0/false/off/no` 即关闭，`=1/true/yes/on` 即打开），
# 未设时读配置 ⇒ 默认**开**。
# 硬约束（v2/refs/D9i-prereg-narration-toggle.md）：默认化**只改默认值**，两条收尾指令的字面量
# （`_NARRATION_TAIL_OFF` / `_NARRATION_TAIL_ON`）一字未动 ⇒ `LIFE_PROMPT_NARRATION=0` 仍与改动前
# **逐字节相同**；不改阈值 / 事件结构 / 调度 / 其它措辞。
NARRATION_ENV = "LIFE_PROMPT_NARRATION"

#: 默认值落点：`code/config/life_v2.json` 的 `prompt.narration.enabled`（与 life 其它段同样直读盘）。
NARRATION_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "life_v2.json"

#: 配置文件缺失 / 缺键 / 类型非法时的兜底默认值（默认化后为 True）。
NARRATION_DEFAULT_ENABLED = True

#: env 真值集（与既有臂保持同一套字面量；其余已设值一律按关处理 = D9i 老语义）
_ENV_TRUE = frozenset({"1", "true", "yes", "on"})


def narration_config_default() -> bool:
    """读 `config/life_v2.json :: prompt.narration.enabled`（缺文件/缺键/非 bool ⇒ 兜底 True）。"""
    try:
        data = json.loads(NARRATION_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return NARRATION_DEFAULT_ENABLED
    if not isinstance(data, dict):
        return NARRATION_DEFAULT_ENABLED
    sec = data.get("prompt")
    sec = sec.get("narration") if isinstance(sec, dict) else None
    if not isinstance(sec, dict):
        return NARRATION_DEFAULT_ENABLED
    v = sec.get("enabled", NARRATION_DEFAULT_ENABLED)
    return v if isinstance(v, bool) else NARRATION_DEFAULT_ENABLED

#: 显式关（env 已设且非真值，如 `=0`）时的收尾指令（= 改动前的字面量，逐字节保留；单测据此做 sha256 等价断言）
_NARRATION_TAIL_OFF = {
    "initiate": "\n只写台词本身（一句家常话）：不要用括号、方括号或星号写动作、神态或心理旁白，不要解释也不要总结；用口语短句，别反复用同一句口头禅。",
    "reply": "\n只写台词本身（接着刚才的话往下说一句）：不要用括号、方括号或星号写动作、神态或心理旁白，不要解释也不要总结；用口语短句，别反复用同一句口头禅。",
}

#: env=1 时的收尾指令：放开「成对括号的动作/神态/眼前景」，但**不得**放开到心理独白或旁白叙事。
_NARRATION_TAIL_ON = {
    "initiate": "\n只写台词本身（一句家常话，用成对的（）补一句动作、神态或眼前的景，如（把围裙往腰后一掖），但不要写心理独白或旁白叙事，不要用方括号或星号）：不要解释也不要总结；用口语短句，别反复用同一句口头禅。",
    "reply": "\n只写台词本身（接着刚才的话往下说一句，用成对的（）补一句动作、神态或眼前的景，如（低头刨木，木屑卷起），但不要写心理独白或旁白叙事，不要用方括号或星号）：不要解释也不要总结；用口语短句，别反复用同一句口头禅。",
}


def narration_enabled() -> bool:
    """旁白通道开关：**env 显式值 > `config/life_v2.json` 默认值**。

    * env ∈ {1,true,yes,on} ⇒ 开；其它**任何已设值**（含 `0` / ``空串`` / `false` / `off` / `no` / `2`）⇒ 关
      （= D9i 老语义，逐字未改）；
    * **只有 env 完全未设**时读配置 `prompt.narration.enabled`（默认化后 = True）。
      区分「未设」与「设为空串」是刻意的：显式 `LIFE_PROMPT_NARRATION=`（空）仍算显式关闭，
      这样老臂「置空即禁旁白」的历史行为不被默认化改写。
    """
    raw = os.environ.get(NARRATION_ENV)
    if raw is None:
        return narration_config_default()
    return raw.strip().lower() in _ENV_TRUE


# D9m 臂开关（旁白**示例句**确定性轮换）：只动 D9i 「旁白 ON」模板里 `如（…）` 那**一个示例句**，
# 其余字面量（删禁令、`成对（）`、`不要写心理独白或旁白叙事`、`不要用方括号或星号`、句尾口头禅）
# **逐字节不动**。默认关 ⇒ 直接返回 `_NARRATION_TAIL_ON` 常量对象 ⇒ 与 D9i ON 逐字节相同。
# 与 `LIFE_PROMPT_NARRATION` 的组合语义（四种）：
#   NARRATION 关 + 旋转任意  ⇒ `_NARRATION_TAIL_OFF`（禁旁白；旋转开关在此组合下**无效果**）
#   NARRATION 开 + 旋转关    ⇒ `_NARRATION_TAIL_ON`（D9i 原固定示例，常量对象）
#   NARRATION 开 + 旋转开    ⇒ `_NARRATION_TAIL_ON` 的示例句换成词表选句（唯一差异）
ROTATION_ENV = "LIFE_PROMPT_NARRATION_ROTATION"

#: 例句词表指纹（改词表 = 改行为，须重冻结；报告/runbook 侧按此对齐「尺子」身份）
NARRATION_EXAMPLE_LEXICON_VERSION = "narration-rotation-v1"

#: 示例句库（≥6 句，均为「动作 / 神态 / 眼前景」，只写人话、不出内部 token）。
#: 硬约束：**不得**含 蹭 / 磨 / 抹 / 擦（易与 L-7 高频动词复读叠加）与
#: 围裙 / 锉刀 / 木屑（D9i 固定示例里的旧道具，CYCLE-30 已登记为重复出现）。
#: 单测以正则逐字断言（防未来回潮），并对旋转开的多回合输出全量扫描同一词表。
NARRATION_EXAMPLES: tuple[str, ...] = (
    "抬手把鬓角的碎发别到耳后",
    "把袖口往上挽了一截",
    "低头拢了拢衣襟",
    "侧身让过挑担的街坊",
    "往门槛上靠了靠",
    "把竹篮往脚边挪了挪",
    "抬眼望了望日头",
    "伸手扇了扇风",
    "把凳子往后撤了半步",
)

#: 轮换臂模板：与 `_NARRATION_TAIL_ON` **逐字节相同**，只把 `如（<示例>）` 的示例替换成 `{}`。
#: 单测用 `_NARRATION_TAIL_ON_TPL[kind].format(_NARRATION_TAIL_ON_EXAMPLE[kind]) ==
#: _NARRATION_TAIL_ON[kind]` 硬锁「除示例句外一字未改」。
_NARRATION_TAIL_ON_TPL = {
    "initiate": "\n只写台词本身（一句家常话，用成对的（）补一句动作、神态或眼前的景，如（{}），但不要写心理独白或旁白叙事，不要用方括号或星号）：不要解释也不要总结；用口语短句，别反复用同一句口头禅。",
    "reply": "\n只写台词本身（接着刚才的话往下说一句，用成对的（）补一句动作、神态或眼前的景，如（{}），但不要写心理独白或旁白叙事，不要用方括号或星号）：不要解释也不要总结；用口语短句，别反复用同一句口头禅。",
}

#: D9i 原示例句（仅用于等价性自检；**不参与**轮换臂的输出）
_NARRATION_TAIL_ON_EXAMPLE = {"initiate": "把围裙往腰后一掖", "reply": "低头刨木，木屑卷起"}


def narration_rotation_enabled() -> bool:
    """D9m 臂开关（env `LIFE_PROMPT_NARRATION_ROTATION` ∈ {1,true,yes,on}）；默认关。"""
    return os.environ.get(ROTATION_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def narration_example(kind: str, agent_id: str | None = None,
                      round_no: int | None = None) -> str:
    """确定性选示例句：`sha256(seed|agent_id|round|kind)` 取词表下标。

    稳定输入只有三个：`HITT_WORLD_SEED`（缺省 `"0"`；与 weather 臂共用同一 env key，
    跑批时同批同一个 seed）、角色 id、回合号。**不读墙钟、不用 random** ⇒ replay 逐字节可复现。
    契约：**缺省回落**——env 未设或空串一律按 `"0"`，此时全批恒为 seed=0 的那一套序列
    （仍然确定；换 seed 则序列随 seed 变，不要误以为序列失稳）。
    """
    seed = (os.environ.get(WX.WORLD_SEED_ENV, "") or "0").strip() or "0"
    rnd = 0 if round_no is None else int(round_no)
    h = sha256_hex(f"narration-rotate|{seed}|{agent_id or ''}|{rnd}|{kind}")
    return NARRATION_EXAMPLES[int(h[:8], 16) % len(NARRATION_EXAMPLES)]


def narration_tail(kind: str, agent_id: str | None = None,
                   round_no: int | None = None) -> str:
    """返回对话 prompt 的收尾指令（D9i/D9m 唯一改动点）。

    kind ∈ {"initiate"（开场白）, "reply"（接话）}。
    NARRATION 关 ⇒ 改动前字面量（`_NARRATION_TAIL_OFF`，逐字节等价）；
    NARRATION 开 + 旋转关 ⇒ `_NARRATION_TAIL_ON` **常量对象**（不做任何字符串拼装）；
    NARRATION 开 + 旋转开 ⇒ 仅示例句换为 `narration_example(...)` 的确定性选句。
    """
    if not narration_enabled():
        return _NARRATION_TAIL_OFF[kind]
    if not narration_rotation_enabled():
        return _NARRATION_TAIL_ON[kind]
    return _NARRATION_TAIL_ON_TPL[kind].format(
        narration_example(kind, agent_id, round_no))

# ---- 同场偶遇搭话臂（encounter chat）-----------------------------------------
# 缺口（**窄口径**，可复算）：同场共处本身**一直有机制**——`code/life/settlement.py:580` 的
# `RELATION_ENCOUNTER` + `:583-584` 的 `copresence` 关系增量、`code/engine/wake.py:147` 的
# W6 邻居(共处)唤醒都在跑；**但「同场 → 直接搭一句话」的通道在 HEAD 上为零**：
# `_initiate()` 在 `template_id` 缺失时直接早退（见本文件 `_initiate` 首两行）
# ⇒「两个人正好站在同一处」这件事实**永远不会变成一句话**。
# 本臂把 life 层**已经可见**的 `PLACE_ARRIVED`（`config/perception_scope.json` 里是
# `place_local`，同处即互相可见）当作「同场」判据，在没有模板的空档里发一句非任务性搭话。
# 默认 OFF ⇒ 不新增任何事件、提示词逐字节不变（与接入前行为一致）。
ENCOUNTER_ENV = "LIFE_PROMPT_ENCOUNTER_CHAT"
ENCOUNTER_RATE_ENV = "LIFE_PROMPT_ENCOUNTER_CHAT_RATE"

#: 搭话话题标签（**人话**，不是内部 token；L-13 纪律：不许把内部 id 递给模型）
ENCOUNTER_TOPIC = "闲聊"

#: 夜里不搭话（居民在睡觉；`residence` 夜里同处不是可搭话的「场合」）
ENCOUNTER_SKIP_SLOTS = frozenset({"night"})

#: 默认门率（整数百分比）：每个 (agent, slot) 掷一次确定性骰，命中才搭话。
ENCOUNTER_RATE_DEFAULT = 50


def encounter_enabled() -> bool:
    """同场偶遇搭话臂开关（env `LIFE_PROMPT_ENCOUNTER_CHAT` ∈ {1,true,yes,on}）；默认关。"""
    return os.environ.get(ENCOUNTER_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def encounter_rate() -> int:
    """门率（0–100 整数百分比）；未设/非法 ⇒ `ENCOUNTER_RATE_DEFAULT`。关闭时不被读取。"""
    raw = os.environ.get(ENCOUNTER_RATE_ENV, "").strip()
    if not raw:
        return ENCOUNTER_RATE_DEFAULT
    try:
        val = int(raw)
    except ValueError:
        return ENCOUNTER_RATE_DEFAULT
    return max(0, min(100, val))


def encounter_world_seed() -> str:
    """与 weather / narration-rotation **共用同一个 seed env**（缺省回落 `"0"`，单一真源）。"""
    return (os.environ.get(WX.WORLD_SEED_ENV, "") or "0").strip() or "0"


def encounter_decision(agent_id: str, slot_id: str, peers: list) -> str | None:
    """确定性「搭不搭话、跟谁搭」：不读墙钟、不用 random ⇒ replay 逐字节可复现。

    步骤：① 候选 = 同处者去自去重后字典序（顺序与事件到达序无关，避免"谁先到谁被选中"）；
    ② `sha256("encounter|seed|agent|slot")` 取 8 hex nibble 对 100 取模，≥ 门率 ⇒ 不搭；
    ③ 命中后按 `sha256("encounter-pick|seed|agent|slot|peer")` 取最小值定序选人。
    返回 partner 或 None（不搭话 / 无人同处）。
    """
    cands = sorted(p for p in (peers or []) if p and p != agent_id)
    if not cands:
        return None
    seed = encounter_world_seed()
    h = sha256_hex(f"encounter|{seed}|{agent_id}|{slot_id}")
    if int(h[:8], 16) % 100 >= encounter_rate():
        return None
    return min(cands, key=lambda p: sha256_hex(
        f"encounter-pick|{seed}|{agent_id}|{slot_id}|{p}"))


_SALIENT_EVENTS = {
    "ACTIVITY_STARTED", "ACTIVITY_COMPLETED", "PLACE_ARRIVED",
    "MSG_PUBLIC", "MSG_DM", "MSG_GROUP", "RELATION_ENCOUNTER", "RELATION_CHANGE",
    "SEED_EVENT", "AGENT_DIED", "TAG_EMITTED", "NARRATIVE", "NORM_VIOLATED",
}

_TPL_TBL: dict | None = None


def _templates(places: dict) -> dict:
    global _TPL_TBL
    if _TPL_TBL is None:
        from .templates import load_activity_templates
        _TPL_TBL = load_activity_templates(places=places)
    return _TPL_TBL

# deprivation -> satisfying (activity_type, place), deterministic (06 §7.3)
_NEED_ACTIVITY = {
    "satiety": ("self_care", "kitchen"), "energy": ("rest", "residence"),
    "social": ("socialize", "plaza"), "leisure": ("leisure", "park"),
    "esteem": ("civic", "town_hall"), "mastery": ("learn", "school"),
}

# template_id -> dialogue channel (T98). private=MSG_DM, place_group=MSG_GROUP,
# global=MSG_PUBLIC.
_DM_TEMPLATES = {"whisper", "gift", "ice_break", "rel_maintain", "rel_accept",
                 "polite_reject", "counter_propose", "mentorship"}
_GROUP_TEMPLATES = {"creative_collab", "academic_collab", "power_conflict", "contest",
                    "combat_training"}
_PUBLIC_TEMPLATES = {"group_proposal", "job_choice"}


@dataclass
class StepReport:
    round: int
    perceived: int = 0
    observed: int = 0
    retrieved: list = field(default_factory=list)
    planned: bool = False
    goals_set: bool = False
    moved_to: str | None = None
    reflected: bool = False
    concentrated: bool = False
    soft_judgments: int = 0
    narrated: bool = False
    accepted: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    slept: int = 0


class LifeLayerAgent:
    def __init__(self, agent_id: str, persona: Persona, kernel: KernelPort, *,
                 llm: LLMClient | None = None, side_store: SideStore,
                 embedding: EmbeddingModel | None = None,
                 memory_params: dict | None = None,
                 places: dict[str, dict] | None = None,
                 peers: list[str] | None = None,
                 peer_names: dict[str, str] | None = None) -> None:
        self.agent_id = agent_id
        self.persona = persona
        self.kernel = kernel
        self.llm = llm or get_llm_client()
        self.embedding = embedding or HashEmbeddingModel()
        self.memory = AssociativeMemory(agent_id, self.embedding, side_store, memory_params)
        self.side_store = side_store       # T234: 叙事正文 writer 复用同一 side root
        self.places = places or {}
        self.peers = [p for p in (peers or []) if p and p != agent_id]
        self.soft = get_soft_layer(self.llm)
        self._rel_cache: dict = {}          # (to, dim) -> current outgoing relation value
        self._judged: set = set()           # (to, dim, level) already soft-judged
        self._llm_permit = True             # T221c: M4 本回合 LLM 许可（默认 True=不变）
        self._appraised: set = set()        # (to, week) already social-appraised (T127)
        self._narrated_weeks: set = set()
        self._comm_slot: str | None = None  # last slot we generated dialogue for (≤1/slot)
        # D2 线程化（agent-local 表达层状态；不进 state_hash、不发事件）
        self._peer_names = dict(peer_names or {})   # persona_id -> 提示词显示名（只读注入）
        self._slot_msgs: dict = {}                  # slot_id -> 本 slot 已发 MSG 条数（上限见配置）
        # R41：slot_id -> 本 slot 已发出的**公开接话**条数（默认 OFF 时恒空、不参与任何判断）
        self._slot_public_replies: dict = {}
        self._thread_replied_turn: dict = {}        # thread_id -> 我已回复到的最大 turn
        self._replied_msg_ids: set = set()          # 已回复过的 msg_id（防重复回同一条）
        self._round_replies = 0                     # 本回合已发出的回复数（K 上限）
        self._round_marker = -1
        self._pub_k = 0                             # 本回合 PUBLIC 线程自增序号
        self._accepted: set = set()         # offer_ids already accepted (T133)
        # own needs (initial from persona; then folded from own NEED_UPDATE events)
        self.needs: dict[str, int] = {d: int(persona.needs_init.get(d, 50)) for d in C.NEED_DIMS}
        # agent-local ephemera (NOT world state):
        self._planned_weeks: set[int] = set()
        self._goals_set_weeks: set[int] = set()
        self._plan_slots: dict[str, dict] = {}
        self._observed_seqs: set[int] = set()
        # T224 睡眠离线窗（默认关；见 config/life_v2.json）—— agent-local 表达层状态
        self._persona_state: dict | None = None
        self._persona_p0: dict | None = None
        self._slept_days: set[int] = set()
        self._drift_streak: dict[str, int] = {}  # T244: 逐维"连续被反思信号"计数（分抖动/真漂移）
        # T364：`world_params`（D3 口径②）消费计数 + 最近一次读数（**证据用**：证明消费点被读）
        # 纯观测：仅本对象内存计数，**不进 state_hash、不发事件、不进序列化/restore**。
        self._wp_reads: int = 0          # ① 端口读次数（证明"端口通了"）
        self._wp_nonempty: int = 0       # ② 参数非空次数（关 ⇒ 必须=0）
        self._wp_changed_choice: int = 0  # ③ 实际改变活动选择次数（"真影响行为"的直接证据）
        self._wp_last: dict | None = None
        # R6-T2 / F-4「误会与和解」上下文机制（默认关；见 config/dialogue_repair.json）
        # **只读台账 + 只给处境**：不写正文、不发事件、不进 state_hash。
        self._rifts: dict = {}              # rift_id -> {with, thread_id, msg_uid, seq, round, ...}
        self._rifts_seen: set = set()       # 已吸收的 MSG 事件 seq（增量、幂等）
        # F-6「记忆进对话」：本次装配实际注入的跨天记忆 id（**纯审计**，供 ctx 落盘追溯；
        # 不进 state_hash、不发事件、不参与决策；OFF 臂恒为空）。
        self._mem_refs: list = []
        # 处境锚臂（scene-anchor）：本条消息生成时实际下发的那一行处境的审计快照
        # （**纯审计**，供 ctx 落盘追溯；不进 state_hash、不发事件、不参与决策；
        #  OFF 臂恒为 None ⇒ ctx.scene 不出现）。
        self._scene: dict | None = None
        # 天气臂（weather）：本条消息生成时实际下发的那一行「今儿天怎么样」的审计快照
        # （**纯审计**，只进 ctx；不进 state_hash、不发事件、不参与决策；
        #  OFF 臂恒为 None ⇒ ctx.weather 不出现）。
        self._weather: dict | None = None
        # 同场偶遇搭话臂（encounter）：已在该 slot 掷过骰/搭过话的 slot_id 集合。
        # **agent-local 表达层状态**（不进 state_hash、不发事件）；OFF 臂恒为空。
        self._enc_slots: set = set()

    # ---- T288 / T276: 从账本单一真源恢复「只前向累积」的内部态 ---------------
    def restore(self, state, records) -> None:
        """Rebuild forward-accumulated internal state from the ledger (single source).

        Called by `orchestration` once, right after `load_prefix` (duck-typed hook).
        **只做「原样重建」，不做有界化**（有界化=改语义，另议）。

        Rebuilt: `_observed_seqs` / `needs` / `_plan_slots`(schedule) /
        `_planned_weeks` / `_goals_set_weeks` / `_comm_slot` / `_narrated_weeks` /
        `_accepted` / `_rel_cache`, plus `memory` via `sync_from_refs`.
        No new decision, no event payload change — the engine world state was already
        restored by `replay_records`; this only re-syncs the life-side mirrors.
        """
        from .ports import MemoryRef
        a = state.agents.get(self.agent_id)
        if a is None:
            return
        # memory (bodies/embeddings live in side storage; sync rebuilds nodes)
        self.memory.sync_from_refs(tuple(
            MemoryRef(mem_id=m["mem_id"], kind=m["kind"], body_ref=m["body_ref"],
                      embed_ref=m["embed_ref"], importance=int(m["importance"]),
                      day=int(m["day"]), slot=m["slot"], subject=m.get("subject"),
                      source_event_seq=m.get("source_event_seq"),
                      last_access=int(m.get("last_access", 0)),
                      access_count=int(m.get("access_count", 0)))
            for m in a.get("memories", [])))
        # memory reflection state (reflection dedup + unreflected accumulator):
        # otherwise the resumed run re-fires MEMORY_REFLECT (observed at N=20).
        _W = (C.TIME_CONFIG["DAYS_PER_WEEK"] * len(C.TIME_CONFIG["SLOTS_PER_DAY"])
              * C.TIME_CONFIG["ROUNDS_PER_SLOT"])
        for rec in records:
            if rec.get("type") == "MEMORY_REFLECT" and (rec.get("payload") or {}).get("agent_id") == self.agent_id:
                for mid in ((rec.get("payload") or {}).get("triggered_by_mem_ids") or []):
                    nd = self.memory.nodes.get(mid)
                    if nd is not None:
                        nd.reflected = True
                self.memory.note_reflection(int(rec.get("round", 0)) // _W)
        self.memory._unreflected_importance = sum(
            n.importance for n in self.memory.nodes.values()
            if n.kind == "observation" and not n.reflected)
        # T244 睡眠/人格前向态（原样重建）—— 否则 cut 落在 night 边界时，续跑会**重跑**该日
        # 睡眠窗（`_slept_days` 空）并丢失已累积的人格漂移（`_persona_state`）。
        slept: set = set()
        persona_after: dict = {}
        for rec in records:
            p = rec.get("payload") or {}
            if p.get("agent_id") != self.agent_id:
                continue
            t = rec.get("type")
            if t in ("SLEEP_STARTED", "SLEEP_COMPLETED") and p.get("day") is not None:
                slept.add(int(p["day"]))
            elif t == "PERSONA_DRIFT" and p.get("dim"):
                persona_after[p["dim"]] = p.get("after")
        self._slept_days = slept
        if slept or persona_after:
            anchor = {"personality_big5": self.persona.personality_big5}
            self._persona_p0 = PD.init_state(anchor)
            st = PD.init_state(anchor)
            for k, v in persona_after.items():
                if v is not None:
                    st[k] = int(v)
            self._persona_state = st
        # T323：`_drift_streak` 按"**逐维**、连续含候选窗数"原样重建
        # （每睡眠窗：该维有候选→+1；`reached_threshold`→清零；缺失→0）
        cand_reached: dict = {}
        for rec in records:
            p = rec.get("payload") or {}
            if rec.get("type") == "PERSONA_DRIFT_CANDIDATE" and p.get("agent_id") == self.agent_id:
                cand_reached[(p.get("window"), p.get("dim"))] = bool(p.get("reached_threshold"))
        if slept or cand_reached:
            streak: dict = {}
            for w in sorted(slept):
                for dim in PD.BIG5_DIMS:
                    key = (w, dim)
                    if key in cand_reached:
                        streak[dim] = streak.get(dim, 0) + 1
                        if cand_reached[key]:
                            streak[dim] = 0
                    else:
                        streak[dim] = 0
            self._drift_streak = streak
        # observed: engine-authoritative OBSERVATION set ∪ this agent's MEMORY_WRITE sources
        obs = set(a.get("observed_event_seqs", []))
        for rec in records:
            if rec.get("type") == "MEMORY_WRITE" and (rec.get("payload") or {}).get("agent_id") == self.agent_id:
                s = (rec["payload"] or {}).get("source_event_seq")
                if s is not None:
                    obs.add(s)
        self._observed_seqs = obs
        # needs (own NEED_UPDATE folded into engine agent state)
        self.needs = {d: int(a.get("needs", {}).get(d, self.needs.get(d, 50))) for d in C.NEED_DIMS}
        # schedule -> _plan_slots (planner re-reads this; avoids re-planning drift)
        self._plan_slots = {}
        for s in a.get("schedule", []) or []:
            sid = s.get("slot_id")
            if not sid:
                continue
            e = {"activity_type": s.get("activity_type"), "place": s.get("place")}
            for k in ("template_id", "participants"):
                if k in s:
                    e[k] = s[k]
            self._plan_slots[sid] = e
        # week caches + dialogue/narrative dedup (else resume re-emits events)
        W = (C.TIME_CONFIG["DAYS_PER_WEEK"] * len(C.TIME_CONFIG["SLOTS_PER_DAY"])
             * C.TIME_CONFIG["ROUNDS_PER_SLOT"])
        planned: set[int] = set()
        goals_weeks: set[int] = set()
        narrated: set[int] = set()
        accepted: set = set()
        judged: set = set()
        appraised: set = set()
        comm_round = None   # _comm_slot 按"是否**尝试**过对话"定（被拒的尝试不留 MSG_*）
        _slot_names = C.TIME_CONFIG["SLOTS_PER_DAY"]
        _rps = C.TIME_CONFIG["ROUNDS_PER_SLOT"]
        _dow = C.TIME_CONFIG.get("DAYS_PER_WEEK", 7)

        def _slot_of(rr: int) -> str:
            per_day = len(_slot_names) * _rps
            return f"day{(rr // per_day) % _dow}-{_slot_names[(rr % per_day) // _rps]}"

        rel: dict = {}
        # D2：线程化状态的**前向重建**（否则续跑会在同一 slot 重复发消息 / 重复接同一轮，
        # 破坏 T276「续跑与一次性跑逐字节一致」）。纯读日志、确定性。
        slot_msgs: dict = {}
        thread_replied: dict = {}
        replied_uids: set = set()   # D2 P2：我曾回复过的消息 msg_uid（防续跑重复回同一条）
        replied_uids: set = set()   # P2：我回复过的 msg_uid（否则续跑会对同一条再回一次 ⇒ DROPPED{dup}）
        for rec in records:
            t = rec.get("type")
            p = rec.get("payload") or {}
            r = int(rec.get("round", 0))
            if t == "SCHEDULE_PLANNED" and p.get("agent_id") == self.agent_id:
                planned.add(r // W)
            elif t == "GOAL_SET" and (p.get("agent_id") == self.agent_id or rec.get("actor") == self.agent_id):
                goals_weeks.add(r // W)
            elif t in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
                who = p.get("from") or p.get("author") or rec.get("actor")
                if who == self.agent_id:
                    if comm_round is None or r >= comm_round:
                        comm_round = r
                    sid = _slot_of(r)
                    slot_msgs[sid] = slot_msgs.get(sid, 0) + 1
                    tid_ = p.get("thread_id")
                    ti_ = p.get("turn_index")
                    if tid_ and ti_ is not None:
                        thread_replied[tid_] = max(thread_replied.get(tid_, -1), int(ti_))
                    rt_ = p.get("reply_to")
                    if rt_:
                        replied_uids.add(rt_)
                    rt_ = p.get("reply_to")
                    if rt_:
                        replied_uids.add(rt_)
            elif t == "INTENT_REJECTED":
                # `_communicate` 在**尝试**时就置 `_comm_slot`（即使 SOCIAL 被拒、无 MSG_*）⇒
                # 被拒的对话尝试也必须算，否则续跑会**重复尝试**同一 slot（T298 cut=75）。
                if p.get("agent_id") == self.agent_id and p.get("intent_class") == "INTENT.SOCIAL":
                    if comm_round is None or r >= comm_round:
                        comm_round = r
            elif t == "NARRATIVE":
                br = p.get("body_ref") or ""
                if f"narrative/{self.agent_id}/" in br:
                    tail = br.rsplit("-", 1)[-1].split(".")[0]
                    if tail.isdigit():
                        narrated.add(int(tail))
            elif t == "OFFER_ACCEPTED":
                who = p.get("by") or p.get("accepter") or p.get("to")
                oid = p.get("offer_id")
                if oid and who == self.agent_id:
                    accepted.add(oid)
            elif t == "RELATION_CHANGE" and p.get("from") == self.agent_id:
                rel[(p.get("to"), p.get("dim"))] = p.get("after")
            elif t == "LLM_JUDGMENT" and (p.get("judgment_id") or "").startswith("J-"):
                # 去重集按 **jid 归属人**（`J-<owner>-<to>-<dim>-...`）计，而非"parties 含我"——
                # 否则会把**对方**的判定误记到我名下（实测：`J-P003-P001-affinity-weak-11`
                # 曾被错加进 P001 的 `_judged`，导致 P001 在 round22 漏判）。
                dim = p.get("dimension") or ""
                toks = (p.get("judgment_id") or "").split("-")
                if len(toks) < 5 or toks[1] != self.agent_id:
                    continue
                if dim.startswith("rel_") and len(toks) >= 6:
                    judged.add((toks[2], dim[4:], toks[4]))
                elif dim in ("stance", "respect", "affection"):
                    tail = toks[4]
                    if tail[:1] == "w" and tail[1:].isdigit():
                        appraised.add((toks[2], int(tail[1:])))
        self._planned_weeks = planned
        self._goals_set_weeks = goals_weeks
        self._narrated_weeks = narrated
        self._accepted = accepted
        self._judged = judged
        self._appraised = appraised
        self._comm_slot = _slot_of(comm_round) if comm_round is not None else None
        self._slot_msgs = dict(slot_msgs)
        self._thread_replied_turn = dict(thread_replied)
        self._replied_msg_ids = set(replied_uids)
        self._replied_msg_ids = set(replied_uids)
        self._rel_cache = rel
        # R6-T2：F-4 上下文机制的 rift 台账**前向重建**（同一条规则 `DR.ingest_one`；
        # 否则续跑会"忘记旧账"，与一次性跑不等价）。开关关闭时 `ingest_one` 立即返回。
        self._rifts = {}
        self._rifts_seen = set()
        _dr = DR.load_params()
        if _dr.get("enabled"):
            for rec in records:
                DR.ingest_one(self._rifts, self._rifts_seen, int(rec.get("seq", -1)),
                              rec.get("type"), rec.get("payload") or {},
                              int(rec.get("round", 0) or 0), self.agent_id, _dr)
            DR.prune(self._rifts, _dr, int(state.round))

    # ---- public entry ------------------------------------------------------
    def step(self) -> StepReport:
        wv = self.kernel.perceive(self.agent_id)          # IF-1 (read-only)
        rep = StepReport(round=wv.round)
        self._llm_permit = self._llm_ok(wv)               # T221c: M4 本回合 LLM 许可
        self.memory.sync_from_refs(wv.memory_refs)
        self._read_world_params(wv)     # T364：每回合读一次 WorldParams（消费点被读的计数证据）
        self._update_needs(wv)
        self._observe(wv, rep)
        retrieved_ids, _ = self._retrieve(wv)
        rep.retrieved = retrieved_ids
        rep.planned, rep.goals_set = self._plan(wv)
        rep.moved_to = self._act(wv)
        rep.reflected = self._reflect(wv, retrieved_ids)
        self._fold_relations(wv)
        rep.soft_judgments = self._maybe_soft_judge(wv)
        self._maybe_social_appraisal(wv)
        rep.narrated = self._maybe_narrate(wv)
        self._communicate(wv)
        self._maybe_negotiate(wv)
        self._maybe_accept_offers(wv)
        rep.slept = self._maybe_sleep_window(wv)
        return rep

    # ---- helpers -----------------------------------------------------------
    def _submit(self, intent: Intent, rep: StepReport) -> bool:
        res = self.kernel.submit_intent(self.agent_id, intent)
        if res.ok:
            rep.accepted.append(intent.intent_class)
        else:
            rep.rejected.append(f"{intent.intent_class}:{res.reason}")
        return res.ok

    def _update_needs(self, wv) -> None:
        for ev in wv.visible_events:
            if ev.type == "NEED_UPDATE" and ev.payload.get("agent_id") == self.agent_id:
                self.needs[ev.payload["dim"]] = int(ev.payload["after"])

    # 1. perceive ----------------------------------------------------------
    def _observe(self, wv, rep: StepReport) -> None:
        rep.perceived = len(wv.visible_events)
        observe_msg = True
        try:
            observe_msg = bool(DT.load_params()["observe"].get("msg_enabled", True))
        except Exception:
            observe_msg = True
        for ev in wv.visible_events:
            if ev.seq in self._observed_seqs or ev.type not in _SALIENT_EVENTS:
                continue
            if not observe_msg and ev.type in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
                continue  # D2 消融开关：对话措辞不进记忆（默认开；关闭=行为回到旧链路）
            self._observed_seqs.add(ev.seq)
            text = self._describe_event(ev)
            imp = self._score_importance(text, wv.round)
            payload = self.memory.prepare_write(
                kind="observation", text=text, importance=imp, day=wv.day, slot=wv.slot,
                tick=wv.round, subject=ev.actor if ev.actor != self.agent_id else None,
                refs=[str(ev.seq)], source_event_seq=ev.seq)
            if self._submit(Intent(INTENT_MEMORY, self.agent_id, payload), rep):
                self.memory.commit_write(payload)
                self._submit(Intent(INTENT_OBSERVE, self.agent_id,
                                    {"target_event_seq": ev.seq, "salience": imp}), rep)
                rep.observed += 1

    # 2. retrieve ----------------------------------------------------------
    def _retrieve(self, wv, query: str | None = None) -> tuple[list, dict]:
        if query is None:
            query = self._retrieval_query(wv)
        hits, debug = self.memory.score_and_rank(query, now_tick=wv.round)
        ids = [n.mem_id for n, _ in hits]
        scores = [round(s, 6) for _, s in hits]
        payload = {"op": "retrieve", "query_id": f"Q-{self.agent_id}-{wv.round}",
                   "top_k": debug["top_k"], "selected_mem_ids": ids, "scores": scores,
                   "weights": debug["weights"], "tie_order": debug["tie_order"],
                   "query_digest": self.embedding.version}
        # T228：检索降级标记（additive；字段名引用 freeze.side 单一来源，不另拼）
        try:
            from freeze.side import degradation_marker
            payload.update(degradation_marker(
                vec_available=debug.get("vec_available", True),
                retrieval_mode=debug.get("retrieval_mode", "vector")))
        except Exception:
            payload["vec_available"] = bool(debug.get("vec_available", True))
            payload["retrieval_mode"] = debug.get("retrieval_mode", "vector")
        if self._submit(Intent(INTENT_MEMORY, self.agent_id, payload), StepReport(wv.round)):
            self.memory.touch(ids, wv.round)
        return ids, debug

    def _retrieval_query(self, wv) -> str:
        recents = [n.text for n in list(self.memory.nodes.values())[-3:]]
        head = f"{self.persona.compressed_profile(self._current_goal())} {self._activity_for(wv)[0]}"
        return head + " " + " ".join(recents)

    # ---- M6 降级 gate（T221c）：默认关 = 行为不变 -------------------------------
    def _llm_ok(self, wv) -> bool:
        """M4：本回合该 agent 是否获准调用 LLM（`schedule_enabled` 时按 Kc 限流）。
        默认 True（未启用=行为不变）；异常偏保守（True，宁可多算不可静默少算）。"""
        try:
            return _degrade.llm_permit(wv)
        except Exception:
            return True

    def _judge_skip(self, wv, dimension: str, parties) -> bool:
        """M6 critical-only：该 judge 是否应跳过（M4 未许可 或 内核 critical-only 判跳）。
        内核已负责把跳过落成**可列** `DEGRADE`；life 只读布尔。默认 False=不跳。"""
        if not self._llm_ok(wv):
            return True
        try:
            return _degrade.should_skip_judgment(self.kernel, dimension, parties)
        except Exception:
            return False

    # 3. plan --------------------------------------------------------------
    def _plan(self, wv) -> tuple[bool, bool]:
        if wv.time.week in self._planned_weeks:
            return False, False
        focus = self._weekly_focus(wv)          # LLM-decided, frozen (T57)
        slots = self._weekly_slots(wv, focus)
        if self._llm_ok(wv):                     # T221c: M4 未许可 → 不调 LLM（计划本身确定性）
            self.llm.call("plan", self.persona.compressed_profile(self._current_goal()),
                          meta={"agent_id": self.agent_id, "round": wv.round})
        planned = self._submit(Intent(INTENT_PLAN, self.agent_id,
                                      {"horizon": "week", "week": wv.time.week, "slots": slots}),
                               StepReport(wv.round))
        if planned:
            self._planned_weeks.add(wv.time.week)
        goals_set = False
        if wv.time.week not in self._goals_set_weeks:
            goals = [g.as_dict() for g in G.initial_goals(self.agent_id, self.persona)]
            if self._submit(Intent(INTENT_GOAL, self.agent_id, {"op": "set", "goals": goals}),
                            StepReport(wv.round)):
                self._goals_set_weeks.add(wv.time.week)
                goals_set = True
        return planned, goals_set

    def _weekly_focus(self, wv) -> str:
        """LLM decides the week's focus from a small option set; the choice is FROZEN
        (LLM_JUDGMENT) so the resulting plan stays replay-stable, yet differs between
        mock and a real LLM (T57: LLM output drives structure)."""
        from .planner import FOCUS_OPTIONS
        mode = m2b_judge_mode()
        # M2b 判别式：候选含逃生项（单一真源 JUDGMENT_OPTIONS）；关闭时用旧 FOCUS_OPTIONS（逐项一致）
        options = list(C.JUDGMENT_OPTIONS["weekly_focus"]) if mode == "discriminative" \
            else list(FOCUS_OPTIONS)
        branch = rng_branch(self.agent_id, "weekly_focus", "self", wv.time.week, options)
        envelope = {"options": options}
        jid = f"JF-{self.agent_id}-{wv.time.week}"
        if self._judge_skip(wv, "weekly_focus", [self.agent_id]):
            return str(branch)               # 降级：确定性 RNG 选择，不调 LLM
        try:
            payload, emitted = self.soft.judge(
                judgment_id=jid, dimension="weekly_focus", question_ref="weekly_focus",
                envelope=envelope, rng_branch=branch, parties=[self.agent_id],
                context={"goal": self._current_goal(), "needs": dict(self.needs),
                         "memories": self.memory.summary_for_prompt(
                             list(self.memory.nodes)[-8:], 300)},
                round_no=wv.round, mode=mode)
        except Exception:
            return "balance"
        if not emitted:
            self._submit_audit("LLM_JUDGMENT", payload, phase=2)
        return str(payload.get("resolved", payload["decision"]))

    def _weekly_slots(self, wv, focus: str | None = None) -> list[dict]:
        """Weekly plan. Social/economy slots may carry a `template_id` (T49) chosen by
        the deterministic `Planner`; other slots fall back to the base template."""
        from .planner import Planner
        templates = _templates(self.places)
        planner = Planner(self.agent_id, templates, self.peers, self.places)
        slots = []
        self._plan_slots = {}
        for dow in range(C.TIME_CONFIG["DAYS_PER_WEEK"]):
            day_type = C.TIME_CONFIG["DAY_TYPES"][dow]
            for si, slot in enumerate(C.TIME_CONFIG["SLOTS_PER_DAY"]):
                slot_id = f"day{dow}-{slot}"
                planned_tick = dow * 12 + si * C.TIME_CONFIG["ROUNDS_PER_SLOT"]
                chosen = planner.plan_slot(day_type, slot, slot_id, int(wv.cash), focus)
                extra: dict = {}
                if chosen:
                    atype, place = chosen["activity_type"], chosen["place"]
                    extra = {"template_id": chosen["template_id"],
                             "participants": chosen["participants"]}
                    self._plan_slots[slot_id] = {"activity_type": atype, "place": place,
                                                 "template_id": chosen["template_id"],
                                                 "participants": chosen["participants"]}
                else:
                    atype, place = self._choose_activity(day_type, slot)
                    self._plan_slots[slot_id] = {"activity_type": atype, "place": place}
                d = {"slot_id": slot_id, "activity_type": atype, "place": place,
                     "priority": 0.7, "planned_tick": planned_tick}
                d.update(extra)
                slots.append(d)
        return slots

    def _base_activity(self, day_type: str, slot: str) -> tuple[str, str]:
        if slot == "night":
            return ("rest", "residence")
        if slot == "morning":
            if day_type == "workday":
                wp = self._work_place_for(slot)
                return ("work", wp) if wp else ("self_care", "residence")
            return ("self_care", "residence")
        if slot == "afternoon":
            if day_type == "workday":
                wp = self._work_place_for(slot)
                return ("work", wp) if wp else ("socialize", "plaza")
            return ("socialize", "plaza")
        return ("socialize", "cafe") if day_type == "workday" else ("leisure", "park")

    def _valid(self, atype: str, place: str, slot: str) -> bool:
        spec = self.places.get(place, {})
        return slot in spec.get("open_slots", []) and atype in spec.get("affordances", [])

    def _work_place_for(self, slot: str) -> str | None:
        """A place that actually affords `work` and is open at `slot` (role's, else any)."""
        wp = self.persona.work_place
        if self._valid("work", wp, slot):
            return wp
        for cand in C.ACTIVITY_TO_PLACES["work"]:
            if self._valid("work", cand, slot):
                return cand
        return None

    def _choose_activity(self, day_type: str, slot: str) -> tuple[str, str]:
        """Deprivation-aware (06 §7.3): a need below θ_dep overrides the template."""
        base = self._base_activity(day_type, slot)
        if slot == "night":
            return base
        deprived = [d for d in C.NEED_DIMS if self.needs.get(d, 50) < C.THETA_DEP]
        if not deprived:
            return base
        dim = min(deprived, key=lambda d: (self.needs.get(d, 50), d))
        atype, place = _NEED_ACTIVITY[dim]
        if self._valid(atype, place, slot):
            return (atype, place)
        return base

    def _read_world_params(self, wv) -> None:
        """T364 / D3 口径②：经**端口**读 `WorldParams`（不直读盘）；仅本回合缓存 + 计数。

        形状（与 `engine/world_params.py` / `KernelAdapter.world_params(round)` 对齐）：
        `{"activity_weight": {place:int}, "resource_factor_bp": {..}, "market_scarcity_bp": {..}, "active": [..]}`。
        端口缺失（如 mini 内核）⇒ 不读、行为不变。
        """
        fn = getattr(self.kernel, "world_params", None)
        if not callable(fn):
            return
        try:
            self._wp_last = fn(wv.round)
        except Exception:
            self._wp_last = None
            return
        self._wp_reads += 1
        wp = self._wp_last or {}
        if (wp.get("activity_weight") or wp.get("resource_factor_bp")
                or wp.get("market_scarcity_bp") or wp.get("active")):
            self._wp_nonempty += 1

    def _activity_for(self, wv) -> tuple[str, str]:
        slot_id = f"day{wv.time.day_of_week}-{wv.time.slot}"
        entry = self._plan_slots.get(slot_id)
        if entry:
            atype, place = entry["activity_type"], entry["place"]
        else:
            atype, place = self._base_activity(wv.time.day_type, wv.time.slot)
        # T364 / D3 口径②：消费 `world_params.activity_weight`（只对未来 [start,end)、dose/空 恒等）：
        # 本 slot 内**倾向高权重 place**（如节日 hall），但**仅当该 place 对当前活动合法** ⇒ 有界。
        wp = getattr(self, "_wp_last", None) or {}
        aw = wp.get("activity_weight") or {}
        cands = [p for p, w in aw.items() if int(w) > 0 and self._valid(atype, p, wv.time.slot)]
        if cands:
            chosen = min(cands, key=lambda p: (-int(aw[p]), p))
            if chosen != place:
                self._wp_changed_choice += 1   # ③ 实际改变了选择（纯观测计数）
                place = chosen
        return atype, place

    # 4. act ---------------------------------------------------------------
    def _act(self, wv) -> str | None:
        atype, place = self._activity_for(wv)
        if wv.location == place:
            return None
        # T354 期②（life 消费，**有界去重门**）：若**本地**已有"同活动进行中"，则不重复发起移动；
        # 跨地/换活动照常 ⇒ 天然有界（换 slot 目标变即放行），与 travel 时长无关。
        ca = getattr(wv, "current_activity", None)
        if ca is not None:
            cap = ca.get("place") if isinstance(ca, dict) else getattr(ca, "place", None)
            cat = ca.get("activity_type") if isinstance(ca, dict) else getattr(ca, "activity_type", None)
            if cap == wv.location and cat == atype:
                return None
        slot_id = f"day{wv.time.day_of_week}-{wv.time.slot}"
        res = self.kernel.submit_intent(self.agent_id, Intent(
            INTENT_MOVE, self.agent_id, {"to_place": place, "slot_id": slot_id,
                                         "activity_type": atype}))
        return place if res.ok else None

    # 5. reflect -----------------------------------------------------------
    def _reflect(self, wv, retrieved_ids: list) -> bool:
        force_weekly = C.week_phase(
            {"day_of_week": wv.time.day_of_week, "slot": wv.time.slot}) == "REVIEW"
        if not self.memory.reflection_due(wv.time.week, force_weekly):
            return False
        if not self._llm_ok(wv):                     # T221c: M4 未许可 → 跳过反思 LLM
            return False
        src_ids, imp_sum = self.memory.take_reflection_input()
        prompt = self.persona.compressed_profile(self._current_goal()) + "\n" + \
            self.memory.summary_for_prompt(src_ids or retrieved_ids)
        text = self.llm.call("reflect", prompt,
                             meta={"agent_id": self.agent_id, "round": wv.round}).text
        produced = []
        for i in range(3):
            payload = self.memory.prepare_write(
                kind="reflection", text=f"{text}（insight {i + 1}）", importance=min(10, 6 + i),
                day=wv.day, slot=wv.slot, tick=wv.round, refs=list(src_ids))
            if self._submit(Intent(INTENT_MEMORY, self.agent_id, payload), StepReport(wv.round)):
                self.memory.commit_write(payload)
                produced.append(payload["mem_id"])
        if produced:
            self._submit(Intent(INTENT_MEMORY, self.agent_id, {
                "op": "reflect", "triggered_by_mem_ids": src_ids, "importance_sum": imp_sum,
                "produced_mem_id": produced[0], "produced_mem_ids": produced}), StepReport(wv.round))
            self.memory.note_reflection(wv.time.week)
            return True
        return False

    # ---- soft judgment (F) & narrative (N) --------------------------------
    def _fold_relations(self, wv) -> None:
        for ev in wv.visible_events:
            if ev.type == "RELATION_CHANGE" and ev.payload.get("from") == self.agent_id:
                to = ev.payload.get("to")
                if to:
                    self._rel_cache[(to, ev.payload["dim"])] = int(ev.payload["after"])

    def _submit_audit(self, kind: str, payload: dict, phase: int) -> None:
        fn = getattr(self.kernel, "submit_audit", None)
        if fn is not None:  # mini test-double path; the freeze layer emits on its own
            fn(kind, payload, actor=self.agent_id, phase=phase)

    def _maybe_soft_judge(self, wv) -> int:
        n = 0
        mode = m2b_judge_mode()
        for (to, dim), after in list(self._rel_cache.items()):
            if dim not in ("affinity", "trust", "respect", "familiarity"):
                continue
            level = "strong" if abs(after) >= C.EPS_STRONG else ("weak" if abs(after) >= C.EPS else None)
            if level is None or (to, dim, level) in self._judged:
                continue
            self._judged.add((to, dim, level))
            envelope = R.soft_judgment_envelope(dim, 0, after)
            if mode == "discriminative":  # M2b: 候选含逃生项（单一真源）
                envelope = {**envelope, "options": list(C.JUDGMENT_OPTIONS[f"rel_{dim}"])}
            branch = rng_branch(self.agent_id, dim, to, wv.round, envelope["options"])
            jid = f"J-{self.agent_id}-{to}-{dim}-{level}-{wv.round}"
            if self._judge_skip(wv, f"rel_{dim}", [self.agent_id, to]):
                continue
            payload, emitted = self.soft.judge(
                judgment_id=jid, dimension=f"rel_{dim}", question_ref="rel_relation_quality",
                envelope=envelope, rng_branch=branch, parties=[self.agent_id, to],
                context={"dim": dim, "to": to, "after": after}, round_no=wv.round, mode=mode)
            if not emitted:
                self._submit_audit("LLM_JUDGMENT", payload, phase=2)
            # numeric consequence from the FROZEN label (deterministic, D-12);
            # M2b 逃生项命中时用确定性兜底值 resolved（decision 保留模型原话）
            for d, dv in R.delta_from_frozen_label(
                    payload.get("resolved", payload["decision"])).items():
                before = int(self._rel_cache.get((to, d), 0))
                lo, hi = C.RELATION_RANGE[d]
                self.kernel.submit_intent(self.agent_id, Intent(INTENT_RELATION, self.agent_id, {
                    "to": to, "dim": d, "before": before,
                    "after": clamp(before + dv, lo, hi), "cause": "soft_judgment"}))
            n += 1
        return n

    def _maybe_social_appraisal(self, wv) -> int:
        """T127: emit frozen LLM_JUDGMENT for two extra social dimensions that light
        up the `rel-acceptance` (stance flip) and `diff-scoring` (respect/affection
        divergence) cards. Same frozen path as the relation judgments: RNG picks the
        branch, the LLM fills the label, the decision is frozen into the log (replay
        reads it back, never re-calls). One appraisal per (peer, week), bounded."""
        week = wv.time.week
        peers = sorted({to for (to, _dim) in self._rel_cache})[:4]
        n = 0
        mode = m2b_judge_mode()
        for to in peers:
            key = (to, week)
            if key in self._appraised:
                continue
            self._appraised.add(key)
            for dim, opts in (("stance", ["accept", "reject"]),
                              ("respect", ["high", "low"]),
                              ("affection", ["high", "low"])):
                if mode == "discriminative":  # M2b: 候选含逃生项（单一真源）
                    opts = list(C.JUDGMENT_OPTIONS[dim])
                branch = rng_branch(self.agent_id, dim, to, wv.round, opts)
                envelope = {"options": list(opts)}
                jid = f"J-{self.agent_id}-{to}-{dim}-w{week}"
                if self._judge_skip(wv, dim, [self.agent_id, to]):
                    continue
                payload, emitted = self.soft.judge(
                    judgment_id=jid, dimension=dim, question_ref=f"social_{dim}",
                    envelope=envelope, rng_branch=branch, parties=[self.agent_id, to],
                    context={"dim": dim, "to": to}, round_no=wv.round, mode=mode)
                if not emitted:
                    self._submit_audit("LLM_JUDGMENT", payload, phase=2)
                n += 1
        return n

    def _maybe_narrate(self, wv) -> bool:
        phase = C.week_phase({"day_of_week": wv.time.day_of_week, "slot": wv.time.slot})
        if phase != "REVIEW" or wv.time.week in self._narrated_weeks:
            return False
        if not self._llm_ok(wv):                     # T221c: M4 未许可 → 跳过叙事 LLM
            return False
        self._narrated_weeks.add(wv.time.week)
        seqs = [ev.seq for ev in wv.visible_events][-20:]
        nid = f"N-{self.agent_id}-{wv.time.week}"
        body_ref = SideStore.narrative_ref(self.agent_id, nid)
        payload, emitted, text = self.soft.narrate(
            narrative_id=nid, fact_event_seqs=seqs,
            body_ref=body_ref, round_no=wv.round)
        # T234: 写入叙事正文到 side（IF-7 body_ref 的 writer）；开关关时不写。
        if emitted and text and narrative_persist_enabled():
            self.side_store.write_narrative(self.agent_id, nid, text)
        if not emitted:
            self._submit_audit("NARRATIVE", payload, phase=6)
        return True

    # ---- M6 dialogue / public / group (T98) + D2 线程化 ---------------------
    def _dlg_cfg(self) -> dict:
        try:
            return DT.load_params()["dialogue"]
        except Exception:
            return dict(DT.DEFAULTS)

    def _name(self, pid: str, cfg: dict | None = None) -> str:
        """提示词里的称呼：优先显示名，关闭开关则回退 persona_id（保证非空、无裸 ID 断链）。"""
        cfg = cfg or self._dlg_cfg()
        if not cfg.get("names_enabled", True):
            return pid
        return self._peer_names.get(pid) or pid

    def _comm_limits(self, wv) -> None:
        if self._round_marker != wv.round:
            self._round_marker = int(wv.round)
            self._round_replies = 0
            self._pub_k = 0

    def _communicate(self, wv) -> None:
        """D2：先看「是否有该我接的话」，有就接着往下说（多轮往复）；否则按计划发起一段新对话。

        措辞由 LLM 生成后**冻结进 MSG_* 事件**（重放直接读 body，不重调模型）；
        结构字段（thread_id/turn_index/reply_to/participants/ctx）由本处决定、内核落盘。
        上限：单 slot 最多 `max_messages_per_slot` 条；单回合回复 ≤ `max_turns_per_round`；
        单线程 ≤ `max_turns` 轮（到顶封口）。**不含任何世界态/数值后果。**
        """
        if not social_enabled():          # T115: whole social-voice channel off
            return
        if not self._llm_ok(wv):          # T221c: M4 未许可 → 不发对话 LLM
            return
        self._comm_limits(wv)
        cfg = self._dlg_cfg()
        dr = DR.load_params()
        if dr.get("enabled"):                 # R6-T2：先吸收可见消息 → 更新 rift 台账（只读）
            DR.ingest(self._rifts, self._rifts_seen, wv.visible_events,
                      self.agent_id, dr, wv.round)
        slot_id = f"day{wv.time.day_of_week}-{wv.time.slot}"
        if int(self._slot_msgs.get(slot_id, 0)) >= int(cfg.get("max_messages_per_slot", 2)):
            return
        if cfg.get("enabled", True):
            prefer = set()
            if dr.get("enabled") and dr.get("reply_priority"):
                prefer = DR.threads_with_open_rift(self._rifts)   # 有旧账的线程优先接话
            target = self._pick_reply_target(wv, cfg, prefer_threads=prefer)
            if target is not None and self._send_reply(wv, target, cfg, slot_id):
                return
        if self._initiate(wv, cfg, slot_id):
            return
        # 同场偶遇搭话臂（默认 OFF ⇒ 直接返回 False，事件流与接入前一致）：
        # 只有「本 slot 没有模板对话」这个空档才会走到这里。
        self._initiate_encounter(wv, cfg, slot_id)

    def _thread_max_turn(self, wv, tid: str) -> int:
        """线程内「已存在的最大 turn_index」（按可见事件；无则 -1）。多方可同时处于同一 turn。"""
        mx = -1
        # R41：开启时把「公开消息」也算进线程轮数（关闭 ⇒ 白名单与接入前逐字节一致）
        types = ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC") if PT.enabled() else ("MSG_DM", "MSG_GROUP")
        for ev in wv.visible_events:
            if ev.type not in types:
                continue
            p = ev.payload or {}
            if p.get("thread_id") != tid:
                continue
            t = p.get("turn_index")
            if t is not None:
                mx = max(mx, int(t))
        return mx

    # ---- 入站 → 回复 -------------------------------------------------------
    def _pick_reply_target(self, wv, cfg, prefer_threads=frozenset()):
        """从可见事件里挑一条「对我说、尚未回、未超时、未到轮数顶」的消息。

        确定性：按 seq 倒序遍历（最近优先），取第一条满足全部条件的；无则 None。
        `prefer_threads`（R6-T2）：这些线程里有「未了结的不愉快」⇒ **优先**接话；
        仍是同一套硬条件（可见/未超时/未到轮数顶/未重复回），只改**挑选顺序**，
        目的是提高「误会→和解」在自然语言里真正发生的机会，不造事件。
        """
        window = int(cfg.get("reply_window_rounds", 2))
        max_turns = int(cfg.get("max_turns", 6))
        fallback = None
        # R41 公开面接话臂（默认 OFF ⇒ 下面三行全是空/假，循环体走原路径）：
        pub_on = PT.enabled()
        co_present = self._co_present_peers(wv) if pub_on else []
        pub_slot = f"day{wv.time.day_of_week}-{wv.time.slot}"
        for ev in reversed(list(wv.visible_events)):
            p = ev.payload or {}
            if pub_on and ev.type == "MSG_PUBLIC":
                # 四条有界条件见 life/public_talk.py：作者非我 / 在场者非空 / 同处 / 双配额
                if not PT.is_replyable_public(p, self.agent_id, wv.location, co_present):
                    continue
                if not PT.agent_quota_ok(self._slot_public_replies, pub_slot):
                    continue
                # R43：这里只是「省一次 LLM」的**预过滤**（判据/口径与写入口同一函数
                # `PT.place_quota_ok` → `PT.place_quota_gate`，键同为 day+slot+place）；
                # **裁决点**在写入口 `orchestration/integration.py::_do_social`，
                # 因为它才看得到本回合已放行的消息（本函数只有决策时点可见集）。
                # R44：这里的预过滤按**接话桶**判（`kind="reply"`），与写入口
                # `integration._do_social` 的分桶口径一致；否则「开场白已满 2 条」会在决策侧
                # 就把接话全部挡掉，写入口的分桶永远用不上（改动退化为空转）。
                if not PT.place_quota_ok(wv.visible_events, PT.place_of(p), pub_slot,
                                         day=wv.time.day, kind="reply"):
                    continue
            else:
                if ev.type not in ("MSG_DM", "MSG_GROUP"):
                    continue
                if not DT.is_replyable(ev.type, p, self.agent_id):
                    continue
            tid = p.get("thread_id")
            if not tid:
                continue                      # 旧格式（无线程字段）不接话：保持向后兼容
            max_turn = self._thread_max_turn(wv, tid)
            if max_turn + 1 >= max_turns:
                continue                      # 线程到顶，封口
            if int(wv.round) - int(ev.round) > window:
                continue                      # 超时，线程结束
            if int(self._thread_replied_turn.get(tid, -1)) >= max_turn:
                continue                      # 线程最新一轮我已经接过
            mid = p.get("msg_uid") or p.get("msg_id")   # D2：优先用全局唯一 msg_uid 去重
            if mid and mid in self._replied_msg_ids:
                continue
            if self._round_replies >= int(cfg.get("max_turns_per_round", 2)):
                continue                      # K 上限（单回合最多推进 K 轮）
            if prefer_threads and tid in prefer_threads:
                return ev                     # 有旧账的线程：立刻接
            if fallback is None:
                fallback = ev
        return fallback

    def _thread_history(self, wv, tid: str, cfg) -> list:
        """同线程最近 `history_turns` 条（(说话人名字, body)），文本总长受 `max_thread_chars` 限。"""
        rows = []
        # R41：开启时线程历史里包含公开消息（关闭 ⇒ 白名单与接入前逐字节一致）
        types = ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC") if PT.enabled() else ("MSG_DM", "MSG_GROUP")
        for ev in wv.visible_events:
            if ev.type not in types:
                continue
            p = ev.payload or {}
            if p.get("thread_id") != tid:
                continue
            rows.append((p.get("from") or "?", (p.get("body") or "").strip()))
        rows = rows[-int(cfg.get("history_turns", 3)):]
        budget = int(cfg.get("max_thread_chars", 240))
        out = []
        for who, body in rows:
            line = f"{self._name(who, cfg)}：{body}"
            if sum(len(x[1]) for x in out) + len(body) > budget:
                break
            out.append((who, line))
        return out

    def _ctx_snapshot(self, partner: str | None, topic: str | None,
                      trigger: str | None = None, initiator: str | None = None,
                      echo: dict | None = None,
                      breadth: dict | None = None) -> dict:
        """生成时的语境快照（体积控：只存被引用的键；缺的键省略而非填假值）。

        `trigger`/`initiator` 记录「这段对话怎么起的、谁先开口」——下一阶段做「生活气息」
        （非功能闲聊、串门偶遇触发）时直接可用，不必重做字段。
        """
        rel = 0
        if partner:
            rel = int(self._rel_cache.get((partner, "affinity"), 0))
        ctx = {"relation": rel, "mood": DT.mood_label(self.needs),
               "need": DT.scarcest_need(self.needs), "topic": topic}
        if getattr(self, "_mem_refs", None):
            # F-6 审计（additive）：本条消息生成时提示词里实际注入了哪些跨天记忆
            # （可回 run.jsonl 的 MEMORY_WRITE 事件按 mem_id 还原其 day/slot/text）。
            # OFF 臂 `_mem_refs` 恒为空 ⇒ 该键不出现 ⇒ payload 与 A0 逐字节一致。
            ctx["memory_refs"] = list(self._mem_refs)
        if trigger:
            ctx["trigger"] = trigger
        if initiator:
            ctx["initiator"] = initiator
        if AR.enabled():
            # R12 去重臂审计（additive）：本条生成时去重机制的累计行为。
            # 默认 OFF ⇒ 该键不出现 ⇒ payload 与接入前逐字节一致。
            ctx["dequp"] = AR.audit()
        if L7S.enabled():
            # L-7 结构臂审计（additive）：本条生成前实际下发的结构约束。
            # 关闭（LIFE_PROMPT_L7_STRUCT=0）⇒ `_l7s` 为 None ⇒ 该键不出现。
            _l7a = L7S.audit(getattr(self, "_l7s", None))
            if _l7a is not None:
                ctx["l7struct"] = _l7a
        if echo is not None:
            # F-3 审计（additive）：本条回复接的是谁的哪种情绪、多强（确定性推导，可复算）。
            # 默认 OFF / 不产 ⇒ 该键不出现 ⇒ payload 与接入前逐字节一致。
            # 刻意放进已透传的 `ctx`（`orchestration/integration.py::_thread_fields` 有白名单，
            # 顶层新键会被静默吞掉；`ctx` 已整体透传，与 memory_refs/dequp 同一先例）。
            ctx["echo"] = echo
        if TB.enabled() and breadth is not None:
            # R19 话题宽度臂审计（additive）：本条生成前下发了哪个相邻话题、正文是否真的落地。
            # 关闭（LIFE_PROMPT_TOPIC_BREADTH 未设）⇒ breadth 恒 None ⇒ 该键不出现。
            ctx["topic_breadth"] = breadth
        if SA.enabled() and getattr(self, "_scene", None) is not None:
            # 处境锚臂审计（additive）：本条生成时提示词里实际下发的那一行处境
            # （时段/场所 id/活动 id + 该行 sha256）。关闭（LIFE_PROMPT_SCENE 未设）⇒
            # `_scene` 恒 None ⇒ 该键不出现 ⇒ payload 与接入前逐字节一致。
            ctx["scene"] = self._scene
        if WX.enabled() and getattr(self, "_weather", None) is not None:
            # 天气臂审计（additive）：本条生成时提示词里实际下发的那一行「今儿天怎么样」
            # （weather/season/day/seed + 该行 sha256）。关闭（HITT_WEATHER 未设）⇒
            # `_weather` 恒 None ⇒ 该键不出现 ⇒ payload 与接入前逐字节一致。
            ctx["weather"] = self._weather
        return ctx

    def _dequp_body(self, prompt: str, body: str, meta: dict) -> str:
        """R12 去重臂：新台词与最近窗口内的台词撞 8-gram ⇒ **一次性**重生成。

        默认 OFF ⇒ `AR.collide()` 恒 None、`AR.remember()` 不记账，本方法等于
        `return body`（零额外 LLM 调用、提示词与 payload 与接入前一致）。
        开启时最多多花 1 次 `purpose="dialogue"` 调用（有界，不级联）。

        L-7 结构臂（`LIFE_PROMPT_L7_STRUCT`，默认 ON）优先接管：约束已经在
        `_dialogue_prompt` / `_reply_prompt` 里**生成前**下发，这里**不再重试**
        （零额外 LLM 调用，也不留任何进程级状态 ⇒ 同 seed 两次跑逐字节一致）。
        """
        if L7S.enabled():
            return body
        hit = AR.collide(body)
        if hit is None:
            AR.remember(body)
            return body
        AR.note_retry()
        res = self.llm.call("dialogue", prompt + AR.retry_suffix(hit),
                            meta={**meta, "dequp_retry": 1})
        out = (res.text or "").strip() or body
        AR.remember(out)
        return out

    def _emotion_echo(self, ctx_in: dict | None, partner_body: str | None,
                      partner: str | None) -> tuple[str | None, dict | None]:
        """F-3 情绪呼应：判定「对方此刻的情绪」并给出**一句处境提示**（+ 审计字段）。

        单变量约束（沿用 `_gossip_hint` / `_memory_line` 的开关先例）：
          - 开关关闭（`config/emotion_echo.json::enabled=false` 且未设 env，**默认**）
            ⇒ 直接返回 `(None, None)`：提示词不加任何字、payload 不加任何键，逐字节不变；
          - 打开 ⇒ 只在提示词中**插入**这一段，并**只追加** `ctx.echo` 审计键
            （`ctx` 是 `orchestration/integration.py::_thread_fields` 已整体透传的段，
            与既有 `ctx.memory_refs` / `ctx.dequp` 同一先例）。
        判定与强度全部由 `life/emotion_echo.py` 的纯函数推导（**不调用 LLM**）：
        语面极性复用 `life/emotion.emotion_sign`（单一真源），处境情绪取入站消息
        `payload["ctx"]["mood"]`（发送方生成时按自身 needs 算出的确定性标签）。
        """
        if not EE.enabled():
            return None, None
        plan = EE.plan((ctx_in or {}).get("mood"), partner_body or "")
        if plan is None:
            return None, None
        name = self._name(partner) if partner else None
        return EE.prompt_line(plan, name), EE.audit(plan)

    def _send_reply(self, wv, ev, cfg, slot_id: str) -> bool:
        p = ev.payload or {}
        tid = p["thread_id"]
        turn = self._thread_max_turn(wv, tid) + 1
        partner = p.get("from") or p.get("author")   # R41：公开消息的作者字段是 author 而非 from
        parts = [x for x in (p.get("participants") or [partner, p.get("to")]) if x]
        if self.agent_id not in parts:
            parts.append(self.agent_id)
        ctx_in = p.get("ctx") or {}
        topic = ctx_in.get("topic") or (p.get("tag_hints") or [None])[0] or "闲聊"
        history = self._thread_history(wv, tid, cfg)
        dr_cfg = DR.load_params()
        rift_line = None
        repair_line = None
        if dr_cfg.get("enabled"):
            rift_line = DR.context_line(self._rifts, partner, int(wv.round),
                                        name=self._name(partner) if partner else None,
                                        params=dr_cfg)
            # R13 / F-4：本线程确有未了结旧账 ⇒ 追加「这一句把话说开」的动作要求（只提要求，不给句式）
            repair_line = DR.repair_ask(self._rifts, tid, partner, int(wv.round), dr_cfg)
        # F-3：接住对方情绪（默认 OFF ⇒ (None, None)，下面两处都退化为"什么都不加"）
        echo_line, echo_audit = self._emotion_echo(ctx_in, p.get("body"), partner)
        prompt = self._reply_prompt(partner, topic, history, cfg, rift_line=rift_line,
                                    repair_line=repair_line, echo_line=echo_line, wv=wv,
                                    turn=turn, tid=tid)
        meta = {"agent_id": self.agent_id, "round": wv.round,
                "thread": tid, "turn": turn}
        res = self.llm.call("dialogue", prompt, meta=meta)
        body = (res.text or "").strip()
        if not body:
            return False
        body = self._dequp_body(prompt, body, meta)   # R12：撞车一次性重生成（默认OFF ⇒ 原样返回）
        # R19 话题宽度臂：**内容门控**——正文真的落到岔入话题才追加第二个 tag（OFF ⇒ 恒 None）
        tb_tag = self._topic_shift_tag(body)
        tb_audit = TB.audit(getattr(self, "_tb", None), bool(tb_tag)) if TB.enabled() else None
        payload: dict = {
            # R41：回公开消息必须落回 `global`（否则会被投成 place_group，错频道）；
            # 默认 OFF ⇒ 下面的条件恒假 ⇒ 该表达式与接入前逐字节等价。
            "scope": (PT.reply_scope(ev.type) if (PT.enabled() and ev.type == "MSG_PUBLIC")
                      else ("private" if ev.type == "MSG_DM" else "place_group")),
            "body": body, "refs": [],
            "tag_hints": list(p.get("tag_hints") or []) + ([tb_tag] if tb_tag else []),
            "thread_id": tid, "turn_index": turn,
            "reply_to": p.get("msg_uid") or p.get("msg_id"),   # D2：指针指向 msg_uid（全局唯一）
            "participants": sorted(set(parts)), "topic": topic,
            "ctx": self._ctx_snapshot(partner, topic, trigger="reply",
                                      initiator=DT.thread_initiator(tid),
                                      echo=echo_audit,   # F-3：OFF/不产 ⇒ None ⇒ 不多键
                                      breadth=tb_audit),
        }
        if dr_cfg.get("enabled"):
            # R6-T2：**只做追溯**（本条生成时我有哪些未了结旧账）；无旧账 ⇒ 不产生该键
            f = DR.audit_fields(self._rifts, int(wv.round), "reply", peers=[partner])
            if f is not None:
                f["prompted"] = bool(rift_line)
                payload["dialogue_rift"] = f
            # R13 / F-4：本线程旧账的**可审计**配对（rift_id + trigger_seq；本条事件的 seq 由日志自带）
            ra = DR.repair_audit(self._rifts, tid, partner, int(wv.round), bool(repair_line))
            if ra is not None:
                payload["dialogue_repair"] = ra
        if ev.type == "MSG_DM":
            payload["to"] = partner
        elif ev.type == "MSG_GROUP":
            payload["group_id"] = p.get("group_id")
        elif PT.enabled() and ev.type == "MSG_PUBLIC":
            # R41：只追加的审计键（关闭/不产时该键不出现 ⇒ payload 与接入前逐字节一致）
            payload["ctx"]["public_reply"] = PT.audit(
                ev.type, self._co_present_peers(wv), PT.place_of(p))
            self._slot_public_replies[slot_id] = \
                int(self._slot_public_replies.get(slot_id, 0)) + 1
        self._round_replies += 1
        self._thread_replied_turn[tid] = turn
        mid = p.get("msg_uid") or p.get("msg_id")
        if mid:
            self._replied_msg_ids.add(mid)
        self._slot_msgs[slot_id] = int(self._slot_msgs.get(slot_id, 0)) + 1
        self._comm_slot = slot_id
        self.kernel.submit_intent(self.agent_id, Intent(INTENT_SOCIAL, self.agent_id, payload))
        return True

    # ---- 发起一段新对话 ----------------------------------------------------
    def _initiate(self, wv, cfg, slot_id: str) -> bool:
        """按周计划里的模板发起一段新对话。**返回是否真的发了**（供偶遇臂判空档）。

        无 `template_id` ⇒ 返回 False（不造事件）。返回值是本轮唯一新增语义：
        OFF 臂下调用方只看它是否 True/False，事件流与接入前逐字节一致。
        """
        entry = self._plan_slots.get(slot_id)
        if not entry or not entry.get("template_id"):
            return False
        tid = entry["template_id"]
        parts = list(entry.get("participants") or [self.agent_id])
        partners = [p for p in parts if p != self.agent_id]
        scope, to, gid = "global", None, None
        if tid in _DM_TEMPLATES and partners:
            scope, to = "private", partners[0]
        elif tid in _GROUP_TEMPLATES and len(parts) >= 3:
            scope, gid = "place_group", f"place:{entry['place']}"
        elif tid in _PUBLIC_TEMPLATES:
            scope = "global"
        elif partners:
            scope, to = "private", partners[0]
        dr_cfg = DR.load_params()
        rift_line = None
        if dr_cfg.get("enabled") and to:
            rift_line = DR.context_line(self._rifts, to, int(wv.round),
                                        name=self._name(to), params=dr_cfg)
        prompt = self._dialogue_prompt(tid, parts, cfg, rift_line=rift_line, wv=wv)
        meta = {"agent_id": self.agent_id, "round": wv.round, "template": tid}
        res = self.llm.call("dialogue", prompt, meta=meta)
        body = (res.text or "").strip()
        if not body:
            return False
        body = self._dequp_body(prompt, body, meta)   # R12：撞车一次性重生成（默认OFF ⇒ 原样返回）
        payload: dict = {"scope": scope, "body": body, "refs": [], "tag_hints": [tid]}
        if to:
            payload["to"] = to
        if gid:
            payload["group_id"] = gid
        if dr_cfg.get("enabled") and to:
            f = DR.audit_fields(self._rifts, int(wv.round), "initiate", peers=[to])
            if f is not None:
                f["prompted"] = bool(rift_line)
                payload["dialogue_rift"] = f
        if cfg.get("enabled", True):
            # D2：线程起点（turn_index=0, reply_to=None）；topic 用模板 id（稳定字符串）
            if scope == "private" and to:
                thread_id = DT.thread_id_dm(self.agent_id, to, wv.round)
            elif scope == "place_group" and gid:
                thread_id = DT.thread_id_group(self.agent_id, gid, wv.round)
            else:
                thread_id = DT.thread_id_public(self.agent_id, wv.round, self._pub_k)
                self._pub_k += 1
            payload.update({"thread_id": thread_id, "turn_index": 0, "reply_to": None,
                            "participants": sorted(set(parts)), "topic": tid,
                            "ctx": self._ctx_snapshot(to, tid, trigger=tid,
                                                      initiator=self.agent_id)})
        self._slot_msgs[slot_id] = int(self._slot_msgs.get(slot_id, 0)) + 1
        self._comm_slot = slot_id
        self.kernel.submit_intent(self.agent_id, Intent(INTENT_SOCIAL, self.agent_id, payload))
        return True

    # ---- 同场偶遇搭话（encounter chat，默认 OFF）--------------------------
    def _co_present_peers(self, wv) -> list:
        """本 slot 里「和我站在同一处」的居民（**只读** place_local 可见事件，不新开真相源）。

        判据（唯一实现；与 `reports/02-dimension.md` 预登记口径一致）：
          取 `wv.visible_events` 中 `PLACE_ARRIVED` 且同时满足
            (i) `payload.place == wv.location`（同场所，**本人当前位置**为真源）；
            (ii) `payload.day == wv.time.day` 且 `payload.slot == wv.time.slot`（同时段，
                 缺字段时视为不约束——兼容不带 day/slot 的旧日志）；
            (iii) `payload.agent_id != self`（不含自己）。
          同一人多次出现**取并集**（集合语义，与事件到达序无关）。
        **不读 `ACTIVITY_STARTED.participants`**：那里含「联合活动」名单，会把
        「同活动」混进「同处」，与本臂要量的东西不是一件事（R23 §1.2 的副口径 `joint`
        同理，只作敏感性口径、不作主判据）。
        """
        me = self.agent_id
        peers = set()
        for ev in wv.visible_events:
            if ev.type != "PLACE_ARRIVED":
                continue
            p = ev.payload or {}
            who = p.get("agent_id")
            if not who or who == me:
                continue
            if p.get("place") != wv.location:
                continue
            if p.get("day") is not None and int(p["day"]) != int(wv.time.day):
                continue
            if p.get("slot") is not None and p["slot"] != wv.time.slot:
                continue
            peers.add(who)
        return sorted(peers)

    def _initiate_encounter(self, wv, cfg, slot_id: str) -> bool:
        """同场偶遇搭话：本 slot **没有模板对话**的空档里，与同处一人搭一句话。

        与 `_initiate` 的差别只有两处，其余（提示词装配 / 去重 / 线程字段）**完全复用**：
          ① 不需要 `template_id`（这正是当前「没有模板就没有对话」的缺口）；
          ② `ctx.trigger = "encounter"` / `ctx.initiator = self`，供读数器区分通道。

        有界与纪律：
          - 默认 OFF（`encounter_enabled()` 假 ⇒ 立刻 False，零事件零改动）；
          - `night` 不搭话（`ENCOUNTER_SKIP_SLOTS`）；
          - 同一 (agent, slot) **至多一次**（`self._enc_slots`，因为门率是 slot 级掷骰）；
          - 仍受 `max_messages_per_slot` / `max_turns` 等既有上限约束（本方法不自带配额）；
          - `tag_hints` 留空：非模板话题**不污染** 20 类模板普查（tag_hints 是模板口径）；
          - 线程起点字段与 `_initiate` 同构 ⇒ 对方可经既有 `_pick_reply_target` 正常接话。
        """
        if not encounter_enabled():
            return False
        if wv.time.slot in ENCOUNTER_SKIP_SLOTS:
            return False
        if slot_id in self._enc_slots:
            return False
        partner = encounter_decision(self.agent_id, slot_id, self._co_present_peers(wv))
        if not partner:
            return False
        self._enc_slots.add(slot_id)          # 掷过骰就作废本 slot（无论下文成败，防抖）
        parts = [self.agent_id, partner]
        dr_cfg = DR.load_params()
        rift_line = None
        if dr_cfg.get("enabled"):
            rift_line = DR.context_line(self._rifts, partner, int(wv.round),
                                        name=self._name(partner), params=dr_cfg)
        prompt = self._dialogue_prompt(ENCOUNTER_TOPIC, parts, cfg, rift_line=rift_line, wv=wv)
        meta = {"agent_id": self.agent_id, "round": wv.round, "template": ENCOUNTER_TOPIC}
        body = (self.llm.call("dialogue", prompt, meta=meta).text or "").strip()
        if not body:
            return False
        body = self._dequp_body(prompt, body, meta)
        payload: dict = {
            "scope": "private", "to": partner, "body": body, "refs": [],
            "tag_hints": [],
            "thread_id": DT.thread_id_dm(self.agent_id, partner, wv.round),
            "turn_index": 0, "reply_to": None,
            "participants": parts, "topic": ENCOUNTER_TOPIC,
            "ctx": self._ctx_snapshot(partner, ENCOUNTER_TOPIC, trigger="encounter",
                                      initiator=self.agent_id),
        }
        self._slot_msgs[slot_id] = int(self._slot_msgs.get(slot_id, 0)) + 1
        self._comm_slot = slot_id
        self.kernel.submit_intent(self.agent_id, Intent(INTENT_SOCIAL, self.agent_id, payload))
        return True

    # ---- 提示词装配 --------------------------------------------------------
    def _gossip_hint(self, exclude: list | None = None) -> str:
        """G 系列 A1 臂（闲话/第三方提及）：把「可引用的真人名单」喂进提示词。

        单变量约束：开关关闭（默认 OFF）时返回空串，A0 的提示词**逐字节不变**；
        打开时只在提示词中**插入**这一段，不改任何既有段落、不改任何配置/世界态。
        名单只取 `code/config/personas.json` 已在用的显示名词表（`_peer_names`，
        由 `dialogue_threads.build_display_map` 生成）∩ 本 run 的 `peers`，
        并排除自己与当前对话对象（否则只是"称呼率"的别名，见 DESIGN §2.1 去噪第 1 条）。
        """
        if not gossip_g1_enabled():
            return ""
        ex = {self.agent_id, *(exclude or [])}
        names = sorted({self._peer_names[p] for p in self.peers
                        if p not in ex and self._peer_names.get(p)})
        if not names:
            return ""
        return (f"\n镇上还住着：{'、'.join(names)}。可以顺口提一句他们最近的事（谁家…），"
                "但不确定就别编，只说你真看见、听见过的事。")

    def _relation_line(self, partners: list) -> str:
        bits = []
        for p in partners:
            if p not in self._peer_names and not self._rel_cache:
                pass
            fam = int(self._rel_cache.get((p, "familiarity"), 0))
            aff = int(self._rel_cache.get((p, "affinity"), 0))
            bits.append(f"{self._name(p)}（熟悉度{fam}/好感{aff}）")
        return "、".join(bits)

    def _mood_line(self) -> str:
        mood = DT.mood_label(self.needs)
        need = DT.scarcest_need(self.needs)
        if need:
            dim, val = next(iter(need.items()))
            return f"情绪：{mood}；最紧的需求：{dim}={val}"
        return f"情绪：{mood}"

    # ---- 处境锚臂（SA）：此刻时段 + 所在场所 + 手上正做什么 --------------
    def _scene_line(self, wv) -> str:
        """把「此刻什么时段、你在哪儿、手上正做什么」渲染成**一行**人话处境。

        单变量约束（沿用 `_gossip_hint` / `_memory_line` 的开关先例）：
          - 开关关闭（默认 OFF）⇒ `self._scene=None`、返回空串 ⇒ 两条提示词**逐字节不变**、
            `ctx.scene` 键不出现（payload 亦逐字节不变）；
          - 打开 ⇒ 只在提示词中**插入一行**，并把本条的处境快照写进 `ctx.scene`（additive）。

        素材**只读** `WorldView`：`time.slot` / `location` / `current_activity`。
        场所名走 `self.places[place_id]["name_cn"]`（人话）；缺项则**不写该片段**，
        **绝不把 `plaza` / `farm` 这类内部 id 递进提示词**（防 L-8c / L-13 回归）。
        """
        self._scene = None
        if wv is None or not SA.enabled():
            return ""
        try:
            slot = str(getattr(getattr(wv, "time", None), "slot", "") or "")
            place = str(getattr(wv, "location", "") or "")
            rnd = int(getattr(wv, "round", 0))
            ca = getattr(wv, "current_activity", None) or {}
            activity = str(ca.get("activity_type") or "") if isinstance(ca, dict) else ""
        except Exception:      # 世界视图字段缺失 ⇒ 退化为「不加处境」，不打断对话
            return ""
        name = ""
        if place:
            spec = (self.places or {}).get(place) or {}
            name = str(spec.get("name_cn") or "").strip()
        line = SA.render(self.agent_id, rnd, slot, name, activity or None)
        if not line:
            return ""
        self._scene = SA.audit(slot, place or None, activity or None, line)
        return line

    # ---- 天气臂（WX）：今儿天怎么样（季 + 天气）--------------------------
    def _weather_line(self, wv) -> str:
        """把「今儿天怎么样」渲染成**一行**人话（如「今儿天怎么样：开春了，阴着天。」）。

        单变量约束（同 `_scene_line` / 日历臂的开关先例）：
          - 开关关闭（默认 OFF）⇒ `self._weather=None`、返回空串 ⇒ 两条提示词**逐字节不变**、
            `ctx.weather` 键不出现（payload 亦逐字节不变）；
          - 打开 ⇒ 只在提示词中**插入一行**，并把本条的天候快照写进 `ctx.weather`（additive）。

        素材**只读** `WorldView.time.day`（`engine/time.py::derive_time` 已确定性派生）；
        天气由 `(HITT_WORLD_SEED, day)` 纯函数推出（同 seed 同 day 恒同天气，可 replay）。
        **不读墙钟、不新增真相源、不发事件、不改 state_hash、不写记忆、不碰 config**。
        字段缺失/非法 ⇒ 退化为「不加天气」，不打断对话。
        """
        self._weather = None
        if wv is None or not WX.enabled():
            return ""
        try:
            tc = getattr(wv, "time", None)
            if tc is None:            # 没有时间坐标 ⇒ 不知道今天第几天 ⇒ 不加天气
                return ""
            day = int(getattr(tc, "day", 0))
            rnd = int(getattr(wv, "round", 0))
        except Exception:      # 世界视图字段缺失 ⇒ 退化为「不加天气」，不打断对话
            return ""
        seed = WX.world_seed()
        line = WX.render(self.agent_id, rnd, day, seed)
        if not line:
            return ""
        self._weather = WX.audit(day, WX.season_of_day(day), WX.weather_of_day(day, seed),
                                 seed, line)
        return line

    def _memory_line(self, wv, exclude: list | None = None) -> str:
        """F-6 臂（跨天记忆进对话）：把「**本人**前些天记下的事」原样接进提示词。

        单变量约束（沿用 `_gossip_hint` 的开关先例）：
          - 开关关闭（默认 OFF）⇒ `self._mem_refs` 置空、返回空串，A0 提示词**逐字节不变**；
          - 打开 ⇒ 只在提示词中**插入**这一段，不改任何既有段落、不改配置、不改世界态、不改检索权重。

        取材只读现有的 `memory.nodes`（**不新增检索通道、不改 `score_and_rank` 权重、
        不 touch/不改 access_count**）：过滤 `node.day < 当前 day`（跨天，含昨天）+
        「人话」门（见 `_readable`），再按 (day 新→旧, importance 高→低, 去重键升序) 排序。
        准入（D1 改动）：先给固化印象（`kind=="semantic"`）保底 `MEMORY_F6_SEMANTIC_QUOTA`
        个槽，剩余额度按 observation → 其它 填，总数仍受 `MEMORY_F6_TOP_N` 约束。
        审计：实际注入的 `mem_id` 记到 `self._mem_refs`，由 `_ctx_snapshot()` 落进 MSG payload；
        `-SM-` 条目可直接从 `mem_id` 里区分（如 `M-P003-SM-P007`）。
        """
        self._mem_refs = []
        if not memory_f6_enabled():
            return ""
        today = int(getattr(wv, "day", 0))
        # 只排除「自己的」记忆条目（`subject` 是自己）；**不排除**对话对象——
        # 「昨天阿禾说……／阿禾送来半袋米」正是最像过日子的引用，排除掉就剩不下什么了。
        ex = {self.agent_id}
        picked: list[tuple[int, str]] = []
        seen: set[str] = set()

        def _norm(t: str) -> str:
            """去重键：去掉尾部括注（如「（insight 3）」）与空白，防同义重复白占额度。"""
            t = re.sub(r"[（(][^（）()]{0,12}[)）]\s*$", "", (t or "").strip())
            return re.sub(r"\s+", "", t)

        def _readable(t: str) -> str | None:
            """记忆流 → 人话。**本臂的第二道门**（不是装饰，见 exec-notes §机制事实）：

            记忆流里大量条目是原始事件短语（实测如「P001 的 RELATION_CHANGE 事件。」、
            「P003 在 residence 开始 rest。」）。原样喂进提示词会 ①把内部 token 泄漏给模型
            （等于制造 L-8/L-13 回归）②把台词带成机器话。故：
              - `Pxxx` → 显示名（复用 `_name`，失败保留原串）；
              - 含 ASCII 词（≥3 字母）或「事件」/全大写 token ⇒ 丢弃（非人话）；
              - 去空白后短于 6 字 ⇒ 丢弃（没有信息量）。
            返回 None 表示不可用。
            """
            s = (t or "").strip().replace("\n", " ")
            if not s:
                return None

            def _sub(m):
                pid = m.group(0)
                try:
                    return self._name(pid) or pid
                except Exception:
                    return pid

            s = re.sub(r"P\d{3}", _sub, s)
            s = re.sub(r"\s*说：", "说：", s)          # 「秀娘 说：」→「秀娘说：」
            if "事件" in s or re.search(r"[A-Za-z]{3,}", s):
                return None
            if re.search(r"[A-Z]{2,}", s):
                return None
            if len(re.sub(r"\s+", "", s)) < 6:
                return None
            return s

        # 取材：**本人的跨天记忆**里，挑「最近发生、还挂得上心」的两条。
        # 排序键固定为 (day 新→旧, importance 高→低, 去重键升序) ⇒ 确定性、与 RNG 无关。
        # 只读 `memory.nodes`：不 touch、不改 access_count、不改检索权重 ⇒ 对既有检索零影响。
        cand: list[tuple[str, int, int, str, str, str]] = []   # (kind, day, imp, key, text, mem_id)
        for node in self.memory.nodes.values():
            try:
                if int(node.day) >= today:        # 只要跨天记忆（当天的不算"想起来"）
                    continue
            except Exception:
                continue
            text = _readable(node.text)
            if text is None:
                continue
            key = _norm(text)
            # 内容级去重：同一句话由不同人说过也只引一次（避免两条记忆只是换了说话人）
            content_key = key.split("说：", 1)[1] if "说：" in key else key
            if not key or key in seen or content_key in seen:
                continue
            if node.subject and str(node.subject) in ex:   # 不喂「正在跟我说话的人」的旧账
                continue
            seen.add(key)
            seen.add(content_key)
            cand.append((str(getattr(node, "kind", "") or ""),
                         int(node.day), int(getattr(node, "importance", 0) or 0),
                         key, text, str(node.mem_id)))

        # D1：准入顺序（改前是「先 observation 桶、后 other 桶」两趟，observation 常常
        # 一趟就把 TOP_N 占满 ⇒ 固化印象几乎排不进）。改后**分两段**：
        #   ① 固化印象（`kind=="semantic"`，即 `-SM-`）先占 `MEMORY_F6_SEMANTIC_QUOTA` 个槽；
        #   ② 剩余额度仍按观察类 → 其它 的顺序填（这两趟内部排序口径与改前逐字一致）。
        # 排序键固定为 (day 新→旧, importance 高→低, 去重键升序) ⇒ 确定性、与 RNG 无关。
        ranked = sorted(cand, key=lambda t: (-t[1], -t[2], AR.mem_usage(t[5]), t[3]))

        # ① 固化印象保底（跨天攒出来的「关于某人的印象」，带细节或至少带人话）
        for kind, day, _imp, key, text, mid in ranked:
            if len(picked) >= MEMORY_F6_SEMANTIC_QUOTA:
                break
            if kind != "semantic":
                continue
            picked.append((day, text[:MEMORY_F6_ITEM_CHARS]))
            self._mem_refs.append(mid)

        # ② 剩余额度：先观察类、后反思/其它（沿用改前的桶序，只是不会再吃掉印象的槽）
        for want in ("observation", "other"):
            for kind, day, _imp, key, text, mid in ranked:
                if len(picked) >= MEMORY_F6_TOP_N:
                    break
                if mid in self._mem_refs:          # ① 已用掉的条目不再重复占槽
                    continue
                if want == "observation" and kind != "observation":
                    continue
                if want == "other" and kind in ("observation", "semantic"):
                    continue
                picked.append((day, text[:MEMORY_F6_ITEM_CHARS]))
                self._mem_refs.append(mid)
        if not picked:
            return ""
        AR.note_memory(self._mem_refs)   # R12：去重臂记账（默认 OFF ⇒ 不改任何状态）
        items = "；".join(f"第{d}天：{t}" for d, t in picked)
        return (f"\n你想起的事：{items}"
                "\n（这些话跟你眼下说的事有关，就顺口提一句；无关就别硬提，也别编没记过的事。）")

    def _l7_struct_line(self, wv, partners, turn: int, mode: str) -> str:
        """L-7 结构臂：生成**前**下发「开口方式 / 收束方式 / 禁忌开头」三条结构约束。

        单变量约束（沿用 F-4/F-6/G-1 的插入先例，但**默认 ON**）：
          - 关闭（`LIFE_PROMPT_L7_STRUCT=0`）⇒ `self._l7s=None`、返回空串，
            两个提示词与接入前**逐字节一致**，payload 不出现 `ctx.l7struct`；
          - 开启 ⇒ 只在提示词中**插入一段**，并把本条实际下发的约束写进
            `ctx.l7struct`（additive，`ctx` 已整体透传，与 `ctx.dequp`/`ctx.echo` 同一先例）。
        指派完全确定性（`L7S.assign` = sha256(agent|对象|day|slot|round|turn|mode)），
        不含墙钟/随机/网络 ⇒ 同一 run 可复现。
        """
        self._l7s = None
        if wv is None or not L7S.enabled():
            return ""
        try:
            day = int(getattr(wv, "day", 0))
            slot = f"{wv.time.day_of_week}-{wv.time.slot}"
            rnd = int(wv.round)
        except Exception:      # 世界视图字段缺失 ⇒ 退化为「不加约束」，不打断对话
            return ""
        # 取材**只读可见事件**（不放进程状态）⇒ 续跑/replay 逐字节可复现
        self._l7s = L7S.plan(self.agent_id, partners, day, slot, rnd, int(turn), mode,
                             recent=L7S.recent_bodies(wv))
        return L7S.render(self._l7s)

    # ---- R19 话题宽度臂（TB）：人话化 topic + 岔题提示 + 内容门控 ----------
    def _topic_label(self, topic: str | None) -> str:
        """L-13：模板/话题 id → 人话，**默认生效**（不再依赖话题宽度臂）。

        默认（`LIFE_PROMPT_TOPIC_LABEL` 未设或为 `on/1/true/yes`）：无条件走
        `TB.label`（未知 id 原样返回 ⇒ 不臆造中文、不丢信息），
        `whisper` / `combat_training` 这类内部 token 不再递给模型。

        回退臂（`LIFE_PROMPT_TOPIC_LABEL=off/0/false/no`）：**逐字节复刻旧实现**
        `TB.label(topic) if TB.enabled() else (topic or "")` ⇒ 话题宽度臂关闭（默认）时
        与改造前提示词完全相同，用于同树 OFF/ON 两臂可复现对照。
        """
        if TB.label_enabled() or TB.enabled():
            return TB.label(topic)
        return topic or ""

    def _topic_shift_line(self, wv, partner: str | None, tid: str | None,
                          topic: str | None, turn: int | None) -> str:
        """TB 臂：turn≥1 的回复**生成前**给一个「可自然岔入的相邻话题」。

        指派完全确定性（sha256(agent|thread|round|turn|base)），不读墙钟/随机 ⇒ replay 一致；
        关闭时 `self._tb=None`、返回空串 ⇒ 提示词与接入前逐字节一致。
        """
        self._tb = None
        if not TB.enabled():
            return ""
        try:
            rnd = int(getattr(wv, "round", 0))
            t = 0 if turn is None else int(turn)
            thread_key = str(tid or f"{partner or '-'}|{topic or '-'}")
        except Exception:
            return ""
        self._tb = TB.plan(self.agent_id, thread_key, rnd, t, topic)
        return TB.render(self._tb)

    def _topic_shift_tag(self, body: str) -> str | None:
        """TB 臂：**内容门控**——正文真的落到该话题（命中关键词）才返回可追加的 tag。"""
        if not TB.enabled():
            return None
        p = getattr(self, "_tb", None)
        if not p:
            return None
        # 双条件：命中 shift 关键词 且 不命中 base 关键词（防「本来就在说这个话题」白送）
        return p["shift"] if TB.confirm(body, p["shift"], p.get("base")) else None

    def _dialogue_prompt(self, tid: str, parts: list, cfg: dict | None = None,
                         rift_line: str | None = None, wv=None) -> str:
        cfg = cfg or self._dlg_cfg()
        partners = [p for p in parts if p != self.agent_id]
        others = self._relation_line(partners) or "(独自)"
        mem_line = self._memory_line(wv, partners) if wv is not None else ""
        return (self.persona.compressed_profile(self._current_goal())
                + f"\n场景：{self._topic_label(tid)}；对象：{others}。{self._mood_line()}。"
                + self._scene_line(wv)      # 处境锚臂：时段/场所/手上事（默认 OFF ⇒ 空串）
                + self._weather_line(wv)    # 天气臂：季 + 今天什么天（默认 OFF ⇒ 空串）
                + (rift_line or "")          # R6-T2：处境（事实+选项）；关闭/无旧账时为空串
                + self._gossip_hint(partners)  # G系列A1臂：可引用真人名单（默认OFF ⇒ 空串）
                + mem_line                   # F-6 臂：跨天记忆原文（默认OFF ⇒ 空串）
                + self._l7_struct_line(wv, partners, 0, "initiate")  # L-7 结构臂：开口/收束/禁忌开头（默认ON）
                + AR.prompt_line()           # R12 去重臂：最近说过的话（默认OFF ⇒ 空串）
                + (ADDR_EVOLVE_LINE if addr_evolve_enabled() else "")  # N-15 臂：称呼随相处演化一行（默认OFF ⇒ 空串）
                + narration_tail("initiate", self.agent_id,
                                 0 if wv is None else getattr(wv, "round", 0)))  # D9i/D9m：收尾指令按 LIFE_PROMPT_NARRATION 二选一；旋转臂再按 LIFE_PROMPT_NARRATION_ROTATION 换示例（均默认关 ⇒ 与改动前逐字节相同）

    def _reply_prompt(self, partner: str | None, topic: str, history: list,
                      cfg: dict | None = None, rift_line: str | None = None,
                      wv=None, repair_line: str | None = None,
                      echo_line: str | None = None, turn: int | None = None,
                      tid: str | None = None) -> str:
        cfg = cfg or self._dlg_cfg()
        lines = "\n".join(line for _, line in history) or "(还没说什么)"
        who = self._name(partner) if partner else "在场的人"
        mem_line = self._memory_line(wv, [partner] if partner else []) if wv is not None else ""
        return (self.persona.compressed_profile(self._current_goal())
                + f"\n你正在和{who}聊「{self._topic_label(topic)}」。{self._mood_line()}。"
                + self._scene_line(wv)      # 处境锚臂：时段/场所/手上事（默认 OFF ⇒ 空串）
                + self._weather_line(wv)    # 天气臂：季 + 今天什么天（默认 OFF ⇒ 空串）
                + (rift_line or "")          # R6-T2：处境（事实+选项）；关闭/无旧账时为空串
                + (repair_line or "")        # R13：本线程旧账的「这一句把话说开」要求；关闭/无旧账为空串
                + (echo_line or "")          # F-3：接住对方情绪的一句处境提示；关闭/不产为空串
                + f"\n刚才的对话：\n{lines}"
                + self._gossip_hint([partner] if partner else [])  # G系列A1臂：可引用真人名单（默认OFF ⇒ 空串）
                + mem_line                   # F-6 臂：跨天记忆原文（默认OFF ⇒ 空串）
                + self._l7_struct_line(wv, [partner] if partner else [],
                                       len(history) if turn is None else turn,
                                       "reply")  # L-7 结构臂：开口/收束/禁忌开头（默认ON）
                + self._topic_shift_line(wv, partner, tid, topic, turn)  # R19 话题宽度臂（默认OFF ⇒ 空串）
                + AR.prompt_line()           # R12 去重臂：最近说过的话（默认OFF ⇒ 空串）
                + narration_tail("reply", self.agent_id,
                                 0 if wv is None else getattr(wv, "round", 0)))  # D9i/D9m：同上（旋转臂默认关 ⇒ 与 D9i ON 逐字节相同）

    # ---- economy: negotiation / offer / order-cancel (T133) ----------------
    def _maybe_negotiate(self, wv) -> None:
        """Produce `INTENT.ECON.*` in the decision phase (v2/04 §5). The LLM
        (`purpose="negotiation"`, thinking=false) only writes the *wording*; the
        asking terms are the agent's own (deterministic, per-round) — never a preset
        world price. Money/goods consequences are settled by the kernel's 4.x hooks.
        Bounded: once per (agent, day)."""
        if not exchange_enabled():
            return
        if not self._llm_ok(wv):            # T221c: M4 未许可 → 不发议价 LLM
            return
        if wv.round % 12 != 0:              # ~ once per day per agent
            return
        # only sell what we actually hold; restrict to transferable goods if the
        # kernel exposes that hint (avoids good_not_transferable drops).
        held = {g: int(q) for g, q in (wv.inventory or []) if int(q) > 0}
        tg = set(getattr(wv, "transferable_goods", ()) or ())
        if tg:
            held = {g: q for g, q in held.items() if g in tg}
        if not held:
            return
        # deterministic pick: largest holding, ties by good_id asc (seed-stable)
        good = min(held, key=lambda g: (-held[g], g))
        res = self.llm.call(
            "negotiation",
            self.persona.compressed_profile(self._current_goal())
            + "\n请拟一句向街坊兜售余货/邀约议价的口头话（只写措辞，不写数字）。",
            meta={"agent_id": self.agent_id, "round": wv.round})
        wording = (res.text or "").strip()
        # agent's own ASK (deterministic, per-round); NOT a preset world price
        price = 50 + (int(sha256_hex(f"ask:{self.agent_id}:{wv.round}")[:6], 16) % 151)
        # public board offer (to=[] == broadcast discovery, v2/04 §4.1)
        self.kernel.submit_intent(self.agent_id, Intent(INTENT_ECON_OFFER, self.agent_id, {
            "act": "create", "kind": "sale", "to": [],
            "terms": {"good_id": good, "price_mu": price, "qty": 1},
            "enforceable": False, "body": wording}))
        # NOTE (T133): no ORDER_PLACE / ORDER_CANCEL here — the order-book path is
        # deferred to its own wave; producing a cancel without a place is a half-state.

    def _maybe_accept_offers(self, wv) -> None:
        """P2: read the (public) offer board via `visible_events()` and ACCEPT an offer
        addressed to us or broadcast (`to=[]`), **at the offer's own terms** (no preset
        price). Submits `INTENT.ECON.OFFER{act:"accept",...}`; the kernel wraps it into
        `OFFER_ACCEPTED`. ≤1 accept per round; each offer accepted at most once."""
        if not exchange_enabled():
            return
        for ev in wv.visible_events:
            if ev.type != "OFFER_CREATED":
                continue
            p = ev.payload or {}
            oid = p.get("offer_id")
            to = list(p.get("to") or [])
            if not oid or oid in self._accepted or p.get("from") == self.agent_id:
                continue
            if to:                                    # only public-board offers (to==[])
                continue
            self._accepted.add(oid)
            self.kernel.submit_intent(self.agent_id, Intent(INTENT_ECON_OFFER, self.agent_id, {
                "act": "accept", "offer_id": oid, "terms": p.get("terms") or {}}))
            return                                    # ≤1 accept per round

    # ---- misc ------------------------------------------------------------
    def _summary_names(self, mems: list[dict]) -> dict[str, str]:
        """D1：把 `Pxxx` 映射成**显示名**，交给 `forgetting.summarize` 组摘要措辞。

        只收「显示名 ≠ 原始 id」的条目（`names_enabled=False` 时映射为空 ⇒ 摘要写
        「有人」，绝不把内部 id 递给模型）。映射只由 `personas.json` 的显示名与
        记忆文本里实际出现的 id 决定（`sorted` 遍历）⇒ 与随机/墙钟无关。
        """
        ids: set[str] = set()
        for m in mems:
            subj = m.get("subject")
            if subj:
                ids.add(str(subj))
            ids.update(re.findall(r"P\d{3}", m.get("text") or ""))
        out: dict[str, str] = {}
        for pid in sorted(ids):
            try:
                nm = self._name(pid)
            except Exception:
                nm = pid
            if nm and nm != pid:
                out[pid] = nm
        return out

    def _sleep_params(self) -> dict:
        """T224：睡眠窗口参数（读 config/life_v2.json；默认关）。可被测试覆盖。"""
        return _sleep.load_params()

    def _maybe_sleep_window(self, wv) -> int:
        """T224 挂载点：night 时段执行一次睡眠离线窗（固化/遗忘/人格漂移）。

        **默认关**（`config/life_v2.json`）→ 直接返回 0、零副作用、行为与接入前逐项一致。
        产出以 INTENT.MEMORY 意图提交（`op ∈ {sleep_start,forget,consolidate,sleep_end}`），
        由裁决器落 `SLEEP_STARTED/MEMORY_FORGET/MEMORY_CONSOLIDATE/SLEEP_COMPLETED` 事件。
        **不新增决策类 LLM 调用**（纯整数模块）。不触碰 M2b 判定调用点。
        """
        params = self._sleep_params()
        if not _sleep.enabled(params):
            return 0
        slot = params["sleep"].get("slot", "night")
        if wv.time.slot != slot:
            return 0
        day = int(wv.time.day)
        if day in self._slept_days:
            return 0
        self._slept_days.add(day)

        anchor = {"persona_id": self.persona.persona_id,
                  "personality_big5": self.persona.personality_big5,
                  "values": self.persona.values, "skills": self.persona.skills}
        if self._persona_state is None:      # 锚定不写回：P(0)=anchor，之后只动表达层
            self._persona_state = PD.init_state(anchor)
            self._persona_p0 = dict(self._persona_state)
        # D1（本轮）：记忆快照**带上正文** `text`，供 `forgetting.summarize` 从被聚合
        # 的经历里提取可读细节（人物/地点/活动）。只读拷贝，不改任何节点状态。
        mems = [{"mem_id": n.mem_id, "kind": n.kind, "importance": n.importance,
                 "last_access": n.last_access, "access_count": n.access_count,
                 "subject": n.subject, "emo": 0, "consolidated": False,
                 "text": n.text or ""}
                for n in self.memory.nodes.values()]

        planned = int(params["sleep"].get("planned_ticks", 3))
        self.kernel.submit_intent(self.agent_id, Intent(INTENT_MEMORY, self.agent_id, {
            "op": "sleep_start", "day": day, "slot": slot, "planned_ticks": planned}))
        out = _sleep.run_sleep_window(self.agent_id, mems, wv.round, params,
                                      day=day, slot=slot, anchor=anchor,
                                      p_state=self._persona_state, p0=self._persona_p0,
                                      drift_events=self._reflection_drift_events(
                                          params, day=day, slot=slot, window=day),
                                      names=self._summary_names(mems))
        n = 0
        for a in out["forget"]:
            if self.kernel.submit_intent(self.agent_id, Intent(INTENT_MEMORY, self.agent_id, {
                    "op": "forget", "mem_id": a["mem_id"], "level": a["level"],
                    "retention_permille": a["retention_permille"], "reason": a["reason"],
                    "protected": a.get("protected"),                     # T244: 保护标记必须透传
                    "protection_reason": a.get("protection_reason"),
                    "day": day, "slot": slot})).ok:
                n += 1
        for g in out["consolidate"]:
            mid = f"M-{self.agent_id}-SM-{g['subject']}"
            # R18：固化摘要落成**真语义记忆**（先 MEMORY_WRITE，再 MEMORY_CONSOLIDATE）。
            # 修前只发 consolidate ⇒ 派生记忆在账本里只有一条索引、没有正文/向量，
            # 也永远没有 MEMORY_WRITE 事件（R10 §5.3 实测 SM 写入=0）。
            # 顺序必须是 write 在前：`_do_memory(write)` 对已存在的 mem_id 拒绝写入（append-only L5）。
            vec = self.memory.embedding.embed(g["text"])
            body_ref, embed_ref = self.memory.side.write(
                self.agent_id, mid, g["text"], vec)
            wpayload = {
                "op": "write", "mem_id": mid, "kind": "semantic", "importance": 6,
                "day": day, "slot": slot, "tick": int(wv.round),
                "subject": g["subject"], "body_ref": body_ref, "embed_ref": embed_ref,
                "refs": list(g["source_mem_ids"]), "source_event_seq": None,
            }
            if self.kernel.submit_intent(self.agent_id, Intent(INTENT_MEMORY, self.agent_id, wpayload)).ok:
                self.memory.commit_write(wpayload)
                n += 1
            if self.kernel.submit_intent(self.agent_id, Intent(INTENT_MEMORY, self.agent_id, {
                    "op": "consolidate", "subject": g["subject"],
                    "source_mem_ids": g["source_mem_ids"],
                    "produced_mem_id": mid,
                    "text": g["text"], "day": day, "slot": slot})).ok:
                n += 1
        # T244 W2b: 把 run_sleep_window 产出的 PERSONA_DRIFT 待发事件提交为 intent
        # （op="drift"，由 adapter `_do_memory` 落 PERSONA_DRIFT 事件；无候选/单窗不发）。
        for ev in out.get("events", []):
            if ev.get("type") != "PERSONA_DRIFT":
                continue
            p = dict(ev.get("payload") or {})
            p["op"] = "drift"
            if self.kernel.submit_intent(self.agent_id, Intent(INTENT_MEMORY, self.agent_id, p)).ok:
                n += 1
        # R18：睡眠收尾必须带上本次睡眠窗的人格指纹/漂移（`run_sleep_window` 的
        # `out["persona"]`）。修前只发 day/slot/actual_ticks ⇒ `SLEEP_COMPLETED` 的
        # `pf0/pf_t/drift_permille` 恒 null，人格漂移在睡眠收尾侧不可观测（R10 §5.3 缺陷②）。
        _p = out.get("persona") or {}
        self.kernel.submit_intent(self.agent_id, Intent(INTENT_MEMORY, self.agent_id, {
            "op": "sleep_end", "day": day, "slot": slot, "actual_ticks": planned,
            "pf0": _p.get("pf0"), "pf_t": _p.get("pf_t"),
            "drift_permille": _p.get("drift_permille")}))
        return n

    def _current_goal(self) -> str:
        return str(self.persona.goal_tendencies[0].get("kind", "")) if self.persona.goal_tendencies else ""

    # T244 W3: 由**既有**反思（MEMORY_REFLECT 产出）转成**有界**人格漂移候选（不新增 LLM）。
    # T333：情感判定**单一真源**在 `life/emotion.py`（此处仅别名，供既有引用/测试）。
    _DRIFT_POS = E.STRICT_POS
    _DRIFT_NEG = E.STRICT_NEG

    def _reflection_drift_events(self, params: dict, *, day: int, slot: str, window: int) -> list[dict]:
        """把既有反思节点转成**有界**漂移候选（06 §1.2；T244 W3）。

        规则（确定性、**宁缺毋滥**、不新增 LLM 调用）：
          * 仅取 `kind=="reflection"` 且 `importance >= min_importance`（默认 7）；
          * `dim` 由 `sha256(mem_id)` **确定性**映射到大五之一；
          * `delta` 符号由**情感词表**定；**无情感词 → 不产**（不在噪声里乱发）；
          * 每窗口每维至多一条候选；
          * **抖动 vs 真漂移**：某维需**连续 `min_windows`（默认 2）个窗口**被反思信号才发
            `PERSONA_DRIFT`（单窗噪声不发）；发出后该维计数清零（自然冷却）；
          * 幅度 = `±delta_max`（`bounded_update` 再夹一层）。
        """
        pd = params.get("persona_drift", {}) or {}
        min_imp = int(pd.get("min_importance", PD.DEFAULTS["min_importance"]))
        dmax = int(pd.get("delta_max", 1))
        min_windows = int(pd.get("min_windows", PD.DEFAULTS["min_windows"]))
        criterion = str(pd.get("criterion", "natural"))   # T333：strict|natural（默认 natural）
        dims = PD.BIG5_DIMS
        cand: dict[str, tuple[int, str]] = {}          # dim -> (sign, mem_id)
        for n in sorted(self.memory.nodes.values(), key=lambda x: x.mem_id):
            if n.kind != "reflection" or n.importance < min_imp:
                continue
            sign = E.emotion_sign(n.text or "", criterion=criterion)   # 单一真源
            if sign == 0:
                continue
            dim = dims[int(sha256_hex(n.mem_id)[:8], 16) % len(dims)]
            if dim not in cand:                        # 每窗口每维至多一条
                cand[dim] = (sign, n.mem_id)
        evs: list[dict] = []
        for dim in dims:
            if dim in cand:
                sign, mem_id = cand[dim]
                self._drift_streak[dim] = self._drift_streak.get(dim, 0) + 1
                reached = self._drift_streak[dim] >= min_windows
                # T323：每窗每"有候选"维落一条 CANDIDATE（identity fold、non-state）——
                # 让 restore() 可按"连续含候选窗数"**逐维**原样重建 _drift_streak。
                self.kernel.submit_intent(self.agent_id, Intent(INTENT_MEMORY, self.agent_id, {
                    "op": "drift_candidate", "dim": dim, "sign": sign, "window": int(window),
                    "mem_id": mem_id, "reached_threshold": bool(reached),
                    "day": day, "slot": slot}))
                if reached:  # 持续 = 真漂移；单窗 = 抖动，不发
                    evs.append({"dim": dim, "delta": sign * dmax, "cause_mem_id": mem_id})
                    self._drift_streak[dim] = 0            # 发出后冷却
            else:
                self._drift_streak[dim] = 0
        return evs

    def _describe_event(self, ev) -> str:
        t, p = ev.type, (ev.payload or {})
        if t == "ACTIVITY_STARTED":
            return f"{ev.actor} 在 {p.get('place')} 开始 {p.get('activity_type')}。"
        if t == "ACTIVITY_COMPLETED":
            return f"{ev.actor} 完成了 {p.get('activity_type')}（{p.get('place')}|{p.get('outcome')}）。"
        if t == "PLACE_ARRIVED":
            return f"{ev.actor} 到达 {p.get('place')}。"
        if t.startswith("MSG_"):
            return f"{ev.actor} 说：{p.get('body', '')}"
        if t == "RELATION_ENCOUNTER":
            return f"{ev.actor} 与 {p.get('b')} 在 {p.get('place')} 相遇。"
        if t == "AGENT_DIED":
            return f"{p.get('agent_id')} 去世了。"
        return f"{ev.actor} 的 {t} 事件。"

    def _score_importance(self, text: str, round_no: int) -> int:
        low = text.lower()
        if not any(k in low for k in ("派对", "救助", "去世", "争吵", "相遇", "party", "help", "died")):
            return 2
        if not getattr(self, "_llm_permit", True):   # T221c: M4 未许可 → 确定性兜底
            return 2
        if m2b_importance_mode() == "discriminative":
            return self._importance_discriminative(text, round_no)
        out = self.llm.call("importance", text,
                            meta={"agent_id": self.agent_id, "round": round_no}).text
        try:
            return clamp(int(out.strip().split()[0]), 1, 10)
        except Exception:
            return 2

    def _importance_discriminative(self, text: str, round_no: int) -> int:
        """M2b：importance 走受限选择（候选 {1..10}+逃生项，单一真源）；关闭时不走此路。"""
        if not getattr(self, "_llm_permit", True):   # T221c: M4 未许可 → 确定性兜底
            return 2
        options = list(C.JUDGMENT_OPTIONS["importance"])
        branch = rng_branch(self.agent_id, "importance", "self", round_no, options)
        jid = f"IMP-{self.agent_id}-{round_no}-{sha256_hex(text)[:8]}"
        try:
            payload, emitted = self.soft.judge(
                judgment_id=jid, dimension="importance", question_ref="importance",
                envelope={"options": options}, rng_branch=branch, parties=[self.agent_id],
                context={"text": text[:200]}, round_no=round_no, mode="discriminative")
            if not emitted:
                self._submit_audit("LLM_JUDGMENT", payload, phase=2)
            return clamp(int(payload.get("resolved", payload["decision"])), 1, 10)
        except Exception:
            return 2
