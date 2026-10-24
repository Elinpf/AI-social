# D2.7 C 臂收批验收：**合法可用**，且与 D2.5a 的 C 臂交叉印证一致

> 日期：2026-10-24 15:27。目录 `v2/evidence/run_d27_C_n16r60_seed42`（主树 `branch=master`）。

## 1. 收批证据（这次有 rc）

| 项 | 值 |
|---|---|
| `run_batch.rc` | **0** |
| `run_batch.end` | `finished_at=2026-10-24T14:59:26+08:00 / rc=0 / arm=C` |
| `code_sha` | `f2bf606`（主树 HEAD，仅文档，`code/` 未动） |
| 规模 | `rounds=60 / n=16 / seed=42` |
| 真 LLM | `provider=openai_compat` |
| 成本 | `llm_calls=2878`、`duration_sec=3284`（54.7 min） |
| override | `overrides_declared=null`（无 override ⇒ 真 C 臂） |

## 2. 结构读数（全量口径，§3.119）

`MSG=510`（有 from 455）、**线程 169**、`ge6=52（30.77%）`、**`paren_rate=0.00%`**、`slot_dist={1:57, 2:199}`。

## 3. 交叉印证（强）

与 **D2.5a 的 C 臂**（`run_d25a_C_…`，另一棵树 `e2e7131`）**逐项相同**：
`510 MSG / 169 线程 / ge6 30.77% / paren 0.00% / slot_dist {1:57, 2:199} / calls 2878`。

⇒ 两次**独立起跑**、不同树、不同时间，得到**完全相同**的结构与成本 ⇒
①本项目的确定性复现可靠；②`run_batch` 侧无隐性漂移；③D2.7 的 B 臂有了可信的 C 对照。

## 4. 并发闸解除

C 已收批 ⇒ `preflight` 的 `concurrency:*` 不再阻挡，执行方可以跑第 ③ 项 mock（`n=6×12`，约 1 分钟）。

## 5. 放行

**B 臂「可跑」**，条件只有一条：mock ③ 的 `paren_rate > 0`（证明模型确实照新指令写旁白）。
mock 通过即起，不必再等我确认——起跑汇报首行引本件 + `v2/refs/D27-amendment1-merge-duplicate-prereg.md` 作为判据依据。
