# 对话质量客观指标读数（D5 复算器自动生成）

- 输入日志: `v2/evidence/run_f3_on_n16r60_seed42/run.jsonl`
- run.jsonl sha256: `sha256:087072f84518eb009fb8d0a6ec445c5515b7561c1f031430702a5187394af16c`
- 脚本 sha256: `sha256:ac1a3886cc2d65588b0a030a168f93e2cfa25b82fd6dadd6ceb72e58a11751aa`
- 口径版本: `d5-metrics/1.0` / thread_schema=`explicit`
- 准入结论: **ADMITTED** / evidence_level=`evidence`

消息数 502，线程数 170，channel={'public': 53, 'dm': 449}

### S-1 线程结构（per-thread；**轮数请用 S-1C**）

| 指标 | 值 |
|---|---|
| `S-1C 轮数(turn_index 去重) p50/p90/max` | 2.0 / 6.0 / 6.0 |
| `S-1A 说话人交替段数 p50/p90/max` | 2.0 / 6.0 / 6.0 |
| `S-1B 往复对数(指针) p50/max` | 1.0 / 5.0 |

### S-2 线程规模（per-thread）

| 指标 | 值 |
|---|---|
| `msgs_per_thread p50/p90/max` | 2.0 / 6.0 / 6.0 |
| `single_msg_thread_ratio` | 0.476471 |
| `single_speaker_thread_ratio` | 0.476471 |
| `multi_turn_thread_ratio (turns_A>=3)` | 0.435294 |

### S-3 最长链（per-thread）

| 指标 | 值 |
|---|---|
| `chain_by_alternation p50/max` | 2.0 / 6.0 |
| `chain_by_pointer max` | 6.0 |

### S-4 回复指针完整率（per-message，条件分母）

| 指标 | 值 |
|---|---|
| `rate` | 1.0 |
| `denominator_nonfirst_msgs` | 332 |
| `ptr_ok` | 332 |
| `ptr_empty` | 0 |
| `ptr_cross_thread` | 0 |
| `ptr_forward` | 0 |
| `ptr_dangling` | 0 |

### K-1b 话题承接·宽口径（day+channel 相邻，分母更大）

| 指标 | 值 |
|---|---|
| `cont_backref` | 0.323171 |
| `cont_lexical` | 0.254065 |
| `tag_overlap_rate_reference` | 0.335366 |
| `denominator_adjacent_pairs` | 492 |

### K-1c 话题承接·对端口径（day+channel+对端；与 S-1/S-2 legacy 线程一致）

| 指标 | 值 |
|---|---|
| `cont_backref` | 0.337731 |
| `cont_lexical` | 0.453826 |
| `denominator_adjacent_pairs` | 379 |

### K-1 话题承接·主口径 mixed（dm 按对、public 按日、group 按组；三列独立，不出合成数）

| 指标 | 值 |
|---|---|
| `cont_same_topic` | 1.0 |
| `cont_backref` | 0.346386 |
| `cont_lexical` | 0.415663 |
| `tag_overlap_rate_reference` | 1.0 |
| `denominator_adjacent_pairs` | 332 |

### L 措辞层（per-message）

| 指标 | 值 |
|---|---|
| `L-1_len.p50 / p90` | 27.0 / 44.0 |
| `L-1_len_excl_paren.p50` | 27.0 |
| `L-2_narration_rate_proxy` | 0.0 |
| `L-3_paren_block_any` | 0.0 |
| `L-4_third_person_self_rate` | 0.0 |
| `L-5_template_hit_rate` | 0.015936 |
| `L-6_dup_exact_rate` | 0.091633 |
| `L-7_dup_ngram8_rate` | 0.444223 |
| `L-8_agent_id_leak_rate（分母=全MSG n=502）` | 0.0 |
| `L-9_meta_talk_rate` | 0.0 |
| `L-10_self_address_error_rate` | 0.0 |
| `L-11_second_person_rate（分母=dm+group n=449）` | 0.768374 |
| `L-12a 对端提及率（分母=dm+group n=449）` | 0.563474 |
| `L-12b 对端称呼率（分母=dm+group n=449，判定用）` | 0.512249 |
| `L-8b_paren_only_id_rate（分母=全MSG n=502；仅旁白内ID）` | 0.0 |
| `L-8c_body_leak_rate（分母=全MSG n=502；台词本体ID）` | 0.0 |

### F 生活气息（proxy，per-message / per-adjacent-pair）

| 指标 | 值 |
|---|---|
| `F-1 非功能性闲聊占比` | 0.703187 |
| `F-2 话题漂移率` | 0.0 |
| `F-2b 多话题线程占比` | 0.0 |
| `F-3 情绪呼应率` | 0.192308 |
| `F-3 分母` | 26 |
| `F-4 修复闭环率` | 0.043478 |
| `F-4 张力事件数` | 23 |
| `F-5 习惯强度` | 1.0 |
| `F-6 跨天记忆引用率` | 0.021912 |
| `F-7a 越界提及率` | 0.123506 |

### E 效率层

| 指标 | 值 |
|---|---|
| `E-1_msg_per_agent_round` | 0.570455 |
| `E-2_tokens_out_per_message` | 21.719124 |
| `dialogue_calls` | 502 |
| `degraded_ratio` | 0.0 |

### 准入检查明细

| 编号 | 通过 | 细节 |
|---|---|---|
| B-7_files | ✅ | "meta.json 存在" |
| B-8_parse | ✅ | [] |
| B-9_event_count | ✅ | {"meta.events": 115494, "actual_lines": 115494} |
| B-10_provider | ✅ | "openai_compat" |
| B-11_real_calls | ✅ | {"dialogue_calls": 502} |
| B-12_degraded_ratio | ✅ | {"ratio": 0.0, "degraded": 0, "calls": 2869} |
| B-13_event_families | ✅ | {"missing": []} |
| B-15_msg_volume | ✅ | {"msg_dm": 449, "messages": 502, "dm_threads": 95, "floor": "MSG>=150 且 MSG_DM>=100 且 DM 会话线>=12（v1.2）"} |
| B-2b_manifest_effective | ✅ | {"rounds_effective": 60, "rounds_per_slot_effective": 3, "note": ""} |
| B-15_msg_fields | ✅ | {"empty_body": [], "required_keys": ["from", "to", "body", "msg_id", "day", "slot", "place", "tag_hints"]} |
| B-16_round_dense | ✅ | {"min": 0, "max": 59, "n": 60} |
| B-17_hash_chain | ✅ | {"seq_dense": true, "hash_links_ok": true, "n": 115494} |
| B-19_provider_distribution | ✅ | {"providers": {"openai_compat": 2869}, "rule": "全部 LLM_CALL.provider 必须为 openai_compat"} |
| B-20_model_no_mock | ✅ | {"models": ["DeepSeek-Flash"], "rule": "model 去重集合不得含 mock"} |
| B-21_body_not_template | ✅ | {"L-5_template_hit_rate": 0.015936, "L-6_dup_exact_rate": 0.091633, "rule": "模板命中率<50% 且 完全重复率<50%；另需人工抽样双查"} |

