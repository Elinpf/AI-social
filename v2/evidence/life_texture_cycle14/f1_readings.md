# F-1 非功能性闲聊占比 · CYCLE-14 可复算读数 + 可比性裁决 + 二维标定

> **笔误说明（置顶）**：任务卡原文写「非功能性**嗟啥**」，为 Leader 打字笔误；正确表述为「F-1 **非功能性闲聊（废话）占比**」，口径以 `reports/R4-life-texture.md:34` 的定义式（表头 `:32-34`）为准。本目录所有文件统一写「闲聊」。
>
> 作者：life-texture-analyst（生活气息判读员）｜时点：2026-10-24 04:1x +08:00｜零 LLM、零跑批、只读既有 run.jsonl
> 结论只取白名单状态词：**描述性读数 / 不可判 / 达标 / 未达标**；本文件**不用**「改善 / 变好 / 提升」。

---

## 0. 一句话

D12-I 的 **F-1 = 363/510 = 71.1765%**；同结构参照臂 T5 = **364/510 = 71.3725%**、D12-H = **360/510 = 70.5882%**。三臂互差 ≤ 3 条消息（≤0.59pp），Wilson95 区间大面积重叠 ⇒ **F-1 在本轮任意两臂之间都不可分辨（描述性读数）**；同时 D12-I 的 **L-3 = 369/510 = 72.3529%** 相对 T5 `57.8431%` 高 `+14.51pp`。即：**旁白轴发生了大位移，闲聊轴没有位移**——这是二维标定的全部结论，**不是**任何效果判定（本轮无新臂、无单变量对照）。

---

## 1. 先证「尺子没动」，再出数

### 1.1 版本 diff：F-1 实现自 v0-anchor 出数以来纯增量、零删改

```
$ git diff --stat db82892 HEAD -- tools/d5/dialogue_metrics.py
 tools/d5/dialogue_metrics.py | 552 +++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 552 insertions(+)
$ git diff db82892 HEAD -- tools/d5/dialogue_metrics.py | grep -c '^-'
1                                    # 唯一命中是 diff 头 `--- a/tools/d5/...` ⇒ 真实删除行 = 0
$ git diff db82892 HEAD -- tools/d5/dialogue_metrics.py | grep '^-' | head -1
--- a/tools/d5/dialogue_metrics.py
$ git blame -L 1040,1060 --date=short tools/d5/dialogue_metrics.py | head -3
→ b306a40e 2026-10-20 …  F-1 整块（TRANS_RX / func 计数 / F-1_chatter 输出）自 2026-10-20 起未变
```

| 项 | v0-anchor 出数时（记录在 `v2/evidence/d5_metrics_v0anchor.json::inputs`） | 本轮 HEAD |
|---|---|---|
| 脚本 sha256 | `288d713f75291273508872e48852625fdac8cae3cd9779eb0cf6428d0b7ddc4f`（= commit `db82892`/`b64ecd0` 版本） | `1d914735f3a13cf4e1640bd694f1d0e070096c9f50abfdefa7359417df551271`（= `d0a320b` master） |
| 二者关系 | — | **HEAD 相对该版本 +552 行 / −0 行**（只新增 F-8 三分解），F-1 相关代码逐字未改 |
| `task_tags.txt` sha256 | `a71c6c963279b28f6f9de3b44317b5c9bbf80498c594c98f9460ed79954aa69e` | **同一 sha**（`a71c6c96…`，词表 12 个事务 tag 未动） |

### 1.2 行为学证据：R4 那三个旧读数在**现在的代码**上逐位复现

用 HEAD 版 `tools/d5/dialogue_metrics.py` 重跑 R4 三臂的原始日志，与 `R4-life-texture.md:101` 的读数比对：

| 臂 | R4 写的 F-1（分子/分母） | 本轮 HEAD 代码复算 | 是否逐位相同 |
|---|---|---|---|
| v0-anchor | 77.0%（`R4:101`） | `0.770053` = 144/187（functional=43） | ✅ 相同 |
| A0 | 76.1%（`R4:101`） | `0.760933` = 522/686（functional=164） | ✅ 相同 |
| A1-措辞 | 75.0%（93/124）（`R4:101`） | `0.75` = 93/124（functional=31） | ✅ 相同 |

⇒ **3/3 逐位相同**：本轮读数与 R4 旧读数**同尺子**，「拿新尺子对旧读数作差」的风险已排除。差异只可能来自「不同批的日志」，不来自「不同版本的尺子」。

---

## 2. F-1 复算表（口径名 + 分子/分母 + 来源批 + 来源路径 + sha）

**口径名**：`F-1_chatter.nonfunctional_chatter_rate`（`tools/d5/dialogue_metrics.py:1056-1060`）
**定义式（逐字照抄脚本 rule 字段）**：功能性 = `tag_hints ∩ task_tags` 非空 **或** 正文命中事务正则（`多少钱|价钱|买|卖|记账|按流程|付钱|工钱|便宜点|划算|合同`，`:1041`）；闲聊率 = `1 − 功能性占比`。
**分母**：`L_wording.denominators.per_message` = `len(extract_messages(recs))`，即全部 `MSG_DM/MSG_PUBLIC/MSG_GROUP` 事件条数。

| 臂 | 来源批 / 分支 | 日志路径（仓库内相对） | 日志 sha256（前 12） | 分母 n_msg | 分子（闲聊） | 功能性 | **F-1** | Wilson95 |
|---|---|---|---|---|---|---|---|---|
| **D12-I** | `feat/d12i-aligned` n16×r60 seed42 | `.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl` | `72c0ca97fe6e` | **510** | **363** | 147 | **0.711765**（71.1765%） | [0.670987, 0.749376] |
| T5 | `d12g-diverse2` n16×r60 seed42 | `.worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42/run.jsonl` | `dd4ad73d5a21` | 510 | 364 | 146 | 0.713725（71.3725%） | [0.673012, 0.751244] |
| D12-H | `d12h-pairing` n16×r60 seed42 | `.worktrees/d12h-pairing/v2/evidence/run_d12h_pairing_n16r60_seed42/run.jsonl` | `122b36e98826` | 510 | 360 | 150 | 0.705882（70.5882%） | [0.664916, 0.743770] |
| v0-anchor | `v0-anchor` 锁定批（84 轮） | `v2/evidence/run_d2_before_n16_seed42/run.jsonl` | `c1f86bf61f62` | 187 | 144 | 43 | 0.770053（77.0053%） | [0.704669, 0.824566] |
| A0 | `v2/evidence/run_d2_after_n16_seed42` | `v2/evidence/run_d2_after_n16_seed42/run.jsonl` | `643f13a528c2` | 686 | 522 | 164 | 0.760933（76.0933%） | [0.727619, 0.791341] |
| A1-措辞 | 4 agents × 60 回合（`REJECTED` probe） | `v2/evidence/run_a1_wording_n4r60_seed42/run.jsonl` | `ae969198feae` | 124 | 93 | 31 | 0.75（75.0%） | [0.667052, 0.817924] |

> 上表全部数值由 `f1_readings.json` 机读产出（每臂含 `log_sha256` 全文、`n_msg`、`functional_msgs`、`chatter_numerator`、`wilson95`、`ruler.script_sha256`、`ruler.task_tags_sha256`）。

### 2.1 分子分解（解释「为什么三臂几乎一样」）

| 臂 | 功能性总数 | 其中 tag 通道命中 | 仅事务正则命中 | tag∩正则双命中 | 仅 tag 命中 | tag 命中按 tag 计 |
|---|---|---|---|---|---|---|
| D12-I | 147 | **129** | 18 | 16 | 113 | `counter_propose 41 / polite_reject 35 / scarce_buy 53` |
| T5 | 146 | **129** | 17 | 10 | 119 | 同上，**逐项相同** |
| D12-H | 150 | **129** | 21 | 6 | 123 | 同上，**逐项相同** |
| v0-anchor | 43 | 39 | 4 | 6 | 33 | +`select_location 5`（`legacy` 结构） |
| A0 | 164 | 136 | 28 | 13 | 123 | +`select_location 6` |
| A1-措辞 | 31 | 29 | 2 | 1 | 28 | 结构差异，见下 |

**结构性事实（D12-I / T5 / D12-H 三臂）**：`tag_hints` 在同一线程内恒为常量并原样继承（CYCLE-13 起的新结构，见 `dialogue_metrics.py:1057-1062` 上方 R19 注释），因此 **129/147 = 87.8% 的功能性判定由「线程模板 tag」决定，且三臂的 tag 通道命中数逐项相同（41/35/53）**。⇒ F-1 在**同结构三臂之间**的可动空间只剩「事务正则通道」（18 / 17 / 21 条），**尺子对结构高度不敏感**；把三臂 F-1 并排读成「趋势」属越界。

---

## 3. 可比性裁决（逐臂：分母同源？口径同源？能否做差？）

**判定依据只引字段/行号**，不引「看起来差不多」。

| 臂 | 分母同源？ | 口径同源？ | 能否做差？ | 裁决依据（字段/行号） |
|---|---|---|---|---|
| **T5** | **是** | **是** | **可做描述性差，但差值不可判** | 分母同源：两批 `denominators.per_message = 510`，且 `thread_schema="explicit"`、`n_threads=169`、`seed=42`、`rounds_max=60` 全等（`f1_readings.json` 各臂 `n_msg`/`cross_check.n_threads`）；口径同源：两批 `ruler.script_sha256` 与 `ruler.task_tags_sha256` 全等。**但** 两臂是不同分支的不同生成代码（`d12g-diverse2` vs `d12i-aligned`），且 F-1 分子 87.8% 由结构 tag 决定 ⇒ 差 −1 条消息（−0.196pp）**落在不可分辨区**，只能写「持平」，不能写方向。 |
| **D12-H** | **是** | **是** | **可做描述性差，差值不可判** | 同上（510/169/seed42/r60、脚本与词表 sha 全等）；差 +3 条消息（+0.588pp），Wilson95 区间几乎完全重叠 ⇒ 不可分辨。**禁止**把 D12-H 的「靠砍旁白换重复」判词（CYCLE-12）挪到 F-1 上说事。 |
| **v0-anchor** | **否** | **是**（尺子同源） | **不得与 D12-I 做差** | 分母不同源：`n_msg=187`、`rounds_max=84`、`legacy` 线程结构（`d5_metrics_v0anchor.json::inputs.rounds_max=84`，`F-2b` 分母 172 且标注 `thread_schema=legacy`）；且 tag 通道成分不同（含 `select_location`，总数 39 ≠ 129）⇒ 消息级混样不同（per-message 率的分母人群不同）。尺子同源已由 §1.2 证。 |
| **A0** | **否** | **是** | **不得与 D12-I 做差** | `n_msg=686`（`d5_metrics_a0.json::meta.n_messages=686`），规模与 D12-I 的 510 不同；tag 成分含 `select_location`。R4 自己对这三臂也只写「同量级；不作结论」（`R4:101`）。 |
| **A1-措辞** | **否** | **是** | **不得做差，且不得参与任何比较** | `n_msg=124`、4 agents × 60 回合、`admission.verdict=REJECTED`（`B-15_msg_volume` 124<150，见 `R4:99` 与 `d5_metrics_a1.json::admission`）⇒ `evidence_level=probe`。 |

**R4 旧表（77.0 / 76.1 / 75.0）的正确读法**：三个百分数**分母不同源（187 / 686 / 124）**，R4 自己标「三臂同量级；不作结论」（`R4:101`、`:113`）。本轮**不**把它们并排暗示趋势，也**不**把它们与 D12-I 的 71.18% 做任何减法。若要一句人话：**「在四类结构上 F-1 都落在 70–77% 这个宽带内；这个宽带的宽度（≈7pp）远大于任何两臂之差」**——这是描述性读数，不是效果量。

---

## 4. 二维标定表：F-1（闲聊占比）× L-3（旁白率）

**L-3 读数来源**：D12-I 取 `v2/evidence/d12i_readings_20261024/form_metrics_full.json::metrics.L-3_paren_block_any`（`numerator=369`、`denominator=510`、`value=0.723529`，该文件 sha256 `2e7213dc0045c06cf6cbe794d0f68b027b90a2f3c1f005d39e0db1f3d7dadf7a`，已用目录内 `SHA256SUMS` 校验 OK）；T5 / D12-H 取 `v2/evidence/form_metrics/{t5,d12h}_form_metrics.json`（CYCLE-13 §2.3 已入库：`295/510`、`1/510`）。本文件**未重跑** L 系列出数器；上述 L-3 亦与 d5 `L_wording.L-3_paren_block_any` 逐位一致（`f1_readings.json::cross_check.d5_L3` = 0.723529 / 0.578431 / 0.001961）。

| 臂 | F-1（闲聊） | L-3（旁白） | 二维位次 |
|---|---|---|---|
| **D12-I**（本轮被批） | **363/510 = 71.1765%** | **369/510 = 72.3529%** | 右上：闲聊未动、旁白最高 |
| T5（参照点 1） | 364/510 = 71.3725% | 295/510 = 57.8431% | 左上偏中 |
| D12-H（参照点 2） | 360/510 = 70.5882% | 1/510 = 0.1961% | 左下（旁白被砍到地板） |

**描述性读数（白名单词）**：

1. **F-1 轴**：三点纵坐标差 ≤0.59pp，Wilson95 两两重叠 ⇒ **不可判（无差异）**。
2. **L-3 轴**：`0.1961%` → `57.8431%` → `72.3529%`，跨度 `72.16pp` ⇒ 该轴**有真实、可分辨的位移**（各点分母同为 510，口径同为 `PAREN_ANY_RE` 命中的 MSG 条数）。
3. **二维含义**：三条臂在「闲聊」维度上几乎是同一个点，只在「旁白」维度上被拉开——与 CYCLE-13 §5.5（`:492-497`）的推论方向一致：**旁白是这三臂之间真正的自由度，闲聊不是**。

**允许区间建议（描述性、非判据）**：

| 轴 | 建议写法 | 依据 |
|---|---|---|
| F-1 | `∈ [66.37%, 76.37%]`（= T5 `71.3725%` ±5pp），或直接用三臂经验带 `[70.0%, 72.0%]` 作**描述性**参照带；**不建议**把 F-1 当任何闸的判据（分子 87.8% 由结构 tag 决定，见 §2.1） | T5 为同结构参照臂；±5pp 与 D12-I 预登记 F1 的 ±5pp 同尺度（`cycle14-state-brief.md` §3.1 行 33-54） |
| L-3 | `∈ [52.84%, 62.84%]`（= T5 `57.8431%` ±5pp），与 CYCLE-13 §5.5 的建议逐字一致 | `reports/CYCLE-13-20261024.md:497` |

> ⚠️ 两条区间都是**允许区间建议**，不是「达标线」；D12-I 的 L-3 `72.3529%` **超出**上表 L-3 建议带（描述性事实），其判词在 `v2/evidence/d12i_result.md` 已由他人给出（`作废（形态漂移，非单变量）`），本轮**不复判、不改判**。

---

## 5. 不可引用项 / 局限（必须先读）

1. **F-1 不是「生活质量」的直接测量**：它是 per-message 的结构代理，且在新结构下 87.8% 的分子由线程模板 tag 决定（§2.1）⇒ **不能用它宣称任何「生活气息变化」**。
2. **三臂 F-1 的「持平」不是效果结论**：T5 / D12-H / D12-I 之间除 F-1 外的维度（生成代码、旁白率、重复率）都不同，非单变量 ⇒ 任何差值都不能归因。
3. **v0-anchor / A0 / A1-措辞 不可与 D12-I 做差**（§3），其读数只作「宽带一致性」的描述性参照。
4. **L-7 / L-1 等 L 系列本轮不判读**，属度量与渲染链负责人口径；本文件只借 L-3 作二维纵轴的参照数值。
5. 若日后要重新出数，**必须**用 `tools/d5/dialogue_metrics.py`（sha256 `1d914735…`）与 `task_tags.txt`（sha256 `a71c6c96…`）；两者任一变化，本文件全部数值失效。

---

## 6. 复算命令（可原地重放，零 LLM）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# ① 一次性复算 6 臂 F-1（本文件所有 F-1 数值的唯一来源）
python3 v2/evidence/life_texture_cycle14/f1_recompute.py \
  --arm D12-I=.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --arm T5=.worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42/run.jsonl \
  --arm D12-H=.worktrees/d12h-pairing/v2/evidence/run_d12h_pairing_n16r60_seed42/run.jsonl \
  --arm v0-anchor=v2/evidence/run_d2_before_n16_seed42/run.jsonl \
  --arm A0=v2/evidence/run_d2_after_n16_seed42/run.jsonl \
  --arm A1-措辞=v2/evidence/run_a1_wording_n4r60_seed42/run.jsonl \
  --out-json v2/evidence/life_texture_cycle14/f1_readings.json

# ② 单臂全指标（下游标准用法，F-1 在 F 系列表内）
python3 tools/d5/dialogue_metrics.py \
  --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --meta .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/meta.json \
  --out-json /tmp/d12i_d5.json --out-md /tmp/d12i_d5.md

# ③ 日志身份校验（应为 72c0ca97…8f5d0c4 / 117724 行）
sha256sum .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl
wc -l    .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl

# ④ L-3 参照（不重跑，仅校验 leader 落盘件的完整性）
(cd v2/evidence/d12i_readings_20261024 && sha256sum -c SHA256SUMS)

# ⑤ 尺子版本 diff（§1.1）
git diff --stat db82892 HEAD -- tools/d5/dialogue_metrics.py
sha256sum tools/d5/dialogue_metrics.py tools/d5/task_tags.txt
```

---

## 7. 文件与 sha256（本目录）

```bash
cd v2/evidence/life_texture_cycle14 && sha256sum -c SHA256SUMS
```

| 文件 | sha256 | 作用 |
|---|---|---|
| `f1_readings.json` | `a46ace5e95f5dd79eaff86b4cd5504cd8f720c03c1217033dc401258e2ae16ed` | 机读读数：6 臂 ×（n_msg / functional_msgs / chatter_numerator / rate / wilson95 / 分子分解 / ruler sha / log sha） |
| `f1_recompute.py` | `fc118ff2f7ab95f29b59f216561ae9b07f6a4cd02b65de6342aeabfb4a271e01` | 复算器（importlib 直取 `tools/d5/dialogue_metrics.py`，只加分子分解，不新立尺子） |
| `f1_report_insert.md` | `9be79f4234999e85f777f5ee6c567e515e7aacabbaaee08722b230c3bf002d66` | 可直接进报告 §2 的片段（自测 `len=798` 字符 ≤ 800） |
| `f1_readings.md` | 见 `SHA256SUMS`（自哈希写不进自身，故由清单文件承载） | 本文件（人能读的表 + 复算命令 + 裁决） |

> ⚠️ 若 `f1_report_insert.md` 在报告成稿时被再编辑，其上表 sha 失效——以同目录 `SHA256SUMS` 的**当次**校验为准。
