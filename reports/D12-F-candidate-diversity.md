# D12-F · 候选结构多样化（在 D12-E 上补「可分性」这一步）——**终态报告**

> **终态声明（本版取代 2026-10-23 16:3x 的骨架版）**：本文件此前是「半成品 · 零读数骨架 · 任何引用无效」。**该状态已结束，此处显式撤回**——本版填入 D12-F 终态（T4）实测读数与逐条判据结论，可被引用。骨架版留下的**待终态占位符**已全部清零（机械检查计数为 0，本项不写命令字面量以免自指命中）。
>
> **作者**：report-author ｜ 终态落笔：**2026-10-23 20:38 (+0800)** ｜ 仓库根：`social-experiment`（`reports/D12-F-candidate-diversity.md`）
> **体例参照**：`reports/R22-d12d-t2-judge.md`、`reports/R21-scene-pair.md`
> **数据来源**：`v2/evidence/d12f_leader_terminal_check.md`（`9b568cb`）、`v2/evidence/d12f_result.md`（eval-researcher 独立复算）、`v2/evidence/d12f_metrics_t1_t4.json`、`v2/evidence/d12f_l15.json`、`v2/evidence/d12f_m4_gate_defect.md`、臂日志 `run.jsonl`（未入库，见 §0）。

## 0. 身份与口径（终态实取）

| 项 | 值 | 取法 / 证据 |
|---|---|---|
| **`batch_code_sha`（判定依据）** | **`1a8a3b4b7aa69a4232b916e1e4d3af036da5c1c7`**（`1a8a3b4`）@ `feat/d12f-diverse` | `.worktrees/d12f-diverse/v2/evidence/run_d12f_diverse_n16r60_seed42/meta.json.code_sha`；与 `v2/evidence/d12f_leader_terminal_check.md:74` 所记树一致 |
| 跑批后 worktree HEAD（**非**判定依据） | `ea25c35` | `git -C .worktrees/d12f-diverse rev-parse HEAD`（收批后被推进，**不得当作 code_sha**） |
| 本臂开关真值 | `LIFE_PROMPT_D12F_DIVERSE=3`（默认 `1`=关闭） | `switch_proof.md`；`meta.json` 侧记 |
| `prompt_fn_sha256`（候选 0 / 1 / 2） | 候选 0 = `effc14db…73f5`（= T1 安全锚 ✅）；候选 1、2 本轮**未落盘**（见 §4.1 观测缺口） | 预登记 §2 第 1 条；`d12f_result.md` §② 披露 2 |
| 批次目录 | `.worktrees/d12f-diverse/v2/evidence/run_d12f_diverse_n16r60_seed42/` | `ls` |
| `run.jsonl` | **117,384 行**，`sha256 = e24c54853688773550f0f5d72aa8c4da76f810b0c71696fb5353f0340a63cd50` | `wc -l`；`sha256sum`；与 `meta.json.run_sha256` 一致 |
| `run_batch.rc` / `run_batch.end` | **`0`** / `finished_at=2026-10-23T17:14:14+08:00, rc=0` | 目录内文件 |
| 预登记 | `v2/refs/D12F-prereg-candidate-diversity.md`，`sha256 = 42a57042614b4eb30454957ecb586412d54a1f5828a94efbfbd5c16304ef27f1` | `sha256sum`；跑前立此存照 2026-10-23 14:30 |
| 本报告落笔基准 HEAD（**文档身份，非代码身份**） | `5282032` | `git rev-parse HEAD` |

> ⚠ **`run.jsonl` 未入库**：主树 `v2/evidence/` 下**没有** `run_d12f_diverse_n16r60_seed42/` 目录，日志只在 worktree ⇒ 与本报告相关的原始日志**不可从仓库直接复算**（与 CYCLE-10 §3.2 G-1 的 D12-E 同型缺口）。引用本报告数字时请以下列已入库件为准：`d12f_metrics_t1_t4.json`、`d12f_l15.json`、`d12f_result.md`、`d12f_leader_terminal_check.md`；缺口已进 CYCLE-11 Q-7。

> **三组关系（不许混）**：
> - **T1 = 干净基线**（`v2/evidence/run_d12c_on_n16r60_seed42`，仅 `LIFE_PROMPT_D12C_SPECIFIC=1`）⇒ 本报告 §3 的 Δpp 一律以 T1 为基线；
> - **D12-E = 污染参考**（best-of-3，缓存命中 44.9%）⇒ 不作效果基线、不出 Δ；
> - **D12-F = 本臂**（候选结构多样化，叠在 D12-E 的择优机制上）；**D12-G = 同维度后续臂**（§7）。

## 1. 阈值原文逐字引用块（机械对照）

| # | 预登记原文（逐字） | 文件:行号 | 本报告实际使用 | 一致? |
|---|---|---|---|---|
| M1 | 「**M1** `ctx.d12f.m=3` 命中率 \| **= 100%** \| 接线」 | `v2/refs/D12F-prereg-candidate-diversity.md:43` | 510/510 = 100% | ✅ |
| M3 | 「**M3** 非全同分样本中 `picked==argmin` \| **= 100%** \| 择优逻辑正确性」 | 同上 `:44` | 110/110 = 100% | ✅ |
| M4 | 「**M4（本臂新增）** **候选可分性**（非全同分样本占比） \| **≥ 25%**（D12-E 实测 15.9%） \| **多样化必须真的提高可分性**，否则等于没做」 | 同上 `:45` | **110/510 = 21.57%**（A/B 双分母同值） | ✅（口径见 §4.1） |
| 判据1 | 「1 \| **`L-7` norm8** \| **≤ 55.10%** \| 55.88%（差 0.78pp）」 | 同上 `:53` | 52.55%（268/510） | ✅ |
| 判据2 | 「2 \| **`L-7` raw8** \| **≤ 64.12%** \| 待 eval 口径复算」 | 同上 `:54` | 65.10%（332/510，判定口径 `recompute_l7_indep.py`） | ✅ |
| 判据3 | 「3 \| **`P1`** \| **≥ 93.82%** \| 99.02%」 | 同上 `:55` | 99.61% | ✅ |
| 判据4 | 「4 \| **`F-2'`（= `F-2_content_drift.drift_rate`，仅 jaccard<0.10）** \| **≤ 75.09%** \| 73.61%」 | 同上 `:56` | 71.26% | ✅ |
| 判据5 | 「5 \| **`L-15 restate_strong`** \| **≤ 4.51%** \| 4.12%」 | 同上 `:57` | 3.73% | ✅ |
| 口径正名 | 「本臂的『内容漂移』判据**只能用 `F-2_content_drift.drift_rate`（即 `F-2'`）**…D5 里另有旧键 `F-2_topic_drift`…`status = LEGACY_DEAD_RULER`、**结构性恒 0**，误用会得到 `0%→0%` 的**假 PASS**」 | 同上 `:59` | 全文只写 `F-2'`；凡提 `F-2_topic_drift` 必标 `LEGACY_DEAD_RULER` | ✅（写作纪律） |
| 次级 | 「**次级（只记录）**：`len_p50`(excl) ≤57.2；结构 510/169/2 ±5%；`L-3` 含括号块率（D12-E 为 68.82%，**本臂不得再砍旁白**）；`L-6`（D12-E 已 0.78%，**不得显著回升**）」 | 同上 `:61` | 54 / 510/169/2 / **60.59%（再降 8.23pp）** / 0.78% | ✅（`L-3` 见 §5 代价） |

### 1.1 判据实现的钉死（预登记未指定实现，由本报告钉死）

- `L-7` 判定用 `v2/evidence/recompute_l7_indep.py`，`sha256 = ae50620d3b9bdd3add9d81cdd47186b87936d15a56eca58d76dbd44686b952f0`（raw8 与 norm8 同脚本输出，排除口径二次分叉）；**不使用** leader 临时实现（基线 67.84%），该值仅作交叉参考。
- `L-3` 含括号块率唯一实现 = `tools/d5/dialogue_metrics.py:990` `L-3_paren_block_any`（**不等于** `v2/evidence/d12c_metrics.py` 的 `paren_rate`，后者是「括号起头率」；见 CYCLE-11 §3.4 撤回登记）。
- `PS1/F-2'/len_p50/结构` 用冻结读数器 `v2/evidence/d12c_metrics.py`，`sha256 = c41cb5aca03c9499fc47047d5acaeba8f4b33bef5298b69556b15d3da290ab58`；`L-15` 用 `tools/d5/l15_restate_rate.py`（`02d1299f…`）。

## 2. 结论先行

> ### 判定：**机制未生效**（按预登记 §3：M4 21.57% < 25%；判词取自预登记五档，不软化、不改写为「部分有效」）
>
> **一句话理由**：M4 候选可分性 **110/510 = 21.57% < 25%** 闸线，按预登记只能判「机制未生效」；**不因**「`L-7` norm8 已达标」「只差 3.43pp」「其余四项全过」**改判**。
>
> **同屏必写的第二句（不许省略、不许调和）**：「该闸受『三候选 `scores` 全 0 必然同分』的天花板限制——此时哪怕候选文本差异巨大也不可分；机制本身的直接证据是：`L-7` norm8 **65.10%→52.55%（−12.55pp，首次达标）**、`scores` 三列均值 **2.022 vs 0.369/0.378（约 1/5.5）**、argmin **110/110 零违例**。」
>
> **禁止软化**：差 0.01pp 也是不达标；不得写「接近达标」「基本达成」「差一点就成」。

## 3. 读数表（T1 干净基线 → D12-F 本臂）

| # | 指标 | 口径 / 分母 | T1 | **D12-F（T4）** | **Δpp** | 阈值 | 判读 |
|---|---|---|---|---|---|---|---|
| 1 | `L-7` norm8 | 全部 `MSG_*`，n=510 | 65.10%（332/510） | **52.55%（268/510）** | **−12.55** | ≤ 55.10% | **达标** |
| 2 | `L-7` raw8 | 同上（`recompute_l7_indep.py`） | 74.12%（378/510） | **65.10%（332/510）** | **−9.02** | ≤ 64.12% | **未达标（差 0.98pp）** |
| 3 | `P1` 具体性 | 全部 `MSG_*` | 98.82% | **99.61%** | +0.79 | ≥ 93.82% | 达标 |
| 4 | `F-2'`（`F-2_content_drift.drift_rate`） | 相邻消息对，n=341 | 70.09% | **71.26%** | +1.17 | ≤ 75.09% | 达标 |
| 5 | `L-15 restate_strong` | 全部 `MSG_*` | 4.51% | **3.73%** | −0.78 | ≤ 4.51% | 达标 |
| 次级 | `len_p50`(excl) | `L-1_len.excl_paren.p50` | 52 | **54** | +2 | ≤ 57.2 | 只记录（+3.8%，未破线） |
| 次级 | 结构 `n_msgs / n_threads / turns_A_p50` | — | 510 / 169 / 2 | **510 / 169 / 2** | 0 / 0 / 0 | ±5% | 只记录（全等） |
| 次级 | `L-3` 含括号块率 | `L-3_paren_block_any` | 66.27%（338/510） | **60.59%（309/510）** | **−5.68** | D12-E 68.82%，「不得再砍旁白」 | 只记录（**旁白又被砍 8.23pp（对 D12-E）**，见 §5） |
| 次级 | `L-6` 完全重复 | 全部 `MSG_*` | — | **0.78%（4/510）** | — | 不得显著回升 | 只记录（保持 D12-E 水平；T1 值未取） |

> **Δ 口径写死**：`Δpp = (T4 率 − T1 率) × 100`，负值 = 下降。**不写「降 N 倍」**。
> **bootstrap CI**（预登记未要求，`d12f_result.md` §④ 补充）：判据 1 CI **[−18.43, −6.27]**（不含 0）、判据 2 CI **[−14.31, −3.33]**（不含 0）、`P1` CI [−0.20, +1.77]（含 0）；`F-2'` 与 `L-15` **无 CI（点估计阈值，未做显著性检验）**。

## 4. 判据对照

### 4.1 机制闸（先判；未过只能写「机制未生效」）

| 闸 | 阈值 | 实测 | 结果 |
|---|---|---|---|
| **M1** `ctx.d12f.m == 3` 命中率 | = 100% | **510/510 = 100%** | **PASS** |
| **M3** 非全同分样本中 `picked == argmin` | = 100% | **110/110 = 100%**（零违例） | **PASS** |
| **M4** 候选可分性 | ≥ 25% | **A（分母 = 全部带 `ctx.d12f` 的 `MSG_*`）= 110/510 = 21.57%**；**B（剔除 `picked is None`）= 同 A = 21.57%**（`picked_none_count = 0`） | **未达标（双分母裁决一致）** |
| M0（Leader 前置闸，非预登记） | 真调用率 ≥ 50% | 全体 **2,404/3,898 = 61.67%**（`calls − cached`，T1 为 1,405/2,878 = 48.82%）；`dialogue` purpose 级 **1,461/1,530 = 95.49%** | **PASS**（两种分母都过） |

> **M4 裁定规则（不许择一）**：两种分母都报，两口径裁决一致才算通过；不一致 ⇒ 判「口径不明 · 不可判」。本臂两口径同为 21.57% ⇒ 不存在择一问题。
> **M4 是坏闸（测量缺陷，不是机制失败）**：`v2/evidence/d12f_m4_gate_defect.md` 证明它测的是「三候选 `scores` 是否全相同」，而三条候选都与近期台词无 8-gram 交集时（`scores` 全 0）**必然同分**。⇒ 本臂判定词「机制未生效」**不得被引用为「候选结构多样化无效」**。
> **观测缺口（本臂，已修复于下一臂）**：`ctx.d12f` 只含 `{group, m, picked, scores}`，**未落候选文本 / `candidate_shas`** ⇒ 「候选两两 8-gram Jaccard 距离」**本轮不可补算**（D12-G 已补 `candidate_shas` 与 `cand_jaccard_dist_mean`）。

### 4.2 效果五条（同时满足才算「有效」）

逐条结论，不合并措辞：

1. `L-7` norm8 **达标**（52.55% ≤ 55.10%，−12.55pp，CI 不含 0）；
2. `L-7` raw8 **未达标**（65.10% > 64.12%，**差 0.98pp**）；
3. `P1` **达标**（99.61% ≥ 93.82%）；
4. `F-2'` **达标**（71.26% ≤ 75.09%，无 CI）；
5. `L-15 strong` **达标**（3.73% ≤ 4.51%，无 CI）。

⇒ **5 条中 4 条达标、1 条未达标（差 0.98pp）⇒ 效果判据不成立**；但因机制闸 M4 先未过，按预登记 §5 最终判词取「**机制未生效**」，不取「无效（效果不足）」（后者是「M1/M3/M4 全过」前提下的档）。

### 4.3 代价闸

| 闸 | 内容 | 阈值 | 实测 | 结果 |
|---|---|---|---|---|
| C-1 | `P1` 不显著下降 | ≥ 93.82% | 99.61% | 守住 |
| C-2 | `F-2'` 不恶化 | ≤ 75.09% | 71.26% | 守住 |
| C-3 | `L-15 strong` 不恶化 | ≤ 4.51% | 3.73% | 守住 |
| C-4 | `L-6` 不完全重复回升 | 不得显著回升 | 0.78% | 守住（保持 D12-E 水平） |
| C-5 | **`L-3` 含括号块率（旁白）** | D12-E 68.82%，「不得再砍旁白」 | **60.59%（−8.23pp）** | **代价发生**：旁白继续被砍（预登记为「只记录」，未设硬阈值） |

## 5. 副作用与成本

| 项 | 值 | 取法 |
|---|---|---|
| 墙钟 / `duration_sec` | 4,515 s（75.2 min） | `meta.json`；`run_batch.end` 15:58:59→17:14:14 |
| `calls` / `cached` / **网络调用** | 3,898 / 1,494 / **2,404** | `python3 -m obs llm-cost … --require-provider openai_compat` |
| `by_purpose.dialogue` | **1,530 = 510×3**（cached 69 ⇒ 缓存 4.5%） | 同上 |
| `degraded` / `provider_guard` | 0 / `ok=true`、`problems=[]` | 同上 |
| `tokens_in/out` | 481,867 + 349,942 = **838,471**（T1 405,955，**+106.5%**） | 同上 |
| `END` / `run_batch.rc` 是否落盘 | **均落盘**（rc=`0`）；首版曾因 trap 用相对 `$OUT_DIR` 落到 `code/v2/evidence/…`，收尾首轮原样复制回并删残留，trap 修为 `${OUT_ABS:-…}`（`f0ae3a3`） | 目录 `ls`；`d12f_result.md` §②-披露 1 |
| 证据入库状态 | `run.jsonl` **未入库**；`meta.json` / `llm_cost.txt` / `run_batch.rc` / `run_batch.end` / `switch_proof.md` **亦未入主树**（只在 worktree） | §0 |

## 6. 反事实与局限

反事实表（预登记 §5，跑前写死；本报告只做对照，不改阈值）：

| 观察到 | 判定词 | 本臂命中 |
|---|---|---|
| `L-7` 双口径达阈值 且 四条代价闸守住 | 有效 | 否（raw8 差 0.98pp） |
| `L-7` 达标但 `P1` 掉 >5pp | 无效（拿具体性换去重） | 否 |
| `L-7` 达标但 `F-2'` 漂 >5pp | 无效（拿承接换去重） | 否 |
| `L-7` 仍差 0–2pp 未达 | 无效（效果不足） | **形式上命中（0.98pp）**，但前提「M1/M3/M4 全过」不成立 |
| 结构超 ±5% | 作废 | 否（全等） |
| **M1/M3/M4 任一未达** | **机制未生效** | **是（M4 21.57%）** |

**边界**：
1. 单 seed（42）/ 单规模（n16×r60，510 条）/ 单树（`feat/d12f-diverse@1a8a3b4`）；外推需重测；
2. `M4` 是受「全 0 天花板」约束的坏闸 ⇒ 判词「机制未生效」**不可引用为「候选结构多样化无效」**；
3. **无人类评证据** ⇒ 不得写「对话更自然」；本报告不作此判断；
4. `L-15`、`F-2'` **无 bootstrap 带 ⇒ 点估计阈值、未做显著性检验**；
5. 观测缺口：`ctx.d12f` 无候选文本 / `candidate_shas` ⇒ 候选两两差异**不可事后复算**；
6. **无截图**：本臂无 `d12f_shots/`，CYCLE-10 Q-6 已由 Leader 裁为「不补拍」；**不用其他批次的图冒充本臂**。渲染命令（若日后解禁，须先让臂日志入库）：
   ```bash
   D=.worktrees/d12f-diverse/v2/evidence/run_d12f_diverse_n16r60_seed42
   python3 code/frontend/tools/gen_threads.py --log $D/run.jsonl --meta $D/meta.json \
     --out code/frontend/sample/dialogue_d12f/threads.json --require-complete
   python3 code/frontend/tools/shot.py \
     --url "http://127.0.0.1:8848/dialogue.html?still=1&multi=1&min=0&sort=turns&data=sample/dialogue_d12f/threads.json" \
     --out v2/evidence/d12f_shots/d12f-chat-<runsha8>.png --width 1400 --height 900 --retry-blank 2
   ```
   （`<runsha8>` = `e24c5485`）
7. `L-15` 只测片段复用，不等于「逻辑」；`L-6`（整条逐字节）与 `L-15`（片段级）不可互代。

## 7. D12-F 与 D12-G：同一维度的两条臂（关系声明）

| 项 | **D12-F（T4）** | **D12-G（T5）** |
|---|---|---|
| 同一维度 | 候选结构多样化（best-of-3 择优的候选 prompt 多样化） | **同一维度**，D12-F 的三处修正版 |
| 相对上一臂的改动 | 在 D12-E 上新增候选 1/2（开口称呼 / 动作自述） | ① 候选 2 换成「收束要短」；② `ctx` 加 `candidate_shas`；③ **M4 废弃 → M5 `cand_jaccard_dist_mean ≥0.05`** |
| 基线 | T1 | **T4（= D12-F 终态读数）**，不是 T1 |
| 机制闸 | M1/M3 PASS，**M4 未达标（21.57% < 25%）** | M1/M3/M5 **全 PASS** |
| 效果 | 4/5 达标，`L-7` raw8 差 0.98pp ⇒ 效果判据不成立 | 4/6 达标，`L-7` 双口径未达（差 6.08 / 5.49pp） ⇒ 效果未达标 |
| 判词 | **机制未生效**（M4） | **机制生效、效果未达标**（落入「无效（效果不足）」档，档位外推） |
| 关系结论 | —— | **D12-G 不是新维度，而是把 D12-F 的「坏闸」换成可算的 M5、并把候选 2 换成另一个结构位**；所以 D12-G 的机制 PASS 只说明「闸变好了、接线对了」，**不构成对 D12-F「机制未生效」的翻案**，两臂判词各自独立成立 |

**一句话**：`D12-F` 与 `D12-G` 是**同一维度的两条臂**；D12-F 的「机制未生效」是**闸的失败**（M4 坏闸 + 未落候选文本），D12-G 的「效果未达标」是**效果层的失败**（候选确实多样、但没换来实际发言去重）。**两者不可互相替代、不可合并成一个结论，也不得用 D12-G 的读数去改写 D12-F 的判词。**

## 附录 · 复算命令

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
T1=v2/evidence/run_d12c_on_n16r60_seed42
T4=.worktrees/d12f-diverse/v2/evidence/run_d12f_diverse_n16r60_seed42

# 身份
git -C .worktrees/d12f-diverse rev-parse HEAD       # ea25c35（非 code_sha）
sha256sum $T4/run.jsonl                             # 期望 e24c5485…cd50
wc -l $T4/run.jsonl                                 # 期望 117384

# P1 / 结构 / len_p50 / paren_rate（冻结读数器）
python3 v2/evidence/d12c_metrics.py --run T1=$T1/run.jsonl --run T4=$T4/run.jsonl \
  --out-json v2/evidence/d12f_metrics_t1_t4.json

# L-7 双口径 / F-2' / L-3 / L-6（d5）
python3 tools/d5/dialogue_metrics.py --log $T1/run.jsonl --meta $T1/meta.json --out-json /tmp/f1.json
python3 tools/d5/dialogue_metrics.py --log $T4/run.jsonl --meta $T4/meta.json --out-json /tmp/f4.json

# L-15
python3 tools/d5/l15_restate_rate.py --run T1=$T1/run.jsonl --run T4=$T4/run.jsonl \
  --out-json v2/evidence/d12f_l15.json

# 机制闸 M1/M3/M4（A/B 双分母）
python3 v2/evidence/d12f_gate_metrics.py --run-jsonl $T4/run.jsonl --ctx-key d12f --label D12F

# 验真
cd code && python3 -m obs llm-cost --log "../$T4/run.jsonl" --require-provider openai_compat; echo rc=$?
```
