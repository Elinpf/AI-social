# LLM_CALL 目的层审计（静默空输出 / 未真跑 / 疑似截断）

- 日志：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d1_f6on_seed42_n16r84/run.jsonl`
- run.jsonl sha256：`sha256:5c28dd85be67a65d621a09b062e9553ebe7bc006706bba1e5a65d4f3bf61ef11`
- LLM_CALL 总数：3403（无法解析行 0）
- 判据：可疑空输出 = `tokens_out==0 且 cached==false`；未真跑 = `cached==false` 调用数为 0 但有缓存；未出现 = 0 条记录（同样是证据）

| purpose | 调用 | cached=T | cached=F | out(p50) 缓存 / 真调用 | out(max) 缓存 / 真调用 | 可疑空输出(真调用) | thinking | 状态 |
|---|---|---|---|---|---|---|---|---|
| `describe` | 16 | 0 | 16 | None / 374.0 | None / 1469 | 0 | {'True': 16} | 正常 |
| `dialogue` | 714 | 0 | 714 | None / 42.0 | None / 95 | 0 | {'False': 714} | 正常 |
| `importance` | 1747 | 1597 | 150 | 0.0 / 251.5 | 0 / 726 | 0 | {'False': 1747} | 正常 |
| `judge` | 717 | 0 | 717 | None / 197.0 | None / 4699 | 0 | {'True': 717} | 正常 |
| `narrate` | 0 | - | - | - | - | - | - | 未出现，无实例 |
| `negotiation` | 81 | 65 | 16 | 0.0 / 36.5 | 0 / 67 | 0 | {'False': 81} | 正常 |
| `plan` | 16 | 0 | 16 | None / 38.0 | None / 184 | 0 | {'False': 16} | 正常 |
| `reflect` | 112 | 4 | 108 | 0.0 / 56.0 | 0 / 246 | 0 | {'False': 112} | 正常 |

## 成本汇总（tokens_out 占比，降序）

| purpose | tokens_in | tokens_out | out 占比 | 单次最大 out |
|---|---|---|---|---|
| `judge` | 95760 | 243726 | 0.7435 | 4699 |
| `importance` | 2466 | 36179 | 0.110366 | 726 |
| `dialogue` | 297420 | 31615 | 0.096443 | 95 |
| `reflect` | 48935 | 7558 | 0.023056 | 246 |
| `describe` | 2941 | 7276 | 0.022196 | 1469 |
| `plan` | 1447 | 869 | 0.002651 | 184 |
| `negotiation` | 1911 | 586 | 0.001788 | 67 |

合计：in 450880 / out 327809 tokens。

## 发现

- **narrate** / `absent`：{"log_sha8": "5c28dd85", "records": 0, "statement": "在该日志（sha8=5c28dd85）中 0 条记录"}
