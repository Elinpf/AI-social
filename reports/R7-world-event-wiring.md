# R7 · 世界事件接线诊断：剂量 → 触发 → 影响面 → 是否进对话

> **状态：骨架版（读数未到齐）**。本文件第 1–2、6–9 节已写实并绑 sha；**第 5–6 节（A/B 对照读数 / 截图）已补齐为「空表 + 逐格定义 + 复算命令」脚手架**（§5.1.1 / §5.6 / §6），但**不含任何实测数字**——两臂真跑批（t4）落盘后才允许填数。
> 空位一律标【待 t4 落盘】，**不含任何占位结论**；`N_world=6 / M-0 分母 24 / M-1 分母 64` 是按 60 回合口径的**预登记值**，填表时须用真实日志复核。
>
> 作者：report-writer（报告与交付编辑）｜2026-10-20
> 诊断正文（源文档，已入库同批）：`v2/evidence/D8-world-director-diagnosis.md`（`aba26406`，含 22:34 时间窗更正）
> 判据（先写后取数）：`v2/evidence/D8-preregistration-world-director.md`（`f6685001`）
> 字段级判据卡：`v2/evidence/D8-mention-criteria-card.md`（`4eddf77e`，含 R1–R8；**已冻结终版**，Leader 先前给的 `9b20e740` 为旧值）
> 代码身份（两个 sha，用途不同，别只写一个）：
> - **`dff515d`**（`dff515da3af282d04a0c4b187fb68b5c1f14743d`）= **master HEAD**（22:24:33 外部会话提交的 R2 meta-sha 登记，非本轮产物、非本报告作者所为，见 §附 诚实边界 7）
> - **`2090287`**（`2090287809ae307614b3f9b2f62e7619f2142ea8`）= **A 臂基线 / 分支基线**：本报告 §2 全部代码判据（行号）均以此 sha 为准复核
> A0 臂数据：`v2/evidence/run_d2_after_n16_seed42/`，`run.jsonl`（`643f13a5`）194,108 行 / `meta.json`（`5fe058f3`），16 agents × 84 rounds × seed 42，真 LLM（`obs llm-cost` `provider_guard.ok=true`，`calls=3403`）

---

## 0. 方法学与纠错清单（**读结论前先读这节**）

> **本轮真正的工作量在把口径钉死上，不在跑批本身。** 跑批是确定性的、几十分钟就出；口径错一次要花几轮返工才能纠回来，而且**错的样子几乎都对**。

### 0.1 硬规则（格式要求，不是建议）

> **任何分母必须在本行内写出单位与推导式。写不出单位的比率不许进报告。**

示例（合格写法）：

| 指标 | 分母（含单位与推导式） |
|---|---|
| `M-0` | `分母 = 存活 agent 数 × 世界实体数 = 4 agent × 6 实体 = 24`（单位：`(agent, directive)`） |
| `M-0_w` | `分母 = 存活 agent 数 × Σ每实体有效期回合数 = 4 × 36 = 144`（单位：`(agent, directive, round)` 三元组） |
| `感知覆盖率` | `分母 = 每 directive 有效期回合数 = 6`（单位：回合/实体）；分子 = 可感知回合 3 ⇒ `3/6` |

**为什么必须是硬规则**：本轮"单位混用"出现**两次，两个都长得很像对的**——
- `M-0_w` 分母把 `(agent, round)` 当 `(agent, directive)`：`4×18=72` vs 正确 `4×36=144`
- `M-0` 上界把 `agent-round(12)` 当 `agent-directive(24)`：0.5 vs 正确 **1.0**

两次都不是算术错，**是"单位没写在分母旁边"**。靠"记得检查单位"防不住，只能靠"必须写出来"防住。

### 0.2 本轮纠错清单（六条，每条一句 + 后果）

| # | 错误 | 后果 |
|---|---|---|
| 1 | **分母单位混用（两次）**：`M-0_w` 把 `(agent,round)` 当 `(agent,directive)`；`M-0` 上界把 `agent-round` 当 `agent-directive` | 上界 0.5 vs 1.0、分母 72 vs 144，比率连同结论一起错 |
| 2 | **成对双记**：`WORLD_DIRECTIVE` 与 `WORLD_GROUP_EVENT` 1:1 成对出现 | 分子分母同时翻倍，比率"看起来"没变、绝对数全错（本报告 48 agent-回合 = 96 次事件-观测即此） |
| 3 | **可见性路径取错**：用了 `contracts.visible_events`（无窗）而非真实跑批路径 `VisibilityIndex(window_rounds=2)` | 曝光 864 → 实际 **48**；"过期后永久可见"只对 L6 那条成立 |
| 4 | **`zero_nature` 两臂复用**：A 臂「结构性 0」与 B 臂「未观测到」被压成同一常量 | 读数表撒谎：把"代码必然"与"观测事实"混为一谈（见 §5.1 陷阱） |
| 5 | **剂量跨行套用曲线**：拿 conservative 的 1.8% 手乘 2，而非从 360bp 直接乘 2 | 期望 3.0 vs 正确 **6.048**；12 回合 `P(≥1)` 13% vs 正确 57.9% |
| 6 | **感知覆盖率 50% 被误当 `M-0` 上界 0.5** | 两个不同指标互相代入，`M-0` 被系统性低估一半 |

> **这份清单比结果更有复用价值**：它记录的不是"我们算错了"，而是"这类错误长什么样"。下一轮开工第一件事是把这六条对着自己的表自查一遍。

---

## 1. 一句话结论

**世界层事件对居民对话零暴露，且这是「运行实测 + 静态必然」双证**：A0 批 84 回合只发生 1 条世界指令（`conservative` 曲线下 Poisson 期望 0.966，属正常下尾抽样），它确实进入了每个 agent 的视野——但**只在 round 30/31/32 三个回合内**（真实感知路径 2 回合滑窗，曝光 = 16 agents × 3 回合 = 48 个 agent-回合），随后在 `code/life/agent.py:41-45` 的观察白名单处被整类丢弃 ⇒ 精确引用世界事件 seq 的 `MEMORY_WRITE` / `OBSERVATION` 均 **0 条**；两个提示词装配函数（`agent.py:1050-1058`、`1060-1069`）里**没有任何世界状态行**，检索输入也不含世界维度 ⇒ 世界事件不存在进入对话的路径。**这条链不是"效果不好"，是从第 3 环起就断了，第 5 环连管道都没有。**

- 本轮代码 sha：`2090287`（`master`，诊断与判据均绑定此 sha）
- 分支实现：`feat/world-event-dose`（工作树基于 `2090287`，**截至写作时该分支尚无提交**，改动在工作树中，见 §4）——提交 sha【待 d-dim-impl 落库后补】
- A/B 验证批 sha：`【待 t4 落盘：两臂 meta.json 的 code_sha / run.jsonl sha8】`

### 1.1 本轮最强的一句定位（已按 repo-scout 22:34 更正限缩）

> **三条路径不同源不同界**：`world_params` 有 `[start,end)` 有效期窗口；真实感知路径（`KernelAdapter.perceive` → `VisibilityIndex.visible(window_rounds=2)`）有 **2 回合滑动窗口**；唯独 L6 走的 `contracts.visible_events`（`life/settlement.py:620` 调用）**没有任何时间维**。

三条路径逐条：

| 路径 | 入口 | 时间维 | 判据 |
|---|---|---|---|
| 传导（世界参数） | `engine/world_params.py::world_params()` | **有**，严格 `[start_round, end_round)`，过期即从 `active` 移除 | `world_params.py:38-41` 的 `start<=t<end` |
| 真实感知（居民看得到） | `KernelAdapter.perceive` → `visibility_query` → `VisibilityIndex.visible(window_rounds=VISIBLE_WINDOW_ROUNDS)`，`VISIBLE_WINDOW_ROUNDS=2` | **有**，滑动窗 `(upto-2, upto]` | `orchestration/integration.py:275/322-346`、`visibility_index.py:146` |
| L6 记忆写入路径 | `life/settlement.py:620` → `life/visibility.py::visible_events` → `contracts/visibility.py::visible_events`（`window_rounds` 默认 `None`） | **无** | `grep -n "start_round\|end_round\|expires" code/contracts/visibility.py` 空输出（rc=1） |

> ⚠️ **写作纪律**：不得把这句话写成"感知层整体没有时间维"——那是错的（真实 perceive 路径有 2 回合窗），会被当场抓住。准确说法只有上表这一句。

**这句话为什么重要（本轮真正的"生活气息"缺口）**：directive 的 `dose.slots=6` ⇒ 有效期 6 回合，而真实感知窗只有 3 回合 ⇒ **可感知覆盖率 = 3/6 = 50%**。即在 `+3..+5` 三个回合里，世界参数**仍在 `world_params.active` 里起作用**（影响 `activity_weight` 等），但**居民已经看不见这件事**。世界在变，居民感知不到变化——这与"世界事件进不了对话"是**两个独立缺口**，不能混为一谈。

---

## 2. 世界导演链路诊断（L1–L6）

> 预注册判据见 `D8-preregistration-world-director.md` §2；下表"判定"列一律按该文件写死的判据给出，取数后未改判据。

| 环节 | 代码位置 | 实测读数 | 命令（可粘贴） | 判定 |
|---|---|---|---|---|
| **L1 剂量** | `code/engine/world_director.py:20-24`（DOSE_CURVES）、`:45-58`（resolve_dose） | 3 个 enabled 机制在 `conservative` 曲线下合计 **E=0.966**，实测 **N=1**；E<1 ⇒ 稀有事件 | `cd code && python3 -c "import json;from engine.world_director import *;cfg=cfg_of({'world_director':json.load(open('config/world_director.json'))});..."`（全文见 §9 ①） | **剂量过低（配置问题，非 bug）** |
| **L2 触发** | `code/engine/world_director.py:74-110`（rng_branch / plan_directives） | 84 回合 × 3 机制复算触发集 `[(30,'wd.tension',8)]` == 日志触发集，**逐条全等**；`WORLD_DIRECTIVE_REJECTED` = 0 条 | §9 ① | **接通** |
| **L3 影响面** | `code/engine/hooks/world_director.py:45-49`（`:48`） | `affected_scope_count` 恒为字面量 `0`；全仓唯一写入点、无解析代码 | `grep -rn "affected_scope_count" code --include=*.py` | **未接通（字段从未被计算）** |
| **L4 感知（暴露）** | `code/contracts/visibility.py` + `code/config/perception_scope.json` + `KernelAdapter.perceive`（`integration.py:275/341`） | 世界事件进入 `visible_events`（P001/P009/P016 实测）；**真实路径（2 回合滑窗）曝光 = round 30/31/32，16 agents × 3 回合 = 48 个 agent-回合 = 96 次"事件-观测"**（每回合 2 条世界事件） | §9 ③ | **暴露=真（但只在一个 3 回合窗口内）** |
| **L4′ 沉淀** | `code/life/agent.py:41-45`（`_SALIENT_EVENTS`）、`:395-418`（`:403` 过滤） | 精确引用世界事件 seq 的 `MEMORY_WRITE`=0、`OBSERVATION`=0（子串 `grep -c '39222'` 的 28 行是 `MEMORY_FORGET` 数值巧合，**不算命中**） | §9 ② | **未接通（白名单过滤）** |
| **L5 对话** | `code/life/agent.py:1050-1058`、`:1060-1069`、`:444-449` | prompt 装配串无世界行；`refs` 命中 0；检索 query 三段均与世界无关 | §9 ④ | **未接通（零暴露）** ← 本轮最重要一句 |
| **L6 消费** | `code/life/agent.py:593-612`（读）、`:614-630`（唯一消费）、`engine/world_params.py:45-59` | 仅 `activity_weight` 被功能消费（而 festival 84 回合 0 次触发）；`market_scarcity_bp` 只参与"是否非空"布尔 | §9 ⑤⑥ | **基本未接通** |

### 2.1 三层"零"必须分列（不许写成同一件事）

| 读数 | 零的性质 | 为什么是这个性质 | 能不能靠"多跑几批"变非零 |
|---|---|---|---|
| `affected_scope_count = 0` | **结构性** | `hooks/world_director.py:48` 是 Python 字面量 `0`，压根没有计算代码 | **不能**。跑到天荒地老还是 0 |
| 世界事件沉淀 = 0（M=0, O=0） | **结构性** | `_SALIENT_EVENTS` 白名单不含 `WORLD_DIRECTIVE`/`WORLD_GROUP_EVENT`，`:403` 必丢弃 | **不能**。除非改白名单 |
| 对话提及 = 0（M-1） | **未观测到** | 窗口内 686 条 MSG 中词表命中 0 —— 这是**观测事实**，不是代码必然（理论上存在"居民自己说缺货"的可能） | **能**。分母够大时可能出现，但当前 0 命中不能证明"不可能" |
| 窗口外提及 | **仅窗口外** | 本批未出现该情形（窗口内已 0 命中）；若 B 臂出现"窗口外才提到"，按下表注记单列 | 不适用（本批） |

> **纪律**：三种零若写成同一句话，读者会误以为"都是缺数据"，从而得出"再跑一批就好了"的错误结论——而其中两个零是代码结构决定的，跑多少批都不会变。

### 2.1.1 感知覆盖率：独立指标，不许与上表混用

| 指标 | 分子 / 分母 | 值 | 含义 | 上界 |
|---|---|---|---|---|
| **感知覆盖率**（per directive，回合口径） | 可感知回合 3 / 有效期回合 6 | **3/6 = 50%** | `dose.slots=6` ⇒ 有效期 `[issued, issued+6)`；真实感知窗 `[r-2, r]` ⇒ 只有 `+0/+1/+2` 可见，`+3/+4/+5` 不可见但仍在 `world_params.active` 里起作用 | 50% |
| **M-0**（entity 口径，"是否曾知道"） | 命中的 (agent, directive) 去重数 / (存活 agent × N_world) | 【待读数】 | 每个 agent 有 3 个回合机会知道，去重后 1 条即算命中 | **1.0**（=24/24），**不是 0.5** |
| M-0_w（窗口口径，可选） | 命中的 (agent, directive, round) 三元组 / `n_alive × Σ有效期回合数` = 4×(6×6)=144 | 【待读数，非必报】 | 若报此列才允许出现 0.5 上界 | 0.5 |

> ⛔ **三套口径不得互相代入**：把"感知覆盖率 50%"当成"M-0 上界 0.5"是错的。M-0 上界 1.0 的静态依据见判据卡 R8.4：`_observe` 是 `for ev in wv.visible_events` 全量遍历，`:403` 只按 `_observed_seqs` 去重与 `_SALIENT_EVENTS` 过滤，**无每回合写入条数上限、无 salience 门限**，故 3 个可感知回合足以让每个 agent 各写 1 条。

### 2.2 方法学注记（两人交叉核验，必须留痕）

**「0 条 OBSERVATION 只能证明没沉淀，不能证明没看见。」**

batch-runner 在早期读数中把"0 条 OBSERVATION"直接读作"可见层断了"；repo-scout 用 §9 ③ 的纯函数复算指出：世界事件在 `visible_events` 里**确实存在**（P001/P009/P016 round 30 起可见），断点在**下游白名单**而非可见性。经两人交叉核验，本轮确立该口径并写入判据卡 §2 / 诊断 §5。

> 为什么值得单列：如果按错误口径走，会把修复方向指向 `visibility.py`（改可见性策略，风险高、改动大），而真实断点在 `agent.py:41-45` 的一行白名单（改动小、可开关）。**口径错一层，方案错一路。**

### 2.3 剂量的刻意抬高（必须原话写明）

A/B 验证批的剂量是**刻意抬高**的（`aggressive` 曲线 + 8 机制全开）。因此：

> **本轮研究对象是「接通性」，不是「自然发生频率」。** 抬高剂量只为了让"事件进对话"这件事有足够机会发生以便观测，**不得**被读作"我们建议把世界事件调密"。任何"提高剂量"的读法都不构成本报告的结论。

剂量期望的精确数值以分支实际 `config/world_director.json` 为准，填表时按 §9 ① 重算并写明曲线名，**不引用口头估值**。

**已知参考值（aggressive + 8 机制，B 臂预期配置）：`E = 720bp/回合 = 7.2%/回合 × 84 = 6.048 条`。**
Poisson 参考（λ=6.048）：`P(X=6)=16.1%`、`P(≥1)=99.8%`。12 回合下 λ=0.864、`P(≥1)=57.9%`——**不是"必然双零"，而是有 42% 概率一条都没有**。

> **方法学注记（本轮踩过的坑，写进来因为"这类错误长得特别像对的"）**
> 本轮曾出现把期望写成 `3.0` / 把 12 回合命中写成"P(≥1)=13%"的错误。根因是**跨行套用剂量曲线**：取了"conservative 下 3 机制合计 1.8%/回合"这个数，又手乘 2 当作 aggressive，而不是从 8 机制的 `360bp` 直接乘 2 得到 `720bp`。
> 正确路径只有一条：**先按 `resolve_dose()` 逐机制折算曲线后的 `prob_bp`，再求和，再乘回合数**；不要拿"某个子集的合计率"去做二次缩放。旁证：mock 短批实测 **6 条** `WORLD_DIRECTIVE`，与 6.048 吻合。

#### 2.3.1 剂量期望参考值（master 现状 config，实测复算）

| 曲线 | 3 个 enabled 机制 | 8 个 `prob_bp>0` 机制全开 |
|---|---|---|
| `conservative`（现网默认） | **E=0.966** | E=1.512 |
| `moderate` | E=1.932 | **E=3.024** |
| `aggressive` | E=3.864 | **E=6.048** |

（`wd.mass_event` 的 `prob_bp=0`，`prob_bp=0 ≡ 关闭`，故"8 机制"= `prob_bp>0` 的 8 个；`wd.season` 无 `prob_bp`，不参与概率剂量。）

---

## 3. 重大发现（优先级高于本轮主线）：`illiquid_no_credit_N` 在 84 回合内杀死 14/16 居民

> **为什么放在 A/B 之前**：这项发现决定"本轮主线值不值得跑"。人都活不过 84 回合，"小镇生活气息"无从谈起。

### 3.1 事实（原文数据，三份真跑日志逐条一致）

| 项 | 值 |
|---|---|
| 批规模 | 16 agents × **84 rounds** × seed 42（真 LLM） |
| 出生 / 死亡 / 存活 | **16 / 14 / 2**（`born=16 died=14 alive=2`） |
| 死因 | **14/14 = `illiquid_no_credit_N`**（同一 cause，无第二种死因） |
| 死亡回合集合 | **`[64,66,67,69,71,74]`**（6 个回合值，跨度 11 个回合；11 回合内死 14 人） |
| 死者 `liquid` 分布 | `[-270, -221, -215, -101, -101, -60, -52, 3, 40, 40, 54, 61, 121, 201]` |
| `liquid` 正 / 负 | **7 正 / 7 负**（正：`3,40,40,54,61,121,201`；负：`-270,-221,-215,-101,-101,-60,-52`）；若只算 `≥40` 则 6 正 |
| `count_c` | 多数为 3，r74 三人为 5 |
| 死亡前状态 | 全部 `from: near_death` |

**逐条清单（同一条在 before / after / r6 三份日志中完全同构）**

| round | agent | liquid | count_c |
|---|---|---|---|
| 64 | P001 | −270 | 3 |
| 66 | P002 | −60 | 3 |
| 66 | P004 | −221 | 3 |
| 67 | P003 | −52 | 3 |
| 69 | P011 | **+40** | 3 |
| 71 | P005 | −101 | 3 |
| 71 | P009 | **+3** | 3 |
| 71 | P010 | −101 | 3 |
| 71 | P012 | **+54** | 3 |
| 71 | P013 | **+40** | 3 |
| 74 | P006 | **+121** | 3 |
| 74 | P007 | **+61** | 5 |
| 74 | P008 | −215 | 5 |
| 74 | P014 | **+201** | 5 |

### 3.2 三份日志一致 ⇒ 与既有 treatment 无关

| 日志 | 死亡数 | `liquid>0` 死者 | `liquid≥40` 死者 | 死者集合与回合 |
|---|---|---|---|---|
| `run_d2_before_n16_seed42`（D2 前） | 14 | 7 | 6 | 与另两份**逐条相同** |
| `run_d2_after_n16_seed42`（A0 锚点，`643f13a5`） | 14 | 7 | 6 | 同上 |
| `run_r6_treat_n16_seed42`（R6 处理臂） | 14 | 7 | 6 | 同上 |

D2 两臂死亡数**相同**（14 vs 14），R6 处理臂也**相同** ⇒ **不是 D2/R6 的 treatment 造成的，是配置性结构缺陷**。

### 3.3 判断（一句话）

> **14 名死者中 7 人 `liquid` 为正（7 正 / 7 负）**——他们不是"没钱"，是被"**无信用**"这条路径批量收割（`illiquid_no_credit_N` + `count_c` 累积 + `near_death` 前置状态）。
>
> **最有力的单条证据**：`r74 P014` 死时 `liquid = +201`。账上还有 201 也被判死，直接排除"只是穷死了"的解释——问题在"无信用路径本身"，不在余额。**人都活不过 84 回合，"小镇生活气息"无从谈起，此项优先级高于世界事件接通。**

### 3.4 对本轮的直接后果：A/B 规模从 84 降到 60 回合

team-leader 裁定两臂 `rounds` 由 84 降为 60：**60 回合内无死亡污染（首死 r64），分母干净**。代价是 A/B 的泄漏量随之下降（见 §5.2 的 λ 重算）。**本节的死亡数据只用于说明"为什么改 60"，不用于 A/B 的任何读数。**

> ⚠️ **单位纪律**：本节所有绝对数都是 **16 agents / 84 rounds** 口径，**不得**与 §5 的 A/B 批（4 agents / 60 rounds）互相引用对方的绝对数。两个"48"是巧合，不是同一个数：
> - §2 的 **48 = 16 agents × 3 回合**（A0 批，1 条 directive 的 3 回合感知窗）
> - A/B 的 **48 = 4 agents × 2 record × 6 实体**（A/B 批，另一种统计单位）
>
> 二者**不可比较、不可相加**。

---

## 4. 分支实现改动清单（`feat/world-event-dose`）

> **代码身份**：分支 `feat/world-event-dose`，基线 `2090287`；下表行号为分支工作树实测行号（`git diff master` 对工作树）。
> **改动面**：**7 个已跟踪文件修改 + 4 个新增文件**（不是"收敛到 `agent.py` 三处"）。验收说明：开关传递链必须贯通 `contracts → engine → orchestration`，故接受该面。
> **总开关默认 `false`** ⇒ 与基线 `2090287` 逐项等价（不改提示词、不写记忆、MSG payload 不多键）。

### 4.1 核心层（**本轮实际生效的那部分**）

| 文件:行 | 作用 | 开关默认值 | 证据 |
|---|---|---|---|
| `code/life/agent.py:42-49`（`_SALIENT_EVENTS` 原有）+ `:409-436`（`_observe` 过滤点 `:414`） | 白名单**门控式开口**：`is_world = ev.type in WA.WORLD_EVENT_TYPES`；只有 `_wa_observe_on()` 为真才放行。`_SALIENT_EVENTS` **集合本身未改**（不是硬加两个类型） | `observe_enabled: true`（父开关 `enabled: false` ⇒ 实际关） | `git diff code/life/agent.py` |
| `code/life/agent.py:1344-1350`（`_describe_event` 新增分支） | 世界事件写记忆的**人话正文**（走 `WA.describe_event`），**不含 `WORLD_*`/`wd.*`/`directive_id`/`*_bp` 内部 token** ⇒ 直接消解判据卡 R5.2 的"token 泄漏"风险 | 随父开关 | 同上 |
| `code/life/agent.py:428-431` | 世界事件写记忆时给**确定性重要性下限**（`max(imp, importance_min=4)`），**不额外调 LLM** | 随父开关 | 同上 |
| `code/life/agent.py:371`（`_scan_world` 调用）+ `:644-705` | 每回合把**可见的**世界事件折成处境快照（纯函数、有界）；关闭时立即清空 ⇒ 零副作用 | 随父开关 | 同上 |
| `code/life/agent.py:1129-1160`（`_dialogue_prompt` / `_reply_prompt` 新增 `world_line` 参数） | 提示词**追加一行**「最近的镇上的事」；关闭/无候选 ⇒ `""` ⇒ 提示词**逐字等于基线** | `dialogue_enabled: true`（父开关关） | 同上 |
| `code/life/agent.py:661-671`（`_world_prompt_line`） | 取那一行并计数 `_wa_prompted` / `_wa_scarcity_prompted`（可诊断"真进提示词"次数） | 随父开关 | 同上 |
| `code/life/agent.py:672-687`（`_world_ctx_payload`）+ `:1037-1039`、`:1092-1094` | MSG payload **追加** `world_ctx` 键（`refs`/`kinds`/`scarcity`/`prompted`）作追溯；关闭 ⇒ `None` ⇒ **payload 不多一个键** | 随父开关 | 同上 |
| `code/life/world_awareness.py`（新增，`WORLD_EVENT_TYPES:38`、`load_params:90`、`enabled:135`、`observe_on:140`、`dialogue_on:146`、`brief_lines:165`、`scarcity_line:207`、`prompt_context:221`、`describe_event:248`） | 新模块：开关解析 + 处境句生成 + 人话描述；**不发事件、不改世界态、不进 `state_hash`** | — | 新增文件 |
| `code/config/world_awareness.json`（新增） | 开关档：`enabled:false`、`observe_enabled:true`、`dialogue_enabled:true`、`scarcity_in_prompt:false`、`world_window_enabled:false`、`window_rounds:24`、`max_lines:2`、`max_kinds:3`、`scarcity_min_bp:1000`、`importance_min:4`；**不进** `engine/version.py::FINGERPRINT_FILES` | 见左 | 新增文件 |

### 4.2 管道层（**已实现但本轮未启用 = 死代码**）

| 文件:行 | 作用 | 开关默认值 | 本轮是否生效 |
|---|---|---|---|
| `code/contracts/visibility.py:88-114`（新增 `world_event_in_window`）+ `:117-143`（`visible_events` 新增 `world_event_window` 形参，裁剪点 `:137-139`） | 世界事件 `[start,end)` 生效窗裁剪（与 `engine/world_params.py` 同口径）；缺时间字段视为在窗内（旧日志可读性保守） | `world_event_window=False` | **否** |
| `code/orchestration/visibility_index.py:141-155`（新增形参与裁剪点） | 同上，索引路径版本 | 默认 `False` | **否** |
| `code/life/visibility.py:37-51` | 透传 `world_event_window` | 默认 `False` | **否** |
| `code/engine/perceive.py:59-90`（新增 `world_event_window_enabled:74-85`） | 从 `config["world_awareness"]` 解析开关 | 缺省 `False` | **否** |
| `code/orchestration/integration.py:309-315`（组合根解析）、`:333-345`（`visibility_query` 透传）、`:184-190`（`_thread_fields` 追加 `world_ctx`） | 把开关从 config 贯通到索引；payload 字段只追加 | `False` | **否** |
| `code/engine/runner.py:33-36` | 读入 `config/world_awareness.json` 到 `cfg["world_awareness"]` | — | 读入但不生效 |

> ⚠️ **必须写清的一句**：`world_window_enabled` 本轮**保持 `false`**（真实路径已有 `window_rounds=2`，见 §1.1），所以 **§4.2 这层本轮是死代码**——它只是"是可选项、不是本轮自变量"。**读者不得把这层的存在理解为"它算出了什么效果"。**

### 4.3 回归风险问答：改 7 个文件有没有引入回归？

| 问题 | 回答 | 依据 |
|---|---|---|
| 原有 `window_rounds` 裁剪逻辑被改动了吗？ | **没有，一行没动** | `visibility_index.py` 的 diff 只有两处**新增**：形参 `world_event_window` 与一段 `if world_event_window and ...: continue`；原有 `if window_rounds is not None and rec["round"] < upto_round - window_rounds` 原样保留 |
| 默认关时行为与基线等价吗？ | **等价**（开关全关 ⇒ 空快照、提示词空串、payload 不多键、可见性裁剪不触发） | `agent.py:644-652` 关闭即清空并 return；`:1129+` `world_line or ""`；`:672-687` 返回 `None` |
| 新增开关会改变旧日志的 `engine_version` 指纹吗？ | **不会** | `world_awareness.json` **不进** `FINGERPRINT_FILES`（见该文件 `_comment`） |
| 有没有新增事件类型？ | **没有** | 只复用 `INTENT_OBSERVE` 既有通路；`_thread_fields` 只追加 payload 键 |

### 4.4 配套测试与脚本（新增文件中的另外两个）

| 文件 | 作用 | 本轮状态 |
|---|---|---|
| `code/tests/test_d8_world_awareness.py`（新增） | 开关语义（默认关 ≡ 基线）、门控放行、人话描述无机器 token、payload 不多键 | 【未完成·待 d-dim-impl 给出 pytest 输出】 |
| `v2/evidence/d8_tension_dose_recompute.py`（新增） | 剂量/期望复算脚本（`§9 ⑦′` 同口径） | 【未完成·待核实与 §9 命令是否同源】 |

## 5. A/B 对照读数表

> **批配置（两章单位不得互相引用，见 §3.4）**：**A/B 批 = 4 agents / 60 rounds / `aggressive` + 8 机制 / 720bp**
> 【待 t4 落盘】**判定口径：仅描述性，不作效果结论；小规模存在性臂，不构成频率估计（§5.0.2）。**

### 5.0 批配置与泄漏量（60 回合口径，不是 84）

| 项 | 值 | 说明 |
|---|---|---|
| agents / rounds | **4 / 60** | 规模由 84 降为 60（理由见 §3：首死 r64，60 回合分母干净） |
| 剂量曲线 / 机制 | **`aggressive` / 8 机制全开** | **刻意抬高**，研究对象是接通性（见 §2.3） |
| 每回合泄漏 | **720bp = 7.2%** | §9 ⑦′ 复算 |
| 60 回合期望 λ | **60 × 7.2% = 4.32** | `P(≥1) = 98.7%` |
| 两臂唯一差异 | **env `HITT_WORLD_AWARENESS=0`（A）/ `1`（B）** | 代码树、`world_director.json`（aggressive + 8 机制）、seed/agents/rounds/模型/端点两臂逐字相同 |
| （参考）84 回合期望 | 6.048 | **只作"若跑 84 回合"的参考，不是本批口径**，不得写进 A/B 任何读数 |

### 5.0.1 规模从 84 降到 60 的书证：A 臂重算**同值**

A 臂在 **60 回合**下的基线重算结果与 84 回合**完全同值**：

| 项 | 值 |
|---|---|
| `N_world` | **6** |
| 各实体可见记录对 | **`[8, 8, 8, 0]`** |
| 合计 `(agent, record, round)` 三元组 | **144** |
| 原因 | **6 条世界事件全部在 r50 之前发出**，且 RNG 按回合独立 ⇒ 截到 60 回合不丢任何事件 |

> **这句话就是"为什么不是 84 回合"的答案**：把 rounds 从 84 降到 60 **没有牺牲任何世界事件、不破坏可比性**，只是去掉了 r64 之后的死亡污染。

### 5.0.2 口径声明：**小规模存在性臂，不构成频率估计**（先写死，防事后外推）

- 本轮 A/B 是 **agents=4 × rounds=60 × seed=42** 的**小规模存在性臂**（依据 §3.4 与分支实现说明 §0），**不是**历史基准的 `n=16 × 84`。
- **分母性质**：两臂 `MSG_*` 分母将远小于历史基准 A0 的 **686**（`16 agents × 84 rounds`）。因此：
  - **只能判「世界事件是否进入对话」的存在性事实（0 → 非零，或仍为 0）**；
  - **不得给比率结论**，不得写「X% 的消息提及世界事件」这类率式表述；
  - **不得与 686 分母的任何读数并列比较**（分母口径不同，跨分母比较=R6 已纠过的错误）。
- 报告正文固定写一句：「**本批为小规模存在性臂，`MSG_*` 分母 N=<填实测值>，不构成频率估计。**」
- 两臂除 env 开关 `HITT_WORLD_AWARENESS=0/1` 外**代码完全相同**；剂量 `aggressive` 为**刻意抬高**（720bp/回合，60 回合 Poisson 期望 λ = 60×7.2% ≈ 4.32 条 directive）——研究的是**接通性**，不是自然频率。这两点必须同时出现在方法说明与结论旁。

### 5.1 读数表（列含「零的性质」，见下）

> **状态：脚手架（等 t4 两臂 run 目录落盘后填数）。** 下表每一格「该填什么 / 从哪个字段取 / 用哪条命令算」见 §5.1.1；**未拿到 run 目录前不得预填任何数字**。
>
> ⚠️ `N_world` / `M-0 分母=24` / `M-1 分母=64` 是**按 5.0.1 的 A 臂重算在 60 回合口径下的预登记值**，t4 落盘后必须用真实日志再核一遍；若实际与预登记不一致，以日志为准并在表下注明差异（不得沿用预登记值）。

表列（判据卡 §5 + 本报告加的 `zero_nature`）：`arm | N_world | world_seqs | M-0 分子 | M-0 分母 | M-1 分子 | M-1 分母 | visibility_window | L-2 旁白率 | 词表 sha8 | zero_nature | 判定`

| arm | N_world | world_seqs | M-0 分子 | M-0 分母 | M-1 分子 | M-1 分母 | visibility_window | L-2 旁白率 | 词表 sha8 | zero_nature | 判定 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A（开关关，对照臂） | 待填（预登记 6，须日志复核） | 待填 | 待填 | 待填（预登记 24） | 待填 | 待填（预登记 64） | 待填 | 待填 | 待填 | **结构性**（须 `--whitelist off`） | 待填 |
| B（开关开，处理臂） | 同上（两臂剂量逐字相同） | 待填 | 待填 | 待填（预登记 24） | 待填 | 待填（**须现算**，不得抄 A 臂） | 待填 | 待填 | 待填（须与 A 臂同值） | **未观测到**（若为 0；须 `--whitelist on`） | 待填 |

#### 5.1.1 逐列定义与复算命令（填表时逐格对照，禁止凭印象填）

| 列 | 口径 / 单位 | 取自字段 | 复算命令（仓库根执行） |
|---|---|---|---|
| `N_world` | 唯一 `directive_id` 去重后的世界事件条数（`D-` 与 `GE-` 成对算 1） | `d8_metrics.py` 的 `layer1_occur` / `N_world` | `python3 v2/evidence/d8_metrics.py --log <run>/run.jsonl --label <ARM> --whitelist <on|off> --out-json /tmp/<ARM>.json` |
| `world_seqs` | 世界事件在日志里的 `seq` 列表 | `world_seqs` | 同上；或读上面 json 的 `world_seqs` |
| `M-0 分子` | 只认 `MEMORY_WRITE.source_event_seq` 指向世界事件 seq 的条数（per `(agent,directive)` 去重，**不是** per message） | `layer3_M0_dedup`（主判据）；`layer3_M0_raw` 仅备查 | 同上 `d8_metrics.py` 输出 |
| `M-0 分母` | `存活 agent 数 × N_world`（单位 `(agent, directive)`），本批预登记 `4×6=24` | `layer3_M0_denom`（含 `_alive_end` / `_window` 变体） | 同上；同时复核 `n_alive_agents` 必须 = 4（60 回合无死亡） |
| `M-1 分子` | 剔除括号旁白后命中冻结词表的 `MSG_*` 条数（**词表代理**，与真引用分列不加和） | `layer4_M1_num_msgs`；并列看 `layer4_real_ref_msgs`（真引用） | 同上；两臂**必须各跑一次**，不得复用 |
| `M-1 分母` | 窗口内全部 `MSG_DM/MSG_PUBLIC/MSG_GROUP` 条数（per-message）；预登记 A 臂 64 | `layer4_M1_denom_msgs` | 同上；**两臂各自现算**，若两臂分母差 >30% ⇒ 判「不可比」，只报事件数 |
| `visibility_window` | 世界事件对 agent 可见的回合区间（真实路径 `VisibilityIndex(window_rounds=2)`），写成 `[起,止)` | §9 ③ 复算；`perception_coverage_rounds` | `python3 v2/evidence/d8_metrics.py ...` 输出 `perception_coverage_rounds` |
| `L-2 旁白率` | 括号旁白被剔除前后的比率代理；**只作参考，不作效果结论** | `L2_narration_rate_proxy` + `L2_denom` | 同上（须同时抄 `L2_denom`，无分母不写率） |
| `词表 sha8` | 冻结词表指纹（两臂必须同值，否则判口径漂移） | `lexicon_sha8` | 同上；两臂值不同 ⇒ 停下排查，不得出表 |
| `zero_nature` | 零的性质：`结构性`/`未观测到`/`仅窗口外`/`未判定` | `zero_nature`（由 `--whitelist` 决定） | A 臂必须 `--whitelist off`，B 臂必须 `--whitelist on`；漏传即 `未判定` ⇒ 本批判定作废 |
| `判定` | 按 §5.5 分支表照抄结论句 | — | — |

> **接线存在性旁证（必填，不进上表主列，但缺了不算接通）**：`layer4_world_ctx_present_msgs`（payload 带 `world_ctx` 的消息条数）两臂对照——A 臂应 0，B 臂应 >0；配合 `layer4_real_ref_msgs`（真引用 `world_ctx.refs` 命中世界事件实体的消息条数）。这两个字段是「世界事件是否真的被带进对话上下文」的直接证据，与 `M-1` 词表代理**并列、不得互相替代或相加**。

> **感知覆盖率**（独立指标，不与 `M-0` 混用）：`分母 = 每 directive 有效期回合数 = 6`（单位：回合/实体）；`分子 = 可感知回合数 = 3` ⇒ `3/6 = 50%`。取自 `perception_coverage_rounds`，**不得**写成 `M-0` 上界 0.5。

> ✅ **已核实：读数脚本本身没有这个 bug**——`v2/evidence/d8_metrics.py:261-270` 的 `zero_nature` 按 `--whitelist` 分三支：`off` ⇒「结构性(白名单未开)」、`on` ⇒「未观测到」、未传 ⇒「未判定」。**风险点只在"两臂是否各自显式传了 `--whitelist on|off`"**：若某臂漏传，会落到「未判定」或被人手填成同一个值。出表时必须核对两臂的 `--whitelist` 实参。
>
> ⛔ **`zero_nature` 陷阱（自动化读数必须核）**：A 臂的 0 是「**结构性**」（白名单未开，代码必然）；B 臂若也是 0，性质应变成「**未观测到**」（开了白名单但没观测到命中，是观测事实而非结构必然）。**两臂共用同一个常量 = 读数表撒谎**。若看到两臂 `zero_nature` 相同且都是"结构性"，**按 bug 上报**，该表不得引用。

### 5.2 M-1 的分母只有 64，比率不作统计推断

- A 臂 60 回合下实际 `MSG_DM/MSG_PUBLIC/MSG_GROUP` 条数**预登记 = 64**（t4 落盘后必须现算复核；B 臂须单独现算，不得抄）。
- **措辞纪律**：M-1 一律按「**事件数为主、比率仅作参考**」写，**禁止**写成"4.7% 的消息提及了世界事件"这类率式表述。报告正文写「**本批为小规模存在性臂，`MSG_*` 分母 N=<实测值>，不构成频率估计**」。
- **不得与历史基准 A0 的 686 分母读数并列比较**（`16 agents × 84 rounds`，口径不同）。
- 若两臂消息量分母差 >30% ⇒ M-1 判「不可比」，只报事件数（判据卡 R3/§4.3）。

### 5.3 两臂 LLM 验真原文要点（`obs llm-cost` 关键字段）

**验真命令（每臂各跑一次，必须贴原文，不得只写"通过"）**：

```bash
cd code && python3 -m obs llm-cost --log ../v2/evidence/<ARM_RUN_DIR>/run.jsonl \
     --require-provider openai_compat
```

| arm | provider | calls | cached | tokens_in | tokens_out | degraded | 日志 sha8 |
|---|---|---|---|---|---|---|---|
| A | 待填（须为 `openai_compat`） | 待填（须 >0 且 >cached） | 待填 | 待填（非零） | 待填（非零） | 待填（须 0） | 待填（`sha256sum <run>/run.jsonl` 前 8） |
| B | 待填（须为 `openai_compat`） | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 |

> 验真判据（基线证据包 §3）：`by_provider` 出现真实 provider 名、`calls > cached`、`tokens_in/out` 非零、`degraded=0`；再加 `--require-provider openai_compat` 作硬断言。
> **三项判定齐全才算过**：① RC=0；② `provider_guard.ok=true` 且 `by_provider` **只含** `openai_compat`；③ `total.calls>0`。任一不满 ⇒ 该臂判失败，如实写，不得用 mock 读数充数。

### 5.4 关键差值

- 【未完成·待读数】：`ΔM-0`、`ΔM-1`、`ΔL-2 旁白率`、分母差是否 >30%。
- **上界口径先钉死（读数到手前写定，防事后改口径）**：`M-0` 上界 **1.0（=24/24）**，**不是 0.5**；`0.5` 只属于独立指标「感知覆盖率 = 3/6」（见 §2.1.1）。`M-0_w` 若报，分母 = **144**、上界 0.5，**与 M-0 分列、不得互相代入**。
- **本表仅描述性**：单 seed、单批、分母 <30 的项只报事件数不报比率；不做"接通后效果显著"类表述（预注册 §3 禁止项）。

### 5.5 结论句：按 B 臂 `zero_nature` 实测值分支写（**先取数，后成句**）

> **禁止先写结论再套数。** B 臂的 `zero_nature` 取到哪个值，就走哪一支；两支措辞不可互换。

| B 臂 `zero_nature` | `M-0` | 结论句（**照抄，不许改写成另一支**） | 本报告这次能不能说"是否有效" |
|---|---|---|---|
| **`未观测到`**（B=0） | 0 | 「**链路已接通，但在这批规模下没有观测到沉淀**」 | **不能**。样本不足 ≠ 机制无效；只报事件数 |
| **`非零`**（B>0） | >0 | 「**链路已接通，并有沉淀证据**」（随后给事件数 + 单位齐全的分母） | 只能说"接通且有沉积"，**仍不能说"效果显著"** |
| **`未判定`**（漏传 `--whitelist`） | — | 「**本批判定作废**，按 §0.2 第 4 条重出表」 | 不能 |
| **`仅窗口外`** | 窗口内 0、窗口外 >0 | 「**窗口内未观测到；窗口外命中 X 次**」（事件级事实，不算接通证据） | 不能 |

> ⚠️ **本轮最容易出的最后一类错：把"没测到"写成"不存在"。**
> 这与 batch-runner 最早那次「0 条 `OBSERVATION` 就读成"可见层断了"」（见 §2.2）是**同一个错误的两副面孔**：
> - 那次把"没沉淀"读成"没看见"；
> - 这次的风险是把"没观测到沉淀"读成"接通失败"。
>
> 两者的共同点是**用零去证明否定**。零只证明"这批里没有"，不证明"不可能有"。

### 5.6 读数执行手册（t4 落盘后按此逐条跑，命令级）

> 前置：t4 产出两个 run 目录（`v2/evidence/` 下，各含 `run.jsonl` + `meta.json`）。**只读、零 LLM、不改代码。** 两臂的 run 目录名以 t4 运行记录 md（`team-workspace/d8-run-log.md`）为准，本报告填表时原样引用。

**⓪ 先钉两臂身份（防止 A/B 贴错标签）**

```bash
# 每臂：日志 sha8 + meta 关键字段 + 代码 sha；两臂除 D8 开关外应完全一致
for D in <ARM_A_DIR> <ARM_B_DIR>; do
  echo "== $D"; sha256sum "$D/run.jsonl" | cut -c1-8
  python3 -c "import json,sys;m=json.load(open(sys.argv[1]));print({k:m.get(k) for k in ['code_sha','seed','n','rounds','events','degraded_calls','fallback_detected','provider']})" "$D/meta.json"
done
```

**① M-0 / M-1 / 覆盖率 / zero_nature（两臂各跑一次，`--whitelist` 不可漏）**

```bash
# A 臂（开关关）
python3 v2/evidence/d8_metrics.py --log <ARM_A_DIR>/run.jsonl --label A \
        --whitelist off --out-json v2/evidence/d8_metrics_<A_TAG>.json
# B 臂（开关开）
python3 v2/evidence/d8_metrics.py --log <ARM_B_DIR>/run.jsonl --label B \
        --whitelist on  --out-json v2/evidence/d8_metrics_<B_TAG>.json
# 自检：两臂 zero_nature 必须不同（A=结构性 / B=未观测到 或 非零）；lexicon_sha8 必须相同
python3 -c "
import json
a=json.load(open('v2/evidence/d8_metrics_<A_TAG>.json')); b=json.load(open('v2/evidence/d8_metrics_<B_TAG>.json'))
print('zero_nature', a.get('zero_nature'), '|', b.get('zero_nature'))
print('lexicon', a.get('lexicon_sha8'), '|', b.get('lexicon_sha8'))
print('M0', a.get('layer3_M0_dedup'), a.get('layer3_M0_denom'), '|', b.get('layer3_M0_dedup'), b.get('layer3_M0_denom'))
print('M1', a.get('layer4_M1_num_msgs'), a.get('layer4_M1_denom_msgs'), '|', b.get('layer4_M1_num_msgs'), b.get('layer4_M1_denom_msgs'))
"
```

**② LLM 验真（每臂原文）**：见 §5.3 命令；原文贴进本节下方「验真原文附录」。

**③ 感知覆盖率（独立指标，勿并入 M-0）**：读上面 json 的 `perception_coverage_rounds`；口径 `分母 = 每 directive 有效期回合数 6`、`分子 = 可感知回合数 3`。若实测与 `3/6` 不同，写实测值与推导式，并说明差异来源（如 `window_rounds` 或 directive 有效期变化）。

**④ 截图（每臂四视图，必须真实渲染、等 `__RENDER_READY__`）**

```bash
# 1) 由 run.jsonl + meta.json 生成线程视图数据（落 code/frontend/sample/，被 .gitignore 忽略但不影响提交）
python3 code/frontend/tools/gen_threads.py --log <ARM_DIR>/run.jsonl --meta <ARM_DIR>/meta.json \
        --out code/frontend/sample/dialogue_<ARM_TAG>/threads.json --require-complete
# 2) 出四张对照截图（服务已在 8848 跑；文件名自动从 threads.json 的 run_label/run_sha256 派生并自校验）
cd code && bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 \
        sample/dialogue_<ARM_TAG>/threads.json
# 3) 记录：绝对路径 + 图 sha256 + threads.json 的 source.run_sha256（必须等于 run.jsonl sha256）
sha256sum ../v2/evidence/d7_shots/<ARM_TAG>-*.png
```

> `shot.py` 内部等 `window.__RENDER_READY__===true`（`main.js` 在素材加载 + 首帧后置位），等不到即非零退出，**不会默默产出黑图**。截图完成后须再用页面文本核对：chat 视图可见世界事件相关线索（B 臂）与 `world_ctx` 指示（如前端已加筛选则见 §6.1）。

**⑤ 填入 §5.1 表并做一致性自检**（缺一不可）

- [ ] 两臂 `--whitelist` 实参分别为 `off` / `on`（`zero_nature` 不同）；
- [ ] 两臂 `lexicon_sha8` 相同；
- [ ] `M-0 分母` = `n_alive_agents × N_world`，且 `n_alive_agents` 两臂均为 4；
- [ ] `M-1 分母` 两臂各自现算；差 >30% ⇒ 判不可比；
- [ ] 每个数字都绑 `<ARM_DIR>/run.jsonl` 的 sha8 与本次复算命令；
- [ ] 结论只按 §5.5 分支照抄，不写效果层表述；剂量刻意抬高（aggressive）已在 §5.0 + §2.3 写明。

---

## 6. 真实截图引用

> **状态：脚手架（等两臂 run 目录落盘后出图填表）。**
> 格式固定：`绝对路径 + 渲染的是哪一臂 + 渲染命令 + 日志 sha256`。
> 纪律（全族通用）：文件名 `<batch_id>-<视图>-<sha8>.png`；禁止拼图与跨批混拼；拿不到图就写「无图 + 渲染命令」，不用图替代。
> 截图必须真实渲染：`shot.py` 等 `window.__RENDER_READY__===true` 再截，等不到即非零退出。

**生成命令（每臂一次，`<ARM_TAG>` 由 threads.json 的 `run_label` 自动派生；在仓库根执行，服务 8848 需在跑）**：

```bash
python3 code/frontend/tools/gen_threads.py --log <ARM_DIR>/run.jsonl --meta <ARM_DIR>/meta.json \
        --out code/frontend/sample/dialogue_<ARM_TAG>/threads.json --require-complete
cd code && bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 \
        sample/dialogue_<ARM_TAG>/threads.json
```

| 视图 | 绝对路径 | 渲染的是哪一臂 | 渲染命令 | 日志 sha8 |
|---|---|---|---|---|
| chat（对话流） | `v2/evidence/d7_shots/<A_TAG>-chat-<sha8>.png` 待填 | A（开关关） | 见上方命令 | 待填 |
| chat（对话流） | `v2/evidence/d7_shots/<B_TAG>-chat-<sha8>.png` 待填 | B（开关开） | 见上方命令 | 待填 |
| rhythm（节律·串门） | `v2/evidence/d7_shots/<A_TAG>-rhythm-<sha8>.png` 待填 | A | 同上 | 待填 |
| rhythm（节律·串门） | `v2/evidence/d7_shots/<B_TAG>-rhythm-<sha8>.png` 待填 | B | 同上 | 待填 |
| spread（闲话传播） | `v2/evidence/d7_shots/<A_TAG>-spread-<sha8>.png` 待填 | A | 同上 | 待填 |
| spread（闲话传播） | `v2/evidence/d7_shots/<B_TAG>-spread-<sha8>.png` 待填 | B | 同上 | 待填 |
| 600（窄屏） | `v2/evidence/d7_shots/<A_TAG>-600-<sha8>.png` 待填 | A | 同上 | 待填 |
| 600（窄屏） | `v2/evidence/d7_shots/<B_TAG>-600-<sha8>.png` 待填 | B | 同上 | 待填 |

**填表附带（每张图三件套 + 自校验）**：

- 图 sha256：`sha256sum v2/evidence/d7_shots/<TAG>-<view>-<sha8>.png`；
- 数据源：`code/frontend/sample/dialogue_<ARM_TAG>/threads.json` 的 `source.run_sha256`，**必须等于** `<ARM_DIR>/run.jsonl` 的 sha256（`sha256sum` 核对）；
- 生成时间：`stat -c '%y'`；
- 页面文本核对（可选但建议）：Playwright 等 `__RENDER_READY__` 后读 `document.body.innerText`，B 臂 chat 视图应能看到世界事件线索 / `world_ctx`（若已加筛选）。

### 6.1 前端「世界事件」筛选（**仅在两臂跑批全部结束后**才可做）

- 允许目录：`code/frontend/`（不在跑批禁改范围）；**不得**影响既有三视图（chat / rhythm / spread）渲染。
- 目的：让 D8 的 `world_ctx.refs / prompted` 在页面上肉眼可见（B 臂有、A 臂无）。
- 改动须单独说明：文件、行、默认行为（默认不改变既有视图）、回归证据（三视图截图 sha 前后一致或说明差异）。
- **本轮若未做，在此写明「未做，原因：两臂未跑完 / 时间不足」，不得留空。**

---

## 7. 三档标注（已证实 / 仅机制接通未验证 / 未解决）

### 6.1 已证实（有代码 + 数据双证，可直接引用）
1. **世界事件对对话零暴露**（L5）：prompt 装配函数无世界行（代码判据）+ `refs` 命中 0（数据判据）+ 检索输入不含世界维度（代码判据）。三判据按预注册 §2 L5 "①②③ 全为否"给出。
2. **可见但未沉淀**（L4/L4′）：世界事件存在于 `visible_events`（纯函数复算）+ 精确引用 seq 的 `MEMORY_WRITE`/`OBSERVATION` = 0。
3. **`affected_scope_count` 是字面量 0**（L3）：全仓唯一写入点即字面量，无解析代码。
4. **剂量 E=0.966 < 1**（L1）：配置 + 曲线实测复算，1 条落在 Poisson(E=0.966) 的 37% 分位，属正常。
5. **触发逻辑与日志逐条全等**（L2）：复算触发集 == 日志触发集，`WORLD_DIRECTIVE_REJECTED`=0。
6. **三条路径不同源不同界**：`world_params` 有 `[start,end)`；真实 perceive 路径有 2 回合滑窗（`VISIBLE_WINDOW_ROUNDS=2`，实测 round 30/31/32 可见、33 起不可见）；L6 的 `contracts.visible_events` 无时间维（`grep` 空输出 rc=1）。**注意这三者不对称，不是"感知层没有时间维"。**
7. **`market_scarcity_bp` 无功能消费**（L6）：grep 原文只有"是否非空"计数，稀缺期唯一交易 `{"scarcity_index":0,"unit_price":100}` 价格未变。

### 6.2 仅机制接通未验证（代码改了，效果没验）
- 【未完成·待 d-dim-impl / d-dim-verify】本档的判据：**改了代码但 A/B 读数未到齐、或读数受污染（如 token 泄漏、时间窗未修）**，一律进本档，不得进 6.1。
- **B 臂 `M-0 = 0` 时的归属（先定死，防事后挪档）**：进本档，结论句用 §5.5 的第一支「接通了，但在这批规模下没有观测到沉淀」；**不得**挪进 6.3「未解决」去暗示"机制无效"——"没测到"不属于"未解决"。

### 6.3 未解决
- 【未完成·待 veriy】世界事件进对话后是否真的会让"小镇更有生活气息"（北极星目标）——本轮**不回答**，只回答"管道通不通"。

---

## 8. 遗留问题（含本轮新发现）

### 7.0 口径变更登记（本报告作为最新报告，声明变更；**不改历史报告正文**）

- **`d5_v0anchor_lock.md` 的 sha256 已变**：该锁定凭证随脚本入库（`b306a40`）后更新，sha256 由 `2940fb8f…`（**R4 正文引用的值**）变为 `e827f885…`。裁决：**不回滚该文件、不改 R4 正文**——改历史报告会破坏"当时快照"的性质。**以本报告与现文件 sha256 为准，R4 该处引用值已过时。**
- **诊断正文 §5.1 的曝光数已自更正**：`16×54=864 agent-回合` → **`16×3=48 agent-回合`**（原先用的是 `engine.perceive.visible_events` 这个**无时间窗的复算入口**，而真实跑批路径是 `KernelAdapter.perceive → VisibilityIndex.visible(window_rounds=2)`）。这不改变"可见层是通的"判断，只把曝光窗口从"半个模拟周"更正为"3 个回合"。**这也是一条方法学教训：复算入口必须与被复算的生产路径同一个函数，否则读数看似精确、实则是另一条路径的事实。**

### 7.1 本轮新发现（诊断过程中撞见，非本轮修复范围）

**(1) `msg_id` 撞号，与 `ports.py` 契约不符 —— 中危，下轮修**
- 现象：同回合不同 agent 的 `msg_id` 相同。
- 证据：`code/orchestration/integration.py:825` `f"D-{r}-{n}"`、`:840` `f"P-{r}-{n_a}"`、`:864` `f"G-{gid}-{r}-{n_g}"`；契约在 `code/life/ports.py:78-82`（`D-<round>-<agent_id>-<n>` / `P-<round>-<agent_id>-<n>` / `G-<group_id>-<round>-<n>`，注释自带"旧格式会撞"的警告）。
- 实测（A0 批 `643f13a5`）：686 条 MSG 只有 **216** 个不同 `msg_id`；**71 个值撞号、涉及 541 条消息（79%）**；样例 `P-0-0`×5、`D-1-0`×9、`D-3-0`×10。
- **口径修正记录**：team-leader 先前判"低危、可延后"，据上述实测**修正为中危、下轮修**——据实测修正先前判断，不悄悄改口径。现存读数未受影响（D2 线程分析由 `msg_uid` 兜住，`meta.assertions.msg_uid_unique=true`），但**契约已破**。
- 危害：任何按 `msg_id` 去重/引用的下游会静默丢消息。

**(2) `_default_llm` 静默降级 MockProvider —— 中危，下批起跑前加断言**

> **最有说服力的对照：同一个团队里，"未声明"有两种处理方式，一个暴露成失败、一个静默降级。**
> - 读数脚本 `v2/evidence/d8_metrics.py:83` 的 `--whitelist` 参数**默认值就是 `unknown`（失败态）**，且 `:267` 明确写"未判定(需传 --whitelist on|off;脚本不替调用方猜)" ⇒ 忘传就**拿不到判定**，不会被默认值蒙过去。
> - `integration.py:894-945` 则是"忘记设 `HITT_LLM_PROVIDER` 就静默降级 `MockProvider()` 且不报错" ⇒ 忘设会**安静地跑完一整批**，产出一份"看起来是真跑"的日志。
>
> 两者面对的是同一类问题（调用方没声明配置），差别只在"默认值是失败态还是残缺态"。**这不是水平差异，是默认值设计差异**——因此修复成本很低：把默认值改成失败态即可，不需要重构。

- 证据：`code/orchestration/integration.py:894-945`：`:943-945` `except Exception: from life.llm import RuleBasedLLM; return RuleBasedLLM()`；且 `:929-936` 在 `HITT_LLM_PROVIDER=openai_compat` 但 `LLM_ENDPOINT`/`LLM_MODEL` 为空时 provider 仍是 `MockProvider()`、**不抛错**。
- 危害：可能"零 token 也算真跑"；只有 `obs llm-cost --require-provider openai_compat` 门禁兜得住，其余环节无声。

### 7.2 诊断里顺带确认的既有问题

**(3) `affected_scope_count` 恒为 0**（见 §2.1、§8.1(3) 同源）：下游会把"0 影响"当事实读，无法判定事件是否真落地——"从未实现"被误读成"读数为 0"的典型。建议下轮（与 `market_scarcity_bp` 定价消费同批）算真值，或先改名标注 `affected_scope_count_uncomputed`。

**(4) 感知窗（3 回合）⊂ 有效期（6 回合）—— 感知覆盖率只有 50%**（本轮新量化）：`dose.slots=6` ⇒ directive 有效期 `[issued, issued+6)`；真实感知窗 `[r-2, r]` ⇒ 仅 `+0/+1/+2` 可见。在 `+3..+5` 期间 directive **仍在 `world_params.active` 里起作用**，但**居民看不见**。这是独立于"事件进不了对话"的第二个缺口：世界在变，居民感知不到变化。修复方向二选一：把 `slots` 与感知窗对齐（语义上更干净），或让 `contracts.visible_events` 接受 `window_rounds` 并由 L6 传入有效期（工程上更小）。

**(5) `contracts.visible_events` 无时间维（三路径不一致的第三处）**：`grep -n "start_round\|end_round\|expires" code/contracts/visibility.py` 空输出（rc=1）。受影响的正是 L6 `settlement.py:620` 那条路径——**生命层写记忆走的是无窗版本**，而 perceive 走的是有窗版本。危害：观测白名单一放开，L6 会持续观察"过期事件" ⇒ B 臂 M-0 虚高、样本全脏。修复必须让两条路径**同源同界**；注意这对 perceive 路径是"与既有 `window_rounds=2` 叠加/重复"，真正缺窗的只有 L6 那条。（此条修正了原文"世界 directive 过期后仍永久可见"的过宽表述。）

**(6) 9 个世界机制中 7 个 `enabled=false`，唯一能影响行为的参数（`activity_weight`）由从不触发的 festival 驱动**：现状是"唯一能影响行为的参数从不触发，唯一触发的参数不影响任何行为"。

---

## 9. 复算清单（第三方按原样命令核对全文每个数字）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# ⓪ 身份与数据
git rev-parse HEAD                       # 2090287809ae307614b3f9b2f62e7619f2142ea8
sha256sum v2/evidence/run_d2_after_n16_seed42/run.jsonl v2/evidence/run_d2_after_n16_seed42/meta.json
sha256sum code/config/world_director.json code/config/perception_scope.json

# ① L1/L2 剂量 + roll 复算 + 与日志比对
cd code && python3 - <<'PY'
import json
from engine.world_director import cfg_of, mechanism_enabled, resolve_dose, rng_branch
cfg = cfg_of({'world_director': json.load(open('config/world_director.json'))})
idx = {m:i for i,m in enumerate(sorted(cfg['mechanisms']))}
for mid in sorted(cfg['mechanisms']):
    if not mechanism_enabled(cfg,mid): continue
    prob = int(resolve_dose(cfg,mid)['prob_bp'])
    rolls = [rng_branch(42,r,idx[mid],1)[0]%10000 for r in range(84)]
    print(mid,'prob_bp=',prob,'E=',round(84*prob/10000,3),'N=',sum(1 for x in rolls if x<prob),
          'min=',min(rolls),'max=',max(rolls))
PY
cd .. && python3 - <<'PY'
import json
lg=[(d['payload']['issued_round'],d['payload']['mechanism_id'],d['payload']['rng_branch']['roll_bp'])
    for d in map(json.loads,open('v2/evidence/run_d2_after_n16_seed42/run.jsonl')) if d.get('type')=='WORLD_DIRECTIVE']
print('日志触发集:',lg)
PY
grep -c '"WORLD_DIRECTIVE_REJECTED"' v2/evidence/run_d2_after_n16_seed42/run.jsonl

# ② L3/L4 影响面字段唯一写入 + 世界事件 seq 精确引用条数
grep -rn "affected_scope_count" code --include=*.py
python3 - <<'PY'
import json
tg={39222,39223}; n=0
for line in open('v2/evidence/run_d2_after_n16_seed42/run.jsonl'):
    p=(json.loads(line).get('payload') or {})
    if p.get('source_event_seq') in tg or p.get('target_event_seq') in tg or \
       any(str(x) in {str(t) for t in tg} for x in (p.get('refs') or [])): n+=1
print('精确引用世界事件 seq 的记录数 =',n)
PY

# ③ L4 世界事件是否进入 visible_events —— 必须用**真实路径同一函数**（窗=2）
cd code && python3 - <<'PY'
from engine.runner import read_log
from engine.perceive import load_perception_scope
from contracts.visibility import visible_events as ve_c
sc = load_perception_scope()
recs = read_log('../v2/evidence/run_d2_after_n16_seed42/run.jsonl')
for aid in ('P001','P009','P016'):
    row=[]
    for rnd in range(29,37):
        a=[e['seq'] for e in ve_c(recs,aid,rnd,scope_table=sc.get('scope',{}),
             default_cls=sc.get('default_visibility_class','place_local'),window_rounds=2)
           if e['type'].startswith('WORLD_')]
        row.append((rnd,len(a)))
    print(aid,row)   # 期望: 29→0, 30/31/32→2, 33 起→0
PY
# 若把 window_rounds 去掉（错误入口），33 起仍为 2 ⇒ 说明"无时间维"只对 contracts/L6 路径成立

# ④ L5 提示词装配与检索输入（代码判据）
cd .. && sed -n '1050,1069p' code/life/agent.py
sed -n '444,449p' code/life/agent.py
sed -n '41,45p;395,405p' code/life/agent.py

# ⑤ L6 消费点
grep -rn "activity_weight\|resource_factor_bp\|market_scarcity_bp" code/life/agent.py
grep -rn "world_params" code/engine --include=*.py | grep -v world_params.py    # 空
sed -n '249,266p' code/engine/hooks/econ.py

# ⑥ 稀缺期交易样本
python3 - <<'PY'
import json
for d in map(json.loads, open('v2/evidence/run_d2_after_n16_seed42/run.jsonl')):
    if d.get('type')=='MARKET_TRADE' and 30<=d['round']<=35:
        print({k:v for k,v in (d.get('payload') or {}).items() if k in ('scarcity_index','unit_price','good_id','qty')})
PY

# ⑥′ 重大发现：三份 16 agents 日志的死亡清单（应逐字一致）
for d in run_d2_before_n16_seed42 run_d2_after_n16_seed42 run_r6_treat_n16_seed42; do
  python3 - "v2/evidence/$d/run.jsonl" "$d" <<'PY'
import sys,json
f,name=sys.argv[1],sys.argv[2]
ds=[(r['round'],(r.get('payload') or {}).get('agent_id'),(r.get('payload') or {}).get('liquid'),
     (r.get('payload') or {}).get('cause'))
    for r in map(json.loads,open(f)) if r.get('type')=='AGENT_DIED']
print(name,'died=',len(ds),'liquid>0=',sum(1 for d in ds if isinstance(d[2],int) and d[2]>0),
      'rounds=',sorted({d[0] for d in ds}))
for d in ds: print('  ',d)
PY
done
# 期望：三份均 died=14 / liquid>0=7 / rounds=[64,66,67,69,71,74]，cause 全为 illiquid_no_credit_N

# ⑦ 三路径时间维判据（定位句的全部依据）
grep -n "VISIBLE_WINDOW_ROUNDS" code/orchestration/integration.py          # =2
sed -n '322,346p' code/orchestration/integration.py                        # visibility_query + perceive
sed -n '140,150p' code/orchestration/visibility_index.py                    # 窗口裁剪实现
sed -n '616,624p' code/life/settlement.py                                   # L6 调用（无 window_rounds）
grep -n "start_round\|end_round\|expires" code/contracts/visibility.py ; echo "rc=$?"   # 空输出，rc=1
sed -n '36,60p' code/engine/world_params.py                                 # [start,end) 裁剪

# ⑦′ 剂量期望复算（曲线 × 机制数；禁止跨行套用曲线）
cd code && python3 - <<'PY'
import json
from engine.world_director import DOSE_CURVES
cfg=json.load(open('config/world_director.json')); mechs=cfg['mechanisms']
allp={k:v['dose'].get('prob_bp') for k,v in mechs.items() if v['dose'].get('prob_bp')}
en=[k for k,v in mechs.items() if v.get('enabled')]
for cn,cv in DOSE_CURVES.items():
    s3=sum(int(allp[k])*cv['prob_bp']//10000 for k in en)
    s8=sum(int(v)*cv['prob_bp']//10000 for v in allp.values())
    print(f"{cn:13s} 3机制E={84*s3/10000:.3f} 8机制E={84*s8/10000:.3f}")
PY
# 期望: conservative 0.966/1.512；moderate 1.932/3.024；aggressive 3.864/6.048

# ⑧ 遗留问题：msg_id 撞号 / 静默降级
grep -n 'msg_id": f"' code/orchestration/integration.py
sed -n '75,85p' code/life/ports.py
sed -n '894,945p' code/orchestration/integration.py
python3 - <<'PY'
import json,collections
c=collections.Counter()
for l in open('v2/evidence/run_d2_after_n16_seed42/run.jsonl'):
    r=json.loads(l)
    if r.get('type') in ('MSG_DM','MSG_PUBLIC','MSG_GROUP'):
        m=(r.get('payload') or {}).get('msg_id')
        if m: c[m]+=1
dup={k:v for k,v in c.items() if v>1}
print('MSG=',sum(c.values()),'distinct=',len(c),'dup_keys=',len(dup),'dup_msgs=',sum(dup.values()))
PY
```

---

## 10. 下一轮建议

1. **先修读数可信度，再谈效果**：`affected_scope_count` 要么算真值要么改名为 `_uncomputed`；`visibility.py` 补 `[start,end)` 裁剪。理由：这两处不修，任何"事件进对话"的读数都可能虚高或含义不清，先把分母/含义修干净。
2. **`msg_id` 撞号与 `ports.py` 契约对齐**（中危，见 §8.1(1)）：改 `integration.py:825/840/864` 为契约格式，或用同一套生成器；同时给 `meta.assertions` 加 `msg_id_unique` 断言，让它从"靠 `msg_uid` 兜住"变成"按契约就不撞"。
3. **`_default_llm` 加显式失败断言**：`HITT_LLM_PROVIDER=openai_compat` 但 endpoint/model 为空时抛错而非回落 Mock；`meta` 落 `provider_used` 字段，让"零 token 也算真跑"在日志层就不可发生。
4. **下一个「生活气息」维度建议**：世界事件接通后，真正的北极星问题变成"居民提及时**说什么**"（是否只是复述通告 vs 带自身处境的转述），建议下轮做**提及内容的质性抽检**（分母够大才有意义，先解决剂量/样本量）。**不建议**靠继续抬剂量来制造样本。
5. **不要做的事**：不把 `aggressive` 曲线的读数当"推荐配置"；不把"接通"当"改善"；不用单 seed 外推频率。

---

## 附：诚实边界

1. 本报告第 2、7、8、9 节的读数均来自 repo-scout 诊断正文（同批入库），作者已按 §9 命令逐条复核过关键判据（`grep` 空输出、字面量 0、msg_id 撞号计数）；未复核的部分以源文档为准并在此标注。
2. 第 5–6 节为**脚手架**（空表 + 逐格定义 + 复算命令），**不含任何实测数字、不含推断性内容**；t4 两臂落盘后填数。
3. `LLM_CALL` 只落 `prompt_hash` 不落 prompt 正文，"prompt 无世界行"只能由代码判据证明（行号 + 函数签名），不能用日志直接看到——这是本报告最容易被误读的边界，特此写明。
4. **判据卡 sha256 已定版**：终版为 `4eddf77e`（含 R1–R8，已冻结）；Leader 先前给的 `9b20e740` 系旧值，已由 Leader 确认为作废。提交时仍会重算一次并核对。
5. **本报告 §2 的 L4 曝光数依赖 D8 诊断 22:34 的自更正**：`864 → 48 agent-回合`（= 96 次事件-观测）。作者已独立实测复算该数（`48×2=96`）并写入 §9 ③；若读者用的是 22:16 之前的诊断版本，会读到 `864`——**以本报告与现行诊断文件为准**。
6. **master HEAD 在写作期间被外部变动推进了一次**：`2090287 → dff515d`（22:24:33，+2 行 `reports/R2-dialogue-structure.md` 的 meta-sha 登记）。**该提交不是本报告作者所为**（本报告作者自本轮开始至提交前未执行任何 `git add` / `git commit`），内容亦不在本轮范围。影响：本报告 §2 的代码判据仍以 `2090287` 为基线（两者在 `code/` 下无差异，`git diff 2090287 dff515d -- code/` 为空），文件级引用不受影响；提交时以 `dff515d` 为父提交。
