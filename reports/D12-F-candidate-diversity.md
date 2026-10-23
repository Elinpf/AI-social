# D12-F · 候选结构多样化（在 D12-E 上补"可分性"这一步）——实验报告

> **半成品 · 不可引用（§3.103.3）**：本文件此刻是**零读数骨架**，不是交付物，**任何结论/数字引用一律无效**。
>
> **文件身份（必读）**：本文件此刻是**骨架 + 预登记原文逐字引用块 + 复算命令模板**，**不含任何读数、不含任何效果判定**。原因：D12-F 批次（`run_d12f_diverse_n16r60_seed42`）尚未收批，`v2/evidence` 下尚无终态 `meta.json`/读数底稿。**任何在收批前填入的效果结论都属事后编造**，本文件一律留 `【待终态】` 占位。
>
> 作者：`evidence-reporter`｜骨架落盘时刻：2026-10-23 16:3x (+08:00)｜仓库根：`social-experiment`
> 体例参照：`reports/R22-d12d-t2-judge.md`、`reports/R21-scene-pair.md`
> 预登记：`v2/refs/D12F-prereg-candidate-diversity.md`（跑前立此存照 2026-10-23 14:30，**在 D12-F 代码改动与跑批之前**）

## 0. 身份与口径（收批后按实填，本节数字一律实取，不抄旧文档）

| 项 | 值 | 取法（收批后执行） | 状态 |
|---|---|---|---|
| **判读对应代码 sha（`batch_code_sha`）** | `【待终态】` | 跑批树 `.worktrees/d12f-diverse` 的 HEAD：`git -C .worktrees/d12f-diverse rev-parse HEAD`；并与 `meta.json` 的 `code_sha` 交叉核对，二者不一致即如实写「不一致」 | 【待终态】 |
| 本臂开关真值 | `LIFE_PROMPT_D12F_DIVERSE=3`（默认 `1`=关闭） | `/proc/<pid>/environ` 留档或 `switch_proof.md` | 【待终态】 |
| `prompt_fn_sha256`（候选 0 / 1 / 2） | `【待终态】` | 候选 0 必须**逐字等于 T1 的 `effc14dbffdb6865…`**（预登记 §2 第 1 条） | 【待终态】 |
| 批次目录 | `.worktrees/d12f-diverse/v2/evidence/run_d12f_diverse_n16r60_seed42/` | `ls` | 【待终态】 |
| 规模 / seed | n=16 agents × 60 rounds，seed 42（预登记 §6） | `meta.json` | 预登记已写死 |
| 报告落笔基准 HEAD（文档身份，**非代码身份**） | `【待终态】` | `git rev-parse HEAD`（写报告时取） | 【待终态】 |

> **三组关系（不许混）**：
> - **T1 = 干净基线**（`v2/evidence/run_d12c_on_n16r60_seed42`，仅 `LIFE_PROMPT_D12C_SPECIFIC=1`）⇒ **本报告正式 Δpp 一律以 T1 为基线**；
> - **D12-E = 污染参考**（best-of-3；对话采样命中缓存 44.9%，M0 真调用仅 28.35%）⇒ **不作为效果基线、不出 Δ**，只作「同尺子证据 + 缓存污染参考」；
> - **D12-F = 本臂**（候选结构多样化，叠在 D12-E 的择优机制上）。

## 1. 阈值原文逐字引用块（**机械对照用，不得改写**）

> 目的：本轮所有口径争议都起于「预登记原文到底写的是什么」。此块**逐字抄录**，每条附 `文件:行号`；右列填本报告实际使用的值，**与左列不一致即必须在本节暴露**。

| # | 预登记原文（逐字） | 文件:行号 | 本报告实际使用的值 | 是否一致 |
|---|---|---|---|---|
| M1 | 「\| **M1** `ctx.d12f.m=3` 命中率 \| **= 100%** \| 接线 \|」 | `v2/refs/D12F-prereg-candidate-diversity.md:43` | `【待终态】` | 【待终态】 |
| M3 | 「\| **M3** 非全同分样本中 `picked==argmin` \| **= 100%** \| 择优逻辑正确性 \|」 | 同上 `:44` | `【待终态】` | 【待终态】 |
| M4 | 「\| **M4（本臂新增）** **候选可分性**（非全同分样本占比） \| **≥ 25%**（D12-E 实测 15.9%） \| **多样化必须真的提高可分性**，否则等于没做 \|」 | 同上 `:45` | `【待终态】`；**两种分母同时报**（见 §2.3） | 【待终态】 |
| 判据1 | 「\| 1 \| **`L-7` norm8** \| **≤ 55.10%** \| 55.88%（差 0.78pp） \|」 | 同上 `:53` | `【待终态】` | 【待终态】 |
| 判据2 | 「\| 2 \| **`L-7` raw8** \| **≤ 64.12%** \| 待 eval 口径复算 \|」 | 同上 `:54` | `【待终态】`（判定用 `v2/evidence/recompute_l7_indep.py` 的 raw8） | 【待终态】 |
| 判据3 | 「\| 3 \| **`P1`** \| **≥ 93.82%** \| 99.02% \|」 | 同上 `:55` | `【待终态】` | 【待终态】 |
| 判据4 | 「\| 4 \| **`F-2'`（= `F-2_content_drift.drift_rate`，仅 jaccard<0.10）** \| **≤ 75.09%** \| 73.61% \|」 | 同上 `:56` | `【待终态】` | 【待终态】 |
| 判据5 | 「\| 5 \| **`L-15 restate_strong`** \| **≤ 4.51%** \| 4.12% \|」 | 同上 `:57` | `【待终态】` | 【待终态】 |
| 口径正名 | 「**⚠ 口径正名（跑前，2026-10-23 15:35）**：本臂的「内容漂移」判据**只能用 `F-2_content_drift.drift_rate`（即 `F-2'`，仅 jaccard<0.10）**；D5 里另有旧键 `F-2_topic_drift`（tag 无交集 **且** jaccard<0.10）其 `status = LEGACY_DEAD_RULER`、**结构性恒 0**，若误用会得到 `0%→0%` 的**假 PASS**。报告一律写 `F-2'`，禁止混称。」 | 同上 `:59` | 本报告**全文只写 `F-2_content_drift` / `F-2'`**；凡提及 `F-2_topic_drift` 一律标注 `LEGACY_DEAD_RULER` | 一致（写作纪律） |
| 次级 | 「**次级（只记录）**：`len_p50`(excl) ≤57.2；结构 510/169/2 ±5%（**该树结构与 T1 同构是硬要求**）；`L-3` 含括号块率（D12-E 为 68.82%，**本臂不得再砍旁白**）；`L-6`（D12-E 已 0.78%，**不得显著回升**）。」 | 同上 `:61` | `【待终态】` | 【待终态】 |

### 1.1 判据实现的口径来源（**预登记未定实现，由本报告钉死**）

预登记 `:54` 的判据2 原文只写「**≤ 64.12%**」并在 D12-E 参照列写「待 eval 口径复算」——**即预登记没有指定读写器实现**。本报告按以下方式钉死，避免"事后换实现"：

| 项 | 值 |
|---|---|
| **`L-7` 判定实现（raw8 + norm8 同出一个脚本）** | `v2/evidence/recompute_l7_indep.py`，sha256 = **`ae50620d3b9bdd3add9d81cdd47186b87936d15a56eca58d76dbd44686b952f0`** |
| 同脚本输出两口径的行 | `:159` `[raw8 · 判定口径]`、`:161` `[norm8 · 辅助口径]` ⇒ **raw8 与 norm8 天然同源，排除第二次口径分叉** |
| 阈值 64.12% 的来源 | 与 D12-C 口径同源（`recompute_l7_indep.py` 自述「口径来源」段：`tools/d5/dialogue_metrics.py:471-490` 归一化 + `v2/evidence/l7v2_judge.py:53-77` 的 `re.sub(r"\s+","")` 8-window） |
| **不使用**的实现 | leader 临时实现（T1 基线 67.84%）——**仅作交叉参考，不参与判定**；D12-E 记录的「74.12% vs 67.84% 差 6.28pp」属参考臂缺陷，本报告只披露、不据此判 |

> 口径来源说明（收批后原文照抄进正文）：**raw8 实现由独立复核钉死为 `v2/evidence/recompute_l7_indep.py`（sha256 `ae5062…52f0`），与阈值 64.12% 同源（D12-C 口径）；不使用 leader 临时实现（基线 67.84%），该实现仅作交叉参考，不参与判定。**
> 核验：`sha256sum v2/evidence/recompute_l7_indep.py` 与 `git show HEAD:v2/evidence/recompute_l7_indep.py | sha256sum` 必须同为该值（2026-10-23 16:46 实测一致）。

## 2. 结论先行

> **判定：`【待终态】`**（只允许取自预登记 §5 五档：`有效` / `无效（拿具体性换去重）` / `无效（拿承接换去重）` / `无效（效果不足）` / `作废` / `机制未生效`）
> 一句话理由：`【待终态】`
> **禁止软化**：差 0.01pp 也是不达标；不得写「接近达标」「基本达成」「差一点就成」。

## 3. 读数表（T1 干净基线 → D12-F 本臂，逐项 Δpp）

| # | 指标 | 口径 / 分母 | T1（干净基线） | D12-F（本臂） | **Δpp** | 阈值 | 判读 |
|---|---|---|---|---|---|---|---|
| 1 | `L-7` norm8 | 全部 `MSG_*`，n=`【待终态】` | `【待终态】` | `【待终态】` | `【待终态】` | ≤ 55.10% | `【待终态】` |
| 2 | `L-7` raw8 | 同上（判定口径 `recompute_l7_indep.py`） | `【待终态】` | `【待终态】` | `【待终态】` | ≤ 64.12% | `【待终态】` |
| 3 | `P1` 具体性 | 全部 `MSG_*` | `【待终态】` | `【待终态】` | `【待终态】` | ≥ 93.82% | `【待终态】` |
| 4 | `F-2_content_drift.drift_rate`（=`F-2'`） | 相邻消息对，n=`【待终态】` | `【待终态】` | `【待终态】` | `【待终态】` | ≤ 75.09% | `【待终态】` |
| 5 | `L-15 restate_strong` | 全部 `MSG_*` | `【待终态】` | `【待终态】` | `【待终态】` | ≤ 4.51% | `【待终态】` |
| 次级 | `len_p50`(excl) | `L-1_len.excl_paren.p50` | `【待终态】` | `【待终态】` | `【待终态】` | ≤ 57.2 | 只记录 |
| 次级 | 结构 `n_msgs / n_threads / turns_A_p50` | — | `【待终态】` | `【待终态】` | `【待终态】` | 510/169/2 ±5% | 只记录 |
| 次级 | `L-3` 含括号块率 | 全部 `MSG_*` | `【待终态】` | `【待终态】` | `【待终态】` | 不得再砍旁白（D12-E 68.82%） | 只记录 |
| 次级 | `L-6` 完全重复 | 全部 `MSG_*` | `【待终态】` | `【待终态】` | `【待终态】` | 不得显著回升（D12-E 0.78%） | 只记录 |

> **Δ 口径写死**：`Δpp = (D12-F 率 − T1 率) × 100`，负值 = 下降。**不写"降 N 倍"**（本轮已发生 pp/倍混写事故，见 `v2/refs/batch-hosting-runbook.md` §3.103.4）；若确要写倍数，必须同时给「a/b 计数比」。

## 4. 判据对照

### 4.1 机制闸（**先判；未过只能写"机制未生效"**）

| 闸 | 阈值 | 实测 | 结果 |
|---|---|---|---|
| **M1** `ctx.d12f.m == 3` 命中率 | = 100% | `【待终态】` | `【待终态】` |
| **M3** 非全同分样本中 `picked == argmin` | = 100% | `【待终态】`（分子/分母同时给） | `【待终态】` |
| **M4** 候选可分性 | ≥ 25% | **A/B 双分母同时报**：A（分母=全部带 `ctx.d12f` 的 `MSG_*`）= `【待终态】`；B（分母=剔除 `picked is None`）= `【待终态】` | `【待终态】` |
| M0（Leader 前置闸，非预登记） | 真调用率 ≥ 50% | `【待终态】`（`cached=False` 的 `LLM_CALL` / 全部 `LLM_CALL`） | `【待终态】` |

> **M4 裁定规则（已锁，不许择一）**：两种分母**都报**；**两口径裁决一致**（同为达标或同为不达标）才算通过；**不一致 ⇒ 判「口径不明 · 不可判」**，禁止挑一个有利分母。依据 `v2/refs/batch-hosting-runbook.md` §3.103.1/§3.103.2。
> **披露既有事实（防误读）**：D12-E 的可分性应是 **82/510 = 16.0784%**；旧文档 `79/497 = 15.90%` 系**把中途快照当终态**（497 在终态日志不可达），**不作为"第二种口径"**。

### 4.2 效果五条（同时满足才算「有效」）

`【待终态】` —— 逐条填「达标 / 不达标 + 差多少 pp」，**一条也不许合并措辞**。

### 4.3 代价闸

| 闸 | 内容 | 阈值 | 实测 | 结果 |
|---|---|---|---|---|
| C-1 | `P1` 不显著下降 | ≥ 93.82% | `【待终态】` | `【待终态】` |
| C-2 | `F-2'` 不恶化（承接未被牺牲） | ≤ 75.09% | `【待终态】` | `【待终态】` |
| C-3 | `L-15 strong` 不恶化 | ≤ 4.51% | `【待终态】` | `【待终态】` |
| C-4 | `L-6` 不完全重复回升 | 不得显著回升 | `【待终态】` | `【待终态】` |

## 5. 副作用与成本

| 项 | 值 | 取法 |
|---|---|---|
| 墙钟 / `duration_sec` | `【待终态】` | `meta.json` |
| `calls` / `cached` / **网络调用数** | `【待终态】` | `python3 -m obs llm-cost --log <run.jsonl> --require-provider openai_compat` |
| `by_purpose.dialogue`（应为 510×3 = 1530） | `【待终态】` | 同上 |
| **缓存命中率**（对话） | `【待终态】`（**必须披露**） | 同上 |
| `degraded` / `provider_guard` | `【待终态】` | 同上 |
| `tokens_in/out`（与 T1 对比） | `【待终态】` | 同上 |
| `END` / `run_batch.rc` 是否落盘 | `【待终态】**必须披露缺哪个**` | `ls <run_dir>/` |

## 6. 反事实与局限（预登记 §5 原文照录，跑前写死）

在 **M1/M3/M4 全过** 的前提下：

| 观察到 | 判定词 |
|---|---|
| `L-7` 双口径达阈值 且 四条代价闸守住 | **有效** |
| `L-7` 达标但 `P1` 掉 >5pp | **无效（拿具体性换去重）** |
| `L-7` 达标但 `F-2'` 漂 >5pp | **无效（拿承接换去重）** |
| `L-7` 仍差 0–2pp 未达 | **无效（效果不足）** —— 但须写清"距门槛还差多少、可分性是否真的上去了" |
| 结构超 ±5% | **作废**（不是单变量） |
| M1/M3/M4 任一未达 | **机制未生效** |

**边界的三种"带"必须分列，不得混成一句「无带」**：

| # | 对象 | 性质 | 本报告怎么写 |
|---|---|---|---|
| ① | **B2 噪声带**（若引用） | 统计重采样带（B=2000, seed=42） | 只读 **HEAD blob**：`git show HEAD:v2/evidence/d3_noiseband_bootstrap.json`；**禁用工作区版本**（该文件工作区为他人历史脏 ` M`），更禁用 `denom_341` 旧版 |
| ② | **结构 `510/169/2 ±5%`** | **同构要求**，不是统计带 | 直接与 T1 逐项比，**不需要 bootstrap**；超出 ±5% ⇒ 预登记 §5 判「作废（不是单变量）」 |
| ③ | **`L-15` / `F-2_content_drift` 的阈值** | **点估计阈值、无带**（预登记 §7 已写死） | 写「点估计阈值，**未做显著性检验**」，**不借用**他项带宽 |

**边界（预登记 §7 照录 + 本报告补充）**：
1. 单 seed / 单规模 / 单树；本臂改的是**候选 prompt**（不是择优规则）；
2. `L-15`、`F-2_content_drift` **无 bootstrap 带** ⇒ 点估计阈值，**必须写「未做显著性检验」**；
3. **不得**写"对话更自然"；无人类评证据；
4. 若 M4（≥25%）达标但 `L-7` 仍不达 ⇒ 说明"选中最优候选"本身天花板不高，下一轮应考虑 M=5 或换评判口径（预登记已先写死，防事后找理由）；
5. 【本报告补充】D12-E 的 44.9% 缓存命中与「raw8 两实现分歧」属**参考臂**缺陷，**不得**用它替 D12-F 解释任何读数；D12-F 若出现缓存命中，须单列披露并给命中来源。

## 7. 附录 · 复算命令模板（收批后照抄执行，输出填回 §3/§4）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# ---- 0. 身份与收批闸 ----
RUN=.worktrees/d12f-diverse/v2/evidence/run_d12f_diverse_n16r60_seed42
git -C .worktrees/d12f-diverse rev-parse HEAD          # batch_code_sha
cat $RUN/meta.json | head -40
ls $RUN                                                # END / run_batch.rc 是否存在
sha256sum $RUN/run.jsonl

# ---- 1. 机制闸 M1/M3/M4（含 A/B 双分母 + M0） ----
python3 v2/evidence/d12f_gate_metrics.py \
  --run-jsonl $RUN/run.jsonl --ctx-key d12f --label D12F \
  --out-json v2/evidence/d12f_gate_metrics.json
# 交叉复核（D12-E 上验证过的独立片段）：非全同分 = len(set(scores))>1

# ---- 2. L-7 norm8 / L-6 / L-3 / len_p50 / F-2_content_drift ----
python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl \
  --out-json /tmp/d12f_t1_d5.json --out-md /tmp/d12f_t1_d5.md
python3 tools/d5/dialogue_metrics.py --log $RUN/run.jsonl \
  --out-json /tmp/d12f_arm_d5.json --out-md /tmp/d12f_arm_d5.md

# ---- 3. L-7 raw8（判定口径，单一实现，避免两实现分歧） ----
python3 v2/evidence/recompute_l7_indep.py --log v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl
python3 v2/evidence/recompute_l7_indep.py --log $RUN/run.jsonl

# ---- 4. P1 / 结构 / len_p50（冻结读数器） ----
python3 v2/evidence/d12c_metrics.py \
  --run T1=v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl \
  --run D12F=$RUN/run.jsonl --out-json v2/evidence/d12f_metrics_t1_arm.json

# ---- 5. L-15 restate_strong ----
python3 tools/d5/l15_restate_rate.py \
  --run T1=v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl \
  --run D12F=$RUN/run.jsonl --out-json /tmp/d12f_l15.json

# ---- 6. 真跑验真（门禁口径，不是跑批进程 rc） ----
cd code && python3 -m obs llm-cost --log "../$RUN/run.jsonl" --require-provider openai_compat; echo "llm-cost rc=$?"

# ---- 7. 截图（收批后现场拍，禁止复用旧图） ----
cd code
python3 frontend/tools/gen_threads.py --log ../$RUN/run.jsonl --meta ../$RUN/meta.json \
  --out frontend/sample/dialogue_r_d12f/threads.json --label run_d12f_diverse_n16r60_seed42
curl -s http://127.0.0.1:8848/sample/dialogue_r_d12f/threads.json | sha256sum
python3 frontend/tools/shot.py \
  --url "http://127.0.0.1:8848/dialogue.html?still=1&multi=0&min=0&data=sample/dialogue_r_d12f/threads.json" \
  --out ../v2/evidence/d12f_shots/d12f-chat-<runsha8>.png --width 1400 --height 900 --timeout 180
python3 frontend/tools/shot.py \
  --url "http://127.0.0.1:8848/dialogue.html?still=1&multi=0&min=0&view=rhythm&data=sample/dialogue_r_d12f/threads.json" \
  --out ../v2/evidence/d12f_shots/d12f-rhythm-<runsha8>.png --width 1300 --height 1050 --timeout 180
```

> 截图纪律：`render.log` 必须记 `RENDER_START` 时刻、`data_sha256_of_served_file`、`source.run_sha256`、`URL_PROVENANCE`（`shot.py` 不回显 `--url`，须事后补录并标注"事后补录"）；文件名带 `<runsha8>`；**旧图一律不得充当本轮证据**，确需引用须标来源批次与日期。
