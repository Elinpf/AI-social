#!/usr/bin/env python3
"""calib_report.py —— 标定批三项产出（斜率 / 降级 / 墙钟）+ places 与双线程数

用途：三点标定（16×8 / 32×8 / 16×15）跑完后，一条命令出全部判读输入，
避免"跑完只剩一个墙钟数"。

口径（写死，见 v2/refs/three-questions-before-any-number.md §11）：
  相邻对 = 线程内 ≥2 条 MSG 的连续回复对；分母 = rounds − 1（round 0 为预热轮）
  线程数 = 两个值：全类型 / 仅有回复（≥2 条 MSG）
  places = 两个值：到过的（含 PLACE_ARRIVED）/ 说过话的（仅 MSG_*）；**不含 residence 的可对话口径另报**
  降级   = LLM_CALL.payload.degraded 为真、tokens_in==0（缓存）、SYSTEM_ERROR 计数

用法：
  calib_report.py <run_dir>            # 目录含 run.jsonl / launch_cmd.txt
  calib_report.py --selftest
"""
import json, sys, os, collections, datetime

def load(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows

def report(run_dir):
    rj = os.path.join(run_dir, "run.jsonl")
    if not os.path.isfile(rj):
        print(f"FATAL: 缺 {rj}", file=sys.stderr); return 3
    rows = load(rj)
    if len(rows) < 100:
        print(f"FATAL: 只有 {len(rows)} 行（<100），不足以标定", file=sys.stderr); return 3

    msg = [r for r in rows if r.get("type") in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")]
    if not msg:
        print("FATAL: 无 MSG_* 事件", file=sys.stderr); return 3
    idx = {}
    for r in msg:
        p = r.get("payload") or {}
        idx[p.get("msg_uid") or p.get("msg_id")] = r.get("round")

    # ---- 相邻对（仅线程内 ≥2 条） ----
    by_thread = collections.defaultdict(list)
    for r in msg:
        p = r.get("payload") or {}
        by_thread[p.get("thread_id")].append(r)
    rep_threads = {t: v for t, v in by_thread.items() if len(v) >= 2}

    pairs = 0; gaps = collections.Counter()
    for t, rs in rep_threads.items():
        for r in rs:
            p = r.get("payload") or {}
            rt = p.get("reply_to")
            if rt and rt in idx:
                g = (r.get("round") or 0) - (idx[rt] or 0)
                pairs += 1; gaps[g] += 1

    # ---- rounds / 斜率 ----
    rounds = max((r.get("round") or 0) for r in rows) + 1
    slope = pairs / (rounds - 1) if rounds > 1 else float("nan")

    # ---- places 两值 + 排除 residence ----
    to_visited = collections.defaultdict(set)
    to_spoke = collections.defaultdict(set)
    for r in rows:
        p = r.get("payload") or {}
        pl = p.get("place")
        who = p.get("from") or p.get("author") or r.get("actor")
        if not pl or not who:
            continue
        if r.get("type") in ("PLACE_ARRIVED", "PLACE_MOVE"):
            to_visited[pl].add(who)
        if r.get("type") in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
            to_visited[pl].add(who); to_spoke[pl].add(who)
    def npairs(d, exclude_residence=False):
        return sum(len(v) * (len(v) - 1) // 2 for k, v in d.items()
                   if not (exclude_residence and k == "residence"))

    # ---- 降级 / 缓存 / 错误 ----
    calls = [r for r in rows if r.get("type") == "LLM_CALL"]
    degraded = sum(1 for r in calls if (r.get("payload") or {}).get("degraded"))
    cached = sum(1 for r in calls if (r.get("payload") or {}).get("cached"))
    no_tok = sum(1 for r in calls if not (r.get("payload") or {}).get("tokens_in"))
    errs = sum(1 for r in rows if r.get("type") == "SYSTEM_ERROR")

    # ---- 墙钟 ----
    wall = "CANNOT-VERIFY（launch_cmd 无 started/finished）"
    cmd = os.path.join(run_dir, "launch_cmd.txt")
    if os.path.isfile(cmd):
        txt = open(cmd, encoding="utf-8").read()
        st = fin = None
        for line in txt.splitlines():
            if line.startswith("started_at="): st = line.split("=", 1)[1]
            if line.startswith("finished_at="): fin = line.split("=", 1)[1]
        if st and fin:
            try:
                a = datetime.datetime.fromisoformat(st); b = datetime.datetime.fromisoformat(fin)
                wall = f"{(b - a).total_seconds() / 60:.1f} 分钟（{st} → {fin}）"
            except Exception:
                wall = f"{st} → {fin}"
        elif st:
            wall = f"started_at={st}；finished_at 缺失 ⇒ 墙钟 CANNOT-VERIFY"

    print(f"== {run_dir} ==")
    print(f"MSG 总数            = {len(msg)}")
    print(f"线程数（全类型）    = {len(by_thread)}")
    print(f"线程数（有回复≥2条） = {len(rep_threads)}")
    print(f"相邻对              = {pairs}")
    print(f"rounds              = {rounds}（有效轮 = {rounds - 1}）")
    print(f"**斜率（对/有效轮） = {slope:.2f}**")
    print(f"gap 分布            = {dict(sorted(gaps.items()))}")
    print(f"places（到过）      = {len(to_visited)} ；配对数 = {npairs(to_visited)} ；**排除 residence 后 = {npairs(to_visited, True)}**")
    print(f"places（说过话）    = {len(to_spoke)} ；配对数 = {npairs(to_spoke)}")
    print(f"LLM_CALL total      = {len(calls)} ；degraded = {degraded} ；cached = {cached} ；tokens_in=0 = {no_tok}")
    print(f"SYSTEM_ERROR        = {errs}")
    print(f"墙钟                = {wall}")
    if degraded:
        print("**判读：degraded > 0 ⇒ 该批不得用于估墙钟（预置规则）**")
    return 0

def selftest():
    tgt = "v2/evidence/d9t-on_n16r24_s42"
    if not os.path.isdir(tgt):
        print("selftest SKIP（缺历史臂）"); return 0
    print("[selftest] 用历史臂 D9t ON 复算，期望：相邻对 125 / 有效轮 23 / 斜率 5.43")
    rc = report(tgt)
    return rc

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if len(sys.argv) < 2:
        print("用法: calib_report.py <run_dir> [--selftest]", file=sys.stderr); sys.exit(2)
    sys.exit(report(sys.argv[1]))
