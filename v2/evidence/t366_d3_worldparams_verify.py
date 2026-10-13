#!/usr/bin/env python3
"""T366 非作者独立核：D3 口径②（T353 端口 + T364 消费）—— 四项（只读；不改 code/）。

⚠️ 前置门：重活须 T350 结束 + Leader「完全解冻」后跑。

用法（mode）：
  consumption  ① 消费点三档计数（夹具 ON / propagate OFF / 默认 conservative）+ 运行时纯度
  future       ②' 只对未来 [start,end) 的纯函数单测
  dose0        ② dose=0 ⇒ 恒等（同 sha 内翻开关 + 跨 sha 两开关同关）+ 负例
  matrix       ③ A0/A1 受控剂量对照
  all          依次全跑
"""
import os
import sys
import json
import shutil
import tempfile
import subprocess
from collections import Counter

os.environ.setdefault("N50_VEC", "0")
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "code"))

from orchestration.integration import build_world          # noqa: E402
from engine.runner import default_config                   # noqa: E402
from engine.state import state_hash                        # noqa: E402
from engine.world_params import world_params as _wp_pure   # noqa: E402


def cfg(**wd):
    c = default_config()
    c.setdefault("world_director", {}).update(wd)
    return c


def force_festival_cfg(place="hall", slots=3, prob_bp=10000):
    """⚠️ 确定性夹具 = 人为提高剂量/注入指令：仅证"通路 + 三档计数可测"，非"默认世界可感"。"""
    c = cfg(dose_curve="moderate")
    ms = c["world_director"].setdefault("mechanisms", {})
    ms["wd.festival"] = {"kind": "festival", "enabled": True, "place": place,
                         "scope_level": "global",
                         "dose": {"prob_bp": prob_bp, "capacity": 40, "slots": slots}}
    return c


def run(seed, rounds, n, config):
    w = build_world(seed=seed, config=config, n=n)
    eng = w["engine"]
    for r in range(rounds):
        eng.run_round(r)
    return w, eng


def ctr(w):
    return (sum(getattr(a, "_wp_reads", 0) for a in w["agents"]),
            sum(getattr(a, "_wp_nonempty", 0) for a in w["agents"]),
            sum(getattr(a, "_wp_changed_choice", 0) for a in w["agents"]))


def fam(eng):
    return Counter(r.get("type") for r in eng.ledger.records)


def check_consumption():
    seed, rounds, n = 42, 24, 6
    ok = True
    print(f"=== ① 消费点三档 · seed={seed} rounds={rounds} n={n} ===")
    w1, e1 = run(seed, rounds, n, force_festival_cfg())
    r1, n1, c1 = ctr(w1)
    rounds_nonempty = sum(1 for t in range(rounds)
                          if _wp_pure(e1.ledger.records, t, e1.config).get("activity_weight"))
    print(f"[夹具 ON festival@hall] reads={r1} nonempty={n1} changed_choice={c1} ; wp非空回合={rounds_nonempty}")
    print(f"  ①开>0 {'PASS' if r1>0 else 'FAIL'} | ②非空>0 {'PASS' if n1>0 else 'FAIL'} | ③真改变选择>0 {'PASS' if c1>0 else 'FAIL'}")
    ok &= (r1 > 0 and n1 > 0 and c1 > 0)

    w0, e0 = run(seed, rounds, n, cfg(propagate={"enabled": False}))
    r0, n0, c0 = ctr(w0)
    print(f"[propagate=False] reads={r0} nonempty={n0} changed_choice={c0}")
    print(f"  ②关⇒非空必=0 {'PASS' if n0==0 else 'FAIL'} | ③关⇒改选择=0 {'PASS' if c0==0 else 'FAIL'}")
    ok &= (n0 == 0 and c0 == 0)

    wc, ec = run(seed, rounds, n, default_config())
    print(f"[默认 conservative] reads={ctr(wc)[0]} nonempty={ctr(wc)[1]} changed_choice={ctr(wc)[2]}（稀疏读数，如实报）")

    print("--- 运行时纯度 ---")
    hb = state_hash(e1.state)
    a = w1["agents"][0]
    a._wp_reads += 99999; a._wp_nonempty += 123; a._wp_changed_choice += 456
    ha = state_hash(e1.state)
    print(f"  改计数后 state_hash 不变: {'PASS' if hb==ha else 'FAIL'}")
    ok &= (hb == ha)
    ev_wp = [t for t in fam(e1) if "wp" in t.lower()]
    print(f"  无 wp 相关事件类型: {'PASS' if not ev_wp else 'FAIL '+str(ev_wp)}")
    before = (a._wp_reads, a._wp_nonempty, a._wp_changed_choice)
    a.restore(e1.state, e1.ledger.records)
    after = (a._wp_reads, a._wp_nonempty, a._wp_changed_choice)
    print(f"  restore() 不重置计数: {'PASS' if before==after else 'FAIL'}")
    ok &= (before == after)
    print(f"→ ①: {'PASS' if ok else 'FAIL'}")
    return ok


def check_future():
    print("=== ②' 只对未来 [start,end)（纯函数单测）===")
    rec = [{"type": "WORLD_GROUP_EVENT", "round": 5,
            "payload": {"directed": True, "kind": "festival", "place": "hall",
                        "start_round": 5, "end_round": 8, "params": {"capacity": 40},
                        "directive_ref": "D-x"}}]
    good = True
    for t in range(0, 12):
        wp = _wp_pure(rec, t, default_config())
        inside = 5 <= t < 8
        nonempty = bool(wp.get("activity_weight"))
        if inside != nonempty:
            good = False
        print(f"  t={t:2d} inside={inside} activity_weight={wp.get('activity_weight')}")
    print(f"→ ②' 只对未来 [start,end): {'PASS' if good else 'FAIL'}")
    return good


def _probe(code_dir, prop):
    env = {**os.environ, "T366_CODE": code_dir, "T366_PROPAGATE": str(prop), "N50_VEC": "0"}
    out = subprocess.run([sys.executable, os.path.join(REPO, "v2/evidence/t366_probe_hash.py"),
                          "42", "24", "6"], capture_output=True, text=True, env=env)
    lines = out.stdout.strip().splitlines()
    return lines[-1] if lines else f"ERR:{out.stderr[-300:]}"


def check_dose0():
    print("=== ② dose=0 ⇒ 恒等 ===")
    ok = True
    w_off, e_off = run(42, 24, 6, cfg(propagate={"enabled": False}))
    h_off = state_hash(e_off.state)
    w_on, e_on = run(42, 24, 6, force_festival_cfg())
    h_on = state_hash(e_on.state)
    print(f"[同 sha 内] propagate=false → {h_off}")
    print(f"[同 sha 内] 夹具 dose≠0    → {h_on}")
    print(f"  负例（dose≠0 真红）: {'PASS' if h_on != h_off else 'FAIL'}")
    ok &= (h_on != h_off)

    # pre-T353 基线树 = 被核提交 1ffd7eb 的父提交（勿用 HEAD：HEAD 可能已含 T353）
    BASE = os.environ.get("T366_BASE", "1ffd7eb^")
    base_sha = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", BASE],
                              capture_output=True, text=True).stdout.strip()
    tmp = tempfile.mkdtemp(prefix="t366_")
    hd = os.path.join(tmp, "head"); wp = os.path.join(tmp, "wip")
    os.makedirs(hd); os.makedirs(wp)
    subprocess.run(f"git -C {REPO} archive {BASE} | tar -x -C {hd}", shell=True, check=True)
    shutil.copytree(os.path.join(REPO, "code"), os.path.join(wp, "code"))
    for root in (hd, wp):
        tf = os.path.join(root, "code/config/time.json")
        d = json.load(open(tf)); d.setdefault("ongoing", {})["enabled"] = False
        json.dump(d, open(tf, "w"), ensure_ascii=False, indent=2)
    h_head = _probe(os.path.join(hd, "code"), 0)
    h_wip = _probe(os.path.join(wp, "code"), 0)
    print(f"[跨 sha] 基线 {BASE}={base_sha}(pre-T353, time.off)  → {h_head}")
    print(f"[跨 sha] 当前树(1ffd7eb, propagate=false + time.off)  → {h_wip}")
    print(f"⚠️ 注明：基线 {base_sha} 已含 T354；两树 time.ongoing 同关 ⇒ 差异只可能来自 T353")
    same = (h_head == h_wip) and h_head.startswith("sha256:")
    print(f"  dose=0 ≡ 现状（跨 sha 恒等）: {'PASS' if same else 'FAIL'}")
    ok &= same
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"→ ②: {'PASS' if ok else 'FAIL'}")
    return ok


def check_matrix():
    print("=== ③ A0/A1 受控剂量对照（dose_curve=moderate）===")
    w0, e0 = run(42, 24, 6, cfg(dose_curve="moderate", propagate={"enabled": False}))
    w1, e1 = run(42, 24, 6, cfg(dose_curve="moderate", propagate={"enabled": True}))
    c0, c1 = fam(e0), fam(e1)
    nz = {f: c1.get(f, 0) - c0.get(f, 0) for f in sorted(set(c0) | set(c1)) if c1.get(f, 0) != c0.get(f, 0)}
    print(f"[A0] counts={sum(c0.values())} wp={ctr(w0)}")
    print(f"[A1] counts={sum(c1.values())} wp={ctr(w1)}")
    print(f"非零族 delta: {nz or '（全 0）'}")
    print(f"state_hash A0={state_hash(e0.state)}")
    print(f"state_hash A1={state_hash(e1.state)} 相同={state_hash(e0.state)==state_hash(e1.state)}")
    print("⚠️ delta≈0/state_hash 同 ⇒ 不判 inert/等价，回 ① 看消费点（稀疏预期）")
    return True


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    fns = {"consumption": [check_consumption], "future": [check_future],
           "dose0": [check_dose0], "matrix": [check_matrix],
           "all": [check_consumption, check_future, check_dose0, check_matrix]}[mode]
    rc = 0
    for f in fns:
        rc |= (0 if f() else 1)
    sys.exit(rc)
