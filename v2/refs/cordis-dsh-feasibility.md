# Cordis / DSH 可行性方案：插件化 Agent 层能否承载 50+（含 TS↔Python 边界建议）

> 文档类型：技术选型建议 + spike 方案（**不直接开写**）｜ 作者：solution-architect
> 状态：**Draft v0.1（增量落盘，逐节追加）**
> 任务：T201-cordis-dsh-feasibility
> 标注约定：**【已核实】**=有来源链接/代码位置；**【未验证】**=推断或未实测；**推荐**=给 Leader 的倾向，非最终裁决。
> 上游无关性说明：本项目现状 = **Python 世界引擎 + 生活层 + 观测层 + PixiJS 前端**（用户 2026-10-12 将项目重定义为「游戏化 AI 城镇工程」）。

---

## 0. 一页建议（TL;DR，供 Leader 向用户汇报与裁决）

**结论：不建议「全 TS/Cordis 重写」（路线 A）；建议先跑半天 spike（路线 D），通过后采用「窄混合」（路线 C-narrow）——Python 世界引擎仍是唯一真值源，Cordis/DSH 只承接 agent 侧「内容生成 + 会话日志/技能/压缩」等叶子能力，经官方 Python SDK 以子进程方式驱动。**

理由（三条）：
1. **DSH 插件能点名，但它们是「编码 Agent 运行时」的插件，不是「小镇社会模拟」的插件。** 真正能复用的是**基础设施层**（会话日志、LLM 适配、技能注册、压缩、subagent），而**不是**我们核心需要的「确定性裁决器 / 经济 / 生命周期 / 社会观测」——那部分 DSH 完全没有，且其 agent loop 是 LLM 驱动的工具循环，与我们「LLM 只出意图与话术 · 世界引擎唯一真值」的边界**语义不同**（见 §1、§4）。
2. **我们最核心的资产（世界规则/经济/观测/确定性 replay）是 Python**，DSH/Cordis 是 **TypeScript/Node**。全量重写（A）会把这些资产保值率压到 ~10–20%（见 §2）；而混合（C）保留 ~90%，代价是跨语言边界与「双日志/双真值」的一致性风险（见 §2、§6）。
3. **DSH 是 developer preview、迭代极快、且 vendored Cordis 已累积 18 项本地补丁**（见 §1 证据）。跨语言 + 跟踪快变 upstream，长期维护成本高；先 spike 用**可判定的成功/失败判据**决定「值不值」，避免贸然押注。

**补充（应 T200/SKYCity 实证）**：我们既定的「**离散回合 + 单裁决器**」已用确定性换掉了并发复杂度，→ **跨语言的唯一理由只剩「插件生态复用」**；且「**50 agent 单进程**」**无任何实证**（SKYCity 实测 19），验证方法见 §5.5。

**给用户的三个决策点（见 §5 判据）**：spike 只需半天；若 S1–S4 全过 → 走 C-narrow；若 S2/S4 不过（需 fork/补丁过多）→ 保持路线 B（Python 自建插件化）；**A 仅在「愿意放弃 Python 资产、且团队愿意长线维护 TS 栈」时才考虑**。

---

## 1. Cordis 到底能给什么（Q1）

### 1.1 Cordis 本体（【已核实】）

- **定位**：`cordiverse/cordis`，一个**面向 TypeScript/Node 的元框架**，核心约 **2000 行 TS**；最初为 **Koishi**（QQ 机器人框架）打造的插件运行时，被 DSH **vendor 进仓库**（`vendor/cordis`，版本 `4.0.0-rc.7`，rescope 为 `@deepseek-ai/cordis`，并追加 **18 项本地修改**：生命周期加固、事务性配置加载、JSDoc 等）。
  来源：<https://juejin.cn/post/7673436957741236239>（掘金·宇擎智脑科技，2026-08-13）、<https://cordis.moe/zh-CN/guide/>
- **五个核心概念**：`Service`（命名的 `ctx` 键，任何插件可提供/消费）、`Fiber`（插件生命周期状态机 `PENDING→LOADING→ACTIVE→DISPOSED`）、`Effect`（注册即返回 disposer 的可逆副作用）、`inject`（声明式依赖等待）、`Events`（类型化 `emit/waterfall/serial/parallel`）。
  来源：<https://cordis.moe/zh-CN/guide/philosophy/disposable.html>（可逆副作用的形式化：`effect`/`restore`、上下文即「副作用插座」）
- **相比传统 DI 的关键差异**：不只是 IoC，而是**带 lifecycle + reactivity 的 plugin orchestrator**——① 服务可**运行时消失**（MCP 崩溃/限流），依赖方自动 `DISPOSED` 并在服务恢复后自动重新 `apply`；② `cordis.yml` + patch/overlay **多层配置组合 + HMR 热替换**；③ **waterfall 事件** = 事件系统上的 around-middleware（`next()` 短路/改写），如 `tools/pre-execute`、`agent/request`、`llm/stream`。
  来源：同上掘金文；<https://deepseek-harness.github.io/deepseek-harness/develop/cordis-tutorial/>
- **它解决的「Agent 特有问题」**：service 消失的**优雅降级**、声明式组合+HMR、配置 patch/overlay 组合、effect-scoped 资源管理（MCP 连接/PTY/file watcher/后台 job 统一生命周期）。
  来源：掘金文（同上）。

> **一句话**：Cordis 给的是**「可逆副作用 + 响应式依赖 + 配置即组合 + around-middleware 事件」**这套**插件运行时地基**，不提供任何领域能力（没有经济、没有世界、没有社会模拟）。

### 1.2 实际可复用的 DSH 插件（**点名，不泛泛说「生态」**）

**能点出具体的。** DSH 仓库 `packages/` 按能力系列分组，每组有权威包清单（来源：<https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/packages/README.zh.md>）。**与我们「游戏化 AI 城镇」相关的、真正可复用的，集中在基础设施层**：

| 我们需要的领域 | 可直接复用的 DSH 包（点名） | 复用价值 | 证据 |
|---|---|---|---|
| **LLM 接入（provider 无关）** | `dsh-llm`（抽象服务+消息/流式词汇）、`dsh-llm-deepseek*`、`dsh-llm-pi-ai`、`dsh-llm-retry`、`dsh-token-meter` | **高**：可替换 provider、重试、token 计量 | `packages/llm/README.zh.md` |
| **append-only 会话日志 + 折叠投影（≈我们的 event log + replay）** | `dsh-session`（仅追加 `SessionEvent` 日志）、`dsh-session-persistence` + `dsh-session-persistence-jsonl`（不可变 generation 文件、可选 **zstd**）、`dsh-session-checkpoint-policy`、`dsh-session-projection`（**增量折叠已提交事件为当前值**，`stateOf()/snapshot()`） | **高**：与我们的「哈希链日志 + 从日志重建 + 快照节流」**同构**，是 DSH 里最值得借鉴/复用的一块 | `packages/session/README.zh.md`、`docs/architecture.zh.md` |
| **会话检索/血缘/全文搜索（≈我们的观测/叙事血缘）** | `dsh-session-query`（统一查询+**关系追踪 lineage**+有界读取）、`dsh-session-query-sqlite`（**SQLite FTS5** 全文）、`dsh-session-log-export`（ZIP 导出） | **中高**：血缘/SQL 检索/导出，适合观测台与叙事检索 | `packages/session-query/README.zh.md` |
| **技能注册与加载** | `dsh-skill`（provider 注册表、本地 provider、面向模型的目录/loader） | **中**：agent 技能成长可挂此 | `packages/README.zh.md` |
| **上下文压缩（≈我们的记忆压缩档案）** | `dsh-compaction`（Service Definition + 基础 provider + 命令 consumer）、`dsh-context`（模型可见请求上下文） | **中**：记忆/token 治理参考 | `packages/README.zh.md` |
| **agent loop（可替换）** | `dsh-agent`（公开 `Agent` 约定）+ `dsh-agent-loop`（默认驱动器，`ctx.agentLoop`） | **低（语义不符）**：它是 **LLM 驱动的工具循环**，与我们的确定性内核 + 分层决策**不是一回事** | `docs/architecture.zh.md`、`packages/core/README.zh.md` |
| **目标 / 日程 / 计划 / 待办** | `dsh-goal`、`dsh-schedule`（host 拥有的定时后续）、`dsh-plan`、`dsh-todo` | **中低**：语义是「编码任务」，概念可借鉴，直接复用需改造 | `packages/README.zh.md` |
| **subagent / Agent Teams** | `dsh-subagent`、`experimental` 的 **Agent Teams**（持久 roster、任务状态、直接 inbox 协作，`ctx.agentTeams`） | **中（值得深挖）**：与「50+ agent 协作/调度」相关 | `docs/architecture.zh.md` |
| **运行时插件自省/装卸** | `dsh-extensions`（实时插件/服务检查与模型挂载/卸载） | **中**：可做「世界运行中热插拔 agent 能力」 | `packages/README.zh.md` |
| **工具接入** | `dsh-mcp`（外部 MCP server 工具 → 原生工具）、`dsh-fs`/`dsh-shell`/`dsh-sandbox`/`dsh-web` | **低**：多为编码 Agent 工具，城镇模拟基本用不上 | `packages/README.zh.md` |
| **测试基建（复现相关）** | `dsh-test-support`（testkit、**回放 replay**、Loader 冒烟测试） | **中**：与我们「可复现门禁」思路一致，可借鉴 | `packages/README.zh.md` |
| **Web GUI（前端）** | `dsh-client`、`dsh-host`（Web GUI 宿主 + `ui-*` 插件） | **低**：我们要的是 **PixiJS 像素小镇**，与 DSH 的通用 Web GUI 不同 | `packages/README.zh.md` |

**点名结论（诚实版）**：
- **能点出具体的**：`dsh-llm*`、`dsh-session*`、`dsh-session-query*`、`dsh-skill`、`dsh-compaction`、`dsh-context`、`dsh-subagent`、`dsh-extensions`、`dsh-test-support` —— **集中在「日志/LLM/技能/压缩/检索/协作」基础设施**。
- **点不出任何「社会模拟/经济/生命周期/社会观测」领域插件**：DSH 面向**编码 Agent**，**没有**这个世界模型。我们最核心的资产（世界规则/经济/观测）**无 DSH 插件可复用**，只能自建（这与 v1.1 结论一致）。
- **生态成熟度警告**：DSH 明确标注 **developer preview，会有 breaking changes**；第三方插件生态用 `dsh-plugin` GitHub topic 组织，尚处早期。来源：<https://github.com/deepseek-ai/deepseek-harness>（README）

### 1.3 与「Python 自建插件化」的能力对照

| 能力 | Cordis/DSH 提供 | Python 自建（DI + entry-points + 事件总线）可达到 |
|---|---|---|
| 依赖注入 | ✅ `inject` + `ctx` 服务键 | ✅ 有成熟库（如 `dependency-injector`、`pluggy`、`importlib.metadata` entry-points） |
| **可逆副作用 / 自动 dispose** | ✅ **框架级保证**（Effect + Fiber） | ⚠️ 需自建（`contextlib`/生命周期管理），无框架级保证 |
| **服务消失→依赖方自动重启** | ✅ **框架级** | ⚠️ 需自建（较复杂） |
| 配置即组合 + 多层 patch | ✅ `cordis.yml` + overlay | ⚠️ 需自建（Hydra/pydantic-settings 可部分覆盖，但无 HMR patch 语义） |
| HMR 热替换 | ✅ | ⚠️ 需自建 |
| 类型化事件 + waterfall（around-middleware） | ✅ | ⚠️ 需自建（`blinker`/自研，waterfall 语义要自写） |
| **LLM 适配 / 会话日志 / 检索 / 压缩** | ✅ **现成插件可点名复用** | 🔴 需自建或另找库 |
| **确定性整数 RNG / 哈希链 / 定点** | ❌（TS number 为 float64，需 BigInt 处理） | ✅ **Python 任意精度整数天然适配** |

> **关键判断**：Cordis 相对 Python 自建的**增益**主要是**「可逆副作用 + 服务消失自愈 + 配置组合/HMR + waterfall」这四件框架级能力**（自建约 6000–8000 行 + 长期 edge case 维护，来源：掘金文对「方案 B」的估算）。**对我们的价值取决于：我们到底需不需要「运行时热插拔 + 服务自愈」**——对一个**确定性离线仿真**来说，这套 reactivity 的价值**远低于**对一个长驻、多 provider、可热更的编码 Agent。

---

## 2. 四种路线的取舍（Q2）

> 评分维度同 v1.2 惯例：**铁律契合度 / 资产保值率 / 交付速度 / 运维复杂度（越低越好）/ 演进成本（越低越好）**，0–5 同向评分（越高越好）。

| 维度 | 权重 | A 全 TS/Cordis 重写 | B 保持 Python 自建插件化 | **C 窄混合（推荐）** | D 先 spike 再定 |
|---|---|---|---|---|---|
| 铁律契合（确定性引擎/同日志逐位一致） | 0.30 | 2（TS float64 需 BigInt 重做；内核须整体重写） | **5**（沿用现有 Python 内核） | 4（内核保 Python；agent 层不碰真值） | 5（不押注） |
| 资产保值率 | 0.25 | **1**（世界/经济/观测需重写，~10–20%） | **5**（~100%） | 4（世界/经济/观测 ~90%；仅 agent 内容层换栈） | 5 |
| 交付速度 | 0.15 | 1 | 4 | 3 | **5** |
| 运维复杂度（越低越高分） | 0.15 | 2（单栈但仍需跟踪快变 upstream） | 4（单栈） | 2（**双栈**：Node+Python + 协议 + 双日志） | 5 |
| 演进成本（越低越高分） | 0.15 | 2 | 3 | 3 | 4 |
| **加权** | 1.00 | **1.60** | **4.40** | **3.40** | **4.85** |

（算式：A = 0.30×2+0.25×1+0.15×1+0.15×2+0.15×2 = **1.60**；B = 0.30×5+0.25×5+0.15×4+0.15×4+0.15×3 = **4.40**；C = 0.30×4+0.25×4+0.15×3+0.15×2+0.15×3 = **3.40**；D = 0.30×5+0.25×5+0.15×5+0.15×5+0.15×4 = **4.85**。注：**D 是「先验证再定」的元步骤**，得分高反映「零押注 + 可判定」，不与 A/B/C 直接互斥——实际决策是 **D 通过后走 C、否则 B**。）

### 2.1 逐路线代价与风险

**A. 全 TS/Cordis 重写**
- 做法：世界引擎、经济、生命周期、观测层、GA 认知全部用 TS + Cordis 重写；前端沿用 PixiJS。
- 代价：① **确定性内核重写**——TS `number` 是 float64，我们的金额/哈希链/定点要求须改用 `BigInt` 或整型约定，**replay 逐位一致的验证要从头做**；② 经济/生命周期/观测的 v1/v1.1 资产（大量 Python 规则与测试）**基本清零**；③ 需跟踪 DSH 的 breaking changes。
- 风险：**最高**。除非团队决定“Python 资产不要了、全面转 TS”，否则**不推荐**。

**B. 保持 Python 自建插件化**
- 做法：用 `pluggy`/`dependency-injector`/entry-points + 自研事件总线，把现有 Python 代码插件化；**不复用 DSH/Cordis**。
- 代价：需自建约 6000–8000 行插件基建（evaluate：掘金文「方案 B」）；**放弃 Cordis 的框架级可逆副作用/服务自愈/HMR**。
- 优势：**单栈、零跨语言、资产 100% 保留、交付最快**。风险：中低（自研基建的 edge case）。
- **若不追求「运行时热插拔 + 复用 DSH 插件」，这是工程上最稳的路线。**

**C. 窄混合（Python 世界引擎 + TS/Cordis agent 层）**
- 做法：**Python 保持为唯一真值源**（世界/经济/生命周期/观测/确定性 replay）；**仅把 agent 侧的「内容生成」**（计划文本/对话/反思/描述）与「复用型叶子能力」（LLM 适配、会话日志、技能、压缩）放到 Cordis/DSH；两栈通过**官方 Python SDK（子进程 stdio JSON-RPC）**通信。
- 代价：① **跨语言边界**——官方 SDK 是 **子进程 + 行分隔 JSON-RPC**（`python/README.zh.md`：`deepseek_harness` 通过 stdio JSON-RPC 与内置 `dsh --profile sdk` 运行时通信），有**进程边界 + 序列化 + 每次调用延迟**；② **双日志/双真值风险**——DSH 的 `session` 日志与我们的哈希链事件日志会是**两套事实源**，必须明确「DSH 日志只做 agent 内容缓存，世界真值只在 Python」；③ **双栈运维**（Node + Python 环境、版本、CI）。
- 风险：**中**（一致性设计与双栈运维是主要风险，可通过“agent 层无状态、只产内容、经冻结层回写”约束缓解）。
- **这是「用户想用 Cordis + 复用 DSH 插件」与「保住 Python 核心资产」之间的折中点。**

**D. 先 spike 再定**
- 做法：半天 spike（见 §5）验证「DSH 插件复用收益」与「跨语言边界代价」。
- 代价：半天人力。收益：**用二元判据决定 C 还是 B**，避免押注。
- **推荐作为第一步。**

### 2.2 跨语言调用的延迟/一致性代价（专项）

- **调用形态（已核实）**：DSH 官方 Python 集成是 **子进程**（`dsh --profile sdk`）+ **行分隔 JSON-RPC over stdio**；不是进程内 FFI，也不是 HTTP 服务。来源：<https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/python/README.zh.md>
- **延迟（【未验证】，量级推断）**：进程内 Python 函数调用 ≈ μs；子进程 JSON-RPC 往返 ≈ **ms 级**（IPC + JSON 编解码）。**对「每回合数十次 LLM 内容生成」而言，ms 级 IPC 相对 LLM 秒级延迟可忽略**；但若把**每回合上千次的确定性内核结算**也做成跨语言调用，则不可接受 → **故内核必须留 Python，只有粗粒度的内容生成跨语言**。
- **一致性代价（关键风险）**：① 两套日志（DSH session log vs 我们的哈希链 event log）——**必须只认一套为真值**；② 若 DSH 侧引入 LLM 温度/重试不确定性，**我们已有的「LLM 判定冻结 + 重放不重调」机制必须由我们在 Python 侧强制**，DSH 侧输出只作「待冻结载荷」；③ 版本漂移（DSH 快变）可能改变内容生成行为 → 需把 DSH 版本纳入 `engine_version` 指纹。

*（§0–§2 完成）*

---

### 2.3 并发模型决定「要不要跨语言」（T200/SKYCity 实证，**关键**）

**实证输入（来自 T200 对 SKYCity 的拆解）**：
- SKYCity 用「**异步并发 + DB 行锁**」在 **19 Agent** 上跑通，代价是**行锁 / 条件 UPDATE / 重试 / 竞态复杂度**，且它是**单动作即提交、无哈希链**。
- 反过来：**「离散回合 + 单裁决器」可以完全绕开行锁/竞态复杂度**——即「**用确定性换并发复杂度**」（我们 v1/v1.2 的内核正是此路线）。

**→ 对 TS↔Python 边界裁决的直接含义（本文采纳）**：

| 若我们的运行时形态是… | 后果 | 是否需要跨语言 |
|---|---|---|
| **连续时间 / 异步并发**（多进程 / DB 行锁 / 竞态） | 并发复杂度高，Python 单进程不够，需外部 DB/锁 | **跨语言代价才可能值得** |
| **离散回合 + 单裁决器**（我们的现状与既定铁律） | **Python 单进程就够**，无行锁/竞态 | **跨语言的理由只剩「插件生态复用」** |

> **结论**：我们**已经选了「离散回合 + 单裁决器」**（v1.2 §1.4 P0–P6 调度），因此 **性能/并发不构成跨语言的理由**；**唯一可能的理由是「复用 DSH 插件生态」**——这正是 §1.2 要点名的东西。

---

## 3. 50+ 规模下 Cordis 是否合适（Q3）

### 3.1 事实基线

- **DSH/Cordis 是单进程 Node**（`dsh web` 默认单进程；Cordis 单线程 event loop）。来源：<https://github.com/deepseek-ai/deepseek-harness>（README“Run from npm/source”）、`docs/architecture.zh.md`（“不存在需要打补丁的特权内核”，插件树单运行时）。
- **DSH 的 agent 模型是「每 session 一个 `Agent`」**：`ctx.agents` 是活跃 agent 注册表，`dsh-agent-loop` 逐个驱动轮次。来源：`packages/core/README.zh.md`、`docs/architecture.zh.md`。→ **50 个 agent ≈ 50 个 `Agent` 实例挂在同一进程**。
- **我们的实测基线（来自本轮 T203 上游）**：N=20 × 84 回合 = **3782 s 墙钟 / 4814 次 LLM 调用 / 660,501 tokens**（折算 ≈ 57 次调用/agent/周、≈ 3.3k tokens/agent/周）。
- **⚠️ 规模实证缺口（来自 T200/SKYCity）**：**没有任何仓库实测过 50 个 agent loop**——SKYCity 实测的是 **19 Agent**，其 README 的“可调 50”与 juejin 文“可调到 50”**均未实测**。→ **本报告中所有“50 agent 可行”的判断一律为【推测/未验证】。**

### 3.2 判断：TS 单进程能否承载 50 个 agent loop？

**【推测/未验证】可能能，但瓶颈不在 Cordis/Node，而在 LLM 与内存——且「50」无任何实证。** 依据：
1. **agent loop 是 I/O 密集**（等 LLM 流式响应、等工具结果），不是 CPU 密集。Node 单线程 event loop 天然擅长**高并发 I/O**；50 个 agent 的 LLM 调用可异步并发（受 API 并发/限流约束，而非 Node）。
2. **量级核算（【未验证】，基于基线外推）**：50 agent ≈ **2.5×** N=20 的调用量 → 约 **12,000 次调用/周 · ~1.65M tokens/周**。即便把墙钟按并发打平，**瓶颈是 LLM 吞吐与费用**，不是 Node 的插件调度（Cordis 每次派发纳秒–微秒级，相对 LLM 秒级延迟可忽略）。
3. **CPU 密集的是「确定性世界结算」**（我们每回合的撮合/税/代谢/关系折叠）——这部分**绝不该放在 Node 单线程**做，也不该跨语言逐条调用（见 §2.2）。**正确分工**：Python 内核做批量 tick 结算；Node/Cordis 只做 I/O 型的内容生成。

**风险点**：① **内存**——50 个 Agent 各持上下文/记忆，DSH 的 session 状态会累积（DSH 自述“状态须可持久化”，用 JSONL + compaction 治理，`packages/session`、`packages/compaction`）；② **单进程故障域**——一个进程挂 = 全挂，需靠 DSH 的持久化 + 恢复（`session-checkpoint-policy`）；③ **Node 长驻稳定性**与 DSH 快变。

### 3.3 与 Python 方案的性能对比要点

| 对比项 | TS/Cordis 单进程 | Python（asyncio） |
|---|---|---|
| LLM 并发 I/O | ✅ 强（event loop） | ✅ 强（asyncio）——**两者对本项目等价** |
| 确定性 tick CPU | ⚠️ 单线程；float64 需 BigInt | ✅ 任意精度 int；numpy 批量 |
| 统计/数值 | ⚠️ 生态弱于 Python | ✅ numpy/scipy/pandas |
| 内存/上下文治理 | ✅ DSH 现成（session+compaction） | 🔴 需自建 |
| 50 agent 承载 | 可行（I/O-bound） | 可行（I/O-bound） |

**结论**：**50+ 规模不是选 Cordis 的决定性理由**——两边都能承载（注：**「两边都能承载 50」本身无实证**，见 §3.1、§5.5）。**决定性因素是「是否要复用 DSH 的内容/日志/技能插件」与「是否愿承担双栈」**，而非性能。

---

## 4. Generative Agents「像素级迁移」的具体含义与工作量（Q4）

### 4.1 「像素级迁移」的两种解读（先对齐语义）

- **解读 ①（本文采用）**：把 GA 的**认知流水线**尽量 **1:1（保真）** 迁移到 Cordis 的**插件模型**——每个认知模块变成一个 `ctx` 上的 service/plugin，**保留其行为与 prompt**，只改「LLM 调用的落点」（接到 DSH/Cordis 的 `llm` 服务或我们的冻结层）。
- **解读 ②**：把 GA 的**可视化/像素地图**按像素对齐迁移——这与「认知迁移」无关，那属前端（PixiJS），**不在本任务范围**。

> **【待确认】** 用户原话「Generative Agents 能否迁移到 cordis，像素级迁移」中「像素级」的确切所指。**倾向解读 ①**（保真迁移认知模块），若用户指 ②，则与 Cordis 无关。

### 4.2 GA 各模块 → Cordis 插件的适配性（逐模块）

| GA 模块（Python） | 来源文件 | 作为 Cordis 插件 | 适配性 | 说明 |
|---|---|---|---|---|
| 记忆流存储 | `memory_structures/associative_memory.py`（`ConceptNode`：event/thought/chat + poignancy + embedding_key + keywords） | ✅ 可做 `dsh-*-memory` 服务 | **高** | 纯数据结构 + 增删查，天然是 service；但 GA 是 O(N) 全表检索，须换向量索引（我们已有此结论） |
| 三因子检索 | `cognitive_modules/retrieve.py`（recency/importance/relevance，`gw=[0.5,3,2]`，`n_count=30`） | ✅ service | **高** | 纯函数打分，好迁 |
| 反思 | `cognitive_modules/reflect.py`（`importance_trigger_max=150`） | ✅ service/事件 | **高** | 触发阈值 + LLM 生成 insight，可挂 waterfall |
| 计划（递归分解） | `cognitive_modules/plan.py`（day→hour→task 分解） | ✅ service + `dsh-schedule`/`dsh-plan` 语义相近 | **中高** | 结构可迁，`dsh-plan` 是「编码任务计划」，语义需改造 |
| 执行/移动 | `cognitive_modules/execute.py` + `maze.py` + `path_finder.py`（网格 A*） | ⚠️ 可做 service | **中** | 网格寻路可迁；但**我们的世界是离散小镇场所图**，maze 需替换 |
| 对话 | `cognitive_modules/converse.py`（`generate_one_utterance`/`decide_to_talk`/`summarize_ideas`） | ✅ service | **高** | 纯 LLM 内容生成，最契合 |
| 感知 | `cognitive_modules/perceive.py`（`vision_r=4`） | ✅ service | **中高** | 视野半径需映射到我们的场所/可见性 |
| **主循环** | `persona/persona.py` `move()`（perceive→retrieve→plan→reflect→execute） | ❌ **不宜**直接作为 `dsh-agent-loop` | **低** | GA 主循环**每次全 LLM**、无冻结、无确定性内核；与我们的「分层决策 + LLM 只出意图」冲突（`14` §D.1） |
| **LLM 调用层** | `prompt_template/gpt_structure.py`（硬编码 OpenAI 旧 SDK） | 🔴 必须重写 | **低** | 不能照搬；应接 `dsh-llm` 或我们的冻结层 |
| scratch（`scratch.py`） | 全局「上帝对象」 | ⚠️ 拆分为多 service | **中** | GA 的 `scratch` 是集中状态，与 Cordis「服务化」相反，须拆分 |

### 4.3 适配「不适配」的部分（关键）

- **GA 主循环与 LLM 策略不适配 Cordis 的 agent-loop 语义**：GA `move()` 是「感知→检索→计划→反思→执行」的**每步全 LLM** 循环；而我们的铁律是「**LLM 只出意图与话术 · 世界引擎唯一真值 · 判定冻结**」。直接套 `dsh-agent-loop` 会把 LLM 拉进决策真值路径 → **违反铁律**。
- **正确做法**：把 GA 的**认知模块**作为 Cordis **service 插件**迁移（记忆/检索/反思/计划/对话），但**主循环与真值结算留我们的 Python 内核**（即 §2 的 C-narrow）。

### 4.4 工作量估计（【未验证】）

- GA 认知模块源码规模：`cognitive_modules/` + `memory_structures/` 约 **数千行 Python**（来源：`14` §F.1 文件清单）。
- **Python→TS 逐模块重写**（保行为/prompt）经验系数 **1.5–2.5×**；加上「接我们的冻结层 + 落不可篡改日志 + 重放不重调 LLM」的适配，**总量约 1–3 人周**（模块级），**不含**主循环/内核重做。
- 若**不换栈**（保持 Python，只借 Cordis 的**设计思想**），则工作量最小，但**拿不到 Cordis 运行时本身**。
- **【未验证】**：GA 在现代 Python/新 SDK 下能否直接跑（`14` U2），与迁移无关但影响参照物可用性。

---

## 5. spike 设计（Q5，半天可跑完）

> **目标**：用**二元判据**回答「Cordis/DSH 插件的**实际复用收益**值不值我们跨语言」。**不是**做产品原型。

### 5.1 spike 范围（严格限定）

- **环境**：`npx @deepseek-ai/dsh web --no-open` 起本地 DSH（来源：README）；或 `git clone` 后 `pnpm install && pnpm dsh web`。
- **实验对象**：① 一个**自定义 Cordis 插件**（按官方 tutorial：函数插件 + `name/inject/Config/apply`）；② **复用 ≥1 个真实 DSH 插件**（首选 `dsh-llm` + `dsh-llm-deepseek*`，或 `dsh-session-persistence-jsonl`）；③ **Python SDK 往返**（`deepseek-harness-sdk`，子进程 JSON-RPC）。
- **不做**：不做小镇世界、不做经济、不做像素前端。

### 5.2 步骤（半天，四步）

| 步 | 动作 | 目标产物 |
|---|---|---|
| **S1** | 按 tutorial 写一个最小 Cordis 函数插件，挂进 `cordis.yml`，用 `dsh --dump-config` 确认加载、日志确认 `apply` 执行 | 截图/日志：插件已挂载且可被卸载（dispose） |
| **S2** | **只改配置**替换/启用一个真实 DSH 插件（如把 LLM provider 换成另一个，或启用 `session-persistence-jsonl` 的 zstd），**零 fork** | 配置 diff + 生效证据 |
| **S3** | 用 **Python SDK** 起 `dsh --profile sdk`，从 Python 发起**一个 turn**，拿回结果，并读回 DSH 的 append-only 日志 | Python 脚本 + 单次往返**延迟测量** + 日志可读性 |
| **S4** | 尝试把我们「LLM 输出→落不可篡改日志+缓存→重放不重调」的语义**嫁接到 DSH 之上**，记录需要**多少胶水代码/补丁** | 胶水 LOC 估算 + 是否需要 fork |

### 5.3 成功 / 失败判据（必须能得出「值/不值」）

| 判据 | **通过（值）** | **不通过（不值）** |
|---|---|---|
| **S1 挂载** | 自定义插件被 loader 加载、卸载时副作用**自动撤销**（dispose 生效） | 无法挂载，或需改 Cordis 源码 |
| **S2 复用** | **仅靠 config/patch** 即可复用 ≥1 个真实 DSH 插件（零 fork、零改源码） | 复用需 fork DSH 或改其 vendored 代码 |
| **S3 边界** | Python→DSH 单 turn 往返成功；**IPC 延迟 ≤ 50 ms**（相对 LLM 秒级可忽略）；DSH 日志能被 Python 确定性读回 | 往返失败，或延迟 > 200 ms，或日志无法可靠读回 |
| **S4 冻结嫁接** | 用 **< 150 行胶水**即可在 Python 侧实现「输出冻结 + 重放不重调」；**无需改 DSH** | 需 > 300 行胶水，或必须在 DSH 内改判定路径 |

**决策规则（写死）**：
- **S1∧S2∧S3∧S4 全过** → **采纳路线 C（窄混合）**：Python 世界引擎 + Cordis/DSH 承接 agent 内容与日志/技能/压缩叶子能力。
- **S2 或 S4 不过**（需 fork / 胶水过多）→ **回到路线 B**（Python 自建插件化），仅**借鉴** Cordis 的可逆副作用/waterfall 设计，不引入 Node 栈。
- **S1 或 S3 不过** → 说明 Cordis/Python 边界不成立 → **直接 B**。
- **S3 延迟虽过但双日志一致性无法收敛** → **B**（因为确定性 replay 是硬铁律）。

### 5.4 spike 的「反模棱两可」设计要点

- **量化**：延迟用实测量（ms），胶水用 LOC，判据用**硬阈值**（上表），不允许“感觉还行”。
- **对照**：S4 同时给出「Python 自建等价实现」的 LOC，**对比跨语言胶水 vs 自建**，让「值/不值」有基线。
- **产出**：一页 `spike-report.md`（结果表 + 原始日志 + 结论二选一）。

*（§3–§5 完成）*

### 5.5 「50 agent loop 单进程」的验证方法（应 T200 要求；可在 spike 内加做）

> 背景：**「Cordis/TS 单进程能承载 50 个 agent loop」目前无任何实证**（SKYCity 实测 19）。以下方法**可在同一 spike 内附加**，用最小成本给出**实测**而非推断。

| 步 | 动作 | 测量量 | 判据（示例阈值，可调） |
|---|---|---|---|
| V1 | 单进程起 DSH，注册 **N 个空 Agent**（或 N 个 session），N = 10 → 19 → 30 → 50 递增 | 峰值 RSS、启动时间 | RSS 随 N **近似线性**、无 OOM |
| V2 | 对 N 个 Agent **并发触发一轮固定 prompt**（用 mock/本地小模型，避免 API 限流干扰测量） | 吞吐（完成 turns/s）、event-loop 延迟 p99 | 单 tick 阻塞 > 100 ms 记为**退化**；吞吐随 N 线性无退化 |
| V3 | 同构实现一份 **Python asyncio** 对照（同 N、同 mock） | 同上 | 与 TS 侧对比，得出「差异是否显著」 |
| V4 | 若上步退化 → 定位瓶颈（CPU? 内存? GC?） | CPU profile / heap | 给出「50 需要多进程/分片」或「50 单进程可行」的二选一结论 |

- **产出**：一张 `N vs {RSS, 吞吐, p99}` 曲线 + 二元结论。
- **注意**：这是**验证规模上限**，与 spike 主目标（验证**复用收益**）独立；若时间不够，可**单列为后续小实验**，但**不得**把「50 可行」写成已定事实。

---

## 6. 风险清单

| ID | 风险 | 级别 | 影响 | 缓解 |
|---|---|---|---|---|
| R-1 | **DSH 是 developer preview、breaking changes 频繁** | 高 | 采用后持续返工 | spike 后先窄接口、锁版本；`engine_version` 纳入 DSH/Cordis 版本 |
| R-2 | **vendored Cordis 已 18 项本地补丁**，upstream 更新需 re-apply | 中 | 维护成本 | 不 vendor 进我们仓；用 npm 发布版；跟踪 issue |
| R-3 | **双栈运维（Node + Python）** | 高 | 环境/CI/部署复杂度翻倍 | 仅当 spike 证明复用收益 > 双栈成本才引入 |
| R-4 | **双日志/双真值**（DSH session log vs 我们的哈希链） | 高 | 破坏「唯一真值 + 同日志逐位一致」 | 硬约束：**世界真值只在 Python**；DSH 日志仅作 agent 内容缓存，经冻结层回写 |
| R-5 | **跨语言延迟/序列化** | 中 | 性能 | 内核结算留 Python（粗粒度跨语言）；实测延迟纳入 spike 判据 |
| R-6 | **DSH 插件点是「编码 Agent」语义**，与城镇模拟错配 | 中 | 复用名不副实 | 只复用基础设施层（llm/session/query/skill/compaction），不套其 agent-loop |
| R-7 | **确定性在 TS 侧被破坏**（float64、异步调度） | 高 | 违反铁律 | 真值与 replay 留 Python；TS 侧不参与真值 |
| R-8 | **许可与合规**：DSH 为 **MIT**，Cordis 亦开源；但第三方插件许可需逐个核 | 中 | 合规 | 复用前核每个插件 license（我们已有 AI Town/GA 的核验习惯） |
| R-9 | **团队认知负担**（Cordis 概念 + Node 工具链） | 中 | 交付速度 | 用 spike 评估实际上手曲线；文档化 |

---

## 7. 来源与证据 / 未验证项

### 7.1 已核实（附链接/位置）

1. **DSH 仓库**：`deepseek-ai/deepseek-harness`，MIT，**247.5k stars**，“Everything is a Plugin”，**developer preview**。来源：<https://github.com/deepseek-ai/deepseek-harness>
2. **Cordis = DSH 底层插件框架，agent loop 本身是插件、可替换**。来源：`docs/architecture.zh.md`（<https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/docs/architecture.zh.md>）；`packages/core/README.zh.md`（`dsh-agent` vs `dsh-agent-loop`）
3. **DSH 包分组与具体包名**（llm/session/session-query/skill/compaction/subagent/extensions/test-support 等）。来源：`packages/README.zh.md`（<https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/packages/README.zh.md>）
4. **DSH 会话日志 = append-only + 不可变 generation + zstd；`session-projection` 增量折叠事件为当前值；`session-checkpoint-policy` 在下一步前持久化**。来源：`packages/session/README.zh.md`
5. **DSH 会话检索 = 统一查询 + 关系追踪 lineage + SQLite FTS5 全文 + /export ZIP**。来源：`packages/session-query/README.zh.md`
6. **LLM 能力系列 = provider 无关服务 + DeepSeek/pi-ai 适配器 + retry + token-meter**。来源：`packages/llm/README.zh.md`
7. **官方 Python SDK = 子进程 + 行分隔 JSON-RPC over stdio，驱动 `dsh --profile sdk`；另有 `sdk-runtime` 打包 CLI**。来源：`python/README.zh.md`（<https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/python/README.zh.md>）
8. **Cordis 本体 = ~2000 行 TS 元框架；五概念（Service/Fiber/Effect/inject/Events）；被 DSH vendor（4.0.0-rc.7）+18 项本地补丁；waterfall = 事件系统上的 around-middleware**。来源：<https://juejin.cn/post/7673436957741236239>（掘金，2026-08-13）
9. **可逆副作用的形式化（effect/restore、上下文即副作用插座）**。来源：<https://cordis.moe/zh-CN/guide/philosophy/disposable.html>
10. **Cordis 教程（插件=函数、生命周期与 effect、service、事件与 waterfall、配置校验、HMR）**。来源：<https://deepseek-harness.github.io/deepseek-harness/develop/cordis-tutorial/>
11. **GA 模块文件清单与硬编码 OpenAI**：见本仓 `v1.1/14-agent-impl-reuse-map.md` §F.1（`persona/cognitive_modules/*`、`memory_structures/*`、`prompt_template/gpt_structure.py`）。
12. **本项目实测基线**：N=20×84 = 3782 s / 4814 调用 / 660,501 tokens（来自本轮 T203 上游口径）。
13. **T200/SKYCity 实证输入**：SKYCity 以「异步并发 + DB 行锁」在 **19 Agent** 跑通（非 50；“可调 50”未实测）；「离散回合 + 单裁决器」可绕开行锁/竞态；SKYCity 观察/渲染层（PixiJS+Tiled+整数缩放+WS 缺口自愈）可借鉴，其记忆检索为「全量 select + Python 打分」，50+ 线性变慢、**不要照抄**。来源：本团队 **T200-skycity-teardown**（sim-system-architect）。

### 7.2 未验证（明确标注）

| # | 事项 | 说明 |
|---|---|---|
| U1 | **「≤50 ms IPC 延迟」** | 为量级推断，未在本机实测；须由 spike S3 实测 |
| U2 | **「胶水 < 150 行」** | 为立项阈值估计，未实测；须由 spike S4 实测 |
| U3 | **50 agent 单进程的实际内存/稳定性上限** | DSH 未给 50-agent 实测数据；须 spike 或后续验证 |
| U4 | **第三方 `dsh-plugin` topic 生态的实际可用插件** | 仅确认 topic 机制存在，未枚举真实第三方插件 |
| U5 | **「像素级迁移」的用户确切所指（认知保真 vs 像素地图）** | 见 §4.1，待用户澄清 |
| U6 | **GA Python→TS 逐模块重写系数 1.5–2.5×** | 经验估计，未实测 |
| U7 | **DSH 版本与内容生成行为的关系** | 未验证 DSH 升级是否会改变 LLM 输出（影响冻结/复现） |
| U8 | **`dsh-plan`/`dsh-goal`/`dsh-schedule` 直接复用于「小镇agent日程」的改造量** | 语义是编码任务，改造量未评估 |

---

## 8. 附：一页建议（正式版，供 Leader 汇报与用户裁决）

**建议：路线 D → C-narrow。即「先跑半天 spike；通过后采用『Python 世界引擎（唯一真值）+ Cordis/DSH agent 内容层』的窄混合」。不建议全 TS/Cordis 重写（A）。**

**理由**
1. **DSH 插件能点名，但复用面比预期窄**：真正可复用的是 **llm / session / session-query / skill / compaction / subagent / extensions / test-support** 这些**基础设施**插件；**没有**任何「社会模拟/经济/生命周期/观测」领域插件——我们最核心的资产**无现成可复用**。
2. **资产保值**：全量重写（A）会把 Python 世界/经济/观测资产打到 ~10–20%；窄混合（C）保留 ~90%，且内核算术（任意精度整数 + 哈希链）继续满足「同日志逐位一致」铁律；TS float64 反而是风险。
3. **性能不是理由**：50+ agent 是 **I/O-bound**，Node 与 Python(asyncio) **等价**；瓶颈是 LLM 吞吐/费用与内存治理，不是 Cordis/Node。**且**：我们既定的「**离散回合 + 单裁决器**」已用确定性换掉了并发复杂度（§2.3），**Python 单进程就够**；「50 单进程可行」本身**无实证**（SKYCity 实测 19，§3.1 / §5.5）。
4. **确定性铁律**：Cordis/DSH 的 `agent-loop` 是 LLM 驱动的工具循环，**语义与我们冲突**；只能把它当**内容生成器**用，真值结算必须留 Python。

> **「为 Cordis 跨语言」到底买到了什么（本文的正面回答）**：**买到的是一份可点名的插件清单**——`dsh-llm*`（provider 无关 LLM 接入/重试/token 计量）、`dsh-session*`（append-only JSONL + 投影折叠，≈我们的日志/replay）、`dsh-session-query*`（lineage + SQLite FTS5）、`dsh-skill`、`dsh-compaction`、`dsh-context`、`dsh-subagent`、`dsh-extensions`、`dsh-test-support`（§1.2）；**买不到的是任何领域能力**（经济/生命周期/社会观测/世界规则无一可复用）。**以及买到的是 Cordis 运行时本身**：可逆副作用 + 服务消失自愈 + 配置组合/HMR + waterfall（§1.1）。**是否值得，取决于 spike 的 S2/S4 判据**——若复用需 fork、或胶水 > 150 行，则这份清单**不足以**支撑双栈代价。

**风险（须向用户明示）**
- DSH 是 **developer preview、快变**；vendored Cordis 已有 18 项本地补丁 → 长期维护成本。
- **双栈运维 + 双日志一致性**是窄混合的最大代价；必须硬约束「世界真值只在 Python，DSH 输出只作待冻结载荷」。
- 若 spike 的 **S2（零 fork 复用）或 S4（胶水 < 150 行）不过**，则**回到路线 B**（Python 自建插件化），仅借鉴 Cordis 设计，不引入 Node。

**给用户的决策请求**
1. 是否批准 **半天 spike**（人力成本极低，能给出「值/不值」的硬结论）？
2. 若 spike 通过，是否接受 **窄混合（C）**（Python 保真值 + Node 复用 DSH 内容/日志能力）？
3. 澄清「**像素级迁移**」的确切所指（认知保真迁移 vs 像素地图，见 §4.1）——**这会影响是否需要跨语言**。

*（v2/refs/cordis-dsh-feasibility.md 完成 — solution-architect）*