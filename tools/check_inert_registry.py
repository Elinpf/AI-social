#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T226 · inert registry 核对器（v2：手工棘轮条目 + 自动枚举事件/开关）。

回答一个问题：**一个"已登记"的东西到底有没有『活』**（登记 != 生效）。

⚠️ 本工具是**棘轮**，不是"一次性的表"：
  - **未接线必须显式声明**（写进 `tools/inert_registry.json` 的 `expected_status`）；
  - **接线之后必须同步更新 `expected_status`**（把"未接线"改成"已接线"）。
  - 它造成的"红"**不是 bug**，而是"有人改了接线状态但没同步声明"（棘轮本义）。

⚠️ 盲区（诚实标注）：静态扫描的"已接线"**只保证有生产侧调用点，不保证运行时真产生**。
   重大条目请叠加一次**实跑日志核对**：`grep '"type": "XXX"' <LOG>`（静态 + 运行双证据）。

三段：
  A. 手工条目（`inert_registry.json`）—— 含 `expected_status`（棘轮，参与退出码）。
  B. 自动枚举：`engine/events.py::EVENT_TYPES` 的全部事件 —— 逐条判 `已接线/未接线(...)`（仅报告）。
  C. 自动枚举：`code/config/policy.json` 的全部 `*.enabled` 开关 —— 生产侧是否读取（近似，标【未验证】）。

用法：
    python3 tools/check_inert_registry.py            # 三段表 + 退出码
    python3 tools/check_inert_registry.py --json     # 机器可读
    python3 tools/check_inert_registry.py --no-auto  # 只看手工棘轮条目
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


# ------------------------------------------------------------------ 基础扫描
def _load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def _py_files(code_dir: Path, exclude_parts: set[str]):
    for p in sorted(code_dir.rglob("*.py")):
        if set(p.parts) & exclude_parts:
            continue
        yield p


def _hits(name: str, code_dir: Path, exclude_parts: set[str]) -> list[str]:
    out: list[str] = []
    for f in _py_files(code_dir, exclude_parts):
        rel = f.relative_to(ROOT).as_posix()
        try:
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if name in line:
                    out.append(f"{rel}:{i}")
                    break
        except Exception:
            continue
    return out


def _event_types(events_py: Path) -> list[str]:
    if not events_py.exists():
        return []
    text = events_py.read_text(encoding="utf-8")
    m = re.search(r"EVENT_TYPES\s*=\s*\{(.*?)\}", text, re.S)
    block = m.group(1) if m else ""
    return sorted(set(re.findall(r'"([A-Z][A-Z0-9_]+)"', block)))


def _has_fold(name: str, replay_py: Path) -> bool:
    return replay_py.exists() and name in replay_py.read_text(encoding="utf-8")


# ------------------------------------------------------------------ A. 手工条目（棘轮）
def classify(entry: dict, code_dir: Path, exclude_parts: set[str]) -> dict:
    name = entry["name"]
    kind = entry.get("kind", "event")
    declared = set(entry.get("declared_in", []))
    hits = _hits(name, code_dir, exclude_parts)
    hits_prod = [h for h in hits if any(h.startswith(s) for s in PRODUCER_SCOPE)]
    used_beyond_decl = [h for h in hits_prod if not any(h.startswith(d) for d in declared)]
    events_py, replay_py = code_dir / "engine" / "events.py", code_dir / "engine" / "replay.py"
    registered = _in_event_types(name, events_py) if kind == "event" else None
    folds = _has_fold(name, replay_py) if kind == "event" else None
    if kind == "event":
        if registered and folds and hits_prod:
            status = "已接线"
        elif hits_prod and not registered:
            status = "未接线(产事件未注册)"
        elif not hits_prod:
            status = "未接线(仅声明)"
        else:
            status = "待核(已注册未产/未折叠)"
    else:
        status = "已接线" if used_beyond_decl else "未接线(仅声明)"
    alive = status.startswith("已接线")
    return {
        "name": name, "kind": kind, "status": status, "alive": alive,
        "registered": registered, "folds": folds, "produced": bool(hits_prod),
        "hits": (hits_prod or hits)[:5], "declared_in": sorted(declared),
        "expected_status": entry.get("expected_status"),
        "expected_ok": _expected_ok(entry.get("expected_status"), alive),
        "owner": entry.get("owner"), "due_condition": entry.get("due_condition"),
    }


def _in_event_types(name: str, events_py: Path) -> bool:
    return name in _event_types(events_py)


def _expected_ok(expected: str | None, alive: bool) -> bool | None:
    if expected is None:
        return None
    return expected.strip().startswith("已接线") == alive


# ------------------------------------------------------------------ B. 自动枚举事件
def _is_registry_file(hit: str) -> bool:
    """登记/折叠两个文件本身**不算发射点**（否则"登记"会被当成"发射"——正是本工具要防的陷阱）。"""
    return hit.startswith("code/engine/events.py:") or hit.startswith("code/engine/replay.py:")


def auto_events(code_dir: Path, exclude_parts: set[str]) -> list[dict]:
    """对 `EVENT_TYPES` 全部事件判「有没有生产侧**发射点**」（排除 events.py/replay.py 的登记）。"""
    rows = []
    for name in _event_types(code_dir / "engine" / "events.py"):
        hits = _hits(name, code_dir, exclude_parts)
        prod = [h for h in hits if any(h.startswith(s) for s in PRODUCER_SCOPE)]
        emit = [h for h in prod if not _is_registry_file(h)]
        folds = _has_fold(name, code_dir / "engine" / "replay.py")
        if emit:
            st = "已接线(有发射点)"
        else:
            st = "未接线(已注册·无生产侧发射点)"
        rows.append({"name": name, "status": st, "produced": bool(emit), "folds": folds,
                     "hits": emit[:3]})
    return rows


# ------------------------------------------------------------------ C. 自动枚举开关
def auto_switches(policy_path: Path, code_dir: Path, exclude_parts: set[str]) -> list[dict]:
    if not policy_path.exists():
        return []
    data = json.loads(policy_path.read_text(encoding="utf-8"))
    paths: list[tuple[str, str]] = []

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "enabled":
                    paths.append((f"{path}.enabled", path.split(".")[-1]))
                walk(v, f"{path}.{k}")
    walk(data, "policy")

    prod_texts = {f: f.read_text(encoding="utf-8") for f in _py_files(code_dir, exclude_parts)
                  if any(f.relative_to(ROOT).as_posix().startswith(s) for s in PRODUCER_SCOPE)}
    rows = []
    for path, section in sorted(paths):
        wired = any((f'"{section}"' in t and "enabled" in t) for t in prod_texts.values())
        rows.append({
            "name": path, "section": section,
            "status": ("已接线(疑似)" if wired else "未接线(仅配置)"),
            "note": "生产侧是否读取为近似判定【未验证】；请叠加实跑开/关核对",
        })
    return rows


# ------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-auto", action="store_true")
    args = ap.parse_args()

    reg = _load_registry()
    code_dir = ROOT / reg.get("scan_root", "code")
    exclude = set(reg.get("production_exclude_parts", ["tests", "scripts", "__pycache__"]))

    manual = [classify(e, code_dir, exclude) for e in reg.get("entries", [])]
    mism = [r for r in manual if r["expected_ok"] is False]
    ev = [] if args.no_auto else auto_events(code_dir, exclude)
    sw = [] if args.no_auto else auto_switches(code_dir / "config" / "policy.json", code_dir, exclude)

    if args.json:
        print(json.dumps({
            "manual": manual, "mismatches": [r["name"] for r in mism],
            "auto_events": ev, "auto_switches": sw,
        }, ensure_ascii=False, indent=2))
        return 1 if mism else 0

    W = 78
    print("=" * W)
    print("T226 · inert registry（登记 != 生效）—— 棘轮：未接线显式声明，接线后须更新 expected_status")
    print("=" * W)
    print("[A] 手工条目（含 expected_status，参与退出码）")
    for r in manual:
        mark = "OK" if r["expected_ok"] else "MISMATCH"
        print(f"  - {r['name']:<22} [{r['kind']:<13}] {r['status']:<20} 期望 {r['expected_status']} -> {mark}")
        print(f"      hits={r['hits'] or '-'}")
    print(f"  小计 {len(manual)} 条；与期望不一致 {len(mism)}"
          f"{' -> ' + ', '.join(x['name'] for x in mism) if mism else ''}")

    if ev:
        un = [r for r in ev if not r["status"].startswith("已接线")]
        print("-" * W)
        print(f"[B] 自动枚举 · EVENT_TYPES 事件：共 {len(ev)}，未接线 {len(un)}"
              f"（其余 已接线 = 有生产侧调用点且已折叠；仍须实跑确认【未验证】）")
        for r in un:
            print(f"  - {r['name']:<26} {r['status']}  hits={r['hits'] or '-'}")

    if sw:
        print("-" * W)
        print(f"[C] 自动枚举 · config 开关（policy.*.enabled）：共 {len(sw)}")
        for r in sw:
            print(f"  - {r['name']:<28} {r['status']}")

    print("-" * W)
    print("盲区：静态扫描不保证运行时真产生 -> 重大条目叠加 `grep '\"type\":\"XXX\"' <LOG>`。")
    return 1 if mism else 0


if __name__ == "__main__":
    sys.exit(main())
