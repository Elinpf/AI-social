# R21 · 处境/场景细节：F-8 处境锚（`LIFE_PROMPT_SCENE`）同树配对臂

> **本轮主判定为「不可判」，触发条为预登记 §5.1 否决条款中的 `F-8a = not_applicable`。**
>
> **紧接着必须同屏读到的两项主判据实测值（`Δ ≥ +3.0pp` 且两臂 Wilson 95% CI 不重叠）；它们达到预登记阈值，但**不是主判定**，不得单独引用为结论**：
> - `F-8t_core`：OFF **1/191 = 0.52%**（Wilson [0.09%, 2.91%]）→ ON **16/191 = 8.38%**（[5.22%, 13.17%]），**Δ = +7.85pp**，CI 不重叠；
> - `F-8p_place`：OFF **0/167 = 0%**（[0%, 2.25%]）→ ON **9/167 = 5.39%**（[2.86%, 9.92%]），**Δ = +5.39pp**，CI 不重叠；
> - `F-8a_activity`：OFF **`not_applicable(no_ctx_scene)`**；ON 12/179 = 6.70%（**单臂描述，无配对**）。
>
> **「不可判」不等于实验无效，也不等于效应不存在**；同理，「达到阈值」不等于「已证明」。本报告把这两件事分开写，任一单独引用都会失真。
>
> 附带产出：① 登记 1 处**预登记结构性缺陷**（§5.1 否决条恒真 ⇒「成立」在数学上不可达，与 `R15` 的「F1/F2 结构互斥」同型）；② 登记 1 处**工具字段缺陷**（`meta.code_sha` 语义，§2.2）。两处均**只登记、本轮不改**。
>
> **写作口径**：照 `reports/CYCLE-06-20261023.md` 的六元组 —— 数值 + 分母（口径）+ 判据编号 + 来源路径 + sha + 证据状态（`已验证` / `仅观察` / `未对账` / `不可判`）。
> **用词纪律**：不使用「提升 / 改善 / 显著 / 更自然 / 生活气息提升」。所有结论绑定本文件所在提交的 commit sha（见 §0 与文末回填）。

---

## 0. 文件身份与取数时刻

| 项 | 值 | 取法 |
|---|---|---|
| 报告文件 | `reports/R21-scene-pair.md` | 命名依据：`R<n>-<slug>.md`（`reports/README.md` 族索引，R1–R20 为既有序列） |
| 交付分支 | `feat/r21-scene-pair` | `git branch --show-current` |
| **报告绑定 sha（本文件首次入库 commit）** | `git log --diff-filter=A -1 --format=%H -- reports/R21-scene-pair.md`；该 sha 即本报告全部读数对应的提交（分支 `feat/r21-scene-pair`） | git |
| 两臂跑批代码身份 pin | ON `3bb44308291c8ea61d71ae0c595ff2e8b09b5502` / OFF `e878a6e5da57e5661d07ec2c3fbed91ea91b10a0`；两者 `code/` 树对象同为 `4e8727499a589b13a2972577090d71490e047883`（详见 §2.2） | `switch_proof.txt` / `host.log` |
| 取数时刻 | 2026-10-23 08:33–08:37 +0800 | `date '+%F %T %z'` |
| 预登记 | `v2/refs/prereg-r21-scene-anchor.md`，sha256 `0fc9107042735c726a3efc527d2d37d1fd5df81f31824fc29d29dbfaeb8c6670`（12614 B / 161 行） | `sha256sum` |
| 指标真源 | `tools/d5/dialogue_metrics.py` sha256 `1d914735f3a13cf4e1640bd694f1d0e070096c9f50abfdefa7359417df551271`（与 `v2/evidence/f8_metrics_selfcheck.txt` 的 `METRICS_GATE=PASS` 同一 sha） | `sha256sum` |
| F-8 词表 | `tools/d5/f8_lexicon.json` sha256 `004f3bca138e7800a0fc0ac7e0f1c0f0bdb9b0a862432fa53f65b152bdb2ddd3`（`f8-lexicon-v3`） | 同上 |

---

## 1. 本轮维度与动机

- **维度**：处境/场景细节 —— 台词是否带「时段 / 场所 / 手上事」（F-8 三分解）。本轮**只做这一个维度**。
- **动机（缺口是报告自述的，不是新提的）**：`reports/CYCLE-06-20261023.md` 判定表原文「**F-8 / 处身锚：无臂级读数；处身锚仅 ON 单臂且无 d5 指标 ⇒『不可判』**」。
- **本轮补的正是这一格**：机制代码已于 `59bad20` 入库（`code/life/scene_anchor.py`，21 项单测），ON 臂已跑并留证，**只差同树 OFF 臂**。

---

## 2. 改动范围（含两处必须披露的面）

### 2.1 改动清单

| 类别 | 内容 | 是否动 core |
|---|---|---|
| 行为代码 | **零改动**：`code/{life,engine,orchestration,config}` 一个字节未改；两臂跑批代码经树对象哈希证明等价（§2.2） | 否 |
| 跑批 | 新增 OFF 臂（`seed=42 / agents=16 / rounds=24 / flush_every=2`），与既有 ON 臂配对 | 否 |
| 新增跑批脚本 | `v2/evidence/run_scene_anchor_off_seed42_n16r24/launch_worktree.sh`（**本轮新增**，是 ON 臂 `launch.sh` 的同构改写：把「REPO 解析」从主树改为 worktree，保留全部门禁语义并新增闸门 0d「分支父提交必须 = `3bb4430`」）。**为什么必须另写**：ON 臂 `launch.sh` 把 `REPO` 写死为主树且闸门 0f 要求 `WT` 匹配主树；若把 worktree 塞进去，它会用**主树**（`a6d6be0`，含 L-13 改动）的 `code/` 去跑 OFF，与 `3bb4430` 的 ON 臂构成双变量 | 否 |
| 新增预登记 | `v2/refs/prereg-r21-scene-anchor.md`（从 worktree 拷入，**只拷内容不拷历史**，两处 sha256 逐位相同，`cmp` identical） | — |
| 新增证据 | `v2/evidence/d5_metrics_r21_scene_{on,off}.{json,md}`、`r21_f8_crosscheck_{on,off}.json`、`r21_scene_shots/`（8 PNG + `render.log`）、`run_scene_anchor_off_…/llm_cost.txt` | — |

复算脚本差异（可核）：

```bash
diff -u v2/evidence/run_scene_anchor_on_seed42_n16r24/launch.sh \
        v2/evidence/run_scene_anchor_off_seed42_n16r24/launch_worktree.sh | head -80
```

### 2.2 两臂代码身份（`meta.code_sha` 不一致的查证与**工具层缺陷登记**）

**结论：两臂跑批代码等价**，证据为内容寻址级；但 `meta.code_sha` 这个字段**语义有缺陷**，它把「跑批后与代码无关的 commit」记成 code_sha，在读者眼里制造「两臂代码不同」的假象。

**字段语义（源码级）**：`tools/d2/emit_run_meta.py:214` / `:224` 均为 `_git("rev-parse", "HEAD")`，`_git` = `subprocess.check_output(["git", *args], cwd=ROOT)`（同文件 `:48-50`），`ROOT` = 脚本所在树的仓库根。
⇒ `code_sha` = **生成 meta 那一刻**的 HEAD 快照，**不是**起跑时钉住的 sha，**不是** `code/` 子树指纹，**不是** engine_version。

**起跑时钉住的 sha（权威 pin，launcher 在起跑瞬间写下）**：

| 臂 | `switch_proof.txt` | `host.log` |
|---|---|---|
| ON | `HEAD: 3bb44308291c8ea61d71ae0c595ff2e8b09b5502`（`:6`） | `code_sha=3bb44308…`（`:5`） |
| OFF | `HEAD: e878a6e5da57e5661d07ec2c3fbed91ea91b10a0`（`:6`） | `code_sha=e878a6e5…`（`:4`） |

> **经实测纠正**（审计链不许写顺）：起跑头**不是**两个相同的 sha —— ON 臂 `3bb4430`、OFF 臂 `e878a6e`（二者为父子关系；OFF `switch_proof.txt:17` 原文「父提交(基线)=`3bb4430…`」）。`meta.code_sha` 的 ON/OFF 值为 `d30520c` / `44e3710`，均为**收批后** HEAD。

**`code/` 内容等价证明（内容寻址，比 diff 更硬）**：

```bash
for c in 3bb4430 e878a6e 44e3710 d30520c a6d6be0; do printf "%-10s %s\n" "$c" "$(git rev-parse $c:code)"; done
```

| commit | `code/` 树对象 |
|---|---|
| `3bb4430`（ON 起跑头） | `4e8727499a589b13a2972577090d71490e047883` |
| `e878a6e`（OFF 起跑头） | `4e8727499a589b13a2972577090d71490e047883` |
| `44e3710`（OFF 收批后） | `4e8727499a589b13a2972577090d71490e047883` |
| `d30520c`（ON 收批后） | `4e8727499a589b13a2972577090d71490e047883` |
| `a6d6be0`（主树，**对照**） | `e0566d1e6ead9f410701deb663b7f600c784790b` ← 不同（L-13 改动只在主树） |

辅助：两两 `git diff --stat -- code/` 全为空（`3bb4430..e878a6e`、`3bb4430..44e3710`、`e878a6e..44e3710`、`d30520c..3bb4430`、`d30520c..44e3710`）。

**日志内 config 身份（`meta.code_identity_note` 指定的第二项硬证据）**：

| 字段 | ON | OFF | 同否 |
|---|---|---|---|
| `WORLD_INIT.config_components`（12 个配置文件 sha256） | 逐项 | 逐项同 | **全等** |
| `config_digest` | `sha256:58485c06…1f112f` | 同 | **相同** |
| `fingerprint` | `sha256:a871e36c…8f3b1c` | 同 | **相同** |
| `engine_version` | `v0.1-skeleton` | 同 | **相同** |
| `seed` / `time_U` / `time_model` | `42` / `6` / `atomic` | 同 | **相同** |

**⚠️ 工具层缺陷登记（本轮附带发现，**本轮不改工具，只登记**）**

`meta.code_sha` 取「生成 meta 时」的 HEAD ⇒ 任何在跑批期间发生的、**与代码无关**的提交（本轮即只改 `v2/refs/` 的 `44e3710`）都会被记成 code_sha，使同代码的两臂在读者眼里像是「跑在不同 commit 上」。
**修复建议**（供后续轮次采纳）：把 pin 改为**起跑瞬间** `git rev-parse HEAD` 落盘（launcher 已有 `switch_proof.txt` 可承载），或直接记 **`code/` 子树对象哈希**（`git rev-parse HEAD:code`）——后者对「非 code 路径的提交」天然免疫。

**未跟踪目录的不对称（如实披露，不淡化）**

`meta.git_dirty_code_files`：ON 臂 3 条、OFF 臂 `[]`。
- ON：`?? code/frontend/sample/dialogue_cycle03_ctrl/`、`?? code/frontend/sample/dialogue_cycle04_a5/`、`?? code/v2/`
- 全部是**未跟踪目录**（没有已跟踪文件被修改）；已跟踪内容零差异已由 §2.2 树对象哈希证明。
- `code/v2/` 是否构成导入面：**已反证** —— `cd code && python3 -c "import v2"` → `ModuleNotFoundError: No module named 'v2'`；`code/v2/` 下**无 `__init__.py`**；`sys.path` 首项为 `code/` 而非 `code/v2/`。⇒ 该影子目录**不构成导入面**（复查命令见附录 A）。

---

## 3. 可复算命令与统计口径

### 3.1 命令（第三方可照抄，全部在本轮实跑过）

```bash
ROOT=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
cd "$ROOT"
OFF_RUN=.worktrees/scene-pair-r21/v2/evidence/run_scene_anchor_off_seed42_n16r24
ON_RUN=v2/evidence/run_scene_anchor_on_seed42_n16r24

# 0) 串行纪律（起跑前；不要用含裸 run_batch 字样的命令行调 preflight，会自匹配假阳性）
pgrep -f "[o]rchestration run"        # 本轮：无命中（rc=1）

# 1) 真 LLM 验真（唯一判决口径，rc==0 才算真跑）
cd code && python3 -m obs llm-cost --log ../$OFF_RUN/run.jsonl --require-provider openai_compat \
  > ../v2/evidence/run_scene_anchor_off_seed42_n16r24/llm_cost.txt ; echo rc=$?
cd code && python3 -m obs llm-cost --log ../$ON_RUN/run.jsonl --require-provider openai_compat \
  > ../v2/evidence/run_scene_anchor_on_seed42_n16r24/llm_cost.txt ; echo rc=$?
cd "$ROOT"

# 2) 两臂指标（唯一真源；口径冻结，不得改参数）
python3 tools/d5/dialogue_metrics.py --log $ON_RUN/run.jsonl  --meta $ON_RUN/meta.json \
  --out-json v2/evidence/d5_metrics_r21_scene_on.json  --out-md v2/evidence/d5_metrics_r21_scene_on.md  --arm ON
python3 tools/d5/dialogue_metrics.py --log $OFF_RUN/run.jsonl --meta v2/evidence/run_scene_anchor_off_seed42_n16r24/meta.json \
  --out-json v2/evidence/d5_metrics_r21_scene_off.json --out-md v2/evidence/d5_metrics_r21_scene_off.md --arm OFF

# 3) F-8 交叉复算（非指标真源，只作交叉校验；不一致 exit 3）
python3 tools/d9/f8_crosscheck.py --log $ON_RUN/run.jsonl  --lexicon tools/d5/f8_lexicon.json \
  --expect-json v2/evidence/d5_metrics_r21_scene_on.json  --out v2/evidence/r21_f8_crosscheck_on.json
python3 tools/d9/f8_crosscheck.py --log $OFF_RUN/run.jsonl --lexicon tools/d5/f8_lexicon.json \
  --expect-json v2/evidence/d5_metrics_r21_scene_off.json --out v2/evidence/r21_f8_crosscheck_off.json

# 4) 机制闸 M1（单测）
cd .worktrees/scene-pair-r21/code && python3 -m pytest life/tests/test_scene_anchor.py -q
cd "$ROOT"

# 5) 出图（真渲染；两臂分别入库，禁止拼图）
python3 code/frontend/tools/gen_threads.py --log $ON_RUN/run.jsonl --meta $ON_RUN/meta.json \
  --out code/frontend/sample/dialogue_r21_scene_on/threads.json --require-complete \
  --label run_scene_anchor_on_seed42_n16r24-8a5a88ac
python3 code/frontend/tools/gen_threads.py --log $OFF_RUN/run.jsonl \
  --meta v2/evidence/run_scene_anchor_off_seed42_n16r24/meta.json \
  --out code/frontend/sample/dialogue_r21_scene_off/threads.json --require-complete \
  --label run_scene_anchor_off_seed42_n16r24-4d70674e
# 前置：静态服务在 8848（cd code && python3 frontend/tools/serve.py）
cd code && bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 sample/dialogue_r21_scene_on/threads.json  "" "" ../v2/evidence/r21_scene_shots
cd code && bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 sample/dialogue_r21_scene_off/threads.json "" "" ../v2/evidence/r21_scene_shots
```

### 3.2 统计口径（判定/非判定通道严格分离；`denominator_rule` 引 `tools/d5/dialogue_metrics.py::compute_f8()` 原文）

**（1）判定通道（只有这两项进主判定，`F-8a` 见 §5 说明）**

| 通道 | 键 | 分子 | 分母 |
|---|---|---|---|
| 时段 | `F-8t_core` | 正文命中**档内时段词**（排除 `slot_agnostic`「这会儿」类通用指示词）的 `MSG_*` | **有 slot 的 `MSG_*`** |
| 地点 | `F-8p_place` | 正文含**本人 place** 名称（`places.json::name_cn` ∪ 可接受简称） | **有 `payload.place` 的 `MSG_*`**（24 条 `MSG_PUBLIC` 无该字段，另列 `F-8p_public`，**不参与判定**） |

**（2）严禁进判定的通道**：`F-8t_all`（原文「只能用于『词汇使用』结论，**不得用于处境锚定裁定**」）、`F-8t_time`、`F-8t_time_pre_am2`、`F-8t_broad_scoped`、`F-8t_open_any`、`F-8t_render_echo`、`F-8t_ckpt_narrow/wide`、`F-8_with_all_time`、`F-8p_public`、`F-8p_open_any_cn`、`F-8p_short_only`、`F-8a_render_only`。

**（3）三条硬规则**

1. **D-1 退化**：某通道 `numerator == 0` 时不许出两比例检验/p 值，只报绝对率 + Wilson 95% CI。本轮工具 `degenerate_d1` 另有说明：「**OFF 臂 F-8 分子 ≤ 2 ⇒ 两比例检验不适用，只报 ON 臂 x/n + 标准 Wilson 95% CI**」——本轮 OFF 两项分子为 `1` 与 `0`，**故本文不报两比例 p 值**，只报两臂各自率与 CI（CI 不重叠的比较照做，见 §5）。
2. **分母不同源**：`F-8t`（191）/ `F-8p`（167）/ `F-8a`（ON 179、OFF 0）三者**不是一个数**，不得合并。
3. **硬失败**：`guard.place_id_in_body > 0`（正文出现 place 内部 id，对应 `L-8c`）⇒ 批次无效；本轮 **0/191（ON）与 0/191（OFF），未触发**。

**（4）判定档（预登记 §5.1 原文）**：`Δ = 100 × (ON − OFF)`（pp）；**成立** ⇔ `Δ(F-8t_core) ≥ +3.0pp` **且** `Δ(F-8p_place) ≥ +3.0pp` **且** 两项各自两臂 Wilson 95% CI 不重叠；**部分成立** ⇔ 仅一项满足；**未达标** ⇔ 两项 `Δ < +3pp`；**不可判** ⇔ 两臂 CI 重叠 / 分母 < 30 / `F-8a = not_applicable` / 任一守卫击穿。
**B2 带不覆盖 F-8**（预登记 §5.1 明写），故以**两臂 Wilson 95% CI 是否重叠**作上界替代，**不借用他项带宽**。

---

## 4. 原始数据 / 日志路径

| 臂 | 目录（`v2/evidence/…`） | 关键文件 | 说明 |
|---|---|---|---|
| ON | `run_scene_anchor_on_seed42_n16r24/` | `meta.json`（events **33828**、`duration_sec` **1177**）、`host.log`、`switch_proof.txt`、`launch.sh`、`llm_cost.txt`（本轮补落） | `run.jsonl` **17,180,516 B**，sha256 `8a5a88ac1e57c1e692d90221dfdc794acc6f8e49ca212b6c233b684f95b6c1a9`（**不入库**，`.gitignore:8 **/*.jsonl`） |
| OFF | `run_scene_anchor_off_seed42_n16r24/` | `meta.json`（events **33846**、`duration_sec` **1289**）、`host.log`、`switch_proof.txt`、`launch_worktree.sh`、`llm_cost.txt` | `run.jsonl` **17,161,028 B**，sha256 `4d70674e0be7dcf24b92ecd73ed01062f03cf41d483464dc85ec538a2060c7e6`（**不入库**；正本在 worktree，主树未复制） |
| 指标 | `d5_metrics_r21_scene_{on,off}.{json,md}` | sha256：on `65b40c8a…d0296` / `d2f8996c…a4e88`；off `54c04a59…682f7` / `eb6fe57a…1b6e` | — |
| 交叉复算 | `r21_f8_crosscheck_{on,off}.json` | 两臂均 `MATCH` | — |
| 截图 | `r21_scene_shots/` | 8 PNG + `render.log` | 见 §7.1 |
| 前端数据集 | `code/frontend/sample/dialogue_r21_scene_{on,off}/threads.json` | sha256：on `d0b59d48…c3b`；off `35aa8b52…2540` | 各 191 消息 / 66 线程 |

---

## 5. 改动前后对比（OFF → ON）

### 5.1 F-8 主表（判定通道 + 登记通道分列）

| 指标 | OFF 臂 | ON 臂 | Δ（pp） | 判据（预登记 §5.1） | 判定 | 证据状态 |
|---|---|---|---|---|---|---|
| **`F-8t_core`**（时段·判定） | **1/191 = 0.5236%**，Wilson [0.0925%, 2.9056%] | **16/191 = 8.3770%**，[5.2219%, 13.1732%] | **+7.8534** | `Δ ≥ +3.0pp` 且 CI 不重叠 | **该条满足** | `已验证`（交叉复算 MATCH） |
| **`F-8p_place`**（地点·判定） | **0/167 = 0%**，[0%, 2.2486%] | **9/167 = 5.3892%**，[2.8609%, 9.9238%] | **+5.3892** | 同上 | **该条满足** | `已验证` |
| `F-8a_activity`（活动） | **`not_applicable(no_ctx_scene)`**（分母 0：191/191 条无 `ctx.scene.activity`） | 12/179 = 6.7039%，[3.8762%, 11.3509%] | — | — | **不可算**（原样写，**不填 0、不译作「0%」**） | `不可判` |
| `F-8t_all`（宽口径，**只登记**） | 5/191 = 2.6178%，[1.1232%, 5.9807%] | 25/191 = 13.0890%，[9.0253%, 18.6082%] | +10.4712 | **不得用于裁定** | 登记项 | `仅观察` |
| `F-8`（综合，信息性） | 5/191 = 2.6178% | 38/191 = 19.8953% | +17.28 | 不进判定 | 登记项 | `仅观察` |
| `F-8p_public`（覆盖说明，不判） | 2/24 = 8.3333% | 3/24 = 12.5% | +4.17 | **不作判定** | 登记项 | `仅观察` |

> **D-1 说明**：OFF 两项分子 ≤ 2 ⇒ 按工具 `degenerate_d1` 规则**不做两比例检验、不报 p 值**；上表只给两臂各自率与 Wilson 95% CI。
> **时段词的组成**（可核）：ON 的 16 条 `F-8t_core` 命中里，档内词分布见 `d5_metrics_r21_scene_on.json` 的 `F-8_scene_anchor.F-8t_core.hits_by_token`（如「下午」「擦黑」等，逐词条数见文件）；「这会儿」属 `slot_agnostic`，**不计入 core**，只计入 `F-8t_all`。

### 5.2 守卫（任一击穿 ⇒ 效果「不可判」）

| 编号 | 守卫 | 阈值（预登记 §6 原文） | OFF | ON | 结论 | 证据状态 |
|---|---|---|---|---|---|---|
| **G1** | L-13 内部 token 泄漏（事件数） | ON **>** OFF 即击穿 | **2**（1.0471%） | **1**（0.5236%） | **不击穿** | `已验证` |
| **G2** | L-7 8-gram 重复率 | `Δ > +9.043pp`（冻结带 `item:L-7` **denom=188 档** `hi_97.5`；本轮分母 191 ⇒ 取**最接近档 188**） | 14.6597% | 13.6126% | **Δ = −1.047pp，不击穿** | `已验证` |
| **G3** | L-1 长度 | `len_p50(ON) < 0.90 × len_p50(OFF)` 即击穿 | `p50` **43**（mean 44.97，p90 67） | `p50` **43**（mean 45.75，p90 64） | **不击穿**（0.90×43 = 38.7 ≤ 43） | `已验证` |
| **G4** | 结构三项 | 两臂差 `> ±5%` 即击穿 | 191 消息 / 66 线程 / 28 个 ≥3 轮线程 | **同值** | **不击穿（0% 差）** | `已验证` |
| **G5** | 真跑 | `rc≠0` / `provider_guard.ok≠true` / `degraded≠0` | rc=0 | rc=0 | **不击穿** | `已验证` |

**硬失败项**：`guard.place_id_in_body` OFF **0/191**、ON **0/191** ⇒ **未触发**「批次无效」。
（附：`guard.place_alias_hit` 两臂均 0/191，仅作归因抽样，不参与判定。）

### 5.3 机制闸（M1–M5；任一不过 ⇒ 写「机制未生效/批次无效」）

| 编号 | 判据 | 通过条件 | 实测 | 结论 |
|---|---|---|---|---|
| **M1** | 提示词接线（ON 减掉那一行 == OFF 逐字节） | 单测全绿 | `pytest life/tests/test_scene_anchor.py -q` → **28 passed**（worktree `3bb4430` 树） | **PASS** |
| **M2** | ON 臂 MSG 带 `ctx.scene` | ≥100% | `coverage.n_scene_present` = **191/191** | **PASS** |
| **M3** | OFF 臂 `ctx.scene` 不出现 | = 0 | **0/191** | **PASS** |
| **M4** | `ctx.scene.line_sha256` 可反解且与正文一致（ON） | 抽检一致率 100% | `n_line_sha_recovered` ON **191**、OFF **0**；`F-8t_exact` 通道见文件 | **PASS（ON）** |
| **M5** | 真跑 | 同 G5 | 两臂 rc=0、`openai_compat 2252`、`degraded 0`、`problems=[]` | **PASS** |

### 5.4 成本（同量级，无开关导致的调用暴涨）

| 项 | OFF | ON |
|---|---|---|
| `llm_calls` / `dialogue_calls` | **2252 / 191** | **2252 / 191** |
| `degraded_calls` | 0 | 0 |
| `E-2_tokens_out_per_dialogue_call` | 38.85 | 39.04 |
| `meta.duration_sec` | 1289 s | 1177 s |

---

## 6. 结论

### 6.1 主判定（一句）

**本轮主判定为「不可判」，触发条为预登记 §5.1 否决条款中的 `F-8a = not_applicable`。**

并列事实（**非主判定**，不得单独引用为结论）：两项主判据达到预登记阈值（CI 不重叠）—— `F-8t_core` **+7.8534pp**（0.5236% → 8.3770%）、`F-8p_place` **+5.3892pp**（0% → 5.3892%）；机制闸 M1–M5 全部通过；五项守卫 G1–G5 全部未击穿；硬失败项 `place_id_in_body` 两臂均 0/191。
`F-8a_activity` 在 OFF 为 `not_applicable(no_ctx_scene)`、ON 为 12/179 = 6.7039%（**单臂描述，无配对**，不作差值与判断）。

**D-1 执行说明**：OFF 分子为 `1` 与 `0`（均 ≤ 2）⇒ 按工具 `degenerate_d1` 规则**不出两比例 p 值**，只报 `x/n` + Wilson 95% CI。上文的「CI 不重叠」是**区间关系陈述**，不据此推断 p 值，也不使用「显著」一词。

### 6.2 预登记结构性缺陷登记（本轮发现；**未修改预登记一个字节**）

**（1）缺陷性质**

预登记 §5.1 把 **`F-8a = not_applicable`** 列为「不可判」的否决条件之一；但对照臂（OFF）关闭 `LIFE_PROMPT_SCENE` 时，`ctx.scene` **结构上必然不存在** ⇒ `F-8a` 在 OFF **恒** `not_applicable` ⇒ **该否决条恒真 ⇒「成立」在数学上不可达**。
同时，§5.1 的「成立」条件只要求 `F-8t_core` 与 `F-8p_place` **两通道**达标，**未把 `F-8a` 写入成立条件**，却把它写进否决条件 —— 一边要求两通道、一边否决三通道，**集合不一致**。

**（2）同型先例**

与 `reports/README.md` 所记 `R15` 缺陷同类，原文：「**F1 与 F2 结构互斥**（G-1b ≡ G-1）⇒ 按冻结判据 A1-措辞 数学上不可能被判『改善』」。本轮是同一类错误的另一实例。

**（3）修复建议（**建议，本轮未生效**；本轮 `v2/refs/prereg-r21-scene-anchor.md` 保持冻结未动）**

1. 否决条件应改为「**两臂均** `not_applicable`」；**单臂** `not_applicable` 属**结构性差异**（由开关定义决定），应作为**说明项**列示，不作否决项。
2. 「成立条件」与「否决条件」必须使用**同一组通道集合**：不允许一边按两通道判成立、一边按三通道否决。
3. 建议在预登记中显式区分「结构上不可能的取值」与「观测到的不良取值」，前者不得作为否决条。

> 若后续 Amendment 明确「`F-8a` 仅为说明项、不进否决条」，则依 §5.1 主判据本组读数对应「成立」——**该表述需 Amendment 生效后才可使用，本报告不作此结论**。

### 6.3 本轮相对 CYCLE-06 的位移

| 项 | CYCLE-06（原文） | 本轮之后 |
|---|---|---|
| 臂级读数 | 「F-8 / 处身锚：**无臂级读数**；仅 ON 单臂且无 d5 指标 ⇒『不可判』」 | **同代码树**（`code/` 树对象 `4e872749…`，两臂 `code/` 逐字节相同）的**配对读数**，各通道带分子/分母/Wilson CI |
| 判定 | 无判定（「不可判」的原因是**没有读数**） | 有判定，且**受预登记结构性条款限制判「不可判」**；两项主判据的达标情况同屏并列 |

**位移的唯一允许表述**：
> 「相对 CYCLE-06 的位移为：从『无臂级读数』推进到『有同代码配对读数并可判定，但受预登记结构性条款限制判不可判』。」

> 措辞纪律：主判定为「不可判」**不等于**本轮失败；本报告不写「本轮失败」，只写触发了哪一条规则、读数是什么。也不写「提升 / 改善 / 显著 / 更自然」。

---

## 7. 未取到 / 未验证（逐项登记）

### 7.1 截图（8 项，全部取到）

| 项 | 状态 | 证据 |
|---|---|---|
| OFF chat / rhythm / spread / 600 | **已取到** | `r21_scene_shots/run_scene_anchor_off_seed42_n16r24-{chat,rhythm,spread,600}-4d70674e.png`；`blank_retries=0/2`（逐张三行 `SHOT OK` 在 `render.log`） |
| ON chat / rhythm / spread / 600 | **已取到** | `…-{chat,rhythm,spread,600}-8a5a88ac.png`；`blank_retries=0/2` |
| 生成命令 | `bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 sample/dialogue_r21_scene_{on,off}/threads.json "" "" ../v2/evidence/r21_scene_shots` | 生成时刻 **2026-10-23 08:36**；`render.log` 65 行 |
| 真伪复核 | **已用视觉模型复核 ON-chat 图**：确为真实渲染（可见标题「青溪镇·对话观看台」、线程 66/多轮 32/消息 191、以及「天刚亮，手就闲不住。给老周家修的那把椅子，榫头还得再磨磨。」等台词），非空白/黑屏/报错页 | 未对 8 张逐一复核（只抽 1 张），其余 7 张仅凭 `blank_retries=0/2` 与亮度指标 |

### 7.2 真 LLM 验真

| 项 | 状态 | 证据 |
|---|---|---|
| OFF 臂 | **已取到** rc=0：`by_provider={"openai_compat":2252}`、`total.calls=2252`、`degraded=0`、`provider_guard.ok=true`、`problems=[]` | `run_scene_anchor_off_seed42_n16r24/llm_cost.txt` |
| ON 臂 | **已取到** rc=0，同上量级（2252） | `run_scene_anchor_on_seed42_n16r24/llm_cost.txt`（本轮补落；此前该臂缺此文件） |

### 7.3 口径与身份类

| 项 | 状态 | 说明 |
|---|---|---|
| `F-8a` | **`not_applicable(no_ctx_scene)`**（OFF） | 原样引用工具输出，**未**译作「活动锚定 0%」 |
| `degenerate` / D-1 | **已触发**（OFF 分子 1 与 0 ≤ 2） | 只报绝对率 + Wilson CI，**未**报 p 值、**未**写「无差异」 |
| 两臂代码身份 | **等价**（`code/` 树对象全等），pin 分别为 `3bb4430` / `e878a6e` | 见 §2.2；**未**把 code_sha 差异写成「双变量」 |
| `*.jsonl` | **未入库** | 仅以 sha256 索引（§4） |
| 单测 | **已跑**（M1，28 passed，worktree 树） | — |
| sim 预备 ON 读数 vs 本报告交付读数 | **数值逐项一致**，差异仅 **8 处绝对路径前缀**（工具所在树不同：worktree vs 主树），已做结构化 diff 逐条确认（`PATH_PREFIX_ONLY` × 8、`VALUE` × 0、`LEN` × 0、`MISSING` × 0），明细见附录 C 与 `v2/evidence/r21_on_metrics_crossrun_diff.json` | sim json `588cb26a…` / md `ad1b0efd…`；本报告 on json `65b40c8a…` / md `d2f8996c…`（**不作「逐字节一致」的表述**，因为确实不是逐字节） |
| 全套 `d5` 评测（`run_batch_eval.sh`） | **未跑** | 本报告直接调用真源 `dialogue_metrics.py` 生成两臂读数 + 交叉复算；`run_batch_eval.sh` 的 `d5_s0a`/purpose 审计未覆盖本轮（已跑项见 §5.4 的 `llm` 块） |

---

## 附录 A · 复算回执（本轮实跑原文摘要）

| 命令 | 结果 |
|---|---|
| `pgrep -f "[o]rchestration run"` | 无命中（rc=1） |
| `python3 -m obs llm-cost --log <OFF>/run.jsonl --require-provider openai_compat` | **rc=0**；`openai_compat 2252`；`degraded 0`；`provider_guard.ok=true`；`problems=[]` |
| `python3 -m obs llm-cost --log <ON>/run.jsonl …` | **rc=0**，同上 |
| `python3 tools/d5/dialogue_metrics.py … --arm ON/OFF` | 两臂 rc=0；产出 §4 四个文件 |
| `python3 tools/d9/f8_crosscheck.py …`（两臂） | 两臂均 `[f8_crosscheck] MATCH: F-8t_all / F-8t_core 分子分母与真源一致`，rc=0 |
| `pytest life/tests/test_scene_anchor.py -q` | `28 passed in 0.41s` |
| `python3 code/frontend/tools/gen_threads.py … --require-complete`（两臂） | `完整性断言通过：TURN_SEAL 24 条覆盖 round 0..23`；各 `messages=191 threads=66 multi_turn=32 ge3=28` |
| `bash frontend/tools/dialogue_shots.sh …`（两臂） | 各 `OK: …-{chat,rhythm,spread,600}-<sha8>.png`，`blank_retries=0/2` |
| `cd code && python3 -c "import v2"` | `ModuleNotFoundError: No module named 'v2'`（反证 `code/v2/` 非导入面） |
| `git rev-parse <sha>:code`（5 个 commit） | 四臂 commit 同为 `4e872749…`，主树 `e0566d1e…` |

## 附录 B · 截图清单（8 张，含 sha256）

| 文件 | sha256 |
|---|---|
| `run_scene_anchor_off_seed42_n16r24-chat-4d70674e.png` | `dea70b2edeac9deb8d2e29d0855192a0da7def2e80e1595e40c2f40f0ce03d02` |
| `run_scene_anchor_off_seed42_n16r24-rhythm-4d70674e.png` | `d759a6ac5ba459f5842b48dddb30e17f84d065fe5196204e0dcd401a4d6971d2` |
| `run_scene_anchor_off_seed42_n16r24-spread-4d70674e.png` | `bb5458f8aaa083408ca6f798a7bb126c7da9303e8a00ec7f89c7b67a8e411748` |
| `run_scene_anchor_off_seed42_n16r24-600-4d70674e.png` | `3c72cb8aa37fa7fb4ed75661968bebeb9b977b431b9b1b2eb831b77ef8b3d215` |
| `run_scene_anchor_on_seed42_n16r24-chat-8a5a88ac.png` | `50e5d6e4203c5aef2d289dcfd9ef2291419362dc8752b0fe9b4d25bbea64f0c2` |
| `run_scene_anchor_on_seed42_n16r24-rhythm-8a5a88ac.png` | `ec6acdf88ef18a6b7d6f0f4f9e884ad57c761ebbb3ae08779729de7d337fd44a` |
| `run_scene_anchor_on_seed42_n16r24-spread-8a5a88ac.png` | `f5948945c7f6c4ab6bebe0e007cc3342cc4dbe9fa53a2402e90de63707c4f5e1` |
| `run_scene_anchor_on_seed42_n16r24-600-8a5a88ac.png` | `36a7d5f5c40b3fc9c6296fc831e4348ae6e4a78e864f06fae52a930c4511e28e` |

## 附录 C · 独立复现：sim 预备 ON 读数 vs 本报告交付 ON 读数（结构化 diff）

- 文件：`v2/evidence/r21_on_metrics_crossrun_diff.json`（本附录的机器可读版，逐条列出 8 处差异）
- 对比对象：`.worktrees/scene-pair-r21/v2/evidence/d5_metrics_r21_scene_on.json`（sim 预备，非交付）↔ `v2/evidence/d5_metrics_r21_scene_on.json`（本报告交付）
- 两棵树使用的指标工具 sha256 **完全相同**：`1d914735f3a13cf4e1640bd694f1d0e070096c9f50abfdefa7359417df551271`
- 结论：`total_diffs = 8`，`by_kind = {"PATH_PREFIX_ONLY": 8}`，**`VALUE` / `LEN` / `MISSING_IN_*` / `TYPE` 均为 0** ⇒ **全部指标数值逐项一致**，差异只是「工具所在树的绝对路径前缀」被写进了 `inputs.*.path` 与 `F-8_scene_anchor.*.path` 这类**元信息字段**。

| # | 差异路径 | 类型 | sim（worktree 树） | 交付（主树） |
|---|---|---|---|---|
| 1 | `/inputs/script` | PATH_PREFIX_ONLY | `…/social-experiment/.worktrees/scene-pair-r21/tools/d5/dialogue_metrics.py` | `…/social-experiment/tools/d5/dialogue_metrics.py` |
| 2 | `/inputs/f8_lexicon/path` | PATH_PREFIX_ONLY | `…/.worktrees/scene-pair-r21/tools/d5/f8_lexicon.json` | `…/tools/d5/f8_lexicon.json` |
| 3 | `/inputs/f8_places/path` | PATH_PREFIX_ONLY | `…/.worktrees/scene-pair-r21/tools/d5/../../code/config/places.json` | `…/tools/d5/../../code/config/places.json` |
| 4 | `/inputs/personas/path` | PATH_PREFIX_ONLY | `…/.worktrees/scene-pair-r21/tools/d5/../../code/config/personas.json` | `…/tools/d5/../../code/config/personas.json` |
| 5 | `/inputs/templates/path` | PATH_PREFIX_ONLY | `…/.worktrees/scene-pair-r21/tools/d5/template_patterns.txt` | `…/tools/d5/template_patterns.txt` |
| 6 | `/inputs/lexicon/path` | PATH_PREFIX_ONLY | `…/.worktrees/scene-pair-r21/tools/d5/backref_lexicon.txt` | `…/tools/d5/backref_lexicon.txt` |
| 7 | `/F-8_scene_anchor/lexicon/path` | PATH_PREFIX_ONLY | `…/.worktrees/scene-pair-r21/tools/d5/f8_lexicon.json` | `…/tools/d5/f8_lexicon.json` |
| 8 | `/F-8_scene_anchor/places/path` | PATH_PREFIX_ONLY | `…/.worktrees/scene-pair-r21/tools/d5/../../code/config/places.json` | `…/tools/d5/../../code/config/places.json` |

复算命令（第三方可照抄，输出应与 `r21_on_metrics_crossrun_diff.json` 同构）：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 - <<'PY'
import json
a=json.load(open('.worktrees/scene-pair-r21/v2/evidence/d5_metrics_r21_scene_on.json'))
b=json.load(open('v2/evidence/d5_metrics_r21_scene_on.json'))
d=[]
def walk(x,y,p=''):
    if type(x)!=type(y): d.append((p,'TYPE')); return
    if isinstance(x,dict):
        for k in set(x)|set(y):
            if k in x and k in y: walk(x[k],y[k],p+'/'+k)
            else: d.append((p+'/'+k,'MISSING'))
    elif isinstance(x,list):
        if len(x)!=len(y): d.append((p,'LEN'))
        for i,(u,v) in enumerate(zip(x,y)): walk(u,v,f'{p}[{i}]')
    elif x!=y:
        d.append((p,'PATH_PREFIX_ONLY' if str(x).replace('/.worktrees/scene-pair-r21','')==str(y).replace('/.worktrees/scene-pair-r21','') else 'VALUE'))
walk(a,b)
from collections import Counter
print(len(d), Counter(k for _,k in d))
PY
```

> 意义：这是**一次独立复现**（不同人、不同树、同工具、同一份 ON 日志）⇒ 数值层可复现；也说明本报告的读数不是单点结论。
