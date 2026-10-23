#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D2.1-A2 诊断：**"对未回对端发起"在现有日志里到底占多少**

目的：在写 A2 预登记、花 50 分钟跑批之前，先用量产日志量出 A2 会拦掉的量。
若极低（比如 <2%），A2 机制再正确也无效果可测 ⇒ 直接判"不值得跑"。

口径（全部并列输出，名字带后缀，遵 runbook §3.113）：
- `n_init_with_to`      : `turn_index==0` 且 `to` 非空的发送数（= 可被 A2 检查的发起）
- `n_init_owed_any`     : 其中「**对方**曾向本人发过消息，且本人此后未回过对方」的条数
- `init_owed_rate_any`  : 上面两者之比
- `n_init_owed_thread`  : 严格口径：上述"未回"还要求那条未回的消息**在同一个 thread 内**（A2 只按对端判，不按 thread，故此列仅作对照）
- `n_init_owed_last_only`: 弱口径：只要求"对方最后一条消息晚于本人最后一条发给对方的消息"

用法：
  python3 tools/d21/a2_incidence.py --log A=path1 --log B=path2 [--out-json ...]
"""
import argparse, json, sys
from collections import defaultdict

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")


def load(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("type") not in MSG_TYPES:
                continue
            pl = e.get("payload") or {}
            a = pl.get("from")
            b = pl.get("to")
            ts = e.get("mono_ts")
            if a is None or not isinstance(ts, (int, float)):
                continue
            rows.append({
                "ts": ts, "frm": a, "to": b,
                "thread": pl.get("thread_id"),
                "turn": pl.get("turn_index"),
                "uid": pl.get("msg_uid"),
            })
    rows.sort(key=lambda r: (r["ts"], str(r["uid"])))
    return rows


def analyse(rows):
    # 每对 (x, y)：x 发给 y 的所有 ts 与 y 发给 x 的所有 ts
    sent = defaultdict(list)      # (frm,to) -> [(ts, thread)]
    for r in rows:
        if r["to"]:
            sent[(r["frm"], r["to"])].append((r["ts"], r["thread"]))

    n_init = n_owed_any = n_owed_thread = n_owed_last_only = 0
    for r in rows:
        if r["turn"] != 0 or not r["to"]:
            continue                      # 只看"发起"
        n_init += 1
        A, B, t0 = r["frm"], r["to"], r["ts"]
        back = sent.get((B, A), [])       # B → A
        fwd = sent.get((A, B), [])        # A → B
        prior_back = [(ts, th) for ts, th in back if ts < t0]
        if not prior_back:
            continue                      # B 从未在此之前找过 A ⇒ 没有"欠回复"
        # 强口径：存在某条 B→A（ts<t0），A 在 (ts, t0) 之间没有回过 B
        owed = any(not any(ts < ft < t0 for ft, _ in fwd) for ts, _ in prior_back)
        if owed:
            n_owed_any += 1
            if any(th == r["thread"] for _, th in prior_back):
                n_owed_thread += 1
        # 弱口径：B 的最后一条 > A 的最后一条（且都 < t0）
        last_back = max(ts for ts, _ in prior_back)
        prior_fwd = [ft for ft, _ in fwd if ft < t0]
        if not prior_fwd or last_back > max(prior_fwd):
            n_owed_last_only += 1

    def pct(a, b):
        return round(100.0 * a / b, 2) if b else None

    return {
        "n_msgs_total": len(rows),
        "n_init_with_to": n_init,
        "n_init_owed_any": n_owed_any,
        "init_owed_rate_any": pct(n_owed_any, n_init),
        "n_init_owed_thread": n_owed_thread,
        "init_owed_rate_thread": pct(n_owed_thread, n_init),
        "n_init_owed_last_only": n_owed_last_only,
        "init_owed_rate_last_only": pct(n_owed_last_only, n_init),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", action="append", required=True, help="ARM=path")
    ap.add_argument("--out-json", default=None)
    a = ap.parse_args()
    out = {}
    for spec in a.log:
        arm, _, path = spec.partition("=")
        err = None
        try:
            out[arm] = analyse(load(path))
        except FileNotFoundError:
            out[arm] = {"error": "missing file"}
            err = True
        out[arm]["log"] = path
        print(f"[{arm}] {json.dumps(out[arm], ensure_ascii=False)}", file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    if a.out_json:
        with open(a.out_json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
