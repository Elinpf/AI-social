#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T226 · inert registry 核对器（可执行、确定性、无第三方依赖）。

回答一个问题：**一个"已登记"的东西到底有没有『活』**——
「登记了」≠「生效了」：在文件里，"存在"与"生效"长得一样。本脚本用**代码/配置扫描**
把每条登记对象自动判为『已接线 / 未接线』，**表由它校验，不靠人维护**。

判定信号（全部来自 `code/` 实扫）：
  - `registered`：该事件名是否出现在 `engine/events.py::EVENT_TYPES`（仅 event 类）；
  - `folds`     ：该名是否出现在 `engine/replay.py`（折叠器登记）；
  - `produced`  ：该名是否出现在**生产文件**（排除 tests/scripts/frontend/__pycache__）。

状态：
  - event：`已接线` = registered ∧ folds ∧ produced；`未接线(产事件未注册)` = produced ∧ ¬registered；
           `未接线(仅声明)` = ¬produced。
  - judgment_dim/snapshot/hook：`已接线` = 生产文件里有**声明文件之外**的使用；否则 `未接线(仅声明)`。

退出码：0 = 所有条目与 `expected_status` 一致；非 0 = 有偏差（棘轮：登记表与代码不一致即失败）。

用法：
    python3 tools/check_inert_registry.py            # 打印表 + 退出码
    python3 tools/check_inert_registry.py --json     # 机器可读
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
REGISTRY = BASE / "inert_registry.json"

#: 「生产侧」= 能真正产生/发射的一方；obs/freeze/frontend 只是**消费/白名单**，不算接线。
PRODUCER_SCOPE = ("code/life", "code/engine", "code/orchestration")


def _load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def _py_files(code_dir: Path, exclude_parts: set[str]):
    for p in sorted(code_dir.rglob("*.py")):
        parts = set(p.parts)
        if parts & exclude_parts:
            continue
        yield p


def _in_event_types(name: str, events_py: Path) -> bool:
    if not events_py.exists():
        return False
    text = events_py.read_text(encoding="utf-8")
    m = re.search(r"EVENT_TYPES\s*=\s*\{(.*?)\}", text, re.S)
    block = m.group(1) if m else text
    return re.search(rf'["\']{re.escape(name)}["\']', block) is not None


def _has_fold(name: str, replay_py: Path) -> bool:
    if not replay_py.exists():
        return False
    return name in replay_py.read_text(encoding="utf-8")


def classify(entry: dict, code_dir: Path, exclude_parts: set[str]) -> dict:
    name = entry["name"]
    kind = entry.get("kind", "event")
    declared = set(entry.get("declared_in", []))

    hits: list[str] = []
    for f in _py_files(code_dir, exclude_parts):
        rel = f.relative_to(ROOT).as_posix()
        try:
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if name in line:
                    hits.append(f"{rel}:{i}")
                    break
        except Exception:
            continue

    produced = bool(hits)
    hits_producer = [h for h in hits if any(h.startswith(s) for s in PRODUCER_SCOPE)]
    # 生产侧、且声明文件之外的使用 → 才算"接线"（judgment_dim/snapshot 用）
    used_beyond_decl = [h for h in hits_producer if not any(h.startswith(d) for d in declared)]

    events_py = code_dir / "engine" / "events.py"
    replay_py = code_dir / "engine" / "replay.py"
    registered = _in_event_types(name, events_py) if kind == "event" else None
    folds = _has_fold(name, replay_py) if kind == "event" else None

    if kind == "event":
        produced_ev = bool(hits_producer)
        if registered and folds and produced_ev:
            status = "已接线"
        elif produced_ev and not registered:
            status = "未接线(产事件未注册)"
        elif not produced_ev:
            status = "未接线(仅声明)"
        else:
            status = "待核(已注册未产/未折叠)"
    else:
        status = "已接线" if used_beyond_decl else "未接线(仅声明)"

    verify = {
        "event": (f"grep -n '{name}' code/engine/events.py code/engine/replay.py; "
                  f"grep -rn '{name}' code/ --include=*.py | grep -vE 'tests/|scripts/|__pycache__'"),
        "judgment_dim": (f"grep -rn '{name}' code/life code/engine code/orchestration --include=*.py "
                         f"| grep -vE 'tests/|scripts/'"),
        "snapshot": (f"grep -rn '{name}' code/ --include=*.py | grep -vE 'tests/|scripts/|__pycache__'"),
    }.get(kind, f"grep -rn '{name}' code/ --include=*.py")

    alive = status.startswith("已接线")
    return {
        "name": name, "kind": kind, "status": status, "alive": alive,
        "registered": registered, "folds": folds, "produced": bool(hits_producer),
        "hits": hits_producer[:5] or hits[:5], "hits_all": hits[:5], "declared_in": sorted(declared),
        "expected_status": entry.get("expected_status"),
        "expected_ok": _expected_ok(entry.get("expected_status"), alive),
        "owner": entry.get("owner"), "due_condition": entry.get("due_condition"),
        "verify_cmd": verify,
    }


def _expected_ok(expected: str | None, alive: bool) -> bool | None:
    if expected is None:
        return None
    exp_alive = expected.strip().startswith("已接线")
    return exp_alive == alive


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    reg = _load_registry()
    code_dir = ROOT / reg.get("scan_root", "code")
    exclude = set(reg.get("production_exclude_parts", ["tests", "scripts", "__pycache__"]))

    rows = [classify(e, code_dir, exclude) for e in reg.get("entries", [])]
    mismatches = [r for r in rows if r["expected_ok"] is False]

    if args.json:
        print(json.dumps({"entries": rows, "mismatches": [r["name"] for r in mismatches]},
                         ensure_ascii=False, indent=2))
    else:
        print("=" * 78)
        print("T226 · inert registry（登记 != 生效；状态由代码扫描判定）")
        print("=" * 78)
        for r in rows:
            print(f"- {r['name']:<22} [{r['kind']:<13}] {r['status']}")
            print(f"    登记于: {', '.join(r['declared_in']) or '-'}")
            print(f"    核证据: registered={r['registered']} folds={r['folds']} produced={r['produced']}"
                  f"  hits={r['hits'] or '-'}")
            print(f"    验证:   {r['verify_cmd']}")
            if r["expected_status"]:
                print(f"    期望:   {r['expected_status']} -> {'OK' if r['expected_ok'] else 'MISMATCH'}")
        print("-" * 78)
        print(f"共 {len(rows)} 条；与 expected_status 不一致：{len(mismatches)}"
              f"{'  -> ' + ', '.join(r['name'] for r in mismatches) if mismatches else ''}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
