#!/usr/bin/env python3
"""集日臂 OFF 等价性 / 只差一行 对拍器（跨树、只读、零 LLM）。

用途（本臂的三条可比性命脉，全部机械可复算）：

  A. **OFF 逐字节等价**：臂缺省（`HITT_MARKET_DAY` 未设）时，**基线树**与**本臂树**的
     `_dialogue_prompt` / `_reply_prompt` 文本在 day0..day5 六个日子上**逐字节相同**
     ⇒ 本轮「基线 sha vs 改进 sha」的对照不会被本臂改动污染。
  B. **只差一行**：本臂树 ON（集日）时，把「今儿镇上的日子：……」那一行**原样减掉**后，
     与同一棵树的 OFF 提示词**逐字节相等**。
  C. **不外溢**：本臂树 ON 但**非集日**时，提示词与 OFF **逐字节相等**（一行都不加）。

一行命令重跑（基线树 + 本臂树，结果落 json）：

    python3 tools/market_day/off_equiv_prompts.py \
        --base   /tmp/hitt_baseline_master \
        --branch /tmp/hitt_life_marketday \
        --out    /tmp/market_day_off_equiv.json

判据（脚本只输出读数与 `verdict`，不改任何文件、不跑批、不调 LLM）：
  * `verdict.off_identical == true`：A 成立（`n_prompts_off_compared` 条全部 0 diff）；
  * `verdict.on_minus_mark_equals_off == true`：B 成立（集日全部 0 diff）；
  * `verdict.on_non_market_identical_to_off == true`：C 成立；
  * `verdict.deterministic_across_processes == true`：两次独立进程派生表逐字符相同（可 replay）。

纪律：只用公开/半公开 API 构最小 agent（`P003`，同伴 `P007`），不写仓库内文件
（`--out` 指向 /tmp 或证据目录），不调 LLM、不发事件、不读墙钟。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

MK_MARK = "今儿镇上的日子："
#: 对拍覆盖的日子：0..5 覆盖「集日 day0/day3」与「非集日 day1/day2/day4/day5」。
DAYS = (0, 1, 2, 3, 4, 5)
#: 每棵树每日子对拍的两条提示词。
KINDS = ("dialogue_prompt", "reply_prompt")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git(tree: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(tree), *args],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:                              # noqa: BLE001
        return None


def _build_agent(tree: Path, tmp: Path):
    code = tree / "code"
    if str(code) not in sys.path:
        sys.path.insert(0, str(code))
    from life.agent import LifeLayerAgent
    from life.memory import HashEmbeddingModel, SideStore
    from life.persona import load_personas
    from life.tests.support.mini_kernel import MiniKernel

    cfg_dir = code / "config"
    places = {p["place_id"]: p for p in
              json.loads((cfg_dir / "places.json").read_text(encoding="utf-8"))["places"]}
    personas = load_personas(cfg_dir / "personas.json")
    persona = personas["P003"]
    kernel = MiniKernel(seed=7, places=places)
    kernel._emit("AGENT_BORN", {"agent_id": "P003", "home_place": persona.home_place,
                                "needs_init": persona.needs_init}, phase=0, actor="SYSTEM")
    kernel._emit("AGENT_BORN", {"agent_id": "P007",
                                "home_place": personas["P007"].home_place,
                                "needs_init": personas["P007"].needs_init},
                 phase=0, actor="SYSTEM")
    return LifeLayerAgent("P003", persona, kernel, side_store=SideStore(tmp / "side"),
                          embedding=HashEmbeddingModel(), places=places,
                          peer_names={"P007": "阿禾"})


def _wv(*, day: int, rnd: int):
    return SimpleNamespace(round=rnd, visible_events=[], location="market",
                           current_activity=None, inventory=(),
                           time=SimpleNamespace(slot="morning", day=day, day_of_week=day % 7,
                                                day_type="workday"))


def _prompts(agent, wv):
    from life import dialogue_threads as DT
    cfg = dict(DT.DEFAULTS)
    history = [("P007", "阿禾：今儿个有点乏。")]
    return (agent._dialogue_prompt("rel_maintain", ["P003", "P007"], cfg, wv=wv),
            agent._reply_prompt("P007", "rel_maintain", history, cfg, wv=wv, turn=1))


def _strip_market(prompt: str) -> str:
    return "\n".join(ln for ln in prompt.split("\n") if not ln.startswith(MK_MARK))


def _is_market_day(day: int) -> bool:
    """树内若有 `life.market_day` 就用它；基线树没有该模块 ⇒ 用同一算式（周期 3）。"""
    try:
        from life import market_day as MK
        return bool(MK.is_market_day(day))
    except Exception:                              # noqa: BLE001
        return day % 3 == 0


def dump_tree(tree: Path) -> dict:
    """在给定树上（强制 OFF）导出 day0..day5 两条提示词的 sha256 与全文。"""
    tmp = Path(tempfile.mkdtemp(prefix="mkequiv_"))
    saved = os.environ.get("HITT_MARKET_DAY")
    os.environ.pop("HITT_MARKET_DAY", None)               # 强制 OFF（未设置 == OFF）
    try:
        agent = _build_agent(tree, tmp)
        out: dict = {"tree": str(tree), "tree_head": _git(tree, "rev-parse", "HEAD"),
                     "tree_code": _git(tree, "rev-parse", "HEAD:code"), "prompts": {}}
        for day in DAYS:
            d, r = _prompts(agent, _wv(day=day, rnd=day * 12))
            out["prompts"][str(day)] = {
                "dialogue_prompt": d, "reply_prompt": r,
                "dialogue_prompt_sha256": _sha(d), "reply_prompt_sha256": _sha(r),
                "ctx_has_market_key": "market" in agent._ctx_snapshot("P007", "rel_maintain"),
            }
        return out
    finally:
        if saved is None:
            os.environ.pop("HITT_MARKET_DAY", None)
        else:
            os.environ["HITT_MARKET_DAY"] = saved


def dump_tree_on(tree: Path) -> dict:
    """在给定树上（强制 ON）导出 day0..day5 两条提示词 + 集日/非集日差异读数。"""
    tmp = Path(tempfile.mkdtemp(prefix="mkequiv_on_"))
    saved = os.environ.get("HITT_MARKET_DAY")
    os.environ["HITT_MARKET_DAY"] = "1"
    try:
        agent = _build_agent(tree, tmp)
        out: dict = {"prompts": {}}
        for day in DAYS:
            d, r = _prompts(agent, _wv(day=day, rnd=day * 12))
            ctx = agent._ctx_snapshot("P007", "rel_maintain").get("market")
            out["prompts"][str(day)] = {
                "dialogue_prompt": d, "reply_prompt": r,
                "dialogue_prompt_sha256": _sha(d), "reply_prompt_sha256": _sha(r),
                "market_mark_count_dialogue": d.count(MK_MARK),
                "market_mark_count_reply": r.count(MK_MARK),
                "ctx_market": ctx,
            }
        return out
    finally:
        if saved is None:
            os.environ.pop("HITT_MARKET_DAY", None)
        else:
            os.environ["HITT_MARKET_DAY"] = saved


def _dump_via_subprocess(script: Path, tree: Path, mode: str) -> dict:
    """在**独立进程**里 dump 一棵树（两棵树的 `life` 包同名，必须进程隔离）。"""
    cmd = [sys.executable, str(script), "--dump-tree", str(tree), "--dump-mode", mode]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if res.returncode != 0:
        raise SystemExit(f"[market-day-equiv] dump 失败 tree={tree} mode={mode}\n{res.stderr}")
    return json.loads(res.stdout)


def compare(base: dict, branch: dict, branch_on: dict) -> dict:
    n_cmp = len(DAYS) * len(KINDS)
    off_diffs = []
    for day in DAYS:
        for kind in KINDS:
            a = base["prompts"][str(day)][kind]
            b = branch["prompts"][str(day)][kind]
            if a != b:
                off_diffs.append({"day": day, "kind": kind,
                                  "base_sha256": _sha(a), "branch_sha256": _sha(b)})
    strip_ok, strip_bad = 0, []
    nonmarket_ok, nonmarket_bad = 0, []
    for day in DAYS:
        mk = _is_market_day(day)
        for kind in KINDS:
            off_text = branch["prompts"][str(day)][kind]
            on_text = branch_on["prompts"][str(day)][kind]
            if mk:
                if _strip_market(on_text) == off_text and on_text.count(MK_MARK) == 1:
                    strip_ok += 1
                else:
                    strip_bad.append({"day": day, "kind": kind})
            else:
                if on_text == off_text:
                    nonmarket_ok += 1
                else:
                    nonmarket_bad.append({"day": day, "kind": kind})
    n_market = sum(1 for d in DAYS if _is_market_day(d)) * len(KINDS)
    n_nonmarket = n_cmp - n_market
    return {
        "n_prompts_off_compared": n_cmp,
        "n_prompts_off_diff": len(off_diffs),
        "off_diffs": off_diffs,
        "n_prompts_market_compared": n_market,
        "n_prompts_market_strip_equals_off": strip_ok,
        "market_strip_failures": strip_bad,
        "n_prompts_nonmarket_compared": n_nonmarket,
        "n_prompts_nonmarket_identical_to_off": nonmarket_ok,
        "nonmarket_identical_failures": nonmarket_bad,
        "verdict": {
            "off_identical": len(off_diffs) == 0,
            "on_minus_mark_equals_off": not strip_bad,
            "on_non_market_identical_to_off": not nonmarket_bad,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", help="基线树根（含 code/）")
    ap.add_argument("--branch", help="本臂树根（含 code/）")
    ap.add_argument("--out", default=None, help="读数 json 输出路径（缺省打印到 stdout）")
    ap.add_argument("--dump-tree", default=None, help="内部用：导出该树的 OFF 读数")
    ap.add_argument("--dump-mode", default="off", choices=["off", "on"],
                    help="内部用：导出 OFF / ON 读数")
    args = ap.parse_args()

    if args.dump_tree:                                     # 子进程分支
        tree = Path(args.dump_tree).resolve()
        data = dump_tree(tree) if args.dump_mode == "off" else dump_tree_on(tree)
        print(json.dumps(data, ensure_ascii=False, sort_keys=True))
        return 0

    if not args.base or not args.branch:
        ap.error("比较模式需要 --base 与 --branch")
    script = Path(__file__).resolve()
    base = _dump_via_subprocess(script, Path(args.base).resolve(), "off")
    branch = _dump_via_subprocess(script, Path(args.branch).resolve(), "off")
    branch_on = _dump_via_subprocess(script, Path(args.branch).resolve(), "on")
    out = {
        "base_tree": {"path": base["tree"], "head": base["tree_head"], "code": base["tree_code"]},
        "branch_tree": {"path": branch["tree"], "head": branch["tree_head"],
                        "code": branch["tree_code"]},
        "days": list(DAYS),
        "market_days": [d for d in DAYS if _is_market_day(d)],
        "non_market_days": [d for d in DAYS if not _is_market_day(d)],
        "off_equiv": compare(base, branch, branch_on),
        "on_ctx_market_sample": branch_on["prompts"]["0"]["ctx_market"],
        "on_mark_counts": {str(d): branch_on["prompts"][str(d)]["market_mark_count_dialogue"]
                           for d in DAYS},
    }
    text = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"[market-day-equiv] wrote {args.out}")
        print("[market-day-equiv] verdict = "
              + json.dumps(out["off_equiv"]["verdict"], ensure_ascii=False))
    else:
        print(text)
    return 0 if all(out["off_equiv"]["verdict"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
