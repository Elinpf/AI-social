# v2 经济循环指标（`metrics.econ_loop.*`）+ 制度涌现 · T101（经济半侧）

> 口径：`v2/01-economy-substrate.md §2.1–§2.3、§5.1/§5.2`；字段：`v1.1/08 §1.2`（T90/T108）。
> **`qty` 单位 = milli-unit（1 unit=1000）**（T108 登记）——`Y` 已按此换算。
> 全 D 类；两次重算字节相等；`llm_judged_metric_count=0`；F 类单列出门禁（本项无 F）。

## 0. 输入与复现

- 日志：`../v2/evidence/run_b2_n20_econ.jsonl`（N=20×84 seed42，canonical：economy/lifecycle 开 + 生产/对话/群聊）
- log sha256：`sha256:633969153ecf9b88c112eeac3ee469e3f15bf1e7eeb4e6724e1caacddaf27ca4`
- **重算**：`python -m obs metrics --log v2/evidence/run_b2_n20_econ.jsonl --out v2/evidence/metrics_full.json`（取 `metrics.econ_loop.*` / `metrics.social.institutions.*`）
- **两次重算字节相等**：`metrics_bitewise_equal=True`（`obs gate.metrics_bitwise_equal` 同判 PASS）；`obs gate G1–G7` 全 **PASS**。

## 1. `metrics.econ_loop`（宏观循环，D）

| 指标 | 口径 | 实测 |
|---|---|---|
| `M(t)` 序列 | `TURN_SEAL.money_supply` | `M_final=35100`，`M_min=0`，`M_max=197200`，`M_mean=85948` |
| `M_target` | 创世铸币 `Σ MONEY_MINTED{reason=genesis}` | `200000` |
| `M(t)/M_target` | 见左 | `final=0.1755`，`min=0.0` |
| `M_never_negative` | `M_min≥0` | `True` |
| `V`（流速） | `(Σ TRANSFER+Σ MARKET_TRADE)/mean(M)` | `0.055848` |
| `Y`（总产出） | `Σ PRODUCE.(qty_milli/1000)×p_ref_mu` | `Y_mu=48070`；`Y_units_by_good={'art': 3946, 'food': 111216, 'material': 55608, 'service': 123915}` |
| 中位工资 | `median(TRANSFER amount where reason∈{wage,salary})` | `None`（**None=本 run 无工资流**） |
| `Gini` | 净值分布 | `0.858709` |
| 税池 | `fold_economy.tax_pool` | `3271` |
| 公共品供给 | 公共品预算执行额/数量（未落事件→0） | `public_goods_spend_mu=0` |
| 铸销平衡（**窗口**） | `最近一回合 net_mint_burn / M_final` | `net_mint_burn_last_round=0`，`mint_burn_balance_window=0.0` |
| 价格离散度 `CV` | `MARKET_TRADE`(带 `good_id`&`qty>0`) 成交价 `σ/μ` | `price_cv={}`，`price_cv_mean=0.0` |
| `n_produce` | `PRODUCE` 计数 | `321` |

> **口径防假绿（本项重点）**：
> - **累计 `(minted−burned) ≡ M_final`（守恒恒等式）→ 累计口径"永远=1.0"**。故铸销平衡改用**窗口口径**，并加锁测 `test_mint_burn_window_not_trivially_one`。
> - `V`/`CV`/`Gini`：均有「分母/样本为 0 → 0.0」且「不同构造 → 不同值」的可区分测试（`test_V_*`/`test_CV_*`/`test_gini_*`）。
> - `p_ref_mu` 权威在 `engine/production.GOODS`；观测层不可 import 写路径，故**镜像**并经 `test_pref_mirror_matches_engine` **交叉校验防漂移**。

## 2. 制度涌现（`metrics.social.institutions`，D；详见 metrics_social.md）

| 指标 | 实测 |
|---|---|
| `n_groups` / `group_kinds` | 8 / {'chat': 8} |
| `norm_proposed` / `norm_adopted` / `norm_violated` | 17 / 17 / 0 |
| `adoption_success_rate` / `norm_coverage` | 1.0 / 1.0（**不同口径**，见测试） |
| `n_contracts` / `contract_kinds` | 0 / {} |
| `employment_contracts` / `loan_contracts` / `n_votes` | 0 / 0 / 0 |
| `contract_fulfillment_rate` | 0.0 |

## 3. 如实标注的已知缺口/预期值（**不美化**）

- **`M_min=0` 是 OFF 默认配置（`policy.economy.fallback_mint_enabled=false`）下的预期值，不是回归**。
- **G-P1-1 已知缺口：商品→货币转换通道缺失（B 层未涌现）** → 表现为 `V=0.055848`（很低）、`median_wage_mu=None`、`MARKET_TRADE` 卖方仅世界 MARKET（Agent 间零交易）、`price_cv={}`。**这不计入 P1 的 6 条验收**（另列 P2 命题）。
- 雇佣/契约/投票本 run **未产出**（`n_contracts=0`、`n_votes=0`）——指标函数就位、类型已登记，触发即非零；**未臆造**。
- `public_goods_spend_mu=0`：公共品事件未落 → 0。

## 4. 面板数据契约（观测台接线）

见 `v2/evidence/panel_contract.md`（面板读取 `metrics.econ_loop.*` + `metrics.social.*` + `metrics.econ/lifecycle`）。
