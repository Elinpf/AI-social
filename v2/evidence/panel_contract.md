# 观测台面板 · 数据契约（v2 P3，T101）

> 观测层（obs）产出**只读指标快照**；前端「观测台/经济循环面板」消费之。**本契约不含前端代码**（前端由 frontend-dev 实现）。
> 生成：`python -m obs metrics --log <run.jsonl> --out <snapshot.json>`（或 `python -m obs evidence ...`）。
> 保证：同日志两次快照**逐字节相等**（规范 JSON：键排序 + 浮点 `round(...,6)` + 全序 tie-break）；`llm_calls==0`。

## 快照顶层（面板读取）

```jsonc
{
  "round": int, "week": int, "day": int, "engine_version": str, "log_hash": "sha256:…",
  "metrics": {
    "econ":        { … v1 冻结 K 类：money_supply_final/gini_cash_final/… },
    "lifecycle":   { … 存活/死亡/复活 … },
    "econ_loop":   { … v2 宏观循环（下表）… },
    "social":      { "network":…, "group_heat":…, "issues":…, "institutions":… },
    "social_soft": { … F 类，单列，面板可标注来源 frozen_llm，不作门禁 … },
    "emergence":   { … }, "emergence_soft": { … },
    "wellbeing":   { … }, "wellbeing_soft": { … }
  },
  "reproducibility": { "llm_calls":0, "llm_judged_metric_count":0, … }
}
```

## 面板核心字段

### 经济循环（`metrics.econ_loop`）
- `M_final/M_min/M_max/M_mean/M_target`、`M_final_over_target`、`M_min_over_target`、`M_never_negative`
- `V`（流速）、`Y_mu`（总产出·mu）、`Y_units_by_good`（分商品·milli 单位）
- `median_wage_mu`（可为 `null`）、`gini_net_worth`
- `tax_pool_final`、`public_goods_spend_mu`
- `net_mint_burn_last_round`、`mint_burn_balance_window`（**窗口口径**，非累计）
- `price_cv`（分商品）、`price_cv_mean`、`n_produce`

### 制度涌现（`metrics.social.institutions`）
- `n_groups/group_kinds`、`norm_proposed/norm_adopted/norm_violated`
- `adoption_success_rate`（采纳率）**与** `norm_coverage`（覆盖率）——**两个不同口径**
- `n_contracts/contract_kinds/contract_fulfillment_rate`、`employment_contracts/loan_contracts/n_votes`

### 社会结构（`metrics.social.*`）
- `network`：`channel_counts{DM,PUBLIC,GROUP}`、`comm_directed_edges/comm_density/comm_reciprocity`、`comm_pagerank_topK`、`n_groups/org_size_dist`
- `group_heat`：`n_msg_dm/public/group`、`active_groups`、`public_vs_group_vs_dm_ratio`、`heat_gini`、`spam_drop_rate`
- `issues`：`n_topics/entropy/hhi`、`by_tag`、`reaction_counts`、`boycott_pairs`

## 建议的面板区块（前端）

1. **经济循环**：`M(t)/M_target` 折线（用逐回合 `TURN_SEAL.money_supply`）、`V`/`Y`/`Gini`/税池 卡片、`price_cv` 分商品。
2. **制度涌现**：规范采纳漏斗、契约数/履约率（本 run 为 0，占位显示"未产出"）。
3. **社会结构**：沟通图（`network`）、三通道份额、群热度、议题榜（`issues.by_tag`）。
4. **F 类标注**：`social_soft` 以"冻结 LLM 判定（敏感性）"单独样式呈现，**不入门禁/不作判据**。

## 判别/审计约定

- 面板**只读**快照，不回写世界；`state_hash`/`M(t)` 可复现可审计。
- **已知缺口**（面板应显式标注，勿当异常）：`G-P1-1 商品→货币转换通道缺失`（`V` 低、无工资、Agent 间零交易）；`M_min=0` 为 OFF 默认预期值。
