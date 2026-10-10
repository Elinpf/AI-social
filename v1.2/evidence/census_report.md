# 事件普查报告（15 号规格）

- seed=42 rounds=84 weeks=1 N=20
- log_hash=`sha256:fdeebcf62a0bc110f82c922dad1d59bf366f8bd50de3f578cf15b970706701ec` log_last_seq=148868 engine_version=`v0.1-skeleton`
- 复现：`same_log_bitwise=True`、`llm_judged_metric_count=0`、`llm_calls=0`

## ① 原子事件频次表（Top）

| type | count |
|---|---|
| MEMORY_WRITE | 59188 |
| OBSERVATION | 58768 |
| RELATION_CHANGE | 22820 |
| NEED_UPDATE | 3506 |
| MEMORY_RETRIEVE | 1680 |
| ACTIVITY_COMPLETED | 420 |
| ACTIVITY_STARTED | 420 |
| PLACE_ARRIVED | 420 |
| PLACE_MOVE | 420 |
| TAG_EMITTED | 420 |
| GOAL_PROGRESS | 249 |
| RELATION_ENCOUNTER | 190 |
| MEMORY_REFLECT | 140 |
| TURN_SEAL | 84 |
| GOAL_SET | 39 |
| GOAL_ACHIEVED | 24 |
| AGENT_BORN | 20 |
| INIT_ENDOW | 20 |
| SCHEDULE_PLANNED | 20 |
| TIME_MARK | 7 |
| NORM_ADOPTED | 6 |
| NORM_PROPOSED | 6 |
| MONEY_MINTED | 1 |
| WORLD_INIT | 1 |

## ①b 经济事件族（单列盯防：本实验核心设定「货币经济激励成长」）

- ⚠️ **经济停摆（无任何真实经济活动）**：`active_total=0`（创世项 `genesis_total=21` 不计入活跃）

| type | count |
|---|---|
| DEPOSIT | 0 |
| INIT_ENDOW | 20 |
| INTEREST_CHARGED | 0 |
| INTEREST_PAID | 0 |
| LOAN_DEFAULT | 0 |
| LOAN_ISSUED | 0 |
| LOAN_REPAY | 0 |
| MARKET_TRADE | 0 |
| METABOLISM | 0 |
| MONEY_BURNED | 0 |
| MONEY_MINTED | 1 |
| PENALTY_APPLIED | 0 |
| REVIVE_FEE_PAID | 0 |
| TAX_LEVIED | 0 |
| TRANSFER | 0 |
| UBI_PAID | 0 |
| WITHDRAW | 0 |

## ② 20 类语义事件命中表

| # | 语义事件 | 含义 | hit | first_round | participants | count |
|---|---|---|---|---|---|---|
| E1 | E1_mentorship | 师徒关系 | False | None | 0 | 0 |
| E2 | E2_gift_giving | 赠礼 | False | None | 0 | 0 |
| E3 | E3_combat_training | 对抗训练 | False | None | 0 | 0 |
| E4 | E4_creative_collab | 创作协作 | False | None | 0 | 0 |
| E5 | E5_saving_money | 储蓄 | False | None | 0 | 0 |
| E6 | E6_whispered_comm | 私语 | False | None | 0 | 0 |
| E7 | E7_emotion_burnout | 情绪倦怠 | True | 27 | 20 | 20 |
| E8 | E8_diff_scoring | 差异化评分 | False | None | 0 | 0 |
| E9 | E9_scarcity_buy | 稀缺购买 | False | None | 0 | 0 |
| E10 | E10_skill_practice | 技能练习 | False | None | 0 | 0 |
| E11 | E11_polite_rejection | 礼貌婉拒 | False | None | 0 | 0 |
| E12 | E12_passion_vs_salary | 热爱vs薪资 | False | None | 0 | 0 |
| E13 | E13_group_proposal | 群体提案 | True | 3 | 20 | 6 |
| E14 | E14_academic_collab | 学术协作 | False | None | 0 | 0 |
| E15 | E15_counter_propose | 反提案 | False | None | 0 | 0 |
| E16 | E16_select_location | 场所选择 | True | 0 | 20 | 420 |
| E17 | E17_power_conflict | 权力冲突 | False | None | 0 | 0 |
| E18 | E18_rel_acceptance | 关系接纳 | False | None | 0 | 0 |
| E19 | E19_ice_breaking | 破冰 | False | None | 0 | 0 |
| E20 | E20_rel_maintenance | 关系维护 | False | None | 0 | 0 |

## ③ 未命中清单（17）

- E1_mentorship
- E2_gift_giving
- E3_combat_training
- E4_creative_collab
- E5_saving_money
- E6_whispered_comm
- E8_diff_scoring
- E9_scarcity_buy
- E10_skill_practice
- E11_polite_rejection
- E12_passion_vs_salary
- E14_academic_collab
- E15_counter_propose
- E17_power_conflict
- E18_rel_acceptance
- E19_ice_breaking
- E20_rel_maintenance

**难触发项（E4/E8/E12/E13/E17）命中情况**：

| 难触发项 | hit |
|---|---|
| E4_creative_collab | False |
| E8_diff_scoring | False |
| E12_passion_vs_salary | False |
| E13_group_proposal | True |
| E17_power_conflict | False |

## ④ 覆盖度

| 项 | 值 |
|---|---|
| atomic_types_registered | 73 |
| atomic_types_observed | 24 |
| unknown_types_seen | [] |
| atomic_registered_unused（前20） | ACTIVITY_INTERRUPTED, AGENT_DIED, AGENT_REVIVED, CONFLICT_RESOLVED, CONFLICT_STARTED, DEPOSIT, DROPPED, ECONOMY_INVARIANT_VIOLATION, GOAL_ABANDON, GROUP_CREATED, GROUP_JOINED, GROUP_LEFT, INTENT_REJECTED, INTEREST_CHARGED, INTEREST_PAID, LLM_CALL, LLM_JUDGMENT, LOAN_DEFAULT, LOAN_ISSUED, LOAN_REPAY |

## 护栏 / 干预标注

| 项 | 值 |
|---|---|
| death_count | 0 |
| guardrail_ok | True |
| observer_injection_count | 0 |
| rescue_flag_count | 0 |
| revival_count | 0 |
| safety_valve_triggered | False |
