#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D4 · A0 起飞前自检（30 秒内给 PASS/FAIL，决定能不能起 A1）

作者：prompt-linguist ｜ 只读：不跑 LLM、不改文件、不写世界态。
用法：
  python3 v2/evidence/d4_preflight_a0.py --run-dir /path/to/A0_dir
  或  python3 v2/evidence/d4_preflight_a0.py --run /path/to/run.jsonl [--meta /path/to/meta.json]

检查项（任一 FAIL ⇒ 先报 leader，不许起 A1）：
  C1 run.jsonl 存在且非空
  C2 meta.json 存在、provider 非空且不含 "mock"、seed/model/sha 字段在
  C3 MSG 条数 ≥150（DM+PUBLIC），且 DM ≥100
  C4 线程字段存在：MSG_* payload 里有 thread_id（D2 结构生效）
  C5 K-1 分母（线程内非首条消息数）≥30（否则 B2 太宽、承接类无法判定 → 报 INCONCLUSIVE 供 leader 决定）
  C6 线程切分异常检测：单条线程占比 >95% 或 平均 msgs/thread <1.05 ⇒ WARN（结构可能没生效）
  C7 分母异常：任一 L 类分母为 0 ⇒ FAIL
退出码：0 全 PASS（可能有 WARN）；1 有 FAIL。
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
CH = {"MSG_DM": "dm", "MSG_PUBLIC": "public", "MSG_GROUP": "group"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=None)
    ap.add_argument("--run-dir", default=None)
    ap.add_argument("--meta", default=None)
    a = ap.parse_args()
    run = a.run or (str(Path(a.run_dir) / "run.jsonl") if a.run_dir else None)
    meta = a.meta or (str(Path(a.run_dir) / "meta.json") if a.run_dir else None)
    if not run:
        print("需要 --run 或 --run-dir")
        return 1

    checks = []

    def add(name, ok, detail, level="FAIL"):
        checks.append({"check": name, "ok": bool(ok), "detail": detail,
                       "level": "PASS" if ok else level})

    # C1
    p = Path(run)
    add("C1_run_exists", p.exists() and p.stat().st_size > 0,
        f"{run} size={p.stat().st_size if p.exists() else 'missing'}")

    # C2 = 三段式（leader 17:11 裁决：meta.provider 只是作者声明，不是证据）
    md = {}
    if meta and Path(meta).exists():
        try:
            md = json.loads(Path(meta).read_text(encoding="utf-8"))
        except Exception:
            md = {}
    prov_declared = str(md.get("provider") or "")

    # C2a（硬）：obs 官方 provider guard，rc 必须 0
    cmd = [sys.executable, "-m", "obs", "llm-cost", "--log", str(Path(run).resolve()),
           "--require-provider", "openai_compat"]
    obs_cwd = str(Path(__file__).resolve().parents[2] / "code")
    try:
        r = subprocess.run(cmd, cwd=obs_cwd, capture_output=True, text=True, timeout=1800)
        guard_rc = r.returncode
        try:
            guard = json.loads(r.stdout).get("provider_guard", {})
        except Exception:
            guard = {}
        add("C2a_obs_provider_guard", guard_rc == 0,
            f"cmd=python3 -m obs llm-cost --require-provider openai_compat (cwd=code) rc={guard_rc} "
            f"by_provider={guard.get('by_provider')} problems={guard.get('problems')}")
    except Exception as e:  # noqa: BLE001
        add("C2a_obs_provider_guard", False, f"命令执行失败: {e}")

    # C2b（硬）：直接扫 LLM_CALL.payload 的 provider/model 取值集合
    provs, models = Counter(), Counter()
    if p.exists():
        for line in open(run, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("type") != "LLM_CALL":
                continue
            pl = e.get("payload") or {}
            provs[str(pl.get("provider"))] += 1
            models[str(pl.get("model"))] += 1
    ok_c2b = (set(provs) == {"openai_compat"}) and provs.get("openai_compat", 0) > 0 \
        and not any("mock" in m.lower() for m in models)
    add("C2b_llmcall_facts", ok_c2b,
        f"LLM_CALL.provider={dict(provs)} LLM_CALL.model={dict(models)}")

    # C2c（软，仅记录）：声明 vs 事实
    consistent = (prov_declared == "openai_compat") and ok_c2b
    add("C2c_declaration_matches_fact", consistent,
        f"meta.provider={prov_declared!r} vs facts={dict(provs)} (不一致=有价值发现，仅记录不阻断)",
        level="WARN")

    # 扫日志
    msgs, types = [], Counter()
    if p.exists():
        for line in open(run, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            types[e.get("type")] += 1
            if e.get("type") in MSG_TYPES:
                pl = e.get("payload") or {}
                msgs.append({
                    "type": e["type"], "channel": CH[e["type"]],
                    "round": e.get("round"), "seq": e.get("seq"),
                    "speaker": pl.get("from") or pl.get("author"),
                    "to": pl.get("to"), "group_id": pl.get("group_id"),
                    "thread_id": pl.get("thread_id"), "turn_index": pl.get("turn_index"),
                    "reply_to": pl.get("reply_to"), "topic": pl.get("topic"),
                    "msg_uid": pl.get("msg_uid"), "participants": pl.get("participants"),
                    "body": pl.get("body") or "",
                })
    n = len(msgs)
    ch = Counter(m["channel"] for m in msgs)

    # C3
    dp = ch.get("dm", 0) + ch.get("public", 0)
    add("C3_sample_size", dp >= 150 and ch.get("dm", 0) >= 100,
        f"n_total={n} dm={ch.get('dm',0)} public={ch.get('public',0)} group={ch.get('group',0)} (需 dm+public>=150 且 dm>=100)")

    # C4
    has_tid = sum(1 for m in msgs if m["thread_id"])
    add("C4_thread_field", has_tid > 0,
        f"MSG_* payload 含 thread_id: {has_tid}/{n}")

    # 线程
    def key(m):
        if m["thread_id"]:
            return "T|" + str(m["thread_id"])
        if m["channel"] == "dm":
            return f"L|{m['round']}|dm|{'-'.join(sorted([str(m['speaker']), str(m['to'])]))}"
        if m["channel"] == "group":
            return f"L|{m['round']}|group|{m['group_id']}"
        return f"L|{m['round']}|public"

    th = defaultdict(list)
    for m in msgs:
        th[key(m)].append(m)
    for k in th:
        th[k].sort(key=lambda m: (m["round"] or 0, m["seq"] or 0))
    sizes = [len(v) for v in th.values()]
    non_first = sum(s - 1 for s in sizes)

    # C5
    add("C5_k1_denominator", non_first >= 30,
        f"线程内非首条消息={non_first}（K-1 分母；<30 则承接类只能 INCONCLUSIVE）",
        level="WARN")

    # C6
    single = (sum(1 for s in sizes if s == 1) / len(sizes) * 100) if sizes else 0
    avg = (n / len(sizes)) if sizes else 0
    add("C6_thread_split_sane", not (single > 95 or avg < 1.05),
        f"threads={len(sizes)} single_msg_ratio={single:.1f}% avg_msgs/thread={avg:.2f}",
        level="WARN")

    # C7
    denoms = {"per_message": n, "dm_group": ch.get("dm", 0) + ch.get("group", 0),
              "per_thread": len(sizes), "k1": non_first}
    bad = [k for k, v in denoms.items() if v == 0]
    add("C7_denominators", not bad, f"denoms={denoms} zero={bad}")

    # C8（硬，leader 19:23 要求）：meta 断言与行数自洽
    #   meta.assertions.msg_uid_unique 必须为 true；meta.events 必须 == wc -l（run.jsonl 行数）
    n_lines = 0
    if p.exists():
        with open(run, "rb") as f:
            for _ in f:
                n_lines += 1
    asserts = (md.get("assertions") or {}) if isinstance(md, dict) else {}
    uid_unique = asserts.get("msg_uid_unique")
    events_meta = md.get("events")
    # C8a 实质条件：**从日志独立核** msg_uid 唯一（不依赖作者声明）
    uids = [m["msg_uid"] for m in msgs if m.get("msg_uid")]
    n_msgs_all = len(msgs)
    uniq_ok = (len(uids) == n_msgs_all) and (len(set(uids)) == len(uids)) and n_msgs_all > 0
    add("C8a_msg_uid_unique_log", uniq_ok,
        f"日志派生：msg_uid 非空 {len(uids)}/{n_msgs_all}，去重后 {len(set(uids))}（要求非空且唯一）")
    add("C8a2_meta_declared", uid_unique is True,
        f"meta.assertions.msg_uid_unique={uid_unique!r}（缺失=作者漏填，记 WARN，不作 FAIL）",
        level="WARN")
    ok_c8b = (events_meta is not None and int(events_meta) == n_lines)
    add("C8b_events_match_lines", ok_c8b,
        f"meta.events={events_meta!r} vs wc -l={n_lines}")

    # ---- T0 指标块（30 秒判读用；无 meta 也能跑，仅 provider 硬项需要真跑） ----
    core_names, pid2name = set(), {}
    try:
        for pr in json.loads((Path(__file__).resolve().parents[2] / "code" / "config" / "personas.json")
                             .read_text(encoding="utf-8"))["personas"]:
            nm = str(pr.get("display_name") or "").split("·")[-1].strip()
            if nm:
                core_names.add(nm)
                pid2name[str(pr.get("persona_id"))] = nm
    except Exception:
        pass
    l8 = sum(1 for m in msgs if re.search(r"P\d{3}", m["body"]))
    l12 = 0
    dmg = [m for m in msgs if m["channel"] in ("dm", "group")]
    for m in dmg:
        own = pid2name.get(str(m["speaker"]))
        if any(nm in m["body"] for nm in core_names if nm != own):
            l12 += 1
    nonfirst = [m for m in msgs if m.get("turn_index") not in (None, 0)]
    replied = sum(1 for m in nonfirst if m.get("reply_to"))
    topic_ok = sum(1 for m in msgs if m.get("topic"))
    t0 = {
        "n_msgs": n,
        "S1_multi_turn_threads": sum(1 for v in th.values() if len(v) >= 3),
        "S2_reply_pointer_coverage_pct": round(100 * replied / len(nonfirst), 2) if nonfirst else None,
        "S2_denom_nonfirst": len(nonfirst),
        "S3_single_msg_thread_pct": round(single, 2),
        "S4_msgs_per_thread_p50": statistics.median(sizes) if sizes else None,
        "S5_longest_thread": max(sizes) if sizes else None,
        "S6_L12_peer_name_pct": round(100 * l12 / len(dmg), 2) if dmg else None,
        "S6_denom_dm_group": len(dmg),
        "S7_L8_agent_id_pct": round(100 * l8 / n, 2) if n else None,
        "S9_ctx_topic_nonnull_pct": round(100 * topic_ok / n, 2) if n else None,
        "S10_K1_denominator": non_first,
        "S11_dropped_dup": types.get("DROPPED", 0),
    }
    # T0 卡死判据（任一触发 ⇒ STOP）
    stop = []
    if t0["S6_L12_peer_name_pct"] == 0:
        stop.append("S6 L-12=0（名字没进 prompt）")
    if t0["S2_reply_pointer_coverage_pct"] is not None and t0["S2_reply_pointer_coverage_pct"] < 95:
        stop.append(f"S2 指针完整率 {t0['S2_reply_pointer_coverage_pct']}% <95%")
    if t0["S1_multi_turn_threads"] == 0:
        stop.append("S1 无多轮线程")
    if n < 100:
        stop.append(f"S11 消息数 {n}<100（疑似被拦截或未跑完）")

    # 输出
    fails = [c for c in checks if not c["ok"] and c["level"] == "FAIL"]
    warns = [c for c in checks if not c["ok"] and c["level"] == "WARN"]
    print(json.dumps({"run": run, "meta": meta, "checks": checks,
                      "verdict": "FAIL" if fails else ("PASS_WITH_WARN" if warns else "PASS"),
                      "n_msgs": n, "channels": dict(ch), "event_types_top": types.most_common(6),
                      "T0_metrics": t0, "T0_stop_reasons": stop},
                     ensure_ascii=False, indent=2))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
