# T287 期① off 对照实验（开关默认 off ⇒ 零行为变化）

**日期** 2026-10-12 · **作者** kernel-dev · **性质** 对照实验证据（同种子、off vs 现状逐条比对）

## 方法（对照，不是"我保证"）

- **参照（现状）**：`git stash` 暂存本期改动 → 于**原 HEAD 代码**上跑 `run_e2e(seed=42, rounds=12, n=4)`（mock LLM）→ `/tmp/t287_ref.jsonl`；随后 `git stash pop` 恢复改动。
- **对照（off）**：新代码、`config/time.json` 全部默认 off → 同参数 → `/tmp/t287_off.jsonl`。
- 两者事件条数相同：**1635**。

## 结果

| 比对口径 | 结果 |
|---|---|
| 逐条内容（剥离 `hash`/`prev_hash`）| **118 条差异** |
| 逐条内容（再剥离**指纹派生**字段：`WORLD_INIT.{fingerprint,config_digest,config_components,time_model,time_U}`、`LLM_CALL.{engine_version,cache_key}`、`TURN_SEAL.{last_hash,state_hash}`）| **0 / 1635 差异** ✓ |
| `TURN_SEAL.state_hash` 序列 | **完全相等** ✓ |
| `code/tests` 全量 | **494 passed** ✓ |

## 唯一差异 = 指纹行及其派生（显式标注）

- `config/time.json` 新增并**加入 `FINGERPRINT_FILES`**（Leader 裁定：开关进指纹） ⇒
  `WORLD_INIT.fingerprint` / `config_digest` / `config_components` 变；
- 链哈希随之变（`hash`/`prev_hash`/`TURN_SEAL.last_hash`）；
- `LLM_CALL.payload.engine_version`（=指纹）及其派生 `cache_key` 变；
- `WORLD_INIT` 新增 `time_model="atomic"` / `time_U=6`（**总是**写，跨 sha 自描述）。

⇒ **无任何行为/判定/`state_hash` 变化**；与 Leader 修订口径（与 `wake.enabled=false` 同构）一致。

## on 时可用性（单测）

`tests/test_t287_time_model.py`：`span_bounds` 缺省=瞬时；`derive_order` 语义序 `(start_μt,actor,seq)` 确定性；`time_model_of` = `atomic`/`interval-U6`；on 时 `span` 落账、`TURN_SEAL` 带戳；**回退=忽略字段**（无 span 事件=瞬时，向后兼容）。

## 未做（诚实边界）

- `same-agent` 独占重叠的**可解释拒绝**属期②/③行为（本期只加字段+纯函数+戳，**默认 off 不启用**），故本期未触发放射/拒绝路径。
