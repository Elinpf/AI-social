"""T295：`event_index` 读路径增量聚合（派生缓存）。

- **派生、可重建**（由日志/`event_index` 重建）⇒ **不入 `state_hash`**、**不进 `restore()`**。
- 维护点两处（必须一致）：**P6 commit 之后**（`arbiter.commit`）与 **replay 折叠**（`replay.apply_event`）。
- 读取保持 **seq 全序、顺序不变**（与原"全表扫 + 过滤"逐条等价）。
"""

from __future__ import annotations


def note_event(state, rec: dict) -> None:
    """累加进 `events_by_round[round][type]` 与 `seqs_by_type[type]`（seq 升序追加）。"""
    by = state.events_by_round.setdefault(int(rec["round"]), {})
    by.setdefault(rec["type"], []).append(int(rec["seq"]))
    state.seqs_by_type.setdefault(rec["type"], []).append(int(rec["seq"]))
    state.acc_n = getattr(state, "acc_n", 0) + 1
    _note_income(state, rec)   # T328③：收入标量累加器


def _note_income(state, rec: dict) -> None:
    """按 agent 累加每回合净流入（口径同 `liquidity.recent_income`）。"""
    t = rec.get("type")
    if t not in ("TRANSFER", "MARKET_TRADE"):
        return
    from .liquidity import _INCOME_TX_TYPES, _EXCLUDE_FLAGS  # 延迟导入（避免环）
    p = rec.get("payload") or {}
    if t == "TRANSFER":
        frm, to, tt = p.get("from"), p.get("to"), p.get("tx_type", "transfer")
    else:
        frm, to, tt = p.get("buyer"), p.get("seller"), p.get("tx_type", "trade")
    if tt not in _INCOME_TX_TYPES:
        return
    if frm == to or (set(p.get("flags") or []) & _EXCLUDE_FLAGS):
        return
    amt = int(p.get("amount", 0))
    rd = int(rec["round"])
    if to:
        state.income_net.setdefault(to, {}).setdefault(rd, 0)
        state.income_net[to][rd] += amt
    if frm:
        state.income_net.setdefault(frm, {}).setdefault(rd, 0)
        state.income_net[frm][rd] -= amt


def rebuild(state) -> None:
    state.events_by_round.clear()
    state.seqs_by_type.clear()
    state.income_net.clear()
    state.acc_n = 0
    for rec in state.event_index.values():
        note_event(state, rec)


def ensure(state) -> None:
    """自愈/信任判定：

    - **不可信状态**（非 Engine/replay 产出，如单测直接注入/覆盖 `event_index`）⇒ **每次重建**
      （等价全表扫；测试态量小，可接受）；
    - **可信状态**（Engine/replay）⇒ 仅当 `acc_n != len(event_index)` 时重建（防御性）。
    """
    if not getattr(state, "acc_trusted", False):
        rebuild(state)
        return
    if int(getattr(state, "acc_n", 0)) != len(state.event_index):
        rebuild(state)


def seqs_of_round(state, round_no: int, types=None) -> list:
    """该回合的 seq 列表（可选按 type 过滤），**升序**。"""
    ensure(state)
    by = state.events_by_round.get(int(round_no), {})
    if types is None:
        out = [s for lst in by.values() for s in lst]
    else:
        out = [s for t in types for s in by.get(t, [])]
    return sorted(out)


def recs_of_round(state, round_no: int, types=None) -> list:
    return [state.event_index[s] for s in seqs_of_round(state, round_no, types)]


def seqs_of_type(state, type_: str) -> list:
    """全局该 type 的 seq 列表（升序）。"""
    ensure(state)
    return list(state.seqs_by_type.get(type_, []))


def recs_of_type(state, type_: str) -> list:
    return [state.event_index[s] for s in seqs_of_type(state, type_)]


def seqs_of_types(state, types) -> list:
    """多个 type 合并后的 seq 列表（升序）。"""
    ensure(state)
    out = []
    for t in types:
        out.extend(state.seqs_by_type.get(t, []))
    return sorted(out)


def recs_of_types(state, types) -> list:
    return [state.event_index[s] for s in seqs_of_types(state, types)]
