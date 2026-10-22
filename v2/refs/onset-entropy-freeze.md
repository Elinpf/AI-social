# 句首熵「冻结」说明（D12-B 机制闸的判定用唯一实现）

> 依据 runbook §3.97：判定阈值的指标必须冻结唯一实现（函数 + `sha256`）。
> 本文件把 **D12-B 的机制闸（句首 4 字经验熵）** 与具体性代理（`v2/refs/detail-proxy-freeze.md`）同等对待。

## 1. 判定用实现

- 文件：`tools/d9/onset_entropy.py`（本次新增并冻结）
- **`impl_sha256 = 0e685f1f13c97e1897b3df0c9776cf6ec3743bf0adf01dc66004ff7d3806fab8`**

**判定语义（写死）**：
1. 单位 = **per-agent**；agent 取 `MSG_*` 的 `from`/`author`；
2. 句首 = `body` 原文**前 4 个字符**（不足 4 字取全部；空 body 跳过）；
3. 熵 = 该 agent 句首 4 字的**经验熵（自然对数）** `H = -Σ p ln p`；
4. 全体值 `H_mean` = **有效 agent（台词≥1）熵的算术平均**；
5. 渠道合并（DM/GROUP/PUBLIC）；**不**规范化文本、**不**切词、**不**用 LLM。

## 2. 判据（来自 D12 原预登记，B 臂对称闸）

- **机制生效**：`H_mean(ON) / H_mean(OFF) - 1 ≥ 10%`；
- 未达 ⇒ 判 **「机制未生效」**（模型没按自己的脾气起句），**不得判「无效」**。
- 工具内置该判定：`python3 tools/d9/onset_entropy.py --compare <OFF> <ON>`（PASS exit 0 / FAIL exit 1）。

## 3. 参考读数（基线，非本轮结论）

`run_d12a_q_a_off_seed7_n16r24`（OFF 臂，24 轮）：`agents=16`、`msgs=191`、**`H_mean = 2.362216`**、`impl_sha256=0e685f1f…`。

## 4. 用法（下一轮起强制）

```bash
python3 tools/d9/onset_entropy.py --run <arm>/run.jsonl --json     # 单臂读数
python3 tools/d9/onset_entropy.py --compare <OFF> <ON>             # 判定（≥10% 才算生效）
```
- 预登记/结果文档必须写 `impl_sha256=0e685f1f…`；
- 不得另写一版参与判定；若出现第二实现，判定值取**更保守**者（runbook §3.97）。
