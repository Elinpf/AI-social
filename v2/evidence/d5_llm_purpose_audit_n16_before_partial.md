# LLM_CALL 目的层审计（静默空输出 / 未真跑 / 疑似截断）

- 日志：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d2_before_n16_seed42/run.jsonl`
- run.jsonl sha256：`sha256:a9a6478cae96f7b10fcc34ebf7cbef3e91f092a7baae22d226edfe3760e8041b`
- LLM_CALL 总数：2101（无法解析行 0）
- 判据：可疑空输出 = `tokens_out==0 且 cached==false`；未真跑 = `cached==false` 调用数为 0 但有缓存；未出现 = 0 条记录（同样是证据）

| purpose | 调用 | cached=T | cached=F | out(p50) 缓存 / 真调用 | out(max) 缓存 / 真调用 | 可疑空输出(真调用) | thinking | 状态 |
|---|---|---|---|---|---|---|---|---|
| `describe` | 0 | - | - | - | - | - | - | 未出现，无实例 |
| `dialogue` | 63 | 2 | 61 | 0.0 / 30.0 | 0 / 67 | 0 | {'False': 63} | 正常 |
| `importance` | 1523 | 1387 | 136 | 0.0 / 269.0 | 0 / 1051 | 0 | {'False': 1523} | 正常 |
| `judge` | 420 | 0 | 420 | None / 183.0 | None / 3380 | 0 | {'True': 420} | 正常 |
| `narrate` | 0 | - | - | - | - | - | - | 未出现，无实例 |
| `negotiation` | 7 | 0 | 7 | None / 38.0 | None / 77 | 0 | {'False': 7} | 正常 |
| `plan` | 16 | 0 | 16 | None / 40.0 | None / 168 | 0 | {'False': 16} | 正常 |
| `reflect` | 72 | 0 | 72 | None / 46.5 | None / 204 | 0 | {'False': 72} | 正常 |

## 成本汇总（tokens_out 占比，降序）

| purpose | tokens_in | tokens_out | out 占比 | 单次最大 out |
|---|---|---|---|---|
| `judge` | 50982 | 85567 | 0.661505 | 3380 |
| `importance` | 2312 | 36848 | 0.284866 | 1051 |
| `reflect` | 29798 | 3773 | 0.029168 | 204 |
| `dialogue` | 6820 | 1953 | 0.015098 | 67 |
| `plan` | 1447 | 939 | 0.007259 | 168 |
| `negotiation` | 839 | 272 | 0.002103 | 77 |

合计：in 92198 / out 129352 tokens。

## 发现

- **describe** / `absent`：{"log_sha8": "a9a6478c", "records": 0, "statement": "在该日志（sha8=a9a6478c）中 0 条记录"}
- **narrate** / `absent`：{"log_sha8": "a9a6478c", "records": 0, "statement": "在该日志（sha8=a9a6478c）中 0 条记录"}
