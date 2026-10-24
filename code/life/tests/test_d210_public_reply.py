"""D2.10 单测：公开场合接话（`life/public_reply.py` + `dialogue_threads.is_replyable`）——不依赖 LLM。

钉住的事实（对应 `v2/refs/D210-prereg-public-reply.md` §2/§3）：
1. **开关语义**：缺省/`0` ⇒ 关；`1` ⇒ 开；其它值抛错（不静默）；
2. **关闭态逐字节等价**：`is_replyable("MSG_PUBLIC", ...)` 恒 False（master 行为）；
3. **开启态同场判据**：`place_ctx == 我的地点` ⇒ 可接；不等/缺失 ⇒ 不可接；自己不能接自己；
4. **开启态成员判据**：`me in participants` ⇒ 可接（沿用 GROUP 语义）；
5. **回话 scope**：PUBLIC 线程的回话**仍走 global**（不得落成 place_group）。
"""
from __future__ import annotations

import pytest

from life import public_reply as PR
from life.dialogue_threads import is_replyable

PUB = {"author": "P002", "participants": ["P002"], "place_ctx": "cafe",
       "thread_id": "TH-P002-PUB-0-0", "reply_to": None, "scope": "global"}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv(PR.ENV, raising=False)


# ---------------------------------------------------------------- 1) 开关语义
@pytest.mark.parametrize("raw,want", [("", False), ("0", False), ("1", True)])
def test_switch_values(monkeypatch, raw, want):
    monkeypatch.setenv(PR.ENV, raw)
    assert PR.enabled() is want


def test_switch_rejects_other_values(monkeypatch):
    monkeypatch.setenv(PR.ENV, "yes")
    with pytest.raises(ValueError):
        PR.enabled()


# ------------------------------------------- 2) 关闭态：PUBLIC 恒不可回复
def test_off_public_never_replyable():
    assert is_replyable("MSG_PUBLIC", PUB, "P003", my_place="cafe") is False
    assert is_replyable("MSG_PUBLIC", PUB, "P003") is False
    # DM/GROUP 的既有语义不受影响
    assert is_replyable("MSG_DM", {"to": "P003", "from": "P002"}, "P003") is True
    assert is_replyable("MSG_GROUP", {"participants": ["P002", "P003"],
                                      "from": "P002"}, "P003") is True


# ------------------------------------------------------------ 3) 同场判据
def test_on_same_place_replyable(monkeypatch):
    monkeypatch.setenv(PR.ENV, "1")
    assert is_replyable("MSG_PUBLIC", PUB, "P003", my_place="cafe") is True
    assert is_replyable("MSG_PUBLIC", PUB, "P003", my_place="market") is False   # 不同场
    assert is_replyable("MSG_PUBLIC", PUB, "P003", my_place=None) is False       # 缺我的地点 ⇒ 不猜


def test_on_author_cannot_reply_self(monkeypatch):
    monkeypatch.setenv(PR.ENV, "1")
    assert is_replyable("MSG_PUBLIC", PUB, "P002", my_place="cafe") is False


def test_on_missing_place_ctx_not_replyable(monkeypatch):
    monkeypatch.setenv(PR.ENV, "1")
    bare = {"author": "P002", "participants": ["P002"]}          # 旧日志无 place_ctx
    assert is_replyable("MSG_PUBLIC", bare, "P003", my_place="cafe") is False


# ------------------------------------------------------------ 4) 成员判据
def test_on_participant_can_reply_even_if_elsewhere(monkeypatch):
    monkeypatch.setenv(PR.ENV, "1")
    pub = dict(PUB, participants=["P002", "P003"])
    assert is_replyable("MSG_PUBLIC", pub, "P003", my_place="market") is True


# ------------------------------------------------------------ 5) 回话 scope
def test_scope_for_public_stays_global():
    assert PR.scope_for("MSG_PUBLIC") == "global"
    assert PR.scope_for("MSG_DM") == "private"
    assert PR.scope_for("MSG_GROUP") == "place_group"
