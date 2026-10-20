# R8 · 对话往来密度：放宽回复窗口（`reply_window_rounds` 2→4）的单臂诊断

> **版本状态：【两臂实测已入库（独立复核 PASS-WITH-CAVEATS）· 结论限于方向性】** 两臂读数已齐：A0 `run_d2_after_n16_seed42`（`643f13a5`，`code_sha 884f4541`）vs D9 `run_d9_a1_n16r84_seed42`（`abefdf73`，`code_sha 05636bc`），同 `n16r84 seed42`，分母均为 **686 消息 / 206 线程**。§2 读数表与 §7 判定表已填，读数与复算命令的唯一引用源为 **`reports/d9-readings.md`**。**6 条 caveat（C-1…C-6）是其硬边界，读本报告须连同 `d9-readings.md` §6 一起读**：C-3（L-7 计数相同属巧合）、C-5（judge 侧四类 purpose 不吃正文）、C-6（两臂 code_sha 隔 11 个 commit，"唯一变量"只限相对 master 的 diff）三条直接决定结论写法。
>
> **版本状态取值规则（定稿时二选一，写在本行）**：
> - **`实测已入库、机制解释待补（未发布）`** —— 读数已齐但 §2.3 机制解释缺项时的状态：**仍要落本地 commit**（不丢已确证证据），但**不 push**，报告不得对外引用为最终结论。
> - **`可发布（待 Leader 授权 push）`** —— 读数与 §2.3 机制解释均齐备时的状态；是否真正 push 由 Leader 向用户申请授权后决定。
>
> ⛔ **"抑制发布" ≠ "不落 commit"**：前者指不 push/不对外引用；后者是保存证据。两者不可互相替代。
> **报告族**：R8｜短名 `dialogue-density`｜可信边界见 **R1 §3 / §2.5**，生活气息维度定义见 **R4 §1**（本份不复制定义，只引用编号）
> **署名**：AI 小镇 · 对话体验与研究发布小队（JiuwenSwarm 多智能体团队）
> **分层标记**：【事实】／【读数】／【判断】／【未完成】

---

## 0. 臂身份与锚点（先读这节，否则后面每个数字都会用错代码）

### 0.1 两个 sha，用途不同，**不许互相替代**

| 角色 | sha | 说明 |
|---|---|---|
| **master HEAD** | `371772e1dfe6cb078777b6ffcbe20e116791a03e`（`371772e`） | 仓库主干，**仅用于说明"改动相对什么基线"**。**不得**用它当本轮 A1 臂的 `code_sha`。 |
| **本轮变量臂 code_sha（分支 commit）** | `05636bcde2f1759b1bbc8d9eb74f43ec241be6a9`（`05636bc`） | 分支 `feat/dialogue-density` 的**唯一改动提交**，`code/life/dialogue_threads.py` 一行。**D9 批确实在此 commit 上跑完**（`run_d9_a1_n16r84_seed42/meta.json`：`code_sha = code_sha_end = 05636bc…`、`git_dirty_code_files=[]`）。 |
| **A0 臂 code_sha** | `884f4541b80e5343119b51bf94054b2f54dd4559`（`884f4541`，取自 `v2/evidence/run_d2_after_n16_seed42/meta.json::code_sha`）【若本轮重新跑 A0，则以新批 `meta.json.code_sha` 为准并替换本行】 | 基线臂。**该 sha 早于 master HEAD `371772e`**，两者之间存在 `code/` 漂移——但实测**仅限 `code/frontend/`**，行为路径零漂移，故 A0 可作行为基线；证据与命令见 **§3.0**（不得只写"两臂同口径"了事）。 |

### 0.2 本轮唯一变量（`git diff` 语义摘录）

**【事实】** 分支相对 master 的代码改动**只有一行**，且不涉及任何 `code/config/`：

```bash
git diff --stat 371772e..05636bc -- code/        # code/life/dialogue_threads.py | 2 +-
git diff --stat 371772e..05636bc -- code/config/ # 空输出（配置零改动）
```

```diff
--- a/code/life/dialogue_threads.py
+++ b/code/life/dialogue_threads.py
@@ -27,7 +27,7 @@ DEFAULTS = {
     "max_turns": 6,               # 单线程最大轮数（含发起），到顶即封口
     "max_turns_per_round": 2,     # 单线程单回合最多推进轮数（K）
     "max_messages_per_slot": 2,   # 单 agent 单 slot 最多发出的 MSG 条数（发起+回复合计）
-    "reply_window_rounds": 2,     # 入站消息在多少回合内仍可被回（超时即线程结束）
+    "reply_window_rounds": 4,     # 入站消息在多少回合内仍可被回（超时即线程结束）[D9: 2→4 单变量]
     "history_turns": 3,           # 上下文装配只带最近 K 轮（控 token）
     "max_thread_chars": 240,      # 线程历史文本硬上限（控 token）
     "names_enabled": True,        # 邻居显示名注入（false = 回退到 persona_id 裸 ID）
```

### 0.3 生效值证据（"改了"≠"生效"，必须证明运行时真的读到 4）

**【事实】** 采集路径：`code/life/agent.py:788-790` `_dlg_cfg()` → `DT.load_params()["dialogue"]`；`load_params()`（`code/life/dialogue_threads.py:71-95`）先取 `DEFAULTS`，再由 `code/config/life_v2.json` 的 `dialogue` 段覆盖，最后由运行时 `--override life_v2.*` 覆盖。

因此"生效值 = 4"需要三件事同时成立：

| # | 断言 | 采集命令 | 结果 |
|---|---|---|---|
| L1 | 该臂代码里默认值是 4 | `grep -n "reply_window_rounds" code/life/dialogue_threads.py`（A1 臂分支） | `30:    "reply_window_rounds": 4,` |
| L2 | 配置文件**没有**覆盖该项 | `python3 -c "import json;print(list(json.load(open('code/config/life_v2.json')).keys()))"` | `['_comment','schema_version','sleep','forgetting','persona_drift']` ⇒ **无 `dialogue` 段**，覆盖不成立 |
| L3 | 跑批**没有**用 `--override` 改回 2 | D9 臂 `meta.json` 与 `run_d9_a1_n16r84_seed42/host.log` 首行命令行（`python3 -m orchestration run --life --seed 42 --agents 16 --rounds 84 --out /tmp/d9_a1_run/run.jsonl --flush-every 2 --side-root /tmp/d9_a1_side`，**无 `--override`**）；且两臂 `WORLD_INIT.config_components` 12 项逐项 sha256 相同（digest `b4421cfc053d6fb6`） | ✅ 成立（`config_components` 对拍命令见 `d9-readings.md` §4.1） |

> **C-1 提醒**：`host.log` 是**作者保存的 stdout 摘录**，`/tmp` 原件里并没有这个文件，故它不能作为独立可对拍的原始产物；L3 的硬证据是 `meta.json` 的字段组合 + `config_components` 逐项相同。

补充硬证据：A0 臂 `WORLD_INIT.config_components` 记有 `life_v2.json` 的 sha256（`v2/evidence/run_d2_after_n16_seed42/run.jsonl` 首行）。若 A1 臂同一字段的 `life_v2.json` sha256 与 A0 **完全相同**，则"配置零改动"获得运行侧双证（代码 diff + 运行期配置指纹一致）。

**【判断】** 只有 L1+L2+L3 全成立，才可以写"本轮 A1 行为变化的唯一上游差异是 `reply_window_rounds`"。任一条缺，本报告的归因强度降为「方向性观察」。

---

## 1. 摘要

> **预登记结论句式（数据到手后按此填写，不得换成模糊表述）**。本节允许的两种写法已经先写死，执行时只做「选哪一支 + 填分母」，不允许临时造新句式：
> - **若两臂在关键指标上逐项相同**（`batch` 级同回合结构一致、线程/消息读数无差）⇒ 必须明确写出一句等价表述（措辞已按 §2.3 的代码级机制定稿）：
>   「**在本配置（感知窗 `VISIBLE_WINDOW_ROUNDS=2`）下，`reply_window_rounds` 是 dead parameter，2→4 不产生可观测差异**」，并**紧随其后**写「真正的约束候选是 `max_messages_per_slot=2`（A0：381 个 `(agent,day,slot)` 单位中 305 个顶格 = 80.05%）与 `max_turns=6`（206 线程中 68 条跑满 = 33.0%）」。
>   ⚠️ 不得把它写成「窗口从未被用满」——该推测已被 `agent.py:871-872` 外层截断的**恒等式性质**证伪（详见 §2.3 纠错留痕）。
> - **若两臂存在差异** ⇒ 按 §3.2 判定三件套逐条给：`|Δ|` / 同分母噪声带上界 / 分母条数；分母不足或带缺失时写「本规模下无法判定」，不得写效果层结论。
> - **两支都不得**出现「放宽窗口无效 / 失败 / 没做成」这类把负结果写成失败的措辞：负结果是结论，不是事故（区别见 §3.2「无差异 ≠ 不显著」）。

**【摘要 · 事实层】** 在本配置（外层感知窗 `VISIBLE_WINDOW_ROUNDS=2`）下，**`reply_window_rounds` 2→4 是 dead parameter：2→4 不产生可观测的结构差异**。依据是 §2.2 的十项结构读数在两臂**逐项相同**（686 消息 / 206 线程 / slot 顶格 305 of 381 / ≥3 轮 89 / ≥6 轮 68 / 延迟 327-153-480 / ≥3 回合 0 等），而这是**存在性事实**（同 seed、同 `engine_version`、同 12 项配置指纹下的确定性调度），不是"差异不显著"。

真正的约束候选是 **`max_messages_per_slot=2`**（A0：381 个 `(agent,day,slot)` 单位中 **305 个顶格 = 80.05%**、**≥3 条 0 个**）与 **`max_turns=6`**（206 条线程中 **68 条跑满 = 33.01%**）。

**【摘要 · 措辞层】** 结构相同不代表正文相同：两臂正文**仅 35/686 同位相同**（唯一正文交集 34 条）。措辞层出现**小幅、方向性**变化：L-2 0.8192→0.810496（−0.87 pp，562→556 of 686）、L-3 0.8601→0.846939（−1.31 pp，590→581 of 686）、L-6 0.0991→0.090379，而 **L-5 反向 +0.29 pp（13→15 of 686）**；**L-7 两臂计数相同（335/686）但触发集合不同（jaccard 0.5581）⇒ 属计数巧合**（C-3）。分母均 686，**本轮不判定"改善成立"**，只登记方向。

> 以下写作约束保留（定稿时已逐条遵守，防事后找补）：

- 摘要**只允许**出现两类句子：① 机制接通性事实（例如"入站消息在 4 回合内仍可被回"这一路径是否被走到）；② 读数层描述（附分母与统计单位）。
- 摘要**禁止**出现"提升了生活气息""对话更自然"等效果层宣称——本轮是**单臂改动**（只改 A1，A0 为基线），且关键指标分母规模待核，按全族纪律效果层最多写「本规模下无法判定」。
- 若某组数据未交付，摘要里写「未交付」，**不得**用相邻指标推算补位。

---

## 2. 读数表（A0 vs A1 双列）

### 2.1 主表：F-1…F-7（同口径、同分母对比）

| 编号 | 指标 | 统计单位 | A0 | D9 | 分母（A0 / D9） | \|Δ\| | 噪声带上界 `band_source` | 证据级 | 判定 |
|---|---|---|---|---|---|---|---|---|---|
| F-1 | 非功能性闲聊占比 | per-message | 0.760933 | 0.753644 | 686 / 686（功能性 164 → 169） | 0.007289 | 无可用带（本轮未做同分母 bootstrap） | evidence | **方向性**（不判改善/恶化） |
| F-2 | 话题漂移率 | per-adjacent-pair | **0.0** | **0.0** | 480 / 480 | 0 | 恒 0 ⇒ `rule-of-three(3/n)` | evidence | **无差异（已证实）** |
| F-2b | 多话题线程占比 | per-thread | **0.0** | **0.0** | 206 / 206 | 0 | 恒 0 ⇒ `rule-of-three(3/n)` | evidence | **无差异（已证实）** |
| F-3 | 情绪呼应 | per-adjacent-pair | 0.242991 | 0.190476 | 107 / 105（分子 26 → 20） | 0.052515 | 无可用带 | evidence | **方向性**（分母 ≥68 但缺带） |
| F-4 | 修复闭环 | per-event | 0.076923 | 0.03125 | 39 / 32（分子 3 → 1） | — | 分母 <68 ⇒ `probe` | probe | **本规模下无法判定** |
| F-5 | 习惯强度 | per-agent | **1.0** | **1.0** | 16 / 16 | 0 | 恒 1 ⇒ B2 退化，用精确二项上界 | evidence | **无差异（已证实）** |
| F-6 | 跨天记忆引用率 | per-message | 0.064140 | 0.051020 | 686 / 686 | 0.013120 | 无可用带 | evidence | **方向性** |
| F-7 | 越界编造率（P1 提及层） | per-message（可判定子集） | 0.155977（**旧口径，不可引用**） | 0.158892（同上） | — | — | — | — | **C-5：judge 侧指标，对措辞改造不敏感 ⇒ 不得用于衡量措辞效果** |

### 2.2 本轮重点表：往来密度（本报告的核心）

| # | 指标 | 统计单位 | A0 | D9 | 分母（A0 / D9） | \|Δ\| | 噪声带上界 | 证据级 |
|---|---|---|---|---|---|---|---|---|
| M-1 | F-2b 多话题线程占比 | per-thread | **0.0** | **0.0** | 206 / 206 | 0 | 恒 0 ⇒ `rule-of-three` | evidence |
| M-2 | 线程平均往返轮数 | per-thread（均值） | **3.0049** | **3.0049** | 206 / 206 | 0 | — | evidence（逐项相同） |
| M-3 | 线程消息数分布（含最长线程条数） | per-thread（分布） | `{1:102,2:14,3:6,4:14,6:62,11:1,12:1,13:3,15:2,18:1}`，最长 **18** | 同上，**逐项相同** | 206 / 206 | 0 | 无可用带（分布） | evidence |
| M-4 | 连续往来 ≥3 轮的线程数 | 事件数（per-thread 计数） | **89**（0.432039） | **89**（0.432039） | 206 / 206 | 0 | — | evidence（逐项相同） |
| M-5 | 连续往来 ≥6 轮的线程数 | 事件数（per-thread 计数） | **68**（0.330097） | **68**（0.330097） | 206 / 206 | 0 | — | evidence（逐项相同） |
| M-6 | 多参与者（≥3 发言者）线程数 | 事件数（per-thread 计数） | **9**（0.043689） | **9**（0.043689） | 206 / 206 | 0 | — | evidence（逐项相同） |
| M-7 | 每 slot 实际发消息数分布 | per-(agent,slot) 分布 | `{1:76, 2:305}`；单位 **381**、顶格 **305（80.05%）**、**≥3 = 0** | **逐项相同** | 381 / 381 | 0 | 无可用带（分布） | evidence |

> **M-7 的读法（本轮已由数据落定）**：`max_messages_per_slot = 2`（`code/life/dialogue_threads.py:29`）是每 agent 每 slot 的硬上限；两臂 381 个单位里 **305 个顶格、0 个 ≥3**，而 M-2/M-4/M-5 也逐项不动 ⇒ **往来密度的封顶在 `max_messages_per_slot`，不在 `reply_window_rounds`**。这是本轮的有效发现，不是"放宽窗口无效果"。

> **口径提醒（C-3 / C-5）**：本区所有"逐项相同"都是**结构层**结论；不得推广到措辞层。措辞层的 L-7 计数相同属**巧合**（两臂触发集合 jaccard 0.5581），judge 派生的 F-7 一类指标**不能**用来衡量措辞变化。

> **M-7 为什么是本轮的关键读法**：`max_messages_per_slot = 2`（`code/life/dialogue_threads.py:29`）是**每 agent 每 slot 的硬上限**。若放宽回复窗口后 M-2/M-4/M-5 读数不动、而 M-7 分布右端贴着 2，则说明**新的封顶已经转移**——往来密度被 `max_messages_per_slot` 而不是 `reply_window_rounds` 限制住。**这个判断本身是有效发现**，必须作为结论写出，不得只写"放宽窗口无效果"。

---

### 2.3 机制解释：**双窗叠加——外层感知窗先把候选集截断**

**【事实 · 代码级（本节结论不依赖任何读数，可单独复算）】** 可回复性由**两道窗**共同决定，而本轮只改了内层：

| 层 | 位置（主树 grep 值） | 作用 |
|---|---|---|
| **外层：感知窗（本轮未改动）** | `code/orchestration/integration.py:275` `VISIBLE_WINDOW_ROUNDS = 2`；调用点 `:341` `self.visibility_query(agent_id, r, window_rounds=self.VISIBLE_WINDOW_ROUNDS, …)`；截断实现 `code/contracts/visibility.py:100` `if window_rounds is not None and rec["round"] < upto_round - window_rounds: continue` | round `r` 时，此 agent **根本看不见** `r-2` 及更早的事件 ⇒ 它们**进不了候选集** |
| **内层：回复窗（本轮变量）** | `code/life/agent.py:856` `window = int(cfg.get("reply_window_rounds", 2))`；判定 `:871-872` `if int(wv.round) - int(ev.round) > window: continue  # 超时，线程结束` | 在**已可见**的候选里再筛一次"未超时" |

**【判断 · 本轮的核心机制结论】**
1. 外层窗已把可回复范围限定在 **≤2 回合**内，因此内层的"延迟 ≥3 跳过"分支**永远不可能命中**——`延迟 ≥3 = 0` 是**恒等式**（由两层上界共同决定），**不是**观测证据。把它当证据读会得出"居民都不想晚回"的伪结论。
2. ⇒ `reply_window_rounds` 2→4 在本配置下是 **dead parameter**：放宽一个已经被外层截断的区间，不产生任何可观测差异。**【实测确认】** 两臂（A0 `643f13a5` / D9 `abefdf73`，同 n16r84 seed42）的结构层十项读数**逐项相同**（§2.2 全表），且正文仅 35/686 同位相同 ⇒ 这不是"两臂跑重了"，而是"调度结构由确定性内核决定，只有措辞层受采样影响"。这与 §3.4 记录的「`r0–r21` 两臂逐回合调用结构逐项相同」相互印证——**是"为什么相同"，不是"恰好相同"**。
3. 分支相对 master 未触碰这两层代码的任一处：`git diff --stat 371772e..05636bc -- code/contracts/ code/orchestration/` → **空输出**（唯一改动仍是 `code/life/dialogue_threads.py:30`，见 §0.2）。

**【描述性读数 · 边界正被频繁触及，但再放宽也看不见】** A0 批（`run.jsonl` `643f13a5`）中可解析的 `reply_to` 配对共 **480** 条，延迟分布只有两档：**t+1 = 327（68.1%）**、**t+2 = 153（31.9%）**，**没有任何 ≥t+3 的回复**。
- 读法：31.9% 的回复**恰好卡在本配置能允许的最晚那一回合**，说明"想回但只能等到 t+2"这种情况大量存在——**边界确实被压着用**；
- 但因外层感知窗在 t+3 就看不见了，这批"想更晚回"的消息**根本没有机会变成候选** ⇒ 这与 dead parameter 的结论**不矛盾**：不是"没人想晚回"，而是"晚回的路径被外层窗封死"。两者必须一起写，否则会把 dead parameter 误读成"居民本来就不想晚回"。

**口径旁证（两种配对方式，计数不可互换）**：本节采用 **`payload.reply_to` 指针配对**（分母 = 带 `reply_to` 的 480 条）⇒ `t+1=327 / t+2=153`。另有团队内的**线程相邻法**（同线程内相邻 `turn_index` 的回合差）算得 `269 / 144`。两种口径的**分母与配对定义都不同**（指针配对只覆盖"确实指向某条消息"的回复；线程相邻法覆盖"同线程内先后的两条消息"，会把发起-发起或跨分支的情形也计入），因此**两套计数不得相加、不得互相替换、不得混引**。两者唯一一致的结论是：**延迟 ≥3 的回复为 0**——而这正是 §2.3 判断第 1 条所说的**恒等式**，两种口径都只能确认它，不能把它当独立证据。

**【纠错留痕】** 本节初稿曾推测「窗口从未被用满」（基于"若大多数回复都很快，放宽就没有样本"的推理）。**该推测已被证伪**：真正的机制是上表的**恒等式性质**（外层窗截断候选集），而非样本不足。保留此痕迹，避免下一个人再走同一条错路。

**【与下一轮的接口】** 提高往来密度的真正约束候选不是回复窗，而是：`max_messages_per_slot = 2`（A0 每 `(agent, day, slot)` 单位共 381 个，其中 **305 个顶格 = 80.05%**、**≥3 为 0**）与 `max_turns = 6`（206 条线程中 **68 条已跑满 6 轮 = 33.0%**）。这两项的具体处置属 D10 范畴，本报告只给判据。

---

## 3. 方法与陷阱

### 3.0 前提审计：A0 能不能当行为基线（**读读数前必读，含可复算命令**）

**【事实】** A0 基线臂的 `code_sha = 884f454`（`884f4541b80e5343119b51bf94054b2f54dd4559`，取自 `v2/evidence/run_d2_after_n16_seed42/meta.json::code_sha`）**早于**本轮分支基座 master HEAD `371772e`。两者并非同一 commit，因此"两臂同口径"这句话必须先证明**中间这段代码漂移没有碰到行为路径**，否则 A0/A1 的差异会被记到错误的账上。

**【事实 · 漂移审计（原样输出，读者可自己跑一遍）】**

```bash
cd <repo>
git diff --stat 884f4541b80e5343119b51bf94054b2f54dd4559..371772e -- code/
```

```text
 code/frontend/README.md                            |   3 +-
 code/frontend/dialogue.html                        |   1 +
 .../dialogue_run_d8_armA_n4r60_seed42/threads.json |   1 +
 .../dialogue_run_d8_armB_n4r60_seed42/threads.json |   1 +
 code/frontend/src/dialogue.js                      |  80 ++++++++++++-
 code/frontend/tools/dialogue_compare.py            | 125 +++++++++++++++++++++
 code/frontend/tools/gen_threads.py                 |   3 +
 7 files changed, 209 insertions(+), 5 deletions(-)
```

（上列 7 个条目中，2 个是前端渲染用的 `threads.json` 数据文件，**源码文件 5 个**，全部位于 `code/frontend/`。）

```bash
git diff --stat 884f4541b80e5343119b51bf94054b2f54dd4559..371772e -- \
  code/life/ code/orchestration/ code/config/ code/engine/
# 空输出（rc=0，零命中）
```

**【判断】** **`884f454..371772e` 的 `code/` 差异仅限 frontend，生活层与编排层行为路径零漂移，故 A0 可作为行为基线。**（`code/frontend/` 只影响渲染与截图工具链，不参与模拟行为；这条diff 里连 `code/frontend/tools/` 的改动也是在**截图/对照工具**侧，不是行为侧。）

**【判断 · 这条审计为什么必须贴在正文】** 读者要复核的从来不是"我们说了同口径"，而是"基线是不是真的能用"。把 `git diff --stat` 原样贴出来，任何人 `git clone` 后一行命令就能验证；不贴则退化成一句无法证伪的声明。**同理，本节的结论只对 `code/` 成立**——`v2/evidence/`、`tools/d5/` 的漂移只影响读数脚本版本，需在 §3.1 里逐条绑 sha，不能靠这条审计兜住。

### 3.1 复算命令（逐字，来自 d9-readings.md，不得改写）

**【未完成】** 待 `d9-readings.md` 交付后按原文粘贴，逐条附 stdout 摘要（含分母打印行）。

**【事实 · 已可先行认定的脚本身份（已逐行读过源码）】** 本轮新增的往来密度读数器 `v2/evidence/d9_density.py`：

- **只读**：唯一输入是 `--log <run.jsonl>`，用 `tools/d5/dialogue_metrics.py` 的 `read_run` / `extract_messages` / `group_threads` 解析（**复用 F-2b 同一口径与同一分母**，不另写解析器）；
- **零 LLM、零网络、零业务写**：全文无 `requests`/`openai`/`subprocess`，不 import `code/` 下任何业务模块，不写世界态；只写 `--out-json` / `--out-md` 两个读数产物；
- **无跑批逻辑**：不含 orchestration / 事件注入 / 状态推进代码，退出码仅 0（成功）/ 2（输入不可用）。
- ⇒ 符合"证据可复算性依赖它 ⇒ 入 commit"的条件，**随本轮 commit 一并入库**；其 sha256 见证据索引。

**【事实 · 脚本可用性已复测（三种调用方式，均 rc=0）】** 该脚本在入库前曾有一个**只影响 CLI 汇总段的缺陷**（`t` 只在 `if a.out_md:` 分支内绑定，导致只传 `--out-json` 时 `UnboundLocalError`）。上游已于固定 `t = out["threads"]`（现 `d9_density.py:156`，位于 `if a.out_md:` 之前）修复，**零计算逻辑改动**；本报告作者按同一 A0 日志独立复测三种调用方式：

| 调用 | 退出码 | 产物 sha256 |
|---|---|---|
| 仅 `--out-json` | **0** | json = `260b6725a1950c40c41ff1346ae7af186b8a8e9cd749d76b3e3fc1519de98b5e` |
| 仅 `--out-md` | **0** | md = `7930cab2369efedf8dcbfef38f83a9d6c19d1e77a5310b06951a36bd83a94e4c` |
| 两者同时给 | **0** | json / md 同上（逐字节一致） |

⇒ **修复前后 `--out-json` 产物逐字节相同**（同 sha），故该脚本可直接作为**干净的可复算凭据**入库；当前脚本 sha256 = `78a32e66…`（见 §8 第 10b 行）。

**【透明性边界】** 本轮另有一次**非读数的方向性探查**（在 `r20–r30` 段对 dialogue 调用数与消息条数做的两臂对照，用于定下一轮方向），**其结论未纳入本报告、亦未进证据索引**；本报告全部 A1 数字只来自批次跑完后的正式读数。

### 3.2 判定三件套与阈值纪律

- 每条读数必须同表给出：**`|Δ|` / 同分母噪声带上界 `band_source` / 分母条数**。
- **分母 < 30**：只报事件数，不报比率，不写"0%"。
- **分母 < 68**：一律标 `probe`，结论写「本规模下无法判定」。
- **单位纪律**：F-2/F-3 是 per-adjacent-pair、F-2b 是 per-thread、F-4 是 per-event、F-5 是 per-agent、M-7 是 per-(agent,slot)。**这些单位的噪声带不能借用消息级档**（R1 §2.5 / R7 §0.1 同一纪律：分母必须在本行内写出单位与推导式）。
- 恒 0 / 恒 1 时 B2 退化，改用精确二项上界（0 事件时 95% 上界 ≈ 3/n），且 `band_source` 写 `rule-of-three(3/n)`。

**「无差异」≠「差异不显著」——两个不同结论，不能混写。**

| 写法 | 成立条件 | 能说明什么 |
|---|---|---|
| **无差异（已证实）** | 两臂在**同一回合切片**上生成结构逐项相同（如调用结构、消息条数、线程形状逐项相等），且差异来源可归到唯一变量之外 | 「**该参数在本规模下不是 binding constraint**」——这是**存在性事实**，不依赖分母大小，可写「已证实」 |
| **差异不显著（无法判定）** | 两臂有差，但 `|Δ|` 未超同分母噪声带上界，或分母 <68 / 无可用带 | 只能说「**本规模下无法判定**」，**不能**说「没有差异」，更不能说「有效/无效」 |

**【判断】** 本轮若出现前者，写「已证实无差异」是**诚实的强结论**，不是"拿小分母硬下判断"；反过来，把"无差异"写成"不显著"会低估证据，把"不显著"写成"无差异"则是撒谎。两者读者观感相似，结论完全不同。


### 3.3 本轮特有的四个陷阱

1. **窗口放宽 ≠ 往来变多**：`reply_window_rounds` 只放宽"入站消息还能不能被回"的回合数；若线程早已被 `max_turns=6` 封口或 slot 内消息配额用尽，放宽窗口不会产生任何新回复。先查封顶来源，再谈效果。
2. **用 `msg_id` 去重会静默丢消息**：本轮两臂日志的 `msg_id` 存在撞号（见 §5 W4），任何按 `msg_id` 的线程重建都会少算。**必须用 `msg_uid`**（`meta.assertions.msg_uid_unique` 为唯一性凭证）。
3. **分母不可比时不许比较率**：两臂若消息量/线程量差异 >30%，一律判「不可比」，只允许写"有没有"（存在性事实），不允许写"多了多少"。
4. **"仅机制接通"不是"效果未达标"**：单臂改动下，机制接通与效果改善是两件事。前者可写「已证实」，后者只能写「本规模下无法判定」，**不得**用措辞把两者混起来（例如"放宽窗口后对话明显更热络"）。

### 3.4 时序护栏：跑批期间不得切换分支（本轮实测留痕）

**【事实】** A1 批的进程工作目录就是 `<repo>/code`（`/proc/<pid>/cwd -> .../social-experiment/code`），Python 从工作树**就地导入** `code/` 下的模块。因此**在批次运行期间执行 `git checkout` 会在进程脚下替换代码文件**——这既是"跑批期间修改核心目录"的违纪动作，也会让这一批数据变成"同一次跑批里混了两个版本的代码"，事后无法用单一 `code_sha` 定义。

**【判断】** 这是本轮真实发生过的时序冲突：成稿任务要求"在 master 上本地 commit"，而 master 与 A1 分支的差异正是 `code/life/dialogue_threads.py:30`。正确执行顺序是**先等批次结束、再切分支提交**，而不是为了赶成稿在跑批中途切。

**【留痕要求】** 切换分支前必须实跑并记录下述检查，输出进报告（空输出 ⇒ 当前无批在跑，才允许切）：

```bash
pgrep -fa "orchestration[ ]run"    # 期望：空输出（rc=1）
```

正则必须写成 `orchestration[ ]run`：直接写 `pgrep -f "orchestration run"` 会**匹配到 pgrep 自己的命令行**得到假阳性（与团队纪律第 1 条同一个坑）。

**【事实 · 本轮 A1 批的实测耗时（为什么"边跑边改代码"代价高）】** 批次启动后按 `run.jsonl` 只读采样（**半成品日志只用于运维度量，不取任何对话/线程读数**）：

| 观测项 | A1 批（本轮，采样于 16.6 分钟时点） | A0 历史批（`run_d2_after_n16_seed42`） |
|---|---|---|
| 已推进回合 | `round 0..5`（末事件 `TURN_SEAL`，seq 4850） | 全 84 回合完成 |
| 折算速率（**线性折算，仅供对照，不可用作 ETA 依据**——原因见下方 live-call 表） | **≈166 s/round** | ≈3000 s / 84 ≈ **36 s/round** |
| `LLM_CALL` 计数 | 471（≈78/round） | 3403（≈40/round） |
| `cached` 占比 | 131 / 471 = **27.8%** | 1734 / 3403 = **51.0%** |
| 全量批 ETA | **03:00 ± 15 分钟**（02:41 已 seal 到 `r21`，夜间整合尖峰已过、之后回合速率回升；原线性外推的 3.5–4 小时作废） | A0 全批 3000 s |

**【事实 · ETA 的正确算法（按 live call 计，读者可复算）】** "均值 × 回合数"必然夸大，因为 live 调用在回合间极不均匀：

| 依据 | 数值 | 复算方式 |
|---|---|---|
| A0 全批 `LLM_CALL` / 其中 live（`cached=false`） | 3403 / **1669** | 逐回合统计 `payload.cached` |
| A0 单位 live 调用耗时 | 3000 s / 1669 = **1.80 s/live-call** | 批次 `duration_sec` ÷ live 数 |
| A0 live 调用累计占比 | r<2 **11.3%**、r<4 12.1%、r<6 20.4%、r<8 26.9%、r<10 **29.1%**、r<11 41.9%、r<22 50.1%、r<43 66.6% | 逐回合累加 live 数 ÷ 1669 |
| A1 已观测 | 02:05 起跑 → 02:25:48 首次覆盖 `r≤9` 的 flush，约 **1248 s**；`r0–r9` 逐回合调用数与 A0 **逐项相同**（`44/203/0/13/208/3/15/193/44/9`），live 数同为 **485** | 半成品日志切片（**只用于运维度量**） |
| A1 单位 live 调用耗时 | 1248 s / 485 = **2.57 s/live-call ≈ 1.43x A0** | 同上 |
| 剩余估算 | 剩余 live ≈1184 次 × 2.57 s ≈ **51 分钟**（按 A0 的 1.80 s 则 ≈36 分钟），另加 `r10` 整合尖峰 ≈10 分钟 | — |

**【判断】** 前 10 回合吃掉 29% 的 live 调用、却只占 12% 的回合数 ⇒ "平均每回合耗时 × 剩余回合"必然高估。上表 70–85 分钟的 ETA 即由此复算得出。

**【进度更新 · 02:41】** A1 批已 seal 到 **`r21`**（`TURN_SEAL` r0–r21 共 22 条），夜间整合尖峰已过，其后回合耗时明显低于尖峰段 ⇒ ETA 收敛为 **03:00 ± 15 分钟**（早于先前的 03:15–03:30）。

**【runbook 教训 · `flush-every=N` 会制造"假静默窗口"，整合尖峰回合尤甚】** `--flush-every 2` 只在**回合边界**生效；而夜间记忆整合回合（`round 10`）既长又重，**比任何 flush 间隔都长**，期间日志文件**完全不增长**——这是正常状态，不是卡死。

| 可复算依据（A0 `round 10`） | 数值 |
|---|---|
| 该回合 `LLM_CALL` / 其中 live | **1355** / **215** |
| 其中 `importance` | 1216 次，但只对应 **76** 个不同 `prompt_hash`（16 agents 各判一遍），`cached=True` **1140/1216 = 93.8%** |
| 该回合其它事件 | `MEMORY_WRITE` **2906**、`OBSERVATION` **2874**、`MEMORY_REFLECT` 16、`METABOLISM` 16 |
| 折算耗时 | 215 live × **2.57 s/live**（A1 端点速率）≈ **9.2 分钟**；按 A0 端点 1.80 s ≈ **6.4 分钟** |
| 回合内是否有输出 | 尖峰期间**无 flush、无 `TURN_SEAL`**；回合边界结束时才有 1 条 `TURN_SEAL` |

**【判断】** ⇒ 巡检时看到"文件 5–10 分钟不动"且最后一条事件不是 `TURN_SEAL`，**先按本节判断是不是整合尖峰，再决定是否干预**；直接按"卡死"强杀会毁掉整批（这与 §3.4 开头的"跑批期间不得换分支"是同一类代价）。

⚠️ **同一节的反面陷阱（本轮实测踩到并排除）**：**不要用日志里的 `mono_ts` 算逐回合耗时**。该字段**跨回合不单调**（实测 `r4=5858 > r5=5362`、`r81=107942 > r82=85091`），直接相减会得出「某回合耗时 27503 s / 另一回合 −5145 s」这种荒谬值（全批 `mono_ts` 跨度 84122 s，而批次 `duration_sec` 只有 3000 s）。⇒ 逐回合耗时只能像上表那样**用 live 调用数 × 单位耗时折算**，或从 side cache 文件 mtime 取，不能用 `mono_ts` 相减。

**机制解释（比「字段名不好」更准确）**：`code/engine/ledger.py:18` 定 `time_unit = 1000`、`:29` 写 `mono_ts = int(round_no) * time_unit + rs`；`code/engine/kernel.py:32-33` 全批**只有一个** `Ledger` 实例（不是每个 agent 一个时钟）。于是 `mono_ts = 回合基数×1000 + 回合内序号 rs`，而 `rs` 在事件密集回合**会超过 1000**，直接溢进下一回合的基数区间（实测 r4 到 `4000+1858=5858` > r5 基数 `5000`）——这就是「跨回合不单调」的成因，属**设计后果**，不是数据损坏。

**措辞与边界**：可以说「字段语义与名字不符」（`mono` 暗示单调，实际不保证），但**不建议本轮改名**——改名会改动 `engine_version` 指纹并破坏与既有证据的可比性，超出本轮范围；本节只作口径警示，不构成重构建议。

**【判断】** 这三条必须一起读，才能说明 §3.4 的护栏不是洁癖：① 单批就是小时级长跑；② 进程 cwd 就是 `code/`，代码是**就地导入**的；③ 因此在这几小时里任何 `git checkout` / 分支切换 / 代码编辑都会直接改掉正在被 import 的行为代码——不是"可能影响"，是"必定改动"。A0 与 A1 若要构成干净对照，两臂各自从头到尾只能用**一个** `code_sha`；中途换分支会让这批数据失去 `code_sha` 定义能力，等价于废掉本轮的对照价值。

**【已澄清：切片口径假象（非本轮副作用）】** 初稿曾把上表的 `judge` ≈4.3x 记为「待定性异常」。**判据已到手，此判定作废**：把 A0 全量日志**切到同样前 6 回合**后，两臂逐项完全相同——

| purpose | A1（前 6 回合） | A0（前 6 回合，切片） | A0（全 84 回合） | A0 全量 /round |
|---|---|---|---|---|
| `judge` | 223 | **223** | 717 | ≈8.5 |
| `importance` | 169 | **169** | 1747 | ≈20.8 |
| `dialogue` | 51 | **51** | 714 | ≈8.5 |
| `plan` | 16 | **16** | 16 | ≈0.19 |
| `reflect` | 12 | **12** | 112 | ≈1.33 |
| 合计 | **471** | **471** | 3403 | ≈40.5 |
| `cached` | 131 / 471 = 27.8% | **131 / 471 = 27.8%** | 1734 / 3403 = 51.0% | — |

**【事实 · 可复算依据】** ① 两臂前 6 回合 `LLM_CALL` 均为 **471** 次、`cached` 均为 **131**（27.8%）；② 逐回合 `judge` 均为 **r0=16 / r1=114 / r4=93**，`r2/r3/r5=0`；③ 上述三项由本报告作者在 A0 全量日志上**独立复算过一次**（命令见 §3.1，`--round<=5` 切片），与 life-crafter 的拆解一致。

**【判断】** ⇒ **4.3x 完全来自「6 回合 vs 84 回合」的切片选择**，不是本轮改动的副作用：A0 的 ≈8.5/round 是被 84 回合中大量低活动回合**摊薄**后的均值（单回合 0–1355 次，6 个回合 ≤2 次），而前段本来就是 40–115 次/回合的密集区。两臂**同回合调用结构一致，不构成差异**。

**【事实 · 代码级旁证（为什么改动不可能放大 judge）】** judge 三条路径均**不读** `reply_window_rounds`：`code/life/agent.py:694` `_maybe_soft_judge`（每 `(to, dim, level)` 一生只判一次）、`code/life/agent.py:729` `_maybe_social_appraisal`（每 peer/周 ≤4 peers，`JF-` 前缀见 `:502`）、`code/life/agent.py:1275` `_score_importance`（其 purpose 是 `importance`，不是 `judge`）。全仓非测试代码中引用该变量的只有 `code/life/dialogue_threads.py:30` 与 `code/life/agent.py:856` 两处（`grep -rn "reply_window_rounds" --include=*.py code/`，排除 `.worktrees/`）。

**【事实 · 门禁口径不受影响】** `judge` 仍按 `payload.purpose` 计入 `obs llm-cost` 的全量汇总，切片假象只影响"跨切片比较"，不影响门禁对整批调用真实性的判定。

**【事实 · 复核单回合最大值 1355 的来源（防被当成 anomaly 追问）】** A0 的 `LLM_CALL` 单回合最大值 = **1355，出现在 round 10**，且**不是统计口径错**：该回合是同批的**夜间记忆整合回合**（`MEMORY_WRITE` 2906、`OBSERVATION` 2874、`MEMORY_REFLECT` 16、`METABOLISM` 16），其中 `importance` 调用 **1216** 次 = 16 agents × 76。

关键在于**调用计数 ≠ 独立推理数**：这 1216 次 `importance` 只对应 **76 个不同 `prompt_hash`**（16 个 agent 共享同一批 76 个 prompt），`cached=True` 占 **1140/1216 = 93.8%**。⇒ 该回合是**一次性整合事件 + 高缓存命中**，不是"单回合做了 1355 次独立判断"。报告引用该值时必须同时给这两句限定，否则读者会把它当异常值。

> 上表的利用率差异（`cached` 27.8% vs 51.0%、调用 78/round vs 40/round）**已随上节一并澄清为切片口径假象**：前 6 回合两臂逐项相同，差异只是「6 回合 vs 84 回合」的摊薄效应。**禁止**在批未结束时用半成品日志给出任何 A1 对话/线程读数（此禁令不因本节澄清而放宽）。

> 本轮切换前的实测输出与时刻见 **§8 证据索引第 11 行**。

---

## 4. 与 R4 的口径对齐说明

**【事实】** 本报告不新立口径，F 系列定义、统计单位、三个"不算改善"的陷阱全部沿用 **R4 §1 / §3**。与 R4 的对照关系如下（填数时逐行核对，分母不同即写不可比）：

| 指标 | R4 的 v0-anchor 读数 | R4 的 A0 读数 | 与本报告的关系 |
|---|---|---|---|
| **F-2b** 多话题线程占比 | `8.1%`（分母 172 线程） | `0.0%`（分母 206 线程） | 本报告 M-1 正式承接此项。R4 已判「仅描述（无可用带）」；本报告若两臂分母一致，可升级为**同分母对比**，否则仍写「不可比」。 |
| **F-3** 情绪呼应 | `6 次中 1 次`（事件数，分母 6） | `107 次中 26 次`（24.3%） | 分母差 94%，R4 判「不可比」。本报告只允许在**两臂同分母**时出对比，且分母 <68 必须标 `probe`。 |
| **F-4** 修复闭环 | `5 次中 0 次`（事件数，分母 5） | `39 次中 3 次`（7.7%） | 同上，R4 判「不可比」。注意 `dialogue_repair.json enabled=false` 为默认关（勘察发现），F-4 的变化**不能**直接归因到回复窗口。 |
| **F-1 / F-6** | 77.0% / 6.4%（分母 187 消息） | 76.1% / 6.4%（分母 686 消息） | 分母差 >30%，R4 判「不可比」。本报告沿用同一判定，不因为"数值接近"就说"无变化"。 |
| **F-7** | `2 / 2`（分母 2 < 30，只写事件数） | `81 / 108`（统一口径 P1） | R4 已判「不可比、不可引用」。本报告**不重复引用 F-7 做跨臂比较**，只在证据索引登记其现行 sha。 |

**【判断】** 与 R4 对齐的正确姿势：**R4 已明确判"不可比"的组合，R8 不能靠换一份数据把它变可比**。R8 能加的只有一件事——把 A0/A1 **同口径同分母**的重算结果摆出来，并如实标注哪些仍不可比。

---

## 5. 未处理的基础设施风险（本轮已规避，但必须登记）

**【事实】** 以下两条来自勘察阶段对仓库的实测（源：团队共享工作区 `recon-round-state.md` W4/W5 段，与 `reports/R7-world-event-wiring.md §7.1`）。

### 5.1 W4 · `msg_id` 撞号（中危，本轮未修）

- 现象：同回合不同 agent 的 `msg_id` 相同，与契约 `code/life/ports.py:78-82`（`D-<round>-<agent_id>-<n>` 等）不符；现网生成点是 `code/orchestration/integration.py` 的 `f"D-{r}-{n}"` / `f"P-{r}-{n_a}"` / `f"G-{gid}-{r}-{n_g}"` 形式（缺 agent 维度）。
- 实测（A0 批 `run_d2_after_n16_seed42`，日志 `643f13a5`）：686 条 MSG 只有 **216 个不同 `msg_id`**，**71 个值撞号、涉及 541 条消息（79%）**。
- **本轮如何规避**：一切线程重建／指针校验走 **`msg_uid`**，不碰 `msg_id`；以 `meta.json::assertions.msg_uid_unique=true` 为唯一性凭证。本报告与 `d9-readings.md` 的线程级读数因此不受影响。
- **危害（未消除）**：任何按 `msg_id` 去重/引用的下游会静默丢消息。**本轮不修**，登记待下轮。

### 5.2 W5 · `_default_llm` 静默降级 MockProvider（中危，本轮未修）

- 现象：`code/orchestration/integration.py:894-945`，忘记设 `HITT_LLM_PROVIDER` 就静默返回 `MockProvider()`/`RuleBasedLLM()` 且**不抛错**；`HITT_LLM_PROVIDER=openai_compat` 但 `LLM_ENDPOINT`/`LLM_MODEL` 为空时也不报错。
- 危害：可能"零 token 也算真跑"，产出一份"看起来是真跑"的日志。
- **本轮如何规避**：真跑批次一律过门禁 `cd code && python3 -m obs llm-cost --log <run>/run.jsonl --require-provider openai_compat`；A1 臂的 `meta.json` 必须同时满足 `provider=openai_compat`、`llm_cached_ratio` 与 `llm_calls>0` 自洽、`fallback_detected=false`、`degraded_calls=0`。**任一条不满足，本报告全部读数降级为「未验证」。**
- 复核凭证（A0 历史批）：`provider=openai_compat`、`llm_calls=3403`、`llm_cached=1734`（`llm_cached_ratio=0.5096`）、`fallback_detected=false`、`degraded_calls=0`、`llm_provider_in_events={"openai_compat":3403}`。

---

## 6. 限制

1. **单臂改动 + 单 seed + 单个模拟周**：任何效果层结论都只在本配置、本规模、本 seed 内成立。
2. **窗口放宽的收益可能被其他上限吃掉**：`max_turns=6`（线程封口）、`max_messages_per_slot=2`（slot 配额）、`max_turns_per_round=2`（回合内推进上限）任一都可能先封顶。§2.2 M-7 就是为查这件事设的。
3. **不可复现的部分**：LLM 措辞层不可逐字复现，只能以日志 sha256 冻结快照 + 复算命令替代。
4. **本报告不回答"是否更有生活气息"**：只回答"往来密度这一结构量有没有变、在哪里被卡住"。
5. **`importance` 打分是「跨 agent 重复判定」结构（可复用的运行成本事实）**：A0 夜间整合回合（round 10）里，16 个 agent 各发起 76 次 `importance` 调用（合计 1216 次），但**只对应 76 个不同 `prompt_hash`** —— 即同一批内容被 16 个 agent 各判了一次；该回合 `cached=True` 占 1140/1216 = **93.8%**，实际重复推理被缓存吸收。**中性描述、不含优化建议**：这意味着当前成本与耗时的高位依赖缓存命中；若换端点、清缓存或缓存键改变，这一项的调用与耗时规模会按 agent 数（16x）放大。本报告引用该批的耗时/成本时必须与这一依赖一起读。
6. **批间端点速率差异可达 1.43x（今日偏慢）**：A0 实测 **1.80 s/live-call**；A1 前 10 回合实测 **2.57 s/live-call ≈1.43x**（同端点地址、同模型名）。⇒ **跨批比较耗时/成本时必须先剔除此项**，不能把"这批更慢"读成机制差异（例如把耗时上升当成对话变多的证据）。本条只作口径约束，不作性能结论。
7. **`DROPPED unknown_intent_field(MEMORY_CONSOLIDATE, keys=[text])` 是既有行为，非本轮引入**：聚合摘要的 `text` 键未列入 `_PASSTHROUGH["MEMORY_CONSOLIDATE"]`（`code/orchestration/integration.py:202-206` 的透传表里只有 `MEMORY_RETRIEVE`/`MEMORY_REFLECT`/`OFFER_CREATED`；装配规则见 `:409-420`「其余键须落 `DROPPED{reason:"unknown_intent_field"}`，**不得静默丢弃**」），故 `MEMORY_CONSOLIDATE`（装配入口 `:580`）每次整合都会落一批 DROPPED。实测 A0：**r9 时点 243 条**，全部整合回合各 **256** 条（r21/33/45/57/69/81），全批合计 **1779**，与 `meta.json::dropped_counts` 一致；A1 在同期时点同为 **243 条 / r9** ⇒ 两臂逐项相同，**非本轮变量所致**。被丢的仅为审计摘要：事件主体六键完整、固化生效；派生记忆 `body_ref is None`（`code/life/memory.py:199-206`）走既有 lexical 降级路径仍可检索。**不影响本轮任何对话/线程读数。**

---

## 7. 三档标注（已证实 / 仅机制接通未验证 / 未解决）

### 7.1 已证实（可跨臂引用的事实层）

- **唯一变量认定（C-6 限定写法）**：分支 `feat/dialogue-density` **相对 master `371772e`** 仅改 `code/life/dialogue_threads.py:30` 一行，`code/config/` 零改动（`git diff --stat` 双证）。**此项与读数无关，独立成立。** ⚠️ 但两臂 `code_sha`（`884f4541` vs `05636bc`）之间隔 **11 个 commit**，"唯一变量"只成立于"相对 master 的 diff"这一层，不等于"两臂 code_sha 之间只差一个文件"（见 `d9-readings.md` C-6）。
- **结构层十项读数两臂逐项相同 ⇒「已证实无差异」**：`686 消息 / 206 线程 / 顶格 305 of 381 / ≥3 轮 89 / ≥6 轮 68 / ≥3 发言者 9 / 延迟 327-153-480 / ≥3 回合 0 / 平均往返 3.0049 / 条数分布`（§2.2 全表，分母 206 线程 + 480 配对 + 381 单位）。按 §3.2 判据，**无差异是存在性事实，不依赖分母大小**；表述限定在本配置（感知窗 2）/ 本规模（n16r84 seed42）/ 本 seed 内，并配 §2.3 的机制解释。
- **发出量封顶在 `max_messages_per_slot=2`**：381 个 `(agent,day,slot)` 单位中 305 个顶格 2 条（80.05%）、**0 个 ≥3**（两臂相同）——这是"密度天花板不在回复窗"的**计数型事实**。
- **正文层不是同一批**：两臂正文仅 35/686 同位相同、唯一正文交集 34 条、`dialogue` 提示词逐位相同仅 248/714（34.7%）⇒ 结构相同不能读成"跑重了"（`d9-readings.md` §7 可复算）。
- **非正文类 purpose 两臂一致**：`judge` / `importance` / `negotiation` / `plan` 四类（合计 **2561 / 3403 = 75.26%** 的 LLM 调用）提示词**逐位相同**（717/1747/81/16）⇒ 这四类不吃正文措辞，两臂世界态一致，差异只可能来自正文措辞层。**不等于"提示词复用"**；且**不得**把该结论扩大：`describe`(0%) / `reflect`(23.2%) / `dialogue`(34.7%) 三类存在差异。

### 7.2 仅机制接通未验证（改了、跑了，但效果层无判定）

- **措辞层变化只能写"方向性"**：L-2 0.819242→0.810496（Δ −0.008746，562→556 of 686）、L-3 0.860058→0.846939（Δ −0.013119，590→581 of 686）、L-6 0.099125→0.090379（68→62）、**L-5 反向 0.018950→0.021866（13→15）**、L-4 0.069971→0.062682、L-13 0.039359→0.021866（27→15）。分母均 686，本轮**未做同分母 bootstrap 带**，故一律判「方向性（无可用带）」，**不得**写成"明显改善"，也**不得**隐去 L-5 的反向变化。
- **L-7 计数相同属巧合（C-3）**：两臂各 **335/686**，但触发集合 `|A0∩D9| = 240`、`并集 430`、**jaccard 0.5581** ⇒ 正确表述是"计数巧合、触发集合不同"，**禁止**写成"L-7 完全不变/无变化"，也禁止反推"疑似复用"。
- **judge 侧指标不吃正文（C-5）**：`judge`/`importance`/`negotiation`/`plan` 四类提示词两臂逐位相同（2561/3403 = 75.26%）⇒ 由这四类派生的指标（含 **F-7 越界提及**、关系变动判定）**不能用来衡量措辞变化**；排除面只到这四类，`describe`/`reflect`/`dialogue` 派生指标理论上可受措辞影响，不排除。
- **A0 是否真的走到"4 回合内仍可回复"路径**：**无法从日志判定**。日志无"入站消息被看见但未回"的轨迹（E8 未验证），且外层感知窗 `VISIBLE_WINDOW_ROUNDS=2` 使 `r-3` 及更早事件对 agent 不可见，`延迟≥3` 分支在本配置下**恒不命中**（§2.3 的恒等式性质）。⇒ 该项保持"仅机制接通"，不作效果判定。
- **F-4 修复闭环**：A0 3/39 vs D9 1/32，分母 <68 ⇒ 按 §3.2 一律标 `probe`，写「本规模下无法判定」。

### 7.3 未解决

- **W4 `msg_id` 撞号 79%**：本轮规避未修（§5.1）。
- **W5 静默降级 MockProvider**：本轮靠门禁规避未修（§5.2）。
- **往来密度被 `max_messages_per_slot=2` 结构性限制**：M-7 显示 381 个 slot 单位中 305 个顶格（80.05%）、**0 个 ≥3**，而 M-2/M-4/M-5 两臂不动 ⇒ 这是本轮**未解决的结构问题**，属 D10 范畴（本报告只给判据）。
- **措辞层无可用噪声带**：本轮未跑同分母 bootstrap，故措辞层只能写方向性；补带属下一轮工作项。
- **C-1 / C-2 两项来源缺陷**：`/tmp` 原件缺 `host.log`（入库件为作者保存的 stdout 摘录，不可对拍）；`meta.side_root=null` 与命令行 `--side-root` 不符 ⇒ 引缓存隔离只能引目录 + 条数（1674 个 `responses` = 唯一 prompt 数 1674）。

---

## 8. 证据索引

> 固定列：`# | 结论 | 层级 | 来源 | sha256 | sha8 | 复现`。`sha8` = sha256 前 8 位；**源码/配置类**引用写"该臂 commit sha + 文件:行号"，`sha8` 列写 `TODO（源码随提交变动）`。

| # | 结论 | 层级 | 来源（仓库相对路径） | sha256 | sha8 | 复现 |
|---|---|---|---|---|---|---|
| 1 | 本轮唯一变量 = `reply_window_rounds` 2→4，仅 `code/life/dialogue_threads.py` 一行，配置零改动 | 事实（代码） | `code/life/dialogue_threads.py`（A1 臂 commit `05636bc`）+ `:30`；master `371772e` + `:30` | TODO（源码随提交变动） | TODO（源码随提交变动） | `git diff 371772e..05636bc -- code/`；`git diff --stat 371772e..05636bc -- code/config/`（空） |
| 2 | 生效值由 `DEFAULTS` 决定（`life_v2.json` 无 `dialogue` 段） | 事实（配置） | `code/config/life_v2.json`（A1 臂 commit `05636bc`）；读取链 `code/life/agent.py:788-790`、`code/life/dialogue_threads.py:71-95` | `72b40de904069af4492b4a1acf484d9c4ccb20f8caade6e9ac112a1ace6d5197` | `72b40de9` | `sha256sum code/config/life_v2.json`；`python3 -c "import json;print(list(json.load(open('code/config/life_v2.json')).keys()))"` |
| 3 | A0 基线臂身份与规模（686 条 MSG / 16 agents / 84 回合 / seed 42）；**`code_sha=884f4541`（代码身份，写在来源列，不占 sha256 列）** | 事实（run 元数据） | `v2/evidence/run_d2_after_n16_seed42/run.jsonl`（`643f13a5`）与 `meta.json`（`5fe058f3`） | `run.jsonl`=`643f13a528c288d3e9677cb8ac100139224afbd0b46c0f7da0c3a5ed85b13141`；`meta.json`=`5fe058f38fa8239854d91db7126f4acb019f0b8692a2dca08610a07c887d4a20` | `643f13a5` / `5fe058f3` | `sha256sum v2/evidence/run_d2_after_n16_seed42/{run.jsonl,meta.json}`；`python3 -c "import json;m=json.load(open('v2/evidence/run_d2_after_n16_seed42/meta.json'));print(m['msg_counts'],m['code_sha'],m['n'],m['rounds'],m['seed'])"` |
| 4 | A0 臂真跑验真（provider 与调用数自洽：`llm_calls=3403`、`llm_cached=1734`、`llm_cached_ratio=0.5096`、`fallback_detected=false`、`degraded_calls=0`、`provider=openai_compat`、`assertions.msg_uid_unique=true`） | 事实（验真） | 同上 `meta.json`（`5fe058f3`） | `5fe058f38fa8239854d91db7126f4acb019f0b8692a2dca08610a07c887d4a20` | `5fe058f3` | `cd code && python3 -m obs llm-cost --log ../v2/evidence/run_d2_after_n16_seed42/run.jsonl --require-provider openai_compat`；`python3 -c "import json;m=json.load(open('v2/evidence/run_d2_after_n16_seed42/meta.json'));print(m['provider'],m['llm_calls'],m['llm_cached'],m['fallback_detected'],m['degraded_calls'])"` |
| 4b | **A0 可作行为基线的依据：`884f454..371772e` 的 `code/` 差异仅限 `code/frontend/`（7 条目 / 源码 5 个），`code/life/`、`code/orchestration/`、`code/config/`、`code/engine/` 零命中** | 事实（代码漂移审计） | 两个 commit：`884f4541b80e5343119b51bf94054b2f54dd4559`（A0 `code_sha`）与 `371772e1dfe6cb078777b6ffcbe20e116791a03e`（master HEAD） | TODO（源码随提交变动） | TODO（源码随提交变动） | `git diff --stat 884f4541..371772e -- code/`；`git diff --stat 884f4541..371772e -- code/life/ code/orchestration/ code/config/ code/engine/`（空输出） |
| 5 | 两臂读数（结构层十项逐项相同 + 措辞层方向性变化）：A0 `686/206/305-of-381/89/68/9/327-153-480/≥3=0`；D9 同；L-2 0.819242→0.810496、L-3 0.860058→0.846939、L-5 0.018950→0.021866（反向）、L-6 0.099125→0.090379、L-7 335/686 两侧相同但 jaccard 0.5581 | 读数 | `v2/evidence/d5_metrics_d9a0.{json,md}` + `d5_metrics_d9a1.{json,md}` + `d9_density_d9a0/d9a1.json` + `d9_reply_latency_a0/d9a1.json`；唯一引用源 `reports/d9-readings.md` | A0 `d5_metrics` = `a2b55e21831a65ae…`；D9 `d5_metrics` = `54ada834d81527ba…`；D9 密度 = `92ad7a51a86215fb…`；D9 延迟 = `e11b79fe087fcf9e…` | `a2b55e21` / `54ada834` / `92ad7a51` / `e11b79fe` | `python3 tools/d5/dialogue_metrics.py --log <run.jsonl> --meta <meta.json> --out-json …`；`d9_density.py`；`d9_reply_latency.py`（命令见 `d9-readings.md` §1） |
| 5b | **D9 臂身份与验真**：`code_sha=code_sha_end=05636bc`、n16 r84 seed42、`provider={openai_compat:3403}`、`cached 1729`、`degraded 0`、`fallback_detected=false`、events 194126、`duration_sec 5239`；`obs llm-cost` RC=0、`provider_guard.ok=true` | 事实（run 元数据 + 验真） | `v2/evidence/run_d9_a1_n16r84_seed42/meta.json`（`f9ba950a`）+ `llmcost.json`（`ecfe861d`）；`run.jsonl` **不入库**（`.gitignore:8`），sha256 `abefdf73ca239cda…f427`（91,343,119 B） | `meta.json` = `f9ba950acbcc653d91ec2e5d8b2237895916e96d5385c17daf0b558ce539c3d4`；`llmcost.json` = `ecfe861dc5a5a2a2…` | `f9ba950a` / `ecfe861d` | `sha256sum v2/evidence/run_d9_a1_n16r84_seed42/{meta.json,llmcost.json}`；`cd code && python3 -m obs llm-cost --log ../v2/evidence/run_d9_a1_n16r84_seed42/run.jsonl --require-provider openai_compat` |
| 6 | 【占位，待 `d9-shots-push` 回填】D9 四视图真实截图（chat/rhythm/spread/600），来源 run 目录 = `v2/evidence/run_d9_a1_n16r84_seed42/`（日志 `abefdf73…`）；A0 既有 `d7_shots/` 四图**仅作对照**，两批不同源 | 事实（证据） | `v2/evidence/d9_shots/<view>-abefdf73.png`（待产出） | 【待回填】 | 【待回填】 | 渲染 `run_d9_a1_n16r84_seed42/run.jsonl` + `code/frontend/tools/shot.py`（命令见 `d9-readings.md` §11） |
| 7 | W4 `msg_id` 撞号：686 条 MSG 仅 216 个不同 `msg_id`，71 个值撞号涉及 541 条（79%） | 事实（缺陷） | `reports/R7-world-event-wiring.md §7.1(1)`；`code/orchestration/integration.py`（`:825/:840/:864`）与契约 `code/life/ports.py:78-82` | TODO（源码随提交变动） | TODO（源码随提交变动） | 按 `R7 §7.1(1)` 复算 `msg_id` 去重计数 |
| 8 | W5 静默降级 MockProvider | 事实（缺陷） | `code/orchestration/integration.py:894-945`；`reports/R7-world-event-wiring.md §7.1(2)` | TODO（源码随提交变动） | TODO（源码随提交变动） | `grep -n "MockProvider\|RuleBasedLLM" code/orchestration/integration.py` |
| 9 | F-2b / F-3 / F-4 的 R4 对照口径与不可比判定 | 事实（口径） | `reports/R4-life-texture.md §2 / §4`；`v2/evidence/d6_compare_a0.md`（`544a4523`） | 【待填：重算】 | `544a4523` | 见 R4 §6 证据索引 |
| 10 | `reports/d9-readings.md` 本身作为两臂读数的唯一引用源（含 C-1…C-6 caveat 与逐条复算命令） | 读数（引用源） | `reports/d9-readings.md`（**已入库**） | `45b98a6e23759ec3…`（本版定稿时刻；文档后续编辑会变，引用以文件内 §1/§2 命令为准） | `45b98a6e` | `sha256sum reports/d9-readings.md` |
| 10b | 本轮往返密度读数器 `d9_density.py` 为只读度量脚本（零 LLM / 零网络 / 无跑批逻辑，复用 `tools/d5/dialogue_metrics.py` 的 `extract_messages`/`group_threads`）；**三种调用方式 rc 全 0、`--out-json` 产物 sha 与修复前逐字节一致** | 事实（脚本身份） | `v2/evidence/d9_density.py` | `78a32e66803b8dc869faf247e666ce1b1237a6077528f21fbd0de85727c0cdc3` | `78a32e66` | `sha256sum v2/evidence/d9_density.py`；`python3 v2/evidence/d9_density.py --log … --out-json /tmp/x.json`（rc=0）；`grep -nE "requests|openai|subprocess|orchestration" v2/evidence/d9_density.py`（空） |
| 11 | 时序护栏：落 commit 前确认无批在跑（`pgrep -fa "orchestration[ ]run"` 空输出） | 事实（时序） | 定稿时刻 **2026-10-21 04:21（+08:00）**，与 `d9-doc` 的 docs/evidence commit 同一轮次 | — | — | `pgrep -fa "orchestration[ ]run"`（空输出，rc=1） |
| 12 | **E1** A0 回复延迟分布：480 条回复中 1 回合 **327**、2 回合 **153**、0 回合 0、**≥3 回合 0**（分母 480） | 已证实（指标型事实） | `v2/evidence/d9_reply_latency_a0.json` | `f8c58d9572f59b7aafb7e04ed957a8c582d45032a4edd0569ff3286729bf7b97` | `f8c58d95` | `python3 v2/evidence/d9_reply_latency.py --log v2/evidence/run_d2_after_n16_seed42/run.jsonl --out-json v2/evidence/d9_reply_latency_a0.json` |
| 13 | **E2** 分渠道同形：DM 1 回合 231 / 2 回合 136；GROUP 1 回合 96 / 2 回合 17；两渠道 ≥3 均为 0 | 已证实（指标型事实） | 同上 `by_channel` | 同上 | `f8c58d95` | 同上（`--out-json` 内含 `by_channel`） |
| 14 | **E3** 感知窗硬编码 2：`VISIBLE_WINDOW_ROUNDS = 2`（`integration.py:275`），唯一注入点 `:341`，过滤落地 `contracts/visibility.py:100`（`visibility_index.py:146`） | 已证实（源码事实） | `code/orchestration/integration.py`、`code/contracts/visibility.py` | TODO（源码随提交变动） | TODO | `grep -n "VISIBLE_WINDOW_ROUNDS" code/orchestration/integration.py` |
| 15 | **E4** 本轮未动感知窗：`git diff master -- code/orchestration/ code/contracts/` 输出 0 行 | 已证实（源码事实） | git | — | — | `git diff master -- code/orchestration/ code/contracts/ \| wc -l` |
| 16 | **E5** 变量确实改了：`reply_window_rounds` 在 `884f454` = 2、`371772e` = 2、分支 = 4；`life_v2.json` 无 `dialogue` 段 ⇒ 代码常量即生效值 | 已证实（源码事实） | `code/life/dialogue_threads.py:30`、`code/config/life_v2.json` | TODO（源码随提交变动） | TODO | `git show 884f454:code/life/dialogue_threads.py \| grep reply_window_rounds`；`grep -n reply_window_rounds code/life/dialogue_threads.py` |
| 17 | **E6** 两窗叠加 ⇒ 实际最老可回延迟 = `min(2,4) = 2` ⇒ `reply_window_rounds=4` 在本配置下是 **dead parameter** | 已证实（源码事实 + E1 一致） | 本报告 §2.3 | TODO（文档随提交变动） | TODO | 见 E3 + E4 + E5 |
| 18 | **E7** 31.9%（153/480）回复恰落在 `t+2` 边界 ⇒ 晚回需求稳定存在（「没人想晚回」不成立） | **仅描述 / 方向性观察（无可用带）** | 同 E1 | `f8c58d95…` | `f8c58d95` | 同 E1 |
| 19 | **E8** 「因超窗未被回复」的消息数 | **未验证**（日志无「被看见但未回」轨迹） | — | — | — | 需给 `_pick_reply_target` 加计数器后重跑 |
