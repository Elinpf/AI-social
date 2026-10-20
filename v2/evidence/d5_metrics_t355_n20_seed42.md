# 对话质量客观指标读数（D5 复算器自动生成）

- 输入日志: `/root/t271/runs/t355/run.jsonl`
- run.jsonl sha256: `sha256:bee77237e7c2fa3a41ae7613d2ef3e4bf989c1b4f57b831fc29edc714dec3c36`
- 脚本 sha256: `sha256:df07440cd3bb2ff71b2882de28fb07b5e8d1f5b389497657c956a7c1af994ae1`
- 口径版本: `d5-metrics/1.0` / thread_schema=`legacy`
- 准入结论: **ADMITTED** / evidence_level=`evidence`

消息数 230，线程数 212，channel={'public': 59, 'dm': 163, 'group': 8}

### S-1 线程轮次（per-thread）

| 指标 | 值 |
|---|---|
| `A_speaker_turns.p50` | 1.0 |
| `A_speaker_turns.p90/max` | 1.0 / 2.0 |
| `B_roundtrips.p50` | 0.0 |
| `B_roundtrips.max` | 0.0 |

### S-2 线程规模（per-thread）

| 指标 | 值 |
|---|---|
| `msgs_per_thread p50/p90/max` | 1.0 / 1.0 / 2.0 |
| `single_msg_thread_ratio` | 0.915094 |
| `single_speaker_thread_ratio` | 0.966981 |
| `multi_turn_thread_ratio (turns_A>=3)` | 0.0 |

### S-3 最长链（per-thread）

| 指标 | 值 |
|---|---|
| `chain_by_alternation p50/max` | 1.0 / 2.0 |
| `chain_by_pointer max` | 1.0 |

### S-4 回复指针完整率（per-message，条件分母）

| 指标 | 值 |
|---|---|
| `rate` | 0.0 |
| `denominator_nonfirst_msgs` | 18 |
| `ptr_ok` | 0 |
| `ptr_empty` | 18 |
| `ptr_cross_thread` | 0 |
| `ptr_forward` | 0 |

### K-1b 话题承接·宽口径（day+channel 相邻，分母更大）

| 指标 | 值 |
|---|---|
| `cont_backref` | 0.413953 |
| `cont_lexical` | 0.102326 |
| `tag_overlap_rate_reference` | 0.497674 |
| `denominator_adjacent_pairs` | 215 |

### K-1c 话题承接·对端口径（day+channel+对端；与 S-1/S-2 legacy 线程一致）

| 指标 | 值 |
|---|---|
| `cont_backref` | 0.555556 |
| `cont_lexical` | 0.166667 |
| `denominator_adjacent_pairs` | 18 |

### K-1 话题承接·主口径 mixed（dm 按对、public 按日、group 按组；三列独立，不出合成数）

| 指标 | 值 |
|---|---|
| `cont_same_topic` | N/A |
| `cont_backref` | 0.308824 |
| `cont_lexical` | 0.176471 |
| `tag_overlap_rate_reference` | 0.602941 |
| `denominator_adjacent_pairs` | 68 |

### L 措辞层（per-message）

| 指标 | 值 |
|---|---|
| `L-1_len.p50 / p90` | 44.0 / 69.0 |
| `L-1_len_excl_paren.p50` | 35.0 |
| `L-2_narration_rate_proxy` | 0.647826 |
| `L-3_paren_block_any` | 0.656522 |
| `L-4_third_person_self_rate` | 0.069565 |
| `L-5_template_hit_rate` | 0.143478 |
| `L-6_dup_exact_rate` | 0.121739 |
| `L-7_dup_ngram8_rate` | 0.543478 |
| `L-8_agent_id_leak_rate` | 0.352174 |
| `L-9_meta_talk_rate` | 0.0 |
| `L-10_self_address_error_rate` | 0.0 |
| `L-11_second_person_rate(dm+group)` | 0.760234 |
| `L-12_peer_name_address_rate(dm+group)` | 0.0 |

### F 生活气息（proxy，per-message / per-adjacent-pair）

| 指标 | 值 |
|---|---|
| `F-1 非功能性闲聊占比` | 0.730435 |
| `F-2 话题漂移率` | 0.382353 |
| `F-2b 多话题线程占比` | 0.084906 |
| `F-3 情绪呼应率` | 0.066667 |
| `F-3 分母` | 15 |
| `F-4 修复闭环率` | 0.0 |
| `F-4 张力事件数` | 4 |
| `F-5 习惯强度` | 0.9 |
| `F-6 跨天记忆引用率` | 0.06087 |
| `F-7a 越界提及率` | 0.0 |

### E 效率层

| 指标 | 值 |
|---|---|
| `E-1_msg_per_agent_round` | 0.547619 |
| `E-2_tokens_out_per_message` | 38.673913 |
| `dialogue_calls` | 270 |
| `degraded_ratio` | 0.0 |

### 准入检查明细

| 编号 | 通过 | 细节 |
|---|---|---|
| B-7_files | ✅ | "meta.json 存在" |
| B-8_parse | ✅ | [] |
| B-9_event_count | ✅ | {"meta.events": null, "actual_lines": 292255, "note": "legacy manifest 无 events 字段，改以 wc -l 为准（须人工核对）"} |
| B-10_provider | ✅ | "openai_compat" |
| B-11_real_calls | ✅ | {"dialogue_calls": 270} |
| B-12_degraded_ratio | ✅ | {"ratio": 0.0, "degraded": 0, "calls": 4757} |
| B-13_event_families | ✅ | {"missing": []} |
| B-15_msg_volume | ✅ | {"msg_dm": 163, "messages": 230, "dm_threads": 152, "floor": "MSG>=150 且 MSG_DM>=100 且 DM 会话线>=12（v1.2）"} |
| B-2b_manifest_effective | ✅ | {"rounds_effective": null, "rounds_per_slot_effective": null, "note": "legacy manifest：以 meta.cmd 中的 --rounds 为准，须人工核对"} |
| B-15_msg_fields | ✅ | {"empty_body": [], "required_keys": ["from", "to", "body", "msg_id", "day", "slot", "place", "tag_hints"]} |
| B-16_round_dense | ✅ | {"min": 0, "max": 83, "n": 84} |
| B-17_hash_chain | ✅ | {"seq_dense": true, "hash_links_ok": true, "n": 292255} |
| B-19_provider_distribution | ✅ | {"providers": {"openai_compat": 4757}, "rule": "全部 LLM_CALL.provider 必须为 openai_compat"} |
| B-20_model_no_mock | ✅ | {"models": ["DeepSeek-Flash"], "rule": "model 去重集合不得含 mock"} |
| B-21_body_not_template | ✅ | {"L-5_template_hit_rate": 0.143478, "L-6_dup_exact_rate": 0.121739, "rule": "模板命中率<50% 且 完全重复率<50%；另需人工抽样双查"} |

