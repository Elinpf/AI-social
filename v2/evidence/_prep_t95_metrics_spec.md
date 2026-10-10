# T95 预置：v2 P3 观测指标口径与实现计划（obs-stats-dev）

> 状态：**预置/草案（T95 依赖 T91 生产经济 + T94 社交对话，先备口径与脚本，待数据再实现）**。
> 权威来源：`v2/01-economy-substrate.md §5.1/§5.2`、`v2/02-social-v2.md §5.1–§5.6`。本文件**不新造口径**，仅汇总待实现项。
> 铁律：全部 **D 类（确定性可重算）**、**两次重算字节相等**、**`llm_judged_metric_count==0`**；F 类（`metrics.*_soft`）**单列、出门禁**；只读日志、`llm_calls==0`。

---

## 1. 命名空间与落位（复用 obs 现有结构）

`metrics()` 快照新增（与 `econ/lifecycle/life/emergence/wellbeing` 并列）：
- `metrics.econ`（扩）：宏观循环指标（§2）
- `metrics.social.institutions`（D）：制度涌现（§3）
- `metrics.social.network` / `metrics.social.group_heat` / `metrics.social.issues`（D）：社会结构（§4）
- `metrics.social_soft`（F，仅描述/敏感性）：尊重/喜爱/议题情感冻结值

实现落位：新增 `obs/econloop.py`（宏观循环）、`obs/social.py`（网络/群热/议题）、`obs/institutions.py`（制度）；复用 `obs/emergence.py` 的 PageRank/社团/tag/norm 与 `obs/wellbeing_soft`；统一在 `obs/report.py::metrics()` 组装。依赖白名单不变（engine.canon/ledger/events/time）。

## 2. 宏观循环指标（`metrics.econ.*`，v2/01 §5.1）

| 指标 | 口径 | 期望（N=20 沙盒） |
|---|---|---|
| `M_total` | `TURN_SEAL.money_supply` | ∈[0.9,1.1]×M_target 且**全程>0** |
| `V`（流速） | `(ΣTRANSFER+ΣMARKET_TRADE)/M` | [0.3,1.5] |
| `Gini` | 净值分布 | [0.2,0.5] |
| `Y`（总产出） | `Σ PRODUCE × p_ref` | >0 且不萎缩 |
| 中位工资 | `Σ wage / 受雇人数` | ≥ `metabolism` |
| 死亡率/存活率 | `AGENT_DIED` / 存活占比 | 多数存活、少数死亡、有复活 |
| 铸币/销毁平衡 | `|Mint−Burn|/M` | <5% |
| `CV`（价格离散度） | 同类商品成交价 `σ/μ` | >0 即有议价 |

## 3. 制度涌现指标（`metrics.social.institutions.*`，v2/01 §5.2 + v2/02 §5.6）

| 指标 | 口径 |
|---|---|
| 雇佣合同数 | `CONTRACT_CREATED(type=EMPLOYMENT)` 活跃/累计 |
| 契约多样性 | 契约类型去重数 / 6 类 |
| 规范采纳数 | `NORM_ADOPTED` 按 type 分组计数 |
| 发行决策数 | `MONEY_MINTED(by=vote_id)` / 铸币提案数 |
| 公共品供给 | 公共品预算执行额 / 公共品数量 |
| 契约履约率 | `CONTRACT_FULFILLED / CONTRACT_CREATED` |
| 违约/坏账率 | `CONTRACT_VIOLATED`、`LOAN_DEFAULT` 占比 |

## 4. 社会结构指标（v2/02 §5.1–§5.3）

- `social.network`：`G_comm`（MSG 边权）、`comm_n_edges/comm_density/comm_degree_mean/comm_pagerank_topK/comm_reciprocity`；`G_org` 二分图 → `org_size_dist/org_overlap`；`cross_group_edge_ratio`。确定性 tie-break（节点/边升序、PageRank d=0.85 固定 K）。
- `social.group_heat`：`n_public_posts/public_post_rate`、`n_group_msgs/group_msg_rate`、`active_groups`、`per_group{msg_count,participants,msgs_per_member,heat_gini}`、`public_vs_group_vs_dm_ratio`、`broadcast_depth1_ratio`、`spam_drop_rate=DROPPED(MSG_*)/attempted`。
- `social.issues`：per-topic `freq/share/entropy/hhi/adoption/valence_mean/trend`、`lifespan/peak_freq/peak_round`、`n_places/n_groups/participants`、`promoted/escalated_to_norm`；`reaction_counts{kind}`；`reputation_topK`。

## 5. F 类（`metrics.social_soft`，出门禁）

读 `LLM_JUDGMENT`（respect/affection、议题情感）冻结值，标 `frozen_llm`+`frozen_ref`；**不进判定/门禁**。

## 6. 门禁与复现计划（与 T96 联动，避免多次重冻）

1. 实现后：`obs gate` 增/改 schema 断言（新事件类型 `PRODUCE/CONTRACT_*/VOTE_CAST` 登记 08 后加入 `EVENT_TYPES`）；`G7 schema_conformance` 覆盖新事件字段。
2. **G6 黄金基线**：v2 新事件 + policy 变更会改 `engine_version` 指纹 → **按最终 canonical 指纹重冻一次**（与 T96 统一收口，避免多次重冻）。
3. 字节相等：`metrics()`/`census` 两次运行规范 JSON 逐位一致（现有 `check_metrics_bitwise` 覆盖新命名空间）。
4. 交付：口径表 + 重算命令 + `v2/evidence/` 报告。

## 7. 依赖与顺序

- **等 T91（生产/经济，新事件 `PRODUCE/CONSUME/DEPRECIATE/PRODUCE_OVERFLOW`）与 T94（社交/对话，`MSG_PUBLIC/GROUP`、议题/组织事件）落主干**后，obs 才能折叠出上述指标（否则 events=0）。
- T95 实现 → **T96 统一收口**（解冻后一次重跑 + 重冻基线 + 四门禁 + 新消融）。
