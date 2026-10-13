#!/usr/bin/env python3
"""T351 非作者独立核：T338 `events_this_round` 端口修（d598f47）—— 等价 / 命中 / 可观测 / 反向。

自建口径：参考 = 独立全表扫（直接读 state.event_index），不复用作者单测。
只读；不改 code/。
运行：cd repo && python3 v2/evidence/t351_round_events_port_verify.py [seed] [rounds] [n]
"""
import os
import sys
import time

os.environ.setdefault("N50_VEC", "0")
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "code"))

from orchestration.integration import build_world      # noqa: E402
from life import settlement as S                        # noqa: E402
from life.settlement import LifeState                   # noqa: E402
from engine.state import state_hash                     # noqa: E402


def ref_full_scan(state, rd, etype=None):
    out = [rec for rec in state.event_index.values()
           if rec.get("round") == rd and (etype is None or rec.get("type") == etype)]
    out.sort(key=lambda r: r.get("seq", 0))
    return out


def seqs(recs):
    return [r.get("seq") for r in recs]


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    print(f"=== T351 独立核 · seed={seed} rounds={rounds} n={n} ===")

    # ---- HIT 计数：包一层 adapter.round_events ----
    hits = {"n": 0}
    w = build_world(seed=seed, n=n)
    eng = w["engine"]
    adapter = eng.kernel
    assert adapter is not None and hasattr(adapter, "round_events"), "engine.kernel 未注入 adapter"
    _orig = adapter.round_events

    def counting_round_events(round_no, types=None):
        hits["n"] += 1
        return _orig(round_no, types)
    adapter.round_events = counting_round_events

    S.reset_port_fallback_count()
    for r in range(rounds):
        eng.run_round(r)
    fb = S.port_fallback_count()
    print(f"\n[运行期] adapter.round_events HIT 调用数 = {hits['n']} ; life 端口回退(FALLBACK) 次数 = {fb}")
    print(f"  ⇒ 命中证据：{'HIT>0 且 FALLBACK=0（端口真生效、未静默回退）' if hits['n'] > 0 and fb == 0 else '✗ 异常'}")

    st = eng.state
    ls = LifeState(st, kernel=adapter)   # 以 adapter 作 kernel（同运行期 ctx.kernel 注入）

    # ---- 逐条等价：端口 vs 独立全扫 ----
    diffs = []
    ncmp = 0
    all_types = sorted({rec.get("type") for rec in st.event_index.values()})
    for rd in range(rounds):
        # etype=None
        p = ls.events_this_round(rd, None, kernel=adapter)
        r0 = ref_full_scan(st, rd, None)
        ncmp += 1
        if seqs(p) != seqs(r0) or p != r0:
            diffs.append(f"round={rd} etype=None: port {len(p)} vs scan {len(r0)}")
        for t in all_types:
            p = ls.events_this_round(rd, t, kernel=adapter)
            r0 = ref_full_scan(st, rd, t)
            ncmp += 1
            if seqs(p) != seqs(r0) or p != r0:
                diffs.append(f"round={rd} etype={t}: port {len(p)} vs scan {len(r0)}")
    print(f"\n[① 逐条等价] 比对 {ncmp} 组（round×type，含 etype=None） -> {'N/N 全等' if not diffs else '差异:'}")
    for d in diffs[:10]:
        print("  ✗ " + d)
    print(f"  state_hash={state_hash(st)}")

    # ---- ④ 可观测性：无端口 ⇒ 计数+WARN 可触发 ----
    print("\n[④ 可观测性] 走无端口路径（kernel=None ⇒ 回退）")
    S.reset_port_fallback_count()
    ls_null = LifeState(st, kernel=None)
    import io
    import contextlib
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        for rd in range(min(3, rounds)):
            ls_null.events_this_round(rd, "ACTIVITY_COMPLETED", kernel=None)
    cnt = S.port_fallback_count()
    warned = "T338" in err.getvalue() and "WARN" in err.getvalue()
    print(f"  fallback 计数 = {cnt}（对 {min(3,rounds)} 次无端口调用）; 首告警 WARN 出现 = {warned}")
    print(f"  ⇒ 可观测：{'计数递增 + 首告警可触发（非静默）' if cnt == min(3, rounds) and warned else '✗'}")

    # ---- ③ 反向验证：篡改端口 ⇒ 必检出 ----
    print("\n[③ 反向验证] 篡改端口 = 漏 1 条 / 逆序 ⇒ 必须与全扫不一致")
    rev = {}
    rd = rounds // 2
    base = _orig(rd, None)
    # a) 漏一条
    adapter.round_events = lambda rn, types=None, _b=base, _rd=rd: (list(_b[:-1]) if rn == _rd and types is None else _orig(rn, types))
    pa = ls.events_this_round(rd, None, kernel=adapter)
    ra = ref_full_scan(st, rd, None)
    rev["漏 1 条"] = (seqs(pa) != seqs(ra))
    # b) 逆序
    adapter.round_events = lambda rn, types=None, _b=base, _rd=rd: (list(reversed(_b)) if rn == _rd and types is None else _orig(rn, types))
    pb = ls.events_this_round(rd, None, kernel=adapter)
    rev["逆序"] = (seqs(pb) != seqs(ra))
    adapter.round_events = counting_round_events  # 还原
    for k, v in rev.items():
        print(f"  {k}: {'PASS-检出' if v else 'FAIL-未检出'}")
    print(f"  ⇒ 反向：{'全部检出' if all(rev.values()) else '有未检出'}")

    # ---- 时间（同进程；口径写明）----
    aid_types = ("ACTIVITY_COMPLETED", "MARKET_TRADE", "TRANSFER")
    t0 = time.perf_counter()
    c1 = 0
    for _ in range(20):
        for r in range(rounds):
            for t in aid_types:
                _orig(r, (t,)); c1 += 1
    t_port = time.perf_counter() - t0
    t0 = time.perf_counter()
    c2 = 0
    for _ in range(20):
        for r in range(rounds):
            for t in aid_types:
                ref_full_scan(st, r, t); c2 += 1
    t_scan = time.perf_counter() - t0
    print(f"\n[时间·同进程] 端口 {c1} 次={t_port*1000:.1f}ms ; 全扫 {c2} 次={t_scan*1000:.1f}ms ; 比={t_scan/max(t_port,1e-9):.2f}×")

    print("\n==== 汇总 ====")
    ok = (not diffs) and fb == 0 and hits["n"] > 0 and cnt == min(3, rounds) and warned and all(rev.values())
    print(f"等价 N/N={'是' if not diffs else '否'}; HIT>0&FALLBACK=0={'是' if hits['n']>0 and fb==0 else '否'}; 可观测={'是' if warned else '否'}; 反向={'全检出' if all(rev.values()) else '否'}")
    print(f"结论: {'可判为无行为变（等价）+ 端口真生效且可观测' if ok else '见上'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
