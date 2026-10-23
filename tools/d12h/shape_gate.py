#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-I 形态闸（**纯只读**）：一条命令出四项形态指标 + 与 T5 的漂移 + 越界判定。

为什么需要它（代价已付过）：D12-H 花了 6,073 次调用才发现「以称呼开头」把**旁白整条挤掉**
（`paren_rate` T5 57.84% → D12-H **0.20%**），而预登记里的 `L-3` 代价闸**没在 1/3 处先核**。
⇒ 本工具就是那道闸：**1/3（约 20 轮）与收尾各跑一次**，F1/F2 越界即停跑、判「作废（形态漂移，非单变量）」。

**为什么必须对真跑日志核**：mock 冒烟抓不到这类漂移——mock 文本是模板、本来就没有旁白。

口径（**不自造**）：
- `paren_rate` / `len_p50` / `len_p50_excl` **直接复用 `tools/d9/arm_state_check.py::metrics`**，
  运行时打印该函数的 `impl_sha256`；
- `paren_head_rate` = 正文去空白后**以 `（` 或 `(` 开头**（旁白起头，D12-H 实测为 0.20% 的那一项）；
- `addr_head_rate`（**精确口径**）= 正文以**对端/角色显示名**开头（名字取自跑批树的 `build_world(seed,n)`
  的 `_peer_names`，允许名字后跟 0–2 个称谓字如「哥/姐/啊」再接 `，：:,`）；
- `addr_head_upper`（**正则上界**，只作参照）= `^[\\u4e00-\\u9fa5]{1,4}[，,：:]` —— 会把「这块榫头，」也算称呼，
  **不得作为判据**（D12-H 时 94.90% vs 精确 90.98%）。

判据（D12-I 预登记 §2，阈值写死在此、可由参数覆盖）：
| 闸 | 口径 | 基线 T5 | 容许 |
|---|---|---|---|
| **F1** | `paren_rate` | 0.5784 | 漂移 ≤ 5pp（绝对） |
| **F2** | `addr_head_rate`（精确） | 0.41 | 漂移 ≤ 15pp（绝对） |
| **F3** | `len_p50` | 53 | 漂移 ≤ 10%（相对） |

用法：
    python3 tools/d12h/shape_gate.py --log <run.jsonl> [--rounds 20] [--out-json x.json]
退出码：**0** 全过 / **1** 有越界 / **2** 无法判定（日志为空或无 MSG）
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDR_UPPER = re.compile(r"^[\u4e00-\u9fa5]{1,4}[，,：:]")
SUFFIX_CHARS = "哥姐叔婶爷奶老师先生女士先儿啊呀诶哎"


def _main_checkout_root() -> Path | None:
    """worktree 与主 checkout 不同时，`tools/d9/` 只在主 checkout 里（a977cb0 系树没有它）。"""
    try:
        import subprocess
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-common-dir"],
                             capture_output=True, text=True, timeout=10)
        common = out.stdout.strip()
        if not common:
            return None
        p = Path(common)
        if not p.is_absolute():
            p = (ROOT / p).resolve()
        return p.parent           # <main>/.git → <main>
    except Exception:
        return None


def load_metrics_impl():
    """复用 `tools/d9/arm_state_check.py::metrics`（不自造口径），并给出其源码 sha256 与来源路径。

    查找顺序：`$SHAPE_GATE_METRICS_SRC` → 本 worktree → 主 checkout（`git rev-parse --git-common-dir`）。
    **找不到就明确报错**（不静默换自造口径）。
    """
    cands = []
    env = os.environ.get("SHAPE_GATE_METRICS_SRC")
    if env:
        cands.append(Path(env))
    cands.append(ROOT / "tools" / "d9" / "arm_state_check.py")
    mr = _main_checkout_root()
    if mr:
        cands.append(mr / "tools" / "d9" / "arm_state_check.py")
    p = next((c for c in cands if c.exists()), None)
    if p is None:
        raise SystemExit(f"[shape_gate] 找不到 arm_state_check.py；试过：{[str(c) for c in cands]}\n"
                         f"  ⇒ 用 --code-dir/SHAPE_GATE_METRICS_SRC 指定，或从主 checkout 运行")
    spec = importlib.util.spec_from_file_location("_shape_gate_arm_state_check", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    src = inspect.getsource(mod.metrics)
    return mod.metrics, hashlib.sha256(src.encode("utf-8")).hexdigest(), str(p)


def load_names(seed: int, n: int, code_dir: Path) -> tuple:
    """从跑批树 `build_world(seed, n)` 取全部显示名；失败则返回空集合（F2 降级为 CANNOT-VERIFY）。"""
    try:
        sys.path.insert(0, str(code_dir))
        from orchestration.integration import build_world  # noqa: E402
        w = build_world(seed=seed, n=n)
        names = set()
        for a in w["agents"]:
            names |= set((getattr(a, "_peer_names", {}) or {}).values())
        names.discard("")
        return names, None
    except Exception as e:                                    # 不静默：把原因返回给上层显示
        return set(), f"{type(e).__name__}: {e}"


def is_addr_head(body: str, names: set) -> bool:
    b = body.strip()
    for nm in names:
        if b.startswith(nm):
            rest = b[len(nm):]
            # 允许 0–2 个称谓字再接标点：「老石，」「铁头哥，」「老周啊，」
            for k in range(0, 3):
                if rest[k:k + 1] in ("，", ",", "：", ":"):
                    return True
                if k >= len(rest) or (k > 0 and rest[k - 1] not in SUFFIX_CHARS):
                    break
    return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--rounds", type=int, default=None, help="只看前 N 轮（1/3 处用；缺省=全 run）")
    ap.add_argument("--points", default=None,
                    help="三点核：逗号分隔的轮数上界，如 20,30,60（60=收尾）。给此项时忽略 --rounds，"
                         "并额外报 Δparen/Δaddr(前两点) 与跃变标记")
    ap.add_argument("--jump-pp", type=float, default=10.0,
                    help="跃变阈值：|Δparen(前两点)| 或 |Δaddr(前两点)| > 该值 ⇒ 标 jump（**只是提示，不影响 rc**）")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--code-dir", default=None, help="跑批树 code/ 路径（取显示名用），缺省 <repo>/code")
    ap.add_argument("--t5-paren", type=float, default=0.5784)
    # §3.113：strict 是判据口径，upper 仅参照。原 default=0.41 实为 *upper* 值，
    # 却被 strict 判据使用 ⇒ F2 基线高估 4.53pp（D12-I 曾因此把 PASS 翻成 FAIL）。
    ap.add_argument("--t5-addr-strict", type=float, default=0.3647,
                    help="T5 上 addr_head_strict（显示名精确匹配）实测值 = 36.47%%；F2 判据基线")
    ap.add_argument("--t5-addr-upper", type=float, default=0.41,
                    help="T5 上 addr_head_upper（正则上界）实测值 = 41.00%%；仅参照，不作判据")
    ap.add_argument("--t5-addr", type=float, default=None,
                    help="[DEPRECATED] 旧名，等同 --t5-addr-strict；保留仅为兼容旧命令行")
    ap.add_argument("--t5-len", type=float, default=53.0)
    ap.add_argument("--f1-pp", type=float, default=5.0)
    ap.add_argument("--f2-pp", type=float, default=15.0)
    ap.add_argument("--f3-rel", type=float, default=0.10)
    ap.add_argument("--out-json", default=None)
    a = ap.parse_args(argv)
    if a.t5_addr is not None:
        print("[shape_gate] --t5-addr 已弃用，按 --t5-addr-strict 处理", file=sys.stderr)
        a.t5_addr_strict = a.t5_addr

    metrics, impl_sha, impl_path = load_metrics_impl()
    code_dir = Path(a.code_dir) if a.code_dir else (ROOT / "code")
    names, names_err = load_names(a.seed, a.n, code_dir)

    def _bodies(rounds, lo=None):
        bs, rds = [], set()
        with open(a.log, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                if not str(r.get("type", "")).startswith("MSG"):
                    continue
                rd = r.get("round")
                if rounds is not None and isinstance(rd, int) and rd >= rounds:
                    continue
                if lo is not None and (not isinstance(rd, int) or rd < lo):
                    continue
                b = ((r.get("payload") or {}).get("body") or "").strip()
                if b:
                    bs.append(b)
                    rds.add(rd)
        return bs, rds

    def _point(rounds, lo=None):
        bs, rds = _bodies(rounds, lo)
        if not bs:
            return None
        mm = metrics(bs)
        nb = len(bs)
        ph = sum(1 for b in bs if b[:1] in "（(")
        ad = sum(1 for b in bs if names and is_addr_head(b, names))
        au = sum(1 for b in bs if ADDR_UPPER.match(b[:8]))
        paren = mm["paren_rate"]
        len_excl = mm["len_p50_excl"]
        d1 = paren - a.t5_paren
        d2 = (ad / nb) - a.t5_addr_strict if names else None
        d3 = (len_excl - a.t5_len) / a.t5_len
        return {
            "rounds": (("[%s,%s)" % (lo, rounds)) if (lo is not None and rounds is not None)
                       else (("<" + str(rounds)) if rounds is not None else "full")),
            "n_bodies": nb,
            "rounds_covered": [min(rds), max(rds)] if rds else None,
            "metrics": {"paren_rate": paren, "paren_head_rate": ph / nb,
                        "addr_head_strict": (ad / nb) if names else None,
                        "addr_head_upper_rate": au / nb,
                        "len_p50": mm["len_p50"], "len_p50_excl": len_excl,
                        "id_leak_rate": mm.get("id_leak_rate"),
                        "dup_exact_rate": mm.get("dup_exact_rate")},
            "gate": {
                "F1_paren": {"t5": a.t5_paren, "drift_pp": d1 * 100, "tol_pp": a.f1_pp,
                             "verdict": "PASS" if abs(d1) * 100 <= a.f1_pp else "FAIL"},
                "F2_addr_head": {"t5": a.t5_addr_strict, "t5_label": "addr_head_strict",
                                 "t5_upper_reference": a.t5_addr_upper,
                                 "observed_label": "addr_head_strict",
                                 "observed_upper_reference": (au / nb),
                                 "drift_pp": (d2 * 100) if d2 is not None else None,
                                 "tol_pp": a.f2_pp,
                                 "verdict": ("CANNOT-VERIFY" if not names else
                                             ("PASS" if abs(d2) * 100 <= a.f2_pp else "FAIL"))},
                "F3_len_p50_excl": {"t5": a.t5_len, "observed": len_excl, "drift_rel": d3,
                                    "tol_rel": a.f3_rel,
                                    "verdict": "PASS" if abs(d3) <= a.f3_rel else "FAIL",
                                    "raw_len_p50_shown_only": mm["len_p50"]},
            },
        }

    # ---- 三点核模式 ----
    if a.points:
        try:
            pts = [int(x) for x in str(a.points).split(",") if str(x).strip()]
        except ValueError:
            print(f"[shape_gate] --points 解析失败：{a.points!r}", file=sys.stderr)
            return 2
        rows = []
        for n in pts:
            r = _point(n if n < 10 ** 6 else None)      # n>=大数视作"全 run"
            if r is None:
                print(f"[shape_gate] 时点 {n} 无可用 MSG", file=sys.stderr)
                return 2
            rows.append(r)
        # 逐段（块）分析：段 = [上一时点, 本时点)，用于抓"段间跃变"（D12-I 的漂移是块级 +24.5pp）
        segs, prev = [], 0
        for n in pts:
            hi = None if n >= 10 ** 6 else n
            r = _point(hi, prev)
            if r is not None:
                r["rounds"] = ("[%s,%s)" % (prev, "end" if hi is None else hi))
                segs.append(r)
            prev = hi if hi is not None else prev
        seg_jump = None
        if len(segs) >= 2:
            worst = None
            for i in range(1, len(segs)):
                dp = (segs[i]["metrics"]["paren_rate"] - segs[i - 1]["metrics"]["paren_rate"]) * 100
                a0 = segs[i - 1]["metrics"]["addr_head_strict"]
                a1 = segs[i]["metrics"]["addr_head_strict"]
                da = ((a1 - a0) * 100) if (a0 is not None and a1 is not None) else None
                big = abs(dp) > a.jump_pp or (da is not None and abs(da) > a.jump_pp)
                item = {"from": segs[i - 1]["rounds"], "to": segs[i]["rounds"],
                        "delta_paren_pp": dp, "delta_addr_pp": da, "jump": big}
                if big and (worst is None or abs(dp) > abs(worst["delta_paren_pp"])):
                    worst = item
            seg_jump = {"threshold_pp": a.jump_pp, "largest": worst,
                        "any_jump": bool(worst),
                        "note": "段间（块级）跃变；只是提示，不参与 rc"}

        jump = None
        if len(rows) >= 2:
            p0 = rows[0]["metrics"]["paren_rate"]
            p1 = rows[1]["metrics"]["paren_rate"]
            a0 = rows[0]["metrics"]["addr_head_strict"]
            a1 = rows[1]["metrics"]["addr_head_strict"]
            d_paren = (p1 - p0) * 100
            d_addr = ((a1 - a0) * 100) if (a0 is not None and a1 is not None) else None
            flagged = abs(d_paren) > a.jump_pp or (d_addr is not None and abs(d_addr) > a.jump_pp)
            jump = {"pair": [rows[0]["rounds"], rows[1]["rounds"]],
                    "delta_paren_pp": d_paren, "delta_addr_pp": d_addr,
                    "threshold_pp": a.jump_pp, "flagged": flagged,
                    "note": "跃变只是提示，不参与 rc；rc 只看各时点闸是否越界"}
        out = {"log": a.log, "mode": "points", "points": rows, "segments": segs,
               "segment_jump": seg_jump, "jump": jump,
               "impl": {"metrics_from": impl_path, "metrics_impl_sha256": impl_sha},
               "names_source": {"n_names": len(names), "error": names_err},
               "metrics_note": "F3 判据口径 = len_p50_excl；addr_head_strict 用显示名匹配（判据），addr_head_upper_rate 仅参照"}
        txt = json.dumps(out, ensure_ascii=False, indent=2)
        print(txt)
        if a.out_json:
            Path(a.out_json).write_text(txt + "\n", encoding="utf-8")

        print("", file=sys.stderr)
        print(f"[shape_gate:points] log={a.log}  metrics_impl_sha256={impl_sha[:16]}…", file=sys.stderr)
        print(f"  {'时点':<10}{'n':>5}{'paren':>9}{'F1':>6}{'addr_strict':>13}{'F2':>6}"
              f"{'len_excl':>10}{'F3':>6}", file=sys.stderr)
        any_fail = False
        for r in rows:
            g = r["gate"]
            for k in g:
                if g[k]["verdict"] == "FAIL":
                    any_fail = True
            print(f"  {r['rounds']:<10}{r['n_bodies']:>5}"
                  f"{r['metrics']['paren_rate'] * 100:>8.2f}%{g['F1_paren']['verdict']:>6}"
                  f"{(r['metrics']['addr_head_strict'] * 100 if r['metrics']['addr_head_strict'] is not None else float('nan')):>12.2f}%"
                  f"{g['F2_addr_head']['verdict']:>6}"
                  f"{r['metrics']['len_p50_excl']:>10.1f}{g['F3_len_p50_excl']['verdict']:>6}", file=sys.stderr)
        if segs:
            print("  分段（块级）读数：", file=sys.stderr)
            for r in segs:
                print(f"    {r['rounds']:<12}{r['n_bodies']:>5}"
                      f"{r['metrics']['paren_rate'] * 100:>8.2f}%"
                      f"{(r['metrics']['addr_head_strict'] * 100 if r['metrics']['addr_head_strict'] is not None else float('nan')):>13.2f}%"
                      f"{r['metrics']['len_p50_excl']:>10.1f}", file=sys.stderr)
        if seg_jump:
            lg = seg_jump["largest"]
            print(f"  段间跃变（阈值 ±{a.jump_pp}pp）："
                  + (f"{lg['from']}→{lg['to']} Δparen={lg['delta_paren_pp']:+.2f}pp"
                     + (f"  Δaddr={lg['delta_addr_pp']:+.2f}pp" if lg["delta_addr_pp"] is not None else "")
                     + "  ⇒ JUMP（提示，不影响 rc）" if seg_jump["any_jump"] else "no-jump"), file=sys.stderr)
        if jump:
            print(f"  累积点间 Δ（{jump['pair'][0]}→{jump['pair'][1]}，阈值 ±{a.jump_pp}pp）："
                  f"Δparen={jump['delta_paren_pp']:+.2f}pp"
                  + (f"  Δaddr={jump['delta_addr_pp']:+.2f}pp" if jump["delta_addr_pp"] is not None else "")
                  + f"  ⇒ {'JUMP（提示，不影响 rc）' if jump['flagged'] else 'no-jump'}", file=sys.stderr)
        if any_fail:
            print("[shape_gate:points] 结论：FAIL（至少一个时点越界） ⇒ 按预登记判「作废（形态漂移）」", file=sys.stderr)
            return 1
        print("[shape_gate:points] 结论：PASS（各时点 F1/F2/F3 均在容许带内）"
              + ("；但有跃变提示，请复核" if jump and jump["flagged"] else ""), file=sys.stderr)
        return 0

    # ---- 单时点模式（兼容旧用法）----
    pt = _point(a.rounds)
    if pt is None:
        print(f"[CANNOT-VERIFY] 日志没有可用 MSG（--rounds={a.rounds}）", file=sys.stderr)
        return 2
    out = {"log": a.log, "rounds_filter": a.rounds, "n_bodies": pt["n_bodies"],
           "rounds_covered": pt["rounds_covered"],
           "impl": {"metrics_from": impl_path, "metrics_impl_sha256": impl_sha},
           "metrics": pt["metrics"],
           "names_source": {"n_names": len(names), "error": names_err},
           "metrics_note": "F3 判据口径 = len_p50_excl（与预登记 §2 一致）；len_p50(raw) 仅展示；"
                           "addr_head_strict 用显示名匹配（判据），addr_head_upper_rate 仅参照",
           "gate": pt["gate"],
           "note": "F2 用精确口径（显示名匹配）；addr_head_upper_rate 是正则上界，仅参照，不作判据"}
    txt = json.dumps(out, ensure_ascii=False, indent=2)
    print(txt)
    if a.out_json:
        Path(a.out_json).write_text(txt + "\n", encoding="utf-8")

    g = pt["gate"]
    print("", file=sys.stderr)
    print(f"[shape_gate] log={a.log}  rounds={'-' if a.rounds is None else '<' + str(a.rounds)}  "
          f"n_bodies={pt['n_bodies']}  metrics_impl_sha256={impl_sha[:16]}…", file=sys.stderr)
    print(f"  paren_rate        = {pt['metrics']['paren_rate'] * 100:6.2f}%   (T5 {a.t5_paren * 100:.2f}%)   "
          f"drift {g['F1_paren']['drift_pp']:+.2f}pp  tol ±{a.f1_pp}pp   [{g['F1_paren']['verdict']}]",
          file=sys.stderr)
    print(f"  paren_head_rate   = {pt['metrics']['paren_head_rate'] * 100:6.2f}%   （旁白起头，参照项）", file=sys.stderr)
    if names:
        print(f"  addr_head_strict  = {pt['metrics']['addr_head_strict'] * 100:6.2f}%   (T5 {a.t5_addr_strict * 100:.2f}% strict)   "
              f"drift {g['F2_addr_head']['drift_pp']:+.2f}pp  tol ±{a.f2_pp}pp   [{g['F2_addr_head']['verdict']}]",
              file=sys.stderr)
    else:
        print(f"  addr_head_strict  = CANNOT-VERIFY（取显示名失败：{names_err}）", file=sys.stderr)
    print(f"  addr_head_upper   = {pt['metrics']['addr_head_upper_rate'] * 100:6.2f}%   （正则上界，仅参照）",
          file=sys.stderr)
    print(f"  len_p50_excl(F3)  = {pt['metrics']['len_p50_excl']:6.1f}    (T5 {a.t5_len:.0f})   "
          f"drift {g['F3_len_p50_excl']['drift_rel'] * 100:+.2f}%  tol ±{a.f3_rel * 100:.0f}%   "
          f"[{g['F3_len_p50_excl']['verdict']}]", file=sys.stderr)
    print(f"  len_p50(raw)      = {pt['metrics']['len_p50']:6.1f}    （仅展示，不作判据）", file=sys.stderr)

    verdicts = [v["verdict"] for v in g.values()]
    if "FAIL" in verdicts:
        print(f"[shape_gate] 结论：FAIL（越界闸 = {[n for n, v in zip(('F1', 'F2', 'F3'), verdicts) if v == 'FAIL']}）",
              file=sys.stderr)
        return 1
    if "CANNOT-VERIFY" in verdicts:
        print(f"[shape_gate] 结论：CANNOT-VERIFY（{[n for n, v in zip(('F1', 'F2', 'F3'), verdicts) if v == 'CANNOT-VERIFY']}）",
              file=sys.stderr)
        return 2
    print("[shape_gate] 结论：PASS（F1/F2/F3 全在容许带内）", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
