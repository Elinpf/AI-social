# R46 · C1 处境锚：效果层「生活气息」指标定档与两臂读数（0 新增跑批）

- 报告编号：R46
- 维度：C1「处境锚」（`LIFE_PROMPT_SCENE`）——缺口 A「对话里没有我在哪、手上干什么」
- 批次：`c1-scene-a0-20261101_n16r24_s42`（OFF） / `c1-scene-a1-20261101_n16r24_s42`（ON）
- 起跑树锚：`code_sha = 8b64615b0c717a5a42db8d40ae9fff5b469cfe7d`（两臂同树）
- 判据：`v2/refs/C1-scene-prereg-20261101.md`（判据先于数据，**本报告未改任何阈值**）
- 新增尺子：`tools/metrics/c1_effect_metrics.py`（M2~M4 辅助读数；M1 直接复用冻结尺子）
  ＋ `tools/metrics/c1_anchor_stale_check.py`（**零依赖独立复核器**，只读 `run.jsonl`，供他人复现 87/191）
- 分支：`feat/r46-c1-effect-metrics`（本地新建，**未 commit、未 push**，由 run-observer 统一交付）
- 冻结区改动：`git status --porcelain -- code/life code/orchestration code/config code/engine` = **0 行**
- 数据源：**仅两臂 `run.jsonl`**；**未读任何 side_root**（A0 side_root 被 A1 attempt1 误写 211 文件，污染发生在 A0 收批之后）

---

## 0. 四条并列主结论（定稿口径，引用本报告时四条必须一起出现）

> 定稿人：`run-observer`（跑批验证与证据报告官，独立复核者）。数据锚：两臂 `code_sha = 8b64615b0c717a5a42db8d40ae9fff5b469cfe7d`。复核证据文件：`v2/evidence/c1-scene-verify-20261101/R3-VERIFY-EVIDENCE.md`。

| # | 结论 | 关键数字 | 状态 |
|---|---|---|---|
| 1 | **机制接通** | A1 `ctx.scene` 覆盖率 **0.0000 → 1.0000（191/191）** | 已验证 |
| 2 | **成本可测** | `openai_compat` 真调用 **2255 calls**、`degraded=0`、`provider_guard.ok=true`；`dialogue` 用途 **调用数 193↔193 不变**、`tokens_in 63305 → 73040（+15.4%）** | 已验证 |
| 3 | **效果层按预登记判据不成立（`probe` 级，单批单 seed，不外推）** | A0 `58/174=0.3333` vs A1 `56/165=0.3394`，**Δ=+0.61pp**（线 ≥+15pp）、rate(A1) `0.3394`（线 ≥0.55）、Fisher `p=0.9090`；五条不可判条件均未触发 | 已验证（双人独立复算一致） |
| 4 | **根因定位（两个性质不同的缺陷）** | ①**被测对象**：锚点 **87/191 = 45.55%** 指错场所，87/87 由"同轮内先移动、锚点取移动前快照"解释；②**测量工具**：`place_content_consistency` **不区分"提到"与"在做"**（纯子串匹配；A1 cafe 26/2、park 17/1、plaza 15/2） | 已验证 |

### 0.1 结论口径：**双重未定**

1. **被测对象不干净**：锚点时序缺陷使本轮注入内容有 45.55% 是「上一站」；
2. **测量工具不干净**：尺子不区分"提到/在做"，在闲聊型场所系统性偏负（两臂同型低水位 ⇒ 是尺子性质）；
3. **两者叠加 ⇒ 本轮既不能判「有效」，也不能判「无效」**，只能说：**该假设尚未获得公允检验。**

> **唯一允许的措辞**：「本轮实现存在可定位缺陷（锚点时序 + 尺子偏差），该假设尚未获得公允检验。」
> **禁止的三种写法**：✗「场景锚方向无效」；✗「场景锚有效，只是被 bug 埋没了」；✗「修好锚点就能过线」。
> 关于第三种的进一步约束：§5.5 的「乐观上界 A1≤0.4111」是在**"尺子有效"前提下**做的算术，而 §7 已证明尺子效度存疑 ⇒ 该上界**只能**读作「在现有尺子口径下，即使给错位子集最乐观的假设，读数仍不过线」，**不得**读作「真实一致率只有 0.41」，更**不得**推出「修好也达不到 0.55」。

### 0.2 团队纪律（本轮新增，写在正文不是脚注）· 转述数字必须先自跑

> **纪律（三半，缺一不可）**：
> 1. **数字要自己跑一遍**（别信别人转述的）；
> 2. **也别信自己没跑过的直觉**（例：`repo-scout` 自查出 `actor` / `payload.agent_id` **取键 bug**，同一口径改键后数字就变——取键这种事都能改数）；
> 3. **数字必须连定义一起落盘**（同一个 `12` 在三种变体下指向三件不同的事；只写数字不写定义 = 不可复算）。
>
> **来历（本轮真实代价）**：我在 §5.2/§10.1 写过「朴素写法会产生**约 12 条**假反例」，那是**转述 teammate 提示、当时没有自跑**。repo-scout 复算重现不出 12；我自己跑变体在 **104 / 0** 之间摆动（其中另一个被转述的 **89** 我**未能复现**，见 §12.3 表第 3 行，登记为待核项），最终把该数字**撤回**，改用可复算的 **104 条**（= 无本轮移动的对话条数）。
>
> **冻结令（team-leader 2026-11-01 12:20）**：`12 / 104 / 87 / 75` 四个数自定稿起冻结，不再调整措辞，除非 R7 审查拿出反证。理由：这组数字已走过「12 → 撤回 → 104 → 12（含义不同）」四步，继续改动会让读者怀疑整份报告的数字纪律——那比数字本身更伤。
>
> **为什么这条值得占正文位置**：报告里最贵的东西不是结论，是**别人敢不敢引用**。一个转述来的数字若跑不出来，整份报告的可复算性都会被读者合理怀疑；而一条"撤回 + 给出可复算替代值 + 公开勘误"的记录，反而把可信度补回来了。所以这条纪律的执行标准是：**宁可报告里少一个数字，也不留一个别人跑不出来的数字。**

---

## 1. 一句话结论

**预登记主指标（M1 处所-内容一致性率）判「不成立」**：Δrate(A1−A0) = **+0.61pp**（远低于 +15.0pp 通过线），A1 一致率 0.3394 也低于 0.55 下限，Fisher 精确检验 p = 0.9090。

但**「不成立」不等于「处境锚这个机制没价值」**——本轮新增的 M2 读数给出了另一个更可能的解释：**A1 注入的处境锚有 45.55%（87/191）指错了地方**，且这 87 条**全部（100%）**可由「本轮内先移动到新场所、再在新场所说话，而锚点取的是移动前的场所」这一确定性时序解释。也就是说：模型被告知的处境，近一半是**上一站**。

因此本轮的**真实信息增益不在"效果没出来"，而在"为什么没出来"**：这不是一个需要更多跑批的悬念，而是一个**已定位到行号级别的实现缺陷**（见 §5 独立成果、§9 建议）。

> **口径定稿（唯一允许的表述，三种说法之外不要再写别的）**：
> **本轮实现存在可定位缺陷（锚点时序 + 尺子偏差），该假设尚未获得公允检验。**
>
> 不得写「场景锚方向无效」；不得写「场景锚有效、只是被实现 bug 埋没了」；也不得写「生活气息提升/下降」。
> 前两句都预设了方向，本轮数据不支持任何方向；第三句只陈述"检验未完成"这一事实。

### 1.1 对 Leader 三问的直接回答

| 问题 | 回答 |
|---|---|
| 尺子测的是不是本轮场景锚想改善的东西？ | **不是同一件事，且错位是系统性的**。尺子判的是「正文提到的活动域是否与该场所相容」，而居民在闲聊型场所大量是**提及别处**正在做的事（"我灶上还炖着汤"）。见 §7。 |
| 是"场景锚没效果"还是"尺子没测到该测的"？ | **两者都有，但主因是第二个 + 输入本身有缺陷**：① 锚点有 45.55%（87/191）指错地方（§5，且 100% 可由同轮内移动解释）；② 尺子的"提及=在做"这一前提在 cafe/park/plaza 系统性出负（§7）。**不能**由 M1 的"不成立"推出"处境锚无用"。 |
| 这批数据能否支撑任何效果层结论？ | **对"生活气息是否提升"——不能。** 能支撑的只有三件事：机制接通、成本可测、锚点缺陷定位（见 §1.2）。 |

### 1.2 这批数据**能**支撑 / **不能**支撑什么

**能支撑（可复算、有证据）**：
1. 机制接通：`ctx.scene` 覆盖 A0 0/191 → A1 191/191（payload 级证据，不依赖 meta）。
2. 成本可测：两臂 `obs llm-cost` 均 `provider_guard.ok = true`、2255 calls、`degraded = 0`；leader 侧的 dialogue tokens_in 63305 → 73040（+15.4%）与本报告数据源一致。
3. **锚点缺陷定位**：A1 的处境锚 87/191 与消息实际场所不一致，87/87 由「同轮内先到达后说话」解释 ⇒ 实现层确定性时序问题。

**不能支撑（本轮明确不结论）**：
1. 「处境锚让对话更有生活气息」——**不可判定**（唯一预登记口径判不成立，且该口径效度存疑、输入一半是错的）。
2. 「处境锚对生活气息无效」——**同样不可判定**（不得把尺子失效读成机制无效）。
3. 任何幅度性断言（"提升了 X%"、"更具体了 X%"）——M3/M4 无差异信号，且样本单批单 seed。

---

## 2. 指标定档（2 个判定口径 + 3 个辅助读数，层级不许互相顶替）

判据层级是本报告的立身之本：

- **M1 是唯一判定指标**，其定义、分母、通过线**照抄预登记卡，一字未改**；
- **M2/M3/M4 是本轮新增的辅助读数，未预登记，不参与任何成立/不成立判定**，只用来解释 M1 与给出方向。
- **红线（本轮遵守记录）**：探索性指标**只以"假设生成"形式出现**，不得用来推翻或替换预登记判据的「不成立」。本报告 M1 的「不成立」判定保持不变，M3/M4 的任何数字都不改变它。

### M1（预登记主指标）· 处所-内容一致性率

| 项 | 内容 |
|---|---|
| 定义式 | 一致率 = 判为「相符」的可判定对话条数 ÷ 可判定对话条数 |
| 分子 | `type ∈ {MSG_PUBLIC, MSG_DM}`、`payload.place` 与 `payload.body` 非空、正文命中冻结线索词表 ≥1 词，且命中活动域中至少一个允许当前 `place` 的条数 |
| 分母 | 对话类事件 − 缺 `place`/`body` 条数 − `no_cue`（无线索）条数 |
| 数据来源 | `run.jsonl` 的 `type` / `payload.place` / `payload.body` |
| 实现 | `tools/metrics/place_content_consistency.py`（冻结尺子，`lexicon_sha256 = 7e514eba…f22e`） |
| 通过线 | Δ ≥ **+15.0pp** 且 rate(A1) ≥ **0.55**（先验，不得事后下调） |
| 局限 | 纯规则版、无 LLM judge；「条件一致率」不是全体对话一致率；词表覆盖有限；"允许场所"是先验设定 |

### M2（辅助）· 锚点自证：锚有没有指对地方

| 项 | 内容 |
|---|---|
| 定义式 | 锚点指对率 = `ctx.scene.place == payload.place` 的对话条数 ÷ 含 `ctx.scene` 的对话条数 |
| 分子/分母 | 分子 = 锚点场所与消息场所相同的条数；分母 = 含 `scene` 键的对话条数（A0 无该键 ⇒ 分母 0，读数 NA 而非 0%） |
| 数据来源 | `payload.ctx.scene.place`、`payload.place`；归因另用 `PLACE_ARRIVED` 事件的 `round`/`seq`/`place` |
| 性质 | **机制质量**读数（不是效果层结论） |

### M3（辅助）· 具体性密度

| 项 | 内容 |
|---|---|
| 定义式 | 每百字命中 = 四家族具体实词总命中次数 ÷ 正文字数 × 100；具体性发言率 = 至少命中 1 词的发言条数 ÷ 有 `body` 对话条数 |
| 四家族 | 物件/器物（复用 M1 冻结线索词表 169 词）、时间词（31 词，显式词表）、地点人话名（`places.json::name_cn`，17 词）、人名（`personas.json::display_name` 中"·"之后，20 词） |
| 词表指纹 | `concrete_lexicon_sha256 = 4f54f75c7944c28234c0c48c46d422f61986cdd3d64ee28018d6744dd2ef20c3` |
| 局限 | 地名人名只按人话名字面匹配，村民说「铺子/镇上」算漏；只可读方向，不可读绝对增幅 |

### M4（辅助）· 可见动作与发言长度

| 项 | 内容 |
|---|---|
| 定义式 | 旁白发言率 = 正文含成对括号（`（）`/`()`）的发言条数 ÷ 有 `body` 对话条数；旁白字数占比 = 括号内字符数 ÷ 正文字数；长度按正文字符数统计 mean/median/p90 |
| 数据来源 | `payload.body` |
| 性质 | 生活气息的"看得见人在做什么"表征；括号可能是旁白也可能是补充说明，不区分 |

---

## 3. 方法与可比性闸（全部实测，非引用）

| 闸门 | 实测结果 | 结论 |
|---|---|---|
| `env_manifest` 差异 | 逐 key 双向比对状态 `ok_only_scene`，实质差异仅 `LIFE_PROMPT_SCENE`（另 2 行为臂标签注释） | 通过（单变量成立） |
| `governor` 真跑验真 | 两臂各自 `obs llm-cost --require-provider openai_compat`：`provider_guard.ok = true`、`by_provider = {openai_compat: 2255}`、`degraded = 0` | 通过（非 mock） |
| 尺子词表指纹 | 两臂均 `7e514eba…f22e`，与预登记卡一致 | 通过（判据未漂移） |
| 分母 | A0 = 174、A1 = 165，均 ≥30 | 通过（不触发 §5.1） |
| `no_cue` 占比漂移 | A0 8.90%（17/191） vs A1 13.61%（26/191），差 **4.71pp** < 10pp | 通过（不触发 §5.5） |
| 数据隔离 | 只读 `run.jsonl`，未读 A0 side_root | 通过 |

复算命令见 §10。证据文件：
- `v2/evidence/r46-c1-effect-metrics/llm_cost_a0.json`、`llm_cost_a1.json`（两臂 `obs llm-cost` 原始输出）
- `v2/evidence/r46-c1-effect-metrics/c1-arm-compare.md`（既有尺子 `c1_arm_compare.py` 输出，作交叉核对）
- `v2/evidence/r46-c1-effect-metrics/metrics-table.md`（本报告 M1~M4 的机器输出）

---

## 4. 读数（M1 判定表）

| 臂 | 对话事件 | 缺字段 | `no_cue` | `no_cue` 占比 | 分母 | 相符 | 一致率 [Wilson 95%] |
|---|---|---|---|---|---|---|---|
| A0（OFF） | 191 | 0 | 17 | 8.90% (17/191) | 174 | 58 | **0.3333** [0.268, 0.406] |
| A1（ON） | 191 | 0 | 26 | 13.61% (26/191) | 165 | 56 | **0.3394** [0.272, 0.415] |

- **Δrate(A1−A0) = +0.61pp**；2×2 Fisher 精确检验双侧 **p = 0.9090**。
- 判定（按预登记卡 §4）：**不成立**（Δ 未达 +15.0pp，且 rate(A1) = 0.3394 < 0.55）。
- **判定与证据强度必须分两档写，且两档都不能省**：
  - **判定 = 「不成立」**：合法，因为卡 §5 第 1 条要求「任一臂 `denominator(judged) < 30` 才写不可判」，本批两臂 **174 / 165 均 ≥ 30** ⇒ **卡内五条不可判条件逐条未触发**，**不得**把「不成立」降级成「不可判」。
  - **证据强度 = `probe`**：两臂均 **< 68**（报告族纪律 `reports/README.md:152`）/ 单批 / 单 seed ⇒ 只能作点估计、不外推。
  - 因此本报告的规范写法是：**「`不成立`（`probe` 级，单批单 seed，不外推）」**——「不成立」是**判定结论**，「probe」是**证据强度标签**，两者不冲突、也**不能互相顶替**（只写 probe 会让读者以为没判定；只写"不成立"会让读者以为这是强证据）。
- 交叉核对：既有尺子 `c1_arm_compare.py` 独立跑出同一组数字（0.3333 / 0.3394 / +0.61pp / 不成立）⇒ 本报告 M1 与既有判据实现一致。

> 读这一行时必须带上：这是**条件一致率**（只覆盖命中冻结词表的 165~174 条），不是「只有 34% 的对话与场所相容」。`no_cue` 的 17/26 条不进分母。

---

## 5. 本轮独立成果：处境锚「指错场所」= 87/191，且 100% 由移动前快照解释

> 本节是**独立成果**，不是"探索性指标"的配角。理由：预登记判据只能告诉团队"没测出效果"，
> 而本节告诉团队"**为什么测不出，且它是可修的**"——这是一条可执行的技术推进，不是无解的悬念。

### 5.1 主读数

| 臂 | 含 `scene` 键 | 锚点 place == 消息 place | 锚点指对率 [Wilson 95%] |
|---|---|---|---|
| A0 | 0/191 | 0 | **NA（无 `scene` 键，不是 0%）** |
| A1 | 191/191 | 104 | **0.5445** [0.474, 0.614] |

错位 **87/191 = 45.55%**：近一半发言，模型被告知的处境不是它说话的地方。

### 5.2 归因：不是噪声，是「移动前快照」

| 臂 | 锚点错位 | 锚点 == 同轮前一次 `PLACE_MOVE.from_place` | 同轮内先到达消息场所可解释 | **既非 from 也非 to（判伪反例）** |
|---|---|---|---|---|
| A1 | 87 | **87（100.00%）** | 87（100.00%） | **0** |

| 臂 | 本 round 内有过移动的对话 | 本 round 内无移动的对话 |
|---|---|---|
| A0 | 87 | 104 |
| A1 | 87 | 104 |

结构性解释（**两臂"受影响子集"一致**，191 = 87 + 104）：

- **有同轮移动的 87 条**：`payload.place` = `to_place`（新场所，与 `PLACE_ARRIVED` 一致），而 `ctx.scene.place` = `from_place`（旧场所）；
- **无同轮移动的 104 条**：`ctx.scene.place` == `payload.place`（锚点正确）；A1 里这 104 条 `anchor != place` 的条数 = **0/104**（边界干净，缺陷精确落在有移动的那一侧）。

即：**锚点取的是本轮移动之前的场所**——`WorldView` 在本轮 perceive 阶段取定，居民随后本轮内移动、并在新场所开口。

> **表述纪律（repo-scout 复核收紧，本轮最容易翻船的一点）——「零值」还是「不适用」，必须分清**：
>
> **A0 的 `mismatch = 0` 是"平凡真"，不是"锚点正确"的证据。** A0 根本没有 `ctx.scene` 键（`scene_key = 0/191`），该判据在 A0 上**不适用**（NA），所以它的 0 只能读作「A0 没有可判定的锚点」，**不能**读作「A0 的锚点都对」。同理 §5.1 表里 A0 的「锚点指对率」写的是 **NA（无 `scene` 键，不是 0%）**。
>
> 正确表述只有一种：**「两臂受影响子集一致（都是 87 + 104 = 191），不匹配只能在 A1 观测」**；**不得**写「两臂 mismatch 一致」。⇒ 本判据对 A0 **不适用（NA）**，**不是「A0 通过」**；任何把 A0 的 0 读成"基线锚点无误"的写法都是错的。

**可直接读的例子（`seq=73`，P004）**：

```
seq=70  PLACE_MOVE    P004  residence → library
seq=71  PLACE_ARRIVED P004  place=library
seq=73  MSG_DM        place=library ；ctx.scene.place=residence
```

> **实现陷阱（后人写复核脚本必看，比结论本身更容易帮到人）**：直觉写法是"对每条对话都去找它之前最近的一次 `PLACE_MOVE`，再拿 `ctx.scene.place` 与它的 `from_place` 比"，这会**漏掉本轮根本没有移动的那 104 条**——它们的"最近一次移动"在**上一轮**，锚点当然不等于那个旧的 `from_place`，于是凭空产生**与无移动条数同量级的假反例：本批实测 104 条**（无本轮移动的条目恰为 104 条，可复算）。
> 正确做法：**先判本条在本轮内是否有过 `PLACE_MOVE`**（`same round` 且 `seq` 更小）；无移动的条目**不进入**该判据（它们本就锚点一致）。`c1_anchor_stale_check.py` 就是这么实现的，其输出里 `falsify_H2_no_move_but_mismatch=0` 正是这条守卫生效的证据。
>
> **勘误（可追溯）**：本条早前写的「约 12 条假反例」是转述 teammate 口头提示、我当时**未自行复算**；repo-scout 与我都无法重现"约 12 条"（我复现到的是 104；另有被转述的 89 我未复现，见 §12.3）。**该数字已撤回**，改用上面可复算的 104。教训：转述他人数字必须先自己跑一遍再落盘。

### 5.3 判伪条件（任一成立即推翻上面的解释）

> **性质声明（务必先说）**：**F1~F3 是内部一致性检验（用同一批日志反复核对解释自洽、无残余反例），不是外部验证**。
> 真正的外部判伪是 **F4**（改了快照口径后，新批次的锚点指对率是否真的上升），**本轮不可测**。
> 因此本节的正确表述是「解释与本批数据内部一致、无残余反例」，**不是**「该解释已被完全检验」。

| # | 判伪条件 | 本批实测 | 状态 |
|---|---|---|---|
| F1 | 存在错位条目，其 `ctx.scene.place` **既非**同轮前一次 `PLACE_MOVE.from_place` **也非** `to_place` | **0 条** | 未触发（内部一致性） |
| F2 | 存在**本轮无移动**却 `ctx.scene.place != payload.place` 的对话 | **0 条** | 未触发（内部一致性） |
| F3 | 存在某 actor 的 `payload.place` 与本轮前一次 `PLACE_MOVE.to_place` 不一致（则"place 记录口径"本身可疑，不能把 `payload.place` 当真值） | **0 条** | 未触发（内部一致性） |
| F4 | 把 scene 快照改为「发言时点场所」后，锚点指对率**没有**上升 | **需新跑批，本轮不可测** | **未检验（外部判伪）** |

F1~F3 全为零 ⇒ 「移动前快照」解释在本批日志层面**内部一致、无残余反例**；这只排除了"本批数据里还存在别的成因"，**不等于**该解释已在外部检验过。F4 是唯一的外部判伪，只有下一轮改了 `_scene_line()` 并重跑双臂才能检验。

### 5.4 与 M1 的关系（不以本节推翻 §4 判定）

A1 的 109 条相悖中：内容贴「锚点所说场所」的 **21.10%（23/109）**，两边都不贴的 **78.90%（86/109）**。
这说明"被锚点带偏"只占相悖的一小部分，**锚点时序不是 M1 不成立的全部原因**——另一半原因在 §7 的尺子偏差。
本节**不改变** §4 的「不成立」判定，只解释它为什么不能当"机制无效"的证据。

### 5.5 「乐观上界」读数（run-observer 独立复算后提出，辅助口径、不参与判定）

按 A1 的**锚点是否指对**把可判定条目分成两层：

| 层 | 相符 / 可判定 | 一致率 |
|---|---|---|
| 锚点**错位**子集 | 19 / 75 | **0.2533** |
| 锚点**一致**子集 | 37 / 90 | **0.4111** |

**乐观上界**：假设"错位子集"全部表现得和"一致子集"一样好 ⇒ A1 一致率至多 **0.4111**，仍 **< 0.55** 下限；对应 Δ 仅 **+7.8pp < +15.0pp**。

读法（须与数字一起引用）：这一层说明**缺陷确实让"不成立"更没有说服力**（错位层 0.2533 明显低于一致层 0.4111，方向与"锚点带偏"一致），**但按预登记判据不会翻转为"成立"**。因此正确表述仍是 §1 那句：**"本轮实现存在可定位缺陷（锚点时序 + 尺子偏差），该假设尚未获得公允检验。"** 不得写成"如果修好了就会成立"。

---

## 6. 生活气息辅助读数（M3 具体性 / M4 可见动作）

> **定位声明（红线）**：本节两项指标**未预登记**，只作**假设生成**用途（下一步该测什么），
> 其数字**不参与判定、也不推翻 §4 的「不成立」**。两臂在这些指标上都没有超出噪声的差异，
> 因此它们既不能证明"更有人味"，也不能证明"变差"。

### M3 具体性密度

| 臂 | 有 body | 命中的发言 | 具体性发言率 [Wilson 95%] | 总命中 | 每百字命中 | 正文字数 |
|---|---|---|---|---|---|---|
| A0 | 191 | 186 | 0.9738 [0.940, 0.989] | 657 | **5.831** | 11268 |
| A1 | 191 | 183 | 0.9581 [0.920, 0.979] | 593 | **5.064** | 11711 |

- 具体性发言率两臂 Fisher 双侧 **p = 0.5743**（无差异信号）。
- 分家族命中条数：A0 = 物件 174 / 时间 63 / 地点 3 / 人名 110；A1 = 物件 165 / 时间 67 / 地点 9 / 人名 98。
- 方向：A1 的每百字命中略低（5.06 vs 5.83）、地名提及略高（9 vs 3）。**两者都在噪声量级内，不构成"更有人味"的证据**，只能作为"没有明显变差"的旁证。

### M4 可见动作与长度

| 臂 | 有 body | 含旁白发言 | 旁白发言率 [Wilson 95%] | 旁白字数占比 | mean | median | p90 |
|---|---|---|---|---|---|---|---|
| A0 | 191 | 176 | 0.9215 [0.874, 0.952] | 32.13% | 59.0 | 56.0 | 83 |
| A1 | 191 | 181 | 0.9476 [0.906, 0.971] | 30.30% | 61.3 | 59.0 | 85 |

- 方向：A1 的旁白发言率略高（+2.6pp，CI 大幅重叠）、平均长度略长（+2.3 字）、旁白字数占比略低（−1.8pp）。**同样在噪声量级**。
- 剂量上的意义：提示词只加了一行（约 30~50 字），发言长度分布**没有整体漂移**（median 56→59，p90 83→85）⇒ 没有"变长变啰嗦"的副作用。

---

## 7. 尺子校准：`place_content_consistency.py` 测的是不是场景锚想改善的东西

这一节只做**判据诊断**，不新增指标、不改任何阈值。

### 7.1 代码层：它到底在判什么

`classify()`（`tools/metrics/place_content_consistency.py:123-131`）对每条正文做**纯子串包含**匹配：只要正文里出现该活动域任一线索词，就把这个活动域算作「命中」，再要求「命中的活动域里至少有一个允许当前 `place`」。

由此产生两个与"生活气息"错位的前提：

1. **"提到" = "在做"**。规则无法区分「我正揉着一盆面」（在此处做）与「我灶上还炖着汤」（提到别处的事）。后者在闲聊里极其常见，却被逐字判成"相悖"。
2. **允许场所是"生产场所"口径**。例如 `trade_accounting` 只允许 `market` / `bank` / `office`，而它的线索词里有 `买`、`卖`、`账`、`摊上`、`柜台`——**在咖啡馆聊"这布多少钱买的"就会被判相悖**。

### 7.2 数据层：相悖条目被哪些词、在哪些地方触发

把两条臂的**相悖条目**按触发线索词与被判场所拆开（只读 `run.jsonl`，命令见 §10 ⑦）：

| 臂 | 相悖条数 | 触发最多的线索词（次数） |
|---|---|---|
| A0 | 116 | 灶 20、锅 12、药 11、锄头 10、账 10、锉刀 9、刨子 5、算盘 5、围裙 5、红薯 5 |
| A1 | 109 | 账 13、灶 10、面粉 6、药 6、算盘 6、锄头 6、练功 6、柜台 6、糖糕 5 |

按场所分层（可判定/相符，来自 `c1_arm_compare.py` 的同一把尺子）：

| place | A0 可判定 / 相符 | A1 可判定 / 相符 |
|---|---|---|
| cafe | 27 / **1** | 26 / **2** |
| park | 21 / 5 | 17 / **1** |
| plaza | 14 / 1 | 15 / 2 |
| market | 21 / 6 | 20 / 5 |
| residence | 26 / 18 | 27 / 16 |
| school | 13 / 2 | 12 / 2 |

**读法**：在 `cafe` 的 27 条里只有 1 条被判相符——这不可能是"居民在咖啡馆干木工/做饭"，只能是"人在咖啡馆，嘴上说着家里灶上、铺子里的事"。触发词 `灶/锅/药/账/买/卖` 都是**日常闲聊高频词**，不是"在此处动手"的证据。

### 7.3 判断（基于代码与数据，不基于希望）

> **判断：两者都有，但主因是"尺子没测到该测的东西"叠加"输入本身有缺陷"，不是"场景锚已被证伪"。**
>
> - **尺子侧（更根本）**：它测的是「正文提到的活动域与该场所是否相容」，而场景锚想改善的是「居民说话时是否带着此情此景的具体性」。两者在**闲聊型场所系统性反向**：越是在咖啡馆/公园这类地方自然地聊起别处的活计，越容易被判相悖 ⇒ 该尺子对"生活气息"这一构念**不敏感**，甚至轻微反向。
> - **输入侧**：A1 的锚点有 87/191 指错地方（§5），模型在近一半发言里被告知的是**上一站**。即使尺子完全正确，这也会把 A1 的读数往 0 拉。
> - **不能推出的结论**：不能由此说"处境锚有效"；也不能说"位处错了就说明没问题"。**任何方向的正向宣称都没有数据支撑。**

补充一条剂量事实（用于排除"提示词变长副作用"）：本案只加一行（约 30~50 字），M4 的发言长度分布 median 56→59、p90 83→85，**没有整体漂移**。

---

## 8. 诚实边界与不可判定项（逐条登记，不得删项）

1. **`participants_violations` 两臂均为 9**（`meta.assertions.participants_consistent = false`）⇒ 同型、不构成臂间差异，但**样本存在线程级元组不一致**（首帖 1 人 → 接话 2 人形态），引用任何数字时须带这一条。
2. **`meta.assertions.code_unchanged_during_run` 两臂均为 `null`** ⇒ "跑批期间冻结区未变"**不可判**（缺 `--git-status-start` 断言）。两臂同 `code_sha = 8b64615` 可佐证同一棵树，但不等于跑批期间无改动。
3. **`meta.switch_effective` 里没有 `LIFE_PROMPT_SCENE` 这个键（键缺失，不是 `null`）**：两臂 `switch_effective` 只有 `HITT_DIALOGUE_EMOTION_ECHO` / `HITT_DIALOGUE_REPAIR` / `HITT_WEATHER` / `LIFE_PROMPT_ADDR_EVOLVE` 四个键，对照 `tools/d2/emit_run_meta.py:133/181` 的既有范式 ⇒ 属**工具链缺一个提取器**（repo-scout 独立复算纠正的口径）。开关确实生效的证据只能来自 `ctx.scene` 覆盖 0/191 → 191/191，**不能引用 meta**。
4. **A0 side_root 被污染 211 文件**（A1 attempt1 误写，`SIDE_ROOT_CONTAMINATED.md`），污染发生在 A0 收批之后 ⇒ 本报告**只读 run.jsonl**，所有读数不依赖 side_root；但**任何需要重读 A0 side_root 的复算都不可信**。
5. **单批、单 seed（42）、16 居民 × 24 轮、无重复批** ⇒ 无批间方差，所有差异只能作点估计；未做多重比较校正。两臂分母 174 / 165 均 < 68 ⇒ 整条读数 `probe = true`，任何地方都不得写「显著／有效／生活气息提升」。
   - **`probe` 阈值的来源（已核，区分清楚）**：`分母 < 68 ⇒ probe` 是**报告族既有纪律**，出自 `reports/README.md:152`（原文：「分母 < 68 的指标一律标 `probe` / 『本规模下无法判定』」），并被 `docs/team-board.md:10` 沿用。它**不在** C1 预登记卡里。
   - 因此这既**不是**"本轮新发现的判据缺陷"，也**不是**"预登记卡原本就有的降级条款"——它是**卡外的通用纪律**，本轮按纪律执行，**不违反**预登记卡。
   - 但要如实登记一处**预登记卡不完备**：卡 §5 的 5 条不可判条件只处理了 `分母 < 30`，**没有**把"小样本点估计应先降级为 `probe`"写进卡内。这属于判据覆盖面缺口，已挂进 §9 的 P2（下一轮尺子/判据改进假设），**不当作一句免责声明**。
6. **M2/M3/M4 未预登记**，是本轮新增的探索性读数，**不得**被引作"生活气息提升/下降"的判据。
7. **M1 为纯规则版、未用 LLM judge**，结论强度弱于人工标注；且 §7 显示其构念效度在闲聊型场所存疑。
8. **证据不足 / 明确不可判定**的项：
   - 「处境锚对生活气息的效果」——**不可判定**。M1 是唯一预登记口径且判不成立，但 §5 证明锚点本身有一半指错、§7 证明尺子在该用途上效度存疑 ⇒ 既不能说"有效"，也不能说"机制无用"。
   - 「修好时序后能否过 +15pp」——**无数据，不可推测为结论**（§5 给出的 21% 只是相悖内部构成，不是效果上界估计）。
   - 「A1 是否让居民更有人味」——M3/M4 均无差异信号，**不可判定**。
9. 历史未决项不因本报告消失：`R41V-C4` 不成立、`R41V-C1` 不可判、`R44-C1a/C1b/C2/C3` 不可判、CYCLE-47 `N-1…N-7` 未销号。

---

## 9. 对下一轮的建议（属实现侧，本轮按纪律不动冻结区）

按优先级，均需**开分支、跑批前由 run-observer 确认时机**：

| # | 建议 | 落点 | 为什么 |
|---|---|---|---|
| P1 | **修锚点时序**：`_scene_line()` 改用「本条发言发生时点的场所」，而不是本轮 perceive 阶段的 `WorldView.location`；最小改法是取该 round 内最后一次 `PLACE_ARRIVED` 之后的场所，或在移动后刷新 life 侧持有视图 | `code/life/agent.py:1576 _scene_line()`（可只改 life 一侧，不碰 engine） | 87/87 的错位都由此产生；不修则任何"处境锚"实验都在向模型喂上一站的信息 |
| P2 | **M1 尺子升级（须新预登记卡 `C1-scene-prereg-v2`）**：① 区分「在此处做」与「提到别处的事」（闲聊型场所 + 他处活动词 → 归 `no_cue`），或改为"锚点一致性"与"场所一致性"双读数；② **把「小样本 `probe` 降级」写进新卡**——现卡 §5 只有 `分母 < 30` 一条，缺"分母 < 68 一律按点估计/probe 处理"这一报告族纪律（出处 `reports/README.md:152`），本轮只能按卡外纪律执行，属**预登记覆盖面缺口**（见 §8-5） | `v2/refs/C1-scene-prereg-v2.md` + `tools/metrics/` | §7 显示现尺子在 cafe/park/plaza 系统性出负；§8-5 显示卡缺 probe 条款 |
| P3 | 把 `LIFE_PROMPT_SCENE` 登记进 `meta.switch_effective`（跑批工具链） | `tools/d2/emit_run_meta.py` | 否则开关生效只能靠 payload 旁证 |

---

## 10. 复算命令（照抄可复现本报告全部数字）

### 10.1 一条命令独立复现「87/191」（不依赖本报告任何人写的脚本）

`tools/metrics/c1_anchor_stale_check.py` 是**零依赖单文件**（不 import 仓库任何模块、不复用 `c1_effect_metrics.py`），只读 `run.jsonl`：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 tools/metrics/c1_anchor_stale_check.py v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl
```

期望输出（实测，2026-11-01）：

```
dialogue=191 scene_key=191 anchor_match=104 anchor_mismatch=87 mismatch_rate=0.4555
anchor_eq_from_place=87 (100.00%) neither_from_nor_to=0
falsify_H2_no_move_but_mismatch=0 falsify_H3_place_ne_to_place=0

# 逐条明细（seq | round | actor | 消息place | 锚place | 前置移动 from→to | 正文前40字）
53 | 0 | P002 | library | residence | residence→library | 天刚亮，手就闲不住。（把刨子往木料上一推…
...（共 87 行）
# 判伪反例（非空即推翻「移动前快照」解释）
(none：锚点场所 100% 落在 from_place 上)
```

同一条命令换 A0：`dialogue=191 scene_key=0 ...`（无 `scene` 键 ⇒ 机制未接通，符合预期）。

完整输出已存档：`v2/evidence/r46-c1-effect-metrics/anchor-stale-a1.txt`（95 行）、`anchor-stale-a0.txt`。

> **实现陷阱（后人写复核脚本必看）**：若实现是"对每条对话都去找它之前最近一次 `PLACE_MOVE`、再与 `from_place` 比"，会漏掉**本轮没有移动**的 104 条（它们的最近一次移动在上一轮），从而凭空产生**与无移动条数同量级的假反例：本批实测 104 条**（可复算：`无本轮移动的对话条数 = 104`）。正确做法：**先判本条是否在本轮内有过移动**，无移动的条目**不进入**该判据（它们本就锚点一致）。详见 §5.2 的勘误说明（早前"约 12 条"的说法已撤回）。

### 10.2 全量复算

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
A0=v2/evidence/c1-scene-a0-20261101_n16r24_s42/run.jsonl
A1=v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl

# ① 本报告 M1~M4 全部读数（一条命令）
python3 tools/metrics/c1_effect_metrics.py --arm A0=$A0 --arm A1=$A1 \
    --out-md v2/evidence/r46-c1-effect-metrics/metrics-table.md

# ② 幂等自检（同一输入两次运行逐字节一致）
python3 tools/metrics/c1_effect_metrics.py --arm A0=$A0 --arm A1=$A1 > /tmp/a.txt
python3 tools/metrics/c1_effect_metrics.py --arm A0=$A0 --arm A1=$A1 > /tmp/b.txt
cmp /tmp/a.txt /tmp/b.txt && echo BYTE_IDENTICAL

# ③ 交叉核对：既有冻结尺子（M1 必须与 ① 中的 M1 一致）
python3 tools/metrics/c1_arm_compare.py --arm A0=$A0 --arm A1=$A1 \
    --out-md v2/evidence/r46-c1-effect-metrics/c1-arm-compare.md

# ④ 真跑验真（两臂）
cd code
python3 -m obs llm-cost --log ../$A0 --require-provider openai_compat
python3 -m obs llm-cost --log ../$A1 --require-provider openai_compat

# ⑤ 可比性闸：两臂 env 只差 LIFE_PROMPT_SCENE
diff v2/evidence/c1-scene-a0-20261101_n16r24_s42/env_manifest.txt \
     v2/evidence/c1-scene-a1-20261101_n16r24_s42/env_manifest.txt

# ⑥ 冻结区无改动
git status --porcelain -- code/life code/orchestration code/config code/engine | wc -l   # 期望 0

# ⑦ §7.2 触发词归因（相悖条目按线索词计数；确定性，同一输入两次结果一致）
python3 - <<'PY'
import json,sys,collections
sys.path.insert(0,"tools/metrics")
import place_content_consistency as R
for arm in ("a0","a1"):
    p=f"v2/evidence/c1-scene-{arm}-20261101_n16r24_s42/run.jsonl"
    cue=collections.Counter(); n=0
    for l in open(p):
        e=json.loads(l)
        if e.get("type") not in R.DIALOGUE_TYPES: continue
        pl=e["payload"]; place=(pl.get("place") or "").strip(); body=(pl.get("body") or "").strip()
        if not place or not body: continue
        doms,cues=R.classify(body)
        if not doms: continue
        if any(place in R.DOMAINS[d]["places"] for d in doms): continue
        n+=1
        for c in cues: cue[c]+=1
    print(arm,"contra",n,"top cues",cue.most_common(12))
PY

# ⑧ M2b 归因(同轮内先到达)
python3 - <<'PY'
import json,collections
p="v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl"
evs=[json.loads(l) for l in open(p)]
arr=collections.defaultdict(list)
for e in evs:
    if e.get("type")=="PLACE_ARRIVED":
        arr[e.get("actor")].append((e.get("round"),e.get("seq"),(e.get("payload") or {}).get("place")))
mm=ex=0
for e in evs:
    if e.get("type") not in ("MSG_PUBLIC","MSG_DM"): continue
    pl=e["payload"]; sc=(pl.get("ctx") or {}).get("scene") or {}
    if not sc or sc.get("place")==pl.get("place"): continue
    mm+=1
    if any(r==e.get("round") and s<e.get("seq") and pl_==pl.get("place") for r,s,pl_ in arr.get(e.get("actor"),[])):
        ex+=1
print("mismatch=%d explained_by_intraround_arrival=%d"%(mm,ex))
PY
```

两臂 `run.jsonl` 逐字节 sha256：

- A0: `1bfeb51d0bb336abca748dad0b1a40375f702df204f9c42cfd0591f24f5dbcb4`（17,299,533 B）
- A1: `c828b4075f027917ce883670564b2a827b4f1feecd322315619f9ecbe9324633`（17,318,810 B）

---

## 11. 产物清单

| 文件 | 说明 |
|---|---|
| `tools/metrics/c1_effect_metrics.py` | 本轮新增尺子（M1 复用冻结实现，M2~M4 新增；确定性、可逐字节复算） |
| `tools/metrics/c1_anchor_stale_check.py` | **零依赖独立复核器**：一条命令复现 87/191 + 87 条逐条明细 + 判伪反例清单 |
| `v2/evidence/r46-c1-effect-metrics/metrics-table.md` | 两臂全部读数机器输出（本报告 §4~§6 的数字来源） |
| `v2/evidence/r46-c1-effect-metrics/anchor-stale-a1.txt` / `anchor-stale-a0.txt` | 独立复核器原始输出（A1 含 87 条明细） |
| `v2/evidence/r46-c1-effect-metrics/c1-arm-compare.md` | 既有尺子交叉核对输出 |
| `v2/evidence/r46-c1-effect-metrics/llm_cost_a0.json` / `llm_cost_a1.json` | 两臂 `obs llm-cost` 原始输出（真跑验真；A1 的标准名 `llm_cost.txt` 由 run-observer 在批次目录内补齐） |
| `reports/R46-c1-effect-metrics-20261101.md` | 本报告（run-observer 定为 R4 唯一报告基座） |

---

## 12. 复核者独立验证与「第三方审计」结论（`run-observer`，本节为本报告新增）

> 本节回答一个容易被含糊过去的问题：**「独立复算」到底独立到什么程度。**

### 12.1 我自己的独立实现（不使用任何他人的脚本）

- 实现方式：**按 `PLACE_ARRIVED` 时间线重建每个 agent 的站位序列**，再对每条错位发言判断 `ctx.scene.place` 是否等于「移动到目的地之前所在场所」；首轮用 `AGENT_BORN.home_place` 补初始站位。
- 结果：**87/191 = 0.4555**（与 §5 一致，逐条相同）；成因两条判据 **87/87、87/87**，反例 **0**。
- 命令：见 `v2/evidence/c1-scene-verify-20261101/R3-VERIFY-EVIDENCE.md` §11.9。

### 12.2 `c1_anchor_stale_check.py` 的第三方审计（三项）

| 审计项 | 方法与结果 | 判定 |
|---|---|---|
| ① 是否真的零依赖 | 源码 import 段只有 `from __future__ / collections / json / sys`（无 `tools.*`、无 `sys.path` 注入）；`python3 -X importtime tools/metrics/c1_anchor_stale_check.py <A1>/run.jsonl` 的 import 记录里**不含任何仓库模块** | **通过（真零依赖）** |
| ② 判据实现是否与声称一致 | 源码确认：以 `PLACE_MOVE.from_place/to_place` 为据，**限定同 round 且 `seq < 消息 seq`**，取最后一条 move；`eq_from` = 锚点 == `from_place`；`falsify_H3` = `payload.place != to_place`。实测 `anchor_eq_from_place=87 (100.00%)`、`neither_from_nor_to=0`、`falsify_H2=0`、`falsify_H3=0` | **通过（与声明一致）** |
| ③ 与我方实现是否结构性不同 | **是**。我方用 `PLACE_ARRIVED` 事件序列 + `home_place` 兜底；对方用 `PLACE_MOVE` 的 `from→to` 配对。两者**事件源不同、数据结构不同**，不是同一段逻辑的两次运行 ⇒ 结果一致才构成**跨实现交叉验证** | **通过（非同一实现）** |

补充稳健性检验（我做的参数扰动）：把「同 round 过滤」去掉、改为跨轮取最后一条 `PLACE_MOVE`，结果仍为 **87/87 命中、0 不命中** ⇒ 该解释对这一参数选择不敏感。

### 12.3 **勘误（三方复算，最终版）：三个"12/104/89"必须分开写**

> 本节勘误对象是我自己先前的转述。教训见 §0.2：**数字不但要自跑，还要写清变体与定义——同一个数字在不同定义下指向完全不同的东西。**

| 量 | 定义（可复算） | 实测 | 我是否自跑复现 |
|---|---|---|---|
| **陷阱后果** | 朴素写法：对每条消息都取「最近一次 `PLACE_MOVE.from_place`」比对、**不加同轮守卫** | **104 条**，恰等于「无本轮移动的对话条数」（191 − 87 = 104；用 `PLACE_MOVE` 与用 `PLACE_ARRIVED` 两种事件源都得 104） | ✅ 复现 |
| **12 的真实含义** | A1 中「**锚点错位但被 `no_cue` 排除在分母外**」的条目数：`87（错位总数）− 75（错位且进判分母）= 12`，等价 `26（no_cue 总数）− 14（no_cue 且锚点一致）= 12` | **12 条**（两条路径一致） | ✅ 复现（两种算式都得 12） |
| **89** | repo-scout 称其"变体 B=104 是 `actor` 取键 bug，改 `payload.agent_id` 后得 89" | **我未复现出 89**：两种事件源（`PLACE_MOVE` / `PLACE_ARRIVED`）、两种取键（`actor` / `payload.agent_id`）下，"无本轮移动的对话条数"均为 **104** | ⚠️ **未复现 ⇒ 按 §0.2 纪律不转述，登记为待核项** |

- **原说法「`home_place` 兜底缺失会产出 12」撤回**：本批 191 条含 `scene` 的消息中，「该次到达是该 agent 的**首次**到达、因而缺"移动前站位"、需要 `home_place` 兜底」的情形我在一个**刻意变体**下确实数到 12 条，但那**不是**团队流传说法的含义（该说法指"陷阱后果"）；同一数字在两套不同定义下撞车，正是必须写清定义的理由。**该解释作废，以本表为准。**
- **复算件已由我实跑验证**：`v2/evidence/r46-c1-effect-metrics/recompute-three-numbers.py`（standalone，只读 `run.jsonl`）输出 `mismatch_total=87 judged_mismatch=75 judged_match=90 分母=165`、`87−75=12`、`26−14=12`、`naive_from_place_false_positives=104 no_move_dialogue=104`，两次运行 `cmp` ⇒ **BYTE_IDENTICAL**，与本报告数字逐项一致。
- 保留结论：`c1_anchor_stale_check.py` 的口径（只遍历错位条目 + 同轮守卫 + 取 `from_place`）**不受上述任何变体影响**，其 87/87 与反例 0 不变。

### 12.4 因此本报告可以说到哪一步

- 可以说：**「87/191 与 87/87 由两套结构不同的独立实现交叉验证一致（我方 `PLACE_ARRIVED` 时间线实现 vs 对方 `PLACE_MOVE` from→to 实现）」**；
- 可以说（三个量的复算件）：**「三份互不 import 的独立实现复算一致（其中两份同作者、一份异作者）」**——`c1_anchor_stale_check.py`（life-impl）、`recompute-three-numbers.py`（life-impl，分母链归属口径）、以及我自己的 `PLACE_ARRIVED` 实现（run-observer）。**代码载体独立 ✓；作者独立 ✗**——3 份实现去重后只有 **2 位作者**（其中 2 份同作者）；
- **强度声明必须带条件标签**（§0.2 第③半的延伸）：「多方复算」应标注**异作者数量**，而不是**复算次数**；
- 
- 不可以说：「已由第三方外部验证」——外部判伪仍是 §5.3 的 **F4（需新跑批）**。

---

### 12.5 §0.2 纪律的实证案例（本团队每个人都适用，包括审查者与被审查者）

- **`repo-scout`（R7 审查员）自查纠错**：其"变体 B = 104"被自己发现是 `actor` / `payload.agent_id` **取键 bug**，改键后报告为 **89**。→ 说明取键口径这种细节足以改变数字，纪律对审查者同样适用。
- **`life-impl`**：把"陷阱后果"与"12 的真义"混成一个量，已按 §12.3 分开并撤回。
- **本复核者（`run-observer`）**：转述了未自跑的"约 12 条"，且在**刻意变体**下"复现"了解释、误认为找到了来源；已按 §12.3 撤回解释。
- **诚实边界**：`repo-scout` 的 **89 我未能复现**（我的四种组合都给出 104），因此本报告**不把 89 当作事实**，登记为待核项（§12.3 表第 3 行）。这也正是 §0.2 的用法：**别人自查后的数字，仍需自己跑一遍才算落盘**。

---

## 13. 数据完整性复核（三方时间线 + 零窗口）

### 13.1 「A0 side_root 被误写 211 文件」的独立复算（不引用任何成员结论）

| 事实 | 实测值 | 依据 |
|---|---|---|
| A0 收批时刻 | **10:34:22**（`run.jsonl` mtime `10:34:22.021`；`host.log` `finished_at=2026-11-01T10:34:23+08:00 rc=0`） | 文件系统 mtime + host.log |
| A0 side_root 文件总数 | 3564 | `os.walk` 全量统计 |
| 晚于收批时刻的文件 | **恰好 211 个** | 同上 |
| 211 个文件的 mtime 区间 | **10:43:33 – 10:43:47**（跨度 15 秒） | 同上 |
| **10:34:24 – 10:43:31 之间的文件数** | **0（零窗口）** | 同上 |
| 211 个文件的位置 | 全部在 `freeze_cache/judgments/*` 与 `freeze_cache/responses/*` | 同上 |
| 写入者 | A1 的 `attempt1`（起跑 10:43:32，`host.log` 内 `[d2] run: … --side-root /tmp/c1_scene_a0_n16r24_s42_side`） | host.log 命令行 |
| A0 `run.jsonl` 是否受影响 | **否**：sha256 `1bfeb51d…` 与 `meta.run_sha256` 逐字相等；mtime 早于全部 211 个文件 | sha256sum + meta |
| A1 正式批次是否读到残留 | **否**：A1 自己的 side_root 最早文件 mtime **10:44:06**，晚于 A1 起跑 10:44:02 | 同上 |

**「零窗口」是本节最硬的证据**：A0 收批后 9 分钟内其 side_root 无任何写入，211 次写入全部集中在 15 秒内并与 A1 attempt1 起跑时刻吻合。

**边界条件（引用结论时必须带上）**：受影响的只有 A0 的 **side_root 缓存**；任何**读 A0 side_root 缓存**的二次分析必须按 `mtime ≤ 2026-11-01T10:34:22` 过滤；**只用 `run.jsonl` 的读数（本报告全部数字）不受影响**，因为 `cached` 字段在事发前已写入日志。

### 13.2 串行纪律（可复算事实）

| 事件 | 时刻 |
|---|---|
| A0 起跑 / 收批 | 10:09:59 / 10:34:23 |
| A1 attempt1（误用 A0 side_root）起跑 / 最后写入 | 10:43:32 / 10:43:47 |
| A1 正式起跑 / 收批 | 10:44:02 / 11:06:43 |

A0 `[10:09:59, 10:34:23]` 与 A1 `[10:44:02, 11:06:43]` **不相交**，间隔 9 分 39 秒；A1 的 `preflight@10:09:56` 虽 PASS 但 `host.log` 无 `[d2] run:` 行、A1 side_root 当时 0 文件 ⇒ **未起引擎，无并发双跑**。

### 13.3 其他完整性事实

- 行数 = `meta.events`（A0 34096 / A1 34075），坏行 0，`seq` 连续（= 行号 − 1），24 轮每轮恰好 1 个轮末 `TURN_SEAL`；
- `participants_violations` 两臂**均 9**、`participants_consistent` 两臂均 `false`（同型）；两臂对话类事件同为 191（`MSG_DM=161 + MSG_PUBLIC=30`）；
- `code_unchanged_during_run` 两臂均 `null` ⇒ **不可判**（缺 `--git-status-start` 断言），只能以 `code_sha == code_sha_end == 8b64615` 佐证同树。

---

## 14. 口径与陷阱：`mono_ts` 不是墙钟（照抄避坑）

- **事实**：`run.jsonl` 每行的 `mono_ts` **等于 `seq`（事件计数器）**。d47 实测：`WORLD_INIT seq=0/mono_ts=0`；round 0 的 `TURN_SEAL seq=425/mono_ts=425`，而该轮恰 426 行；全批 `max(mono_ts)=33227` 而 `meta.events=33228`。本轮两臂同样成立（`max_seq` 34095 / 34074）。
- **错误推演 → 假结论**：
  | 错误做法 | 会得到的假结论 | 真实值 |
  |---|---|---|
  | `started_at + max(mono_ts)` 当收批时刻 | d47 跨 **33227 秒 ≈ 9.23 小时** | `duration_sec=1261`（20 分 41 秒）⇒ 夸大 **26 倍** |
  | 逐轮首末 `mono_ts` 当轮起止 | round1 起点晚于 round2 终点，**轮次互相重叠** | 24 轮严格串行 |
- **正确做法**：墙钟只能来自 `meta.started_at/finished_at/duration_sec`、`host.log` 的 `started_at=`/`finished_at=` 行，或跑批进行中的真实采样（`tools/run/alive_sampler.py`，精度 = 采样间隔，须在表头写明）；`mono_ts` 只可用于排序/定位（如 `tools/d21/a2_incidence.py`、`partner_choice_stats.py` 仅排序，结论不受影响），一旦用于「时间窗口/速率/间隔」结论即为假。

---

## 15. 已证实的工具链缺陷（三处，登记不修）

> 本轮 `diff` 要保持干净可审计；三处均为**证据可信度**问题，已由 team-leader 另排任务修复，本报告只登记。

| # | 缺陷 | 根因（文件:行） | 影响面 | 本轮证据 |
|---|---|---|---|---|
| A | **`meta.side_root` 结构性失真**（恒 `null`） | `tools/d2/run_batch.sh:54` 把 `--side-root` 传给引擎的 `ARGS`，但 `:62` 的 `META_ARGS` **不含**该参数；`tools/d2/emit_run_meta.py:291` `--side-root default=None` | 任何依赖该字段判断 side-root 隔离性的分析会**系统性误判**（本轮差点据此错判 A0 被污染） | 两臂 `host.log` 均有 `[d2] run: … --side-root …`，而两臂 `meta.side_root` 均为 `null` |
| B | **`launch_evidence` 声明 ≠ 实际命令** | A1 `attempt1` 的 `launch_evidence.txt` 自述 `side_root: …a1_side`，同目录 `host.log` 实际是 `--side-root …a0_side` | `launch_evidence` **不能单独作为隔离性证据**，必须交叉 `host.log` 命令行 | `attempt1_wrong_side_root/` 目录同时含两种说法 |
| C | **llm-cost 门禁输出不落批次目录** | `tools/d2/run_batch.sh:81` 写死 `/tmp/d2_llmcost_$$.out`，`tail -3` 后不落批次目录 | 造成「证据缺口」**误判**——性质是落点问题，不是门禁没跑 | A1 门禁原件 `/tmp/d2_llmcost_1251980.out`（mtime 11:06:43）与归档 `llm_cost.txt` **BYTE_IDENTICAL** |

修复建议（供另开任务）：A 补传 `--side-root` 并记 `side_root_source ∈ {cli, host.log, missing}`、两者皆缺则非零退出（保留 `--allow-missing-side-root`）；B 让声明取自实际生效命令行、不一致直接 fail，并加只读回归检查器（**必须能抓出 attempt1 这个已知坏例，否则是空检查器**）；C 门禁输出落批次目录并给出历史批次回填/不回填的兼容策略。

---

## 16. 真实截图（两臂关键视图）

链路：与 d47 同一链路（`tools/metrics/render_shots.py` → `gen_threads.py` 派生 `threads.json` → 临时静态服务 → Chromium 现场截图）。**只读日志、零跑批、零 LLM、不写 `code/frontend`**；文件名中的 8 位十六进制 = 该臂 `run.jsonl` sha256 前 8 位。

| 臂 | 视图 | 路径（仓库相对） | 字节 | PNG sha256 |
|---|---|---|---|---|
| A0 | chat | `v2/evidence/c1_scene_shots/c1-a0-chat-1bfeb51d.png` | 279008 | `ad034cfa1542484723bfd5aed5e7b60a8fa545687a7303fbd8b6b9c2103d807f` |
| A0 | rhythm | `v2/evidence/c1_scene_shots/c1-a0-rhythm-1bfeb51d.png` | 279430 | `161b4c80e19a437971cdb84752a8eaed7dde2a97a1e622b29ac4151ab0cd373e` |
| A1 | chat | `v2/evidence/c1_scene_shots/c1-a1-chat-c828b407.png` | 285493 | `10ddaaef0784f2a39be85fc00e33c3527a6652ae854f64717147b1397ed4ae55` |
| A1 | rhythm | `v2/evidence/c1_scene_shots/c1-a1-rhythm-c828b407.png` | 279438 | `2b1fe43046088eeec41d82ea4a622f79278caeb1cd9eedd42f72f2336b932a46` |

生成命令（两臂各一条；均 `ok_count=2 fail_count=0`，像素自检 `distinct_colors` 数万级、`top_color_frac` ≪ 0.99 ⇒ 非空图/非单色图；未拼图、未跨批混拼）：

```bash
/opt/openjiuwen/workswarm-venv/bin/python3 tools/metrics/render_shots.py \
  --run-dir v2/evidence/c1-scene-a0-20261101_n16r24_s42 --batch-id c1-a0 \
  --outdir v2/evidence/c1_scene_shots --views chat,rhythm --timeout 180
/opt/openjiuwen/workswarm-venv/bin/python3 tools/metrics/render_shots.py \
  --run-dir v2/evidence/c1-scene-a1-20261101_n16r24_s42 --batch-id c1-a1 \
  --outdir v2/evidence/c1_scene_shots --views chat,rhythm --timeout 180
```

渲染报告（可溯源三件套）：`v2/evidence/c1_scene_shots/render_report_c1-a0.json`、`render_report_c1-a1.json`（含每张图的 `gen_threads_cmd` / `render_cmd` / `log_sha256` / `png_sha256`）。

---

## 17. 交付与发布

- **唯一报告基座**：本文件（`reports/R46-c1-effect-metrics-20261101.md`）。`reports/R45-C1-scene-anchor-20261101.md` 顶部已加「已被 R46 取代」指针，**不留两份半成品**。
- **分支**：`feat/r46-c1-effect-metrics`（从 `feat/r44-public-reply-inbound` 的 `8b64615` 切出）。**不 push master、不 force push**。
- **对外报告 sha**：见下「回填区」（推送后回填，并与远程核对一致）。
- **本轮无新增跑批**：所有 LLM 调用均为 2026-11-01 已完成的两臂历史批次；归档动作（A1 `llm_cost.txt` / `llm_cost.gate.out` / `A1_ACCEPT.txt`）为零跑批的只读重算。

### 17.1 sha 回填区（推送后填写）

| 项 | 值 |
|---|---|
| **首交付 sha**（四条并列结论 + 证据 + 截图 + 工具） | `dcf8c9dcd2523c5f6fae5c0378818922278f64d1`（短码 `dcf8c9d`） |
| **勘误 sha**（§0.2 三半纪律 / §12.3 12-104-89 分开 / §0 补 probe 级 / §12.5 自查案例；**不改变任何数据与结论**） | `7a1cbbdd152e61b7a1cfcad1855ccd257fafa394`（短码 `7a1cbbd`） |
| **定稿 sha**（内容定稿提交） | `63d3226aeed68b072939ed84827b9a470ec07d91`（短码 `63d3226`）——四条并列结论 + 证据 + 截图 + 工具 + 勘误 + 交付回填，均在此提交 |
| 远程分支 | `origin/feat/r46-c1-effect-metrics`（不推 master、不 force） |
| 回填一致性核对 | 见 §17.2 |

> **后续修正规则**：任何进一步的措辞修正一律**追加提交**（不 amend、不 force）；修正提交的 sha 见 `git log --oneline -- reports/R46-c1-effect-metrics-20261101.md` 的第 1 行，**定稿 sha 仍指上表的值**（它承载全部数据与结论）。

### 17.2 回填核对命令（第三方可复核）
```bash
git log --oneline -3 -- reports/R46-c1-effect-metrics-20261101.md
git rev-parse HEAD; git ls-remote --heads origin feat/r46-c1-effect-metrics
```
