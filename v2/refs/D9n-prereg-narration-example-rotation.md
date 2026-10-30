# D9m 预登记：旁白示例句确定性轮换（6 条判据 + 反事实自检 + 复算实现）

> 立件：exp-designer（实验设计与预登记官）｜**冻结时刻：2026-10-30 08:12 +08:00（起跑前，落盘即冻结；此后判据行不得回改。**精确到秒的 mtime 与本件 sha256 以 `team-workspace/recon/D9m-freeze-receipt.txt` 为准——文件无法自指自身 sha256**）**
> 本件自身身份：**不写自身 sha256（自指不可能）**，落盘后立即 `sha256sum` 并把「sha256 + mtime + 落盘时刻」写入
> `team-workspace/recon/D9m-freeze-receipt.txt`（留痕回执），报告侧引用该回执。分支创建后由实现件一并 `git add` 本件并 commit，把 commit sha 回填到本文件头「§11 冻结回执」区（此为追加区，**不改动判据正文**）。
> 上游：`v2/refs/D9j-prereg-narration-quality-gate.md`（**未跟踪文件**，sha256 `dc909541e52c7eaf96f637836d8ee006cc0d0589d90b1e14cb165df1191bed68`，mtime 2026-10-30 05:39:41）、`v2/evidence/d9k_action_diversity_diagnosis.md`、`team-workspace/recon/d9m-lineage.md`、`reports/CYCLE-30-20261030.md`
> **本件不是效果判定档**，是「跑前冻结的判定契约」：规定用什么尺子、什么阈值、什么算成立/失败/不可判。

---

## 0. 一页速览（先读这个）

| 项 | 值 |
|---|---|
| 维度 | 旁白（括号动作/神态）动作多样性：纵向角色固化 + 横向模板同构 |
| 改动 | `code/life/agent.py` `_NARRATION_TAIL_ON` 的 **`如（…）` 一个示例句** → 由 `sha256(seed\|agent_id\|round\|kind) % n` 从 ≥6 句冻结词表选一句 |
| 开关 | `LIFE_PROMPT_NARRATION_ROTATION`（默认关 = 返回 `_NARRATION_TAIL_ON` 常量对象 = 与 D9i ON 逐字节相同） |
| base sha | `d2a6fa9`（= `feat/prompt-narration-toggle` 尖端），分支 `feat/life-narration-rotation` |
| 对照臂 | **不重跑**，复用 `v2/evidence/narr-on-20261030/`（理由与四项钉死见 §3） |
| 判据条数 | **6 条**：(a) (b1) (b2′) (c) (d) (e)——D9j 表内实为 6 行（文件头自称「八条」= 已知瑕疵，见 §10） |
| 主判据 | **(b2′)**、(d) 两条；**(c) 的密度分量**作「非恒真守卫」而非改善判据 |
| 不可判项 | **(c) 的咬合率分量**本轮判**不可判**（无冻结实现，见 §4.4） |
| 功效充足性 | (d) 充足；(b2′) 边缘（分母小，见 §7）；**(b1) 功效不足 + 口径不稳健 ⇒ 降为辅助（见 §4.2 / §10.3）** |
| 结论措辞上限 | 只准写「结构指标改善」，**禁止**「更自然 / 更像真人」 |

---

## 1. 立项理由（只准用这两条，硬约束）

依据 `team-leader` 2026-10-30 08:04 裁决：**「示例导致同质化」这一理由不得使用**（commit `6e79c00` 已自纠、`cb26a38` 撤回、F-7 判不成立、原句严格命中 0/205）。因此本立项只基于两条**可复算事实**：

**R-1 示例词面覆盖面积大（`47a7da9` ON 臂，B 口径，分母 = 205 个成对括号片段）**

| 词面 | 片段数 / 205 | 占比 |
|---|---|---|
| 含「蹭」 | **31** | **15.12%** |
| 含「围裙」（initiate 示例词） | 13 | 6.34% |
| 含「锉」（reply 示例同型） | 10 | 4.88% |
| 含「刨」（reply 示例词） | 7 | 3.41% |
| 含「木屑/木花」（reply 示例词） | 5 | 2.44% |

**R-2 旁白族分布集中：b1 / b2′ 双红**（族 = 动词 × 部位/器物，见 §4.1 口径）

| 判据 | 基线读数 | 阈值 | 状态 |
|---|---|---|---|
| (b1) 纵向 | `蹭+手` 族 9 次，P004 独占 **5/9 = 55.6%**（D9j 记 8 次 ⇒ 62.5%） | ≤60% 且 ≤2 次 | **口径依赖的红/绿双值**（见 §10.3） |
| (b2′) 横向 | `蹭+锉刀` 族 **9 次**（D9j 记 8），载于 **4 个角色**，其中 ≥2 次者 **3 个**（P014 3 / P013 3 / P011 2 / P002 1） | 族总量 ≤3 且 ≥2 次角色数 ≤1 | **红** |

> ⇒ 立项句（唯一许可表述）：**「两句固定示例的词面在 205 个旁白片段中覆盖 15.12%（蹭）与 6.34%（围裙），且旁白族分布在纵向(b1)/横向(b2′)两个方向同时集中」** ⇒ 假设：把示例句改为确定性轮换的 ≥6 句（并禁用 `蹭/磨/抹/擦` 与 `围裙/锉刀/木屑`），可降低 (b2′) 与 (d) 两项集中度指标。**本假设不主张因果归因到「示例导致同质化」。**

---

## 2. 基线裁决与谱系身份断言

### 2.1 身份断言（可直接引用，来自 `team-workspace/recon/d9m-lineage.md` §0，已由我独立复核）

> base=d2a6fa9；其 code/ 与 D9i 基线 47a7da9 零差异（`git diff --stat 47a7da9 d2a6fa9 -- code/` 为空）；master=6fda371 与 dd7e3fb 均不含 47a7da9，三者共同祖先 b43033e ⇒ 本轮结论不外推至 master / dd7e3fb。

我自己的复核命令与实测值（本轮实跑，非抄录）：

```bash
cd <repo>
git merge-base --is-ancestor 47a7da9 d2a6fa9 && echo ANCESTOR_OK     # → ANCESTOR_OK
git diff --stat 47a7da9 d2a6fa9 -- code/ | wc -l                    # → 0  （判「零 diff」必须看行数，不能只看 rc）
git diff --shortstat 47a7da9 d2a6fa9 -- code/                       # → 空输出
git log --oneline 47a7da9..d2a6fa9                                  # → 2 条：43bbc8a, d2a6fa9
git merge-base master feat/prompt-narration-toggle                  # → b43033e
git rev-list --left-right --count feat/prompt-narration-toggle...master  # → 12  38
git show master:code/life/agent.py | grep -c 'NARRATION\|narration' # → 0 （master 不含旁白实现）
```

### 2.2 基线裁决（按 Leader 方向，不另行选择）

- 作业分支：**`git switch -c feat/life-narration-rotation d2a6fa9`**。**不从 master 拉、不 merge master。**
- 硬理由（事实）：`master=6fda371` 的 `code/life/agent.py` 对 `NARRATION` **零命中**。若以 master 为 base，「旋转关」那臂连旁白通道都没有 ⇒ 变成「旁白有无 × 旋转」双变量，违反 `runbook §3.95`。
- `dd7e3fb` 线（兄弟分支，删示例句）与本线互不包含；其臂**无示例句 ⇒ 旋转臂无定义域**，本轮不碰、不外推。
- **master 不动**：本轮不向 master 提交任何东西。

### 2.3 联网核实状态（按实测登记，两次 fetch 结果不同，务必按时间读）

| 时刻 | 动作 | 结果 |
|---|---|---|
| 08:0x（本件起草时） | `git fetch origin`（全量） | **失败**：`fatal: unable to access 'https://github.com/Elinpf/AI-social.git/': GnuTLS recv error (-110): The TLS connection was non-properly terminated.` |
| 08:1x（本件冻结前） | `git fetch origin master`（重试） | **rc=0 成功**；远端 master 前移 |

⇒ 因此本轮对远端的陈述**以 08:1x 的成功 fetch 为准**；`origin/master` **不是陈旧快照**，已随 fetch 更新。但仍须保留一句事实：**本地 `master` 分支本身未变，仍是 `6fda371`**（本地分支不会因 fetch 自动前移，勿误读为「本地 master 已跟进」）。

**远端 master 现状（08:1x 实测）**：`git rev-parse FETCH_HEAD` = `2761559353a945ab8ed41fbf40f9673752f7c65e`（`origin/master` 同值）。
> 注：`team-workspace/recon/remote-master-check.md` 与 Leader 消息记的是 `7cd10f9`，那是**更早一次 fetch** 的读数；两次 fetch 之间远端又前移了 1 条。差值已核对：`7cd10f9 → 2761559` 亦为纯文档提交。**远端在动，引用时须带 fetch 时刻。**

**master 无旁白实现**——对**本地 `6fda371`** 与**远端 `2761559`（先前的 `7cd10f9` 亦然）**同时成立，证据按强度排序：

1. `git show FETCH_HEAD:code/life/agent.py | grep -c 'NARRATION\|narration'` → **0**（`git grep -c` 直接返 **rc=1 无输出**）；`wc -l` = **1765**（与本地 `6fda371` 同）；
2. **最有说服力**：远端那几条提交**全是文档** —— `git diff --name-only 6fda371 FETCH_HEAD` 仅 5 个 `v2/evidence/*.md`（d9k 三件套 + 闸门矩阵 + 旁白率定义件）；`git diff --stat 6fda371 FETCH_HEAD -- code/ | wc -l` → **0**（`agent.py` 零差异）；
3. 全 `code/` 子树 `git grep -ci narration FETCH_HEAD -- code/` → **rc=1 无输出**；
4. `d2a6fa9`、`47a7da9` **均不是** FETCH_HEAD 的祖先（`git merge-base --is-ancestor` → 非 0）⇒ master 与 base 是两条互不包含的线。

复算命令：

```bash
cd <repo>
git fetch origin master; echo rc=$?          # 须为 0；失败则落 rc 文件，不得声称已联网核实
git rev-parse FETCH_HEAD; git rev-parse master
git merge-base --is-ancestor d2a6fa9 FETCH_HEAD; echo "d2a6fa9_in_master_rc=$?"   # 期望非 0
git diff --name-only 6fda371 FETCH_HEAD
git diff --stat 6fda371 FETCH_HEAD -- code/ | wc -l                               # 期望 0
git show FETCH_HEAD:code/life/agent.py | grep -c 'NARRATION\|narration'           # 期望 0
```

### 2.4 与历史报告的可比性

| 对象 | 可比？ | 理由 |
|---|---|---|
| 与 D9i / CYCLE-30 的 **ON 臂** | **代码身份可比** | `d2a6fa9` 与 `47a7da9` 的 `code/` 零 diff（lines=0）⇒ 同一棵树 |
| 与 `dd7e3fb` 线 | **不可比** | 兄弟分支，`agent.py` 21+/81−，删掉示例句 ⇒ 无示例可言 |
| 与 `master=6fda371` 上任何读数 | **不可比** | master 无旁白实现（零命中） |
| 与 judge 五维（R3/R22） | **不可比且禁用** | R3 已证 judge 五维差 ≤0.21，不可区分（见 §9） |

> **措辞纪律**：只能说「代码身份 47a7da9 ≡ 基线树 d2a6fa9（`code/` 零 diff，lines=0）」。**不得**顺带声称「D9i 那两臂是干净单变量对照」——D9i 两臂 prompt 在语义上是两处改动（删禁令 + 加固定示例句），该歧义已在 `reports/CYCLE-30:237-239` 登记。

---

## 3. 对照臂取用方式（OFF 臂不重跑）与四项钉死

### 3.1 取舍与理由

**决定：OFF（= 旁白 ON + 旋转关）臂不重跑**，复用历史产物。

理由：① `code/` 零 diff ⇒ 代码身份等价；② 旋转开关在 `47a7da9`/`d2a6fa9` 树中**根本不存在**（`git show d2a6fa9:code/life/agent.py | grep -c NARRATION_ROTATION` → **0**），故该臂必然是「旋转关」，**不是靠 env 推断而是代码层不存在**；③ 省一臂 ≈19 分钟 / ≈1.5e5 tokens。
**代价（必须写进报告）**：该臂是历史产物、非本轮同批执行 ⇒ **「两臂同批同环境」这句话不成立**。两臂关系只能表述为「**同代码身份 + 同 cache 内容副本**（`code/freeze_cache` 内容副本作种子，不写共享 cache）」，属**辅助支撑**，**不得**作为任何主判据成立的必要条件；若某判据的成立必须依赖「两臂同批」，该判据本轮降级为**不可判**。
**cache 口径（Leader 裁决 A′）**：基线 `cached_ratio = 1387/2252 = 0.6159`（`llm_cost.json` 实测；`importance` 1419 次中 1387 cached），而 **`dialogue` purpose `cached=0`**（191 次全 miss）、`judge` / `plan` / `reflect` / `negotiation` 亦 `cached=0` ⇒ 复用 cache 内容副本**不会**把对话类调用变成缓存命中，两臂的对话生成仍是真实 LLM 调用。报告须同时给 `llm_cost.json` 的 `degraded=0` 与 `provider_guard.ok=true`。

### 3.2 基线产物四项钉死（缺一项 verifier 应打回）

| # | 项 | 值 |
|---|---|---|
| 1 | 绝对路径 | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/narr-on-20261030/` |
| 2 | `run.jsonl` sha256 | `fdb31c7e2ca64b4dac1466fd4c81770dc0198ced4904584a3faf59939fd663ee`（`sha256sum run.jsonl` 实测，与 `meta.derived_from_log_sha256` 一致） |
| 3 | `meta.code_sha` | `47a7da9e71e4ab31e8b58a9a5cc14105ecd0aed8`（`code_sha_end` 同值） |
| 4 | 开关状态 | `switch_proof.txt`（`/proc/<pid>/environ` 层）：`HITT_LLM_PROVIDER=openai_compat`、`LIFE_PROMPT_NARRATION=1`、**无 `LIFE_PROMPT_NARRATION_ROTATION` 键**；旋转关的**更强证据**：该 env 名在 `d2a6fa9` 树中零命中（代码层不存在） |
| 5 | 第三方核查回执 | `team-workspace/run1-baseline-reuse-check.md`（batch-runner 出）：一次给全路径 / `meta` / 开关状态 / sha256，并核 `degraded=0`、`fallback=false` |

其他核过的事实：`seed=42`、`rounds=24`、`agents=16`、`provider=openai_compat`、`model=DeepSeek-Flash`（`meta.llm_provider_in_events={"openai_compat":2252}`）、`rounds_contiguous=true`、`llm_cost.degraded=0`。

复算命令：

```bash
B=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/narr-on-20261030
sha256sum "$B/run.jsonl"
python3 -c "import json;m=json.load(open('$B/meta.json'));print(m['code_sha'],m['seed'],m['rounds'],m['provider'],m['derived_from_log_sha256'])"
grep -E 'LIFE_PROMPT_NARRATION|PROVIDER' "$B/switch_proof.txt"
```

---

## 4. 六条判据：口径 + 复算实现 + 阈值 + 三态条件

### 4.0 通用口径（所有判据共用，写死不许漂移）

**语料分母**：只取 `MSG_DM` / `MSG_PUBLIC` / `MSG_GROUP` 三类消息事件的 `payload.body`（`tools/d5/dialogue_metrics.py:MSG_TYPES`、`extract_messages()`），做**片段级**计数。
**必须排除**：`MEMORY_CONSOLIDATE` 等非消息事件。实测 `narr-on-20261030/run.jsonl`：

| 层级 | 含「蹭」的条数 | 说明 |
|---|---|---|
| 片段级（括号内文本） | **31** | **本轮唯一合法计数** |
| MSG 记录级（body 任意位置） | **33**（`MSG_DM 30` + `MSG_PUBLIC 3`） | 其中 **2 条**的「蹭」只在**台词里**、不在括号旁白内 ⇒ 与片段级差 2 |
| `MEMORY_CONSOLIDATE` | **30**（该类型共 499 条） | **纯污染源**（旁白被写进记忆摘要） |
| 全事件流记录级 | **63** = 33 + 30 | 若用这个数，「蹭」从 31 变成 63，**翻倍** |

⇒ **分母/计数口径错误即结论作废**。记录级 33 ≠ 片段级 31 的差 2 条必须能解释（台词内出现），报告侧若出现 33 必须标注「记录级」。

**片段定义**：`PAIRED_RE = （[^（）]{1,120}）|\([^()]{1,120}\)`（左右括号成对、中间 ≥1 字符；空括号不计）。一个匹配 = 一个片段；片段内文本 = 去掉首尾括号后的 `inner`。

**测量仪器（必须钉死 sha256，runbook §3.97 防「两套实现翻转结论」）**：

| 用途 | 文件 | 现值 sha256 |
|---|---|---|
| 片段/密度/撞车（已冻结、已验证可复算） | `tools/d9i/narration_stats.py` | `8ddb9111072c9ef71e7853dc7b455d618352b2baf44492d0576e440467627e85` |
| 语料抽取（上游，已在 `master` 版本化） | `tools/d5/dialogue_metrics.py` | 以 `d2a6fa9` 树内版本为准（`impl_sha256` 于起跑前随实现件记录） |
| 族/动词分类（**本轮必须新冻结**，见 §4.5） | `tools/d9m/narration_family.py`（待实现件产出） | **起跑前必须给出 `impl_sha256`；未给出 ⇒ (b1)(b2′)(d) 本轮判不可判** |

**仪器纪律**：`narration_stats.py` 的 sha256 须在**跑批前后各取一次、两臂共用同一份**（任一次不符即判「仪器中途更换」⇒ 本轮结论作废）。

**复算命令（六条判据共用的唯一入口，实现件落盘后可直接复制执行）**：

```bash
R=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
cd "$R"
# 6 条判据一次算完（实现件由 impl-1 交付；--arm ON|OFF 只影响输出标签）
python3 tools/d9m/narration_family.py \
   --log <arm_out_dir>/run.jsonl \
   --lexicon tools/d9m/narration_family_lexicon.json \
   --out <arm_out_dir>/d9m_judgement.json
# 片段级交叉校验（第三方独立口径，必须与上面 blocks_total 相等）
python3 tools/d9i/narration_stats.py --log <arm_out_dir>/run.jsonl --out <arm_out_dir>/narration_stats.json
```

**变异带（noise band）来源**：比例量用 **Wilson 95% 区间**（不假设正态、小样本稳健）；计数量用 **Poisson 近似** `k ± 1.96·√k`。基线噪声带**全部由本轮在历史日志上重算得到**（不引用任何「历史带」文件），避免「带来自另一口径」。

---

### 4.1 族定义冻结（(b1)(b2′)(d) 的公共前提）

1. **单位**：一个片段**恰好归一族**（禁一片多计）。
2. **归族算法（确定性，按序执行）**：
   - 步骤 1：在 `inner` 中按 `VERBS` 表**顺序**取**首个命中**的动词 `v`（不做同义归并）；无命中 ⇒ 该片段**未归族**（记 `unassigned`）。
   - 步骤 2：在 `inner` 中按 `PARTS`（身体部位）**由具体到泛**取首个命中 → `p`；若无，则按 `OBJS`（器物/环境）取首个命中 → `o`。
   - 步骤 3：族名 = `(v, p or o or None)`。**部位优先于器物**（`手背/指腹 > 手指 > 手`；`手背/指腹` 命中时不再看 `手`）。
3. **表冻结**：`VERBS` 8 个 = `蹭/搓/抹/擦/拂/拍/抿/揉`（D9j §3 原表，不改）；`PARTS`、`OBJS` 按 D9j §3 原规模（部位 6 / 器物 13），**并扩展**：`V_judge = VERBS ∪（旋转词表中出现的全部动词，由实现件导出并冻结）`，`OBJS_judge = OBJS ∪（旋转词表中出现的器物，若有）`。扩展是**为了让旋转臂的新动词也在尺子覆盖内**，否则判据会被「换表外新词」轻易绕过 ⇒ 恒真（见 §5 自检 S-3）。
4. **两行并报**：`A 口径`（字面包含，可多计，仅诊断）+ `B 口径`（归族，用于判定）。**结论只准用 B 口径。**
5. **归族覆盖率守卫（防恒真）**：`coverage = assigned / blocks_total`。实测基线（D9j 闭表口径）**仅 40/205 = 19.5%**。⇒ 若 ON 臂 `coverage` 低于基线的 60%（即 < 11.7pp 绝对覆盖），则 (b1)(b2′) **判「不可判」**并写明「尺子覆盖不足，无法区分『改善』与『词表外迁移』」。**这是可判性前置，不是阈值放宽。**

---

### 4.2 (a) 精确串重复 —— **辅助（诊断）**

- **口径**：`max_exact_dup = max over inner of count(inner)`，分母 `blocks_total`。
- **阈值**：`≤ 2`（D9j 原值，不放宽）。
- **基线**：**3**（`把沾着面粉的手在围裙上蹭了蹭` 3 次；另有 `把算盘珠子拨回原位` 3 次、`顿了顿` 3 次）。
- **三态**：成立 = `max_exact_dup ≤ 2`；失败 = `≥ 3`；不可判 = `blocks_total < 50`（样本不足）。
- **状态**：**辅助判据，不得单独引用下结论**（D9j 原文：可换皮绕过）。作为「闸是否被换皮击穿」的诊断量。

### 4.3 (b1) 同一「角色 × 族」占比 —— **辅助（本轮降级，理由见 §10.3）**

- **口径**：对每个族 `f`（**仅取 `族总量 ≥ 3` 的族进入判定**，`<3` 的族占比无意义）：`share(p,f) = count(p,f) / count(f)`；判 `max_{p,f} share ≤ 60%` **且** `该 (p,f) 的 count ≤ 2`。
- **阈值**：`≤60%` 且 `≤2 次`（D9j 原值，不放宽）。
- **基线（两值并报，口径依赖）**：`蹭+手` 族 **D9j 记 8 次 ⇒ P004 5/8 = 62.5%（红）**；**本轮冻结口径重算 = 9 次 ⇒ P004 5/9 = 55.6%（绿）**（P004 5 / P001 2 / P003 1 / P015 1）。
- **三态**：成立 = 全部 `族总量≥3` 的族都 `≤60%` 且 `该角色该族 ≤2`；失败 = 任一不满足；不可判 = `coverage` 守卫失败 **或** 全部族总量 <3（无判定对象）**或** 基线本身口径依赖未能消解。
- **⚠️ 功效与稳健性（必须与读数并报）**：`n=9` 下 Wilson 95% CI 半宽约 **±26pp**（`5/9` 区间 ≈ [0.27, 0.81]）；且分母 8→9 的**口径差异就足以跨过 60% 阈值**。⇒ 本条**无统计功效、且不稳健**，本轮**只作辅助读数**，其「红/绿」不得单独构成结论。

### 4.4 (c) 咬合率 且 旁白片段密度 —— **主判据之一（仅密度分量可判；咬合分量判不可判）**

#### (c-1) 旁白片段密度 —— 可复算，已实测

- **口径**：`density = blocks_total / msgs_total`；分母 = `MSG_DM+MSG_PUBLIC+MSG_GROUP` 消息条数。
- **阈值**：`≥ 1.0`（D9j 原值）。
- **基线**：`205 / 191 = 1.0733`（`narration_stats.py` 复算：`denominator_msg_total=191`、`blocks_total=205`，与我独立重算一致）。
- **三态**：成立 `≥1.0`；失败 `<1.0`；不可判 `msgs_total < 50`。
- **作用**：**非恒真守卫**——防止「少写旁白」把 (b2′)/(d) 刷绿（D9j 20 格表 Q2「少写」格）。**它不判改善，只判「没有靠少写取胜」。**

#### (c-2) 咬合率 ≥ 82.35% —— **本轮判「不可判」**

- 82.35% 的真实来源是**人工/语言学判读**：`v2/evidence/d9i_language_read_prompt_linguist.md:46`「旁白与台词咬合 **42 / 51**」，分母是 **51 条抽样**，判定公式与实现件**不存在**（D9j §6 自认「实现闸未做」）。
- ⇒ **本轮不给读数、不引用 82.35% 当 (c) 的读数**；(c) 只能表述为「**密度达标，咬合不可复算 ⇒ (c) 部分不可判**」。
- 缺什么才能判：① 咬合判定的**文字化判据**（何为「同物/同动作」）+ ② 冻结实现（脚本 + `impl_sha256`）+ ③ 抽样框与抽样量（当前 51/191，抽样规则未披露）。

### 4.5 (b2′) 族内「出现 ≥2 次的角色数」 —— **主判据（横向 / 模板同构）**

- **口径**：对每个族 `f`：`n_ge2(f) = #{角色 p : count(p,f) ≥ 2}`；`total(f) = count(f)`（全部角色合计）。
  - **成立条件**：对所有 `f`：`total(f) ≤ 3` **且** `n_ge2(f) ≤ 1`。
  - 判定集合 = 全部出现在语料中的族（不设最小总量门，因为「族总量 ≤3」本身就是判据的一半）。
- **阈值**：`族总次数 ≤ 3` 且 `≥2 次角色数 ≤ 1`（D9j 原值，不放宽）。
- **基线（并报，不取单值）**：`蹭+锉刀` 族 **D9j 记 8 次 / 独立重算 9 次（差 1 来源未披露）**；载于 **4 个角色**（P014 3 / P013 3 / P011 2 / P002 1），其中 **≥2 次者 3 个**。⇒ `total=9 > 3` 且 `n_ge2=3 > 1` ⇒ **双红**。
  - 另：`蹭+手` 族 `total=9`、`n_ge2 = #{P004 5, P001 2} = 2` ⇒ 亦红。
- **三态**：成立 = 全部族同时满足两条；失败 = 任一族的任一条不满足；不可判 = `coverage` 守卫失败 **或** 语料 `blocks_total < 50`。
- **主/辅分量**：`total(f)` 为主分量（计数位移大、噪声小）；`n_ge2(f)` 为辅分量（n=9 时分母小，见 §7）。

### 4.6 (d) 动词级总量（抹掉器物维度） —— **主判据（封洞①：换器物/换皮绕过分族）**

- **口径**：对 `v ∈ V_judge`：`cnt(v) = #片段 whose inner 含 v`（**每片段对同一 v 只计一次**；跨 v 可多计，仅用于诊断，判定用逐 v 上限）。判定量 `max_v cnt(v)`。
- **阈值**：`max_v cnt(v) ≤ 5`（D9j 原值，不放宽）。
- **基线**：`蹭 31`、`搓 5`、`抹 3`、`揉 1`、`擦/拂/拍/抿 0` ⇒ `max_v = 31 ≫ 5` ⇒ **红**。
  - **D9j §6 记「(d) 未算，不编数」；本件基线值来源 = `d9k_action_diversity_diagnosis.md §4`（表中「蹭 31 / 搓 5 / 抹 3 / 揉 1」），并已由我独立重算复核一致（蹭=31、搓=5、抹=3、揉=1）。D9k 测自 `47a7da9`，与 base 代码身份等价。**
- **三态**：成立 = `max_v ≤ 5` **且** `unassigned_verb_rate ≤ 30%`（见下）；失败 = `max_v > 5`；不可判 = `unassigned_verb_rate > 30%`（说明动作动词大量落在 `V_judge` 外 ⇒ 尺子失效，读数不可信）。
  - `unassigned_verb_rate = #片段中 V_judge 全部不命中的条数 / blocks_total`。基线实测（D9j 闭表 8 动词）：未归族 165/205 ⇒ **80.5%**！⇒ **闭表口径下 (d) 天然可判但覆盖极低**；这是 §5 自检 S-3 的核心风险，必须靠 `V_judge` 扩展 + 该守卫处理。
- **为什么必须扩展 `V_judge`**：旋转词表刻意排除 `蹭/磨/抹/擦`，若 `V_judge` 只保留 8 个闭表动词，旋转臂的 `max_v` 会因「新动词不计」而**近 0 ⇒ 恒真通过**。扩展后新动词同样受限 ≤5，判据才非恒真。

### 4.7 (e) 单条 MSG 旁白片段数 —— **辅助（封洞②：防「塞旁白刷密度」）**

- **口径**：`dist[k] = #MSG whose body 含 k 个片段`；判定量 `max_k`。
- **阈值**：`max_k ≤ 2`（D9j 原值）。
- **基线**：`0:12 / 1:153 / 2:26`（191 条 MSG），`max_k = 2` ⇒ **达标**（D9j §6 记「未算，不编数」；本件值来源 = `d9k §4`，我已独立重算复核一致）。
- **三态**：成立 `max_k ≤ 2`；失败 `max_k ≥ 3`；不可判 `msgs_total < 50`。
- **作用**：辅助护栏，(c-1) 密度达标必须与 (e) 联合读，否则「1 条 MSG 塞 3 个片段」可刷密度。

### 4.8 旋转词表（词表要求 + 现值候选，冻结时以实现件 sha256 为准）

**硬要求**：≥6 句；只写人话、不出内部 token（不得出现 `persona_id` / 场所 id）；**禁用词面** `蹭 / 磨 / 抹 / 擦`（动词族，防与 (d) 的高频动词叠加）与 `围裙 / 锉刀 / 木屑`（D9i 旧示例道具）；每句须含**至少一个** `V_judge` 内的动词（否则 `unassigned_verb_rate` 攀升，见 §4.6 三态）。
**选句**：`idx = int(sha256_hex("narration-rotate|<seed>|<agent_id>|<round>|<kind>")[:8], 16) % n`，`seed` 取 `HITT_WORLD_SEED`（未设 = `"0"`）；不读墙钟、不用 `random`。
**现值候选（`life-engineer` 已在工作树实现的 9 句，冻结时须连同词表文件 `sha256` 一起固定；本件不对其逐句背书）**：`抬手把鬓角的碎发别到耳后` / `把袖口往上挽了一截` / `低头拢了拢衣襟` / `侧身让过挑担的街坊` / `往门槛上靠了靠` / `把竹篮往脚边挪了挪` / `抬眼望了望日头` / `伸手扇了扇风` / `把凳子往后撤了半步`。
**词表身份**：`NARRATION_EXAMPLE_LEXICON_VERSION = "narration-rotation-v1"`；改词表 = 改行为 ⇒ 须重冻结、重开臂，**不得**在跑后替换。

---

## 5. 反事实自检表（必填；逐条「成立/失败/不可判 + 恒真恒假检查」）


> 目的：本仓库有 `R15`（判据结构互斥 ⇒ 数学上不可能判改善）与 `R21`（否决条恒真 ⇒ 成立不可达）两起前科。下表逐条作答。

| 判据 | 什么数据判**成立** | 什么数据判**失败** | 什么数据判**不可判** | 恒真/恒假自检 |
|---|---|---|---|---|
| (a) | `max_exact_dup ≤ 2` | `max_exact_dup ≥ 3` | `blocks_total < 50` | 非恒真（基线 3，改动可降可升）；非恒假（阈值 2 在 191 MSG/205 片段规模下常见，实测有 3 个串各 3 次 ⇒ 可达） |
| (b1) | 所有 `族总量≥3` 的族：`share ≤60%` 且 `该(p,f) count ≤2` | 任一 `族总量≥3` 的族越界 | ①`coverage` 守卫失败（ON 覆盖 < 基线的 60%）②无 `族总量≥3` 的族 ③基线口径依赖未消解 | **恒真风险高**：若旋转把动作迁到表外词，族总量全部 <3 ⇒ 无判定对象 ⇒ 「成立」靠空集。**已由三态第②条堵住**。恒假风险：基线 P004 5/9=55.6% 已绿，若 ON 略升即红，非恒假 |
| (b2′) | 所有族 `total ≤3` **且** `n_ge2 ≤1` | 任一族 `total ≥4` 或 `n_ge2 ≥2` | `coverage` 守卫失败 或 `blocks_total<50` | 恒真风险：切换词表后族被拆碎，每族 ≤3 天然满足 ⇒ **由 (d) 的 `max_v ≤5` 上卷封住**（族碎但单动词仍 ≤5 才准过）；恒假风险：基线 `total=9`、`n_ge2=3`，需真实位移才能过 ⇒ 非恒假 |
| (c-1) 密度 | `density ≥1.0` | `density <1.0` | `msgs_total<50` | 非恒真（基线 1.0733，模型改少写即掉下 1.0）；非恒假（可写多条） |
| (c-2) 咬合 | **本轮不可达**（无实现） | 同左 | **恒为不可判** | **明确登记：本轮 100% 不可判**（缺判据文字化 + 实现 + 抽样规则）⇒ 报告不得出现咬合率读数 |
| (d) | `max_v ≤5` **且** `unassigned_verb_rate ≤30%` | `max_v ≥6` | `unassigned_verb_rate >30%` | **恒真风险极高**（若 `V_judge` 不扩展，旋转臂新动词不计 ⇒ `max_v≈0`）⇒ **强制 `V_judge = 闭表8 ∪ 旋转词表动词`，且 `unassigned_verb_rate ≤30%` 是成立的必要条件**；恒假风险：`V_judge` 扩展后若新词集中使用，`max_v` 可 >5 ⇒ 非恒假 |
| (e) | `max_k ≤2` | `max_k ≥3` | `msgs_total<50` | 非恒真（可塞 3 片段）；非恒假（基线已达标，仍可能保持） |

### 5.1 否决条款审计（R21 式前科专项）

- **本件设有 2 条否决/前置：`coverage` 守卫与 `unassigned_verb_rate ≤30%`。逐条做「非恒真」证明**：
  - `coverage < 基线 60%`：基线 `coverage = 40/205 = 19.5%`（闭表），守卫门限 = `11.7pp`。**ON 臂要达到 11.7pp 覆盖**：只要旋转词表动词被 `V_judge` 覆盖（本件强制），任何 ≥24 个片段归族即过 ⇒ **不是恒真**（否则 (b1)(b2′) 立即不可判，读数会显示不可判而非成立）。**反证**：若守卫恒真，则 (b1)(b2′) 从不会判不可判，与三态表矛盾。
  - `unassigned_verb_rate ≤30%`：`V_judge` 含旋转词表全部动词 + 闭表 8 ⇒ 旋转生效时未命中率必然下降（该率由词表覆盖决定，不由结果好坏决定）⇒ **它是对「尺子是否有效」的检验，不是对「效果是否好」的检验，因此不会与改善方向共线（非恒真亦非恒假）**。
- **结论**：无恒真否决条；**但 (b1) 与 (d) 的「成立」在旧闭表口径下都近乎恒真，本件已分别用「三态第②条」与「`V_judge` 扩展 + `unassigned_verb_rate` 守卫」显式消除**。此两条是本轮相对 D9j 的**唯一收紧**（收紧而非放宽，不违反「不得放宽阈值」）。

---

## 6. 指标口径节（分子/分母/CI/主辅）

| 量 | 分子 | 分母 | CI 方法 | 主/辅 |
|---|---|---|---|---|
| (a) `max_exact_dup` | 最大同串次数 | —（计数量） | Poisson `k±1.96√k` | 辅助 |
| (b1) `share(p,f)` | `count(p,f)` | `count(f)`（族总量，仅 `≥3` 的族） | Wilson 95% | 辅助（降级，§10.3） |
| (b2′) `total(f)` / `n_ge2(f)` | 计数 | —（计数量） | `total` 用 Poisson；`n_ge2` 只报计数+参与者明细 | **主** |
| (c-1) `density` | `blocks_total` | `msgs_total` | Wilson 95%（按「MSG 含 ≥1 片段」比例报） | 守卫（非改善判据） |
| (c-2) 咬合率 | — | 51（历史抽样） | — | **不可判** |
| (d) `max_v` | `cnt(v)` | —（计数量） | Poisson `k±1.96√k` | **主** |
| (e) `max_k` | 分布 | `msgs_total` | 只报分布 | 辅助 |

**硬纪律**：
1. **主判据只有 (b2′) 与 (d)**；(c-1) 是守卫；(a)(b1)(e) 是辅助/诊断。**辅助判据不得单独引用下结论**（D9j 对 (a) 原话，本件扩展至全部辅助项）。
2. 任何「改善」表述必须同时给出：**两臂读数 + 分子分母 + CI + 阈值**，四项缺一不许写结论句。
3. 比例量一律 Wilson；**不得**用正态近似替代（n=9 时会给出越界区间）。

---

## 7. 样本量与功效（诚实版）

**运行规格**：n16 / seed42 / rounds24（与基线同规格，`rounds_contiguous=true`）。

**样本量**：`msgs_total = 191`、`blocks_total = 205`（基线实测；ON 臂允许小幅漂移，若 `blocks_total` 落在 `[150, 260]` 之外需在报告里说明漂移原因）。

**可检出效应下限（每条判据分别算，不做统一宣称）**：

| 判据 | 基线读数 | Wilson/ Poisson 半宽（95%） | 阈值距基线 | 功效结论 |
|---|---|---|---|---|
| (d) `max_v`（蹭） | 31/205 = 15.12% | **±4.90pp**（比例口径）；Poisson `±5.9` 次 | 31 → ≤5（位移 26 次 ≈ 12.7pp） | **充足**（位移 ≈2.6× 半宽） |
| (b2′) `total(f)` | 9 次 | Poisson `±5.9` 次 | 9 → ≤3（位移 6 次） | **边缘**：位移 6 次 ≈ 1.0× 半宽 ⇒ 只能主张「大幅下降」，不能主张「小幅改善」 |
| (b2′) `n_ge2` | 3 个角色 | 计数 3，无 CI 意义 | 3 → ≤1 | **功效不足**：参与者只有 4 个角色承载 9 次，随机排列下 `n_ge2≥2` 本就常见（16 个角色上放 9 个球的碰撞期望 ≈2.25 对）⇒ **该分量不得单独作为成立依据**，只作辅读 |
| (b1) `share` | 5/9 = 55.6%（或 D9j 5/8） | **±26pp**（n=9） | 距 60% 阈值 **4.4pp** | **功效严重不足**：半宽 26pp ≫ 距阈值 4.4pp ⇒ 红绿读数与噪声不可区分 ⇒ **降级为辅助（§10.3）** |
| (c-1) `density` | 205/191 = 1.0733 | 比例半宽 **±3.5pp**（按 179/191 报） | 阈值 1.0 仅距 7.3pp | 够判「是否掉破 1.0」，不够判「小幅上升」 |
| (e) `max_k` | 2 | 计数 | 阈值 2 | 只能判「是否被塞到 ≥3」 |

**必须明说的功效不足项**：(b1) 全部读数、(b2′) 的 `n_ge2` 分量、(c-1) 的小幅上升。**报告不得用这些量写「改善」。**

**不做功效宣传**：本件**不主张**「n16×r24 足以支持任何语义层结论」；它只支持上表中标「充足/边缘」的结构计数判据。

---

## 8. 确定性 / replay 自检（Leader 硬要求 E，必判）

**S-DET（新增自检，非 D9j 原有）**：同一 seed 两次运行，**示例序列逐字节一致**。

- **判法**：把每次 LLM 对话调用的「(agent_id, round, kind, 选中示例句)」落成一份可 diff 的序列文件（实现件需提供，建议写在 prompt 装配处，形如 `<out_dir>/narration_example_seq.tsv`，每行 `agent_id\tround\tkind\texample`，UTF-8 无 BOM、`\n` 结尾）。
- **命令**：
  ```bash
  python3 tools/d9m/narration_example_seq.py --run-dir <armA_out> --out /tmp/seq_a.tsv
  python3 tools/d9m/narration_example_seq.py --run-dir <armB_out> --out /tmp/seq_b.tsv
  sha256sum /tmp/seq_a.tsv /tmp/seq_b.tsv   # 两值必须逐字节相同
  diff /tmp/seq_a.tsv /tmp/seq_b.tsv        # 必须无输出（行数需一并核对：wc -l 相等且 > 0）
  ```
- **三态**：成立 = 两 sha256 相同且 `wc -l` 相同且 >0；失败 = 任一不同（⇒ **旋转非确定性，本轮全部判据作废**）；不可判 = 序列文件未产出（⇒ 判「确定性未证」，主判据结论只能标「待复现」）。
- **辅助静态证据（不必跑两次也算，但不能替代 S-DET）**：`narration_example()` 只依赖 `sha256(seed|agent_id|round|kind)`，不读墙钟、不用 `random`；且单位断言 `_NARRATION_TAIL_ON_TPL[kind].format(_NARRATION_TAIL_ON_EXAMPLE[kind]) == _NARRATION_TAIL_ON[kind]`（保证「除示例句外一字未改」）。
- **等价性自检（旋转关必须复现 d2a6fa9 ON 臂）**：`life-engineer` 已导出 4 个 GOLDEN sha256（OFF initiate/reply、ON+旋转关 initiate/reply）。**验收要求**：旋转关时四值逐一相等，否则「逐字节等价」不成立 ⇒ 本轮基线复用失效。

---

## 9. 可比性边界（结论措辞上限）

1. **结构指标改善 ≠ 更自然**。本件全部判据都是**结构/计数代理**（族集中度、动词上限、密度）。即使六条全绿，也只能写「旁白动作分布更分散」。
2. **禁止**把 judge 五维作为主判据（`R3` 已证五维差 ≤0.21 不可区分；`R22` 判「机制未生效」）。judge 若使用，只能是「不作为判据的旁证」，且**不得**写进结论句。
3. **不外推**：master（无旁白实现）、`dd7e3fb`（无示例句）、以及任何非 `d2a6fa9` 代码身份的批次。
4. **两臂关系**：历史对照臂（非本轮同批）⇒ 只能写「代码身份等价 + 开关状态已核」，**不得**写「两臂同批同环境」。
5. **不做剂量外推**：词表 9 句、每 (agent,round,kind) 取 1 句的剂量是固定的；不得据此外推「更多句更好」。
6. **测量仪器身份**：结论必须绑定 `narration_stats.py` sha256 `8ddb9111…` 与 `narration_family.py` 的 `impl_sha256`；换实现即换尺子，结论不可跨实现混用（runbook §3.97）。

---

## 10. 已知瑕疵登记（必须进报告，不得隐瞒）

### 10.1 D9j 文件头「八条判据」vs 表内 6 行
D9j 标题写「八条判据 + 20 格自检表」，其 §1 实际列 **6 行**（(a)(b1)(b2′)(c)(d)(e)）；其 §1「判据定稿（八条：四条判定 + 两条绝对量护栏 + 一条上卷 + 一条诊断）」是**计数口径混乱**（4 判定 (b1)(b2′)(c)+? ；2 护栏 (d)(e)；1 上卷；1 诊断 (a) ⇒ 文字上凑 8，表内只有 6 行）。**本件以 6 条为准**。此为 D9j 的已知内部不一致，登记于此。

### 10.2 (d)(e) 的基线值来源
D9j §6 状态框记「(d)(e) 未算，不编数」；现值来自 `v2/evidence/d9k_action_diversity_diagnosis.md` **§4**（测自 `code_sha=47a7da9`）。引用规则：必须写「**值由 D9k §4 提供**」，且注明 D9k 的树虽与 base 代码身份等价（`code/` 零 diff），**但 D9k 自身声明其数字不可作为基准沿用** ⇒ 本件处理方式：**基线值一律由本轮用冻结实现重算**，D9k 值只作**交叉校验**（允许出现差异，差异须列出并解释）。

### 10.3 (b1) 的口径敏感性（本轮降级理由）
`蹭+手` 族分母：D9j 记 **8**（⇒ 5/8 = 62.5%，红）；本轮冻结口径重算 **9**（⇒ 5/9 = 55.6%，绿）。**同一批数据、同一阈值，分母差 1 即翻转结论**（= runbook §3.97 的教科书案例）。叠加 n=9 的 ±26pp CI ⇒ (b1) **既不稳定也无功效**，本轮由「判定」降为「辅助读数」。**该降级是收紧不是放宽**：原判定位置由 (b2′) + (d) 承担。

### 10.4 20 格自检表扩容
D9j 的 20 格表只覆盖 (a)(b1)(b2′)(c) **四条 × 五问**；本件判据为 6 条，故扩为 **6 × 5 = 30 格**（补充 (d)(e) 两行 + 新增两条守卫列）。扩容依据：D9j §2「任何新增判据必须重填这 20 格（判据数 × 5 问）」。

| 判据 | Q1 反向 | Q2 少写 | Q3 打薄 | Q4 稀释 | Q5 换皮 |
|---|---|---|---|---|---|
| (a) 诊断 | 无 | 能 | 能 | 能 | 能 ⇒ 不进判定 |
| (b1) | 无 | 能（受 c-1 密度下限封） | 不能（受 b2′ 封） | 不能（≤2 次封） | 不能（族按语义不按字面） |
| (b2′) | 无 | 能（受 c-1 封） | **能 ⇒ 由 (d) 封** | 不适用 | 能 ⇒ 由 (d) 的 `V_judge` 扩展封 |
| (c-1) 密度 | 无 | 不适用（它正是防少写） | 不适用 | 能（无关旁白拉低咬合）⇒ **咬合分量不可判 ⇒ 登记为残余风险** | 不适用 |
| (d) | 无 | 能（受 c-1 封） | 不能（打薄会抬 `max_v`? 否：打薄降 `max_v` ⇒ **是能**；由 (b1)/(b2′) 的族分布辅读封） | 不能（逐 v 计数不随总量漂移） | **能 ⇒ 由 `V_judge` 扩展 + `unassigned_verb_rate ≤30%` 封** |
| (e) | 无 | 不适用 | 不适用 | 不适用 | 能（长旁白单片段内堆动作）⇒ **登记残余风险**（本件不封，因无「片段内动作数」判据） |

**残余风险（诚实登记，不封）**：① (c-2) 不可判 ⇒ (c) 只剩密度，「装饰型无关旁白」本轮不被约束；② (e) 无法约束「单片段内堆多个动作」。两项**不进入本轮结论**。

### 10.5 D9j 无版本化历史
`v2/refs/D9j-prereg-narration-quality-gate.md` 是**未跟踪文件**（`git ls-files --error-unmatch` rc=1；`git log -- <file>` 空输出）⇒ **「起跑前冻结、跑后未被回改」没有 commit 历史可证**，只能靠 sha256 + mtime 弱证据。本件措辞固定为「**历史判据文件无版本化历史**」，不得写「已被版本化冻结」。本件自身的冻结强化见 §11。

---

## 11. 冻结与验收清单

### 11.1 冻结手续（本件自身）

1. 落盘 → `sha256sum v2/refs/D9m-prereg-narration-rotation.md` → 与 `stat -c '%y'` 一并写入 `team-workspace/recon/D9m-freeze-receipt.txt`（留痕回执，verifier 事后比对字节）。
2. 分支 `feat/life-narration-rotation` 创建后，**由实现件把本件 `git add` 一并 commit**，把 commit sha 回填到 §11.3 的追加区（**只追加，不改判据正文**）。
3. **跑后不得回改本件任何判据行**。若必须修订，另起 `D9m-prereg-amendment1-*.md` 并写明理由与原判据编号。

### 11.2 起跑前必须闭合的前置（缺一即不得起跑）

- [ ] `tools/d9m/narration_family.py` + `narration_family_lexicon.json` 落盘，记录 **`impl_sha256`** 与 `V_judge` 词表全文
- [ ] `tools/d9m/narration_example_seq.py` 落盘 + `impl_sha256`
- [ ] 冻结实现在**历史 ON 日志**上重算基线，输出 `d9m_baseline_judgement.json`，与本件 §4 各基线值**并报差异**
- [ ] 旋转关的 4 个 GOLDEN sha256 逐一相等（逐字节等价）
- [ ] 本件 sha256 已进 `D9m-freeze-receipt.txt`
- [ ] `bash tools/d5/preflight.sh --tag d9m-run`（串行 + 冻结区干净度）通过

### 11.3 冻结回执追加区（留空，由实现件 commit 后回填）

```
[prereg_sha256] = <落盘后填写，并同步到 team-workspace/recon/D9m-freeze-receipt.txt>
[frozen_at]     = 2026-10-30 08:12 +08:00（详见 D9m-freeze-receipt.txt）
[prereg_commit] = <分支创建后由实现件回填>
[impl_sha256]   = <narration_family.py> / <narration_family_lexicon.json> / <narration_example_seq.py>
```

---

## 12. 本轮不做的事（边界）

- **不做实现**（属于 `impl-1` / `life-engineer`）、**不跑批**（属于 `run-1` / `batch-runner`）、**不写报告结论**（属于 `report-1` / `report-writer`）。
- 不批「方案 C（改 `personas.json` 动作池）」：会改 `config_digest` / `engine_version` 指纹 ⇒ 与全部历史报告不可比。
- 不动 `dd7e3fb`、不动 `master`。
