# 幸福感 / 生活质量报告 · wellbeing_report（W1–W7）

- round=83 log_hash=`sha256:fdeebcf62a0bc110f82c922dad1d59bf366f8bd50de3f578cf15b970706701ec`
- 激励层（经济机制）与观测层（W1–W7）分离；**禁止单一分数优化**

## 汇总（D 类）

| 指标 | 值 |
|---|---|
| divergence_count | 20 |
| gini_net_worth | 0.0 |
| mean_net_worth | 10000.0 |
| n_alive | 20 |
| wellbeing_vector_keys | ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7'] |

## 背离检测（金钱 ≠ 幸福，D 类可重算）

| 项 | 值 |
|---|---|
| divergence_count | 20 |
| divergence_rate | 1.0 |
| cases | {"rich_unhappy": 0, "poor_but_rich_relations": 20, "growth_stalled": 0} |

## 维度分量键

- W1_economy、W2_social_status_D、W4_health、W5_relation_quality、W6_skill_growth、W7_autonomy_meaning_D

## F 类（W3 主观满足 / W2 互评 / W7 meaning，单列·不入门禁）

- `contains_llm_judgment=False`
- subjective_satisfaction={}
- meaning_score={}
