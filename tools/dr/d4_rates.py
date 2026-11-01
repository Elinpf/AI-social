"""D4 判据落地：臂内条件率 D4-1（机制到位率）/ D4-2（和解率）—— **只读脚本，零 LLM、零跑批**。

## 为什么只做"臂内条件率"
DR-off 世界里没有 rift ⇒ `和解率 = 注销/登记` 的分母是 **0/0（未定义）**。
⇒ **OFF 不能当基线**，D4 只做臂内条件率（D4-1 / D4-2），不做"ON 相对 OFF 提升 X%"。

## 两个口径必须分开报（否则又会把"没数"读成"0"）
- **口径 A（批内可观测，= 该臂运行期的真值）**：直接读 `run.jsonl` 里 MSG 的
  `payload["dialogue_rift"]` / `payload["dialogue_repair"]`。
  这两个字段**只在 `enabled=1` 时出现** ⇒ DR 关的批里必然一条都没有。
- **口径 B（离线重放，= "若开 DR，这批里会有多少旧账"的预估）**：用 `DR.ingest_one()`
  （纯函数、无 LLM）按 seq 重放重建台账。⚠ 重放必须 `enabled=True`，否则
  `ingest_one` 首行就 return ⇒ 台账恒空，会把"重放没开"误当成"批里没有负向话"。
  **口径 B 是预估，不是该臂读数**；它的 D4-1 **分子不可观测**（批内无 `prompted` 字段），
  故只给分母、不给比值。

## 「未了结（open）」的时点口径（写死）
处理到 `seq = e` 的 MSG 时，若发言方 agent 的台账在**吸收完所有 `seq < e` 的可见 MSG 之后**
仍非空（`len(rifts[agent]) > 0`），则称"该条 MSG 生成时存在未了结 rift"。
理由：运行期 `_communicate()` 是**先 `DR.ingest(可见事件)` 更新台账，再挑目标/生成消息**
（`agent.py` 的 `_communicate` 开头），所以"生成时"= 已吸收前序可见消息之后。

## 可见性口径（与运行期一致）
按 MSG 类型的 `perception_scope` 判定：`MSG_PUBLIC = global`（人人可见）、
`MSG_DM = private`（仅 `from`/`to`）、`MSG_GROUP = members`（`participants` 内）。
（`contracts/visibility.py` 是唯一真源；MSG 三类不依赖 `place`，故无需 location。）

用法：
    python3 tools/dr/d4_rates.py --log v2/evidence/d9z-on_n16r56_s42/run.jsonl
    python3 tools/dr/d4_rates.py --log A.jsonl --log B.jsonl --out /tmp/d4.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(_ROOT, "code"), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")


# ---------------------------------------------------------------- 读入
def load(path: str) -> list:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _msgs(recs: list) -> list:
    return [r for r in recs if str(r.get("type", "")) in MSG_TYPES]


def _sender(p: dict) -> str | None:
    return p.get("from") or p.get("author")


def _visible_to(p: dict, etype: str, aid: str) -> bool:
    """按 perception_scope 语义判定该 MSG 是否对 aid 可见（与运行期一致）。"""
    if etype == "MSG_PUBLIC":
        return True
    if etype == "MSG_DM":
        return aid in (p.get("from"), p.get("to"))
    if etype == "MSG_GROUP":
        return aid in (p.get("participants") or []) or aid in (p.get("from"),)
    return True


def _ratio(num: int, den: int, undefined_reason: str) -> dict:
    """分母=0 ⇒ **显式未定义**，绝不输出 0.0 冒充。"""
    if den == 0:
        return {"numerator": num, "denominator": den, "value": None,
                "status": "undefined",
                "undefined_reason": undefined_reason}
    return {"numerator": num, "denominator": den, "value": round(num / den, 6),
            "status": "ok"}


# ---------------------------------------------------------------- 口径 A
def mode_a(recs: list) -> dict:
    """批内可观测：直接读 MSG 上的 `dialogue_rift` / `dialogue_repair` 字段。

    ⚠ **字段缺失 ≠ 观测到 0**：旧批次可能根本没有 `dialogue_repair` 键（R13 之前）。
    这里显式统计"键是否存在"，并把缺键情形报为 `not_observable`，不当作 0 参与比值。
    """
    import life.dialogue_repair as DRm

    msgs = _msgs(recs)
    has_rift_key = [m for m in msgs if isinstance((m.get("payload") or {}).get("dialogue_rift"), dict)]
    has_repair_key = [m for m in msgs if isinstance((m.get("payload") or {}).get("dialogue_repair"), dict)]
    open_gt0 = [m for m in has_rift_key
                if int(((m.get("payload") or {}).get("dialogue_rift") or {}).get("open") or 0) > 0]
    # 按 route 分组：`dialogue_repair` 只在 reply 路径存在 ⇒ 分母必须给"全口径"与"reply 子口径"两个
    open_reply = [m for m in open_gt0
                  if ((m.get("payload") or {}).get("dialogue_rift") or {}).get("route") == "reply"]
    open_initiate = [m for m in open_gt0
                     if ((m.get("payload") or {}).get("dialogue_rift") or {}).get("route") == "initiate"]
    prompted = [m for m in msgs
                if ((m.get("payload") or {}).get("dialogue_repair") or {}).get("prompted") is True]
    repair_word_msgs = sum(1 for m in msgs if DRm.has_repair((m.get("payload") or {}).get("body") or ""))
    neg_word_msgs = sum(1 for m in msgs if DRm.is_gripe((m.get("payload") or {}).get("body") or ""))

    # ⚠ 若 `dialogue_repair` 键根本不存在（历史版本早于 R13），分子**不可观测**
    # ⇒ 必须报 undefined，**不能被算成 0.0**（否则就是"字段缺失伪装成 0%"）
    not_obs = len(has_repair_key) == 0
    d41_all = ({"numerator": None, "denominator": len(open_gt0), "value": None,
                "status": "undefined",
                "undefined_reason": "dialogue_repair 键在本批不存在（代码版本早于 R13）"
                                    "⇒ 分子不可观测，**不是 0%**"}
               if not_obs else
               _ratio(len(prompted), len(open_gt0),
                      "本臂没有一条 MSG 处于「有未了结 rift」状态 ⇒ D4-1 未定义"))
    d41_reply = ({"numerator": None, "denominator": len(open_reply), "value": None,
                  "status": "undefined",
                  "undefined_reason": "dialogue_repair 键在本批不存在（代码版本早于 R13）"
                                      "⇒ 分子不可观测，**不是 0%**"}
                 if not_obs else
                 _ratio(len(prompted), len(open_reply),
                        "本臂没有「reply 路径且带未了结 rift」的 MSG ⇒ D4-1 未定义"))
    return {
        "note": "口径 A = 该臂运行期真值（字段只在 enabled=1 时出现）",
        "msgs_total": len(msgs),
        "field_presence": {
            "msgs_with_dialogue_rift": len(has_rift_key),
            "msgs_with_dialogue_repair": len(has_repair_key),
            "msgs_missing_dialogue_repair_key": len(msgs) - len(has_repair_key),
            "dialogue_repair_not_observable": len(has_repair_key) == 0,
            "note": "键不存在 ⇒ 该通道在本批不可观测（历史版本早于 R13），**不是 0**",
        },
        "msgs_with_rift_open_gt0": len(open_gt0),
        "rift_open_gt0_by_route": {"reply": len(open_reply), "initiate": len(open_initiate)},
        "msgs_with_dialogue_repair_prompted_true": len(prompted),
        "word_hits": {"neg_word_msgs": neg_word_msgs, "repair_word_msgs": repair_word_msgs},
        # D4-1 两个分母：全口径（下界，被 initiate 稀释）与 reply 子口径（公平值）
        "d4_1_all_paths": d41_all,
        "d4_1_reply_only": d41_reply,
        "d4_1": d41_reply if d41_reply["status"] == "ok" else d41_all,
        "d4_2_note": "口径 A 无法观测'注销'（`ingest_one` 的 pop 不落事件）⇒ D4-2 只看口径 B",
    }


# ---------------------------------------------------------------- 口径 B
def mode_b(recs: list) -> dict:
    """离线重放（enabled=True）：重建台账，算登记/注销/悬置 + D4-2 与 D4-1 的分母预估。"""
    import life.dialogue_repair as DR

    params = dict(DR.DEFAULTS)
    params["enabled"] = True          # ⚠ 重放必须开，否则 ingest_one 首行 return
    msgs = sorted(_msgs(recs), key=lambda r: int(r.get("seq", 0)))

    agents = set()
    for m in msgs:
        p = m.get("payload") or {}
        for k in ("from", "author", "to"):
            if isinstance(p.get(k), str):
                agents.add(p[k])
        for x in (p.get("participants") or []):
            if isinstance(x, str):
                agents.add(x)
    agents = sorted(agents)

    rifts = {a: {} for a in agents}
    seen = {a: set() for a in agents}
    registered = resolved = pruned = 0
    dwell = []                        # 注销时的悬置轮数
    by_agent_reg = Counter()
    by_agent_res = Counter()
    by_thread_reg = Counter()
    by_thread_res = Counter()
    open_msg_denom = 0                # D4-1 口径 B 分母：发言时台账非空的 MSG 条数
    open_msg_by_agent = Counter()
    last_round = None

    for m in msgs:
        seq = int(m.get("seq", 0))
        rnd = int(m.get("round", 0) or 0)
        etype = m.get("type")
        p = m.get("payload") or {}
        snd = _sender(p)

        # ① 先看"生成时"状态（运行期：先 ingest 前序、再生成）
        if snd in rifts and rifts[snd]:
            open_msg_denom += 1
            open_msg_by_agent[snd] += 1

        # ② 再让可见的 agent 吸收这条（含发言者自己 —— 但 ingest_one 会跳过 author==agent_id）
        for a in agents:
            if not _visible_to(p, etype, a):
                continue
            before = set(rifts[a])
            DR.ingest_one(rifts[a], seen[a], seq, etype, p, rnd, a, params)
            after = set(rifts[a])
            new = after - before
            gone = before - after
            if new:
                registered += len(new)
                by_agent_reg[a] += len(new)
                for rid in new:
                    by_thread_reg[rifts[a][rid]["thread_id"]] += 1
            if gone:
                resolved += len(gone)
                by_agent_res[a] += len(gone)
                for rid in gone:
                    by_thread_res[rid.split("|")[1] if "|" in rid else "?"] += 1
                    dwell.append(rnd - int((m.get("payload") or {}).get("_rift_round", rnd)))

        # ③ 回合末有界化（与运行期 `DR.ingest` 末尾 `_prune` 一致）
        if last_round is not None and rnd != last_round:
            for a in agents:
                n0 = len(rifts[a])
                DR.prune(rifts[a], params, rnd)
                pruned += n0 - len(rifts[a])
        last_round = rnd

    import life.dialogue_repair as _DR2
    repair_word_msgs = sum(1 for m in msgs
                           if _DR2.has_repair((m.get("payload") or {}).get("body") or ""))
    neg_word_msgs = sum(1 for m in msgs
                        if _DR2.is_gripe((m.get("payload") or {}).get("body") or ""))
    return {
        "note": "口径 B = 离线重放假想台账（enabled=True）⇒ 预估，不是该臂读数",
        "word_hits": {"neg_word_msgs": neg_word_msgs, "repair_word_msgs": repair_word_msgs},
        "replay_enabled": True,
        "agents": len(agents),
        "registered": registered,
        "resolved": resolved,
        "pruned_dropped": pruned,
        "d4_1_denominator_estimate": open_msg_denom,
        "d4_1_estimate_note": "口径 B 只给分母：批内无 `dialogue_repair.prompted` 字段 ⇒ 分子不可观测，"
                              "故不给比值（给了就是编数）",
        "d4_2": _ratio(resolved, registered,
                       "重放台账里没有任何 rift 登记 ⇒ 和解率未定义（不是 0%）"),
        "open_msgs_by_agent": dict(open_msg_by_agent),
        "registered_by_agent": dict(by_agent_reg),
        "resolved_by_agent": dict(by_agent_res),
        "registered_by_thread_top": dict(Counter(by_thread_reg).most_common(10)),
        "dwell_rounds": {"n": len(dwell),
                         "min": min(dwell) if dwell else None,
                         "max": max(dwell) if dwell else None,
                         "mean": round(sum(dwell) / len(dwell), 3) if dwell else None},
        "open_at_end": sum(len(v) for v in rifts.values()),
    }


# ---------------------------------------------------------------- 自检
def selftest() -> dict:
    """构造小台账，证明宏能算出**非 0**（装置能出声）。与真数据结果分开报。"""
    import life.dialogue_repair as DR

    params = dict(DR.DEFAULTS); params["enabled"] = True
    out = {}

    # 例1：A 听到一句负向话（登记），随后同线程 A 说修复词（注销）⇒ 和解率 1.0
    rifts, seen = {}, set()
    DR.ingest_one(rifts, seen, 1, "MSG_DM",
                  {"from": "B", "to": "A", "body": "你什么意思，我很生气", "thread_id": "T1",
                   "msg_uid": "m1"}, 0, "A", params)
    reg = len(rifts)
    DR.ingest_one(rifts, seen, 2, "MSG_DM",
                  {"from": "A", "to": "B", "body": "对不起，我不是那个意思", "thread_id": "T1",
                   "msg_uid": "m2"}, 1, "A", params)
    out["case1_register_then_repair"] = {
        "registered": reg, "resolved": reg - len(rifts),
        "rate": _ratio(reg - len(rifts), reg, "n/a"),
    }

    # 例2：登记但无修复 ⇒ 0.0（此时分母非 0，0% 是合法读数）
    rifts2, seen2 = {}, set()
    DR.ingest_one(rifts2, seen2, 1, "MSG_DM",
                  {"from": "B", "to": "A", "body": "烦死了，凭什么", "thread_id": "T2",
                   "msg_uid": "m3"}, 0, "A", params)
    out["case2_register_no_repair"] = {
        "registered": len(rifts2), "resolved": 0,
        "rate": _ratio(0, len(rifts2), "n/a"),
    }

    # 例3：没有任何负向话 ⇒ 分母 0 ⇒ 必须输出 undefined（不是 0%）
    out["case3_no_rift"] = {"registered": 0, "resolved": 0,
                            "rate": _ratio(0, 0, "分母=0：无 rift 登记 ⇒ 未定义")}

    # 例4：D4-1 比值形状（合成 3 条"有旧账的发言"，其中 2 条 prompted）⇒ 2/3
    out["case4_d41_shape"] = _ratio(2, 3, "n/a")

    ok = (out["case1_register_then_repair"]["rate"]["value"] == 1.0
          and out["case2_register_no_repair"]["rate"]["value"] == 0.0
          and out["case3_no_rift"]["rate"]["status"] == "undefined"
          and out["case3_no_rift"]["rate"]["value"] is None
          and abs(out["case4_d41_shape"]["value"] - 2 / 3) < 1e-6)
    out["selftest_ok"] = ok
    return out


def export_slice(recs: list, out_path: str) -> dict:
    """导出**可入库的复算底稿**：只留最有用的字段（<1MB 量级），不含 body/ctx 等大字段。"""
    rows = []
    for m in _msgs(recs):
        p = m.get("payload") or {}
        rift = p.get("dialogue_rift") if isinstance(p.get("dialogue_rift"), dict) else None
        rep = p.get("dialogue_repair") if isinstance(p.get("dialogue_repair"), dict) else None
        rows.append({
            "msg_uid": p.get("msg_uid") or p.get("msg_id"),
            "seq": int(m.get("seq", 0)),
            "round": int(m.get("round", 0) or 0),
            "type": m.get("type"),
            "author": _sender(p),
            "thread_id": p.get("thread_id"),
            "reply_to": p.get("reply_to"),
            "dialogue_rift": ({"prompted": bool(rift.get("prompted")), "open": int(rift.get("open") or 0),
                               "route": rift.get("route"), "with": rift.get("with"),
                               "threads": rift.get("threads"), "age_rounds": rift.get("age_rounds")}
                              if rift else None),
            "dialogue_repair": ({"prompted": bool(rep.get("prompted")), "rift_ids": rep.get("rift_ids"),
                                 "trigger_seqs": rep.get("trigger_seqs"), "thread": rep.get("thread")}
                                if rep else None),
        })
    payload = {"generated_by": "tools/dr/d4_rates.py", "card": "T-D4-RATES",
               "note": "切片：只含复算 D4 所需字段；body 未导出（体积与隐私）", "msgs": len(rows),
               "rows": rows}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    return {"slice_path": out_path, "slice_msgs": len(rows),
            "slice_bytes": os.path.getsize(out_path)}


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="D4 臂内条件率（只读）")
    ap.add_argument("--log", action="append", required=True, help="run.jsonl（可多次）")
    ap.add_argument("--out", default=None)
    ap.add_argument("--skip-selftest", action="store_true")
    ap.add_argument("--export-slice", default=None,
                    help="导出切片 JSON 的路径（每个 --log 一个，用 {n} 占位序号）")
    args = ap.parse_args(argv[1:])

    result = {"tool": "tools/dr/d4_rates.py", "card": "T-D4-RATES",
              "definitions": {
                  "D4-1": "机制到位率 = dialogue_repair.prompted=true 的 MSG 条数 / "
                          "该 agent 存在未了结 rift 的 MSG 条数",
                  "D4-2": "和解率 = 同线程后续出现修复词而注销的 rift 数 / 登记的 rift 数",
                  "open_timing": "处理到 seq=e 的 MSG 时，发言方台账在吸收完所有 seq<e 的可见 MSG 后仍非空",
                  "zero_rule": "分母=0 ⇒ 输出 status=undefined + undefined_reason，**不输出 0%**",
              },
              "inputs": []}
    for path in args.log:
        recs = load(path)
        entry = {"log": path, "events": len(recs), "msgs": len(_msgs(recs)),
                 "mode_a_observed": mode_a(recs), "mode_b_replay": mode_b(recs)}
        if args.export_slice:
            sp = args.export_slice.replace("{n}", str(len(result["inputs"]) + 1))
            entry["slice"] = export_slice(recs, sp)
        result["inputs"].append(entry)

    if not args.skip_selftest:
        result["selftest"] = selftest()

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
