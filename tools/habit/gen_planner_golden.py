#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成/校验 `planner.plan_slot` 的 **OFF 臂黄金夹具**（F-5 生活气息臂的消融前提）。

目的：证明「`HITT_LIVING_SLOT` 未设时，`code/life/planner.py` 的 `plan_slot` 与 master
`d2d1993` 的实现产出**逐字节相同的计划**」。做法是**直接执行 baseline 版本源码**
（`git show <BASE>:code/life/planner.py` 落到临时目录后 import），对同一批
(agent, day_type, slot, slot_id, cash, focus) 输入收集输出，落盘成 JSON 夹具；
单测 `code/life/tests/test_habit_living_slot.py` 再用当前树实现跑同一批输入，逐条比对。

用法（仓库根，只读 + 只在 /tmp 写临时文件；**不需要跑批、不需要 LLM**）：
    python3 tools/habit/gen_planner_golden.py --base d2d1993 \
        --out code/life/tests/support/planner_off_golden.json
    # 只校验不落盘：
    python3 tools/habit/gen_planner_golden.py --base d2d1993 --check

退出码：0 = 一致/已生成；1 = 与既有夹具不一致（夹具漂移或 OFF 臂被改动）；2 = 环境不可用。
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
AGENTS = [f"P{i:03d}" for i in range(1, 5)]
PEERS = [f"P{i:03d}" for i in range(1, 17)]
DAY_TYPES = ["workday", "weekend"]
SLOTS = ["morning", "afternoon", "evening", "night"]
SLOT_IDS = [f"day{d}-{s}" for d in range(7) for s in SLOTS]
CASHES = [0, 50, 120]
FOCUSES = [None, "work", "leisure", "balance"]


def _child_rows(pkg_root: Path) -> list:
    """在**子进程**里用指定包根跑同一批输入（隔离 baseline/current 两套 `life` 包）。"""
    runner = (
        "import json,sys;"
        "root=sys.argv[1];"
        "sys.path.insert(0,root);"
        "from life.planner import Planner;"
        "cfg=sys.argv[2];"
        "import os;"
        "tpl={t['template_id']:t for t in json.load(open(os.path.join(cfg,'activity_templates.json')))['templates']};"
        "plc={p['place_id']:p for p in json.load(open(os.path.join(cfg,'places.json')))['places']};"
        "agents=json.loads(sys.argv[3]);peers=json.loads(sys.argv[4]);spec=json.loads(sys.argv[5]);"
        "rows=[]\n"
        "for agent in agents:\n"
        "    p=Planner(agent,tpl,peers,plc)\n"
        "    for dt,slot,sid,cash,focus in spec:\n"
        "        rows.append([agent,dt,slot,sid,cash,focus,p.plan_slot(dt,slot,sid,cash,focus)])\n"
        "print(json.dumps(rows,ensure_ascii=False))\n"
    )
    spec = [[dt, sl, sid, cash, focus]
            for dt in DAY_TYPES for sl in SLOTS for sid in SLOT_IDS
            if sid.endswith("-" + sl) for cash in CASHES for focus in FOCUSES]
    out = subprocess.run([sys.executable, "-c", runner, str(pkg_root), str(REPO / "code" / "config"),
                          json.dumps(AGENTS), json.dumps(PEERS), json.dumps(spec)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        print("[golden] child failed:\n" + out.stderr[-4000:], file=sys.stderr)
        raise SystemExit(2)
    return json.loads(out.stdout)


def _baseline_pkgroot(base: str, tmp: Path) -> Path:
    """把 baseline 的 life 包（planner.py + util.py + __init__.py）取到临时包根。"""
    root = tmp / "pkg"
    dst = root / "life"
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "__init__.py").write_text("", encoding="utf-8")
    for name in ("planner.py", "util.py"):
        out = subprocess.run(["git", "-C", str(REPO), "show", f"{base}:code/life/{name}"],
                             capture_output=True, text=True)
        if out.returncode != 0:
            print(f"[golden] git show {base}:code/life/{name} failed: {out.stderr.strip()}",
                  file=sys.stderr)
            raise SystemExit(2)
        (dst / name).write_text(out.stdout, encoding="utf-8")
    return root


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="d2d1993", help="baseline sha（OFF 臂语义锚）")
    ap.add_argument("--out", default=None, help="夹具落盘路径")
    ap.add_argument("--check", action="store_true", help="只校验当前树与夹具/基线是否一致")
    a = ap.parse_args(argv)

    cur_rows = _child_rows(REPO / "code")

    if a.check and a.out and Path(a.out).is_file():
        golden = json.loads(Path(a.out).read_text(encoding="utf-8"))["rows"]
        now = cur_rows
        if now != golden:
            for i, (x, y) in enumerate(zip(now, golden)):
                if x != y:
                    print(f"[golden] MISMATCH at row {i}:\n  now   ={x}\n  golden={y}",
                          file=sys.stderr)
                    break
            return 1
        print(f"[golden] CHECK OK: {len(now)} rows identical (base={a.base})")
        return 0

    with tempfile.TemporaryDirectory() as td:
        rows = _child_rows(_baseline_pkgroot(a.base, Path(td)))

    if a.out:
        p = Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"base": a.base, "schema": "planner-off-golden/1.0",
                                 "n_rows": len(rows), "rows": rows},
                                ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"[golden] wrote {p} rows={len(rows)}")
    now = cur_rows
    if now != rows:
        for i, (x, y) in enumerate(zip(now, rows)):
            if x != y:
                print(f"[golden] MISMATCH baseline vs current at row {i}:\n"
                      f"  current ={x}\n  baseline={y}", file=sys.stderr)
                break
        return 1
    print(f"[golden] OFF parity OK: {len(rows)} rows identical to baseline {a.base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
