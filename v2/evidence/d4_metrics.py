#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D4 · 双跑指标读数 + B2 阈值判定（只读，可复算）

作者：prompt-linguist ｜ 口径：`D5-指标定义-定稿v1.0.md`（L/S/K/E 编号）+ `D4-事前登记.md §2.3`
判定：|Δ| > 同分母 B2 上界 ⇒ 带外（结构性）；否则带内（仅印象）。
B2 上界由 `v2/evidence/d3_noiseband_bootstrap.py` 的同一方法现场算（消息级有放回重采样、B=2000、Random(42)、
      rate_A − rate_B 的 2.5/97.5 分位），分母 = 该指标在本跑的真实分母。

用法：
  python3 v2/evidence/d4_metrics.py \
      --run A0=/path/to/before/run.jsonl --run A1=/path/to/after/run.jsonl \
      --out v2/evidence/d4_metrics_pair.json [--side-by-side v2/evidence/d4_side_by_side.md]

设计约束：
  * 只读 run.jsonl，不调 LLM、不改世界态；
  * 线程口径自适应：有 `thread_id` 用 explicit，否则退 legacy（并在输出里标 `thread_schema`）；
  * 每张读数表都写清分子/分母；per-message / per-thread / per-agent-round 不混算。
"""
from __future__ import annotations

import argparse
import json
import random
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
CHANNEL = {"MSG_DM": "dm", "MSG_PUBLIC": "public", "MSG_GROUP": "group"}

PAREN = re.compile(r"[（(]([^）)]{0,60})[）)]")
BACKREF = ["你刚", "刚才", "你说", "你说过", "那", "这事儿", "这事", "这个",
           "上回", "昨天", "前天", "上次", "也是", "对啊", "可不是", "嗯", "对", "是嘛"]
TEMPLATE_PATTERNS = [r"^哎哟[，,]", r"^哎[，,]", r"^哎呀[，,]", r"^喂[，,]", r"^嘿[，,]",
                     r"^好家伙", r"^\S{1,3}啊[，,]"]
CLERK = [r"按流程", r"签章", r"归档", r"备案", r"汇报", r"审批", r"定期储蓄", r"最稳妥的方式"]
MODERN = [r"限量款", r"排队", r"滑板", r"网红", r"打卡", r"性价比", r"资产配置", r"理财",
          r"APP", r"手机", r"微信", r"人工智能", r"语言模型"]
# 生活气息 proxy（标 proxy，不替代 F 系列正式定义）
TIME_REF = [r"昨天", r"前天", r"上回", r"上次", r"记得", r"那天", r"前儿"]
REPAIR = [r"对不起", r"是我不好", r"别往心里去", r"你别多想", r"咱不说了", r"我错了", r"对不住"]
GOSSIP = [r"听说", r"你知不知道", r"听讲", r"有人说", r"那家"]

DETAIL_WORDS = [r"[0-9０-９一二三四五六七八九十百千万两]", r"[斤两把钱文斗升只条块张副担捆]",
                r"米|面|柴|油|盐|糖|布|木|铁|药|茶|酒|鸡|鱼|菜|糕|饼|书|笔|伞|鞋|绳|灯|碗|锅"]
STOPCHARS = set("的了是在我你他她它们和就都而及与着或一个上中下很再又还也很不没有这那"
                "吗呢吧啊呀哦么什怎样为好要说去来到得地过把被给对从向往已经"
                "（）：:；;，,。.！!？?、“”\"'…—-　 ")


def load(path: str) -> dict:
    msgs = []
    providers = None
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") not in MSG_TYPES:
            continue
        p = e.get("payload") or {}
        msgs.append({
            "seq": e.get("seq"), "round": e.get("round"), "type": e["type"],
            "channel": CHANNEL[e["type"]],
            "speaker": p.get("from") or p.get("author"),
            "to": p.get("to"), "group_id": p.get("group_id"),
            "thread_id": p.get("thread_id"), "turn_index": p.get("turn_index"),
            "reply_to": p.get("reply_to"), "topic": p.get("topic"),
            "ctx_topic": (p.get("ctx") or {}).get("topic"),
            "participants": p.get("participants"),
            "day": p.get("day"), "slot": p.get("slot"),
            "template": (p.get("tag_hints") or [None])[0],
            "body": p.get("body") or "",
        })
    return {"path": path, "msgs": msgs}


def thread_key(m: dict) -> str:
    if m.get("thread_id"):
        return f"T|{m['thread_id']}"
    if m["channel"] == "dm":
        return f"L|{m['day']}|dm|{'-'.join(sorted([str(m['speaker']), str(m['to'])]))}"
    if m["channel"] == "group":
        return f"L|{m['day']}|group|{m['group_id']}"
    return f"L|{m['day']}|public|-"


def norm(s: str) -> str:
    return re.sub(r"[\s\u3000，。！？、；：“”‘’（）()…—\-\.!?,;:\"']+", "", s).lower()


def grams(body: str, n: int = 8) -> set:
    s = re.sub(r"\s+", "", body)
    return {s[i:i + n] for i in range(max(0, len(s) - n + 1))}


def content_grams(body: str) -> set:
    s = re.sub(r"P\d{3}", "", body)
    s = "".join(ch for ch in s if ch not in STOPCHARS)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def wilson(k: int, n: int, z: float = 1.96):
    if not n:
        return None
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [round(100 * max(0, c - h), 2), round(100 * min(1, c + h), 2)]


def metrics(run: dict, core_names: set, pid2name: dict | None = None) -> dict:
    pid2name = pid2name or {}
    ms = run["msgs"]
    n = len(ms)
    ch = Counter(m["channel"] for m in ms)
    # 线程
    th = defaultdict(list)
    for m in ms:
        th[thread_key(m)].append(m)
    for k in th:
        th[k].sort(key=lambda m: (m["round"] or 0, m["seq"] or 0))
    prev = {}
    for k, arr in th.items():
        for i, m in enumerate(arr):
            prev[id(m)] = arr[i - 1] if i else None

    seen = Counter(norm(m["body"]) for m in ms)
    g8 = defaultdict(int)
    for m in ms:
        for g in grams(m["body"]):
            g8[g] += 1

    def hit(pats, b):
        return any(re.search(p, b) for p in pats)

    rows = []
    for m in ms:
        b = m["body"]
        r = {"len": len(b.strip()),
             "len_excl_paren": len(PAREN.sub("", b).strip()),
             "detail": hit(DETAIL_WORDS, b),
             "flat": (len(re.findall(r"[。！？!?]", b)) == 0) and (not hit(DETAIL_WORDS, b))}
        r["L2"] = b.lstrip()[:1] in ("（", "(")
        r["L3"] = bool(PAREN.search(b))
        r["L4"] = bool(PAREN.search(b)) and any(nm in PAREN.search(b).group(1) for nm in core_names)
        r["L5"] = hit(TEMPLATE_PATTERNS, b.lstrip("（( "))
        r["L6"] = seen[norm(b)] > 1
        r["L7"] = any(g8[g] > 1 for g in grams(b))
        r["L8"] = bool(re.search(r"P\d{3}", b))
        r["L9"] = hit(MODERN, b)
        r["L11"] = (m["channel"] in ("dm", "group")) and not re.search(r"[你您]", b)
        own = pid2name.get(str(m["speaker"]))
        # L-12a 提及率 / L-12b 称呼率（eval-researcher 定稿：dm+group 分母 623）
        peers = []
        if m["channel"] == "dm":
            peers = [pid2name.get(str(m.get("to")))]
        elif m["channel"] == "group":
            peers = [pid2name.get(str(x)) for x in (m.get("participants") or []) if str(x) != str(m["speaker"])]
        peers = [t for t in peers if t]
        r["L12a_mention"] = any(t in b for t in peers)
        r["L12b_address"] = any(re.search(re.escape(t) + r"[，、！？：；—…~～啊呀哦呢哈嘛吧]|" + re.escape(t) + r"$",
                                          PAREN.sub("", b)) for t in peers)
        # L-13 内部 token 泄漏：ctx.topic 原字符串直接出现在 body
        tok = m.get("ctx_topic")
        r["L13_token_leak"] = bool(tok) and (str(tok) in b)
        r["F_time_ref"] = hit(TIME_REF, b)
        r["F_repair"] = hit(REPAIR, b)
        r["F_gossip"] = hit(GOSSIP, b)
        p = prev.get(id(m))
        if p is None:
            r["K1_backref"] = None
            r["K1_lexical"] = None
            r["K1_same_topic"] = None
        else:
            r["K1_backref"] = hit(BACKREF, b)
            r["K1_lexical"] = bool(content_grams(b) & content_grams(p["body"]))
            r["K1_same_topic"] = (m["topic"] is not None and m["topic"] == p["topic"])
        rows.append(r)

    def rate(key, restrict=None):
        pool = [x for x, m in zip(rows, ms) if restrict is None or m["channel"] in restrict]
        pool = [x for x in pool if x.get(key) is not None]
        k = sum(1 for x in pool if x[key] is True)
        return k, len(pool)

    _lex = sorted(x["len_excl_paren"] for x in rows)
    out = {"path": run["path"], "n_msgs": n, "channels": dict(ch),
           "len_excl_paren_p50": statistics.median(_lex) if _lex else None,
           "len_excl_paren_p10": _lex[int(0.1 * (n - 1))] if n else None,
           "thread_schema": "explicit" if any(m["thread_id"] for m in ms) else "legacy",
           "n_threads": len(th),
           "len_p10": sorted(x["len"] for x in rows)[int(0.1 * (n - 1))] if n else None,
           "len_p50": statistics.median([x["len"] for x in rows]) if n else None,
           "len_p90": sorted(x["len"] for x in rows)[int(0.9 * (n - 1))] if n else None,
           "metrics": {}}
    spec = [("L2", None), ("L3", None), ("L4", None), ("L5", None), ("L6", None),
            ("L7", None), ("L8", None), ("L9", None), ("L11", {"dm", "group"}),
            ("L12a_mention", {"dm", "group"}), ("L12b_address", {"dm", "group"}),
            ("L13_token_leak", None), ("K1_backref", None), ("K1_lexical", None),
            ("K1_same_topic", None), ("F_time_ref", None), ("F_repair", None), ("F_gossip", None)]
    for key, restrict in spec:
        k, d = rate(key, restrict)
        out["metrics"][key] = {"hit": k, "denom": d,
                               "rate_pct": round(100 * k / d, 2) if d else None,
                               "ci95": wilson(k, d)}
    # 线程/效率
    sizes = sorted(len(v) for v in th.values())
    turns = []
    for arr in th.values():
        t = 1
        for a, b2 in zip(arr, arr[1:]):
            if a["speaker"] != b2["speaker"]:
                t += 1
        turns.append(t)
    out["S"] = {
        "n_threads": len(th),
        "msgs_per_thread_p50": statistics.median(sizes) if sizes else None,
        "single_msg_thread_ratio_pct": round(100 * sum(1 for s in sizes if s == 1) / len(sizes), 2) if sizes else None,
        "multi_turn_thread_ratio_pct": round(100 * sum(1 for t in turns if t >= 3) / len(turns), 2) if turns else None,
        "turns_A_p50": statistics.median(turns) if turns else None,
    }
    replied = sum(1 for m in ms if m.get("reply_to"))
    out["S"]["reply_pointer_coverage_pct"] = round(100 * replied / n, 2) if n else None
    return out


def boot_band(a: dict, b: dict, key: str, restrict=None, B: int = 2000, seed: int = 42):
    """同口径 B2：两跑各自按本跑分母有放回重采样，取 rate 差 2.5/97.5 分位。"""
    def pool(run):
        rows = [m for m in run.get("_rows", []) if restrict is None or m["_channel"] in restrict]
        return [x for x in rows if x.get(key) is not None]
    A, Bp = pool(a), pool(b)
    if not A or not Bp:
        return None
    rng = random.Random(seed)
    diffs = []
    for _ in range(B):
        ra = sum(1 for _ in range(len(A)) if A[rng.randrange(len(A))][key] is True) / len(A)
        rb = sum(1 for _ in range(len(Bp)) if Bp[rng.randrange(len(Bp))][key] is True) / len(Bp)
        diffs.append(100 * (ra - rb))
    diffs.sort()
    return [round(diffs[int(0.025 * (B - 1))], 2), round(diffs[int(0.975 * (B - 1))], 2)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, help="name=path，必须给两个")
    ap.add_argument("--out", required=True)
    ap.add_argument("--side-by-side", default=None)
    ap.add_argument("--names", default=None, help="personas.json 路径（用于 L-4/L-12 人名表）")
    a = ap.parse_args()
    core = set()
    pid2name = {}
    npath = a.names or str(Path(__file__).resolve().parents[2] / "code" / "config" / "personas.json")
    try:
        for p in json.loads(Path(npath).read_text(encoding="utf-8"))["personas"]:
            nm = str(p.get("display_name") or "").split("·")[-1].strip()
            if nm:
                core.add(nm)
                pid2name[str(p.get("persona_id"))] = nm
    except Exception:
        pass

    runs = {}
    for spec in a.run:
        name, _, path = spec.partition("=")
        runs[name] = load(path)
        runs[name]["_core"] = core
    names = list(runs)
    res = {"generated_by": "v2/evidence/d4_metrics.py",
           "criterion_source": "artifacts/reports/D5-指标定义-定稿v1.0.md + D4-事前登记.md §2.3",
           "runs": {}}
    for nm in names:
        res["runs"][nm] = metrics(runs[nm], core, pid2name)
    if len(names) == 2:
        A, Bn = names
        ma, mb = res["runs"][A], res["runs"][Bn]
        cmp = {}
        for key in ma["metrics"]:
            d = mb["metrics"][key]["denom"]
            if not d:
                continue
            delta = round((mb["metrics"][key]["rate_pct"] or 0) - (ma["metrics"][key]["rate_pct"] or 0), 2)
            cmp[key] = {"A_rate_pct": ma["metrics"][key]["rate_pct"],
                        "B_rate_pct": mb["metrics"][key]["rate_pct"],
                        "delta_pp": delta,
                        "A_ci95": ma["metrics"][key]["ci95"],
                        "B_ci95": mb["metrics"][key]["ci95"],
                        "denom_B": d}
        cmp["_len_p50"] = {"A": ma["len_p50"], "B": mb["len_p50"],
                           "delta": (mb["len_p50"] or 0) - (ma["len_p50"] or 0)}
        cmp["_len_excl_paren_p50"] = {"A": ma["len_excl_paren_p50"], "B": mb["len_excl_paren_p50"],
                                      "delta_pct": round(100 * ((mb["len_excl_paren_p50"] or 0) / (ma["len_excl_paren_p50"] or 1) - 1), 2)}
        res["compare"] = {"A": A, "B": Bn, "rows": cmp,
                          "note": "带外判定需按 D4-事前登记 §2.3.0 的 B2 上界；本脚本只出读数与 CI，不自动下结论"}
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    for nm in names:
        r = res["runs"][nm]
        print(f"== {nm} n={r['n_msgs']} {r['channels']} threads={r['n_threads']} p50={r['len_p50']}")
        for k, v in r["metrics"].items():
            print(f"   {k:14s} {v['hit']:4d}/{v['denom']:4d} = {v['rate_pct']}%  ci={v['ci95']}")
    if "compare" in res:
        print("== compare (B - A)")
        for k, v in res["compare"]["rows"].items():
            if k.startswith("_"):
                print(f"   {k:22s} {v}")
            else:
                print(f"   {k:14s} {v['A_rate_pct']} -> {v['B_rate_pct']}  Δ={v['delta_pp']}pp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
