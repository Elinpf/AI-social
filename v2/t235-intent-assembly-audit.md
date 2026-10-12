# T235 · `INTENT.*` → 事件 装配点全量排查表

> 作者：kernel-dev ｜ 日期：2026-10-12
> 契约：所有 `INTENT.*` → 事件 的装配**统一走** `KernelAdapter._emit_assembled()` →
> `_assemble(p, base, event)`：base 必需字段优先；既定 additive 字段**透传**；其余非控制键、非合法提示键 → 落 `DROPPED{reason:"unknown_intent_field", keys:[...]}`（**不静默丢**）。

## 装配点清单（`code/orchestration/integration.py`）

| handler | intent | 事件 | base（必需字段） | 透传 `_PASSTHROUGH` | 未知键处理 |
|---|---|---|---|---|---|
| `_do_plan` | `INTENT.PLAN` | `SCHEDULE_PLANNED` | agent_id,horizon,week,slots | — | hints{slots,horizon,week}；余→DROPPED |
| `_do_goal` | `INTENT.GOAL`（每 goal 一条） | `GOAL_SET`（扁平） | goal_id,agent_id,kind,layer,priority,description_ref,target_metric,deadline_week | — | hints{description,description_ref,status,progress}；余→DROPPED |
| `_do_move` | `INTENT.MOVE` | `PLACE_MOVE` | agent_id,from_place,to_place,travel_ticks,day,slot | — | hints{slot_id,activity_type}；余→DROPPED |
| `_do_move` | `INTENT.MOVE` | `PLACE_ARRIVED` | agent_id,place,day,slot | — | hints{slot_id,activity_type,to_place}；余→DROPPED |
| `_do_activity` | `INTENT.ACTIVITY` | `ACTIVITY_STARTED` | activity_id,agent_id,activity_type,place,slot_id,start_tick,participants,day,slot | — | hints{slot_id}；余→DROPPED |
| `_do_memory`(write) | `INTENT.MEMORY` | `MEMORY_WRITE` | mem_id,agent_id,kind,importance,day,slot,subject,body_ref,embed_ref,source_event_seq | — | hints{refs,tick}；余→DROPPED |
| `_do_memory`(retrieve) | `INTENT.MEMORY` | `MEMORY_RETRIEVE` | agent_id,query_id,top_k,selected_mem_ids,scores,weights,tie_order | **vec_available, retrieval_mode, query_digest** | 余→DROPPED |
| `_do_memory`(reflect) | `INTENT.MEMORY` | `MEMORY_REFLECT` | agent_id,triggered_by_mem_ids,importance_sum,produced_mem_id | **produced_mem_ids** | 余→DROPPED |
| `_do_observe` | `INTENT.OBSERVE` | `OBSERVATION` | observer,target_event_seq,salience,day,slot | — | 余→DROPPED |
| `_do_relation` | `INTENT.RELATION` | `RELATION_CHANGE` | from,to,dim,before,after,cause,cause_event_seq | — | 余→DROPPED |
| `_do_econ`(OFFER create) | `INTENT.ECON.OFFER` | `OFFER_CREATED` | offer_id,from,to,kind,terms,round_no | **enforceable** | hints{body}；余→DROPPED |
| `_do_econ`(OFFER counter/accept/reject) | `INTENT.ECON.OFFER` | `OFFER_COUNTERED/ACCEPTED/REJECTED` | offer_id,by,(new_terms\|terms\|reason),round_no | — | hints{terms,act}；余→DROPPED |
| `_do_econ`(CONTRACT_SIGN) | `INTENT.ECON.CONTRACT_SIGN` | `CONTRACT_CREATED` | contract_id,offer_id,parties,terms,kind,round_no | — | 余→DROPPED |
| `_do_econ`(其余 ECON) | `INTENT.ECON.{TRADE,ORDER_PLACE,ORDER_CANCEL,TRANSFER,LOAN_APPLY}` | （无事件，入 `pending_intents`） | — | — | 由 4.1/4.2 消费 |
| `_do_social` | `INTENT.SOCIAL` | `MSG_DM/PUBLIC/GROUP` | msg_id,(from\|author),to/group_id,body,body_ref,refs,tag_hints,place,day,slot[,scope=global] | — | hints{to,group_id,topic}；余→DROPPED |
| `_reject`/`_reject_reason` | 非法 intent | `INTENT_REJECTED` | agent_id,intent_class,reason,requested | — | —（输出事件） |

## 结论
- **所有 `INTENT.* → 事件` 装配点已统一走 `_emit_assembled`**（单一入口，杜绝"各处固定字段 dict"各写各的）。
- **既定 additive 字段透传**：`MEMORY_RETRIEVE`(vec_available/retrieval_mode/query_digest)、`MEMORY_REFLECT`(produced_mem_ids)、`OFFER_CREATED`(enforceable)。
- **未知键一律落 `DROPPED{reason:"unknown_intent_field", keys}`**（可审计、可统计），不再静默消失。
- 合法"intent-only 路由/提示键"登记于 `_HINTS`（非事件字段，明确丢弃、不算丢失）。

## 实测（本次）
- `MEMORY_RETRIEVE`：72/72 条含 `vec_available`（N=3×24；此前 0）。
- `DROPPED{unknown_intent_field}`：**0**（提示键登记后无噪声）。
- 回归：`tests/test_intent_assembly.py`（透传到达事件 + 未知键落 DROPPED）。

## 归属/协同
- `integration.py` 本身：kernel-dev。**注**：本次 sweep 的装配器改动在提交时被并入 life-layer-dev 的 `8d64f30`（T228b）中（当时在飞、被其 `git add` 一并提交）；不影响语义，仅归属说明。
- T228 关闭判据 `event_marked>0` 已满足（freeze `9b0aa46` 复验 60/60）。
