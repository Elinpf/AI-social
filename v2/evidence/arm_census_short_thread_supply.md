# arm_census_short_thread_supply · 既有各臂 2–3 轮线程供给普查（只读）

> 作者：`codebase-scout`｜卡号：**`T-ARM-CENSUS-SHORT`**｜时刻 `2026-10-29 05:2x`
> 性质：**只读普查**。未跑批、未改 `code/`、未做 git 写操作。**仅落盘，提交权在 Leader。**
> 目的：`batch4` 按现规格不成立（同配置异 seed 线程集合与轮数 169/169 全同，见 `v2/evidence/batch4_seed_invariance_voids_design.md` `b1ccd08`）⇒ 先查**是否已有现成臂可直接借用**，避免新跑。

---

## §0 汇总表（先看这里）

| 配置分组 | 臂数 | 2–3 轮层（绝对条数） | 尾截断 | 干净（非截断） | 净供给（扣除 36 已用） | 能否供 ≥12 干净短线程 |
|---|---|---|---|---|---|---|
| **r84 / n=16 / seed42**（有 meta 的 6 条：`d1_f6off`、`d1_f6on`、`d2_after`、`d9_a1`、`f6off_cycle06`、`r6_treat`；另有 `worldline_c1_a1`/`worldline_c1_ctrl` 2 条**无 meta**，线程同为 206 / 2–3 层 20） | 6（+2 无 meta） | **20**（`r6_treat` 为 22） | **0** | **20**（`r6_treat` 22） | **16**（`r6_treat` **18**） | ✅ **能，且多条臂满足** |
| r84 / n=16 / seed42（r6_treat，变体） | 1 | 22 | 0 | 22 | **18** | ✅ |
| r60 / n=16 / seed42 | 多 | 18（f3_on 为 23） | 0 | 18（23） | 14（**f3_on 19**） | ✅（f3_on 满足；其余 14 也≥12） |
| **r42 / n=16 / seed42（A5 臂＝抽样来源）** | 1 | **8** | **4** | **4** | **0** | ❌ 这正是"短线程层已耗尽"的那批 |
| n=8 / r16 | 2 | 5 | 2 | 3 | 3 | ❌ |
| n=4 / r60 | 3 | 3 | 0 | 3 | 3 | ❌ |
| n=16 / r12 | 1 | 9 | 0 | 9 | 3 | ❌ |
| **n=32** | **0** | — | — | — | — | **❌ 不存在任何 n32 臂（全库最大 n=16）** |

**一句话结论**：**不必新跑也能拿到干净短线程——`r84` 系多条臂各能提供 16–18 条（扣除已用 36 后），`run_f3_on_n16r60_seed42` 可提供 19 条。** 但**没有任何 n32 臂**，所以"n32 路线"必须新跑。

⚠️ 另两条须在借用时注意的臂级事实：
1. `run_d2_before_n16_seed42`（before 臂，`code_sha=dc93c9d9`）**线程数 = 0** —— 该臂是 **D2 之前**的树，日志里根本没有 `thread_id` 字段 ⇒ **它不能供任何线程样本**（不是漏算，是字段不存在；谓词域：`MSG_*/payload.thread_id` 命中 0 条）。
2. `run_a5_real_n16r42_seed42`（抽样来源）与 `run_d28_C_n16r60_seed43_INVALID_duplicate_stopped` **无 `meta.json`** ⇒ 按卡面 ① 判不可用（A5 仅作参照系使用）。

---

## §1 口径（含两处必须先说清的口径陷阱）

### 1.1 ★ 卡面谓词的**极性**与读数不符（重要，需你确认后改 R1 边界 14）

卡面写的"非尾截断"谓词是 `min(round) > maxround − (max_turns−1)`。**按字面执行，51 个臂全部得 0**（不是"某臂为 0"，是**每条臂都 0**）⇒ 该谓词按字面**筛不出任何线程**。

按**语义**（线程从 `min(round)` 起、连续 T 轮，若末轮 `min(round)+T-1 ≥ maxround` 则被 run 结束截断）应为：

```
非尾截断 ⇔ min(round) < maxround − (T − 1)
```

用这个方向立刻与**既有事实对上**：A5 臂 2–3 轮 **8 条 → 干净 4 / 尾截断 4**，与 Leader 先前所说"短线程层仍是那 8 条（其中 4 条截断件）"**逐字吻合** ⇒ 反证 `<` 是正确极性，卡面 `>` 为笔误。

本报告的所有"干净"列**均用 `<` 计算**，并在每行同时给出"尾截断"条数，便于你复核。

### 1.2 ★ `thread_id` 也出现在 `INTENT_REJECTED.requested` 里（不过滤会虚增线程数）

`INTENT_REJECTED{intent_class:"INTENT.SOCIAL", reason:"not_group_member"}` 的 `requested` 子对象里**带着 draft 的 `thread_id`**。若不按 `"type":"MSG_*"` 过滤，线程数会**虚增**：
- `run_d2_after_n16_seed42`：228 → **正确 206**（虚增 22，+10.7%）
- `run_r6_treat_n16_seed42`：236 → **正确 210**（虚增 26，+12.4%）

⇒ 本报告统一口径：**线程 = `type ∈ {MSG_DM, MSG_PUBLIC, MSG_GROUP}` 且带 `thread_id` 的消息按 `thread_id` 分组**；只在 `INTENT_REJECTED` 里出现的 id **不计线程**（每臂 22–26 个）。

### 1.3 `round` 取法
按卡面：`msg_id` **次末段**。实测 `msg_id` 形态：`D-{round}-{turn_index}`、`P-{round}-{turn_index}`、`G-{gid}-{round}-{turn_index}` ⇒ `split('-')[-2]` 恒为 round，`[-1]` 为 turn_index。与卡面一致。
（`thread_id` 末段不取：`TH-…-PUB-{r}-{t}` 形态下会退化——卡面已注明，实测确认。）

---

## §2 「可用臂」三条件逐条判定（对最强候选）

| 条件 | `run_r6_treat_n16_seed42` | `run_f3_on_n16r60_seed42` | `run_d1_f6off_seed42_n16r84` | `run_d2_after_n16_seed42` |
|---|---|---|---|---|
| ① 非 INVALID/ABORTED 且有 `meta.json` | ✅ | ✅ | ✅ | ✅ |
| ② `--require-provider openai_compat` 实测 | ✅ **rc=0**，`provider_guard.ok=true`，`by_provider={openai_compat:3405}` | 未跑（见下） | ✅ **rc=0**，`{openai_compat:3403}` | ✅ **rc=0**，`{openai_compat:3403}` |
| ③ 与 A5 线程集合**交集为 0** | ❌ **交集 15** | ❌ 交集 13 | ❌ 交集 15 | ❌ 交集 15 |
| **净供给（干净 − 已用）** | **18** | **19** | **16** | **16** |
| 判定（按卡面严格版 ③） | **不可用** | **不可用** | **不可用** | **不可用** |
| 判定（若 ③ 改为"净供给 ≥ 12"） | ✅ 可用 | ✅ 可用 | ✅ 可用 | ✅ 可用 |

⭐ **这是本卡最需要你裁决的一点**：按卡面 ③ 的字面（交集必须为 0），**所有 r84/r60 臂全部判"不可用"**——因为它们与 A5 共享 15 个线程 id（同族池、跨配置重叠）。但"交集≠0"并不妨碍借用：那 15 个里落在 2–3 轮层的只有 **4 个**，扣除后仍余 16–19 条。⇒ 建议把 ③ 从"交集=0"改为**"扣除 36 个已用 id 后，干净短线程净供给 ≥ 12"**（这才是"能不能借"的实义）。我按两种口径都判了，未擅自改判据。

**② 的补充**：`run_f3_on_n16r60_seed42` 我**没有**跑 `obs llm-cost`（该臂 115k 事件、跑一次约数十秒，但为遵守"不跑重活/串行"我可留给你或另开一次）；它的 `meta.json` 记录 `provider=openai_compat / degraded_calls=0 / fallback_detected=false`，但**meta 是事后派生件，不作准入**——按纪律标 **待验**。

---

## §3 借臂的最优候选（只给数，不建议）

| 优先序（按净供给） | 臂 | 配置 | 干净短线程 | 净供给 | 备注 |
|---|---|---|---|---|---|
| 1 | `run_f3_on_n16r60_seed42` | n16 / r60 / seed42 | 23 | **19** | ②待验 |
| 2 | `run_r6_treat_n16_seed42` | n16 / r84 / seed42 | 22 | **18** | ②已验 rc=0；`code_sha=7b6846dc` |
| 3 | r84 系 6 条（d1_f6off / d1_f6on / d2_after / d9_a1 / f6off_cycle06 / worldline_c1_a1 / worldline_c1_ctrl） | n16 / r84 / seed42 | 20 | **16** | d1_f6off、d2_after 已验 rc=0 |
| — | A5（抽样来源） | n16 / r42 / seed42 | 4 | 0 | 短线程层已耗尽 |

⚠️ **r84 系各臂的 thread_id 集合高度重合**：实测 `d1_f6off` 与 `d2_after` 的线程集合**完全相同（228→206 条，a==b True）**，只是**内容不同**（`code_sha` `d7d1d93f` vs `884f4541`）。⇒ 从"多拿几批"角度它们**不是 6 个独立来源，只是 1 个池的 6 种措辞版本**。

---

## §4 全表（逐臂一行）

> 状态列：`meta`=有 meta.json；`no-meta`=无 meta.json（按卡面 ① 判不可用）；`INVALID`/`ABORTED`/`VOID`=目录名自带否决标记。
> "净供给" = 干净（非截断）2–3 轮线程 − 与 batch1/2/3 已用 36 个 id 的交集。

| 臂 | n | rounds | seed | code_sha8 | 线程 | 1轮 | 2–3轮 | 尾截断 | 干净(非截断) | 净供给(扣除36已用) | 状态 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| run_a1_wording_n4r60_seed42 | 4 | 60 | 42 | a6373719 | 40 | 20 | 3 | 0 | 3 | 3 | meta |
| run_a1budget_real_n16r42_seed42 | ? | ? | ? | — | 154 | 70 | 20 | 9 | 11 | 8 | no-meta |
| run_a1wording_n16r42_seed42 | ? | ? | ? | — | 94 | 43 | 14 | 1 | 13 | 11 | no-meta |
| run_a5_real_n16r42_seed42 | ? | ? | ? | — | 140 | 55 | 8 | 4 | 4 | 0 | no-meta |
| run_baseline_n4r2_20261020T220207 | ? | ? | ? | — | 3 | 2 | 1 | 1 | 0 | 0 | no-meta |
| run_d12a_base_seed7_n16r24_INVALID_confounded | ? | ? | ? | — | 66 | 34 | 6 | 0 | 6 | 3 | INVALID |
| run_d12a_q_a_off_seed7_n16r24 | ? | ? | ? | — | 66 | 34 | 6 | 0 | 6 | 3 | no-meta |
| run_d12a_q_a_on_seed7_n16r24 | ? | ? | ? | — | 66 | 34 | 6 | 0 | 6 | 3 | no-meta |
| run_d12a_real_n16r24_seed42 | ? | ? | ? | — | 66 | 34 | 6 | 0 | 6 | 3 | no-meta |
| run_d12a_treat_seed7_n16r24_INVALID_incomplete | ? | ? | ? | — | 23 | 14 | 9 | 0 | 9 | 5 | INVALID |
| run_d12b_off_seed7_n16r24 | ? | ? | ? | — | 66 | 34 | 6 | 0 | 6 | 3 | no-meta |
| run_d12b_off_seed7_n16r24_INVALID_concurrent | ? | ? | ? | — | 0 | 0 | 0 | 0 | 0 | 0 | INVALID |
| run_d12b_on_seed7_n16r24 | ? | ? | ? | — | 66 | 34 | 6 | 0 | 6 | 3 | no-meta |
| run_d12c_off_n16r60_seed42 | ? | 60 | ? | — | 169 | 81 | 18 | 0 | 18 | 14 | meta |
| run_d12c_on_n16r60_seed42 | ? | 60 | 42 | — | 169 | 81 | 18 | 0 | 18 | 14 | meta |
| run_d12d_on_n16r60_seed42 | ? | 60 | 42 | 5ca515d | 169 | 81 | 18 | 0 | 18 | 14 | meta |
| run_d12g_diverse2_n16r60_seed42 | - | - | - | - | - | - | - | - | - | - | no run.jsonl |
| run_d1_f6off_seed42_n16r84 | 16 | 84 | 42 | d7d1d93f | 206 | 102 | 20 | 0 | 20 | 16 | meta |
| run_d1_f6on_seed42_n16r84 | 16 | 84 | 42 | e8a9fd5e | 206 | 102 | 20 | 0 | 20 | 16 | meta |
| run_d27_C_n16r60_seed42 | 16 | 60 | 42 | f2bf606b | 169 | 81 | 18 | 0 | 18 | 14 | meta |
| run_d28_C_n16r60_seed43_INVALID_allcached | 16 | 60 | 43 | a8e1c46b | 169 | 81 | 18 | 0 | 18 | 14 | INVALID |
| run_d28_C_n16r60_seed43_INVALID_duplicate_stopped | ? | ? | ? | — | 135 | 68 | 19 | 4 | 15 | 10 | INVALID |
| run_d28_C_s43_n16r60_seed43 | 16 | 60 | 43 | 04ff044e | 169 | 81 | 18 | 0 | 18 | 14 | meta |
| run_d2_after_n16_seed42 | 16 | 84 | 42 | 884f4541 | 206 | 102 | 20 | 0 | 20 | 16 | meta |
| run_d2_after_resume_ABORTED | - | - | - | - | - | - | - | - | - | - | no run.jsonl |
| run_d2_before_n12_ABORTED | - | - | - | - | - | - | - | - | - | - | no run.jsonl |
| run_d2_before_n16_seed42 | 16 | 84 | 42 | dc93c9d9 | 0 | 0 | 0 | 0 | 0 | 0 | meta |
| run_d4_P1_n16r12 | ? | 12 | ? | — | 37 | 19 | 9 | 0 | 9 | 6 | meta |
| run_d4_P2_n16r12 | ? | ? | ? | — | 0 | 0 | 0 | 0 | 0 | 0 | no-meta |
| run_d8_armA_n4r60_seed42 | 4 | 60 | 42 | 6602b777 | 40 | 20 | 3 | 0 | 3 | 3 | meta |
| run_d8_armB_n4r60_seed42 | 4 | 60 | 42 | 6602b777 | 40 | 20 | 3 | 0 | 3 | 3 | meta |
| run_d9_a1_n16r84_seed42 | 16 | 84 | 42 | 05636bcd | 206 | 102 | 20 | 0 | 20 | 16 | meta |
| run_dequant_baseline_n16r60_seed42 | 16 | 60 | 42 | 71a6d74b | 169 | 81 | 18 | 0 | 18 | 14 | meta |
| run_dequant_baseline_n8r16_seed42 | 8 | 16 | 42 | 71a6d74b | 25 | 13 | 5 | 2 | 3 | 3 | meta |
| run_dequant_on_n16r60_seed42 | 16 | 60 | 42 | 38889574 | 169 | 81 | 18 | 0 | 18 | 14 | meta |
| run_dequant_on_n8r16_seed42 | 8 | 16 | 42 | 38889574 | 25 | 13 | 5 | 2 | 3 | 3 | meta |
| run_dr_round1_arm-ctrl_n16r60_seed42 | ? | ? | ? | — | 169 | 81 | 18 | 0 | 18 | 14 | no-meta |
| run_f3_off_n16r60_seed42 | 16 | 60 | 42 | 6b7ae8a9 | 169 | 81 | 18 | 0 | 18 | 14 | meta |
| run_f3_on_n16r60_seed42 | 16 | 60 | 42 | 6f87363f | 170 | 81 | 23 | 0 | 23 | 19 | meta |
| run_f4_on_n16r60_seed42 | 16 | 60 | 42 | 6b7ae8a9 | 167 | 80 | 19 | 0 | 19 | 15 | meta |
| run_f6_dequp_n16r60_seed42 | 16 | 60 | 42 | 263a4300 | 169 | 81 | 18 | 0 | 18 | 14 | meta |
| run_f6_off_n16r60_seed42 | 16 | 60 | 42 | 895b9a38 | 169 | 81 | 18 | 0 | 18 | 14 | meta |
| run_f6_off_n16r84_seed42_VOID | ? | ? | ? | — | 37 | 19 | 9 | 0 | 9 | 6 | VOID |
| run_f6_on_n16r60_seed42 | 16 | 60 | 42 | 895b9a38 | 169 | 81 | 18 | 0 | 18 | 14 | meta |
| run_f6off_cycle06_seed42_n16r84 | 16 | 84 | 42 | 8f4330e9 | 206 | 102 | 20 | 0 | 20 | 16 | meta |
| run_g1_a1_n16r60_seed42 | 16 | 60 | 42 | 52492099 | 169 | 81 | 18 | 0 | 18 | 14 | meta |
| run_g1_b0_n16r60_seed42 | ? | ? | ? | — | 169 | 81 | 18 | 0 | 18 | 14 | no-meta |
| run_l7struct_on_n16r60_seed42 | ? | ? | ? | — | 169 | 81 | 18 | 0 | 18 | 14 | no-meta |
| run_l7v2_on_n16r60_seed42 | ? | ? | ? | — | 169 | 81 | 18 | 0 | 18 | 14 | no-meta |
| run_r10e2e_n16r60_seed42 | 16 | 60 | 42 | 625187c3 | 169 | 81 | 18 | 0 | 18 | 14 | meta |
| run_r6_treat_n16_seed42 | 16 | 84 | 42 | 7b6846dc | 210 | 104 | 22 | 0 | 22 | 18 | meta |
| run_r6_treat_n16_seed42_ABORTED_2036 | ? | ? | ? | — | 0 | 0 | 0 | 0 | 0 | 0 | ABORTED |
| run_scene_anchor_off_seed42_n16r24 | 16 | 24 | 42 | 44e37103 | 66 | 34 | 6 | 0 | 6 | 3 | meta |
| run_scene_anchor_on_seed42_n16r24 | 16 | 24 | 42 | d30520c8 | 66 | 34 | 6 | 0 | 6 | 3 | meta |
| run_worldline_c1_a1_n16r84_seed42 | ? | ? | ? | — | 206 | 102 | 20 | 0 | 20 | 16 | no-meta |
| run_worldline_c1_ctrl_n16r84_seed42 | ? | ? | ? | — | 206 | 102 | 20 | 0 | 20 | 16 | no-meta |

---

## §5 复算脚本与证据绑定

脚本（只读，参见本文件生成方式）核心三段：
1. **线程提取**（必须过滤 type）：`TYP = re.compile(r'"type":\s*"(MSG_[A-Z]+)"')`，只有匹配到的行才计入线程；
2. **round**：`msg_id.split('-')[-2]`；
3. **干净**：`min(round) < maxround - (T-1)`；`maxround` 取该日志 `TURN_SEAL.payload.round` 最大值（与 msg round 取大）。

关键输入 sha256（前 6 条候选臂）：
```
d42e2d921637a1e1f853e7d1c43ed45488afb7b23898a02d46ffac7f62add289  run_r6_treat_n16_seed42/run.jsonl
087072f84518eb009fb8d0a6ec445c5515b7561c1f031430702a5187394af16c  run_f3_on_n16r60_seed42/run.jsonl
dbff7b97b2820429b3378da0517283e1c34af246221286e666c9e28223977e64  run_d1_f6off_seed42_n16r84/run.jsonl
643f13a528c288d3e9677cb8ac100139224afbd0b46c0f7da0c3a5ed85b13141  run_d2_after_n16_seed42/run.jsonl
efb8b30f2969bd31d36ab75f6754632c3080ae0c6b5c370b5cdc60367656f07d  run_f6off_cycle06_seed42_n16r84/run.jsonl
aa6edc351cefdd9983ba8a58a4e673aaf7890cc742a5761f3dd5d2c1cd569e24  run_a5_real_n16r42_seed42/run.jsonl（A5，抽样来源）
```
`meta.json` 字段（候选臂，均为**事后派生件** `generated_after_run=true`，不作准入，仅陈列）：
- r6_treat：`code_sha=7b6846dce71eeb8b5e4f42cb82151bb39d468fe0`，events=193,959，degraded_calls=0，duration_sec=2735
- f3_on：`code_sha=6f87363fc30c52adf77d51b560aec312053ec484`，events=115,494，degraded_calls=0，duration_sec=2420
- d1_f6off：`code_sha=d7d1d93fa5871388fd8e51c44b6e179ac668b03f`，events=193,989，degraded_calls=0，duration_sec=2709
- d2_after：`code_sha=884f4541b80e5343119b51bf94054b2f54dd4559`，events=194,108，degraded_calls=0，duration_sec=3000

---

## §6 边界 / UNKNOWN（不猜）

| 项 | 状态 |
|---|---|
| `run_f3_on_n16r60_seed42` 的 provider 断言 | **待验**（未跑 `obs llm-cost`，见 §2） |
| "干净"是否还要排除**语义**截断（如话没说完但轮数已满） | **UNKNOWN**：本报告只做**几何**截断判定（末轮撞 run 尾），不含语义判定 |
| n32 | **不存在**（全库 meta 的 n ∈ {16,8,4}，最大 16）⇒ n32 路线必须新跑，无法借臂 |
| 借用 r84 臂是否会引入"与前几批不同 code_sha"的混杂 | **是**（候选臂 code_sha 各异）⇒ 若借用，须在证据里写明"措辞来自 <臂>@<code_sha>"，不能与 A5 的样本混算 |
| 该不该借、借哪条 | **不做建议**（Leader 域） |
