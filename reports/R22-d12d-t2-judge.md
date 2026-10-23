# R22 · D12-D T2 判读：D12-C 的模板化代价到底在旁白还是正文

> 报告编号：**R22** ｜ 周期：**CYCLE-08** ｜ 撰写：`metrics-judge`（判读与复算专家）
> 撰写时刻：**2026-10-23 10:14 (+0800)**（HEAD 当时 = `635740f`），定稿 **10:21 (+0800)**（HEAD = **`4d8a583`**，期间 `ddc5b4e` / `4d8a583` 两个 commit 由其他成员落地）
> 报告绑定的仓库 HEAD（**定稿时刻 `git rev-parse HEAD`**）：**`4d8a5832f03056ea81e513c8d4c3398bd58c65b8`**（`master`）
> 被判批次代码树：**`feat/d12c-dedup@5ca515d`**（parent `a977cb0`）——与被弹报告 HEAD **不是同一个 commit**，两者关系见 §八-D4
> 预登记：`v2/refs/D12D-prereg-dedup-on-detail.md`（2026-10-23 08:30 立此存照，跑前写死判据与阈值）

---

## 一、结论先行

**1. 判定词：「机制未生效」。** T2（D12-C + D12-D）相对 T1（仅 D12-C）的 `L-7` 8-gram 撞车率只降 **0.588pp**（norm8 65.098% → 64.510%）、raw8 只降 **0.196pp**（74.118% → 73.922%），**远低于预登记的「↓≥5pp」机制闸**；两个口径的 95% CI 都跨 0（norm8 `[−6.43, +5.26]`、raw8 `[−5.57, +5.18]`）。按预登记 §5 反事实表最后一行，**判「机制未生效」，不得判「无效」**；同时主判据 L-7 双门槛（≤55.10% / ≤64.12%）**均未达**，所以**更不能判「有效」**。

**2. 是否可判：可判（判的就是「机制未生效」这一档）；但「D12-D 这条路是否走得通」在本规模下不可判。** 因为指令是否被模型采纳这一前提没有成立，主判据的落空不能归因于「这条路走不通」。

**3. 本轮真正要回答的问题——「D12-C 降下来的是旁白还是模板」——答案是「不是旁白」：**
- T2 把旁白（括号块）率砍掉 **16.078pp**（66.27% → 50.20%），但**去掉括号后同算法重算**的 `L7_noparen` **反而升了 0.99pp**（47.25% → 48.24%），原口径 `L-7` 几乎不动。
- 若 L-7 的代价主体是旁白，砍掉 16pp 旁白后 L-7 应显著下降；实测相反 ⇒ **模板化代价主要落在正文层（句式开头 + 具体物复用）**，D12-D 的两行指令**没有压住它**。
- 归因四格（**非判据**）：**「换开头」反向 +5.49pp**（开头×含具体物 39.80% → 45.29%）、**「换新物」弱生效 −4.51pp**（正文×含具体物 45.88% → 41.37%），两股力量互相抵消 ⇒ 净持平。
- 但「+5.49pp」**不等于**「指令没被采纳」：另有一个**待验假设 H1**——模型把开头换成了**另一套同样集中**的句式（`把…往…上一…` 开头 13.14% → 15.49%，开头 shingle 种类 343 → 331 反降），本轮证据**倾向于但不足以证实**它，见 §4.3。

**4. 代价与副作用同屏：** P1 具体性基本保住（98.82% → 98.63%，仍在 ≥93.82% 线上）；P2 第三方 −2.54pp；`len_p50`（excl_paren）52 → 53（+1.92%，未超 ≤57.2）；结构三项 510 / 169 / 2 **零变化**。

---

## 二、臂设计与验真（先验真，再读数）

### 2.1 三态与单变量

| 态 | env | `prompt_fn_sha256` | 日志 |
|---|---|---|---|
| T0 基线 | 无 | `5cf08593…93f7`（与 D12-C 的 T0 逐字相等 ✅） | `run_d12c_off_n16r60_seed42` |
| T1 = D12-C | `LIFE_PROMPT_D12C_SPECIFIC=1` | `effc14db…d73f5`（逐字复现 ✅） | `run_d12c_on_n16r60_seed42` |
| **T2 = D12-C+D** | `LIFE_PROMPT_D12C_SPECIFIC=1` + `LIFE_PROMPT_D12C_DEDUP=1` | **`ca61423c…e51cf`（≠ T1 ✅）** | `run_d12d_on_n16r60_seed42` |

- 单变量证明：`git diff --stat a977cb0 feat/d12c-dedup` → **仅** `code/life/agent.py(+21/−2)`、`tools/d12d/render_d12d_prompt.py(+31)`，**未触碰机制层**；tip = `5ca515d`。
- env 真值取自 `/proc/3500780/environ`（`switch_proof.txt`），非人工填写。
- 三态 prompt sha 表见 `v2/evidence/d12d_wiring_proof.md`。

### 2.2 验真：`obs llm-cost`（唯一判决口径）

```
$ cd code && python3 -m obs llm-cost --log ../v2/evidence/run_d12d_on_n16r60_seed42/run.jsonl \
      --require-provider openai_compat
rc=0
{"engine_log":{"by_provider":{"openai_compat":2878},
  "by_purpose":{"dialogue":{"cached":49,"calls":510,"degraded":0,"thinking":0,
                            "tokens_in":125335,"tokens_out":27659},
                "importance":{"cached":1387,"calls":1523,"degraded":0},
                "judge":{"cached":0,"calls":668,"degraded":0,"thinking":668,
                         "tokens_in":88382,"tokens_out":215553},
                "negotiation":{"cached":34,"calls":49,"degraded":0},
                "plan":{"cached":0,"calls":16,"degraded":0},
                "reflect":{"cached":4,"calls":112,"degraded":0}},
  "total":{"cached":1474,"calls":2878,"degraded":0,"thinking":668,
           "tokens_in":270017,"tokens_out":286666,"tokens_total":556683}},
 "provider_guard":{"by_provider":{"openai_compat":2878},"expected":"openai_compat",
                   "ok":true,"problems":[]}}
```

原文见 `v2/evidence/d12d_t2_judge/llm_cost.txt`。**rc=0、`by_provider` 只有 `openai_compat`（2878 次）、`degraded=0`、`provider_guard.problems=[]`** ⇒ 判为**真跑**。

**口径注记（不把 admission 的 REJECTED 当失败）**：`dialogue_metrics.py` 对 T2 输出 `admission.verdict=REJECTED`，唯一失败项 `B-10_provider` 的 detail 是 `<empty>`——这是 **legacy manifest 没有 `provider` 字段**导致的结构性误判；同批 `B-19_provider_distribution`（providers 全为 `openai_compat`）、`B-20_model_no_mock`（models 仅 `DeepSeek-Flash`）、`B-12_degraded_ratio`（0.0）**均 PASS**，T1 的 `arm_state_check.txt` 也是 `PASS=6 / FAIL=0 / CANNOT-VERIFY=1`。故**真实验真以 `obs llm-cost` 为准**。

### 2.3 收批闸

| 检查 | 结果 |
|---|---|
| `END` | `rc=0` |
| `TURN_SEAL` | **60 条，覆盖 round 0..59，无缺轮** |
| 进程 | `batch.pid=3500780` 已退出 |
| 日志完整性 | 两次探针间尺寸不变（55,316,353 B），mtime `10:08:18`；`run.jsonl` sha256 `ad0c939f…44ca0` |

### 2.4 B2 噪声带（现算；**真源是脚本+语料，不是某个 json 快照**）

**真源（可复算的唯一依据）**：
- 脚本 `v2/evidence/d3_noiseband_bootstrap.py`，sha256 `d878ac64…2986`
- 语料 `v2/evidence/d3_annotated_corpus.jsonl`，sha256 `2d06c184…4954`
- 方法（脚本内写死）：B=2000、`random.Random(42)`、从 t300/t355 各按消息有放回重采样 `m=denom` 条，取 `rate_A−rate_B` 的 2.5%/97.5% 分位

**现算命令与结果**：

```bash
python3 v2/evidence/d3_noiseband_bootstrap.py --denom 510   --out v2/evidence/d12d_t2_judge/d3_noiseband_bootstrap_denom510.json
# == denom 510
#   L-2  narration_proxy   [-5.69, 5.69] width=11.37pp
#   L-8  agent_id_leak     [-5.49, 5.88] width=11.37pp
#   L-11 no_second_person  [-6.17, 5.86] width=12.03pp
#   L-7  8gram_shared      [-5.88, 5.88] width=11.76pp   ← 本报告用的带
#   K-1  cont_backref      [-3.73, 3.53] width=7.25pp
#   U1   template_opening  [-3.73, 3.53] width=7.25pp
```

- 复算产物：`v2/evidence/d12d_t2_judge/d3_noiseband_bootstrap_denom510.json`，sha256 **`3e920dddd0be2b798da0ebf7279e9af0a992e8124fc6b853eb6d6b36656cbde0`**
- 该 sha256 **与 CYCLE-07 §S05 记录的「工作区版 denom_510」逐字节一致** ⇒ 本报告用的是同一份带，且它是**确定性可复现**的。
- **分母核验**：T2 实测分母 **510 / 510**，与预登记 510 偏差 0%（≪10%）⇒ 按 §4.1(b) **无需按实际分母重跑**。

> **⚠ 真源 / 副本 / 默认输出位（三段式，必须同写，否则下一轮会踩）**
> 1. **内容真源＝`denom_510` 的输出内容本身**，其 sha256 = `3e920dddd0be2b798da0ebf7279e9af0a992e8124fc6b853eb6d6b36656cbde0`（即本报告判 L-7 用的那份带）。
> 2. **可复现副本**（本轮 `--out` 重建，**与 10:11 取数版逐字节一致**）：`v2/evidence/d12d_t2_judge/d3_noiseband_bootstrap_denom510.json`，sha256 同上。**引用带时指这个文件**。
> 3. **共享 `v2/evidence/d3_noiseband_bootstrap.json` 是「脚本默认输出位」，会被后跑者覆盖**：10:11 时它是 `denom_510`（sha `3e920ddd…`）；**10:11:52 被并发分析以 `--denom 341` 覆盖**（现 sha `2313c001…1f04`，键 `denom_341`，见 `4d8a583` 的 D12-E 记录）；HEAD 版（`cf7a8575…9ac`，自 `b21042b`）是 `denom_480 / 623 / 686`。**该默认输出位不可作跨时点真源引用。**
>
> ⇒ 因此：B2 带的**可复算性来自脚本**（`--denom 510`，B=2000/seed=42 写死），**不来自那个 json 的内容**；json 只是输出存档。文件被覆盖**不影响** `[−5.88, +5.88]pp` 的可复算性——本轮已用 `--out` 复原出**同 sha 副本**即为证明。长期约定：**每个 denom 独立文件，共享 JSON 只当默认输出位、不入判定引用**。

### 2.5 跨窗口批声明（按 CYCLE-07 §1.4 先例单列）

| 项 | 值 |
|---|---|
| 起跑 | **2026-10-23 09:24:36 (+0800)** |
| 收批 | **≈10:06 (+0800)**，`END rc=0` |
| 本轮报告窗口 | 以 **10:00** 划界 ⇒ **该批起跑早于窗口起点 35 分钟** |
| 结论 | **本批属「跨窗口批」**。引用时必须连同「起跑/收批时刻 + 窗口划界」一起写，避免下一轮把它当成「本窗口内起跑、可比速率」的批 |
| 处置 | 与 CYCLE-07 §1.4 的先例一致：**单列、不据此比较窗口间吞吐/速率**；读数本身不受影响（同树单变量成立、`switch_proof` 取自 `/proc/<PID>/environ`） |

---

## 三、证据表（每个数字都带取数方式）

同尺度：n=16 agents × 60 rounds，seed 42，两臂消息数 / 线程数完全相同（**510 / 169**），分母同为 510。

| # | 指标 | T1（D12-C） | T2（D12-C+D） | Δ(T2−T1) | 取数命令 → 文件 |
|---|---|---|---|---|---|
| 1 | **`L-7_dup_ngram8_rate`（norm8）** | 332/510 = **65.098%** | 329/510 = **64.510%** | **−0.588pp** | `python3 tools/d5/dialogue_metrics.py --log <run.jsonl> --meta <meta.json> --arm <T1|T2> --out-json …` → `d12d_t2_judge/t1_metrics.json` / `t2_metrics.json` |
| 2 | **`L-7` raw8** | 378/510 = **74.118%** | 377/510 = **73.922%** | **−0.196pp** | `python3 v2/evidence/recompute_l7_indep.py --log <run.jsonl> --tag <T1|T2>` → `t2_raw8_indep.txt` |
| 3 | **`P1_specificity_rate`** | **98.82%** | **98.63%** | −0.19pp | `python3 v2/evidence/d12c_metrics.py --run T1=… --run T2=… --out-json $E/arms_d12c_metrics.json` |
| 4 | **`P2_thirdparty_rate`** | **77.25%** | **74.71%** | −2.54pp | 同上 |
| 5 | **`len_p50`（excl_paren，正则上限 60）** | **52.0** | **53.0** | **+1.92%** | 同上（`PAREN = r"[（(][^）)]{0,60}[）)]"`） |
| 6 | **`L-6_dup_exact_rate`** | 9.608% | 9.804% | +0.196pp | `dialogue_metrics.py`（重复率**唯一引用口径**） |
| 7 | `L-3_paren_block_any`（观察项） | 66.274% | 50.196% | **−16.078pp** | `dialogue_metrics.py` |
| 8 | `L-2_narration_rate_proxy`（观察项） | 60.980% | 46.667% | −14.314pp | `dialogue_metrics.py` |
| 9 | `L7_noparen`（去括号反事实） | 47.25% | 48.24% | **+0.99pp** | `python3 tools/d12d/decompose_l7.py --run T1=… --run T2=…` → `l7_decompose.json` |
| 10 | 结构三项（msgs / threads / threads_p50） | 510 / 169 / 2 | 510 / 169 / 2 | **0** | `arms_d12c_metrics.json` |
| 11 | `llm`（calls / degraded / provider） | 2878 / 0 / openai_compat | 2878 / 0 / openai_compat | — | `t1_metrics.json` / `t2_metrics.json` 的 `llm` 块 |

**B2 带**：`[−5.88, +5.88]pp`（§2.4）。**判据落位**：主判据要求「达标即超带」（10pp > 5.88pp），机制闸的 5pp **落在带内**，只作方向判断、不得声明显著性（预登记 §4.1(b) 原文）。

**CI（Newcombe，本报告自算、仅辅助说明）**：norm8 Δ `[−6.43, +5.26]pp`，raw8 Δ `[−5.57, +5.18]pp`，**均含 0**。

---

## 四、模板化代价归因（两个维度分开读）

> **纪律**：以下归因**不是判据**。预登记只判 `L-7` / `P1` / 结构，未为归因格设任何阈值；归因只回答「为什么 L-7 不动」，**不能替代** §五的判定。

### 4.1 维度 A：旁白层 vs 正文层（`tools/d12d/decompose_l7.py`，已入库 `635740f`，自检与 D5 的 L-7 逐位相等）

| 项 | T1 | T2 | Δ |
|---|---|---|---|
| `L7_orig`（= D5 的 L-7 同算法） | 65.10% | 64.51% | −0.59pp |
| **`L7_noparen`（删掉全部括号块后重算）** | **47.25%** | **48.24%** | **+0.99pp** |
| 旁白率 `L-3_paren_block_any` | 66.27% | 50.20% | −16.08pp |
| dup 消息中含旁白者占比 | 65.36% | 47.72% | −17.64pp |

**读法**：旁白确实被大幅削减（含旁白的重复消息占比也降 17.64pp），但**去括号后的 L-7 不降反升**。⇒ **旁白不是 L-7 代价的主体**；T1 去掉括号仍有 **47.25%** 的正文层撞车，T2 是 **48.24%**。

### 4.2 维度 B：句式开头 vs 具体物复用（`v2/evidence/d12d_t2_judge/attribute_l7.py`，本判读新写的**非判据**脚本）

按「撞车 8-gram 在归一化正文中的起始位置 <4（对应预登记「前四个字」表述）」× 「该 8-gram 是否含 D12-C 冻结的具体物/数词词表」分四格：

| 格 | 含义 | T1 消息数(率) | T2 消息数(率) | Δ(pp) | 对应 D12-D 指令 |
|---|---|---|---|---|---|
| **A** | 开头 × 含具体物/数词 | 203 (39.80%) | **231 (45.29%)** | **+5.49** | 第 2 条「换开头」**未生效，且反向** |
| B | 开头 × 不含具体物 | 84 (16.47%) | 78 (15.29%) | −1.18 | 同上 |
| **C** | 正文 × 含具体物/数词 | 234 (45.88%) | **211 (41.37%)** | **−4.51** | 第 1 条「换新物」**方向对、幅度小** |
| D | 正文 × 不含具体物 | 203 (39.80%) | 206 (40.39%) | +0.59 | — |
| — | 撞车消息总数 | 332 | 329 | −3 条 | — |

辅助量：`distinct_shingles` C 格 **1231 → 936（−295）**、D 格 1367 → 1109（−258）、A 格 254 → 261、B 格 89 → 70。

> **口径提醒**：四格是**消息集合**、一条消息可落多格，**不可相加当分子**（T1 四格和 724 > 332；T2 726 > 329）。只看单格率的方向与幅度。
**「占比」口径（任务要求 3 的另一种读法，按撞车 shingle 与撞车消息分别给占比，仍**非判据**）**：

| 量 | T1 | T2 | Δ |
|---|---|---|---|
| 撞车 8-gram **种类总数** | 2901 | **2347** | **−554（−19.1%）** |
| 关键位置：仅开头撞 / 仅正文撞 / 两者都撞 的消息数 | 48 / 85 / 199 | 53 / 72 / 204 | +5 / −13 / +5 |
| **开头被撞**的消息占全部撞车消息的比例 | **74.40%** | **78.12%** | **+3.72pp** |
| **正文被撞**的消息占全部撞车消息的比例 | 85.54% | 83.89% | −1.65pp |

**分母（必须同写）**：上表两行「开头被撞 / 正文被撞」的**分母都是「全部撞车消息」**（T1 332 条、T2 329 条），**不是**全部 510 条消息；且一条撞车消息可同时被开头与正文各撞一次 ⇒ **两者不是互补关系，绝不能相加当 100%**（T1 74.40% + 85.54% = 159.94%，正因为有 199 条消息两处都撞）。若要看占全体消息的比例，请读上面四格表的 `rate_pct` 列（分母 510）。

读法：撞车 shingle 的**种类**减少了 19.1%（模型确实少用了不少固定串），但**被撞消息的比例结构更加偏向「开头」**（74.40% → 78.12%）⇒ 与「换开头反向」同向，也与 H1 一致。

**读法**：净效果是两股力量抵消——「换新物」在正文层拿到 −4.51pp（具体物 shingle 种类也少 295 个），「换开头」在开头层**反向** +5.49pp（且开头撞的是含具体物的 8-gram，说明开头句式与器物绑定得更紧）。合成后 L-7 持平。

### 4.3 待验假设 H1：「换开头」不是没被采纳，而是换成了**另一套同样集中**的开头（**派生分析，非预登记判据**）

「开头×含具体物 +5.49pp」这个数**必须**读作派生观察，**不能**直接写成「指令没被采纳」的既成结论。存在一个可证伪的替代解释：

> **H1**：D12-D 第 2 条「开口别用上一句的前四个字」让模型**换掉了个别旧开头，但换成了同一个新开头**——即「换开头」的净效果是**把开头撞车集中到一套新句式上**，而不是打散。

**支持 H1 的证据（本报告现算，`l7_attribution.json` 的 `head_concentration` / `opening_pattern_ba_wang_yi` 块）**：

| 量 | T1 | T2 | 方向 |
|---|---|---|---|
| 开头层撞车 shingle **种类数** | 343 | **331**（−12） | 种类**变少** ⇒ 不是「打散」，更像「重集中」 |
| 最热开头 8-gram 覆盖消息数 | 8（`手里那根半指宽的`） | **11**（`把火钳往砧子上一`） | 更集中 |
| top-5 开头 8-gram 覆盖消息数（占全部消息） | 23（4.51%） | **35（6.86%）** | **+2.35pp 集中度** |
| 以 **「把…往…上一…」** 开头的消息占比 | 67（13.14%） | 79（15.49%） | **+2.35pp** |

**这条证据的含义与边界**：
- 「把X往Y上一磕/杵/搁」是一套**可套用的动作句式**，器物（火钳/锄头/秤）换了、句式没换 —— 与「换新物弱生效、换开头反向」的读数**互相印证**。
- 但它**不能证明** H1 成立：最热开头也可能只是随机波动（单 seed、单规模，top-1 只有 8→11 条消息），且**没有**对「前四个字」做逐句的采纳率审计（需模型侧采样或人读）。**故 H1 记为待验假设，不是结论。**

**独立旁证（同一窗口内另一成员的不同口径，**不影响**本报告判定）**：`v2/evidence/d12d_result.md`（commit `ddc5b4e`，读数人 `eval-researcher`）用**全文**正则 `把.{1,8}往.{1,8}一` 得 **113/510 = 22.2% → 119/510 = 23.3%（+1.2pp，未降反升）**；本报告用的是**开头位置**（`^把…往…上一`，仅首 4 字内的开头撞车）得 **13.14% → 15.49%**。两者口径不同（全文 vs 开头、正则宽度不同）**不可直接相减**，但**方向一致、互相印证 H1**：换的是槽里的名词（火钳/药碾子/搪瓷缸…），不是句式骨架。

**可证伪方式（下一轮若选 (a) 或 (b) 必须带上）**：① 对「开头层」做**新/旧开头分类审计**（旧开头是否真的消失、新开头是否只增加一个模板）；② 加一条**只换前半句、保留具体物**的更窄试验（见 §八 候选 b）；③ 若 H1 成立，则「再加强去重指令」收益有限，方向应转 (c) 行为层。

### 4.4 两个维度与预登记判据的对应关系（避免读者混成一个）

| 维度 | 拆的是什么 | 对应预登记哪一条 | 是否参与判定 |
|---|---|---|---|
| A 旁白/正文 | L-7 的**来源层**（括号旁白 vs 正文） | 无直接判据；用于排除「L-7 降=砍旁白的算术效应」这一替代解释 | ❌ 不参与 |
| B 开头/具体物 | 正文层内部**撞的是什么**（句式开头 vs 器物/数词） | 无直接判据；对应 D12-D 两条指令各自的设计意图 | ❌ 不参与 |
| 判定 | `L-7` norm8/raw8、`P1`、结构三项 | §3 机制闸 + §4/§4.1 主判据 | ✅ **只有这一行判** |

---

## 五、判定表（逐条给通过/未通过 + 原文依据）

| 预登记条目 | 原文阈值 | T2 实测 | 判定 | 原文依据 |
|---|---|---|---|---|
| **机制闸 M1** | `L-7` 比 T1 **↓≥5pp** ⇒ ≤60.10%；raw8 同步 **↓≥5pp** ⇒ ≤69.12% | norm8 65.098→**64.510（↓0.588pp）**；raw8 74.118→**73.922（↓0.196pp）** | ❌ **未过闸** | §3「T2 比 T1 ↓≥5pp ⇒ ≤60.10%」+ §4.1(a) 双门槛表 |
| 口径方向一致性 | norm8 与 raw8 **方向必须一致** | 两者**都降** | ✅ 通过（无「口径分叉」） | §4.1(c) |
| 主判据 1-a（norm8） | **≤55.10%** | **64.510%**（高 9.41pp） | ❌ 未达 | §4 第 1 行 |
| 主判据 1-b（raw8） | **≤64.12%** | **73.922%**（高 9.80pp） | ❌ 未达 | §4.1(a) 表 |
| 主判据 2（P1） | **≥93.82%** | **98.63%**（优于线 4.81pp） | ✅ 达 | §4 第 2 行 |
| 次级：`len_p50` | 涨幅 ≤10%（≤57.2） | **53.0（+1.92%）** | ✅ 达 | §4「次级（只记录，不判定）」 |
| 次级：结构三项 | ±5% | 510 / 169 / 2 与 T1 完全一致 | ✅ 达 | 同上 |
| **反事实定档** | 「M1 未过闸（降<5pp）⇒ **机制未生效**（不得判无效）」 | M1 未过闸 | **判定词 = 机制未生效** | §5 表最后一行 |

**为什么不是「无效」**：预登记把「未过闸」单列一档，含义是**指令是否被采纳这个前提没有成立**，此时主判据落空不构成「这条路走不通」的证据。
**为什么也不是「有效」**：主判据 1 的两个口径都显著高于线（64.51 > 55.10、73.92 > 64.12）。

---

## 六、真实截图节（**两臂图像互异性已核验；截图不作效果证据，但可作「两臂数据源确实不同」的展示性佐证**）

渲染人 `shot-renderer`。清单与核验表的唯一来源是 `team-workspace/shots/index.md`（§0、§1、§2.1）；本报告只引用，不自行编造路径。**4/4 张 `SHOT OK`，`blank_retries=0/2`，两臂目录均未创建 `_blank_check_failed/`。**

### 6.1 四条全量清单（尺寸/字节为本报告 `ls -l` 实测复核）

| 文件 | 臂 | 视图 | 尺寸 | 字节 | 空白检测 | 渲染时刻(+0800) |
|---|---|---|---|---|---|---|
| `d12c_t1-chat-bd2df77f.png` | T1 | 对话流 | 1400×900 | 268,729 | ✅ `SHOT OK`，`blank_retries=0/2`，`max_color_frac=30.33%` | 10:04:15–10:04:20 |
| `d12c_t1-rhythm-bd2df77f.png` | T1 | 节律·串门 | 1300×1050 | 283,471 | ✅ `SHOT OK`，`max_color_frac=34.45%` | 10:04:21–10:04:22 |
| `d12d_t2-chat-ad0c939f.png` | T2 | 对话流 | 1400×900 | 268,972 | ✅ `SHOT OK`，`max_color_frac=30.33%` | 10:09:33–10:09:36 |
| `d12d_t2-rhythm-ad0c939f.png` | T2 | 节律·串门 | 1300×1050 | 284,491 | ✅ `SHOT OK`，`max_color_frac=34.45%` | 10:09:37–10:09:39 |

绝对路径前缀：
- T1：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/d12c_t1_shots/`
- T2：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/d12d_t2_shots/`

### 6.2 两臂互异性核验（`index.md` §2.1 提供，本报告 `md5sum` 实跑复核一致）

**(a) 四个 PNG 哈希两两互异**（同名视图跨臂也不同）：

| 文件 | md5 |
|---|---|
| `d12c_t1-chat-bd2df77f.png` | `dde9764f2e0d360f240c733b78e5f566` |
| `d12c_t1-rhythm-bd2df77f.png` | `3c7481d96ac9149d59b253b881f9eddc` |
| `d12d_t2-chat-ad0c939f.png` | `34aec98d0352ca193bb742ff6d48bc18` |
| `d12d_t2-rhythm-ad0c939f.png` | `e502be64a58b6138f55643fbd9a4af44` |

**(b) 文本侧**：两臂各 510 条台词**逐位置比对 0 条相同（差异率 100%）**；抽样可见连「第三方是谁」都不同（T1 `阿福` vs T2 `阿茂`）。

**(c) 数据源侧**：8848 服务返回的两份 `threads.json` sha256 不同，且各自 `source.run_sha256` 分别指向 `bd2df77f…96c87`（T1）与 `ad0c939f…44ca0`（T2）；本判读实算的 `run.jsonl` sha256 前 8 位与之**完全一致** ⇒ **两臂渲染没有串台**。

> `max_color_frac` 精确相同（chat 30.33% / rhythm 34.45%）是**版式与背景占比相同**（同页面、同视口、同布局、同为夜间场景主色）所致，已被上述三项独立证据排除「T2 实际渲染的是 T1 数据」。

### 6.3 证据等级与措辞边界（**必须照此引用**）

> 这 4 张图**不作效果证据**：不参与 P1 / P2 / L-7 任何判据，不能用于证明 T2 优于或劣于 T1。
> 但**也不能说截图无意义**：两臂图像互异性已核验（PNG md5 两两互异 + 510 条台词逐位置 0 相同 + 服务侧数据文件 sha 不同），因此它们可作为**「两臂数据源确实不同」的展示性佐证**，以及「两臂日志都能在 `dialogue.html` 上正常渲染、非空白、计数自洽（510 消息 / 169 线程）」的可展示性证据。

### 6.4 `render.log` 的引用限制（可复算性要求）

`shot.py` **不回显 `--url`**，两个 `render.log` 末尾的 `=== URL_PROVENANCE ===` 段是 **2026-10-23T10:13:37 事后补录**，日志内已明确标注「事后补录」并给出实际执行的 `--url` 原文与 `[data_sha256_of_served_file]` / `[source.run_sha256_in_that_file]`。
⇒ **引用 `render.log` 时必须注明该 URL 段是事后补录、不是原始同刻记录**；`RENDER_START` / `SHOT OK` / `rc=0` 的时间戳是原始记录，URL 归属以该补录段 + 服务侧 sha 校验为准。

## 七、复算命令节（读者照抄可复现）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment      # 仓根
E=v2/evidence/d12d_t2_judge
T1=v2/evidence/run_d12c_on_n16r60_seed42
T2=v2/evidence/run_d12d_on_n16r60_seed42
mkdir -p $E

# ① 收批闸
cat $T2/END                                  # 期望 rc=0
python3 -c "import json;p='$T2/run.jsonl';rs=[json.loads(l)['round'] for l in open(p) if '\"TURN_SEAL\"' in l];print(len(rs),min(rs),max(rs))"
                                             # 期望 60 0 59

# ② 验真（必须 cd code，仓根会 No module named obs）
cd code && python3 -m obs llm-cost --log ../$T2/run.jsonl --require-provider openai_compat; cd ..
                                             # 期望 rc=0 / 仅 openai_compat / degraded=0

# ③ B2 噪声带（以脚本为核心真源，写到自己的输出文件，避免覆盖他人快照）
sha256sum v2/evidence/d3_noiseband_bootstrap.py               # 期望 d878ac64…2986
sha256sum v2/evidence/d3_annotated_corpus.jsonl               # 期望 2d06c184…4954
python3 v2/evidence/d3_noiseband_bootstrap.py --denom 510 \
  --out $E/d3_noiseband_bootstrap_denom510.json               # 期望 L-7 [-5.88, 5.88]
sha256sum $E/d3_noiseband_bootstrap_denom510.json             # 期望 3e920ddd…cbde0

# ④ D5 全量指标（两臂各一次）
python3 tools/d5/dialogue_metrics.py --log $T1/run.jsonl --meta $T1/meta.json --arm T1 \
  --out-json $E/t1_metrics.json --out-md $E/t1_metrics.md
python3 tools/d5/dialogue_metrics.py --log $T2/run.jsonl --meta $T2/meta.json --arm T2 \
  --out-json $E/t2_metrics.json --out-md $E/t2_metrics.md

# ⑤ P1 / P2 / len_p50（冻结读数器，双跑同表）
python3 v2/evidence/d12c_metrics.py --run T1=$T1/run.jsonl --run T2=$T2/run.jsonl \
  --out-json $E/arms_d12c_metrics.json

# ⑥ raw8（判定口径，独立实现）
python3 v2/evidence/recompute_l7_indep.py --log $T1/run.jsonl --tag T1
python3 v2/evidence/recompute_l7_indep.py --log $T2/run.jsonl --tag T2

# ⑦ 归因：旁白/正文（已入库工具）+ 开头/具体物（本判读脚本，非判据）
python3 tools/d12d/decompose_l7.py --run T1=$T1/run.jsonl --run T2=$T2/run.jsonl \
  --out-json $E/l7_decompose.json
python3 $E/attribute_l7.py --run T1=$T1/run.jsonl --run T2=$T2/run.jsonl \
  --out-json $E/l7_attribution.json

# ⑧ 单变量证明
git diff --stat a977cb0 feat/d12c-dedup        # 期望仅 agent.py + render_d12d_prompt.py
```

---

## 八、与预登记的偏离（单列）

| # | 偏离 | 说明 | 对结论的影响 |
|---|---|---|---|
| D1 | 预登记 §3 只写「一条闸」（norm8），§4.1(a) 又给了 norm8/raw8 双门槛 | 本判读按**更严**的 §4.1(a) 读：两口径都要 ↓≥5pp 才算过闸 | **无**（两口径都没到 5pp，更严/更宽同结论） |
| D2 | 预登记未定义「模板化代价归因」方法 | 维度 A 用已入库 `decompose_l7.py`；维度 B 是本判读新写的 `attribute_l7.py`，**预登记未授权其为判据** | 只作解释，不入判定 |
| D3 | §4.1(b) 要求「T2 收尾后若实际分母偏差 >10% 须重跑带」 | 实测分母 **510/510**，偏差 0% ⇒ 未重跑；带已用 `--denom 510` 现算并落 `d3_noiseband_bootstrap_denom510.json`（sha256 `3e920ddd…`，与 CYCLE-07 §S05 逐字节一致） | 无 |
| D8 | **共享默认输出位被覆盖**：`v2/evidence/d3_noiseband_bootstrap.json` 的 `denom_510`（10:11 时为 `3e920ddd…`）于 10:11:52 被并发分析以 `--denom 341` 覆盖为 `2313c001…` | 已用 `--out` 把 `--denom 510` 重算到独立文件 `v2/evidence/d12d_t2_judge/d3_noiseband_bootstrap_denom510.json`，**复原同 sha 副本（`3e920ddd…`，逐字节一致）**；报告改为「脚本 sha + 语料 sha + `--denom 510` + 副本 sha」引用，见 §2.4 三段式 | **无**（带值未变且可离线重算出同一字节串） |
| D4 | `meta.code_sha` 字段的已知缺陷 | `meta.code_sha=5ca515d` 记的是「生成 meta 时刻的 HEAD」，不是起跑 pin；须与 `switch_proof.txt` 的 `parent a977cb0` 一起读。本报告已用 `git cat-file -t 5ca515d` 证其在本仓存在且 = `feat/d12c-dedup` tip | 无 |
| D5 | **跨窗口批** | 本批 **09:24:36 起跑**，本轮窗口以 **10:00** 划界 ⇒ **跨窗口批**（按 CYCLE-07 §1.4 先例单列）；实际收批约 **10:06**，END rc=0 | 引用时须写明 |
| D6 | `admission.verdict=REJECTED` | legacy manifest 的 `B-10_provider=<empty>` 结构性误判（T1 同状态）；真实验真以 `obs llm-cost` 为准 | 无 |
| D7 | 报告 HEAD（`635740f`，主树 master）≠ 被判树（`5ca515d`，`feat/d12c-dedup`） | 判读脚本在主树跑、日志来自分支树跑批；两者不可混称为同一 commit | 已在页首声明 |

---

## 九、下一轮候选（**只从这三项里选**，各带本轮证据来源）

本轮证据只支持三个方向，**不建议**再开第四个。每项都注明了它是「能被本报告哪个数字支撑」的：

| 选项 | 做什么 | 本轮证据来源（为什么是它） | 成本/风险 |
|---|---|---|---|
| **(a) 直攻开头层** | 先**诊断**「反的是哪一类开头句式」：对开头层做新/旧开头分类审计，量化「旧开头消失率 / 新开头集中度」，验证或否证 §4.3 的 H1 | `attribute_l7.json`：A 格 head×含具体物 **39.80%→45.29%（+5.49pp）**；`head_concentration` 开头 shingle 种类 343→331、top-5 覆盖 23→35；`把…往…上一` 开头 13.14%→15.49% | 纯离线（`tools/` + 证据目录），**无需跑批**；风险是只解释不产出效果，需配新预登记 |
| **(b) 把 D12-D 第 2 条拆成更窄的试验** | 只换**前半句/首个分句**、**保留具体物**，单独一臂（T3）对 T2 对照 | `decompose_l7`：`L7_noparen` **47.25%→48.24%（+0.99pp）**、旁白率 −16.08pp 而 L-7 几乎不动 ⇒ 正文层才是靶心；A/C 两格反向/减弱说明「开头」与「具体物」两条指令**互相干扰**，应拆开单跑 | 需**新跑一臂**（n16×60，约 45–60 分钟）+ 跑批串行窗口；须新开预登记先把阈值写死 |
| **(c) 承认提示词层已到边际，转行为层** | 作息 / 串门 / 习惯重复的离线量化（历轮几乎空白），例如同一 (slot, place) 的习惯强度与串门路径多样性 | 本轮 `L-7` 双口径几乎不动（−0.588 / −0.196pp，CI 均跨 0）+ 旁白砍 16pp 也换不来 L-7 下降 ⇒ **提示词层对 L-7 的边际已近零**；`t2_metrics.json` 的 `F-5_habit_repetition`（habit_strength=1.0、max_repeat_days_mean=4.375）说明行为层**有现成读数但缺基线** | 纯离线可做（无需跑批），但要**重新定义口径 + 预登记**，且与 R4 的 F 系列**不可比**（须写明差异） |

**取舍建议（基于证据、不含偏好）**：(a) 与 (c) 都能在**不跑批**的前提下推进，且都能把本轮的不确定项（H1 / L-7 是否已触顶）变成可判问题；(b) 是唯一能直接产出「效果读数」的，但**必须先有预登记**且占用唯一的跑批窗口。若下轮只想推一件事，建议 **(a)+(c) 并行做离线诊断**，把跑批窗口留给 (b) 的正式版。

---

## 十、局限与不可外推边界

1. **单 seed（42）/ 单规模（n=16×60）/ 单树**；不外推到其他 seed、其他规模、其他提示词组合。
2. `L-7` 是 **8-gram 撞车率代理**，不等于「读起来重复」；本项目人读 κ 仅 0.625 ⇒ **本报告不作人读结论**，也不把 L-7 的高低等同于「生活气息」的强弱。
3. **不得跨树比** `L-3_paren_block_any` / `L-2` / `F-6` 率（U-14）；本报告只报同树两臂的差值，且对差值**不声明显著性**（5pp 机制闸落在 ±5.88pp 带内）。
4. 「机制未生效」的**归因**超出本批证据范围：`prompt_fn_sha256 ≠ T1` 只证明**提示词版本被换掉**，**不证明模型遵守了新增的两行**；本批没有「模型是否读到/采纳该行」的采样证据。
5. 归因四格的 `head` 阈值取「归一化正文起始位置 <4」，与预登记「前四个字」的措辞对应；**未做 3/5 的敏感性扫描**，故 A/C 格的绝对 pp 值应视为量级参考，**方向**（开头升、正文具体物降）才是结论。
6. `len_p50` 一律用 **excl_paren** 冻结读数器；**不得**引用 `arm_state_check.txt` 的 `len_p50=67.0`（未去括号口径）——那是另一个数。
7. 本轮只移动了**提示词**，未改任何机制层；即便 D12-D 将来过闸，也只说明「能同时有具体物且少撞车」，**仍不等于「像过日子」**。

---

## 十一、产物索引

| 类别 | 路径 |
|---|---|
| 判读摘要（团队内） | `team-workspace/judge/judgment.md` |
| 复算证据包 | `v2/evidence/d12d_t2_judge/`（`llm_cost.txt`、`b2_band.json`、`b2_band_denom510.txt`、`judge_metrics.json`、`t1_metrics.json/.md`、`t2_metrics.json/.md`、`arms_d12c_metrics.json`、`t2_raw8_indep.txt`、`l7_decompose.json`、`l7_attribution.json/.txt`（含 `head_concentration` / `opening_pattern_ba_wang_yi`）、`attribute_l7.py`、`d3_noiseband_bootstrap_denom510.json`（B2 带复算产物，sha256 `3e920ddd…`）、`b2_band_denom510_rerun.txt`） |
| 截图清单（唯一来源） | `team-workspace/shots/index.md`；图片在 `v2/evidence/d12c_t1_shots/`、`v2/evidence/d12d_t2_shots/` |
| 预登记 | `v2/refs/D12D-prereg-dedup-on-detail.md` |
| 臂接线证明 | `v2/evidence/d12d_wiring_proof.md`、`v2/evidence/run_d12d_on_n16r60_seed42/switch_proof.txt` |
