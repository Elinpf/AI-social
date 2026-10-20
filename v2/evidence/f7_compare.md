# F-7 越界提及 · 两臂同口径对照（脚本自动生成）

- 脚本：`tools/f7/f7_offscreen_mention.py`（schema `f7-offscreen/1.0`）
- 判据卡：`v2/refs/F7-offscreen-criteria.md`
- 名字表：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code/config/personas.json` sha256 `08d11eb36d644e55db0c9b7e00adccb81613d50476927e3acf07117f7f970f7d`（n=20，name_table_sha256 `cdf28d499146220921482d175d43298269d2c2b08c25c0585b6f5e51af4b64d1`）
- 臂 A：`run_d2_before_n16_seed42`（v2/evidence/run_d2_before_n16_seed42/run.jsonl）log sha256 `c1f86bf61f62b3a0ce8e17e0c2312791cf0262381cd2120c2a63c9b6258963cf`
- 臂 B：`run_d2_after_n16_seed42`（v2/evidence/run_d2_after_n16_seed42/run.jsonl）log sha256 `643f13a528c288d3e9677cb8ac100139224afbd0b46c0f7da0c3a5ed85b13141`

## 1. 主判据（P1）读数

P1 = 旁白剔除 · 主干名+裸ID · 全渠道 · 收件人不算越界 · 消息时刻位置（point-in-time）

| 臂 | 可判定消息（分母） | 越界命中消息（分子） | per-message 率 | 95% CI | per-mention 率 | 不可判定提及 |
|---|---|---|---|---|---|---|
| run_d2_before_n16_seed42 | 2 | 2 | 100.00% | [100.00%, 100.00%] | 100.00% | 0 |
| run_d2_after_n16_seed42 | 108 | 81 | 75.00% | [66.67%, 83.33%] | 57.04% | 4 |

**可比性裁决**：**不可比** —— 分母差 98.1%（run_d2_before_n16_seed42=2 vs run_d2_after_n16_seed42=108），超过 30% 阈值

## 2. 称呼层（P2）读数——更接近「对不在场者说话」的一层

P2 = P1 的提及集合里只保留称呼型（token 后接呼语标点，或前接 喂/哎/嘿/嗨/哟/唉）。**启发式代理，非人工标注；与 P1 不得相加或互相代入。**

| 臂 | 可判定消息（分母） | 越界称呼命中（分子） | per-message 率 | 95% CI | per-mention 率 | 旁白计入时 分子/分母 |
|---|---|---|---|---|---|---|
| run_d2_before_n16_seed42 | 1 | 1 | 100.00% | [100.00%, 100.00%] | 100.00% | 1/1 |
| run_d2_after_n16_seed42 | 79 | 56 | 70.89% | [60.76%, 81.01%] | 64.37% | 57/80 |

**可比性裁决（P2）**：**不可比** —— 分母差 98.7%（run_d2_before_n16_seed42=1 vs run_d2_after_n16_seed42=79），超过 30% 阈值

## 3. 消息量与提及面（口径为何不成立的结构原因）

| 臂 | 总消息 | DM | PUBLIC | GROUP | 含他人指称的消息 | 其中 DM | 其中 PUBLIC | 其中 GROUP |
|---|---|---|---|---|---|---|---|---|
| run_d2_before_n16_seed42 | 187 | 132 | 48 | 7 | 58 | 58 | 0 | 0 |
| run_d2_after_n16_seed42 | 686 | 497 | 63 | 126 | 398 | 305 | 0 | 93 |

## 4. 旧口径（legacy_compat）与 P1 的差

| 臂 | 旧口径读数（分子/分母） | 旧口径不可判定位置查询数 | P1 读数 | P1 不可判定提及 |
|---|---|---|---|---|
| run_d2_before_n16_seed42 | 2/187 = 1.07% | 0 | 2/2 = 100.00% | 0 |
| run_d2_after_n16_seed42 | 107/686 = 15.60% | 487 | 81/108 = 75.00% | 4 |

> 说明：旧口径不可判定位置查询数远大于 0 时，其分子只在极小可查子集上取值、分母却是全部消息，两个单位混用 ⇒ 该读数**不可解释**。P1 用消息时刻位置（point-in-time）把不可判定压到最小，并把分母换成「真的有可判定提及的消息」。

## 5. 全变体矩阵（48 个变体，两臂并列）

| 变体 | run_d2_before_n16_seed42 分子/分母 | run_d2_before_n16_seed42 率 | run_d2_after_n16_seed42 分子/分母 | run_d2_after_n16_seed42 率 | 分母差 | 裁决 |
|---|---|---|---|---|---|---|
| `nar=exclude|id=names+id|ch=all|addr=exclude|pres=pit` P1 | 2/2 | 100.00% | 81/108 | 75.00% | 98.1% | 不可比 |
| `nar=exclude|id=names+id|ch=all|addr=exclude|pres=round_last`  | 2/2 | 100.00% | 31/52 | 59.62% | 96.2% | 不可比 |
| `nar=exclude|id=names+id|ch=all|addr=include|pres=pit`  | 45/56 | 80.36% | 264/395 | 66.84% | 85.8% | 不可比 |
| `nar=exclude|id=names+id|ch=all|addr=include|pres=round_last`  | 40/51 | 78.43% | 102/177 | 57.63% | 71.2% | 不可比 |
| `nar=exclude|id=names+id|ch=dm_group|addr=exclude|pres=pit`  | 2/2 | 100.00% | 81/108 | 75.00% | 98.1% | 不可比 |
| `nar=exclude|id=names+id|ch=dm_group|addr=exclude|pres=round_last`  | 2/2 | 100.00% | 31/52 | 59.62% | 96.2% | 不可比 |
| `nar=exclude|id=names+id|ch=dm_group|addr=include|pres=pit`  | 45/56 | 80.36% | 264/395 | 66.84% | 85.8% | 不可比 |
| `nar=exclude|id=names+id|ch=dm_group|addr=include|pres=round_last`  | 40/51 | 78.43% | 102/177 | 57.63% | 71.2% | 不可比 |
| `nar=exclude|id=names+id|ch=public_group|addr=exclude|pres=pit`  | 0/0 | — | 67/93 | 72.04% | — | 不可比 |
| `nar=exclude|id=names+id|ch=public_group|addr=exclude|pres=round_last`  | 0/0 | — | 26/45 | 57.78% | — | 不可比 |
| `nar=exclude|id=names+id|ch=public_group|addr=include|pres=pit`  | 0/0 | — | 67/93 | 72.04% | — | 不可比 |
| `nar=exclude|id=names+id|ch=public_group|addr=include|pres=round_last`  | 0/0 | — | 26/45 | 57.78% | — | 不可比 |
| `nar=exclude|id=names|ch=all|addr=exclude|pres=pit`  | 2/2 | 100.00% | 81/108 | 75.00% | 98.1% | 不可比 |
| `nar=exclude|id=names|ch=all|addr=exclude|pres=round_last`  | 2/2 | 100.00% | 31/52 | 59.62% | 96.2% | 不可比 |
| `nar=exclude|id=names|ch=all|addr=include|pres=pit`  | 2/2 | 100.00% | 264/395 | 66.84% | 99.5% | 不可比 |
| `nar=exclude|id=names|ch=all|addr=include|pres=round_last`  | 2/2 | 100.00% | 102/177 | 57.63% | 98.9% | 不可比 |
| `nar=exclude|id=names|ch=dm_group|addr=exclude|pres=pit`  | 2/2 | 100.00% | 81/108 | 75.00% | 98.1% | 不可比 |
| `nar=exclude|id=names|ch=dm_group|addr=exclude|pres=round_last`  | 2/2 | 100.00% | 31/52 | 59.62% | 96.2% | 不可比 |
| `nar=exclude|id=names|ch=dm_group|addr=include|pres=pit`  | 2/2 | 100.00% | 264/395 | 66.84% | 99.5% | 不可比 |
| `nar=exclude|id=names|ch=dm_group|addr=include|pres=round_last`  | 2/2 | 100.00% | 102/177 | 57.63% | 98.9% | 不可比 |
| `nar=exclude|id=names|ch=public_group|addr=exclude|pres=pit`  | 0/0 | — | 67/93 | 72.04% | — | 不可比 |
| `nar=exclude|id=names|ch=public_group|addr=exclude|pres=round_last`  | 0/0 | — | 26/45 | 57.78% | — | 不可比 |
| `nar=exclude|id=names|ch=public_group|addr=include|pres=pit`  | 0/0 | — | 67/93 | 72.04% | — | 不可比 |
| `nar=exclude|id=names|ch=public_group|addr=include|pres=round_last`  | 0/0 | — | 26/45 | 57.78% | — | 不可比 |
| `nar=include|id=names+id|ch=all|addr=exclude|pres=pit`  | 2/2 | 100.00% | 85/114 | 74.56% | 98.2% | 不可比 |
| `nar=include|id=names+id|ch=all|addr=exclude|pres=round_last`  | 2/2 | 100.00% | 33/55 | 60.00% | 96.4% | 不可比 |
| `nar=include|id=names+id|ch=all|addr=include|pres=pit`  | 45/56 | 80.36% | 274/409 | 66.99% | 86.3% | 不可比 |
| `nar=include|id=names+id|ch=all|addr=include|pres=round_last`  | 40/51 | 78.43% | 107/185 | 57.84% | 72.4% | 不可比 |
| `nar=include|id=names+id|ch=dm_group|addr=exclude|pres=pit`  | 2/2 | 100.00% | 85/114 | 74.56% | 98.2% | 不可比 |
| `nar=include|id=names+id|ch=dm_group|addr=exclude|pres=round_last`  | 2/2 | 100.00% | 33/55 | 60.00% | 96.4% | 不可比 |
| `nar=include|id=names+id|ch=dm_group|addr=include|pres=pit`  | 45/56 | 80.36% | 274/409 | 66.99% | 86.3% | 不可比 |
| `nar=include|id=names+id|ch=dm_group|addr=include|pres=round_last`  | 40/51 | 78.43% | 107/185 | 57.84% | 72.4% | 不可比 |
| `nar=include|id=names+id|ch=public_group|addr=exclude|pres=pit`  | 0/0 | — | 71/99 | 71.72% | — | 不可比 |
| `nar=include|id=names+id|ch=public_group|addr=exclude|pres=round_last`  | 0/0 | — | 28/48 | 58.33% | — | 不可比 |
| `nar=include|id=names+id|ch=public_group|addr=include|pres=pit`  | 0/0 | — | 71/99 | 71.72% | — | 不可比 |
| `nar=include|id=names+id|ch=public_group|addr=include|pres=round_last`  | 0/0 | — | 28/48 | 58.33% | — | 不可比 |
| `nar=include|id=names|ch=all|addr=exclude|pres=pit`  | 2/2 | 100.00% | 85/114 | 74.56% | 98.2% | 不可比 |
| `nar=include|id=names|ch=all|addr=exclude|pres=round_last`  | 2/2 | 100.00% | 33/55 | 60.00% | 96.4% | 不可比 |
| `nar=include|id=names|ch=all|addr=include|pres=pit`  | 2/2 | 100.00% | 274/409 | 66.99% | 99.5% | 不可比 |
| `nar=include|id=names|ch=all|addr=include|pres=round_last`  | 2/2 | 100.00% | 107/185 | 57.84% | 98.9% | 不可比 |
| `nar=include|id=names|ch=dm_group|addr=exclude|pres=pit`  | 2/2 | 100.00% | 85/114 | 74.56% | 98.2% | 不可比 |
| `nar=include|id=names|ch=dm_group|addr=exclude|pres=round_last`  | 2/2 | 100.00% | 33/55 | 60.00% | 96.4% | 不可比 |
| `nar=include|id=names|ch=dm_group|addr=include|pres=pit`  | 2/2 | 100.00% | 274/409 | 66.99% | 99.5% | 不可比 |
| `nar=include|id=names|ch=dm_group|addr=include|pres=round_last`  | 2/2 | 100.00% | 107/185 | 57.84% | 98.9% | 不可比 |
| `nar=include|id=names|ch=public_group|addr=exclude|pres=pit`  | 0/0 | — | 71/99 | 71.72% | — | 不可比 |
| `nar=include|id=names|ch=public_group|addr=exclude|pres=round_last`  | 0/0 | — | 28/48 | 58.33% | — | 不可比 |
| `nar=include|id=names|ch=public_group|addr=include|pres=pit`  | 0/0 | — | 71/99 | 71.72% | — | 不可比 |
| `nar=include|id=names|ch=public_group|addr=include|pres=round_last`  | 0/0 | — | 28/48 | 58.33% | — | 不可比 |

