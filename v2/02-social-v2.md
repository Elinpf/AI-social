# 02 · 社会结构 v2：公开对话 / 群聊 + 公共议题与组织（设计提案）

> 文档类型：v2 设计提案（社会层，**设计层，不改代码**）｜ 作者：emergence-observer-designer（涌现观测层设计专家）
> 状态：v2 候选（供下一阶段立项；标注【已定】/【待讨论】/【缺口】/【新增】）
> 触发：用户要求下一阶段加入「公开对话 / 群聊」能力，并追问「**一个小镇是如何运转的**（社会层面）」。
> 上游依据（已核）：
> - `v1.1/08-engine-stats-extension.md`（**事件 schema 权威**：`MSG_*`、`GROUP_*`、`OFFER_*`、`CONFLICT_*`、`NORM_*`、`TAG_EMITTED`、`PERCEPTION_SCOPE`）
> - `v1.1/06-life-layer.md`（M6 对话与传播在 v1 三通道 + `refs/tag_hints`；`NORM rule_ref` 格式、`NORM_DEFAULT_THRESHOLD`）
> - `v1.1/00-architecture.md`（IF-1 `perceive`、IF-4 只读、软判定冻结、单小镇青溪镇、周尺度）
> - `v1/01-economy.md`（收费/交易/税等经济议题来源）
> - `v1.2/03-pov-visibility-check.md`（`visible_events()` 与 `PERCEPTION_SCOPE` 最小补齐 R1–R6）
> - 代码基线：`engine/events.py`（EVENT_TYPES 注册表）、`config/perception_scope.json`、`life/visibility.py`、`obs/report.py`（指标命名空间）
> 标签约定：**【已定】**=沿用上游、可直接实现；**【待讨论】**=需立项裁决；**【缺口】**=当前未实现；**【新增】**=本提案建议新增的事件/指标。

---

## 0. 现状基线、定位与约束

### 0.1 现状数据（Leader 核实，2026-10-10）

| 指标 | 现状 | 含义 |
|---|---|---|
| `MSG_DM` | **81** | 一对一私聊**已实现** |
| `MSG_PUBLIC` | **0** | 公开/布告**未实现**（事件已登记，运行时未产出） |
| `MSG_GROUP` | **0** | 群组/场所聊**未实现**（事件已登记，运行时未产出） |
| `RELATION_ENCOUNTER` | 210 | 共处/偶遇（place_local） |
| `CONFLICT_STARTED` | 46 | 权力冲突（`CONFLICT_STARTED/RESOLVED` 已登记） |
| `NORM_PROPOSED` | 17 | 规范提案（`NORM_*` 已登记） |

> **结论**：**一对多 / 多对多的社会传播通道是当前最大缺口**；社会层 v2 的核心任务是把已登记的 `MSG_PUBLIC`/`MSG_GROUP`/`GROUP_*` 从「事件契约」推进到「可运行机制」，并补上「议题 / 舆论 / 组织」这一层**社会结构**。

### 0.2 定位（【已定】）

本提案设计「一个小镇如何在**社会层面**运转」：**信息如何公开流动**（公开对话/群聊）→ **什么成为公共议题**（舆论）→ **共识如何固化为规范与组织**（行会/互助/规范）→ **如何被观测**（社会网络/群聊热度/议题指标）。全部**只读复用**现有内核与可见性框架，**不改前端/engine**。

### 0.3 设计铁律（继承，【已定】）

1. **写世界的只有中央裁决器**；社会事件与其他事件同构（`EventSpec → Arbiter → Ledger`）。
2. **可见性唯一来源 = `PERCEPTION_SCOPE` config + `visible_events()`**；不得在业务逻辑里另立「谁能看见」的判断。
3. **判定只用可从日志确定性重算的指标**（T9 铁律 R1–R7）；LLM 仅生成正文/描述，不参与可见性、议题判定、名声计算。
4. **含 LLM 冻结判定的指标单列**（`*_soft`，`frozen_llm`），不进判定/门禁。
5. **频次上限**：公开/群聊通道必须**防噪声爆炸**（与私聊配额同族，确定性截断 + 显式 `DROPPED` 审计）。

### 0.4 主线：AI 如何用它自己造制度（**物理层我们定，制度层交给 AI 涌现**）

> 用户定调：**「作为 AI 自己驱动的小镇，我们不替他们设计经济，而是给他们能自己造经济的底座与工具；但必须有产生的手段。」**

| 层 | 谁定 | 本文件（社会层）对应内容 |
|---|---|---|
| **物理层（我们定）** | 确定性代码 | 场所与可见性（`PERCEPTION_SCOPE`）、时间结构、**发声原语**（公开/群聊/私聊 = 议价与议题的场域）、**可执行契约的表达原语**（`OFFER_*`）、**组织原语**（`GROUP_*`）、**规范/投票原语**（`NORM_*`） |
| **制度层（AI 涌现）** | Agent 自己 | **价格/工资/雇佣/借贷/分成/租佃**（经对话与 `OFFER_*` 协商形成）、**税收/公共品/铸币规则**（经 `NORM_*`+投票形成）、**行会/互助/合作社**（经 `GROUP_*` 形成） |

- **社会层的核心职责 = 做「制度涌现」的载体**：不是「做一个聊天功能」，而是让**议价、缔约、结社、立规**这四类社会行为**可由 AI 自发产生并留痕可观测**（§3.5）。
- **不写死制度**：物理层**不预设**价格、工资、税率、发行规则；只保证**话语场（公开/群聊）、承诺可表达（契约）、集体决策可成规（规范+投票）**三类**工具**可用。
- **保底（不代劳）**：即便 AI 什么都没造（无缔约、无组织、无规范），世界**照常运转**（时间照走、守恒成立、可见性正常、观测可读）——社会层**不崩**，只是「低活跃」。
- **验收主线**（与 `v2/00-roadmap.md` §2.4 / T78 对齐）：见 §5.6 的**制度涌现指标 ①–⑤**。

---

## 1. 公开 / 群聊机制（与 `visible_events()` 一致）

### 1.1 三通道 × 可见性（【已定】，沿用现有配置）

现有 `config/perception_scope.json`（v1.2-r2）已定义：

| 通道 | 事件 | `visibility_class` | 谁听得见（确定性判据） | 现状 |
|---|---|---|---|---|
| 私聊 | `MSG_DM` | `private` | `agent ∈ {from, to}` | ✅ 已实现 |
| 公开/布告 | `MSG_PUBLIC` | `global` | **全体存活 Agent**（`alive(agent, round)`，`place=null`） | 缺口：未产出 |
| 群组/场所聊 | `MSG_GROUP` | `members` | `agent ∈ members(group_id, e.round)` | 缺口：未产出 |

**关键定义（【已定】）**：

- **公开板 = 全镇可见**：`MSG_PUBLIC` 标 `place=null`、`scope=global`；判据 `alive(agent, e.round)`（单小镇闭合，`gate` 内外一视同仁——对应 v1.2/03 的 **T26-D1 建议：全员存活**）。
- **群聊 = 群成员可见**：`MSG_GROUP` 判据 `agent ∈ members(group_id, e.round)`；**成员必须可按「时点」重算**（v1.2/03 缺口-2 / R3）。群组不**自动**全镇可见——这是与公开板的**根本区别**。
- **场所聊**：本提案把「同场所闲聊」建模为**以场所为作用域的群**（`GROUP_CREATED{kind:"place", scope_place:"cafe"}`），从而复用 `members` 可见性，而**不新增** `place_local` 消息通道。理由：避免与 `ACTIVITY_*`/`RELATION_ENCOUNTER` 的 `place_local` 语义混淆，且使「场所聊」可被 `GROUP_*` 生命周期审计。

> **与 `visible_events()` 的兼容承诺（【已定】）**：本提案**不改变** `perceived()` 的类语义，只**填充** `MSG_PUBLIC`/`MSG_GROUP`/`GROUP_*` 的产出，使 `visible_events()` 的 S3（公开板）/S5（群组）从「已定义但无数据」变为「有数据可重算」。

### 1.2 「听得见」的确定性定义（复用 §3 判定函数）

```
perceived(agent, e, cfg) -> bool          # life/visibility.py 已实现，无需改
  cls = cfg.PERCEPTION_SCOPE[e.type]
  MSG_PUBLIC : cls==global  -> alive(agent, e.round)
  MSG_GROUP  : cls==members -> agent ∈ members(e.group_id, e.round)   # members() 由 GROUP_* 折叠
  MSG_DM     : cls==private -> agent ∈ {e.from, e.to}
```

- **传播范围**：公开板 = 1→N（全镇）；群聊 = 1→|members|；私聊 = 1→1。
- **传播边**（供观测）：`MSG_*.refs` + `OBSERVATION.target_event_seq` 共同构建（沿用 08 §4.4 传播图口径）。

### 1.3 频次 / 噪声限制（【新增】，确定性 + 显式审计）

公开/群聊最容易「刷屏」，必须硬约束（沿用 v1 §4 配额思路，确定性截断）：

| 通道 | 单发送者上限 | 全局/单群上限 | 溢出策略 |
|---|---|---|---|
| `MSG_PUBLIC` | `CAP_PUBLIC_PER_AGENT = 2` 条/回合 | `CAP_PUBLIC_GLOBAL = 20` 条/回合 | 按 `(round, author_id, seq)` 全序截断，落 `DROPPED{type:"MSG_PUBLIC", reason:"quota"}` |
| `MSG_GROUP` | `CAP_GROUP_PER_AGENT = 3` 条/回合/群 | 单群 `CAP_GROUP = 20` 条/回合 | 同上，落 `DROPPED` |
| `MSG_DM` | `CAP_DM = 3` 条/回合（沿用 v1） | — | 同 v1 |

- **夜间/场所限制（【待讨论】）**：是否禁止 `night` 时段公开板刷屏、或限制场所聊只在营业时段（沿用 `place_open(place, slot)`）？建议**默认不禁**（保持信息自由），仅配额限制；长窗再评估噪声。
- **去重 / 反刷屏（【待讨论】）**：同一 `(author, body_hash)` 在同一时段重复公开是否折叠为 1 条并记 `DROPPED{reason:"dup"}`？建议**采纳**（确定性、防噪声），阈值待沙盒标定。
- **与惩罚衔接**：超标/刷屏可由 `apply_penalty` 记 `PENALTY_APPLIED{kind:"spam"}`（**可选**，待讨论）。

### 1.4 与私聊的区分（【已定】）

| 维度 | `MSG_DM`（私聊） | `MSG_PUBLIC`（公开） | `MSG_GROUP`（群聊） |
|---|---|---|---|
| 可见性 | `private`（双方） | `global`（全镇存活） | `members`（群成员） |
| 留痕可见性 | 仅双方 | 全体可回溯（append-only） | 群成员可回溯 |
| 传播潜力 | 低（1→1） | 高（1→N，可被引用再传） | 中（1→|G|，可跨群经公开板再传） |
| 追责/声誉 | 私密 | **公开**（影响名声，可被围观） | 半公开（群内） |
| 沉默/spam 约束 | 配额 | 配额 + 去重 | 配额 + 去重 |

> **设计要点**：公开与群聊的**可回溯性**是「公共议题/名声」得以成立的物理基础——只有留痕且多方可引用，`refs` 闭包才可重算传播。

### 1.5 对 `visible_events()` 的兼容与最小补齐（对接 v1.2/03 R1–R5）

| 补齐项 | 内容 | 本提案用法 |
|---|---|---|
| **R2** `PERCEPTION_SCOPE` | 已有；**新增条目**：`MSG_PUBLIC=global`（已）、`MSG_GROUP=members`（已）、`GROUP_CREATED/JOINED/LEFT` 建议 `global`（组织成立是公共事件，可配） | 可见性判定 |
| **R3** 群组成员时序 | `GROUP_CREATED{members[]}`（默认不可变）；**若组织成员可变**则启用 `GROUP_JOINED/LEFT` | 使 `members(g, t)` 可重算 |
| **R4** `MSG_*.refs` | **转发/转述类必填 `refs[]`**；无来源的标 `spec=true`（"听说"），**不进亲历集** | 传播链与舆论溯源 |
| **R1** `place` 字段 | `MSG_PUBLIC.place=null`；`MSG_GROUP.place` 取群作用域场所（可 null） | S2 视野判定 |
| **R5** `OBSERVATION` 语义 | 维持「显著感知样本」，**非**可见性全集 | 与 T9 传播图口径一致 |

---

## 2. 公共议题与舆论

### 2.1 议题的生命周期（【已定】阶段，判据确定性）

```
萌芽 → 发酵 → 峰值 → 衰减/固化
```

- **议题载体**：以 **`tag`**（`TAG_EMITTED{agent_id, tag, valence, source_msg_id}`）为议题原子；一个「公共议题」= 一个 `tag` 在**公开/群聊语境**下的时间序列。
- **如何成为公共议题（【已定】确定性判据）**：

```
topic_promoted(tag, W) iff
  (1) adoption_W(tag) = |{distinct emitters}| / alive ≥ θ_topic_adopt     # 参与面
  (2) 且 tag 的出现**跨 ≥ K_topic 个不同场所或群**（place/group 去重）      # 公共性（非小圈子）
  (3) 且 freq_W(tag) 相对基线（§T9 滑窗噪声带）显著（> μ + z·σ，z=3 默认）
```

默认建议：`θ_topic_adopt = 0.30`、`K_topic = 2`。【待标定（T10）】

- **阶段划分（确定性）**：对 `freq_W(tag)` 序列取一阶差分 `trend`：
  `萌芽 trend>0 且 adoption<θ`；`发酵 trend>0 且 adoption≥θ`；`峰值 trend≈0 且 freq 最大`；`衰减 trend<0`。
- **固化**：议题若触发 `NORM_PROPOSED`（见 §3），则从「舆论」升格为「制度」。

### 2.2 什么能成为公共议题（触发规则，【已定】）

议题来源**全部是已存在的事件流**，无需 LLM 判断「什么重要」：

| 议题类型 | 触发事件（可观测） | 默认 `tag` 先验 |
|---|---|---|
| **收费 / 价格** | `TAX_LEVIED`、`MARKET_TRADE` 价格异动、`INTEREST_CHARGED`、`OFFER_*` 条款 | `topic:fee`、`topic:price` |
| **死亡 / 濒死** | `AGENT_DIED`（global）、`STATE_CHANGE→near_death/exhausted` | `topic:death` |
| **乱纪 / 违规** | `NORM_VIOLATED`、`CONFLICT_STARTED`、`PENALTY_APPLIED` | `topic:misconduct` |
| **交易 / 行情** | `MARKET_TRADE` 成交量/价异动、`MONEY_*` | `topic:trade` |
| **公共事件** | `SEED_EVENT`（观察者注入，如「周末礼堂办活动」） | `topic:event` |

- **机制**：当上述事件发生且可见性允许时，目睹/听闻的 Agent 在 T1/T2 决策中可产出带 `tag_hints` 的 `MSG_*`；`emit_tags`（L7）落 `TAG_EMITTED`。**议题是自发涌现的**，不由脚本指定（除 `SEED_EVENT` 种子）。

### 2.3 口碑 / 名声的积累（【已定】：D 类为主 + F 类补充）

- **D 类（结构名声，确定性）**——`metrics.social`：

```
mention_indegree(a) = |{msg: refs/提及 a}|                 # 被谈论度
public_citation(a)  = |{MSG_PUBLIC whose body_ref mentions a}|
endorsement(a)      = |{SCORE_POSTED/RANKING_EMITTED: subject=a, score≥θ}|
pagerank_comm(a)    = PageRank(G_comm)                     # 沟通图上的声望
reputation_rank(a)  = 上述加权后的全序排名（权重显式，见 §5）
```

- **F 类（主观口碑，冻结）**——`metrics.social_soft`：读 `LLM_JUDGMENT.dimension ∈ {respect_score, affection_score}`（Agent 互评/环境评估，`frozen=true`），标 `frozen_llm`，**只作描述/敏感性**。

### 2.4 公众反应：围观 / 讨论 / 抵制（【新增】`PUBLIC_REACTION`）

为把「围观/讨论/抵制」变成**一等可观测事件**（而非从 `MSG_*` 事后猜测），建议新增：

```python
# 事件（建议最小新增之一）
PUBLIC_REACTION {
  reaction_id: str,
  agent_id: AgentId,
  target: {kind: "event"|"msg"|"agent", ref: int|str},   # 反应对象
  kind: "gather" | "discuss" | "boycott" | "endorse",     # 围观/讨论/抵制/声援
  topic_tag: str | None,                                  # 关联议题
  day: int, slot: str, place: str | None
}
```

- **判定（确定性，非 LLM）**：
  - `gather`（围观）：同 `(place, round)` 内 `≥ N_gather` 个 Agent 出现在**非自身日程**的公共事件场所 → 可由 `PLACE_MOVE/ACTIVITY_*` **派生**（故 `PUBLIC_REACTION.gather` 可**不落**，仅统计）；
  - `discuss`（讨论）：公开/群聊消息 `refs` 指向同一议题 `tag` 且 `≥ N_discuss` 人参与；
  - `boycott`（抵制）：对某 subject **行为性**切断（拒绝 `OFFER_*`、停止与该 Agent 的 `MARKET_TRADE`）→ 无法纯派生，**需显式事件**（或由 `OFFER_REJECTED` + 交易断流规则确定性推断）。
- **最小化建议（【待讨论】）**：**只新增 `kind="boycott"` 的必要性最高**（行为性、不可派生）；`gather/discuss/endorse` 优先**由日志派生**，暂不落事件。最终取舍交立项。

### 2.5 与 `TAG_EMITTED` 的衔接（【已定】）

- 议题统计完全建立在 `TAG_EMITTED` 之上（频次/份额/采纳/valence/趋势），**复用 T9 §1.3 的口径**，无需新事件。
- `MSG_*.tag_hints[]`（内容层）→ `emit_tags`（L7）→ `TAG_EMITTED`，链路已存在（08 §1.2-F / 06 §10）。

---

## 3. 组织与规范

### 3.1 组织类型（行会 / 互助 / 合作社）（【已定】建模，【新增】字段）

- **载体**：组织 = **`GROUP_*`** 的特化。建议在 `GROUP_CREATED` **新增可选字段 `kind`**：

```python
GROUP_CREATED {
  group_id: str, members: [AgentId], created_round: int,   # 现有
  kind: "chat" | "guild" | "mutual_aid" | "cooperative" | "place",  # 新增
  scope_place: str | None,          # place 型群的作用场所
  charter_ref: str | None          # 组织章程/规则引用（可指向 rule_ref）
}
```

| kind | 中文 | 作用 | 与规范关系 |
|---|---|---|---|
| `chat` | 闲聊群 | 信息交流 | 无 |
| `guild` | 行会 | 同业者联合、定价/准入 | 常产出 `NORM_PROPOSED` |
| `mutual_aid` | 互助组 | 风险共担（互助金/救助） | 与经济 `TRANSFER/LOAN_*` 联动 |
| `cooperative` | 合作社 | 联合生产/分成 | 与 `MARKET_TRADE` 联动 |
| `place` | 场所群 | 场所内公开聊 | 无 |

### 3.2 组织生命周期（【已定】）

```
GROUP_CREATED → (GROUP_JOINED/LEFT)* → GROUP_DISSOLVED?
```

- **默认不可变成员**（08 §1.2-M）：小镇 N=20、组少，`GROUP_CREATED{members}` 一次成型、冻结 `members`，**不落 `JOINED/LEFT`**。
- **【待讨论】**：行会/互助**需要成员变动**吗？若需要，启用 `GROUP_JOINED/GROUP_LEFT`（已登记，只增），并新增 `GROUP_DISSOLVED{group_id, round, reason}`（**建议新增**，使组织可终结、可审计）。
- **治理**：组织内决策（如「是否收会费」）走 `NORM_PROPOSED/ADOPTED`（§3.3）+ 可选 `CONFLICT_STARTED/RESOLVED`（权力冲突，已登记）。

### 3.3 规范形成（提案→采纳→遵守→违反）（【已定】，复用 `NORM_*`）

- **现有契约**（08 §1.2 / 06 §10）：
  `NORM_PROPOSED{norm_id, proposer, rule_ref, support_count, threshold}` → `NORM_ADOPTED{norm_id, adopters[], adopted_day, threshold_used}`（支持者 `≥ threshold`，**纯规则判定**）→ `NORM_VIOLATED{norm_id, violator, day, severity}`（**确定性检测**，L7 为主 / 4.5 为辅）。
  `rule_ref = "norm:{scope}:{predicate}:{threshold}"`，如 `norm:plaza:no_shout_at_night:majority`；`NORM_DEFAULT_THRESHOLD = 3`。
- **组织如何形成规范（【已定】机制）**：

```
① 议题（§2.2）在组织/公开板发酵 → 某 Agent 提 NORM_PROPOSED（scope 多为 group/place）
② 支持者数达到 threshold（默认 3，或组织章程规定的比例）→ NORM_ADOPTED
③ 遵守：默认行为；偏离则由 L7 规则检测 NORM_VIOLATED
④ 惩罚：apply_penalty 执行（口径详见 v1/02），落 PENALTY_APPLIED
```

- **组织级规范**：`scope` 可为 `group:{group_id}`（仅组织内约束）；组织可对成员施加**会费/互助金**（`TRANSFER` 到组织账户，或 `OFFER_*` 条款）——**经济后果仍走 4.x 结算**，社会层不直接改账。

### 3.4 声誉与制裁（【已定】：D 类）

- **制裁（确定性、可观测）**：`NORM_VIOLATED{severity}` + `PENALTY_APPLIED{kind}`；组织可发起**集体抵制**（`PUBLIC_REACTION.kind="boycott"` 或交易断流规则）。**不新增 `SANCTION_ISSUED`**——用「`NORM_VIOLATED` + `PENALTY_APPLIED` + 抵制派生」组合表达，避免事件膨胀。
- **声誉下降**：由 §2.3 的 `reputation_rank` 随时间下降可观测（D 类）。

### 3.5 制度涌现主线：AI 如何自造制度（与 T78 / `v2/00-roadmap.md` 对齐）

> 物理层给**工具**，制度层靠 **AI 的互动**。社会层把四类社会行为 → 四类制度，全部**复用现有事件**、**不写死常量**。

#### 3.5.1 四类社会行为 → 制度

| 社会行为 | 物理层工具（我们给） | 制度产物（AI 造） | 承载事件 |
|---|---|---|---|
| **① 议价** | 公开/群聊话语场（`MSG_PUBLIC`/`MSG_GROUP`）+ 私聊 | 价格/工资/条款的**协商过程** | `MSG_*` + `OFFER_COUNTERED` |
| **② 缔约** | 可执行契约表达（`OFFER_*`） | 雇佣 / 借贷 / 分成 / 租佃 / 买卖 / 劳务**合同** | `OFFER_CREATED/ACCEPTED/REJECTED/COUNTERED/EXPIRED` |
| **③ 结社** | 组织原语（`GROUP_*`） | 行会 / 互助组 / 合作社 | `GROUP_CREATED`(+`JOINED/LEFT/DISSOLVED`) |
| **④ 立规** | 规范 + 投票原语（`NORM_*`） | 税收 / 公共品 / 铸币 / 行为规范 | `NORM_PROPOSED/ADOPTED/VIOLATED` |

#### 3.5.2 可执行契约（`OFFER_*` 承载雇佣/借贷/分成/租佃）〔**工具增强**〕

现有 `OFFER_CREATED{offer_id, from, to[], kind, terms, round_no}` 已具备骨架。为承载**可执行**契约，建议**最小增强**（字段，不新增事件类型）：

```python
OFFER_CREATED {                              # 现有字段
  offer_id, from, to[], kind, terms, round_no,
  # 建议增强：
  kind: "sale" | "service" | "employment" | "loan" | "split" | "tenancy",  # 契约类型枚举
  terms: {                                   # 结构化条款（确定性可校验）
    price_mu?: int, qty?: int,               # sale/service
    wage_mu?: int, period?: "day"|"week",    # employment
    principal_mu?: int, rate_bp?: int, due_round?: int,   # loan（对接 4.2 借贷）
    share_bp?: int,                          # split（分成）
    rent_mu?: int, place?: str               # tenancy（租佃）
  },
  enforceable: bool = True,                  # 是否可执行（违约可判）
  rule_ref?: str                             # 关联规范（如最低工资规范）
}
```

- **生效**：`OFFER_ACCEPTED` 后，契约进入**执行表**（确定性状态机）；经济后果**仍经 4.1/4.2 结算**（如 employment 每周期发 `TRANSFER`；loan 走 `LOAN_ISSUED`）。
- **履约/违约（确定性、非 LLM）**：到期未执行 → `OFFER_EXPIRED` 或触发 `NORM_VIOLATED`（若存在对应规范）；严重违约可由 `apply_penalty` 记 `PENALTY_APPLIED`。
- **不写死价格/工资**：`terms` 由 AI 协商填，**物理层不填默认值**（保底仅保证「可缔约」这一工具可用）。

#### 3.5.3 集体决策 / 投票 → 税收 / 公共品 / 铸币规则〔**工具增强**〕

- **投票 = 规范支持计数**：`NORM_PROPOSED.support_count` → `NORM_ADOPTED`（支持者 `≥ threshold`，纯规则）。**不新增投票事件**（如需显式投票，可选 `VOTE_CAST`，标【待讨论】）。
- **让规范产生经济后果（制度落地的关键）**：建议在 `NORM_ADOPTED` **新增可选字段 `effect`**（**确定性执行**，经济后果仍经 4.3 税/铸币 hook）：

```python
NORM_ADOPTED {                               # 现有字段
  norm_id, adopters[], adopted_day, threshold_used,
  # 建议增强：
  scope: "town" | "group:{id}" | "place:{id}",          # 作用域（全镇/组织/场所）
  effect: {                                              # 可选：制度→经济原语
    kind: "tax" | "public_goods" | "mint" | "behavior",
    rate_bp?: int,                                       # tax：税率（由 AI 议定，非写死）
    budget_mu?: int, purpose?: str,                      # public_goods：公共品预算
    mint_amount_mu?: int, reason?: str                   # mint：铸币授权（对接 4.3 铸币判定）
  }
}
```

- **税收/公共品**：`effect.kind="tax"` 授权 `apply_tax(4.3)` 按 AI 议定的 `rate_bp` 征收 → 入公共品池（税池），由「公共品规范」决定用途。**税率由 AI 投票产生，不是我们写死**。
- **铸币**：`effect.kind="mint"` 是 **AI 发起的发行授权**（对接 T78/内核「铸币落账户」前置，roadmap R3）；物理层只提供**铸币原语**，不预设发行量。
- **边界**：`effect` 的执行必须**确定性**（给定 `NORM_ADOPTED` 即可重算），且**不得绕过守恒**（铸币须有对应 `MONEY_MINTED` 并更新 `M_intended`）。

#### 3.5.4 与 T78（经济底座）的接口

| 接口 | 由谁提供 | 内容 |
|---|---|---|
| 生产/变现原语 | **T78**（`v2/01-economy-substrate.md`） | 可产出资源、可变现（活动的资源入账）——「产生的手段」 |
| 契约执行器 | **T78/4.1–4.3** | `OFFER_*` → `TRANSFER`/`LOAN_ISSUED`/`MARKET_TRADE` 的确定性结算 |
| 议价/发声场 | **本文件（T79）** | `MSG_PUBLIC`/`MSG_GROUP`/`MSG_DM` |
| 缔约/结社/立规工具 | **本文件（T79）** | `OFFER_*` / `GROUP_*` / `NORM_*`(+`effect`) |
| 制度涌现指标 | **本文件 §5.6**（与 T78 对齐口径） | 见 §5.6 |

> **分工一句话**：**T78 给「能生产/能结算」的手，T79 给「能议价/能缔约/能结社/能立规」的嘴与契约**；二者合起来才是「AI 自造制度」的完整工具集。

#### 3.5.5 如何避免「假制度」（呼应 T9 六类区分法）

- **消融判据（硬性）**：移除对应**工具**（如关掉 `OFFER_*` 或 `NORM_effect`）→ 该制度**消失**；若制度在我们**写死常量**也存在，则判为**假制度**（规则产物）。
- **非平凡判据**：市场价格须**非单一常量**（方差 > 0 且由 Agent 议定）；工资/税率须**跨 Agent/跨时间可变**。
- **白盒**：全部制度事实（合同、规范、税率、发行）**可从日志确定性重算**，不依赖叙事或 LLM 复评。

---

## 4. 与已有事件的衔接：最小新增集与字段（【新增】）

### 4.1 复用（**无需新增**，【已定】）

| 能力 | 复用事件 | 说明 |
|---|---|---|
| 公开对话 | `MSG_PUBLIC` | 已登记；补齐 `place=null, scope=global` 产出 |
| 群聊/场所聊 | `MSG_GROUP` | 已登记；补齐 `members` 可见性产出 |
| 组织 | `GROUP_CREATED/JOINED/LEFT` | 已登记（默认不可变） |
| 协商/合作 | `OFFER_CREATED/ACCEPTED/REJECTED/COUNTERED/EXPIRED` | 已登记 |
| 冲突 | `CONFLICT_STARTED/RESOLVED` | 已登记 |
| 规范 | `NORM_PROPOSED/ADOPTED/VIOLATED` | 已登记 |
| 评价 | `SCORE_POSTED/RANKING_EMITTED` | 已登记（确定性） |
| 关系 | `RELATION_CHANGE/RELATION_ENCOUNTER` | 已登记 |
| 议题原子 | `TAG_EMITTED` | 已登记 |

### 4.2 建议新增（**最小集**，按必要性排序）

| # | 事件 | 必要性 | 用途 | 字段（建议） |
|---|---|---|---|---|
| **N1** | `PUBLIC_REACTION`（**仅 `kind="boycott"`**） | 高 | 抵制（行为性、不可派生） | `reaction_id, agent_id, target{kind,ref}, kind, topic_tag, day, slot, place` |
| **N2** | `GROUP_CREATED.kind`（**字段扩展**，非新事件） | 高 | 区分 chat/guild/mutual_aid/cooperative/place | 见 §3.1 |
| **N3** | `GROUP_DISSOLVED{group_id, round, reason}` | 中 | 组织终结、可审计 | — |
| **N4** | `TOPIC_RAISED{topic_id, tag, by, scope, day}` | 低（可省） | 显式登记议题（否则用 `TAG_EMITTED` 频次判定） | — |
| **N5** | `GROUP_JOINED/LEFT` 启用 | 中（视组织可变性） | 成员时序 | 已登记，无需新增类型 |
| **N6** | `OFFER_CREATED.kind/terms/enforceable/rule_ref`（**字段增强**） | 高 | 承载**可执行契约**（雇佣/借贷/分成/租佃）——制度涌现的「缔约」工具 | 见 §3.5.2 |
| **N7** | `NORM_ADOPTED.scope/effect`（**字段增强**） | 高 | 让**规范产生经济后果**（税/公共品/铸币）——「立规」工具 | 见 §3.5.3 |
| **N8** | `VOTE_CAST`（**可选**） | 低 | 显式投票（否则用 `support_count` 计数） | `vote_id, norm_id, agent_id, choice, day` |

> **制度涌现所需工具（【新增】主线）**：N6（缔约）+ N7（立规）+ §3.1 的 `GROUP_CREATED.kind`（结社）+ 公开/群聊产出（议价）——**合起来构成「AI 自造制度」的最小工具集**（§3.5）。

> **最小化原则**：**优先派生（`gather/discuss` 由 `PLACE_MOVE/MSG_*.refs` 派生），仅在「行为性且不可派生」时新增事件**（抵制）。所有新增事件必须：① 注册进 `engine/events.py` EVENT_TYPES；② 在 `replay.apply_event` 注册确定性折叠器；③ 带 `day/slot/place` 审计字段（08 §1.1）。

### 4.3 字段扩展（复用事件，【已定】）

- `MSG_PUBLIC`：`place=null`、`scope=global`（派生）、`topic_tag?`、`refs[]`（转述必填）、`tag_hints[]`。
- `MSG_GROUP`：`group_id`、`place?`（群作用域）、`refs[]`、`tag_hints[]`。
- 全部 `MSG_*`：**转述类必带 `refs[]`**（v1.2/03 R4），否则标 `spec=true`。

---

## 5. 如何观测：新增「社会网络 / 群聊热度 / 公共议题」指标（【新增】）

> 新增命名空间 **`metrics.social`（D 类）** 与 **`metrics.social_soft`（F 类）**，挂进 `obs/report.py` 的 `metrics()` 快照（与 `econ/lifecycle/life/emergence/wellbeing` 并列）。全部**只读日志、纯函数、`llm_calls==0`、`llm_judged_metric_count==0`**（F 类单列）。

### 5.1 社会网络指标（D，`metrics.social.network`）

沿用 T9 §4.3 的图口径，**新增沟通图与组织图**：

```
G_comm : 节点=Agent；边 a→b 权 = MSG_{a→b} 条数（DM + GROUP 内 + 其 PUBLIC 被 b 引用）
G_org  : 二分图 Agent × Group（成员关系）
G_public: 公开板引用图（msg.refs 闭包）

指标：
  comm_n_edges / comm_density / comm_degree_mean
  comm_pagerank_topK                # 名声（§2.3），确定性 tie-break
  comm_reciprocity                  # 双向沟通比例
  org_size_dist / org_overlap        # 组织规模分布、Agent 跨组织重叠
  cross_group_edge_ratio             # 跨群连接占比（"桥"）
```

- **确定性**：节点按 `agent_id` 升序、边按 `(from,to)` 升序、PageRank 固定 `d=0.85`/固定 K 次（复用 `obs/emergence.py` 的实现风格）。

### 5.2 群聊热度指标（D，`metrics.social.group_heat`）

```
n_public_posts / public_post_rate           # 公开板总热度
n_group_msgs / group_msg_rate               # 群聊总量
active_groups                               # 窗口内有消息的群数
per_group: {msg_count, participants, msgs_per_member, heat_gini}
public_vs_group_vs_dm_ratio                 # 三通道份额（社会传播结构）
broadcast_depth1_ratio                      # depth=1 占比（区分"广播"与"扩散"）
spam_drop_rate = DROPPED(MSG_*) / attempted # 噪声/配额压力
```

- **热度**定义：`msg_count / alive`（人均）、`participants / |members|`（参与率）。全部整数/定点。

### 5.3 公共议题指标（D，`metrics.social.issues`）

```
per_topic(tag):
  freq / share / entropy / hhi              # 复用 T9 §1.3
  adoption / valence_mean / trend
  lifespan = last_seen_round - first_seen_round
  peak_freq / peak_round
  n_places / n_groups                        # 跨场所/跨群数（公共性）
  participants                                # 去重参与 Agent 数
  promoted: bool                              # §2.1 topic_promoted
  escalated_to_norm: bool                     # 是否触发 NORM_PROPOSED
```

- **舆论反应**：`reaction_counts{kind}`（围观/讨论/抵制/声援，来自 `PUBLIC_REACTION` 或派生）、`boycott_pairs`（抵制主体对）。
- **声誉**：`reputation_topK`（D，§2.3）。

### 5.4 F 类补充（`metrics.social_soft`，仅描述/敏感性）

- 读 `LLM_JUDGMENT`（respect/affection、以及（若设计）议题情感判定）冻结值，标 `frozen_llm`、附 `frozen_ref`；**不进判定/门禁**（T9-D3）。

### 5.5 与现有指标的映射（复用，不重复造轮子）

| 社会层指标 | 复用来源 |
|---|---|
| `G_comm` 边权 | `MSG_*`（新增口径；`emergence` 已有 `G_rel`/金钱图/沟通图骨架） |
| PageRank / 社团 / degree | `obs/emergence.py` `relation_metrics/community_metrics`（同算法、改图源） |
| 议题频次/份额/熵 | `obs/emergence.py` `tag_metrics` |
| 规范指标 | `obs/emergence.py` `norm_metrics` |
| 冲突/协商 census | `obs/census.py`（E13/E15/E17 等） |
| 声誉的 F 类 | `obs/wellbeing.py` `wellbeing_soft`（respect/affection） |

### 5.6 制度涌现指标（`metrics.social.institutions`，D 类；与 T78 / roadmap §2.4 ①–⑤ 对齐）

> **验收主线**：衡量的是「**AI 是否自己造出了制度**」，而非「我们是否调出了好看的数」。全部**只读日志、纯函数、`llm_calls==0`、`llm_judged_metric_count==0`**。命名与 T78 的「制度涌现指标」**共用口径**（同一 key，两文件对齐）。

| # | 制度 | 指标（确定性） | 判定「涌现」的默认判据 |
|---|---|---|---|
| **①** | **市场 / 定价** | `n_offers{kind=sale/service}`、`n_trades`、`price_points`（不同成交单价数）、`price_by_agent_variance`、`n_counter_offers` | `n_trades>0` **且** `price_points>1`（**非单一常量**，价格由 Agent 议定） |
| **②** | **雇佣 / 工资** | `n_contracts{kind=employment}`、`wage_points`、`active_employment_contracts`、`wage_by_employer_variance` | `n_contracts>0` **且** 工资非恒定 |
| **③** | **借贷 / 信用** | `n_peer_loans`（`LOAN_ISSUED.lender≠"SYSTEM"`）、`credit_terms_variance{rate_bp,due_round}`、`n_loans_by_kind=loan` | `n_peer_loans>0`（**非仅系统续命贷**） |
| **④** | **税收 / 公共品** | `n_norms_adopted{effect.kind=tax}`、`tax_rate_points`、`public_goods_budget_mu`、`public_goods_spend` | 出现 AI 议定的**税率**且执行（非写死常量） |
| **⑤** | **发行 / 规范** | `n_norms_adopted{effect.kind=mint}`、`n_norms_proposed`、`n_norms_adopted`、`n_orgs_by_kind` | 出现 **AI 发起的铸币授权** 或 **规范采纳**（`NORM_ADOPTED>0`） |

- **汇总**：`institutions_emerged = Σ ①–⑤ 达标数`；roadmap §5.1 M3 要求 **≥K 项**（K 由 T80/roadmap 定，建议 ≥2）。
- **反「假制度」判据（复用 §3.5.5）**：`hardcoded_constant_detected`（价格/工资/税率等于 config 常量 → 不计涌现）；**消融**后应消失。
- **社会丰富度**（辅助）：`n_public_msgs`、`n_group_msgs`、`n_orgs`、`n_topics_promoted`（§5.3）；与 `n_norms_adopted`、组织数同列。
- **对齐说明**：T78 负责**经济底座与生产原语**及其经济侧指标；本层负责**制度形成的社会侧指标**（合同/规范/议题/组织）。两文件在同一 namespace 约定下输出 ①–⑤，供 `v2/00-roadmap.md` §5 验收与观测台「制度涌现面板」消费。

---

## 6. 一致性核对（与现有契约）

| 检查项 | 结论 |
|---|---|
| 可见性 | 复用 `PERCEPTION_SCOPE`（`MSG_PUBLIC=global`/`MSG_GROUP=members`/`MSG_DM=private`），**不另立** | ✅ |
| 事件外壳 | 新增事件走 `EventSpec → Arbiter → Ledger`，带 `day/slot/place` | ✅ |
| 复现 | 新增事件须在 `replay.apply_event` 注册折叠器；重放不重算 | 【缺口】待实现 |
| 判定无 LLM | 议题/名声/组织/传播判定**全为 D 类**；`llm_judged_metric_count==0` | ✅ |
| 冻结口径 | F 类单列 `_soft`、`frozen_llm`、出门禁 | ✅ |
| 命名空间 | 新增 `metrics.social` / `metrics.social_soft`，挂 `obs/report.py` | 【新增】 |
| 与内核 | 不改 4.1–4.8；社会层经济后果仍经 4.x | ✅ |
| 物理/制度分离 | 物理层只给原语（发声/契约/组织/规范+投票），**不写死价格/工资/税/发行**（§0.4） | ✅ |
| 制度涌现 | `metrics.social.institutions` ①–⑤ 全 D 类、可重算；消融判据防「假制度」（§5.6/§3.5.5） | 【新增】 |
| 与 T78 联动 | 契约执行器/铸币原语对接 T78（§3.5.4）；制度涌现指标共用口径（§5.6） | 【待联审】 |

---

## 7. 已定 / 待讨论 / 缺口 / 新增 汇总

**【已定】**
- **主线（§0.4）：物理层我们定、制度层交给 AI 涌现**；社会层 = 「制度涌现」载体（议价/缔约/结社/立规 → 价格/雇佣/借贷/税收/发行/组织）。
- 三通道 × 可见性（§1.1）与「听得见」确定性定义（§1.2）；频次/噪声硬约束骨架（§1.3）；与私聊区分（§1.4）；对 `visible_events()` 的兼容（§1.5）。
- 议题生命周期与「成为公共议题」确定性判据（§2.1–2.2）；名声 D 类口径（§2.3）；规范/组织机制（§3）；**制度涌现机制与工具（§3.5：议价/缔约/结社/立规 + `OFFER_*` 可执行契约 + `NORM_*`+投票 → 税/公共品/铸币）**。
- 复用事件清单（§4.1）；观测指标框架 `metrics.social`（§5）；**制度涌现指标 ①–⑤（§5.6，与 T78/roadmap §2.4 对齐）**；一致性核对（§6）。

**【待讨论】**
- 频次/噪声参数（`CAP_*`、去重、夜间限制）；议题阈值（`θ_topic_adopt/K_topic`）。
- 组织是否可变成员（`GROUP_JOINED/LEFT`）与 `GROUP_DISSOLVED`（N3）。
- `PUBLIC_REACTION` 是否只保留 `boycott`（N1）；`TOPIC_RAISED`（N4）是否新增。
- 声誉 D 类加权（`reputation_rank` 的权重假设）与是否给汇总（须显式权重 + 敏感性，参照 T15 §2.3）。
- **制度涌现工具边界（与 T78 联审）**：`OFFER_*` 契约种类枚举（N6）、`NORM_ADOPTED.effect` 的可执行范围（N7）、`VOTE_CAST`（N8）是否显式化；铸币 `effect` 的守恒前置（roadmap R3）。
- **制度涌现阈值 K**（roadmap M3「≥K 项」）与消融判据参数（§3.5.5 / §5.6）。

**【缺口】**（现状未实现，须立项开发）
- `MSG_PUBLIC`/`MSG_GROUP` 的运行时产出与配额/去重（§1.3）。
- `GROUP_*` 折叠器与 `members(g, t)` 时序（v1.2/03 R3）。
- `metrics.social*` 指标实现与快照挂载。
- **制度工具（N6/N7）的执行器**（`OFFER_*` 契约执行表、`NORM_ADOPTED.effect` → 税/公共品/铸币），须与 T78 协同。

**【新增】**（本提案建议的最小集）
- 事件：`PUBLIC_REACTION`（boycott）、`GROUP_DISSOLVED`、`TOPIC_RAISED`（可选）、`VOTE_CAST`（可选）；**字段增强**：`GROUP_CREATED.kind`、`OFFER_CREATED.{kind,terms,enforceable,rule_ref}`、`NORM_ADOPTED.{scope,effect}`；启用 `GROUP_JOINED/LEFT`（可选）。
- 指标：`metrics.social.{network, group_heat, issues, institutions}`（D）、`metrics.social_soft`（F）。

---

## 8. 下一步（立项建议）

> 顺序遵循 roadmap 铁律：**先给底座与工具（物理层）→ 再看涌现（制度层）→ 再谈调参**；里程碑含**制度涌现指标**验收。

1. **P0（发声工具）**：实现 `MSG_PUBLIC`/`MSG_GROUP` 产出 + 配额/去重 + `GROUP_*` 折叠器（使 §1 可运行）——**议价/议题的场域**。
2. **P1（缔约/立规工具）**：落地 N6/N7 字段与执行器（`OFFER_*` 契约执行表、`NORM_ADOPTED.effect`→税/公共品/铸币），**与 T78 的契约执行器/铸币原语对齐**——**制度涌现的「工具」**。
3. **P2（观测）**：`metrics.social.{network,group_heat,issues,institutions}` 确定性实现 + 快照挂载 + `replay` 折叠器注册 + 观测台「制度涌现面板」。
4. **P3（看涌现）**：放开 LLM 参与，观察 §3.5 四类制度自发形成；按待讨论裁决启用组织可变成员 / `PUBLIC_REACTION(boycott)` / `GROUP_DISSOLVED`。
5. **验收**：新增事件 100% 可从日志重放；`metrics.social` 两次调用字节相等；`llm_judged_metric_count==0`；`MSG_PUBLIC/MSG_GROUP` 计数由 0 变为非零且可见性判定与 `visible_events()` 一致；**制度涌现 ①–⑤ 达标 ≥K 项且消融后消失**（roadmap §5.2）。

---

*（本文件为 v2 社会结构设计提案：主线 = **物理层我们定、制度层交给 AI 涌现**——把「公开对话/群聊 → 公共议题 → 组织与规范」设计为**AI 自造制度（议价/缔约/结社/立规）的载体**，**复用现有可见性与事件契约**、**判定全确定性**、**可观测量化**（含制度涌现指标 ①–⑤）；新增事件/字段保持最小集，优先派生。与 T78 联动、供下一阶段立项裁决。）*

---

## 9. 消融开关 `policy.social.enabled`（T115）

为支持 v2 里程碑 M3 的「**逐步只变一个变量**」，社交发声通道加一等开关（`config/policy.json` 的 `social.enabled`，**默认 `true` / 行为不变**）。

- **控制范围**：`INTENT.SOCIAL` → `MSG_DM` / `MSG_PUBLIC` / `MSG_GROUP`，以及 `GROUP_CREATED` 的物化。
- **off 的确切含义 ＝ 关闭 v2「社交发声原语」整体**：在**生成侧整体短路**——`agent._communicate` 不发 `INTENT.SOCIAL`、`settlement._start_specs` 不物化 `GROUP_CREATED`。因此 off 时：
  - `MSG_DM == MSG_PUBLIC == MSG_GROUP == GROUP_CREATED == 0`；
  - **无 `LLM_CALL(purpose="dialogue")`**（对话成本归零）；
  - **配额/去重逻辑不经过**：`INTENT_REJECTED{quota_agent} == 0`、`DROPPED{quota} == 0`、`DROPPED{dup} == 0`。
  > 后两条是「**整条通道没跑**」而非「事件被过滤掉」的判据 —— 干净的隔离。
- **口径注记（留给后人）**：**v1 时期的 `MSG_DM` 正文是写死的模板**（`life/settlement.py` 的 `_dm(body)`，如“（寒暄）你好呀。”），**已被 v2 的 LLM 生成取代**（T98/T103）。因此 off 时**把 DM 一并关闭**不会混淆新旧变量 —— **off 即「无 v2 社交发声」**。
- **不删契约**：只控制「是否产生」，事件类型/字段不变；重放读日志，`state_hash` 可算、`replay` 逐位一致不受影响。
- **开关读取**：life 侧 `life/policy.py`（**不 import engine**，直接读共享 config）；支持 `SOCIAL_ENABLED=0` 环境变量便于消融运行。
