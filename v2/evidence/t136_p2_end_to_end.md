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
| `distinct_buyers_excl_world` | 5 | 5 | 5 |
| `distinct_counterparty_excl_world` | 4 | 3 | 0 |
| `agent_agent_share` | 0.641026 | 0.522727 | 0.0 |
| `state_hash` | `135a6289…` | `814691d9…` | `8d8d1c3d…` |

> probe N=10 的 `25 / 120 / 69` 与 Leader 的 T133 基线**逐项一致**（基线 seed7、本 run seed42 —— 聚合口径与种子无关）。

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

## 4. 涌现结构观察（**观察，非指标**；非设计）
canonical N=20：**卖方仅 3 个**（`P001/P002/P003`，持有 `material` 者），**买方 5 个** —— **P004、P006 只买不卖（纯消费者）**。
→ 可交易物**集中在少数人手里**，这**决定了谁成为卖方**：这是涌现出的**经济角色分化**，**不是我们设计的**；也说明 `> 1` 判据确由真实异质行为触发。**写成观察，勿包装成指标。**

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
