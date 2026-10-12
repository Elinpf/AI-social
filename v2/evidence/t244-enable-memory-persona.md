# T244 证据：启用记忆/人格三族（睡眠窗 + 遗忘 + 人格漂移）

> 作者：persona-life-designer｜日期：2026-10-12
> 结论一句话：**T244 不是"改默认值"，而是"把从未接通的内核装配线路接通"** —— 翻开关本身**不生效**（三族恒 0），根因与修复如下。

---

## 0. 关键发现：翻开关 ≠ 生效

| 运行 | 目标三族事件 | 总事件 | `INTENT_REJECTED` |
|---|---|---|---|
| **OFF**（原默认） | 全 0 | 5287 | 5 |
| **仅翻 `life_v2.json` ON（未接线）** | **仍全 0** | 8068 | **2786** |
| **ON + W1 接线**（本次交付） | 见 §2 | 8161 | 5 |

**根因（代码级）**：`code/orchestration/integration.py::_do_memory` 原先**只实现 `write/retrieve/reflect`**，**没有** `sleep_start / sleep_end / forget / consolidate` → 这 4 类 `INTENT.MEMORY` 一律 `unsupported` 被拒（`INTENT_REJECTED` 5→2786）。
→ 即 **T224 的"睡眠窗/遗忘"从未接通内核装配点**；T224 单测走的是 `run_sleep_window()` 直调 + mini_kernel，**绕过真装配** → "绿了"但系统永不走这条路（与 T235「装配点丢字段」同族）。

---

## 1. W1 修复（本次，integration.py）

在 `_do_memory` 补 4 个 op（非货币、纯审计/记忆结构、确定性、无 LLM）：
- `sleep_start` → `SLEEP_STARTED{agent_id,day,slot,planned_ticks}`
- `sleep_end` → `SLEEP_COMPLETED{agent_id,day,slot,actual_ticks,pf0,pf_t,drift_permille}`
- `forget` → `MEMORY_FORGET{agent_id,mem_id,level,retention_permille,reason,protected,protection_reason,day,slot}`
- `consolidate` → `MEMORY_CONSOLIDATE{agent_id,subject,source_mem_ids,produced_mem_id,day,slot}`

字段按 `v1.1/08-engine-stats-extension.md §1.2 S`；并**补** `protected/protection_reason` 透传（消除同族"装配点丢字段"）。

---

## 2. 开关对照实测（n=3、84 回合=1 模拟周、seed 7、mock LLM）

**命令**：
```
cd code && python -c "from orchestration.integration import run_e2e; run_e2e(seed=7, rounds=84, n=3, out_path='/tmp/t244_on2.jsonl')"
```
**真装配点日志 `grep`（Leader 要求的验收：必须能在能被世界看见的地方 grep 到）**：

| 事件 | ON（W1 后） | OFF |
|---|---|---|
| `SLEEP_STARTED` | **21** | 0 |
| `SLEEP_COMPLETED` | **21** | 0 |
| `MEMORY_CONSOLIDATE` | **60** | 0 |
| `MEMORY_FORGET` | **2712** | 0 |
| `PERSONA_DRIFT` | 0（mock）/**75**（语义反思 stub，见 §2.1，真装配） | 0 |
| 守恒/链/重放 | `conservation_ok=True` / `chain_ok=True` / `replay_parity=True` | 同 |

**`metrics.life.memory`（ON，obs 只读日志复算）**：
- `forget_count=2712`，**三级分布** `demote=1791 / merge=572 / drop=349`；
- `retention_hist`（千分比，非空箱）：`0-99:14, 100-199:401, 200-299:516, 300-399:681, 400-499:687, 500-599:413`；
- `consolidate_count=60`，`consolidate_source_count=2353`；
- ⚠️→✅ `protected_kept`：1 周 mock run 曾为 0；**W2（`6ffedde`）补传后已 >0** —— 2 周语义 proof run：`protected_kept=1129`（`forget_count=13655`，三级 `demote/merge/drop=4683/4782/4190`）。

**成本影响**：
```
LLM_CALL  OFF: calls=154 tokens_in=944 tokens_out=944 total=1888
LLM_CALL  ON : calls=154 tokens_in=944 tokens_out=944 total=1888   → 增量 = 0
```
→ **睡眠/遗忘/整合为纯整数模块，零新增 LLM 调用、零 token 增量**；仅日志事件量 5287→8161（+2874，压缩后小）。**50+ agent 负担得起。**

---

## 3. 消融 / 回退

- **独立消融**：`life_v2.json::sleep.enabled` 与 `::forgetting.enabled` **各自独立**；
- `PERSONA_DRIFT` **无独立开关**，**随睡眠窗流程**（`sleep_window.enabled = sleep.enabled OR forgetting.enabled`）——已写入登记表 `default_state_note`；
- **回退方式**：把 `config/life_v2.json` 的 `sleep.enabled` / `forgetting.enabled` 改回 `false` 即回到现状（该文件纳入 `engine_version` 指纹，改动即变指纹，属预期）。

---

## 4. `PERSONA_DRIFT`：后退一步，是**整条通路缺两环**（不是情感门）

**实测（语义 reflect stub 直调 `_reflection_drift_events()`）**：候选生成逻辑**本身没问题** ——
连续两窗返回候选：`[{dim:conscientiousness,delta:1},{dim:neuroticism,delta:1}]`（importance≥7 的反思节点存在：6/6/7/7/8/8；且 stub 文本含情感词）。✓

**但 `PERSONA_DRIFT` 仍为 0，真因是通路缺两环**（grep 确认）：
1. **`agent._maybe_sleep_window` 从不提交 drift 意图**（`run_sleep_window` 产出的 `PERSONA_DRIFT` 事件没人 submit）；
2. **`orchestration/integration.py::_do_memory` 没有 `drift` op**（所以即便提交也被拒）。

**处置**：
- **②（我，W1）已补**：`_do_memory` 新增 `op=="drift"` → 发 `PERSONA_DRIFT{agent_id,dim,before,after,anchor,cause_mem_id,pf0,pf_t,drift_permille,day,slot}`（08 §1.2 S）✓；
- **①（W2b，life-layer-dev，`agent.py`）已交办**：把 `out["persona"]`/候选逐个 submit（一维一事件；单窗不发）。

**两步式举证（Leader 口径）——✅ 第二步已补齐**：
- 第一步（线路）✓：候选生成 + 事件装配（W1 `_do_memory op=drift`）+ agent 提交（W2b `9553368`）三环到位；
- 第二步（语义输入下能非零）✓ **真装配 run**（非直调）：`run_e2e(seed=7, rounds=168, n=3, llm=SemanticReflectLLM())` → **`PERSONA_DRIFT=75`**、`metrics.life.persona.drift_by_dim={openness:17,extraversion:17,neuroticism:15,agreeableness:14,conscientiousness:12}`、`drift_permille.mean=6.67/max=10/min=4`；`chain/replay/conservation` 全绿。
  命令：注入 reflect→含情感词的语义文本的 `RuleBasedLLM` 子类，经 `orchestration.integration.run_e2e` 跑 n=3/168 回合。
- **说明（诚实标注）**：本环境 `LLM_API_KEY` 未设置，无法跑真 LLM；以"语义 stub 走真装配"替代。**纯 mock 下 `PERSONA_DRIFT=0` 是设计使然**（`RuleBasedLLM` 反思文本 `（反思）…照常作息…` 无情感词 → 情感门不发）——**0 = "无语义输入"，不等于"人格漂移不发生"**。

`protected_kept`：W2 已提交（`6ffedde`），`forget` 保护字段已透传（life-layer-dev 实测 33751/33751 带 `protected`）✓。

---

## 5. 同族排查：还有哪些一等开关默认关（engine/kernel 侧实测清单）

**默认 OFF（要留意）**：
- `life_v2.json::sleep.enabled` → **T244 已开**
- `life_v2.json::forgetting.enabled` → **T244 已开**
- `world_director.json::enabled` = false（**总闸**；其子机制 `festival/edict/tension.enabled=true` 但被总闸钳制 → **有效默认 = 父闸 AND 自身**，登记表 `default_state` 须写明）
- `world_director.json::mechanisms.{visitor,supply_shock,disaster,epidemic,public_works,season,mass_event}.enabled` = false

**默认 ON（对照）**：`policy.json::{llm_budget,economy,lifecycle,social,production,exchange}.enabled` = true；`life.memory.persist_vec=true`、`life.narrative.persist_body=true`。

> 口径：`status`（有没有活）与 `default_state`（默认开不开）是**两个维度**；"父闸 OFF 钳制子 ON"须写**有效默认 = 父 AND 自身**。

---

## 6. 交付物与 sha

- 代码：`code/orchestration/integration.py`（W1 接线）、`code/config/life_v2.json`（开启 + 可回退）、`code/life/tests/test_t224_sleep_window.py`（默认开/显式关 两路）
- 登记表：`tools/inert_registry.json`（5 条 `default_state` on + 回退/有效默认注记）
- 本证据：`v2/evidence/t244-enable-memory-persona.md`
- 命令与输出见 §2；门禁：`python -m pytest -q`（全绿）+ `make lexicon-gate`（新增违规 0）
