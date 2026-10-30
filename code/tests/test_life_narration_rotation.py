"""D9m 旁白**示例句确定性轮换**臂（`LIFE_PROMPT_NARRATION_ROTATION`）单测。

口径（v2/refs/D9m-prereg-narration-rotation.md + impl-1 任务书）：

  A. **默认关 = 与基线逐字节等价**：`LIFE_PROMPT_NARRATION` 未设时，`narration_tail`
     两段输出与 `d2a6fa9` 现场导出值 sha256 相等（GOLDEN_OFF_*），且整条 prompt 的
     sha256 仍等于 `life/tests/test_narration_toggle.py` 的 GOLDEN_*（同输入同装配路径）。
  B. **旋转关 = D9i ON 逐字节等价**（硬验收，防第三变量）：`NARRATION=1` 且旋转关时，
     `narration_tail` **返回 `_NARRATION_TAIL_ON` 常量对象本身**（`is` 断言），
     sha256 == d2a6fa9 ON 臂现值（GOLDEN_ON_*）。
  C. **模板只换示例句中那一句**：`_NARRATION_TAIL_ON_TPL[k].format(<D9i 原示例>)`
     逐字节等于 `_NARRATION_TAIL_ON[k]`（除示例外一字未改）。
  D. **确定性 / 可复现 / 幂等**：同 (seed, agent, round, kind) 恒同；不同 round 构成稳定序列；
     序列随 seed、随 agent 变化（不是常数指派，也不是随机源）。
  E. **禁用词表（防回潮）**：示例库与旋转开的**所有**输出都不得含
     蹭 / 磨 / 抹 / 擦 / 围裙 / 锉刀 / 木屑（正则级断言）。
  F. **组合语义**：NARRATION 关 × 旋转开 ⇒ 仍是禁旁白 OFF 文案（旋转在此外无效果）。

复跑（仓根）：
    cd code && python3 -m pytest tests/test_life_narration_rotation.py -q

GOLDEN 生成方式（不改工作树）：
    git archive d2a6fa9 | tar -x -C /tmp/d2a6fa9
    env -u LIFE_PROMPT_NARRATION PYTHONPATH=/tmp/d2a6fa9/code \
      python3 -c "import hashlib;from life.agent import narration_tail;\
print({k: hashlib.sha256(narration_tail(k).encode()).hexdigest() for k in ('initiate','reply')})"
    # 再以 LIFE_PROMPT_NARRATION=1 跑一次取 ON 臂 GOLDEN_ON_*
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from life.agent import (
    NARRATION_ENV,
    NARRATION_EXAMPLES,
    ROTATION_ENV,
    _NARRATION_TAIL_OFF,
    _NARRATION_TAIL_ON,
    _NARRATION_TAIL_ON_EXAMPLE,
    _NARRATION_TAIL_ON_TPL,
    narration_example,
    narration_tail,
)
from life.tests.test_narration_toggle import (  # 复用同一装配路径，避免"另写一份 prompt"
    GOLDEN_INITIATE_SHA256,
    GOLDEN_REPLY_SHA256,
    OFF_INITIATE_TAIL,
    OFF_REPLY_TAIL,
    _prompts,
)

WORLD_SEED_ENV = "HITT_WORLD_SEED"

#: d2a6fa9 现场导出：env 未设时 narration_tail 两段输出（= 禁旁白）
GOLDEN_OFF_INITIATE_SHA256 = "3646f04995a961b12573157ccd7dc70fa4fef1828c1415209f197aab0972a77c"
GOLDEN_OFF_REPLY_SHA256 = "ce2cfb8757b1a053b1a9e811e070c7ef91aa3a90cac2c5b6161dff6543ad324d"

#: d2a6fa9 现场导出：LIFE_PROMPT_NARRATION=1 时 narration_tail 两段输出（= D9i ON 固定示例）
GOLDEN_ON_INITIATE_SHA256 = "d8382f82eb5285eb78110f40b204e6c99e61645d9a233e1a347f98cff101168d"
GOLDEN_ON_REPLY_SHA256 = "5e45e318030098824bc32b9d429d8fddb8c55167fb9b35728c5e325525f02d2b"

#: 禁用词（单个字符即可命中：蹭/磨/抹/擦 为高频动作动词，围裙/锉刀/木屑 为 D9i 旧道具）
BANNED = re.compile(r"[蹭磨抹擦]|围裙|锉刀|木屑")

KINDS = ("initiate", "reply")


def _sha(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


@pytest.fixture()
def base_env(monkeypatch):
    """清空两个开关与 seed，得到确定的基线环境。"""
    for k in (NARRATION_ENV, ROTATION_ENV, WORLD_SEED_ENV):
        monkeypatch.delenv(k, raising=False)


# ---------------------------------------------------------------- A. 默认关等价
def test_default_off_tail_byte_identical(base_env):
    assert narration_tail("initiate") == _NARRATION_TAIL_OFF["initiate"] == OFF_INITIATE_TAIL
    assert narration_tail("reply") == _NARRATION_TAIL_OFF["reply"] == OFF_REPLY_TAIL
    assert _sha(narration_tail("initiate")) == GOLDEN_OFF_INITIATE_SHA256
    assert _sha(narration_tail("reply")) == GOLDEN_OFF_REPLY_SHA256


def test_default_off_prompt_sha_unchanged(base_env, tmp_path):
    """默认关：整条 prompt 的 sha256 仍等于 D9i 基线（同输入同装配路径）。"""
    p_init, p_reply = _prompts(tmp_path)
    assert _sha(p_init) == GOLDEN_INITIATE_SHA256
    assert _sha(p_reply) == GOLDEN_REPLY_SHA256


def test_rotation_on_without_narration_is_off_wording(base_env, monkeypatch):
    """F. 组合语义：NARRATION 关 × 旋转开 ⇒ 仍为禁旁白 OFF 文案（旋转无效果）。"""
    monkeypatch.setenv(ROTATION_ENV, "1")
    for k in KINDS:
        assert narration_tail(k, "P003", 7) is _NARRATION_TAIL_OFF[k]
    assert _sha(narration_tail("initiate", "P003", 7)) == GOLDEN_OFF_INITIATE_SHA256


# ---------------------------------------------- B. 旋转关 == D9i ON（硬验收）
def test_rotation_off_returns_d9i_on_constant_object(base_env, monkeypatch):
    monkeypatch.setenv(NARRATION_ENV, "1")
    for k in KINDS:
        tail = narration_tail(k, "P003", 12)
        assert tail is _NARRATION_TAIL_ON[k], "旋转关必须直接返回常量对象，不得拼装"
    assert _sha(narration_tail("initiate", "P003", 12)) == GOLDEN_ON_INITIATE_SHA256
    assert _sha(narration_tail("reply", "P003", 12)) == GOLDEN_ON_REPLY_SHA256


@pytest.mark.parametrize("val", ["0", "", "false", "off", "2", "no"])
def test_rotation_off_values_are_equivalent(base_env, monkeypatch, val):
    monkeypatch.setenv(NARRATION_ENV, "1")
    monkeypatch.setenv(ROTATION_ENV, val)
    assert narration_tail("initiate", "P003", 3) is _NARRATION_TAIL_ON["initiate"]
    assert narration_tail("reply", "P003", 3) is _NARRATION_TAIL_ON["reply"]


# --------------------------------------------------- C. 模板只换了示例句
@pytest.mark.parametrize("kind", KINDS)
def test_template_differs_from_d9i_on_only_in_example(kind):
    rebuilt = _NARRATION_TAIL_ON_TPL[kind].format(_NARRATION_TAIL_ON_EXAMPLE[kind])
    assert rebuilt == _NARRATION_TAIL_ON[kind]


@pytest.mark.parametrize("kind", KINDS)
def test_rotation_on_is_single_variable_against_d9i_on(base_env, monkeypatch, kind):
    """旋转开 vs 旋转关：前缀/后缀逐字节相同，只有「（示例）」这一段不同。"""
    monkeypatch.setenv(NARRATION_ENV, "1")
    off_tail = _NARRATION_TAIL_ON[kind]
    monkeypatch.setenv(ROTATION_ENV, "1")
    on_tail = narration_tail(kind, "P003", 5)
    old = f"（{_NARRATION_TAIL_ON_EXAMPLE[kind]}）"
    ex = narration_example(kind, "P003", 5)
    assert old in off_tail
    assert on_tail == off_tail.replace(old, f"（{ex}）")
    # 括号结构与旋转关完全相同，且只命中选中的那句示例一次
    assert on_tail.count("（") == off_tail.count("（")
    assert on_tail.count("）") == off_tail.count("）")
    assert on_tail.count(ex) == 1
    assert ex not in off_tail  # 新示例不得是 D9i 固定示例


# ------------------------------------------- D. 确定性 / 幂等 / 与 seed 相关
def test_sequence_deterministic_and_idempotent(base_env, monkeypatch):
    monkeypatch.setenv(NARRATION_ENV, "1")
    monkeypatch.setenv(ROTATION_ENV, "1")
    monkeypatch.setenv(WORLD_SEED_ENV, "42")
    for kind in KINDS:
        seq1 = [narration_tail(kind, "P003", r) for r in range(12)]
        seq2 = [narration_tail(kind, "P003", r) for r in range(12)]
        assert seq1 == seq2, "同输入必须逐字节相同（幂等/replay 可复现）"
        assert narration_example(kind, "P003", 7) == narration_example(kind, "P003", 7)


def test_sequence_not_constant(base_env, monkeypatch):
    """不是常数指派：12 个回合至少取到 2 种示例（否则轮换名不副实）。"""
    monkeypatch.setenv(NARRATION_ENV, "1")
    monkeypatch.setenv(ROTATION_ENV, "1")
    for kind in KINDS:
        seen = {narration_example(kind, "P003", r) for r in range(12)}
        assert len(seen) >= 2


def test_sequence_depends_on_seed(base_env, monkeypatch):
    monkeypatch.setenv(NARRATION_ENV, "1")
    monkeypatch.setenv(ROTATION_ENV, "1")
    monkeypatch.setenv(WORLD_SEED_ENV, "0")
    s0 = [narration_example("initiate", "P003", r) for r in range(12)]
    monkeypatch.setenv(WORLD_SEED_ENV, "12345")
    s1 = [narration_example("initiate", "P003", r) for r in range(12)]
    assert s0 != s1, "序列必须与 seed 相关"


def test_sequence_depends_on_agent(base_env, monkeypatch):
    monkeypatch.setenv(NARRATION_ENV, "1")
    monkeypatch.setenv(ROTATION_ENV, "1")
    a = [narration_example("reply", "P003", r) for r in range(12)]
    b = [narration_example("reply", "P007", r) for r in range(12)]
    assert a != b, "不同角色不应共用同一序列"


def test_seed_default_fallback_is_zero(base_env, monkeypatch):
    """HITT_WORLD_SEED 缺省回落 "0"：未设 / 空串 / "0" 三种情况序列相同。"""
    monkeypatch.setenv(NARRATION_ENV, "1")
    monkeypatch.setenv(ROTATION_ENV, "1")
    unset = [narration_example("initiate", "P003", r) for r in range(6)]
    monkeypatch.setenv(WORLD_SEED_ENV, "")
    empty = [narration_example("initiate", "P003", r) for r in range(6)]
    monkeypatch.setenv(WORLD_SEED_ENV, "0")
    zero = [narration_example("initiate", "P003", r) for r in range(6)]
    assert unset == empty == zero


# --------------------------------------------------- E. 禁用词表（防回潮）
def test_lexicon_size_and_banned_words():
    assert len(NARRATION_EXAMPLES) >= 6
    for ex in NARRATION_EXAMPLES:
        assert not BANNED.search(ex), f"示例库含禁用词: {ex}"
        assert ex and "（" not in ex and "）" not in ex


def test_rotation_outputs_free_of_banned_words(base_env, monkeypatch):
    monkeypatch.setenv(NARRATION_ENV, "1")
    monkeypatch.setenv(ROTATION_ENV, "1")
    for seed in ("0", "7", "42"):
        monkeypatch.setenv(WORLD_SEED_ENV, seed)
        for agent in ("P001", "P003", "P007"):
            for r in range(24):
                for kind in KINDS:
                    tail = narration_tail(kind, agent, r)
                    assert not BANNED.search(tail), (seed, agent, r, kind, tail)


def test_switch_parsing(base_env, monkeypatch):
    from life.agent import narration_rotation_enabled
    for v in ["1", "true", "TRUE", "yes", "On", " 1 "]:
        monkeypatch.setenv(ROTATION_ENV, v)
        assert narration_rotation_enabled() is True
    for v in ["0", "", "false", "off", "no", "2"]:
        monkeypatch.setenv(ROTATION_ENV, v)
        assert narration_rotation_enabled() is False
    monkeypatch.delenv(ROTATION_ENV, raising=False)
    assert narration_rotation_enabled() is False
