# T365 · 08 登记草稿（世界层「持续可见」常驻源）—— **成稿形态，待解冻后并入追认**

> 类型：**草稿（DRAFT）**，只读设计文档（`v2/refs/`），**未改 `code/`、未改 `08` 正文**。
> 作者：`sim-engine-stats-architect`（08 事件 schema 权威）｜ 状态：草稿，**Leader 解冻广播后正式落 §1.2 T / §5.11 / §5.8**。
> 依据：`v2/refs/T365-persistent-world-layer-design.md`（`652491f`，narrative-designer，用户 14:27 批）Q4「R1–R7」；leader 14:51 指令。
> **是否并入 `T355` epoch 取决于两条前提（§6），故此处**只写草稿、不改指纹**。**

---

## 0. 一句话

把「偶发 RNG 触发」补一条「**确定性日历驱动的长窗口常驻源**」——**复用** `WORLD_DIRECTIVE`/`WORLD_GROUP_EVENT` 契约与 `world_params()` 派生视图，**唯一新增** = 「还有一个发射方：`world_calendar`」。⇒ 不新增事件类型、不新增派生视图、不新增消融轴（常驻源落在 `propagate` 之下）。

---

## 1. R1 · 事件字段（加性；落 08 §1.2 T）

> **T-rng/calendar · 世界层事件加【来源与调度】可选字段（应 T365，只增不改，不新增事件类型）**：
> `WORLD_DIRECTIVE` / `WORLD_GROUP_EVENT` 增**可选**一等字段：
> - **`source ∈ {"rng", "calendar"}`**（**必填于新发射方**；区分「偶发 RNG 触发」与「常驻日历触发」⇒ 可审计、可**分栏统计**，证「持续」来自日历而非碰巧）。缺省（旧日志/★仅 RNG）= 按 `"rng"` 解释（向后兼容）。
> - **`schedule : {"mode":"calendar", "cadence":"season|annual|festival|weekend", "profile":"season_tone|abundance_sine|festival_window|…"}`**（可选；描述**平滑 profile** 与**节奏**，供派生端求值）。**注：`cadence` 不含 `daypart`**（退让，见 §2/§8）。
>
> **装配点/产生方**：`world_calendar`（`round → 相位` 的**纯函数**）在**窗口边界**发射 `WORLD_DIRECTIVE(directed=true, mechanism_id="wd.calendar.<src>", source="calendar", schedule=…)`；**只发边界、不发每回合**（事件少）。RNG 侧 `source` 由 WD-Core 置 `"rng"`。
> **不变量**：`directed=true` 恒真、`effective_from_round ≥ issued_round` 恒真（保底 a/c **不变**）；`params` 仍**不得含金额/死亡/胜负数值**（R5 不变）。

**落点**：08 §1.2 **T.1/T.2 表格**各加一行可选字段（`source`、`schedule`）+ 一条装配点注。

---

## 2. R2 · `kind` 枚举 14 → 15（**Leader 已批**）

> **新增 1 项 `abundance`（资源丰度基线）**。理由：**语义正交**——若把丰度塞进既有 `season`/`supply_shock`，会让「按 `kind` 聚合 / 消融 / 归因」变糊；**归因靠 `kind`**。
> - `festival` **复用**（增 `window=true` 表常驻窗口，非新 kind）。
> - ⚠️ **`daypart` 退让（写死；Leader 14:54 裁定）**：**`daypart` 不作为常驻源、不新增 profile 支路、不新增 kind**。life 侧**已有完整**「时段→日程/活动」机制（`_base_activity(day_type,slot)` / `DAY_TYPE_PARAMS` / `planner` 的 `(day_type,slot)→活动模板`）⇒ 世界层**不得新造第二真源**（同 `T250` 双 `iou`/`T257` 双 truth 之型）。世界层若要影响时段/晨昏，**只经既有路径的偏置项**（`activity_weight` / `need_decay_scale` 一类），见 §8。
> - ⇒ `WORLD_GROUP_EVENT.kind` **14 → 15**：`season, festival, abundance, opportunity, public_works, supply_shock, scarcity, tension, incident, disaster, epidemic, visitor, edict, agenda, mass_event`。

**落点**：08 §1.2 **T.2 表格 `kind` 行**（14→15）+ 权威注（`v2/refs/world-event-mechanisms.md §2.1` 需同步登记该新增项）+ §4.2 事件表。

---

## 3. R3 · `WorldParams` 传导映射表补 3 行（落 08 §5.11 Q4）

> 在 §5.11 **Q4 传导映射表**补 **3 行**（上下限沿用现有 bp 夹取；`dose=0 ⇒ 该项恒等`）：

| 机制 `kind` | → `WorldParams` 参数 | 影响的生活/经济变量（消费点） | 方向 | 上下限（整数 bp/计数） | 备注 |
|---|---|---|---|---|---|
| `season` | `need_decay_scale[dim]` / 活动 `affordance` | `NEED_UPDATE` 衰减率 / 活动结构 | ± | `scale ∈ [0, 20000] bp`（沿用） | **既有行**（`§5.11 Q4` 已有） |
| `festival`（`window=true`） | `activity_weight[place]` / `open_slots` | planner 活动权重、选址、社交意愿 | ↑ | `activity_weight_bp ∈ [0, 20000]`（沿用） | **既有行**（已有；本处仅补 `window=true` 常驻语义） |
| `abundance`（**新 kind**） | `resource_milli[good/place]` | 生产层 `resource_factor` → `PRODUCE` 量 | ±（正弦缓变） | `amp_bp ∈ [0, 10000]`；**只改丰度不写价**（沿用 `supply_shock` 口径） | **新增行** |

- ⚠️ **`daypart` 不列本表**（**退让**，见 §2/§8）：不新增 `daypart → WorldParams` 映射；时段影响只经**既有** `activity_weight`/`need_decay_scale` 偏置项。
- **可判定**：每项 = `f(kind, dose, profile(t))` 的**确定性整数映射**；`profile(t)` 定点整数求值（**禁浮点**，见 §7 V1）。
- **上下限硬约束**：越界 → **夹取到限**（沿用 T352）。

---

## 4. R4 · 新 config 键（落 08 §5.8 开关族；`world_director.json`）

> `world_director.calendar.{season, festival, abundance, ecology}.{...}`：
> - 公共：`enabled`（默认见下）、剂量键。
> - `season`：`enabled=true`、`len_slots=4*28=112 slot(4 周)`、`fade_slots=6`、`strength_bp`。
> - `festival`：`enabled=true`、窗口 = **周末 2 日**（`day5–day6`）、`activity_weight_bp`、`jitter_bp`。
> - `abundance`：`enabled=true`、`period_slots=112(4 周)`、`amp_bp`。
> - `daypart`：**不新增键**（退让既有，见 §8）。
> - `ecology`：`enabled=false`（可选，【未验证】）。
>
> **剂量语义**：`strength_bp/amp_bp` 为**定点整数（万分比）**；**剂量 0 ≡ 关闭该源**（沿用 `prob_bp>0` 判据）。
> **默认开**：用户要的功能默认开（与 `D11` 期② / `D3-②` 一致）；`ecology` 默认关（【未验证】）。
> **`world_director.json` 已在 `FINGERPRINT_FILES`** ⇒ 新键 **进指纹**（见 §5）。

**落点**：08 §5.8 开关族（新增 `world_director.calendar.*` 说明段）+ `config/world_director.json`（实现时，与消费者同批落地防 inert）。

---

## 5. R5 · 指纹 / 重冻影响声明（落 08 §5.11 尾部）

> ⚠️ **影响声明（T365 必答）**：
> - **`engine_version` 指纹：变**（新增 `world_director.calendar.*` config 键，且 `world_director.json` **已在 `FINGERPRINT_FILES`**）——与「只动事件 payload 不改 config」的**不同类**（对照片 `T360 G-lg`）。
> - **行为：变**（默认开 ⇒ 日历常驻源经 `world_params` 真影响行为）。
> ⇒ **【指纹变】+【行为变】⇒ 必须重冻**。
> - **epoch 归属**：**期望并入 `T355`**，**前提=Leader 两条（§6）同时成立**；**任一不成立 ⇒ 独立 epoch、如实多冻一次**（不为省重冻抢工）。
> - **分界线戳**：`world_model` **保持 `"effective"`**（与 `T352` 同，**不新立分界线**）。
> - **消融口径**：常驻源在 `world_director.propagate.enabled`（总闸）之下，**不新增独立消融轴** ⇒ `T355` 仍 **2×2（`time.ongoing` × `propagate`）**；须在归因里报告「两侧都含常驻源」，并用**日历-only 对照**（§7）补证「持续≠偶发」。

---

## 6. epoch 前提（Leader 定；两条**同时**成立才并入 `T355`）

1. **不加轴**：常驻源作 `propagate=on` 的**源项**、不新增独立消融轴 ⇒ 仍 2×2。
2. **赶在起跑前发布**：`T355` 起跑前完成 **08 登记 + 实现 + 前端可见通道声明（R）**。

> 任一条不成立 ⇒ **独立 epoch**，如实声明多冻一次。

---

## 7. R6 / R7 · 可见性与可审计

- **R6 可见性（落 08 §3.5 / §5.11）**：`GROUP_EVENT`/`WORLD_DIRECTIVE` = **`global`**（已登）；`WorldParams` 为**层内派生**、**不经 `PERCEPTION_SCOPE`**（同 `T352`）。**本条不改可见性**。
- **R7 可审计口径（落 08 §1.2 T 脚注）**：常驻源每条 `directed` 可经 `mechanism_id` + `directive_ref` 检索；**`source="calendar"` 与 `"rng"` 分栏统计**（证「持续」来自日历而非碰巧触发）。

---

## 8. 窗口尺度（三层；**快层退让不新造**）

| 层 | 常驻源 | 默认尺度 | 一周跑批表现 | 防机械 |
|---|---|---|---|---|
| **慢（底色）** | `season` | `len_slots=4 周` + `fade_slots=6` | **恒定偏移**（底色） | fade 带（非阶跃） |
| **中** | `festival` | **周末 2 日**，每周一次 | **必现且有起止**（验收主战场） | `jitter_bp` 种子抖动 |
| **中慢** | `abundance` | `period_slots=4 周`（正弦） | 近似恒定偏移 | 正弦平滑 |
| **快** | **时段基调（既有）** | **life 既有机制**（`_base_activity`/`DAY_TYPE_PARAMS`/`planner` 的 `(day_type,slot)→模板`/`SCHEDULE_PLANNED`） | 日内 28 次节奏 | 天然 |

- ⚠️ **快层 `daypart` 退让（防第二真源）**：与 life 既有「时段→日程/活动」机制**重叠** ⇒ **世界层不做独立常驻源**；若要影响，**只经既有路径的偏置项**（如 `world_params.need_decay_scale`/`activity_weight`），**宁可退让不并列**（同 `T250` 双 `iou`/`T257` 双 truth 之型）。
- ⚠️ **`jitter_bp` 必须确定性可重建**：抖动**只能由 seed 派生**（`rng_branch(seed, "world_calendar", <window_index>)`，与既有分层 RNG 同源）、**可离线重算**；**不得引入不可重建随机源**（否则 `restore()`/续跑分叉，同 `T298` 型）。

---

## 9. 三保底对齐（逐条，红线不变）

| 保底 | 本设计如何满足 |
|---|---|
| **(a) 显式 `directed`** | 日历在窗口边界发 `WORLD_DIRECTIVE(directed=true, source="calendar", mechanism_id="wd.calendar.<src>")`；`WorldParams` 各项可溯源 `directive_ref`；验收 `count(改变宏观情境, 无 directed)==0` |
| **(b) 独立开关 + 剂量** | 每源 `wd.calendar.<src>.enabled` + 剂量（`strength_bp`/`amp_bp`/`len_slots`）；总闸沿用 `propagate.enabled`；**剂量 0 ≡ 关闭** |
| **(c) 只对未来** | 窗口 `[start,end)`、`effective_from_round = 窗口起 ≥ issued_round`；只对 `t ≥ start` 生效、**不改写已发生事实** |

---

## 10. 风险 / 未验证（如实标注）

| # | 项 | 状态 |
|---|---|---|
| V1 | `profile(t)` 平滑求值**定点整数化**（禁浮点） | 【未验证】需实现时定 |
| V2 | 「世界层可见通道 R」依赖前端声明（未落地前画面闸不可测） | 【未验证】需 frontend |
| V3 | `len_slots`/`period_slots` 与 `TRAVEL`/活动时长交互 | 【未验证】 |
| V4 | 新增 config 键对日志体积/耗时影响 | 【未验证】 |

---

## 11. 变更清单（并入 08 §8 时追加一行）

| 类别 | 变更 | 落点 |
|---|---|---|
| **字段扩展（`WORLD_DIRECTIVE`/`WORLD_GROUP_EVENT`，T365）** | 加**可选** `source ∈ {rng,calendar}`（缺省=rng，向后兼容）+ `schedule{mode,cadence,profile}`；**不新增事件类型** | §1.2 T |
| **`kind` 枚举 14→15（T365）** | 新增 `abundance`；`festival` 复用（`window=true`）；**`daypart` 退让、不新增 kind / profile** | §1.2 T.2 / §4.2 |
| **传导映射补齐（T365）** | **补 3 行**：`season`(既有)/`festival`(既有，补 `window=true` 语义)/`abundance`(**新增**)；**`daypart` 不列**（退让） | §5.11 Q4 |
| **新 config 键（T365）** | `world_director.calendar.*`（`world_director.json` 在指纹内）⇒ **【指纹变】+【行为变】（默认开）⇒ 需重冻**；`world_model` 保持 `"effective"` | §5.8 + §5.11 |

---

*（草稿完 — 只读文档，未改 `code/`/`08` 正文。正式落账在 Leader 解冻广播后，且 epoch 归属以 §6 两前提为准。）*
