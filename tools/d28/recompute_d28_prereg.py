#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recompute_d28_prereg.py —— D2.8 判据读数复算 / 裁决口径执行器（零跑批、零 LLM、只读 run.jsonl）

配套裁决文件：`v2/refs/D28-F2prime-resolution.md`
（该文件是 `batch-hosting-runbook.md` §3.103.2「出处只认三处」里的第 ③ 类：`v2/refs/` 下的独立修订文件）

它做什么：
  把预登记（`v2/refs/D28-prereg-narration-quota.md`）+ 修正案 1
  （`v2/refs/D28-amendment1-two-seed.md`）里那几张判据表，落成一个**可直接执行的读数器**：
  对每一臂，从 `run.jsonl` 现算主指标与代价项，**每个比率都打印分子 / 分母 / 分母为何是这个**，
  再按**裁决后的单一口径**（见 `D28-F2prime-resolution.md` §3）给出 PASS / FAIL / 待两 seed。

纪律：
  · 不自创口径、不自创词表：全部指标函数**原样 import** 自冻结读数器
    `v2/evidence/cycle21_recon/recompute_d27.py`（它内部又原样 import `v2/evidence/d12c_metrics.py::DETAIL`）。
    本脚本只做**组装 + 打印 + 判定**，不重写任何度量。
  · 纯函数、无随机、无时间戳、不联网 ⇒ 同输入两次运行输出逐字节相同
    （`top_shared` 之类受 hash 顺序影响的部分由冻结读数器自行排序，本脚本只取计数）。
  · 只读：不写 run 目录，只写 `--out-json` 指定的一个文件。

用法（在仓库根执行）：
  python3 tools/d28/recompute_d28_prereg.py \
      --C v2/evidence/run_d27_C_n16r60_seed42/run.jsonl \
      --B .worktrees/d28-narration-quota/v2/evidence/run_d28_B_n16r60_seed42/run.jsonl \
      --label B42 --out-json /tmp/d28_prereg_B42.json

  # 只算一臂（不做 C/B 差值判定）：
  python3 tools/d28/recompute_d28_prereg.py --B <run.jsonl> --label SOMEARM

退出码：0 = 读数算完（不等于"判据通过"）；2 = 输入不可读。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "v2" / "evidence" / "cycle21_recon" / "recompute_d27.py"

# ---- 裁决后的阈值（唯一出处：v2/refs/D28-F2prime-resolution.md §5；此处只是常量副本，改阈值必须改那份文件）----
TH = {
    "M1_paren_band": (25.0, 45.0),      # prereg:56 「落在 [25%,45%]，过高也算未达」
    "P1_len_floor": 40.0,               # prereg:57 / amendment1:29 「≥ C 的 100%（≥40.0）」，一票否决
    "P2_rel_min_pct": 10.0,             # prereg:58 / amendment1:30 「相对同 seed 的 C ↑≥10%」
    "Q1_L15_max_pp": 2.0,               # prereg:59 「↑≤2.0pp」（单侧上界，方向无歧义）
    "Q2_L7_max_pp": 5.0,                # 裁决：取 amendment1:23 的 5.0pp（原闸 3.0pp < 实测噪音 4.90pp）
    "Q3_F2_max_pp": 5.0,                # 裁决：取 amendment1:23 的 5.0pp（原闸 2.0pp < 实测噪音 2.94pp）
    "S_rel_max_pct": 10.0,              # prereg:62
    "cost_rel_max_pct": 10.0,           # prereg:63「llm_calls ≤ +10%，破只记录」
}


def load_frozen():
    spec = importlib.util.spec_from_file_location("recompute_d27", FROZEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def arm_readings(R, path: Path) -> dict:
    """一臂的全部读数：每个比率都带分子/分母。"""
    msgs = R.read_msgs(path)
    names = R.load_names()
    pl = R.paren_and_len(msgs)
    st = R.structural(msgs)
    p1p2 = R.p1_p2(msgs, names)
    l7 = R.l7_norm8(msgs)
    l15 = R.l15_restate(msgs)
    f2 = R.f2_content_drift(msgs)
    cst = R.cost(path)
    meta_p = path.parent / "meta.json"
    meta = json.load(open(meta_p, encoding="utf-8")) if meta_p.exists() else {}

    return {
        "path": str(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "wc_l": sum(1 for _ in open(path, "rb")),
        "meta": {k: meta.get(k) for k in (
            "seed", "rounds", "n", "provider", "model", "llm_calls", "degraded_calls",
            "started_at", "finished_at", "code_sha", "code_sha_end", "events", "run_sha256")},
        "readings": {
            "M1_paren_rate": {
                "num": pl["paren_lead_count"], "den": pl["n_msgs"],
                "pct": pl["paren_rate_pct"],
                "den_rule": "全部 MSG_DM/MSG_PUBLIC/MSG_GROUP；分子=body.lstrip() 以（或( 起头的条数（d12c_metrics:51）",
            },
            "P1_len_p50_excl": {
                "value": pl["len_p50_excl"], "den": pl["n_msgs"],
                "den_rule": "中位数，样本=全部 MSG_*（去括号块 + strip 后字符数；d12c_metrics:52）",
            },
            "P2_P1_count_mean": {
                "num": p1p2["P1_count_sum"], "den": p1p2["n_msgs"],
                "value": p1p2["P1_count_mean"],
                "den_rule": "num=DETAIL 词表正则 findall 次数总和；den=全部 MSG_*（连续口径，prereg:58）",
            },
            "S_n_msgs": {"value": st["n_msgs"], "den_rule": "MSG_DM+MSG_PUBLIC+MSG_GROUP 事件数"},
            "S_n_threads": {"value": st["n_threads_threadid"],
                            "den_rule": "thread_id 去重，缺失回退 legacy-<msg_uid>（d12c_metrics:53）"},
            "Q1_L15_restate_rate": {
                "num": l15["restate_count"], "den": l15["n_msgs"], "pct": l15["restate_rate_pct"],
                "den_rule": "分子=同线程内与本线程更早消息共享≥1 个 8-gram 的消息数；den=全部 MSG_*",
                "strong_pct": l15["restate_strong_rate_pct"], "strong_num": l15["restate_strong_count"],
            },
            "Q2_L7_norm8": {
                "num": l7["dup_msgs"], "den": l7["n_msgs"], "pct": l7["L7_dup_ngram8_rate_pct"],
                "den_rule": "分子=全批范围内与任一其它消息共享≥1 个 8-gram 的消息数；den=全部 MSG_*",
            },
            "Q3_F2_drift_rate": {
                "num": f2["drift_pairs"], "den": f2["denominator_adjacent_pairs"], "pct": f2["drift_rate_pct"],
                "den_rule": "分母=Σ(线程长度−1)（各线程相邻消息对数，**逐臂现算，禁止跨臂归一**）；"
                            "分子=char-bigram Jaccard<0.10 的相邻对数",
            },
            "cost_llm_calls": {
                "value": cst["llm_calls_total"], "meta_value": meta.get("llm_calls"),
                "den_rule": "run.jsonl 内 type==LLM_CALL 事件数；与 meta.llm_calls 双证",
            },
        },
    }


def _delta_pp(b, c, nd=4):
    return None if (b is None or c is None) else round(b - c, nd)


def _rel_pct(b, c):
    return None if (b is None or c is None or c == 0) else round(100.0 * (b - c) / c, 2)


def judge(C: dict, B: dict) -> list[dict]:
    """按裁决口径逐项判定。返回行列表（行 = 一个判据）。"""
    cr, br = C["readings"], B["readings"]
    rows = []

    # M1 区间带（双侧）
    c_m1, b_m1 = cr["M1_paren_rate"]["pct"], br["M1_paren_rate"]["pct"]
    lo, hi = TH["M1_paren_band"]
    rows.append({
        "id": "M1", "metric": "paren_rate",
        "C": f'{cr["M1_paren_rate"]["num"]}/{cr["M1_paren_rate"]["den"]} = {c_m1}%',
        "B": f'{br["M1_paren_rate"]["num"]}/{br["M1_paren_rate"]["den"]} = {b_m1}%',
        "delta": f"{_delta_pp(b_m1, c_m1, 2)} pp",
        "gate": f"∈[{lo}%,{hi}%]（双侧，过高也算未达）",
        "verdict": "PASS" if (b_m1 is not None and lo <= b_m1 <= hi) else "FAIL",
    })

    # P1 一票否决（单侧下界）
    c_p1, b_p1 = cr["P1_len_p50_excl"]["value"], br["P1_len_p50_excl"]["value"]
    rows.append({
        "id": "P1", "metric": "len_p50_excl",
        "C": str(c_p1), "B": str(b_p1),
        "delta": f"{_delta_pp(b_p1, c_p1)}（{_rel_pct(b_p1, c_p1)}%）",
        "gate": f"≥{TH['P1_len_floor']}（且 ≥ C 的 100%），一票否决",
        "verdict": "PASS" if (b_p1 is not None and b_p1 >= TH["P1_len_floor"] and b_p1 >= c_p1) else "FAIL",
    })

    # P2 相对增幅（单侧下界）
    c_p2, b_p2 = cr["P2_P1_count_mean"]["value"], br["P2_P1_count_mean"]["value"]
    rel = _rel_pct(b_p2, c_p2)
    rows.append({
        "id": "P2", "metric": "P1_count_mean（连续口径）",
        "C": f'{cr["P2_P1_count_mean"]["num"]}/{cr["P2_P1_count_mean"]["den"]} = {c_p2}',
        "B": f'{br["P2_P1_count_mean"]["num"]}/{br["P2_P1_count_mean"]["den"]} = {b_p2}',
        "delta": f"+{_delta_pp(b_p2, c_p2)}（{rel}%）",
        "gate": f"相对同 seed C ↑≥{TH['P2_rel_min_pct']}%",
        "verdict": "PASS" if (rel is not None and rel >= TH["P2_rel_min_pct"]) else "FAIL",
    })

    # S 结构（双侧 ±10%）
    for key, label in (("S_n_msgs", "n_msgs"), ("S_n_threads", "n_threads")):
        c_v, b_v = cr[key]["value"], br[key]["value"]
        rel = _rel_pct(b_v, c_v)
        rows.append({
            "id": "S", "metric": label,
            "C": str(c_v), "B": str(b_v),
            "delta": f"{_delta_pp(b_v, c_v, 0)}（{rel}%）",
            "gate": f"相对 C ±{TH['S_rel_max_pct']}%（双侧）",
            "verdict": "PASS" if (rel is not None and abs(rel) <= TH["S_rel_max_pct"]) else "FAIL",
        })

    # Q1/Q2/Q3 —— 单侧上界：只有"变大"才可能破闸；变小是改善，永不判破
    qspecs = (
        ("Q1", "Q1_L15_restate_rate", "L-15 restate_rate", "Q1_L15_max_pp"),
        ("Q2", "Q2_L7_norm8", "L-7 norm8", "Q2_L7_max_pp"),
        ("Q3", "Q3_F2_drift_rate", "F-2′ content_drift", "Q3_F2_max_pp"),
    )
    for qid, key, label, thk in qspecs:
        c_pct, b_pct = cr[key]["pct"], br[key]["pct"]
        dpp = _delta_pp(b_pct, c_pct, 2)
        if dpp is None:
            verdict = "N/A"
        elif dpp > TH[thk]:
            verdict = "FAIL(单批超带·须两 seed 同向后才判)"
        else:
            verdict = "IN-BAND(单批，须两 seed 同向才可判)"
        rows.append({
            "id": qid, "metric": label,
            "C": f'{cr[key]["num"]}/{cr[key]["den"]} = {c_pct}%',
            "B": f'{br[key]["num"]}/{br[key]["den"]} = {b_pct}%',
            "delta": f"{'+' if (dpp or 0) > 0 else ''}{dpp} pp",
            "gate": f"Δ(B−C) ≤ +{TH[thk]} pp（单侧上界；Δ<0 = 改善，不计破闸）",
            "verdict": verdict,
        })

    # 代价闸（只记录）
    c_c, b_c = cr["cost_llm_calls"]["value"], br["cost_llm_calls"]["value"]
    rel = _rel_pct(b_c, c_c)
    rows.append({
        "id": "代价", "metric": "llm_calls",
        "C": str(c_c), "B": str(b_c),
        "delta": f"{_delta_pp(b_c, c_c, 0)}（{rel}%）",
        "gate": f"≤ +{TH['cost_rel_max_pct']}%（破只记录）",
        "verdict": "PASS" if (rel is not None and rel <= TH["cost_rel_max_pct"]) else "记录",
    })
    return rows


def _dw(s: str) -> int:
    """显示宽度：CJK 全角算 2 列，便于终端对齐。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)


def _pad(s: str, w: int, right: bool = False) -> str:
    gap = max(0, w - _dw(s))
    return (" " * gap + s) if right else (s + " " * gap)


def print_table(rows: list[dict]) -> None:
    hdr = ["闸", "指标", "C（分子/分母）", "B（分子/分母）", "Δ", "闸口", "单批判定"]
    body = [[r["id"], r["metric"], r["C"], r["B"], r["delta"], r["gate"], r["verdict"]] for r in rows]
    table = [hdr] + body
    widths = [max(_dw(line[i]) for line in table) for i in range(7)]

    def render(cells):
        return "| " + " | ".join(_pad(str(c), w) for c, w in zip(cells, widths)) + " |"

    print(render(hdr))
    print("|" + "|".join("-" * (w + 2) for w in widths) + "|")
    for cells in body:
        print(render(cells))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--C", help="C（基线）臂 run.jsonl")
    ap.add_argument("--B", help="B（处理）臂 run.jsonl")
    ap.add_argument("--label", default="arm", help="输出标签，如 B42")
    ap.add_argument("--out-json", help="把读数与判定落成 JSON（可选）")
    a = ap.parse_args()
    if not (a.C or a.B):
        ap.error("至少给一个臂：--C 和/或 --B")

    R = load_frozen()
    out = {
        "rulers": {
            "driver": {"path": str(FROZEN.relative_to(REPO)), "sha256": sha256(FROZEN)},
            "p1_wordlist": {"path": "v2/evidence/d12c_metrics.py",
                            "sha256": sha256(REPO / "v2" / "evidence" / "d12c_metrics.py")},
            "names": {"path": "code/config/personas.json",
                      "sha256": sha256(REPO / "code" / "config" / "personas.json")},
            "this_script": {"path": str(Path(__file__).resolve().relative_to(REPO)),
                            "sha256": sha256(Path(__file__).resolve())},
            "resolution": "v2/refs/D28-F2prime-resolution.md",
        },
        "thresholds": TH,
        "label": a.label,
        "arms": {},
    }

    if a.C:
        out["arms"]["C"] = arm_readings(R, Path(a.C).resolve())
    if a.B:
        out["arms"]["B"] = arm_readings(R, Path(a.B).resolve())

    for tag in ("C", "B"):
        if tag not in out["arms"]:
            continue
        arm = out["arms"][tag]
        print(f"# ===== {tag} 臂：{Path(arm['path']).name} =====")
        print(f"# run.jsonl sha256 = {arm['sha256']}")
        print(f"# wc -l = {arm['wc_l']}；meta.events = {arm['meta']['events']}；"
              f"meta.run_sha256 = {arm['meta']['run_sha256']}")
        print(f"# seed={arm['meta']['seed']} rounds={arm['meta']['rounds']} n={arm['meta']['n']} "
              f"provider={arm['meta']['provider']} model={arm['meta']['model']} "
              f"degraded_calls={arm['meta']['degraded_calls']} code_sha={arm['meta']['code_sha']}")
        for key, r in arm["readings"].items():
            if "pct" in r:
                print(f"  {key:24s} {r['num']}/{r['den']} = {r['pct']}%   [分母规则] {r['den_rule']}")
            else:
                print(f"  {key:24s} {r['value']}   [分母/样本] {r['den_rule']}")
        print()

    if "C" in out["arms"] and "B" in out["arms"]:
        rows = judge(out["arms"]["C"], out["arms"]["B"])
        out["judgement"] = rows
        print("# ===== 逐项判定（口径见 v2/refs/D28-F2prime-resolution.md）=====")
        print_table(rows)
        print()
        print("# 注：Q1/Q2/Q3 的 IN-BAND / FAIL 一律是**单批**状态；"
              "按 amendment1:23 与裁决 §5，须两 seed 方向一致才可出结论。")

    if a.out_json:
        outp = Path(a.out_json)
        outp.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        print(f"# wrote {outp}  sha256={sha256(outp)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
