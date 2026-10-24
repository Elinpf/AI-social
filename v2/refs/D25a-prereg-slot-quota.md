# D2.5a 预登记 · **每时段消息配额 2 → 3**（`max_messages_per_slot`）

> 立此存照：**2026-10-24，在任何 D2.5a 跑批之前**。判据、阈值、反事实先写死。
> 依据：`v2/evidence/d24_flow_limits.md`（配额饱和 77.7%、6 条封顶 45.6%）、
> `v2/evidence/d25_quota_bottleneck.md`（封顶线程 57.7% 被配额掐、放到 3 可解锁 100%）。
> 锚点：master HEAD = `f0eb3f7`。

## 1. 目标

居民**每时段固定只能说 2 句**，无论对话聊到哪里都停 ⇒ 对话"短、齐、机械"。
本臂只放宽这一条配额到 **3**，看对话能否自然延伸（而非靠复述填充）。

## 2. 改动方式（**必须走 override，不改文件**）

```
--override life_v2.dialogue.max_messages_per_slot=3
```
- 依据 runbook §3.116：改 `config/life_v2.json` 文件会改 `engine_version` 指纹 ⇒ 毁掉全部历史对照；override 不落盘、不改指纹。
- **单变量**：`max_turns=6`、`max_turns_per_round=2`、`reply_window_rounds=4`、`history_turns=3`、`max_thread_chars=240` **一律不动**；
- **不改任何 `.py`**，不改提示词（`prompt_fn_sha256` 必须与 T0 逐字节一致，作为接线自检）。

## 3. 臂

| 臂 | override |
|---|---|
| **C 基线** | 无 override（`max_messages_per_slot=2`） |
| **B 本臂** | `life_v2.dialogue.max_messages_per_slot=3` |

> 本臂**没有映射伪影问题**（不改抽样函数），故不需要 §3.115 的等权档；但**必须**用同一份代码同一 seed 跑 C，不得拿历史 T0 日志直接当 C。

## 4. 判据（跑前写死）

| # | 指标 | 达标线 | 未达的档位 |
|---|---|---|---|
| **M1 机制生效** | `slot_saturated_rate`（每 (agent,slot) 达到 3 条的比例）+ `n_msgs_total` | `n_msgs_total` 相对 C **↑ ≥ 10%**，且 `slot_saturated_rate(≥3)` **≥ 20%** | 判**「机制未生效」** |
| **P 主判据** | `threads_ge6_rate`（线程 ≥6 条比例） | 相对 C **↑ ≥ 15pp**（C 预期 45.6%） | 判**「无效（效果不足）」** |
| **Q1 质量闸（防复述）** | `L-15 restate_rate`（`tools/d5/l15_restate_rate.py`） | 相对 C **↑ ≤ 2.0pp** | 破 ⇒ **「无效（加长靠复述）」** |
| **Q2 质量闸（防重复）** | `L-7 norm8`（`tools/d5/dialogue_metrics.py`） | 相对 C **恶化 ≤ 3.0pp** | 破 ⇒ **「无效（加长靠重复）」** |
| **Q3 质量闸（防跑题）** | `F-2_content_drift`（= F-2′，**不用** `F-2_topic_drift`） | 相对 C **降 ≤ 2.0pp** | 破 ⇒ **「无效（内容漂移）」** |
| **S 保结构** | `n_threads` | 相对 C **±10%** | 破 ⇒ **「作废（非单变量）」** |
| **T 文体闸** | `tools/d12h/shape_gate.py` F1/F2/F3（F2 已修 strict 36.47%） | 全 PASS | 破 ⇒ **「作废（形态漂移）」** |
| **代价闸** | `llm_cost.calls` | 相对 C **≤ +50%** | 破 ⇒ **「作废（代价超限）」**，只记数不换算金额 |

## 5. 反事实（跑前写死）

| 观察 | 判定词 |
|---|---|
| M1 过 + P 过 + Q1/Q2/Q3 过 + S/T/代价 过 | **有效** |
| M1 过、`n_msgs↑` 但 `threads_ge6_rate` 不动 | **无效（只是多开话头，没聊更久）** |
| M1 过、P 过、Q1 破（复述↑>2pp） | **无效（加长靠复述）** |
| M1 过、P 过、Q2 破（重复恶化>3pp） | **无效（加长靠重复）** |
| P 过、T 破 | **作废（形态漂移）** |
| calls > +50% | **作废（代价超限）** |
| M1 未过 | **机制未生效**（查 override 是否真读到：`meta` 里记生效参数） |

## 6. 执行

- 规模 n16r60 seed42，**两臂串行**（C 先、B 后）≈ 2×52min ≈ 1.8h；B 臂 calls 预期 +30~50%。
- 起跑前 `pgrep` 确认无在跑批；跑批期间禁改 `code/life|orchestration|config|engine`。
- **必须在 `meta.json` 里落盘生效参数**（证明 override 真被读到，而不是静默失败）——这是本臂的接线证据。
- 真 LLM 验真：`obs llm-cost --require-provider openai_compat`。
- 交付：`v2/evidence/d25a_result.md` + 五组读数 + `run_batch.rc/end` + 成本。

## 7. 失效条件（跑前声明）

1. override 未被读到（`meta.json` 里 `max_messages_per_slot` 仍为 2）⇒ **作废（接线失败）**，不计入判定；
2. `max_turns_per_round=2` 在 B 臂变成新主约束（`round_capped_rate` 很高）⇒ P 判据不达标属**预期内的瓶颈转移**，判定仍按表走，但报告须写明"瓶颈已转移"，**不得改阈值**。
