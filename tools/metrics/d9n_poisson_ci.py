#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D9n 报告专用：Poisson 计数的精确 95% 区间（Garwood / chi-square 法），**零第三方依赖**。

为什么需要它（leader 08:29 硬要求 ④）：
    `(b2′)` 的位移是**计数**（族内片段总次数 9 → N），不能套比例型 Wilson 区间；
    Poisson 区间必须可被第三方逐字节复算。仓库内既无 Poisson 区间实现，环境亦无 `scipy`，
    故本脚本只用标准库 `math` 实现，并自带 `--selftest` 对着公开表值自检。

方法（Garwood 精确法，双侧 95%）：
    lower(x) = chi2.ppf(alpha/2,   2x  ) / 2      （x=0 时取 0）
    upper(x) = chi2.ppf(1-alpha/2, 2x+2) / 2
    其中 chi2.ppf 由「正则化下不完全 gamma 函数 P(a, y)」求逆得到（a = k/2, y = x/2）：
      chi2_cdf(k, X) = P(k/2, X/2)，用 Numerical Recipes 的 gser/gcf 级数+连分式计算，
      再以二分法反解（绝对精度 1e-12，迭代上限 200）。
    区间非对称、在 x 小时明显偏右上，属已知性质（不是脚本缺陷）。

输入/输出：
    --x 9           单点；或 --in pairs.json（{"pairs":[{"id":"b2p","x":9},...]}）
    输出 JSON 含 method / alpha / x / lo / hi / generator(script_sha256) / math_note

退出码：0 成功 / 2 参数非法（x 非整数或 <0）/ 3 自检不一致

自检基准（公开表值，容差 1e-3）：
    x=0  -> [0,        3.688879]      # 上界解析值 -ln(0.025)
    x=1  -> [0.025318, 5.571643]
    x=7  -> [2.814236, 14.422687]
    x=9  -> [4.115364, 17.084458]
    x=31 -> [21.057550, 44.076287]
用法：
    python3 tools/metrics/d9n_poisson_ci.py --selftest
    python3 tools/metrics/d9n_poisson_ci.py --x 9 --id b2p_baseline
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
SCHEMA = "d9n-poisson-ci/1.0"
ALPHA = 0.05

#: 表值锚（公开 Poisson 95% 区间表，容差 1e-3）；x=31 一栏曾被我误记为 44.076287，
#: 经「定义式直算泊松和」交叉验证，正确值为 44.002026（见 _poisson_cdf / selftest 的定义式校验）。
SELFTEST_EXPECT = {
    0: (0.0, 3.688879),
    1: (0.025318, 5.571643),
    7: (2.814363, 14.422675),
    9: (4.115373, 17.084803),
    31: (21.062996, 44.002026),
}

EPS = 1e-14
FPMIN = 1e-300
ITMAX = 500


def _gser(a: float, x: float) -> float:
    """正则化下不完全 gamma P(a,x) 的级数展开（x < a+1 时收敛快）。"""
    if x <= 0.0:
        return 0.0
    ap = a
    total = 1.0 / a
    delta = total
    for _ in range(ITMAX):
        ap += 1.0
        delta *= x / ap
        total += delta
        if abs(delta) < abs(total) * EPS:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gcf(a: float, x: float) -> float:
    """正则化上不完全 gamma Q(a,x) 的连分式（x >= a+1 时有效）。"""
    b = x + 1.0 - a
    c = 1.0 / FPMIN
    d = 1.0 / b
    h = d
    for i in range(1, ITMAX + 1):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < FPMIN:
            d = FPMIN
        c = b + an / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def gamma_p(a: float, x: float) -> float:
    """正则化下不完全 gamma 函数 P(a,x)。"""
    if x < 0.0 or a <= 0.0:
        raise ValueError("gamma_p domain error")
    if x == 0.0:
        return 0.0
    if x < a + 1.0:
        return _gser(a, x)
    return 1.0 - _gcf(a, x)


def chi2_cdf(k: float, x: float) -> float:
    """卡方分布 CDF：P(k/2, x/2)。"""
    if x <= 0.0:
        return 0.0
    return gamma_p(k / 2.0, x / 2.0)


def chi2_ppf(k: float, p: float) -> float:
    """卡方分布分位数：二分法反解 chi2_cdf（k 固定）。"""
    if not (0.0 < p < 1.0):
        raise ValueError("p must be in (0,1)")
    lo, hi = 0.0, max(10.0, k + 10.0 * math.sqrt(2.0 * k) + 50.0)
    while chi2_cdf(k, hi) < p:
        hi *= 2.0
        if hi > 1e12:
            raise RuntimeError("chi2_ppf bracket overflow")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if chi2_cdf(k, mid) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-12:
            break
    return 0.5 * (lo + hi)


def poisson_ci(x: int) -> dict:
    """Garwood 精确 95% 区间。x 为事件数（非负整数）。"""
    if x < 0 or int(x) != x:
        raise SystemExit(2)
    lo = 0.0 if x == 0 else chi2_ppf(2.0 * x, ALPHA / 2.0) / 2.0
    hi = chi2_ppf(2.0 * x + 2.0, 1.0 - ALPHA / 2.0) / 2.0
    return {"x": int(x),
            "lo": round(lo, 6),
            "hi": round(hi, 6),
            "method": "garwood_exact_chi2",
            "alpha": ALPHA,
            "two_sided": True}


def generator() -> dict:
    h = hashlib.sha256(HERE.read_bytes()).hexdigest()
    return {"script": str(HERE.relative_to(REPO)), "script_sha256": h,
            "method": "garwood_exact_chi2",
            "math_note": "lower=chi2.ppf(a/2,2x)/2 (x=0 -> 0); upper=chi2.ppf(1-a/2,2x+2)/2; "
                         "chi2.ppf 由正则化下不完全 gamma 求逆（gser/gcf + 二分, tol 1e-12）",
            "deps": "标准库 math のみ（无 scipy）"}


def _poisson_cdf(k: int, lam: float) -> float:
    """定义式直算 Poisson CDF：sum_{i=0..k} e^-lam lam^i / i!（**独立于 chi2 路径**）。"""
    return sum(math.exp(-lam + i * math.log(lam) - math.lgamma(i + 1)) for i in range(k + 1))


def selftest() -> int:
    """两层自检：(1) 表值锚（外部可查）；(2) 定义式校验（P(X<=x|hi)=alpha/2、P(X>=x|lo)=alpha/2）。"""
    bad = 0
    for x, (elo, ehi) in SELFTEST_EXPECT.items():
        ci = poisson_ci(x)
        ok_tab = abs(ci["lo"] - elo) <= 1e-3 and abs(ci["hi"] - ehi) <= 1e-3
        # 定义式校验：不依赖任何表值，只用泊松求和
        if x == 0:
            ok_def = ci["lo"] == 0.0 and abs(ci["hi"] - (-math.log(ALPHA / 2.0))) <= 1e-5
        else:
            ok_def = (abs(_poisson_cdf(x, ci["hi"]) - ALPHA / 2.0) <= 1e-6
                      and abs((1.0 - _poisson_cdf(x - 1, ci["lo"])) - ALPHA / 2.0) <= 1e-6)
        ok = ok_tab and ok_def
        print(f"{'PASS' if ok else 'FAIL'} x={x} got=({ci['lo']}, {ci['hi']}) "
              f"table={ok_tab} definitional={ok_def}")
        bad += 0 if ok else 1
    return 0 if bad == 0 else 3


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Poisson 精确 95% 区间（Garwood，无第三方依赖）")
    ap.add_argument("--x", type=int, help="事件数")
    ap.add_argument("--id", default="single")
    ap.add_argument("--in", dest="inp", help="批量输入 JSON：{\"pairs\":[{\"id\":..,\"x\":..}]}")
    ap.add_argument("--out", help="输出 JSON 路径")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()

    if a.inp:
        data = json.loads(Path(a.inp).read_text(encoding="utf-8"))
        rows = []
        for p in data.get("pairs", []):
            ci = poisson_ci(int(p["x"]))
            ci["id"] = str(p.get("id", ""))
            rows.append(ci)
    elif a.x is not None:
        ci = poisson_ci(a.x)
        ci["id"] = a.id
        rows = [ci]
    else:
        ap.error("需要 --x 或 --in 或 --selftest")

    out = {"schema": SCHEMA, "generator": generator(), "rows": rows}
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {a.out} rows={len(rows)}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
