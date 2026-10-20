# LLM_CALL 目的层审计（静默空输出 / 未真跑 / 疑似截断）

- 日志：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d2_before_n16_seed42/run.jsonl`
- run.jsonl sha256：`sha256:c1f86bf61f62b3a0ce8e17e0c2312791cf0262381cd2120c2a63c9b6258963cf`
- LLM_CALL 总数：2905（无法解析行 0）
- 判据：可疑空输出 = `tokens_out==0 且 cached==false`；未真跑 = `cached==false` 调用数为 0 但有缓存；未出现 = 0 条记录（同样是证据）

| purpose | 调用 | cached=T | cached=F | out(p50) 缓存 / 真调用 | out(max) 缓存 / 真调用 | 可疑空输出(真调用) | thinking | 状态 |
|---|---|---|---|---|---|---|---|---|
| `describe` | 16 | 0 | 16 | None / 333.0 | None / 441 | 0 | {'True': 16} | 正常 |
| `dialogue` | 216 | 22 | 194 | 0.0 / 32.0 | 0 / 69 | 0 | {'False': 216} | 正常 |
| `importance` | 1747 | 1597 | 150 | 0.0 / 247.0 | 0 / 1051 | 0 | {'False': 1747} | 正常 |
| `judge` | 717 | 0 | 717 | None / 198.0 | None / 4168 | 0 | {'True': 717} | 正常 |
| `narrate` | 0 | - | - | - | - | - | - | 未出现，无实例 |
| `negotiation` | 81 | 65 | 16 | 0.0 / 34.0 | 0 / 77 | 0 | {'False': 81} | 正常 |
| `plan` | 16 | 0 | 16 | None / 40.0 | None / 168 | 0 | {'False': 16} | 正常 |
| `reflect` | 112 | 14 | 98 | 0.0 / 49.0 | 0 / 204 | 0 | {'False': 112} | 正常 |

## 成本汇总（tokens_out 占比，降序）

| purpose | tokens_in | tokens_out | out 占比 | 单次最大 out |
|---|---|---|---|---|
| `judge` | 95760 | 241528 | 0.812829 | 4168 |
| `importance` | 2466 | 37203 | 0.125202 | 1051 |
| `dialogue` | 22032 | 6489 | 0.021838 | 69 |
| `reflect` | 39854 | 5218 | 0.01756 | 204 |
| `describe` | 2940 | 5173 | 0.017409 | 441 |
| `plan` | 1447 | 939 | 0.00316 | 168 |
| `negotiation` | 1911 | 595 | 0.002002 | 77 |

合计：in 166410 / out 297145 tokens。

## 发现

- **narrate** / `absent`：{"log_sha8": "c1f86bf6", "records": 0, "statement": "在该日志（sha8=c1f86bf6）中 0 条记录"}
