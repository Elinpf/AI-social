# 观测台 / 事件流 / 角色详情 —— 信息架构与「游戏化叙事」UX 规格（v1.2）

> 任务：T76-obs-console-ux-spec　｜　作者：visual-researcher　｜　日期：2026-10-10
> 面向：frontend-dev（按此实现 T77）、art-director（导出 `EVENT_STYLE` 常量 + 像素图标）、pixel-asset-artist（出图标资产）、leader
> 硬约束遵守：**只读**——不改前端/engine；本文件仅为**规格**（不写实现代码）。

---

## 0. 摘要与约束吸收

用户诉求三句话：**①要有游戏感；②能知道"发生了什么、以及为什么发生"；③人物背景是什么、做了什么、发表了什么观点。**

现状痛点：审计观测台是**给工程师看的日志**（`#seq + 大写事件名 + JSON payload`），不是**给人看的"小镇故事"**。规格的核心动作是：**把 settle 后的确定性事件，翻译成「谁 · 做了什么 · 为什么 · 结果」的人话卡，并保留一条可下钻到原始事件的审计通道。**

**已吸收 leader/art-director 约束**：
1. **事件四族**：经济 / 生命周期 / 社会 / 认知·生活（§3 裁定并细化，另设"系统·审计"横向类）。
2. **图标口径**：**优先自绘像素图标**（与 `pixel-asset-artist` 资产库同源），**禁用彩色 emoji**（字体依赖 + 与像素风冲突）；退化方案为**单色符号**。
3. **角色卡**：放**右侧抽屉**（与"审计抽屉"同位置切换），从**地图角色 或 事件流里的名字**点开的是**同一张卡**。
4. 给出**可被前端直接 import 的常量**：`EVENT_STYLE`（图标/颜色/族/层级）等（§7），art-director 导出为 JS 常量。

**数据基础（权威，已核对）**：事件类型以 `engine/events.py::EVENT_TYPES`（66 个）为准；字段与真实样例以实跑日志（`v1.2/e2e_n10_week.jsonl` 等）为准；人格字段以 `code/frontend/data/personas.json`（20 位）为准。

---

## 1. 调研：同类游戏的"游戏化叙事"范式（附来源 URL）

| 游戏 | 做法（可借鉴点） | 来源 |
|---|---|---|
| **RimWorld** | **「事件信札(letter)」+ 可折叠日志**：重大事件用带图标/标题/一段人话的信札弹出，日志按类别（威胁/社交/健康）分组；**人物面板**含 traits/关系/健康/心情。核心是"**图标 + 一句人话 + 可展开因果**"。 | RimWorld Wiki — Social: https://rimworldwiki.com/wiki/Social ｜ 入口 https://rimworldwiki.com/ |
| **Crusader Kings 3** | **事件弹窗 = 一张卡**：大插图 + 标题 + 2–3 段选项，每个选项**明示后果**；**角色卡**有 3D 立绘 + traits + 关系（友好/敌对/血亲）+ 头衔；**因果链**通过"事件 → 选项 → 结果"显式表达。 | CK3 Wiki — Character: https://ck3.paradoxwikis.com/Character ｜ 入口 https://ck3.paradoxwikis.com/ |
| **The Sims** | **需求条(Needs) + 情绪(Mood)**：六维需求用**图标 + 条形**，随时可见；情绪由需求/事件驱动的**状态图标**表达；**关系面板**用双箭头（好感/浪漫）。核心是"**把内部状态可视化**"。 | The Sims Wiki — Needs: https://sims.fandom.com/wiki/Needs |
| **Dwarf Fortress — Legends** | **"传说"叙事学**：把世界史拆成**可点选的人物/事件条目**，每条给"谁在哪年做了什么、与谁有关联"，并**可追索关联人物/事件**（超链接式因果）。核心是"**从日志抽取可读传说 + 可追索**"。 | Dwarf Fortress Wiki — Legends: https://dwarffortresswiki.org/index.php/Legends |
| **Stellaris** | **事件弹窗分色调**（不同事件族不同配色/边框），**事件链(event chain)** 把相关的多个事件归为一条主线；调查/异常有**进度与结果卡**。核心是"**事件链 + 配色区分族**"。 | Stellaris Wiki — Events: https://stellaris.paradoxwikis.com/Events |

> 诚实说明：RimWorld / The Sims 页面本次抓取超时、CK3 站点返回反爬挑战，URL 为**官方 wiki 入口**（长期有效），内容为通用性陈述；DF Legends 页面已实际抓取成功。

**提炼为 5 条设计原则**：
- **P1 人话优先**：默认视图是一句"人话"，原始 JSON 藏进"审计模式"。
- **P2 一事件一卡**：图标 + 颜色(族) + 一句主体 + 右侧可展开"为什么/结果"。
- **P3 因果可追**：`cause_event_seq` / `reason` / `goal_id` 等变成**可点击的因果链接**。
- **P4 状态可视**：需求/情绪/关系/金钱用**条形 + 图标**（The Sims）。
- **P5 人物中心**：同一张**角色卡**串起"背景→行为→观点→因果"（CK3/Dwarf Fortress）。

---

## 2. 信息架构：三层 + 导航

```
┌ L1 小镇·上帝视角（地图主舞台） ──────────────── [右抽屉切换] ─┐
│  · PixiJS 地图（场所/角色/道路）                              │
│  · 悬停角色→轻提示(名字/状态/1条最近行为)                     │  ┌ 右抽屉(与审计同位) ┐
│  · 点击角色/场所 → 打开右抽屉的「角色卡 / 场所卡」            │  │ 角色卡 或 审计台   │
│  · 顶部：时间/回合条 + 关键事件 Toast（"P007 去世了"等）      │  └────────────────────┘
└──────────────────────────────────────────────────────────────┘
                          ↓ 点击"事件流" / 底部条
┌ L2 事件流（小镇编年史，人话卡列表） ─────────────────────────┐
│  筛选：[族 经济|生命周期|社会|认知] [场所▾] [人物▾] [仅重大]  │
│        [搜索 🔍] [回合滑杆联动]                               │
│  每行：图标 | 人话句（可点名字/场所） | 回合/时刻 | ⌄因果      │
│  ⌄展开：为什么(reason/cause/goal/need) + 结果 + [审计原始]    │
└──────────────────────────────────────────────────────────────┘
                          ↓ 点"人名"
┌ L3 角色卡（右抽屉） ─────────────────────────────────────────┐
│  头像+名字+年龄+职业 | 生死徽章 | 金钱/负债                   │
│  需求条(6) | 情绪 | 关系(可点) | 技能                          │
│  人格背景(background) | 目标 | 最近行为(时间线) | MSG观点     │
│  记忆/反思要点 | [因果时间线]（事实/推断分色）                │
└──────────────────────────────────────────────────────────────┘
```

**交互规则**
- **导航**：地图 ↔ 事件流 ↔ 角色卡 三者**互链**：地图点人→角色卡；事件流点名字→角色卡；角色卡点事件→定位事件流该行；角色卡点关系人→切换角色卡。
- **悬停**：地图悬停角色显示极简卡（名字/状态/最近 1 条行为）；悬停事件行显示完整人话。
- **筛选/搜索**：按**族 / 场所 / 人物 / 回合区间 / 仅重大(叙事级)**；搜索匹配人话文本 + 人名 + 场所名。
- **审计模式开关**：默认关闭（人话模式）；开启后事件行可展开**原始 payload/seq/hash**（保留工程师可审计性）。
- **时间联动**：回合滑杆与事件流、角色卡"最近行为"同步；拖动即重算（这是确定性回放，天然可复现）。

---

## 3. 事件四族裁定 + 事件流人话化映射表

**族（family）与配色**（色值见 §7）：
- **ECON 经济**（金 `#E8B84B`）｜**LIFE 生命周期**（生绿 `#6FCF6B`/死红 `#D9534F`/复活蓝 `#7EC8FF`）｜**SOCIAL 社会**（紫粉 `#B07CE8`）｜**COGN 认知·生活**（青蓝 `#5CC8FF`）｜**SYS 系统·审计**（灰 `#8B98AB`，默认折叠/审计模式）。

**显示层级（level）**：`narrative` 叙事级（默认显示，用户"发生了什么"）｜`detail` 明细级（默认折叠，展开看）｜`audit` 审计级（仅在审计模式显示）。

> **"为什么"字段标注**：✅reason / ✅cause / ✅cause_event_seq（因果链接） / ✅goal_id / ✅need(dim) / ✅relation(from-to-dim) / ✅decision+dimension(LLM_JUDGMENT) / ✅flag。

### 3.1 经济族 ECON（金）
| 事件 | 层级 | 人话模板（{...}取 payload） | 图标(key) | 为什么字段 |
|---|---|---|---|---|
| `MONEY_MINTED` | audit | 系统注入了 {amount} mu（{reason}） | `mint` | ✅reason |
| `INIT_ENDOW` | detail | {agent_id} 出生获得初始资金 {amount} mu | `coin-init` | — |
| `TRANSFER` | narrative | **{from} 给 {to} {amount} mu**（{reason}） | `coin-arrow` | ✅reason, flags |
| `MARKET_TRADE` | narrative | **{buyer} 在市场买了 {qty} 件（{unit_price}mu/件，共 {amount}）**（{reason}） | `shop` | ✅reason, scarcity_index, flags |
| `DEPOSIT` | detail | {agent_id} 存入银行 {amount} mu（{reason}） | `bank-in` | ✅reason |
| `WITHDRAW` | detail | {agent_id} 从银行取出 {amount} mu | `bank-out` | — |
| `LOAN_ISSUED` | narrative | **{borrower} 借到一笔贷款 {principal} mu（利率 {rate_bp/100}%，到期 round {due_round}）**（{reason}） | `loan` | ✅reason |
| `LOAN_REPAY` | detail | {borrower} 还了 {amount} mu | `loan-repay` | — |
| `INTEREST_CHARGED` | detail | {borrower} 被计息 {amount} mu（{rate_bp/100}%） | `percent` | overdue |
| `LOAN_DEFAULT` | narrative | **{borrower} 违约，欠款 {outstanding} mu** | `loan-broken` | ✅(outstanding) |
| `TAX_LEVIED` | narrative | **{agent_id} 缴税 {amount} mu（{kind}，{reason}）** | `tax` | ✅reason, kind |
| `UBI_PAID` | narrative | **{agent_id} 领到全民基本收入 {amount} mu** | `gift-ubi` | — |
| `PENALTY_APPLIED` | narrative | **{agent_id} 被罚 {amount} mu（{reason}）** | `gavel` | ✅reason, kind |
| `REVIVE_FEE_PAID` | narrative | **{agent_id} 支付复活费 {amount} mu** | `revive-fee` | — |
| `DROPPED` | detail | 一笔 {amount} mu 转账失败（{reason}） | `drop` | ✅reason |
| `MONEY_BURNED` | audit | 系统销毁 {amount} mu（{reason}） | `burn` | ✅reason |

### 3.2 生命周期族 LIFE
| 事件 | 层级 | 人话模板 | 图标 | 为什么字段 |
|---|---|---|---|---|
| `WORLD_INIT` | audit | 世界初始化（seed={seed}） | `world` | — |
| `AGENT_BORN` | narrative | **{agent_id} 在 {home_place} 出生** | `born` | — |
| `METABOLISM` | detail | {agent_id} 本回合代谢消耗 {amount} mu（流动性 {liquid}） | `metabolism` | ✅flag, count_c |
| `STATE_CHANGE` | narrative | **{agent_id} 状态：{from} → {to}**（{cause}） | `state` | ✅cause |
| `AGENT_DIED` | narrative | **☠ {agent_id} 去世了**（原因：{cause}，流动性仅 {liquid}） | `skull` | ✅cause ✅from |
| `AGENT_REVIVED` | narrative | **✦ {agent_id} 复活了**（{via}，代价 {cost} mu，冻结 {freeze_rounds} 回合） | `revive` | ✅via |
| `ECONOMY_INVARIANT_VIOLATION` | audit | ⚠ 经济不变量被破坏：{...} | `alert` | — |

> `AGENT_DIED.cause`（如 `illiquid_no_credit_N`）是**死亡"为什么"的关键**，详见 §5 因果。

### 3.3 社会族 SOCIAL（紫粉）
| 事件 | 层级 | 人话模板 | 图标 | 为什么 |
|---|---|---|---|---|
| `MSG_PUBLIC` | narrative | **{from} 公开说：「{body}」** | `speech-public` | — |
| `MSG_DM` | narrative | **{from} 私信 {to}：「{body}」** | `speech-dm` | — |
| `MSG_GROUP` | narrative | {from} 在群里说：「{body}」 | `speech-group` | — |
| `RELATION_CHANGE` | narrative | **{from} 对 {to} 的{dim} {before→after}**（{cause}） | `relation` | ✅cause, ✅cause_event_seq |
| `RELATION_ENCOUNTER` | detail | {a} 与 {b} 在 {place} 相遇 | `meet` | — |
| `NORM_PROPOSED` | narrative | **{proposer} 提议一条新规范（{norm_id}）**，支持 {support_count} 人 | `norm-new` | support_count |
| `NORM_ADOPTED` | narrative | **规范 {norm_id} 被采纳**（{adopters}） | `norm-ok` | ✅adopted_day |
| `NORM_VIOLATED` | narrative | ⚠ 有人违反了规范 {norm_id} | `norm-bad` | — |
| `OFFER_CREATED` | narrative | **{from} 向 {to} 发起{kind}请求**（{terms}） | `offer` | terms |
| `OFFER_ACCEPTED` | narrative | {by} 接受了请求 {offer_id} | `offer-ok` | — |
| `OFFER_REJECTED` | narrative | {by} 拒绝了请求 {offer_id}（{reason}） | `offer-no` | ✅reason |
| `OFFER_COUNTERED` | detail | {by} 还价：新条件 {new_terms} | `offer-alt` | — |
| `OFFER_EXPIRED` | detail | 请求 {offer_id} 过期 | `offer-exp` | — |
| `CONFLICT_STARTED` | narrative | **{parties} 起冲突**（起因 {rule_ref}，赌注 {stakes}） | `clash` | ✅stakes/rule_ref |
| `CONFLICT_RESOLVED` | narrative | **冲突结束，{winner} 胜出**（{rule_ref}） | `clash-ok` | ✅winner/rule_ref |
| `GROUP_CREATED/JOINED/LEFT` | narrative/detail | {agent_id} {创建/加入/离开}了群体 | `group` | — |
| `ROLE_CHANGE` | narrative | **{agent_id} 身份从 {from_role} 变为 {to_role}**（{cause}） | `role` | ✅cause |
| `TAG_EMITTED` | detail | {agent_id} 被贴了标签「{tag}」（valence {valence}） | `tag` | ✅valence |

### 3.4 认知·生活族 COGN（青蓝）
| 事件 | 层级 | 人话模板 | 图标 | 为什么 |
|---|---|---|---|---|
| `PLACE_MOVE` | narrative | **{agent_id} 从 {from_place} 前往 {to_place}**（{travel_ticks} tick） | `walk` | — |
| `PLACE_ARRIVED` | detail | {agent_id} 到达 {place} | `pin` | — |
| `SCHEDULE_PLANNED` | detail | {agent_id} 制定了本周计划 | `calendar` | — |
| `SCHEDULE_REVISED` | detail | {agent_id} 调整了计划 | `calendar-edit` | ✅reason(如有) |
| `ACTIVITY_STARTED` | narrative | **{agent_id} 在 {place} 开始{activity_type}**（{participants}） | `act-play` | — |
| `ACTIVITY_COMPLETED` | detail | {agent_id} 完成{activity_type}（结果 {outcome}） | `act-done` | ✅outcome |
| `ACTIVITY_INTERRUPTED` | detail | {agent_id} 的{activity_type}被打断 | `act-stop` | ✅reason |
| `NEED_UPDATE` | detail | {agent_id} 的{dim}：{before}→{after}（{cause}） | `need` | ✅cause |
| `GOAL_SET` | narrative | **{agent_id} 立下目标：{description_ref}**（{kind}/{layer}） | `goal` | ✅kind/layer |
| `GOAL_PROGRESS` | detail | 目标 {goal_id} 进度 {before}→{after} | `goal-bar` | ✅goal_id |
| `GOAL_ACHIEVED` | narrative | **{agent_id} 达成了目标 {goal_id}** | `goal-ok` | ✅goal_id |
| `GOAL_ABANDON` | detail | {agent_id} 放弃了目标 {goal_id} | `goal-x` | ✅goal_id |
| `MEMORY_WRITE` | audit | {agent_id} 写入记忆（{kind}，重要性 {importance}） | `mem` | source_event_seq |
| `MEMORY_RETRIEVE` | audit | {agent_id} 检索了 {top_k} 条记忆 | `mem-search` | — |
| `MEMORY_REFLECT` | narrative | **{agent_id} 陷入了反思**（由 {triggered_by_mem_ids} 触发） | `reflect` | triggered_by |
| `OBSERVATION` | audit | {observer} 观察到事件 #{target_event_seq} | `eye` | ✅target_event_seq |
| `SEED_EVENT` | narrative | 🌱 种子事件：{...} | `seed` | — |
| `SKILL_PRACTICE` | detail | {agent_id} 练习了 {skill_id} | `skill` | — |
| `SKILL_LEVEL_UP` | narrative | **{agent_id} 的 {skill_id} 升到 {level_after} 级**（{cause}） | `skill-up` | ✅cause |
| `SKILL_OUTPUT` | detail | {agent_id} 产出了 {skill_id} 成果（质量 {quality}） | `craft` | — |
| `SCORE_POSTED`/`RANKING_EMITTED` | narrative | **比赛 {contest_id} 名次公布：{winner} 第一** | `trophy` | — |

### 3.5 软判定 / 叙事 / 系统（SYS + 专项）
| 事件 | 层级 | 人话模板 | 图标 | 为什么 |
|---|---|---|---|---|
| `LLM_JUDGMENT` | detail | 裁决（{dimension}）：{decision} | `judge` | ✅decision/✅dimension/envelope |
| `NARRATIVE` | narrative | 📖 {pov} 视角小记（见 `body_ref`） | `book` | fact_event_seqs ✅ |
| `LLM_CALL` | audit | LLM 调用（{provider}/{model}，tier {tier}） | `cpu` | — |
| `TIME_MARK` | audit | 时间：第{day}日 {slot} | `clock` | — |
| `TURN_SEAL` | audit | 回合封条 #{round}（state_hash …） | `seal` | — |
| `INTENT_REJECTED` | detail | ⚠ {agent_id} 的意图被拒（{intent_class}：{reason}） | `reject` | ✅reason |
| `SYSTEM_ERROR` | narrative(警示) | ⚠ 系统错误：{...} | `error` | — |

> 规则：**叙事级**进"编年史"默认视图；**明细级**默认折叠、展开即见；**审计级**仅在"审计模式"显示——既给人话，又不丢可审计性。

---

## 4. 角色卡设计（右抽屉，与审计台切换）

**数据源**：`personas.json`（静态人格）+ 运行日志（动态）。

| 区块 | 字段 | 来源 |
|---|---|---|
| **头部** | 头像（像素立绘）、`display_name`、`age`、`role_id`、`home_place`、**生死徽章**（alive/dead/frozen） | personas + `STATE_CHANGE/AGENT_DIED/REVIVED` |
| **金钱/负债** | 现金、存款、负债(`LOAN_*`)、净值 | `TRANSFER/DEPOSIT/LOAN_*` 折叠 |
| **需求条(6)** | energy/satiety/social/esteem/mastery/leisure（条形+图标，The Sims 式） | `NEED_UPDATE`（最新值） |
| **情绪** | 由需求+近期事件推得的情绪图标（如 满足/焦虑/悲痛） | 规则推断（§5 标"推断"） |
| **关系** | 对他人 affinity/trust（可点→切换角色卡） | `RELATION_CHANGE` |
| **技能** | skills[] 等级 | `SKILL_LEVEL_UP` |
| **人格背景** | `background`、Big5、values、`speech_style` | personas |
| **目标** | 当前目标 goal_tendencies + `GOAL_SET/ACHIEVED` | personas + 日志 |
| **最近行为** | 时间线（PLACE_MOVE/ACTIVITY_STARTED/…，最近 N 条） | 日志 |
| **发表的** | 最近 **MSG_PUBLIC/DM/GROUP 的 `body` 原文**（观点/言论） | `MSG_*` |
| **记忆/反思** | 高重要性 `MEMORY_WRITE` 摘要 + `MEMORY_REFLECT` 要点 | `MEMORY_*` |
| **因果时间线** | 关键节点（含死亡/复活原因链），事实/推断分色 | §5 |

**同一张卡**：地图点角色、事件流点名字、角色列表 → 都渲染**同一个 React/组件**（同一数据契约）。

---

## 5. 「为什么」的表达：因果链 + 事实 vs 推断

**三条因果表达能力**
1. **显式因果字段（事实）**：直接读事件自身的 `reason` / `cause` / `cause_event_seq` / `goal_id` / `need(dim)` / `decision`。→ **可点击跳到被引用的 seq/事件**（Dwarf Fortress 式可追索）。
2. **回归因果链（事实）**：把 `cause_event_seq` / `source_event_seq` / `target_event_seq` / `fact_event_seqs` 串成**扑克牌式链条**，例如：
   `NEED_UPDATE(energy↓) → ACTIVITY_STARTED(work) → METABOLISM(流动性↓) → LOAN_ISSUED(续命贷) → LOAN_DEFAULT → AGENT_DIED(cause=illiquid_no_credit_N)`。
3. **可推原因（推断，需显式标注）**：当字段不足以直接给出"为什么"时，用**确定性规则**在 UI 上生成一句"推断"，例如「**流动性不足且借不到贷 → 判死**」。这类文案**必须打「推断」标记**（不同底色/虚线下划线），与**事实**（来自日志字段）**视觉区分**。

**事实 / 推断 的视觉区分（硬要求）**
- **事实**：实心图标 + 常规字重 + 可点跳源事件；标注 `来源: #seq`。
- **推断**：虚线边框/浅底 + 前缀「**推测**：」+ 灰字；不可点击跳转（无源 seq）。
- 规则示例（推断，写死在前端常量里，可由 obs 口径复核）：
  - `illiquid_no_credit_*` → 「流动性枯竭，且信贷不可得 → 死亡」
  - `negative_net_worth` 惩罚 → 「净值转负触发惩罚」
  - `copresence` 关系上升 → 「因同处一地，好感提升」

---

## 6. 游戏感：视觉语言与文案风格

**视觉语言**
- **地图为舞台**：默认全屏地图（已在 T67 落地），观测台是**可开合的抽屉**，不抢地图。
- **图标**：**自绘像素图标**（24/32px，与像素风同源），每族一色系；**禁用 emoji**（退化=单色符号）。
- **配色**：族色（§3/§7）+ 语义色（生=绿/死=红/复活=蓝/警告=橙红）；保持与地图调色板一致（见 T69 风格指南）。
- **动效**：事件发生 → 地图上角色**轻微跳动 + 一圈脉冲**；重大事件（死/复活/升职）→ 顶部**Toast 信札**滑入（RimWorld 式），3s 后收进事件流；因果链在角色卡里**逐条点亮**。
- **弹窗（信札）**：仅用于**重大事件**（AGENT_DIED/REVIVED/GOAL_ACHIEVED/冲突结果/规范采纳），样式=小卡片：图标 + 标题句 + 一句"为什么" + [查看角色卡][查看因果]。
- **密度**：默认只显示**叙事级**；明细折叠；审计默认隐藏。

**文案风格**
- **第三人称"小镇编年史"**：客观、温暖、克制；句式「**谁 · 在哪 · 做了什么 · 因为什么 · 结果**」。
- **用名字不用 id**：`P003` → `青溪镇·老周`（`display_name`）；无名字时退回 id。
- **数字带单位**：`100` → `100 mu`；利率 `rate_bp/100` 转百分比。
- **观点原样引用**：MSG 的 `body` 用「」引号原样呈现，不改写（防幻觉）。
- **禁忌**：不新增日志无据的事实（与叙事层"防幻觉"一致）；推断必须标注。

---

## 7. 可被前端直接用的常量建议（供 art-director 导出 JS）

```js
// EVENT_STYLE: 事件类型 → 样式元数据（图标为 pixel-asset-artist 的资产 key）
// family: ECON|LIFE|SOCIAL|COGN|SYS ; level: narrative|detail|audit
export const FAMILY_COLOR = {
  ECON:  "#E8B84B", LIFE:  "#6FCF6B", SOCIAL:"#B07CE8",
  COGN:  "#5CC8FF", SYS:   "#8B98AB", WARN:  "#E4572E",
};
export const SEMANTIC_COLOR = { born:"#6FCF6B", died:"#D9534F", revived:"#7EC8FF", warn:"#E4572E" };

export const EVENT_STYLE = {
  TRANSFER:      { family:"ECON",  icon:"coin-arrow",  level:"narrative", color:FAMILY_COLOR.ECON },
  MARKET_TRADE:  { family:"ECON",  icon:"shop",        level:"narrative", color:FAMILY_COLOR.ECON },
  LOAN_ISSUED:   { family:"ECON",  icon:"loan",        level:"narrative", color:FAMILY_COLOR.ECON },
  LOAN_DEFAULT:  { family:"ECON",  icon:"loan-broken", level:"narrative", color:SEMANTIC_COLOR.warn },
  TAX_LEVIED:    { family:"ECON",  icon:"tax",         level:"narrative", color:FAMILY_COLOR.ECON },
  UBI_PAID:      { family:"ECON",  icon:"gift-ubi",    level:"narrative", color:FAMILY_COLOR.ECON },
  AGENT_BORN:    { family:"LIFE",  icon:"born",        level:"narrative", color:SEMANTIC_COLOR.born },
  AGENT_DIED:    { family:"LIFE",  icon:"skull",       level:"narrative", color:SEMANTIC_COLOR.died },
  AGENT_REVIVED: { family:"LIFE",  icon:"revive",      level:"narrative", color:SEMANTIC_COLOR.revived },
  STATE_CHANGE:  { family:"LIFE",  icon:"state",       level:"narrative", color:FAMILY_COLOR.LIFE },
  MSG_PUBLIC:    { family:"SOCIAL",icon:"speech-public",level:"narrative",color:FAMILY_COLOR.SOCIAL },
  MSG_DM:        { family:"SOCIAL",icon:"speech-dm",   level:"narrative", color:FAMILY_COLOR.SOCIAL },
  RELATION_CHANGE:{family:"SOCIAL",icon:"relation",    level:"narrative", color:FAMILY_COLOR.SOCIAL },
  OFFER_CREATED: { family:"SOCIAL",icon:"offer",       level:"narrative", color:FAMILY_COLOR.SOCIAL },
  CONFLICT_STARTED:{family:"SOCIAL",icon:"clash",      level:"narrative", color:SEMANTIC_COLOR.warn },
  PLACE_MOVE:    { family:"COGN",  icon:"walk",        level:"narrative", color:FAMILY_COLOR.COGN },
  ACTIVITY_STARTED:{family:"COGN", icon:"act-play",    level:"narrative", color:FAMILY_COLOR.COGN },
  GOAL_SET:      { family:"COGN",  icon:"goal",        level:"narrative", color:FAMILY_COLOR.COGN },
  GOAL_ACHIEVED: { family:"COGN",  icon:"goal-ok",     level:"narrative", color:FAMILY_COLOR.COGN },
  NEED_UPDATE:   { family:"COGN",  icon:"need",        level:"detail",    color:FAMILY_COLOR.COGN },
  MEMORY_REFLECT:{ family:"COGN",  icon:"reflect",     level:"narrative", color:FAMILY_COLOR.COGN },
  LLM_JUDGMENT:  { family:"SYS",   icon:"judge",       level:"detail",    color:FAMILY_COLOR.SYS },
  NARRATIVE:     { family:"SYS",   icon:"book",        level:"narrative", color:FAMILY_COLOR.SYS },
  LLM_CALL:      { family:"SYS",   icon:"cpu",         level:"audit",     color:FAMILY_COLOR.SYS },
  TURN_SEAL:     { family:"SYS",   icon:"seal",        level:"audit",     color:FAMILY_COLOR.SYS },
  INTENT_REJECTED:{family:"SYS",   icon:"reject",      level:"detail",    color:SEMANTIC_COLOR.warn },
};
// 图标资产 key → pixel-asset-artist 的接触表；缺图时前端退化为"族色圆点 + 首字母"
```

**人话模板常量**建议：`EVENT_TEMPLATE[type] = (p) => \`...\``（模板见 §3；占位符直接映射 payload 字段；不可用字段留空而非报错）。

---

## 8. 交接
- **frontend-dev（T77）**：按 §2 三层 IA + §3 映射表 + §7 常量实现；默认"人话模式"，保留"审计模式"开关；因果链接跳 `seq`。
- **art-director**：把 §7 `EVENT_STYLE`/`FAMILY_COLOR` 导出为 JS 常量；确认像素图标清单。
- **pixel-asset-artist**：按 §3 的 icon key 出**24/32px 单色/族色像素图标**（禁用 emoji）。
- **leader**：§0/§5 的事实 vs 推断、§3 的层级口径可转用户对齐。

## 附：来源
- Dwarf Fortress Wiki — Legends：https://dwarffortresswiki.org/index.php/Legends ✓（已抓取）
- RimWorld Wiki（Social/日志范式）：https://rimworldwiki.com/wiki/Social
- Crusader Kings 3 Wiki（Character/事件）：https://ck3.paradoxwikis.com/Character
- The Sims Wiki（Needs）：https://sims.fandom.com/wiki/Needs
- Stellaris Wiki（Events）：https://stellaris.paradoxwikis.com/Events
- 数据口径：`engine/events.py::EVENT_TYPES`、`code/frontend/data/personas.json`、实跑日志 `v1.2/e2e_n10_week.jsonl`
