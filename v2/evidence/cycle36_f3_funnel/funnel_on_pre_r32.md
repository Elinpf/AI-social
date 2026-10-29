# F-3 采纳漏斗读数（`tools/metrics/f3_funnel.py`）

- log: `v2/evidence/cycle34_f3_on_n16r84_seed42/run.jsonl`（sha256 `b6cacdaf975a178c…`，193933 行）
- 复算脚本 sha256: `6a92f99bcfd7e591…`；`emotion_echo.py` sha256: `8248470b2519a200…`

| 级 | 名称 | 数量 | 说明 |
|---|---|---|---|
| S0 | MSG_* 事件 | 686 | 全量消息 |
| S0 | 其中 reply 事件 | 480 | `reply_to != null` |
| S1 | 宽口径机会集 | 438 | 父消息可解析 ∧ (父 mood∉{平和} ∨ 父正文极性≠0) |
| S2 | plan() 候选 | 107 | 证据门控 + 强度阈值后仍产出 |
| S3 | 进入决策（prompted） | 107 | echo_line 真的拼进 `_reply_prompt` |
| S4 | 采纳（原口径 first-clause） | 7 | has_ref ∧ has_cue ∧ ¬ack_then_switch |
| S4 | 采纳（内容分句口径） | 7 | 跳过单独的应声/称呼后再判 |

- 候选/回复 = 0.222917；原口径采纳率 = 0.065421；内容分句口径采纳率 = 0.065421

## S1→S2 丢弃原因

| 原因 | 条数 |
|---|---|
| gated_mood_only | 339 |
| no_emotion_signal | 34 |

## S4 丢弃原因（内容分句口径）

| 原因 | 条数 |
|---|---|
| ack_then_switch_no_cue | 66 |
| no_cue | 34 |

## 第一段形态（诊断：线索词落在第几段）

| 指标 | 条数 |
|---|---|
| cue_in_segment_0 | 7 |
| cue_in_segment_1 | 44 |
| cue_in_segment_2plus | 38 |
| cue_nowhere | 18 |
| raw_first_is_ack_only | 62 |
| raw_first_is_name_only | 30 |
