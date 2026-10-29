#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F-3「情绪呼应」**采纳漏斗**读数器（零 LLM、零网络、只读 run.jsonl）。

回答一个问题：ON 臂 `echo_msgs=107` 里只有 7 条 `verify.adopted`（6.54%），
**107→7 到底掉在哪一级、每一级各掉了多少、原因是什么**。

口径来源
    * 机会集（宽口径）= `tools/metrics/f3_echo_rate.py::wide_caliber()`（**直接 import 复用**，
      不另写一份，保证与预登记口径卡 `v2/refs/P-F3-verdictable-r32.md` 一致）；
    * 候选/采纳判定 = `code/life/emotion_echo.py` 的**纯函数**（`plan()` / `verify()`），
      以离线复算方式重放，**不新增埋点、不跑批**；
    * `verify.adopted` 是**审计字段，不是报告口径**（见 `emotion_echo.py` docstring）。

四级漏斗（每一级都有可指认的代码位置，运行输出里逐级打印）
    S0 回复事件数        code/life/agent.py::_send_reply 入口（reply_to 非空）
    S1 机会集（宽口径）  f3_echo_rate.py::wide_caliber
    S2 候选生成数        code/life/emotion_echo.py::plan（+ agent.py::_emotion_echo 的证据门控/形态让位）
    S3 候选进入决策数    code/life/agent.py::_send_reply 把 echo_line 拼进 _reply_prompt
    S4 采纳数            code/life/emotion_echo.py::verify（has_ref ∧ has_cue ∧ ¬ack_then_switch）

用法（仓库根）：
    python3 tools/metrics/f3_funnel.py --log v2/evidence/cycle34_f3_on_n16r84_seed42/run.jsonl \
        --json <out.json> [--md <out.md>]

确定性：零随机 / 零墙钟 / JSON sort_keys ⇒ 同输入两次运行逐字节相同。
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CODE = os.path.join(ROOT, "code")
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from life import emotion_echo as EE           # noqa: E402  （纯函数：plan/verify/detect）
from life.dialogue_threads import core_name  # noqa: E402  （提示词显示名：与 agent._peer_names 同源）

SCHEMA = "f3-funnel/1.0"


def _load_sibling(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def display_names() -> dict:
    """{persona_id: 提示词显示名}——与 `orchestration/integration.py::build_display_map` 同口径。"""
    with open(os.path.join(CODE, "config", "personas.json"), encoding="utf-8") as f:
        raw = json.load(f)
    out = {}
    for p in raw.get("personas", []):
        pid = p.get("persona_id")
        if pid:
            out[pid] = core_name(p.get("display_name") or pid)
    return out


# ---------------------------------------------------------------- 日志读取
def read_events(path: str):
    msgs, n_lines = [], 0
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            n_lines += 1
            try:
                rec = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if not str(rec.get("type", "")).startswith("MSG_"):
                continue
            p = rec.get("payload") or {}
            body = p.get("body") if isinstance(p.get("body"), str) else ""
            ctx = p.get("ctx") or {}
            rt = p.get("reply_to")
            msgs.append({
                "seq": rec.get("seq"), "round": rec.get("round"), "type": rec.get("type"),
                "msg_uid": str(p.get("msg_uid")),
                "reply_to": (str(rt) if rt is not None else None),
                "thread_id": p.get("thread_id"),
                "participants": p.get("participants") or [],
                "from": p.get("from"), "to": p.get("to"),
                "body": body, "mood": ctx.get("mood"), "echo": ctx.get("echo"),
            })
    return msgs, n_lines


# ---------------------------------------------------------------- 级间复算
def replay_plan(parent: dict, params: dict, names: dict, partner: str | None):
    """离线重放 `agent._emotion_echo()` 的判定链（**同一批纯函数**，零副作用）。

    与 agent.py::_emotion_echo 的对应关系：
      * `EE.plan(ctx_in["mood"], partner_body, …)` —— agent.py:1140 同一调用；
      * `L7S.enabled()` 时把 form/form_ins 置 None（形态让位）—— agent.py:1143-1145。
        L-7 结构臂默认 ON（`LIFE_PROMPT_L7_STRUCT`），本批 `ctx.l7struct` 全部存在 ⇒ 恒让位，
        故这里直接置 None；若某批 l7struct 缺失需改用 `L7S.enabled()` 判定。
    """
    plan = EE.plan(parent["mood"], parent["body"], params,
                   agent_id=None, thread_id=None, turn=None, round_no=None)
    if plan is None:
        return None, classify_no_plan(parent, params)
    plan["form"] = None
    plan["form_ins"] = None
    plan["name"] = names.get(partner or "", None)
    return plan, None


def classify_no_plan(parent: dict, params: dict) -> str:
    """`plan()` 返回 None 的**唯一原因分类**（按 plan() 内部判定顺序，逐条对应代码行）。"""
    d = EE.detect(parent["mood"], parent["body"], params)
    if d["sign"] == 0:
        return "no_emotion_signal"              # 情绪未命中：正文极性=0 且 mood∈{平和,未知}
    if params["require_text_evidence"] and d["source"] == "mood":
        return "gated_mood_only"                # 证据门控：只有处境标签，无文本证据
    if int(d["intensity"]) < int(params["min_intensity"]):
        return "below_min_intensity"            # 强度低于 min_intensity
    return "other"


CLAUSE_RE = re.compile(r"[，。！？!?；;、,.~～\n]")
ACK_ONLY_RE = re.compile(r"^(嗯+|唉+|哎+|哦+|哟+|啊+|唔+)$")


def first_clause_shape(body: str, name: str | None, params: dict) -> dict:
    """审计用：正文第一段（按标点切）的形态 + 「线索词落在第几段」。"""
    segs = [s.strip() for s in CLAUSE_RE.split((body or "").strip()) if s.strip()]
    raw = segs[0] if segs else ""
    cue_seg = None
    for i, s in enumerate(segs):
        if any(t in s for t in EE.CUE_TOKENS):
            cue_seg = i
            break
    return {
        "raw_first": raw,
        "raw_is_ack_only": bool(ACK_ONLY_RE.match(raw)),
        "raw_is_name_only": bool(name and raw == name),
        "cue_segment_index": cue_seg,     # None = 全文无线索词
        "n_segments": len(segs),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--json", default=None)
    ap.add_argument("--md", default=None)
    ap.add_argument("--emotion", default=os.path.join(ROOT, "tools", "d5", "emotion_lexicon.txt"))
    a = ap.parse_args(argv)

    f3 = _load_sibling("f3_echo_rate", os.path.join(HERE, "f3_echo_rate.py"))
    msgs, n_lines = read_events(a.log)
    by_uid = {}
    for m in msgs:
        by_uid.setdefault(m["msg_uid"], m)
    names = display_names()

    # —— 口径：echo 打开 + 本轮默认参数（require_text_evidence=True / form_rotation=True）
    params = dict(EE.DEFAULTS)
    params["enabled"] = True
    params_raw = {**params, "content_clause": False}
    params_now = {**params, "content_clause": True}

    # ===== S0 / S1：回复事件 与 宽口径机会集（直接复用读数器，不另写口径）
    f3_msgs, _ = f3.read_msgs(a.log)
    emo = f3.load_emotion(a.emotion)
    wide = f3.wide_caliber(f3_msgs, emo)

    n_msgs = len(msgs)
    replies = [m for m in msgs if m["reply_to"]]
    n_reply = len(replies)

    # ===== S2：离线重放 plan()，逐条给原因
    reasons = collections.Counter()
    candidates = []          # [(msg, parent, plan)]
    for m in replies:
        parent = by_uid.get(m["reply_to"])
        if parent is None:
            reasons["parent_unresolvable"] += 1
            continue
        # 对端 = **被回复那条消息的发送方**（ag.py::_send_reply 的 `partner = p.get("from")`
        # 里 `p` 是入站事件 payload；MSG_GROUP 的回复自身没有 `to`，只能从父消息取）。
        partner = parent.get("from") or m.get("to")
        plan, why = replay_plan(parent, params, names, partner)
        if plan is None:
            reasons[why] += 1
            continue
        candidates.append((m, parent, plan))
    n_cand = len(candidates)

    # 与日志实证对齐（logger 侧 ctx.echo 条数）——不一致即说明复算失效，必须点名
    logged_echo = [m for m in msgs if isinstance(m.get("echo"), dict) and m["echo"]]
    logged_keys = {m["msg_uid"] for m in logged_echo}
    replay_keys = {m["msg_uid"] for m, _, _ in candidates}
    consistency = {
        "logged_echo_rows": len(logged_echo),
        "replayed_candidates": n_cand,
        "missing_in_replay": sorted(logged_keys - replay_keys),
        "extra_in_replay": sorted(replay_keys - logged_keys),
        "identical": logged_keys == replay_keys,
    }

    # ===== S3：候选是否真的进了提示词（prompted）
    prompted = sum(1 for m, _, _ in candidates if bool((m["echo"] or {}).get("prompted")))

    # ===== S4：采纳（用 verify() 在两种「第一分句」口径下各算一次）
    def run_verify(p):
        rows = []
        for m, parent, _plan in candidates:
            plan = dict(_plan)
            v = EE.verify(m["body"], plan if p.get("content_clause") else {**plan})
            rows.append(v)
        return rows

    # 注意：verify 只看 plan 的 name/form；两种口径的差异由 params 开关在模块内决定，
    # 故这里用 EE.set_override 切换（纯函数内部读 load_params()）。
    def verify_with(p):
        EE.set_override(p)
        try:
            return [EE.verify(m["body"], pl) for m, _pa, pl in candidates]
        finally:
            EE.set_override(None)

    ver_raw = verify_with({**params, "content_clause": False})
    ver_now = verify_with({**params, "content_clause": True})

    def agg(vers):
        c = collections.Counter()
        for v in vers:
            c["has_ref"] += int(bool(v.get("has_ref")))
            c["has_cue"] += int(bool(v.get("has_cue")))
            c["ack_then_switch"] += int(bool(v.get("ack_then_switch")))
            c["adopted"] += int(bool(v.get("adopted")))
        return dict(sorted(c.items()))

    raw_agg, now_agg = agg(ver_raw), agg(ver_now)

    # 采纳失败的**原因分类**（按 verify 内部三项断言的失败组合）
    loss = collections.Counter()
    for v in ver_now:
        if v.get("adopted"):
            continue
        if not v.get("has_cue") and v.get("ack_then_switch"):
            loss["ack_then_switch_no_cue"] += 1      # 应一声就转话题，第一句无线索
        elif not v.get("has_cue"):
            loss["no_cue"] += 1                      # 第一句有内容但无线索词
        elif not v.get("has_ref"):
            loss["no_ref"] += 1                      # 有线索但没指称对方
        else:
            loss["other"] += 1

    # 结构诊断：线索词到底落在第几段 / 第一段是不是纯应声
    shapes = [first_clause_shape(m["body"], plan.get("name"), params)
              for m, _pa, plan in candidates]
    shape_c = collections.Counter()
    for s in shapes:
        shape_c["raw_first_is_ack_only"] += int(s["raw_is_ack_only"])
        shape_c["raw_first_is_name_only"] += int(s["raw_is_name_only"])
        idx = s["cue_segment_index"]
        shape_c["cue_in_segment_0"] += int(idx == 0)
        shape_c["cue_in_segment_1"] += int(idx == 1)
        shape_c["cue_in_segment_2plus"] += int(idx is not None and idx >= 2)
        shape_c["cue_nowhere"] += int(idx is None)

    out = {
        "schema": SCHEMA,
        "log": a.log,
        "log_sha256": sha256_file(a.log),
        "lines_total": n_lines,
        "script_sha256": sha256_file(os.path.abspath(__file__)),
        "f3_echo_rate_sha256": sha256_file(os.path.join(HERE, "f3_echo_rate.py")),
        "emotion_echo_sha256": sha256_file(os.path.join(CODE, "life", "emotion_echo.py")),
        "params": {k: params[k] for k in sorted(params)},
        "funnel": {
            "S0_msgs": n_msgs,
            "S0_reply_events": n_reply,
            "S1_wide_opportunity": wide["den"],
            "S1_wide_breakdown": wide.get("opportunity_breakdown"),
            "S2_candidates": n_cand,
            "S3_prompted": prompted,
            "S4_adopted_raw_clause": raw_agg["adopted"],
            "S4_adopted_content_clause": now_agg["adopted"],
        },
        "S1_to_S2_loss": dict(sorted(reasons.items())),
        "verify_raw_clause": raw_agg,
        "verify_content_clause": now_agg,
        "S4_loss_content_clause": dict(sorted(loss.items())),
        "first_clause_shape": dict(sorted(shape_c.items())),
        "replay_consistency": consistency,
        "wide_caliber": {
            "den": wide["den"], "hits": wide["hits"], "rate": wide["rate"],
            "band": wide["band"], "wilson95": wide["wilson95"],
        },
        "rates": {
            "adopted_raw_over_candidates": (round(raw_agg["adopted"] / n_cand, 6) if n_cand else None),
            "adopted_content_over_candidates": (round(now_agg["adopted"] / n_cand, 6) if n_cand else None),
            "candidates_over_replies": (round(n_cand / n_reply, 6) if n_reply else None),
        },
    }
    text = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print("written:", a.json)
    print(text)

    if a.md:
        md = render_md(out)
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(md)
        print("written:", a.md)
    return 0


def render_md(o: dict) -> str:
    f, r = o["funnel"], o["rates"]
    lines = [
        "# F-3 采纳漏斗读数（`tools/metrics/f3_funnel.py`）",
        "",
        f"- log: `{o['log']}`（sha256 `{o['log_sha256'][:16]}…`，{o['lines_total']} 行）",
        f"- 复算脚本 sha256: `{o['script_sha256'][:16]}…`；`emotion_echo.py` sha256: `{o['emotion_echo_sha256'][:16]}…`",
        "",
        "| 级 | 名称 | 数量 | 说明 |",
        "|---|---|---|---|",
        f"| S0 | MSG_* 事件 | {f['S0_msgs']} | 全量消息 |",
        f"| S0 | 其中 reply 事件 | {f['S0_reply_events']} | `reply_to != null` |",
        f"| S1 | 宽口径机会集 | {f['S1_wide_opportunity']} | 父消息可解析 ∧ (父 mood∉{{平和}} ∨ 父正文极性≠0) |",
        f"| S2 | plan() 候选 | {f['S2_candidates']} | 证据门控 + 强度阈值后仍产出 |",
        f"| S3 | 进入决策（prompted） | {f['S3_prompted']} | echo_line 真的拼进 `_reply_prompt` |",
        f"| S4 | 采纳（原口径 first-clause） | {f['S4_adopted_raw_clause']} | has_ref ∧ has_cue ∧ ¬ack_then_switch |",
        f"| S4 | 采纳（内容分句口径） | {f['S4_adopted_content_clause']} | 跳过单独的应声/称呼后再判 |",
        "",
        f"- 候选/回复 = {r['candidates_over_replies']}；原口径采纳率 = {r['adopted_raw_over_candidates']}；"
        f"内容分句口径采纳率 = {r['adopted_content_over_candidates']}",
        "",
        "## S1→S2 丢弃原因",
        "",
        "| 原因 | 条数 |",
        "|---|---|",
    ]
    for k, v in o["S1_to_S2_loss"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## S4 丢弃原因（内容分句口径）", "", "| 原因 | 条数 |", "|---|---|"]
    for k, v in o["S4_loss_content_clause"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## 第一段形态（诊断：线索词落在第几段）", "", "| 指标 | 条数 |", "|---|---|"]
    for k, v in o["first_clause_shape"].items():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
