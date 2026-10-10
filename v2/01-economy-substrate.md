# 01 · 经济底座（Economy Substrate）：价值创造 + 制度工具箱 v2

> 领域：经济机制设计 | 作者：econ-mechanism-designer | 版本：v2 设计提案（设计层，不改代码）
> 定调（用户拍板）：**我们不做「替小镇规定一套经济」，而做「给他们能自己造经济的底座与工具」。**
> 分层：**A 物理层（我们必须定死）→ B 制度层（AI 自己涌现）→ C 保底（防自毁、不越俎代庖）**
> 联动：T79（公开/群聊，制度靠对话协商形成）、T80（v2 roadmap）
> 上游：`v1/01-economy.md`（四层闭环）、`v1.2/evidence/ablation_final.md`（canonical 实测）、`T62`（canonical 信贷档）

---

## 0. 设计哲学与三层职责边界

### 0.1 用户问题的直答
> 「作为 AI 自己驱动的小镇，我们有必要替他们设计一套经济吗？他们能不能自己设计？但必须要有产生的手段。」

**答案：不能替他们设计制度，但必须给他们"产生价值的手段"和"结算的工具"。** 理由：
- **经济制度（谁雇佣谁、工资多少、税怎么收、钱发不发）应由 AI 自己谈出来**——这才是"AI 自己驱动的小镇"的实验价值所在。
- 但 AI **不可能**自己定义"劳动如何变成产出""一笔支付如何原子成立""账本如何不可篡改"——**这些若不写死，世界无法结算、无法复现，实验不成立**。所以物理层必须由我们定。
- 关键前提：必须存在**价值创造的手段**（生产函数），否则"钱只会被消耗、不会被创造"——当前 canonical 正是这个病。

### 0.2 三层职责边界（核心表）
| 层 | 谁定 | 内容 | 为什么 |
|---|---|---|---|
| **A 物理层** | **我们（写死、可复现）** | 生产函数/产出/库存/消耗/折旧、账本与结算原语、守恒、时间/可见性 | AI 自定义则无法结算/复现；这是"产生手段"的唯一合法源头 |
| **B 制度层** | **AI 涌现（我们只给工具箱）** | 可执行契约原语（雇佣/借贷/租佃/分成）、可协商价格与工资、规范/集体决策、可选铸币阀 | 制度是实验要观察的"涌现物"，写死就杀死实验 |
| **C 保底** | **我们（最小、不强制）** | 最小市场、最小救济、总量地板、可选兜底铸币 | 防系统自毁；但**不写死价格/工资/税率** |

> 一句话：**A 是"物理定律"，B 是"玩家能造的规则"，C 是"停电时的应急灯"。**

---

## 1. 诊断：为何货币总量单调减少（实测，canonical B2_N20）

### 1.1 数据来源
`v1.2/evidence/run_abl_B2_N20.jsonl`（canonical N=20 × 84 回合，seed42，rule-based；`economy.enabled=true` + `lifecycle.enabled=true`；`metabolism_mu=140`、`ubi_mu=0`）。124,451 条事件。

### 1.2 货币流向总账（全 84 回合聚合，单位 mu）
| 渠道 | 事件 | 次数 | 金额 | 对总量 | 备注 |
|---|---|---|---:|---|---|
| 创世铸币 | `MONEY_MINTED(genesis)` | 1 | **+200,000** | 创造 | 初始注入 |
| 救助铸币 | `MONEY_MINTED(rescue)` | 2 | **+40,000** | 创造（安全阀） | 濒死才触发 |
| 系统续命贷 | `LOAN_ISSUED`（lender=空=系统发行） | 20 | **+3,321** | 创造 | 会计诚实 `cash↑debt↑` |
| **代谢销毁** | `METABOLISM` | 1,591 | **−219,240** | **销毁（主出口）** | 20×140×≈78 有效回合 |
| 手续费 | `TAX_LEVIED(kind=fee)` | 21 | −21 | 销毁/税池 | 极小 |
| 收入税 | `TAX_LEVIED(income)` | 23 | 260 | 转移（税池） | 极小 |
| UBI | `UBI_PAID` | **0** | **0** | 转移 | **canonical 停用** |
| 转账 | `TRANSFER` | 27 | 2,700 | **零和** | 只改分布 |
| 市场交易 | `MARKET_TRADE` | 21 | 2,100 | 零和（→世界市场账户） | 消费漏出 |
| 存款 | `DEPOSIT` | 19 | 1,900 | 零和（银行内） | — |
| 利息 | `INTEREST_CHARGED` | 270 | 3,443 | 转移（→税池/坏账） | — |
| 坏账核销 | `LOAN_DEFAULT` | 7 | −1,281 | 销毁 | — |
| 复活费 | `REVIVE_FEE_PAID` | 10 | 10,000 | 转移（→bank_reserve） | — |
| 负净值罚 | `PENALTY_APPLIED` | 2 | 2 | 转移 | — |

**净变化核算**：`+200,000 + 40,000 + 3,321 − 219,240 − 21 − 1,281 ≈ +22,779`，与终值 `M(r83)=24,079` 同量级（差额来自 ENDOW/其他小额）。**创造几乎全部来自"救援"，销毁来自"代谢"，中间的经济活动全是零和。**

### 1.3 货币总量曲线（`TURN_SEAL.money_supply`）
```
r0: 197,200 ──(−2,800/回合)──▶ r60: 29,397 ──▶ r72: −402 ──▶ r76: −9,620 ──(救援铸币)──▶ r83: 24,079
```
- **前 59 回合严格线性下滑**：每回合恰好 **−2,800 = 20 人 × 140 mu**，即**纯代谢销毁**，零对冲。
- **r72 起总量为负**：代谢在货币耗尽后**仍继续销毁**，说明"销毁无地板约束"，而 `conservation_ok` 用的是代数恒等式（`minted−burned`），**不约束 `M≥0` 的物理意义**。
- **r77 / r82 两次跳升 +≈18.6k**：是安全阀 `MONEY_MINTED(rescue)` 注入，**证明了"只有救援才创造货币"**。

### 1.4 根因（四条）
| # | 根因 | 证据 |
|---|---|---|
| **R1** | **无生产/无工资 → 没有价值创造入口** | `MARKET_TRADE` 仅 21 笔且多为向世界市场购买（钱漏出），`TRANSFER` 仅 27 笔；无任何"劳动→收入"事件 |
| **R2** | **常规铸币未启用 + UBI=0** | v1 §2.3 的 `M_target=N×E0` 锚**未生效**；`UBI_PAID=0`；唯一发行是 rescue |
| **R3** | **代谢销毁远大于一切创造，且无地板** | 2,800/回合 vs 创造≈0；M 耗尽后继续销毁至 −9,620 |
| **R4** | **零和循环无法补血** | 转账/交易/存款只改变分布，不增加总量 |

### 1.5 核心洞察（写给"小镇如何运转"）
1. **钱 ≠ 价值**：生产创造的是**商品与服务（价值）**，不是货币；货币只是**交换媒介**。所以"没有生产"的直接后果不是"钱变少"，而是"**劳动无法变现、无人有收入、只剩消耗**"。
2. **总量枯竭的直接原因是"回收 > 投放"**：代谢把货币吸走，却没有任何常规投放（工资/采购/铸币）把它送回来 → 单向漏斗。
3. **小镇运转的答案**：`劳动→产出→出售/工资→收入→消费/纳税→公共品/再生产` 的**循环**，加上一个**总量锚**（投放≈回收）保证货币不枯竭也不膨胀。

> 结论：v1 的经济是"**半张网**"——只有回收、没有创造入口、没有制度层。v2 要补的是 **A 层的"产生手段"** 与 **B 层的"制度工具箱"**。

---

## 2. A 物理层规格（我们必须定死；AI 不能自定义）

> 原则：**确定性、可审计、可复现**；AI 只能**使用**这些原语，不能**改写**它们。

### 2.1 生产函数（价值创造的唯一合法源头）

**投入 → 产出**（每个劳动 tick 的确定性命中）：
```
qty(g, agent, t) = floor( base_rate[g] × (1 + 0.1 × skill_level[agent][g])
                        × resource_factor[place(t)][g][t]
                        × (1 + tool_bonus[agent][g]) )
```
| 符号 | 含义 | 默认 | 可调 |
|---|---|---|---|
| `base_rate[g]` | 每劳动 tick 的基础产出（单位） | 食物 2、材料 1、工具 0.3、服务 1、艺术品 0.2 | 按商品 |
| `skill_level` | 技能等级 0–20，由 `SKILL_PRACTICE` 确定性增长 | 起始 0，每次练习 +1（上限 20） | 成长曲线 |
| `resource_factor` | 场所资源丰度 ∈[0.2,1.0]，可再生/衰减，固定种子 PRNG | 场所基础丰度；每回合 ±5% 波动（种子确定性） | 波动率 |
| `tool_bonus` | 持有对应工具加成 | 每件工具 +0.2（上限 +0.6） | 加成系数 |

- **确定性**：所有随机项用 `draw_u64(seed, stream="resource", round, place_id)`，可重放。
- **产出物**：带 `good_id`（可扩展注册表）、`qty`、可选 `quality`（v2 先不做）。
- **产出入库存**：产生 `PRODUCE` 事件；**若库存超上限则溢出丢弃**（记 `PRODUCE_OVERFLOW`）。

**消耗与折旧**：
| 机制 | 规则 | 默认 |
|---|---|---|
| 生存消费 | 每回合需消费 `food ≥ need[g]`，否则福祉/体力下降（对接 lifecycle，不直接判死） | `need_food=1 单位/回合` |
| 生产投入品 | 生产需消耗上游投入（food←seed、tool←material、service←无） | 按配方 `recipe[g]` |
| 折旧 | 工具/资产每回合 `δ` 折旧，floor 0 | `δ=2%/回合` |

**技能成长**：`SKILL_PRACTICE(agent, skill)` → `SKILL_LEVEL_UP`；技能越高产出越大 → **价值创造有"成长"维度**。

> **关键定性**：生产函数是"钱能被创造"的**正当性来源**——因为有真实产出/效用，货币投放（工资/采购/铸币）才有对应的商品背书。**没有生产的铸币只是通胀**。

### 2.2 商品 / 库存数据模型
```
good:      { good_id, kind ∈ {food,material,tool,service,art}, unit, p_ref_mu, shelf_life|None }
inventory: { owner_id, good_id, qty }            # 每个 Agent 一个库存表；世界有 public_stock
recipe:    { output_good, inputs:[(good_id, qty)], labor_ticks }
```
- **参考价 `p_ref_mu`**：仅用于**统计计价与铸币挂钩**，**不是成交价**（成交价由 B 层协商/市场形成）。
- **库存上限 `cap_mu`**：防囤积（默认 = 10×E0）；超限溢出。

### 2.3 结算原语（账本，确定性可审计）
- **货币事件复用 v1.1/08**：`TRANSFER` / `MARKET_TRADE` / `DEPOSIT` / `WITHDRAW` / `LOAN_*` / `TAX_LEVIED` / `UBI_PAID` / `MONEY_MINTED` / `MONEY_BURNED` / `METABOLISM`。
- **新增商品族事件**（A 层，登记进 08 事件表）：
  | 事件 | 语义 | payload |
  |---|---|---|
  | `PRODUCE` | 生产产出入库存 | `agent_id, good_id, qty, place, activity` |
  | `CONSUME` | 消费/投入品扣减 | `agent_id, good_id, qty, purpose` |
  | `DEPRECIATE` | 资产折旧 | `agent_id, asset_id, delta_mu` |
  | `PRODUCE_OVERFLOW` | 库存溢出丢弃 | `agent_id, good_id, qty_dropped` |
- **原子性**：一笔成交 = `买方扣款 + 卖方交货 + 双方手续费` 三合一，要么全成要么全回滚（沿用 v1 §3.3）。
- **守恒（双账本）**：
  - 货币：`Σcash + 银行库存 + 税池 = M0 + ΣMINT + Σ系统贷 − ΣBURN − Σ坏账`
  - 商品：`ΣPRODUCE = ΣCONSUME + Σ库存 + Σ溢出 + Σ折旧耗损`
- **守恒校验**：任一回合不成立 → 全回合回滚 + `ECONOMY_INVARIANT_VIOLATION`（沿用 v1）。
- **新增硬约束（补 R3）**：`M(t) ≥ 0` 恒成立；代谢销毁时若 `Σcash < burn`，只销毁可得部分，**绝不允许总量为负**（当前 canonical bug）。

### 2.4 时间 / 可见性（沿用）
- 回合制（"模拟周"时间尺度，见 00 架构）；Phase 4 全序不变；
- 可见性：Agent 只能看到授权信息（感知范围），**不能读全市场底牌**（防套利）；
- 价格/工资的呈现由 B 层协商决定，A 层不预设。

---

## 3. B 制度工具箱规格（AI 自己造经济）

> 原则：**我们给"可执行契约 + 协商媒介 + 集体决策 + 有阀门的铸币权"，参数（工资/利率/税率/价格）一律不写死，由 AI 谈、由市场形成。**

### 3.1 可执行契约原语（由确定性执行器托管）
AI 通过对话（T79）协商条款，达成后注册为契约，**执行器只做确定性结算，不参与定价**。

| 契约类型 | 字段 | 执行器行为 |
|---|---|---|
| `EMPLOYMENT` 雇佣 | `employer, employee, wage_mu, slots_per_day, duration, task` | 每约定时段：扣雇主、发雇员（不足则 `CONTRACT_VIOLATED`） |
| `LOAN` 借贷 | `lender, borrower, principal, rate_bp, due_round, collateral` | 计息/催收/没收抵押/坏账（复用 v1.2 信贷规则，但**参数由双方谈**） |
| `TENANCY` 租佃 | `owner, tenant, asset, rent_mu, duration, output_share_bp` | 每回合收租；产出按 share 分配 |
| `PROFIT_SHARE` 分成 | `parties[], revenue_split_bp[]` | 收入按比例自动分配 |
| `COOPERATIVE` 合作 | `members[], shared_pool, rule` | 共池资金/库存共用 |
| `SERVICE` 服务 | `provider, client, fee_mu, task` | 完成后结算 |

**契约生命周期事件**（复用 v1.1 既有 `OFFER_*`）：
```
OFFER_CREATED → (COUNTERED → ... ) → OFFER_ACCEPTED → CONTRACT_CREATED
                                                     → CONTRACT_FULFILLED | CONTRACT_VIOLATED | CONTRACT_EXPIRED
```
- **违约** → `PENALTY_APPLIED` + 信用降级（复用 v1.2 `recent_default` 冷却），且**违约记录公开可查**（声誉）。
- **执行器是唯一的"法院"**：只按契约字段确定性执行，不做主观裁决。

### 3.2 可协商的价格与工资（不写死）
- **价格**：由 `MARKET_TRADE`（订单簿/标价）与 `OFFER_*`（点对点议价）共同形成；**A 层只提供撮合与结算，不设价格**。`p_ref_mu` 仅用于统计计价，**不得强制为成交价**。
- **工资/利率/租金**：完全由契约双方协商（B 层），A 层不设默认值。
- 仅要求：**成交/支付仍走原子结算**，价格写入事件（供"价格离散度"指标）。

### 3.3 规范与集体决策（制度涌现的法律接口）
| 原语 | 事件 | 用途 |
|---|---|---|
| 提案 | `NORM_PROPOSED{by, rule_text, scope, params}` | 提出税收/公共品/铸币/价格管制等规则 |
| 投票 | `VOTE_CAST{voter, proposal_id, choice}` | 表决 |
| 采纳 | `NORM_ADOPTED{proposal_id, yes, no, threshold}` | 达阈值即生效（默认 >50% 存活 Agent） |
| 违反 | `NORM_VIOLATED{agent, norm_id, evidence}` | 记录违规（可触发集体惩罚） |

- **规范可参数化**：如 `{"type":"income_tax","rate_bp":800}`、`{"type":"public_good","good":"school","budget_mu":5000}`。
- **生效方式**：AI 通过的税/公共品规则由执行器**确定性执行**（税率来自规范参数，不来自我们的默认值，除非 AI 没提）。
- ⚠️ **边界**：AI 可改"税率/该不该征税/公共品预算"，**不可改** A 层的生产函数、结算原语、守恒（那会导致世界不可复现）。

### 3.4 可选铸币阀（有上限、可审计）
- **谁能发**：只有**经 `NORM_ADOPTED` 通过的铸币规则**，或 C 层兜底才能触发 `MONEY_MINTED`；单个 Agent **无权**凭空造币。
- **阀门（确定性硬上限）**：
  ```
  issue_t ≤ issue_cap           # issue_cap = α × M_target，默认 α=5%
  M_target = N_alive × E0       # 动态锚：随存活人数缩放
  累计发行 ≤ M_target × β       # β=1.0，硬顶防超发
  ```
- **挂钩规则（AI 可选）**：① 税池缺口；② 公共品预算；③ `存活率 < ρ_min` 的救助；④ 无挂钩的等额 UBI。
- **审计**：每次发行落 `MONEY_MINTED{by, amount, reason, vote_id, issue_cap_at_time}`，可复算。
- **为什么必须有阀**：没有上限的铸币权 = 通胀核弹，会让币值、死亡判定、Gini 全部失去意义（见下段影响分析）。

### 3.5 "AI 怎么用它自己造经济"——剧本化示例
1. **分工与生产**：A 在农场用劳动 tick 产 `food`（`PRODUCE`）；B 练习获得 `tool` 技能。
2. **雇佣契约**：A 通过 DM 向 B 发 `OFFER_CREATED{EMPLOYMENT, wage=300mu/日}`；B `OFFER_COUNTERED{wage=400}`；双方 `OFFER_ACCEPTED` → `CONTRACT_CREATED`。执行器每日扣 A、发 B。
3. **市场与价格**：A 把 food 挂单，C/D 竞价买入 → 成交价随供需波动（**价格离散度指标**由此产生）。
4. **借贷与投资**：B 想买工具，向 A 提议 `LOAN{principal, rate_bp, due}`；A 接受 → B 得资金买入 → 未来用工资偿还。
5. **集体制度**：C 提 `NORM_PROPOSED{"type":"sales_tax","rate_bp":500}` 用于资助"学校"（公共品）；`VOTE_CAST` 过半 → `NORM_ADOPTED` → 执行器开始征税。
6. **铸币决策**：若镇子货币不足，D 提 `NORM_PROPOSED{"type":"mint","amount":...,"target":"public_goods"}`；投票 + 阀内执行 → `MONEY_MINTED(by=vote_id)`。
> **全过程无一处需要我们写死工资/价格/税率/是否铸币**——这正是"AI 自己造经济"。

---

## 4. C 保底机制（防自毁，但不越俎代庖）

| 保底 | 触发 | 行为 | 是否写死参数 |
|---|---|---|---|
| 最小市场 | 常开 | 世界市场账户 `MARKET` 以**参考价±带宽**买卖必需品，保证商品可流通 | 用 `p_ref` 带宽，**不强制成交价** |
| 总量地板 | `M(t) < μ_floor` | **只暂停代谢销毁**，绝不让 `M` 为负（补 canonical bug）；不铸币 | `μ_floor=0` |
| 存活救助 | `存活率 < ρ_min` | 一次性 UBI/减代谢（复用 v1 安全阀），打 `flag=rescue`，统计可剔除 | `ρ_min=60%` |
| 兜底铸币 | `M < 0.9×M_target` 且 AI 无规则 且持续 `W` 回合 | **最后一手段**小幅发行补至锚，打 `flag=fallback` | 仅在 AI 沉默时；有上限 |
| 自洽 | 始终 | 即使 AI 什么都不造，系统仍能结算、守恒、复现、Agent 能靠最小生产存活 | **不写死税/工资/价格** |

> C 层哲学：**保底只保证"不崩溃"，不保证"繁荣"**。繁荣必须由 AI 自己谈出来。

---

## 5. 验收指标

### 5.1 宏观指标（确定性、只读日志）
| 指标 | 口径 | 期望区间（N=20 沙盒） |
|---|---|---|
| 货币总量 `M_total` | `TURN_SEAL.money_supply` | ∈ [0.9, 1.1]×M_target 且**全程 >0**（当前 −402 = 硬失败） |
| 货币流速 `V` | `(ΣTRANSFER+ΣMARKET_TRADE)/M` | [0.3, 1.5]（当前 ≈0.04，近乎冻结） |
| 基尼 `Gini` | 净值分布 | [0.2, 0.5] |
| 总产出 `Y` | `Σ PRODUCE × p_ref` | >0 且**不萎缩**（需有增长/平台） |
| 中位工资 | `Σ wage / 受雇人数` | ≥ `metabolism`（否则必死，当前无工资） |
| 死亡率 / 存活率 | `AGENT_DIED` / 存活占比 | 沙盒目标"多数存活、少数死亡、有复活" |
| 铸币/销毁平衡 | `|Mint − Burn| / M` | < 5%（稳态近似） |

### 5.2 制度涌现指标（v2 核心新增）
| 指标 | 口径 | 观测意义 |
|---|---|---|
| 雇佣合同数 | `CONTRACT_CREATED(type=EMPLOYMENT)` 活跃/累计 | AI 是否自发形成雇佣关系 |
| 契约多样性 | 契约类型去重数 / 6 类 | 制度丰富度 |
| 价格离散度 | 同类商品成交价 `CV = σ/μ` | 价格是否"形成"（>0 即有议价） |
| 规范采纳数 | `NORM_ADOPTED` 计数（按 type 分组） | 集体制度是否涌现 |
| 发行决策数 | `MONEY_MINTED(by=vote_id)` 计数 / 铸币提案数 | 货币主权是否被 AI 使用 |
| 公共品供给 | 公共品预算执行额 / 公共品数量 | 集体行动落地程度 |
| 契约履约率 | `CONTRACT_FULFILLED / (CREATED)` | 制度可信度 |
| 违约/坏账率 | `CONTRACT_VIOLATED`、`LOAN_DEFAULT` 占比 | 制度风险 |

> 全部指标**只折叠日志、纯函数计算、可重放**，不依赖 LLM 判断（延续铁律）。

---

## 6. 与 v1 / T79 的接口 + 不改引擎的映射

### 6.1 复用与新增（不改内核骨架）
| 类别 | 复用（v1.1/08 已有） | 新增（A 层登记进 08） |
|---|---|---|
| 货币 | `TRANSFER/MARKET_TRADE/DEPOSIT/LOAN_*/TAX_LEVIED/UBI_PAID/MONEY_*/METABOLISM` | 无 |
| 商品 | — | `PRODUCE / CONSUME / DEPRECIATE / PRODUCE_OVERFLOW` |
| 契约 | `OFFER_CREATED/COUNTERED/REJECTED` | `OFFER_ACCEPTED / CONTRACT_CREATED / FULFILLED / VIOLATED / EXPIRED` |
| 制度 | `NORM_PROPOSED/ADOPTED/VIOLATED` | `VOTE_CAST` |
| 结算执行 | Phase4 hook 机制 | 新增 `apply_contracts()`、`apply_production()` 两个 hook（挂在 4.1 前/4.1 内） |

- **不改引擎骨架**：全部通过"新增事件类型 + 新增 hook"接入既有 Phase4 全序；`engine_version` 指纹随 config 变化（属预期）。
- **与 T79 联动**：制度靠**对话**形成——`OFFER_*`/`NORM_PROPOSED` 的发起与议价发生在公开/群聊通道（T79），执行器只做结算。

### 6.2 两个必须的契约登记请求（交 08）
1. 商品族 4 个事件 + 契约族 5 个事件 + `VOTE_CAST`，登记进 08 §1.2（含 payload）。
2. A 层硬约束 `M(t) ≥ 0`（代谢销毁不得致负）——这是对 canonical bug 的修复口径。

---

## 7. 已定 / 待讨论

### 7.1 已定（v2 提案生效）
1. **三层职责边界**：A 物理层写死、B 制度层 AI 涌现、C 保底不越权；
2. **诊断结论**：货币单调减少 = 无生产入口 + 常规铸币未启用 + UBI=0 + 代谢销毁无地板（4 根因，实测支撑）；
3. **A 层**：生产函数公式 + 库存/消耗/折旧 + 商品族结算原语 + 双账本守恒 + `M≥0` 硬约束；
4. **B 层**：6 类可执行契约 + 价格/工资不写死 + 规范/投票 + 有阀门的铸币权；
5. **C 层**：最小市场/总量地板/救助/兜底铸币（均带 flag，不写死税价）；
6. **验收**：宏观 7 项 + 制度涌现 8 项。

### 7.2 待讨论
| # | 议题 | 影响 | 建议 |
|---|---|---|---|
| Q1 | 生产函数具体数值（base_rate/recipe/p_ref） | 经济活力与校准 | 沙盒扫描标定 |
| Q2 | `issue_cap` 的 α、β 取值 | 通胀/超发风险 | α=5%、β=1.0 起步，扫描 |
| Q3 | 契约违约的集体惩罚是否允许 | 制度强度 vs 误伤 | 交 AI 用规范决定 |
| Q4 | 商品种类注册表初始集合 | 分工深度 | 5 类起步，可扩展 |
| Q5 | 铸币是否允许挂钩"汇率的"外部？ | 复杂度 | v2 不做 |
| Q6 | C 层兜底铸币是否算"干预自然演化" | 实验解释力 | 打 flag，统计可剔除 |
| Q7 | 价格参考价带宽 ±多少 | 最小市场是否扭曲价格 | 交沙盒标定 |
| Q8 | 与 T79 的对话协议如何承载 `OFFER_*`/`NORM_*` | 制度涌现率 | 联动设计 |

---

## 附：诊断数据可复现命令
```bash
python3 - <<'PY'
import json
from collections import Counter, defaultdict
f='v1.2/evidence/run_abl_B2_N20.jsonl'
amt=defaultdict(int); cnt=Counter()
for line in open(f):
    e=json.loads(line); t=e['type']; p=e.get('payload',{}); cnt[t]+=1
    if t=='MONEY_MINTED': amt[t]+=p.get('amount',0)
    elif t in ('METABOLISM','INTEREST_CHARGED','REVIVE_FEE_PAID','DEPOSIT','UBI_PAID'): amt[t]+=p.get('amount',0)
    elif t=='TAX_LEVIED': amt[t]+=p.get('amount',0)
    elif t=='TRANSFER': amt[t]+=p.get('amount',0)
    elif t=='MARKET_TRADE': amt[t]+=p.get('amount',0)
    elif t=='LOAN_ISSUED': amt[t]+=p.get('principal',0)
print(dict(amt))
PY
```

---

*（文档结束，v2 设计提案 — econ-mechanism-designer）*
