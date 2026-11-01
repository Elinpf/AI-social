# R50 · 具体性尺子 v2 —— 位置分层与选点消歧（**post-hoc 开发集标定，不产生效果结论**）

- 报告人：`report-writer`（实验报告与证据官）｜出数时刻：2026-11-01 20:0x +08:00
- 分支：`feat/r49-life-diversity`，基线 HEAD **`f53d3a1`**（R49 定稿）→ 本轮尺子入库 **`58bcdc7`**（`master` 未动；本报告入库 sha **`<pending-repo-gatekeeper>`**，由 R50-T3 提交后回填）
- 预登记卡 v2（**下一轮真跑批用**，本轮零跑批）：`v2/refs/R50-prereg-20261101.md`
- 尺子入库 commit：**`58bcdc7`**（`ruler(R50)`，5 文件 / 1262 insertions：新尺子 + 标定器 + 预登记卡 + 标定 JSON + 标定说明）
- 新尺子：`tools/metrics/r50_detail_position.py`（`ruler_version=r50-detail-position-v2`，`impl_sha256=ccac0523544787054029ba9ff3680e86d25b2d84909451364cd760f3a0e0b1d7`，`lexicon_sha256=e8507082b0915f93eb62ab200969da17d4a700e1b337e0d97ce2355196dd7477` ＝ **与 R49 预登记卡逐字相同**）
- 标定读数：`v2/evidence/r50-calib-20261101.json`（`status=POST_HOC_DEVELOPMENT_SET_CALIBRATION`）
- 截图：`v2/evidence/r50_shots/`（本轮**现渲** 4 张 + 2 份 `render_report_*.json`）
- 输入（R49 已冻结两臂，本轮**未重跑、未改一行**）：
  - OFF：`v2/evidence/r49-diversity-off-20261101_n16r24_s42/`，`run.jsonl sha256=40d1bb09c3face4afabbae8e786eb2f7aaaf3ecb079171aaa83a6425b8430434`
  - ON ：`v2/evidence/r49-diversity-on-20261101_n16r24_s42/`，`run.jsonl sha256=cfc1d44ae065ff660394efb997c3bd44be18bb3f7ba6a1af7336dac69c39b6bb`

---

## 摘要（**首段即红线**）

**本轮是开发集标定，不产生效果结论。** 全部 Δ / Fisher p / MDE 都来自 R49 **已冻结日志**上的事后重算（`status=POST_HOC_DEVELOPMENT_SET_CALIBRATION`），**不得写成任何效果判决**。本轮真正交付的是三件事：①**旧尺子的选点缺陷已定位并修正**（把「剥旁白后前 6 字符」单窗口，改成 `opener6 / first_clause / first_clause_skip / anywhere` 四档位置分层）；②**下一轮真跑批的判据已提前冻结**（M1a `first_clause_skip` Δ≥+14.4pp 且绝对率≥73.0%、M1b `first_clause` Δ>0 守卫、U1–U8 八条不可判条件，见 `v2/refs/R50-prereg-20261101.md`）；③**`distinct_body_ratio` 正式退役**。

**定档（只取实际达到的那一档）**：**尺子缺陷已定位并修正 ＝ 已成立（观测级）**；**机制是否被采纳 ＝ 不判**（无新数据）；**效果 ＝ 不判**；**生活气息提升 ＝ 不判**。

若只陈述观测级事实：旧口径 `opener6`（6 字窗口）对两臂做的是**近似等比压缩**——压缩因子（旧/新）OFF **`0.3750`**（42/112）、ON **`0.3904`**（57/146），**两臂仅差 4%**；相对漏判率 OFF `70/112=62.50%`、ON `89/146=60.96%`（**ON 并不更高**）。其后果有两个，都可复算：①**效应被压掉一半以上**——`Δ` 从 `+17.80pp` 掉到 `+7.85pp`，**压掉 9.95pp＝55.88%，只保留 44.12%**；②**功效也被污染**——用于解 MDE 的 OFF 基线 `p1` 被低估 **36.65pp**（`0.219895` vs `0.586387`）。⇒ **「旧尺子测错对象、把效应近似等比压缩过半」这一条已成立（观测级）**。⚠️ 注意：这**不是**「旧尺子专门低估某一臂」——两臂压缩因子近似相等，绝对漏判条数 `89 > 70` 纯属 ON 基数更大（`146` vs `112`），**不得写成「旧窗专门低估了某一臂」这类因果**（口径见 `r50-calib-20261101.json` 的 `compression_analysis.note`）。⚠️ 但由此**不得反推 D12-A 有效**：位置修正后的高读数（`first_clause_skip` OFF 58.64% → ON 76.44%、Δ+17.80pp）本身是 post-hoc 标定，**且它的窗口参数（跳≤2 个短分句）就是在同一批 R49 数据上定的、含拟合成分**，增益还可能全部来自「跳过前导分句」这一机械动作（见 §6-1、§6-4）。

---

## 1. 问题与背景（只推进这一个维度）

R49 的结论是「机制接通成立、效果未成立」，但 R49 自认存在判据选点缺陷，并把它列为下一轮第一优先（`reports/R49-diversity-20261101.md` §10 缺陷 1、§11 建议 1；`docs/team-board.md` B 段同登记）。缺陷的实证形态是模型的实际写法：

```
金先生，（把琴弓在松香上蹭了两下）天刚亮我就开练了，这段揉弦总差口气。你听听。
```

「琴弓 / 松香 / 天刚亮」都是具体物与具体事，但 `strip_lead_paren(body)` 的前 6 字符是「金先生，（把」⇒ 旧闸判 0。**旧尺子测的是「有没有立刻说物」，不是「有没有说具体物」——判据与假设错位。**

为什么这一轮**不跑批、只修尺子**：R49 两臂已花 ≈48 min / ≈6.7×10⁵ tokens（`reports/R49-diversity-20261101.md` §10 缺陷 4）。在判据本身可能测错对象的前提下再花钱跑一轮，等于把预算押在一个已知有偏的闸上。**先把尺子修好、把下一轮判据冻结在数据之前，再花钱**——这是本轮唯一做的事，**零新增 LLM 调用、零新增跑批**（`pgrep` 证据见 §9）。

---

## 2. 预登记与不可判条件（**先冻结，再看数据**）

### 2.1 冻结时序

本轮**没有任何新数据**产生，因此「预登记先于数据」在这里的形态是：**卡冻结在下一轮跑批之前**。卡文件 `v2/refs/R50-prereg-20261101.md` 与尺子 `tools/metrics/r50_detail_position.py` 同批落盘（2026-11-01 20:02–20:03），**早于任何 R50 跑批**（R50 至今 0 次跑批）。卡的 §10 自我约束条款规定：卡提交后 §3 窗口定义、§4 阈值、§6 不可判条件一律冻结，跑批后出现的「更好的尺子/窗口/词表」只能写进**下一轮**预登记，**不得回填本轮结论**。

### 2.2 下一轮判据（摘录卡 §4，**阈值不得事后改**）

| 编号 | 指标 | 方向 | 达标线 |
|---|---|---|---|
| **M1a（主闸）** | `first_clause_skip` | ON > OFF | **Δ ≥ +14.4pp**（= 用 OFF 臂 `p1=0.586387`、`n1=n2=191` 反解的 MDE）**且 ON 绝对率 ≥ 73.0%** |
| **M1b（一致性守卫，非独立判据）** | `first_clause` | ON > OFF | **Δ > 0**（只要求方向为正，不设显著性）——用于否掉「增益只来自跳过动作」的假象 |
| E1 | `opener_top10_share` | ON < OFF | **Δ ≤ −5.9pp** 且 ON 的 Wilson95 上界 < OFF 点估计；`\|Δ\|<5.9pp` 一律写「不可判」 |
| E2 | `distinct_body_ratio` | — | **不判（已退役，见 §2.4）** |
| E3 | `backref_hit` | 无方向 | **只描述，不进判据** |
| 对账档 / 对照档 | `opener6` / `anywhere` | — | **只记录，不作判据** |

### 2.3 不可判条件（U1–U8，逐条触发即写「不可判/作废」）

U1 任一臂 `n_msgs<160`｜U2 `obs llm-cost --require-provider openai_compat` 不过或 `degraded≠0` ⇒ 全部作废｜U3 M1a 未达 ⇒ 判「机制未生效」｜U4 M1a 达但 E1 `|Δ|<5.9pp` ⇒ 「效果不可判」｜U5 两臂 `prompt_fn_sha256` 相同 ⇒ 整轮作废｜U6 `run_batch.rc≠0` 或 `TURN_SEAL` 不完整 ⇒ 该臂作废｜**U7（R50 新增）两臂 `no_cue` 率差 ≥10pp ⇒ M1a 与 E1 全部不判**（本轮旧数据上实测 −2.09pp，**未触发**）｜**U8（R50 新增）`first_clause_skip` 与 `first_clause` 方向相反 ⇒ 判「位置档自相矛盾」**。

### 2.4 `distinct_body_ratio` 退役登记（按 R49 §11 建议 3 正式执行）

- **事实**：`c1-scene-a1-20261101_n16r24_s42` 与 **R49 两臂**连续多批均为 **`191/191 = 1.000`**（Wilson95 上界 `1.0`）。本轮在 R49 两臂上复算，仍是 `off 191/191 = 100.00%`、`on 191/191 = 100.00%`（命令见 §9-④）⇒ **无区分度**，任何「保持不降」的写法都是白送分。
- **决定**：自 R50 起 `distinct_body_ratio` **退出判据体系**，只作描述性读数登记；**不得**在今后的预登记卡里重新启用为判据（除非出现 `rate < 0.99` 的新基线并能说明分母来源）。
- **同理**：`anywhere`（= R49 的 `detail_body`，含旁白整句）也贴近天花板（`97.91% → 100%`，MDE 仅 6.5pp），**永久只作对照档**，不得用作判据（反面教材见 §6-2）。

> **该退役与本轮「不产生效果结论」是同一件事的两面**：旧尺子里有一把已经饱和、一把测错位置；修完这两处之后，本轮**仍然不出效果结论**，因为修尺子不等于拿到新证据。

---

## 3. 接线与数据来源（本轮零新增跑批，全部为既有产物的复算）

### 3.1 数据身份（两臂均为 R49 已冻结产物，本轮未动一个字节）

| 项 | OFF 臂 | ON 臂 |
|---|---|---|
| 目录 | `v2/evidence/r49-diversity-off-20261101_n16r24_s42/` | `v2/evidence/r49-diversity-on-20261101_n16r24_s42/` |
| `run.jsonl sha256` | `40d1bb09…b8430434` | `cfc1d44a…c39b6bb` |
| `wc -l run.jsonl` | **34102** | **34102** |
| `n_msgs`（`MSG_DM/MSG_PUBLIC/MSG_GROUP`） | **191** | **191** |
| `run_batch.rc` | **0** | **0** |
| `meta.duration_sec` | 1459（24.3 min） | 1426（23.8 min） |
| `meta.provider` / `meta.model` | `openai_compat` / `DeepSeek-Flash` | 同左 |
| `meta.degraded_calls` / `fallback_detected` | 0 / false | 0 / false |

### 3.2 接线（`tools/r49/wiring_proof.py`，本轮重跑，`wiring_verdict=PASS`）

```
env_var=HITT_D12_DETAIL
OFF_dialogue_prompt_sha256=e672f5ec6306e4c0dba54022b69f92beb6863faa986f1302e27db464fd8819b1
ON_dialogue_prompt_sha256 =802082051c21678b1ef28de99c53c5e6f8021e05c853d8d2bd1f16974cf45d87
OFF_reply_prompt_sha256   =a5b2b11760ac8a3af443bae49cd788488c96565d29182f7fff84b975614d72e3
ON_reply_prompt_sha256    =b66e6e210072b68c6282cf73e3f645eacd71028d8158bcf2f03ed576698f89b6
detail_line_len_on=55
wiring_verdict=PASS
```

### 3.3 真 LLM 验真（**同屏必写**：R49 两臂原本的 `obs llm-cost` 状态）

两臂各跑 `obs llm-cost --require-provider openai_compat`，**我自查与 `repo-gatekeeper` 独立重跑双向一致**（口径：`engine_log(LLM_CALL)` 聚合 + `provider_guard` 校验，非 mock）：

| 指标 | OFF 臂 | ON 臂 |
|---|---|---|
| `rc` | **0** | **0** |
| `calls` / `degraded` | 2255 / **0** | 2255 / **0** |
| `cached` / `thinking` | 1387 / 425 | 1387 / 425 |
| `tokens_total`（in / out） | **335280**（173972 / 161308） | **339765**（182112 / 157653） |
| `by_provider` / `provider_guard.ok` / `problems` | `openai_compat:2255` / **true** / `[]` | 同左 |
| 分用途 calls | dialogue 193 / importance 1523 / judge 425 / negotiation 7 / plan 16 / reflect 91 | **完全相同** |

⇒ **真 LLM 跑批、无 mock 混入**；两臂 `calls` 完全相同（2255）说明该对比**未引入额外调用预算差异**。原始落盘：两臂各自 `llm_cost.gate.out`（`rc=0`）。

### 3.4 本轮自证「零跑批、零 LLM、冻结区零改动」

```
git diff --stat HEAD -- code/life code/orchestration code/config code/engine   # 空输出
pgrep -af '[r]un_batch|[o]rchestration run|[n]ightly.py'                      # 无命中（rc=1）
```

⚠️ 口径提醒：`pgrep -af run_batch`（**不带括号技巧**）会匹配到执行该命令的 shell 自身——这是 R49 §10 缺陷 3 记录过的假阳性，本轮用 `[r]un_batch` 写法规避，**不可据此写成"有并发跑批"**。

---

## 4. 三档读数（实际为四档 + 两个补充项；**禁止只摘主判据**）

同一份 `run.jsonl`、同一词表（`lexicon_sha256=e8507082…`）、同一 `n_msgs=191`，**只改「在正文哪一段里找具体物」**：

| 位置档 | OFF（n=191） | ON（n=191） | Δ | Fisher 双侧 p | MDE（n=191/臂） | Wilson95 是否重叠 |
|---|---|---|---|---|---|---|
| `opener6`（=R49 `detail_opener6`，对账档） | **42/191 = 21.99%** ｜[16.70, 28.38] | **57/191 = 29.84%** ｜[23.80, 36.68] | +7.85pp | `0.101829` | 10.7pp | 是 |
| `first_clause`（守卫档） | **48/191 = 25.13%** ｜[19.51, 31.73] | **61/191 = 31.94%** ｜[25.74, 38.85] | +6.81pp | `0.173801` | 11.4pp | 是 |
| **`first_clause_skip`（主判据候选）** | **112/191 = 58.64%** ｜[51.55, 65.39] | **146/191 = 76.44%** ｜[69.94, 81.90] | **+17.80pp** | **`0.000293`** | **14.4pp** | **否** |
| `anywhere`（=R49 `detail_body`，对照档·近天花板） | 187/191 = 97.91% ｜[94.74, 99.18] | 191/191 = 100.00% ｜[98.03, 100] | +2.09pp | `0.123034` | 6.5pp | 是 |
| `no_cue`（整条正文无具体物，地板） | **4/191 = 2.09%** ｜[0.82, 5.26] | **0/191 = 0.00%** ｜[0.00, 1.97] | −2.09pp | — | — | — |
| `paren_lead`（括号旁白起头，描述项） | 172/191 = 90.05% | 180/191 = 94.24% | +4.19pp | `0.1823`（R49 已公布） | — | 是 |

**关于 `opener6` 的 MDE 为何是 10.7pp（而不是 R49 公布的 11.7pp）**：R49 公布的 11.7pp 以 `c1-scene-a1` 基线 `p1=0.267016` 反解；本表一律用 **R49 自家 OFF 臂 `p1`**（`opener6` 为 `0.219895`），同一算法得 **10.7pp**。两者**基线不同、非矛盾**，R50 统一口径是「基线读数与判据同源」（见 `v2/refs/R50-prereg-20261101.md` §5）。

> **本表每一个数字都由一条命令产出**：`python3 tools/metrics/r50_calib.py --off … --on … --out-json v2/evidence/r50-calib-20261101.json`（纯标准库，`reconcile_all_match=True`），或单臂 `python3 tools/metrics/r50_detail_position.py --log …`。**再次声明：以上是开发集标定，不产生效果结论。**

### 4.1 「选点缺陷已成立（观测级）」的算法（**这是本轮唯一可写的成立项**）

`first_clause_skip` 与 `opener6` 用的是**同一个词表、同一批消息**，`first_clause_skip` 只是把窗口放宽到「跳过最多 2 个 ≤8 字且无具体物的前导分句」。两者分子之差就是**旧窗口漏判的条数**：

| 臂 | `first_clause_skip`（新，真有物） | `opener6`（旧） | 漏判条数 | 相对漏判率 | **压缩因子（旧/新）** |
|---|---|---|---|---|---|
| OFF | 112 | 42 | **70** | **70/112 = 62.50%** | **42/112 = 0.3750** |
| ON | 146 | 57 | **89** | **89/146 = 60.96%** | **57/146 = 0.3904** |

**正确读法：旧闸对两臂是近似等比压缩，不是专门低估某一臂。** 压缩因子 `0.3750` vs `0.3904` 只差 **4%**；相对漏判率 ON 甚至**略低**于 OFF（`60.96% < 62.50%`）。绝对条数 `89 > 70` 完全由 ON 基数更大（`146` vs `112`）解释，**不构成差分偏倚的证据**（拿绝对条数比相对比例 = 基数率谬误）。

**由此得出两条可复算后果（机器可读块 `compression_analysis`）**：

1. **效应被压缩过半**：同一个 `Δ`，旧窗口只给出 `+7.85pp`，新窗口给出 `+17.80pp` ⇒ **被压掉 `9.95pp`（`55.88%`），只保留 `44.12%`**（`retained_fraction=0.4412`）。因此 **R49 的 `+7.85pp < MDE 11.7pp` 不能读成「效应弱」**——它是「尺子把效应压掉一半以上之后的残余读数」。⚠️ 这句话只是**读数归因**，**不是效果判决**（post-hoc 红线不变）。
2. **功效估计也被污染**：旧口径把 OFF 基线 `p1` 从 `0.586387` 压到 `0.219895`，**低估 `36.65pp`**；而 MDE 由 `p1` 反解 ⇒ 旧尺子下算出的 MDE（10.7pp）与真基线对应的 MDE（14.4pp）**不是同一把闸的刻度**。两轮 MDE 不可直接互比，这也是 R50 卡强制改由脚本产出 MDE（`mde_table`）的原因之一。

**第三条证据：修正档是旧档的严格超集（不是换了一把不相关的尺）。** 逐条复核「`opener6` 判命中、但 `first_clause_skip` 判未命中」的消息条数：**OFF `0`、ON `0`** ⇒ 旧窗口命中的每一条，新窗口**必命中**；四档差异全部来自「新增命中」，不存在「新尺子把旧尺子已认的条目否掉」的情形。复算命令见 §9-3b。

> ⚠️ **这三条只证明尺子有缺陷（近似等比压缩、压缩后果可复算）；它们不构成任何效果证据**。`first_clause_skip` 的窗口参数就是在同一批数据上定的，因此上面 `+17.80pp` 的读数含参数拟合成分（见 §6-1、§6-4）。

---

## 5. 判据机械比对（把**下一轮**冻结闸套回旧数据，**不改判、不追认**）

下表**不是**本轮的判决，而是「把 `v2/refs/R50-prereg-20261101.md` §4 的闸机械地跑一遍已冻结数据会得到什么」。它的用途只有一个：**在花钱之前，看清这把闸会不会在这批数据上判过——从而暴露过拟合风险（见 §6-1、§6-4）**。

| 编号 | 达标线（卡 §4） | 旧数据上实测 | 机械结论 |
|---|---|---|---|
| **M1a** | Δ ≥ +14.4pp **且** ON 绝对率 ≥ 73.0%（MDE 由 OFF 臂 `p1=0.586387`、`n1=n2=191`、α=0.05 双侧、power=0.80 反解） | **+17.80pp**，ON `76.44%` | **✅ 会判过** |
| **M1b** | Δ > 0（仅方向） | **+6.81pp** > 0 | **✅ 会判过**（但强度弱，`p=0.174`） |
| **E1** | Δ ≤ −5.9pp 且 Wilson95 上界 < OFF 点估计 | `opener_top10_share` OFF 6.81% → ON 7.85%，**Δ=+1.05pp（方向相反）** | **❌ 不过 ⇒ 依 U4 写「效果不可判」** |
| E2 | 不判（已退役） | 191/191 → 191/191 | ➖ 不判 |
| E3 | 只描述 | `backref_hit` 31/191 = 16.23% → 17/191 = 8.90% | ➖ 只描述，不进判据 |
| U1 | ≥160/臂 | 191 / 191 | ✅ 未触发 |
| U2 | 门禁过 + degraded=0 | §3.3 | ✅ 未触发 |
| U5 | 两臂 prompt sha 不同 | §3.2 `PASS` | ✅ 未触发 |
| U6 | rc=0 + seal 完整 | `run_batch.rc=0` / `events 34102=34102` | ✅ 未触发 |
| **U7** | 两臂 `no_cue` 差 ≥10pp | **−2.09pp** | ✅ 未触发（余量 7.91pp） |
| **U8** | 两位置档方向相反 | 两档同向（+17.80 / +6.81） | ✅ 未触发 |

**一句话（按卡字面 + 红线）**：若把冻结闸套回旧数据，**M1a+M1b 会判过、E1 不过** ⇒ 依卡 U4 只能写「**效果不可判（效应低于本采样结构的 MDE）**」。**但这一步是 post-hoc 开发集标定，不产生效果结论，也绝不构成下一轮的预判**——下一轮必须在新数据上按同一把闸重跑。

> **这正是本轮最该被记住的一条**：闸在「设计它所依据的那批数据」上判过，几乎是必然的；它的信息量等于零。真正有意义的是它在**新数据**上判什么。

---

## 6. 反面证据与自证伪（**必须与结论同屏**）

1. **增益可能全部来自「跳过」这一机械动作，而非机制被采纳。** `first_clause_skip` 涨 **+17.80pp**，而 `first_clause`（不跳过的首分句）只涨 **+6.81pp**（`p=0.173801`，Wilson95 重叠）。若机制真的在提升「开口即带物」，首分句档应当同步上涨；现在两档落差 **10.99pp**，说明相当一部分增益来自「窗口多给了两次跳过机会」这一自由度。**卡里 M1b 守卫正是为此存在，而 M1b 只要求"方向为正"，强度不足以排除该解释** ⇒ 本轮据此**不得**写「位置修正后机制已被采纳」。
2. **对照档 `anywhere` 是反面教材，不是判据。** `97.91% → 100%`，MDE 仅 6.5pp；拿它当闸必然「通过」且毫无信息量。R49 之所以把 D12 家族旧口径判成不可判，正是因为它在句中层早已饱和（`reports/R49-diversity-20261101.md` §2 硬约束 3）。
3. **地板不一致（U7 的余量只剩 7.91pp）。** `no_cue` OFF `4/191=2.09%` vs ON `0/191=0.00%`（差 −2.09pp）。地板一动，「开口带物」的分子/分母就不再取自同一总体。本轮未触发 U7，但**下一轮若样本量放大、或提示词微调，这条会先亮**。
4. **本轮的窗口定义是在看过 ON 臂失败样例之后设计的，存在对这批数据的过拟合风险。** `first_clause_skip` 的「跳过 ≤2 个」「前导分句 ≤8 字且无具体物」两个参数，都是从「金先生，（把琴弓…」这类样例反推出来的（见 `v2/refs/R50-prereg-20261101.md` §0）。**这在方法论上是"按失败样例调窗口"**，唯一合法的检验方式是**新数据**。这也是本轮坚持「不产生效果结论」的技术理由，不是谦辞。
5. **自证伪 A（旧口径没被改坏）。** 新尺子 `opener6` 档与 R49 已公布读数**逐条一致**：OFF `42/42`、ON `57/57`；`anywhere` `187/187`、`191/191`；`paren_lead` `172/172`、`180/180`；`n_msgs 191/191`。机器可读证据：`r50-calib-20261101.json` 的 `r49_reconcile.all_match == true`。⇒ 四档之间的差异**不是**靠改坏对账档造出来的。
6. **自证伪 B（确定性）。** 同输入两次运行 `r50_detail_position.py --out-json` **逐字节相等**（`DETERMINISTIC`）；重跑 `r50_calib.py` 与入库 JSON **逐字节相等**（`CALIB_BYTE_IDENTICAL`）。
7. **自证伪 C（词表未扩）。** `lexicon_sha256=e8507082…` 与 R49 预登记卡 §3.1 逐字相同，`lexicon_extensions: []` ⇒ 四档差异**不可能**来自加词。

---

## 7. 截图（本轮**现渲**，禁占位 / 禁拼图 / 禁旧图冒充）

R49 旧图在 `v2/evidence/r49-diversity-{off,on}_shots/` 是存在的，但**本轮不在报告里引用旧图**——两臂 chat / rhythm 全部在 R50 重新渲染到 `v2/evidence/r50_shots/`：

```bash
python3 tools/metrics/render_shots.py --run-dir v2/evidence/r49-diversity-off-20261101_n16r24_s42 \
    --batch-id R50-off --outdir v2/evidence/r50_shots --views chat,rhythm   # rc=0, ok=2 fail=0
python3 tools/metrics/render_shots.py --run-dir v2/evidence/r49-diversity-on-20261101_n16r24_s42 \
    --batch-id R50-on  --outdir v2/evidence/r50_shots --views chat,rhythm   # rc=0, ok=2 fail=0
```

| 臂 | 图（PNG 文件名内嵌日志 sha8） | PNG sha256 前 8 | 像素自检 |
|---|---|---|---|
| OFF | `R50-off-chat-40d1bb09.png` | `4d6d7b84` | distinct_colors 23467 / top_color_frac 0.1513 / **OK** |
| OFF | `R50-off-rhythm-40d1bb09.png` | `012c17a6` | distinct_colors 20827 / top_color_frac 0.3709 / **OK** |
| ON | `R50-on-chat-cfc1d44a.png` | `12946cd9` | distinct_colors 23003 / top_color_frac 0.1573 / **OK** |
| ON | `R50-on-rhythm-cfc1d44a.png` | `09c09293` | distinct_colors 20789 / top_color_frac 0.3709 / **OK** |

**三件套完整性**（`reports/README.md:116` 要求「来源 run 目录 + 渲染命令 + 日志 sha256」）：

| 报告文件 | `run_dir` | `log_sha256` | `views[].png_sha256` | `triplet.gen_threads_cmd` | `pixel_selfcheck` |
|---|---|---|---|---|---|
| `v2/evidence/r50_shots/render_report_R50-off.json` | R49 OFF 目录 | `40d1bb09…` | ✅ 2 条 | ✅ 完整命令行 | ✅ 逐张落盘 |
| `v2/evidence/r50_shots/render_report_R50-on.json` | R49 ON 目录 | `cfc1d44a…` | ✅ 2 条 | ✅ 完整命令行 | ✅ 逐张落盘 |

- 两份报告均 `ok_count=2 / fail_count=0`，`rc.txt` 记 `off_rc=0 / on_rc=0`。
- `policy.code_untouched`：渲染服务根为**临时目录 + 符号链接**，未在 `code/frontend/` 下写入任何文件（`sys.dont_write_bytecode=True` 亦避免 `__pycache__`）。
- `policy.no_reuse`：输出同名 PNG 若已存在先删除，**只认本次现截**。
- 另存 `threads_R50-{off,on}.json`（`gen_threads.py` 派生物）供复核，`run_sha256_in_threads` 与两臂日志 sha 一致。

---

## 8. 下一轮建议（按性价比排序）

1. **跑下一轮（唯一能把"标定"变成"证据"的动作）**，两臂参数同步放大：
   - 方案 A（`n=191/臂`，≈45–55 min）：MDE **14.4pp**（由 OFF 臂 `first_clause_skip` 基线 `p1=0.586387`、`n1=n2=191`、α=0.05 双侧、power=0.80 反解；口径见 §4 表注与 `mde_table`）。**风险**：若真效应落在 10–12pp，本轮按 U4 只能写「不可判」。
   - 方案 B（每臂 ≥271 条，≈65–80 min，同一 `p1` 口径下 MDE 压到 12pp）：**推荐**。⚠️ 该推荐属于 **post-hoc 功效估算（仅用于排样本量，不是效果判决）**：本标定观测到的 +17.80pp 与方案 A 的 MDE 14.4pp 余量不大，而窗口参数本身是从这批数据反推的（§6-4），真实效应理应更小 ⇒ 用更大的 `n` 换更小的 MDE 是更划算的保险。
2. **`distinct_body_ratio` 永久退役**（见 §2.4）；`anywhere`/`detail_body` 永久对照档，不得再作判据。
3. **要判「生活气息」仍需新证据来源**：judge 语义维度（`is_reply`/自然度）或 ≥20 条人工盲评；否则任何轮次都只能停在②档以下——这一点与 R49 §11 建议 2 完全一致，本轮没有改变它。
4. **把 `backref_hit` 的下降（R49 `p=0.043913`）在新一轮卡里预登记为可判候选**：它是 R49 唯一"未被解释"的变化；本轮仍按 E3「只描述」处理，**不得**把它写成本轮结论。
5. **尺子层面的技术债**：`first_clause_skip` 的「≤2 个」「≤8 字」两个自由参数应在新一轮卡里做**敏感性报告**（如 skip∈{1,2,3} × 长度∈{6,8,10} 的读数矩阵），把「窗口调参」这件事本身变成可核对的读数，而不是写作里的隐参数。
6. **下一轮必须换世界：`HITT_WORLD_SEED=43`（新世界）+ 四档同屏——把它做成对 R50 标定的独立检验。** 理由：本轮四档读数全部来自 `seed=42` 的**同一批** R49 日志，而 `first_clause_skip` 的窗口参数正是在这批日志上定的（§6-4）。**只有在新 seed 的新世界上四档同屏重跑，`+17.80pp` 才可能从「含拟合成分的读数」升级为「独立检验下的读数」**；在新数据之前，任何"闸会判过"的结论都只属于 §5 的机械演练。建议在新卡里写明：主闸 M1a/M1b、守卫与不可判条件 U1–U8 **逐字沿用 R50 卡**（不得因新世界读数不同而改阈值），仅把 `HITT_WORLD_SEED` 42→43。

---

## 9. 一次性复算命令清单（**逐条可跑，产出本报告全部数字**）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# 0) 环境与边界（无跑批 / 冻结区零改动 / 分支）
git rev-parse --abbrev-ref HEAD                                  # feat/r49-life-diversity
git log --oneline -1        # 本轮尺子入库 58bcdc7（基线 f53d3a1）
git diff --stat HEAD -- code/life code/orchestration code/config code/engine   # 空
pgrep -af '[r]un_batch|[o]rchestration run|[n]ightly.py'; echo "rc=$?"         # 无命中，rc=1

# 1) 单臂四档读数（确定性；同输入两次输出逐字节相等）
python3 tools/metrics/r50_detail_position.py --log v2/evidence/r49-diversity-off-20261101_n16r24_s42/run.jsonl --label off
# → n_msgs=191 opener6=42/191 first_clause=48/191 first_clause_skip=112/191 anywhere=187/191 no_cue=4/191 paren_lead=172/191
python3 tools/metrics/r50_detail_position.py --log v2/evidence/r49-diversity-on-20261101_n16r24_s42/run.jsonl --label on
# → n_msgs=191 opener6=57/191 first_clause=61/191 first_clause_skip=146/191 anywhere=191/191 no_cue=0/191 paren_lead=180/191

python3 tools/metrics/r50_detail_position.py --log v2/evidence/r49-diversity-off-20261101_n16r24_s42/run.jsonl --out-json /tmp/a.json >/dev/null
python3 tools/metrics/r50_detail_position.py --log v2/evidence/r49-diversity-off-20261101_n16r24_s42/run.jsonl --out-json /tmp/b.json >/dev/null
cmp /tmp/a.json /tmp/b.json && echo DETERMINISTIC               # → DETERMINISTIC

# 2) 两臂对照 + MDE + R49 对账（§4 / §5 全部数字）
python3 tools/metrics/r50_calib.py \
  --off v2/evidence/r49-diversity-off-20261101_n16r24_s42/run.jsonl \
  --on  v2/evidence/r49-diversity-on-20261101_n16r24_s42/run.jsonl \
  --out-json v2/evidence/r50-calib-20261101.json
# → reconcile_all_match=True + 四行：
#   opener6            off=42/191(21.9895%) on=57/191(29.8429%)  d=+7.85pp  p=0.101829 MDE=10.7pp
#   first_clause       off=48/191(25.1309%) on=61/191(31.9372%)  d=+6.81pp  p=0.173801 MDE=11.4pp
#   first_clause_skip  off=112/191(58.6387%) on=146/191(76.4398%) d=+17.80pp p=0.000293 MDE=14.4pp
#   anywhere           off=187/191(97.9058%) on=191/191(100.0%)  d=+2.09pp  p=0.123034 MDE=6.5pp

# 2b) 确定性自证：重跑与入库 JSON 逐字节相等
python3 tools/metrics/r50_calib.py --off v2/evidence/r49-diversity-off-20261101_n16r24_s42/run.jsonl \
  --on v2/evidence/r49-diversity-on-20261101_n16r24_s42/run.jsonl --out-json /tmp/r50-recheck.json >/dev/null
sha256sum v2/evidence/r50-calib-20261101.json   # 88f9b79fd36d9eaa2c3a043ae08c8269b1322ab8f9d73dd7c03e738cc37ae39a
cmp /tmp/r50-recheck.json v2/evidence/r50-calib-20261101.json && echo CALIB_BYTE_IDENTICAL_TO_88f9b79f

# 3) §4.1 漏判条数（减法即得，脚本无此字段，用一条命令复算）
python3 - <<'EOF'
import json
d=json.load(open('v2/evidence/r50-calib-20261101.json'))
for a in ('off','on'):
    s=d['arms'][a]['strata']; miss=s['first_clause_skip']['num']-s['opener6']['num']; base=s['first_clause_skip']['num']
    print(a,'skip',base,'opener6',s['opener6']['num'],'miss',miss,'miss_rate',round(miss/base,4))
EOF
# → off skip 112 opener6 42 miss 70 miss_rate 0.625 / on skip 146 opener6 57 miss 89 miss_rate 0.6096

# 3b) §4.1 第三条证据：修正档是旧档严格超集（opener6 命中 ⇒ skip 必命中；反向漏判应为 0）
python3 - <<'EOF'
import importlib.util
spec=importlib.util.spec_from_file_location("r50","tools/metrics/r50_detail_position.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
for lbl in ("off","on"):
    log=f"v2/evidence/r49-diversity-{lbl}-20261101_n16r24_s42/run.jsonl"
    hm=hit=sk=n=0
    for b in m.collect_bodies(log):
        n+=1; s=m.strip_lead_paren(b)
        o=bool(m._DETAIL_RE.search(s[:m.OPENER_CHARS])); k=bool(m._DETAIL_RE.search(m.first_clause_skip(s)))
        hit+=o; sk+=k; hm+= (o and not k)
    print(lbl,"n",n,"opener6",hit,"skip",sk,"opener6_hit_but_skip_miss",hm,"superset",hm==0)
EOF
# → off n 191 opener6 42 skip 112 opener6_hit_but_skip_miss 0 superset True
# → on  n 191 opener6 57 skip 146 opener6_hit_but_skip_miss 0 superset True

# 4) distinct_body_ratio 退役依据（E1/E2/E3 读数）
python3 tools/metrics/lex_template_rate.py --log v2/evidence/r49-diversity-off-20261101_n16r24_s42/run.jsonl --label off
# → n_msgs=191 quant_hit=0/191 backref_hit=31/191 opener_top10_share=0.068063
python3 tools/metrics/lex_template_rate.py --log v2/evidence/r49-diversity-on-20261101_n16r24_s42/run.jsonl --label on
# → n_msgs=191 quant_hit=2/191 backref_hit=17/191 opener_top10_share=0.078534
python3 tools/metrics/lex_template_rate.py --log v2/evidence/r49-diversity-off-20261101_n16r24_s42/run.jsonl \
  --out-json /tmp/lex_off.json >/dev/null   # → distinct_body_ratio 191/191 = 100.00%
python3 tools/metrics/lex_template_rate.py --log v2/evidence/r49-diversity-on-20261101_n16r24_s42/run.jsonl \
  --out-json /tmp/lex_on.json  >/dev/null   # → distinct_body_ratio 191/191 = 100.00%

# 5) 真 LLM 验真 + run_batch.rc（§3.3）
cd code
python3 -m obs llm-cost --log ../v2/evidence/r49-diversity-off-20261101_n16r24_s42/run.jsonl --require-provider openai_compat; echo "rc=$?"
python3 -m obs llm-cost --log ../v2/evidence/r49-diversity-on-20261101_n16r24_s42/run.jsonl  --require-provider openai_compat; echo "rc=$?"
cd ..
cat v2/evidence/r49-diversity-off-20261101_n16r24_s42/run_batch.rc v2/evidence/r49-diversity-on-20261101_n16r24_s42/run_batch.rc   # 0 0
wc -l v2/evidence/r49-diversity-{off,on}-20261101_n16r24_s42/run.jsonl                                                          # 34102 34102

# 6) 接线（两态 prompt sha 必须不同）
python3 tools/r49/wiring_proof.py --code-root code        # → wiring_verdict=PASS

# 7) 截图三件套（本轮现渲，可重渲；rc=0 / ok=2 / fail=0）
python3 tools/metrics/render_shots.py --run-dir v2/evidence/r49-diversity-off-20261101_n16r24_s42 --batch-id R50-off --outdir v2/evidence/r50_shots --views chat,rhythm
python3 tools/metrics/render_shots.py --run-dir v2/evidence/r49-diversity-on-20261101_n16r24_s42  --batch-id R50-on  --outdir v2/evidence/r50_shots --views chat,rhythm
```

---

## 10. 三档口径声明（本轮只取实际达到的那一档）

| 档 | 本轮 | 依据 |
|---|---|---|
| **① 机制接通** | ✅ **已成立**（且这是 R49 的既有事实，本轮未新增跑批） | `wiring_verdict=PASS`（§3.2）；`HITT_D12_DETAIL=1` 见 `env_manifest.txt` |
| **①′ 尺子缺陷已定位并修正** | ✅ **已成立（观测级）** | 三条依据：①`opener6_hit_but_skip_miss=0/0` ⇒ 新档是旧档**严格超集**；②旧窗**近似等比压缩两臂**（压缩因子 `0.3750`/`0.3904`，相对漏判率 `62.50%`/`60.96%`，ON 并不更高）⇒ **Δ 被压掉 `9.95pp`（55.88%），仅保留 `44.12%`**；③OFF 基线 `p1` 被低估 **`36.65pp`**（`0.219895` → `0.586387`），连 MDE 的 `p1` 都取自被低估基线 ⇒ **旧窗测偏了绝对水位、并等比缩小了臂间差，而不是「低估某一臂」**；另：四档落盘、词表 sha 未变、R49 对账 `all_match=true`（§4.1） |
| **② 效果成立** | ⛔ **本轮不判** | 本轮**零新增跑批**，全部读数来自 `status=POST_HOC_DEVELOPMENT_SET_CALIBRATION` 的旧数据标定 ⇒ **开发集标定，不产生效果结论** |
| **③ 生活气息提升** | ⛔ **本轮不判** | 无人工盲评、无 judge 语义维度、无跨 seed 复现 ⇒ 无证据来源 |

**允许的表述**：「R49 的机制闸存在可复算的选点缺陷（旧窗口在两臂各漏判约 60% 的开口带物发言）；R50 已把它换成位置分层尺子并冻结了下一轮判据；**本轮为新尺子在已冻结旧数据上的开发集标定，不产生任何效果结论**。」
**禁止的表述**：「位置修正后 D12-A 有效 / 显著」「具体性插槽有效」「生活气息提升」「第一分句具体性显著上升」「R50 判据已通过验证」。

---

## 11. 本轮暴露的缺陷与遗留风险（**必须与结论同屏**）

1. **窗口参数事后调参（本轮最大方法论风险）**：`first_clause_skip` 的「≤2 个前导分句 / ≤8 字」是从 ON 臂失败样例反推的，属"按样例调窗口"。下一轮必须做敏感性矩阵（§8-5），否则这把闸的解释力无法自证。
2. **M1b 守卫强度不足**：只要求方向为正，无法排除"增益来自跳过动作"（§6-1，两档落差 10.99pp）。建议下一轮卡把 M1b 升级为「Δ ≥ +3pp」或将 `skip − first_clause` 的差值本身预登记为一致性判据。
3. **`no_cue` 地板差余量仅 7.91pp**（U7 阈值 10pp）：本轮 −2.09pp 未触发，但这一点对样本量变化敏感。
4. **`first_clause` 与旧 `opener6` 的 Wilson95 均重叠**（`p=0.174` / `p=0.102`）：只有放宽位置窗口后才出现区间不重叠的读数（`first_clause_skip`, `p=0.000293`）——**这本身就是"窗口决定结论"的直接证据**，也正是不能把标定当效果的原因。
5. **本报告的所有"成立"都限缩在观测级**，且**没有任何一行可以升级为效果结论**：本轮零新增 LLM 调用（`obs llm-cost` 复核仅针对 R49 既有日志），不涉及任何新的模型行为样本。
