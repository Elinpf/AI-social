#!/usr/bin/env python3
"""repeat_metric_guard.py —— 重复率类指标的「暴露面 / 同口径」可比性校验（核验方工具）。

背景（D9i 实证）
----------------
`L-7_dup_ngram8_rate` 的定义是「**与任一其他 MSG 共享 ≥1 个归一后 8-gram 的 MSG 数 / 总 MSG 数**」。
分子取决于「能否在别处找到同一 8-gram」，因此**任一条目变长都会抬高其他条目的命中率**
（双向碰撞）。D9i 的旁白通道把 body 平均长度抬了 +41.5%，`L-7` 表面 +7.33pp；
但把新增载体（括注旁白）剥掉后重算，`L-7` 反而**低于**对照臂 —— 说明那是**暴露面效应**，
不是质量下降。

本工具做两件事
-------------
1. **暴露面**：body 平均字符长度、字符总数、8-gram 总数、平均 8-gram/条、候选池大小（MSG 数）；
2. **同口径重算**：剥除「新增载体」（默认＝成对全角/半角括号内的旁白）后，重算 `L-7` 与暴露面；

并据预登记的固定阈值给出 `PASS / WARN-暴露面效应 / FAIL`。

设计约束（写死）
---------------
* **只读**：只读入参 `run.jsonl`，不写任何日志、不改引擎、不 import `life.*`（只复用官方指标模块的归一函数）；
* **不改判据**：`normalize_body` / 8-gram / 去重口径一律**直接调用** `tools/d5/dialogue_metrics.py`，
  本工具**不重新实现** L-7，避免口径漂移；
* **确定性**：同一输入多次运行输出逐字节相同（无随机、无时间戳）。

用法
----
    python tools/metrics/repeat_metric_guard.py \
        --off v2/evidence/narr-off-20261030/run.jsonl \
        --on  v2/evidence/narr-on-20261030/run.jsonl \
        [--strip 'bracket'] [--json out.json]

退出码：PASS=0，WARN=0，FAIL=1（便于 CI 直接当闸门用）。
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

# ---- 官方指标口径（不重新实现）------------------------------------------------
_TOOLS_D5 = Path(__file__).resolve().parents[1] / "d5"
if str(_TOOLS_D5) not in sys.path:
    sys.path.insert(0, str(_TOOLS_D5))
from dialogue_metrics import normalize_body  # noqa: E402  （官方归一，L-7 的前置）

NGRAM = 8

# ---- 阈值（预登记，写死；改动必须另立预登记）----------------------------------
RAW_DIFF_GATE_PP = 5.0     # L-7 原始差 > +5pp 才需要考虑"代价"
SAME_DIFF_GATE_PP = 2.0    # 同口径差 < +2pp ⇒ 判为"暴露面效应"

PAIR_BRACKET = re.compile(r"[（(][^（）()]*[）)]")


def strip_narration(body: str) -> str:
    """剥掉**成对**括号及其内容（全角/半角都算，反复剥到稳定；未配对括号原样保留）。"""
    prev = None
    cur = body or ""
    while prev != cur:
        prev = cur
        cur = PAIR_BRACKET.sub("", cur)
    return cur.strip()


def load_msgs(path: str) -> list[str]:
    """从 run.jsonl 取全部 MSG 的 body（按 seq 出现顺序；只读）。"""
    out: list[str] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if '"MSG' not in line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not str(rec.get("type", "")).startswith("MSG"):
                continue
            payload = rec.get("payload") or {}
            out.append(payload.get("body") or "")
    return out


def l7(bodies: list[str]) -> dict:
    """按官方口径算 L-7 + 暴露面。

    L-7 = |{i: ∃j≠i, shingle_i ∩ shingle_j ≠ ∅}| / |MSG|
    """
    n = len(bodies)
    norm = [normalize_body(b) for b in bodies]
    shingles = [{t[i:i + NGRAM] for i in range(max(0, len(t) - NGRAM + 1))} for t in norm]
    index: dict[str, list[int]] = collections.defaultdict(list)
    for i, sh in enumerate(shingles):
        for g in sh:
            index[g].append(i)
    dup = {i for ids in index.values() if len(ids) > 1 for i in ids}
    total_chars = sum(len(b) for b in bodies)
    total_ngrams = sum(len(sh) for sh in shingles)
    return {
        "n_msgs": n,
        "dup_msgs": len(dup),
        "l7_rate": (len(dup) / n) if n else 0.0,
        "avg_chars": (total_chars / n) if n else 0.0,
        "total_chars": total_chars,
        "total_ngrams": total_ngrams,
        "avg_ngrams_per_msg": (total_ngrams / n) if n else 0.0,
        "pool_size": max(0, n - 1),   # 每条 MSG 可碰撞的对端数 = n−1（L-7 是"与任一**其他** MSG 共享 8-gram"）
    }


def verdict(raw_diff_pp: float, same_diff_pp: float) -> tuple[str, str]:
    """按预登记阈值给出判定（顺序即优先级）。"""
    if raw_diff_pp <= RAW_DIFF_GATE_PP:
        return "PASS", f"L-7 原始差 {raw_diff_pp:+.2f}pp ≤ +{RAW_DIFF_GATE_PP:.0f}pp"
    if same_diff_pp < SAME_DIFF_GATE_PP:
        return "WARN-暴露面效应", (
            f"L-7 原始差 {raw_diff_pp:+.2f}pp > +{RAW_DIFF_GATE_PP:.0f}pp，"
            f"但同口径差 {same_diff_pp:+.2f}pp < +{SAME_DIFF_GATE_PP:.0f}pp"
        )
    if same_diff_pp >= raw_diff_pp:
        return "FAIL", (
            f"L-7 原始差 {raw_diff_pp:+.2f}pp > +{RAW_DIFF_GATE_PP:.0f}pp 且"
            f"同口径差 {same_diff_pp:+.2f}pp 未下降 ⇒ 疑真实退化"
        )
    return "FAIL", (
        f"L-7 原始差 {raw_diff_pp:+.2f}pp > +{RAW_DIFF_GATE_PP:.0f}pp，"
        f"同口径差 {same_diff_pp:+.2f}pp ≥ +{SAME_DIFF_GATE_PP:.0f}pp ⇒ 无法归因于暴露面"
    )


def _identity(body: str) -> str:
    """`--strip none` 用的恒等变换（不剥任何载体）。"""
    return body


STRIP_MODES = {
    "bracket": strip_narration,     # 默认：剥成对全角/半角括号内的旁白
    "none": _identity,              # 不剥（同口径 ≡ 原始口径）
}


def analyse(off_path: str, on_path: str, strip: str | None = "bracket") -> dict:
    """算两臂的 `L-7` 原始差与同口径差，并给判定。

    `strip` 为**显式入参**（"bracket" / "none"），用于同口径重算；
    **不修改模块全局**，因此同一进程内可用不同 `strip` 反复调用 `analyse()` 而互不污染。
    """
    if strip not in STRIP_MODES:
        raise ValueError(f"未知 strip 模式：{strip!r}（可选 {sorted(STRIP_MODES)}）")
    strip_fn = STRIP_MODES[strip]

    off = load_msgs(off_path)
    on = load_msgs(on_path)

    off_m = l7(off)
    on_m = l7(on)

    # 同口径：剥除新增载体（两侧都剥；对照臂若无载体则数值不变）
    off_s = l7([strip_fn(b) for b in off])
    on_s = l7([strip_fn(b) for b in on])

    raw_pp = (on_m["l7_rate"] - off_m["l7_rate"]) * 100
    same_pp = (on_s["l7_rate"] - off_s["l7_rate"]) * 100
    v, why = verdict(raw_pp, same_pp)

    return {
        "off": {"raw": off_m, "same_caliber": off_s},
        "on": {"raw": on_m, "same_caliber": on_s},
        "diff": {
            "l7_raw_pp": raw_pp,
            "l7_same_caliber_pp": same_pp,
            "avg_chars_delta": on_m["avg_chars"] - off_m["avg_chars"],
            "avg_chars_delta_pct": ((on_m["avg_chars"] / off_m["avg_chars"] - 1) * 100) if off_m["avg_chars"] else 0.0,
            "total_ngrams_delta": on_m["total_ngrams"] - off_m["total_ngrams"],
            "total_ngrams_delta_pct": ((on_m["total_ngrams"] / off_m["total_ngrams"] - 1) * 100) if off_m["total_ngrams"] else 0.0,
        },
        "verdict": v,
        "reason": why,
        "thresholds": {
            "raw_diff_gate_pp": RAW_DIFF_GATE_PP,
            "same_diff_gate_pp": SAME_DIFF_GATE_PP,
            "ngram": NGRAM,
        },
    }


def render(res: dict) -> str:
    o, n, d = res["off"], res["on"], res["diff"]
    lines = []
    lines.append("== 暴露面（原始口径）==")
    hdr = f"{'臂':<6}{'MSG':>6}{'dup':>6}{'L-7':>10}{'body均长':>10}{'字符总数':>10}{'8-gram总数':>12}{'8-gram/条':>11}"
    lines.append(hdr)
    for name, m in (("off", o["raw"]), ("on", n["raw"])):
        lines.append(
            f"{name:<6}{m['n_msgs']:>6}{m['dup_msgs']:>6}{m['l7_rate']:>10.6f}"
            f"{m['avg_chars']:>10.2f}{m['total_chars']:>10}{m['total_ngrams']:>12}{m['avg_ngrams_per_msg']:>11.2f}"
        )
    lines.append("")
    lines.append("== 同口径重算（剥除成对括号载体后）==")
    lines.append(hdr)
    for name, m in (("off", o["same_caliber"]), ("on", n["same_caliber"])):
        lines.append(
            f"{name:<6}{m['n_msgs']:>6}{m['dup_msgs']:>6}{m['l7_rate']:>10.6f}"
            f"{m['avg_chars']:>10.2f}{m['total_chars']:>10}{m['total_ngrams']:>12}{m['avg_ngrams_per_msg']:>11.2f}"
        )
    lines.append("")
    lines.append("== 差异 ==")
    lines.append(f"L-7 原始差            : {d['l7_raw_pp']:+.2f}pp")
    lines.append(f"L-7 同口径差          : {d['l7_same_caliber_pp']:+.2f}pp")
    lines.append(f"body 平均长度差       : {d['avg_chars_delta']:+.2f} 字符 ({d['avg_chars_delta_pct']:+.2f}%)")
    lines.append(f"8-gram 总数差         : {d['total_ngrams_delta']:+d} ({d['total_ngrams_delta_pct']:+.2f}%)")
    lines.append("")
    t = res["thresholds"]
    lines.append(f"阈值：原始差 > +{t['raw_diff_gate_pp']:.0f}pp 触发核查；同口径差 < +{t['same_diff_gate_pp']:.0f}pp ⇒ 暴露面效应")
    lines.append(f"判定：{res['verdict']}  —— {res['reason']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="重复率类指标的暴露面/同口径可比性校验")
    ap.add_argument("--off", required=True, help="对照臂 run.jsonl")
    ap.add_argument("--on", required=True, help="处理臂 run.jsonl")
    ap.add_argument("--strip", default="bracket", choices=["bracket", "none"],
                    help="同口径重算时剥除的载体（默认 bracket=成对括号旁白；none=不剥）")
    ap.add_argument("--json", default=None, help="把结构化结果写到该路径（可选）")
    args = ap.parse_args(argv)
    res = analyse(args.off, args.on, strip=args.strip)
    print(render(res))
    if args.json:
        Path(args.json).write_text(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\n[json] {args.json}")
    return 1 if res["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
