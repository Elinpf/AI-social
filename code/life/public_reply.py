"""D2.10 公开场合接话（PUBLIC reply）——**开关 + 纯函数判据**，默认关。

问题（可复算事实，见 `v2/evidence/d210_public_reply_prep.md`）：
基线批 `run_d27_C_n16r60_seed42` 的 **55 条 `MSG_PUBLIC` 全部** `participants` 长度 = 1、
`reply_to` = null ⇒ 公开场合只有「当众自言自语」，没有任何机制让旁人接一句。
而**能力本身是有的**：`MSG_DM` 侧 `S-4_reply_pointer_coverage = 1.0`（341/341）。
⇒ 缺的是**渠道接线**，不是能力缺失。

单变量口径（本模块只做判据，不产生任何措辞/世界态后果）：
  * OFF（`HITT_PUB_REPLY` 缺省/`0`）⇒ 本模块全部函数不得把任何 PUBLIC 判为可回复，
    调用方走**原路径**（`_pick_reply_target` 的 `ev.type in ("MSG_DM","MSG_GROUP")` 不变）；
  * ON（`=1`）⇒ 追加一条判据：**同场旁人可接**——
    `author != me` 且（`me in participants` 或 `payload["place_ctx"] == 我的计划地点`）。

设计取舍（写死，跑前不改）
  * **不改 `MSG_PUBLIC` 既有 `place` 键**（它现在是 `None`，可见性是 global）⇒
    发起人地点用**新增键** `place_ctx` 携带，缺省 None ⇒ 不打键 ⇒ OFF 日志逐字节不变；
  * `place_ctx` 取**计划地点**（`_plan_slots[slot_id]["place"]`，确定性、两相位都可得），
    不读别人的私有状态 ⇒ 不引入新的私有依赖（D2.3 的教训：判据的输入必须在计算时刻存在）；
  * **不做 LLM 判定**：谁能接话完全由确定性规则决定，措辞仍由既有 dialogue 调用生成。
"""
from __future__ import annotations

import os

ENV = "HITT_PUB_REPLY"


def enabled() -> bool:
    """`HITT_PUB_REPLY`：缺省/`0` ⇒ 关（行为与 master 逐字节一致）；`1` ⇒ 开；其它值抛错（不静默）。"""
    raw = (os.environ.get(ENV, "") or "").strip()
    if raw in ("", "0"):
        return False
    if raw == "1":
        return True
    raise ValueError(f"{ENV}={raw!r}：只接受 0(关闭) / 1(开启)")


def same_place(payload: dict, my_place: str | None) -> bool:
    """发起人与我是否同场：只比 `place_ctx` 与我的计划地点；任一缺失 ⇒ False（不猜）。"""
    p = payload or {}
    theirs = p.get("place_ctx")
    return bool(theirs) and bool(my_place) and theirs == my_place


def replyable(payload: dict, me: str, my_place: str | None) -> bool:
    """ON 判据（纯函数）：我是不是「这条公开话」的**同场旁人**。

    - `author == me` ⇒ False（自己不能接自己）；
    - `me in participants` ⇒ True（已被点名的成员，沿用 GROUP 的既有语义）；
    - 否则只看**同场**：`place_ctx == my_place`。
    """
    p = payload or {}
    author = p.get("author") or p.get("from")
    if not author or author == me:
        return False
    if me in (p.get("participants") or []):
        return True
    return same_place(p, my_place)


def scope_for(ev_type: str) -> str:
    """回复时的 scope：PUBLIC 线程的回话**仍走 global**（不能落成 place_group）。"""
    return "private" if ev_type == "MSG_DM" else (
        "global" if ev_type == "MSG_PUBLIC" else "place_group")
