# R12 · L-7「套路化」代价治理：记忆注入的去重与反照抄（第三臂 DEQUP）

> 性质：**骨架先写、读数后填**（凡数字一律留 `{ }` 占位；读数到手只填空，不改表头与口径）。
> 报告日期：2026-10-21 ｜ 团队轮次：ROUND-1 ｜ 维度：L-7（单一维度，不扩散）
> 代码 sha（本轮实现，跑批用树）：`263a4300692d2ef3136c8a50e9bade2f99608945`
> 分支：`feat/life-l7-dedup-1021`（从 `origin/master=44c28d5` 切出）
> 本文件 commit sha：`f899fe7ebbfa924033452a7456624d09b086850b`（报告内容首版提交；本次回填见锚点行）
> 锚点行：`git log --format=%H -- reports/R12-l7-dequp.md`

---

## 0. 摘要 TL;DR

**一句话**：本轮把 R11 留下的代价（L-7 从 `181/510=0.354902` 恶化到 `332/510=0.65098`）做成一个
**单 env 开关、默认关闭、可回滚**的第三臂干预（`LIFE_PROMPT_MEMORY_F6_DEQUP`），在**与 R11 ON 臂完全相同**
的 config/seed/规模（n16×60 seed42、`LIFE_PROMPT_MEMORY_F6=1`）之上只多加这一个开关，读数：
`L-7 = 193/510 = 0.378431`、`F-6 = 42/510 = 0.082353`、`calls = 2966`、`degraded = 0`
（来源：回执 §2 / §2b / §5，`v2/evidence/l7_arm_compare.json`、`v2/evidence/l7_f6_guard_check.json`、
`v2/evidence/l7_llmcost_dequp.json`）。

**三臂定位（措辞只按这张表说，禁止外推）**：

| 臂 | L-7 计数 / 率 | 相对 OFF 基线 | 相对 R11 ON 臂 |
|---|---|---|---|
| OFF 基线（`run_f6_off_n16r60_seed42`） | `181/510 = 0.354902` | — | — |
| R11 ON 臂（`run_f6_on_n16r60_seed42`） | `332/510 = 0.65098` | `+151 条 / +29.6078pp` | — |
| **本轮 DEQUP 臂** | **`193/510 = 0.378431`** | **`+12 条 / +2.3529pp`** | **`−139 条 / −27.2549pp`** |

⇒ 结论口径：**L-7 相对 R11 ON 臂明显回落（−139 条 / −27.2549pp），但未回到 OFF 基线
（仍高 12 条 / +2.3529pp）**。因此本轮**不写**「L-7 已改善 / 已修复 / 套路化已解决」——预注册判据
（§3）明确跨批无 CI、不作显著性判定；这里是「方向性回落 + 未回收干净」两句话并列。

> **判读纪律（跑批前写死，非事后找补）**：跨批对比（R11 ON 臂 vs 本轮 DEQUP 臂）同 seed、同 config、
> 不同时间窗，**L-7 无置信区间，不做显著性判定**；只允许写「方向」+ 并列 F-6 守卫，**禁止写「改善」**。
> 若 F-6 相对 R11 ON 臂下降超过 5pp（`57/510=0.111765` 的预注册守卫），即便 L-7 下降也判「以记忆为代价换措辞，不构成净改善」。

---

## 1. 本轮维度与为什么选它（单一维度）

### 1.1 缺口是可复算的（零跑批锚点，先做再花钱）

命令（只读两个已入库日志，零 LLM、零批次）：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 tools/l7/l7_baseline_recount.py \
  --on  v2/evidence/run_f6_on_n16r60_seed42/run.jsonl \
  --off v2/evidence/run_f6_off_n16r60_seed42/run.jsonl \
  --out v2/evidence/l7_baseline_recount.json
```

期望（R11 报告给出的对照值）↔ 实测：

| 量 | R11 报告 | 本轮独立复算 | 一致 |
|---|---|---|---|
| ON 臂带 `ctx.memory_refs` 的消息数 | 412 | **412** | ✅ |
| ON 臂记忆引用总数 | 824 | **824** | ✅ |
| 去重后唯一 `mem_id` | 128 | **128** | ✅ |
| 每条唯一记忆平均被引用 | 6.4 | **6.4375** | ✅ |
| ON 臂 L-7 近重复消息数 / 率 | 332 / 0.65098 | **332 / 0.65098** | ✅ |
| 其中带 `memory_refs` 的条数 | 315 | **315** | ✅ |
| OFF 臂 L-7 近重复消息数 / 率 | 181 / 0.354902 | **181 / 0.354902** | ✅ |
| OFF 臂带 `memory_refs` 的条数 | 0 | **0** | ✅ |

> 口径：8-gram shingle 任一与他人重合即记 dup，`normalize_body` 直接取自
> `tools/d5/dialogue_metrics.py`（本脚本 `import` 官方函数，不另立口径）。

### 1.2 为什么这算「生活气息」

居民反复说同一句话（尤其把别人的话照搬一遍）是「机械 NPC」最直观的表征。R11 已证明记忆注入把
「想起前一天的事」（F-6）拉起来的同时把「套路化」（L-7）拉爆；本轮不问「要不要记忆」，只问
**「记忆能不能不变成复读」**。

### 1.3 本轮不做什么（边界）

- 不改检索权重、不改 `score_and_rank`、不 touch / 不改 `access_count`；
- 不碰世界态、不新增事件类型、不改 `state_hash`、不动 `config/`；
- 不做 F-3 情绪呼应（另一 prompt 装配面）、不做节律/天气（新机制），避免多维度扩散。

---

## 2. 机制事实（实现，`263a4300`）

新增 `code/life/anti_repeat.py`（默认 OFF），三件**有界**的事：

| # | 机制 | 位置 | 有界性 |
|---|---|---|---|
| ① | 记忆注入加权：同一 `mem_id` 本批内被反复注入后降权 | `agent.py::_memory_line` 排序键加 `AR.mem_usage(mid)` | 只改排序，候选集合不变；不改检索与记忆 |
| ② | 反照抄提示：最近 3 条已出口台词进提示词 | `AR.prompt_line()` → `_dialogue_prompt` / `_reply_prompt` | 零额外 LLM 调用；长度上限 3×50 字 |
| ③ | 8-gram 撞车**一次性**重生成 | `agent.py::_dequp_body`（`_send_reply` / `_initiate` 两处接线） | 每条消息最多 +1 次 `purpose="dialogue"` 调用，不级联 |

审计字段（additive，**仅 ON 时出现**）：`payload.ctx.dequp = {v, retries, collisions, messages, mem_used, top_mem}`。

单变量自证（单测 A）：`ON 提示词 == OFF 提示词 + 恰好一处插入`（`d_on.replace(seg,"",1)==d_off`）。

OFF 零扰动的三重保证：
1. `AR.enabled()` False ⇒ `prompt_line()` 空串、`collide()` None、`remember()` 不记账；
2. `_dequp_body` 直接返回原文，**零额外调用**（单测 `test_off_means_zero_extra_calls`）；
3. `ctx.dequp` 不产生（OFF 臂 payload 与接入前一致）。

---

## 3. 预注册判据（跑批前写死）

| 项 | 定义 |
|---|---|
| 干预臂 | n16×60 seed42，`LIFE_PROMPT_MEMORY_F6=1` + `LIFE_PROMPT_MEMORY_F6_DEQUP=1` |
| 对照臂 | R11 已入库 `run_f6_on_n16r60_seed42`（同 config/seed/规模，`DEQUP` 未开） |
| 主口径 | `L-7_dup_ngram8_rate`（den = 全部 MSG，官方脚本） |
| 守卫 | `F-6`（不得低于 R11 ON 臂 −5pp）、`L-6`/`L-5`（不得恶化 >5pp）、`L-8`/`L-13`（必须保持 0） |
| 判定 | L-7 下降且 F-6 不破守卫 ⇒ 写「方向性下降（无 CI，不作显著性判定）」；否则写「未见净改善」 |
| 分母纪律 | den ≥68 才可报率；den <68 只报事件数（沿用 R11 §0.2） |
| 禁止措辞 | 「显著改善」「生活气息变好了」等（跨批无 CI） |

---

## 4. 证据链

### 4.1 批身份与完整性

| 项 | 本轮 DEQUP 臂 | 对照（R11 ON 臂） |
|---|---|---|
| run 目录 | `v2/evidence/run_f6_dequp_n16r60_seed42/` | `v2/evidence/run_f6_on_n16r60_seed42/` |
| `code_sha`（meta） | `263a4300692d2ef3136c8a50e9bade2f99608945` | `895b9a381cd5a1838c23bd3b38e139f7edade3b8` |
| 规模 / seed | n=16、rounds=60、seed=42 | 同 |
| `run.jsonl` 行数 / bytes / sha256 | 116385 / 55,404,972 B / `6bf3ec88…`（`6bf3ec88700fa1a7451b18c63678d0904c69b9de39896739190e7e674db8fdbd`） | 116261 / 55,235,141 B / `7de6a7be…` |
| `meta.events` ↔ `wc -l` | 116385 ↔ 116385（一致） | 一致 |
| 起止 / 耗时 | 18:08:42→19:47:54（5952 s；host.log 记录引擎内部 `seconds=5939.4797`） | 14:05:57→15:53:13（6436 s） |
| side-root | `/tmp/f6_dequp60_side`（`host.log` 里的命令行原文；`meta.side_root` 为 `null`，脚本注明命令行声明值不写回） | `/tmp/f6_on60_side` |

> 完整性断言（`meta.assertions`）：`msg_uid_unique=true`、`ptr_dangling=0`、`ptr_cross_thread=0`、
> `turn_index_dense=true`、`participants_violations=0`；`fallback_detected=false`、`degraded_calls=0`。
> 回执 §1 给出全部原文。

### 4.2 真 LLM 验真（`obs llm-cost` 原文入库）

```bash
cd <REPO>/code && python3 -m obs llm-cost --log ../v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl \
    --require-provider openai_compat; echo rc=$?
```

输出（`rc=0`；原文已入库 `v2/evidence/l7_llmcost_dequp.txt`（sha256 `b59772c7…`）/ `.json`（sha256 `b37adc2f…`），
本节下面是该文件的原文，回执 §5 给出捕获命令）：

```json
{"engine_log":{"by_provider":{"openai_compat":2966},"by_purpose":{"dialogue":{"cached":0,"calls":598,"degraded":0,"thinking":0,"tokens_in":236082,"tokens_out":18232},"importance":{"cached":1387,"calls":1523,"degraded":0,"thinking":0,"tokens_in":2312,"tokens_out":35942},"judge":{"cached":0,"calls":668,"degraded":0,"thinking":668,"tokens_in":88382,"tokens_out":205158},"negotiation":{"cached":34,"calls":49,"degraded":0,"thinking":0,"tokens_in":1787,"tokens_out":531},"plan":{"cached":0,"calls":16,"degraded":0,"thinking":0,"tokens_in":1447,"tokens_out":978},"reflect":{"cached":4,"calls":112,"degraded":0,"thinking":0,"tokens_in":46054,"tokens_out":7715}},"llm_judgment_by_dimension":{"affection":132,"rel_affinity":32,"rel_familiarity":222,"rel_trust":2,"respect":132,"stance":132,"weekly_focus":16},"source":"engine_log(LLM_CALL)","total":{"cached":1425,"calls":2966,"degraded":0,"thinking":668,"tokens_in":376064,"tokens_out":268556,"tokens_total":644620}},"provider_guard":{"by_provider":{"openai_compat":2966},"expected":"openai_compat","ok":true,"policy":"计划用真 LLM 时必须显式校验 provider 计数 > 0 且无 mock 混入。","problems":[]}}
```

判读：`provider_guard.ok = true`、`problems = []`、`by_provider = {openai_compat: 2966}`、
`total.degraded = 0`、`rc = 0` ⇒ **本臂是真 LLM 跑出来的，无 mock/桩混入**。
（注：`dialogue.cached = 0`，而对照 ON 臂 `dialogue.cached = 52`——去重臂每轮提示词都带「最近 3 条已出口台词」，
提示词逐轮变化导致 dialogue 段几乎拿不到 freeze 缓存；这是 §4.6 token 增量的成因之一，如实并列。）

### 4.3 干预生效面（计数型，只证"开关端到端能翻"，不证"用上了"）

- `ctx.dequp` 出现条数 **510**（= 全部 MSG 510，逐条带审计字段）；累计 `retries` **88**；`collisions` **88**；
  `mem_used = 816`、`messages = 510`、`v = "l7-dequp/1"`（来源：`v2/evidence/l7_arm_compare.json` → `dequp_arm.dequp_last`，回执 §2）。
- 额外 `purpose="dialogue"` 调用数 = 总 dialogue calls 598 − 510 = **88**，与 `retries = 88` **逐值相等**
  ⇒ 额外调用**全部**来自机制③（重试），①②为 0（回执 §2b 末行为 `True`）。
- 记忆引用集中度：**412 条带 `memory_refs` / 824 次引用 / 816 个唯一 `mem_id` / 均值 1.0098 次每唯一记忆 / 最高 2 次**；
  对照 R11 ON 臂为 **412 / 824 / 128 / 6.4375 / 最高 8 次**（同口径 `tools/l7/l7_arm_compare.py`，回执 §2 / §2b）。
  ⇒ ①②确实生效：同一 `mem_id` 被反复注入的集中度从 6.4375 压到 1.0098（唯一记忆数 128 → 816）。
  这是**机制生效面事实**，不等于「对话更好」。

### 4.4 截图（本轮真拍，禁止复用 `r11_shots/`）

```bash
cd code && python frontend/tools/gen_threads.py --log ../v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl \
    --meta ../v2/evidence/run_f6_dequp_n16r60_seed42/meta.json \
    --out frontend/sample/dialogue_run_f6_dequp_n16r60_seed42/threads.json --require-complete \
    --label run_f6_dequp_n16r60_seed42-<sha8>
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 \
    sample/dialogue_run_f6_dequp_n16r60_seed42/threads.json "" "" ../v2/evidence/l7_shots
```

产物（**4 张真拍**，落 `v2/evidence/l7_shots/`；来源 run 目录统一为 `v2/evidence/run_f6_dequp_n16r60_seed42/`，
`run.jsonl` sha256 = `6bf3ec88700fa1a7451b18c63678d0904c69b9de39896739190e7e674db8fdbd`；

渲染命令原文（两段，均在 `code/` 下执行）：

```bash
python3 frontend/tools/gen_threads.py --log ../v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl \
    --meta ../v2/evidence/run_f6_dequp_n16r60_seed42/meta.json \
    --out frontend/sample/dialogue_run_f6_dequp_n16r60_seed42/threads.json --require-complete \
    --label run_f6_dequp_n16r60_seed42-6bf3ec88
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 \
    sample/dialogue_run_f6_dequp_n16r60_seed42/threads.json "" "" ../v2/evidence/l7_shots
```

渲染日志：`v2/evidence/l7_shots/render.log`（sha256 `c8ced752287b62eeea9d0ec0b40b64d89e8a9e72a620e80a4d101c72d26e70d4`）。
`threads.json`：`code/frontend/sample/dialogue_run_f6_dequp_n16r60_seed42/threads.json`（2,213,637 B，
sha256 `0720bd050c51b19ced65ba304c847ce1e26d91510ae3884002e392b308b08043`），其中
`source.run_label = run_f6_dequp_n16r60_seed42-6bf3ec88`、`source.run_sha256` 与上表一致，
`stats = {messages:510, threads:169, multi_turn_threads:88, threads_ge3_turns:77, legacy_threads:0, ...}`。

| # | 文件（`<batch_id>-<视图>-<sha8>.png`） | 视图 / 视口 | 尺寸 B | sha256 | 生成时刻 |
|---|---|---|---|---|---|
| 1 | `v2/evidence/l7_shots/run_f6_dequp_n16r60_seed42-chat-6bf3ec88.png` | 对话流 chat 1400×900 | 261,319 | `a82aa3102b61f63dad259c131d2ede856567ce09dfe2039584b0e0795ed4c926` | 2026-10-21 20:07:54 |
| 2 | `v2/evidence/l7_shots/run_f6_dequp_n16r60_seed42-rhythm-6bf3ec88.png` | 节律·串门 rhythm 1300×1050 | 284,620 | `2b0d74a84cfac385e88a70f6bdb52da322ca274fc98d848d4df4602bb8af367c` | 2026-10-21 20:07:56 |
| 3 | `v2/evidence/l7_shots/run_f6_dequp_n16r60_seed42-spread-6bf3ec88.png` | 闲话传播 spread 1300×900 | 177,519 | `90f762ca29eb7cea2aa543581e223bc41162961aea5c1f7111452fe2a39ae72d` | 2026-10-21 20:07:57 |
| 4 | `v2/evidence/l7_shots/run_f6_dequp_n16r60_seed42-600-6bf3ec88.png` | 600px 判读 600×900 | 183,326 | `cd74484a80e5604da53295eabdd945ae0f12a80eae9b9e3fadf7596370692867` | 2026-10-21 20:07:59 |

`blank_retries=0/2` 的含义（四张图逐张都是 `0/2`）：`frontend/tools/shot.py` 出图后会检查
「近全黑 / 无内容」，判为空白则最多重试 2 次并记 `blank_retries=2/2`；本批四张**首帧即有内容、零重试**
（`mean_brightness` 33.5 / 32.5 / 23.2 / 38.5，`max_color_frac` 30.33% / 34.45% / 71.20% / 35.53%），
另 `blank_cumulative=7/160` 是脚本全局观察哨的累计计数（含历史轮次，不属本批）。
页面自证：chat 图内标签 `数据源 run_f6_dequp_n16r60_seed42-6bf3ec88`、`sha 6bf3ec88700f`、
`事件 116385`、`消息 510`、`线程 169 · 多轮 88`，与 §4.1 逐项一致。

### 4.6 预算增量与归因（必须正面回答：L-7 下降是「更会说话」还是「多问了一遍」？）

机制③会**额外消耗 LLM 调用**，因此本臂的总 calls 可能 > 2878（R11 ON 臂）。必须逐项披露：

| 项 | 本轮 DEQUP 臂 | R11 ON 臂 | 增量 |
|---|---|---|---|
| 撞车重生成触发次数（`ctx.dequp.retries` 末值） | **88**（`collisions` 亦 88） | 0（无此机制） | **+88** |
| 重生成 / 总消息（510）比例 | **88/510 = 17.2549%** | 0 | — |
| `purpose="dialogue"` calls | **598** | 510 | **+88** |
| 总 calls | **2966** | 2878 | **+88** |
| `tokens_in` / `tokens_out` / `tokens_total` | **376064 / 268556 / 644620** | 271717 / 269123 / 540840 | **+104347 / −567 / +103780** |
| `dialogue` 段 tokens_in / out / cached | **236082 / 18232 / 0** | 130924 / 16057 / 52 | +105158 / +2175 / −52 |
| 花费（若 obs 给出） | **未生成**（`obs llm-cost` 只出 calls/tokens/cached/degraded，不产出计价字段，本仓库无单价表） | 未生成（同因） | — |

**88 次差额单独归因（正面回答「L-7 下降是更会说话还是多问了一遍」）**：
`dialogue calls 598 − 510 条消息 = 88`，与 `ctx.dequp.retries = 88`、`collisions = 88` **逐值相等**
（回执 §2b 末行判定 `True`）；`messages = 510` 说明**没有因重试而少发给谁的消息**，修正项为 0。
⇒ **本臂多出的 88 次 dialogue 调用 100% 是机制③的撞车重生成成本，①②零额外调用**
（`grep -n 'llm.call\|LLM_CALL' code/life/anti_repeat.py` → `rc=1`，零命中，回执 §8）。
`tokens_in` 多出 104,347 的原因有两项、都已计量：①88 次重试（`dialogue_tokens_in` +105,158）；
②`dialogue.cached` 从 52 掉到 0（提示词逐轮带最近 3 条台词，缓存命中消失）。`tokens_out` 反而 −567，属生成侧波动，不解释为质量。

**判定（按 §4.6 预注册口径执行，未软化）**：重生成率 **17.2549% ≥ 5%** ⇒ 触发「不得把多花一次调用包装成
对话质量改善」的条款，因此本轮**声明「无法分离③的贡献，只报 L-7 方向」** ——
即 `193/510` 这个读数里，①②（注入加权 + 反照抄提示）与③（撞车重生成）的贡献**在本轮实验设计下不可分离**，
因为臂是三者同时打开的。

**生活气息层面的定性事实（只记录，不升级为结论）**：`retries = 88`、`collisions = 88`、`messages = 510`
三个实测值 ⇒ 约 **每 5.8 条消息就有 1 条（17.2549%）是因为 8-gram 撞车被重写一次**。
这说明该机制是**「先撞后重试」的被动去重**，而非生成前规避。这是可复算的行为事实；
是否要改成生成前规避（如更强的前置约束）属**下一轮**决策，本轮不据此下「需要改机制」的结论。

**①②零额外调用的自证**（代码 + 计数双证）：
- 代码：`AR.prompt_line()` 只返回字符串；`_memory_line` 只改排序键；`grep -n 'llm.call\|LLM_CALL' code/life/anti_repeat.py`
  → `rc=1`（0 命中，回执 §8 原文）。
- 计数：`retries 88 == dialogue_calls 598 − 510 − 0` ⇒ `True`；即额外 dialogue 调用**全部**来自机制③，①②为 0。

### 4.5 读数表（官方脚本）

来源：`tools/d5/dialogue_metrics.py`（唯一口径）。DEQUP 臂输出 `v2/evidence/l7_metrics_dequp_d5.json`
（sha256 `a06ed524760f7bfe…`）/ `.md`；对照两臂沿用 R11 已入库的 `v2/evidence/r1_f6_on_metrics.json`
（sha256 `abe4977d8ecb6dc4…`）与 `v2/evidence/r1_f6_off_metrics.json`（sha256 `cb757208249dd9fc…`）。
复算命令见回执 §3，回执同一节给出三臂同表读数。

| 指标 | OFF 基线 | R11 ON 臂 | **本轮 DEQUP** | DEQUP−ON | 守卫 / 判定（预注册 §3） | band_source |
|---|---|---|---|---|---|---|
| **L-7 8-gram 近重复率**（主口径） | 0.354902（181/510） | 0.65098（332/510） | **0.378431（193/510）** | **−27.2549pp（−139 条）** | 跨批无 CI ⇒ 只写「方向性回落」，**禁写改善** | 无可用带（跨批不同时间窗） |
| **F-6 跨天记忆引用率** | 0.037255 | 0.111765（57/510） | **0.082353（42/510）** | **−2.9412pp** | 守卫：不得低于 ON−5pp ⇒ **未破守卫**（2.94 < 5）；且仍高于 OFF 基线 +4.5098pp | 无可用带；交叉核对 Wilson95 [0.0615,0.1094] vs [0.0873,0.1421]，区间重叠 ⇒ 不判显著 |
| L-6 精确重复率 | 0.101961 | 0.127451 | **0.003922**（2/510） | −12.3529pp | 守卫：不得恶化 >5pp ⇒ 通过 | 无可用带 |
| L-5 模板套话率 | 0.011765 | 0.015686 | **0.001961**（1/510） | −1.3725pp | 守卫：不得恶化 >5pp ⇒ 通过 | 无可用带 |
| L-8 裸 ID 泄漏率 | 0.0 | 0.0 | **0.0** | 0 | 守卫：必须保持 0 ⇒ **通过** | 精确二项上界 rule-of-three（3/510 ≈ 0.588% 上界） |
| L-11 二人称率（DM+群） | 0.665934 | 0.650549 | **0.698901** | +4.8352pp | 非守卫项，仅登记 | — |
| L-10 分母 | 407 | 483 | **471** | −12 | 仅登记 | — |
| L-13 token 泄漏条数 | 2 | 14 | **9** | −5 | 守卫原定「必须保持 0」⇒ **未达成**；但**两臂同源**（OFF 2 / ON 14 / DEQUP 9 均 > 0），非本臂引入，如实登记为既存缺陷 | — |

> **L-13 说明（不粉饰）**：预注册写的是「L-8/L-13 必须保持 0」。实测三臂 L-13 分别为 2 / 14 / 9，
> **没有一臂为 0**，即该守卫在 R11 阶段就已经不成立（token 泄漏源自 `ctx.topic` 原字符串进正文）。
> 本轮只登记事实与计数差（DEQUP 比 ON 少 5 条），**不作「已修复」表述**，也不拿它抵扣 L-7。
>
> **分母纪律**：den = 510 ≥ 68 ⇒ 可报率（沿用 R11 §0.2）；L-13 报事件数不报率。

---

## 5. 纪律自查（逐条带证据）

| # | 纪律 | 证据 |
|---|---|---|
| 1 | 起跑前串行确认 | **本批起跑非本轮执行**（`started_at 18:08:42`，由前序轮次起跑），`host.log` 不记录起跑前的 `pgrep`，故「起跑前串行确认」**本轮未确认**（不编造）。本轮**我自己**的复算前串行确认有据：回执 §0 `pgrep -af "[o]rchestration run"` → `rc=1`、`pgrep -af "[r]un_batch.sh"` → `rc=1` |
| 2 | 跑批期间未改禁改目录 | `meta.assertions.code_unchanged_during_run = null`（**未捕获**，meta 为 run 后生成，起始快照 `git_status_start=null`），故该字段**不可作为通过证据**；替代硬证据三条：① `code_sha == code_sha_end == 263a4300692d2ef3136c8a50e9bade2f99608945`；② `meta.git_dirty_code_files` 仅 `?? code/frontend/sample/dialogue_run_g1_b0_n16r60_seed42/`（前端样本，非 `code/life|orchestration|config|engine`）；③ 本轮 `git diff --stat 263a430 -- code/life code/orchestration code/config code/engine` **无输出**（回执 §7） |
| 3 | 无长 sleep 轮询；后台 setsid | **未确认**：`host.log` 记录的是引擎内 `seconds=5939.4797` 与命令行原文，不含 `setsid` pid 与轮询间隔；本批非我起跑，pid/间隔无据可查，如实写「未生成」 |
| 4 | 真 LLM 验真 | §4.2：`provider_guard.ok=true`、`by_provider={openai_compat:2966}`、`degraded=0`、`rc=0` |
| 5 | 截图本轮产生 | §4.4：四张 PNG `mtime = 2026-10-21 20:07:54–20:07:59`，**晚于跑批结束 19:47:54**；`render.log` sha256 `c8ced752…`；文件名 `<batch_id>-<视图>-<sha8>.png` 与本臂 `run_sha256` 前缀 `6bf3ec88` 逐张自校验通过 |
| 6 | 结论绑定 sha | §0 + §4.1：数据 = `code_sha 263a4300`、`run.jsonl 6bf3ec88…`；本报告 commit sha 见文首 |
| 7 | 维度单一 | 回执 §8：`263a430` 只动 `code/life/agent.py`(+36/−6)、`code/life/anti_repeat.py`(+146)、`code/tests/test_anti_repeat.py`(+162)、 `tools/l7/l7_baseline_recount.py`(+110)、`v2/evidence/l7_baseline_recount.json`(+103)，全部围绕 L-7 |

## 6. 本轮新增路径清单（显式不认领历史遗留）

新增（`263a430` 已入库）：`code/life/anti_repeat.py`、`code/tests/test_anti_repeat.py`、`tools/l7/l7_baseline_recount.py`、
`v2/evidence/l7_baseline_recount.json`。本轮收口新增：`v2/evidence/run_f6_dequp_n16r60_seed42/`（run.jsonl + meta.json + host.log）、
`v2/evidence/l7_arm_compare.json`、`v2/evidence/l7_metrics_dequp_d5.json` / `.md`、`v2/evidence/l7_f6_guard_check.json`、
`v2/evidence/l7_llmcost_dequp.json` / `.txt`、`v2/evidence/l7_shots/`（4 张 PNG + `render.log`）、
`v2/evidence/l7_recompute_receipt.md`、`tools/l7/l7_arm_compare.py`、`tools/l7/l7_receipt.sh`、
`code/frontend/sample/dialogue_run_f6_dequp_n16r60_seed42/threads.json`、本报告。

**不认领**：`git status` 里历史未跟踪产物（`v2/evidence/d4_*` 15 项、`v2/evidence/run_g1_*`、`v2/evidence/run_dr_*`、
`v2/evidence/r1_llmcost_off.*`、`v2/evidence/g1_launch_evidence_b0.txt`、
`code/frontend/sample/dialogue_run_g1_b0_n16r60_seed42/` 等），非本轮产生，本轮**不入库**。

## 7. 下一步建议

1. **先做「③关掉」的分离臂，再谈 L-7 是不是①②的功劳**：本轮三者同时打开，`88/510=17.2549%` 的重试成本
   与①②的收益无法分离（§4.6 已降级声明）。下一轮只需把 `LIFE_PROMPT_MEMORY_F6_DEQUP` 拆成
   `DEQUP_RANK`（只①，零额外调用）+ `DEQUP_RETRY`（只③）两个子开关，跑一臂只开①，即可把
   「排序加权」的净效果从「重写一次」的成本里剥出来；这是唯一能把结论从「方向」推到「归因」的路径。
2. **残余 12 条差距要定向看，不要靠调参撞**：DEQUP 仍高 OFF 基线 12 条（+2.3529pp），需人工抽读这 12 条
   近重复对（`l7_arm_compare.json` 的 `top_mem_ids` 与 `dup` 明细可定位），判断是「记忆确实让两人说了同一件事」
   （可接受）还是「模板句式残留」（不可接受）；两者处置完全不同。
3. **被动去重的机制形态待定**：`retries=88` 说明当前是「先撞后重试」。若下一轮把撞车检查前移到生成前约束
   （提示词侧显式排除最近 N 条 8-gram 片段），同样的 L-7 读数将不再花 88 次额外调用；但那属机制改造，
   须在无跑批窗口开分支做，且要用单测锁「OFF 零扰动」不变。
4. **L-13 是既存缺陷，需要单独一轮**：`ctx.topic` 原字符串进正文在三臂都存在（2/14/9），与 L-7 无关，
   建议作为独立维度立项（提示词侧把 token 人话化），不要并进 L-7 的收口。
