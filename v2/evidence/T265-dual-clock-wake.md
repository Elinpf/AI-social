# T265 · 乙+ 双时钟落地证据（个体决策节拍 + 唤醒集 W1–W10 + DECIDE 门控）

> 任务：T265（sim-system-architect）｜ 依据：用户 2026-10-12 14:57 批准「乙+ 双时钟」+ `v2/refs/time-model-redesign.md`
> 口径：世界**结算节拍=回合不变**；新增**个体决策节拍**。`wake.enabled` **默认 false（行为不变）**。
> 证据纪律：实测给 seed/规模/命令；外推标【未验证】；**不宣称"根治 R1"**（T263 已证伪）。

---

## 1. 交付物（改了哪些文件）

| 文件 | 变更 | 归属 |
|---|---|---|
| `code/engine/wake.py` | **新增**：确定性纯函数 `compute_wake_set`（W1–W10）、`wake_config/enabled` | T265 |
| `code/engine/kernel.py` | `phase_route` 计算唤醒集 + 发 `WAKE/IDLE`；`phase_decide` **仅对被唤醒 Agent `step()`** | T265 |
| `code/engine/events.py` | 登记 `WAKE`/`IDLE` 事件类型（08 §1.2 S） | T265 |
| `code/engine/replay.py` | `WAKE/IDLE` 加入 no-op 折叠（审计事件，不改世界状态） | T265 |
| `code/config/policy.json` | 新增 `wake` 开关块（`enabled=false` 默认 + `triggers.{W1..W10}` + `base_cadence_rounds=12`） | T265 |
| `code/tests/test_wake.py` | **新增** 11 项（单元 + 门控 + e2e） | T265 |

**未触碰**（T264/kernel-dev 独占）：`engine/perceive.py`、`life/visibility.py`、`contracts/visibility.py`、`orchestration/integration.py`。→ **同文件不跨人交错改**。

---

## 2. 契约遵守（逐条对齐 Leader 7 条边界）

1. **世界结算节拍=回合不变**：`run_round` 六阶段、84 回合/周、每回合 P3.5/P4 结算**未改一行**。✔
2. **个体决策节拍**：未到期/未唤醒者**不 `step()`**（安静）。✔
3. **与 T264 零文件重叠**；唤醒集只用 `state.event_index`（**不做可见性判定**，不引入第四份口径）。✔
4. **08 登记先行**：`WAKE/IDLE` 已由 T8 登记（commit `103973a`）后才接线。✔
5. **独立开关**：`wake.enabled`（默认 false）+ `triggers.{W1..W10}`（W6 默认 true 可关）。✔
6. **全量日志可审计**：`WAKE`（每被唤醒 Agent 一条）+ `IDLE`（每回合一条全局聚合）落账本；`seq` 全局全序不变。✔
7. **不宣称根治 R1**（见 §5）。✔

---

## 3. 测试

- **新增** `tests/test_wake.py`：**11 passed**（W1/W2/W6/W9 触发器、主因优先级、门控开/关、e2e 发 `WAKE/IDLE` 且重放一致 + 守恒）。
- **全量回归**：`pytest tests -q` → **473 passed**（无回归）。

---

## 4. 开/关对照（N=20×24，mock，seed=42，`ulimit -v 6G`）

命令：`PYTHONPATH=code python /tmp/t265_ablation.py`（脚本仅用 `build_world` + 手动 `run_round`，不改 `code/`）

| 指标 | **OFF（默认）** | **ON（wake.enabled=true）** |
|---|---|---|
| 墙钟 | 28.9 s | 32.0 s |
| 事件数 | 46,087 | 46,530 |
| `state_hash` | `baac3e45…` | `aa6d2529…`（**变**，行为变更，预期） |
| `WAKE` 事件 | 0 | **387** |
| 未唤醒 agent-回合（`IDLE.idle` 求和） | 0 | **110** |
| 唤醒率 / 静默率 | — | **77.9% / 22.1%** |
| 不变量 `WAKE + idle == Σtotal_agents` | — | **✔ True** |

**DECIDE 门控直接证据**（`test_wake.py`）：
- `test_gate_closed_when_no_trigger_fires`：无触发器命中 → 3 个假 stepper **step 次数=0**；
- `test_gate_open_when_w1_fires`：W1 命中 → 各 **step=1**；
- `test_gate_off_when_disabled_all_step`：默认关 → 各 **step=1**（行为不变）。

---

## 5. 诚实解读（**防报喜**）

1. **mock 下没有变快**（28.9→32.0 s，+3.1s）：因为 mock 无 LLM 延迟，而唤醒集每回合要扫 `event_index`（O(账本长)）→ 净增开销。**真实收益（少调 LLM 的延迟）在 mock 下量不出来**。
2. **唤醒率 77.9% → 门控只跳过 22.1% 的 agent-回合**：**与 T263 预测完全一致**——「N 大时每回合几乎总有事发生 → 唤醒几乎恒真」。→ **对 CPU/LLM 的节省有限**；本机制的**真实价值 = 语义拟人 + 并发错峰 + 为"异步分时对话"铺路**，**不是省成本**。
3. **`state_hash` 改变 = 行为变更**，属预期；配 `wake.enabled=false` 默认关，故不影响现行基线。
4. **【未验证】**：真 LLM 下的耗时/成本变化（需真 provider）；N>20 的表现（**>N=20 要先报 Leader + 设内存上限**，宿主今日已 OOM 一次）。
5. **fingerprint**：新增 `policy.wake` 键使 `engine_version` 指纹**变更** → **T236 这版基线会在 T265 落地后过期**（Leader 已预登记为"第二次重冻"，非返工）。

---

## 6. 与 T264（差分门禁）的关系

- 三份 `visible_events` 差异清单与收敛由 **T264 独占**（`contracts/visibility.py` + `tests/test_visibility_single_source.py`）；**本任务不重复造**。
- 本任务保证：**唤醒集不新增可见性口径**（只按事件目标字段/共处场所判定，不做 scope 过滤）。

---

## 7. 后续（待 Leader 排期）

- **【未验证】真 LLM 开/关对照**（才能量出"少决策"的墙钟/成本收益）；
- 若启用：需与 T236 重冻联动、更新 canonical；
- 差分门禁（T264）落地后，回归确认 `WAKE/IDLE` 不影响可见性语义。

---

*（T265 证据结束 — sim-system-architect；mock 实测 + 全量回归通过；未验证项已标注）*
