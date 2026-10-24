# D2.8 中期（2）：**B 臂跨 seed 极其稳定**；C:43 由 Leader 起跑补位

> 日期：2026-10-24 22:58。**仍是中期，不作最终判定。**

## 1. B 臂两 seed 对比（`run_d28_B_…seed42` @`0474ee5` vs `…seed43` @`c3ec266`）

| 指标 | B:42 | B:43 | 差 |
|---|---|---|---|
| `paren_rate` | **29.22%** | **29.22%** | **0.00pp** |
| `len_p50_excl` | **53** | **53** | **0** |
| `P1_count_mean` | 4.1078 | 4.1373 | +0.7% |
| `n_msgs` / `n_threads` | 510 / 169 | 510 / 169 | 0 |
| `llm_calls` | 2878 | 2878 | 0 |
| 时长 | 40.2 min | 43.7 min | — |

**`paren_rate` 完全相同是合理的**：`para_on` 由 `sha256(thread_id|turn)` 决定、与 seed 无关；
而 thread 集合在两 seed 下相同（510/169）⇒ 触发集合一致 ⇒ 比例必然一致。
`len_p50_excl` 与 `P1_count_mean` 的差异（0 / 0.7%）说明**文本层的 seed 波动远小于 D2.7 观察到的批次噪音**。

⇒ **D2.8 的效应（相对 C:42 的 `len 41 → 53`，+29.3%）远大于 B 臂自身的跨 seed 波动。**

## 2. C:43 的处理（必须说清）

`C:43` 原先那批（`ad6197e`，分支树，含 `para_on`）已判**作废**（`d28_C43_INVALID_wrong_tree.md`），
执行方已把目录改名为 `run_d28_C_n16r60_seed43_INVALID_branch_has_D28`（标记正确）。

**截至 22:58，master 树的 C:43 仍未起跑**（距我 21:28 的指令已 1.5h）。
为不让 seed43 的配对悬空，**Leader 直接在主树起跑**：

```
bash tools/d2/run_batch.sh --out-dir v2/evidence/run_d28_C_s43_n16r60_seed43 \
  --seed 43 --agents 16 --rounds 60 --side-root /tmp/d28_C_s43
```
起跑自检（22:59:07）：`PASS preflight sha=834dd2d0(master) concurrency=0 frozen_tree=clean`。
**收批第一件事核 `paren_rate` 必须 = 0.00%**（§3.120 的判别量）；不为 0 则本批再作废。

## 3. 为什么要跑它（不能拿 C:42 顶替）

C 臂的**跨 seed 波动未知**（`C:42` 与作废的 C:43 不可比）。若要判"两 seed 同向"，必须有一对**同 seed** 的 C。
拿 C:42 当 C:43 用，等于把"seed 差异"混进"臂间差异"，这正是 §3.99 那类事故。

## 4. 当前进度

| 臂 | 状态 |
|---|---|
| C:42（`run_d27_C`，master `f2bf606`，`paren 0.00%`） | ✅ 有效 |
| B:42（`0474ee5`，`paren 29.22%`，`len 53`） | ✅ 有效 |
| C:43（master `834dd2d`） | ⏳ **Leader 已起跑**，预计 ~47min |
| B:43（`c3ec266`，`paren 29.22%`，`len 53`） | ✅ 有效 |
