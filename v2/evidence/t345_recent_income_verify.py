#!/usr/bin/env python3
"""T345 非作者独立复验：T328③ `recent_income` 标量累加器（`state.income_net`）。

纪律：
- **自建口径**：参考实现 `ref_recent_income` 为独立全表扫（直接读 `state.event_index`，
  不复用作者单测、不 import 被改函数）。
- **只读**：不改 `code/`。
- 等价判据：对全部 (agent × round) 抽满，比较 **新实现** `liquidity.recent_income`
  与 **独立参考** ⇒ 报 `N/N` 或差异清单。
- 反向验证：人为破坏累加器（漏一个回合 / 错位 / 漏 TRANSFER）⇒ **必须被检出**。
- 同进程内的调用数写明；乘数不作通用结论。

运行：cd repo && python3 v2/evidence/t345_recent_income_verify.py [seed] [rounds] [n]
"""
import os
import sys
import copy
import time

os.environ.setdefault("N50_VEC", "0")

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "code"))

from orchestration.integration import build_world   # noqa: E402
from engine import liquidity                        # noqa: E402
from engine.state import state_hash                 # noqa: E402

# 独立写死的口径常量（**不** import 自被改模块，避免与被核对象同源漂移）
_REF_INCOME_TX = ("transfer", "trade")
_REF_EXCLUDE = frozenset({"wash", "cycle", "self", "mule"})


def ref_recent_income(state, aid, round_no, window):
    """独立全表扫参考实现（读 event_index，逐条）。"""
    per_round = {}
    lo = int(round_no) - int(window)
    hi = int(round_no)
    for rec in state.event_index.values():
        rd = int(rec.get("round", -1))
        if rd < lo or rd > hi:
            continue
        t = rec.get("type")
        p = rec.get("payload") or {}
        if t == "TRANSFER":
            frm, to, tt = p.get("from"), p.get("to"), p.get("tx_type", "transfer")
        elif t == "MARKET_TRADE":
            frm, to, tt = p.get("buyer"), p.get("seller"), p.get("tx_type", "trade")
        else:
            continue
        if tt not in _REF_INCOME_TX:
            continue
        if frm == to or (set(p.get("flags") or []) & _REF_EXCLUDE):
            continue
        amt = int(p.get("amount", 0))
        d = per_round.setdefault(rd, 0)
        if to == aid:
            d += amt
        if frm == aid:
            d -= amt
        per_round[rd] = d          # ← 写回（int 不可变；漏此步则恒为 0）
    return sum(max(0, v) for v in per_round.values())


def compare(state, params, rounds, tag, collect_diffs=True):
    """对全部 (agent × round) 比较 新实现 vs 参考；返回 (n_cmp, diffs)。"""
    aids = sorted(state.agents)
    n = 0
    diffs = []
    for aid in aids:
        for rd in range(0, rounds + 2):   # 多探边界两回合
            got = liquidity.recent_income(state, aid, rd, params)
            want = ref_recent_income(state, aid, rd, params.get("w_income_rounds", 12))
            n += 1
            if got != want:
                if collect_diffs and len(diffs) < 20:
                    diffs.append(f"{tag} aid={aid} round={rd}: 新实现={got} 参考={want}")
    return n, diffs


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    n_agents = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    window = 12
    params = {"w_income_rounds": window}

    print(f"=== T345 独立复验 · seed={seed} rounds={rounds} n={n_agents} window={window} ===")
    world = build_world(seed, n=n_agents)
    eng = world["engine"]
    for r in range(rounds):
        eng.run_round(r)
    st = eng.state

    print(f"acc_trusted={getattr(st,'acc_trusted',None)}  len(event_index)={len(st.event_index)}  "
          f"acc_n={getattr(st,'acc_n',None)}  income_net agents={len(getattr(st,'income_net',{}))}")
    print(f"state_hash={state_hash(st)}")

    # ---- ① 逐条等价（可信态：Engine 直产）----
    n1, d1 = compare(st, params, rounds, "①trusted")
    print(f"\n[① 逐条等价 · 可信态] 比对 {n1} 条 -> {'N/N 全等' if not d1 else '差异:'}")
    for x in d1:
        print("  ✗ " + x)
    # 确认口径常量与被核模块一致（仅作一致性说明，非等价判据）
    same_consts = (tuple(liquidity._INCOME_TX_TYPES) == _REF_INCOME_TX
                   and frozenset(liquidity._EXCLUDE_FLAGS) == _REF_EXCLUDE)
    print(f"    口径常量自洽（_INCOME_TX_TYPES/_EXCLUDE_FLAGS == 独立写死）: {same_consts}")

    # ---- ② 不可信态（强制 rebuild 自愈路径）也应等价 ----
    st2 = copy.deepcopy(st)
    st2.acc_trusted = False
    from engine import event_acc
    event_acc.ensure(st2)   # 不可信 ⇒ 每次 rebuild
    n2, d2 = compare(st2, params, rounds, "②untrusted-rebuild")
    print(f"[② 逐条等价 · 不可信态(强制 rebuild)] 比对 {n2} 条 -> {'N/N 全等' if not d2 else '差异:'}")
    for x in d2:
        print("  ✗ " + x)

    # ---- ③ 反向验证：破坏累加器 ⇒ 必须被检出 ----
    print("\n[③ 反向验证（必须检出）]")
    rev = {}

    # ③a 漏一个回合（对某 agent 抹掉一个非零 round）
    broken = copy.deepcopy(st)
    victim = None
    for a, m in broken.income_net.items():
        for rd, v in m.items():
            if v != 0:
                victim = (a, rd); break
        if victim:
            break
    if victim:
        a, rd = victim
        before = broken.income_net[a][rd]
        broken.income_net[a][rd] = 0   # 抹零 = 漏该回合
        nA, dA = compare(broken, params, rounds, "③a-漏一回合")
        rev["③a 漏一回合"] = (bool(dA), f"篡改 {a}.round{rd}: {before}->0", nA, dA[:3])
    else:
        rev["③a 漏一回合"] = (False, "无可用非零样本", 0, [])

    # ③b 错位：把某 agent 一个 round 的净额搬到相邻 round
    broken2 = copy.deepcopy(st)
    victim2 = None
    for a, m in broken2.income_net.items():
        for rd, v in m.items():
            if v != 0:
                victim2 = (a, rd, v); break
        if victim2:
            break
    if victim2:
        a, rd, v = victim2
        del broken2.income_net[a][rd]
        broken2.income_net[a][rd + 1] = broken2.income_net[a].get(rd + 1, 0) + v  # 错位一回合
        nB, dB = compare(broken2, params, rounds, "③b-错位一回合")
        rev["③b 错位一回合"] = (bool(dB), f"迁 {a} round{rd}({v})->round{rd+1}", nB, dB[:3])
    else:
        rev["③b 错位一回合"] = (False, "无可用非零样本", 0, [])

    # ③c 漏 TRANSFER：重建一个"丢掉 TRANSFER"的累加器（模拟累加器缺陷）
    broken3 = copy.deepcopy(st)
    # 用参考口径的"仅 MARKET_TRADE"版本重建，制造与全扫不一致
    broken3.income_net = {}
    for rec in broken3.event_index.values():
        t = rec.get("type")
        if t != "MARKET_TRADE":   # 故意漏 TRANSFER
            continue
        p = rec.get("payload") or {}
        frm, to, tt = p.get("buyer"), p.get("seller"), p.get("tx_type", "trade")
        if tt not in _REF_INCOME_TX or frm == to or (set(p.get("flags") or []) & _REF_EXCLUDE):
            continue
        amt = int(p.get("amount", 0)); rd = int(rec["round"])
        if to:
            broken3.income_net.setdefault(to, {}).setdefault(rd, 0); broken3.income_net[to][rd] += amt
        if frm:
            broken3.income_net.setdefault(frm, {}).setdefault(rd, 0); broken3.income_net[frm][rd] -= amt
    nC, dC = compare(broken3, params, rounds, "③c-漏TRANSFER")
    rev["③c 漏 TRANSFER"] = (bool(dC), "累加器仅记 MARKET_TRADE", nC, dC[:3])

    for k, (detected, how, ncmp, sample) in rev.items():
        print(f"  {k}: {'PASS-检出' if detected else 'FAIL-未检出'}  ({how}; 比 {ncmp} 条)")
        for x in sample:
            print("      ✗ " + x)

    # ---- ④ 时间收益（同进程；调用数写明）----
    aids = sorted(st.agents)
    calls = 0
    t0 = time.perf_counter()
    for _ in range(1):
        for aid in aids:
            for rd in range(rounds):
                liquidity.recent_income(st, aid, rd, params); calls += 1
    t_new = time.perf_counter() - t0
    calls_r = 0
    t0 = time.perf_counter()
    for _ in range(1):
        for aid in aids:
            for rd in range(rounds):
                ref_recent_income(st, aid, rd, window); calls_r += 1
    t_ref = time.perf_counter() - t0
    print(f"\n[④ 时间 · 同进程] 新实现 {calls} 次={t_new*1000:.1f}ms ; "
          f"独立全扫 {calls_r} 次={t_ref*1000:.1f}ms ; 比={t_ref/max(t_new,1e-9):.2f}×（N=calls 次，单进程，不作通用乘数）")

    # ---- 汇总 ----
    all_eq = (not d1) and (not d2)
    all_rev = all(v[0] for v in rev.values())
    print("\n==== 汇总 ====")
    print(f"①逐条等价: {'N/N' if not d1 else f'{len(d1)} 差异'} ({n1}); ②不可信态: {'N/N' if not d2 else f'{len(d2)} 差异'} ({n2})")
    print(f"③反向验证: {'全部检出' if all_rev else '有未检出项'}")
    print(f"结论: {'可判为无行为变（等价）' if (all_eq and all_rev) else '不可判（见上差异）'}")
    return 0 if (all_eq and all_rev) else 1


if __name__ == "__main__":
    sys.exit(main())
