#!/usr/bin/env python3
"""T368 独立核验脚本 —— T367「世界层持续可见」实现。

前置门：T367 落地 + Leader 解冻后才执行本脚本（在此之前**只写不跑**）。
用法示例（T367 落地后按实际 CLI 调整）：
    python v2/evidence/T368/t368_verify.py --check 1 --log <on.jsonl>
    python v2/evidence/T368/t368_verify.py --check 3 --log-a <a.jsonl> --log-b <b.jsonl> \
        --seed 9 --n-windows 2 --code-root code
    python v2/evidence/T368/t368_verify.py --check 4 --log-dose0 <d0.jsonl> --log-off <off.jsonl>

设计原则：**可构造的证据** > 只看代码；每项含**反例/负例**；输出原始数字供报告引用。
本脚本只读（jsonl / config / code 目录），不改任何状态。
"""
from __future__ import annotations
import argparse, json, os, sys, hashlib
from collections import Counter, defaultdict


# ---------- helpers ----------
def load(path: str) -> list[dict]:
    recs = []
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                recs.append(json.loads(ln))
    return recs


def is_calendar_directive(rec: dict) -> bool:
    if rec.get("type") != "WORLD_DIRECTIVE" and rec.get("type") != "WORLD_GROUP_EVENT":
        return False
    p = rec.get("payload") or {}
    return p.get("source") == "calendar"


def payload(rec): return rec.get("payload") or {}


# ---------- Check 1: 窗口边界发一次（事件数证据）----------
def check1_window_boundary(log_path: str, src: str = "calendar"):
    """断言：日历常驻源【只在窗口边界】发一条 / 窗口；窗口内不逐回合发。
    证据 = 事件条数（非只看代码）。"""
    recs = load(log_path)
    cal = [r for r in recs if is_calendar_directive(r)]
    # 按 (mechanism_id/kind, source) 分窗口：窗口用 (start_round,end_round) 标识
    per_key = defaultdict(list)
    for r in cal:
        p = payload(r)
        key = (p.get("mechanism_id") or p.get("kind"), p.get("start_round"),
               p.get("end_round"))
        per_key[key].append(r)
    print(f"[C1] 日志 = {log_path}")
    print(f"[C1] calendar 发的 DIRECTIVE/GROUP_EVENT 总条数 = {len(cal)}")
    print(f"[C1] distinct 窗口(mechanism,start,end) 数 = {len(per_key)}")
    multi = {k: len(v) for k, v in per_key.items() if len(v) > 1}
    for k, v in sorted(per_key.items(), key=lambda kv: str(kv[0])):
        print(f"       {k}: {len(v)} 条  rounds={sorted(r.get('round') for r in v)[:6]}")
    # 反例探测：若“窗口内逐回合发”，则同一 (mechanism,start,end) 会有“很多条”或 round 连续
    verdict = "PASS: 每窗口 1 条" if not multi else f"FAIL: 存在多发的窗口 {multi}"
    print(f"[C1] verdict = {verdict}")
    return not multi


# ---------- Check 2: 退让不复活（构造性 + 反向负例）----------
NEW_SOURCE_PATTERNS = ["wd.calendar.daypart", "daypart_source", "calendar.daypart",
                       "def plan_daypart", "TIME_SOURCE_DAYPART"]
def check2_no_new_time_source(code_root: str):
    """构造性核对：码中不存在“新造时间源”。"""
    hits = []
    for dirpath, _, files in os.walk(code_root):
        if "__pycache__" in dirpath: continue
        for fn in files:
            if not fn.endswith(".py"): continue
            fp = os.path.join(dirpath, fn)
            try: txt = open(fp, encoding="utf-8").read()
            except Exception: continue
            for pat in NEW_SOURCE_PATTERNS:
                if pat in txt:
                    hits.append((fp, pat))
    print(f"[C2] 新造时间源命中 = {hits if hits else '无'}")
    # kind 枚举增量核对（设计声明 14→15，只新增 abundance；daypart 不得作为新 kind）
    wd = os.path.join(code_root, "engine", "world_director.py")
    kinds = []
    try:
        import re
        m = re.search(r"KINDS?\s*=\s*[\[\(\{]([^\]\)\}]*)[\]\)\}]", open(wd, encoding="utf-8").read())
        if m: kinds = re.findall(r"\"([a-z_]+)\"", m.group(1))
    except Exception as e:
        print(f"[C2] kind 解析失败：{e}")
    print(f"[C2] 现有 kind = {kinds}")
    has_daypart_kind = "daypart" in kinds
    has_abundance = "abundance" in kinds
    print(f"[C2] 'daypart' 作为独立 kind？ {has_daypart_kind}（应为 False）")
    print(f"[C2] 'abundance' 新增 kind 在场？ {has_abundance}（应为 True；14→15）")
    # schedule.cadence 不得含 daypart（登记草稿 §1 R1）
    cadence_daypart = False
    for dirpath, _, files in os.walk(code_root):
        if "__pycache__" in dirpath: continue
        for fn in files:
            if fn.endswith(".py"):
                try: txt = open(os.path.join(dirpath, fn), encoding="utf-8").read()
                except Exception: continue
                if '"cadence"' in txt and "daypart" in txt:
                    cadence_daypart = True
    print(f"[C2] schedule.cadence 含 daypart？ {cadence_daypart}（应为 False）")
    ok = (not hits) and (not has_daypart_kind) and has_abundance and (not cadence_daypart)
    print(f"[C2] verdict = {'PASS' if ok else 'FAIL'}")
    return ok


# ---------- Check 3: jitter 确定性可重建 ----------
def _jitter_series(recs, src="calendar"):
    out = []
    for r in recs:
        p = payload(r)
        if is_calendar_directive(r) and ("jitter_bp" in p or "jitter" in p):
            out.append(((p.get("start_round"), p.get("mechanism_id") or p.get("kind")),
                        p.get("jitter_bp", p.get("jitter"))))
    return out


def check3_jitter_determinism(a_path, b_path, seed, n_windows, code_root):
    a, b = _jitter_series(load(a_path)), _jitter_series(load(b_path))
    same = (a == b)
    print(f"[C3] A 与 B（同 seed={seed}）jitter 序列逐条相等？ {same}  |A|={len(a)} |B|={len(b)}")
    print(f"[C3] A 前 5：{a[:5]}")
    # 离线重算：rng_branch(seed,"world_calendar",window_index) -> 与日志比较
    sys.path.insert(0, code_root)
    try:
        from engine.rng import draw_u64
        recomputed = []
        for wi in range(n_windows):
            v = draw_u64(int(seed), "world_calendar", int(wi), 0, 1)[0]
            recomputed.append(v & 0x7fffffff)  # 与实现约定一致前先打印，供人工核对
        print(f"[C3] 离线重算（draw_u64 seed,world_calendar,wi,0）前几项 = {recomputed[:5]}")
        print("[C3] ⚠️ 需与实现约定的 jitter 派生式对齐后再判等（window_index 语义/取模）")
    except Exception as e:
        print(f"[C3] 离线重算不可用：{e}")
    print(f"[C3] verdict = {'PASS(同seed逐条相等)' if same else 'FAIL: 同 seed 两跑不一致'}")
    return same


# ---------- Check 4: 三保底 + 剂量（dose=0 逐条等价）----------
def _stream_sig(recs):
    return Counter(r.get("type") for r in recs)


def _state_hashes(recs):
    return [payload(r).get("state_hash") for r in recs if r.get("type") in ("TURN_SEAL", "ROUND_END") and payload(r).get("state_hash")]


def check4_dose_zero_equivalence(dose0_path, off_path):
    d0, off = load(dose0_path), load(off_path)
    s_d0, s_off = _stream_sig(d0), _stream_sig(off)
    types_equal = (s_d0 == s_off)
    h_d0, h_off = _state_hashes(d0), _state_hashes(off)
    hash_equal = (h_d0 == h_off)
    print(f"[C4] dose=0 vs 无日历：事件类型计数相等？ {types_equal}")
    if not types_equal:
        keys = set(s_d0) | set(s_off)
        diff = {k: (s_d0.get(k, 0), s_off.get(k, 0)) for k in keys if s_d0.get(k, 0) != s_off.get(k, 0)}
        print(f"[C4] 差异 = {diff}")
    print(f"[C4] state_hash 序列相等？ {hash_equal}  |d0|={len(h_d0)} |off|={len(h_off)}")
    ok = types_equal and hash_equal
    print(f"[C4] verdict = {'PASS' if ok else 'FAIL'}")
    return ok


# ---------- Check 5: 可感度闸 A（slot 级持续性）----------
def check5_gate_a(log_on, log_off):
    """从日志复算受影响族的 slot 级偏置覆盖率（≥70% slot 非零）。
    ⚠️ 需 T367 落地后按实际事件字段填充 slot 口径。"""
    on, off = load(log_on), load(log_off)
    # TODO(T367 落地后)：按受影响 place（hall/plaza）或 resource_factor 计算 per-slot delta
    print("[C5] 闸 A：需 T367 落地后按实际 slot 口径复算（本骨架先占位）")
    print("[C5] 判据：|Δ|≥5% 且 ≥2/3 seed 同向 且 窗口内 ≥70% slot 非零偏置")
    print("[C5] ⚠️ 恒定偏移须标 mode=constant_offset；有起止/过渡带标 mode=dynamic")


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", type=int, required=True, choices=[1, 2, 3, 4, 5])
    ap.add_argument("--log"); ap.add_argument("--log-a"); ap.add_argument("--log-b")
    ap.add_argument("--log-dose0"); ap.add_argument("--log-off")
    ap.add_argument("--log-on")
    ap.add_argument("--seed", type=int, default=9); ap.add_argument("--n-windows", type=int, default=2)
    ap.add_argument("--code-root", default="code")
    a = ap.parse_args()
    if a.check == 1: check1_window_boundary(a.log)
    elif a.check == 2: check2_no_new_time_source(a.code_root)
    elif a.check == 3: check3_jitter_determinism(a.log_a, a.log_b, a.seed, a.n_windows, a.code_root)
    elif a.check == 4: check4_dose_zero_equivalence(a.log_dose0, a.log_off)
    elif a.check == 5: check5_gate_a(a.log_on, a.log_off)


if __name__ == "__main__":
    main()
