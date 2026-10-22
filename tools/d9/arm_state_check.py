#!/usr/bin/env python3
"""arm_state_check.py — 对照臂「期望值自检」（只读，秒级；建议每批起跑后 1 分钟内跑）。

设计初衷（2026-10-22 四次事故的直接教训）
------------------------------------------------
事故类型：① provider 静默回落到 mock；② 开关未接线（A2 未生效）；③ mock 批无法验证提示词；
④ 跑批树里混入了旧变量（混淆）。
共同点：**配置文件写了什么 / 声明了什么，都不等于行为符合该树期望**。
故本工具一律按「**行为 vs 该树期望**」判定，而不是读 config 或 env。

用法
----
  python3 tools/d9/arm_state_check.py --run <run.jsonl> \
      --tree-expectation '{"paren_rate": 0.70, "len_p50": 39}' \
      [--tolerance 0.05] [--first-n 20] \
      [--expect-struct '{"msgs": 686, "threads": 206, "ge3": 90}'] \
      [--expect-provider openai_compat] \
      [--expect-env HITT_D12_DETAIL=1] \
      [--expect-behavior '{"paren_rate": {"min": 0.30}}']

退出码：0 全 PASS；1 有 FAIL；2 仅 CANNOT-VERIFY（未给期望，无从判定）。

判据
----
C0 provider（可选）：`LLM_CALL.payload.provider` 必须只含 `--expect-provider` 指定值。
    —— 直接抓「mock 静默回落」；不给则 CANNOT-VERIFY。
C1 前 N 条消息指标 vs `--tree-expectation`：
    rate 类（期望值 < 1）用**绝对差** ≤ tolerance；计数/长度类（≥1）用**相对差** ≤ tolerance。
C2 seals 单调递增且无重复、`WORLD_INIT` 唯一（抓「续跑污染 / 断链 / 双初始化」）。
C3 开关与行为的耦合：给了 `--expect-env KEY=VAL` 就**必须**同时给 `--expect-behavior`（行为判据），
    否则 FAIL ——「只声明 env 不算，必须验行为」。behavior 语法：
    `{"<metric>": {"min": x}}` / `{"<metric>": {"max": x}}` / `{"<metric>": {"eq": x}}`，metric 见 C1。
C4 结构三项（`msgs` / `threads` / `ge3`）与 `--expect-struct` 相对差 ≤ tolerance。

指标定义（与 reports 口径一致）
    paren_rate      含括号块消息 / 消息数       （括号块 = `（…）` 或 `(…)`）
    len_p50          body 原始字符长度中位数（向上取整位）
    len_p50_excl     去括号块后长度中位数
    id_leak_rate     `P\\d{3}(?!\\d)` 命中 body 的消息占比
    dup_exact_rate   1 - 唯一(body) / 消息数（前 N 条内）
    msgs / threads / ge3   全量：消息数 / 线程数 / turn_index≥3 的线程数
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import statistics
import sys
from pathlib import Path

BR = re.compile(r"（[^（）]*）|\([^()]*\)")
ID = re.compile(r"P\d{3}(?!\d)")

R: list[tuple[str, str, str]] = []


def add(item: str, verdict: str, ev: str) -> None:
    R.append((item, verdict, ev))


def load(path: Path):
    recs = []
    bad = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError:
                bad += 1
    return recs, bad


def msg_bodies(recs, limit: int | None = None):
    out = []
    for r in recs:
        if not str(r.get("type", "")).startswith("MSG_"):
            continue
        b = (r.get("payload") or {}).get("body")
        out.append(str(b or ""))
        if limit is not None and len(out) >= limit:
            break
    return out


def metrics(bodies) -> dict:
    n = len(bodies) or 1
    raw = [len(b) for b in bodies]
    excl = [len(BR.sub("", b)) for b in bodies]
    return {
        "paren_rate": sum(1 for b in bodies if BR.search(b)) / n,
        "len_p50": statistics.median(raw) if raw else 0,
        "len_p50_excl": statistics.median(excl) if excl else 0,
        "id_leak_rate": sum(1 for b in bodies if ID.search(b)) / n,
        "dup_exact_rate": (1 - len(set(bodies)) / n) if bodies else 0.0,
    }


def struct_metrics(recs) -> dict:
    msgs = [r for r in recs if str(r.get("type", "")).startswith("MSG_")]
    th = collections.defaultdict(set)
    for m in msgs:
        pl = m.get("payload") or {}
        key = pl.get("thread_id") or ("DM+%s+%s" % (pl.get("from"), pl.get("to")))
        ti = pl.get("turn_index")
        th[key].add(ti if isinstance(ti, int) else -1)
    return {
        "msgs": len(msgs),
        "threads": len(th),
        "ge3": sum(1 for v in th.values() if len(v) >= 3),
    }


def near(actual: float, expect: float, tol: float) -> bool:
    if expect == 0:
        return abs(actual) <= tol
    if abs(expect) < 1:
        return abs(actual - expect) <= tol
    return abs(actual - expect) / abs(expect) <= tol


def main(argv=None) -> int:
    epilog = """指标口径（务必看清，避免两个数对不上）：
  * C1 的比较范围由 `--expect-scope` 决定：**默认 `full`（全 run）**；`first20` 为历史行为（仅前 --first-n 条）。
    **期望值必须与 scope 同源**——全 run 的 `len_p50` 喂给 `first20` 会造成「假红」（正常臂被误判 FAIL）。
  * `len_p50` = **原始 body 字符数**中位数（**不去括号**）；
  * `len_p50_excl` = 去括号块后的中位数；
  * `paren_rate` = 含括号块消息 / 消息数；`id_leak_rate` = 命中 P\\d{3} 的消息占比；
  * `dup_exact_rate` = 1 - 唯一(body)/消息数（前 N 条内）；
  * C4 的 `msgs/threads/ge3` 是**全批**口径。
参考值（A0 = run_d2_after_n16_seed42，686 条）：
  前 20 条：raw len_p50 = 38.5，去括号 = 33.0
  全批　　：raw len_p50 = 54.0，去括号 = 41.0
  A0 前 34 回合子集（D6 同窗口口径）：raw len_p50 = 48.0
  ⇒ 若你算到 47/48/54/38.5 中某个数，先确认「全批还是前N条」「原始还是去括号」，再比。
"""
    ap = argparse.ArgumentParser(epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--tree-expectation", default=None, help="JSON 或指向 .json 文件")
    ap.add_argument("--expect-struct", default=None, help="JSON：msgs/threads/ge3")
    ap.add_argument("--expect-provider", default=None)
    ap.add_argument("--expect-env", action="append", default=[], help="KEY=VAL，可多次")
    ap.add_argument("--expect-behavior", default=None, help="JSON：metric -> {min|max|eq}")
    ap.add_argument("--tolerance", type=float, default=0.05)
    ap.add_argument("--first-n", type=int, default=20)
    ap.add_argument("--expect-scope", choices=["first20", "full"], default="full",
                    help="C1 的比较范围：full=全 run（默认，与常见期望值同源）；first20=仅前 --first-n 条"
                         "（历史行为）。**期望值必须与 scope 同源**：全 run 的期望值不能喂给 first20。")
    a = ap.parse_args(argv)

    def as_json(s):
        if s is None:
            return None
        p = Path(s)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return json.loads(s)

    run = Path(a.run)
    if not run.exists():
        print(f"日志不存在: {run}", file=sys.stderr)
        return 2
    recs, bad = load(run)
    add("解析完整性", "FAIL" if bad else "PASS", f"坏行={bad}，记录={len(recs)}")

    bodies_first = msg_bodies(recs, a.first_n)
    bodies_full = msg_bodies(recs, None)
    bodies = bodies_full if a.expect_scope == "full" else bodies_first
    m = metrics(bodies)
    m_first = metrics(bodies_first)
    add("样本量", "PASS" if len(bodies_first) >= min(a.first_n, 1) else "FAIL",
        f"前 {a.first_n} 条取到 {len(bodies_first)} 条；全 run {len(bodies_full)} 条"
        f"（C1 比较范围 = {a.expect_scope}）")

    # ---- C0 provider ----
    prov = collections.Counter((r.get("payload") or {}).get("provider")
                               for r in recs if r.get("type") == "LLM_CALL")
    if not a.expect_provider:
        add("C0 provider", "CANNOT-VERIFY", f"未给 --expect-provider；实测={dict(prov)}")
    else:
        ok = set(prov) == {a.expect_provider}
        add("C0 provider", "PASS" if ok else "FAIL",
            f"期望 {{{a.expect_provider}}}；实测={dict(prov)}")

    # ---- C1 前 N 条指标 ----
    exp = as_json(a.tree_expectation)
    if not exp:
        add("C1 指标", "CANNOT-VERIFY",
            f"未给 --tree-expectation；scope={a.expect_scope} 实测={ {k: round(v,4) for k,v in m.items()} }")
    else:
        rows, bad_ = [], []
        for k, v in exp.items():
            if k not in m:
                bad_.append(f"{k}:未知指标")
                continue
            ok = near(m[k], float(v), a.tolerance)
            rows.append(f"{k} 实测={m[k]:.4f} 期望={v} {'ok' if ok else 'FAIL'}")
            if not ok:
                bad_.append(f"{k}({m[k]:.4f} vs {v})")
        add(f"C1 指标(scope={a.expect_scope})", "FAIL" if bad_ else "PASS",
            f"[比较范围={a.expect_scope}，n={len(bodies)}；len 为原始长度] " + "；".join(rows)
            + (f" ⇒ 超差：{bad_}" if bad_ else "")
            + f" ｜ 参考：前{a.first_n}条实测={ {k: round(v,4) for k,v in m_first.items()} }，"
              f"全run实测={ {k: round(v,4) for k,v in metrics(bodies_full).items()} }")

    # ---- C2 seals / WORLD_INIT ----
    seals = [(r.get("round"), r.get("seq")) for r in recs if r.get("type") == "TURN_SEAL"]
    rounds = [x[0] for x in seals if isinstance(x[0], int)]
    wi = sum(1 for r in recs if r.get("type") == "WORLD_INIT")
    problems = []
    if len(set(rounds)) != len(rounds):
        problems.append("seal 回合重复")
    if rounds != sorted(rounds):
        problems.append("seal 非单调")
    if wi != 1:
        problems.append(f"WORLD_INIT={wi}（应为 1）")
    add("C2 seals/初始化", "FAIL" if problems else "PASS",
        f"seals={len(seals)} 覆盖={min(rounds) if rounds else None}..{max(rounds) if rounds else None}；"
        f"WORLD_INIT={wi}；问题={problems or '无'}")

    # ---- C3 开关 ↔ 行为 ----
    beh = as_json(a.expect_behavior)
    if not a.expect_env:
        add("C3 开关↔行为", "PASS", "本批未声明开关（不涉及 env↔行为耦合检查）")
    elif not beh:
        add("C3 开关↔行为", "FAIL",
            f"声明了 env {a.expect_env} 但未给 --expect-behavior —— 「只声明 env 不算，必须验行为」")
    else:
        bad_ = []
        for k, spec in beh.items():
            if k not in m:
                bad_.append(f"{k}:未知指标")
                continue
            v = m[k]
            if "min" in spec and not v >= float(spec["min"]):
                bad_.append(f"{k}={v:.4f} < min {spec['min']}")
            if "max" in spec and not v <= float(spec["max"]):
                bad_.append(f"{k}={v:.4f} > max {spec['max']}")
            if "eq" in spec and not near(v, float(spec["eq"]), a.tolerance):
                bad_.append(f"{k}={v:.4f} != {spec['eq']}")
        add("C3 开关↔行为", "FAIL" if bad_ else "PASS",
            f"env={a.expect_env} 行为判据={beh}；违规={bad_ or '无'}")

    # ---- C4 结构 ----
    st = as_json(a.expect_struct)
    s = struct_metrics(recs)
    if not st:
        add("C4 结构", "CANNOT-VERIFY", f"未给 --expect-struct；实测={s}")
    else:
        bad_ = [f"{k}({s[k]} vs {v})" for k, v in st.items()
                if k in s and not near(s[k], float(v), a.tolerance)]
        add("C4 结构", "FAIL" if bad_ else "PASS",
            f"实测={s} 期望={st} ⇒ " + (f"超差：{bad_}" if bad_ else "一致"))

    for item, verdict, ev in R:
        print(f"[{verdict:<14}] {item}\n    {ev}")
    vs = [v for _, v, _ in R]
    overall = "FAIL" if "FAIL" in vs else ("CANNOT-VERIFY" if "CANNOT-VERIFY" in vs else "PASS")
    print(f"\n[汇总] {overall}  PASS={vs.count('PASS')} FAIL={vs.count('FAIL')} "
          f"CANNOT-VERIFY={vs.count('CANNOT-VERIFY')}（CANNOT-VERIFY ≠ PASS：未给期望的判据不放行）")
    return 1 if "FAIL" in vs else (2 if "CANNOT-VERIFY" in vs else 0)


if __name__ == "__main__":
    sys.exit(main())
