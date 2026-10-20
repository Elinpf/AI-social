# G 系列 · 闲话八卦（第三方提及）—— 设计说明与**预注册**判定口径

> 作者：模拟实现工程师（`engine/kernel` 实现者）｜日期：2026-10-20 18:10 (+08:00)
> 本轮维度：勘测第一名「闲话八卦 / 第三方提及」（`artifacts/recon/round-recon.md` §7 🥇），由 Leader 指定，不换题。
> 状态：**§1–§6 已完成（零 LLM 复算，基线已落盘）**；§7 的 A1 措辞改动与 A1 跑批**待 A0 跑批结束后串行执行**。
> 分层标记：【事实】／【读数】／【判断】／【预注册】／【未完成】

---

## 0. 一句话

【判断】当前小镇居民之间**几乎不谈第三方**（v0-anchor 187 条消息里只有 2 条提到不在场的邻居，且这 2 条都是"旁白句式"的副产品）。"背后说人"是"过日子"最典型的社会行为，而它在 AI 小镇是**近乎缺席**的——这是一个**尚未被 R4 七维覆盖**的空白（F-2b 只测"线程内标签数 ≥2"，不测人）。

---

## 1. 设计说明（改什么、为什么、预期在指标上如何体现）

### 1.1 现状机制（【事实】，读码得出）

`code/life/agent.py` 的两处措辞装配函数（改造前逐字）：

| 函数 | 行号 | 改造前指令文本（尾句） |
|---|---|---|
| `_dialogue_prompt` | `code/life/agent.py:988-994` | `\n请用一句话自然地说点什么。` |
| `_reply_prompt` | `code/life/agent.py:996-1005` | `\n请接着说一句。` |

两处都**没有**任何"可以提到别人"的出口。`_relation_line()` 只把**当前对话对象**的名字喂进提示词（`_dialogue_prompt` 的 `对象：{others}`）。⇒ 模型没有任何线索知道"镇上还有别人、可以说他们的事"，也让"提别人"这件事在**提示词层面不可达**。

【判断】这不是"措辞不够生动"，而是**输入里没有第三方这个概念**。因此本维度的改动属于「补一个机制」而不是「调一句措辞」。

### 1.2 设计假设（可证伪）

**H1**：在提示词里给出一份**可引用的真人名单**（不含自己、不含当前对话对象），并要求"可以顺口提一句别人最近的事；不确定就别编"，会让 `G-1 第三方提及率` 相对基线上升。

**H2（反向风险，必须同时验）**：若模型把"提别人"的实现方式退化为**旁白/括号**（如 `（巧儿想起老石…）`），则 `L-2 旁白率` 同步上升 ⇒ 本次改动是「用旁白换闲聊」，**不算改善**。

**H3（最需要防的污染）**：若模型编出不存在的邻居或不存在的事件，`G-1b 越界提及率` 上升 ⇒ **世界观污染**，其优先级**高于** G-1 的任何好看读数（沿用 R4 §3.2 第 3 条纪律）。

### 1.3 预期在指标上的体现

| 指标 | 期望方向 | 说明 |
|---|---|---|
| G-1 第三方提及率 | **↑** | 主指标，per-message，分母 187（两臂同规模） |
| G-1b 越界提及率 | **不应显著 ↑** | 一票否决项，逐条人核 |
| L-2 旁白率 | **不应 ↑** | 守卫项（防旁白化冒充闲聊） |
| L-8 裸 ID 率 | **不应 ↑** | 守卫项（防 `P0xx` 冒充人名） |
| U8b 8-gram 共享率（重复） | **不应 ↑** | 守卫项（防"每句都提老石"变成套路） |

### 1.4 失败判据（**先于读数固定**）

本轮改动的**失败**（= 这个改动没效果，应回退或换实现）定义为下列任一成立：

1. **F1** `ΔG-1 ≤ +10.6pp`（落在 n=170 档 B2 带内）⇒ 只能写「带内，仅印象」，**不得称改善**。
2. **F2** `ΔG-1 > +10.6pp` 但 `ΔG-1b > 0`（出现新的越界提及）⇒ **判失败**：以世界观污染换热闹，直接回退。
3. **F3** `ΔG-1 > +10.6pp` 但 `ΔL-2 > +10.6pp`（旁白率同步显著上升）⇒ **判失败**：用旁白换闲聊（R4 §3.2 第 1 条）。
4. **F4** 两臂分母差 >30%（消息量塌缩，如 187 → <131）⇒ **该指标不可比**，本轮不出对比结论，只报 E-1。
5. **F5** G-1 的全部新增命中都集中在同一个被提及对象（如新增 8 条里 8 条都是"老石"）⇒ 判为**模板化套路**，需在报告里单列，不算生活气息改善。

---

## 2. 度量口径（定义 / 分子分母 / 单位 / 样本下限 / 去噪）

脚本：`experiments/gossip-third-party/g_metrics.py`（只读、零 LLM、确定性）。

### 2.1 G-1 第三方提及率（per-message）

- **分子** = 正文中出现的「居民主干名」里**至少有一个属于第三方集合**的消息条数。
- **第三方集合** = 全部 20 个居民主干名（`code/config/personas.json` 的 `display_name` 按 `·` 取主干） − 本条发送者 − 本条线程的 `participants`。
- **分母** = 该 run 全部 `MSG_DM / MSG_PUBLIC / MSG_GROUP` 条数（v0-anchor = 187）。
- **统计单位** = per-message。
- **去噪三条（写死）**：
  1. 排除"提到自己在场伙伴"——已由 `− participants` 实现（否则只是称呼率提升的别名）。
  2. 名字匹配用**主干名子串包含**、不做分词（与 `tools/d5/dialogue_metrics.py` 同口径，保证可复算）；重名在每次运行时重新校验，**重名即 fail-loud 退出**（当前 20 人重名 = 0）。
  3. `participants` 的来源分层记录：`thread_schema=explicit`（D2 起，读 `payload.participants`）/ `legacy`（v0，按渠道近似：DM={发送者,收件人}，GROUP/PUBLIC={发送者}）。legacy 近似**宁可少排除、不虚增第三方**。两臂 schema 不同时，报告必须标注。
- **样本量下限**：n ≥ 68 才有可用 B2 带（`v2/evidence/D3-noiseband-two-level.md`）；v0-anchor 分母 187 ⇒ 落 **n=170 档 ±10.6pp**，**可判定**，不是 probe。

### 2.2 G-1b 越界提及率（per-message，**优先级最高**）

- **分子** = G-1 命中消息中，**任一提及者**在同一 `round` 的位置 ≠ 本条消息 `place` 的条数。
- **分母** = 全部 MSG 条数（与 G-1 同分母，便于并排看）。
- **位置来源** = `PLACE_ARRIVED` / `PLACE_MOVE` 事件的 `payload.place`，按 `(round, agent_id)` 建索引。
- **宁漏不虚增**：本条 `place` 为空（`MSG_PUBLIC` 的 `place` 一律 null）⇒ 记 `unknown_place_base`；位置索引查不到 ⇒ 记 `unknown_place_lookups`；**两者都不计入越界**。
- **对账**：脚本同一次运行还按 `tools/d5/dialogue_metrics.py::F-7a` 的原始规则复算一遍（提及任意非发送者名字 + 位置不符），用于证明与既有口径**同源**。v0-anchor 上二者均为 **2/187 = 1.07%**，与 `d5_metrics_v0anchor.md` 的 `F-7a=1.07%` **完全对上**。

### 2.3 G-2 闲话传播链（per-topic-cluster，条件可用）

- **分子** = 同一 `topic` 被 **≥3 个不同 agent** 先后提及的簇数；**分母** = 有非空 `topic` 的簇数。
- v0-anchor **无 `topic` 字段** ⇒ `applicable=false`，不出比率（A0 起 `ctx.topic` 才有值，故 G-2 只报后臂一侧，不参与前后差——同 R1 §2.4 对"往复对数"的处理）。

### 2.4 守卫指标

`L-8 裸 ID 率`（命中 `P\d{3}` / 全部 MSG）、`L-2 旁白率`（首字符为 `（`/`(` / 全部 MSG）、`L-3 括号块率`（任意位置含括号块 / 全部 MSG）。三者与 G-1 **并排报**，不单独下结论。

---

## 3. 预注册判定（**写于任何 A0/A1 读数之前，不许事后找补**）

| 项 | 预注册内容 |
|---|---|
| 判据来源 | `v2/evidence/D3-noiseband-two-level.md` 第 16 行：**n=170 ⇒ ±10.6pp**（v0-anchor 分母 187，按该文档第 65 行「分母 150–190 用 n=170 档并注明」取用） |
| 带外条件 | `\|Δ\| > 10.6pp` **且** `\|Δ\|` 大于两臂合并的 Wilson 95% CI 覆盖范围 |
| 带内后果 | 只能写「**带内，仅印象**」，不进摘要、不进结论要点 |
| 一票否决 | G-1b 出现新增越界提及 ⇒ 无论 G-1 多好看，本轮判失败（F2） |
| 必须并列 | 报 G-1 时必须同时报 L-8、L-2、U8b（防"用称呼/旁白/套路换闲聊"） |
| 不可比 | 两臂分母差 >30% ⇒ 不出对比结论（F4） |
| 无 A1 时 | 只报基线 + 新口径 + G-1b 事实，**不得出现任何"改造后"数字** |

---

## 4. v0-anchor 基线读数（已落盘，零 LLM）

【读数】输入 `v2/evidence/run_d2_before_n16_seed42/run.jsonl`（sha256 `c1f86bf6…`，186,972 行，`n_msgs=187`，`thread_schema=legacy`）：

| 指标 | 读数 | 分母 | 单位 | 证据级 |
|---|---|---|---|---|
| **G-1 第三方提及率** | **2 / 187 = 1.07%**（CI 0.29–3.82） | 187 | per-message | evidence（n=170 档可用） |
| **G-1b 越界提及率** | **2 / 187 = 1.07%** | 187 | per-message | evidence |
| G-2 闲话传播链 | `applicable=false`（无 topic 字段） | — | per-topic-cluster | 不可算 |
| L-8 裸 ID 率 | 29.95% | 187 | per-message | 守卫 |
| L-2 旁白率 | 64.17% | 187 | per-message | 守卫 |
| L-3 括号块率 | 64.71% | 187 | per-message | 守卫 |
| F-7a 对账复算 | 2 / 187 = 1.07% | 187 | per-message | **与 d5 定稿一致** |
| 被提及对象分布 | `{老石: 2}` | — | per-mention | — |

【读数】两条命中原样（全量明细见 `g_metrics_v0anchor.json` 的 `_hits`）：

- `seq=86116` round=54 place=`community_center`：「（压低声音）嘘——**别告诉老石**，我把那块废木头雕成了小兔子，送你啦。」
- `seq=116262` round=63 place=`park`：「（巧儿蹲在废料堆边翻找，抬头冲三人笑）哎你们说，这块破木头要是雕成小木马，会不会比**老石师傅**的还招人疼？」

【判断】这两条很有意思：它们**语义上正是标准的"背后说人"**（"别告诉老石"、"比老石师傅的还招人疼"），但**形式上都是括号旁白起句**。说明当前的第三方提及不是"机制产生"的，而是**旁白化生成方式的副产品**——旁白给了模型一个"站在外面描述"的位置，人名字才顺带被说出来。这直接支撑 H2 的反向风险：如果只靠旁白来"提别人"，读数会上去但那是假的生活气息。

【判断 · 必须克制】G-1 = 2/187 是**极小分子**。CI 0.29–3.82% 很宽。因此本轮**能说的**是"基线极低、且两条都是旁白副产品"这一**事实级**判断；**不能说的**是"居民不谈第三方"这种普遍化表述的强度——只能说"在这一个 seed、一个模拟周、187 条消息里，只观测到 2 条"。

---

## 5. 与既有口径的关系（不另起一套）

| 本维度 | 复用/依赖 | 关系 |
|---|---|---|
| G-1 | `v2/evidence/d3_corpus_annotate.py` 的名字表加载法（`personas.json` 主干名） | 同一名字来源，同口径子串匹配 |
| G-1b | `tools/d5/dialogue_metrics.py::F-7a_offscreen_mention` | **兼容但不相同**：F-7a 不排除 `participants`；G-1b 排除 ⇒ G-1b ⊆ F-7a。基线两者恰好相等（2/187），因为两条命中都不是"在场的伙伴" |
| 守卫 | `d3_corpus_annotate.py` 的 U4（裸 ID）/ U2（旁白）/ U8b（8-gram） | 直接复用判据，不新写 |
| 判定带 | `v2/evidence/D3-noiseband-two-level.md` | 直接引用 n=170 档 |

---

## 6. 限制（不藏）

1. **分子极小（2）**：基线太低是"可判定但难有弹性"——A1 只要新增 ≥20 条就能明确超带；但若新增 0–15 条，会落在"带内"，届时只能写"带内，仅印象"。
2. **per-message 口径不区分"真八卦"与"顺口带名"**：本口径只测"提了别人"，不测"说的内容是否为关于他的事"。语义层需 judge（本轮不做，标 `proxy`）。
3. **legacy participants 近似**：v0-anchor 无线程字段，DM 按 `{发送者,收件人}` 近似；若某条 DM 实际是三人以上小圈子，会被误判为"第三方提及"。已在输出里标 `thread_schema`，A0/A1 为 `explicit` 无此问题。
4. **单 seed、单模拟周**：与全族一致，不外推。
5. **G-1 升高不等于用户会觉得"有生活气息"**：必要非充分（同 R4 §5 第 5 条）。

---

## 7. A1 实现计划（**待 A0 跑批结束后串行执行**）

【未完成】本节内容**尚未落地**，写下的是**已冻结的范围**：

- **只改**：`code/life/agent.py` 的 `_dialogue_prompt`（:988-994）与 `_reply_prompt`（:996-1005）两个函数的**指令尾句**。
- **复用**：`v2/refs/D4-prompt-candidates.md` §6 的 **C15（闲话/第三方转述）** 候选，不另写一套措辞。C15 原文要求：「可以提一嘴别人最近的事（谁家…），但不确定就别编」+「只许转述**你真看见/听见过**的事件」。
- **不碰**：`config/**`（含 `policy.json` 经济/`lifecycle` 数值）、`code/engine/**`、`code/orchestration/**`、任何世界层数值与 `state_hash`。
- **开关化**：新增一个仅影响提示词文本的开关（默认 OFF，`run_override`/env 打开），保证 A0 与 A1 只差提示词文本，其余逐字节一致；交付里给 `prompt_sha(A0) ≠ prompt_sha(A1)` 与 diff 行号区间。
- **跑批**：`bash tools/d2/run_batch.sh --out-dir experiments/gossip-third-party/run_a1_n16_seed42 --seed 42 --agents 16 --rounds 84 --side-root /tmp/gossip_a1_side`，**排在 A0 之后串行**，跑前跑后各保留一次 `python3 -m obs llm-cost --require-provider openai_compat` 的原始输出。
- **若时间不够**：按 Leader 指示，交「脚本 + 基线 + G-1b 事实 + 待跑 A1」，**不编数字**。

---

## 8. 复算方法（任何人可重跑）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# 基线（本文件 §4 的所有数字都由这一条命令产出）
python3 experiments/gossip-third-party/g_metrics.py \
    --run v0anchor=v2/evidence/run_d2_before_n16_seed42/run.jsonl \
    --out-json experiments/gossip-third-party/g_metrics_v0anchor.json \
    --out-quotes experiments/gossip-third-party/g_quotes_v0anchor.md

# 两臂对照（A0/A1 落盘后）
python3 experiments/gossip-third-party/g_metrics.py \
    --run A0=v2/evidence/run_d2_after_n16_seed42/run.jsonl \
    --run A1=experiments/gossip-third-party/run_a1_n16_seed42/run.jsonl \
    --out-json experiments/gossip-third-party/g_metrics_pair.json \
    --out-quotes experiments/gossip-third-party/g_quotes_pair.md
```

原始 stdout 逐字留档：`experiments/gossip-third-party/out_v0anchor.stdout.txt`（含命令行、`git_HEAD`、输入 sha256、脚本 sha256、耗时）。
