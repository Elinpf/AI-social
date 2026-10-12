# T239 · 世界 AI 导演 v1（WD）实现说明 + 机制表落地清单

> 作者：kernel-dev ｜ 日期：2026-10-12 ｜ 依据：`v2/refs/world-director-design.md`(T210)、`v2/refs/world-event-mechanisms.md`(T216)、`08 §1.2 T`(T238)

## 模块（WD-Core / Mech / Control / Audit）
- **WD-Core**：`engine/world_director.py` —— 机制表读取、**判定树 R1–R6 真实现**（`validate_directive`）、**剂量曲线**（`DOSE_CURVES` 保守/中/激进，整数 bp）、**RNG 先定** `(seed,"world_director",round,idx)`、directive 草案（`plan_directives`）。
- **Mech**：`config/world_director.json` 机制表（每机制开关 + 剂量）＋ `kind` 取 T216 权威 14 枚举子集。
- **Control**：`engine/hooks/world_director.py::apply_world_director`（挂 `PHASE4_CHAIN` **最前**：情境先于经济结算）＋**消融**（总开关关→`[]`）＋**登记门控**（`"WORLD_DIRECTIVE" not in EVENT_TYPES` → 只产草案不 emit）。
- **Audit**：每次介入落 `WORLD_DIRECTIVE`/`WORLD_GROUP_EVENT`（`directed=true`，`actor="DIRECTOR"`，`GROUP_EVENT.directive_ref` 溯源）；违 R1–R6 → `WORLD_DIRECTIVE_REJECTED`。

## 三条保底（机器可校验）
- **(a) 显式事件**：有介入 ⇒ 有 `directed=true` 事件；`GROUP_EVENT.directive_ref ∈ {DIRECTIVE.directive_id}`。
- **(b) 可消融**：`world_director.enabled=false` ⇒ **0 事件**；每机制独立开关 + `dose_curve∈{conservative,moderate,aggressive}`（整数缩放）；**新 config 进 `FINGERPRINT_FILES`**（`world_director.json`）。
- **(c) 不改过去**：`effective_from_round ≥ issued_round`（违反→`rewrites_past` 拒绝）；只对未来下情境。

## 判定树 R1–R6（`validate_directive` 真实现，非文档）
| 编号 | 检查 | 拒绝 reason |
|---|---|---|
| R1/R2 | `scope.level` 合法；不含个体目标键 | `invalid_scope_level` / `targets_individual` |
| R3 | `directed=true` | `no_directed_marker` |
| R4 | `effective_from_round ≥ issued_round` | `rewrites_past` |
| R5 | params/dose 不含金额/死亡/胜负键 | `contains_hard_kernel_number` |
| R6 | 不含强制/指定结果键 | `targets_individual` |
| WD-D1 | `level=agents` 且规模<K | `warn`（**非拒绝**） |
| — | 机制存在 / 剂量档已知 | `invalid_mechanism` / `dose_curve_unknown` |

## 机制表落地清单（一行一条）
- **WD-1 节庆/集市/大型活动**（`wd.festival`）：✅ 已落地（默认 **on**，`kind=festival`）
- **WD-3 政令/公共公告**（`wd.edict`）：✅ 已落地（默认 **on**，`kind=edict`；只给公共情境，R5 拦数字）
- **WD-8 紧张升级**（`wd.tension`）：✅ 已落地（默认 **on**，`kind=tension`；只造 stakes）
- **WD-4 外来者/访客**（`wd.visitor`）：◻︎ 机制+开关**已就绪**（默认 **off**，未启用）
- **WD-5 市场波动/供给冲击**（`wd.supply_shock`）：◻︎ 就绪（默认 **off**）
- **WD-2 灾害/气候**（`wd.disaster`）：◻︎ 就绪（默认 **off**；仅环境级，不含逐 Agent 影响复算）
- **WD-6 疫病/健康**（`wd.epidemic`）：◻︎ 就绪（默认 **off**）
- **WD-7 公共工程/资源投放**（`wd.public_works`）：◻︎ 就绪（默认 **off**）
- **WD-9 季节/世界节律**（`wd.season`）：◻︎ 就绪（默认 **off**）
- **WD-10 外来集体事件（大规模）**：◻︎ 就绪（默认 **off**；`aggressive` 档须 Leader 明示）
> "就绪"= 走同一 Control 路径（开关+剂量→DIRECTIVE+GROUP_EVENT），仅**默认未启用**；启用即生效。

## 实测证据（命令 + 结果）
```
# 关：config["world_director"]={"enabled":False} → 0 事件；开：festival+edict enabled, dose_curve=moderate
WORLD_DIRECTIVE=24  WORLD_GROUP_EVENT=24  WORLD_DIRECTIVE_REJECTED=0  directed=true 事件 = 48
grep -c '"directed":true' ON.jsonl  → 48
grep -o '"directive_ref":"[^"]*"' ON.jsonl → D-0-wd.edict / D-0-wd.festival   # 可溯源
```
`pytest -q` **484 passed**；`make lexicon-gate` exit=0；`lint-imports` **9 kept/0 broken**。

## 约束落实
- **无决策类 LLM**：导演决策纯 RNG 先定（`rng_branch`），未引入 LLM（符合"要用先报 Leader"）。
- **replay 遇新事件不报错**：4 类型登记 `EVENT_TYPES` + `replay._NOOP_TYPES`（Fork B：审计折叠，不改世界状态）。
- **life 不 import engine**：未触碰 life。
- **字段装配点**：WD 事件由 `engine/hooks/world_director.py` **唯一装配点**产出，字段集中构造（对照 `tools/inert_registry.json` 的 `装配点` 列）。
