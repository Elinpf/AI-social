#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-F 旁证：同一对 agent 跨轮相邻消息对（给 T9「像不像在对话」做样例材料）

纯读 run.jsonl，不联网、不调 LLM、不改任何引擎代码。

配对规则（写死，避免事后挑样本）：
- 只看 DM（`MSG_DM`，有明确 `from`/`to`），按 `(from,to)` 归一化为无序 pair；
- 对每个 pair，取**相邻两轮**（r, r+1）各自在该 pair 上的**第一条**DM，组成一对；
- 同一 pair 在同一轮内若有多条，只取 seq 最小者（避免自选）。

「是否互相回应」用两个**机械**代理量（不做好坏判断，只供人工抽样）：
- `jaccard_bigram` = 两条 body 的 char-bigram Jaccard（与 F-2_content_drift 同口径思路）
- `shared_tokens` = 两条 body 共享的 ≥2 字内容片段数（去掉标点与常见虚词）
- 判词：`shared_tokens==0 且 jaccard<0.02` ⇒ 「无词面回应」；`shared_tokens>=2 或 jaccard>=0.10` ⇒ 「有词面回应」；其余「弱」

用法：
    python3 v2/evidence/d12f_adjacent_pairs.py \
        --run-jsonl <run.jsonl> --out-md v2/evidence/d12f_adjacent_dialogue_pairs.md [--limit 40]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict

PUNCT = re.compile(r"[\s,，。！？!?、；;:：\"'“”‘’…—\-\.\(\)\[\]【】（）]")
STOP = set("的了是我你他她它们在有和就都不也这那个一上个说要把被很还又再对给跟吧呢啊吗么着过来去得地")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def norm(s: str) -> str:
    return PUNCT.sub("", s or "")


def bigrams(t: str) -> set:
    return {t[i:i + 2] for i in range(len(t) - 1)}


def tokens(t: str) -> set:
    """粗粒度「内容片段」：去虚词后的连续 2 字窗口。"""
    out = set()
    for i in range(len(t) - 1):
        g = t[i:i + 2]
        if any(c in STOP for c in g):
            continue
        out.add(g)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-jsonl", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--seals", type=int, default=None)
    ap.add_argument("--snapshot-at", default=None)
    ap.add_argument("--final", action="store_true", help="终态版（partial=false）")
    ap.add_argument("--partial", action="store_true", help="期中快照（与 --final 二选一；默认即 partial）")
    a = ap.parse_args(argv)

    dms = []
    seals = 0
    max_round = None
    for line in open(a.run_jsonl, encoding="utf-8"):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") == "TURN_SEAL":
            seals += 1
            continue
        if e.get("type") != "MSG_DM":
            continue
        pl = e.get("payload") or {}
        fr, to = pl.get("from"), pl.get("to")
        if not fr or not to:
            continue
        body = pl.get("body") or ""
        dms.append({"seq": e.get("seq"), "round": e.get("round"), "from": fr, "to": to,
                    "pair": tuple(sorted((fr, to))), "body": body, "thread": pl.get("thread_id")})
        max_round = e.get("round") if max_round is None else max(max_round, e.get("round") or 0)

    # pair+round -> 第一条 DM
    first = {}
    for m in sorted(dms, key=lambda x: (x["round"], x["seq"])):
        k = (m["pair"], m["round"])
        if k not in first:
            first[k] = m

    pairs = []
    for (pair, r), m1 in sorted(first.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        m2 = first.get((pair, r + 1))
        if not m2:
            continue
        t1, t2 = norm(m1["body"]), norm(m2["body"])
        b1, b2 = bigrams(t1), bigrams(t2)
        jac = (len(b1 & b2) / len(b1 | b2)) if (b1 | b2) else 0.0
        shared = len(tokens(t1) & tokens(t2))
        if shared == 0 and jac < 0.02:
            verdict = "无词面回应"
        elif shared >= 2 or jac >= 0.10:
            verdict = "有词面回应"
        else:
            verdict = "弱"
        pairs.append({"pair": pair, "r1": r, "r2": r + 1,
                      "from1": m1["from"], "to1": m1["to"], "from2": m2["from"], "to2": m2["to"],
                      "body1": m1["body"], "body2": m2["body"],
                      "thread1": m1["thread"], "thread2": m2["thread"],
                      "jaccard": round(jac, 4), "shared_tokens": shared, "verdict": verdict})

    total = len(pairs)
    show = pairs[: a.limit]
    cnt = defaultdict(int)
    for p in pairs:
        cnt[p["verdict"]] += 1

    L = []
    L.append("# D12-F 旁证：同一对 agent 跨轮相邻消息对（给 T9「像不像在对话」）\n")
    L.append("> %s｜seals %s/60｜采集时刻 **%s**（由 wrapper 的 `date -Iseconds` 回显，非手写）" % (
        ("🟢 **终态（partial=false）**" if a.final else "**PARTIAL（跑批进行中）**"), a.seals or seals, a.snapshot_at))
    L.append("> 读数人：run-warden｜生成脚本：`v2/evidence/d12f_adjacent_pairs.py`（纯标准库，纯读日志）")
    L.append("> 源日志：`%s`（sha256 `%s`）" % (a.run_jsonl, sha256_file(a.run_jsonl)))
    L.append("")
    L.append("## 0. 配对规则与汇总\n")
    L.append("配对规则（写死，非按需挑选）：只看 `MSG_DM`；按 `(from,to)` 归一化为无序 pair；"
             "同一 pair 在轮 r 与 r+1 各取**seq 最小**的一条组成一对；同轮多条不参与。")
    L.append("")
    L.append("| 项 | 读数 |")
    L.append("|---|---|")
    L.append("| DM 消息总数 | %d |" % len(dms))
    L.append("| 可配对（pair, r→r+1）实例数 | **%d** |" % total)
    for k in ("有词面回应", "弱", "无词面回应"):
        L.append("| %s | %d（%.1f%%） |" % (k, cnt.get(k, 0), 100.0 * cnt.get(k, 0) / total if total else 0))
    L.append("")
    L.append("> 判词是**机械代理量**，只用于抽样与排序，**不是**「对话质量」结论："
             "`jaccard_bigram` = 两条 body 的 char-bigram Jaccard；"
             "`shared_tokens` = 去掉常见虚词后共享的 2 字片段数。"
             "`shared_tokens==0 且 jaccard<0.02` ⇒ 无词面回应；`shared_tokens>=2 或 jaccard>=0.10` ⇒ 有词面回应；其余为弱。")
    L.append("")
    L.append("## 1. 样例（前 %d 对；全量用文末命令重算）\n" % len(show))
    L.append("| # | pair | 轮次 | 前轮发言 → 后轮发言 | 前轮 body（前 80 字） | 后轮 body（前 80 字） | jaccard | shared_tokens | 判词 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for i, p in enumerate(show, 1):
        L.append("| %d | %s/%s | r%s→r%s | %s→%s / %s→%s | %s | %s | %.4f | %d | %s |" % (
            i, p["pair"][0], p["pair"][1], p["r1"], p["r2"],
            p["from1"], p["to1"], p["from2"], p["to2"],
            p["body1"].replace("|", "/")[:80], p["body2"].replace("|", "/")[:80],
            p["jaccard"], p["shared_tokens"], p["verdict"]))
    L.append("")
    L.append("## 2. 仅供 T9 使用的读法提示（不是结论）\n")
    L.append("1. 本表只回答「**相邻两轮里，同一对 agent 说的两句话有没有词面上的接力**」，"
             "不回答「内容是否推进」「情绪是否延续」——那需要人工读或 judge。")
    L.append("2. 与 `d12f_adjacent_same_prompt.md` 互补：那份证明「**输入**两次相同」，"
             "这份看「**输出**有没有接上对方」。")
    L.append("3. 线程 id 通常每轮新开（`…-24` → `…-25`），因此「同一个 thread 内多轮」的样本本来就不多；"
             "若要区分「同线程续聊」与「跨轮重开」，请按 `thread_id` 分组再看。")
    L.append("")
    L.append("## 3. 复算命令\n")
    L.append("```bash")
    L.append("cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment")
    L.append("python3 v2/evidence/d12f_adjacent_pairs.py \\")
    L.append("  --run-jsonl .worktrees/d12f-diverse/v2/evidence/run_d12f_diverse_n16r60_seed42/run.jsonl \\")
    L.append("  --out-md /tmp/d12f_adjacent_dialogue_pairs.md --limit 40")
    L.append("```")

    with open(a.out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(json.dumps({"dm_msgs": len(dms), "pairable": total, "verdicts": dict(cnt)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
