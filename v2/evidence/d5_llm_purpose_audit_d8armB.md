# LLM_CALL 目的层审计（静默空输出 / 未真跑 / 疑似截断）

- 日志：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d8_armB_n4r60_seed42/run.jsonl`
- run.jsonl sha256：`sha256:3966309f218b960ea5c84d6732cb1f872d7abfa170715a59c70b708ba041debd`
- LLM_CALL 总数：274（无法解析行 0）
- 判据：可疑空输出 = `tokens_out==0 且 cached==false`；未真跑 = `cached==false` 调用数为 0 但有缓存；未出现 = 0 条记录（同样是证据）

| purpose | 调用 | cached=T | cached=F | out(p50) 缓存 / 真调用 | out(max) 缓存 / 真调用 | 可疑空输出(真调用) | thinking | 状态 |
|---|---|---|---|---|---|---|---|---|
| `describe` | 0 | - | - | - | - | - | - | 未出现，无实例 |
| `dialogue` | 124 | 6 | 118 | 0.0 / 26.5 | 0 / 97 | 0 | {'False': 124} | 正常 |
| `importance` | 34 | 24 | 10 | 0.0 / 285.0 | 0 / 560 | 0 | {'False': 34} | 正常 |
| `judge` | 74 | 0 | 74 | None / 204.5 | None / 1939 | 0 | {'True': 74} | 正常 |
| `narrate` | 0 | - | - | - | - | - | - | 未出现，无实例 |
| `negotiation` | 13 | 9 | 4 | 0.0 / 17.5 | 0 / 50 | 0 | {'False': 13} | 正常 |
| `plan` | 4 | 0 | 4 | None / 34.5 | None / 153 | 0 | {'False': 4} | 正常 |
| `reflect` | 25 | 0 | 25 | None / 27.0 | None / 95 | 0 | {'False': 25} | 正常 |

## 成本汇总（tokens_out 占比，降序）

| purpose | tokens_in | tokens_out | out 占比 | 单次最大 out |
|---|---|---|---|---|
| `judge` | 9652 | 24139 | 0.752087 | 1939 |
| `dialogue` | 17951 | 3888 | 0.121137 | 97 |
| `importance` | 170 | 2849 | 0.088765 | 560 |
| `reflect` | 10467 | 880 | 0.027418 | 95 |
| `plan` | 357 | 240 | 0.007478 | 153 |
| `negotiation` | 473 | 100 | 0.003116 | 50 |

合计：in 39070 / out 32096 tokens。

## 发现

- **describe** / `absent`：{"log_sha8": "3966309f", "records": 0, "statement": "在该日志（sha8=3966309f）中 0 条记录"}
- **narrate** / `absent`：{"log_sha8": "3966309f", "records": 0, "statement": "在该日志（sha8=3966309f）中 0 条记录"}
