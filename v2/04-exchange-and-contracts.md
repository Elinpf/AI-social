# 04 · Agent 间交易与契约原语（Exchange & Contract Primitives）v2

> 领域：经济机制设计 ｜ 作者：econ-mechanism-designer ｜ 版本：v2 设计提案（设计层，不改代码）
> 任务：P2 首要命题 **G-P1-1（商品→货币转换通道缺失）** 的 A 层原语设计
> 修订：v2.1 —— 并入 Leader E1–E7 裁决 + A1（`counterparty`）/A2（V2a/V2b 分列），并统一 `INTENT.ECON.*` 命名空间
> 上游依据：`v2/00-roadmap.md`（P2 命题）、`v2/01-economy-substrate.md`（A/B/C 三层与结算原语）、`v1.1/08-engine-stats-extension.md`（事件契约权威）、`v1.2/01-implementation-architecture.md §AD R-08`（回合缓冲/唯一 append）
> 红线（用户拍板，不可破）：**不预设价格 / 工资 / 税率 / 是否铸币**；**确定性内核不得调 LLM**。

---

## 0. 命题、诊断与设计边界

### 0.1 G-P1-1 的正解（本文件要解的题）
**实测（T91/T104/T125）**：`PRODUCE=321`、商品双账本守恒成立，但 `MARKET_TRADE` 仅 21 笔、**`distinct_sellers=1`（卖方全是世界 `MARKET`，`top_seller_share=1.0`）**、`volume=2100 mu`；**Agent 之间零交易**，收入 `I_eff` **P50=0**、正收入者占比 0.4；`WAGE/EMPLOYMENT=0`。

**结论口径**：A 层已给「**产生的手段**」（生产/库存/技能/折旧），但**没有把商品变成货币的通道**——即没有「**双边同意的一手交钱一手交货**」的可落点原语，也没有让 life 侧能**发起**交易的意图通道。故 P2 **不是调参**，而是**补齐 A 层原语、让 B 层能涌现交易与雇佣**。

### 0.2 设计边界（与 `v2/01 §0.2` 三层分离一致）
| 层 | 本次交付 | 绝不交付 |
|---|---|---|
| **A 物理层（写死）** | 成交/契约**结算原语**、发现通道的**只读投影**、守恒与原子性、事件契约 | 具体价格/工资/税率/是否铸币 |
| **B 制度层（AI 涌现）** | 只给**工具箱**（可挂单、可议价、可缔约） | 替 AI 定价、代 AI 决定交易对象 |
| **C 保底** | 沿用 `v2/01 §4` 最小市场（世界 `MARKET` 参考价±带宽） | 把世界市场当成「唯一卖方」（正是当前病根） |

> **一句话**：本文件只造「**能成交的插座**」，不造「插在上面的电器」。

---

## 1. 成交原语（核心）：双边交换结算

### 1.1 定义
**成交原语 = 一笔「双边同意、原子、零和」的交换结算**：
> 两个主体同时、等量地交换各自的「腿」——每条腿是 **商品束和/或货币**；要么**两方全部变更**，要么**整笔不发生**；交换**不创造也不销毁任何商品或货币**（只改归属）。

这是「一手交钱一手交货」的**唯一合法落点**，也是 **goods↔money 通道**的物理实现。

### 1.2 一条原语、两个事件出口（避免与 08 冲突，守「只增不改」）
| 来源通道 | 事件 | 说明 |
|---|---|---|
| **订单簿撮合（order-book）** | **复用 `MARKET_TRADE`**（扩展可选字段 `channel="orderbook"`） | 单商品 × 价格的标准成交；**关键改动：允许 Agent 作为 seller 挂单**（当前只有世界 `MARKET` 挂卖单）→ 自然产生 agent↔agent 成交 |
| **点对点议价 / 契约（p2p / contract）** | **新增 `EXCHANGE_SETTLED`** | 由 `OFFER_ACCEPTED` 或 `CONTRACT_*` 触发的**一般双边交换**（支持多商品/服务/以物易物/工资兑换实物等，`MARKET_TRADE` 表达不了的形态） |

> **为什么要两个出口**：`MARKET_TRADE` 已是订单簿成交的既有契约（承载 `price/scarcity_index` 等指标，**不得改语义**，08 X1）；而议价成交经常是**多腿/非同质**交换，需更一般的 `give/take` 结构。二者共用**同一个结算原语函数** `apply_exchange()`，只是事件的「入口形状」不同。

> **对手方可观测 —— 一等字段 `counterparty`（Leader A1 裁决，硬要求）**：**每笔成交（`MARKET_TRADE` / `EXCHANGE_SETTLED`）必须携带 `counterparty`**，回答「**对手方是谁、是否 world**」。这是 E1/E6/V2 的共同基石——**没有它，「Agent 间交易」无法被合成、G-P1-1 无法被判定**。世界市场 `MARKET` 作为一种特殊 `counterparty`（`is_world=true`）。

### 1.3 结算原语函数（确定性，不调 LLM）
```
# 位于 Phase 4.1（与 settle_market 同层，固定全序）
def apply_exchange(state, deal) -> Delta:
    # deal = {parties:[a,b], legs:[(from,to,good_id,qty)|(from,to,money_mu)], meta}
    # 1) 校验（纯函数，任一不过 → 整笔拒绝，不部分执行）
    assert len(deal.parties) == 2
    for (f,t,g,qty) in deal.goods_legs:
        if state.inventory[f][g] < qty: return REJECT("insufficient_goods")
    for (f,t,amt) in deal.money_legs:
        if state.cash[f] < amt: return REJECT("insufficient_cash")   # 负现金须由借贷背书
    if not transferable(g): return REJECT("good_not_transferable")
    # 2) 双边同时应用（原子）
    for leg in deal.legs: apply_leg(state, leg)      # 交易双方同回合、同序
    # 3) 守恒自检（见 §1.4），不成立 → 整回合回滚（ADR-08）
    assert exchange_conserved(state, deal)
    # 4) 落事件（入本回合缓冲，P6 唯一 append，ADR-08）
    emit(EXCHANGE_SETTLED | MARKET_TRADE, deal)
```
- **失败语义**：校验不过 → 不落成交事件；由 life 侧下次决策或对方收到 `OFFER_REJECTED`/`INTENT_REJECTED`（规则性拒绝，08 §1.2 H）。**不存在半分成交。**
- **原子性来源**：沿用 **ADR-08**——所有 `emit` 入本回合**待提交缓冲区**，**P6 COMMIT 为唯一 append 点**；整回合守恒不成立则**丢弃整缓冲区**（含本回合全部事件）。
- **确定性**：校验/结算全为整数纯函数；`parties` 内应用顺序按 `agent_id` 升序（消除顺序套利）。

### 1.4 守恒（双账本，硬约束）
一笔交换必须**同时**满足：
```
商品零和：  ∀ good_id:  Σ_in qty(g) = Σ_out qty(g)           # 交换不改变商品总量
货币零和：  Σ money_in = Σ money_out                          # 交换不改变货币总量
```
与全局账本衔接（`v2/01 §2.3`）：
```
货币：Σcash + 银行库存 + 税池 = M0 + ΣMINT + Σ系统贷 − ΣBURN − Σ坏账
商品：ΣPRODUCE = ΣCONSUME + Σ库存 + Σ溢出 + Σ折旧耗损       # 交换不进入此式（零和，只改 owner）
```
任一回合不成立 → **整回合回滚 + `ECONOMY_INVARIANT_VIOLATION`**。

### 1.5 不写死价格
- 成交价 `price_mu` **完全来自双方协商**（`OFFER_CREATED.terms.price_mu` / 契约 `terms.price_mu` / 订单簿 `price_mu` 挂单价）；A 层**不设默认价、不设价格带作为成交价**。
- `p_ref_mu`（`v2/01 §2.2`）**仅用于统计计价与铸币挂钩**，**不得强制为成交价**（红线）。
- 价格写入事件（`EXCHANGE_SETTLED.price_mu` / `MARKET_TRADE.price`），供「价格离散度 `CV=σ/μ`」指标。

---

## 2. 契约底座：life 发起 → 确定性执行

> 契约是「**时间维度的交换**」（现在立约、未来结算），成交原语是「**瞬时交换**」。二者共用同一账本与守恒。

### 2.1 生命周期（复用 08 既有事件，不新增状态机）
```
OFFER_CREATED → (OFFER_COUNTERED → … ×N_round) → OFFER_ACCEPTED → CONTRACT_CREATED
                                                                  → CONTRACT_FULFILLED | CONTRACT_VIOLATED | CONTRACT_EXPIRED
              ↘ OFFER_REJECTED / OFFER_EXPIRED（协商失败）
```
- **发起（life）**：life 决策相位产出 `INTENT.ECON.OFFER{kind, to[], terms, enforceable}`（§5）→ 内核封装为 `OFFER_CREATED`（phase 2/3，08 §1.2 K）。
- **还价/应约**：`INTENT.ECON.OFFER{offer_id, act∈{counter,accept,reject}, terms?}` → `OFFER_COUNTERED/ACCEPTED/REJECTED`。
- **成约**：`OFFER_ACCEPTED` → 该契约进入**确定性执行表** → `CONTRACT_CREATED`（phase 2/3）。
- **`kind`**：复用 08 已登记枚举 `{EMPLOYMENT, LOAN, TENANCY, PROFIT_SHARE, COOPERATIVE, SERVICE}`（+ 交换类 `sale` 走 `OFFER_CREATED` 但**不建长周期契约**，直接 §1 成交）。

### 2.2 执行器（唯一的「法院」，确定性）
```
# 新 hook：apply_contracts()，位于 Phase 4.2（结算义务，与 settle_obligations 同层）
def apply_contracts(state, round) -> Delta:
    for c in active_contracts(state, round):        # 按 contract_id 升序，确定性
        if not due(c, round): continue
        if can_fulfill(state, c):                   # 纯函数：雇主余额/库存/期限
            emit CONTRACT_FULFILLED (and settle legs via apply_exchange/转账)
        elif expired(c, round):
            emit CONTRACT_EXPIRED
        else:
            emit CONTRACT_VIOLATED(reason=deterministic_code)  # 如 insufficient_funds
            emit PENALTY_APPLIED / 信用降级（复用 v1.2 规则）
```
- **结算时点**：按 `terms.period`（每 period 回合）、`due_round`（到期日）、或 `terms.slots_per_day`（雇佣按时段）确定性触发。
- **违约判定**：**默认确定性**（余额不足 / 未按期交货 / 期限届满），原因码可复现；**允许软判定但结果冻结**——若某条款需定性判断（如「服务达标」），必须走既有 **`LLM_JUDGMENT`（frozen=true）**（08 §1.2 K），**判定结果冻结后由确定性派生事件执行数值后果**；`replay` **绝不重调 LLM**。
- **硬约束（Leader E4）**：**软判定不得改金额**——**金额只能由确定性结算改**；质量/达标类软判定**只能产布尔**（是否认定违约），且**必须冻结进 `LLM_JUDGMENT`**，由确定性派生事件据此结算，不得在软判定里直接写数值。
- **`enforceable=false`**：君子协定，不判违约（仅记 `CONTRACT_EXPIRED`）。
- **边界**：执行器**只按 `terms` 确定性结算，不参与定价、不做主观裁决**。

### 2.3 契约经济后果仍经 4.1/4.2
契约的每一笔付款/交货，**物理上仍是 `TRANSFER` / `EXCHANGE_SETTLED` / `MARKET_TRADE`**，经同一守恒校验。契约事件（`CONTRACT_*`）是**制度层的「意图/结果」记录**，账务落点仍在结算原语（08 §1.2 P 已明确「契约经济后果仍经 4.1/4.2 结算」）。

---

## 3. 可转让物品：`state.inventory` 如何参与交换

### 3.1 数据模型（已登记，08 §1.2 O.2）
```
state.inventory : { owner_id → { good_id → qty:int } }   # qty 单位 = milli-unit（1 unit = 1000 milli）
```
- **入 `state_hash`**：按 `owner_id`、`good_id` 双键 `sorted` 规范化 → 同状态逐位一致、可复现。
- **单位一致**：与商品族事件 `PRODUCE/CONSUME/DEPRECIATE/PRODUCE_OVERFLOW` 的 `qty` **同单位（milli）**，可直接加减（08 O.1/O.2）。

### 3.2 交换/转移如何改 inventory（守恒的形式化）
一笔 `EXCHANGE_SETTLED` 对 `inventory` 的作用 = 对每条商品腿执行：
```
inventory[from][good] -= qty ;  inventory[to][good] += qty     （同一回合、原子）
```
并要求 `∀good: Σ_from qty = Σ_to qty`（§1.4 商品零和）。**交换不改 `Σ库存`**，只改 `owner` 归属。
- **失败保护**：`inventory[from][good] < qty` → 整笔拒绝（不落事件、不改状态）。
- **转移是 `EXCHANGE_SETTLED` 的退化形态**：当一方腿为纯商品、另一方腿为纯货币，即「卖货收钱」；当双方腿都是商品，即「以物易物」。

### 3.3 可转让性（`transferable`）
| 商品 `kind` | 可转让 | 说明 |
|---|---|---|
| `food` / `material` / `tool` | ✅ | 标准可转让、可库存 |
| `art` | ✅（`shelf_life=None`） | 收藏品，可转让 |
| `service` | ⚠️ **非库存、即时交付** | 不落 `inventory`；用「服务腿」= 当场 `EXCHANGE_SETTLED`（一方付钱、另一方交付即消失于履约），或走 `SERVICE` 契约 |

> 新增可选字段 `good.transferable: bool`（默认 `true`），供 A 层约束「某些物品不可转让」（如绑定身份的资产）——**只增字段，不改语义**。

---

## 4. 发现机制：Agent 怎么知道「谁有货 / 谁要货」

> **结论：不新造「发现原语」，复用既有两条通道 + 一个只读投影。** 发现属「信息」，不是「结算」，守住两层分离。

### 4.1 两条既有通道
| 通道 | 机制 | 复用/新增 |
|---|---|---|
| **公开挂单（订单簿）** | Agent 用 `INTENT.ECON.ORDER_PLACE{good_id, side∈{bid,ask}, price_mu, qty}` 挂单（**v1 已有该意图**，只是缺「Agent 挂卖单」） | **复用**；关键是**允许 Agent 作 maker（含卖家）**，不必只由世界 `MARKET` 挂卖单 |
| **点对点议价** | Agent 用 `OFFER_CREATED{kind, to[], terms}` 主动向指定 Agent（或 `to=[]` 广播）发要约 | **复用 08 既有 `OFFER_*`**（`kind` 已含 `sale/service/…`） |

- **撮合**：订单一进 `settle_market`（Phase 4.1）即按「价格优先 → 时间优先 → 固定种子」撮合（沿 v1 §3.2），成交落 `MARKET_TRADE{channel="orderbook"}`（**买卖双方都是 Agent** 时即 agent↔agent 成交）。
- **`to=[]` 广播要约** = 「公开求购/求售板」，等价于把发现暴露给全镇；单播 `to=[x]` = 私下议价。

### 4.2 一个只读投影：公开簿视图（防底牌，防套利）
- 新增**只读**投影 `orderbook_view(good_id, identity)` → 返回**聚合深度**（各价位挂单量）与**最优买卖价**，供 life 决策；**默认不返回**对手身份与逐单明细（防「抢跑/内幕」）。
- **必须参数化（Leader E2）**：`orderbook_view.identity ∈ {aggregate(默认), named}`——「**匿名 vs 实名**」本身是**制度变量**，应**可被 B 层演化或被消融**，**不得写死在 A 层**。
- **性质**：**由日志/状态派生**，非事件、非新原语（`v2/01 §2.4` 可见性：Agent 不能读全市场底牌）。

### 4.3 明确「不新增发现原语」的理由
- 发现 = 信息公开度问题，用 `MSG_PUBLIC`（T79 已建）声明「我有多余 food 想换 tool」是**内容层**做法，天然已有；
- 结构化的「货/钱」撮合沿用订单簿与 `OFFER_*`，**无需第三套原语**——新增只会增加口径冲突面。

---

## 5. life 侧发起通道 + LLM 角色与 thinking 策略

### 5.1 新增意图类型（沿 `INTENT.ECON.*` 命名空间）
| 意图 | 载荷 | 内核封装事件 | phase |
|---|---|---|---|
| `INTENT.ECON.ORDER_PLACE`（已有） | `{good_id, side, price_mu, qty}` | （挂单，成交落 `MARKET_TRADE`） | 4.1 |
| `INTENT.ECON.TRADE`（**新增，P2 暂不启用**） | `{offer_id, accept:bool}` 或 `{counterparty, give:[…], take:[…]}` | `EXCHANGE_SETTLED` | 4.1 |
| `INTENT.ECON.OFFER`（**新增**，→ 封装 `OFFER_CREATED`） | `{act∈{create,counter,accept,reject}, offer_id?, kind, to[], terms, enforceable}` | `OFFER_CREATED/COUNTERED/ACCEPTED/REJECTED` | 2/3 |
| `INTENT.ECON.CONTRACT_SIGN`（**新增，可选**） | `{offer_id}`（成约确认） | `CONTRACT_CREATED` | 2/3 |

> 命名放在 `INTENT.ECON.*` 下（与既有 `ORDER_PLACE/TRANSFER/LOAN_APPLY` 同族），而**非**顶层 `INTENT.TRADE`——**理由**：统一经济意图边界，便于 `ports.py::ALL_INTENT_CLASSES` 一次性登记与门禁。
> **裁决 B（2026-10-10）**：`INTENT.ECON.TRADE` **登记保留但 P2 暂不启用**——offer 链的结算由 `apply_exchange` 折叠 `OFFER_ACCEPTED` 完成（§6.1）。

### 5.2 LLM 的角色（只产「内容/条款」，不写账、不判可行性）
| 环节 | 谁做 | LLM 是否参与 |
|---|---|---|
| 与谁交易、交易什么、开价多少 | **Agent（LLM 决策）** | ✅ 产出 `INTENT.ECON.OFFER`（→`OFFER_CREATED`）与 `INTENT.ECON.TRADE` 的**候选项与条款数值** |
| 议价措辞、说服、还价理由 | **Agent（LLM）** | ✅ 文本内容（N 类） |
| **合法性校验**（余额/库存/可转让/额度/守恒） | **确定性内核** | ❌ 绝不调 LLM |
| **成交/记账/守恒** | **确定性内核** | ❌ |
| 违约判定（默认） | **确定性内核** | ❌（软判定须 `LLM_JUDGMENT` 冻结） |

> **铁律**：LLM 只**产出意图与条款内容**；**可行性、合法性、结算一律确定性**。`life/settlement.py` 的 `_m6_specs`/确定性命中**不得写死交易内容**（防「假涌现」，对齐 T79/T81 教训）。

### 5.3 thinking 策略（对齐用户拍板）
| 角色 | thinking | 用途 |
|---|---|---|
| **居民（life Agent）** | **`false`** | 议价/挂单/缔约决策：**高频、低成本**；措辞+条款一拍产出 |
| **世界 LLM（制度/NORM/观测叙述）** | **`true`** | 起草税收/规范/铸币提案、写「小镇日报」等**低频高价值**推理 |
- **实现**：`LLM_CALL.purpose` 新增 `negotiation`（居民，`thinking=false`，与 `dialogue` 同批接线）；世界级 `purpose` 保持/启用 `thinking=true`。
- **复现**：谈判文本落 `MSG_*`/`OFFER_*.terms`（**内容**）；`replay` 只读文本，**不重调 LLM**（08 C4）。

---

## 6. 与 08 事件契约的对齐清单（先登记，再实现）

> 原则（08 X1/X4）：**只增不改**；新增类型在旧日志不出现；新增可选字段被容忍。所有新增事件必须：① 登记 `engine/events.py::EVENT_TYPES`；② 在 `replay.apply_event` 注册**确定性折叠器**；③ 带 `round/phase/actor` 审计字段。

| # | 类型 | 事件/字段 | phase | payload（关键字段） | 折叠器行为 |
|---|---|---|---|---|---|
| A1 | **新增事件** | `EXCHANGE_SETTLED` | 4.1 | `exchange_id, channel∈{offer,contract}, offer_id?, contract_id?, parties[2], goods_legs:[(from,to,good_id,qty)], money_legs:[(from,to,mu)], price_mu?, place?, activity?, round` | 对 `inventory`/`cash` 逐腿原子应用；校验零和 |
| A2 | **字段扩展** | `MARKET_TRADE.channel∈{orderbook}`（可选） | 4.1 | （既有字段 + `channel`） | 无（纯审计；不改语义） |
| A2b | **一等字段（Leader A1）** | `counterparty`（必带，回答「对手方是谁、是否 world」） | 4.1 | `EXCHANGE_SETTLED.counterparty` / `MARKET_TRADE.counterparty`（world 记 `is_world=true`） | 无（供 E1/E6/V2 合成 Agent 间交易量） |
| A2c | **新增事件出口（Leader E7）** | `ORDER_CANCEL`（撤单必须可观测） | 4.1 | `order_id, agent_id, good_id, side, price_mu, qty, round` | **仅当「有订单簿且该单存在」时才发**；**无簿则仅发 `DROPPED{reason:"no_order_book"}`**（**不伪造事件**，防污染撤单指标） |
| A2d | **相位/原语（Leader 裁决 B）** | `OFFER_ACCEPTED{offer_id}` → 4.1 由 `apply_exchange` 折叠 offer 链生成 deal → `EXCHANGE_SETTLED` | 4.1 | （无新事件，复用 `EXCHANGE_SETTLED`） | deal 由 offer `terms` **唯一确定**；**life 无需产 `INTENT.ECON.TRADE`**（单源，宁少不重） |
| A3 | **新增意图** | `INTENT.ECON.TRADE` / `INTENT.ECON.OFFER`（→`OFFER_CREATED`）/ `INTENT.ECON.CONTRACT_SIGN` | 2/3→4.1 | 见 §5.1 | 内核封装为对应事件 |
| A4 | **复用** | `OFFER_CREATED/COUNTERED/ACCEPTED/REJECTED/EXPIRED` | 2/3 | 既有（`kind` 已含 `sale/service`） | 无需改 |
| A5 | **复用** | `CONTRACT_CREATED/FULFILLED/VIOLATED/EXPIRED`、`VOTE_CAST` | 2/3・3.5/4 | 既有 | 无需改 |
| A6 | **新增字段** | `good.transferable: bool`（默认 `true`） | — | （商品注册表字段，非事件） | 校验用 |
| A7 | **新增 hook** | `apply_exchange()`（4.1）、`apply_contracts()`（4.2） | 4.1/4.2 | — | 挂入 Phase4 全序 |
| A8 | **配置开关** | `policy.exchange.enabled`（§7） | — | `config/policy.json` | 见 §7 |
| A9 | **笼统登记** | `LLM_CALL.purpose += "negotiation"` | 2/3 | 既有事件 | 无需改契约 |

### 6.1 `offer → 成交` 的相位与规则（Leader 裁决 B，2026-10-10）
> **`OFFER_ACCEPTED{offer_id}` → 4.1 由 `apply_exchange` 折叠 offer 链生成 deal → `EXCHANGE_SETTLED`**
> ——**life 无需产 `INTENT.ECON.TRADE`**：accept 只表达「我同意」，**deal 由 offer 的 `terms` 唯一确定** → **单源，宁少不重**。

**三条精确规则（econ-dev 提、Leader 全采纳）**：
1. **有效 `terms` = 链上最后一个 counter 的 terms**（`OFFER_CREATED → OFFER_COUNTERED × N → OFFER_ACCEPTED`）——否则**还价后接受会用旧价结算**。
2. **按 `kind` 分流**：`sale` → 即时 `EXCHANGE_SETTLED`（4.1）；`kind ∈ {EMPLOYMENT, LOAN, TENANCY, PROFIT_SHARE, COOPERATIVE}` → **走 `CONTRACT_CREATED`（2/3）→ `apply_contracts`@4.2 分期结算**（**时间维度的交换**）。
3. **广播 `to=[]` 多方可接受**：每个 accept 生成**各自的双边 deal**、互不影响；**单笔失败 → 该笔 `DROPPED`，不半成交**。

**暂缓注记（防后人以为漏了）**：**`service` 暂按契约走、P2 不做即时成交**——因为它**没有 goods 腿**，「当场交付」的**零和如何定义**是额外设计问题；**`sale` 是最小充分路径，先窄后宽**。

**订单簿完整路径（`ORDER_PLACE` + 撤单 + 簿可见性）留下一波做**——P2 阶段 life **只走 `OFFER`（→`OFFER_CREATED`）路径**（实测 `ORDER_PLACE=0`）。

**与 `sim-engine-stats-architect` 的协同口径（需其确认/登记进 v1.1/08）**：
1. `EXCHANGE_SETTLED` 的**折叠器**与 `market_trade` 折叠器共用 `apply_exchange` 内核；
2. 指标口径（Leader A1 裁决）：**一等字段 `counterparty`** 落在每笔成交（回答「对手方是谁、是否 world」）；核心判据 **`distinct_sellers_excl_world`**（卖方去重、**排除 world**）**> 1**；**agent↔agent 占比 = 分子(双方均非 world 的成交额) / 分母(全部成交额)**；**不去重**，但必须能合成「Agent 间交易量」；
3. 守恒校验（货币式 + 商品式）需把 `EXCHANGE_SETTLED` 纳入**零和事件白名单**（与 `TRANSFER/MARKET_TRADE/DEPOSIT` 同类，不计入 MINT/BURN）。

---

## 7. M3 可消融：`exchange.enabled`（一个开关关掉交易原语）

### 7.1 开关语义（对齐 08 §5.8 开关族纪律）
| 项 | 定义 |
|---|---|
| 名称 | `policy.exchange.enabled`（runtime `config.exchange.enabled` 优先），**默认 `true`（行为不变）** |
| 控制范围（Leader E6 写死） | **语义 = 关闭「agent↔agent 成交」**（**不是**关闭全部成交）：`OFF` 时 life **不产生** `INTENT.ECON.TRADE/OFFER/ORDER_PLACE`（→`OFFER_CREATED`），engine **不挂** `apply_exchange/apply_contracts` |
| `OFF` 的结果 | `EXCHANGE_SETTLED=0`、**agent-as-seller 的 `MARKET_TRADE=0`**、`CONTRACT_CREATED=0` → **Agent 间交易 = 0**；**世界市场 `MARKET` 成交保留**（保底仍在） |
| 与 `economy.enabled` 嵌套 | **`AND`**：`economy=false` ⇒ exchange 无意义（整个经济结算关闭） |
| 纪律 | **不删事件契约、不改守恒、不 fail-loud**（显式消融）；发**审计事件** `DROPPED{reason:"exchange_disabled", flag:"exchange_disabled"}`（08 §5.8 同款）——**「开关生效」的唯一查法 = 查该 `DROPPED`** |
| 与静默失效区分 | 「静默失效」必须 **fail-loud**；「显式关闭」不 fail-loud 且留 flag（08 §5.8 统一纪律） |

### 7.2 消融证伪（M3 判据）
```
开：exchange.enabled=true  → distinct_sellers > 1（卖方含 Agent）、I_eff P50 > 0、CONTRACT_CREATED > 0
关：exchange.enabled=false → distinct_sellers = 1（退回仅世界市场）、I_eff P50 = 0、CONTRACT_CREATED = 0
其余 A 层不变（生产/代谢/守恒照常）→ 差异只能归因于「交易原语」
```
- **证伪力**：若关掉后 `distinct_sellers_excl_world` 仍 >1，则说明「agent↔agent 交易」另有来源（非本原语）→ 设计被证伪。
- **防「假涌现」**：交易若靠**写死常量/规则代劳**产生，则 `OFF` 时不会归零→ 用本对照排除（对齐 `v2/00 §0.3`「写死常量不算涌现」）。

### 7.3 消融矩阵（`economy.enabled × exchange.enabled`，Leader E6 要求）
| `economy` | `exchange` | 预期 | 判据 |
|---|---|---|---|
| `true` | `true`（默认） | 正常：Agent 间交易、世界市场成交、契约皆可发生 | V1–V7 |
| `true` | `false` | **仅 agent↔agent 归零**；世界市场成交保留；生产/代谢/守恒照常 | `distinct_sellers_excl_world=1`、`EXCHANGE_SETTLED=0`、`CONTRACT_CREATED=0`；`M(t)≥0` 仍成立 |
| `false` | `true` | **经济结算整体关闭** ⇒ exchange **无意义**（AND 语义，等价于 exchange 也关） | 无成交、无契约；发 `DROPPED{flag=economy_disabled}` |
| `false` | `false` | 同上级 | 同上 |

> **读法**：只有第 2 行才是「**去交易原语**」的单变量对照（保持其余 A 层不变）——这是 M3 证伪的基准行。

---

## 8. 验收：为什么这能解 G-P1-1（因果链）

```
【病根】Agent 有商品，却无法变现
   ├─(a) 没有「双边同意的成交原语」→ 无法把「我出 food、你出钱」原子落地
   ├─(b) 订单簿不允许 Agent 当卖家 → 卖方只有世界 MARKET（distinct_sellers=1）
   └─(c) life 侧无「发起交易/缔约」的意图通道 → 交易无从被 AI 决策触发

【本设计补的三块原语】
   ① 成交原语 apply_exchange/EXCHANGE_SETTLED —— 原子、零和、双账本守恒、不写死价格
   ② 允许 Agent 作 maker（含卖方）的订单簿 —— 复用 MARKET_TRADE，自然产生 agent↔agent 成交
   ③ INTENT.ECON.{TRADE, OFFER, ORDER_PLACE}（→OFFER_CREATED）—— life 侧可发起交易/议价/缔约

【因果链（可观测）】
   life 决策(LLM, thinking=false) 产出 INTENT.ECON.OFFER（→OFFER_CREATED）/TRADE
      → 确定性校验（余额/库存/可转让）
      → OFFER_ACCEPTED
      → apply_exchange 原子结算
      → EXCHANGE_SETTLED / MARKET_TRADE{买方&卖方∈Agent}
      → distinct_sellers ↑（>1）、成交笔数 ↑、volume ↑
      → 卖方收到货款 → I_eff P50 > 0（商品→货币通道打通）
      → 工资(CONTRACT EMPLOYMENT)/消费/税 随成交出现 → 货币循环

【红线守住】
   价格/工资/税率由 OFFER_CREATED.terms / 竞价值 决定（B 层）——A 层只给插座；
   确定性内核全程不调 LLM；不写死任何价格/工资/税率/铸币。
```
**验收项**：
| # | 验收 | 判据 |
|---|---|---|
| V1 | 原语可用 | `EXCHANGE_SETTLED > 0` 且守恒（商品零和 + 货币零和）成立 |
| **V2a** | **结构性（原语可用）** | `INTENT.ECON.OFFER`（→`OFFER_CREATED`）/`TRADE > 0`、`OFFER_ACCEPTED > 0`（**证明「工具通了」**） |
| **V2b** | **涌现性（AI 真的交易了）** | **`distinct_sellers_excl_world > 1`**、`MARKET_TRADE(seller∈Agent) > 0`（**证明「涌现发生了」**） |
| V3 | 变现 | `I_eff P50 > 0`（≥ 代谢 `metabolism` 为佳） |
| V4 | 契约 | `CONTRACT_CREATED(type=EMPLOYMENT/…) > 0`、履约率 > 0 |
| V5 | 消融 | `exchange.enabled=false` → **V2b/V3 归零、V2a 归零**，其余 A 层不变（世界市场保留，见 §7.3 第 2 行） |
| V6 | 复现/守恒 | `replay` 逐位一致；`ECONOMY_INVARIANT_VIOLATION=0`；双账本守恒成立 |
| V7 | 不写死 | 无任何「价格/工资/税率/铸币」默认值；价格来自 `terms` |
| V8 | 对手方可观测 | 每笔成交带 `counterparty`；`distinct_sellers_excl_world` 可由日志纯函数算出 |

> **V2a/V2b 必须分开报（Leader A2 硬要求）**：否则「**AI 选择不交易**」会被误读成「**原语坏了**」。区分「工具可用」与「涌现发生」——这是 M3 消融教训的延伸。

---

## 9. 已定 / 待讨论

### 9.1 已定（本提案）
1. **成交原语** = 双边同意、原子、零和、双账本守恒的交换结算；**一条函数 `apply_exchange` + 两个事件出口**（复用 `MARKET_TRADE` 订单簿 / 新增 `EXCHANGE_SETTLED` 议价）；
2. **原子性** 走 ADR-08 回合缓冲（P6 唯一 append，整回合回滚）；**失败即整笔拒绝**；
3. **守恒**：`∀good 净额=0`、`Σmoney 净额=0`；交换不进商品总量式；
4. **契约底座**：复用 `OFFER_*→CONTRACT_*` 生命周期 + 新 hook `apply_contracts`（Phase 4.2），**默认确定性违约判定**，软判定须 `LLM_JUDGMENT` 冻结；
5. **可转让物品**：`state.inventory`（milli、入 `state_hash`）参与交换，腿式原子改 owner；`service` 即时交付；新增 `good.transferable`；
6. **发现机制**：**不新造原语**，复用订单簿 + `OFFER_*` + 只读公开簿投影（防底牌/套利）；
7. **life 通道**：新增 `INTENT.ECON.{TRADE, OFFER, CONTRACT_SIGN}`（→`OFFER_CREATED`）；LLM 只产内容/条款，合法性/结算确定性；居民 `thinking=false`、世界 LLM `thinking=true`；
8. **消融**：`policy.exchange.enabled`（默认 true），**语义 = agent↔agent 成交**（世界市场保留），`OFF` 时 Agent 间交易归零并留 `DROPPED{flag=exchange_disabled}`；含 `economy × exchange` 消融矩阵（§7.3）；
9. **对手方可观测（Leader A1）**：每笔成交带**一等字段 `counterparty`**；核心判据 **`distinct_sellers_excl_world`**（§6 A2b、§8 V8）；
10. **验收分列（Leader A2）**：**V2a 结构性（原语可用）** 与 **V2b 涌现性（AI 真的交易了）** 必须分开报（§8）；
11. **撤单可观测（Leader E7）**：`INTENT.ECON.ORDER_CANCEL` 具事件出口 `ORDER_CANCEL`（§6 A2c）。

### 9.2 议题 —— 已由 Leader 裁决（E1–E7 全部【已决】）
| # | 议题 | 裁决 |
|---|---|---|
| E1 | 成交量去重口径 | **分开计**；**加一等字段 `counterparty`**；写死判据 **`distinct_sellers_excl_world`**、**agent↔agent 占比 = 分子(双方均非 world)/分母(全部)**；不去重但须能合成 Agent 间交易量（§6 A1/A2b、§8 V8） |
| E2 | 订单簿是否公开身份 | **默认只见聚合深度**，但 **`orderbook_view.identity` 必须参数化**（匿名 vs 实名是**制度变量**，可被 B 层演化/消融，**不写死 A 层**）（§4.2） |
| E3 | 是否允许以物易物 | **允许**——只允许「钱↔货」等于预设「必须有货币」，违反「不替 AI 设计经济」；零和天然安全（§1.5） |
| E4 | 服务/艺术品质量判定 | **默认按 qty 确定性**；**硬约束：软判定不得改金额**，质量软判定只能产**布尔**（是否违约）且必须冻结进 `LLM_JUDGMENT`（§2.2） |
| E5 | 契约违约集体惩罚 | **交 AI 规范决定**（与 `v2/01 Q3` 一致）；我们只提供 `PENALTY_APPLIED`，**不预设是否惩罚/多重** |
| E6 | 开关嵌套语义 | **`exchange.enabled` 语义 = agent↔agent 成交**（世界市场保留）；`economy=false ⇒ exchange 无意义`；**补消融矩阵**（§7.3） |
| E7 | 撤单可观测 | **批准复用 `INTENT.ECON.ORDER_CANCEL`，但必须有事件出口** `ORDER_CANCEL`（撤单可观测、订单簿状态可审计）（§6 A2c） |

### 9.3 新增术语（需回填 `glossary/LEXICON.md`）
`成交原语（Exchange Primitive）`、`EXCHANGE_SETTLED`、`apply_exchange`、`apply_contracts`、`exchange.enabled`、`公开簿视图（orderbook_view）`、`agent↔agent 成交占比`。

---

## 附：与既有资产的接口（不改内核骨架）
- **继承**：Phase4 全序（4.1/4.2）、ADR-08 回合缓冲、双账本守恒、08 事件契约「只增不改」、`state.inventory` 单位与 state_hash。
- **新增**：2 个 hook（`apply_exchange`@4.1、`apply_contracts`@4.2）+ 1 事件（`EXCHANGE_SETTLED`）+ 3 意图 + 1 配置开关 + 1 商品字段 + `LLM_CALL.purpose=negotiation`。
- **不改**：引擎骨架、既有事件语义、生产函数、生命周期。

*（文档结束，v2 设计提案 — econ-mechanism-designer）*
