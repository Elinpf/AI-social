# T91 · v2 P1 物理层（生产/库存/双账本守恒/M(t)≥0/保底）实现与验收证据

> 作者：econ-dev ｜ 2026-10-10 ｜ 交付：`code/engine/production.py`（纯内核）、`code/engine/hooks/production.py`（hook）、`code/engine/hooks/econ.py`（4.2/4.3 世界预算 + 兜底铸币）、`code/config/policy.json`（经济档一等参数）

## 0. 交付与口径

- **`apply_production`**（挂 `PHASE4_CHAIN` 首项，4.1 前）：按同回合 `ACTIVITY_COMPLETED` 劳动类活动 → good **确定性映射**产出；含库存/上限溢出、上游投入消耗、生存消费、工具折旧、技能驱动。
- **事件**（08 §1.2 O 权威）：`PRODUCE{agent_id,good_id,qty,place,recipe,skill_level}`、`CONSUME{...,purpose}`、`DEPRECIATE{agent_id,asset_id,delta_mu}`、`PRODUCE_OVERFLOW{...,qty_dropped}`。
- **单位**：商品 `qty` = **milli-unit（1 unit=1000）**，`base_rate` 定点（food2000/material1000/tool300/service1000/art200）；已写入 `production.py` 模块 docstring，`qty` 入 `state_hash`。
- **双账本守恒**：货币式（kernel `check_all`）+ 商品式 `ΣPRODUCE = ΣCONSUME + Σ库存 + Σ溢出 + Σ折旧耗损`（kernel 断言，独立复算一致）。
- **`M(t)≥0`（世界级）**：销毁通道 `METABOLISM`/`PENALTY_APPLIED`/手续费受世界预算 `max(0,M−μ_floor)`（`μ_floor=0`）；个体现金允许为负（欠账）；`conservation` 断言 `M≥μ_floor`。
- **C 层保底**：`economy.fallback_mint_enabled`（**默认 false**，一等参数）、`fallback_trigger_mu=0`（自动 3×N×代谢）、`fallback_issue_max_mu=0`；兜底铸币 = `MONEY_MINTED`+`INIT_ENDOW` 等额配对（守恒），打 `flag=fallback`。

## 1. 验收（rule-based N=20×84, seed42；经济开 + 生命周期开 metabolism=140）

**canonical 配置 = OFF（`fallback_mint_enabled=false`）**：

| 指标 | 值 |
|---|---|
| `PRODUCE` | **321**（food 111216 / material 55608 / service 123915 / art 3946 milli） |
| `CONSUME` | 165 |
| 商品双账本守恒 | **✓**（`ΣPRODUCE 294685 = ΣCONSUME 136216 + 库存 158469 + 溢出 0 + 折旧 0`） |
| `M_min` / `M_final` | **0** / 35100 → **全程不穿负**（`M≥μ_floor=0`） |
| `fallback_mint_events` | 0（默认关） |
| `SYSTEM_ERROR` | **0** ｜ `ECONOMY_INVARIANT_VIOLATION` 0 |
| 守恒 / replay | 货币守恒 ✓ ｜ replay 逐位一致 ✓ |
| `pytest -q` | **269 passed** |

**ON 态（证明机制可用，非 canonical）**：`fallback-on` + 低代谢 60 → `M_min=99200 > 0`（**全程 >0**）、守恒 ✓、replay ✓；
`fallback` 机制单测 `test_fallback_mint_fires_and_conserves`（触发+守恒）与 `test_fallback_mint_off_by_default`（默认关）通过。

## 2. 根因钉死三件套（Leader 要求）——「商品造出来了，但没变现」

| 项 | 值 | 含义 |
|---|---|---|
| `MARKET_TRADE` 计数 / 卖方集中度 | 21 笔 ｜ distinct_sellers=**1**（top_seller_share=1.0，卖方=世界 `MARKET`） ｜ volume 2100 mu | **无 Agent 间交易**，只有零星「向世界市场购买」 |
| 收入分布 `I_eff` | P50=**0** ｜ P90=400 ｜ Max=2100 ｜ 正收入占比 **0.4** | 中位居民**货币收入为 0**；少数靠赠予/零散成交 |
| 84 回合总量 | `MONEY_MINTED` genesis 200000 + rescue 40000 ｜ `METABOLISM` −208058 ｜ `MARKET_TRADE` 2100 | 货币创造=救援、销毁=代谢；**商品产出未转化为货币收入** |

## 3. 正式缺口条目（回填 `v2/00-roadmap.md` P2 首要命题）

> **G-P1-1｜商品→货币转换通道缺失（属 B 层未涌现，非 A 层缺陷）**
> `PRODUCE>0` 且商品双账本守恒，但 `WAGE/EMPLOYMENT = 0`、`P50 收入(I_eff)=0`。
> A 层已提供「产生的手段」（生产/库存/技能/折旧），但**没有把商品变成货币的通道**——无工资、无雇佣、无 Agent 间市场。
> 结论：P1 造物成功，**变现待 B 层（雇佣/契约/最小市场带宽）涌现**。

## 4. 未达标/诚实报告

- `中位收入 ≥ 代谢`：**未达**（P50 I_eff=0 < 代谢 140）——见 §3 缺口，非粉饰。
- `tool` 商品 `PRODUCE=0`（material 投入链在 skill_practice 时点常不足；后续调参/配方可解）。
- ON 态在「种群灭绝（n=0）」时段兜底**无铸币对象** → `M` 可停在 0（不穿负，合规）；这是兜底的已知边界（需保留最小存活/系统池）。
