# 09 · 沙盒与验收方案 v1.1（护栏判据 + 观测判据）

> **【Fork B 时效标注 · 2026-10-12】** 凡本文「可复现性」判据以「逐位/字节相等」作**验收口径**处，按 Leader Q-12.1 改为「**放开"必须可复现"、保留"可被复算"**」——改为「全量日志 + 种子化 + 产物 sha/命令 可追溯」；`replay` 一致性**降为诊断**。**单一口径见 `v2/refs/gate-grading.md`。**

> 归属：sandbox-test-lead（沙盒实验与验收负责人）
> 上游依赖（已读）：`00-architecture.md`（T12，含 r1 N=20）、`08-engine-stats-extension.md`（T8）、`07-emergence-observation.md`（T9）、`06-life-layer.md`（T7）、`13-wellbeing-metrics.md`（T15）
> 已并入：`12-event-lineage.md`（T14，事件谱系 + 活动模板库）
> 状态：**v1.1 定稿（T7/T8/T9/T12/T14/T15 已并入；§7.1 事件表核对已完成）**
> 已定前提（用户拍板）：**单一小镇（五脏俱全）、时间尺度先做「模拟周」、架构以 T12 为准、本轮目标 N=20（先跑通）**，50 降为展望。

---

## 0. 目的、范围与使用方式

- **v1.1 沙盒的角色**：验证 ① **生活世界能长时运转**（不崩、可复现、成本可控）；② **能观测到有意义的涌现**（种子事件可自主传播、可复现、无系统性观测偏差）。二者是 v1.1 放量的前置门禁。
- **与 v1 的根本差异**：v1「通过」= 经济指标达标；v1.1「通过」= **护栏不越界（必要）** + **观测到有意义的涌现（充分）**。经济从「主角」降为「背景条件与护栏」（T12 §1.4、§6.1，AR-C6）。
- **使用方式**：判据给出可量化阈值与判定动作；失败按 §5 回滚；差异表（§6）说明每条 v1 判据的去留。
- 复现入口：`run(seed, config, rounds)`、`replay(log)`、`metrics(log, T)`、`emergence_report(log, T, params)`、`wellbeing_report(log, T, params)`（T8 §5.3、T9 §0、T15 §0）。
- **时间坐标（T12 §3 / T8 §3.1）**：`1 时段 = 3 回合`，`1 日 = 4 时段 = 12 回合`，**`1 周 = 84 回合`**；`ROUNDS_PER_SLOT ≥ 3`（AR-D4）。
- **本轮规模（T16/AR-D5）**：沙盒起步 **N=10**，跑通后升 **N=20（本轮目标）**；35/50 仅展望。

---

## 1. 判据拆分：护栏判据 + 观测判据

### 1.1 健康度护栏判据（必要条件：不越界即「世界未崩」）

沿用 v1 阈值（`04-sandbox-plan.md` §3、`05-v1-proposal.md` §7.4/§7.5）；v1.1 仅作护栏、不追求经济优秀：

| 护栏 | 阈值（沿用 v1） | v1.1 新说明 |
|---|---|---|
| 存活率（自然模式） | 60% ≤ 存活率 ≤ 90% | 死亡为护栏与压力源，须打标剔除；口径沿用 v1 Q2 |
| 基尼 `gini_shifted` | ≤ 0.60 且连续 5 回合变化 < 0.05 | 背景条件 |
| 坏账率 `default_rate_outstanding` | ≤ 5% | — |
| 通胀 `M(t)/M_target` | ∈ [0.90, 1.10] | 口径沿用 v1 Q1 |
| 单回合 LLM 调用数 | **≤ N×0.5**（N=10→5，N=20→10，N=50→25；与 08 §5.5 一致） | **不可沿用 v1 的 8/回合**（AR-C5 / AR-D5） |
| 场所容量/超容拒绝 | N=20 下容量余量复核（T12 AR-D5） | `market 20/plaza 30/hall 40` 按 N 缩放 |
| 可复现性 | `replay(log)` 状态一致；`metrics()`/`emergence_report()`/`wellbeing_report()` 两次字节相等 | 硬门禁（T8 §5/§6、T9 §0.4、T15 §5）。**口径＝「同日志逐位一致」**（AR-C9）：首跑含 LLM 判定，**不保证跨跑一致**；A/B 对照须用 D 类指标 |
| 反作弊 | C1–C10 注入 100% 被标记且不计入 `I_eff` | 硬门禁 |
| 守恒/不变量 | v1 五条 + T8 新增 6 条 + T7 生活层 L1–L8 | 硬门禁 |
| 稳定性 | 无 `SYSTEM_ERROR`、无哈希链断裂、无回滚 | 硬门禁 |

### 1.2 观测判据（充分条件：观测到有意义的涌现）

> 铁律：**判定一律用可从日志确定性重算的指标（D 类），LLM 只用于生成与描述、或（冻结后）作定性输入**（T9 §0.2 R1–R7、T8 §4.10、T15 §0.2）。三类：**D 纯确定性**（判定主力）、**F 含 LLM 冻结判定**（仅敏感性/描述、**不进判定与门禁**）、**K 硬内核**（护栏）。

| 观测判据 | 具体口径 | 阈值（默认，待沙盒回填） |
|---|---|---|
| **有突现（种子级联）** | T9 §2.3 全部满足：`reach_ratio≥θ_reach` ∧ `depth≥2` ∧ `R0≥1.0` ∧ `time_to_spread≤1 周` ∧ A/B 显著 ∧ 配额终止占比 `<θ_cap` | `θ_reach=0.50(N=10)/0.40(N=20+)`；排除 `depth=1` 平凡广播 |
| **可复现** | `emergence_report()`/`wellbeing_report()` 同 `(log,T,params)` 两次字节相等；跨 ≥3 seed 符号检验 S3 一致 | S3：≥3 seed 中 ≥⌈2/3⌉ 同向 |
| **无系统性观测偏差** | `llm_judged_metric_count==0`（`metrics.emergence`/`metrics.wellbeing`）；`narrative_reads_in_decision==0`；`observer_injection_count` 显式记录干预 | 硬门禁（T9 §4、T15 §5） |
| **福祉可观测（T15 §7.1）** | ① `WBV` 可稳定重算；② 至少 **1 类背离现象**（T15 §4.2）可被 D 类指标检出（`divergence_count>0` 或某背离判据成立）；③ `metrics.wellbeing.llm_judged_metric_count==0` | D 类；F 类（W3/W2 互评/W7 meaning）仅长窗重点报告，**不作门禁**（WB-C2） |

「有意义涌现」判定清单 = T9 §1.1 总表（A 关系、B 观点、C 圈层、D 规范、E 职业）+ §2.3 突现成立 + §6.1 预注册现象 H-E1–H-E5 + T15 §4.2 背离现象（富而不乐/地位降而幸福升/经济差而关系意义强/成长停滞）。

---

## 2. 核心场景：种子事件 → 自主传播（Smallville 复刻）

> 唯一人类干预入口 `inject_seed_event → SEED_EVENT`（T12 IF-5、T8 §1.2-F、T9 §2）。

- **范式（T9 §2.1）**：注入**一个** `SEED_EVENT`（默认＝「某 Agent 想在**周末**于 `hall` 办一场活动」，`t0`＝day5 morning，扩散落在 weekend）；随后**零追加干预**。
- **传播图（确定性，来自日志）**：节点＝(event, agent)；边 u→v：`OBSERVATION(observer=v, target_event_seq∈u)` 或 `msg(v).refs` 含 u 的 msg_id；级联＝从 `SEED_EVENT` 在窗口 Δ 内可达子图（T9 §2.1）。
- **可量化观测点**：
  - **传播链**（T9 §2.2 / T8 §4.4）：`cascade_size/depth/breadth/R0/time_to_spread/reach_ratio/path_len_dist`；
  - **关系**（T9 §1.2 / T8 §4.3）：`tie_formation_rate/tie_decay_rate/reciprocity/PageRank(G_rel)/encounter_rate`（阈值 `ε=20`、`ε_strong=50`、值域 `[-100,100]`，T7 §6.2）；
  - **观点/标签**（T9 §1.3 / T8 §4.5）：`freq/share/entropy/HHI/adoption/valence/trend`；
  - **圈层**（T9 §1.4 / T8 §4.6）：`n_communities/Q/size_dist/ARI/isolation_rate`；
  - **规范**（T9 §1.5 / T8 §4.7）：`adoption_success_rate/time_to_adopt/norm_violation_rate/norm_coverage`；
  - **职业/身份**（T9 §1.6 / T8 §4.8）：`transition_matrix/role_entropy/switch_rate`（角色 10 类，T12 §2.5）。
- **对照与显著性（T9 §3）**：三类对照——① 组内基线窗 `B0=[t0−Wb,t0−1]`；② **A/B 双胞胎**（同 seed、B 组去 `SEED_EVENT`）；③ **≥3 seed** 复现。判据 **S1∧S2∧S3∧S4**：S1 噪声带（z=3）、S2 置换检验（`N_perm=1000`、`p≤0.05`、排列种子固定→可复现）、S3 跨 seed 符号检验、S4 观测窗内 `k=2` 连续子窗稳定；A/B `Δ_m≥θ_effect` 且 `p≤0.05`。
- **抗「假象」（T9 §6.3）**：规则内建→消融对照；LLM 污染→D 类复算；观察者干预→A/B + induced/spontaneous 分离；平凡传播→`depth≥2`；算法假象→固定算法+种子；小样本→多 seed+置换检验。

---

## 3. 时间尺度与规模：以「模拟周」为主档 + 月/年升级档

> 用户拍板「先做模拟周」。**关键可行性**：默认参数下首个自然死亡约在第 **65 回合**；**1 周=84 回合 > 65**，故「模拟周」内**死亡动态可观测**（T12 §3.4）。

| 档 | 规模 | 窗口 | 回合数 | 用途 | 成本（见 §4） |
|---|---|---|---|---|---|
| **短窗（主档）** | 10 / **20** | **1–2 周** | 84–168 | 冒烟 + 种子事件传播 + H2 可观测 | N=20：~8×10²–1.7×10³ 调用 |
| **长窗（升级档）** | 10 / **20** | **4–12 周** | 336–1008 | 关系漂移、职业/身份转变、规范形成、圈层演化 | N=20：~3.4×10³–1×10⁴ 调用 |
| （展望） | 35 / 50 | 1–12 周 | 84–1008 | 正式实验 | 线性放大 |

- **建议**：L0 先 **N=10 短窗 1–2 周**验证「能运转 + 能观测」；再升 **N=20** 跑通（本轮目标）；长窗 4–12 周验证长期涌现（长窗须重点报告 F 类福祉指标，WB-C2）。
- **约束 AR-D4**：`ROUNDS_PER_SLOT` 默认 3；若降到 1（1 周=28<65）周内测不到自然死亡，须设「死亡压力档」（§5）。
- **日志/复现（T12 r1 §7.1）**：N=20×12 周压缩 ~8MB、N=50×12 周 ~20MB——**日志非瓶颈，唯一显著成本是 LLM 调用**。
- **可观测性核对（种子范式）**：种子注入 day5，扩散落在 day5–day6（24 回合内）≪ 1 周（84），**周尺度内可完整观测**（T9 §2.3）。

---

## 4. 成本估算（按 T7/T8 新模块重算，N=10 与 N=20 两档）

### 4.1 模型（T12 §7.2 / T8 §5.1 / T7 §9.2）

```
每 Agent 每周 LLM 调用 ≈ (c_life + c_social) · SLOTS_PER_WEEK = (1.0+0.5)×28 ≈ 42 次
  c_life=1.0（计划/活动/反思摊薄）、c_social=0.5；SLOTS_PER_WEEK=28
```
T7 §9.2 逐模块调用点：M2 记忆（importance 批 `B_imp=10` + 嵌入 batch 16 + 反思 `min(触发,R_max=7/周)`）、M4 日程（周计划 1 + 周回顾 1 + 日解析 ≤7，多 T1）、M7 目标（1/周 T2）、M3 印象叙述（≤交互数，可批）、M1 人格（离线，稳态 ≈0）。

### 4.2 沙盒预算（N=10 与 N=20）

| 项 | N=10 | N=20（本轮目标） |
|---|---|---|
| 每周调用 | 42×10 ≈ **4.2×10²/周** | 42×20 ≈ **8.4×10²/周** |
| 每周 token | ≈ 10⁶ | ≈ 2×10⁶ |
| 短窗 1 周 | 4.2×10² | 8.4×10² |
| 短窗 2 周 | 8.4×10² | 1.7×10³ |
| 长窗 4–12 周 | 1.7×10³–5.0×10³ | 3.4×10³–1.0×10⁴ |
| **每回合预算**（折算） | 420/84 ≈ 5 | 840/84 ≈ 10 |

- **硬预算闸（护栏）**：每回合 LLM 调用 `≤ N×0.5`（N=10→5，N=20→10，N=50→25；**与 08 §5.5 重算一致**，由 T7 模块调用点支撑、随 N 线性缩放）；**不得沿用 v1 的 8/回合**（AR-C5/AR-D5），沙盒实测后收紧。
- **成本闸门与降级优先级**（T7 §9.2 / T8 §1.2-G）：超限按 `濒死求生 > 投资/结盟 > 周计划/反思 > 印象叙述/日解析` 降级 T2→T1→T0，写 `LLM_CALL(degraded=true)`。
- **对照**：Agentopia 单世界一年 ≈ 13.7B token/56.7 万次调用/186 小时；v1.1 单周（10⁶–10⁷ token）远低于其年尺度 → 「先模拟周」成本可行。

### 4.3 生活层/观测层的增支与压缩手段

- **增支来源（T7 §9.2）**：M2 记忆（obs 驱动，**最高敏感**）、M4 日程（周计划/回顾/日解析）、M7 目标、M3 印象叙述。
- **观测层成本≈0 LLM**：`metrics.emergence`/`metrics.wellbeing`（D 类）全为确定性图/统计计算；`narrate()` 可选且非权威、不进判定。
- **压缩手段**（T7 §3.6 / T8 §5.2）：① 重要性触发反思（`θ_reflect=150`，`R_max=7/周`）；② 压缩档案进 prompt（人格≤200 + 目标≤100 + 记忆摘要 ≤`M_mem`=800 + 最近 6 条对话）；③ `top_k=8` 上限；④ importance/嵌入批量；⑤ 低信息量 observation 走 T0 规则；⑥ 相遇事件节流（`D_enc=3`）；⑦ 快照节流；⑧ `LLM_BUDGET` 分层降级。

---

## 5. 放量阶梯与回滚（单变量推进）

| 级 | 规模 | 放行条件 | 回滚条件 |
|---|---|---|---|
| **L0** | **10** | §1.1 护栏全过 + **观测判据**（种子级联「成立」，S1–S4 通过，A/B 显著）+ 复现一致 + 福祉背离可检出（D 类） | 命中任一护栏失败信号或突现判据不成立 |
| **L1（本轮目标）** | **20** | L0 通过 + 无新崩溃 + 单回合 LLM 调用 ≤ 2.2×(L0 值) + 多 seed（≥3）突现可复现 + 场所容量余量复核（AR-D5） | 成本超线性/护栏越界/突现不可复现 |
| （展望）L2 | 35 | L1 通过 + 长窗（4 周）稳定 + `metrics()`/`emergence_report()`/`wellbeing_report()` 与离线重算一致 | 任一派生指标发散 |
| （展望）L3 | 50 | L2 通过 + 全部判据在目标规模成立 + 成本在预算内 | 任何失败 |

- **单变量推进**：每级只改规模；**每级至少 3 个 seed**（满足 S3）；每级同跑「种子组（A）/ 对照组（B，去 `SEED_EVENT`）」。
- **死亡压力档**（补偿 AR-D4）：为控成本缩短窗口/降 `ROUNDS_PER_SLOT` 时，并行跑一档（`m`↑ 或 `E0`↓）专测 H2。

---

## 6. 与 v1 沙盒的关系（差异表）

| v1 判据/条目 | v1.1 处置 | 说明 |
|---|---|---|
| 存活率 ∈ [60%,90%] | **改用为护栏** | 死亡降级为压力源，须打标剔除（T12 §1.4） |
| 基尼 `gini_shifted` ≤ 0.60 | **改用为护栏** | 背景条件 |
| 坏账率 ≤ 5%（失败 >10%） | **改用为护栏** | — |
| 通胀 `[0.9,1.1]` | **改用为护栏** | 口径待 v1 Q1 |
| 单回合 LLM 调用 ≤ 8 | **改用为护栏（阈值重算 N×0.5）** | 生活层抬高预算（AR-C5/AR-D5），与 08 §5.5 一致 |
| 消息配额触顶率 ≤ 20% | **改用为护栏** | 传播场景或更易触顶 |
| 反作弊 C1–C10 / 守恒 / 稳定性 | **保留为护栏（硬门禁）** | — |
| 可复现性（首跑=重放、metrics 字节一致） | **保留（硬门禁）+ 扩展** | 增加 `emergence_report()`/`wellbeing_report()` 逐位一致 |
| 「经济表现优秀」为成功标准 | **废弃** | 改为「观测到有意义的涌现」（+ 福祉背离） |
| 「实验成功 = 经济闭环自持」 | **废弃** | 同上 |
| v1「50 回合窗口」 | **废弃 / 调整** | 改为模拟周（84 回合/周），短窗 1–2 周、长窗 4–12 周 |
| v1 两轮制（自然/干预模式） | **保留** | 安全阀冲突（v1 C-16）仍适用 |
| v1 经济/生命周期指标口径 | **保留（冻结）** | 迁 `metrics.econ/.lifecycle`（T8 X3） |

---

## 7. 冲突清单（T7/T8/T9/T12/T14/T15 间自洽性检查）

> 交 Leader 与 design-synthesizer 裁决。每条：编号/级别/事项/出处/建议。

| 编号 | 状态 | 级别 | 事项 | 出处 / 处置 |
|---|---|---|---|---|
| S-C1 | **已关闭** | 中 | `INTENT_REJECTED` 未列入 T8 事件表 | 08 §1.2-H 已登记（确定性拒绝，不产生状态变化） |
| S-C2 | **已一致** | — | 关系维度数值须确定性 | T7 §6.3 已定「确定性函数更新、LLM 只产叙述」，08 §6 不变量(L1)冻结值域 |
| S-C3 | **已关闭** | 高 | 成本预算沿用 v1「≤8/回合」 | 08 §5.5 已按新模块重算；本文件 §1.1/§4 采用 **≤ N×0.5**（见 S-C19） |
| S-C4 | 已一致 | 中 | 记忆 `body` 是否入主日志 | T7 OQ-L5 采纳「侧存储 + 哈希」，与 08 §5.2/XT-3 一致 |
| S-C5 | 待用户 | 中 | 嵌入模型版本是否冻结进 `engine_version` | 08 D7-6 / T7 OQ-L6：均建议冻结 |
| S-C6 | **保留** | 高 | `ROUNDS_PER_SLOT` 降到 1 → 周内测不到死亡 | 00/08 AR-D4：默认 ≥3，否则设死亡压力档（§5） |
| S-C7 | 已一致 | 低 | `slot` 命名与场所营业表 | 00 §2.2/§3.2 与 06 §10 回填一致 |
| S-C8 | 待定 | 低 | 角色是否扩到 12（journalist/courier） | 00 AR-D3 / T9-D2 / T7 OQ-L12：默认 10，数据驱动再提 |
| S-C9 | 待定 | 低 | 是否加 `blackmarket`/`shelter` | 默认不加（00 AR-D1 / T7 OQ-L9） |
| S-C10 | 待用户 | 中 | v1 Q1/Q2/Q7 未裁决，影响护栏与统计口径 | 沿用 v1 同口径（00 AR-C7） |
| S-C11 | **已对齐** | 中 | 干预标签 `rescue_flag/safety_valve_triggered/guardrail_ok` 非 T8 一等事件 | 与 T9-C1 同一事项；命名待 T8/T10 快照派生层统一后彻底对齐 |
| S-C12 | **已关闭** | 中 | `metrics.emergence_soft`/`wellbeing`/`wellbeing_soft` 命名空间未登记 | 08 §4.0 已登记，明确「只作敏感性、**不进判定与门禁**」；本文件 §1.2 门禁判据与此一致（F 类出门禁） |
| S-C13 | 已关闭 | 低 | 文档命名（`10-` vs `07-`） | 统一按实际文件名 `07-emergence-observation.md` 引用 |
| S-C14 | 待定 | 低 | 社区发现算法默认选型（Louvain vs Girvan-Newman） | T9-D1/08 D7-4：T9 建议确定性 Girvan-Newman，Louvain 作对照 |
| S-C15 | **已关闭** | 中 | W6 技能依赖 `SKILL_*` 事件，T8 事件表未含 | 08 §1.2-J 已登记 `SKILL_PRACTICE/SKILL_LEVEL_UP/SKILL_OUTPUT`，命名与 T14 对齐 |
| S-C16 | **已关闭** | 中 | N=20 引发容量与 `LLM_BUDGET` 复核 | 08 §5.5 已按 N 线性缩放重算；本文件 §1.1/§4 同口径 |
| S-C17 | 保留（属标定） | 中 | T7 多项阈值待沙盒标定 | `θ_reflect/R_max/M_mem/D_enc/θ_dep/decay`、日程漂移、importance 批量策略由 T10 标定（T7 §11.2） |
| S-C18 | 已一致 | 低 | T7 生活层不变量 L1–L8 并入 T8 §6 | 08 §6 已并入 L1–L8，冻结值域 |
| **S-C19** | **已解决（记录数值冲突）** | 中 | **LLM 预算口径**：本文件旧稿写 `N×0.6`（N=20→12），08 §5.5 重算为 `≈N×0.5`（N=10→5、N=20→10、N=50→25） | **统一采纳 08 §5.5 的 `≤ N×0.5`**（由 T7 模块调用点支撑、随 N 线性缩放）；本文件 §1.1/§4/§6 已改 |

**结论**：Leader 指出的 5 项（S-C1/S-C2/S-C11/S-C12/S-C15）已按 08 最新版处置（3 关闭、1 一致、1 对齐）；唯一真实数值冲突 S-C19 已收敛到 `≤ N×0.5`。

---

### 7.1 事件表一致性核对（T14 × 08，T17）

> 核对对象：T14 `12-event-lineage.md`（20 类事件谱系 + 20 条活动模板）引用的**全部事件类型** × 08 `08-engine-stats-extension.md` §1.2（A–K）+ v1 事件表。目标：杜绝「模板引用未登记事件」与「登记却无人产生」。

**A. 缺口核对（T14 引用但 08 未登记）**

| # | 事件 | T14 出处 | 08 状态 | 建议 |
|---|---|---|---|---|
| G-1 | `DEPOSIT` / `WITHDRAW` | E5 §1/§2 | 未登记 | **需裁决**：补登（银行存取）或废弃（复用 `TRANSFER`↔银行 SYSTEM 账户）→ 交 T11（T14-C3） |
| G-2 | `GOAL_ABANDON` | E12 §1（`GOAL_SET/ABANDON`） | 未登记（08 §1.2-C 仅 SET/PROGRESS/ACHIEVED） | **需补登**，或改用 `GOAL_SET(status=abandoned)` |
| G-3 | `PROPOSAL` / `VOTE` | E13 §1/§2 | 未登记 | **建议不新增**：复用 `NORM_PROPOSED/ADOPTED`（T14 D14-2 默认复用） |
| G-4 | `LOCATION_SELECTED` | E16 §1/§2 | 未登记 | **建议不新增**：并入 `PLACE_MOVE`（T14 D14-3 默认合并） |
| G-5 | `WELLBEING_ALERT` | E7 §1/§2 | 未登记 | **不新增**（T14-C4 已裁定）：以 `STATE_CHANGE(→exhausted)` 承载 |
| G-6 | `ORDER_PLACE` / `ORDER_CANCEL` | E9 §1 | 未登记（v1 以其为 **intent** `INTENT.ECON.*`） | **无问题**：订单是意图，成交才落 `MARKET_TRADE`（v1 语义） |

**B. 孤立核对（08 登记但 T14 谱系/模板无显式产生者）**

| # | 事件 | 08 出处 | 判断 | 建议 |
|---|---|---|---|---|
| O-1 | `NORM_VIOLATED` | 08 §1.2-F | **疑似遗漏** | T14 无模板产生违规；需明确产生时机（建议：L7 `emit_tags`/规则校验触发）并在 T14 补「违规检测」说明 |
| O-2 | `GOAL_ACHIEVED` | 08 §1.2-C | 疑似弱遗漏 | 由 `GOAL_PROGRESS` 达 1 触发（引擎规则）；建议在 T14 §4.2 模板 `outputs` 补 goal 达成钩子 |
| O-3 | `SCHEDULE_REVISED`、`ACTIVITY_INTERRUPTED` | 08 §1.2-B | 留给引擎 | 计划漂移/中断由 L2/L3 产生；保留 |
| O-4 | v1 经济/生命周期事件（`TRANSFER/MARKET_TRADE/LOAN_*/INTEREST_CHARGED/TAX_LEVIED/UBI_PAID/METABOLISM/PENALTY_APPLIED/REVIVE_FEE_PAID/MONEY_*/STATE_CHANGE/AGENT_DIED/AGENT_REVIVED/INIT_ENDOW/AGENT_BORN`） | v1 表 | 留给经济/生命周期层 | 由 4.1–4.8 钩子产生，非 T14 模板；保留 |
| O-5 | `TIME_MARK`/`LLM_CALL`/`SYSTEM_ERROR`/`DROPPED`/`ECONOMY_INVARIANT_VIOLATION` | 08/v1 | 留给引擎审计 | 保留 |

结论：**真正疑似遗漏仅 O-1（`NORM_VIOLATED`）与 O-2（`GOAL_ACHIEVED`，弱）**；其余为引擎/经济层产生，非「无人产生」。

**C. 命名一致性**

| # | 语义 | 不同命名 | 处置 |
|---|---|---|---|
| N-1 | 协商发起 | T14 `OFFER` vs 08 `OFFER_CREATED` | **需统一** → 采纳 08 `OFFER_CREATED` |
| N-2 | 还价 | T14 `COUNTER_OFFER` vs 08 `OFFER_COUNTERED` | **需统一** → 采纳 08 `OFFER_COUNTERED` |
| N-3 | 排名 | T14 §2 `RANKING` vs 08 `RANKING_EMITTED` | **需统一** → 采纳 08 `RANKING_EMITTED` |
| N-4 | 规则拒绝 vs 社交婉拒 | `INTENT_REJECTED` vs `OFFER_REJECTED` | **已分离**（08 §1.2-K 注 / T14-C5）✓ |
| N-5 | 耗竭告警 | `WELLBEING_ALERT` vs `STATE_CHANGE(exhausted)` | **已裁定**：不用前者，用后者（T14-C4）✓ |

**D. 可执行清单（供 T11 直接采纳）**

- **需补登**：`GOAL_ABANDON`（或改 `GOAL_SET(status=abandoned)`）〔G-2〕；`DEPOSIT`/`WITHDRAW` 由 T11 裁决补登或废弃〔G-1〕。
- **需废弃/不新增**：`PROPOSAL`/`VOTE`（复用 `NORM_*`）〔G-3〕；`LOCATION_SELECTED`（并入 `PLACE_MOVE`）〔G-4〕；`WELLBEING_ALERT`（用 `STATE_CHANGE`）〔G-5〕。
- **需改名（统一到 08）**：`OFFER`→`OFFER_CREATED`、`COUNTER_OFFER`→`OFFER_COUNTERED`、`RANKING`→`RANKING_EMITTED`〔N-1/2/3〕。
- **无问题**：20 类事件主体、`SKILL_*`、`OFFER_ACCEPTED/REJECTED`、`SCORE_POSTED`、`CONFLICT_*`、`NORM_PROPOSED/ADOPTED`、`INTENT_REJECTED` vs `OFFER_REJECTED` 分离、`ORDER_*` 作为意图。
- **需 T14/T8 补说明**：`NORM_VIOLATED` 产生时机〔O-1〕；`GOAL_ACHIEVED` 触发钩子〔O-2〕。

**核对结论**：缺口与孤立项**已逐条列出**——缺口 6 项中 4 项裁决为「不新增/意图」，仅 `DEPOSIT/WITHDRAW`（待 T11）与 `GOAL_ABANDON`（需补登或改 status）为待办；孤立项中真正遗漏仅 `NORM_VIOLATED`（+弱 `GOAL_ACHIEVED`）；命名 3 项需统一到 08。可被 T11 直接采纳。

---

## 附：沙盒执行清单（可直接照跑）

1. 固定 `config`（含 `rule_version`、`personas.json`、`places.json`、`topology.json`，金额 `1 CR=100 mu`）；N=10，seed 取 ≥3。
2. **轮次 1·自然模式**：关安全阀；跑 `run(seed,config,84×W)`（W=1–2 周），记录全部事件。
3. 每回合末跑 `metrics(log,T)`；每窗口跑 `emergence_report` 与 `wellbeing_report`；核对 §1.1/§1.2。
4. 注入 `SEED_EVENT`（A 组）/ 不注入（B 组，同 seed）；按 S1–S4 判定突现是否成立。
5. `replay(log)` + 两次 `metrics()`/报告字节比对：验证复现。
6. 执行 v1 反作弊 C1–C10 注入测试；核对守恒/不变量（含 T7 L1–L8）。
7. 由 `LLM_CALL` 回放标定 `c_life/c_social`、`θ_*`、`Δ/ε` 等（S-C17），核对 §4 成本模型。
8. L0（N=10）全通过 → 升 L1（N=20）跑通；逐级记录放行/回滚。

---

*（定稿 v5 — sandbox-test-lead；已并入 T7/T8/T9/T12/T14/T15 与 N=20 目标；按 08 最新版勘误 §1/§4/§6/§7：S-C1/S-C2/S-C3/S-C11/S-C12/S-C15/S-C16/S-C18 已关闭或对齐，S-C19 预算口径收敛为 `≤N×0.5`；§7.1 事件表一致性核对（T14×08）已完成）*
