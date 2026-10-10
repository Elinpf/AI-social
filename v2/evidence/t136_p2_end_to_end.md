# T136 · P2 端到端：Agent↔Agent 成交首次出现（G-P1-1 解开）

> 运行登记：**sha `e6d77c2`** · **provider `mock(rule-based)`** · seed 42 ·
> **N/rounds = 10×84 → 20×84 → 20×84(消融)** · 开关 `exchange.enabled = true → true → false`。
> 证据：`v2/evidence/t136_raw.json` + 日志 `run_t136_{probe_n10,canon_n20,exchangeoff_n20}.jsonl`（`*.jsonl` 被 .gitignore，sha256 见 raw.json）。

## 0. 结论（先给判据）
| 判据 | N=10×84 | N=20×84 | 消融(off) | 结论 |
|---|---|---|---|---|
| **V2b `distinct_sellers_excl_world > 1`** | **3 ✓** | **3 ✓** | 0 | **达标（G-P1-1 解开）** |
| **V2a 结构化** real_sale `OFFER_CREATED>0` 且 `OFFER_ACCEPTED>0` | 60 / 120 ✓ | 120 / 240 ✓ | 0 / 0 | **达标** |
| `EXCHANGE_SETTLED` | 25 | 23 | **0** | 真实成交出现 |
| `agent_agent_share` | 0.641026 | 0.522727 | 0.0 | — |
| `SYSTEM_ERROR` / `chain_ok` / `replay_parity` / `seals_ok` / `conservation_ok` | 0 / ✓✓✓✓ | 0 / ✓✓✓✓ | 0 / ✓✓✓✓ | 全绿 |

**指纹对照**：不动开关，**单进程 vs 两次独立子进程** `state_hash` 三者**一致** = `7ce8349…`
→ 证明「每段独立进程」的驱动改造**本身没改结果**（先验通过，才上三档）。

> **⚠️ 结论的边界（务必带）**：**P2 只主张一条 —— 「出现了 agent↔agent 成交」**（`EXCHANGE_SETTLED>0` 且非 world）。
> **不主张任何市场结构**（卖方数、集中度等）—— `distinct_sellers_excl_world=3` 是**遍历顺序偏置**（见 §4），
> **结构须在修掉顺序偏置后重测**。

> **LLM 无关性检验**：life 的接受逻辑**完全确定性、不含 LLM** → 真 LLM 应给出**同样的** `EXCHANGE_SETTLED=23`。
> 若 real-LLM 与 mock 在此**不一致**，则是更重要的发现（说明有 LLM 依赖被藏起来）。见 §7。

## 1. 两档对照表（canonical 为主）
| 指标 | probe N=10 | **canon N=20** | 消融 N=20(off) |
|---|---|---|---|
| events | 36,763 | 130,180 | 129,626 |
| `OFFER_CREATED`（real_sale / social_pseudo） | 69 (60 / 9) | 142 (**120** / 22) | 22 (0 / 22) |
| `OFFER_ACCEPTED`（尝试接受） | 120 | **240** | **0** |
| `EXCHANGE_SETTLED`（成交） | 25 | **23** | **0** |
| `MARKET_TRADE`（世界市场保留） | 14 | 21 | 21 |
| `PRODUCE` | 155 | 322 | 321 |
| `distinct_sellers_excl_world`（exch / mt） | 3 (3 / 0) | **3 (3 / 0)** | 0 |
| `distinct_buyers_excl_world`（= union，正确口径） | 5 | 5 | 5 |
| `distinct_counterparty_excl_world` | 4 | 3 | 0 |
| `agent_agent_share` | 0.641026 | 0.522727 | 0.0 |
| `state_hash` | `135a6289…` | `814691d9…` | `8d8d1c3d…` |

> probe N=10 的 `25 / 120 / 69` 与 Leader 的 T133 基线**逐项一致**（基线 seed7、本 run seed42 —— 聚合口径与种子无关）。

> **买方口径说明**：`distinct_buyers_excl_world` 与 `distinct_sellers_excl_world` 同为「**全部成交**」口径
> （= `MARKET_TRADE` ∪ `EXCHANGE_SETTLED`，与 `agent_agent_share` 分母一致）。canonical = **5 = `{P001..P005}`**（正确）。
> 细分键 `..._exchange`（= `{P001..P004}`）/ `..._market_trade`（并集里贡献 P005）供排查，**headline 用并集**。
> 买方权威口径 = `legs.money[].from`（付款方），本数据无物物交换，其与 `goods.to` **等集**。

## 2. 消融（`exchange.enabled=false`）——生效查法
- **`DROPPED{flag:exchange_disabled}` = 168**（08 规定的「开关生效唯一查法」✓）
- `EXCHANGE_SETTLED=0`、`OFFER_ACCEPTED=0`、`real_sale=0` → **V2a/V2b 归零** ✓
- **不是逐位不变**：世界市场保留 `MARKET_TRADE=21`（与 canonical 同），但 `PRODUCE 322→321`（**Δ1**，机理见 §5）。
  正确措辞 = 「**除与库存轨线耦合的 Δ1 外其余不变**」，**不得写「其余 A 层完全不变」**。
- 消融段仍有 `OFFER_CREATED=22` —— **全部 `social_pseudo`**（模板社交要约不受 exchange 开关影响），**不算 V2a 证据**。

## 3. 口径（必须读）
### 3.1 「尝试接受」≠「成交」
`OFFER_ACCEPTED=240` 是**尝试**；**成交**只有 `EXCHANGE_SETTLED=23`。`23 + 217(DROPPED) = 240` 自洽。
**不得把 accept 数当成交数。**

### 3.1b `agent_agent_share` 的**分母定义**（写死，防后人重复犯错）
- **`agent_agent_share`（指标）= 分子(双方非 world 的成交) / 分母(= **全部成交 = `MARKET_TRADE` + `EXCHANGE_SETTLED`**)**（E1 裁决）。canon `23/(23+21)=0.522727`。
- **另一个结构性命题（不叫 share）**：**新的 exchange 路径成交 `25/25` 全部是 agent↔agent** —— 这是**构造性**的（world 不可能成为 offer 链的一环）。**单独陈述，勿混入 `agent_agent_share`。**
  > 早先误报的 `25/25 = 1.000` 是「只用 `EXCHANGE_SETTLED` 作分母」的错误口径，**作废**。

### 3.2 `offer_exhausted`：引擎口径 vs 离线复算（两列）
| DROPPED reason | 引擎口径(=日志) | 离线复算 | 差异 |
|---|---|---|---|
| `good_not_transferable` | 19 | 19 | 0 |
| `insufficient_cash` | 3 | 3 | 0 |
| `insufficient_goods`（真缺货） | **78** | **78** | 0 |
| `offer_exhausted`（售罄） | **117** | **117** | 0 |
| **reclassified（跨回合补全）** | — | **0（同回合 0 / 跨回合 0）** | **0** |

- 离线口径（`obs.metrics_exchange.dropped_reconcile`）：某 `DROPPED{insufficient_goods}` 的 `offer_id` **此前已出现 `EXCHANGE_SETTLED`** ⇒ 已成交过 ⇒ 售罄。
- **本 run 引擎口径与离线复算完全一致（差 0）**：econ 的 `offer_exhausted`（`627e81c`）在该日志上**覆盖完整**；T133 基线同样如此（80→29+51）。
  ⚠️ **勘误**：Leader 早先「~33% 跨回合」的告警**不成立** —— 那批「跨回合多次接受」经 join 后全是 **`good_not_transferable`**（卖不可转让品，每条接受必失败，与回合无关），**不是 `insufficient_goods`**。离线列照出，**该日志/本 run 差值 = 0**。
- `insufficient_goods` 的**真因是广播要约超额认购**（卖方仅持有 1 单位，被多人接受，1 成 N 败），**不是缺货**。

### 3.3 ⚠️ `payload.counterparty` 是「歧义字段」（同名不同义）
`counterparty` = **相对 `actor` 的另一方**，**有时是卖方、有时是买方** → **绝不能由它推 seller/buyer**（早先取到的 `{P002,P003,P004,P006}` 掺进了 P004/P006 两个**纯买方**，即此误）。
**唯一权威口径**：卖方 = `EXCHANGE_SETTLED.legs.goods[].from`（交货方）；买方 = `legs.money[].from`（付款方）。
本 run 的 `distinct_sellers_excl_world` 用 `goods.from`（`628fd11`）；`distinct_counterparty_excl_world` **单列**仅为透明对照。

## 4. ⚠️ 结构性偏置（**实验缺陷**，非涌现）—— 必须写清
canonical N=20：`distinct_sellers_excl_world = 3`（`{P001,P002,P003}`）。**这不是市场结构**：

- **行为完全均匀**：20 个 agent **各挂 6 个 real_sale 要约（共 120）**、**各尝试接受 12 次（共 240）**，无人偷懒。
- **但只有 12 个要约成交，creator 恰 = `{P001,P002,P003}`（id 最小的 3 个）**；P004–P020 的 **102 个要约 0 成交**。
- **机理（实测）**：
  - 挂单创建顺序 = phase2 **按 `agent_id` 升序**（首 seq：P001=26317 < P002=26409 < P003=26503 < P004=26601 < … < P020）；
  - life 接受策略 = 「接受 `visible_events` 里**第一个未接受过的** `OFFER_CREATED`」；广播要约对**所有 agent 可见且顺序相同** → **人人优先接受"最早创建"的那条** → **P001 的要约永远排在最前**。
- **结论**：`distinct_sellers_excl_world = 3` 判据**仍成立**（成交确实发生、且非 world），**但该值不可解释为市场结构 —— 它是遍历顺序支配的、由我们自己的流水线造成的偏置**（**不是自发涌现**）。
- **修掉顺序偏置后必须重测**，才能谈市场结构（否则会把偏置当发现写进证据）。

### 4b. 波及面：**系统性的确定性顺序偏置**（不止 offer 链）
| 路径 | 分布 | id 顺序偏置 |
|---|---|---|
| `EXCHANGE_SETTLED` 卖方 | `{P001,P002,P003}` | **是（最小 id）** |
| `EXCHANGE_SETTLED` 买方 | `{P001..P004}` | **是** |
| `MARKET_TRADE` 买方 | `{P001:11, P002:4, P003:3, P004:2, P005:1}` | **是 —— P001 独占 11/21（52%）** |
| `PRODUCE` | 20 人全有（8425–22274 milli） | 否 |
| `MSG_PUBLIC` | 19 个 actor | 否 |
→ 偏置**局限在「贸易/稀缺配给」路径**（凡「排序决定谁先被服务」处），**不在生产、不在发言**。
→ ⚠️ **P1 时代凡基于 `MARKET_TRADE` 的「谁买到稀缺品 / 不平等」解读，都可能被同一偏置污染** —— 报告若引用过此类结论须一并标注。
→ Leader 将把「**修顺序偏置**」升级为**独立立项**（结算顺序 + 世界市场配给 + life 接受目标，口径统一）。

## 5. 诚实说明
- **`PRODUCE 322→321`（Δ1）**：消融后无库存转移 → 持有量轨线微变 → 生产恰好差 1 单位。**A 层非逐位不变**，据实报（`MARKET_TRADE` 21 不变）。
- 三段 `state_hash` 各不相同（含消融）——预期（不同开关=不同状态）。
- **provider = mock(rule-based)**：判据（成交链路）确定性、不依赖 LLM，mock 足以解 G-P1-1；mock 档同时是**逃逸验证**。**P2 证据记录将追加 real-LLM canonical N=20×84**（与 P1 同口径），达标后即跑。

## 6. 命令（可复现）
```bash
cd social-experiment
# 对照 + 三档（每段独立子进程；env EXCHANGE_ENABLED + engine 侧 config 覆写，不碰 policy.json）
python /tmp/t136.py
# 单段：python /tmp/t136_seg.py  (env: T136_NAME/T136_N/T136_ROUNDS/T136_EXCH/T136_OUT)
# 离线复算：python -c "import json;from obs.metrics_exchange import exchange_metrics; \
#   print(exchange_metrics([json.loads(l) for l in open('v2/evidence/run_t136_canon_n20.jsonl')])['dropped_reconcile'])"
```

## 7. 世界观上下文（**既有性质，非 T136 回归**）
| run | `AGENT_DIED` | 死亡 | 死因 | 存活 | `LOAN_ISSUED` | 死亡回合 |
|---|---|---|---|---|---|---|
| T136 probe N=10 (mock) | 10 | 10/10 | `illiquid_no_credit_N` | 0 | 10 | 61–75 |
| **T136 canon N=20 (mock)** | 18 | **18/20** | `illiquid_no_credit_N` | 2（P018/P020） | 19 | 61–73 |
| P1 canonical (真 LLM) | 18 | 18/20 | `illiquid_no_credit_N` | 2 | 20 | — |
| M3-A baseline | 18 | 18/20 | `illiquid_no_credit_N` | 2 | 19 | — |

- **三 run 完全一致 → 既有性质，不是 T136 的回归。**
- 小镇在第 5–6 天（round 60–76）**基本死光**；84 回合里**前 ~60 回合才是「活着的」**。
  **T136 的 23 笔成交落在 round 14–62，恰好全在此窗口内。**
- 死亡**均匀、与个体无关**（18 人各 1 次、同因、无 id 偏置）→ **系统性经济性质**（`illiquid` + 授信被拒 `count_c:3`），**不是选择效应**。
- **续命机制没救下任何人**：`LOAN_ISSUED` 19–20 次 ≈ 每人 1 次，之后即 `no_credit_N`。
- ⚠️ **解读边界**：任何「社会结构 / 不平等 / 福祉」的观察，都发生在**一个正在整体死去的世界里** —— 与 v2 总目标（小镇能否自洽运转，T78/T80）**直接相关**。
- **与顺序偏置是两件事**：一个污染「**谁**先被服务」，一个是「**世界本身**在 60 回合后崩掉」。**两者都写，都不该包装成涌现。**

## 8. real-LLM canonical（P2 证据记录）—— 见下方追记
> `provider=openai_compat` · N=20×84 · seed 42 · `exchange.enabled=true` · HEAD `6f7407e`。
> **预期**：life 接受逻辑确定性、不含 LLM → 应与 mock 给出**同样**的 `EXCHANGE_SETTLED=23`（LLM 无关性检验）。
> **结果**：_（运行完成后追记：V2a/V2b/`EXCHANGE_SETTLED`/`distinct_sellers_excl_world`/`agent_agent_share`/`state_hash`/`SYSTEM_ERROR` + 与 mock 的逐项对照）_
