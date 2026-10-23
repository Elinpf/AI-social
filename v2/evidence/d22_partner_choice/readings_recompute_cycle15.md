# C. 关键读数重算与 CYCLE-14 对照表（防漂移）

- 目的：逐项**自跑**出数器，与 `reports/CYCLE-14-20261024.md` 登记的数值比对。
- 结论先行：**5 组读数全部一致（0 项不一致）**，无需向 Leader 上报漂移。
- 口径纪律（runbook §3.113）：近似量并列输出、名字带口径后缀、互不替代。

## C.0 本文件用到的来源件与指纹

| 件 | 路径 | sha256 |
|---|---|---|
| D12-I 日志 | `.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl` | `72c0ca97fe6e38632f67e3b2810c65126c0d15d296d068b521dfbb45c8f5d0c4` |
| T5 日志 | `.worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42/run.jsonl` | `dd4ad73d5a21c7485c2afbfc9701e267c25da3150b10adade3b3819a3996ff36` |
| D12-H 日志 | `.worktrees/d12h-pairing/v2/evidence/run_d12h_pairing_n16r60_seed42/run.jsonl` | `122b36e988267a396cfdd95b167bad92bf69beabc249c253b46555f2679c3207` |
| F-1 复算器 | `v2/evidence/life_texture_cycle14/f1_recompute.py` | 见其目录 `SHA256SUMS` |
| 形态出数器 | `tools/metrics/form_metrics.py` | — |
| 重复度三口径 | `tools/metrics/d12i_dup_calibers.py` | — |
| 轮子 sha（d5） | `tools/d5/dialogue_metrics.py` | `1d914735f3a13cf4e1640bd694f1d0e070096c9f50abfdefa7359417df551271` |

复算总命令：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# C.1 F-1 三臂
python3 v2/evidence/life_texture_cycle14/f1_recompute.py \
  --arm D12-I=.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --arm T5=.worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42/run.jsonl \
  --arm D12-H=.worktrees/d12h-pairing/v2/evidence/run_d12h_pairing_n16r60_seed42/run.jsonl \
  --out-json v2/evidence/d22_partner_choice/f1_recompute_cycle15.json

# C.2–C.4 形态读数（L-3 / addr_head 双口径 / L-7 norm8）
python3 tools/metrics/form_metrics.py \
  --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --code-dir .worktrees/d12i-aligned/code \
  --out v2/evidence/d22_partner_choice/form_metrics_D12-I_cycle15.json \
  --batch-id D12-I --no-timestamp

# C.4 L-7 raw8 口径（norm8 已在上一件，二者并列）
python3 tools/metrics/d12i_dup_calibers.py \
  --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --out v2/evidence/d22_partner_choice/dup_calibers_D12-I_cycle15.json

# C.5 成本
cd code && python3 -m obs llm-cost \
  --log ../.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --require-provider openai_compat
```

## C.1 F-1 非功能性闲聊占比（三臂）

| 臂 | 本周期重算 | CYCLE-14 登记值 | 对照 |
|---|---|---|---|
| D12-I | `363/510 = 71.1765%`，Wilson95 `[0.670987, 0.749376]` | `363/510 = 71.1765%`，`[0.670987, 0.749376]`（`reports/CYCLE-14-20261024.md:120` 邻近表 §2.1） | **一致** |
| T5 | `364/510 = 71.3725%`，`[0.673012, 0.751244]` | `364/510 = 71.3725%`，`[0.673012, 0.751244]`（`…:120`） | **一致** |
| D12-H | `360/510 = 70.5882%`，`[0.664916, 0.743770]` | `360/510 = 70.5882%`（`…:151`） | **一致** |

分母口径：`n_msg = 510`（全部 MSG）。判据出处：`reports/R4-life-texture.md:33`；实现 `tools/d5/dialogue_metrics.py`（sha `1d914735…1271`）。
证据状态：**已验证（重算）**。
> 纪律：F-1 现阶段**不宜作闸**（CYCLE-14 Leader 定调 2），本表只作描述性对照，不做「趋势/效果」解读。

## C.2 L-3 旁白率（`L-3_paren_block_any`）

| 项 | 本周期重算 | CYCLE-14 登记值 | 对照 |
|---|---|---|---|
| 分子/分母 | `369 / 510` | `369 / 510` | **一致** |
| 值 | `0.723529 = 72.3529%` | `0.723529（72.3529%）` | **一致** |

口径：分子 = body 命中任一括号块（`PAREN_ANY_RE`）的 MSG 条数；分母 = 全部 MSG（d5 `meta.n_messages`）。实现 `tools/d5/dialogue_metrics.py::compute()` → `L_wording.L-3_paren_block_any`。

## C.3 `addr_head` 双口径并列（**不得互代**）

| 口径名 | 本周期重算 | CYCLE-14 登记值 | 差 | 对照 |
|---|---|---|---|---|
| `addr_head_pfx2`（下界参照） | `116 / 510 = 22.7451%` | `116/510 = 22.7451%` | — | **一致** |
| `addr_head_strict_personas20`（判据唯一口径） | `134 / 510 = 26.2745%` | `134/510 = 26.2745%` | — | **一致** |
| 两者之差 | `18 条消息 / 3.5294pp` | `3.53pp（18 条）` | — | **一致** |

口径名后缀：`pfx2` = 名字在第 0 位、后缀 ≤2 字后接 `，/：:`（逐字复用 `shape_gate.py::is_addr_head()`，源件 sha `f7740b6d…0ea3`）；`strict_personas20` = 以 `code/config/personas.json` 的 20 个 `display_name` 之一起头（`d12h_verdict_amendment3.md §C:47` 冻结口径）。两者是**两个不同的量**，引用必须带后缀。

> 附带重算但**不进判据**的参照量（同 `form_metrics_D12-I_cycle15.json`）：`addr_head_loose = 144/510 = 28.2353%`（上界参照）、`addr_head_pfx2_plus = 116/510`（与 pfx2 逐位相同）、`addr_head_alias = 0/510`（只读指示量）。均与 CYCLE-14 表 §2.4 一致。

## C.4 L-7 重复度双口径并列（`norm8` / `raw8`）

| 口径名 | 本周期重算 | CYCLE-14 登记值 | 对照 |
|---|---|---|---|
| `L-7_dup_ngram8_rate`（norm8） | `317 / 510 = 62.1569%`；索引 sha `37ca0729e439df75faaa97c42f38133a0e51c950261b9166515c23d125739869`（27,639 gram） | `317/510 = 62.1569%`，索引 sha `37ca0729…9869` | **一致** |
| `L-7_raw8_shingle`（raw8） | `368 / 510 = 72.1569%` | `368/510 = 72.1569%` | **一致** |
| 两者差 | `51 条 / 10.0pp` | `51 条（10.0pp）` | **一致** |

口径说明：`norm8` = `d5.normalize_body()` 归一后 8-gram 重合；`raw8` = **未归一原文** 8-gram 重合（`d12i_dup_calibers.py` 现算，口径 ≠ d5 的 norm8）。二者**分子不同、互不替代**，且**跨批不可比**（索引 sha 是参照系指纹）。同件另给 `raw_exact = norm_exact = 47/510 = 9.2157%`（=`dup_exact_rate`），与 CYCLE-14 §2.3/§2.5 交叉验证值 `0.092157（47/510）` 一致。

## C.5 obs llm-cost（D12-I 批，**非本周期成本**）

| 项 | 本周期重算 | CYCLE-14 登记值 | 对照 |
|---|---|---|---|
| `rc` | `0` | `0` | **一致** |
| `provider_guard.ok` | `true`，`problems=[]`，`expected=openai_compat` | 同 | **一致** |
| `by_provider` | `{"openai_compat": 4200}` | 同 | **一致** |
| `total.calls` / `cached` / `degraded` / `thinking` | `4200 / 1583 / 0 / 668` | `4200 / 1583 / 0 / 668` | **一致** |
| `total.tokens_in` / `tokens_out` / `tokens_total` | `516559 / 363620 / 880179` | `516,559 / 363,620 / 880,179` | **一致** |
| 分用途 `calls` | `dialogue 1832`、`importance 1523`、`judge 668`、`reflect 112`、`negotiation 49`、`plan 16`（合 4200） | 同 | **一致** |
| `llm_cost.txt` 文件 sha256 | `76a68ed07c744730e4db3d19c3dce5a77cf674b9ff95985b9ab1f79eef797830` | `76a68ed0…7830` | **逐字节一致** |

> 说明：本次 `obs llm-cost` 重跑输出与 CYCLE-14 入库的 `llm_cost.txt` **逐字节相同**（同 sha），说明该命令对该日志是**确定性**的。
> 口径限定：这是 **D12-I 批** 的历史成本，不是 CYCLE-15 成本；本周期方法层零 LLM、零跑批。
> 纪律提醒（runbook §3.101）：`llm-cost` 的 `rc` ≠ 跑批进程 `rc`，不可混报。

## C.6 对照结论

- 5 组 / 12 个数值项**全部一致**，**无漂移**、**无需上报 Leader**。
- 全部读数在 5 分钟内可复现（见 C.0 命令）。
- 证据状态统一：**已验证（本周期重算）**。
