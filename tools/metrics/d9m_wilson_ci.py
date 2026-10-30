#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D9m 报告专用：Wilson 95% 置信区间批量计算器（**只调用唯一真源实现，不自带公式**）。

为什么需要这个脚本（leader 08:10 硬要求）：
    报告里的 CI 必须能被第三方逐字节复算。手算 CI 不可复算，会被 verifier 判 FAIL。
    本脚本把「分子/分母 → p + Wilson CI」这条链落盘化，且**复用** `tools/d5/dialogue_metrics.py::
    wilson_ci()` 这唯一实现（z=1.959964，来源 `tools/d5/f8_lexicon.json::raw.thresholds.
    wilson_z_95_two_sided`），**不重写公式**——若唯一天源改了，本脚本输出会随之改变，
    不会出现"两套实现给出两个 CI"的口径分叉（runbook §3.97 类事故）。

输入（JSON，UTF-8）：
    {"z": 1.959964,
     "pairs": [{"id": "M-a", "x": 3, "n": 205, "note": "精确串重复"}, ...]}
    x / n 必须是**整数**（分子、分母都必须来自可复算产物）；n=0 时输出 null（区间不填 0）。

输出（JSON）：
    {"schema": "d9m-wilson-ci/1.0",
     "generator": {"script": "<相对路径>", "script_sha256": "<实算>", "canonical_impl":
                   "tools/d5/dialogue_metrics.py::wilson_ci", "canonical_impl_sha256": "<实算>",
                   "z": 1.959964, "z_source": "tools/d5/f8_lexicon.json::thresholds.wilson_z_95_two_sided (dialogue_metrics 内别名为 raw.thresholds)"},
     "rows": [{"id":..., "x":..., "n":..., "p":..., "lo":..., "hi":..., "method":..., "note":...}]}

退出码：0 全成功 / 2 输入不合法（非整数、x>n、x<0、n<0）/ 3 自检不一致 / 4 唯一天源缺失

用法：
    python3 tools/metrics/d9m_wilson_ci.py --in pairs.json --out ci.json
    python3 tools/metrics/d9m_wilson_ci.py --x 179 --n 191            # 临时单点
    python3 tools/metrics/d9m_wilson_ci.py --selftest                  # 自检（比对写死的期望值）
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # 不在 tools/ 下留 __pycache__

HERE = Path(__file__).resolve()          # <repo>/tools/metrics/d9m_wilson_ci.py
REPO = HERE.parents[2]                   # <repo>（注意不是 parents[1]=<repo>/tools）
CANON = REPO / "tools" / "d5" / "dialogue_metrics.py"
LEXICON = REPO / "tools" / "d5" / "f8_lexicon.json"
SCHEMA = "d9m-wilson-ci/1.0"

# 自检期望值：由 canonical 实现（z=1.959964）实算得出，见报告 §可复算证据段。
SELFTEST_EXPECT = {
    (0, 191): (0.0, 0.019716),
    (179, 191): (0.893409, 0.963698),
    (10, 191): (0.028684, 0.093679),
    (28, 66): (0.312425, 0.544393),
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_canonical():
    """按文件路径加载唯一天源模块（不写 sys.path、不产生 bytecode）。"""
    if not CANON.exists():
        sys.stderr.write(f"canonical impl missing: {CANON}\n")
        raise SystemExit(4)
    spec = importlib.util.spec_from_file_location("d9m_canon_dialogue_metrics", str(CANON))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "wilson_ci"):
        sys.stderr.write("canonical impl has no wilson_ci()\n")
        raise SystemExit(4)
    return mod


def canonical_z() -> float:
    """z 从唯一天源配置文件读，不写死（写死会与 d5 口径分叉）。

    实现说明：`f8_lexicon.json` 的 `thresholds` 位于**顶层**；`dialogue_metrics.py` 里的
    `raw` 只是 `load_f8_inputs()` 把整份 lexicon 包成 `{"raw": lex}` 后的别称（见该文件 `:307`），
    并非文件内的真实键。本函数按文件真实结构取值，并对降级路径标注来源，避免静默取错。
    """
    with open(LEXICON, encoding="utf-8") as fh:
        lex = json.load(fh)
    th = lex.get("thresholds")
    if isinstance(th, dict) and "wilson_z_95_two_sided" in th:
        return float(th["wilson_z_95_two_sided"])
    legacy = (lex.get("raw") or {}).get("thresholds")
    if isinstance(legacy, dict) and "wilson_z_95_two_sided" in legacy:
        return float(legacy["wilson_z_95_two_sided"])
    sys.stderr.write("cannot locate wilson_z_95_two_sided in f8_lexicon.json\n")
    raise SystemExit(4)


def check_pair(pid: str, x, n) -> None:
    if not isinstance(x, int) or not isinstance(n, int) or isinstance(x, bool) or isinstance(n, bool):
        sys.stderr.write(f"[{pid}] x/n 必须是整数，得到 x={x!r} n={n!r}\n")
        raise SystemExit(2)
    if x < 0 or n < 0 or x > n:
        sys.stderr.write(f"[{pid}] 非法计数：x={x} n={n}（要求 0 <= x <= n）\n")
        raise SystemExit(2)


def build(pairs, mod, z: float) -> dict:
    rows = []
    for p in pairs:
        pid = str(p.get("id", ""))
        x, n = p.get("x"), p.get("n")
        check_pair(pid, x, n)
        ci = mod.wilson_ci(x, n, z)  # n=0 ⇒ None（不填 0）
        row = {"id": pid, "x": x, "n": n,
               "p": None if ci is None else ci["p"],
               "lo": None if ci is None else ci["lo"],
               "hi": None if ci is None else ci["hi"],
               "method": None if ci is None else ci["method"],
               "note": p.get("note", "")}
        rows.append(row)
    return {
        "schema": SCHEMA,
        "generator": {
            "script": str(HERE.relative_to(REPO)),
            "script_sha256": sha256_of(HERE),
            "canonical_impl": "tools/d5/dialogue_metrics.py::wilson_ci",
            "canonical_impl_sha256": sha256_of(CANON),
            "z": z,
            "z_source": "tools/d5/f8_lexicon.json::thresholds.wilson_z_95_two_sided (dialogue_metrics 内别名为 raw.thresholds)",
        },
        "rows": rows,
    }


def selftest(mod, z: float) -> int:
    bad = 0
    for (x, n), (exp_lo, exp_hi) in SELFTEST_EXPECT.items():
        ci = mod.wilson_ci(x, n, z)
        got = (ci["lo"], ci["hi"])
        ok = abs(got[0] - exp_lo) < 1e-9 and abs(got[1] - exp_hi) < 1e-9
        print(f"{'PASS' if ok else 'FAIL'} x={x} n={n} exp={exp_lo,exp_hi} got={got}")
        bad += 0 if ok else 1
    return 0 if bad == 0 else 3


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="D9m Wilson 95% CI 批量计算（复用 tools/d5 唯一实现）")
    ap.add_argument("--in", dest="inp", help="输入 JSON（含 pairs 列表）；与 --x/--n 二选一")
    ap.add_argument("--out", dest="out", help="输出 JSON 路径；省略则打印 stdout")
    ap.add_argument("--x", type=int, help="单点分子")
    ap.add_argument("--n", type=int, help="单点分母")
    ap.add_argument("--id", default="single", help="单点 id")
    ap.add_argument("--selftest", action="store_true", help="只跑自检")
    args = ap.parse_args(argv)

    mod = load_canonical()
    z = canonical_z()

    if args.selftest:
        return selftest(mod, z)

    if args.inp:
        with open(args.inp, encoding="utf-8") as fh:
            data = json.load(fh)
        pairs = data.get("pairs") or []
        if "z" in data and abs(float(data["z"]) - z) > 1e-12:
            sys.stderr.write(f"注意：输入 z={data['z']} 与唯一天源 z={z} 不同，按唯一天源计算\n")
    elif args.x is not None and args.n is not None:
        pairs = [{"id": args.id, "x": args.x, "n": args.n}]
    else:
        ap.error("需要 --in 或 (--x 且 --n)，或用 --selftest")

    result = build(pairs, mod, z)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}  rows={len(result['rows'])}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
