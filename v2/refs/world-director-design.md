# 世界 AI 导演（World Director）设计 · 宏观群体事件 + 世界侧介入 v2

> **【Fork B 时效标注 · 2026-10-12】** 凡本文（§0.3 / §2 / §6 / §7 保底 (c)）以「`replay(log)` 逐位一致」作**验收口径**处，按 Leader Q-12.1 改为「**保留可复算（同日志→同状态）、不判字节 FAIL**」。**单一口径见 `v2/refs/gate-grading.md`，另见 `v2/refs/review-world-director-design.md` R-1。**

> 文档类型：v2 参考设计（模块分解 + 可审计口径 + 验收判据）｜ 作者：narrative-designer（叙事与故事层设计专家）
> 状态：v2 设计稿（供 Leader / sim-engine-stats-architect / 前端消费；显式区分 **【已定】/【待讨论】/【未验证】**）
> 上游依据（不另立口径，只引用）：
> - `v2/refs/story-and-event-engine.md`（T204：故事叙述机 + 事件制造机；**「只给环境，不给结局」原红线**、「观察并叙述 vs 主动制造」分野、Q-8 来源诚实判据）
> - `v1.1/00-architecture.md`（§1.5 底座三角色带、§5.4 复现口径「同日志逐位一致」、§4.1 IF-5/IF-7）
> - `v1.1/08-engine-stats-extension.md`（**事件 schema 权威**：§1.2 事件表、审计事件族 E-AUDIT、`LLM_JUDGMENT`/`NARRATIVE`）
> - `v1.1/12-event-lineage.md`（20 类事件谱系 + D/F/N/R 归属 + 确定性结算）
> - `v2/00-roadmap.md`（§0 A 物理层 / B 制度层 / C 保底；消融证伪纪律）
> - `v2/refs/mihoyo-deck-teardown.md`（§C-1/C-4：米哈游「AI 导演」= 玩家体验导向，实时调叙事节奏与分支走向）
> 产出约束：本文件**只设计，不改 `code/`**；落 `v2/refs/`。

---

## 0. 红线放宽与本设计的立足点

### 0.1 用户本轮拍板（前提，本设计据此展开）

| # | 用户拍板 | 对本设计的含义 |
|---|---|---|
| 1 | 「**我们要有世界 AI 导演**」 | 新增一个**世界层**的主动角色（非单个 Agent），本设计即其职责与机制 |
| 2 | 「**作者化的活世界**比只看涌现更有意义、能看到更多可能性」 | 不再把「只给环境」当唯一解；**允许世界侧主动制造宏观事件** |
| 3 | 「会产生**宏观群体事件**，但**肯定不仅是观察者**」 | Director **可以介入**，不是被动观测器 |
| 4 | 「经济/社会……**可以定义，也可以不被定义，自行涌现**」 | B 层制度**允许两种模式并存**：世界侧可给框架，也可只给底座看涌现 |

### 0.2 先前裁决的放宽与保留

- **放宽**：T204 中我裁定的 **「只给环境，不给结局」原红线**，对**世界层宏观介入**部分**放宽**——世界 AI 导演**可以产生宏观群体事件、可以介入**。
- **保留（不放宽的部分）**：
  - **「观察并叙述」层（Storyteller）仍严格只读**（`NARRATIVE{affects_state=false}`，H-2 不破）；Director **不改叙事层**。
  - **个体层的自主性仍保留**：Director **不替单个 Agent 做选择**（见 §1 判定总则）。
  - **确定性内核仍是唯一写入口**：Director 只能产出**意图/指令**，由内核校验、封装为事件后才影响世界（`00 §1.5`）。

### 0.3 三条保底（**本条是本设计的宪法，必须同时满足**）

> 用户要求：作者化**不能**变成「结果不可查」。故世界 AI 导演每次介入**必须**满足 (a)(b)(c)：

| # | 保底 | 精确含义 | 机器可校验的不变量 |
|---|---|---|---|
| **(a)** | **显式事件（不得隐形手）** | 每一次介入都是一条**可审计事件**，带 `directed=true` 标记 | `count(directed=true 事件) == count(实际介入)`；不存在「无 directed 事件却改变宏观情境」；否则记 `SYSTEM_ERROR` |
| **(b)** | **可消融** | 每个介入机制有**独立开关**与**剂量参数**，可单独关闭做对照 | `Ω = {机制×开关×剂量}` 可配置；关某机制 → 其 `WORLD_GROUP_EVENT` 归零（置换检验）；剂量只缩放强度、不改变「是否可消融」的性质 |
| **(c)** | **不改过去** | 只能对**未来**下情境；**不得直接改写个体已发生的事实**（不能改过去的账） | `directive.effective_from_round ≥ issued_round`；任何试图修改 `< issued_round` 的介入被内核拒绝 → `WORLD_DIRECTIVE_REJECTED`；`replay(log)` 对同日志逐位一致 |

> **一句话**：**世界 AI 导演可以「导演未来」，不可以「篡改过去」，也不能「隐形出手」——每一次出手都必须是一条能被独立复算的、带 `directed` 标记的事件。**

---

## 1. 职责边界与判定总则

### 1.1 三层职责（World Director 在哪一层）

```
┌──────────────────────────────────────────────────────────────────────┐
│ 世界 AI 导演（World Director）—— 世界层                               │
│   管「世界上发生什么宏观情境/群体事件」                                 │
│   产出：WORLD_DIRECTIVE（意图/指令）→ 内核封装 → WORLD_GROUP_EVENT（事实）    │
└───────────────────────────────▲──────────────────────────────────────┘
                                │ 只产出「情境/事件」，不产出「个体选择」
┌───────────────────────────────┴──────────────────────────────────────┐
│ 个体 Agent 的 LLM 决策（人格生活层）—— 个体层                          │
│   管「这个角色自己想做什么、和谁、怎么想」                              │
└───────────────────────────────▲──────────────────────────────────────┘
                                │ 写世界的唯一入口
┌───────────────────────────────┴──────────────────────────────────────┐
│ 确定性内核 / 中央裁决器 —— 世界法则（金额/死亡/胜负/结算）              │
└──────────────────────────────────────────────────────────────────────┘
```

- **个体层**：每个 Agent 的 LLM 决策（计划/对话/关系/目标）——**决定「这个角色做什么」**。
- **世界层（Director）**：**决定「世界上发生什么宏观情境/群体事件」**——如节庆、灾害、政令、外来者、市场波动。
- **内核**：Director 的指令必须经内核**校验**（保底 a/b/c）后封装为事件，才进入世界；**Director 不直接改账本**。

### 1.2 判定总则：什么算「宏观」，什么算「越权插手个体」（【已定】）

> 目标：把"宏观介入（允许）"与"越权插手个体（禁止）"变成**可判定的规则**，而非主观感受。

| 规则 | 宏观（**允许**） | 越权插手个体（**禁止**） |
|---|---|---|
| **R1 作用对象** | 面向**群体/环境/公共条件**（≥K 个 Agent、公共资源、全局状态、某场所/时段） | 面向**单个 Agent 的私密决策、内心、指定对象**（如「让 A 去和 B 结盟」） |
| **R2 粒度** | 设定**情境/条件/事件**（"将有一场丰收节"），**不指定具体行为与结果** | 指定**某个体的具体行为/对象/结果**（"让 A 赢得冲突""让 A 与 B 分手"） |
| **R3 可观测** | 介入必落**一条 `directed` 事件**（可审计） | 隐形手、事后合理化、不可溯源 |
| **R4 时间性** | 只对**未来**下情境（`effective_from_round ≥ 现在`） | 改写**过去**已发生的事实/账目 |
| **R5 数值归属** | Director 只给**情境参数**（规模/时长/强度），**不给**金额/死亡/胜负/结算的具体数值 | 直接产出金额/死亡/胜负等**硬内核数字**（违反 T9 R5） |
| **R6 与个体决策的关系** | 只**改变个体的处境**，个体**仍自主决策**（可无视、可应对） | **替代**个体决策或**强迫**其接受某结果 |

**判定流程（决策树，可机器实现）**：

```
一个 Director 介入是否合规？
  1) 它的作用对象是「处境」（群体/环境/公共条件）还是「个体结果」？（R1）  个体结果 → ❌ 越权
  2) 它是否只给「情境」而不给「某个体的行为与结果」？（R2）                否 → ❌ 越权
  3) 它是否落为一条 directed 事件（可达溯源）？（R3）                      否 → ❌ 隐形手（违保底 a）
  4) 它的 effective_from_round ≥ issued_round？（R4）                      否 → ❌ 篡改过去（违保底 c）
  5) 它是否含金额/死亡/胜负的具体数值？（R5）                              是 → ❌ 越内核（违 R5/T9 R5）
  ── 全部通过 → ✅ 合规宏观介入；否则拒绝并记 WORLD_DIRECTIVE_REJECTED
```

- **K 的定位（Leader 已裁决 WD-D1）**：**K 不作准入条件，只作「审计告警阈值」**（默认 3、可调）。
  - **准入由 R1 判**（作用对象是「处境」还是「个体结果」）；**固定 K 会反过来鼓励"把个体操作包装成 3 人群体"**——想碰线的人会绕过阈值而非被挡住。
  - K 的用途：当 `scope.level=agents` 且规模 `< K` 时**标记"疑似个体化介入"**，触发审计关注（记告警，不直接拒绝）。
- **关键纪律**：**宏观 ≠ 结果**。Director 无「让某角色如何」；只「让世界变成什么样」，然后**看角色怎么应对**。

---

## 2. 世界 AI 导演 vs 米哈游「AI 导演」（**概念差异，必须写清**）

> 依据：`v2/refs/mihoyo-deck-teardown.md` §C-1 对其「AI 导演」的定义——*"一个以玩家体验为中心的 Agent，实时感知玩家动态，在框架内调整叙事节奏和分支走向"*。

| 维度 | 米哈游「AI 导演」 | **我们：世界 AI 导演** |
|---|---|---|
| **导向** | **玩家体验导向**（player-experience-oriented）：服务「玩家的爽感/沉浸」 | **世界层导向**（world-layer-oriented）：服务「世界产生什么宏观事件/情境」 |
| **调的什么** | **叙事节奏与分支走向**（调"故事怎么讲、往哪走"） | **世界的宏观情境**（造"世界上发生什么"，**不调叙事文本**） |
| **时间性** | **实时**感知玩家、实时调 | **事件化、可冻结**：每次介入落 `directed` 事件，**可重放** |
| **对结局的态度** | **可决定分支走向**（干预"往哪走/谁是主角"） | **不决定结局**：只给情境，个体自主应对；**不指定胜负/关系/谁重要** |
| **可复现** | 实时调整 → **不可冻结/重放** | **可复现**：介入 + RNG 先定 → `replay(log)` 逐位一致 |
| **可消融** | —（体验优先，通常不做消融） | **必须可消融**（保底 b），否则「作者化」会污染"是否为涌现"的判断 |
| **与叙事层关系** | 导演**直接调叙事** | 导演**不碰叙事层**；叙事机只读，照常叙述（H-2 不破） |
| **红线** | 与我们**原红线**「只给环境不给结局」正面冲突（`deck-teardown §C-1/C-4`） | **放宽但加保底**：可介入，但受 (a) 显式事件 / (b) 可消融 / (c) 不改过去 约束 |

> **一句话差异**：**他们「导玩家体验」（调叙事节奏与分支）；我们「导世界情境」（造宏观事件，且每次出手都可审计、可消融、不改过去）。** 二者都叫"导演"，但**一个动的是"叙事与结局"，一个动的是"世界的环境与情境"**——后者的介入**不改变事实的可追溯性**，这正是我们区别于"作者化剧情游戏"的地方。

---

## 3. 宏观群体事件清单（逐条判 (a)(b)(c) 合规 + 开关与剂量）

> 判据：**(a) 显式事件**（落 `directed` 事件）、**(b) 可消融**（独立开关 + 剂量参数）、**(c) 不改过去**（只对未来）。另附「**可审计口径**」= 事后如何从日志复算「这是导演干的」。

> ⚠️ **【T216 合并声明】** 本节的 `WD-1..WD-10` 判定表**已与 T204 的 `EF-1..EF-9` 合并**为 `v2/refs/world-event-mechanisms.md`（统一红线 A′）的**单一机制表**。机制判定**以该文件 §2 为准**；本表仅作**历史/溯旧**保留（WD 编号在该文件 `别名` 列可追）。**出现不一致时，以 `world-event-mechanisms.md` 为准。** 本节 §3.1 剂量曲线、§3.2 四项裁决**仍有效**（补充约定，不冲突）。

| # | 宏观群体事件 | 触发（确定性/RNG 先定） | 产出（事件/情境） | (a) | (b) 开关·剂量 | (c) | 可审计口径 |
|---|---|---|---|---|---|---|---|
| **WD-1** | **节庆 / 集市 / 大型活动** | 日历相位 + Director 调度（RNG 先定） | `WORLD_DIRECTIVE`→`WORLD_GROUP_EVENT(kind=festival)`；场所开放、活动概率↑ | ✅ `directed=true` | 开关 `wd.festival.enabled`；剂量：频率（次/周）、规模（容量上限）、时长（slot 数） | ✅ 只影响 `t≥now` | 存在 `WORLD_GROUP_EVENT(directive_ref=…)`，且其 `directive_ref` 溯源到一条 `directed=true` 的 `WORLD_DIRECTIVE` |
| **WD-2** | **灾害 / 气候（环境级）** | RNG 按 `wd.disaster.p_k` 触发 | `WORLD_GROUP_EVENT(kind=disaster)`；`NEED_UPDATE`/`PRODUCE`↓/场所关闭 | ✅ | 开关 `wd.disaster.enabled`；剂量：**强度分级**（轻/中/重）、概率、面积（场所数） | ✅ | 同上；强度写进 `directive.dose` |
| **WD-3** | **政令 / 公共公告** ⚠️ | Director 判断发布（RNG 先定是否发布） | `WORLD_DIRECTIVE(kind=edict)`→`WORLD_GROUP_EVENT(kind=edict)`；改变**公共情境**（如"某场所设为公共集会地""某时段宵禁"） | ✅ | 开关 `wd.edict.enabled`；剂量：范围（place/global）、时长 | ✅ | ⚠️ **合规前提**：政令**只给"公共情境"**，**不得**写死税率/价格/工资（那是 B 层制度，违 §1.2 R5、`v2/00 §0.3`）。**违反 → 拒绝** |
| **WD-4** | **外来者 / 访客** | 经 `gate` 按日历/RNG 注入 | `WORLD_GROUP_EVENT(kind=visitor)`；外来物资上架/新面孔出现 | ✅ | 开关 `wd.visitor.enabled`；剂量：人数、停留时长、携带物资量 | ✅ | 同上；`scope` 记 `gate` |
| **WD-5** | **市场波动（供给冲击）** ⚠️ | RNG 触发丰收/歉收/外来供给 | `WORLD_GROUP_EVENT(kind=supply_shock)`；**改变供给量** | ✅ | 开关 `wd.supply_shock.enabled`；剂量：幅度、持续周数 | ✅ | ⚠️ **合规前提**：只改**供给数量**，**不写死价格**（价格由 B 层市场涌现） |
| **WD-6** | **疫病 / 健康事件** | RNG 按 `wd.epidemic.p` 触发 | `WORLD_GROUP_EVENT(kind=epidemic)`；`NEED_UPDATE(health)`↓、`clinic` 压力↑ | ✅ | 开关 `wd.epidemic.enabled`；剂量：感染范围、强度分级 | ✅ | 同上 |
| **WD-7** | **公共工程 / 资源投放** | Director 判断（RNG 先定） | `WORLD_GROUP_EVENT(kind=public_works)`；公共品需求出现、资源投放 | ✅ | 开关 `wd.public_works.enabled`；剂量：资源量、工期 | ✅ | 同上；**只投放可认领的目标**，不指定谁做 |
| **WD-8** | **紧张升级（stakes 制造）** ⚠️ | Director 提高某公共资源稀缺/时限 | `WORLD_GROUP_EVENT(kind=tension)`；制造"值得争的东西" | ✅ | 开关 `wd.tension.enabled`；剂量：稀缺度、时限 | ✅ | ⚠️ **合规前提**：**只制造 stakes，不指定对手、不指定胜负**（冲突是否发生仍由 Agent 自主；胜负由 T14 §3.2 内核结算）。**指定对手 → 越权（R1/R2）** |
| **WD-9** | **季节 / 世界节律** | 日历纯函数 + RNG | `WORLD_GROUP_EVENT(kind=season)`；环境参数季节性漂移 | ✅ | 开关 `wd.season.enabled`；剂量：季节长度、漂移幅度 | ✅ | 同上 |
| **WD-10** | **外来集体事件（大规模）** 【未验证】 | Director 判断（高剂量） | `WORLD_GROUP_EVENT(kind=mass_event)` | ✅ | 开关 `wd.mass_event.enabled`（默认 **OFF**）；剂量：全局 | ✅ | **剂量最高档，默认关闭**；启用需 Leader 明示；**不做灾难级**（沿用 T204 D-3 的"最小剂量"安全值） |

- **通用条款**：所有 `WORLD_GROUP_EVENT` **只有环境/情境参数**，**无金额/死亡/胜负数值**（R5）；涉及金额/死亡的部分**由内核**从情境 + RNG 确定性推导为独立事件（如 `METABOLISM`/`NEED_UPDATE`/`AGENT_DIED`），**与 Director 指令分列**（对齐 `08 §1.2` 三事件分列）。
- **剂量语义**：剂量 = **强度缩放**（规模/时长/幅度/概率），**不改变机制的"可消融性"**；剂量为 0 ≡ 关闭。

### 3.1 剂量曲线（Leader 建议，【已定】）——「保守 / 中 / 激进」

> **观察"介入强度如何改变世界走向"本身就是用户想看的"更多可能性"**——这是把「作者化」变成**可研究**的关键旋钮，也是我们区别于米哈游的地方（他们只服务体验，我们要能**解释**世界为什么变成那样）。

| 档位 `dose_curve` | 含义 | 典型剂量 | 用途 |
|---|---|---|---|
| `conservative` | 最小剂量（环境级） | 低概率、小规模、短时长 | 默认；两边都成立的安全值（对齐 T204 D-3） |
| `moderate` | 中剂量（可开关档位） | 中概率/规模（**保留**，WD-D4） | 观察"中等扰动"的世界响应 |
| `aggressive` | 灾难级（**默认 OFF**） | 高剂量、全局 | **最强故事发生器**；启用须 Leader 明示；**硬约束**：须能事后**复算该事件对每个 Agent 的影响**（`per_agent_impact_ref`），否则无法归因＝不算可审计 |

- **曲线可消融**：档位是 config 参数，`conservative` 为默认；切档即改世界轨迹（需重跑/重冻）。
- **可研究性**：同一 seed 下扫 `dose_curve` → 得到「介入强度 → 世界走向」的对照曲线，**本身可作为实验结论**。

### 3.2 四项裁决（Leader 2026-10-12，已回写）

| # | 裁决 | 落法 |
|---|---|---|
| **WD-D1** | **K 不作准入条件，只作审计告警阈值**（默认 3、可调） | §1.2 决策树与 §4.2 规则 4 已改为「`< K` → `warn` 告警，非拒绝」；准入由 R1 判 |
| **WD-D2** | **政令只给情境、不写数字** | 可宣布「某事成为公共事务 / 设立某机构 / 征集某物」；**不得写死税率/价格/配额数值**。**补充**：若政令产生**机制性后果**（新机构占场所/改通行），**必须做成可消融的独立开关**（行 WD-3） |
| **WD-D3** | **紧张升级上限 = 不得产生「必然冲突」的结构** | 让资源变紧 ✅；**把两个具体的人锁在同一稀缺品上、并规定先到者得 ❌**（那是替他们写结局）。行 WD-8 已据此收紧 |
| **WD-D4** | **默认不做灾难级；保留「中剂量」可开关档位** | §3.1 剂量曲线；灾难级（`aggressive`）默认 OFF，启用须能事后复算逐 Agent 影响 |


---

## 4. 介入的事件 schema（**需交 `sim-engine-stats-architect` 登记 08，实现前**）

> 本节只**提出建议 schema**；**权威登记在 `08 §1.2`**。实现**前**必须先完成登记（对齐 T204 SE-C1 流程）。

### 4.1 建议新增事件类型

```jsonc
// 世界层「指令」（Director 的意图；由内核校验后封装；directed 恒 true）
WORLD_DIRECTIVE {
  directive_id: str,            // 全局唯一
  // —— v1 事件外壳（统一审计字段，采纳 sim-engine-stats-architect 建议）——
  round: int, phase: int,
  actor: "DIRECTOR",            // ★ 导演来源（若 08 不作 actor 扩展，则退 actor="SYSTEM" 且以 directed=true 判别）
  place: str|None,              // 若可归属场所则填（便于 visible_events()/POV 对齐），全局级为 null
  directed: true,               // ★ 保底 (a)
  // —— 载荷 ——
  mechanism_id: str,            // 对应 §3 的 WD-x（如 "wd.festival"）
  kind: str,                    // festival|disaster|edict|visitor|supply_shock|epidemic|public_works|tension|season|mass_event
  scope: {                      // 作用对象（宏观判定用，§1.2 R1/R2）
    level: "global"|"place"|"group"|"agents",
    place?: str, group_ref?: str,
    agents?: [agent_id]         // level=agents 且 规模<K → 审计告警(非拒绝，WD-D1)
  },
  params: dict,                 // 情境参数（规模/时长/强度等；★ 不得含金额/死亡/胜负数值）
  dose: dict,                   // 剂量（强度缩放，§3 通用条款）
  dose_curve: str,              // ★ 剂量曲线档位：conservative|moderate|aggressive（Leader 建议，§3.1）
  issued_round: int,
  effective_from_round: int,    // ★ 保底 (c)：须 ≥ issued_round
  expires_round: int|None,
  rng_branch: dict,             // ★ RNG 先定（可复算）
  seed_ref: str,                // 溯源：用了哪个 RNG 流/seed
  rationale_ref: str|None,      // 侧存储：Director 的理由文本（N 类，不进判定）
  model: str|None,              // 若理由由 LLM 生成，记模型（审计四要素）
  prev_hash: str, hash: str     // 沿用 v1 事件外壳
}

// 世界层「群体事件」（事实；内核据 DIRECTIVE + RNG 封装）
WORLD_GROUP_EVENT {
  group_event_id: str,
  directive_ref: str,           // ★ 溯源到 WORLD_DIRECTIVE（可审计口径核心）
  // —— v1 事件外壳 ——
  round: int, phase: int, actor: "DIRECTOR", place: str|None, directed: true,
  // —— 载荷 ——
  kind: str,                    // ★ 值域 = §3 的 WD-x kind（与 GROUP_CREATED.kind 不相交，见 §4.3）
  scope: {...},                 // 同上
  params: dict,                 // 实际生效的情境参数
  start_round: int, end_round: int|None,
  affected_scope_count: int,    // 受影响 Agent/场所数（供 c_impact 叙事度量）
  per_agent_impact_ref: str|None, // ★ WD-D4：灾难级开启时，指向可复算的「逐 Agent 影响」侧产物
  prev_hash: str, hash: str
}

// 内核拒绝 / 审计告警（违保底 (c)、越权、或 K 告警时产生）
WORLD_DIRECTIVE_REJECTED {
  directive_id: str,
  round: int, phase: int, actor: "SYSTEM",
  reason: str,                  // "rewrites_past" | "targets_individual" | "contains_hard_kernel_number"
                                // | "invalid_mechanism" | "dose_curve_unknown"
  severity: "reject"|"warn",    // reject=拒绝；warn=审计告警（如 scope 规模 < K，WD-D1）
  prev_hash: str, hash: str
}
```

### 4.2 schema 纪律

1. **`directed: true` 恒真**（保底 a）；`WORLD_DIRECTIVE` 与 `WORLD_GROUP_EVENT` 均带，使"导演介入"可被一次性检索。
2. **`effective_from_round ≥ issued_round` 硬校验**（保底 c）；违者拒绝并记 `WORLD_DIRECTIVE_REJECTED`。
3. **`params`/`dose` 不得含金额/死亡/胜负数值**（R5/T9 R5）；含则拒绝。
4. **`scope.level=agents` 且规模 `< K` 时记审计告警（`severity="warn"`），不直接拒绝**（WD-D1：K 只作告警阈值，准入由 R1 判）。
5. **RNG 先定**：`rng_branch` 由 `(seed, "world_director", round, seq)` 确定；LLM（若参与生成 `rationale`）**不掷骰子**。
6. **三事件分列**（对齐 `08 §1.2`）：`WORLD_DIRECTIVE`（意图）/ `WORLD_GROUP_EVENT`（情境事实）/ 内核硬件事件（金额/死亡…）**互不混写**，以 `directive_ref`/`effect_ref` 关联。
7. **`rationale` 正文入侧存储 + 哈希**，主日志只留 `rationale_ref`（瘦身 + 可审计）。

> **【冲突 WD-C1】**：以上 3 个事件类型**当前不在 `08 §1.2`**，须由 `sim-engine-stats-architect` 登记后方可实现（**现在不做**，实现前必登）。

### 4.3 命名与枚举对齐（**采纳 sim-engine-stats-architect 的落地核查**）

1. **命名去歧义**：原 `GROUP_EVENT` 与既有群组生命周期事件 `GROUP_CREATED/GROUP_JOINED/GROUP_LEFT/GROUP_DISSOLVED`（`08 §1.2`）**高度相似**，故**定名为 `WORLD_GROUP_EVENT`**（明确「世界层群体事件事实」），与 `GROUP_*`（群组成立/成员/解散）**彻底分开**。
2. **`kind` 值域不相交（硬约定）**：
   - `WORLD_GROUP_EVENT.kind ∈ {festival, disaster, edict, visitor, supply_shock, epidemic, public_works, tension, season, mass_event}`（= §3 的 WD-x）。
   - `GROUP_CREATED.kind ∈ {chat, guild, …}`（群组类型）。
   - 二者**枚举互不重叠**；`08` 登记时显式写明 **`WORLD_GROUP_EVENT ≠ GROUP_*`**。
3. **统一审计字段**：三类世界级事件统一带 `round` + `phase` + `actor`（`"DIRECTOR"`，若 08 不作 actor 扩展则退 `"SYSTEM"` 并以 `directed=true` 判别）+ `directed=true`；可归属场所时带 `place`（便于 `visible_events()`/POV 对齐）。
4. **`reason` 枚举**：`WORLD_DIRECTIVE_REJECTED.reason ∈ {rewrites_past, targets_individual, contains_hard_kernel_number, invalid_mechanism, dose_curve_unknown}`；`severity ∈ {reject, warn}`。
5. **登记与实现的边界（不越界）**：`08` 只登记 **schema**；新事件类型须在实现阶段登记 `engine/events.py::EVENT_TYPES` + `replay.apply_event` 确定性折叠器（由实现方负责，交 sim-engine-stats-architect 排期）。

---

## 5. 与故事叙述机的接口（**避免把 `directed` 说成自发**）

> 对接 T204：`v2/refs/story-and-event-engine.md` §3 Q-8（来源诚实）。**Director 制造事件 → 叙述机照常只读叙述**；关键是**忠实标注**。

### 5.1 来源标签扩展（T204 origin 枚举 + `directed`）

T204 的 `StoryAtom.origin ∈ {spontaneous, induced, rescue, frozen_llm}`；本设计**新增 `directed`**（世界 AI 导演介入），并明确：

```
origin 判定优先级：directed > induced > rescue > spontaneous
  - 原子若锚点含 WORLD_DIRECTIVE / WORLD_GROUP_EVENT(directed=true) 的 seq → origin="directed"
  - 原子若锚点含 SEED_EVENT(injected_by=OBSERVER) → origin="induced"
  - 其余 → spontaneous
```

### 5.2 叙述纪律（**Q-8 的强化**）

1. **凡 `origin="directed"` 的原子，渲染时必须显式表述为「世界侧介入/导演安排」**（如"一场由世界推动的丰收节……"），**不得**叙述为"小镇自发"。
2. **硬门扩展**：`story_quality` 新增 **Q-9 `directed_mislabel == 0`**（把 directed 说成自发 = 违规，硬门不通过）；Q-9 与 Q-6/Q-8 同为**发布硬门**。
3. **锚点保留**：`NARRATIVE.source_event_seqs[]` **必须包含** `WORLD_DIRECTIVE` 的 seq，使读者能一键追到"这是导演出手"。
4. **叙事层只读不变**：Director **不直接调叙事**（区别于米哈游 AI 导演，§2）；叙述机仍 `affects_state=false`、`narrative_reads_in_decision==0`（H-2 不破）。

### 5.3 可读性收益

- **正面**：`directed` 事件是**高叙事价值**素材（宏观群体事件天然 `c_impact`/`c_rarity` 高），叙述机可据此产出"世界大事记"。
- **诚实底线**：**读者永远能分辨**「这是镇里自己发生的」还是「这是世界导演推动的」——**这就是保底 (a) 在叙事侧的落地**。

---

## 6. 模块清单（功能边界 + 交付物 + 验收判据 + 依赖）

| 模块 | 功能边界（一句话） | 交付物 | 验收判据 | 依赖 |
|---|---|---|---|---|
| **WD-Core**（导演决策器） | 生成 `WORLD_DIRECTIVE`（意图）——**只给情境、不给个体结果** | 决策器设计 + `wd_policy.json`（规则/阈值） | §1.2 决策树全通过；`WORLD_DIRECTIVE_REJECTED` 可复现；`llm_calls` 仅在 `rationale` 生成处 | `00 §5.4`、`08` |
| **WD-Mech**（宏观事件机制库） | §3 的 WD-1..WD-10 机制（**数据化 config**，加机制不改代码） | `wd_mechanisms.json`（每机制 kind/开关/剂量/参数域） | 每机制 (a)(b)(c) 全合规；剂量=0≡关闭 | `12` 事件谱系、`00 §3` 时间 |
| **WD-Control**（控制面） | 总开关 + 每机制独立开关 + 剂量参数 + **剂量曲线档（保守/中/激进）** | `wd.enabled` + per-mech flags + dose 表 + `dose_curve` | **消融**：关机制→其 `WORLD_GROUP_EVENT` 归零（置换检验）；见 §7 | `v2/00 §0.3` |
| **WD-Audit**（可审计层） | 保证每次介入可溯源、可复算 | 审计查询 `directed_events(log)` + `directive→group_event` 链 | `count(directed) == count(介入)`；`effective_from ≥ issued`；replay 逐位一致 | `08` E-AUDIT |
| **WD-Schema**（事件契约） | 提出并推动 `WORLD_DIRECTIVE`/`WORLD_GROUP_EVENT`/`WORLD_DIRECTIVE_REJECTED` 登记 | schema 提案（**交 sim-engine-stats-architect**） | 登记进 `08 §1.2` 后方可实现 | `08`、WD-C1 |
| **WD-Narr-Bridge**（叙事桥） | 把 `directed` 贯穿到 Storyteller origin 与 Q-9 | origin 扩展 + Q-9 判据 | `directed_mislabel==0`；`NARRATIVE.source_event_seqs` 含 directive seq | T204 文档、`17 §3.3` |

---

## 7. 三条保底的机器可校验判据（**可复算**，总表）

| 保底 | 判据（纯 D，可复算） | 通过线 |
|---|---|---|
| **(a) 显式事件** | ① 每条 `WORLD_GROUP_EVENT` 都有 `directive_ref` 且指向 `directed=true` 的 `WORLD_DIRECTIVE`；② `count(改变宏观情境的事件, 无 directed) == 0` | ① 全覆盖；② **==0** |
| **(b) 可消融** | 关闭机制 m → 其 `WORLD_GROUP_EVENT(kind=m)` 计数相对开启期**显著下降**（置换检验 p≤0.05）；剂量=0 与关闭**等价** | 显著下降 |
| **(c) 不改过去** | ① `∀ DIRECTIVE: effective_from_round ≥ issued_round`；② 无 `WORLD_DIRECTIVE_REJECTED(reason="rewrites_past")` 存活；③ `replay(log)` 逐位一致 | ① 全满足；② **==0**；③ 一致 |

> **【未验证】**：判据 (b) 的**显著性与阈值**、各机制的**剂量默认值**、宏观阈值 **K** 的取值，均需 v2 沙盒实测标定（当前无实现，属设计期判据；落地后回填）。

---

## 8. 已定 / 待讨论 / 未验证 / 冲突

### 8.1 已定（可直接引用/实施）

- **红线放宽的范围**与**三条保底 (a)(b)(c)**（§0.2/§0.3）。
- **职责边界与判定总则**（§1）：三层职责 + R1–R6 + 可机器实现的决策树。
- **与米哈游「AI 导演」的差异**（§2）：他们"导玩家体验/叙事分支"，我们"导世界情境"。
- **宏观群体事件清单 WD-1..WD-10**（§3）：逐条 (a)(b)(c) 判定 + 开关与剂量 + 可审计口径。
- **事件 schema 建议**（§4）：`WORLD_DIRECTIVE`/`WORLD_GROUP_EVENT`/`WORLD_DIRECTIVE_REJECTED`。
- **与叙述机接口**（§5）：origin 扩展 `directed` + Q-9 硬门。
- **模块清单**（§6）与**保底判据**（§7）。

### 8.2 待讨论（交 Leader / 用户）

| # | 议题 | 建议 |
|---|---|---|
| **WD-D1** | ~~宏观阈值 `K` 的取值~~ | **【已裁决 → §3.2】Leader：K 只作审计告警阈值，不作准入** |
| **WD-D2** | ~~WD-3「政令」情境边界~~ | **【已裁决 → §3.2】只给情境、不写数字；机制性后果须独立开关** |
| **WD-D3** | ~~WD-8「紧张升级」强度上限~~ | **【已裁决 → §3.2】不得产生「必然冲突」结构** |
| **WD-D4** | ~~WD-2/WD-10 中/重剂量~~ | **【已裁决 → §3.2/§3.1】默认不做灾难级；保留中剂量档；灾难级须可逐 Agent 复算** |
| **WD-D5** | Director 的 `rationale` 是否用 LLM 生成 | 可用（N 类，侧存储）；**不得**影响判定与 RNG 【待讨论】 |
| **WD-D6** | 剂量曲线三档的**默认与阈值**取值 | `conservative` 为默认；`moderate`/`aggressive` 阈值交沙盒标定【待讨论】 |

### 8.3 未验证（**如实标注，不臆造**）

- 「作者化世界」相对「纯涌现」的**收益量级**未经用户实测（属设计假设）。
- 各机制的**剂量默认值与发生率**、判据 (b) 的**显著性**——**尚无实现**，需实测回填。
- WD-10 大规模外来事件、WD-2 灾害的**沉浸收益 vs 可审计成本**——未测。

### 8.4 冲突 / 待对齐

| # | 事项 | 处置 |
|---|---|---|
| **WD-C1** | `WORLD_DIRECTIVE`/`WORLD_GROUP_EVENT`/`WORLD_DIRECTIVE_REJECTED` **未登记 `08 §1.2`** | **实现前必须先交 sim-engine-stats-architect 登记**；本文件**不**自行改 08 |
| **WD-C2** | 与 T204 原「只给环境，不给结局」**口径差** | 本文件**放宽世界层**（§0.2），**保留**叙述层只读 + 个体自主；T204 文档的 EF-1..EF-9 作为**世界层机制的子集**继续有效 |
| **WD-C3** | 与 `v2/refs/mihoyo-deck-teardown.md` 的「AI 导演」是否采纳 | 本设计**部分借鉴其"世界活跃"目标，拒绝其"实时调分支/决定结局"**（§2）；采纳 = 差异化定位保留 |

---

*（本文件为 v2 世界 AI 导演设计稿：在用户放宽红线后，给出「可介入宏观情境、可产生群体事件」的设计，并用三条保底 (a) 显式事件 / (b) 可消融 / (c) 不改过去 把"作者化"约束在可审计、可复现、可消融的边界内；与米哈游「AI 导演」（玩家体验导向）概念分清；与故事叙述机以 `directed` 标签对接，杜绝"把导演安排说成自发"。— narrative-designer）*
