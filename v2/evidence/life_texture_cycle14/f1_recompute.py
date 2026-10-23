#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F-1（非功能性闲聊占比）复算器 —— CYCLE-14 / life-texture-analyst

口径唯一来源：tools/d5/dialogue_metrics.py::compute() 的 F-1_chatter 块
（rule: 功能性 = tag_hints∩task_tags 非空 或 正文命中事务正则；闲聊率 = 1 − 功能性占比）。

本脚本不新立尺子：直接 importlib 加载 tools/d5/dialogue_metrics.py，
复用其 read_run / extract_messages / compute / wilson_ci，只额外做**分子分解**
（tag 命中 / 事务正则命中 / 两者都命中），用于可比性裁决引用具体字段。

零 LLM、零跑批、只读 run.jsonl 与 config。

用法：
  python3 v2/evidence/life_texture_cycle14/f1_recompute.py \
      --arm D12-I=<run.jsonl> --arm T5=<run.jsonl> ... \
      --out-json v2/evidence/life_texture_cycle14/f1_readings.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
D5 = os.path.join(REPO, "tools", "d5", "dialogue_metrics.py")

# 与 dialogue_metrics.py:1041 逐字相同（只在分解统计里复述；判定仍走 compute()）
TRANS_RX = re.compile(r"多少钱|价钱|买|卖|记账|按流程|付钱|工钱|便宜点|划算|合同")
WILSON_Z = 1.959964  # tools/d5/f8_lexicon.json::thresholds.wilson_z_95_two_sided


def load_module():
    spec = importlib.util.spec_from_file_location("d5_metrics", D5)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_words(p):
    if not os.path.exists(p):
        return []
    return [ln.strip() for ln in open(p, encoding="utf-8")
            if ln.strip() and not ln.strip().startswith("#")]


def arm_reading(mod, arm, log):
    recs, parse = mod.read_run(log)
    msgs = mod.extract_messages(recs)
    d5d = os.path.join(REPO, "tools", "d5")
    emotion = {}
    for ln in load_words(os.path.join(d5d, "emotion_lexicon.txt")):
        parts = ln.split()
        if len(parts) >= 2:
            try:
                emotion[" ".join(parts[1:])] = int(parts[0])
            except ValueError:
                pass
    task_tags = load_words(os.path.join(d5d, "task_tags.txt"))
    extra = {"emotion": emotion,
             "repair": load_words(os.path.join(d5d, "repair_lexicon.txt")),
             "timeref": load_words(os.path.join(d5d, "timeref_lexicon.txt")),
             "task_tags": task_tags}
    lexicon = load_words(os.path.join(d5d, "backref_lexicon.txt"))
    tmpl = [re.compile(t) for t in load_words(os.path.join(d5d, "template_patterns.txt"))
            if not t.startswith("#")]
    names, _ = mod.load_personas(os.path.join(REPO, "code", "config", "personas.json"))
    res = mod.compute(msgs, lexicon, tmpl, names, extra)

    f1 = res["F-1_chatter"]
    n_msg = res["L_wording"]["denominators"]["per_message"]
    tt = set(task_tags)
    by_tag = by_rx = by_both = 0
    for m in msgs:
        t = bool(set(m["tags"]) & tt)
        r = bool(TRANS_RX.search(m["body"]))
        if t and r:
            by_both += 1
        elif t:
            by_tag += 1
        elif r:
            by_rx += 1
    func = f1["functional_msgs"]
    assert by_tag + by_rx + by_both == func, (arm, by_tag, by_rx, by_both, func)

    num = n_msg - func
    ci = mod.wilson_ci(num, n_msg, WILSON_Z)  # z 取自 tools/d5/f8_lexicon.json::thresholds
    tag_counter = Counter(t for m in msgs for t in (set(m["tags"]) & tt))
    return {
        "arm": arm,
        "log_path": os.path.relpath(os.path.abspath(log), REPO),
        "log_sha256": sha256_file(log),
        "log_lines": len(recs),
        "n_msg": n_msg,
        "units": {"n_msg_source": "d5 L_wording.denominators.per_message = len(extract_messages(recs))"},
        "functional_msgs": func,
        "chatter_numerator": num,
        "nonfunctional_chatter_rate": f1["nonfunctional_chatter_rate"],
        "wilson95": ci,
        "decomposition": {
            "func_by_tag_only": by_tag,
            "func_by_trans_rx_only": by_rx,
            "func_by_tag_and_rx": by_both,
            "tag_hit_msgs": by_tag + by_both,
            "trans_rx_hit_msgs": by_rx + by_both,
            "tag_hits_by_tag": dict(sorted(tag_counter.items())),
        },
        "cross_check": {
            "d5_F1_rate": res["F-1_chatter"]["nonfunctional_chatter_rate"],
            "d5_L3": res["L_wording"]["L-3_paren_block_any"],
            "d5_n_messages_meta": res["meta"]["n_messages"],
            "n_threads": res["meta"]["n_threads"],
        },
        "ruler": {
            "script": "tools/d5/dialogue_metrics.py",
            "script_sha256": sha256_file(D5),
            "task_tags_sha256": sha256_file(os.path.join(d5d, "task_tags.txt")),
            "rule": f1["rule"],
        },
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", default=[],
                    help="NAME=path/to/run.jsonl，可重复")
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args(argv)
    mod = load_module()
    arms = []
    for spec in a.arm:
        name, _, log = spec.partition("=")
        arms.append(arm_reading(mod, name, log))
    out = {
        "schema_version": "f1-readings/1.0",
        "caliber": "F-1 非功能性闲聊占比（R4-life-texture.md:33 定义，实现 = tools/d5/dialogue_metrics.py::compute()::F-1_chatter）",
        "note": "任务卡原文写「嗟啥」为笔误，口径以 R4 定义为准（= 非功能性闲聊/废话占比）",
        "arms": arms,
    }
    with open(a.out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")
    print("wrote", a.out_json, "arms:", [x["arm"] for x in arms])
    return 0


if __name__ == "__main__":
    sys.exit(main())
