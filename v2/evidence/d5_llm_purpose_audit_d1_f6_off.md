# LLM_CALL 目的层审计（静默空输出 / 未真跑 / 疑似截断）

- 日志：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d1_f6off_seed42_n16r84/run.jsonl`
- run.jsonl sha256：`sha256:dbff7b97b2820429b3378da0517283e1c34af246221286e666c9e28223977e64`
- LLM_CALL 总数：3403（无法解析行 0）
- 判据：可疑空输出 = `tokens_out==0 且 cached==false`；未真跑 = `cached==false` 调用数为 0 但有缓存；未出现 = 0 条记录（同样是证据）

| purpose | 调用 | cached=T | cached=F | out(p50) 缓存 / 真调用 | out(max) 缓存 / 真调用 | 可疑空输出(真调用) | thinking | 状态 |
|---|---|---|---|---|---|---|---|---|
| `describe` | 16 | 0 | 16 | None / 333.5 | None / 764 | 0 | {'True': 16} | 正常 |
| `dialogue` | 714 | 0 | 714 | None / 37.0 | None / 124 | 0 | {'False': 714} | 正常 |
| `importance` | 1747 | 1597 | 150 | 0.0 / 248.5 | 0 / 708 | 0 | {'False': 1747} | 正常 |
| `judge` | 717 | 0 | 717 | None / 196.0 | None / 3446 | 0 | {'True': 717} | 正常 |
| `narrate` | 0 | - | - | - | - | - | - | 未出现，无实例 |
| `negotiation` | 81 | 65 | 16 | 0.0 / 34.0 | 0 / 63 | 0 | {'False': 81} | 正常 |
| `plan` | 16 | 0 | 16 | None / 37.0 | None / 157 | 0 | {'False': 16} | 正常 |
| `reflect` | 112 | 4 | 108 | 0.0 / 60.0 | 0 / 249 | 0 | {'False': 112} | 正常 |

## 成本汇总（tokens_out 占比，降序）

| purpose | tokens_in | tokens_out | out 占比 | 单次最大 out |
|---|---|---|---|---|
| `judge` | 95760 | 233498 | 0.747773 | 3446 |
| `importance` | 2466 | 36494 | 0.116871 | 708 |
| `dialogue` | 216738 | 27873 | 0.089263 | 124 |
| `reflect` | 48672 | 7211 | 0.023093 | 249 |
| `describe` | 2937 | 5794 | 0.018555 | 764 |
| `plan` | 1447 | 787 | 0.00252 | 157 |
| `negotiation` | 1911 | 601 | 0.001925 | 63 |

合计：in 369931 / out 312258 tokens。

## 发现

- **narrate** / `absent`：{"log_sha8": "dbff7b97", "records": 0, "statement": "在该日志（sha8=dbff7b97）中 0 条记录"}
