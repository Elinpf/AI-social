#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F-4 / F-4b 事件级证据枚举器（词表层）。

定位：**不是新的指标定义**，而是把 `tools/d5/dialogue_metrics.py` 已经算出的
F-4（张力→修复闭环数 / 张力事件数）与 F-4b（张力→修复的间隔条数）**逐条展开**，
让每个分子都能回溯到具体消息事件与日志行号；并**断言**本脚本的枚举计数与
`dialogue_metrics.py` 的输出完全一致，不一致即非零退出（防止两套口径悄悄漂移）。

口径来源（与 dialogue_metrics.py 严格同源，逐行对照实现）：
  * 线程分组 = compute() 内的 mixed_key：`thread_id` 优先；否则 dm 按无序对、
    public 按当日合流、group 按 (day, place)；
  * 极性 polarity(body) = 正/负词表命中数比较（子串包含，不做分词）；
  * 张力 = 相邻两句极性异号，或当前句极性为负；
  * 闭环 = 张力句之后 8 条内（j ∈ [i+1, i+8]）同线程出现修复词，取最近一次命中；
  * F-4b lag = 命中的修复句与张力句之间的消息条数（j - i）。

用法：
  python3 tools/d5/f4_repair_evidence.py \
    --log v2/evidence/<批目录>/run.jsonl \
    --metrics-json v2/evidence/<指标文件>.json \
    --out-json v2/evidence/<输出>.json --out-md v2/evidence/<输出>.md

退出码：0 成功且交叉校验通过；2 输入不可用；4 交叉校验不一致（口径漂移）。
"""
import argparse
import hashlib
import json
import os
import statistics as st
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dialogue_metrics as dm  # noqa: E402  复用同一套解析，避免第二套解析口径

DEFAULT_EMOTION = os.path.join(HERE, "emotion_lexicon.txt")
DEFAULT_REPAIR = os.path.join(HERE, "repair_lexicon.txt")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_words(path):
    if not os.path.exists(path):
        return []
    return [ln.strip() for ln in open(path, encoding="utf-8")
            if ln.strip() and not ln.strip().startswith("#")]


def load_emotion(path):
    emo = {}
    for ln in load_words(path):
        parts = ln.split()
        if len(parts) >= 2:
            try:
                emo[" ".join(parts[1:])] = int(parts[0])
            except ValueError:
                continue
    return emo


def mixed_key(m):
    """与 dialogue_metrics.compute() 内 mixed_key 逐行一致。"""
    if m.get("thread_id"):
        return "m:T|%s" % m["thread_id"]
    if m["channel"] == "dm":
        k = "-".join(sorted({str(m["from"]), str(m["to"])}))
    elif m["channel"] == "public":
        k = "-"
    else:
        k = str(m.get("place") or "-")
    return "m:%s|%s|%s" % (m["day"], m["channel"], k)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--metrics-json", default=None,
                    help="dialogue_metrics.py 的 out-json；给出则做交叉校验（不一致 rc=4）")
    ap.add_argument("--emotion", default=DEFAULT_EMOTION)
    ap.add_argument("--repair", default=DEFAULT_REPAIR)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--window", type=int, default=8, help="闭环判定窗口（默认 8，与 d5 一致）")
    args = ap.parse_args(argv)

    if not os.path.exists(args.log):
        print("[FAIL] log 不存在: %s" % args.log, file=sys.stderr)
        return 2

    emo = load_emotion(args.emotion)
    repair = load_words(args.repair)
    recs, info = dm.read_run(args.log)
    msgs = dm.extract_messages(recs)
    if not msgs:
        print("[FAIL] 日志中没有 MSG_* 消息事件", file=sys.stderr)
        return 2
    chain = dm.check_chain(recs)

    # seq -> 原始日志行号（让每个事件都能回到原文行）
    seq2line = {}
    with open(args.log, encoding="utf-8") as f:
        for ln_no, ln in enumerate(f, 1):
            ln = ln.strip()
            if not ln:
                continue
            try:
                o = json.loads(ln)
            except Exception:  # noqa: BLE001
                continue
            if o.get("type") in dm.MSG_TYPES and o.get("seq") is not None:
                seq2line[o["seq"]] = ln_no

    def polarity(body):
        pos = sum(1 for w, p in emo.items() if p > 0 and w in body)
        neg = sum(1 for w, p in emo.items() if p < 0 and w in body)
        if pos > neg:
            return 1
        if neg > pos:
            return -1
        return 0

    threads = defaultdict(list)
    for m in msgs:
        threads[mixed_key(m)].append(m)
    for k in threads:
        threads[k].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                       m["seq"] if m["seq"] is not None else -1))

    events = []
    lags = []
    for key in sorted(threads):
        th = threads[key]
        for i in range(1, len(th)):
            p_prev = polarity(th[i - 1]["body"])
            p_cur = polarity(th[i]["body"])
            conflict = (p_prev * p_cur < 0) or (p_cur < 0)
            if not conflict:
                continue
            hit = None
            for j in range(i + 1, min(i + 1 + args.window, len(th))):
                words = [w for w in repair if w in th[j]["body"]]
                if words:
                    hit = {"j": j, "lag": j - i, "words": words}
                    break
            ev = {
                "thread": key,
                "channel": th[i]["channel"],
                "idx_in_thread": i,
                "seq": th[i]["seq"],
                "msg_uid": th[i].get("msg_uid"),
                "msg_id": th[i].get("msg_id"),
                "line": seq2line.get(th[i]["seq"]),
                "round": th[i]["round"],
                "from": th[i]["from"], "to": th[i]["to"],
                "body": th[i]["body"],
                "pol_prev": p_prev, "pol_cur": p_cur,
                "trigger": ("异号" if p_prev * p_cur < 0 else "当前句为负"),
                "closed": hit is not None,
                "repair_seq": th[hit["j"]]["seq"] if hit else None,
                "repair_msg_uid": th[hit["j"]].get("msg_uid") if hit else None,
                "repair_line": seq2line.get(th[hit["j"]]["seq"]) if hit else None,
                "repair_words": hit["words"] if hit else [],
                "lag": hit["lag"] if hit else None,
                "repair_body": th[hit["j"]]["body"] if hit else None,
            }
            events.append(ev)
            if hit:
                lags.append(hit["lag"])

    tension = len(events)
    closed = len(lags)
    res = {
        "schema_version": "f4-evidence/1.0",
        "generated_at": __import__("datetime").datetime.now().astimezone().isoformat(),
        "layer": "词表层（word-lexicon layer）——与 dialogue_metrics.py 同源同规则",
        "rule": {
            "grouping": "mixed_key: thread_id 优先；dm 无序对 / public 当日合流 / group (day,place)",
            "polarity": "正负词表命中数比较（子串包含，不分词）",
            "tension": "相邻两句极性异号 或 当前句极性为负",
            "closed_loop": "张力句之后 %d 条内同线程出现修复词，取最近一次命中" % args.window,
            "f4b": "lag = 修复句与张力句之间的消息条数（j-i）",
        },
        "inputs": {
            "log": os.path.abspath(args.log),
            "log_sha256": sha256_file(args.log),
            "script": os.path.abspath(__file__),
            "script_sha256": sha256_file(__file__),
            "emotion_lexicon": os.path.abspath(args.emotion),
            "emotion_sha256": sha256_file(args.emotion),
            "repair_lexicon": os.path.abspath(args.repair),
            "repair_sha256": sha256_file(args.repair),
            "metrics_json": os.path.abspath(args.metrics_json) if args.metrics_json else None,
            "bad_lines": info["n_bad"],
            "chain": chain,
        },
        "F-4_tension_repair": {
            "numerator_repaired": closed,
            "denominator_tension_events": tension,
            "ratio": (round(closed / tension, 6) if tension else None),
            "grade": "probe" if tension < 30 else "reportable",
            "grade_rule": "分母<30 只报事件数+分母，标 probe，不做百分比结论",
        },
        "F-4b_repair_lag": {
            "denominator_repaired_events": closed,
            "mean_lag_msgs": (round(sum(lags) / len(lags), 6) if lags else None),
            "median_lag_msgs": (st.median(lags) if lags else None),
            "min_lag": (min(lags) if lags else None),
            "max_lag": (max(lags) if lags else None),
            "lag_distribution": dict(sorted(Counter(lags).items())),
            "note": ("无闭环样本 ⇒ 时滞不可计算（null）；不得补 0、不得估" if not lags else ""),
        },
        "channels": {
            ch: {
                "tension_events": sum(1 for e in events if e["channel"] == ch),
                "repaired": sum(1 for e in events if e["channel"] == ch and e["closed"]),
            } for ch in ("dm", "public", "group")
        },
        "threads_with_tension": len({e["thread"] for e in events}),
        "events": events,
        "n_messages": len(msgs),
    }

    # ---- 交叉校验：与 dialogue_metrics.py 的聚合读数必须完全一致
    xcheck = {"checked": False}
    rc = 0
    if args.metrics_json:
        if not os.path.exists(args.metrics_json):
            print("[FAIL] metrics-json 不存在: %s" % args.metrics_json, file=sys.stderr)
            return 2
        mref = json.load(open(args.metrics_json, encoding="utf-8"))
        ref = mref.get("F-4_tension_repair") or {}
        same_tension = ref.get("tension_events") == tension
        same_closed = ref.get("repaired") == closed
        same_ratio = (ref.get("closed_loop_rate") is None and res["F-4_tension_repair"]["ratio"] is None) or \
                     (ref.get("closed_loop_rate") is not None and abs(float(ref["closed_loop_rate"]) -
                      float(res["F-4_tension_repair"]["ratio"])) < 1e-6)
        xcheck = {
            "checked": True,
            "metrics_json_sha256": sha256_file(args.metrics_json),
            "ref": {"tension_events": ref.get("tension_events"), "repaired": ref.get("repaired"),
                    "closed_loop_rate": ref.get("closed_loop_rate"),
                    "mean_lag_msgs": ref.get("mean_lag_msgs")},
            "match": {"tension_events": same_tension, "repaired": same_closed,
                      "closed_loop_rate": same_ratio,
                      "mean_lag_msgs": ref.get("mean_lag_msgs") == res["F-4b_repair_lag"]["mean_lag_msgs"]},
        }
        xcheck["ok"] = all(xcheck["match"].values())
        if not xcheck["ok"]:
            rc = 4
    res["cross_check"] = xcheck

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")

    f4 = res["F-4_tension_repair"]
    f4b = res["F-4b_repair_lag"]
    lines = []
    lines.append("# F-4 / F-4b 事件级证据（%s）" % res["layer"])
    lines.append("")
    lines.append("- 生成时刻：`%s`" % res["generated_at"])
    lines.append("- 日志：`%s`" % res["inputs"]["log"])
    lines.append("- 日志 sha256：`%s`" % res["inputs"]["log_sha256"])
    lines.append("- 脚本 sha256：`%s`" % res["inputs"]["script_sha256"])
    lines.append("- 修复词表 sha256：`%s`" % res["inputs"]["repair_sha256"])
    lines.append("- 情绪词表 sha256：`%s`" % res["inputs"]["emotion_sha256"])
    lines.append("- 消息数：%d；含张力事件的线程数：%d；坏行：%d；hash 链：seq_dense=%s / links_ok=%s"
                 % (res["n_messages"], res["threads_with_tension"], res["inputs"]["bad_lines"],
                    chain["seq_dense"], chain["hash_links_ok"]))
    lines.append("")
    _uid_have = sum(1 for m in msgs if m.get("msg_uid"))
    lines.append("- `msg_uid` 覆盖：%d / %d 条消息%s" % (
        _uid_have, len(msgs),
        "" if _uid_have else "（本日志为 legacy 线程结构，无 msg_uid；定位请用 `seq` + 日志行号）"))
    lines.append("")
    lines.append("## 聚合读数（分子/分母写全）")
    lines.append("")
    lines.append("| 指标 | 分子 | 分母 | 比率 | 判级 |")
    lines.append("|---|---|---|---|---|")
    lines.append("| F-4 修复闭环 | %d | %d | %s | **%s** |"
                 % (f4["numerator_repaired"], f4["denominator_tension_events"],
                    ("—（分母<30，不做百分比结论）" if f4["grade"] == "probe" else f4["ratio"]), f4["grade"]))
    lines.append("| F-4b 修复时滞 | 分母=%d（闭环事件） | — | mean=%s / median=%s | %s |"
                 % (f4b["denominator_repaired_events"], f4b["mean_lag_msgs"],
                    f4b["median_lag_msgs"], "**probe**" if f4["grade"] == "probe" else "reportable"))
    if f4b["note"]:
        lines.append("")
        lines.append("> F-4b：%s" % f4b["note"])
    lines.append("")
    lines.append("## 分渠道")
    lines.append("")
    lines.append("| 渠道 | 张力事件 | 已闭环 |")
    lines.append("|---|---|---|")
    for ch, v in res["channels"].items():
        lines.append("| %s | %d | %d |" % (ch, v["tension_events"], v["repaired"]))
    lines.append("")
    lines.append("## 交叉校验（与 dialogue_metrics.py 同输入比对）")
    lines.append("")
    if xcheck.get("checked"):
        lines.append("- 参照文件 sha256：`%s`" % xcheck["metrics_json_sha256"])
        lines.append("- 一致：**%s**（tension_events=%s, repaired=%s, closed_loop_rate=%s, mean_lag_msgs=%s）"
                     % (xcheck["ok"], xcheck["match"]["tension_events"], xcheck["match"]["repaired"],
                        xcheck["match"]["closed_loop_rate"], xcheck["match"]["mean_lag_msgs"]))
        lines.append("- 不一致即 rc=4 且本文件不应被引用。")
    else:
        lines.append("- 未提供 `--metrics-json`，本次**未做**交叉校验（引用时须补做）。")
    lines.append("")
    lines.append("## 逐事件明细（全部张力事件，含已闭环/未闭环）")
    lines.append("")
    lines.append("| # | 线程 | msg_uid | 渠道 | 轮次 | 触发消息 seq | 行号 | 触发者 | 极性(前→本) | 触发原因 | 闭环 | 修复词 | 间隔 lag | 修复 msg_uid | 修复 seq | 修复行号 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for n, e in enumerate(events, 1):
        lines.append("| %d | `%s` | `%s` | %s | %s | %s | %s | %s | %d→%d | %s | %s | %s | %s | %s | %s | %s |"
                     % (n, e["thread"], e["msg_uid"] or "—", e["channel"], e["round"], e["seq"], e["line"], e["from"],
                        e["pol_prev"], e["pol_cur"], e["trigger"],
                        "是" if e["closed"] else "**否**",
                        "/".join(e["repair_words"]) if e["repair_words"] else "—",
                        e["lag"] if e["lag"] is not None else "—",
                        e["repair_msg_uid"] or "—",
                        e["repair_seq"] if e["repair_seq"] is not None else "—",
                        e["repair_line"] if e["repair_line"] is not None else "—"))
    lines.append("")
    lines.append("## 原始正文（逐事件，便于人工复核词表判定）")
    lines.append("")
    for n, e in enumerate(events, 1):
        lines.append("**#%d** `seq=%s`/`msg_uid=%s` L%s `%s` %s→%s（%s）：%s"
                     % (n, e["seq"], e["msg_uid"] or "—", e["line"], e["thread"], e["from"], e["to"],
                        e["trigger"], e["body"]))
        if e["closed"]:
            lines.append("  - 闭环：`seq=%s`/`msg_uid=%s` L%s lag=%s 命中词=%s：%s"
                         % (e["repair_seq"], e["repair_msg_uid"] or "—", e["repair_line"], e["lag"],
                            "/".join(e["repair_words"]), e["repair_body"]))
        else:
            lines.append("  - 未闭环：其后 %d 条内无修复词" % args.window)
        lines.append("")
    open(args.out_md, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    print(json.dumps({
        "F-4": "分子 %d / 分母 %d = %s (%s)" % (closed, tension, f4["ratio"], f4["grade"]),
        "F-4b": "闭环样本 %d, mean_lag=%s" % (closed, f4b["mean_lag_msgs"]),
        "cross_check": xcheck.get("ok") if xcheck.get("checked") else "not-checked",
        "out_json": args.out_json, "out_md": args.out_md,
    }, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    sys.exit(main())
