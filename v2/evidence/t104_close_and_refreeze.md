# T104 · v2 P1 收口（冻结 trunk · 统一重跑 + 重冻基线 + 门禁 + 消融）

> 收口 lead：obs-stats-dev。trunk 冻结（T90–T103 完成）；canonical policy = `economy.enabled=true`+`lifecycle.enabled=true`（+ 生产/社交/对话，随内核/life 生效）。
> **本文件所有结论均为冻结 trunk 产出，不带「待冻结确认」标注。**

## 1. 真 LLM N=20 重跑（关键路径）
- 日志：`v2/evidence/run_p1_final_n20_llm.jsonl`（N=20×84 seed42；独立 `--side-root=side_final_n20`）
- **sha256：`sha256:fb832372af235736b78e539ab676feff08c3e94e79ffcdbe0dc4b5d88b13a2fc`**；事件 **128,564**；**chain_ok / replay_parity / first_run_equals_replay / conservation_ok 全 True**；墙钟 **3839.6s**
- state_hash：`sha256:494184f461295db1f5c44d86cc4eced82d03b81566b0e434865ca36a2d004d53`

### P1 六条验收（逐条）

| # | 判据 | 实测 | 判定 |
|---|---|---|---|
| ① | `M(t)` 不穿 μ_floor 且有源 `PRODUCE>0` | `M_min=0`（=0，**OFF 默认预期值**）、`M_never_negative=True`、`PRODUCE=314` | **PASS** |
| ② | `purpose=dialogue>0` 且正文非模板、mock/真 LLM body 分叉 | `dialogue=270`；分叉见 §4（T103） | **PASS** |
| ③ | `MSG_PUBLIC/MSG_GROUP>0` | `MSG_PUBLIC=59`、`MSG_GROUP=8` | **PASS** |
| ④ | 双账本守恒 | `conservation_ok=True`（货币 P6）；商品账本内核 `assert_production_available`+商品守恒（T91 `294685=136216+158469+0+0`） | **PASS** |
| ⑤ | replay 逐位一致、`SYSTEM_ERROR=0` | replay_parity=True；`SYSTEM_ERROR=0` | **PASS** |
| ⑥ | 制度涌现指标可重算且字节相等 | `obs gate.metrics_bitwise_equal`=PASS | **PASS** |

## 2. 四项门禁（原始输出见 `gates_final_t104.txt`）

| 门禁 | 结果 |
|---|---|
| `pytest -q` | **277 passed** |
| `lint-imports` | **8 kept, 0 broken** |
| `obs gate G1–G7` | **GATE PASS** |
| `make lexicon-gate` | **exit=0** |
| **fail-loud**（kernel 新增） | `assert_production_available(...)` **OK**；kernel fail-loud 测试 **23 passed** |

> fail-loud 三态（T114 须保）：`production.enabled=true`+挂载→正常；`=false` 显式关→不触发、`PRODUCE==0` 守恒仍成立；`economy.enabled=true`+`production.enabled=true`+**hook 未挂载/静默失效→必须 FAIL**。

## 3. 消融（如实：仅有 economy.enabled / provider 两个真开关）

| 段 | 变量 | 事件 | 经济族* | PRODUCE | MSG_PUBLIC/GROUP | SYSTEM_ERROR | state_hash | provider |
|---|---|---:|---:|---:|---|---|---|---|
| A `econ_off` | `economy.enabled=false` | 122,579 | 1653 | 321 | 64 / 7 | 0 | `41c9052f…` | mock |
| B `canonical(mock)` | `economy.enabled=true` | 128,456 | 1721 | 321 | 64 / 7 | 0 | `9eba46a5…` | mock |
| C `canonical(real LLM)` | + provider=openai_compat | 128,564 | 1738 | 314 | 59 / 8 | 0 | `494184f4…` | openai_compat |

\* 经济族含 `METABOLISM`（lifecycle），非纯经济；A 段 `TRANSFER=0` 为关键差异。**三段 state_hash 互异 → 每步可归因。**

**⚠️ 已知限制（不造假消融）**：**production / social 无独立 `enabled` 开关**（`engine/hooks/production.py` 只读参数无开关；社交随 life 必然生效）→ 无法"逐步只变一个变量"地隔离「+生产 / +公开群聊/对话」。已立 **T114（production.enabled）/ T115（social.enabled）**（depends_on T104）补开关后再补真消融。

## 4. T103 分叉引用（带 by_provider 守卫）

- C 段账本 `LLM_CALL=4180`，**`by_provider={'openai_compat': 4180}`（无 mock 混入；`obs llm-cost --require-provider openai_compat` PASS）**。
- mock↔真 LLM 正文分叉见 `v2/evidence/t103_dialogue_real_llm.json`（T103：同 seed/config 下 dialogue 正文不同、非模板）。
- C 段 by_purpose：`{'describe': 20, 'dialogue': 270, 'importance': 3254, 'judge': 476, 'plan': 20, 'reflect': 140}` → **dialogue/judge/describe 均已自然触发**。

## 5. 重冻基线（旧基线归档）

- **G6 golden**：`code/obs/golden_baseline.json` 的 `n20_week_seed42` 重冻为 **`feature_set=v2-P1-final`、`n_events=128,564`**；旧基线归档 `v2/evidence/archive/golden_baseline_pre_t104.json`。
- **新指标基线**：`v2/evidence/metrics_baseline_p1.json`（econ_loop+social；回归用「≥ratio，增长通过、塌陷失败」）。

## 6. 成本（C 段）

- **4180 calls**；tokens **165024(in)+317177(out)=482201**；thinking=496、degraded=0；provider 守卫 PASS。

## 7. 已知缺口 / 预期值（不美化）

- **G-P1-1**：商品→货币转换通道缺失（B 层未涌现）→ `V=0.062536` 低、`median_wage_mu=null`、Agent 间零交易、`price_cv=∅`。**不计入 P1 六条验收**（P2，T110）。
- **`M_min=0` 是 OFF 默认（`policy.economy.fallback_mint_enabled=false`）预期值，非回归**。
- `n_contracts=0`、`n_votes=0`：本 run 未产出（指标就位、类型已登记），**未臆造**。
