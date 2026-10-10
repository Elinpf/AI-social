# T63 最终消融对比（冻结 trunk）

> trunk 冻结（T51/T52/T54/T55/T56/T57/T59/T60 + T61/T62）；canonical policy = `economy.enabled=true` + `lifecycle.enabled=true`（metabolism_mu=140, liquid_trigger_mu=250, liquid_sustain_mu=600, credit_unsecured_base_mu=0）。
> 每段仅变一个变量。narrate 为纯输出（affects_state=false），不计入轨迹。
> **N 标注**：A/B1/B2 同时在 N=20 与 N=10 跑；**C（真 LLM）为 N=10 与 N=20（目标规模，T73 已补）**。

## ① N=20（用户目标规模）

| 段 | econ/life | 事件 | 20类命中 | 经济族 | 生命周期族 | state_hash | SYSTEM_ERROR | parity | seals_ok | 死亡(轮次) | 复活 | LOAN_ISSUED/DEFAULT |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_N20 | False/False | 116063 | 14/20 | 0 | 0 | `sha256:20d88eb9611…` | 0 | True | True | — | 0 | 0/0 |
| B1_N20 | True/False | 121179 | 16/20 | 111 | 1 | `sha256:b19d8aec361…` | 0 | True | True | — | 0 | 0/0 |
| B2_N20 | True/True | 124451 | 16/20 | 2011 | 2031 | `sha256:486d31fc43d…` | 0 | True | True | P001@60,P002@66,P003@66,P004@69,P005@70,P006@70,P007@70,P008@70,P010@70,P011@70,P009@73,P012@73,P013@73,P014@73,P015@73,P016@73,P017@73,P019@73,P020@73,P018@76 | 10 | 20/7 |
| **C_N20**（T73 补） | True/True/**openai_compat** | 124731 | 16/20 | 2026 | 2045 | `sha256:acf10e5a07d…` | 0 | True | True | P001@60,P003@64,P002@65,P010@68,P008@69,P006@70,P007@70,P011@70,P004@73,P005@73,P009@73,P012@73,P013@73,P014@73,P015@73,P016@73,P017@73,P018@76,P019@76,P020@76 | 12 | 20/7 |

## ② N=10（含真 LLM C 段）

| 段 | econ/life/provider | 事件 | 20类命中 | 经济族 | 生命周期族 | state_hash | SYSTEM_ERROR | parity | seals_ok | 死亡(轮次) | 复活 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | False/False/mock | 30892 | 14/20 | 0 | 0 | `sha256:81f43e540ae…` | 0 | True | True | — | 0 |
| B1 | True/False/mock | 33212 | 15/20 | 61 | 1 | `sha256:78998e3c726…` | 0 | True | True | — | 0 |
| B2 | True/True/mock | 34535 | 15/20 | 997 | 1003 | `sha256:9be080ebdc3…` | 0 | True | True | P001@63,P002@65,P003@70,P004@70,P005@71,P007@72,P008@72,P006@73,P009@73,P010@75 | 3 |
| C | True/True/openai_compat | 35030 | 16/20 | 994 | 997 | `sha256:3dacc849d1b…` | 0 | True | True | P001@62,P002@66,P003@67,P004@70,P008@71,P007@72,P009@72,P005@73,P006@74,P010@74 | 3 |

## ③ 20 类命中集合（N=20）

- **A_N20**（14/20）：E10_skill_practice, E11_polite_rejection, E12_passion_vs_salary, E13_group_proposal, E14_academic_collab, E15_counter_propose, E16_select_location, E17_power_conflict, E19_ice_breaking, E3_combat_training, E4_creative_collab, E6_whispered_comm, E7_emotion_burnout, E8_diff_scoring
- **B1_N20**（16/20）：E10_skill_practice, E11_polite_rejection, E12_passion_vs_salary, E13_group_proposal, E14_academic_collab, E15_counter_propose, E16_select_location, E17_power_conflict, E18_rel_acceptance, E19_ice_breaking, E3_combat_training, E4_creative_collab, E5_saving_money, E6_whispered_comm, E7_emotion_burnout, E8_diff_scoring
- **B2_N20**（16/20）：同上集合
- **C_N20**（16/20，目标规模 + 真 LLM，T73 补）：E10_skill_practice, E11_polite_rejection, E12_passion_vs_salary, E13_group_proposal, E14_academic_collab, E15_counter_propose, E16_select_location, E17_power_conflict, E18_rel_acceptance, E19_ice_breaking, E3_combat_training, E4_creative_collab, E5_saving_money, E6_whispered_comm, E7_emotion_burnout, E8_diff_scoring

## ③b C@N=20（T73 补充验证，目标规模真 LLM）

- **段定义**：`B2@N=20 + judge`；provider=**openai_compat**（独立 `--side-root=side_Cn20`；`provider_guard PASS`，全 openai_compat、无 mock 混入）；canonical policy（economy=true/lifecycle=true）；seed42 / N=20 / 84 回合。
- **`state_hash`**：`sha256:acf10e5a07d…` **≠ B2@N=20 `sha256:486d31fc43d…`** ✔（满足 T73 预期）→ **LLM 输出在目标规模下确已进入结构决策**（T57 生效，非仅 N=10）。
- **门禁**：chain_ok=True、replay_parity=True、**seals_ok=True**、conservation_ok=True、**SYSTEM_ERROR=0**。
- **20 类命中**：16/20（与 B2_N20 同集合）——**宏观命中集合不变、微观轨迹已变**（`state_hash` 不同），属"LLM 影响内容/标签与个体选择、但未新增/减少可命中类"的如实结论。
- **经济/生命周期**：经济族 active_total=2026（TRANSFER31/MARKET_TRADE23/LOAN_ISSUED20/LOAN_DEFAULT7/TAX46/METABOLISM1600/REVIVE_FEE12）；生命周期族 2045；`near_death`=26、**`AGENT_DIED`=20、`AGENT_REVIVED`=12**；死亡轮次**错峰 60–76**；两路径并存（借贷续命 vs 借不到→死）。
- **成本（实测）**：**3950 次 LLM_CALL**；tokens_in **129,661** + tokens_out **312,954** = **442,615**；墙钟 **≈4400s（~73min）**；by_purpose：`importance`=3294、`judge`=**476**、`reflect`=140、`plan`=20、`describe`=**20**；`thinking`=496；唯一真实响应 872 条。
  - 注：实测高于 T73 预估（1.4–1.6k calls / 250–280k tok）——N=20 + judge/describe 自然触发所致；口径与 T43/T53 一致（成本记 LLM_CALL、判定记 LLM_JUDGMENT）。
  - 数据文件：`v1.2/evidence/c_n20.json`。

## ④ 归因声明

- A→B1：仅 `economy.enabled` false→true。B1→B2：仅 `lifecycle.enabled` false→true。B2→C：仅 provider mock→openai_compat（真 LLM）。
- **A/B1/B2 三段 `state_hash` 两两不同**（每步都改变轨迹，可归因）；**C 的 `state_hash`（`3dacc849…`）≠ B2（`9be080eb…`）** → **LLM 输出已真正进入结构决策**（T57 生效）。
- narrate 纯输出，不计轨迹。
- **规模敏感性（如实，非缺陷）**：N=10 时 B2/C 为 10 死/3 活；**N=20 时 B2 为 20 死/10 复活 → 10 活**，与 T61 canonical 验收一致（借贷续命存活路径存在）。N=10 续命贷额度偏小（234/81/192mu）→ 偿付不足者仍死。
- **两路径**：`LOAN_ISSUED`（续命贷）+ `LOAN_DEFAULT`（坏账）并存；`AGENT_REVIVED`>0 证明借贷/救助续命路径；`AGENT_DIED` 轮次错峰（N=20: 60–76 轮）。
