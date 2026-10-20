# 对话质量客观指标读数（D5 复算器自动生成）

- 输入日志: `v2/evidence/d5_synth_schema_test/run.jsonl`
- run.jsonl sha256: `sha256:41649e2b2c48d6af2b86a5aae8fa031e9272d2b1401681858c5ec76fb2287ab6`
- 脚本 sha256: `sha256:34b23a3d934e41de6427e30abcfaf69fb6c16d6c783996bd03221ec7ecaca761`
- 口径版本: `d5-metrics/1.0` / thread_schema=`explicit`
- 准入结论: **REJECTED** / evidence_level=`probe`

消息数 4，线程数 1，channel={'dm': 4}

### S-1 线程轮次（per-thread）

| 指标 | 值 |
|---|---|
| `A_speaker_turns.p50` | 4.0 |
| `A_speaker_turns.p90/max` | 4.0 / 4.0 |
| `B_roundtrips.p50` | 3.0 |
| `B_roundtrips.max` | 3.0 |

### S-2 线程规模（per-thread）

| 指标 | 值 |
|---|---|
| `msgs_per_thread p50/p90/max` | 4.0 / 4.0 / 4.0 |
| `single_msg_thread_ratio` | 0.0 |
| `single_speaker_thread_ratio` | 0.0 |
| `multi_turn_thread_ratio (turns_A>=3)` | 1.0 |

### S-3 最长链（per-thread）

| 指标 | 值 |
|---|---|
| `chain_by_alternation p50/max` | 4.0 / 4.0 |
| `chain_by_pointer max` | 4.0 |

### S-4 回复指针完整率（per-message，条件分母）

| 指标 | 值 |
|---|---|
| `rate` | 1.0 |
| `denominator_nonfirst_msgs` | 3 |
| `ptr_ok` | 3 |
| `ptr_empty` | 0 |
| `ptr_cross_thread` | 0 |
| `ptr_forward` | 0 |
| `ptr_dangling` | 0 |

### K-1b 话题承接·宽口径（day+channel 相邻，分母更大）

| 指标 | 值 |
|---|---|
| `cont_backref` | 1.0 |
| `cont_lexical` | 0.0 |
| `tag_overlap_rate_reference` | 0.666667 |
| `denominator_adjacent_pairs` | 3 |

### K-1c 话题承接·对端口径（day+channel+对端；与 S-1/S-2 legacy 线程一致）

| 指标 | 值 |
|---|---|
| `cont_backref` | 1.0 |
| `cont_lexical` | 0.0 |
| `denominator_adjacent_pairs` | 3 |

### K-1 话题承接·主口径 mixed（dm 按对、public 按日、group 按组；三列独立，不出合成数）

| 指标 | 值 |
|---|---|
| `cont_same_topic` | 0.666667 |
| `cont_backref` | 1.0 |
| `cont_lexical` | 0.0 |
| `tag_overlap_rate_reference` | 0.666667 |
| `denominator_adjacent_pairs` | 3 |

### L 措辞层（per-message）

| 指标 | 值 |
|---|---|
| `L-1_len.p50 / p90` | 16.5 / 17.7 |
| `L-1_len_excl_paren.p50` | 16.5 |
| `L-2_narration_rate_proxy` | 0.0 |
| `L-3_paren_block_any` | 0.0 |
| `L-4_third_person_self_rate` | 0.0 |
| `L-5_template_hit_rate` | 0.0 |
| `L-6_dup_exact_rate` | 0.0 |
| `L-7_dup_ngram8_rate` | 0.0 |
| `L-8_agent_id_leak_rate` | 0.0 |
| `L-9_meta_talk_rate` | 0.0 |
| `L-10_self_address_error_rate` | 0.0 |
| `L-11_second_person_rate(dm+group)` | 0.75 |
| `L-12_peer_name_address_rate(dm+group)` | 0.0 |

### F 生活气息（proxy，per-message / per-adjacent-pair）

| 指标 | 值 |
|---|---|
| `F-1 非功能性闲聊占比` | 0.75 |
| `F-2 话题漂移率` | 0.333333 |
| `F-2b 多话题线程占比` | 1.0 |
| `F-3 情绪呼应率` | None |
| `F-3 分母` | 0 |
| `F-4 修复闭环率` | None |
| `F-4 张力事件数` | 0 |
| `F-5 习惯强度` | 0.0 |
| `F-6 跨天记忆引用率` | 0.5 |
| `F-7a 越界提及率` | 0.0 |

### E 效率层

| 指标 | 值 |
|---|---|
| `E-1_msg_per_agent_round` | 2.0 |
| `E-2_tokens_out_per_message` | 5.0 |
| `dialogue_calls` | 1 |
| `degraded_ratio` | 0.0 |

### 准入检查明细

| 编号 | 通过 | 细节 |
|---|---|---|
| B-7_files | ✅ | "meta.json 存在" |
| B-8_parse | ✅ | [] |
| B-9_event_count | ✅ | {"meta.events": 7, "actual_lines": 7} |
| B-10_provider | ✅ | "openai_compat" |
| B-11_real_calls | ✅ | {"dialogue_calls": 1} |
| B-12_degraded_ratio | ✅ | {"ratio": 0.0, "degraded": 0, "calls": 1} |
| B-13_event_families | ✅ | {"missing": []} |
| B-15_msg_volume | ❌ | {"msg_dm": 4, "messages": 4, "dm_threads": 1, "floor": "MSG>=150 且 MSG_DM>=100 且 DM 会话线>=12（v1.2）"} |
| B-2b_manifest_effective | ✅ | {"rounds_effective": 1, "rounds_per_slot_effective": "3", "note": ""} |
| B-15_msg_fields | ✅ | {"empty_body": [], "required_keys": ["from", "to", "body", "msg_id", "day", "slot", "place", "tag_hints"]} |
| B-16_round_dense | ✅ | {"min": 0, "max": 0, "n": 1} |
| B-17_hash_chain | ✅ | {"seq_dense": true, "hash_links_ok": true, "n": 7} |
| B-19_provider_distribution | ✅ | {"providers": {"openai_compat": 1}, "rule": "全部 LLM_CALL.provider 必须为 openai_compat"} |
| B-20_model_no_mock | ✅ | {"models": ["DeepSeek-Flash"], "rule": "model 去重集合不得含 mock"} |
| B-21_body_not_template | ✅ | {"L-5_template_hit_rate": 0.0, "L-6_dup_exact_rate": 0.0, "rule": "模板命中率<50% 且 完全重复率<50%；另需人工抽样双查"} |

