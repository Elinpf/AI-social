# 事件卡映射（青溪镇 E1–E20 ↔ Agentopia 20 卡）· 门控版（T118）

> 目标参考：`v1.2/evidence/style-refs/agentopia_events_ref.png`（Agentopia 论文 图1：20 张社会/生活事件卡拼贴）。
> 我方卡（**单一在用集**）：`assets/generated/event_cards_hand/<slug>.png`（手绘像素）；清单 `event_cards_hand.json`。
> **门控权威（机器可读）**：`v2/evidence/event_card_mapping_revised.json`；审计表：`v2/evidence/event_card_mapping_audit.md`（obs-stats-dev, T118）。
> ✅ **数字口径（T123 已收敛）**：**权威 = 脚本 `code/obs/recount_cards.py`（一条命令）+ `v2/evidence/event_card_counts.json`**。
> **现行 23,185 / 门控后 612 / 降幅 −97.36%**。
> **`546`、`616` 已作废**（546=template-only 变体，未含 `TRANSFER{gift}`+`DEPOSIT` 语义并集、且 whisper=0；616 含 `rel_accept` 兜底+4，按反造假移除）。数字以脚本输出为唯一来源。
> 四区 + 标注规格：`assets/event-card-spec.md`。

---

## 0. 卡片模型：两档 + 两层标注（定稿）

**两档**（Leader 裁决，T118）：
- **① 片段卡（episode）**：由**若干事件在窗口内聚合**触发（D 类确定性可重算）。语义 = "一段生活片段"，**非**单条事件别名。
- **② 事件卡（event）**：**本身就是一次事件、且低频**（或**带语义条件门控**，如活动 `template=`／`scarcity_index≥θ`）。
- **不配卡**：**机械/高频事件默认不配**（`RELATION_CHANGE`、`NEED_UPDATE`、`PLACE_MOVE`、`ACTIVITY_*` 逐次、`LLM_JUDGMENT` 逐次）。原则：**宁可不显示，也不显示错的。**

**两层标注**（= 卡片机制标注区）：
- **第①层 机制标注（聚合事实）**：复用 4 模板 `rel-bars / equation / timeline / ab-choice / status`（**对基准 5↔5 完备，无需新增**）；
- **第②层 一句叙事引用**：`quote = {text, quote_ref:{msg_id, seq, channel}}`——**只能引用日志里真实存在的 `MSG_*.body`**（不造假）；`channel ∈ {private, global, members}`（私聊/公开/群组，渲染可分档）；**观测台里可点击 → 跳转/高亮源 `MSG_*`**。
- **口径澄清（防歧义）**：`quote` 锚定的 `MSG_*` 是**窗口内代表样本**，**不是 episode 定义**；定义由 ① 层聚合式给出。**"没有锚定 MSG ≠ 不存在该 episode"。** ① 定义"为什么算片段"，② 举证"当事人怎么说"。

---

## 1. 20 卡对照表（含档位 / 门控 / 本 run 预测频次 / 当前为 0 原因）

> 本 run = 冻结 canonical 真 LLM 日志 `v2/evidence/run_p1_final_n20_llm.jsonl`（128,564 事件，N=20）。频次取 `event_card_mapping_revised.json`。

| # | 中文名 | slug | Agentopia 卡 | 档 | ① 标注类型 | **② 门控条件（D 类）** | 本 run | 为 0 原因 |
|---|---|---|---|---|---|---|---|---|
| E1 | 导师指导 | `mentorship` | Mentorship | episode | rel-bars | `ACTIVITY_*{template=mentorship}` | 32 | — |
| E2 | 赠礼 | `gift-giving` | Gift-giving | event | equation | `TRANSFER{reason=gift}` ∨ `ACTIVITY_*{template=gift}` | 93 | — |
| E3 | 冲突演练 | `combat-training` | Combat Training | event | status | `ACTIVITY_*{template=combat_training}`（**非任意活动开始**） | 68 | — |
| E4 | 创意协作 | `creative-collab` | Creative Collab | event | rel-bars | `ACTIVITY_*{template=creative_collab}` | 6 | — |
| E5 | 储蓄 | `saving-money` | Saving Money | event | equation | `DEPOSIT`/`WITHDRAW` ∨ `ACTIVITY_*{template=savings}` | 54 | — |
| E6 | 私语 | `whispered-comm` | Whispered Comm. | event | ab-choice | `ACTIVITY_*{template=whisper}` ∨ `MSG_DM{visibility=private}` | 42 | — |
| E7 | 情绪耗竭 | `emotion-burnout` | Emotion Burnout | episode | status | `STATE_CHANGE{to=exhausted}`（连续低需求聚合） | **0** | 本 run 无 `to=exhausted`（需 life 侧状态机产出） |
| E8 | 评分分歧 | `diff-scoring` | Diff. Scoring | episode | rel-bars | 同 subject `SCORE_POSTED` **分歧**（≥2 且极差≥θ）**∨** respect/affection 两维**背向** | **0** | ①本 run 按 subject 聚合无分歧；②**当前无 respect/affection 维度** |
| E9 | 稀缺抢购 | `scarcity-buy` | Scarcity Buy | event | equation | `MARKET_TRADE{scarcity_index≥θ}` ∨ `reason=scarce_buy` | 23 | — |
| E10 | 技能练习 | `skill-practice` | Skill Practice | event | status | `SKILL_PRACTICE` | 77 | — |
| E11 | 礼貌拒绝 | `polite-reject` | Polite Rejection | event | ab-choice | `OFFER_REJECTED`（非规则 `INTENT_REJECTED`） | 11 | — |
| E12 | 热爱与薪资 | `passion-salary` | Passion vs Salary | episode | ab-choice | `ROLE_CHANGE`（`OFFER_CREATED` **移出**：泛要约≠权衡） | 9 | — |
| E13 | 小组提案 | `group-proposal` | Group Proposal | event | timeline | `NORM_PROPOSED`（采纳 `NORM_ADOPTED` 不重复配卡） | 19 | — |
| E14 | 学术协作 | `academic-collab` | Academic Collab | episode | rel-bars | `ACTIVITY_*{template=academic_collab}` | 14 | — |
| E15 | 反提案 | `counter-propose` | Counter-propose | event | timeline | `OFFER_COUNTERED` | 10 | — |
| E16 | 选择地点 | `select-location` | Select Location | event | ab-choice | `ACTIVITY_*{template=select_location}`（**非 `PLACE_MOVE`**：走路≠选址） | 22 | — |
| E17 | 权力冲突 | `power-conflict` | Power Conflict | episode | rel-bars | `CONFLICT_RESOLVED{cid, winner≠⊥}`（`STARTED` 不重复；仅 RESOLVED 配卡=88） | 88 | — |
| E18 | 关系接纳 | `rel-acceptance` | Rel. Acceptance | episode | rel-bars | 同 agent→同对象 **accept↔reject 立场翻转**（或关系维度跃变） | **0** | **当前 `LLM_JUDGMENT.dimension` 无 `accept/reject`** → 严格门控=0；**临时兜底 `template=rel_accept` 已按反造假移除**（待 life 侧补维度） |
| E19 | 破冰 | `ice-breaking` | Ice-breaking | episode | ab-choice | 首次 `RELATION_ENCOUNTER ∧ familiarity<ε ∧ ∃MSG`；或 `template=ice_break` | 12 | — |
| E20 | 关系维护 | `rel-maintain` | Rel. Maintenance | episode | timeline | `RELATION_CHANGE{a→b, gap>D_maint}`；或 `template=rel_maintain` | 32 | — |

**合计：门控后 612 张**（现行 23,185 张，**−97.36%**）；叙事卡占比 ~1% → ~100%。**权威 = `code/obs/recount_cards.py` + `v2/evidence/event_card_counts.json`**（`546`/`616` 作废）。门控明细：mentorship32 / gift-giving93 / combat68 / creative6 / saving54 / whisper42 / scarcity23 / skill77 / polite11 / passion9 / group19 / counter10 / select22 / power88 / academic14 / ice12 / rel-maintain32 / emotion0 / diff0 / rel-acceptance0。

---

## 2. 不配卡（机械/高频事件，逐次不配）

`RELATION_CHANGE`（本 run 16,716）、`NEED_UPDATE`（3,399）、`PLACE_MOVE`（511）、`ACTIVITY_STARTED`/`ACTIVITY_COMPLETED` 逐次（1,100）、`LLM_JUDGMENT` 逐次（476）→ **默认不配卡**。它们要么由 ① 的 **聚合门控**触发片段卡（E7/E8/E18/E20），要么仅作事件行显示。

---

## 3. 完备性依据（对基准 5↔5，无缺无余）

| 图中标注形态 | 实例（Agentopia 图1） | 我方模板 |
|---|---|---|
| 算式 | `💰(40) − 💰(35) = 💰(5)`（Scarcity Buy） | `equation` |
| 双面板对照 | `respect high/affection low ‖ affection high/respect low`（Diff. Scoring） | `rel-bars` |
| 日历/进度勾选 | `Mo–Su` 日历 ✓（Group Proposal）、`Day1✗ Day2✓ Day3✓`（Counter-propose） | `timeline` |
| 状态条 | 空电池+心碎（Emotion Burnout）、`Recharging Resting to survive.`（Polite Rejection） | `status` |
| 选项对照 | `Music rehearsal room✗ VS sunset rooftop✓`、`Boring Job✗ / Interesting Research✓` | `ab-choice` |

→ 5↔5 严格对应，**模板集对基准完备、无需新增**。

---

## 4. 单一在用集 + 接线 + 归档

- ✅ **在用**：`assets/generated/event_cards_hand/`（20 张 + json + sheet）。
- 🗄️ **已归档**：`assets/generated/_archived/event_cards/`、`_archived/event_cards_v2/`（三套并存曾致 60 张零引用，同 T107 型）。
- **接线**：单一真源在 `src/sprites.js`（`EVENT_CARD_BASE` + `EVENT_CARDS`）；`src/audit.js` 事件流命中即显示卡图（`_cardHtml`）。**门控替换在 `sprites.js`/`audit.js` 由 frontend-dev 执行**（按 `event_card_mapping_revised.json`）：机械事件不再直配；`ACTIVITY_*` 按 `template`、`MARKET_TRADE` 按 `scarcity_index≥θ` 等条件命中。
- **风格**：用我方像素卡，只借鉴 Agentopia 的**信息结构**（图标徽章 / 图内机制标注 / 木牌标签），**不学其动漫画风**。

## 5. 诚实边界
动漫手绘那一层我们**做不到**（本机无图像生成）；我们给的是**手绘像素**（像素语言内的手绘）。真正接近 Agentopia 需用户提供图像生成通道。

## 6. P2 谱系（登记，未做）
**"社交提议被无视 / 同处无互动"**（负面/未发生也成卡）：目前仅 `OFFER_REJECTED` 覆盖"契约被拒"，**社交拒绝/沉默/无响应无卡** → 纳入 P2。
