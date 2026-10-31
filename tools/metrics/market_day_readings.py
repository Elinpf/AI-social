#!/usr/bin/env python3
"""market_day_readings.py —— market-day 臂（CYCLE-44）**只读**读数器（零 LLM）。

仓库内目标路径：`tools/metrics/market_day_readings.py`
判据词表真源：`tools/metrics/market_day_lexicon.json`（**判据词表/负例表全部外置，不在本文件硬编码**）

纪律（对齐 tools/metrics/weather_readings.py、v2/evidence/r37_readings.py）：
  - 只读 `run.jsonl`（+ 词表 + 可选人工标注），不 import `code/`、不写 run 目录、不改运行时源码；
  - 输出里附**词表文件与标注文件的 sha256**（可冻结、可对表）；
  - 输出 JSON + Markdown 两份；措辞只有预登记的判定映射，不写"提升/改善"。

三档口径（T1b 审计裁决：原式假阳性 69.2%，已否决）：
  R_A 显式日历档 → 只作「注入被采纳」探针
  R_B 时间邻接档 → **主判据**
  R_C 宽档（原式） → 仅作召回探索

用法（任意目录可跑，一行命令）：
  python3 tools/metrics/market_day_readings.py --selftest
  python3 tools/metrics/market_day_readings.py \
      --arm off=<off>/run.jsonl --arm on=<on>/run.jsonl \
      --json v2/evidence/cycle44_market_readings.json \
      --md   v2/evidence/cycle44_market_readings.md
  ... --subset market|nonmarket|all|both      # both=集日/非集日分列（默认）
  ... --labels tools/metrics/market_day_labels_baseline13.json   # 算真阳/假阳

退出码：0 正常；2 参数/文件错；3 词表自检失败。
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

MSG_TYPES = {"MSG_PUBLIC", "MSG_DM", "MSG_PRIVATE", "MSG"}
DEFAULT_LEXICON = Path(__file__).resolve().parent / "market_day_lexicon.json"


# ------------------------------------------------------------------ 工具
def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def wilson(k: int, n: int, z: float = 1.959964) -> list[float]:
    """Wilson 95% 区间（与仓库其余读数器同式）。"""
    if n <= 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, c - h), min(1.0, c + h)]


# ------------------------------------------------------------------ 词表（外置 JSON）
class Lexicon:
    def __init__(self, path: Path):
        self.path = path
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.raw = raw
        self.version = raw["version"]
        mk, tw = raw["market_words_re"], raw["time_words_re"]
        cal = raw["calibers"]
        self.R_A = re.compile(cal["R_A"]["re"])
        self.R_B = re.compile(cal["R_B"]["re_template"].format(TW=tw, MK=mk))
        self.R_C = re.compile(cal["R_C"]["re"])
        self.hard_negatives = [(d["name"], re.compile(d["re"])) for d in raw["hard_negatives"]]
        self.negation = re.compile(raw.get("negation_re") or r"(?!x)x")
        self.dropped_tokens = list((raw.get("dropped_tokens") or {}).keys())
        rule = (raw.get("market_day_rule") or {}).get("params") or {}
        self.market_every = int(rule.get("every", 3))
        self.market_offset = int(rule.get("offset", 0))
        self.sha256 = sha256_of(path)

    def classify(self, body: str) -> dict:
        flags = [name for name, rx in self.hard_negatives if rx.search(body)]
        r_a = bool(self.R_A.search(body))
        r_b_raw = bool(self.R_B.search(body))
        r_c = bool(self.R_C.search(body))
        r_b = bool(r_b_raw and not flags)          # 主判据：邻接 + 非硬负例
        negated = bool(self.negation.search(body))
        return {"hit_R_A": r_a, "hit_R_B_raw": r_b_raw, "hit_R_B": r_b, "hit_R_C": r_c,
                "flags": flags, "polarity": (-1 if negated else 1) if r_b else 0}


# ------------------------------------------------------------------ 扫描
def _blank() -> dict:
    return {"msgs": 0, "hit_R_A": 0, "hit_R_B": 0, "hit_R_B_raw": 0, "hit_R_C": 0,
            "pos": 0, "neg": 0, "cells": set(), "cells_hit": set(),
            "by_day": Counter(), "by_day_hit": Counter()}


def scan_run(path: Path, lex: Lexicon, every: int, offset: int) -> dict:
    acc = {"msgs_all": 0, "market": _blank(), "nonmarket": _blank(),
           "flags": Counter(), "hits": []}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
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
            body = p.get("body") or ""
            if not body:
                continue
            day = p.get("day")
            acc["msgs_all"] += 1
            key = "market" if (isinstance(day, int) and day % every == offset) else "nonmarket"
            sub = acc[key]
            sub["msgs"] += 1
            sub["by_day"][day] += 1
            sub["cells"].add((e.get("actor"), day))
            c = lex.classify(body)
            for k in ("hit_R_A", "hit_R_B", "hit_R_B_raw", "hit_R_C"):
                if c[k]:
                    sub[k] += 1
            if c["hit_R_B"]:
                sub["by_day_hit"][day] += 1
                sub["cells_hit"].add((e.get("actor"), day))
                sub["pos" if c["polarity"] > 0 else "neg"] += 1
            for fl in c["flags"]:
                acc["flags"][fl] += 1
            if c["hit_R_C"]:
                acc["hits"].append({
                    "seq": e.get("seq"), "day": day, "actor": e.get("actor"),
                    "msg_id": p.get("msg_id"), "msg_uid": p.get("msg_uid"), "subset": key,
                    "hit_R_A": c["hit_R_A"], "hit_R_B": c["hit_R_B"],
                    "hit_R_B_raw": c["hit_R_B_raw"], "hit_R_C": c["hit_R_C"],
                    "polarity": c["polarity"],
                    "flags": c["flags"], "text": body})
    return acc


# ------------------------------------------------------------------ 人工标注 → TP/FP
def apply_labels(acc: dict, arm: str, labels: dict | None) -> dict | None:
    if not labels:
        return None
    by_key = {it["key"]: it for it in (labels.get("items") or [])}
    tp = fp = unlabeled = 0
    detail = []
    for h in acc["hits"]:
        k = f"{arm}|{h['seq']}"
        it = by_key.get(k)
        if not it:
            unlabeled += 1
            continue
        if it["label"] == "TP":
            tp += 1
        else:
            fp += 1
        detail.append({"key": k, "label": it["label"], "kind": it.get("kind"),
                       "hit_R_B": h["hit_R_B"], "hit_R_C": h["hit_R_C"]})
    n = tp + fp
    return {"labels_version": labels.get("version"), "n_labeled": n, "tp": tp, "fp": fp,
            "fp_rate": (fp / n) if n else None, "unlabeled_hits": unlabeled, "detail": detail}


# ------------------------------------------------------------------ 汇总
def _block(sub: dict) -> dict:
    n = sub["msgs"]
    return {
        "denominator_msgs": n,
        "main_R_B": {"num": sub["hit_R_B"], "den": n,
                     "rate": (sub["hit_R_B"] / n) if n else None,
                     "wilson95": wilson(sub["hit_R_B"], n)},
        "probe_R_A": {"num": sub["hit_R_A"], "den": n,
                      "rate": (sub["hit_R_A"] / n) if n else None,
                      "wilson95": wilson(sub["hit_R_A"], n)},
        "explore_R_C": {"num": sub["hit_R_C"], "den": n,
                        "rate": (sub["hit_R_C"] / n) if n else None},
        "narrative_R_B_raw": {"num": sub["hit_R_B_raw"], "den": n},
        "polarity": {"positive": sub["pos"], "negated": sub["neg"]},
        "dedup": {"cells": len(sub["cells"]), "cells_with_hit": len(sub["cells_hit"]),
                  "rate_cell_level": (len(sub["cells_hit"]) / len(sub["cells"]))
                  if sub["cells"] else None},
        "by_day": {str(d): {"msgs": sub["by_day"][d], "hit": sub["by_day_hit"][d]}
                   for d in sorted(sub["by_day"], key=lambda x: (x is None, x))},
    }


def summarize_arm(name: str, acc: dict, lex: Lexicon, labels: dict | None,
                  labels_path: str | None, arm_path: Path) -> dict:
    out = {
        "arm": name,
        "run_jsonl": str(arm_path),
        "run_sha256": sha256_of(arm_path),
        "lexicon": {"version": lex.version, "path": str(lex.path), "sha256": lex.sha256},
        "labels": ({"path": labels_path, "sha256": sha256_of(Path(labels_path)),
                    "version": (labels or {}).get("version")} if labels_path else None),
        "msgs_all": acc["msgs_all"],
        "market": _block(acc["market"]),
        "nonmarket": _block(acc["nonmarket"]),
        "hard_negative_flags": dict(acc["flags"]),
        "dropped_tokens": lex.dropped_tokens,
        "hit_detail_R_C": acc["hits"][:60],
    }
    lab = apply_labels(acc, name, labels)
    if lab:
        out["tp_fp"] = lab
    return out


def compare(off: dict, on: dict, key: str) -> dict:
    a, b = off[key]["main_R_B"], on[key]["main_R_B"]
    if not (a["den"] and b["den"]):
        return {"subset": key, "verdict": "CANNOT-JUDGE（分母为 0）"}
    delta = b["rate"] - a["rate"]
    lo_a, hi_a = a["wilson95"]
    lo_b, hi_b = b["wilson95"]
    overlap = not (lo_b > hi_a or lo_a > hi_b)
    if a["num"] == 0 and b["num"] == 0:
        v = "两臂 R_B 命中均为 0：只能报『注入未被台词采纳』，不得判机制无效。"
    elif delta >= 0.05 and not overlap:
        v = "Δ≥+5.0pp 且 CI 不重叠 ⇒ 判『成立（仅限本构念与本规模）』。"
    elif delta >= 0.05 and overlap:
        v = "方向达标但 CI 重叠 ⇒ 判『不可分（统计不足）』，不得写成成立。"
    elif delta > 0:
        v = "Δ<+5.0pp ⇒ 判『未达阈值』。"
    else:
        v = "Δ≤0 ⇒ 判『未达阈值（方向为负）』。"
    return {"subset": key, "delta_pp": round(delta * 100, 2),
            "off_rate_pct": round(a["rate"] * 100, 2), "on_rate_pct": round(b["rate"] * 100, 2),
            "off_wilson95_pct": [round(lo_a * 100, 2), round(hi_a * 100, 2)],
            "on_wilson95_pct": [round(lo_b * 100, 2), round(hi_b * 100, 2)],
            "ci_overlap": overlap, "verdict": v,
            "reading_rule": "Δ 与 CI 只描述『集日提及率』之差；不描述生活气息、不描述行为。"}


# ------------------------------------------------------------------ Markdown
def to_markdown(res: dict) -> str:
    L = ["# market-day 读数（自动生成，勿手改）", ""]
    first = next(iter(res["arms"].values()))
    lx = first["lexicon"]
    L += [f"- 词表：`{lx['version']}`　sha256 `{lx['sha256']}`",
          f"- 词表文件：`{lx['path']}`",
          "- 集日定义：`" + res["subset"]["rule"] + f"`（every={res['subset']['market_every']}, "
          f"offset={res['subset']['market_offset']}）",
          "- 口径：主判据 `R_B`（时间邻接 + 硬负例）；`R_A` 探针；`R_C` 仅探索（已否决）", "",
          "## 各臂读数（集日 / 非集日分列）", "",
          "| 臂 | 子集 | 分母 MSG | **R_B** | R_B 率 | Wilson 95% | R_A | R_C | 阳性/否定 | 去重单元(命中/总) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for name, arm in res["arms"].items():
        for key, label in (("market", "集日"), ("nonmarket", "非集日")):
            b = arm[key]
            mb = b["main_R_B"]
            rate = "-" if mb["rate"] is None else f"{mb['rate']*100:.2f}%"
            ci = f"[{mb['wilson95'][0]*100:.2f}%, {mb['wilson95'][1]*100:.2f}%]"
            L.append(f"| {name} | {label} | {mb['den']} | **{mb['num']}** | {rate} | {ci} | "
                     f"{b['probe_R_A']['num']} | {b['explore_R_C']['num']} | "
                     f"{b['polarity']['positive']}/{b['polarity']['negated']} | "
                     f"{b['dedup']['cells_with_hit']}/{b['dedup']['cells']} |")
    L.append("")
    if "pair" in res:
        L += ["## 两臂对照（主判据）", ""]
        for p in res["pair"]:
            L.append(f"- **{p['subset']}**：off {p.get('off_rate_pct')}% → on {p.get('on_rate_pct')}%，"
                     f"Δ **{p.get('delta_pp')}pp**，CI {'重叠' if p.get('ci_overlap') else '不重叠'} ⇒ {p.get('verdict')}")
        L.append("")
    tps = [(n, a["tp_fp"]) for n, a in res["arms"].items() if "tp_fp" in a]
    if tps:
        L += ["## 人工标注对表（真阳/假阳，仅覆盖已标注命中）", "",
              "| 臂 | 已标注 | TP | FP | 假阳性率 | 未标注命中 |", "|---|---|---|---|---|---|"]
        for n, t in tps:
            fr = "-" if t["fp_rate"] is None else f"{t['fp_rate']*100:.1f}%"
            L.append(f"| {n} | {t['n_labeled']} | {t['tp']} | {t['fp']} | {fr} | {t['unlabeled_hits']} |")
        L.append("")
    L += ["## 硬负例剔除计数", ""]
    for name, arm in res["arms"].items():
        L.append(f"- {name}: `{json.dumps(arm['hard_negative_flags'], ensure_ascii=False)}`")
    L += ["", f"## 已从判据剔除的 token", f"`{'`, `'.join(first['dropped_tokens'])}`", ""]
    return "\n".join(L)


# ------------------------------------------------------------------ 自检
def selftest(lex: Lexicon) -> int:
    cases = [
        ("（拿围裙角蹭了蹭手）我这会儿得去集上把最后两筐青椒清了", False),
        ("这两天铺子前头挤得跟赶集似的", False),
        ("她上回为半垄菜地能追到集上骂三条街", False),
        ('你刚说"赶集"，我倒想起桂香家那口子', False),
        ("布角还沾着今早集上的泥点子", True),
        ("今早那趟集上碰见你三叔", True),
        ("那两把葱我按集上价给你", False),
        ("他娘今儿又没来集上", True),
        ("我刚从集上拎了半袋新茶回来", False),
        ("买点盐，回头再买些菜", False),
        ("明天逢集，得早点去占位", True),
    ]
    bad = 0
    for text, expect in cases:
        got = lex.classify(text)["hit_R_B"]
        if got != expect:
            print(f"  SELFTEST FAIL: expect={expect} got={got} :: {text}", file=sys.stderr)
            bad += 1
    if lex.R_A.search("今早集上"):
        print("  SELFTEST FAIL: R_A 不应命中『今早集上』", file=sys.stderr)
        bad += 1
    print(f"selftest: {len(cases)+1-bad}/{len(cases)+1} passed | lexicon={lex.version} "
          f"sha256={lex.sha256[:16]}")
    return 0 if bad == 0 else 3


# ------------------------------------------------------------------ main
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="market-day 臂只读读数器（零 LLM，词表外置）")
    ap.add_argument("--arm", action="append", default=[], help="name=path/to/run.jsonl（可给两次）")
    ap.add_argument("--lexicon", default=str(DEFAULT_LEXICON), help="判据词表 JSON 路径")
    ap.add_argument("--labels", default=None, help="人工标注 JSON（算 TP/FP）")
    ap.add_argument("--json", dest="json_out", default=None)
    ap.add_argument("--md", dest="md_out", default=None)
    ap.add_argument("--subset", choices=["market", "nonmarket", "all", "both"], default="both")
    ap.add_argument("--market-every", type=int, default=None)
    ap.add_argument("--market-offset", type=int, default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    lex_path = Path(args.lexicon)
    if not lex_path.exists():
        print(f"FATAL: 找不到词表 {lex_path}", file=sys.stderr)
        return 2
    lex = Lexicon(lex_path)
    if args.selftest:
        return selftest(lex)

    every = args.market_every if args.market_every is not None else lex.market_every
    offset = args.market_offset if args.market_offset is not None else lex.market_offset

    labels = None
    if args.labels:
        lp = Path(args.labels)
        if not lp.exists():
            print(f"FATAL: 找不到标注文件 {lp}", file=sys.stderr)
            return 2
        labels = json.loads(lp.read_text(encoding="utf-8"))

    if not args.arm:
        ap.error("至少给一个 --arm name=path")

    arms, order = {}, []
    for spec in args.arm:
        if "=" not in spec:
            ap.error(f"--arm 需 name=path 形式：{spec}")
        name, path = spec.split("=", 1)
        p = Path(path)
        if not p.exists():
            print(f"FATAL: 找不到 {p}", file=sys.stderr)
            return 2
        acc = scan_run(p, lex, every, offset)
        arms[name] = summarize_arm(name, acc, lex, labels, args.labels, p)
        order.append(name)

    res = {"lexicon_version": lex.version,
           "subset": {"mode": args.subset, "market_every": every, "market_offset": offset,
                      "rule": "集日 = day % every == offset"},
           "arms": arms}
    if len(order) == 2:
        res["pair"] = [compare(arms[order[0]], arms[order[1]], k) for k in ("market", "nonmarket")]
        res["pair_note"] = f"{order[0]} → {order[1]}"

    text = json.dumps(res, ensure_ascii=False, indent=1, default=str)
    if args.json_out:
        Path(args.json_out).write_text(text, encoding="utf-8")
    if args.md_out:
        Path(args.md_out).write_text(to_markdown(res), encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
