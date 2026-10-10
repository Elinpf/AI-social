# 03 · 「角色视角」可见性依据核查（NT-C3）

> 文档类型：跨层一致性核查（观测方法论 × 叙事层 × 生活层）｜ 作者：emergence-observer-designer（涌现观测层设计专家）
> 状态：v1.2 核查报告（供 Leader / T8 汇总；标注【已覆盖】/【缺口】/【待讨论】）
> 上游必读（已核）：
> - `v1.1/17-narrative-layer.md` §4.3 角色视角 Character POV、§3.3 防幻觉、§9.3 NT-C3
> - `v1.1/07-emergence-observation.md`（T9：铁律 R1–R7、D/F/K 分类、只读契约、命名空间）
> - `v1.1/06-life-layer.md`（T7：§1.3 端到端、§1.4 私有状态、§3 M2 记忆、§5.3 昼夜与偶遇）
> - `v1.1/00-architecture.md`（T12：IF-1 `perceive`、IF-4 只读契约、§1.5 三条角色带、§5.5 冻结判定）
> - `v1.1/08-engine-stats-extension.md`（T8：§1.2 事件 schema、§2.3 L6 `write_memories`）
> - `v1.1/12-event-lineage.md` / `15-event-census-spec.md`（`MSG_DM(visibility=private)` 用法）

---

## 0. 结论速览（TL;DR）

| 问题 | 结论 |
|---|---|
| **`OBSERVATION` + `MSG_*` 是否充分？** | **不充分**。`OBSERVATION` 是 **salience 门控的「显著感知」样本**（T8 §2.3：L6 按确定性 salience 规则落 `MEMORY_WRITE / OBSERVATION`），**不等于「Agent 所见一切」**；且**缺「可见性分类」与「视野（co-location）规则」的显式定义**、**缺群组成员时序**、**`MSG.refs` 来源不可保证**。 |
| **能否确定性重算？** | **能**——只要补上**一张 config 可见性分类表 + 占用时间线（复用现有事件）+ 群组成员事件 + refs 约束**。判定函数**纯只读日志、`llm_calls==0`**，不改变内核、**不新增写入型事件**（群组事件为确定性小型补充）。 |
| **角色视角模板能否按现设计实现？** | **能，但有前置**：须先落 §4 的 **R1–R4 最小补齐**（否则 POV 会遗漏「亲眼所见但未被 OBSERVATION 记录」的信息，或将「听说」误当「亲历」）。补齐后 POV 可严格受限、可复现。 |
| **一句话** | 把 POV 的可见性判据从「读了哪些 `OBSERVATION`/`MSG`」升级为「**由日志+config 确定性推导的 `visible_events(agent)`**」；`OBSERVATION` 退化为**显著度证据**，而非可见性全集。 |

---

## 1. 可见性来源清单（Agent「知道一件事」的全部途径）

> 逐条标注：**判定依据** / **是否可由日志确定性重算** / **状态**。所有条目的判定**不得回退到 LLM**（T9 R1/R2）。

| # | 途径 | 判定依据（确定性） | 可重算？ | 状态 |
|---|---|---|---|---|
| **S1** | **直接参与**（agent 是 actor） | 事件 `actor` / `participants[]` 含该 agent | ✅ | 【已覆盖】 |
| **S2** | **视野同场**（事件发生地 = agent 当时所在地） | 占用时间线（`PLACE_MOVE/ARRIVED` 折叠）+ 事件 `place` + 可见性分类 | ⚠️ 规则未定义 | **【缺口-1】** |
| **S3** | **公开板** `MSG_PUBLIC` | 全体存活 Agent 可见（`global`） | ✅（需定义可见范围） | 【已覆盖】 |
| **S4** | **私聊** `MSG_DM` | `from/to`；已有 `visibility=private` | ✅ | 【已覆盖】 |
| **S5** | **群组** `MSG_GROUP` | 该时刻 `group.members` | ❌ 无成员时序 | **【缺口-2】** |
| **S6** | **显著感知** `OBSERVATION` | `observer` 字段 | ✅（但**门控子集**） | **【缺口-3】（被高估）** |
| **S7** | **口述/二次传播**（听说） | 收到的消息 `refs[]` 闭包指向原始事实 | ⚠️ `refs` 不保证填充 | **【缺口-4】** |
| **S8** | **记忆写入来源** | `MEMORY_WRITE.source_event_seq` | ✅ | 【已覆盖】 |
| **S9** | **记忆检索命中** | `MEMORY_RETRIEVE.selected_mem_ids` → 其 `source_event_seq` | ✅（命中已落日志，T8 C4） | 【已覆盖】 |
| **S10** | **反思产物**（传递闭包） | `MEMORY_REFLECT.triggered_by_mem_ids` → `produced_mem_id` | ✅ | 【已覆盖】 |
| **S11** | **冻结定性判定** | `LLM_JUDGMENT.parties` 含该 agent | ✅（读冻结，标 `frozen_llm`） | 【已覆盖】（F 类） |
| **S12** | **谈话中的对话内容**（DM/群组正文） | `MSG_*` 正文（侧存储） | ✅（投递可见） | 【已覆盖】 |

> **要点**：S1/S3/S4/S8–S11 已可由日志重算；**S2/S5/S6/S7 是四个缺口**（其中 S6 是「语义被高估」，非缺失）。

---

## 2. 充分性判定与最小补齐建议

### 2.1 缺口-1：视野（co-location）规则未定义

- **现状**：`IF-1 perceive(agent)→WorldView`（T12 §4.1）只抽象说「可见事件」，**未给确定性定义**；`OBSERVATION` 又只覆盖显著子集。→ POV 若要「亲眼所见」，缺规则。
- **可复用**：占用时间线可**完全由日志重建**——`PLACE_MOVE / PLACE_ARRIVED`（T8 §1.2-A）给出 `location(agent, t)`；生活事件必带 `place/day/slot`（T8 §1.1）；场所营业时段在 `config/places.json`（T7 §5.2）；相遇规则已按「同 `place` 同 `round`」定义（T7 §5.3），说明 co-location 是可判的。
- **最小补齐 R2（**config 表，无新事件**）**：新增确定性 **可见性分类表** `PERCEPTION_SCOPE`：
  ```
  PERCEPTION_SCOPE: { event_type -> visibility_class }
  visibility_class ∈ { global, place_local, participants_only, subject_only, private }
  例：MSG_PUBLIC=global；MSG_DM=private；MSG_GROUP=members；ACTIVITY_*=place_local；
      PLACE_MOVE=place_local；TRANSFER/MARKET_TRADE=participants_only；
      AGENT_DIED/STATE_CHANGE=global（重大事件全镇可见，可配）；LLM_JUDGMENT=parties
  ```
  落 `config`，版本写入 `engine_version`，保证可复现（同 T12 AR-D2 对 `TOPOLOGY` 的处理）。
- **判定**（纯函数，见 §3）：`e.scope==place_local ∧ e.place==location(agent,e.round)`。

### 2.2 缺口-2：群组成员时序缺失

- **现状**：v1 `Group{group_id, members, created_round}` 有成员表，但 v1.1 事件表**无** `GROUP_*` 成员变更事件（08 §1.2 仅 `MSG_GROUP`）。→ 若成员可变，`MSG_GROUP` 的可见对象无法按时间重算。
- **最小补齐 R3（**新增小型确定性事件**）**：
  - 首选：`GROUP_CREATED{group_id, members[], created_round}` + `GROUP_JOINED{group_id, agent_id, round}` + `GROUP_LEFT{...}`；
  - 若组队不可变（小镇规模小、组少），**退化为** `GROUP_CREATED{members}` 一次成型（v1 原义），即可省 2 类事件。
- **判定**：`agent ∈ members(group_id, e.round)`。

### 2.3 缺口-3：`OBSERVATION` 语义被高估（关键澄清）

- **现状**：`OBSERVATION` 在 L6 由 **确定性 salience 规则**产出（T8 §2.3），T9 也把它当「传播图边锚点」。它**是「显著感知」的样本**，**不是「Agent 所见一切」**。叙事层 §4.3 若把 POV 严格等同于「读 `OBSERVATION`」，会**漏掉**「A 亲眼看到 B 与他人争执但该事件 salience 低于门控」这类 POV 应有内容。
- **处置 R5（**语义澄清，无新事件**）**：明确 **POV 可见性以 §3 的 `visible_events()`（含 S2 视野判定）为准**；`OBSERVATION` 降级为**显著度/注意力证据**（可作 POV 的「重点」而非「全集」）。**不改变 `OBSERVATION` 现有 schema 与传播口径**（不与 T9/T8 冲突）。

### 2.4 缺口-4：`MSG.refs` 来源不可保证（二次传播链）

- **现状**：传播边由 `OBSERVATION.target_event_seq` 与 `msg.refs` 共同构建（T8 §4.4）。但**自由转述**（「听说镇上要办事」）未必携带 `refs`；正文（LLM 内容）**不可作为确定性事实依据**（H-1）。
- **最小补齐 R4（**字段约束，无新事件**）**：
  - **转发/转述类**消息**必须**携带 `refs[]`（指向被转述的 `msg_id` 或事实 `event_seq`）；
  - 无法确定来源的消息 `refs=[]` → POV 渲染时标 `spec=true`，表述为「**听说（未经核实）**」，**不进入「亲历」集合**。
- **判定**：`heard_closure(agent)` = 对 agent 收到的消息，沿 `refs[]` 反向闭包到达的事实集合；**仅作「听说」**，非亲历。

### 2.5 其余可复用（无需补齐）

- **S3 公开板可见范围**：定义为「`e.round` 时刻存活的 Agent」（或「在镇内」，二选一口径，**待讨论 T26-D1**）。
- **S8–S10 记忆链**：`MEMORY_WRITE.source_event_seq`、`MEMORY_RETRIEVE.selected_mem_ids`、`MEMORY_REFLECT.triggered_by_mem_ids` 均已落日志，直接折叠即可（T8 C4：重放不算嵌入）。
- **S11 冻结判定**：`LLM_JUDGMENT.parties` 已存在（T12 §5.5），可直接作 subject 可见依据，标 `frozen_llm`。

---

## 3. 确定性保证：判定函数签名

> 全部**纯函数、只读 `EventLog` + config**、`llm_calls == 0`、全序 tie-break、可逐位重放（T9 R1/R2、T12 IF-4）。**无 LLM 参与**。

```python
# 占用时间线（由 PLACE_MOVE / PLACE_ARRIVED 折叠；初始 = residence）
location(agent, t) -> place_id            # 纯函数，t 为 round
place_open(place, slot) -> bool           # 来自 config/places.json（T7 §5.2）

# 单事件对单 Agent 的可见性（deterministic predicate）
perceived(agent, e, cfg) -> bool:
    cls = cfg.PERCEPTION_SCOPE[e.type]                 # §2.1 R2
    return (
        cls == "global"                                # S3 公开板/重大事件
        or (cls == "place_local"                       # S2 视野同场
            and e.place == location(agent, e.round)
            and alive(agent, e.round))
        or (cls == "members"                           # S5 群组（ADR：R3）
            and agent in members(e.group_id, e.round))
        or (cls == "private"                           # S4 私聊
            and agent in {e.from_, e.to})
        or (cls == "participants_only"                 # S1 直接参与
            and agent in (e.participants or [e.actor]))
        or (cls == "subject_only" and agent in {e.actor, *e.subject})
        or (e.type == "LLM_JUDGMENT" and agent in e.parties)   # S11
    )

# 亲历可见事件集（含记忆链）
visible_events(agent, log, T, cfg) -> set[seq]:
    direct = {e.seq for e in log.up_to(T) if perceived(agent, e, cfg)}       # S1/S2/S3/S4/S5/S6/S11
    mem    = {mw.source_event_seq for mw in MEMORY_WRITE(agent)}             # S8
             ∪ {src(mid) for mid in MEMORY_RETRIEVE(agent).selected_mem_ids} # S9
             ∪ closure({mr.triggered_by_mem_ids for MR in MEMORY_REFLECT(agent)})  # S10
    return direct ∪ mem

# 「听说」集（二次传播；非亲历，POV 须标 spec=true）
heard_events(agent, log, T, cfg) -> set[seq]:
    # 对 agent 收到的 MSG（DM/组/公开），沿 refs[] 反向闭包到达的事实
    return refs_closure( messages_received_by(agent) )

# POV 过滤（供 17 §4.3 filter_by_visibility）
filter_by_visibility(atoms, agent, log, T, cfg) -> (keep_direct, keep_heard, dropped):
    vis  = visible_events(agent, log, T, cfg)
    heard = heard_events(agent, log, T, cfg)
    keep_direct = [a for a in atoms if set(a.anchors) ⊆ vis]
    keep_heard  = [a for a in atoms if set(a.anchors) ⊆ heard and set(a.anchors) ⊄ vis]  # 标 spec=true
    dropped     = [a for a in atoms if set(a.anchors) ⊄ (vis ∪ heard)]
    return keep_direct, keep_heard, dropped
```

- **可复现**：`location/ perceived / visible_events / filter_by_visibility` 仅依赖 `(log, T, cfg)`；两次调用**逐位一致**（规范 JSON、键排序、整数/枚举比较）。
- **审计**：POV 报告附 `visible_event_digest`（`visible_events` 的规范哈希）与 `scope_table_version`，使「此 POV 依据哪些可见事件」可核验。
- **与 `OBSERVATION` 的关系**：`visible_events ⊇ OBSERVATION(agent)`；`OBSERVATION` 作为**显著度子集**用于选片重点，**不再作为可见性全集**。

---

## 4. 对 T8 的最小补齐建议（汇总，供登记）

| 编号 | 类型 | 建议 | 影响面 | 是否必须 |
|---|---|---|---|---|
| **R1** | 字段（复用/确认） | 确认所有**可感知**事件带 `place`（生活事件已带，T8 §1.1）；`MSG_PUBLIC`/重大事件标 `place=null` 且 `scope=global` | 使 S2 可判 | 必须 |
| **R2** | **config 表（无事件）** | 新增 **`PERCEPTION_SCOPE`**（event_type→visibility_class），版本入 `engine_version` | 可见性判定核心 | 必须 |
| **R3** | 事件（小） | 新增 `GROUP_CREATED`（+可选 `GROUP_JOINED/LEFT`）；或明确「组队不可变」并冻结 `members` | 使 S5 可判 | 必须（若成员可变） |
| **R4** | 字段约束 | `MSG_*` 的 `refs[]`：**转发/转述类必填**；缺省则 POV 标「听说（未核实）」 | 使 S7 可判、防幻觉 | 必须 |
| **R5** | 语义澄清（文档） | 明确 `OBSERVATION` = **显著感知样本**，POV 可见性以 `visible_events()` 为准 | 防误用 | 建议 |
| **R6** | 复用确认 | `LLM_JUDGMENT.parties` 作为 S11 依据（标 `frozen_llm`） | 无需新增 | 复用 |

> **不改动**：`OBSERVATION`/`MSG_*` 现有 schema 与传播口径（T8 §4.4）、`RELATION_ENCOUNTER` 定义（T7 §5.3）、内核 4.1–4.8（T12 X2）。**不新增写入型事件**除 R3 的小型群组事件（确定性）。

---

## 5. 已覆盖 / 缺口 / 待讨论 汇总

**【已覆盖】**（可直接用于 POV）
- S1 直接参与、S3 公开板、S4 私聊（`visibility=private`）、S8/S9/S10 记忆链、S11 冻结判定（标 `frozen_llm`）、S12 对话正文。
- 占用时间线（`PLACE_MOVE/ARRIVED`）、场所营业时段（config）、相遇共处（`RELATION_ENCOUNTER`）。

**【缺口】**（须补齐方可严格实现 POV）
- **缺口-1** 视野 co-location 规则未定义 → **R2**（config 可见性表）。
- **缺口-2** 群组成员时序缺失 → **R3**（`GROUP_*` 或冻结成员）。
- **缺口-3** `OBSERVATION` 被当作可见性全集（实为 salience 门控子集）→ **R5**（语义澄清）。
- **缺口-4** `MSG.refs` 来源不可保证 → **R4**（转述必带 refs；否则标「听说」）。
- **缺口-5**（字段）确认可感知事件普遍带 `place` → **R1**。

**【待讨论】**
- **T26-D1** 公开板可见范围 =「全员存活」还是「在镇内（`gate` 外不可见）」？建议默认「全员存活」（单小镇、闭合），长窗再细化。
- **T26-D2** `residence` 内「私密对话」的可见类：是 `place_local`（同屋可见）还是 `participants_only`（仅对话双方）？建议 `participants_only`。
- **T26-D3** 「重大事件全镇可见」的白名单范围（如 `AGENT_DIED/NORM_ADOPTED` 是否 `global`）？建议可配、默认仅 `AGENT_DIED` 为 `global`。
- **T26-D4** 归一阶「听说」是否计入 POV 的「亲历」旁注（默认：计入但标 `spec=true`，永不计入 `visible_events`）。

---

## 6. 结论（可执行）

1. **`OBSERVATION` + `MSG_*` 单独不充分**，不能作为 POV 的严格可见性依据。
2. **补 R1–R5 后可行**：核心是 **`PERCEPTION_SCOPE` 配置表（R2）+ 占用时间线（复用）+ 群组成员事件（R3）+ `refs` 约束（R4）**；判定函数见 §3，**纯只读、可重算、`llm_calls==0`、无 LLM 判定**。
3. **角色视角模板可按设计实现**（17 §4.3 的 `filter_by_visibility` 落到 §3 函数）；「亲历 vs 听说」以 `visible_events` / `heard_events` 严格二分，`spec=true` 标注，符合 17 §3.3 防幻觉与 T9 R6（叙事不回写、不参与判定）。
4. **对 NT-C3 的答复**：**不充分 → 需补**；补齐为**配置表 + 小型确定性事件 + 字段约束**，不破坏内核、不引入 LLM 判定。

---

*（本文件为 v1.2 角色视角可见性核查报告；核心：把「谁能看到什么」变成可从日志与 config 确定性重算的 `visible_events()`，`OBSERVATION` 退为显著度证据。补齐建议交 T8 汇总登记。）*
