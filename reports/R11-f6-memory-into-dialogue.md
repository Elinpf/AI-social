# R11 · F-6「跨天记忆进对话」：一个纯装配缺口的单变量干预（n16×60 seed42，OFF vs ON）

> 性质：**两臂读数均已填实（v2 定稿版）**。骨架在 ON 臂起跑前写成（凡数字一律留花括号占位，读数到手只填空、不改表头与口径）；
> v2 已回填 ON 臂（`run_f6_on_n16r60_seed42`，15:53:13 结束、`provider_guard.ok=true`、`calls=2878`、`degraded=0`）全部读数，**模板占位符清零**；唯一仍缺的是本文件自身的 commit sha（提交后才产生），已在原处标注「未获取到 + 原因」，见附录 D。
> 锚点行：本文件首版提交见 `git log --format=%H -- reports/R11-f6-memory-into-dialogue.md`。
> 报告日期：2026-10-21 ｜ 团队轮次：ROUND-1 ｜ 维度：F-6（生活气息 · 跨天记忆引用）
> 代码 sha（本轮 F-6 实现）：`895b9a381cd5a1838c23bd3b38e139f7edade3b8`（分支 `feat/life-memory-f6-on`，与 `feat/life-memory-f6` 同树、零代码改动）
> 报告 sha：`**未获取到（原因：本文件尚未 commit；sha 由 delivery-gatekeeper 提交后以 `git log -1 --format=%H -- reports/R11-f6-memory-into-dialogue.md` 取得）**`（push 后回填）

> **尺寸留痕（本版订正，不静默改）**：骨架首版通篇写 `n8×60`（标题、§4.1 目录名 `run_f6_off_n8r60_seed42`、§5.3、§6、§6.1「次序 3 = 最终」、附录 C 全部路径），
> 实际两臂是 **`n16×60`**：依据 `v2/evidence/run_f6_off_n16r60_seed42/meta.json` 的 `n=16`、`rounds=60`、`duration_sec=5201`。
> 订正人：evidence-reporter；订正时点：ON 臂仍在跑（`pgrep` 可见 `orchestration run`）。原 `n8r60` 属**起跑前笔误**，不是看结果改口径；变更依据见 §6.1「次序 4」。

---

## 0. 摘要 TL;DR

**一句话**：本轮把 F-6 从「检索早已算好、对话提示词里却一个字都不进」的**装配缺口**，做成了一个同代码、单 env（`LIFE_PROMPT_MEMORY_F6`）、可机械自证的单变量干预；两臂均已跑完并通过真跑验真（OFF `calls=2878` / ON `calls=2878`、`degraded=0`），读数已全部填实：**F-6 升 +7.45pp（19/510 → 57/510，两臂 Wilson95 不重叠），但 L-7 同步恶化 +29.61pp（越过预注册 +5pp 闸门）⇒ 不构成生活气息的净改善**。

**已确证的（两臂 + 代码事实）**
- OFF 基线：`F-6 timeref_rate = 0.037255`（**19/510**，分母 510 ≥ 68 可报比率）；守卫 `L-6 0.101961` / `L-7 0.354902` / `L-8 0.0`；`admission = ADMITTED`（20 项 check 全 pass）。
- 真跑验真：`obs llm-cost --require-provider openai_compat` → `rc=0`、`provider_guard.ok = true`、`problems = []`、`by_provider = {openai_compat: 2878}`、`degraded = 0`、`tokens_in 228749` / `tokens_total 484835`。
- 单变量第 3 查（日志级）：OFF 臂 510 条 MSG 里 `ctx.memory_refs` 出现 **0** 次（键不存在）⇒ 开关关死时提示词路径未被触碰。
- 四张 OFF 臂真拍截图已产出（`v2/evidence/f6_shots/*-c73bead6.png`，含 sha256 与亮度/色彩占比非退化判据，见 §4.3）。
- **ON 臂（`run_f6_on_n16r60_seed42`，`code_sha 895b9a3`，14:05:57→15:53:13，`duration_sec=6436`，`events=116261`）**：`F-6 = 0.111765（57/510）`、`L-6 0.127451`、`L-7 0.65098`、`L-8 0.0`、`admission = ADMITTED`。
- ON 臂真跑验真：同样四项全过（`rc=0`、`provider_guard.ok=true`、`problems=[]`、`by_provider={openai_compat:2878}`、`calls=2878`、`degraded=0`；`tokens_in 271717` / `tokens_total 540840`）⇒ 2878 次调用**不是 mock**。
- ON 臂注入面：510 条 MSG 中 **412 条**带 `ctx.memory_refs`（824 次引用 / 128 个不同记忆）⇒ 开关端到端能翻（**只证注入，不证用上**）。
- 四张 ON 臂真拍截图已产出（`v2/evidence/f6_shots/*-7de6a7be.png`），非退化判据复算通过（亮度 24.1–38.4、`dark_frac ≤0.02%`，见 §4.3）。

**本轮核心结论之一（【事实】，可用 seq 号查证）：M-1 在 OFF 臂本身就被"自我复读"污染**
- OFF 臂 M-1 命中 **3 条**，其中 **2 条是同一说话人在几天后重复自己**：`seq 86316`(P008) 与 `seq 82424`(P008) 正文**逐字相同**（6-gram 覆盖 13/13 = 1.000）；`seq 34699`(P012) 与 `seq 28261`(P012) 共享 3 个 6-gram（覆盖 3/43 = 0.070，复述"不客气 / 肚子咕咕叫"）。
- 只有 `seq 19241`(P007) vs `seq 8348`(P007) 属真正的内容呼应（共享 1 个 6-gram，覆盖 1/37 = 0.027，把"夜里听见压着嗓子数数"后一天重提并补细节）。
- **本轮唯一主口径（读者只需记这一个）：`M-1′ = 1/33`**，判据 = **同一说话人 且 共享 6-gram ≥ 3 ⇒ 剔除**（定义、阈值理由与复算命令见 §3.6）。
  分母 33 < 68 ⇒ 该值**只作事件数级描述**，不构成比率结论。
- **另两个数只作敏感性分析 / 上界，不是第二、第三个结论**：
  - `M-1′_strict = 2/33`（严判据 `覆盖率 |A∩B|/|A| ≥ 0.5`）——**去重的下界**（只剔逐字复读）；
  - `M-1_原始 = 3/33`——**未去重的上界**（含复读，属被污染读数，仅用于说明污染幅度）。
- 意义：**"6-gram 重合"混入"复读机"的比例在本轮高达 2/3**。这比 MDE 更根本——MDE 说的是"看不看得见"，这条说的是"看见了也可能看错东西"。**任何后续 F-6 / M-1 读数都必须先去自我重复**（§7 建议 1）。

**必须提前说清的判读边界（跑批前定，非事后找补）**
- 本轮 M-1（跨天内容重合，新指标）的机会分母在 n16×60 下只有 **33**（60 回合仅跨 **5 个游戏日** `days=[0,1,2,3,4]`）⇒ 按 §0.2 分母纪律只能标 **probe / 只报事件数**。
- 以 OFF 侧 `p=3/33` 代入 §3.5b 算式：**MDE(区间不重叠口径)=19.62pp**、**MDE(power 口径)=19.83pp**，均远超骨架 §3.5b 自定的「MDE > 10pp」闸门 ⇒ 按**起跑前写死的预案**，M-1 相关结论的措辞已被锁定为「**在本样本量下无法在噪声之上判定差异**」，禁止出现任何效果性措辞。
- 因此本轮**可判定的读数只有四条**：F-6（den 510）、L-6/L-7/L-8（den 510）、token 成本（计数型）、`ctx.memory_refs` 注入面（计数型）。ON 臂的 F-6 若相对 OFF 变化，按 §3.3 判据给「显著/不显著」，但**单 seed 单批、不做跨 seed 方差**，只作方向性陈述。

### 0.1 口径澄清（防串味，三个必须分开的东西）

| 东西 | 是什么 | 不是什么 |
|---|---|---|
| **F-6** | 仓库既有指标，实现唯一来源 `tools/d5/dialogue_metrics.py:738`（11 个时间回指词表命中率，分母=全部 MSG） | 不是本轮新指标；**本轮不重写它**，只引官方脚本输出 |
| **M-1 / M-1b / M-0** | 本轮新增指标（见 §3.2），测「与同线程更早一天消息的 6-gram 实际重合」 | 不与 F-6 混称、**禁止跨指标比数值大小** |
| **`LIFE_PROMPT_MEMORY_F6`** | 本轮唯一干预开关（env，默认 OFF） | 不是「记忆功能开关」——记忆检索本来就在跑，本开关只管「检索结果进不进提示词」 |

> ⚠️ 与 R10 的 `F-2`、R4 的 `F-2「话题漂移率」` 无任何关系，勿按编号联想。
> ⚠️ **本轮另有一条同名风险**：`v2/evidence/r1_f6_compare.py`（`ctx.memory_refs` 审计 + `mem_echo`＝正文与**被注入记忆正文**的 6-gram 重合）与本文 §3.2 的 M-1（正文与**同线程更早一天消息**的重合）**不是同一指标**：分母不同（注入条数 vs 天级机会分母）、比较对象不同。二者一律分栏写，**禁止互相替代、禁止比数值大小**。

### 0.2 证据分级与分母纪律（全篇适用，先写死）

**三级证据标签**（每个论断必须落在其中一级，不得越级）：

| 标签 | 含义 | 例 |
|---|---|---|
| `【事实】` | 代码/配置/日志结构可直接验证，不依赖跑批统计 | `agent.py` 内 `grep -n` 行号、`ctx.memory_refs` 键是否存在 |
| `【读数】` | 分母达标的实测数，可比率、可做判定 | F-6（den 510）、L-6/L-7/L-8（den 510）、token（计数型） |
| `【读数·probe】` | 分母不足，**只报事件数与占比，不作判定、不进摘要结论** | M-1（den 33）、F-7（den 2） |

**分母纪律（全族统一，本轮不例外）**：
- 分母 `< 30` ⇒ **只报事件数**，禁止写百分比；
- 分母 `30 ≤ n < 68` ⇒ 标 **`probe`**，可写「x/n」与原值，但**不得作显著性判定、不得进摘要**；
- 分母 `≥ 68` ⇒ 可报率并参与 §3.3 判据。

> 本轮触线情况：M-1 机会分母 **33**（probe）、F-7 per-message 分母 **2**（只报事件数 `pos=1/2`）、F-4 分母 22（只报事件数）、F-3 分母 36（probe）。F-6 / L-6 / L-7 / L-8 分母 510，达标。

**tokens 两字段口径（都列，不二选一）**：`tokens_in`（仅入向 prompt token，`f6_metrics.py` 读 `engine_log.total.tokens_in`，用于两臂对齐）；`tokens_total`（`in + out` 合计，`obs llm-cost` 的 `engine_log.total.tokens_total` 直出，用于成本全貌）。

### 0.3 结论 → commit 绑定表

| # | 结论 | 层级 | 绑定对象 |
|---|---|---|---|
| C-1 | F-6 缺口是「检索已算好、提示词零注入」的**装配缺口**（代码事实，不依赖跑批） | 【事实】 | `895b9a3` 前树：`agent.py:450 _retrieve` ↔ `:1206/:1219` prompt 装配 |
| C-2 | 干预为「过滤后的跨天记忆一行注入」，OFF/ON 同一份代码，唯一差异为 env；OFF 侧日志级自证：510 条 MSG 中 `ctx.memory_refs` 出现 0 次 | 【事实】 | `895b9a3`；§4.6 三查；OFF `run.jsonl`（`c73bead6…`） |
| C-3 | M-1（跨天内容重合）机会分母仅 **33**（60 回合只跨 5 个游戏日）⇒ probe 级；**MDE 19.62pp > 事前闸门 10pp** ⇒ 结论锁定为「在本样本量下无法在噪声之上判定差异」 | 【读数·probe】 | `tools/f6/f6_metrics.py`（`be27a3be…`）+ OFF `run.jsonl`；§3.5b |
| **C-3b** | **M-1 的 3 条命中里 2 条是同一说话人自我复读**（`86316`=`82424` 逐字相同、`34699`≈`28261`）⇒ 原始 `M-1=3/33`、去重 `M-1′=1/33`；**6-gram 口径在本基线上有 2/3 命中是复读**，属度量效度问题 | 【事实】 | `run_f6_off_n16r60_seed42/run.jsonl` 的 `seq 19241/8348/34699/28261/86316/82424`；复算命令在 §3.6 |
| C-4 | F-6 基线（OFF）= **0.037255（19/510）**，分母达标可报比率；ON 侧对比 **0.111765（57/510）**，Δ=**+7.45pp**，Wilson95 [8.73%, 14.21%] 与 OFF [2.40%, 5.75%] **不重叠 ⇒ 按 §3.3 判为「显著」**（但同段落必须并列 L-7 恶化 +29.61pp，见 C-5 与 §5.2 D） | 【读数】 | 官方脚本 `tools/d5/dialogue_metrics.py`（§4.5 ①）|
| C-5 | 守卫项基线：`L-6 0.101961` / `L-7 0.354902` / `L-8 0.0`（den 均 510）；ON 侧 `L-6 0.127451（65/510，+2.55pp）` / **`L-7 0.65098（332/510，+29.61pp）`** / `L-8 0.0`（den 均 510）⇒ **L-7 越过预注册闸门「≤ 基线+5pp」⇒ 判为恶化（代价是套路化）**，不得写「改善了生活气息」 | 【读数】 | 官方脚本 + `obs llm-cost` |
| C-6 | OFF 臂真跑验真通过：`rc=0`、`provider_guard.ok=true`、`by_provider={openai_compat:2878}`、`degraded=0` | 【事实】 | `v2/evidence/f6_cost_off.json`；§4.2 |
| C-7 | OFF 臂四视图真拍非退化（`mean_brightness` 23.2–38.3、`dark_frac ≤0.01%`、`max_color_frac` 14.3–52.5%） | 【事实】 | `v2/evidence/f6_shots/*-c73bead6.png`；§4.3 |

---

## 1. 本轮维度与为什么选它

### 1.1 「空白是可复算的，不是形容词」——给原文

F-6 的缺口不是我们的说法，是仓库里可以直接验证的两处代码事实：

```bash
# ① 检索侧：记忆检索早就实现了（返回 top-k）
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
sed -n '450,500p' code/life/agent.py          # _retrieve() —— 算好了，还给 rank/meta
# ② 装配侧：两个对话提示词只看 persona/scene/relation/mood/rift/gossip，看不到任何记忆正文
sed -n '1206,1240p' code/life/agent.py        # _dialogue_prompt / _reply_prompt（改动前树 c1bb533）
# ③ 直接对拍：prompt 装配函数区间内 grep 记忆字样
git show c1bb533:code/life/agent.py | sed -n '1080,1101p' | grep -c "记忆\|memory"   # 实测 = 0
```

> 行号漂移说明：recon 报告记的是 `agent.py:432`/`:455`（读的是更早的树）；在 `895b9a3` 父提交 `c1bb533` 上实际是 `:450`/`:473`。**引用行号一律以本节命令的输出为准**，不要抄二手行号。

### 1.2 为什么它算「生活气息」

「像不像真的有人在过日子」，很大一部分来自**把前几天的事顺口带出来**：昨天谁送来的米、前天集市上的闲话。R4 把它列为生活气息七维之一（F-6），本轮不去造新机制，而是把**已经有的事实**（记忆已写入 `memory.nodes`）接到**已经存在的出口**（对话提示词）上。

### 1.3 本轮不做什么（边界先声明）

- 不改检索权重、不改 `score_and_rank`、不 touch / 不改 `access_count` ⇒ **对既有检索行为零影响**；
- 不碰世界态、不碰 `state_hash`、不新增事件类型（只加一个 additive 审计字段）；
- 不做 F-3 情绪呼应（另一个 prompt 装配面）、不做天气/节日（新增机制，属"广"）、不顺手收尾 G 系列（是"补完上一轮"，且会给同一次跑批叠加第二变量）。

---

## 2. 机制事实（实现，`895b9a3`）

### 2.1 干预一句话

打开 `LIFE_PROMPT_MEMORY_F6` 时，在对话提示词里**插入恰好一段**「你想起的事：第X天：…；第Y天：…」；关闭时**返回空串，A0 提示词逐字节不变**。

### 2.2 代码行号表（行号取自 `grep -n` 实跑，见 §4.5 ⑥）

| 位置 | 内容 |
|---|---|
| `code/life/agent.py:56` | `MEMORY_F6_ENV = "LIFE_PROMPT_MEMORY_F6"` |
| `:58` | `MEMORY_F6_TOP_N = 2`（每次最多注入 2 条，控 token） |
| `:60` | `MEMORY_F6_ITEM_CHARS = 60`（单条正文截断） |
| `:63-65` | `memory_f6_enabled()`：env ∈ {1,true,yes,on}，**默认 OFF** |
| `:174` | `self._mem_refs: list = []`（纯审计，不进 state_hash） |
| `:947-951` | `_ctx_snapshot()` 追加 `ctx["memory_refs"]`（**additive**；OFF ⇒ 键不出现 ⇒ payload 与 A0 逐字节一致） |
| `:1103-1199` | 新增 `_memory_line()`（取材 + 人话门 + 去重 + 排序 + 截断 + 记 `mem_id`） |
| `:1206` / `:1219` | `_dialogue_prompt(..., wv=None)` / `_reply_prompt(..., wv=None)` 各自插入 `mem_line` |

改动量：`1 file changed, 135 insertions(+), 4 deletions(-)`（`git show 895b9a3 --stat`）。

> 📌 **行号漂移提醒**：recon 报告记的是 `agent.py:432`（`_retrieve`）/`:455`（`_retrieval_query`），那是更早的树；在 `c1bb533` 上实跑为 **`:450` / `:473`**。**本报告一律用实跑输出**（§4.5 ⑥），读者核对时如与二手行号对不上，以上表为准。

### 2.3 取材规则（确定性，与 RNG 无关）

- 只读 `self.memory.nodes`，**只要跨天**：`node.day < 当前 day`（当天的"新鲜事"不算"想起来"）；
- 排序键固定 `(kind: observation 优先 → other, day 新→旧, importance 高→低, 去重键升序)` ⇒ replay 稳定；
- 去重：去尾部括注（如「（insight 3）」）后同键只留一条；同一句台词换说话人只留一条；
- 不排除「正在对话的对象」：`昨天阿禾说…` 正是最像过日子的引用（排除后几乎剩不下内容）。

### 2.4 人话门（**这是干预的一部分，不是实现细节**）

记忆流里大量条目是原始事件短语（形如 `P001 的 RELATION_CHANGE 事件。`、`P003 在 residence 开始 rest。`）。原样注入等于把内部 token 喂给模型（会制造 L-8/L-13 回归），故 `_memory_line()` 内置第二道门：`Pxxx`→显示名；含 ASCII 词（≥3 字母）/「事件」/全大写 token ⇒ 丢弃；去空白后 < 6 字 ⇒ 丢弃。

**可用率的数字**：`471` 条记忆节点、人话可用约 `13%`（`55/413` 跨天条）。
- 层级：**【读数 · mock 探针】**，口径 `n4×60 mock`；
- 来源状态：仅见 `round1/status-off-launch.md §6` 的叙述，**无原始日志/输出文件落盘** ⇒ **本报告不把它写成结论**，只在 §5.3 作为"设置人话门的动机"引用，并标注「不可独立复核」；
- 复算入口：见 §4.5 ⑦。**当前状态：无脚本、无原始输出** ⇒ 保持「不可复核」标记。
  **补救计划（Leader 已批，不打断当前批）**：若该探针是纯读 node store、零 LLM 调用，跑批结束后用一条命令把命中/未命中明细 dump 成 `v2/evidence/f6_human_gate_probe.txt`，下轮即可升为可用证据；**若发现任何副作用（写盘/发事件/耗 token）则放弃，只列下一轮建议**。

### 2.5 事件 → 可观测字段

| 观测点 | 落点 | 复算 |
|---|---|---|
| 本次装配实际注入了哪些记忆 | MSG payload `ctx.memory_refs`（`mem_id` 列表） | `python3 - <<'PY'` 统计 ON 臂含 `memory_refs` 的 MSG 数（§4.5 ④） |
| 注入的记忆正文 | 可回 `run.jsonl` 的 `MEMORY_WRITE` 按 `mem_id` 还原 `day/slot/text` | 同上 |
| 效果（是否真被引用） | 不能由 `memory_refs` 证明 ⇒ 只能用 M-1/M-0 的语言重合间接观察 | §3.2 |

> ⚠️ `memory_refs` 只证「注入了」，**不证「被用上了」**。这是本报告最重要的一条观测边界。

---

## 3. 指标定义与实测表

### 3.1 F-6（沿用仓库定义，官方脚本唯一来源）

- 分子：正文命中 11 个时间回指词表任一词的消息数；分母：全部 `MSG_DM/MSG_GROUP/MSG_PUBLIC` 消息数；
- 唯一来源：`tools/d5/dialogue_metrics.py:738` → `F-6_crossday_memory.timeref_rate`，本报告**不重写实现**；
- 本轮值只作两臂内部对比；`6.4%` 的历史值（出处：`reports/R4-life-texture.md:61`，`run_d2_after_n16_seed42`，`code_sha 884f4541`）跨 `code_sha`（`884f4541` → `895b9a3`），**只写「历史参照（跨 code_sha，不可直接等同）」，禁止写成「从 6.4% 提升到 X%」或任何等价比**。

- **连分母一起说清楚（为什么它连"内部对照"都不适合当锚点）**：`R4:61` 那一行的分母是 **187 条消息**，`6.4% × 187 ≈ 12 条命中`。用小分母算 Wilson 95% 区间：

  ```bash
  python3 -c "
  import math
  z=1.959963984540054; k,n=12,187
  p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d
  h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
  print('p=%.4f%%'%(p*100), 'CI=[%.2f%%, %.2f%%]'%((c-h)*100,(c+h)*100), 'halfwidth=%.2fpp'%(h*100))
  "
  # 实测输出：p=6.4171% CI=[3.71%, 10.88%] halfwidth=3.59pp
  ```

  ⇒ **半宽 ≈ 3.6pp**，即"6.4%"背后是「区间跨 3.7%–10.9%、只有 12 条命中」的读数。**本轮不拿它当对比锚点，不是回避，而是它本来就不够稳**：任何小于 3.6pp 的差异在这个分母下都无法与噪声区分。

### 3.2 M-1 / M-1b / M-0（本轮新指标，作者定义）

| 指标 | 分子 | 分母 | 角色 |
|---|---|---|---|
| **M-1 本轮记忆引用率** | 正文 6-gram 与「同线程**更早一天**消息正文 6-gram」有交集的消息数 | `day>=1` 且同线程存在更早一天消息的消息数（**机会分母**） | 主口径 |
| **M-1b** | 同上分子 | 全部 `day>=1` 消息数 | 副列，同报不引用 |
| **M-0 同日对照** | 正文 6-gram 与「同线程**同一天**更早消息」有交集 | `day>=1` 且同线程存在同日更早消息 | 对照列；期望≈0；若与 M-1 同量级 ⇒ M-1 抓到的是**共享模板句式**，须写进局限 |

线程键：`payload.thread_id`；缺失时 DM 用 `sorted(from,to)`、GROUP 用 `group_id`、PUBLIC 用 `public|from`。预处理：去空白与中英文标点后切 6 字窗口。
与 F-6 的三点差异（必须写进报告）：①F-6 只看 11 词固定表，M-1 看与旧消息的实际语言重叠；②分母不同（全 MSG vs 机会分母/`day>=1`）；③M-1 能捕捉复述旧话，但**不证明语义引用正确**。

### 3.3 噪声与「显著」（事前定死，不得事后改）

- 率类（M-1/M-1b/M-0/交叉核对时间回指）：二项 **Wilson 95% 区间**（z=1.959963984540054），报 `Δ(pp)` + 两区间是否重叠；
- 判定：`|Δ| >= 1pp` **且**两臂 Wilson95 区间**不重叠** ⇒ 判「显著」，否则「不显著」；
- `F-6 / L-5 / L-6 / L-7 / L-8`：官方脚本只出比率标量（无计数）⇒ **本表不给 CI，只报 Δ(pp)，标明「无 CI，不作显著性判定」**；
- token（计数型，不与率类混用）：报绝对差 + 相对差，`|相对差| < 5%` 视为「无实质差别」。

### 3.4 抽样规则（跑完前冻结，不择优）

ON 臂 `day>=1` 且 M-1 命中的消息按 `seq` 升序取**前 5 条**；OFF 臂同规则；命中 0 ⇒ 照实写「零命中」，不替换样本。

### 3.5 主表（两臂均实测，v2 填实）

| 指标 | OFF | ON | Δ(pp) | Wilson95 重叠 | 判定 | band_source |
|---|---|---|---|---|---|---|
| **M-1′（去自我复读后 · 本轮唯一主口径）** | **1 条 / 33（描述性，不比率）**〔probe〕 | **2 条 / 33**〔probe〕 | **+1 条（+3.03pp）** | OFF Wilson95 = [0.54%, 15.32%] | **不显著**（ON Wilson95 = [1.68%, 19.61%] 与 OFF [0.54%, 15.32%] 重叠） | 判据「同一说话人 且 共享 6-gram ≥ 3」，见 §3.6 |
| M-1′_strict（**敏感性分析 · 去重下界**） | 2 条 / 33 | **6 条 / 33**〔probe〕 | **+4 条（+12.12pp）** | OFF = [1.68%, 19.61%] | 不作判定 | 严判据 `covA ≥ 0.5`；只剔逐字复读 |
| M-1（**未去重 · 上界 / 被污染读数**） | 3 条 / 33 | **6 条 / 33**〔probe〕 | **+3 条（+9.09pp）** | OFF = [3.14%, 23.57%] | 不作判定 | 仅用于说明污染幅度（2/3 命中为复读）|
| M-1b（副列） | **0.73%（3/412）** | **1.46%（6/412）** | **+0.73pp** | OFF = [0.25%, 2.12%] | **不显著**（ON [0.67%, 3.14%] 与 OFF [0.25%, 2.12%] 重叠） | `day>=1` n=412 |
| M-0（对照） | **1.92%（5/260）** | **29.62%（77/260）** | **+27.70pp** | OFF = [0.82%, 4.42%] | **不作效果判定**：仅用于「M-1 降级」判据（ON 侧 M-0 与 M-1 同量级 ⇒ 按预注册 §3.5 把 M-1 降级为模板重叠，见 §5.2 D） | 同日对照，den 260 |
| F-6（官方，分母达标） | **0.037255（19/510）** | **0.111765（57/510）** | **+7.45pp** | OFF = [2.40%, 5.75%] | 无 CI 判定；只报 Δ 与方向 | den 510 |
| L-6 重复率 | **0.101961** | **0.127451（65/510）** | **+2.55pp** | 无 CI（官方只出标量） | 不作显著性判定 | den 510 |
| L-7 口头禅/句末重复 | **0.354902** | **0.65098（332/510）** | **+29.61pp（恶化）** | 无 CI | 不作显著性判定（预注册闸门：≤ 基线+5pp 视为未恶化） | den 510 |
| L-8 内部 token 泄漏 | **0.0** | **0.0** | **0.00pp** | 无 CI | 不作显著性判定（预注册：应保持 0） | den 510 |
| `tokens_in`（入向） | **228749** | **271717** | **+42968（+18.78%）** | — | 计数型 | `obs llm-cost` |
| `tokens_total`（in+out） | **484835** | **540840** | **+56005（+11.55%）** | — | 计数型；相对差 **+11.55%**（≥5% ⇒ 报增量与每消息成本） | `obs llm-cost` |
| `ctx.memory_refs` 注入消息数 | **0**（510 条中 0 条） | **412**（510 条中 412 条，共 **824** 个 `mem_id` 引用，去重后 **128** 个不同记忆） | — | — | 计数型（只证"注入发生了"） | `f6_metrics.py` / `r1_f6_compare.py` |
| **MDE（可检出最小差异）** | — | — | **19.62pp（overlap）/ 19.83pp（power）**（跑前以 OFF 率算）<br>**22.97pp / 23.67pp**（ON 读数到手后按两臂实测率复核） | — | **两种算法均 > 事前闸门 10pp ⇒ 不可判** | 见 §3.5b |

> **这张表怎么读（重要）**：只有 F-6 与 L-6/L-7/L-8 的分母（510）达标，可参与判定；M-1/M-0 的分母 33/260 与实例数（3、5）都太小，**一律 probe 级**，其百分比只作描述，不作结论。`tokens_*` 与 `memory_refs` 是计数型，不与率类混算。
> **M-0 与 M-1 的关系（预先登记的读法）**：OFF 侧 M-0（同日）1.92%、M-1（跨天）9.09%，量级不同但样本各只有 3/5 例，按 §3.5 预案**不据此判定"M-1 等于模板重叠"，也不据此判定反证**——见 §3.6 抽样本的实际质地。
> **ON 侧触发了预注册的第 3 条处置**：M-0（29.62%）与 M-1（18.18%）**同量级** ⇒ 按预案 **M-1 在 ON 侧降级为「模板重叠」，不得称为记忆引用**（详见 §5.2 D-2）。**M-1/M-0 一律不参与任何效果判定**，本轮唯一可判定的读数是 F-6 与 L-5..L-8（den 510）与计数型。

> 若 M-0 与 M-1 同量级 ⇒ 按 §3.5 预案把 M-1 降级为「模板重叠」，**不得称为记忆引用**。

### 3.5b 检验功效（MDE：算法先定，OFF 参数已代入算出；ON 到手只需替换参数复核）

| 口径 | 算法 | 本次数值 |
|---|---|---|
| **MDE（区间不重叠口径，对应 §3.3 判据）** | `Δ ≈ 1.959964 × (se_OFF + se_ON)`，`se = sqrt(p(1-p)/n)` | **19.62pp**（`p_off = 3/33 = 0.0909`，`n_off = n_on = 33`） |
| MDE（标准功效口径，α=0.05 双侧、power=0.8） | `Δ ≈ (1.959964 + 0.841621) × sqrt(2·p̄(1-p̄)/n_arm)` | **19.83pp**（同上参数） |

> 两口径在等臂、同率量级下几乎重合（系数 `3.92×se` vs `3.96×se`），所以 §3.3 的「区间不重叠」闸门并不比常规功效分析更宽松；反过来说，**它也不会更严格**。
> **本次数值是拿 OFF 侧实测率与分母算的（`p=3/33`），不是事后按结果倒推**：`se = sqrt(0.0909×0.9091/33) = 0.05003` ⇒ `MDE(overlap) = 1.959964×2×0.05003 = 19.62pp`。
> **ON 读数到手后的复核（v2 补记，不改上面的算法与闸门）**：代入两臂实测率（`p_off=3/33`、`p_on=6/33`、`n=33`）⇒ `MDE(overlap)=22.97pp`、`MDE(power)=23.67pp`，**仍远高于 10pp 闸门**，故 §5.2 B 段的「不可判定」结论不变。复算命令与输出见 `v2/evidence/r11_recompute_receipt.md` §4。

**结果处置（事前定，不得事后改；镜像冻结件 §4 并新增第 5 条）**

| 情形 | 结论怎么写 |
|---|---|
| M-1 Δ 不显著（§3.3 判定） | 写「不显著」，指出瓶颈可能在「人话记忆可用率」（附 mock 13% 观察并标 mock） |
| F-6 升、M-1 不动 | 分开写「只提升了提到过去的口头词，未提升内容复用」，不合并成「改善了」 |
| M-0 与 M-1 同量级 | M-1 降级为「模板重叠」，写进局限，不得称为记忆引用 |
| L-6/L-7 上升 > 1pp | 与提升并列报，不出「净改善」 |
| token 相对差 ≥ 5% | 报增量与每消息成本，供判断性价比 |
| **【本轮新增·事前定】两臂 MDE > 10pp** | 结论只写「**在本样本量下无法在噪声之上判定差异**」；主价值落在「**装配链路已打通 + 单变量可自证 + 真跑可复算**」；**禁止**出现「改善 / 提升 / 趋势向好」等任何效果性措辞 |

复算命令（结果到了把 `p_off/p_on/n_off/n_on` 换成本轮真实值）：

```bash
python3 -c "
import math
z=1.959963984540054; zb=0.8416212335729143
p_off,p_on,n_off,n_on = 3/33,3/33,33,33        # OFF 侧实测；ON 侧到手后替换为实测值
se=lambda p,n: math.sqrt(p*(1-p)/n)
print('MDE(overlap)=%.2fpp' % (100*z*(se(p_off,n_off)+se(p_on,n_on))))
pbar=(p_off*n_off+p_on*n_on)/(n_off+n_on); n_arm=(n_off+n_on)/2
print('MDE(power)=%.2fpp'   % (100*(z+zb)*math.sqrt(2*pbar*(1-pbar)/n_arm)))
"
# 实测输出（OFF 侧参数）：MDE(overlap)=19.62pp  MDE(power)=19.83pp
```

### 3.6 抽样本（按 §3.4 规则，原文不改写）

**OFF 臂 M-1 命中 3 条（< 抽 5 条上限）⇒ 按规则全列，不择优、不替换。** 命中正文原文如下（`body` 逐字引用，未改写；`seq` 为日志内序号，可复算）：

| # | 命中 `seq`/day/round | 说话人 | 更早日消息 `seq`/day | 同一说话人？ | 正文逐字相同？ | 共享 6-gram 数 | 覆盖率（A∩B ÷ A） | 判为 |
|---|---|---|---|---|---|---|---|---|
| 1 | `19241` / day1 / round12 | P007 | `8348` / day0 | 是 | 否 | **1**（A 37, B 51） | 1/37 = **0.027** | **真跨天呼应（保留）** |
| 2 | `34699` / day2 / round24 | P012 | `28261` / day1 | 是 | 否 | **3**（A 43, B 15） | 3/43 = **0.070** | **自我重述（去重剔除）** |
| 3 | `86316` / day4 / round50 | P008 | `82424` / day3 | 是 | **是（逐字）** | **13**（A 13, B 13） | 13/13 = **1.000** | **逐字复读（去重剔除）** |

**原文（各截取足够判定的一段，逐字引用）**

1. `seq 19241`（保留）：「周哥，方位我真说不准，就记得是后半夜，声音贴着河那边飘过来的，断断续续的，像有人压着嗓子在数数。」
   ← 更早 `seq 8348`：「周公文你这一问我还真得说两句，前阵子夜里老听见有人压着嗓子嘀咕，凑近又没声了…」
2. `seq 34699`（剔除）：「哎哟老周，那我就不跟你客气了，肚子正咕咕叫呢。你这红薯闻着就甜，我先拿一个，回头我家腌的萝卜干给你送一坛来。」
   ← 更早 `seq 28261`：「哎哟老周，那我就不客气啦，肚子正饿得咕咕叫呢。」
3. `seq 86316`（剔除）：「阿禾，心意我领了，但东西真不能收，这是规矩。」
   ← 更早 `seq 82424`：「阿禾，心意我领了，但东西真不能收，这是规矩。」（**与命中句完全相同**）

**去重规则（先写死，可复算，不择优）**

- 预处理与 M-1 完全一致：去空白与中英文标点后切 6 字窗口，得集合 `A`（命中消息）、`B`（用于判定的更早日消息）。
- **判据（主口径，产出 M-1′）**：一条命中被剔除当且仅当 **① 更早日消息与命中消息为同一说话人**（`payload.from` 相同）**且 ② `|A∩B| ≥ 3`**（共享 ≥3 个 6-gram）。
  - **阈值为什么取 3（判据定义的一部分，不是事后解释）**：1 个共享 6-gram 只是 6 个连续汉字，常见于固定寒暄/称谓（本轮 #1 正是 1 个，且内容确属真呼应），不足以判"复述"；≥3 个共享 6-gram 意味着**至少 8 个连续汉字逐字相同**（若相邻）或跨度更长，属"把上次说过的话又说一遍"。因此把门槛定在 3，**并在此声明：若下一轮改阈值，必须先把新阈值写进预注册再跑，不得在读数到手后调整**。
- **严判据（并列报，不影响主口径）**：`|A∩B|/|A| ≥ 0.5`（近乎逐字）⇒ 本轮只剔 #3 ⇒ `M-1′_strict = 2/33`。
- **本轮结果（分层，不并列）**：**主口径 `M-1′ = 1/33`**（剔 #2、#3）；`M-1′_strict = 2/33` 作**敏感性分析·去重下界**；`M-1_原始 = 3/33` 作**未去重上界/被污染读数**。三者都只在事件数级使用（分母 33 < 68，按 §0.2 不写比率结论）。
- 注意：该判据只剔除"同一说话人重复自己"；**不同说话人互相复读**（A 说、B 照念）本轮 0 例，不在剔除范围。

**为什么这条是本轮核心结论（不是脚注）**：它说明 **M-1/6-gram 口径在 OFF 基线上就有 2/3 的命中是"复读机"而非"记得昨天"**。这是**度量效度**问题，与样本量/MDE 无关——样本再大，只要不去重，"复读"比例也会被一起放大。因此下一轮任何 F-6/M-1 类读数都应先过这一步（§7 建议 1）。

复算本节的命令（不改冻结脚本，只是把它的命中按 `seq` 反查正文）：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 - <<'PY'
import json,re
from collections import defaultdict
MSG=("MSG_DM","MSG_GROUP","MSG_PUBLIC")
def ng(t,n=6):
    t=re.sub(r"[\s，。！？、；：「」（）,.!?;:()\"'“”‘’…—-]","",t or "")
    return {t[i:i+n] for i in range(max(0,len(t)-n+1))}
recs=[json.loads(l) for l in open("v2/evidence/run_f6_off_n16r60_seed42/run.jsonl") if l.strip()]
msgs=[]
for r in recs:
    if r.get("type") not in MSG: continue
    p=r.get("payload") or {}
    msgs.append(dict(seq=r.get("seq"),round=r.get("round"),day=p.get("day"),type=r["type"],
        frm=p.get("from"),to=p.get("to"),gid=p.get("group_id"),
        body=(p.get("body") or "").strip(),tid=p.get("thread_id")))
def tk(m):
    if m["tid"]: return "T:"+str(m["tid"])
    if m["type"]=="MSG_DM": return "D:"+"|".join(sorted([str(m["frm"]),str(m["to"])]))
    if m["type"]=="MSG_GROUP": return "G:"+str(m["gid"])
    return "P:"+str(m["frm"])
th=defaultdict(list)
for m in msgs: th[tk(m)].append(m)
for k,grp in th.items():
    for i,m in enumerate(grp):
        if m["day"] is None or m["day"]<1: continue
        g=ng(m["body"]); ec=[x for x in grp[:i] if x["day"] is not None and x["day"]<m["day"]]
        if not ec: continue
        if g and any(g & ng(x["body"]) for x in ec):
            hit=[x for x in ec if g & ng(x["body"])][0]
            print("seq=%s day=%s round=%s thread=%s"%(m["seq"],m["day"],m["round"],k))
            print("  body:",m["body"])
            print("  earlier seq=%s day=%s body=%s"%(hit["seq"],hit["day"],hit["body"]))
PY
# 期望输出恰好 3 组，seq = 19241 / 34699 / 86316（与上表一致）

# —— 去重判定（产出 M-1 与 M-1′ 三个数）——
python3 - <<'PY'
import json,re
from collections import defaultdict
MSG=("MSG_DM","MSG_GROUP","MSG_PUBLIC")
def ng(t,n=6):
    t=re.sub(r"[\s，。！？、；：「」（）,.!?;:()\"'“”‘’…—-]","",t or "")
    return {t[i:i+n] for i in range(max(0,len(t)-n+1))}
msgs=[]
for l in open("v2/evidence/run_f6_off_n16r60_seed42/run.jsonl"):
    if not l.strip(): continue
    r=json.loads(l)
    if r.get("type") not in MSG: continue
    p=r.get("payload") or {}
    msgs.append(dict(seq=r.get("seq"),day=p.get("day"),type=r["type"],frm=p.get("from"),
                     to=p.get("to"),gid=p.get("group_id"),body=(p.get("body") or "").strip(),
                     tid=p.get("thread_id")))
def tk(m):
    if m["tid"]: return "T:"+str(m["tid"])
    if m["type"]=="MSG_DM": return "D:"+"|".join(sorted([str(m["frm"]),str(m["to"])]))
    if m["type"]=="MSG_GROUP": return "G:"+str(m["gid"])
    return "P:"+str(m["frm"])
th=defaultdict(list)
for m in msgs: th[tk(m)].append(m)
hit=den=0; drop_main=drop_strict=0
for grp in th.values():
    for i,m in enumerate(grp):
        if m["day"] is None or m["day"]<1: continue
        A=ng(m["body"]); ec=[x for x in grp[:i] if x["day"] is not None and x["day"]<m["day"]]
        if not ec: continue
        den+=1
        hs=[x for x in ec if A & ng(x["body"])]
        if not hs: continue
        hit+=1
        x=hs[0]; B=ng(x["body"]); sh=len(A&B)
        same_speaker=(m["frm"]==x["frm"])
        main=same_speaker and sh>=3
        strict=same_speaker and (sh/len(A) if A else 0)>=0.5
        drop_main+=main; drop_strict+=strict
        print("hit=%s(%s) earlier=%s(%s) same_speaker=%s shared6=%d covA=%.3f drop_main=%s drop_strict=%s"
              % (m["seq"],m["frm"],x["seq"],x["frm"],same_speaker,sh,sh/len(A),main,strict))
print("M-1  = %d/%d" % (hit,den))
print("M-1' (main, same_speaker & shared6>=3)   = %d/%d" % (hit-drop_main,den))
print("M-1'_strict (same_speaker & covA>=0.5)   = %d/%d" % (hit-drop_strict,den))
PY
# 期望输出（本报告实测，可逐字比对）：
#   hit=19241(P007) earlier=8348(P007)  same_speaker=True shared6=1  covA=0.027 drop_main=False drop_strict=False
#   hit=34699(P012) earlier=28261(P012) same_speaker=True shared6=3  covA=0.070 drop_main=True  drop_strict=False
#   hit=86316(P008) earlier=82424(P008) same_speaker=True shared6=13 covA=1.000 drop_main=True  drop_strict=True
#   M-1  = 3/33
#   M-1' (main, same_speaker & shared6>=3)   = 1/33
#   M-1'_strict (same_speaker & covA>=0.5)   = 2/33
```

### 3.6b ON 臂抽样本（同规则、同判据，v2 新增；原文不改写）

**ON 臂 M-1 命中 6 条 ⇒ 按 §3.4「按 `seq` 升序取前 5 条」的规则本应只列 5 条，但命中表只有 6 行且第 6 行为判据边界（共享 6-gram=5），为免"挑样本"之嫌，本表 6 条全列、不裁剪、不择优。**

| # | 命中 `seq`/day/round | 说话人 | 更早日消息 `seq`/day | 同一说话人？ | 逐字相同？ | 共享 6-gram | 覆盖率 | 判为 |
|---|---|---|---|---|---|---|---|---|
| 1 | `34118` / day2 / round24 | P004 | `23853` / day1 | 是 | 否 | **3**（A 52, B 33） | 3/52 = 0.058 | 自我重述（剔除） |
| 2 | `34913` / day2 / round24 | P015 | `24012` / day1 | 是 | 否 | **10**（A 57, B 33） | 10/57 = 0.175 | 自我重述（剔除） |
| 3 | `56239` / day3 / round36 | P003 | `38790` / day2（P011） | **否** | 否 | **1** | 1/20 = 0.050 | **跨人呼应（保留）** |
| 4 | `84033` / day4 / round48 | P007 | `62319` / day3 | 是 | 否 | **3**（A 79, B 77） | 3/79 = 0.038 | 自我重述（剔除） |
| 5 | `84593` / day4 / round48 | P013 | `80012` / day3（P008） | **否** | 否 | **1** | 1/24 = 0.042 | **跨人呼应（保留）** |
| 6 | `84301` / day4 / round43 | P010 | `62626` / day3 | 是 | 否 | **5**（A 71, B 25） | 5/71 = 0.070 | 自我重述（剔除） |

**三档结果（`tools/f6/f6_m1_dedup.py`，判据与 §3.6 逐字一致、阈值不可调）**：`M-1 = 6/33`、**`M-1′ = 2/33`（主口径）**、`M-1′_strict = 6/33`（撤销比：无一条达到 `covA ≥ 0.5`）。

**原文（各截取足够判定的一段，逐字引用）**

1. `seq 34913`（剔除）：「兰姐，你这话我可记着呢，干贝那回是真鲜。不过今天我这肚子也饿得直叫…改天汤好了我给你留一碗，可别又让桂婶先尝了去。」
   ← 更早 `seq 24012`（同人 P015）：「…行，你忙你的，改天我熬好了给你留一碗，可别又让桂婶先尝了去。」
2. `seq 56239`（保留，**跨人**）：「周公文那话在理，可你肚子都饿扁了，先垫两口再练也不耽误。」
   ← 更早 `seq 38790`（**P011** 说的）：「阿禾，我肚子都饿扁了，你那儿还有吃的没？」
3. `seq 84593`（保留，**跨人**）：「周公文，兰姐那锅汤还惦记着呢，你先把训练办妥，回头顺路催一句就行。」
   ← 更早 `seq 80012`（**P008** 说的）：「铁头，whisper的事我先记下，回头按流程问清楚。兰姐那碗汤我顺路去催，但得先把训练办妥。」

**与 OFF 侧的质地差异（v2 新观察，只作描述）**

- OFF 的 2/3 命中是**逐字/近逐字复读**（`seq 86316` = `seq 82424` 完全相同，`covA = 1.000`）；
- ON 的 4/6 命中是**改写式复述**（共享 3–10 个 6-gram、`covA` 仅 0.038–0.175，无一条 ≥ 0.5）⇒ 注入让"复述"从「照抄」变成「换词重讲」，**但仍然是复述**；
- ON 侧剩下的 2 条**全部是「别人说过的话被另一个居民拿去讲」**，更像"闲话扩散"，而不是"当事人自己记得"。这两条恰好是 M-1 口径里语义最接近"记忆进对话"的样本，但分母只有 33，**只作事件数**。

> 复算：`python3 tools/f6/f6_m1_dedup.py --run v2/evidence/run_f6_on_n16r60_seed42/run.jsonl`（落盘 `v2/evidence/f6_m1_dedup_on.json`，sha256 `041a3eca…`）；OFF 同法 `--run v2/evidence/run_f6_off_n16r60_seed42/run.jsonl`（`1c9a9678…`），输出 `M-1 = 3/33`、`M-1′ = 1/33`、`strict = 2/33`，与 §3.6 的原有结果**逐字一致**（同一判据的两种实现互证）。

---

## 4. 证据链

### 4.1 两臂批身份与完整性

| 项 | OFF 臂 | ON 臂 |
|---|---|---|
| run 目录 | `v2/evidence/run_f6_off_n16r60_seed42/` | `v2/evidence/run_f6_on_n16r60_seed42/` |
| `code_sha`（meta 实测） | **`895b9a381cd5a1838c23bd3b38e139f7edade3b8`**（`code_sha_end` 同值） | **`895b9a381cd5a1838c23bd3b38e139f7edade3b8`**（`code_sha_end` 同值 ⇒ 与 OFF 逐字相同） |
| 规模 / seed | **n=16、rounds=60、seed=42** | 同（`--agents 16 --rounds 60 --seed 42`） |
| `run.jsonl` 字节 / 行数 | **55,213,213 B / 116294 行** | **55,235,141 B** / **116261 行** |
| `run.jsonl` sha256 | **`c73bead61a440db789f6d6ba1de555fe326a203ee27d1219690174e3d9483642`** | **`7de6a7be5adff276f1e42c065a708c271f870f2bf8daa930cf0cdfc983f7434d`** |
| `meta.json` sha256 | **`5d0634b6f43b0129496f329c071ad55bb876ca499d322933a3896c5012930500`** | **`8c7215a25b0e4f36d0084c4321f8c902b7b5144c5f819b451b763bfdfca44eb5`** |
| `host.log` sha256 | **`fee17565629e55a5aa287236fc47f152ad15c6b5d71324fce7fdc9dc666bc654`** | **`5ba74fb6324020ad310768229307aeda77bb824a3248caa25cb95c8510ec2535`** |
| `meta.events` ↔ `wc -l` | **116294 ↔ 116294**（一致） | **116261 ↔ 116261**（一致） |
| 起止 / 耗时 | **12:35:19 → 14:02:00（`duration_sec=5201`；`host.log` 内 `seconds=5188.0449`）** | **14:05:57 → 15:53:13（`duration_sec=6436`；`host.log` 内 `seconds=6423.1065`）** |
| side-root（各批独立，防缓存串味） | `/tmp/f6_off60_side` | `/tmp/f6_on60_side` |

> 两组耗时口径都列：`meta.duration_sec=5201`（含起跑/收尾）、`host.log seconds=5188.0449`（纯 life 循环）——两者差 13 s，属进程启停开销，**不是矛盾**。
> `meta.git_dirty_code_files` 两臂都有值，且**全是 `code/frontend/sample/` 下的前端派生物目录**：OFF = `?? …/dialogue_run_g1_b0_n16r60_seed42/`；ON = `?? …/dialogue_run_f6_off_n16r60_seed42/` + 同上 —— 属元数据用子串 `" code/"` 过滤造成的误报（`code/` 下**无源码改动**）。**硬判据只有 §4.6(c) 的 `git diff 895b9a3 -- code/{life,orchestration,config}`（空输出）**。

`run.jsonl` 被 `.gitignore:8 **/*.jsonl` 忽略，**不入库**，故一律用「文件路径 + sha256 全值 + 行数」做身份引用（见 §4.4）。

### 4.2 真 LLM 验真（`obs llm-cost` 原文入库）

```bash
cd <REPO>/code && python3 -m obs llm-cost --log ../v2/evidence/run_f6_off_n16r60_seed42/run.jsonl --require-provider openai_compat; echo rc=$?
cd <REPO>/code && python3 -m obs llm-cost --log ../v2/evidence/run_f6_on_n16r60_seed42/run.jsonl  --require-provider openai_compat; echo rc=$?
```

| 判据 | OFF（实测） | ON |
|---|---|---|
| `rc == 0` | **`rc=0`** | **`rc=0`** |
| `provider_guard.ok == true` 且 `problems == []` | **`ok=true`、`problems=[]`** | **`ok=true`、`problems=[]`** |
| `by_provider` 只含 `openai_compat` 且 >0 | **`{openai_compat: 2878}`** | **`{openai_compat: 2878}`**（无 mock 混入） |
| `total.calls > 0` 且 `degraded == 0` | **`calls=2878`、`degraded=0`、`cached=1472`、`thinking=668`** | **`calls=2878`、`degraded=0`、`cached=1477`、`thinking=668`** |
| `tokens_in` / `tokens_out` / `tokens_total` | **228749 / 256086 / 484835** | **271717 / 269123 / 540840** |
| `meta.provider` / `meta.model` / `fallback_detected` | **`openai_compat` / `DeepSeek-Flash` / `False`** | **`openai_compat` / `DeepSeek-Flash` / `False`** |

**OFF 臂 `obs llm-cost` 原始输出（入库件 `v2/evidence/f6_cost_off.json`，原文摘，未改写）**：

```
{"engine_log":{"by_provider":{"openai_compat":2878},
 "by_purpose":{"dialogue":{"cached":47,"calls":510,"degraded":0,"thinking":0,"tokens_in":88878,"tokens_out":12057},
               "importance":{"cached":1387,"calls":1523,"degraded":0,"thinking":0,"tokens_in":2312,"tokens_out":34276},
               "judge":{"cached":0,"calls":668,"degraded":0,"thinking":668,"tokens_in":88382,"tokens_out":201605},
               "negotiation":{"cached":34,"calls":49,"degraded":0,"thinking":0,"tokens_in":1787,"tokens_out":525},
               "plan":{"cached":0,"calls":16,"degraded":0,"thinking":0,"tokens_in":1447,"tokens_out":906},
               "reflect":{"cached":4,"calls":112,"degraded":0,"thinking":0,"tokens_in":45943,"tokens_out":6717}},
 "source":"engine_log(LLM_CALL)",
 "total":{"cached":1472,"calls":2878,"degraded":0,"thinking":668,
          "tokens_in":228749,"tokens_out":256086,"tokens_total":484835}},
 "provider_guard":{"by_provider":{"openai_compat":2878},"expected":"openai_compat","ok":true,
  "policy":"计划用真 LLM 时必须显式校验 provider 计数 > 0 且无 mock 混入。","problems":[]}}
```

> ⚠️ 验真**不传 `--cache-dir`**（`obs/llmcost.py:58-68` docstring：共享 FREEZE 缓存会把 mock 与真响应混存）。

**ON 臂 `obs llm-cost` 原始输出（入库件 `v2/evidence/f6_cost_on.json`，sha256 `db92fee7…`，原文摘，未改写）**：

```json
{"engine_log":{"by_provider":{"openai_compat":2878},
 "by_purpose":{"dialogue":{"cached":52,"calls":510,"degraded":0,"thinking":0,"tokens_in":130924,"tokens_out":16057},
               "importance":{"cached":1387,"calls":1523,"degraded":0,"thinking":0,"tokens_in":2312,"tokens_out":37246},
               "judge":{"cached":0,"calls":668,"degraded":0,"thinking":668,"tokens_in":88382,"tokens_out":206604},
               "negotiation":{"cached":34,"calls":49,"degraded":0,"thinking":0,"tokens_in":1787,"tokens_out":563},
               "plan":{"cached":0,"calls":16,"degraded":0,"thinking":0,"tokens_in":1447,"tokens_out":1039},
               "reflect":{"cached":4,"calls":112,"degraded":0,"thinking":0,"tokens_in":46865,"tokens_out":7614}},
 "source":"engine_log(LLM_CALL)",
 "total":{"cached":1477,"calls":2878,"degraded":0,"thinking":668,
          "tokens_in":271717,"tokens_out":269123,"tokens_total":540840}},
 "provider_guard":{"by_provider":{"openai_compat":2878},"expected":"openai_compat","ok":true,
  "policy":"计划用真 LLM 时必须显式校验 provider 计数 > 0 且无 mock 混入。","problems":[]}}
```

**为什么这四个数能证明「真实 LLM 调用」而非 mock**（判据不是"跑完了"，而是四者同时成立）：

| 判据 | 为什么这条能排除 mock |
|---|---|
| `by_provider = {openai_compat: 2878}`，**不含任何 mock 供应方** | mock 臂会把计数记在 `MockProvider`；`obs/llmcost.py` 的 `provider_guard` 只要见到非预期 provider 就写进 `problems` |
| `problems = []`、`ok = true` | 门禁对象是**整条日志的全部 `LLM_CALL` 事件**，不是抽样 |
| `degraded = 0` 且 `calls = 2878` | `degraded` 表示"降级/兜底"调用（模板回退）；为 0 ⇒ 510 条对话全部来自真实端点响应 |
| `tokens_in / tokens_out` 非零且与 `by_purpose` 分项相加一致（271717 = 130924+2312+88382+1787+1447+46865） | mock 不产生真实 token 计量；分项可加总校验 ⇒ 数值不是编造的单点 |

> 补充：`meta.llm_provider_in_events = {openai_compat: 2878}`、`meta.llm_model_in_events = {DeepSeek-Flash: 2878}`、`fallback_detected = false` —— 与 `obs llm-cost` 完全一致（两条独立路径同源日志互证）。`rc=0`，退出码 4/6 的门禁语义见 `tools/d2/run_batch.sh:11`。

### 4.3 截图（真拍，图源批与生成时刻**两栏不得合并**）

**OFF 臂四视图（本版已产出，真实文件）**：

| 视图 | 文件 | 尺寸/模式 | sha256 | 图源批 | 生成时刻 |
|---|---|---|---|---|---|
| chat（对话流） | `v2/evidence/f6_shots/run_f6_off_n16r60_seed42-chat-c73bead6.png` | 1400×900 RGB | `966be072b43639d647f3282c855f47724bf4609c53c57539d9a02e4249e302ee` | OFF 臂 `run_f6_off_n16r60_seed42`（`c73bead6…`） | 2026-10-21 14:33 |
| rhythm（节律·串门） | `v2/evidence/f6_shots/run_f6_off_n16r60_seed42-rhythm-c73bead6.png` | 1300×1050 RGB | `0f1bae4b3f56a5875983cc59f21833d2f1bbc18e7b1bd89f56ec6e0c8bb9c5c1` | 同上 | 同上 |
| spread（闲话怎么传开） | `v2/evidence/f6_shots/run_f6_off_n16r60_seed42-spread-c73bead6.png` | 1300×900 RGB | `d7d764058fbdbc3dea9e11f6f71379974e7daf3abee09cf99e1e77ba8baf09ca` | 同上 | 同上 |
| 600（窄屏判读） | `v2/evidence/f6_shots/run_f6_off_n16r60_seed42-600-c73bead6.png` | 600×900 RGB | `2dffa247ecbc4d5f41939658e8939a922ed05db081c78f918cc869f8c487cbd1` | 同上 | 同上 |

**非退化判据（不是"有文件就算"）**：截图脚本自身输出 `SHOT OK`（`blank_retries=0/2`）；另用 Pillow 全解码复核尺寸/模式并独立复算像素统计：

| 视图 | OFF `mean_brightness` | OFF `dark_frac` | OFF `max_color_frac` | **ON `mean_brightness`** | **ON `dark_frac`** | **ON `max_color_frac`** |
|---|---|---|---|---|---|---|
| chat | 33.5 | 0.00% | 14.34% | **33.7** | **0.01%** | **10.70%** |
| rhythm | 32.5 | 0.00% | 26.20% | **32.6** | **0.01%** | **17.48%** |
| spread | 23.2 | 0.00% | 52.48% | **24.1** | **0.01%** | **46.62%** |
| 600 | 38.3 | 0.01% | 15.58% | **38.4** | **0.02%** | **10.12%** |

> ON 侧三列由本报告独立复算（Pillow 全解码 → 缩到 1/4 → 逐像素统计），命令见 `v2/evidence/r11_recompute_receipt.md` §7；与 `evidence-visualizer` 的 `r11_shots_manifest.json` 属两套独立测量，**只用于"非退化"这一结论，不比较两者数值大小**。
> ⇒ ON 四视图与 OFF 同量级（亮度 24.1–38.4、`dark_frac ≤ 0.02%`）⇒ **非黑非白，非退化**。

⇒ **非黑非白**（`dark_frac ≈ 0`，亮度 23–38，与 R10 同族 D9 四视图 23.2–38.2 量级一致）。

> **两套 `max_color_frac` 数值不同，原因已查明、不是矛盾**：下表（自算）用**全图**最大单色占比；脚本 stdout 的 `max_color_frac`（如 spread `71.19%`）是在其内部**取样区域**上算的（同 R10 记录口径），两者定义不同。本报告只把「非退化」结论建立在**两套都远未达到"单色铺满"**这一点上，不比较两者的大小。

**ON 臂四视图（真拍已产出，`evidence-visualizer` 生成于 2026-10-21 16:08；文件名与本节预留位一致，sha256 由本报告独立复算）**：

| 视图 | 文件 | 尺寸 | sha256 | 图源批 | 生成时刻 |
|---|---|---|---|---|---|
| chat（对话流） | `v2/evidence/f6_shots/run_f6_on_n16r60_seed42-chat-7de6a7be.png` | 1400×900 RGB | `2cf622ebfd025f7182c98afe7dd7a5c345b5f31d4e7bb6617119f9462b5babfd` | ON 臂 `run_f6_on_n16r60_seed42`（`7de6a7be…`） | 2026-10-21 16:08 |
| rhythm（节律·串门） | `v2/evidence/f6_shots/run_f6_on_n16r60_seed42-rhythm-7de6a7be.png` | 1300×1050 RGB | `fc11501c1a421d8fe8d97e8a4cc3c1b41bf5f851451f385fa07003483a071c32` | 同上 | 同上 |
| spread（闲话怎么传开） | `v2/evidence/f6_shots/run_f6_on_n16r60_seed42-spread-7de6a7be.png` | 1300×900 RGB | `308844ded88073fd8c0508abaea9467030ef6c0ef7724f3486c1ebbb0ea79f7e` | 同上 | 同上 |
| 600（窄屏判读） | `v2/evidence/f6_shots/run_f6_on_n16r60_seed42-600-7de6a7be.png` | 600×900 RGB | `54e36930ad154258bd1efbacc8e01b33833c42a6f3f04d1b6c35764b90b76f88` | 同上 | 同上 |

**生成命令（本版 OFF 臂实跑原文，逐条可复制；ON 臂同法只换目录）**：

```bash
cd <REPO>/code
curl -s -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8848/     # 期望 200（静态服务 pid 477109）
SHA8=$(sha256sum ../v2/evidence/run_f6_off_n16r60_seed42/run.jsonl | cut -c1-8)   # c73bead6
python3 frontend/tools/gen_threads.py \
  --log ../v2/evidence/run_f6_off_n16r60_seed42/run.jsonl \
  --meta ../v2/evidence/run_f6_off_n16r60_seed42/meta.json \
  --out frontend/sample/dialogue_run_f6_off_n16r60_seed42/threads.json \
  --require-complete --label run_f6_off_n16r60_seed42-$SHA8
mkdir -p ../v2/evidence/f6_shots
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 \
  sample/dialogue_run_f6_off_n16r60_seed42/threads.json "" "" ../v2/evidence/f6_shots
# 实跑 stdout（原文）：
#   [gen_threads] 完整性断言通过：TURN_SEAL 60 条覆盖 round 0..59
#   [gen_threads] events=116294 messages=510 threads=169 multi_turn=88 ge3=77 legacy_msgs=0 moves=299 ref_edges=0 echoes=0
#   [gen_threads] wrote frontend/sample/dialogue_run_f6_off_n16r60_seed42/threads.json (1987464 bytes)
#   SHOT OK: ...-spread-c73bead6.png  elapsed=1.58s  mean_brightness=23.2  max_color_frac=71.19%  blank_retries=0/2
#   SHOT OK: ...-600-c73bead6.png     elapsed=1.82s  mean_brightness=38.3  max_color_frac=35.82%  blank_retries=0/2
#   OK: ...-{chat,rhythm,spread,600}-c73bead6.png
```

**判读边界（必须说清）**：四视图显示的是**对话流、空间节律、闲话传播**，**看不到** `ctx.memory_refs` 注入与否 ⇒ 它们能证明「这批 16 居民 × 60 回合的小镇确实在正常说话、正常串门、非黑屏」，**不能**用来证明 F-6 干预生效；后者只由 §3.5 的 F-6 读数与 §4.2 的验真支撑。图注：**图源为既有批产物，非新跑批截图**；生成时刻 14:33 仅为渲染时间。

### 4.4 入库边界：哪些进、哪些不进（含 `threads.json` 的裁定证据）

**不入库**：
- `run.jsonl`（55 MB 级，`.gitignore:8 **/*.jsonl` 已忽略）：只留 sha256 + 行数 + 字节数（两臂见 §4.1）。

**必须入库（sidecar，否则身份链断裂）**：
- 两臂 `meta.json` / `host.log`（OFF 侧另有起跑证据留档在上一届 `round1/`，本轮不重复引用）；
- 验真件 `v2/evidence/f6_cost_{off,on}.json`、官方指标 `v2/evidence/r1_f6_{off,on}_metrics.{json,md}`、预注册 `r1_f6_preregistration.md`、审计脚本 `r1_f6_compare.py`、M-1 脚本 `tools/f6/f6_metrics.py`、四视图 `v2/evidence/f6_shots/*.png`。

**`threads.json` 是否入库——按仓库既有事实裁定，不按偏好**：

```
$ git ls-tree -r --long origin/master -- code/frontend/sample/dialogue_run_d9_a1_n16r84_seed42/
100644 blob 94bfd2d39687842c1e52b488eb1c7057210f28d9 4363050  code/frontend/sample/dialogue_run_d9_a1_n16r84_seed42/threads.json

$ git check-ignore -v code/frontend/sample/dialogue_run_f6_off_n16r60_seed42/threads.json
rc=1        # 未被任何 .gitignore 规则忽略
```

上游 `code/frontend/sample/` 下 **7 个 `dialogue_*` 目录全部入库了 `threads.json`**：`dialogue_demo` 543,829 B｜`dialogue_a1_wording_n4r60` 411,358 B｜`dialogue_run_d8_armA` 415,432 B｜`dialogue_run_d8_armB` 418,511 B｜`dialogue_v0anchor_n16` 439,056 B｜`dialogue_run_d2_after_n16` **4,356,850 B**｜`dialogue_run_d9_a1_n16r84` **4,363,050 B**。
⇒ 结论：**本轮 `threads.json` 入库**（OFF 臂 1,987,464 B，小于上游已有两批 4.36 MB），依据是"仓库既有做法 + 未被忽略"，不是个人偏好。**若后续 ON 臂的 `threads.json` 也生成，同样入库**。

**一律不提交**（与本轮无关，留作下一轮候选）：`code/frontend/sample/dialogue_run_g1_b0_n16r60_seed42/`（G1 批次派生物）、全部 19 个 `d4_*` / `g1_*` 证据文件。

### 4.5 复算命令清单（第二人照做，绝对路径可粘贴）

> ⚠️ **两处路径订正（本报告为准）**：
> ① `metrics-definition-frozen.md` §3 与 `exec-notes.md` §8 里写的是 `run_f6_off_n16r84_seed42` / `run_f6_on_n16r84_seed42`——**尺寸变更前**的路径，OFF 那份已作废为 `_VOID/`，ON 从未跑出。本节的命令已改为正式批 **`n16r60`**。
> ② **冻结脚本已入仓**：`tools/f6/f6_metrics.py`（sha256 `be27a3be696f39e6f64c506ad19f42e20fbc33b9e056ce2a22820cf9ccc90c6a`，与源件**逐字节一致**，`cmp` 通过）。
> **上一届团队工作空间的旧路径 `…/jiuwen_team_cron___1a15c9dae2f_32922fef9198/team-workspace/round1/scripts/f6_metrics.py` 已失效，不要再照抄**（该目录不在本团队成员可见的路由内，且随时可能被清理）。冻结件的**公式/分母/阈值/抽样规则不变**（`metrics-definition-frozen.md` sha256 `f0f1f4b45b5f6c832fa4739879592261843bcc5196c947e62388b2eaac0c4cb8`），只有路径过期。

```bash
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# ① 官方指标（F-6 / L-5..L-8 的唯一来源）
cd $REPO
python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_f6_off_n16r60_seed42/run.jsonl \
  --meta v2/evidence/run_f6_off_n16r60_seed42/meta.json --out-json v2/evidence/r1_f6_off_metrics.json --out-md v2/evidence/r1_f6_off_metrics.md
python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_f6_on_n16r60_seed42/run.jsonl \
  --meta v2/evidence/run_f6_on_n16r60_seed42/meta.json --out-json v2/evidence/r1_f6_on_metrics.json --out-md v2/evidence/r1_f6_on_metrics.md

# ② 验真（同时另存 json 供 ③ 读 token；不传 --cache-dir）
cd $REPO/code
python3 -m obs llm-cost --log ../v2/evidence/run_f6_off_n16r60_seed42/run.jsonl --require-provider openai_compat > $REPO/v2/evidence/f6_cost_off.json; echo rc=$?
python3 -m obs llm-cost --log ../v2/evidence/run_f6_on_n16r60_seed42/run.jsonl  --require-provider openai_compat > $REPO/v2/evidence/f6_cost_on.json;  echo rc=$?

# ③ M-1 / M-1b / M-0 + 差值表（仓内冻结脚本，sha256 be27a3be…）
cd $REPO
python3 tools/f6/f6_metrics.py \
  --run OFF=v2/evidence/run_f6_off_n16r60_seed42/run.jsonl \
  --run ON=v2/evidence/run_f6_on_n16r60_seed42/run.jsonl \
  --official OFF=v2/evidence/r1_f6_off_metrics.json --official ON=v2/evidence/r1_f6_on_metrics.json \
  --cost OFF=v2/evidence/f6_cost_off.json --cost ON=v2/evidence/f6_cost_on.json \
  --out v2/evidence/f6_metrics_two_arms.json --markdown v2/evidence/f6_metrics_two_arms.md

# ④ memory_refs 注入计数（只证"注入"，不证"用上"）
python3 - <<'PY'
import json
for arm in ("off","on"):
    n=tot=0
    for line in open(f"v2/evidence/run_f6_{arm}_n16r60_seed42/run.jsonl"):
        d=json.loads(line)
        if d.get("type") in ("MSG_DM","MSG_GROUP","MSG_PUBLIC"):
            tot+=1
            if ((d.get("payload") or {}).get("ctx") or {}).get("memory_refs"): n+=1
    print(arm, "msgs", tot, "with_memory_refs", n)
PY
# 实测输出：off msgs 510 with_memory_refs 0 ｜ on msgs 510 with_memory_refs 412（共 824 个 mem_id 引用）

# ⑤ 代码纯洁性（本轮硬判据，期望空输出）
cd $REPO && git diff 895b9a3 -- code/life code/orchestration code/config; echo "rc=$? (空=合规)"

# ⑥ 行号核对（§2.2 的来源）
grep -n "MEMORY_F6_ENV\|MEMORY_F6_TOP_N\|MEMORY_F6_ITEM_CHARS\|def memory_f6_enabled\|def _memory_line\|def _dialogue_prompt\|def _reply_prompt" $REPO/code/life/agent.py

# ⑦ 人话门可用率（§2.4 的比例，mock 探针；无脚本 ⇒ 保持"不可复核"标记）
# 结论：**暂无脚本 ⇒ 保持"不可复核"标记**。
# 复核入口（若要做，需自建）：遍历 mock n4x60 批的 memory.nodes，调 agent._readable() 统计可用率。
# 本轮未落地该脚本，故 §2.4 的比例只作"设置人话门的动机"引用，不进任何读数表、不进摘要。

# ⑧ 单变量自证（mock，零网络；§4.6(b) 的可复现入口）
#    脚本同样来自上一届 round1/，已失效 ⇒ 本节保留命令原貌但**标不可复算**，见 §5.4。
#    （探针结论仅在 round1/evidence_prompt_{identity,diff}.txt 留档，sha256 见 §8 证据索引）

# ⑨ 截图（真拍四视图；8848 静态服务已在跑，勿重复起）
cd $REPO/code
curl -s -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8848/
SHA8=$(sha256sum ../v2/evidence/run_f6_on_n16r60_seed42/run.jsonl | cut -c1-8)
python3 frontend/tools/gen_threads.py --log ../v2/evidence/run_f6_on_n16r60_seed42/run.jsonl \
  --meta ../v2/evidence/run_f6_on_n16r60_seed42/meta.json \
  --out frontend/sample/dialogue_run_f6_on_n16r60_seed42/threads.json --require-complete \
  --label run_f6_on_n16r60_seed42-$SHA8
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 \
  sample/dialogue_run_f6_on_n16r60_seed42/threads.json "" "" ../v2/evidence/f6_shots
sha256sum ../v2/evidence/f6_shots/*.png
```

### 4.6 单变量三查（**(a)(b)(c)**，含证据等级；时序：exec 交付后、commit 前）

| # | 声明 | 方法 | 结果（原文见下） | 证据等级 |
|---|---|---|---|---|
| (a) | 两臂 `code_sha` 相同 | 两臂 `meta.json` 的 `code_sha` 逐字比对，**并与当时实际 landing（`git log -1`）比对，防事后回填** | **OFF 侧已核**：`code_sha = code_sha_end = 895b9a381cd5a1838c23bd3b38e139f7edade3b8`，与 `git rev-parse HEAD` 一致；**ON 侧已核**：`code_sha = code_sha_end = 895b9a381cd5a1838c23bd3b38e139f7edade3b8`、`generated_after_run=true`、`started_at=2026-10-21T14:05:57+08:00`，同样与 HEAD 逐字一致 ⇒ **两臂同树** | **机械验证（两臂 meta 逐字比对 + 与 HEAD 比对，已通过）** |
| (b) | 唯一差异是 `LIFE_PROMPT_MEMORY_F6`；OFF 提示词 = ON 去记忆段后**逐字节相同** | mock 探针 `insert_only`（同 wv 两次装配）+ 跨进程 200 对 diff；真跑两臂齐后用真实 prompt 复核一次 | **mock 级已通过**：`insert_only` 4/4（`_dialogue_prompt` 与 `_reply_prompt` 均）；跨进程 200 对中 `identical_pairs=112`、`first_diff_idx=112`、分叉点 `ON = OFF + 恰好一段插入块`、违例 0。真跑两臂齐后复核：**真跑复核以「代码级静态复核」替代（本轮零跑批，未新跑 mock 探针）**：两个提示词的插入点均为 `+ mem_line`（`agent.py:1211/1216`、`:1225/1231`），而 `_memory_line()` 在 `if not memory_f6_enabled(): return ""` 处早退（`:1114-1117`）⇒ OFF 时 `mem_line=""`、`A + "" == A`，提示词逐字节不变。原文见 `v2/evidence/f6_single_variable_checks.txt` §(b) | **mock 级：机械验证（探针未入仓 ⇒ 不可复算）**；**真跑级：代码级静态复核（已通过，原文见 `f6_single_variable_checks.txt` §(b)）** |
| (c) | 提交后代码与 `code_sha` 一致 | `git diff 895b9a3 -- code/life code/orchestration code/config` 空 | 已跑（本版 14:36 复跑）：**空输出，rc=0**；`git status --porcelain` 中 `code/{life,orchestration,config,engine}` = `NONE` | **机械验证（已通过，本版复跑）** |

**(c) 本报告写作时的实跑原文：**

```
$ git diff 895b9a3 -- code/life code/orchestration code/config
（空输出）
rc=0
$ git status --porcelain | grep -E "^.. code/(life|orchestration|config|engine)"
NONE
```

> **留档口径**：三查原文的正式留档件 `v2/evidence/f6_single_variable_checks.txt` **在两臂 `meta` 齐、(a) 追完之前不入库、不进证据索引表**（避免报告引用一个即将失效的 sha）；中间态只留在 `round1/`。判读陷阱：`meta.git_dirty_code_files` 用子串 `" code/"` 过滤，会把 `?? code/frontend/sample/…` 算成"代码脏"。**硬判据只有上面这条 `git diff <code_sha> -- code/…`**；引用前者时必同栏给后者。

---

## 5. 结论与局限

### 5.1 可写成「事实」的部分（存在性，不含效果判断）

1. 【事实】**F-6 的缺口是装配缺口**：改动前树 `c1bb533` 上 `_retrieve()`（`:450`）已返回 top-k 记忆，而 `_dialogue_prompt`/`_reply_prompt`（`:1206`/`:1219`）区间内 `记忆|memory` 命中数 = **0**（复算见 §1.1 ③）。
2. 【事实】**干预形态**：唯一开关 `LIFE_PROMPT_MEMORY_F6`（默认 OFF）；OFF ⇒ 返回空串、提示词逐字节不变、`memory_refs` 键不出现。
3. 【事实】**不影响既有检索**：`_memory_line()` 只读 `memory.nodes`，不调 `score_and_rank`、不改 `access_count`；不碰世界态/`state_hash`；未新增事件类型。
4. 【事实】**代码纯洁性 (c) 已通过**：`git diff 895b9a3 -- code/life code/orchestration code/config` 空输出、`git status` 中 `code/{life,orchestration,config,engine}` 无改动项。
5. 【事实·mock】**单变量：(b) 的 mock 级自证**：同 wv 两次装配 `insert_only` 4/4；跨进程 200 对里 112 对逐字节相同、分叉点 `ON = OFF + 恰好一段插入块`、违例 0（**这是探针证据，不是 LLM 证据**）。
6. 【读数】**注入面（OFF 侧）**：510 条 MSG 中 `ctx.memory_refs` 出现 **0** 次（`f6_metrics.py` 的 `ctx_memory_refs_msgs=0`；`r1_f6_compare.py` 自测同样 0）——**只证"OFF 时未注入"，不证"ON 时被用上"**。ON 侧读数：**412**（510 条中 412 条，共 **824** 个 `mem_id` 引用，去重后 **128** 个不同记忆）。

### 5.2 阴性结果与「不可判定」结果（照实写，不修饰；措辞为跑批前预注册）

**A. 已在 OFF 基线上成立的阴性事实（不依赖 ON 臂）**

1. **OFF 臂不存在记忆注入**：`ctx.memory_refs` 命中 0/510 ⇒ 基线批的"跨天记忆引用"完全来自模型自身生成的台词，与注入无关。这是 §3.1 那条 3.73% 的真实来源，不能读成"系统已有记忆能力"。
2. **【事实】M-1 的 3 条命中里 2 条是同一说话人重复自己**（§3.6 逐条给出 `seq` 与 6-gram 计数）：`seq 86316`(P008) 与 `seq 82424`(P008) **正文逐字相同**（共享 6-gram 13/13）；`seq 34699`(P012) 与 `seq 28261`(P012) 共享 3 个 6-gram（复述"不客气 / 肚子咕咕叫"）。⇒ 同一分母 33 下：**主口径 `M-1′ = 1/33`**；`2/33`（严判据，去重下界）与 `3/33`（未去重上界）**只作敏感性分析**，不是并列结论；分母 33 < 68，**三者一律只在事件数级使用、不写比率结论**。
   **这条读法的影响超过 MDE**：MDE 说的是"能不能看见差异"，它说的是"看见了也可能是看错对象"（把复读机当成记得昨天）。§7 建议 1 因此把"先去自我重复"列为下一轮的口径前提，而不是可选项。
3. **F-7（越界提及）在 OFF 臂 per-message 分母只有 2**（`pos=1/2`，`v2/evidence/r1_f7_off.json`）⇒ 按 §0.2 分母纪律**只报事件数，不写百分比、不参与判定**。

**B. 本轮已锁定的「不可判定」结论（事前闸门，非事后解释）**

- 本轮 M-1 机会分母 **33**、`MDE` **19.62pp（overlap）/ 19.83pp（power）**，均越过骨架 §3.5b 自定的 **10pp** 闸门 ⇒ 按预注册规则，M-1 的任何两臂差异**只能**表述为：**「在本样本量下无法在噪声之上判定差异」**。
- 因此 M-1 与 M-0 的百分比**不进入摘要、不进入 §7 小结的效果陈述**，只作为 probe 级描述保留在 §3.5 表中。
- **本轮的主价值不在效果读数，而在**：装配链路已打通（§2）、单变量可机械自证（§4.6）、真跑可复算（§4.2）、四个视图真拍非退化（§4.3）。

**C. ON 臂结果的写法（预注册，读数到手只填事实，不改规则）**

- 若 `F-6` ON > OFF：写「F-6 读数上升 Δ=x.xxpp（den 510，单 seed 单批，未做跨 seed 方差）」，**同段并列** L-6/L-7/L-8 变化；若 `L-7` 恶化 > 5pp ⇒ 按预案写「代价是套路化」，**不得**写"改善了生活气息"。
- 若 `F-6` ON ≤ OFF：按预案写**阴性结果**「干预未抬升 F-6」，并给可能原因（记忆池只覆盖 5 个游戏日 / 人话门过滤后可选素材少 / 指令被模型忽略 / 注入位置被后续上下文淹没），**不得**改口径或改判据。
- **无论哪种情形**，M-1 一律按 B 段写法，不因结果好看/难看而改变措辞强度。

**C-实际（读数已到手，按上面的模板逐条照做，不改规则）**

下判定的是**情形「F-6 升、M-1 不动、L-7 恶化」**，并按预案写法落笔：

1. 【读数】**F-6 读数上升 Δ = +7.45pp**（`0.037255 → 0.111765`，即 19/510 → **57/510**，den 510，单 seed 单批，未做跨 seed 方差）。两臂 Wilson95 为 OFF [2.40%, 5.75%] / ON [8.73%, 14.21%]，**区间不重叠** ⇒ 按 §3.3 判「显著」。
2. 【读数·并列】**同段必须并列的守卫项**：`L-6 0.101961 → 0.127451（65/510，+2.55pp）`；`L-7 0.354902 → 0.65098（332/510，**+29.61pp**）`；`L-8 0.0 → 0.0（0.00pp）`；`L-5 0.011765 → 0.015686（+0.39pp）`。
3. **按预案的措辞裁决**：`L-7` 恶化 **29.61pp ≫ 5pp 闸门** ⇒ 本轮**只能**写「**代价是套路化**」，**禁止**出现「改善了生活气息 / 更像过日子」一类净改善措辞。**本轮结论因此是：干预有效（F-6 升、区间不重叠），但代价显著（L-7 越过预注册闸门），不构成净改善。**
4. 【事实】**"注入了什么"与"说出了什么"的真实对应**（可 `seq` 定位；`mem_id` 可回 `MEMORY_WRITE` 的 `body_ref` 解引用，side-root `/tmp/f6_on60_side`）：
   - **正例 `seq 27449`**（P004，day1，round21）：`ctx.memory_refs = [M-P004-000009, M-P004-000028]`，其中 `M-P004-000009` 原文为「P015 说：今天这锅汤我少放了半勺盐，多搁了一小把干贝…鲜得我自己都多喝了两碗。」；正文为「五味那锅汤啊，我那天听她说少放半勺盐、多搁一把干贝，鲜得她自己都多喝了两碗，可惜我也没赶上。」⇒ **与该记忆共享 7 个 4-gram**，是"注入内容确实进了台词"的字面证据。
   - **反例 `seq 21821`**（P002，day1，round15）：同样注入了两条（**汤类**）记忆，正文却是「小满，你上回说家里凳子腿松了，我顺手给你带了根木楔子。」⇒ **与两条注入记忆 0 个 4-gram 重合**。这说明 **F-6 命中时间回指词 ≠ 用上了注入的记忆**（模型可以自己"想起"别的事，也可能是在说没记过的事——后者本轮无判定器，见 §5.4）。
5. 【读数·描述性（分母 53）】`ctx.memory_refs` 非空且正文命中时间回指词的 MSG 共 **53** 条，其中 **37 条（69.8%）与至少一条注入记忆共享 ≥1 个 4-gram**、16 条无字面重合。分母 53 < 68 ⇒ **只作描述，不写比率结论、不进摘要**。

**D. 本版新增观察（不改任何既有口径，仅补记；供下一轮处理）**

> 这一节是对已填读数的**如实登记**，不是新增判据：预注册的判定规则一条没动，只是把"同一批里还动了什么"摆到桌面上。

1. **`L-7` 恶化 +29.61pp 的质地**：与"记忆池极窄"一致——412 条注入消息共引用 **824** 次、但去重后只有 **128** 个不同 `mem_id`（平均每条记忆被复用 **6.4** 次），且高复用集中在少数几条（如 `M-P001-000007`/`M-P001-000024`/`M-P004-000009` 各被引用 8 次）。
   **可复算的关联（本报告独立复算，与官方 L-7 逐位一致）**：ON 臂 332 条「有 8-gram 近重复」的 MSG 中，**315 条带 `ctx.memory_refs`**；OFF 臂 181 条中带 `memory_refs` 的为 **0**（OFF 无注入）。复算命令：按 `tools/d5/dialogue_metrics.py:476-488` 的定义（正文去空白标点后切 8-gram，凡与其他 MSG 共享任一 8-gram 即计入 `dup_msgs`）重算得 `off 181/510 = 0.354902`、`on 332/510 = 0.650980`，再对 `dup_msgs` 取 `ctx.memory_refs` 非空计数 ⇒ `on 315`、`off 0`。⇒ **重复主要发生在"被注入过记忆"的消息上**，与「记忆行被吸收进正文、再跨线程复用」的机制方向一致。**但这是关联而非因果**：本轮零跑批、未做归因实验，**不写成因果结论**。
   **图证引用位（相对仓库根）**：`v2/evidence/r11_shots/f6_on_vs_off_n16r60_seed42-l7-l13-degradation.png`（`evidence-visualizer` 产出；左 L-7 含预注册闸门 `OFF+5pp = 40.49%` 红线、右 L-13；图注要求「F-6 增益与 L-7 代价必须同时呈现」）。
2. **`M-0`（同日重合）由 1.92%（5/260）跳到 29.62%（77/260，+27.70pp）**：按 §3.5 预注册「若 M-0 与 M-1 同量级 ⇒ 把 M-1 降级为「模板重叠」，不得称为记忆引用」，**ON 侧 M-1（6/33 = 18.18%）与 M-0（29.62%）确属同量级 ⇒ 本报告不把 ON 侧 M-1 称作"记忆引用读数"**。这条使 §7 建议 1 从"建议"升为"硬前提"。
3. **`L-13` 内部 token 泄漏 `n = 2 → 14`（0.003922 → 0.027451，den 均为 510，+2.35pp）**：分项 `whisper 11 / scarce_buy 2 / combat_training 1`（OFF 侧仅 `whisper 2`）。**成因未查**（本轮零跑批、未做归因），只登记读数；但它与 `L-8 = 0`（无 `Pxxx` 泄漏）不冲突——两条测的不是同一件事（`L-13` 测 `ctx.topic` 内部串，`L-8` 测 agent id）。⇒ 下一轮若继续走记忆注入，**必须把 `L-13` 列进守卫表**。**样本 2/510 vs 14/510（分子为事件计数，n=2 与 n=14），不作统计判定，列入下轮预注册候选。**
4. **`F-7a` 越界提及 0.145098 → 0.22549（+8.04pp，den 510；`unknown_place_lookups` 340 → 651）**：同样只登记、不归因。「提到不在场的人」上升，既可能是"记性变好"，也可能是"编造"，本轮无判定器可分辨。
5. **`F-3` / `F-4` 两臂不可比（口径提醒，禁止跨臂比较）**：`F-3` 机会分母 OFF 36 → ON 19、`F-4` 张力事件 OFF 22 → ON 15 —— **机会分母本身随生成行为变化而变化**，跨臂比较这两个数会把"分母变了"读成"效果变了"。本轮不对 F-3/F-4 出任何两臂结论。

### 5.3 观测缺陷（直接决定结论上限，不弱化）

1. **`memory_refs` 只证注入、不证使用**。要证"用上了"，只能靠 M-1 的语言重合间接推断；M-1 抓不到同义改写，且已被 §3.6 证明会混入"台词复读"。
2. **F-6 有天花板**：词表仅 11 个时间回指词，只测"提到过去"，不测"引用是否正确"。
3. **人话门是干预的一部分**：被过滤掉大部分原始事件短语没有进入提示词（该比例来自 mock 探针、**无原始文件**，标「不可独立复核」）⇒ 本轮测的是"过滤后记忆注入"的效果，**不是**"记忆全量注入"。
4. **单 seed 单批**（seed=42、n16×60、每臂仅 1 批），不做跨 seed 方差 ⇒ 只给方向性结论；**不构成统计推断**。
5. **结构性限制（本轮最该记住的一条）**：n16×60 只跨 **5 个游戏日**（`days=[0,1,2,3,4]`，由 `f6_metrics.py` 直接从日志读出）。"跨天回指"的机会本身就少——M-1 机会分母只有 33 条，正是这一点的直接后果；**天数少比 MDE 数字更能解释"为什么这个维度在小规模下难判"**。要放大机会，只能加长回合数（跨更多天）或加大居民数（每轮消息更多），单纯提高统计门槛是没用的。
6. **检验功效（写死在跑批之前，不依赖结果）**：本轮判定采用 **Wilson 区间不重叠**的保守闸门；在 M-1 分母 **33 / 33** 条的量级下，最小可检出效应（MDE，见 §3.5b）为 **19.62pp（overlap）/ 19.83pp（power）**。因此「不显著」只表示**本样本量下无法与噪声区分，不表示无效果**；反过来说，**也不表示有方向性效果**——两个方向都不许过度解读。
7. **本轮尺寸 n16×60**，与历史 **n16×84** 批（以及更早的 n8 设想）**不可逐值对比**（尺寸变更口径见 §6.1）。

### 5.4 未观测 / 不可得（照实列，不填坑）

- 未观测：记忆注入是否导致"编造未记过的事"（无幻觉/事实性判定器，本轮不评测）；
- 未观测：长程（跨 3 天以上）记忆引用是否比短期更难（本轮总跨度只有 5 天，**结构上做不了**）；
- **不可复算（本版新增，必须写明）**：单变量三查 (b) 的 mock 探针脚本 `probe_prompt_identity.py` / `probe_prompt_diff.py` 与 §2.4 的人话门探针，均只在**上一届团队工作空间** `…/round1/` 留档，**未入仓** ⇒ 本报告对这两项只引用其**留档结论与 sha256**，**标「不可独立复核」**；
- 不可得：`M-3 记忆原文锚点率` 需解引用 `side://src/<sha>.txt`，解不出即 `not_available`，不参与结论。
- ~~未获取到：ON 臂四视图 PNG~~ → **已获取**（`evidence-visualizer` 于 2026-10-21 16:08 产出，文件名与预留位一致；sha256 与「非退化判据」由本报告独立复算，见 §4.3）。
- **未获取到：本文件 commit sha**（原因：报告尚未提交；由 `delivery-gatekeeper` 提交后以 `git log -1 --format=%H -- reports/R11-f6-memory-into-dialogue.md` 取得）。
- 未观测：`L-13` 上升的成因（本轮零跑批、未做归因实验）；`F-7a` 上升的成因（同上）。

---

## 6. 与基线的对比

| 对比项 | 做法 | 允许的写法 | 禁止的写法 |
|---|---|---|---|
| 本轮 OFF vs ON | 同 `code_sha 895b9a3`、同 **n16×60** seed42、唯一 env 差异 | 「两臂内部 Δ」+ 区间/Wilson 判定 | 无 |
| 与 `6.4%`（`884f4541`，R4） | **跨 code_sha**（且分母仅 187） | 「历史参照（跨 code_sha，不可直接等同）」 | 「从 6.4% 提升到 X%」「涨了 Y 个百分点」等任何等价比 |
| 与历史 n16×84 批 | **尺寸不同** | 「尺寸不同，不可逐值对比」 | 逐值比较或按比例折算 |

### 6.1 尺寸变更与可信度声明（含本版订正的「次序 4」）

| 次序 | 尺寸 | 结局 | 变更依据 |
|---|---|---|---|
| 1 | n16×84 | 跑到 round 9 作废（目录 `run_f6_off_n16r84_seed42_VOID/`，`run.jsonl` 9,679 行 / sha256 `4c8ef41ee398cb87…`，`VOID.md` sha256 `c6e961cf…`） | 实测 pace 2.5–4 倍于预估 |
| 2 | n16×60 | 跑到 round 6 作废 | calls/round 由历史 48 升至 78（+62%）⇒ 两臂 n16 预计 6.5 小时 |
| 3 | ~~n8×60~~ | **未执行**（骨架按此写死，属笔误） | — |
| **4（最终，实际执行）** | **n16×60** | 正式批：OFF `run_f6_off_n16r60_seed42`（12:35:19→14:02:00，`duration_sec=5201`）、ON `run_f6_on_n16r60_seed42` | 依据 OFF `meta.json` 的 `n=16`/`rounds=60`（实测值，非声明值） |

> **可信度声明（必须有）**：前两次尺寸变更**发生在算出任何 F-6 / M-1 读数之前**——当时只看得到 round 进度与 calls/round，**没有看过任何指标数字**，因此不是"看着结果调实验"。
> **次序 4 的性质不同，必须单独说清**：它不是新的实验设计决策，而是**本报告对骨架笔误的订正**（骨架写 `n8×60`，实际两臂一直是 `n16×60`）。订正发生时 ON 臂**仍在跑**（`pgrep` 可见 `orchestration run --life … --agents 16 --rounds 60`），且订正只改文字、不改任何分母/阈值/判据 ⇒ **不构成"看结果改口径"**。

**作废批处置**：两批均**保留不删**、仅标注，其任何读数**不写入本报告**。

### 6.2 calls/round 异常（独立发现，也是"跨批不可比"的具体机制）

| 项 | 历史批 | 本轮 OFF 臂 |
|---|---|---|
| calls/round | ~48 | **78（+62%）** |
| OFF 臂行为 | — | 走空串分支、**零额外调用** |

⇒ OFF 臂不因 F-6 多花一次调用，calls/round 却仍显著高于历史 ⇒ **本轮运行环境/版本与历史批不同**，这是"跨批不可比"的具体机制，而不只是尺寸差异。

> **但不影响内部对比**：两臂**同代码（`895b9a3`）、同环境、同尺寸、同 seed**，唯一差异是 `LIFE_PROMPT_MEMORY_F6`；外部环境漂移对两臂是同向等量的，故 **OFF vs ON 的内部 Δ 不受此影响**。

### 6.3 成本对比：干预的固有代价（**有效结论，不是脚注**）

记忆注入会让**对话提示词逐条变长且不再命中缓存**，这是干预的固有成本。OFF 臂实测与 ON 臂实测并列如下（`obs llm-cost`，不传 `--cache-dir`）：

| 成本项 | OFF（实测） | ON | 说明 |
|---|---|---|---|
| `total.calls` | **2878** | **2878** | 调用次数 |
| `total.cached` | **1472**（ratio **0.5115**） | **1477**（ratio **0.5132**） | 命中缓存数；OFF 侧 `meta.llm_cached_ratio=0.5115` |
| **未命中 = 计费/耗时来源** | **1406**（2878−1472） | **1401**（2878−1477） | 这是真正的"跑一次要多久"的主因子 |
| `tokens_in` | **228749** | **271717** | 入向 token |
| `tokens_out` | **256086** | **269123** | 出向 token |
| `tokens_total` | **484835** | **540840** | in+out |
| `by_purpose.dialogue.tokens_in` | **88878**（510 calls） | **130924**（510 calls） | **只看对话这一路**，最能反映干预直接影响 |
| 墙钟 `duration_sec` | **5201**（86.7 min） | **6436**（107.3 min；相对 OFF **+23.75%**） | 实际墙钟（`meta.duration_sec`），非估算 |
| 每秒 call 数（粗算） | **0.553 calls/s**（2878/5201） | **0.4472 calls/s**（2878/6436） | 两臂同法计算 |

**怎么读这张表（事前定的读法 + v2 的实况裁决）**：成本上升属**干预的固有代价**，不设阈值裁决；但必须给出「每多注入一条记忆，值多少延迟/token」的量级感。

**事前写下的读法**：「若 ON 臂 `cached` 显著下降而 `calls` 不变，则**时间成本几乎全部来自缓存失效**（提示词变长且不再命中前缀缓存）」。

**v2 实况（照实写，包括与预判不符的部分）**：`cached` **没有下降**——OFF 1472（0.5115）→ ON **1477**（0.5132），未命中数 1406 → **1401**（还少了 5 次），`calls` 两臂同为 2878。⇒ **前述预判在本批被否证：墙钟 +23.75% 不是缓存失效造成的**。可复算的替代解释只有一个方向——**入向 token 变多**：`tokens_in` 228749 → 271717（**+18.78%**），其中**对话这一路** 88878 → 130924（**+47.31%**，510 calls）；`tokens_out` 256086 → 269123（+5.09%）。即：每条对话提示词更长（多了一段记忆行），模型输出也稍长 ⇒ **时间与 token 成本来自"提示词变长"，不是"缓存失效"**。

> 量级感（可复算）：510 条对话多花的入向 token = `130924 − 88878 = 42046`，摊到 510 条 ⇒ **≈82 token/条**；相对整批 `tokens_total` 的 +56005（+11.55%）。这是「每多注入一段记忆，值多少 token」的直接读数。**该结论与效果读数无关，独立成立；且它推翻了本报告 v1 里预先写下的缓存假设，按纪律必须原样写出、不得静默删掉预判。**

---

## 7. 本轮小结与下一轮建议

**本轮小结**
- 本轮把 F-6 从「检索有、提示词无」的装配缺口，做成一个**同代码、单 env、可机械自证**的干预；
- 口径在 ON 臂起跑前已冻结（`metrics-definition-frozen.md`，sha256 `f0f1f4b45b5f6c832fa4739879592261843bcc5196c947e62388b2eaac0c4cb8`，含判定规则、抽样规则与结果处置预案）⇒ 不存在"看结果再改口径"的空间；
- OFF 基线：`F-6 0.037255（19/510）`、`L-6 0.101961`、`L-7 0.354902`、`L-8 0.0`、`admission=ADMITTED`、验真 `provider_guard.ok=true`；
- **M-1 被事前闸门判为不可判定**（分母 33、MDE ≈19.6pp > 10pp）⇒ 本轮不以 M-1 作效果陈述；主价值落在装配链路打通 + 单变量可自证 + 真跑可复算 + 四视图非退化；
- **ON 臂读数已回填**：`F-6 = 0.111765（57/510）`，相对 OFF `0.037255（19/510）` 升 **+7.45pp**，两臂 Wilson95 **不重叠**（[8.73%,14.21%] vs [2.40%,5.75%]）⇒ 按 §3.3 判「显著」；**但同一批的守卫项同步恶化**：`L-7 0.354902 → 0.65098（+29.61pp）`、`L-6 0.101961 → 0.127451（+2.55pp）`，且同口径 M-0（同日重合）由 1.92% 跳到 29.62%。按预注册预案，本轮结论写成：**「干预确实把跨天回指词写进了台词（F-6 升），代价是套路化（L-7 越过 +5pp 闸门）⇒ 不构成生活气息的净改善」**，M-1 家族因分母 33 / MDE 22.97pp 仍**不可判定**。

**本轮局限（与上面并列陈列，不藏在附录）**
- **度量效度问题（本轮最根本的一条）**：M-1/6-gram 口径在 OFF 基线上就有 **2/3 的命中是"自我复读"**（3 条里 2 条，`seq 86316`/`82424` 逐字相同、`seq 34699`/`28261` 复述）。这意味着**本轮 M-1 的任何一个百分比都不应被直接当作"跨天记忆引用率"**；即使样本放大到分母 ≥68，只要不去重，复读比例也会被一起放大 ⇒ 不去重就不构成有效度量。
- **〔推论 / probe，非事实〕F-6 可能同样不免疫**——F-6 只看"是否出现时间回指词"，**机制上**它区分不了"真的想起昨天"与"把昨天那句再说一遍"。本轮**没有**对 F-6 的 19 条命中逐条做去重判定，故这只是推论，**不进 F-6 结论、不进摘要**。若后续要升格为结论，须先按 Leader 裁决在 n32 规模上跑「回指词 + 去重后语义是否指向被引用事件」的双条件判据。

**下一轮建议（按性价比排序，第 1 条为口径前提）**
1. **【口径修正，优先级最高】任何 F-6 / M-1 读数都必须先去自我重复**：判据用本轮 §3.6 的主口径（同一说话人 且 共享 6-gram ≥ 3 ⇒ 剔除），并把 `M-1` 与 `M-1′` **两个值并列报**；基准值取本轮实测 **OFF `M-1 = 3/33`、`M-1′ = 1/33`**（严判据 `2/33`）；**ON 同口径 `M-1 = 6/33`、`M-1′ = 2/33`（严判据 `6/33`）**，下一轮两臂都按同判据复算再比，下一轮只用同一判据、同一预处理做比较，**不得中途改阈值**。若下一轮想改判据，必须先写进预注册再跑。
2. **放大跨天机会（本轮暴露的最大瓶颈）**：n16×60 只有 5 个游戏日 ⇒ M-1 机会分母仅 33。两条可排期路线：
   - **n32×60**：消息量约翻倍至 ~1020，M-1 机会分母预估 **≈66–70**（线性外推，**推断·未实测**），耗时 **≈2.9 h**（同样为推断；若 cached 继续失效，按 ON 臂实测速率重估）；
   - **n16×120**：游戏日翻倍（跨天机会更密），耗时同为 **≈2.9 h** 量级，但**总消息量只翻一倍**，M-1 分母与 n32×60 相近。
   - 判据：**本轮不改口径、不重定义分母**；下一轮要把 n 写进预注册再跑，才能把 M-1 从 probe 升级到可判定。
3. **M-1 的语义真伪判别（人工抽检，补机器判据的盲区）**：本轮 §3.6 已证明 3 条命中里 2 条是台词复读。下一轮应改用 `v2/evidence/r1_f6_compare.py` 的口径（正文 vs **被注入记忆正文**的 6-gram 重合 = `mem_echo`），并配 20 条人工抽检量表（逐条判"是否真的想起旧事"），把口径与抽检一致率绑定。
4. **F-3 情绪呼应**：把「对方上一句的情绪极性」注入提示词（`life/emotion.py` 已有判定器），与 F-6 属同一类 prompt 装配面，改动面小、指标可复用；但注意 F-3 当前分母只有 **36（probe 级）**，同样需要先扩规模。
5. **人话门可用率脚本化**：把 §2.4 的比例从"口述 mock 读数"升级为仓内可复跑脚本，这是当前报告唯一"不可独立复核"的数字。

---

### 附录 D：占位符扫描（v2 终稿，**0 处**）

> 扫描时间：2026-10-21 16:20（ON 臂产物已齐）。扫描口径与 v1 相同：统计全文件「连续两个左花括号」的出现次数（命令见下表，用 `'{'*2` 拼出模式，避免自指）。
> **结果：0 处。** v1 的 78 处（ON 臂产物类 65 / 结论判定文本类 8 / 提交后值类 5 / 三查终态类 3）已全部处理，
> 处理方式分三类：**填实**（绝大多数，来源为 ON 臂 `meta.json` / `host.log` / `run.jsonl` / `obs llm-cost` 输出 / 官方指标 json）、
> **换成真实测得的替代值**（单变量 (b) 的「真跑 prompt 复核」→ 代码级静态复核原文）、**显式标「未获取到 + 原因」**（仅 2 处，见下）。

| 项 | 状态 | 说明 |
|---|---|---|
| 全部模板占位符（连续两个左花括号包名） | **0 处** | 复算：`python3 -c "print(open('reports/R11-f6-memory-into-dialogue.md',encoding='utf-8').read().count('{'*2))"` → 输出 `0` |
| ON 臂四视图 PNG | **已获取**（4 张，sha256 全值见 §4.3） | 由 `evidence-visualizer` 于 2026-10-21 16:08 产出，文件名与 §4.3 预留位完全一致；本报告独立复算 sha256 与非退化统计，未使用空白占位图 |
| 本报告 commit sha | **未获取到** | 原因：文件尚未提交；由 `delivery-gatekeeper` 提交后以 `git log -1 --format=%H -- reports/R11-f6-memory-into-dialogue.md` 取得并回填版本栏 |
| §4.6 (b) 的「真跑 prompt 复核」 | **部分未获取到** | 原因：真跑 prompt 抓取需新增 mock 探针（脚本未入仓），本轮**零跑批**纪律下不新跑；改用**代码级静态复核**（`_memory_line()` 早退 ⇒ `mem_line=""` ⇒ 提示词逐字节不变），原文见 `v2/evidence/f6_single_variable_checks.txt` §(b) |
| 上一届 mock 探针（`insert_only` 4/4、跨进程 200 对） | **不可复算** | 脚本只留在上一届团队工作空间，未入仓（§5.4 / §8 E-5..E-7），只引用留档 sha256，**不升级为证据** |

> 说明：本附录**不是**"仍留占位符的清单"，而是"终稿已清零 + 仍缺的两处缺口逐条给原因"的清单。按任务验收口径，缺口均已显式标注「未获取到」并写明原因。

### 附录 A：工作区未跟踪项清单（本版写作时原文，32 项）

```
$ git status --porcelain | grep '^??' | cat -n
     1	?? code/frontend/sample/dialogue_run_f6_off_n16r60_seed42/
     2	?? code/frontend/sample/dialogue_run_g1_b0_n16r60_seed42/
     3	?? reports/R11-f6-memory-into-dialogue.md
     4	?? tools/f6/
     5	?? v2/evidence/d4_a1_overlap_check.py
     6	?? v2/evidence/d4_a1_pipeline.sh
     7	?? v2/evidence/d4_judge_run.py
     8	?? v2/evidence/d4_judge_sample.py
     9	?? v2/evidence/d4_judge_sample_A0.json
    10	?? v2/evidence/d4_judge_sample_P1.json
    11	?? v2/evidence/d4_judge_sampling_plan.md
    12	?? v2/evidence/d4_judge_summary.py
    13	?? v2/evidence/d4_metrics_P1.json
    14	?? v2/evidence/d4_preflight_P1.json
    15	?? v2/evidence/d4_prompt_diff_P2.txt
    16	?? v2/evidence/d4_prompt_diff_P3.txt
    17	?? v2/evidence/d4_prompt_patch.py
    18	?? v2/evidence/d4_r9_binding_audit.md
    19	?? v2/evidence/d4_side_by_side.md
    20	?? v2/evidence/f6_cost_off.json
    21	?? v2/evidence/f6_shots/
    22	?? v2/evidence/g1_launch_evidence_b0.txt
    23	?? v2/evidence/r1_f6_compare.py
    24	?? v2/evidence/r1_f6_off_metrics.json
    25	?? v2/evidence/r1_f6_off_metrics.md
    26	?? v2/evidence/r1_f6_preregistration.md
    27	?? v2/evidence/r1_f7_off.json
    28	?? v2/evidence/run_dr_round1_arm-ctrl_n16r60_seed42/
    29	?? v2/evidence/run_f6_off_n16r60_seed42/
    30	?? v2/evidence/run_f6_off_n16r84_seed42_VOID/
    31	?? v2/evidence/run_f6_on_n16r60_seed42/
    32	?? v2/evidence/run_g1_b0_n16r60_seed42/
```

**分类与处置（本轮严格遵守"只提交本轮相关"）**

| 类别 | 条目 | 处置 |
|---|---|---|
| 本轮报告 | `reports/R11-f6-memory-into-dialogue.md` | **入库**（ON 臂读数到手并核验后定稿提交） |
| 本轮脚本 | `tools/f6/`（`f6_metrics.py`，sha `be27a3be…`） | **入库** |
| 本轮证据 | `v2/evidence/f6_cost_off.json`、`f6_shots/`（4 张 PNG）、`r1_f6_off_metrics.{json,md}`、`r1_f6_preregistration.md`、`r1_f6_compare.py`、`r1_f7_off.json` | **入库** |
| 本轮 run 目录 | `run_f6_off_n16r60_seed42/`（`meta.json`+`host.log` 入库，`run.jsonl` 被忽略）、`run_f6_on_n16r60_seed42/`（同）、`run_f6_off_n16r84_seed42_VOID/`（作废批，sidecar 入库） | **sidecar 入库 / 日志不入库** |
| 本轮前端派生物 | `code/frontend/sample/dialogue_run_f6_off_n16r60_seed42/` | **入库**（依据 §4.4） |
| 历史遗留 | 15 个 `d4_*` | **一律不动、不提交**（`git log --all` 与本轮 `grep` 均无归属） |
| G1 批次 | `code/frontend/sample/dialogue_run_g1_b0_n16r60_seed42/`、`v2/evidence/g1_launch_evidence_b0.txt`、`run_g1_b0_n16r60_seed42/` | **不提交**，留作下一轮候选 |
| 其他历史 | `run_dr_round1_arm-ctrl_n16r60_seed42/`（DR 对照臂） | **不提交**，留作 C2 候选 |

> `.gitignore` **不新增条目**（本轮无需要特批放行的文件类型）。

### 附录 C：可直接粘贴的复算命令（n16r60 正式批版；不必先读 §4.5）

```bash
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
OFF=$REPO/v2/evidence/run_f6_off_n16r60_seed42
ON=$REPO/v2/evidence/run_f6_on_n16r60_seed42

# ① 批身份 + 完整性
sha256sum $OFF/run.jsonl $ON/run.jsonl
wc -l $OFF/run.jsonl $ON/run.jsonl
python3 -c "import json;d=json.load(open('$OFF/meta.json'));print(d.get('code_sha'),d.get('events'),d.get('llm_provider_in_events'),d.get('fallback_detected'))"
python3 -c "import json;d=json.load(open('$ON/meta.json'));print(d.get('code_sha'),d.get('events'),d.get('llm_provider_in_events'),d.get('fallback_detected'))"

# ② 真 LLM 验真（不传 --cache-dir）
cd $REPO/code
python3 -m obs llm-cost --log $OFF/run.jsonl --require-provider openai_compat; echo rc=$?
python3 -m obs llm-cost --log $ON/run.jsonl  --require-provider openai_compat; echo rc=$?

# ③ 官方指标（F-6 / L-5..L-8 唯一来源）
python3 $REPO/tools/d5/dialogue_metrics.py --log $OFF/run.jsonl --meta $OFF/meta.json --out-json $REPO/v2/evidence/r1_f6_off_metrics.json
python3 $REPO/tools/d5/dialogue_metrics.py --log $ON/run.jsonl  --meta $ON/meta.json  --out-json $REPO/v2/evidence/r1_f6_on_metrics.json

# ④ M-1 / M-1b / M-0 + 差值表（冻结脚本 be27a3be…）
python3 -m obs llm-cost --log $OFF/run.jsonl --require-provider openai_compat > /tmp/f6_cost_off.json
python3 -m obs llm-cost --log $ON/run.jsonl  --require-provider openai_compat > /tmp/f6_cost_on.json
python3 $REPO/tools/f6/f6_metrics.py \
  --run OFF=$OFF/run.jsonl --run ON=$ON/run.jsonl \
  --official OFF=$REPO/v2/evidence/r1_f6_off_metrics.json --official ON=$REPO/v2/evidence/r1_f6_on_metrics.json \
  --cost OFF=/tmp/f6_cost_off.json --cost ON=/tmp/f6_cost_on.json \
  --out $REPO/v2/evidence/f6_metrics_two_arms.json --markdown $REPO/v2/evidence/f6_metrics_two_arms.md

# ⑤ 代码纯洁性（期望空输出）
cd $REPO && git diff 895b9a3 -- code/life code/orchestration code/config; echo "rc=$?"

# ⑥ 单变量自证（mock，零网络）—— ⚠️ 本项**不可复算**：
#    探针脚本 probe_prompt_identity.py / probe_prompt_diff.py 只留在上一届团队工作空间（round1/），
#    本轮**未入仓**，故此处不给出可执行路径；只引用其留档结论与 sha256（§8 E-5/E-6）。
#    原命令形态（仅供追溯，勿照抄）：
#      env -u HITT_LLM_PROVIDER python3 <round1>/scripts/probe_prompt_identity.py --out /tmp/id.jsonl
#      env -u HITT_LLM_PROVIDER -u LIFE_PROMPT_MEMORY_F6 python3 <round1>/scripts/probe_prompt_diff.py --out /tmp/off.jsonl
#      env -u HITT_LLM_PROVIDER LIFE_PROMPT_MEMORY_F6=1   python3 <round1>/scripts/probe_prompt_diff.py --out /tmp/on.jsonl

# ⑦ 截图（真拍四视图）
cd $REPO/code && python3 frontend/tools/serve.py --host 0.0.0.0 --port 8848 &
python3 frontend/tools/gen_threads.py --log $ON/run.jsonl --meta $ON/meta.json \
  --out frontend/sample/dialogue_run_f6_on_n16r60_seed42/threads.json --require-complete
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 \
  sample/dialogue_run_f6_on_n16r60_seed42/threads.json "" "" ../v2/evidence/f6_shots
```

---

### 附录 B：R9 绑定审计的关键原文（本地未入库件，仅内嵌结论）

> **来源状态（不省）**：作者已知为 prompt-linguist（非本轮成员、非本团队产出），该文件未入库且 `grep -rn` 在 `reports/` 下零引用，故本报告只内嵌结论、不引用其路径。

> 以下为**逐句摘录**（不改写），非"大意复述"。

**§1 事实一：A1 臂不止改两条提示词**

```
git -C <repo> diff 884f4541 a637371 -- code/life/dialogue_threads.py
# (关键 hunk)
-    "reply_window_rounds": 2,     # 入站消息在多少回合内仍可被回（超时即线程结束）
+    "reply_window_rounds": 4,     # ... [D9: 2→4 单变量]
```

> 「⇒ **A1 臂同时把"可回窗口"从 2 回合放宽到 4 回合**（线程化剂量变量）。若沿用 R9 绑定，A0→A1 是**两个变量**（提示词 + 回窗），A1 结论须降级为"合并效应"。」

**§2 事实二：A0 的 `code_sha` 疑为事后回填**

> 「`v2/evidence/run_d2_after_n16_seed42/meta.json`：`code_sha = code_sha_end = 884f4541…`、`generated_after_run = true`、`assertions = null`。」
> 「但该批 **19:19 起跑时 landing 是 `3ec85a0`**（leader 21:54 通告与 S0e 判据均以 3ec85a0 为基线）。」

**§3 交叉验证：prompt_sha 对不上**（`tools/prompt_iter` 口径 = `life/agent.py` + `life/soft.py` + `life/planner.py`）

| 树 | prompt_sha |
|---|---|
| `3ec85a0`（A0 日志实际所在树） | `2cb2f5ba9c8d43c5` |
| `884f4541`（meta 里记的 code_sha / R9 报告用的 A0 基线） | `e6ec7355789358d8` |
| `a637371`（R9 的 A1） | `5186aa9a3db55de8` |

> 「⇒ R9 报告的 A0 `prompt_sha e6ec7355…` **不是**产生 `run_d2_after_n16_seed42` 那份日志的树的 prompt_sha。」

**复算命令（不依赖该文件也能自验）**

```bash
cd <repo>
for ref in 3ec85a0 884f4541 a637371; do
  python3 - "$ref" <<'PYEOF'
import hashlib, subprocess, sys
ref=sys.argv[1]; h=hashlib.sha256()
for rel in ("life/agent.py","life/soft.py","life/planner.py"):
    h.update(rel.encode()); h.update(subprocess.check_output(['git','show',f'{ref}:code/{rel}']))
print(ref, h.hexdigest()[:16])
PYEOF
done
```

**本报告为什么内嵌它**：本轮三查 (a) 的「与当时实际 landing 比对、防事后回填」正是这份审计的核心教训；我们要把方法用在本轮，而不是重犯它批出的那种失真。

---

## 8. 证据索引表

> **硬规矩（本轮起）**：每行必须同时有 **文件路径 + sha256 + 复算命令**；三者缺一，该行只能进附录、不得进摘要或结论。源码类行的 `sha256` 列写**该臂 commit sha**（`reports/README.md` 已批准的例外），不用文件 sha256。

| # | 结论 | 层级 | 来源路径 | sha256（源码行=commit sha） | sha8 | 复算命令 |
|---|---|---|---|---|---|---|
| E-1 | F-6 装配缺口（检索有、prompt 无） | 【事实】 | `code/life/agent.py:450` ↔ `:1206/:1219` | `895b9a381cd5a1838c23bd3b38e139f7edade3b8`（改动前树 `c1bb5335af8c00…`） | `895b9a3` / `c1bb533` | `git show c1bb533:code/life/agent.py \| sed -n '1080,1101p' \| grep -c "记忆\|memory"`（实测 0） |
| E-2 | 干预实现与开关默认 OFF | 【事实】 | `code/life/agent.py:56,58,60,63-65,174,947-951,1103-1199,1206,1219` | `895b9a381cd5a1838c23bd3b38e139f7edade3b8` | `895b9a3` | `git show 895b9a3 --stat` + `grep -n "MEMORY_F6_ENV\|def _memory_line\|def _dialogue_prompt" code/life/agent.py` |
| E-3 | 指标口径冻结版 v1 | 【口径】 | `metrics-definition-frozen.md`（**上一届团队工作空间 round1/，未入仓、不可本仓复算**） | `f0f1f4b45b5f6c832fa4739879592261843bcc5196c947e62388b2eaac0c4cb8` | `f0f1f4b4` | 见 §5.4「不可复算」条目；原命令 `sha256sum <round1>/metrics-definition-frozen.md` |
| E-4 | **M-1/M-1b/M-0 计算脚本（已入仓）** | 【口径】 | `tools/f6/f6_metrics.py` | `be27a3be696f39e6f64c506ad19f42e20fbc33b9e056ce2a22820cf9ccc90c6a`（与源件**双 sha 一致**，`cmp` 通过） | `be27a3be` | `sha256sum tools/f6/f6_metrics.py`；源件同名 sha 见 §4.5 订正说明 |
| E-5 | 单变量自证（同 wv 装配，mock） | 【读数·mock·**不可复算**】 | `round1/evidence_prompt_identity.jsonl`（未入仓） | `619ef419aa920859cccc25120a6a36ab2bdd2352ff8d18d9c7fe56a0a595adf8` | `619ef419` | 无本仓复算入口（脚本未入仓），见 §5.4 |
| E-6 | 单变量自证（跨进程 200 对，mock） | 【读数·mock·**不可复算**】 | `round1/evidence_prompt_diff.txt`（未入仓） | `a52c95a8e444ef6324152b65da75852aee24d1b625206a74edb16c538404dc23` | `a52c95a8` | 无本仓复算入口（脚本未入仓），见 §5.4 |
| E-7 | 探针脚本（装配/跨进程） | 【口径·**未入仓**】 | `round1/scripts/probe_prompt_identity.py` / `probe_prompt_diff.py` | `b0f081ee638d22ddd9098abd785143252416d0bb0cce767964d386e747c6d0e9` / `912f60ccd3364e7d53f35c062cc5da19a9c949df39eedb3add073b083b702d03` | `b0f081ee` / `912f60cc` | 无（原路径已失效） |
| E-8 | 作废批（n16r84，不入结论） | 【读数·作废】 | `v2/evidence/run_f6_off_n16r84_seed42_VOID/VOID.md` | `c6e961cf23b35bab3179691d9aa3c54e349158dd3be4471ee58e2b09c22e7fa4` | `c6e961cf` | `sha256sum v2/evidence/run_f6_off_n16r84_seed42_VOID/VOID.md`；`cat` 其内容 |
| E-9 | **OFF 臂 run.jsonl（不入库，`.gitignore:8`）** | 【读数】 | `v2/evidence/run_f6_off_n16r60_seed42/run.jsonl`（55,213,213 B / 116294 行） | `c73bead61a440db789f6d6ba1de555fe326a203ee27d1219690174e3d9483642` | `c73bead6` | `sha256sum v2/evidence/run_f6_off_n16r60_seed42/run.jsonl`；`wc -l` |
| E-10 | **OFF 臂 sidecar（入库）** | 【事实】 | `v2/evidence/run_f6_off_n16r60_seed42/{meta.json,host.log}` | meta `5d0634b6f43b0129496f329c071ad55bb876ca499d322933a3896c5012930500`；host.log `fee17565629e55a5aa287236fc47f152ad15c6b5d71324fce7fdc9dc666bc654` | `5d0634b6` / `fee17565` | `sha256sum v2/evidence/run_f6_off_n16r60_seed42/{meta.json,host.log}` |
| E-11 | **OFF 臂验真原文（`obs llm-cost`，rc=0）** | 【事实·真跑】 | `v2/evidence/f6_cost_off.json` | `69f3b5a8d6ed03c7799c9ca12ea1ed124ad2f6fd9e6db1f0a4a03f4d08a7b8a1` | `69f3b5a8` | 附录 C ②；两次独立运行输出**逐字节相同**（`cmp` 通过） |
| E-12 | **OFF 臂官方指标复算（F-6/L-5..L-8 唯一来源的输出件）** | 【读数】 | `v2/evidence/r1_f6_off_metrics.json` / `.md` | `cb757208249dd9fc02bbd712d70070c1d998d018aab3b89e84a3721502fc355c` / `6447f80567a3f75c88ae706e582574ec7af66c43d0c6fc64613630ed1c9b5e00` | `cb757208` / `6447f805` | `python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_f6_off_n16r60_seed42/run.jsonl --meta v2/evidence/run_f6_off_n16r60_seed42/meta.json --out-json v2/evidence/r1_f6_off_metrics.json` |
| E-13 | **预注册判据（起跑前写死）** | 【口径】 | `v2/evidence/r1_f6_preregistration.md` | `4f4e8017821350c53bc3486b47e334cc691cedcbcfa37fc1240c16d323272155` | `4f4e8017` | `sha256sum v2/evidence/r1_f6_preregistration.md` |
| E-14 | **四视图真拍（OFF 臂，4 张）** | 【读数·渲染】 | `v2/evidence/f6_shots/run_f6_off_n16r60_seed42-<view>-c73bead6.png` ×4 | chat `966be072…02ee` / rhythm `0f1bae4b…c5c1` / spread `d7d76405…09ca` / 600 `2dffa247…cbd1`（全值见 §4.3 表） | `c73bead6` | 附录 C ⑦（`gen_threads.py` + `dialogue_shots.sh`）；非退化统计见 §4.3 |
| E-15 | **前端派生物（入库，依据见 §4.4）** | 【产物】 | `code/frontend/sample/dialogue_run_f6_off_n16r60_seed42/threads.json`（1,987,464 B） | `665e1a09bc134f7cffcdea7e4e86648846993a559aa12f36bfccdb818cd32d31` | `665e1a09` | `sha256sum code/frontend/sample/dialogue_run_f6_off_n16r60_seed42/threads.json` |
| E-16 | `memory_refs` 审计脚本（中途零 LLM） | 【口径】 | `v2/evidence/r1_f6_compare.py` | `3bccedb946592efecd96512adabcd04aa90e975fdd3d5187f958fd75ca8213e5` | `3bccedb9` | `sha256sum v2/evidence/r1_f6_compare.py`；用法见文件头 |
| E-17 | F-7 越界提及（OFF，分母 2 ⇒ 只报事件数） | 【读数·probe】 | `v2/evidence/r1_f7_off.json` | `c30ebcbee71a587f4ec520c6c3498fb8be181cb0d6c62a5c2dee89bd20fd840e` | `c30ebcbe` | `python3 tools/f7/f7_offscreen_mention.py ...`（口径 `v2/refs/F7-offscreen-criteria.md`） |
| E-18 | ON 臂 run.jsonl（55,235,141 B / 116261 行，不入库） | 【读数】 | `v2/evidence/run_f6_on_n16r60_seed42/run.jsonl` | **`7de6a7be5adff276f1e42c065a708c271f870f2bf8daa930cf0cdfc983f7434d`** | `7de6a7be` | `sha256sum v2/evidence/run_f6_on_n16r60_seed42/run.jsonl`；`wc -l` |
| E-19 | ON 臂验真（`obs llm-cost`, rc=0） | 【事实·真跑】 | `v2/evidence/f6_cost_on.json` | `db92fee77701c509ffd61ac5fc3f354c50562b1efeab8cc0f8e2d909ad4594d8` | `db92fee7` | 附录 C ②（不传 `--cache-dir`） |
| E-19b | ON 臂官方指标 + M 家族交叉核对 | 【读数】 | `v2/evidence/r1_f6_on_metrics.json` / `.md` / `r1_f6_on_f6metrics.json` | json `abe4977d8ecb6dc40ab7883ea7f3a614f5f6dc1d7db66e8680b74477c1ded410`；md `56f025bf280fba568614be3ad9cb243679b13ec60d2084a70fcace1603fcd8c2`；f6metrics `519689d7f77ec8ff6359d0453081a218039bfc3c6d5fe152c0de2793d4fc035d` | `abe4977d` / `56f025bf` / `519689d7` | 附录 C ③④ |
| **E-21** | **M-1 去自我复读判定（`M-1 = 3/33` / `M-1′ = 1/33` / strict `2/33`）** | 【事实】 | 派生自 `v2/evidence/run_f6_off_n16r60_seed42/run.jsonl`（`c73bead6…`），无需新文件；命令内嵌 §3.6 | 见 §3.6「去重判定」脚本（已在本机实跑，输出与报告逐行一致） | `c73bead6` | §3.6 末段 `python3 - <<'PY'`（去重判定块） |
| E-20 | 单变量三查 (a)(b)(c) 终态原始输出 | 【事实/判断】 | `v2/evidence/f6_single_variable_checks.txt` | `aa9f9f7e2761951aed784d05151d19e3aca831debc1acb4332a3812374fbfc5a` | `aa9f9f7e` | `sha256sum v2/evidence/f6_single_variable_checks.txt` + 附录 C ⑤⑥ |
| E-23 | ON 臂四视图真拍（4 张） | 【读数·渲染】 | `v2/evidence/f6_shots/run_f6_on_n16r60_seed42-<view>-7de6a7be.png` ×4 | chat `2cf622eb…abfd` / rhythm `fc11501c…1c32` / spread `308844de…9f7e` / 600 `54e36930…6f88`（全值见 §4.3） | `7de6a7be` | 附录 C ⑦（`gen_threads.py` + `dialogue_shots.sh`）；非退化统计见 §4.3 |
| **E-22** | **M-1 去自我复读判定器（新增，判据冻结不可调阈值）** | 【口径】 | `tools/f6/f6_m1_dedup.py` | `b9faa7de1e8dabcc15a40954ced6196748f336d1fddc964e40dc97bc99caaa6c` | `b9faa7de` | `python3 tools/f6/f6_m1_dedup.py --run v2/evidence/run_f6_{off,on}_n16r60_seed42/run.jsonl`；落盘件 `v2/evidence/f6_m1_dedup_{off,on}.json`（`1c9a9678…` / `041a3eca…`） |

### 版本栏

| 版本 | 时间 | 内容 | 报告 sha |
|---|---|---|---|
| v0-skeleton | 2026-10-21 12:47 | 骨架：§1/§2/§3 定义/§4 命令/§5 局限/§6 对比口径 已写实；读数留中等价占位（花括号空位） | — |
| v1-off-filled | 2026-10-21 14:45 | 本版：尺寸订正 n16×60（§6.1 次序 4）；补 §0.2 分母纪律/证据分级；回填 OFF 臂全部读数、验真原文、4 张真拍截图、抽样本与质地判读；新增 §6.3 成本对比；MDE 与「不可判定」措辞按预注册写死；证据索引扩到 E-21（ON 行留占位）；M-1′ 三档分层（1/33 主口径，2/33 与 3/33 降为敏感性/上界）；§3.6 阈值理由写入判据定义并声明改组须预注册；新增附录 D 占位符逐条说明 | 未提交（ON 门禁） |
| v2 | 2026-10-21 16:20（ON 臂收口） | 回填 ON 臂全部读数（批身份/验真原文/官方指标/M 家族/成本）+ 新增 §3.6b ON 抽样本与质地对比 + §5.2「C-实际」与「D 新观察」 + §5.4 缺口 + 附录 D 重扫归零 + 证据索引补 E-19b/E-22；三查终态入库 `f6_single_variable_checks.txt`（`aa9f9f7e…`） | **未获取到（原因：本文件尚未 commit；sha 由 delivery-gatekeeper 提交后以 `git log -1 --format=%H -- reports/R11-f6-memory-into-dialogue.md` 取得）** |
