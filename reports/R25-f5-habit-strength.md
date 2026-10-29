# R25 · F-5 作息/习惯强度（口径下沉版）：把「闲」排进作息表

> **一句话结论**：单 env 开关 `HITT_LIVING_SLOT`（默认关 = 逐字节等价）把每天 `evening`（+ 周末 `afternoon`）固定成生活时段后，**活动作息结构层**的指标由 OFF 变到 ON：`M3`（闲时段命中率）0.65625 → **1.000**（64/64）、`M2`（休闲频次）1.328125 → 2.65625（**ratio 2.000**）、`M1`（生活类活动人均日频）0.421875（27/64）→ 0.890625（57/64），**Δ=+0.46875 < +0.50 阈值**。⇒ 按冻结卡记「**部分有效（未达阈值）**」，**PASS 不成立**。机制已落地（M3=64/64），但 M1 的绝对门槛落在有界指标上、结构上界 +0.594 使门槛几乎不可达；属**判据设计缺陷，非功能无效**。
>
> **本轮产出定义**：「**机制落地 + 指标设计缺陷取证**」。
> **证据等级**：`probe`（准入 `REJECTED`，失败项 B-19/B-20/B-21 属 `--mock` 特征）。**不得**当证据级单独结论、**不得**与真 LLM 批次横比。
> **真 LLM 调用验真：不适用（离线确定性路径）**；替代证据 = 两臂各两次同参重跑 `run.jsonl` sha256 相等 + `cmp` IDENTICAL（§5）。
> **禁止表述**：「居民对话更有生活气息了」「真 LLM 已验证」「AI 小镇变活跃了」。本轮**只覆盖 planner 层作息/习惯结构指标**，**不覆盖 LLM 生成侧对话自然度**。

---

## ⓪ 口径与选址

### 0.1 选址理由（报告为何放 `reports/`）

仓库**没有** `docs/reports/` 约定（`docs/` 下只有 `forensics/`）；既有的报告族全部在仓库根 **`reports/`**，且 `reports/README.md` 逐行登记每份报告（编号 / 一句话内容 / 状态），惯例是「每份报告独立可读、自带证据索引与复现命令」。既有同类路径举例（均为本仓库已入库文件）：

- `reports/R23-solitude-idle.md`（把「独处/空闲」从无判据读数补成三个可复算尺子）
- `reports/R4-life-texture.md`（「生活气息」F 系列维度表，本轮 F-5 定义即出自此文件 `:41-42`）
- `reports/CYCLE-30-20261030.md`（周期实验报告，固定五节体例）

故本轮沿用 `reports/`，编号取报告族下一个空位 **R25**（R1–R24 已占用，`R6` 空缺不复用），文件名 `R25-f5-habit-strength.md`，并在 `reports/README.md` 追加登记行。

### 0.2 五行冻结口径（本报告写作时刻实测）

| 项 | 值 | 取证方式 |
|---|---|---|
| 仓库根 | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment` | `git rev-parse --show-toplevel`（注意上级 `尝试/` 不是 git 仓库） |
| 工作树 | `.worktrees/life-habit-strength`（隔离 worktree，**主工作区未 checkout/stash/reset**） | 主树仍在 `feat/prompt-narration-toggle@d2a6fa9`，其 dirty 为既有脏 |
| base sha | **`d2d1993f842428692da457c4f0105d0787ae3a31`**（= `master` = `origin/master`） | `git rev-parse master` / `git ls-remote origin master` |
| head sha / 分支 | **`d356a5b6cb537dfb10006dfcb723654b717e6371`** / `feat/life-habit-strength` | `git rev-parse HEAD` |
| 两臂运行树 | 均为 `d356a5b`（`code/` git tree sha `f008714f…`），唯一差异 = `HITT_LIVING_SLOT` | 见 §3 开关真值表 |

### 0.3 版本与身份链（引用任何读数必须附带的三个 sha）

| 对象 | 值 | 算法 / 说明 |
|---|---|---|
| `code/` **git tree object sha** | `d356a5b:code` = **`f008714f158b261c368678b43d920b1ebe0e1693`**；`b21a79d:code` / `2a327dd:code` 同值；基线 `d2d1993:code` = `6d96916da9db954e3a68ab7d436462b3e5325781` | `git rev-parse <rev>:code`。**tree sha 相等 = 目录内容逐字节等价**，不依赖 `diff` 输出为空这种间接判法 |
| `code/` 子树**指纹**（另一算法） | `d356a5b` = `c4cc72b95773d53b8f4e412fdce38f8116d561dc966bb22a7c1a35a2a146a717`；`d2d1993` = `38cdd4a77a3d4b4143080bc532747d77320fb6a28d87446fe47ec45fc423de63` | `git ls-tree -r <rev> -- code/ \| sha256sum`。**注意：这不是 `git rev-parse HEAD:code` 的结果，与上一行 `f008714f…` 是两种不同算法，二值不可互换、不可并列当作同一栏** |
| 读数器 | `tools/habit/habit_readings.py` = **`c695fce4c2c5aa835c7ed526dbaf1e37bdc8d9fd8cf730a07b79a74d4de5560a`** | `2a327dd` 定稿，`d356a5b` 未改。**换版本 = 口径变更，不是行为变更**；旧版会给 `M3=0.203125` |
| 口径卡（预登记） | `v2/refs/round1-prereg-F5.md` = **`7314adec37ecacdb2dfbb293fbfa3581f00265d68d2e0329c7682dd79d7d2b9e`** | 与 `team-workspace/round1-prereg-F5.md` 逐字节一致（本报告实测两值相同） |

---

## ① 维度与选择理由

**本轮只推进一个维度：F-5 作息/习惯强度（口径下沉：作息里有没有「闲」）。**

### 1.1 为什么是 F-5

- **可观测**：数据直接来自 `run.jsonl` 的 `ACTIVITY_STARTED` 事件（字段 `agent_id/day/slot/place/activity_type/template`），全部机械可算，无需人工判读、无需 judge。
- **可归因**：机制改动集中在 planner 的「选什么活动」这一层，单 env 开关，默认关逐字节等价 ⇒ 单变量对照成立（§3、§5）。
- **可复用**：不改 `activity_templates.json`（它在 `engine/version.py::FINGERPRINT_FILES` 内）⇒ 两臂 `engine_version` 指纹一致。

### 1.2 为什么口径必须「下沉」

官方 F-5 的定义是「同一 agent 在同一 `(slot, place)` 覆盖 ≥3 天」，但该指标在既有批次上**已饱和**：`habit_strength` 87.5%（A0）→ **100.0%**、`max_repeat_days_mean` 7/7（`reports/R4-life-texture.md:41-42` 定义、`:61`、`:107` 读数）。饱和源是 **`night` 全员同睡同地点**（本轮 `slot×template` 分布中 night 的 `(none)=64/64`），白天的差异被夜晚的常数项吃掉 ⇒ 该指标在本规模**无可观测余量**，**不得**把官方 F-5 数字当效果证据。

⇒ 本轮把口径下沉为：**白天段 + 作息里有没有「闲」**（M1/M2/M3 + 守卫 G1–G4，见 §6.1）。官方 `habit_strength` 只作**对照读数**（本报告附于 §6.1 表末，并标注饱和源），**不参与 PASS**。

### 1.3 为什么是 r48（而非 r24 / r60 / r84）

| rounds | 覆盖 day | 官方 F-5 `habit_strength` | 结论 |
|---|---|---|---|
| 24 | day0–1（2 天） | **0/16** | 「≥3 天」数学上不可达 ⇒ **结构性恒 0**，跑出来也只能说「无法回答改没改」 |
| **48** | **day0–3（4 天）** | **13/16 = 0.8125** | **本轮采用**：官方定义不变、仍有余量；分母 `16×4=64` ≥30 满足 R4 §0 门槛；mock 耗时约 57s |
| 84 | day0–6（7 天） | 16/16 = 1.0 | 饱和、无余量 |

（该表来自 `team-workspace/round1-baseline-F5-metrics.md` §0① 的实测，`repo-analyst` 在 `d2d1993` 离线 mock 得到。）

> 与冻结卡的偏差：口径卡 §4 原本冻结 `rounds=60`（5 天，分母 80），leader 06:12 裁决改 48（4 天，分母 64）。该偏差**未经 AMENDMENT 正式改写**，属计划-执行脱钩，已在 §7 与 §9 逐项登记。

---

## ② 改动文件清单

分支 `feat/life-habit-strength`，`d2d1993..d356a5b` 共 **5 个提交**（`git log --oneline d2d1993..d356a5b`）：

| 提交 | 类型 | 内容 |
|---|---|---|
| `c1bfee5` | docs | 预登记入库（`v2/refs/round1-prereg-F5.md`）——**先于任何代码改动**落盘 |
| `b21a79d` | feat | 机制：`code/life/planner.py` 增 `HITT_LIVING_SLOT`，闲时段优先排既有生活类模板 + 单测 + 黄金夹具 + 读数器 |
| `2a327dd` | fix | 读数器口径自洽（M3 用机制候选池 `LIVING_POOL`；新增载体口径 M1'） |
| `992b6ae` | docs | AMENDMENT-3 落盘 + `tools/habit/g2_attribution.py`（G2 归因取证器） |
| `d356a5b` | docs | AMENDMENT-3 补 A3-5（读数器版本钉死 + M3 判据补全） |

逐文件（`git diff --stat d2d1993..d356a5b`）：

| 文件 | 状态 | 改动 |
|---|---|---|
| `code/life/planner.py` | M（+96/−23） | 新增 `LIVING_ENV`/`_LIVING_CANDIDATES`/`living_enabled()`/`_living_candidates()`；`plan_slot()` 在「闲时段」插入生活类优先分支并跳过 1/3 频率门；其余路径不变；把 eligibility 循环与「选址出计划」抽成 `_eligible()`/`_materialize()`（语义不变，由 2688 组黄金夹具逐行证明） |
| `code/life/tests/test_habit_living_slot.py` | A（8 用例） | OFF 与 baseline 夹具逐行相同；ON 只改闲时段；确定性；频率门绕过有界；无候选时回落 |
| `code/life/tests/support/planner_off_golden.json` | A（460K） | **黄金夹具**：2688 组 `(agent×day_type×slot×slot_id×cash×focus)` → `plan_slot` 输出，由**直接执行 `d2d1993` 源码**生成，不是手抄 |
| `tools/habit/gen_planner_golden.py` | A | 生成/校验夹具（`--check` 复核 OFF 是否漂移） |
| `tools/habit/habit_readings.py` | A | 零依赖只读读数器（M1/M1'/M2/M3/M4 + G1–G4，输出分子/分母/公式/`run.jsonl` sha256/复算命令 + OFF→ON delta） |
| `tools/habit/g2_attribution.py` | A | G2 差额归因取证器（本轮 G2 diff=0，未触发） |
| `v2/refs/round1-prereg-F5.md` | A | 口径卡入库副本（含 AMENDMENT-1/2/3） |
| `reports/R25-f5-habit-strength.md` | A | **本报告** |
| `v2/evidence/f5_round1/**` | A | **本报告全部截图与证据文件**（5 PNG + 18 件原始输出，见 §8） |

**没有改**：`activity_templates.json`、`engine/`、`orchestration/`、`config/`、任何提示词、任何 LLM 调用路径。

---

## ③ 开关真值证明（主表）

唯一变量 = `HITT_LIVING_SLOT`。默认不设 = 关（`0`/`off`/`no`/空亦为关），`1`/`true`/`yes`/`on` = 开。取证来自执行层 `/proc/<pid>/environ`（不是「启动命令里写了」，而是**进程实际环境**）：

| 臂 | orchestration_pid | captured_at | environ 中 `HITT_LIVING_SLOT` | cgroup | cmdline 关键段 |
|---|---|---|---|---|---|
| **OFF** | 2299621 | 2026-10-30T06:23:37+08:00 | **不存在该行**（期望事实） | `0::/system.slice/jiuwenswarm.service` | `--seed 42 --agents 16 --rounds 48 --flush-every 2` |
| **ON** | 2304542 | 2026-10-30T06:25:31+08:00 | **`HITT_LIVING_SLOT=1`** | 同上 | 同上 |

原始文件：`v2/evidence/f5_round1/official/off/switch_proof.txt`、`.../on/switch_proof.txt`。

---

## ④ 可复算命令与关键原始输出

### 4.1 跑批命令（两臂串行，唯一差异是 env）

```bash
cd /tmp/f5-branch            # git clone --shared <主树> /tmp/f5-branch && git checkout d356a5b
env -u HITT_LIVING_SLOT bash tools/d2/run_batch.sh --mock \
    --out-dir /tmp/r1runs/d356_off --seed 42 --agents 16 --rounds 48 --flush-every 2
env      HITT_LIVING_SLOT=1 bash tools/d2/run_batch.sh --mock \
    --out-dir /tmp/r1runs/d356_on  --seed 42 --agents 16 --rounds 48 --flush-every 2
```

### 4.2 四重判定原始行（`official/four_fold.txt`）

```
---- off ----
rc=0
[d2] run: python3 -m orchestration run --life --seed 42 --agents 16 --rounds 48 --out /tmp/r1runs/d356_off/run.jsonl --flush-every 2
[meta] events=82906 llm_calls=2646 cached_ratio=0.5276 provider={'mock': 2646} model={'mock-1': 2646}
[meta] seed_in_log=42 n_in_log=16 rounds_effective=48
[meta] OK (mock 臂：跳过真跑判定)
[d2] self-check wc -l=82906 meta.events=82906
[d2] OK
---- on ----
rc=0
[meta] events=80300 llm_calls=2653 cached_ratio=0.5273 provider={'mock': 2653} model={'mock-1': 2653}
[meta] seed_in_log=42 n_in_log=16 rounds_effective=48
[meta] OK (mock 臂：跳过真跑判定)
[d2] self-check wc -l=80300 meta.events=80300
[d2] OK
```

四重判定 = ① `rc=0` ② `meta.json` 非空 ③ `[d2] self-check` 两数相等 ④ `[d2] OK`。两臂四跑次（OFF×2、ON×2）全过。

### 4.3 串行证明

- 手写 `pgrep` 三重（bracket 防自匹配 + 排除自身祖先链）：OFF 起跑前 06:23:36 三 pattern 全 **0 命中**；
- 仓库自带闸：`PASS preflight sha=d356a5b6(HEAD) ts=2026-10-30T06:23:36+08:00 concurrency=0 frozen_tree=clean`；
- 时间线首尾相接、无并发：OFF#1 06:23:36–06:24:32、OFF#2 06:24:33–06:25:30、ON#1 06:25:31–06:26:30、ON#2 06:26:31–06:27:27，`rc` 全 0。

> 旁证（闸确实会拦）：06:14:38 有一批次被 `[preflight] FAIL exit=9 reasons=concurrency:orchestration_run=1 concurrency:run_batch=3` 拒绝，**该批次未启动**，随后撤销重排。这不是本轮批次的一部分，只作「串行闸有效」的证据。

### 4.4 指标复算（唯一真源命令）

```bash
cd /tmp/f5-branch
python3 tools/habit/habit_readings.py \
  --run OFF=/tmp/r1runs/d356_off --run ON=/tmp/r1runs/d356_on \
  --out-json v2/evidence/f5_round1/official/habit_readings.json
```
关键原始输出见 `official/habit_readings_summary.txt`（本报告 §6.1 表的数值逐字来自该文件）。

---

## ⑤ 确定性证明与等价性交叉验证

### 5.1 确定性证明（路径 A 替代「真调用验真」的唯一证据）

```
$ env -u HITT_LIVING_SLOT bash tools/d2/run_batch.sh --mock --out-dir /tmp/r1runs/d356_off       --seed 42 --agents 16 --rounds 48 --flush-every 2
$ env -u HITT_LIVING_SLOT bash tools/d2/run_batch.sh --mock --out-dir /tmp/r1runs/d356_off_rerun --seed 42 --agents 16 --rounds 48 --flush-every 2
OFF#1 vs OFF#2:  IDENTICAL (cmp rc=0)

$ env HITT_LIVING_SLOT=1 bash tools/d2/run_batch.sh --mock --out-dir /tmp/r1runs/d356_on        --seed 42 --agents 16 --rounds 48 --flush-every 2
$ env HITT_LIVING_SLOT=1 bash tools/d2/run_batch.sh --mock --out-dir /tmp/r1runs/d356_on_rerun  --seed 42 --agents 16 --rounds 48 --flush-every 2
ON#1 vs ON#2:    IDENTICAL (cmp rc=0)

97b8f62498fd0d863d5707aefbe239bce8f329bc74bafcf1c2035f4cd743d820  d356_off/run.jsonl
97b8f62498fd0d863d5707aefbe239bce8f329bc74bafcf1c2035f4cd743d820  d356_off_rerun/run.jsonl
2154598d620a626c894a8c9f77b166f6dd0dd8b8267a984168d2070f797a1ce1  d356_on/run.jsonl
2154598d620a626c894a8c9f77b166f6dd0dd8b8267a984168d2070f797a1ce1  d356_on_rerun/run.jsonl
97b8f62498fd0d863d5707aefbe239bce8f329bc74bafcf1c2035f4cd743d820  d2d1993_r48/run.jsonl
```

完整：`official/determinism.txt`。**两臂各做一次两次同参重跑，sha256 两两相等、`cmp` IDENTICAL。**

### 5.2 等价性交叉验证（「默认关 = 与 `d2d1993` 逐字节等价」）

| 维度 | OFF 臂（`d356a5b`） | 锚点（`d2d1993`，repo-analyst） | 对齐 |
|---|---|---|---|
| `code/` tree sha | `f008714f…` | `6d96916d…`（不同，含 `planner.py` +96/−23） | 期望不同 ⇒ 靠「默认关等价」消除 |
| seed / agents / rounds / flush-every | 42 / 16 / 48 / 2 | 同 | ✅ |
| `--mock` | 是 | 是 | ✅ |
| 开关 | 无该 env 行 | 同（默认关） | ✅ |
| **`run.jsonl` sha256** | **`97b8f62498fd0d863d5707aefbe239bce8f329bc74bafcf1c2035f4cd743d820`** | **同值** | ✅ **成立** |

⇒ 「树不同、整跑输出逐字节相同」证明：不设 `HITT_LIVING_SLOT` 时行为与基线等价，故 OFF 臂可作 `d2d1993` 的代理，单变量成立。（另有 `b21a79d` 树预跑、`d2d1993` 独立克隆重跑两次旁证，见 `official/determinism.txt` 末行。）

### 5.3 真 LLM 调用验真：不适用（离线确定性路径）

走**路径 A（`--mock`）**，不产生任何真实 LLM 调用（`obs llm-cost` 原始输出 `official/llm_cost_{off,on}.json`）：

| 臂 | `total.calls` | `by_provider` | `openai_compat` 计数 | `provider_guard.ok` | rc |
|---|---|---|---|---|---|
| OFF | 2646 | `{"mock": 2646}` | **0** | `false` | 1 |
| ON | 2653 | `{"mock": 2653}` | **0** | `false` | 1 |

口径说明：① 该工具**只有 calls/cached/tokens/degraded/provider 分布，没有任何计价字段** ⇒ 「花费」无口径，本报告**不换算、不估算任何金额**；② `tokens_total` 20000 / 20064 是 mock 客户端的**桩计数**（`tokens_in == tokens_out`），不代表真实计费 token，**不得用于成本估算**；③ `rc=1` 是 `--require-provider openai_compat` 的**预期失败**（本轮本就没有真调用），不是「跑批失败」。

---

## ⑥ 指标前后对比与口径

### 6.1 主表（读数器 `c695fce4…`；口径卡 `7314adec…` + AMENDMENT-3）

| 指标 | 口径（分子/分母） | OFF（无 env 行） | ON（`HITT_LIVING_SLOT=1`） | Δ / 比值 | 判据 | 结论 |
|---|---|---|---|---|---|---|
| **M1** 生活类活动人均日频 | `#{template∈LIVING}` / `agents×days`(16×4=64) | 0.421875（**27/64**） | 0.890625（**57/64**） | **+0.46875**（×2.111） | ≥ +0.50 | **未过**（差 0.03125） |
| **M2** 休闲人均 5 天频 | `#{activity_type=="leisure"}` / 64 ×5 | 1.328125（17/64×5） | 2.65625（34/64×5） | ratio **2.000** | ≥1.5×OFF | **过** |
| **M3** 闲时段命中率（= m） | `#{(agent,day): 该日 evening 命中 LIVING_POOL}` / 64 | 0.65625（**42/64**） | **1.000**（**64/64**） | +0.34375 | ≥0.60 **且** ≥0.70625 | **过（双条件都过）** |
| M4 白天作息稳定性（描述性） | 众数天数/观测天数 的均值 | 0.578125 | 0.515625 | −0.0625 | 仅描述 | — |
| M1' 载体口径（**不参与 PASS**） | `#{template∈LIVING_POOL}` / 64 | 0.921875（59/64） | 1.265625（81/64） | +0.34375 | 仅附带 | — |
| **G1** 活动多样性 | 每 agent `#distinct(slot,place,activity_type)` 均值 | 8.875 | 9.625 | +0.75 | ≥0.95×OFF（8.431） | 未击破 |
| **G2** 活动总量 | `#ACTIVITY_STARTED` | **256** | **256** | **diff 0** | `==16×days×4 = 256` | 守恒 |
| **G3** 生产性占比 | 生产类 / 总量 | 0.382812（98/256） | 0.382812（98/256） | 0.0 | ≥OFF−0.05 | 未击破 |
| **G4** 模板命中率 | 非空 template / 总量 | 0.492188（126/256） | 0.578125（148/256） | +0.0859 | ≥OFF−0.02 | 未击破 |
| 对照：官方 `habit_strength` | 官方 F-5 口径（同 (slot,place) ≥3 天） | 0.8125（13/16） | 1.0000（16/16） | +0.1875 | **不参与 PASS** | 对照读数 |
| 对照：`max_repeat_days_mean` | 同上 | 3.25 | 3.6875 | +0.4375 | 不参与 PASS | 对照读数 |

> 官方两项的**饱和源必须与该值同写**：`night` 全员同睡同地点（本轮 night 的 `slot×template` 分布 `(none)=64/64`）⇒ 该指标在本规模无可观测余量，因此只作对照，不进判定。

### 6.2 判定（按冻结卡 + AMENDMENT-3）

- **PASS 四条**：`M1` ✗（+0.46875 < +0.50）、`M2` ✓、`M3` ✓（双条件）、守卫 ✓ ⇒ **不构成 PASS**。
- **FAIL 分层**：`M1` 提升落在 `[+0.10, +0.50)` ⇒ 按卡记「**部分有效（未达阈值）**」。**不是**「机制未生效」（那要 < +0.10），也没有守卫击破（不属于「不构成净改善」）。

### 6.3 M1 结构上界分析（Leader 解析式 + 实测口径）

**解析近似式**（Leader 06:24 给出，**近似、经实测判定为高估 0.125**）：

```
M1(ON) ≈ [17 + (1−m)·10 + m·64·0.75] / 64          # m = 闲时段命中率 = M3
```

> ⚠️ 该式在「**池内权重均匀 6/8 = 0.75**」这一简化假设下成立，**实测不成立**（见本节末实测段）。故下方五档增量表**只作敏感性参照，不是权威上界**；权威值为实测 **+0.46875**。

| m = M3 | 0.70625 | 0.75000 | **0.84100** | 0.90000 | 1.00000 |
|---|---|---|---|---|---|
| ΔM1 | +0.419 | +0.445 | **+0.500（过线临界）** | +0.534 | +0.594（理论上界） |

分量来源（OFF 臂 `run.jsonl`，sha `97b8f624…`）：`M1_OFF = 0.421875` = morning LIVING `17/64` + evening LIVING `10/64`；afternoon/night 的 LIVING 命中恒为 0；evening 的 `LIVING_POOL` 命中 `42/64`（= `M3_OFF`）；`LIVING_POOL` 内落进 `LIVING` 计数集的权重取 `6/8 = 0.75`。

⇒ **`M1` 过线需 m ≥ 0.841，而 `M3` 的判据只要 0.70625** ⇒ 「**M3 过而 M1 不过**」是**算术默认结果**：判据把最难的那条（`+0.50` 绝对门槛）压在一个**有界指标**上，`+0.50` 吃掉了理论上界的 **84%**。

**实测印证（比解析式更保守）**：ON 臂 `M3 = 1.000`（64/64，机制 100% 落地），但 evening 的 64 个槽实测分布是 `contest 17 / creative_collab 7 / gift 16 / ice_break 6 / rel_maintain 6 / select_location 4 / whisper 8`，其中落进 `LIVING` 集合的 = 17+7+6+6+4 = **40/64 = 0.625**（`gift 16 + whisper 8 = 24/64` 属 `LIVING_POOL` 但不在 `LIVING` 集合内）⇒ 实际权重 **0.625 而非 0.75**（模板是按 eligibility + 人数 + 现金等条件确定性筛选，不是 8 项均匀）。故：

```
M1_ON = (17 + 40)/64 = 57/64 = 0.890625 ；Δ = (40 − 10)/64 = 30/64 = +0.46875
```

实测上界比解析式的 +0.594 低 0.125，差在「池权重均匀」这一简化假设；两者不矛盾。

**本轮定性（原文，不改写）**：

> "机制已落地（M3=64/64），但 M1 绝对门槛落在有界指标上、结构上界 +0.594 使门槛几乎不可达；属**判据设计缺陷，非功能无效**。"

**更强的一条结论（以实测为权威值）**：

> 在机制**完全激活**（`M3 = 64/64`，每个 `agent·day` 的 evening 都命中闲时段池）的情况下，`M1` 仍只有 **0.890625**，**距 `+0.50` 门槛差 0.03125**。即在当前 `LIVING` 计数集定义与池构成下，**该机制的 `M1` 增量上界（实测）就是 `+0.46875`，门槛 `+0.50` 在本机制下不可达** ⇒ 判据设计缺陷，与实现质量无关。

> 这比「结构上界很接近门槛」更有力：**不是差一点没运气好，而是机制跑满也过不了**（`evening` 落进 `LIVING` 需 `≥42/64 = 65.6%`，实测 `40/64 = 62.5%`；`gift/whisper` 共 24/64 属 `LIVING_POOL` 但不在 `LIVING` 计数集内，这是结构性的，不是随机波动）。
>
> **必须并列的两条限制**（防止被读成定论）：① **单 seed 无方差**——不能据此断言「再跑一次必不过」；② **4 天窗口**——更长窗口（r60/r84）下 `M1` 是否过线**未验证**。

### 6.4 判据可自算说明

- `M3` 的双条件下限 `0.70625 = 45.2/64` **非整数倍** ⇒ 唯一判定点是 hits **45 ↔ 46**：`45/64 = 0.703125`（不达标）、`46/64 = 0.71875`（达标）。本轮 ON 为 64/64，远离判定点。
- M3 单条下限 `≥0.60 = 38.4/64` ⇒ 护栏 **≥39/64（0.609375）**；OFF 自身 42/64 已在该线之上，故单条下限判别力弱，这正是 AMENDMENT-3 增设「≥`M3_OFF`+0.05」的原因（该 +0.05 标注为**最小可判别阈值，非效应量预期**）。

---

## ⑦ 预登记时间线与「没有事后调参」的凭据

| 版本 | 文件 sha256 | 说明 |
|---|---|---|
| `c1bfee5` 副本 | `c788a8a4278779cef87a73ff7a0dd5d7ff61ef9a2ede54803061a30d2a545d1b` | 预登记首次入库，**早于任何代码改动** |
| `2a327dd` | `83b3ec69c2440aaed2f15db590178491c09ee41fb5f1d8dcf349bb0c9a181f0d` | 口径自洽 |
| `992b6ae` | `15f4c848556e52aee2b6d3f1f57ee60975815d27a008f0b239f59499db61122c` | AMENDMENT-3（G2 按天 / M2 外推加注 / M3 双条件 / G2 语义） |
| `d356a5b` | **`7314adec37ecacdb2dfbb293fbfa3581f00265d68d2e0329c7682dd79d7d2b9e`** | AMENDMENT-3 补 A3-5（读数器版本钉死 + M3 判定点） |

复算：`git show <sha>:v2/refs/round1-prereg-F5.md | sha256sum`（本报告实测，四值如上；`d356a5b` 与 `team-workspace/round1-prereg-F5.md` 逐字节相同）。

- **公式 / 阈值 / 样本量冻结时刻：`2026-10-30 06:06:22`**（口径卡 §7，`stat -c '%y'` 留痕）。
- **AMENDMENT-2**：改的是 §2 机制作用时段（`dow%3` 轮转 → 每天 evening + 周末 afternoon），**§3 公式 / §4 样本量 / §5 阈值一字未改**，理由是静态复算发现原方案必然击破自设 `G3` 守卫，且发生在任何 ON 读数之前。
- **AMENDMENT-3**：修 3 处与 r48 不相容的判据（G2 期望值按天、M2 外推加注、M3 双条件）+ 1 处语义澄清；`M3_OFF=0.65625` 取自 **OFF 基线读数**，**不是** ON 读数；发生在**任何 ON 读数之前**。
- **决策记录 D-1**（`round1-impl-handoff.md` §9）：leader 裁决「走 A，阈值一字不改」；该决策**晚于** OFF 臂可能已起跑之时 ⇒ 因此**不改判据**，而不是「看到 ON 结果再改」。
- **决策记录 D-2**：「同代码 ⟺ `code/` tree sha 相等」（登记 06:25:45），早于 ON 读数。

---

## ⑧ 截图（两类分节）

> 本环境**无帧缓冲截屏能力**（无 `xterm` / `import` / `scrot`；跑批经 `setsid` 启动本身无 TTY）。因此终端证据一律用「**终端输出渲染图**」，图注固定声明「本环境无帧缓冲截屏能力」。所有图片已随本报告提交在 `v2/evidence/f5_round1/shots/`。

### 8.1 第一类：真实浏览器渲染截图（真 UI）

真浏览器 `/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome`（`HITT_CHROME` 指定）；渲染器 `frontend/tools/shot.py`（等 `window.__RENDER_READY__` 才拍，自带空白帧检测）。

| 文件（仓库内路径） | 数据源 | 产物 sha256 | 检查 |
|---|---|---|---|
| `v2/evidence/f5_round1/shots/ui_off_r48_round12.png` | OFF 臂 `run.jsonl`（`97b8f624…`） | `88dc34f399ad049f984883e152850ed92cd7a376cbeeb23f6b9b9a62768f4473` | `SHOT OK … blank_retries=0/2`，mean_brightness=86.4，max_color_frac=9.10% |
| `v2/evidence/f5_round1/shots/ui_on_r48_round12.png` | ON 臂 `run.jsonl`（`2154598d…`） | `7f931a72514da40641eeaf6b675398519e503b8fec5eb0e90e08fbea7a450a64` | `SHOT OK … blank_retries=0/2`，mean_brightness=86.4，max_color_frac=9.18% |

生成命令：

```bash
cd /tmp/f5-branch/code && setsid python3 frontend/tools/serve.py --host 127.0.0.1 --port 8851 &
cp /tmp/r1runs/d356_off/run.jsonl frontend/sample/r1_off_r48.jsonl
cp /tmp/r1runs/d356_on/run.jsonl  frontend/sample/r1_on_r48.jsonl
python3 frontend/tools/shot.py --chrome /root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome \
  --url "http://127.0.0.1:8851/?log=sample/r1_off_r48.jsonl&round=12&still=1&audit=1" \
  --out <artifacts>/shots/ui_off_r48_round12.png --width 1500 --height 950 --timeout 120
```

**可核对性（本报告作者实测复核）**：ON 图右侧观演台审计面板显示「累计事件 **80300**」，与 ON 臂 `meta.events=80300` 一致；OFF 图同构为 82906 ⇒ 图像确实渲染自本轮日志，不是历史图复用。两张图的地图/对话流/节律三视图均可辨（非空白帧）。

### 8.2 第二类：终端输出渲染图（非帧缓冲）

渲染器 `term_render.py`（真 Chromium + Noto Sans Mono，**逐字节**读取源文件、不做编辑；页脚固定声明「本环境无帧缓冲截屏能力」）。

| 文件（仓库内路径） | 源文件 | 源 sha256 | 产物 sha256 |
|---|---|---|---|
| `v2/evidence/f5_round1/shots/term_fourfold.png` | `official/term_src_fourfold.txt`（= `four_fold.txt` + `determinism.txt` 逐字节拼接） | `d2370b7d5a5e3074bd1a517ca9ccb966cf56b0a2e0ba80753e52686a6f371819` | `2dc3477261d65e20138ff5f6eea853528f78ffc494c661dd4bdb5e464f3f15c8` |
| `v2/evidence/f5_round1/shots/term_llmcost.png` | `official/term_src_llmcost.txt`（= 两臂 `llm_cost_*.json` 逐字节拼接） | `f8a3d7e12dc858f01ddc0acaf61aa9cbd3e89af47e2c1b2ad55c9ff1fb85d081` | `45e6fde0d74c4d26a0d9d10d38bbe52c79a1f3dd7b54647e2c6681e35f501447` |
| `v2/evidence/f5_round1/shots/term_metrics.png` | `official/term_src_metrics.txt`（= `habit_readings_summary.txt` 逐字节） | `452ebf7d7da1547501c41fb00e14bb97257eea7d2d5794889c9fd13f435529a2` | `53430910d0a5548c4bfd56bb74e93f1929838646e3e73cbd884303cd60673555` |

生成命令（三张同构，换 `--src/--out/--title`）：

```bash
python3 term_render.py --src <artifacts>/official/term_src_fourfold.txt \
  --out <artifacts>/shots/term_fourfold.png \
  --title "终端输出渲染图：fourfold（r48 两臂，d356a5b，mock 路径 A）"
```

图注声明：**本环境无帧缓冲截屏能力**；图为终端输出渲染图（非截屏/screenshot）。

---

## ⑨ 异常、偏差与未解释项（如实）

1. **事件总量差异（非判据，但必须披露）**：OFF `events=82906` vs ON `80300`（−2606），而 `ACTIVITY_STARTED` 两臂均 **256**（G2 守恒）。差异集中在下游事件：`MEMORY_WRITE −993`、`OBSERVATION −997`、`RELATION_CHANGE −536`、`NEED_UPDATE −97`、`LLM_JUDGMENT −51`、`MSG_DM −24`，同时 `SCORE_POSTED +136`、`MSG_GROUP +65`、`GROUP_CREATED +28`、`RANKING_EMITTED +17`、`SKILL_OUTPUT +7`（赛事类活动带来的新事件族）。明细：`official/event_type_diff.txt`。
   ⇒ 判读：这是「把 evening 换成比赛/串门类活动」后的下游结构差异，**不是丢事件**；但本轮**未**对「事件总量下降是否影响记忆/关系演化」做因果分析 ⇒ 列为本轮**未解释项**。**不得**宣称「无副作用」或「不影响记忆/关系演化」。
2. **`meta.json` sha 与锚点不同**（OFF `6615c514…` / ON `c8b9d51f…` vs 锚 `34b0c9c4…`）：`meta.json` 含 out-dir/路径/耗时等环境元数据 ⇒ **不参与等价性判定**；等价性只用 `run.jsonl` 原始 sha256。
3. **口径卡与执行参数脱钩**（计划-执行，须披露）：卡 §4 冻结 `rounds=60`（5 天、分母 80）、§5 冻结 `G2 == 16×5×4 = 320`；实际 `rounds=48`（4 天、分母 64、`G2 == 16×days×4 = 256`）。卡 §4/§5 未经 AMENDMENT 正式改写，属**计划-执行脱钩**，已由 AMENDMENT-3 只修 G2 期望值算式与 M3/M2 语义，**阈值未动**。
4. **`place is None` 口径瑕疵（既有，非本轮引入）**：`MSG_PUBLIC` 的 payload 无 `place`（`code/life/agent.py:1190-1200` 只在 private/place_group 分支写 `place`），这些消息落入 `(agent, slot, None)` 组。本轮 r48 占比 12.34%（49/397 的既有口径统计，取自基线文件）；**主判据保官方原口径**，剔除 `None` 的敏感性口径见基线文件（r48 下 `habit_strength` 仍 13/16，仅 `max_repeat_days_mean` 3.25 → 3.1875）。
5. **mock 定性（预期特征，不是系统缺陷）**：两臂 `admission.verdict = REJECTED`、`evidence_level = probe`，失败项 `B-19_provider_distribution`（`provider=mock`）/`B-20_model_no_mock`（`model=mock-1`）/`B-21_body_not_template`（mock 正文高度模板化，`L-6_dup_exact_rate=98.99%`）。**这是本轮选择零成本路径（路径 A）的结果，不是系统缺陷**；该批**不得**当证据级，**不得**与真 LLM 批次横比。
6. **`pgrep` 假阳性事故（已修正）**：早期把 pattern 写在命令行里导致 `pgrep -f` 命中自己的 shell；改为「pattern 放进脚本文件 + 排除自身祖先链」后归零。本报告引用的 `pgrep_proof.txt` 是修正后的干净版本。

---

## ⑩ 未验证项与风险

1. **不覆盖 LLM 生成侧对话自然度**：本轮未触发真实 LLM 调用 ⇒ 结论**只覆盖 planner 层作息/习惯结构指标**。F-5 改的是作息模板；**对话侧有没有变得更「有人味」，本轮根本没测**。
2. **`probe` 级不可作证据级单独结论**：`--mock`（`RuleBasedLLM`）与真实 LLM 的 weekly focus 标签不同（代码注释明示），换真 LLM 后 planner 的实际选点可能变化，本报告数值**不可外推**到真 LLM 批次。
3. **长窗口未验证**：本轮只有 4 天窗口（r48）；`M2` 的 ×5 是**4 天速率外推**，与 R23「5 天实测 1.44 次/人/5 天」**非同口径**，仅作量级对表（1.328 vs 1.44 同为「每天约 0.26–0.29 次/人」量级）。r60/r84 下 M1 是否过线**未验证**。
4. **单 seed、无方差**：只跑 seed=42，无跨 seed 方差；`M1` 距阈值仅差 **0.03125**，**不得**断言「再跑一次必过」或「必不过」。
5. **事件总量差异的因果**（§9.1）**未测**：对记忆/关系演化的影响本轮未做分析。
6. **`meta.code_sha` 的语义**：`meta.json::code_sha` = 生成 meta 那一刻的 HEAD，**不是**起跑钉住的 sha、也不是 `code/` 子树指纹（R21 已登记的已知语义）。本轮两臂 `meta.code_sha` 实际同为 `d356a5b`（`habit_readings.json::arm_meta` 实测），故此争议本轮不触发；但该语义本身仍是工具缺陷，**未修**。
7. **工作区既有脏未清理**：主工作区仍有既有 dirty（3 个已跟踪文件 + 大量未跟踪件），与本轮无关，本轮未触碰（跑批用 `git clone --shared` 隔离树）。

---

## ⑪ 下一步建议（round2）

1. **给 F-5 补 evidence 级读数**：round2 做 F-4 时**搭车**跑真 LLM 两臂（`n16r60` 量级），顺带取 F-5 的 evidence 级读数；届时必须用 `obs llm-cost --require-provider openai_compat` 真调用验真（`degraded=0`），并重跑本报告的 M1/M2/M3 口径。
2. **判据两条硬要求（写进下一份预登记卡）**：
   - **比值型判据**优先（如 `M2 ratio`、`M1 ratio`），不用落在有界指标上的**绝对门槛**；
   - **先算结构上界再定阈值**：阈值必须落在 `[0, 上界]` 的合理分位，并在卡里显式写出上界推导（本轮 `+0.50` 吃掉上界 84% 即反例）。
3. **修 `M3` 单条下限的判别力问题**：`≥0.60` 在 OFF 已 0.65625 时接近恒真，建议直接采用「相对 OFF 的最小可判别增量」作为唯一形式。
4. **口径卡与执行参数强绑定**：把 `rounds/days/分母/G2 期望值` 做成卡里的**派生式**（`agents × days × k`）而非写死数字，避免 r60→r48 这类脱钩再次发生。
5. **`place is None` 口径缺陷**：建议在 `MSG_PUBLIC` 的 payload 补 `place`（或统计层显式剔除并标注），使习惯统计不再混入「无地点」消息。
6. **事件总量差异的因果**（−2606 下游事件）值得单列一条诊断任务：换 evening 活动族后记忆写入/观察量下降是否影响后续演化，本轮未测。

---

## 附：复现步骤（另一人照抄即可重跑）

```bash
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
EVID=$REPO/.worktrees/life-habit-strength/v2/evidence/f5_round1

# 1) 隔离树（不碰主工作区 dirty 树）
git clone -q --shared "$REPO" /tmp/f5-branch && cd /tmp/f5-branch
git checkout -q d356a5b && git rev-parse HEAD      # 期望 d356a5b6cb537dfb10006dfcb723654b717e6371
: > code/.env.local                                 # 空占位（mock 不需要凭据）

# 2) 串行闸
bash tools/d5/preflight.sh --tag r1-off --quiet     # 期望 PASS concurrency=0 frozen_tree=clean

# 3) 两臂（串行；OFF 四重判定通过再起 ON），各跑两遍验确定性
env -u HITT_LIVING_SLOT bash tools/d2/run_batch.sh --mock --out-dir /tmp/r1runs/d356_off       --seed 42 --agents 16 --rounds 48 --flush-every 2
env -u HITT_LIVING_SLOT bash tools/d2/run_batch.sh --mock --out-dir /tmp/r1runs/d356_off_rerun --seed 42 --agents 16 --rounds 48 --flush-every 2
env      HITT_LIVING_SLOT=1 bash tools/d2/run_batch.sh --mock --out-dir /tmp/r1runs/d356_on        --seed 42 --agents 16 --rounds 48 --flush-every 2
env      HITT_LIVING_SLOT=1 bash tools/d2/run_batch.sh --mock --out-dir /tmp/r1runs/d356_on_rerun  --seed 42 --agents 16 --rounds 48 --flush-every 2
sha256sum /tmp/r1runs/d356_off{,_rerun}/run.jsonl /tmp/r1runs/d356_on{,_rerun}/run.jsonl   # 期望 97b8f624…×2、2154598d…×2

# 4) 指标（唯一真源）
python3 tools/habit/habit_readings.py --run OFF=/tmp/r1runs/d356_off --run ON=/tmp/r1runs/d356_on --out-json /tmp/habit_readings.json

# 5) 验真（期望 rc=1、provider=mock、openai_compat=0）
cd code && python3 -m obs llm-cost --log /tmp/r1runs/d356_off/run.jsonl --require-provider openai_compat --out /tmp/lc.json
```

---

## 附：本报告作者的独立复核（抽查，不依赖上游自述）

| # | 复核项 | 我的命令 | 结果 |
|---|---|---|---|
| 1 | 两臂 `run.jsonl` sha256 与重跑一致性 | `sha256sum /tmp/r1runs/d356_{off,off_rerun,on,on_rerun}/run.jsonl` + `cmp` | OFF 两次均 `97b8f624…`、ON 两次均 `2154598d…`，`cmp` 均 IDENTICAL ✅ |
| 2 | 指标独立复算 | `python3 tools/habit/habit_readings.py --run OFF=/tmp/r1runs/d356_off --run ON=/tmp/r1runs/d356_on --out-json /tmp/dr_recheck.json` | M1 27/64→57/64（Δ+0.46875）、M2 ratio 2.0、M3 42/64→64/64、M4 −0.0625、M1' 59/64→81/64、G1 8.875→9.625、G2 256=expected 256、G3 98/256 两支相同、G4 126/256→148/256 — 与 §6.1 表逐项一致 ✅ |
| 3 | 截图真实性 | `sha256sum` 5 张 PNG + 人工读图 | 5 个 sha256 与 §8 声明逐位一致；ON 图审计面板「累计事件 80300」= ON `meta.events` ✅ |
| 4 | 身份链 sha | `git rev-parse <rev>:code` / `git show <rev>:v2/refs/... \| sha256sum` | tree sha `f008714f…` 三处同值、基线 `6d96916d…` 不同；预登记四版 sha 与 §7 表一致 ✅ |
| 5 | 开关真值 | 读 `official/{off,on}/switch_proof.txt` | OFF「不存在该行」/ ON「HITT_LIVING_SLOT=1」，`captured_at` 与起跑时刻吻合 ✅ |

---

*本报告所有数字绑定：HEAD `d356a5b`、读数器 `c695fce4…`、口径卡 `7314adec…`、两臂 `run.jsonl` sha256 `97b8f624…` / `2154598d…`。凡未直接验证的条目已在 §⑩ 标注。*

---

## ⑫ 合入记录（可复现：在哪个路径、哪个分支、基于哪个 sha 完成合并）

> 本节由交付方（delivery-reporter）在合入后补记；正文所有验证结论与读数不受本节影响。

### 12.1 边界（为什么不在主工作区做 git 写操作）

主工作区 `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment` 当时在 `feat/prompt-narration-toggle`（HEAD `d2a6fa9`）且 **dirty 141 项**，全程未被触碰（未 `checkout`/`stash`/`reset`/`commit`）。本轮**所有** git 写操作（`commit` / `fetch` / `merge` / `push`）都在下列两个干净位置之一完成：

| 操作 | 路径 | 分支 | 基于 sha |
|---|---|---|---|
| 报告与证据的 `commit` | `.worktrees/life-habit-strength`（隔离 worktree，`git status --porcelain` 为空） | `feat/life-habit-strength` | 父提交 `d356a5b`（`code/` 未改） |
| `fetch` / 分支 `push` / 合入 master / master `push` | `/tmp/f5-merge`（`git clone --shared <主树>` 的临时克隆，干净树） | 先在 `feat/life-habit-strength`，后在 `master` | 分支推 `7ee591e`，master 以 `origin/master` 为合入基 |

### 12.2 合入方式（明确 merge commit，不是 FF）

合入前实测：`origin/master` 已从 `d2d1993` 前进到 **`0e65476`**（master 侧另有 **3 条 doc-only 提交**：`f7b7fbf`、`df488ce`、`0e65476`，只动 `v2/refs/` 与 `v2/evidence/` 下的文档，与本轮**无文件重叠**）。因此 `origin/master` 不是本分支 HEAD 的祖先，**无法 fast-forward**，采用显式 **merge commit**：

```
$ git checkout -B master origin/master          # 0e65476
$ git merge --no-ff origin/feat/life-habit-strength
=> merge commit 3a2ef22293e8c9b691886aae4040a5d5d238fb9d
   parents: 0e65476 (origin/master) + 7ee591e (本轮分支)
```

**「没有把别的分支内容带进来」的机械核查**（`git diff --name-only origin/master HEAD`）：

```
 38 v2/evidence        （全在 v2/evidence/f5_round1/ 下）
  3 tools/habit
  3 code/life
  1 v2/refs（round1-prereg-F5.md）
  1 reports/README.md
  1 reports/R25-f5-habit-strength.md
```

白名单外文件数 = **0**（`git diff --name-only origin/master HEAD | grep -v -E '^(code/life/planner\.py|code/life/tests/|tools/habit/|v2/refs/round1-prereg-F5\.md|reports/R25-f5-habit-strength\.md|reports/README\.md|v2/evidence/f5_round1/)'` → 空）。差异合计 `47 files changed, 39655 insertions(+), 23 deletions(-)`，全部为本轮产物。

### 12.3 push 后三 sha 核对（`git ls-remote origin` 实测）

| ref | origin 上实测 | 本地 | 一致 |
|---|---|---|---|
| `refs/heads/feat/life-habit-strength` | `7ee591ead572ddc1951c0e275975a25b55ae5345` | `7ee591e` | ✅ |
| `refs/heads/master` | `3a2ef22293e8c9b691886aae4040a5d5d238fb9d` | `3a2ef22` | ✅ |

复现命令：

```bash
git ls-remote origin refs/heads/master refs/heads/feat/life-habit-strength
git log --oneline --graph -4 3a2ef22
git diff --name-only 0e65476 3a2ef22        # 应只含本轮 47 个文件
```

> 本节补记本身的提交 sha 见 `git log -1 -- reports/R25-f5-habit-strength.md`（master 上）；
> 补记只增本节文字，**不改任何读数、阈值、判据与证据文件**。
