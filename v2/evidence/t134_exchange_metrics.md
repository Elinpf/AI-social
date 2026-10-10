# T134 · 交易指标（excl_world + agent↔agent 占比 + V2a/V2b）

> 口径权威：`v1.1/08-engine-stats-extension.md §1.2 R`（T129 登记）。全 **D 类**、只读日志、纯函数、两次重算**字节相等**、`llm_judged_metric_count==0`。
> 落位：`metrics.econ_loop.exchange`（`obs/metrics_exchange.py`，接入 `obs/metrics_econ_loop.py`）。

## 1. 口径表（写死）

| 指标 | 口径 |
|---|---|
| `distinct_sellers` | `MARKET_TRADE` 卖方身份去重（**含 world**） |
| **`distinct_sellers_excl_world`** | 卖方去重后**排除 world**（`{WORLD,MARKET,BANK,SYSTEM,TAX_POOL}`）→ **G-P1-1 真判据** |
| `distinct_buyers_excl_world` | 买方对称口径 |
| `agent_agent_deals` | `|MARKET_TRADE: buyer&seller 均∈Agents| + |EXCHANGE_SETTLED: parties 双方均∈Agents|` |
| `all_deals` | `|MARKET_TRADE| + |EXCHANGE_SETTLED|` |
| `agent_agent_share` | `agent_agent_deals / all_deals`（分母 0→0.0），`round(...,6)` |
| `V2a_tool_available` | `(OFFER_CREATED>0 ∨ MARKET_TRADE>0 ∨ EXCHANGE_SETTLED>0) ∧ OFFER_ACCEPTED>0`（**工具可用**；intent 不落日志，用事件侧代理） |
| `V2b_ai_trades` | `distinct_sellers_excl_world > 1`（**AI 真交易**，涌现性） |

- 对手方判定：优先一等字段 `counterparty`（A1，08 §1.2 R），否则回退 `seller`/`buyer` 主体 id；agent = `AGENT_BORN` 出现过的 id。
- **V2a 与 V2b 必须分列** —— 避免「AI 选择不交易」被误读为「原语坏了」。

## 2. 在现有日志上跑通（新事件为 0 → 如实报 0）

`run_p1_final_n20_llm.jsonl`（128,564 事件）：
```json
{"n_market_trade":23,"n_exchange_settled":0,"distinct_sellers":1,"distinct_sellers_excl_world":0,
 "distinct_buyers":4,"distinct_buyers_excl_world":4,"agent_agent_deals":0,"all_deals":23,
 "agent_agent_share":0.0,"V2a_tool_available":false,"V2b_ai_trades":false,
 "V2a_components":{"offer_created":21,"offer_accepted":0,"market_trade":23,"exchange_settled":0},
 "llm_judged_metric_count":0}
```
**如实结论**：`distinct_sellers_excl_world=0`、`agent_agent_share=0.0`、`V2b=false`（卖方仅 world `MARKET`）——**G-P1-1 缺口被"可测量"**。`V2a=false` 因本 run `OFFER_ACCEPTED=0`（工具侧仅有 `OFFER_CREATED`）→ **区分「工具可用」与「AI 真交易」**的意义即在此。
> T131 落地 `EXCHANGE_SETTLED`/agent-as-seller 后，在真日志复算即应非零。

## 3. 复算命令

```bash
cd code
python -c "import json;from obs.metrics_econ_loop import econ_loop_metrics;print(econ_loop_metrics([json.loads(l) for l in open('../v2/evidence/run_p1_final_n20_llm.jsonl')])['exchange'])"
# 或全套
python -m obs metrics --log ../v2/evidence/run_p1_final_n20_llm.jsonl --out ../v2/evidence/metrics_full.json  # metrics.econ_loop.exchange
```

## 4. 验收

- 两次重算**字节相等**（`obs gate.metrics_bitwise_equal` PASS）；`llm_judged_metric_count=0`；F 类单列（本项无 F）。
- `obs gate G1–G7` **PASS**；`pytest -q`（**从 `code/` 跑**）**299 passed**；`lint-imports` **8 kept/0 broken**。
- 在现有日志上如实报 **0**（未造假）。
