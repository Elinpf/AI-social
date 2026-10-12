"""Phase 4（A 物理层）· `apply_production`：价值创造入口（v2 P1）。
**单位口径（重要）**：商品 `qty` 一律为 **milli-unit（定点）**，`1 unit = 1000 milli-unit`
——`base_rate` 用定点换算（food=2000、material=1000、tool=300、service=1000、art=200 milli，
即 2.0/1.0/0.3/1.0/0.2）；`qty = ⌊base_milli × 技能因子(1000+100·lv) × resource_milli × tool_milli / 1000³⌋`。
库存/配方投入/生存消费（`need_food=1000` milli）/折旧 `delta_mu` 均同口径；`qty` 入 `state_hash` 并被观测指标消费。


契约（同 4.x）：纯函数 `fn(state, round_no, ctx) -> list[EventSpec]`，不直写 state，
金额/数量整数、禁浮点、不调 LLM、emit 守 ADR-08（入本回合缓冲、P6 唯一 append）。

**挂载**：`PHASE4_CHAIN` 首项（`settle_market` 之前）——生产先更新商品库存，4.1 市场再用新库存。

**生产触发（Leader 裁定）**：**确定性映射**——按同回合 `ACTIVITY_COMPLETED` 的「劳动类活动 → good」
（不打 `INTENT.PRODUCE`；属 A 层世界规则）。映射见 `ACTIVITY_GOOD`（可经 `config["production"]` 覆盖）。

**事件（08 §1.2 O 权威字段）**：
  - `PRODUCE`：`{agent_id, good_id, qty, place, recipe, skill_level}`
  - `CONSUME`：`{agent_id, good_id, qty, purpose}`（purpose ∈ {eat, input}）
  - `DEPRECIATE`：`{agent_id, asset_id, delta_mu}`（商品资产：asset_id=good_id、delta_mu=损失单位数）
  - `PRODUCE_OVERFLOW`：`{agent_id, good_id, qty_dropped}`

生产函数/库存/折旧/消耗的**纯逻辑**在 `engine/production.py`（本模块只做「读 state → 产事件」编排）。
"""

from __future__ import annotations

from ..constants import PHASE_ARBITRATE
from ..events import spec
from .. import production as P

P4 = PHASE_ARBITRATE

# 劳动类活动 → 产出商品（确定性；Leader 裁定，A 层世界规则）
ACTIVITY_GOOD: dict[str, list] = {
    "work": ["material", "food"],       # 采集+耕作（material 先，供 food 投入链）
    "skill_practice": ["tool"],         # 练习 → 制具
    # "socialize" 不再产入库商品：改发 SERVICE_DELIVERED（即时交付、inventory-neutral，T278）
    "leisure": ["art"],                 # 休闲 → 艺术品
}

# 即时交付的服务类活动：activity → good（不进货品库存，发 SERVICE_DELIVERED；T278/08 §1.2 V）
ACTIVITY_SERVICE: dict[str, str] = {
    "socialize": "service",
}

_PROD_DEFAULTS = {
    "place_base_milli": 800,   # 场所基础资源丰度
    "need_food_milli": 1000,   # 生存消费 1 单位/回合（milli）
    "depreciate_bp": P.DEFAULTS["depreciate_bp"],
    "cap_milli": P.DEFAULTS["cap_milli"],
}


def _params(ctx) -> dict:
    p = {**P.DEFAULTS, **_PROD_DEFAULTS}
    cfg = getattr(ctx, "config", None)
    if isinstance(cfg, dict):
        sec = cfg.get("production")
        if isinstance(sec, dict):
            for k, v in sec.items():
                if not str(k).startswith("_"):
                    p[str(k)] = v
    # 允许 policy.production（随指纹）覆盖
    try:
        pol = cfg.get("policy", {}).get("production") if isinstance(cfg, dict) else None
        if isinstance(pol, dict):
            for k, v in pol.items():
                if not str(k).startswith("_"):
                    p[str(k)] = v
    except Exception:
        pass
    return p


def _activity_good(params: dict) -> dict:
    m = params.get("activity_good")
    return m if isinstance(m, dict) else ACTIVITY_GOOD


def _labor_completions(state, round_no):
    """本回合已完成的「劳动类」活动（按 seq 全序）。"""
    idx = getattr(state, "event_index", {}) or {}
    out = []
    from ..event_acc import recs_of_round  # T295：读路径增量聚合
    for r in recs_of_round(state, round_no, ("ACTIVITY_COMPLETED",)):
        p = r.get("payload") or {}
        out.append((int(r.get("seq", 0)), p.get("agent_id"), p.get("place"),
                    p.get("activity_type"), p))
    return sorted(out, key=lambda x: x[0])


def _skill_level(state, aid, good) -> int:
    """从 `SKILL_LEVEL_UP` 折叠出 (agent, skill) 当前等级（确定性，默认 0）。"""
    idx = getattr(state, "event_index", {}) or {}
    lv = 0
    from ..event_acc import recs_of_type  # T295：读路径增量聚合
    for r in recs_of_type(state, "SKILL_LEVEL_UP"):
        p = r.get("payload") or {}
        if p.get("agent_id") != aid:
            continue
        sid = str(p.get("skill_id", ""))
        if sid == good or sid.startswith(good):
            lv = max(lv, int(p.get("level_after", 0)))
    return lv


def _real_agents(state):
    return sorted(a for a, d in state.agents.items()
                  if a not in ("MARKET", "BANK", "WORLD", "SYSTEM", "TAX_POOL")
                  and d.get("status") not in ("dead", "terminated"))


def _production_enabled(ctx) -> bool:
    """生产层一等开关（T114）：`policy.production.enabled` / runtime `config.production.enabled`，
    **默认 true**（行为不变）。"""
    cfg = getattr(ctx, "config", None)
    if isinstance(cfg, dict):
        p = cfg.get("production")
        if isinstance(p, dict) and "enabled" in p:
            return bool(p["enabled"])
        pol = cfg.get("policy")
        if isinstance(pol, dict):
            pp = pol.get("production")
            if isinstance(pp, dict) and "enabled" in pp:
                return bool(pp["enabled"])
    return True


def production_enabled_from_config(config) -> bool:
    """供 kernel/fail-loud 复用的配置读取（默认 true）。"""
    class _C:
        pass
    c = _C()
    c.config = config
    return _production_enabled(c)


def _service_enabled(ctx) -> bool:
    """服务即时交付开关（T278）：`policy.service_delivered.enabled` / `config.service_delivered.enabled`，默认 true。"""
    cfg = getattr(ctx, "config", None)
    if isinstance(cfg, dict):
        rt = cfg.get("service_delivered")
        if isinstance(rt, dict) and "enabled" in rt:
            return bool(rt["enabled"])
        pol = cfg.get("policy")
        if isinstance(pol, dict):
            sd = pol.get("service_delivered")
            if isinstance(sd, dict) and "enabled" in sd:
                return bool(sd["enabled"])
    return True


def apply_production(state, round_no, ctx):
    if not _production_enabled(ctx):
        # 显式关闭：零生产事件，但留一条审计（flag=production_disabled）；双账本守恒平凡成立
        return [spec(round_no, P4, "SYSTEM", "DROPPED",
                     {"reason": "production_disabled", "flag": "production_disabled"})]
    params = _params(ctx)
    ag = _activity_good(params)
    seed = int(getattr(ctx, "global_seed", 0))
    cap = int(params.get("cap_milli", P.DEFAULTS["cap_milli"]))
    dep_bp = int(params.get("depreciate_bp", P.DEFAULTS["depreciate_bp"]))
    base_res = int(params.get("place_base_milli", _PROD_DEFAULTS["place_base_milli"]))

    inv = {k: dict(v) for k, v in (getattr(state, "inventory", {}) or {}).items()}  # 本地模拟副本（不直写 state）
    specs = []

    # ---- (1) 生产：劳动类活动 → good ----
    for _seq, aid, place, atype, _p in _labor_completions(state, round_no):
        if not aid:
            continue
        for good in ag.get(str(atype), []) or []:
            if good not in P.GOODS:
                continue
            skill = _skill_level(state, aid, good)
            res = P.resource_factor_milli(seed, round_no, place or "residence", base_res, params)
            tools = P.inv_get(inv, aid, "tool")
            qty = P.produce_qty(good, skill, res, tools, params)
            if qty <= 0 or not P.can_produce(inv, aid, good):
                continue
            # 扣上游投入（原子：can_produce 已确保足额）
            for gid, need in P.RECIPES[good]["inputs"]:
                P.inv_remove(inv, aid, gid, int(need))
                specs.append(spec(round_no, P4, aid, "CONSUME", {
                    "agent_id": aid, "good_id": gid, "qty": int(need), "purpose": "input"}))
            r = P.inv_add(inv, aid, good, qty, cap)
            if r["added"] > 0:
                specs.append(spec(round_no, P4, aid, "PRODUCE", {
                    "agent_id": aid, "good_id": good, "qty": int(r["added"]),
                    "place": place, "recipe": good, "skill_level": int(skill)}))
            if r["dropped"] > 0:
                specs.append(spec(round_no, P4, aid, "PRODUCE_OVERFLOW", {
                    "agent_id": aid, "good_id": good, "qty_dropped": int(r["dropped"])}))

    # ---- (1b) 服务即时交付：socialize → SERVICE_DELIVERED（inventory-neutral；T278/08 §1.2 V）----
    svc_on = _service_enabled(ctx)
    for _seq, aid, place, atype, p_ in _labor_completions(state, round_no):
        if not aid:
            continue
        sg = ACTIVITY_SERVICE.get(str(atype))
        if not sg:
            continue
        if not svc_on:
            specs.append(spec(round_no, P4, "SYSTEM", "DROPPED",
                              {"reason": "service_disabled", "flag": "service_disabled",
                               "agent_id": aid}))
            continue
        skill = _skill_level(state, aid, sg)
        res = P.resource_factor_milli(seed, round_no, place or "residence", base_res, params)
        qty = P.produce_qty(sg, skill, res, 0, params)     # 服务无库存/工具加成
        if qty <= 0:
            continue
        # counterparty：参与者中除自己外恰一人 → 其 id；否则 None（自服务 → subject_only）
        others = [x for x in (p_.get("participants") or []) if x and x != aid]
        payload = {"agent_id": aid, "good_id": sg, "qty": int(qty), "place": place,
                   "round": int(round_no)}
        if len(others) == 1:
            payload["counterparty"] = others[0]
        specs.append(spec(round_no, P4, aid, "SERVICE_DELIVERED", payload))

    # ---- (2) 折旧（工具资产，δ/回合，floor 0）----
    for aid in _real_agents(state):
        q = P.inv_get(inv, aid, "tool")
        if q <= 0:
            continue
        d = P.depreciate(q, dep_bp)
        if d["loss"] > 0:
            inv.setdefault(aid, {})["tool"] = d["qty_after"]
            specs.append(spec(round_no, P4, aid, "DEPRECIATE", {
                "agent_id": aid, "asset_id": "tool", "delta_mu": int(d["loss"])}))

    # ---- (3) 生存消费（food，扣可得部分；不足不直接判死，交福祉/lifecycle）----
    need = int(params.get("need_food_milli", P.DEFAULTS["need_food_milli"]))
    for aid in _real_agents(state):
        have = P.inv_get(inv, aid, "food")
        eat = min(need, have)
        if eat > 0:
            P.inv_remove(inv, aid, "food", eat)
            specs.append(spec(round_no, P4, aid, "CONSUME", {
                "agent_id": aid, "good_id": "food", "qty": int(eat), "purpose": "eat"}))

    return specs


__all__ = ["apply_production", "ACTIVITY_GOOD"]
