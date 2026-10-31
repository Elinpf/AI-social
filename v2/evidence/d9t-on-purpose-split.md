# D9t ON 臂 · `LLM_CALL` 按 `purpose` 拆分（双口径对账表）

数据源：`v2/evidence/d9t-on_n16r24_s42/run.jsonl`（sha256 `af4c44d11dd22eb84ae9e6fd1f5d32417d128d34ff07ec54d2bb08bd61256dec`，33877 行，17189995 B）
口径：`real = tokens_in > 0`（真调用，`cached=False`）；`cached = tokens_in == 0`（缓存回放，`cached=True`）

## 主表（行和 = 2252）

| purpose | calls | real(`tokens_in>0`) | cached | tokens_in | tokens_out |
|---|---:|---:|---:|---:|---:|
| importance | 1523 | 136 | 1387 | 2312 | 32473 |
| judge | 425 | 425 | 0 | 51730 | 97993 |
| dialogue | 191 | 191 | 0 | 112369 | 11793 |
| reflect | 90 | 90 | 0 | 45031 | 6510 |
| plan | 16 | 16 | 0 | 1447 | 955 |
| negotiation | 7 | 7 | 0 | 839 | 267 |
| **合计** | **2252** | **865** | **1387** | **213728** | **149991** |

## 为什么会出现两个口径（不是矛盾，是分母不同）

| 口径 | MSG | dialogue 调用 | 真调用 | 缓存回放 | 说明 |
|---|---:|---:|---:|---:|---|
| **仅 `purpose=dialogue`** | 191 | 191 | **191** | **0** | 与判定件/复核件 `191/191/191/0` **完全一致** |
| **全 purpose** | 191 | 191 | **865** | **1387** | 差额全部来自 `importance` 的同批去重 |

- `MSG` 与 `dialogue` 调用是 **1:1**（191 条对话调用产出 191 条消息），且 dialogue **零回放**。
- 全 purpose 口径下"缓存回放 0/0"**不成立**：1387 次回放真实存在，但**不在 dialogue**，全在 `importance`。

## `importance` 那 1387 次回放的来源（已核，不是旧缓存复用）

- 本臂 `side-root=/tmp/d9t_on_side_191408` 为**全新路径**（起跑前不存在）⇒ 排除"沿用历史缓存"。
- 136 个不同 `prompt_hash`，**每个首次真执行一次**（`sets(cached) ⊆ sets(real)`，两集合均为 136）⇒ 1387 = 1523 − 136，属**同批内同 prompt 去重**。
- 单 key 最大回放 **15** 次（16 agents 同一 `importance` 提示 ⇒ 1 次真调 + 15 次回放）。

## 建议在判定件里怎么写（双口径同屏，不自判对错）

> 四数按**两个分母**并列：`dialogue` 口径 **191/191/191/0**；全 purpose 口径 **191/191/865/1387**（总账 2252 次调用、`tokens_in 213728`、`tokens_out 149991`）。
> "缓存回放 0"仅对 `dialogue` 成立；全 purpose 下回放 1387 次，全部来自 `importance` 的同批同 prompt 去重（全新 side-root，非历史缓存）。

## 边界

- 仅限 `cef1c58 / n=16 / rounds=24 / seed=42 / openai_compat(DeepSeek-Flash)`。
- 本件只做计数拆分，不含任何效果结论。
