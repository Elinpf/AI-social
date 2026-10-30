#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""D9s 测量仪器（**冻结**）：六类起首定稿 + 把·拿·用占比 + H6 熵。

定位
----
D9s 的**主判据** = 「`ba_na_rate`（①把·拿·用 占比）」与「`head_entropy`（六类分布熵）」
（`v2/refs/D9s-prereg-syntax-diversity.md` §4/§5）。
**本文件是它们的唯一实现**；任何"手搓数字"（含 md 里贴的内联脚本，如
`d9m-syntax-slot-monotony.md` §1 那段 4 类 `shape()`）**不得与本仪器输出并列**——两者类数与口径不同。

口径（**六类定义由 Leader 于 2026-10-30 定稿，判定用；顺序即优先级**）
--------------------------------------------------------------------
| 代号 | 名称 | 判定 |
|---|---|---|
| `c1_penal` | ① 把·拿·用 | 首字 ∈ `{把, 拿, 用}` |
| `c2_sp` | ② 主谓 | 匹配 `^(他|她|P0\d\d)` 起首 |
| `c4_act` | ④ 手部动作起句 | 匹配 `^(抬手|伸手|低头|侧身|抬眼|蹲在|站在|掀开|手里|指腹|抬脚|欠身|弯下|俯身)` |
| `c5_adv` | ⑤ 副词·时间 | 匹配 `^(先|又|刚|正|就|还|已|再|随手|顺手|一|两)` |
| `c6_interj` | ⑥ 语气短句·其他 | 匹配 `^(嗯|哎|唉|哦|唔|嗨|嘿)` **或** 片段长度 ≤ 6 |
| `c3_nominal` | ③ 名词性·结果先行 | **不属于** ①②④⑤⑥ 任何一类，**且** 片段长度 > 6 |

**判定顺序（显式声明，先命中先归）**：**① → ② → ④ → ⑤ → ⑥ → ③**。
不得用"取首个候选字"式互斥（那是 `d9n` 的逐字独立计数问题，与本项"整片段定类"是两个不同问题）。

**长度口径**：片段 = 成对括号内文本去掉首尾括号后 `.strip()` 的字符数（`len()`）。
⇒ 边界例：`先把话说完` 长度 5 ≤ 6，但 **⑤ 优先于 ⑥** ⇒ 归 ⑤（这是固定判定顺序的用途）。

**③ 只按"不是其他五类 + 长度>6"判定，不做任何语义规则**（不查"是否含数字/气味词"），避免造出第二套标准。

**③ 的子类（Leader 2026-10-30 追加，机械可判；不改动 ①②④⑤⑥）**
- `c3a_result_first`（结果/话题先行）当且仅当满足下列之一：
  - **(a) 名词性短语 + 逗号 + 主谓**：片段含 `，`，且**首个分句**（至首个 `，。；`）以趋向/结果结尾词
    （`下来/出来/起来/上了/过了/开了/过来/回来`）或 `了/着` 结尾 —— "结果先落地、再出人"；
  - **(b) 方位先行**：以方位词（`灶上/院里/门口/屋里/桌上/窗/墙/地上/门槛/街口`）起首 且 首分句含 `了`；
  - **(c) 数字起首且非账目句**：首字属数字集；**账目句 = 同时含 `账|钱|两|百` 之一与 `平|对|算` 之一** ⇒ 落 `c3b`。
    ⇒ `三两七钱，对上了` **属账目句 ⇒ c3b，不进 c3a**。
- `c3b_other_nominal`：其余 ③ 片段。
- 输出另给 `c3a_share` / `c3b_share`（各占 `blocks_total`）。

指标（输出字段固定）
--------------------
* `ba_na_rate` = ① 的 share = `count(c1_penal) / blocks_total`  ← 主判据之一
* `head_entropy` = 六类分布的香农熵（bit）
* `normalized_entropy` = `head_entropy / log2(6)`
* `max_head_share` = 单类最高 share
* `h4` = **按旧 4 类**（`把` / `拿·用` / `动作起句（旧 10 前缀）` / `其他`）算的计数与 `ba_na_rate`，
  **仅供与 `d9m-syntax-slot-monotony.md` 对账，不参与判定**

可复算三件（stdout 与 `--out` 都打印）
--------------------------------------
`instrument_sha256`（本文件自身）、`log_sha256`（输入 `run.jsonl`）、`arm`。

用法
----
    python3 tools/d9s/syntax_shape.py --log <run.jsonl> [--arm ON|OFF] \
        [--out <path.json>] [--split-family] [--selftest]

  --split-family  另报「可归族 / 不可归族」两侧（复用 `assign_family`），**仅供与 D9m 已登记值对账**
  --selftest      ≥12 条手工片段覆盖六类（含跨类边界），断言各类计数与 H6

只读 `run.jsonl`；只在 `--out` 时写一个 JSON。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools" / "d5"))

from dialogue_metrics import extract_messages  # noqa: E402

NF_PATH = REPO / "tools" / "d9n" / "narration_family.py"
DEFAULT_LEXICON = REPO / "tools" / "d9n" / "narration_family_lexicon.json"

#: 六类（输出顺序；判定顺序见 PRIORITY）
CLASSES = ("c1_penal", "c2_sp", "c4_act", "c5_adv", "c6_interj", "c3_nominal")
#: 判定顺序：①→②→④→⑤→⑥→③（先命中先归）
PRIORITY = ("c1_penal", "c2_sp", "c4_act", "c5_adv", "c6_interj", "c3_nominal")

C1_CHARS = ("把", "拿", "用")
C2_RE = re.compile(r"^(?:他|她|P0\d\d)")
C4_RE = re.compile(r"^(?:抬手|伸手|低头|侧身|抬眼|蹲在|站在|掀开|手里|指腹|抬脚|欠身|弯下|俯身)")
C5_RE = re.compile(r"^(?:随手|顺手|先|又|刚|正|就|还|已|再|一|两)")
C6_RE = re.compile(r"^(?:嗯|哎|唉|哦|唔|嗨|嘿)")
SHORT_LEN = 6

#: ③ 子类常量（机械可判，不做语义判断）
C3A_TREND_END = ("下来", "出来", "起来", "上了", "过了", "开了", "过来", "回来")
C3A_LOC_START = ("灶上", "院里", "门口", "屋里", "桌上", "窗", "墙", "地上", "门槛", "街口")
C3_DIGITS = set("一二三四五六七八九十百千两零") | set("0123456789")
C3_ACCOUNT_CHARS = set("账钱两百")
C3_ACCOUNT_MARK = set("平对算")
C3_FIRST_CLAUSE_RE = re.compile(r"^[^，,。；;：:]*")

#: 旧 4 类（`h4` 对账专用）：与 `d9m-syntax-slot-monotony.md` §1 内联口径一致（只按首字）
H4_ACT_RE = re.compile(r"^(?:抬手|伸手|低头|侧身|抬眼|蹲在|站在|掀开|手里|指腹)")
H4_CLASSES = ("ba", "na", "act", "other")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_nf():
    """按路径导入 narration_family（不复制其提取/归族逻辑）。"""
    import importlib.util

    spec = importlib.util.spec_from_file_location("narration_family_d9s", NF_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.argv = ["narration_family"]
    spec.loader.exec_module(mod)
    return mod


def classify(inner: str) -> str:
    """六类判定，顺序 ①→②→④→⑤→⑥→③，先命中先归。"""
    s = (inner or "").strip()
    if not s:
        return "c6_interj"
    if s[0] in C1_CHARS:
        return "c1_penal"
    if C2_RE.match(s):
        return "c2_sp"
    if C4_RE.match(s):
        return "c4_act"
    if C5_RE.match(s):
        return "c5_adv"
    if C6_RE.match(s) or len(s) <= SHORT_LEN:
        return "c6_interj"
    return "c3_nominal"


def classify_h4(inner: str) -> str:
    """旧 4 类（仅对账）：把 / 拿·用 / 动作起句(旧 10 前缀) / 其他。"""
    s = (inner or "").strip()
    if not s:
        return "other"
    if s[0] == "把":
        return "ba"
    if s[0] in ("拿", "用"):
        return "na"
    if H4_ACT_RE.match(s):
        return "act"
    return "other"


def classify_c3(inner: str) -> str:
    """③ 子类：c3a_result_first / c3b_other_nominal（仅对已归 ③ 的片段调用）。"""
    s = (inner or "").strip()
    if not s:
        return "c3b_other_nominal"
    head = C3_FIRST_CLAUSE_RE.match(s).group(0)
    has_comma = bool(re.search(r"[，,]", s))
    if s[0] in C3_DIGITS:
        is_account = bool(set(s) & C3_ACCOUNT_CHARS) and bool(set(s) & C3_ACCOUNT_MARK)
        return "c3b_other_nominal" if is_account else "c3a_result_first"
    head_not_subject = not re.match(r"^(?:他们|她们|咱们|他|她|它|我|你)", head)
    result_marker = (head.endswith(C3A_TREND_END) or head.endswith(("了", "着"))
                     or ("了" in head) or ("着" in head))
    if has_comma and head_not_subject and result_marker:
        return "c3a_result_first"
    if s.startswith(C3A_LOC_START) and "了" in head:
        return "c3a_result_first"
    return "c3b_other_nominal"


def entropy_bits(counts: Counter, total: int) -> float:
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c:
            p = c / total
            h -= p * math.log2(p)
    return h


def measure(log_path: Path, arm: str, split_family: bool) -> dict:
    nf = load_nf()
    msgs = extract_messages(nf.read_log(log_path))

    c6 = Counter()
    c3sub = Counter()
    c4old = Counter()
    blocks_total = 0
    fam6 = {"assigned": Counter(), "unassigned": Counter()}
    fam_old = {"assigned": Counter(), "unassigned": Counter()}
    fam_n = {"assigned": 0, "unassigned": 0}
    lex = v = parts = objs = None
    if split_family:
        lex = nf.load_lexicon(DEFAULT_LEXICON)
        v = nf.v_judge(lex)
        parts = list(lex["parts_6"])
        objs = list(lex["objs_13"])

    for m in msgs:
        body = m.get("body") or ""
        for block in nf.PAIRED_RE.findall(body):
            inner = block[1:-1]
            if not inner.strip():
                continue
            blocks_total += 1
            k6 = classify(inner)
            k4 = classify_h4(inner)
            c6[k6] += 1
            if k6 == "c3_nominal":
                c3sub[classify_c3(inner)] += 1
            c4old[k4] += 1
            if split_family:
                asg = nf.assign_family(inner, v, parts, objs)
                side = "assigned" if asg["assigned"] else "unassigned"
                fam6[side][k6] += 1
                fam_old[side][k4] += 1
                fam_n[side] += 1

    def pack6(c: Counter, total: int) -> dict:
        shares = {k: (c.get(k, 0) / total if total else 0.0) for k in CLASSES}
        hb = entropy_bits(c, total)
        n_nonempty = sum(1 for k in CLASSES if c.get(k, 0) > 0)
        return {
            "blocks_total": total,
            "count": {k: c.get(k, 0) for k in CLASSES},
            "share": {k: round(x, 6) for k, x in shares.items()},
            "ba_na_rate": round(shares["c1_penal"], 6),
            "head_entropy": round(hb, 6),
            "normalized_entropy": round(hb / math.log2(len(CLASSES)), 6) if total else 0.0,
            "max_head_share": round(max(shares.values()) if total else 0.0, 6),
            # 非空类数 + 以非空类为分母的归一化（诊断用；判定仍用 normalized_entropy）
            "n_nonempty_classes": n_nonempty,
            "normalized_entropy_nonempty": (round(hb / math.log2(n_nonempty), 6)
                                            if total and n_nonempty else 0.0),
            # ③ 的子类（Leader 2026-10-30 追加）：c3a=c3_nominal 中未被判为 c3b 的部分
            "c3_count": {
                "c3a_result_first": c3sub.get("c3a_result_first", 0),
                "c3b_other_nominal": c3sub.get("c3b_other_nominal", 0),
            },
            "c3a_share": round(c3sub.get("c3a_result_first", 0) / total, 6) if total else 0.0,
            "c3b_share": round(c3sub.get("c3b_other_nominal", 0) / total, 6) if total else 0.0,
        }

    def pack4(c: Counter, total: int) -> dict:
        shares = {k: (c.get(k, 0) / total if total else 0.0) for k in H4_CLASSES}
        return {
            "blocks_total": total,
            "count": {k: c.get(k, 0) for k in H4_CLASSES},
            "share": {k: round(x, 6) for k, x in shares.items()},
            "ba_na_rate": round(shares["ba"] + shares["na"], 6),
            "note": "旧 4 类口径，仅与 d9m-syntax-slot-monotony.md 对账，不参与判定",
        }

    six = pack6(c6, blocks_total)
    out = {
        "instrument": "tools/d9s/syntax_shape.py",
        "instrument_sha256": sha256_file(Path(__file__).resolve()),
        "log": str(log_path),
        "log_sha256": sha256_file(log_path),
        "arm": arm,
        "msgs_total": len(msgs),
        "class_order": list(CLASSES),
        "classification_priority": list(PRIORITY),
        "six_class": six,
        "h4": pack4(c4old, blocks_total),
    }
    out.update({
        "blocks_total": six["blocks_total"],
        "ba_na_rate": six["ba_na_rate"],
        "head_entropy": six["head_entropy"],
        "normalized_entropy": six["normalized_entropy"],
        "max_head_share": six["max_head_share"],
        "c3a_share": six["c3a_share"],
        "c3b_share": six["c3b_share"],
    })
    if split_family:
        out["family_split"] = {
            "note": "仅与 d9m 已登记值对账；不改变主读数口径",
            "assigned": {"six": pack6(fam6["assigned"], fam_n["assigned"]),
                         "h4": pack4(fam_old["assigned"], fam_n["assigned"])},
            "unassigned": {"six": pack6(fam6["unassigned"], fam_n["unassigned"]),
                           "h4": pack4(fam_old["unassigned"], fam_n["unassigned"])},
        }
    return out


#: 自测：15 条，覆盖六类 + 跨类边界（`先把话说完`：⑤ 命中而非 ⑥，因 ⑤ 优先于 ⑥）
SELFTEST = [
    ("把袖口往上挽了一截", "c1_penal"),
    ("拿算盘珠子拨回原位", "c1_penal"),
    ("用袖口抹了抹额角", "c1_penal"),
    ("他伸手去够那根麻绳", "c2_sp"),
    ("她低头看了看鞋尖", "c2_sp"),
    ("P013抬眼扫了一圈", "c2_sp"),
    ("抬手把灯芯挑亮", "c4_act"),
    ("蹲在门槛上数蚂蚁", "c4_act"),
    ("欠身把凳子挪开", "c4_act"),
    ("先把话说完", "c5_adv"),
    ("又添了一勺水", "c5_adv"),
    ("嗯", "c6_interj"),
    ("顿了顿", "c6_interj"),
    ("灶上的汤滚了两滚", "c3_nominal"),
    ("木花卷着落下来", "c3_nominal"),
]
EXPECT_COUNT = {"c1_penal": 3, "c2_sp": 3, "c4_act": 3, "c5_adv": 2, "c6_interj": 2, "c3_nominal": 2}
EXPECT_H = 2.5559126
EXPECT_HN = 0.9887617
EXPECT_BANA = 0.2
EXPECT_MAX = 0.2


#: ③ 子类自测（≥6 条，含 `三两七钱，对上了` 必须落 c3b 的边界）
SELFTEST_C3 = [
    ("木花卷着落下来，刨子还在推", "c3a_result_first"),
    ("锅里那股焦香先冒出来，他掀了盖", "c3a_result_first"),
    ("门轴响了一声，他抬头", "c3a_result_first"),
    ("灶台上落了一层灰，他没动", "c3a_result_first"),
    ("三两七钱，对上了", "c3b_other_nominal"),
    ("屋里的灯灭了，他还在写", "c3a_result_first"),
    ("案板上的面醒得正好", "c3b_other_nominal"),
]


def selftest() -> int:
    counts = Counter()
    fails = []
    for text, want in SELFTEST:
        got = classify(text)
        counts[got] += 1
        if got != want:
            fails.append({"fragment": text, "expect": want, "got": got})
    total = len(SELFTEST)
    hb = entropy_bits(counts, total)
    hn = hb / math.log2(len(CLASSES))
    shares = {k: counts.get(k, 0) / total for k in CLASSES}
    got_count = {k: counts.get(k, 0) for k in CLASSES}
    ok = (
        not fails
        and got_count == EXPECT_COUNT
        and abs(hb - EXPECT_H) < 1e-5
        and abs(hn - EXPECT_HN) < 1e-5
        and abs(shares["c1_penal"] - EXPECT_BANA) < 1e-9
        and abs(max(shares.values()) - EXPECT_MAX) < 1e-9
    )
    # ③ 子类断言
    c3_fails = []
    c3_counts = Counter()
    for text, want in SELFTEST_C3:
        six_cls = classify(text)
        if six_cls != "c3_nominal":
            c3_fails.append({"fragment": text, "expect_six": "c3_nominal", "got_six": six_cls})
            continue
        got = classify_c3(text)
        c3_counts[got] += 1
        if got != want:
            c3_fails.append({"fragment": text, "expect": want, "got": got})
    expect_c3 = {"c3a_result_first": 5, "c3b_other_nominal": 2}   # 7 条子类样本
    c3_ok = (not c3_fails
             and {k: c3_counts.get(k, 0) for k in expect_c3} == expect_c3)
    ok = ok and c3_ok

    print(json.dumps({
        "selftest": "PASS" if ok else "FAIL",
        "n": total,
        "c3_subtest": {
            "n": len(SELFTEST_C3),
            "count": {k: c3_counts.get(k, 0) for k in ("c3a_result_first", "c3b_other_nominal")},
            "expect_count": expect_c3,
            "mismatches": c3_fails,
        },
        "count": got_count,
        "expect_count": EXPECT_COUNT,
        "ba_na_rate": round(shares["c1_penal"], 6),
        "head_entropy": round(hb, 7),
        "normalized_entropy": round(hn, 7),
        "max_head_share": round(max(shares.values()), 6),
        "mismatches": fails,
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D9s 冻结仪器：六类起首定稿 / 把·拿·用占比 / H6 熵",
        epilog=("六类：①把·拿·用(首字∈{把,拿,用}) ②主谓(^他|她|P0dd) "
                "④手部动作(^抬手|伸手|低头|侧身|抬眼|蹲在|站在|掀开|手里|指腹|抬脚|欠身|弯下|俯身) "
                "⑤副词·时间(^先|又|刚|正|就|还|已|再|随手|顺手|一|两) ⑥语气短句·其他(^嗯|哎|唉|哦|唔|嗨|嘿 或 长度≤6) "
                "③名词性·结果先行(不属于其他五类 且 长度>6)；判定顺序 ①→②→④→⑤→⑥→③（先命中先归）。"),
    )
    ap.add_argument("--log")
    ap.add_argument("--arm", default="UNKNOWN")
    ap.add_argument("--out")
    ap.add_argument("--split-family", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.log:
        ap.error("--log 必填（或使用 --selftest）")

    res = measure(Path(a.log), a.arm, a.split_family)
    text = json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
