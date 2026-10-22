# 中性树（`3ec85a0`）24 轮窗口的期望值 —— 供 `arm_state_check --tree-expectation` 使用

> 用途：**避开天花板**。禁旁白树（`feat/d12-detail`）的基线具体性已 95–98%，+3pp 结构上不可达；
> 中性树基线 87.43% / 旁白 78.01%，是下一轮 B 臂（偏好驱动选词）的**正确战场**。

## 1. 来源与口径

- 日志：`v2/evidence/run_d2_after_n16_seed42/run.jsonl`（**A0 臂**，树 `3ec85a0`，真 LLM，84 轮）
- 窗口：**`round ≤ 23`**（与 `n=16 × 24 轮` 同窗口，取前缀子集，非另跑）
- 具体性：用**冻结实现** `tools/d9/detail_proxy.py`（`impl_sha256=335cb48c…`，`words_sha256=1c2a342f…`）

## 2. 期望值（写死，直接喂工具）

```json
{"paren_rate": 0.78, "len_p50": 47}
```
```json
{"msgs": 191, "threads": 66, "ge3": 28}
```

| 指标 | 期望值 | 实测 |
|---|---|---|
| 括号旁白率 | **≈0.78**（**不是 0**） | 149/191 = **78.01%** |
| 具体性（冻结代理） | **≈0.87** | 167/191 = **87.43%** |
| `len_p50` | **≈47** | 47（`len_mean` 54.2） |
| MSG / 线程 / ≥3 轮 | 191 / 66 / 28 | 一致 |

## 3. 用途与硬闸

- 起跑 60 秒内跑：
  ```bash
  python3 tools/d9/arm_state_check.py --run <arm>/run.jsonl \
    --tree-expectation '{"paren_rate": 0.78, "len_p50": 47}' \
    --expect-struct '{"msgs": 191, "threads": 66, "ge3": 28}' \
    --expect-provider openai_compat
  ```
- **对照臂（OFF）旁白率若 ≈0 而非 ≈0.78 ⇒ 说明跑错树（又跑到禁旁白树上）⇒ 立即停跑**；
- 这条正是 D12-A 那次事故的硬闸：**期望值必须按树现算，不能一律写 0**。
