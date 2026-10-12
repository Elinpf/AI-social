# 可见性语义定口径（D2 `subject` / D3 `members`-`actor`）—— 08 权威

> 作者：仿真引擎与统计架构师（sim-engine-stats-architect）｜ 任务：T266（T264 关键路径）
> 上游证据：`v2/t264-visible-events-divergence.md`（kernel-dev 步骤1）｜ 权威：`v1.1/08-engine-stats-extension.md §3.5`、`code/contracts/visibility.py`（T264 抽出的唯一真源）
> 状态：D2/D3 **已裁定**（下）；D1 已由 T137 裁定、不再重复；G1–G3 为 Q4 扫描出的同类缺口（报告，供排期）

---

## 0. 结论速览

| 项 | 裁定 | 依据 |
|---|---|---|
| **D1** `OFFER_CREATED` 分档 | `to==[]`→`global`；定向→`private` | **已由 T137 固化**（engine 为准）；life 落 `place_local` 是不可见 bug |
| **D2** `payload.subject` 是否纳入可见性 | **不纳入**（`subject_only`/`private` 均**不含** `subject`） | 「subject=关于谁」≠「当事人」；纳入会泄漏 actor 私有认知 |
| **D3** `members` 是否含 `actor==agent_id` 回退 | **含**（`members = 群组成员 ∪ {actor}`） | 跨 class 一般规则「当事人对自己发起的事件总可见」 |

→ D2/D3 **均以 engine 现行语义为准**；`code/contracts/visibility.py::visible()`（T264 唯一真源）**当前已是该语义**，故**无需改代码**，只需登记 + 保证三处只调用它。

---

## 1. 元原则：可见性 = 「谁该知道发生了什么」

- **可见性回答的是「是否与某事有当事人关系」，不是「是否被提及」**。`perception`（感知）与 `memory`（记忆写入，L6 `write_memories`）**必须用同一可见性**——否则「A 感知到、但记忆未写入」或反之，叙事/传播/统计三处口径立刻分叉（T264 报告的 D1 后果即此类）。
- 判定字段族（**当事人字段**）：`agent_id`（主体本人）、`observer`（观察者本人）、`from`/`to`/`to[]`/`participants`（交互方）、`actor`（发起者）。**`subject` 不在其中**（见 §2）。

---

## 2. D2 裁定：`subject` **不纳入**可见性

**语义**：`payload.subject` = 「该事件**关于谁** / 被指向 / 被谈论 / 注意力对象」——它是**他者视角的宾语**，**不是事件的当事人或作者**。

**理由（两条，缺一不可）**：
1. **防私有认知泄漏**：带 `subject` 的事件多为 **actor 的私有认知**——如 `MEMORY_WRITE{agent_id=A, subject=C}`（A 记了一条关于 C 的记忆）、A 对 C 的 `OBSERVATION`/`LLM_JUDGMENT`。若把 `subject` 纳入可见性，则 **C 会看到 A 的私有记忆/观察/判定**（"A 在背后记了 C"→ C 直接读到），违反「谁该知道」。
2. **感知/记忆一致性**：engine 现行不含 `subject`；life 曾含 → 同一 `NEED_UPDATE{agent_id=X, subject=C}` 对 C「life 可见、engine 不可见」。二者必须一致，否则记忆链与感知分叉。

**裁定**：以 **engine 现行（不含 `subject`）**为准；life 旧实现含 `subject` 属**越权泄漏**，纠正为不含。

**影响面**：
- 受影响事件（class ∈ `subject_only`/`private` 且携带 `subject`）：`MEMORY_WRITE`/`MEMORY_RETRIEVE`/`MEMORY_REFLECT`/`OBSERVATION`/`NEED_UPDATE`/`SCHEDULE_PLANNED`/`SCHEDULE_REVISED`/`GOAL_*`/`LLM_CALL` 等。
- 消费方：`orchestration.KernelAdapter.perceive`（agent 感知）、`life.settlement L6 write_memories`（记忆）——**均须走单一真源**。
- 净效果：把 life 路径对 `subject` 的可见性**收紧**到 engine 语义（不再泄漏 actor 私有认知）；对既有"当事人本人（`agent_id`/`observer`/`from`）"的可见性**不变**。

---

## 3. D3 裁定：`members` **含 `actor==agent_id` 回退**

**语义**：`members` class = 「**群组成员**可见」；**并含**一般规则「**当事人（`actor`）对自己发起的事件总可见**」。

**理由**：这是一条**跨 class 的一般规则**——`subject_only` / `private` / `participants_only` **均已**含 `actor` 回退。若 `members` 独独不含，则出现反直觉缺口：**「自己发到群里的消息（`MSG_GROUP`, actor=自己）自己看不见」**。`members` 语义 = 群组成员 **∪** {发起者}，二者不冲突、可叠加。

**裁定**：以 **engine 现行（含 `actor` 回退）**为准；life 旧实现不含 → 纠正为含。

**影响面**：`members` class 事件（`MSG_GROUP` 及未来 class=members 的事件）对 **actor 始终可见**（无论 actor 是否落在 group 成员快照内）。修掉"自发群消息对发送者不可见"缺口；对普通成员可见性**不变**。

---

## 4. Q3：在 `perception_scope.json` 如何表达，使三处从「同一处」派生

**结论**：**不把 D2/D3 的逐字段规则塞进 `perception_scope.json`**（那会把"类语义"挤进"事件→类 映射表"，并需改 loader/schema）。分层如下：

| 层 | 内容 | 位置 |
|---|---|---|
| **映射** | `event_type → visibility_class`（+ `default_visibility_class`） | `config/perception_scope.json`（唯一真源；**保留**） |
| **类语义** | 每个 `visibility_class → 判据字段集`（含 **D2 不含 subject**、**D3 含 actor**） | **08 §3.5 权威表** + **唯一实现** `contracts/visibility.py::visible()` |
| **动态特例** | `OFFER_CREATED`：`to==[]`→`global`，否则 `private`（T137） | 08 显式规则 + `contracts/visibility.py`（**登记为已知特判**，见下） |

- **三处（`engine/perceive`、`life/visibility`、`KernelAdapter.perceive`）只允许调用 `contracts/visibility`，不得内联**（T264 已收敛；08 §3.5 已写死"单一来源"）。
- **`perception_scope.json` 增补**（非破坏性，仅注释性真源）：
  - `_class_semantics`：逐 class 列出判据字段集（与 08 §3.5 表一致，便于人读/机读对照，**不改变机器行为**）；
  - `OFFER_CREATED` 备注：其 class 由**动态覆盖**决定（表内不写死；或写 `"private"` 作默认 + 动态提升），**消除"表里没有、代码特判"的暗规则**。
- ⚠️ 改 `perception_scope.json` 会变 `engine_version` 指纹（属预期）→ 与 **T236 重冻**联动。

---

## 5. Q4：扫描全部 `visibility_class`，同类未覆盖分支（G1–G3）

`scope` 现有 6 类：`global / place_local / private / members / participants_only / subject_only`。逐类扫描：

| 编号 | 缺口 | 说明 | 建议 |
|---|---|---|---|
| **G1** | `place_local` **无 `actor` 回退** | `place_local` 仅判 `p.place == location`。**缺 `place` 或 location 未同步时，本人也看不到自己的事件**（与 D3 的「当事人总可见」一般规则不一致；`OFFER_CREATED` 无 `place` 落此即踩中）。 | **建议加 `actor==agent_id` 回退**（与其它 class 一致）；**影响面大**（所有 place_local 事件对 actor 增加可见）→ 需 Leader/影响评估后实施 |
| **G2** | **scope 表未覆盖 v2 新增事件** | `EXCHANGE_SETTLED`/`CONTRACT_*`/`DEPOSIT`/`WITHDRAW`/`OFFER_*`/`SKILL_*`/`GROUP_*`/`WAKE`/`IDLE`/`NORM_*`/`TAG_EMITTED`/`ROLE_CHANGE`/`SEED_EVENT`… **无条目** → 落 `default=place_local`，多为「无 `place`→不可见」。 | **逐类补登记**（03 R5 原则"缺条目≠漏登记"仅适用于**不经 perceive 消费**的事件；**可感知事件必须有条目**）。归 T264/实现前补齐 |
| **G3** | `subject_only` 含 `from` 字段；`private` 的 `to[]` 与 `OFFER_CREATED` 特判**语义重叠** | `subject_only` 判据含 `from`（`from` 属交互方，属 `private`/`participants_only` 语义，放 `subject_only` 可疑）；`private` 已含 `to[]` 列表，而 `OFFER_CREATED` 又特判 `to` → 两处。 | 收敛进「class 语义表」（08 §3.5）；`subject_only` 是否保留 `from` 需定（**建议**：`subject_only` = `{agent_id, observer, actor}`，**去掉 `from`**；交互方走 `private`/`participants_only`） |

> **G1/G3 会改语义**——**先报告，等 Leader 裁定再动**（守"改世界语义先问"）。**G2 是补登记**（不改变既有事件语义，仅让新事件有明确 class），建议随 T264 一并落。

---

## 6. 影响面 / 重冻 / 兼容（汇总）

- **D2/D3**：`engine` 语义**不变**（已是该语义）；`life.visibility` 已随 T264 收敛到同一真源 → **净改变 = 修掉 life 的两处越权/缺口**（D2 泄漏、D3 缺口）。**不新增/不删除事件类型**。
- **指纹**：若按 §4 增补 `perception_scope.json` 注释真源 → `engine_version` 指纹变 → **T236 重冻联动**。
- **G7**：本裁定不改事件 schema，G7 不受影响。

---

## 7. 登记内容（08 §3.5 增补，可 diff）

在 08 §3.5 增补：
1. **`visibility_class` 类语义表**（6 类 → 判据字段集，含 **D2 不含 subject**、**D3 含 actor**）；
2. **D2/D3 裁定 + 理由**（本节 §2/§3 的浓缩）；
3. **`OFFER_CREATED` 动态分档规则**（T137）显式登记；
4. **G1–G3 缺口**记为「待裁定/待补登记」（G1/G3 待 Leader，G2 随 T264）。

---

*（本文为 T266 交付：D2/D3 口径定案 + Q3 表达方式 + Q4 缺口扫描 + 08 登记内容 + 影响面。完成后通知 kernel-dev（T264）与 Leader。）*
