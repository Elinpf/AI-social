"""N-15 称呼演化臂（`LIFE_PROMPT_ADDR_EVOLVE`）单测 = 预登记机制闸 `M1`。

预登记：`v2/refs/N15-prereg-addr-evolve-20261030.md`（§8.1 实现约束 / §8.3 L1 / §4 M1）。
本单测**只测开关语义与单变量性**，不测效果。

断言清单：
  1. 三态解析：{`1`,`true`,`yes`,`on`} ⇒ ON；未设 / 空串 / 其它值 ⇒ OFF（与既有 `LIFE_PROMPT_*` 同口径）。
  2. **OFF 逐字节等价**：OFF 态 `_dialogue_prompt` 的 sha256 == 未改动基线树（commit `43e8a39`，
     worktree `.worktrees/n15-baseline`）实测的常量 `GOLDEN_OFF_DIALOGUE_SHA256`。
  3. **单变量**：ON 态 = OFF 态 + 恰好一处 `ADDR_EVOLVE_LINE`（把该串删掉后与 OFF 逐字节相等）。
  4. **只注入 `_dialogue_prompt`**：`_reply_prompt` 的 OFF / ON 逐字节相同。

复算命令（仓库根）：
    python3 -m pytest code/life/tests/test_addr_evolve_toggle.py -q
交叉验证（静态渲染，含基线树对比）：
    python3 tools/d9/addr_evolve_wiring.py --code-root code --baseline-root .worktrees/n15-baseline/code
"""
from __future__ import annotations

from pathlib import Path

import pytest

from life import dialogue_threads as DT
from life.agent import (
    ADDR_EVOLVE_ENV,
    ADDR_EVOLVE_LINE,
    LifeLayerAgent,
    addr_evolve_enabled,
)
from life.persona import load_personas

CODE_DIR = Path(__file__).resolve().parents[2]
CONFIG = CODE_DIR / "config"

#: 未改动基线树（`43e8a39`）实测：同输入、同装配路径下 `_dialogue_prompt` 的 sha256
#: 由 `tools/d9/addr_evolve_wiring.py` 输出（基线树 OFF 一行），本单测据此防「OFF 被手滑改掉」。
GOLDEN_OFF_DIALOGUE_SHA256 = "e672f5ec6306e4c0dba54022b69f92beb6863faa986f1302e27db464fd8819b1"


def _mk_agent():
    """构造一个只依赖 prompt 装配路径的 agent（不跑内核、不联网）。"""
    personas = load_personas(CONFIG / "personas.json")
    pid = sorted(personas)[0]
    other = sorted(personas)[1]
    names = {pid: "老周", other: "秀娘"}
    a = object.__new__(LifeLayerAgent)
    a.agent_id = pid
    a.persona = personas[pid]
    a.peers = [other]
    a._peer_names = names
    a._rel_cache = {(other, "familiarity"): 20, (other, "affinity"): 5}
    a.needs = {"energy": 55, "satiety": 60, "social": 40, "esteem": 50, "mastery": 50, "leisure": 45}
    a._rifts = {}
    a._rifts_seen = set()
    a._thread_replied_turn = {}
    a._goals_set_weeks = set()
    return a, pid, other, names


def _prompts() -> tuple[str, str]:
    a, pid, other, names = _mk_agent()
    cfg = dict(DT.DEFAULTS)
    history = [(other, f"{names[other]}：show me")]
    return (a._dialogue_prompt("rel_maintain", [pid, other], cfg),
            a._reply_prompt(other, "rel_maintain", history, cfg))


@pytest.mark.parametrize("raw,expected", [
    (None, False), ("", False), ("  ", False), ("0", False), ("false", False), ("off", False),
    ("no", False), ("2", False), ("oFF", False),
    ("1", True), ("true", True), ("TRUE", True), ("yes", True), ("on", True), (" ON ", True),
])
def test_env_tristate(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv(ADDR_EVOLVE_ENV, raising=False)
    else:
        monkeypatch.setenv(ADDR_EVOLVE_ENV, raw)
    assert addr_evolve_enabled() is expected


def test_off_is_byte_identical_to_baseline(monkeypatch):
    monkeypatch.delenv(ADDR_EVOLVE_ENV, raising=False)
    d, _r = _prompts()
    import hashlib
    got = hashlib.sha256(d.encode("utf-8")).hexdigest()
    assert got == GOLDEN_OFF_DIALOGUE_SHA256, (
        "OFF 态 dialogue_prompt 与基线树不再逐字节相同 ⇒ 「OFF = 现状」这条锚被破坏（预登记 §8.3 L1 / J-9）。"
        f"got={got}")


def test_on_adds_exactly_one_line(monkeypatch):
    monkeypatch.delenv(ADDR_EVOLVE_ENV, raising=False)
    off_d, off_r = _prompts()
    monkeypatch.setenv(ADDR_EVOLVE_ENV, "1")
    on_d, on_r = _prompts()

    # 1) 注入行在 ON 里恰好出现一次、OFF 里不出现
    assert ADDR_EVOLVE_LINE.strip() not in off_d
    assert on_d.count(ADDR_EVOLVE_LINE.strip()) == 1
    # 2) 单变量：删掉注入行后，ON 与 OFF 逐字节相同
    assert on_d.replace(ADDR_EVOLVE_LINE, "", 1) == off_d
    # 3) reply_prompt 不受影响（只注入 _dialogue_prompt）
    assert on_r == off_r


def test_line_shape_is_frozen_single_sentence():
    """注入行形态冻结：单行、一句、不含示例 / 轮换池痕迹。"""
    body = ADDR_EVOLVE_LINE.strip()
    assert "\n" not in body
    assert len(body) <= 80, f"注入行过长（{len(body)} 字），需重新评审"
    for banned in ("例如", "比如", "第一次", "第二次", "轮换", "{", "}"):
        assert banned not in body, f"注入行出现了 {banned!r}：可能引入示例/轮换池（预登记 §8.4 硬边界）"
