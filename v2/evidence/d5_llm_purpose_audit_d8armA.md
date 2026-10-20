# LLM_CALL 目的层审计（静默空输出 / 未真跑 / 疑似截断）

- 日志：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d8_armA_n4r60_seed42/run.jsonl`
- run.jsonl sha256：`sha256:a17ffcfab1d0a26b38b40978cb9bdfe7bccab4e09ff70bd7bfae4cbd7c2ed1c0`
- LLM_CALL 总数：272（无法解析行 0）
- 判据：可疑空输出 = `tokens_out==0 且 cached==false`；未真跑 = `cached==false` 调用数为 0 但有缓存；未出现 = 0 条记录（同样是证据）

| purpose | 调用 | cached=T | cached=F | out(p50) 缓存 / 真调用 | out(max) 缓存 / 真调用 | 可疑空输出(真调用) | thinking | 状态 |
|---|---|---|---|---|---|---|---|---|
| `describe` | 0 | - | - | - | - | - | - | 未出现，无实例 |
| `dialogue` | 124 | 10 | 114 | 0.0 / 25.0 | 0 / 84 | 0 | {'False': 124} | 正常 |
| `importance` | 34 | 24 | 10 | 0.0 / 258.0 | 0 / 804 | 0 | {'False': 34} | 正常 |
| `judge` | 74 | 0 | 74 | None / 201.0 | None / 2504 | 0 | {'True': 74} | 正常 |
| `narrate` | 0 | - | - | - | - | - | - | 未出现，无实例 |
| `negotiation` | 13 | 9 | 4 | 0.0 / 18.0 | 0 / 57 | 0 | {'False': 13} | 正常 |
| `plan` | 4 | 0 | 4 | None / 32.0 | None / 87 | 0 | {'False': 4} | 正常 |
| `reflect` | 23 | 0 | 23 | None / 27.0 | None / 104 | 0 | {'False': 23} | 正常 |

## 成本汇总（tokens_out 占比，降序）

| purpose | tokens_in | tokens_out | out 占比 | 单次最大 out |
|---|---|---|---|---|
| `judge` | 9652 | 25437 | 0.75755 | 2504 |
| `dialogue` | 17004 | 3640 | 0.108404 | 84 |
| `importance` | 170 | 3356 | 0.099946 | 804 |
| `reflect` | 9501 | 868 | 0.02585 | 104 |
| `plan` | 357 | 169 | 0.005033 | 87 |
| `negotiation` | 473 | 108 | 0.003216 | 57 |

合计：in 37157 / out 33578 tokens。

## 发现

- **describe** / `absent`：{"log_sha8": "a17ffcfa", "records": 0, "statement": "在该日志（sha8=a17ffcfa）中 0 条记录"}
- **narrate** / `absent`：{"log_sha8": "a17ffcfa", "records": 0, "statement": "在该日志（sha8=a17ffcfa）中 0 条记录"}
