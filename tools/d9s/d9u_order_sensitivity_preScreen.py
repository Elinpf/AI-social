#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D9u 顺序敏感检查（只读）——**与词表版本解耦**。

背景（2026-10-31 修）：v1 版本脚本写死"旧表=21 词、追加到 verbs_rotation_13 尾部"，
在 lexicon 升到 **v2.0（43 词，含 verbs_expansion_22）** 后必然断言失败（会插在 expansion_22 之前）。
⇒ 本版改为 **显式传旧表 + 自动识别"最后一个动词表"**，任何表版本都能跑。

用法（在 code/ 下）：
  # 默认：以 v1.1 快照为旧表（复算 D9u 立项时的那次检查）
  python3 ../tools/d9s/d9u_order_sensitivity.py
  # 以"当前表"为旧表（检查下一批新词追加是否仍顺序不敏感）
  python3 ../tools/d9s/d9u_order_sensitivity.py --old-lexicon current
  # 指定任意旧表
  python3 ../tools/d9s/d9u_order_sensitivity.py --old-lexicon ../tools/d9s/lexicon_v1.1_snapshot.json

三条口径（Leader 确认）：
  1. 新词只**追加到最后一个动词表**（v1.1=rotation_13 尾；v2.0=expansion_22 尾），顺序即语义；
  2. 只读对拍：全部走 `narration_family.analyse` / `assign_family`，**不写第二份实现**；
  3. 判据 A 顺序不敏感（旧词 counts 不变 + 含旧词片段改族 0）**与** 判据 B 总量变化（只登记）**分开**。
"""
from __future__ import annotations
import argparse, copy, json, sys
from pathlib import Path

#: **实现版本必须与所传 lexicon 同版本**：优先用"当前工作树"的 tools/d9n（cwd=<tree>/code 时），
#: 找不到再用脚本自身所在树的 tools/d9n。两处都没有才报错。
_CAND_D9N = [Path.cwd().parent / "tools" / "d9n", Path(__file__).resolve().parents[1] / "d9n"]
for _c in _CAND_D9N:
    if (_c / "narration_family.py").exists():
        sys.path.insert(0, str(_c))
        break
import narration_family as NF  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[4]          # 主仓根（本脚本可能在工作树里跑）
DEFAULT_OLD = HERE / "lexicon_v1.1_snapshot.json"   # v1.1（21 词）逐字节快照，sha256 01e55338…

#: D9u 第一步的 31 个真新增候选；运行时**自动剔除旧表里已有的**（v2.0 下只剩 9 个）
NEW_VERBS = ["搁", "压", "推", "摊", "翻", "蹲", "按", "掀", "拨", "包", "捏", "响", "点", "敲",
             "算", "卷", "插", "夹", "凿", "绕", "停", "走", "码", "摸", "锤", "转", "磨", "蒸",
             "烧", "咬", "缝"]

ARMS = {
    "H0(narr-on)": REPO / "v2/evidence/narr-on-20261030/run.jsonl",
    "A_only(d9n-rot)": REPO / "v2/evidence/d9n-rot-20261030/run.jsonl",
    "A+B(d9m-ab-on)": REPO / ".worktrees/narration-action-diversity/runs/d9m-ab-on_n16r24_s42/run.jsonl",
    "OFF_run1(d9s-syntax-off)": REPO / "v2/evidence/d9s-syntax-off_n16r24_s42/run.jsonl",
    "ON2(d9s-on2)": REPO / "v2/evidence/d9s-on2_n16r24_s42/run.jsonl",
}


def last_verbs_key(lex: dict) -> str:
    """返回"最后一个动词表"的键名（V_judge 的尾部；v1.1=rotation_13，v2.0=expansion_22）。"""
    for k in ("verbs_expansion_22", "verbs_rotation_13", "verbs_closed_8"):
        if k in lex:
            return k
    raise KeyError("lexicon 里找不到任何 verbs_* 表")


def extend(lex: dict, verbs: list) -> tuple[dict, str]:
    k = last_verbs_key(lex)
    new = copy.deepcopy(lex)
    new[k] = list(lex[k]) + list(verbs)
    return new, k


def metrics(lex: dict, log: Path) -> dict:
    d = NF.analyse(log, lex)
    vc = {k: v for k, v in (d.get("verb_counts") or {}).items() if v}
    return dict(max_v=d["max_v"]["value"], max_v_verb=d["max_v"]["verb"], d2=len(vc),
                b2=len((d.get("b2p") or {}).get("offenders") or []), max_k=d["max_k"],
                unassigned=d["unassigned_verb_rate"], blocks=d["blocks_total"])


def main() -> int:
    print("【口径强制声明】起点表版本见 --old-lexicon / 词数=52 / 口径=筛前(31 候选全收,非正式) / 本脚本读数不得作为正式判据")

    ap = argparse.ArgumentParser()
    ap.add_argument("--old-lexicon", default=str(DEFAULT_OLD),
                    help="旧表路径；传 'current' 表示用主仓当前 lexicon")
    ap.add_argument("--new-verbs", default=",".join(NEW_VERBS))
    a = ap.parse_args()

    old_path = Path(NF.DEFAULT_LEXICON) if a.old_lexicon == "current" else Path(a.old_lexicon)
    old = NF.load_lexicon(old_path)
    V_old = NF.v_judge(old)
    # ⚠ 版本一致性硬检查（2026-10-31 加）：lexicon 的 verbs_* 必须都被本次运行的 v_judge 消费
    _vb_keys = [k for k in old if str(k).startswith("verbs_")]
    _consumed = sum(len(old[k]) for k in _vb_keys if k in ("verbs_closed_8", "verbs_rotation_13"))
    if any(k == "verbs_expansion_22" for k in _vb_keys) and len(V_old) == _consumed:
        raise SystemExit(
            "!! 版本不一致：所传 lexicon 含 verbs_expansion_22，但本次运行的 narration_family.v_judge\n"
            f"   只读 closed_8+rotation_13（{len(V_old)} 词），未消费 expansion ⇒ 实现比词表旧。\n"
            "   请在该 lexicon 所属的那棵树的 code/ 下运行本脚本（脚本会优先用 cwd 的 tools/d9n），\n"
            "   或改用 --old-lexicon 指向与本实现同版本的表。")
    cand = [w for w in a.new_verbs.split(",") if w]
    fresh = [w for w in cand if w not in V_old]          # **自动剔除旧表已有**
    skipped = [w for w in cand if w in V_old]
    new, key = extend(old, fresh)

    print(f"旧表: {old_path}  V_judge={len(V_old)} 词  最后一个动词表 = {key}")
    print(f"候选 {len(cand)} 个 → 新增 {len(fresh)} 个；旧表已含而跳过 {len(skipped)} 个 {skipped if skipped else ''}")
    # 硬断言：追加点必须让旧词序原样保留
    assert NF.v_judge(new)[:len(V_old)] == V_old, "追加点不对：旧词序被改变"
    assert len(NF.v_judge(new)) == len(V_old) + len(fresh)
    print(f"新表 V_judge={len(NF.v_judge(new))} 词；前 {len(V_old)} 项与旧表逐项相同 ✔")
    if not fresh:
        print("⇒ 无新增词，无可检查（脚本仍可安全运行）")
        return 0

    rows = []
    for name, log in ARMS.items():
        if not log.exists():
            print(f"!! 缺文件：{log}")
            continue
        rows.append((name, log, metrics(old, log), metrics(new, log)))

    print(f"\n{'臂':26}{'max_v 旧→新':>20}{'(d2) 旧→新':>14}{'b2′ 旧→新':>13}{'max_k 旧→新':>13}{'未归族率':>17}")
    for name, _, o, n in rows:
        mv = f"{o['max_v']}({o['max_v_verb']})→{n['max_v']}({n['max_v_verb']})"
        d2 = f"{o['d2']}→{n['d2']}"
        b2 = f"{o['b2']}→{n['b2']}"
        mk = f"{o['max_k']}→{n['max_k']}"
        un = f"{round(100*o['unassigned'],1)}%→{round(100*n['unassigned'],1)}%"
        print(f"{name:26}{mv:>20}{d2:>14}{b2:>13}{mk:>13}{un:>17}")

    print("\n【判据 A｜顺序不敏感】旧词 per-verb counts 不变 且 含旧词片段逐片归族 0 变化")
    bad = 0
    for name, log, o, n in rows:
        msgs = NF.extract_messages(NF.read_log(log))
        frags = [b[1:-1] for m in msgs for b in NF.PAIRED_RE.findall(m.get("body") or "")]
        diff = sum(1 for f in frags
                   if any(v in f for v in V_old)
                   and NF.assign_family(f, V_old, old["parts_6"], old["objs_13"])
                   != NF.assign_family(f, NF.v_judge(new), new["parts_6"], new["objs_13"]))
        bad += diff
        print(f"  {name:26} 含旧词片段改族 = {diff} 片")
    print(f"  ⇒ 合计改族 {bad} 片；{'**顺序不敏感（通过）**' if bad == 0 else '!! 有改族，追加点不对'}")

    print("\n【判据 B｜总量变化】只登记不设阈（扩表必然把 unassigned 收编 ⇒ max_v 上升，不是缺陷）")
    for name, _, o, n in rows:
        print(f"  {name:26} Δmax_v = {n['max_v'] - o['max_v']:+d}   Δ(d2) = {n['d2'] - o['d2']:+d}"
              f"   Δ未归族 = {round(100 * (n['unassigned'] - o['unassigned']), 1):+.1f}pp")

    print("\n【`搁` 专项】只吃『不含任何旧动词』的片段 ⇒ 追加末尾不会顶掉旧词的首次命中")
    for name, log, _, _ in rows:
        msgs = NF.extract_messages(NF.read_log(log))
        frags = [b[1:-1] for m in msgs for b in NF.PAIRED_RE.findall(m.get("body") or "")]
        hit = [f for f in frags if "搁" in f]
        eaten = [f for f in hit if not any(v in f for v in V_old)]
        print(f"  {name:26} 含『搁』={len(hit):3d}  仍归旧族={len(hit) - len(eaten):3d}  新归『搁』={len(eaten):3d}")

    json.dump([dict(arm=n, old=o, new=nn) for n, _, o, nn in rows],
              open("/tmp/d9u_order_sensitivity.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n（JSON: /tmp/d9u_order_sensitivity.json）")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
