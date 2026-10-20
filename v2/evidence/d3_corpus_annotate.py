#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D3 · 对话语料标注 / 不自然模式频次（只读，可复算）

作者：prompt-linguist ｜ 类型：只读统计脚本（不改 world layer、不调 LLM、不写世界态）
口径依据：`artifacts/reports/D5-指标定义-定稿v1.0.md`（唯一引用源，编号 L-*/K-*/S-*）
语料：既有真 LLM 跑批的 run.jsonl（默认 t300 主样本 + t350/t326 外样本复现）

用法：
    python3 v2/evidence/d3_corpus_annotate.py \
        --run t300=/root/t271/runs/t300/run.jsonl \
        --run t350=/root/t271/runs/t350_n50_real/run.jsonl \
        --run t326=/root/t271/runs/t326_real/run.jsonl \
        --out-jsonl v2/evidence/d3_annotated_corpus.jsonl \
        --out-json  v2/evidence/d3_pattern_counts.json

判据全部写死在下面（冻结词表/正则随脚本一起落盘即 sha 可绑）：
  U1 模板化开场     起句套话（U1_PATTERNS）
  U2 旁白化         L-2/L-3：正文首字符为（/( ；任意位置含括号动作块
  U3 第三人称自述   L-4：括号块内「人名+动作」，人名取自 personas.json 主干名
  U4 裸 ID 称呼     L-8：正文命中 P\\d{3}
  U5 不对人说       L-11：DM/GROUP 正文无 你/您/你们
  U6 事务/公文腔     U6_PATTERNS
  U7 无承接         K-1 分项（legacy thread_key）：cont_backref / cont_lexical
  U8 重复句式       L-6 exact dup（run 内）；L-7 8-gram 共享
  U9 世界观/时代越界 U9_PATTERNS（现代消费/元话语/书面体）
  U10 公开声道独白  MSG_PUBLIC 且正文含独白标记或无第二人称

统计单位：措辞层 per-message；U7 为 per-message（线程内非首条），并给 per-thread 中位数。
所有比率的分母在输出里写明（不许只有比率没有分母）。
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
CHANNEL = {"MSG_DM": "dm", "MSG_PUBLIC": "public", "MSG_GROUP": "group"}

# ---------------- 冻结判据 ----------------
OPEN_PAREN = ("（", "(")

U1_PATTERNS = [
    r"^哎哟[，,]",
    r"^哎[，,]",
    r"^哎呀[，,]",
    r"^喂[，,]",
    r"^我说[，,]",
    r"^好家伙",
    r"^嘿[，,]",
    r"^行[，,]",
]
# U1 的「套话骨架」：称呼 + 啊/呀/哦 的寒暄起句（P0xx 会被 U4 单独记）
U1_CALL = re.compile(r"^(哎|我说|你瞧)[，,]?\s*(P\d{3}|\S{1,3})[啊呀哦]?[，,]")

U6_PATTERNS = [
    r"按流程", r"签章", r"归档", r"备案", r"汇报", r"审批", r"文件", r"材料都齐",
    r"定期储蓄", r"利息", r"最稳妥的方式", r"作为一种", r"需要考虑",
]
U9_PATTERNS = [
    r"限量款", r"排队", r"滑板", r"网红", r"打卡", r"品牌", r"消费", r"性价比",
    r"定期储蓄", r"资产配置", r"理财", r"APP", r"手机", r"微信",
]
U9_META = [r"作为一个", r"人工智能", r"语言模型", r"我是助手"]
U10_SOLILOQUY = [r"自言自语", r"独自", r"喃喃", r"嘀咕"]
BACKREF_LEXICON = ["你刚", "刚才", "你说", "你说过", "那", "这事儿", "这事", "这个",
                   "上回", "昨天", "也是", "对啊", "可不是", "嗯", "对", "是嘛"]
STOPCHARS = set("的了是在我你他她它们和就都而及与着或一个上中下很再又还也很不没有这那"
                "吗呢吧啊呀哦么什怎样为好要说去来到得地过把被给对从向往已经"
                "（）：:；;，,。.！!？?、“”\"'…—-　 ")
PAREN_BLOCK = re.compile(r"[（(]([^）)]{0,40})[）)]")

# personas 主干名（用于 U3 第三人称自述判定）：惰性从 config 读，只读
PERSONAS_PATH = Path(__file__).resolve().parents[2] / "code" / "config" / "personas.json"


def load_core_names() -> set:
    try:
        d = json.loads(PERSONAS_PATH.read_text(encoding="utf-8"))
        names = set()
        for p in d.get("personas", []):
            nm = str(p.get("display_name") or "").split("·")[-1].strip()
            if nm:
                names.add(nm)
        return names
    except Exception:
        return set()


CORE_NAMES = load_core_names()


def load_msgs(path: str) -> list[dict]:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            t = e.get("type")
            if t not in MSG_TYPES:
                continue
            p = e.get("payload") or {}
            speaker = p.get("from") or p.get("author") or p.get("from_id")
            out.append({
                "seq": e.get("seq"),
                "round": e.get("round"),
                "type": t,
                "channel": CHANNEL[t],
                "from": speaker,
                "to": p.get("to"),
                "group_id": p.get("group_id"),
                "day": p.get("day"),
                "slot": p.get("slot"),
                "template": (p.get("tag_hints") or [None])[0],
                "refs": p.get("refs"),
                "topic": p.get("topic"),
                "body": (p.get("body") or ""),
            })
    return out


# ---------------- 判据实现 ----------------
def l1_len(body: str) -> int:
    return len(body.strip())


def l2_narration_proxy(body: str) -> bool:
    b = body.lstrip()
    return bool(b) and b[0] in OPEN_PAREN


def l3_paren_any(body: str) -> bool:
    return bool(PAREN_BLOCK.search(body))


def l4_third_person_self(body: str) -> bool:
    """括号块内出现「人名 + 动作」自述（说话人第三人称叙述自己）。"""
    for m in PAREN_BLOCK.finditer(body):
        inner = m.group(1)
        if any(nm in inner for nm in CORE_NAMES):
            return True
        # 「笑眯眯地递过」这类：括号结束后紧跟主语式叙述
    tail = body[PAREN_BLOCK.search(body).end():] if PAREN_BLOCK.search(body) else ""
    if tail and any(nm in tail[:12] for nm in CORE_NAMES):
        return True
    return False


def u1_template_opening(body: str) -> bool:
    b = body.lstrip().lstrip("（(")
    for pat in U1_PATTERNS:
        if re.match(pat, b):
            return True
    return bool(U1_CALL.match(b))


def u6_clerk_tone(body: str) -> bool:
    return any(re.search(p, body) for p in U6_PATTERNS)


def u9_out_of_world(body: str) -> bool:
    if any(re.search(p, body) for p in U9_META):
        return True
    return any(re.search(p, body) for p in U9_PATTERNS)


def u10_public_soliloquy(m: dict) -> bool:
    if m["channel"] != "public":
        return False
    if any(re.search(p, m["body"]) for p in U10_SOLILOQUY):
        return True
    return not re.search(r"[你您]", m["body"])


def content_grams(body: str) -> set:
    """内容词代理：去掉实体 ID 与停用字符后的中文二元组集合（无分词器，标 proxy）。"""
    s = re.sub(r"P\d{3}", "", body)
    s = "".join(ch for ch in s if ch not in STOPCHARS)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def grams8(body: str) -> set:
    s = re.sub(r"\s+", "", body)
    return {s[i:i + 8] for i in range(max(0, len(s) - 7))}


def legacy_thread_key(m: dict) -> str:
    """D2 之前的线程近似（D5 定稿 §0 legacy 口径）。"""
    ch = m["channel"]
    if ch == "dm":
        pair = "-".join(sorted([str(m["from"]), str(m["to"])]))
        return f"{m['day']}|dm|{pair}"
    if ch == "group":
        return f"{m['day']}|group|{m['group_id']}"
    return f"{m['day']}|public|-"


# ---------------- 主流程 ----------------
def annotate(msgs: list[dict]) -> None:
    # run 内去重 / 8-gram 索引
    norm = lambda s: re.sub(r"[\s\u3000，。！？、；：“”‘’（）()…—\-\.!?,;:\"']+", "", s).lower()
    seen = Counter()
    g8 = defaultdict(list)
    for i, m in enumerate(msgs):
        seen[norm(m["body"])] += 1
        for g in grams8(m["body"]):
            g8[g].append(i)

    # 线程分组（legacy）
    threads = defaultdict(list)
    for i, m in enumerate(msgs):
        threads[legacy_thread_key(m)].append(i)
    for k in threads:
        threads[k].sort(key=lambda i: (msgs[i]["round"] or 0, msgs[i]["seq"] or 0))

    prev_in_thread = {}
    for k, idxs in threads.items():
        for pos, i in enumerate(idxs):
            prev_in_thread[i] = idxs[pos - 1] if pos > 0 else None

    for i, m in enumerate(msgs):
        body = m["body"]
        lab = {}
        lab["U1_template_opening"] = u1_template_opening(body)
        lab["U2_narration_proxy"] = l2_narration_proxy(body)
        lab["U2b_paren_block_any"] = l3_paren_any(body)
        lab["U3_third_person_self"] = l4_third_person_self(body)
        lab["U4_agent_id_leak"] = bool(re.search(r"P\d{3}", body))
        lab["U5_no_second_person"] = (m["channel"] in ("dm", "group")
                                      and not re.search(r"[你您]", body))
        lab["U6_clerk_tone"] = u6_clerk_tone(body)
        lab["U8_dup_exact"] = seen[norm(body)] > 1
        lab["U8b_ngram_shared"] = any(len(v) > 1 for g, v in [] ) or False  # 占位，下面填
        lab["U9_out_of_world"] = u9_out_of_world(body)
        lab["U10_public_soliloquy"] = u10_public_soliloquy(m)
        lab["len"] = l1_len(body)

        # U8b：与同 run 其他消息共享 ≥8 字连续子串
        shared = False
        for g in grams8(body):
            others = [j for j in g8[g] if j != i]
            if others:
                shared = True
                break
        lab["U8b_ngram_shared"] = shared

        # U7 承接（仅线程内非首条）
        pi = prev_in_thread.get(i)
        if pi is None:
            lab["U7_in_thread"] = False
            lab["K1_cont_backref"] = None
            lab["K1_cont_lexical"] = None
            lab["K1_cont_same_topic"] = None
        else:
            prev = msgs[pi]
            lab["U7_in_thread"] = True
            lab["K1_cont_backref"] = any(w in body for w in BACKREF_LEXICON)
            ov = content_grams(body) & content_grams(prev["body"])
            lab["K1_cont_lexical"] = len(ov) >= 1          # D5 定稿口径：重叠 ≥1
            lab["K1_cont_lexical_bigram2"] = len(ov) >= 2  # 更严的稳健性读数（proxy）
            lab["K1_cont_same_topic"] = None               # 无 topic 字段 ⇒ N/A（D5 定稿）
            lab["prev_body"] = prev["body"]
        lab["K1_cont_composite_R1"] = (
            (lab["K1_cont_backref"] is True) or
            (lab["K1_cont_same_topic"] is True)
        ) if lab["U7_in_thread"] else None
        m["labels"] = lab


def wilson_ci(k: int, n: int, z: float = 1.96) -> list[float] | None:
    """Wilson 95% 置信区间（百分比）。n=0 → None。"""
    if not n:
        return None
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [round(100 * max(0.0, centre - half), 2), round(100 * min(1.0, centre + half), 2)]


def add_ci(stats: dict) -> dict:
    """给所有含 hit/denom 的条目补 ci95（Wilson）。"""
    for k, v in stats.items():
        if isinstance(v, dict) and "hit" in v and "denom" in v:
            v["ci95_pct"] = wilson_ci(int(v["hit"]), int(v["denom"]))
        elif isinstance(v, dict):
            add_ci(v)
    return stats


def summarize(name: str, msgs: list[dict]) -> dict:
    n = len(msgs)
    by_ch = Counter(m["channel"] for m in msgs)
    lab = [m["labels"] for m in msgs]
    lens = sorted(m["labels"]["len"] for m in msgs)

    def pct(k: int, d: int) -> float | None:
        return round(100.0 * k / d, 2) if d else None

    n_in_thread = sum(1 for l in lab if l["U7_in_thread"])
    out = {
        "run": name,
        "n_msgs": n,
        "channels": dict(by_ch),
        "len_p10": lens[int(0.1 * (n - 1))] if n else None,
        "len_p50": statistics.median(lens) if n else None,
        "len_p90": lens[int(0.9 * (n - 1))] if n else None,
        "len_max": max(lens) if n else None,
        "U1_template_opening": {"hit": sum(l["U1_template_opening"] for l in lab), "denom": n,
                                "rate_pct": pct(sum(l["U1_template_opening"] for l in lab), n)},
        "U2_narration_proxy": {"hit": sum(l["U2_narration_proxy"] for l in lab), "denom": n,
                               "rate_pct": pct(sum(l["U2_narration_proxy"] for l in lab), n)},
        "U2b_paren_block_any": {"hit": sum(l["U2b_paren_block_any"] for l in lab), "denom": n,
                                "rate_pct": pct(sum(l["U2b_paren_block_any"] for l in lab), n)},
        "U3_third_person_self": {"hit": sum(l["U3_third_person_self"] for l in lab), "denom": n,
                                 "rate_pct": pct(sum(l["U3_third_person_self"] for l in lab), n)},
        "U4_agent_id_leak": {"hit": sum(l["U4_agent_id_leak"] for l in lab), "denom": n,
                             "rate_pct": pct(sum(l["U4_agent_id_leak"] for l in lab), n)},
        "U5_no_second_person": {
            "hit": sum(bool(l["U5_no_second_person"]) for l in lab),
            "denom": by_ch.get("dm", 0) + by_ch.get("group", 0),
            "rate_pct": pct(sum(bool(l["U5_no_second_person"]) for l in lab),
                            by_ch.get("dm", 0) + by_ch.get("group", 0))},
        "U6_clerk_tone": {"hit": sum(l["U6_clerk_tone"] for l in lab), "denom": n,
                          "rate_pct": pct(sum(l["U6_clerk_tone"] for l in lab), n)},
        "U8_dup_exact": {"hit": sum(l["U8_dup_exact"] for l in lab), "denom": n,
                         "rate_pct": pct(sum(l["U8_dup_exact"] for l in lab), n)},
        "U8b_ngram_shared": {"hit": sum(l["U8b_ngram_shared"] for l in lab), "denom": n,
                             "rate_pct": pct(sum(l["U8b_ngram_shared"] for l in lab), n)},
        "U9_out_of_world": {"hit": sum(l["U9_out_of_world"] for l in lab), "denom": n,
                            "rate_pct": pct(sum(l["U9_out_of_world"] for l in lab), n)},
        "U10_public_soliloquy": {
            "hit": sum(l["U10_public_soliloquy"] for l in lab), "denom": by_ch.get("public", 0),
            "rate_pct": pct(sum(l["U10_public_soliloquy"] for l in lab),
                            by_ch.get("public", 0))},
        "U7_thread_continuation": {
            "denom_in_thread_msgs": n_in_thread,
            "K1_cont_backref_hit": sum(1 for l in lab if l["K1_cont_backref"] is True),
            "K1_cont_backref_rate_pct": pct(sum(1 for l in lab if l["K1_cont_backref"] is True), n_in_thread),
            "K1_cont_lexical_hit": sum(1 for l in lab if l["K1_cont_lexical"] is True),
            "K1_cont_lexical_rate_pct": pct(sum(1 for l in lab if l["K1_cont_lexical"] is True), n_in_thread),
            "K1_cont_lexical_bigram2_rate_pct": pct(
                sum(1 for l in lab if l.get("K1_cont_lexical_bigram2") is True), n_in_thread),
            "K1_cont_same_topic": None,
            "K1_cont_composite_R1_rate_pct": pct(
                sum(1 for l in lab if l["K1_cont_composite_R1"] is True), n_in_thread),
            "note": "legacy thread_key=(day,channel,pair/group)；topic 字段缺失 ⇒ cont_same_topic=N/A（D5 定稿）",
        },
        "S_legacy_threads": thread_stats(msgs),
    }
    # K-1 分项补 CI（这些不是 hit/denom 结构，单独算）
    t = out["U7_thread_continuation"]
    d = t["denom_in_thread_msgs"]
    t["K1_cont_backref_ci95_pct"] = wilson_ci(t["K1_cont_backref_hit"], d)
    t["K1_cont_lexical_ci95_pct"] = wilson_ci(t["K1_cont_lexical_hit"], d)
    return add_ci(out)


def thread_stats(msgs: list[dict]) -> dict:
    threads = defaultdict(list)
    for i, m in enumerate(msgs):
        threads[legacy_thread_key(m)].append(m)
    for k in threads:
        threads[k].sort(key=lambda m: (m["round"] or 0, m["seq"] or 0))
    sizes, turns = [], []
    for k, ms in threads.items():
        sizes.append(len(ms))
        t = 1
        for a, b in zip(ms, ms[1:]):
            if (a["from"] or a.get("to")) != (b["from"] or b.get("to")):
                t += 1
        turns.append(t)
    sizes.sort()
    turns_sorted = sorted(turns)
    nn = len(sizes)
    return {
        "thread_schema": "legacy",
        "n_threads": nn,
        "msgs_per_thread_p50": statistics.median(sizes) if nn else None,
        "msgs_per_thread_max": max(sizes) if nn else None,
        "turns_A_p50": statistics.median(turns) if nn else None,
        "turns_A_p90": turns_sorted[int(0.9 * (nn - 1))] if nn else None,
        "single_msg_thread_ratio_pct": round(100.0 * sum(1 for s in sizes if s == 1) / nn, 2) if nn else None,
        "multi_turn_thread_ratio_pct": round(100.0 * sum(1 for t in turns if t >= 3) / nn, 2) if nn else None,
        "note": "turn 判定旧口径含 PUBLIC 单一说话者（from 缺失时以内部占位区分），仅作方向",
    }


def emit_quotes(rows: list[dict], path: str, k: int = 3) -> None:
    """为每条模式抽 k 条原样样本（按 run, seq 确定性排序，不随机），生成 markdown。"""
    keys = ["U1_template_opening", "U2_narration_proxy", "U3_third_person_self",
            "U4_agent_id_leak", "U5_no_second_person", "U6_clerk_tone",
            "K1_cont_backref", "K1_cont_lexical", "U8_dup_exact", "U8b_ngram_shared",
            "U9_out_of_world", "U10_public_soliloquy"]
    lines = ["# D3 · 各不自然模式的代表性原文（由 d3_corpus_annotate.py 确定性生成）", "",
             "> 抽样规则：按 `run, seq` 升序取前 k 条命中样本，**不随机、不挑选**。", ""]
    for key in keys:
        lines.append(f"## {key}")
        shown = 0
        for r in sorted(rows, key=lambda x: (x["run"], x["seq"] or 0)):
            if r.get(key) is True:
                lines.append(f"- `{r['run']}` seq={r['seq']} round={r['round']} "
                             f"{r['from'] or '(public)'}→{r['to'] or '-'} "
                             f"[{r['channel']}/{r['template']}]：{r['body']}")
                shown += 1
                if shown >= k:
                    break
        if not shown:
            lines.append("- （本语料无命中）")
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, help="name=path，可多次")
    ap.add_argument("--out-jsonl", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-quotes", default=None, help="生成代表性原文 markdown")
    a = ap.parse_args()

    all_stats = {}
    rows = []
    for spec in a.run:
        name, _, path = spec.partition("=")
        if not Path(path).exists():
            print(f"[WARN] missing run {name}: {path}", file=sys.stderr)
            continue
        msgs = load_msgs(path)
        annotate(msgs)
        all_stats[name] = summarize(name, msgs)
        for m in msgs:
            r = {k: m[k] for k in ("seq", "round", "type", "channel", "from", "to",
                                   "group_id", "day", "slot", "template", "topic", "body")}
            r["run"] = name
            r["legacy_thread"] = legacy_thread_key(m)
            r.update({k: v for k, v in m["labels"].items() if k != "prev_body"})
            rows.append(r)
        print(f"[ok] {name}: {len(msgs)} msgs", file=sys.stderr)

    Path(a.out_jsonl).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out_jsonl, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    Path(a.out_json).write_text(
        json.dumps({"generated_by": "v2/evidence/d3_corpus_annotate.py",
                    "criterion_source": "artifacts/reports/D5-指标定义-定稿v1.0.md",
                    "runs": all_stats}, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8")
    if a.out_quotes:
        emit_quotes(rows, a.out_quotes)
        print(f"[ok] quotes -> {a.out_quotes}", file=sys.stderr)
    print(json.dumps({k: {kk: v[kk] for kk in ("n_msgs", "channels")} for k, v in all_stats.items()},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
