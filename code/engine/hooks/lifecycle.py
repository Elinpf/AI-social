"""Phase 4.4–4.8 生命周期层 hook（T61：死亡/续命以「流动性」为基准）。

契约（kernel-dev 交接 + ADR-08，不可违反）：
  fn(state, round_no, ctx) -> list[EventSpec]
  - 纯函数：相同 (state, round_no, ctx) 恒返回相同事件；**不直写 state**；
  - 随机只经 ctx.rng(stream_id, seq, n)（本模块**不掷骰子**：判定全确定性）；
  - 只返回事件，由中央裁决器 Arbiter 折叠；本回合任一 hook 抛异常 → 整回合回滚。

顺序（X2 冻结）：4.4 apply_metabolism → 4.5 apply_penalty → 4.6 check_lifecycle
            → 4.7 resolve_revival → 4.8 check_death。

判定基准（T61，用户拍板 A）：**流动性 L = 可动用现金 cash**。
  - 判死：`L < liquid_trigger_mu`（不足以支付下一回合生存开销）**且** `not can_borrow`
    （无法获得新增流动性：授信为 0 / 已有存量未偿 / 逾期），**连续 N_death 回合**
    → near_death → dead；超冻结窗 K_exit → terminated。
  - **允许负净值长期存活**：只看 L，不看 net_worth（net_worth 仅记录/惩罚）。
  - 续命：由 **econ 4.2** 按确定性授信放贷（`LOAN_ISSUED` → cash↑ debt↑）；lifecycle **不自己放贷**，
    只读流动性态、据 `can_borrow` 判「能否获得新增流动性」。
  - 复活：dead 且冻结窗 K_exit 内 `L ≥ liquid_sustain_mu` → AGENT_REVIVED（复活费 + C_cool）。
  - 安全阀：保持可开关 + `flag=rescue`（口径按 v1/02 §4.3）。

统一接口（T61×T62，Leader 定）：流动性视图（cash/deposits/debt/credit_limit/overdue）是
`state.cash/deposits/loans/event_index` 的**确定性函数**，**不新增 state 字段**；由 econ-dev 的
`engine/liquidity.py` **单一权威**提供 —— 本模块直接消费其 `credit_limit()/can_borrow()` 与
`resolve_params()`（同一份参数，避免口径分叉）。

跨回合状态（c / freeze_start / cool_left）不落 state：
  * 每回合为每个未 terminated 的 Agent 产出 `METABOLISM`，payload 附 `liquid`（L）、
    `distress`（本回合是否濒死不可贷）、`credit_limit`、`can_borrow`、`count_c`；历史从
    `state.event_index` 重建；冻结起点复用 `AGENT_DIED` 折出的 `death_round`；复活冷却由
    `AGENT_REVIVED` 回合推出。首跑最终状态只由既有事件 fold 决定 → replay 逐位一致。

配置：`policy.lifecycle`（生命周期档，指纹内）+ `policy.economy`（共享流动性参数：`liquid_trigger_mu`
默认 200、`liquid_sustain_mu` 默认 600、`loan_max_debt_mu` 等）。键名大小写不敏感；运行时
`config["lifecycle"]`/`config["economy"]` 可临时覆盖（不属指纹）。
"""

from __future__ import annotations

from ..constants import PHASE_ARBITRATE
from ..events import spec
from ..state import LEGAL_STATUS_EDGES, STATUS_WHITELIST, money_total

try:  # 共享流动性/授信模块（econ-dev owner，T62）
    from .. import liquidity as _liq  # type: ignore
except Exception:  # pragma: no cover
    _liq = None

# ---- 事件类型常量（均为 engine/events.py 已登记、replay 已注册折叠器）----
_T_METABOLISM = "METABOLISM"
_T_PENALTY = "PENALTY_APPLIED"
_T_STATE_CHANGE = "STATE_CHANGE"
_T_DIED = "AGENT_DIED"
_T_REVIVED = "AGENT_REVIVED"
_T_REVIVE_FEE = "REVIVE_FEE_PAID"
_T_MINTED = "MONEY_MINTED"
_T_ENDOW = "INIT_ENDOW"

_FLAG_CHEAT = frozenset({"wash", "cycle", "self", "mule"})
_TX_TYPES = ("TRANSFER", "MARKET_TRADE")

#: 生命周期默认参数（v1/02 §7 + T61）
DEFAULTS = {
    "ENABLED": False,
    "METABOLISM_MU": 200,          # m = 2 CR/回合（生存开销主项）
    "N_DEATH": 3,                  # 连续「濒死不可贷」回合数
    "K_EXIT": 6,                   # 死亡冻结 / 退出窗口
    "REVIVE_FEE_MU": 1000,
    "C_COOL": 5,
    "PENALTY_BP": 10000,
    "P8_ENABLED": False,           # 复活期代谢加速（默认关）
    "P8_NUM": 3,
    "P8_DEN": 2,
    "SAFETY_ENABLED": True,
    "RESCUE_ENABLED": True,
    "RHO_MIN_BP": 6000,
    "D_BURST": 3,
    "W_RESCUE": 5,
    "W_PAUSE": 3,
    "RESCUE_GRANT_MU": 2000,
    # 流动性参数兜底（权威在 liquidity.resolve_params）
    "LIQUID_TRIGGER_MU": 200,
    "LIQUID_SUSTAIN_MU": 600,
    # 世界货币地板（M≥μ_floor 硬不变量；销毁点按世界预算钳制，T91-P1）
    "MU_FLOOR_MU": 0,
}


def _mu_floor(ctx, cfg: dict) -> int:
    """世界货币地板 μ_floor（缺省 0）。权威来源 `policy.money_floor_mu`；
    兼容 `policy.lifecycle.mu_floor_mu` / 运行时 `config["lifecycle"]`、`config["economy"]`。
    容忍 policy 键为 `{"default":...}` 结构或裸值。"""
    def _num(v, d=0):
        if isinstance(v, dict):
            v = v.get("default", d)
        try:
            return int(v)
        except (TypeError, ValueError):
            return int(d)

    floor = _num(cfg.get("MU_FLOOR_MU", 0), 0)
    raw = getattr(ctx, "config", None)
    if isinstance(raw, dict):
        pol = raw.get("policy")
        if isinstance(pol, dict):
            if pol.get("money_floor_mu") is not None:
                floor = _num(pol.get("money_floor_mu"), floor)
            if isinstance(pol.get("economy"), dict) and \
                    pol["economy"].get("money_floor_mu") is not None:
                floor = _num(pol["economy"].get("money_floor_mu"), floor)
        for sec in (raw.get("lifecycle"), raw.get("economy")):
            if isinstance(sec, dict):
                for k in ("MU_FLOOR_MU", "mu_floor_mu"):
                    if sec.get(k) is not None:
                        floor = _num(sec.get(k), floor)
    return floor


def _burn_flags(rescue: bool, floor_hit: bool):
    """销毁点系统标签：`rescue`（救助期）/ `floor`（世界地板抑制）；兼容标量 `flag`。"""
    fl = []
    if rescue:
        fl.append("rescue")
    if floor_hit:
        fl.append("floor")
    return fl, (fl[0] if fl else None)


# ====================================================================== 配置
def _cfg(ctx) -> dict:
    """生命周期档：DEFAULTS ← policy.lifecycle ← 运行时 lifecycle。"""
    out = dict(DEFAULTS)
    raw = getattr(ctx, "config", None)
    if isinstance(raw, dict):
        pol = raw.get("policy")
        if isinstance(pol, dict):
            sec = pol.get("lifecycle")
            if isinstance(sec, dict):
                for k, v in sec.items():
                    if not str(k).startswith("_"):
                        out[str(k).upper()] = v
        rt = raw.get("lifecycle")
        if isinstance(rt, dict):
            for k, v in rt.items():
                if not str(k).startswith("_"):
                    out[str(k).upper()] = v
    return out


def _lparams(ctx) -> dict:
    """流动性/授信参数（单一来源：liquidity.resolve_params；缺失时从 config 兜底）。"""
    if _liq is not None and hasattr(_liq, "resolve_params"):
        try:
            return _liq.resolve_params(ctx)
        except Exception:
            pass
    p = {"liquid_trigger_mu": DEFAULTS["LIQUID_TRIGGER_MU"],
         "liquid_sustain_mu": DEFAULTS["LIQUID_SUSTAIN_MU"],
         "loan_max_debt_mu": 10000, "credit_ltv_bp": 6000, "loan_ltv_bp": 6000}
    raw = getattr(ctx, "config", None)
    if isinstance(raw, dict):
        pol = raw.get("policy")
        if isinstance(pol, dict):
            for section in ("economy", "lifecycle"):
                sec = pol.get(section)
                if isinstance(sec, dict):
                    for k, v in sec.items():
                        if not str(k).startswith("_"):
                            p[str(k).lower()] = v
        econ = raw.get("economy")
        if isinstance(econ, dict):
            for k, v in econ.items():
                if not str(k).startswith("_"):
                    p[str(k).lower()] = v
    return p


def effective_preset(ctx) -> dict:
    cfg = _cfg(ctx)
    lp = _lparams(ctx)
    cfg["LIQUID_TRIGGER_MU"] = int(lp.get("liquid_trigger_mu", cfg["LIQUID_TRIGGER_MU"]))
    cfg["LIQUID_SUSTAIN_MU"] = int(lp.get("liquid_sustain_mu", cfg["LIQUID_SUSTAIN_MU"]))
    return {k: cfg[k] for k in sorted(cfg)}


def _enabled(ctx) -> bool:
    return bool(_cfg(ctx).get("ENABLED"))


def _trigger(params: dict, cfg: dict) -> int:
    return int(params.get("liquid_trigger_mu", cfg["LIQUID_TRIGGER_MU"]))


def _sustain(params: dict, cfg: dict) -> int:
    return int(params.get("liquid_sustain_mu", cfg["LIQUID_SUSTAIN_MU"]))


# ====================================================================== 流动性接口
def _credit_limit(state, aid: str, round_no: int, params: dict) -> int:
    if _liq is not None:
        try:
            return int(_liq.credit_limit(state, aid, round_no, params))
        except Exception:
            pass
    return 0


def _can_borrow(state, aid: str, round_no: int, params: dict) -> bool:
    if _liq is not None:
        try:
            return bool(_liq.can_borrow(state, aid, round_no, params))
        except Exception:
            pass
    return False


# ====================================================================== 只读工具
def _status(state, aid: str) -> str:
    return str(state.agents.get(aid, {}).get("status", "alive"))


def _liquid(state, aid: str) -> int:
    return int(state.cash.get(aid, 0))


def _agent_ids(state) -> list:
    return sorted(state.agents.keys())


def _events_of_round(state, round_no: int, types=None) -> list:
    out = []
    for rec in state.event_index.values():
        if int(rec.get("round", -1)) != int(round_no):
            continue
        if types is not None and rec.get("type") not in types:
            continue
        out.append(rec)
    out.sort(key=lambda r: int(r.get("seq", 0)))
    return out


def _distress_series_all(state, upto_round: int) -> dict:
    """一次遍历：{agent_id: {round: {"d": bool(distress), "L": liquid}}}。"""
    out: dict = {}
    for rec in state.event_index.values():
        if rec.get("type") != _T_METABOLISM:
            continue
        r = int(rec.get("round", -1))
        if r > int(upto_round):
            continue
        p = rec.get("payload", {}) or {}
        aid = p.get("agent_id")
        if aid is None:
            continue
        out.setdefault(aid, {})[r] = {"d": bool(p.get("distress", False)),
                                      "L": int(p.get("liquid", 0))}
    return out


def _flagged_inflow_map(state, round_no: int) -> dict:
    m: dict = {}
    for rec in state.event_index.values():
        if int(rec.get("round", -1)) != int(round_no):
            continue
        t = rec.get("type")
        if t not in _TX_TYPES:
            continue
        p = rec.get("payload", {}) or {}
        to = p.get("to") if t == "TRANSFER" else p.get("seller")
        if to is None:
            continue
        if set(p.get("flags") or ()) & _FLAG_CHEAT:
            m[to] = m.get(to, 0) + int(p.get("amount", 0))
    return m


def _flagged_inflow(state, aid: str, round_no: int) -> int:
    return int(_flagged_inflow_map(state, round_no).get(aid, 0))


def _count_from_flags(hist: dict, now, sustain: int) -> int:
    """由 {round:{"d","L"}} 序列（+本回合 now）按流动性口径计算连续濒死计数 c。

    L ≥ sustain → 清零；distress → 递增；其余（可支付或可贷）→ 递减（滞回，防抖动）。
    """
    c = 0
    for r in sorted(hist):
        L = int(hist[r]["L"])
        d = bool(hist[r]["d"])
        if L >= sustain:
            c = 0
        elif d:
            c += 1
        else:
            c = max(0, c - 1)
    if now is not None:
        L = int(now["L"])
        d = bool(now["d"])
        if L >= sustain:
            c = 0
        elif d:
            c += 1
        else:
            c = max(0, c - 1)
    return c


def _count_c(state, aid: str, round_no: int, cfg: dict, params: dict) -> int:
    return _count_from_flags(_distress_series_all(state, round_no).get(aid, {}), None,
                             _sustain(params, cfg))


def _bucket(L: int, distress: bool, trigger: int, sustain: int) -> str:
    if distress:
        return "near_death"          # L 见底且借不到 → 濒死
    if L < sustain:
        return "warning"
    return "alive"


def _last_round_of(state, pred):
    last = None
    for rec in state.event_index.values():
        if pred(rec):
            r = int(rec.get("round", -1))
            if last is None or r > last:
                last = r
    return last


def _rescue_last_round(state):
    return _last_round_of(state, lambda rec: (
        rec.get("type") == _T_MINTED
        and (rec.get("payload", {}) or {}).get("reason") == "rescue"))


def _rescue_active(state, round_no: int, cfg: dict) -> bool:
    if not cfg["SAFETY_ENABLED"] or not cfg["RESCUE_ENABLED"]:
        return False
    last = _rescue_last_round(state)
    return last is not None and 0 <= int(round_no) - last < int(cfg["W_RESCUE"])


def _death_paused(state, round_no: int, cfg: dict) -> bool:
    if not cfg["SAFETY_ENABLED"]:
        return False
    per_round: dict = {}
    for rec in state.event_index.values():
        if rec.get("type") == _T_DIED:
            r = int(rec.get("round", -1))
            per_round[r] = per_round.get(r, 0) + 1
    for r, n in per_round.items():
        if n >= int(cfg["D_BURST"]) and 0 <= int(round_no) - r < int(cfg["W_PAUSE"]):
            return True
    return False


def _revived_round(state, aid: str):
    return _last_round_of(state, lambda rec: (
        rec.get("type") == _T_REVIVED
        and (rec.get("payload", {}) or {}).get("agent_id") == aid))


def _cool_left(state, aid: str, round_no: int, cfg: dict) -> int:
    r0 = _revived_round(state, aid)
    if r0 is None:
        return 0
    return max(0, int(cfg["C_COOL"]) - (int(round_no) - int(r0)))


def _freeze_start(state, aid: str):
    dr = state.agents.get(aid, {}).get("death_round")
    if dr is not None:
        return int(dr)
    return _last_round_of(state, lambda rec: (
        rec.get("type") == _T_DIED
        and (rec.get("payload", {}) or {}).get("agent_id") == aid))


# ====================================================================== 迁移守卫
def _assert_legal_edge(frm: str, to: str) -> None:
    if frm not in STATUS_WHITELIST or to not in STATUS_WHITELIST:
        raise ValueError(f"生命周期非法状态（不在白名单）：{frm!r} -> {to!r}")
    if frm != to and (frm, to) not in LEGAL_STATUS_EDGES:
        raise ValueError(f"生命周期非法迁移：{frm!r} -> {to!r}（非法边）")


def _state_change(round_no, aid, frm, to, reason, L, c, **extra):
    if frm == to:
        return None
    _assert_legal_edge(frm, to)
    p = {"agent_id": aid, "from": frm, "to": to, "reason": reason,
         "liquid": int(L), "count_c": int(c)}
    p.update(extra)
    return spec(round_no, PHASE_ARBITRATE, aid, _T_STATE_CHANGE, p)


# ================================================================== 4.4 代谢
def apply_metabolism(state, round_no, ctx):
    """4.4：每回合固定代谢扣减（生存开销主项、销毁出口）→ METABOLISM。

    为每个未 terminated 的 Agent 产出 METABOLISM；payload 附流动性量（`liquid`=L、
    `distress`、`credit_limit`、`can_borrow`、`count_c`），供后续 hook 与重放读取
    （fold 只消费 agent_id/amount）。救助窗口代谢减半；P8 开启时复活期上浮（默认关）。
    """
    if not _enabled(ctx):
        return []
    cfg = _cfg(ctx)
    params = _lparams(ctx)
    trigger = _trigger(params, cfg)
    sustain = _sustain(params, cfg)
    rescue = _rescue_active(state, round_no, cfg)
    m = int(cfg["METABOLISM_MU"])
    if rescue:
        m //= 2
    # 世界级货币地板（T91-P1）：销毁只能在世界货币预算内进行；`budget=max(0, M-μ_floor)`，
    # 按 agent_id 升序分配；**个体 cash 允许变负**（v1/02 §0），故本处不钳个体。
    budget = max(0, money_total(state) - _mu_floor(ctx, cfg))
    hist_all = _distress_series_all(state, round_no - 1)
    out = []
    for aid in _agent_ids(state):
        st = _status(state, aid)
        if st == "terminated":
            continue
        desired = m
        if cfg["P8_ENABLED"] and st == "revived":
            desired = desired * int(cfg["P8_NUM"]) // int(cfg["P8_DEN"])
        applied = min(desired, budget) if budget > 0 else 0   # 世界预算钳制
        floor_hit = applied < desired
        budget -= applied
        L = _liquid(state, aid) - applied                     # 代谢后流动性（可为负）
        credit = _credit_limit(state, aid, round_no, params)
        can_borrow = _can_borrow(state, aid, round_no, params)
        distress = (L < trigger) and (not can_borrow)
        now = {"L": L, "d": distress}
        c = _count_from_flags(hist_all.get(aid, {}), now, sustain)
        fl, flag = _burn_flags(rescue, floor_hit)
        out.append(spec(round_no, PHASE_ARBITRATE, aid, _T_METABOLISM, {
            "agent_id": aid, "amount": int(applied), "desired": int(desired),
            "liquid": L, "distress": distress, "can_borrow": can_borrow,
            "credit_limit": credit, "count_c": c, "status_before": st,
            "equity": int(state.net_worth(aid)) - int(applied),  # 仅记录（非判据）
            "round": int(round_no),
            "flags": fl, "flag": flag,
        }))
    return out


# ================================================================== 4.5 惩罚
def apply_penalty(state, round_no, ctx):
    """4.5：作弊罚没 → PENALTY_APPLIED（v1/02 §3.3）。

    对本回合被标记 {wash,cycle,self,mule} 的流入按 `penalty_bp` 计罚并销毁
    （kind="cheat_fine"）。债务侧的利率惩罚/抵押没收/坏账罚由 econ 4.2 主责
    （`INTEREST_CHARGED`/`LOAN_DEFAULT`/`PENALTY_APPLIED`），lifecycle 不重复扣账。
    """
    if not _enabled(ctx):
        return []
    cfg = _cfg(ctx)
    fine_bp = int(cfg["PENALTY_BP"])
    # 世界级货币地板（T91-P1）：罚没同属销毁通道，受同一世界预算约束；个体 cash 可为负。
    budget = max(0, money_total(state) - _mu_floor(ctx, cfg))
    flagged = _flagged_inflow_map(state, round_no)
    out = []
    for aid in _agent_ids(state):
        if _status(state, aid) == "terminated":
            continue
        base = flagged.get(aid, 0)
        if base <= 0:
            continue
        desired = base * fine_bp // 10000
        if desired <= 0:
            continue
        applied = min(desired, budget) if budget > 0 else 0   # 世界预算钳制
        floor_hit = applied < desired
        budget -= applied
        fl, flag = _burn_flags(False, floor_hit)
        out.append(spec(round_no, PHASE_ARBITRATE, "SYSTEM", _T_PENALTY, {
            "agent_id": aid, "kind": "cheat_fine", "amount": int(applied),
            "desired": int(desired), "base": int(base),
            "flags": sorted(set(_FLAG_CHEAT) | set(fl)), "flag": flag,
            "reason": "flagged_inflow",
        }))
    return out


# ============================================================ 4.6 状态机
def check_lifecycle(state, round_no, ctx):
    """4.6：6 态状态机（流动性口径）→ STATE_CHANGE。

    L ≥ sustain → alive；trigger ≤ L < sustain → warning；`L < trigger 且借不到` → near_death。
    连续濒死计数 + 滞回（L≥sustain 清零）。dead/terminated 迁移在 4.7/4.8。
    """
    if not _enabled(ctx):
        return []
    cfg = _cfg(ctx)
    params = _lparams(ctx)
    trigger = _trigger(params, cfg)
    sustain = _sustain(params, cfg)
    series_all = _distress_series_all(state, round_no)
    out = []
    for aid in _agent_ids(state):
        st = _status(state, aid)
        if st in ("dead", "terminated"):
            continue
        ser = series_all.get(aid, {})
        cur = ser.get(int(round_no))
        if cur is None:
            L0 = _liquid(state, aid)
            can = _can_borrow(state, aid, round_no, params)
            cur = {"L": L0, "d": (L0 < trigger) and (not can)}
        L = int(cur["L"])
        distress = bool(cur["d"])
        c = _count_from_flags(ser, None, sustain)
        if st == "revived":
            if _cool_left(state, aid, round_no, cfg) <= 0 and L >= sustain:
                sc = _state_change(round_no, aid, "revived", "alive",
                                   "cool_done_solvent", L, c)
                if sc:
                    out.append(sc)
            continue
        target = _bucket(L, distress, trigger, sustain)
        if target == st:
            continue
        reason = {"alive": "solvent", "warning": "low_liquidity",
                  "near_death": "illiquid_no_credit"}[target]
        sc = _state_change(round_no, aid, st, target, reason, L, c)
        if sc:
            out.append(sc)
    return out


# ============================================================ 4.7 复活
def resolve_revival(state, round_no, ctx):
    """4.7：冻结窗内 L 恢复到可持续阈值 → 复活（AGENT_REVIVED / REVIVE_FEE_PAID）。

    `dead`（旧称 `DECEASED`）且 now-freeze_start < K_exit 且 `L ≥ liquid_sustain_mu`
    （借到钱 / 他人有效转入 / 救助）→ 进入 REVIVING，收复活费，持续 C_cool 冷却。
    """
    if not _enabled(ctx):
        return []
    cfg = _cfg(ctx)
    params = _lparams(ctx)
    sustain = _sustain(params, cfg)
    series_all = _distress_series_all(state, round_no)
    out = []
    for aid in _agent_ids(state):
        if _status(state, aid) != "dead":
            continue
        fs = _freeze_start(state, aid)
        if fs is None:
            continue
        window = int(round_no) - int(fs)
        if window < 0 or window >= int(cfg["K_EXIT"]):
            continue
        L = _liquid(state, aid)
        if L < sustain:
            continue
        c = _count_from_flags(series_all.get(aid, {}), None, sustain)
        sc = _state_change(round_no, aid, "dead", "revived", "resupplied", L, c,
                           freeze_rounds=int(window))
        if sc:
            out.append(sc)
        out.append(spec(round_no, PHASE_ARBITRATE, aid, _T_REVIVED, {
            "agent_id": aid, "cost": int(cfg["REVIVE_FEE_MU"]),
            "via": "liquidity_restored", "liquid": int(L), "freeze_rounds": int(window),
        }))
        fee = int(cfg["REVIVE_FEE_MU"])
        if fee > 0:
            out.append(spec(round_no, PHASE_ARBITRATE, aid, _T_REVIVE_FEE, {
                "agent_id": aid, "amount": fee, "pool": "bank_reserve",
            }))
    return out


# ============================================================ 4.8 判死
def check_death(state, round_no, ctx):
    """4.8：最终判死 + 永久退出 + 全局安全阀（流动性口径）。

    ① 判死：存活侧 Agent 连续 `N_death` 回合 `distress`（L<trigger 且借不到）→ AGENT_DIED；
       单回合死亡 ≥ D_burst 时暂停判死 W_pause 回合。
    ② 退出：dead 且 now-freeze_start ≥ K_exit → terminated。
    ③ 安全阀：存活率（非 terminated 占比，v1/02 §4.3）< ρ_min → 世界救助（打 flag=rescue）。
    """
    if not _enabled(ctx):
        return []
    cfg = _cfg(ctx)
    params = _lparams(ctx)
    trigger = _trigger(params, cfg)
    sustain = _sustain(params, cfg)
    series_all = _distress_series_all(state, round_no)
    paused = _death_paused(state, round_no, cfg)
    out = []

    def _views(aid):
        ser = series_all.get(aid, {})
        cur = ser.get(int(round_no))
        if cur is None:
            L0 = _liquid(state, aid)
            can = _can_borrow(state, aid, round_no, params)
            cur = {"L": L0, "d": (L0 < trigger) and (not can)}
        return int(cur["L"]), bool(cur["d"]), ser

    # ① 判死
    for aid in _agent_ids(state):
        st = _status(state, aid)
        if st in ("dead", "terminated", "revived"):
            continue
        L, distress, ser = _views(aid)
        c = _count_from_flags(ser, None, sustain)
        if c >= int(cfg["N_DEATH"]) and distress and not paused:
            sc = _state_change(round_no, aid, st, "dead", "illiquid_no_credit_N", L, c)
            if sc:
                out.append(sc)
            out.append(spec(round_no, PHASE_ARBITRATE, aid, _T_DIED, {
                "agent_id": aid, "death_round": int(round_no),
                "cause": "illiquid_no_credit_N", "liquid": int(L),
                "count_c": int(c), "from": st,
            }))

    # ② 永久退出（超冻结窗口）
    for aid in _agent_ids(state):
        if _status(state, aid) != "dead":
            continue
        fs = _freeze_start(state, aid)
        if fs is None:
            continue
        if int(round_no) - int(fs) >= int(cfg["K_EXIT"]):
            L, distress, ser = _views(aid)
            c = _count_from_flags(ser, None, sustain)
            sc = _state_change(round_no, aid, "dead", "terminated",
                               "grace_expired", L, c,
                               freeze_rounds=int(round_no) - int(fs))
            if sc:
                out.append(sc)

    # ③ 全局安全阀：存活率低水位 → 世界救助
    if cfg["SAFETY_ENABLED"] and cfg["RESCUE_ENABLED"]:
        total = len(state.agents)
        if total > 0:
            non_term = sum(1 for a in state.agents.values()
                           if a.get("status") != "terminated")
            rate_bp = non_term * 10000 // total
            if rate_bp < int(cfg["RHO_MIN_BP"]) and not _rescue_active(state, round_no, cfg):
                grant = int(cfg["RESCUE_GRANT_MU"])
                survivors = [a for a in _agent_ids(state)
                             if _status(state, a) != "terminated"]
                if grant > 0 and survivors:
                    out.append(spec(round_no, PHASE_ARBITRATE, "SYSTEM", _T_MINTED, {
                        "amount": grant * len(survivors), "reason": "rescue",
                        "flag": "rescue",
                    }))
                    for aid in survivors:
                        out.append(spec(round_no, PHASE_ARBITRATE, "SYSTEM", _T_ENDOW, {
                            "agent_id": aid, "amount": grant, "flag": "rescue",
                        }))
    return out
