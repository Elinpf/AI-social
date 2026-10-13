# T361 · `LLM_CALL` 调用主体归属（`agent_id`）实现

> 作者：freeze-layer-dev ｜ 日期：2026-10-13 ｜ 域：freeze（emitter 在 freeze）
> 口径唯一准：`v1.1/08-engine-stats-extension.md §1.2 G-lg`（T360 登记，提交 `9ca29ff`）。

---

## 1. 改了什么（仅字段增）

| 文件 | 改动 |
|---|---|
| `code/freeze/events.py::llm_call_payload` | 新增**可选** `agent_id`；**仅在给出时写入**该键（缺省不写 ⇒ 旧日志兼容）。 |
| `code/freeze/llm_client.py::_emit_call` | 从 `meta["agent_id"]` **提升**为一等 payload 字段；无则**不写**（= `UNATTRIBUTED`）。 |
| `code/tests/test_t361_llmcall_agent_id.py` | 新增 5 测试（提升/缺省/非居民/helper 可选/旧日志读回）。 |

**未改**：`actor`（仍 `SYSTEM`）、事件类型、fold 语义、判定/事件顺序、**life 侧**（`life` 的 4 处 `.call(...)` **已**带 `meta={"agent_id":...}`，**无需改**）⇒ **本项无跨域改动**。

口径（照登记）：`LLM_CALL.agent_id` 可选，取值 ∈ `AgentId ∪ {SYSTEM, DIRECTOR, OBSERVER}`，**缺省（不写键）= `UNATTRIBUTED`**；消费方须先 `is_agent_actor()` 守卫；非 Agent 主体不伪装成居民。

## 2. 旧日志兼容

- 新字段**可选**：旧日志 payload 无 `agent_id` 键 ⇒ 读回 `.get("agent_id") is None`（`UNATTRIBUTED`），**不抛错、不改语义**（测试 `test_replay_reparses_payload_without_agent_id`）。

## 3. 同 seed 抽样（mock，`seed=7 / N=3 / 12 回合`）

共 **60** 条 `LLM_CALL`；按 `(purpose, agent_id)`：

| purpose | agent_id | 条数 |
|---|---|---|
| plan | P001 / P002 / P003 | 1 / 1 / 1 |
| dialogue | P001 / P002 / P003 | 2 / 3 / 1 |
| reflect | P001 / P003 | 1 / 1 |
| importance | P001 / P002 / P003 | 6 / 5 / 5 |
| **judge** | **`<absent>`（未归属）** | **33** |

抽样 8 条（`seq / purpose / actor / agent_id`）：
```
  9 judge     actor=SYSTEM agent_id=<absent>
 11 plan      actor=SYSTEM agent_id=P001
 18 judge     actor=SYSTEM agent_id=<absent>
 20 plan      actor=SYSTEM agent_id=P002
 26 dialogue  actor=SYSTEM agent_id=P002
 29 judge     actor=SYSTEM agent_id=<absent>
 31 plan      actor=SYSTEM agent_id=P003
 78 importance actor=SYSTEM agent_id=P001
```
⇒ **可按居民归属**（plan/dialogue/reflect/importance）；`actor` 仍 `SYSTEM`（未改）。

> ⚠️ **待登记方确认的缺口**：`judge`（33/60，**最大一类**）**未归属**——其 `meta` 无 `agent_id`，
> 且判定涉及 `parties[]`（多主体），**单一 `agent_id` 语义不明**。按登记「枚举覆盖不到回来找我」，
> 我**未在码里绕**：暂缺省（`UNATTRIBUTED`）。**若需按发起居民归属 judge，请补登记**（life 侧传参）。

## 4. 重冻影响声明（照 T360 §5）

- `state_hash` **不变**（`LLM_CALL` 属 identity fold / 不入状态）；
- **日志哈希链变**（`compute_event_hash` 覆盖含 payload）⇒ 归 **【行为不变/仅日志字段增（哈希链变）】**；
- `engine_version` 指纹 **不变**（不新增 config 键）；
- ⇒ **需重冻，归入 `T355` 同一 epoch（零额外成本）**；
- **T299 语义门**：`agent_id` 是**语义字段**，**不得**进「纯计量白名单」；跨 epoch 对照须标注「唯一差异 = 指纹行及其派生 + `LLM_CALL.agent_id` 新增字段」。

## 5. 门禁

- `python3 -m pytest -q tests/test_t361_llmcall_agent_id.py` → **5 passed**。
- `make verify` → 见提交/频道（同刻只跑一个；`T340` 门报"可信"）。
- **本单不自标 `completed`**（等 `T355` 清日志/哈希读数）。
