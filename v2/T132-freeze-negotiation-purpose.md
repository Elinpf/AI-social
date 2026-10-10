# T132 · freeze 支持 `LLM_CALL.purpose=negotiation`

> 作者：freeze-layer-dev ｜ 日期：2026-10-10
> 范围：**只做"放行 `negotiation`"**（白名单 + 缓存 + thinking 策略 + 审计）；**不改 `negotiation` 语义**（合法性/结算在确定性内核，属 T131）。
> 依据：`v1.1/08 §1.2 R`（已登记 `negotiation`）、`v2/04-exchange-and-contracts.md`、T126 设计。

---

## 1. 我改了什么

| 文件 | 改动 |
|---|---|
| `code/freeze/config.py` | `ALLOWED_PURPOSES += "negotiation"`（含注释：只产内容/条款，不判可行性、不写账） |
| `code/life/llm.py` | `ALLOWED_PURPOSES += "negotiation"`（与 freeze 对齐；覆盖 RuleBasedLLM 回退路径） |
| `code/tests/test_freeze.py` | 新增 3 个测试：`test_negotiation_purpose_end_to_end`、`test_unknown_purpose_still_rejected`、`test_negotiation_whitelists_aligned` |
| `v2/T132-freeze-negotiation-purpose.md` | 本证据/说明 |

**缓存/thinking**：无需新增代码——`negotiation` 走与 `dialogue` 完全相同的路径：
`complete(purpose, tier, ...)` → `params` 含 `thinking` → **进缓存键**（键 = `engine_version + prompt_hash + model + tier + params`）。

**thinking 策略**（用户拍板，由既有 `ThinkingPolicy` 天然满足，不散落硬编码）：
- 居民议价 `tier=T1` → `thinking=false`（`true_purposes` 不含 negotiation）；
- 世界 LLM 议价 `tier=T2` → `thinking=true`（`true_tiers={"T2"}`）。

**审计**：`LLM_CALL{purpose="negotiation", ...}` 由 obs 动态按 purpose 汇总
（`obs.llmcost.llm_cost_from_records` 不硬编码 purpose 集合），测试已覆盖。

## 2. 依赖方改了什么

- **kernel-dev（T131/T126）**：engine 原语（`exchange.py`/`econ.py`/`production.py`）——**本项不依赖**，可并行；`negotiation` 语义（内容/条款 vs 结算）归其确定性内核。
- **life-layer-dev（T126/life 侧）**：`agent` 议价调用点将用 `purpose="negotiation"`——白名单已就绪。

## 3. 未动什么

- **未改 `negotiation` 的语义**（不产金额/不判可行性/不写账）。
- **未改 `ThinkingPolicy` 逻辑**、`FORBIDDEN_PURPOSES`、缓存键结构、预算闸门。
- **未放水未知 purpose**：`assert_purpose_allowed` 白头外仍 `raise ValueError`（专项测试）。
- 未改 `08 §1.2 R`（已登记，无需动）。

---

## 4. 验证

```
$ python3 -m pytest -q tests/test_freeze.py     # 44 passed
$ python3 -m pytest -q                          # 284 passed（≥ 基线 281）
$ lint-imports                                  # Contracts: 8 kept, 0 broken
```

要点：
- `test_negotiation_purpose_end_to_end`：居民(T1)→`thinking=false`、世界(T2)→`thinking=true`；不同缓存键；**重放 `llm_calls==0`**；obs 可按 purpose 统计。
- `test_unknown_purpose_still_rejected`：未登记 purpose → `ValueError`，`llm_calls==0`（不放水）。
- `test_negotiation_whitelists_aligned`：freeze 与 life 白名单均含 `negotiation`（两处对齐）。
