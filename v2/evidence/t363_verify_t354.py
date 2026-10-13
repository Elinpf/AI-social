"""T363 独立核验：T354 期②a（tick 内时间 · current_activity 消费 + 活性）。

非作者独立核验：不 import 作者测试 `code/tests/test_t354_current_activity.py`；
全部指标**从事件日志独立重算**（就地复现 current_activity 定义，见 _derived_cur）。

⚠️ 前置门：**必须等 T350 结束、Leader 广播「完全解冻」后才可跑**（本脚本含 3 次世界跑，属重活）。

用法：
    python v2/evidence/t363_verify_t354.py --seed 7 --n 8 --rounds 84
输出：stdout（人读表）+ 可选 --json <path>（机读）。

四项：
  ① 开关真通路（防 inert）：off vs 中和变体应**逐条相等**；on vs off 须有**族级差异表** + state_hash。
  ② 活性：进行中**连续回合长度分布** / 有无**永久进行中** / **逐人**零移动·零活动（点名个体）。
  ③ 作者证据三件前提（文件存在性 + 内容检查）——由本脚本 --check-author-evidence 旁路报告。
  ④ 无其它行为面偷跑：ACTIVITY_INTERRUPTED==0；`[ongoing:` 不出现在检索 query（扫 code/life）。
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
os.environ.setdefault("N50_VEC", "0")

from engine.runner import default_config          # noqa: E402
from engine.state import state_hash               # noqa: E402
from orchestration.integration import build_world  # noqa: E402
from contracts.actors import is_agent_actor       # noqa: E402


# --------------------------------------------------------------------------- #
# 独立重算 current_activity（与 08/实现同定义，但本文件自持副本，不调用作者函数）
# --------------------------------------------------------------------------- #
def _derived_cur(records, agent_id, upto_round):
    """返回该 agent 在 [0, upto_round] 末的『进行中』记录（None=无）。"""
    act = None
    for rec in records:
        if rec["round"] > upto_round:
            break
        t = rec["type"]
        if t not in ("ACTIVITY_STARTED", "ACTIVITY_COMPLETED"):
            continue
        p = rec.get("payload", {})
        if p.get("agent_id") != agent_id and rec.get("actor") != agent_id:
            continue
        act = ({"activity_type": p.get("activity_type"), "place": p.get("place")}
               if t == "ACTIVITY_STARTED" else None)
    return act


def _canon(recs):
    return [json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for r in recs]


def _family_counts(records):
    return collections.Counter(r["type"] for r in records)


def _first_diff(a_recs, b_recs):
    ca, cb = _canon(a_recs), _canon(b_recs)
    n = min(len(ca), len(cb))
    for i in range(n):
        if ca[i] != cb[i]:
            return i
    if len(ca) != len(cb):
        return n
    return None


def run_world(seed, n, rounds, ongoing, neutralize=False):
    """跑一个世界。neutralize=True：开关标 on，但把 ca 强制为 None（模拟 pre-T354 行为）。

    返回 (engine, records, state_hash)。
    """
    cfg = default_config()
    cfg.setdefault("time", {}).setdefault("ongoing", {})["enabled"] = bool(ongoing)
    w = build_world(seed=seed, n=n, config=cfg)
    eng = w["engine"]
    if neutralize:
        # 只中和 life 的消费入口：adapter.perceive 里读的 current_activity 恒 None
        ad = w["adapter"]
        ad._ongoing = False   # 与 off 同效；用于证明 off 与「无该字段」等价
    for r in range(rounds):
        eng.run_round(r)
    return eng, list(eng.ledger.records), state_hash(eng.state)


# --------------------------------------------------------------------------- #
# 活性分析
# --------------------------------------------------------------------------- #
def liveness(records, agents, rounds):
    """返回 per-agent 进行中连续段 + 永久进行中 + 零移动/零活动点名。"""
    out = {}
    for aid in sorted(agents):
        runs = []
        cur_len = 0
        seen_any = False
        for r in range(rounds + 1):
            if _derived_cur(records, aid, r) is not None:
                cur_len += 1
                seen_any = True
            else:
                if cur_len:
                    runs.append(cur_len)
                cur_len = 0
        permanent = _derived_cur(records, aid, rounds) is not None
        if cur_len:
            runs.append(cur_len)
        moves = sum(1 for rec in records
                    if rec["type"] in ("PLACE_MOVE", "PLACE_ARRIVED")
                    and rec.get("payload", {}).get("agent_id") == aid)
        acts = sum(1 for rec in records
                   if rec["type"] == "ACTIVITY_STARTED"
                   and rec.get("payload", {}).get("agent_id") == aid)
        out[aid] = {
            "runs": runs,
            "max_run": max(runs) if runs else 0,
            "permanent_in_progress": permanent,
            "moves": moves,
            "activities": acts,
            "zero_move": moves == 0,
            "zero_activity": acts == 0,
            "ever_in_progress": seen_any,
        }
    return out


def _report_liveness(liv, rounds):
    print("\n[② 活性] 逐人（不得只看均值）：")
    print(f"{'agent':<8}{'max_run':>8}{'permanent':>10}{'moves':>8}{'acts':>6}{'zero_move':>10}{'zero_act':>9}  runs")
    permanent_agents = []
    stalled = []
    for aid, d in liv.items():
        print(f"{aid:<8}{d['max_run']:>8}{str(d['permanent_in_progress']):>10}"
              f"{d['moves']:>8}{d['activities']:>6}{str(d['zero_move']):>10}"
              f"{str(d['zero_activity']):>9}  {d['runs'][:12]}")
        if d["permanent_in_progress"]:
            permanent_agents.append(aid)
        # 卡死定义（照 T363 措辞）= 永久进行中**导致不再行动**：整周零移动且零活动。
        if d["zero_move"] and d["zero_activity"]:
            stalled.append(aid)
    all_runs = [x for d in liv.values() for x in d["runs"]]
    if all_runs:
        print(f"  连续段长度分布：n={len(all_runs)} min={min(all_runs)} "
              f"max={max(all_runs)} mean={sum(all_runs)/len(all_runs):.2f}")
    print(f"  『永久进行中』个体（观察项，非=卡死）：{permanent_agents or '无'}")
    print(f"  ⚠️ 卡死个体（整周零移动且零活动 ⇒ gate）：{stalled or '无'}")
    return stalled, permanent_agents


# --------------------------------------------------------------------------- #
def _check_author_evidence():
    """③ 作者证据三件前提。返回 (verdict, notes)。

    verdict ∈ {"ok", "未补", "补了不合规"} —— 按 Leader 裁定：两种整改动作不同，不得混为一句。
    """
    notes = []
    cand = [f for f in (ROOT / "v2" / "evidence").glob("*T354*") if "363" not in f.name]
    if not cand:
        return "未补", ["v2/evidence/ 下无任何 T354 专用作者证据文件 ⇒ 判【未补】"
                        "（在 T350 前=预期；在跑重活那一刻仍缺=不合格，但判词须写『未补』）"]
    bad = []
    for f in cand:
        txt = f.read_text(encoding="utf-8", errors="replace")
        has_sha = bool(re.search(r"\b[0-9a-f]{7,40}\b", txt))
        has_uncommitted = ("未提交" in txt) or ("WIP" in txt) or ("uncommitted" in txt)
        has_notrepro = ("不可复现" in txt) or ("not reproducible" in txt.lower())
        has_design_only = ("仅设计验证" in txt) or ("不作" in txt and "epoch" in txt)
        miss = [n for n, ok in [("绑sha", has_sha), ("逐文件未提交清单", has_uncommitted),
                                ("该sha不可复现声明", has_notrepro), ("仅设计验证/不作epoch对照", has_design_only)]
                if not ok]
        notes.append(f"{f.name}: 缺={miss or '无'}")
        if miss:
            bad.append((f.name, miss))
    if bad:
        return "补了不合规", notes
    return "ok", notes


def _check_no_leak():
    """④ ACTIVITY_INTERRUPTED==0（本期不做）+ `[ongoing:` 不出现。"""
    intr = 0
    ongoing_tag = []
    for p in (ROOT / "code").rglob("*.py"):
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "[ongoing:" in t:
            ongoing_tag.append(str(p.relative_to(ROOT)))
    return intr, ongoing_tag


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--rounds", type=int, default=84)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    rep = {"seed": args.seed, "n": args.n, "rounds": args.rounds}

    # ---- ① 开关真通路 ---- #
    eng_on, recs_on, h_on = run_world(args.seed, args.n, args.rounds, ongoing=True)
    eng_off, recs_off, h_off = run_world(args.seed, args.n, args.rounds, ongoing=False)
    eng_neu, recs_neu, h_neu = run_world(args.seed, args.n, args.rounds, ongoing=True, neutralize=True)

    fc_on, fc_off = _family_counts(recs_on), _family_counts(recs_off)
    fams = sorted(set(fc_on) | set(fc_off))
    delta = {f: fc_on.get(f, 0) - fc_off.get(f, 0) for f in fams}
    delta = {k: v for k, v in delta.items() if v}

    print("\n[① 开关真通路]")
    print(f"  on : len={len(recs_on)}  state_hash={h_on}")
    print(f"  off: len={len(recs_off)} state_hash={h_off}")
    print(f"  neu: len={len(recs_neu)} state_hash={h_neu}  （开关 on 但 ca 强制 None）")
    print(f"  on vs off  族级 delta：{delta or '（无差异 ⇒ 疑似 inert/未被消费！）'}")
    print(f"  on vs off 首个差异 seq：{_first_diff(recs_on, recs_off)}")
    fc_neu = _family_counts(recs_neu)

    def _nohash(rs):
        return [json.dumps({k: v for k, v in r.items() if k not in ("hash", "prev_hash")},
                           ensure_ascii=False, sort_keys=True, separators=(",", ":")) for r in rs]

    cn_off, cn_neu = _nohash(recs_off), _nohash(recs_neu)
    diff_stripped = [i for i in range(min(len(cn_off), len(cn_neu))) if cn_off[i] != cn_neu[i]]
    diff_types = sorted({recs_off[i]["type"] for i in diff_stripped})
    # 行为等价判据：state_hash 相等（折叠世界态，权威）+ 族计数相等
    # + 去哈希链后差异仅限【指纹行及其链派生】：WORLD_INIT(config 摘要) 与 TURN_SEAL(last_hash)。
    off_eq_neu = (h_off == h_neu and fc_off == fc_neu
                  and set(diff_types) <= {"WORLD_INIT", "TURN_SEAL"})
    print(f"  off ≡ neu（行为等价：state_hash 相等 + 族计数相等 + 去哈希链后差异仅指纹行及其链派生）：{off_eq_neu}")
    print(f"    去哈希链后差异行 seq={diff_stripped[:8]} 类型={diff_types}"
          f"（= WORLD_INIT 运行时 config 摘要 + TURN_SEAL.last_hash 链级联，均非行为）")
    rep["on_off_delta"] = delta
    rep["on_len"], rep["off_len"] = len(recs_on), len(recs_off)
    rep["state_hash"] = {"on": h_on, "off": h_off, "neu": h_neu}
    rep["off_eq_neutralized"] = off_eq_neu
    rep["consumed"] = bool(delta) or (h_on != h_off)

    # ---- ② 活性（用 on 跑，最不利情形）---- #
    agents = sorted(a for a in eng_on.state.agents if is_agent_actor(a))
    liv = liveness(recs_on, agents, args.rounds)
    stalled, permanent_agents = _report_liveness(liv, args.rounds)
    rep["liveness"] = liv
    rep["stalled_agents"] = stalled
    rep["permanent_in_progress_agents"] = permanent_agents

    # ---- ③ 作者证据 ---- #
    ev_verdict, ev_notes = _check_author_evidence()
    print("\n[③ 作者证据三件前提]")
    for nline in ev_notes:
        print("  " + nline)
    print(f"  判定：{ev_verdict}")
    rep["author_evidence_verdict"] = ev_verdict

    # ---- ④ 无其它行为面偷跑 ---- #
    _, ongoing_tag = _check_no_leak()
    intr = fc_on.get("ACTIVITY_INTERRUPTED", 0)
    print("\n[④ 无其它行为面偷跑]")
    print(f"  ACTIVITY_INTERRUPTED 事件数（on）= {intr}（本期不做 ⇒ 期望 0）")
    print(f"  code/ 内 `[ongoing:` 残留：{ongoing_tag or '无'}")
    rep["activity_interrupted"] = intr
    rep["ongoing_tag_residue"] = ongoing_tag

    # ---- 结论 ----
    verdict = []
    if not rep["consumed"]:
        verdict.append("FAIL①：开/关无差异 ⇒ 疑似 inert（current_activity 未被 life 消费）")
    if not off_eq_neu:
        verdict.append("FAIL①：off 与中和变体行为不等价 ⇒ 关态存在其它隐藏依赖")
    if stalled:
        verdict.append(f"FAIL②（gate）：存在卡死个体 {stalled} ⇒ T354 回炉 + T353 回归")
    elif permanent_agents:
        verdict.append(f"②gate：无『不再行动』个体 ⇒ gate 未触发（pass）；但『永久进行中』普遍存在"
                       f"{permanent_agents[:8]}{'…' if len(permanent_agents) > 8 else ''} —— 见风险说明")
    if ev_verdict != "ok":
        verdict.append(f"③：作者证据【{ev_verdict}】（未补/不合规须分列，整改动作不同）")
    if intr != 0:
        verdict.append(f"FAIL④：ACTIVITY_INTERRUPTED={intr}（本期应 0）")
    rep["verdict"] = verdict or ["四项无 FAIL 证据（细节见上）"]
    print("\n[结论]")
    for v in rep["verdict"]:
        print("  - " + v)

    if args.json:
        Path(args.json).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n(机读报告：{args.json})")


if __name__ == "__main__":
    main()
