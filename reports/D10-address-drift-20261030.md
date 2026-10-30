# D10 · C-A「称呼与关系演化」基线测量报告（零 LLM、纯文本尺子）

> **本报告性质**：**不跑新批、不调 LLM、不改运行时代码**。全部数字来自**已入库日志** + 新写的只读尺子。
> **作者**：life-texture-dev（生活气息实现工程师）
> **写作时间**：2026-10-30 18:03–18:10 +08:00
> **本轮分支 / HEAD（未提交前的基线）**：`feat/round-D10-address-drift` @ `fe7816cfa80900f8439817a6a7cfeb90e941b57e`（从 `feat/round-narration-hedge` HEAD 新开，不合 master、不 rebase）
> **审计状态**：**审计判决 PASS-with-caveat（2026-10-30 18:19），R1–R4 已整改**（改动落在 §8.1 / §8.2 / §4.2 / §10.5 / §5.1，整改 commit 见文末 §12）。整改前的 §8.1/§8.2/§4.2 **不得**被任何后续报告引用；引用整改后版本时请一并带上本行状态。
> **维度编号**：本报告用 `C-A` 指本轮维度（称呼与关系演化）。**不新造 `F-9` 之类编号**——`R4-life-texture.md:29-44` 是维度编号的唯一定义源，本轮不扩它。

---

## 0. 一句话结论（先读，避免把描述当因果）

1. **基线是可测的**：居民台词里「带称呼」的比例约 **31.9%–39.3%**（5 份日志，分母各 191 条 MSG），而「名字被提及」的比例高达 **81.2%–91.1%** —— **叫得出名字，但绝大多数时候不叫**（`addr_coverage` vs `addr_any_mention_rate`）。
2. **称呼"随相处时长演化"这一现象在当前配置下基本不存在**：同一有向关系内相邻称呼的**变化**在 3 份基线/近似基线日志里是 **0 次**（`0/11`、`0/15`、`0/22`）；`addr_stage_ordinal` 里 **绝大多数是「平」**（15/16、20/20、18/20 平），即「第一次怎么叫，最后一次还怎么叫」。
3. **两处同 `code_sha` 的对照臂里出现了变化**（`3/17 = 17.65%`、`4/19 = 21.05%`），**但其中 `4/19` 那一臂同时是模板红旗臂：`d9s-on` 的 `L-7` 8-gram 重复率 = `74.87%`（其余四份 20.94%–30.37%）** ⇒ 按 `R4:89` 陷阱2，这 4 次"称呼变化"**首选解释是模板轮换的副产品，不是关系演化**；且两臂干预都不是称呼（旁白轮换 / 句式起首）⇒ **只能当描述，不能归因**；Fisher 双侧 p 分别为 `0.2579` / `0.1130`，**都不显著**；而且两臂**缓存回放率本身不同**（`100.0% vs 98.1%`、`98.8% vs 92.7%`，§7.1）⇒ 连"同样条件下的差"都不成立。
4. **主判**：**「本规模下无法判定（因果）」**。可成立的只有基线描述：*称呼形式高度固定、几乎不随轮次演化；且每 100 次具名称呼里有 1.4–8.6 次叫错人（叫成自己或第三者）*。
5. **顺带发现的真问题（一级证据、可复算）**：`addr_error_rate`（自称 + 错称第三人）在 5 份日志 = **3.39% / 0.00% / 2.94% / 8.57% / 1.35%**（分母 59–74）。样例逐条见 §8.2 与 `v2/evidence/d10_address_drift/*.md` 的「3b. 称呼指向」表。

---

## 1. 假设与预登记

| 项 | 内容 |
|---|---|
| **H1（主假设）** | 若「关系亲近度会体现在称呼上」，则同一有向说话对（甲→乙）在**同一线程**内的称呼应随轮次单向变化，`addr_stage_ordinal` 的 `升/降` 应显著多于 `平`。 |
| **H0（零假设）** | 称呼只由固定人格模板决定，与相处时长/关系值无关 ⇒ `平` 占绝对多数、`addr_switch_rate ≈ 0`。 |
| **预登记判据（出数前写死）** | ① `addr_switch_rate(rate_scored)` 在基线 ≥ 30% 才算「称呼会变」；② `addr_stage_ordinal` 中 `升+降` 占比 ≥ 30% 才算「有方向性演化」；③ 分母 < 30 的一律只报事件数，不报百分比趋势（沿用 `R4-life-texture.md:79-83` 全族纪律）。 |
| **本轮判据状态** | ① 未达（基线最佳 0%，见 §5）；② 未达（基线 `升+降` 最多 1/16 = 6.25%）；③ **全程触发**：`addr_switch_rate` 分母 11–22、`addr_stage_ordinal` 分母 16–20，**都 < 30** ⇒ 下文所有百分比一律标注「分母 < 30，仅作描述，不作趋势」。 |
| **与 `R4:86-90` 三条陷阱的关系** | 陷阱1（景物≠生活气息）、陷阱2（塞词=套路）、陷阱3（编造事件优先级最高）：本维度**不写新提示词、不改代码**，故不引入新编造风险（陷阱3 不受影响）；但**必须**并列 `L-7` 8-gram 重复率防陷阱2（§6），并列 `F-1` 防假性相关。 |

---

## 2. 数据来源（5 份已入库日志，逐份给 sha256）

| key | 日志路径（仓库根相对） | `run.jsonl` sha256 | `code_sha`（meta） | 规模 | 模型 |
|---|---|---|---|---|---|
| `d9m-off` | `v2/evidence/d9m-ab-off_n16r24_s42/run.jsonl` | `5f1dda97633ccf0b3f7d2b279c39a43752db7d945a2ca6f9133e0b2bc9106ed5` | `3176048a39f0429204adbdb9eac7a975bfe10c72` | n16 r24 seed42 | DeepSeek-Flash / openai_compat |
| `d9m-on` | `v2/evidence/d9m-ab-on_n16r24_s42/run.jsonl` | `2edc751c5a32d1328ed5834ab169d29c5c457cbe7b1d5abe3146d7840df6a795` | `3176048a39f0429204adbdb9eac7a975bfe10c72` | 同上 | 同上 |
| `d9s-off` | `v2/evidence/d9s-off_n16r24_s42/run.jsonl` | `bd6623c209641bbeff1f72df6e0e843d756ef395eb7898571acf3dae0ad4be4c` | `05526e0d9ec9775876b6c7c5764fa70fa4c5b26a` | 同上 | 同上 |
| `d9s-on` | `v2/evidence/d9s-on_n16r24_s42/run.jsonl` | `0a50484d0fce2933fbc87bd20bedae93d8f3d1d233310d2a8c005d1e0bdef4d9` | `05526e0d9ec9775876b6c7c5764fa70fa4c5b26a` | 同上 | 同上 |
| `round1` | `v2/evidence/round1_narration_default_n16r24_s42/run.jsonl` | `ca108da9f90031f7d8b9dbc346518898e48976c33ec0965737ca80255cb6e37b` | `dfe6d5b283a9e37f9d3f2373e1b8224fd15d609f` | 同上 | 同上 |

**成对性（关键，否则会被误读成"臂间差=因果"）**：
* `d9m-off` / `d9m-on`：**同 `code_sha` `3176048`**，两臂只差**旁白示例轮换**开关（D9m）；
* `d9s-off` / `d9s-on`：**同 `code_sha` `05526e0`**，两臂只差**句式六类起首**臂（D9s）；
* `round1`：`code_sha dfe6d5b`，是**旁白默认化为 ON 之后**的另一棵树 ⇒ 与上面四份**不同代码**，只作「另一份快照」，不参与「同 sha 两臂」的差值叙述。

> ⚠ 三份不同 `code_sha` 之间**不得**写「复现/等价」，只能写「同量级/快照」（`CYCLE-33 §0.4` 纪律）。

---

## 3. 词表冻结（**先冻结、后出数**，时序可核）

### 3.1 冻结件

| 项 | 值 |
|---|---|
| 词表路径 | `v2/refs/address-ordinal.yaml` |
| 词表 sha256 | `dc4ce327ff8e0a77d34545903e8589ea97429a30c9b26bf0ed9d972eda122d95` |
| 词表字节数 / mtime | `4782` B / `2026-10-30 18:04:37 +0800` |
| 冻结回执 | `v2/refs/D10-address-freeze-receipt.txt`（`frozen_at_iso=2026-10-30T18:04:39+08:00`，内含同一 sha256） |
| 首次出数 | `2026-10-30T18:04:42+08:00`（v1 口径）；**现行口径 v3 出数** `2026-10-30T18:06:40+08:00`；汇总件 `summary.json` 的 `computed_at=2026-10-30T18:06:49+0800` |

### 3.2 时序证据（可原位重放）

```
$ sha256sum v2/refs/address-ordinal.yaml
dc4ce327ff8e0a77d34545903e8589ea97429a30c9b26bf0ed9d972eda122d95  v2/refs/address-ordinal.yaml

$ stat -c '%y %n' v2/refs/address-ordinal.yaml v2/refs/D10-address-freeze-receipt.txt v2/evidence/d10_address_drift/summary.json
2026-10-30 18:04:37.526908763 +0800 v2/refs/address-ordinal.yaml
2026-10-30 18:04:39.855725475 +0800 v2/refs/D10-address-freeze-receipt.txt
2026-10-30 18:06:49.100768448 +0800 v2/evidence/d10_address_drift/summary.json

$ cat v2/refs/D10-address-freeze-receipt.txt   # 摘
frozen_at_iso=2026-10-30T18:04:39+08:00
lexicon_sha256=dc4ce327ff8e0a77d34545903e8589ea97429a30c9b26bf0ed9d972eda122d95
first_measurement_pending=YES（写本文件时尚未对任何真实日志出数）
```

读数：**词表 mtime（18:04:37）< 回执（18:04:39）< 首次出数（18:04:42）< 现行出数（18:06:40）**。
✅ 词表在出数后**一字未改**（sha 与 `summary.json` 里记录的 `lexicon_sha256` 逐字符相同）。

### 3.3 有序性为什么是"判断"而不是"测量"（必须披露）

`v2/refs/address-ordinal.yaml` 里 5 档 tier 的排序（tier0 指代 → tier1 身份敬称 → tier2 亲属类推 → tier3 直呼其名 → tier4 伙伴式）是**作者的社区常识约定**，不是从数据统计出来的。因此：
* 本报告**同时**给出 `coarse_tiers` 粗粒度复算（粗疏 / 乡亲 / 近昵三档，把 tier2 独立一档、tier0+1 与 tier3+4 各自合并），见 §5 的 `coarse` 行；
* 反方可以主张 tier2 与 tier3 对调（"叫名比叫婶更亲"）。**若对调，`addr_stage_ordinal` 的 `升/降` 会整体反号，但 `平` 的占比不变** ⇒ 本报告的**主结论（"几乎不变"）对这张词表的排序不敏感**，这就是它可信的原因。

---

## 4. 口径（三口径 + 两次修订的完整披露）

### 4.1 三个口径（定义见 `tools/metrics/address_drift.py` 模块 docstring，出数前写死）

| 口径 | 单位 | 分子 | 分母 |
|---|---|---|---|
| `addr_vocab_per_pair` | **无向角色对** | 双方对彼此用过的**去重称呼形式数** | 该对之间 MSG 条数 ≥ 3 的角色对 |
| `addr_switch_rate` | **同线程 × 同说话人 × 同对象** 的相邻两条 | 两端都识别出称呼且**形式不同** | ①两端都识别出称呼的相邻对（`rate_scored`）；②全部相邻对（`rate_all`） |
| `addr_stage_ordinal` | **有向说话对**（speaker→addressee） | 首次/末次称呼的 tier，`delta=last-first` | 该有向对识别出 ≥2 次可判指向的称呼 |
| `addr_coverage` | per-message | 呼语位识别出称呼的 MSG | 全部 MSG |
| `addr_any_mention_rate`（**描述量，不参与主判**） | per-message | 正文任意位置出现称呼形式的 MSG | 全部 MSG |
| `addr_error_rate`（**描述量**） | 可判指向的具名称呼 | 叫成自己（`self_name`）+ 叫成第三者（`other_named`） | `target_ok + self_name + other_named` |

**呼语位规则**（写死在词表 §三）：命中位置前一字 ∈ {句首, ，。！？；：、“「…\n 空格 哎 喂 嗨 哟}，后一字 ∈ {，。！？；：、”」…\n 空格 啊 呀 哎 呢 吧 哈 嘛 **你 您**, 句末}；同句多命中取**最靠前**、**最长优先**。预处理：先剥「说话人标签前缀」（`阿林：` 这类格式伪影，仅当标签文本确实是某位居民基名才剥），再剥 `（…）` 括注（旁白通道不是台词）。

### 4.2 两次修订（**都会影响数字，全部披露，不藏**）

| 版本 | 时间 | 改了什么 | 为什么改 | 影响 |
|---|---|---|---|---|
| **v1** | `18:04:42` | 首版：`addr_switch_rate` 用「**同线程相邻两条**」（不分说话人）；无指向分类 | —— | 出现 `巧儿→金先生` 这类"变化"，实为**甲叫乙、乙叫甲**两条不同关系被当成一次变化 ⇒ **该口径测的不是"一个人怎么叫另一个人"** |
| **v2** | `18:05:39` | ① `addr_switch_rate` 改为**同线程 × 同说话人 × 同对象**；② 新增称呼**指向分类**（target_ok / self_name / other_named / unknown_target / generic） | v1 的分子被跨说话人对照污染；且发现"叫错人"是独立真问题 | **不可复算：v2 的中间产物未留档**（只存活在进程内存里，未落盘）⇒ 本条**不给任何数字** |
| **v3** | `18:06:40` | 剥离「说话人标签前缀」（`阿林：（…）周公文…` 会被误取成"阿林"） | 格式伪影被算成称呼 | `addr_error_rate` 相对 v2 下降（去掉了伪影）；**具体降幅不可复算**（v2 未留档） |

**v1 逐 run 实值（整改 R3：原表只写了一个 `10/10` 就归给"两个基线"，属归因错误，现逐 run 列）**

| run | v1 `switch` 分子/分母 | 出处（可原位重放） |
|---|---|---|
| `d9m-ab-off_n16r24_s42` | **10 / 10** | `v2/evidence/d10_address_drift/v1_preamend/d9m-ab-off_n16r24_s42.json` |
| `d9m-ab-on_n16r24_s42` | **14 / 14** | 同上目录 `…-ab-on…json` |
| `d9s-off_n16r24_s42` | **20 / 21** | 同上目录 `d9s-off…json` |
| `d9s-on_n16r24_s42` | **24 / 26** | 同上目录 `d9s-on…json` |

> 复核命令：`python3 -c "import json,glob;[print(f.split('/')[-1], json.load(open(f))['metrics']['addr_switch_rate']['n_switch'], '/', json.load(open(f))['metrics']['addr_switch_rate']['denom_scored_pairs']) for f in sorted(glob.glob('v2/evidence/d10_address_drift/v1_preamend/*.json'))]"`
> 读数：v1 的 `rate_scored` 在 4 份上是 `100.0% / 100.0% / 95.2% / 92.3%` —— 这组数**本身就是口径失效的证据**（称呼"变化率"接近 100% 显然不是关系演化），**不是**另一种可信结果。
> **原写「4–7/61–71」的那组数已删**：它是 v2 的 `addr_error_rate` 中间读数，**v2 未留档 ⇒ 不可复算**，不应出现在报告里。

> **口径最终态（一句话，请据此引用）**：**本报告正文所有口径数值一律由 `v3` 产出；`v1` / `v2` 已作废（仅作算法缺陷留痕，不是另一种结果），任何跨轮/跨报告引用只能复用 `v3`**。上面 v1 逐 run 的 `10/10、14/14、20/21、24/26` **只是被替换掉的缺陷读数**，**不得与 `v3` 的数值并列成"两个结果"**、更不得被引作"候选结论"；`v2` 连缺陷读数都没有留档（**不可复算**）。

**v1 的原始产物原样留档**：`v2/evidence/d10_address_drift/v1_preamend/`（含 `computed_at=2026-10-30T18:04:42+0800` 与 `tool_sha256=67ac488384d6259c46cc23c49e8ff1465dec875e0ab8322a9f289b9beb4a7707`），仅供复核"缺陷长什么样"，**不作任何结论依据**。
**词表 sha 三次出数完全相同**（`dc4ce327…`）⇒ 本轮**没有"事后调尺"**，改的是**尺子的算法缺陷**，不是量尺的刻度。
⚠ 本节自评：v1→v3 的三次改动发生在同一小时内、且都在首次出数之后完成 —— 这**降低了"预登记"的强度**。诚实说法：**本报告是「探索性测量 + 完整修订留痕」，不是严格预登记实验**；任何跨轮对比都应重跑 v3 口径，不要混用 v1 数字。

---

## 5. 结果（5 份日志，逐项带分母）

来源：`v2/evidence/d10_address_drift/summary.json`（sha256 `69a21d40443a3a64049793961a228a53b5007108da58b5e2e47a02a731d4b009`）/ `summary.md`（`31b53046fd371c95271b9d878ec506a024566f513ac9c0affe35666836b3289e`），由 `tools/metrics/d10_address_summary.py`（sha256 `46f431f1eb54120e06ea6099184037f99605e4e85fa4bc68e94b8ffe4669abb4`）生成。

### 5.1 主表

| key | arm | MSG | `cov%` | `mention%` | `vocab` 分母/均值 | `switch` 分子/分母A（%） | 分母B（`rate_all`%） | `stage` 分母（升/平/降） | `err` 分子/分母（%） | `F-1%` | `L-7%` | `L-12b%` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `d9m-off` | OFF | 191 | **31.94** | 81.15 | 19 / 1.579 | **0/11（0.00）** | 93（0.00） | 16（0/15/1） | 0+2/59（**3.39**） | 77.49 | 21.47 | 28.14 |
| `d9m-on` | ON | 191 | 36.65 | 85.34 | 19 / 1.684 | **3/17（17.65）** | 93（3.23） | 18（1/16/1） | 0+0/67（0.00） | 74.87 | 29.84 | 34.13 |
| `d9s-off` | OFF | 191 | 36.65 | 86.39 | 19 / 1.526 | **0/15（0.00）** | 93（0.00） | 20（0/20/0） | 2+0/68（**2.94**） | 73.30 | 30.37 | 34.13 |
| `d9s-on` | ON | 191 | 37.17 | 86.39 | 19 / 1.789 | **4/19（21.05）** | 93（4.30） | 18（0/17/1） | 5+1/70（**8.57**） | 73.82 | **74.87** | 35.93 |
| `round1` | 旁白默认 ON | 191 | 39.27 | 91.10 | 19 / 1.684 | **0/22（0.00）** | 93（0.00） | 20（1/18/1） | 1+0/74（1.35） | 75.92 | 20.94 | 35.93 |

> **脚注（审计 R5）**：`d9s-on` 有 **1 个 `vocab_size = 0` 的角色对**（`P002×P015`，5 条 MSG、0 条带称呼）**被计入均值**（分母 19、均值 1.7895）⇒ 该均值把"一对完全不称呼彼此"也算作一对，**是下界性质的均值**；若剔除，则该臂均值 = 34/18 = 1.8889。复核：`python3 -c "import json;d=json.load(open('v2/evidence/d10_address_drift/d9s-on_n16r24_s42.json'));print([r for r in d['metrics']['addr_vocab_per_pair']['rows'] if r['vocab_size']==0])"`

**分母纪律**：`switch` 分母 A = 11–22（< 30）、`stage` 分母 = 16–20（< 30）、`vocab` 分母 = 19（< 30）。
⇒ 按预登记判据③，**上表所有百分比只作描述，不得写成"趋势"或"提升/下降"**。

### 5.2 粗粒度敏感性（`coarse_tiers`）

`addr_stage_ordinal.coarse` 与细粒度**逐行同值**（本样本未出现"细粒度变了但粗粒度没变"或反之）：`d9m-off 0/15/1`、`d9m-on 1/16/1`、`d9s-off 0/20/0`、`d9s-on 0/17/1`、`round1 1/18/1`（顺序为 升/平/降）。
⇒ **主结论对 tier 排序不敏感**（见 §3.3）。

### 5.3 `addr_vocab_per_pair` 明细（`d9m-off`，19 对）

均值 **1.579**、中位 **1**、最大 **3**。分布形状（逐对见 `v2/evidence/d10_address_drift/d9m-ab-off_n16r24_s42.md`）：**19 对里 10 对只用过 1 种称呼、7 对用过 2 种、只有 2 对用过 3 种**（复核命令：`python3 -c "import json;from collections import Counter;d=json.load(open('v2/evidence/d10_address_drift/d9m-ab-off_n16r24_s42.json'));print(Counter(r['vocab_size'] for r in d['metrics']['addr_vocab_per_pair']['rows']))"` → `Counter({1: 10, 2: 7, 3: 2})`）；用满 3 种的只有 `P004×P013`（周公文/秀娘/铁头）与 `P011×P014`（小满/巧儿/巧儿姐）—— 且这两对里的第 3 种，一种是**错称**、一种是**来回摆动**（见 §8）。
⇒ 与 §0② 同向：**角色对的称呼词表几乎不扩张**。

---

## 6. 防陷阱并列（**读任何差值之前先看这三列**）

| 陷阱 | 并列指标 | `d9m-off` | `d9m-on` | `d9s-off` | `d9s-on` | `round1` |
|---|---|---|---|---|---|---|
| 陷阱2：变化可能只是模板轮换 | **`L-7` 8-gram 重复率** | 21.47% | 29.84% | 30.37% | **74.87%** | 20.94% |
| 假性相关 | `F-1` 非功能性闲聊占比 | 77.49% | 74.87% | 73.30% | 73.82% | 75.92% |
| 官方已有同族口径（一致性核对） | **`L-12b` 对方称呼率**（官方） | 28.14% | 34.13% | 34.13% | 35.93% | 35.93% |

**三条读法（必须与数字同时出现）**：
1. **`d9s-on` 的 `L-7 = 74.87%` 是红旗**：该臂句子重复度极高 → 它那 `4/19` 次"称呼变化"**很可能是模板轮换的副产品**，不是关系演化。这正是陷阱2 要拦的东西。
2. 本尺子的 `addr_coverage` 与官方 `L-12b` **口径不同、数值不同**（本尺子 31.9–39.3%，官方 28.1–35.9%）。差异来源：本尺子认**通用称呼**（师傅/老板…）+ 亲属类推派生式（`石叔`/`铁头哥`）与**称呼紧接第二人称**（`石叔你来了`）；官方 `L-12b` 只认「对方名字 + 后接标点/句末」。**两者不互相校验为"一致"**，只作**同向性**观察：本样本里两者同向（`round1` 都最高）。**不得**把任一方的数值当另一方的复现。
3. `F-1` 五份都在 73–77% 的窄带里 ⇒ **称呼覆盖率的变化与闲聊量没有同向关系**（`round1` 闲聊最高但变化数为 0），**不存在由 F-1 撑起来的假性相关**。

---

## 7. 与基线/另一臂的对比（量化结论 + 样本量 + 局限）

来源：`v2/evidence/d10_address_drift/summary.md` §「与基线/另一臂的对比」，Fisher 双侧精确检验由 `tools/metrics/d10_address_summary.py::fisher_exact_two_sided` 现算（纯 stdlib，可复算）。

| baseline | treatment | `switch`(baseline) | `switch`(treatment) | Δpp | Fisher 双侧 p | 能否归因 |
|---|---|---|---|---|---|---|
| `d9m-off` | `d9m-on`（同 `code_sha 3176048`） | 0/11 | 3/17 | +17.65 | **0.2579** | ❌ 不显著，且干预是**旁白轮换**、不是称呼 |
| `d9s-off` | `d9s-on`（同 `code_sha 05526e0`） | 0/15 | 4/19 | +21.05 | **0.1130** | ❌ 不显著，且干预是**句式起首**、不是称呼 |

**结论（一句话，整改 R4 后升级）**：**本轮没有"称呼干预臂"，所以不存在能归因的因果结论**。更硬的理由是两条同时成立：
① **Fisher 双侧都不显著**（`0.2579` / `0.1130`）；
② **两臂的缓存回放率还不相同**（`d9m-off 100.0%` vs `d9m-on 98.1%`；`d9s-off 98.8%` vs `d9s-on 92.7%`，见 §7.1）⇒ 连"在同一条件下只差一个开关"这个前提都不成立，`3/17`、`4/19` **连"同样条件下的差值"都算不上**，**不可归因**。
另：`d9s-on` 同时出现 `L-7 = 74.87%` 的模板红旗（其余四份 20.94–30.37%），按 `R4:89` 陷阱2 首选解释是模板轮换副产品。

### 7.1 缓存回放率（**已核验，且结论不利**；整改 R4 补入）

统计口径：`run.jsonl` 中 `type=LLM_CALL` 的事件，`payload.cached == true` 记一次回放；`tokens` = `tokens_in + tokens_out` 合计。

| key | LLM_CALL | cached | **cached%** | tokens 合计 |
|---|---|---|---|---|
| `d9m-off` | 2252 | 2252 | **100.0%** | **0** |
| `d9m-on` | 2252 | 2209 | 98.1% | 32 607 |
| `d9s-off` | 2252 | 2226 | 98.8% | 20 567 |
| `d9s-on` | 2252 | 2088 | 92.7% | 93 179 |
| `round1` | 2252 | 1387 | 61.6% | 310 960 |

复核命令（本报告作者实跑，与审计 §6.4 独立算出同一组数）：
```bash
python3 - <<'PY'
import json
for d in ['d9m-ab-off','d9m-ab-on','d9s-off','d9s-on','round1_narration_default']:
    n=c=ti=to=0
    for line in open(f'v2/evidence/{d}_n16r24_s42/run.jsonl'):
        r=json.loads(line)
        if r.get('type')!='LLM_CALL': continue
        n+=1; pl=r.get('payload') or {}
        if pl.get('cached'): c+=1
        ti+=pl.get('tokens_in') or 0; to+=pl.get('tokens_out') or 0
    print(f'{d}: LLM_CALL={n} cached={c} ({100*c/n:.1f}%) tokens={ti+to}')
PY
```

**三条读法（必须与上表同行）**：
1. `d9m-off` 是**纯缓存回放**（`cached=100%`、`tokens=0`）—— `F-58` 同族现象；这 5 份日志**不能当独立采样**，Fisher p 只对"这 5 份已落盘计数"成立。
2. **两处"同 `code_sha` 两臂"的缓存率并不相同**（100.0% vs 98.1%；98.8% vs 92.7%）⇒ 臂间差异里混着"命中率不同"这一层，这是**比"p 不显著"更强的不可归因理由**。
3. `d9s-on` vs `round1` 在 `summary.json` 里确有 `p = 0.0383` 已入库 —— **本报告不引用它作为"显著"**：它是 5 份日志两两比较（8 组）里的 1 组，属**多重比较**产物，未做任何校正；且这两份的缓存率（92.7% vs 61.6%）差 31pp。**故该 p 值不构成任何结论**。

**样本量与局限（必须同行披露）**：
* 每份日志 **191 条 MSG / 66 线程 / 22 轮（16 agents, seed 42）**；`switch` 可评分分母仅 **11–22**，`stage` 分母 **16–20**。**这是"很小"的样本**，任何百分比都不稳定（1 次事件 = 5–9pp）。
* 单 seed（42）、单规模（n16 r24）、单模型（DeepSeek-Flash）⇒ **不可外推到其他 seed/规模/模型**。
* 缓存回放率 **61.6%–100%**（§7.1）⇒ **不主张"两次采样独立"**；Fisher p 只对"这 5 份已落盘日志的计数"做精确检验，**不代表对"模型随机性"做推断**。

---

## 8. 案例与截图（**二级证据，仅可读性佐证，不作结论依据**）

### 8.1 选图规则（写清，避免 `F-70` 非分层抽样那个坑）

1. **候选池** = 5 份受检日志中「同一有向关系内称呼发生**变化**」的**全部**事件：`d9m-on` 3 条 + `d9s-on` 4 条 = **7 条**（池子小是因为基线里没有变化）。
2. **筛选条件**：① 必须能在**单一日志**内完整渲染（禁止跨批/跨 run 拼接）；② 优先「同一线程内**至少 2 次**变化」的样例（能看出来回，而不是一次跳变）。
3. **满足②的候选有 2 条（不是 1 条）**，**我在两者中做了选择**：

| 候选 | 线程 | 变化链 | 是否选入 | 选/弃理由 |
|---|---|---|---|---|
| **A** | `d9m-on` `TH-P013-P004-15` | `铁头`（seq 22638, r16）→ `铁头哥`（24741, r19）→ `铁头`（30028, r22） | ✅ **选入** | 所在臂 `L-7` 8-gram 重复率 = **29.84%**（与其余非红旗臂同量级），模板污染风险低 |
| **B** | `d9s-on` `TH-P001-P009-12` | `老周`（seq 20830）→ `金先生`（22969）→ `老周`（25311） | ❌ 弃用 | 所在臂 `L-7` = **74.87%**（模板红旗，陷阱2）⇒ 该线程的"称呼来回"**无法排除是模板轮换的产物**，作为案例会把红旗当结论 |

> **整改说明（原写法错误，已删）**：本节原写「满足②的只有 1 条……无挑拣余地」——**这是事实错误**（漏看了候选 B）。真实情况是 **2 个候选、我选了 A**；A 的理由是**其所在臂没有模板红旗**，不是因为"别无选择"。审计（R1）指出"别无选择"是最典型的自欺句式，此处按整改要求改写成"做了选择 + 放弃理由 + 被放弃候选的完整定位"。
> 复核命令（可原位重放，两条都列出来）：
> ```bash
> # 候选 A / B 的 4 次变化事件（v3 口径 addr_switch_rate.examples）
> python3 -c "import json;[print(f, json.dumps(json.load(open(f))['metrics']['addr_switch_rate']['examples'],ensure_ascii=False)) for f in ['v2/evidence/d10_address_drift/d9m-ab-on_n16r24_s42.json','v2/evidence/d10_address_drift/d9s-on_n16r24_s42.json']]"
> # 两臂 L-7（决定弃用 B 的那一列）
> python3 -c "import json;d=json.load(open('v2/evidence/d10_address_drift/summary.json'));print([(r['key'],r['flat']['L7_pct']) for r in d['runs']])"
> ```

### 8.2 该样例原文（一级证据；**摘录——原文含 `（…）` 括注旁白，为可读性省略，全文见 `run.jsonl` 对应 seq**）

```
seq 22638  r16  P004(秀娘) -> P013(铁头)：铁头，我这儿也紧着呢，面粉铺老周说下午才到货，我先把这笼豆沙包蒸上顶一顶。你吃没？
seq 24741  r19  P004(秀娘) -> P013(铁头)：铁头哥，灶上那锅红糖发糕正发着，我腾不开手，这俩包子你先揣着垫垫肚子吧。
seq 30028  r22  P004(秀娘) -> P013(铁头)：铁头，你等会儿去老赵家，顺道帮我把这屉新蒸的枣泥糕捎给巷尾张婶…
```

**全文（含括注旁白，逐字，整改 R2 后补全）**：

```
seq 22638  r16  P004(秀娘) -> P013(铁头)：
（掀开蒸笼盖，白汽扑了满脸，手里还捏着给赵家孙子留的豆沙包）铁头，我这儿也紧着呢，面粉铺老周说下午才到货，我先把这笼豆沙包蒸上顶一顶。你吃没？
seq 24741  r19  P004(秀娘) -> P013(铁头)：
（掀开蒸笼盖，白汽扑了满脸，拿竹夹子夹起两个豆沙包搁进粗瓷碗）铁头哥，灶上那锅红糖发糕正发着，我腾不开手，这俩包子你先揣着垫垫肚子吧。
seq 30028  r22  P004(秀娘) -> P013(铁头)：
铁头，你等会儿去老赵家，顺道帮我把这屉新蒸的枣泥糕捎给巷尾张婶，她家小孙子昨儿还念叨呢。（掀开笼屉，白汽扑了满脸，拿油纸包了两块往他碗边搁）
```

> **整改说明（R2）**：本节原标"逐字取自日志"，但上面那个代码块其实删掉了三条的括注旁白且没加省略号 ⇒ 标注与内容不符。现在**两种都给**：摘录块（明确标"省略括注"）+ 全文块（逐字）。称呼形式（`铁头`/`铁头哥`/`铁头`）在两版中一致。
> 复核命令：`python3 -c "import json;[print(json.loads(l)['seq'], json.loads(l)['payload']['body']) for l in open('v2/evidence/d9m-ab-on_n16r24_s42/run.jsonl') if json.loads(l).get('seq') in (22638,24741,30028)]"`

读数：**同一线程内先升（tier3→tier2）再降（tier2→tier3）**。
⇒ 这解释了 §5 为什么 `stage` 几乎全是「平」：**称呼变化是"来回摆动"，不是单向演化**；`delta = 首末差 = 0`，但 `switch = 2`。**这是本维度最该被记住的一条口径差异**（`stage` 单调口径会漏掉摆动，`switch` 才能看见）。
⚠ 同一条变化里还夹着"铁头哥"这种**亲属类推**是否真表示更亲，本身依赖 §3.3 的词表判断。

### 8.3 截图（三件套齐全）

| 图 | 路径 | PNG sha256 | 说明 |
|---|---|---|---|
| **主图（单线程视图）** | `v2/evidence/d10_address_shots/D10-addr-subset-chat-TH-P013-P004-15-2edc751c.png` | `138d23d9fc932ee2e384c3c44cbde53d1127c0059c2dcb8e77682fd84350d575` | 目标线程 6 条全可见，「铁头 → 铁头哥 → 铁头」肉眼可核 |
| 全批默认视图（对照） | `v2/evidence/d10_address_shots/D10-addr-chat-2edc751c.png` | `9044b2ad88f829cf23b1027fa06ee0643099a2256118c41e077013cd81b505e1` | 渲染链路可用性佐证；页面默认落在别的线程 |
| `thread=` 参数尝试 | `v2/evidence/d10_address_shots/D10-addr-thread-chat-TH-P013-P004-15-2edc751c.png` | `fe385ad84854c2714e613d8d864bcce078c5ed2bcc2ff61459188ed1776d796d` | **失败留档**：前端 `thread=` 只展开列表卡片、不切换首屏，实测与全批默认图同内容 ⇒ **此图不作证据** |

三件套（逐张写在 `render_report_D10-addr*.json`）：
* ① 来源 run 目录：`v2/evidence/d9m-ab-on_n16r24_s42`；
* ② 日志 sha256：`2edc751c5a32d1328ed5834ab169d29c5c457cbe7b1d5abe3146d7840df6a795`（与主表 `d9m-on` 逐字符一致）；
* ③ 渲染命令原文（主图）：

```bash
python3 tools/metrics/d10_thread_shot.py \
  --run-dir v2/evidence/d9m-ab-on_n16r24_s42 \
  --batch-id D10-addr-subset --thread TH-P013-P004-15 --subset-thread \
  --outdir v2/evidence/d10_address_shots --timeout 180
# 内部真实链路（与 tools/metrics/render_shots.py 同一条，未改它）：
#   code/frontend/tools/gen_threads.py --log …/run.jsonl --meta …/meta.json --out …/threads_D10-addr-subset_subset1.json --label D10-addr-subset
#   code/frontend/tools/shot.py --url http://127.0.0.1:<port>/dialogue.html?still=1&multi=1&min=0&sort=turns&data=sample/dialogue_D10-addr-subset/threads.json --width 1400 --height 900
```

**必须披露的裁剪**：主图用的是 `--subset-thread`——把该批 `threads.json` 的 `threads[]` **过滤成只含目标线程**（`761042 → 6 条消息`，消息正文**逐字节未改**；过滤前后的线程数/消息数写在 `render_report_D10-addr-subset_TH-P013-P004-15.json` 的 `subset_filter` 字段）。
页面顶部批次级计数（191 条消息 / 16 人 / 24 轮）**仍是全批值**，不随过滤变化 —— 这不是"拼图"、也不是"跨批混拼"，但**确实是裁剪**，故在此明写。
渲染前已 `pgrep` 确认无跑批在跑；渲染全链路只读，未改 `code/` 任何文件。

> **使用边界（硬约束）**：本节截图**只能放在案例区**作"该线程可读性"佐证，**不得**作为"居民日常就是这样"的插图或封面图放进 §0 / §9 的结论段 —— 它是**单线程裁剪渲染**，页面顶部计数仍是全批值，且 6 条原文本身在 `run.jsonl` 里可逐字核对（那才是一级证据）。

---

## 9. 结论（严格按证据分层）

**能成立的（描述层，一级证据）**
1. `addr_coverage` = **31.94% / 36.65% / 36.65% / 37.17% / 39.27%**（分母各 191），而 `addr_any_mention_rate` = **81.15% / 85.34% / 86.39% / 86.39% / 91.10%** ⇒ **"名字常被提到、称呼很少用"**，落差 45–52pp。
2. 同一有向关系内称呼变化：**0/11、3/17、0/15、4/19、0/22**；`stage` 中「平」占比 **15/16、16/18、20/20、17/18、18/20** ⇒ **称呼不随轮次演化**，H0 与数据一致，**H1 未获支持**。
   **同一段必须连读的模板红旗**：`4/19` 来自 `d9s-on`，该臂 `L-7` 8-gram 重复率 = **74.87%**（其余四份 20.94%–30.37%，差 44–54pp）⇒ 这 4 次"变化"**按陷阱2 首选解释为模板轮换副产品**，**不计入任何"称呼会演化"的证据**；基线三份的 `0/11、0/15、0/22` 不受此红旗影响（同臂 `L-7` 为 21.47% / 30.37% / 20.94%）。
3. 具名称呼中叫错人（自称+错称第三者）：**3.39% / 0.00% / 2.94% / 8.57% / 1.35%**（分母 59–74）⇒ **每 100 次具名称呼 1.4–8.6 次叫错**。

**不能成立的（本报告不做的主张）**
4. 不能说「旁白/句式臂让称呼变好了/变坏了」：**Fisher p = 0.2579 / 0.1130（不显著）** **且**两臂缓存回放率不同（`d9m-off 100.0%` vs `d9m-on 98.1%`；`d9s-off 98.8%` vs `d9s-on 92.7%`，§7.1）⇒ **差值连"同样条件下的差"都不算，不可归因**；何况两臂干预都不是称呼。（`summary.json` 里 `d9s-on` vs `round1` 的 `p=0.0383` 属 8 组两两比较中的 1 组，**多重比较产物，本报告不引用为显著**。）
5. 不能给「关系值 → 称呼亲密度」的因果或相关系数：本轮**没有**把 `RELATION_CHANGE` 事件与称呼序列对齐（日志里有 3115 条 `RELATION_CHANGE`，但未做映射）——**这是明确的下一步，不是已完成的工作**。
6. `F-7b`（编造事件率）在本轮仍为 `None` ⇒ 任何"称呼变多/叫错人不带来编造"的说法**均不成立**（`R4:90` 陷阱3）。

**给下一轮的建议（不是承诺）**
* 若要把 C-A 推成**能判因果**的维度，需要：① 写 `LIFE_PROMPT_ADDR_EVOLVE` 开关（默认 OFF，OFF 与现状逐字节等价）；② 同 `code_sha` 的 OFF/ON 两臂；③ 规模至少 n16 r84（把 `switch` 分母从 ~15 抬到 ~60 以上）；④ 出数前把 `addr_stage_ordinal` 的单调口径**换成"摆动计数"**（本轮已证明单调口径会漏）。
* 已经可以直接做的低风险修：`addr_error_rate` 那一族（叫错人）可以直接接到 `L-10 self_address_error` 官方口径上做对拍。

---

## 10. 局限与不可复算项清单（引用本报告时必须同行）

1. **样本极小**：`switch` 分母 11–22、`stage` 分母 16–20、`vocab` 分母 19，全部 < 30 ⇒ 百分比只描述，不趋势（预登记判据③）。
2. **非严格预登记**：词表确实先冻结后出数（§3.2 时序可核），但**尺子算法在出数后改了两版**（§4.2），v1 产物留档在 `v1_preamend/`。跨轮复用请只用 v3 口径。
3. **`code_sha` 不一致的三份不可比**：`round1`（`dfe6d5b`）与两组臂（`3176048` / `05526e0`）是不同树；本报告只写"同量级/快照"。
4. **称呼识别是规则式，不是语义式**：转述、引语、方言变体（如「哎，那谁」）与未收录的称呼形式会被漏判；`addr_coverage` 因此是**下界**。反过来，「周公文啊，我把上月工资单…」这类**自称口吻**会被判成 `self_name`（本报告按"叫成自己"计，属口径选择，非事实争议）。
5. **缓存回放率已核验（整改 R4），且结论不利**：`d9m-off 100.0%（tokens=0）`、`d9m-on 98.1%`、`d9s-off 98.8%`、`d9s-on 92.7%`、`round1 61.6%`（§7.1）。**两处同 sha 两臂的缓存率互不相同** ⇒ "两次采样独立"不成立、臂间差值不可归因。原写"未核验"已按审计实测升级为数字。
6. **截图是二级证据**：主图经过 `threads[]` 过滤（§8.3 已披露）；图上气泡末尾的 `#编号` 不可作 `seq` 依据（`F-71` OCR 幻觉，`CYCLE-32/33` 连续复现），一切以 `run.jsonl` 的 `seq` 为准。
7. **`v2/evidence/d3_noiseband_bootstrap.json` 磁盘现值被工作区改写**（`denom 480→341`、`±3.75→±4.4pp`，属他人在途）⇒ 本报告**未引用任何噪声带**；若后续要判"差值是否超过噪声底"，必须先用**已入库版本**重算，磁盘现值**存疑**。
8. **未做的事**（别把没做的当做了）：没有新跑批、没有任何 LLM 调用、没有实现 `LIFE_PROMPT_ADDR_EVOLVE`、没有把 `RELATION_CHANGE` 与称呼对齐、没有做人工双读者 κ、没有扩 `F-9` 编号。

---

## 11. 复算命令清单（原文，逐条可原位重放）

```bash
# 0) 位置与身份
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
git rev-parse --abbrev-ref HEAD && git rev-parse HEAD     # 见 §0 头部：feat/round-D10-address-drift @ fe7816c…
pgrep -af "orchestration run|run_batch|nightly\.py"       # 出数与渲染前各跑一次，均应无命中

# 1) 词表身份（只读；sha 应与 §3.1 一致）
sha256sum v2/refs/address-ordinal.yaml
cat v2/refs/D10-address-freeze-receipt.txt

# 2) 尺子自检（10 条呼语位用例 + 3 条端到端用例；rc=0 才算过）
python3 tools/metrics/address_drift.py --selftest

# 3) 单份日志出数（逐份；下面以 d9m-off 为例，其余同形）
python3 tools/metrics/address_drift.py \
  --log v2/evidence/d9m-ab-off_n16r24_s42/run.jsonl --arm OFF \
  --out-json v2/evidence/d10_address_drift/d9m-ab-off_n16r24_s42.json \
  --out-md   v2/evidence/d10_address_drift/d9m-ab-off_n16r24_s42.md

# 4) 5 份汇总 + 官方 F-1/L-7/L-12b 并列 + Fisher 精确检验
python3 tools/metrics/d10_address_summary.py \
  --run d9m-off=OFF=v2/evidence/d9m-ab-off_n16r24_s42/run.jsonl \
  --run d9m-on=ON=v2/evidence/d9m-ab-on_n16r24_s42/run.jsonl \
  --run d9s-off=OFF=v2/evidence/d9s-off_n16r24_s42/run.jsonl \
  --run d9s-on=ON=v2/evidence/d9s-on_n16r24_s42/run.jsonl \
  --run round1=ROUND1_NARR_ON=v2/evidence/round1_narration_default_n16r24_s42/run.jsonl \
  --out-dir v2/evidence/d10_address_drift
# 官方口径单独复核（汇总器内部就是调它；可手工再跑一遍）
python3 tools/d5/dialogue_metrics.py --log v2/evidence/d9m-ab-off_n16r24_s42/run.jsonl --out-json /tmp/dm_off.json

# 5) 截图（二级证据）
python3 tools/metrics/render_shots.py \
  --run-dir v2/evidence/d9m-ab-on_n16r24_s42 --batch-id D10-addr \
  --outdir v2/evidence/d10_address_shots --views chat --timeout 180 --retry-blank 2 --blank-check shot
python3 tools/metrics/d10_thread_shot.py \
  --run-dir v2/evidence/d9m-ab-on_n16r24_s42 \
  --batch-id D10-addr-subset --thread TH-P013-P004-15 --subset-thread \
  --outdir v2/evidence/d10_address_shots --timeout 180
sha256sum v2/evidence/d10_address_shots/*.png
```

**本轮新增/改动文件（逐项，全部为新增，未改任何既有文件）**
| 文件 | 性质 |
|---|---|
| `v2/refs/address-ordinal.yaml` | 新增：冻结词表 |
| `v2/refs/D10-address-freeze-receipt.txt` | 新增：冻结回执（时序证据） |
| `tools/metrics/address_drift.py` | 新增：三口径尺子 + `--selftest` |
| `tools/metrics/d10_address_summary.py` | 新增：汇总 + 官方口径并列 + Fisher |
| `tools/metrics/d10_thread_shot.py` | 新增：指定线程渲染（复用 `render_shots.py` 链路，未改它） |
| `v2/evidence/d10_address_drift/**` | 新增：出数产物（含 `v1_preamend/` 留档） |
| `v2/evidence/d10_address_shots/**` | 新增：3 张真实 PNG + 2 份 `render_report` + threads.json |
| `reports/D10-address-drift-20261030.md` | 新增：本报告 |

**未改动/未提交**：`code/` `life/` `orchestration/` `config/` `engine/` 一字未动；工作区他人 3 个 `M`（`tools/metrics/weather_readings.py`、`v2/evidence/d3_noiseband_bootstrap.json`、`v2/evidence/d9f_dr_on_mock_result.md`）与其余未跟踪条目**均未 add、未提交**。

---

## 12. 审计整改记录（PASS-with-caveat → 待升 PASS）

审计件：`team-workspace/audit/round-D10-audit.md`（判决 **PASS-with-caveat**：数字层 55 格全过，sha/复算/伪预登记/截图全过）。下列整改**只改本报告文本**，未重跑任何数、未改任何代码与证据文件。

| # | 审计要求 | 落点 | 改成了什么 |
|---|---|---|---|
| **R1（必修）** | §8.1「只有 1 条 / 无挑拣余地」是事实错误 | §8.1 | 改成**候选 2 条**：`d9m-on TH-P013-P004-15`（选入）与 `d9s-on TH-P001-P009-12`（弃用，理由：所在臂 `L-7=74.87%` 模板红旗）；给出两条的完整定位、选择理由、复核命令；"别无选择"句式已删 |
| **R2（必修）** | §8.2「逐字取自日志」不成立（括注被删且无省略号） | §8.2 | 拆成两块：**摘录块**（明确标"省略 `（…）` 括注旁白"）+ **全文块**（三条 seq 22638/24741/30028 逐字含括注）；附复核命令 |
| **R3（必修）** | §4.2 归因串味 + v2 不可复算 | §4.2 | v1 改**逐 run 实值** `10/10、14/14、20/21、24/26`（附复核命令与出处文件）；v2 行标注**「不可复算：中间产物未留档」并删除 `4–7/61–71` 那组数** |
| **R4（要求做）** | 补缓存回放率表，结论升级 | §7.1（新增）+ §9④ + §10 第 5 条 | 新增 5 行缓存表（`100.0% / 98.1% / 98.8% / 92.7% / 61.6%`，本作者实跑复现审计数）；结论升级为「Fisher 不显著 **且** 两臂缓存率不同 ⇒ 差值不可归因」；明确 `d9s-on vs round1 p=0.0383` 属多重比较产物、**不引用为显著** |
| **R5（可选）** | `d9s-on` 有 1 个 `vocab_size=0` 的角色对计入均值 | §5.1 脚注 | 加脚注：`P002×P015`（5 条 MSG、0 条带称呼）计入分母 19；剔除后该臂均值 = 34/18 = 1.8889 ⇒ 现值为下界性质 |
| 状态标注 | 报告顶部加一行审计状态 | 文件头 | 新增「审计状态」行：PASS-with-caveat、R1–R4 已整改、整改前 §8.1/§8.2/§4.2 不得被引用 |

**整改后仍未做/仍不成立（不变）**：因果不可判；「趋势/提升」表述一律不成立（分母 <30 + 缓存回放 61.6–100%）；`F-7b` 仍为 `None`。
