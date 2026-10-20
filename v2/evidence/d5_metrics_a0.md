# 对话质量客观指标读数（D5 复算器自动生成）

- 输入日志: `v2/evidence/run_d2_after_n16_seed42/run.jsonl`
- run.jsonl sha256: `sha256:643f13a528c288d3e9677cb8ac100139224afbd0b46c0f7da0c3a5ed85b13141`
- 脚本 sha256: `sha256:4049fbf83f2bfde52c7565c28869669de40478a2db7282177e4567c749d1163c`
- 口径版本: `d5-metrics/1.0` / thread_schema=`explicit`
- 准入结论: **ADMITTED** / evidence_level=`evidence`

消息数 686，线程数 206，channel={'public': 63, 'dm': 497, 'group': 126}

### S-1 线程轮次（per-thread）

| 指标 | 值 |
|---|---|
| `A_speaker_turns.p50` | 2.0 |
| `A_speaker_turns.p90/max` | 6.0 / 18.0 |
| `B_roundtrips.p50` | 1.0 |
| `B_roundtrips.max` | 17.0 |

### S-2 线程规模（per-thread）

| 指标 | 值 |
|---|---|
| `msgs_per_thread p50/p90/max` | 2.0 / 6.0 / 18.0 |
| `single_msg_thread_ratio` | 0.495146 |
| `single_speaker_thread_ratio` | 0.495146 |
| `multi_turn_thread_ratio (turns_A>=3)` | 0.436893 |

### S-3 最长链（per-thread）

| 指标 | 值 |
|---|---|
| `chain_by_alternation p50/max` | 2.0 / 18.0 |
| `chain_by_pointer max` | 6.0 |

### S-4 回复指针完整率（per-message，条件分母）

| 指标 | 值 |
|---|---|
| `rate` | 1.0 |
| `denominator_nonfirst_msgs` | 480 |
| `ptr_ok` | 480 |
| `ptr_empty` | 0 |
| `ptr_cross_thread` | 0 |
| `ptr_forward` | 0 |
| `ptr_dangling` | 0 |

### K-1b 话题承接·宽口径（day+channel 相邻，分母更大）

| 指标 | 值 |
|---|---|
| `cont_backref` | 0.491045 |
| `cont_lexical` | 0.197015 |
| `tag_overlap_rate_reference` | 0.374627 |
| `denominator_adjacent_pairs` | 670 |

### K-1c 话题承接·对端口径（day+channel+对端；与 S-1/S-2 legacy 线程一致）

| 指标 | 值 |
|---|---|
| `cont_backref` | 0.516505 |
| `cont_lexical` | 0.631068 |
| `denominator_adjacent_pairs` | 515 |

### K-1 话题承接·主口径 mixed（dm 按对、public 按日、group 按组；三列独立，不出合成数）

| 指标 | 值 |
|---|---|
| `cont_same_topic` | 1.0 |
| `cont_backref` | 0.547917 |
| `cont_lexical` | 0.685417 |
| `tag_overlap_rate_reference` | 1.0 |
| `denominator_adjacent_pairs` | 480 |

### L 措辞层（per-message）

| 指标 | 值 |
|---|---|
| `L-1_len.p50 / p90` | 54.0 / 97.5 |
| `L-1_len_excl_paren.p50` | 41.0 |
| `L-2_narration_rate_proxy` | 0.819242 |
| `L-3_paren_block_any` | 0.860058 |
| `L-4_third_person_self_rate` | 0.069971 |
| `L-5_template_hit_rate` | 0.01895 |
| `L-6_dup_exact_rate` | 0.099125 |
| `L-7_dup_ngram8_rate` | 0.488338 |
| `L-8_agent_id_leak_rate（分母=全MSG n=686）` | 0.0 |
| `L-9_meta_talk_rate` | 0.0 |
| `L-10_self_address_error_rate` | 0.0 |
| `L-11_second_person_rate（分母=dm+group n=623）` | 0.727127 |
| `L-12a 对端提及率（分母=dm+group n=623）` | 0.656501 |
| `L-12b 对端称呼率（分母=dm+group n=623，判定用）` | 0.510433 |
| `L-8b_paren_only_id_rate（分母=全MSG n=686；仅旁白内ID）` | 0.0 |
| `L-8c_body_leak_rate（分母=全MSG n=686；台词本体ID）` | 0.0 |

### F 生活气息（proxy，per-message / per-adjacent-pair）

| 指标 | 值 |
|---|---|
| `F-1 非功能性闲聊占比` | 0.760933 |
| `F-2 话题漂移率` | 0.0 |
| `F-2b 多话题线程占比` | 0.0 |
| `F-3 情绪呼应率` | 0.242991 |
| `F-3 分母` | 107 |
| `F-4 修复闭环率` | 0.076923 |
| `F-4 张力事件数` | 39 |
| `F-5 习惯强度` | 1.0 |
| `F-6 跨天记忆引用率` | 0.06414 |
| `F-7a 越界提及率` | 0.155977 |

### E 效率层

| 指标 | 值 |
|---|---|
| `E-1_msg_per_agent_round` | 0.529321 |
| `E-2_tokens_out_per_message` | 42.833819 |
| `dialogue_calls` | 714 |
| `degraded_ratio` | 0.0 |

### 准入检查明细

| 编号 | 通过 | 细节 |
|---|---|---|
| B-7_files | ✅ | "meta.json 存在" |
| B-8_parse | ✅ | [] |
| B-9_event_count | ✅ | {"meta.events": 194108, "actual_lines": 194108} |
| B-10_provider | ✅ | "openai_compat" |
| B-11_real_calls | ✅ | {"dialogue_calls": 714} |
| B-12_degraded_ratio | ✅ | {"ratio": 0.0, "degraded": 0, "calls": 3403} |
| B-13_event_families | ✅ | {"missing": []} |
| B-15_msg_volume | ✅ | {"msg_dm": 497, "messages": 686, "dm_threads": 109, "floor": "MSG>=150 且 MSG_DM>=100 且 DM 会话线>=12（v1.2）"} |
| B-2b_manifest_effective | ✅ | {"rounds_effective": 84, "rounds_per_slot_effective": 3, "note": ""} |
| B-15_msg_fields | ✅ | {"empty_body": [], "required_keys": ["from", "to", "body", "msg_id", "day", "slot", "place", "tag_hints"]} |
| B-16_round_dense | ✅ | {"min": 0, "max": 83, "n": 84} |
| B-17_hash_chain | ✅ | {"seq_dense": true, "hash_links_ok": true, "n": 194108} |
| B-19_provider_distribution | ✅ | {"providers": {"openai_compat": 3403}, "rule": "全部 LLM_CALL.provider 必须为 openai_compat"} |
| B-20_model_no_mock | ✅ | {"models": ["DeepSeek-Flash"], "rule": "model 去重集合不得含 mock"} |
| B-21_body_not_template | ✅ | {"L-5_template_hit_rate": 0.01895, "L-6_dup_exact_rate": 0.099125, "rule": "模板命中率<50% 且 完全重复率<50%；另需人工抽样双查"} |

