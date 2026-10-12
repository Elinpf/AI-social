# 各家实验的「随机性 / 可复现性」做法与理由证据表（reproducibility-survey）

> **【Fork B 时效标注 · 2026-10-12】** 本文 §「对我们的含义 / 我们主张同日志重放逐位一致」为 **v1.1 时期口径**；用户 2026-10-12 拍板 **Fork B（放开"逐位可复现"作验收口径）**后，我方主张修正为「**可复算 + 全量日志 + 种子化 + 产物 sha/命令**；字节相等降为诊断」。**保留历史结论不清删；单一口径见 `v2/refs/gate-grading.md`。**

> 文档类型：带出处的证据表（支撑我方「为何选可复现」的差异化论证）
> 作者：emergence-researcher（涌现社会实验调研专家）
> 日期：2026-10-10
> 上游依据：`research/town-life-brief.md`、`v1.1/11-agentopia-reuse-assessment.md`、`v1.1/14-agent-impl-reuse-map.md`
> 新核验来源：本地代码（GA `/tmp/gaf`、AI Town `/tmp/ai-town`）+ 论文/文档（arXiv、官方文档、README）
> 证据标记：**【已核实】**=可追溯到具体文件路径/行号/文档文本/官方文档；**【领域常识/推测】**=公认但本次未逐行核验其一源代码。

---

## 0. 结论速览（可直接用于论证段落）

1. **「其他实验都选随机」并非疏忽，而是目标函数使然**：它们的**首要目标不是「复现某一条轨迹」，而是「让 LLM 生成可信/多样的社会行为」或「用模拟产出训练数据」**（GA 目标=believable behavior；Agentopia 目标=生成 RFT 训练数据；Project Sid 目标=展示文明里程碑）。**多样性是它们的特性，不是 bug。**
2. **一个被低估的硬约束**：**LLM 采样本身不保证逐位可复现**（GA 大量 prompt 用 temperature 0.8/1/0.5；OpenAI 对 `seed` 也仅承诺 "best effort"）。**在「LLM 不可逐位复现」的前提下，"同 seed 重跑一致"对它们根本不可达**——这才是它们放弃严格可复现的根本原因，而非偷懒。
3. **经典 ABM 与 LLM-ABM 存在清晰分野**：**Sugarscape / NetLogo 传统是确定性的**（规则=代码 + 固定 seed ⇒ 完全可复现），并**原生支持多种子批量实验与方差统计**（NetLogo BehaviorSpace）；**LLM-ABM 把决策外包给不可控的 LLM，主动放弃了这一传统**。
4. **代价是真实且具体的**：不可审计、无法做严格 A/B、**无法从同一条轨迹重算不同奖励指标**（奖励改了必须重跑）、跨跑方差未报导致结论稳健性存疑。
5. **对我们的含义（诚实版）**：我们的「种子化 RNG + LLM 判定冻结 + 哈希链日志」在**可审计、可重放、可重算指标、可严格 A/B** 上**确实更强**；但**我们并不在「同 seed 跨跑一致」上更强**——只有当 LLM 输出被冻结落盘后，我们才逐位一致；**复现性建立在「已记录日志」之上，而非「凭种子重跑」**。并且要付出**冻结与日志膨胀的存储/工程代价**，LLM 成本也依然存在。**我们卖的是「审计性与事后可重算」，不是「事前可预测」。**

---

## 1. 做法表（逐对象）

> 列：①随机性来源 ②是否种子化 ③LLM 输出是否落盘可重放 ④是否报告跨跑方差/多种子 ⑤是否声称可复现

| 对象 | ①随机性来源 | ②种子化 | ③LLM 输出落盘/可重放 | ④跨跑方差/多种子 | ⑤声称可复现 | 证据 |
|---|---|---|---|---|---|---|
| **Stanford Generative Agents（Smallville）** | LLM 采样（**temperature 0.8/1/0.5/0** 混用）+ Python `random.sample/choice`（**未播种**）+ 用户注入的单一种子事件 | ❌ 无全局 seed | ❌ 无（直调 OpenAI，输出不落为可重放事件） | ❌ 论文报告**消融实验**，非多种子方差 | 未声称可复现；论文以「believable + 消融贡献」为结论 | **【已核实】** `gaf/run_gpt_prompt.py:70`(temp 0.8)、`:142`(temp 1)、`:269`(temp 0.5)、`:430/606/703`(temp 0)；`gaf/persona_cognitive_modules_execute.py:83/100/102`、`plan.py:687/695`（`random.*` 无 seed）；`gaf/gpt_structure.py:276-281`（`get_embedding` 直调） |
| **a16z AI Town** | LLM 采样 + **大量 `Math.random()`（未播种）**（角色分配、邀请接受概率、寻路回退、随机位置/朝向、随机活动）+ 随机 UUID | ❌ 无 seed（`xxhash` 的 seed 用于内容寻址**非 RNG**） | ❌ 无审计日志；`HistoricalObject` 仅用于**渲染平滑**回放，非重放 | ❌ 未报告（是 starter kit，非研究论文） | 未声称；README 定位为「可部署/可扩展地基」 | **【已核实】** `ai-town/convex/world.ts:134`、`convex/aiTown/agent.ts:114/174/195/222`、`convex/aiTown/agentOperations.ts:34/129/159/175`、`convex/aiTown/player.ts:154/193/211`（`Math.random()`）；`convex/agent/memory.ts:256`（`temperature: 0.0` 仅用于 importance）；`convex/util/xxhash.ts:61`；`ARCHITECTURE.md`（`historicalObject` 用途） |
| **Agentopia** | `god_model`（LLM，temp 0.7）+ 局部确定性 tie-break 种子 + 环境模型生成 | ⚠️ **局部**（tie-break 用 hashlib 派生 seed），**无全局 seed** | ❌ 无全局 event log/replay（落盘的是状态/生成轨迹，非可折叠重放事件） | ❌ 论文报告单次运行的指标提升，**未见多种子方差** | 未声称；定位为「长期社会模拟 + 训练数据生成」 | **【已核实】** `config.example.json`（`temperature:0.7`）；`src/world/world.py:1196-1199`、`god.py:257-262`、`position_application.py:360-385`（局部 seed）；见 `v1.1/11-agentopia-reuse-assessment.md` |
| **Project Sid（Altera）** | 实时 LLM 多流（PIANO）+ Minecraft 环境动态 | ❌ 未见 seed 说明 | ❌ 未见（技术报告） | ❌ 未见（自述为 **preliminary results**） | 未声称可复现；自称「初步结果」 | **【已核实】** arXiv:2411.00114 摘要与引言（「**preliminary results**」、10–1000+、PIANO）；**未在可获取内容中见到种子/方差说明**（→ 记为「未见」而非「不存在」） |
| **AgentSociety（清华 FIB Lab）** | LLM 驱动 + Ray 分布式异步调度 | ❌ 文档未见 seed 说明 | ⚠️ **V2 提供 JSONL replay**（记录后回放）；V1 为 Ray 异步 | ⚠️ 论文强调与**真实世界结果对齐**（分布层面），未见单轨迹多种子方差 | 定位为「社会科学实验床」，重在与真实数据对齐 | **【已核实】** 官方文档首页（「V2 提供…**JSONL replay** 与研究技能」「Ray 分布式计算」「异步模拟架构」）；arXiv:2502.08691 摘要（「alignment between AgentSociety's outcomes and real-world experimental results」） |
| **AI Economist（Salesforce）** | 双层深度 RL（agent + 政府学习）+ 经济仿真 | ✅（RL/仿真**通常**以 seed 驱动，仓库含 `run_configs`/rllib 配置） | ❌（RL 环境，非 LLM 重放） | ✅（RL 研究惯例报告多轮训练/评估，含误差） | 论文以「仿真环境 + 多轮学习」为准 | **【领域常识/推测】** arXiv:2004.13332（「two-level deep reinforcement learning」「economic simulation environment」）；仓库树含 `ai_economist/training/run_configs`、`tutorials/rllib/*/config.yaml`（**未逐行核验 seed 字段**） |
| **EconAgent（清华）** | LLM 驱动 ABM（perception + memory 模块）+ 规则化市场 | ⚠️ 未核验（可能含 seed） | ❌ 未见 | ⚠️ 未核验（论文/代码是否多轮重复未确认） | 论文强调「更真实的宏观现象」 | **【已核实(仅存在性)】** arXiv:2310.10436（ACL 2024，LLM-ABM，「codes are released」）；**可复现细节本次未获取** → 记为未核实 |
| **Sugarscape（对照：经典 ABM）** | 规则=确定性代码；**仅初始条件/事件表由 seed 驱动** | ✅ 固定 seed ⇒ 完全确定性 | N/A（无 LLM） | ✅（ABM 传统：多种子/多参数扫描） | 经典 ABM 默认**可复现** | **【领域常识/推测】** Epstein & Axtell, *Growing Artificial Societies* (1996)；Sugarscape 以「代谢→资源→死亡」的确定性规则著称 |
| **NetLogo 传统（对照）** | 规则=确定性代码；`random-seed` 显式控制 | ✅ `random-seed` 原语 | N/A（无 LLM） | ✅ **原生**：BehaviorSpace 内置多次重复运行 + **输出均值与标准差** | 明确支持「参数扫描 + 可复现」 | **【已核实】** 官方手册 docs.netlogo.org/behaviorspace：「runs a model **many times**, systematically varying the model's settings and recording the results of each model run」（parameter sweeping）；NetLogo 6.4 起「**the mean and standard deviation of data from repetitions can be saved**」 |

### 1.1 做法表速读
- **确定性/可复现：** Sugarscape、NetLogo（经典 ABM）✅ ；其余 LLM 类基本 ❌。
- **唯一有「回放」能力的 LLM 框架：** AgentSociety **V2 的 JSONL replay**（记录后回放，非「凭种子重跑」）。
- **种子的真实作用**：在经典 ABM/RL 里 seed 决定「世界如何随机」；在 LLM-ABM 里 **seed 管不到 LLM 采样**，于是即使设了 seed 也不可复现——**这是分野的关键**。

---

## 2. 理由归纳：为何普遍放弃「严格可复现」

> 每类动机尽量给佐证。

**动机 A：目标是「生成多样性 / 可信行为 / 训练数据」，而非复现单条轨迹。**
- GA 目标= "*believable* individual and emergent social behaviors"（arXiv:2304.03442 摘要），并用**消融**证明组件贡献——关心的是「行为是否可信」，不是「第 37 步是否与上次一致」。
- Agentopia 目标= 用长期模拟轨迹经拒绝采样**训练 LLM**（`build_rft_data.py`）；**轨迹越多样，训练数据越有价值**——多样性是**需求**。
- Project Sid 目标= 展示「文明里程碑」（专业分工/规则演变/文化传播），是**存在性演示**。
- **佐证等级**：GA/Agentopia/Project Sid 均为【已核实】其一手目标表述。

**动机 B：LLM 采样本身不保证逐位可复现——「同 seed 重跑一致」根本不可达。**
- GA 多数生成 prompt 用 **temperature 0.8/1/0.5**（【已核实】`run_gpt_prompt.py`），非 0；采样必然带来非确定输出。
- 即便 temperature=0，云端 LLM 也不保证逐位一致（模型版本、批次、硬件、MoE 路由等），OpenAI 对 `seed` 参数亦仅承诺 "**best effort**"（【领域常识】官方文档语义）。
- **推论**：在 LLM-ABM 中，**seed 只能固定「非 LLM 的随机」，固定不了「LLM 的随机」**——这从根上否决了「凭种子重跑」的可行性，是它们转向「分布视角」的技术原因。

**动机 C：工程与成本复杂度——冻结+重放代价高，研究项目优先出结果。**
- 要严格可复现，必须：① 把每次 LLM 输出落盘并缓存；② 确定性调度；③ 版本锁定模型。GA 直调旧版 OpenAI SDK（`openai==0.27.0`，【已核实】`requirements.txt`），AI Town 在 Convex action 里实时调 LLM（【已核实】`convex/agent/*`）——**都没做输出冻结**。
- 这是一笔**只在「需要审计」时才划算**的投入；纯探索型研究不会先付。

**动机 D：社会科学统计传统以「分布/期望」而非「单条轨迹」为目标。**
- NetLogo BehaviorSpace 的设计哲学就是「参数扫描 + 多次重复 + **报告均值与标准差**」（【已核实】官方手册）——**ABM 传统关心分布，不关心单轨迹**。
- AgentSociety 明确强调其**与真实世界实验结果的对齐**（分布层面，arXiv:2502.08691 摘要，【已核实】）。
- 因此「随机」在社会科学语境下**不是缺陷**：**要的是统计规律，而非一次重演的确定性**。

**动机 E：ABM 传统与 LLM-ABM 的分野。**
- Sugarscape/NetLogo（【领域常识/已核实 NetLogo】）：agent 规则是**代码**，随机仅来自 seed 化的初始条件/事件 ⇒ **可复现**。
- LLM-ABM：把决策**外包给不可控的 LLM** ⇒ **主动放弃**了「规则确定」这一可复现来源。
- 这一分野解释了「为什么经典 ABM 讲可复现，而 LLM-ABM 几乎不讲」。

---

## 3. 代价对比：不可复现的具体代价

| 代价 | 具体表现 | 佐证/推断 |
|---|---|---|
| **不可审计** | 无法核验「某条结论对应哪条轨迹/哪次决策」；GA/AI Town/Agentopia 均无事件级审计链 | 【已核实】三仓库均无哈希链/事件日志（见 §1） |
| **无法做严格 A/B** | 同一初始条件下对比「有/无某干预」需**同轨迹**；LLM 非确定使对照组与实验组的差异被采样噪声污染 | 【推断，基于动机 B】 |
| **无法从同轨迹重算不同奖励指标** | Agentopia 的 reward 变了就得**重跑整个 10 年模拟**；无法「读旧日志、换新奖励函数重算」 | 【已核实】`reward.py` 与模拟耦合；无独立可重算日志 |
| **结论稳健性存疑** | 未报跨跑方差 ⇒ 无法判断「+15.6% 提升」是稳定效应还是单跑幸运 | 【已核实】Agentopia 论文报告单跑提升 |
| **科学可复现性危机** | 第三方**无法复现**结果，只能复现「方法」 | 【领域常识】LLM-ABM 领域的普遍批评 |

---

## 4. 对我们的含义（**诚实区分优与不优**）

### 4.1 我们**确实更强**的方面
1. **审计性**：哈希链 append-only 日志 ⇒ 每个结论可追溯到具体事件（`LLM_CALL`/`TRANSFER`/`STATE_CHANGE`）。
2. **可重放**：`State = reduce(apply, EventLog, seed)`，**同日志逐位一致**（而非「凭种子重跑」）。
3. **可从同一轨迹重算不同指标**：统计程序只读日志纯函数 ⇒ **奖励/指标改了不必重跑模拟**，直接重算——**这是它们都做不到的**。
4. **可做严格 A/B**：固定日志后对比干预，噪声被隔离。
5. **LLM 判定冻结**：`llm_judged_metric_count==0` ⇒ 指标不随模型版本漂移。

### 4.2 我们**并不优于**它们、或需付出代价的方面（**必须诚实**）
1. **我们不保证「同 seed 跨跑一致」**：若 LLM 输出未被冻结，**首次运行本身就是非确定的**；我们的复现性**建立在「已记录日志」之上**，**不是**「凭 seed 重跑」。—— 本质上我们用的是与 AgentSociety V2 同类的「**记录后回放**」策略，只是把它**在全系统层面硬化**了。
2. **冻结与日志膨胀的代价**：要把每次 LLM 输出落盘 + 哈希链，**存储与写放大显著上升**；长时程（年尺度）下日志可能成为主要存储开销。它们不做，部分正是因为「不划算」。
3. **LLM 成本依然存在**：冻结只是**避免重放时重复调用**，**首次生成仍需付费**。
4. **确定性内核的复杂度**：整数记账/规范 JSON/全序 tie-break/无墙钟依赖，**工程成本高于它们的「随便跑跑」**。
5. **我们牺牲了「多样性即需求」的场景**：对 Agentopia 式「用模拟生成多样训练数据」的目标，**我们的严格复现反而不是卖点**——**我们的目标（可审计的社会实验）与它们（生成/演示）不同，所以选择不同**。

### 4.3 可直接用于论证段落的一句话
> **「其他实验普遍选择随机，不是因为随机更好，而是因为它们的目标是『生成可信/多样的社会行为』或『产出训练数据』，且 LLM 采样从根本上不可逐位复现，于是它们转向『分布视角』。我们选择可复现，是因为我们的目标是『可被审计、可被第三方从同一份日志重算与复核的社会实验』——在这个目标下，种子化 RNG + LLM 判定冻结 + 哈希链日志是唯一能同时满足『可追溯、可重算、可 A/B』的路径。我们不主张『同 seed 跨跑一致』（那对 LLM 不可达），我们主张的是『同日志重放逐位一致』——这是一条更弱但真正可交付的承诺。」**

---

## 5. 严格区分：已核实 vs 推测/领域常识

### 5.1 【已核实】（附出处）
1. **GA 温度与随机**：`gaf/run_gpt_prompt.py:70/142/269/430/606/703`（temp 0.8/1/0.5/0）；`execute.py:83/100/102`、`plan.py:687/695`（`random.*` 未播种）。
2. **GA 直调 OpenAI、嵌入无缓存**：`gaf/gpt_structure.py:276-281`；`requirements.txt`（`openai==0.27.0`）。
3. **AI Town 未播种 `Math.random()`**：`convex/world.ts:134`、`aiTown/agent.ts:114/174/195/222`、`aiTown/agentOperations.ts:34/129/159/175`、`aiTown/player.ts:154/193/211`。
4. **AI Town 仅 importance 用 temp 0.0**：`convex/agent/memory.ts:256`。
5. **AI Town `HistoricalObject` 仅用于渲染平滑**：`ARCHITECTURE.md`（Historical tables 一节）。
6. **Agentopia temp 0.7 + 局部 seed**：`config.example.json`；`world.py:1196-1199`、`god.py:257-262`、`position_application.py:360-385`。
7. **AgentSociety V2 提供 JSONL replay + Ray 异步**：官方文档首页（readthedocs）。
8. **Project Sid 自称 preliminary results、10–1000+、PIANO**：arXiv:2411.00114 摘要/引言。
9. **NetLogo BehaviorSpace 原生多跑 + 输出均值/标准差**：docs.netlogo.org/behaviorspace。
10. **AI Economist 为双层深度 RL + 经济仿真**：arXiv:2004.13332 摘要；仓库含 `run_configs`/rllib 配置（文件树）。
11. **EconAgent 为 LLM-ABM、代码已发布**：arXiv:2310.10436 摘要。

### 5.2 【领域常识 / 推测 / 未核实】（**不得当作已证事实**）
| 编号 | 事项 | 状态 |
|---|---|---|
| P1 | OpenAI `seed` 仅 "best effort"、不保证逐位一致 | 领域常识（官方文档语义），未逐字引用 |
| P2 | AI Economist 的 RL/仿真以 seed 驱动、报告多轮方差 | 推测（未逐行核验 `run_configs` 之 seed 字段） |
| P3 | EconAgent 是否报告多种子/多轮 | **未核实**（未获取其可复现细节/代码） |
| P4 | Sugarscape 完全确定性、可复现 | 领域常识（Epstein & Axtell 1996），未核验其原始仿真代码 |
| P5 | Project Sid「无种子/无方差」 | **记为「未见」**（技术报告未在可获取内容中出现），**不等于不存在** |
| P6 | GA「用消融替代多种子」的解读 | GA 论文确有消融；「替代多种子」是本次**分析性推断** |
| P7 | 各对象「实测跨跑方差」 | 本次为**静态证据核验**，未运行任何实验 |

---

## 附：本报告引用的关键出处
- GA 代码：`/tmp/gaf/run_gpt_prompt.py`、`persona_cognitive_modules_{execute,plan}.py`、`prompt_template/gpt_structure.py`、`environment/frontend_server/requirements.txt`
- AI Town 代码：`/tmp/ai-town/convex/{world.ts,agent/memory.ts,aiTown/agent.ts,aiTown/agentOperations.ts,aiTown/player.ts,util/xxhash.ts}`、`ARCHITECTURE.md`
- Agentopia：见 `v1.1/11-agentopia-reuse-assessment.md`
- 论文/文档：arXiv:2304.03442（GA）、arXiv:2411.00114（Project Sid）、arXiv:2502.08691（AgentSociety）、arXiv:2004.13332（AI Economist）、arXiv:2310.10436（EconAgent）、docs.netlogo.org/behaviorspace、agentsociety.readthedocs.io

---

*（可复现性调研报告结束 — emergence-researcher）*
