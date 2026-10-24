# CYCLE-21 提交窗口勘定 与 D2.7 证据盘点（recon 件，非结论件）

> 作用：为《周期实验报告》`reports/CYCLE-21-20261024.md` 的 §一 与页首 sha 绑定的**可信底座**。
> 本件**只做取证与盘点**，不出效果结论、不改任何判定词；所有数字/ sha 均可原地重放。
> 作者：evidence-auditor（提交窗口与证据审计员）。取数时点：**2026-10-24 16:31–16:36 +0800**。
> 仓库根：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment`（下文相对路径均以此为根；外层 `嘗試` 不是 git 仓库）。
> 取数时点 HEAD：`dc02e06da5f0d17f251465bc92cab11b2e9a22e1`（`master`，提交时间 `2026-10-24 16:29:35 +0800`）。
> 取数时点**工作树状态指纹**（`git status --porcelain | sha256sum`）：
> **`251a7895cbddc8b46cafa779fc658d73be7e9b2ac6d8664d9e0d2fcc488450de`**（16:36 观测：2 个 `M` + 27 个 `??`，共 29 行）→
> **`fc001adb20e7501a56badbe1851d39bff221a3d2f9967528306eeb92b62624d6`**（16:38 复测：2 个 `M` + 32 个 `??`，共 35 行；增量来自队友新建的 `v2/evidence/cycle21_cases/`、`cycle21_shots/`、`cycle21_recon/`）。
> ⇒ **指纹是活的**：它随队友落盘而变化，**说明只写 HEAD 一定不够**。报告落笔时须重新执行 `git status --porcelain | sha256sum` 并就地冻结，写明"分析基准 = `dc02e06` + 该时刻指纹"。
> ⇒ **「分析基准 sha」必须与本指纹同屏书写**：HEAD 相同而工作树不同，读数就可能不同（见 §7.1 的活例）。

---

## 0. 对任务卡的一处更正（先立规矩：以 git 实跑为准）

任务卡原写「预期区间 `a0fb1eb..dc02e06`，含 **10 条**提交」。**实测为 11 条**，多出的是
**`21b6738`（`result(d25a)`，`2026-10-24 12:58:48`）**——它在 `a0fb1eb`（12:43:57）之后，属本区间。
team-leader 已于 16:33 发消息确认该更正（`report-author` 独立自算同为 11）。本件全部以实测为准。

---

## 1. 区间边界实测证明（命令 + 实测输出 + 退出码）

### 1.1 两端 sha 实测与对象类型

```bash
git rev-parse a0fb1eb          # a0fb1ebcee133ab16d79d9700eca2ac0ac9878db     exit=0
git cat-file -t a0fb1eb        # commit                                        exit=0
git rev-parse dc02e06          # dc02e06da5f0d17f251465bc92cab11b2e9a22e1      exit=0
git cat-file -t dc02e06        # commit                                        exit=0
```

### 1.2 左端 `a0fb1eb` 的身份（不是随口说「上一份报告之后」）

```bash
git log -1 --pretty='%H %ad %s' --date=format:'%Y-%m-%d %H:%M:%S' a0fb1eb
# a0fb1ebcee133ab16d79d9700eca2ac0ac9878db 2026-10-24 12:43:57 report(cycle20): cd0e85b..1aa57a1 恰 1 条判定/文档修正(...)
```
⇒ 左端 = `reports/CYCLE-20-20261024.md` 的入库提交（`report(cycle20)`），**左开**：该提交本身不计入本区间。

### 1.3 计数、方向、端点互斥（三条独立证据）

```bash
git rev-list --count a0fb1eb..dc02e06     # 11      exit=0
git rev-list --count dc02e06..a0fb1eb     # 0       exit=0   ⇒ 方向正确，无反向漂移
git rev-list a0fb1eb..dc02e06 | head -1   # dc02e06da5f0d17f251465bc92cab11b2e9a22e1
git rev-list --reverse a0fb1eb..dc02e06 | head -1   # 21b673869c417cac58a37810b361ca18e1210aab
git rev-list a0fb1eb..dc02e06 | grep -c "$(git rev-parse a0fb1eb)"   # 0  grep_exit=1
```
⇒ **左端 `a0fb1eb` 不在区间内**（`grep -c` = 0，grep 退出码 1 = 未匹配），**右端 `dc02e06` 在区间内**（`rev-list` 首条）。

### 1.4 区间是否线性（有无合并/分叉）

```bash
git rev-list --merges --count a0fb1eb..dc02e06   # 0        exit=0
git rev-list --first-parent --count a0fb1eb..dc02e06  # 11   exit=0
git rev-list --parents -1 dc02e06                # dc02e06… 4d619b5b3e139e89a638ff932b6b500f36c01a84
```
⇒ **纯线性、零合并**，11 条 = 11 步 first-parent。区间表（§2）即完整历史，无侧支遗漏。

### 1.5 端点邻居（供复核方逐层对照）

```bash
git rev-parse a0fb1eb^1   # 1aa57a12450b421b491dc341794cec12684ee9f7  （CYCLE-20 的分析基准）
git rev-parse dc02e06^1   # 4d619b5b3e139e89a638ff932b6b500f36c01a84  （区间倒数第 2 条）
```

**判定：区间 = `a0fb1eb..dc02e06`，左开右闭，实测 11 条，纯线性。**

---

## 2. 区间内全部提交逐条表（11 条，按时间正序）

取法：`git log --pretty=format:'%h|%ad|%s' --date=format:'%Y-%m-%d %H:%M:%S' --reverse a0fb1eb..dc02e06`，
逐条路径用 `git show --name-status --pretty=format:'' <sha>`。**「自有交付」= 本组本轮产出的判定/证据/规则文档**（本区间无外部提交、无 `code/` 变更，见 §2.1）。

| # | 短 sha | 时间(+0800) | 标题（截断至判定词） | 自有交付 | 涉及路径（A=新增 M=修改） |
|---|---|---|---|---|---|
| 1 | `21b6738` | 12:58:48 | `result(d25a)`: 判「无效(加长靠复述与重复)」 | 是 | A `v2/evidence/d25a_result.md`；A `v2/refs/D25a-amendment1-baseline-and-gates.md` |
| 2 | `ac3d2b7` | 13:28:24 | `diag+prereg(D2.7)`: 旁白消失根因=agent.py:1453/1478 | 是 | A `v2/evidence/d27_paren_removal_root_cause.md`；A `v2/refs/D27-prereg-restore-paren.md` |
| 3 | `9aaceee` | 13:58:18 | `prereg(D2.7)`: 立项放开旁白（第二份预登记） | 是 | A `v2/evidence/d27_narration_ban_rootcause.md`；A `v2/refs/D27-prereg-narration.md` |
| 4 | `d24e3fd` | 14:28:27 | `amend(D2.7-1)`: 合并两份并存预登记、定唯一判据 | 是 | A `v2/refs/D27-amendment1-merge-duplicate-prereg.md`；M `v2/refs/D27-prereg-restore-paren.md` |
| 5 | `fa58a93` | 14:30:53 | `correct(d25a-2)`: P 读数分母漏 55 个匿名旁白线程 | 是 | A `v2/evidence/d25a_result_amendment2.md` |
| 6 | `5f73676` | 14:30:53 | `runbook §3.119`: 线程级比例分母须含匿名旁白线程 | 是 | M `v2/refs/batch-hosting-runbook.md` |
| 7 | `4f70eeb` | 14:31:34 | `review(d27)`: 接线审查通过①②，③被并发闸挡 | 是 | A `v2/evidence/d27_wiring_review.md` |
| 8 | `f2bf606` | 14:58:18 | `review(d27)`: 前两项验收通过，mock 仍被挡 | 是 | M `v2/evidence/d27_wiring_review.md` |
| 9 | `f8a9113` | 15:28:24 | `accept(d27-C)`: C 臂收批验收合法可用（rc=0/510MSG/169线程） | 是 | A `v2/evidence/d27_C_arm_acceptance.md` |
| 10 | `4d619b5` | 15:58:34 | `baseline(d27-C)`: C 臂完整基线 + P1 天花板预警 | 是 | A `v2/evidence/d27_C_baseline_readings.json`；A `v2/evidence/d27_C_baseline_readings.md` |
| 11 | `dc02e06` | 16:29:35 | `result(d27)`: 判「作废(台词被旁白挤短)」 | 是 | A `v2/evidence/d27_result.md` |

### 2.1 两条硬事实（报告 §一 必须写清，否则会误导）

```bash
git log --oneline a0fb1eb..dc02e06 -- code/        # （空）exit=0
```
⇒ **本区间 11 条提交没有一条改动 `code/`**；治疗臂的代码改动**不在 master 上**（见 §7.2）。

```bash
git rev-list --parents -1 dc02e06   # 单父 ⇒ 无合并
```

---

## 3. 本周期证据文件清单（路径 + sha256 + 入库状态）

sha256 取法：`sha256sum <path>`。入库复核取法（三件套，任一条都能原地重放）：

```bash
git ls-files --error-unmatch <path>              # 是否已入库
git rev-parse "HEAD:<path>"                      # 入库 blob 对象名
git cat-file -p <blob> | sha256sum               # 由 blob 内容重算 sha256，与工作树 sha256 对照
```
> **口径声明**：`sha256(blob)` 恒等于同名工作树文件的 `sha256sum`；**MATCH** 表示"入库内容 = 我此刻读到的工作树内容"，
> **DIFF** 表示"工作树已被改、入库版是旧版"（见 `d27_C_baseline_readings.md`）。这是区分「时点状态」与「交付状态」的唯一办法。

### 3.1 单文件（12 项）

| 路径 | 工作树 sha256 | 入库状态 | blob / 复核 |
|---|---|---|---|
| `v2/evidence/d27_paren_removal_root_cause.md` | `4e2c8bf2bcd5a0201877bbad58ff9a0034b27dce73151f1f092fa38b750037de` | 已入库 `ac3d2b7` | blob `0237f0d3…` / **MATCH** |
| `v2/evidence/d27_narration_ban_rootcause.md` | `cde1837ddf98b2b37681a5a5ef26281ac718db906948a8c2ec6e8b55cfbc30ed` | 已入库 `9aaceee` | blob `417c785a…` / **MATCH** |
| `v2/evidence/d27_C_arm_acceptance.md` | `c507392538541f553421666cfbca9f87d208cf93445b43c8ec744ae0c27450cd` | 已入库 `f8a9113` | blob `a2109eed…` / **MATCH** |
| `v2/evidence/d27_C_baseline_readings.md` | `674f7406bf6b1dd16fd7266227170207641bb6e1b79f01ee0f80a7772e4ef218` | 已入库 `4d619b5`，**工作树已改（M）** | blob `46ffd7e4…` = `f2166616554daaca0587dc9dac25db26d4350c89da798e01d86a4855de3d39ee` / **DIFF** |
| `v2/evidence/d27_C_baseline_readings.json` | `ffbd9a905d32d9573b50af6005d7c80f343f4ff404dc11d3f89b1f10b434758b` | 已入库 `4d619b5` | blob `f17c656b…` / **MATCH** |
| `v2/evidence/d27_gate_prediction_prereg.md` | `bf1a657623a468222319f633421b79e967bb447d06a1e8c8fc6e14196f509f6a` | **未入库** | — |
| `v2/evidence/d27_gate_verification.md` | `b1f1f9a8d57c02c44168afee1cb0f72b4b957b735b3ab3144ea7177b2b983c78` | **未入库，且仍在被改**（16:30:27 版为 `d23892f2…`/10,926 B，16:33:16 版为本值/13,441 B） | — |
| `v2/evidence/d27_result.md` | `0fde7dcad5740bfca51b7518e4eb6604e3ecd32bd1edb9611b3114ecd1b45ba6` | 已入库 `dc02e06` | blob `3ee08a4c…` / **MATCH** |
| `v2/evidence/d27_wiring_review.md` | `fc4f62be3bfab8b65fb5d6d71e0b183a6c6d27bbd1951512b7af9aac5ae68abd` | 已入库 `f2bf606` | blob `7e0eeb30…` / **MATCH** |
| `v2/evidence/d25a_result_amendment2.md` | `c3e72913274b6b9a9203b9b9482e13fd20d466e2370e5d0b107eedf609253679` | 已入库 `fa58a93` | blob `5d6390b7…` / **MATCH** |
| `v2/evidence/d25a_amendment1_Tgate_relative.md` | `f1329974e8fd5a62c219c9bb114ad39433a28c091e87ced11bab79d282fec183` | 已入库，但**在区间外**（`1aa57a1`，即 `a0fb1eb` 的父，属 CYCLE-20 区间） | blob `8f4d7711…` / **MATCH** |
| `v2/evidence/d25a_gates.py` | `3cf1b35f815e95777f8eadbae03f57050822ac767c36bbdfb5085d16093ed227` | **未入库**（mtime `2026-10-24 10:04`，早于区间起点） | — |

### 3.2 目录（4 个）

| 目录 | 文件数 | 说明 | 入库状态 |
|---|---|---|---|
| `v2/evidence/d27_harvest/` | **26**（含 `_selftest_c_vs_c/` 12 件；含 16:35:48 新增的 `HANDOFF-to-gate.md`） | D2.7 复算产物：`d27_gates.py/.json`、`d27_metrics.py`、`p1_count.py`、`dm_B/dm_C`、`shape_B/C`、`l15_c_b`、`d12c_c_b` 等 + 移交件 `HANDOFF-to-gate.md`。全 26 件 sha256 见同目录 `commit_window.json` 的 `evidence_files.dirs` | **未入库** |
| `v2/evidence/d27_shots/` | **5**（3 PNG + `render_d27_shots.sh` + `render_wrap.log`） | §四 案例截图（C/B 同线程 `TH-P009-P008-24` 对照），PNG sha256 与 `d27_gate_verification.md` §6.1 逐值一致 | **未入库** |
| `v2/evidence/run_d27_C_n16r60_seed42/` | **9**（其中 `run.jsonl` 56.5 MB、`run_batch.log`、`host.log` 被 `.gitignore` 忽略） | C 臂真 LLM 跑批（`code_sha=f2bf606`，`rc=0`，`llm_calls=2878`，`finished_at=14:59:23`）。可入库子集 = `code_id_start.txt` / `frozen_diff_start.txt`(空) / `git_status_start.txt` / `meta.json` / `run_batch.end` / `run_batch.rc` | **未入库** |
| `v2/evidence/cycle20_shots/` | 5 | 上一周期截图，`a0fb1eb` 已入库，本周期**未改动** | 已入库（`a0fb1eb`） |

**忽略规则实测**（决定"哪些根本进不了库"，不是我说了算）：

```bash
git check-ignore -v v2/evidence/run_d27_C_n16r60_seed42/*
# .gitignore:8:**/*.jsonl   v2/evidence/run_d27_C_n16r60_seed42/run.jsonl
# .gitignore:63:**/*.log    v2/evidence/run_d27_C_n16r60_seed42/host.log
# .gitignore:63:**/*.log    v2/evidence/run_d27_C_n16r60_seed42/run_batch.log
```
⇒ `run.jsonl`（54 MB）与两份 `.log` **按仓库规则不入库**；仓内先例（`v2/evidence/run_d12c_on_n16r60_seed42/` 只入库 `END`/`meta.json`/`switch_proof.txt`/`arm_state_check.txt`）与本次可入库子集一致。

### 3.3 B 臂跑批（在主树之外，需单独核实）

```bash
git worktree list | grep d27-narration
# …/.worktrees/d27-narration   c749850 [feat/d27-narration]

cd .worktrees/d27-narration
git rev-parse HEAD                     # c74985050b86f31c21f4ab90da8d9244b3410251
git log -1 --pretty='%h %ad %s' --date=format:'%Y-%m-%d %H:%M:%S'
# c749850 2026-10-24 14:30:57 evidence(d27): mock 验证前两项——prompt_fn_sha256 47623c9d→f553b4c4…
git merge-base HEAD dc02e06            # 9aaceee0c141dc7d3986cae9417547f3716f41d2
git log --pretty='%h|%ad|%s' --date=format:'%Y-%m-%d %H:%M:%S' dc02e06..HEAD
# c749850|2026-10-24 14:30:57|evidence(d27): mock 验证前两项…
# 4123628|2026-10-24 14:04:35|feat(D2.7): 放开旁白——仅改 agent.py:1453/1478 收尾指令的旁白半段…
```

| 项 | 值（取法见上） |
|---|---|
| B 臂 run 目录 | `.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/`（**未跟踪**，主树看不到） |
| `meta.code_sha` = `meta.code_sha_end` | `c74985050b86f31c21f4ab90da8d9244b3410251` ⇔ worktree HEAD（一致） |
| `meta.run_sha256` / `run.jsonl` sha256 | `87e233c421aebeb5ecf3d4f37c74ba721cd6829f3d7e55ec75042e76d350f2f4`（两值一致，`derived_from_log_sha256` 同值） |
| `started_at` / `finished_at` / `duration_sec` | `15:32:28` / `16:23:24` / `3056` |
| `llm_calls` / `events`(= `wc -l run.jsonl`) | `2869` / `115545` |
| `git_dirty_code_files` | `[]`（code/ 无未提交改动） |
| `git_dirty_files` | 9 项，全为 `??`（其中 7 个 preflight json、1 个 `d27_run_scripts/d27_metrics.py`、1 个本 run 目录） |
| **`run_batch.rc`** | **`9`**（⚠ 见 §7.1：不是本批的退出码） |

---

## 4. 工作树脏项清单与建议处置

取法：`git status --porcelain=v1`（29 行）；`git diff --stat` ⇒ 仅 2 个 `M`（`d27_C_baseline_readings.md` +37/−? 行、`d3_noiseband_bootstrap.json` +25/−125 行）。

### 4.1 已修改（`M`）2 项

| 路径 | mtime | 内容性质 | 建议 | 理由 |
|---|---|---|---|---|
| `v2/evidence/d27_C_baseline_readings.md` | 16:28:04 | **实质更正**：C 臂 4 项基线被证为**跨批污染**（原值来自 d25a C / `e2e7131`），已改双列 `原值(污染) → 本批现算(采用)`：Q1 4.12→**4.31**、Q2 20.59→**25.49**、Q3 66.28→**63.34**、T 40.0→**41.0**；判据阈值一个未改 | **必须随本报告入库**（与 `d27_gate_verification.md`、`d27_harvest/` 同批） | 它是 `4d619b5` 的错误基线的**唯一更正载体**；不入库则 §二 的 C 列读数无法溯源，且 `dc02e06` 的提交信息与本表互相矛盾（§6） |
| `v2/evidence/d3_noiseband_bootstrap.json` | **2026-10-23 10:11:52** | **历史脏项**：D3 噪声带口径由 `denom_480` 改 `denom_341`，各指标带宽整体变化（如 `L-7 8gram_shared` `7.5pp→14.66pp`）；最后入库提交是 `b21042b`(2026-10-21 00:11:56) | **忽略 / 不裹带**（另行单独提交或明确作废） | ① 时点 `10-23 10:11` **早于本区间起点 `10-24 12:43`**，属 CYCLE-20 之前遗留；② 与 D2.7 无任何关系（噪声带 vs 旁白）；③ 裹带会让"本周期证据边界"失真，且无人能说清它属于哪个判定 |

### 4.2 未跟踪（`??`）27 项（16:36 时点）—— 按归属分三类

> ⚠ 时点说明：16:38 复测已是 **32 个 `??`**，增量是队友新建的 `v2/evidence/cycle21_cases/`、`v2/evidence/cycle21_shots/`、`v2/evidence/cycle21_recon/`（后者是本件自身）。
> 前两者为 case-curator 的 §四 素材目录 → 由其在自身任务内决定入库/不入库，**本件不代判**；`cycle21_recon/` 是本审计件，**随报告入库**。

| 类 | 项 | 时点 | 建议 | 理由 |
|---|---|---|---|---|
| **A. 本周期必须入库（D2.7 证据链）** | `v2/evidence/d27_gate_prediction_prereg.md` | 16:13:20 | **入库** | 事前预测件（写于 B 臂 round 45/60、未出数前），是"接线已生效"的**事前可判**依据；不入库则 §二 P/T 的接线论证无源 |
| | `v2/evidence/d27_gate_verification.md` | 16:33:16（**仍在改**） | **入库**，但须**先冻结** | 独立验收件；⚠ 入库前必须确认作者已停笔（16:30→16:33 已变更两次，sha 从 `d23892f2…`→`b1f1f9a8…`）；入库 sha256 以提交时刻为准 |
| | `v2/evidence/d27_harvest/`（26 件，含 `HANDOFF-to-gate.md`） | 16:29–16:36 | **入库** | §二 每个百分数的**可复算产物**（分子/分母/判据编号都在 `d27_gates.json`）；含 `_selftest_c_vs_c/` 自检对，是"换树≠复现"铁证的脚注；`HANDOFF-to-gate.md` 为 metric-recomputer 的移交说明（16:35:48），随产物一并入库 |
| | `v2/evidence/d27_shots/`（5 件） | 16:31 | **入库** | §四 案例素材，PNG 与 `run.jsonl` sha 前 8 绑定（`1fbb9ef5`/`87e233c4`）；先例 `cycle20_shots/` 即随报告入库 |
| | `v2/evidence/run_d27_C_n16r60_seed42/` 的 6 个非忽略件 | 14:04–14:59 | **入库**（`meta.json`/`run_batch.rc`/`run_batch.end`/`code_id_start.txt`/`frozen_diff_start.txt`/`git_status_start.txt`） | C 臂是全部对照的基线，`code_sha=f2bf606` + `rc=0` 必须可原地复核；`run.jsonl`/`.log` 按 `.gitignore` 不入库（§3.2） |
| | **（被修改的）** `d27_C_baseline_readings.md` | 16:28 | **入库**（见 4.1） | 同上 |
| **B. 本周期产物的 `code/` 影子目录（实证见 §4.3）** | `code/frontend/sample/dialogue_d27_C/`（`threads.json` 2,153,042 B）、`code/frontend/sample/dialogue_d27_B/`（`threads.json` 2,093,912 B） | 目录/文件 mtime `16:30:28.07` / `16:30:29.00` | **不入库**（不删、不移） | 它们是 `code/frontend/tools/gen_threads.py` 对**本轮** d27_C / d27_B 日志生成的中间产物，但**写在了 `code/` 里**；`d27_gate_verification.md` §6.1「纪律提示」明确"**不得纳入本次提交**"。登记入 §1.4「未提交产物」即可（详见 §4.3 溯源）。 |
| **C. 历史遗留脏项（与 D2.7 无关，不得裹带）** | `code/frontend/sample/dialogue_a5_full6/`、`dialogue_a5_multiturn/`、`dialogue_cycle03_ctrl/`、`dialogue_cycle04_a5/`、`dialogue_cycle06_f6off/`、`dialogue_cycle06_f6on/`、`dialogue_cycle07_d12c_off/`、`dialogue_cycle07_d12c_on/`、`dialogue_f2b_v2_off/`、`dialogue_r21_scene_off/`、`dialogue_r21_scene_on/` | 各异 | **不入库** | 十余个历史臂的样例目录，均非本周期产物；裹带会把无关渲染数据混进周期提交 |
| | `tools/f2/r10e2e_forget_levels.py`、`v2/evidence/forget_levels_f2b_v2_off_a9c74f5.json`、`v2/evidence/forget_levels_g1_b0_d9391a3.json`、`v2/evidence/run_r10e2e_n16r60_seed42/`、`v2/evidence/e1_run_scripts/` | 各异 | **不入库** | 属 r10/e1/f2b/g1 等其他实验线，与 D2.7 无关 |
| | `v2/evidence/d12h_shots/`、`v2/evidence/cycle06_shots/_blank_check_failed/` | 历史 | **不入库** | 历史截图目录；后者名字即"自检失败"，更不该混入 |
| | `v2/evidence/preflight/clean_tree_20261024T060438Z_9aaceee0_run_batch.json` | 06:04 | **不入库** | 早于区间起点的 preflight 记录（且 `clean_tree` 判定已被后续 run 覆盖） |
| | **`v2/evidence/d25a_gates.py`** | 10:04 | **不入库**（本报告不需） | 与已入库 `v2/refs/D25a-amendment1-baseline-and-gates.md` 同批的脚本，属 D2.5a 遗留；若 D2.5a 结算需要，应在其自身修正件里入库，不借 D2.7 的提交搭车 |

> **判定规则（写给 report-author）**：入库白名单 = **A 类** + `reports/CYCLE-21-20261024.md`；**B/C 类一律 `git add` 前用显式 pathspec 挡掉**，不得 `git add -A`。

### 4.3 专项溯源：`code/frontend/sample/dialogue_d27_{C,B}/` 是谁、什么时点、属不属于本轮

> 触发：team-leader 16:36 转来 case-curator 的移交线索（其判断为「非本轮 §4 渲染链产物」）。**我实证的结论与它不同**：这两目录**确实属本轮 D2.7**，只是不属于「本轮走 `/tmp` + 符号链接的那条正式渲染链」。证据如下，全部可原地重放。

**(1) 时点与体积**

```bash
stat -c '%n | %y' code/frontend/sample/dialogue_d27_C code/frontend/sample/dialogue_d27_B
# code/frontend/sample/dialogue_d27_C | 2026-10-24 16:30:28.069625963 +0800
# code/frontend/sample/dialogue_d27_B | 2026-10-24 16:30:29.002647864 +0800
find code/frontend/sample/dialogue_d27_C code/frontend/sample/dialogue_d27_B -type f -printf '%p | %TY-%Tm-%Td %TH:%TM:%TS | %s\n'
# …/dialogue_d27_C/threads.json | 2026-10-24 16:30:28.2256296250 | 2153042
# …/dialogue_d27_B/threads.json | 2026-10-24 16:30:29.1536514090 | 2093912
```
两目录各只有 1 个文件 `threads.json`，**无 HTML/无截图**（截图产物在 `v2/evidence/d27_shots/`，mtime 16:31）。

**(2) 生成器与数据来源（决定性证据：`source` 里带 run sha256）**

```bash
python3 -c "import json;d=json.load(open('code/frontend/sample/dialogue_d27_C/threads.json'));print(d['generated_by'],d['generator_sha256']);print(json.dumps(d['source'],ensure_ascii=False))"
# frontend/tools/gen_threads.py 1ab81778464d8bcd5f358e75adbe44159d0a62ec3da8e8af106e93e1a004776e
# {"run_label":"d27_C","run_sha256":"1fbb9ef5161fd07aa68fcc9fc4038f104ff18b56383a2fc6b31bb3cb5486a188",
#  "run_bytes":56531099,"events_total_in_log":116308,"round_range":[0,59],
#  "meta_json":{"model":"DeepSeek-Flash","seed":42,"n":16,"rounds":60,
#               "code_sha":"f2bf606bf5f6c362a7d4d34b9177f3210d43aabf","llm_cached_ratio":0.4951,
#               "started_at":"2026-10-24T14:04:39+08:00","finished_at":"2026-10-24T14:59:23+08:00"} …}
（d27_B 同结构：run_sha256 = 87e233c421ae… ，code_sha = c7498505… ，started/finished = 15:32:28 / 16:23:24）
```
- `d27_C/threads.json` 的 `source.run_sha256` = **`1fbb9ef5…`** = `v2/evidence/run_d27_C_n16r60_seed42/run.jsonl` 的实测 sha256（§3.2），`code_sha=f2bf606`；
- `d27_B/threads.json` 的 `source.run_sha256` = **`87e233c4…`** = B 臂 `meta.run_sha256`（§3.3），`code_sha=c749850`；
- 统计量与判据件自洽：C `messages 510 / threads 169`、B `messages 502 / threads 170`，与 `d27_gate_verification.md` §2/§4 完全一致。

**(3) 归属判定**

| 问题 | 实证答案 |
|---|---|
| 谁产生 | **无法由文件证明操作者身份**（`threads.json` 不记 user/host。仓内无 author 元数据）——只能说"用 `code/frontend/tools/gen_threads.py` 生成"。**不猜测、不写成某个人**。 |
| 哪个时点 | `16:30:28.07`（C）/ `16:30:29.00`（B），**早于**截图服务首次渲染 `16:32:41`，**晚于** `d27_gate_verification.md` 首版 `16:30:27` |
| 是否 D2.7 跑批残留 | **不是跑批残留**。跑批目录 `run_d27_C_…`（14:04–14:59）/ `run_d27_B_…`（15:32–16:23）在别处；这两目录是**跑批之后的派生件** |
| 是否"旧渲染链残留" | **不是旧链**。`run_sha256` 指向**本轮**两个 run，且 `generator_sha256` 与现行 `gen_threads.py` 一致 |
| 属不属于本轮 §4 | **属本轮，但走的是"直调写 `code/`"的旁路**：`gen_threads.py` 支持 `--out`，本次被指定为 `code/frontend/sample/dialogue_d27_*`。官方渲染链（`tools/metrics/render_shots.py`）走 `/tmp` + 符号链接，**不写 `code/`**。⇒ case-curator 说"非本轮渲染链产物"**在其自身口径下成立**（不是它那条链的产物），但**不能说"与本轮无关"**：它绑的就是本轮两臂的 run sha。 |

**(4) 处置结论（明确、可执行）**

- **不入库**（`git add -A` 会把 2 个 2 MB 的 `threads.json` 塞进报告提交，污染 `code_sha` 口径，且报告族纪律禁止 `code/` 下建影子产物）。
- **不删除、不移动**（不改他人产物、不留"证据消失"口实；它们与 `d27_shots` 的 sha 绑定关系本身就是可核的旁证）。
- 报告 §1.4「未提交产物」如实登记一句：**`code/frontend/sample/dialogue_d27_{C,B}/threads.json` = `gen_threads.py` 于 16:30:28/29 对 run sha `1fbb9ef5…`/`87e233c4…` 生成的中间件，写在 `code/` 下 ⇒ 不入库；理由：`code/` 影子产物污染 `code_sha` 口径 + 报告族纪律**。

---

## 5. 报告页首可用的「sha 分层」候选值（照 CYCLE-19/20 体例）

> CYCLE-20 页首体例（`reports/CYCLE-20-20261024.md` 第 9–17 行）：① **分析基准**（字面量，可直接 `git cat-file -t` 复核）② **首笔交付** ③ **修正提交** ④ **sha 回填提交**；②③④ 因"自指不可能"一律用**取法回查** + **预期父提交**。

| 层 | 候选值 / 取法 | 复核命令 | 说明 |
|---|---|---|---|
| **① 分析基准 sha** | **`dc02e06da5f0d17f251465bc92cab11b2e9a22e1`**（短 `dc02e06`，`2026-10-24 16:29:35`）**＋ 树状态指纹** `251a7895cbddc8b46cafa779fc658d73be7e9b2ac6d8664d9e0d2fcc488450de` | `git cat-file -t dc02e06` → `commit`；`git status --porcelain \| sha256sum` | 本件全部读数取自此刻此树；**必须双写**，因为本树当时含 2 个 `M`（`d27_C_baseline_readings.md` 已改、`d3_noiseband_bootstrap.json` 历史脏项）——只写 HEAD 会让人误以为"库内即所读" |
| **② 首笔交付提交** | **取法回查**：`git log -1 --format=%H -- reports/CYCLE-21-20261024.md`；**预期父**：若 D2.7 证据先单独入库，则父 = 该证据提交（取法 `git log -1 --format=%H -- v2/evidence/d27_gate_verification.md`）；若证据与报告同笔入库，则父 = ① `dc02e06` | `git rev-parse <②>^` 对照上述预期 | 报告 + 截图 + 证据入库的那一笔；**两种父关系都要在页首写清走的是哪一种**，复核方才有得对 |
| **③ 修正提交** | 若独立复核提出修正 → 该修正所在提交，**取法回查**：`git log -1 --format=%H -- reports/CYCLE-21-20261024.md`（取到的是最后一次改动该文件的提交）；**预期父 = ②**；一次通过则写 **null**（不是空值） | 同上 | 只允许改字面表述与 sha 回填，**不得动数字与判定档** |
| **④ sha 回填提交** | 把 ②③ 字面 sha 写进页首的提交；**预期父 = ③（无③则 ②）**；同样"取法回查" | `git log -1 --format=%H -- reports/CYCLE-21-20261024.md` 取其**第二新**一条：`git log --format=%H -2 -- reports/CYCLE-21-20261024.md \| tail -1` | 仅回填字面 sha，不改其它内容 |

**④ 的补充取法（比 CYCLE-20 更稳，建议采用）**：

```bash
git log --format='%H %ad %s' --date=iso -- reports/CYCLE-21-20261024.md   # 该文件的全部入库提交，按时间倒序
```
页首只要声明「第 N 条 = ②、第 N-1 条 = ③ …」，就不必靠"第几新"数法，复核方按同一命令即可复现。

**禁止**：把 ② 的 sha 写进报告正文自身（自指不可能），也不要用"约等于/大概/如上"代替取法。

---

## 6. 追加项：区间内「提交信息所述读数 与 后续更正件不一致」的提交

> team-leader 16:33 追加要求。判定口径：**提交信息里写死的数字，被区间内更晚的件或工作树中的更正件推翻**。结论：**只此 1 条**（其余 10 条的提交信息未被推翻；`21b6738` 的"差 0.61pp"在**同一时点**由 `fa58a93` 更正，但其更正件在区间内，故 `21b6738` 也算**部分作废**——见下表第 1 行）。

| 提交 | 提交信息里的表述 | 被谁推翻 | 更正后 | 影响 |
|---|---|---|---|---|
| **`dc02e06`**（`result(d27)`） | 「Q2 破（`L-7 20.59→28.49`，**+7.90pp**）、T 闸破（`len_p50_excl 40→26`，**−35%**）、Q1 `4.12→4.18`、Q3 `66.28→66.87`」——其中 C 列四值全部来自**污染基线** | `v2/evidence/d27_C_baseline_readings.md`（工作树 M，16:28）+ `v2/evidence/d27_gate_verification.md` §3（16:30）+ `v2/evidence/d27_harvest/d27_gates.json`(`appendix_legacy_baseline`) | C 现算 = Q1 **4.31** / Q2 **25.49** / Q3 **63.34** / T **41.0** ⇒ Q2 = **+2.9959pp（擦线过，余量 0.0041pp）**、T = **−36.59%**、Q1 = **−0.13pp**、Q3 = **+3.5244pp** | **单闸判定词会反转**（Q2：无效→擦线过；Q3：`d27_gates.json` 记 `pass=false`）**但总判定「作废」不变**（T 闸两侧都破 + P 未达 +2.88pp<+5pp）。⇒ **提交信息属"更正前版本"，报告 §一 加注时必须原样引用本表，不得把 +7.90pp / −35% 当最终值** |
| `21b6738`（`result(d25a)`） | 「P 差 **0.61pp**（+14.39 vs +15）」「Q2 L-7 +8.91pp」 | 同区间 `fa58a93`（`correct(d25a-2)`，14:30:53）+ `5f73676`（runbook §3.119） | 全量口径 30.77→37.17（**+6.40pp**）⇒ 实差 **8.60pp**；"差 0.61pp"表述**作废** | 判定不变（仍「无效」），但**"差点就过"的叙事必须删**；这是 §一 可引用的"分母口径事故"活教材 |

> 另外两条**件内不一致**（非提交信息，但报告若引用会踩到，故一并列出）：

0. **时点更新（16:43 由 leader 告知并已由我复核）**：`d27_gate_verification.md` **16:39:03 版**（23,131 B，sha256 `8cf511d1…f575`）**已自行把 Q3 更正为 ❌**（该件 §2.1 原话：「本件此前误记 ✅，已更正」；`grep -n Q3` 实测 `:58` 行已是 `❌（内容漂移，超 2.0pp 一倍多）`，`:68` 标题即「Q3 裁决：❌」）。⇒ **下列第 1 条冲突记录描述的是 16:33 版的历史状态，已被作者自解，不是现行状态**；报告引用该件时**不得**再写「该件把 Q3 记为 ✅」。（我保留该条仅为留痕，不据此自裁；leader 已初裁 Q3=FAIL 并转 verifier。）
1. _（历史状态，16:33 版）_ `d27_gate_verification.md` §2 把 Q3 判为 **✅（`+3.53pp`，写"降≤2pp"）**，而同一基线的 `v2/evidence/d27_harvest/d27_gates.json` 里 `Q3.pass = false`（`rule: 升<=2.0pp`，实测 `+3.5244pp`）；`v2/refs/D27-amendment1-merge-duplicate-prereg.md:34` 的规则原文是「`F-2′` 降 ≤2.0pp ⇒ 否则**无效（内容漂移）**」⇒ **两处判词冲突，须 verifier 收口**。本件不裁决，只标注。
2. `d27_C_baseline_readings.md` 的**入库版**（`4d619b5`）本身即污染版；工作树更正版尚未入库 ⇒ **同一路径存在两个互相矛盾的"官方读数"**，这正是它必须随本报告入库的原因。

---

## 7. 审计发现（不入判定，但报告与提交都必须知道）

### 7.1 B 臂 run 目录是「混装目录」：`rc=9` 不是本批的退出码

```bash
stat -c '%n | %y | %s' .worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/*
# code_id_start.txt   | 14:59:38 | 760      ← 14:59 被拒尝试
# frozen_diff_start.txt| 14:59:38 | 0
# git_status_start.txt | 14:59:38 | 163
# host.log             | 14:59:38 | 1200
# run_batch.end        | 14:59:38 | 282      finished_at=2026-10-24T14:59:38+08:00  rc=9
# run_batch.log        | 14:59:38 | 235      [preflight] FAIL exit=9 reasons=concurrency:run_batch=1
# run_batch.rc         | 14:59:38 | 2        ⇒ 9
# meta.json            | 16:23:25 | 4317     started_at=15:32:28 finished_at=16:23:24
# run.jsonl            | 16:23:22 | 56148529
```
⇒ 目录内 **8 个控制件是 14:59:38 那次被并发闸拒绝的尝试**，**只有 `meta.json` / `run.jsonl` 属真批（15:32–16:23）**。
`d27_result.md` §0 与 `d27_gate_verification.md` §1 已如实声明此事并按六项等价证据收批（本件复核其 6 项全部成立：`generated_after_run=true`、`115545=115545`、`code_sha=code_sha_end=c749850`、`duration 3056s` 自洽、`git_dirty_code_files=[]`、`llm_calls 2869` 且 `degraded_calls=0`/`fallback_detected=false`）。
**报告纪律**：可以写「按等价清单判为正常结束」，**不得写 `rc=0`**，也不得写「rc=9 失败」——两者都与事实不符。

### 7.2 治疗臂的代码改动**不在 master**（§一 若漏写，等于骗人）

```bash
git log --oneline a0fb1eb..dc02e06 -- code/                 # （空）
git merge-base --is-ancestor 4123628 dc02e06; echo $?        # 1  ⇒ 不是祖先
git merge-base --is-ancestor c749850 dc02e06; echo $?        # 1  ⇒ 不是祖先
grep -n '旁白' code/life/agent.py                            # 1453/1478 仍是"不要用括号…写…旁白"（旧版）
```
⇒ `4123628`（`feat(D2.7)`，改 `code/life/agent.py` 2 行）+ `c749850`（mock 证据）**只存在于 `feat/d27-narration` 分支**，
**从未合入 master**。所以：
- **C 臂**（主树 `f2bf606`）= 旧提示词（`paren 0.00%`）；
- **B 臂**（worktree `c749850`）= 新提示词（`paren 100%`）；
- 这与 `f8a9113` 提交信息「`code_sha f2bf606`（主树仅文档）」完全一致，**不是错误，但必须写清**：本周期 master 上**没有任何代码变更**，"治疗"只在一棵未被合并的工作树上跑过。

### 7.3 本件自身的边界

- 只读：本件除 `v2/evidence/cycle21_recon/` 下两个自有交付文件外**未写任何路径**；未跑批、未调 LLM、未改 `code/`。
- `python3 -c` 仅用于读 JSON（未 import 项目模块，不复现时不会在 `code/` 下产生 `__pycache__`）。
- `d27_gate_verification.md` 在本次取数窗口内**仍在被作者修改**（16:30:27 → 16:33:16）；本件记录的是**16:33:16 版**的 sha256，报告入库前必须重新 `sha256sum` 冻结。
- 未能取到的项：**无**（B 臂 `meta.json`/`run.jsonl` 在主树之外，但通过 `.worktrees/…` 绝对路径可读，已给 sha256）。唯一"取不到"的是**B 臂真批的退出码**——目录内 `run_batch.rc=9` 属 14:59 残留，**真批未写 `rc`**，这是事实缺口，不是本次遗漏。

---

## 8. 收尾两件（按 team-leader 16:40 指令补）

### 8.1 两份"活文件"的最终 sha256（16:40:44 复测）

| 路径 | 观测到的版本（时点 / 字节 / sha256） | **最终 sha256（16:40:44）** |
|---|---|---|
| `v2/evidence/d27_gate_verification.md` | ① `16:30:27` / 10,926 B / `d23892f26194d7a5e670eeca43e520011453e494e750f222ada300b1eadeb8aa`<br>② `16:33:16` / 13,441 B / `b1f1f9a8d57c02c44168afee1cb0f72b4b957b735b3ab3144ea7177b2b983c78`<br>③ `16:39:03` / 23,131 B / **`8cf511d15c16cadbdeb2745e7996db249a98fa99e3f105a79e9baf3be16ef575`** | **`8cf511d15c16cadbdeb2745e7996db249a98fa99e3f105a79e9baf3be16ef575`**（= ③，`mtime 2026-10-24 16:39:03`） |
| `v2/evidence/d27_gate_prediction_prereg.md` | 仅一版：`16:13:20` / 6,003 B | **`bf1a657623a468222319f633421b79e967bb447d06a1e8c8fc6e14196f509f6a`**（`mtime 2026-10-24 16:13:20`，自落笔后未变） |

复测命令（可原地重放）：

```bash
sha256sum v2/evidence/d27_gate_verification.md v2/evidence/d27_gate_prediction_prereg.md
# 8cf511d15c16cadbdeb2745e7996db249a98fa99e3f105a79e9baf3be16ef575  v2/evidence/d27_gate_verification.md
# bf1a657623a468222319f633421b79e967bb447d06a1e8c8fc6e14196f509f6a  v2/evidence/d27_gate_prediction_prereg.md
stat -c '%n | %y | %s' v2/evidence/d27_gate_verification.md v2/evidence/d27_gate_prediction_prereg.md
```

> ✅ 16:43 复核确认：现行版即 16:39:03 版（23,131 B / `8cf511d1…f575`），且**该版已自行把 Q3 更正为 ❌**（§2.1「本件此前误记 ✅，已更正」）⇒ 报告引用写「C21-F 提交内含版本，23,131 B，sha 提交时回填」，**不要**写「该件把 Q3 记为 ✅」。
>
> ⚠ **以 C21-F 提交内含版本为准**：`d27_gate_verification.md` 在 16:30 / 16:33 / 16:39 **被改了三次**（10,926 → 13,441 → 23,131 B），
> 本件给出的 `8cf511d1…` 只是**16:40:44 的时点值**。报告引用时**不得**写死本值，必须写「以 C21-F 提交内含版本为准」，
> 并在 C21-F 提交后用 `git cat-file -p <blob> | sha256sum` 回填真值（§3 的三件套取法）。若提交前它又变了，**以提交时刻重新 `sha256sum` 为准，且须在报告 §二 注明"验收件在提交前仍在增补"**。

### 8.2 入库白名单（可直接照抄的逐行实路径，禁通配）

> **禁止**使用 `v2/evidence/d27_harvest/`、`v2/evidence/d27_shots/` 这类目录通配：`run_d27_C` 内的 `run.jsonl`/`.log` 会被 `.gitignore` 静默排除，
> 而 `d27_shots/*.log`（`render_wrap.log`）却因 `!.gitignore:78 v2/evidence/**/shots/**/*.log` 被**放行**——通配会让"进没进库"变成运气。故**逐条列实路径**。
> 下列 43 条已逐条 `git check-ignore` 实测**无一被忽略**（`git check-ignore -q <f>` 全部返回非 0）。

```bash
git commit -- \
  reports/CYCLE-21-20261024.md \
  v2/evidence/cycle21_recon/commit_window.md \
  v2/evidence/cycle21_recon/commit_window.json \
  v2/evidence/d27_C_baseline_readings.md \
  v2/evidence/d27_gate_prediction_prereg.md \
  v2/evidence/d27_gate_verification.md \
  v2/evidence/run_d27_C_n16r60_seed42/code_id_start.txt \
  v2/evidence/run_d27_C_n16r60_seed42/frozen_diff_start.txt \
  v2/evidence/run_d27_C_n16r60_seed42/git_status_start.txt \
  v2/evidence/run_d27_C_n16r60_seed42/meta.json \
  v2/evidence/run_d27_C_n16r60_seed42/run_batch.end \
  v2/evidence/run_d27_C_n16r60_seed42/run_batch.rc \
  v2/evidence/d27_shots/d27-B-chat-multi-87e233c4.png \
  v2/evidence/d27_shots/d27-B-thread-focus-87e233c4.png \
  v2/evidence/d27_shots/d27-C-thread-focus-1fbb9ef5.png \
  v2/evidence/d27_shots/render_d27_shots.sh \
  v2/evidence/d27_shots/render_wrap.log \
  v2/evidence/d27_harvest/d12c_c_b.json \
  v2/evidence/d27_harvest/d27_gates.json \
  v2/evidence/d27_harvest/d27_gates.py \
  v2/evidence/d27_harvest/d27_metrics_c_b.json \
  v2/evidence/d27_harvest/d27_metrics.py \
  v2/evidence/d27_harvest/dm_B.json \
  v2/evidence/d27_harvest/dm_B.md \
  v2/evidence/d27_harvest/dm_C.json \
  v2/evidence/d27_harvest/dm_C.md \
  v2/evidence/d27_harvest/HANDOFF-to-gate.md \
  v2/evidence/d27_harvest/l15_c_b.json \
  v2/evidence/d27_harvest/p1_count_c_b.json \
  v2/evidence/d27_harvest/p1_count.py \
  v2/evidence/d27_harvest/shape_B.json \
  v2/evidence/d27_harvest/shape_C.json \
  v2/evidence/d27_harvest/_selftest_c_vs_c/d12c_c_b.json \
  v2/evidence/d27_harvest/_selftest_c_vs_c/d27_gates.json \
  v2/evidence/d27_harvest/_selftest_c_vs_c/d27_metrics_c_b.json \
  v2/evidence/d27_harvest/_selftest_c_vs_c/dm_B.json \
  v2/evidence/d27_harvest/_selftest_c_vs_c/dm_B.md \
  v2/evidence/d27_harvest/_selftest_c_vs_c/dm_C.json \
  v2/evidence/d27_harvest/_selftest_c_vs_c/dm_C.md \
  v2/evidence/d27_harvest/_selftest_c_vs_c/l15_c_b.json \
  v2/evidence/d27_harvest/_selftest_c_vs_c/p1_count_c_b.json \
  v2/evidence/d27_harvest/_selftest_c_vs_c/shape_B.json \
  v2/evidence/d27_harvest/_selftest_c_vs_c/shape_C.json
```
（上面 **43 条**路径 = harvest 26 件 + shots 5 件 + run_d27_C 6 件 + 证据 md 3 件（`d27_C_baseline_readings.md`/`d27_gate_prediction_prereg.md`/`d27_gate_verification.md`）+ 报告与审计件 3 件（`reports/CYCLE-21-20261024.md`、`commit_window.md`、`commit_window.json`）；
**不含**：`d3_noiseband_bootstrap.json`、`d25a_gates.py`、`code/frontend/sample/dialogue_d27_{C,B}/`、以及全部历史 `??` 项——理由见 §4。）

**提交后自检三条（照抄执行）**：

```bash
git show --stat --name-only HEAD | wc -l                      # 与预期文件数对账
git show --name-only HEAD | grep -E 'dialogue_d27_[CB]|d3_noiseband|run\.jsonl'   # 应为空（= 未裹带）
git cat-file -p HEAD:v2/evidence/d27_gate_verification.md | sha256sum             # 真值回填报告 §二
```

### 8.3 与报告 §一/§2.0 的对接（leader 四条确认的落点）

| leader 确认项 | 已落点 |
|---|---|
| ① 零代码变更须为 §一 第一硬事实，§2.0 写「本周期没有可归因于 master 的效果变化」，禁写"本周期实现了旁白放开" | §2.1 + §7.2（含 `merge-base --is-ancestor` exit=1 与 master 旧文本 `agent.py:1453/1478` 两证据） |
| ② B 臂 rc 缺口表述批准（等价清单正常结束；真批未写 rc 属事实缺口；禁 rc=0 / 禁 rc=9 失败；须点明 rc=9/end/log 是 14:59:38 preflight 残留） | §7.1（含逐文件 mtime 表） |
| ③ Q3 冲突**保留记录、不改判词**（leader 已初裁 FAIL，转 verifier） | §6 末「件内不一致」第 1 条，原文保留冲突双方 + 预登记 ref:34 原文；**本件不含任何自裁** |
| ④ `d3_noiseband_bootstrap.json` 不裹带、`dialogue_d27_{C,B}` 不入库不删不移 | §4.1 / §4.3 / §8.2 白名单（两者均不在清单内） |
