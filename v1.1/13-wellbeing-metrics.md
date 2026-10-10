# 13 · 生活质量 / 幸福感观测指标体系（超越金钱）v1.1

> 文档类型：领域设计（观测层一等交付）｜ 作者：emergence-observer-designer（涌现观测层设计专家）
> 状态：v1.1 设计草案（供 Leader 汇总；标注【已定】/【待讨论】/【冲突】）
> 上游依据：
> - `v1.1/00-architecture.md`（T12 架构：三层、单小镇、周尺度、只读契约 IF-4、软判定冻结 §5.5；**r1：目标规模 N=20**）
> - `v1.1/08-engine-stats-extension.md`（T8 事件表 §1.2、`metrics.life/.emergence` §4）
> - `v1.1/07-emergence-observation.md`（T9 观测框架：铁律 R1–R7、D/F/K 三级分类、命名空间、复现口径）
> - `research/town-life-brief.md` + `v1.1/11-agentopia-reuse-assessment.md`（Agentopia life reward 三维与「社会奖励下降但主观幸福上升」等背离案例）
> 下游对齐：`v1.1/09-sandbox-v1.1.md`（T10 需本层给出「哪些 well-being 指标进观测判据」）
> 标签约定：**【已定】**=本轮基线；**【待讨论】**=语义未收敛，交 Leader/用户/T7 标定；**【冲突】**=与上游不一致，须回写消解。

---

## 0. 定位、原则与铁律继承

### 0.1 定位（【已定】）

用户明确指出：**金钱不能代表人的全部**。Agentopia 用 life reward（社会地位 + 主观满足 + 经济）映射人类福祉；本层据此把「幸福感 / 生活质量」从**单一经济维度**扩展为**多维观测指标体系**，作为 v1.1 观测层的**一等公民**（不是附加项）。

- **本层复用 T9 的观测框架**（铁律 R1–R7、D/F/K 三级分类、只读日志、命名空间隔离），**新增命名空间 `metrics.wellbeing.*`**（§6）。
- 产物形态同 T9：`wellbeing_report(log, T, params)` 为**可复现侧产物**，不入世界日志、不影响状态。

### 0.2 核心原则（【已定】）

| # | 原则 | 说明 |
|---|---|---|
| **P1** | **激励 / 观测分离** | 金钱、UBI、代谢、税收、价格工资等是**激励层（输入，机制）**；W1–W7 是**观测结果（输出）**。二者不得混同（§2）。 |
| **P2** | **禁止单一分数优化** | **严禁**把多维幸福度合成单一 scalar reward 去优化、训练或调参。幸福度只作**分项 + 多维向量**呈现（§2.3）。 |
| **P3** | **判定归属无歧义** | 每维标明 D（纯确定性）/ F（含 LLM 冻结判定）；F 类计算时 `llm_calls==0`、标 `frozen_llm`、与 D 类**分栏列示**（§3，继承 T9 R2–R4）。 |
| **P4** | **硬内核不接 LLM** | 金额 / 死亡 / 交易类指标（K）绝不以 LLM 判定为输入（T9 R5、T12 §1.5）。 |
| **P5** | **可复现可审计** | D 类从日志确定性重算；F 类可追溯 `model/version/context_digest`（§5）。 |

> **F 类地位（继承 Leader 对 T9-D3 的定论 + WB-C2 裁决「采纳」）**：所有含 LLM 冻结判定的 well-being 指标（`metrics.wellbeing_soft`）**只作敏感性分析/描述，不进判定路径、不进沙盒门禁**；核心判定保持 `llm_judged_metric_count == 0`。**因此主观满足感（W3）等 F 类维度是「被观测、被报告」的幸福感核心，但不作为自动验收门禁**——这是方案甲（冻结 LLM 判定）下的有意权衡。**WB-C2（【已定】）**：F 类须在**长窗实验**作为一等观测结果**重点报告**、在 v1.1 开放问题中**单列一条**、并同时给出 `frozen_llm` 来源标注与**敏感性分析**（见 §8）。

---

## 1. 维度集：含义、观测口径与判定归属

> 至少 7 维。每维给出：**含义 / 观测口径 / 来源事件 / 指标 / 判定归属（D/F/K）/ 沙盒地位**。阈值为符号 + 默认建议，标【待标定】者依赖 T7（`D7-3`）或 T10。

### 1.1 维度总表（【已定】清单，取值部分【待讨论】）

| # | 维度 | 含义 | 判定归属 | 主来源 | 沙盒地位 |
|---|---|---|---|---|---|
| **W1** | 经济状况 | 物质资源保障与稳定（**仅一维，不代表全部**） | **D** | `TRANSFER/MARKET_TRADE/TAX/UBI/METABOLISM/LOAN_*` | 描述（D） |
| **W2** | 社会地位 | 声望 / 被尊重 / 被喜爱 / 影响力 | **D + F** | `G_rel`（T9 §1.2）、`MSG_*`、`LLM_JUDGMENT`(respect/affection) | D 部分可入判据；F 部分描述 |
| **W3** | 主观满足感 | 情绪 / 物质 / 社交 / 尊重 四维满足（Agentopia 式） | **F**（+D 代理） | `LLM_JUDGMENT`(satisfaction)、`NEED_UPDATE` | **仅描述/敏感性** |
| **W4** | 健康 | 身体 / 精力状态 | **D** | `NEED_UPDATE`(health/energy)、`clinic` 活动 | 描述（D） |
| **W5** | 关系质量 | 关系强度 / 互惠 / 支持可获得性 | **D** | `G_rel`、`RELATION_ENCOUNTER`、求助响应 | 可入判据（D） |
| **W6** | 技能 / 成长 | 技能提升、学习、目标达成 | **D**（依赖 T7 技能事件） | 技能事件（T7/T8 补）、`GOAL_*`、`school/library` 活动 | 描述（D） |
| **W7** | 自主与意义感 | 自主选择、目标意义、节奏掌控 | **D 代理 + F** | `SCHEDULE_*`、`ACTIVITY_*`、`GOAL_SET`、`LLM_JUDGMENT`(meaning) | D 代理可入判据；F 描述 |

### 1.2 W1 · 经济状况（D）

- **含义**：物质资源保障与稳定（生活/生产/消费能力），**仅是幸福感的一个维度**。
- **口径与指标**（全部由 v1 经济事件折叠，D）：
  - `net_worth_i`（净财富，v1 口径）与 `wealth_percentile_i`（分位）；
  - `income_weekly`（周收入 = 出售/工资类流入）；
  - `consumption_weekly`（周消费 = 购买 `food/meal/tool` 等）；
  - `financial_security_rounds = cash_i / metabolism_per_round`（现金可支撑回合数，抗风险能力）；
  - `income_trend`（周收入一阶差分）。
- **来源**：`TRANSFER/MARKET_TRADE/TAX_LEVIED/UBI_PAID/METABOLISM/LOAN_*`。
- **归属**：D（**K 级经济指标的派生展示**，口径冻结于 v1，不重定义）。

### 1.3 W2 · 社会地位（D + F）

- **含义**：他人眼中的声望、被尊重、被喜爱、以及社会影响力。
- **D 口径**（结构地位，复用 T9 §1.2 / T8 §4.3 的 `G_rel`）：
  - `pagerank_rank_i`（`G_rel` 上的 PageRank 排名，固定 `d=0.85`、固定 K 次、`agent_id` 升序 tie-break）；
  - `incoming_strong_ties_i`（入向强关系边数，`≥ ε_strong`）；
  - `cited_count_i`（被 `MSG_*` 的 `refs` 指向次数）；
  - `governance_influence_i`（`NORM_PROPOSED` 提案被 `NORM_ADOPTED` 采纳的比率）。
  - 指标：`social_status_D = {pagerank_rank, incoming_strong_ties, cited_count, governance_influence}`。
- **F 口径**（Agentopia 式互评，**冻结**）：读 `LLM_JUDGMENT.dimension ∈ {respect_score, affection_score}`（Agent→Agent 互评及环境评估，`frozen=true`）→ `metrics.wellbeing_soft.social_status_llm = {respect_mean, affection_mean, liked_by_count}`，标 `frozen_llm`。
- **来源**：`RELATION_CHANGE`/`MSG_*`/`NORM_*`（D）；`LLM_JUDGMENT`（F）。
- **归属**：D + F（**分栏**）。

### 1.4 W3 · 主观满足感（F，+D 代理）

- **含义**：Agent 自身的主观满足，含**情绪 / 物质 / 社交 / 尊重**四子维（对齐 Agentopia subjective reward 四维）。
- **F 口径（主）**：读 `LLM_JUDGMENT.dimension="satisfaction"` 的冻结判定（软判定层产出、硬内核封装、`frozen=true`），四子维：
  `subj_emotion / subj_material / subj_social / subj_esteem`（值域与打分口径由 T7/软判定层定）。
  指标 → `metrics.wellbeing_soft.subjective = {subj_emotion, subj_material, subj_social, subj_esteem}`，标 `frozen_llm`，可追溯 `model/version/context_digest`。
- **D 代理（辅，客观侧）**：`NEED_UPDATE` 折叠出的 `need_level{dim}`（T8 §4.2）作为**客观代理**（如 hunger/energy 满足），不是主观满足本身。
- **归属**：**F**（主观满足必须走冻结 LLM 判定，方案甲）；D 代理单列。
- **沙盒地位**：**仅描述 / 敏感性**（依 T9-D3 定论）。

### 1.5 W4 · 健康（D）

- **含义**：身体与精力状态。
- **口径**：`NEED_UPDATE` 的 `health` / `energy` 维度折叠值（T8 §1.2-C）；`clinic` 场所就医/恢复活动次数；`deprivation_rate(health)`（低于阈值 θ_dep 的比例）。
- **指标**：`health_level, energy_level, clinic_visits, health_deprivation_rate`。
- **来源**：`NEED_UPDATE`、`ACTIVITY_*`（`place=clinic`）。
- **归属**：D。**依赖 T7 定义 need 维度枚举（health/energy）**——【待讨论】。

### 1.6 W5 · 关系质量（D）

- **含义**：关系的强度、互惠与**社会支持可获得性**。
- **口径**（复用 T9 §1.2）：
  - `strong_ties_i`（`≥ ε_strong` 的边数）；
  - `reciprocity_i`（互惠强边比例）；
  - `mean_affinity_i / mean_trust_i`（关系维均值）；
  - `support_received_i`（`near_death` 时 distress 私聊被响应的次数，`MSG_DM` + `ACTIVITY` 协同判定，D）；
  - `isolation_flag_i`（孤立节点，`degree=0`）。
- **来源**：`RELATION_CHANGE / RELATION_ENCOUNTER / MSG_*`。
- **归属**：D。

### 1.7 W6 · 技能 / 成长（D，依赖 T7 技能事件）

- **含义**：技能提升、学习与目标达成。
- **口径**：
  - `skill_level{dim}` 与 `skill_gain_rate`（由**技能事件**折叠；T8 现有事件表**未含** `SKILL_*`，需 T7/T8 补，见【冲突】WB-C1）；
  - `learning_activity_rate`（`school/library` 活动占比）；
  - `goal_achievement_rate = Σ GOAL_ACHIEVED / Σ GOAL_SET`；
  - `goal_progress_trend`（`GOAL_PROGRESS` 一阶差分）。
- **来源**：技能事件（待补）、`GOAL_*`、`ACTIVITY_*`。
- **归属**：D（**技能口径待 T7/T8 补**）。

### 1.8 W7 · 自主与意义感（D 代理 + F）

- **含义**：自主选择、目标意义、生活节奏掌控。
- **D 代理**（结构性自主，确定性）：
  - `autonomy_ratio`（自主计划活动 / 全部活动，来自 `SCHEDULE_PLANNED` 与 `ACTIVITY_*` 的 `cause`）；
  - `activity_diversity`（窗口内 `activity_type` 的归一化熵）；
  - `leisure_work_ratio`（休闲活动 / 劳动活动）；
  - `self_goal_rate`（Agent 自设目标 / 全部 `GOAL_SET`）。
- **F 口径**：读 `LLM_JUDGMENT.dimension="meaning"`（意义感/目标感的定性判定，冻结）→ `metrics.wellbeing_soft.meaning_score`，标 `frozen_llm`。
- **归属**：D 代理 + F。

---

## 2. 激励层 vs 观测层（输入 / 输出分离）

### 2.1 分层定义（【已定】）

```
激励层（输入，机制，影响行为）        观测层（输出，衡量结果）
─────────────────────────           ─────────────────────────
货币 / UBI / 代谢 / 税收              W1 经济状况
价格 / 工资 / 门票 / 利率             W2 社会地位
赊账 / 借贷 / 复活费                  W3 主观满足感
规范阈值 / 活动概率参数               W4 健康
（决定 Agent「被激励去做什么」）       W5 关系质量
                                      W6 技能/成长
                                      W7 自主与意义感
（决定「最终过得怎么样」）
```

- **方向**：激励层 → 行为 → 观测层；观测层**不得反哺**为优化目标（本轮实验**不训练、不优化单一 reward**）。
- **反例警示（Agentopia）**：其 life reward 用 z-score 加权（社会 0.4 / 经济 0.2，权重假设强），并**用 reward 反训模型**；结果显示训练后**经济 +2.5% 但物质满足 −14.8%、个人活动 −19.8%**（town-life-brief §1.2、§1.4）。这正是「把福祉压成单一分数去优化」的风险实证——**本层明确不重蹈**。

### 2.2 为何不合成单一分数（【已定】）

1. **概念上**：金钱/地位/健康/关系/意义**不可通约**，加权合成会掩盖维度间**背离**（§4），而背离恰恰是最有信息量的现象。
2. **方法上**：任何权重都是**价值假设**；合成后无法区分「真的更幸福」与「权重凑的」。
3. **实验定位**：v1.1 是**观察实验**（不问「怎样最幸福」，只问「自发产生什么」），无需 scalar。

### 2.3 呈现方式（【已定】）

- **一等产物 = 多维向量** `WBV_i = [W1_i, ..., W7_i]`（分项 + 向量），随快照输出。
- **分项**均进 `metrics.wellbeing.*`，每项标 `basis`（D/F）。
- **（可选）汇总指数 `WBI`**：若确需一个便于阅读的标量，**必须**：
  1. **显式声明权重假设**（如等权 / Agentopia 式 0.4/0.4/0.2）；
  2. **附敏感性分析**：至少给出 3 组不同权重下的 `WBI` 排序与相关系数；
  3. **显式标注**「**仅供呈现，不用于优化、不用于验收判定**」；
  4. F 类维度进 `WBI` 时标 `contains_frozen_llm=true`。
- **禁止**：把 `WBI` 写回世界、作为激励、或作为 Agent 的目标函数。

---

## 3. 判定归属与方案甲约束（逐维）

### 3.1 归属表（【已定】）

| 维度 | D（纯确定性） | F（含 LLM 冻结判定） | 计算约束 |
|---|---|---|---|
| W1 经济 | 全部 | 无 | D；`llm_calls==0` |
| W2 社会地位 | `pagerank_rank/incoming_strong_ties/cited_count/governance_influence` | `respect_mean/affection_mean/liked_by_count` | D 与 F **分栏** |
| W3 主观满足 | `need_level{dim}`（客观代理） | `subj_emotion/material/social/esteem` | **主为 F**，仅描述 |
| W4 健康 | 全部 | 无 | D |
| W5 关系质量 | 全部 | 无 | D |
| W6 技能成长 | 全部（待技能事件） | 无 | D |
| W7 自主意义 | `autonomy_ratio/activity_diversity/leisure_work_ratio/self_goal_rate` | `meaning_score` | D 代理 + F 分栏 |

### 3.2 方案甲约束（【已定】）

- **F 类读取方式**：读 `LLM_JUDGMENT.frozen=true`（T12 §5.5），**只读回、不重问**；计算过程 `llm_calls == 0`；每条 F 指标标 `"source":"frozen_llm"` 与 `"frozen_ref":[judgment_id...]`。
- **命名空间隔离**：F 类入 `metrics.wellbeing_soft`（**不混入** `metrics.wellbeing`）。
- **门禁**：`metrics.wellbeing` 的 `llm_judged_metric_count == 0`；F 类**不进**沙盒门禁与验收判定（T9-D3 定论）。
- **审计四要素**：F 判定必须可追溯 `decision + model + context_digest + frozen`（T12 §5.5）。
- **硬内核隔离**：W1 是 K 级经济事件的**派生展示**，**绝不接受 LLM 判定为输入**（P4）。

---

## 4. 与金钱解耦（为何单一经济指标不够 + 背离现象判据）

### 4.1 为何不能用单一经济指标代表生活质量（【已定】）

1. **手段 vs 目的**：金钱是换取需求的**手段**；W3/W5/W7 是**目的**本身。
2. **实证背离**：Agentopia 自身案例——「**社会奖励下降但主观幸福上升**」、训练后**经济 +2.5% 而物质满足 −14.8%、个人活动 −19.8%**（town-life-brief §1.2、§1.4）。若只看经济，会得出「更幸福」的错误结论。
3. **循环论证**：经济是**激励层**（§2），用它代表幸福感等于「用输入衡量输出」。
4. **维度不可通约**：健康、意义、关系无法折算成货币。

### 4.2 背离现象的可观测判据（【已定】规则骨架，阈值【待标定】）

> 全部用确定性口径；涉及 W3/W7 的 F 子维时，**另出 D 代理版**（§3.1），使背离检测在纯 D 口径下也可用。

| 现象 | 判据（确定性） | 归属 |
|---|---|---|
| **富而不乐** | `wealth_percentile_i ≥ 0.75` **且**（D：`mean need_level` 低于中位 **或** `health_deprivation_rate` 高）；F 版用 `subj_*` 均值 < 基线 | D（+F 版） |
| **地位降而幸福升** | `pagerank_rank` 名次下降 `≥ Δrank` **且**（D：`strong_ties`/`leisure_work_ratio`/`self_goal_rate` 上升；F：`subj_social`/`meaning_score` 上升） | D 代理 + F |
| **经济差而关系/意义强** | `wealth_percentile_i ≤ 0.25` **且** `strong_ties`/`activity_diversity` 高于中位 | D |
| **成长停滞** | `skill_gain_rate ≈ 0` **且** `goal_achievement_rate` 下降，同时 `financial_security_rounds` 高（有钱但无成长） | D |
| **背离计数** | `divergence_count(t) = |{i: sign(Δecon_i) ≠ sign(Δwellbeing_D_i)}| / alive_count`，其中 `Δwellbeing_D` 为 W4/W5/W6/W7-proxy 的归一化合成**仅用于背离检测**（非优化） | D |

- **阈值**：`Δrank / θ` 等【待标定】（T10）。`divergence_count` 是**核心可执行产物**：它把「金钱 ≠ 幸福」变成**可从日志重算的数字**。

---

## 5. 可复现与审计（【已定】）

- **D 类**：全部由日志确定性重算（整数优先、规范 JSON、全序 tie-break、定点输出），同 `(log,T,params)` 两次报告**逐位一致**。
- **F 类**：只读冻结判定；报告附 `frozen_ref` 与 `model/version/context_digest`，可审计「该结论依赖哪个模型版本的哪次判定」。
- **复现单位 = 日志**（T12 §5.4 / T9 §0.4）：首跑含 LLM 判定，跨跑不保证逐位一致；`replay(log)` 与 `metrics()` 对同日志逐位一致即可。
- **分栏证书**：报告头声明 `llm_judged_metric_count`（`metrics.wellbeing` 中 basis==F 条目，**必须 0**）、`frozen_llm_metric_count`（`metrics.wellbeing_soft` 条目，仅报告）、`narrative_reads_in_decision == 0`、`llm_calls == 0`。

---

## 6. 与 T9 观测框架的关系与命名空间映射（【已定】）

### 6.1 新增命名空间

```
metrics: {
  econ, lifecycle,          # v1（冻结，K 级）
  life, emergence,          # T8/T9（D 级）
  emergence_soft,           # T9（F 级，仅敏感性）
  wellbeing:      { ... },  # 本层（D 级判定）
  wellbeing_soft: { ... }   # 本层（F 级，仅描述/敏感性）
}
```

### 6.2 与既有指标的映射（复用，不重复造轮子）

| well-being 维度 | 复用来源 | 说明 |
|---|---|---|
| W1 经济 | `metrics.econ`（v1） | 派生展示，口径不变 |
| W2 社会地位(D) | `metrics.emergence`（`G_rel`：PageRank/degree/reciprocity） | 同 T9 §1.2 |
| W2 社会地位(F) | `metrics.emergence_soft`（互评） | F 级 |
| W3 主观满足 | `metrics.life`（need 代理）+ `emergence_soft`（satisfaction） | D 代理 + F |
| W4 健康 | `metrics.life`（need：health/energy） | T8 §4.2 |
| W5 关系质量 | `metrics.life/emergence`（`G_rel`） | 同 T9 §1.2 |
| W6 技能成长 | `metrics.life`（activity/goal）+ 新增 skill | 待技能事件 |
| W7 自主意义 | `metrics.life`（schedule/activity）+ `emergence_soft`（meaning） | D 代理 + F |

- **一致性**：本层**不重定义** T8/T9 任何指标口径；仅做**组合、派生与命名**。
- **背离检测**（§4.2）作为 T9 §4.10「观测方法论」在福祉维度的特化实例。

---

## 7. 与 T10 沙盒的接口（观测判据 vs 描述性统计）

### 7.1 建议拆分（【已定】建议，交 T10 确认）

| 类别 | 内容 | 处置 |
|---|---|---|
| **进「观测判据」（D 类，可做门禁）** | ① `WBV` 可被**稳定重算**（两次 `wellbeing_report` 字节相等）；② 至少 **1 类背离现象**（§4.2）可被 **D 类**指标检出（`divergence_count>0` 或某背离判据成立）；③ `metrics.wellbeing` 的 `llm_judged_metric_count==0` | 与 T9 观测判据同族 |
| **仅描述性统计（F 类 + 部分 D）** | W3 主观满足（F）、W2 respect/affection（F）、W7 meaning（F）；以及各维分项分布 | 报告，**不作门禁** |
| **护栏（K 类）** | W1 所依赖的 v1 经济指标 | 沿用 v1/T10 护栏，不重复 |

### 7.2 对 T10 的交接

- 本层提供沙盒可用的：`metrics.wellbeing.*`（D）与 `metrics.wellbeing_soft.*`（F）的**计算定义**、背离判据（§4.2）、以及「哪些进判据」的建议（§7.1）。
- **依赖 T7 的枚举**（need 维、activity_type、skill、GOAL kind）——T7 落盘后回填，见 §8。

---

## 8. 已定 / 待讨论 / 冲突项

**已定（v1.1 基线，下游可引用）**
- 定位与五条原则 P1–P5（§0.2）；维度集 W1–W7 与逐维口径/归属（§1）。
- 激励 / 观测分离、禁单一分数优化、`WBV` 向量 + 可选 `WBI`（显式权重 + 敏感性 + 非优化声明）（§2）。
- 判定归属表与方案甲约束（D/F 分栏、`frozen_llm`、`llm_calls==0`、硬内核不接 LLM）（§3）。
- 与金钱解耦的论证与**背离现象可观测判据**（含 `divergence_count`）（§4）。
- 可复现与审计四要素（§5）；命名空间 `metrics.wellbeing` / `wellbeing_soft` 与映射（§6）；与 T10 接口建议（§7）。
- **WB-C2（【已定】，Leader 裁决「采纳」）**：W3 主观满足 / W2 互评 / W7 meaning 等 **F 类指标不进沙盒门禁**（门禁只管护栏与确定性观测判据），但**必须**：
  1. 在**长窗实验**中作为**一等观测结果重点报告**（不是附注）；
  2. 在 v1.1 方案开放问题清单中**单列一条**（主题：「主观满足感等 F 类指标如何进入结论、其 LLM 依赖如何被读者正确理解」）；
  3. 报告中**同时给出** `frozen_llm` 来源标注与**敏感性分析**，避免读者误当作确定性结论。

**待讨论（开放问题）**
- `need.dim[]`（含 health/energy）、`activity_type[]`、**技能事件 schema**、`GOAL kind` 枚举——依赖 T7（`D7-3`）。
- F 类判定的 question 模板与打分口径（W3 satisfaction 四子维、W2 respect/affection、W7 meaning）——依赖 T7/软判定层。
- 阈值：`θ_dep(health)`、`ε_strong`、`Δrank/θ`、`divergence` 归一化与阈值（T10 标定）。
- 是否提供 `WBI` 及权重假设（建议：**默认不给 scalar**，仅在用户要求时给并附敏感性）。

**冲突 / 待对齐项**
- **WB-C1**（中）**技能/成长（W6）依赖 `SKILL_*` 事件，而 T8 §1.2 事件表未含**。请 T7/T8 补技能事件（如 `SKILL_GAINED{agent_id, dim, before, after, cause, day}`）或明确用 `ACTIVITY_COMPLETED(outcome)` + `GOAL_*` 代理。
- **WB-C2**（【已定】，Leader 已裁决「采纳」→ 转入 §8「已定」）：W3/W7 的 F 子维不进沙盒门禁，但须在长窗实验重点报告、单列开放问题、附 `frozen_llm` 标注与敏感性分析。
- **WB-C3**（低）`metrics.wellbeing_soft` 命名空间需 T8 §4.0 登记（与 T9-C4 一并处理）。

---

*（本文件为 v1.1 幸福感/生活质量观测指标体系草案；核心立场：**把「金钱不能代表人的全部」变成可从日志确定性重算的多维向量 + 背离判据**；激励层与观测层分离，禁止单一分数优化；F 类冻结 LLM 判定仅作描述/敏感性。待讨论项交 Leader 汇总与 T7/T10 标定。）*
