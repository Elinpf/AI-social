# v2 社会面板指标（`metrics.social.*`）· T105

> 口径：`v2/02-social-v2.md §5`、`v2/evidence/_prep_t95_metrics_spec.md`；事件字段：`v1.1/08 §1.2`（T90 v2 登记）。
> 本项为 **T101 的社会半侧**：只做 `metrics.social.{network,group_heat,issues,institutions}` 指标函数 + 口径；
> **不含**经济半侧（`M(t)/M_target`、`V`、`Y`、中位工资、Gini、税池、价格 `CV` → 留 T101）；**不含**前端面板接线（留 T101）。

## 0. 输入与复现

- 日志：`../v2/evidence/run_b2_n20_social.jsonl`（N=20×84 seed42；由当前 trunk 生成，含 T98 社会通道）
- 日志 sha256：`sha256:633969153ecf9b88c112eeac3ee469e3f15bf1e7eeb4e6724e1caacddaf27ca4`
- **重算命令**：
  ```bash
  cd code
  python -m obs metrics --log ../v2/evidence/run_b2_n20_social.jsonl --out ../v2/evidence/metrics_full.json
  # 取 metrics.social.*；或
  python -m obs gate --log ../v2/evidence/run_b2_n20_social.jsonl --baseline auto
  ```
- **两次重算字节相等**：`metrics_bitewise_equal=True`（`obs gate` 的 `metrics_bitwise_equal` 同判 **PASS**）。
- **D 类**：`metrics.social.llm_judged_metric_count=0`；**F 类** `metrics.social_soft` 单列、**出门禁**（`contains_llm_judgment=True`）。

## 1. `social.network`（沟通图 / 组织图，D）

| 指标 | 值 |
|---|---|
| 通道计数 | DM=162, PUBLIC=64, GROUP=7 |
| 图节点 `n_nodes`（全部出现过的 Agent） | 27 |
| 有向边 `comm_directed_edges` | 161 |
| 无向边 `comm_undirected_edges` | 123 |
| `comm_density` | 0.350427 |
| `comm_reciprocity` | 0.308943 |
| `comm_degree_mean` | 5.962963 |
| `n_groups` / `org_size_dist` | 8 / [4, 4, 5, 5, 6, 6, 8, 8] |
| `org_overlap_agents` | 16 |
| `comm_pagerank_topK`（前3） | [{'agent_id': 'MARKET', 'score': 0.007126, 'rank': 21}, {'agent_id': 'P001', 'score': 0.033372, 'rank': 20}, {'agent_id': 'P002', 'score': 0.040918, 'rank': 17}] |

## 2. `social.group_heat`（公开/群聊热度，D）

| 指标 | 值 |
|---|---|
| `n_msg_dm` / `n_msg_public` / `n_msg_group` | 162 / 64 / 7 |
| `public_post_rate` / `group_msg_rate` | 6.4 / 0.7 |
| `active_groups` | 4 |
| 三通道份额 public/group/dm | 0.274678 / 0.030043 / 0.695279 |
| `heat_gini` | 0.321429 |
| `dropped_quota` / `intent_rejected_quota` / `spam_drop_rate` | 0 / 0 / 0.0 |

## 3. `social.issues`（议题/舆论，D）

| 指标 | 值 |
|---|---|
| `n_topics` / `freq_total` | 8 / 540 |
| `entropy` / `hhi` | 1.854951 / 0.181825 |
| `reaction_counts` | {} |
| `boycott_pairs` | [] |

> `by_tag` 明细见 `metrics_social.json`（`freq/share/adoption/valence_mean/lifespan/peak_*/n_places/participants`）。
> `PUBLIC_REACTION`/`VOTE_CAST` 若未落事件则为 0（**不臆造**）；本日志未见（见 §5）。

## 4. `social.institutions`（组织/规范/契约存量，D）

| 指标 | 值 |
|---|---|
| `n_groups` / `group_kinds` | 8 / {'chat': 8} |
| `norm_proposed` / `norm_adopted` / `norm_violated` | 17 / 17 / 0 |
| `adoption_success_rate` / `norm_coverage` | 1.0 / 1.0 |
| `n_contracts` / `contract_kinds` | 0 / {} |
| `contract_fulfillment_rate` | 0.0 |
| `employment_contracts` / `loan_contracts` / `n_votes` | 0 / 0 / 0 |

## 5. 口径说明与边界（如实）

- **契约族零值原因**：`CONTRACT_CREATED/FULFILLED/VIOLATED/EXPIRED`、`VOTE_CAST`、`PUBLIC_REACTION` 在本 run **未产出**（`n_contracts=0`、`n_votes=0`、`reaction_counts={}`）——其事件类型已在 `v1.1/08`（T90）登记，但当前 trunk 尚未由 life/econ 触发；指标函数已就位，一旦产出即非零。**未臆造字段**。
- **商品族**（`PRODUCE/CONSUME/DEPRECIATE/PRODUCE_OVERFLOW`）属**经济半侧**，本项**不纳入**（留 T101，且 T91 未落主干）。
- **F 类** `metrics.social_soft`（respect/affection）**单列、不进沙盒门禁**。
- **验收**：`obs gate G1–G7` 在本日志上 **全 PASS**（含 `schema_conformance`、`metrics_bitwise_equal`）。
