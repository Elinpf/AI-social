# `d12i_receipt_README.md` —— D12-I 收批验真（收口 `Q-17` 文档部分）

> 执行：metrics-engineer｜2026-10-24｜**零 LLM、不重跑批、只读、未 commit**
> 本文件只给**读数与对账结论**；**不含任何判定词**（达标/未达标/有效/无效一律不出现 —— D12-I 的判读属下一轮）。

## 0. 为什么有这份文件

- `Q-17`：收批目录在主树**没有 README** ⇒ 远端 clone 后不可复算。
- 本批（D12-I）收批目录里**缺 `llm_cost.txt`** —— 团队纪律「真 LLM 必须用 `obs llm-cost` 验真」缺证据。
- `CYCLE-12 §3.7` 的「派生≠本体」争执，根因是**没人把 `run.jsonl` 的 sha256/行数与 `meta.json` 对上**；本文件把这项对账做掉。

## 1. 收批状态（事实，逐项可核）

| 项 | 值 | 来源 |
|---|---|---|
| 收批目录 | `.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/` | — |
| `run_batch.rc` | `0` | 文件内容 |
| `run_batch.end` | `finished_at=2026-10-24T02:23:43+08:00` / `rc=0` | 文件内容 |
| `meta.finished_at` | `2026-10-24T02:23:41+08:00`（比 `run_batch.end` 早 2 s：meta 写完才写 end） | `meta.json` |
| `meta.started_at` | `2026-10-24T01:31:38+08:00` | `meta.json` |
| `meta.duration_sec` | `3123` | `meta.json` |
| `meta.events` / `meta.wc_l` | `117724` / `117724` | `meta.json` |
| `meta.run_bytes` | `58438033` | `meta.json` |
| `meta.code_sha` | `ca76ceb2e6ebfbe99450389186307c625e911974` | `meta.json` |
| `meta.provider` / `model_requested` | `openai_compat` / `DeepSeek-Flash` | `meta.json` |
| `meta.endpoint_host` | `172.16.3.41:31809` | `meta.json` |
| `meta.degraded_calls` / `fallback_detected` | `0` / `false` | `meta.json` |
| `meta.git_dirty_code_files` | `[]` | `meta.json` |
| 进程结局 | **正常退出**（`rc=0` + `run_batch.end` 齐全），非 kill | 两文件 |

## 2. `run.jsonl` 本体指纹与 `meta.json` 对账（**结论：本批派生 = 本体**）

| 量 | 实测值 | `meta.json` 声明 | 结论 |
|---|---|---|---|
| `sha256(run.jsonl)` | `72c0ca97fe6e38632f67e3b2810c65126c0d15d296d068b521dfbb45c8f5d0c4` | `run_sha256` = 同值；`derived_from_log_sha256` = 同值 | **三方一致** |
| 行数 `wc -l` | `117724` | `events` = `117724`、`wc_l` = `117724` | **一致** |
| 字节数 | `58438033` | `run_bytes` = `58438033` | **一致** |
| MSG 条数（实测，出数器 `n_msgs`） | `510` | `msg_counts` = `MSG_DM 455` + `MSG_PUBLIC 55` = `510` | **一致** |

**对 `CYCLE-12 §3.7`「派生≠本体」的处置结论**：
**本批 `meta.json` 就是从这份 `run.jsonl` 本体派生的**（sha256 三方同值 + 行数/字节/MGS 三项一致）。
⇒ 「派生≠本体」在本批**不成立**；但这不是对历史批的追认——历史批（如 D12-H/T5）**从未做过这项对账**，
其 `meta` 与日志是否同源**仍属未核项**，需按同一命令逐批补（不在本周期范围）。

复算命令：

```bash
sha256sum .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl
wc -l     .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl
python3 -c "import json;m=json.load(open('.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/meta.json'));print(m['events'],m['wc_l'],m['run_bytes'],m['run_sha256'],m['derived_from_log_sha256'])"
```

## 3. LLM 成本验真（补 `llm_cost.txt`）

命令（照 `tools/d2/run_batch.sh:82` 的标准写法，**从 `code/` 目录执行**）：

```bash
cd code && python3 -m obs llm-cost \
  --log ../.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --require-provider openai_compat
```

结果：**`rc = 0`**，输出落盘 `v2/evidence/form_metrics/d12i_llm_cost.txt`
（sha256 `76a68ed07c744730e4db3d19c3dce5a77cf674b9ff95985b9ab1f79eef797830`，1 行，即 `obs` 的原始单行 JSON，未改写）。

| 项 | 值 |
|---|---|
| `provider_guard.ok` | **`true`**，`problems = []` |
| `provider_guard.expected` | `openai_compat` |
| `engine_log.by_provider` | `{"openai_compat": 4200}`（**无 mock 混入**） |
| `total.calls` / `cached` / `degraded` / `thinking` | `4200` / `1583` / `0` / `668` |
| `total.tokens_in` / `tokens_out` / `tokens_total` | `516559` / `363620` / `880179` |
| 分用途 calls | `dialogue 1832`、`importance 1523`、`judge 668`、`reflect 112`、`negotiation 49`、`plan 16`（合计 4200） |

**与 `meta.json` 逐项对账（全部一致）**：

| 量 | `meta.json` | `llm-cost` | 一致 |
|---|---|---|---|
| `llm_calls` vs `total.calls` | `4200` | `4200` | ✅ |
| `llm_cached` vs `total.cached` | `1583` | `1583` | ✅ |
| `degraded_calls` vs `total.degraded` | `0` | `0` | ✅ |
| `llm_provider_in_events` vs `by_provider` | `{"openai_compat": 4200}` | `{"openai_compat": 4200}` | ✅ |
| `llm_model_in_events` | `{"DeepSeek-Flash": 4200}` | `obs` 不按模型分列（按 provider/用途） | 无冲突项 |

⇒ **本批 LLM 真实性有硬证据**：provider 计数 4200 全为 `openai_compat`、`provider_guard.ok = true`、
`degraded = 0`、`fallback_detected = false`、`mock_precalib_msg_count = 0`。

## 4. 全批形态读数（**只给读数，不判读**）

命令（全批，不限制 rounds；`--code-dir` 指向本臂自己的代码树，取 pfx2 显示名用）：

```bash
python3 tools/metrics/form_metrics.py \
  --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --code-dir .worktrees/d12i-aligned/code \
  --out v2/evidence/form_metrics/d12i_form_metrics_full.json \
  --batch-id D12-I --no-timestamp
```

落盘 `d12i_form_metrics_full.json`（350 行，sha256 `8d2f0d5feb0916882b6d0c4d011879104c56f3da673407d30334acdce641c88b`；
`--no-timestamp` ⇒ 重跑逐位一致，已实测两次同 sha256）。

| 指标 | 读数 | 分母 |
|---|---|---|
| `L-3_paren_block_any` | `0.723529` | 510（全部 MSG） |
| `addr_head_strict`（判据口径） | `0.262745` | 510（body 非空） |
| `addr_head_loose`（上界参照） | `0.282353` | 510 |
| `addr_head_pfx2`（下界参照） | `0.227451` | 510 |
| `addr_head_pfx2_plus`（参照量） | `0.227451` | 510 |
| `addr_head_alias`（只读指示量） | `0.0` | 510 |
| `L-1_len_p50` / `L-1_len_p50_excl_paren` | `70.0` / `55.0` | 510（分位分母） |
| `L-7_dup_ngram8_rate` | `0.621569` | 510（全部 MSG） |

`L-7` **本批索引 sha256 = `37ca0729e439df75faaa97c42f38133a0e51c950261b9166515c23d125739869`**
（**跨批不可互译**：与 D12-H `465593b8…`、T5 `aa1c61fc…` 均不同 ⇒ 三批 L-7 数值不得互相做差读作效果量）。

四个 addr_head 参照量的 `role` 在 JSON 内分别为 `criterion_primary` / `reference_only`，
判定只允许用 `addr_head_strict`（Leader 裁决 FM-3 / FM-4 / FM-5）。

## 5. 残留限制（必须与上表同屏）

1. **日志本体未入库**：`run.jsonl`（58,438,033 字节）仍在 `.worktrees/d12i-aligned/…`，**未复制进主树、未 `git add`**。
   ⇒ 远端 clone 后**无法完全复算**本批（只能核 README 里的 sha256 是否与将来拿到的同一份日志相符）。
   若要远端可复算，须另立任务把 58 MB 日志按项目既有归档方式入库（**不在本任务范围**）。
2. `meta.json`、`run_batch.rc`、`run_batch.end`、`shape_gate_first20.json`、`d12i_midpoint_gate.md` 同样在 worktree 内。
3. 本文件与两件落盘证据（`d12i_llm_cost.txt`、`d12i_form_metrics_full.json`）在主树
   `v2/evidence/form_metrics/`，**未 commit**（冻结期，提交由 report-writer 按 pathspec 执行）。

## 6. 本任务落盘清单

| 文件 | 行数 | sha256 |
|---|---|---|
| `v2/evidence/form_metrics/d12i_llm_cost.txt` | 1 | `76a68ed07c744730e4db3d19c3dce5a77cf674b9ff95985b9ab1f79eef797830` |
| `v2/evidence/form_metrics/d12i_form_metrics_full.json` | 350 | `8d2f0d5feb0916882b6d0c4d011879104c56f3da673407d30334acdce641c88b` |
| `v2/evidence/form_metrics/d12i_receipt_README.md`（本文件） | — | 见目录 `sha256sum`（自指不写死） |

## 7. 纪律自述

零 LLM、未重跑批、只读日志与 meta、未 kill 进程、未 commit / push、未碰 `code/life|orchestration|config|engine`；
`obs llm-cost` 仅解析日志、不发起调用。全文只有读数与对账结论，**无任何判定词**。
