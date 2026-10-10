# T139 查根：`good_not_transferable=105` —— 选项与代价（仅分析，未改）

> 作者：kernel-dev ｜ 日期：2026-10-10 ｜ 状态：立案查根（Leader 要求"三选项 + 代价，先别改"）

## 0. 事实链（证据）
1. **`service` 会被生产**：`engine/hooks/production.py:34 ACTIVITY_GOOD = {"socialize": ["service"], ...}`。
   实测 `/tmp/t137b.jsonl`：PRODUCE 共 19 条 = `material 6 / food 6 / service 7`。
2. **入库不校验可转让性**：`engine/production.py:121 inv_add()` 只做上限钳制，不看 `transferable` → `service` 进 `state.inventory`。
3. **注册表已声明 service 不可转让**：`engine/production.py:27 GOODS["service"].transferable=False`，且 `:22` 注释「service 非库存/即时交付 → 不可经 inventory 转让」——**与 (2) 现状矛盾**。
4. **后果**：life 按"余量最大"选货 → 选中 `service` → 挂 `sale service` → econ `validate_deal` 正确 `DROPPED{good_not_transferable}`（105/120 笔）。

> 本质：**"不可转让品"被允许进入库存**，而库存是"可交易持有量"的语义。矛盾点在 **engine 生产/入库侧**（econ-dev 的 `engine/production.py` + `engine/hooks/production.py`），不在 life、不在 exchange。

## 1. 三个选项与代价

### (i) `service` 不进入库存（产出侧拦）
- **做法**：`ACTIVITY_GOOD["socialize"]=[]`（不产商品）；或产 `PRODUCE` 前按 `transferable` 判定，`transferable=False` **不入库**。
- **守恒/账本**：若**完全不产** `service` 事件 → 商品守恒式 `ΣPRODUCE==ΣCONSUME+Σ库存+Σ溢出+Σ折旧` 不受影响（service 两边都没有）。若"产但丢弃" → 必须记为 `PRODUCE_OVERFLOW{qty_dropped}`（既有口径），守恒式成立。
- **事件 schema**：**零新增**（仅改映射或走既有 `PRODUCE_OVERFLOW`）；08 无需改。
- **replay**：折叠器不动 → **旧日志兼容**；新日志事件流变化（确定性）。
- **服务经济涌现**：**有风险**——若直接"不产 service"，等于**关掉"服务作为产出"这一可能性**；即便"产但丢弃"也只留审计痕迹、无可交易语义。**与"给底座工具、不关可能性"的总纲相悖**（除非 (i) 只用于"过量/畸形"清理）。

### (ii) `service` 可产，但**即时交付、不入库存**（新增交付事件出口）
- **做法**：`socialize` 产出 → 发新事件 `SERVICE_DELIVERED{agent_id, good_id, qty, place, counterparty?, round}`（即时交付给消费方/自身），**不进 `inventory`**；exchange 不涉及 service。
- **守恒/账本**：`SERVICE_DELIVERED` 是**即时结算**、不驻留库存 → **不进商品库存总量式**；需与 `ΣPRODUCE` 口径解耦（service 不发 `PRODUCE`，改发 `SERVICE_DELIVERED`），否则 `ΣPRODUCE` 含 service 又与库存式冲突。
- **事件 schema**：**新增 `SERVICE_DELIVERED`**（08 只增不改；需权威补登字段）。engine 侧需 ①登记 `EVENT_TYPES` ②在 `replay.apply_event` 注册**确定性折叠器**（inventory-neutral：可 noop 或记 `state.services_delivered` 计数）→ 否则重放遇未知类型**报错**（X4）。
- **replay**：旧日志不含新类型 → 兼容；新日志需折叠器（随注册一起落地）。**逐位一致仍成立**。
- **服务经济涌现**：**最佳**——服务作为"即时交付的经济活动"被保留且**可观测**（可统计交付量/服务网络），库存语义保持干净（库存=可交易品）。代价是需要 08 权威补登 + 引擎折叠器 + econ 产出侧改造。

### (iii) 维持现状 + life 侧过滤
- **做法**：不改核心；life 选货时用 `WorldView.transferable_goods`（已交付 `aadf035`）过滤，不再错选 service。
- **守恒/账本**：**不动**。
- **事件 schema**：**不动**（08 无需改）。
- **replay**：**不动**。
- **服务经济涌现**：**保留**（service 仍可产、可入库），但语义略怪（"能生产、占库存，却不可交易"），且 inventory 堆积不可转让品（占 `cap_milli`、审计噪声：每笔错选产 `DROPPED`）。

## 2. 建议（供 Leader 裁）
- **立即**：采 **(iii)**（零风险，life 已具备 `transferable_goods`）——已消除 105 笔错选。
- **中期**：评估 **(ii)**（最符合"服务经济不关掉 + 库存干净 + 可观测"），需 08 权威补登 `SERVICE_DELIVERED` + 守恒口径明确 + 引擎折叠器 + econ 产出改造（跨 econ/engine/08-owner）。
- **(i) 不建议**以"完全不产 service"落地（会永久关掉服务经济）；若采 (i)，其正确形态其实是 (ii)（即时交付不入库）。

## 3. 归属（红线）
- `engine/production.py` / `engine/hooks/production.py`：**econ-dev**（(i)/(ii) 的产出/入库改动）。
- `engine/events.py` + `engine/replay.py` 折叠器：**kernel-dev（我）**（仅当 (ii) 新增事件时，登记 + 折叠器，加性）。
- `08` schema 补登：**sim-engine-stats-architect**（权威）。
- 我已交付的 life 侧过滤（`transferable_goods`）不依赖以上任一决定。

*（仅分析，未改任何代码；等 Leader 裁决。）*
