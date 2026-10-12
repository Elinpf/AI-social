# T222 证据：M2b「受限选择」路径（life 侧）

> 作者：life-layer-dev ｜ 日期：2026-10-12
> 任务：T222-m2b-implementation（主责）｜ 协作：freeze-layer-dev（provider/freeze）、obs-stats-dev（口径）、kernel-dev（引擎侧）
> 关键前置：T212 结论 `v2/refs/m2b-judge-ab.md`（一致率 0.9902、tokens_out 16.3×↓、置信度回退证据不足→默认分支 B）

## 0. sha / 命令

| 件 | sha | 内容 |
|---|---|---|
| life 脚手架 | `a956b35` | `JUDGMENT_OPTIONS` 单一真源 + `policy.m2b` 开关（默认关）+ `soft` 判别式分派 |
| life 调用点 | `7481f6f` | `agent.py` 判定调用点接 M2b + `soft` 逃生兜底 + 单测 |
| 共用底座 | `53410f1` | `CRITICAL_DIMENSIONS` + 语义源==投影守卫（T221b 共用） |
| freeze B1 | `dd865d9` | `LLMClient.judge_discriminative` + provider logprobs |
| obs 口径 | `2058d08` | `obs.admission.judge_method_rates`（escape/fallback/inert 唯一口径） |

```bash
cd code && python -m pytest tests/test_t222_m2b.py -q          # 10 passed
cd code && python scripts/t222_m2b_switch_compare.py --n 10 --rounds 84 --seed 7
cd .. && make lexicon-gate && cd code && lint-imports
```

## 1. 设计要点（对齐 T213 设计 + Leader 口径）

- **候选枚举单一真源** `life/constants.JUDGMENT_OPTIONS`：每个 judge 维含**逃生项 `undecidable`**；`ESCAPE_FALLBACK` 给确定性兜底。LLM 只"选"不"造枚举"。
- **默认关 = 旧路径本身**（`policy.m2b.judge.mode=generative`）：**"关闭"与"现在"在结构上是同一件事** → "逐项一致"由设计保证，不由测试兜。
- **逃生项语义**：`decision` 保留模型原话（`undecidable`，与 freeze 落盘一致，故 `escape_rate` 可从日志聚合）；`resolved` = 确定性兜底值供**下游消费**。**不静默**。
- **回退**：默认分支 B = **不开置信度回退**；候选分值差阈值 `margin_theta` 默认 `0.0`+`fallback=none` → **保守不触发**【未标定，见 §5】。
- **`mentor_relation`**：登记进 `JUDGMENT_OPTIONS`，`MENTOR_DIMENSION_WIRED=False` → **inert（无调用点，不假装有活）**；obs 按 `inert=True` 单列、不进 mainline。
- **`importance`** 一并（另一条轴）：判别式走 `soft.judge(dimension="importance")`，候选 `{1..10}+undecidable`。

## 2. 开关对照（离线、确定性，N=10×84，seed=7）

| 侧 | events | LLM_JUDGMENT | method 直方图 | replay parity | 守恒 |
|---|---|---|---|---|---|
| **off（generative，默认）** | **36763** | 319 | `{None:319}`（旧路径） | ✅ | ✅ |
| **on（discriminative）** | 36799 | 860 | `{discriminative:860}` | ✅ | ✅ |

- **off 的 events=36763 = 既有基线（T133 证据同为 36763）** → **"关闭=现状"有数**（不只是设计声明）。
- **on** 额外 36 事件来自 `importance` 判别式（+539 judgment）；**两侧 replay_parity/conservation 均 True**（判别式不破坏确定性与守恒）。
- 两侧 `final_state_hash` 不同（**预期**：判定路径不同）。
- **off vs on 的差异 100% 归因于 LLM_JUDGMENT/派生事件**（无未知事件类型）。

## 3. `escape_rate` / `fallback_rate`（obs 唯一口径 `judge_method_rates`）

on 侧（offline mock provider）：

| dim | n | escape_rate | fallback_rate | inert |
|---|---|---|---|---|
| rel_affinity | 23 | 0.2609 | 0.0 | false |
| rel_trust | 3 | 0.6667 | 0.0 | false |
| rel_familiarity | 102 | 0.3922 | 0.0 | false |
| stance | 61 | 0.2459 | 0.0 | false |
| respect | 61 | 0.3115 | 0.0 | false |
| affection | 61 | 0.2295 | 0.0 | false |
| weekly_focus | 10 | 0.1000 | 0.0 | false |
| importance | 539 | 0.1002 | 0.0 | false |

- **`rel_respect` / `mentor_relation` 未出现**：`rel_respect` 本 run 无阈值穿越；**`mentor_relation` 无调用点 → 不出现在表里（inert 成立）**。
- **`fallback_rate=0.0`**：默认 `fallback=none` → 无回退（保守，符合分支 B）。
- ⚠️ **这些 `escape_rate` 是 offline MockProvider 的产物，不是真实模型行为** → **不能据此判"枚举是否完备"**。真实 `escape_rate` 需真 provider 跑批**【未验证】**。机制（逃生项存在、可聚合、偏高=回去补枚举）已验证。

## 4. 单测（`code/tests/test_t222_m2b.py`，10 passed）

- 候选枚举完备/互斥/逃生项存在；兜底值∈候选；`JUDGMENT_OPTIONS ⊇ 已发射维度`。
- **默认关 payload 无新增字段**（`method` 不在 generative payload）→ 逐项一致。
- 判别式分派（`method`/`margin`/`resolved`）、**逃生→兜底**（decision 保留 `undecidable`、resolved=兜底）、**失败→可见 rng-branch 回退**。
- `judge_method_rates` 聚合 + `mentor_relation` `inert=True`。
- **e2e（N=3×12）**：判别式开→产 `method=discriminative`、`decision∈envelope.options`、守恒/链 ok。

## 5. 成本对照（对齐 obs：`tokens_out`，`cost_ratio_out`）

- **判据**：`judge` ≤0.2×基线、`importance` ≤0.3×（分母=out）。
- **T212 实测（真 provider，`v2/refs/m2b-judge-ab.md`）**：`tokens_out` 26166→1604（**16.3×↓ / ratio 0.061 ≤ 0.2**）、`reasoning=0`、延迟 p50 1.55s→0.1285s。
- ⚠️ **本 run 的 token 数是 offline mock 合成值，不入成本判据**；**life 侧真 provider 的 end-to-end 成本对照【未验证】**（本环境无 `LLM_API_KEY`，真跑批由 freeze/obs 侧执行）。
- 算式：`ratio_out = tokens_out(B) / tokens_out(A) = 1604/26166 ≈ 0.061 ≤ 0.2` ✅（判据 T212 数据）。

## 6. 门禁

- `pytest tests/test_t222_m2b.py`：**10 passed**。
- `make lexicon-gate`：**新增违规 0**，退出 0。
- `lint-imports`：**Contracts: 9 kept, 0 broken**。
- `pytest tests`（全量）：383 passed，4 failed —— **均非本任务**：`test_obs_metrics::test_obs_gate_on_kernel_log`（obs 侧门禁改名 WIP，`_conformance` vs `metrics_bitwise_equal`）；`test_freeze` ×3（**单跑绿、全量红**的瞬态，环境 inode/磁盘压力所致，非代码）。

## 7. 未验证 / 遗留

- 【未验证】真实 provider 的 life end-to-end 成本对照（无 key）。
- 【未验证】真实 `escape_rate` / margin 阈值标定（本集无负例；`margin_theta` 默认不触发 = 分支 B）。
- 【inert】`mentor_relation` 规则兜底已登记，无调用点，待 E1 接线生效。
- 【环境】共享树 inode/磁盘紧张 → 出现"单跑绿、全量红"瞬态；建议报告/跑批注意清理 `__pycache__`/临时 side store。
