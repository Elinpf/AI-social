# T365 · 世界层「持续可见」设计 + 08 登记清单（用户已批）

> 文档类型：设计 + 登记清单（**只读设计，不改 `code/`**）｜ 作者：narrative-designer
> 状态：v1（供 Leader；含推荐 + 理由 + 可测验收判据 + epoch 建议）
> 上游依据：`v2/refs/world-director-design.md`(T210)、`v2/refs/world-event-mechanisms.md`(T216)、`v2/refs/worldbook-v1.md`(T260)、`v2/refs/T347-d3-worldparams-to-behavior-design.md`(T347)、`v2/refs/T289-world-director-dose-diagnosis.md`(T289)、`v1.1/08 §5.11`(已登 `WorldParams`)、`code/engine/world_params.py`、`code/config/world_director.json`
> 绑定现状 sha（读时）：`code/engine/world_params.py` / `code/config/world_director.json`（主树读，未改）

---

## 0. 问题与目标（为什么"偶发"不够）

**现状（有据）**：
- `T289` 实测：世界导演 `world_director.json` 默认开，但**剂量≈1 次/周**（保守曲线半衰 + 基数低）→ `WORLD_DIRECTIVE/WORLD_GROUP_EVENT` 各 **1 条/84 回合**。
- `T347/T352` 已把 `D3-②` 通路接上（`WorldParams = f(已提交的 GROUP_EVENT/WORLD_DIRECTIVE 的 [start,end) ∩ t, config)` → life 读参 → 行为），但**源是偶发、窗口又短** ⇒ **行为与画面几乎无持续变化**（用户 13:10「变化不大」正是此味）。

**目标（用户 14:27 拍板「世界层可以加持续可见」）**：让世界层参数**持续地、可感知地存在**——不是偶发指令，而是**常驻的、随时间平滑演变的**情境（季节基调 / 节日窗口 / 资源丰度基线 / 时段基调）。

**一句话设计**：**把"偶发 RNG 触发"补上一条"确定性日历驱动的长窗口常驻源"**——长窗口保证"持续"，窗口边界的 `directed` 指令保证"可审计"，平滑 profile 保证"可见"。

---

## 1. 机制表（常驻源 = 确定性世界日历）

> 每个常驻源的**发射方 = `world_calendar`**（`round → 相位` 的**纯函数**）；在**窗口边界**发一条 `WORLD_DIRECTIVE(directed=true, [start,end), params={profile,…})`（**只发边界，不发每回合**，故事件少）；`world_params(t)` 在窗口内**求值 profile**（平滑、可重建）。这使"常驻"复用**既有事件契约与派生视图**（见 §2）。

| ID | 常驻源 | 持续源（怎么来 / 如何平滑演变） | 作用面 | 默认强度 | 可消融开关 | 剂量 |
|---|---|---|---|---|---|---|
| **PP-1** | **季节基调** `season` | 日历：`round → 季节相位`（每 `len_slots` 一个季节），相位边界线性/cos 平滑过渡 | **行为**(need 衰减率、活动 affordance) + **画面**(季相配色/天气叠加) | 中 | `wd.calendar.season.enabled`（默认 **true**） | `strength_bp`、`len_slots`、过渡带 `fade_slots` |
| **PP-2** | **节日窗口常驻** `festival` | 日历：每年/每季**固定节日**，多日窗口常驻（非 1 次/周） | **行为**(活动权重 `hall/plaza`↑、社交意愿) + **画面**(节庆横幅/装饰) | 中 | `wd.calendar.festival.enabled`（默认 true） | 窗口 `[start,end)`、`activity_weight_bp` |
| **PP-3** | **资源丰度基线** `abundance` | 日历：收获季/淡季（缓慢正弦，周期=若干周） | **经济**(生产层 `resource_factor`，**只改丰度不写价**) + **画面**(农田色/货架) | 低–中 | `wd.calendar.abundance.enabled`（默认 true） | `amp_bp`、`period_slots` |
| **PP-4** | ~~时段基调 `daypart`~~ → **退让（不新造）** | **life 侧已有时段→日程/活动机制**（`life/agent.py::_base_activity`、`life/constants.py::DAY_TYPE_PARAMS`、`life/planner.py` 的 `(day_type,slot)→活动模板` 表、`SCHEDULE_PLANNED`/`_plan_slots`）⇒ **世界层不新造第二套**；若要影响，只经**既有路径的偏置项**（如 `world_params.activity_weight`/`need_decay_scale`），**不并列** | 行为（经既有） | — | 复用既有（不新增 `wd.calendar.daypart`） | 经既有偏置项 |
| **PP-5** | 生态周期（可选）`ecology` | 日历：水源/气候慢变量 | 行为+经济 | 低 | `wd.calendar.ecology.enabled`（默认 **false**） | 【未验证】 |

- **通用条款**：常驻源**只给情境参数，不给个体结果**（不给对手/胜负/价格，守 R5/R6）；统一经 `world_params()` 传导（§2）。
- **剂量语义**：`strength_bp`/`amp_bp` 为定点整数（万分比）；**剂量=0 ≡ 关闭该源**（沿用 `prob_bp>0` 判据）。
- **平滑**：profile 求值为**定点整数**（bp），避免浮点导致的不可复算【未验证：需定点实现】。

### 1.1 窗口尺度（**Leader 质疑④**：这条比机制表更影响"用户能不能看见"）

**矛盾**：观看/跑批窗口只有**一周（84 回合 = 28 slot）**量级。
- 窗口 **>> 一周** ⇒ 一周内看不出"变化"，只看出"**底色不同**"；
- 窗口 **<< 一周** ⇒ 显得**机械周期**（直接伤"活人感"= 用户第一条目标）。

**默认尺度 = 多尺度叠加**（让一周跑批里**同时看到"底色"与"变化"**）：

| 层 | 常驻源 | **默认窗口尺度** | 一周跑批里表现为 | 防机械 |
|---|---|---|---|---|
| **慢（底色）** | 季节基调 `season` | `len_slots = 4 周`（336r）+ `fade_slots=6` 过渡带 | **恒定偏移（底色）**——与 baseline 对照"底色不同" | fade 带（非阶跃） |
| **中** | 节日窗口 `festival` | **周末 2 日**（`day5–day6`，24r），**每周一次** | 一周内**必现**一个**有起止**的节庆窗口（"过了一个节"） | 种子里小 `jitter_bp`（非严格等周期） |
| **中慢** | 资源丰度 `abundance` | `period_slots = 4 周`（缓慢正弦） | 近似**恒定偏移**（底色） | 正弦平滑 |
| **快（活人感）** | ~~时段基调~~ → **既有**（day_type/slot） | **life 既有机制**（§1 PP-4） | 一周内 **28 次**变化（晨昏节奏）——**已由既有机制提供，世界层不新造** | 天然日节律 |

**理由**：**单尺度必陷两难**；**多尺度叠加**同时拿到：慢层=底色（可对照看出）、中层=**周内可见的"事件"**（必现且有起止）、快层=**日内活人感**（最高频可见）。

**"用户在一周跑批里怎么看出它"（默认尺度下）**：
1. **快层**：每天晨→午→暮→夜，行为/画面对应变化（肉眼节奏）；
2. **中层**：一周内出现**一个有起止的节庆窗口**（装饰/聚集），**与无节周末对照明显**；
3. **慢层**：与 baseline 跑并排看，**"底色不同"**（季节/丰度）——**须标注为"恒定偏移"，非"动态演变"**（见 §5.2）。

**多尺度 ≠ 反"作者化"**：三层都是 `directed` 常驻源（§2/§3），可分别消融。

**⚠️ 提醒落实（Leader 两条）**：
1. **快层退让（防第二真源）**：`daypart` 与 life 既有"时段→日程/活动"机制**重叠**（已核实：`_base_activity`/`DAY_TYPE_PARAMS`/`planner` 的 `(day_type,slot)→模板`表/`SCHEDULE_PLANNED`）⇒ **不做独立常驻源**（新造即第二真源，同 `T250` 双 `iou`/`T257` 双 truth 之型）；世界层若要影响，**只经既有路径的偏置项**，**宁可退让不并列**。
2. **`jitter_bp` 必须"确定性可重建"**：抖动**只能由 seed 确定性派生**（`rng_branch(seed, "world_calendar", <window_index>)`，与既有分层 RNG 同源），**不得引入不可重建的随机源**——否则 `restore()`/续跑会分叉（今晨 `T298` 同型）。**实现时 `jitter` 入 `world_params` 的确定性求值，可离线重算。**

**优先级（Leader 定）**：**中层（周末节日）先做扎实**——最可能被用户"肉眼看出来"，是这轮验收主战场；**快层退让（并入既有）**；**慢层保留为"底色"**。

---

## 2. ⭐ 与 `T352 world_params()` 派生视图的关系 —— **同一派生视图，新增"发射方"**（推荐 = 第一实现）

**结论：同一派生视图（第一实现），不新增视图。** 严格说比"新增源项"更省：**视图与其输入类都不变**——因为常驻源**就是 `WORLD_DIRECTIVE`**（只是由**日历**发射而非 RNG）。

```
现状：  WorldParams(t) = f( RNG 触发的 WORLD_DIRECTIVE/GROUP_EVENT ∩ [start,end), config )
本设计：WorldParams(t) = f( (RNG 触发 + 日历触发) 的 WORLD_DIRECTIVE/GROUP_EVENT ∩ [start,end), config )
        ↑ 唯一新增 = "还有一个发射方：world_calendar"；视图/事件契约/消费点全不改
```

**推荐理由（五条）**：
1. **单一消费点**：life 只读**一个端口** `kernel.world_params(round)`（`life/agent.py::_read_world_params`）；新视图 ⇒ 第二读取路径 + 第二实现 ⇒ 违背"口径唯一"。
2. **三保底天然满足**：常驻源走**同一 `directed` 事件契约** ⇒ (a) 可溯源、(c) 只对未来，**无需为"非法事件源"另立规矩**。
3. **不新增事件类型**：复用 `WORLD_DIRECTIVE`（强化 `T347 Q2`「不新增事件类型」）。
4. **消融/归因复用**：`propagate.enabled`（总闸）+ 每机制 `dose` 直接生效；无需新消融框架。
5. **可重建派生**：日历是 `round` 的纯函数，`world_params(t)` 仍**可由日志+config 确定性重建**（不强依赖每回合事件）。

> **被否决的"第二实现"**：把常驻量做成**纯时间项 `ambient(round, config)`** 直接并入视图——**看似更省事件，但会造出"无 `directed` 事件却改变了行为"的参数 ⇒ 违反保底 (a)**（这正是 `T347 §3` 要守的）。故**必须让常驻源落 `directed` 事件**。

---

## 3. 三保底对齐（逐条）

| 保底 | 本设计如何满足 |
|---|---|
| **(a) 显式 `directed`** | 日历在**窗口边界**发 `WORLD_DIRECTIVE(directed=true, mechanism_id="wd.calendar.<src>", directive_id=…)`；`WorldParams` 每项溯源其 `directive_ref`；验收 `count(改变宏观情境, 无 directed)==0` |
| **(b) 独立开关 + 剂量** | 每常驻源 `wd.calendar.<src>.enabled` + 剂量（`strength_bp`/`amp_bp`/`len_slots`）；总闸沿用 `world_director.propagate.enabled`；**剂量 0 ≡ 关闭** |
| **(c) 只对未来** | 窗口 `[start,end)`、`effective_from_round = 窗口起 ≥ issued_round`；**只对 `t ≥ start` 的决策生效，不改写已发生事实** |

---

## 4. 08 登记清单（交 `sim-engine-stats-architect`；**登记先行，未登不实现**）

| # | 项 | 内容 | 落点 |
|---|---|---|---|
| **R1** | **事件类型** | **不新增类型**；复用 `WORLD_DIRECTIVE`/`WORLD_GROUP_EVENT`。**建议新增两个可选字段**：`source ∈ {"rng","calendar"}`（区分偶发 / 常驻，**可审计**）、`schedule: {"mode":"calendar","cadence":"season|annual|daypart","profile":"season_tone|…"}`（描述平滑 profile） | 08 §1.2 T（加性字段） |
| **R2** | **`kind` 枚举**（**✅ Leader 已批**：语义正交不塞同一 kind——归因靠 kind） | 现有 14 值中 **`season` 已存在**；**新增 1 项 `abundance`**（资源丰度基线）；`festival` 复用（加 `window=true` 表常驻）；`daypart` 作为 `season` 的 `profile` 变体（**不新增 kind**）。⇒ **kind 14 → 15** | 08 §1.2 T / §4.2 表 |
| **R3** | **`WorldParams` 映射扩表** | 在 `§5.11 Q4` 传导映射表**增加 4 行**：`season → need_decay_scale[dim]/affordance`；`abundance → resource_milli[good/place]`（**只改丰度不写价**）；`festival(window) → activity_weight[place]/open_slots`；`daypart → need_decay_scale[dim]`。**上下限沿用现有 bp 夹取** | 08 §5.11 Q4 |
| **R4** | **新 config 键** | `world_director.calendar.{season,festival,abundance,daypart,ecology}.{enabled,len_slots|period_slots,phase_slots,fade_slots,strength_bp|amp_bp}`。`world_director.json` **已在 `FINGERPRINT_FILES`** | 08 §5.8 开关族 + `config/world_director.json` |
| **R5** | **指纹 / 重冻声明** | 新增 config 键 ⇒ **【指纹变】**；默认开 ⇒ **【行为变】** ⇒ **必须重冻**；`world_model` 戳**保持 `"effective"`**（同 T352，不新立分界线） | 08 §5.11 尾部 |
| **R6** | **可见性** | `GROUP_EVENT` = `global`（已登）；`WorldParams` 层内派生、**不经 `PERCEPTION_SCOPE`**（同 T352） | 08 §3.5 / §5.11 |
| **R7** | **可审计口径** | 常驻源每条 `directed` 可 `mechanism_id`+`directive_ref` 检索；`source="calendar"` 可与偶发 `"rng"` **分栏统计**（证明"持续"来自日历而非碰巧触发） | 08 §1.2 T 脚注 |

> **【已裁决（Leader 2026-10-13）】**：`abundance` **新增 kind ✅ 同意**（语义正交，复用会让"按 kind 聚合/消融"变糊）；`source∈{rng,calendar}` + `schedule{}` 一并同意。登记由 `sim-engine-stats-architect` 在解冻后派（他当前在 `T363`）。

---

## 5. ⭐⭐ 可感度验收判据（本单最要紧：怎么证明"用户真的能看见"）

> 目标：把"感觉更丰富"变成**可测**。两条闸——**行为族 delta**（日志可复算）+ **画面可见差异**（像素可测）；两条都要求**持续性**（贯穿窗口，排除偶发尖峰）。

### 5.1 装置前提（否则复算不出来；吸取今晚"假分叉/假间歇"教训）
- **同 seed、同 sha、共享同一 `freeze_cache`**（`T289 §6`：否则真 LLM 跨批噪声淹没小信号）；
- **开/关两跑各独立进程**（防模块级状态污染造"假分叉"）；
- 唯一差异 = `wd.calendar.*`（或 `propagate`）开关 + **指纹行**。

### 5.2 闸 A · 行为族 delta（确定性、可从日志复算）

| 族 | 指标（从日志算） | 默认阈值（【待标定】） |
|---|---|---|
| **活动族** | `place_share[受影响 place]`（如 `hall/plaza`）、`activity_type_share` | `|Δ| ≥ 5%`（相对） |
| **社交族** | `RELATION_ENCOUNTER`、`MSG_*` 的周计数 | `Δ ≥ +5%` |
| **需求族** | `NEED_UPDATE` 各单位衰减斜率 | `Δ ≥ +5%` |
| **经济族**（若 abundance 开） | `PRODUCE` 体量、`resource_factor` 生效量 | `Δ ≥ +5%` |

**通过 = 三条同时成立**：
1. **幅度**：`|Δ| ≥ 阈值`；
2. **方向一致**：≥⌈2/3⌉ 独立 seed 同向（符号检验）；
3. **⭐ 持续性**：**窗口内 ≥70% 的 slot 出现非零偏置**（**单点尖峰不算**——这是与"偶发 episodic"的关键区分）。

> **⚠️ 必须区分"持续"与"恒定偏移"（Leader 收紧③）**：若**窗口 >> 跑批长度**（如季节 `len=4 周` 但只跑 1 周），则本次对照实为**常数偏置**——**也判"通过"**（能被看见就算），**但证据里必须显式写明"这是常量偏置/底色、不是动态演变"**，**不得把两件事混成一句"持续可见"**。判据分栏：
> - **恒定偏移（底色）**：整窗偏置符号不变、幅度近常数 → 证据标 `mode="constant_offset"`；
> - **动态演变**：窗内出现**符号/幅度变化或过渡带**（如节庆窗口的起止、daypart 的日内轮转）→ 证据标 `mode="dynamic"`。

### 5.3 闸 B · 画面可见差异（像素可测 + 人眼佐证）

> **⚠️ 可执行前置（Leader 收紧③）**：闸 B 依赖"**前端声明的世界层可见通道 R**"，而**该通道目前不存在** ⇒ **闸 B 的前置 = frontend 先声明 R**。**在 R 声明前**：可感度验收**降级为「闸 A + 首帧对比图（人眼）」**；**严禁把"闸 B 没过"变成"再调一轮美术"**（用户已明确"看不出就停"的停止规则——门禁不过就是不过，不用美术去凑）。

- **定义"世界层可见通道"**：前端**由 `WorldParams` 驱动**的像素区域集合 R（如地面色调、天空、节庆横幅、季相 overlay）——由前端显式声明（**需 frontend 配合**，【未验证】）。
- **确定性像素闸**：同一 round、开/关两帧，**R 区域 ΔRGB 像素占比 ≥ `T_px`（默认 5%）**，**且窗口内每一采样帧都成立**（持续性）。
- **人眼佐证**：窗口内抽 `N=5` 帧，**≥80% 被 ≥2 评审判"明显不同"**（呼应"用户真的能看见"）。
- **复用**：现有截图工具 `code/frontend/tools/shot.py` / `gate_render.py`；产物落 `v2/evidence/`（含 off/on 对比图 + 差分热力图）。

### 5.4 证"持续 ≠ 偶发"的最小证据
- **对照**：仅开日历常驻源（关掉 RNG 偶发机制）→ **闸 A 持续性 + 闸 B 每帧成立仍通过** ⇒ 证明"持续可见"来自日历，而非偶发事件；
- **反例**：只留 RNG 偶发（关日历）→ 持续性应**不通过**（单点尖峰）⇒ 双向证伪。

---

## 6. 与 epoch 的关系建议（只给判断与理由，落地时点由 Leader 定）

**判断：能赶进 `T355`（推荐），前提是 Leader 定的两条【同时】成立。**
- **条件①（不加轴）**：常驻源作 `propagate=on` 的源项、**不新增独立消融轴** ⇒ `T355` 仍 2×2（`time.ongoing` × `propagate`）。
- **条件②（赶在起跑前发布）**：**`T355` 起跑前**完成 **08 登记 + 实现 + 前端可见通道声明（§5.3 R）**。
- **任一条不成立 ⇒ 独立 epoch，如实声明多冻一次**；**不为省一次重冻而抢工**（抢工出来的基线要重做，代价翻倍）。
- 理由：① 常驻源复用**同一 `world_params` 视图、同一 `WORLD_DIRECTIVE` 契约、同一 `propagate` 开关** ⇒ 不新增语义轴；② "持续可感"由**窗口常驻（多尺度，§1.1）**保证，不需独立开关轴；③ 满足两条件即**省一次重冻**。
- 代价/注意：需在 `T355` 的 2×2 归因里**报告"两侧都含常驻源"**，避免把"持续"误记成 `propagate` 的效应——用 §5.4 的**日历-only 对照**补证。


**例外（独立 epoch）**：若 Leader 要求常驻源做**独立消融轴**（`wd.calendar.enabled` 单独 A/B）⇒ 建议**独立 epoch**（避免 `2×2×2` 归因复杂 + 守"一期一纵"); 代价 =**多冻一次**。

---

## 7. 风险 / 未验证（如实标注）

| # | 项 | 状态 |
|---|---|---|
| V1 | profile 平滑求值的**定点整数化**（避免浮点不可复算） | 【未验证】需实现时定 |
| V2 | "世界层可见通道" R 的**定义依赖前端实现**（未落地前闸 B 不可测） | 【未验证】需 frontend 配合 |
| V3 | 常驻参数长期偏置使"涌现 vs 作者化"更难分离 | 风险 ⇒ 用 `calendar.*` 独立开关做消融（若独立 epoch） |
| V4 | `len_slots`/`period_slots` 与 `TRAVEL`/活动时长的交互 | 【未验证】 |
| V5 | 新增 config 键的**日志体积/耗时**影响 | 【未验证】 |

---

## 8. 结论速览

- **机制**：5 个常驻源（季节/节日窗口/丰度基线/时段基调/生态可选），由**确定性日历**发射**长窗口 `directed` 指令**。
- **⭐ 窗口尺度（Leader 质疑④，已在 §1.1 给默认）**：**多尺度叠加**——慢层季节/丰度=`4 周`（一周跑批里=**底色/恒定偏移**）、中层节日=**周末 2 日每周一次**（一周内**必现且有起止**，**验收主战场**）、快层=**既有** day_type/slot 机制（**世界层退让、不新造第二真源**）；防机械（`fade_slots` 过渡带 + `jitter_bp`）。
- **两条提醒落实**：① 快层 `daypart` **退让**（与 `_base_activity`/`planner`/`SCHEDULE_PLANNED` 重叠，新造=第二真源）——只经既有路径偏置；② `jitter_bp` **仅由 seed 派生、确定性可重建**（防 `restore`/续跑分叉，同 `T298` 型）。**优先级：中层（周末节日）先做扎实**。
- **⭐ 视图关系**：**同一 `world_params()` 派生视图**（仅新增发射方=日历）；**第一实现**；"纯时间项"第二实现**被否决**（违保底 a）。
- **三保底**：走同一事件契约，**天然满足**。
- **08**：R1–R7（**不新增事件类型**；**`abundance` 新增 kind ✅ 已批**（14→15）、+`source`/`schedule` 字段、扩 §5.11 映射表、新 config 键 + 重冻声明）。
- **⭐⭐ 可感度**：闸 A 行为族 delta（幅度+方向一致+**持续性≥70% slot**）+ 闸 B 画面像素（ΔRGB≥5% **每帧成立** + 人眼佐证）；**必须区分"持续/动态"与"恒定偏移(底色)"并写进证据**；闸 B **前置=前端声明可见通道 R**（未声明前降级为闸 A + 首帧对比，**不许拿"调美术"替代门禁**）；用**日历-only 对照**证"持续≠偶发"。
- **epoch**：**能赶进 `T355`** 仅在**两条同时成立**时——① **不新增独立消融轴**（常驻源在 `propagate` 之下，仍 2×2）；② **`T355` 起跑前**完成 **08 登记 + 实现 + 前端通道声明**。**任一条不成立 ⇒ 独立 epoch（如实多冻一次）；不为省重冻抢工**。
- **Leader 裁定状态**：①②③④（及 `abundance`）**已批/已采纳**；产物**未标 completed**（留实现前再对一次）。


---

*（T365 设计 + 登记清单完 — narrative-designer。只读设计，未改 `code/`；产物交 Leader，不自标 completed。）*
