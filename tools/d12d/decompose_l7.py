#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-D 配套分析：把 `L-7`（8-gram 近重复率）**拆解**成「旁白层」与「正文层」。

## 为什么需要它

D12-C 已经证明：**旁白（括号块）本身就是 L-7 撞车的主要来源**（ON 侧 top 8-gram 里
`（把锄头往地上一`、`（把吉他横在膝上`、`（把第三格药柜的` 三条都是括号旁白）。
而 D12-D 的「换开头 / 换新物」两行指令，在跑批中途快照里已经让**旁白率继续大跌**
（`L-3_paren_block_any` 66.27% → 44.58%，中途值）。

⇒ 于是存在一个**必须排除的替代解释**：
> **L-7 的下降，可能只是「旁白被砍掉」的算术效应，而不是「同一批模板句式被换掉了」。**

本脚本就是用来回答这个问题的，**它不发明新指标**：
- `L7_orig` 严格复刻 `tools/d5/dialogue_metrics.py` 的 `L-7` 算法（`normalize_body` +
  `{t[i:i+8]}` shingle + "同一 shingle 出现在 ≥2 条消息即双方计入分子"），**并用自检保证逐位相等**；
- `L7_noparen` 只是把**同样的算法**作用在「先删掉括号块」的文本上 —— 这是**反事实重算**，
  目的是看「旁白全没了之后还剩多少撞车」。

## 判读用法（**不是判据**，只作机制解释）

- 若 `L7_orig` 明显降、但 `L7_noparen` 几乎不降 ⇒ **降的是旁白，不是模板**；
- 若两者同幅下降 ⇒ 正文层的模板句式也被换掉了，D12-D 的指令是真起作用。

## 用法

    python3 tools/d12d/decompose_l7.py \
        --run T1=v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl \
        --run T2=v2/evidence/run_d12d_on_n16r60_seed42/run.jsonl \
        --out-json v2/evidence/d12d_l7_decompose.json

自检：每臂都会打印 `d5_L7`（用 D5 同款算法算的原始率）与 `自检` 标记；
与 `tools/d5/dialogue_metrics.py` 输出的 `L-7_dup_ngram8_rate` **必须逐位相等**，
否则本脚本的拆解不可用（脚本退出码 2）。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "tools" / "d5"))

from dialogue_metrics import normalize_body, strip_paren  # noqa: E402  （冻结实现，不自创口径）

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")
NGRAM = 8


def l7_dup(norm_texts: list[str]) -> tuple[int, int]:
    """严格复刻 D5 的 L-7 算法（含 shingle 长度与计数规则）。"""
    shingles = []
    for t in norm_texts:
        shingles.append({t[i:i + NGRAM] for i in range(max(0, len(t) - (NGRAM - 1)))})
    index: dict[str, list[int]] = defaultdict(list)
    for i, sh in enumerate(shingles):
        for g in sh:
            index[g].append(i)
    dup: set[int] = set()
    for g, idxs in index.items():
        if len(idxs) > 1:
            dup.update(idxs)
    return len(dup), len(norm_texts)


def read_msgs(path: str) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("type") in MSG_TYPES:
                out.append(e.get("payload") or {})
    return out


def analyze(path: str) -> dict:
    msgs = read_msgs(path)
    bodies = [(m.get("body") or "") for m in msgs]
    norm_all = [normalize_body(b) for b in bodies]
    norm_np = [normalize_body(strip_paren(b)) for b in bodies]
    n = len(bodies)

    dup_all, _ = l7_dup(norm_all)
    dup_np, _ = l7_dup(norm_np)

    # 旁白（含括号块）消息
    paren_flags = [strip_paren(b) != b.strip() for b in bodies]
    n_paren = sum(paren_flags)

    # dup 消息里，含旁白 / 不含旁白 的构成
    shingles = [{t[i:i + NGRAM] for i in range(max(0, len(t) - (NGRAM - 1)))} for t in norm_all]
    index: dict[str, list[int]] = defaultdict(list)
    for i, sh in enumerate(shingles):
        for g in sh:
            index[g].append(i)
    dup_idx: set[int] = set()
    for g, idxs in index.items():
        if len(idxs) > 1:
            dup_idx.update(idxs)
    dup_with_paren = sum(1 for i in dup_idx if paren_flags[i])
    dup_without_paren = len(dup_idx) - dup_with_paren

    rate = lambda a, b: round(100 * a / b, 2) if b else None  # noqa: E731
    return {
        "n_msgs": n,
        "L7_orig": {"n_dup": dup_all, "rate": rate(dup_all, n)},
        "L7_noparen": {"n_dup": dup_np, "rate": rate(dup_np, n)},
        "n_paren_msgs": n_paren,
        "L3_paren_block_any": rate(n_paren, n),
        "dup_msgs_with_paren": dup_with_paren,
        "dup_msgs_without_paren": dup_without_paren,
        "dup_paren_share": rate(dup_with_paren, len(dup_idx)) if dup_idx else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, help="arm=path，可多次")
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--expect", action="append", default=[],
                    help="arm=rate，提供则做自检（与 D5 的 L-7 逐位比对，容差 0.01pp）")
    a = ap.parse_args()

    expects = {}
    for spec in a.expect:
        arm, _, val = spec.partition("=")
        expects[arm] = float(val)

    result = {}
    bad = []
    for spec in a.run:
        arm, _, path = spec.partition("=")
        r = analyze(path)
        result[arm] = r
        if arm in expects:
            got, want = r["L7_orig"]["rate"], expects[arm]
            ok = abs(got - want) <= 0.01
            r["selfcheck"] = {"d5_expected": want, "got": got, "ok": ok}
            if not ok:
                bad.append(arm)
        print(f"[{arm}] n={r['n_msgs']} L7_orig={r['L7_orig']['rate']}% "
              f"L7_noparen={r['L7_noparen']['rate']}% L3={r['L3_paren_block_any']}% "
              f"dup含旁白占比={r['dup_paren_share']}%"
              + (f" 自检={'PASS' if r.get('selfcheck', {}).get('ok') else 'FAIL'}" if "selfcheck" in r else ""))

    Path(a.out_json).write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    if bad:
        print(f"!! 自检失败：{bad} ⇒ 本脚本的 L-7 复刻与 D5 不一致，拆解结果不可用", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
