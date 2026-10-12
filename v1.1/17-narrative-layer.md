# 17 · 叙事/故事层设计（第三种产出：从确定性日志长出有趣故事）v1.2

> **【Fork B 时效标注 · 2026-10-12】** 凡本文以「逐位一致」作**验收/门禁**处，按 Leader Q-12.1 改为「**保留可复算、字节相等降为诊断**」。**单一口径见 `v2/refs/gate-grading.md`。**

> 文档类型：领域设计（展示与观测层 / 叙事子线）｜ 作者：narrative-designer（叙事与故事层设计专家）
> 状态：v1.2 设计草案（供 Leader 汇总；显式区分【已定】/【待讨论】/【冲突】）
> 上游依据（本层不另立口径，只引用）：
> - `v1.1/00-architecture.md`（§1.5 底座三角色带「叙事层」、§4.1 IF-7 `narrate`、§4.6 叙事接口契约、§5.4 复现口径「同日志逐位一致」）
> - `v1.1/07-emergence-observation.md`（T9 §4「叙事观测 vs 数字指标」分工与隔离机制 R6；命名空间 D/F/K）
> - `v1.1/08-engine-stats-extension.md`（事件 schema 权威：§1.2 `NARRATIVE{fact_event_seqs[],body_ref,affects_state=false}`、`LLM_JUDGMENT`、E-* 事件族）
> - `v1.1/12-event-lineage.md`（20 类事件谱系、D/F/N/R 归属、确定性结算）
> - `v1.1/13-wellbeing-metrics.md`（W1–W7 福祉向量与「背离现象」确定性判据 §4.2）
> - `v1.1/16-project-goal-options.md`（A 能力训练 + B 受控社会实验双主线；D2 剧情生成从展示层提升为正式子线）
> 标签约定：**【已定】**=本轮基线，下游可直接引用；**【待讨论】**=语义/取值未收敛，交 Leader/用户/T10 标定；**【冲突】**=与上游口径不一致，须回写消解。

---

## 0. 定位、三条硬约束与铁律继承

### 0.1 本层定位（【已定】）

叙事层是**同一批运行的第三种产出**（不新增 run、不新增写入路径）：A 线产出训练轨迹、B 线产出政策结论，**叙事层产出人类可读的故事**。它**栖身于 00 §1.5 的「③ 叙事层（Narrative）」角色带**，对应接口 **IF-7 `narrate`**，落 **`NARRATIVE` 事件（`affects_state=false`）**：

```
narrate(scene_atoms) -> NARRATIVE{fact_event_seqs[], body_ref, affects_state=false}   # 纯输出，非权威
```

- **唯一输入**：`EventLog`（已发生的事实事件）+ `LLM_JUDGMENT.frozen`（可读，标 `frozen_llm`）+ 确定性戏剧性度量。
- **绝不**：写世界状态、触发裁决、进入 `metrics()` 判定路径、进入 A 线训练信号、进入 B 线效应量。正文入**侧存储**（`body_ref`），主日志只留引用与哈希。
- **与 T9 §4 的关系（不冲突声明）**：T9 已定义「数字指标=证据（权威）/ 叙事观测=供人阅读（非权威）」的分工与隔离机制。本层**不推翻、不重定义**，只把 T9 的 `narrate(fact_event_seqs)` **细化成一条可执行管线**（抽取→度量→渲染→形态），并沿用 T9 §4.2 的三条隔离机制。T9 的 `narrative_reads_in_decision == 0` 对本层**依旧成立**。

### 0.2 三条硬约束（H-1 / H-2 / H-3，不可违反）

| # | 约束 | 精确含义 | 机器可校验的不变量 |
|---|---|---|---|
| **H-1** | **事实可追溯** | 故事里每一件「发生了什么」都指向具体事件 `seq`；叙述**不得引入日志不支持的事实**。世界状态是确定的，只有「怎么讲」是生成的。 | 每个 `StoryAtom.anchors[]` 非空且每个 anchor 均为日志中真实存在的 `seq`；每个 `NARRATIVE.source_event_seqs[]` ⊆ 日志已发生事件；渲染后的**句级锚点映射** `anchor_map` 覆盖全部断言句。校验函数 `validate_narrative(narr, log)` 返回 `ok/违规清单`。 |
| **H-2** | **只读、不污染** | 叙事层只读 `EventLog`，**绝不回写世界**；**绝不进入**评估指标、验收门禁、A 线训练信号。延续 v1.1「叙事不参与判定」铁律（T9 R6/R7）。 | `NARRATIVE.affects_state == false`；`apply_event(NARRATIVE)` 为**恒等折叠**（不改状态）；`metrics()` / `emergence_report()` / `wellbeing_report()` **常数时间跳过** `NARRATIVE`；报告头 `narrative_reads_in_decision == 0`、`narrative_in_training_signal == 0`。 |
| **H-3** | **同一日志可多风格重述** | 因事实固定，可用不同叙述风格/视角**重复生成同一段历史**：事实层不变，叙述层可多版。这是「可复现」带来的红利，不是缺陷。 | 同一 `fact_event_seqs` 的**锚点集**在任意版本间**逐位一致**（`narrative_anchor_digest` 确定性）；不同版本的差异**只允许出现在措辞/视角/顺序/详略**，**不得出现在事实内容**（金额、胜负、死亡、关系数值、时间地点）。 |

> **一句话**：**事实层逐位一致、叙述层可多版**——这正是 H-3 与 00 §5.4「同日志逐位一致」的接口。

### 0.3 铁律继承（【已定】，逐条映射）

| 继承自 | 铁律 | 本层落法 |
|---|---|---|
| 00 §1.5 / §5.4 | LLM 只填充内容、不掷骰子、判定冻结 | 戏剧性度量与「选哪些片段」**全部确定性**（D 类），LLM **只做叙述**；叙事不参与任何 RNG 分支 |
| T9 R1/R2 | 判定只读日志、计算 `llm_calls==0` | 本层**判定部分**（抽取+度量+选片）`llm_calls == 0`；只有**渲染**一步调 LLM |
| T9 R5 | 硬内核（钱/死亡/交易）不接 LLM | 叙事中涉及金额/死亡/胜负的句子**必须逐字匹配日志**（见 §3.3 硬事实校验），LLM 不得改写数字 |
| T9 R6 | 判定与描述分离 | 渲染路径**永不回写**；度量路径**永不读叙事文本** |
| T9 §4.2 | `NARRATIVE` 恒等折叠、判定显式忽略 | 原样复用，本层不新增写入型事件 |

---

## 1. 事实抽取：EventLog → 故事原子（StoryAtom）

### 1.1 什么是「故事原子」

**故事原子（StoryAtom）**是叙事的最小事实单元：一条可独立指认「谁在何时、因何、做了什么、导致了什么」的记录。它**不是**事件本身，而是对一到多个事件的**结构化折叠**，并强制携带事实锚点。

```pythonc
StoryAtom := {
  atom_id:   str,               # 全局唯一，规范生成（见 §1.4）
  kind:      AtomKind,          # 见 §1.2 枚举
  cast:      [agent_id],        # 涉及角色（主角/对手/旁观）
  when:      {seq, round, week, day, slot, day_type},
  what:      str,               # 事实陈述骨架（模板填充，非长篇散文）
  anchors:   [seq],             # ★ 事实锚点（≥1，且必须存在于日志）
  evidence:  [{type, seq, field, value}],  # ★ 逐字段证据，供硬事实校验(§3.3)
  inferred:  bool,              # ★ true=「动机线索」等推断项，叙述必须加推测标记
  origin:    "spontaneous" | "induced" | "rescue" | "frozen_llm",  # 来源标签(§1.3)
}
```

### 1.2 原子种类（AtomKind）与职责（对应任务第 1 点五要素）

| kind | 五要素映射 | 主要来源事件（08 §1.2 / 12） | `inferred` |
|---|---|---|---|
| `CAST` **角色** | 角色 | `INIT_ENDOW`、`ROLE_CHANGE`、人格配置离线冻结（N-1） | false |
| `MOTIVE_HINT` **动机线索** | 动机线索 | `GOAL_SET/GOAL_ABANDON`、`SCHEDULE_PLANNED`、低 `need` 的 `NEED_UPDATE`、`intent` 记录 | **true** |
| `ACTION` **行动** | 行动 | `ACTIVITY_STARTED/COMPLETED`、`MSG_*`、`PLACE_MOVE`、`OFFER_*`、`TRANSFER`、`MARKET_TRADE`、`NORM_PROPOSED`、`CONFLICT_STARTED`、`SEED_EVENT` | false |
| `OUTCOME` **后果** | 后果 | `SKILL_LEVEL_UP/OUTPUT`、`GOAL_ACHIEVED/ABANDON`、`NEED_UPDATE`、`RANKING_EMITTED`、`NORM_ADOPTED/VIOLATED`、`AGENT_DIED/REVIVED`、`STATE_CHANGE` | false |
| `RELATION_DELTA` **关系变化** | 关系变化 | `RELATION_CHANGE`（含 `before/after/dim/cause_event_seq`）、`RELATION_ENCOUNTER`、`OFFER_REJECTED` | false |
| `JUDGMENT` **（冻结）定性判定** | 补充定性 | `LLM_JUDGMENT{frozen=true}`（读回不重问） | false（但 `origin="frozen_llm"`） |
| `INTERVENTION` **干预** | 溯源标签 | `SEED_EVENT`、救助/安全阀相关事件（T9 §5.2） | false |

> **动机线索的纪律（防幻觉关键）**：动机**永远不是**日志直接记录的事实，而是从 `GOAL_*`/`need`/`intent` **确定性推断**出的「线索」。凡 `inferred=true` 的原子，渲染时**必须**使用推测语（「似乎/大约是想/看得出他有意…」），且**不得**被当作因果断言。这把 00 §5.2「LLM 只产叙述」落到句级。

### 1.3 来源标签：把「诱导」与「自发」分开（与 T9 §5.3 对齐）

抽取时必须给每个原子打 `origin`：

- `spontaneous`：无 `SEED_EVENT` 锚点；
- `induced`：级联中含 `SEED_EVENT` 锚点（观察者注入，T9 §5.3「诱导涌现」）；
- `rescue`：含救助/安全阀标记（`flag=rescue` / `safety_valve_triggered`）；
- `frozen_llm`：来自 `LLM_JUDGMENT`。

**纪律**：编年史/纪事**必须显式区分**「镇里自己发生的」与「被注入的（induced）」。**绝不**把观察者注入的种子事件叙述成「小镇自发」。这是叙事层的诚实底线（与 T9 §5.3、§6.3 假象③一致）。

### 1.4 抽取规则与可追溯保证（**可重算**）

```
extract_atoms(log, T, params) -> [StoryAtom]        # 纯函数，llm_calls==0
  1) 过滤：只保留 §1.2 白名单事件类型；恒等跳过 NARRATIVE（H-2）。
  2) 折叠：把同一 actor/activity/offer/conflict 的 STARTED→COMPLETED 折叠为一条 ACTION/OUTCOME。
  3) 归并：按 (participants, 时间窗, topic/seed_id) 把相关原子聚成「场景 Scene」（§2.4）。
  4) 打标：为每原子生成 anchors[] 与 evidence[]（逐字段），并计算 origin。
  5) 去重：atom_id = sha256(规范JSON(kind,cast.sorted(),when.seq,what_key))[:16]，全序去重。
```

- **可重算**：`extract_atoms` 只依赖 `(log, T, params)` 与固定 `params`，两次调用**逐位一致**（规范 JSON、键排序、整数优先）。抽取本身 `llm_calls == 0`。
- **可追溯**：`validate_atom` 断言 `anchors ⊄ ∅` 且 `∀a∈anchors: a ∈ log.seqs`，否则记 `SYSTEM_ERROR` 并丢弃该原子（**宁缺毋造**）。

---

## 2. 戏剧性度量（确定性）：挑选「值得讲」的片段

> 目标：把「哪一段历史更值得叙述」变成**可从日志确定性重算**的数字，供自动选片。**全部 D 类、`llm_calls==0`。** 度量只决定「讲什么」，不决定「世界怎么变」。

### 2.1 原子级戏剧分量（9 个子维，各归一化到 [0,1]）

| 子维 | 符号 | 确定性口径（输入全部来自日志） | 默认权重 |
|---|---|---|---|
| 冲突强度 | `c_conflict` | `CONFLICT_RESOLVED` 的 `stakes` 权重 + 双方 `power` 差（12 §3.2 `power_breakdown`）+ 冲突持续回合数归一 | 0.16 |
| 转折 | `c_turn` | 个体或集体轨迹（`net_worth` / `pagerank_rank` / W 维 D 代理）**一阶差分符号翻转**且幅度 ≥ `θ_turn`；`ROLE_CHANGE` 计入 | 0.14 |
| 反差 | `c_contrast` | 复用 13 §4.2 背离判据（富而不乐 / 地位降而幸福升 / 经济差而关系强 / 成长停滞）命中数归一 | 0.12 |
| 关系陡变 | `c_plunge` | `RELATION_CHANGE` 单步 `|after−before| ≥ θ_plunge`，或跨越 `ε_strong` 向下（破裂）；向上强边形成计入（幅度减半权重） | 0.13 |
| 福祉背离 | `c_wbdiv` | 13 §4.2 `divergence_count` 在该场景内占比；`Δecon` 与 `Δwellbeing_D` 符号相反计数 | 0.10 |
| 破产与重生 | `c_ruin` | `net_worth` 触地板 / `AGENT_DIED` / `AGENT_REVIVED` / `REVIVE_FEE_PAID`（三态加权：死亡≥复活>濒死） | 0.14 |
| 结盟与背叛 | `c_ally` | 互惠强边形成（双向 `≥ε_rec`）→ `c_ally↑`；其后出现 `OFFER_REJECTED` / 同对 `CONFLICT_STARTED` / `RELATION_CHANGE` 向下 → 叠加「背叛」项 | 0.10 |
| 稀有度/意外 | `c_rarity` | `−log2(p_baseline(type))`，`p_baseline` 由同 run 基线窗或全库计数确定（固定口径）；越稀有越高 | 0.06 |
| 影响面 | `c_impact` | 场景波及的去重 Agent 数 / `alive_count`；传播级联用 T9 §2.2 `reach_ratio` | 0.05 |

```
D(atom) = [c_conflict, c_turn, c_contrast, c_plunge, c_wbdiv, c_ruin, c_ally, c_rarity, c_impact]  ∈ [0,1]^9
NV(atom) = Σ_k w_k · D_k,  权重 w_k 落 config（默认见上表，Σw=1）   # ★ 权重是配置假设，写入 engine_version 指纹
```

> **权重纪律**：权重是**可声明的价值假设**（类比 13 §2.3 `WBI` 的三条纪律），落 `config/narrative_weights.json`，**随实验配置冻结**。任何改权重都必须重算并标注新 `narrative_config_hash`；**不得**把`NV`写回世界、不得作为激励。

### 2.2 场景聚合并打分

```
Scene := 在时间上相邻(≤Δ_slots)、按 (participants∪seed_id∪place) 连通的一组原子
NV(Scene) = max_a NV(a) + λ·Σ_{a≠argmax} NV(a)·decay(Δt_a)      # 主峰 + 衰减副峰，λ=0.3, decay 半衰期=1 slot
```

- **时间窗**：默认以**周（84 回合）**为选片单位（对齐周纪事），可选更长窗做编年史。
- **选片规则（确定性）**：按 `NV(Scene)` 降序，取 `NV ≥ θ_drama` 的场景；同周最多 `K_top`（默认 5）个；**场景不重叠**（锚点集不相交，冲突时取 NV 高者）。

### 2.3 可重算与阈值

- **可重算**：`compute_drama(log, T, params) -> [scored_scene]` 全为日志纯函数；两次调用逐位一致（规范 JSON、`round(...,6)`、全序 tie-break）。
- **阈值**【待讨论 → 交 T10 标定】：`θ_turn / θ_plunge / θ_drama / K_top / λ / Δ_slots`。默认建议：`θ_drama = 0.35`、`K_top = 5`、`θ_plunge = 0.25·R`（`R=W_MAX−W_MIN`，与 T9 §1.2 同域）、`Δ_slots = 6`。
- **反「算法假象」**：所有排序用**全序 tie-break**（`NV` 降序 → `scene_id` 升序），杜绝并列歧义（对齐 T9 §6.3 假象⑤）。

### 2.4 与 T9 指标的关系

戏剧性度量**复用** T9/T13 的既有确定性指标（`G_rel`、`divergence_count`、`need_level`、`CONFLICT_*`、`net_worth`），**不重定义**任何口径。它**不进** `metrics.emergence`，而是**独立侧产物** `narrative_selection`（供渲染器消费），故**不影响** T9 的判定与门禁。

---

## 3. 叙述渲染：LLM 只做叙述，绑定事实锚点

### 3.1 渲染管线（D 决定「讲什么」→ N 决定「怎么讲」）

```
render(scene, style, pov, budget) -> NarrativeRecord
  ① [D] 组装「事实包」：仅取该 scene 的 story atoms（含 anchors/evidence/origin），
        生成规范 JSON —— 这是 LLM 的**唯一世界知识**（不给整份日志，防越界）。
  ② [N] LLM 按模板生成带句级锚点的文本（§3.2 结构化输出格式）。
  ③ [D] 硬事实校验（§3.3）：逐句核对金额/死亡/胜负/关系数值/时间地点。
  ④ [D] 锚点覆盖校验：每句断言句必须映射到 ≥1 个 anchor；未覆盖 → 打 [推测] 或丢弃。
  ⑤ [D] 封装 NARRATIVE{fact_event_seqs[], body_ref, affects_state=false} + 元数据，入侧存储。
```

> **RNG 无关**：渲染不消耗任何 RNG 分支，LLM 不掷骰子（00 §5.4）。同一事实包可渲染出多版（H-3）。

### 3.2 结构化输出格式（强制）

```jsonc
{
  "narrative_id": "nar-...",
  "style": "chronicle" | "weekly_gazette" | "character_pov" | "feature",
  "pov": "omniscient" | "<agent_id>",
  "model": "<模型/版本>",            // 审计四要素之一（对齐 LLM_JUDGMENT）
  "prompt_hash": "sha256:...",
  "sentences": [
    {"text": "……", "anchor": [1010, 1011], "spec": false},
    {"text": "……似乎……", "anchor": [1003], "spec": true}   // spec=true 表示含推测语气（多为 MOTIVE_HINT）
  ],
  "anchor_map_ref": "<side://...>",  // 句级锚点全表
  "spec_flags": 2,                   // 推测句计数
  "anchor_digest": "sha256:..."      // ★ 锚点集指纹（与事实无关，确定性）
}
```

- **`anchor_digest` = 对 `sorted(unique(所有 anchor))` 的规范 JSON 取哈希**：它**不依赖 LLM**，故对同一 `fact_event_seqs` **逐位一致**——这就是 H-3 与「同日志逐位一致」的接口：**事实/锚点层可复现，叙述层可多版**。

### 3.3 防幻觉：三层约束

| 层 | 机制 | 拦截对象 | 处置 |
|---|---|---|---|
| **输入约束** | LLM 只见场景的事实包，**不见**整份日志、不见其他角色私有记忆 | 越界编造未提供的世界知识 | 事实包即边界 |
| **硬事实校验（逐字）** | 金额/死亡/胜负/关系数值/时间地点：正则+结构化抽取，要求与 `evidence[]` **逐字相等** | LLM 改写数字（如把 12 写成 20、把败者写成胜者） | **不相等 → 该句判失败**：重渲染一次（带纠错提示）；再失败则**回退模板句**（纯 D 生成） |
| **锚点覆盖校验** | 每句断言句必须映射到真实 `anchor`；`inferred` 原子句必须 `spec=true` | 无锚点断言、把「动机线索」写成事实 | 无锚点 → 强制打 `[推测]` 或删除；`inferred` 未加推测语气 → 改写/标记 |

> **金额/死亡纪律（对齐 T9 R5）**：这三类**绝不**允许 LLM 自由表述，只能引用日志数值。叙事层的**硬事实校验器是纯 D 代码**，故马太效应任一句都可回溯。

> **【待讨论】** 是否引入一次「渲染后自检」的 LLM 复核（成本换质量）：默认**不引入**，以省成本并避免引入新的不可复现环节；若引入，其输出只影响 `spec_flags` 标注、**不改变事实**，且需标 `model` 供审计。

### 3.4 推测语的使用规范（防幻觉的人读侧）

- `MOTIVE_HINT`（推断）→ 允许「似乎/大约/看得出/大概是」；
- 对话心理、未记录的内心活动 → **禁止**直接叙述为事实，要么删，要么标 `[推测]`；
- `frozen_llm`（如「他们认为彼此是师徒」）→ 可叙述，但标注 `(LLM 判定, 已冻结)`，提示读者这是定性判定非硬事实（对齐 T9 R3「可读不可算」）。

---

## 4. 输出形态：四类模板（【已定】至少 4 类）

> 每类给出：用途 / 视角 / 输入 / 结构 / 长度预算 / 典型触发。

### 4.1 编年史 Chronicle

- **用途**：全镇按时间线的大事记，适合长窗（4–12 周）总览。
- **视角**：全知第三人称。
- **输入**：按 day/slot 排序、`NV ≥ θ_drama` 的场景原子（跨多周）。
- **结构**：`按周分章 → 每日小节 → 段落`；每段以时间地点起句。
- **长度预算**：每次调用 ≤ `B_chronicle`（默认 ~1200 token 输出），超长**分章多次**渲染。
- **触发**：长窗结束、用户按需。

### 4.2 每周纪事 Weekly Gazette

- **用途**：以「青溪周报」样式给出一周要闻，最适合**持续订阅**与 B 线政策解读。
- **视角**：全知、报刊体（标题 + 导语 + 简讯）。
- **输入**：本周 `top-K` 场景。
- **结构**：`头条（NV 最高场景）→ 2–4 条简讯 → 一句「本周数字」锚定（存活率/Gini 等 K 类事实，逐字）`。
- **长度预算**：≤ `B_gazette`（默认 ~800 token）。
- **触发**：**每模拟周自动一次**（默认采样运行时）。

### 4.3 角色视角 Character POV

- **用途**：第一人称，代入某个 Agent 的「一周目击」，最能体现「同一历史、多种真相」。
- **视角**：**严格受限**——只允许该 Agent **亲历或听闻**的原子；**禁止上帝视角**。
- **输入**：`filter_by_visibility(atoms, agent, log, T, cfg)`。**判据来源已升级**（依 T9 核查 `v1.2/03-pov-visibility-check.md` §3，回应 NT-C3）：**不再以「读了哪些 `OBSERVATION`/`MSG_*`」为全集**，而用从日志+config 确定性推导的 `visible_events(agent)`（亲历）与 `heard_events(agent)`（听说）严格二分：
  - **`visible_events(agent)`（亲历）** = S1 直接参与（`actor/participants`）∪ S2 视野同场（占用时间线 `PLACE_MOVE/ARRIVED` 折叠 + 事件 `place` + `PERCEPTION_SCOPE` 可见性分类）∪ S3 公开板 ∪ S4 私聊（`from/to`）∪ S5 群组成员 ∪ S8–S10 记忆链（`source_event_seq`/检索命中/反思闭包）∪ S11 冻结判定（`LLM_JUDGMENT.parties`，标 `frozen_llm`）。
  - **`heard_events(agent)`（听说）** = agent 收到的消息沿 `refs[]` 反向闭包到达的事实；**与亲历互斥**：`set(heard) \ set(vis)`。缺 `refs` 的转述一律按「**听说（未核实）**」处理，`spec=true`。
  - **`OBSERVATION` 降级为显著度证据**（salience 门控子集，`visible_events ⊇ OBSERVATION`），用于 POV 的「重点」而非「全集」——避免漏掉「亲眼所见但未达显著阈值」的内容（核查缺口-3）。
- **结构**：`第一人称日记体`；`keep_direct` 原子直述，`keep_heard` 原子必须以「听说」起句并 `spec=true`，`dropped` 原子（既非亲历亦非听说）**不得出现**。
- **前置**：严格实现依赖 T8 登记核查报告的 **R2（`PERCEPTION_SCOPE` 配置表）/ R3（群组成员事件或冻结成员）/ R4（转述必带 refs）**。在 R1–R4 落地前，POV 可用**保守集**先跑：`直接参与 ∪ 私聊 ∪ 公开板 ∪ 记忆链`（只会偏保守、不会越界）。
- **长度预算**：≤ `B_pov`（默认 ~700 token）。
- **触发**：用户指定角色、或该角色本周 `NV` 高（主角化）。
- **审计**：POV 记录附 `visible_event_digest`（`visible_events` 规范哈希）与 `scope_table_version`，使「此 POV 依据哪些可见事件」可核验。

### 4.4 重大事件特写 Feature

- **用途**：对单个高 `NV` 场景做深度特写（多视角拼贴）。
- **视角**：全知 + 关键角色片段。
- **输入**：单场景全部原子（含多方视角）。
- **结构**：`场景定镜 → 各方行动 → 结算与后果 → 余波`。
- **长度预算**：≤ `B_feature`（默认 ~1500 token）。
- **触发**：`NV ≥ θ_feature`（默认 0.6，明显高于周纪事）。

> **四类共享**：同一场景可用**四种模板各出一版**（H-3 红利）；版本间 `anchor_digest` 一致、事实一致、措辞视角不同。

---

## 5. 可复现红利：一日志多风格（与「同日志逐位一致」的关系）

### 5.1 分层复现口径（【已定】）

```
事实层（EventLog）        : replay(log) 逐位一致；metrics() 两次字节相等          —— 由 D0/T9 保证
锚点层（story atoms/anchor_digest）: 对同一 log 确定性重算，逐位一致              —— 由本层 D 部分保证
叙述层（NARRATIVE 正文）   : 允许 LLM 生成，跨跑不逐位一致；入侧存储 + 哈希        —— 有意接受
```

- **「同日志逐位一致」管的是事实与锚点**：叙事**不进**该保证（它也不进判定，见 §0.2 H-2）。
- **多版红利的来源**：正因为**事实固定**，才能用同一份 `fact_event_seqs` 反复重述出编年史/纪事/角色视角/特写；差异**只在叙述层**，且每版都携带可核验的 `anchor_digest`——**读者能确认「这几版讲的是同一件事」**。

### 5.2 版本管理

- 每次渲染产出一条 `NARRATIVE`，`narrative_id` 唯一，元数据记 `{style, pov, model, prompt_hash, anchor_digest, spec_flags}`。
- **同一 `anchor_digest` 下可挂多版**；去重缓存键 = `(anchor_digest, style, pov)`，命中则复用，省成本（§7）。
- **不作权威**：任何版本都不得被引用为「实验结论」；结论只来自 `metrics`（T9/T13）。

---

## 6. 与 A/B 的关系：只读、不回写、作「人读观测台」

### 6.1 与 A 线（能力训练）

- **不进训练信号**：A 线红线（16 §3.4）已规定「F 类不得作训练信号、只用确定性 outcome」；叙事层**更甚**——它是 LLM 生成的**描述**，**绝不**进入 `reward_calculator`。硬校验 `narrative_in_training_signal == 0`。
- **不与轨迹导出冲突**：轨迹导出读 `state→decision→outcome`（16 §2.2），叙事层读同样的日志但**只产文本**，两者**并行只读、互不干扰**。

### 6.2 与 B 线（受控社会实验）——**本层的主要价值位**

- **不进效应量**：B 的效应量由确定性统计器算（16 §2.4），叙事层**不参与** `Δ_m`、p 值、门禁。
- **作人读观测台**：政策效应本身是数字（如「累进税使 Gini 降 0.05」），叙事层可把**同一 seed 的政策 A 组 vs B 组**渲染成**两篇平行故事**，让人类**直观读**出机制差异——但这只是**解读辅助**，**不产生新结论**。读者被明确告知：结论看数字，故事看「像不像那么回事」。

### 6.3 隔离机制（复用 T9 §4.2，不新增写入路径）

1. `NARRATIVE.affects_state=false`；`apply_event(NARRATIVE)` 恒等折叠；
2. `metrics()` / `emergence_report()` / `wellbeing_report()` **显式忽略** `NARRATIVE`（常数时间跳过）；
3. 报告头硬校验：`narrative_reads_in_decision == 0`、`narrative_in_training_signal == 0`。

---

## 7. 成本与节流

### 7.1 何时生成（触发策略）

| 触发 | 频率 | 模板 | 说明 |
|---|---|---|---|
| **周事件** | 每模拟周 1 次 | 每周纪事 | 主档；沙盒期可关或采样 |
| **重大事件** | `NV ≥ θ_feature` | 重大事件特写 | 稀有、按需，成本最高 |
| **长窗收束** | 4/12 周结束 | 编年史 | 分章多次渲染 |
| **按需** | 用户/评审请求 | 任意 | 指定角色/周/场景 |
| **默认关闭** | 沙盒 L0/L1 | — | 沙盒首验**默认不生成叙事**，仅在需要观感时开启采样 |

### 7.2 token 预算与降级

```
叙事有独立预算 NARRATIVE_BUDGET，与 LLM_BUDGET（世界运行）分离；
叙事为**最低优先级**：世界运行绝不因叙事排队而阻塞（叙事是侧产物，可掉）。
降级链：T2 完整渲染 → T1 小模型/模板骨架填充 → T0 纯模板句（仅事实陈述，无润色）
        超 NARRATIVE_BUDGET → 只保留头条/骨架，其余丢弃，并记 NARRATIVE(degraded=true)
```

- 预算量级（估，待 T10 标定）：周纪事 ~`8e2` 输出 token / 次；特写 ~`1.5e3`；编年史分章。相对 16 §P0「N=20 单周 ≈2e6 token」的世界运行成本，叙事占比**可忽略**（<1%）。
- **可审计**：每次渲染记 `LLM_CALL(purpose="describe")`，成本与判定分列（对齐 08 §1.2 三事件分列）。

### 7.3 节流手段

1. **去重缓存**：键 `(anchor_digest, style, pov)`，命中复用不重生成；
2. **采样**：沙盒期按 `sample_rate`（默认 0 或 1/4）只对部分周生成；
3. **场景上限**：每次渲染 `K_top` 封顶，禁止把整份日志喂给 LLM（既省成本又防越界）；
4. **分区解耦**：**训练/实验分区（16 §2.5）用的场景**，叙事可照常生成，但叙事**不得**倒入任何分区数据集。

---

## 8. 输出样例（虚构但合规）

> 以下日志片段为**虚构**，但字段严格遵循 `08` §1.2 事件 schema 与 `12` 事件谱系；数值内自洽（金额守恒、关系在 `[W_MIN,W_MAX]` 内）。**每句故事都带 `[seq]` 锚点**，体现 H-1。

### 8.1 虚构日志片段（青溪镇 · 第 0 周 day5–day6 周末）

| seq | type | 关键 payload |
|---|---|---|
| 1001 | `TIME_MARK` | `{round:60, week:0, day:5, slot:morning, day_type:weekend}` |
| 1002 | `ROLE_CHANGE` | `{agent:A-HE, from:unemployed, to:farmer, cause:"goal_change", day:5}` |
| 1003 | `GOAL_SET` | `{goal:g-he-1, agent:A-HE, kind:mastery, description_ref:"西坡试验田"}` |
| 1010 | `ACTIVITY_STARTED` | `{activity:act-1, agent:A-HE, activity_type:work, place:farm, slot_id:morning}` |
| 1011 | `ACTIVITY_COMPLETED` | `{activity:act-1, agent:A-HE, outcome:done, duration_ticks:6}` |
| 1012 | `SKILL_LEVEL_UP` | `{agent:A-HE, skill_id:farming, level_before:2, level_after:3}` |
| 1013 | `NEED_UPDATE` | `{agent:A-HE, dim:energy, before:70, after:41, cause:"act-1"}` |
| 1015 | `SEED_EVENT` | `{seed:s-1, kind:festival, injected_by:OBSERVER, payload:{host:A-LIN, place:hall, day:6}}` |
| 1016 | `MEMORY_WRITE` | `{mem:m-1, agent:A-LIN, kind:observation, source_event_seq:1015, importance:8}` |
| 1017 | `MSG_DM` | `{from:A-LIN, to:A-SU, body_ref:b-1, refs:[1015], tag_hints:["festival"]}` |
| 1018 | `MSG_DM` | `{from:A-SU, to:A-HE, body_ref:b-2, refs:[1017], tag_hints:["festival"]}` |
| 1019 | `OBSERVATION` | `{observer:A-HE, target_event_seq:1018, salience:0.7}` |
| 1020 | `TAG_EMITTED` | `{agent:A-HE, tag:festival, valence:1, source_msg_id:b-2}` |
| 1031 | `TRANSFER` | `{from:A-HE, to:A-LIN, amount:12, reason:gift}` |
| 1032 | `RELATION_CHANGE` | `{from:A-HE, to:A-LIN, dim:affinity, before:48, after:63, cause:gift, cause_event_seq:1031}` |
| 1040 | `CONFLICT_STARTED` | `{conflict:c-1, parties:[A-LIN,A-MU], stakes:{hall_evening_slot:true}, rule_ref:R-CONFLICT-2}` |
| 1041 | `CONFLICT_RESOLVED` | `{conflict:c-1, winner:A-MU, power_breakdown:{wealth:0.5,ally:0.3,pagerank:0.5,rng:0.1}}` |
| 1042 | `RELATION_CHANGE` | `{from:A-LIN, to:A-MU, dim:affinity, before:30, after:18, cause:conflict, cause_event_seq:1041}` |
| 1050 | `METABOLISM` | `{agent:A-MU, amount:3, cash_after:4}` |
| 1051 | `LOAN_ISSUED` | `{agent:A-MU, amount:20, outstanding_after:20}` |
| 1052 | `INTEREST_CHARGED` | `{agent:A-MU, amount:5, outstanding_after:25}` |
| 1060 | `AGENT_DIED` | `{agent:A-MU, cause:"insolvent_at_floor", round:72}` |
| 1070 | `AGENT_REVIVED` | `{agent:A-MU, fee:25, via:"loan_guarantor"}` |
| 1080 | `NORM_PROPOSED` | `{norm:n-1, proposer:A-LIN, rule_ref:"hall-evening-reservation", support_count:4, threshold:5}` |
| 1081 | `NORM_ADOPTED` | `{norm:n-1, adopters:[A-HE,A-SU,A-LIN,A-MU,A-XX], adopted_day:6, threshold_used:5}` |

### 8.2 抽取出的故事原子（节选）+ 戏剧性打分

| atom_id | kind | cast | when(seq) | what（事实骨架） | anchors | inferred | origin |
|---|---|---|---|---|---|---|---|
| a-he-cast | CAST | A-HE | 1002 | 阿禾由失业转为农民 | [1002] | false | spontaneous |
| a-he-goal | MOTIVE_HINT | A-HE | 1003 | 阿禾似有「种好西坡试验田」的意愿 | [1003] | **true** | spontaneous |
| a-he-work | ACTION+OUTCOME | A-HE | 1010–1013 | 阿禾整上午在农场劳作，农技 2→3，体力 70→41 | [1010,1011,1012,1013] | false | spontaneous |
| a-seed | INTERVENTION | A-LIN | 1015 | 观察者注入「周末礼堂办丰收节」种子 | [1015] | false | **induced** |
| a-cascade | ACTION | A-LIN,A-SU,A-HE | 1017–1019 | 邀请经 林砚→苏晚→阿禾 两跳扩散 | [1017,1018,1019] | false | induced |
| a-gift | ACTION+RELATION | A-HE,A-LIN | 1031–1032 | 阿禾赠林砚 12 枚钱，好感 48→63 | [1031,1032] | false | spontaneous |
| a-conflict | ACTION+OUTCOME | A-LIN,A-MU | 1040–1042 | 林砚与穆青争礼堂档期，穆青胜，好感 30→18 | [1040,1041,1042] | false | spontaneous |
| a-ruin | OUTCOME | A-MU | 1050–1070 | 穆青现金触地板→借贷→计息→第72回合破产死亡→以 25 枚复活费重生 | [1050,1051,1052,1060,1070] | false | rescue |
| a-norm | OUTCOME | A-LIN 等 | 1080–1081 | 林砚提「礼堂晚间预订」规范，5 人附议，当场采纳 | [1080,1081] | false | spontaneous |

**确定性戏剧性打分（默认权重，节选）**：

| scene | 主峰原子 | `c_conflict` | `c_turn` | `c_plunge` | `c_ruin` | `c_ally` | `c_impact` | **NV** |
|---|---|---|---|---|---|---|---|---|
| S1 西坡的新农夫 | a-he-work | 0.00 | 0.62 | 0.00 | 0.00 | 0.00 | 0.05 | **0.38** |
| S2 丰收节的邀请 | a-cascade | 0.05 | 0.10 | 0.00 | 0.00 | 0.20 | 0.15 | **0.24** |
| S3 赠礼与结盟 | a-gift | 0.00 | 0.20 | 0.55 | 0.00 | 0.60 | 0.05 | **0.42** |
| S4 礼堂之争 | a-conflict | 0.72 | 0.30 | 0.60 | 0.00 | 0.40 | 0.10 | **0.58** |
| S5 穆青的破产与重生 | a-ruin | 0.10 | 0.55 | 0.20 | **0.92** | 0.00 | 0.10 | **0.63** |
| S6 礼堂预订案 | a-norm | 0.05 | 0.40 | 0.00 | 0.00 | 0.20 | 0.30 | **0.36** |

> `θ_drama=0.35` ⇒ 本周选出 S1/S3/S4/S5/S6（场景不重叠，`K_top=5`）；`NV≥0.6` 仅 S5 → 触发**特写**。

### 8.3 渲染样例 A —— 每周纪事（Weekly Gazette，节选）

> **《青溪周报》· 第 0 周**
> **【头条】礼堂之争：穆青险胜，穆家账本见底** —— 本周末，工匠林砚与商人穆青为礼堂晚间档期起争执，最终穆青胜出[1040,1041]；但这场胜仗代价高昂：穆青现金一度跌至 4 枚[1050]，借入 20 枚又被计息 5 枚[1051,1052]，第 72 回合终因无力偿付倒下[1060]，随后以 25 枚复活费勉强归镇[1070]。
> **▲ 西坡的新农夫** —— 阿禾正式落籍为农夫[1002]，整个上午泡在农场，农技升至 3 级[1010,1011,1012]。
> **▲ 一份 12 枚的礼** —— 阿禾向东道主林砚送上 12 枚谢礼[1031]，两人好感升至 63[1032]。
> **▲ 礼堂预订案过关** —— 林砚提的「礼堂晚间预订」规范获 5 人附议、当场采纳[1080,1081]。
> 🔎 本周数字（K 类事实，逐字核对）：存活率 3/4、本周死亡 1 例[1060]。

*（说明：原为观察者注入的丰收节种子[1015]在正式刊出时以「镇中筹备」表述，并在版尾标注「本周有 1 项外部注入事件」，以区分 induced 与 spontaneous。）*

### 8.4 渲染样例 B —— 角色视角（Character POV：阿禾，第一人称，节选）

> **阿禾的日记 · 周末**
> 我把名字落在了农册上，从现在起是农夫了[1002]。西坡那块地我盯了很久，今天总算下足力气，从清早忙到晌午[1010,1011,1012]——胳膊酸得抬不起，可心里踏实。
> 傍晚苏晚捎来话，说礼堂周末有场丰收节[1018]，我听得心里发热（听说东家是镇上那位匠人，我没细问）[1019]。我托人给东家送了 12 枚钱当谢礼[1031]。
> 夜里听说穆老板出事了，倒在账本上，后来又被赎了回来[1060,1070]——这么大的事，我这把身子骨也只能替自己那点营生操心。

*（说明：阿禾未亲历礼堂之争[1040,1041]，故 POV 版**不含**该场景；对穆青死亡仅以「听说」转述并 `spec=true`——H-3 的「同一历史、不同真相」。）*

### 8.5 渲染样例 C —— 重大事件特写（Feature：穆青的破产与重生，节选）

> **特写 · 一场胜利的代价**（`NV=0.63`，触发特写）
> 礼堂的灯先亮在穆青这一边。权力结算显示，他以财富 0.5、盟友 0.3、声望 0.5 的分量压过林砚[1041]——争到了那个周末最值钱的晚间档。
> 但账本记着另一个结局。散场后不久，穆青的现金只剩 4 枚[1050]；他借了 20 枚[1051]，利滚利又多出 5 枚[1052]。第 72 回合，数字终于不肯再等，穆青倒在破产的地板上[1060]。
> 镇子没有让他消失。25 枚复活费把他赎了回来[1070]——一场胜利，标价 25 枚，外加一件格林砚衬衫的旧交情，从 30 一路降到 18[1042]。

---

## 9. 接口、落盘与冲突清单（交 Leader / T8）

### 9.1 接口对齐

| 接口 | 本层用法 | 依据 |
|---|---|---|
| **IF-7 `narrate(fact_event_seqs) -> text`** | 本层主接口；`scene` 的事实包即 `fact_event_seqs` | 00 §4.1 / §4.6 |
| **`NARRATIVE` 事件** | 原样复用（`affects_state=false`、`body_ref`、`source_event_seqs[]`） | 08 §1.2 |
| **`LLM_JUDGMENT.frozen`** | 只读回、标 `frozen_llm`，不重问 | 00 §5.5 / T9 R3 |
| **`LLM_CALL(purpose="describe")`** | 叙事成本单列，与判定分列 | 08 §1.2 三事件分列 |
| 只读契约 | `narrative_reads_in_decision==0`、`narrative_in_training_signal==0` | T9 §4.2 / 16 §3.4 |

### 9.2 落盘（config 化，保可复现）

```
config/narrative_weights.json     # 戏剧性权重(§2.1) + 阈值，随 engine_version 指纹
config/narrative_templates/       # 四类模板的 prompt 骨架(§4)
side-store/narrative/<nid>.txt    # NARRATIVE 正文（body_ref 指向），主日志只留哈希引用
```

### 9.3 冲突 / 待对齐项

| 编号 | 级别 | 事项 | 处置建议 |
|---|---|---|---|
| **NT-C1** | 低 | 08 §1.2 `NARRATIVE` payload 现为 `{fact_event_seqs[], body_ref, affects_state=false}`，本层需补元数据 `{narrative_id, style, pov, model, prompt_hash, anchor_digest, spec_flags, degraded}` | 请 T8 在 §1.2 扩 `NARRATIVE` **可选字段**（只增不改，X1 允许）；不新增事件类型 |
| **NT-C2** | 低 | 本层新增侧产物 `narrative_selection`（戏剧性选片）+ 命名空间 `metrics.narrative`（可选，仅描述） | 请 T8 §4.0 登记为**非判定命名空间**（与 `emergence_soft` 同类，`llm_judged_metric_count` 不涉）；**不进**门禁 |
| **NT-C3** | 中 | `OBSERVATION` 是否为「角色视角可见性」的**充分**依据 | **已裁决·已回写**（T9 核查 `v1.2/03-pov-visibility-check.md`）：**不充分**。`OBSERVATION` 是 salience 门控子集，非可见性全集。本层 §4.3 已改用以日志+config 确定性推导的 `visible_events(agent)`（亲历）/ `heard_events(agent)`（听说）严格二分。**转 T8 登记 R2（`PERCEPTION_SCOPE` 配置表）/ R3（群组成员事件）/ R4（转述必带 refs）**；R1–R4 落地前 POV 用保守集先跑 |
| **NT-C4** | 低 | 文档编号：任务书要求落 `17-narrative-layer.md`，而 16 §D2 记为展示层子项 | 以 `17-` 为准（命名对齐，非内容冲突） |

---

## 10. 已定 / 待讨论汇总

**已定（v1.2 基线，下游可直接引用）**
- 三条硬约束 H-1/H-2/H-3 及其机器可校验不变量（§0.2）；与 T9 §4/IF-7 的不冲突声明（§0.1）。
- 故事原子 schema 与抽取规则 `extract_atoms`（§1）；来源标签 `origin`（induced/spontaneous/rescue/frozen_llm）（§1.3）。
- 戏剧性度量 `D(atom)` 九子维 + `NV(Scene)` 与确定性选片（§2），权重落 config、可重算。
- 渲染管线与结构化输出、三层防幻觉约束（输入/硬事实/锚点覆盖）（§3）。
- 四类输出模板：编年史 / 每周纪事 / 角色视角 / 重大事件特写（§4）；**角色视角可见性判据** = `visible_events()`/`heard_events()` 严格二分（依 T9 核查 `v1.2/03-pov-visibility-check.md`）。
- 分层复现口径与多版红利（§5）；与 A/B 的只读关系与「人读观测台」定位（§6）；成本节流与降级链（§7）。
- 完整输出样例：日志片段→故事原子→打分→三类风格成稿（§8）。

**已裁决转入「已定」（本轮 T9 核查）**
- `NT-C3` POV 可见性：`OBSERVATION` **不充分**，改以 `visible_events`（亲历）/ `heard_events`（听说）二分；`OBSERVATION` 降为显著度证据。前置补齐 R1–R4 转 T8 登记（见 `v1.2/03-pov-visibility-check.md` §4）。

**待讨论（开放问题）**
- 阈值标定（交 T10）：`θ_turn/θ_plunge/θ_drama/θ_feature/K_top/λ/Δ_slots`；`p_baseline` 口径。
- 权重 `w_k` 的默认值与是否提供多组（类比 13 §2.3 `WBI` 敏感性）。
- `NT-C1` `NARRATIVE` 字段扩展、`NT-C2` 侧命名空间登记（交 T8）；POV 前置 `R1–R4` 登记（交 T8）。
- 是否引入「渲染后 LLM 自检」（默认不引入，§3.3）。

---

*（本文件为 v1.2 叙事/故事层设计草案；核心立场：**世界状态是确定的，只有「怎么讲」是生成的**——事实逐位可追溯、叙事只读不污染、同一日志可多风格重述；戏剧性度量全确定性可重算，LLM 只做绑定锚点的叙述，防幻觉靠「输入约束 + 逐字硬事实校验 + 句级锚点覆盖」三层。待讨论项交 Leader 汇总与 T10 标定。）*
