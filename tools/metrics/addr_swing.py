#!/usr/bin/env python3
"""addr_swing.py — N-15 主判据尺子：称呼「摆动口径」（`S-1` / `S-2`），只读聚合。

预登记：`v2/refs/N15-prereg-addr-evolve-20261030.md` §3.1 / §3.2（**定义出数前冻结**）。
本脚本**不修改** `address_drift.py` 的任何判据；呼语位识别、词表派生、指向分类全部**复用**它。

## 口径（逐条照抄预登记 §3.1，跑后不得改）

| 项 | 定义 |
|---|---|
| 统计单位 | **有向说话对 × 线程**（`speaker → addressee`，同一 `thread_id` 内），**仅 `MSG_DM`** |
| 可判条件（分母） | 该有向对在该线程内识别出 **≥2 次可判指向**的称呼（`addr_target == "target_ok"` 才计入；`self_name` / `other_named` / `unknown_target` / `generic` **不计入**摆动分子与分母，只进排除计数） |
| `S-1` 分子 | 上述有向对中，**至少出现 1 次**「相邻两次可判称呼形式不同」（`A → B`，含 `A→B→A` 计 1 对）的有向对数 |
| `S-1` 比率 | `分子 / 分母`（报告必须写成 `12/43 (27.91%)` 形态） |
| `S-2`（次级登记，**不作判据**） | 出现 **`A→B→A` 回摆**（≥2 次方向反转）的有向对数 / 同一分母 |

## 为什么必须新写（不是偏好）

`tools/metrics/address_drift.py:320` 对 `addr_switch_rate.examples` 有 `if len(switch_examples) < 20`
的**硬上限** ⇒ 在 `n16r84` 规模上会被截断，**不能**作摆动聚合的数据源。

## 用法

```bash
# 出数（主判据 + 次级登记）
python3 tools/metrics/addr_swing.py --log v2/evidence/<批次>/run.jsonl --arm OFF \
        --out-json v2/evidence/n15_addr/off.json --out-md /tmp/off.md

# 尺子自检（≥8 用例；起跑前必须 rc=0）
python3 tools/metrics/addr_swing.py --selftest

# L2 离线等价：两树各跑一次 mock，比较 MSG_* payload 逐条 0 差异
python3 tools/metrics/addr_swing.py --msg-diff /tmp/eq_base.jsonl /tmp/eq_new_off.jsonl
```

退出码：0 正常；2 参数/输入错误；3 `--msg-diff` 发现差异；4 `--selftest` 有用例失败。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
import tempfile
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import address_drift as AD  # noqa: E402  # 复用呼语位识别 / 词表派生 / 指向分类（不改其判据）

ROOT = AD.ROOT
DEFAULT_LEXICON = AD.DEFAULT_LEXICON
DEFAULT_PERSONAS = AD.DEFAULT_PERSONAS

#: 摆动口径只纳入 `MSG_DM`（与预登记 §3.1 一致）
SWING_MSG_TYPE = "MSG_DM"

#: 摆动分子允许的指向分类（只有 `target_ok` 是「可判指向」）
COUNTABLE_TARGET = "target_ok"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _classify_msgs(log_path: str, lex_path: str = DEFAULT_LEXICON,
                   personas_path: str = DEFAULT_PERSONAS) -> tuple[list, dict]:
    """把 `run.jsonl` 的 MSG 逐条分类成带 `addr_form` / `addr_target` 的行。

    分类逻辑与 `address_drift.compute()` 的对应段落**逐字同源**（复用其公开函数）：
    `strip_parenthetical` / `find_vocative` / `any_mention` + `owners` 指向判定。
    """
    lex = AD.load_lexicon(lex_path)
    terms, _agent_info, owners = AD.build_agent_terms(lex, personas_path)
    with open(personas_path, "r", encoding="utf-8") as f:
        base_names = {p["display_name"].split("·")[-1].strip() for p in json.load(f)["personas"]}
    voc = lex.get("vocative") or {}

    rows = []
    for rec in AD.iter_msgs(log_path):
        m = AD.as_msg(rec)
        if m is None:
            continue
        text = AD.strip_parenthetical(m["body"], base_names)
        hit = AD.find_vocative(text, terms, voc)
        m["addr_form"] = hit[0] if hit else None
        m["addr_tier"] = hit[1] if hit else None
        if hit is None:
            m["addr_target"] = None
        else:
            own = owners.get(hit[0]) or set()
            if not own:
                m["addr_target"] = "generic"
            elif m["addressee"] is None:
                m["addr_target"] = "unknown_target"
            elif m["addressee"] in own:
                m["addr_target"] = "target_ok"
            elif m["speaker"] in own:
                m["addr_target"] = "self_name"
            else:
                m["addr_target"] = "other_named"
        rows.append(m)
    rows.sort(key=lambda x: (x["seq"] if x["seq"] is not None else 0))
    return rows, {"lexicon": lex, "terms": terms, "owners": owners}


def compute_swing(rows: list) -> dict:
    """按预登记 §3.1 计算 `S-1` / `S-2`。输入 = `_classify_msgs` 的行。"""
    by_dir: dict[tuple, list] = defaultdict(list)
    for m in rows:
        if m.get("type") != SWING_MSG_TYPE:
            continue
        if not (m.get("thread_id") and m.get("speaker") and m.get("addressee")):
            continue
        if m.get("addr_target") != COUNTABLE_TARGET:
            continue
        by_dir[(m["thread_id"], m["speaker"], m["addressee"])].append(m)

    pair_rows = []
    denom = 0
    n_swing = 0
    n_back_forth = 0
    for (tid, spk, to), msgs in sorted(by_dir.items()):
        msgs.sort(key=lambda r: (r["seq"] if r["seq"] is not None else 0))
        forms = [r["addr_form"] for r in msgs]
        if len(forms) < 2:
            continue
        denom += 1
        changes = [i for i in range(1, len(forms)) if forms[i] != forms[i - 1]]
        swing = bool(changes)
        # `A→B→A`：相邻两次变化回到首个形式（≥2 次方向反转）
        back_forth = any(forms[i - 2] == forms[i] and forms[i - 1] != forms[i]
                         for i in range(2, len(forms)))
        if swing:
            n_swing += 1
        if back_forth:
            n_back_forth += 1
        pair_rows.append({
            "thread_id": tid, "speaker": spk, "addressee": to,
            "n_addr_judgeable": len(forms), "forms": forms,
            "n_changes": len(changes), "swing": swing, "back_forth": back_forth,
            "seqs": [r["seq"] for r in msgs],
        })

    # 排除计数（只披露，不进判据）
    excl = defaultdict(int)
    for m in rows:
        t = m.get("addr_target")
        if t:
            excl[t] += 1

    return {
        "msg_type_scope": SWING_MSG_TYPE,
        "countable_target": COUNTABLE_TARGET,
        "S-1_addr_swing_pairs_rate": {
            "denom_pairs": denom,
            "n_swing_pairs": n_swing,
            "rate": (n_swing / denom) if denom else None,
            "n_pairs_lt2_addr": sum(1 for k, v in by_dir.items() if len(v) < 2),
        },
        "S-2_back_forth_pairs_rate": {
            "denom_pairs": denom,
            "n_back_forth_pairs": n_back_forth,
            "rate": (n_back_forth / denom) if denom else None,
        },
        "addr_target_counts": {k: excl[k] for k in sorted(excl)},
        "pairs": pair_rows,
        "n_pairs_listed": len(pair_rows),
        "n_addr_forms_histogram": _hist([len(r["forms"]) for r in pair_rows]),
    }


def _hist(values: list) -> dict:
    out: dict[str, int] = {}
    for v in values:
        out[str(v)] = out.get(str(v), 0) + 1
    return {k: out[k] for k in sorted(out, key=lambda x: int(x))}


def compute(log_path: str, lex_path: str = DEFAULT_LEXICON, personas_path: str = DEFAULT_PERSONAS,
            arm: str | None = None) -> dict:
    rows, _ctx = _classify_msgs(log_path, lex_path, personas_path)
    n_msg = len(rows)
    n_dm = sum(1 for m in rows if m.get("type") == SWING_MSG_TYPE)
    swing = compute_swing(rows)
    out = {
        "tool": "tools/metrics/addr_swing.py",
        "tool_sha256": AD.sha256_file(os.path.abspath(__file__)),
        "defines": "v2/refs/N15-prereg-addr-evolve-20261030.md §3.1/§3.2（出数前冻结）",
        "lexicon_path": os.path.relpath(lex_path, ROOT),
        "lexicon_sha256": AD.sha256_file(lex_path),
        "personas_path": os.path.relpath(personas_path, ROOT),
        "input_log": os.path.abspath(log_path),
        "input_log_sha256": AD.sha256_file(log_path),
        "arm": arm,
        "computed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "n_messages": n_msg,
        "n_messages_dm": n_dm,
        "metrics": swing,
    }
    return out


def to_markdown(res: dict) -> str:
    s1 = res["metrics"]["S-1_addr_swing_pairs_rate"]
    s2 = res["metrics"]["S-2_back_forth_pairs_rate"]

    def _fmt(num: int, den: int) -> str:
        return f"{num}/{den} ({100.0 * num / den:.2f}%)" if den else f"{num}/{den} (n/a)"

    def _pct(rate) -> str:
        return "n/a" if rate is None else f"{100.0 * rate:.2f}%"

    lines = [
        f"# addr_swing · arm={res.get('arm')}",
        "",
        f"- 工具 sha256: `{res['tool_sha256']}`",
        f"- 词表 sha256: `{res['lexicon_sha256']}`",
        f"- 输入日志 sha256: `{res['input_log_sha256']}`",
        f"- MSG 总数 / MSG_DM 数: `{res['n_messages']}` / `{res['n_messages_dm']}`",
        "",
        "| 读数 | 分子/分母 | 比率 |",
        "|---|---|---|",
        f"| **`S-1` addr_swing_pairs_rate**（主判据） | {_fmt(s1['n_swing_pairs'], s1['denom_pairs'])} | {_pct(s1['rate'])} |",
        f"| `S-2` back_forth_pairs_rate（次级登记，不作判据） | {_fmt(s2['n_back_forth_pairs'], s2['denom_pairs'])} | {_pct(s2['rate'])} |",
        "",
        f"- `addr_target` 计数：`{json.dumps(res['metrics']['addr_target_counts'], ensure_ascii=False, sort_keys=True)}`",
        f"- 可判有向对中每条对的可判称呼次数直方图：`{json.dumps(res['metrics']['n_addr_forms_histogram'], ensure_ascii=False)}`",
        f"- `<2` 次可判称呼而被排除的有向对数：`{s1['n_pairs_lt2_addr']}`",
    ]
    if s1["denom_pairs"] < 30:
        lines += ["", f"> ⚠ 分母 `{s1['denom_pairs']} < 30` ⇒ 按全族纪律与预登记 §6.2 **只报事件数、不报百分比趋势、不作跨臂比较**。"]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- 自检
def _mk_log(records: list) -> str:
    fd, path = tempfile.mkstemp(suffix=".jsonl", prefix="addr_swing_selftest_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path


def _msg(seq, body, speaker, to, tid="T1", mtype="MSG_DM"):
    return {
        "seq": seq, "round": seq, "type": mtype,
        "payload": {"body": body, "author": speaker, "to": to, "thread_id": tid,
                    "msg_uid": f"m{seq}", "turn_index": 0, "day": 0, "slot": 0},
    }


def selftest() -> int:
    # P002=老石（base 老石 tier3；石+叔=石叔 tier2）；P003=阿禾；P004=秀娘
    P2, P3, P4 = "P002", "P003", "P004"
    cases = []

    def rec(name, records, want_denom, want_swing, want_bf):
        cases.append((name, records, want_denom, want_swing, want_bf))

    # 1) 同一称呼两次 ⇒ 进分母、不摆动
    rec("c1 同称呼不摆动", [_msg(1, "石叔，早上好", P3, P2), _msg(2, "石叔，吃了吗", P3, P2)], 1, 0, 0)
    # 2) 一次形式变化 ⇒ 摆动
    rec("c2 一次变化即摆动", [_msg(1, "石叔，早上好", P3, P2), _msg(2, "老石，吃了吗", P3, P2)], 1, 1, 0)
    # 3) A→B→A ⇒ 摆动 + 回摆
    rec("c3 来回摆动", [_msg(1, "石叔，早", P3, P2), _msg(2, "老石，早", P3, P2),
                       _msg(3, "石叔，早", P3, P2)], 1, 1, 1)
    # 4) 只有 1 次可判称呼 ⇒ 不进分母
    rec("c4 仅1次称呼不进分母", [_msg(1, "石叔，早", P3, P2), _msg(2, "今天挺好", P3, P2)], 0, 0, 0)
    # 5) 自称（叫成自己）不进分母也不进分子
    rec("c5 自称不进口径", [_msg(1, "老石，早", P2, P3), _msg(2, "石叔，早", P2, P3)], 0, 0, 0)
    # 6) 非 MSG_DM 不进口径
    rec("c6 仅统计MSG_DM", [_msg(1, "石叔，早", P3, P2, mtype="MSG_PUBLIC"),
                           _msg(2, "老石，早", P3, P2, mtype="MSG_PUBLIC")], 0, 0, 0)
    # 7) 同说话对、不同线程 ⇒ 各算一个单位
    rec("c7 线程各自计数", [_msg(1, "石叔，早", P3, P2, tid="T1"), _msg(2, "老石，早", P3, P2, tid="T1"),
                           _msg(3, "石叔，早", P3, P2, tid="T2"), _msg(4, "石叔，好", P3, P2, tid="T2")],
        2, 1, 0)
    # 8) 通用称呼（generic，指向不可判）不进分母
    rec("c8 通用称呼不进口径", [_msg(1, "师傅，早", P3, P2), _msg(2, "老板，早", P3, P2)], 0, 0, 0)
    # 9) 空日志 ⇒ 0/0、比率为 None
    rec("c9 空日志", [], 0, 0, 0)
    # 10) 变化后保持 ⇒ 摆动但无回摆
    rec("c10 单向变化无回摆", [_msg(1, "石叔，早", P3, P2), _msg(2, "老石，早", P3, P2),
                            _msg(3, "老石，吃了吗", P3, P2)], 1, 1, 0)
    # 11) 反向有向对独立计数（P3→P2 与 P2→P3 不是同一单位）
    rec("c11 有向对独立", [_msg(1, "石叔，早", P3, P2), _msg(2, "老石，早", P3, P2),
                          _msg(3, "阿禾，早", P2, P3), _msg(4, "禾妹子，吃了吗", P2, P3)], 2, 2, 0)

    failures = 0
    for name, records, want_denom, want_swing, want_bf in cases:
        path = _mk_log(records)
        try:
            rows, _ = _classify_msgs(path)
            got = compute_swing(rows)
        finally:
            os.unlink(path)
        g1 = got["S-1_addr_swing_pairs_rate"]
        g2 = got["S-2_back_forth_pairs_rate"]
        ok = (g1["denom_pairs"] == want_denom and g1["n_swing_pairs"] == want_swing
              and g2["n_back_forth_pairs"] == want_bf)
        if ok:
            print(f"[selftest] PASS {name}  S-1={g1['n_swing_pairs']}/{g1['denom_pairs']} "
                  f"S-2={g2['n_back_forth_pairs']}/{g2['denom_pairs']}")
        else:
            failures += 1
            print(f"[selftest] FAIL {name}  期望 denom={want_denom} swing={want_swing} bf={want_bf}；"
                  f"实得 denom={g1['denom_pairs']} swing={g1['n_swing_pairs']} bf={g2['n_back_forth_pairs']}",
                  file=sys.stderr)
    # 12) 定义稳定性：注入行 sha 与词表 sha 可复算（非口径用例，仅防手滑）
    print(f"[selftest] INFO tool_sha256={AD.sha256_file(os.path.abspath(__file__))}")
    print(f"[selftest] INFO lexicon_sha256={AD.sha256_file(DEFAULT_LEXICON)}")
    if failures:
        print(f"[selftest] FAIL (failures={failures})", file=sys.stderr)
        return 4
    print("[selftest] PASS (failures=0)")
    return 0


# --------------------------------------------------------------------------- L2 等价比较
_IGNORE_KEYS = {"hash", "prev_hash", "mono_ts", "config_digest", "ts", "wall_ts",
                "elapsed", "duration", "duration_sec", "generated_at"}


def _strip(obj):
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items() if k not in _IGNORE_KEYS}
    if isinstance(obj, list):
        return [_strip(v) for v in obj]
    return obj


def msg_payloads(log_path: str) -> list:
    out = []
    for rec in AD.iter_msgs(log_path):
        out.append({"seq": rec.get("seq"), "type": rec.get("type"),
                    "payload": _strip(rec.get("payload") or {})})
    out.sort(key=lambda r: (r["seq"] if r["seq"] is not None else 0))
    return out


def msg_diff(a_path: str, b_path: str) -> int:
    a = msg_payloads(a_path)
    b = msg_payloads(b_path)
    print(f"[msg-diff] A={os.path.abspath(a_path)} n_msgs={len(a)}  sha256={AD.sha256_file(a_path)}")
    print(f"[msg-diff] B={os.path.abspath(b_path)} n_msgs={len(b)}  sha256={AD.sha256_file(b_path)}")
    if len(a) != len(b):
        print(f"[msg-diff] FAIL 条数不同：{len(a)} vs {len(b)}", file=sys.stderr)
        return 3
    diffs = []
    for x, y in zip(a, b):
        if json.dumps(x, ensure_ascii=False, sort_keys=True) != json.dumps(y, ensure_ascii=False, sort_keys=True):
            diffs.append((x["seq"], x, y))
    print(f"[msg-diff] differing_messages={len(diffs)}")
    if diffs:
        seq, x, y = diffs[0]
        print(f"[msg-diff] 首个差异 seq={seq}", file=sys.stderr)
        print("  A: " + json.dumps(x, ensure_ascii=False, sort_keys=True)[:800], file=sys.stderr)
        print("  B: " + json.dumps(y, ensure_ascii=False, sort_keys=True)[:800], file=sys.stderr)
        return 3
    print("[msg-diff] PASS MSG_* payload 逐条 0 差异（忽略 hash 链 / config_digest / 时间戳字段）")
    return 0


# --------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="N-15 称呼摆动口径（S-1/S-2）只读聚合")
    ap.add_argument("--log", help="run.jsonl")
    ap.add_argument("--arm", default=None, help="臂标签（OFF/ON/PROBE…）")
    ap.add_argument("--lexicon", default=DEFAULT_LEXICON)
    ap.add_argument("--personas", default=DEFAULT_PERSONAS)
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--msg-diff", nargs=2, metavar=("A", "B"),
                    help="比较两份 run.jsonl 的 MSG_* payload（L2 离线等价用）")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()
    if a.msg_diff:
        return msg_diff(a.msg_diff[0], a.msg_diff[1])
    if not a.log:
        ap.error("需要 --log（或 --selftest / --msg-diff）")
    if not os.path.exists(a.log):
        print(f"[FAIL] 日志不存在: {a.log}", file=sys.stderr)
        return 2

    res = compute(a.log, a.lexicon, a.personas, arm=a.arm)
    md = to_markdown(res)
    if a.out_json:
        os.makedirs(os.path.dirname(os.path.abspath(a.out_json)) or ".", exist_ok=True)
        with open(a.out_json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2, sort_keys=True)
    if a.out_md:
        os.makedirs(os.path.dirname(os.path.abspath(a.out_md)) or ".", exist_ok=True)
        with open(a.out_md, "w", encoding="utf-8") as f:
            f.write(md)
    if not a.quiet:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
