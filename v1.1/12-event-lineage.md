# 12 · 事件谱系 → 触发条件 → 判定方式 映射 + 活动模板库规格 v1.1

> 作者：仿真引擎与统计架构师（sim-engine-stats-architect）
> 状态：v1.1 设计草案（供 Leader 汇总；显式区分【已定】与【待讨论】）
> 对齐基准（权威来源，本文不另立口径）：
> - `v1.1/00-architecture.md`（三层架构、单小镇世界设定「青溪镇」、周时间结构、层间接口 IF-1~IF-7、确定性边界、§2 场所/角色、§3 时段）
> - `v1.1/06-life-layer.md`（**枚举权威**：activity_type 8 类、need 6 维、relation dim/值域、WEEK_PHASES、事件族映射、不变量 L1–L8）
> - `v1.1/08-engine-stats-extension.md`（**事件 schema 权威**：Phase 3.5 L1–L7、事件表、指标命名空间）
> - `v1.1/07-emergence-observation.md`（观测指标 D/F/K 分级）、`v1.1/13-wellbeing-metrics.md`（福祉指标）
> - `research/town-life-brief.md`、`v1.1/11-agentopia-reuse-assessment.md`（20 类事件来源与 Agentopia 参照）

**本文目标**：把 20 类事件从「希望它发生」变成「**有机制使它可能发生、且能确定性判定它是否真的发生**」。

---

## 0. 三条判定归属与确定性边界（【已定】，复用 00 §5 / 08 §1.2）

> 用户「底座拆分」约束：**硬内核确定性 / 软判定 LLM 但结果冻结 / 叙事 LLM**；**随机性由种子化 RNG 决定，LLM 不掷骰子**；**金额/死亡/结算绝不由 LLM 判定**。

| 判定归属 | 标记 | 执行者 | 允许范围 | 事件落点 |
|---|---|---|---|---|
| **硬内核确定性** | **D** | 确定性代码 | 资格/数值/胜负/排名/金额/死亡/结算/阈值判定 | 直接产生确定性事件（`ACTIVITY_*`、`TRANSFER`、`MARKET_TRADE`、`RELATION_CHANGE`、`NEED_UPDATE`…） |
| **软判定 LLM 冻结** | **F** | LLM（定性） | 仅定性社会判断（是否结为密友/师徒、创意优劣评语）；**结果写日志后冻结，不重问** | `LLM_JUDGMENT{decision, model, context_digest, frozen=true}`（08 §1.2 I） |
| **纯叙事** | **N** | LLM | 把已定事实叙述成情节/对话；**绝不影响状态** | `NARRATIVE{affects_state=false}`、`MSG_*` 正文 |
| **随机分支** | **R** | 种子化 RNG | 一切分支/结果分布；`rng_branch` 先定分支，LLM 再填充 | `redraw(stream_id, round, seq)`（08 §1.4 层级 RNG） |

**关键纪律**：任何「对抗/评分/竞争」类事件，**胜负与名次必须由 D 类确定性函数 + R 类 RNG 决定**；LLM 至多给 F 类定性评语（**不进排名、不进门禁**，入 `metrics.emergence_soft`）。

---

## 1. 事件谱系总表（20 类 + 补充）

> 列含义：**触发条件**（前置状态/关系/资源/场所/时段）｜**协议**（单方 S / 双方 Dy / 群体 G，及协商环节）｜**判定**（D/F/N/R 归属）｜**日志事件**（08 事件表类型，`+` 表示本文建议补登）｜**可观测指标**（供 T9）。

### E1 Mentorship（师徒 / 教导）
- **触发**：同 `skill_id` 且师父 `level − 徒弟 level ≥ 2`；`familiarity ≥ ε`(=20)；地点 `school/workshop/library`；时段 `morning/afternoon`；徒弟有 `mastery` 目标或 `learn` 计划。
- **协议**：**Dy**（发起 `mentor_teach` 要约 → 应约 / 婉拒 Polite Rejection / 成约）；可多期（周）。
- **判定**：**D**（资格/时长/产出/技能提升）+ **F**（是否结为「正式师徒」关系 → `LLM_JUDGMENT{dimension=mentor_relation}`，envelope 由 D+R 预置）+ **N**（教导叙事）。
- **日志事件**：`ACTIVITY_STARTED/COMPLETED(template=mentorship)`、`SKILL_LEVEL_UP`、`RELATION_CHANGE(respect/trust↑)`、`LLM_JUDGMENT`、`GOAL_PROGRESS`、`MEMORY_WRITE`。
- **指标**：师徒对及数量、教学网络边、respect PageRank、技能提升率。

### E2 Gift-giving（赠礼）
- **触发**：`affinity ≥ ε_strong`(=50)；有可赠资源或货币（`cash > 保留额`）；地点不限（`plaza/cafe/residence` 常用）；时段 `evening` 偏好；可选节日/生日因子。
- **协议**：**S→Dy**（一方发起赠予 → 接受 / 婉拒）。
- **判定**：**D**（`TRANSFER` 金额与资源转移、关系数值更新）+ **N**（礼物寓意）。
- **日志事件**：`TRANSFER(reason=gift)`、`RELATION_CHANGE(affinity/trust↑)`、`MEMORY_WRITE`、`NARRATIVE`。
- **指标**：赠礼金额分布、赠礼网络边、互惠率、affinity 提升率。

### E3 Combat Training（战斗 / 体能训练）※小镇适配为「体能 / 竞技训练」
- **触发**：技能 `athletics/combat`；`need.energy ≥ θ_train`；地点 `park`（对练）；时段 `morning/afternoon`；可选对手（对方同意）。
- **协议**：**S**（独自训练）或 **Dy**（对练：挑战 → 应战 / 拒绝）。
- **判定**：**D**（训练成长；对练胜负由 §3 确定性对抗结算）+ **R**（胜负随机项）+ **N**（场面叙述）。
- **日志事件**：`ACTIVITY_STARTED/COMPLETED(template=combat_training)`、`NEED_UPDATE(energy↓)`、`SKILL_LEVEL_UP`、`RELATION_CHANGE(affinity/respect)`、可选 `CONFLICT_RESOLVED+`。
- **指标**：训练参与度、胜负分布、技能提升、体能-产出关系。

### E4 Creative Collab（创意协作）
- **触发**：`participants ≥ 2`；参与者有 `art/craft` 技能；地点 `hall/workshop/cafe`；goal=`creative`。
- **协议**：**G**（发起 → 应约 / 还价 Counter-propose 分工 → 成约）。
- **判定**：**D**（产出 `quality = f(Σ 参与者 skill/effort)`）+ **F**（创意评语 → `LLM_JUDGMENT{dimension=creative_quality}`，**仅 F 类，不进质量数值**）+ **N**。
- **日志事件**：`ACTIVITY_STARTED/COMPLETED(template=creative_collab)`、`SKILL_OUTPUT`、`RELATION_CHANGE`、`LLM_JUDGMENT`、`TAG_EMITTED`。
- **指标**：协作网络边、产出数、质量分布、创意标签频次。

### E5 Saving Money（储蓄）
- **触发**：`cash > 保留额`；`saving_propensity`（M1 派生）；地点 `bank`；时段 `morning/afternoon`。
- **协议**：**S**（存款 / 取款意图）。
- **判定**：**D**（纯硬内核，与 v1 银行机制一致）。
- **日志事件**：`DEPOSIT`/`WITHDRAW`（**已登记** 08 §1.2 L，phase=4.2）、`INTEREST_CHARGED`/`INTEREST_PAID`（若有息）。
- **指标**：储蓄率、存款分布、货币总量 M 与流速。

### E6 Whispered Comm.（私语 / 秘密沟通）
- **触发**：话题敏感 / `affinity ≥ ε`；通道 `MSG_DM`；地点 `residence/cafe` 偏好；时段 `night/evening`。
- **协议**：**Dy**（1:1 私聊；受 v1 通道配额与状态分档约束）。
- **判定**：**D**（投递、配额、可见性）+ **F**（若「是否可信任以披露秘密」需判断 → `LLM_JUDGMENT{dimension=secret_trust}`）+ **N**（正文）。
- **日志事件**：`MSG_DM(visibility=private)`、`RELATION_CHANGE(trust)`、`MEMORY_WRITE`。
- **指标**：私聊网络密度、信任变化、秘密传播链（T9 B 类）。

### E7 Emotion Burnout（情绪耗竭）※依赖临界资源
- **触发**：**内在需求驱动** —— `need.energy/leisure` 持续 `< θ_dep`(=20) 超过 `W_burn` 个时段，叠加过劳（work 占比高）/负面事件；**无协商**（非自愿）。
- **协议**：**S / 系统**（规则持续累积 → 阈值触发）。
- **判定**：**D**（耗竭函数 `burnout = f(持续低 need, 负荷, 负事件)`，超阈 → 状态/产出确定性下降）+ **N**（描述）。
- **日志事件**：`NEED_UPDATE`、`STATE_CHANGE(→exhausted)`（**已裁定**：不新增 `WELLBEING_ALERT`，以 `STATE_CHANGE` 为唯一事实源）、`GOAL_PROGRESS(受阻)`。
- **指标**：耗竭发生率/时长、energy/leisure 分布、产量下降率、WBV 健康维度。
- **依赖生活层输入**：`need.dim` + `decay[]` + 活动负荷 + 负事件。

### E8 Diff. Scoring（差异打分）※需确定性结算
- **触发**：评比/竞赛/评估场景（`hall/plaza/school`）；`participants ≥ 2`；有可评属性。
- **协议**：**G / Dy**（提交 → 评分 → 公布）。
- **判定**：**D**（评分与排名**全确定性**，见 §3.1；**LLM 绝不当裁判**）+ **F**（定性评语，F 类，不进排名）+ **N**。
- **日志事件**：`SCORE_POSTED`、`RANKING_EMITTED`（**已登记** 08 §1.2 K）、`LLM_JUDGMENT{dimension=qualitative_review}`、`RELATION_CHANGE`、`TAG_EMITTED`。
- **指标**：评分离散度、排名、评分-客观属性相关性（校验「评分是否被客观属性解释」）。

### E9 Scarcity Buy（稀缺购买）
- **触发**：某商品库存低（稀缺）+ 需求高；地点 `market`；时段 `afternoon`（撮合高峰）。
- **协议**：**G**（多方竞价购买；订单簿撮合）。
- **判定**：**D**（v1 CDA 订单簿撮合，纯硬内核）+ **N**。
- **日志事件**：`MARKET_TRADE`、`ORDER_PLACE/CANCEL`（v1 `INTENT.ECON.*`）、价格变化（市场态）。
- **指标**：成交量、价格波动、稀缺指数、成交额分布（T8 §5.7）。

### E10 Skill Practice（技能练习）
- **触发**：有 `mastery` 目标或技能成长意图；place `affordances` 匹配（如 `learn→school/library`）；needs 允许（非耗竭）。
- **协议**：**S**。
- **判定**：**D**（练习 → 成长确定性函数）。
- **日志事件**：`SKILL_PRACTICE`、`SKILL_LEVEL_UP`（超阈）、`NEED_UPDATE`。
- **指标**：练习频次、成长曲线、技能分布、技能提升率。

### E11 Polite Rejection（礼貌拒绝）
- **触发**：收到要约/请求；满足拒绝条件（资源不足 / `affinity < ε` / 优先级冲突 / 非营业时段）。
- **协议**：**协商环节**（响应方；可含理由，可触发 Counter-propose）。
- **判定**：**D**（拒绝决策可由 T0 规则：资源/关系/优先级阈值）+ **F**（若拒绝理由含社会判断）+ **N**（措辞）。
- **日志事件**：`OFFER_REJECTED`（社交婉拒，08 §1.2 K）或 `INTENT_REJECTED`（规则拒绝，08 §1.2 H）、`MSG_*`、`RELATION_CHANGE(轻微↓或维持)`。
- **指标**：拒绝率、拒绝后关系变化、协商成功率。

### E12 Passion vs Salary（热情 vs 薪资）※依赖稀缺 & 内在目标
- **触发**：Agent 面临「高薪岗位 vs 符合价值观/兴趣岗位」二选一（`ROLE_CHANGE` 候选）；薪资差显著；`goal_tendencies` 含 `achievement/self_direction`。
- **协议**：**S**（个人抉择；可选咨询他人 → Dy）。
- **判定**：**D**（**选择由确定性效用函数 + RNG 分支落定**：`utility = α·salary + β·value_fit + γ·need_fit`，权重由 M1 派生标量定）+ **F**（软性偏好 `LLM_JUDGMENT`，仅记录） + **N**。
- **日志事件**：`ROLE_CHANGE`、`GOAL_SET/ABANDON`、`LLM_JUDGMENT{dimension=job_preference}`。
- **指标**：职业转换矩阵、薪资-满意度背离（WBV 经济 vs 意义）、转换率。
- **依赖生活层输入**：`goal_tendencies/values` + 经济薪资 + `need` 状态。

### E13 Group Proposal（群体提案）
- **触发**：议题需 ≥ K 人（`K=5` 默认）；地点 `town_hall/plaza`；时段 `morning/afternoon/evening`。
- **协议**：**G**（发起 → 附议 → 还价 → 表决）。
- **判定**：**D**（**通过阈值确定性**：支持者 ≥ `threshold`，非 LLM）+ **N**（提案文本）。
- **日志事件**：`NORM_PROPOSED/ADOPTED`（**复用**，已裁定：群组提案走 `OFFER_*` 状态机 + 规范流程，不新增 `PROPOSAL/VOTE`）、`MSG_PUBLIC`。
- **指标**：提案数与通过率、表决网络、规范形成（T9 D 类）。

### E14 Academic Collab（学术协作）
- **触发**：`school/library`；`participants ≥ 2`；goal=`mastery/research`；技能 `learn/research`。
- **协议**：**G**。
- **判定**：**D**（产出/成长）+ **F**（学术评语，F 类）+ **N**。
- **日志事件**：`ACTIVITY_STARTED/COMPLETED(template=academic_collab)`、`SKILL_LEVEL_UP`、`SKILL_OUTPUT`、`RELATION_CHANGE`。
- **指标**：协作网络、学术产出、知识传播链。

### E15 Counter-propose（还价 / 反提案）
- **触发**：收到要约且不满足（价格/条件）；协商进行中且轮次 `< N_round`（默认 3）。
- **协议**：**Dy/G 协商状态机**（`OFFER_CREATED → {OFFER_ACCEPTED | OFFER_REJECTED | OFFER_COUNTERED}`）。
- **判定**：**D**（还价接受阈由确定性效用函数；轮次上限硬约束）+ **N**（措辞）。
- **日志事件**：`OFFER_COUNTERED`、`OFFER_ACCEPTED`/`OFFER_REJECTED`（均 08 §1.2 K）、成交后走 `TRANSFER/MARKET_TRADE`。
- **指标**：协商轮数分布、成交率、让价幅度。

### E16 Select Location（选择地点）
- **触发**：活动/会面前需确定 `place`；多候选。
- **协议**：**S** 或 **Dy 共识**。
- **判定**：**D**（合法性/容量/营业时段/`travel_ticks` 择优：确定性 argmax + 全序 tie-break）。
- **日志事件**：`PLACE_MOVE`、`PLACE_ARRIVED`（**已裁定**：`LOCATION_SELECTED` 并入 `PLACE_MOVE`，到达即隐含已选，不新增）。
- **指标**：场所热度分布、移动距离、场所共现（偶遇载体）。

### E17 Power Conflict（权力冲突）※需确定性结算
- **触发**：争夺稀缺资源/决策权；`town_hall/market/plaza`；双方目标冲突；关系竞争（低 affinity / 高 respect 竞争）或资源紧张。
- **协议**：**Dy/G**（挑战 → 应战 → 可选调停 → 解决）。
- **判定**：**D**（**对抗胜负全确定性**，见 §3.2；**LLM 绝不当裁判**）+ **R**（随机项）+ **N**（情节）。
- **日志事件**：`CONFLICT_STARTED+/CONFLICT_RESOLVED+`、`RELATION_CHANGE(↓)`、资源再分配走 `TRANSFER/MARKET_TRADE`、`TAG_EMITTED`。
- **指标**：冲突数、胜率、资源再分配量、关系破裂率、地位变化（respect PageRank）。

### E18 Rel. Acceptance（关系接纳）
- **触发**：交互累积后关系达阈值（`familiarity ≥ ε` 且 `affinity ≥ 某阈`）；从弱关系向「朋友」质变候选。
- **协议**：**S 或 Dy**（一方接纳 / 互认）。
- **判定**：**F**（「是否接纳为朋友/伙伴」→ `LLM_JUDGMENT{dimension=friendship_label}`，envelope 由 D+R 预置，LLM 在 `envelope.options` 内定性）+ **D**（标签→数值 delta 由 D-12 确定性映射，06 §6.3）。
- **日志事件**：`LLM_JUDGMENT`、`RELATION_CHANGE`、`TAG_EMITTED`。
- **指标**：朋友边数、互惠率、关系网络演化（T9 A 类）。

### E19 Ice-breaking（破冰）
- **触发**：`familiarity < ε` 且同处 / 新遇；`social_initiative`（M1 派生）高；地点 `plaza/cafe/community_center`。
- **协议**：**S→Dy**（发起 → 回应：接受 / 婉拒）。
- **判定**：**D**（发起资格/配额；`RELATION_ENCOUNTER`）+ **F**（首因印象，可选，F 类）+ **N**（寒暄）。
- **日志事件**：`MSG_DM/MSG_PUBLIC`、`RELATION_ENCOUNTER`、`RELATION_CHANGE(familiarity↑)`、`LLM_JUDGMENT(optional first_impression)`。
- **指标**：破冰成功率、新边形成率、familiarity 增长、tie_formation_rate。

### E20 Rel. Maintenance（关系维护）
- **触发**：`last_interaction_round` 距今 > `D_maint`（默认 1 周）；关系数值存在自然衰减。
- **协议**：**S / Dy**（主动联系：CHAT / gift / share_activity）。
- **判定**：**D**（衰减函数 + 维护动作回复数值，06 §6.3）。
- **日志事件**：`RELATION_CHANGE`（衰减负向 / 维护正向）、`MSG_*`、`MEMORY_WRITE`。
- **指标**：关系衰减率、维护频率、强关系存续时长、tie_decay_rate（T9 A 类）。

---

## 2. 补充事件类型清单（本文识别，供 08 补登记）

> 规则（Leader 指示）：**先补登记、冲突记入 T14 冲突清单**。以下为上表出现的补充事件。**2026-10-09 Leader 裁决（含 T17 核对）**：`OFFER_*`（C1）、`SCORE_POSTED/RANKING_EMITTED`、`CONFLICT_*`（C2）**已登记 08 §1.2 K**；`DEPOSIT/WITHDRAW`+`INTEREST_PAID` **已登记 08 §1.2 L**；`GOAL_ABANDON` **已登记 08 §1.2 C**；`PROPOSAL/VOTE` **复用 `NORM_*`**、`LOCATION_SELECTED` **并入 `PLACE_MOVE`**、`WELLBEING_ALERT` **不新增**（STATE_CHANGE 承载）。下列"处理"列已同步裁决结果。

| 建议事件 | 建议 phase | 关键 payload | 归属/说明 | 处理建议 |
|---|---|---|---|---|
| `OFFER_CREATED` / `OFFER_COUNTERED` | 2/3 | `offer_id, from, to[], kind, terms, round_no` | 协商状态机 | **已登记** 08 §1.2 K |
| `OFFER_ACCEPTED` / `OFFER_REJECTED` / `OFFER_EXPIRED` | 2/3 | `offer_id, by/new_terms/round_no` | 协商结果 | **已登记** 08 §1.2 K（婉拒≠规则拒绝） |
| `SCORE_POSTED` / `RANKING_EMITTED` | 2/3.5 | `contest_id, subject/ranking, score, rank` | Diff. Scoring（D） | **已登记** 08 §1.2 K |
| `CONFLICT_STARTED` / `CONFLICT_RESOLVED` | 2/3.5 | `conflict_id, parties[], stakes, winner, rule_ref` | Power Conflict（D） | **已登记** 08 §1.2 K |
| `PROPOSAL` / `VOTE` | — | — | Group Proposal | **不新增**：复用 `NORM_PROPOSED/ADOPTED` + `OFFER_*` 流程 |
| `LOCATION_SELECTED` | — | — | Select Location | **不新增**：并入 `PLACE_MOVE` |
| `DEPOSIT` / `WITHDRAW` | 4.2 | `agent_id, amount, cash_after, deposit_after` | Saving Money（D） | **已登记** 08 §1.2 L |
| `INTEREST_PAID` | 4.2 | `bank, agent_id, amount, deposit_after` | 存款息（bank→agent） | **已登记** 08 §1.2 L |
| `GOAL_ABANDON` | 3.5 | `goal_id, agent_id, reason, progress_at_abandon` | 目标放弃 | **已登记** 08 §1.2 C |
| `WELLBEING_ALERT` | — | — | Emotion Burnout | **不新增**：以 `STATE_CHANGE(exhausted)` 承载 |
| `SKILL_PRACTICE/LEVEL_UP/OUTPUT` | 3.5 | 见 08 §1.2 J | Skill Practice | **已登记（WB-C1）**，直接引用 |

---

## 3. 确定性结算规则（对抗 / 评分类，**LLM 绝不当裁判**）

> 应要求 2：`Diff. Scoring`、`Power Conflict` 等需要评价/对抗结果的事件，**必须**给出确定性结算；LLM 只提供**定性描述**或**软性偏好（冻结）**。

### 3.1 Diff. Scoring 的确定性评分与排名

```
输入（全部来自日志可重放）:
  subjects = [i1..in]                 # 被评对象（Agent 或 产出物）
  attr_k(i) = 客观属性                  # 由确定性事件折叠，如:
              skill_level(skill_id), effort(练习/工作时长), resource_spent(mu),
              prior_record(历史得分), quality(§E4 产出质量)
  w_k = 固定权重常数（config，整数或万分比），Σ w_k 归一
  stream_id = "contest.<contest_id>"

评分（确定性）:
  norm(attr_k) = (attr_k − min_j attr_k(j)) / (max_j − min_j)   # 定点；分母0 -> 0
  raw(i)  = Σ_k w_k · norm(attr_k(i))                          # 定点整数
  noise(i)= rng_draw("contest", round, seq_i) 归一化 → 加性随机项（R 类）
  score(i)= raw(i) + noise(i)

排名（确定性）:
  rank = sort desc by (score, then agent_id asc)   # 全序 tie-break，杜绝并列歧义
```

- **LLM 的角色**：仅可产
  (a) `NARRATIVE`（对已定结果的评语叙述），或
  (b) `LLM_JUDGMENT{dimension=qualitative_review}`（**F 类**，写入 `metrics.emergence_soft`，**绝不参与 score/rank**）。
- **反作弊**：`raw` 权重与属性来源公开可审；统计可校验「排名是否被客观属性解释」（§E8 指标），暴露「LLM 偏好是否偷偷影响结果」——因为结果里根本没有 LLM 输入。

### 3.2 Power Conflict 的确定性对抗结算

```
power(i) = α·wealth_norm(i)            # 净财富（v1 net_worth）
         + β·ally_strength(i)          # 强关系入边加权和（Σ_{j: ε_strong} w_affinity(j→i)）
         + γ·respect_pagerank(i)       # G_rel(respect) 的 PageRank（D-12 确定性）
         + δ·resource_control(i)       # 掌控的稀缺资源量
         + ε·rng_term(i)               # R 类随机项（rng_branch 先定）

winner = argmax_i power(i)   # 确定性；并列按 agent_id asc
后果（确定性）:
  - 争夺资源重分配：TRANSFER/MARKET_TRADE（v1 原子语义）
  - 关系：败者→胜者 affinity↓、respect 变动（D-12 夹取）
  - 可选：控制权/职位变更 → ROLE_CHANGE
```

- **LLM 的角色**：仅 `NARRATIVE`（冲突情节）或 F 类定性描述；**胜负、资源、关系数值全部 D/R**。
- **可复现**：`power` 全部输入来自日志；`rng_term` 由 `(seed, "conflict", round, seq)` 确定 → 同日志逐位一致。

### 3.3 通用协商协议（E1/E2/E11/E13/E15 共用）

```
协商状态机（确定性骨架，内容层填文本）:
  OFFER_CREATED ──应约──► OFFER_ACCEPTED ──► 结算（走对应经济/关系事件）
        ├─婉拒──► OFFER_REJECTED  （Polite Rejection；可终止）
        └─还价──► OFFER_COUNTERED ──► (回到 OFFER_CREATED，轮次+1)
  约束：round_no ≤ N_round（默认 3）→ 超限确定性终止(EXPIRED)
  接受/还价阈：确定性效用函数 util(terms | agent 状态/目标)；LLM 只生成措辞
```
- 协商**结果**（接受与否、轮数）**全部确定性**；LLM 不决定结果，只生成语言。

---

## 4. 活动模板库规格（应要求 3）

### 4.1 模板 schema（【已定】，数据落 config，确定性）

```jsonc
// config/activity_templates/<template_id>.json
{
  "template_id": "mentorship",
  "activity_type": "learn",                 // 取自 06 §10 的 8 类枚举
  "place_allowed": ["school","workshop","library"],
  "slot_allowed": ["morning","afternoon"],
  "participants": {"min": 2, "max": 2, "roles": ["mentor","mentee"]},
  "preconditions": {                         // 全部确定性可判定
    "skill":    [{"who":"mentor","skill_id":"*","op":">=","val_rel":"mentee+2"}],
    "relation": [{"dim":"familiarity","op":">=","val":"ε"}],   // ε=20 (06)
    "need":     [{"who":"mentee","dim":"mastery","op":">=","val":"θ_dep"}],
    "place_capacity": true, "open_slot": true
  },
  "deterministic_settlement": {              // 结算钩子（见 §4.2）
    "hook": "L3.settle_activities",
    "effects": {
      "skill":   [{"target":"mentee","skill_id":"*","delta":"growth(effort)"}],
      "need":    [{"who":"mentee","dim":"mastery","delta":"+g"}],
      "relation":[{"from":"mentee","to":"mentor","dim":"respect","delta":"+k"}]
    }
  },
  "outputs": {
    "resource_intents": [],                  // 货币后果 → pending_intents → 4.x
    "memory": {"kind":"observation","importance_rule":"rule_or_llm_frozen"},
    "tags":   ["knowledge_transfer"]
  },
  "llm_slots": {                             // 仅内容填充（N 类）；可选 F 类软判定
    "plan_text": true, "dialogue": true, "narrative": true,
    "soft_judgment": {"dimension":"mentor_relation","envelope_from":"D+R"}   // 可选
  },
  "cost_class": "T1",                        // 默认执行层（T0 规则 / T1 小模型 / T2 LLM）
  "event_emit": ["ACTIVITY_STARTED","ACTIVITY_COMPLETED","SKILL_LEVEL_UP","RELATION_CHANGE"]
}
```

### 4.2 模板库总表（覆盖 20 类事件）

| template_id | 对应事件 | activity_type | 默认场所 | 时段 | 人数 | 判定 | 执行层 |
|---|---|---|---|---|---|---|---|
| `mentorship` | E1 | learn | school/workshop | morning/afternoon | 2 | D+F | T1 |
| `gift` | E2 | socialize | plaza/cafe | evening | 2 | D | T0/T1 |
| `combat_training` | E3 | leisure | park | morning/afternoon | 1–2 | D+R | T1 |
| `creative_collab` | E4 | socialize | hall/workshop | evening | 2–6 | D+F | T2 |
| `savings` | E5 | trade | bank | morning/afternoon | 1 | D | T0 |
| `whisper` | E6 | socialize | residence/cafe | evening/night | 2 | D(+F) | T1 |
| `burnout_event` | E7 | —（状态判定） | residence | any | 1 | D | T0 |
| `contest` | E8 | leisure/civic | hall/plaza | evening | 2–N | D(+F) | T2 |
| `scarce_buy` | E9 | trade | market | afternoon | 1–N | D | T0 |
| `skill_practice` | E10 | learn | school/library/farm/workshop | morning/afternoon | 1 | D | T0 |
| `polite_reject` | E11 | —（协商环节） | any | any | 2 | D(+F) | T0 |
| `job_choice` | E12 | civic/work | town_hall/office | morning | 1 | D(+F) | T2 |
| `group_proposal` | E13 | civic | town_hall/plaza | morning/afternoon/evening | ≥5 | D | T2 |
| `academic_collab` | E14 | learn | school/library | morning/afternoon | 2–5 | D+F | T1/T2 |
| `counter_propose` | E15 | —（协商环节） | market/cafe | any | 2 | D | T0/T1 |
| `select_location` | E16 | —（决策） | any | any | 1–N | D | T0 |
| `power_conflict` | E17 | civic | town_hall/market | afternoon/evening | 2–N | D+R | T2 |
| `rel_accept` | E18 | socialize | any | any | 2 | F(+D) | T1 |
| `ice_break` | E19 | socialize | plaza/cafe/community_center | any | 2 | D(+F) | T1 |
| `rel_maintain` | E20 | socialize | any | any | 1–2 | D | T0/T1 |

### 4.3 与 T8 Phase 3.5 生活层 hook 的对接（【已定】）

```
[Phase 2 DECIDE]        LLM/T0 生成 INTENT.ACTIVITY{template_id, participants,...}
                        → 硬内核校验 preconditions（场所/时段/容量/关系/技能）
                        → 不合法: INTENT_REJECTED（08 §1.2 H）
[Phase 3.5 L2 resolve_schedule]
                        到期 slot 实例化模板 → ACTIVITY_STARTED（写 place/slot/participants）
[Phase 3.5 L3 settle_activities]
                        deterministic_settlement.effects 结算：
                          - skill/need 变化 → SKILL_*/NEED_UPDATE
                          - 货币后果 → state.pending_intents（交 4.1/4.2，**L-2 不直接改账**）
                          - 协商类模板 → 产出 OFFER_CREATED/OFFER_COUNTERED/OFFER_ACCEPTED/OFFER_REJECTED 事件
[Phase 3.5 L5 update_relations]  relation effects → RELATION_CHANGE
[Phase 3.5 L6 write_memories]    outputs.memory → MEMORY_WRITE / OBSERVATION
[Phase 3.5 L7 emit_tags]         outputs.tags → TAG_EMITTED；NORM_* 阈值判定
```
- **模板即数据**：新增活动只需加一个 config 文件，**不改引擎代码**（可复现：模板文件纳入 `engine_version` 指纹）。
- **内容与判定分离**：`llm_slots` 只填文本/（可选）F 类软判定；`deterministic_settlement` 只由确定性代码执行。

---

## 5. 可产生性自查（应要求 4）

> 逐条结论：**A=现有机制即可产生**（v1 经济/生命周期 + 08 生活层事件已足）；**B=需人格生活层补齐**（依赖 06 的 need/goal/relation/skill 等，已在 06 设计，实现即产生）；**C=需新增规则/事件**（本文 §2/§3 需补登记）。
> **⚠️=在「单小镇 + 周尺度(84 回合/周)」下实际较难触发**（规模/时长/资源约束）。

| # | 事件 | 结论 | 难触发 | 关键依赖 / 补齐项 |
|---|---|---|---|---|
| E1 | Mentorship | **B+C** | | 06 skill/relation + `LLM_JUDGMENT(mentor_relation)` 登记 |
| E2 | Gift-giving | **A+B** | | v1 `TRANSFER` + 06 relation |
| E3 | Combat Training | **B+C** | | 06 skill + §3 对抗结算 + `CONFLICT_*`（对练版可轻量） |
| E4 | Creative Collab | **B+C** | ⚠️ | 需 ≥2 高技能同龄 Agent 且同场所——50/N=20 小镇密度；周尺度可发生 |
| E5 | Saving Money | **A** | | v1 银行/存款机制；`DEPOSIT/WITHDRAW`(已登记 08 §1.2 L) |
| E6 | Whispered Comm. | **A+B** | | v1 `MSG_DM` + 06 relation/secret_trust(F) |
| E7 | Emotion Burnout | **B+C** | | **强依赖临界资源**：06 `need.energy/leisure` + decay + `STATE_CHANGE(exhausted)`/状态；周尺度需足够负载 |
| E8 | Diff. Scoring | **C** | ⚠️ | 需 §3.1 评分规则 + `SCORE_POSTED/RANKING_EMITTED`(已登记)；评比场景需被设计触发 |
| E9 | Scarcity Buy | **A** | | v1 市场机制 + 稀缺供给参数 |
| E10 | Skill Practice | **A+B** | | 06 skill/目标 |
| E11 | Polite Rejection | **B+C** | | 协商协议 + `OFFER_REJECTED`（与违规拒绝分离） |
| E12 | Passion vs Salary | **B+C** | ⚠️ | **强依赖稀缺+内在目标**：06 `goal_tendencies/values` + 经济薪资差；需岗位市场足够分化 |
| E13 | Group Proposal | **B+A** | ⚠️ | 需 ≥5 人共识议题 + 治理场景；周尺度内可发生但依赖触发设计 |
| E14 | Academic Collab | **B** | | 06 skill/goal；`school` 容量 10 足够 |
| E15 | Counter-propose | **B+C** | | 协商协议 + `OFFER_COUNTERED`(已登记) |
| E16 | Select Location | **A** | | v1 场所 + 08 `PLACE_MOVE` |
| E17 | Power Conflict | **C** | ⚠️ | 需 §3.2 对抗规则 + `CONFLICT_*`；小镇 + 稀缺→冲突，但需资源紧张才能触发 |
| E18 | Rel. Acceptance | **B+C** | | 06 relation + `LLM_JUDGMENT(friendship_label)` |
| E19 | Ice-breaking | **A+B** | | v1 `MSG_*` + 08 `RELATION_ENCOUNTER` |
| E20 | Rel. Maintenance | **B** | | 06 关系衰减函数 + 维护动作 |

**难触发项小结（⚠️）**：E4/E8/E12/E13/E17 —— 共同原因是「**需要足够的社会密度、岗位/资源分化或被主动设计的评比/治理场景**」。**建议 T10 沙盒显式植入触发脚本**（如投放稀缺、发起评比/提案），否则纯自发概率低。**这是 v1.1 需重点关注的「可产生性风险」**（记入 §7）。

---

## 6. 与临界资源 / 内在需求的关系（应要求 5）

| 事件 | 依赖的稀缺/需求 | 需生活层提供 |
|---|---|---|
| E7 Emotion Burnout | `need.energy/leisure` 持续低 + 过劳 | `need.dim`+`decay[]`+活动负荷+负事件；耗竭函数 |
| E12 Passion vs Salary | 薪资差（经济稀缺）+ `values/goal_tendencies` | M1 派生标量（saving/risk）、M7 目标与价值拟合 |
| E9 Scarcity Buy | 商品稀缺 + 需求 | 市场供给参数（econ）+ 需求 |
| E5 Saving Money | 现金盈余 + `saving_propensity` | M1 储蓄倾向；v1 银行 |
| E17 Power Conflict | 稀缺资源/决策权争夺 | 资源掌控量、盟友网络、respect |
| E2 Gift-giving | 盈余资源 + 强关系 | relation + 资源 |
| E13 Group Proposal | 公共议题 + 治理参与 | 目标/规范倾向、town_hall 场景 |
| E4/E8/E14 协作与评比 | 技能/资源分化 + 目标 | skill、goal、资源 |

**结论**：生活层的 **`need` 6 维 + `goal_tendencies/values` + `skill` + 关系数值** 是上述事件可产生性的**共同前置**；缺任一项，相关事件将**不可实现或退化为纯叙事**。这些均已在 06 设计为确定性数值（**非 LLM**），满足可判定与可复现。

---

## 7. 已定 / 待讨论 / 冲突清单

### 7.1 已定（可直接实现）
- 20 类事件逐条的触发条件、协商协议、判定归属（D/F/N/R）、日志事件、观测指标（§1）。
- 对抗/评分类确定性结算规则（§3.1 `Diff. Scoring`、§3.2 `Power Conflict`、§3.3 通用协商状态机）——**LLM 不当裁判**。
- 活动模板库 schema 与总表、与 Phase 3.5 L2–L7 的对接（§4）。
- 可产生性自查（§5）与临界资源关系（§6）。
- 判定归属纪律：金额/死亡/结算/胜负/名次 = D；LLM 仅 F（冻结，进门禁外）/N。

### 7.2 待讨论
- **D14-1**：~~§2 补充事件命名与登记~~ → **已全部裁决**（见 §7.3）；命名已统一为 08 口径（`OFFER_CREATED/OFFER_COUNTERED/OFFER_ACCEPTED/OFFER_REJECTED/OFFER_EXPIRED`、`RANKING_EMITTED`）。
- **D14-2**：~~`PROPOSAL/VOTE` 是否复用 `NORM_*`~~ → **已裁定**：复用 `NORM_PROPOSED/ADOPTED` + `OFFER_*`，不新增。
- **D14-3**：~~`LOCATION_SELECTED` 是否并入 `PLACE_MOVE`~~ → **已裁定**：并入。
- **D14-4**：~~E7 是否引入状态 `exhausted`~~ → **已裁定**：不新增事件，以 `STATE_CHANGE(exhausted)` 承载（T14-C4，交 02 定义该状态）。
- **D14-5**：E12/E17 的效用/威力权重 `α..ε` 取值（T10 标定）。
- **D14-6**：难触发项（⚠️）的沙盒触发脚本设计（交 T10）。

### 7.3 冲突清单（先补登记、冲突记此）
| 编号 | 事项 | 现状 | 处理 |
|---|---|---|---|
| T14-C1 | 协商类事件（`OFFER_*`）未登记 | 08 无 | **已登记**（08 §1.2 K）：`OFFER_CREATED / OFFER_ACCEPTED / OFFER_REJECTED / OFFER_COUNTERED / OFFER_EXPIRED`（Leader 批准） |
| T14-C2 | `SCORE_POSTED/RANKING`、`CONFLICT_*` 未登记 | 08 无 | **已登记**（08 §1.2 K）：`SCORE_POSTED / RANKING_EMITTED`、`CONFLICT_STARTED / CONFLICT_RESOLVED`（Leader 批准） |
| T14-C3 | `DEPOSIT/WITHDRAW` 命名 | v1 以 `LOAN_*`/`TRANSFER` 承载银行行为 | **已裁定·已登记**：`DEPOSIT/WITHDRAW/INTEREST_PAID` 入 08 §1.2 L（phase=4.2，不入流速/I_eff）；M_supply 口径待 Q1 |
| T14-C4 | `WELLBEING_ALERT` vs `STATE_CHANGE(exhausted)` | 02 未定 | **已裁定·不新增事件**：以 `STATE_CHANGE`（含 `exhausted`）为唯一事实源；well-being 告警为观测层派生指标（由日志重算） |
| T14-C5 | `INTENT_REJECTED`（规则拒绝）与 `OFFER_REJECTED`（礼貌婉拒）区分 | 08 已登记 `INTENT_REJECTED` | **已确认**：二者并存、语义分离，统计分别计入「意图拒绝率」/「协商婉拒率」 |
| T14-C6 | `SKILL_*` 命名 | 08 已登记（WB-C1） | 无冲突，直接引用 |
| T14-C7 | `GOAL_ABANDON`（E12）未登记 | 08 无 | **已登记**（08 §1.2 C，独立事件，T17 批准）；并补 `GOAL_ACHIEVED`/`GOAL_ABANDON` 确定性产生钩子 |
| T14-C8 | `NORM_VIOLATED` 无产生者 | 08 §1.2 F 已登记类型 | **已补产生者**：Phase 3.5 L7 为主、4.5 `apply_penalty` 为辅，确定性规则检测（T17 裁定） |

### 7.4 T14-C3 最终裁定：已采纳 econ 建议并登记 `DEPOSIT/WITHDRAW`

**Leader 2026-10-09 复核裁定：采纳方案 (a)——登记 `DEPOSIT/WITHDRAW`（见 08 §1.2 L）。**

**econ（01 权威）答复要点**（已据此登记）：
- **独立事件**（不复用 `TRANSFER`），理由：① 语义不同（主体↔银行 负债科目转移 vs 主体↔主体支付），复用会污染**基础流速 / wash-环路-自成交反作弊 / I_eff** 三处口径；② 「储蓄率/存款分布」指标需独立事件锚点；③ 货币守恒校验需事件锚点。
- **口径（已登记）**：`DEPOSIT`/`WITHDRAW`，phase = **4.2 settle_obligations**；payload `{agent_id, amount, cash_after, deposit_after}`；`INTEREST_PAID`（4.2，bank→agent）与 `INTEREST_CHARGED` 成对；**不计入基础流速、不计入 I_eff**。
- **配套（⚠️ 属 v1 开放问题 Q1，待用户确认）**：银行须为**显式 money holder**（`M_supply = Σmax(cash,0) + 税池 + 银行库存`）；净值 `E = cash + 存款 + 资产估值 − (贷款本息)`。已记入 08 §5.7，标注「Q1 推荐口径·待确认」，交 T11 呈报。

---

*（全文完 — sim-engine-stats-architect。本文以 00 架构、06 生活层枚举、08 事件 schema 为权威；20 类事件逐条可判定、可复现、LLM 边界无歧义；补充事件按「先补登记、冲突记清单」处理。）*
