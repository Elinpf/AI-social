# 11 · Agentopia 开源仓库可直接复用性评估

> 文档类型：可拍板的技术评估（供用户决策「能不能直接用、用哪部分、要改多少」）
> 作者：emergence-researcher（涌现社会实验调研专家）
> 日期：2026-10-09
> 评估对象：`https://github.com/Neph0s/Agentopia`（commit `da264aa6d82cca98f2051bcf794ff5dd98f10fdb`，2026-06-05）
> **方法**：真实 `git clone`（深度 1）到本地 `/tmp/agentopia-repo` 后**实际阅读源码 / 配置 / 数据 / 许可证**，并调用 GitHub API 核对仓库元数据；**非仅看 README**。
> 证据标记：**【代码】**=可追溯到具体文件路径/行号；**【文档】**=README/config 等仓库内文件；**【外部】**=论文/媒体；**【不确定】**=无法从仓库确证。

---

## 0. 结论速览（TL;DR）

| 问题 | 结论 |
|---|---|
| **能直接整体复用（路线 A）吗？** | **不能，且不建议。** ① **法律障碍**：仓库**没有 LICENSE 文件**，GitHub API 的 `license` 字段为 `None`（README 声称 MIT 但无许可证文本，权属不清）；② **架构冲突**：核心「环境引擎」是**纯 LLM（`god_model`）**，与我们「裁决器必须是确定性代码」的铁律**正面冲突**；③ **缺核心机制**：**没有死亡/破产/市场/税收**；④ **不满足确定性统计铁律**：仿真**不可整体重放**，且指标含 **LLM 评判**（`llm_judged_metric_count != 0`）。 |
| **能部分复用（路线 B）吗？** | **能，且这是推荐路线。** 建议**只复用**：① 人格/画像数据模型（`profile/year=*.json`）；② 文件系统式长期记忆（scratchpad + read-before-write）；③ 周/日时间结构与 Plan→Contact→Activity→Review 阶段骨架；④ 每日活动/公开活动/偶遇的**数据 schema 与调度思路**；⑤ 中文世界样例（`data/school`）。**引擎（含 god_model 裁决）、经济、奖励、统计必须自建/替换。** |
| **要改多少？** | 若走路线 B，**可直接搬运的代码占比约 20–35%**（数据模型 + 记忆 + 时间/调度骨架 + 部分工具函数）；**必须重写或替换约 40–55%**（god_model 裁决层、奖励/统计、世界的确定性契约）；**不可用约 10–25%**（RFT 训练链路、LLM 评判奖励）。 |
| **最大的两个坑** | ① **法律**：无 LICENSE 文件，**商用/二次分发存在真实风险**，须先与作者确认授权；② **不可复现**：其仿真无全局确定性日志与重放，**无法满足我们「同 seed 逐位一致 / replay(log)」的要求**。 |

**一句话推荐**：**走路线 B —— 把 Agentopia 当作「人格生活层的设计蓝本 + 中文数据资产 + 记忆机制参考」，而不是「实现框架」**；其引擎/裁决/经济/统计全部由我们按 v1 的确定性铁律自建。

---

## 1. 事实层（每条附代码/文件/许可证依据）

### 1.1 开源许可证 —— ⚠️ **最严重问题：无 LICENSE 文件**

| 证据 | 内容 |
|---|---|
| **【代码】** `git ls-files \| grep -iE "licen\|copying"` | **无任何输出** → 仓库未跟踪任何 LICENSE/COPYING 文件 |
| **【代码】** `find . -not -path './.git/*' -iname '*license*'` | **无输出** |
| **【外部】GitHub API** `https://api.github.com/repos/Neph0s/Agentopia` | `"license": null`（GitHub 也判定为「无许可证」） |
| **【文档】** `README.md:175` | "This project is released under the MIT License." |
| **【文档】** `docs/README.zh.md:171` | "本项目基于 MIT 许可证发布。" |

**结论（关键）**：
- 仓库**只在 README 文字里声称 MIT**，**但没有 LICENSE 文件、没有版权持有者信息**。
- 按 GitHub 与多数司法辖区的默认规则：**没有 LICENSE 文件的公开仓库 = 保留所有权利（all rights reserved）**。README 的 MIT 声明可视为**作者意图的公开表达**，但**缺乏标准许可证文本与版权人署名**，法律上**不足以构成完整、可依赖的授权**。
- **风险等级：高（商用/二次分发/再许可）**。
- **必须动作**：若决定复用，**先通过 issue/邮件向作者确认授权**，要求补一个带版权人的标准 MIT/Apache-2.0 LICENSE 文件，或取得书面授权。**在此之前不得把其代码并入我们的交付物或产品。**

### 1.2 仓库结构与模块划分【代码】

```
Agentopia/
├── config.example.json        # 配置模板（需 cp 为 config.json）
├── requirements.txt
├── data/
│   ├── apartment/             # 示例世界：现代合租公寓（英文）
│   ├── school/                # 示例世界：中国高中（中文；persona 直接是中文）
│   └── persona_template/      # persona 数据格式模板
├── scripts/
│   ├── run_world.py           # 主入口（324 行）
│   ├── build_rft_data.py      # 计算 advantage + 生成 RFT 训练数据（641 行）
│   ├── compute_metrics.py     # 运行后量化指标（691 行）
│   ├── extract_activity_dialogues.py  # 抽取活动对话
│   └── time_analysis.py       # 逐周墙钟耗时
├── src/agents/                # 角色 agent：prompts / context / memory
│   ├── role_agent.py(1793)  prompts.py(2164)  data_manager.py(2703)
│   ├── functions.py(186)    context.py(90)    response_validator.py(553)
└── src/world/                 # 仿真引擎：调度 / 活动 / 奖励 / 环境
    ├── god.py(2249)  activity.py(1561)  world.py(1559)  reward.py(1088)
    ├── scheduling.py(895)  position_application.py(1206)  clock.py(350)
    ├── locations.py(334)  mapgen.py(152)  solo/joint/public_activity_data.py
    ├── cleanup.py(142)  run_manager.py(61)
└── src/config.py(81)  src/utils.py(3475)
```
**规模**：`src`+`scripts` 合计约 **2.3 万行 Python**；`find -type f` 共 1797 个文件（含 data 样例）。

### 1.3 运行时依赖与外部服务【代码/文档】

`requirements.txt`：
```
openai>=1.0.0 / anthropic>=0.40.0 / google-genai>=0.3.0 / google-auth>=2.0.0
tiktoken / requests / jsonlines / file-read-backwards / python-dotenv
```
- **无重框架**（无 LangChain/无 RL 库），核心是**自研轻量 Python + 多个 LLM SDK**。
- 外部服务：**LLM API**（OpenAI 兼容/vLLM、Anthropic、Gemini/Vertex、Azure OpenAI）。**无数据库、无消息队列、无向量库依赖**（记忆是文件系统 JSONL，不是向量检索）。
- 对比 a16z AI Town 的 Convex+向量库：Agentopia **运行时依赖更轻**，但**可扩展性靠文件系统与目录并发**。

### 1.4 对模型的要求 —— **不强依赖 Qwen3.5-397B**（这是好消息）【文档/代码】

- `config.example.json` 末尾：`role_model` / `god_model` / `fallback_model` 三个槽位，配合 `models` 字典，**内建 4 类后端**：
  - `claude-sonnet`（anthropic）、`gpt-4o`（OpenAI 兼容 url+key）、`my-vllm-model`（vLLM 本地，`vllm_model_name`+`context_length`）、`gemini-flash`（Vertex 凭据）。
- **【文档】** README §Model Configuration 明确列出 4 种后端及所需字段。
- `scripts/run_world.py` 支持 CLI 覆盖 `--role-model`、`--god-model`、`--world`、`--language`（注释示例含 `Qwen3.5-397B-A17B`）。
- **【代码】** `src/utils.py` 内对 `qwen`、`claude`、`gemini`、`gpt-5`、`azure-responses` 等做了分支适配（如 `utils.py:1026-1035`、`utils.py:1249-1262` 处理 Qwen3/3.5 的 reasoning 字段），说明**作者自己就跑了多种模型**。
- **结论**：**框架模型无关**；论文用 Qwen3.5-397B-A17B 是实验选择，不是代码硬绑定。**但 `god_model` 需要是「够强」的模型**（`god_model_max_tokens: 16384`），因为环境引擎承担了大量判定。**【外部】**论文提到输出非法时用 Gemini 3 Flash 兜底重生成。

### 1.5 是否含训练环节与所需算力【代码/文档】

- **仓库包含「训练数据构建」，不含「训练本身」**：
  - `scripts/build_rft_data.py`（641 行）从一次已完成仿真中选高 advantage 轨迹、打包 SFT 数据，输出 `rft_data/*.jsonl`（详见 README §Life Reward Training 与 `reward.py:895-1062` 的 `calculate_returns/calculate_advantages/select_top_trajectories`）。
  - **实际的 SFT 微调脚本、分布式训练框架、模型权重均不在仓库内**。
- **【外部】**论文的训练算力（30 节点 × 8×H100，1 epoch）**只是论文报告，仓库不含复现脚本** → 我们**无法据此在本地复现训练**，也**不需要**（我们 v1.1 不训练底层模型）。

### 1.6 部署与运行成本量级

- **【外部】**论文报告：每世界平均 **约 137 亿 token、约 56.7 万次调用、约 186 小时墙钟**；输入 token 为主成本，且**随记忆增长而上升**。
- **【代码】**控成本手段：`max_concurrency`（默认 10）、`god_model` 只吃「压缩档案」而非全量记忆、记忆上下文有摘要/限流。
- **量级判断**：**50 Agent × 长时程的主要成本是 LLM 推理费**，与 v1 的「分层决策控成本」结论一致；Agentopia **没有** T0/T1/T2 分层降级机制，成本控制相对粗放。

### 1.7 活跃度【外部 GitHub API】

| 字段 | 值 |
|---|---|
| created_at | 2026-06-05 |
| pushed_at（最后代码推送） | **2026-06-05** |
| stars / forks | 214 / 30 |
| open_issues_count | 3 |
| license | **null** |
| archived | false |

- **判断**：**论文配套的一次性代码发布**（最后推送与建仓同日），**无持续维护迹象**；社区有一定关注（214 stars）。**合作/提问可能得不到响应**（尽管有 3 个 open issue）。

### 1.8 中英文支持【代码/文档】

- **【文档】** `docs/README.{zh,ja,ko}.md` 提供中/日/韩 README。
- **【文档/代码】** 配置 `world.language` 支持 `en` / `zh`；`data/school` 为**中国高中世界，persona 直接是中文**（例：`data/school/persona/丛雪薇/profile/*.json`）。
- **结论**：**中英文双语支持完备**（甚至含中文本地化世界样例），这一点**对我们极有价值**。

---

## 2. 与 v1.1 架构的逐条对照

> 我们 v1.1 的铁律见 `v1/05-v1-proposal.md` §2.2 / §6；对照基准 = 「确定性内核 + 人格生活层 + 涌现观测层」三层架构。

### 2.1 冲突 ①：**「世界引擎/裁决器必须是确定性代码」 vs `god_model`（LLM 环境引擎）** —— **正面冲突，且难以拆改**

- **【代码】** 环境引擎全在 `src/world/god.py`（2249 行），**至少 11 处** `model=get_config()["god_model"]` 调用，功能包括：
  - `evaluate_solo_activity`(471)、`evaluate_joint_activity`(711)、`evaluate_public_activity`(869) —— **活动结果判定**
  - `generate_public_events`(1076)、`god_generate_encounter_events`(1282) —— **世界事件生成**
  - `god_evaluate_position_application`(1415)、`god_design_positions`(1725)、`god_grow_positions`(1891)、`update_yearly_profile`(2135) —— **职业/档案评估**
  - `generate_consumption_offers`(593) —— **消费场景生成**
- **【文档】** README 直言："An **environment model (a capable LLM)** serves as the generative engine … **without hard-coded rules**."
- **判定**：
  - 它的「社会规律」**大量来自 LLM 判定**，不是来自独立真实环境（这一点第三方解读也指出）。
  - **能否拆掉换成确定性裁决器？** **理论可以、工程代价极大**：这些函数不是「校验器」，而是**生成器 + 裁判 + 状态更新器三合一**。若替换为确定性规则，等于**重写整个 `god.py` 的语义**（活动结果如何由规则算出？偶遇如何生成？），并会**彻底改变仿真行为**——那已不是「复用」，而是「借壳重写」。**结论：不可直接拆换；应自建裁决层。**

### 2.2 冲突 ②：**「归零即死 + 可续命 + 惩罚」 vs 它没有死亡机制** —— **完全缺失**

- **【代码】** 全仓 `src`+`scripts` 检索 `death|dead|dies|bankrupt|alive|lifespan|survival` → **零命中**。
- **【代码】** 检索 `market|tax|auction|order_book|clearing|interest|loan|debt` → **无经济市场相关命中**（仅 "interest class" 等无关词）。
- **【文档】** `config.example.json` 的 `economy` 只有：`weekly_income`、`extra_work_income_per_day`、`living_standards`（frugal/moderate/comfortable/luxurious 四档消费）。
- **判定**：Agentopia 的「经济」= **收入 + 消费 + 职位**的**生活水平模型**，**没有**订单簿/撮合/税收/借贷/负资产/破产死亡。**我们的死亡与续命机制需完全自建**；它至多提供「经济奖励」这一维度（=年末存款−年初存款）作为参照。

### 2.3 对照 ③：**「单一小镇 + 先跑周尺度」 vs 它的「一年/周/日 + 3 世界」** —— **时间结构高度可借鉴，世界设定需收敛**

- **【代码】** `src/world/clock.py`：`Stage`(IntEnum)、`TimeState`、`Clock`，层级 `year → week → stage/day/slot`。
- **【文档】** `config.example.json` world.time：`start_year:2020, n_year:10, n_week:10, n_day:5, n_contact_slot:5`。
- **【代码】** 每周阶段：**Plan → Contact → Activity → Review**（`role_agent.py` 的 `plan/contact/act/review`）。
- **判定**：
  - 它的**周尺度 + 四阶段**与我们 v1.1「周尺度时间结构」**高度契合**，**可直接借鉴骨架**（这是路线 B 的核心复用点之一）。
  - 差异：它是 `year` 为顶层（10 年）且**每个 run 单世界**（`world.name`=apartment/school），而论文跑了 3 个世界（第三个 Arcane Academy 未见样例数据）。我们**单一小镇**目标与之兼容（配置单世界即可）。
  - ⚠️ 它的 clock **不是**我们要求的「全局确定性回合时钟 + 事件队列 + 哈希链」；需要**重写为确定性内核**。

### 2.4 冲突 ④：**「确定性统计程序（llm_judged_metric_count==0）」 vs 它的奖励/指标口径（含 LLM 评判）** —— **有实质冲突**

- **【代码】** `src/world/reward.py`：`calculate_social_rewards`(300) 依赖 **LLM 打出的喜爱/尊重分**（`_validate_ranking_response`(396) 是 LLM 回复解析）；`compute_subjective_rewards`(661) 来自环境模型的满足度判定；`calculate_total_rewards`(799) 做 z-score 加权（`social 0.4 / economy 0.2 / gamma 0.9`，见 config.reward）。
- **【代码】** `src/agents/role_agent.py:1694 judge_others()` —— 角色 Agent 用 LLM **互相打分**（affection/respect）。
- **【代码】** `scripts/compute_metrics.py`：**自身不调 LLM**，只读 `data_dir` 下的 JSONL（`reward.jsonl`、`state.jsonl` 等）做**确定性聚合**；**但**它聚合的原始信号（affection_scores/respect_scores、fulfillment、satisfaction）**本身是 LLM 生成的**（见 `compute_social_eval_metrics`(386) 读 `ranking`）。
- **【代码】** 另有**独立 LLM 评判层**：`src/agents/response_validator.py`(553) + config `response_validation.{enabled, judge_model}`（默认 `enabled:false`）。
- **判定**：
  - Agentopia 的「指标」在**聚合层是确定性的**（给定数据可重算），但在**信号层依赖 LLM** → **不满足我们 `llm_judged_metric_count==0`**。
  - 更关键：**它的整个仿真不可重放**（见 2.5），数据本身不可复现，聚合再确定也无意义。
  - **可借鉴**：它的**数据落盘 schema（每 agent 的 state/schedule/activity/reward JSONL）**与**指标维度划分**（系统/联系/活动/成长/满足度/社会评价）值得我们参考，但**判定必须换确定性口径**。

### 2.5 附加冲突 ⑤：**确定性/可复现性 —— 它只有局部确定性，没有全局可复现**【代码】

- **【代码】** 它确有**局部确定性种子**（tie-break 用），例如：
  - `world.py:1196-1199` 偶遇事件用 `sha256("Y{t.year}-W{t.week}-D{day}-encounter")` 派生 seed；
  - `god.py:257-262`、`position_application.py:360-385` 用 hashlib 派生稳定排序；
  - `world.py:190-191` 初始模型分配用 `random.Random(data_dir)`。
- **【代码】** **但**：核心内容由 LLM 生成（`temperature:0.7`），**没有全局 event log / 哈希链 / replay / state hash**；`compute_metrics` 是对**已落盘结果**的聚合，**不是** `State = reduce(apply, EventLog, seed)`。
- **判定**：**同 seed 重跑 ≠ 逐位一致**；**无法 `replay(log)` 到任意回合**。这与 v1「确定性与可审计」的根本目标**冲突**。**若采用路线 B，必须用我们的确定性内核替换其世界推进**。

### 2.6 契合点汇总（路线 B 的复用依据）

| 契合点 | 依据 | 可复用程度 |
|---|---|---|
| 人格/画像数据模型 | `data/*/persona/<name>/profile/year=*.json`（见 §3.1 样例） | **高**：直接作为 M1/M3/M7 的 schema 蓝本 |
| 文件系统式长期记忆 | `functions.py` 的 `list/read/update_scratchpad`；`role_agent.py:61/98/111/184` 的 `_opened_scratchpads` read-before-write；`data/.../memory/scratchpad/{general,characters/<p>,others/<t>}.jsonl` | **高**：M2 直接参考（append-only JSONL 与我们日志哲学一致） |
| 周/日时间结构与四阶段 | `clock.py`、`config.world.time`、`plan/contact/activity/review` | **高**：M4 骨架 |
| 活动/公开事件/偶遇的数据 schema | `solo/joint/public_activity_data.py`、`scheduling.py` 的 `PublicEvent/Schedule/MessageCenter` | **中-高**：M4/M5/M6 参考 |
| 中文世界样例 | `data/school`（中文 persona + `worldview.json`）；`world.language=zh` | **高**：直接可用的中文人格/世界观资产 |
| 指标维度划分 | `compute_metrics.py` 的 system/contact/activity/growth/fulfillment/social_eval | **中**：观测维度参考（口径须换确定性） |

---

## 3. 三种路线对比与推荐

### 路线 A：直接整体复用
- **做法**：clone 后改 config、接我们的模型，直接跑。
- **代价**：低（数天）。
- **风险**：**不可接受**——
  1. **法律**：无 LICENSE 文件，商用/交付不合规（§1.1）；
  2. **架构**：裁决器是 LLM，**直接违反铁律**（§2.1）；
  3. **缺机制**：无死亡/经济/市场（§2.2）；
  4. **不可复现**：无确定性日志与重放（§2.5）；
  5. **统计不合规**：含 LLM 评判（§2.4）。
- **判定**：**否决**。

### 路线 B：部分复用（记忆 / 时间结构 / 人格配置 / 中文数据），引擎自建 —— ✅ **推荐**
- **做法**：
  - **搬运/改写**：人格画像 schema、scratchpad 记忆机制、周/日时间与四阶段骨架、活动/事件数据 schema、中文 persona 资产；
  - **自建**：确定性内核（时钟/事件队列/中央裁决器/哈希链日志）、经济闭环、死亡续命、确定性统计；
  - **替换**：`god_model` 裁决层 → 确定性裁决器（LLM 仅保留「描述/生成内容」，不参与判定）。
- **代价**：中（约 **4–8 人周**，取决于裁决层替换深度）。
- **风险**：中——
  - 需**逐条确认可搬运代码的许可证**（在授权到位前，**只参考设计、不复制代码**）；
  - 记忆与人格数据可复用，但**引擎语义要重写**，存在「看起来能抄、实际要重写」的落差。
- **工作量估算**：
  | 子项 | 复用/自建 | 估算 |
  |---|---|---|
  | 人格画像 schema + 中文资产 | 复用（改写 adapter） | 0.5–1 周 |
  | 记忆机制（scratchpad/read-before-write） | 复用（移植到我们日志体系） | 1 周 |
  | 周/日时间 + 四阶段骨架 | 借鉴（重写为确定性） | 1–1.5 周 |
  | 确定性内核（时钟/裁决/日志） | **自建**（v1 已有 03 分册） | 已在 v1 计划内 |
  | god_model 裁决层替换 | **重写** | 1.5–3 周 |
  | 经济/死亡/统计 | **自建**（v1 已设计） | 已在 v1 计划内 |
- **判定**：**推荐**。

### 路线 C：不复用，仅参考设计
- **做法**：只读其论文/代码，把设计经验写进 v1.1，不搬任何代码。
- **代价**：低（数天阅读）。
- **风险**：低（无法律与耦合风险）；**唯一损失**是放弃其**中文 persona 资产**与**文件系统记忆的成熟实现**。
- **判定**：**保守可用**，但**性价比低于路线 B**（B 在同样的低风险下多拿到「人格/记忆/时间结构/中文数据」）。

### 推荐结论
> **推荐路线 B**：**复用「人格生活层的数据模型与记忆机制 + 周/日时间骨架 + 中文人格资产」，自建「确定性引擎 + 经济 + 死亡 + 统计」，并把 `god_model` 裁决层替换为确定性裁决器。**
> **前置条件（阻塞项）**：**在复制任何代码前，必须先取得作者对许可证的明确授权**（补 LICENSE 或书面许可）；在此之前，**只参考设计、不复制代码**，走「路线 C 的安全子集」。

---

## 4. 已证实 vs 不确定项

### 4.1 已证实（可追溯到代码/文件/许可证文本）
1. **无 LICENSE 文件**：`git ls-files` 无 license；GitHub API `license: null`；README.md:175、docs/README.zh.md:171 仅文字声称 MIT。【代码/外部】
2. **环境引擎 = 纯 LLM**：`src/world/god.py` 11+ 处 `model=get_config()["god_model"]`；README 明言 "without hard-coded rules"。【代码/文档】
3. **无死亡/破产/市场/税收**：`src`+`scripts` 关键词零命中；economy 仅收入/消费/职位。【代码】
4. **模型无关**：config `role_model/god_model/fallback_model` + 4 类后端；README §Model Configuration。【代码/文档】
5. **训练数据构建在仓库、训练本身不在**：`scripts/build_rft_data.py`；无训练脚本/权重。【代码/文档】
6. **记忆 = 文件系统 scratchpad + read-before-write**：`functions.py`、`role_agent.py:61/98/111/184`。【代码】
7. **时间结构**：`clock.py` + `config.world.time`（year/week/day/slot）+ Plan→Contact→Activity→Review。【代码/文档】
8. **指标含 LLM 信号**：reward.py 的 social/subjective 来自 LLM 判定；compute_metrics 只做确定性聚合。【代码】
9. **中英文支持**：docs README 多语言；`data/school` 为中文世界。【文档/代码】
10. **活跃度**：created/pushed 均 2026-06-05，214 stars / 30 forks / 3 open issues / 未归档。【外部】

### 4.2 不确定项（**不得当作事实**）
| 编号 | 不确定项 | 说明 |
|---|---|---|
| N1 | **实际法律授权状态** | README 声称 MIT 但无文件；**是否有隐含授权、版权人是谁**，须与作者确认，**不可推定**。 |
| N2 | 训练所需算力细节的可复现性 | 论文声称 30×8×H100，但**仓库无脚本**，无法核验；【外部】 |
| N3 | 运行成本（137 亿 token/世界、186h） | 来自【外部】论文/解读，**未在本地实测**。 |
| N4 | 第三个世界（Arcane Academy）数据 | 论文有、仓库样例仅 apartment/school；**未在仓库确证**。 |
| N5 | 长期维护意愿 | 仅一次推送，**issue 是否会被回应未知**。 |
| N6 | `god_model` 换更弱模型后的行为退化程度 | 需实测，仓库未给消融。 |

---

## 5. 附：关键文件路径索引（供复核）

- 许可证相关：`README.md:173-175`、`docs/README.zh.md:169-171`、`git ls-files | grep -i license`（空）、GitHub API `license=null`
- 环境引擎：`src/world/god.py`（`evaluate_solo_activity:471`、`evaluate_joint_activity:711`、`evaluate_public_activity:869`、`generate_public_events:1076`、`god_generate_encounter_events:1282`、`god_evaluate_position_application:1415`、`god_design_positions:1725`、`god_grow_positions:1891`、`update_yearly_profile:2135`）
- 奖励/统计：`src/world/reward.py`、`scripts/compute_metrics.py`
- 记忆：`src/agents/functions.py`、`src/agents/role_agent.py`
- 时间/调度：`src/world/clock.py`、`src/world/scheduling.py`
- 人格/数据 schema：`data/apartment/persona/<name>/profile/year=*.json`、`data/school/persona/丛雪薇/profile/*.json`
- 配置：`config.example.json`、`src/config.py`
- 入口：`scripts/run_world.py`、`scripts/build_rft_data.py`
- 本地克隆：`/tmp/agentopia-repo`（commit `da264aa6d82cca98f2051bcf794ff5dd98f10fdb`）

---

*（评估报告结束 — emergence-researcher）*
