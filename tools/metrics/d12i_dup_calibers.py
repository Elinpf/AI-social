#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-I 的**重复度三口径并列**出数器（纯只读、零跑批、零 LLM）。

为什么单列一个文件：任务纪律要求「相近但不同的量必须并列输出、名字带口径后缀，禁止二选一」。
D12-I 报告里最容易被混用的是「重复」这件事的三个量，它们的**分子不同、可比性也不同**：

| 口径后缀 | 定义 | 分母 | 能不能跨批比 |
|---|---|---|---|
| `raw_exact`   | 原文 body 完全相同的消息数（sha/exact） | 全部 MSG | 能（同口径） |
| `norm_exact`  | `d5.normalize_body()` 归一后完全相同的消息数 | 全部 MSG | 能（同口径） |
| `norm8_shingle` | 与任一其他 MSG 共享 ≥1 个**归一后 8-gram** 的消息数（= d5 `L-7_dup_ngram8_rate` 的分子） | 全部 MSG | **不能**（跨批索引不同，见 README） |

口径来源（不自造）：
- `raw_exact` / `norm_exact` 是 `tools/d9/arm_state_check.py::metrics()` 的 `dup_exact_rate` 的同族写法
  （该函数用 `1 - len(set(bodies))/n`，即原文 body）；
- `norm_exact` / `norm8_shingle` 的归一函数与 8-gram 构造**直接调用** `tools/d5/dialogue_metrics.py`
  的 `normalize_body()`，并在输出里记录该文件的 sha256；
- `norm8_shingle` 的数值必须与 `tools/metrics/form_metrics.py` 的 `L-7_dup_ngram8_rate` 分子相等，
  本脚本会做一致性自检（不相等即以 rc=3 退出）。

用法：
    python3 tools/metrics/d12i_dup_calibers.py --log <run.jsonl> --out <out.json>
退出码：0 正常 / 2 输入缺失或无 MSG / 3 与 form_metrics 的 L-7 分子不一致
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
D5_SRC = REPO / "tools" / "d5" / "dialogue_metrics.py"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_d5():
    spec = importlib.util.spec_from_file_location("d5_dialogue_metrics", D5_SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # type: ignore[union-attr]
    return mod


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    log = Path(a.log)
    if not log.exists():
        print(f"[FAIL] 缺日志 {log}", file=sys.stderr)
        return 2

    bodies = []
    with open(log, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            if not str(r.get("type", "")).startswith("MSG"):
                continue
            b = (r.get("payload") or {}).get("body") or r.get("body") or ""
            bodies.append(b)
    n = len(bodies)
    if not n:
        print("[FAIL] 日志内无 MSG", file=sys.stderr)
        return 2

    d5 = load_d5()
    norm = [d5.normalize_body(b) for b in bodies]

    raw_exact_dup = n - len(set(bodies))
    norm_exact_dup = n - len(set(norm))
    grams = [set(x[k:k + 8] for k in range(max(0, len(x) - 7))) for x in norm]
    index = {}
    for i, gs in enumerate(grams):
        for g in gs:
            index.setdefault(g, []).append(i)
    dup_norm8 = sum(1 for i, gs in enumerate(grams) if any(len(index[g]) > 1 for g in gs))

    # raw8 口径：**不做 normalize**，直接在原文 body 上取 8-gram（与 norm8 并列、不可混用）
    grams_raw = [set(b[k:k + 8] for k in range(max(0, len(b) - 7))) for b in bodies]
    idx_raw = {}
    for i, gs in enumerate(grams_raw):
        for g in gs:
            idx_raw.setdefault(g, []).append(i)
    dup_raw8 = sum(1 for i, gs in enumerate(grams_raw) if any(len(idx_raw[g]) > 1 for g in gs))

    out = {
        "schema_version": "d12i-dup-calibers/1.0",
        "log": str(log),
        "log_sha256": sha256_file(log),
        "denominator": n,
        "denominator_definition": "全部 MSG（MSG_* 事件的 body 非空与否都计入，与 d5 meta.n_messages 同口径）",
        "calibers": {
            "raw_exact": {
                "definition": "原文 body 完全相同的消息数（未归一，sha/exact 语义）",
                "numerator": raw_exact_dup,
                "value": round(raw_exact_dup / n, 6),
                "cross_batch_comparable": True,
                "source": "同 tools/d9/arm_state_check.py::metrics() 的 dup_exact_rate 写法（1 - 唯一(body)/n）",
            },
            "norm_exact": {
                "definition": "d5.normalize_body() 归一后完全相同的消息数",
                "numerator": norm_exact_dup,
                "value": round(norm_exact_dup / n, 6),
                "cross_batch_comparable": True,
                "source": f"tools/d5/dialogue_metrics.py::normalize_body（sha256 {sha256_file(D5_SRC)}）",
            },
            "norm8_shingle": {
                "definition": "与任一其他 MSG 共享 ≥1 个归一后 8-gram 的消息数（= d5 L-7 分子）",
                "numerator": dup_norm8,
                "value": round(dup_norm8 / n, 6),
                "cross_batch_comparable": False,
                "source": "tools/d5/dialogue_metrics.py L-7_dup_ngram8_rate 的同构复算",
            },
            "raw8_shingle": {
                "definition": "与任一其他 MSG 共享 ≥1 个**未归一**原文 8-gram 的消息数（仓内无现成出数器，本文件现算）",
                "numerator": dup_raw8,
                "value": round(dup_raw8 / n, 6),
                "cross_batch_comparable": False,
                "source": "本文件按 norm8 同构写法在原文 body 上取 8-gram（口径**不**等于 d5 的 norm8）",
            },
        },
        "note": "三个口径**分子不同、互不替代**：raw_exact ≤ norm_exact，norm8_shingle 因 8-gram 片断重合而显著更大；"
                "跨批只能比 raw_exact / norm_exact，norm8_shingle 的值只能与本批自身索引一起读。",
        "recompute_cmd": f"python3 tools/metrics/d12i_dup_calibers.py --log {a.log} --out {a.out}",
    }

    # 一致性命中：norm8_shingle 必须等于 form_metrics 的 L-7 分子
    fm = Path(a.out).parent / "form_metrics_full.json"
    if fm.exists():
        l7 = json.loads(fm.read_text(encoding="utf-8"))["metrics"]["L-7_dup_ngram8_rate"]
        expected = l7["numerator"]
        out["checks"] = {
            "form_metrics_L7_numerator": expected,
            "norm8_shingle_numerator": dup_norm8,
            "match": expected == dup_norm8,
            "raw_exact_matches_shape_gate_dup_exact_rate": None,
        }
        Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if expected != dup_norm8:
            print(f"[FAIL] L-7 分子不一致：form_metrics={expected} 本脚本={dup_norm8}", file=sys.stderr)
            return 3
    else:
        Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(out["calibers"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
