# 02 · 架构交付评审——对 T23《系统实现架构（v1.2 工程蓝图）》的独立复核

> 文档类型：交付评审（独立复核）｜ 作者：delivery-reviewer（交付评审员）
> 复核对象：`v1.2/01-implementation-architecture.md`（T23，823 行 / 64KB，§1–§7 全）
> 复核基线：`v1.1/00-architecture.md`、`v1.1/08-engine-stats-extension.md`（最新版）、`v1.1/14-agent-impl-reuse-map.md`
> 复核纪律：独立复核，不替设计者辩护；每项结论给证据（章节）+ 最小验证方法；区分**确定缺陷（阻塞）**与**待验证风险（非阻塞）**；不把风格偏好升级为架构问题。
> **最终结论：有条件放行（Conditional Pass）**。前置 B1–B4 已闭合降级；新增 3 项确定缺陷须闭合、若干风险须登记。

---

## 0. 复核范围与方法

- 逐节复核：§1 模块结构、§2 接口契约、§3 数据模型与存储、§4 选型 decision matrix、§5 P0 任务分解、§6 风险与演进成本、§7 ADR。
- 八项必查（leader 任务书）：①确定性/可复现 ②异常/恢复 ③并发/顺序 ④接口/依赖 ⑤容量/性能 ⑥可测试性 ⑦迁移/发布回滚 ⑧安全/权限。
- 额外实测：`code/` 现有实现（pytest 实跑）、跨包 import 关系、CI 门禁可跑性。
- 分类口径：
  - **确定缺陷（阻塞）**：与上游【已定】契约/三条铁律（C1 内核确定性 / C2 同日志逐位一致 / C3 LLM 判定冻结）直接冲突，或不可实现/自相矛盾，且缺最小修补即开工必然返工。
  - **待验证风险（非阻塞）**：取决于 P0 实测、参数标定或后续章节闭合，当前证据不足以判为缺陷。

---

## 1. §1 模块结构复核

**复核对象**：§1.1 目录树、§1.2 模块边界表、§1.3 依赖方向 + import-linter 规则、§1.4 运行期控制流。

### 1.1 依赖方向是否真单向无环
**结论：成立。** 依赖图（§1.3）包级无环；`contracts` 为纯类型包（零业务依赖），`kernel` 零反向依赖，`emergence`/`traj`/`frontend`/`narrative` 为只读下游。§1.2 模块边界表逐行与 `00`/`08`/`16` 的层定义一致。

### 1.2 原 B1–B4 复验（**前置缺陷：全部闭合，予以降级**）

| 原项 | 复验证据 | 结论 |
|---|---|---|
| **B1** 接口/hook 协议类型无归属模块 | §1.1 目录树新增 `contracts/`（`interfaces.py`/`hooks.py`/`models.py`/`errors.py`）；§2 引言「所有协议类型统一定义于 `contracts` 包」；§1.3 规则 1「`contracts` 纯类型、零业务依赖、被四包依赖」；ADR-02 | **✅ 闭合（蓝图层）**。残留见 §7-R7 / D3 |
| **B2** import 规则按「方法」粒度不可执行 | §1.3 规则 3 已改为**模块/符号粒度**：「`life` 不得 import `kernel.arbiter`/`hooks`/`state`/`scheduler` 的**任何符号**」 | **✅ 闭合** |
| **B3** `emergence` 只读规则过严致复现缺陷 | §1.3 规则 2 已开白名单：`contracts.*`、`kernel.ledger`、**`kernel.canonical_json`、`kernel.version`（纯函数只读）**，理由即「避免复制序列化实现导致字节漂移」 | **✅ 闭合** |
| **B4** LLM 审计事件写路径矛盾 | §2.2.1 专设「IF-2c 提交接口与调用时序（B4 闭合）」：`freeze`/`narrative` 只产 `AuditPayload` → `submit_audit` → **Arbiter 校验后 emit**；`LLM_CALL` 于 P2 相位由 Arbiter emit；单一写入口不动 | **✅ 闭合** |
| **N1** 叙事层归属与 `00` §1.5 不一致 | §7 ADR-07 明确「叙事层物理分包、逻辑属生活层角色带（N1 选项②）」 | **✅ 已说明** |
| **N2** 依赖图 `life.decision` 无对应模块 | §1.3 依赖图已改为 `life (L1)` | **✅ 已统一** |

### 1.3 §1 残留（新登记）
- **D3（见 §8）**：§1.1 引言仍写「**十个**一级域」而实际已 11 个（含 `contracts`）；§1.1 `config/` 目录树漏列 `perception_scope.json`、`narrative_weights.json`（§3.6 与实现 `code/config/` 均含）。

---

## 2. §2 接口契约复核（维度④接口/依赖、③并发/顺序）

**结论：接口签名无歧义、铁律符合性核对（§2.7）成立；发现 1 项时序不一致（D1）。**

- ✅ IF-1~IF-7 + IF-2c 签名完整（§2.1）；`WorldView` 反泄漏（`heard_annotations` 标 `spec=true` 不进决策主视图，§2.1）；`JudgmentRequest`/`AuditPayload` 字段与 `08` §1.2 I 对齐。
- ✅ 冻结层契约 F1–F6（§2.2）完整：F2「`decision ∈ envelope.options`」、F3「重放态外部调用数恒为 0（CI 断言）」、F5 嵌入冻结入 `engine_version`——直接落实 C3。
- ✅ hook 链：P4 4.1–4.8 顺序冻结、P3.5 L1–L7 顺序固定（§2.3），与 `08` §2.4 一致；依赖倒置（内核持 `contracts.hooks` Protocol、`orchestration` 注入）闭合 B1。
- ✅ 感知作用域 `visible_events()`/`location()`/`PERCEPTION_SCOPE`（§2.4）与最新版 `08` §3.5 / R1–R5、T26-D1–D4 一致，纯函数、无 LLM。
- **D1【确定缺陷·中】事件持久化/`emit` 时序在 §1.4 / §2.1(IF-3) / §2.2.1 之间不一致**。
  - 证据：§1.4「P6 COMMIT：`ledger.append(events)`」（**批量提交**）；§2.1 IF-3「`emit(event, ledger) -> Event` …**追加哈希链**」（**即时追加**）；§2.2.1「`LLM_CALL` …在 **P2 相位内**由 Arbiter emit」。
  - 影响：两种读法互斥——(a) `emit` 仅暂存、P6 批量落盘；(b) `emit` 即时落盘。若为 (b)，则 P2 的 `LLM_CALL` 已入链，**R-5 声称的「整回合回滚」无法覆盖它**，异常恢复语义（任务书 #2）与 C2 哈希链一致性受影响。
  - 最小验证：P0 单测注入一个使 P4 某 hook raise 的用例，断言**回滚后日志中不存在本回合任何事件（含 P2 的 `LLM_CALL`）**；当前措辞无法据以判定期望行为。
  - 最小修补：明确「`emit` = 分配 seq/构造 Event 并**暂存**；**唯一持久化 = P6 `ledger.append`**」，或在 IF-3 注明「`emit` 内部即 append，故 P2 事件不参与回合回滚」并同步修正 R-5 回滚范围。

---

## 3. §3 数据模型与存储复核（维度①确定性、②恢复、⑤容量、⑧安全）

**结论：数据模型完整、复现口径正确；2 项非阻塞风险（R2/R5）。**

- ✅ 哈希链（§3.1）：`hash=sha256(canonical_json(...))`、`prev_hash`、`GENESIS_HASH`、篡改检测 → `HashChainBroken`，继承 `v1/03` §6。
- ✅ `turn_seal`（§3.2）独立封条链、不进主链（避免自指）——设计正确；用于断点续跑/前端切块。
- ✅ 侧存储（§3.3）内容寻址 + 主日志只存引用（AR-C4/XT-3）；向量索引（§3.4）**不进判定/统计**，重放折叠 `MEMORY_RETRIEVE` 已落日志的 `mem_id`——**这是 C2 的关键正确设计**。
- ✅ 快照（§3.5）节流 K=100、从日志重建、CI 断言「重建==从头重放」。P0=84 回合不触发中途快照（无隐患）。
- ✅ `engine_version` 指纹（§3.6）含 `topology_hash`/`perception_scope_hash`/`embedding_model`/`llm_models`/`prompt_registry_hash`/`event_schema_hash`，重放前断言一致——复现输入封闭。
- **R2【非阻塞】守恒不变量 I2 公式依赖未决 Q1**。§3.7 I2「货币守恒式(1)（**含银行库存项，待 Q1 裁决**）」→ P0 门禁（P0-2/P0-14）的守恒口径未定。验证：Q1 裁决后固定公式并落黄金测试；未裁决前若用不含银行库存项口径，会误报/漏报。
- **R5【非阻塞】侧存储完整性校验未进 §3.7 不变量表**。§3.3 声明「body_ref 与 blob 哈希一致可校验」，但 §3.7 I1–I7 无「`body_ref`/`embed_ref` 可解析且哈希一致」条目（仅 §6.1 R-4 提及）。验证：补一条不变量并在 P6 校验。

---

## 4. §4 技术选型 decision matrix 复核（维度⑤容量、⑦迁移/许可）

**结论：六项选型均有真备选 + 加权 + 演进成本，可支撑决策；但有 1 项合规缺陷（D2）与 1 处数值瑕疵。**

- ✅ 语言（Python 3.11）/冻结层（自建 FreezeClient vs LiteLLM）/向量库（本地精确 vs sqlite-vec/FAISS vs Convex）/序列化（规范 JSON vs CBOR/Protobuf）/测试（pytest+黄金日志+import-linter vs Hypothesis）/前端（AI Town PixiJS 迁移 vs 全自建）——**每项至少 2 个备选、显式推荐 + 主备选 + 演进成本**，符合任务书验收（"选型有比较与理由"）。
- ✅ 前端选型体现用户对 PixiJS 的期待（§4.6 + P0-15）。
- **D2【确定缺陷·中】缺第三方许可证合规落地项**。§4.6/ADR-01 明确要**迁移/包裹复用** AI Town（MIT）与 GA（Apache-2.0）；`14` §A.1 已列义务（MIT 保留版权与许可声明；Apache-2.0 保留声明、**标明修改**、保留 NOTICE），但本蓝图 §1.1（无 `NOTICE`/`THIRD_PARTY`/`licenses/`）、§3、§4、§7 均**未落地该义务**。
  - 最小验证：检索蓝图全文 `NOTICE`/`licenses`/`third_party`/`modified` → 无命中；对照 `14` §A.1 义务表逐条缺失。
  - 最小修补：增 `THIRD_PARTY_NOTICES.md`（含 AI Town MIT 全文 + 版权行、GA Apache-2.0 + NOTICE）与 `licenses/`；对 GA 派生文件头部标注「modified from …」。**不阻塞内部 P0 跑通，阻塞任何对外发布/分发**。
- **低**：§4 加权评分有个位小数误差（如 4.1 A 复算 4.50≠4.55、4.2 A 4.30≠4.35），**不影响排序**，属计算瑕疵，建议核对。

---

## 5. §5 P0 任务分解复核（维度⑤⑥）

**结论：分解可执行、验收标准可测、依赖图合理。**

- ✅ 15 个子任务（P0-1~P0-15）均含**负责/依赖/可测验收标准**；依赖 DAG（§5.2）关键路径 `P0-1→P0-3→P0-6→P0-7→P0-8→P0-9→P0-13→P0-14` 合理，并行组清晰。
- ✅ 责任映射到名册（kernel-dev / life-layer-dev / freeze-layer-dev / sim-engine-stats-architect / sandbox-test-lead）。
- ⚠️ **低**：P0-15（前端）负责人「待分派」——现已新增 `frontend-dev`，建议指派（不影响内核/生活层主线）。

---

## 6. §6 风险与演进成本复核（维度③⑤⑦⑧）

**结论：风险清单覆盖度高；补 3 项非阻塞风险（R1/R3/R4）。**

- ✅ §6.1 R-1~R-11 覆盖成本/缓存偏差/嵌入漂移/侧存储/hook 异常/观测污染/浮点/长窗/多 seed/训练污染/可见性；§6.4 G1–G5 CI 硬门禁与三条铁律映射明确；§6.2 演进路线「配置+编排，不重写内核」合理。
- **R1【非阻塞】并发/顺序模型未显式声明（任务书 #3）**。§2.3 `Scheduler.run_round` 单线程串行、冻结层签名同步阻塞——**默认同步**即天然保确定；但蓝图**未显式规定**「LLM 调用不得并行 / 结果消费顺序」，也未规定 **P1/P2/P3 阶段内 Agent 遍历顺序**（仅 P3.5/P4 规定 `agent_id` 升序，`08` §2.3）。若后续为降延迟并行化 LLM，`seq`/`mono_ts` 分配将随完成顺序漂移。验证：§2/§6 补「LLM 调用同步、按 `agent_id` 升序发起与消费；任何并行化须保证 seq 分配与遍历顺序解耦」。
- **R3【非阻塞】日志不可篡改性边界**。§3.1 仅本地哈希链 + **可选** `merkle_root` 外部锚定（「不进主链」）；无签名（`00` Q9 未决）。→ 防的是**局部篡改**；能一致重写全链且有权限者**不可检测**。验证：裁决 Q9 增签名/外部锚定后固定威胁模型。
- **R4【非阻塞】LLM 输出注入/记忆投毒未讨论（任务书 #8）**。已防护：判定 `decision ∈ envelope.options`（F2）、意图经裁决器校验（`INTENT_REJECTED`）、叙事 `affects_state=false`。**未覆盖**：跨 Agent 对话内容注入下游 prompt、侧存储记忆投毒、叙事 prompt 注入。验证：增「LLM 输出视作不可信输入、写入侧存储前规范化、prompt 组装转义」条目并加注入测试用例。
- **R6【非阻塞】**容量/成本数字均为**未标定估计**（`α_*`、`c_life/c_social`、压缩比，`08` D7-5）；N=20/周 ~2.5MB→0.6MB、12 周 ~8MB 结论**方向可信**但待 P0 实测。验证：P0 实跑聚合 `LLM_CALL` 与日志体积曲线。

### 6.1 容量/性能（任务书 #5）结论
N=20 单周：~8.4e3 事件 / ~2.5MB（压缩 ~0.6MB）；长窗 12 周 ~8MB；展望 N=50×12 周 ~20MB。**日志/复现非瓶颈，唯一显著成本是 LLM 调用**（§4.3 本地精确检索 P0 足够；`MEMORY_RETRIEVE` 落日志使换库不影响复现）。外推风险 = 未标定系数（R6），非架构缺陷。

---

## 7. 可测试性与 CI 门禁实测（任务书 #6 + leader 追加）

**leader 追加「门禁是否能在 CI 里真跑绿」——实测答案：部分可跑，完整复现门禁当前尚未落地（属 P0-13 待办，非蓝图缺陷）。**

实测证据（`code/` 现状）：
- ✅ **已有且全绿**：`python -m pytest -q` → **45 passed in 0.11s**，覆盖 `test_canon`/`test_conservation`/`test_hashchain`/`test_replay`/`test_rng`/`test_freeze`——**内核+冻结层的核心不变量与哈希链/重放单测已可跑**。
- ✅ 依赖方向**当前未被违反**（grep 实测）：`engine/` 不 import `life`/`freeze`；`life/` 不 import `engine`；`freeze/` 不 import `engine`/`life`（生活层以 `life/ports.py` 定义本地 IF-1/IF-2 Protocol 解耦）。
- ❌ **G1 边界门禁未落地**：`code/` 下**无 `contracts/` 包**（与 §1.1/§2 蓝图不符）、**无 import-linter 配置**（无 `.importlinter`/pyproject 契约）、**无 CI workflow**（无 `.github/`）。→ §6.4 G1「import-linter 边界」**当前不可运行**，且**无强制对象**（`contracts` 不存在）。
- ❌ **G2 复现门禁不完整**：无 `golden_logs/`，`emergence` 未实现 → 「`metrics()` 两次字节相等」无从断言（仅 replay/canon 单测覆盖部分）。
- ❌ **G3 冻结门禁**：`test_freeze` 已有基础，但「重放态 `llm_external_calls==0`」端到端断言未接 CI。

**判定**：门禁的**定义**（§4.5/§6.4）**可执行、可断言**，方向正确；但**当前 CI 真跑绿不成立**——尤其 G1 缺 `contracts` 包与 import-linter、G2/G3 缺 golden_logs/端到端断言。这是**实现进度问题**（P0-13 未完成），非蓝图缺陷；**但需 leader 知晓：蓝图 §1.1 的 `contracts/` 与实现分包（`life/ports.py`）已出现偏离（见 R7），若不放回 `contracts` 共享包，§1.3/ADR-02 的「可机器强制」将名不副实。**

---

## 8. 总评与结论

### 8.1 阻塞项清单（确定缺陷，附最小复现/验证）
| ID | 缺陷 | 级别 | 最小验证 | 最小修补 |
|---|---|---|---|---|
| **D1** | 事件 `emit`/持久化时序在 §1.4、§2.1(IF-3)、§2.2.1 间不一致，影响整回合回滚与 C2 | 中 | P0 单测注入 P4 hook 异常，断言回滚后本回合事件（含 P2 `LLM_CALL`）不在日志 | 统一「emit=暂存、P6 唯一 append」，或在 IF-3/R-5 明确回滚范围 |
| **D2** | 缺第三方许可证合规项（NOTICE/THIRD_PARTY/标明修改），而 §4.6/ADR-01 明确复用 GA(Apache-2.0)/AI Town(MIT) | 中 | 全文检索 `NOTICE`/`licenses`/`modified` 无命中；对照 `14` §A.1 义务表 | 增 `THIRD_PARTY_NOTICES.md` + `licenses/`；GA 派生文件标 modified |
| **D3** | §1.1 文档一致性：引言「十个一级域」实为 11；`config/` 目录树漏列 `perception_scope.json`、`narrative_weights.json`；§3.6「五大件」实列 7 项 | 低-中 | 对照 §1.1 树 ↔ §3.6 ↔ 实现 `code/config/` | 回写 §1.1 与 §3.6 标题/清单 |

> 说明：D1/D2/D3 均为**可最小修补的文档/契约一致性问题**，不改变架构骨架；**不构成「不放行」**。

### 8.2 非阻塞风险清单（待验证，附验证手段）
| ID | 风险 | 验证手段 |
|---|---|---|
| R1 | 并发/顺序模型未显式声明（同步 vs 并行 LLM；P1/P2/P3 遍历顺序） | §2 补「同步阻塞 + `agent_id` 升序」约束，加并行化禁用断言 |
| R2 | 守恒不变量 I2 公式依赖未决 Q1（银行库存项） | Q1 裁决后固定公式 + 黄金测试 |
| R3 | 日志不可篡改边界=本地哈希链+可选锚定，无签名 | Q9 裁决后固定威胁模型 + 签名 |
| R4 | LLM 输出注入/记忆投毒/侧存储污染未讨论 | 增不可信输入规范化 + 注入测试 |
| R5 | 侧存储完整性校验未进 §3.7 不变量表 | 补不变量 + P6 校验 |
| R6 | 容量/成本系数未标定（`08` D7-5） | P0 实测聚合 `LLM_CALL`/日志曲线 |
| R7 | 蓝图 `contracts/` 与实现分包（`life/ports.py`）偏离，G1 无强制对象 | 实现补 `contracts/` 并落 import-linter 契约 |

### 8.3 结论：**有条件放行（Conditional Pass）**

**理由**：
1. 架构骨架**正确且自洽**：三层边界清晰、依赖单向无环、三条铁律（C1/C2/C3）在接口层（§2.7）与门禁层（§6.4）均有可执行保障；`contracts` 包 + IF-2c 已闭合原 B1–B4。
2. 选型有真备选与理由，P0 分解可执行，风险清单覆盖度高，复现/容量/演进路径清晰。
3. 现存问题**均为可最小修补的一致性问题**（D1–D3）或**待标定/待裁决风险**（R1–R7），**不动摇架构**。

**放行条件（须闭合后方可视为通过）**：
- **必修（放行前）**：D1（统一 emit/commit 时序，保异常回滚与 C2）、D2（补第三方许可证合规项）、D3（回写 §1.1/§3.6 文档一致性）。
- **落实 P0-13 全门禁并真跑绿**：新增 `contracts/` 包 + import-linter 契约（对齐 §1.3/ADR-02）、`golden_logs/` + 「`metrics()` 两次字节相等」断言、重放态 `llm_external_calls==0` 端到端断言；当前仅 pytest 45 项（内核/冻结层）真跑绿，G1–G3 尚未落地。
- **登记**：R1–R7 纳入 §6 风险表并给验证手段。

**不放行的唯一情形**：D1 若不闭合且 P0 采用「emit 即时落盘」实现，则异常回滚与 C2 哈希链一致性存在实质风险——届时升级为阻塞。

---

## 9. 三条铁律最终核对
| 铁律 | 蓝图层 | 实测 `code/` |
|---|---|---|
| C1 内核确定性、非 LLM | ✅ §2.7 / §1.3 规则 4 | ✅ engine 不 import life/freeze |
| C2 同日志逐位一致 | ✅ §3.1/§3.4/§3.5（重放折叠、嵌入不进判定） | 🟡 hashchain/replay/canon 单测绿；metrics 字节一致门禁未接 |
| C3 LLM 判定冻结 | ✅ §2.2 F2/F3 + §2.2.1 + IF-6 | 🟡 test_freeze 基础绿；重放调用=0 端到端断言未接 |

*（评审收口 — delivery-reviewer）*

---

## 10. 复验记录（T36 · D1/D2/D3/R7 落地校验）

复核时机：T35（D1/R7/D2）与 T37（D3/D1 措辞）完成后。全部用**可重跑命令**取证。

### 10.1 D1 — emit/持久化时序统一 ✅ 达标
- **代码**：`engine/arbiter.py` 实现 `emit → 本回合待提交缓冲区`，`commit(state)` 为 **P6 唯一 append 点**（证据：`_pending` / `buffer_len` / `commit` 定义）。
- **回滚用例（实跑）**：`python -m pytest tests/test_emit_rollback.py -v` → **3 passed**：
  - `test_p4_exception_rolls_back_whole_round`：P4 注入异常 → 断言 `"LLM_CALL" not in types`（P2 的 `LLM_CALL` 随回合回滚丢弃）、`SYSTEM_ERROR` 计数==1、`state_hash` 不变；
  - `test_conservation_failure_rolls_back_and_audits`：破坏守恒 → 断言 `MONEY_MINTED`/`LLM_CALL` 均不在日志、`ECONOMY_INVARIANT_VIOLATION`≥1、状态不变；
  - `test_success_round_appends_buffer_at_p6`：正常回合 P6 一次性落盘、`seq` 严格连续。
- **文档同步**：§1.4、§2.1 IF-3、§2.2.1、§3.1、§7 ADR-08 均已统一为「emit 入缓冲区 / P6 唯一 append / 回滚丢弃整缓冲（含 P2 `LLM_CALL`）」。
- **结论**：**✅ 达标**（代码 + 最小用例 + 文档三方一致）。

### 10.2 D2 — 第三方许可证合规 ✅ 达标
- `code/THIRD_PARTY_NOTICES.md` 存在：登记 GA=Apache-2.0、AI Town=MIT，含上游 URL / 版权行 / 改编位置。
- `code/licenses/Apache-2.0.txt`（11357 B，首行 Apache License 2.0）、`licenses/MIT.txt`（1067 B，`Copyright (c) 2023 a16z-infra`）。
- **modified 标注**：`life/NOTICE`（按 Apache-2.0 §4(b) 逐文件列改编摘要）+ `frontend/NOTICE`；GA 派生源文件头亦标注（`life/agent.py`「adapted to…Apache-2.0」、`life/memory.py`「adapted reimplementation (see NOTICE)」、`life/persona.py`「modified/adapted reimplementation」）。
- **结论**：**✅ 达标**（MIT 保留声明；Apache-2.0 保留声明 / NOTICE / 标明修改均落实）。

### 10.3 D3 — 文档一致性 ✅ 达标
- §1.1 引言：已改为「…共 **11** 个一级域」（含 `contracts`）。
- §1.1 `config/` 目录树：已补 `perception_scope.json`、`narrative_weights.json`；目录标题改「config 核心五件 + 扩展两件」。
- §3.6 标题：已改「config **核心五件 + 扩展两件** + engine_version 指纹」（与 7 项一致）。
- **结论**：**✅ 达标**。

### 10.4 R7 / G1 — contracts 包 + import-linter 真跑绿 ✅ 达标
- `code/contracts/` 已落地：`interfaces.py`/`hooks.py`/`models.py`/`errors.py`/`__init__.py`。
- `.importlinter` 含 **8 条契约**（contracts-pure / engine-no-upstream / life-no-kernel / freeze-no-kernel-life / obs-read-only / obs-no-write-path / narrative-only-read / frontend-only-read）。
- **实跑**：`lint-imports` → **Contracts: 8 kept, 0 broken**（Analyzed 85 files, 209 dependencies）。观测层只读、life 不 import kernel 实现、kernel 零反向依赖、contracts 零业务依赖 **全部 KEPT**。
  - 声明例外（合理豁免）：`engine.cli`/`engine.integration → orchestration.integration`（组合根 shim，2 条）、`frontend.tools.gen_demo_log → life.run_demo`（离线演示脚本，1 条）——不削弱内核/观测边界。
- **回归**：`python -m pytest -q` → **111 passed**（较 T24 时 45 项显著扩充：emit 回滚、obs 黄金门禁 G2/G6、run 健康门禁等）。
- **结论**：**✅ 达标**。

### 10.5 复验新增发现（非阻塞）
- **N3（文档陈旧·低）**：§6.4「状态：待实现」注记现**部分过时**——`contracts/` 与 `.importlinter` 已落地、G2/G6 门禁已实现为 pytest（`test_obs_golden_gate.py`）；仅 **CI workflow 文件（`.github/workflows`）与完整 golden 基线**仍待补。建议 §6.4 更新为「部分落地」。**不阻塞放行。**
- **观察（实现进度，非放行条件）**：`code/config/` 暂缺 `activity_templates.json`/`policy.json`/`narrative_weights.json`/`engine_version.json`（蓝图 §3.6 列出）——属 P0 继续实现项，登记备查，非 D1/D2/D3/R7 范围。

### 10.6 复验结论：**四项放行条件全部达标 → 改判「无条件放行」（Unconditional Pass）**
- D1/D2/D3/R7 **全部达标**，均有可重跑证据（命令 + 结果）；未引入新的确定缺陷。原「有条件放行」**升级为无条件放行**。
- **保留登记**：R1–R6（并发/顺序模型声明、Q1 守恒口径、日志篡改边界/签名、LLM 注入/记忆投毒、侧存储完整性、容量系数标定）仍为**非阻塞风险**，按 leader 计划在 v1.2 收口逐条处置。
- **建议（非阻塞）**：更新 §6.4 状态注记（N3）；P0 完成后补齐 §3.6 其余 config 件。

---

*（复验记录 — delivery-reviewer，T36）*

---

## 11. 新增门禁登记：术语合规 · 棘轮（T50，2026-10-10）

> 由 design-synthesizer 交付（`glossary/`），Leader 裁定**纳入每轮验收清单**（与 `pytest -q` / `lint-imports` / `obs gate` 并列）。

| 项 | 内容 |
|---|---|
| 门禁命令 | `make lexicon-gate`（= `python3 glossary/tools/lint_terms.py --root . --baseline glossary/term_baseline.json`） |
| 语义 | **基线/棘轮**：仅当出现「基线之外的**新**违规」返回非 0；已知历史违规（`v1/**`）不报错 |
| 基线 | `glossary/term_baseline.json`（当前冻结 **50** 条，全部在历史目录 `v1/**`；活文档 0 违规） |
| 权威来源 | `glossary/LEXICON.md`（369 行，93 词条）+ `glossary/lexicon.json` |
| 扫描范围 | `social-experiment/**/*.md` 与 `code/**/*.py`（跳过 `glossary/` 自身、`__pycache__`、`data/`、`.jsonl`） |
| 命中分类 | `violation`（违规，计门禁）vs `mention`（别名/废弃说明，**不计**） |

**每轮验收清单（更新后）**：
1. `cd code && python -m pytest -q`（内核/冻结/obs 单测）
2. `lint-imports`（边界契约，`code/` 下）
3. `python -m obs gate --log <run>`（观测门禁 G1–G7）
4. **`make lexicon-gate`（术语合规 · 棘轮）** ← 本轮新增
5. 复现：`replay(log)` 状态哈希相等 + `metrics()` 两次字节相等

> 相关裁决：TC-10（文档编号）→ **RESOLVED**（现行编号为规范、旧序编号只作 mention）；TC-1（`M_supply` 口径）保持 **OPEN**，属用户未决 Q1。详见 `glossary/LEXICON.md §11`。

---

## 12. 口径时效标注：Fork B 变更对本次评审的影响（2026-10-12）

> 依据：Leader 2026-10-12 09:55 广播（用户 09:53 拍板）**Fork B ——「放开逐位可复现作为验收口径」**，同时保留「**全量日志 + 种子化随机 + 每份产物记 sha + 生成命令**」。
> 本节为**时效标注**，不删除 §1–§11 历史结论；旧文以本文为最新口径。

### 12.1 受影响的既有结论

| 本报告位置 | 旧口径表述 | Fork B 后的状态 |
|---|---|---|
| §0 分类口径 / §9 «C2» 行 | 以「同日志逐位一致 / `metrics()` 两次字节相等」为**验收红线** | **从验收红线降为诊断项**（可保留用于回归体检，但**不再作为放行门禁**） |
| §2「B3」/ §1.2 复验 | 「禁止 emergence 用 canonical_json → 字节漂移威胁 C2」 | 严重度**下降**：字节相等已非门禁，B3 的修补（白名单）仍**合理保留**，但不再具阻塞性 |
| §3「R2/R5」 | 侧存储完整性、守恒公式（Q1）——原挂 C2 | **不变**（属数据完整性/守恒，独立于复现口径） |
| §10.4 / §10.6 | 「无条件放行」依赖 G2「`metrics()` 两次字节相等」门禁 | 该门禁**移出放行条件**；T24 放行结论本身**自洽**（其他三项：contracts/import-linter、emit 回滚、许可证合规与复现口径无关） |
| §11 每轮验收清单 第 5 项 | 「复现：`replay(log)` 状态哈希相等 + `metrics()` 两次字节相等」 | **须改写**（见 12.2） |

### 12.2 建议的新验收清单第 5 项（待 Leader 确认）

```
5. 可追溯（Fork B）：日志全量落盘 + 随机种子化 + 每份产物记 sha256 与生成命令（可复算）
```
- 与旧项的差别：由「**输出字节相等**」改为「**输入/过程可追溯 + 产物 sha/命令可复算**」。
- **保留为诊断（非门禁）**：同日志 `replay(log)` 状态一致性、`metrics()` 可重算性——建议仍随 P0 报告**附带**，用于发现实现回归，但**不判 FAIL**。

### 12.3 需 Leader 裁决的口径歧义（1 项）

**Q-12.1**：Fork B ②「放开逐位可复现」是否**同时**放开「**同日志** replay 确定性（`replay(log)` = 纯折叠、确定性函数）」，还是仅放开「**跨跑**同 seed 字节一致」？
- 本次评审理解（默认）：**仅放开「输出字节相等作为门禁」**；`replay(log)` 的**代码确定性**仍应保持（否则哈希链/异常回滚 D1、turn_seal、审计均失去基础）。
- 若裁决为「连同日志确定性亦不要求」，则 §9 «C2» 行与 D1 的「C2 相关性」需再次下调，请知会我方改写。

### 12.4 对本报告结论的净影响

- **T24 最终结论（无条件放行）不因 Fork B 反转**：原放行的四项落地条件（D1/D2/D3/R7）与复现口径**相互独立**；Fork B 只是**降低了其中一项门禁的强度**。
- **后续所有架构/交付评审**改用 12.2 的可追溯口径；本条作为评审纪律的**最新时效口径**。

*（时效标注 — delivery-reviewer，2026-10-12）*
