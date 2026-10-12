# 质量门禁与测试策略 v1

> 归属：sandbox-test-lead（测试侧负责人）｜ 日期：2026-10-12
> 口径真源：`code/obs/*`（指标/普查/门禁）、`glossary/lexicon.json`（术语）、`code/.importlinter`（边界）。**本文不另立第二套数**。
> 与 `delivery-reviewer`（T218 门禁分级表）对齐；**Fork B 已定**：不把「逐位可复现」当验收口径（见 §7）。
> 定位（Leader）：质量系统**不是为了拦住探索**，而是守住两件事——**红线不被破**、**结论可被独立复算**。**只在真出事时响。**

---

## 0. 结论速览

- 现有门禁 **10 条**（§1），当前**全绿**：`pytest` 353 passed ｜ `lint-imports` 10 kept/0 broken ｜ `obs gate` G2–G7 PASS ｜ `make lexicon-gate` exit=0 ｜ 前端 `ci_gate` PASS（smoke + 真渲染）｜ `make art` PASS（幂等，git 无新增变更）。
- **每条门禁都做了反向验证**（§4，RV1–RV6 实录）：**故意弄坏 → 确实变红**。
- 四类「假」各配对策与可跑例子（§3）。
- **一处真实「假绿」风险**（必须修）：`obs gate G6` 在 `--baseline auto` **未命中时静默 skip（ok=None）**，会被当成通过 → 停摆世界可能漏检（§3.1 假绿·F2）。
- **P0 前置**：安装 `pytest-cov` 才能上覆盖率棘轮；当前用「测试/契约/门禁计数 + 模块-测试矩阵」作基线（§2）。

---

## 1. 现有门禁盘点（逐条：防什么假 / 防不到什么）

| # | 门禁 | 命令 | 防什么假 | **防不到什么**（已知盲区） |
|---|---|---|---|---|
| G0 | **单元/集成测试** | `cd code && python3 -m pytest -q` | 逻辑回归；契约/守恒/hashchain/重放/调度/预算 | 覆盖不到的模块（无 cov 计量）；「世界停摆但全绿」旧盲区由 G8/G6 补 |
| G1 | **import 边界契约**（10 条） | `cd code && lint-imports` | 架构腐化：内核零反向依赖、life 不碰内核、obs/narrative/frontend 只读、plugin 仅 stdlib | 运行期**动态** import、字符串反射；ignore_imports 白名单被滥用 |
| G2 | **术语棘轮** | `make lexicon-gate` | 命名漂移（同一物多叫法，如 `OFFER`→`OFFER_CREATED`）；仅**基线外新违规**报错 | 语义「同名不同义」；.md 中被判为「提及」的合法引用不罚（需人工判） |
| G3 | **pre-commit 钩子** | `.git/hooks/pre-commit` | 把 G2 提前到**提交前**，防漏网进库 | `--no-verify` 可绕过；仅覆盖 lexicon，不跑 pytest/lint |
| G4 | **obs gate G2–G7** | `python -m obs gate --log <log> --baseline auto` | 见 §1.1（观测层 7 项） | G6 未命中基线时静默 skip（假绿 F2）；F 类指标正确性靠 07 口径 |
| G5 | **前端双门禁** | `bash code/frontend/tools/ci_gate.sh` | ① smoke（PIXI mock 快检）② 真渲染（Chromium/SwiftShader：pageerror/空画面/图层数） | **像不像 / 好不看**（主观，§6）；SKIP(rc=3) 不等于 PASS（结构上区分） |
| G6 | **美术管线幂等** | `make -C code art` | 「图旧资产新」脱钩：JSON `distinct_colors` == **落盘 PNG 实测**；剪影/角色 gate；事件卡空槽 | 美术品味；配色美观度（主观） |
| G7 | **版本指纹** | `pytest tests/test_version_fingerprint.py` | config/资产变更未进 `engine_version` | 指纹算法本身的正确性（靠 G0） |
| G8 | **「世界真的在运转」** | `pytest tests/test_run_health_gate.py` | **停摆静默回归**：`SYSTEM_ERROR==0`、`TIME_MARK` 日边界数、关键事件族 >0、事件量下界 | 阈值标定（下界=防塌陷，非质量上限） |
| G9 | **复现门禁** | `pytest tests/test_obs_repro_gate.py` | metrics/census 两次字节相等、`llm_calls==0`、守恒、CLI 退出码；内核可用时重放哈希 | **Fork B 下**：跨跑逐位一致**不再是**验收口径（§7） |
| G10 | **黄金基线冻结** | `python -m obs golden-freeze` | 从「已验证良好运行」固化 G6 基线（`n3/n10/n20_week_seed42`） | 基线会「过期」（假阻塞，§3.4） |

### 1.1 obs gate 内部 7 项（口径真源 `code/obs/gate.py`）

| 门禁 | 名 | 断言 | Fork B 处置 |
|---|---|---|---|
| G2a | `metrics_bitwise_equal` | `metrics()` 两次规范 JSON 字节相等 | **降为诊断**（§7） |
| G2b | `census_bitwise_equal` | `semantic_census()` 两次字节相等 | **降为诊断**（§7） |
| G3 | `llm_calls_zero` | 观测计算过程 `llm_calls==0` | **保留**（纯度红线） |
| G5 | `llm_judged_metric_count_zero` | 门禁指标集内 F 类计数=0 | **保留** |
| G4 | `money_conservation` | 货币守恒残差=0 | **保留（阻塞）** |
| G7 | `schema_conformance` | 缺字段/锚点悬空 → **硬报错** | **保留（阻塞）** |
| G6 | `distribution_regression` | 事件量 ≥基线×0.8、`SYSTEM_ERROR=0`、`TIME_MARK`=日边界数、关键族>0 | **保留（阻塞）** |

---

## 2. 覆盖率基线 + 棘轮（只许升不许降）

**P0 前置**：`pytest-cov` 当前**未安装** → 先装（隔离 env），再启用行覆盖率棘轮。在此之前用**可度量的计数基线**代替：

| 指标 | 当前基线（2026-10-12） | 棘轮规则 |
|---|---|---|
| 测试用例数 | **353** | 不得减少；新增模块必须**同 PR 带测试** |
| 测试文件数 | **42** | 同上 |
| import 契约数 | **10 kept / 0 broken** | 契约只增不减；breaking 必须 0 |
| obs 门禁项 | **7**（G2–G7） | 只增不减 |
| 术语新增违规 | **0** | 恒为 0 |
| 前端门禁 | **2**（smoke + render） | 只增不减；SKIP≠PASS |
| 美术门禁 | **3**（剪影/角色/事件卡）+ 自洽断言 | 只增不减 |

**必须覆盖（红区）**：`engine/*`（时钟/裁决/hashchain/守恒/RNG/replay）、`contracts/*`（类型与协议）、`obs/*`（口径）、`freeze/*`（LLM 冻结）、`code/.importlinter` 全部边界。
**允许豁免（须写明理由）**：`frontend/tools/*`（开发工具，非产品路径）、`license`/文档、生成型脚本（`gen_*.py`）——豁免项**不参与覆盖率门禁**，但其**产物**由 G5/G6 覆盖。

**模块 → 测试存在性矩阵**（无 cov 时的替代证据）：
`engine`→22 个 test ｜ `obs`→17 ｜ `life`(activity_templates/e2e) ｜ `freeze`(test_freeze) ｜ `contracts`(被 lint-imports + conftest 覆盖) ｜ `narrative`(test_narrative_weights) ｜ `plugin`(test_plugin_arch) ｜ `orchestration`(被 test_run_health_gate/e2e 覆盖)。
**缺口**：`plugin/*`、`orchestration/*`、`devtools/*` 尚无独立测试文件（`plugin` 有 `test_plugin_arch`）→ 列为 P1 补齐。

---

## 3. 四类「假」的测试对策（各附可跑例子）

### 3.1 假绿（门禁全绿但未生效）
| # | 场景 | 对策 | 可跑例子 |
|---|---|---|---|
| F1 | 门禁**没跑**被当通过 | 退出码三分：`ci_gate.sh` 用 **0=PASS / 1=FAIL / 3=SKIP**，SKIP **不算** PASS | RV5 证明 runner 会把失败传播为 rc=1 |
| F2 | **G6 未命中基线静默 skip**（`ok=None` 被当通过） | **P0 修复**：`obs gate` 在 `--baseline auto` 未命中时**报警并 rc≠0**（或要求显式 `--baseline none` 才允许 skip）；在报告里把 `skipped` 单列 | `python -m obs gate --log <任意新log> --baseline auto` 观察是否静默跳过 |
| F3 | 生成物与「数字」脱钩 | `make art` **自洽断言**：JSON `distinct_colors` == **落盘 PNG 实测**（不靠人记得重跑） | `make -C code art` 内 `[art] 3/4 自洽断言` |

### 3.2 假红（时序/环境导致）
| # | 场景 | 对策 | 可跑例子（实录） |
|---|---|---|---|
| F4 | **陈旧 `__pycache__` 导致测试假红** | 门禁/CI 前置 `find -name __pycache__ -exec rm -rf`；写入 pytest 缓存清理；提交前不依赖本地 .pyc | **RV6 实录**：注入后回滚，未清 pyc 仍红；清 `engine/__pycache__` 后 `4 passed`（`canonical_json({'x':1/3})→{"x":0.333333}`） |
| F5 | 真渲染门禁缺浏览器/服务导致假红 | 明确 **rc=3 SKIP**（不是 FAIL）；CI 里 SKIP 要显式标记「依赖缺失」 | `bash code/frontend/tools/ci_gate.sh` 的 SKIP 分支 |
| F6 | 时序/并发抖动 | 随机只走种子化 RNG；遍历/排序有全序 tie-break；禁墙钟进入判定 | `pytest tests/test_rng.py`、`test_hashchain.py` |

### 3.3 同名不同义（一个东西两个数）
| # | 场景 | 对策 | 可跑例子 |
|---|---|---|---|
| F7 | 口径复制（两套数） | **口径唯一不复制**：指标真源只在 `code/obs/*`；其他处只**引用**不重算 | `devtools` 只读复用 `obs.*`（import 契约强制） |
| F8 | 量纲/层级混淆 | 文档化「计数层级」；门禁输出显式标注 | `lexicon-gate`：**行命中(50) vs 条目数(0)** 分两栏（其输出已标注「两者不可直接相加」） |
| F9 | 语义不同名 | 术语棘轮：同一物必须同名（`OFFER` → `OFFER_CREATED` 等） | `make lexicon-gate`（RV2 实录命中 `code/_rv_lexicon_probe.py:1:11`） |

### 3.4 假阻塞（报过期状态）
| # | 场景 | 对策 | 可跑例子 |
|---|---|---|---|
| F10 | 黄金基线过期（世界合理演化后被旧基线判红） | 基线**随功能集演进**更新，且**更新须在 commit message 说明原因**（`golden_baseline.json._policy`）；`min_event_ratio` 只防塌陷、不设上限 | `obs.golden.compute_baseline` / `python -m obs golden-freeze` |
| F11 | 门禁依赖残留进程/端口 | `ci_gate.sh` 先探测 `:8848`，无则自起服务 | `ss -ltn | grep :8848` |

---

## 4. 反向验证证据（RV1–RV6 实录 · 故意弄坏 → 确实变红）

> 原则：**一个不会报警的守卫等于没有守卫。** 每条门禁附一次「注入 → 变红 → 还原」实录。全部在**临时文件/临时改源码**上做，**已还原，git 无新增 diff**。

| RV | 门禁 | 注入 | 结果（实录） | 还原 |
|---|---|---|---|---|
| **RV1** | `lint-imports` | 新建 `code/life/_rv_probe.py`：`from engine import state` | `Contracts: 8 kept, 1 broken` · `life._rv_probe -> engine.state (l.1)` · **exit=1** | 删除探针；`lint-imports` 复跑 10 kept/0 broken |
| **RV2** | `make lexicon-gate` | 新建 `code/_rv_lexicon_probe.py`：`STATUS = "DECEASED"`（无提及标记） | `新增违规(条目数): 2` · `code/_rv_lexicon_probe.py:1:11 [DECEASED] -> dead` · **exit=2** | 删除探针；复跑 exit=0 |
| **RV3** | `obs gate G7` schema | 既有负例测试：注入未知类型/缺字段/锚点悬空 | `4 passed`（`test_preflight_unknown_type_hard_error` / `missing_field` / `dangling_observation_anchor` / `g7_schema_conformance_fail_with_repro`）→ **门禁确实抛错** | 无需还原（只读测试） |
| **RV4** | `obs gate G6` 分布 | 合成「停摆日志」（仅 1 条 `TIME_MARK`，无 `ACTIVITY_COMPLETED`）+ 合成基线 | `G6 ok=False`，problems= `事件总量 1 < 0.8×基线 1000` / `TIME_MARK=1（预期 7）` / `ACTIVITY_COMPLETED=0（要求 >0）` | 临时脚本 `/tmp/rv4_g6.py`，无仓内改动 |
| **RV5** | 前端 `ci_gate` runner | `GATE_PY=/tmp/rv_fail_gate.py`（强制 exit 1） | `CI GATE: FAIL` · **exit=1**（SKIP 分支不触发） | 无仓内改动 |
| **RV6** | `pytest` | `engine/canon.py` 注入「去掉浮点 6 位舍入」 | `2 failed`（`test_float_rounded_to_6`、`test_equivalent_to_freeze_canonical`）**exit≠0** | `git checkout` 还原；**并发现假红 F4**（清 `__pycache__` 后 4 passed） |

**附加正向基线**（证明门禁现在是绿的、不是空跑）：
- `cd code && python3 -m pytest -q` → **353 passed in 46.32s**
- `cd code && lint-imports` → **Contracts: 10 kept, 0 broken**（130 files / 301 deps）
- `python -m obs gate --log logs/t59_mock84.jsonl --baseline auto` → **G2–G7 全 PASS，GATE PASS**（`money_conservation residual=0`、`schema anomalies=0`、`TIME_MARK=7=预期`）
- `bash code/frontend/tools/ci_gate.sh` → smoke ok + 真渲染 `GATE PASS`（`placeLayer=17`）
- `make -C code art` → PASS，`batch_id=f21015494501090d`（60 files），**git 无新增变更（幂等）**

---

## 5. 改动 → 门禁矩阵（避免「全跑太慢、挑跑漏测」）

| 改动区域 | 必跑 | 可选/相关 |
|---|---|---|
| `engine/*`（内核/裁决/hashchain/RNG） | G0(pytest) · **G1** · **G4-G6/G7** · **G8** · G9 | G6(art 无关) |
| `life/*` | G0 · **G1** · G4-G6 · **E2E** | G8 |
| `freeze/*`（LLM 冻结） | G0 · **G1** · **G3**(llm=0) · G9 | G4 |
| `obs/*`（口径真源） | G0 · **G1** · **G4** · G8 | G10 |
| `contracts/*` | G0 · **G1** · G7 | G4 |
| `frontend/*` | **G5**（smoke+render） · G1 | G6(事件卡) |
| `frontend/assets` 或美术脚本 | **G6**（`make -C code art`） | G5 |
| `narrative/*` | G0 · **G1** | G4 |
| `plugin/*` · `orchestration/*` | G0 · **G1** | G8 |
| `glossary/*` · 任意 `.md`/命名 | **G2**（lexicon） · **G3**（pre-commit） | — |
| `config/*` · 资产清单 | **G7**（version fingerprint） · G4 | G8 |
| **发版前**（release-engineer） | **全部** + G10 + 前端/美术门禁 + `obs evidence` 证据包 | — |

**最小充分集**：改一个区域 = 跑该行「必跑」即可；**跨区域改动取并集**。CI 建议：PR 按 paths 触发上表。

---

## 6. 必须人工（别把主观伪装成自动门禁）

| 项 | 为什么必须人工 | 支撑（自动化只做「可判定部分」） |
|---|---|---|
| 渲染「像不像」（像素风/构图/可辨性） | 审美主观 | 自动化只保证「无 pageerror / 图层数 / 资产路径」；观感由 art-director 截图自检 |
| 故事「好不好」、事件有意义否 | 价值判断 | 自动化只保证「事件成立判据（07/12）可重算」；叙事质量由 narrative-designer |
| 「福祉背离是否真有趣」 | 解释性 | 自动化只算 `divergence_count` 等（D 类）；含义由人读 |
| 涌现是否「真涌现」而非规则产物 | 因果推断 | 自动化提供 ablation / A-B 对照数据；结论由人（07 §6.3 假象清单） |
| provider 能力/模型行为 | 外部不确定 | 自动化提供 probe 记录（T#provider-capability-probe） |

---

## 7. 与 Fork B / delivery-reviewer 对齐

- **Fork B（用户 09:53 拍板）**：**「逐位可复现」不再是验收口径**。故：
  - `obs gate` 的 **G2a `metrics_bitwise_equal` / G2b `census_bitwise_equal`**、以及测试里的 **replay 状态哈希相等（G2c）** → **显式降为「诊断」（diagnostic，非阻塞）**，避免环境/浮点导致的**假 FAIL**。
  - **保留为阻塞**：G3 `llm_calls_zero`、G5 `llm_judged_zero`、G4 守恒、G7 schema、G6 分布回归、G1 边界、G2 术语、G5 前端、G6 美术。
- **绑证据方式不变**：**全量日志 + 种子化随机 + 产物 sha + 生成命令**（每条结论附 `log_hash` + 命令）。这是「结论可被独立复算」的落点。
- **待与 `delivery-reviewer`（T218 门禁分级表）对齐**：分级命名（blocking / diagnostic / manual）、以及 F2「G6 skip 假绿」的修复归属。
- **口径唯一不复制**：本表所有阈值/命令均引用现有实现（`code/obs/*`、`glossary/*`、`.importlinter`），**未新增第二套数**。

---

## 8. 落地清单（P0 / P1）

**P0（本轮）**
1. 修 **F2 假绿**：`obs gate --baseline auto` 未命中时**报警并 rc≠0**（或强制显式 `--baseline none`）。
2. 门禁/CI 前置**清 `__pycache__` + pytest 缓存**（治 F4 假红）。
3. 安装 `pytest-cov`，启用**行覆盖率棘轮**（红区模块阈值先设保守值，只升不降）。
4. 在 CI 里把 G2a/G2b/G2c **标为 diagnostic**（Fork B），不阻塞；其余保持阻塞。

**P1（后续）**
5. 补 `plugin/*`、`orchestration/*`、`devtools/*` 独立测试（§2 缺口）。
6. 给每条**新增门禁**强制附**一个反向验证用例**（可放在 `tests/negative/`，或 CI 的「注入-断言-还原」脚本）。
7. PR paths → 门禁矩阵（§5）接入 CI，避免全跑/漏测。

---

## 9. 反向验证的元规则（写给未来的门禁）

> **不会报警的守卫 = 没有守卫。**
> 每加一条门禁，必须同时交付：① 一条**故意弄坏 → 变红**的证明；② 它**防不到的盲区**说明；③ 退出码语义（**SKIP ≠ PASS**）。
> 三条缺一，该门禁**不予合并**。

---

*（策略 v1 — sandbox-test-lead；含 RV1–RV6 反向验证实录；口径真源 `code/obs/*`；与 delivery-reviewer T218 对齐中。）*
