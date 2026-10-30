# R28 · 称呼 × 关系演化：把「可判」的前置修好（N-15 预登记 / N-16 对齐 / N-17 对拍 / 现场截图）

| 项 | 值 |
|---|---|
| **报告性质** | **本轮未跑批、未调用任何 LLM**。全部工作 = 只读核算（N-17 口径对拍、N-16 事件流对齐）+ 对**既有**真 LLM 日志的现场渲染截图 + 一份出数前写死的预登记件。**`code/{life,orchestration,config,engine}` 冻结区零改动**。 |
| **作者** | round-closer（实验报告成稿与交付收口专家） |
| **写作时间** | 2026-10-30 +0800（第 28 轮） |
| **本轮分支 / HEAD** | 分支 `feat/round-D10-address-drift`，成稿时 HEAD = `2ad74a56c7d8570bfd10d7b55e55ce40ecc8bac6`（本报告自身所在 commit 的 sha 由交付回报给出——报告无法包含自己的 sha） |
| **审计状态** | **自审已做**（每个数字在 §附录 A 给出可重放命令与实测输出）；**未做**独立第三方复核（本轮无 reviewer 席位指派）。凡未复核的项均按「不可判」处理。 |
| **维度编号** | 沿用 `reports/D10-address-drift-20261030.md` 的 **C-A（称呼与关系演化）** 临时命名，**不新造 F-9**；本轮不新增任何 F 编号维度 |

---

## 0. 一句话结论

**本轮没有提升任何效果层指标——一个都没有测，也没有一个能测。**

本轮的产物全部是「**把『称呼随关系演化』从不可归因推到可判、但在当前采样结构下功效不足**」的前置：① 证明 D10 的 `addr_error_rate` 与官方 `L-10 self_address_error` **不是同一个量**（分子逐条零重叠、分母差一个量级），从此不能再拿 `L-10=0` 去背书「称呼没问题」；② 把 `RELATION_CHANGE` 事件流与称呼序列做了**第一次逐对对齐**（见 §4）——结论是「**可判事件够（44 / 42 条，≥30），可判片段不够（10 / 14 个，<30）**」，因此本轮**只报计数、不报百分比**，并据此证明 `n16 r24` 这个采样结构**功效不足**；③ 对既有真 LLM 日志现场渲染 4 张真实截图；④ 把 N-15 判据阈值**在起跑前**写死。

**因此下一轮 N-15 必须先解决两件事**（不是「跑一次就行」）：
- **（i）摆动口径的新尺子**——现有 `address_drift.py` 的 `examples` 被截断到 20 条（`:320`），单调口径又已证会漏摆动 ⇒ 必须新增 `tools/metrics/addr_swing.py`（`S-1`），出数前冻结 sha；
- **（ii）采样结构导致的片段稀释**——`n16 r24` 下 191 条 MSG 摊给 272 个有向对，同一个「before→after」被多个关系事件重复计数 ⇒ 规模必须抬到 `n16 r84`，且报告必须同时给**不重复片段数**，否则「变化 N 次」会被误读成 N 个独立样本。

**不得写成因果，也不得写成「生活气息提升」**：本轮没有干预臂、没有对照臂、没有两次独立采样 ⇒ **不能**说「关系变化导致称呼变化」，也**不能**说「称呼有问题 / 没问题」，更不能说生活气息有任何变化（本轮没测效果层任何一项）。本轮能说的只有一句：**下一轮（N-15）第一次具备了可判的前提，且已知它只能检出 `Δ ≥ +20pp`。**

---

## 1. 假设与预登记

本轮**不产生**任何新效果假设；本轮存在的唯一假设件是**下一轮**的：

- **`v2/refs/N15-prereg-addr-evolve-20261030.md`**（455 行，42699 bytes，作者 prereg-author，落盘时刻 2026-10-30 22:06）
  - H1：在对话提示词里加一行「熟了以后别再一直用最初那个称呼」⇒ 同一有向关系（甲→乙）线程内**称呼摆动对率 `S-1`** 相对 OFF 臂上升。
  - H0：称呼只由人格模板 + 词表决定，与相处轮次/关系值无关 ⇒ `S-1(ON) − S-1(OFF) ≈ 0`。
  - 主判据 `S-1 = addr_swing_pairs_rate`，统计单位 = **有向说话对 × 线程（仅 `MSG_DM`）**，每份读数必须写成 `分子/分母 (百分比)` 形态。
  - 可检出线 **`Δ ≥ +20pp`**（α=.05 双侧、power≈.80，基于 `n16 r84` 实测分母 43/50）。**低于该线一律判 `不可判（功效不足）`，不得判 `未达标`。**
  - 护栏 `G1`（`L-7` 8-gram 重复率）、`G2`（`addr_error_rate` **与官方 L-10 并列**）、`G3` 覆盖、`G4` 闲聊量、`G6` 两臂 `dialogue` 真调用率 = 100%、`G7` 实例边界。**`G1`/`G2` 并列是 CYCLE-34 对 N-15 的硬要求**，本轮 §3 的对拍正是为 `G2` 的并列打好地基。
  - 判定格 J-1…J-9 逐格写死；`Δ ≤ 0` 才是 `未达标`；机制/批次问题**不得**写成 `无效`。
  - 可行性结论：**能跑**。缺 3 件实现物（开关 `LIFE_PROMPT_ADDR_EVOLVE`、`tools/metrics/addr_swing.py`、接线预检件）+ 1 项 `CANNOT-VERIFY`（账余额/鉴权，验证必须真发一次请求，本轮纪律禁止）⇒ **不属环境阻塞**。

> 报告纪律：本报告全文不出现 `更有生活气息` / `更自然` / `改善` / `提升` / `显著` 等效果词来修饰本轮产物；N-15 预登记件 §1 已把这条写成硬纪律，本报告沿用。

---

## 2. 数据来源

本轮读取的日志**全部是历史既有真 LLM 跑批**，本轮未新增任何一次 LLM 调用。逐份给身份：

### 2.1 N-17 对拍用（D10 称呼线引用批，`n16 r24`，5 份）

| key | `run.jsonl` 路径 | `run.jsonl` sha256 | `code_sha` | 规模 | 模型 |
|---|---|---|---|---|---|
| `d9m-ab-off` | `v2/evidence/d9m-ab-off_n16r24_s42/run.jsonl` | `5f1dda97633ccf0b3f7d2b279c39a43752db7d945a2ca6f9133e0b2bc9106ed5` | `3176048a39f0429204adbdb9eac7a975bfe10c72` | 191 MSG / 16 居民 × 24 回合 / seed 42 | DeepSeek-Flash |
| `d9m-ab-on` | `v2/evidence/d9m-ab-on_n16r24_s42/run.jsonl` | `2edc751c5a32d1328ed5834ab169d29c5c457cbe7b1d5abe3146d7840df6a795` | `3176048a39f0429204adbdb9eac7a975bfe10c72` | 191 MSG / 16×24 / seed 42 | DeepSeek-Flash |
| `d9s-off` | `v2/evidence/d9s-off_n16r24_s42/run.jsonl` | `bd6623c209641bbeff1f72df6e0e843d756ef395eb7898571acf3dae0ad4be4c` | `05526e0d9ec9775876b6c7c5764fa70fa4c5b26a` | 191 MSG / 16×24 / seed 42 | DeepSeek-Flash |
| `d9s-on` | `v2/evidence/d9s-on_n16r24_s42/run.jsonl` | `0a50484d0fce2933fbc87bd20bedae93d8f3d1d233310d2a8c005d1e0bdef4d9` | `05526e0d9ec9775876b6c7c5764fa70fa4c5b26a` | 191 MSG / 16×24 / seed 42 | DeepSeek-Flash |
| `round1` | `v2/evidence/round1_narration_default_n16r24_s42/run.jsonl` | `ca108da9f90031f7d8b9dbc346518898e48976c33ec0965737ca80255cb6e37b` | `dfe6d5b283a9e37f9d3f2373e1b8224fd15d609f` | 191 MSG / 16×24 / seed 42 | DeepSeek-Flash |

共同事实（各 `meta.json`）：`provider = openai_compat`、`endpoint_host = 172.16.3.41:31809`、`llm_calls = 2252`/臂、`degraded_calls = 0`、`fallback_detected = false`、`code_sha == code_sha_end`、`llm_purposes = {dialogue 191, importance 1523, judge 425, negotiation 7, plan 16, reflect 90}`。

**缓存回放率（必须同行，否则「两臂的差」连「同条件下的差」都不算）**：`d9m-off` `cached = 2252/2252 = 100.00%`（**零真实调用，纯回放**）、`d9m-on` `2209/2252 = 98.09%`、`d9s-off` `2226/2252 = 98.85%`、`d9s-on` `2088/2252 = 92.72%`、`round1` `1387/2252 = 61.59%`。

### 2.2 现场截图用（2 批，均为真 LLM 跑批）

| 批次标签 | run 目录 | `run.jsonl` sha256 | `code_sha` | 规模 | 模型 | 调用 / 真调用 |
|---|---|---|---|---|---|---|
| `R34-n16r84-f3on` | `v2/evidence/cycle34_f3_on_n16r84_seed42` | `b6cacdaf975a178ca3f950df9b905b5734cd8aa58298359ed09fac6ba25cffee` | `80009f4fb2213e68785c5c89bbe3462c87dcac5b` | n16 r84 seed42 | DeepSeek-Flash | `3403` / **`1737`**（`cached_ratio = 0.4896`） |
| `R34-D10-addr` | `v2/evidence/d9m-ab-on_n16r24_s42` | `2edc751c5a32d132…`（同 §2.1） | `3176048a…` | n16 r24 seed42 | DeepSeek-Flash | `2252` / **`43`**（`cached_ratio = 0.9809`） |

> 第二行是 §2.1 同一份日志的复用（D10 称呼线的代表批），**不是新批**；这一点在 §5 与截图件 `render_summary.md` 中同样写明。

---

## 3. N-17：`addr_error_rate` vs 官方 `L-10 self_address_error` 逐份对拍

产物：`v2/evidence/addr_calib/n17_calibration.json` + `n17-calibration.md`；对拍器 `tools/addr_calib/n17_calibrate.py` sha256 `cf8441906d03d461510a3fab5cf72db8f062de50ae426ca27b96ca4d2090c46a`。

### 3.1 结论（不是「两个口径不一致要修一个」）

**这两个数不是同一个量，不能互相替代。** `addr_error_rate` 测「**在呼语位把谁叫成谁**」（叫成自己 = `self_name` / 叫成第三者 = `other_named`）；官方 `L-10` 测「**用第一人称把自己说成别人**」（正文 `我(是|叫|乃|就是)?<他人名>`）。**事件方向相反**：一个是「叫谁」，一个是「说我是谁」。

### 3.2 逐份对拍表（同一批日志，两口径各算一次；单位均为 **MSG 条**）

| run | addr 分母（呼语位具名且指向可判） | addr 分子（自称 + 错称） | `addr_error_rate` | 官方分母（含自称代词或他人名） | 官方分子 | `L-10` |
|---|---|---|---|---|---|---|
| `d9m-ab-off` | 59 | 2（self 0 + other 2） | 2/59 = 3.39% | 174 | 0 | 0/174 = 0.00% |
| `d9m-ab-on` | 67 | 0 | 0/67 = 0.00% | 172 | 0 | 0/172 = 0.00% |
| `d9s-off` | 68 | 2（self 2 + other 0） | 2/68 = 2.94% | 165 | 0 | 0/165 = 0.00% |
| `d9s-on` | 70 | 6（self 5 + other 1） | 6/70 = 8.57% | 172 | 0 | 0/172 = 0.00% |
| `round1` | 74 | 1（self 1 + other 0） | 1/74 = 1.35% | 172 | 0 | 0/172 = 0.00% |

**两口径分子逐条零重叠**（`crosstab.both_num = 0`，5 份全部）；分母规模差一个量级（59–74 vs 165–174）。全部分母 ≥ 30，故上表可按百分比表述；若未来某份分母 < 30，按全族纪律只报事件数。

### 3.3 五条机制归因（每条都能落到具体行/具体标签）

| # | 差异 | 机制 |
|---|---|---|
| 1 | 分母差一个量级 | 官方分母 = 「含自称代词 **或** 含他人名」的消息数，天然接近全量 MSG；addr 分母只收「呼语位命中具名 **且** 指向可判」 |
| 2 | 分子方向相反 | addr 要「呼语位出现名字」；官方要「我 + 判断词 + **他人**名」⇒ 说话人拿**自己**名字当呼语（如 P013 说「铁头，…」）结构上永远进不了官方分子 |
| 3 | 预处理不同 | addr 先剥说话人标签前缀与 `（…）` 括注；官方**不剥**⇒ 括注里的名字被官方算作「提到他人」，抬高分母 |
| 4 | 名字集合不同 | 官方只用 `personas.json` 基名（不含 `石叔`/`石师傅` 后缀变体）；addr 用 `v2/refs/address-ordinal.yaml` 词表家族（sha256 `dc4ce327…22d95`） |
| 5 | 实现位置与任务书描述不符 | `grep -rn 'self_address_error' code/` 空结果；唯一实现在 `tools/d5/dialogue_metrics.py:919-932`、`:1011-1012` |

### 3.4 尺子未漂移（**不是**「两口径一致」）——D10 已发布读数可复算

5 份日志的 `addr_error_rate` 与 D10 已发布读数 `v2/evidence/d10_address_drift/<run>.json` **逐位一致**（`2/59`、`0/67`、`2/68`、`6/70`、`1/74`），且「同尺子 sha=True、同日志 sha=True」。⇒ D10 的 5 个读数**可复算**，不是一次性产物。

### 3.5 本轮能说 / 不能说

- **能说**：D10 的 5 个 `addr_error_rate`（分母 59–74，均 ≥30）是**称呼错指率**的描述量。
- **能说**：官方 `L-10` 在 5 份日志里**分子恒为 0**（分母 165–174）⇒ 「我(是/叫)别人名」这类自述错误在本配置下**未出现**；也正因恒零，**它对本维度没有区分力**。
- **不能说**：「`L-10 = 0` ⇒ 称呼没问题」。这两件事无关。
- **不能说**：两口径之差是「实现 bug」。它们是不同构念，差是**定义差**，不是缺陷。
- **不能说**：D10 §0.5 的 5 个读数就是「官方 L-10 的另一种算法」。

### 3.6 ⚠️ 必须同行的警告：`L-10` 恒零 ⇒ 无区分力 ⇒ 只能「并列披露」，不能当判据

> **官方 `L-10 self_address_error_rate` 在本批 5 份日志里分子恒为 `0`**：`0/174`、`0/172`、`0/165`、`0/172`、`0/172`（分母 165–174，单位 MSG 条）。
>
> 因此它**对本维度没有区分力**——一个在两臂里都恒为 0 的读数，无法区分「称呼有没有问题」。
>
> **禁止**用「`L-10 = 0`」背书「称呼没问题」；也**禁止**把 `L-10` 上升/不上升写成「称呼错指改善/恶化」。
>
> 这条是下一轮 N-15 **护栏 `G2` 的口径限制**：`G2` 中 `L-10` **只能作为「并列披露」项**（同屏出现、供读者自查），**不能**单独充当判据；`G2` 的实际判定只能看 `addr_error_rate`（`ON − OFF ≤ +2.0pp`，且 `Δ ≥ +3pp` 视为击穿）。若下一轮出现「`addr_error_rate` 未升但 `L-10` 升」的情形，按 `G2` 击穿处理（保守方向），但该情形下**必须在报告里注明 `L-10` 是另一构念**，不得解释为「称呼错指」。这一点已同步进 §6「下一步」。

---

## 4. N-16：`RELATION_CHANGE` 事件流 × 称呼序列对齐

产物：`v2/evidence/addr_relation/n16_alignment.json`（2.1 MB，含全部逐条行）+ `n16-alignment.md`；对齐器 `tools/addr_relation/n16_align.py` sha256 `bfebbf433fba29400721d4acdc7b467d5f5c4ace9122b35fb4062045082b8365`；称呼尺子复用 `tools/metrics/address_drift.py`（`37a5dc52…dcc0c`，**未改一行**）+ 词表 `address-ordinal.yaml`（`dc4ce327…22d95`）。

### 4.1 结论：**可判事件够，可判片段不够** ⇒ 只报「N 个片段里 M 个变了」

- **可判事件**：`d9m-ab-off` **44 条**、`d9s-on` **42 条**——两端都 **≥30**，所以「对齐」这件事本身是成立的。
- **可判片段**：这些事件背后**不重复的片段（有向对 × before/after 形式）只有 `10` / `14` 个**——两端都 **<30**，且被关系事件**重复计数**（单片段最大重复 13 次 / 6 次）。

⇒ 按全族纪律（分母 <30 只报事件数），本轮**不报任何百分比、不报趋势**，只写「**N 个片段里 M 个变了**」：`d9m-ab-off` 是「**10 个片段里 1 个变了**」，`d9s-on` 是「**14 个片段里 0 个变了**」。

逐份计数（单位：事件条 / 片段个）：

| run | 事件总数 | 对齐成功 | 有变化 | 无变化 | 丢配合计 | 不重复片段 | 片段内真变了 | 单片段最大重复 |
|---|---|---|---|---|---|---|---|---|
| `d9m-ab-off` | 3115 | **44** | **2** | 42 | 3071 | **10** | **1** | 13 |
| `d9s-on` | 3116 | **42** | **0** | 42 | 3074 | **14** | **0** | 6 |

**事件字段缺失 = 0、时间戳不可比 = 0**（`seq` 稠密性与哈希链均已实测，非假设）。

### 4.2 对齐表（分母即事件数；坐标轴可核性已实测）

| run | 事件总数 | 对齐成功（可判） | 有称呼变化 | 无称呼变化 | 丢配合计 | 对方未再发声 | 称呼未具名 | 变化前无基线 | 字段缺失 | 时间戳不可比 |
|---|---|---|---|---|---|---|---|---|---|---|
| `d9m-ab-off` | 3115 | **44** | **2** | 42 | 3071 | 2819 | 140 | 112 | 0 | 0 |
| `d9s-on` | 3116 | **42** | **0** | 42 | 3074 | 2820 | 125 | 129 | 0 | 0 |

坐标口径：事件与称呼**共用同一个 `seq` 轴**（同一条哈希链、稠密自增，`seq` 范围 `0–33849` / `0–33883`）。⇒ 「时间戳不可比」在本批为 **0**，是实测而非假设。

### 4.3 独立性诊断（**必须先于 4.2 阅读**，这是本件最有价值的一张表）

| run | 对齐成功事件 | 涉及的不同有向对 | **不重复片段**（对 × before/after） | 其中称呼真变了 | 单片段最大重复次数 |
|---|---|---|---|---|---|
| `d9m-ab-off` | 44 | 10 | **10** | **1** | 13 |
| `d9s-on` | 42 | 14 | **14** | **0** | 6 |

机制：`RELATION_CHANGE` 在 `round 0–23` 密集发生（familiarity 每遇到一次 +1），同一对居民的 20–28 个关系事件夹在**同一对**称呼之间 ⇒ 同一个「before→after」被数很多次。**「变化 2 次」≠「2 个不同的关系变化引发了 2 次称呼变化」**。

唯一一个「称呼真的变了」的片段（`d9m-ab-off`）：`P011→P014`，`巧儿(tier3)` → `巧儿姐(tier2)`，被 2 个事件共用（`seq 1659` familiarity `1→2`、`seq 2014` familiarity `2→3`）。原文：「巧儿姐你这铁花子溅得我眼馋…」。这只是**一个片段**，不能当「关系驱动称呼」的证据。

### 4.4 按关系维度拆（同一批事件按 `payload.dim` 分箱，仍是事件数）

| run | dim | 事件数 | 对齐成功 | 有变化 | 无变化 |
|---|---|---|---|---|---|
| `d9m-ab-off` | familiarity | 2688 | 30 | 2 | 28 |
| `d9m-ab-off` | affinity | 369 | 10 | 0 | 10 |
| `d9m-ab-off` | trust | 45 | 2 | 0 | 2 |
| `d9m-ab-off` | respect | 13 | 2 | 0 | 2 |
| `d9s-on` | familiarity | 2688 | 31 | 0 | 31 |
| `d9s-on` | affinity | 369 | 5 | 0 | 5 |
| `d9s-on` | trust | 46 | 1 | 0 | 1 |
| `d9s-on` | respect | 13 | 5 | 0 | 5 |

### 4.5 强变化子集（`|after − before| ≥ 3`）

| run | 强变化事件数 | 其中对齐成功 | 有变化 | 无变化 |
|---|---|---|---|---|
| `d9m-ab-off` | 409 | 14 | 0 | 14 |
| `d9s-on` | 411 | 11 | 0 | 11 |

⇒ 关系值变化幅度大的那批事件里，**没有一个**伴随称呼变化。这仍然只是计数，不能读成「大变化也不影响称呼」。

### 4.6 丢配原因（为什么「丢配」不等于「关系没影响」）

| 类别 | 判定（写死在 `align()`） | 本批规模 |
|---|---|---|
| 对方未再发声 | 事件 `seq` 之后该有向对**完全无 MSG** | 2819 / 2820 |
| 称呼未具名 | 之后有 MSG 但无 `target_ok` 呼语位具名称呼 | 140 / 125 |
| 变化前无基线 | 事件之前该有向对没有具名称呼 | 112 / 129 |
| 字段缺失 / 时间戳不可比 | `payload.from/to` 或 `seq` 为空 / `seq` 不稠密 | 0 / 0 |

丢配的主因是**采样结构**：每对居民全批只有 191 条 MSG 要分给 272 个有向对，且关系事件在 `round 0–23` 均匀密集发生 ⇒ 大多数有向对在某个关系事件之后**根本没再发过言**。这不是「关系没影响」，是「没观察到」。

### 4.7 无向对敏感性（只作敏感性，**不进判据**）

| run | 有称呼的无向对 | 对齐成功事件 | 有变化 | 无变化 |
|---|---|---|---|---|
| `d9m-ab-off` | 23 | 94 | 26 | 68 |
| `d9s-on` | 21 | 99 | 63 | 36 |

无向对会把「甲→乙」与「乙→甲」混成一条线（D10 v1 口径就栽在这里）⇒ 只列不判。

### 4.8 N-16 本轮**不能**得出的三条结论（必须一起读，不得美化）

1. **既不能说「关系变了称呼跟得上」，也不能说「跟不上」。** 不重复片段只有 `10` / `14` 个（**<30**），只能报事件与片段计数；任何「跟得上 / 跟不上」的表述都超出本轮证据。
2. **不能把丢配读成「关系无影响」。** 丢配主因是**采样结构**：每份日志只有 **191 条 MSG 要摊给 272 个有向对**，而关系事件在 `round 0–23` 密集发生（`familiarity` 每遇到一次 +1）⇒ 大多数有向对在某个关系事件之后**根本没再发过言**（`对方未再发声` 2819 / 2820 条），这是「没观察到」，不是「没影响」。
3. **不排除 H0（称呼由人格模板固定）。** 本对齐只说「事件之后第一次具名称呼」与「事件之前最后一次」相同/不同，**无法**区分 H0 与 H1（关系驱动）。另外，无向对敏感性（`26/94`、`63/99` 的「变化」计数）会把「甲→乙」和「乙→甲」跨方向串味——**这正是 D10 v1 口径栽过的坑**，因此无向对结果**只列不判**（见 4.7）。

附带的一条**限定措辞的正面事实**（不是效果证据）：唯一「真变了」的片段是 `d9m-ab-off` 的 `P011→P014`：`巧儿(tier3)` → `巧儿姐(tier2)`，被 **2 个**关系事件重复计数。强变化子集（`|Δ| ≥ 3`）共 `409` / `411` 条事件，其中对齐成功 `14` / `11` 条、**有变化 `0`** 条。

---

## 5. 现场截图（真实渲染，非旧图顶替）

产物目录：`v2/evidence/round34_addr_shots/`；渲染器 `tools/metrics/render_shots.py` sha256 `a85f2711a46bfe150d0d162361cfa7584d8d7aea9ec2fb01b344d3ec879e0b34`。

### 5.1 四张真实图片（本轮现场渲染，渲染前对同名 PNG 先 `unlink`）

| 图 | 字节 | png sha256 |
|---|---|---|
| `v2/evidence/round34_addr_shots/R34-n16r84-f3on-chat-b6cacdaf.png` | 296057 | `1afa2d515019fc1e1d3344a21c36e9e1cd84c83c6f52ab902dfa165f955c5542` |
| `v2/evidence/round34_addr_shots/R34-n16r84-f3on-rhythm-b6cacdaf.png` | 285197 | `6a15be1b1c2fe59d7bbc9d1801194f97b78e408d6a5a1c465ed9a40bfaca61e3` |
| `v2/evidence/round34_addr_shots/R34-D10-addr-chat-2edc751c.png` | 294563 | `167fd1267004a20c003489a7b3c989f2c6e32b27395bc1e1e4c3fb494c9b280c` |
| `v2/evidence/round34_addr_shots/R34-D10-addr-rhythm-2edc751c.png` | 279783 | `803e412d7c694a2ca521b6f8bf358a063786f135cbc80ca34fe02579bee5534b` |

文件名后缀 `b6cacdaf` / `2edc751c` = 对应 `run.jsonl` 的 sha256 前 8 位，便于反查日志身份。

### 5.2 空白自检（不是「看起来不空」）

`--blank-check off`（不给 `shot.py` 传单色判据），改用脚本自算：**`distinct_colors ≥ 200` 且 `top_color_frac ≤ 0.99` ⇒ OK**。4 张**全部 OK**，逐张判据见 `render_report.json` 的 `pixel_selfcheck`。两批均 `ok_count=2 / fail_count=0`。

### 5.3 可重放命令

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

python3 tools/metrics/render_shots.py \
  --run-dir v2/evidence/cycle34_f3_on_n16r84_seed42 \
  --batch-id R34-n16r84-f3on \
  --outdir v2/evidence/round34_addr_shots \
  --views chat,rhythm --timeout 180 --retry-blank 2

python3 tools/metrics/render_shots.py \
  --run-dir v2/evidence/d9m-ab-on_n16r24_s42 \
  --batch-id R34-D10-addr \
  --outdir v2/evidence/round34_addr_shots \
  --views chat,rhythm --timeout 180 --retry-blank 2
```

附带件：`render_report.json`（两批合并）、`render_report_R34-D10-addr.json`、`render_report_R34-n16r84-f3on.json`、`render.log` + 分卷 `render_d10_addr.log` / `render_n16r84_f3on.log`、`threads_R34-D10-addr.json`、`threads_R34-n16r84-f3on.json`（后者 4.6 MB，内容量随 n16r84 规模）。

### 5.4 截图的限定（防止被当成「效果证据」）

截图**只是可读性证据**，不是效果证据：它们是**两份既有日志的只读可视化**，两批不同 `code_sha`（`80009f4f` vs `3176048a`）、不同规模（n16r84 vs n16r24）⇒ **两张图之间不可比较**，不得并列讲「变化」。

---

## 附录 A · 本轮亲自复算的量

以下每条都是 round-closer **本人在本轮亲自执行**的命令与实测输出；未执行的一律标注原因，不转述他人的输出当自己的。

### A.1 addr 侧独立复算（`d9s-on`）

```bash
python3 tools/metrics/address_drift.py --log v2/evidence/d9s-on_n16r24_s42/run.jsonl \
    --out-json /tmp/rc_a.json --out-md /tmp/rc_a.md
```

实测输出：`addr_misaddress.addr_error_rate = 0.08571428571428572`、`n_named_addr_judgeable = 70`、`addr_target_distribution = {target_ok: 64, self_name: 5, other_named: 1}`、`tier 分布 {1: 21, 2: 13, 3: 37}`。
⇒ **6/70 = 8.5714%**，与 N-17 §3.2 表 `d9s-on` 行、与 D10 已发布读数 `6/70` **逐位一致**。

### A.2 官方口径独立复算（`d9s-on`）

```bash
python3 tools/d5/dialogue_metrics.py --log v2/evidence/d9s-on_n16r24_s42/run.jsonl \
    --meta v2/evidence/d9s-on_n16r24_s42/meta.json \
    --out-json /tmp/rc_b.json --out-md /tmp/rc_b.md
```

实测输出（`L_wording` 块）：`L-10_denominator = 172`、`L-10_self_address_error_rate = 0.0`（同块 `L-11_second_person_rate_dm_group = 0.844311`）。
⇒ **0/172 = 0.00%**，与 N-17 §3.2 表 `d9s-on` 行一致。命令 rc=0。
（`--meta` 必须带：缺它会触发「非证据级」判 `REJECTED`，那是准入开关伪影，不是数据问题。）

### A.3 日志身份与规模（5 份 + 截图 2 批）

```bash
sha256sum v2/evidence/{d9m-ab-off,d9m-ab-on,d9s-off,d9s-on,round1_narration_default}_n16r24_s42/run.jsonl
sha256sum v2/evidence/cycle34_f3_on_n16r84_seed42/run.jsonl
```

⇒ 6 个 sha256 全部与 §2 表**逐字符一致**；`meta.json` 的 `code_sha`、`code_sha_end`、`llm_calls`、`llm_cached`、`fallback_detected=false`、`degraded_calls=0` 亦逐份核对（§2.1 / §2.2 的数字即由此得到）。

### A.4 官方 L-10 实现位置

```bash
grep -rn "self_address_error" code/
```

⇒ **空输出**（推翻任务书「实现在 `code/obs/`」的说法）；唯一实现位于 `tools/d5/dialogue_metrics.py:919-932`、出数在 `:1011-1012`（由 N-17 读码定位，§A.1/A.2 的实测输出可从该实现复现）。

### A.5 `RELATION_CHANGE` 事件数与 MSG 数独立复算（不使用任何 `tools/` 现有脚本）

```bash
python3 - <<'PY'
import json, collections
for f in ['v2/evidence/d9m-ab-off_n16r24_s42/run.jsonl',
          'v2/evidence/d9s-on_n16r24_s42/run.jsonl']:
    c = collections.Counter(); msg = 0
    for line in open(f, encoding='utf-8'):
        e = json.loads(line); t = e.get('type') or e.get('event'); c[t] += 1
        if isinstance(t, str) and t.startswith('MSG'): msg += 1
    print(f, 'RELATION_CHANGE=', c.get('RELATION_CHANGE'), 'MSG=', msg, 'total_events=', sum(c.values()))
PY
```

实测输出：
`v2/evidence/d9m-ab-off_n16r24_s42/run.jsonl RELATION_CHANGE= 3115 MSG= 191 total_events= 33850`
`v2/evidence/d9s-on_n16r24_s42/run.jsonl RELATION_CHANGE= 3116 MSG= 191 total_events= 33884`
⇒ 与 N-16 §1 的 `3115 / 3116`、`191`、`seq 范围 0–33849 / 0–33883`（即 `总事件数 − 1`）**逐位一致**。

### A.6 两个只读核件自检（`--selftest`，不触网、不写仓）

```bash
python3 tools/addr_relation/n16_align.py --selftest
python3 tools/addr_calib/n17_calibrate.py --selftest
```

实测输出：
`[selftest] aligned: 1 lost: 1 lost_by_reason: {'对方未再发声': 1} changed: 1` / `[selftest] forms: 秀娘 -> 秀婶 changed: True` / `[selftest] PASS (failures=0)`
`[selftest] addr: 1 / 1 official: 1 / 1` / `[selftest] PASS (failures=0)`
⇒ 两个核件在合成样例上都能各自触发「变化」「丢配」与两口径命中，`failures=0`。**这是自检，不是对真日志的复核**——真日志的复核见 A.1 / A.2 / A.5。

### A.7 出数人本人执行的两条正式命令（**转述，非 round-closer 执行**）

以下两条由 **addr-analyst（出数人）本人**在本轮执行，round-closer **未重复执行**（本人执行的是 A.1 / A.2 / A.5 / A.6，与这里口径不同：A.1/A.2 是单份日志的单侧复算，A.6 是合成样例自检）。此处记录**执行人归属**，避免把别人的执行冒充成自己的：

| 命令 | 执行人 | 记录结果 |
|---|---|---|
| `python3 tools/addr_calib/n17_calibrate.py --selftest` | addr-analyst | **PASS** |
| `python3 tools/addr_calib/n17_calibrate.py` | addr-analyst | **rc=0**，5/5 份日志的复刻校验 PASS（addr 复刻 vs `compute()`、官方复刻 vs CLI 各 5 次全 PASS） |
| `python3 tools/addr_relation/n16_align.py --selftest` | addr-analyst | **PASS** |
| `python3 tools/addr_relation/n16_align.py` | addr-analyst | **rc=0**（默认 2 份日志） |

> 说明：`--selftest` 一项 round-closer 也在 A.6 中实跑过并得 `failures=0`，属**交叉一致**；正式出数命令（不带 `--selftest` 的两条）由出数人执行，round-closer 只核对了其落盘产物与 sha256（A.3 / §2）。

### A.8 本轮**无法**复算的量（写明原因）

| 量 | 无法复算的原因 |
|---|---|
| N-15 的 `S-1` / `S-2` 摆动读数 | **开关 `LIFE_PROMPT_ADDR_EVOLVE` 尚未实现**（`grep -rn ADDR_EVOLVE code/ tools/` 零命中），且 `tools/metrics/addr_swing.py` 尚不存在 ⇒ 主判据连尺子都还没有。这是下一轮的首项，不是本轮遗漏。 |
| 官方 `L-10` 的**鉴权/配额**可用性 | 验证必须真发一次 LLM 请求，本轮纪律禁止调用 LLM ⇒ 只能声明「端点 TCP 可达 + 历史同端点同模型真跑成功」，**不声明现在能鉴权**。 |
| 本轮截图之外的视图（如关系图 / 事件流图） | `render_shots.py` 本轮只要求 chat / rhythm 两视图；其他视图未经渲染，**不编造**。 |
| 独立第三方复核结论 | 本轮无 reviewer 席位，自审不能替代复核 ⇒ 标注为**未复核**。 |

---

## 6. 下一步（下一轮看板）

**首项（唯一入口）**：**N-15 `LIFE_PROMPT_ADDR_EVOLVE` 称呼演化臂真 LLM 跑批**——按 `v2/refs/N15-prereg-addr-evolve-20261030.md` §12 执行清单照抄，先补 3 件实现物再起跑：

1. 开关实现（`code/life/agent.py`，**冻结区 ⇒ 必须开新分支**，默认 OFF 且与现状逐字节等价）。
2. `tools/metrics/addr_swing.py`（`S-1`/`S-2`，`--selftest` ≥8 例，出数前冻结 sha）。
3. `tools/d9/addr_evolve_wiring.py`（`L1/L2` 的 OFF==基线逐字节证明）。

跑批前提（缺一即不得起跑或不得判 `有效`）：`pgrep` 确认无并发；OFF/ON 同 `code_sha`；冷缓存 `side-root`；串行；`dialogue` 真调用率 100%（`G6`）；`L-7` 与 `L-10` 同屏并列（`G1`/`G2`）。

**`G2` 的口径限制（下一轮必须照此执行，不得放宽）**：
- `G2` 的**唯一判据**是 `addr_error_rate`：`ON − OFF ≤ +2.0pp`，`Δ ≥ +3pp` 视为击穿。
- 官方 `L-10 self_address_error` 在本批 5 份日志里**分子恒为 0**（`0/174`、`0/172`、`0/165`、`0/172`、`0/172`）⇒ **对本维度无区分力**，在 `G2` 中**只能作为「并列披露」项**（同屏出现、供读者自查），**不能**单独充当判据。
- **禁止**用「`L-10 = 0`」背书「称呼没问题」；若出现「`addr_error_rate` 未升但 `L-10` 升」，按 `G2` 击穿处理（保守方向），但**必须**在报告里注明 `L-10` 是另一构念，不得解释为「称呼错指」。

**采样结构必须先处理（N-16 的教训）**：`n16 r24` 下 191 条 MSG 摊给 272 个有向对，关系事件在 `round 0–23` 密集发生，同一「before→after」被多个事件重复计数（单片段最大重复 13 次）⇒ 下一轮报 `S-1` 时**必须同时给不重复片段数**，否则「变化 N 次」会被误读成 N 个独立样本。规模抬到 `n16 r84` 是**必要条件而非充分条件**。

**仍被阻塞的项**（明确写清，不留空）：

| 项 | 阻塞原因 | 解除条件 |
|---|---|---|
| N-15 效果读数 | 依赖上面 3 件实现物 + 一次约 96 min、≈6800 次调用的双臂跑批 | 实现物合入 + 起跑 + `obs llm-cost --require-provider` 验真 |
| 「称呼随关系演化」的因果结论 | 本轮只做到「可判」，**没有任何干预臂** | N-15 双臂出数并通过 J-4 全格 |
| 官方 `L-10` 覆盖「称呼错指」 | `L-10` 是另一构念，且恒零；就地改定义属冻结区改动 | 新登记一个口径（不得就地改 `L-10`） |
| 独立第三方复核 | 本轮无 reviewer 席位 | 下一轮指派复核席位 |
