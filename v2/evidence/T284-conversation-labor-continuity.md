# T284 —— 只读诊断：一个 tick 内是否只有瞬时快照 / 对话与劳作能否"延续"

- **只读**：未改任何代码（`code/{engine,life,freeze,config,obs,contracts,orchestration}` 均未动）。
- **证据日志**：`v2/evidence/run_p1_final_n20_llm.jsonl`（canonical N=20 真 LLM 单周日志，84 回合）。
  ⚠️ 该日志日期 **2026-10-10**，早于 T244/T265；**"对话频次"类数字**可能随近期改动变化（见"不确定"）。**事件 schema / 机制类结论**（本任务主旨）不受影响。
- 分析方式：纯文件解析统计（无仿真、轻负载，未开重分析）。

---

## 问一：对话能不能"延续"？—— **不能（当前无任何会话对象/回复链接）**

**证据（日志统计）**：
- `MSG_DM` 共 **164** 条，散在 **20/84** 回合（max 15/回合）；payload **只有** `from/to/body/msg_id/refs/tag_hints`，**无 `thread_id`/`reply_to`/`in_reply_to`/会话 id**。
- **有"对方后来回一条"的定向 DM：仅 33/164**，且**多数相隔很远**（如 P004→P013 第0回合、回信在第 **63** 回合）→ 属**巧合**而非应答。
- 同一对 agent 的**最大往复链长 = 3**（仅少数几对）。
- **谈判也非多回合**：20 个 `offer_id` 全部在同一条事件回合内走完 `CREATED→COUNTERED/REJECTED`（如 `O-6-*` rounds=`[6]`）——payload 里的 `round_no` 是**要约内部步号**，不是世界回合。
- **机制佐证**（读码）：`life/agent.py::_communicate` 的伙伴来自**当 slot 计划模板**的 participants，**每 slot 独立、无"未结束对话"态**，**没有回复目标** ←结构上没有延续的载体。

> **一句结论**：`MSG_DM` 是**孤立事件**；**不存在跨回合的会话对象**；谈判也不是多回合对话实例（它同样在**一个 tick 内**完成）。**当前没有任何"多回合对话"实例。**

## 问二：劳作的过程在日志里存在吗？—— **只有两个端点，过程中间无事件**

**证据**：
- `ACTIVITY_COMPLETED.duration_ticks` 分布 = **{3: 540}**（**恒为 3**）；`completed_round − start_tick` 分布 = **{3: 540}**。
  ⇒ 活动**确实跨 3 个回合**，但**日志里只有 `ACTIVITY_STARTED` 与 `ACTIVITY_COMPLETED` 两个端点**，**没有任何"进行中"事件**（无 progress/ongoing 类型）。
- **`ACTIVITY_INTERRUPTED` = 0**（机制存在，**真实日志里从未发生**）。
- `PLACE_MOVE`=511 / `PLACE_ARRIVED`=511，`travel_ticks` **恒 1**，但 **`arrived_round − move_round` 恒 0** ⇒ **移动消耗 0 回合**（`travel_ticks` 字段存在但**不参与回合调度**；与 T283 一致）。
- **`WorldView` 无 `current_activity` 字段**（`life/ports.py`：仅 `status/location/...`）⇒ **"进行中的劳作"不可被 self/他人经 `perceive()` 看到**，只能从两个端点事件推断。

> **一句结论**：**"过程"在世界**（引擎 `current_activity` 状态里）**存在，但在日志里只剩"起/止"两端点**；`ACTIVITY_INTERRUPTED` 从不发生；移动名义有时长、实则 0 回合。**同一 tick 内仍是瞬时快照**——因为**没有任何事件能表达"跨回合进行中"**。

---

## 分类表：哪些事件带"时长"

| 事件 | 带时长？ | 字段 / 实况 |
|---|---|---|
| `ACTIVITY_COMPLETED` | ✅ **唯一** | `duration_ticks`（**恒 3**） |
| `ACTIVITY_STARTED` | ⚠️ 只带起点 | `start_tick`，**无 duration** |
| `ACTIVITY_INTERRUPTED` | — | **日志 0 次** |
| `PLACE_MOVE` | ⚠️ 名义 | `travel_ticks=1`，但 `PLACE_ARRIVED` **同回合** ⇒ **不生效** |
| `PLACE_ARRIVED` | ❌ | 无 |
| `MSG_DM / MSG_PUBLIC / MSG_GROUP` | ❌ | 无时长、**无线程、无 reply_to** |
| `MARKET_TRADE / TRANSFER / DEPOSIT` | ❌ | 瞬时、无时长 |
| `OFFER_CREATED/COUNTERED/ACCEPTED/REJECTED` | ❌ | 有 `round_no`(要约步号)，**事件同回合** |
| `RELATION_CHANGE / RELATION_ENCOUNTER` | ❌ | 无 |
| `NEED_UPDATE / GOAL_* / SCHEDULE_*` | ❌ | 无 |
| `MEMORY_WRITE / OBSERVATION / LLM_CALL` | ❌ | 无（审计/认知，非世界动作） |

---

## 最小需求清单（**只列需求，不设计、不实施**）

**要让"对话"可延续，最少需要**：
1. `MSG_*` 带上**会话/回复链接**（如 `thread_id` 与 `reply_to`）——否则无从判断谁在接谁。
2. agent 侧持有**"未结束对话"态**，使"回复同一伙伴"成为可能（**现完全不存在**）。
3. 允许**一次对话跨多回合**（现 `_communicate` 每 slot ≤1 且伙伴独立重选）。
4. **谈判链要能跨回合**（现 create/counter/reject 全在一个 tick 内）。
5. 一个**时间线语义**：让"回应在发起之后"在事件序上**可判定**（现同回合多事件不表达先后）。

**要让"劳作"可延续，最少需要**：
1. **"进行中"表示且可感知**：`WorldView` 暴露 `current_activity`（现无），或增补**进行中事件**。
2. **时长可变**（现 `duration_ticks` 恒 3）。
3. `ACTIVITY_INTERRUPTED` **真的会发生**（现 0 次；机制存在但无触发条件）。
4. **移动真消耗回合**（`travel_ticks` 参与调度；现 `PLACE_ARRIVED` 同回合）。

**触及用户"根问题"的（需用户拍板，不由我定）**：
- tick 语义是否要支持**一次动作跨多 round**，或事件**显式携带 [start,end]**；
- 一个 tick 内多事件**是否需要表达先后顺序**（现"一瞬"）。

---

## 不确定（如实标注）
1. **20 个"started 无 completed"**（560 vs 540）：疑为**日志末尾边界**（末段活动未跑完），**未验证**。
2. **日志时效**：本次数字来自 **10-10 旧日志**，**早于 T244/T265/T268**；**"对话频次/链长"可能已变**，**未在最新 HEAD 复测**（今晚冻结，未开重跑）。**schema/机制结论不受影响**。
3. **引擎 `current_activity` 是否在别处被非事件方式消费**：**未验证**（本次仅确认 `WorldView` 不含它）。
4. 应答统计用的是"后续存在反向 DM"的**弱判据**（无 `reply_to` 可用），**可能高估**真实"应答"。
