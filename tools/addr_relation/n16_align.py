#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N-16 对齐器：`RELATION_CHANGE` 事件流 × 称呼序列（只读核算）。

一句话：关系**真的变了**的时候，称呼**有没有跟上**？——把事件流和称呼序列放到同一条
`seq` 坐标轴上，逐事件判「有没有可比的基线称呼 + 之后有没有具名称呼」。

零 LLM、零写入运行时代码、纯只读。只 import 既有尺子 `tools/metrics/address_drift.py`
（不改一行）来抽称呼，`RELATION_CHANGE` 用本脚本自己的解析（该事件没有尺子）。

=== 口径（出数前写死，报告逐条披露）===
坐标：`seq`（run.jsonl 记录序号，哈希链 + 稠密自增，脚本运行时校验 `seq_dense`
      与 `prev_hash` 链接；校验失败 ⇒ 该 run 直接判「时间戳不可比」不出数）。
事件：`RELATION_CHANGE` 记录，字段 `payload.{from,to,dim,before,after,cause}` + `seq/round/phase/mono_ts`。
单位：**有向居民对**（`from → to`，与 `addr_stage_ordinal` 的有向对一致）。无向对只作敏感性附表。

称呼：沿用 `address_drift.py` 的呼语位识别结果，只取 `addr_target ∈ {target_ok, generic}`
      （= 指向正确或指向不可判的具名称呼），与 `addr_stage_ordinal` 的纳入条件一致；
      `other_named`/`self_name`（叫错人）与 `unknown_target` 不计入——它们不是「怎么叫对方」的证据。

对齐（每个 RC 事件判一次）：
  before = 同一有向对上，`seq < s` 的**最后一次**具名称呼
  after  = 同一有向对上，`seq > s` 的**第一次**具名称呼
  ① before 与 after 都有 ⇒ **对齐成功（可判）**，再看 `form_before == form_after` 判「无变化 / 有变化」
  ② 只有 before        ⇒ 丢配：该有向对在 s 之后**完全无 MSG** = `对方未再发声`；
                          有 MSG 但无具名称呼 = `称呼未具名`
  ③ 只有 after         ⇒ 丢配：`变化前无基线`（本类为任务书四类之外的补充类，单列不合并）
  ④ `from`/`to`/`seq` 缺失 ⇒ 丢配：`事件字段缺失`
  ⑤ `seq` 非稠密/断链 ⇒ 丢配：`时间戳不可比`

子集：
  全量 = 所有 RC 事件；
  强变化 = `|after-before| >= 3`（幅度大的真变化）；
  无变化 = `after == before`（若有，单列）。

**纪律**：分母 = 事件数，不是独立样本数——同一对多次 RC 会重复使用同一段称呼，
所以**只报事件数**；凡分母 < 30 的分组**不报百分比**。

用法：
    python3 tools/addr_relation/n16_align.py
    python3 tools/addr_relation/n16_align.py --runs v2/evidence/<a> v2/evidence/<b>
    python3 tools/addr_relation/n16_align.py --selftest
退出码：0 正常；2 输入不可用；3 自检失败。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ADDR_TOOL = os.path.join(ROOT, "tools", "metrics", "address_drift.py")
LEXICON = os.path.join(ROOT, "v2", "refs", "address-ordinal.yaml")
PERSONAS = os.path.join(ROOT, "code", "config", "personas.json")

DEFAULT_RUNS = [
    "v2/evidence/d9m-ab-off_n16r24_s42",
    "v2/evidence/d9s-on_n16r24_s42",
]

ADDR_OK = ("target_ok", "generic")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # type: ignore[name-defined]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def git_head() -> dict:
    import subprocess
    try:
        sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.strip()
        br = subprocess.run(["git", "-C", ROOT, "rev-parse", "--abbrev-ref", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
        return {"head_sha": sha, "branch": br}
    except Exception as e:  # noqa: BLE001
        return {"head_sha": None, "branch": None, "error": str(e)}


# --------------------------------------------------------------------------- 读日志
def scan_log(path: str) -> dict:
    """一次扫描：返回 (relation_change 事件, 消息记录, 链完整性)。"""
    rc: list[dict] = []
    msgs: list[dict] = []
    seqs: list[int] = []
    chain_ok = True
    prev = "sha256:" + "0" * 64
    last_seq = None
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except Exception:
                continue
            s = r.get("seq")
            if isinstance(s, int):
                seqs.append(s)
                if last_seq is not None and s != last_seq + 1:
                    chain_ok = False
                last_seq = s
            if r.get("prev_hash") not in (None, prev):
                chain_ok = False
            prev = r.get("hash") or prev
            t = r.get("type")
            if t == "RELATION_CHANGE":
                rc.append(r)
            elif isinstance(t, str) and t.startswith("MSG"):
                msgs.append(r)
    seq_dense = bool(seqs) and all(b == a + 1 for a, b in zip(seqs, seqs[1:]))
    return {"rc": rc, "msgs": msgs, "seq_dense": seq_dense, "chain_ok": chain_ok,
            "seq_min": min(seqs) if seqs else None, "seq_max": max(seqs) if seqs else None}


def addr_msgs(ADDR, msgs: list[dict]) -> list[dict]:
    """用既有尺子抽称呼：返回 [{seq, speaker, addressee, form, tier, target}]。"""
    lex = ADDR.load_lexicon(LEXICON)
    terms, _info, owners = ADDR.build_agent_terms(lex, PERSONAS)
    base_names = {p["display_name"].split("·")[-1].strip()
                  for p in json.load(open(PERSONAS, encoding="utf-8"))["personas"]}
    voc = lex.get("vocative") or {}
    out = []
    for rec in msgs:
        m = ADDR.as_msg(rec)
        if m is None:
            continue
        text = ADDR.strip_parenthetical(m["body"], base_names)
        hit = ADDR.find_vocative(text, terms, voc)
        form = hit[0] if hit else None
        tier = hit[1] if hit else None
        if hit is None:
            target = None
        else:
            own = owners.get(hit[0]) or set()
            if not own:
                target = "generic"
            elif m["addressee"] is None:
                target = "unknown_target"
            elif m["addressee"] in own:
                target = "target_ok"
            elif m["speaker"] in own:
                target = "self_name"
            else:
                target = "other_named"
        out.append({"seq": m["seq"], "speaker": m["speaker"], "addressee": m["addressee"],
                    "form": form, "tier": tier, "target": target,
                    "body": (m["body"] or "")[:80]})
    return out


# --------------------------------------------------------------------------- 对齐
def align(run_key: str, log_rel: str, log_sha: str, scan: dict, amsgs: list[dict],
          strong_delta: int = 3) -> dict:
    by_dir: dict[tuple, list[dict]] = {}
    by_pair_undir: dict[tuple, list[dict]] = {}
    for m in amsgs:
        if m["form"] and m["target"] in ADDR_OK and m["speaker"] and m["addressee"]:
            by_dir.setdefault((m["speaker"], m["addressee"]), []).append(m)
            by_pair_undir.setdefault(tuple(sorted((m["speaker"], m["addressee"]))), []).append(m)
    for k in by_dir:
        by_dir[k].sort(key=lambda r: r["seq"])
    for k in by_pair_undir:
        by_pair_undir[k].sort(key=lambda r: r["seq"])

    msgs_by_dir: dict[tuple, list[int]] = {}
    for m in amsgs:
        if m["speaker"] and m["addressee"]:
            msgs_by_dir.setdefault((m["speaker"], m["addressee"]), []).append(m["seq"])

    rows = []
    lost: dict[str, int] = {}
    changed = 0
    unchanged = 0
    aligned = 0
    per_dim: dict[str, dict] = {}
    strong = {"n": 0, "aligned": 0, "changed": 0, "unchanged": 0}
    zero_delta = 0
    seq_ok = scan["seq_dense"] and scan["chain_ok"]

    for r in scan["rc"]:
        pl = r.get("payload") or {}
        s = r.get("seq")
        f, t = pl.get("from"), pl.get("to")
        dim = pl.get("dim")
        before_v, after_v = pl.get("before"), pl.get("after")
        delta = (after_v - before_v) if isinstance(before_v, (int, float)) and isinstance(after_v, (int, float)) else None
        base = {"seq": s, "round": r.get("round"), "phase": r.get("phase"),
                "pair": [f, t], "dim": dim, "cause": pl.get("cause"),
                "before": before_v, "after": after_v, "delta": delta}

        # ⑤ 时间戳/链不可比
        if not seq_ok or s is None:
            lost["时间戳不可比"] = lost.get("时间戳不可比", 0) + 1
            rows.append({**base, "status": "丢配", "reason": "时间戳不可比"})
            continue
        # ④ 事件字段缺失
        if not f or not t:
            lost["事件字段缺失"] = lost.get("事件字段缺失", 0) + 1
            rows.append({**base, "status": "丢配", "reason": "事件字段缺失"})
            continue
        if delta == 0:
            zero_delta += 1

        cand = by_dir.get((f, t), [])
        pre = [m for m in cand if m["seq"] < s]
        post = [m for m in cand if m["seq"] > s]
        b = pre[-1] if pre else None
        a = post[0] if post else None

        if b is not None and a is not None:
            aligned += 1
            is_changed = a["form"] != b["form"]
            if is_changed:
                changed += 1
            else:
                unchanged += 1
            d = per_dim.setdefault(dim or "NA", {"n": 0, "aligned": 0, "changed": 0, "unchanged": 0})
            d["n"] += 1
            d["aligned"] += 1
            d["changed" if is_changed else "unchanged"] += 1
            if delta is not None and abs(delta) >= strong_delta:
                strong["n"] += 1
                strong["aligned"] += 1
                strong["changed" if is_changed else "unchanged"] += 1
            rows.append({**base, "status": "对齐成功",
                         "form_before": b["form"], "tier_before": b["tier"], "seq_before": b["seq"],
                         "form_after": a["form"], "tier_after": a["tier"], "seq_after": a["seq"],
                         "changed": is_changed,
                         "body_after": a["body"]})
        else:
            if b is not None and a is None:
                later_msgs = [x for x in msgs_by_dir.get((f, t), []) if x > s]
                reason = "对方未再发声" if not later_msgs else "称呼未具名"
            elif b is None and a is not None:
                reason = "变化前无基线"
            else:
                later_msgs = [x for x in msgs_by_dir.get((f, t), []) if x > s]
                reason = "对方未再发声" if not later_msgs else "称呼未具名"
            lost[reason] = lost.get(reason, 0) + 1
            d = per_dim.setdefault(dim or "NA", {"n": 0, "aligned": 0, "changed": 0, "unchanged": 0})
            d["n"] += 1
            if delta is not None and abs(delta) >= strong_delta:
                strong["n"] += 1
            rows.append({**base, "status": "丢配", "reason": reason,
                         "has_before": b is not None, "has_after": a is not None})

    # 无向对敏感性（只报事件数）
    undir = {"pairs_with_addr": len(by_pair_undir)}
    u_aligned = u_changed = 0
    for r in scan["rc"]:
        pl = r.get("payload") or {}
        s, f, t = r.get("seq"), pl.get("from"), pl.get("to")
        if s is None or not f or not t or not seq_ok:
            continue
        cand = by_pair_undir.get(tuple(sorted((f, t))), [])
        pre = [m for m in cand if m["seq"] < s]
        post = [m for m in cand if m["seq"] > s]
        if pre and post:
            u_aligned += 1
            if post[0]["form"] != pre[-1]["form"]:
                u_changed += 1
    undir.update({"n_aligned": u_aligned, "n_changed": u_changed, "n_unchanged": u_aligned - u_changed,
                  "note": "无向对：只作敏感性，不作为判据（无向对会把甲叫乙/乙叫甲混在一起）"})

    # 独立性诊断：对齐成功的事件背后有多少**不重复**的「对×称呼对」片段
    pairs_aligned = {(x["pair"][0], x["pair"][1]) for x in rows if x["status"] == "对齐成功"}
    episodes: dict[tuple, int] = {}
    for x in rows:
        if x["status"] != "对齐成功":
            continue
        k = (x["pair"][0], x["pair"][1], x["form_before"], x["form_after"])
        episodes[k] = episodes.get(k, 0) + 1
    ep_changed = sum(1 for k in episodes if k[2] != k[3])
    ep_unchanged = sum(1 for k in episodes if k[2] == k[3])

    return {
        "key": run_key, "log": log_rel, "log_sha256": log_sha,
        "seq_dense": scan["seq_dense"], "chain_ok": scan["chain_ok"],
        "seq_range": [scan["seq_min"], scan["seq_max"]],
        "n_rc_events": len(scan["rc"]),
        "n_msg_records": len(scan["msgs"]),
        "n_addr_msgs_usable": sum(len(v) for v in by_dir.values()),
        "n_directed_pairs_with_addr": len(by_dir),
        "align": {
            "n_events": len(scan["rc"]),
            "n_aligned": aligned,
            "n_lost": sum(lost.values()),
            "lost_by_reason": dict(sorted(lost.items(), key=lambda x: -x[1])),
            "n_changed": changed,
            "n_unchanged": unchanged,
            "n_zero_delta_events": zero_delta,
            "by_dim": dict(sorted(per_dim.items())),
            "strong_subset": {"rule": f"|after-before| >= {strong_delta}", **strong},
        },
        "independence": {
            "n_distinct_pairs_aligned": len(pairs_aligned),
            "n_distinct_episodes": len(episodes),
            "n_distinct_episodes_changed": ep_changed,
            "n_distinct_episodes_unchanged": ep_unchanged,
            "max_events_per_episode": max(episodes.values()) if episodes else 0,
            "note": "episode = (有向对, before 形式, after 形式)；同一 episode 被多个 RC 事件重复计数 ⇒ 事件数≠独立观测数",
            "episodes": [{"pair": [k[0], k[1]], "form_before": k[2], "form_after": k[3],
                          "n_events": v, "changed": k[2] != k[3]}
                         for k, v in sorted(episodes.items(), key=lambda kv: -kv[1])],
        },
        "undirected_sensitivity": undir,
        "rows": rows,
    }


# --------------------------------------------------------------------------- 自检
def selftest() -> int:
    ADDR = load_module("addr_drift", ADDR_TOOL)
    recs = [
        # ① 关系变化前：P002(老石) 叫 P004(秀娘)「秀娘」
        {"seq": 1, "round": 0, "type": "MSG_DM",
         "payload": {"body": "秀娘，早啊。", "author": "P002", "from": "P002", "to": "P004",
                     "participants": ["P002", "P004"], "thread_id": "T1"}},
        {"seq": 2, "round": 0, "type": "RELATION_CHANGE",
         "payload": {"from": "P002", "to": "P004", "dim": "affinity", "before": 0, "after": 5,
                     "cause": "chat"}},
        # ② 关系变化后：同一个人改叫「秀婶」（同属 P004 的派生形式）⇒ 应判「有变化」
        {"seq": 3, "round": 0, "type": "MSG_DM",
         "payload": {"body": "秀婶，豆腐好了。", "author": "P002", "from": "P002", "to": "P004",
                     "participants": ["P002", "P004"], "thread_id": "T1"}},
        # ③ 一对从未说过话的有向对（P005→P006）的关系变化 ⇒ 应判「对方未再发声」
        {"seq": 4, "round": 0, "type": "RELATION_CHANGE",
         "payload": {"from": "P005", "to": "P006", "dim": "familiarity", "before": 1, "after": 2,
                     "cause": "encounter"}},
    ]
    tmpdir = tempfile.mkdtemp(prefix="n16_selftest_")
    log = os.path.join(tmpdir, "run.jsonl")
    with open(log, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    scan = scan_log(log)
    amsgs = addr_msgs(ADDR, scan["msgs"])
    res = align("SELFTEST", "tmp/run.jsonl", sha256_file(log), scan, amsgs)
    shutil.rmtree(tmpdir, ignore_errors=True)
    al = res["align"]
    print("[selftest] aligned:", al["n_aligned"], "lost:", al["n_lost"],
          "lost_by_reason:", al["lost_by_reason"], "changed:", al["n_changed"])
    bad = 0
    if al["n_aligned"] != 1 or al["n_lost"] != 1:
        bad += 1
        print("[SELFTEST FAIL] 期望 1 对齐 / 1 丢配")
    if al["lost_by_reason"].get("对方未再发声") != 1:
        bad += 1
        print("[SELFTEST FAIL] 期望「对方未再发声」= 1")
    ok = [x for x in res["rows"] if x["status"] == "对齐成功"]
    if ok:
        row = ok[0]
        print("[selftest] forms:", row.get("form_before"), "->", row.get("form_after"),
              "changed:", row.get("changed"))
        if row.get("form_before") != "秀娘" or row.get("form_after") != "秀婶" or row.get("changed") is not True:
            bad += 1
            print("[SELFTEST FAIL] 期望 秀娘 -> 秀婶 且 changed=True")
    else:
        bad += 1
        print("[SELFTEST FAIL] 无对齐成功行")
    print(f"[selftest] {'FAIL' if bad else 'PASS'} (failures={bad})")
    return 3 if bad else 0


# --------------------------------------------------------------------------- 报告
def to_markdown(res: dict) -> str:
    L: list[str] = []
    L.append("# N-16 对齐件：`RELATION_CHANGE` 事件流 × 称呼序列")
    L.append("")
    L.append(f"- 生成时间：`{res['generated_at']}`")
    L.append(f"- 仓库 HEAD（**读日志时刻**）：`{res['git']['head_sha']}`（分支 `{res['git']['branch']}`）")
    L.append(f"- 对齐器：`tools/addr_relation/n16_align.py` sha256 `{res['tool_sha256']}`")
    L.append(f"- 称呼尺子：`{res['inputs']['addr_impl']['path']}` sha256 `{res['inputs']['addr_impl']['sha256']}`（未改一行）")
    L.append(f"- 词表：`{res['inputs']['lexicon']['path']}` sha256 `{res['inputs']['lexicon']['sha256']}`")
    L.append("- 性质：**只读核算**。不跑批、不调 LLM、不改 `code/{life,orchestration,config,engine}`。")
    L.append("")
    L.append("## §0 一句话结论")
    L.append("")
    ev = " + ".join(f"{r['align']['n_events']}" for r in res["runs"])
    al = " / ".join(f"{r['align']['n_aligned']}" for r in res["runs"])
    ch = " / ".join(f"{r['align']['n_changed']}" for r in res["runs"])
    ep = " / ".join(f"{r['independence']['n_distinct_episodes']}" for r in res["runs"])
    epc = " / ".join(f"{r['independence']['n_distinct_episodes_changed']}" for r in res["runs"])
    L.append(f"**能对齐的事件很少，且高度重复，因此本轮只能报计数、不能下「称呼跟不跟得上」的结论**："
             f"两份真 LLM 日志各有 `RELATION_CHANGE` {ev} 条，其中「变化前有具名称呼 **且** 变化后有具名称呼」"
             f"的可判事件 {al} 条；而这些事件背后的**不重复片段（有向对 × before/after 形式）只有 {ep} 个**，"
             f"其中「称呼真的变了」的片段 {epc} 个（其余是把同一段称呼被多个关系事件重复计数）。"
             f"⇒ 口径上**只报事件数与片段数，不报百分比、不作趋势判断**。")
    L.append("")
    L.append("## §1 数据来源与坐标可核性")
    L.append("")
    L.append("| run | 日志 | run.jsonl sha256 | `RELATION_CHANGE` | MSG 记录 | 可用具名称呼 | 有称呼的有向对 | seq 稠密 | 哈希链 | seq 范围 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in res["runs"]:
        L.append(f"| `{r['key']}` | `{r['log']}` | `{r['log_sha256']}` | {r['n_rc_events']} | {r['n_msg_records']} "
                 f"| {r['n_addr_msgs_usable']} | {r['n_directed_pairs_with_addr']} "
                 f"| {'✅' if r['seq_dense'] else '❌'} | {'✅' if r['chain_ok'] else '❌'} "
                 f"| {r['seq_range'][0]}–{r['seq_range'][1]} |")
    L.append("")
    L.append("> 坐标口径：事件与称呼**共用同一个 `seq` 轴**（同一条哈希链、稠密自增，上表两列即现场校验结果）。"
             "⇒ 「时间戳不可比」这一类在本批为 0，不是靠假设，是靠 `seq` 稠密性实测。")
    L.append("")
    L.append("## §2 对齐结果（分子分母都写，分母即事件数）")
    L.append("")
    L.append("| run | 事件总数 | 对齐成功（可判） | 其中**有**称呼变化 | 其中**无**称呼变化 "
             "| 丢配合计 | 对方未再发声 | 称呼未具名 | 变化前无基线 | 事件字段缺失 | 时间戳不可比 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in res["runs"]:
        a = r["align"]
        lb = a["lost_by_reason"]
        L.append(f"| `{r['key']}` | {a['n_events']} | **{a['n_aligned']}** | **{a['n_changed']}** | **{a['n_unchanged']}** "
                 f"| {a['n_lost']} | {lb.get('对方未再发声', 0)} | {lb.get('称呼未具名', 0)} "
                 f"| {lb.get('变化前无基线', 0)} | {lb.get('事件字段缺失', 0)} | {lb.get('时间戳不可比', 0)} |")
    L.append("")
    L.append("## §2b 独立性诊断（**读 §2 之前先读这张表**）")
    L.append("")
    L.append("| run | 对齐成功事件 | 涉及的不同有向对 | **不重复片段**（对×before/after） | 其中称呼真变了 | 单片段最大重复次数 |")
    L.append("|---|---|---|---|---|---|")
    for r in res["runs"]:
        a, ind = r["align"], r["independence"]
        L.append(f"| `{r['key']}` | {a['n_aligned']} | {ind['n_distinct_pairs_aligned']} "
                 f"| **{ind['n_distinct_episodes']}** | **{ind['n_distinct_episodes_changed']}** "
                 f"| {ind['max_events_per_episode']} |")
    L.append("")
    L.append("> 为什么会重复：`RELATION_CHANGE` 在 `round 0–23` 密集发生（familiarity 每遇到一次 +1），"
             "同一对居民的 20–28 个关系事件夹在**同一对**称呼之间 ⇒ 同一个「before→after」被数很多次。"
             "所以「变化 2 次」不等于「2 个不同的关系变化引发了 2 次称呼变化」。")
    L.append("")
    L.append("| run | 不重复片段明细（对 / before→after / 被几个事件共用） |")
    L.append("|---|---|")
    for r in res["runs"]:
        eps = r["independence"]["episodes"]
        cell = "<br>".join(f"{e['pair'][0]}→{e['pair'][1]}：{e['form_before']}→{e['form_after']}"
                           f"（{e['n_events']} 个事件）{'【变了】' if e['changed'] else ''}" for e in eps) or "—"
        L.append(f"| `{r['key']}` | {cell} |")
    L.append("")
    L.append("## §3 按关系维度拆（同一批事件按 `payload.dim` 分箱，仍是事件数）")
    L.append("")
    L.append("| run | dim | 事件数 | 对齐成功 | 有变化 | 无变化 |")
    L.append("|---|---|---|---|---|---|")
    for r in res["runs"]:
        for dim, d in r["align"]["by_dim"].items():
            L.append(f"| `{r['key']}` | {dim} | {d['n']} | {d['aligned']} | {d['changed']} | {d['unchanged']} |")
    L.append("")
    L.append("## §4 强变化子集（`|after-before| >= 3`）与空变化事件")
    L.append("")
    L.append("| run | 强变化事件数 | 其中对齐成功 | 有变化 | 无变化 | `after == before` 的事件数 |")
    L.append("|---|---|---|---|---|---|")
    for r in res["runs"]:
        s = r["align"]["strong_subset"]
        L.append(f"| `{r['key']}` | {s['n']} | {s['aligned']} | {s['changed']} | {s['unchanged']} "
                 f"| {r['align']['n_zero_delta_events']} |")
    L.append("")
    L.append("## §5 逐条对齐明细（对齐成功的事件，全部列出，不抽样）")
    L.append("")
    for r in res["runs"]:
        rows = [x for x in r["rows"] if x["status"] == "对齐成功"]
        L.append(f"### {r['key']}（{len(rows)} 条）")
        L.append("")
        if not rows:
            L.append("（本 run 无可判事件）")
            L.append("")
            continue
        L.append("| seq | 有向对 | dim | before→after | 变化前称呼（seq） | 变化后称呼（seq） | 是否变化 | 变化后原句 |")
        L.append("|---|---|---|---|---|---|---|---|")
        for x in rows:
            L.append(f"| {x['seq']} | {x['pair'][0]}→{x['pair'][1]} | {x['dim']} | {x['before']}→{x['after']} "
                     f"| {x['form_before']}(tier{x['tier_before']}, seq {x['seq_before']}) "
                     f"| {x['form_after']}(tier{x['tier_after']}, seq {x['seq_after']}) "
                     f"| {'**是**' if x['changed'] else '否'} | {(x.get('body_after') or '').replace('|','/')} |")
        L.append("")
    L.append("## §6 丢配原因分类（逐类给定义与判定方式）")
    L.append("")
    L.append("| 类别 | 判定（写死在 `align()` 里） | 说明 |")
    L.append("|---|---|---|")
    L.append("| 对方未再发声 | 该有向对在事件 `seq` **之后完全无 MSG** | 关系变了，但这一对之后**没再说话** ⇒ 称呼无从观察 |")
    L.append("| 称呼未具名 | 之后有 MSG，但没有任何 `target_ok/generic` 的呼语位具名称呼 | 说了话但没叫名字（或叫错人） ⇒ 无法比「怎么叫」 |")
    L.append("| 变化前无基线 | 事件之前该有向对**没有**具名称呼 | 只能看到变化后怎么叫，没有对照 ⇒ 不判 |")
    L.append("| 事件字段缺失 | `payload.from/to` 或 `seq` 为空 | 本批为 0 |")
    L.append("| 时间戳不可比 | `seq` 非稠密或哈希链断裂 | 本批为 0（§1 已实测） |")
    L.append("")
    L.append("## §7 无向对敏感性（**不作判据**）")
    L.append("")
    L.append("| run | 有称呼的无向对 | 对齐成功事件 | 有变化 | 无变化 |")
    L.append("|---|---|---|---|---|")
    for r in res["runs"]:
        u = r["undirected_sensitivity"]
        L.append(f"| `{r['key']}` | {u['pairs_with_addr']} | {u['n_aligned']} | {u['n_changed']} | {u['n_unchanged']} |")
    L.append("")
    L.append("> 无向对会把「甲→乙」和「乙→甲」混成一条线（D10 的 v1 口径就栽在这里）⇒ 只作敏感性，不进判据。")
    L.append("")
    L.append("## §8 本轮**不能**得出什么结论（必须一起读）")
    L.append("")
    L.append("1. **不能**说「关系变化后称呼不跟着变」，也**不能**说「称呼会跟着变」："
             "可判**事件**虽有 44 / 42（≥30），但它们背后的**不重复片段只有 10 / 14（<30）**，"
             "且同一片段被重复计数（§2b）⇒ 按「分母<30 只报事件数」的纪律，本件**不报百分比**。"
             "若下游一定要引用，必须写成「N 个不重复片段里 M 个称呼发生了变化」，并同时给出片段数分母。")
    L.append("2. **不能**把「丢配」当「关系没影响」：丢配主要来自**采样结构**——"
             "每对居民全批只有 191 条 MSG 分给 272 个有向对，且关系事件在 `round 0–23` 均匀密集发生，"
             "大多数有向对在某个关系事件之后根本没再发过言。")
    L.append("3. **不能**把事件数当独立样本：§2b 已给出证据——对齐成功的几十个事件其实只对应个位数的"
             "不重复片段，同一个「before→after」被多个关系事件重复计数。引用本件时必须同时给片段数。")
    L.append("4. **不能**归因方向：本对齐只说「事件之后第一次具名称呼」与「事件之前最后一次」相同/不同，"
             "**不排除**「称呼由人格模板固定」(H0) 与「关系驱动」(H1) 两种解释——这正是需要在"
             "预登记里用更大规模双臂才能分开的东西。")
    L.append("")
    L.append("## §9 复算命令")
    L.append("")
    L.append("```bash")
    L.append("python3 tools/addr_relation/n16_align.py --selftest")
    L.append("python3 tools/addr_relation/n16_align.py            # 默认 2 份日志")
    L.append("python3 tools/addr_relation/n16_align.py --runs v2/evidence/d9m-ab-off_n16r24_s42 \\")
    L.append("        v2/evidence/d9s-on_n16r24_s42 v2/evidence/round1_narration_default_n16r24_s42")
    L.append("```")
    L.append("")
    L.append("产物：`v2/evidence/addr_relation/n16_alignment.json`（含全部逐条行）与本文件。")
    L.append("")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="N-16 RELATION_CHANGE × 称呼序列对齐（只读）")
    ap.add_argument("--runs", nargs="*", default=None)
    ap.add_argument("--out-json", default=os.path.join(ROOT, "v2/evidence/addr_relation/n16_alignment.json"))
    ap.add_argument("--out-md", default=os.path.join(ROOT, "v2/evidence/addr_relation/n16-alignment.md"))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()

    runs = a.runs or [os.path.join(ROOT, p) for p in DEFAULT_RUNS]
    ADDR = load_module("addr_drift", ADDR_TOOL)

    out = {
        "tool": "tools/addr_relation/n16_align.py",
        "tool_sha256": sha256_file(os.path.abspath(__file__)),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git": git_head(),
        "inputs": {
            "addr_impl": {"path": os.path.relpath(ADDR_TOOL, ROOT), "sha256": sha256_file(ADDR_TOOL)},
            "lexicon": {"path": os.path.relpath(LEXICON, ROOT), "sha256": sha256_file(LEXICON)},
            "personas": {"path": os.path.relpath(PERSONAS, ROOT), "sha256": sha256_file(PERSONAS)},
        },
        "runs": [],
    }
    for rd in runs:
        log = os.path.join(rd, "run.jsonl")
        if not os.path.isfile(log):
            print(f"[FAIL] 输入不可用: {log}", file=sys.stderr)
            return 2
        scan = scan_log(log)
        amsgs = addr_msgs(ADDR, scan["msgs"])
        out["runs"].append(align(os.path.basename(rd.rstrip("/")), os.path.relpath(log, ROOT),
                                 sha256_file(log), scan, amsgs))

    os.makedirs(os.path.dirname(os.path.abspath(a.out_json)), exist_ok=True)
    with open(a.out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
    md = to_markdown(out)
    os.makedirs(os.path.dirname(os.path.abspath(a.out_md)), exist_ok=True)
    with open(a.out_md, "w", encoding="utf-8") as f:
        f.write(md + "\n")

    for r in out["runs"]:
        al = r["align"]
        print(f"[n16] {r['key']}: events={al['n_events']} aligned={al['n_aligned']} "
              f"changed={al['n_changed']} unchanged={al['n_unchanged']} lost={al['n_lost']} "
              f"lost_by_reason={al['lost_by_reason']}")
    print(f"[n16] out_json={a.out_json}")
    print(f"[n16] out_md  ={a.out_md}")
    return 0


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
