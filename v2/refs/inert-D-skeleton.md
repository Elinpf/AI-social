# inert registry · D 段骨架（前端资产/常量「定义↔引用」核对）—— 供 T267 同构实现

> 作者：仿真引擎与统计架构师（sim-engine-stats-architect）｜ 用途：`frontend-dev` 实现 T267 的 D 段模板
> 同构对象：`tools/check_inert_registry.py` 的 **A（手工棘轮）/B（EVENT_TYPES）/C（policy 开关）** 三段
> 目标：**D 段与 B/C 同输出、同退出码、同 JSON 结构**，避免"两份门禁"

---

## 0. 与 B/C 的对齐（必须一致）

| 维度 | B/C 现状 | D 段要求 |
|---|---|---|
| 运行入口 | `python3 tools/check_inert_registry.py [--json] [--no-auto]` | 同 |
| 退出码 | `1` 当**手工棘轮条目** `expected_ok is False`；否则 `0` | 同（D 的 `expected_status` 不匹配也置 1） |
| JSON | `{"manual":[...], "mismatches":[...], "auto_events":[...], "auto_switches":[...]}` | **新增一键** `"auto_assets":[...]`（不改既有键） |
| 三态理念 | `wired_observed / wired_not_observed / missing_wiring`（事件） | 资产映射为 **`referenced / zero_ref / dynamic_ref_unknown`**（见 §2） |
| 棘轮 | `expected_status` 显式声明；改了须同步 | 同（资产条目亦须 `expected_status`） |

---

## 1. 数据源与作用域

- **手工棘轮条目**：沿用已有 `code/frontend/tools/inert_assets.json`（T258e）——每条至少 `{name, expected_status, declared_in}`。
- **自动枚举**：`code/frontend/**/sprites.js`（及其他资产映射模块）的**顶层具名定义 / 映射表键**。
- **引用面**：`code/frontend/**/*.js`（渲染/主循环），**排除 `sprites.js` 自身定义行**（定义≠引用，同 B 段排除 `events.py/replay.py`）。

---

## 2. 三态判据（**D 段专用，与事件三态同构**）

```python
D_STATES = ("referenced", "zero_ref", "dynamic_ref_unknown")

def d_state(name: str, value_ids: list, refs_name: list, refs_value: list,
            dynamic_scope: bool) -> str:
    """资产/常量的"活/睡"三态。

    - referenced          : 名字命中 **或** 其值(id)命中任一引用点。
    - zero_ref            : 名字与值均**零命中**，**且**作用域内**无动态索引**（可确证零引用）。
    - dynamic_ref_unknown : 名字/值零命中，但作用域内**存在动态索引/间接引用**
                            （如 `W.pick(glight, …)`、`TILES[k]`、数字/字符串拼接）
                            → **未知，绝不写成 zero_ref**。
    """
    if refs_name or refs_value:
        return "referenced"
    return "dynamic_ref_unknown" if dynamic_scope else "zero_ref"
```

> **核心纪律（Leader 采纳入 08）**：`zero_ref` 才可报警；`dynamic_ref_unknown` **只报"未知"**。
> **值引用**：`grassLight=[745,1015]` 的关键——须建 `符号 → 值(数字/字符串 id)` 映射，把**值也纳入引用搜索**（`W.pick(glight,…)` 用的是变量 `glight` 的值，不是 `grassLight` 名）。

---

## 3. 函数骨架（同构 B/C）

```python
# ---- 枚举：顶层定义 / 映射键  ----
def _asset_defs(frontend_dir: Path) -> list[tuple[str, list]]:
    """返回 [(symbol_name, value_ids)]；如 grassLight -> [745,1015]。
    解析 sprites.js 顶层 `const NAME = [...]` / `NAME: [...]` 等；值抽数字/字符串字面量。"""

def _symbol_value_map(frontend_dir: Path) -> dict[str, list]:
    """符号 -> 值(id) 映射（供值引用搜索）。"""

# ---- 引用搜索（排除定义处）----
def _refs(sym: str, ids: list, frontend_dir: Path) -> tuple[list, bool]:
    """返回 (命中行列表, 作用域内是否含动态索引)。

    - 命中 = 名字 `sym` 或任一 id 字面量出现在**非定义**的 frontend 代码里；
    - 动态索引探测：正则 `\\[[a-zA-Z_]`、`\\.pick\\(`、`eval`、`window\\[` 等（近似，标【近似】）。
    """

# ---- 单条判据（对应 B 的 classify）----
def classify_asset(entry: dict, frontend_dir: Path) -> dict:
    name = entry["name"]
    ids = _symbol_value_map(frontend_dir).get(name, entry.get("values", []))
    rn, dyn = _refs(name, ids, frontend_dir)
    status = d_state(name, ids, rn, rn, dyn)
    exp = entry.get("expected_status")
    return {
        "name": name, "kind": "asset", "status": status,
        "value_ids": ids, "hits": (rn or [])[:5],
        "expected_status": exp,
        "expected_ok": (exp == status) if exp else None,
        "owner": entry.get("owner"), "note": entry.get("note"),
    }

# ---- 自动枚举（对应 B 的 auto_events）----
def auto_assets(frontend_dir: Path) -> list[dict]:
    rows = []
    for name, ids in _asset_defs(frontend_dir):
        rn, dyn = _refs(name, ids, frontend_dir)
        st = d_state(name, ids, rn, rn, dyn)
        rows.append({"name": name, "status": st, "value_ids": ids,
                     "hits": (rn or [])[:3], "produced": bool(rn)})
    return rows
```

---

## 4. main 接线（同构；只加一段）

```python
    # ... 既有 A/B/C ...
    ass = [] if args.no_auto else auto_assets(ROOT / "code" / "frontend")
    if args.json:
        print(json.dumps({"manual": manual, "mismatches": [...],
                          "auto_events": ev, "auto_switches": sw,
                          "auto_assets": ass}, ensure_ascii=False, indent=2))
        return 1 if mism else 0
    # 文本段
    if ass:
        print("-" * W)
        print(f"[D] 自动枚举 · 前端资产/常量（定义↔引用）：共 {len(ass)}")
        for r in ass:
            print(f"  - {r['name']:<22} {r['status']:<20} ids={r['value_ids']} hits={r['hits'] or '-'}")
    return 1 if mism else 0
```

---

## 5. 硬要求（Leader 已定，写入验收）

1. **两态不得混淆**：`dynamic_ref_unknown` **绝不**写成 `zero_ref`。
2. **只做数据级**：局部未用变量交 ESLint `no-unused-vars`，本器不判。
3. **值引用**必须纳入（数字/字符串 id）。
4. **棘轮** `expected_status`：已知未引用显式声明；引用后同步（红了=状态没同步）。
5. **双证据**：静态 + 一次实跑/渲染核对。
6. **反向验证**：`grassLight`（`sprites.js:52`）——修复前 `zero_ref`，修复后（`town.js:425` `W.TILES.grassLight`）`referenced`。
7. **同输出/同退出码/同 JSON**（新增 `auto_assets` 键，不动既有键）。

---

*（D 段骨架完 —— 与 A/B/C 同构；B/C 实现仍在 `tools/check_inert_registry.py`，归 sim-engine-stats-architect。）*
