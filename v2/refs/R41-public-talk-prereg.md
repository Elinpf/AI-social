# R41 公开面接话 · 预登记（CYCLE-42，跑前定死，跑后不得回改）

> 撰写时点：**起跑前**。本文件先于任何 CYCLE-42 正式批次落盘；落盘后到出数之间不得修改判据定义（CYCLE-41 缺口 G-4：R41 无预登记 ⇒ 本次补上）。
> 撰写人：`life-engineer`｜代码基线：`c325f19`（分支 `feat/life-public-talk-r41`）｜唯一自变量：`HITT_DIALOGUE_PUBLIC_REPLY`

## 1. 实验设计

| 项 | 值 |
|---|---|
| 臂 | OFF（不设 env）/ ON（`HITT_DIALOGUE_PUBLIC_REPLY=1`） |
| 规模 | `--seed 42 --agents 16 --rounds 24`（与 r38 on 批同规模，可作天然对照） |
| 串行 | 严格串行，前臂拿到 rc 才起后臂（`tools/d2/run_batch.sh` 内置 preflight） |
| 真跑判定 | `obs llm-cost --log <run.jsonl> --require-provider openai_compat`，`rc=0` 且 `by_provider` 仅 `openai_compat`、计数 > 0 |
| 允许的后果 | 两臂都允许"接话为 0"；阴性结果照写，不修饰 |

## 2. 判据（跑前写死）

统计单位（不得中途更换）：**一条 `type == "MSG_PUBLIC"` 的 jsonl 事件 = 1 次公开发言**。

| 编号 | 量 | 定义（分子 / 分母） | 字段 | 判定 |
|---|---|---|---|---|
| **PR-1** | `pub_reply_to_nonnull` | MSG_PUBLIC 中 `payload.reply_to` 非 null 的条数 / MSG_PUBLIC 总数 | `payload.reply_to` | OFF 臂**结构上不可 > 0** ⇒ 若 OFF > 0 即判"开关串扰/实验作废"；ON 臂 **≥ 1 条即"机制生效（存在性）"** |
| **PR-2** | `pub_thread_multi_turn` | 含至少一条 `turn_index > 0` 的公开 `thread_id` 个数 / 公开 thread 总数 | `payload.thread_id`,`payload.turn_index` | ON 臂 ≥ 1 即"公开面出现多轮同线程"；OFF 期望 0 |
| **PR-3** | `public_place_nonnull` | `payload.place` 非 null 的 MSG_PUBLIC 条数 / MSG_PUBLIC 总数 | `payload.place` | **接通闸**：ON 臂 < 90% ⇒ 判"机制未接通（机制层失败）"，此时 PR-1/PR-2 一律不作效果解读 |
| **PR-4** | `public_has_public_reply_ctx` | `payload.ctx.public_reply` 键存在的条数 / MSG_PUBLIC 总数 | `payload.ctx.public_reply` | 仅 ON 臂可 > 0；OFF 必须 = 0（只追加键的等价性守门） |

## 3. 分母门槛与可判性（预先声明，防止跑完改口）

- 以 r38 on 批同规模实测（`MSG_PUBLIC = 24`）为参照，16×24 规模 `MSG_PUBLIC` **可能 < 30**。
- 规则：`MSG_PUBLIC < 30` ⇒ 本报告**只报条数与两臂差值**，所有比率标 `probe=true`，**不给任何显著性/百分比结论**。
- 禁止表述：「生活气息提升」「接话质量变好」「公开面已像小镇」。允许表述：「机制是否接通」「存在性是否成立」「条数差是多少」。

## 4. 噪声带 / 混杂控制

- 两臂同 seed、同规模、同代码（同一 `git rev-parse HEAD`），唯一差异是 env 开关。
- 记录两臂 `meta.json` 的 `llm_calls` 与 `code_sha`，若两者不同即判"对照不成立"。
- 已知非对称（必须写进报告）：`payload.place` 由 `integration.py::_r41_public_place()` 在 **ON 时**注入，OFF 臂为 null ⇒ `place_adjacency` 与 PR-3 在 OFF 臂不可比，只作 ON 侧接通证据。

## 5. 成功/失败判读表（跑完照此判）

| 观测 | 判读 |
|---|---|
| ON PR-3 < 90% | **机制未接通**（机制层失败，非效果不佳） |
| ON PR-3 ≥ 90% 且 PR-1 = 0 | 机制接通但**未触发接话**（成效为零，如实写） |
| ON PR-3 ≥ 90% 且 PR-1 ≥ 1、OFF PR-1 = 0 | **机制生效（存在性成立）**；质量另判，不并入本判据 |
| ON PR-1 ≥ 1 但 OFF PR-1 > 0 | **实验作废**（开关串扰），需排查后重跑 |
