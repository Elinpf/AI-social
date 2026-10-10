# 03 · 确定性仿真引擎 + 确定性统计程序 v1

> 作者：仿真引擎与统计架构师（sim-engine-stats-architect）
> 状态：v1 设计草案（供 Leader 汇总；标注「已定 / 待讨论」）
> 适用实验：50 个 LLM Agent 社会实验（先 10-Agent 沙盒验证，再放量）

本文件设计实验的**世界引擎架构**与**确定性统计程序**，硬约束如下（贯穿全文）：

- **硬约束 C1**：世界引擎 / 规则裁决器必须是**确定性代码**，绝不能是 LLM。LLM 只负责个体决策。
- **硬约束 C2**：**事件驱动 + 分层决策**。常规行为走廉价规则 / 小模型；昂贵 LLM 只在重大决策（投资、结盟、濒死求生）时调用，以控制成本。
- **硬约束 C3**：统计程序必须**确定性、可复现、可审计**，不依赖任何 LLM 判断；输入相同则输出**逐位一致**。

术语沿用团队既定口径：世界引擎 / 裁决器（Game Master 式中央裁决）、代谢消耗（metabolism）、归零（account depletion）、可续命借贷（revival loan）、负资产（negative net worth）。

---

## 0. 全局设计原则（已定）

| 编号 | 原则 | 说明 |
|---|---|---|
| P1 | **整数货币** | 所有金额以**整数最小单位**（下文称 `mu`，money unit，例如 1 元 = 100 mu）存储与运算，**禁止浮点**参与任何账务或指标结算。数值边界：`int64`，单笔上限 `2^53-1` 以防 JSON 精度问题。 |
| P2 | **状态 = 事件日志的函数** | 权威状态永远是 `State = reduce(apply, EventLog, InitialState(seed))`。快照只是加速缓存，可随时从日志重建。 |
| P3 | **纯函数裁决** | 所有规则 hook 是**纯函数**：`(state, round, rng_stream) -> (state', events)`，无 I/O、无墙钟、无全局可变状态。 |
| P4 | **显式随机源** | 世界内**不存在隐式随机**。任何随机抽样必须从受控 RNG 流取数（见 §1.4），抽样序列由 `(seed, stream_id, round, seq)` 唯一确定。 |
| P5 | **确定性顺序** | 一切遍历、排序、集合迭代必须有**全序 tie-break**（一般以 `agent_id` 升序、再以 `event_id` 升序）。禁止依赖哈希表迭代顺序。 |
| P6 | **只追加日志** | 交易 / 生命周期 / 通信日志只追加、不修改、不删除；每条记录带链式哈希（见 §6.1）。 |
| P7 | **裁决器先行、LLM 后置** | LLM 只能产生**意图（intent）**，意图交由裁决器校验后才成为**事实（event）**。LLM 输出永不直接改账。 |

> **已定 D0-1（2026-10-09 与 lifecycle 确认）**：`mu` 进制 = **1 CR = 100 mu**。比例量（税率/利率等）用**万分比整数**（bp），不使用浮点。
> **待讨论 D0-2**：是否为世界引入「回合内子 tick」（连续时间近似）。v1 建议**纯离散回合**，降低复杂度与复现难度。

---

## 1. 引擎架构

### 1.1 模块划分（已定）

```
+--------------------------------------------------------------------------+
|                            Simulation Kernel                              |
|                                                                          |
|  +----------------+   +-------------------+   +----------------------+   |
|  | Clock/Round    |   | Event Queue       |   | World State Store    |   |
|  | Scheduler      |-->| (deterministic    |-->| (authoritative state |   |
|  | (phase order)  |   |  priority queue)  |   |  + snapshot cache)   |   |
|  +----------------+   +-------------------+   +----------------------+   |
|          |                     |                        ^                |
|          v                     v                        |                |
|  +--------------------------------------------------+   |                |
|  |      Central Rule Arbiter  (NON-LLM, pure)        |---+                |
|  |  settle_market | apply_tax | check_death | ...    |                    |
|  +--------------------------------------------------+                    |
|          ^                     |                                         |
|          | intents             | events                                  |
|  +----------------+   +------------------+   +----------------------+    |
|  | Decision Layer |   | Communication    |   | Ledger / Audit Log   |    |
|  | T0 rules / T1  |   | Channels         |   | (append-only + hash) |    |
|  | small / T2 LLM |   | (3 channels)     |   |                      |    |
|  +----------------+   +------------------+   +----------------------+    |
|          ^                                                              |
|  +----------------+   +----------------------+                          |
|  | RNG Streams    |   | Stats / Metrics      |                          |
|  | (seeded, hier.)|   | (deterministic)      |                          |
|  +----------------+   +----------------------+                          |
+--------------------------------------------------------------------------+
        ^                                   |
        | rule hooks (econ / lifecycle)     v
   +---------+                        +-----------+
   | Economy |  mount hooks           | Lifecycle |  mount hooks
   | Layer   |<---------------------->| Layer     |
   +---------+                        +-----------+
```

模块职责：

1. **Clock / Round Scheduler**：驱动回合，规定**固定的阶段顺序**（§1.2），保证跨运行一致。
2. **Event Queue**：存放待处理事件（消息到达、定时唤醒、悬挂的市场委托、到期债务）。全序优先级。
3. **World State Store**：权威状态 + 定期快照。快照仅作性能缓存（P2）。
4. **Central Rule Arbiter**：非 LLM 纯函数集合，是**唯一**允许修改账务与生命周期的组件。
5. **Decision Layer**：分层决策（T0/T1/T2，§3），产出 intent。
6. **Communication Channels**：三通道（§4），产出 message 事件。
7. **Ledger / Audit Log**：只追加 + 哈希链（§6.1）。
8. **RNG Streams**：层级化确定性随机源（§1.4）。
9. **Stats / Metrics**：确定性统计（§5），只读日志。

### 1.2 回合阶段与数据流（已定）

每个回合 `Round t` 严格按以下**六阶段**执行，顺序不可变：

```
Phase 0  ROUTE       : 事件队列出队到点事件 -> 分发为 intent/trigger
Phase 1  PERCEIVE     : 为被唤醒 Agent 构造观测 (world_view)，不含未来信息
Phase 2  DECIDE       : 分层决策 (T0 rules -> 可选 T1 -> 可选 T2 LLM) -> intents
Phase 3  COMMUNICATE  : 处理三通道消息 (受每回合配额与惩罚约束) -> message events
Phase 4  ARBITRATE    : 裁决器依次执行 hook 链 (确定性顺序) -> state deltas
Phase 5  LIFECYCLE    : check_death / bankruptcy / revival / penalty
Phase 6  COMMIT       : 追加日志 + 守恒校验 + 快照 + 指标计算 (可选)
```

数据流（单向）：

```
EventQueue --(到点)--> PERCEIVE --(world_view)--> DECIDE --(intents)-->
   ARBITRATE --(validated events)--> COMMIT --(append log, snapshot)-->
   Stats 只读 log -> metrics
```

关键规则：
- **Phase 4 前不产生任何状态突变**。所有 intent 在 Phase 4 由裁决器一次性、按全序处理。
- Phase 4 内 hook 链顺序固定（§2.2），跨运行一致。
- Phase 6 的守恒校验失败 → **整回合中止并落审计告警**（不是静默修正）。

### 1.3 Hook 链与调用顺序（已定，供 econ / lifecycle 挂载）

Phase 4 `ARBITRATE` 内部固定顺序（每条 hook 输入同一 `state`，串行折叠 `state := hook(state).state`）：

```
4.1  settle_market(state)        # 经济层：撮合、清算、原子转账
4.2  settle_obligations(state)   # 经济层：到期债务、利息、扣款（含续命贷）
4.3  apply_tax(state)            # 经济层：征税与再分配 / UBI
4.4  apply_metabolism(state)     # 生命周期层：每回合代谢消耗
4.5  apply_penalty(state)        # 生命周期层：负资产 / 策略性作弊惩罚
4.6  check_lifecycle(state)      # 生命周期层：破产/濒死/归零标记
4.7  resolve_revival(state)      # 生命周期层：复活 / 续命贷发放
4.8  check_death(state)          # 生命周期层：最终死亡判定（本回合终局）
```

> **已定（与 econ/lifecycle 对齐）**：`apply_tax(4.3)` 内部子顺序 = **铸币判定 → 收入税 → 财富税 → UBI**。
> **反作弊打标（已定，与 lifecycle 对齐）**：引擎在 Phase 4.1 对 `TRANSFER`/`MARKET_TRADE` 确定性打标 `flags{wash,cycle,self,mule}`，判定窗口 `W_wash = 4` 回合（同 `from`/`to` 在窗口内反向或环路回流 → `cycle/wash`；`from==to` → `self`；同源多账户 → `mule`）。打标为纯函数，仅依赖日志与 `(round, tx_seq)`，可重放。
> 顺序理由：先经济结算 → 再征费 → 再代谢/惩罚（扣钱）→ 再判生命（用扣费后的余额）→ 死亡判定放最后，保证「本回合扣完才算死」。
> **已定 D1-1（与 lifecycle 确认）**：`apply_tax`(4.3) 在 `apply_metabolism`(4.4) **之前**（先税后代谢）。濒死判定统一在「同回合扣完税与代谢后的 E_eff」上做，口径全引擎一致。

### 1.4 确定性随机源（已定）

层级化 RNG：为每个逻辑子系统分配独立 `stream_id`，避免一处抽样改变另一处序列。

```
stream_id 示例:
  "init"        # 初始禀赋 / 出生采样
  "market"      # 撮合随机化（如需）
  "metabolism"  # 代谢扰动（如需）
  "decision.t1" # 小模型决策随机
  "decision.t2" # LLM 调用点随机（如 temperature 重试计数）
  "comms"       # 消息投递随机（如需）
  "lifecycle"   # 死亡/复活相关随机
```

抽样接口（伪代码）：

```python
def draw(stream_id: str, round: int, seq: int, n: int) -> list[int]:
    """确定性抽 n 个整数。序列由 (global_seed, stream_id, round, seq) 唯一确定。"""
    sub_seed = H(global_seed, stream_id, round, seq)   # H = SHA-256, 取前 8 字节 -> uint64
    rng = SplitMix64(sub_seed)                         # 纯整数 PRNG，跨语言可复现
    return [rng.next_u64() for _ in range(n)]
```

要求：
- `H` 使用固定哈希（SHA-256）截断，跨语言/跨进程一致。
- PRNG 使用**整数运算**（SplitMix64 / xoshiro），禁止依赖语言内置 `random` 的浮点实现。
- 浮点若必须（仅统计展示层，不参与账务），用固定精度整数重算或定点算术。

---

## 2. 对外接口约定（Hook 契约）

### 2.1 数据类型（已定）

```python
# ---- 标识与基础 ----
AgentId   = str          # 稳定 id，如 "A007"；排序按字符串升序
Round     = int          # 回合号，从 0 开始
Mu        = int          # 金额，整数最小单位，可为负（负资产）

# ---- 世界状态（权威，不可变风格：hook 返回新 state）----
class WorldState:
    round: Round
    seed: int
    agents: dict[AgentId, AgentState]      # 有序：对外遍历按 key 升序
    cash: dict[AgentId, Mu]                # 现金余额
    deposits: dict[AgentId, Mu]            # 平台内存款/托管（如需要）
    loans: dict[LoanId, Loan]
    market: MarketBook                     # 委托簿 / 价格状态
    money_minted_total: Mu                 # 累计发行
    money_burned_total: Mu                 # 累计销毁
    # ... 其他经济/生命周期字段由对应层扩展

class AgentState:
    agent_id: AgentId
    status: str            # 见 §5.9 白名单（6 值）: alive|warning|near_death|dead|revived|terminated
    # 语义（与 lifecycle 层对齐）：
    #   alive      正常存活
    #   warning    预警：可主动转出，尚未禁转
    #   near_death 濒死：**禁止主动转出**（= lifecycle 的 DISTRESSED），可发 1 条私聊求助
    #   dead       死亡冻结中：0 条主动消息，可接收外部救助
    #   revived    复活缓冲期（= lifecycle 的 REVIVING）
    #   terminated 永久退出（不再参与存活率统计的分子/分母口径见 §5.3）
    birth_round: Round
    death_round: Round | None
    net_worth: Mu          # = cash + deposits + assets - liabilities
    health/metabolism 等字段由生命周期层扩展

class Loan:
    loan_id: str
    lender: AgentId | None    # None => 系统（续命贷）
    borrower: AgentId
    principal: Mu
    outstanding: Mu
    rate_bp: int              # 基点
    due_round: Round
    status: str               # "active"|"overdue"|"repaid"|"written_off"
    repaid_total: Mu

# ---- 事件（日志记录，见 §6）----
class Event:
    seq: int                 # 全局单调递增
    round: Round
    phase: int               # 阶段号 0..6
    actor: AgentId | "SYSTEM"
    type: str                # 见 §2.3 事件类型表
    payload: dict            # 结构化，字段见 §2.3
    prev_hash: str
    hash: str                # H(seq,round,phase,actor,type,payload,prev_hash)

class Delta:                 # hook 返回
    state: WorldState
    events: list[Event]
```

### 2.2 Hook 接口签名（伪代码，可直接实现）

```python
# 所有 hook 必须满足：
#  (1) 纯函数：相同 (state, round, ctx) 恒返回相同 (state', events)
#  (2) 幂等性由引擎保证：引擎以 (round, phase, hook_name) 为键，
#      对同一回合同一 hook 只调用一次；重放时按日志回放其结果，不重算。
#  (3) 不得读取墙钟、环境变量、外部网络；随机只能经 ctx.rng(stream_id, seq) 获取。

def settle_market(state: WorldState, round: Round, ctx: Ctx) -> Delta: ...
def settle_obligations(state: WorldState, round: Round, ctx: Ctx) -> Delta: ...
def apply_tax(state: WorldState, round: Round, ctx: Ctx) -> Delta: ...
def apply_metabolism(state: WorldState, round: Round, ctx: Ctx) -> Delta: ...
def apply_penalty(state: WorldState, round: Round, ctx: Ctx) -> Delta: ...
def check_lifecycle(state: WorldState, round: Round, ctx: Ctx) -> Delta: ...
def resolve_revival(state: WorldState, round: Round, ctx: Ctx) -> Delta: ...
def check_death(state: WorldState, round: Round, ctx: Ctx) -> Delta: ...

class Ctx:
    def rng(self, stream_id: str, seq: int, n: int) -> list[int]: ...
```

**幂等与调用契约（已定）**：

| 契约 | 内容 |
|---|---|
| I1 | 引擎以 `(round, phase, hook_name)` 为幂等键，同回合同 hook 恰好调用一次。 |
| I2 | 重放（replay）模式**不重新执行 hook**，而是按日志中已记录的事件折叠状态（见 §6.2）。这保证重放与首跑逐位一致，且 hook 演进的版本通过 `engine_version` 标注隔离。 |
| I3 | hook 之间的数据交换只经 `state`，不共享隐式全局。 |
| I4 | 任一 hook 抛异常 → 引擎回滚该回合（丢弃本回合所有 delta）并写入 `SYSTEM_ERROR` 审计事件，**不得**产生部分结算。 |
| I5 | 所有 hook 输出的事件必须携带完整 `payload`（§2.3），使重放无需重算。 |

### 2.3 事件类型表（已定，供日志/统计对齐）

| type | 触发阶段 | 关键 payload 字段 | 说明 |
|---|---|---|---|
| `AGENT_BORN` | 0 | `agent_id, birth_round` | 出生 |
| `INIT_ENDOW` | 0 | `agent_id, amount` | 初始禀赋 |
| `TRANSFER` | 4.1 | `tx_id, from, to, amount, fee, reason, counterparty_id, flags{wash,cycle,self,mule}` | 原子转账；**必须**带反作弊打标字段 |
| `MARKET_TRADE` | 4.1 | `tx_id, buyer, seller, qty, unit_price, amount, counterparty_id, flags{wash,cycle,self,mule}` | 成交；**必须**带反作弊打标字段 |
| `LOAN_ISSUED` | 4.2 | `loan_id, lender, borrower, principal, rate_bp, due_round` | 放贷 |
| `LOAN_REPAY` | 4.2 | `loan_id, payer, amount, outstanding_after` | 还款 |
| `INTEREST_CHARGED` | 4.2 | `loan_id, borrower, amount, pool` | 计息（borrower→税池），供利率/税基复算锚点 |
| `LOAN_DEFAULT` | 4.2/5 | `loan_id, outstanding, written_off` | 违约/坏账 |
| `TAX_LEVIED` | 4.3 | `agent_id, base, amount` | 征税 |
| `UBI_PAID` | 4.3 | `agent_id, amount` | 再分配 |
| `METABOLISM` | 4.4 | `agent_id, amount` | 代谢消耗（销毁） |
| `PENALTY_APPLIED` | 4.5 | `agent_id, kind, amount` | 惩罚（非复活费；kind 例：作弊罚没） |
| `REVIVE_FEE_PAID` | 4.7 | `agent_id, amount, pool` | 复活/续命费（独立事件，便于审计与成本统计） |
| `MONEY_MINTED` | 任意 | `amount, reason` | 发行 |
| `MONEY_BURNED` | 任意 | `amount, reason` | 销毁 |
| `STATE_CHANGE` | 5 | `agent_id, from, to` | 状态流转（alive/near_death/dead） |
| `AGENT_DIED` | 5 | `agent_id, death_round, cause` | 死亡 |
| `AGENT_REVIVED` | 5 | `agent_id, cost` | 复活/续命 |
| `MSG_PUBLIC` | 3 | `msg_id, author, topic, body, refs` | 公告板 |
| `MSG_DM` | 3 | `msg_id, from, to, body` | 私聊 |
| `MSG_GROUP` | 3 | `msg_id, group_id, from, body` | 群组 |
| `LLM_CALL` | 2 | `agent_id, tier, model, tokens_in, tokens_out, trigger` | 成本记录（不在裁决器内改账） |
| `SYSTEM_ERROR` | 任意 | `where, detail` | 审计 |

> **对齐要求**：统计程序（§5）只读上表字段。lifecycle 层的「破产 / 死亡 / 存活时长」判定必须落到 `STATE_CHANGE` / `AGENT_DIED` 事件；经济层的「借贷坏账」必须落到 `LOAN_*`；现金变动必须落到 `TRANSFER` / `MARKET_TRADE` / `METABOLISM` / `TAX_LEVIED` / `UBI_PAID` / `MONEY_*`。**任何账务变化若无对应事件，视为 bug（守恒校验会暴露）。**

---

## 3. 分层决策与成本控制

### 3.1 决策分层（已定）

| 层 | 执行者 | 适用行为 | 每次成本 | 默认是否调用 |
|---|---|---|---|---|
| **T0** | 纯规则代码（无模型） | 代谢扣除、被动收入、按价格信号下的**规则化限价单**、自动接受/拒绝标准报价、余额阈值告警、消息自动分类 | 0 | 每回合对「被唤醒」Agent 执行 |
| **T1** | 廉价小模型（短 prompt，≤N tokens） | 常规协商、简短回信、标准报价生成、简单声誉判断 | 低 | 仅当 T0 无法判定且**非**重大决策 |
| **T2** | 昂贵 LLM（长上下文、带工具） | **投资**、**结盟/长期契约**、**濒死求生**（借贷/抛售/求助）、重大战略转向 | 高 | 仅当触发条件命中 |

**触发条件（已定，可配置阈值）**：

```
T2 触发（任一）:
  a) 投资机会：可用资金 >= INVEST_THRESHOLD 且愿投目标净现值 > 0
  b) 结盟：有主动结盟/长期契约意图且对象数 >= ALLIANCE_MIN
  c) 濒死求生：net_worth < SURVIVAL_THRESHOLD 或 cash < METABOLISM*k_rounds
  d) 重大外部冲击：收到影响自身 > X% 净资产的 public 事件
  e) 显式请求：Agent 自评「重大决策」并给出理由（有配额与审计）

T1 触发（任一，且未命中 T2）:
  a) 收到需要自然语言回复的 DM/群组消息
  b) 报价空间离散、T0 规则无法覆盖
  c) 需要跨方协调的普通事务
```

> **待讨论 D3-1**：具体阈值取值（`INVEST_THRESHOLD`、`SURVIVAL_THRESHOLD`、`k_rounds`）需与 sandbox-test 联调后定，v1 先给符号参数。

### 3.2 事件驱动唤醒（已定）

Agent 默认**休眠**，仅在下列事件到达时被唤醒（进入 PERCEIVE→DECIDE）：

```
wake(agent, round) = true  iff  任一:
  W1 定时：round % cadence == 0              (常规巡检，如每 5 回合)
  W2 消息：本回合收到发给自己或所在群组的消息
  W3 状态触发：net_worth < threshold 或 cash 低于代谢若干回合量
  W4 市场相关：自己的挂单被成交/被撮合
  W5 债务：自己有到期债务或将逾期
  W6 邻居行动：强关系（Top-K 权重）邻居发生重大事件
```

唤醒集合在 Phase 0 由 `ROUTE` 统一计算，**按 agent_id 升序**处理 → 保证确定性。

### 3.3 每回合 LLM 调用量估算（已定方法，初值与 lifecycle 对齐）

**符号（无歧义定义，避免与通信配额混淆）**：

| 符号 | 含义 | 默认初值 | 来源 |
|---|---|---|---|
| `N` | 存活 Agent 数 | 10(沙盒)/50(全量) | 状态 |
| `N_near` | 濒死(`near_death`) Agent 数 | 由仿真得 | 状态 |
| `a` | 单回合**主动决策率**（非 idle 的比例）= lifecycle 的 `p1` | **0.6**（0.4–0.8） | lifecycle 初值 |
| `p2` | 濒死 Agent **触发求助(T2)** 的比例 | **0.70**（0.5–0.9） | lifecycle 初值 |
| `p_t1` | 主动决策中走 T1（非直接 T2）的比例 | 0.9（待标定） | 估计 |
| `q_near` | near_death 通信配额上限 | **1** | §4.3 |
| `q_alive` | alive 通信配额上限 | 3 | §4.3 |

> **口径提示**：lifecycle 早期用的 `w=3` 实为**通信配额上限 `q_alive`**，不是唤醒率；本文的「唤醒率」= 主动决策率 `a`。两者不可混用，故此处显式拆分。

**估算公式（已定）**：

```
E[Calls_T2] ≈ N_near · min(q_near, 1) · p2            # near_death 配额硬钳制
E[Calls_T1] ≈ (N − N_near) · a · p_t1
E[Tokens]   ≈ E[Calls_T1]·tok1 + E[Calls_T2]·tok2
E[Cost]     ≈ Σ_tier (tokens_in·price_in + tokens_out·price_out)
```

**成本上界的硬性质**：因 `near_death` 通信配额 = 1，`E[Calls_T2] ≤ N_near / 回合`；即使濒死率飙到 40%，`E[Calls_T2] ≤ 0.4N`。T2 调用**天然有界**，near_death 白名单不会炸成本。

**定标参考（`D3-2`，最终以沙盒日志回放标定 `a/p2` 为准；lifecycle 配合复核）**：

- 10-Agent 沙盒、濒死占比 ~10%（`N_near≈1`）：`E[Calls_T2] ≈ 1×0.7 ≈ 0.7 次/回合`；`E[Calls_T1] ≈ 9×0.6×0.9 ≈ 4.9 次/回合`。
- 50-Agent、濒死占比 15%（`N_near≈7.5`）：`E[Calls_T2] ≈ 7.5×0.7 ≈ 5.3 次/回合`；`E[Calls_T1] ≈ 42.5×0.6×0.9 ≈ 23 次/回合`。
- 单日 100 回合（全量）：T2 ≈ 530、T1 ≈ 2300 次。据此设 token 预算硬上限。

**成本闸门（已定）**：引擎维护每回合 `LLM_BUDGET`；超出时**降级**：T2→T1→T0（按优先级，濒死求生 > 投资 > 结盟 > 常规），并把降级写入 `LLM_CALL` 事件（带 `degraded=true`），保证可审计、可复现。

---

## 4. 沟通通道

### 4.1 三通道数据结构（已定）

```python
# 公开公告板：全体可见，永久留存（只追加）
class PublicPost:
    msg_id: str          # "P-{round}-{seq}"
    round: Round
    author: AgentId
    topic: str           # 话题标签
    body: str
    refs: list[str]      # 引用 msg_id
    ts: int              # 逻辑时间 = round*1000 + phase_seq

# 私聊：仅 from/to 可见
class DirectMessage:
    msg_id: str          # "D-{round}-{seq}"
    round: Round
    from_: AgentId
    to: AgentId
    body: str
    ts: int

# 群组：group.members 可见
class GroupMessage:
    msg_id: str          # "G-{group_id}-{round}-{seq}"
    round: Round
    group_id: str
    from_: AgentId
    body: str
    ts: int

class Group:
    group_id: str
    members: list[AgentId]   # 升序
    created_round: Round
```

### 4.2 每回合消息条数上限（已定，防消息爆炸）

| 通道 | 单发送者上限 | 全局上限 | 溢出策略 |
|---|---|---|---|
| 公开公告板 | 1 条/回合/Agent | `CAP_PUBLIC = 20` 条/回合 | 超出按 `(round, author_id)` 升序截断，被截断的消息记 `DROPPED` 审计事件（不静默丢） |
| 私聊 | `CAP_DM = 3` 条/回合/Agent | 不设全局（受发送者上限约束） | 超出发送者上限的意图被拒，回执给发送者 |
| 群组 | 1 条/回合/Agent/群 | 单群 `CAP_GROUP = 10` 条/回合 | 超出按 `(round, from)` 升序截断 |

> **待讨论 D4-1**：上限具体数值需 sandbox 校准（过紧会抑制涌现，过松会 token 爆炸）。v1 用符号常量。

### 4.3 通道如何受负资产惩罚限制（已定）

负资产 / 濒死 Agent 的可通信能力**分级收紧**（惩罚与生命周期层协同，落在 `PENALTY_APPLIED` 事件）：

```
定义 voice_quota(agent) 基于 net_worth 与 status：

  status == "alive"       -> 公开板 1、私聊 3、群组 1/群/回合   （§4.2 正常上限）
  status == "warning"     -> 公开板 1、私聊 3、群组 1/群/回合   （预警可主动转出）
  status == "near_death"  -> 公开板 0、私聊 1（**仅 distress 求助**）、群组 0
  status == "dead"        -> 主动发信 0 条；**仍可接收**外部救助消息
  status == "revived"     -> 公开板 0、私聊 1、群组 0（复活缓冲期）
  status == "terminated"  -> 全部通道 0 条
```
（分档与 lifecycle §负资产通信惩罚一致：`alive:3 / warning:3 / near_death:1 / dead:0主动 / revived:1 / terminated:0`。）

设计意图（**已定 D4-2，与 lifecycle 确认**）：
- 负资产者「被剥夺发声权」既是惩罚，也抑制刷屏续命与串通。
- 但需保证**濒死 Agent 仍能发 1 条私聊求助**，否则无法触发 T2「濒死求生」LLM 调用，机制闭环断裂。→ v1 保留「濒死 1 条私聊救助」白名单。
- 建议为「求救类消息」设**免配额**特殊通道（内容分类由 T0 规则判定，仅允许 `distress` 标签），**待讨论**是否采纳。

---

## 5. 确定性统计程序

> 总原则：**只读事件日志（§6.1），不读 LLM 输出，不做主观判断**。所有指标 = `f(EventLog, snapshot_round)`，纯函数、确定性、可重放。金额一律用整数 `mu`；涉及除法时**先通分再整除**，浮点仅在最终格式化输出时使用，且固化为 `round(x, 6)` 或定点字符串。

### 5.0 指标快照结构（已定）

```json
{
  "schema_version": "1.0",
  "engine_version": "v1",
  "seed": 12345,
  "round": 100,
  "metrics": { "<metric_name>": { "value": ..., "unit": "...", "def_ref": "§5.1" }, ... },
  "log_hash": "sha256:...",
  "log_last_seq": 98765
}
```
- `metrics` 键**按字典序**排列；序列化用规范 JSON（键排序、无多余空格、浮点固定 6 位）。
- 相同 `(seed, engine_version, log)` → 快照**逐字节一致**。

### 5.1 财富分布不平等的 Gini 系数

- **口径（已定）**：财富 `w_i = net_worth_i`（净财富 = 现金 + 存款 + 资产 − 负债），单位 `mu`。
- **离散 Gini 公式（升序 `w_(1) ≤ … ≤ w_(n)`）**：

```
G = ( 2 · Σ_{i=1..n} i · w_(i) ) / ( n · Σ_{i=1..n} w_(i) )  −  (n+1)/n
```

- **负值处理（待讨论 D5-1）**：净财富可为负（P1 允许负资产）。经典 Gini 要求非负。v1 采用**平移法**：`w'_i = w_i − min_j(w_j)`（平移后全部 ≥ 0），在 `w'` 上计算 G，并在快照中同时输出 `gini_shifted` 与 `min_net_worth` 供解释。备选：仅对非负子集算 G（`gini_nonneg`）。两者都输出，主指标标注。
- 边界：`n < 2` 或 `Σ w' = 0` → `G := 0`（明确定义，不用 NaN）。

### 5.2 破产率

- **定义（已定）**：回合 `t` 的瞬时破产率

```
bankrupt(t) = |{ i : net_worth_i(t) < 0 ∧ status_i ∈ {alive, near_death} }| / alive_count(t)
```

- **流量破产率（周期）**：`flow_bankrupt(t) = |{ i : 本回合首次从 ≥0 跌破 <0 }| / alive_count(t-1)`。
- 快照同时输出 `bankruptcy_rate_stock` 与 `bankruptcy_rate_flow`。
- 数据来源：`TRANSFER/MARKET_TRADE/METABOLISM/TAX_LEVIED/PENALTY_APPLIED` 折叠出的每回合 `net_worth`；`STATE_CHANGE` 提供 status。

### 5.3 死亡率

```
alive_count(t)       = |{ i : birth_round_i <= t ∧ (death_round_i is None ∨ death_round_i > t) }|
deaths(t)            = |{ i : death_round_i == t }|
mortality_rate(t)    = deaths(t) / alive_count(t-1)          # 瞬时死亡率
cum_mortality(T)     = |{ i : death_round_i <= T }| / N_initial # 累计死亡率
```
- 来源：`AGENT_DIED` / `STATE_CHANGE`。
- **口径（与 lifecycle 对齐）**：`AGENT_DIED` 的判定必须基于 `E_eff = E − 已标记作弊流入（flags ∈ {wash,cycle,self,mule}）`，即统计中的「死亡」不承认对倒/环路刷出的续命余额；系统项（UBI/铸币/税/费/息/罚/复活费）不计入 `I_eff`。统计只读该事件，不自行判断。
- 边界：`alive_count(t-1) == 0 → rate := 0`。

### 5.4 存活时长分布

```
lifetime_i = death_round_i − birth_round_i      (仅对已死者)
```
输出（确定性）：
- `n_dead`、`mean`、`median`（最近秩法）、`p25/p75/p90`（最近秩法）、`min`、`max`。
- **直方图**：固定分箱边界 `bins = [0,10,20,...,100, +inf)`（v1 固定），每箱计数。
- **生存函数 S(k)**：`S(k) = |{ i : lifetime_i ≥ k }| / N_initial`，`k=0..K_max`。
- 仍需区分「已死者」与「删失存活者（右删失）」：另输出 `n_alive_at_T`，分布只基于已死者，并标注删失。

### 5.5 借贷坏账率

```
outstanding_total(t) = Σ_{loans: status ∈ {active, overdue}} ( principal − repaid_total )
overdue_total(t)     = Σ_{loans: status == overdue ∨ written_off} ( principal − repaid_total )
principal_issued(t)  = Σ_{loans: issued_round ≤ t} principal

default_rate_outstanding(t) = overdue_total(t) / outstanding_total(t)   # 主指标
default_rate_issued(t)      = Σ_{written_off} outstanding / principal_issued(t)  # 备选
npl_ratio(t)                = (逾期贷款余额) / (贷款总余额)              # 同 default_rate_outstanding
```
- 来源：`LOAN_ISSUED / LOAN_REPAY / LOAN_DEFAULT`。
- 边界：分母为 0 → 指标 := 0（明确定义）。

### 5.6 货币总量与流速

```
# 货币总量（存量，回合末）
M(t) = Σ_i cash_i(t) + Σ_i deposits_i(t)          # 在流通货币
# 累计净发行（对账用）
M_intended(t) = money_minted_total(t) − money_burned_total(t)

# 流速（Fisher 式，单回合 + 窗口两种）
V_round(t)  = ( Σ tx_amount in round t ) / M(t)
V_window(t) = ( Σ_{τ∈[t−L+1, t]} tx_volume_τ ) / mean_{τ∈[t−L+1,t]} M(τ)
```
- **换手口径（已定，与 econ 确认）**：基础流速仅计 `TRANSFER` + `MARKET_TRADE`；`MARKET_TRADE.amount` = 成交额（**不含手续费**），手续费单列为 `MONEY_BURNED`(50%) 与 `TRANSFER`→税池(50%)。`LOAN_ISSUED/LOAN_REPAY` 单列「信贷换手」；`INTEREST_CHARGED / TAX_LEVIED / UBI_PAID / METABOLISM / PENALTY_APPLIED / REVIVE_FEE_PAID` 单列，**均不入基础流速**（避免转移/内部结算虚增流速）。
- 边界：`M(t) == 0 → V := 0`。

### 5.7 交易额分布

```
对 round/window 内每笔交易金额 a_j（整数 mu）:
  n, sum, mean, median(最近秩), p90/p99(最近秩), min, max, stdev(整数→定点)
  直方图: 对数分箱, 边界 = 10^0,10^1,...  固定
  幂律指数 α: Hill 估计 (确定性)
       α = 1 + n · ( Σ_{j=1..k} ln(a_(j) / a_(k+1)) )^{-1}
       其中 a_(1)≥...≥a_(n) 降序, k = floor(0.1·n)  (top 10%)
```
- 为保证可复现：`ln` 用**定点/高精度**实现或统一对该指标以「浮点 + 固定 6 位 rounded」输出并在快照标注 `alpha_method="hill_k10"`。
- 来源：`TRANSFER`（按 `tx_type` 过滤）+ `MARKET_TRADE`。

### 5.8 Agent 间关系网络指标

```
构建有向加权图 G=(V,E):
  V = 参与过交互的 Agent
  E(a→b): weight_transfer(a→b) = Σ 净转出金额 (a 给 b 的 tx 额, mu)
          weight_msg(a→b)      = Σ 消息条数 (DM + 群组内 @, 可选)
  两个权重可分别构建两张图：金钱图 G_money、沟通图 G_comm

指标（均在确定性子图上算）:
  - 度中心性: degree(a), weighted_degree(a)
  - 网络密度: dens = |E| / (|V|·(|V|−1))
  - 聚类系数: 局部/全局（无权重或按权重，口径固定）
  - 介数中心性: Brandes 算法, 节点并列时按 agent_id 升序打破平局
  - 模块度: Louvain 固定随机种子与固定遍历顺序；n 小(≤50)时用确定性贪心
  - 强/弱连通分量: Tarjan, 确定性
  - 关系强度 Top-K 邻居列表（每 Agent 输出 K=5, 按 (weight desc, id asc)）
```
- 来源：`TRANSFER/MARKET_TRADE`（金钱图）、`MSG_*`（沟通图）。**待讨论 D5-5**：是否剔除 `flags ∈ {wash,cycle,self,mule}` 的作弊边（建议同时输出「含作弊边」与「剔作弊边」两版）。
- **待讨论 D5-4**：图指标是否需要「时间窗」版本（滚动窗口）与「累计」版本，v1 先都给累计，窗口版待定。

### 5.9 守恒律与不变量（作为指标兼校验）

```
(1) 货币守恒: M(t) == M_intended(t)  （当无外部净注入时）
    对账式: money_minted_total − money_burned_total − M(t) == 0
(2) 交易原子性: 每笔 TRANSFER/MARKET_TRADE 满足 Σ senders = Σ receivers + fee_burned
(3) 现金不变量（**已定，与 econ 对齐**）: `cash_i ≥ 0` 为默认；允许负现金 `B_i < 0`，但**必须由借贷背书**（|B| ≤ D_max=100CR，新增借贷需抵押 LTV 0.6），**不存在无偿透支**；濒死/冻结期禁主动转出、允转入。
(4) 借贷台账: Σ loans.outstanding == outstanding_total(t)
(5) 生命周期单调（**已定，与 lifecycle 对齐**）: status 白名单 = `alive / warning / near_death / dead / revived / terminated`（6 值），转换只允许白名单内的合法边（如 alive→warning→near_death→dead→revived→alive，及任意→terminated）；非法转换 → `SYSTEM_ERROR`。
```
任一不变量被违反 → `SYSTEM_ERROR` 审计事件 + 快照标记 `audit_violations`。

---

## 6. 复现与审计

### 6.1 不可篡改日志格式（已定）

只追加（append-only），每条记录：

```json
{
  "seq": 98765,                     // 全局单调递增
  "round": 100, "phase": 4,
  "actor": "A007",
  "type": "TRANSFER",
  "payload": {"tx_id":"T-100-42","from":"A007","to":"A012","amount":500,"fee":5,"reason":"trade"},
  "mono_ts": 100442,                // 逻辑时间, 非墙钟
  "prev_hash": "sha256:....",
  "hash": "sha256:...."             // = H(canonical_json(去掉hash字段的整条记录))
}
```
- `hash` 使用规范 JSON（键排序、无空格）→ SHA-256，形成**哈希链**（Merkle 链式）。任意篡改会破坏后续所有 `hash`。
- 可选：每条 `hash` 再进 Merkle 树，提供根 `merkle_root` 供外部锚定。

### 6.2 日志重放流程（已定）

```
replay(seed, engine_version, log) -> WorldState:
  1. 校验 engine_version 匹配；校验哈希链完整（若断开 → 拒绝重放）。
  2. state := InitialState(seed)            # 由 seed 确定性生成初始禀赋/出生
  3. for record in log (按 seq 升序):
        state := fold(apply_event, state, record)   # 纯折叠，不重跑 hook
        if record.round/phase 越界或类型未知 -> 报错
  4. return state
```
- **首跑 vs 重放一致**：首跑时事件由 hook 生成并写入日志；重放时**只折叠日志中的事件**，不重算 hook。故两者状态逐位相同（前提：日志完整）。
- `apply_event` 对每种 `type` 有确定性实现，与 hook 语义一致，由一致性测试守护。

### 6.3 指标快照与逐位一致（已定）

- 统计程序：`metrics(log, T) -> snapshot`（§5.0 格式）。
- **逐位一致的保证**：
  1. 金额整数运算；除法最后一步、定点输出。
  2. 规范 JSON 序列化（键排序、浮点 `round(...,6)`）。
  3. 所有排序/遍历有全序 tie-break（P5）。
  4. 无墙钟、无环境依赖、无并发不确定性。
- 验证手段：CI 中对同一日志跑两次 `metrics()`，断言输出字节相等；对同一 seed 首跑与重放断言状态哈希相等。

### 6.4 异常检测清单（已定）

| 检测项 | 触发条件 | 处置 |
|---|---|---|
| 哈希链断裂 | `record.prev_hash != prev.hash` | 拒绝重放，报 `AUDIT` |
| seq 非单调 | `seq` 不严格递增 | 报 `AUDIT` |
| 货币守恒破坏 | §5.9 式(1) 不为 0 | 报 `SYSTEM_ERROR`，整回合中止 |
| 交易不原子 | 式(2) 不成立 | 报 `SYSTEM_ERROR` |
| 状态非法转换 | 命中非白名单 status 转移 | 报 `SYSTEM_ERROR` |
| 负现金越界 | 未经允许的 `cash < 0` | 报 `AUDIT`（视经济层口径） |
| 消息越配额 | 某发送者超 §4.2 上限 | 记录 `DROPPED`，统计超限次数 |
| LLM 预算越界 | 每回合调用超 `LLM_BUDGET` | 记录降级事件，统计降级率 |
| 非确定复现 | 两次 `metrics()` 不等 | 硬失败（CI gate） |

---

## 7. 与依赖层的衔接（接口清单）

对 **economy layer（econ-mechanism-designer）** 已对齐：
- 挂载：`settle_market`、`settle_obligations`、`apply_tax` 的 `Delta` 语义与事件类型（§2.3）。
- **已定**：mu 进制 = 100（D0-1）；允许负现金但由借贷背书（§5.9 式(3)）；流速仅计 TRANSFER+MARKET_TRADE（§5.6）；新增 `INTEREST_CHARGED` 事件（4.2）；`apply_tax` 内部子序（§1.3）。

对 **lifecycle layer（lifecycle-anticheat-designer）** 已对齐：
- 挂载：`apply_metabolism`、`apply_penalty`、`check_lifecycle`、`resolve_revival`、`check_death`。
- **已定**：濒死判定用「扣税/代谢后的 E_eff」（D1-1）；status 白名单 6 值（§5.9 式(5)）；负资产通信惩罚分档（§4.3，已定）；`TRANSFER`/`MARKET_TRADE` 必带 `counterparty_id`+`flags` 且 `W_wash=4` 确定性打标（§2.3/§1.3）；死亡计数基于 `E_eff`（§5.3）。
- 字段对齐：`STATE_CHANGE`/`AGENT_DIED` 提供 `death_round`、`cause`，供 §5.3/§5.4。`REVIVE_FEE_PAID` 为独立事件（4.7 发）。

对 **sandbox-test（sandbox-test-lead）** 需提供/确认：
- 可用复现入口：`run(seed, config, rounds)`、`replay(log)`、`metrics(log, T)`。
- 阈值参数符号（§3 D3-1）与成本模型（§3.3 D3-2）供其标定与预算。

---

## 8. 「已定」与「待讨论」汇总

**已定（v1 基线，可直接实现）**：
- 整数货币 P1（**1 CR = 100 mu**）；状态=日志函数 P2；纯函数裁决 P3；显式随机 P4；全序 tie-break P5；只追加日志 P6；意图/事实分离 P7。
- 六阶段回合顺序（§1.2）与 hook 链顺序（§1.3）；`apply_tax` 内部子序（铸币→收入税→财富税→UBI）；`W_wash=4` 反作弊打标。
- 层级化确定性 RNG（§1.4）。
- Hook 接口签名与幂等契约 I1–I5（§2.2）；事件类型表（§2.3，含 `INTEREST_CHARGED`、`REVIVE_FEE_PAID`、`counterparty_id`/`flags`）。
- T0/T1/T2 分层与唤醒集合 W1–W6（§3.1/§3.2）；成本闸门降级策略（§3.3 末）。
- 三通道数据结构与配额表（§4.1/§4.2）；负资产/状态分档收紧发声权（§4.3，6 档）。
- 全部指标公式与边界定义（§5.1–§5.9）；流速口径（仅 TRANSFER+MARKET_TRADE）；负现金由借贷背书（§5.9 式(3)）。
- 日志格式与哈希链、重放流程、快照格式、异常检测清单（§6）。

**待讨论（开放问题）**：
- D0-2 是否需要回合内子 tick。
- D3-1 投资/濒死阈值取值；D3-2 主动决策率 `a`、濒死求助率 `p2`、T1 占比 `p_t1` 的实测标定（沙盒回放标定；已有初值 a=0.6、p2=0.70）。
- D4-1 消息配额具体数值；D4-3 是否给「求救消息」免配额白名单通道。
- D5-1 Gini 负值处理口径（平移法 vs 非负子集，建议两者都出、平移为主）。
- D5-4 网络指标是否需要时间窗版本；D5-5 关系网络是否剔除 `flags` 标记的作弊边。

---

*（本文件为 v1 草案，所有接口与公式以「可直接实现、与 lifecycle/econ 日志字段对齐」为目标；待讨论项交 Leader 汇总裁决。）*
