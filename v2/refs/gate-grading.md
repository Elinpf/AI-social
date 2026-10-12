# 门禁分级表（单一来源）——Fork B 后的「必须 / 诊断 / 已废弃」v3

> 文档类型：验收侧门禁分级（**单一来源**，合并实现侧「确定性：可松 vs 红线」）｜作者：delivery-reviewer
> 依据：Leader 2026-10-12 裁决 **Q-12.1**——**「放开"必须可复现"，保留"可被复算"」**：
> - ✅ **保留（必须）**：`replay(log)` 代码确定性（同日志→同状态，审计地基：哈希链/`turn_seal`/异常回滚 D1/IF-2c）、**全量日志 + 随机种子化 + 每产物 sha256 + 生成命令**。
> - ❌ **放开（降级）**：「每次重跑输出逐位相等」**不再作门禁**；`metrics()`/`census`/replay 的**字节/哈希相等断言降为诊断**。
> 状态：**v3 定稿（2026-10-12）**：obs 终校通过 —— commit `d9cb79f` 落地 must/diagnostic 拆分 + 死桩删除 + 反向验证测试；本人已独立核验（见 §1.1 前注）。
> 口径唯一不复制：分级**只引用** `code/obs/gate.py` 与 `code/obs/golden_baseline.json`，不另立定义。

---

## 0. 分级定义 + 硬语义

| 分级 | 含义 | 影响 CI 退出码？ |
|---|---|---|
| **必须（gate）** | 不通过即**阻塞交付** | ✅ 是（非 0） |
| **诊断（diagnostic）** | **执行+打印**进报告，但**不判 FAIL** | ❌ **否（恒 0）** |
| **已废弃（abolished）** | 从验收流程移除 | — |

> **F4（写死）**：诊断级**不得进入 `obs gate` 的 `gate_ok`、不得影响任何退出码**——否则"降级"是空话。
> **F5（obs 提醒）**：每条标**实际命令 + 期望退出码**，便于核对"降级是否真落地"。
> **反假绿**：「未跑」不得算通过（`ci_gate.sh` rc=3 范式）。

---

## 1. 验收侧门禁分级表

| # | 门禁 / 断言 | 实际命令 | 期望退出码 | 分级 | 说明 |
|---|---|---|---|---|---|
| 1 | 全量日志 + seed/sha256/命令 | `obs evidence` / 证据包 | 0 | **必须** | Q-12.1 保留红线 |
| 2 | 边界契约（`import-linter`） | `lint-imports` | 0（**全 KEPT / 0 broken**；条数随契约演进，**不写死**） | **必须** | 观测只读 / life 不 import kernel 实现 / kernel 零反向 / contracts 纯类型 |
| 3 | 单测（内核/冻结/obs） | `python -m pytest -q` | 0 | **必须** | 含哈希链 / D1 回滚 / 守恒 / RNG / 冻结 |
| 4 | G7 `schema_conformance` | `python -m obs gate --log LOG` | 0 | **必须** | 数据契约 |
| 5 | G4 守恒 | 同上 | 0 | **必须** | 独立于复现（Q1 待决） |
| 6 | G5 `llm_judged_metric_count==0`（C3） | 同上 | 0 | **必须** | **C3 未放开** |
| 7 | G3 `llm_calls_zero` + obs 只读边界 | 同上 / `lint-imports` | 0 | **必须** | 回归样本：`obs/calibration.py`、`obs/truth_from_consequences.py`、`obs/admission.py`（仅 stdlib） |
| 8 | `provider_guard`（真 LLM 跑**无 mock 混入**） | `python -m obs llm-cost --log LOG --require-provider openai_compat` | 0 | **必须** | **不在 `obs gate` 的 `ok` 内，属独立门禁**（独立命令 + 独立退出码）；语义 = run 的 provider 校验，与日志结构门禁不同源 |
| 9 | 「世界真在运转」 | `python -m pytest tests/test_run_health_gate.py` | 0 | **必须** | 防"跑完但停摆" |
| 10 | G6 分布回归 / 黄金基线 | `python -m pytest tests/test_obs_golden_gate.py` | 0 | **必须** | 分布守卫非字节门；基线**仅在 schema/feature 变更后重冻**（F1/F2 已确认） |
| 11 | 术语棘轮 | `make lexicon-gate` | 0（0 新增违规） | **必须** | 口径唯一 |
| 12 | 前端回归 | `make ci` | 0 / 1 / **3(=SKIP≠PASS)** | **必须** | smoke + 真渲染 |
| 13 | 降级可观测（M6） | `obs gate` / 报告 | 0 | **必须** | `DEGRADE`/`degraded` 落事件，禁静默 |
| 14 | G2a `metrics()` 字节相等 | `obs gate`（诊断段）/ `pytest test_obs_repro_gate` | **恒 0** | **诊断** | Fork B 降级 |
| 15 | G2b `census` 字节相等 | 同上 | **恒 0** | **诊断** | 同上 |
| 16 | G2c replay 哈希 / 首跑==重放 | 同上 | **恒 0** | **诊断** | Leader：同日志可复算**保留为诊断** |
| 17 | 重放**代码**确定性（不读墙钟/网络/哈希序） | 代码契约 + 评审 | — | **必须（能力）** | Q-12.1：审计地基，不能丢；一致性由 #16 诊断观测 |

> ✅ **【已闭合 · 2026-10-12】原「假降级」已修复并独立核验**：obs commit `d9cb79f` 在 `obs/gate.py` 落地 **`gates`(must) 与 `diagnostics` 分离**——`ok = all(g["ok"] is not False for g in gates)`（**诊断不进 `ok`**）、`return {ok, gates, diagnostics}`、CLI 打印 `[DIAG]` 且 `exit 0 if ok`。**本人实测核验**：`run_gates` 现为**单一定义**（211 行，死桩已删）；must = `llm_zero`/`llm_judged_zero`/`conservation`/（`schema`）/（`distribution`）；diagnostic = `metrics_bitwise`/`census_bitwise`；反向验证测试 `tests/test_obs_repro_gate.py::test_g2_diagnostic_does_not_block_ok`（monkeypatch G2a→FAIL，断言 `ok` 仍 True）**在位**。
> **注（provider_guard 已闭合）**：`provider_guard` **不在** `run_gates` 的 must `gates` 内——它是 **`obs llm-cost --require-provider <p>`**（**独立命令 + 独立退出码**）。故 #8 标"**必须、但由另一扇门拦**"（命令/退出码已写清 → 非"表说必须、代码没拦"）。**不并入 `obs gate`**（语义与日志结构门禁不同源）。
> **历史留痕**：修复前 `run_gates` 曾**重复定义**（68 行死桩 + 214 行真身），死桩**无 `return`**（被覆盖、从未执行）；obs 已删除并提供**行为等价论证**（见 commit `d9cb79f`）。

### 1.1 已废弃

| # | 项 | 说明 |
|---|---|---|
| X1 | 跨 run / 同 seed 两跑逐位相等作**门禁** | Fork B 移除（纯确定性金额/死亡/结算仍确定，但不作整体 FAIL 依据） |
| X2 | `replay_parity`/`state_hash` 作**硬 FAIL** | 降 #16 诊断（保留观测，只移除 FAIL 权限） |
| X3 | 旧卡量口径 `22,987 / 616 / 567 / 546` | 废弃；现行 **23,185 / 612** |

---

## 2. 实现侧「确定性：可松 vs 红线」——**两栏分离，不混表**（obs 修订，commit `d1b4d3d`）

### 2.1 红线（**不可妥协**）

| 红线 | 内容 |
|---|---|
| R-A | **唯一写入口 Arbiter + 串行 append（P6）**：**并行的是"计算"，不是"提交"** |
| R-B | 事件按**确定的全局全序**写 `seq`；守恒**可验**；日志**全量** |
| R-C | 随机**种子化**；每产物记 **sha + 生成命令** |

> **定性结论（Leader 采纳）**：原「妥协②分片并行写」**不是妥协，是红线**——已由 obs 移出妥协清单。

### 2.2 可松（Fork B 放开）

| 妥协项 | 分级 | 约束 |
|---|---|---|
| ① 回合边界强同步 → 自由推进 | 可放开 | 事件仍按确定全局全序写日志 |
| ② 计算并行（非提交） | 可放开 | 提交串行（R-A） |
| ③ 调度顺序按 `agent_id` 全序 → 可打散 | 可放开 | **实际顺序须落日志** |
| ④ stagger 取 `hash(agent_id)` → 动态避峰 | 可放开 | seq 分配与遍历顺序解耦或记录 |

---

## 3. 待对齐 / 风险（F1/F2 已由 obs 确认）

- **F1/F2 ✅ 已确认**：G6 基线**仅在事件 schema / feature 集变更后重冻**；commit message 写明原因 + 记 sha/命令；`auto_match` **显式钉 baseline id**（防匹配旧基线→假红）。
- **F3**：#14–#16 降诊断后**仍须打印进报告**（保回归体检）。
- **F5**：其他文档「逐位一致」口径已按 Leader 要求**全库回写**——见 `v2/refs/forkb-rewrite-log.md`。

---

*（门禁分级表 v3 — delivery-reviewer；待 obs-stats-dev 终校）*
