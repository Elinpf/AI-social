#!/usr/bin/env python3
"""T331b 独立复验：T330（fc412a8）settlement 可见性「走索引」vs「全扫」等价 +
反向验证必红 + 身份注册脆弱性探测。
自建口径（不调用作者单测）。运行：
    cd code && python3 ../v2/evidence/t331b_settlement_port_verify.py
"""
import os, sys, io
os.environ.setdefault("N50_VEC", "0")

from orchestration.integration import build_world
import life.visibility as LV
from contracts.visibility import visible_events as _ve
from engine.perceive import load_perception_scope
from engine.version import load_visibility_flags
from engine.rng import Ctx
from life.settlement import write_memories


def _scope():
    s = load_perception_scope()
    plaf = load_visibility_flags().get("place_local_actor_fallback", False)
    return s.get("scope", {}), s.get("default_visibility_class", "place_local"), plaf


def fullscan_seq(state, aid, r):
    sc, dc, plaf = _scope()
    return [x["seq"] for x in _ve(list(state.event_index.values()), aid, r,
                                  scope_table=sc, default_cls=dc,
                                  place_local_actor_fallback=plaf)]


def run_world(seed, n, rounds):
    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    for r in range(rounds):
        eng.run_round(r)
    return eng


def equiv_scan(eng, label):
    st = eng.state
    total = diffs = 0
    for r in range(st.round + 1):
        for aid in sorted(st.agents):
            got = [x["seq"] for x in LV.visible_events(st.event_index, aid, r)]   # 索引/provider 路径
            ref = fullscan_seq(st, aid, r)                                        # 全扫（单一真源）
            total += 1
            if got != ref:
                diffs += 1
    print(f"[{label}] provider vs 全扫: {total - diffs}/{total} 相等, 差异={diffs}")
    return total, diffs


def main():
    print("=== A. 等价（自建口径，逐条 seq）===")
    allok = True
    for seed, n, rounds in [(1, 4, 10), (7, 6, 10), (42, 4, 12)]:
        eng = run_world(seed, n, rounds)
        t, d = equiv_scan(eng, f"seed={seed} n={n} r={rounds}")
        allok &= (d == 0)
    print("A 等价:", "PASS" if allok else "FAIL")

    print("\n=== B. 反向验证（人为让 provider 与全扫不一致 ⇒ 必须红）===")
    eng = run_world(42, 4, 12)
    st = eng.state
    key = id(st.event_index)
    if key not in LV._INDEXES:
        print("B: FAIL — state.event_index 未注册 provider（无法做反向验证）")
    else:
        real = LV._INDEXES[key]

        def broken(agent_id, upto, *, window_rounds=None, location=None):
            out = real(agent_id, upto, window_rounds=window_rounds, location=location)
            return out[:-1] if out else out        # 人为少一条
        LV._INDEXES[key] = broken
        _, d = equiv_scan(eng, "反向(provider 少一条)")
        LV._INDEXES[key] = real
        print("B 反向验证:", "PASS（变红=检出差异）" if d > 0 else "FAIL（差异=0 ⇒ 断言恒真，检查无效）")

    print("\n=== C. 身份注册脆弱性探测（本单重点）===")
    eng = run_world(42, 4, 12)
    st = eng.state
    # C1: 传浅拷贝 dict（内容相同、对象不同）
    shallow = dict(st.event_index)
    hit = id(shallow) in LV._INDEXES
    print(f"C1 浅拷贝 dict(state.event_index): id 命中={hit}  ⇒ {'走索引' if hit else '静默回退全扫(FALLBACK)'}")
    # C2: 传 list(...) 物化（内容相同、对象不同）
    lst = list(st.event_index.values())
    hit2 = id(lst) in LV._INDEXES
    print(f"C2 list(state.event_index.values()): id 命中={hit2}  ⇒ {'走索引' if hit2 else '静默回退全扫(FALLBACK)'}")
    # C3: 内容仍等价？（退化只是慢，还是也错？）
    r0 = st.round
    a0 = sorted(st.agents)[0]
    eq_copy = ([x["seq"] for x in LV.visible_events(shallow, a0, r0)] == fullscan_seq(st, a0, r0))
    print(f"C3 浅拷贝路径结果 == 全扫: {eq_copy}（⇒ 退化是【性能】而非【正确性】）")
    # C4: provider 覆盖真实机制（原始 id 命中）
    print(f"C4 原始 state.event_index id 命中={id(st.event_index) in LV._INDEXES}（应 True）")
    # C5: id 复用风险（说明，不实测）
    print("C5 注：lookup 用 id(records)。一对象释放后其 id 可能被复用 ⇒ 理论假命中；"
          "且若 state.event_index 被替换/restore 重建 ⇒ 旧 id 失效 ⇒ 静默回退。")

    print("\n=== D. state_hash：provider 路径 vs 全扫（清 provider）端到端 ===")
    def run_and_seals(clear):
        w = build_world(seed=42, n=4)
        eng = w["engine"]
        if clear:
            LV.clear_indexes()
        seals = []
        for r in range(12):
            eng.run_round(r)
        return eng
    e1 = run_and_seals(False)
    e2 = run_and_seals(True)
    s1 = e1.state_hash() if hasattr(e1, "state_hash") else None
    s2 = e2.state_hash() if hasattr(e2, "state_hash") else None
    if s1 is None:
        # fallback：比最终 TURN_SEAL state_hash
        def last_seal(eng):
            for rec in reversed(list(eng.state.event_index.values())):
                if rec.get("type") == "TURN_SEAL":
                    return (rec.get("payload") or {}).get("state_hash")
            return None
        s1, s2 = last_seal(e1), last_seal(e2)
    print(f"D provider end state_hash = {s1}")
    print(f"D fallback end state_hash = {s2}")
    print("D:", "PASS（同）" if (s1 == s2 and s1 is not None) else "CHECK（不同或缺失）")


if __name__ == "__main__":
    main()
