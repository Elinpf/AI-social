# T361 · T307 自查（新字段是否牵动门禁）+ 解冻后待办清单

> 作者：freeze-layer-dev ｜ 日期：2026-10-13 ｜ 只读/文档，不跑重活（T350 运行期）。
> 新字段 = `LLM_CALL.agent_id`、`LLM_CALL.judgment_id`（T360 登记；实现 `e1ac81d`/`8a7dc16`）。

---

## 1. 自查结论（三问）

### ① 是否被任何门禁/计量路径当"字段比对对象"？（T299 语义一致门）
- T299 门 = `tools/t271/semantic_log_sha.py`：`EXCLUDE = {cached, tokens_in, tokens_out, cost_units}`（**白名单式**，仅在 `LLM_CALL.payload` 内），其余字段**全部参与比较**。
- **判定：`agent_id`/`judgment_id` 属【审计/归属】字段，非【纯计量】字段** ⇒ 按 T307-i「**纯计量才入 `EXCLUDE`；语义/配置字段不得加入；拿不准一律不排**」⇒ **两个字段都【不得】加入 `EXCLUDE`**。
  - **理由**：加入 = **假绿**（把一次真实的跨 epoch schema 差异掩盖成"语义相同"）；它们**不影响 world 语义**（`LLM_CALL` 属 `_NOOP_TYPES`、不入 `state_hash`），但**也不影响 freeze 缓存命中/计费** ⇒ 不满足"纯计量"定义。
- **后果（预期、需标注）**：**跨 epoch**（T361 前/后）`semantic_log_sha` 会**不同** —— 这是**真实差异**，非假红；须按登记在跨 epoch 对照注明：
  > **唯一差异 = 指纹行及其派生 + `LLM_CALL.agent_id`/`judgment_id` 新增字段**。
  - **同一 epoch 内**（同代码续跑 vs 一次跑）**不受影响**（两边都有该字段）。

### ② `engine_version` 指纹 / schema 硬编码字段全集？
- `engine_version` 指纹 **不变**（不新增 `config` 键）；`engine/version.py::FINGERPRINT_FILES` 列的是 **config 文件**，**非事件字段** ⇒ **无需同步**。
- `engine/replay.py::_NOOP_TYPES` 按 **type**（非字段）：`LLM_CALL` 早已在列 ⇒ 新字段不改类型、不改 `state_hash`（与声明一致）。
- `obs/atomic.py::REQUIRED_FIELDS`：**不含 `LLM_CALL`**；`obs/gate.py` 的 "15 §5 规定字段" 检查是**存在性检查**（缺→FAIL），**无"精确字段集/禁多余字段"**校验 ⇒ **新可选字段不可能触发门禁**。

### ③ 旧日志兼容 + 反向负例
- **正向**（旧日志无键 ⇒ `None`/`UNATTRIBUTED`，不抛错）：`tests/test_t361_llmcall_agent_id.py::test_replay_reparses_payload_without_agent_id` ✓。
- **反向负例**（缺省**不得**被"假装成某居民"）：`tests/test_t361_judge_linkage_e2e.py::test_unattributed_llm_call_is_not_attributed_to_anyone` —— 无 `agent_id`/`judgment_id` 的 `LLM_CALL` **对任何居民轨迹都不得命中**（若命中即红）✓。
- 全部 T361 测试：**9 passed**。

## 2. 解冻后待办清单

| # | 项 | 谁 | 需非作者复跑？ |
|---|---|---|---|
| 1 | **跑 `make verify`**（T350 结束后）；绿 ⇒ 按 Leader 口径可标 `T361` completed | freeze（我） | 否（门禁运行） |
| 2 | T355 epoch 重冻时：跨 epoch 对照**注明唯一差异**（含 `agent_id`/`judgment_id` 新增字段） | obs / T355 | — |
| 3 | **`semantic_log_sha.py` 是否需改 `EXCLUDE`**：**结论=不改**（见 §1①）。若 obs 日后判定要改 ⇒ **改门须非作者复跑 `--selftest`（T307-i）** | obs（若改） | **是**（若改门） |
| 4 | T299 门 `--selftest` 复跑确认（不改门则**非必跑**，可作为回归） | obs | —（若改门则需非作者） |

## 3. 一句话
**新字段不牵动任何门禁/指纹/字段全集校验**；T299 白名单**刻意不放**它们（放=假绿）；兼容与反向负例均有测试。**唯一解冻后动作 = 跑 `make verify`**。
