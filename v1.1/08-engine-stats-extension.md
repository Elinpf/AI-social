# 08 · 确定性引擎与统计程序扩展（生活层 + 涌现观测层）v1.1

> **【Fork B 时效标注 · 2026-10-12】** 凡本文（X5 / §5.3 / §5.4 / §6）以「同日志逐位一致 / `metrics()` 两次字节相等」作**验收口径**处，按 Leader Q-12.1 修正为「**放开"必须可复现"、保留"可被复算"**」：`replay` 确定性保留，「字节相等」**降为诊断**。**单一口径见 `v2/refs/gate-grading.md`。**

> 作者：仿真引擎与统计架构师（sim-engine-stats-architect）
> 状态：v1.1 设计草案（在 v1 `03-engine-stats.md` 基础上扩展，供 Leader 汇总）
> 设计基准（2026-10-09 用户拍板）：**先做「模拟周」时间尺度**（§3.1 回合→时段→日→周定稿）；**单一小镇场景**（§3.3，不做多场景派生）；总体架构以 `00-architecture.md`（T12）为对齐基准，未落盘前按本文默认推进、差异记 §7 XT-4。
> 基线：`social-experiment/v1/03-engine-stats.md`（v1）
> 上游依据：`social-experiment/research/town-life-brief.md`（M1–M8 模块清单与 v1.1 定位）

本文件把 v1 确定性引擎与统计程序**扩展**到 v1.1 的「人格生活层（M1/M2/M3/M4/M5/M7）」与「涌现观测层（M8）」，**不推翻 v1 任何契约**。三条铁律继续成立：

- **C1**：世界引擎 / 裁决器是确定性代码，绝不是 LLM。
- **C2**：事件驱动 + 分层决策；LLM 只产出内容，裁决器才产出事实。
- **C3**：统计只读日志、纯函数、逐位一致；**新增指标同样不依赖 LLM 判断**。

新增一条**贯穿约束 C4**（延续 v1 的复现铁律，生活层特有）：**凡「决策/检索/判定」类输出（计划、对话文本、记忆检索命中、反思生成、规范采纳与否）一律以事件形式落日志；统计与重放只折叠日志，绝不重新调用 LLM 或重算嵌入**。

术语沿用 v1：回合（round）/ tick、事件（event）、hook、Delta、mu（1 CR=100 mu）、哈希链日志。

---

## 0. 与 v1 的兼容总原则（已定）

| 编号 | 原则 | 说明 |
|---|---|---|
| X1 | **v1 事件表只增不改** | v1 §2.3 全部事件类型及其 payload 字段**不得修改语义**；新增类型另起一节（§1）。 |
| X2 | **hook 链 4.1–4.8 顺序冻结** | v1 `ARBITRATE` 内 4.1–4.8 的**相对顺序与语义不可变**；生活层以**新阶段 3.5**（§2）挂载，不插入 4.x 内部。 |
| X3 | **指标口径分离** | v1 经济/生命周期指标（`metrics.*`）口径**冻结**；新增指标放入**独立命名空间** `metrics.life.*` 与 `metrics.emergence.*`（§4）。 |
| X4 | **日志向后兼容** | 新增事件沿用 v1 同款外壳（`seq/round/phase/actor/type/payload/mono_ts/prev_hash/hash`），仅扩充 `type` 取值与 `payload` 字段；v1 工具可忽略未知类型（但重放器遇到未知类型必须报错，见 §6）。 |
| X5 | **重放语义统一（对齐 AR-C9）** | 重放仍是 `fold(apply_event)`（v1 §6.2），新增事件登记进同一 `apply_event` 分派表。**可复现口径 = 「同日志逐位一致」**：首跑含 LLM 判定（不保证跨跑一致），但 `replay(log)` 对**同一日志**逐位一致、`metrics()` 两次字节相等。 |
| X6 | **LLM 输出即事件** | 任何 LLM 生成物在进入世界前，必须被裁决器封装为带完整 `payload` 的事件（C4）；统计层永不触发 LLM。 |

---

## 1. 事件类型扩展（覆盖要求 1）

### 1.1 事件外壳（已定，沿用 v1）

```python
class Event:
    seq: int          # 全局单调递增（与 v1 共用同一计数器）
    round: Round      # 底层 tick
    phase: int        # 0..6 及新增 3.5（见 §2 编码约定）
    actor: AgentId | "SYSTEM" | "OBSERVER"
    type: str         # 见 §1.2 新增；v1 类型不变
    payload: dict     # 结构化；字段见 §1.2
    mono_ts: int      # 逻辑时间 = round * TIME_UNIT + phase_seq（非墙钟）
    prev_hash: str
    hash: str
```

生活层事件在 `payload` 中**额外必带**三个审计字段（满足「必带 timestamp/round/actor」要求）：
`day`（派生日号）、`slot`（时段）、`day_type`（workday/weekend）、`place`（发生时场所，可为 `null`）。这些由 §3 的时间结构确定性派生（§3.1 `derive_time`），便于按时段/日/周切片统计。

> **待讨论 XT-1**：`mono_ts` 的 `TIME_UNIT` 取值（见 §3 D7-1）。默认 `TIME_UNIT=1000`，保证同回合内相位有序。

### 1.2 新增事件类型表（已定 schema，供 persona / emergence 层填入内容）

**A. 时间与场所（M5）**

| type | phase | payload 关键字段 | 说明 |
|---|---|---|---|
| `TIME_MARK` | 3.5 | `round, week, day, slot` | 日/周边界锚点（每跨日/跨周各一条），供审计对齐 |
| `PLACE_MOVE` | 3.5 | `agent_id, from_place, to_place, travel_ticks, day, slot` | 场所移动 |
| `PLACE_ARRIVED` | 3.5 | `agent_id, place, day, slot` | 到达（可并入 MOVE，v1.1 默认保留独立以利统计） |

**B. 日程与活动（M4）**

| type | phase | payload 关键字段 | 说明 |
|---|---|---|---|
| `SCHEDULE_PLANNED` | 2 | `agent_id, horizon("day"|"week"), slots:[{slot_id, activity_type, place, priority, planned_tick}]` | 计划生成（LLM 产内容，裁决器封装） |
| `SCHEDULE_REVISED` | 2/3.5 | `agent_id, slot_id, reason, delta` | 计划调整 |
| `ACTIVITY_STARTED` | 3.5 | `activity_id, agent_id, activity_type, place, slot_id, start_tick, participants[AgentId]` | 活动开始（可为单人/多人） |
| `ACTIVITY_COMPLETED` | 3.5 | `activity_id, agent_id, outcome("done"|"failed"), duration_ticks, resource_intents[...]` | 活动结算（经济后果以 intent 交 4.x 结算，见 §2） |
| `ACTIVITY_INTERRUPTED` | 3.5 | `activity_id, agent_id, reason` | 中断 |

**C. 需求与目标（M7）**

| type | phase | payload 关键字段 | 说明 |
|---|---|---|---|
| `NEED_UPDATE` | 3.5 | `agent_id, dim, before, after, cause` | 需求/满足度变化（dim 由 persona 层定义，如 hunger/social/esteem/energy） |
| `GOAL_SET` | 2 | `goal_id, agent_id, kind, description_ref` | 目标设定 |
| `GOAL_PROGRESS` | 3.5 | `goal_id, agent_id, before, after` | 目标进度 |
| `GOAL_ACHIEVED` | 3.5 | `goal_id, agent_id, reward_intents[...]` | 目标达成 |
| `GOAL_ABANDON` | 3.5 | `goal_id, agent_id, reason, progress_at_abandon` | 目标放弃（**独立事件**，应 T17 裁决；可观测福祉信号） |

> **产生者/钩子（应 T17 裁决补全，已定）**：
> - `GOAL_ACHIEVED`：**确定性达成钩子**——Phase 3.5 **L4 `apply_needs`**（或 L3 末）中，目标 `target_metric`/`progress` 达 `≥ 1.0`（或达 `deadline` 内完成条件）时，由确定性规则落 `GOAL_ACHIEVED`；`reward_intents[]` 交 4.x。
> - `GOAL_ABANDON`：**确定性放弃钩子**——触发（T8 裁决 T231 **写死**）：**周 REVIEW 时 `status=active` 且本周窗口 `progress` 增量 `== 0`** → `GOAL_ABANDON{reason:"stalled"}`；`deadline`（`deadline_week` 过期未达成）/`voluntary`（Agent 主动 `INTENT`，经校验）保持**已定义但暂不启用**；`reason ∈ {deadline, stalled, superseded, voluntary}`。**不得为凑事件强发或改 `progress`**；某窗口无停滞目标则 **0 事件**（允许空）。
> - `GOAL_PROGRESS`：由活动/技能/经济事件**确定性推导**（progress = f(相关技能提升/资源/活动计数)）。

**D. 关系（M3）**

| type | phase | payload 关键字段 | 说明 |
|---|---|---|---|
| `RELATION_CHANGE` | 3.5 | `from, to, dim("affinity"|"trust"|"respect"), before, after, cause, cause_event_seq` | 关系维度变化（Agent 视角有向） |
| `RELATION_ENCOUNTER` | 3.5 | `a, b, place, day, slot, duration_ticks` | 共处/相遇（可由 PLACE_MOVE 派生，此处**记录首次共处超阈事件**以省算量） |

**E. 记忆（M2，遵循 Smallville 记忆流 + Agentopia 文件式）**

| type | phase | payload 关键字段 | 说明 |
|---|---|---|---|
| `MEMORY_WRITE` | 3.5 | `mem_id, agent_id, kind("observation"|"plan"|"reflection"|"chat"), importance(int 0..10), day, slot, subject(可选), body_ref, embed_ref, source_event_seq` | 记忆写入（append-only）。`body_ref`/`embed_ref` 指向侧存储（§5.4） |
| `MEMORY_RETRIEVE` | 2 | `agent_id, query_id, top_k, selected_mem_ids[], scores[], weights{recency,importance,relevance}, tie_order` + **可选诊断字段**：`vec_available:bool`、`retrieval_mode∈{vector,lexical,recomputed}` | 检索命中（**决策结果落日志**，重放不再算嵌入，C4）。**T228**：side `.vec` 可关时检索降级须**显式可见**（不静默）——`vec_available`=本次是否用上向量，`retrieval_mode`=诊断/降级模式（可选） |
| `MEMORY_REFLECT` | 3.5 | `agent_id, triggered_by_mem_ids[], importance_sum, produced_mem_id` | 反思触发（累积重要性超阈）与产物 |

**F. 传播与观测（M6/M8，涌现核心）**

| type | phase | payload 关键字段 | 说明 |
|---|---|---|---|
| `OBSERVATION` | 3.5 | `observer, target_event_seq, salience, day, slot` | Agent 观测到某事件（**传播图的边锚点**） |
| `SEED_EVENT` | 3.5 | `seed_id, kind, injected_by("OBSERVER"), payload` | 观测者注入的种子事件（Smallville「派对」范式） |
| `TAG_EMITTED` | 3.5 | `agent_id, tag, valence(-1|0|1), source_msg_id` | 标签/观点发射（标签频次与演化统计的原子） |
| `ROLE_CHANGE` | 3.5 | `agent_id, from_role, to_role, cause, day` | 职业/身份转变 |
| `NORM_PROPOSED` | 3.5 | `norm_id, proposer, rule_ref, support_count, threshold` | 规范提案（判定用**确定性阈值**，非 LLM） |
| `NORM_ADOPTED` | 3.5 | `norm_id, adopters[], adopted_day, threshold_used` | 规范被采纳（支持者 ≥ 阈值即采纳，纯规则判定） |
| `NORM_VIOLATED` | 3.5 | `norm_id, violator, day, severity` | 规范违反（**确定性产生**，见下） |

> **`NORM_VIOLATED` 产生者/钩子（应 T17 裁决补全，已定）**：由**确定性规则检测**，落在 **Phase 3.5 L7 `emit_tags`**（规范层）为主、**Phase 4.5 `apply_penalty`** 为辅：
> - **触发条件**：Agent 的行为事件（`MSG_*`/`ACTIVITY_*`/`TRANSFER` 等）匹配某条**已采纳规范** `rule_ref` 的违规谓词（`predicate` 为确定性可判表达式），且该 Agent 属规范作用域 `scope`；
> - **判定**：纯确定性（规则匹配 + 阈值），**非 LLM**；
> - **后果**：`severity` 由规则给出；惩罚由 4.5 `apply_penalty` 执行（与 v1 惩罚机制衔接），并落 `NORM_VIOLATED` 供统计 `norm_violation_rate`（T9 D 类）。

> **R5 · `OBSERVATION` 语义澄清（应 03-pov-visibility-check §R5 / NT-C3，已登记）**：`OBSERVATION` = **显著感知样本（salience 门控子集）**，**不是「Agent 所见一切」的可见性全集**。「角色视角（POV）」的可见性判据以**确定性推导的 `visible_events(agent)`** 为准（由 `PLACE_MOVE/ARRIVED` 占用时间线 + `PERCEPTION_SCOPE` 配置表 + 事件 `place` 确定性重算），`OBSERVATION` 降级为**显著度/注意力证据**。**不改变 `OBSERVATION` 现有 schema 与传播口径**（不碰 T9 §2.2 传播图）。
> **R4 · `MSG_*` 的 `refs[]` 约束（应 §R4，已登记）**：**转发 / 转述类**消息**必须**携带 `refs[]`（指向被转述的 `msg_id` 或事实 `event_seq`）；无法确定来源者 `refs=[]` → POV 渲染标 `spec=true`、表述为「听说（未经核实）」，**不进入「亲历」集**（`heard_events`，见 §3.5）。

**G. LLM 成本/内容审计（沿用 v1 `LLM_CALL`，扩 `purpose`）**

| type | phase | payload 关键字段 | 说明 |
|---|---|---|---|
| `LLM_CALL`（v1，扩字段） | 2 | v1 字段 + `purpose("plan"|"dialogue"|"reflect"|"decide_t2"|"describe")` | 成本与内容来源审计；**不改账** |

**H. 意图拒绝审计（新增，应 00-architecture §4.2 / AR-C1 回补）**

| type | phase | payload 关键字段 | 说明 |
|---|---|---|---|
| `INTENT_REJECTED` | 3 / 3.5 / 4 | `agent_id, intent_class, reason, requested` | **确定性拒绝**：非法场所 / 超容 / 超配额 / 非营业时段 / 日程不一致 / 余额不足（4.x）。**不产生任何状态变化**，仅审计 |

> **AR-C1 处置**：`INTENT_REJECTED` 登记为本扩展的审计事件（v1 事件表本无此类型）；按 00-architecture §4.2 拒绝路径产生，供统计「意图拒绝率 / 拒绝原因分布」。

**I. 软判定 / 叙事（冻结，应 00-architecture §4.1 / §5.5 / AR-C8 回补）**

用户方案甲（「底座拆分」）：软判定层（LLM 定性社会判断）输出**必须写入日志后冻结**；叙事层纯输出、不改状态。二者均以一等事件落日志：

| type | phase | payload 关键字段 | 说明 |
|---|---|---|---|
| `LLM_JUDGMENT` | 2 | **必带四要素**：`decision`（∈ `envelope.options`）、`model`（判定模型/版本）、`context_digest`（相关上下文摘要哈希）、`frozen=true`；另含 `judgment_id, parties[], dimension, question_ref, envelope, rng_branch, effect_ref` | **冻结的 LLM 定性判定**（E-JUDGE）。`rng_branch` 记录**由 RNG 预先确定的分支**（LLM 不掷骰子）；数值后果另记派生确定性事件（如 `RELATION_CHANGE`），经 `effect_ref` 关联 |
| `NARRATIVE` | 2/6 | `fact_event_seqs[], body_ref, affects_state=false` + **可选元数据**：`narrative_id, style, pov, model, prompt_hash, anchor_digest, spec_flags, degraded` | 叙事层纯输出（E-NARRATE），**不改任何状态**；正文入侧存储。**`apply_event(NARRATIVE)` 恒等折叠**（不产生任何状态变化） |

> **NT-C1（应 17-narrative-layer §NT-C1 登记，已定）**：上表 `NARRATIVE` 的**可选元数据字段**（**只增不改**，不新增事件类型，X1 允许）：
> - `narrative_id`（唯一）、`style ∈ {chronicle, weekly_gazette, character_pov, feature}`、`pov ∈ {omniscient, <agent_id>}`、`model`（审计）、`prompt_hash`、`anchor_digest`（**锚点集指纹，确定性、与 LLM 无关**，对同一 `fact_event_seqs` 逐位一致）、`spec_flags`（推测句计数）、`degraded`（预算降级标记）。
> - **不变量**：`affects_state=false`、`apply_event(NARRATIVE)` 恒等折叠**不变**；多版叙述共享同一 `anchor_digest`（事实/锚点层可复现，叙述层可多版，H-3）。
> - **成本分列**：叙事渲染记 `LLM_CALL(purpose="describe")`（§1.2 G 已含），与判定类 `LLM_CALL` **不冲突、分列**（对齐「成本记 LLM_CALL、判定记 LLM_JUDGMENT」三事件分列原则）。

**接口对应（00 §4.1）**：
- **IF-2b** `submit_judgment(agent_id, judgment_request) -> LLM_JUDGMENT(frozen)`：软判定层唯一出口；**硬内核先校验 `envelope`（合法 `options` / 阈值 / `rng_branch`），通过后才冻结为事件**。
- **IF-6** `get_frozen_judgment(judgment_id) -> decision`：重放/统计**读回已冻结判定，绝不重问 LLM**。
- **IF-7** `narrate(fact_event_seqs) -> text`：叙事层→侧存储，记 `NARRATIVE`（`affects_state=false`）。

**重放语义（硬约束）**：`apply_event(LLM_JUDGMENT)` 仅把 `decision` 写入 `state.judgments[judgment_id]`，**绝不重调 LLM**；数值后果由随后的确定性派生事件（如 `RELATION_CHANGE`）折叠得出，保证图/关系指标可复现。

**三事件分列（已定）**：成本 → `LLM_CALL`；判定 → `LLM_JUDGMENT`；数值后果 → 派生确定性事件（如 `RELATION_CHANGE`）。三者以 `judgment_id` 关联，互不混写。

**J. 技能 / 成长（应 WB-C1 登记，命名与 T14 事件谱系对齐）**

| type | phase | payload 关键字段 | 说明 |
|---|---|---|---|
| `SKILL_PRACTICE` | 3.5 | `agent_id, skill_id, slot_id, place, effort, skill_before` | 技能练习（对应 T14「Skill Practice」模板） |
| `SKILL_LEVEL_UP` | 3.5 | `agent_id, skill_id, level_before, level_after, cause` | 技能提升（**确定性结算**：由 effort/练习次数经固定成长函数推出，非 LLM） |
| `SKILL_OUTPUT` | 3.5 | `agent_id, skill_id, output_ref, quality` | 技能产出物（如作品/工具；`quality` 由确定性规则算，LLM 仅命名/描述） |

> **WB-C1 处置**：`SKILL_*` 供「技能—成长维度」观测。**命名对齐 T14**：T14（12-event-lineage.md）将以本表为 skill 类事件的唯一命名来源，避免重复登记；若 T14 需细分（如 `SKILL_TEACH`），记入 T14 冲突清单并回写本节。

**K. 协商 / 评价 / 冲突事件（应 T14-C1/C2/C5，Leader 批准登记）**

| type | phase | payload 关键字段 | 说明 |
|---|---|---|---|
| `OFFER_CREATED` | 2/3 | `offer_id, from, to[], kind, terms, round_no` | 协商状态机——**发起**（T14-C1） |
| `OFFER_ACCEPTED` | 2/3 | `offer_id, by, terms` | **应约 / 成约** |
| `OFFER_REJECTED` | 2/3 | `offer_id, by, reason` | **社交性婉拒**（与规则性 `INTENT_REJECTED` 区分，见下） |
| `OFFER_COUNTERED` | 2/3 | `offer_id, by, new_terms, round_no` | **还价**（反提案；轮次上限 `N_round`，默认 3） |
| `OFFER_EXPIRED` | 2/3 | `offer_id, round_no` | 协商超限确定性终止 |
| `SCORE_POSTED` | 3.5 | `contest_id, subject, attrs{}, score` | **确定性评分**（§见 T14 §3.1；LLM 不参与） |
| `RANKING_EMITTED` | 3.5 | `contest_id, ranking[{subject, score, rank}]` | **确定性排名**（全序 tie-break） |
| `CONFLICT_STARTED` | 2/3.5 | `conflict_id, parties[], stakes, rule_ref` | 权力冲突——开始（T14-C2） |
| `CONFLICT_RESOLVED` | 3.5 | `conflict_id, winner, power_breakdown{}` | **确定性对抗结算**（§T14 §3.2；LLM 不当裁判） |

> **T14-C5 语义分离（已定）**：`INTENT_REJECTED`（§1.2 H）= **规则性拒绝**（非法场所/超容/超配额/非营业时段等，审计用）；`OFFER_REJECTED` = **社交性婉拒**（合法要约被对方礼貌拒绝）。二者**并存且语义分离**，统计上分别计入「意图拒绝率」与「协商婉拒率」。
> **T14-C4（已裁定·不新增）**：`WELLBEING_ALERT` **不作为事件**；生命周期状态以 `STATE_CHANGE`（含 `exhausted` 等）为唯一事实源；well-being 告警为**观测层派生指标**（由日志重算），不落新事件。
> **T14-C3（交 T11 待讨论）**：`DEPOSIT/WITHDRAW` **暂不新增**；v1 经济以 `LOAN_*`/`TRANSFER` 承载银行行为，若确需再单开。

**L. 银行 / 负债科目事件（应 T14-C3，Leader 2026-10-09 采纳 econ 建议，已登记）**

| type | phase | payload 关键字段 | 说明 |
|---|---|---|---|
| `DEPOSIT` | 4.2 | `agent_id, amount, cash_after, deposit_after` | 存款（主体→银行，负债科目转移） |
| `WITHDRAW` | 4.2 | `agent_id, amount, cash_after, deposit_after` | 取款（银行→主体） |
| `INTEREST_PAID` | 4.2 | `bank, agent_id, amount, deposit_after` | 存款利息（bank→agent），与 `INTEREST_CHARGED`(agent→bank) 成对，方向分明 |

- **语义（已定）**：`DEPOSIT/WITHDRAW` 是「主体↔银行」的负债科目转移，**与 `TRANSFER`（主体↔主体支付）语义不同**，独立登记以免污染基础流速、wash/环路反作弊与 `I_eff` 三处口径（econ 2026-10-09）。
- **不计入基础流速**（并入 v1 `03` §5.6 基础流速的「单列」清单）；**不计入 `I_eff`**（银行/系统项，且存款不改变净值 E）。**`INTEREST_PAID`（bank→agent）与 `INTEREST_CHARGED`（agent→bank）同样不计入 `I_eff`**（属系统项，防止靠吃存款息重置死亡计数/续命，与 02 §5.2 同源）。
- **配套口径（⚠️ 属 v1 遗留开放问题 Q1 范畴，见下）**：银行须为**显式 money holder**，存款不销毁。

**M. 群组生命周期事件（应 03-pov-visibility-check §R3，已登记）**

| type | phase | payload 关键字段 | 说明 |
|---|---|---|---|
| `GROUP_CREATED` | 3.5 | `group_id, members[], created_round` | 群组创建（使 `MSG_GROUP` 可见性可按**时点**重算，S5） |
| `GROUP_JOINED` | 3.5 | `group_id, agent_id, round` | 成员加入（**若成员可变**；若采用「组队不可变」则不需要，见下） |
| `GROUP_LEFT` | 3.5 | `group_id, agent_id, round` | 成员退出（同上，可选） |

- **R3 处置**：新增 `GROUP_CREATED` 为**确定性小型事件**，使群组可见性 `agent ∈ members(group_id, e.round)` 可按时点重算。
- **默认取舍（待讨论）**：小镇规模小、组少——**默认采用「组队不可变」**：仅 `GROUP_CREATED{members[]}` 一次成型，**冻结 members**，不落 `GROUP_JOINED/LEFT`；若后续需要可变成员，再启用二者（只增不改）。
- **R6 复用确认**：`LLM_JUDGMENT.parties`（§1.2 I）可直接作「主体可见（S11）」依据，标 `frozen_llm`，**无需新增**。

**N. 经济事件字段扩展：`MARKET_TRADE.scarcity_index`（应 T60 登记，已定）**

> 背景：体验类语义事件 E9（稀缺交易）在自然运行中不可判——需 `MARKET_TRADE` 携带本地稀缺度。此前 `scarcity_index` 在 v1/08/v1.2 中**均未定义**（econ-dev 正确地未擅自改 schema）。现正式登记（**只增不改**，X1）：

在 `MARKET_TRADE` payload 追加**可选**字段 `scarcity_index`：

| 项 | 定义 |
|---|---|
| **语义** | 本笔成交发生时，**本地该商品的供给/存量相对需求的紧张程度**（确定性指标；**非** LLM 判断） |
| **取值域 / 单位** | **整数 `0–100`**（百分比；`0`=极充裕，`100`=极稀缺），贴合整数 `mu` 体系，**禁浮点** |
| **计算口径（确定性、可重放）** | `scarcity_index = clamp( round100( 1 − min(1, stock_on_hand / demand_window) ) )` 之整数化。<br>· `stock_on_hand` = 该商品在 `market` 的**当前可售存量**（挂单/库存，确定性字段）；<br>· `demand_window` = 近 `W_scarce` 回合（默认 `= 1 时段回合数`，见配置）该商品的**需求量**（订单/消费，确定性）；<br>· `round100(x)` = `min(100, max(0, int(round(x·100))))`。**无外部数据、无随机、无 LLM**。 |
| **阈值** | `theta_scarce`（obs 侧判定阈值，**0–100 同尺度**），默认 **50**。对齐位置：`obs/params.py::EmergenceParams.theta_scarce`（census E9 读取；`15-event-census-spec §2` 引用）。 |
| **缺失语义** | 若成交记录**不含**该字段（旧日志 / 非稀缺商品）→ `scarcity_index` 视为**未知**，obs 判定 **不计** E9（保守，不误报）。 |
| **消费方** | **econ-dev** 在 4.1 `settle_market` 按本 schema 填入（来自挂单/库存与需求窗口的确定性计算）；obs census E9 读取 `≥ theta_scarce` 计命中。 |

> **G7 schema conformance**：`scarcity_index` 为**可选**字段（`obs/atomic.py::REQUIRED_FIELDS` 不强制），故 G7 **不受影响**（额外字段被容忍）。
> **golden baseline**：本变更为**判定阈值/可选字段**，不改变事件类型计数；G6 黄金基线**不受影响**；如后续事件量口径变化，由 **T58** 统一重冻。

**O. v2 商品族事件（A 层价值创造，应 `v2/01-economy-substrate.md` §2.3 / §6.2，已登记）**

> 目的：补 v2「价值创造入口」——生产把劳动/投入转为商品库存，消费/折旧/溢出为出口。**确定性、可审计、无 LLM**。商品守恒：`ΣPRODUCE = ΣCONSUME + Σ库存 + Σ溢出 + Σ折旧耗损`。

| type | phase | payload 关键字段 | 说明 |
|---|---|---|---|
| `PRODUCE` | 4 | `agent_id, good_id, qty, place, recipe, skill_level` | 生产产出入库存（唯一合法价值创造源头）；`recipe`/`skill_level` 决定 `qty`（确定性生产函数） |
| `CONSUME` | 4 | `agent_id, good_id, qty, purpose` | 消费/投入品扣减（`purpose` 例：`eat`/`input`/`feed`） |
| `DEPRECIATE` | 4 | `agent_id, asset_id, delta_mu` | 资产折旧（`delta_mu ≥ 0`；确定性折旧率） |
| `PRODUCE_OVERFLOW` | 4 | `agent_id, good_id, qty_dropped` | 库存超上限溢出丢弃（确定性上限） |

> **登记口径**：字段名以 `v2/01 §2.3` 为准；`good_id` 取值域由 `v2/01 §2.2` 商品模型定义（本文件只固定结构）。新增事件须在 `engine/events.py` 登记并在 `replay.apply_event` 注册确定性折叠器（v2 实现阶段，本任务只登记 schema）。

**O.1 `qty` 单位与定点换算（权威：`engine/hooks/production.py` 模块 docstring，应 T108 如实登记，已定）**

> **单位口径（重要）**：商品族事件的 `qty`（`PRODUCE`/`CONSUME`/`PRODUCE_OVERFLOW` 的 `qty`/`qty_dropped`）**一律为 `milli-unit`（定点整数）**：**`1 unit = 1000 milli-unit`**（`MILLI = 1000`）。**禁浮点**，与金额 `mu` 同为整数体系。

- **`base_rate` 定点值**（千分比，1000 == 1.0）：
  | good_id | `base_milli` | 折算 | `p_ref_mu`（统计计价，非成交价） |
  |---|---|---|---|
  | `food` | 2000 | 2.0 | 100 |
  | `material` | 1000 | 1.0 | 150 |
  | `tool` | 300 | 0.3 | 500 |
  | `service` | 1000 | 1.0 | 200 |
  | `art` | 200 | 0.2 | 1000 |
- **生产函数（确定性）**：`qty = ⌊ base_milli × 技能因子(1000 + 100·lv) × resource_milli × tool_milli / 1000³ ⌋`
  （`resource_milli`/`tool_milli` 均为 milli 定点；整除向下取整，全程整数）。
- **同口径字段**：库存数量、配方上游投入（`RECIPES.inputs` 的 qty_milli）、生存消费（`need_food_milli = 1000`）、折旧 `DEPRECIATE.delta_mu`（= 损失单位数，同 milli 口径）。
- **消费目的**：`CONSUME.purpose ∈ {eat, input}`。

**O.2 库存 `state.inventory` 与事件 `qty` 同单位（应 T108，已定）**

- **结构**：`state.inventory : { owner_id → { good_id → qty:int } }`（`engine/state.py`）——**`qty` 与商品族事件 `qty` 同单位（milli-unit）**，两者可直接比较/相加减。
- **入 `state_hash`**：`inventory` 纳入 `state_hash` 投影，**按 `owner_id` 与 `good_id` 双键 `sorted`** 规范化输出（保证同状态逐位一致、可复现）。
- **被指标消费**：T101 的总产出 `Y`、库存守恒（`ΣPRODUCE = ΣCONSUME + Σ库存 + Σ溢出 + Σ折旧耗损`）直接读该字段；单位口径不一致会导致对不上——故本条为指标口径的前置。

**P. v2 契约族 + 投票（B 制度工具箱，应 `v2/01 §6.2` / `v2/02 §3.5`，已登记）**

> 目的：让「AI 自造制度」的**缔约**与**集体决策**可被确定性托管与审计。契约经济后果仍经 4.1/4.2 结算；`VOTE_CAST` 为可选显式投票（默认用 `NORM_PROPOSED.support_count` 计数）。

| type | phase | payload 关键字段 | 说明 |
|---|---|---|---|
| `CONTRACT_CREATED` | 2/3 | `contract_id, kind, parties[], terms{}, enforceable, rule_ref, created_round` | 契约生效（`OFFER_ACCEPTED` 后进入确定性执行表）。`kind ∈ {EMPLOYMENT, LOAN, TENANCY, PROFIT_SHARE, COOPERATIVE, SERVICE}`；`terms` 为**结构化条款**（确定性可校验） |
| `CONTRACT_FULFILLED` | 3.5/4 | `contract_id, round, by, evidence_ref` | 履约（周期/到期按 `terms` 确定性判定） |
| `CONTRACT_VIOLATED` | 3.5/4 | `contract_id, round, violator, reason, rule_ref` | 违约（确定性判定；可由 `apply_penalty` 追加 `PENALTY_APPLIED`） |
| `CONTRACT_EXPIRED` | 3.5/4 | `contract_id, round` | 到期未续（确定性） |
| `VOTE_CAST` | 3/3.5 | `vote_id, norm_id, agent_id, choice, support_count, day` | 显式投票（可选；`support_count` 为**计票后**计数，纯规则） |

- **`CONTRACT_CREATED.terms` 结构（确定性可校验，字段名以 `v2/02 §3.5.2` 为准）**：
  `{price_mu?, qty?, wage_mu?, period?, principal_mu?, rate_bp?, due_round?, share_bp?, rent_mu?, place?}`（按 `kind` 选用）。
- **`enforceable`**：`True` 时违约可判（走 `CONTRACT_VIOLATED` + 可选惩罚）；`False` 为君子协定（不判违约）。
- **`rule_ref`**：关联规范（如最低工资规范 `norm:town:min_wage:majority`）。
- **边界**：契约/投票均为**工具**，不写死价格/工资/税率（由 AI 协商填）；执行必须确定性、不得绕过守恒。

**Q. v2 字段扩展（复用既有事件，只增字段；应 `v2/02 §4.2/§4.3`，已登记）**

| 事件 | 新增**可选**字段 | 说明 |
|---|---|---|
| `GROUP_CREATED` | `kind ∈ {chat, guild, mutual_aid, cooperative, place}`、`scope_place?` | 组织特化（`v2/02 §3.1`）；`place` 类承载「场所聊」（复用 `members` 可见性） |
| `GROUP_DISSOLVED`（**新增事件**） | `group_id, round, reason` | 组织终结、可审计（`v2/02 §3.2`） |
| `OFFER_CREATED` | `kind ∈ {sale, service, employment, loan, split, tenancy}`、`terms{}`、`enforceable=true`、`rule_ref?` | 承载**可执行契约**（`v2/02 §3.5.2`）；`terms` 结构同上 |
| `NORM_ADOPTED` | `scope ∈ {town, group:{id}, place:{id}}`、`effect{kind ∈ {tax, public_goods, mint, behavior}, rate_bp?, budget_mu?, purpose?, mint_amount_mu?, reason?}` | 让规范产生**经济后果**（`v2/02 §3.5.3`）；`effect` 确定性执行、经济后果仍经 4.3/4.1 |
| `PUBLIC_REACTION`（**新增事件**，最小集仅 `kind="boycott"`） | `reaction_id, agent_id, target{kind ∈ {event,msg,agent}, ref}, kind, topic_tag, day, slot, place` | 抵制（行为性、不可派生）；`gather/discuss/endorse` 优先由日志**派生**，暂不落事件（`v2/02 §2.4`） |

> **最小化原则（v2/02 §4.2）**：优先派生，仅在「行为性且不可派生」时新增事件。所有新增事件必须：① 登记 `engine/events.py::EVENT_TYPES`；② 在 `replay.apply_event` 注册确定性折叠器；③ 带 `day/slot/place` 审计字段。
> **G7 影响**：以上均为**新增类型**或**可选字段**——新增类型在**旧日志中不出现**，G7 对既有日志仍通过；可选字段被容忍，G7 不受影响。**均不与既有 66 类事件冲突**（只增不改）。

**R. v2 交换原语事件（A 层成交通道，应 `v2/04-exchange-and-contracts.md` §6 / T126，已登记）**

> 目的：解 G-P1-1（Agent 间零交易 / 商品→货币转换通道缺失）。**一条成交原语 `apply_exchange` + 两个事件出口**：复用 `MARKET_TRADE`（订单簿，**关键改动：允许 Agent 作卖家**）与**新增 `EXCHANGE_SETTLED`**（议价/契约的多腿双边原子交换）。红线：**不预设价格/工资/税率/铸币；内核不调 LLM**。

| type | phase | payload 关键字段 | 折叠器行为 |
|---|---|---|---|
| `EXCHANGE_SETTLED`（**新增**） | 4.1 | `exchange_id, channel∈{offer,contract}, offer_id?, contract_id?, parties[2], legs{goods:[(from,to,good_id,qty)], money:[(from,to,mu)]}, counterparty?, price_mu?, meta?, place?, activity?, round` | 对 `inventory`/`cash` **逐腿原子应用**；**校验零和**：∀good 净额=0、`Σmoney` 净额=0 |

> `legs` 即多腿双边交换：`legs.goods[]`（商品腿）与 `legs.money[]`（货币腿），等价 `v2/04 §6` 的 `goods_legs`/`money_legs` 记法；`meta` 为可选审计元数据。

- **`MARKET_TRADE` 扩展可选字段 `channel∈{orderbook}`；并显式允许 `seller ∈ Agent`**（关键改动：卖方不再仅世界 `MARKET`；**只增字段、不改语义**，X1；G7 容忍）。
- **`counterparty` 一等字段（Leader 裁决 A1）**：`MARKET_TRADE` 与 `EXCHANGE_SETTLED` 均新增可选字段 `counterparty` = **成交对手方标识**（`AgentId` ⇒ agent↔agent 成交；world 标识 `"WORLD"`/`"MARKET"` ⇒ 与世界成交）。**每笔成交必须能回答「对手方是谁、是否 world」**——服务 G-P1-1 判据与 `exchange.enabled` 消融口径。
- **折叠器**：`EXCHANGE_SETTLED` 与 `market_trade` **共用 `apply_exchange` 内核**（`replay.apply_event` 注册确定性折叠器）。
- **守恒白名单**：`EXCHANGE_SETTLED` 归入**零和事件**（与 `TRANSFER`/`MARKET_TRADE`/`DEPOSIT` 同类，**不计入 MINT/BURN**）——货币式与商品式守恒均适用。
- **契约的账务落点**：契约（`CONTRACT_*`）是**制度层意图/结果**记录，其每一笔付款/交货**物理上仍是** `TRANSFER`/`EXCHANGE_SETTLED`/`MARKET_TRADE`，经同一守恒校验（与 §1.2 P 一致）。
- **意图（登记契约）**：`INTENT.ECON.TRADE` / `INTENT.ECON.OFFER`（意图侧；事件侧 → `OFFER_CREATED`）/ `INTENT.ECON.CONTRACT_SIGN` / `INTENT.ECON.ORDER_CANCEL`（新增，登记 `life/ports.py::ALL_INTENT_CLASSES`）。**撤单必须有事件出口**（`ORDER_CANCEL`），否则订单簿状态不可审计。
- **成本口径**：`LLM_CALL.purpose += "negotiation"`（居民 `thinking=false`，与 `dialogue` 同批接线）。**须同步 freeze 白名单 + 缓存键**（T92 同类坑：purpose 未登记会导致缓存/回放不一致）。
- **新增 hook**：`apply_exchange()`@4.1、`apply_contracts()`@4.2（挂入 Phase4 全序）。
- **新增商品字段**：`good.transferable: bool`（默认 `true`，商品注册表字段，非事件；校验用）。

> **指标口径（写死分子/分母，供 T101/T126）**：
> - **agent↔agent 成交占比**：`分子 = |{MARKET_TRADE: buyer∈Agents ∧ seller∈Agents}| + |{EXCHANGE_SETTLED: parties 双方均∈Agents}|`；`分母 = |全部成交| = |MARKET_TRADE| + |EXCHANGE_SETTLED|`。**分子/分母如上写死**，可复现。
> - **`distinct_sellers_excl_world`** = 卖方身份去重后**排除 world 标识**的计数（世界不计入）；与含 world 的 `distinct_sellers` **并列输出**——**`distinct_sellers_excl_world > 0` 才是 G-P1-1 的真判据**（当前 `distinct_sellers=1` 混了 world 与 Agent，故必须排除 world 才能作答）。
> - **`exchange.enabled=false` 消融** → `distinct_sellers_excl_world = 0`（世界市场保留，`distinct_sellers` 可能 =1）、`agent↔agent 成交占比 = 0`、`I_eff` P50=0、`CONTRACT_CREATED=0`（证伪力见 §5.8）。

> **G7/兼容**：`EXCHANGE_SETTLED` 为**新增类型**（旧日志不出现）、`channel` 为**可选字段**（被容忍）——**G7 不受影响**；与既有 66 类不冲突（只增不改，X1/X4）。**引擎实现**（`EVENT_TYPES`/`apply_event` 折叠器/两个 hook/意图）由 econ/kernel 实现阶段落地，本节只登记 schema。

**S. v2 双时钟唤醒事件（`WAKE` / `IDLE`；应 T263/T265，用户 2026-10-12 批准「乙+ 双时钟」，已登记）**

> 背景：用户批准「乙+ 双时钟」——**世界结算节拍 = round 不变**（84 回合/周、每回合结算全保留）；**新增「个体决策节拍」= 事件驱动唤醒**（未到期不决策、事件可唤醒、未唤醒者安静）。**`round` 仍为必带字段**（降为结算/显示标尺），**`seq` 仍全局全序唯一事实序（红线不变）**。W1–W10 唤醒集是 `(state, log, round)` 的**纯函数**、可离线复算 → **可审计**。

| type | phase | payload 关键字段 | 说明 |
|---|---|---|---|
| `WAKE` | 0 | `agent_id, round, reason∈{W1..W10}, source_event_seq, all_reasons?[]` | 唤醒记录（**每被唤醒 Agent 一条**，`actor=agent_id`），供「唤醒率 / 原因分布」统计与消融。`reason` **复用 §3.2 的 W1–W10**（单一真源 = 08 §3.2）；**一轮多因取优先级最高者**为主 `reason`、其余入可选 `all_reasons[]`；`source_event_seq` 指向触发源（W1 到期→`SCHEDULE_PLANNED`/反思事件；W2→`MSG_*`；W4→`MARKET_TRADE/OFFER_*`；W5→`LOAN_*`；W6→`RELATION_ENCOUNTER/PLACE_*`；定时兜底可 `null`） |
| `IDLE` | 0/6 | `round, total_agents, woken, idle, by_reason{W1..W10: count}` | **每回合一条全局聚合**（未唤醒汇总），`actor=SYSTEM`。**逐 agent 的 idle 集由 `roster − woken_set` 确定性推导**，不逐 agent 落事件（控体积、防刷屏） |

- **不新增 `DUE`**（T263 裁定）：到期触发**统一经 `WAKE` 承载**（`reason∈{W1,W7,W9}` + `source_event_seq`）；`SCHEDULE_PLANNED.planned_tick` / 反思阈值 `θ_reflect` **作为源保持不变**，`WAKE` 只记「被唤醒 + 因何」，不复制到期值。
- **不另立 `SLEEP`**：与 `IDLE` 同义，**统一用 `IDLE`**（避免"同概念两词"）。
- **`PERCEPTION_INDEX`（可选，暂不登记）**：增量感知一致性审计锚点；若 T264 增量索引确需落事件再单开（待定）。
- **config 开关（可消融；进 `engine_version` 指纹；§5.8 家族）**：`wake.enabled`（**默认 `false` = 行为不变**；置 `true` 启用事件驱动唤醒）+ `wake.triggers.{W1..W10}`（逐因开关，`W6` 默认 `true` 可关，供消融）+ `perception.incremental`（T264，默认/切换待定）。
- **红线**：`seq` 全局全序不变；`round` 仍必带；**全量日志仍必须可审计**（D1 只放开"逐位可复现"，**未**放开"可审计"）。
- **影响**：行为会变（DECIDE 门控）→ `state_hash`/canonical 变 → **与 T236 重冻联动**（由 sim-system-architect / obs 统筹）。
- **G7/兼容**：`WAKE`/`IDLE` 为**新增类型**（旧日志不出现），G7 不受影响；`visible_events` 收敛归 **T264（kernel-dev 独占）**，与本事件登记对齐 §3.5 单一来源口径。

**S. v2 睡眠 / 记忆整合遗忘 / 人格漂移事件（E-LIFE / E-MEM / E-LIFE-PERSONA，应 T224，已登记）**

> 口径：按用户 09:53 拍板的 **Fork B**——本族事件服务「**可审计**」（全量日志 + 种子化随机 + sha + 生成命令），**不要求「逐位重放一致」**；故 `retention_permille` 等可为**确定性规则/近似量**，无需为逐位一致做定点妥协。

| type | phase | payload 关键字段 | 归属族 / 说明 |
|---|---|---|---|
| `SLEEP_STARTED` | 3.5 | `agent_id, day, slot, planned_ticks` | **E-LIFE**：睡眠开始（日程 L2/L4） |
| `SLEEP_COMPLETED` | 3.5 | `agent_id, day, slot, actual_ticks` + `pf0, pf_t, drift_permille`（**每次睡眠必发**） | **E-LIFE**：睡眠结束；**携带人格指纹派生视图**（`pf0`/`pf_t`/`drift_permille`），保证 obs 能取到指纹（因 `PERSONA_FINGERPRINT` 为快照非事件，读不到） |
| `MEMORY_CONSOLIDATE` | 3.5 | `agent_id, source_mem_ids[], produced_mem_id, subject` | **E-MEM**：记忆**整合**（由源记忆产出新记忆；与 `MEMORY_REFLECT` 反思区分——整合是结构合并，非高层反思） |
| `MEMORY_FORGET` | 3.5 | `agent_id, mem_id, level∈{demote,merge,drop}, retention_permille, reason` + `protected(bool)`、`protection_reason?(str)` | **E-MEM**：记忆**遗忘/降级**（`demote` 降权 / `merge` 并入 / `drop` 丢弃；`retention_permille`=保留度千分比）。`protected`=受保护未忘；**保护名单单源在 life**，obs 直接 count、**不复刻规则** |
| `PERSONA_DRIFT` | 3.5 | `agent_id, dim, before, after, anchor, cause_mem_id` + `pf0, pf_t, drift_permille` | **E-LIFE-PERSONA**：人格维度漂移（**单事件单维**；`dim` 取值见 06 人格维度；`anchor` 为不变量基线）。**对齐用** `pf0`/`pf_t`/`drift_permille`（漂移发生时与 `SLEEP_COMPLETED` 的指纹视图对齐） |

- **`PERSONA_FINGERPRINT` 为快照、非事件**：`{agent_id, pf0, pf_t, drift_permille}` 建议入 **metrics / 侧存储**，**不登记为事件类型、不落哈希链**。**其派生视图由 `SLEEP_COMPLETED`（每次睡眠必发）与 `PERSONA_DRIFT` 携带**（否则 obs 读不到"快照非事件"的指纹）。
- **审计字段**：本族 life 事件均带 `day/slot`（`PERSONA_DRIFT` 亦带）；如需 `place` 视实现补。
- **引擎接入（不在本节）**：`engine/events.py::EVENT_TYPES` + `replay.apply_event` 折叠器由 **persona-life-designer** 在 T35/M2b 重构收敛后补——本节只登记 schema。
- **统计口径（建议，入 `metrics.life` 子键，按字典序）**：
  `metrics.life.memory{ forget_count_by_level, retention_hist, protected_kept, consolidate_count }`；
  `metrics.life.persona{ drift_permille, pf0, pf_t }`。

> **G7/兼容**：均为**新增类型**（旧日志不出现）→ **G7 不受影响**；与既有 66 类不冲突（只增不改，X1/X4）。

**T. v2 世界导演 + 事件制造机事件族（应 T238 / T204·T210·T216，已登记）**

> 权威来源：字段以 `v2/refs/world-director-design.md` §4（T210）为准；`kind` 枚举**以 `v2/refs/world-event-mechanisms.md` §2.1（T216）为唯一权威**；机制合规判据以 T216 单一机制表为准（取代 T204 §1.3 EF 表 / T210 §3 WD 表）。**红线 A′**：世界层可「导演未来」，三条保底不变。
>
> **actor 枚举扩展（已定）**：08 既有 actor 取值为 `AgentId | "SYSTEM" | "OBSERVER"`；本族**新增一等 actor `"DIRECTOR"`**（与 `"OBSERVER"` 同列），使「世界侧介入」可**一条过滤捞出**（`actor="DIRECTOR"`）。
>
> **⚠️ 装配点纪律（T235 教训）**：**每个字段都必须指明「由哪个装配点产生」**——08 登记了字段、装配白名单却**静默丢弃**（`MEMORY_RETRIEVE.vec_available` 曾是 0/60）是本项目已知病。**下表「装配点/产生方」列即为此**：实现方须确保这些字段**真的到达事件 payload**（装配白名单不得静默丢弃；不接收则显式报错）。

**T.1 `WORLD_DIRECTIVE`**（世界层**指令**＝导演意图；phase=3.5；`actor="DIRECTOR"`；**由内核校验后封装**）

| 字段 | 必填 | 语义边界 |
|---|---|---|
| `directive_id` | ✅ | 全局唯一 |
| `round, phase, actor("DIRECTOR")` | ✅ | v1 外壳；`actor` 为导演来源 |
| `directed=true` | ✅ | **保底(a)** 恒真；「导演介入」可一次检索 |
| `mechanism_id` | ✅ | 对应 T216 §2 机制ID（`WM-xx`/`wd.*`）；**保底(b)** 开关挂载点 |
| `kind` | ✅ | ∈ §2.1 的 WD-x/机制 kind（见 T.2，14 值） |
| `scope{level∈global\|place\|group\|agents, place?, group_ref?, agents?[]}` | ✅ | 作用对象；`level=agents` 且规模<K → **告警(非拒绝)**（WD-D1） |
| `params{}` | ✅ | 情境参数（规模/时长/强度）；**不得含金额/死亡/胜负数值**（R5） |
| `dose`, `dose_curve∈conservative\|moderate\|aggressive` | ✅ | **保底(b)** 剂量与曲线档（§3.1） |
| `issued_round`, `effective_from_round`（**≥ issued_round**） | ✅ | **保底(c)**：「只对未来生效」硬校验；违者 → `WORLD_DIRECTIVE_REJECTED{reason:"rewrites_past"}` |
| `seed_ref` | ✅ | RNG 流/seed 溯源（**RNG 先定**） |
| `place`(null=全局), `expires_round`, `rng_branch`, `rationale_ref`, `model` | ⭕ | 可选；`rationale_ref` 侧存储（N 类，不进判定）；`model` 审计四要素（若理由由 LLM 生成） |

- **什么算它**：世界层发起的**宏观情境指令**（节庆/灾害/政令/访客/供给冲击/疫病/公共工程/紧张升级/季节/大规模事件）。
- **什么不算它**：任何**社会结果**（关系/契约/规范/组织/排名/胜负）不得由 `WORLD_DIRECTIVE` 表达——那些必须由 Agent 自主行为产生。
- **装配点/产生方**：**WD-Core 决策器**（world-director）在决策相（Phase 2/3.5）生成意图 → **内核合规校验器**（§1.2 判定树 R1–R6）通过后封装落 `WORLD_DIRECTIVE`（经 IF-2 通道）。

**T.2 `WORLD_GROUP_EVENT`**（世界层**群体事件事实**；phase=3.5/4；`actor="DIRECTOR"`）

| 字段 | 必填 | 语义边界 |
|---|---|---|
| `group_event_id` | ✅ | 全局唯一 |
| `directive_ref` | ✅ | **溯源到 `WORLD_DIRECTIVE`**（可审计口径核心：每条宏观情境事件都能追到「哪条导演指令」） |
| `round, phase, actor, place?(null=全局), directed=true` | ✅ | v1 外壳 + **保底(a)** |
| `kind` | ✅ | **14 值**：`season, festival, opportunity, public_works, supply_shock, scarcity, tension, incident, disaster, epidemic, visitor, edict, agenda, mass_event`（**T216 §2.1 权威**） |
| `scope, params` | ✅ | 实际生效的作用域与情境参数（**无金额/死亡/胜负数值**） |
| `start_round` | ✅ | 生效起点（**≥ 对应 DIRECTIVE 的 `issued_round`**） |
| `end_round`, `affected_scope_count`, `per_agent_impact_ref` | ⭕ | `per_agent_impact_ref`：**灾难级(`aggressive`)开启时**指向「逐 Agent 影响」可复算侧产物（WD-D4） |

- **命名去歧义（硬约定）**：`WORLD_GROUP_EVENT ≠ GROUP_*`；其 `kind`（14 值，世界/环境）与 `GROUP_CREATED.kind`（`chat/guild/…`，组织）**枚举互不重叠**。
- **装配点/产生方**：**EF-Core / EF-Opp / EF-Incident**（T216 机制库）按日历/RNG 触发 → **内核据 `WORLD_DIRECTIVE` + RNG 确定性封装**为事实（**涉及金额/死亡的部分由内核从情境+RNG 推导为独立事件**，与本族**分列**）。

**T.3 `WORLD_DIRECTIVE_REJECTED`**（内核**拒绝 / 审计告警**；phase=3.5/4；`actor="SYSTEM"`）

| 字段 | 必填 | 语义边界 |
|---|---|---|
| `directive_id` | ✅ | 被拒/告警的指令 |
| `round, phase, actor("SYSTEM")` | ✅ | v1 外壳 |
| `reason` | ✅ | `rewrites_past` / `targets_individual` / `contains_hard_kernel_number` / `invalid_mechanism` / `dose_curve_unknown` |
| `severity` | ✅ | `reject`（拒绝）/ `warn`（审计告警，如 `scope` 规模 < K，WD-D1） |

- **装配点/产生方**：**WD-Core 合规校验器**（§1.2 判定树 R1–R6）在**拒绝或告警**时发；`rewrites_past`/`targets_individual`/`contains_hard_kernel_number` 对应三条保底与越权红线。

**T.4 `FORGE_FIRED`**（事件制造机**审计事件族**；phase=3.5/4；`actor="SYSTEM"|"DIRECTOR"`）

> **明确：`FORGE_*` 只有「审计事件族」，无「结果事件族」。** 事件制造机的「产物」经**既有事件**承载（`TIME_MARK` / `SEED_EVENT` / `MARKET` 上架 / `NEED_UPDATE` / `PRODUCE`…），**不新增 result 事件**（守 T216 红线：只造环境/机会/压力，不造社会结果）。

| 字段 | 必填 | 语义边界 |
|---|---|---|
| `mechanism_id` | ✅ | 触发的机制（`WM-xx`） |
| `cause` | ✅ | 触发原因（日历/库存/概率/条件），可回溯「哪个机制、哪个 RNG 分支」（E-5） |
| `seed_ref`, `rng_branch` | ✅ | RNG 先定（可复算） |
| `induced` | ✅ | 是否观察者/导演**诱导**（外部冲击/机会注入须标，禁被叙述成自发） |
| `effective_from_round`, `enabled_flag` | ✅ | 只对未来 + 当时开关态（**保底(b)**） |
| `social_result_emits` | ✅ | **恒 `0`**（E-3 机器可校验：forge 不得 emit 社会结果事件） |
| `dose`, `dose_curve` | ⭕ | 剂量（与 DIRECTIVE 对齐时填） |

- **装配点/产生方**：**EF-Control 控制面**（T216 机制库）在机制被调度触发时发射。

> **三条保底的机器可校验判据（落成字段，A′ 宪法）**：
> | 保底 | 字段承载 | 判据（可复算） |
> |---|---|---|
> | **(a) 显式介入** | `directed=true`（T.1/T.2） | `count(介入型事件, directed≠true)==0` |
> | **(b) 可消融** | `mechanism_id` + per-mech `wd.*.enabled` + `dose`/`dose_curve`（T.1/T.4） | 关闭机制 m → 其 `kind` 的 `WORLD_GROUP_EVENT` 归零/显著下降 |
> | **(c) 不改过去** | `effective_from_round ≥ issued_round`（T.1/T.2） | `∀DIRECTIVE: eff≥issued`；无存活 `WORLD_DIRECTIVE_REJECTED(reason="rewrites_past")` |

> **G7/兼容**：`WORLD_DIRECTIVE`/`WORLD_GROUP_EVENT`/`WORLD_DIRECTIVE_REJECTED`/`FORGE_FIRED` 均为**新增类型**（旧日志不出现）→ **G7 不受影响**；与既有 66 类不冲突（只增不改，X1/X4）。**引擎实现**（`engine/events.py::EVENT_TYPES` + `replay.apply_event` 折叠器 + WD-Core/EF-* hook）由实现阶段（T239 等）落地，本节只登记 schema。**`inert_registry.json` 已同步登记其「装配点/预期状态」**。

> **通信事件复用 v1**：`MSG_PUBLIC / MSG_DM / MSG_GROUP` 不新增，但新增可选字段 `refs[]`（引用 msg_id）与 `tag_hints[]`（供 `TAG_EMITTED` 关联，实为内容层）。传播边由 `OBSERVATION.target_event_seq` 与 msg `refs` 共同构建（§4.3）。

**U. 字段主体口径：`agent_id`（及 `actor`/`subject`）可含「非 Agent 主体」（应 T248，已登记为已知例外）**

> **已知例外（Leader 2026-10-12 裁定：登记，不改名）**：`payload.agent_id` **不保证是真实 Agent**——它语义为「**本事件主体的账户标识**」，**可含世界侧哨兵**（`MARKET`/`BANK`/`WORLD`/`TAX_POOL`）。实测来源：econ 系统账户折叠（如 `STATE_CHANGE{agent_id:"MARKET"}`、`NEED_UPDATE{agent_id:"MARKET"}`）。与 `actor`（T241）**同族、在另一字段上**——统一按「主体字段可为非 Agent」处理。

- **消费方硬约束**：凡把 `agent_id`（及 `actor`/`subject`/`observer`）**当作某个 Agent**（计入 agent 级指标 / 渲染为角色 / 建索引）前，**必须用单一真源 `contracts.actors` 守卫**：`is_agent_actor(x)` / `agent_or_none(x)`（`NON_AGENT_ACTORS = {SYSTEM, OBSERVER, DIRECTOR, WORLD, MARKET, BANK, TAX_POOL}`）。**各消费方一律引用本模块，勿各自复制白名单**（同名不同义风险）。
- **不改事件语义的理由**：改名（另立 `subject_id`/world 字段）代价大、动 08 全套；故本轮**登记为已知例外**（口径清晰 + 消费方守卫），**非"两种都不做"**。
- **观测影响（T248 实测，obs 侧已止血）**：未守卫时泄漏量见 `v2/evidence/t248-agent-id-semantics.md`（如 `mastery` min 25→29、`n_need_updates` 3399→3310）；obs `life.py::need_metrics` 与 `census.py` E7 已复用 `contracts.actors` 过滤。
- **生产侧**：本次**不动**（哨兵账户是 v2 市场/系统账户设计的既有产物）；如未来为 world 主体单列字段，须回写本节。

> **「确定性后果真值」口径（T257 裁定，08 权威；替代原「建议合并」附记）**：
> 存在**两个**实现 `obs/truth.py`(`264c07f`) 与 `obs/truth_from_consequences.py`(`969335f`)，口径分歧（3/3 输入）。现裁定：
> 1. **单一真源** = **`obs/truth_from_consequences.py`**（`obs/truth.py` 废弃并入）；验收=合并机制下输出一致（**口径变更处按本表修正输出**，非"跨口径逐字节不变"）。
> 2. **词汇唯一权威** = `life/constants.py::JUDGMENT_OPTIONS`。**注意**：`respect`(high/low) 与 `rel_respect`(formed/not_formed) 是**不同维度、不得归一**；`rel_trust` 属 **formed 族**（**非** high/low）——`truth.py` 的 `rel_trust→high/low` 错，按此纠正。
> 3. **维度→真值口径**（窗口 `(r, r+W]`，`W=12` 默认、参数化；全确定性、无 LLM/时钟）：
>    | dimension | 选项 | 真值口径 |
>    |---|---|---|
>    | `rel_affinity` / `rel_familiarity` / `rel_trust` / `rel_respect` | `formed`/`not_formed` | 窗口内存在 `RELATION_CHANGE{dim}.after ≥ θ_dim` ⇒ `formed`；**有事件但均 < θ ⇒ `not_formed`**；**无事件 ⇒ `undecidable`（剔除、按维计数）**。`θ_dim` 默认 = **`ε=20`**（06/07 弱边阈），可配【待标定】 |
>    | `stance` | `accept`/`reject` | 窗口内 `OFFER_ACCEPTED{by=A, creator=B}` ⇒ `accept`；`OFFER_REJECTED{…}` ⇒ `reject`；均无 ⇒ `undecidable` |
>    | `respect` | `high`/`low` | 窗口内 `RELATION_CHANGE{dim=respect}.after ≥ θ_respect` ⇒ `high`，否则 `low`；无事件 ⇒ 剔除 |
>    | `affection` | `high`/`low` | **无对应关系维 ⇒ 剔除** |
>    | `weekly_focus` / `importance` | … | **无干净确定性后果 ⇒ 剔除** |
> 4. **关键裁定**：① `formed` 判据 = **状态量达阈（`after ≥ θ`）**、**非 `Δ>0`**（Δ=1 不应算"形成"）；② `stance` 真值 = **行为性 `OFFER_*`**、**非关系净符号**（关系净符号是间接后果）；③ 词表收敛见第 2 条。
> 5. 归 **obs-stats-dev** 实现/合并。**同族一并留意**：`visible_events` 存在 `engine/perceive` 与 `life/visibility` 双实现（口径同族，须收敛为单一来源）。

> **对齐提示（供 persona-life-designer / emergence-observer-designer）**：上表 `dim`、`activity_type`、`place`、`tag` 的**取值枚举**由你们在 06/07 分册定义；本文件只固定**结构、必带字段与语义**。我会在看到 06/07 后按需在 §8 补一张「枚举取值对齐表」。

---

## 2. Hook 链扩展（覆盖要求 2）

### 2.1 阶段编码约定（已定）

v1 阶段：`0 ROUTE → 1 PERCEIVE → 2 DECIDE → 3 COMMUNICATE → 4 ARBITRATE → 5 LIFECYCLE → 6 COMMIT`。

v1.1 新增 **Phase 3.5 `LIFE`**，插在 `COMMUNICATE(3)` 与 `ARBITRATE(4)` 之间：

```
Phase 3   COMMUNICATE
Phase 3.5 LIFE   <-- 新增：生活层确定性结算（L1..L7）
Phase 4   ARBITRATE  (4.1..4.8 顺序冻结，见 X2)
```

- `phase` 字段编码：用整数 `35` 表示 Phase 3.5（避免小数字段），并在 `apply_event` 分派中映射为 `LIFE`。
- **为什么放在 4 之前**：生活层先推进时间、结算活动的**非货币状态**（场所、需求、关系、记忆、标签），其产生的**货币后果以 intent 形式交给 4.1–4.8 结算**。这样既让活动能影响经济，又**完全不动 4.x 内部顺序**。

> **待讨论 XT-2**：若某些活动需「先买入再消费」（依赖 4.1 撮合结果），可把该类活动结算拆到 `Phase 6` 之后的新阶段 `6.5`。v1.1 默认**先生活后经济**（活动多为非即时货币），如需可配置。

### 2.2 新增 hook 签名（已定，可直接实现）

```python
# 全部满足 v1 §2.2 的 I1–I5（纯函数、幂等、无 I/O、随机经 ctx.rng）。
def advance_time(state, round, ctx) -> Delta: ...        # L1
def resolve_schedule(state, round, ctx) -> Delta: ...    # L2
def settle_activities(state, round, ctx) -> Delta: ...   # L3
def apply_needs(state, round, ctx) -> Delta: ...         # L4
def update_relations(state, round, ctx) -> Delta: ...    # L5
def write_memories(state, round, ctx) -> Delta: ...      # L6
def emit_tags(state, round, ctx) -> Delta: ...           # L7
```

### 2.3 Phase 3.5 内部顺序与语义（已定）

```
L1 advance_time(state)        # 派生 week/day/slot；跨日/周发 TIME_MARK
L2 resolve_schedule(state)    # 到期 slot 提升为 ACTIVITY_STARTED intent；计划调整
L3 settle_activities(state)   # 到期活动结算法：ACTIVITY_COMPLETED/INTERRUPTED，
                              #   产出 resource_intents[]（货币后果交 4.x）、NEED_UPDATE
L4 apply_needs(state)         # 需求自然衰减/满足（规则驱动）→ NEED_UPDATE
L5 update_relations(state)    # 由活动/对话/相遇更新关系维度 → RELATION_CHANGE / RELATION_ENCOUNTER
L6 write_memories(state)      # 按确定性 salience 规则落 MEMORY_WRITE / OBSERVATION；
                              #   累积重要性超阈 → MEMORY_REFLECT（反思内容由 Phase2 LLM 产，此处封装落日志）
L7 emit_tags(state)           # 由消息/活动内容层提交的 tag_hints 落 TAG_EMITTED；跑 NORM_* 阈值判定
```

- **与 4.x 的接口**：L3 产生的货币意图写入 `state.pending_intents`，由 4.1 `settle_market` / 4.2 `settle_obligations` 统一校验结算；**生活 hook 自身永不直接改账**（延续 P7「意图/事实分离」）。
- **幂等契约同 v1 I1–I5**：引擎以 `(round, phase=35, hook_name)` 为幂等键；重放不重算（X5）。
- **哨兵顺序固定**：L1→L7 顺序不可变；每个 hook 内遍历按 `agent_id` 升序、事件按 `(round, phase, seq)` 全序（v1 P5）。

### 2.4 完整 hook 链（v1.1 全景）

```
P0 ROUTE
P1 PERCEIVE
P2 DECIDE            (T0 规则 / T1 小模型 / T2 LLM；含 SCHEDULE_PLANNED / GOAL_SET / MEMORY_RETRIEVE)
P3 COMMUNICATE       (三通道配额与惩罚，见 v1 §4)
P3.5 LIFE            L1 advance_time → L2 resolve_schedule → L3 settle_activities
                     → L4 apply_needs → L5 update_relations → L6 write_memories → L7 emit_tags
P4 ARBITRATE         4.1 settle_market → 4.2 settle_obligations → 4.3 apply_tax
                     → 4.4 apply_metabolism → 4.5 apply_penalty → 4.6 check_lifecycle
                     → 4.7 resolve_revival → 4.8 check_death      (顺序冻结，X2)
P5 LIFECYCLE
P6 COMMIT            (追加日志 + 守恒校验 + 快照 + 指标)
```

---

## 3. 时间结构（覆盖要求 3）

### 3.1 时间层级：回合–时段–日–周（已定，按「模拟周」定稿）

用户已拍板：**先做「模拟周」**，场景为**单一小镇**（不再考虑多场景派生）。时间层级自底向上为 **回合(round/tick) → 时段(slot) → 日(day) → 周(week)**，全部为**确定性派生**（纯函数、参数化）。

```python
TIME_CONFIG = {
    "ROUNDS_PER_SLOT": 3,          # 1 时段 = 3 回合（底层 tick）
    "SLOTS_PER_DAY": [             # 一日四时段（语义由 00-architecture / 生活层细化）
        "morning", "afternoon", "evening", "night"
    ],
    "DAYS_PER_WEEK": 7,            # 一周 7 日
    "DAY_TYPES": [                 # 工作日 / 周末 分类（前 5 工作日 + 后 2 周末）
        "workday","workday","workday","workday","workday","weekend","weekend"
    ],
    # 工作日 vs 周末 的差异参数（供 L2 日程 / L7 事件概率使用）
    "DAY_TYPE_PARAMS": {
        "workday": {"work_required": True,  "leisure_weight": 0.3, "social_event_prob": 0.05, "sleep_slots": ["night"]},
        "weekend": {"work_required": False, "leisure_weight": 0.7, "social_event_prob": 0.25, "sleep_slots": ["night"]},
    },
    "WEEK_PHASES": ["PLAN", "CONTACT", "ACTIVITY", "REVIEW"],  # Agentopia 式周相位（可选，D7-2）
}

def derive_time(round: int, cfg) -> dict:
    """纯函数：round -> 时间坐标。确定性、无副作用、无墙钟。"""
    rps = cfg["ROUNDS_PER_SLOT"]; spd = len(cfg["SLOTS_PER_DAY"])
    rounds_per_day = rps * spd                                   # 默认 3*4 = 12 回合/日
    day  = round // rounds_per_day
    slot_idx = (round % rounds_per_day) // rps
    tick_in_slot = round % rps
    week = day // cfg["DAYS_PER_WEEK"]
    day_type = cfg["DAY_TYPES"][day % cfg["DAYS_PER_WEEK"]]      # workday / weekend
    return {"week": week, "day": day, "day_of_week": day % cfg["DAYS_PER_WEEK"],
            "day_type": day_type, "slot": cfg["SLOTS_PER_DAY"][slot_idx],
            "tick_in_slot": tick_in_slot}
```

**按默认参数的换算**：`1 时段=3 回合`，`1 日=4 时段=12 回合`，`1 周=7 日=84 回合`。

**工作日 / 周末 参数化（已定框架，取值待生活层定 D7-3）**：
- 差异只影响**行为倾向与事件概率**（`DAY_TYPE_PARAMS`：是否强制工作、休闲权重、大型社交事件概率、睡眠时段），**不影响 tick 级经济/生命周期结算频率**（v1 契约 X2/X3 不变）。
- `day_type` 作为生活层事件的必带审计字段（§1.1），供「工作日 vs 周末」对比统计（§4 各指标可按 `day_type` 分组）。

> **待讨论 D7-1（已收窄）**：`ROUNDS_PER_SLOT` / `SLOTS_PER_DAY` / `DAYS_PER_WEEK` 的具体取值，以及工作日/周末的 `DAY_TYPE_PARAMS` 数值——**以 `00-architecture.md`（T12）的周时间结构为准**；该文档未落盘前先采用上表默认值。
> **待讨论 D7-2**：周相位 `WEEK_PHASES` 是否采纳、如何映射到 L2 日程语义。

### 3.2 与 v1 回合的关系（已定）

- v1「回合」= v1.1「回合/tick」，语义不变；v1 的经济/生命周期 hook 仍每回合执行（代谢、税、债务按回合计息，口径不变）。
- 时段/日/周是**叠加在回合之上的派生视图**，不改变回合级结算频率（保持 v1 契约 X2/X3）。
- **单小镇世界**：场所集合为单一小镇内的若干场所（枚举由 00-architecture 定义）；引擎不引入跨场景/多世界维度，`place` 为小镇内场所标识。

### 3.3 单小镇场景声明（已定）

- 采用**单一小镇（五脏俱全）**：一个拓扑内的场所集（住家/工作地/公共空间等，枚举待 00-architecture）。
- 引擎不为「多场景」预留派生分支；`SEED_EVENT`/观测/传播均在**同一小镇**内进行，简化关系与传播图的构建。
- 与 v1.1 调研简报 §6「多场景」建议的差异：**以用户拍板为准，收敛为单小镇**（原 Agentopia 多场景派生**放弃**）。

### 3.4 审计锚点（已定）

跨时段/跨日/跨周时 L1 发 `TIME_MARK`（含 `round, week, day, slot, day_type`），使「按时段/日/周切片」的统计可对齐而无需回算（也可回算，二者一致）。

### 3.5 感知作用域与可见性分类（R1/R2 + D1–D4，已登记）

> 来源：`v1.2/03-pov-visibility-check.md`（NT-C3 核查）。目的：把「谁能看到什么」变成**可从日志 + config 确定性重算**的 `visible_events(agent)`（纯只读、`llm_calls==0`、可逐位重放），`OBSERVATION` 退为显著度证据（R5，见 §1.2）。

**R1 · 事件 `place` 字段（确认，已登记）**：所有**可感知**事件带 `place`（生活层事件已带，§1.1）；`MSG_PUBLIC` 及**重大事件**标 `place=null` 且 `scope=global`。

**R2 · config 表 `PERCEPTION_SCOPE`（新增，无新事件）**：

```
PERCEPTION_SCOPE: { event_type -> visibility_class }
visibility_class ∈ { global, place_local, members, private, participants_only, subject_only }
```
| visibility_class | 判定（确定性谓词） | 典型 event_type |
|---|---|---|
| `global` | 全体存活 Agent 可见 | `MSG_PUBLIC`、重大事件（见 D3 白名单） |
| `place_local` | `e.place == location(agent, e.round)` 且 `alive(agent, e.round)` | `ACTIVITY_*`、`PLACE_MOVE`、`RELATION_ENCOUNTER`、生活/涌现事件 |
| `members` | `agent ∈ members(group_id, e.round)`（R3） | `MSG_GROUP` |
| `private` | `agent ∈ {from, to}` | `MSG_DM` |
| `participants_only` | `agent ∈ (participants ∪ {actor})` | `TRANSFER`、`MARKET_TRADE` |
| `subject_only` | `agent ∈ {actor} ∪ subject` | 特定主观事件 |

> **T247 口径（2026-10-12 定稿 · 记录性语义分类）**：`SKILL_PRACTICE / SKILL_LEVEL_UP / SKILL_OUTPUT` 在 `PERCEPTION_SCOPE` 无条目（落 `default=place_local`）。**记录其语义分类**（表明"08 事件表 ↔ `perception_scope.json` 真源未对齐"这一缺口）：
> - `SKILL_PRACTICE` = **`place_local`**（payload 含 `place`，同场所可见其练习）
> - `SKILL_LEVEL_UP` = **`subject_only`**（自己的成长）
> - `SKILL_OUTPUT` = **`subject_only`**（自己的产出物）
>
> **但 config 本轮不应用（by design）**：T247 最终裁定**在 emit 边界物化正文/产物**（行为中性、无数据丢失）→ **不需要 `SKILL_OUTPUT` 经 `perceive` 可见**；且 `SKILL_*` **不在** life `_SALIENT_EVENTS` → 加 scope 条目**今天零效果、却改复现输入/`engine_version` 指纹**。**故本轮不改 `config/perception_scope.json`。** 若**未来**把 `SKILL_*` 加入 `_SALIENT_EVENTS`（进入 LLM observation），须**届时应用本分类并重估 token/行为**。
> **一般口径（记录）**：**并非所有事件都经 `perceive` 消费**——`visible_events(agent)` 只覆盖「供 Agent 决策/记忆」的事件；**emit 边界物化的正文/产物、纯审计类事件无需 `PERCEPTION_SCOPE` 条目（缺条目 ≠ 漏登记）**。

- **版本入 `engine_version`**（比照 TOPOLOGY，00 AR-D2 / 08 §5.6）：`PERCEPTION_SCOPE` 表落 config，纳入引擎版本指纹，保证可复现。
- **`location(agent, t)`**：由 `PLACE_MOVE / PLACE_ARRIVED` 折叠的占用时间线（初始 = `residence`），纯函数。
- **`visible_events(agent, log, T, cfg)`** = 直接可见（按上表谓词）∪ 记忆链（`MEMORY_WRITE.source_event_seq` / `MEMORY_RETRIEVE` / `MEMORY_REFLECT` 闭包）∪ `LLM_JUDGMENT.parties`（S11）。判定与函数签名见 03 报告 §3；**无 LLM 参与**。

- **口径唯一 · `visible_events` 单一来源（硬规则，应 T254 §6.2 / T257 / T263）**：**`visible_events` 只允许一份实现，语义唯一、不得复制**。现状为**多份**（`engine/perceive.py::visible_events`、`life/visibility.py::visible_events`、`orchestration.KernelAdapter.perceive` 内联）——**必须收敛为单一来源**：
  - **权威算法** = 本节 §3.5 的谓词（读 canonical `PERCEPTION_SCOPE`，不各自维护 white-list）；
  - **参考实现** = `engine/perceive.py::visible_events`（直接读 canonical `config/perception_scope.json`）；
  - **收敛落点**（共享模块 or 委托）由 **kernel-dev** 定（受分层约束：`life` 不 import `engine`，故通常需抽到中立层）；**未收敛前，其它实现须与本参考实现语义一致**（不得各自演化）；
  - **禁止**：两处并存且语义不同（"同概念两处定义"）。

**Leader 已裁定 T26-D1–D4（落定，不再列待讨论）**：
- **D1**：公开板可见范围 = **全员存活**（单小镇闭合；长窗再细化）→ `MSG_PUBLIC.visibility_class = global`，判定 `alive(agent, e.round)`。
- **D2**：`residence` 内私密对话 = **`participants_only`**（仅对话双方）。
- **D3**：重大事件 `global` 白名单 = **可配**，**默认仅 `AGENT_DIED`**（`STATE_CHANGE` 默认 `place_local`，除非进入白名单）。
- **D4**：一阶「听说」（`heard_events`，沿收信 `refs[]` 反向闭包）计入 POV 旁注，但**标 `spec=true`，永不计入 `visible_events`**。

> **审计**：POV 报告附 `visible_event_digest`（`visible_events` 规范哈希）与 `scope_table_version`，使「此 POV 依据哪些可见事件」可核验。

---

## 4. 统计指标扩展（覆盖要求 4）

> 全部指标 `f(EventLog, T, TIME_CONFIG)`，纯函数、整数优先、规范 JSON、逐位一致（v1 §5 同款约束）。**LLM 判定一律不参与**（C3/C4）。金额用 mu；比例最后一步定点输出 `round(x,6)`。

### 4.0 命名空间与快照（已定）

```json
{
  "schema_version": "1.1",
  "round": 100, "week": 4, "day": 29,
  "metrics": {
    "econ":            { /* v1 原样，口径冻结 */ },
    "lifecycle":       { /* v1 原样，口径冻结 */ },
    "life":            { "<life_metric>": {...} },
    "emergence":       { "<emergence_metric>": {...} },
    "emergence_soft":  { "<soft_metric>": {...} },
    "wellbeing":       { "<wellbeing_metric>": {...} },
    "wellbeing_soft":  { "<soft_metric>": {...} },
    "narrative":       { "<narrative_metric>": {...} }
  }
}
```
- v1 指标迁入 `metrics.econ` / `metrics.lifecycle`，**数值口径完全不变**（仅容器变化，可用适配层兼容旧键名）。
- 新增指标在 `metrics.life` / `metrics.emergence`；键按字典序。

**`metrics.emergence_soft` 命名空间（应 T9-C4 / AR-C8 登记，已定）**：
- 适用：**其输入含「冻结的 LLM 定性判定」（`LLM_JUDGMENT`）** 的指标（如基于 LLM 喜好/尊重打分的软性社会评价维度）。
- **硬约束**：该命名空间指标**只作敏感性分析（sensitivity analysis）**，**绝不进入任何判定路径与门禁（gate）**；`llm_judged_metric_count == 0`（§4.10）**仅针对 `metrics.econ/lifecycle/life/emergence` 四类**，`emergence_soft` 单独标注 `contains_llm_judgment=true` 并从门禁指标集**排除**。
- **确定性要求**：即便输入是冻结判定，该命名空间的计算仍须**只读日志、纯函数、对同一日志逐位一致**（AR-C9）；不重问 LLM。
- 用途示例：软性声望/喜爱度的趋势观察、与硬指标（`emergence`）的相关性对照——**观察用，非验收用**。

**`metrics.wellbeing` 与 `metrics.wellbeing_soft` 命名空间（应 WB-C3 登记，已定）**：
- `metrics.wellbeing`（**确定性**）：幸福感/生活质量的**纯确定性**部分（如需求满足度、活动多样性、技能成长、客观生活水平等），**纳入门禁统计**，保持 `llm_judged_metric_count == 0`。
- `metrics.wellbeing_soft`（**含 LLM 冻结判定**）：主观满足感、W2 互评、W7 meaning 等**依赖 `LLM_JUDGMENT`** 的指标；**与 `emergence_soft` 同等处理**——标 `contains_llm_judgment=true`、**只作描述与敏感性分析**、**不进沙盒门禁**，并从门禁指标集排除。
- 两者对同一日志均须**确定、逐位一致**（AR-C9）；不重问 LLM。

**`metrics.narrative` 命名空间（应 17-narrative-layer §NT-C2 登记，已定）**：
- 适用：叙事侧产物与展示指标（戏剧性选片 `narrative_selection`、各风格/视角版本计数、`anchor_digest` 覆盖率、`spec_flags` 统计等）。
- **性质**：**非判定命名空间**——与 `emergence_soft`/`wellbeing_soft` **同类**：`llm_judged_metric_count` **不涉及**（叙事不进入判定路径）、**不进沙盒门禁**、**仅描述性/展示用**。
- **确定性边界**：其**确定性部分**（`narrative_selection` 的戏剧性度量 `D(atom)`、`NV(Scene)` 与选片、`anchor_digest`）**全部 D 类、可重算、同日志逐位一致**，权重落 `config/narrative_weights.json` 并纳入 `engine_version` 指纹；**叙述文本（N 类）不入本命名空间的硬指标**，仅以 `model/prompt_hash/spec_flags` 元数据标注。
- **与 17 的对应**：`narrative_selection` 为独立侧产物（供渲染器消费），**不进** `metrics.emergence`，不影响 T9 判定与门禁。

### 4.1 活动参与度（life）

```
对窗口 W（回合/日/周），按 activity_type a：
  eligible(a)  = 窗口内有该 a 类型 slot 计划的 Agent 数
  participated(a) = 窗口内 ≥1 次 ACTIVITY_STARTED(type=a) 的 Agent 数
  participation_rate(a) = participated(a) / eligible(a)          # 分母0 -> 0
  completion_rate(a)   = Σ completed(a) / Σ started(a)
  mean_duration(a)     = Σ duration_ticks(completed) / |completed(a)|   # 最近秩/整数均值
  interrupt_rate(a)    = Σ interrupted(a) / Σ started(a)
```
- 来源：`SCHEDULE_PLANNED / ACTIVITY_STARTED / ACTIVITY_COMPLETED / ACTIVITY_INTERRUPTED`。
- 全局 `activity_engagement = Σ participated / alive_count`。

### 4.2 需求满足度分布（life）

```
对每个 need 维度 d：
  need_level_i(t) = 由 NEED_UPDATE 折叠出的当前值（取每 Agent 最后一笔 after）
  mean/median/p10/p90（最近秩）
  deprivation_rate(d, θ) = |{i: need_level_i < θ}| / alive_count     # θ 待 persona 层给（D7-3）
  satisfaction_trend(d)  = 窗口内 mean 的差分序列
```
- 来源：`NEED_UPDATE`。

### 4.3 关系网络演化（life + emergence）

**在 v1 §5.8 基础上增加时间维与方向语义**：

```
金钱图 G_money(v1) / 沟通图 G_comm(v1) 保持不变（口径冻结）。
新增 关系图 G_rel：有向、多维权（dim ∈ {affinity,trust,respect}），
  边权 w_dim(a→b) = 由 RELATION_CHANGE 折叠出的当前值。

关系指标（每窗口一个快照）：
  reciprocity(dim)   = |{(a,b): a→b 与 b→a 均存在且 |w|≥ε}| / |{a→b 存在}|
  tie_formation_rate = 本窗口新增「强关系边(|w|≥ε_strong)」数 / alive_count
  tie_decay_rate     = 本窗口由强转弱/断开的边数 / alive_count
  mean_degree(dim), weighted_mean_degree(dim)
  PageRank(G_rel, dim)   # Agentopia 式，确定性：固定阻尼 d=0.85、固定迭代次数 K、固定节点顺序
  encounter_rate     = RELATION_ENCOUNTER 数 / (alive_count·窗口)
```
- 来源：`RELATION_CHANGE / RELATION_ENCOUNTER`（关系图）；`TRANSFER/MARKET_TRADE`（金钱图，v1）；`MSG_*`（沟通图，v1）。
- **平局打破**：PageRank 迭代与遍历按 `agent_id` 升序；收敛判据固定（`L1` 差 < 1e-9 或达 K 次）。

### 4.4 传播链长度（emergence，核心范式）

**传播图构建（确定性，来自日志）**：

```
节点：参与某 seed 级联的 (agent, event) 二元组
边 u→v：存在 OBSERVATION(observer=v, target_event_seq=u事件)
        或 msg(v).refs 含 u 的 msg_id（同一 seed 级联内）
级联 C = 从 SEED_EVENT(seed_id) 出发、在窗口 Δ 内可达的子图

指标：
  cascade_size  = |nodes(C)|
  depth         = 从 seed 到最远节点的最长路径长度
  breadth       = 各层级节点数的最大值
  R0            = 传播者平均出度 = Σ outdeg(spreader) / |spreaders|
  time_to_spread= 首达各层级所需 tick 的中位数
  reach_ratio   = |distinct agents in C| / alive_count
  path_len_dist = 从 seed 到各节点距离的直方图（固定分箱）
```
- 来源：`SEED_EVENT / OBSERVATION / MSG_*`。
- **不依赖 LLM**：级联完全由图可达性定义，标签/文本仅作为 `OBSERVATION` 的锚点。

### 4.5 标签/观点频次与时间演化（emergence）

```
对窗口 W 与标签 tag：
  freq_W(tag)   = Σ TAG_EMITTED(tag) 计数
  share_W(tag)  = freq_W(tag) / Σ_{tag'} freq_W(tag')          # 分母0 -> 0
  entropy_W     = -Σ share_W(tag)·ln(share_W(tag))            # 归一化 H/ln(K)
  HHI_W         = Σ share_W(tag)^2                            # 集中度
  adoption_W(tag) = |{distinct agent: 曾 emit tag}| / alive_count
  valence_mean_W(tag) = Σ valence / freq_W(tag)
  trend_W(tag)  = freq_W(tag) − freq_{W-1}(tag)               # 时间演化一阶差分
```
- 来源：`TAG_EMITTED`。
- `entropy/HHI` 用定点数值实现或统一 `round(...,6)` 输出（快照标注 `num_method`）。

### 4.6 圈层 / 群体涌现（emergence）

```
对关系图 G_rel（每窗口切片）:
  communities = Louvain(G_rel, seed=FIXED, node_order=升序)   # 确定性
  n_communities, modularity Q
  community_size_dist = 各社区规模直方图（固定分箱）
  membership_stability = ARI(communities_W, communities_{W-1})  # Adjusted Rand Index
  isolation_rate = 孤立节点(|deg|=0)数 / alive_count
```
- **确定性保证**：Louvain 固定随机种子与节点遍历顺序；n≤50 时节点少，亦可退化为确定性贪心（Girvan-Newman 边介数）以求完全可复现。**待讨论 D7-4** 选哪种。

### 4.7 规范 / 文化形成（emergence）

```
NORM_ADOPTED 判定为纯规则（支持者 ≥ threshold）——LLM 不判定。
指标:
  n_norms_proposed / n_norms_adopted / adoption_success_rate
  time_to_adopt = median(adopted_day − proposal_day)
  norm_violation_rate = Σ NORM_VIOLATED / (adopted norms × alive_count × 窗口)
  norm_coverage = mean(adopters)/alive_count at window end
```

### 4.8 职业 / 身份转变（emergence）

```
ROLE_CHANGE 折叠出角色时间线。
  transition_matrix[from_role][to_role] = 计数（行归一化）
  role_entropy = 当前角色分布的 Shannon 熵
  switch_rate = Σ ROLE_CHANGE / (alive_count × 窗口)
```

### 4.9 记忆系统指标（life，用于成本与行为分析）

```
  mem_count_i(t)      = MEMORY_WRITE 累计（每 Agent）
  mem_growth_rate     = 窗口新增记数 / alive_count
  retrieval_hit_rate  = |{MEMORY_RETRIEVE: selected 非空}| / |MEMORY_RETRIEVE|
  mean_topk           = mean(top_k)
  importance_dist     = MEMORY_WRITE.importance 直方图（固定分箱 0..10）
  reflection_rate     = Σ MEMORY_REFLECT / (alive_count × 周)
```
- 来源：`MEMORY_WRITE / MEMORY_RETRIEVE / MEMORY_REFLECT`。用于成本监控与「反思触发阈值」调优。

### 4.10 观测偏差自查（emergence，方法论必需）

```
  llm_judged_metric_count = 0        # 硬约束：统计指标中 LLM 判定者必须为 0
  observer_injection_count = Σ SEED_EVENT（人为干预强度）
  determinism_ok = (两次 metrics() 输出字节相等)   # CI gate
```
- 目的：显式证明「涌现观测不依赖 LLM 主观判断」（对应 emergence-observer 的方法论铁律）。

---

## 5. 存储与成本（覆盖要求 5）

### 5.1 日志体积模型（已定方法）

```
每回合事件量:
  E_round ≈ N_alive·(α_act + α_move + α_need + α_rel + α_mem + α_tag) + M_msgs + E_sys
其中（初值待 sandbox 标定，D7-5）:
  α_act≈0.5(活动启停) α_move≈0.3 α_need≈1.0 α_rel≈0.5 α_mem≈1.5 α_tag≈0.5
  M_msgs = 三通道实际条数（v1 §4 配额上界）
  E_sys  = 每回合系统事件（TIME_MARK/税/代谢等）≈ 少量

日志体积 ≈ Σ_round E_round × bytes_per_event × (1 − compression_ratio)
  bytes_per_event 基准 ≈ 200–400 B（JSON）；gzip/列式压缩后 ≈ 3–6× 下降
```

**量级示例（按「模拟周」定稿，1 周 = 84 回合）**：
- 每回合事件量：50 Agent → `E_round ≈ 50×4.3 + 30 + 5 ≈ 250`；10 Agent（沙盒）→ `E_round ≈ 10×4.3 + 12 + 5 ≈ 60`。
- 每回合字节（未压缩，200–400 B/事件，取 300 B）；压缩比按 4× 估。

| 运行时长 | 回合 | 50-Agent 事件量 / 体积（原始→压缩） | 10-Agent 事件量 / 体积（原始→压缩） |
|---|---|---|---|
| 1 周 | 84 | ~2.1e4 / ~6.3 MB → ~1.6 MB | ~5.0e3 / ~1.5 MB → ~0.4 MB |
| 4 周 | 336 | ~8.4e4 / ~25 MB → ~6.3 MB | ~2.0e4 / ~6.0 MB → ~1.5 MB |
| 12 周 | 1008 | ~2.5e5 / ~76 MB → ~19 MB | ~6.0e4 / ~18 MB → ~4.5 MB |

**结论**：即便跑到 12 个模拟周、50 Agent，压缩后日志仍在 **~20 MB** 量级，内存随快照节流（§5.2）可控；**唯一显著成本是 LLM 调用**（见 v1 §3.3 成本模型，生活层新增 `plan/dialogue/reflect` 类调用，须并入同一 `LLM_BUDGET` 闸门）。日志/复现成本不构成瓶颈。

> **待讨论 D7-5（已按周细化）**：α_* 各系数与本表的 bytes_per_event、压缩比，需 sandbox（T10）实测标定；`ROUNDS_PER_SLOT` 变化会线性改变周内回合数与此表数值。

### 5.2 控制手段（已定）

| 手段 | 做法 | 效果 |
|---|---|---|
| **列式/字典压缩** | 日志按列（round/type/actor）用字典编码 + parquet/zstd | 体积 ↓ 3–6× |
| **快照节流** | 快照每 K 回合一次（K 可配，默认 100），其余从日志重建 | 内存可控 |
| **记忆侧存储** | `MEMORY_WRITE.body`、`embed` 存**侧存储**，主日志只存 `body_ref/embed_ref`（含内容哈希） | 主日志瘦身；审计用哈希校验 |
| **检索/反思限额** | `top_k` 上限、反思阈值、每 Agent 每窗口反思次数上限（v1 成本闸门同款） | 控制记忆事件量 |
| **相遇事件节流** | 仅记录**首次/超阈**共处（RELATION_ENCOUNTER），日常共处由 PLACE_MOVE 派生 | 避免 O(N²) 事件爆炸 |
| **内容压缩档案** | 进 prompt 的是「压缩档案」而非全量记忆（Agentopia 经验） | 降 token（成本），不影响日志审计 |

### 5.3 复现流程（已定，沿用 v1 §6.2 + 扩展分派）

```
replay(seed, engine_version, log) -> WorldState:
  校验哈希链 -> 初始状态 -> for record: state := apply_event(state, record)
apply_event 分派表 = v1 类型 ∪ §1.2 新增类型；遇到未知 type -> 立即报错（X4）
```
- **可复现口径（对齐 AR-C9）= 「同日志逐位一致」**：首跑含 LLM 判定（`LLM_JUDGMENT`，不保证跨跑一致）；`replay(log)` 对**同一日志**逐位一致（新增事件因携带完整 `payload` 而无需重算，C4），`metrics()` 两次字节相等。
- 记忆检索（`MEMORY_RETRIEVE`）已落日志，重放**不重算嵌入** → 规避嵌入模型不确定性对复现的污染。

### 5.4 嵌入与确定性（已定策略 + 待讨论）

- **铁律**：统计/重放**永不调用嵌入模型**；嵌入只由 Agent 决策路径产生，其结果（被选中的 mem_id 列表）落为 `MEMORY_RETRIEVE`。
- **可复现性（对齐 AR-C9）**：即便嵌入模型版本变化导致「同 query 不同排序」，重放折叠的是**历史选中结果**（`MEMORY_RETRIEVE` 落日志），故对**同一日志**世界演化逐位一致；跨跑一致本就不作要求（首跑含 LLM）。
- **待讨论 D7-6**：是否要求嵌入模型**固定版本并冻结**（写进 `engine_version`），以缩小「相同 seed 首跑」的差异面。建议：**固定并冻结**，记入 `engine_version`。

### 5.5 LLM 成本预算重算（应 AR-C5 / AR-D5，已定口径）

> **AR-C5**：v1 的「≤8 次 LLM/回合」是为**纯经济沙盒**标定，**生活层（计划/对话/反思/记忆）会显著抬高**，**不可直接沿用**。v1.1 必须按新模块重算。

**新增调用来源（生活层）**：`plan`（日/周计划）、`dialogue`（对话生成）、`reflect`（反思文本）、`decide_t2`（T2 决策）、`describe`（描述）。成本口径沿用 v1 模型并按生活层扩展：

```
每 Agent 每周调用 ≈ c_life·SLOTS_PER_WEEK + c_social·SLOTS_PER_WEEK
  SLOTS_PER_WEEK = 28（4 时段×7 日）
  c_life ≈ 1.0（0.5–3.0，待 T10 标定）  c_social ≈ 0.5（0.2–1.5）
  → 每 Agent 每周 ≈ 42 次（T1 为主；T2 于关键事件触发）
```

**按新规模 N=20 重算每回合量级（应 AR-D5，AR-§7.3）**：

```
E[Calls_round] ≈ N·(a·p_t1 + p2_near) / (SLOTS_PER_WEEK·ROUNDS_PER_SLOT) + ...
简化量级估算（取每 Agent 每周 42 次摊到 84 回合：≈0.5 次/Agent/回合）:
  N=10  → ≈ 5 次/回合   （沙盒）
  N=20  → ≈ 10 次/回合  （先跑通规模，当前目标）
  N=50  → ≈ 25 次/回合  （扩展目标）
```

- **容量/预算随 N 线性缩放**（本文与 00 §7.2 一致）：`LLM_BUDGET` 应按 N 设定，勿用固定常数。
- **成本闸门不变**：超限按优先级（濒死求生 > 投资/结盟 > 常规）降级 `T2→T1→T0`，写 `LLM_CALL(degraded=true)`，可审计。
- **待讨论 D7-5/D7-6**：`c_life/c_social` 与实际调用率需 T10 用日志回放标定；表中数值为量级估算。

### 5.6 拓扑与复现输入常数（应 AR-D2，待讨论）

- **AR-D2**：场所移动依赖拓扑。建议**将 `TOPOLOGY`（17×17 邻接/`travel_ticks` 常数矩阵）落为 **config 常数矩阵**（而非运行时按环层近似生成），以保证**跨环境、同日志可复现**（AR-C9）。
- 归属：**00-architecture §2.3** 定义拓扑与环层近似；本扩展要求其**固化为常数文件**并纳入 `engine_version` 指纹。
- **待讨论 XT-5**：`TOPOLOGY` 常数矩阵的落盘格式（JSON/CSV）与校验（对称性、三角不等式）。

### 5.7 货币总量与净值口径（⚠️ 属 v1 开放问题 Q1，**待用户确认**，非已定）

> 来源：econ 2026-10-09（银行/负债科目扩展）。**不得写成已定事实**。

- **v1 默认（现状）**：`M = Σ max(B_i, 0) + 税池`。
- **推荐口径（含银行库存项）**：`M_supply = Σ max(cash_i, 0) + 税池 + 银行库存(存款总额)`——**存款仍是货币、不销毁**；银行是**显式 money holder**。
- **净值口径扩展**：`E = cash + 存款 + Σ 资产估值 − (贷款本金 + 利息)`（涉及 02 生命周期净值 E 口径）。
- **状态**：属 **v1 遗留开放问题 Q1**（v1 默认未含银行库存项），**待用户最终拍板**；T11 汇总一并呈报。
- 守恒校验（v1 §5.9 式(1)）在采用推荐口径后须含 `银行库存` 项，否则会误报/漏报。

### 5.8 一等开关配置口径（`policy.production.enabled` 等，应 T124/T114/T115，已定）

> **性质**：属**配置口径**（非事件字段、非 canonical 参数值）。权威实现：`engine/hooks/__init__.py::assert_production_available` 与 `engine/hooks/production.py::_production_enabled`；配置声明：`config/policy.json`。

- **开关语义与默认值**：`policy.production.enabled`（runtime 覆盖 `config.production.enabled` 优先），**默认 `true`（行为不变）**。
  - **只控制「是否产生」**，**不删除事件契约**（`PRODUCE/CONSUME/...` 仍在 schema 中）。
  - 读取失败时按 `true`（保守：宁可 fail-loud）。读取优先级：runtime `config.production.enabled` > `policy.production.enabled` > 默认 `true`。

- **与 `assert_production_available` 的「三态 fail-loud 协同」**（防线不得削弱）：

  | `economy.enabled` | `production.enabled` | `apply_production` 状态 | 结果 |
  |---|---|---|---|
  | `true` | `true` | **已挂载** | **正常**：产出 `PRODUCE>0`，双账本守恒成立 |
  | `true` | **`false`**（显式声明关闭） | 任意（含未挂载） | **不触发 fail-loud**（有意消融，非事故）：`PRODUCE==0`、**双账本守恒仍成立**、`M(t)` 不穿负、**emit 一条 `DROPPED` 审计事件**（payload `{reason:"production_disabled", flag:"production_disabled"}`，`SYSTEM`/phase 4；`DROPPED` 为已登记的纯审计事件、恒等折叠）——即「开关生效」的**唯一查法 = 查 `DROPPED{flag=production_disabled}`**（非在既有事件上加字段） |
  | `true` | `true` | **未挂载 / 静默失效** | **fail-loud 必须 FAIL**（`RuntimeError`）——T35 同型「静默停摆」事故防线 |
  | `false` | 任意 | 任意 | 允许 no-op（既有行为）：4.1–4.3 全跳过 |

- **口径注记**：
  - 修改本节所述开关块**会改变 `engine_version` 指纹**（属预期，非数据损坏）；`config/policy.json` 的 `production`/`economy`/`lifecycle`/`social` 各块均纳入指纹。
  - **同族开关**：`social.enabled`（v2 社交发声档，T115）同属这一族——`false` 时整条 v2 社交发声通道在**生成侧短路**（不发 `INTENT.SOCIAL`、不物化 `GROUP_CREATED` → `MSG_*`/`GROUP_CREATED` 全为 0、无 `LLM_CALL(purpose=dialogue)`），**同样只控制「是否产生」、不删事件契约、不触发 fail-loud**。`economy.enabled`（T58）/`lifecycle.enabled` 同族。
  - **消融口径**：显式关闭必须与「静默失效」可区分——前者不 fail-loud 且发审计 flag，后者必须 fail-loud。这是本族开关的统一纪律。
  - **`exchange.enabled`（v2 交换原语档，T126/T129）同属这一族**：`policy.exchange.enabled`（runtime `config.exchange.enabled` 优先），**默认 `true`（行为不变）**。**语义 = 控制「agent↔agent 成交」原语**（**世界市场 `MARKET` 保留**，不受本开关影响）。`OFF` 时 life 不产生 `INTENT.ECON.TRADE/OFFER/ORDER_PLACE/ORDER_CANCEL`、engine 不挂 `apply_exchange/apply_contracts` → `EXCHANGE_SETTLED=0`、agent-as-seller 的 `MARKET_TRADE=0`、`CONTRACT_CREATED=0`（**Agent 间交易 = 0；世界市场成交仍在**）；**不删事件契约、不改守恒、不 fail-loud**，发审计 `DROPPED{reason:"exchange_disabled", flag:"exchange_disabled"}`（**「开关生效」唯一查法 = 查该 `DROPPED`**）。与 `economy.enabled` 的嵌套语义 = **AND**（`economy=false` 则 exchange 无意义）。
  - **`wake.enabled` / `wake.triggers.*`（v2 双时钟档，T263/T265）同属这一族**：`wake.enabled` **默认 `false`（行为不变）**；置 `true` 启用「个体决策节拍 = 事件驱动唤醒」。`wake.triggers.{W1..W10}` 为**逐因开关**（`W6` 默认 `true` 可关，供消融）；**世界结算节拍（round）不受本开关影响、始终不变**。**只控制「是否启用唤醒门控」、不删事件契约、不改守恒、不 fail-loud**；`engine_version` 指纹随本块变化（属预期）。

---

## 6. 与 v1 的兼容性（覆盖要求 6）

| 检查项 | 结论 |
|---|---|
| v1 事件类型/字段 | 不变（X1）；仅新增类型 |
| v1 hook 4.1–4.8 顺序/语义 | 冻结（X2）；生活层挂 Phase 3.5 |
| v1 经济/生命周期指标 | 口径冻结（X3）；容器迁 `metrics.econ/.lifecycle`，配适旧键名 |
| 日志外壳 / 哈希链 / 重放 | 不变（X4/X5）；新增类型入 `apply_event` 分派 |
| 守恒律（v1 §5.9） | 继续成立；生活层**不新增货币发行/销毁**（活动经济后果仍走 4.1–4.8 与 v1 事件） |
| 逐位一致（口径 AR-C9） | **同日志逐位一致**：整数货币、规范 JSON、全序 tie-break、定点输出；`replay(log)` 确定、`metrics()` 两次字节相等。首跑含 LLM 判定，**不保证跨跑一致**（提示 T10 判据采用「同日志」口径）。 |
| 新增不变量 | 见下 |

**新增不变量（并入 v1 §5.9 校验集）**：

```
(6) 记忆 append-only：MEMORY_WRITE 的 mem_id 全局唯一、只增不改；哈希链覆盖记忆事件
(7) 关系值域：RELATION_CHANGE 折叠后 w_dim ∈ [W_MIN, W_MAX]（由 persona 层定，越界报错）
(8) 场所合法性：PLACE_MOVE.to_place ∈ 合法场所集合；travel_ticks ≥ 0
(9) 日程一致性：ACTIVITY_STARTED 的 slot_id 必须存在于该 agent 的 SCHEDULE_PLANNED/REVISED
(10) 观测锚点存在：OBSERVATION.target_event_seq 必须指向已存在事件（否则拒绝）
(11) 统计无 LLM 判定：§4.10 的 llm_judged_metric_count == 0
(12) M(t) ≥ 0（v2 硬约束，应 `v2/01` §2.3/§6.2）：货币总量恒不为负；**代谢销毁时若 `Σcash < burn`，只销毁可得部分**（`burn × Σcash/burn` 的上限即 `Σcash`），**绝不允许总量为负**（修复 canonical「销毁无地板」bug）。
(13) 商品守恒（v2）：`ΣPRODUCE = ΣCONSUME + Σ库存 + Σ溢出 + Σ折旧耗损`（不成立 → 全回合回滚 + `ECONOMY_INVARIANT_VIOLATION`）。
```

**生活层新增不变量（应 06-life-layer §8.3，已并入；编号 L1–L8 沿用 06）**：

```
(L1) 关系值域：RELATION_CHANGE 折叠后 w_dim ∈ [W_MIN, W_MAX]；respect ∈ [0,100]（超界报错）
(L2) 需求值域：NEED_UPDATE.after ∈ [0,100]
(L3) 场所合法性：PLACE_MOVE.to_place ∈ 合法场所集，且匹配营业时段
(L4) 日程一致性：ACTIVITY_STARTED.slot_id 存在于该 agent 的 SCHEDULE_PLANNED/REVISED
(L5) 记忆 append-only：mem_id 全局唯一、只增不改；哈希链覆盖记忆事件（= 上 (6)）
(L6) 观测锚点：OBSERVATION.target_event_seq 指向已存在事件（= 上 (10)）
(L7) 统计无 LLM 判定：llm_judged_metric_count == 0（= 上 (11)）
(L8) 意图/事实分离：生活 hook 输出不含货币 delta（结构层校验）
```
> 上述 (L1)–(L8) 已冻结为 **W_MIN/W_MAX = −100/100、respect ∈ [0,100]、θ_dep = 20、ε = 20、ε_strong = 50**（来源 06 §10 回填表）。

---

## 7. 「已定」与「待讨论」汇总

**已定（v1.1 基线，可直接实现）**：
- 兼容原则 X1–X6；事件外壳；生活层额外审计字段 `day/slot/day_type/place`。
- 新增事件类型表（§1.2，结构与必带字段固定，枚举留待 06/07）。
- 新增 Phase 3.5 `LIFE` 与 L1–L7 hook 顺序、签名、幂等契约；4.1–4.8 冻结（§2）。
- 时间结构：**回合→时段→日→周**四层确定性派生（§3.1，按「模拟周」定稿，默认 1 周=7 日×4 时段×3 回合=84 回合）；工作日/周末参数化（§3.1）；**单小镇场景**（§3.3）；TIME_MARK 锚点（§3.4）。
- 生活/涌现指标公式（§4.1–§4.10），命名空间隔离。
- 日志体积模型与控制手段（§5）；重放分派扩展；嵌入不进统计（§5.4）；按周成本量级（§5.1）。
- 兼容性检查与新增不变量（§6）。

**待讨论（开放问题，交 Leader / 06/07 / 00-architecture 分册）**：
- **D7-1（已收窄）** 时间参数取值 `ROUNDS_PER_SLOT/SLOTS_PER_DAY/DAYS_PER_WEEK` 与工作日/周末 `DAY_TYPE_PARAMS` 数值——**以 `00-architecture.md`（T12）周时间结构为准**；未落盘前用 §3.1 默认（1 周=84 回合）。
- **D7-2** 是否采纳 Agentopia 式周四阶段（Plan/Contact/Activity/Review）。
- **D7-3** 各 need 维度的剥夺阈值 θ、关系强度阈值 ε/ε_strong、W_MIN/W_MAX 取值（persona 层定）。
- **D7-4** 社区发现算法选型（固定种子 Louvain vs 确定性 Girvan-Newman）。
- **D7-5** 各 α_*（每 Agent 每回合事件率）与 bytes_per_event、压缩比的 sandbox 实测标定（T10）。
- **D7-6** 是否冻结嵌入模型版本并写入 engine_version（建议冻结）。
- **XT-1** `mono_ts` 的 TIME_UNIT；**XT-2** 是否需 `6.5` 阶段处理「先买后消费」型活动。
- **XT-3** 记忆 `body` 是否入主日志（审计强度 vs 体积）——建议入侧存储 + 哈希。
- **XT-4（与 00-architecture 对齐项）** 场所枚举集、单小镇拓扑、`slot` 语义命名、三层架构的层间接口命名——**待 `00-architecture.md` 落盘后对齐**，差异记此。

---

## 8. 待补对齐（与 00-architecture / 06 / 07 分册）

**已与 `00-architecture.md`（T12）对齐（2026-10-09）**：
- **时间结构**：00 §3 与本文 §3.1 **完全一致并冻结**（1 周=7 日×4 时段×3 回合=84 回合；`ROUNDS_PER_SLOT≥3` 约束 AR-D4）。XT-4 时间项关闭。
- **场所**：`place` 枚举以 00 §2.2 为准（17 处，`residence/farm/.../gate`）；本文 §3.3 单小镇声明一致。
- **层间接口**：00 §4 的五条接口（IF-1..IF-7）与意图分类（`INTENT.*`）与本文 §2 hook 契约一致；生活层仍挂 Phase 3.5。
- **AR-C1**：`INTENT_REJECTED` 已回补（§1.2 H）。
- **AR-C8**：`LLM_JUDGMENT`（冻结判定）+ `NARRATIVE`（叙事纯输出）已回补（§1.2 I），含 IF-2b/IF-6/IF-7 接口对应与「三事件分列」「重放不重问 LLM」硬约束。
- **AR-C9**：可复现口径已改为**「同日志逐位一致」**（§0 X5 / §5.3 / §5.4 / §6），首跑含 LLM 不保证跨跑一致；已在 §6 提示 T10 判据采用同口径。
- **T9-C4**：已登记 `metrics.emergence_soft` 命名空间（§4.0），**只作敏感性分析、不进判定与门禁**，`contains_llm_judgment=true` 并排除在门禁指标集外。
- **AR-C5 / AR-D5**：已新增 §5.5「LLM 成本预算重算」，按生活层与新规模 **N=20** 重算（≈10 次/回合；N=10→≈5、N=50→≈25），注明容量/预算随 N 线性缩放，不沿用 v1「≤8/回合」。
- **AR-D2**：已新增 §5.6「拓扑与复现输入常数」，建议 `TOPOLOGY` 落 config 常数矩阵并纳入 `engine_version`。
- **WB-C1**：已登记 `SKILL_PRACTICE / SKILL_LEVEL_UP / SKILL_OUTPUT`（§1.2 J），命名与 T14 事件谱系对齐。
- **WB-C3**：已登记 `metrics.wellbeing`（确定性、入门禁）与 `metrics.wellbeing_soft`（含 LLM 冻结判定、只作描述与敏感性分析、出门禁），与 `emergence_soft` 同等处理（§4.0）。
- **T14-C1/C2/C5**：已登记协商/评价/冲突事件（§1.2 K）：`OFFER_CREATED/ACCEPTED/REJECTED/COUNTERED/EXPIRED`、`SCORE_POSTED/RANKING_EMITTED`、`CONFLICT_STARTED/RESOLVED`；并确认 `INTENT_REJECTED`(规则拒绝) 与 `OFFER_REJECTED`(社交婉拒) 语义分离。`WELLBEING_ALERT` 不新增（用 `STATE_CHANGE`）。
- **T14-C3（已裁定·已登记）**：`DEPOSIT/WITHDRAW`/`INTEREST_PAID` 已登记（§1.2 L，phase=4.2，不入流速/I_eff）；配套 `M_supply`（含银行库存）与净值 E 口径记入 §5.7，**属 Q1、待用户确认**。
- **NT-C1（已登记）**：`NARRATIVE` 补可选元数据字段（§1.2 I，只增不改，不新增事件类型）。
- **NT-C2（已登记）**：`metrics.narrative` 非判定命名空间（§4.0），与 `emergence_soft`/`wellbeing_soft` 同类，不进判定与门禁；`narrative_selection` 为确定性侧产物。`LLM_CALL(purpose="describe")` 与判定类分列不冲突。
- **R1–R5（已登记，应 v1.2/03 NT-C3）**：R1 可感知事件带 `place`（§3.5）；R2 `PERCEPTION_SCOPE` config 表（§3.5，版本入 engine_version）；R3 `GROUP_CREATED`(+可选 JOINED/LEFT)（§1.2 M）；R4 `MSG_*` 转述必带 `refs[]`（§1.2 F）；R5 `OBSERVATION` 语义澄清（§1.2 F）；R6 `LLM_JUDGMENT.parties` 复用（§1.2 M）。
- **T26-D1–D4（已裁定并落定，§3.5）**：D1 公开板=全员存活；D2 residence 私密=participants_only；D3 global 白名单可配、默认仅 `AGENT_DIED`；D4 一阶「听说」标 spec=true、永不入 visible_events。

**v2 P1 事件 schema 登记（应 T90，2026-10-10，只增不改）——变更清单**：

| 类别 | 变更 | 落点 |
|---|---|---|
| **新增事件（商品族 4）** | `PRODUCE` / `CONSUME` / `DEPRECIATE` / `PRODUCE_OVERFLOW` | §1.2 O |
| **新增事件（契约族 4）** | `CONTRACT_CREATED` / `CONTRACT_FULFILLED` / `CONTRACT_VIOLATED` / `CONTRACT_EXPIRED` | §1.2 P |
| **新增事件（投票 1）** | `VOTE_CAST` | §1.2 P |
| **新增事件（社会 2）** | `GROUP_DISSOLVED`、`PUBLIC_REACTION` | §1.2 Q |
| **字段扩展（复用事件）** | `GROUP_CREATED.kind/scope_place`、`OFFER_CREATED.kind/terms/enforceable/rule_ref`、`NORM_ADOPTED.scope/effect` | §1.2 Q |
| **新增不变量** | `M(t) ≥ 0`（代谢只销毁可得部分）、商品守恒 | §6 式(12)(13) |
| **字段语义登记** | 商品族 `qty` 的 **milli-unit** 口径（`1 unit = 1000 milli-unit`）+ `base_rate` 定点值 + `state.inventory` 同单位/入 state_hash/sorted | §1.2 O.1 / O.2 |
| **配置口径登记** | 一等开关 `policy.production.enabled`（默认 true、只控「是否产生」）+ 三态 fail-loud 协同（显式关闭不 fail-loud/静默失效必 FAIL）+ `social.enabled` 同族 | §5.8 |
| **新增事件（v2 交换，T126/T129）** | `EXCHANGE_SETTLED`（4.1，多腿双边原子交换，零和）+ `MARKET_TRADE.channel∈{orderbook}`（允许 seller∈Agent）+ 一等字段 `counterparty` + 意图 `ORDER_CANCEL` + 统计口径（`distinct_sellers_excl_world`/agent↔agent 占比） | §1.2 R |
| **配置口径登记（v2 交换）** | `policy.exchange.enabled`（默认 true，同开关族；OFF→Agent 间交易归零 + `DROPPED{flag=exchange_disabled}`，不 fail-loud） | §5.8 |
| **新增事件（v2 双时钟，T263/T265）** | `WAKE`（phase 0，每被唤醒 Agent 一条）+ `IDLE`（每回合一条全局聚合）；**无 `DUE`**（到期经 `WAKE` 承载）；config `wake.enabled`(默认 false)/`wake.triggers.*` | §1.2 S + §5.8 |
| **新增事件（v2 世界导演+事件制造机，T238）** | `WORLD_DIRECTIVE` / `WORLD_GROUP_EVENT`（kind 14 值，≠`GROUP_*`）/ `WORLD_DIRECTIVE_REJECTED` / `FORGE_FIRED`（审计-only）；新增一等 actor `"DIRECTOR"`；三条保底落成字段（`directed` / `mechanism_id`+`dose`+`dose_curve` / `effective_from_round≥issued_round`）；**每字段标「装配点」** | §1.2 T |
| **字段主体口径（T248）** | `agent_id`（及 `actor`/`subject`）**可含非 Agent 主体**（`MARKET`/`BANK`/`WORLD`/`TAX_POOL`）——**登记为已知例外**；消费方须用单一真源 `contracts.actors` 守卫 | §1.2 U |
| **新增事件（v2 睡眠/记忆/人格，T224）** | `SLEEP_STARTED/SLEEP_COMPLETED`、`MEMORY_CONSOLIDATE/MEMORY_FORGET`、`PERSONA_DRIFT`（`PERSONA_FINGERPRINT` 为快照非事件）+ 统计 `metrics.life.memory/persona` | §1.2 S |

> **合计**：新增事件 **11** 类（商品 4 + 契约 4 + 投票 1 + 社会 2）；字段扩展 **3** 事件；不变量 **2** 条；字段语义登记 **1** 项（商品族 `qty` milli-unit 口径）。**均只增不改**，与既有 66 类不冲突；G7 对既有日志仍通过（新增类型旧日志不出现、可选字段被容忍）。**引擎实现**（`engine/events.py` EVENT_TYPES + `replay.apply_event` 折叠器 + `apply_production()/apply_contracts()` hook）由 v2 实现阶段（econ-dev T91 等）落地，本任务只出 schema。

**已由 06-life-layer §10 回填的取值枚举（2026-10-09，已定）**：
- `need.dim[]` = `energy, satiety, social, esteem, mastery, leisure`（6 维，0–100，θ_dep=20）。
- `activity_type[]` = `work, learn, socialize, leisure, self_care, civic, trade, rest`（8 类），及 → `place.affordances` 映射。
- `RELATION_CHANGE.dim` = `affinity[-100,100], trust[-100,100], respect[0,100]`；`W_MIN/W_MAX=−100/100`；`ε=20, ε_strong=50`。
- `θ_reflect=150`；`WEEK_PHASES` = PLAN(day0 morning)/CONTACT(day0–4)/ACTIVITY(day0–6)/REVIEW(day6 evening·night)。
- `tag` 来源：内容层（M6/M8）从消息/活动产出 `tag_hints`；`valence ∈ {-1,0,1}`。
- `NORM rule_ref` 格式：`norm:{scope}:{predicate}:{threshold}`。

**仍待 07-emergence / 13-wellbeing 细化的项**：`metrics.emergence.*` 判定指标与 LLM 描述分界（T9 已给 D/F/K 分级）、WBV 各维精确口径（T15/06 §7.4）。

---

*（本文件为 v1.1 扩展草案；核心目标是「不动 v1、只做加法」，并把生活与涌现层的观测保持为「确定性、可重放、不依赖 LLM 判定」。待讨论项交 Leader 汇总与 06/07 分册回填。）*
