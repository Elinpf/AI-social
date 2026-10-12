# T224 证据：人格与记忆第一批（睡眠离线窗 + 遗忘三级 + 人格抗漂移）

> 作者：persona-life-designer｜代码提交 **`851ef28`**｜基线文档：`v2/refs/persona-memory-engineering.md`（T205）
> 口径：**Fork B（已定案）—— 按"可审计"写，不按"逐位重放"写**（全量日志 + 种子化随机 + sha + 命令）。

## 1. 范围与边界（本批**只做确定性核心**）
**已实现（新文件，未碰 `life/agent.py`）**：
| 文件 | 内容 |
|---|---|
| `code/life/forgetting.py` | 定点保留度 `retention_permille()` + 强度 `strength_permille()` + **保护名单** `is_protected()` + 三级 `classify()`/`plan_forgetting()` + 固化分组 `consolidation_groups()` |
| `code/life/persona_drift.py` | 锚定不写回 + 有界更新 `bounded_update()`（α 均值回归 + Δ 夹取）+ 漂移度量 `drift_permille()`/`drift_dims_permille()`/`within_bounds()` + 指纹 `persona_fingerprint()`(PF0)/`dynamic_fingerprint()`(PF(t)) |
| `code/life/sleep_window.py` | 睡眠离线窗入口 `run_sleep_window()`（固化→遗忘→人格漂移；产出**待发事件**，交调用方落账） |
| `code/config/life_v2.json` | 参数（**默认关**），已纳入 `engine_version` 指纹（`engine/version.py::FINGERPRINT_FILES` 增 `life_v2.json`） |
| `code/life/tests/test_t224_*.py` | 22 个单元测试 |

**未做（按 Leader「同一文件同一改动者」规矩 + T35/M2b 重构中）**：
- 未改 `life/agent.py`（睡眠窗口**挂载点接线**待 T222 释放 `agent.py` 后与 life-layer-dev 约时再接）；
- 未改 `engine/events.py::EVENT_TYPES` / `replay.apply_event` 折叠器（事件 schema 已由 sim-engine-stats-architect 登记 `08 §1.2 S`，commit `d5dfb69`；代码注册待重构收敛后补）。
→ **因此"引擎级 N=10×84 drift 不越界"的端到端证据留到接线后**；本批给**模块级降规模 harness**（§4）。

**成本结论**：本批 **新增决策类 LLM 调用 = 0**（模块纯整数、无 LLM import；测试 `test_no_llm_dependency` 守护）。

## 2. 门禁结果
命令：`cd code`
| 门禁 | 命令 | 结果 |
|---|---|---|
| 术语 | `make lexicon-gate` | **退出 0，新增违规条目数 0** |
| 导入边界 | `lint-imports` | **Contracts: 9 kept, 0 broken** |
| 本批单测 | `python -m pytest life/tests/test_t224_forgetting.py life/tests/test_t224_persona_drift.py life/tests/test_t224_sleep_window.py -q` | **22 passed** |
| 全量 | `python -m pytest -q` | **415 passed, 1 failed**（见下） |

**唯一失败 = 非本批**：`tests/test_obs_metrics.py::test_obs_gate_on_kernel_log` —— 断言观测门禁名仍含 `metrics_bitwise_equal`/`census_bitwise_equal`，而 `code/obs/gate.py`（**别人未提交的 Fork B 改名中**）已改（`git status` 显示 `code/obs/*` 均为 ` M`）。**与 T224 文件无关**，待 obs-stats-dev 收口 Fork B 后自然消失。

> ⚠️ 过程记录：一次全量跑批曾出现 33 failed / 6 errors，根因是 **inode 打满（`IUse% 99%`，`OSError: No space left on device`）**，非代码缺陷；空间回落后重跑即恢复。

## 3. 保护名单（本批最关键）证据
硬要求：**重要记忆只降级、永不 merge/drop**。
- `test_protected_high_importance_never_dropped_or_merged`：`importance=9` 且同 subject 有兄弟（未保护者会 `merge`）→ 判 `demote`。
- `test_protected_variants_never_merge_or_drop`：5 类保护（importance≥7 / access≥3 / |emo|≥6 / `kind∈{semantic,reflection}` / 被反思引用）在 `round=100000`（极老）下**全部 `∈{keep,demote}`**。
- `test_protected_memory_only_demoted_in_events`：睡眠窗口事件流中，受保护记忆 **level 恒为 `demote`**。

## 4. 降规模验证（N=10 × 84 = 1 模拟周；合成 harness，不含引擎接线）
命令：见 `v2/evidence/` 记录（`python -` 内联脚本，import `life.{forgetting,persona_drift,sleep_window}`；参数取自 `config/life_v2.json` 并置 `enabled=true`）。

| 指标 | N=10 × 84 | N=10 × 1000（延长，标 `【未验证】`） | 阈值 | 结论 |
|---|---|---|---|---|
| `max_drift_permille` | **2** | 2 | ≤150 | ✅ |
| `max_dim_drift_permille` | **10** | 10 | ≤200 | ✅ |
| `agents_out_of_bounds` | **0** | 0 | =0 | ✅ |
| `protected_merge_or_drop_violations` | **0** | — | =0 | ✅ |
| `forget_actions` / `drop` | **230** / 80 | — | — | 遗忘生效 |
| `consolidate_groups` | **10** | — | — | 固化生效 |

> 说明：漂移事件按"每周 ≤k 次"**稀疏**注入（每 12 回合 +1）——正是设计里的冷却/门槛前提；若每步都注入则会超出 `drift_dim_max`（**这是保护机制的设计前提，非缺陷**）。
> **【未验证】**：真实引擎接线后的 N=10×84、以及**1000 回合**长期判据；本次 1000 回合为**合成 harness**，不等于引擎级 `drift` 证据。

## 5. 配置与指纹（"默认关"≠"没影响"）
- 新配置 `code/config/life_v2.json`：`sleep.enabled=false`、`forgetting.enabled=false`、`persona_drift.*`（全部默认关）。
- `engine/version.py::FINGERPRINT_FILES` 已加入 `life_v2.json` → **默认关也进指纹**，切换配置可被复现输入审计捕获。
- 事件 schema 已登记 `08 §1.2 S`（`SLEEP_STARTED/COMPLETED`、`MEMORY_CONSOLIDATE`、`MEMORY_FORGET`、`PERSONA_DRIFT`；`PERSONA_FINGERPRINT` 为快照非事件）。

## 6. 未验证 / 待办
- `【未验证】`：遗忘曲线形状与系数（`h0/w_*/θ_*`）为**工程初值**，待沙盒标定；`1000 回合`长期漂移；引擎级端到端。
- **待办（接线）**：① `life/agent.py` 睡眠点调用 `run_sleep_window`（待 T222 释放）；② `engine/events.py` + `replay.apply_event` 注册新事件折叠（待重构收敛）；③ 观测指标 `metrics.life.memory/persona`（T9/obs 侧）。
