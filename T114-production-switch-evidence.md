# T114 · 生产层一等开关 `production.enabled` + 三态 fail-loud 协同（证据）

> 作者：econ-dev ｜ 2026-10-10 ｜ 交付：`engine/hooks/production.py`、`engine/hooks/__init__.py`、`config/policy.json`、`tests/test_production_switch.py`

## 0. 交付

- **一等开关** `policy.production.enabled`（+ runtime `config.production.enabled`，**默认 `true`、行为不变**），落 `policy.json`（含注释）。
- `apply_production` 读开关：`false` → 零生产事件 + 每回合一条 `DROPPED{reason:"production_disabled", flag:"production_disabled"}` 审计。
- `assert_production_available(config)` 三态协同（**防线不削弱**）：
  `economy.enabled=true 且 production.enabled=true 且 hook 未挂载` → **raise（fail-loud）**；`production.enabled=false` → 永不 raise；`economy.enabled=false` → 允许 no-op。读取顺序与 `econ._econ_enabled` 一致（runtime 覆盖优先）。

## 1. 三态验收（每条一断言，`tests/test_production_switch.py`）

| 态 | 断言 | 结果 |
|---|---|---|
| ① economy on + production on + 已挂载 | `build_world` 默认跑 24 回合 → `SYSTEM_ERROR=0` 且 `PRODUCE>0` | ✅ |
| ② production.enabled=false（显式关闭） | 跑 24 回合 → `PRODUCE==0`、`conservation==[]`、`M_min≥0`、存在 `flag=production_disabled` | ✅ |
| ③ economy on + production on + **未挂载**（monkeypatch `PRODUCTION_HOOK_AVAILABLE=False`） | `assert_production_available` **必须 raise RuntimeError**；production off / economy off / `{}` 不 raise | ✅ |

- `pytest -q` = **281 passed**（基线 277 + 新增 4）。
  **fail-loud 口径（可复现）**：`pytest -q tests/test_production_mounted.py` → **3 用例 / 4 条 assert，3 passed**（`def test_` ×3：mounted / fails_loud_when_missing / economy_enabled_produces_and_no_stall）；
  第三态另由 `tests/test_production_switch.py::test_state3_fail_loud_when_mounted_missing` 覆盖。**防线未被削弱**。

## 2. 开关 OFF 消融日志（**rule-based**，N=20×84, seed42；`production.enabled=false`）

> **provider/配置标注**：本行用 `build_world(seed=42,n=20)`，**rule-based（无真 LLM provider）**。
> 与 `PRODUCE` 的其他两数**不可直接互比**：T91=`321`（rule-based，production on）、T104=`314`（**真 LLM**，production on）、本行=`0`（rule-based，production off）。

| 指标 | 值 |
|---|---|
| `PRODUCE` | **0** ｜ `CONSUME` 0 |
| 商品双账本守恒 | ✅（平凡成立：0=0） |
| `M_min` / `M_final` | 0 / （全程不穿负，`M≥μ_floor`） |
| `SYSTEM_ERROR` / `ECONOMY_INVARIANT_VIOLATION` | 0 / 0 |
| 守恒 / replay | 货币守恒 ✅ ｜ replay 逐位一致 ✅ |
| `flag=production_disabled` | 每回合一条审计（可见） |

> 与 ON（默认）对照：ON 下 `PRODUCE=321`、商品双账本守恒 `294685=136216+158469+0+0`（T91 证据）。
> → **只改一个变量**（`production.enabled`）即可隔离生产层，供 v2 M3「消融证伪」使用。

## 3. 文档口径

- `policy.json` 的 `production` 块含注释（默认 true / off 语义 / flag / 指纹影响）。
- **08 事件 schema 侧**：`production.enabled` 属**配置口径**、非事件字段，建议在 `08` 配置/不变量节登记一行「生产层开关」——已请 Leader 转 sim-engine-stats-architect（与 milli-unit 同批，T108/T106 范畴）。
