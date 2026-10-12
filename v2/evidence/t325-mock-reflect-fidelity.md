# T325 · mock 反思文本保真度（含情感词）⇒ `PERSONA_DRIFT` 在 mock 下可 e2e 触发

> 作者：freeze-layer-dev ｜ 日期：2026-10-13 ｜ 域：freeze（`code/freeze/providers.py::MockProvider`）
> 依据：`life/agent.py::LifeLayerAgent._reflection_drift_events`（T244）、`_DRIFT_POS/_DRIFT_NEG`（26 子串）、T326 探针、T323 e2e。

---

## 0. 一句话

旧 mock 对自然语言用途一律返回 `mock::<sha256>`（**纯哈希、无句子**）⇒ `purpose=reflect` 的反思节点**必然**不含情感词 ⇒ `PERSONA_DRIFT` 在 mock 下**无法 e2e 触发**。本单只修**装置保真度**：让 mock 在自然语言用途产出**可读、带情绪**的句子。

## ⚠️ 保真度声明（最重要）

> **mock 可触发 ≠ 真世界可触发。** `T326` 真 LLM 探针（154 调用、无 mock）实测：**reflection 63 条、26 词表命中 `0/63`**，
> 但原文**有隐性情绪** ⇒ **主根因是判据太窄**（`T332`/`T333`，**life 域**）。
> **本单不解决真世界问题**；"mock 绿了"**不得**被误读为"人格漂移问题已解决"。

## 1. 改了什么（只改 mock 生成文本）

- 文件：`code/freeze/providers.py`
  - 新增**确定性文本池**（`_REFLECT_POOL` 8 句、`_DIALOGUE_POOL`/`_PLAN_POOL`/`_DESCRIBE_POOL`），`reflect` 池**每句至少含 1 个情感词**；
  - `MockProvider.complete`：无 `responder`/`options` 时，若 `extra.purpose ∈ {reflect, dialogue, plan, describe, narrate, negotiation, decide_t2}` → 从池中**按 `sha256(purpose+system+user)` 确定性取句**；其余用途（如 `importance`）保持 `mock::<hash>`。
- **未改**：世界语义、`config` 语义键、真 LLM 路径、软判定 `options` 分支。

## 2. 判定依据（"含情感词"）

`life/agent.py::LifeLayerAgent._reflection_drift_events`：对 `kind=="reflection"` 且 `importance>=min_importance` 的节点，
`sign = +1 if any(k in text.lower() for k in _DRIFT_POS) else (-1 if any(k in text.lower() for k in _DRIFT_NEG) else 0)`；
**`sign==0`（无情感词）→ 不产候选**。
26 子串 = `_DRIFT_POS`（帮助/成长/喜悦/连接/感谢/陪伴/温暖/成功/support/growth/joy/connect/thanks）
+ `_DRIFT_NEG`（冲突/失败/孤独/失去/争吵/痛苦/挫折/焦虑/conflict/loss/lonely/fail/struggle）。

## 3. 前后对照 + 5 条原文

| | 旧（before） | 新（after） |
|---|---|---|
| `purpose=reflect` 输出 | `mock::<hash>（insight 1）`（纯哈希，情感词命中 **0**） | 可读句子，**含情感词** |
| 情感词命中 | 0/样本 | **12/12**（单测） |

新 5 条原文（`MockProvider`，`purpose=reflect`）：
```
和同伴把集市收拾干净，感到被陪伴，挺开心。        命中：陪伴
和同伴把集市收拾干净，感到被陪伴，挺开心。        命中：陪伴
今天帮邻居修好了篱笆，心里踏实又有点温暖。        命中：温暖
和旧友重逢那一刻，忽然觉得人和人的连接很珍贵。    命中：连接
这段时间总觉着孤独，像被热闹落下了一样。          命中：孤独
```

## 4. `PERSONA_DRIFT` e2e 触发（用的哪个键值）

两个连续窗口的 mock 反思节点（每窗 3 条 `insight 1/2/3`、`importance 6/7/8`、`mem_id=M-w{win}-{i}`）
喂入 `_reflection_drift_events`（`min_windows=2`、`min_importance=7`、`delta_max=1`）：

- window 1 → `[]`（单窗=抖动，不发）；
- **window 2 → 发 `PERSONA_DRIFT`**：
```json
[ {"dim": "openness",        "delta":  1, "cause_mem_id": "M-w1-1"},
  {"dim": "extraversion",    "delta": -1, "cause_mem_id": "M-w1-2"} ]
```
**用的键值**：`dim ∈ {openness, extraversion}`、`delta ∈ {+1,-1}`（幅度=`delta_max`）、`cause_mem_id` 指向首窗反思节点。

> 复现：`python3 -m pytest -q tests/test_t325_mock_reflect.py`（含本 e2e 用例）→ 5 passed。

## 5. 回归 / 门禁

- `python3 -m pytest -q` → **591 passed**（旧 mock 文本改动**无 golden 破坏**）。
- `tools/t271` 相关：多跑对比分进程（本单未跑多跑对照）。
- `make verify`：见提交/频道（与 kernel 错开）。
- `v2/evidence/t103_dialogue_real_llm.json` 已重生成：mock 侧正文由 `mock::<hash>` 变为**可读句**（分叉仍 6/6）。
