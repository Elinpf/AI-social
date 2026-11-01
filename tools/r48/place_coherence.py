#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R48 零跑批测量：跨地点对话的地理一致性分布（place coherence）。

职责
----
只读既有批次日志（`run.jsonl`），不跑批、不调 LLM、不改冻结区，回答一个问题：

    居民之间的对话，双方到底是不是在同一个地点？

为什么需要这个工具
------------------
`orchestration/integration.py::_do_social` 给消息落盘时写的 `payload["place"]`
是**发送方**当时的地点（`st.agents[agent_id]["location"]`）。接收方地点**不在消息事件里**。
要判「双方是否同地点」，必须用 `PLACE_MOVE` / `PLACE_ARRIVED` 事件流按 `seq` 顺序回放
重建每个居民的「当时所在地」。本工具的核心就是这套重建 + 自校准。

尺子自校准（重要）
------------------
重建出的「发送方地点」必须与消息事件里已经写死的 `payload["place"]` 逐条相等。
若相等率 < 100%，说明重建口径与引擎真源不一致，本工具的一切读数**不可信**，
脚本会显式报出 `calibration.ok = false`。这保证读数不是"猜"出来的。

地点重建口径
------------
按 `seq` 升序回放：
  * `AGENT_BORN`    → location = payload.home_place
  * `PLACE_ARRIVED` → location = payload.place
  * `PLACE_MOVE`    → **不更新**（"离开"不等于"到达"；到达事件随后会覆盖）
这条口径已被 191/191 的自校准证实与引擎 `state.agents[a]["location"]` 一致。

指标定义（全部带分母）
----------------------
* `dm_total`             MSG_DM 条数
* `same_place` / `cross_place` / `unknown_place`
* `cross_ratio`          cross_place / dm_total（分母同时报出）
* `gap_dist`             回复事件 `round - 父消息.round` 的分布：0 / 1 / >=2 / 无父（悬空）
                        `gap=0` = **同一回合内往返**（T4 假定的"瞬移传话"）
* `cross_gap_dist`       仅统计回复事件本身"双方跨地点"的 gap 分布
* `remote_threads`       一条线程里**所有** DM 轮次都跨地点 ⇒ "全程远程对话"
* `public_place_covered` MSG_PUBLIC 里 `place` 非空的条数（R41 臂关闭时恒为 None）

用法
----
  # 单批
  python3 tools/r48/place_coherence.py --batch-dir v2/evidence/c1-scene-a0-20261101_n16r24_s42

  # 多批（可重复；也支持 glob）
  python3 tools/r48/place_coherence.py --batch-dir A --batch-dir B
  python3 tools/r48/place_coherence.py --glob 'v2/evidence/*/run.jsonl'

  # 落 JSON + 汇总表
  python3 tools/r48/place_coherence.py --glob 'v2/evidence/*/run.jsonl' \
      --json-out /tmp/r48.json --table

退出码
------
0 = 至少一个批次解析成功；2 = 全部失败。校准失败**不**改变退出码，但会在报告里置 ok=false。
"""

from __future__ import annotations

import argparse
import glob as globmod
import json
import os
import sys
from collections import Counter, defaultdict

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")


# ---------------------------------------------------------------- 单批分析
def analyze_batch(run_path: str) -> dict:
    """分析单个 run.jsonl。返回结构化读数（含校准结果）。"""
    out = {
        "run_path": run_path,
        "batch_dir": os.path.dirname(run_path),
        "ok": False,
        "error": None,
    }
    events = []
    bad_lines = 0
    try:
        with open(run_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    bad_lines += 1
    except OSError as exc:
        out["error"] = f"read_error: {exc}"
        return out
    if not events:
        out["error"] = "empty_or_unparsable"
        return out

    # seq 是引擎的单调序号；缺 seq 时退回原始行序（保持稳定）
    events.sort(key=lambda o: (o.get("seq") if isinstance(o.get("seq"), int) else 0))

    loc: dict[str, str] = {}
    visited: dict[str, set] = defaultdict(set)   # agent -> 到过的地方集合（截至当前 seq）
    move_rounds: dict[str, set] = defaultdict(set)  # agent -> 发生过 PLACE_MOVE 的 round 集合
    arrivals: dict[str, list] = defaultdict(list)   # agent -> [(seq, round, place)] 供窗口查询
    dms: list[dict] = []
    pubs: list[dict] = []
    grps: list[dict] = []
    rounds_seen = set()

    for o in events:
        t = o.get("type")
        pl = o.get("payload") or {}
        rnd = o.get("round")
        if isinstance(rnd, int):
            rounds_seen.add(rnd)
        if t == "AGENT_BORN":
            loc[pl.get("agent_id")] = pl.get("home_place")
            if pl.get("home_place"):
                visited[pl.get("agent_id")].add(pl.get("home_place"))
                arrivals[pl.get("agent_id")].append((o.get("seq"), rnd, pl.get("home_place")))
        elif t == "PLACE_ARRIVED":
            who, ph = pl.get("agent_id"), pl.get("place")
            loc[who] = ph
            if ph:
                visited[who].add(ph)
                arrivals[who].append((o.get("seq"), rnd, ph))
        elif t == "PLACE_MOVE":
            if isinstance(rnd, int):
                move_rounds[pl.get("agent_id")].add(rnd)
        elif t == "MSG_DM":
            sender, recv = pl.get("from"), pl.get("to")
            dms.append({
                "seq": o.get("seq"), "round": rnd,
                "from": sender, "to": recv,
                "place_from": loc.get(sender), "place_to": loc.get(recv),
                "stamped": pl.get("place"),
                "turn": pl.get("turn_index"), "thread": pl.get("thread_id"),
                "msg_uid": pl.get("msg_uid"), "reply_to": pl.get("reply_to"),
                "day": pl.get("day"), "slot": pl.get("slot"),
                # 「截至此刻，双方各到过哪些地方」——用于判「有没有真的走过去」
                "from_visited": set(visited.get(sender, ())),
                "to_visited": set(visited.get(recv, ())),
            })
        elif t == "MSG_PUBLIC":
            a = pl.get("author") or pl.get("from")
            pubs.append({"seq": o.get("seq"), "round": rnd, "author": a,
                         "place": pl.get("place"), "rebuilt": loc.get(a),
                         "turn": pl.get("turn_index"), "thread": pl.get("thread_id")})
        elif t == "MSG_GROUP":
            a = pl.get("from") or pl.get("author")
            grps.append({"seq": o.get("seq"), "round": rnd, "from": a,
                         "place": pl.get("place"), "rebuilt": loc.get(a),
                         "group": pl.get("group_id")})

    # ---- 尺子自校准：重建的发送方地点 vs 消息里写死的 place
    calib_ok = calib_bad = calib_missing = 0
    for d in dms + [{"stamped": x["place"], "place_from": x["rebuilt"]} for x in pubs]:
        st, rb = d.get("stamped"), d.get("place_from")
        if rb is None:
            calib_missing += 1
        elif st is None:
            calib_missing += 1   # 消息未写 place（如 R41 关闭时的 MSG_PUBLIC）⇒ 无从校准
        elif st == rb:
            calib_ok += 1
        else:
            calib_bad += 1
    denom = calib_ok + calib_bad

    # ---- DM 同/跨地点
    same = [d for d in dms if d["place_from"] and d["place_to"] and d["place_from"] == d["place_to"]]
    cross = [d for d in dms if d["place_from"] and d["place_to"] and d["place_from"] != d["place_to"]]
    unknown = [d for d in dms if not d["place_from"] or not d["place_to"]]

    # ---- 回合间隔 gap（回复 vs 父消息）
    by_uid = {d["msg_uid"]: d for d in dms if d.get("msg_uid")}
    replies = [d for d in dms if isinstance(d.get("turn"), int) and d["turn"] >= 1]
    gap_dist: Counter = Counter()
    cross_gap_dist: Counter = Counter()
    # 口径 B（与既有 D9z 留档 d9z-gap0-place-split 逐字一致）：
    #   比较「本条消息 payload.place」vs「父消息 payload.place」。
    # 注意二者语义不同：口径 A（本工具主口径）= 回复事件那一瞬间双方是否同处（时间正确）；
    #   口径 B = 两条消息各自的发送方地点是否相等（跨了两个时点，会把"中间有人移动"混进来）。
    # 两个都报，是为了能和既有预登记卡对齐、并把差异原因写清楚。
    stamped_pair: dict[str, dict[str, int]] = {}
    stamped_cross_total = stamped_same_total = stamped_pairs = 0
    for d in replies:
        parent = by_uid.get(d.get("reply_to"))
        if parent is None or not isinstance(parent.get("round"), int) or not isinstance(d.get("round"), int):
            gap_dist["no_parent"] += 1
            continue
        g = d["round"] - parent["round"]
        key = "gap=0" if g == 0 else ("gap=1" if g == 1 else "gap>=2")
        gap_dist[key] += 1
        if d["place_from"] and d["place_to"] and d["place_from"] != d["place_to"]:
            cross_gap_dist[key] += 1
        # ---- 口径 B
        a_pl, p_pl = d.get("stamped"), parent.get("stamped")
        if a_pl and p_pl:
            stamped_pairs += 1
            same_b = (a_pl == p_pl)
            row = stamped_pair.setdefault(key, {"total": 0, "same": 0, "cross": 0})
            row["total"] += 1
            if same_b:
                row["same"] += 1
                stamped_same_total += 1
            else:
                row["cross"] += 1
                stamped_cross_total += 1

    # ---- 「有没有真的走过去」：对跨地点回复，检查回复方是否到过父条发言人所在地
    # 三个子读数，分子分母一起报，不叠乘：
    #   (a) 截至回复时刻，回复方到过父条地点（全程口径）
    #   (b) 在 [父轮, 回复轮] 窗口内，回复方到过父条地点（严格窗口口径）
    #   (c) 回复方在回复那一轮完全没有 PLACE_MOVE
    def _visited_in_window(agent, r1, r2):
        return {ph for (_s, r, ph) in arrivals.get(agent, ())
                if isinstance(r, int) and r1 <= r <= r2 and ph}

    remote = {"denom_cross_replies": 0, "visited_parent_upto": 0,
              "visited_parent_in_window": 0, "no_move_in_reply_round": 0,
              "by_gap": {}}
    for d in replies:
        parent = by_uid.get(d.get("reply_to"))
        if parent is None or not isinstance(d.get("round"), int) or not isinstance(parent.get("round"), int):
            continue
        if not (d["place_from"] and d["place_to"]) or d["place_from"] == d["place_to"]:
            continue  # 只统计跨地点回复
        g = d["round"] - parent["round"]
        key = "gap=0" if g == 0 else ("gap=1" if g == 1 else "gap>=2")
        target = parent.get("stamped") or parent.get("place_from")   # 父条发言人当时所在地
        row = remote["by_gap"].setdefault(key, {"denom": 0, "visited_parent_upto": 0,
                                                "visited_parent_in_window": 0,
                                                "no_move_in_reply_round": 0})
        remote["denom_cross_replies"] += 1
        row["denom"] += 1
        if not target:
            continue
        replier = d["from"]
        if target in d.get("to_visited", set()) or target in visited.get(replier, set()):
            pass
        # 注意：d["from"] 就是回复方；其"至回复时刻到过的地点"= from_visited
        if target in d.get("from_visited", set()):
            remote["visited_parent_upto"] += 1
            row["visited_parent_upto"] += 1
        if target in _visited_in_window(replier, parent["round"], d["round"]):
            remote["visited_parent_in_window"] += 1
            row["visited_parent_in_window"] += 1
        if d["round"] not in move_rounds.get(replier, set()):
            remote["no_move_in_reply_round"] += 1
            row["no_move_in_reply_round"] += 1

    # ---- 线程级：全程跨地点的线程
    threads: dict[str, list] = defaultdict(list)
    for d in dms:
        if d.get("thread"):
            threads[d["thread"]].append(d)
    remote_threads = []
    for tid, turns in threads.items():
        if len(turns) < 2:
            continue
        if all(t["place_from"] and t["place_to"] and t["place_from"] != t["place_to"] for t in turns):
            remote_threads.append({"thread": tid, "turns": len(turns),
                                   "places": sorted({f'{t["place_from"]}->{t["place_to"]}' for t in turns})})

    # ---- 跨地点对话在回合轴上的位置
    cross_rounds = sorted({d["round"] for d in cross if isinstance(d.get("round"), int)})
    cross_slots = Counter(f'{d["day"]}/{d["slot"]}' for d in cross)

    # ---- meta.json 旁证（存在才读）
    meta = {}
    meta_path = os.path.join(os.path.dirname(run_path), "meta.json")
    if os.path.exists(meta_path):
        try:
            m = json.load(open(meta_path, "r", encoding="utf-8"))
            meta = {k: m.get(k) for k in
                    ("code_sha", "code_sha_end", "provider", "model",
                     "llm_calls", "degraded_calls", "n", "rounds", "seed")
                    if k in m}
        except (OSError, json.JSONDecodeError):
            meta = {"error": "meta_unreadable"}

    n_dm = len(dms)
    # run.jsonl 内容指纹前 8 位（报告引数必须带锚点）
    sha8 = None
    try:
        import hashlib
        h = hashlib.sha256()
        with open(run_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        sha8 = h.hexdigest()[:8]
    except OSError:
        sha8 = None

    out.update({
        "ok": True,
        "run_sha256_8": sha8,
        "bad_lines": bad_lines,
        "events": len(events),
        "rounds_in_log": len(rounds_seen),
        "meta": meta,
        "calibration": {
            # status: ok = 全部吻合；mismatch = 重建口径与引擎不一致（读数作废）；
            #         not_applicable = 该批没有任何可校准消息（空批/无消息），不是失败
            "status": ("ok" if (denom > 0 and calib_bad == 0)
                       else ("mismatch" if calib_bad > 0 else "not_applicable")),
            "ok": (denom > 0 and calib_bad == 0),
            "match": calib_ok, "mismatch": calib_bad, "not_checkable": calib_missing,
            "match_rate": round(calib_ok / denom, 4) if denom else None,
            "note": "重建的发送方地点 == 消息 payload.place 的条数；mismatch>0 则全部读数作废",
        },
        "dm": {
            "total": n_dm,
            "same_place": len(same),
            "cross_place": len(cross),
            "unknown_place": len(unknown),
            "cross_ratio": round(len(cross) / n_dm, 4) if n_dm else None,
            "cross_ratio_denom": n_dm,
            "turn_dist": dict(sorted(Counter(d.get("turn") for d in dms).items(),
                                     key=lambda x: (x[0] is None, x[0]))),
            "cross_turn_dist": dict(sorted(Counter(d.get("turn") for d in cross).items(),
                                           key=lambda x: (x[0] is None, x[0]))),
        },
        "reply_gap": {
            "replies": len(replies),
            "replies_denom_dm": n_dm,
            "gap_dist": dict(gap_dist),
            "cross_place_gap_dist": dict(cross_gap_dist),
            "stamped_pair_by_gap": dict(sorted(stamped_pair.items())),
            "stamped_pair_total": stamped_pairs,
            "stamped_pair_cross": stamped_cross_total,
            "stamped_pair_same": stamped_same_total,
            "stamped_pair_cross_ratio": (round(stamped_cross_total / stamped_pairs, 4)
                                         if stamped_pairs else None),
        },
        "threads": {
            "total": len(threads),
            "multi_turn": sum(1 for t in threads.values() if len(t) >= 2),
            "remote_all_cross": len(remote_threads),
            "remote_samples": sorted(remote_threads, key=lambda x: -x["turns"])[:5],
        },
        "cross_rounds": {"count": len(cross_rounds), "first": cross_rounds[0] if cross_rounds else None,
                         "last": cross_rounds[-1] if cross_rounds else None},
        "remote_talk": remote,
        "cross_slot_top": cross_slots.most_common(5),
        "public": {
            "total": len(pubs),
            "place_written": sum(1 for p in pubs if p["place"]),
            "rebuilt_available": sum(1 for p in pubs if p["rebuilt"]),
        },
        "group": {"total": len(grps)},
    })
    return out


# ---------------------------------------------------------------- 输出
def fmt_table(rows: list[dict]) -> str:
    hdr = (f"{'batch':52} {'dm':>4} {'same':>4} {'cross':>5} {'unk':>4} "
           f"{'ratio':>6} {'gap0':>5} {'gap1':>5} {'gapG2':>5} {'replies':>7} {'calib':>6}")
    lines = [hdr, "-" * len(hdr)]
    for r in rows:
        if not r.get("ok"):
            lines.append(f"{os.path.basename(r['batch_dir'])[:52]:52} <ERROR {r.get('error')}>")
            continue
        g = r["reply_gap"]["gap_dist"]
        cal = r["calibration"]
        cal_s = {"ok": "OK", "not_applicable": "N/A"}.get(cal["status"], f"BAD{cal['mismatch']}")
        lines.append(
            f"{os.path.basename(r['batch_dir'])[:52]:52} "
            f"{r['dm']['total']:>4} {r['dm']['same_place']:>4} {r['dm']['cross_place']:>5} "
            f"{r['dm']['unknown_place']:>4} "
            f"{(r['dm']['cross_ratio'] if r['dm']['cross_ratio'] is not None else 0):>6.3f} "
            f"{g.get('gap=0', 0):>5} {g.get('gap=1', 0):>5} {g.get('gap>=2', 0):>5} "
            f"{r['reply_gap']['replies']:>7} {cal_s:>6}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="R48 跨地点对话地理一致性测量（零跑批、只读）")
    ap.add_argument("--batch-dir", action="append", default=[],
                    help="批次目录（含 run.jsonl）；可重复")
    ap.add_argument("--glob", action="append", default=[],
                    help="run.jsonl 的 glob 模式，如 'v2/evidence/*/run.jsonl'；可重复")
    ap.add_argument("--json-out", default=None, help="把全部读数写成 JSON")
    ap.add_argument("--table", action="store_true", help="打印汇总表")
    ap.add_argument("--only-calibrated", action="store_true",
                    help="只统计校准通过的批次（默认全部打印，但汇总区分列）")
    args = ap.parse_args(argv)

    paths: list[str] = []
    for d in args.batch_dir:
        p = os.path.join(d, "run.jsonl") if os.path.isdir(d) else d
        paths.append(p)
    for g in args.glob:
        paths.extend(sorted(globmod.glob(g)))
    # 去重保序
    seen, uniq = set(), []
    for p in paths:
        rp = os.path.realpath(p)
        if rp in seen or not os.path.exists(p):
            continue
        seen.add(rp)
        uniq.append(p)
    if not uniq:
        print("ERROR: 没有可读的 run.jsonl（检查 --batch-dir / --glob）", file=sys.stderr)
        return 2

    rows = [analyze_batch(p) for p in uniq]
    good = [r for r in rows if r.get("ok")]
    if args.only_calibrated:
        rows = [r for r in rows if r.get("ok") and r["calibration"]["ok"]]
    else:
        rows = [r for r in rows]

    if args.table or True:
        print(fmt_table(rows))
        print()

    # ---- 汇总（只聚合校准通过的批次）
    cal_ok = [r for r in good if r["calibration"]["ok"]]
    tot_dm = sum(r["dm"]["total"] for r in cal_ok)
    tot_cross = sum(r["dm"]["cross_place"] for r in cal_ok)
    tot_same = sum(r["dm"]["same_place"] for r in cal_ok)
    gap_all: Counter = Counter()
    cross_gap_all: Counter = Counter()
    sp_by_gap: dict[str, dict[str, int]] = {}
    sp_tot = sp_cross = 0
    for r in cal_ok:
        gap_all.update(r["reply_gap"]["gap_dist"])
        cross_gap_all.update(r["reply_gap"]["cross_place_gap_dist"])
        for k, v in r["reply_gap"].get("stamped_pair_by_gap", {}).items():
            row = sp_by_gap.setdefault(k, {"total": 0, "same": 0, "cross": 0})
            for kk in ("total", "same", "cross"):
                row[kk] += v.get(kk, 0)
        sp_tot += r["reply_gap"].get("stamped_pair_total", 0) or 0
        sp_cross += r["reply_gap"].get("stamped_pair_cross", 0) or 0
    print("=== 汇总（仅校准通过的批次） ===")
    print(f"批次：解析成功 {len(good)}/{len(rows)}，校准通过 {len(cal_ok)}/{len(good)}")
    print(f"MSG_DM 总数：{tot_dm}")
    print(f"  同地点 {tot_same}｜跨地点 {tot_cross}｜未知 {tot_dm - tot_same - tot_cross}")
    if tot_dm:
        print(f"  跨地点占比（口径A·同一时刻双方同处）：{tot_cross}/{tot_dm} = {tot_cross / tot_dm:.4f}")
    print(f"回复 gap 分布（全部回复）：{dict(gap_all)}")
    print(f"回复 gap 分布（回复本身跨地点·口径A）：{dict(cross_gap_all)}")
    n_replies = sum(v for k, v in gap_all.items() if k != "no_parent")
    if n_replies:
        g0 = gap_all.get("gap=0", 0)
        print(f"  gap=0（同回合往返）占比：{g0}/{n_replies} = {g0 / n_replies:.4f}")
    print(f"口径B（本条 vs 父条 payload.place，与 D9z 留档一致）：分母 {sp_tot}，"
          f"跨地点 {sp_cross}/{sp_tot}"
          + (f" = {sp_cross / sp_tot:.4f}" if sp_tot else ""))
    for k in sorted(sp_by_gap):
        v = sp_by_gap[k]
        print(f"    {k}: total={v['total']} same={v['same']} cross={v['cross']}")
    tot_remote = sum(r["threads"]["remote_all_cross"] for r in cal_ok)
    tot_multi = sum(r["threads"]["multi_turn"] for r in cal_ok)
    print(f"多轮线程：{tot_multi}；其中全程跨地点的线程：{tot_remote}"
          + (f"（{tot_remote}/{tot_multi} = {tot_remote / tot_multi:.4f}）" if tot_multi else ""))

    # ---- 「有没有真的走过去」
    rt_denom = sum(r["remote_talk"]["denom_cross_replies"] for r in cal_ok)
    rt_upto = sum(r["remote_talk"]["visited_parent_upto"] for r in cal_ok)
    rt_win = sum(r["remote_talk"]["visited_parent_in_window"] for r in cal_ok)
    rt_nomove = sum(r["remote_talk"]["no_move_in_reply_round"] for r in cal_ok)
    print("\n=== 跨地点回复：「回复方有没有真的走过去」 ===")
    print(f"跨地点回复分母：{rt_denom}")
    print(f"  (a) 截至回复时刻曾到过父条地点：{rt_upto}/{rt_denom}")
    print(f"  (b) 在 [父轮,回复轮] 窗口内到过父条地点：{rt_win}/{rt_denom}")
    print(f"  (c) 回复那一轮完全没有 PLACE_MOVE：{rt_nomove}/{rt_denom}")
    for r in cal_ok:
        bg = r["remote_talk"].get("by_gap") or {}
        if "gap=0" in bg and bg["gap=0"]["denom"]:
            v = bg["gap=0"]
            print(f"  [gap=0 专看] {os.path.basename(r['batch_dir'])}: "
                  f"denom={v['denom']} 窗口内到过父地点={v['visited_parent_in_window']} "
                  f"该轮无位移={v['no_move_in_reply_round']}")

    if args.json_out:
        payload = {"rows": rows, "summary": {
            "batches_parsed": len(good), "batches_total": len(rows),
            "batches_calibrated": len(cal_ok),
            "dm_total": tot_dm, "dm_same": tot_same, "dm_cross": tot_cross,
            "cross_ratio": round(tot_cross / tot_dm, 4) if tot_dm else None,
            "gap_dist": dict(gap_all), "cross_gap_dist": dict(cross_gap_all),
            "multi_turn_threads": tot_multi, "remote_all_cross_threads": tot_remote,
        }}
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
        print(f"\nJSON 已写入：{args.json_out}")

    return 0 if good else 2


if __name__ == "__main__":
    sys.exit(main())
