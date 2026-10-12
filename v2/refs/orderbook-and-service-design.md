# refs · 订单簿路径 + `SERVICE_DELIVERED` 设计稿（T277，**仅设计**）

> 作者：econ-dev ｜ 2026-10-12 ｜ 状态：设计 + 08 登记清单（**不写代码**；遵守夜间冻结）
> 依据（事实基线）：`v2/04-exchange-and-contracts.md` §4/§6、`v1.1/08 §1.2 R`、`v2/t139-service-not-transferable-analysis.md`、`code/config/perception_scope.json`（TF-1 单真源）、`code/engine/hooks/{econ,exchange}.py`。
> 标记约定：**【事实】**=现有代码/文档行为；**【建议】**=本稿提议；**【待定】**=不确定，需裁决。

---

## 0. 事实基线（只读核对，未改码）

- 【事实】**无持久订单簿**：`engine/hooks/econ.py` 的 `_settle_order_book` 只做**同回合内**限价单即时交叉（跨回合挂单簿无载体）；`INTENT.ECON.ORDER_PLACE` 仅在本回合内撮合。
- 【事实】**撤单无簿**：`ORDER_CANCEL` 意图当前落 `DROPPED{reason:"no_order_book"}`；Leader E7/A2c 已裁定「**有簿且该单存在才发 `ORDER_CANCEL`**，无簿保留 DROPPED」（不伪造事件）。
- 【事实】**成交出口**：`MARKET_TRADE` 已扩 `channel∈{orderbook}` + 一等 `counterparty`（允许 `seller∈Agent`）；`EXCHANGE_SETTLED` 承载多腿双边交换（08 §1.2 R）。
- 【事实】**service 矛盾（t139）**：`GOODS["service"].transferable=False`，但 `production.inv_add` 不校验可转让性 → service **进库存**；life 按余量选货 → 挂 `sale service` → `DROPPED{good_not_transferable}`（实测 105/120）。
- 【事实】**可见性单真源（TF-1）**：`config/perception_scope.json`（event→visibility_class）为 canonical；机器行为唯一实现在 `contracts/visibility.py::visible()`；`MARKET_TRADE`=**participants_only**；有「**感知集==记忆集**」门禁。
- 【事实】**开关族纪律**：`policy.<x>.enabled`（默认 true）+ 显式 OFF 发 `DROPPED{flag:"<x>_disabled"}` + 静默失效才 fail-loud。

---

## 1. 订单簿路径设计

### 1.1 事件族（建议）

| 事件 | phase | 建议字段 | 语义 | 与现有关系 |
|---|---|---|---|---|
| `ORDER_PLACED`（**建议新增**） | 4.1 | `order_id, agent_id, good_id, side∈{bid,ask}, price_mu, qty, place?, round` | 挂单入簿（可观测、可审计） | 意图 `INTENT.ECON.ORDER_PLACE` 的**事件出口**；与 `OFFER_CREATED` 并列（簿 vs 点对点要约） |
| `ORDER_CANCEL`（**已裁定新增**，A2c） | 4.1 | `order_id, agent_id, good_id, side, price_mu, qty, round` | 撤单（**仅"有簿且单存在"时发**） | 无簿 → 仍 `DROPPED{no_order_book}` |
| `MARKET_TRADE`（**复用**，channel="orderbook"） | 4.1 | 既有 + `counterparty` | 撮合成交 | 簿成交出口；`seller∈Agent` 即 agent↔agent |

- 【建议】**簿 = 由事件确定性折叠出的只读视图**（`ORDER_PLACED` − `ORDER_CANCEL` − 已成交量），**不新增持久 state 字段**（与 `liquidity.py` 同范式：纯函数、可重放、零 state 侵入）。**【待定】**若性能需要，可改入 `state`（代价：入 `state_hash`、基线重冻）。
- 【建议】**与要约路径的关系 = 并存、按来源分流**：订单簿撮合 → `MARKET_TRADE{channel:"orderbook"}`；点对点议价/契约 → `EXCHANGE_SETTLED`。二者共用**零和**结算与守恒。

### 1.2 撮合与确定性（建议）

- 优先级：**价格优先 → 时间优先（`ORDER_PLACED.seq` 升序）→ 同价同时按固定种子**（`ctx.rng("orderbook", round, good_id)`）——**禁止依赖 dict 顺序/墙钟**。
- 每笔成交：原子（买方扣款+卖方交货+手续费）→ 落 `MARKET_TRADE`（沿用既有原子性/零和）。
- 遍历与排序全序：`(side, price, seq, order_id)`。

### 1.3 独立开关（建议，对齐开关族）

`policy.orderbook.enabled`（默认 **true**；新增能力，当前 life 无 `ORDER_PLACE` 生产者 → 默认下 no-op、行为不变）。
OFF → engine 不挂簿撮合、life 不产 `ORDER_PLACE/ORDER_CANCEL`；发 `DROPPED{reason:"orderbook_disabled", flag:"orderbook_disabled"}`；**不 fail-loud**（显式消融）。与 `exchange.enabled` 为 **AND**。

---

## 2. 可见性口径（**重点**）

> 原则：**簿是信息通道，不得成为泄露/抢跑通道**；一切可见性必须落到 **TF-1 单真源**（`config/perception_scope.json`）+「感知集==记忆集」门禁。

### 2.1 事件级可见性（建议登记进 `perception_scope.json`）

| 事件 | 建议 class | 理由 |
|---|---|---|
| `ORDER_PLACED` | **`place_local`**（默认） | 挂单是「在**市场场所**公开的承诺」——与 `PLACE_MOVE`/`ACTIVITY_*` 同档；**不 global**（否则全镇即时可见 → 抢跑/信息泄露） |
| `ORDER_CANCEL` | **`place_local`** | 同挂单 |
| `MARKET_TRADE` | （既有）`participants_only` | 成交仅买卖双方可见（既有事实，保持不变） |

- 【待定】若 B 层要求「公开挂单板=全局」，应作为**制度变量**由 `orderbook_view.identity`/政策档切换，**不写死 A 层**（Leader E2）。

### 2.2 只读投影 `orderbook_view(good_id, identity)`（建议）

- **只读、由日志/状态派生**（非事件、非新原语）。
- `identity ∈ {aggregate(默认), named}`（**必须参数化**，E2）：
  - `aggregate`：仅**聚合深度**（各价位挂单量）+ 最优买卖价；**不返回**对手身份与逐单明细 → 防内幕/抢跑。
  - `named`：额外返回挂单者身份（**制度变量**，默认关；可被 B 层演化/消融）。
- **防泄露门禁**（建议）：投影只允许聚合「**对该 agent 可见**的事件」（`visible()` 判定后聚合），**不得越过 TF-1**；新增投影须进「感知集==记忆集」门禁用例。

---

## 3. `SERVICE_DELIVERED`（服务即时交付）

采 `t139` 的 **(ii) 服务可产、即时交付、不入库存**（t139 §2 建议的中期最优）。

### 3.1 事件（建议）

| 事件 | phase | 建议字段 | 折叠器行为 |
|---|---|---|---|
| `SERVICE_DELIVERED`（**建议新增**） | 4.1 | `agent_id, good_id("service"), qty, place, counterparty?, round` | **inventory-neutral**：可 noop 或记 `state.services_delivered` 计数（**不落 inventory**） |

- **守恒/账本**：即时结算、**不驻留库存** → **不进**商品库存总量式 `ΣPRODUCE=ΣCONSUME+Σ库存+Σ溢出+Σ折旧`；**service 不再发 `PRODUCE`**（改发 `SERVICE_DELIVERED`），使 `ΣPRODUCE` 与库存式口径一致。
- 【建议】新增**服务侧计数式**（仅审计/指标）：`Σ SERVICE_DELIVERED.qty`，与商品库存式**分离**。
- **可见性**：**`participants_only`**（交付方+受方）；自服务（`counterparty` 空）→ `subject_only`。**【待定】**是否允许他人"看到某人在提供服务"（`place_local`）——涉及"服务经济可见性"，建议默认 `participants_only`（保守）。
- **产出侧改造（econ 归属）**：`engine/hooks/production.py` 对 `ACTIVITY_GOOD["socialize"]=["service"]` 改为**发 `SERVICE_DELIVERED` 而非 `PRODUCE`**；`GOODS["service"]` 语义对齐「非库存」。
- **引擎侧（kernel 归属）**：`events.py` 登记 + `replay` 确定性折叠器（否则 X4 重放报错）。

---

## 4. 给 08 的登记清单（**登记先行**）

【建议】需 08 权威登记（只增不改）：

1. **新增事件**：`ORDER_PLACED`（字段见 §1.1）、`SERVICE_DELIVERED`（§3.1）；
2. **确认/补全既有**：`ORDER_CANCEL`（A2c 已裁，确认字段与 phase）；
3. **可选字段**：`MARKET_TRADE.channel`（已登记 `orderbook`）、`counterparty`（已登记）——确认沿用；
4. **不变量/口径**：`SERVICE_DELIVERED` **inventory-neutral**、**不入商品库存式**；订单簿成交仍走**零和**白名单；
5. **配置口径（08 §5.8 开关族）**：`policy.orderbook.enabled`（默认 true，OFF→`DROPPED{flag:"orderbook_disabled"}`、不 fail-loud）；
6. **可见性**：`ORDER_PLACED/ORDER_CANCEL`→`place_local`、`SERVICE_DELIVERED`→`participants_only` **登记进 `config/perception_scope.json`（TF-1 单真源）**（非 08 事件表，但须同步，避免双真源）。

---

## 5. 红线自检

- **不预设价格/工资/税率/铸币**：撮合价取自挂单 `price_mu`（life 提交）；`orderbook_view` 是**信息投影**、**不生成价**；【建议】不引入任何"参考价作为成交价"。
- **世界/社会层分离**：票/价/是否用簿由 B 层与政策档决定；A 层只给**确定性机制与开关**。
- **不造假事件**：无簿不发 `ORDER_CANCEL`（沿 A2c）；OFF 只发 `DROPPED` 审计。

---

## 6. 最小可落地切片（第一步先做什么）

> 建议**先 `SERVICE_DELIVERED`、后订单簿**（前者更小、解 t139 矛盾、不依赖簿的持久化）。

- **Slice-1（SERVICE_DELIVERED）**：① 08 登记（sim-engine-stats-architect）；② kernel 登记类型 + inventory-neutral 折叠器；③ econ 产出侧 `socialize` 改发 `SERVICE_DELIVERED`；④ `perception_scope.json` 加 `participants_only`；⑤ 测试：service 不再入库存 / 守恒不破 / 可见性。
- **Slice-2（订单簿 MVP）**：① 08 登记 `ORDER_PLACED` + 确认 `ORDER_CANCEL`；② 簿由事件折叠（只读视图）；③ `settle_market` 跨回合撮合（价格-时间-种子）；④ `orderbook_view(aggregate)` + 开关 `orderbook.enabled`；⑤ 测试：确定性排序、撤单可观测、开关三态、无簿不发 `ORDER_CANCEL`。

---

## 7. 待定清单

1. 【待定】簿视图：**只读折叠**（本稿建议）vs **入 `state`/`state_hash`**（性能 vs 基线重冻）。
2. 【待定】`ORDER_PLACED` 可见性 `place_local` vs 全局（制度变量，E2）。
3. 【待定】`SERVICE_DELIVERED` 是否 **`place_local`**（"可见他人服务"）——本稿保守取 `participants_only`。
4. 【待定】`orderbook.enabled` 默认值：本稿取 **true**（无生产者→no-op）；若要求"新能力默认 off"可改。
