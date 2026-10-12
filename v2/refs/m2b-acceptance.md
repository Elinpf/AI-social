# M2b 验收口径（obs-stats-dev 提供）

> 对象：**judge + importance 判别式化**（T222）。验收分**成本 / 质量 / 校准 / 可观测**四组，**每组给口径+算式+判据**。
> 工具：`obs/calibration.py`（校准/一致率/多类）、`obs/admission.py`（合法率/token比/延迟比/flag 率）。**口径唯一，不复制。**

---

## 0. ⚠️ 先钉一个歧义：`成本 ≤0.2×` 的**分母口径**
同批请求（T212 实测）：

| 口径 | B/A | 说明 |
|---|---|---|
| `cost_ratio_out` = Σ`tokens_out`B / Σ`tokens_out`A | **0.061** | **生成成本**（判别式化直接砍这里） |
| `cost_ratio_total` = Σ(in+out)B / Σ(in+out)A | **0.479** | 含输入（两侧 prompt 相近，降不下来） |
| `latency_p50` B/A | **0.083** | 12×↓ |

→ **「≤0.2×」必须指名分母**。**建议 pin 为 `cost_ratio_out`（或 provider 计价 `cost_units`）**；`cost_ratio_total` 作**参考列**（它天然降不到 0.2，因为输入没变）。
**否则「0.479 vs 0.2」会被当成不达标** —— 一个纯粹口径造成的误判。**请 leader 拍板口径。**

## 1. 成本（判据）
- **`cost_ratio_out(judge) ≤ 0.2×`**（生成 token）；`cost_ratio_out(importance) ≤ 0.3×`（重要性输出更短，先给）。
- 参考列：`cost_ratio_total`、`latency_p50`、`reasoning_tokens`（B 应=0）。
- 算式/复算：`obs.admission.admission_report(records)`；基线取同批 A 侧 或 `run_t136_real_llm_canon_n20.jsonl`（judge 479,927 tok/84 回合）。

## 2. 质量（判据：**一致率不退**）
- **`agreement_rate(B_labels, A_labels) ≥ 0.95`**（T212=**0.9902** ✓），且**逐维**无 drop > **0.03**。
- **`legal_rate(B) ≥ 0.99`**（T212=**1.000** ✓）。
- `agreement_N` = A、B 都有 label 的样本（**独立报 N**）。
- 特例：**`mentor_relation` 维用规则兜底**（T212 发现 B 更宽松）—— 该维不纳入一致率门，单列。

## 3. 校准（判据：**证据充分才允许置信度回退**）
- **硬门**（`obs.calibration.calibration_report`）：`evidence_sufficient = (非空档≥2 且 正负例都在)` **且**（`ECE ≤ 0.05` 或 分层单调且 top−bottom≥gap）→ **才允许「置信度回退」**；否则**回退用规则（候选分值差阈值）**。
- T212：`n=81, n_pos=81, n_neg=0, tiers=1` → **`evidence_insufficient` → 不开置信度回退（分支 B）**。
- **红线**：**单档/零负例的 `ECE≈0` 不算校准好**（`3645e08` 已硬化）。

## 4. `escape_rate` / `fallback_rate`（可观测，**必须**）
| 指标 | 定义 | 判据 |
|---|---|---|
| **`escape_rate`** | `|{judge 请求：判别式无法在合法候选内决定 / 主动逃生到生成式}| / |judge 请求|` | **`≤ 0.05`**（提案）；**偏高 = 回去补枚举**（**不是调阈值**） |
| **`fallback_rate`** | `|{judge 请求：用了回退判据}| / |judge 请求|`；分支 B 下回退判据 = **候选分值差阈值**（非置信度） | 报告 + 监控（无硬门，偏高需定位） |
- **必须落事件/旗标**（如 `JUDGE_ESCAPED` / `JUDGE_FALLBACK{rule:"score_gap"}`），**可静默=违规**。
- 观测口径：`obs.admission.flag_rate(records, "escaped")` / `flag_rate(records, "fallback_used")`。

## 5. 默认开关 & 回归（判据）
- **默认关**；**关闭时行为与现状逐项一致**：`obs.metrics` / `obs.census` 两次调用**字节相等**，且与关闭态基线分布一致（G6）。
- 开关本身**可消融**、**可观测**。

## 6. 未验证 / 待对齐
- `escape`/`fallback` 的**事件名与语义** 待 T222 落地后对齐（本表先给口径）。
- `成本 ≤0.2×` 的**分母口径**待 leader 拍板（见 §0）。
- importance 的 cost 目标（0.3×）为提案，需实测后校准。

---
_产出：obs-stats-dev · 口径工具 commit `3645e08`（calibration 证据充分性）/ `d1b4d3d`（admission）。_
