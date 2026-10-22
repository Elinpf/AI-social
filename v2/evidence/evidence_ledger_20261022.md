# 证据台账 · 2026-10-22 · 缺 meta.json 的真 LLM 批处置登记

> 编写：evidence-auditor（独立核验者）｜初版取数 commit：`84ed6b1`（主树 master）｜**勘误复核 commit：`3ed7eb1`**｜世界线两臂相关分支 `feat/world-line-c1@af1dffc`
> 修订记录：**2026-10-22 22:2x 勘误（T-fix-ledger）**——修正初版两条关于 worldline worktree 的**错误否定断言**（详见 §0.1 勘误），并补一条「10 批逐批凭据清点」新事实（§5.1）。除此之外读数、结论、判据均未改动。
> 性质：**只读审计台账**。本文件不改 `code/life|orchestration|config|engine`，不跑任何批次，不为任何批次生成 meta 字段，不 commit（由报告与交付专员统一提交）。
> 口径纪律：**宁可登记作废，不补不实字段**。凡本文件写「可重建」，均附可复算命令；凡未复算的数字，标 `UNVERIFIED`。

---

## 0. 判定摘要（先读这四条）

1. **5 个批次的"读数级证据"全部可以客观重建**（provider/model/events/seed/n/rounds/token 成本/开关取值），**但原版 `meta.json` 永久缺失**，其中 **`assertions.code_unchanged_during_run` 一条对 3 个批次不可重建**（起跑时未留 `git status --porcelain` 快照）。→ 按团队纪律「缺 meta 一律 `REJECTED`/`probe`」，**这 5 批当前状态仍是 probe，不得被报告当作任何效果结论的锚点**，除非执行第 4 节的重建方案。
2. **可忠实重建（有现成 run-time 代码环境）**：`run_a5_real`、`run_a1budget_real`、`run_d12a_real` —— 对应 worktree 仍存在且 HEAD 恰为跑批时的 sha（`.worktrees/a2-prefer@51cdb07`、`.worktrees/d12-detail@a6ae5e5`）。重建出来的 meta 才不会伪造 `code_sha`。
3. **代码环境已在，不阻塞**：`run_worldline_c1_ctrl`、`run_worldline_c1_a1` 的跑批 worktree **仍然存在**——`.worktrees/worldline-c1-n16r84` @ `af1dffc` `[feat/world-line-c1]`，其 `HEAD` 全 40 位 `af1dffc61040adc97c828b4927ac3935dbef2d1b` 与两臂 `host.log` 记录的 `code_sha` **逐位一致** ⇒ **补 meta 的代码环境不阻塞**（可直接在该 worktree 内重建，无需新建）。⚠ **本条已勘误**：初版此处误写「已被删除（`git worktree list` 无此项）」，属**未复算就下的否定断言**，详见 §0.1。
4. **⚠ 漏报（本台账新增，任务书未含）**：除任务书列的 5 批外，**另有 5 个同样是真 LLM、同样无 meta 的批次**（`run_a1wording_n16r42`、`run_g1_b0_n16r60`、`run_l7struct_on_n16r60`、`run_l7v2_on_n16r60`、`run_dr_round1_arm-ctrl_n16r60`，均由 `obs llm-cost` 亲跑验真，见 §5）。这 5 个批次**无 switch_proof / 无 host.log**，`code_sha`、`started_at`、开关取值**无法重建**，只能登记为「只读数据源、永久 probe」。因此「缺 meta 的真 LLM 批 = 5 个」这一表述**不成立，实际为 10 个**（= 任务书 5 个 + 本台账补登 5 个；另有 2 个已按命名作废的 `run_d12a_*_seed7_INVALID_*`、1 个 `_VOID`、1 个 `_ABORTED_`、2 个 34/223 行的小样本不计）。

> **勘误（2026-10-22 22:12，经 report-writer 交叉核对）**：本台账初稿此处曾写「≥10 / 剩余 11 个」，属**本审计数错 1 个**（把 `run_baseline_n4r2_20261020T220207` 与 `run_d4_P2_n16r12` 两个小样本之一重复计入）。**正确计数为 10**，复核命令见 §5 末。以 10 为准，不写 11、也不用「≥10」含糊带过。

### 0.1 勘误（2026-10-22 22:2x，T-fix-ledger）：worldline worktree **未删**

**错在哪**：初版 §0 第 3 条与 §2.4「缺什么」行写「worktree `.worktrees/worldline-c1-n16r84` **已被删除**（`git worktree list` 无此项）」。实况是**它存在**。

**错因（不掩过去）**：我初版执行的是 `git worktree list 2>&1 | head`——`head` 默认只输出 10 行，而该 worktree 恰好是**第 11 行**，被管道截断；我随后把"截断后的输出里没有"当成了"不存在"，**属于未复算就下的否定断言**（正是我要求别人别犯的错）。该错误由 team-leader 与 state-surveyor 在 22:22 交叉核实后指出。

**复跑（仓库根执行，无 `head`、无 `grep` 过滤，完整输出）**：
```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment   # 必须仓库根，不能在子目录或 worktree 内
git worktree list
```
```
/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment                                     3ed7eb1 [master]
/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/a2-prefer                51cdb07 [feat/d2-prefer]
/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/a2-trigger               913ac4d (detached HEAD)
/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d12-detail               a6ae5e5 [feat/d12-detail]
/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/feat-world-event-dose    6602b77 [feat/world-event-dose]
/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/g1-b0-n16r60             d9391a3 (detached HEAD)
/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/l7v2-dequp-n16r60        a851a8f [feat/l7-dequp-v2]
/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/pi_t362                  1ffd7eb (detached HEAD)
/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/t298head                 e959dc3 [t298head]
/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/t367                     eed664e [t367]
/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/worldline-c1-n16r84      af1dffc [feat/world-line-c1]
```
（共 **11** 行；初版用 `head` 只看到前 10 行 ⇒ 漏掉最后一行。）

**追加三重复核**：
```bash
git worktree list | wc -l                                          # → 11
git worktree list | grep worldline                                 # → .worktrees/worldline-c1-n16r84  af1dffc [feat/world-line-c1]
ls .worktrees/worldline-c1-n16r84                                  # → code docs experiments glossary Makefile …（目录实在）
git -C .worktrees/worldline-c1-n16r84 rev-parse HEAD               # → af1dffc61040adc97c828b4927ac3935dbef2d1b
git -C .worktrees/worldline-c1-n16r84 rev-parse --abbrev-ref HEAD  # → feat/world-line-c1
```

**结论更正**：`.worktrees/worldline-c1-n16r84` **存在**，HEAD = `af1dffc61040adc97c828b4927ac3935dbef2d1b`，与两臂 `host.log` 的 `code_sha=af1dffc61040adc97c828b4927ac3935dbef2d1b` **逐位一致** ⇒ **世界线两臂补 meta 的代码环境不阻塞**（前提仍见 §4-B 那两条限制：ctrl 无起跑快照 ⇒ `code_unchanged_during_run` 只能 `null`；a1 有快照 ⇒ 可算 `true`）。

---

## 1. 主台账（任务书指定的 5 批）

| # | 批次目录 | 现有产物 | meta 可否重建 | 处置 | 关键依据命令 |
|---|---|---|---|---|---|
| 1 | `v2/evidence/run_a5_real_n16r42_seed42` | `run.jsonl`(30.3MB/62,027 行, sha256 `aa6edc35…`)、`switch_proof.txt` | **部分可重建**：日志派生字段 + `code_sha`（worktree 在）可；`code_unchanged_during_run` **不可**（无起跑快照）；`duration_sec` 只能由 mtime 推（±20s） | 不重建则登记 **probe**；若重建必须按 §4-A 在 `.worktrees/a2-prefer` 内执行，并附 `rebuilt_at` 说明 | §2.1 |
| 2 | `v2/evidence/run_a1budget_real_n16r42_seed42` | `run.jsonl`(30.4MB/62,365 行, `0bc80cd2…`)、`switch_proof.txt` | **部分可重建**（同上，同一 worktree） | 同上 | §2.2 |
| 3 | `v2/evidence/run_d12a_real_n16r24_seed42` | `run.jsonl`(17.1MB/33,824 行, `64f9da4b…`)、`switch_proof.txt`（含 `prompt_fn_sha256`/`detail_line_len_on`） | **部分可重建**（`.worktrees/d12-detail@a6ae5e5` 在） | 同上 | §2.3 |
| 4 | `v2/evidence/run_worldline_c1_ctrl_n16r84_seed42` | `run.jsonl`(91.4MB/194,057 行, `4c840b5b…`)、`host.log`（含 `[life]` 收尾行）、`env_dump.txt`、`launch_evidence.txt`、`launch.sh` | **部分可重建**：`code_sha`/`started_at`/`duration_sec` 有硬证据；`code_unchanged_during_run` 仅**弱证据**（`env_dump` 闸门 3 记录，非 emit_run_meta 口径） | 不重建则登记 **probe**；环境已在（`.worktrees/worldline-c1-n16r84` @ `af1dffc`），可直接按 §4-B 原地重建 | §2.4 |
| 5 | `v2/evidence/run_worldline_c1_a1_n16r84_seed42` | 同上 + `git_status_start.txt`（4 行 untracked）、`prompt_diff_proof.txt`、`stats_and_replay_check_partial.txt`、`window_probe_partial.txt` | **最完整可重建**：起跑 porcelain 快照**在库** ⇒ `code_unchanged_during_run` 可算；`code_sha`/`started_at`/`duration_sec`/开关 PROC-ENV 自证齐全 | 环境已在，可直接按 §4-B 原地重建（起跑快照在库 ⇒ `code_unchanged_during_run` 可算 true）；或不重建则降级为 probe | §2.5 |

> 一句话对照：`run_a1wording`（§5）连 `switch_proof.txt` 都没有，**只有 `run.jsonl`** —— 所以 §1 的 5 批虽然缺 meta，取证条件已明显优于仓库里更早的那批。

---

## 2. 逐批核查（数字均为本审计独立复算，命令可复算）

### 2.1 `run_a5_real_n16r42_seed42`

| 项 | 复算值 |
|---|---|
| run.jsonl | 30,303,995 B；62,027 行；sha256 `aa6edc351cefdd99…`（与 `d2_a5_real_three_arm.md` 记的 `aa6edc35` 一致） |
| seed / n / rounds | `WORLD_INIT.payload.seed=42`；`AGENT_BORN=16`；`round 0..41` 共 42 轮，**连续无跳号** |
| LLM 真跑 | `calls=2705`，`by_provider={"openai_compat":2705}`，`model=DeepSeek-Flash`，`cached=1406`，`degraded=0`；`tokens_in=285,864 / out=213,348 / total=499,212` |
| purposes | dialogue 523 / importance 1523 / judge 497 / negotiation 34 / plan 16 / reflect 112 |
| 代码身份 | `WORLD_INIT.config_components` 12 个 config 文件 **12/12 与 commit `51cdb071…` 的 `code/config` 树一致**（按 `engine.version.component_digests` 同口径复算） |
| 开关 | `switch_proof.txt`：`HITT_LLM_PROVIDER=openai_compat`、`HITT_REPLY_BUDGET=1`、`HITT_INIT_PREFER_UNREPLIED=1`、`params seed=42 n=16 rounds=42 max_turns=6 …`；`code_sha=51cdb07`、`branch=feat/d2-prefer`（**7 位短 sha，自述式**，非进程内自证） |
| 时间 | `started_at=2026-10-22T17:07:25+08:00`（switch_proof）；run.jsonl mtime `17:44:03` ⇒ 墙钟 **2198 s**（无 `[life] seconds` 精确值） |
| 跑批期间 code/ 提交 | 窗口内 `git log --all --since … -- code/life code/orchestration code/config code/engine` → **0 条** |
| **缺什么** | 无 `meta.json`；**无起跑 `git status --porcelain` 快照**；无 host.log ⇒ `duration_sec` 只能 mtime 推导 |

```bash
# 复算命令（仓库根执行）
python3 -m obs llm-cost --log ../v2/evidence/run_a5_real_n16r42_seed42/run.jsonl --require-provider openai_compat   # 在 code/ 下
git log --all --since="2026-10-22T17:07:25+08:00" --until="2026-10-22T17:44:03+08:00" --format='%h %ci %s' -- code/life code/orchestration code/config code/engine
```

### 2.2 `run_a1budget_real_n16r42_seed42`

| 项 | 复算值 |
|---|---|
| run.jsonl | 30,435,509 B；62,365 行；sha256 `0bc80cd23fbc235e…`（与 `d2_a5_real_three_arm.md` 的 `0bc80cd2` 一致） |
| seed / n / rounds | 42 / 16（`AGENT_BORN`）/ `round 0..41`（42 轮连续） |
| LLM 真跑 | `calls=2665`，provider 全 `openai_compat`，`cached=1408`，`degraded=0`；`tokens_in=269,382 / out=211,199 / total=480,581` |
| purposes | dialogue **483**（其余与 a5 相同：importance 1523 / judge 497 / …） |
| 代码身份 | 12/12 与 `51cdb071…` 一致 |
| 开关 | `HITT_REPLY_BUDGET=1`、`HITT_INIT_PREFER_UNREPLIED=0`（唯一变量相对 a5）、`code_sha=51cdb07`、`branch=feat/d2-prefer` |
| 时间 | `started_at=18:04:18`；mtime `18:41:15` ⇒ 墙钟 **2217 s** |
| 跑批期间 code/ 提交 | 窗口内 **1 条**：`c01f6dd`（18:20:01，`fix(life): R18 睡眠—固化链路…`）。**归属分支 = master / feat/d12-detail / feat/r19-*，不含 `feat/d2-prefer`** ⇒ 该提交未进入跑批所用 worktree（`.worktrees/a2-prefer@51cdb07`）；但因无起跑 porcelain 快照，**不能用工具口径证明工作树未被改动**，也无法排除未提交的临时编辑 |
| **缺什么** | 同 2.1；外加一条纪律观察（上条） |

> 审计意见：`c01f6dd` 落在 master 而非跑批分支，**不判违规**，但必须在报告里写明「跑批窗口内主树 code/life 有提交」，并注明「跑批走 worktree、未受影响」这一免责依据即可，不要用"跑批期间无 code 改动"这类绝对表述。

### 2.3 `run_d12a_real_n16r24_seed42`

| 项 | 复算值 |
|---|---|
| run.jsonl | 17,126,977 B；33,824 行；sha256 `64f9da4bb264c2fc…`（与 `d12a_real_result.md` 的 `64f9da4b` 一致） |
| seed / n / rounds | 42 / 16 / `round 0..23`（24 轮连续） |
| LLM 真跑 | `calls=2252`，provider 全 `openai_compat`，`cached=1387`，`degraded=0`；`tokens_in=160,461 / out=144,410 / total=304,871` |
| 代码身份 | 12/12 与 `a6ae5e5794a4…` 的 `code/config` 树一致 |
| 开关 | `HITT_D12_DETAIL=1`；`prompt_fn_sha256=0e16c4f8…`、`detail_line_len_on=55`；`code_sha=a6ae5e5`（短 sha）、`branch=feat/d12-detail` |
| 时间 | `started_at=20:24:36`；mtime `20:47:29` ⇒ 墙钟 **1373 s** |
| 跑批期间 code/ 提交 | 窗口内 **0 条** |
| 状态更正 | `reports/CYCLE-04-20261022.md:121` 记「取数时刻末行 seq=2628 / round 3，进程存活，该批无任何可引用读数」——**该观察已过期**：本批已正常收尾（33,824 行、`round 0..23` 连续、provider 全真），**但收尾不改变"缺 meta ⇒ probe"的准入结论**，只应把 CYCLE-04 那句"进程存活/无读数"改成"已收尾但仍缺 meta，仍为 probe" |
| **缺什么** | 无 `meta.json`、无起跑 porcelain 快照、无 host.log |

### 2.4 `run_worldline_c1_ctrl_n16r84_seed42`

| 项 | 复算值 |
|---|---|
| run.jsonl | 91,390,751 B；194,057 行；sha256 `4c840b5b8f8fe4bc…`（与 `R17` §附录一致） |
| seed / n / rounds | 42 / 16 / `round 0..83`（84 轮连续） |
| LLM 真跑 | `calls=3403`，provider 全 `openai_compat`，`cached=1666`，`degraded=0`；`tokens_in=368,419 / out=299,940 / total=668,359`；purposes 含 `describe 16` |
| 代码身份 | 12/12 与 `af1dffc61040…` 的 `code/config` 一致；`host.log` 记 `code_sha=af1dffc61040adc97c828b4927ac3935dbef2d1b`、`code_dir=…/.worktrees/worldline-c1-n16r84/code`（**全 40 位 sha，硬证据**） |
| 收尾自证 | `host.log`：`n_agents=16 rounds=84 events=194057 seconds=3567.2769 log_bytes=91390751`，`chain_ok/replay_parity/first_run_equals_replay/conservation_ok=True`，`final_state_hash=sha256:a8bf29c8…`；**`log_bytes` 与实测文件大小逐字节一致** |
| 开关 | `env_dump.txt`：`LIFE_PROMPT_WORLD_C1 = UNSET（变量不存在）`，存在性判定 **NO**，`开关断言: PASS`；`HITT_LLM_PROVIDER=openai_compat` |
| 时间 | `started_at=14:28:45`；`[life] seconds=3567.2769`（**批内精确值**）；mtime `15:28:31` ⇒ 墙钟 3586 s（**teardown 约 19 s**，即 mtime 比真实运行时长系统性高约 19 s） |
| 跑批期间 code/ 提交 | 窗口内 2 条（`913ac4d`@15:23 `feat/d2-prefer`、`a5ead79`@14:53 `feat/d2-trigger`）——**均不含于 `feat/world-line-c1`** ⇒ 未进入跑批 worktree |
| **缺什么** | 无 `meta.json`；**无独立 `git_status_start.txt`**（只有 `env_dump` 闸门 3 的 `code_dirty_rc=1` + 空输出）。**跑批 worktree 未删**（`.worktrees/worldline-c1-n16r84` @ `af1dffc`，见 §0.1 勘误；初版此处误写"已被删除"） |
| 廉正提示 | `launch_evidence.txt` 自带勘误：`launch.sh` 是事后从 `artifacts/r1-batch/` 手工补拷（同内容，记 sha256），非起批自动落盘；另 `TCP 443 探测: 可达` 与 `git ls-remote rc=124` 冲突，报告已按 rc=124 判「远端可见性未验证」。引用这两点时必须带上该勘误，不得写成"起批自动留痕" |

### 2.5 `run_worldline_c1_a1_n16r84_seed42`

| 项 | 复算值 |
|---|---|
| run.jsonl | 91,397,526 B；194,047 行；sha256 `ac9fa3122df3ca48…` |
| seed / n / rounds | 42 / 16 / `round 0..83`（84 轮连续） |
| LLM 真跑 | `calls=3403`，provider 全 `openai_compat`，`cached=1666`，`degraded=0`；`tokens_in=387,046 / out=317,196 / total=704,242` |
| 代码身份 | 12/12 与 `af1dffc61040…` 一致；`host.log` 记同一 `code_sha=af1dffc6…`（与 ctrl 臂同 sha ⇒ 单变量成立） |
| 收尾自证 | `[life] n_agents=16 rounds=84 events=194047 seconds=3492.0673 log_bytes=91397526`，四项自检 `True`，`final_state_hash=sha256:96de5c62…`；`log_bytes` 与实测一致 |
| 开关 | **进程内自证最强**：`launch_evidence.txt` 记 `systemd-run` unit `worldline-c1-a1-n16r84`、`cgroup=/system.slice/…`、`PROC-ENV LIFE_PROMPT_WORLD_C1=1`、`switch_in_process=PASS`、`env_file_removed_after_start=YES` |
| 时间 | `started_at=16:07:59`；`[life] seconds=3492.0673`；mtime `17:06:30` ⇒ 墙钟 3511 s（teardown 约 19 s） |
| 起跑快照 | `git_status_start.txt` **在库**（4 行，全为 `?? v2/evidence/…` untracked，**无 code/ 路径**）⇒ `code_unchanged_during_run` 可算为 `true`（只要在跑批 worktree 内重跑） |
| 跑批期间 code/ 提交 | 窗口内 1 条（`51cdb07`@16:56 `feat/d2-prefer`），**不含于 `feat/world-line-c1`** |
| 两臂差异观察 | 两臂 `LLM_CALL` 数、purposes 分布、`cached` 数**完全相同**（3403/1666），但 `events` 差 10（194,057 vs 194,047，差在 `MEMORY_FORGET`），`tokens_in` 差 18,627。⇒ 与本项目一贯口径一致：**这只说明"接线成立 + 内容有变"，不构成任何效果结论**，不得写成"世界线让记忆更…" |

---

## 3. `meta.json` 字段级可重建性矩阵（5 批通用）

| meta 字段 | 可否客观重建 | 主要依据 | 风险 |
|---|---|---|---|
| `provider` / `model` / `llm_calls` / `llm_cached` / `llm_purposes` / `degraded_calls` | ✅ | run.jsonl 的 `LLM_CALL.payload`（`obs llm-cost` 单一真源） | 无 |
| `events` / `wc_l` / `msg_counts` / `dropped_counts` / `msg_dropped_unknown_intent_field` | ✅ | run.jsonl 逐行统计 | 无 |
| `seed` / `n` / `rounds` | ✅ | `WORLD_INIT.payload.seed`、`AGENT_BORN` 计数、`round` 连续区间（已复算） | 与命令行声明交叉校验即可 |
| `run_sha256` / `derived_from_log_sha256` / `run_bytes` | ✅ | `sha256sum`（本文件 §2 已给） | 注意 run.jsonl **不入库**（`R17` 附录注明按仓库惯例），入库存的只有本台账里的 sha |
| `assertions`（`msg_uid_unique` / `ptr_*` / `turn_index_dense` / `participants_consistent`） | ✅ | emit_run_meta 从日志自算 | 无 |
| `assertions.code_unchanged_during_run` | ⚠ **a5 / a1budget / d12a 不可重建**（无起跑 porcelain 快照）；c1-ctrl 仅弱证据；c1-a1 可 ✅ | 需 `--git-status-start <快照文件>` | **这条不可用"我记得没改"替代**；`R19 finalize_arm.sh` 明确 S1 门禁要求该字段为 `true` |
| `code_sha` / `code_sha_end` | ⚠ 条件可重建：**必须在跑批当时的 sha 环境内运行 emit_run_meta** | `tools/d2/emit_run_meta.py` 取的是**执行时刻** `git rev-parse HEAD`（见源码 `code_sha = _git("rev-parse","HEAD")`） | **在当前主树重建会把 master HEAD 写进 code_sha —— 这是伪造代码身份，禁止** |
| `started_at` / `finished_at` / `duration_sec` | ⚠ 部分：c1 两臂有 `[life] seconds` 精确值；其余 3 批只能 mtime 推导 | switch_proof / host.log / 文件 mtime | mtime 系统性高估约 **19 s**（由 c1 两臂标定：3586 vs 3567.28、3511 vs 3492.07） |
| 开关取值（`LIFE_PROMPT_*` / `HITT_*`） | ✅ 但**不进 meta.json**（meta 无 switch 字段） | `switch_proof.txt`（3 批，自述式）/ `host.log`+`env_dump`（c1-ctrl）/ `PROC-ENV`（c1-a1，最强） | 「自述式 switch_proof」与「进程内自证」不等价，引用时要分清 |

---

## 4. 重建方案（本审计**不执行**，交由实现者/报告专员决定）

### 4-A 环境仍在的 3 批（a5 / a1budget / d12a）——可产出「原版口径」meta

前提（均已核）：`git worktree list` 显示
- `.worktrees/a2-prefer` → **`51cdb07` `[feat/d2-prefer]`**（a5 与 a1budget 的跑批 sha ✔）
- `.worktrees/d12-detail` → **`a6ae5e5` `[feat/d12-detail]`**（d12a 的跑批 sha ✔）

推荐步骤（须由实现者执行，审计角色不跑）：
1. 在该 worktree 内、以**仓库根**为 cwd 运行单一真源工具：
   `python3 tools/d2/emit_run_meta.py --run-dir <批次目录> --seed 42 --n 16 --rounds <42|24> --started-at <switch_proof 值> --duration-sec <推导值>`
2. **不要**传 `--git-status-start`（没有快照就别伪造）→ `assertions.code_unchanged_during_run` 会是 `null`，**这是诚实结果**，必须原样保留。
3. 落盘后**必须**另加 sidecar（例如 `meta.rebuild_note.txt`）写明：`rebuilt_at`（真实时间）、`code_sha` 来源 = 该 worktree HEAD、`started_at`/`duration_sec` 来源 = switch_proof + mtime（±20s）、`code_unchanged_during_run=null 的原因`。
4. 结论口径：**重建后仍不能升 evidence 级**——因为 S1 门禁要求 `code_unchanged_during_run=true`，而这 3 批无快照 ⇒ 只能判「`probe`（重建后可核对代码身份与规模）」。若要升 evidence，只能在报告里显式说明用的是**降级判据**并请 Leader 裁决，不得默认放行。

### 4-B 环境**已在**的 2 批（c1 ctrl / a1）——可直接原地重建，无需新建 worktree

> ⚠ 本节标题初版写「环境已删的 2 批……先建环境再重建」，**已勘误**：worktree `.worktrees/worldline-c1-n16r84` 存在且 HEAD=`af1dffc`（见 §0.1）。故第 1 步由"创建 worktree"改为"进入既有 worktree 并先核对 HEAD"。

1. **先进既有 worktree 核对身份（不要新建 worktree）**：
   `git -C .worktrees/worldline-c1-n16r84 rev-parse HEAD` 必须 = `af1dffc61040adc97c828b4927ac3935dbef2d1b`（与两臂 `host.log` 的 `code_sha` 逐位一致）——一致才允许继续；不一致则**停止重建**、以实况另行登记。
   然后在**该 worktree 内**运行 §4-A 第 1 步（`--rounds 84`、`--seed 42 --n 16`），这样 `meta.code_sha` 才会写成真值 `af1dffc`。
2. `duration_sec` 用 `[life] seconds`（3567 / 3492）而非 mtime；`started_at` 用 host.log 值。
3. c1-a1 有 `git_status_start.txt` 可传 → 该臂重建后 `code_unchanged_during_run` 可为 `true`；**c1-ctrl 仍为 `null`**（无独立快照，`env_dump` 闸门 3 只是弱证据，不能当 porcelain 快照用）⇒ 按 S1 门禁，**ctrl 臂即便重建也升不到 evidence**。
4. 若不想重建：按仓库既有先例写 **`meta.derived.json`**（模板见 `v2/evidence/run_l7v2_on_n16r60_seed42/meta.derived.json`），其 `_warning` 已明示「**不得**当作原版 meta.json 引用，**不得**用于任何准入判定」——这条先例值得直接沿用。

### 4-C 不建议的做法（会被本审计判为伪造）
- 在当前 master 主树直接跑 `emit_run_meta` 补这 5 批 → `code_sha` 会写成 `84ed6b1`，与跑批 sha（`51cdb07`/`a6ae5e5`/`af1dffc`）不符。
- 手写 `assertions.code_unchanged_during_run=true`。
- 用 mtime 推导的 `duration_sec` 冒充实测值而不注明来源。

---

## 5. 附加发现：任务书"5 个真 LLM 批缺 meta"是**漏报**

全库扫描（`v2/evidence/*/run.jsonl` 且无 `meta.json`）命中共 **35 个目录**：**mock 19 个**（`mock_*`）、**命名已作废 4 个**（2×`*_INVALID_*`、`run_f6_off_n16r84_seed42_VOID`、`run_r6_treat_n16_seed42_ABORTED_2036`）、**小样本 2 个**（`run_baseline_n4r2_20261020T220207` 223 行、`run_d4_P2_n16r12` 34 行），**剩余 10 个为真 LLM 缺 meta**（= 35 − 19 − 4 − 2）。任务书只列了其中 5 个，以下 5 个是本台账补登的：

| 批次目录 | run.jsonl | seed/n/rounds | 真跑验真（obs llm-cost） | 现有旁证 | 处置 |
|---|---|---|---|---|---|
| `run_a1wording_n16r42_seed42` | 25,069,906 B / 51,426 行 | 42 / 16 / **`0..33`（34 轮，合法不完整前缀）** | rc=0，`openai_compat 2389/2389`，tokens 301,049 | 仅 `README.md`（已自述 34 轮原因与"为什么没有 meta.json"） | **永久 probe**；README 已规定"必须按窗口 34 轮引用" |
| `run_g1_b0_n16r60_seed42` | 55,225,513 B / 116,318 行 | 42 / 16 / `0..59`（60 轮） | rc=0，`openai_compat 2878/2878`，tokens 504,062 | **仅 run.jsonl** | **不可重建**（无 code_sha/started_at/开关）→ 只读数据源、永久 probe |
| `run_l7struct_on_n16r60_seed42` | 55,347,247 B / 116,385 行 | 42 / 16 / 60 轮 | rc=0，`openai_compat 2878/2878`，tokens 574,420 | `recompute_r17.txt` | 同上 |
| `run_l7v2_on_n16r60_seed42` | 55,598,046 B / 116,498 行 | 42 / 16 / 60 轮 | rc=0，`openai_compat 3042/3042`，tokens 733,601 | `meta.derived.json` + `recompute_r16.txt` | 已有派生 meta 先例，**仍不得用于准入** |
| `run_dr_round1_arm-ctrl_n16r60_seed42` | 55,224,767 B / 116,319 行 | 42 / 16 / 60 轮 | rc=0，`openai_compat 2878/2878`，tokens 500,513 | **仅 run.jsonl** | 与 g1/l7struct 同处置 |

另有 `run_d12a_base_seed7_n16r24_INVALID_confounded`（33,840 行，真跑 2252 calls）与 `run_d12a_treat_seed7_n16r24_INVALID_incomplete`（2,629 行，真跑 260 calls）——**名字已自述作废**，本台账不重复登记，但提醒报告别把它们当对照臂读数引用。

### 5.1 逐批凭据清点：谁能补、谁不能补（新事实，2026-10-22 22:2x 补登）

state-surveyor 报「10 个缺 meta 批里只有少数带起批凭据」，本审计逐目录实测如下（`ls <批次目录>`）：

| 批次 | switch_proof.txt | 其它起批侧凭据 | 能否补出**可信** `code_sha`/`env` |
|---|---|---|---|
| `run_a5_real_n16r42_seed42` | ✅ | — | **能**（短 sha `51cdb07` + env 行；worktree 在） |
| `run_a1budget_real_n16r42_seed42` | ✅ | — | **能**（同上） |
| `run_d12a_real_n16r24_seed42` | ✅ | — | **能**（`a6ae5e5` + `prompt_fn_sha256`；worktree 在） |
| `run_a1wording_n16r42_seed42` | ❌ | `README.md`（自述 34 轮 + 无 meta 原因 + `run.jsonl` sha256） | **部分**：README 自述 `code a637371` 的只读副本 + `--override`，**无机器可校验的 switch_proof** ⇒ 只能登记"自述式、不可硬验" |
| `run_worldline_c1_ctrl_n16r84_seed42` | ❌ | `host.log`（含 40 位 `code_sha`）、`env_dump.txt`（开关存在性断言）、`launch_evidence.txt` | **能**（40 位 sha 硬证据，强于 switch_proof） |
| `run_worldline_c1_a1_n16r84_seed42` | ❌ | `host.log`、`launch_evidence.txt`（**进程内 PROC-ENV 自证**）、`git_status_start.txt`、`prompt_diff_proof.txt` | **能**（最强） |
| `run_g1_b0_n16r60_seed42` | ❌ | **无（仅 `run.jsonl`）** | **不能** ⇒ **不可补例外** |
| `run_dr_round1_arm-ctrl_n16r60_seed42` | ❌ | **无（仅 `run.jsonl`）** | **不能** ⇒ **不可补例外** |
| `run_l7struct_on_n16r60_seed42` | ❌ | `recompute_r17.txt`（**事后复算输出，非起批凭据**） | **不能**（事后文件无法证明跑批时刻的代码/开关） |
| `run_l7v2_on_n16r60_seed42` | ❌ | `meta.derived.json`（派生，非原版）、`recompute_r16.txt`（事后） | **不能**（只有派生 meta，按纪律不得用于准入） |

**口径修正（对 state-surveyor 原始表述的精确化）**：带 `switch_proof.txt` 的**恰为 3 个**（`a5` / `a1budget` / `d12a_real`）；`a1wording` 没有 `switch_proof`，只有 `README.md` 自述——把两者合称"4 个带 switch_proof"会**高估**可机器校验性。**真正的"零凭据（除 run.jsonl 外无任何文件）"是 2 个**：`run_g1_b0` 与 `run_dr_round1_arm-ctrl`；`l7struct` / `l7v2` 有文件但全是**事后**产物，同样补不出可信 `code_sha`/`env`。⇒ 本轮 P0-1 应在台账内**单列 4 个不可补例外**（`g1_b0`、`dr_round1_arm-ctrl`、`l7struct_on`、`l7v2_on`），这 4 个**即便将来树也在**也不补 meta，只作只读数据源。

```bash
# 复算（仓库根）：逐批看有没有起批侧凭据
for d in $(cat /tmp/ten.txt); do b=$(basename $d); printf "%-48s " $b
  for f in switch_proof.txt host.log env_dump.txt launch_evidence.txt git_status_start.txt README.md; do
    [ -f "$d/$f" ] && printf "%s✓ " "${f%%.*}"; done; echo; done
# 实测结论：switch_proof✓ 仅 a5 / a1budget / d12a_real；零凭据仅 g1_b0 / dr_round1_arm-ctrl
```

> 复现命令（一次扫全）：
> ```bash
> # ① 列出所有「有 run.jsonl 但无 meta.json」的目录（应得 35 个）
> for d in v2/evidence/*/; do [ -f "$d/run.jsonl" ] || continue; [ -f "$d/meta.json" ] || echo "$d"; done | wc -l
> # ② 排除 mock_/INVALID/VOID/ABORTED/小样本后应得 10 个（本台账口径）
> for d in v2/evidence/*/; do d=${d%/}; [ -f "$d/run.jsonl" ] || continue; [ -f "$d/meta.json" ] && continue
>   case "$(basename $d)" in mock_*|*_INVALID_*|*_VOID|*_ABORTED_*|run_baseline_*|run_d4_P2_*) continue;; esac; echo "$d"; done
> # 期望 10 行：run_a1budget_real_n16r42_seed42 / run_a1wording_n16r42_seed42 / run_a5_real_n16r42_seed42 /
> #          run_d12a_real_n16r24_seed42 / run_dr_round1_arm-ctrl_n16r60_seed42 / run_g1_b0_n16r60_seed42 /
> #          run_l7struct_on_n16r60_seed42 / run_l7v2_on_n16r60_seed42 /
> #          run_worldline_c1_a1_n16r84_seed42 / run_worldline_c1_ctrl_n16r84_seed42
> # ③ 真跑验真（逐个）：cd code && python3 -m obs llm-cost --log ../v2/evidence/<dir>/run.jsonl --require-provider openai_compat
> ```

---

## 6. 阻塞项：R19 人工 precision（CYCLE-04 P0-2 / N-2 / C-2）现状确认

| 项 | 现状（本审计核实） | 判定 |
|---|---|---|
| `v2/evidence/r19_topicbreadth_n8r24_seed42/precision_sample.md` | `grep -c '待人工填'` → **10**；10 条样本的 `judgement:` 全部仍是 `【待人工填】`（第 13/21/29/37/45/53/61/69/77/85 行） | **仍全部未填**，与 CYCLE-04 §N-2 记录一致 |
| 能否由 AI 代填 | **不能**。本项目判据写死为"人工 precision"，用 LLM 代判＝用被审计对象自己的判据来源冒充人工标签，属自证；本审计**拒绝**代替任何人填写 | **硬阻塞** |
| 门槛冲突（C-2） | `precision_sample.md` 写「N=10 ∈ [8,15) ⇒ 全量判（预注册 B.4）」；`README.md` §5 与 `readings.md` 写「≥15 才判」 | CYCLE-04 按更严一侧（≥15）判"门槛未达"，**这个选择本身要在报告里保留原文**，不得只写结论 |
| 结论 | **双重阻塞**：① 10 条 judgement 未填（需真人）；② 即便填满，n=10 < 15 ⇒ 仍不能出 precision 结论，只能作 pilot 参考 | 报告中的 R19 效果结论**必须**保持「不可判」 |

> 建议（给 Leader/报告专员）：把 precision 明确写成"需**未参与 R19 代码编写**的真人成员逐条判定"的待办，并在报告把"n=10<15"与"未填"两件事**分开写**，避免读者误以为填完就能出结论。

---

## 7. 给报告与交付专员（report-writer）的写入白名单

**可以写进结论（有本审计独立复算 + 可复算命令）**
- 5 批的 `obs llm-cost` 读数：`calls / provider 全 openai_compat / cached / degraded=0 / tokens_in / tokens_out / tokens_total`（数值见 §2，全部本审计亲跑 rc=0）。
- 5 批的 `events`、`seed=42`、`n=16`、`rounds`（`42/42/24/84/84`，均连续）。
- 5 批 `run.jsonl` 的 sha256 前 8 位（`aa6edc35 / 0bc80cd2 / 64f9da4b / 4c840b5b / ac9fa312`）。
- 代码身份：`config_components` 12/12 与各批跑批 commit 一致；c1 两臂另有 40 位 `code_sha=af1dffc6…` 与 worktree 关系（**可写**，但须注明"来自 host.log/launch_evidence，非 meta.json"）。
- 时间：c1 两臂的 `[life] seconds`（3567.2769 / 3492.0673）为**实测**；其余 3 批 `started_at` 来自 switch_proof、`finished_at` 来自 mtime（**必须带"mtime 推导，约 +19s"标注**）。
- 开关：a5/a1budget/d12a 的取值**只能**溯源自 `switch_proof.txt` 并注明"起批脚本自述"；c1-a1 可写"进程内 PROC-ENV 自证"；c1-ctrl 写"env 存在性断言 PASS（变量不存在）"。

**只能写进"缺口/局限"小节**
- 任何以 `meta.json` 为锚点的表述——这 5 批**都没有**；直到有人按 §4 重建为止。
- `assertions.code_unchanged_during_run`（除 c1-a1 在重建环境重算后可取 true 外）——**不要写"跑批期间代码未改动"**；可写"跑批窗口内 code/ 四子树无提交进入该跑批分支（命令见 §2），但起跑快照缺失，无法用工具口径证明工作树未变"。
- `duration_sec` 一律标"推导值"，不得与 c1 两臂的实测值混排。
- CYCLE-04:121 关于 `run_d12a_real` 的"进程存活 / 无任何可引用读数"——**已过期**，请更新为"已收尾（33,824 行、round 0..23 连续），但仍缺 meta ⇒ 仍 probe"。
- 新增漏报：缺 meta 的真 LLM 批**实际 10 个**（任务书 5 + 补登 5，§5），**不要写"仅 5 个"**，也**不要写 11**。

**一律不得写**
- "对话变好""生活气息提升"等效果结论（5 批均为 probe；R19 precision 未填且 n<15）。
- 任何未在 §2 出现过的派生比率（如把 tokens 换算成成本、把 cached 率当效果）。
- 把 `meta.derived.json` 或重建后的 meta 当作原版 `meta.json` 引用、或据以通过 d5 准入。

---

## 8. 本审计做了什么 / 没做什么

**做了**：逐批统计 run.jsonl（行数/sha256/事件/rounds/AGENT_BORN/WORLD_INIT）；`obs llm-cost` 亲跑 12 个批次（5 指定 + 5 补登 + 2 INVALID）；按 `engine.version.component_digests` 同口径验证 12 个 config 文件在 5 个跑批 commit 上的身份；读取并交叉核对 `switch_proof.txt` / `host.log` / `env_dump.txt` / `launch_evidence.txt`；统计 5 个跑批窗口内 `code/` 四子树的提交（并归属分支）；核实 worktree 现状；核实 precision_sample 现状。

**没做（硬约束）**：未写/未改任何 `meta.json`（含 `meta.derived.json`）；未跑批；未改 `code/life|orchestration|config|engine`；未 commit；未代替任何人填 precision 判定；未使用未经复算的数字。

**遗留**：本文件为未跟踪新文件，需由 report-writer 纳入提交；若 Leader 决定执行 §4 重建，重建动作应由 life-behavior-eng（实现者）执行，并由本审计在重建后按同一口径复核。
