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
| G3 | **pre-commit 钩子** | `.git/hooks/pre-commit`（源 `tools/pre-commit-lexicon.sh`） | 把 G2 提前到**提交前**，防漏网进库；**T237：只扫本次提交范围**（`git diff --cached`），对他人 WIP 免疫 | `--no-verify` 可绕过；仅覆盖 lexicon，不跑 pytest/lint |
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

**P0 前置**：`pytest-cov` 当前**未安装**。**Leader 裁定：暂不装**（装它需动环境，当前为「先跑通」阶段且非关键路径），故**行覆盖率棘轮暂缓**，改用**可度量的计数基线**（下）替代。

> **⚠️ 替代口径的局限（必须写明，不得悄悄用弱口径顶替）**：
> ① 计数基线只能证明「有测试、且数量没缩水」，**无法发现「未覆盖的边缘分支/异常路径」（如错误处理、边界值）**；② 无法区分「测试覆盖了函数」与「测试真正断言了行为」（可能有空跑/弱断言）；③ 模块-测试存在性矩阵只到**文件粒度**，非**行/分支粒度**。**因此本替代不等于覆盖率达标，只是「不倒退」的下界护栏。** 需要行覆盖率时单独提 `pytest-cov`。

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
- **待与 `delivery-reviewer`（T218 门禁分级表）对齐**：分级命名（blocking / diagnostic / manual）。
- **F2「G6 skip 假绿」已修**（obs-stats-dev，commit `d1ee62e`）：改为 fail-loud，见 §10。
- **发布入口分级**（release-engineer 提议，已认同）：**产出型发布 `make release` → `GIT_STAMP_STRICT=1`（脏树停）**；**只检查型 `make release-check` → 非 strict（脏树继续但标 `[DIRTY — 仅供参考]`，不作通过依据）**。理由：发版树干净不放松；诊断可继续但不背书。
- **口径唯一不复制**：本表所有阈值/命令均引用现有实现（`code/obs/*`、`glossary/*`、`.importlinter`），**未新增第二套数**。

---

## 8. 落地清单（P0 / P1）

**P0（本轮）**
1. 修 **F2 假绿**：`obs gate --baseline auto` 未命中时**报警并 rc≠0**（或强制显式 `--baseline none`）。→ **已修✓**（§10 ①，commit `d1ee62e`）
2. 门禁/CI 前置**清 `__pycache__` + pytest 缓存**（治 F4 假红）。→ **入口已修✓**（§10 ②）；CI 全局环境【待 release-engineer】
3. 安装 `pytest-cov`，启用**行覆盖率棘轮**。→ **Leader 裁定暂不装**；用替代口径（§2），**并写明其局限**（见 §2 注）。
4. 在 CI 里把 G2a/G2b/G2c **标为 diagnostic**（Fork B），不阻塞；其余保持阻塞。→ **已做✓**（obs gate 输出 `[DIAG]`）
5. **门禁绑 git 状态**（T220③）→ Makefile/ci_gate 已接✓；obs gate / release 入口【待】。
6. **门禁覆盖全测试**（T220④，修 `life/tests` 静默缺口）→ **已修✓**（§10 ④）

**P1（后续）**
5. 补 `plugin/*`、`orchestration/*`、`devtools/*` 独立测试（§2 缺口）。
6. 给每条**新增门禁**强制附**一个反向验证用例**（可放在 `tests/negative/`，或 CI 的「注入-断言-还原」脚本）。
7. PR paths → 门禁矩阵（§5）接入 CI，避免全跑/漏测。

---

## 9. 反向验证的元规则（写给未来的门禁）

> **不会报警的守卫 = 没有守卫。**
> 每加一条门禁，必须同时交付：① 一条**故意弄坏 → 变红**的证明；② 它**防不到的盲区**说明；③ 退出码语义（**SKIP ≠ PASS**）。
> 三条缺一，该门禁**不予合并**。

**判定例（来自 T220 的两处真缺陷——「会响」的守卫与「看得到全部」的守卫，缺一不可）：**

1. **判定例·假绿（F2）**：`obs gate --baseline auto` 未命中基线时**静默 skip 被当通过**（RV-F2 修复前：`[SKIP]`→`GATE PASS` rc=0）。
   → 违反元规则的**精神**：它「没报警」，但它也**没在工作**。「**没找到基线 ≠ 基线通过**」。
   → 新门禁判定：**存在「未命中/未运行」路径时，必须 fail-loud 或显式声明 skip**；否则不予合并。
2. **判定例·假红（F4）**：陈旧 `__pycache__` 让「已还原」的代码**仍报红**（RV6 实录）。
   → 这是「**守卫误报**」：它响了，但响错了对象——**假红会训练团队忽略告警**。
   → 新门禁判定：**门禁入口必须控制环境确定性**（清缓存 / 禁写字节码 / 固定种子），否则不予合并。
3. **判定例·覆盖缺口（T220④）**：门禁「绿」但**一整个测试目录从未被收集**（`code/life/tests` 27 测试）。
   → 这是**最安静的失败**：**「门禁看得到全部该看的东西」与「门禁会响」同等重要**。一个覆盖不全的门禁，和不会响的门禁一样危险。
   → 新门禁判定：**必须列出「实际覆盖范围」**（目录/文件），不得只写「pytest 通过」。
4. **判定例·环境伪装（T220+ 磁盘余量）**：**磁盘/inode 满会伪装成代码坏**——"偶发红 → 复跑就好"会把这个伪装一直盖住（freeze-layer-dev 查明今天多次"偶发红"真因是 **inode 99–100%**，非 flaky）。
   → 这是**假红的另一个来源**：不是时序，是**资源**。
   → 新门禁判定：**门禁结论必须绑定运行环境**（git 状态 + 磁盘/inode 余量），否则不予合并。本机实测 `avail_inode=8667 / 16,252,928（100% 用尽）` → 戳应显示 `DISK LOW`。

---

## 10. T220 门禁缺陷修复与验证（四件）

> 来源：T217 §3/§4 反向验证凿出的**真缺陷**。原则：**未修完的标【未修】**，不得因「已报过」当已解决。

| # | 缺陷 | 修复 | 反向验证 | 状态 |
|---|---|---|---|---|
| ① 假绿 | `obs gate --baseline auto` 未命中基线静默 skip（`ok=None`→通过） | obs-stats-dev 改 `obs/gate.py`+`obs/cli.py`（commit `d1ee62e`）：auto 未命中→`ok=False`；`none` 显式才跳过并打印；unknown id→fail | **RV-F2**：`auto` 未命中→`GATE FAIL` rc=1；`none`→PASS rc=0 + 打印；命中（t59_mock84）→PASS；`nope_id`→FAIL | **已修 ✓** |
| ② 假红 | 陈旧 `__pycache__` → 回滚后仍红 | 门禁入口前置清缓存 + 禁写字节码：`Makefile` `pyclean` + `code-test` 用 `PYTHONDONTWRITEBYTECODE=1 … -p no:cacheprovider` | **RV7**：`pyclean` 后 0；普通 import→3 个 `__pycache__`；`-B` import→0 | **入口已修 ✓**；CI 全局环境 / 发布入口【待 release-engineer】 |
| ③ 绑 git 状态 | 门禁结论不标「在哪个 git 状态上跑的」→ 并发编辑期结果不可信 | 新增 `tools/git_stamp.sh`；接入根 `Makefile`（`stamp`，且为 `gate` 首步）、`code/frontend/tools/ci_gate.sh` | **RV9**：当前树→`[DIRTY — 结论仅供参考]`；临时净仓库→`[CLEAN]`；+1 未跟踪→`[DIRTY]` | `Makefile`/`ci_gate` **已接 ✓**；`obs gate`【待 obs-stats-dev】；`make release`【待 release-engineer，contract 已钉】 |
| ④ 覆盖率缺口 | `pytest.ini testpaths=tests` 只收 `code/tests`；`code/life/tests`(27)、`plugin-skeleton/tests`(11) **从未被门禁运行**（**同名不同义**：两套「跑测试」覆盖不同） | `pytest.ini`→`testpaths = tests life/tests`；新增 `make plugin-test` 纳入 `gate` | **RV8**：BEFORE——`life/tests` 放必失败测试，`make code-test` 仍 `358 passed`（缺口实证）；AFTER——同一测试让 `make code-test` `FAILED` | **已修 ✓** |
| ⑤ 磁盘余量打戳（T220+） | 磁盘/**inode 满会伪装成代码坏**（"红→复跑→绿"盖住真因） | `tools/git_stamp.sh` 增 `disk:`（字节+inode）+ `磁盘: [DISK OK]|[DISK LOW — 结论仅供参考]`；阈值可覆盖 | **RV-DISK**：默认→`DISK LOW`（本机 `avail_inode=8667`，inode 100%）；阈值≤1→`DISK OK`；`GIT_STAMP_STRICT=1`→rc=1 | **make/ci_gate/obs gate 已接 ✓**（obs 五行 `85f7176`+caveat `3bbe67e`） |
| ⑥ 红来源不明（T220+） | 长期红时**只能猜**（flaky? 脏树? 磁盘?）——真相是**在飞改动**；比"红"更糟的是"红来源不明"，会训练人忽略门禁 | 打戳推至 **pytest 出口**：`code-test: pyclean stamp`；新增 `tools/pytest_stamped.sh`（根 pytest 入口包装）；戳新增两行 `未提交文件数:` + `最近改动的模块:`（脏文件按纳秒 mtime 降序 → 模块目录，前 3） | **RV-STAMP（受控 temp 仓库）**：建脏文件 obs→engine→life（依次更新）→ 戳输出 `最近改动的模块: code/life code/engine code/obs`（最新优先）；修复了「全新未跟踪目录呈 `dir/` → dirname 少一层」的 bug | **已修 ✓** |

### 10.1 门禁覆盖范围表（逐入口 —— 禁止再以为「跑了 pytest」=「测试都跑了」）

| 入口 | 命令 | **实际覆盖**（测试目录/范围） | 备注 |
|---|---|---|---|
| `make code-test` | `pytest` | `code/tests` + **`code/life/tests`** | 旧版漏 `life/tests`（④ 已修）；含重 e2e，~4 min |
| `make plugin-test` | `pytest` | `plugin-skeleton/tests` | ④ 新增 |
| `make gate` | `stamp`+`lexicon-gate`+`code-test`+`plugin-test`(+`lint-imports`) | 上述全部 | 汇总入口；**首步打戳** |
| `obs gate` | `python -m obs gate --log …` | 无测试收集（读日志跑 G2–G7） | 观测层门禁 |
| `tools/pytest_stamped.sh` | `pytest`（带戳） | 同 `pytest`（参数决定） | 「根 pytest 入口」推荐包法；**先打戳再 pytest**（⑥） |
| `ci_gate.sh` | `node` + `python` | `frontend/tools/smoke_test.js` + 真渲染 | JS/渲染，非 pytest |
| `make -C code art` | `bash` | 美术脚本自检（剪影/角色/事件卡/自洽断言） | 非 pytest |
| **豁免** | — | `frontend.src`（只读应用本体）、`devtools/*`、`orchestration/*`、`gen_*.py`（生成脚本） | 豁免理由：只读/工具/生成物，其**产物**由 G5/G6/G8 覆盖；独立测试列 §8-P1 |

### 10.2 遗留（【未修】/【待复核】——不虚报）

- 【已收口】`obs gate` **五行打戳**（commit `85f7176`：`sha/dirty_files/disk:/状态/磁盘:` + `GIT_STAMP_STRICT`）；已独立复跑验证（strict 脏树→rc=1；非 strict→GATE PASS）✓。`disk:` 行与本仓 `tools/git_stamp.sh` 口径一致（跨入口同一数）。caveat 已在 `3bbe67e` 注释写明（`avail` 列不含 5% root 预留，root 场景 LOW 是保守误报、安全的错法）。**交叉核验**：obs gate 默认→`DISK OK`、`DISK_MIN_INODE_AVAIL=1`→OK、阈值极大→`DISK LOW`（两分支均可达）✓。
- 【待 release-engineer】发布入口打戳 + CI 全局 `PYTHONDONTWRITEBYTECODE`（contract 已钉在其方案 `5af0bac`）；
- 【待洁净树复核】T220 改动后「现有门禁全绿」的**最终确认**：当前工作树 **DIRTY（46 文件，他人并发编辑 T213/T215 中）**，观测到 `37 failed / 7 errors` 且集中在**正在被改的模块**（`scheduling_budget`/`production_*`/`llm_audit_bridge`/`version_fingerprint`/`freeze`）——**按 ③ 语义，该结果标 `[DIRTY — 仅供参考]，不作为通过依据`**；需在**洁净树**上复核。**本文件不声称全绿。**

---

## 11. T237 pre-commit 扫描范围修复（只扫「本次提交」，含反向验证）

**问题（今日 2 次致堵）**：旧 pre-commit 跑 `make lexicon-gate` = **全树**扫描 → **他人未提交的 WIP 违规**会阻断**所有人**的提交（econ-dev 被他人 WIP 拦；sim-engine-stats-architect 被 life-layer-dev 新建 `code/tests/test_t231_goal_abandon.py` 第 3 行 `sim-engine` 拦）。诱发的错误"解阻"是**代改他人文件** → 又制造归属/裹带问题。故**修根因，不修症状**。

**修复（只放宽"扫描范围"，不放宽"检测强度"）**：
- `glossary/tools/lint_terms.py` 新增 `--paths <...>` 与 `--paths-from-stdin`（**仅扫给定文件**；缺省仍全树）；报告新增 `scope: full-tree | changed-only`。
- pre-commit 改为：`git diff --cached --name-only --diff-filter=ACM | python3 glossary/tools/lint_terms.py --root . --baseline glossary/term_baseline.json --paths-from-stdin` —— **本次提交范围**，对共享索引 / 他人 WIP **免疫**。
- 钩子脚本**入库**：`tools/pre-commit-lexicon.sh`；安装 `make install-hooks`（`cp` 到 `.git/hooks/pre-commit`）。
- **CI 全树门禁未削弱**：`make lexicon-gate` 仍是 `--root .`（全树），**不改**。

**反向验证（实际命令与输出；受控 temp 仓库 `/tmp/t237-rv`，装真实钩子）**：

| # | 构造状态 | 命令 | 实测结果 |
|---|---|---|---|
| ① | 仅**他人** WIP 违规（`other_wip.md` 含 `OFFER`，**未暂存**） | staged 仅 `mine.md`（无违规）→ `git commit` | **成功**（`5380f41`）→ 仅他人 WIP 违规**不再阻断**我的提交 ✓ |
| ② | **我的**文件违规（staged `mine_bad.md` 含 `OFFER`） | `git commit` | **失败**，打印 `mine_bad.md:1:1 [OFFER] -> OFFER_CREATED` + 建议替换 ✓ |
| ④ | CI 全树门禁 | `lint_terms.py --root . --baseline …` | `scope=full-tree files_scanned=319 new_violations=0`；对照 `--paths` → `scope=changed-only files_scanned=1` ✓（全树**未削弱**） |

> 红线守住：**放宽的是扫描范围，不是检测强度**——自己文件里的**新违规照样红**（②）。若做不到 ②，本改动作废。

---

## 12. T242 pre-commit 阶段 2：机器可读文件「可解析」（只扫本次提交，含反向验证）

**背景**：sim-engine-stats-architect 提交时把 `tools/inert_registry.json` 写成**无效 JSON**（Python 命令里 `"` 未转义），事后 `json.load` 才发现（`036f8c3` 修）。同一族病：**写入了机器可读文件却没校验，发现得太晚**——而 `json.load` 成本 0.1 秒。

**修复（复用同一钩子，不另起第二套）**：
- 新增 `tools/check_machine_readable.py`：`*.json`→`json.load`；`*.jsonl`→逐行（报断行号）；`*.yaml/.yml`→`yaml.safe_load`（无 PyYAML 则**可见地**标 `skipped (no parser)`）；`*.toml`→`tomllib`（stdlib）。**只做"可解析"，不校验 schema 语义**。
- **大文件门上限**：> `--size-cap`（默认 **5 MiB**）→ 打印 `skipped (size): <file> (<name> B > <cap> B)` 后跳过——**跳过原因可见，绝不静默**。
- 挂在既有钩子 `tools/pre-commit-lexicon.sh` 的**阶段 2**（阶段 1 = T237 术语棘轮），**仍由 `make install-hooks` 装**；两段都用 `git diff --cached`（本次提交范围）。

**反向验证（实际命令与输出；受控 temp 仓库 `/tmp/t242-rv`，装真实钩子）**：

| # | 构造状态 | 命令 | 实测结果 |
|---|---|---|---|
| ② | staged 合法 `good.json` | `git commit` | **成功**，钩子打印 `✅ 机器可读文件可解析（checked=1, skipped(size)=0）` ✓ |
| ① | staged 坏 `bad.json`（`{"a": 1,, "b": }`） | `git commit` | **失败**，打印 `bad.json:1:9: JSON 解析失败：Expecting property name enclosed in double quotes` ✓（**文件名 + 行列**） |
| 附 | staged 坏 `bad.jsonl`（第 2 行非法） | `git commit` | **失败**，打印 `bad.jsonl:2: JSONL 第 2 行解析失败：Expecting value` ✓（**断行号**） |
| ④ | staged 大文件 `big.json`（6 000 001 B > 5 MiB） | `git commit` | **成功**，打印 `skipped (size): big.json (6000001 B > 5242880 B)` + `（checked=0, skipped(size)=1）` ✓（**跳过可见**） |

> 红线守住：**不为"更快"而静默跳过**——跳过的每条都打印原因（`skipped (size)` / `skipped (no parser)`）。未覆盖 `.csv/.txt` 等：**明确不做**（非机器可读 JSON/YAML/TOML 目标，且无低成本通用解析）。

---

## 13. T241 actor 类型守卫：反向验证的「**证明旧代码会错**」样板（kernel-dev）

> **元规则补一条**（§9 是「证明弄坏会红」，本条是它的**兄弟**）：
> **"证明新代码对"是弱证据；"证明旧代码错"是强证据** —— 后者说明**这个修复确实解决了一个真实存在的问题**，而不是防御性的美观。
> 判定：凡"补守卫 / 堵回退路径"类改动，验收**必须**含一条「**旧代码在什么输入下会出错**」的实测，且**双向**（新代码拦住了坏输入 **且** 好输入仍照常）。

**背景（同名不同义）**：`actor` 字段在多数消费方意味着「Agent id」，但 v2 起可为非 Agent 一等 actor（`SYSTEM`/`OBSERVER`/`DIRECTOR`，+世界哨兵）。存在 `agent_id or actor` 回退路径 **会把 `DIRECTOR` 当 Agent 串** → 某天某个指标里把 DIRECTOR 当成一个人。

**修复**：单一真源 `code/contracts/actors.py`（`NON_AGENT_ACTORS` + `is_agent_actor`/`agent_or_none`），四处收敛：`obs/life.py`（删本地白名单改引用真源）· `frontend/src/replay.js`（6 处 `ev.actor` 回退加 `agentActor` 守卫；`frontend.src` 不能 import Python contracts，故为**白名单 JS 镜像**——诚实标注的例外）· `frontend/tools/render_svg.py:92`（STATE_CHANGE）· `contracts/models.py` 注释。sha `151de17`。

**反向验证（实际命令与输出）**：

| # | 构造 | 命令 | 实测结果 |
|---|---|---|---|
| ① **旧代码会错**（强证据） | 造 `STATE_CHANGE actor="DIRECTOR"/"SYSTEM"/"OBSERVER"`（无 payload.agent_id）喂旧 `replay.js` | `node` 实跑旧版 | 旧版**造出假角色快照键** `"SYSTEM"`/`"DIRECTOR"`（把系统 actor 当成了人）→ 证明**存在**真实问题 |
| ② 新代码拦住（同一输入） | 同上喂新版 | `node` 实跑新版 | snapshot keys 仅真 Agent；`humanize.actor` 对 DIRECTOR/SYSTEM/OBSERVER 为 `null` ✓ |
| ③ **双向·好输入仍照常** | 同一日志含真 `P001` | 同上 | `P001` 状态照常折叠、`humanize.actor="P001"` ✓ |
| ④ obs 侧（指标口径） | WD-on 日志（真实产物）：171 条 `actor=非 Agent 且无 payload.agent_id` | `obs.life._agent_of` 逐条 | **泄漏 0**；真 Agent 指标（activity_engagement 等）照常 ✓ |
| ⑤ 静态导出工具 | `render_svg.fold_until` 喂 SYSTEM/DIRECTOR/OBSERVER/P001 的 STATE_CHANGE | 断言 | fold 出的 agent 集合 == `{P001}`，非 Agent 全被挡 ✓ |

> **同型分清「真同型」与「看起来像但安全」**（避免扩大化）：`engine/perceive.py` / `life/visibility.py` / `orchestration/integration.py` 用 `actor == agent_id`（与真实 id 比较，DIRECTOR 不会相等）→ **安全，不改**；`life/agent.py::_describe_event` 把 `ev.actor` 当**显示文本**（展示非指标）→ **低危，不改**。
> **相邻缝不擅自动手**：`payload.agent_id = "MARKET"`（`NEED_UPDATE` 等）是**同一语义裂缝的另一条缝**，且**正在污染** `obs.need_metrics` 聚合 —— 因属**跨模块语义**（改它要动事件语义/可能动 08），**交 Leader 裁决立项 T248**，未擅自改。

---

*（策略 v1 + T220 §10 + T237 §11 + T242 §12 + T241 §13 — sandbox-test-lead（§10–§12）· kernel-dev（§13）；含 RV1–RV9 + RV-DISK + RV-STAMP + T237/T242/T241 反向验证实录；口径真源 `code/obs/*`；与 delivery-reviewer T218 对齐中。）*
