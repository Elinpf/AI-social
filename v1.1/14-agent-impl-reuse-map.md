# 14 · 人格 Agent 实现的「可直接照搬」核验与复用图

> 文档类型：以**许可证与代码为据**的可拍板复用图（回答「能不能照搬、搬哪个文件、许可证是否允许、要改多少」）
> 作者：emergence-researcher（涌现社会实验调研专家）
> 日期：2026-10-10
> 核验对象（均**真实克隆/下载后逐文件阅读**，非只看 README）：
> - `a16z-infra/ai-town`（AI Town）— 本地 `/tmp/ai-town`（tarball 解压，源文件）
> - `joonspk-research/generative_agents`（Stanford Smallville 官方代码）— 本地 `/tmp/gaf`（逐文件下载源码）+ `/tmp/genagg`（LICENSE/README）
> - `Neph0s/Agentopia` — 沿用 `11-agentopia-reuse-assessment.md`（已核验，本次不重做）
> 证据标记：**【已核实】**=可追溯到具体文件路径/行号/许可证文本/GitHub API；**【未证实】**=无法从仓库确证。
> 说明：本报告分 **§A 研究对象事实**、**§B 逐模块复用图**、**§C Agentopia vs AI Town 差异对比**（本次新增）、**§D 确定内核兼容性**、**§E 推荐路线与避坑**、**§F 已核实/未证实清单**。

---

## §0. 结论速览（TL;DR）

| 问题 | 结论 |
|---|---|
| **有没有「现成可直接照搬」的人物 Agent 架构？** | **有可照搬的「组件」，但没有可以整体照搬「系统」**。三仓库都缺我们的确定内核与死亡/经济机制，且都与「日志可重放 + LLM 判定冻结」冲突。 |
| **许可证** | **AI Town = MIT（可商用/二改）**；**Generative Agents = Apache-2.0（可商用/二改）**；**Agentopia = 无 LICENSE 文件**（GitHub `license:null`，用户已口头放行；若对外发布/分发建议向作者确认授权）。 |
| **最能直接照搬的部分** | ① **Smallville 的 Agent 认知架构**（`perceive/retrieve/plan/reflect/execute`，Apache-2.0，模块最清晰）；② **AI Town 的记忆检索三因子代码 + 前端 PixiJS 可视化 + 引擎分层范式**（MIT）；③ **Agentopia 的文件系统式长记忆 + 中文人格资产**。 |
| **必须自建的部分** | **确定性内核（时钟/裁决器/事件日志/重放）、经济闭环、死亡续命、确定性统计**——三仓库都没有，且都不能直接兼容我们的铁律。 |
| **明确推荐** | **内核自建；Agent 侧以 Generative Agents 认知架构为主参照（Python、Apache-2.0、最 canonical），AI Town 作为工程范式/前端/向量记忆的可复用组件（MIT、活跃维护）；Agentopia 作为长时程记忆与中文资产参考。** 详见 §E。 |
| **要改多少** | 若走推荐路线，**可直接搬运/编译通过的代码约 15–30%**（记忆检索三因子、可视化、部分工具函数）；**改后可用约 25–40%**（人格/记忆/日程/对话需接我们的确定性日志与冻结口径）；**必须自建约 40–55%**（内核/经济/死亡/统计）。 |

---

# §A. 研究对象事实（许可证为最高优先级）

## A.1 许可证一手核实（**结论均追溯到 LICENSE 文件文本或 GitHub API license 字段**）

| 仓库 | LICENSE 文件 | 许可证文本首行 | GitHub API `license.spdx_id` | 可商用 | 可二改 | 义务 |
|---|---|---|---|---|---|---|
| **a16z-infra/ai-town** | ✅ 存在 `LICENSE`（1067 B）| `MIT License` + `Copyright (c) 2023 a16z-infra` | **MIT** | ✅ | ✅ | 保留版权与许可声明 |
| **joonspk-research/generative_agents** | ✅ 存在 `LICENSE`（11335 B）| `Apache License Version 2.0, January 2004` | **Apache-2.0** | ✅ | ✅ | 保留声明、**标明修改**、含专利授权、NOTICE 保留 |
| **Neph0s/Agentopia** | ❌ **无 LICENSE 文件** | —（仅 `README.md:175`、`docs/README.zh.md:171` 文字声称 MIT）| **null** | ⚠️ 法律上默认保留所有权利 | ⚠️ | 需向作者确认授权 |

> **【已核实】** AI Town LICENSE 原文（`/tmp/ai-town/LICENSE`）：
> `MIT License` / `Copyright (c) 2023 a16z-infra` / "Permission is hereby granted, free of charge, ... to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software"。
> **【已核实】** Generative Agents LICENSE 原文（`/tmp/genagg/LICENSE`）：`Apache License Version 2.0, January 2004`。
> **【已核实】** Agentopia：`git ls-files | grep -i license` 无输出；GitHub API `"license": null`。
>
> **Agentopia 授权提示（按 leader 要求如实标注）**：用户已口头放行使用 Agentopia。**若未来需对外发布或分发含其代码的产物，仍建议向作者确认授权并补 LICENSE 文件**——因 README 的 MIT 声明缺少标准许可证文本与版权人署名，不构成完整可依赖的授权。

## A.2 各仓库工程事实

| 维度 | a16z AI Town | Stanford Generative Agents | Agentopia |
|---|---|---|---|
| 语言/栈 | **TypeScript**；后端 Convex（响应式 DB+serverless+向量检索+调度器），前端 React + PixiJS | **Python**；Django 前端 + 自研后端；`openai==0.27.0`(旧 SDK)、numpy、gensim、matplotlib、Django 2.2 | **Python**；轻量自研 + 多 LLM SDK（openai/anthropic/google-genai） |
| 部署门槛 | 中（Convex 账号或 Docker；`docker compose up`） | 较高（Django 2.2 + 旧 Python 生态 + OpenAI key；依赖重） | 中（pip + config.json + LLM 端点） |
| 模型要求 | **可插拔**：OpenAI / Together.ai / Ollama / 任意 OpenAI 兼容；默认 chat `gpt-4o-mini`，embedding `text-embedding-ada-002`(1536)/`mxbai-embed-large`(1024) | **硬编码 OpenAI**（`gpt-3.5-turbo`/`gpt-4`/`text-embedding-ada-002`，`gpt_structure.py`） | **可插拔**：OpenAI 兼容/vLLM、Claude、Gemini、Azure |
| 活跃度 | created 2023-07-16，**pushed 2026-08-26**，★10609 / forks 1219 / issues 73，活跃 | created 2023-07-23，**pushed 2024-08-05**，★22206 / forks 3113 / issues 145，成熟但**停更** | created 2026-06-05，pushed 2026-06-05，★214 / forks 30 / issues 3，一次性发布 |
| 中文支持 | 无（英文角色） | 无（the_ville，英文） | **有**：`world.language` en/zh，`data/school` 中文高中世界 |
| 规模定位 | 小镇「一起玩」；**游戏态 < 几十 KB**，十万级对象不适配 | 25 Agent / 2 天；研究 demo | 100 Agent × 3 世界 × 10 年（长时程） |

> **【已核实】** AI Town 技术细节出处：`ARCHITECTURE.md`（18712 B，顶层图/引擎/Agent 记忆全述）、`convex/util/llm.ts`（provider 可插拔 + 维度常量）、`convex/agent/memory.ts`、`convex/constants.ts`（`NUM_MEMORIES_TO_SEARCH=3`）、`data/characters.ts`。
> **【已核实】** GA 技术细节出处：`reverie/backend_server/persona/persona.py`、`persona/memory_structures/{associative_memory.py,scratch.py,spatial_memory.py}`、`persona/cognitive_modules/{perceive,retrieve,plan,reflect,execute,converse}.py`、`persona/prompt_template/gpt_structure.py`、`environment/frontend_server/requirements.txt`。

---

# §B. 逐模块复用图

> 三档判定：**🟢 直接照搬**（许可证允许且代码可基本原样用/轻改即用）／**🟡 改后可用**（思路与结构可借鉴，需接入我们的确定性日志与冻结口径）／**🔴 必须自建**。
> 依据均给**具体文件路径**。

## B.1 M1 人格/身份配置

| 档位 | 来源 | 文件路径与理由 |
|---|---|---|
| 🟢 | **GA 的 identity stable set** | `persona/memory_structures/scratch.py`：`innate`(L0 永久特质)/`learned`(L1 稳定)/`currently`(L2 当前)/`lifestyle`/`living_area`；`get_str_iss()` 生成「身份稳定集」摘要注入所有 prompt。**结构可直接照搬**，与我们的 M1 对齐度高。 |
| 🟢 | **AI Town 角色表** | `data/characters.ts`：`{name, character(sprite), identity(字符串), plan(字符串)}`；`convex/aiTown/agentDescription.ts` 的 `AgentDescription{identity, plan}`。**极简配置，直接可搬**。 |
| 🟡 | **Agentopia 人格画像** | `data/*/persona/<name>/profile/year=*.json`（含 traits 定量分/技能/资产/价值观/目标）。**字段最丰富，可作 M1 schema 蓝本**，但需按我们口径裁剪。 |
| 结论 | M1 可基本「照搬结构 + 自定 schema」；**建议以 GA 的 ISS + Agentopia 画像字段合成**，不照搬 Agentopia 代码（无 LICENSE）。 |

## B.2 M2 记忆（存储/检索/反思）

| 档位 | 来源 | 文件路径与理由 |
|---|---|---|
| 🟢 | **GA 记忆流（最有价值）** | `persona/memory_structures/associative_memory.py`：`ConceptNode`(type=event/thought/chat, poignancy, embedding_key, keywords, depth)；`seq_event/seq_thought/seq_chat`；`kw_strength_*`。**检索三因子**见 `persona/cognitive_modules/retrieve.py`：recency=`recency_decay**i` + importance=`poignancy` + relevance=`cos_sim`，`gw=[0.5,3,2]`，`n_count=30`。**可直接照搬**（注意其检索为 O(N) 全表扫描，需换成向量索引）。 |
| 🟢 | **GA 反思机制** | `persona/cognitive_modules/reflect.py`：`importance_trigger_max=150`，`importance_trigger_curr<=0` 触发反思，生成 focal points → 检索 → insights。**可直接照搬**。 |
| 🟢 | **AI Town 记忆检索（现代实现）** | `convex/agent/memory.ts`：会话摘要 + `calculateImportance`(LLM 0–9) + embedding → **Convex 向量库** `memoryEmbeddings`；`searchMemories` 用 `ctx.vectorSearch` + overfetch(×10) + `rankAndTouchMemories` 按 relevance+importance+recency(`0.99**hours`) 排序；反思触发=最近 100 条 importance 之和 >500；`NUM_MEMORIES_TO_SEARCH=3`。**工程实现最值得照搬**（向量检索 + 缓存，`convex/agent/embeddingsCache.ts`）。 |
| 🟢 | **Agentopia 文件式长记忆** | `src/agents/functions.py` 的 `list/read/update_scratchpad` + `role_agent.py:61/98/111/184` 的 read-before-write；`memory/scratchpad/{general,characters/<p>,others/<t>}.jsonl` append-only。**结构可照搬**（按无 LICENSE 提示，建议参考设计）。 |
| 🔴/🟡 | **冻结与可重放** | 三者的 memory 都**无「LLM 输出冻结/可重放」**：GA 每次 `get_embedding`/LLM 直调；AI Town 在 Convex action 里实时调 LLM 写库。**需自建「记忆写入必须来自被冻结的事件」的封装**。 |
| 结论 | M2 **可大量照搬**：存储结构用 GA、检索加权用 GA、工程检索用 AI Town、长记忆文件化用 Agentopia；**但记忆写入通道必须挂到我们的确定性事件日志**（🔴 自建薄封装）。 |

## B.3 M3 关系/印象

| 档位 | 来源 | 文件路径与理由 |
|---|---|---|
| 🟡 | **GA 关系（隐式）** | `scratch.py` 的 `chatting_with`/`chat`/`chatting_with_buffer`（`{名字: 视野半径}`）；`associative_memory.get_last_chat(target)`；`converse.py` 的 `generate_summarize_agent_relationship`。**关系是「对话缓存 + 印象」，非结构化关系图**——可改后接入我们的关系状态。 |
| 🟡 | **AI Town 关系（图）** | `playerDescription` / `participatedTogether` 图（`ARCHITECTURE.md` L187 保存 world 时更新）；`memory.ts` 里记忆带 `playerIds`。**「谁和谁一起待过」的图可直接借鉴**。 |
| 🟡 | **Agentopia 有向喜爱/尊重图 + PageRank** | `src/world/reward.py` 的 `build_social_graphs`/`pagerank`/`calculate_social_rewards`。**关系图聚合思路可借鉴**，但打分由 LLM 产生（\(\text{llm\_judged}\)），与铁律冲突。 |
| 结论 | M3 无「纯照搬」；**建议自建结构化关系状态**，检索/图聚合借鉴 AI Town（图）+ Agentopia（PageRank），**打分口径改为确定性**（🔴/🟡）。 |

## B.4 M4 日程与活动推进

| 档位 | 来源 | 文件路径与理由 |
|---|---|---|
| 🟢 | **GA 计划/日程（最完整）** | `persona/cognitive_modules/plan.py`：`generate_wake_up_hour`/`generate_first_daily_plan`/`generate_hourly_schedule`/`generate_task_decomp`/`generate_new_decomp_schedule`；`scratch.py` 的 `daily_req`/`f_daily_schedule`/`f_daily_schedule_hourly_org`（**递归分解：日→小时→更细**）。**可直接照搬思路与结构**。 |
| 🟢 | **GA 执行/移动** | `persona/cognitive_modules/execute.py`、`reverie/backend_server/maze.py`（`Maze`：world/sector/arena/game_object 四级地址）、`path_finder.py`（A* 寻路）。**离散网格 + 寻路可直接照搬**（适合我们的确定性内核）。 |
| 🟡 | **Agentopia 周/日四阶段** | `src/world/clock.py` + `plan/contact/activity/review` 四阶段 + `scheduling.py` 的 `Schedule/MessageCenter`。**周尺度骨架很契合我们的 v1.1**，但需重写为确定性时钟。 |
| 🟡 | **AI Town 活动推进** | `ARCHITECTURE.md` 的 tick/step 模型 + `convex/aiTown/{movement,location,worldMap}.ts`。**在线平滑推进范式**，与我们的「周尺度离散回合」不同，参考即可。 |
| 结论 | M4 **GA 可直接照搬**（日程分解 + 网格寻路 + 执行）；**时间骨架可借 Agentopia 的周/日四阶段**，但**时钟与推进必须换我们的确定内核**。 |

## B.5 M6 对话/传播

| 档位 | 来源 | 文件路径与理由 |
|---|---|---|
| 🟢 | **GA 对话** | `persona/cognitive_modules/converse.py`：`agent_chat_v1/v2`、`generate_one_utterance`、`generate_decide_to_talk`/`generate_decide_to_react`（`plan.py:301/311`，决定是否搭话/反应）、`generate_summarize_ideas`、`generate_next_line`、`generate_inner_thought`、`open_convo_session`。**结构化、可直接照搬**。 |
| 🟢 | **AI Town 对话** | `convex/agent/conversation.ts`（`startConversationMessage`/`continueConversation`/`leaveConversation`，注入 personality+memories 的 prompt 工程）；`convex/aiTown/conversation*.ts`（会话状态机 invited/walkingOver/participating）。**在线对话与会话状态机可借鉴**。 |
| 🟡 | **传播链** | GA 的「决定搭话/反应」+ 消息进 memory 形成传播；AI Town 的 conversation membership。**传播观测口径需自建**（我们的 M8 观测量）。 |
| 结论 | M6 **GA/AI Town 对话生成均可照搬**；**传播的可审计口径必须自建**（对接确定性日志）。 |

## B.6 Agent 主循环（perceive→retrieve→plan→act→reflect）

| 档位 | 来源 | 文件路径与理由 |
|---|---|---|
| 🟢 | **GA 主循环（标准范式）** | `persona/persona.py` 的 `Persona.move()`：`perceive → retrieve → plan → reflect → execute`；`perceive`(`cognitive_modules/perceive.py`) 用 `vision_r=4/att_bandwidth=3/retention=5`；`execute`(`execute.py`)；`open_convo_session`(`converse.py`)。**这是教科书级实现，直接照搬**。 |
| 🟢 | **AI Town Agent 循环** | `convex/aiTown/agent.ts`：`Agent.tick`（游戏内决策）+ `startOperation`（异步 LLM 长任务 `agentDoSomething`/`agentRememberConversation`/`agentGenerateMessage`）；`convex/aiTown/agentOperations.ts`。**「游戏循环 + 异步 LLM 外挂」范式可照搬**——**这与我们「分层决策 + 事件驱动」高度同构**。 |
| 🟡 | **Agentopia 周循环** | `role_agent.py` 的 `plan/contact/act/review` + `settle_week`。**阶段骨架可借鉴**。 |
| 结论 | 主循环 **GA 为主、AI Town 的异步 LLM 外挂范式为辅**，**均可照搬结构**；**但每步的 LLM 调用必须经我们的「冻结 + 日志」封装**（🔴 自建）。 |

## B.7 可视化/观测前端

| 档位 | 来源 | 文件路径与理由 |
|---|---|---|
| 🟢 | **AI Town 可视化（最佳直接复用）** | `src/components/{PixiGame,PixiStaticMap,Character,Player,Messages,PlayerDetails,MessageInput}.tsx`；`src/App.tsx`；`data/gentle.js`(地图) + `data/spritesheets/*`(角色精灵)。**MIT 许可、像素风小镇可视化 + 历史平滑回放（`engine/historicalObject.ts` + `useHistoricalValue`）可直接照搬**。 |
| 🟡 | **GA 前端** | `environment/frontend_server/`（Django + templates + `compressed_storage` + 浏览器回放）。**较旧、依赖重**，参考即可。 |
| 🔴 | **「可审计观测台」** | 我们要求的「只读事件日志 → 确定性重放/指标」三仓库都没有。**必须自建**（我们的 03 分册统计程序 + 08 扩展）。 |
| 结论 | 前端 **AI Town 的 PixiJS 可视化可直接照搬**用来看「小镇在发生什么」；**冷冰冰的审计观测台自建**。 |

### B.8 复用图一览

| 模块 | 直接照搬 🟢 | 改后可用 🟡 | 必须自建 🔴 |
|---|---|---|---|
| M1 人格/身份 | GA ISS、AI Town characters | Agentopia 画像 | 与确定性配置绑定 |
| M2 记忆 | GA memory stream/reflect + AI Town 向量检索 | Agentopia 文件记忆 | **LLM 输出冻结/记忆写入通道** |
| M3 关系 | — | GA 对话印象、AI Town 图、Agentopia PageRank | **结构化关系 + 确定性打分** |
| M4 日程/活动 | GA plan/execute/maze/path | Agentopia 周四阶段、AI Town tick | **确定性时钟/推进** |
| M6 对话/传播 | GA converse、AI Town conversation | — | **传播可审计口径** |
| 主循环 | GA `move()`、AI Town `tick+startOperation` | Agentopia 周循环 | **每步 LLM 冻结+日志** |
| 可视化 | AI Town PixiJS + 历史回放 | GA Django 前端 | **审计观测台** |
| 内核 | — | AI Town 引擎分层范式（仅参考） | **时钟/裁决器/事件日志/重放/经济/死亡/统计** |

---

# §C. Agentopia vs a16z AI Town 差异对比（本次新增）

| # | 维度 | **Agentopia**（Neph0s/Agentopia） | **a16z AI Town** |
|---|---|---|---|
| 1 | **定位与适用场景** | **长期人生模拟 + 用模拟轨迹反训模型**（研究框架，年尺度，3 个世界） | **可部署的小镇 starter kit**（可扩展地基，多人在线小镇，天/小时尺度） |
| 2 | **许可证与代码可用性** | ❌ **无 LICENSE 文件**（`license:null`；README 文字称 MIT）。用户已口头放行；**若对外发布/分发建议向作者确认授权** | ✅ **MIT**（`LICENSE` 文本 + API `spdx_id=MIT`，Copyright 2023 a16z-infra）；**可商用/二改/再许可** |
| 3 | 语言/栈、部署门槛、依赖 | Python；轻量自研 + 多 LLM SDK；pip+config.json；门槛中 | TypeScript；Convex（DB+serverless+向量检索+调度）+ React/PixiJS；Convex 账号或 Docker；门槛中 |
| 4 | 人格配置 | 画像丰富（traits 定量分/技能/资产/价值观） | 极简（`identity`/`plan` 字符串，`data/characters.ts`） |
| 5 | 记忆机制 | **文件系统式 scratchpad**（`general/characters/others` JSONL，read-before-write，append-only 版本） | **向量记忆**（会话摘要→embedding→Convex 向量库→三因子重排；`memory.ts`） |
| 6 | 关系/印象 | 有向喜爱/尊重图 + PageRank（`reward.py`，**LLM 打分**） | `participatedTogether` 图 + 记忆带 `playerIds`（**结构化、无主观打分**） |
| 7 | 日程推进 | 年/周/日 + Plan→Contact→Activity→Review，程序排期 | tick 60/s + step 1/s，输入表驱动，RTS 式寻路 |
| 8 | 对话传播 | 结构化社交动作 + 自由文本活动；`god_model` 选发言者 | 会话状态机（invited/walkingOver/participating）+ LLM 对话 |
| 9 | 主循环 | 周循环 `plan/contact/act/review` | `Agent.tick` + 异步 `startOperation`（**游戏循环 + LLM 外挂**） |
| 10 | **确定性/可复现** | ❌ 只有**局部 tie-break 种子**（`world.py:1196`、`god.py:257`、`position_application.py:360`）；**无全局 event log/哈希链/replay** | ❌ 引擎**单线程、输入驱动、tick 确定**，但输入来自 LLM；**无重放/审计哈希链**；`historicalObject` 只用于渲染平滑 |
| 11 | 世界引擎性质 | **`god_model`（LLM 裁决）**：活动判定/事件生成/职位评估，**"without hard-coded rules"** | **状态同步式引擎**：`convex/engine` 确定性 tick + 输入表；**LLM 不在引擎内**，只在 agent 异步任务里生成「意图输入」 |
| 12 | 与「引擎必须确定性」冲突程度 | 🔴 **高**：引擎本体就是 LLM，替换=重写 `god.py` | 🟡 **中**：引擎本体已是确定性 tick，冲突只在「输入非确定 + 无冻结/无重放」——**架构更接近我们，可作范式参考** |
| 13 | 规模与长时程 | 100 Agent × 10 年（论文）；长时程是设计目标 | 小镇级；**游戏态须 < 几十 KB，十万级对象不适配**（ARCHITECTURE.md 明述） |
| 14 | 成本量级 | 论文 ~**13.7B token/世界**、~186h 墙钟（输入 token 为主，随记忆增长上升） | 未给总量；靠**空闲暂停 + 记忆检索数可调（`NUM_MEMORIES_TO_SEARCH`）** 控成本；本地 Ollama 可零 API 成本 |
| 15 | 中文支持 | ✅ 有（`data/school` 中文世界） | ❌ 无（英文角色） |
| 16 | **对我们的适配度（贡献模块）** | 强：M2 长记忆、M4 周四阶段、M1 画像、中文资产；弱：引擎/确定性 | 强：**可视化前端、向量记忆、引擎分层范式、对话状态机**；弱：长时程、无中文 |
| 17 | 接入我们确定性内核的改造量 | 大（引擎须整体替换） | 中（引擎范式可借；agent 侧 LLM 需包冻结层；前端可直接用） |
| 18 | 已验证踩过的坑 | 环境模型承担过多、reward 价值假设强、归因粗糙、记忆 token 增长是主瓶颈 | 状态须塞进内存、单线程、输入延迟 ~1.5s、LLM/embedding 成本、无长时程机制 |

**对比小结**：
- **AI Town** = 「**工程与前端最强、许可证最干净、引擎范式最接近我们**」，但**不是长时程/带经济社会的框架**。
- **Agentopia** = 「**长时程社会机制与中文资产最强**」，但**许可证不清、引擎是 LLM、不可复现**。
- 两者**互补**：AI Town 供「引擎分层 + 前端 + 向量记忆 + 对话状态机」，Agentopia 供「长时程记忆 + 周尺度骨架 + 中文人格」。

---

# §D. 与「确定内核」的兼容性评估

> 我们的三条铁律：① 世界引擎/裁决器必须**确定性代码**；② 日志**可重放**（同日志逐位一致）；③ **LLM 判定需冻结**（`llm_judged_metric_count==0`）。

## D.1 逐仓库冲突点

| 仓库 | 冲突 | 具体位置 | 严重度 |
|---|---|---|---|
| **Generative Agents** | 环境+认知**全程 LLM**，无 seed/无重放 | `gpt_structure.py`（`openai` 直调 `gpt-3.5/4`、`get_embedding`）；`reverie.py` 主循环 | 🔴 高 |
| | 无事件日志/哈希链 | 全仓无 replay 机制 | 🔴 高 |
| | 检索 O(N) 全表 + 每步 embedding，成本随记忆爆炸 | `retrieve.py:new_retrieve`（遍历全部 event+thought） | 🟡 中（工程） |
| **AI Town** | 引擎本体确定，但**输入来自 LLM**，无冻结 | `convex/engine/abstractGame.ts`（tick/step 确定）；`convex/aiTown/agent.ts`+`convex/agent/*`（LLM 生成输入） | 🟡 中 |
| | 无重放/审计 | `engine/historicalObject.ts` 仅渲染回放，非审计 | 🟡 中 |
| | 状态须入内存、单线程 | `ARCHITECTURE.md` L286-291 | 🟡 中 |
| **Agentopia** | 引擎=LLM（`god_model`） | `src/world/god.py` 11+ 处 `model=get_config()["god_model"]` | 🔴 高 |
| | 指标含 LLM 评判 | `reward.py`（social/subjective 由 LLM 打分）；`role_agent.py:1694 judge_others` | 🔴 高 |
| | 无死亡/经济/市场 | 全仓无 death/market/tax 命中 | 🔴 高（缺功能） |

## D.2 兼容性结论

- **没有任何一个仓库满足我们的三条铁律**——**内核必须自建**（沿用 v1 的 `03-engine-stats.md`）。
- **但 Agent 侧可以「包裹式复用」**：把 GA/AI Town 的认知与对话模块的 **LLM 调用点收敛为一个「冻结层」**——凡 LLM 输出（utterance/plan/importance/embedding）在**首次生成时写入不可篡改日志并缓存**，重放时**直接读缓存而非重调 LLM**。这样即可满足「LLM 判定冻结 + 逐位重放」，同时复用它们的成熟 prompt/记忆结构。
- **AI Town 的引擎范式（单线程、输入表、引擎独占状态表）与我们的「中央裁决器 + 事件日志」同构**，是**最值得借鉴的架构参考**（虽语言/框架不同）。

---

# §E. 推荐路线与避坑

## E.1 推荐路线

> **内核自建；Agent 侧「GA 认知架构为主干 + AI Town 工程/前端组件 + Agentopia 长记忆与中文资产」。**

1. **内核侧（🔴 自建）**：沿用 v1 `03-engine-stats.md` 的确定性内核（时钟/事件队列/中央裁决器/哈希链日志/重放）+ 经济/死亡/统计。**范式可参考 AI Town 的 `convex/engine`（输入表 + 单线程 + 独占状态）**。
2. **Agent 侧（🟢/🟡 复用）**：以 **GA 的 `persona.py` 主循环 + memory_structures + cognitive_modules** 为**主干**（Apache-2.0、Python、模块最清晰、与我们的 Python 引擎栈一致）；**M2 检索工程**借 AI Town 的向量检索三因子。
3. **LLM 冻结层（🔴 自建薄封装）**：所有 LLM 调用经统一入口，首次输出落日志；重放读缓存。这是把「LLM 判定」变「可重放」的关键。
4. **前端（🟢 复用）**：**AI Town 的 PixiJS 小镇可视化（MIT）直接照搬**做「观察窗口」；另建只读日志的**审计观测台**。
5. **长时程与中文（🟡 参考）**：记忆增长治理借 Agentopia（摘要限流/压缩档案）；中文人格资产可参考 `data/school`（注意无 LICENSE）。

**若团队偏 TypeScript / 需要在线可视小镇**：可把主干换成 **AI Town**（引擎分层 + agent 循环 + 前端全套，MIT），但**长时程/经济/死亡/中文仍需自建**——改造量更大。

## E.2 「哪些坑已有人踩过、我们可避开」

| 坑 | 谁踩过 | 我们如何避开 |
|---|---|---|
| **记忆无限增长 → token/成本爆炸** | GA（每步遍历全部记忆）、Agentopia（论文承认记忆增长是主瓶颈） | ① 用 AI Town 式**向量检索 + 摘要限流**（`NUM_MEMORIES_TO_SEARCH`、压缩档案进 prompt）；② 记忆写入挂确定性日志，容量可审计 |
| **检索 O(N) 全表扫描** | GA `retrieve.py` | 直接采用 AI Town 的**向量索引 + overfetch(×10) + 三因子重排** |
| **旧 SDK / 硬编码 OpenAI** | GA `gpt_structure.py`（`openai==0.27.0`） | 只搬**结构**，模型层用我们可插拔封装（AI Town `llm.ts` 思路） |
| **引擎状态必须塞进内存** | AI Town（`ARCHITECTURE.md` 明述 < 几十 KB） | 用我们的事件日志 + 存档快照，状态不必常驻内存 |
| **环境模型承担过多（判定不透明）** | Agentopia `god.py` | 裁决器改为**确定性规则**，LLM 只生成描述 |
| **归因粗糙 / reward 价值假设** | Agentopia（按 Agent-年选轨迹） | 我们的**确定性统计程序**按事件粒度归因，口径可复现 |
| **许可证不清** | Agentopia（无 LICENSE） | 优先 MIT（AI Town）/ Apache-2.0（GA）组件；Agentopia 仅参考设计或先取授权 |
| **无长时程/无死亡机制** | AI Town、Agentopia（后者无死亡） | 我们的 **v1 死亡续命 + 长时程**设计补齐（这是我们的增量价值） |

---

# §F. 已核实 vs 未证实

## F.1 已核实（附文件路径/许可证文本/API）
1. **AI Town = MIT**：`/tmp/ai-town/LICENSE` 文本 + GitHub API `spdx_id=MIT`（Copyright 2023 a16z-infra）。
2. **Generative Agents = Apache-2.0**：`/tmp/genagg/LICENSE` 文本 + GitHub API `spdx_id=Apache-2.0`。
3. **Agentopia 无 LICENSE**：`git ls-files | grep -i license` 无输出 + GitHub API `license:null`。
4. **GA 主循环与记忆**：`persona/persona.py`（`move()`）、`memory_structures/associative_memory.py`、`cognitive_modules/retrieve.py`（`gw=[0.5,3,2]`、`n_count=30`、`recency_decay`）、`reflect.py`（`importance_trigger_max=150`）、`plan.py`、`execute.py`、`converse.py`、`maze.py`。
5. **GA 硬编码 OpenAI**：`persona/prompt_template/gpt_structure.py`（`gpt-3.5-turbo`/`gpt-4`/`text-embedding-ada-002`）。
6. **AI Town 记忆与引擎**：`convex/agent/memory.ts`（向量检索 + 三因子 + 反思阈值 500）、`convex/util/llm.ts`（provider 可插拔 + 维度常量）、`ARCHITECTURE.md`（引擎/输入表/单线程/状态上限）、`data/characters.ts`、`convex/constants.ts`（`NUM_MEMORIES_TO_SEARCH=3`）。
7. **活跃度/星标**：均来自 GitHub API（见 §A.2）。
8. **Agentopia 事实**：见 `11-agentopia-reuse-assessment.md`（god_model、无死亡、文件式 memory、中文 `data/school`）。

## F.2 未证实 / 限制
| 编号 | 事项 | 说明 |
|---|---|---|
| U1 | 三仓库**实测性能/成本** | 本次为**静态代码核验**，未运行仿真，成本数据来自论文/文档，非本地实测 |
| U2 | GA 代码在**现代 Python/新 OpenAI SDK** 下的可运行性 | 依赖 `openai==0.27.0`、Django 2.2，**未实测**能否直接跑通 |
| U3 | AI Town **改造为长时程/50+ Agent** 的实际上限 | `ARCHITECTURE.md` 自述状态须小，**未实测**上限 |
| U4 | Agentopia 的**授权状态** | README 声称 MIT 但无文件；版权人/隐含授权**未确证** |
| U5 | AI Town 前端**迁移到我们技术栈**的工作量 | 其前端耦合 Convex `useQuery`/`useHistoricalValue`，**未做迁移验证** |
| U6 | GA 的 tarball 完整克隆 | 网络受限，GA 采用**逐文件下载**关键源码 + contents API 核对文件清单，**非整仓克隆**；文件大小与路径已核对一致 |

---

## 附：关键文件路径索引

**AI Town（MIT）**
- `LICENSE`｜`ARCHITECTURE.md`｜`convex/agent/memory.ts`｜`convex/agent/conversation.ts`｜`convex/agent/embeddingsCache.ts`｜`convex/aiTown/agent.ts`｜`convex/aiTown/agentOperations.ts`｜`convex/engine/{abstractGame,schema,historicalObject}.ts`｜`convex/util/llm.ts`｜`convex/constants.ts`｜`data/characters.ts`｜`src/components/{PixiGame,PixiStaticMap,Character,Player,Messages}.tsx`

**Generative Agents（Apache-2.0）**
- `LICENSE`｜`reverie/backend_server/{reverie.py,maze.py,path_finder.py}`｜`reverie/backend_server/persona/persona.py`｜`persona/memory_structures/{associative_memory,scratch,spatial_memory}.py`｜`persona/cognitive_modules/{perceive,retrieve,plan,reflect,execute,converse}.py`｜`persona/prompt_template/gpt_structure.py`｜`environment/frontend_server/requirements.txt`

**Agentopia（无 LICENSE）**
- 见 `11-agentopia-reuse-assessment.md`

---

*（复用图报告结束 — emergence-researcher）*
