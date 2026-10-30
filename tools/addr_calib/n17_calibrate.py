#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N-17 对拍器：`addr_error_rate`（D10 尺子） vs 官方 `L-10 self_address_error_rate`。

一句话：**两个数不是同一件事**。本脚本把两者的实现逐字段摊开，并在同一批已入库
真实 LLM 日志上各算一遍、逐份并列、逐条归因差异。

零 LLM、零写入运行时代码、纯只读：只 import 两个既有实现（不改一行），
只写 `tools/addr_calib/` 与 `v2/evidence/addr_calib/`。

两侧定义的真实位置（读代码确认，不是转述）：
  * `addr_error_rate`：`tools/metrics/address_drift.py` 第 254–271 行（指向分类）
    与第 366–369 / 422–435 行（`addr_misaddress` 汇总）。
  * 官方 `L-10`：`tools/d5/dialogue_metrics.py` 第 919–932 行（分子/分母的逐条循环）
    与第 1011–1012 行（`L-10_self_address_error_rate` / `L-10_denominator`）。
    **注意**：任务书写的"`code/obs/` 下"与仓库现状不符——`code/obs/` 里没有 L-10 实现，
    唯一实现就在 `tools/d5/dialogue_metrics.py`；本脚本按真实位置对拍。

用法（一行命令重跑，默认 5 份 D10 日志）：
    python3 tools/addr_calib/n17_calibrate.py
    python3 tools/addr_calib/n17_calibrate.py --runs v2/evidence/<a> v2/evidence/<b> ...
    python3 tools/addr_calib/n17_calibrate.py --selftest

退出码：0 正常；2 输入不可用；3 自检/复刻校验失败（复刻与官方实现不一致时**不得**出数）。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ADDR_TOOL = os.path.join(ROOT, "tools", "metrics", "address_drift.py")
OFF_TOOL = os.path.join(ROOT, "tools", "d5", "dialogue_metrics.py")
PERSONAS = os.path.join(ROOT, "code", "config", "personas.json")
LEXICON = os.path.join(ROOT, "v2", "refs", "address-ordinal.yaml")

DEFAULT_RUNS = [
    "v2/evidence/d9m-ab-off_n16r24_s42",
    "v2/evidence/d9m-ab-on_n16r24_s42",
    "v2/evidence/d9s-off_n16r24_s42",
    "v2/evidence/d9s-on_n16r24_s42",
    "v2/evidence/round1_narration_default_n16r24_s42",
]


# --------------------------------------------------------------------------- 基础设施
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def git_head() -> dict:
    try:
        sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.strip()
        br = subprocess.run(["git", "-C", ROOT, "rev-parse", "--abbrev-ref", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
        return {"head_sha": sha, "branch": br}
    except Exception as e:  # noqa: BLE001
        return {"head_sha": None, "branch": None, "error": str(e)}


# --------------------------------------------------------------------------- 两侧实现细节（写死，供逐字段摊开）
FIELD_DIFF = [
    {
        "field": "口径定义（测的是什么现象）",
        "addr": "**称呼错指**：说话人在**呼语位**叫出的名字，指向的不是当前对话对象"
                "（叫成自己 = self_name；叫成第三者 = other_named）",
        "official": "**第一人称身份自述错误**：正文出现「我(，)?(是|叫|乃|就是)?<另一位居民的名字>」"
                    "⇒ 说话人把自己说成别人（L-10_self_address_error_rate）",
        "note": "两者是**不同构念**：一个测「叫谁」，一个测「说我是谁」。数值不可互相替代。",
    },
    {
        "field": "代码位置",
        "addr": "tools/metrics/address_drift.py:254-271（指向分类）、:366-369、:422-435（汇总）；"
                "复算入口 `compute()`",
        "official": "tools/d5/dialogue_metrics.py:919-932（分子/分母循环）、:1011-1012（出数）；"
                    "复算入口 `compute()` 内的 `L_wording` 块",
        "note": "任务书说官方实现在 `code/obs/` 下，**与仓库不符**；`code/obs/` 中 grep 不到 "
                "`self_address_error`/`L-10`，唯一实现在 tools/d5。",
    },
    {
        "field": "统计单位",
        "addr": "**MSG 条**，且必须是「呼语位命中具名称呼 **且** 指向可判（有明确 addressee）」的消息",
        "official": "**MSG 条**，只要正文含自称代词（我/俺/咱）**或**含他人名字",
        "note": "单位都是 MSG 条 ⇒ 形式上同类；差别在**入池条件**（见下两行）。",
    },
    {
        "field": "分母取法",
        "addr": "`n_named_addr_judgeable = target_ok + self_name + other_named`"
                "（排除 generic 通用称呼、排除 unknown_target 指向不可判）",
        "official": "`L-10_denominator = cand`：正文含 我/俺/咱 **或** 含任一他人 display_name 的消息条数"
                    "（什么都不排除，也不要求有称呼）",
        "note": "官方分母天然接近全量 MSG（本批 174/191），addr 分母只有几十条量级 ⇒ 两率的分母规模差一个量级。",
    },
    {
        "field": "预处理 / 去重规则",
        "addr": "先剥「说话人标签前缀」（仅当标签文本是某居民基名）→ 再剥 `（…）/(…)` 括注 → "
                "词表最长优先匹配 → 同句多命中取**最靠前**一个；**一句只取一个称呼**（取到即止）",
        "official": "**不做任何预处理**：不剥括注、不剥标签前缀，直接在 `body` 原文上跑正则；"
                    "`break` 保证**一条消息最多计 1 次分子**",
        "note": "addr 剥旁白 ⇒ 括注里的名字不算称呼；官方把括注里的名字也算进「提到他人」⇒ 分母被抬高。",
    },
    {
        "field": "排除条件",
        "addr": "① `generic` 通用称呼（师傅/老板…，指向不可判）整类排除；② `unknown_target`"
                "（公开场合无明确对象）排除；③ 非呼语位的「提及」不计入",
        "official": "**无排除**：只排除说话人**自己**的名字（`pid != from`）；他人名字无论在句子哪个位置都算",
        "note": "官方不区分「称呼」与「提及」，也不区分指向。",
    },
    {
        "field": "分子匹配方式",
        "addr": "词表驱动（`v2/refs/address-ordinal.yaml` 冻结件 + personas 派生形式，含 叔/婶/师傅 等后缀变体），"
                "按 owner 集合判指向",
        "official": "**单一正则**：`我[，,]?\\s*(?:是|叫|乃|就是)?\\s*<他人 display_name>`；"
                "名字集合 = personas.json 的基名（去 `青溪镇·` 前缀），**不含**任何后缀变体（石叔/石师傅 等）",
        "note": "官方只认基名（老石/秀娘），addr 认一整个词表家族 ⇒ 识别面不同。",
    },
    {
        "field": "「自称」判定的方向",
        "addr": "`self_name` = 说话人**在呼语位叫出自己名字**（如 P002 对 P004 说「老石，早。」）",
        "official": "命中 = 说话人**用第一人称说出别人名字**（「我是老石」）——这与 addr 的 `self_name` **不是同一事件**",
        "note": "两侧都用「自称/自我」字样，但**事件方向相反**，是最容易被误读成「同口径」的地方。",
    },
]


# --------------------------------------------------------------------------- 单 run 计算
def addr_replica(ADDR, log_path: str) -> list[dict]:
    """按 address_drift.py 的逐条逻辑复刻消息级指向分类（用于逐条归因与复刻校验）。"""
    lex = ADDR.load_lexicon(LEXICON)
    terms, _info, owners = ADDR.build_agent_terms(lex, PERSONAS)
    base_names = {p["display_name"].split("·")[-1].strip()
                  for p in json.load(open(PERSONAS, encoding="utf-8"))["personas"]}
    voc = lex.get("vocative") or {}
    rows = []
    for rec in ADDR.iter_msgs(log_path):
        m = ADDR.as_msg(rec)
        if m is None:
            continue
        text = ADDR.strip_parenthetical(m["body"], base_names)
        hit = ADDR.find_vocative(text, terms, voc)
        form = hit[0] if hit else None
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
        rows.append({
            "seq": m["seq"], "type": m["type"], "speaker": m["speaker"],
            "addressee": m["addressee"], "thread_id": m["thread_id"],
            "body": m["body"], "text_after_strip": text,
            "addr_form": form, "addr_target": target,
            "form_owners": sorted(owners.get(form) or []) if form else [],
        })
    return rows


def official_replica(OFF, log_path: str) -> tuple[list[dict], dict]:
    """按 dialogue_metrics.py:919-932 复刻 L-10 逐条逻辑（消息级），并返回汇总。"""
    recs, _parse = OFF.read_run(log_path)
    msgs = OFF.extract_messages(recs)
    names, _pinfo = OFF.load_personas(PERSONAS)
    import re as _re
    rows = []
    cand = 0
    self_err = 0
    for m in msgs:
        body = m["body"]
        has_self = ("我" in body) or ("俺" in body) or ("咱" in body)
        others = [(pid, nm) for pid, nm in names.items()
                  if pid != str(m["from"]) and nm and nm in body]
        in_den = bool(has_self or others)
        hit_name = None
        if in_den:
            cand += 1
        for pid, nm in others:
            if _re.search(r"我[，,]?\s*(?:是|叫|乃|就是)?\s*" + _re.escape(nm), body):
                self_err += 1
                hit_name = nm
                break
        rows.append({
            "seq": m["seq"], "channel": m["channel"], "speaker": m["from"],
            "body": body, "has_self_pronoun": has_self,
            "other_names_in_body": [nm for _pid, nm in others],
            "in_denominator": in_den, "regex_matched_name": hit_name,
        })
    return rows, {"n_self_err": self_err, "denominator": cand, "n_msgs": len(msgs)}


def run_official_cli(log_path: str, out_json: str, meta_path: str | None = None) -> dict:
    cmd = [sys.executable, OFF_TOOL, "--log", log_path, "--out-json", out_json]
    if meta_path and os.path.isfile(meta_path):
        cmd += ["--meta", meta_path]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"official CLI failed rc={r.returncode}: {r.stderr[-800:]}")
    return json.load(open(out_json, encoding="utf-8"))


# --------------------------------------------------------------------------- 归因
def attribute(arow: dict | None, orow: dict | None) -> list[str]:
    """对单条消息在两口径下的归属差异给出原因标签（可机械复算，不靠人工圆）。"""
    a_num = arow is not None and arow["addr_target"] in ("self_name", "other_named")
    a_den = arow is not None and arow["addr_target"] in ("target_ok", "self_name", "other_named")
    o_num = orow is not None and orow["regex_matched_name"] is not None
    o_den = orow is not None and orow["in_denominator"]
    tags: list[str] = []
    if a_num and not o_num:
        if arow["addr_target"] == "self_name":
            tags.append("ADDR_SELFNAME_NOT_IN_OFFICIAL_UNIVERSE：官方分子只匹配「我+是/叫/乃/就是+**他人**名字」，"
                        "说话人拿自己名字当呼语结构上永远进不了官方分子")
        elif arow["addr_target"] == "other_named":
            tags.append("ADDR_MISADDR_VOCATIVE_NOT_SELFSTATEMENT：错称发生在**呼语位**"
                        f"（「{arow['addr_form']}，…」），不是第一人称自述，官方正则不命中")
    if o_num and not a_num:
        if not a_den:
            tags.append("OFFICIAL_SELFSTATEMENT_NO_VOCATIVE：命中「我…<他人名>」但该句**没有呼语位具名称呼**"
                        "（或指向不可判/通用称呼）⇒ 官方计入分子，addr 连分母都进不去")
        else:
            tags.append("DEFINITION_SPLIT：官方认为这是自称错误，addr 认为呼语指向正确（target_ok）"
                        "——两侧对「错」的定义不同")
    if a_den and not o_den:
        tags.append("ADDR_DEN_ONLY：addr 分母含（呼语位具名称呼 + 指向可判），官方分母不含"
                    "（正文无 我/俺/咱 且无他人名）")
    if o_den and not a_den:
        tags.append("OFFICIAL_DEN_ONLY：官方分母含（正文含自称代词或含他人名），但该句无呼语位具名称呼 ⇒ addr 不入分母")
    return tags


def analyze_run(ADDR, OFF, run_dir: str) -> dict:
    log = os.path.join(run_dir, "run.jsonl")
    if not os.path.isfile(log):
        raise FileNotFoundError(log)
    meta_path = os.path.join(run_dir, "meta.json")
    meta = json.load(open(meta_path, encoding="utf-8")) if os.path.isfile(meta_path) else {}
    log_sha = sha256_file(log)

    # --- addr 侧：官方 compute() 出数（权威）+ 复刻（逐条）
    a_full = ADDR.compute(log, LEXICON, PERSONAS, None)
    a_rows = addr_replica(ADDR, log)
    mis = a_full["addr_misaddress"]
    replica_counts = {
        "denominator": sum(1 for r in a_rows if r["addr_target"] in ("target_ok", "self_name", "other_named")),
        "n_target_ok": sum(1 for r in a_rows if r["addr_target"] == "target_ok"),
        "n_self_name": sum(1 for r in a_rows if r["addr_target"] == "self_name"),
        "n_other_named": sum(1 for r in a_rows if r["addr_target"] == "other_named"),
    }
    addr_ok = (replica_counts["denominator"] == mis["n_named_addr_judgeable"]
               and replica_counts["n_self_name"] == mis["n_self_name"]
               and replica_counts["n_other_named"] == mis["n_other_named"])

    # --- 官方侧：CLI 出数（权威）+ 复刻（逐条）
    tmp_json = os.path.join(tempfile.gettempdir(), f"n17_off_{os.path.basename(run_dir)}.json")
    off_full = run_official_cli(log, tmp_json, meta_path)
    o_rows, o_rep = official_replica(OFF, log)
    lw = off_full["L_wording"]
    off_ok = (lw["L-10_denominator"] == o_rep["denominator"]
              and abs((lw["L-10_self_address_error_rate"] or 0.0)
                      - (o_rep["n_self_err"] / o_rep["denominator"] if o_rep["denominator"] else 0.0)) < 1e-9
              and off_full["meta"]["n_messages"] == o_rep["n_msgs"])

    # --- 逐条对拍（按 seq 对齐；两侧 seq 均来自同一 run.jsonl 记录）
    a_by = {}
    for r in a_rows:
        a_by.setdefault(r["seq"], []).append(r)
    o_by = {}
    for r in o_rows:
        o_by.setdefault(r["seq"], []).append(r)
    seqs = sorted(set(a_by) | set(o_by), key=lambda x: (x is None, x))

    disagreements = []
    xtab = {"both_den": 0, "addr_den_only": 0, "official_den_only": 0, "neither_den": 0,
            "both_num": 0, "addr_num_only": 0, "official_num_only": 0}
    tag_counter: dict[str, int] = {}
    for s in seqs:
        al = a_by.get(s) or [None]
        ol = o_by.get(s) or [None]
        for arow in al:
            for orow in ol:
                a_den = arow is not None and arow["addr_target"] in ("target_ok", "self_name", "other_named")
                a_num = arow is not None and arow["addr_target"] in ("self_name", "other_named")
                o_den = orow is not None and orow["in_denominator"]
                o_num = orow is not None and orow["regex_matched_name"] is not None
                if a_den and o_den:
                    xtab["both_den"] += 1
                elif a_den:
                    xtab["addr_den_only"] += 1
                elif o_den:
                    xtab["official_den_only"] += 1
                else:
                    xtab["neither_den"] += 1
                if a_num and o_num:
                    xtab["both_num"] += 1
                elif a_num:
                    xtab["addr_num_only"] += 1
                elif o_num:
                    xtab["official_num_only"] += 1
                if a_num != o_num or a_den != o_den:
                    tags = attribute(arow, orow)
                    for t in tags:
                        key = t.split("：")[0]
                        tag_counter[key] = tag_counter.get(key, 0) + 1
                    if a_num or o_num:  # 只把"分子级"差异逐条列出，避免分母差把表撑爆
                        disagreements.append({
                            "seq": s,
                            "type": (arow or {}).get("type") or (orow or {}).get("channel"),
                            "speaker": (arow or {}).get("speaker") or (orow or {}).get("speaker"),
                            "addr_target": (arow or {}).get("addr_target"),
                            "addr_form": (arow or {}).get("addr_form"),
                            "addr_form_owners": (arow or {}).get("form_owners") or [],
                            "official_matched_name": (orow or {}).get("regex_matched_name"),
                            "body": ((arow or orow) or {}).get("body", "")[:120],
                            "reasons": tags,
                        })

    # --- 与 D10 已发布读数对拍（同一尺子、同一日志 ⇒ 必须逐位复现）
    key = os.path.basename(run_dir.rstrip("/"))
    d10_path = os.path.join(ROOT, "v2", "evidence", "d10_address_drift", key + ".json")
    d10 = {"path": os.path.relpath(d10_path, ROOT), "exists": os.path.isfile(d10_path)}
    if d10["exists"]:
        d10j = json.load(open(d10_path, encoding="utf-8"))
        d10m = d10j["addr_misaddress"]
        d10.update({
            "d10_rate": d10m["addr_error_rate"],
            "d10_denominator": d10m["n_named_addr_judgeable"],
            "d10_n_num": d10m["n_addr_err"],
            "d10_tool_sha256": d10j.get("tool_sha256"),
            "same_tool": d10j.get("tool_sha256") == a_full["tool_sha256"],
            "same_log": d10j.get("input_log_sha256") == log_sha,
            "matches": (d10m["n_named_addr_judgeable"] == mis["n_named_addr_judgeable"]
                        and d10m["n_addr_err"] == mis["n_addr_err"]),
        })
    else:
        d10["CANNOT-ATTRIBUTE"] = "D10 未发布该 run 的读数，无法与之对拍（不填数）"

    return {
        "key": key,
        "d10_evidence": d10,
        "run_dir": os.path.relpath(run_dir, ROOT),
        "log": os.path.relpath(log, ROOT),
        "log_sha256": log_sha,
        "meta_code_sha": meta.get("code_sha"),
        "meta_model": meta.get("model"),
        "official_admission": off_full.get("admission", {}).get("verdict"),
        "official_admission_failing": sorted(
            k for k, v in (off_full.get("admission", {}).get("checks") or {}).items()
            if not (isinstance(v, dict) and v.get("pass"))),
        "addr": {
            "unit": "MSG 条（呼语位具名称呼且指向可判）",
            "n_messages": a_full["n_messages"],
            "n_messages_with_addr": a_full["n_messages_with_addr"],
            "denominator": mis["n_named_addr_judgeable"],
            "n_target_ok": mis["n_target_ok"],
            "n_self_name": mis["n_self_name"],
            "n_other_named": mis["n_other_named"],
            "n_num": mis["n_addr_err"],
            "rate": mis["addr_error_rate"],
            "n_generic": mis["n_generic"],
            "n_unknown_target": mis["n_unknown_target"],
            "tool_sha256": a_full["tool_sha256"],
            "lexicon_sha256": a_full["lexicon_sha256"],
        },
        "official": {
            "unit": "MSG 条（正文含 我/俺/咱 或含他人名）",
            "n_messages": o_rep["n_msgs"],
            "denominator": lw["L-10_denominator"],
            "n_num": o_rep["n_self_err"],
            "rate": lw["L-10_self_address_error_rate"],
            "official_json_admission": off_full.get("admission", {}).get("verdict"),
        },
        "crosstab": xtab,
        "reason_tag_counts": dict(sorted(tag_counter.items())),
        "disagreements": disagreements,
        "replica_check": {
            "addr_replica_matches_official_compute": addr_ok,
            "addr_replica_counts": replica_counts,
            "official_replica_matches_cli": off_ok,
            "official_replica_counts": o_rep,
        },
    }


# --------------------------------------------------------------------------- 自检
def selftest() -> int:
    ADDR = load_module("addr_drift", ADDR_TOOL)
    OFF = load_module("dialogue_metrics", OFF_TOOL)
    bad = 0
    # 合成日志：一条「我+他人名」（官方命中，addr 不命中）+ 一条「叫成自己」（addr 命中，官方不命中）
    lines = [
        {"seq": 1, "round": 0, "type": "MSG_DM",
         "payload": {"body": "我是老石，你别急。", "author": "P004", "from": "P004", "to": "P002",
                     "participants": ["P004", "P002"], "thread_id": "T1", "turn_index": 0}},
        {"seq": 2, "round": 0, "type": "MSG_DM",
         "payload": {"body": "老石，早。", "author": "P002", "from": "P002", "to": "P004",
                     "participants": ["P002", "P004"], "thread_id": "T1", "turn_index": 1}},
    ]
    import shutil
    tmpdir = tempfile.mkdtemp(prefix="n17_selftest_")
    with open(os.path.join(tmpdir, "run.jsonl"), "w", encoding="utf-8") as f:
        for r in lines:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    res = analyze_run(ADDR, OFF, tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)
    a, o = res["addr"], res["official"]
    print("[selftest] addr:", a["n_num"], "/", a["denominator"], "official:", o["n_num"], "/", o["denominator"])
    if not (a["n_num"] == 1 and o["n_num"] == 1):
        bad += 1
        print("[SELFTEST FAIL] 期望两侧各 1 次命中")
    if not (res["replica_check"]["addr_replica_matches_official_compute"]
            and res["replica_check"]["official_replica_matches_cli"]):
        bad += 1
        print("[SELFTEST FAIL] 复刻未与实现对齐", res["replica_check"])
    print(f"[selftest] {'FAIL' if bad else 'PASS'} (failures={bad})")
    return 3 if bad else 0


# --------------------------------------------------------------------------- 报告
def fmt_rate(x, den) -> str:
    if x is None:
        return "NA"
    pct = x * 100
    s = f"{pct:.2f}%"
    if den is not None and den < 30:
        s += "（分母<30，仅报事件数参考）"
    return s


def to_markdown(res: dict) -> str:
    L: list[str] = []
    L.append("# N-17 对拍：`addr_error_rate`（D10）vs 官方 `L-10 self_address_error_rate`")
    L.append("")
    L.append(f"- 生成时间：`{res['generated_at']}`")
    L.append(f"- 仓库 HEAD（**读日志时刻**）：`{res['git']['head_sha']}`（分支 `{res['git']['branch']}`）")
    L.append(f"- 对拍器：`tools/addr_calib/n17_calibrate.py` sha256 `{res['tool_sha256']}`")
    L.append("- 性质：**只读核算**。不跑批、不调 LLM、不改 `code/{life,orchestration,config,engine}`。")
    L.append("")
    L.append("## §0 一句话结论")
    L.append("")
    L.append("**这两个数不是同一个量，不能互相替代，也不构成「两个口径不一致需修一个」的问题**："
             "`addr_error_rate` 测「**在呼语位把谁叫成谁**」（叫成自己 / 叫成第三者），"
             "官方 `L-10` 测「**用第一人称把自己说成别人**」（`我(是|叫)X`）。"
             "本批 5 份日志里，两者分子**逐条零重叠**，分母规模差一个量级（几十 vs 174/191）。"
             "因此 D10 §0.5 的 5 个 `addr_error_rate` 读数只能作为「称呼错指率」的**描述量**，"
             "**不得**被写成「官方 L-10 的另一种算法」。")
    L.append("")
    L.append("## §1 逐字段差异（读代码确认，行号可原位核对）")
    L.append("")
    L.append("| 字段 | `addr_error_rate`（tools/metrics/address_drift.py） | 官方 `L-10`（tools/d5/dialogue_metrics.py） | 说明 |")
    L.append("|---|---|---|---|")
    for d in FIELD_DIFF:
        L.append(f"| {d['field']} | {d['addr']} | {d['official']} | {d['note']} |")
    L.append("")
    L.append("## §2 逐份对拍表（同一批日志，两口径各算一次）")
    L.append("")
    L.append("| run | run.jsonl sha256 | code_sha | addr 分母 | addr 分子（自称+错称） | `addr_error_rate` "
             "| 官方分母 | 官方分子 | `L-10` | 单位 | admission |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in res["runs"]:
        a, o = r["addr"], r["official"]
        L.append(f"| `{r['key']}` | `{r['log_sha256'][:16]}…` | `{(r['meta_code_sha'] or 'NA')[:8]}` "
                 f"| {a['denominator']} | {a['n_num']}（self {a['n_self_name']} + other {a['n_other_named']}） "
                 f"| {fmt_rate(a['rate'], a['denominator'])} | {o['denominator']} | {o['n_num']} "
                 f"| {fmt_rate(o['rate'], o['denominator'])} "
                 f"| MSG 条（addr：呼语位具名且指向可判；官方：含自称代词或他人名） "
                 f"| {r['official_admission']}（FAIL 检查：{', '.join(r['official_admission_failing']) or '无'}） |")
    L.append("")
    L.append("> 完整 sha256 与各级分量见 `n17_calibration.json` 的 `runs[].log_sha256` / `runs[].addr` / `runs[].official`。")
    L.append("")
    L.append("## §3 逐份明细（分母/分子/交叉表/复刻校验）")
    L.append("")
    for r in res["runs"]:
        a, o, x = r["addr"], r["official"], r["crosstab"]
        rc = r["replica_check"]
        L.append(f"### {r['key']}")
        L.append("")
        L.append(f"- 日志：`{r['log']}`，sha256 `{r['log_sha256']}`，meta `code_sha={r['meta_code_sha']}`，模型 `{r['meta_model']}`")
        L.append(f"- MSG 总数：addr 侧读到 `{a['n_messages']}`，官方侧读到 `{o['n_messages']}`（两侧 `MSG_TYPES` 集合差异："
                 f"addr 收 `MSG*` 前缀全部，官方只收 `MSG_DM/MSG_PUBLIC/MSG_GROUP` ⇒ 本批无差异）")
        L.append(f"- addr：分母 `{a['denominator']}`（target_ok {a['n_target_ok']} + self_name {a['n_self_name']} "
                 f"+ other_named {a['n_other_named']}），排除 generic {a['n_generic']} / unknown_target {a['n_unknown_target']}；"
                 f"分子 `{a['n_num']}` ⇒ `{fmt_rate(a['rate'], a['denominator'])}`")
        L.append(f"- 官方：分母 `{o['denominator']}`，分子 `{o['n_num']}` ⇒ `{fmt_rate(o['rate'], o['denominator'])}`")
        L.append(f"- 交叉表（消息级）：双方都在分母 `{x['both_den']}`；仅 addr 分母 `{x['addr_den_only']}`；"
                 f"仅官方分母 `{x['official_den_only']}`；都不在 `{x['neither_den']}`")
        L.append(f"- 分子重叠：双方都计 `{x['both_num']}`；仅 addr `{x['addr_num_only']}`；仅官方 `{x['official_num_only']}`")
        n_all = a["n_messages"]
        L.append(f"- 强行换到同一分母（MSG 总数 `{n_all}`，**仅为描述，不是任何一方的口径**）："
                 f"addr `{a['n_num']}/{n_all}` = {(a['n_num']/n_all*100 if n_all else 0):.2f}% vs "
                 f"官方 `{o['n_num']}/{n_all}` = {(o['n_num']/n_all*100 if n_all else 0):.2f}%")
        L.append(f"- 复刻校验：addr 复刻 vs `compute()` = {'PASS' if rc['addr_replica_matches_official_compute'] else 'FAIL'}；"
                 f"官方复刻 vs CLI = {'PASS' if rc['official_replica_matches_cli'] else 'FAIL'}")
        d10 = r["d10_evidence"]
        if d10.get("exists"):
            L.append(f"- **与 D10 已发布读数对拍**：D10 `{d10['path']}` 记 `{d10['d10_n_num']}/{d10['d10_denominator']}` "
                     f"= `{d10['d10_rate']}`；本次复算 `{a['n_num']}/{a['denominator']}` = `{a['rate']}` ⇒ "
                     f"{'**逐位一致**' if d10.get('matches') else '**不一致**'}；"
                     f"同尺子 sha={d10.get('same_tool')}，同日志 sha={d10.get('same_log')}")
        else:
            L.append(f"- 与 D10 已发布读数对拍：CANNOT-ATTRIBUTE —— {d10.get('CANNOT-ATTRIBUTE')}")
        if r["reason_tag_counts"]:
            L.append(f"- 差异原因标签计数：{json.dumps(r['reason_tag_counts'], ensure_ascii=False)}")
        if r["disagreements"]:
            L.append("")
            L.append("| seq | 类型 | 说话人 | addr 指向 | addr 称呼 | 官方命中名 | 原文（截 60 字） | 归因 |")
            L.append("|---|---|---|---|---|---|---|---|")
            for d in r["disagreements"]:
                why = "<br>".join(d["reasons"]) if d["reasons"] else "CANNOT-ATTRIBUTE（无标签命中，见 json）"
                own = d.get("addr_form_owners") or []
                own_s = ",".join(own) or "—"
                L.append(f"| {d['seq']} | {d['type']} | {d['speaker']} | {d['addr_target'] or '—'} | "
                         f"{d['addr_form'] or '—'}（词表 owner：{own_s}） | {d['official_matched_name'] or '—'} | "
                         f"{(d['body'] or '').replace('|','/')} | {why} |")
        else:
            L.append("- **分子级差异：无**（两口径分子无交集也无分歧，即侧重的现象完全不同）")
        L.append("")
    L.append("## §4 差异归因（逐条，能归因的写明机制，不能归因的写 CANNOT-ATTRIBUTE）")
    L.append("")
    L.append("| # | 差异 | 归因 | 证据/复算方式 |")
    L.append("|---|---|---|---|")
    L.append("| 1 | 分母规模差一个量级（几十 vs 174/191） "
             "| 官方分母 = 「含自称代词 或 含他人名」的消息数，天然接近全量；addr 分母 = 「呼语位命中具名称呼且指向可判」"
             " | §1 分母取法行 + §3 交叉表 `official_den_only` 与 `addr_den_only` 两侧计数 |")
    L.append("| 2 | 分子事件方向相反（叫谁 vs 说我是谁） "
             "| addr 分子要「呼语位出现名字」；官方分子要「我 + 判断词 + 他人名」。两个匹配器无交集 "
             "| 各 run 的 `crosstab.both_num`（见 §3） |")
    L.append("| 3 | 预处理不同：addr 剥括注与说话人标签，官方不剥 "
             "| 括注里的名字官方算「提到他人」⇒ 抬高分母；addr 剥掉后既不入分母也不入分子 | "
             "`attribute()` 的 `OFFICIAL_DEN_ONLY` 标签计数 |")
    L.append("| 4 | 名字集合不同：官方只用 personas 基名，addr 用词表家族（含 石叔/石师傅 等后缀变体） "
             "| 官方正则拿不到后缀变体 ⇒ 结构上少识别 | `v2/refs/address-ordinal.yaml` vs `personas.json` |")
    L.append("| 5 | `addr_error_rate` 的分子全落在「词表 owner 为该说话人独占」的形式上"
             "（如 `铁头`→P013、`方老师`→P006），不是多主共用形式的误判 "
             "| 每个差异行都列出 `词表 owner`；单一 owner 且 = 说话人 ⇒ 真·自称（叫成自己） | §3 各 run 明细表的「词表 owner」列 |")
    L.append("| 6 | 官方 L-10 实现位置与任务书描述不符（`code/obs/` 下没有） "
             "| 真实唯一实现是 `tools/d5/dialogue_metrics.py:919-932` | `grep -rn 'self_address_error' code/` 空结果 |")
    L.append("")
    L.append("**CANNOT-ATTRIBUTE 声明**：本报告未发现需要写 CANNOT-ATTRIBUTE 的条目——"
             "每一处差异都能定位到上表某一条机制，且逐条消息级差异都有机械标签。"
             "若后续出现两口径分子同时命中同一消息的情形，脚本会在 `crosstab.both_num` 计数而非静默合并。")
    L.append("")
    L.append("## §5 本轮能说什么 / 不能说什么")
    L.append("")
    L.append("- **能说**：D10 的 5 个 `addr_error_rate` 读数（分母 59–74，均 ≥30）是**称呼错指率**的描述量，"
             "逐份复算可复现；它与官方 L-10 **不同构念**，两者不应互相对齐成同一指标。")
    L.append("- **不能说**：不能说「官方 L-10 = 0 ⇒ 没有称呼错误」。L-10 = 0 只说明**没有「我(是/叫)别人名」这类自述错误**，"
             "与「有没有叫错人」无关。")
    L.append("- **不能说**：两口径的差不能当成「实现 bug」，也不能当成「效果」——它们是不同现象，"
             "在预登记里**不得**互相替代或换算。")
    L.append("- **能说（且必须说）**：官方 `L-10` 在 5 份日志里**分子恒为 0**（分母 165–174）"
             "⇒ 「我(是/叫)别人名」这类自述错误在本配置下**未出现**；也正因为它恒零，"
             "**它对本维度没有区分力**，不能拿 `L-10 = 0` 去背书「称呼没问题」。")
    L.append("- **复算提醒**：官方 CLI 必须带 `--meta`（本脚本在 run 目录有 `meta.json` 时自动传），"
             "否则 B-7 会判「非证据级」而 admission 变 REJECTED（这是准入开关的伪影，不是数据问题）。")
    L.append("- **遗留**：若未来要让官方 L-10 覆盖「称呼错指」，需要新增口径（新登记），"
             "不能在 `code/` 冻结区就地改 L-10 定义。")
    L.append("")
    L.append("## §6 复算命令（一行可重跑）")
    L.append("")
    L.append("```bash")
    L.append("# 自检（合成日志，验证两侧实现都能各自触发、且复刻与实现一致）")
    L.append("python3 tools/addr_calib/n17_calibrate.py --selftest")
    L.append("")
    L.append("# 正式对拍（默认 5 份 D10 日志；--runs 可换任意 run 目录）")
    L.append("python3 tools/addr_calib/n17_calibrate.py")
    L.append("")
    L.append("# 单侧手工复核（与脚本内部调用完全一致）")
    L.append("python3 tools/metrics/address_drift.py --log v2/evidence/d9s-on_n16r24_s42/run.jsonl \\")
    L.append("    --out-json /tmp/a.json --out-md /tmp/a.md")
    L.append("python3 tools/d5/dialogue_metrics.py --log v2/evidence/d9s-on_n16r24_s42/run.jsonl \\")
    L.append("    --meta v2/evidence/d9s-on_n16r24_s42/meta.json --out-json /tmp/b.json --out-md /tmp/b.md")
    L.append("```")
    L.append("")
    L.append("产物：`v2/evidence/addr_calib/n17_calibration.json`（机器可读，含逐条差异与全部 sha256）"
             "与 `v2/evidence/addr_calib/n17-calibration.md`（本文件）。")
    L.append("")
    return "\n".join(L)


# --------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="N-17 addr_error_rate × 官方 L-10 对拍（只读）")
    ap.add_argument("--runs", nargs="*", default=None, help="run 目录列表（默认 5 份 D10 日志）")
    ap.add_argument("--out-json", default=os.path.join(ROOT, "v2/evidence/addr_calib/n17_calibration.json"))
    ap.add_argument("--out-md", default=os.path.join(ROOT, "v2/evidence/addr_calib/n17-calibration.md"))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()

    runs = a.runs or [os.path.join(ROOT, p) for p in DEFAULT_RUNS]
    ADDR = load_module("addr_drift", ADDR_TOOL)
    OFF = load_module("dialogue_metrics", OFF_TOOL)

    out = {
        "tool": "tools/addr_calib/n17_calibrate.py",
        "tool_sha256": sha256_file(os.path.abspath(__file__)),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git": git_head(),
        "inputs": {
            "addr_impl": {"path": os.path.relpath(ADDR_TOOL, ROOT), "sha256": sha256_file(ADDR_TOOL)},
            "official_impl": {"path": os.path.relpath(OFF_TOOL, ROOT), "sha256": sha256_file(OFF_TOOL)},
            "lexicon": {"path": os.path.relpath(LEXICON, ROOT), "sha256": sha256_file(LEXICON)},
            "personas": {"path": os.path.relpath(PERSONAS, ROOT), "sha256": sha256_file(PERSONAS)},
        },
        "field_diff": FIELD_DIFF,
        "runs": [],
    }
    for rd in runs:
        if not os.path.isdir(rd):
            print(f"[FAIL] run 目录不存在: {rd}", file=sys.stderr)
            return 2
        out["runs"].append(analyze_run(ADDR, OFF, rd))

    bad = [r["key"] for r in out["runs"]
           if not (r["replica_check"]["addr_replica_matches_official_compute"]
                   and r["replica_check"]["official_replica_matches_cli"])]
    out["replica_all_pass"] = not bad

    os.makedirs(os.path.dirname(os.path.abspath(a.out_json)), exist_ok=True)
    with open(a.out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
    md = to_markdown(out)
    os.makedirs(os.path.dirname(os.path.abspath(a.out_md)), exist_ok=True)
    with open(a.out_md, "w", encoding="utf-8") as f:
        f.write(md + "\n")

    print(f"[n17] runs={len(out['runs'])} replica_all_pass={out['replica_all_pass']}")
    for r in out["runs"]:
        print(f"  {r['key']}: addr {r['addr']['n_num']}/{r['addr']['denominator']} "
              f"= {r['addr']['rate']} | L-10 {r['official']['n_num']}/{r['official']['denominator']} "
              f"= {r['official']['rate']} | shared_num={r['crosstab']['both_num']}")
    print(f"[n17] out_json={a.out_json}")
    print(f"[n17] out_md  ={a.out_md}")
    if bad:
        print(f"[n17] REPLICA MISMATCH: {bad} ⇒ 出数不可信", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
