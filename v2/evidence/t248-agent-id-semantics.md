# T248 · `agent_id` 可含非 Agent 主体（MARKET）—— obs 聚合侧止血 + 口径 + 同型清单

> **性质**：`agent_id` 字段名**暗示「一个 Agent」**，实际可含非 Agent 主体（`MARKET`）。
> 与 `actor`（T241 已修）**同族、但裂在另一个字段上**。**不是潜伏，是正在污染**。
> **处置口径（leader 裁）**：**先止血 + 立口径，不改生产侧**（世界市场确是主体；改名要动事件语义/08）。

## 0. 结论
1. **止血已落**：obs 聚合侧复用 `contracts/actors`（T241 单一真源），**非 Agent 主体不得进"居民"级聚合**。改了两处：`obs/life.py::need_metrics`、`obs/census.py` E7。
2. **泄漏量（实测，前后对照）**：每份 canonical 日志有 **`NEED_UPDATE{agent_id=MARKET}=89` + `STATE_CHANGE{agent_id=MARKET}=1` = 90 条**非 Agent 行。**修前它真的改了指标**（见 §2）。
3. **同型清单**（§4）：`actor`✅T241 · `agent_id`←本项 · 另有 **6 个字段名暗示 Agent、实际可含非 Agent**（多为 world 哨兵）。

## 1. 改动（只 obs 侧，复用单一真源）
- `obs/life.py::need_metrics`：`agent_id` 非 Agent（`not is_agent_actor(aid)`）→ **跳过**；新增字段 `n_need_updates_non_agent_excluded` 报泄漏计数；`n_need_updates` 改为**仅居民**。
- `obs/census.py` E7（`NEED_UPDATE` burnout + `STATE_CHANGE` exhausted）：`agent_id` 非 Agent → **跳过**（不再给 MARKET 造 E7）。
- **未动生产侧**（`life/settlement.py` 仍写 `agent_id=MARKET`）——按裁决，等 08/口径定后再谈改名。
- 守卫**复用** `from contracts.actors import is_agent_actor`，**不另写白名单**。

## 2. 泄漏量：前后对照（实测，命令见 §5）
日志 `v2/evidence/run_t136_real_llm_canon_n20.jsonl`，`need_metrics` 各维 mean/min/max：
| dim | 旧 mean | **新 mean** | 旧 min | **新 min** | 旧 max | 新 max |
|---|---:|---:|---:|---:|---:|---:|
| energy | 19.571429 | **20.55** | 0.0 | 0.0 | 58.0 | 58.0 |
| esteem | 21.190476 | **22.25** | 0.0 | 0.0 | 34.0 | 34.0 |
| leisure | 1.142857 | **1.2** | 0.0 | 0.0 | 4.0 | 4.0 |
| mastery | 52.047619 | **53.4** | 25.0 | **29.0** | 76.0 | 76.0 |
| social | 0.285714 | **0.3** | 0.0 | 0.0 | 2.0 | 2.0 |
| satiety | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

- **`n_need_updates`：3399 → 3310（排除 89）**；`n_need_updates_non_agent_excluded = 89`。
- **事实**：MARKET 的 needs（每维取"最后一笔"）**曾把每维 mean 往上抬**（如 energy 19.57→20.55）、并把 `mastery` 的 **min 从 25 抬到 29**。→ **确认污染真实存在、且改变了"居民"级统计。**

## 3. 双向反向验证（命令 + 预期，见 §5 与测试）
| 方向 | 断言 | 结果 |
|---|---|---|
| **非 Agent 不进** | `NEED_UPDATE{agent_id=MARKET}` → 该 dim 只反映真 Agent | ✅ `test_need_metrics_excludes_non_agent_keeps_agent` |
| **真 Agent 照进** | 两个真 Agent 的 need 正常进 mean | ✅ `test_need_metrics_all_agents_pass` |
| **census E7 排除** | `STATE_CHANGE{agent_id=MARKET}` 不造 E7；真 Agent 造 | ✅ `test_census_e7_excludes_non_agent_state_change` / `_market_only_is_no_hit` |

## 4. 同型清单（**字段名暗示 Agent、实际可含非 Agent**，一行一条）
| # | 字段 | 可含非 Agent | 现状 | 证据/位置 |
|---|---|---|---|---|
| 1 | `actor` | `SYSTEM/OBSERVER/DIRECTOR/WORLD/MARKET/BANK/TAX_POOL` | ✅ **已修**（T241 单一真源 `contracts.actors`） | `contracts/actors.py` |
| 2 | **`agent_id`** | `MARKET`（+可能 SYSTEM…） | ✅ **本项 obs 侧止血**（生产侧待裁） | `obs/life.py`、`obs/census.py` |
| 3 | `seller` / `buyer` / `counterparty`（`MARKET_TRADE`/`EXCHANGE_SETTLED`） | `WORLD/MARKET/…` | ⚠️ **仅 `obs/metrics_exchange` 有 `WORLD_IDS` 排除**；其他消费方【未验证】 | `obs/metrics_exchange.py:27` |
| 4 | `from` / `to`（`TRANSFER`/`RELATION_CHANGE`/`EXCHANGE` 腿） | `BANK/SYSTEM/TAX_POOL` | ⚠️ **部分**：`census.py:138` 对 `TRANSFER.to∈{BANK,SYSTEM}` 有守卫；其余【未验证】 | `obs/census.py:138` |
| 5 | `payer` / `payee`（契约付款） | `SYSTEM/TAX_POOL` | ⚠️【未验证】 | `obs/wellbeing._payer/_recipient` 等 |
| 6 | `parties`（`EXCHANGE_SETTLED`） | 一般 agent；world? | ⚠️ 消费方多用 `is_agent` 判定【部分】 | `obs/metrics_exchange`、`obs/truth*.py` |
| 7 | `owner_id`（记忆/反诈） | ? | ⚠️【未验证】 | `obs/antifraud.py` |

→ **建议**：3–7 若要收口，**统一走 `contracts.actors` 守卫**（当字段也允许 world 时，guard 需扩展"world 哨兵"语义）。
> ⚠️ **顺带发现一处"同物两处定义"**（非本任务，供 leader 裁决）：存在**两个**「确定性后果真值」模块 —— `obs/truth.py`（`264c07f`）与 `obs/truth_from_consequences.py`（`969335f`）。**建议合并为一**，否则又是"同名不同义"。

## 5. 复现命令
```bash
cd code
# 双向反向验证（含非 Agent/真 Agent 两向）
python -m pytest -q tests/test_obs_agent_id_semantics.py tests/test_obs_life_actor.py

# 泄漏量实测
python -c "import json,collections;from contracts.actors import is_agent_actor;\
recs=[json.loads(l) for l in open('../v2/evidence/run_t136_real_llm_canon_n20.jsonl')];\
c=collections.Counter((r['type'],(r.get('payload') or {}).get('agent_id')) for r in recs \
 if r['type'] in ('NEED_UPDATE','STATE_CHANGE') and not is_agent_actor((r.get('payload') or {}).get('agent_id')));print(c)"

# 前后对照
python -c "import json;from obs.life import need_metrics;\
recs=[json.loads(l) for l in open('../v2/evidence/run_t136_real_llm_canon_n20.jsonl')];\
print(need_metrics(recs)['n_need_updates'], need_metrics(recs)['n_need_updates_non_agent_excluded'])"
```

## 6. 口径归属（需 sim-engine-stats-architect 确认）
「`agent_id` 可含非 Agent 主体」→ 二选一（**都不做不允许**）：**①改名**（动语义/08，代价大）或 **②登记为已知例外**（在 08/术语表写明 `agent_id` 可为 world 哨兵）。**本任务只做 obs 止血；归属待其确认**（已直连同步）。

## 7. 【未验证】
- 生产侧（`life/settlement.py`）为何/是否应把世界市场写成 `agent_id`（语义问题）→ **待 leader/08 裁**。
- 同型清单 3–7 的**全部**消费方是否已守卫 → **未验证**（本报告只标已知守卫点）。
- `need_metrics` 排除后对**下游福祉/涌现指标**的连锁影响 → 未逐项核（`wellbeing` 经 `need_metrics` 取 dims，已随之干净）。
