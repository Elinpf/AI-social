# 06 · 人格生活层（M1/M2/M3/M4/M5/M7）v1.1

> 作者：人格生活层设计专家（persona-life-designer）
> 状态：v1.1 设计草案（供 Leader 汇总；显式区分【已定】与【待讨论】）
> 定位：在 v1「确定性内核」之上**新增**的一层，让 Agent「像在生活」，但**一切判定与记账仍走确定性内核**。
> 对齐基准（权威来源，本文不另立口径）：
> - `v1.1/00-architecture.md`（三层架构、单小镇世界设定、周时间结构、层间接口 IF-1~IF-7、确定性边界）——**总体架构权威**
> - `v1.1/08-engine-stats-extension.md`（Phase 3.5 `LIFE`、L1–L7 hook、事件表、指标命名空间）——**引擎 schema 权威**
> - `v1/03-engine-stats.md`（v1 回合契约、事件外壳、哈希链、重放）——**内核契约权威**
> - `research/town-life-brief.md`（M1–M8 模块清单、Smallville/Agentopia/AI Town 参照）

---

## 0. 阅读指引、设计铁律与约定

### 0.1 本文件覆盖范围
覆盖人格生活层的六个模块：**M1 人格/身份、M2 记忆、M3 关系、M4 日程与活动、M5 场所与昼夜、M7 目标与欲望**。
不覆盖：M6 对话与传播（复用 v1 三通道 + `refs/tag_hints`）、M8 涌现观测层（见 T9 `07`）、经济规则（`v1/01`）、生命周期与反作弊（`v1/02`）、引擎与统计程序实现（`08`/`v1/03`）、沙盒验收（`09`/`v1/04`）。
本文件**回填 `08` §8 与 `00-architecture` §9 要求的取值枚举**（见本文 §10 回填表）。

### 0.2 五条设计铁律（贯穿全文）
| 编号 | 铁律 | 落地方式 |
|---|---|---|
| L-1 | **生成与记账分离**：LLM 只产内容（计划/对话/反思/印象叙述）与意图；判定、数值、时间、场所合法性、关系数值全部由确定性代码负责 | 生活层事件全部经中央裁决器封装落日志（`00` §4.5） |
| L-2 | **意图/事实分离**：生活 hook（L1–L7）**不返回货币 delta**，只返回非货币状态 + `pending_intents`；货币后果交 Phase 4.1–4.8 结算 | 复用 v1 P7 / `08` §2.3 |
| L-3 | **可复现**：决策/检索/判定类输出以事件落日志；统计/重放只折叠日志，**绝不重调 LLM、绝不重算嵌入** | 复用 `08` C4 / X5 |
| L-4 | **LLM 判定冻结**：LLM 的定性判断（如「是否结为密友」）经硬内核「先 RNG 定分支、再 LLM 填充、后冻结」流程落 `LLM_JUDGMENT` | 复用 `00` §4.6 / AR-C3 |
| L-5 | **不设单一「好生活」标量**（v1.1 新增，用户已拍板）：生活层输出**多维福祉向量（WBV）**，不定权重、不合成标量、不作为任何判定或优化目标 | 见 §7.4 |

### 0.3 标记约定
- 【已定】：可直接实现 / 被下游引用；来源为 `00`/`08`/用户拍板，或本文给出明确默认值与可调范围。
- 【待讨论】：给出默认值与备选，交 Leader / 沙盒标定 / `00-architecture` 对齐。
- 参数统一格式：`默认值（可调范围）`；成本统一标注 **LLM 影响**。
- 术语沿用 v1（`round`/`tick`、`slot`、`event`、`hook`、`Delta`、`mu`、`place_id`），字段名用 lower_snake_case。

---

## 1. 生活层总览

### 1.1 生活层在三层架构中的位置
```
┌──────────────────────────────────────────────────────────────┐
│ L2 涌现观测层（T9，只读日志，确定性）                          │
│      metrics(log,T) —— 绝不调 LLM / 不算嵌入                   │
└───────────────▲──────────────────────────────────────────────┘
                │ IF-4 只读
┌───────────────┴──────────────────────────────────────────────┐
│ L1 人格生活层（本文 M1/M2/M3/M4/M5/M7 + 内容生成）             │
│   硬功能：人格/记忆/关系/日程/场所/目标 的状态与意图           │
│   LLM 子模块：软判定层（定性判断）+ 叙事层（纯输出）           │
│   唯一写入通道：IF-2 submit_intent；唯一事实出口：IF-3         │
└───────────────▲──────────────────────────────────────────────┘
                │ IF-1 perceive（只读）
┌───────────────┴──────────────────────────────────────────────┐
│ D0 确定性内核（世界法则 + 裁决器 + 时序 + 账本，v1 冻结）      │
│   P0..P6；生活层挂 Phase 3.5 LIFE（L1..L7）；经济 4.1..4.8     │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 模块地图与依赖
```
M1 人格/身份 ──(初始参数/倾向)──┐
                                ▼
M7 目标/欲望 ──(驱动计划)──► M4 日程与活动 ──(占用场所/共处)──► M5 场所与昼夜
        ▲                        │                                   │
        │                        ▼                                   ▼
        └──(满足度反馈)──── M3 关系 ◄──(相遇/对话)────────────── 偶遇载体
                                │
                                ▼
                           M2 记忆（观测→反思→检索）
```
- **最小可信内核**（`town-life-brief` §5）：M1 + M2 + M4 + M7；M3/M5 提供社会性载体。
- **依赖方向**：M1 是静态配置（无状态）；M2/M3/M7 是 Agent 可增量状态；M4/M5 是行为与空间载体。

### 1.3 与内核接口总览（一次回合端到端，对齐 `00` §1.3）
```
① 感知  IF-1 perceive(agent) -> WorldView（只读：可见事件、场所、status/余额、记忆引用）
② 决策  Phase 2 DECIDE：T0 规则 / T1 小模型 / T2 LLM
          产出 INTENT.PLAN / INTENT.SOCIAL / INTENT.MEMORY / INTENT.RELATION / INTENT.ECON.*
          落 SCHEDULE_PLANNED / GOAL_SET / MEMORY_RETRIEVE（LLM 产物即事件）
③ 沟通  Phase 3 COMMUNICATE：MSG_*（配额与状态分档，v1 不变）
④ 生活  Phase 3.5 LIFE：L1..L7 结算「非货币状态」（时间/场所/活动/需求/关系/记忆/标签）
          货币后果写 state.pending_intents
⑤ 裁决  Phase 4 ARBITRATE：4.1..4.8 结算货币与生命周期（顺序冻结）
⑥ 提交  Phase 6 COMMIT：哈希链追加 + 守恒校验 + 快照 + 指标
```
- 生活层**不新增货币发行/销毁**；活动经济后果仍走 4.1–4.8 与 v1 事件（`08` §6）。

### 1.4 生活层的三个 Agent 私有状态（权威日志派生）
| 状态 | 权威来源（日志） | 私有存储（侧） | 是否参与判定 |
|---|---|---|---|
| 记忆 `MemStore[i]` | `MEMORY_WRITE/RETRIEVE/REFLECT` | 正文 + 嵌入向量（侧存储，哈希引用） | 仅「检索命中列表」参与（已落日志） |
| 关系 `Rel[i][j]` | `RELATION_CHANGE/ENCOUNTER` | 印象叙述文本（侧存储） | 数值参与，文本不参与 |
| 目标/需求 `Goal[i]`/`Need[i]` | `GOAL_*`/`NEED_UPDATE` | 目标描述文本（侧存储） | 数值参与，文本不参与 |

> 关键：**判定只读数值与枚举**，文本仅进 prompt（压缩档案）。保证「不依赖 LLM 判断」可复现。

---

## 2. M1 人格 / 身份（persona）

### 2.1 目标与原则【已定】
- 为每个 Agent 提供**结构化人格**：性格维度、技能、背景、价值观、目标倾向。
- **与引擎解耦**：人格是**静态配置**（离线编写/种子生成），引擎只持 `persona_id` 与**派生标量参数**；在线运行**不重新生成人格**（`00` §5.2 N-1）。
- **可批量配置**：人格以外部文件 `personas.json`（或 `characters.*`）声明，支持按模板 + 种子批量生成（借鉴 AI Town `characters.ts`）。

### 2.2 人格 schema【已定】
```jsonc
// personas.json 单条（引擎只见 persona_id 与 §2.4 派生标量）
{
  "persona_id": "P003",
  "display_name": "青溪镇·阿禾",
  "age": 34,
  "role_id": "farmer",                 // 取自 00 §2.5 角色枚举
  "home_place": "residence",           // 取其住宅
  "personality_big5": {                // 大五，0-100，默认 50
    "openness": 55, "conscientiousness": 70, "extraversion": 40,
    "agreeableness": 65, "neuroticism": 35
  },
  "values": {                          // Schwartz 简化 4 维，0-100（本文新增）
    "self_direction": 60, "benevolence": 70, "achievement": 55, "security": 65
  },
  "skills": [                          // 技能 0-5，默认 1-2 项；映射到 01 L1 生产函数
    {"skill_id": "farming", "level": 3},
    {"skill_id": "cooking", "level": 1}
  ],
  "background": "世代务农，性格内敛，重视邻里……",   // 自由文本，≤200 字
  "goal_tendencies": [                 // 目标倾向（M7 的初始先验）
    {"kind": "security", "weight": 0.6},
    {"kind": "mastery",  "weight": 0.4}
  ],
  "needs_init": {                      // 需求初值（M7，0-100）
    "energy": 80, "satiety": 70, "social": 55,
    "esteem": 60, "mastery": 50, "leisure": 60
  },
  "speech_style": {"tone": "plain", "verbosity": "short"},  // 影响 T1/T2 prompt
  "relations_init": [                  // 可选：初始关系先验（M3）
    {"to": "P007", "affinity": 20, "trust": 30, "respect": 40}
  ]
}
```

### 2.3 批量配置与解耦【已定】
- **文件布局**（与引擎完全解耦）：
  ```
  config/personas.json        # N 条人格（N=10 沙盒 / 20 目标 / 50 展望）
  config/personas_seed.json   # 生成规则：模板 + 人数分布 + 随机种子
  ```
- **生成方式**：`personas = generate(seed, N, role_distribution, template)`——纯确定性；同一 `seed` 产出同一组人格。
- **引擎接口**：引擎启动时读 `personas.json`，为每个 `agent_id` 绑定 `persona_id`，并计算 §2.4 派生标量存入 `AgentState.persona_params`。LLM 侧只在**构造 prompt** 时读人格的**压缩档案**（§3.6）。

### 2.4 人格 → 决策参数的确定性映射【已定】
人格不直接进数值判定；它以两种方式影响行为：
1. **派生标量（确定性函数，供 T0 规则与资格判定）**：
```
work_ethic        = f(conscientiousness)              # 影响 work_required 遵守概率
social_initiative = g(extraversion, agreeableness)    # 影响主动社交/Contact 概率
risk_appetite     = h(openness, neuroticism)          # 影响投资类 T2 触发权重
saving_propensity = j(security value, neuroticism)    # 影响消费/储蓄倾向
```
> **命名边界说明**：`saving_propensity` 仅是**行为倾向**，其货币后果统一走 `INTENT.ECON.*`（存款/取款事件命名由 econ/`01` 决定，见 T14-C3），**06 不定义任何货币事件**；`bank` 场所归入 `trade` affordance（§10）。
2. **prompt 人格段（内容层）**：把 `background + personality + values + speech_style + 当前目标` 压成 ≤200 token 的人格段，注入 T1/T2 的系统提示。

### 2.5 参数与可调范围【已定】
| 参数 | 默认 | 可调范围 | 说明 |
|---|---|---|---|
| 大五维度 | 各 50 | 0–100 | 5 维 |
| 价值观维度 | 各 60 | 0–100 | 4 维 |
| 技能等级 | 1–2 | 0–5 | 每 Agent 1–3 项 |
| 背景长度 | ≤200 字 | 0–400 | 进 prompt 前进一步压缩 |
| `role_distribution` | 见 `00` §2.5 | 8–12 类 | 与小镇角色最小集一致 |

### 2.6 LLM 影响【已定】
- **人格本身：0 次在线调用**（静态配置，离线生成）。
- **人格压缩档案**：每 Agent **初始 1 次**（离线批处理），此后仅在**角色转变/重大反思**后更新（每周上限 1 次）。
- **量级**：N=20（目标）→ 初始 20 次（一次性）；稳态 ≈ 0–1 次/Agent/周。50 为后续展望（`00` r1）。

---

## 3. M2 记忆（memory）

### 3.1 目标与原则【已定】
- 引入 Smallville 式**记忆流**（存储–反思–检索）作为「生活观察」的可信内核。
- **复用 v1 的 append-only + 规范 JSON 机制**：记忆事件进同一哈希链日志；正文与嵌入进侧存储（`00` AR-C4 / `08` XT-3）。
- 借鉴 Agentopia：**文件系统式 scratchpad + read-before-write + 压缩档案进 prompt** 控成本。

### 3.2 存储结构【已定】
**主日志**（哈希链，可审计）：`MEMORY_WRITE / MEMORY_RETRIEVE / MEMORY_REFLECT` 事件（schema 见 `08` §1.2 E），只存**元数据 + 引用**：
```jsonc
{"seq":..., "phase":35, "actor":"P003", "type":"MEMORY_WRITE",
 "payload":{"mem_id":"M-P003-000123","agent_id":"P003","kind":"observation",
            "importance":6,"day":3,"slot":"afternoon","subject":"P007",
            "body_ref":"side://mem/P003/000123.txt","embed_ref":"side://mem/P003/000123.vec",
            "source_event_seq":45678}}
```
**侧存储**（Agent 私有，append-only，按 Agentopia 文件式布局）：
```
side/mem/<agent_id>/general.jsonl        # 计划、长期目标、反思
side/mem/<agent_id>/characters/<other>.jsonl  # 对某人的印象/记忆
side/mem/<agent_id>/others/<topic>.jsonl      # 按主题
side/mem/<agent_id>/<mem_id>.txt              # 正文（哈希校验）
side/mem/<agent_id>/<mem_id>.vec              # 嵌入向量（冻结模型）
```
- **append-only**：`mem_id` 全局唯一、只增不改（新增不变量 `08` §6 式(6)）。
- **read-before-write**：写入前先按 `others/<topic>` / `characters/<other>` 读最近 K 条（K=5），避免与既有记忆矛盾、并为 LLM 提供上下文。

### 3.3 记忆条目 schema【已定】
| 字段 | 类型 | 说明 |
|---|---|---|
| `mem_id` | str | `M-{agent}-{seq}`，全局唯一 |
| `kind` | enum | `observation \| plan \| reflection \| chat` |
| `text` | str | 正文（侧存储） |
| `importance` | int 1–10 | 重要性（LLM 打分，**打分结果落日志后冻结**） |
| `datetime` | (day, slot, tick) | 逻辑时间 |
| `subject` | str? | 关于谁（可空） |
| `embed` | vec | 嵌入向量（冻结模型） |
| `refs` | list[str] | 引用的事件/消息/记忆 id |
| `last_access` | tick | 最近被检索命中时间（recency 用） |
| `access_count` | int | 被检索次数 |

### 3.4 检索打分【已定】
Smallville 式三因子加权（默认等权）：
```
score(m) = w_rec · recency(m) + w_imp · importance(m) + w_rel · relevance(m)
  recency(m)    = decay ^ (now_tick − m.last_access)          # decay 默认 0.995
  importance(m) = m.importance / 10                            # 归一到 0..1
  relevance(m)  = cosine( embed(query), m.embed )              # 归一到 0..1
默认权重 w_rec=1.0, w_imp=1.0, w_rel=1.0
```
- **top_k**：默认 `8`（可调 4–20，对齐 AI Town `NUM_MEMORIES_TO_SEARCH`）。
- **平局打破（L-3 必须）**：`(score desc, last_access desc, mem_id asc)`——全序，保证可复现。
- **命中结果落日志**：`MEMORY_RETRIEVE{agent_id, query_id, top_k, selected_mem_ids[], scores[], weights{...}}`；**重放不再算嵌入**（`08` C4）。

### 3.5 反思触发【已定】
Smallville 式「累积重要性超阈」+ 周相位兜底：
```
反思触发（任一）:
  R1 累积重要性：Σ importance(未反思的 observation, 自上次反思) ≥ θ_reflect
  R2 周节律：REVIEW 相位（day6 evening/night）对每 Agent 强制 1 次
  R3 重大事件：收到/经历 importance ≥ 8 的事件（如死亡、被救助、大型活动）
反思产物：一次反思生成 3–5 条 kind="reflection" 的高层记忆（LLM 产，经裁决器封装）
每 Agent 每窗口反思次数上限 R_max（防成本爆炸）
```
- `θ_reflect` 默认 **150**（可调 100–300；Smallville 论文用 150）。
- R_max 默认 **7 次/周**（= 每日上限 1 次，可调 3–14）。

### 3.6 控成本做法【已定】
1. **压缩档案进 prompt**：进 T1/T2 的不是全量记忆，而是
   - 人格段（≤200 token）+ 当前目标（≤100 token）+ **检索 top_k 记忆摘要**（≤ `M_mem` token，默认 800，可调 400–1500）+ 最近 N 条对话（默认 6）。
2. **importance 批处理**：一次 prompt 为**一批** observation 同时打重要性（默认批 `B_imp=10`），而非逐条调用。
3. **规则回退**：对「低信息量」observation（如例行通勤/常规工作）用 **T0 规则**给固定重要性（默认 2），仅在**含新主体/新话题/情绪词**时调 LLM 打分。
4. **嵌入批量**：observation 写入时批量嵌入（batch，默认 16）。
5. **反思降级**：`LLM_BUDGET` 超限时，R1/R3 反思降级为「写摘要不生成反思」（`LLM_CALL(degraded=true)`）。

### 3.7 参数与 LLM 影响【已定】
| 参数 | 默认 | 可调范围 | LLM 影响 |
|---|---|---|---|
| `top_k` | 8 | 4–20 | 决定 prompt 长度（不增调用数） |
| `decay` | 0.995 | 0.99–0.999 | 无 |
| `w_rec/w_imp/w_rel` | 1/1/1 | 0–2 | 无 |
| `θ_reflect` | 150 | 100–300 | 越低反思越多 → LLM 调用↑ |
| `R_max` | 7/周 | 3–14 | 上限硬约束成本 |
| `M_mem`（记忆摘要 token） | 800 | 400–1500 | 直接决定 token 成本 |
| importance 批 `B_imp` | 10 | 5–20 | 批越大调用越少 |
- **调用量量级**：importance 打分 ≈ `(observations/回合) / B_imp`；嵌入 ≈ `observations / 16`；反思 ≈ `min(触发次数, R_max)`。
- **硬约束**：全部并入 v1 `LLM_BUDGET` 闸门（`08`/`00` §7.2 AR-C5）。

---

## 4. M4 日程与活动（daily/weekly routine & activity）

### 4.1 时间旋回：把「回合」作为底层 tick【已定，对齐 `00` §3】
```
回合(round/tick) ─ 1 时段(slot)=3 回合 ─ 1 日=4 时段=12 回合 ─ 1 周=7 日=84 回合
SLOTS_PER_DAY = [morning, afternoon, evening, night]
DAY_TYPES     = [workday ×5, weekend ×2]
```
- **时段语义**（`00` §3.2）：`morning` 通勤开工/开学；`afternoon` 生产/交易/社交（market 撮合高峰）；`evening` 社交/娱乐/大型活动（种子事件主场）；`night` 休息/睡眠（多数场所关闭）。
- **昼夜**：由 `slot` 直接承载；场所营业时间表为确定性常量（`00` §2.2），非营业时段意图被拒并记 `INTENT_REJECTED`。

### 4.2 周节律与四相位【已定，采纳 D7-2 / AQ3】
采用 Agentopia 式周相位 `WEEK_PHASES = [PLAN, CONTACT, ACTIVITY, REVIEW]`：
| 相位 | 周内位置 | 语义 | LLM 层 |
|---|---|---|---|
| **PLAN** | day0 `morning` | 生成本周计划（目标→slot 分配） | T2（每 Agent 每周 1 次） |
| **CONTACT** | day0–day4 | 主动联系/协商/要约（social initiative） | T1 为主 |
| **ACTIVITY** | day0–day6 | 按日程执行活动 | T0 规则为主 |
| **REVIEW** | day6 `evening`/`night` | 周回顾→反思（触发 R2） | T2（每 Agent 每周 1 次） |

### 4.3 活动抽象【已定】
```jsonc
// activity 实例（计划态存于 SCHEDULE_PLANNED.slots[]；执行态由 ACTIVITY_* 事件表达）
{
  "slot_id": "day3-afternoon",
  "activity_type": "work",           // 枚举见 §10
  "place": "farm",                   // 取自 00 §2.2
  "participants": ["P003"],           // 单人可为空/自指
  "priority": 0.7,                    // 0-1，冲突时确定性择优
  "goal_ref": "G-P003-0002",          // 关联目标（可选）
  "planned_tick": 39
}
```
- **活动类型 → 场所可用性**：由 `place.affordances`（确定性常量）校验；不匹配 → 拒绝。
- **活动结算（L3 settle_activities）**：产出 `ACTIVITY_COMPLETED{outcome, duration_ticks, resource_intents[]}`；`resource_intents` 写 `state.pending_intents`，交 4.1/4.2 结算（L-2）。
- **活动结果数值**（产出量/报酬）由确定性函数（`01` L1 生产函数）给出；LLM 只写**结果叙述**（N-4）。

### 4.4 日程生成与执行流程【已定】
```
[周计划 PLAN]  Phase 2, 每 Agent 每周 1 次（T2 LLM）
     输入：人格段 + 当前目标/需求 + 记忆摘要(top_k) + 上周 REVIEW
     输出：INTENT.PLAN{horizon:"week", slots:[...]} → SCHEDULE_PLANNED
        ↓（硬内核校验：场所合法性/营业时段/容量/相位合法性；不合法→INTENT_REJECTED）
[日解析]      Phase 3.5 L2, 每个日边界执行（T0/T1，默认规则模板 + T1 微调）
     把周计划落到当日 slot；处理临时事件（消息/需求触发）→ SCHEDULE_REVISED
        ↓
[执行]        Phase 3.5 L2→L3：到期 slot 提升为 ACTIVITY_STARTED → 结算 ACTIVITY_COMPLETED/INTERRUPTED
        ↓
[周回顾 REVIEW] Phase 2, 每 Agent 每周 1 次（T2 LLM）→ 触发反思(R2) + 下周计划输入
```
- **执行主体分层**（对齐 v1 T0/T1/T2）：
  - T0（规则）：常规工作/睡眠/进食等**模板活动**，按 `DAY_TYPE_PARAMS` 与 `place` 营业表直接执行；
  - T1（小模型）：日程微调、短社交；
  - T2（LLM）：周计划生成、周回顾、大型活动/种子事件参与。
- **工作日/周末差异**（`00` §3.3）：仅影响行为倾向与事件概率（`work_required/leisure_weight/social_event_prob`），**不改 tick 级经济/生命周期结算**。

### 4.5 唤醒源扩展【已定】
在 v1 W1–W6 基础上新增生活层唤醒源（`00` §6.1）：
```
W7 计划到期：本回合有到期的 slot/活动
W8 需求触发：某需求低于 θ_dep（如 satiety/hunger）
W9 周相位：进入 PLAN / REVIEW 相位
W10 活动邀请/相遇：收到活动邀请或与强关系 Agent 同处
```

### 4.6 参数与 LLM 影响【已定】
| 参数 | 默认 | 可调范围 | LLM 影响 |
|---|---|---|---|
| 周计划生成 | 1 次/Agent/周 (T2) | 1–2 | N 次/周 |
| 日解析 | 规则为主，T1 兜底 | — | ≤ N × 7 次/周（多为 T1） |
| 周回顾 | 1 次/Agent/周 (T2) | 1 | N 次/周 |
| `work_required`/`leisure_weight`/`social_event_prob` | 0.3/0.7；0.05/0.25 | 0–1 | 间接影响活动数→T1 调用 |
| `c_life`（每时段生活调用） | 1.0 | 0.5–3.0 | `00` §7.2 主角 |

- **回合计数量级**（`00` §3.4）：1 周 = **84 回合**；1–2 周基线 = 84–168；4 周 = 336；12 周 = 1008。
- **成本对照**（`00` §7.2）：每 Agent 每周 ≈ 42 次生活/社交调用（T1 为主）；N=10 沙盒周 ≈ 4×10² 次 / 10⁶ token，**N=20 目标周 ≈ 8×10² 次 / 2×10⁶ token**（50 为展望）。

---

## 5. M5 场所与昼夜（places & day/night）

### 5.1 单小镇世界设定【已定，引用 `00` §2】
- **青溪镇（Qingxi Town）**，单一小镇、闭合经济系统（生产→交易→消费→税收/再分配镇内闭环）。
- **场所清单：默认 17 处**（可调 12–24），权威枚举见 `00` §2.2：`residence / farm / workshop / kitchen / clinic / school / office / market / bank / plaza / town_hall / library / community_center / cafe / park / hall / gate`。
- **角色最小集：默认 10 类**（`00` §2.5）：`farmer / craftsman / cook / merchant / healer / teacher / public_servant / banker / artist / student|unemployed`。
- **拓扑**：中心–外围（`plaza` 枢纽），`travel_ticks` ∈ {1,2,3}（确定性）。

### 5.2 场所数据与引擎解耦【已定】
- **数据落 config，不进代码**：`config/places.json` + `config/topology.json`（17×17 常数矩阵，建议落定值保复现，`00` AR-D2）。
```jsonc
// places.json 单条
{
  "place_id": "farm",
  "name_cn": "农场",
  "category": "work_production",
  "affordances": ["work"],                  // 允许的 activity_type
  "open_slots": ["morning","afternoon"],    // 营业时段（确定性）
  "capacity": 6,
  "owner_role": "farmer",
  "produces": ["food"]
}
```
- **引擎只见**：`agent.location`（place_id）+ `places.json` 校验函数；引擎不感知场所语义。场所"数据"由玩法层维护（镜像 AI Town 的 Tiled JSON 解耦思路）。
- **合法性校验（确定性，D-9）**：`PLACE_MOVE.to_place ∈ 合法集合`、容量未超、营业时段匹配；否则 `INTENT_REJECTED`。

### 5.3 昼夜与偶遇机制【已定】
- **昼夜**：`night` 段多数场所关闭（`open_slots` 不含 `night`）→ 活动/移动意图被拒；`residence` 全天开放（睡眠/居家/私密对话）。
- **相遇/偶遇（RELATION_ENCOUNTER）**：
  - **定义**：同 `place`、同 `round` 的在场合 Agent 对（排除自己）。
  - **确定性枚举**：按 `agent_id` 升序两两配对；仅记录**首次共处**或**共处超阈**（`duration_ticks ≥ D_enc`）的相遇（`08` 存储节流：避免 O(N²) 事件爆炸）。
  - **`D_enc` 默认 3 tick**（= 1 时段，可调 1–12）。
- **活动载体**：活动通过 `place.affordances` 绑定场所；`hall` 为大型活动/种子事件主场（`00` §2.2）。

### 5.4 参数与 LLM 影响【已定】
| 参数 | 默认 | 可调范围 | LLM 影响 |
|---|---|---|---|
| 场所数 | 17 | 12–24 | 无（静态） |
| 场所容量 | 见 `00` §2.2 | — | 超容拒绝，间接影响活动 |
| `D_enc`（相遇记录阈值） | 3 tick | 1–12 | 无（节流事件量） |
| `travel_ticks` | 1–3 | 固定 | 无 |
- **LLM 影响：M5 本身 0 调用**；仅通过「场所可用性」间接约束活动与对话。

---

## 6. M3 关系（Agent 视角的关系状态）

### 6.1 目标与原则【已定】
- 提供 **Agent 视角的、有向的**关系状态（v1 只有全局金钱图/沟通图，无 Agent 视角）。
- **数值一律由确定性函数更新**（`00` AR-C3 / D-12）；LLM 只产**印象叙述**（N-6），**绝不定数值**。

### 6.2 关系状态 schema【已定】
```jsonc
// Rel[i][j]：有向，i 对 j 的看法
{
  "from": "P003", "to": "P007",
  "affinity": 25,     // 喜爱/好感  [-100, 100]
  "trust": 40,        // 信任       [-100, 100]
  "respect": 55,      // 尊重       [0, 100]
  "familiarity": 30,  // 熟悉度 0-100（由交互次数累积，单调不减）
  "last_interaction_round": 78,
  "interaction_count": 12,
  "impression_ref": "side://rel/P003/P007.txt"   // 印象叙述（不进判定）
}
```
- **值域**：`[W_MIN, W_MAX] = [-100, 100]`（`respect` 额外钳制到 `[0,100]`）。
- **阈值**：`ε = 20`（弱关系存在阈），`ε_strong = 50`（强关系阈）——供 T9 `07` 图指标使用。

### 6.3 关系更新函数【已定】
确定性函数，输入 `cause`（事件类型 + 数值），输出 delta（夹取到值域）：
```
update_rel(cause, dim) -> delta:
  CHAT/共处(duration):   affinity += k_a·min(duration, cap) · sign(现有affinity倾向)
  TRADE合作成功:          trust    += k_t · log(1+amount) ; affinity += k_a2
  TRANSFER救助(from→to):  to.affinity += k_rescue ; to.trust += k_t2  (受助方对施助方)
  SSL反作弊标记(flags):   trust    -= k_pen
  ENCOUNTER重复:          familiarity += 1 (上限 100)
  非法/无 cause:           delta = 0
  全部 delta 最后 clamp 到 [W_MIN, W_MAX]
```
- 系数（默认，可调）：`k_a=1, k_t=2, k_a2=1, k_rescue=8, k_t2=6, k_pen=5`（每次交互幅度上限 ≤ `Δ_max=10`）。
- **软判定（可选，L-4）**：涉及「关系性质质变」的判断（如是否结为密友/师徒）走 IF-2b：硬内核先 RNG 定 envelope，LLM 在 envelope 内给**定性标签**，冻结为 `LLM_JUDGMENT`，再由 D-12 函数把标签映射为数值 delta。

### 6.4 关系 → 福祉维度【已定，L-5】
- 关系数值供 T9 计算 **PageRank(G_rel, dim)**、互惠性、强关系形成率等（`08` §4.3）。
- 在生活层的**福祉向量**中，关系维度取「对该 Agent 的入边强度聚合」（详见 §7.4），**不合成单一分数**。

### 6.5 参数与 LLM 影响【已定】
| 参数 | 默认 | 可调范围 | LLM 影响 |
|---|---|---|---|
| `W_MIN/W_MAX` | −100/100 | 固定 | 无 |
| `ε / ε_strong` | 20 / 50 | 10–30 / 40–70 | 无 |
| `Δ_max`（单次幅度上限） | 10 | 5–20 | 无 |
| 印象叙述生成 | 每次深度交互 1 次 | — | 可批量；≤ 交互数/回合 |
| 关系质变软判定 | 仅质变时 1 次 | — | 低频（envelope 触发） |
- **主力零调用**：数值更新 0 LLM；仅「印象叙述」与「质变判定」调 LLM，且可批处理/降级。

---

## 7. M7 目标与欲望（goals & needs）+ 福祉向量

### 7.1 目标（goals）【已定】
```jsonc
{
  "goal_id": "G-P003-0002",
  "agent_id": "P003",
  "layer": "growth",                 // 生存|成长|社交|意义（枚举）
  "description_ref": "side://goals/P003/0002.txt",  // 文本（LLM 产）
  "priority": 0.7,                   // 0-1
  "target_metric": "skill.farming",  // 可确定性追踪的指标（可选）
  "progress": 0.3,                   // 0-1
  "deadline_week": 4,                // 可空
  "status": "active"                 // active|done|abandoned
}
```
- **来源**：初始 `goal_tendencies`（M1）+ PLAN 相位 LLM 生成/更新（`GOAL_SET` 经裁决器封装）。
- **进度**：`GOAL_PROGRESS` 由确定性规则从活动/事件推导（如 farming 技能提升 → mastery 目标进度↑）。

### 7.2 欲望/需求（needs）【已定】
- **维度（本文回填 `08` §8 的 `need.dim[]`）**：`energy（体力）、satiety（饱腹）、social（社交）、esteem（尊重/成就）、mastery（成长/求知）、leisure（休闲）`，共 6 维，值域 0–100。
- **动态**（确定性，D-11）：
```
每 slot 自然衰减：need -= decay[dim]        （如 satiety −8/时段，social −5/时段）
活动满足       ：need += satisfaction[activity_type][dim]（如 self_care 补 satiety/energy）
clamp 到 [0, 100]；变更记 NEED_UPDATE
```
- **剥夺阈值** `θ_dep`（`08` D7-3，本文回填）：默认 `20`（可调 10–35）；低于阈值触发 W8 唤醒与寻求活动。

### 7.3 目标/需求 → 行为【已定】
- 需求缺口 → 活动优先级提升 → 影响 L2 日程解析（追求满足）。
- 目标 → 周计划倾向（PLAN 相位）；目标达成 → 提升 `esteem/mastery` 需求（正反馈）。

### 7.4 福祉向量 WBV（**替代单一 life reward**）【已定，用户拍板】
> **重要口径（用户 2026-10-09 拍板，记为【已定】，不再作为开放问题）**：
> 1. 生活层**输出多维向量**（社会地位 / 主观满足 / 经济 / 健康 / 关系 / 成长 / 意义），**不合成标量、不定权重**。
> 2. 我们**不设单一 `life reward` 标量**，因此**不存在三维权重**（Agentopia 的 0.4/0.4/0.2 是**训练信号**，我们是**观察实验、不训练**，不适用）。
> 3. 若需便于人读的汇总指数 `WBI`，**仅供呈现**：必须写明权重假设、附**敏感性分析**，且**绝不作为任何判定或优化目标**（与 T15「禁止单分数优化」一致）。

**WBV 定义（7 维，各自独立，均可从日志确定性重算）**：
| 维度 | 符号 | 口径（确定性来源） | 单位/范围 |
|---|---|---|---|
| 社会地位 | `wbv.status` | 入边 PageRank(G_rel, respect) 归一（T9 `08` §4.3） | 0–1 |
| 主观满足 | `wbv.satisfaction` | 6 维 need 的**向量本身**（不取均值；如需展示再定） | 6×0–100 |
| 经济 | `wbv.economic` | 窗口净财富变化（v1 `net_worth` 差分） | mu |
| 健康 | `wbv.health` | `energy + satiety` 相关指标（由 NEED_UPDATE 折叠） | 0–100 |
| 关系 | `wbv.relation` | 入边 affinity/trust 聚合（有向好友数、互惠边数） | 计数/0–100 |
| 成长 | `wbv.growth` | 技能提升次数 + mastery 目标进度 | 计数/0–1 |
| 意义 | `wbv.meaning` | 达成目标数、`self_direction/benevolence` 相关活动参与 | 计数 |

- **明确禁止**：对 WBV 做加权求和作为判定输入；`llm_judged_metric_count == 0` 铁律对 WBV 同样适用。
- **可观测的「背离」**：各维度独立输出后，才能观测「富而不乐」「地位降而幸福升」等背离——这正是本实验的核心观测对象，故**必须保留维度、禁止压平**。
- 建议落地：WBV 快照写入 `metrics.life.wbv`（多键），`WBI`（若呈现）写入 `metrics.life.wbi` 并标注 `assumption_ref` 与 `sensitivity`。

### 7.5 参数与 LLM 影响【已定】
| 参数 | 默认 | 可调范围 | LLM 影响 |
|---|---|---|---|
| 目标生成/更新 | PLAN 相位 1 次/Agent/周 (T2) | 1 | N 次/周 |
| need 维度 | 6 | 4–8 | 无 |
| `decay[dim]` | 见 §7.2 | 1–15/时段 | 无 |
| `θ_dep` | 20 | 10–35 | 缺口越多→活动越多→T1↑ |
| WBV 计算 | 纯统计（T9） | — | **0 LLM** |

---

## 8. 与确定性内核的接口（不得绕过裁决器）

### 8.1 生活层写入路径【已定，对齐 `00` §4.5】
```
LLM/规则 --(INTENT)--> IF-2 submit_intent --(裁决器校验)--> 事实事件 --(IF-3 emit)--> 哈希链日志
                              │
                              └─不合法--> INTENT_REJECTED（审计，不产生状态变化）
```
四条强制机制：
1. 生活 hook（L1–L7）**不返回货币 delta**，只返回非货币状态 + `state.pending_intents`；
2. 货币后果统一由 4.1–4.8 校验结算；守恒校验会暴露任何「无事件记账」；
3. 生活事件必须携带完整 `payload`（C4/X6），否则重放硬报错；
4. 统计/重放遇未知事件类型立即报错（`08` X4）。

### 8.2 生活层事件 → 日志（事件族映射，对齐 `08` §1.2 / `00` §4.3）
| 模块 | 事件类型 | 阶段 | 关联 hook |
|---|---|---|---|
| M5 场所/时间 | `TIME_MARK`、`PLACE_MOVE`、`PLACE_ARRIVED` | 3.5 | L1 |
| M4 日程/活动 | `SCHEDULE_PLANNED/REVISED`、`ACTIVITY_STARTED/COMPLETED/INTERRUPTED` | 2 / 3.5 | L2 / L3 |
| M7 需求/目标 | `NEED_UPDATE`、`GOAL_SET/PROGRESS/ACHIEVED` | 2 / 3.5 | L4 |
| M3 关系 | `RELATION_CHANGE`、`RELATION_ENCOUNTER` | 3.5 | L5 |
| M2 记忆 | `MEMORY_WRITE/RETRIEVE/REFLECT`、`OBSERVATION` | 2 / 3.5 | L6 |
| （M6/M8） | `MSG_*`+refs、`TAG_EMITTED`、`SEED_EVENT`、`NORM_*`、`ROLE_CHANGE` | 3 / 3.5 | L7 / T9 |
| 成本/审计 | `LLM_CALL(+purpose)`、`LLM_JUDGMENT(frozen)`、`NARRATIVE`、`INTENT_REJECTED` | 任意 | — |

- **生活层额外审计字段**（`08` §1.1）：所有生活事件必带 `day / slot / day_type / place`。
- **本职注意**：`INTENT_REJECTED` 由 `00` AR-C1 新增，**已在 `08` §1.2 H 登记**（payload: `agent_id, intent_class, reason, requested`）——OQ-L11 已关闭。

### 8.3 生活层新增不变量（并入 v1 §5.9 / `08` §6 校验集）【已定】
```
(L1) 关系值域：RELATION_CHANGE 折叠后 w_dim ∈ [W_MIN, W_MAX]（respect ∈ [0,100]），越界报错
(L2) 需求值域：NEED_UPDATE.after ∈ [0,100]
(L3) 场所合法性：PLACE_MOVE.to_place ∈ 合法场所集；to_place 营业时段匹配
(L4) 日程一致性：ACTIVITY_STARTED.slot_id 必须存在于该 agent 的 SCHEDULE_PLANNED/REVISED
(L5) 记忆 append-only：mem_id 全局唯一、只增不改；哈希链覆盖记忆事件
(L6) 观测锚点：OBSERVATION.target_event_seq 指向已存在事件
(L7) 统计无 LLM 判定：llm_judged_metric_count == 0
(L8) 意图/事实分离：生活 hook 输出不含货币 delta（结构层校验）
```

### 8.4 统计口径对接【已定】
- v1 经济/生命周期指标口径**冻结**；生活层新增指标入 `metrics.life.*`（活动参与、需求满足、关系演化、记忆指标、WBV），涌现入 `metrics.emergence.*`（T9）。
- **WBV 与关系图指标**由 T9 从日志确定性重算；本文只定义**数值来源与口径**，不实现。

### 8.5 复现保证【已定】
- 生活层所有**决策/检索/判定**结果落日志；重放只折叠日志，**不重调 LLM、不重算嵌入**（L-3）。
- 嵌入模型**冻结版本并写入 `engine_version`**（建议采纳 `08` D7-6 / `00` AR-C5，否则同 seed 首跑不可复现）。

---

## 9. 参数总表与 LLM 成本总览

### 9.1 模块默认参数速查
| 模块 | 关键参数 | 默认 | 可调范围 |
|---|---|---|---|
| M1 | 大五/价值观维度 | 50 / 60 | 0–100 |
| M1 | 人格压缩档案 token | ≤200 | 100–400 |
| M2 | `top_k` | 8 | 4–20 |
| M2 | `decay` | 0.995 | 0.99–0.999 |
| M2 | `θ_reflect` | 150 | 100–300 |
| M2 | `R_max` | 7/周 | 3–14 |
| M2 | `M_mem`（记忆摘要 token） | 800 | 400–1500 |
| M4 | 周计划/周回顾 | 1/1 次/Agent/周 | 1–2 |
| M4 | `c_life` / `c_social` | 1.0 / 0.5 | 0.5–3.0 / 0.2–1.5 |
| M5 | 场所数 / `D_enc` | 17 / 3 tick | 12–24 / 1–12 |
| M3 | `ε / ε_strong` / `Δ_max` | 20 / 50 / 10 | 见 §6.5 |
| M7 | `need` 维度 / `θ_dep` | 6 / 20 | 4–8 / 10–35 |

### 9.2 每模块 LLM 调用影响【已定】
| 模块 | 调用来源 | 频率（默认） | 成本敏感度 |
|---|---|---|---|
| M1 | 人格压缩档案 | 初始 1 次/Agent；稳态 ≤1/周 | 低 |
| M2 | importance 打分（批量）+ 嵌入 + 反思 | `obs/B_imp` + `obs/16` + `min(触发,R_max)` | **高**（obs 数量驱动） |
| M4 | 周计划 + 周回顾 + 日解析(T1) | 2×N/周 + ≤7N/周(T1) | **高** |
| M5 | — | 0 | 无 |
| M3 | 印象叙述 + 质变软判定 | ≤交互数/回合计；质变低频 | 中 |
| M7 | 目标生成/更新 | 1×N/周(T2) | 中 |
- **全部并入 v1 `LLM_BUDGET` 闸门**；超限降级优先级：濒死求生 > 投资/结盟 > **周计划/反思** > 印象叙述/日解析（`00` §7.2 / v1 §3.3）。
- **量级对齐 `00` §7.2（r1 规模口径：沙盒 10 / 目标 20 / 展望 50）**：每 Agent 每周 ≈ 42 次（T1 为主）；N=10 周 ≈ 4×10² 次；**N=20 目标周 ≈ 8×10² 次 / 2×10⁶ token**；N=50 周 ≈ 2×10³ 次（展望）。**注意**：v1「≤8 次 LLM/回合」不再适用（AR-C5），须由 T8/T10 按新模块、按 N=20 重算（合并 `00` AR-D5）。

---

## 10. 枚举回填表（供 `08` §8 / `00` §9）

| 回填项 | 取值（本文定义） |
|---|---|
| `need.dim[]` | `energy, satiety, social, esteem, mastery, leisure`（6 维，0–100） |
| `activity_type[]` | `work, learn, socialize, leisure, self_care, civic, trade, rest`（8 类） |
| `activity_type → place.affordances` | `work→farm/workshop/kitchen/clinic/school/office/market`；`learn→school/library`；`socialize→cafe/plaza/park/community_center/hall`；`leisure→park/cafe/hall`；`self_care→residence/clinic/kitchen`；`civic→town_hall/plaza`；`trade→market/bank`；`rest→residence` |
| `RELATION_CHANGE.dim` 与值域 | `affinity[-100,100], trust[-100,100], respect[0,100]`；`W_MIN/W_MAX=-100/100`；`ε=20, ε_strong=50` |
| `θ_reflect` | 150（100–300） |
| `θ_dep(dim)` | 20（10–35），各维相同默认 |
| `WEEK_PHASES` 映射 | `[PLAN(day0 morning), CONTACT(day0–4), ACTIVITY(day0–6), REVIEW(day6 evening/night)]` |
| `tag` 产生方式 | 由内容层（M6/M8，T9）从消息/活动产出 `tag_hints`；生活层仅提供 `activity_type/place` 话题先验；`valence ∈ {-1,0,1}` |
| `NORM rule_ref` 格式 | `rule_ref = "norm:{scope}:{predicate}:{threshold}"`，如 `norm:plaza:no_shout_at_night:majority`（判定由硬内核阈值，非 LLM） |
| `needs decay` | `satiety −8, energy −4, social −5, esteem −2, mastery −1, leisure −6`（每时段，可调） |

---

## 11. 「已定」与「待讨论」汇总

### 11.1 已定（可被下游直接引用）
- **总览**：生活层三层定位、模块地图、端到端接口、三个 Agent 私有状态与「判定只读数值」原则（§1）。
- **M1**：人格 schema、批量配置与解耦、人格→决策参数映射（§2）。
- **M2**：存储结构（主日志 + 侧存储）、条目 schema、检索打分（recency/importance/relevance + 全序）、反思触发（θ_reflect=150 / R2 周回顾 / R_max）、五项控成本做法（§3）。
- **M4**：周旋回（1 周=84 回合）、周相位 PLAN/CONTACT/ACTIVITY/REVIEW、活动抽象、日程生成与执行流程、唤醒源 W7–W10（§4）。
- **M5**：单小镇世界设定（青溪镇、17 场所、10 角色，引用 `00` §2）、场所数据解耦、昼夜与偶遇机制（§5）。
- **M3**：关系 schema、确定性更新函数（数值非 LLM）、阈值 ε/ε_strong（§6）。
- **M7**：目标 schema、需求 6 维与动态、**福祉向量 WBV（不设单一标量奖励，用户拍板）**（§7）。
- **接口**：写入路径、事件族映射、生活层新增不变量 L1–L8、统计口径与复现保证（§8）。
- **枚举回填**（§10）：`need.dim`、`activity_type`、关系 dim 值域、θ_reflect、θ_dep、WEEK_PHASES、tag 来源、norm rule_ref 格式。
- **记忆存储口径**（原 OQ-L5，Leader 裁决关闭）：记忆 `body` 入**侧存储 + 哈希引用**，主日志只存 `body_ref/embed_ref`（§3.2）。
- **嵌入可复现**（原 OQ-L6，Leader 裁决关闭）：嵌入模型名/版本**冻结并写入 `engine_version`**（§8.5）。
- **规模口径对齐**（`00` r1）：沙盒 10 / **目标 20** / 展望 50；本文成本例与人格批量配置已按此对齐。

### 11.2 待讨论（开放问题）
| 编号 | 事项 | 默认/倾向 | 备选 | 归属 |
|---|---|---|---|---|
| OQ-L1 | 周计划生成用 T2 还是可降到 T1 | T2（保证计划质量） | T1 模板 + 每周 1 次 T2 | T10 标定 |
| OQ-L2 | importance 打分的 LLM 模型与批量策略 | 轻量模型 + `B_imp=10` | 规则回退为主 | T10 标定 |
| OQ-L3 | 关系「质变」软判定的 envelope 阈值 | 暂用 ε_strong 触发 | 由 T10 用例定 | T8/T10 |
| OQ-L4 | WBV 各维度的精确口径与归一 | 见 §7.4 | 由 T9 细化 | T9 |
| ~~OQ-L5~~ | ~~记忆 `body` 是否入主日志~~ | **已关闭（Leader 裁决）**：入侧存储 + 哈希引用（采纳 `00` AR-C4） | — | 已定 |
| ~~OQ-L6~~ | ~~嵌入模型是否冻结进 `engine_version`~~ | **已关闭（Leader 裁决）**：冻结，写入 `engine_version`（采纳 `08` D7-6 / `00` AR-C5） | — | 已定 |
| OQ-L7 | 日程严格遵守 vs 允许漂移 | 允许漂移（事件驱动修订） | 强约束 | T10 |
| OQ-L8 | `D_enc`、`θ_dep`、各 decay 系数标定 | 见 §10 | 沙盒扫描 | T10 |
| OQ-L9 | 是否加 `blackmarket`/`shelter` 场所 | 默认不加（采纳 `00` AR-D1） | 反作弊用例需要则加 | T10 |
| OQ-L10 | `TOPOLOGY` 显式矩阵 vs 环层近似 | 显式常数矩阵（保复现，`00` AR-D2） | 环层近似 | T8 |
| ~~OQ-L11~~ | ~~`INTENT_REJECTED` 事件补登~~ | **已关闭**：`08` §1.2 H 已登记（`00` AR-C1） | — | 已定 |
| OQ-L12 | 是否扩角色到 12（courier/journalist） | 默认 10（`00` AR-D3） | 由 T9 传播范式需要提 | T9 |
- **说明**：用户已拍板的两项（单小镇、模拟周）**不再是开放问题**；`life reward 标量`已按用户口径**改为 WBV 多维向量**，**不再作为开放问题**。

---

## 12. 与下游引用指引

| 下游 | 可直接引用本文 | 需注意 |
|---|---|---|
| **T8 引擎扩展** | §10 枚举回填表（need/activity/relation dim/θ_reflect/θ_dep/WEEK_PHASES/tag/norm）、§8 不变量 L1–L8 | 补登 `INTENT_REJECTED`（OQ-L11） |
| **T9 涌现观测** | §6 关系阈值、§7 WBV 维度、§3 记忆指标来源 | 关系数值确定性来源确认（AR-C3 已满足） |
| **T10 沙盒** | §4 回合计数量级、§9 LLM 成本与降级优先级、§11 待标定项 | 成本预算须重算（AR-C5） |
| **`00-architecture` 对齐** | §5 场所/角色引用、§4 时段语义与周节律 | 若 `00` 后续改动 `place`/`slot` 枚举，本文同步 |

---

*（全文完 — persona-life-designer。本文所有「已定」项与 `00`/`08`/v1 契约一致；「待讨论」项交 Leader 汇总与沙盒标定。）*
