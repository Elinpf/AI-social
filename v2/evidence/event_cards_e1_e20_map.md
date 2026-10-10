# 事件卡 ↔ 观测判据 映射（Agentopia 20 卡 ↔ census E1–E20）

> 目的：让前端「事件卡」由**真实发生的事件**驱动，而非静态展示。
> 权威：`v1.1/15-event-census-spec.md`（E1–E20 判定式）、`v1.1/07-emergence-observation.md`。
> 判定：**全 D 类**、只读日志、`llm_calls==0`、`llm_judged_metric_count==0`（F 项单列出门禁）。
> 接口：`obs.census_report(log)["semantic_hits"][E#] = {hit, first_round, participants, count}`。

| 卡（Agentopia） | 事件 | 含义 | 判据要点（确定性，源自 15 §2） | 主要依赖事件 |
|---|---|---|---|---|
| Mentorship | E1 | 师徒关系 | `same_skill ∧ skill_level(a)−skill_level(b)≥2 ∧ familiarity≥ε ∧ count(mentorship活动)≥2`（可选 [F] mentor_relation） | `SKILL_LEVEL_UP`、`RELATION_CHANGE`、`ACTIVITY_COMPLETED` |
| Gift-giving | E2 | 赠礼 | `∃ TRANSFER{from=a,to=b,reason=gift} ∧ affinity(a→b)≥ε_strong` | `TRANSFER`、`RELATION_CHANGE` |
| Combat Training | E3 | 对抗训练 | `∃ ACTIVITY_STARTED{template=combat_training}`；胜负 `CONFLICT_RESOLVED{rule_ref=training}` | `ACTIVITY_STARTED`、`CONFLICT_RESOLVED` |
| Creative Collab | E4 | 创作协作 | `∃ ACTIVITY_COMPLETED{template=creative_collab, participants≥2} ∧ ∃ SKILL_OUTPUT`（[F] 仅记评语） | `ACTIVITY_COMPLETED`、`SKILL_OUTPUT` |
| Saving Money | E5 | 储蓄 | `∃ DEPOSIT/WITHDRAW{a}` 或 `TRANSFER{a↔银行/SYSTEM}` | `DEPOSIT`/`WITHDRAW`、`TRANSFER` |
| Whispered Comm. | E6 | 私语 | `∃ MSG_DM{from=a,to=b,visibility=private} ∧ affinity(a→b)≥ε`（可选 [F] secret_trust） | `MSG_DM` |
| Emotion Burnout | E7 | 情绪倦怠 | `(need.energy<θ_dep ∨ need.leisure<θ_dep)` 连续 ≥`W_burn` ⇒ `STATE_CHANGE{to=exhausted}` | `NEED_UPDATE`、`STATE_CHANGE` |
| Diff. Scoring | E8 | 差异化评分 | `∃ SCORE_POSTED{cid} ∧ RANKING_EMITTED{cid}`（[F] qualitative_review 不进排名） | `SCORE_POSTED`、`RANKING_EMITTED` |
| Scarcity Buy | E9 | 稀缺购买 | `∃ MARKET_TRADE{good} ∧ 稀缺指数(good)≥θ_scarce`（订单簿深度低） | `MARKET_TRADE` |
| Skill Practice | E10 | 技能练习 | `∃ SKILL_PRACTICE{a,skill_id}`（可后续 `SKILL_LEVEL_UP`） | `SKILL_PRACTICE` |
| Polite Rejection | E11 | 礼貌婉拒 | `∃ OFFER_REJECTED ∧ ¬(同回合 INTENT_REJECTED for 同 offer)`（区分社交婉拒 vs 规则拒绝） | `OFFER_REJECTED`、`INTENT_REJECTED` |
| Passion vs Salary | E12 | 热爱vs薪资 | `∃ ROLE_CHANGE{a} ∧ (OFFER_CREATED{kind=job} ∨ utility 冲突超阈)`（[F] job_preference 仅记录） | `ROLE_CHANGE`、`OFFER_CREATED` |
| Group Proposal | E13 | 群体提案 | `∃ NORM_PROPOSED{nid} ∧ NORM_ADOPTED{nid, support≥threshold}`（采纳=纯规则） | `NORM_PROPOSED`、`NORM_ADOPTED` |
| Academic Collab | E14 | 学术协作 | `∃ ACTIVITY_COMPLETED{template=academic_collab, participants≥2} ∧ ∃(SKILL_LEVEL_UP ∨ SKILL_OUTPUT)` | `ACTIVITY_COMPLETED`、`SKILL_LEVEL_UP`/`SKILL_OUTPUT` |
| Counter-propose | E15 | 反提案 | `∃ OFFER_COUNTERED{o} ∧ round_no≤N_round` | `OFFER_COUNTERED` |
| Select Location | E16 | 场所选择 | `∃ PLACE_MOVE{a}` | `PLACE_MOVE` |
| Power Conflict | E17 | 权力冲突 | `∃ CONFLICT_STARTED{cid} ∧ CONFLICT_RESOLVED{cid, winner≠⊥}`（裁决 D+R，LLM 不当裁判） | `CONFLICT_STARTED`、`CONFLICT_RESOLVED` |
| Rel. Acceptance | E18 | 关系接纳 | `[F] LLM_JUDGMENT{dim=friendship_label, decision=accept, parties⊇{a,b}}` ∧ `RELATION_CHANGE{affinity 跨 ε_strong}` | `LLM_JUDGMENT`(F)、`RELATION_CHANGE` |
| Ice-breaking | E19 | 破冰 | 首次 `RELATION_ENCOUNTER{a,b} ∧ 当时 familiarity<ε ∧ ∃ MSG_{a↔b}`（可选 [F] first_impression） | `RELATION_ENCOUNTER`、`MSG_*` |
| Rel. Maintenance | E20 | 关系维护 | `∃ RELATION_CHANGE{a→b} ∧ (last_interaction_round 距前者 > D_maint)` | `RELATION_CHANGE`、`MSG_*`/`RELATION_ENCOUNTER` |

## 前端对接建议

- 每张卡的状态 = `semantic_hits[E#].hit`；首次出现回合/参与人数/次数分别用 `first_round/participants/count`。
- **F 类（E18 的 LLM 标签、E1/E4/E6/E12/E14/E19 的可选 [F]）单列**，卡片可标注来源（`frozen_llm`），但**不作为门禁判定**。
- 运行期：`python -m obs census --log <run.jsonl> --out census.json`；前端读 `semantic_hits` 即可点亮卡片。
- 硬保证：同一日志两次 `census_report` **逐字节相等**（`same_log_bitwise=true`），卡片状态可复现、可审计。

*（本表由观测层产出，供前端/美术事件卡对接；不改变任何事件判定口径。）*
