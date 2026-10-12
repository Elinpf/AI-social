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
THREE_STATES = ("wired_observed", "wired_not_observed", "missing_wiring")


def three_state(alive_static: bool, observed) -> str:
    """三态判据（Leader 2026-10-12 裁决，T244）：

    - `wired_observed`：**真 run 日志里至少观察到一次**（须附 observed_evidence: 命令+sha+N/rounds）。
    - `wired_not_observed`：代码路径存在、但真 run 未观察到（须说明原因：default off / 条件未触发 / 依赖未接通）。
    - `missing_wiring`：无代码路径。

    "有代码路径"≠"参加了反应" —— 故静态命中只到 `wired_not_observed`，要 `wired_observed` 必须 `observed=True`。
    """
    if not alive_static:
        return "missing_wiring"
    return "wired_observed" if observed is True else "wired_not_observed"


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
    elif kind == "pointer":
        # 「指针」类：事件可能已发射，但**指向的正文/body 是否有写入方**才是关键。
        # 用 writer_probe 正则（在 code/ 排除 tests/scripts）判定"正文写入方是否存在"。
        probes = entry.get("writer_probe", [])
        code_texts = []
        for f in _py_files(code_dir, exclude_parts):
            try:
                code_texts.append(f.read_text(encoding="utf-8"))
            except Exception:
                continue
        found = any(re.search(p, t) for p in probes for t in code_texts)
        status = "已接线(有正文写入方)" if found else "未接线(仅声明)"
    elif kind == "field":
        # 「字段到达」类（Leader 2026-10-12）：**登记了字段，但它是否真的到达事件 payload？**
        # 判据：存在**装配点**（含 emit 调用 `_emit(`/`spec(`/`EventSpec(`）同时出现 `owner_event` 与字段名。
        # 否则 = 被装配白名单静默丢弃 → 登记落空。
        owner = entry.get("owner_event", "")
        leaf = name.split(".")[-1]
        arrived = False
        for f in _py_files(code_dir, exclude_parts):
            rel = f.relative_to(ROOT).as_posix()
            if not any(rel.startswith(s) for s in PRODUCER_SCOPE):
                continue
            try:
                t = f.read_text(encoding="utf-8")
            except Exception:
                continue
            is_assembler = ("_emit(" in t) or ("spec(" in t) or ("EventSpec(" in t)
            if is_assembler and owner and (owner in t) and (leaf in t):
                arrived = True
                break
        status = "已到达事件" if arrived else "未到达(登记未达事件·被装配丢弃?)"
    else:
        status = "已接线" if used_beyond_decl else "未接线(仅声明)"
    alive = status.startswith("已接线") or status.startswith("已到达")
    observed = entry.get("observed")
    three = three_state(alive, observed)
    ev = entry.get("observed_evidence")
    warn = []
    if observed is True and not ev:
        warn.append("wired_observed 缺 observed_evidence(命令+sha+N/rounds)")
    return {
        "name": name, "kind": kind, "status": three, "static_status": status, "alive": alive,
        "observed": observed, "observed_evidence": ev,
        "dependency_missing": bool(entry.get("dependency_missing")),
        "block_reason": entry.get("block_reason"),
        "disposition": entry.get("disposition"),
        "disposition_note": entry.get("disposition_note"),
        "registered": registered, "folds": folds, "produced": bool(hits_prod),
        "hits": (hits_prod or hits)[:5], "declared_in": sorted(declared),
        "expected_status": entry.get("expected_status"),
        "expected_ok": _expected_ok(entry.get("expected_status"), three, alive),
        "owner": entry.get("owner"), "due_condition": entry.get("due_condition"),
        "warn": warn,
    }


def _in_event_types(name: str, events_py: Path) -> bool:
    return name in _event_types(events_py)


def _expected_ok(expected: str | None, three: str, alive: bool) -> bool | None:
    if expected is None:
        return None
    e = expected.strip()
    if e in THREE_STATES:
        return e == three
    # 兼容旧口径
    exp_alive = e.startswith("已接线") or e.startswith("已到达")
    return exp_alive == alive


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


# ------------------------------------------------------------------ D. 前端资产/常量（定义↔引用）
# 「睡着的资产」：一个资产/常量**定义了却零引用**（死帧 / 未接线素材）。案例：grassLight。
# 与 A/B/C 同构：同入口/同退出码/同 JSON（只新增 `auto_assets` 键）。
#
# ⚠️ 两态纪律（Leader 采纳入锚定书）：JS 有**动态访问**（`TILES[k]`/`sprites[id]`/数字索引）
#   → "名字搜不到" ≠ "没被引用"。故输出三态：
#     referenced / zero_ref / dynamic_ref_unknown。**zero_ref 才可报警；后者只报"未知"。**
# 只做**数据级**（映射表的键 vs 引用点）；**局部未用变量交 ESLint `no-unused-vars`**，本器不判。
D_STATES = ("referenced", "zero_ref", "dynamic_ref_unknown")
ASSET_MODULES = ("src/sprites.js",)   # 顶层资产映射所在（可扩展）
# 值(id)引用：仅当 id ≥ 100（tile id 量级）才算，避免 0/1/2 这类结构下标刷屏。


def _asset_defs(frontend_dir: Path) -> list[tuple[str, list, str, str]]:
    """枚举顶层映射表键（值形如 `[271, 226, ...]`）→ [(key, [ids], 定义文件rel, 所属映射名)]。"""
    out = []
    for rel in ASSET_MODULES:
        p = frontend_dir / rel
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        for m in re.finditer(r"const\s+([A-Za-z_]\w*)\s*=\s*\{(.*?)\n\s*\};", text, re.S):
            map_name = m.group(1)
            for km in re.finditer(r"([A-Za-z_]\w*)\s*:\s*\[([0-9,\s]+)\]", m.group(2)):
                ids = [int(x) for x in re.findall(r"\d+", km.group(2))]
                out.append((km.group(1), ids, rel, map_name))
    return out


def _refs_asset(sym: str, ids: list, frontend_dir: Path, define_rel: str, map_name: str):
    """返回 (refs_name, refs_value, dynamic_scope, has_small_ids)。
    名字=`.sym`/`'sym'`；值=id(≥100)字面量（定义文件除外）；has_small_ids = 存在被过滤的 id(<100)
    → 届时无名字命中也不能确证零引用（值命中是【近似】，靠名字兜底）。"""
    rn: list[str] = []
    rv: list[str] = []
    dyn = False
    has_small_ids = any(i < 100 for i in ids)   # <100 的 id 不作值搜索 → 可能漏，不能据此报 zero_ref
    name_re = re.compile(r"\." + re.escape(sym) + r"\b|[\"']" + re.escape(sym) + r"[\"']")
    dyn_re = re.compile(r"\b" + re.escape(map_name) + r"\s*\[\s*[^\"'\]]")
    # 值(id)命中需落在"瓦片消费"上下文，避免 id 在注释/坐标里被误当引用。
    tile_ctx = re.compile(r"pick\(|slice\(|texture|Texture|Rectangle|frame")
    for f in sorted(frontend_dir.rglob("*.js")):
        rel = f.relative_to(frontend_dir).as_posix()
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for i, raw in enumerate(lines, 1):
            code = raw.split("//", 1)[0]           # 去掉行尾注释：注释不是"引用"
            if not code.strip():
                continue
            if name_re.search(code):
                rn.append(f"{rel}:{i}")
            if rel != define_rel and tile_ctx.search(code):
                for idv in ids:
                    if idv >= 100 and re.search(r"\b" + str(idv) + r"\b", code):
                        rv.append(f"{rel}:{i}:{idv}")
            if dyn_re.search(code):
                dyn = True
    return rn, rv, dyn, has_small_ids


def d_state(name: str, value_ids: list, refs_name: list, refs_value: list,
            dynamic_scope: bool, has_small_ids: bool = False) -> str:
    """资产/常量三态（与事件三态同构）：
    - referenced: 名字命中 **或** 值(id)命中；
    - zero_ref: 名字与值均零命中，**且**无动态索引、**且**无被过滤的小 id（可确证零引用）；
    - dynamic_ref_unknown: 零命中但有动态索引 **或被过滤的小 id**（值命中为近似）→ **未知，绝不写 zero_ref**。"""
    if refs_name or refs_value:
        return "referenced"
    return "dynamic_ref_unknown" if (dynamic_scope or has_small_ids) else "zero_ref"


def _load_asset_ratchet(frontend_dir: Path) -> dict:
    """棘轮：`code/frontend/tools/inert_assets.json` 的 `entries`（显式声明 expected_status）。"""
    p = frontend_dir / "tools" / "inert_assets.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {e["name"]: e for e in data.get("entries", []) if e.get("name")}


def auto_assets(frontend_dir: Path, include_auto: bool = True) -> list[dict]:
    ratchet = _load_asset_ratchet(frontend_dir)
    seen: set[str] = set()
    rows: list[dict] = []
    for name, ids, rel, map_name in (_asset_defs(frontend_dir) if include_auto else []):
        seen.add(name)
        rn, rv, dyn, small = _refs_asset(name, ids, frontend_dir, rel, map_name)
        st = d_state(name, ids, rn, rv, dyn, small)
        e = ratchet.get(name, {})
        exp = e.get("expected_status")
        rows.append({
            "name": name, "kind": "asset", "status": st,
            "defined_in": "code/frontend/" + rel, "value_ids": ids,
            "refs_name": rn[:3], "refs_value": rv[:3], "dynamic_scope": dyn, "has_small_ids": small,
            "hits": (rn or rv)[:3],
            "expected_status": exp, "expected_ok": (exp == st) if exp else None,
            "purpose": e.get("purpose"), "owner": e.get("owner"),
        })
    for name, e in ratchet.items():   # 棘轮里但未被自动枚举：报出来（可能名字/路径变了）
        if name in seen:
            continue
        exp = e.get("expected_status")
        rows.append({
            "name": name, "kind": "asset", "status": "-", "defined_in": e.get("defined_in"),
            "value_ids": [], "refs_name": [], "refs_value": [], "dynamic_scope": None, "has_small_ids": None, "hits": [],
            "expected_status": exp, "expected_ok": None, "purpose": e.get("purpose"), "owner": e.get("owner"),
            "note": "棘轮条目未被自动枚举（查名字/路径；--no-auto 下正常）",
        })
    return rows


def _self_test() -> int:
    """反向验证（写死）：用 grassLight 的三种接线状态造夹具，断言三态判据**能报红**。
    一个只会报"绿"的核对器没有价值；能对"未接线"报 zero_ref 的才算判据。"""
    import tempfile
    ok = True
    sp = "const TILES = {\n  grassLight: [745, 1015],\n};\n"
    sp_small = "const TILES = {\n  tiny: [3, 7],\n};\n"
    cases = [
        ("未接线 → zero_ref", sp, "const x = 1;\n", "zero_ref", "grassLight"),
        ("已接线(town.js 具名) → referenced", sp, "const g = W.TILES.grassLight;\n", "referenced", "grassLight"),
        ("动态键访问 → dynamic_ref_unknown", sp, "const g = TILES[k];\n", "dynamic_ref_unknown", "grassLight"),
        ("动态键访问(普通下标不算)", sp, "const r = road[ty][tx];\n", "zero_ref", "grassLight"),
        ("仅小 id(<100) 无具名 → dynamic_ref_unknown(防假红)", sp_small, "const x = 1;\n", "dynamic_ref_unknown", "tiny"),
    ]
    for label, s, t, expect, sym in cases:
        d = Path(tempfile.mkdtemp())
        (d / "src").mkdir()
        (d / "tools").mkdir()
        (d / "src" / "sprites.js").write_text(s, encoding="utf-8")
        (d / "src" / "town.js").write_text(t, encoding="utf-8")
        got = next((r["status"] for r in auto_assets(d) if r["name"] == sym), None)
        mark = "OK" if got == expect else "FAIL"
        ok = ok and got == expect
        print(f"  [{mark}] {label}: got={got} expect={expect}")

    # 真实资产复现（对齐验收原文）：用真 sprites.js；town.js 去掉/保留 grassLight 引用
    real = ROOT / "code" / "frontend" / "src"
    if (real / "sprites.js").exists() and (real / "town.js").exists():
        sp_real = (real / "sprites.js").read_text(encoding="utf-8")
        town_real = (real / "town.js").read_text(encoding="utf-8")
        town_nowire = "\n".join(ln for ln in town_real.splitlines() if "grassLight" not in ln)
        for label, town_src, expect in [
            ("真实 assets · town.js 去掉 grassLight 引用 → zero_ref", town_nowire, "zero_ref"),
            ("真实 assets · town.js 原样(已接线) → referenced", town_real, "referenced"),
        ]:
            d = Path(tempfile.mkdtemp())
            (d / "src").mkdir()
            (d / "tools").mkdir()
            (d / "src" / "sprites.js").write_text(sp_real, encoding="utf-8")
            (d / "src" / "town.js").write_text(town_src, encoding="utf-8")
            got = next((r["status"] for r in auto_assets(d) if r["name"] == "grassLight"), None)
            mark = "OK" if got == expect else "FAIL"
            ok = ok and got == expect
            print(f"  [{mark}] {label}: got={got} expect={expect}")
    return 0 if ok else 1


# ------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-auto", action="store_true")
    ap.add_argument("--self-test", action="store_true", help="D 段反向验证（夹具断言三态判据）")
    args = ap.parse_args()

    if args.self_test:
        print("D 段反向验证（grassLight 三态）：")
        return _self_test()

    reg = _load_registry()
    code_dir = ROOT / reg.get("scan_root", "code")
    exclude = set(reg.get("production_exclude_parts", ["tests", "scripts", "__pycache__"]))

    manual = [classify(e, code_dir, exclude) for e in reg.get("entries", [])]
    mism = [r for r in manual if r["expected_ok"] is False]
    ev = [] if args.no_auto else auto_events(code_dir, exclude)
    sw = [] if args.no_auto else auto_switches(code_dir / "config" / "policy.json", code_dir, exclude)
    ass = auto_assets(ROOT / "code" / "frontend", include_auto=not args.no_auto)
    asset_mism = [r for r in ass if r.get("expected_ok") is False]
    # 对自动事件附「三分类」（Leader 裁决：reserved / missing_wiring / deprecated）
    cls_map = reg.get("auto_event_classification", {})
    for r in ev:
        if r["name"] in cls_map:
            r["class"] = cls_map[r["name"]].get("class")
            r["class_note"] = cls_map[r["name"]].get("note")

    if args.json:
        print(json.dumps({
            "manual": manual, "mismatches": [r["name"] for r in mism],
            "auto_events": ev, "auto_switches": sw, "auto_assets": ass,
        }, ensure_ascii=False, indent=2))
        return 1 if (mism or asset_mism) else 0

    W = 78
    print("=" * W)
    print("T226 · inert registry（登记 != 生效）—— 棘轮：未接线显式声明，接线后须更新 expected_status")
    print("=" * W)
    print("[A] 手工条目（三态：wired_observed / wired_not_observed / missing_wiring）")
    for r in manual:
        mark = "OK" if r["expected_ok"] else "MISMATCH"
        print(f"  - {r['name']:<22} [{r['kind']:<13}] {r['status']:<20} 期望 {r['expected_status']} -> {mark}")
        if r.get("observed"):
            print(f"      observed_evidence={r.get('observed_evidence')}")
        if r.get("dependency_missing"):
            print(f"      ⚠ 依赖未接通: {r.get('block_reason')}")
        elif r.get("block_reason") and r["status"] == "wired_not_observed":
            print(f"      未观测原因: {r.get('block_reason')}")
        if r.get("disposition"):
            print(f"      定性[{r['disposition']}] owner={r.get('owner')}: {r.get('disposition_note')}")
        for w in r.get("warn", []):
            print(f"      ⚠ {w}")
        print(f"      hits={r['hits'] or '-'}  (static: {r['static_status']})")
    dist = {s: sum(1 for r in manual if r["status"] == s) for s in THREE_STATES}
    print(f"  小计 {len(manual)} 条；三态分布 wired_observed={dist['wired_observed']}"
          f" wired_not_observed={dist['wired_not_observed']} missing_wiring={dist['missing_wiring']}"
          f"；与期望不一致 {len(mism)}"
          f"{' -> ' + ', '.join(x['name'] for x in mism) if mism else ''}")

    if ev:
        un = [r for r in ev if not r["status"].startswith("已接线")]
        n_mis = sum(1 for r in un if r.get("class") == "missing_wiring")
        n_res = sum(1 for r in un if r.get("class") == "reserved")
        n_dep = sum(1 for r in un if r.get("class") == "deprecated")
        print("-" * W)
        print(f"[B] 自动枚举 · EVENT_TYPES 事件：共 {len(ev)}，无发射点 {len(un)}"
              f"（有发射点=静态命中，**≠**真 run 观测到；观测证据见 [A]/实跑日志）")
        print(f"    未接线三分类：missing_wiring={n_mis}  reserved={n_res}  deprecated={n_dep}"
              f"  未分类={len(un) - n_mis - n_res - n_dep}（不要求清零，要求分类）")
        for r in un:
            tag = f"[{r.get('class', 'unclassified')}]"
            print(f"  - {r['name']:<26} {r['status']} {tag}")
            if r.get("class_note"):
                print(f"      {r['class_note']}")

    if sw:
        print("-" * W)
        print(f"[C] 自动枚举 · config 开关（policy.*.enabled）：共 {len(sw)}")
        for r in sw:
            print(f"  - {r['name']:<28} {r['status']}")

    if ass:
        n_zero = sum(1 for r in ass if r["status"] == "zero_ref")
        n_unk = sum(1 for r in ass if r["status"] == "dynamic_ref_unknown")
        n_ref = sum(1 for r in ass if r["status"] == "referenced")
        print("-" * W)
        print(f"[D] 自动枚举 · 前端资产/常量（定义↔引用）：共 {len(ass)}"
              f"  referenced={n_ref} zero_ref={n_zero} dynamic_ref_unknown={n_unk}")
        print("    三态纪律：zero_ref 才可报警；dynamic_ref_unknown **只报未知**（动态键访问，不得写成 zero_ref）")
        for r in ass:
            exp = r.get("expected_status")
            mark = "" if r.get("expected_ok") is None else (" OK" if r["expected_ok"] else " MISMATCH")
            print(f"  - {r['name']:<22} {r['status']:<20} ids={r['value_ids']} "
                  f"dyn={r['dynamic_scope']} small_ids={r.get('has_small_ids')} hits={r['hits'] or '-'}"
                  + (f" 期望 {exp}->{mark}" if exp else ""))
            if r.get("purpose"):
                print(f"      用途: {r['purpose']}")
            if r.get("note"):
                print(f"      ⚠ {r['note']}")
        if asset_mism:
            print(f"  棘轮不一致 {len(asset_mism)}：{', '.join(r['name'] for r in asset_mism)}"
                  f"（接线状态变了但 expected_status 未同步）")

    print("-" * W)
    print("盲区：静态扫描不保证运行时真产生 -> 重大条目叠加 `grep '\"type\":\"XXX\"' <LOG>`。")
    return 1 if (mism or asset_mism) else 0


if __name__ == "__main__":
    sys.exit(main())
