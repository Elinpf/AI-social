# 普查并排对比（多段协议）

控制变量：同 seed / 同 config / 同 rounds，**只变 LLM 提供方 / 接线修复**。

> **根因标注**：**⚠️ 本表全部结论待「冻结 trunk 干净重跑」确认**（Leader 冻结时点 = T51/T52/T54/T56/T57 全落地后）。本表为 **post-T55 中间态**（旧 ③ 日志因 round=0 污染已弃用并重生成）。**A/B/C**：同 seed/同 N=10，只变 provider（独立缓存 + provider 守卫）。**结果**：A=5/20·经济 0 → B=11/20·经济 46 → C=11/20·经济 46。① 命中 5→11、经济族 0→46 的增量来自**当前 trunk 上已落地的经济/M6 相关代码（含在途提交）**；**最终归因待冻结 trunk 重跑**（T51 仍 in_progress、T56 仍 pending，勿归因给单个任务）。② **B(mock) 与 C(真 LLM) 的 state_hash/事件数/命中/经济族仍完全一致** → life 判定**当前设计使然**（LLM 仅产内容/记忆；plan 文本未参与计算）；**LLM 当前对结构性轨迹贡献 ≈ 0**。**T54** 落地后单独跑 C、查 `purpose∈{judge,narrate}` 且 `thinking=true` 的 LLM_CALL 是否出现（T54 验收信号）；**T57** 验收 = 同 seed 下 mock 与真 LLM 的 state_hash 不同。③ **成本**：C=522 次 LLM_CALL（provider 守卫 PASS，全 openai_compat）、tokens 21,569+17,481=39,050、225s、thinking=0；by_purpose 仅 importance/reflect/plan、无 judge/narrate/dialogue → **此为不完整 planner 的下限，非完整实验成本**。

## ① 20 类语义命中（并排）

| # | 语义事件 | A_preecon(N10) hit | A_preecon(N10) n | B_mock_econ(N10) hit | B_mock_econ(N10) n | C_llm_econ(N10) hit | C_llm_econ(N10) n |
|---|---|---|---|---|---|---|---|
| E1 | 师徒关系 | · | 0 | · | 0 | · | 0 |
| E2 | 赠礼 | · | 0 | · | 0 | · | 0 |
| E3 | 对抗训练 | · | 0 | ✓ | 24 | ✓ | 24 |
| E4 | 创作协作 | · | 0 | ✓ | 2 | ✓ | 2 |
| E5 | 储蓄 | · | 0 | ✓ | 11 | ✓ | 11 |
| E6 | 私语 | · | 0 | · | 0 | · | 0 |
| E7 | 情绪倦怠 | ✓ | 6 | ✓ | 5 | ✓ | 5 |
| E8 | 差异化评分 | · | 0 | ✓ | 2 | ✓ | 2 |
| E9 | 稀缺购买 | · | 0 | · | 0 | · | 0 |
| E10 | 技能练习 | ✓ | 31 | ✓ | 38 | ✓ | 38 |
| E11 | 礼貌婉拒 | · | 0 | · | 0 | · | 0 |
| E12 | 热爱vs薪资 | ✓ | 16 | ✓ | 7 | ✓ | 7 |
| E13 | 群体提案 | ✓ | 10 | ✓ | 10 | ✓ | 10 |
| E14 | 学术协作 | · | 0 | ✓ | 2 | ✓ | 2 |
| E15 | 反提案 | · | 0 | · | 0 | · | 0 |
| E16 | 场所选择 | ✓ | 260 | ✓ | 259 | ✓ | 259 |
| E17 | 权力冲突 | · | 0 | ✓ | 16 | ✓ | 16 |
| E18 | 关系接纳 | · | 0 | · | 0 | · | 0 |
| E19 | 破冰 | · | 0 | · | 0 | · | 0 |
| E20 | 关系维护 | · | 0 | · | 0 | · | 0 |

## ② 经济事件族（单列盯防）

| type | A_preecon(N10) | B_mock_econ(N10) | C_llm_econ(N10) |
|---|---|---|---|
| DEPOSIT | 0 | 11 | 11 |
| INIT_ENDOW | 10 | 10 | 10 |
| INTEREST_CHARGED | 0 | 0 | 0 |
| INTEREST_PAID | 0 | 0 | 0 |
| LOAN_DEFAULT | 0 | 0 | 0 |
| LOAN_ISSUED | 0 | 0 | 0 |
| LOAN_REPAY | 0 | 0 | 0 |
| MARKET_TRADE | 0 | 8 | 8 |
| METABOLISM | 0 | 0 | 0 |
| MONEY_BURNED | 0 | 0 | 0 |
| MONEY_MINTED | 1 | 1 | 1 |
| PENALTY_APPLIED | 0 | 0 | 0 |
| REVIVE_FEE_PAID | 0 | 0 | 0 |
| TAX_LEVIED | 0 | 17 | 17 |
| TRANSFER | 0 | 10 | 10 |
| UBI_PAID | 0 | 0 | 0 |
| WITHDRAW | 0 | 0 | 0 |
| **active_total** | 0 | 46 | 46 |

## ③ 总量 / 关键族 / 耗时

| 指标 | A_preecon(N10) | B_mock_econ(N10) | C_llm_econ(N10) |
|---|---|---|---|
| n_events | 39450 | 31228 | 31228 |
| TAG_EMITTED | 280 | 270 | 270 |
| NORM_ADOPTED | 10 | 10 | 10 |
| GOAL_ACHIEVED | 16 | 14 | 14 |
| RELATION_CHANGE | 4728 | 4122 | 4122 |
| seconds | — | — | — |
| tokens | — | — | — |

- A_preecon(N10)：命中 **5/20**；未命中：E1_mentorship, E2_gift_giving, E3_combat_training, E4_creative_collab, E5_saving_money, E6_whispered_comm, E8_diff_scoring, E9_scarcity_buy, E11_polite_rejection, E14_academic_collab, E15_counter_propose, E17_power_conflict, E18_rel_acceptance, E19_ice_breaking, E20_rel_maintenance
- B_mock_econ(N10)：命中 **11/20**；未命中：E1_mentorship, E2_gift_giving, E6_whispered_comm, E9_scarcity_buy, E11_polite_rejection, E15_counter_propose, E18_rel_acceptance, E19_ice_breaking, E20_rel_maintenance
- C_llm_econ(N10)：命中 **11/20**；未命中：E1_mentorship, E2_gift_giving, E6_whispered_comm, E9_scarcity_buy, E11_polite_rejection, E15_counter_propose, E18_rel_acceptance, E19_ice_breaking, E20_rel_maintenance
