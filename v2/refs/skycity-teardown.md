# SKYCity 拆解：可借鉴清单 + 差异矩阵

> 任务：T200-skycity-teardown（sim-system-architect）
> 对象：`/tmp/refs/SKYCity`（`github.com/TianyaSKY/SKYCity`，MIT，version 0.2.0 / docs 标 1.2.0）
> 方法：**只读静态拆解**（读源码 + 读 `docs/`）。**未运行代码**，故所有"运行期行为"结论标【静态推断】，需实测复核的标【未验证】。
> 证据约定：每条给 `文件:行` 或 `doc §`，可被独立复算。
> 许可：代码 MIT（`LICENSE`）；地图素材 Kenney Tiny Farm **CC0**（`README.md:309`）；LLM 框架 OpenAI Agents SDK MIT（`README.md:310`）。本文件不评价许可风险，仅登记出处。
>
> ⚠️ **最重要的一条诚实交代**：SKYCity 是 **19 个 Agent**（`README.md:5`）的项目，**不是 50+**。它的"效率机制"是**为规模准备的控制旋钮**（并发上限、日 token 预算、观察缓存、退避），**没有在 50 规模上的实测证据**。任务书的"50+ 规模效率机制"在本仓库应读作"**它的可扩展性设计**"，而非"已验证的 50 规模方案"。

---

## 0. 一句话结论

SKYCity 是一个**质量很高、工程收尾完整**的 19-Agent 像素小镇：**三条边界（LLM 只出意图/引擎唯一真值/前端只观察）与我们的架构同源**，事件信封（sequence/trace_id）与我们的 ADR-08 高度可比，前端 PixiJS 与看板可**直接借鉴为资产**。

**但它与我们的根本分歧在时间与并发模型**：SKYCity 是**连续游戏分钟 + 异步并发 LLM 调用 + DB 行锁**；我们是**离散回合 + 单一裁决器串行 + 回合缓冲提交**。因此它**几乎不能"照搬代码"**，能照搬的是**机制与工程范式**。

---

## 1. 50+ 规模效率机制（最高优先）——机制 / 代码位置 / 可否照搬

> SKYCity 的调度哲学：**Agent 默认休眠，事件驱动唤醒**；**每 0.1s 一个 tick 只做"到期回调"派发**，不逐帧轮询所有居民。这是它控制成本的第一性手段。

### 1.1 并发/调度模型

| # | 机制 | 代码位置 | 细节 | 我们可否照搬 |
|---|---|---|---|---|
| E1 | **Tick 循环只推进时钟 + 派发到期回调** | `backend/app/world_engine/engine.py:992-1000`（`_tick_loop`）、`engine.py:1002-1028`（`_tick_runtime`：`clock.tick` → `scheduler.load_due` → `dispatch`） | `TICK_INTERVAL=0.1` 真实秒（`config/gameplay.py:208`）；每个 tick 对每个 world：推进时钟、跑小时结算、派发 `due_at <= world_time` 的动作 | **机制可借鉴，实现不照搬**：我们是离散回合，无真实秒 tick；但"到期回调队列"思想与我们的 scheduler/事件驱动一致 |
| E2 | **Agent 决策是"被调度"而非"每帧跑"** | `world_engine/scheduler.py:46-64`（`schedule`）、`engine.py:434-453`（注册 `agent_decide` 等 handler） | 决策落在持久表 `scheduled_actions`，`due_at` 到点才派发 | ✅ **可借鉴**（我们已有等价物，可在 §3 对齐命名） |
| E3 | **单 Agent 不并发决策**：原子认领 | `services/agent_decision_service.py:202-237` | 用 `UPDATE ... WHERE is_deciding=False` 条件更新认领，`rowcount!=1` 即返回；避免两个 pending 决策同 tick 触发两次 LLM（注释明说旧 ORM read-then-write 会 race） | ✅ **强烈可借鉴**：任何"事件驱动 + 可重入"实现都需要这个防重入认领 |
| E4 | **全局 LLM 并发上限**：loop-keyed 信号量 | `services/agent_decision_service.py:63-78`（`_llm_semaphore`）、`:110-111`、`:563-567`；`config/settings.py:63` | `asyncio.Semaphore(llm_max_concurrent=2)`，**所有决策 + 反思共用同一 cap**；因 `asyncio.run` 每次新建 loop，信号量按 loop 键控 | ✅ **可借鉴**（对我们尤其重要：我们若引入并发 LLM，必须有全局 cap；见 §7 差异） |
| E5 | **失败退避（指数）** | `services/agent_decision_service.py:1027-1046`；`config/gameplay.py:111,113` | `consecutive_failures` 累加（上限 5），下次决策延迟 `min(backoff_max_delay=120, DEGRADE_DELAY=20 × 2^(n-1))` | ✅ **可借鉴** |
| E6 | **超时 + 一次性重试** | `services/agent_decision_service.py:504-560` | `asyncio.wait_for(..., llm_timeout_seconds=60)`；仅"瞬态错误"重试 1 次，**重试复用同一 observation**（省钱） | ✅ **可借鉴** |
| E7 | **两档降级节奏** | `config/gameplay.py:114-115`；`agent_decision_service.py:64-94` | 观察缓存命中 → 15 游戏分钟后复评（`SKIP_DECIDE_DELAY`）；世界预算耗尽 → 30 分钟后休眠复评（`BUDGET_SKIP_DELAY`） | ✅ **可借鉴** |

### 1.2 观察构建与缓存策略

| # | 机制 | 代码位置 | 细节 | 可否照搬 |
|---|---|---|---|---|
| E8 | **观察文本限长 + 分级裁剪** | `agents/observation_service.py:166`（`build_observation`）、`:1025`（截断）；`config/gameplay.py:215-217` | `OBSERVATION_MAX_CHARS=50000`；未读消息 ≤3、商店商品 ≤6、背包 ≤8、岗位 ≤6、求职/请假各 ≤3…（多处 `[:N]`） | ✅ **可借鉴**（我们已有 `perceive`，限长策略可直接抄） |
| E9 | **观察缓存：同观察跳过 LLM** | `services/agent_decision_service.py:108-109`（per-agent cache）、`:412-439`（命中判定） | 对 observation 做 `md5`，**先 `re.sub(r"\d{2}:\d{2}", "")` 去掉时钟**（否则每分钟 tick 都变，缓存永不命中）；`agent.action_type is None` 且 10 游戏分钟内相同 → 跳过并排 15 分钟后复评 | ✅ **强烈可借鉴**；**注意"去时钟再哈希"这个坑**，否则缓存无效 |
| E10 | **静态 prompt 缓存（身份卡）** | `agents/instructions.py:1-6`；`providers/openai_provider.py:10` | 身份卡按 agent 静态，`_system_prompt(agent_id)` 缓存；世界状态走每次的 observation | ✅ **可借鉴**；我们 life 层 persona 可同法缓存 |

### 1.3 token 预算与降级

| # | 机制 | 代码位置 | 细节 | 可否照搬 |
|---|---|---|---|---|
| E11 | **世界级每日 token 预算闸** | `services/agent_decision_service.py:441-494`；`config/settings.py:64` | `world_daily_token_budget`（0=不限）；从 `llm_runs` 按"当日世界时间窗"求和已用 token，超限 → 跳过调用 + 进入休眠节奏 + 每天只公告一次（去重） | ✅ **可借鉴**；我们的 freeze 层预算闸可对照 |
| E12 | **单 Agent 日用量计数** | `services/agent_decision_service.py:138-146,321` | `daily_call_count` / `daily_token_usage` 累加；成功则 `consecutive_failures=0` | ✅ **可借鉴** |
| E13 | **单工具强制 + 单轮终止** | `providers/openai_provider.py:100-127`；`config/gameplay.py:227` | `tool_choice=required` + `parallel_tool_calls=False` + `tool_use_behavior="stop_on_first_tool"`；`max_turns=4` 仅作畸形调用兜底 | ✅ **可借鉴**；是"一次决策=一个世界动作"的硬保证（对应我们的 intent 单动作） |

### 1.4 失败退避与事务/行锁范围

| # | 机制 | 代码位置 | 细节 | 可否照搬 |
|---|---|---|---|---|
| E14 | **SQLite `BEGIN IMMEDIATE` + 条件 UPDATE + 有限重试** | `world_engine/locks.py:22-23,32-49,52-86` | `LOCK_RETRIES=3`、`LOCK_BACKOFF_SECONDS=0.02`；`BEGIN IMMEDIATE` 抢预留写锁，条件 UPDATE 的 WHERE 携带不变量（如 `stock >= qty`），零行即"竞态失败"，**整笔事务体重跑**保证不跨尝试泄漏旧读 | ⚠️ **机制可借鉴，但不能照搬**：我们是"单裁决器串行"，**根本不存在并发写竞态**；只有引入并发写时才需要它 |
| E15 | **事务范围 = 单动作单事务** | `services/action_execution_service.py:159-282`（`execute_action` 分发）、`:307-419`（`execute_move`）等 | 每个动作在自己的事务里校验→改库→发事件→提交（event_bus 在调用者事务内 `session.add`，`engine.py:841-860`） | ❌ **不照搬**：与我们 ADR-08「整回合缓冲、P6 唯一 append」冲突（见 §3、§7） |

### 1.5 更高层的"省 token"设计（值得注意）

- **`tool_choice=required` 强制一次工具调用**：模型不能"光说不做"，也避免长文本；`auto/none` 时文本回复**降级为 wait 15 分钟**，不burn退避（`openai_provider.py:38-67`）。
- **`work(job_id)` 统一抽象**：**不为每个工种造工具**，控制工具面膨胀（`docs/agent-prompt.md:80-83`）。
- **失败不重试同一调用**：把失败结果写进 observation，下次让 LLM 自己改策略（`docs/agent-prompt.md:31`）。
- **不在 `talk` 工具内运行对方 LLM**：A 说话只投递消息，B 自行决定是否回应（`docs/agent-prompt.md:87-89`）；避免对话触发链式 LLM 爆炸。

---

## 2. 记忆系统

**三层记忆**：`working / episodic / semantic`（`services/memory_service.py:1`；`docs/agent-prompt.md:80`）。

| 维度 | SKYCity 做法 | 位置 | 借鉴点 |
|---|---|---|---|
| 工作记忆 | 只保留最新 `WORKING_MEMORY_CAP=20` 条，超出即删 | `memory_service.py:146-147,162-174`；`gameplay.py:153` | ✅ 有"上限 + 剪枝" |
| 情节记忆 | 事件钩子写入；**只记"当事方"**（对话双向、工作完成、物品、大额金钱、上帝行为、工具失败、雇佣生命周期），**绝不记他人的秘密** | `memory_service.py:2-8,488-720` | ✅ **可借鉴**：以"事件当事方"为记忆写入边界，天然满足"未观察信息不进 prompt" |
| 语义记忆 | 每日 23:30 反思产物（importance 0.8，keyword「今日总结」） | `memory_service.py:14-18,330-395`；`gameplay.py:154` | ✅ |
| 检索 | **加权打分**：`0.35×entity_hit + 0.25×keyword_hit + 0.20×importance + 0.15×recency + 0.05×unresolved`；`recency = created_at/world_time` | `memory_service.py:10-12,242-268`；`gameplay.py:156-160` | ✅ 权重可借鉴；**注意它没有 embedding** |
| 每日反思 | 每 world 一个递归调度动作（23:30），逐 Agent 生成 digest→反思→写 semantic；可换更强模型（`LLM_REFLECT_MODEL`） | `memory_service.py:302-395`；`docs/agent-prompt.md:107-109` | ✅ 独立限频、独立模型 |
| **睡眠/遗忘** | **只有工作记忆剪枝**；**episodic/semantic 永不删除、无衰减** | `memory_service.py:162-174`（唯一 prune） | ⚠️ **它没有真正的"睡眠/遗忘"**；数据库只增不减 |

**关键工程警示（【静态推断】）**：检索是**先 `select` 出该 Agent 全部记忆、再在 Python 里逐条打分排序**（`memory_service.py:190-235`）。**没有向量索引/倒排**。19 Agent 下无碍，**50+ 长时程下会随记忆行数线性变慢**——这是我们若借用其记忆模型**必须改掉**的一点（我们有 embedding/冻结层可解决）。测试佐证：`backend/tests/test_memory_relationships.py`。

---

## 3. 事件协议（与我们的 ADR-08 对比）

### 3.1 SKYCity 信封（`docs/event-protocol.md:5-32`；`domain/event.py`）

```
{ event_id, sequence, world_id, world_time, type, payload, trace_id }
```
- `event_id = evt_{seq:06d}`，`trace_id = trc_{seq:06d}`（`event_bus.py:19-24`）。
- `sequence`：**世界内单调、永不复用**（`event-protocol.md:26`）。
- `trace_id`：**贯穿整条决策链同值**——调度→观察→LLM→工具→Service→事务→事件→WS（`event-protocol.md:31`；`architecture.md:69`）。

### 3.2 排序 / 去重 / 持久化 / 重连

| 点 | SKYCity | 位置 |
|---|---|---|
| 排序 | 消费端按 `sequence` 升序；同 `world_time` 也用 sequence 定序 | `event-protocol.md:33-35` |
| 去重 | 前端记 `lastSequence`，收到 `≤` 的丢弃 | `frontend/src/websocket/client.ts:120` |
| 缺口恢复 | 收到 `> lastSeq+1` → 触发**全量快照重拉** | `client.ts:121-126,131-140` |
| 首包 | WS 建立后**先发 `world_snapshot`**，再推增量 | `event-protocol.md:37`；`client.ts:114-118` |
| 持久化 | 全部事件写 `world_events` 表 | `event-protocol.md:178-182` |
| 补齐 | `GET /api/worlds/{id}/events?after_sequence=N` | `event-protocol.md:182` |
| 重放 | **快照 + 按 sequence 的事件序列，重放不依赖 LLM** | `event-protocol.md:181` |

### 3.3 与我们的 ADR-08 对比

| 维度 | SKYCity | 我们（ADR-08，`v2/04-exchange-and-contracts.md:61-67,337,365`） | 判断 |
|---|---|---|---|
| 事件提交粒度 | **单动作即提交**（`event_bus.publish` 在调用者事务内 `session.add`，`engine.py:841-860`） | **整回合缓冲**：所有 emit 入本回合待提交缓冲，**P6 COMMIT 为唯一 append 点** | ❌ **冲突**：我们更严（整回合原子 + 回滚） |
| 原子性 | 单笔事务内原子；无跨动作回滚 | 整回合守恒不成立则**丢弃整缓冲区** | 我们更强 |
| 顺序号 | 世界内单调 `sequence` | 我们同样有 sequence + `turn_seal` | ✅ 同源 |
| 溯源 | `trace_id` 贯穿链 | 我们事件带 trace/round/phase | ✅ 同源 |
| 哈希链 | **无**（无 append-only 哈希链；靠 DB 行 + sequence） | **有**（`engine/ledger.py`：append-only + SHA-256 链 + `turn_seal`） | 我们更强（防篡改） |
| 快照对齐 | 连接就发快照 + 缺口重拉 | 我们有 snapshot/replay | ✅ 同源 |

> **可借鉴**：SKYCity 的 `trace_id` 全链同值 + 前端"缺口即快照重拉"是**廉价且好用的自愈**，值得我们在观测台/前端沿用。
> **不能借**：它的"逐动作提交、无哈希链"比我们弱，**不要回退**。

---

## 4. 世界规则 R1–R12 逐条对照（冲突项已标注）

> SKYCity 规则是**实现契约**（`docs/world-rules.md:3-5`：不允许交给 LLM 临场发挥）。下表的"我们"指本项目 v1.1/v2 设计（离散回合 + 单一裁决器 + 事件契约）。

| 规则 | SKYCity 内容 | 位置 | 与我们对照 / 冲突 |
|---|---|---|---|
| R1 并发行动 | 一个 Agent **同时最多一个进行中行动**；move/work 独占 | `world-rules.md:15-21` | ✅ 同构（我们有行动/意图预算）。**无冲突** |
| R2 移动中不能对话 | 双方都空闲且距离 ≤3 才能 talk | `world-rules.md:23-26` | 同构（我们 life 层社交） |
| R3 工作不可打断 | 普通行动不能打断 work；上帝可打断并按比例结算 | `world-rules.md:28-31` | 参考 |
| **R4 抢最后一件商品** | **DB 事务内对库存行加锁**（`BEGIN IMMEDIATE` + 条件 UPDATE），先到先得，后者"库存不足" | `world-rules.md:33-38`；`locks.py` | ⚠️ **并发模型冲突**：我们**单裁决器串行**，无竞态、无需行锁；若我们引入并发，需重述此规则 |
| **R5 暂停语义** | 暂停**只阻止新决策**；**已发出的 LLM 请求允许完成**，但其工具调用被拒（`世界已暂停`），拒绝**幂等不产生状态变更** | `world-rules.md:40-44` | ⚠️ **需与我们对照**：这是"异步在途请求"特有的语义；我们离散回合下暂停边界更简单。**待与 solution-architect / 内核对齐** |
| R6 天气影响移动 | 晴/阴 ×1.0，雨 ×1.5，雪 ×2.0；耗时写进记忆 | `world-rules.md:46-52`；`gameplay.py:76` | 可借鉴（我们可加天气维度，但非必须） |
| **R7 没钱能否欠款** | **主动交易不赊账**；**唯一负债来源是每日生活开销**超支，余额变负 | `world-rules.md:54-59`；`gameplay.py:81` | ⚠️ **与"可续命"冲突**：用户已拍板我们走"借贷 + 负资产"；SKYCity **无借贷工具、无银行**。**不可照搬** |
| R8 商店关门 | 营业区间 `[open,close)`，关闭时进入被拒 | `world-rules.md:61-65` | ✅ 同构（我们 §2 场所营业时段） |
| R9 对话距离 | 曼哈顿 ≤3；超距自动中断 | `world-rules.md:67-70` | ✅ 同构 |
| R10 劳动结算 | 自雇只给产物（须卖店变现）；公共工作预留预算；合作社班次走 formal_work | `world-rules.md:72-76` | 参考 |
| **R11 饱食度=0** | 禁 work、移速×2、每小时额外掉精力；触发找食物；**第一版无死亡机制** | `world-rules.md:78-82` | ❌ **根本冲突**：我们**有死亡/生命周期**（Sugarscape 式代谢归零即死）；SKYCity **刻意无死亡**（R21 亦重申） |
| R12 低精力强制休息 | 精力 ≤20 禁 move/开始工作；wait/sleep 恢复 | `world-rules.md:84-87`；`gameplay.py:47` | ✅ 同构（我们有需求/精力） |
| R13 上帝命令 | **可违反普通规则**（瞬移/改库存/发钱/改天气），但必须审计 + 发事件 | `world-rules.md:89-93` | ⚠️ **与观察者定位冲突**：我们观察者是**只读 + 种子事件注入**；SKYCity 上帝**可改钱**。**需 Leader 定夺权限边界** |
| R14 需求节奏 | 每小时结算：饱食−1/精力−1/心情−1/孤单+1…；每日 00:00 扣 `UPKEEP_PER_DAY=100` | `world-rules.md:95-118`；`gameplay.py:14-24,81` | 可借鉴数值锚点 |
| R16 事件顺序 | 同 `world_time` 按 `sequence` 升序；一切状态变更必发事件 | `world-rules.md:128-131` | ✅ 同源 |
| R17 存档 | 快照含时间/天气/状态/背包/库存/关系/记忆/在途动作/待执行事件/随机种子/配置版本 | `world-rules.md:133-136` | ✅ 同构（我们 replay + config 指纹） |

**其它值得注意的机制级规则**：R20.4a 财政分配（维护费 50% UBI / 20% 公共工程 / 30% 工资补贴）、R20.4b 负责人值守津贴 10%、R20.4c **饥饿强制进食（引擎直接调度，不依赖 LLM）**（`world-rules.md:162-167`）、R32 **僵尸企业清算 + 缺勤解约**（`world-rules.md:301-306`）、R36a **采购订单缺货转订单自动履约**（`world-rules.md:336-339`）。这些"**用确定性规则补 LLM 的不可靠**"的手法与我们理念一致，值得借鉴。

---

## 5. 智能体提示词与工具约定（"token 极致利用"视角）

| 手法 | 位置 | 价值 |
|---|---|---|
| 7 段式观察组装（身份卡/世界现状/自身/可见/记忆/来信/行动接口） | `docs/agent-prompt.md:5-17` | 结构化、可控 |
| **观察限长**（默认 ≤50,000 字符，超长截断；不重复发静态说明） | `agent-prompt.md:19-21`；`gameplay.py:215` | ✅ 省 token |
| **相同观察短时缓存**，命中不重复调 LLM | `agent-prompt.md:22`；`agent_decision_service.py:412-439` | ✅ 省 token（大项） |
| `tool_choice=required` + `parallel_tool_calls=False` + `stop_on_first_tool`，max_turns=4 兜底 | `agent-prompt.md:24-31`；`openai_provider.py:100-127` | ✅ 强制单动作、防连环 |
| 工具失败不重试同一调用，结果入观察由 LLM 自纠 | `agent-prompt.md:31` | ✅ 防死循环 |
| LLM 故障降级为 `wait` 15 分钟，世界不崩 | `agent-prompt.md:32`；`gameplay.py:112` | ✅ 韧性 |
| **`agent_id` 由服务端注入，不作为工具参数**（防冒充） | `agent-prompt.md:73`；`instructions.py`；`management` 工具 `agent-prompt.md:141` | ✅ **安全**：值得直接抄 |
| 工具只收**意图参数**；**禁止 LLM 传**金额/余额/库存上限/合同状态 | `agent-prompt.md:137-140` | ✅ **与我们的 intent/arbiter 分离同源** |
| 工具返回结构化 JSON `{success, reason}`，禁止吞异常 | `agent-prompt.md:74-77` | ✅ |
| **`work(job_id)` 统一抽象，不按工种造工具** | `agent-prompt.md:80-83` | ✅ 控制工具面 |
| `LLMRun` 记录 model/tokens/latency/tool/args/result/success/error/trace_id，**不存隐藏推理** | `agent-prompt.md:98-104` | ✅ 可审计、省存储 |
| 帮手固定短语 + 身份卡静态缓存 | `instructions.py:125-144` | ✅ 省 token |

> **工具清单**（`agent-prompt.md:37-53, 115-133`）：move/wait/sleep/talk/buy_item/sell_item/use_item/buy_stock/sell_stock/open_shop/stock_shop/adjust_price/set_buy_price/close_shop + apply_job/withdraw_job_application/start_shift/request_leave/resign_job + 负责人工具（review_job_application / review_leave_request / terminate_employment / pause_recruitment / resume_recruitment / purchase_company_goods / stock_store）。

---

## 6. 前端与游戏质感

| 点 | 实现 | 位置 | 借鉴 |
|---|---|---|---|
| 渲染栈 | **Vue 3 + Pinia + PixiJS 8**；整数倍缩放 1/2/3/4/8×；Tiled JSON 地图 | `README.md:73-74`；`frontend/src/pixi/`（`WorldRenderer/TiledMapLoader/AgentSprite/MovementAnimator/CameraController/AssetLoader` + `layers/TileLayerRenderer`、`StructureLayer/CropLayer/AgentLayer`） | ✅ **可直接借鉴为工程样板** |
| 状态同步 | Pinia `worldStore`：严格升序应用事件、去重、`applySnapshot` 全量覆盖 | `frontend/src/stores/worldStore.ts:1298-1323,1112-1145` | ✅ |
| WS 自愈 | 指数退避重连 1s→10s；缺口即 REST 快照重拉；首包快照 | `frontend/src/websocket/client.ts:22-23,120-150` | ✅ |
| 观感组件 | 对话气泡 `SpeechBubble`、名字牌 `AgentNameplates`、事件流 `EventStream`、状态面板 `AgentPanel`/`AgentCareerCard`、合作社面板 `CompanyPanel`、地点面板 `LocationPanel`、时钟条 `WorldClockBar`（暂停/1×/2×/5×/10×） | `frontend/src/components/` | ✅ |
| 时间控制 | pause/resume/speed 经 REST（`POST .../pause|resume|speed`） | `backend/app/api/worlds.py:122-157` | ✅ |
| **看板** | `GET /api/worlds/{id}/dashboard`；前端 `DashboardView` 组合**LLM 调度统计** + **事件类型统计**；含民生/就业/商业/财政/调度质量 | `api/worlds.py:409`；`frontend/src/views/DashboardView.vue:57-66,306-312` | ✅ **可借鉴为观测台雏形** |
| 截图取证 | `docs/images/*.png`（world-overview / dialogue / agent / god-panel / dashboard 等） | `docs/images/` | 视觉参考 |

> **与我们的差距**：我们已有 `code/frontend` + `obs/report.py` 指标 + 事件卡资产；SKYCity 的**PixiJS 图层拆法与 WS 缺口自愈**是可对齐点；它的看板是"REST 聚合 + 前端画图"，与我们"只读日志确定性重算"口径不同——**看板呈现可借鉴，判定口径不可借鉴**。

---

## 7. 差异矩阵

> 建议列：**照搬 / 改造 / 自建**。判断依据是"是否与我们离散回合 + 单裁决器 + 回合缓冲不变量冲突"。

| 能力 | SKYCity 做法 | 我们现状 | 建议 |
|---|---|---|---|
| **时间模型** | **连续游戏分钟**（0.1s tick × speed 1/2/5/10），非离散回合 | **离散回合**（1 周 = 84 回合，`v1.1/00-architecture.md §3`） | **自建**（不照搬；这是最根本分歧，决定其余一切） |
| **并发模型** | LLM **异步并发**（信号量 cap=2）+ DB 行锁防竞态 | **单一裁决器串行**，无并发写竞态 | **自建**（保留我们的确定性；并发只允许出现在 LLM 调用侧，参照 E4 加 cap） |
| **事件提交** | 单动作即提交；无哈希链 | **ADR-08 整回合缓冲，P6 唯一 append + 守恒回滚 + 哈希链** | **保留自建**（更强；**不要回退**） |
| **溯源** | `trace_id` 全链同值 + `sequence` | 我们事件带 round/phase/trace + `turn_seal` | **改造**：补"全链同 trace"的便利性 |
| **前端缺口自愈** | 缺口 → 快照重拉；首包快照 | 我们有 replay/快照；前端自愈机制**待补齐** | **照搬机制**（便宜、好用） |
| **观察缓存** | 去时钟后 hash，10 分钟内相同跳过 | `perceive` 无此缓存（待确认） | **照搬机制**（含"去时钟再哈希"坑） |
| **全局 LLM 并发 cap** | `llm_max_concurrent` 信号量 | freeze 层**未见全局 cap**（待核） | **照搬机制**（若引入并发） |
| **世界日 token 预算 + 休眠** | 预算耗尽进休眠节奏 | 我们 freeze 有预算/降级设计 | **改造对齐** |
| **失败指数退避** | `20 × 2^(n-1)`，上限 120 | 我们退避策略**待核** | **照搬机制** |
| **记忆检索** | **无 embedding**，全量扫 + 关键词/实体加权 | 我们要 **embedding + 冻结**（`code/freeze/embedding.py`、`obs`） | **自建**（他们在 50+ 会线性变慢） |
| **记忆遗忘** | 只有 working 剪枝；episodic/semantic 永久 | 我们可做衰减/归档 | **自建**（补真遗忘） |
| **死亡/生命周期** | **无死亡**（第一版明确） | 我们**有**（代谢归零/借贷/复活/安全阀） | **自建**（用户已拍板的差异） |
| **经济/借贷** | 无银行、无借贷、不赊账（唯一负债=日开销） | 我们有世界银行 + 负资产 + 惩罚 P1–P8 | **自建** |
| **上帝/观察者权限** | 上帝**可改钱/传送/改天气**（审计） | 观察者**只读 + 种子事件注入** | **待定**（需 Leader 定权限边界，见 §4 冲突） |
| **工具层安全** | `agent_id` 服务端注入；禁 LLM 传金额/余额 | 我们 intent/arbiter 分离（同源） | **照搬机制**（确认我们已等价） |
| **单决策单动作** | `tool_choice=required` + `stop_on_first_tool` | 我们 intent 单动作 | **照搬机制** |
| **提示词结构** | 7 段 + 静态身份卡缓存 + 观察限长 | 我们 life 层 persona/observe | **改造对齐** |
| **文书化规则** | `world-rules.md` 作为**实现契约**（改规则同步改文档+测试） | 我们分册 + 事件契约 | **照搬机制**（我们已有同类，强化） |
| **前端可视化** | PixiJS 图层 + Tiled + 整数缩放 + 元素组件 | 我们 `code/frontend` 已有像素渲染 + 事件卡 | **改造/对齐**（借图层拆法与组件清单） |
| **看板** | REST 聚合 + 前端画图 | 我们 `obs/*` 只读日志确定性重算 | **看板呈现照搬，判定口径自建** |

---

## 8. 我们能直接复用为"资产"的东西

1. **工程范式资产（机制，可直接落地）**
   - 观察缓存（**含"先去除 `HH:MM` 再哈希"**）：`agent_decision_service.py:412-439`。
   - 全局 LLM 信号量 + 指数退避 + 超时重试一次性：`agent_decision_service.py:63-78,504-560,1027-1046`。
   - 世界日 token 预算闸 + 休眠节奏：`:441-494`。
   - `agent_id` 服务端注入、工具只收意图参数：`agent-prompt.md:73,137-140`。
   - 工具返回结构化 JSON、统一 `work(job_id)`：`agent-prompt.md:74-83`。
   - WS 缺口→快照重拉 + 首包快照：`websocket/client.ts:114-140`。
   - 文书化"规则即实现契约"：`world-rules.md:3-5`。
2. **视觉/素材资产**
   - **Kenney Tiny Farm（CC0）**：`/tmp/refs/SKYCity/kenney_tiny-farm/`（tilesheet + 单 tile PNG + `Tilesheet.txt`）。**CC0 可直接用**。
   - Tiled 地图与 tileset：`world_data/maps/tiny_world.tmj`、`tiny_farm.tsj`、`markers.tsj`；地图生成脚本 `tools/build_map.py`。
   - PixiJS 渲染代码可作为**参考实现**（Vue/PixiJS 技术栈）：`frontend/src/pixi/`。
3. **数据/配置资产（可参考，需换皮）**
   - 物品/职业/商店/作物/股价/蓝图/合作社种子：`world_data/{items,jobs,stores,crops,stocks,blueprints,companies}/*.json`。
   - NPC 身份卡模板（含性格五因素、初始金钱、spawn）：`world_data/identities/agent_*.json`；扩展说明见 `README.md:237-261`。
4. **文档资产**：`docs/architecture.md`、`world-rules.md`、`event-protocol.md`、`agent-prompt.md`、`map-specification.md`、`company-employment.md`（合作社/雇佣，22KB）、`deployment.md`/`upgrading.md`（交付/升级/备份）。

---

## 9. 它有而我们没有的

| # | 缺口 | SKYCity 位置 | 对我们的价值 |
|---|---|---|---|
| G1 | **像素前端完整实现**（PixiJS 图层 + 相机 + 移动动画 + 气泡 + 名字牌 + 时钟条 + 看板） | `frontend/src/` | 我们前端的直接对标/速度来源 |
| G2 | **合作社/正式雇佣系统**（岗位/招聘/考勤/工资/欠薪/僵尸清算） | `docs/company-employment.md`；`services/company_employment_service.py`(2349 行) | 我们 v2 若有"组织/雇佣"需求可直接借鉴 |
| G3 | **建造 + 种植系统**（材料预扣、连通性不变式 BFS、作物分阶段生长） | `world-rules.md:180-210`（R22/R23） | 生活世界"环境改造"机制 |
| G4 | **天气系统**（影响移速，写进记忆） | `world-rules.md:46-52` | 我们暂缺的维度 |
| G5 | **上帝干预面板**（发钱/赐物/传送/公共事件/改价）全审计 | `services/god_action_service.py`(994 行)；`god_actions` 模型 | 观察者/演示工具 |
| G6 | **交付/部署工程收尾**（Docker 一体镜像、Alembic 迁移、CI 交付校验、Playwright E2E、隔离验收脚本） | `Dockerfile`、`docker-compose.yml`、`tools/verify_delivery.py`、`docs/deployment.md`、`.github/workflows/` | 我们落地工程化的模板 |
| G7 | **三通道对话 + 对话锁 + 冷却 + 防对聊**（`talk` 不触发对方 LLM） | `services/conversation_service.py`(719 行)；`gameplay.py:120-133` | 对话工程细节 |
| G8 | **Tiled 地图生成管线** | `tools/build_map.py` | 我们小镇地图生产 |

---

## 10. 未验证 / 待实测（诚实清单）

- 【未验证】**50+ 规模的实际表现**：仓库是 19 Agent；`llm_max_concurrent=2`、日 token 预算等**未在 50 规模实测**（README 无 50 数据）。任务书说"50+ 规模效率机制"，**此处应降级为"可扩展性旋钮"**。
- 【未验证】**记忆检索的 O(n) 扫描在长时程的真实开销**（静态读出的结论；未见压测）。
- 【未验证】**`tool_choice=required` 对各样模型的实际成功率**（代码对 `auto/none` 有降级路径，说明强制可能失败）。
- 【未验证】**`world_daily_token_budget` 默认 0（不限）**，即开箱**不设预算**；预算闸是"可选能力"而非默认防护。
- 【静态推断，未运行】§1 各"机制"仅从代码结构推断；语义细节（如并发下的公平性、退避是否真降本）需实测。
- 【未验证】**暂停语义 R5**（在途请求完成但工具被拒）在我们离散回合下的对应实现方式。
- 【需 Leader 裁决】**观察者权限边界**（我们只读 vs SKYCity 上帝可改钱，见 §4 R13）。
- 【未核对】我们 `code/freeze` 是否已有"全局 LLM 并发 cap"与"指数退避"（§7 标"待核"）；本次任务是 SKYCity 拆解，未展开审我们的实现。

---

## 11. 给下游/技术选型的三条行动建议

1. **优先照搬"机制"而非"代码"**：观察缓存（去时钟哈希）、全局 LLM 信号量、指数退避、日 token 预算、`agent_id` 服务端注入、WS 缺口自愈——这 6 项与我们架构**不冲突**、收益明确。
2. **坚决自建、不照搬**：并发模型（保持单裁决器）、事件提交（保持 ADR-08 回合缓冲 + 哈希链）、记忆检索（上 embedding）、死亡/借贷（用户已拍板）。
3. **需要一次跨语言/架构合议**：`solution-architect`（T201）在裁决 TS↔Python 边界时，可参考本文件 §1（并发/调度）与 §3（事件提交）——**SKYCity 证明"异步并发 + DB 行锁"能跑通 19 Agent，但我们若选离散回合 + 单裁决器，可完全绕开它的行锁/竞态复杂度**；这是"用确定性换并发复杂度"的一次实证。

---

## 12. 出处与许可登记

| 资产 | 出处 | 许可 |
|---|---|---|
| SKYCity 代码 | `github.com/TianyaSKY/SKYCity` | **MIT**（`LICENSE`） |
| Kenney Tiny Farm 像素素材 | `kenney.nl/assets/tiny-farm`；本地 `/tmp/refs/SKYCity/kenney_tiny-farm/` | **CC0**（`README.md:309`，`Tilesheet.txt`） |
| OpenAI Agents SDK | `github.com/openai/openai-agents-python` | MIT（`README.md:310`） |
| 参考文档 | `/tmp/refs/SKYCity/docs/{architecture,world-rules,event-protocol,agent-prompt,map-specification,company-employment,deployment,upgrading}.md` | 随仓库 MIT |

*（拆解结束 — sim-system-architect；只读拆解，未修改本项目任何代码）*
