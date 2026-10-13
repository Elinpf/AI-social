# T347 · `D3` 口径②设计（只读）：世界层参数（节日/灾害/资源丰度）→ **真影响居民行为**

> 作者：仿真引擎与统计架构师（sim-engine-stats-architect）｜ 任务：T347（**只读设计，不动码**）
> 绑 sha：`962aaeb` ｜ 上游：`v2/refs/world-director-design.md`(T210)、`v2/refs/world-event-mechanisms.md`(T216)、`08 §1.2 T`(T238 登记)、`code/engine/world_director.py`
> 定位：**把口径②做成"随时可执行"**（用户若选①则停；选②即就绪）。**【事实】/【建议】/【待定】** 标注同惯例。

---

## 0. 现状（【事实】）

- `WORLD_DIRECTIVE`/`WORLD_GROUP_EVENT` ∈ **`_NOOP_TYPES`**（**不改世界状态**）；唯一消费者 = 叙事 ⇒ 实测 **`B−A = −2` = 2 个 noop** ⇒ **默认剂量下世界导演 = 纯旁白、零下游行为影响**。
- WD-Core 已具备：机制表（14 kind）、剂量曲线（conservative/moderate/aggressive，**默认 conservative**）、RNG 先定、判定树 R1–R6、三保底（`directed` / 开关+剂量 / `effective_from_round≥issued`）。
- 已默认开：`festival`/`edict`/`tension`（`world_director.json`），其余机制默认关。

**缺口**：`GROUP_EVENT` 之后**无传导**——没有任何路径把"世界层参数变化"送到 life 的决策/结算。

---

## 1. 核心机制：`WorldParams`（世界层参数）—— **可重建派生视图**（【建议】）

> 让世界层参数**真影响行为**，需一条**从 `GROUP_EVENT` 到 life 决策的传导链**。为守「日志=唯一记录」+ §5.9「可重建派生集合」，采用：

```
WorldParams(t) = f( 已提交的 GROUP_EVENT/WORLD_DIRECTIVE 的 [start,end) ∩ t , 静态 config )
  - 纯函数、可离线重算；对任意 t 由日志确定性重建；
  - 【建议】不进 state_hash、不入事件语义（派生视图，同"进行中"/§5.9 口径）；
  - life 的 perceive/planner/结算 读它（经 `round_events` 或专用只读端口）。
```

- **两条可选实现**：(i) **派生视图（推荐）**：`WorldParams = f(GROUP_EVENT, round)`； (ii) 显式写 `state.world_params`（入 `state_hash`、新增真相源）。**推荐 (i)**（与 T281/T286/T339 的"可重建派生"口径一致）。
- **可见性**：`GROUP_EVENT` 已 = `global`（已登记）；`WorldParams` 是**层内派生**、不经 `PERCEPTION_SCOPE`（非事件）。

---

## 2. 机制候选（≥3；每例：触发/传导链/可观测事件/是否碰 `state_hash`）

### M1 节日 / 集市（`festival`）
- **触发**：WD-Core RNG（`prob_bp`）→ `WORLD_DIRECTIVE(kind=festival)` → `WORLD_GROUP_EVENT(kind=festival, place=hall, slots)`。
- **传导链**：`WorldParams.activity_weight[place=hall]↑` / `open_slots` 扩 / `social_event_prob↑`（在 `[start,end)`）→ **life planner** 提高"去 hall / 社交活动"权重 → `PLACE_MOVE(hall)`↑、`ACTIVITY_STARTED(社交)`↑ → `RELATION_ENCOUNTER`↑、对话（`MSG_*`）↑。
- **可观测事件**：`GROUP_EVENT` + `PLACE_MOVE/ACTIVITY_*(place=hall)`↑ + `RELATION_ENCOUNTER` + `MSG_*`。
- **碰 `state_hash`**：**是（间接）**——世界参数本身不入；但**行为改变 ⇒ 活动/位置/关系派生变 ⇒ `state_hash` 变**。

### M2 灾害 / 供给冲击（`disaster`/`supply_shock`）→ 资源丰度
- **触发**：RNG（`prob_bp`，默认关）→ `GROUP_EVENT(kind=disaster|supply_shock, amp_bp/severity/places)`。
- **传导链**：`WorldParams.resource_milli[good/place] ± amp_bp`（`[start,end)`）→ **生产层** `resource_factor` 变 → `PRODUCE` 量变 → 库存/需求变 → `CONSUME`/`NEED_UPDATE`/`MARKET_TRADE` 变化 → 行为（求生/采购/省吃）。
  **红线**：**只改供给量/丰度，不写死价格**（价格仍 B 层涌现）。
- **可观测事件**：`GROUP_EVENT` + `PRODUCE`/`CONSUME`/`MARKET_TRADE`/`NEED_UPDATE` 分布变化。
- **碰 `state_hash`**：**是**（`inventory` 入 `state_hash`（T108）、下游行为变）。

### M3 政令 / 稀缺 / 紧张（`edict`/`tension`/`scarcity`）→ 公共情境 + 稀缺
- **触发**：RNG → `GROUP_EVENT(kind=edict|tension|scarcity, scarcity_bp/place)`。
- **传导链**：`WorldParams.market.scarcity[good]↑` → 撮合/供给参数变 → **抢购/竞价** → `MARKET_TRADE`/（若启用）`EXCHANGE_SETTLED`/`OFFER_*` → 行为（议价/结盟）。
  **红线**：**只制造 stakes / 情境，不指定对手、不指定胜负**。
- **可观测事件**：`GROUP_EVENT` + `MARKET_TRADE` + `OFFER_*` + `EXCHANGE_SETTLED`。
- **碰 `state_hash`**：**是**。

### M4（可选）季节 / 天气（`season`）
- **传导链**：`WorldParams.season_drift` → `NEED_UPDATE` 衰减率 / 活动 `affordance`（如雨天室内）→ 活动结构变。
- **可观测**：`GROUP_EVENT(season)` + `NEED_UPDATE`/`ACTIVITY_*` 结构漂移。

> **共同形态**：`GROUP_EVENT → WorldParams(派生) → life 读参 → 行为事件变`；**世界层只给"情境参数"，不给个体结果**（守 R5/R6）。

---

## 3. 与「三条保底」逐条对齐（红线）

| 保底 | 现状 | 口径② 如何满足 |
|---|---|---|
| **(a) 显式 `directed`** | `GROUP_EVENT`/`WORLD_DIRECTIVE` 带 `directed=true` + `directive_ref`（已登记） | **传导也以此溯源**：`WorldParams` 每一项可追溯到其 `directive_ref`；无 `directed` 的宏观事件**不存在**（验收 `count(改变宏观情境, 无 directed)==0`） |
| **(b) 独立开关 + 剂量** | 每机制 `enabled`+`dose`、剂量曲线（已存） | **新增传导开关**（见 §5）：`world_director.propagate.enabled` + 每机制**传导权重**（`activity_weight_bp`/`supply_amp_bp`/`scarcity_bp`，含在 `dose`）；**剂量 0 ≡ 关闭**（已实现 `prob_bp>0` 判据） |
| **(c) 只对未来** | `effective_from_round ≥ issued_round`（已登记） | **传导只对 `[start,end)` 未来生效**；**不改写已发生事实**（`WorldParams` 只作用于 `t ≥ start` 的决策，过去事件不动） |

---

## 4. 08 登记清单（我负责；**登记先于实现**）

| # | 项 | 内容 | 落点 |
|---|---|---|---|
| Q1 | **`WorldParams` 派生口径** | 声明为**可重建派生视图**（`f(GROUP_EVENT,directive,round)`；**不入 `state_hash`、不入事件语义**）；life 只读 | 08 §5.11（新） |
| Q2 | **事件** | **不新增事件类型**；`GROUP_EVENT`/`WORLD_DIRECTIVE` schema 复用（`params`/`dose` 已有） | §1.2 T（复核即可） |
| Q3 | **可见性** | `GROUP_EVENT`=`global`（已登记）；`WorldParams` 层内派生、不经 `PERCEPTION_SCOPE` | §3.5 / §1.2 T |
| Q4 | **传导映射表** | 机制 → 世界参数 → life 消费点（planner/结算）的**确定性映射**（登记在 08 §5.11） | §5.11 |
| Q5 | **新 config 键** | `world_director.propagate.enabled`（默认见 §5）+ 每机制传导权重（入 `dose`）；`world_director.json` **已入 `FINGERPRINT_FILES`** | §5.8 开关族 |

---

## 5. 可消融设计（对齐用户判据「同 sha 内只变一个开关」）

- **总传导开关**：`world_director.propagate.enabled` —— **默认 `false`（= 现状：旁白、零行为影响）**；用户选②后**改默认 `true`**。
  - `false` ⇒ `GROUP_EVENT` **照产**（保底 a 不变），但**不写/不派生 `WorldParams` 对行为的权重** ⇒ 退**纯旁白**（= 当前实证 `B−A=−2`）。
  - `true` ⇒ 启用传导 ⇒ 行为变。
- **每机制**：`mechanisms.<m>.dose` 内**传导权重**（如 `activity_weight_bp`），**剂量 0 ≡ 关闭该机制的传导**（沿用现 `prob_bp>0` 判据）。
- **消融矩阵**（同 sha 只翻一个）：`propagate=off/on` ×（可选）单机制 on/off ⇒ 可量"传导到底改了世界多少"。
- **与结论一致**：`propagate=false` 必须**逐字节等价现状**（除指纹行）——即"旁白档"就是消融基线。

---

## 6. ⭐ 与 `T300` 重冻的分界线 / 与 `D11`（T339）的先后

- **口径② 属【行为变】** ⇒ 落地即作废本轮基线 ⇒ **归入 "B 后·下一轮变更清单"**（与 `D11` 期②/③ 同批处理）。
- **与 `D11` 不抢同一批**：**各自独立开关**（`world_director.propagate.enabled` vs `time.ongoing/interleave.enabled`），但**都是行为变 ⇒ 必须分期**（同一晚只动一个语义轴，便于归因——同 Leader 对 T300 的口径）。
- **先后建议**：**两者无强依赖**（口径②对"未来情境"下参，原子结算亦可生效；D11 期②/③ 管时间轴）——
  - **建议：分两轮**，**先 `D11` 期②（时间轴基础）→ 再 口径②（世界参数传导）**；理由：传导的"活动参与/交错"在**有进行中的时间轴**上更自然（如节日提升"进行中活动"参与率）；但顺序非硬约束。
  - **对 T300**：二者**均列 "B 后" 下一轮清单**；**今晚照常重冻（甲）**（与 T339 结论一致），期②/③ 与 口径② 各自登记后**分期落**。
- **分界线承载**：沿用 `time_model` 戳（T339 §4）；口径② 可另加 `world_model`（`narrative`/`effective`）版本戳（【建议】），既有基线标 `narrative`。

---

## 7. 代价估计（【建议】+【未验证】）

| 维度 | 估计 | 备注 |
|---|---|---|
| **token** | **传导本身不增 LLM 调用**；但行为变（更多活动/社交/抢购）**可能增下游对话/决策调用** | 【未验证】须真跑量 |
| **日志增量** | 事件类型**不新增**；下游 `ACTIVITY/MOVE/PRODUCE/MARKET_TRADE` 计数↑（幅度随剂量） | 【未验证】估 +5–20%（随机制开启数） |
| **`state_hash`** | 行为变 ⇒ **变**（M1 间接 / M2/M3 直接）；`propagate=off` ⇒ **不变** | 作废本轮基线 → B 后重冻 |
| **N=50 时长** | 行为变 → 活动/调用平移；**不增 n 的复杂度** | 【未验证】 |

---

## 8. 与 `T339`（D11）的交叉点（列出，不重复）

| 交叉 | 说明 | 处置 |
|---|---|---|
| **X1** | `D11` 期② 的"进行中活动"∩ 口径② 的"节日提升活动参与" | 若两者都开：**节日权重作用于"进行中活动"的参与决策**；**登记在 08 §5.11 各写、勿互相复制** |
| **X2** | `D11` 期③ 的"交错/先后"∩ 口径② 的"抢购竞价（M3）" | 共享资源竞争下的排序按 `(start_μt,actor,seq)`（§5.10 口径）；**口径② 不另立排序** |
| **X3** | 开关簇 | `world_director.*` vs `time.*` **各自独立**（消融不互扰） |

---

## 9. 结论速览

- **核心**：新增 **`WorldParams` 可重建派生视图**（不入 `state_hash`）作传导枢纽；`GROUP_EVENT → WorldParams → life 决策 → 行为事件`。
- **机制**：M1 节日→活动权重；M2 灾害/供给→资源丰度（不碰价）；M3 政令/稀缺→市场稀缺（不指定对手/胜负）；M4 季节。
- **三保底**：逐条满足（`directed` 溯源 / 独立开关+剂量 / 只对未来）。
- **08**：Q1–Q5（新 `WorldParams` 口径 + 传导映射 + 新 config 键）；**不新增事件类型**。
- **消融**：`world_director.propagate.enabled` **默认 false=旁白（=现状逐字节）**，用户选②后默认 true。
- **T300/分界线**：**【行为变】⇒ "B 后"下一轮清单**；与 `D11` **不抢同一批、须分期**；建议 **先 D11 期② → 再口径②**；**今晚照常重冻（甲）**。

---

*（T347 只读设计完，绑 sha `962aaeb`；未碰 `code/**`。用户选②即据此登记 Q1–Q5 并放行实现。）*
