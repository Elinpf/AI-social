#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R41V · 公开面接话 OFF/ON 两臂对比读数（纯只读、零跑批、零 LLM、确定性输出）。

纪律：
  * 单一尺子真源：本脚本**不自己读日志算 reply_to 形态**，而是各臂调用
    `tools/public_talk/public_talk_metrics.py`（仓库唯一尺子），再读它的 json 出对比。
  * 置信区间不重写公式：Wilson 单臂区间调 `tools/metrics/d9m_wilson_ci.py`（canonical =
    `tools/d5/dialogue_metrics.py::wilson_ci`，z=1.959964）；两臂比例差区间 **import**
    `tools/metrics/weather_readings.py::newcombe95`。口径不分叉。
  * 判据编号与阈值来自预登记卡 `v2/refs/prereg-r41v-public-talk-verify.md`，本脚本只做数，
    不「发明」结论；不写「显著」，分母 < 30 不报比率，分母 < 68 一律 probe。

用法：
    python3 tools/public_talk/compare_arms.py \
        --off v2/evidence/r41v_public_talk_n16r24_s42/off/run.jsonl \
        --on  v2/evidence/r41v_public_talk_n16r24_s42/on/run.jsonl \
        --off-meta .../off/meta.json --on-meta .../on/meta.json \
        --out v2/evidence/r41v_public_talk_readings/compare.json

退出码：0 正常出数（判据达标与否写进 json，不用退出码表达）/ 2 输入缺失 / 3 尺子调用失败
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RULER = REPO / "tools" / "public_talk" / "public_talk_metrics.py"
WILSON_TOOL = REPO / "tools" / "metrics" / "d9m_wilson_ci.py"
WEATHER_READINGS = REPO / "tools" / "metrics" / "weather_readings.py"

RATIO_MIN_DEN = 30   # 分母 < 30：只报事件数，不报比率
PROBE_DEN = 68       # 分母 < 68：probe=true


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def wilson(k: int, n: int) -> tuple[float, float] | None:
    """唯一真源：tools/metrics/d9m_wilson_ci.py --x k --n n（内部用 dialogue_metrics.wilson_ci）。"""
    if n <= 0:
        return None
    cp = subprocess.run([sys.executable, str(WILSON_TOOL), "--x", str(int(k)), "--n", str(int(n))],
                        capture_output=True, text=True)
    if cp.returncode != 0:
        return None
    try:
        d = json.loads(cp.stdout[cp.stdout.index("{"):])
    except Exception:
        return None
    row = d.get("rows", [{}])[0] if isinstance(d.get("rows"), list) else {}
    lo, hi = row.get("lo"), row.get("hi")
    return (lo, hi) if lo is not None and hi is not None else None


def run_ruler(log: Path, meta: Path | None, out: Path) -> dict:
    cmd = [sys.executable, str(RULER), "--log", str(log)]
    if meta:
        cmd += ["--meta", str(meta)]
    cmd += ["--out", str(out)]
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode != 0:
        raise SystemExit(f"[compare] 尺子调用失败 rc={cp.returncode}\n{cp.stdout}\n{cp.stderr}")
    return json.loads(out.read_text(encoding="utf-8"))


def struct_gap(log: Path) -> dict:
    """描述性旁证（**不是判据**）：结构缺口本来有多大。

    用仓库**真实实现**（不是复刻语义）对每条 `MSG_PUBLIC` 做两步判定：
      1. `life.dialogue_threads.is_replyable("MSG_PUBLIC", payload, me)` —— 类型白名单是否放行；
      2. `life.public_talk.is_replyable_public(payload, me, my_place, co_present)` —— 四条有界判据是否放行。
    候选回复者 = 日志中出现的全部 agent id（除作者自己）。co_present 给「最宽松」假设
    （非空，即假设我在场有同伴），以便单独暴露 place 缺失这一条缺口。

    纪律：导入 `code/life/*` 只读取，`sys.dont_write_bytecode=True` + `python3 -B` 调用，
    不在 `code/` 下留任何文件（`git status --porcelain -- code/` 由 preflight 独立复核）。
    """
    sys.path.insert(0, str(REPO / "code"))
    from life import dialogue_threads as DT          # noqa: PLC0415
    from life import public_talk as PT               # noqa: PLC0415

    msgs: list[dict] = []
    agents: set[str] = set()
    with log.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            ev = json.loads(raw)
            t = ev.get("type")
            if t not in ("MSG_PUBLIC", "MSG_DM", "MSG_GROUP"):
                continue
            pl = ev.get("payload") or {}
            a = pl.get("author") or pl.get("from")
            if a:
                agents.add(str(a))
            if t == "MSG_PUBLIC":
                msgs.append(pl)

    n = len(msgs)
    type_blocked = 0          # 按消息条数去重：所有候选都拒
    place_blocked = 0         # 按消息条数去重：最宽松 co_present 下仍被 place 拒
    passed_any = 0
    pairs_total = 0           # 展开口径：MSG_PUBLIC × 每个非作者候选 agents 的判定次数
    pairs_type_blocked = 0    # 展开口径：被类型白名单拒的判定次数
    pairs_place_blocked = 0   # 展开口径：最宽松 co_present 下仍被 place 判据拒的判定次数
    for pl in msgs:
        author = pl.get("author") or pl.get("from")
        cands = [a for a in sorted(agents) if a != author]
        pairs_total += len(cands)
        tb = sum(1 for me in cands if not DT.is_replyable("MSG_PUBLIC", pl, me))
        pb = sum(1 for me in cands
                 if not PT.is_replyable_public(pl, me, pl.get("place"), ["CO-PRESENT"]))
        pairs_type_blocked += tb
        pairs_place_blocked += pb
        if cands and tb == len(cands):
            type_blocked += 1
        if cands and pb == len(cands):
            place_blocked += 1
        if cands and any(DT.is_replyable("MSG_PUBLIC", pl, me) for me in cands):
            passed_any += 1

    return {
        "stat_unit": "两个口径并列，必须标清分母，不得混用",
        "not_a_judgment": True,
        "note": ("结构缺口规模（描述性旁证，不进任何判据）：ON 臂读数应显示该缺口被打开；"
                 "本段用仓库真实实现 life.dialogue_threads.is_replyable 与 "
                 "life.public_talk.is_replyable_public 逐条判定，不是语义复刻。"),
        # ---- 口径 A：按消息条数去重（分母 = MSG_PUBLIC 条数） ----
        "by_message": {
            "denominator": "MSG_PUBLIC 条数",
            "pub_instances": n,
            "type_whitelist_blocked_all_candidates": type_blocked,
            "best_case_co_present_place_blocked_all_candidates": place_blocked,
            "type_whitelist_passed_any_candidate": passed_any,
        },
        # ---- 口径 B：展开为「消息 × 非作者候选者」的判定次数（分母 = 判定对总数） ----
        "by_pair": {
            "denominator": "MSG_PUBLIC 条 × 每个非作者候选 agent（判定对总数）",
            "candidate_agents": len(agents),
            "pairs_total": pairs_total,
            "type_whitelist_blocked_pairs": pairs_type_blocked,
            "best_case_co_present_place_blocked_pairs": pairs_place_blocked,
        },
        "co_present_assumption": "最宽松：假设我在场有同伴（['CO-PRESENT']），只暴露 place 缺口",
        "co_present_is_upper_bound": True,
        "upper_bound_note": ("**这是上界口径**：连「假设在场有同伴」都过不去的判定，在真实 co_present 下只会更严；"
                             "引用时不得读成「实测结果」，它是结构缺口的上界估计。"),
    }


def reply_to_semantics(log: Path) -> dict:
    """事后诊断（**非判据**）：`payload.reply_to` 到底指向什么标识符。

    背景：`tools/public_talk/public_talk_metrics.py::reply_to_form()` 用
    「MSG_PUBLIC 的 `msg_id` 集合」判定 `real_message_id`（第 281 行 `msg_ids.add(pl['msg_id'])`），
    而本批实测 `reply_to` 存的是 **`msg_uid`**（形如 `42:189`）⇒ 真实接话会被归到 `other`。
    本函数用**日志自身**核对：reply_to 是否命中某条 MSG_* 的 `msg_uid`、是否与目标同 thread_id。

    纪律：这是跑完之后才发现的尺子口径差异，**不得**用它替换预登记分子；
    只能作为「尺子待修」的证据单列，替换分子须走预登记修订（prereg amendment）。
    """
    uid: dict[str, tuple] = {}
    pubs: list[dict] = []
    with log.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            ev = json.loads(raw)
            if ev.get("type") not in ("MSG_PUBLIC", "MSG_DM", "MSG_GROUP"):
                continue
            pl = ev.get("payload") or {}
            u = pl.get("msg_uid")
            if isinstance(u, str):
                uid[u] = (ev.get("type"), pl.get("msg_id"), pl.get("thread_id"))
            if ev.get("type") == "MSG_PUBLIC" and pl.get("reply_to") is not None:
                pubs.append(pl)

    hit_uid = 0
    hit_uid_same_thread = 0
    kinds: dict[str, int] = {}
    for pl in pubs:
        v = pl.get("reply_to")
        k = "other"
        if isinstance(v, str):
            if v in uid:
                k = "msg_uid_hit"
                hit_uid += 1
                if uid[v][2] and uid[v][2] == pl.get("thread_id"):
                    hit_uid_same_thread += 1
            elif v == "None":
                k = "string_None"
        kinds[k] = kinds.get(k, 0) + 1
    return {
        "not_a_judgment": True,
        "why": ("跑完后发现：ruler 的 `real_message_id` 判定用的是 MSG_PUBLIC 的 msg_id 集合，"
                "而 `reply_to` 实际存 msg_uid ⇒ 真实接话被算进 `other`。本段用日志自身核对，"
                "只作「尺子待修」证据，**不替换预登记分子**（换分子须 prereg amendment）。"),
        "pub_with_nonnull_reply_to": len(pubs),
        "reply_to_is_msg_uid_hit": hit_uid,
        "reply_to_is_msg_uid_hit_and_same_thread_id": hit_uid_same_thread,
        "classified": kinds,
        "target_types": {v: uid[v][0] for v in {pl.get("reply_to") for pl in pubs} if v in uid},
    }


def quota_guard(log: Path) -> dict:
    """R41V-C4：有界配额护栏（直接读 run.jsonl；纯只读）。

    口径（严格按 `code/life/public_talk.py` 语义复刻，**不按 round 分组**——一整天的一个
    slot 横跨多个 round，实测 morning 覆盖 round 0/1，故 slot 键 = (day, slot)）：
      * place 非 null 的 MSG_PUBLIC：同 (day, slot, place) 总数最大值 ≤ MAX_PER_PLACE_PER_SLOT=2；
        **place 为 null 的条目不参与场所配额**（`public_count_at` 里 `if not place: return 0`，
        代码侧同样不做场所截断）⇒ 全部为 null 时该项判 `not_applicable`。
      * 同 (author, day, slot) 的**接话**（`reply_to` 非 null）条数最大值
        ≤ MAX_PER_AGENT_PER_SLOT=1。
    """
    per_place_slot: dict[tuple, int] = {}
    per_agent_slot: dict[tuple, int] = {}
    n_pub = 0
    n_reply = 0
    missing_place = 0
    with log.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            ev = json.loads(raw)
            if ev.get("type") != "MSG_PUBLIC":
                continue
            n_pub += 1
            pl = ev.get("payload") or {}
            place = pl.get("place")
            if place is None:
                missing_place += 1
            else:
                key = (pl.get("day"), pl.get("slot"), str(place))
                per_place_slot[key] = per_place_slot.get(key, 0) + 1
            if pl.get("reply_to") is not None:
                n_reply += 1
                ka = (pl.get("author") or pl.get("from"), pl.get("day"), pl.get("slot"))
                per_agent_slot[ka] = per_agent_slot.get(ka, 0) + 1
    per_place_round: dict[tuple, int] = {}
    with log.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            ev = json.loads(raw)
            if ev.get("type") != "MSG_PUBLIC":
                continue
            pl = ev.get("payload") or {}
            if pl.get("place") is None:
                continue
            k = (ev.get("round"), pl.get("day"), pl.get("slot"), str(pl.get("place")))
            per_place_round[k] = per_place_round.get(k, 0) + 1
    max_place = max(per_place_slot.values()) if per_place_slot else 0
    max_place_round = max(per_place_round.values()) if per_place_round else 0
    max_agent = max(per_agent_slot.values()) if per_agent_slot else 0
    worst_place = None
    if per_place_slot:
        worst_place = sorted(
            ({"day": k[0], "slot": k[1], "place": k[2], "count": v}
             for k, v in per_place_slot.items()), key=lambda d: -d["count"])[0]
    if per_place_slot:
        place_status = "assessable"
        place_ok = max_place <= 2
    else:
        place_status = "not_applicable"
        place_ok = True
    return {
        "stat_unit": "MSG_PUBLIC 条（按 day × slot × place 分组；不按 round 分组）",
        "pub_instances": n_pub,
        "pub_replies": n_reply,
        "records_missing_place": missing_place,
        "place_grouped_records": sum(per_place_slot.values()),
        "max_pub_per_place_slot": max_place,
        "max_pub_per_place_round": max_place_round,
        "worst_place_slot": worst_place,
        "worst_place_round": (sorted(
            ({"round": k[0], "day": k[1], "slot": k[2], "place": k[3], "count": v}
             for k, v in per_place_round.items()), key=lambda d: -d["count"])[0]
            if per_place_round else None),
        "max_replies_per_agent_slot": max_agent,
        "limit_per_place_per_slot": 2,
        "limit_per_agent_per_slot": 1,
        "place_quota_status": place_status,
        "place_quota_ok": place_ok,
        "agent_quota_ok": max_agent <= 1,
        "note": ("配额口径按 code/life/public_talk.py 的 public_count_at / agent_quota_ok 语义复刻："
                 "place 为 null 的条目不参与场所配额（代码侧 `if not place: return 0`），"
                 "故 OFF 臂（place 全 null）判 not_applicable；ON 臂应 assessable。"),
    }


def arm_block(tag: str, log: Path, meta: Path | None, readings: dict, out_readings: Path) -> dict:
    forms = (readings.get("reply_to_forms") or {}).get("forms", {})
    n = int((readings.get("msg_public_total") or {}).get("value") or 0)
    k = int(forms.get("real_message_id", 0))
    # 分母纪律：n < 30 ⇒ **不报比率、不报区间**，只报计数（预登记 §3.2）
    suppress = n < RATIO_MIN_DEN
    w = None if suppress else wilson(k, n)
    place = readings.get("place_adjacency") or {}
    participants = readings.get("participants_length_dist") or {}
    return {
        "arm": tag,
        "log_path": str(log),
        "log_sha256": sha256_file(log),
        "log_sha256_8": sha256_file(log)[:8],
        "readings_path": str(out_readings),
        "readings_sha256": sha256_file(out_readings),
        "msg_public_instances": n,
        "reply_real_message_id": k,
        "p_reply": (None if suppress else ((k / n) if n > 0 else None)),
        "p_reply_wilson95": {"lo": w[0], "hi": w[1]} if w else None,
        "ratio_suppressed_because_den_lt_30": suppress,
        "ratio_suppressed_reason": (f"分母 n={n} < {RATIO_MIN_DEN}：按预登记 §3.2 只报计数，不报比率/区间"
                                    if suppress else None),
        "probe": n < PROBE_DEN,
        "reply_to_forms": forms,
        "msg_graph_degree": {
            "pub_in_degree_total": (readings.get("msg_graph_degree") or {}).get("pub_in_degree_total"),
            "pub_out_degree_reply_nonnull": (readings.get("msg_graph_degree") or {}).get("pub_out_degree_reply_nonnull"),
            "pub_out_degree_zero": (readings.get("msg_graph_degree") or {}).get("pub_out_degree_zero"),
            "isolated_nodes": (readings.get("msg_graph_degree") or {}).get("isolated_nodes"),
        },
        "place_adjacency": {
            "status": place.get("status"),
            "nonnull_place_records": place.get("nonnull_place_records"),
            "denominator": place.get("denominator"),
            "denominator_pairs": place.get("denominator_pairs"),
            "numerator_same_place_pairs": place.get("numerator_same_place_pairs"),
            "ratio_same_place": place.get("ratio_same_place"),
            "coverage": ((place.get("nonnull_place_records") or 0) / place["denominator"]
                         if place.get("denominator") else None),
        },
        "participants_length_histogram": participants.get("length_histogram"),
        "turn_index_histogram": (readings.get("diagnostics") or {}).get("turn_index_histogram"),
        "thread_ids_distinct": (readings.get("diagnostics") or {}).get("distinct_thread_ids"),
        "code_sha": (readings.get("inputs") or {}).get("code_sha"),
        "meta_run_sha256_matches_log": (readings.get("inputs") or {}).get("meta_run_sha256_matches_log"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="R41V 公开面接话 OFF/ON 对比读数（只读、零 LLM）")
    ap.add_argument("--off", required=True)
    ap.add_argument("--on", required=True)
    ap.add_argument("--off-meta", default=None)
    ap.add_argument("--on-meta", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-dir", default=None, help="各臂单份读数 json 落盘目录（默认与 --out 同目录）")
    args = ap.parse_args()

    off_log, on_log = Path(args.off), Path(args.on)
    for p in (off_log, on_log):
        if not p.is_file():
            print(f"[compare] 输入缺失: {p}", file=sys.stderr)
            return 2
    out_path = Path(args.out)
    out_dir = Path(args.out_dir) if args.out_dir else out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    off_read = out_dir / "readings_off.json"
    on_read = out_dir / "readings_on.json"
    r_off = run_ruler(off_log, Path(args.off_meta) if args.off_meta else None, off_read)
    r_on = run_ruler(on_log, Path(args.on_meta) if args.on_meta else None, on_read)

    a_off = arm_block("off", off_log, None, r_off, off_read)
    a_on = arm_block("on", on_log, None, r_on, on_read)

    # ---- R41V-C1：比例差（p_on - p_off）Newcombe 95% ----
    wr = load_module(WEATHER_READINGS, "r41v_weather_readings")
    n_off, k_off = a_off["msg_public_instances"], a_off["reply_real_message_id"]
    n_on, k_on = a_on["msg_public_instances"], a_on["reply_real_message_id"]
    den_ok = (n_off >= RATIO_MIN_DEN) and (n_on >= RATIO_MIN_DEN)
    ci = wr.newcombe95(k_on, n_on, k_off, n_off) if (den_ok and n_off > 0 and n_on > 0) else None
    c1_judgeable = bool(den_ok and k_off == 0)
    c1_hold = bool(ci and ci[0] > 0 and k_on >= 1 and k_off == 0)

    # ---- R41V-C2：OFF 等价性（结构侧） ----
    c2_hold = (k_off == 0 and a_off["msg_graph_degree"]["pub_out_degree_zero"] is True)

    # ---- R41V-C3：place 可判性解锁 ----
    cov_on = a_on["place_adjacency"]["coverage"]
    cov_off = a_off["place_adjacency"]["coverage"]
    # ruler 的可判性信号是 status：UNVERIFIED（place 恒 null）/ MEASURED（place 覆盖满足）
    c3_hold = bool(a_on["place_adjacency"]["status"] == "MEASURED"
                   and a_off["place_adjacency"]["status"] == "UNVERIFIED")

    # ---- R41V-C4：配额护栏 ----
    q_off = quota_guard(off_log)
    q_on = quota_guard(on_log)
    c4_hold = bool(q_off["place_quota_ok"] and q_off["agent_quota_ok"]
                   and q_on["place_quota_ok"] and q_on["agent_quota_ok"]
                   and q_on.get("max_pub_per_place_round", 0) <= q_on["limit_per_place_per_slot"])

    # ---- 描述性旁证（非判据）：结构缺口规模 + reply_to 语义 ---
    g_off = struct_gap(off_log)
    g_on = struct_gap(on_log)
    r2s_off = reply_to_semantics(off_log)
    r2s_on = reply_to_semantics(on_log)

    # ---- R41V-C5：非塌陷 ----
    c5_hold = n_on >= n_off

    verdicts = {
        "R41V-C1_main_rate_diff": {
            "hold": c1_hold, "judgeable": c1_judgeable,
            "spec": "p_on - p_off 的 Newcombe 95% 区间下界 > 0，且 k_on>=1，k_off=0",
            "observed": {"k_on": k_on, "n_on": n_on, "k_off": k_off, "n_off": n_off,
                         # 分母不足时连比率都不报（口径纪律），只报计数
                         "p_on": (a_on["p_reply"] if den_ok else None),
                         "p_off": (a_off["p_reply"] if den_ok else None),
                         "diff_p_on_minus_p_off": ((a_on["p_reply"] - a_off["p_reply"])
                                                   if (den_ok and a_on["p_reply"] is not None
                                                       and a_off["p_reply"] is not None) else None),
                         "newcombe95": ci,
                         "counts_only_reason": (None if den_ok else
                                                "两臂分母未同时 >= 30 ⇒ 按预登记 §3.2 只报计数 k/n，不报比率与区间")},
            "status": ("达标" if c1_hold else ("不成立" if c1_judgeable else "不可判（分母不足）")),
            "denominator_discipline": {
                "ratio_min_denominator": RATIO_MIN_DEN,
                "denominators": {"n_off": n_off, "n_on": n_on},
                "denominators_sufficient": den_ok,
                "what_is_reported": ("只报计数（k_on / n_on / k_off / n_off）与上界口径；"
                                     "**不报比率、不报区间**"
                                     if not den_ok else
                                     "计数 + 比率 + Newcombe 95% 区间（分母达标）"),
                "forbidden": "不得为凑分母放宽 MSG_PUBLIC 定义、不得把 DM/GROUP 并入分母、不得合并两臂分母",
            },
            "probe_note": (f"M实例 n_on={n_on}/n_off={n_off}；分母 <{PROBE_DEN} ⇒ probe=true，"
                           "结论只能写「方向性」，不得写「显著」"),
        },
        "R41V-C2_off_equivalence": {
            "hold": c2_hold, "spec": "OFF 臂 k=0 且 pub_out_degree_zero=true",
            "observed": {"k_off": k_off, "pub_out_degree_zero": a_off["msg_graph_degree"]["pub_out_degree_zero"]},
            "status": "达标" if c2_hold else "不成立",
        },
        "R41V-C3_place_judgeability": {
            "hold": c3_hold, "spec": "ON 臂 place 非 null 覆盖 100% 且 OFF 仍 UNVERIFIED",
            "observed": {"coverage_on": cov_on, "coverage_off": cov_off,
                         "status_on": a_on["place_adjacency"]["status"],
                         "status_off": a_off["place_adjacency"]["status"]},
            "status": "达标" if c3_hold else "不成立",
        },
        "R41V-C4_quota_guard": {
            "hold": c4_hold, "spec": "两臂 MAX_PER_PLACE_PER_SLOT<=2 且 MAX_PER_AGENT_PER_SLOT<=1",
            "observed": {"off": q_off, "on": q_on},
            "status": "达标" if c4_hold else "不成立",
        },
        "R41V-C5_no_collapse": {
            "hold": c5_hold, "spec": "ON 臂 MSG_PUBLIC 条数 >= OFF 臂",
            "observed": {"n_on": n_on, "n_off": n_off},
            "status": "达标" if c5_hold else "不成立",
        },
    }

    result = {
        "schema": "r41v-public-talk-compare/1.0",
        "prereg": "v2/refs/prereg-r41v-public-talk-verify.md",
        "generator": {
            "script": "tools/public_talk/compare_arms.py",
            "script_sha256": sha256_file(Path(__file__).resolve()),
            "ruler": "tools/public_talk/public_talk_metrics.py",
            "ruler_sha256": sha256_file(RULER),
            "wilson_tool": "tools/metrics/d9m_wilson_ci.py",
            "wilson_tool_sha256": sha256_file(WILSON_TOOL),
            "newcombe_impl": "tools/metrics/weather_readings.py::newcombe95",
            "newcombe_impl_sha256": sha256_file(WEATHER_READINGS),
        },
        "arms": {"off": a_off, "on": a_on},
        "descriptive": {
            "struct_gap_off": g_off,
            "struct_gap_on": g_on,
            "reply_to_semantics_off": r2s_off,
            "reply_to_semantics_on": r2s_on,
            "caveat": ("descriptive 段不是判据（not_a_judgment=true）：只描述「结构缺口本来有多大 / "
                       "ON 臂打开了多少」，不参与 C1..C5 的任何达标判定；两个口径（by_message / by_pair）"
                       "分母不同，引用时必须写明用哪个。"),
        },
        "verdicts": verdicts,
        "all_hold": all(v["hold"] for v in verdicts.values()),
        "discipline": {
            "ratio_min_denominator": RATIO_MIN_DEN,
            "probe_threshold_denominator": PROBE_DEN,
            "not_a_quality_claim": "本对比只证「公开面接话通道在 ON 臂被触发」，不证「生活气息提升/接话质量更好」，不写「显著」",
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    out_path.write_text(text, encoding="utf-8")
    print(f"[compare] wrote {out_path}")
    print(f"[compare] sha256 {hashlib.sha256(text.encode('utf-8')).hexdigest()}")
    for name, v in verdicts.items():
        print(f"[compare] {name}: {v['status']}")
    print(f"[compare] all_hold={result['all_hold']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
