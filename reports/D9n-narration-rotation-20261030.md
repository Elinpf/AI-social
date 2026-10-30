# D9n · 旁白示例句确定性轮换（单变量 A only）· OFF/ON 对照报告

> **写作时刻**：2026-10-30 08:35–08:4x +08:00｜**作者**：report-writer（报告撰写与入库官）
> **报告对象**：本分支 `feat/life-narration-rotation` 的 D9n 臂（`LIFE_PROMPT_NARRATION_ROTATION`）相对基线语料的读数对照。
> **本报告不引入上游之外的数字**；凡我未亲跑的读数，一律标「引文件」并给出文件路径与 sha256。凡我亲跑者标「作者实跑」。
> **写作纪律（自我约束）**：①每条读数＝值 + 分子/分母 + 判据编号 + 绑定 sha；②机制层（字段/计数是否变化）与行为层（读起来是否更好）**分节**，不交叉下结论；③未达判据一律写「不成立 / 不可判」，**不写「更自然」「显著改善」「旋转有效」「多样性改善」**；④失效路径前置成表（见 §⑤.0），不让复算者先撞墙。

---

## 结论摘要（先看这五句，细节全部在后文可复算）

1. **`(b2′)`（唯一可能翻绿的主判据）未成立**：`蹭｜锉刀` 族 `total 9 → 6`、`n_ge2 3 → 2`（阈值 `≤3` / `≤1`）；但 `9→6` **差异不显著**（`z=0.775`，`p≈0.44`），**方向为降、功效不足**。
2. **`(e)` 出现新增越线（本轮第一条负向变化）**：`max_k` `2 → 3`，越线条目已定位到 `MSG_PUBLIC / P013 / r3 / seq 2209`（三行各一句旁白），且三个动词 `压/夹/敲` 全在 `unassigned` 内。
3. **禁用词面未下降（本轮第二条负向变化）**：示例句已排除 `围裙/木屑/蹭/磨/抹/擦`，实测 `围裙 13→17（+4）`、`手 47→63（+15）`（**均未达显著**：`z=0.730 / 1.437`），`锉刀 10→9`、`木屑 3→3`、`木花 2→1`。否定「示例句是词面集中度主因」靠的是**「缺席的强效应本身就是证伪」**——若示例句是主因，删示例后应见远超噪声的下落，实测连方向都没稳住。
4. **词面替换 ≠ 结构改善**：可逐条对上的是「同位置换字」（P004 r3 `蹭→擦`），伴 `拍` 7/8 同模板、`往…挪了挪` 模板 4→10、集中度上升 ⇒ **「以替换为主、兼有少量新增」**。
5. **分层**：**机制层成功**（守卫双过 + `degraded=0` + `replay_parity=True`，非测具失效）；**行为层未改善**。
   **一句话结论：「换了一批词，而不是动作更多样。」**

---

## ⓪ 身份与冻结口径

### 0.1 仓库与基线身份（全部本机实测）

| 项 | 值 | 取证 |
|---|---|---|
| 仓库根 | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment` | `git rev-parse --show-toplevel` |
| base sha | **`d2a6fa99b7eb978185a965b3f5c77675a7533498`**（`d2a6fa9`，`feat/prompt-narration-toggle` 尖端） | `git log -1 --format='%H %ad %s' d2a6fa9` → 2026-10-30 04:44:01 |
| 本地 `master` | `6fda371` | `git rev-parse --short=7 master` |
| 远端 `master`（快照） | `7cd10f93f68622308987a6fb4d36ffffdf8191d5`（`7cd10f9`） | `git ls-remote --heads origin`（rc=0） |
| merge-base | `b43033ea2c52238f76aa7c07083f4a8e91deb4a1` | `git merge-base master d2a6fa9` |
| 分叉计数 | 本地 master 独有 **38** / HEAD 独有 **12** | `git rev-list --count d2a6fa9..master` = 38；`master..d2a6fa9` = 12 |

**master 不可比声明（必读）**：
> **master 无旁白实现**，对**本地 `6fda371`** 与**远端 `7cd10f9`** 同时成立：`git fetch origin master` rc=0（FETCH_HEAD=`7cd10f9`）；`git show FETCH_HEAD:code/life/agent.py | grep -c NARRATION` = 0（rc=1，零命中）；`_NARRATION_TAIL_ON` 与 `围裙|木屑` 均零命中；`wc -l` = 1765；全 `code/` 子树 `git grep -ci narration FETCH_HEAD -- code/` rc=1 无输出。最有力的一条：`git diff --name-only 6fda371 FETCH_HEAD` 仅 4 个 `v2/evidence/*.md`（4 files / 699 insertions，零代码改动），`git diff --stat 6fda371 FETCH_HEAD -- code/life/agent.py` 空输出 ⇒ 远端那 2 条提交为纯文档、`agent.py` 零差异。
> **⇒ base 取 `d2a6fa9`，不代表 master 现状，二者不可比。**
> 另：本地 `master` 分支仍为 `6fda371`（未跟进）；`origin/master` 因该次 fetch 更新为 `7cd10f9`。证据件 `team-workspace/recon/remote-master-check.md`。

### 0.2 两臂定义（**注意：这不是同批重跑的两臂**）

| 项 | B 臂（基线语料） | O 臂（轮换臂，本轮） |
|---|---|---|
| 目录 | `v2/evidence/narr-on-20261030/` | `v2/evidence/d9n-rot-20261030/` |
| `code_sha` | `47a7da9e71e4ab31e8b58a9a5cc14105ecd0aed8` | **`df29cf9abc056d7982f01a1ffe10e5c5b4ccd15b`** |
| 日志 `run.jsonl` sha256 | `fdb31c7e2ca64b4dac1466fd4c81770dc0198ced4904584a3faf59939fd663ee` | `e4fd6db7f863fe2f6bcf6e06753600783ce57505b48a10d5c97247bf5866ece1` |
| 开关 | `LIFE_PROMPT_NARRATION=1`（D9i 固定示例句） | `LIFE_PROMPT_NARRATION=1` + **`LIFE_PROMPT_NARRATION_ROTATION=1`** |
| provider / model | `openai_compat` / `DeepSeek-Flash` | 同左 |
| n / seed / rounds | 16 agents / 42 / 24 | 同左 |
| MSG 数 | 191（dm 167 + public 24）／66 线程 | 191（dm 167 + public 24）／66 线程 |
| 起跑→收批 | 2026-10-30 02:34:23 → 02:53:35 | 2026-10-30 08:27:41 → 08:30:16（154 s） |

**两条必须披露的比较性质（不是同批对照）**：
1. **B 臂是历史日志，不是本轮重跑的 OFF 臂**。B 臂日志产生于 `code_sha=47a7da9`（D9i ON 臂），O 臂为 `df29cf9`。`git diff --stat 47a7da9 df29cf9 -- code/` = `code/life/agent.py` +76/−7、`code/tests/test_life_narration_rotation.py` +229（共 305 插入 / 7 删除）⇒ **两臂代码树不同**，名义差异是「示例句是否轮换」，但严格说属**跨批比较**（温度采样非确定性 + 代码差异并存）。
2. 因此本报告**不使用「同 sha 两臂」措辞**；所有差值只能读作「两个语料之间的观测差异」，**不构成因果证明**。

### 0.3 `seed` 未设 ⇒ 回落 `0`（非疏漏）

> `HITT_WORLD_SEED` 全链路从未设置：`meta.switch_declared.HITT_WORLD_SEED = {raw: null, parsed_int: 0}`；选句输入为 `sha256("0"|agent_id|round|kind)`，**非 seed=42**。落地证据两处：`code/life/weather.py:36-37`（缺省 `"0"`）、`code/tests/test_life_narration_rotation.py:189`（未设/空串/`"0"` 三态同序列）。**seed 未设 ⇒ 回落 0，与基线同配置，非疏漏。**

### 0.4 开关真值与 meta 级取证缺口（诚实登记）

- 开关真值来自**内层启动器环境落盘** `v2/evidence/d9n-rot-20261030/env_inner_launcher.txt`：`LIFE_PROMPT_NARRATION=1`、`LIFE_PROMPT_NARRATION_ROTATION=1`、`HITT_LLM_PROVIDER=<unset>`、pid `2587912`、`cmdline=/usr/bin/bash …/d9n_launch_arm.sh`、`finished_at=08:30:16 rc=0`。
- **缺口（与 CYCLE-30 F-6 同型）**：`meta.switch_declared` **未收录** `LIFE_PROMPT_NARRATION` / `LIFE_PROMPT_NARRATION_ROTATION` 两键（该结构只有 `HITT_DIALOGUE_EMOTION_ECHO`/`HITT_DIALOGUE_REPAIR`/`HITT_WEATHER`/`HITT_WORLD_SEED`）⇒ **meta 级开关取证不完整**，本报告只能以启动器内联落盘 env 为据，不声称「meta 已证四项开关」。
- **`switch_proof` 属「取证降级」，不是「已取得」**：本批因 cache 命中仅跑 **154 秒**，`/proc/<pid>/environ` 取证时进程已退出 ⇒ **批次进程 `procfs` 证据未取到（首选口径未达成）**。可接受但必须如实标注的**替代证据四条**：
  1. 包装器被执行层 env 落盘（`pid=2587912` + `cmdline=…/d9n_launch_arm.sh` + 两开关均 `1` + `HITT_WORLD_SEED=<unset>`）；
  2. `env | grep -c HITT_WORLD_SEED` = **0**；
  3. `meta.switch_declared.HITT_WORLD_SEED.raw = null`（**在批次进程内读 environ，价值最高**）；
  4. **191/191 条对话的 `prompt_hash` 与基线全不同** ⇒ 生成面输入的 prompt 整体已被改动（与「仅示例句轮换」的机制一致）。
  > 措辞纪律：写「**批次进程 `/proc/<pid>/environ` 未取到**（154 秒结束，取证时已退出）；替代证据为上述四条；**首选口径未达成**」。

### 0.5 成本与 cache 不对称（不得读作两臂同构）

| 量 | B 臂 | O 臂 | 说明 |
|---|---|---|---|
| `llm_calls` | 2252 | 2252 | `meta.llm_calls`；`llm_cost.json.engine_log.total.calls` |
| `cached` 总数 / 比例 | 1387 / **0.6159** | 1989 / **0.8832** | 差异只在 `importance`/`judge`/`reflect`/`negotiation`/`plan` |
| `dialogue` 的 `cached` | **0** | **0** | 两臂 191 次对话调用**全为真调用** ⇒ 判据读数取自真 LLM 输出 |
| `degraded` | 0 | 0 | `llm_cost.json.total.degraded` |
| tokens（in/out/总） | 152,287 / 145,141 / **297,428** | 97,754 / 13,974 / **111,728** | 差异主要来自 cache 命中结构，**非**对话侧算力 |
| `provider_guard.ok` | true | true | `by_provider={openai_compat: 2252}`，无 mock 混入 |

**⇒ 两臂 cache 不对称，不能声称「两臂同构」。** 但**判据所依赖的 `dialogue` 侧 `cached=0` 两臂一致**，故判据读数不受 cache 结构影响。

- **差异已定位到 purpose 级**：差异全在 `judge 425` / `plan 16` / `negotiation 7` / `reflect 18` / `importance` 尾部 `136`。原因：**A′ 种子是在基线跑完之后复制的 cache**，基线当次新写的键在本臂全部命中。
- **必须写入的限制声明**：
  > 「本臂 `judge` 判定为**复用基线缓存**的结果；因此**任何依赖 judge 的读数在两臂间不可比**。本轮未以 judge 作判据，故不影响本结论，但该两臂的 judge 分数不得用于任何比较。」
- **真 LLM 证据（两条并列）**：① `degraded=0` + `provider_guard.ok=true` + `by_provider={openai_compat: 2252}`（无 mock 混入）；② **`dialogue` 两臂均 `cached=0` ⇒ 191 次对话调用全部为真调用**。

### 0.6 收批凭据（**本臂不生成 `END.json`**）

**另需如实标注**：`run_batch.rc` 的**原始字节已被第 2 次起跑覆盖**（同一 `out_dir`），现存 rc 记录属**原文快照 + 人工陈述，非字节级原件**；本报告不把它称为原件。`run.jsonl` 指纹与规模可独立复核：sha256 `e4fd6db7f863fe2f6bcf6e06753600783ce57505b48a10d5c97247bf5866ece1`，**33826 行 / 17,154,803 B**；`meta.code_sha = meta.code_sha_end = df29cf9`。

本臂**没有** `END.json` 这个文件，收批凭据为五项等价硬信号：`pgrep=0`、`run_batch.rc`/`llm_cost.rc` 均 0、`wc -l run.jsonl == 33826 == meta.events`、`replay_parity / chain 校验` 全 True、`provider={openai_compat:2252}` 且 `degraded=0`；`meta.json`（27663 B，sha256 `9084ecda1c0bafaa29c23bc601b5137669535dbc84b5586879f9a1e69ba96da8`）为凭据载体。**本报告不声称「`END.json` 已生成」。**

---

## ① 预登记引用（主件 + **6 增补**，共 **7 枚哈希** + anchor）

| 编号 | 路径 | sha256 |
|---|---|---|
| 主件 | `v2/refs/D9n-prereg-narration-example-rotation.md` | `0d10450232b04327fe7980ddbaa68b694fba9b1b827b433b5b54b5d7c1b06643` |
| 增补 01（种子勘误 / 守卫阈值来源 / 编号让位 / 判据六条勘误） | `v2/refs/D9n-prereg-amendment-01.md` | `3b055ffa518e07e61375d2f2b0c1c9259c4ec47d21f8fdd46100a4afc602bbd9` |
| 增补 02（守卫阈值来源 + 修恒假） | `v2/refs/D9n-prereg-amendment-02-guard-thresholds.md` | `401617edc2bbb5dcb04e8291df30e8df315200bd9af676146a4108b959988095` |
| 增补 03（族词表内容 + meta 口径） | `v2/refs/D9n-prereg-amendment-03-family-lexicon.md` | `fa5af47dc53f8a272dde9238b741db67a69fa9ac00537ad8bf6cb944862898cf` |
| 增补 04（D9j 版本化勘误；原文件名 `…amendment1-d9j-provenance.md`，无连字符） | `v2/refs/D9n-prereg-amendment-04-d9j-provenance.md` | `1cc362c2be1705e8a8b424b348c13119685fd4c469caa8ee4bdd5e64e11896d5` |
| 增补 05（路径与改名对照；**`v1.1`**） | `v2/refs/D9n-prereg-amendment-05-paths-and-renames.md` | **`3da0f4b63fc646e362febfdf8de60b0bf37bce2ffec241b172d50594cf6f8eeb`**（v1.1 现行值；旧 v1.0 值 `5c465b0e83acc5766a6cb63ac2a45031095fa66dfb468c823ccb3a2f108252d9` 已被取代，仅作 SUPERSEDED 留痕） |
| 增补 06（守卫基线须用同口径 `V_judge` 重算；新旧门限对照 + 收紧论证） | `v2/refs/D9n-prereg-amendment-06-guard-anchor-same-caliber.md` | `543cfd1e6b2da0c592f0c6f3d01d285e59e962ab98ca3157e29455f9a17c3962`（commit `de4649c`） |
| anchor | `v2/refs/D9n-prereg-commit-anchor.txt` | **`4344f4afff8589d0eb2309cecf7a9ac090408ec54da6075ec2f6395381a4f531`**（`ba002ca` 重锚后现行值；旧值 `29cd708113c14b59aee88a46eed48f89963fb99059df26b0609c9d8dc310663b` 已被取代，仅作 SUPERSEDED 留痕） |

**冻结时序（三行 commit 溯源，回答「判据是否跑前冻结」）**：
- 增补 01 入库 commit = **`52336b9`**；增补 02–05 入库 commit = **`5a9b5a2`**；anchor 回填 commit = `f1e758a`。
- **最早一条判据修订 commit = `52336b9`**，早于本臂 `started_at=2026-10-30T08:27:41+08:00`；预登记 rename（content 不变）为 `5f302dc`。
- 声明：**主件字节冻结不改；判据修订全部走增补**；跑后未改任何判据行。

**回执（读取时刻实测三件套，禁自指表述）**：
> `team-workspace/recon/D9n-freeze-receipt.txt`：读取时刻 sha256 = `4809dfd3e48904efdf6a33e1f33681d1c1a854e78c9efa7cf3f7eb8eba094d50`，size = 7957 B，mtime = 2026-10-30T08:34:54+08:00（作者实测）。
> 该回执**无法自指自身终版 sha**（回执内 `cite_rule` 第 82–85 行明写「最终 sha 外部公布」），并记录 SUPERSEDED 链 `20f21e3c` → `33f04e04` → `328a0f77` → `e4a7e63a` → 本次定版。
> 回执现状：`finalized = true`；SUPERSEDED 链 = `20f21e3c` → `33f04e04` → `328a0f77` → `e4a7e63a` → **`4809dfd3`（定版）**。
> ⚠ 时效说明：08:32:49 版本（`e4a7e63a…`，7418 B）已被 08:34:54 版本（`4809dfd3…`，7957 B）取代；本报告按**读取时刻实测三件套**记录（作者读取时刻 2026-10-30T08:35），**不主张其为回执自证值**（回执无法自指）。

**两处主件自身的瑕疵（披露，不回改）**：
1. **判据计数瑕疵**：D9j/D9n 主件自称「八条判据」，表内实际为 **6 条**——`(a)(b1)(b2′)(c)(d)(e)`；其 20 格自检表按「4 条判定 × 5 问」填。**本报告按 6 条逐条判定。**
2. **旧编号残留**：主件正文 **8 行 / 9 处**写 `D9m`（`:3` 行含 2 处：标题「D9m 预登记」+「D9m-freeze-receipt」）、**7 处**写 `tools/d9m/`。复算必按 §⑤.0 映射表读取。

**两处口径变更（本轮有效口径）**：
- `(b1)` **降为辅助判据**（理由：n=8、Wilson ±27pp 无功效）。此处**不含任何数值更正**：`62.5%` 为 D9j 正确值。此前一版曾误算出另一个百分比（漏列「指头」所致，已作废），**本报告不重复该作废数值、也从未用它做过任何读数或判定**。
- `(b2′)` **基线取 9**（含定位到的漏项 P013 r13「铁砧豁口柴刀」/ P014 r19「赵家铁环毛边」）；与 D9j 的 8 差异属漏计 1 条，**按 9 计以免夸大改善**；两数并存时取更保守者（runbook §3.97）。

---

## ①-2 起跑失败记：`preflight` rc=9（启动器 argv 自匹配）与整改

> **节首声明：本节不参与任何判据判定，属 harness 记录。** 它证明「跑批串行」闸门真的会拦东西，并提供其误报代价。

| 项 | 实测 | 证据 |
|---|---|---|
| 结果 | `run_batch.rc=9`，`FAIL exit=9 reasons=concurrency:run_batch=2` | `v2/evidence/d9n-rot-20261030/FAILED_ATTEMPT_1.md` + `preflight/preflight_20261030T002604Z_df29cf9a_run_batch.log` |
| 根因 | 启动器 `argv` 含 `run_batch.sh` 字面量 ⇒ `pgrep -f` **命中自身**（`/bin/sh -c … systemd-run …` 与 `systemd-run` 两个 PID 2584104 / 2584106） | 同上；该二 PID 事后均 **GONE**，且**不在批次祖先链**（`self_pid=2584119 ancestors=2584119 2584116 2584108 1`） |
| 事件量 | **0 事件、无 `run.jsonl`**（目录内唯一 `run.jsonl` 的 mtime 属成功批 08:30） | `ls v2/evidence/d9n-rot-20261030/run.jsonl` 只有一份 |
| 代价（墙钟） | **约 1 秒**：`08:26:04 Starting` → `08:26:05 Deactivated successfully / Finished` | **唯一来源 = `journalctl -u d9n-rot-20261030.service --no-pager -o short-iso`**（原文落 `v2/evidence/d9n-rot-20261030/systemd_journal.txt`，sha256 `0cfbd311…`） |
| 代价（算力） | **0 次 LLM 调用**（批次进程未起，无日志即无调用） | 该 attempt 无 `run.jsonl`（0 事件） |
| 整改 | 改用包装脚本 `d9n_launch_arm.sh`（sha256 `92840eaac45ab54ee2b8345121ad2a66ddb8759c0ee1117d22eed893d5edefa9`）重跑，`preflight_manual.rc=0`、`PASS … concurrency=0 frozen_tree=clean` | `wrapper_sha256.txt`、`preflight_manual.log`、`preflight/preflight_20261030T02741Z…log` |

**三处措辞校正（不采信口头数，也不采信"人工打点反推"，一律以 journal 为唯一来源）**：
1. 我先前写「约 21 秒」、Leader 先后给过「约 43 秒」「约 21 秒」，**均与 systemd journal 不符**：journal 显示 `08:26:04 Starting` → `08:26:05 Deactivated/Finished` ⇒ **实际约 1 秒**。**这说明「按消息时间线或人工打点反推」本身不可靠**，本报告以 journal 为唯一时间来源，并附命令：
   ```bash
   journalctl -u d9n-rot-20261030.service --no-pager -o short-iso
   ```
2. **journal 里留存 attempt#1 的内联 argv 原文**（`bash -lc "… bash tools/d2/run_batch.sh --out-dir v2/evidence/d9n-rot-20261030 …"`）——这是「`pgrep -f` 命中的是启动器自身」的**第一手记录**，比任何转述都硬；本节根因判断即以此为准。
3. 「0 LLM 调用」有**间接**落盘依据（该 attempt 无 `run.jsonl` ⇒ 0 事件），但**没有**直接成本件（无对应 `llm_cost.json`）⇒ 写作「0 事件（无 `run.jsonl`）级证据」，不升级为「`obs llm-cost` 实测 0 调用」。

**结论（限定）**：串行闸门在本轮**确实拦下了一次误报**，且**代价为零算力、约 1 秒墙钟**（systemd journal：`08:26:04 Starting` → `08:26:05 Deactivated/Finished`）；这不等于「闸门设计无误」（误报本身来自 `pgrep -f` 的 argv 自匹配，属已知类缺陷）。

---

## ①-3 与并行线 D9m 的关系声明

1. `v2/refs/D9m-prereg-narration-action-diversity.md`（master `0938f14`）是**另一支团队**的方针件，与本轮 D9n 是**两条独立线**。
2. **差异**：并行线做 **A（改示例）+ B（禁过渡动作）两处改动**，含 r84 绝对量层；本轮 D9n **只做 A、单变量、r24**。因果归因干净是本轮的取舍理由（两处改动无法区分贡献）。
3. **两者结论不得互相引用、不得混算、不得把对方读数当本轮基线或验证。**
4. 若两线结论冲突：**不做裁决、只列事实**（各有各的 sha 与口径）。
5. **并行线已知瑕疵（仅登记，未参与本轮判定，不据此评价对方结论）**：其件第 90 行仍写「沿用 D9j 八条」而其下只列 6 条；件头写 08:15 而入库提交时刻为 08:11:43。
6. 本分支**不含**并行线文件（核对命令与输出见 §⑨）。

---

## ② 结论映射表（**先给表，再给观测值**）

| 判据 | 成立 | 不成立 | 不可判 |
|---|---|---|---|
| `(b2′)` | `total ≤ 3` **且** `n_ge2 ≤ 1`（两者同时满足） | 任一未满足，且样本量足以判定（功效达标） | 位移方向正确但功效不足 / 分子分母不足 / 守卫未过 |
| `(d)` | `max_v ≤ 5`（V_judge 全 21 词口径下）且守卫达阈 | `max_v > 5` 且守卫达阈 | 守卫未过 / 计数不可比 |
| `(e)` | `max_k ≤ 2`（单条 MSG 旁白片段数） | `max_k > 2` | 分母不足 |
| `(c-1)` | 密度 `≥ 1.0 片段/MSG` | 密度 `< 1.0` | — |
| `(c-2)` | — | — | **恒不可判**（无公式、无实现、抽样框未披露） |
| `(a)` | `max_exact_dup ≤ 2` | `> 2` | — |
| `(b1)`（辅助，本轮降级） | 族总量 ≥3 的族：`share ≤ 60%` 且该(角色,族)`count ≤ 2` | 任一未满足 | 族总量 <3（不适用） |

**方向性事实（决定本报告能说什么）**：基线七条判定为 `(a)` 失败｜`(b1)` 失败｜`(b2′)` 失败｜`(c-1)` **成立**｜`(c-2)` 不可判｜`(d)` 失败｜`(e)` **成立**。
⇒ `(c-1)` 与 `(e)` **基线已绿 ⇒ 只能被破坏、不能被「证明改善」**，属**守卫（已绿，非改善证据）**；`(a)` 诊断、`(b1)` 降级、`(d)` 基线即不可行、`(c-2)` 恒不可判。
⇒ **本轮唯一可能由「变好」翻绿的是 `(b2′)` 一条。**

---

## ③ 主结论（六条逐条；先表后判）

| # | 判据 | 门槛 | 基线 B | 本臂 O | 判定 |
|---|---|---|---|---|---|
| `(a)` | 精确串重复 `max_exact_dup` | ≤2 | **3**（`把沾着面粉的手在围裙上蹭了蹭` / `把算盘珠子拨回原位` / `顿了顿` 各 3） | **3**（`把算盘珠子拨回原位` 3；次高 2） | **不成立（诊断项，不进判定）** |
| `(b1)` | 同角色×族占比（辅助） | ≤60% 且该角色该族 ≤2 | P004 `蹭｜手` **5/8 = 62.5%**〔Wilson 95%: 0.305742–0.863156〕 | P002 `蹭｜null` **3/5 = 60.0%**〔Wilson 95%: 0.230724–0.882379〕；P004 `蹭｜手` 3/7 = 42.86% | **不成立**（`count 3 > 2`；注意 60.0% 恰在占比阈值上，判据靠「该角色该族 ≤2 次」这一半否决） |
| `(b2′)` | 族内 `total ≤3` 且 `n_ge2 ≤1`（**主判据**） | — | `蹭｜锉刀` **total 9 / n_ge2 3** | `蹭｜锉刀` **total 6 / n_ge2 2** | **不成立（含功效限定，见 §③.1）** |
| `(d)` | `max_v ≤5`（全 21 词） | ≤5 | **31（`蹭`）**；`挪` 7 | **24（`蹭`）**；`挪` 12、`拍` 8、`擦` 3 | **不成立**（且**基线即不可行**，见 §④ 缺陷 2） |
| `(e)` | 单条 MSG 片段数 `max_k ≤2` | ≤2 | **2**（分布 0:12 / 1:153 / 2:26） | **3**（分布 0:9 / 1:163 / 2:18 / **3:1**） | **由达标变失败（新增越线 1 条，见 §③.2）** |
| `(c-1)` | 密度 ≥1.0 片段/MSG（守卫） | ≥1.0 | 205/191 = **1.073298** | 202/191 = **1.057592** | **成立（守卫，已绿，非改善证据）** |
| `(c-2)` | 咬合率 ≥82.35% | — | — | — | **不可判**（无公式/无实现/抽样框未披露） |
| 守卫 | `coverage ≥ 0.193171` / `unassigned ≤ 0.778049` | — | 0.321951 / 0.678049 | 0.351485 / 0.648515 | **均过**（尺子对两臂语料有效） |

### ③.1 `(b2′)`：点估计未达阈值，但**差异不显著、功效不足**（结论段核心）

- 观测：`total` **9 → 6**（`−3`，相对 `−33.3%`）；`n_ge2` **3 → 2**。
- 阈值判定两层（本轮必须写清，否则会被判「把不可判写成失败」）：
  1. **为什么是「不成立」而不是「不可判」**：`(b2′)` 是**绝对阈值闸**（`total ≤3` **且** `n_ge2 ≤1`），判定依据是**读数本身**、与统计功效无关；三态中的「不可判」只留给「尺子失效 / 样本 < 50 / 无判定对象」，本臂三条均不触发（守卫双过、片段 202）。
  2. **但必须并报功效**：`9→6` 落在 Poisson 区间内（Wald `[3.12,14.88]`；Garwood `[4.115373,17.084803]`）⇒ **不可区分于噪声**，不得主张方向性改善；同理单看 `蹭 31→24` 的 Wald 区间 `[14.4, 33.6]` 与 31 **重叠**，也不可主张显著。
- **可操作的效力上界（本轮最有用的量化，三口径并报，以 B 为规划值）**：按现规模（202 片段、族命中率约 3%）区分 `λ=6 vs λ=3`，当前效力仅约 **`z≈1.22`**（判显著需 ≈2.8）。在 `α=0.05, power=0.8` 下所需规模：

| 口径 | 所需片段/臂 | 等效轮次 | 定位 |
|---|---|---|---|
| **A（单样本 `√6`）** | 1057 | ≈ r126 | **下限**（会让人误以为「再做一轮就够」） |
| **B（两样本 `√9`）** | **1585** | **≈ r188** | **本报告采用的规划值** |
| C（精确条件） | 3615 | ≈ r430 | 精确但偏保守 |

  ⇒ **结论：`(b2′)` 在 r24 规模下只能作「绝对阈值闸」，不能作「差值检验」；下一轮若要做差值检验，按 B 口径规划 ≈1585 片段/臂（≈r188），宁高勿低。**
- **必须同时给出的功效限定（缺此句即等于把「无法区分」写成「失败」）**：
  > **点估计未达成立条件（`total 6>3`、`n_ge2 2>1`）；但 9→6 差异不显著（`z=0.775`，`p≈0.44`），方向为降、功效不足。**
- **区间口径（两套并列，因我实测与上游口径不同，此处显式披露）**：

| 口径 | `k=9` 的 95% 区间 | `k=6` 的 95% 区间 | 出处 |
|---|---|---|---|
| 正态近似（Wald，λ±1.96√λ） | **`[3.12, 14.88]`** | **`[1.20, 10.80]`** | 上游裁决件（verifier 口径） |
| **Garwood 精确法**（本报告脚本实算） | **`[4.115373, 17.084803]`** | **`[2.201894, 13.059474]`** | `tools/metrics/d9n_poisson_ci.py`，`--selftest` 5/5 PASS |

> 两套区间**都覆盖阈值 3**，两套口径下 `z=0.775 / p≈0.44` 的结论**一致**（不显著）。**结论不依赖区间口径选择**；但两者数值差在小计数下不可忽略（`k=6` 下界 1.20 vs 2.20），故并列披露，避免读者以为只有一个"官方区间"。
> 检验口径：`Δ=3`、`SE=√(9+6)=3.873`、`z=3/3.873=0.775`、`p≈0.44`（两样本 Poisson 计数差的正态近似检验）。
> 「位移/半宽」口径：`3 ÷ (1.96×√9 = 5.88) = 0.510×` ⇒ 预登记只认 `≈1.0×` 才算「大幅」，实测 **0.51×** 未达标。

### ③.2 `(e)` 新增越线：1 条，已定位，**与邻族增量相互独立**

| 项 | 值 |
|---|---|
| 位置 | `MSG_PUBLIC` / **P013** / round **3** / `msg_id=P-3-0` / `seq=2209` / 线程 `TH-P013-PUB-3-0` |
| 片段数 | **3**（越过 `max_k ≤2`） |
| 三段旁白原文 | `（把风箱拉杆慢慢压下去，炉膛里火星子溅起来）` / `（拿火钳夹起块铁片翻个面）` / `（往铁砧上轻敲两下）` |
| 三个动词 | `压` / `夹` / `敲` —— **都不在 V_judge 21 词内** |

⇒ **关键性质**：该越线条目的动词全部落 `unassigned`，**既不贡献 `拍`、也不贡献 `擦`**。因此 **`(e)` 与 §③.3 的邻族增量（`挪/拍/擦`）相互独立**，必须分开陈述，不得合并成「整体变差」或相互解释。
其机制是「一条消息分三行塞三句旁白」，即预登记封洞②（防「塞旁白刷密度」）**被反向利用**——旁白密度上限判据在「按 MSG 计」的口径下挡不住「同一条消息切三行」。

### ③.3 词面层生效、结构层未改善、并出现**新族固化**（本轮信息量最大的一节）

| 观察 | 基线 B | 本臂 O | 读法 |
|---|---|---|---|
| 生效：`蹭` 总量 | 31 | **24** | 示例轮换确实压低了被替换词面 |
| 生效：`蹭｜锉刀` 族总量 | 9 | **6** | 同上 |
| 未改善：`max_v` | 31 | 24 | 门槛 5，**差 19 次**，属量级差距 |
| 未改善：越线族**数量** | 7 个族 | **7 个族** | 数量不变 |
| **但族构成变了** | 抬｜null(4)、挪｜手(4)、蹭｜null(6)、蹭｜手(8)、蹭｜指腹(4)、蹭｜锉刀(9)、靠｜null(4) | **拍｜手(8)**、拢｜null(4)、**挪｜null(7)**、蹭｜null(5)、蹭｜手(7)、蹭｜锉刀(6)、靠｜null(6) | 3 族出局、3 族新进（见下行） |
| 邻族增量（**重新分配**） | `挪` 7、`拍` **0**、`擦` **0** | `挪` **12**、`拍` **8**、`擦` **3** | 降幅被邻族增量部分抵消 |
| **新族固化** | — | **`拍｜手` 8 次**（P016 3 / P007 2 / P011 1 / P012 1 / P001 1） | 新出现的「同族多角色重复」 |

**允许的表述**：**「词面层生效、结构层未改善、出现新族固化」**。
**禁止的表述**：「旋转有效 / 多样性改善 / 更自然 / 整体改善 / 方向正确 / 接近阈值」。
**结论句（采用 exp-designer 措辞）**：**「换了一批词，而不是动作更多样。」**

### ③.4 「替换」还是「新增」：决定性逐条证据（**决定结论措辞**）

> 出处：`team-workspace/d9n/D9n-readonly-d-component-and-b2p-adjudication.md`（sha256 `910ed4502df59d49e5a867ccd8bce76326995ab025dfd1d4ef2d518b6415aa63`）。以下原文由该作者逐条对齐 `agent×round×seq`，本报告**照引**并标注「引文件」。

**(i) 纯替换（P004 r3，同 `agent×round×seq` 逐字对照）**〔引文件〕

| 臂 | 原文 |
|---|---|
| 基线 | `把沾着面粉的手在围裙上蹭了蹭，凑近看你刚开的榫眼` |
| 本臂 | `在围裙上擦了擦沾着面粉的手，凑近看了眼那榫头` |

同一器物（`围裙`）、同一受事（`手` + `沾着面粉`）、同一后续动作（凑近看榫头），**只有动词 `蹭 → 擦` 与语序调换** ⇒ 「擦拭类内部换字」，**不是新动作**。

**(ii) 真新增（P015 r16）**〔引文件〕

| 臂 | 原文 |
|---|---|
| 基线 | `手在围裙上蹭了蹭，灶上那锅汤还咕嘟着` |
| 本臂 | `手在围裙上蹭了蹭，往灶台边挪了半步` |

机制修正（以 verifier 复核为准）：**不是「追加 `挪` 分句」，而是尾句替换、`蹭` 原样保留**——基线尾句「灶上那锅汤还咕嘟着」被换成「往灶台边挪了半步」，`（手在围裙上蹭了蹭，…）` 的前半一字未动。**正因为 `蹭` 保留而尾部另加动作，「全部为替换」才不成立**；「以替换为主、兼有少量新增」的结论不变，但本条例证按此正确描述引用。

**(iii) 新模板而非新动作**〔引文件〕
- `拍` 共 8 条，其中 **7 条**同构为「`拍了拍` + 部位/器物 + `上的` + 碎屑名词」（`手上的灰`/`围裙上的碎叶`/`手上的碎叶子`/`麻袋上的灰`/`手上的面`/`手上的碎屑`/…）⇒ **单一模板的 7 次复制**，语义仍是「掸掉手上灰」。
- 「`往{桌角|边上|旁边|脚边|膝头}挪了挪`」模板：基线 **4** → 本臂 **10**（+6）；其中 `把竹篮往膝头挪了挪`（P012 r3）与旋转词表第 6 句「把竹篮往脚边挪了挪」**同构到只差一个方位词**。
  **正则原文（本报告口径，作者实跑可复现）**：`往(?:桌角|边上|旁边|脚边|膝头)挪了挪`（对旁白片段计数，分母 205 / 202）⇒ **4 → 10**。
  **更宽口径对照**：`往[^，。）、]{0,8}挪了挪` ⇒ **5 → 11**（多出的 1 条为 `往膝盖上挪了挪`，方位词不在窄表内）。**两口径差值同为 +6**，结论不依赖口径选择。

**(iv) 反向指标：集中度上升**〔引文件〕

| 关键词 | 基线 | 本臂 | 变化 |
|---|---|---|---|
| 含 `围裙` | 13 | **17** | +4 |
| 含 `手` | 47 | **62** | +15 |

⇒ 词面中心从「`蹭`」迁移到「**手 / 围裙**」，**集中度上升而非分散**。

**⇒ 允许结论：「以替换为主、兼有少量新增」，且伴以新模板化与集中度上升。**
**禁止结论**：「全部为替换」（反例即 P015 r16）、「动作库扩张」（`拍` 7/8 同模板、`max_v=24`、`围裙/手` 集中度上升三条同时反驳）。

### ③.5 禁用词面**未下降**（本轮第二条负向变化）

词表已排除 `蹭/磨/抹/擦` 与 `围裙/锉刀/木屑`。作者实跑（片段级计数，分母 = 旁白片段 205 / 202）并用两样本 Poisson 计数差检验：

| 词面 | BASE → ON | 差值 | 两样本 `z` | `p` | 可说的话 |
|---|---|---|---|---|---|
| `围裙` | 13 → **17** | +4 | 0.730 | 0.465 | **未达显著** |
| `手`（出现次数；含该词片段数 47→62） | 47 → **63**（62 片段） | +15（片段 +15） | 1.437 | 0.151 | **未达显著** |
| `锉刀` | 10 → 9 | −1 | −0.229 | 0.819 | 与 0 不可区分 |
| `木屑` | 3 → 3 | 0 | 0 | 1.00 | 无变化 |
| `木花` | 2 → 1 | −1 | −0.577 | 0.56 | 与 0 不可区分 |

**可写**：「禁用词面**未下降**（`围裙` 点估计 +4、`手` +15，**均未达显著**）」。
**禁写**：「显著反增」「明确上升」——**本轮用统计标准否掉了 `(b2′)` 的点估计改善，就不能对自己的观察改用点估计**。

**核心论证（用这版，别用「反增证伪」）**：否定「示例句是词面集中度主因」靠的不是「上升显著」，而是**「预期的强效应缺席」**——若示例句是主因，删掉示例后应出现一个**远超噪声的下落**；实测连方向都没稳住（`锉刀 10→9`、`木屑 3→3`、`木花 2→1`）。
⇒ 定稿句：**「缺席的强效应本身就是证伪。」**

### ③.6 `拍` 与 `擦` 必须分开判（显著性补完）

| 词 | BASE → ON | 两样本 95% 区间（`Δ ± 1.96·√(Σx)`） | 判定 |
|---|---|---|---|
| `拍` | 0 → **8** | **`[2.46, 13.54]`**，下界 > 0 | **本轮唯一统计可辨的新增** |
| `擦` | 0 → 3 | `[−0.39, 6.39]`，下界 ≤ 0 | **不能判定**（与 0 不可区分），**不得写「新增」** |

**定稿句**：「`拍` 出现统计可辨的新增（`0→8`，CI 下界 `2.46`）；`擦` 不能判定（`0→3`，与 0 不可区分）。」

**顺带把 `(d)` 的解释写干净**：**唯一真实新增的 `拍` 恰好落在同一模板（7/8 条同为「`拍了拍` + 部位/器物 + `上的` + 碎屑名词」）⇒ 模型换的是词，不是动作结构。**

### ③.7 结论上限（无论结果如何）

本报告最多主张：**「`(b2′)` 族总量观测值由 9 降至 6，且该差异不显著」**，并附分子分母 + 两套区间；**不得**升级为任何效果性表述（见上）。

---

## ④ 判据设计缺陷清单（本轮元结论，优先于单个判据结果）

| # | 缺陷 | 事实 | 后果 |
|---|---|---|---|
| 1 | `(c-2)` 咬合率 **不可复算** | 门槛 82.35% = 42/51，出自人工判读（`v2/evidence/d9i_language_read_prompt_linguist.md:46`），**无公式、无实现件**，分母为 51 条手工抽样且抽样框未披露 | 该判据本轮**恒不可判**；报告不得出现咬合率读数 |
| 2 | `(d)` **基线即不成立 ⇒ 无判别力** | 门槛 `max_v ≤5`，而基线 21 词全表 `挪 = 7` 已单独越限，且 `挪` 非示例词、属自然用词；基线 `max_v = 31` | 即使 `蹭` 被压到 0，只要 `挪 ≥6`，`(d)` 照旧失败 ⇒ **与本轮假设解耦**，不构成对旋转效果的检验 |
| 3 | **三态定义把「功效不足」排除在「不可判」之外** | 客观事实是 9→6 差异不显著（`z=0.775`，`p≈0.44`），位移/半宽仅 `0.51×`，而预登记 §7 自己要求 `≈1.0×` 才算「大幅」 | 客观「无法区分」会被字面判定写成「不成立」⇒ 与预登记自身功效条款**矛盾**；本轮按「不成立 + 功效限定」双写以缓解，但**定义缺陷未修**（判据跑中不改） |

---

## ⑤ 可复算证据段

### ⑤.0 失效路径速查表（**复算前先看这张**，请放在你复制任何主件命令之前）

主件正文（冻结不改）共有 **8 行**失效路径：7 处 `tools/d9m/` + 1 处旧预登记路径。

| # | 主件行 | 主件内文（**失效，勿照抄**） | 正确写法（照此复制） | 照抄后果 |
|---|---|---|---|---|
| 1 | `:180` | `tools/d9m/narration_family.py`（仪器表） | `tools/d9n/narration_family.py` | 引用不到实现件 |
| 2 | `:190` | `python3 tools/d9m/narration_family.py \` | `python3 tools/d9n/narration_family.py \` | rc≠0（No such file） |
| 3 | `:192` | `--lexicon tools/d9m/narration_family_lexicon.json` | `--lexicon tools/d9n/narration_family_lexicon.json` | rc≠0 |
| 4 | `:358` | `python3 tools/d9m/narration_example_seq.py …`（armA） | `python3 tools/d9n/narration_example_seq.py …` | rc≠0 |
| 5 | `:359` | 同上（armB） | 同上 | rc≠0 |
| 6 | `:420` | 交付清单 `tools/d9m/…` | `tools/d9n/…` | 被判「未交付」 |
| 7 | `:421` | 交付清单 `tools/d9m/…` | `tools/d9n/…` | 被判「未交付」 |
| 8 | `:414` | `sha256sum v2/refs/D9m-prereg-narration-rotation.md` | `sha256sum v2/refs/D9n-prereg-narration-example-rotation.md` | rc≠0（旧路径已随 `5f302dc` 消失） |

**机械替换规则**：`tools/d9m/` → `tools/d9n/`（basename 不变）；旧预登记路径 → `D9n-prereg-narration-example-rotation.md`。**主件本体不改。**

### ⑤.1 每条读数的「命令 + 产物路径 + rc + sha256」

统一前缀：
```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
BASE=v2/evidence/narr-on-20261030      # B 臂（基线语料，code_sha 47a7da9）
ROT=v2/evidence/d9n-rot-20261030       # O 臂（本轮，code_sha df29cf9）
```

| 读数 | 复算命令 | 产物路径 | rc | sha256 |
|---|---|---|---|---|
| 六条判据（两臂） | `python3 tools/d9n/narration_family.py --log $BASE/run.jsonl --arm BASE --out /tmp/family_base.json`<br>`python3 tools/d9n/narration_family.py --log $ROT/run.jsonl --arm ROT --out /tmp/family_rot.json` | `$ROT/narration_family.stdout`（本臂落盘） | 0 / 0 | 工具 `tools/d9n/narration_family.py` = `3dbca76f1f387cd7df6bd1810cb1a0dcd1e347fb17c26d9f23ea9654628ee636`；词表 `tools/d9n/narration_family_lexicon.json` = `01e5533870f0f6b43300e6be6422130d958a01497a90d610620916f454489ed0` |
| Wilson 95% 区间（占比类） | `python3 tools/metrics/d9m_wilson_ci.py --in pairs.json --out wilson_ci.json` | `/tmp/rw_d9n/wilson_ci.json`（作者实跑） | 0 | 脚本 `tools/metrics/d9m_wilson_ci.py` = `b3b17206e710ce333ca62b946858de960befe9a41d668b9e123f02c1144040f4`；唯一天源 `tools/d5/dialogue_metrics.py` = `1d914735f3a13cf4e1640bd694f1d0e070096c9f50abfdefa7359417df551271` |
| Poisson 95% 区间（计数类） | `python3 tools/metrics/d9n_poisson_ci.py --in pairs.json --out poisson_ci.json`<br>`python3 tools/metrics/d9n_poisson_ci.py --selftest` | `/tmp/rw_d9n/poisson_ci.json`（作者实跑） | 0 / 0（自检 5/5 PASS） | 脚本 `tools/metrics/d9n_poisson_ci.py` = `c4307f225968ac330e409dd6c2fecbda17128a56542bde5299b97ea493dea31f` |
| 官方对话指标 | `python3 tools/d5/dialogue_metrics.py --log $ROT/run.jsonl --meta $ROT/meta.json` | `$ROT/dialogue_metrics.json` | 0 | `e8e63f5eb34acd7a0030cb7b4e6ba664ef219688cbe161fc135a58e204618eaf` |
| 旁白统计（管道口径） | `python3 tools/d9i/narration_stats.py --log $ROT/run.jsonl --arm ON_ROT` | `$ROT/narration_stats.json` | 0 | 工具 `tools/d9i/narration_stats.py` = `8ddb9111072c9ef71e7853dc7b455d618352b2baf44492d0576e440467627e85` |
| 成本 / provider 验真 | `cd code && python3 -m obs llm-cost --log ../$ROT/run.jsonl --require-provider openai_compat` | `$ROT/llm_cost.json` | 0 | `80427b019ea93545a1b2ba061327496efb701a45c833f6474c24d12ae84929b3` |
| 日志指纹 | `sha256sum $ROT/run.jsonl $BASE/run.jsonl` | — | 0 | `e4fd6db7f863fe2f6bcf6e06753600783ce57505b48a10d5c97247bf5866ece1` / `fdb31c7e2ca64b4dac1466fd4c81770dc0198ced4904584a3faf59939fd663ee` |
| meta 凭据 | `sha256sum $ROT/meta.json` | `$ROT/meta.json`（27663 B） | 0 | `9084ecda1c0bafaa29c23bc601b5137669535dbc84b5586879f9a1e69ba96da8` |
| `(b2′)` 逐条片段 | 见 §⑤.2 内联脚本 | `/tmp/rw_d9n/b2p_fragments.txt`（作者实跑） | 0 | — |
| 词面计数（围裙/锉刀/木屑/木花/手） | 见 §③.5 内联脚本（复用 `nf.read_log` + `nf.PAIRED_RE`，对片段计数） | 本报告 §③.5 表（作者实跑） | 0 | 同 `narration_family.py` 指纹 `3dbca76f…` |

**Poisson 区间方法论说明（放在证据段，不单独成节）**：
> 区间实现为 Garwood 精确法（标准库 `math` 自实现 `chi2.ppf`，**无 scipy**）；自检含两层：与公开表值比对（容差 1e-3）**以及**不依赖任何表的定义式校验（泊松求和验 `P(X≤x|hi)=0.025`、`P(X≥x|lo)=0.025`，容差 1e-6）。参考读数：`x=9 → [4.115373, 17.084803]`、`x=31 → [21.062996, 44.002026]`、`x=0 → [0, 3.688879]`。

### ⑤.2 `(b2′)` 逐条明细（`蹭｜锉刀` 族，两臂全列，**不写总数了事**）

B 臂 **9 条**（`total=9`；逐角色 P014 3 / P013 3 / P011 2 / P002 1 ⇒ `n_ge2=3`）：

| # | agent | round | seq | 类型 | 片段原文 |
|---|---|---|---|---|---|
| 1 | P014 | 0 | 178 | DM | 拿锉刀在铜片边上蹭了两下 |
| 2 | P013 | 1 | 1326 | PUBLIC | 拿锉刀蹭着犁头缺口 |
| 3 | P011 | 4 | 3982 | DM | 用锉刀蹭着铜片边 |
| 4 | P013 | 4 | 4182 | PUBLIC | 拿锉刀蹭了蹭犁头边 |
| 5 | P011 | 7 | 6525 | DM | 拿锉刀蹭着铜片边，铜屑落了一裤腿 |
| 6 | P014 | 7 | 6955 | DM | 拿锉刀蹭了蹭凳角，木屑落在鞋面上 |
| 7 | P002 | 13 | 20288 | DM | 拿锉刀在木马耳朵上蹭了两下，木屑落在鞋面 |
| 8 | P013 | 13 | 21068 | PUBLIC | 拿锉刀蹭了蹭铁砧上那把豁口的柴刀 |
| 9 | P014 | 19 | 25868 | DM | 拿锉刀蹭着赵家铁环的毛边，肚子咕噜响了一声 |

O 臂 **6 条**（`total=6`；逐角色 P013 3 / P014 2 / P002 1 ⇒ `n_ge2=2`）：

| # | agent | round | seq | 类型 | 片段原文 |
|---|---|---|---|---|---|
| 1 | P013 | 1 | 1326 | PUBLIC | 拿锉刀蹭着犁头边上的毛刺 |
| 2 | P013 | 4 | 4182 | PUBLIC | 拿锉刀蹭了蹭犁头边 |
| 3 | P014 | 7 | 6955 | DM | 拿锉刀蹭了蹭鱼尾的毛边 |
| 4 | P002 | 13 | 20276 | DM | 拿锉刀蹭了蹭刚削的竹钉尖 |
| 5 | P013 | 13 | 21056 | PUBLIC | 拿锉刀蹭了蹭砧子边角 |
| 6 | P014 | 19 | 25856 | DM | 拿锉刀背蹭了蹭锁舌上的毛刺 |

复算脚本（内联，读日志 → 归族 → 打印逐条）：
```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
PYTHONPATH=tools/d9n python3 - <<'EOF'
import importlib.util, json
from pathlib import Path
spec=importlib.util.spec_from_file_location("nf","tools/d9n/narration_family.py")
nf=importlib.util.module_from_spec(spec); spec.loader.exec_module(nf)
lex=nf.load_lexicon(Path('tools/d9n/narration_family_lexicon.json'))
V=nf.v_judge(lex); PARTS=lex['parts_6']; OBJS=lex['objs_13']
for tag,log in (('BASE','v2/evidence/narr-on-20261030/run.jsonl'),('ROT','v2/evidence/d9n-rot-20261030/run.jsonl')):
    rows=[]
    for r in nf.read_log(Path(log)):
        body=(r.get('payload') or {}).get('body') or ''
        for m in nf.PAIRED_RE.finditer(body):
            inner=m.group(0)[1:-1]
            if nf.assign_family(inner,V,PARTS,OBJS).get('family')=='蹭|锉刀':
                rows.append({'agent':r.get('actor'),'round':r.get('round'),'seq':r.get('seq'),'type':r.get('type'),'inner':inner})
    print('==',tag,'count=',len(rows))
    for x in rows: print(json.dumps(x,ensure_ascii=False))
EOF
```

---

## ⑥ 真实截图（替代像素自检，非原生空白判据）

| 图 | 视图 | PNG 路径 | 字节 | sha256 |
|---|---|---|---|---|
| **图1（本臂）** | `chat` | `v2/evidence/d9n-rot-20261030/shots/d9n-rot-chat-e4fd6db7.png` | 281415 | `7f719dd23815fe762283079660ca6edef18d34b67037dc96795c788e61a99a06` |
| **图2（本臂）** | `rhythm` | `v2/evidence/d9n-rot-20261030/shots/d9n-rot-rhythm-e4fd6db7.png` | 279838 | `64731780deb85c18d80bc186593319c01e049a7eab25814765cb6ec06c848c54` |

- **生成命令**（roll 出图，作者已实跑同构命令于基线，本臂由 batch-runner 实跑并落盘）：
  ```bash
  python3 tools/metrics/render_shots.py --run-dir v2/evidence/d9n-rot-20261030 \
      --batch-id d9n-rot --outdir v2/evidence/d9n-rot-20261030/shots --views chat,rhythm
  ```
  `render_shots.rc=0`；`render_report_d9n-rot.json` sha256 `d085d385954173de3fb8cfb54dbcb7e0b969f2b9cc35909361e1f50d24d71127`；`ok_count=2 / fail_count=0`。
- **空白判据口径（必须照此读，不得写「空白图自检通过」）**：
  > 截图采用**替代像素自检**（`distinct_colors ≥ 200` 且 `top_color_frac ≤ 0.99`）；原生 `_BLANK_FRAC` 判据因深色主题假红率 80.09% 被显式关闭（`--no-blank-check`），规则出处见 `render_report.policy.blank_check`。
- **实测读数**：`chat` `distinct_colors=23157 / top_color_frac=0.16 / non_bg_frac=0.5282`；`rhythm` `20827 / 0.3707 / 0.3873`；两图 `status=OK`、`blank_retries` 未触发。
- **「渲的是本批」的绑定**：`render_report.run_sha256_in_threads` = **`e4fd6db7f863fe2f…`** = `meta.run_sha256` = `$ROT/run.jsonl` 的 `sha256`。三者同值 ⇒ 图像内容来自本批日志，而非旧图或另造。
- **作者侧交叉出图（基线臂，独立于 batch-runner）**：`python3 tools/metrics/render_shots.py --run-dir v2/evidence/narr-on-20261030 --batch-id d9n-base --outdir /tmp/rw_d9n/shots_base --views chat` → `ok_count=1 / fail_count=0`，PNG `0146472ba4d91cbf40d8668887599c649e616487b1fbdaa9ba2ec432352d2ae4`（302862 B），`run_sha256_in_threads` = `fdb31c7e…` = 基线日志 sha256 ⇒ 同法可用基线重现。
- **纪律**：每张图独立截图，**非拼图、非跨批混拼、无旧图**；截图**不进任何判据**，仅作展示材料。

---

## ⑦ 机制层 vs 行为层（分节，不混用）

**分层两句（必须分开读，不得合并成一句）**
- **机制层：成功。** 守卫双过（`coverage 0.351485 ≥ 0.193171`、`unassigned 0.648515 ≤ 0.778049`）+ `degraded=0` + `replay_parity=True` + `provider={openai_compat:2252}` ⇒ **测具与装置正常，非测具失效**。
- **行为层：未改善。** `(b2′)` 未达成立条件、`(d)` 基线即不可行、`(e)` 新增越线 1 条、禁用词面**未下降** ⇒ 无任何「语言/生活气息变好」的可判证据。

**机制层（可数、可复算，本节全部结论只到此为止）**
- 开关生效：轮换 env 在启动器内联环境为 `1`（§0.4）；`蹭` 31→24、`蹭｜锉刀` 9→6 ⇒ **示例句替换在生成面上确实起了作用**。
- 分布重排：`挪` 7→12、`拍` 0→8、`擦` 0→3，并出现 `拍｜手` 8 次的新族固化。
- 越线族数量不变（7→7），构成变化（3 进出）。
- 守卫双过（`coverage 0.351485`、`unassigned 0.648515`）⇒ 尺子在本臂语料上有效。

**行为层（本轮不给结论）**
- 「旁白是否更自然 / 动作是否更多样 / 对话是否更像真人」——**本轮不可判**。
- 理由：(i) 唯一可能翻绿的主判据 `(b2′)` 差异不显著（`z=0.775`，`p≈0.44`）；(ii) `(c-2)` 咬合率恒不可判；(iii) 结构指标改善**不等价于**语言质量改善（R3 已证 judge 五维不可区分）；(iv) 本报告未做人工盲评。
- **禁止**把机制层任何读数表述为「更自然」「更像真人」。

---

## ⑧ 边界与不可比声明

1. **与 master 线不可比**：本地 `6fda371` 与远端 `7cd10f9` 均无旁白实现（§0.1）；本轮 sha 不代表 master 现状。
2. **与 D9i 报告不可比**（`reports/CYCLE-30-20261030.md`，锚 `43bbc8a`，两臂 `code_sha=47a7da9`）：本轮 O 臂为 `df29cf9`，且**B 臂直接复用 D9i 的 ON 臂日志**⇒ 跨基准比较，只作参照不作证据。
3. **与 d9k 诊断（测自 `47a7da9`）不可比**：该 sha 已被裁定「不可用作基准」，`dd7e3fb` 线须重算自己的基线。**本报告默认不引用 d9k 数字**；若读者手上有，须自行加「不可比」标注。
4. **样本量与功效**：n=16 agents、seed=42、rounds=24、单批 191 MSG / 202 片段；**单 seed、单批次，不外推**。`(b1)` n=8（Wilson 半宽 ±27pp）、`(b2′)` 计数 6–9（`z=0.775`）⇒ **本轮判据普遍处于功效边缘**，这正是 §④ 缺陷 3 的现实后果。
5. **结构改善 ≠ 更自然**：本报告全部读数为结构/计数层，**不得**推导语言质量结论。
6. **工作区非冻结**：结论锚定 commit sha（`df29cf9`）与日志 sha256，不锚定「当前树全部字节」；收批窗口内 `scope=仓库零字节改动` 有 verifier 独立佐证（3044 文件 manifest 在 08:27:41–08:30:15 窗口零漂移），唯一新增 `tools/metrics/d9n_poisson_ci.py` 为**收批后**创建。
7. **两臂 cache 不对称**（§0.5）：不得读作两臂同构；但 `dialogue` 侧 `cached=0` 两臂一致。
8. **区间口径分歧已披露**（§③.1）：Wald 与 Garwood 两套并列，结论一致。
9. **回执终版 sha 不可自指**（§①）：本报告记读取时刻实测值，不主张其为最终值。
10. **本报告未做**：未做人工盲评、未做 `(c-2)` 咬合率判读、未把 `(d)` 当作对旋转效果的检验、未使用并行线任何读数。

---

## ⑨ 入库与核对

- 分支：**`feat/life-narration-rotation`**（不推 master）。
- 本分支不含并行线文件与旧编号文件，核验命令（定稿时重跑，输出见下）：
  ```bash
  git ls-tree -r --name-only HEAD | grep -c 'action-diversity'   # 期望 0
  git ls-tree -r --name-only HEAD | grep -c 'D9m-'               # 期望 0
  git ls-tree -r --name-only HEAD | grep -c 'D9n-'               # 期望 ≥1
  ```
  **实测（在报告 commit `accad13` 上重跑，作者实跑）**：`action-diversity` = **0**；`D9m-` = **0**；`D9n-` = **9**（主件 + 增补 01–06 + anchor 等，随 `5a9b5a2`/`de4649c` 等提交计入）。
  ```bash
  git ls-tree -r --name-only accad13 | grep -c 'action-diversity'   # 0
  git ls-tree -r --name-only accad13 | grep -c 'D9m-'               # 0
  git ls-tree -r --name-only accad13 | grep -c 'D9n-'               # 9
  ```
- 提交内容（**路径限定 add，禁 `-A`/`.`**）：本报告 + `tools/metrics/d9m_wilson_ci.py` + `tools/metrics/d9n_poisson_ci.py` + 本报告所引截图与 `render_report`。
- 提交前自检：`git status --porcelain` 与 `git diff --cached --name-status` 的 staged 清单**只含上述文件**（不含他人在编的 `code/life/agent.py`）。
- 时序前提：impl 两枚 commit（`5d20cc5` 实现、`df29cf9` 测试同步）已在分支上，报告 commit 晚于二者。
- push：先 `git ls-remote --heads origin feat/life-narration-rotation` 探针，记录 rc 后 push；失败则落 `push.rc` 并如实记录，**不伪造成**成功、不改写历史。

---

## 附录 · 作者自检声明（本报告的边界）

1. **我独立复算并逐位对上的**：两臂 `(a)(b1)(b2′)(c-1)(d)(e)` 全部读写（实跑 `narration_family.py` 两臂，rc=0）；`(b2′)` 9 条 / 6 条逐条片段（自写内联脚本，落 `/tmp/rw_d9n/b2p_fragments.txt`）；`(e)` 越线条目定位（P013 r3 seq 2209，三段片段与动词 `压/夹/敲`）；`蹭/挪/拍/擦` 四项计数；两臂 `run.jsonl` sha256；`meta.json` 关键字段（events 33826、code_sha、seed、rounds、llm_calls 2252、fallback false）；`llm_cost.json` 的 `dialogue.cached=0`、`by_provider`、`degraded=0`；Wilson/Poisson 两套区间（各自 `--selftest` 通过）；`D9n-prereg-*` 六枚 sha256；`tools/d9n/` 五件 blob sha（`5f20612`）。
2. **我未独立复算、仅引文件的**：`dialogue_metrics.json` 的 `L-1/L-3/L-7` 明细（引官方工具输出，未逐条重算 8-gram）；基线语料的 `code_sha=47a7da9` 『与 base 在 `code/` 零差异』这一等价性（引 `d9m_baseline_judgement.json::corpus.code_identity_note`）。
3. **明示为「不可判 / 证据不足」而未据此下结论的**：`(c-2)` 咬合率；行为层语言质量；`(b2′)` 的「下降」统计主张（区间重叠、`p≈0.44`）；回执终版 sha；`meta` 级开关取证。
4. **我明确改写的两处口头数**：①起跑失败代价一律以 systemd journal 为唯一来源、写「**约 1 秒**」（曾误写 21 秒、口述 43 秒，均与 journal 不符，已在 §①-2 记录该三次更正）；②`(b2′)` 区间并列 Wald 与 Garwood 两套，不单方面采用其中一套。
5. **锚定**：本报告基于 `code_sha=df29cf9abc056d7982f01a1ffe10e5c5b4ccd15b`（O 臂，分支 `feat/life-narration-rotation`）与基线语料 `47a7da9`（`v2/evidence/narr-on-20261030/run.jsonl`，sha256 `fdb31c7e…`）。若提交前 HEAD 前进，§⓪ 的身份段需重新核对。
