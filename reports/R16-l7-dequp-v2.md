# R16 · L-7「对话套路化」v2 去重臂收口 —— raw8 111/510（21.7647%）落到 OFF 基线带**下侧带外**（BELOW_BAND）

> 本文件仅做脱敏替换（绝对路径→仓库相对路径），内容与结论未改。


> **本文件状态：定稿（复算 + 守卫 + 截图三件套 + R17 读数已齐；R17 不下效果判定）**
>
> | 项 | 状态 |
> |---|---|
> | R16 批次证据质量 | **可复算、可追溯**（16 项读数由自写复算器逐项重算一致；`provider_guard.ok=true`） |
> | R16 的 M1 判定（raw8） | **BELOW_BAND**：Δ = **−16.0784pp** < 噪声带下界 **−4.31pp** ⇒ **落带外·下侧**（⚠️ 不是「带内」） |
> | 能否宣称「生活气息已改善」 | **BLOCK —— 不能。** L-7 只是「结构性对冲」这一道子盾解除，不是质量结论 |
> | R17 | **只登记读数与成本，不下效果判定**（缺 `meta.json`、无 dequp 契约行 ⇒ 契约自检不完整） |
>
> 仓库：`<repo-root>`
> R16 批次代码身份：`code_sha = a851a8fcac82846cc12150df43783d4c5922e902`（分支 `feat/l7-dequp-v2`，worktree `.worktrees/l7v2-dequp-n16r60`）
> R17 批次代码身份：`code_sha = 3730240f3ad8416f69b5d90d016b4e42fe008c9e`（`feat/l7-structural-dedup`，主树 `code/`）
> 本报告执行时 HEAD：`3730240f3ad8416f69b5d90d016b4e42fe008c9e`；纪律：**本轮零跑批**、未改 `code/**`、**只做本地 commit（不 push）**

---

## 0. 摘要 TL;DR

**一句话**：把「R16 跑完无报告、R17 跑完无读数」这两笔悬账结掉。R16 的读数我逐项独立复算**全部一致**，其 M1 判定是 **BELOW_BAND（带外·下侧）**——这解除的是「加生活气息原料必被 L-7 反噬」这一**结构性对冲**，**不是**「居民对话生活气息变好了」。

### 0.0 判定表（三件事分开给，不合并）

| 判定项 | 结论 | 一句话理由 |
|---|---|---|
| **① R16 读数是否可复算复现** | **PASS** | 自写复算器（不 import 既有判定器）从 `run.jsonl` 重算 **16 项逐项一致**；`n_msg=510`、`raw8=111`、`norm8=74`、S1 412 / S2 0 / S3 0 / S3b 6、成本 674/3042/733601 全部对上 |
| **② R16 的 M1 判定是什么** | **BELOW_BAND（带外·下侧）**（判定口径 Δ = −16.0784pp，基线 F-6=OFF；单变量口径另为 ≈ −45.29pp，见 §3.1） | `Δ = −16.0784pp`，噪声带 `[−4.31, +5.88]pp`，**下界 −4.31 被越过**；Wilson95 `[18.40, 25.55]%`，Newcombe Δ CI `[−21.53, −10.50]pp` **不含 0** |
| **③ 能否宣称「生活气息改善」** | **BLOCK** | L-7 下降**由机制构造直接决定**（v2 就是「撞了就重写，直到不撞」），且代价是 dialogue `tokens_in` **+216,678（+243.8%）**、`calls` **+164**；`collisions_after_retry=58` 说明还有 35.4% 重写后照样撞。**读数与「改善」之间没有链条。** |

### 0.1 本轮做了什么（零跑批，只算/只拍/只写）

1. **R16 独立复算**：`v2/evidence/recompute_l7_indep.py` 从 `run.jsonl` 自解析 510 条消息、自实现 8-gram 近重复，出 raw8 / norm8 / 守卫分子，落 `recompute_r16.txt`。
2. **R17 读数**：绕开 `run_batch_eval.sh` 的 `meta.json` 门禁（并**先把门禁复现出来**证明它确实会拒），直调官方指标器 + 自写复算器，落 `recompute_r17.txt`。
3. **R16 真截图三件套**：`gen_threads.py`（用**派生** meta）→ `serve.py`（setsid，8948）→ `dialogue_shots.sh` 四视图，落 `v2/evidence/l7v2_shots/`，`blank_retries=0/2`。
4. **本报告** + 证据索引（sha256 实算）+ 可复算命令块 + 边界声明。
5. 环境清理：`serve.py` 拍完 `pkill` 收回，无遗留进程。
   **纪律陈述（已按复审 F4 降级改写，不再说「双闸全程 rc=1」）**：本轮真实判据是 **`pgrep -af 'orchestration ru[n]'` 闸 —— 全程 `rc=1`（无命中）**；
   第二闸 `pgrep -af 'run_batc[h]'` **出现过一次 `rc=0`**，经核为**自匹配伪命中**（我生成 `recompute_r17.txt` 的外层 shell 命令行里含 `run_batch_eval.sh` 字样，见该回执 §0 如实留痕的超长 cmdline），**不含 `-m orchestration run` ⇒ 不是真实跑批**。
   **判别法**：真跑批的 cmdline 必含 `-m orchestration run`；伪命中的 cmdline 必含 `run_batch_eval.sh` 或 `pgrep` 自身。字符类 `[h]` 只能避开 `pgrep` 自身，避不开外层 shell 的整串，须靠 cmdline 复核。

### 0.2 必须最先说的两条口径事实（它们改变读法）

1. **「L-7」有两个口径，数值不同，且官方脚本只实现了其中一个。**
   `tools/d5/dialogue_metrics.py:471-490,588` 的 L-7 用 `normalize_body`（去标点 + 小写 + 全角转半角）取 8-window ⇒ **74/510 = 14.5098%（= 本报告的 norm8，辅助列，不参与判定）**；
   M1 判定用的 **raw8**（只 `re.sub(r"\s+","",body)`，保留标点）**不在该脚本里**，实现在 `v2/evidence/l7v2_judge.py:53-77` ⇒ **111/510 = 21.7647%**。
   两者差 37 条（交集 67、raw8 独有 44、norm8 独有 7）。**引用 L-7 时必须写明口径**，否则 14.5% 与 21.8% 会互相「打假」。
2. **`193/510` 这个基线数字在仓库里同时属于两批不同口径**（数值巧合，极易混用）：
   - **OFF 臂 raw8**（`run_f6_off_n16r60_seed42`）= **193/510 = 37.8431%** ← **这才是 R16 判定用的基线**；
   - **R12 DEQUP 臂 norm8**（`run_f6_dequp_n16r60_seed42`）= **193/510 = 37.8431%**（同批 raw8 是 268/510）。
   我用自写复算器把两批都跑了（`recompute_r16.txt` §4），实证这个巧合。
   **第三个交叉确认**：OFF 臂 `run.jsonl` 的 sha256 `c73bead61a440db789f6d6ba1de555fe326a203ee27d1219690174e3d9483642` 与 `reports/R11-f6-memory-into-dialogue.md:445` 登记的 OFF 臂 sha **逐位相同**（该报告 `:526-529` 的四张 OFF 截图文件名也带 `c73bead6`）⇒ 193/510 的归属可确定为 **OFF 臂 raw8**，不是「R12 的 norm8」。
   ⇒ 结论：R16 的 `Δ = 111 − 193 = −82 条` 是 **raw8 vs raw8 同口径配对**，**不是**跨口径相减；但 `l7v2_readings.md` 里那句「R12 的 193/510 属此口径(norm8)」的脚注**指向了另一个 193**，必须改写。

### 0.3 允许 / 禁止的结论形态

- ✅ 可以说：R16 的 L-7（raw8）**已不再高于 OFF 基线噪声带上界**（不是「击穿」）；机制侧构造存在且可审计（`dequp2 v=l7-dequp/2`，510/510 条消息带契约行，`preventive_hits=283`）。
- ✅ 可以说：S1–S3b 四条守卫全 PASS、S4 成本在门限内、G1–G5 契约自检全 PASS、`H**` 检验 PASS（58/164 = 35.4% ≤ 50%）。
- ⛔ **不可以说**：「L-7 改善」「生活气息提升」「居民对话更自然」「R16 过带 ⇒ 后续机制可以放开」。
- ⛔ **不可以说**：把 `Δ = −16.0784pp` 说成「v2 的单变量效应」。判定基线 `run_f6_off` 是 **F-6 OFF**、R16 是 **F-6 ON + DEQUP_V2 ON** ⇒ 该 Δ 是**净值**（含 F-6 0→1 的反向贡献，F-6 把 L-7 从 193 推到 342）。**v2 单变量口径 ≈ −45.29pp**，两数并存、禁混用（§1.1 末注 / §3.1）。
- ⛔ **不可以说**：把 R16 与 R17 的 `111 vs 163` 当作「结构臂 vs 重试臂」的净效果对比——两批 `code_sha` 不同、不在同一分支（`a851a8fc` 与 `3730240` 是兄弟关系，不是祖先关系），**不是单变量对照**。

---

## 1. 口径与分母（先钉死，再读数）

### 1.1 R16 的口令（单变量声明）

| 项 | 值 | 证据 |
|---|---|---|
| 唯一处理变量 | `LIFE_PROMPT_MEMORY_F6_DEQUP_V2=1` | `launch_evidence.txt` §单变量声明 ③（起跑瞬间生效 env） |
| 冻结上下文（与 R12 DEQUP 臂同构） | `LIFE_PROMPT_MEMORY_F6=1` | 同上 + `env_dump.txt`（`/proc/<pid>/environ`） |
| 明确未设 | `LIFE_PROMPT_MEMORY_F6_DEQUP`（v1 关）、`LIFE_PROMPT_GOSSIP_G1`、`HITT_DIALOGUE_REPAIR`、`HITT_DIALOGUE_EMOTION_ECHO`、`LIFE_PROMPT_L7_STRUCT` | `env_dump.txt` 只列 4 行（provider/凭据/F6/DEQUP_V2） |
| provider | `HITT_LLM_PROVIDER=openai_compat` | `env_dump.txt`；并与 run.jsonl 内 LLM_CALL `payload.provider` 交叉一致 |
| 模型（批内自报） | `DeepSeek-Flash` | run.jsonl LLM_CALL `payload.model` |
| ⚠️ **判定基线的 F-6 状态** | 判定基线 `run_f6_off_n16r60_seed42` 的 `LIFE_PROMPT_MEMORY_F6` 是 **OFF**（该臂 `ctx.memory_refs = 0/510`），而 R16 臂是 `=1`（`412/510`） | 自写复算器；`recompute_r16.txt` §7（三臂 `ctx.memory_refs` 逐批实测） |

> **一个必须说的取证瑕疵**：R16 目录**没有原始 `meta.json`**（`meta_gate.txt`：`meta.json 不可读 ⇒ 批次 VOID`）。
> 因此本报告的「批身份」由 `host.log` + `launch_evidence.txt` + `env_dump.txt` + `four_dir_integrity.txt` 四份旁证拼成，
> 并另写 `meta.derived.json`（逐字段标注派生来源，见 §4.2）。**这不等于原版 meta，也不能用于准入判定**。

> **⚠️ 单变量声明的重要限定（本报告头条 Δ 的读法）**：R16 相对**判定基线**并非只差一个变量。
> 基线 `run_f6_off` 是 **F-6 = OFF**，R16 是 **F-6 = ON + DEQUP_V2 = ON** ⇒
> **`Δ = −16.0784pp` 是「vs F-6-OFF 冻结锚」的净值，含 F-6 0→1 的反向贡献，不是 v2 的单变量效应。**
> 单变量口径的对照值另给（§3.1 第二行）：**v2 单变量 Δ ≈ −45.29pp**。**两个数并存、禁混用。**

### 1.2 分母

| 项 | 值 | 复算命令 |
|---|---|---|
| 日志非空行 | **116,498**（JSON 解析失败 **0**） | `recompute_r16.txt` §2 |
| `n_msg`（L-7 分母） | **510** | 同上 |
| 频道分布 | `MSG_DM 455` + `MSG_PUBLIC 55` + `MSG_GROUP 0` | 同上 |
| 线程数 / 单消息线程比 | 169 / 0.47929（**与 OFF 臂逐位相同**） | `metrics_r16_official.json` vs `d5_run_f6_off_..._r13close.json` |

> 分母 510 ≥ 30，满足「分母 < 30 只报事件数」的排除条件，故本轮可以比率。

### 1.3 噪声带与其取严方式

| 渠道 | 区间 | 说明 |
|---|---|---|
| 单池（single-pool） | `[−5.88, +5.88]pp` | `reports/R15-g1-gossip.md:334` 登记的 L-7(U8b) 单池带 |
| 双池（two-pool） | `[−4.31, +7.45]pp` | 同上 |
| **逐侧取严（本报告用）** | **`[−4.31, +5.88]pp`** | 下界取双池（更严）、上界取单池（更严）——与 `l7v2_judge.py:37` 冻结常量一致 |

> **边界**：噪声带的**原始推导文档（策略包 `r1-l7-strategy.md`）不在本仓库内**（`find` 零命中）。
> 本报告只能做到「与 R15 已发布读数的带登记逐位一致」，**无法在本仓内复算这条带的来源**——列入 §9 未验证项。

---

## 2. R16 独立复算：16 项逐项一致，差异为零

### 2.1 逐项比对（旧读数 vs 我的复算）

| # | 项目 | 旧读数（`l7v2_readings.md` / `l7v2_judge.stdout`） | 我的独立复算 | 一致 |
|---|---|---|---|---|
| 1 | n_msg（分母） | 510 | **510**（116,498 行，0 解析失败） | ✅ |
| 2 | raw8 dup（判定口径） | 111 | **111** | ✅ |
| 3 | raw8 率 | 21.7647% | **21.764706%** | ✅ |
| 4 | norm8 dup（辅助口径） | 74 | **74** | ✅ |
| 5 | norm8 率 | 14.5098% | **14.509804%** | ✅ |
| 6 | OFF 基线 raw8 | 193/510 = 37.8431% | **193/510 = 37.843137%**（我自己跑 OFF 臂得到） | ✅ |
| 7 | Δ（raw8 vs OFF raw8） | −16.08pp | **−16.0784pp** | ✅ |
| 8 | Wilson95(raw8) | `[18.402, 25.55]` | **`[18.402, 25.55]`** | ✅ |
| 9 | S1 F-6 记忆引用 | 412/510 | **412/510** | ✅ |
| 10 | S2 L-2 旁白头 | 0/510 | **0/510** | ✅ |
| 11 | S3 L-8 裸 ID | 0/510 | **0/510** | ✅ |
| 12 | S3b L-13 token 泄漏 | 6/510 | **6/510** | ✅ |
| 13 | S4 dialogue calls | 674 | **674** | ✅ |
| 14 | S4 total calls | 3042 | **3042** | ✅ |
| 15 | S4 total tokens | 733601 | **733601** | ✅ |
| 16 | dialogue tokens_in | 305556 | **305556** | ✅ |

### 2.2 差异说明（本节按任务要求单列）

**数值差异：无。** 16 项全部一致，且不是抄数——第 1–12 项来自自写脚本对 510 条原始消息的重解析与重算，第 13–16 项来自本轮亲跑的 `obs llm-cost`。

**表述差异：2 处（不改任何数值，但必须改口）；另有 1 处「对照源数字与我的亲跑不符」（见第 3 条）**

1. **口径标签**：任务书与旧读数都把 `dialogue_metrics.py:588` 称作 L-7 的「权威实现」，但它的值是 **74/510（norm8）**；判定用的 **111/510（raw8）** 来自另一份脚本。两者都被叫「L-7」是**口径混称**，须逐处写清（§0.2）。
2. **193 的归属**：`l7v2_readings.md` 表头写「OFF 基线 raw8（冻死）193/510」，脚注写「R12 的 193/510 属此口径(norm8)」——两句指向**两个不同的 193**。判定实际取的是 OFF raw8，配对同口径、结论不变，但脚注必须改为「OFF 臂 raw8 = 193/510（本报告 §4 已复算）」，并单独注明「R12 DEQUP 臂 norm8 恰好也是 193/510，属数值巧合，勿混引」。
3. **⚠️ OFF 臂成本数字与 `docs/forensics/2026-10-22-repo-state.md` §4.3 不符（以我的亲跑为准）**：该文件记 `dialogue tokens_in=88830 / tokens_out=12283`；我本轮亲跑 `obs llm-cost`（rc=0）得到 **`tokens_in=88878 / tokens_out=12057`**（差 **+48 / −226**）。
   影响面：§3.4 与 §5.3 的「变化量」据此重算（`+216,678 / +243.79%`、`+59,782 / +67.26%`）。**不影响任何 L-7 判定**（L-7 不依赖 token），但凡引用 OFF 成本的旧文字都应改口径。可能成因（**未验证，不猜**）：docs 记的可能是另一聚合路径或 cached 口径差异；本报告只以亲跑输出为准并登记差异。

### 2.3 「为什么掉得这么低」——三条诊断（回答策略包「不得直接当好结果」的要求）

BELOW_BAND 的字面含义是「比基线还好到了带外」。必须排除三种平凡解释：

| 可能的平凡解释 | 实测 | 判定 |
|---|---|---|
| **消息变短了**（短句 shingle 少 ⇒ 撞车天然变少） | R16 平均正文长 **36.87** 字 > OFF **32.38** 字；p50 33 > 29；p90 58 > 54 | **排除**（**仅此一项结论**）：消息没有变短，所以「撞车减少」不能由「句子变短」解释。⚠️ 但**正文变长不能归因于 v2**——F-6 记忆进提示词本身即会加长正文（两臂 F-6 状态不同，§1.1 末注）。**本条只作排除，不作机制归因。** |
| **线程结构变了**（线程被拆碎 ⇒ 跨线程不互撞） | 线程 169 = OFF 169；单消息线程比 0.47929 = OFF 0.47929；消息 510 = 510 | **排除**：结构逐位未变 |
| **模板命中被清零挤掉了重复** | L-5 模板命中率 OFF 1.176% → R16 **0%**；L-6 精确重复 OFF 10.20% → R16 **0%** | **部分成立但非主因**：这两项归零说明「套路句」被重写机制清掉了，仍属机制构造，不是自然多样性 |

**结论（判断）**：L-7 下降是 **v2 机制的构造性结果**（撞了就重写，直到 8-gram 不撞），不是「居民说话自然变多样」。
它的**代价与残余**必须与读数同读：`calls +164`、`dialogue tokens_in +216,678`、`collisions_after_retry = 58`（**35.4% 的重写后仍然撞**）。

---

## 3. M1 判定与守卫 S1–S4

### 3.1 M1 判定（raw8）

| 量 | 值 |
|---|---|
| raw8 dup | **111 / 510** |
| 率 | **21.7647%**（Wilson95 `[18.402%, 25.55%]`） |
| OFF 基线 raw8 | 193 / 510 = 37.8431% |
| **Δ（判定口径：vs F-6-OFF 冻结锚 193）** | **−16.0784pp**（= −82 条）。⚠️ 该基线 **F-6 = OFF** ⇒ 此 Δ 是**净值**，含 F-6 0→1 的反向贡献 |
| **Δ（v2 单变量口径，补充对照）** | **≈ −45.2941pp**（= **−231 条**/510）：对照臂 `run_f6_on_n16r60_seed42`（**F-6=ON 且无 v2**）raw8 = **342/510 = 67.0588%**（norm8 332/510 = 65.0980%，与 R12 ON 臂一致）⇒ `111 − 342 = −231 条`。**两数并存、禁混用**；单变量口径**未经策略包判据裁定**（带是按 OFF/DEQUP 臂标定的，对 F-6=ON 锚是否适用未检验）⇒ **只作对照，不作判定** |
| Newcombe95 Δ | **`[−21.526, −10.496]pp`**（不含 0 ⇒ 方向可检测，但**不等价于改善**）；此为**判定口径**的 CI，**不是** −45.29pp 那个数的 CI |
| 冻结带（逐侧取严） | `[−4.31, +5.88]pp` |
| **判定** | **BELOW_BAND**（`Δ < −4.31`，落带外·下侧） |
| 预注册目标区间对照 | `target_check`：`dup ≤ 223` ✔ 但 `dup ≥ 171` ✘ ⇒ **111 也低于目标下界** |

**F-6 对照臂的复现命令**（我亲跑，输出见 `recompute_r16.txt` §7）：

```bash
python3 v2/evidence/recompute_l7_indep.py --log v2/evidence/run_f6_on_n16r60_seed42/run.jsonl --tag 'RUN_F6_ON (F-6=1, 无 v2)'
# → raw8 = 342/510 = 67.058824%｜norm8 = 332/510｜S1 F-6 412/510｜S3b L-13 14/510（>9，破 v1.1）
```

**怎么读这两个 Δ（必须同时出现，不许只引一个）**：
| 读法 | 数 | 能说明什么 | 不能说明什么 |
|---|---|---|---|
| **判定口径**（vs F-6-OFF 锚） | **−16.0784pp** | 「相对仓库现有的 F-6-OFF 冻结锚，R16 臂的 L-7 更低」 ⇒ 这是 M1 档位所依赖的那一个数 | **不能**说明「这是 v2 的功劳」——F-6 打开本身把 L-7 从 193 推到 342 |
| **v2 单变量口径**（vs F-6=ON 无 v2） | **−45.2941pp** | 「在 F-6 已开的前提下，v2 把 L-7 从 342 压到 111」 ⇒ 量级远大于 −16.08pp | **不能**当 M1 判定数（该锚未经策略包登记，带是否适用未检验） |

> **写法纪律**：`BELOW_BAND` **不是**「IN_BAND」，也**不是**「OUT_OF_BAND（击穿）」。三者在策略包里是不同档：
> 只有 `IN_BAND` / `IN_BAND_AND_DIR_NEG` 才是「回到带内」。本报告**不把它写成「过带」**。
> 准确说法：**「R16 不再击穿上界（结构性对冲解除），但落到下侧带外，按策略包须先查结构/措辞，不得直接当好结果。」**

### 3.2 守卫 S1–S3b（自写复算，非抄）

| 判据 | 实测 | 门限 | 结果 |
|---|---|---|---|
| S1 F-6 记忆引用 | **412/510** | ≥ 32/510 | **PASS** |
| S2 L-2 旁白开头 | **0/510** | == 0 | **PASS** |
| S3 L-8 裸 ID | **0/510** | == 0 | **PASS** |
| S3b L-13 token 泄漏 | **6/510** | ≤ 9（策略包 v1.1） | **PASS**（⚠️ 相对 OFF 的 2/510 **升了 4 条**，未破门限但需登记为「趋势项」） |

### 3.3 S4 成本守卫与契约 G1–G5（我自己重算，不引旧结论）

| 契约 | 实测 | 结果 |
|---|---|---|
| G1 `dequp2` 覆盖全部消息 | **510/510** | PASS |
| G2 末行版本 | `v = l7-dequp/2` | PASS |
| G3 恒等式 | `Σretried = 164 = retries`；`collision_after_retry 58 + resolved_after_retry 106 = 164`；`index_size 509 = messages 510 − 1` | PASS（三条同时成立） |
| G4 `dialogue_calls − 510 = retries` | `674 − 510 = 164` | PASS |
| G5 `den_retries = retries` | `164 = 164` | PASS |

| S4 门限 | 实测 | 门限 | 结果 |
|---|---|---|---|
| `purpose=dialogue` calls | **674** | ≤ 1020 | OK |
| 总 calls | **3042** | ≤ 3450 | OK |
| retries | **164** | ≤ 510 | OK |
| **S4 判定** | — | — | **OK** |

| `H**`（重写后仍撞比例） | 值 |
|---|---|
| `collision_after_retry / retries` | **58 / 164 = 0.3537** |
| 规则 | `> 0.50 且 retries ≥ 30 ⇒ 失效` |
| 结果 | **PASS（35.4% ≤ 50%）** —— 分母是**重试次数**，不是消息数，**不得**当 L-7 读数引用 |

### 3.4 成本（正面回答：L-7 下降是「更会说话」还是「多问了一遍」？）

| 项 | OFF 臂（`run_f6_off`，**本轮亲跑 `obs llm-cost`**，rc=0） | R16（本轮亲跑 `obs llm-cost`） | 变化 |
|---|---|---|---|
| `purpose=dialogue` calls | 510 | **674** | **+164（= retries，逐值相等）** |
| `dialogue` tokens_in | 88,878 | **305,556** | **+216,678（+243.79%）** |
| `dialogue` tokens_out | 12,057 | 21,189 | +9,132（+75.74%） |
| `total` calls | 2878 | 3042 | +164 |
| `total` tokens_total | 484,835 | **733,601** | +248,766（+51.31%） |
| `degraded` | 0 | **0** | — |
| `cached / calls` | 1472/2878 = 51.15% | **1425/3042 = 46.84%** | 缓存率下降 |

**归因（判断）**：`dialogue calls − 510 = 164 = retries` 逐值相等 ⇒ 多出的 **164 次对话调用 100% 是 v2 撞车重写成本**，不是新增内容。
**因此本报告只报「L-7 读数 + 成本」，不报「对话质量提升」**：读数下降的**机制贡献**（重写到不撞）与**内容贡献**（说话更不一样）在本实验设计下**不可分离**（臂只开了 v2 一个变量，但 v2 本身就含「重写」动作）。

> ⚠️ **写进报告的硬边界**：`obs llm-cost` 读的是**事件日志自报的 provider**，它**不能证明上游 API 真的被调用过**。
> 三条旁证（`provider_guard.ok=true` + `problems=[]` + `by_provider` 仅 `openai_compat(3042)`；`tokens_in/out > 0` 且 `cached ≠ calls`；R16 目录**无** `meta.json` 的 `fallback_detected` 批级自报锚，只能用 `env_dump.txt`+`launch_evidence.txt` 替代）**只能证明「日志里没有 mock 混入」**，不能证明端点侧真扣费。**仓内无端点计费/网关硬证。**

---

## 4. 真截图三件套（`v2/evidence/l7v2_shots/`）

### 4.1 三件套齐备性

| 件 | 内容 | 齐备 |
|---|---|---|
| ① 来源 run 目录 | `v2/evidence/run_l7v2_on_n16r60_seed42/`，`run.jsonl` sha256 `ee3d28bc9606f2c2ee6609af7c5272673e54db674d5268878aa5d99e477f11b8`（55,598,046 B / 116,498 事件 / 510 消息） | ✅ |
| ② 渲染命令 | `gen_threads.py` → `serve.py`（setsid, 8948）→ `dialogue_shots.sh`（见 §4.1 代码块与 §7） | ✅ |
| ③ 日志 sha256 | `render.log` = `8b56486dfeb51525299f1e836238e988578789e1ab0ab9f935003d923698f791` | ✅ |

```bash
# 在 code/ 下执行（完整可复现）
python3 frontend/tools/gen_threads.py \
  --log ../v2/evidence/run_l7v2_on_n16r60_seed42/run.jsonl \
  --meta ../v2/evidence/run_l7v2_on_n16r60_seed42/meta.derived.json \
  --out frontend/sample/dialogue_l7v2/threads.json --label l7v2
setsid python3 frontend/tools/serve.py --port 8948 > /tmp/serve_l7v2_8948.log 2>&1 < /dev/null &
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8948 sample/dialogue_l7v2/threads.json "" "" ../v2/evidence/l7v2_shots
pkill -f 'serve.p[y] --port 8948'
```

> 8848 端口当时被另一进程占用（HTTP 200，同为本仓 frontend），为免歧义本批改用**独立实例 8948**，拍完立即 `pkill` 收回。`serve.py` 用 `setsid` 起、无长 sleep（`shot.py` 等 `window.__RENDER_READY__`）。

### 4.2 ⚠️ meta 是**派生**的，不是原始的（显式标注）

R16 目录没有原始 `meta.json`。按任务纪律**不伪造**，改写出 `meta.derived.json`，每个字段都标注派生来源，且**必须用它跑通后才出图**：

| 字段 | 派生来源 |
|---|---|
| `n=16` / `rounds=60` / `events=116498` | `host.log` 第 5 行 `[life] n_agents=16 rounds=60 ... events=116498`（与 run.jsonl 非空行数 116,498 实测一致） |
| `seed=42` | `host.log` argv `--seed 42` |
| `code_sha=a851a8fc…` | `host.log` `[d2] code_sha=`；`launch_evidence.txt` `HEAD:`；`four_dir_integrity.txt` `HEAD=`（三处同值） |
| `provider=openai_compat` | `env_dump.txt`；并与 run.jsonl LLM_CALL `payload.provider` 交叉一致 |
| `model=DeepSeek-Flash` | run.jsonl LLM_CALL `payload.model`（批内自报） |
| `llm_cached_ratio=0.46844` | 本轮 `obs llm-cost`：1425/3042 |
| `started_at` / `finished_at` | `launch_evidence.txt` 采集时刻 `06:16:52` + `host.log seconds=2500.5991` ≈ `06:58:33`（本批无批内墙钟戳，只有 `mono_ts`） |
| `weeks` | **故意留空**（无旁证，argv 未传 `--weeks`） |

> **⚠️ 勘误（复审 F3，2026-10-22）**：本报告与 `l7v2_shots/README.md` 早前写过「页面芯片显示 **meta 已派生**」——**该陈述不实，已删除**。
> OCR 实测 chat 图右上角芯片是 **`· meta 已对齐`**；`code/frontend/src/dialogue.js:512` 全仓只有 `note.textContent = "· meta 已对齐"` 这一个字符串，
> **不存在「已派生」分支**（判据：`grep -rn "已派生" code/frontend/` 零命中）。
> ⇒ 该芯片的口径是「meta/provider 字段存在即点亮」，**前端无法区分原始 meta 与派生 meta**。
> **「本批 meta 是派生的」这件事只能由本报告 §4.2 表格与 `meta.derived.json` 的 `_meta_kind=derived` 字段自证，不能由页面自证。**

### 4.3 四张图（sha256 实算）

| # | 文件 | 视图 / 视口 | 字节 | sha256 | `blank_retries` |
|---|---|---|---|---|---|
| 1 | `l7v2-chat-ee3d28bc.png` | 对话流 chat 1400×900 | 261,270 | `6efdaabcf80ff53a3f1c4c4777fea4281c7937aece6c69b9eca1a6ce5cb8df52` | 0/2 |
| 2 | `l7v2-rhythm-ee3d28bc.png` | 节律·串门 rhythm 1300×1050 | 282,904 | `fee577e4d9995bf497399f02645135a76170fcbf6a2a97294e85936181f9f2ce` | 0/2 |
| 3 | `l7v2-spread-ee3d28bc.png` | 闲话传播 spread 1300×900 | 175,610 | `77ef11669c6ebc1b87047dcffafb7de49f229d447ddf8dec61a74518f36d76a1` | 0/2 |
| 4 | `l7v2-600-ee3d28bc.png` | 600px 判读 600×900 | 190,684 | `9c50e3266bedb63efda63c2e6c1586bc557456d231daa8698c4f8656563694b8` | 0/2 |

`mean_brightness` 33.5 / 32.4 / 23.1 / 39.2，`max_color_frac` 30.31% / 34.43% / 71.18% / 33.77%（`render.log`）⇒ 首帧即有内容，非全黑假图。
`sha8=ee3d28bc` 由 `threads.json.source.run_sha256` 自动派生并在 `dialogue_shots.sh` 内**自校验**，人工传错即报错退出。

### 4.4 必须与图同时读的边界

**spread（闲话传播）视图是「真实渲染 + 真空态」**：本批日志 `msg_refs` 全为空（`gen_threads` 报 `ref_edges=0`），页面照实显示空态并写明「不用相似度硬凑」。
⇒ 这**不是渲染失败**，也**不是**「本批没有闲话传播」的结论——该口径需要日志记录消息引用关系才可测，**本批不具备**。
**同一原因的连带事实**：R16 的 `echoes=0`（无 8-gram 回声聚合）与 `ref_edges=0` 同源。

---

## 5. R17（L-7 结构臂）：**只登记读数与成本，不下效果判定**

### 5.1 先复现门禁，再绕开它（不是「把门禁当成通过」）

```bash
$ bash tools/d5/run_batch_eval.sh v2/evidence/run_l7struct_on_n16r60_seed42 r17gate ; echo rc=$?
== 0) 输入检查
[FAIL] 缺 meta.json（跑批未正常收尾）——按准入清单 B-7 拒绝出数
rc=2
```

⇒ 门禁**确实会拒**（`exit 2`，未触发任何 LLM 调用、未写任何文件）——这条本身就是 K1 缺口的现场证据。
绕开方式：**直接调用指标器**（`dialogue_metrics.py`）+ **自写复算器**，输出全部落 `recompute_r17.txt`，并在报告里明示「R17 未过准入」。

### 5.2 读数（`recompute_r17.txt`）

| 项 | R17 L-7 结构臂 | 备注 |
|---|---|---|
| 批身份 | `code_sha 3730240f…`；`run.jsonl` sha256 `4df89f4ac1dac1a8df00766b538f4fe12c9e9999664bcf6a606054438446fb5e`；116,385 事件；510 消息（455 DM + 55 PUBLIC） | `host.log`：`LIFE_PROMPT_L7_STRUCT=1` 其余对话开关全未设；`seconds=3141.9324`；chain/replay/conservation 全 True；`final_state_hash=sha256:fec8a5c9…` |
| L-7 **raw8**（判定口径） | **163/510 = 31.9608%**（Wilson95 `[28.061, 36.130]%`） | 自写复算器 |
| L-7 norm8（= 官方脚本 L-7） | 128/510 = 25.0980% | 官方 `dialogue_metrics.py` 与自写复算器一致 |
| Δ（raw8 vs OFF raw8 193） | **−5.8824pp**（−30 条/510）；Newcombe CI `[−11.677, −0.033]pp` | 字面上也落在下界之外 |
| 守卫 | S2 0/510、S3 0/510、S3b **2/510** 全 PASS；**S1 F-6 = 0/510（本臂 F-6 未开 ⇒ 该守卫对本臂不适用，不得记为 FAIL）** | 同上 |
| 契约 | `dequp2` 行 **0**、`retries 0`（结构臂无重试机制）⇒ **G1–G5 契约自检不适用/不完整** | 自写复算器 |
| dialogue calls | **510**（= n_msg，零重试） | 本轮亲跑 `obs llm-cost`，rc=0 |
| **dialogue tokens_in** | **148,660** | 同上 |
| dialogue tokens_out | 19,093 | 同上 |
| total calls / tokens_total | 2878 / 574,420；`cached` 1425（49.51%） | 同上 |
| `provider_guard` | `ok=true`、`problems=[]`、`by_provider` 仅 `openai_compat(2878)` | 同上 |

### 5.3 成本对照（结构约束 = 用 token 换重试）

| 目的 | OFF 臂（`run_f6_off`，**本轮亲跑**） | R17（本轮亲跑） | 变化 |
|---|---|---|---|
| `dialogue` calls | 510 | 510 | 0（**零重试**） |
| `dialogue` tokens_in | 88,878 | **148,660** | **+59,782（+67.26%）** |
| `dialogue` tokens_out | 12,057 | 19,093 | +7,036（+58.36%） |
| `total` tokens_total | 484,835 | 574,420 | +89,585（+18.48%） |

**机制解读（判断）**：R17 把「事后重写」换成「生成前加结构约束行」，所以 `calls` 恰好回到 510，但每次对话输入多了一段约束 ⇒ `tokens_in +67.26%`。
与 R16 的 `+243.9%` 相比**单价便宜得多**，但这是**不同 code_sha 的两条不同实现**，**不能**据此说谁更优（不是单变量对照）。

### 5.4 为什么本报告不给 R17 效果判定

1. **契约自检不完整**：无 `meta.json`（准入 REJECTED）、无 `dequp2` 契约行 ⇒ S4 的 G1–G5 无从校验。**「S4 无法确认」不能当成「S4 通过」。**
2. **S1 不适用**：F-6 在本臂未开，`S1=0/510` 是设计使然，不是破守卫。
3. **噪声带适用性未检验**：带是按 OFF/DEQUP 臂标定的，结构臂零重试、分布可能不同 ⇒ 是否「同分布可比」未检验。
4. 任务书明令不得替 R17 下效果判定。**本节只登记读数与成本**；判定需先补 `meta.json`（或为结构臂单独登记一套不带 dequp 契约的判据），再由 Leader 裁定。

---

## 6. 证据索引表（sha256 全部实算，非抄）

| # | 结论 | 层级 | 来源 | sha256 | sha8 | 复现 |
|---|---|---|---|---|---|---|
| 0 | **本报告自身**（自锚项，复审 F2 补） | 【事实】 | `reports/R16-l7-dequp-v2.md` | 在 commit **`b74a54d`** 的树中实算 = `14e19e755e07e06dd2e332cefbd0f0ba2865131a92dd4fcd708441d708c17a86`（自指无法内嵌，见「自锚说明」） | `14e19e75` | `git show b74a54d:reports/R16-l7-dequp-v2.md \| sha256sum` |
| 1 | R16 日志 510 消息 / 116,498 事件，raw8 = 111/510 | 【事实】 | `v2/evidence/run_l7v2_on_n16r60_seed42/run.jsonl` | `ee3d28bc9606f2c2ee6609af7c5272673e54db674d5268878aa5d99e477f11b8` | `ee3d28bc` | `recompute_r16.txt` §2 |
| 2 | R16 复算回执（16 项逐项比对 + 差异说明） | 【事实】 | `v2/evidence/run_l7v2_on_n16r60_seed42/recompute_r16.txt` | `4703575e5558f89e6a2b0332495e9539764aa83842e756bee3609a6ec06cb835` | `4703575e` | §7 命令块 |
| 3 | 复算器（自写，不 import 既有判定器） | 【事实】 | `v2/evidence/recompute_l7_indep.py` | `ae50620d3b9bdd3add9d81cdd47186b87936d15a56eca58d76dbd44686b952f0` | `ae50620d` | `python3 v2/evidence/recompute_l7_indep.py --log <log>` |
| 4 | R16 派生 meta（**非原始**，逐字段标源） | 【事实】 | `v2/evidence/run_l7v2_on_n16r60_seed42/meta.derived.json` | `cf91b9fed7f979e7bd260b9df8932d9514ea3b926ea747e655b590f6512d3f80` | `cf91b9fe` | 读文件即见 `_derivation` |
| 5 | 官方口径读数（L-7 = norm8 = 74/510、L-1 长度、L-5/L-6、L-13） | 【事实】 | `v2/evidence/metrics_r16_official.json` | `9cb19f7be2d3b4548dc9a7a31bc53fad226295bdbeccb04666ee3ebbbae7a6a1` | `9cb19f7b` | `python3 tools/d5/dialogue_metrics.py --log <R16 log> --out-json <同路径>` |
| 6 | OFF 臂 raw8 = **193/510**（判定基线口径确认）；同批 norm8 = 181/510 | 【事实】 | `v2/evidence/run_f6_off_n16r60_seed42/run.jsonl`（gitignored，sha256 记于回执内） | `c73bead61a440db789f6d6ba1de555fe326a203ee27d1219690174e3d9483642` | `c73bead6` | `recompute_r16.txt` §4 |
| 6′ | R12 DEQUP 臂 **norm8 = 193/510**（raw8 = 268/510）——「193 巧合」的另一半 | 【事实】 | `v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl` | `6bf3ec88700fa1a7451b18c63678d0904c69b9de39896739190e7e674db8fdbd` | `6bf3ec88` | `recompute_r16.txt` §4 |
| 6″ | **F-6=ON 且无 v2** 对照臂：raw8 = 342/510 = 67.0588%（norm8 332/510）——§3.1「v2 单变量口径」的对照臂 | 【事实】 | `v2/evidence/run_f6_on_n16r60_seed42/run.jsonl`（gitignored，sha256 记于回执内） | `7de6a7be5adff276f1e42c065a708c271f870f2bf8daa930cf0cdfc983f7434d` | `7de6a7be` | `recompute_r16.txt` §7 |
| 7 | OFF 臂官方口径（线程 169 / 单消息比 0.47929 / L-1 32.384） | 【事实】 | `v2/evidence/d5_run_f6_off_n16r60_seed42_r13close.json` | `cb757208249dd9fc02bbd712d70070c1d998d018aab3b89e84a3721502fc355c` | `cb757208` | 读 JSON 即得 |
| 8 | 四张真截图 | 【事实】 | `v2/evidence/l7v2_shots/*.png`（见 §4.3 逐张 sha256） | — | `ee3d28bc`（数据源 sha8） | §4.1 命令块 |
| 9 | 渲染日志（`batch=`/`SHOT OK`/`blank_retries`） | 【事实】 | `v2/evidence/l7v2_shots/render.log` | `8b56486dfeb51525299f1e836238e988578789e1ab0ab9f935003d923698f791` | `8b56486d` | 同上 |
| 10 | 截图目录三件套说明与命令 | 【事实】 | `v2/evidence/l7v2_shots/README.md` | `538ab898ca0c0ddf73ca08890ff0a5894ab057622cd8ef95b0eba243daa7f2d8` | `538ab898` | 读文件 |
| 11 | `threads.json`（510 消息 / 169 线程 / 60/60 TURN_SEAL） | 【事实】 | `code/frontend/sample/dialogue_l7v2/threads.json` | `ed0ebff959ffa4789e9e8da38525bea16c0865077dfe0420700c9e75bea5b115` | `ed0ebff9` | §4.1 命令块 |
| 12 | R17 读数回执（含门禁 exit 2 复现） | 【事实】 | `v2/evidence/run_l7struct_on_n16r60_seed42/recompute_r17.txt` | `341e4c26a436a66d50f967875f60e55c73d2895677f2ea11a93580d1a70b3f42` | `341e4c26` | §7 命令块 |
| 13 | R17 日志（510 消息 / 163 raw8 / 128 norm8） | 【事实】 | `v2/evidence/run_l7struct_on_n16r60_seed42/run.jsonl` | `4df89f4ac1dac1a8df00766b538f4fe12c9e9999664bcf6a606054438446fb5e` | `4df89f4a` | `recompute_r17.txt` §4 |
| 14 | R17 官方口径读数 | 【事实】 | `v2/evidence/metrics_r17_official.json` | `d1597e2d3ad0cb1316638d875d8a959ea0dc79d5d65b361f166fdee08d3f9a5f` | `d1597e2d` | `recompute_r17.txt` §3 |
| 15 | 旧读数原件（对照用，非本报告数值来源） | 【对照】 | `v2/evidence/run_l7v2_on_n16r60_seed42/l7v2_readings.md` | `324d86b737f3446d3aca931e203f272b42f4cb8cea41916d1e7e6951bdc3ce9c` | `324d86b7` | — |
| 16 | 旧读数 JSON（对照用） | 【对照】 | `v2/evidence/run_l7v2_on_n16r60_seed42/l7v2_readings.json` | `cbaaa39e3fa2a3508326f98958bfd3b4343f325871196024b6f0a75b9c2cdffd` | `cbaaa39e` | — |
| 17 | 噪声带 `[−4.31,+5.88]`（逐侧取严）的仓内出处 | 【对照】 | `reports/R15-g1-gossip.md:334`、`:455` | —（文本行，见该文件） | — | 读该文件两行 |

> **自锚说明（F2）**：报告不能把自身的 sha256 内嵌进自己——写入哈希会改变文件、进而改变哈希（不定点），因此任何「内嵌自身 sha」都**不可能**同时成立。
> 本报告采用的口径是「**锚定到指定 commit + 给方法**」，两条都可独立复核：
> 1. **定值**：`git show b74a54d:reports/R16-l7-dequp-v2.md | sha256sum` ⇒ `14e19e755e07e06dd2e332cefbd0f0ba2865131a92dd4fcd708441d708c17a86`（该 commit 即 F1–F5 返工稿的入库 commit；本行文字本身是在其后的 commit 中追加的，故**当前 HEAD 树中的本文件哈希必然不同**，属预期）。
> 2. **方法（适用于任何后续 commit）**：`git show <commit>:reports/R16-l7-dequp-v2.md | sha256sum`。
> 历史参考：本文件在 `a4fcf19`（首版）中的 sha256 为 `21e1ac59a6bb01b29fbbe5396f8e87f1a586700d24856ebc77c2841b67585afc`。
> 其余 16 行（#1–#17）都是**他物**，sha256 可内嵌且已逐位实算登记。

> 「层级」列语义：【事实】= 可从日志/文件复算或直接读到；【对照】= 只作对照、不是本报告数值来源；【判断】= 本报告的推理结论（在正文明确标注）；【未验证】= §9 列出的缺口。

---

## 7. 可复算命令块（照抄可用；全程零跑批、零 LLM）

```bash
cd "<repo-root>"

# 0) 跑批双闸（防自匹配）
pgrep -af 'orchestration ru[n]'; echo rc=$?      # 期望 rc=1
pgrep -af 'run_batc[h]';        echo rc=$?      # 期望 rc=1

# 1) R16 独立复算（raw8 / norm8 / 守卫分子）
python3 v2/evidence/recompute_l7_indep.py \
  --log v2/evidence/run_l7v2_on_n16r60_seed42/run.jsonl --tag 'R16 L-7v2 ON'

# 1b) F-6 对照臂（§3.1「v2 单变量口径 −45.29pp」的来源；F-6=ON 且无 v2）
python3 v2/evidence/recompute_l7_indep.py \
  --log v2/evidence/run_f6_on_n16r60_seed42/run.jsonl --tag 'RUN_F6_ON (F-6=1, 无 v2)'
# → raw8 = 342/510 = 67.058824%

# 2) 官方口径（其 L-7 = norm8 = 74/510）
python3 tools/d5/dialogue_metrics.py \
  --log v2/evidence/run_l7v2_on_n16r60_seed42/run.jsonl \
  --out-json v2/evidence/metrics_r16_official.json --out-md v2/evidence/metrics_r16_official.md

# 3) 基线口径确认：OFF 臂 raw8 = 193/510（不要抄，自己跑）
python3 v2/evidence/recompute_l7_indep.py --log v2/evidence/run_f6_off_n16r60_seed42/run.jsonl
python3 v2/evidence/recompute_l7_indep.py --log v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl

# 4) 真 LLM 成本（rc 即判决）
(cd code && python3 -m obs llm-cost \
  --log "../v2/evidence/run_l7v2_on_n16r60_seed42/run.jsonl" --require-provider openai_compat)

# 5) R17 读数（先看门禁确实会拒，再直调指标器）
bash tools/d5/run_batch_eval.sh v2/evidence/run_l7struct_on_n16r60_seed42 r17gate; echo rc=$?   # 期望 rc=2
python3 v2/evidence/recompute_l7_indep.py --log v2/evidence/run_l7struct_on_n16r60_seed42/run.jsonl --tag 'R17'
python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_l7struct_on_n16r60_seed42/run.jsonl \
  --out-json v2/evidence/metrics_r17_official.json --out-md v2/evidence/metrics_r17_official.md
(cd code && python3 -m obs llm-cost \
  --log "../v2/evidence/run_l7struct_on_n16r60_seed42/run.jsonl" --require-provider openai_compat)

# 6) 截图三件套（见 §4.1；在 code/ 下执行）
#    或者直接核对已入库产物：
sha256sum v2/evidence/l7v2_shots/*.png v2/evidence/l7v2_shots/render.log
```

---

## 8. 边界与「不可判」声明（硬约束，逐条列）

1. **`obs llm-cost` 不能证明上游 API 真被调用**。它读的是事件日志自报 provider；旁证只有 `provider_guard` + token 计数 + freeze 缓存命中率。**仓内没有端点侧计费/网关硬证**（内网端点地址不透出；公开版只写「内网端点」，无网关日志）。
2. **R16 目录无原始 `meta.json`** ⇒ `fallback_detected` / `degraded_calls` 的**批级自报锚缺失**；出图用的 meta 是**派生物**，报告已逐字段标源。任何「R16 批次准入 PASS」的说法本报告都不给。
3. **L-7 下降与「对话质量改善」之间没有链条**。v2 机制的定义就是「撞了就重写」，读数下降是构造性结果；本轮设计**无法分离**「重写」与「内容变多样」的贡献。
4. **BELOW_BAND 不等于好结果**。策略包对带外·下侧的处置要求是「先查消息条数/线程结构/守卫」，本报告 §2.3 已查（结构未变、消息更长、模板/精确重复归零），但**仍不足以升级为质量结论**。
5. **R16 与 R17 不是单变量对照**：`a851a8fc`（`feat/l7-dequp-v2`）与 `3730240`（`feat/l7-structural-dedup`）是**兄弟分支**，`git merge-base --is-ancestor` 返回**否**。两者 `Δ code/life` 涉及 `agent.py / anti_repeat.py / l7_structural.py` 共 295 行增删 ⇒ **不得**把 `111 vs 163` 读成两条机制的净效果差。
6. **spread 视图空态 ≠ 传播为零**：本批 `msg_refs` 全空（`ref_edges=0`），该口径在本批不可测。
7. **噪声带的来源文档不在仓内**（策略包 `r1-l7-strategy.md` 零命中），本报告只能做到「与 R15 已发布的带登记一致」，**无法在仓内复算该带**。
8. **`l7v2_readings.md` 的脚注需改写**（见 §2.2）；本报告不复用其结论文字，只把它的数值当「对照项」逐条复算。

---

## 9. 未验证项（明确列出，不假装完成）

| # | 未验证项 | 为什么没做 / 需要什么才能做 |
|---|---|---|
| U1 | **噪声带的原始推导与复算** | 策略包 `r1-l7-strategy.md` 不在仓内；需要把该文件入库或补一份带推导的复算脚本（bootstrap 单池/双池） |
| U2 | **`collision_after_retry = 58` 这 58 条的实际内容** | 需人工抽读这 58 条（seq 可从 `ctx.dequp2` 取），判断是「巧合撞」还是「模板残留」。本轮未做人工判读 |
| U3 | **R16 与 R17 的可比性** | 两批 code_sha 不同、无交集祖先；要可比必须把其中一个机制 rebase 到同一棵树再跑（须新跑批，本轮零跑批） |
| U4 | **真实上游计费** | 无端点侧网关日志；只能靠 `obs llm-cost` 间接证据 |
| U5 | **`L-13` 从 2/510 升到 6/510 的成因** | 未破门限（≤9），但方向是**升**；需看这 6 条的 `ctx.topic` 与 body 才能定性 |
| U6 | **`preventive_hits=283` 的语义** | 该字段出现于 `dequp2` 末行（v2 新增），未在策略包里登记口径；本轮只登记数值，不当判据 |
| U7 | **R17 的效果判定** | 缺 `meta.json` + 无 dequp 契约行 ⇒ 契约自检不完整；需补 meta 或另立结构臂判据 |
| U9 | **v2 单变量口径 −45.29pp 未经判据裁定** | 该数的锚是 `run_f6_on`（F-6=ON 无 v2），**未在策略包里登记**；噪声带按 OFF/DEQUP 臂标定，对 F-6=ON 锚是否同分布**未检验** ⇒ 只作对照，不作判定（复审 F1 后明确降级） |
| U10 | **F-6 对 L-7 的独立效应** | 本报告只登记「F-6 OFF→ON 时 raw8 193→342（+29.2pp）」这一事实；**F-6 本身对 L-7 的因果量级未做单变量实验**（需 F-6 单开臂，属新跑批） |
| ~~U8~~ | **`reports/README.md` 总索引 R16 行** | **已在返工 commit 中补上**（按 Leader 指示纳入本次 commit，状态词 `BELOW_BAND（带外下侧，非改善结论）`）⇒ 本项**已关闭**，不再列为缺口 |

---

## 10. 下一步建议（不打乱账，按依赖排序）

1. **先补 R16/R17 的批级 `meta.json`**（或给结构臂单独登记判据）：这是 R17 从「读数」走向「可判定」的**唯一**前置，也是 K1 缺口的正面收口。
2. **再做「机制 vs 内容」分离臂**：把 v2 拆成 `DEQUP_V2_RETRY`（只重写）与 `DEQUP_V2_PREVENT`（只做生成前结构约束，即 R17 的思路），单开一个只含「预防」的臂 ⇒ 才能回答「L-7 下降是更会说话还是一次重写」。
3. **把 58 条重写后仍撞的消息人工读一遍**（U2）：这是唯一能判断「残余是巧合还是套路」的路径，零成本、零跑批。
4. **`L-13` 单独立项**（U5）：4 条增量虽在门限内，但方向反了，且与 L-7 无关，不要并进 L-7 的账。
5. **不要在 R16 的读数上继续叠加「生活气息」宣称**：L-7 只是子盾。真正要推进「生活气息」，下一维度应按 §0.3 的许可形态，先选一个**未被结构性对冲压住**的原料（F-6 记忆 / G-1 八卦 / 情绪呼应的默认值），再谈效果。

---

## 11. 本轮交付清单

| 交付 | 路径 | 状态 |
|---|---|---|
| 1 | `v2/evidence/run_l7v2_on_n16r60_seed42/recompute_r16.txt` | ✅ |
| 2 | `v2/evidence/run_l7struct_on_n16r60_seed42/recompute_r17.txt` | ✅ |
| 3 | `v2/evidence/l7v2_shots/`（4 PNG + `render.log` + `README.md`） | ✅ 三件套齐备 |
| 3′ | `v2/evidence/run_l7v2_on_n16r60_seed42/meta.derived.json`（**派生、非原始**） | ✅ 已显式标注 |
| 4 | `reports/R16-l7-dequp-v2.md`（本文件） | ✅ |
| 5 | 本地 commit（**不 push**） | ✅ sha 见任务汇报与 `git log -1`（commit 提交后无法回填本文件，以汇报为准） |

> **入库 commit 的完整文件清单（复审 F5 后补全，共 17 个）**：
> ① `reports/R16-l7-dequp-v2.md`（本文件）；
> ② `v2/evidence/recompute_l7_indep.py`（复算器）；
> ③ `v2/evidence/run_l7v2_on_n16r60_seed42/recompute_r16.txt`、④ `v2/evidence/run_l7struct_on_n16r60_seed42/recompute_r17.txt`（复算回执）；
> ⑤ `v2/evidence/run_l7v2_on_n16r60_seed42/meta.derived.json`（**派生** meta）；
> ⑥ `v2/evidence/metrics_r16_official.json`、⑦ `metrics_r16_official.md`、⑧ `metrics_r17_official.json`、⑨ `metrics_r17_official.md`（官方口径读数，`dialogue_metrics.py` 产物）；
> ⑩ `v2/evidence/l7v2_shots/l7v2-chat-ee3d28bc.png`、⑪ `-rhythm-`、⑫ `-spread-`、⑬ `-600-`（四张真截图）、⑭ `render.log`、⑮ `README.md`；
> ⑯ `code/frontend/sample/dialogue_l7v2/threads.json`（**截图渲染输入**，由 `gen_threads.py` 从 R16 `run.jsonl` 派生）；
> ⑰ `reports/README.md`（总索引补 R16 行，复核后按 Leader 指示追加）。
> 全部与本轮证据直接相关，**不含** `run.jsonl`（gitignored）、无关 untracked、`docs/` 全目录。
