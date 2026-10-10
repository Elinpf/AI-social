# P0 验收证据包（N=20 单小镇单周）

> 全部报告**只读日志**产出、可复现；F 类（含 LLM 冻结判定）单列、**不进入门禁**。

## 事件族计数（真实内核分布，如实列出）

| type | count |
|---|---|
| MEMORY_WRITE | 59188 |
| RELATION_CHANGE | 22820 |
| NEED_UPDATE | 3506 |
| ACTIVITY_COMPLETED | 420 |
| ACTIVITY_STARTED | 420 |
| TAG_EMITTED | 420 |
| GOAL_PROGRESS | 249 |
| GOAL_SET | 39 |
| GOAL_ACHIEVED | 24 |
| NORM_ADOPTED | 6 |
| NORM_PROPOSED | 6 |
| NORM_VIOLATED | 0 |
| SEED_EVENT | 0 |
| SKILL_LEVEL_UP | 0 |
| SKILL_PRACTICE | 0 |

**⚠️ 待排查（真内核为 0，mini_kernel 有值）**：`NORM_VIOLATED` → 已派 life-layer-dev 与 kernel-dev 联合排查；**如实记录、未掩盖**。

## 经济事件族（单列盯防：货币经济激励成长）

- ⚠️ **经济停摆（无任何真实经济活动）**：`active_total=0`（创世项 `genesis_total=21` 不计入活跃）

| type | count |
|---|---|
| INIT_ENDOW | 20 |
| MONEY_MINTED | 1 |
| DEPOSIT | 0 |
| INTEREST_CHARGED | 0 |
| INTEREST_PAID | 0 |
| LOAN_DEFAULT | 0 |
| LOAN_ISSUED | 0 |
| LOAN_REPAY | 0 |
| MARKET_TRADE | 0 |
| METABOLISM | 0 |
| MONEY_BURNED | 0 |
| PENALTY_APPLIED | 0 |
| REVIVE_FEE_PAID | 0 |
| TAX_LEVIED | 0 |
| TRANSFER | 0 |
| UBI_PAID | 0 |
| WITHDRAW | 0 |

## 一、文件清单与用途
> **T63 最终结果（冻结 trunk）见 `ablation_final.md`（A/B1/B2/C 消融 + 归因）与 `gates_final.txt`（四项门禁原始输出）。**

| 文件 | 用途 |
|---|---|
| ablation_final.md | **T63 最终消融表**：A/B1/B2(N=20,N=10)+C(N=10)，含 state_hash/命中/经济族/生命周期族/死亡错峰/归因 |
| gates_final.txt | **四项门禁原始输出**：pytest / lint-imports / obs gate G1–G7 / make lexicon-gate |
| run_abl_*.jsonl(.summary.json) | T63 各段日志 + 摘要（A/B1/B2@N=20、A/B1/B2/C@N=10） |
| census_abl_*.json | T63 各段事件普查（20 类命中） |
| llm_cost_C.json | C 段真 LLM 成本 by_purpose（含 judge/describe，thinking>0） |
| run_n20_seed42_week1.jsonl | **统一运行日志**（JSONL，哈希链，append-only；本包唯一权威事实源） |
| run_stdout.txt | `orchestration run` 的 stdout（含 seconds / chain_ok / replay_parity / conservation_ok） |
| summary.json | **日志摘要**：文件 sha256、规范 log_hash、事件数、字节数、seed/N/rounds、engine_version、守恒、字节相等、门禁汇总 |
| metrics.json / .md | 确定性指标快照（`metrics`，7 命名空间：econ/lifecycle/life/emergence/emergence_soft/wellbeing/wellbeing_soft） |
| census_report.json / .md | **事件普查报告**（15 号规格）：① 原子频次表 ② 20 类语义命中表 ③ 未命中清单 ④ 覆盖度 |
| census_anomalies.json | 普查前置异常（事件字段不合约；空数组=无异常） |
| census_compare.md | 两次普查的 20 类命中并排对比（世界是否「活起来」） |
| census_report_pre_life_fix.json | 对比用：life 修复前的普查快照（census_compare.md 的基准） |
| run_n10_*.jsonl / census_report_*_n10.json | 三段对比用：N=10 的 rule 对照 与 真实 LLM 段日志+普查（见 census_compare.md） |
| llm_cost_n10.json | ③ 真实 LLM 段的成本：调用次数 + tokens_in/out（来自独立 FREEZE 缓存） |
| emergence_report.json / .md | 涌现判定报告（关系/圈层/规范/职业/传播级联） |
| wellbeing_report.json / .md | 幸福感报告（W1–W7 + 背离检测） |
| gate.txt | 复现门禁 G1–G7 的 PASS/FAIL 输出（含 G6 分布回归、G7 schema 合约） |
| pytest_report.txt | `pytest -q` 通过数记录（obs 专属 + 全量） |

## 二、如何从零重现（确切命令）

```bash
# 0) 依赖：Python 3.11+；在 code/ 下运行（conftest 已把 code/ 加入 sys.path）
cd code

# 1) 生成 N=20 单周日志（seed=42，20 位居民，84 回合）
python -m orchestration run --life --seed 42 --agents 20 --rounds 84 \
    --out ../v1.2/evidence/run_n20_seed42_week1.jsonl

# 2) 构建证据包（四类报告 + 门禁 + 摘要 + 本 README）
python -m obs evidence --log ../v1.2/evidence/run_n20_seed42_week1.jsonl \
    --out-dir ../v1.2/evidence --baseline auto

# 3) 单独跑复现门禁
python -m obs gate --log ../v1.2/evidence/run_n20_seed42_week1.jsonl --baseline auto

# 3b) 单独跑普查（本 N=20 日志存在 GOAL_SET 字段不合约：严格模式会硬报错，
#     故证据包用 --non-strict 产出并记录异常；严格模式见 census_report(strict=True)）
python -m obs census --log ../v1.2/evidence/run_n20_seed42_week1.jsonl \
    --out ../v1.2/evidence/census_report.json --non-strict

# 4) 测试（obs 专属 + 全量）
python -m pytest -q tests/test_obs_*.py     # obs 专属
python -m pytest -q                          # 全量
```

## 三、复现证据

- **日志指纹**：`log_sha256_of_file=sha256:e9e7cf3b47c1416b9826f94b8c1d897054c66f20bb2585768291f2729d8c1193`，规范 `log_hash=sha256:fdeebcf62a0bc110f82c922dad1d59bf366f8bd50de3f578cf15b970706701ec`，事件数 `148869`，大小 `63086081` 字节（**磁盘实测，权威**）。
- **`log_bytes` 口径**：`summary.log_bytes` = 磁盘实测（**权威**）；`run_stdout.txt` 里内核自报的 `log_bytes` 为**次要参考**，两者差异**待 kernel-dev 解释**（可能为「写出字节数 vs 落盘后大小」或含回滚缓冲差异）。
- **同一日志两次报告字节相等**：`metrics_bitwise_equal=True`（`obs` 用规范 JSON：键排序 + 浮点 round(...,6) + 全序 tie-break；`python -m obs gate` 会独立复算并断言）。
- **守恒**：`conservation_ok=True`（residual=0）。
- **哈希链**：`chain_ok=True`。
- **门禁汇总**：`gate_ok=True`（详见 gate.txt）；测试通过数见 `pytest_report.txt`（obs 专属 / 全量）。

## 四、门禁说明（G1–G7）

- G1 边界：观测层只读白名单（`tests/test_obs_boundary.py`，AST 断言）。
- G2 复现：重放状态哈希相等、`metrics()`/`census` 两次**字节相等**。
- G3 冻结：重放/观测 `llm_calls == 0`；`llm_judged_metric_count == 0`；F 类单列。
- G4 守恒：货币守恒式(1)。
- G5 稳定：无哈希链断裂/无回滚。
- **G6 黄金基线 / 事件量-分布回归**：区分「跑完了」与「真的在运转」——`SYSTEM_ERROR == 0`；事件量 ≥ 基线×0.8（**增长通过、塌陷失败**）；`TIME_MARK == ceil(rounds/ROUNDS_PER_DAY)`（84 回合=7，每跨日一条；**停摆最早信号是 `TIME_MARK=1`**）；关键事件族（MEMORY_WRITE/ACTIVITY_STARTED/ACTIVITY_COMPLETED/NEED_UPDATE）> 0。基线冻结于 `code/obs/golden_baseline.json`，随功能集演进更新（更新须在 commit message 说明原因）。
- **G7 schema 合约（阻塞 FAIL）**：任一事件缺 15 §5 规定字段 / 锚点悬空即 FAIL，并在失败信息给出最小复现（首例事件 seq/type/field + 日志行号 + 复现命令）。原则：**缺失/不匹配一律硬报错，不得静默容忍**。

## 五、备注 / 待补

- ② 段：rule-based N=20×84，life 修复 + GOAL_SET 扁平 + T45 活动模板上线。③ 段（真实 LLM）待 LLM_API_KEY 注入后补。
