"""R41 公开面接话臂（public-talk reply）：让「当着在场的人说出口的话」能被在场者接上。

## 缺口（可复算的事实，不是推测）

`MSG_PUBLIC` 当前**每条都是独白**：在 `v2/evidence/r38_f3_batch/on/run.jsonl` 上实测
（命令见 `reports/r41-*`）：

  * `MSG_PUBLIC = 24` 条，`demonstrates thread_id` 24 个各不重复、`turn_index` 全为 0、
    `reply_to` 全为 null ⇒ `tools/public_talk/public_talk_metrics.py` 判
    `msg_graph_degree.pub_in_degree_total = 0 / pub_out_degree_reply_nonnull = 0`（孤立节点）。
  * 根因在**类型白名单**，不在生成质量：
    - `life/dialogue_threads.py::is_replyable()` 只认 `MSG_DM` / `MSG_GROUP`，`MSG_PUBLIC` 直接 False；
    - `life/agent.py::_thread_max_turn` / `_pick_reply_target` / `_thread_history` 三处的
      类型白名单同样只有 `("MSG_DM", "MSG_GROUP")`；
    - 即便勉强回一条公开消息，`_send_reply` 也会把 scope 投成 `place_group`（错频道）。
  ⇒ 公开面**结构上不存在接话机制**（与 R24 的 `BASELINE-DESCRIPTIVE` 结论一致）。

## 本臂只做一件事

把「公开消息」纳入回复候选，并**在有界条件下**发出第二条公开消息接住它。
措辞仍由 LLM 产出（复用既有 `_reply_prompt`），本模块**不调 LLM、不改世界态、不发事件**，
只提供确定性判据与配额。

## 有界（四条硬上限，全部写死为模块常量，不塞进 `config/`）

  ① `MAX_PER_AGENT_PER_SLOT = 1`：同一 agent 同一 slot 至多接 1 条公开话；
  ② `MAX_PER_PLACE_PER_SLOT = 2`：同一 `day` + 同一 `slot` + 同一 place 内**公开消息总数**
     至多 2 条（防止 16 个 agent 同处一地时瞬间刷屏；公开消息的 place 由 R41 在
     `orchestration/integration.py` 里 additive 补上，见报告「顺带修复」一节）。
     **R43 修复**：这条不再由调用方各自数一遍，唯一判定函数是 `place_quota_gate()`，
     唯一**强制**点是 `integration._do_social()` 的 `scope=="global"` 分支（写入口、串行、
     含本回合 arbiter 缓冲）。R41 把它放在 `agent._pick_reply_target()` 里、对着
     **决策时点可见集**判 ⇒ ①首发公开消息完全不经过它；②同轮他人刚落的消息不可见 ⇒
     多个接话者各自看到「1 < 2」同时放行（实测越界见 `reports/R41b-public-talk-verify.md` §2.3）。
  ③ **在场者 > 0**：复用 `agent.py::_co_present_peers()`（`PLACE_ARRIVED` 的 place_local 可见性，
     同场偶遇臂的现成实现）。独处里的「公开发言」是自言自语，是噪声不是生活气息 ⇒ 不接；
  ④ 仍受既有上限约束：`max_messages_per_slot` / `max_turns_per_round` / `max_turns`。

## 开关与逐字节等价

  * env `HITT_DIALOGUE_PUBLIC_REPLY` ∈ {1,true,yes,on} → **开**；其它任何取值（含空串/拼错）→ 关；
  * **关闭（默认）**：`enabled()` 为假 ⇒ 调用方三处白名单、scope 映射、place 注入**全部走原路径**
    ⇒ 事件流与提示词与接入前**逐字节一致**（由 `code/life/tests/test_r41_public_talk.py` 守住）。
  * 本模块**不进** `engine/version.py::FINGERPRINT_FILES` ⇒ 开/关都不改 `engine_version` 指纹。
"""
from __future__ import annotations

import os

#: 臂开关（默认 OFF）。
ENV = "HITT_DIALOGUE_PUBLIC_REPLY"

#: ① 同一 agent 同一 slot 至多接几条公开话
MAX_PER_AGENT_PER_SLOT = 1
#: ② 同一 place 同一 slot 内公开消息总数上限（含首发与接话）
MAX_PER_PLACE_PER_SLOT = 2

#: 信号版本（写进 ctx 审计字段，便于按版本复算）
VERSION = "r41/1"

_ON = {"1", "true", "yes", "on"}


def enabled() -> bool:
    """臂开关：**只有** {1,true,yes,on} 算开；其它任何取值（含空串/拼错）一律关。"""
    return os.environ.get(ENV, "").strip().lower() in _ON


def place_of(payload: dict) -> str | None:
    """取一条消息的 place（R41 起 `MSG_PUBLIC` 由 integration additive 写入；旧日志为 null）。"""
    p = payload or {}
    v = p.get("place")
    return str(v) if v else None


def author_of(payload: dict) -> str | None:
    """公开消息用 `author`，私信/群聊用 `from`（两套字段都在，缺一不可）。"""
    p = payload or {}
    v = p.get("author") or p.get("from")
    return str(v) if v else None


def is_replyable_public(payload: dict, me: str, my_place: str | None,
                        co_present: list | None) -> bool:
    """这条公开消息是否「值得我当着在场者接一句」。

    四条同时成立才回 True（任何一条不成立 ⇒ False，宁缺毋滥）：
      1. 作者不是我自己（自问自答不是接话）；
      2. 我此刻**有在场同伴**（`co_present` 非空；空 = 独处 ⇒ 不接）；
      3. 消息带 place 且 `place == 我的当前位置`（R41 新增字段；旧日志 place 为 null ⇒ 不接，
         这是**有意的保守**：无法证明同处就不冒充接话，不用 slot/topic 之类顶替）；
      4. 作者与我不同处则不复。（由 3 已覆盖，保留为文档语义）
    """
    p = payload or {}
    author = author_of(p)
    if not author or author == me:
        return False
    if not co_present:
        return False
    pl = place_of(p)
    if not pl or not my_place or pl != str(my_place):
        return False
    return True


#: 场所配额闸版本（写进 DROPPED 审计字段，便于按版本复算）
GATE_VERSION = "r43/1"


def _type_of(ev) -> str:
    """统一取事件类型：兼容 `EventView`（属性）与 `state.event_index` 记录（dict）。"""
    t = getattr(ev, "type", None)
    if t is None and isinstance(ev, dict):
        t = ev.get("type")
    return str(t or "")


def _payload_of(ev) -> dict:
    p = getattr(ev, "payload", None)
    if p is None and isinstance(ev, dict):
        p = ev.get("payload")
    return p or {}


def place_slot_count(records, place: str | None, day=None, slot=None) -> int:
    """**唯一**的场所配额计数（R43）：同一 `place` + 同一 `day` + 同一 `slot` 的 `MSG_PUBLIC` 条数。

    R43 根因修复（R41V-C4 越界的直接原因见 `reports/R41b-public-talk-verify.md` §2.3）：

      * `day` / `slot` 显式入键。R41 的实现只比 `place` 与 `slot`（不区分 `day`），
        却把「同一时段」当键 ⇒ 键粒度与判据不一致；R43 把 `day` 补进键，**键 = 判据**。
      * `records` 既可以是 `WorldState.event_index.values()`（**含本回合 arbiter 缓冲**，
        见 `engine/arbiter.py::emit` → `replay.apply_event` 已写 `event_index`），
        也可以是 agent 侧 `wv.visible_events`（决策时点视图）。
        唯一**强制**点是写入口（`orchestration/integration.py::_do_social`），
        那里的 `event_index` 是串行的、含本回合已放行消息的真源 ⇒ 不会「各自看到 1 条、各自放行」。
      * `place` 为 None ⇒ 无法按场所归一，返回 0（与 R41 一致：不做额外截断）。
      * 旧记录缺 `day` / `slot` 键 ⇒ 该维度视为通配（向后兼容 R41 之前的日志），
        但只要记录带该字段就严格比对 ⇒ 现存日志（`integration` 恒写 `day`/`slot`）比对是精确的。
    """
    if not place:
        return 0
    n = 0
    for ev in records or ():
        if _type_of(ev) != "MSG_PUBLIC":
            continue
        p = _payload_of(ev)
        if place_of(p) != str(place):
            continue
        if day is not None and p.get("day") is not None and str(p.get("day")) != str(day):
            continue
        if slot is not None and p.get("slot") is not None and str(p.get("slot")) != str(slot):
            continue
        n += 1
    return n


def place_quota_gate(records, place: str | None, day=None, slot=None) -> tuple[bool, int]:
    """② 唯一判定函数：`(是否放行, 当前已占条数)`。所有调用点都必须走它，不得各自数一遍。"""
    n = place_slot_count(records, place, day, slot)
    return (n < MAX_PER_PLACE_PER_SLOT, n)


def public_count_at(slot_events, place: str | None, slot_id: str) -> int:
    """R41 兼容包装（不区分 `day`）：等价于 `place_slot_count(..., day=None, slot=slot)`。

    保留它只为不改变既有调用/测试的语义；**判定**请直接用 `place_quota_gate`。
    """
    slot = str(slot_id).split("-", 1)[-1] if slot_id else None
    return place_slot_count(slot_events, place, None, slot)


def place_quota_ok(slot_events, place: str | None, slot_id: str, day=None) -> bool:
    """R41 兼容包装：同 place 同 slot（可选再限 day）公开消息总数是否仍有余额。"""
    slot = str(slot_id).split("-", 1)[-1] if slot_id else None
    return place_quota_gate(slot_events, place, day, slot)[0]


def agent_quota_ok(slot_public_replies: dict, slot_id: str) -> bool:
    """① 本 agent 本 slot 的公开接话配额是否仍有余额。"""
    return int(slot_public_replies.get(slot_id, 0)) < MAX_PER_AGENT_PER_SLOT


def reply_scope(ev_type: str) -> str:
    """回复该类型消息时应投递的 scope（本模块唯一权威）。

    * `MSG_PUBLIC` → `global`（回公开面，落 `MSG_PUBLIC`；不接话时由调用方保证不进入本分支）
    * `MSG_DM`     → `private`
    * 其它（`MSG_GROUP`）→ `place_group`
    """
    if ev_type == "MSG_PUBLIC":
        return "global"
    if ev_type == "MSG_DM":
        return "private"
    return "place_group"


def audit(ev_type: str, co_present: list, place: str | None) -> dict:
    """只追加的审计快照（写进 `ctx.public_reply`；关闭/不产时调用方不写该键）。"""
    return {"v": VERSION, "channel": ev_type, "place": place,
            "co_present": sorted(co_present or [])}
