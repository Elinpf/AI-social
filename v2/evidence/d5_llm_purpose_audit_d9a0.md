# LLM_CALL 目的层审计（静默空输出 / 未真跑 / 疑似截断）

- 日志：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d2_after_n16_seed42/run.jsonl`
- run.jsonl sha256：`sha256:643f13a528c288d3e9677cb8ac100139224afbd0b46c0f7da0c3a5ed85b13141`
- LLM_CALL 总数：3403（无法解析行 0）
- 判据：可疑空输出 = `tokens_out==0 且 cached==false`；未真跑 = `cached==false` 调用数为 0 但有缓存；未出现 = 0 条记录（同样是证据）

| purpose | 调用 | cached=T | cached=F | out(p50) 缓存 / 真调用 | out(max) 缓存 / 真调用 | 可疑空输出(真调用) | thinking | 状态 |
|---|---|---|---|---|---|---|---|---|
| `describe` | 16 | 0 | 16 | None / 342.5 | None / 1962 | 0 | {'True': 16} | 正常 |
| `dialogue` | 714 | 68 | 646 | 0.0 / 41.0 | 0 / 154 | 0 | {'False': 714} | 正常 |
| `importance` | 1747 | 1597 | 150 | 0.0 / 239.0 | 0 / 795 | 0 | {'False': 1747} | 正常 |
| `judge` | 717 | 0 | 717 | None / 198.0 | None / 5857 | 0 | {'True': 717} | 正常 |
| `narrate` | 0 | - | - | - | - | - | - | 未出现，无实例 |
| `negotiation` | 81 | 65 | 16 | 0.0 / 33.0 | 0 / 67 | 0 | {'False': 81} | 正常 |
| `plan` | 16 | 0 | 16 | None / 43.0 | None / 174 | 0 | {'False': 16} | 正常 |
| `reflect` | 112 | 4 | 108 | 0.0 / 50.5 | 0 / 216 | 0 | {'False': 112} | 正常 |

## 成本汇总（tokens_out 占比，降序）

| purpose | tokens_in | tokens_out | out 占比 | 单次最大 out |
|---|---|---|---|---|
| `judge` | 95760 | 252020 | 0.758124 | 5857 |
| `importance` | 2466 | 34673 | 0.104303 | 795 |
| `dialogue` | 112950 | 29384 | 0.088393 | 154 |
| `describe` | 2936 | 8431 | 0.025362 | 1962 |
| `reflect` | 48109 | 6314 | 0.018994 | 216 |
| `plan` | 1447 | 1006 | 0.003026 | 174 |
| `negotiation` | 1911 | 598 | 0.001799 | 67 |

合计：in 265579 / out 332426 tokens。

## 发现

- **narrate** / `absent`：{"log_sha8": "643f13a5", "records": 0, "statement": "在该日志（sha8=643f13a5）中 0 条记录"}
