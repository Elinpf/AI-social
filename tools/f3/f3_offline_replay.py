#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""f3_offline_replay.py —— F-3 情绪呼应：**零成本离线回放**（不改日志、不调 LLM、不跑批）。

回答的问题
----------
「在**已经存在的** run.jsonl 语料上，`life/emotion_echo.py` 的确定性判定器，
对每一次"接情绪的机会"到底会不会产出呼应？」——这是机制**落点覆盖率**，
与 `v2/evidence/f3_audit_echo.py` 的内容层判据（**冻结主口径**）是两件事：

  * 内容层（f3_audit_echo.py）：**事后**数「上一句有极性、下一句接住了没有」——
    受 LLM 措辞影响，任何改码都不能改写老日志的结论；
  * 机制层（本脚本）：**事前**回放判定器，数「判定器给不给提示」——
    纯函数、确定性，改码前后可在**同一份语料**上各跑一次得到可比的 before/after。

因此两者**不可互相替代**：一个说「接住了几次」，一个说「给了几次机会去接」。

口径（与冻结主口径一致的部分）
------------------------------
* 机会（分母）定义**逐字沿用** `v2/evidence/f3_audit_echo.py`：
  同线程相邻对，且 `polarity(prev.body) != 0`；`cur_is_reply = cur.reply_to is not None`。
  极性函数同样从 `tools/d5/emotion_lexicon.txt` + `tools/d5/dialogue_metrics.py` 派生，
  **不另写一份词表**。
* 机制侧判定只调用 `life.emotion_echo.detect()/plan()`，`:mood` 取**上一句** `payload.ctx.mood`
  （发送方生成时按自身 needs 算出的确定性标签），`:partner_text` 取**上一句** `payload.body`
  ——与 `life/agent.py::_emotion_echo(ctx_in, partner_body, partner)` 的入参来源一致。

回放强制 `enabled=True` 的原因
------------------------------
离线回放要测的是「**机制在开臂下会落多少**」，而不是「这条历史日志的作者当时开没开」。
因此用 `emotion_echo.set_override({**load_params(), "enabled": True})` 强制打开，
并在输出里写明 `forced_enabled=true`。**这只是探针**，不改 config/、不影响任何既有日志。

用法（仓库根）
--------------
  python3 tools/f3/f3_offline_replay.py \
      --arm emooff=v2/evidence/emo-off-20261030/run.jsonl \
      --arm v0=v2/evidence/run_d2_before_n16_seed42/run.jsonl \
      --out-json v2/evidence/r38_f3/f3_offline_replay.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter, defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CODE = os.path.join(REPO, "code")
if CODE not in sys.path:
    sys.path.insert(0, CODE)

MSG_PREFIX = ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


d5 = _load("dialogue_metrics_f3replay", os.path.join(REPO, "tools/d5/dialogue_metrics.py"))
f4a = _load("f4_anchor_recompute_f3replay", os.path.join(REPO, "tools/f4/f4_anchor_recompute.py"))

from life import emotion_echo as EE  # noqa: E402  （仓库内模块，需先有 code/ 在 sys.path）


def _event_type(rec):
    for k in ("type", "event", "kind_of"):
        v = rec.get(k)
        if isinstance(v, str):
            return v
    return ""


def load_messages(path):
    """读 run.jsonl → (msgs, bad)。

    `msgs` 直接用 `d5.extract_messages(recs)`（**与冻结主口径同一个抽取器**，
    保证 `f4a.mixed_key()` 的分组/排序逐字节一致）；只额外按 `seq` 补 `ctx_mood`
    （`extract_messages` 不带 ctx，而 F-3 的处境情绪来源正是 `payload.ctx.mood`）。
    """
    recs, bad = d5.read_run(path)
    mood_by_seq = {}
    for r in recs:
        if not _event_type(r).startswith(MSG_PREFIX):
            continue
        p = r.get("payload")
        if not isinstance(p, dict):
            continue
        ctx = p.get("ctx") if isinstance(p.get("ctx"), dict) else {}
        if "mood" in ctx:
            mood_by_seq[r.get("seq")] = ctx.get("mood")
    msgs = d5.extract_messages(recs)
    for m in msgs:
        m["ctx_mood"] = mood_by_seq.get(m.get("seq"))
    return msgs, bad


def replay_arm(label, rel_path, params):
    path = rel_path if os.path.isabs(rel_path) else os.path.join(REPO, rel_path)
    if not os.path.isfile(path):
        return {"label": label, "log": rel_path, "exists": False}

    emo = f4a.load_emotion(os.path.join(REPO, "tools/d5/emotion_lexicon.txt"))

    def polarity(body):  # 逐行复制 dialogue_metrics.py:635-642（与 f3_audit_echo.py 同源）
        pos = sum(1 for w, p in emo.items() if p > 0 and w in body)
        neg = sum(1 for w, p in emo.items() if p < 0 and w in body)
        if pos > neg:
            return 1
        if neg > pos:
            return -1
        return 0

    msgs, bad = load_messages(path)
    threads = defaultdict(list)
    for m in msgs:
        threads[f4a.mixed_key(m)].append(m)   # 分组键与冻结主口径同一实现
    for k in threads:
        threads[k].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                      m["seq"] if m["seq"] is not None else -1))

    opportunities = []
    all_replies = []
    for key in sorted(threads, key=str):
        th = threads[key]
        for i in range(1, len(th)):
            prev, cur = th[i - 1], th[i]
            p_prev = polarity(prev["body"])
            p_cur = polarity(cur["body"])
            row = {
                "thread": key, "prev_seq": prev["seq"], "cur_seq": cur["seq"],
                "round": cur.get("round"), "cur_is_reply": cur.get("reply_to") is not None,
                "p_prev": p_prev, "p_cur": p_cur,
                "prev_mood": prev.get("ctx_mood"), "cur_mood": cur.get("ctx_mood"),
                "prev_body": prev["body"], "cur_body": cur["body"],
                "detect": EE.detect(prev.get("ctx_mood"), prev["body"], params),
                "plan": EE.plan(prev.get("ctx_mood"), prev["body"], params),
            }
            if cur.get("reply_to") is not None:
                all_replies.append(row)
            if p_prev != 0:
                opportunities.append(row)

    def tally(rows):
        planned = [r for r in rows if r["plan"] is not None]
        src = Counter((r["plan"] or {}).get("source") for r in planned)
        kind = Counter((r["plan"] or {}).get("kind") for r in planned)
        by_sign = Counter(str((r["plan"] or {}).get("sign")) for r in planned)
        return {
            "n": len(rows),
            "planned": len(planned),
            "rate": round(len(planned) / len(rows), 6) if rows else None,
            "by_source": dict(src),
            "by_kind": dict(kind),
            "by_sign": dict(by_sign),
        }

    return {
        "label": label,
        "log": os.path.relpath(path, REPO),
        "log_sha8": f4a.sha8(path),
        "exists": True,
        "n_messages": len(msgs),
        "n_threads": len(threads),
        "bad_lines": bad["n_bad"],
        "n_reply_messages": len(all_replies),
        "opportunities": tally(opportunities),
        "all_reply_messages": tally(all_replies),
        "opportunity_rows": [
            {k: r[k] for k in ("thread", "prev_seq", "cur_seq", "round", "p_prev", "p_cur",
                               "prev_mood", "prev_body", "cur_body", "detect")} | {
                "planned": r["plan"] is not None,
                "plan": r["plan"],
            }
            for r in opportunities
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", default=[], metavar="LABEL=PATH")
    ap.add_argument("--out-json")
    args = ap.parse_args()
    if not args.arm:
        raise SystemExit("[FAIL] 至少给一个 --arm LABEL=PATH")

    base = EE.load_params()
    params = dict(base)
    params["enabled"] = True          # 探针：离线回放强制打开（见 docstring）
    EE.set_override(params)

    arms = [replay_arm(*s.partition("=")[::2], params) for s in args.arm]
    payload = {
        "schema": "f3-offline-replay/1",
        "script_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
        "emotion_echo_sha256": hashlib.sha256(
            open(os.path.join(CODE, "life", "emotion_echo.py"), "rb").read()).hexdigest(),
        "code_sha": os.environ.get("F3_REPLAY_CODE_SHA", ""),
        "forced_enabled": True,
        "params": params,
        "arms": arms,
    }
    if args.out_json:
        out = args.out_json if os.path.isabs(args.out_json) else os.path.join(REPO, args.out_json)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        open(out, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
        print("written:", out)

    print("\n### 机制落点覆盖率（回放判定器，强制 enabled=True）")
    print("| arm | sha8 | 消息 | 机会(分母) | 会产呼应 | 率 | by_source | by_kind |")
    print("|---|---|---|---|---|---|---|---|")
    for a in arms:
        if not a.get("exists"):
            print(f"| {a['label']} | — | 文件缺失 | — | — | — | — | — |")
            continue
        o = a["opportunities"]
        print(f"| {a['label']} | {a['log_sha8']} | {a['n_messages']} | {o['n']} | {o['planned']} | "
              f"{o['rate']} | {json.dumps(o['by_source'], ensure_ascii=False)} | "
              f"{json.dumps(o['by_kind'], ensure_ascii=False)} |")
    print("\n### 回复路径全部消息上的覆盖率（不看极性机会，只看回复条数）")
    for a in arms:
        if not a.get("exists"):
            continue
        r = a["all_reply_messages"]
        print(f"- {a['label']} ({a['log_sha8']}): 回复消息 {r['n']} 条 → 会产呼应 {r['planned']} "
              f"({r['rate']})")


if __name__ == "__main__":
    main()
