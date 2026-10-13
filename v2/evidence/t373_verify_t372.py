"""T373 独立核验：`T372` 的 `world_params` 同 `directive_id` 双计修复。

非作者独立核验 —— **不 import 作者测试**（`code/tests/test_t372_world_params_dedupe.py`）；
自建构造 + 世界级两跑对照。

⚠️ 前置：`T372` 落地主树后方可跑重活；跑前频道广播占用。

用法：
    python v2/evidence/t373_verify_t372.py            # 全量（含两次世界跑 = 重活）
    python v2/evidence/t373_verify_t372.py --child <mode> <out>  # 内部：子进程跑单世界
输出：stdout + `--json v2/evidence/T373-run.json`。
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CFG = {"world_director": {"propagate": {"enabled": True}}}


# --------------------------------------------------------------------------- #
# ① 修复前算法（去重前），用于复现"×2" & 作为"修复前"参照——**独立重写**，不复用实现
# --------------------------------------------------------------------------- #
def _prefix_world_params(records, round_no, config):
    out = {"activity_weight": {}, "resource_factor_bp": {}, "market_scarcity_bp": {}, "active": []}
    wd = (config or {}).get("world_director", {}) or {}
    if not bool((wd.get("propagate", {}) or {}).get("enabled", True)):
        return out
    t = int(round_no)
    for rec in records:
        if rec.get("type") not in ("WORLD_GROUP_EVENT", "WORLD_DIRECTIVE"):
            continue
        p = rec.get("payload", {}) or {}
        if not p.get("directed", False):
            continue
        start = int(p.get("start_round", p.get("effective_from_round", rec.get("round", 0))) or 0)
        end = int(p.get("end_round", p.get("expires_round", start + 1)) or (start + 1))
        if not (start <= t < end):
            continue
        kind = str(p.get("kind", "")).lower()
        ref = p.get("directive_ref") or p.get("directive_id")
        if ref:
            out["active"].append(ref)
        scope = p.get("scope", {}) or {}
        place = scope.get("place") or p.get("place")
        params = p.get("params", {}) or {}
        if kind in ("festival", "mass_event"):
            if place:
                out["activity_weight"][place] = out["activity_weight"].get(place, 0) + int(params.get("capacity", 40))
        elif kind in ("supply_shock", "disaster"):
            amp = int(params.get("amp_bp", params.get("severity", 0)) or 0)
            key = place or "global"
            out["resource_factor_bp"][key] = out["resource_factor_bp"].get(key, 0) - abs(amp)
        elif kind in ("tension", "edict", "scarcity"):
            sc = int(params.get("scarcity_bp", 0) or 0)
            g = params.get("good_id") or "global"
            out["market_scarcity_bp"][g] = out["market_scarcity_bp"].get(g, 0) + sc
    return out


def _live_world_params():
    from engine.world_params import world_params
    return world_params


# --------------------------------------------------------------------------- #
# 合成构造器（对齐真实发射形态：DIRECTIVE{directive_id} + GROUP_EVENT{directive_ref}）
# --------------------------------------------------------------------------- #
def _directive(did, kind, place, params, r=0, start=0, end=10):
    return {"seq": 0, "round": r, "phase": 4, "actor": "DIRECTOR", "type": "WORLD_DIRECTIVE",
            "payload": {"directive_id": did, "kind": kind, "scope": {"place": place}, "params": params,
                        "directed": True, "effective_from_round": start, "expires_round": end,
                        "place": place}}


def _group(did, kind, place, params, r=0, start=0, end=10):
    return {"seq": 0, "round": r, "phase": 4, "actor": "DIRECTOR", "type": "WORLD_GROUP_EVENT",
            "payload": {"group_event_id": f"GE-{did}", "directive_ref": did, "kind": kind,
                        "scope": {"place": place}, "params": params, "directed": True,
                        "start_round": start, "end_round": end, "place": place}}


def unit_tests(live):
    res = {}
    # ① 复现原缺陷：同 did 两条 → prefix 2×，live 1×（capacity=40）
    pair = [_directive("D-1-f", "festival", "hall", {"capacity": 40}),
            _group("D-1-f", "festival", "hall", {"capacity": 40})]
    pre = _prefix_world_params(pair, 5, CFG)["activity_weight"].get("hall")
    post = live(pair, 5, CFG)["activity_weight"].get("hall")
    res["①same_did"] = {"prefix(2x)": pre, "live(1x)": post,
                         "prefix_is_2x": pre == 80, "live_is_1x": post == 40}
    # ③ active 不重复
    res["③active_no_dup"] = live(pair, 5, CFG)["active"]
    # ④ 反向：两条**不同 did** ⇒ 必须各计一次（不得误去重）⇒ 40+30=70
    two = [_directive("D-1-f", "festival", "hall", {"capacity": 40}),
           _group("D-1-f", "festival", "hall", {"capacity": 40}),
           _directive("D-2-f", "festival", "hall", {"capacity": 30}),
           _group("D-2-f", "festival", "hall", {"capacity": 30})]
    res["④two_diff_did"] = {"live_weight": live(two, 5, CFG)["activity_weight"].get("hall"),
                            "expect_70": live(two, 5, CFG)["activity_weight"].get("hall") == 70,
                            "prefix_140_would_double": _prefix_world_params(two, 5, CFG)["activity_weight"].get("hall")}
    # 负例：同 did 但改成不同 did（模拟"应不去重"）⇒ live 应 = 80
    neg = [_directive("D-1-f", "festival", "hall", {"capacity": 40}),
           _group("D-1-f-B", "festival", "hall", {"capacity": 40})]
    res["④neg_diff_ref_no_dedup"] = {"live_weight": live(neg, 5, CFG)["activity_weight"].get("hall"),
                                     "expect_80": live(neg, 5, CFG)["activity_weight"].get("hall") == 80}
    # 兼容：单一类型夹具（向后兼容）
    res["compat_single_type"] = {t: live([_directive("D-1-f", "festival", "hall", {"capacity": 40})], 5, CFG)
                                 ["activity_weight"].get("hall") if t == "directive" else
                                 live([_group("D-1-f", "festival", "hall", {"capacity": 40})], 5, CFG)
                                 ["activity_weight"].get("hall") for t in ("directive", "group_event")}
    return res


# --------------------------------------------------------------------------- #
# 世界级：单世界（子进程），可切 prefix/live
# --------------------------------------------------------------------------- #
def _run_child(mode, seed, n, rounds, out_path, code_root):
    sys.path.insert(0, code_root)
    os.environ.setdefault("N50_VEC", "0")
    if mode == "prefix":
        import engine.world_params as W
        import importlib
        # 子进程内需能取到本模块的 _prefix —— 直接内联同算法（避免 import 本脚本）
        def _prefix(records, round_no, config):
            out = {"activity_weight": {}, "resource_factor_bp": {}, "market_scarcity_bp": {}, "active": []}
            wd = (config or {}).get("world_director", {}) or {}
            if not bool((wd.get("propagate", {}) or {}).get("enabled", True)):
                return out
            t = int(round_no)
            for rec in records:
                if rec.get("type") not in ("WORLD_GROUP_EVENT", "WORLD_DIRECTIVE"):
                    continue
                p = rec.get("payload", {}) or {}
                if not p.get("directed", False):
                    continue
                s = int(p.get("start_round", p.get("effective_from_round", rec.get("round", 0))) or 0)
                e = int(p.get("end_round", p.get("expires_round", s + 1)) or (s + 1))
                if not (s <= t < e):
                    continue
                k = str(p.get("kind", "")).lower()
                ref = p.get("directive_ref") or p.get("directive_id")
                if ref:
                    out["active"].append(ref)
                sc = p.get("scope", {}) or {}
                place = sc.get("place") or p.get("place")
                pr = p.get("params", {}) or {}
                if k in ("festival", "mass_event"):
                    if place:
                        out["activity_weight"][place] = out["activity_weight"].get(place, 0) + int(pr.get("capacity", 40))
                elif k in ("supply_shock", "disaster"):
                    amp = int(pr.get("amp_bp", pr.get("severity", 0)) or 0)
                    key = place or "global"
                    out["resource_factor_bp"][key] = out["resource_factor_bp"].get(key, 0) - abs(amp)
                elif k in ("tension", "edict", "scarcity"):
                    out["market_scarcity_bp"][pr.get("good_id") or "global"] = \
                        out["market_scarcity_bp"].get(pr.get("good_id") or "global", 0) + int(pr.get("scarcity_bp", 0) or 0)
            return out
        W.world_params = _prefix
    from engine.runner import default_config
    from orchestration.integration import build_world
    from engine.state import state_hash
    cfg = default_config()
    w = build_world(seed=seed, n=n, config=cfg)
    e = w["engine"]
    for r in range(rounds):
        e.run_round(r)
    recs = e.ledger.records
    fam = collections.Counter(x["type"] for x in recs)
    json.dump({"mode": mode, "state_hash": state_hash(e.state), "len": len(recs),
               "families": dict(fam)}, open(out_path, "w"), ensure_ascii=False)


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--rounds", type=int, default=84)
    ap.add_argument("--json", default=None)
    ap.add_argument("--child", nargs=2, help="内部：<mode> <out>")
    ap.add_argument("--code-root", default=str(ROOT / "code"))
    args = ap.parse_args()
    sys.path.insert(0, args.code_root)

    if args.child:
        _run_child(args.child[0], args.seed, args.n, args.rounds, args.child[1], args.code_root)
        return

    live = _live_world_params()
    rep = {"seed": args.seed, "n": args.n, "rounds": args.rounds}

    print("[合成单元 —— 自建构造]")
    rep["unit"] = unit_tests(live)
    for k, v in rep["unit"].items():
        print(f"  {k}: {v}")

    # 世界级：两跑（prefix vs live）比 state_hash/族计数
    print("\n[世界级 ×2→×1 与四档]")
    outs = {}
    for mode in ("live", "prefix"):
        op = f"/tmp/t373_{mode}.json"
        subprocess.run([sys.executable, __file__, "--child", mode, op,
                        "--seed", str(args.seed), "--n", str(args.n), "--rounds", str(args.rounds),
                        "--code-root", args.code_root], check=True)
        outs[mode] = json.load(open(op))
    same_hash = outs["live"]["state_hash"] == outs["prefix"]["state_hash"]
    same_fam = outs["live"]["families"] == outs["prefix"]["families"]
    print(f"  live  : len={outs['live']['len']}  state_hash={outs['live']['state_hash'][:24]}…")
    print(f"  prefix: len={outs['prefix']['len']} state_hash={outs['prefix']['state_hash'][:24]}…")
    print(f"  state_hash 相同？{same_hash}   族计数相同？{same_fam}")
    rep["world"] = {"same_state_hash": same_hash, "same_families": same_fam,
                    "live_len": outs["live"]["len"], "prefix_len": outs["prefix"]["len"]}

    # 四档分类
    if not same_hash:
        cls = "① 行为变（去重改变 life 收到的 activity_weight ⇒ 行为变）"
    elif not same_fam:
        cls = "② 仅日志增（state_hash 同、事件集变）"
    else:
        cls = "③/④（本跑未观测到派生差异 ⇒ 该窗口内无同 did 双计⇒行为不变）"
    rep["four_class"] = cls
    print(f"  四档：{cls}")

    if args.json:
        Path(args.json).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"(机读：{args.json})")


if __name__ == "__main__":
    main()
