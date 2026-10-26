# R10-E2E 批次记录 · `run_r10e2e_n16r60_seed42`

> 本文件在**起跑后立刻落盘**（前置事实可核），跑完后由同一路径补填实测读数。
> 未填项一律写 `<待跑完填充>`，**不得留空、不得事后改写前置事实**。

## 0. 批次用途与对照关系

本批**不是「新加一个机制」**，而是把「睡眠 → 固化 → 次日记忆延续」的**落账轴**从 probe 推到 admission。

- **绑定 ref**：`feat/r10-residual-memid` @ `625187c31b2c93d80d48bcf60afed1b5f41afc98`（短 sha `625187c3`），**未 push**
  - commit 标题：`fix(life): R10-b 固化摘要跨夜落账（mem_id 纳 day）+ 写被拒不再发「巩固完成」`
  - parent = `9fb3855`（基点）
- **运行树**：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/r10-residual-memid`（**独立 worktree，未动共享主树 HEAD**）
  - 起跑时主树 `master` = `3dd30a0`（life-engineer 报的 rebase 基点为 `9fb3855`；两者差异不在 `code/` 域，见 §5）
- **对照基线（唯一有效）**：`v2/evidence/f2b_v2_n16r60_seed42/run_off/`，`code_sha = a9c74f5…`、`git_dirty_code_files = []`、**有 meta.json**
- **基线与本批的变量**：`mem_id` 键构成 `(agent, subject)` → `(agent, subject, day)`；写意图被拒时不再发 `MEMORY_CONSOLIDATE`
- **不采用的方案（留痕）**：不 cherry-pick 到 `d9391a3`（A 方案，会引入 rebase 风险与 schema 隐性差异）；不用 `run_g1_b0` 作 arm 依据（见 §1.3）

## 1. 起跑前状态（三道闸）

### 1.1 串行闸

```
$ ps -eo pid,args | grep -E 'orchestration run|run_batch' | grep -v -E 'grep|pgrep' | wc -l
0
```

### 1.2 代码身份闸（worktree 内）

```
$ cd .worktrees/r10-residual-memid && git rev-parse HEAD
625187c31b2c93d80d48bcf60afed1b5f41afc98
$ git rev-parse --abbrev-ref HEAD
feat/r10-residual-memid
$ git status --porcelain -- code/life code/orchestration code/config code/engine
（空）
$ git status --porcelain          # 全树
（空）
```

补充 1：worktree 内 `code/.env.local` 为**主树同文件的 bit 级拷贝**。两处 sha256 **逐位一致**：

```
$ sha256sum <main>/code/.env.local
fe48dfca7cfee70d5933b6c46de5541fef9fc09e77b805cd7df3728348dac6f9  <main>/code/.env.local
$ sha256sum <worktree>/code/.env.local
fe48dfca7cfee70d5933b6c46de5541fef9fc09e77b805cd7df3728348dac6f9  <worktree>/code/.env.local
```

该文件在 `.gitignore` 内（`code/.env.local` 与 `**/.env.local` 两条）、**不参与代码身份**，但为可复现补齐；**两处 sha256 逐位一致**。文件内容为真实凭据，只记录 sha256，不记录内容。

补充 2：全树 `git status --porcelain` 原文与时刻。

- **起跑前**（在写入 `started_at.txt`（18:30:30）之前的同一操作序列内执行，该次调用未单独打时间戳，**不臆造时刻**）：输出为**空**。
- **跑批中**（`2026-10-23 18:33:05 +0800`）：全树已出现 2 个**未跟踪**件，均为 run_batch 自己的 preflight 留痕，**不属任何红线目录**：

```
$ git status --porcelain            # 2026-10-23 18:33:05 +0800
?? v2/evidence/preflight/clean_tree_20261023T103036Z_625187c3_run_batch.json
?? v2/evidence/preflight/preflight_20261023T103036Z_625187c3_run_batch.log
$ git status --porcelain -- code/life code/orchestration code/config code/engine
（空）
```

⇒ 跑批期间红线四目录**始终为空**；全树出现的 `??` 仅由本批自身的 preflight 产出，与代码身份无关。

### 1.3 arm 复刻依据

依据文件 = **`v2/evidence/f2b_v2_n16r60_seed42/run_off.sh` 原文**：

```bash
cd "$WT"                                # worktree（本批同样在独立 worktree 跑）
unset LIFE_PROMPT_TOPIC_BREADTH         # ← off 臂：不设（代码内默认 OFF）
setsid nohup bash tools/d2/run_batch.sh \
  --out-dir "$E/run_off" --seed 42 --agents 16 --rounds 60 \
  --side-root /tmp/f2b_v2_off_side
```

运行期硬证据 = `run_off/switch_proof.txt`（取自 `/proc/<pid>/environ`）：仅 `HITT_LLM_PROVIDER=openai_compat`，无其他 `HITT_*`。

**本批 env 口径（防审计误读）**：
- 本批**显式不设任何 `HITT_*`**；`LIFE_PROMPT_TOPIC_BREADTH` 不设（= 代码默认 OFF）
- `HITT_LLM_PROVIDER=openai_compat` 由 `tools/d2/run_batch.sh` **自身 export**（`run_batch.sh` 内 `if [[ "$MOCK" -eq 0 ]]; then export HITT_LLM_PROVIDER=openai_compat`），**非本批设置**
- 起跑前 `env | grep HITT` 原文：**空输出**（0 行），文件留痕 `env_hitt_before_launch.txt`（0 字节）

**明确不作依据的项**：
- `run_g1_b0_n16r60_seed42` **只作历史参照，不作 arm 依据**——该目录**仅剩 `run.jsonl`**（无 `host.log` / `switch_proof.txt` / `meta.json`），`v2/evidence/evidence_ledger_20261022.md:212` 已定其为「不可重建、永久 probe」。任何「复刻自 b0 的 host.log」表述均为**引用错误**。
- `run_g1_a1` 的 `host.log` **只作命令格式参照**，不作 b0 的 arm 依据。

## 2. 起跑命令与实际耗时

```
MODE=real
started_at = 2026-10-23 18:30:30 +0800      (文件 started_at.txt；unit 实际 active 于 18:30:36)
托管方式 = systemd-run --unit=r10e2e-memid-183030 --collect --property=MemoryMax=8G
           （setsid 不换 cgroup、会被 jiuwenswarm.service 连坐回收，故按 runbook §4.5 实测结论改用 systemd-run）
脱离证据 = /proc/898422/cgroup → 0::/system.slice/r10e2e-memid-183030.service
           systemctl show ... --property=ControlGroup → /system.slice/r10e2e-memid-183030.service
           （均不含 jiuwenswarm.service ⇒ 真脱离）

命令：
cd <worktree> && bash tools/d2/run_batch.sh \
  --out-dir <main>/v2/evidence/run_r10e2e_n16r60_seed42 \
  --seed 42 --agents 16 --rounds 60 --side-root /tmp/r10e2e_side_183030
（--side-root 为**全新路径**，不复用基线 /tmp/f2b_v2_off_side）

run_batch 内 preflight 输出（原文）：
PASS preflight sha=625187c3(feat/r10-residual-memid) ts=2026-10-23T18:30:36+08:00
  concurrency=0 frozen_tree=clean
  log=.worktrees/r10-residual-memid/v2/evidence/preflight/preflight_20261023T103036Z_625187c3_run_batch.log

finished_at = <待跑完填充>
实际墙钟   = <待跑完填充> 秒（基线同规模 `seconds=3230.5`≈54 分钟，见 `run_off_host.log`；**该数不可用于折算本批**，理由见 2.1）
墙钟闸门   = **150 分钟（硬闸）**，见 2.1 的放宽记录与依据
```

### 2.1 墙钟闸门由 90 分钟放宽为 150 分钟（**透明记录，非事后默认**）

- **放宽决定作出时刻与主体**：**2026-10-23 18:38，由 Leader 作出**。
- **依据**：起跑后观测到 `max_round` 推进速率明显慢于基线；根因是**缓存态差异**——基线 `f2b_v2_off` 的 `llm_cached = 1425 / ratio 0.4951`（近半调用是缓存重放，近乎瞬时），本批 `--side-root` 全新、**`cached≈0`**，全部为真调用。
- **判据声明**：⇒ **墙钟不可用基线折算**；本轮判据是「**能否跑完并产出可复算证据**」，**不是速度**。
- **两级报警**：① **120 分钟**时向 Leader 交一次进度包（`max_round` / `LLM_CALL` / `judgments` / 增量趋势 / 按 `max_round` 折算的预计完成回合）；② **150 分钟**仍无 `run_batch.rc` ⇒ **停机并报 Leader**。
- **进度口径**：只用 **`max_round`**（不用行数、不用 `LLM_CALL` 外推——调用数随对话密度暴涨，外推必错）；`max_round` 随时间至少两点记录见 §2.2。
- **0 增长报警（两档）**：
  - ① 跨 **≥2 个 flush 窗口（约 ≥5 分钟）** 且 `max_round` 与 `judgments` **同时不动** ⇒ 立即报警；
  - ② **`judgments` 单边不动 5 分钟**（即使 `max_round` 尚未到 flush 边界）⇒ 也立即报警——`judgments` 是实时量，它停住意味着 **LLM 侧断了**，属真问题（`max_round` 的「不动」可能只是缓冲窗口，不得据此判死）。

### 2.2 进度采样（`max_round` 时序，≥2 点）

| 采样时刻 | `max_round` | `judgments` | `LLM_CALL`（累计，仅登记不外推） | 备注 |
|---|---|---|---|---|
| 2026-10-23 18:38:46 | **3** | 186 | 260 | 起跑 18:30:36 ⇒ elapsed≈8.2′；flush 于 18:36:02 |
| 2026-10-23 18:50:25 | **9** | 364 | 732 | elapsed≈19.8′；flush 于 18:44:29（行数 2629→9677）；⇒ 10 回合（0..9）/19.8′ ≈ **1.98 分钟/回合** |
| <待填> | <..> | <..> | <..> | |

判定：`max_round` 在推进、`judgments` 在增长 ⇒ **无 0 增长**、无卡死迹象。
（口径提醒：`max_round=9` 表示回合 **0..9 共 10 个**已完成；`max_round` 只在 flush 边界跳变。）

退出码     = <待跑完填充>
  （0 = 通过；3 = wc -l != meta.events；4 = 非真跑；5 = 日志内 spec 与声明不一致；6 = obs llm-cost 门禁失败；9 = preflight 拒跑）
```

## 3. 叙述前置声明（**原样保留，不得改写**）

> 基线 `a9c74f5` 已含 `c01f6dd`（R18 两条观测断点修复）⇒ **机制轴（`text` 1267 KEPT / 0 DROPPED）与漂移轴（`drift_permille/pf0/pf_t` null 0/80）在本批应当保持不变**；本批预期只有**落账轴**移动（semantic 256→1267、差额 1011→0、拒收 1011→0）。
> **机制轴 / 漂移轴的「不变」是预期内的，不等于修复无效。**

**缓存态差异声明**：基线 `llm_cached = 1425`、`llm_cached_ratio = 0.4951`；本批 `llm_cached = <待填充>`、`cached_ratio = <待填充>`。这是**缓存态差异，非机制差异**。
限定：固化 / 落账计数是**确定性事件链路，不经 LLM 文本层** ⇒ 缓存态不影响落账轴两条等式；但**行为层读数**（`memory_refs`、召回）可能受文本层同源性影响 ⇒ 行为轴**本轮只登记、不下结论**。

**确定性表述（不得改写）**：**「多 1011 条语义记忆进入世界态 ⇒ 状态指纹必然变化；同 seed 同配置两次跑指纹相同 ⇒ 确定性成立」**。
因此**不得**写成「`state_hash` 与基线一致」；「与历史批不同」是**预期副作用，不是非确定性**。
参考值（life-engineer 夹具，**不是本批**）：修前 `sha256:8d18ecc4…6909`、修后 `sha256:c5a22080…15d8`；**本批真实指纹以 `meta.json` 为准**（见 §7）。

## 4. 五轴读数（用冻结脚本复算）

读数器：`tools/f2/r10e2e_axes.py`，`sha256 = f2d2bad51bc6f49cf88191786c78b788a2527442e77590a30afcef6a71f3b94d`
基线预登记件：`v2/evidence/axes_prereg_f2b_v2_off_a9c74f5.json`，`sha256 = e5dcdf278a8cd86c755056e04a4ec29810c5b923cbcb0eae65c7fc8434419a17`
修前预登记件：`v2/evidence/axes_prefix_g1_b0_d9391a3.json`，`sha256 = 0f69ba52a7bc6f5b23e9fc1b4a0350868f22ad99f6802d351d02b18560b4510e`
本批读数件：`axes_r10e2e.json`，`sha256 = <待填充>`

| 轴 | 指标 | 修前 `g1_b0`(d9391a3) | 基线 `f2b_off`(a9c74f5) | 本批(625187c3) | 预登记预测 | 判定 |
|---|---|---|---|---|---|---|
| 机制 | `MEMORY_CONSOLIDATE` 总数 | 1267 | 1267 | <..> | 不变 | <T/F> |
| 机制 | `text` KEPT / DROPPED | 0 / 1267 | 1267 / 0 | <..> | 不变 1267/0 | <T/F> |
| 落账 | `semantic` 写入 | 0 | 256 | <..> | 1267 | <T/F> |
| 落账 | `distinct produced_mem_id` | 256 | 256 | <..> | 1267 | <T/F> |
| 落账 | 差额（事件数 − distinct） | 1011 | 1011 | <..> | 0 | <T/F> |
| 落账 | `INTENT_REJECTED(MEMORY, invalid_payload)` | 0 | 1011 | <..> | 0 | <T/F> |
| 落账 | `assert_gap_eq_rejected` | false | true | <..> | True | <T/F> |
| 落账 | `assert_semantic_eq_distinct` | false | true | <..> | True | <T/F> |
| 漂移 | `SLEEP_COMPLETED` 分母 | 80 | 80 | <..> | 不变 | <T/F> |
| 漂移 | null `drift_permille`/`pf0`/`pf_t` | 80/80/80 | 0/0/0 | <..> | 不变 0 | <T/F> |
| 行为 | `ctx.memory_refs` **键是否存在** | 键不存在 | 键不存在 | <..> | 不变 | <T/F> |
| 行为 | `MEMORY_RETRIEVE` 总数 / 带 selected | 960 / 944 | 960 / 944 | <..> | — | 登记 |
| 口径 | `MEMORY_WRITE` 总数 | 28076 | 28076 | <..> | 29087（+3.60%） | <T/F> |
| 口径 | `MEMORY_WRITE` kind | obs 27484/ref 336/sem 0 | obs 27484/ref 336/sem 256 | <..> | sem→1267 | <T/F> |
| 口径 | `MEMORY_FORGET` | 38978 | 38978 | <..> | 同向升；**下降即停手报 Leader** | <T/F> |
| 口径 | `forget / write` | — | 1.3883 | <..> | 口径漂移（登记） | 登记 |
| 旁证 | `SLEEP_STARTED` / `SLEEP_COMPLETED` | 80 / 80 | 80 / 80 | <..> | 不变 | <T/F> |
| 旁证 | `OBSERVATION` | <..> | 27570 | <..> | 不变 27570 | <T/F> |
| 旁证 | `PERSONA_DRIFT` | 104 | 104 | <..> | — | 登记 |

### 4.1 两个机械断言的写法（三段式，**原样保留**）

1. `assert_gap_eq_rejected` 是**输出字段**而非门禁：脚本恒 `rc=0`、必吐完整读数（`tools/f2/r10e2e_axes.py` 第 167–168 行是两个字典布尔字段的比较赋值，**不是** Python `assert`）。
2. 因此「修前批断言 `false` 但仍留下 1011/0」可解释：**断言只记录、不阻断**（实测修前批 rc=0 且完整产出）。
3. 两个断言本批预期 **True / True**，实测值见上表。

### 4.2 口径红线（**两代 1011 不可混写**）

> 修前批 `g1_b0` 的 gap 1011 但 `rejected = 0` ⇒ 这个 1011 **不能用「拒收」解释**（来自 `text` 被整段丢弃，同批 `text_DROPPED = 1267`）；基线批 `f2b_v2_off` 的 1011/1011 才是拒收解释。两个 1011 是**不同成因**，不是同一件事，**不得混写或合并叙述**。

### 4.3 `forget/write` 唯一计算式

`MEMORY_FORGET 总数 ÷ MEMORY_WRITE 总数`（基线 `38978 / 28076 = 1.388303` → **1.3883**）。**不做 per-agent 比值的均值混合口径**（该算法基线为 1.38912，列出仅为排除歧义）。

### 4.4 `MEMORY_FORGET` 的判据：**总条数 ± 且 level 分布可解释**（不只比总数）

理由（life-engineer 2026-10-23）：`plan_forgetting` 对 `protected` 记忆只 `demote`/`keep`；本批新增的语义记忆 `importance=6` 且 `-SM-` 属派生记忆，若落入保护名单则走 `demote` 而非 `drop` ⇒ **级别分布会变、总数不一定涨**。所以判据写成「总条数 ±、`level` 分布可解释」，而非单看升降。

伴生冻结件（**不改主读数器、不动其 sha256**）：`tools/f2/r10e2e_forget_levels.py`，`sha256 = 409e108ec86e943ef48524ab9248088188daece0d82445ee8118205b5a0f30f1`

| 批 | `MEMORY_FORGET` 总数 | `demote` | `drop` | `merge` | `protected=true` | `-SM-` 命中 | `retention` p50 / mean |
|---|---|---|---|---|---|---|---|
| 修前 `g1_b0`(d9391a3) | **38976** | 30664 | 1920 | 6392 | 738 | 499 | 406 / 398.0 |
| 基线 `f2b_off`(a9c74f5) | **38978** | 30547 | 1990 | 6441 | 617 | 337 | 398 / 397.45 |
| 本批（625187c3） | <待填充> | <..> | <..> | <..> | <..> | <..> | <..> |

预登记件：`v2/evidence/forget_levels_g1_b0_d9391a3.json`、`v2/evidence/forget_levels_f2b_v2_off_a9c74f5.json`（本批对应件跑完补 sha256）。

### 4.5 预登记核对的防误读规则（life-engineer 2026-10-23）

1. `semantic` 落账预登记 **1267**；若实测在 1267 附近但差几条，**先不当失败**——差异只可能来自「同一 `(agent, day, subject)` 当夜出现两次固化」这类撞车，此时**看 `INTENT_REJECTED(MEMORY)` 是否为 0 定因**。
2. `CONSOLIDATE − distinct produced_mem_id` 与 `INTENT_REJECTED(MEMORY)` 应**同为 0**；若两者一起 `>0` 且相等，说明存在**别的撞键源**（不在残修域内）⇒ 抽 `INTENT_REJECTED.payload.requested.mem_id` 3 条原始样本入证。
3. `MEMORY_WRITE ≈ 29087`（= 28076 + 1011）是**估计值**，**不是硬阈值**；硬判据是 `semantic = 1267` 与上条两个 `0`。

## 5. 变量闸原文

```
$ git diff --stat a9c74f5 625187c -- code/
 code/life/agent.py                                |  26 +++-
 code/life/sleep_window.py                         |  24 +++-
 code/tests/test_sleep_consolidation_multinight.py | 159 ++++++++++++++++++++++
 3 files changed, 204 insertions(+), 5 deletions(-)

$ git diff --stat a9c74f5 9fb3855 -- code/      # 基点自身与基线一致
（空）

$ git diff --stat a9c74f5 3dd30a0 -- code/      # 主树 master tip，同样一致
（空）
```

判定：**只含预期文件**（2 个实现文件 + 1 个新增测试；`code/tests` 不是 `code/life|orchestration|config|engine` 指纹域，属允许范围）。
`code/orchestration/integration.py` **未改**（append-only 判重一行未动）、`code/config`、`code/engine` **未改**。第四个改动件 `tools/f2/verify_sleep_multinight.py` 不在 `code/` 域，故不出现在该 diff。

## 6. 真 LLM 验真

### 6.0 侧车目录计数口径（**别把去重计数当调用次数**）

`--side-root` 下三类文件的含义不同，**只有其一是 1:1 对应调用次数**：

| 路径 | 含义 | 与调用次数的关系 |
|---|---|---|
| `src/<sha256>.txt` / `.vec` | **内容寻址**的正文/向量（同内容只存一份） | **去重后唯一正文数 ≤ 调用次数**，**不是**调用次数 |
| `freeze_cache/judgments/JF-*.json` | 每次 judge 调用的判定结果 | **1:1**（基线实测 `judgments = 668`，同批 `llm_purposes.judge = 668`，逐位相同） |
| `mem/` | 语义记忆正文（`-SM-`） | 与 `semantic_writes` 相关，非调用计数 |

基线标定（`/tmp/f2b_v2_off_side`，跑完后）：`src/*.txt = 1311`、`src/*.vec = 1311`、`judgments = 668`，而同批 `llm_calls = 2878`、`llm_purposes.judge = 668`。
⇒ **`src` 只有 `llm_calls` 的约 45.6%**（近半调用命中缓存、正文被内容寻址复用）。
**作进度判据请用 `judgments`（1:1 judge 调用），不要用 `src`（内容寻址去重，仅约 45.6%）。**

### 6.0b `run.jsonl` 行数不能当活性判据（缓冲语义）

`run_batch.sh` 传 `--flush-every 2`，其语义是 **「每 N 回合把已提交前缀原子落盘」**（`orchestration/integration.py`：`flush_every > 0` 时每 N 回合 flush；默认 `0` 表示**只在末尾写**）。
⇒ 因此 **`run.jsonl` 行数会成段滞后**：本批 18:30:37 只落了创世段（34 行），下一次落盘要到回合 2 边界（实测 `mtime=18:36:02`，行数跳到 2629）。
**行数滞后属缓冲，不是卡死；活性以「进程存活 + `judgments` 增长」为准。**

### 6.0c 重放一致性校验（终态后执行，不占跑批时间）

- `cd code && PYTHONPATH=. python3 -m engine verify --log <run.jsonl>`：实现是**对同一条日志折叠两次再比 hash**（`engine/cli.py::_cmd_verify`），输出 `replay#1`/`replay#2`/`PASS`，**不读取 side-root 正文**（`body_ref` 只作文本字段参与折叠）。
- `chain_ok` / `replay_parity` / `conservation_ok` / `final_state_hash` **不来自 `engine verify`**，而来自**批跑自身**的收尾报告（`orchestration/cli.py:36-38` 打印，落进 `run_batch.log` 尾部）。
- **证明边界（不得越界表述）**：双 replay 相同只证明「**同一条日志重放出同一世界态**」，**不**证明「跑两次得到同批对话」——真 LLM 批两次 `run.jsonl` 必然不同；**不得写成「本批可完整复现」**。


```
$ PYTHONPATH=code python3 -m obs llm-cost --log <run.jsonl> --require-provider openai_compat
<待跑完填充>
```
`by_provider` = <..>；`total.calls` = <..>；`total.degraded` = <..>；`tokens_total` = <..>；`cached` = <..>
（注：无 `--log` 时返回 `{}` 且 rc=0，**不得**当作验真通过。）

## 7. 产物与 sha256

| 文件 | sha256 | 说明 |
|---|---|---|
| `run.jsonl` | <待填充> | 行数 <..> |
| `meta.json` | <待填充> | `code_sha`/`started_at`/`switch` 快照 >>|
| `axes_r10e2e.json` | <待填充> | 五轴读数 |
| `run_batch.log` | <待填充> | 含 preflight PASS 与 `[d2] self-check` |
| `run_batch.rc` | 内容 `<..>` | 退出码 |

**meta.json 是准入条件**：<已产出 / 缺失→三步诊断>（① `run_batch.log` 是否有 `[d2] self-check wc -l=… meta.events=…`；② `emit_run_meta.py` 退出码；③ meta 是否 0 字节 → run_batch 对此有 exit 7 硬闸）

## 8. 截图取证

**截图入口 = `code/frontend/tools/screenshot.sh`（≡ `shot.py` 默认带空白校验路径）**
**禁用 `code/frontend/tools/dialogue_shots.sh`**：其 `:64` 硬编码 `--no-blank-check`，会绕过 `shot.py:157-158` 的 `_BLANK_FRAC=0.5` 空白门（这正是 R21 那 8 张被审计的结构性问题，本批不得踩）。

```
$ cd code/frontend && bash tools/screenshot.sh <out.png> <log> <round> 1200x800
<待填充：SHOT OK 原文（elapsed / mean_brightness / max_color_frac / blank_retries / blank_cumulative）>
```
- 路径：<待填充>；`sha256 = <待填充>`
- 命名：`r10e2e_n16r60_seed42_sha8-625187c3_day1r<rr>.png`
- 判定：`mean_brightness` / `max_color_frac` / `blank_retries` 见原文；若出现 `_blank_check_failed` ⇒ **该图不作证据**，改选回合或换视图重出，并在本节记录尝试次数与弃用原因。

## 9. 不做的事（纪律留痕）

- 跑批期间**未修改** `code/life` / `code/orchestration` / `code/config` / `code/engine` 及任何被本批读入的文件
- 未在批次内或监控中使用长 sleep 轮询；完成判定只看产物文件与 `run_batch.rc`
- 未静默缩规模、未改用 mock、未跳过 `obs llm-cost` 验真
- 未用 `dialogue_shots.sh` / `--no-blank-check` 出图
- **不下效果结论**（本文件只交读数与验真，效果判断由报告侧承接）
