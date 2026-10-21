# 对话质量客观指标读数（D5 复算器自动生成）

- 输入日志: `v2/evidence/run_f6_off_n16r60_seed42/run.jsonl`
- run.jsonl sha256: `sha256:c73bead61a440db789f6d6ba1de555fe326a203ee27d1219690174e3d9483642`
- 脚本 sha256: `sha256:ac1a3886cc2d65588b0a030a168f93e2cfa25b82fd6dadd6ceb72e58a11751aa`
- 口径版本: `d5-metrics/1.0` / thread_schema=`explicit`
- 准入结论: **ADMITTED** / evidence_level=`evidence`

消息数 510，线程数 169，channel={'public': 55, 'dm': 455}

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
| `single_msg_thread_ratio` | 0.47929 |
| `single_speaker_thread_ratio` | 0.47929 |
| `multi_turn_thread_ratio (turns_A>=3)` | 0.455621 |

### S-3 最长链（per-thread）

| 指标 | 值 |
|---|---|
| `chain_by_alternation p50/max` | 2.0 / 6.0 |
| `chain_by_pointer max` | 6.0 |

### S-4 回复指针完整率（per-message，条件分母）

| 指标 | 值 |
|---|---|
| `rate` | 1.0 |
| `denominator_nonfirst_msgs` | 341 |
| `ptr_ok` | 341 |
| `ptr_empty` | 0 |
| `ptr_cross_thread` | 0 |
| `ptr_forward` | 0 |
| `ptr_dangling` | 0 |

### K-1b 话题承接·宽口径（day+channel 相邻，分母更大）

| 指标 | 值 |
|---|---|
| `cont_backref` | 0.328 |
| `cont_lexical` | 0.178 |
| `tag_overlap_rate_reference` | 0.346 |
| `denominator_adjacent_pairs` | 500 |

### K-1c 话题承接·对端口径（day+channel+对端；与 S-1/S-2 legacy 线程一致）

| 指标 | 值 |
|---|---|
| `cont_backref` | 0.325641 |
| `cont_lexical` | 0.569231 |
| `denominator_adjacent_pairs` | 390 |

### K-1 话题承接·主口径 mixed（dm 按对、public 按日、group 按组；三列独立，不出合成数）

| 指标 | 值 |
|---|---|
| `cont_same_topic` | 1.0 |
| `cont_backref` | 0.351906 |
| `cont_lexical` | 0.57478 |
| `tag_overlap_rate_reference` | 1.0 |
| `denominator_adjacent_pairs` | 341 |

### L 措辞层（per-message）

| 指标 | 值 |
|---|---|
| `L-1_len.p50 / p90` | 29.0 / 54.0 |
| `L-1_len_excl_paren.p50` | 29.0 |
| `L-2_narration_rate_proxy` | 0.0 |
| `L-3_paren_block_any` | 0.0 |
| `L-4_third_person_self_rate` | 0.0 |
| `L-5_template_hit_rate` | 0.011765 |
| `L-6_dup_exact_rate` | 0.101961 |
| `L-7_dup_ngram8_rate` | 0.354902 |
| `L-8_agent_id_leak_rate（分母=全MSG n=510）` | 0.0 |
| `L-9_meta_talk_rate` | 0.0 |
| `L-10_self_address_error_rate` | 0.0 |
| `L-11_second_person_rate（分母=dm+group n=455）` | 0.665934 |
| `L-12a 对端提及率（分母=dm+group n=455）` | 0.661538 |
| `L-12b 对端称呼率（分母=dm+group n=455，判定用）` | 0.575824 |
| `L-8b_paren_only_id_rate（分母=全MSG n=510；仅旁白内ID）` | 0.0 |
| `L-8c_body_leak_rate（分母=全MSG n=510；台词本体ID）` | 0.0 |

### F 生活气息（proxy，per-message / per-adjacent-pair）

| 指标 | 值 |
|---|---|
| `F-1 非功能性闲聊占比` | 0.717647 |
| `F-2 话题漂移率` | 0.0 |
| `F-2b 多话题线程占比` | 0.0 |
| `F-3 情绪呼应率` | 0.111111 |
| `F-3 分母` | 36 |
| `F-4 修复闭环率` | 0.0 |
| `F-4 张力事件数` | 22 |
| `F-5 习惯强度` | 1.0 |
| `F-6 跨天记忆引用率` | 0.037255 |
| `F-7a 越界提及率` | 0.145098 |

### E 效率层

| 指标 | 值 |
|---|---|
| `E-1_msg_per_agent_round` | 0.559211 |
| `E-2_tokens_out_per_message` | 23.641176 |
| `dialogue_calls` | 510 |
| `degraded_ratio` | 0.0 |

### 准入检查明细

| 编号 | 通过 | 细节 |
|---|---|---|
| B-7_files | ✅ | "meta.json 存在" |
| B-8_parse | ✅ | [] |
| B-9_event_count | ✅ | {"meta.events": 116294, "actual_lines": 116294} |
| B-10_provider | ✅ | "openai_compat" |
| B-11_real_calls | ✅ | {"dialogue_calls": 510} |
| B-12_degraded_ratio | ✅ | {"ratio": 0.0, "degraded": 0, "calls": 2878} |
| B-13_event_families | ✅ | {"missing": []} |
| B-15_msg_volume | ✅ | {"msg_dm": 455, "messages": 510, "dm_threads": 92, "floor": "MSG>=150 且 MSG_DM>=100 且 DM 会话线>=12（v1.2）"} |
| B-2b_manifest_effective | ✅ | {"rounds_effective": 60, "rounds_per_slot_effective": 3, "note": ""} |
| B-15_msg_fields | ✅ | {"empty_body": [], "required_keys": ["from", "to", "body", "msg_id", "day", "slot", "place", "tag_hints"]} |
| B-16_round_dense | ✅ | {"min": 0, "max": 59, "n": 60} |
| B-17_hash_chain | ✅ | {"seq_dense": true, "hash_links_ok": true, "n": 116294} |
| B-19_provider_distribution | ✅ | {"providers": {"openai_compat": 2878}, "rule": "全部 LLM_CALL.provider 必须为 openai_compat"} |
| B-20_model_no_mock | ✅ | {"models": ["DeepSeek-Flash"], "rule": "model 去重集合不得含 mock"} |
| B-21_body_not_template | ✅ | {"L-5_template_hit_rate": 0.011765, "L-6_dup_exact_rate": 0.101961, "rule": "模板命中率<50% 且 完全重复率<50%；另需人工抽样双查"} |

