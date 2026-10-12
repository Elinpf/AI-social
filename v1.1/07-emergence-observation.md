# 07 · 涌现观测层（M8）与观测方法论 v1.1

> **【Fork B 时效标注 · 2026-10-12】** 凡本文以「逐位/字节相等」作**可复现门禁**处，按 Leader Q-12.1 改为「**保留可复算、字节相等降为诊断**」。**单一口径见 `v2/refs/gate-grading.md`。**

> 文档类型：领域设计（涌现观测层 L2 / M8）｜ 作者：emergence-observer-designer（涌现观测层设计专家）
> 状态：v1.1 设计草案（供 Leader 汇总；标注【已定】/【待讨论】/【冲突】）
> 上游依据：
> - `v1.1/00-architecture.md`（T12 架构基线：三层架构、单小镇「青溪镇」、周尺度 `1 周=84 回合`、只读契约 IF-4、软判定冻结 §5.5）
> - `v1.1/08-engine-stats-extension.md`（T8 事件表 §1.2、Phase 3.5、时间结构 §3、指标命名空间 §4）
> - `research/town-life-brief.md`（Smallville「种子事件→自主传播」范式、Agentopia 教训）
> - `v1/05-v1-proposal.md`（v1 护栏判据与开放问题 Q1–Q13）
> 下游对齐：`v1.1/09-sandbox-v1.1.md`（T10 需 T9 提供「突现成立」阈值与观测判据清单）
> 标签约定：**【已定】**=本轮基线，下游可直接引用；**【待讨论】**=语义未收敛，交 Leader/用户/T7 标定裁决；**【冲突】**=与上游口径不一致，须回写消解。

---

## 0. 定位、判定铁律与判定分层

### 0.1 本层定位（【已定】）

涌现观测层（L2，对应模块 **M8 社会规范/文化浮现**）是**只读度量与描述层**：

```
metrics(log, T, TIME_CONFIG) -> Snapshot        # 纯函数、确定性
narrate(fact_event_seqs)     -> text            # LLM 描述，纯输出、非权威
```

- **唯一输入**：`EventLog` + `turn_seal`（T12 IF-4 / §4.4）。**不读 L1 私有内存、不写世界状态、不触发 LLM/嵌入**。
- **观测对象**（T9 任务书）：关系形成/破裂、观点与信息传播、圈层与群体涌现、规范形成、身份/职业转变；外加核心范式「种子事件→自主传播」。
- **产物形态**：涌现判定是一份**可复现的报告** `emergence_report(log, T, params)`（侧产物，**不入世界日志、不影响状态**）。因 L2 只读，判定结果**不作为事件写回**世界；其确定性保证 = 同 `(log, T, params)` 两次计算**逐位一致**（§0.4）。

### 0.2 判定铁律（【已定】，含 Leader 口径更新「方案甲」）

用户已确认**方案甲**：允许 LLM 做定性社会判断，但其结果**冻结进日志**，重放/统计只读日志。据此把铁律精确化为 **R1–R7**：

| # | 铁律 | 说明 |
|---|---|---|
| **R1** | **判定只读日志** | 所有涌现/关系/规范/传播的**判定**只用可从 `EventLog` 确定性重算的指标；判定输出是 `f(EventLog, T, params)`。 |
| **R2** | **计算过程 `llm_calls == 0`** | 计算任何指标/判定时**不得发起任何 LLM 调用**（不重问模型、不重算嵌入）。硬校验：`metrics()` 内 `llm_calls == 0`。 |
| **R3** | **冻结 LLM 判定「可读不可算」** | 日志中的 `LLM_JUDGMENT`（T12 §5.5，`frozen=true`）**可作为输入读取**（如「师徒关系是否建立」「声望变化」），但**计算时不得现调 LLM**；该字段**必须标记来源 `frozen_llm`**，以便审计与敏感性分析。 |
| **R4** | **分栏列示** | 含 LLM 冻结判定的指标与纯确定性指标**分开列示**（见 §0.3 的 D/F/K 分类），使读者能判断「哪些结论依赖 LLM 判定」。 |
| **R5** | **硬内核不接 LLM** | **硬内核类指标（钱 / 死亡 / 交易）绝不允许以 LLM 判定为输入**（对应 T12 §1.5 角色带①「LLM 绝不碰金额/死亡/结算」）。 |
| **R6** | **判定与描述分离** | LLM 只用于生成与自然语言描述（`NARRATIVE`，`affects_state=false`）；**描述不得反向影响判定**，判定路径**永不读叙事文本**（T12 IF-7）。 |
| **R7** | **判定不入世界日志** | L2 只读，判定结果不写回世界状态；涌现「成立/不成立」为侧产物报告，可重算、可审计。 |

> **与 T8 §4.10 的调和（关键）**：T8 §4.10 要求核心涌现指标 `llm_judged_metric_count == 0`。本层据此把指标分三级（§0.3）：**核心判定指标（D 类）100% 确定性**，`llm_judged_metric_count == 0` 对 `metrics.emergence` **严格成立**；**含 LLM 冻结判定者单列 `metrics.emergence_soft`（F 类）**，仅作敏感性分析，**不进入判定路径、不作为验收硬门禁**。这样既守住 T8 铁律，又落实方案甲「可读冻结判定」。

### 0.3 指标三级分类（【已定】）

| 级 | 名称 | 输入来源 | 是否参与「涌现判定」 | 命名空间 | 约束 |
|---|---|---|---|---|---|
| **D** | 纯确定性指标 | 仅确定性事件（T8 §1.2 全部；关系数值由 D-12 确定性推导，见 AR-C3） | **是（判定主力）** | `metrics.emergence` / `metrics.life` | `llm_calls==0`；`llm_judged_metric_count==0` |
| **F** | 含 LLM 冻结判定指标 | `LLM_JUDGMENT.frozen`（读回，标 `frozen_llm`） | **否（仅敏感性分析，【已定】定论）** | `metrics.emergence_soft` | 计算时仍 `llm_calls==0`（只读冻结值）；每指标标 `source:"frozen_llm"` |
| **K** | 硬内核指标 | 金额/死亡/交易事件 | 否（作为护栏，见 §5） | `metrics.econ` / `metrics.lifecycle`（v1 冻结） | **绝不以 LLM 判定为输入（R5）** |

> **实现约定**：快照 JSON 中，每个指标条目带 `"basis": "D" | "F" | "K"` 与（F 类额外）`"frozen_ref": [judgment_id...]`。`emergence_report` 头部声明 `llm_judged_metric_count`（统计 `metrics.emergence` 中 basis==F 的条目数，**必须为 0**）、`frozen_llm_metric_count`（`metrics.emergence_soft` 条目数，仅报告，无门禁）。

### 0.4 复现口径（【已定】，沿用 T12 §5.4）

- **判定可复现**：同 `(log, T, params)` 两次 `emergence_report()` 输出**逐字节一致**（规范 JSON、键排序、浮点 `round(...,6)`、全序 tie-break）。
- **整体复现单位是日志**：v1.1 首跑含 LLM 定性判定，跨跑（同 seed 重跑）**不保证**逐位一致；`replay(log)` 与 `metrics()` 对**同一份日志**逐位一致即可（T12 §5.4、AR-C9）。涌现判定据此以**日志**为单位复现。

---

## 1. 观测对象清单（确定性判定规则与阈值）

> 总原则：每项给出 **事件来源（T8 事件）/ 判定规则（公式）/ 触发阈值 / 指标分类（D/F/K）/ 最小可观窗口**。所有判定均为 §0.2 的纯函数。阈值为**符号 + 默认建议值**，标注【待标定】者依赖 T7（`D7-3`）或沙盒（T10）标定。

### 1.1 观测对象总表（【已定】清单，阈值部分【待讨论】）

| # | 观测对象 | 主事件来源（T8 §1.2） | 判定规则（确定性） | 默认阈值 | 分类 | 最小窗口 |
|---|---|---|---|---|---|---|
| A | **关系形成 / 破裂** | `RELATION_CHANGE`、`RELATION_ENCOUNTER` | 边权 `w_dim(a→b)` 由 `RELATION_CHANGE` 折叠；跨越 `ε_strong`/`ε` 判形成/破裂 | `ε=0.2R`、`ε_strong=0.6R`【待标定 D7-3】 | D | 1–2 周（强关系）/ 4–12 周（结构漂移） |
| B | **观点 / 信息传播** | `MSG_*`(+`refs`)、`OBSERVATION`、`TAG_EMITTED`、`SEED_EVENT` | 级联图可达性（§2）；标签频次/份额/采纳 | §2.3、§1.3 | D | 1 周（种子级联）/ 2 周（观点漂移） |
| C | **圈层 / 群体涌现** | `RELATION_CHANGE`（→`G_rel`） | `Louvain(G_rel)` 社区数/模块度/规模分布/ARI 稳定性 | `Q≥0.30`、`ARI≥0.60`、社区规模 `≥3` | D | 4 周（结构涌现） |
| D | **规范形成** | `NORM_PROPOSED/ADOPTED/VIOLATED` | 采纳=支持者≥阈值（纯规则）；覆盖率/违反率 | 支持率阈值 `θ_sup=0.50·alive`；`θ_cov=0.30` | D | 2–4 周 |
| E | **身份 / 职业转变** | `ROLE_CHANGE`、`GOAL_ACHIEVED` | 转移矩阵、切换率、角色熵偏移 | `Δrole_entropy ≥ θ_H`、`switch_rate > 基线` | D | 4–12 周 |
| F | **记忆 / 反思（辅助）** | `MEMORY_WRITE/RETRIEVE/REFLECT` | T8 §4.9 | 供成本与行为分析 | D | 1 周 |
| G | **（软）关系/声望定性标签** | `LLM_JUDGMENT.frozen` | 读冻结 `decision` 计数 | — | **F（仅描述）** | 同 A |
| K | **（护栏）经济 / 死亡** | `TRANSFER/MARKET_TRADE/.../AGENT_DIED` | v1 §5（口径冻结） | v1 护栏阈值 | **K** | 见 §5 |

### 1.2 A · 关系形成 / 破裂（【已定】规则）

**输入**：`RELATION_CHANGE{from,to,dim,before,after,cause,cause_event_seq}`、`RELATION_ENCOUNTER{a,b,place,day,slot,duration_ticks}`。数值 `w_dim` 必须由确定性函数从 `cause` 推导（T12 AR-C3 / D-12），**LLM 只产叙述**。

**折叠与判定**（确定性）：

```
w_dim(a→b, t) = 折叠所有 t' <= t 的 RELATION_CHANGE(from=a,to=b,dim) 的最后一笔 after
值域 [W_MIN, W_MAX]（由 T7 定；越界 -> SYSTEM_ERROR，T8 不变量 7）
```

| 判定 | 规则 | 分类 |
|---|---|---|
| **关系形成（强边）** | 存在 `dim` 使 `w_dim` 在回合 t 由 `< ε_strong` 升到 `≥ ε_strong`（或边首次出现且 `≥ ε_strong`） | D |
| **关系破裂** | 存在 `dim` 使 `w_dim` 由 `≥ ε_strong` 跌到 `< ε`（或边消失） | D |
| **强互惠** | `w_dim(a→b) ≥ ε_rec` 且 `w_dim(b→a) ≥ ε_rec`（`ε_rec` 默认=`ε_strong`） | D |
| **首次相遇** | `RELATION_ENCOUNTER` 首次出现于 `(a,b)` | D |

**聚合指标**（周期窗口）：`tie_formation_rate`、`tie_decay_rate`、`reciprocity(dim)`、`mean_degree(dim)`、`PageRank(G_rel)`（`d=0.85`、固定 K 次、节点按 `agent_id` 升序，T8 §4.3）。

**F 类补充（单列、不判定）**：`metrics.emergence_soft.relation_label_counts` 读 `LLM_JUDGMENT.dimension ∈ {friendship_label, mentor_relation}` 的冻结 `decision` 计数，标 `frozen_llm`。

> **阈值**【待讨论】：`ε/ε_strong/ε_rec/W_MIN/W_MAX` 依赖 T7 `D7-3`；本层给出默认建议 `ε=0.2R, ε_strong=0.6R`（`R=W_MAX−W_MIN`），沙盒标定后回填。

### 1.3 B · 观点 / 信息传播（【已定】规则）

**输入**：`TAG_EMITTED{agent_id,tag,valence,source_msg_id}`、`MSG_*{refs,tag_hints}`、`OBSERVATION{observer,target_event_seq,salience}`、`SEED_EVENT`。

| 判定 | 规则（确定性） | 默认阈值 | 分类 |
|---|---|---|---|
| **标签浮现** | 标签 `tag` 的 `adoption_W(tag) ≥ θ_adopt` 且 `trend_W` 连续 k 窗口 >0 且 `share_W` 超基线 | `θ_adopt=0.20·alive`，`k=2`【待标定】 | D |
| **观点极化** | `HHI_W` 或 `entropy_W` 相对基线跃迁且持续 k 窗口 | `Δentropy ≥ 0.15·ln(K)` | D |
| **观点转向** | `valence_mean_W(tag)` 符号翻转且后窗口样本 `freq≥f_min` | `f_min=5` | D |
| **级联传播** | 见 §2（可达性定义） | 见 §2.3 | D |

指标公式沿用 T8 §4.5（`freq/share/entropy/HHI/adoption/valence/trend`），`entropy/HHI` 定点或 `round(...,6)` 输出并标 `num_method`。

### 1.4 C · 圈层 / 群体涌现（【已定】规则）

**输入**：`G_rel`（由 A 折叠）。**社区发现算法选型（【已定】，Leader 裁决 T9-D1）**：**确定性 + 可复现优先**——
- **主算法**：**固定种子 + 全序 tie-break 的 Louvain/Leiden**，结果须能由 `(日志, seed)` **唯一确定**，**禁止依赖运行环境/并行顺序**；
- **对照基线**：同时输出更简单的**确定性基线（连通分量 + k-core）**，便于交叉核验；
- **版本冻结**：算法参数与版本号写入 `engine_version`，保证重放一致。

| 判定 | 规则 | 默认阈值 | 分类 |
|---|---|---|---|
| **圈层涌现** | 相对基线 `n_communities` 增加 `≥1` 且 `Q ≥ Q_min`，且该社区规模 `≥ s_min` | `Q_min=0.30`、`s_min=3` | D |
| **圈层稳定** | 相邻两窗口 `ARI(comm_W, comm_{W-1}) ≥ θ_stable` | `θ_stable=0.60` | D |
| **边缘化**（Agentopia「社交建筑师被边缘化」） | 某 Agent 的 `weighted_degree` 排名由 Top `p` 跌出 Top `q` 且持续 k 窗口 | `p=0.3,q=0.6,k=2`【待标定】 | D |

指标：`n_communities/modularity Q/size_dist/membership_stability(ARI)/isolation_rate`（T8 §4.6）。

### 1.5 D · 规范形成（【已定】规则）

**输入**：`NORM_PROPOSED{norm_id,proposer,rule_ref,support_count,threshold}`、`NORM_ADOPTED{adopters[],adopted_day,threshold_used}`、`NORM_VIOLATED`。

- **采纳判定 = 纯规则**：`NORM_ADOPTED` 当且仅当支持者数 `≥ threshold_used`（**LLM 不判定**，T8 §4.7、T12 D-14）。

| 判定 | 规则 | 默认阈值 | 分类 |
|---|---|---|---|
| **规范形成** | 窗口内 `n_norms_adopted ≥ 1` 且 `norm_coverage ≥ θ_cov` | `θ_cov=0.30` | D |
| **规范内化** | `norm_violation_rate` 随窗口下降且 `< θ_viol` | `θ_viol=0.05`【待标定】 | D |
| **程序正义** | `adoption_success_rate = n_adopted/n_proposed`（无 LLM 参与） | 报告值 | D |

指标沿用 T8 §4.7（`adoption_success_rate/time_to_adopt/norm_violation_rate/norm_coverage`）。

### 1.6 E · 身份 / 职业转变（【已定】规则）

**输入**：`ROLE_CHANGE{agent_id,from_role,to_role,cause,day}`、`GOAL_ACHIEVED`。角色 ∈ T12 §2.5 的 10 类。

| 判定 | 规则 | 默认阈值 | 分类 |
|---|---|---|---|
| **个体身份转变** | 单 Agent 在窗口内 `≥ n_switch` 次 `ROLE_CHANGE` | `n_switch=2` | D |
| **群体结构漂移** | `role_entropy` 相对基线偏移 `≥ θ_H` 或 `switch_rate > 基线 + θ_sr` | `θ_H=0.10·ln(K_role)`【待标定】 | D |
| **职业迁移路径** | `transition_matrix[from][to]` 出现非平凡转移（`from≠to` 且计数 `≥ c_min`） | `c_min=2` | D |

指标沿用 T8 §4.8（`transition_matrix/role_entropy/switch_rate`）。

> **【已定】T9-D2（角色扩展，回应 T12 AR-D3 / T10 S-C8）**：**本轮不扩，保持 10 类**（Leader 裁决）。理由：当前目标 **N=20「先跑通」**，扩到 12 会稀释每类角色在 20 人里的样本量。`courier`（快递员）/`journalist`（记者）列为 **N=20 跑通后的第一批候选扩展（待跑通后评估）**，主要服务**传播链观测**（可用 `journalist` 作公告板信息中介提升 `depth≥2`）。

---

## 2. 核心实验范式：种子事件 → 自主传播（Smallville 复刻）

> 依据 town-life-brief §2.3：给一个用户设定，Agent **自主传播**邀请/信息、建立新相识、协调参与。v1.1 以此为**核心观测范式**；唯一人类干预入口 `inject_seed_event → SEED_EVENT`（T12 IF-5 / §4.1、T8 §1.2-F）。

### 2.1 范式定义（【已定】）

1. **注入**：观察者经 IF-5 注入**一个** `SEED_EVENT{seed_id, kind, injected_by:"OBSERVER", payload}`。默认种子 = 「某 Agent 想在**周末**于 `hall`（礼堂，T12 §2.2）办一场活动」，注入时刻 `t0` 取周末前夕（如 day5 morning），使扩散落在 weekend（`social_event_prob` 高，T12 §3.3）。
2. **不追加干预**：随后**不做任何额外干预**，只被动观测。
3. **传播图（确定性，来自日志）**：

```
节点：参与该 seed 级联的事件 (event, agent) 二元组
边 u→v：存在 OBSERVATION(observer=v, target_event_seq ∈ u的事件)
        或 msg(v).refs 含 u 的 msg_id（同一 seed 级联内）
级联 C(seed) = 从 SEED_EVENT 出发、在窗口 Δ 内可达的子图
```

4. **不依赖 LLM**：级联完全由图可达性定义；标签/正文仅作 `OBSERVATION` 锚点（T8 §4.4）。

### 2.2 传播度量（【已定】，口径同 T8 §4.4）

`cascade_size`、`depth`、`breadth`、`R0`（传播者平均出度）、`time_to_spread`（首达各层级 tick 中位数）、`reach_ratio`（去重 Agent 数 / `alive_count`）、`path_len_dist`（固定分箱）。

### 2.3 「突现成立」判据（【已定】规则骨架，阈值【待讨论】）

一次种子级联判定为**「自主传播成立」**，当且仅当**全部**满足：

```
(1) reach_ratio ≥ θ_reach          默认 0.50（N=10 沙盒）/ 0.45（N=20 目标）/ 0.40（N=50 展望）
(2) depth     ≥ 2                  # 排除「一次广播直达全员」的平凡传播
(3) R0        ≥ 1.0                # 传播者平均出度 ≥ 1（超临界，自持）
(4) time_to_spread ≤ W_seed        默认 W_seed = 1 周（84 回合）
(5) A/B 对照差异显著（§3.4）：Δ = m_A − m_B ≥ θ_effect 且 p ≤ 0.05
(6) 稳定性：级联未被配额/规则强制终止主导（INTENT_REJECTED 中 quota 原因占比 < θ_cap）
```

- **周尺度可观测性**：种子注入于 day5，扩散落在 day5–day6（周末 2 日 = 24 回合内），远小于 1 周（84 回合），**周尺度内可完整观测**。
- **平凡传播排除**：若 `breadth ≈ N` 而 `depth = 1`（公告板一发直达全员），**判为「广播而非涌现」**，不成立。这是对抗「假涌现」的第一道闸（§6.3）。
- **阈值**【待讨论】`θ_reach/θ_effect/θ_cap/W_seed` 由 T10 用沙盒实测标定；本层给默认建议值。

> **对 T10 的交接**（回应 `09` §2「待补（T9）」与 §7 待核对项 5）：本节即「突现成立」阈值与判据清单，且与 T8 §4.4 公式、T12 `SEED_EVENT` 契约一致。

---

## 3. 时间窗与基线对照（避免把自然波动误判为涌现）

> 核心问题：涌现判据必须与**同环境下的自然波动**区分。全部对照与显著性检验均为**确定性统计口径**（种子化 RNG，无 LLM）。

### 3.1 三类对照（【已定】）

| 对照 | 做法 | 用途 |
|---|---|---|
| **① 组内基线（同 run）** | 基线窗 `B0 = [t0−Wb, t0−1]`（无种子、无重大干预）；观测窗 `Wx = [t0, t0+Wx−1]` | 剔除该 run 自身的自然波动基线 |
| **② A/B 双胞胎对照（跨 run）** | A 组注入种子；B 组**同 seed、去掉 SEED_EVENT 注入**（其余 RNG 流不变） | 分离「种子效应」与「环境规则固定效应」 |
| **③ 多 seed 复现** | `≥3` 个不同 `global_seed` 重复 A/B | 验证跨实现稳定性（非偶然） |

- **A/B 口径**：因 v1.1 首跑含 LLM 定性判定、跨跑不逐位一致（T12 §5.4），A/B 比较**用确定性指标（D 类）**，并记录各自 `log_hash` 与 `LLM_JUDGMENT` 差异摘要，做**敏感性标注**（F 类单列）。

### 3.2 时间窗规格（【已定】框架，取值【待讨论】）

| 窗 | 默认 | 说明 |
|---|---|---|
| 基线窗 `Wb` | 1 周（84 回合） | 短窗主档；长窗可 2–4 周 |
| 观测窗 `Wx` | 1 周（种子级联）/ 2–4 周（结构涌现） | 依观测对象（§1.1「最小窗口」列） |
| 滑窗步长 | 1 周 | 用于稳定性与趋势 |

### 3.3 显著性 / 稳定性判据（【已定】确定性口径）

```
判据 S1（噪声带）：m 在整段运行上做长度 Wx 的确定性滑窗采样，得 mean μ、MAD σ；
                   要求 obs = m(Wx) > μ + z·σ（z=3 默认）。
判据 S2（置换检验）：固定 RNG seed，对事件时间标签做 N_perm=1000 次确定性置换，
                   经验 p 值 = #{perm ≥ obs}/N_perm；要求 p ≤ 0.05。（因 RNG 固定 -> 可复现）
判据 S3（跨 seed 稳定性）：≥3 seed 中至少 ⌈2/3⌉ 方向一致（符号检验）。
判据 S4（时间稳定性）：指标在观测窗内 k 连续子窗口均满足阈值（k=2 默认）。
判定 = S1 ∧ S2 ∧ S3 ∧ S4（可配置放宽，但须在报告中显式声明）。
```

- **确定性保证**：置换检验的**排列种子固定**（`stream_id="emergence.perm"`），`N_perm` 固定，故 p 值是 `(log, T, params)` 的纯函数。
- **误判防线（把自然波动排除）**：必须**同时**满足噪声带（S1）与时间稳定性（S4），避免「单周尖峰」被当成涌现。

### 3.4 A/B 差异的确定性判定（【已定】）

```
Δ_m = m_A − m_B                     # 仅对 D 类指标
通过 iff Δ_m ≥ θ_effect 且 p_AB ≤ 0.05（对 A/B 两组做 §3.3 的置换检验）
```

- `θ_effect` 默认：连续指标取 `θ_effect = 0.5·σ_B`；计数指标取 `≥ 2` 个事件单元差。【待标定】

---

## 4. 叙事观测 vs 数字指标（分工与隔离）

> 铁律 R6：**叙述生成不得反向影响判定**。

### 4.1 分工（【已定】）

| 维度 | 数字指标（证据） | 叙事观测（供人阅读） |
|---|---|---|
| 载体 | `metrics.emergence`（D）/ `metrics.emergence_soft`（F） | `NARRATIVE` 事件（`affects_state=false`），正文入侧存储 |
| 产出者 | L2 纯函数 | LLM 叙事层（T12 IF-7） |
| 是否权威 | **是**（判定与验收依据） | **否**（仅可读性） |
| 是否影响判定 | — | **绝不**：判定路径永不读叙事文本 |
| 复现 | 同日志逐位一致 | 文本含侧哈希；不进判定，故不影响复现 |

### 4.2 隔离机制（【已定】）

1. `NARRATIVE` 事件带 `source_event_seqs[]`（只引用**已发生的**事实事件）与 `affects_state=false`；`apply_event(NARRATIVE)` 为**恒等折叠**（不改变世界状态）。
2. `metrics()` / `emergence_report()` 的输入**仅 `EventLog` 中的事实事件与冻结判定**，**显式忽略 `NARRATIVE` 类型**（常数时间跳过）。
3. 硬校验：`emergence_report` 报告头 `narrative_reads_in_decision == 0`。

### 4.3 F 类（含 LLM 冻结判定）的落位（【已定】，落实方案甲）

- 读 `LLM_JUDGMENT.frozen=true` 的 `decision`（T12 §5.5 四要素：`decision + model + context_digest + frozen`），**只读回、不重问**。
- 结果落 `metrics.emergence_soft.*`，每条带 `"basis":"F"`、`"source":"frozen_llm"`、`"frozen_ref":[judgment_id...]`。
- **敏感性分析**：报告同时给出「含 F / 仅 D」两版结论对照（如「关系成形计数」D 版 vs F 版），供读者判断结论对 LLM 判定的依赖度。
- **门禁**：F 类**不参与** §2.3 突现成立判据、§3 显著性、§5 护栏；`metrics.emergence.llm_judged_metric_count` 恒为 0。

---

## 5. 与经济 / 死亡护栏的关系（标注、剔除干预）

> v1.1 中经济/死亡从「实验主角」降为「**健康度护栏 + 极端压力源**」（T12 §0.1、§6.1；T10 §1.1）。护栏 K 类指标口径**冻结**（T8 X3），本层**只引用不重定义**。

### 5.1 护栏清单（K 类，沿用 v1/T10，【已定】）

存活率 ∈[60%,90%]（自然模式）、`gini_shifted ≤0.60`、`default_rate_outstanding ≤5%`、通胀 `M/M_target∈[0.9,1.1]`、单回合 LLM 调用 ≤ 重算预算、可复现、反作弊 C1–C10、守恒不变量、稳定性（T10 §1.1）。

### 5.2 干预 / 护栏越界的**标注**（【已定】）

所有观测窗口打上如下**确定性标签**（来自日志，可由引擎回补，见【冲突】T9-C1）：

| 标签 | 来源 | 含义 |
|---|---|---|
| `observer_injection_count` | `SEED_EVENT` 计数 | 人为干预强度（T8 §4.10） |
| `safety_valve_triggered` | `resolve_revival` 相关事件 | 安全阀介入（v1 两轮制，T10 §1.1） |
| `rescue_flag` | v1 `flag=rescue`（T10 §7.3 两轮制） | 救助干预 |
| `pending_rescue_flagged_events` | 救助相关 `TRANSFER`/`REVIVE_FEE_PAID` | 待统计剔除 |
| `guardrail_ok` | 由 §5.1 派生 | 该窗口是否越界 |
| `death_count_on_window` | `AGENT_DIED` | 极端压力源强度 |

### 5.3 干预如何从涌现观测中**剔除**（【已定】方法，双版本输出）

1. **观察者种子干预**：`SEED_EVENT` 导致的级联标记为**「诱导涌现（induced）」**；「自然涌现（spontaneous）」= 不含 `SEED_EVENT` 锚点的级联。报告**同时给两版**：`enrichment.induced` / `enrichment.spontaneous`。核心范式验收用 induced（§2）；「自然涌现」是更高一层观测，仅在有长窗时报告。
2. **安全阀 / 救助**：含 `safety_valve_triggered` 或 `rescue_flag` 的时间窗，在存活率/关系/传播指标上**标记并剔除**或**单列**（沿用 v1 D5-5「含/剔两版」思路）。安全阀只会**掩盖**真实死亡动态（v1 Q4），故自然模式（关安全阀）为 H2 与传播观测主档。
3. **死亡剔除**：`dead/terminated` Agent 按 v1 Q2 口径从 `alive_count` 分母剔除（结构存活率 vs 死亡事件率双指标，v1 Q2-A）。
4. **作弊边剔除**：图指标（`G_rel/G_money/G_comm`）**同时输出含/剔 `flags∈{wash,cycle,self,mule}` 的两版**（T8 §4.3、v1 D5-5）；传播图剔除虚增边（T10 §2 反作弊）。
5. **护栏越界窗口**：若某窗口 `guardrail_ok=false`，则该窗口的涌现判定**降级为「参考」**（不参与验收），并在报告中显式标注「窗口受护栏扰动」。

> **落到 T8 §4.10 的 `observer_injection_count`**：本层要求把它连同 `guardrail_ok/rescue_flag` 一并进快照，作为「观测是否受干预污染」的显式证据。

---

## 6. 猜想与可证伪点（真实涌现 vs 环境/规则造成的假象）

> 参考 Agentopia 教训（town-life-brief §1.4、`11-agentopia-reuse-assessment.md` §2）：环境模型承担过多判定 → 很多「社会规律」其实来自模型判断，而非独立真实环境；且其指标含 LLM 评判、仿真不可整体重放。

### 6.1 可预期现象（预注册，confirmatory）

| 编号 | 猜想 | 观测手段 | 证伪条件 |
|---|---|---|---|
| H-E1 | 种子事件可自主传播至 `depth≥2` 且 `R0≥1` | §2.3 | 多次多 seed 均 `depth<2` 或 `R0<1` |
| H-E2 | 强关系边随时间由稀疏变稠密（Agentopia：互惠友谊 4.3→10.1 类现象） | §1.2 `tie_formation_rate`、`reciprocity` | 强边数无趋势或下降 |
| H-E3 | 出现职业/身份转变（低概率但非零） | §1.6 `switch_rate>0` | 长窗内 `ROLE_CHANGE=0`（可能说明规则太硬） |
| H-E4 | 出现圈层（`Q` 显著上升、社区稳定） | §1.4 | `Q` 不升或社区完全不稳定（ARI≈0） |
| H-E5 | 规范可被提出并采纳（非 LLM 判定） | §1.5 | 提案全被拒或采纳后立即高违反 |

### 6.2 意外发现（探索性，exploratory）

- **定义**：任何**未预注册**、且相对基线显著（§3.3）的现象。
- **纪律（防过拟合）**：探索性发现**必须在留出（held-out）seed 上复现**才升级为结论；报告**显式分栏** confirmatory / exploratory，避免「事后编故事」。这是对 Agentopia「归因粗糙」教训的正面回应。

### 6.3 三类「假象」及其区分方法（【已定】）

| 假象来源 | 表现 | 区分方法（确定性/可证伪） |
|---|---|---|
| **① 规则内建** | 结构看似涌现，实为硬规则/概率参数直接产生（如周末 `social_event_prob=0.25` 导致活动增多） | **消融对照**：把该参数置 0 重跑，若现象消失 → 规则产物而非涌现 |
| **② LLM 判定污染** | 指标依赖 `LLM_JUDGMENT` 的定性判断 | 用 **D 类（纯确定性）指标复算**；报 F/D 两版对照（§4.3）；`llm_judged_metric_count==0` 守护核心判定 |
| **③ 观察者干预** | 级联由我们注入的 `SEED_EVENT` 直接触发 | 用 §5.3 的 **A/B 对照 + induced/spontaneous 分离** |
| **④ 平凡传播** | 一次广播直达全员被当传播 | §2.3 要求 `depth≥2`；排除 `depth=1` 广播 |
| **⑤ 度量的算法假象** | 社区/中心性随算法或随机种子变动 | 固定算法 + 固定种子 + 全序 tie-break；`membership_stability` 检验（§1.4）；算法对照（Louvain vs Girvan-Newman） |
| **⑥ 小样本偶然** | N=10 单 seed 的偶然 | §3.3 多 seed + 置换检验；沙盒仅作「门禁」，不发布结论 |

> **白盒底线**：所有判定都能从 `EventLog` **独立重算**（README 级可审计），这是区分「真实涌现」与「模型生成的社会规律」的**根本手段**——Agentopia 正因不可重放、含 LLM 评判而无法自证。

---

## 7. 接口对齐与冲突项（交 Leader / T10）

### 7.1 对 T10 的交接（回应 `09` §2「待补（T9）」与 §7 待核对项）

| T10 待补项 | 本层提供 |
|---|---|
| 突现成立阈值 | §2.3 判据 (1)–(6) + 默认 `θ_reach=0.50(N=10)/0.45(N=20)`、`depth≥2`、`R0≥1`、`W_seed=1 周` |
| 对照差异显著性口径 | §3.3 判据 S1–S4 + §3.4 A/B `Δ_m` 与 p 值 |
| 「有意义涌现」判定清单 | §1.1 总表 + §2.3 + §6.1 预注册现象 |
| 待核对项 5（级联阈值与 T8 §4.4 一致性） | 口径同 T8 §4.4，仅补阈值 |
| S-C8（角色扩到 12） | §1.6【已定】T9-D2：本轮不扩，保持 10；`courier/journalist` 列为 N=20 跑通后候选 |

### 7.2 冲突 / 待对齐项

| 编号 | 级别 | 事项 | 处置建议 |
|---|---|---|---|
| **T9-C1** | 中 | §5.2 的干预标签（`rescue_flag/safety_valve_triggered/guardrail_ok`）**当前并非 T8 一等事件字段** | 请 T8/T10 在快照派生层标准化（或引擎回补 `flag=rescue` 到相关事件）；本层只读、不新增写入 |
| **T9-C2** | 中 | 关系数值来源（`G_rel` 可复现性） | 依赖 T12 AR-C3 / T8 D-12：**数值必须确定性**；若 T7 让 LLM 直接给数值，则本层图指标失效（须改「LLM 建议→确定性夹取」，T12 §5.3） |
| **T9-D1** | 低 | 社区发现算法选型 | **已裁决【已定】**：主算法 = 固定种子 + 全序 tie-break 的 Louvain/Leiden（结果由 `(日志,seed)` 唯一确定）；另出确定性基线（连通分量 + k-core）对照；参数/版本入 `engine_version`（对应 T8 D7-4） |
| **T9-D2** | 低 | 角色是否扩到 12（`journalist/courier`） | **已裁决【已定】**：本轮不扩，保持 10；`courier/journalist` 列为 N=20 跑通后第一批候选（AR-D3） |
| **T9-D3** | — | F 类（含 LLM 冻结判定）指标的地位 | **已裁决【已定】**：只作敏感性分析，不进判定路径、不进沙盒门禁；核心判定保持 `llm_judged_metric_count==0` |
| **T9-C3** | 低 | T12 §1.2/§4.4/§9 将本层文档记为 `10-emergence-observation.md`（旧编号） | 本文件实际落盘为 `07-emergence-observation.md`（以任务书为准）；请 T12/T10 引用时按 `07-` 对齐（命名差异，非内容冲突） |
| **T9-C4** | 中 | 本层新增命名空间 `metrics.emergence_soft`（F 类），T8 §4.0 只定义了 `metrics.life/.emergence` | 请 T8 在 §4.0 补登 `metrics.emergence_soft`（落实方案甲「含 LLM 冻结判定指标单列」）；该命名空间**不进入判定/门禁**，仅敏感性分析 |

---

## 8. 已定 / 待讨论汇总

**已定（v1.1 基线，下游可直接引用）**
- 判定铁律 R1–R7（含方案甲：frozen_llm 可读不可算、分栏列示、硬内核不接 LLM）；指标三级分类 D/F/K 与命名空间隔离（§0.2–§0.3）；复现口径「同日志逐位一致」（§0.4）。
- 观测对象总表（§1.1）与 A–E 各类确定性判定规则（§1.2–§1.6）。
- 核心范式「种子事件→自主传播」定义、传播图构建、度量与「突现成立」判据骨架（§2）。
- 三类对照 + 时间窗规格 + 显著性/稳定性判据 S1–S4 + A/B 差异判定（§3）。
- 叙事 vs 数字分工与隔离机制、F 类落位（§4）。
- 护栏关系、干预标注与剔除方法（含/剔双版本）（§5）。
- 猜想/可证伪清单与六类假象区分方法（§6）。

**待讨论（开放问题）**
- 阈值取值：`ε/ε_strong/ε_rec/W_MIN/W_MAX`（T7 D7-3）、`θ_reach/θ_effect/θ_cap/W_seed/θ_adopt/θ_cov/Q_min/θ_stable`、`z/N_perm`（T10 标定）。
- `T9-C1` 干预标签的标准化落位（T8/T10）；`T9-C2` 关系数值确定性来源（架构 AR-C3 已裁定「必须确定性函数、LLM 只产叙述」，据此对齐）；`T9-C4` `metrics.emergence_soft` 命名空间登记（T8）；`T9-C3` 文档命名（以 `07-` 为准，Leader 汇总时统一）。
- A/B 双胞胎对照在「含 LLM 判定、跨跑不逐位一致」下，F 类指标的对照统计口径——**已裁决【已定】**：F 类只做敏感性、不作判定。

**已裁决转入「已定」（本轮 Leader 拍板）**
- `T9-D1` 社区发现算法：主算法固定种子 + 全序 tie-break 的 Louvain/Leiden，另出连通分量 + k-core 确定性基线，参数/版本入 `engine_version`。
- `T9-D2` 角色：本轮不扩保持 10，`courier/journalist` 列 N=20 跑通后候选。
- `T9-D3` F 类指标：只作敏感性分析，不进判定路径/门禁。

---

*（本文件为 v1.1 涌现观测层设计草案；核心目标：**判定 100% 确定性、可重放、可审计**，LLM 仅描述与（冻结）定性输入，绝不参与判定；把「真实涌现」与「规则/干预/LLM 造成的假象」用确定性手段分开。待讨论项交 Leader 汇总与 T7/T10 标定。）*
