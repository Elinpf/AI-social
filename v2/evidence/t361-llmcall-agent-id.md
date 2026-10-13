# T361 · `LLM_CALL` 调用主体归属（`agent_id`）实现

> 作者：freeze-layer-dev ｜ 日期：2026-10-13 ｜ 域：freeze（emitter 在 freeze）
> 口径唯一准：`v1.1/08-engine-stats-extension.md §1.2 G-lg`（T360 登记，提交 `9ca29ff`）。

---

## 1. 改了什么（仅字段增）

| 文件 | 改动 |
|---|---|
| `code/freeze/events.py::llm_call_payload` | 新增**可选** `agent_id` **与** `judgment_id`；**仅在给出时写入**该键（缺省不写 ⇒ 旧日志兼容）。 |
| `code/freeze/llm_client.py::_emit_call` | 从 `meta` **提升** `agent_id`（主体归属）**与** `judgment_id`（轨迹 linkage，G-lg-1）为一等 payload 字段；无则**不写**。 |
| `code/tests/test_t361_llmcall_agent_id.py` | 新增 7 测试（提升/缺省/非居民/helper 可选/旧日志读回/judge linkage）。 |

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

---

## 6. 补登记 G-lg-1（judge 轨迹 linkage）+ 裁定落实

**T360 补登记**（`§1.2 G-lg-1`，提交 `4d57826`）分两条、不可混：
- **① 成本归属（单主）**：`LLM_CALL.agent_id` 缺省 = `UNATTRIBUTED` —— judge 多主体，**不伪装成某居民**；
- **② 轨迹可见（可多主）**：`LLM_CALL` 增可选 **`judgment_id`**（复用「三事件分列」既有 linkage）。
  「居民 `R` 的调用轨迹」= `{LLM_CALL: agent_id==R}` ∪ `{LLM_CALL: judgment_id ∈ {LLM_JUDGMENT: R ∈ parties}}`。
  **单一真源在 `LLM_JUDGMENT.parties`**，`LLM_CALL` 不自存 `parties`。

**实现**：`freeze.judge()` 的 `meta` 已带 `judgment_id` ⇒ `_emit_call` 单点提升为 `LLM_CALL.judgment_id`（**无需 life 传参、无跨域**）。测试 `test_judge_llm_call_carries_judgment_id_linkage` 覆盖。

### 6.1 `judge` 33/60 未归属 —— 是**正确缺省，不是漏项**

> ⚠️ **写清**：抽样中 `judge` **33/60** 的 `LLM_CALL` **`agent_id` 缺省**（= `UNATTRIBUTED`），
> **原因 = `judge` 涉多 `parties[]`、单归属语义不明**，按口径**不臆造、不归属**。
> **这不是漏做**；勿把 55% 覆盖率误读成缺陷。其**轨迹可见性**经 `judgment_id` linkage 覆盖（②）。

### 6.2 提交窗口自证（Leader 要求）：T350 读的是**副本**，非主树

自查（`ps` + run 目录 `meta.json`）：
```
workdir = /tmp/t271-probe50/code          # 读的是 /tmp 副本
sha     = 10428f247de6a92ba853884f6040fe1944998ee0
worktree= null
```
⇒ T350（12:40 起跑）读 **`/tmp/t271-probe50/code` @ `10428f24`**（**主树映射 0**）；
我的提交 `e1ac81d`（13:35/主树）**不在该副本内**，且跑步进程启动即 import ⇒ **对 T350 零影响**。
⚠️ 但如实记：**该批起跑时 Leader 漏发预告**（Leader 已认领并补广播）——此"运气对"非"流程对"。

### 6.3 `make verify` 状态

**暂缓**：T350（N=50×12 真 LLM）至 13:37 仍在跑（计时测量期 + 世界层批）⇒ 按机制②**不跑** verify。
待 T350 结束、Leader 广播解冻后运行并回填结果。**本单不自标 `completed`**。

---

## 7. 端到端自证：judge 链路真落到居民（+ 负例）

> 硬要求（Leader，经 sim-arch 转达）：**"推过去了 ≠ 真被消费"** ⇒ 抽一条**真链路** + 一条**负例**（防假绿）。
> 测试：`code/tests/test_t361_judge_linkage_e2e.py`（mock，seed=7/N=3/12 回合）。

**真链路**（实跑输出）：
```
[CHAIN] LLM_CALL seq=9  purpose=judge  agent_id=None  judgment_id=JF-P001-0
        -> LLM_JUDGMENT jid=JF-P001-0  parties=['P001']
        -> resident P001 轨迹命中 judge_link ✓（成本归属仍为 null）
[NEGATIVE] 非 party 居民 P002 反查该 judge 调用 -> 无命中 ✓（防假绿）
```

轨迹查询口径（**仅可见性/追溯，非成本**）：
```
trace(R) = {LLM_CALL: agent_id==R}
         ∪ {LLM_CALL: judgment_id ∈ {LLM_JUDGMENT: R ∈ parties}}
```

**两条查询口径不互相污染**（Leader 13:39 冻结 `43b725b`）：
- **成本归属**：judge 的 `LLM_CALL.agent_id` **恒为 `null`**（本测试断言）；**按居民聚合成本/调用数不得摊 judge**；
- **可见性**：`judgment_id` **只用于追溯**，**不得反推成本**。

⇒ **"推过去了（字段写了）"与"真被消费（能按居民反查到）"均自证**；负例证明**反查不到时为红**。
