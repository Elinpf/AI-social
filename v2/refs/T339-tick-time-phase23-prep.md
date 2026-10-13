# T339 · D11 期②/③ 实施准备（只读设计）—— 分期计划 + 08 前置 + **T300 先后裁定建议**

> 作者：仿真引擎与统计架构师（sim-engine-stats-architect）｜ 任务：T339（只读设计，**不动码**）
> 绑 sha：`20573ef` ｜ 上游：`v2/refs/tick-internal-time-design.md`（D11 路径 B）、`v1.1/08-engine-stats-extension.md §5.10`（期①已登记）
> 状态标签：**【事实】**=有证据；**【建议】**=设计主张；**【待定】**=交 Leader/kernel/life。
> ⚠️ 本文件**只读**（`code/**` 一律未碰）；结论落 `v2/refs/`。

---

## 0. 现状（【事实】）

- **期①（`T287`）已 completed**：`span{start_round,start_sub,end_round,end_sub}`（可选、None=瞬时）+ 纯函数 `derive_order`（语义序 `(start_μt, actor, seq)`）+ `time_model`/`time_U` 版本戳（`WORLD_INIT` 总写、`TURN_SEAL` 仅 on）；**默认 off、行为不变**（off 对照内容差异 0/1635、`state_hash` 相等）。口径在 **08 §5.10**。
- **期②/③ 未实现**（仅设计 §5 一句话）。
- 开关簇：`config/time.json`（`time.interval.enabled`/`U` 默认 6；`time.ongoing.enabled`/`time.interleave.enabled` 默认 off），**已入 `FINGERPRINT_FILES`**。

---

## 1. 期②/③ 拆分与顺序（【建议】；每期=可独立交付）

> 顺序：**② 先、③ 后**（D11「B 包含 A」——先立"进行中"，再上"交错/先后"）。

### 期② —— 进行中可感知（ongoing）

| 项 | 内容 |
|---|---|
| **可独立成果** | ① `PLACE_ARRIVED` 按 `topology.travel_ticks` **延后**（移动成"有过程"）；② `WorldView` 暴露 `current_activity`（self）+ 同场所他人"进行中"活动（按 `PERCEPTION_SCOPE` 过滤）；③ `ACTIVITY_INTERRUPTED` **可达**（现 0 次）。 |
| **最小切片** | **先做 ②（`WorldView.current_activity` 暴露）**——纯**派生视图**、不新增真相源；`PLACE_ARRIVED` 延后为次（动调度）。 |
| **验收** | 关 `time.ongoing.enabled` ⇒ **回原子**（与期①/现状一致）；开 ⇒ `current_activity` 可从日志重建（`ACTIVITY_STARTED` 无 `COMPLETED` 且与当前 μt 相交）；`ACTIVITY_INTERRUPTED>0` 在压力场景可达。 |
| **代价** | **`state_hash`：变**（行为层：移动时长/中断改变活动态）；**日志**：`ACTIVITY_*`/`PLACE_*` 带 `span`（~+几十 B/事件）；**回放**：折叠天然（区间是字段）；**续跑**：进行中=可重建派生，随段/索引恢复；**token**：日程因移动时长位移，**调用点或移位**（【未验证】）。 |

### 期③ —— 交错 / 先后（interleave）

| 项 | 内容 |
|---|---|
| **可独立成果** | ① 跨 agent 交错（不同 agent 区间可重叠、互不影响，除非共享资源：同场所容量/市场撮合）；② **对话延续**：`MSG_*` 加 `thread_id`/`reply_to`（可选字段）+ 排序按 `μt`；③ 跨回合谈判可判定（`reply.start_μt ≥ original.end_μt`，或 `≥ start`【待定】）。 |
| **最小切片** | **先做 `MSG_*` 的 `thread_id`/`reply_to` 可选字段 + 排序按 `μt`**（对话线程）；跨 agent 交错结算为次。 |
| **验收** | 关 `time.interleave.enabled` ⇒ 回期②/①；开 ⇒ 同 tick 内多 agent 区间可交错且**结果确定**（`derive_order` 全序）；对话"回应在发起之后"可判定。 |
| **代价** | **`state_hash`：变**（顺序/切片改变结局）；**日志**：`MSG_*` + 线程字段（~+几 B）；**回放**：折叠天然；**续跑**：线程/区间随事件保存；**token**：多回合谈判**可能增 LLM 调用**（【未验证】）。 |

---

## 2. 08 前置清单（我负责登记；**登记先于实现**）

| # | 项 | 内容 | 落点 |
|---|---|---|---|
| P1 | **schema 起止字段** | `span{start_round,start_sub,end_round,end_sub}`（**期①已登记**；期②③沿用，**不新增类型**） | §5.10 |
| P2 | **`current_activity` 派生视图** | 声明为**可重建派生**（不入 `state_hash`、不入事件语义）；**若需"进度事件"→ 优先扩 `ACTIVITY_*` 加性字段**（不新增类型） | §5.10 + §5.9 口径 |
| P3 | **可见性 / 优先级** | ① 进行中活动按 `PERCEPTION_SCOPE`（`place_local`）可见；② **同一 agent 独占动作（移动/劳作）区间重叠 ⇒ `INTENT_REJECTED{reason:"exclusive_overlap"}`**（期①已登记）；③ 共享资源（同场所容量/撮合）按既有规则 | §5.10 + `perception_scope.json` |
| P4 | **仲裁重叠 / 先后判定口径** | ① 排序键 `(start_μt, actor, seq)`（期①已登记）；② **逐回合切片结算定界**：纯函数可推导⇒无需事件；含独立事实⇒须发事件/扩 `ACTIVITY_*`（期①已登记）；③ **期③ 新增**：`reply.start_μt ≥ original.end_μt`（先后/因果，【待定】具体 `≥end` vs `≥start`） | §5.10 |
| P5 | **线程字段** | `MSG_*` 加**可选** `thread_id`/`reply_to`（只增不改、不新增类型） | §1.2 E（沟通） |
| P6 | **开关 + 版本戳** | `time.ongoing.enabled`/`time.interleave.enabled`（**已登记**默认 off）；`WORLD_INIT`/`TURN_SEAL` 戳（期①已登记） | §5.10 |

> **本清单里 P3③/P4③/P5 是新登记**（期②③增量）；P1/P2/P4①②/P6 期①已登，实现时复核即可。

---

## 3. ⭐ 与 `T300` 重冻的先后建议（本文重点）

**前提（【事实】）**：期②/③ 是 **【行为变】**（改 `state_hash`/日志/回放）⇒ **一旦落地就当场作废刚冻好的基线**；期① 是**【仅指纹变、行为不变】**（默认 off）。T300 是**今晚例行重冻**（已叠 `T323`/`T332` 等变因）。

### 方案对比

| 方案 | 做法 | 代价 | 收益 |
|---|---|---|---|
| **(甲) 先冻再改** | **今晚照常重冻**（含期①/T323/T332…）；**期②/③ 列入"B 后·下一轮变更清单首项"**，落地时**再冻一次** | **2 次重冻**（本次 + 期②③落地）；2 次 cache 全 miss | 今晚起**有可用基线**；期②③落地"当场作废→再冻"本就是行为变的**必要代价**，非额外 |
| **(乙) 等期②/③ 落定再冻** | **`T300` 推后**到 期②/③ 落定后**一次冻** | **1 次重冻** | 只冻一次；但**在期②③落定前，跨多个夜跑无"含期①的干净基线"**；且 T300 推迟会与 T323/T332 等**待冻项堆积**、风险后移 |

### 【建议】= **甲为主，设触发条件**

- **默认取 (甲)**：**今晚照常重冻**。理由：① 期②/③ **未排期/未放行**（实现非今夜，需 Leader 放行），若为其推后 T300 ⇒ **长期无基线**；② 期①**默认 off**、先冻成本低；③ 期②③落地"作废→再冻"是**行为变的内在代价**（迟早要付）。
- **例外转 (乙)**：**若期②/③ 能在【本轮冻结信号前】落定并放行 ⇒ 合并为一次冻（乙）**，避免"冻完即废"。
- **即按"能否在冻结信号前落定"门控**——与 obs「**没落定不开跑**」、T320/T332 的"生效时点=实现落地"**同构**。

> **给 Leader 的一句话**：**今晚照常重冻（甲）**；把 **期②/③ 列为"B 后·下一轮变更清单首项"**；若你决定**在本轮冻结信号前**让期②/③落定，则转乙（合并一次）。

---

## 4. 分界线（B 前 / B 后）的落地形式（【建议】）

- **版本戳**：`time_model ∈ {"atomic"(B 前/B 后·①off), "interval-U<U>"(②③ on)}` + `time_U`；**`WORLD_INIT` 总是写**（期①已登记）、`TURN_SEAL` 仅 on。
- **既有基线**标 **`atomic`**（A 前/B 前）；**跨分界线的 run 不得混入同一曲线**；**消融对照必须同一 `time_model` 内**。
- **落地点**：① **obs 的 golden baseline 元数据加 `time_model` 字段**（重冻**分两套**）——建议 obs 在 `golden_baseline.json`/报告里带该字段；② 报告/曲线按 `time_model` 分组。
- 与 T236（重冻）/T281（`segment.enabled`）**同族**：每次动语义/结构 ⇒ **一个可识别的"版本戳"**。

---

## 5. 冲突 / 依赖清单（【事实】+【建议】）

| 编号 | 冲突/依赖 | 说明 | 处置建议 |
|---|---|---|---|
| **C1** | **期② × `T333`（emotion criterion）** | **同文件 `life/agent.py`**（期②暴露 `current_activity`；T333 改 `_reflection_drift_events` 判据） | **串行**（谁先落谁不碰对方区块；或按 Leader 顺序） |
| **C2** | **期②/③ × `T338`（`KernelPort.round_events` 端口）** | 期②③的排序/线程可能需要"按回合取事件"；`round_events` 已在 `life/ports.py` 声明 | **对齐端口**：期③排序优先复用 `round_events`（勿再自取）；**同文件 `life/ports.py` 需串行** |
| **C3** | **期② × 移动/调度（`life/agent._act` / orchestration `_do_move` / `topology.travel_ticks`）** | `PLACE_ARRIVED` 延后动"移动"语义 | 独立于 T333/T338；**但与"行动瞬间化"T283 结论同源**，须一并核 |
| **C4** | **期③ × `MSG_*`/对话（`life/agent.py` 对话 + `engine/events.py`）** | 加 `thread_id`/`reply_to` 需动 `MSG_*` schema（可选字段） | **登记先于实现**（P5）；与 T333 同文件→C1 同型串行 |
| **C5** | **期① 已登** | 期②③若改 §5.10 的排序/切片口径，须**只增/澄清、不推翻期①** | 我登记时守 X1 |

---

## 6. 结论速览

- **分期**：② ongoing（先 `WorldView.current_activity`、后移动时长）→ ③ interleave（先 `MSG_*` 线程、后跨 agent 交错）；各带独立开关、默认 off、可回退。
- **08 前置**：P1–P6（P3③/P4③/P5 为新增登记）。
- **⭐T300**：**建议（甲）今晚照常重冻**，期②/③ 列"下一轮变更清单首项"；**若能在冻结信号前落定则转（乙）合并一次**。
- **分界线**：`time_model` 戳（`WORLD_INIT` 总写）；既有基线标 `atomic`；obs 基线元数据加 `time_model`、重冻分两套。
- **冲突**：C1（`life/agent.py` × T333）、C2（`life/ports.py` × T338）、C4（`MSG_*` × T333 同型）→ **串行**；C3 独立。

---

*（T339 只读设计完，绑 sha `20573ef`；未碰任何 `code/**`。交 Leader 裁决 T300 先后，交 kernel/life 实施期②③。）*

---

## 7. 期②开工前对口清单（串行冲突处置；Leader 采纳「甲」后追加，2026-10-13）

**放行条件（Leader 三条全满足才放行；预计明天白天相位）**：① 08 登记 **P3③/P4③/P5** 落地（**P5 已补**，见 08 §1.2 F；P3③/P4③ 期①已登 08 §5.10）；② 串行冲突解除；③ **T300 重冻完成**（分界线已立：既有基线标 `atomic`）。

**开工前逐条核（对口清单）**：
- **C1 期② × `T333`（同 `life/agent.py`）**：期②改 `WorldView.current_activity` 暴露；T333 改 `_reflection_drift_events` 判据。→ **串行**：等 T333 落定（合并后）再动期②；或**区块互斥**（不同函数、行不重叠）。开工前向 **life-layer-dev** 确认 T333 提交 sha + 无未合并改动。
- **C2 期②/③ × `T338`（同 `life/ports.py`）**：期③ 排序/线程**优先复用 `KernelPort.round_events`**（勿自取）；→ **同文件串行**。开工前确认 T338 落地 sha。
- **C4 期③ × `T333`（`life/agent.py` 对话发射侧）**：`MSG_*` 线程字段发射在 `life/agent.py` → **同 C1 串行**。
- **C3 期② × 移动/调度**：独立文件（`_act`/`_do_move`/`topology`），但与 **T283「行动瞬间化」**结论同源 → 开工前核一致，勿重复/矛盾。
- **建议前置顺序**：`T325`(freeze 装置) 收口 → **`T300` 重冻**（立分界线 `atomic`）→ 解 **C1/C2**（T333/T338 落定）→ **期②** → **期③**。

> **本清单为「期②开工前」的门控；仅登记/协调，不含实现。**
