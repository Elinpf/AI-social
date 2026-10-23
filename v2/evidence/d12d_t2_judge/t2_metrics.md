# 对话质量客观指标读数（D5 复算器自动生成）

- 输入日志: `v2/evidence/run_d12d_on_n16r60_seed42/run.jsonl`
- run.jsonl sha256: `sha256:ad0c939f062d23553adeb42af52617d082395265ddb2f6fe12a11d3093144ca0`
- 脚本 sha256: `sha256:1d914735f3a13cf4e1640bd694f1d0e070096c9f50abfdefa7359417df551271`
- 口径版本: `d5-metrics/1.0` / thread_schema=`explicit`
- 准入结论: **REJECTED** / evidence_level=`probe`

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
| `cont_backref` | 0.954 |
| `cont_lexical` | 0.764 |
| `tag_overlap_rate_reference` | 0.346 |
| `denominator_adjacent_pairs` | 500 |

### K-1c 话题承接·对端口径（day+channel+对端；与 S-1/S-2 legacy 线程一致）

| 指标 | 值 |
|---|---|
| `cont_backref` | 0.964103 |
| `cont_lexical` | 0.971795 |
| `denominator_adjacent_pairs` | 390 |

### K-1 话题承接·主口径 mixed（dm 按对、public 按日、group 按组；三列独立，不出合成数）

| 指标 | 值 |
|---|---|
| `cont_same_topic` | 1.0 |
| `cont_backref` | 0.97654 |
| `cont_lexical` | 0.991202 |
| `tag_overlap_rate_reference` | 1.0 |
| `denominator_adjacent_pairs` | 341 |

### L 措辞层（per-message）

| 指标 | 值 |
|---|---|
| `L-1_len.p50 / p90` | 61.0 / 114.0 |
| `L-1_len_excl_paren.p50` | 53.0 |
| `L-2_narration_rate_proxy` | 0.466667 |
| `L-3_paren_block_any` | 0.501961 |
| `L-4_third_person_self_rate` | 0.086275 |
| `L-5_template_hit_rate` | 0.0 |
| `L-6_dup_exact_rate` | 0.098039 |
| `L-7_dup_ngram8_rate` | 0.645098 |
| `L-8_agent_id_leak_rate（分母=全MSG n=510）` | 0.003922 |
| `L-9_meta_talk_rate` | 0.0 |
| `L-10_self_address_error_rate` | 0.0 |
| `L-11_second_person_rate（分母=dm+group n=455）` | 0.564835 |
| `L-12a 对端提及率（分母=dm+group n=455）` | 0.643956 |
| `L-12b 对端称呼率（分母=dm+group n=455，判定用）` | 0.534066 |
| `L-8b_paren_only_id_rate（分母=全MSG n=510；仅旁白内ID）` | 0.0 |
| `L-8c_body_leak_rate（分母=全MSG n=510；台词本体ID）` | 0.003922 |

### F 生活气息（proxy，per-message / per-adjacent-pair）

| 指标 | 值 |
|---|---|
| `F-1 非功能性闲聊占比` | 0.690196 |
| `F-2 话题漂移率` | 0.0 |
| `F-2b 多话题线程占比` | 0.0 |
| `F-3 情绪呼应率` | 0.125 |
| `F-3 分母` | 16 |
| `F-4 修复闭环率` | 0.0 |
| `F-4 张力事件数` | 17 |
| `F-5 习惯强度` | 1.0 |
| `F-6 跨天记忆引用率` | 0.882353 |
| `F-7a 越界提及率` | 0.188235 |

### F-8 处境锚定率（per-message，三分项并列；词表外部冻结 sha256=sha256:004f3bca138e7800a0fc0ac7e0f1c0f0bdb9b0a862432fa53f65b152bdb2ddd3）

| 项 | 分子/分母/率 | 分母口径 |
|---|---|---|
| F-8（总：任一项命中） | 13/510 = 2.55%  Wilson95[1.50%, 4.31%] | num=命中本人当回合处境（时段**仅档内词** / 自身地点 / 活动 任一）的 MSG_* 条数；den=全部 MSG_*；时段侧用 F-8t_core（不含通用指示词「这会儿」），故与 F-8_with_all_time 可能不同；各分项按自己的分母计入（F-8p 用有 place 的 167、F-8a 用有 activity 的 n） |
| F-8t 时段词（narrow，本回合 slot） | 9/510 = 1.76%  Wilson95[0.93%, 3.32%] | 判定词表=time.narrow（Amendment 1：不含 刚/早上/下午/晚上/昨晚/今天/今儿）；scope=本人当回合 slot；den=有 slot 的 MSG_* |
| F-8t 时段词·Amendment 2 前口径（敏感性对照） | 9/510 = 1.76%  Wilson95[0.93%, 3.32%] | 敏感性对照（Amendment 2 前口径）：同一 onset 下剔除 ['下午']，仍按本回合 slot 限定；den 与 F-8t_time 完全相同，供报告并列证明结论不依赖该词取舍 |
| F-8p 地点中文名（本人 place） | 4/455 = 0.88%  Wilson95[0.34%, 2.24%] | 只认 places.json::name_cn（含 place.short_names 可接受简称）；num=正文含「本人 place」名称的条数；den=有 payload.place 的 MSG_* |
| F-8a 活动人话名 | not_applicable（no_ctx_scene） | num=正文命中「本人 ctx.scene.activity」的渲染措辞或语义等价项；den=含 ctx.scene.activity 的 MSG_* |
| F-8p_public（仅覆盖说明，不判定） | 4/55 = 7.27%  Wilson95[2.86%, 17.26%] | 仅覆盖说明、不作判定：MSG_PUBLIC 无 place 字段，den=MSG_PUBLIC 条数，num=正文命中任一 name_cn 条数 |
| 守卫：正文出现内部 place_id | 0/510 = 0.00%  Wilson95[0.00%, 0.75%] | 守卫（对应 L-8c）：正文出现 places.json::place_id 内部 id 的条数；>0 ⇒ 硬失败 |

**仅参考、不参与判定 / 敏感性通道**

| 项 | 分子/分母/率 |
|---|---|
| F-8t 宽版词表 | 67/510 = 13.14%  Wilson95[10.48%, 16.35%] |
| F-8t 复现 checkpoint 窄表(7/191) | 23/510 = 4.51%  Wilson95[3.02%, 6.68%] |
| F-8t 复现 checkpoint 宽表(74/191) | 56/510 = 10.98%  Wilson95[8.55%, 13.99%] |
| F-8t narrow∪{今儿}（不按 slot 限定） | 31/510 = 6.08%  Wilson95[4.31%, 8.50%] |
| F-8t slot-scoped broad（Amendment 2 候选） | 10/510 = 1.96%  Wilson95[1.07%, 3.57%] |
| F-8t 渲染词表回声通道 | 12/510 = 2.35%  Wilson95[1.35%, 4.07%] |
| F-8t 不限本回合 slot | 22/510 = 4.31%  Wilson95[2.87%, 6.44%] |
| F-8p 任一中文地名 | 28/510 = 5.49%  Wilson95[3.83%, 7.82%] |
| F-8p 其中只靠简称命中 | 0/455 = 0.00%  Wilson95[0.00%, 0.84%] |
| F-8a 严格口径（只认渲染原文） | not_applicable（no_ctx_scene） |
| F-8t 命中模型实际看到的措辞 | not_applicable（no_line_sha256） |
| F-8a 命中模型实际看到的措辞 | not_applicable（no_line_sha256） |

**分母不适用清单**：[{"item": "F-8a_activity", "status": "not_applicable", "reason": "no_ctx_scene", "detail": "本臂 MSG payload 无 ctx.scene.activity（510/510 条缺该键）⇒ 分母不适用；不等于『模型没做活动锚定』", "den": null, "num": null}, {"item": "F-8p_place", "reason": "55 条 MSG（MSG_PUBLIC）无 payload.place，已从分母剔除，另在 F-8p_public 单列覆盖（不作判定）", "den": 455, "num": 4}]

### E 效率层

| 指标 | 值 |
|---|---|
| `E-1_msg_per_agent_round` | 0.559211 |
| `E-2_tokens_out_per_message` | 54.233333 |
| `dialogue_calls` | 510 |
| `degraded_ratio` | 0.0 |

### 准入检查明细

| 编号 | 通过 | 细节 |
|---|---|---|
| B-7_files | ✅ | "meta.json 存在" |
| B-8_parse | ✅ | [] |
| B-9_event_count | ✅ | {"meta.events": null, "actual_lines": 116398, "note": "legacy manifest 无 events 字段，改以 wc -l 为准（须人工核对）"} |
| B-10_provider | ❌ | "<empty>" |
| B-11_real_calls | ✅ | {"dialogue_calls": 510} |
| B-12_degraded_ratio | ✅ | {"ratio": 0.0, "degraded": 0, "calls": 2878} |
| B-13_event_families | ✅ | {"missing": []} |
| B-15_msg_volume | ✅ | {"msg_dm": 455, "messages": 510, "dm_threads": 92, "floor": "MSG>=150 且 MSG_DM>=100 且 DM 会话线>=12（v1.2）"} |
| B-2b_manifest_effective | ✅ | {"rounds_effective": null, "rounds_per_slot_effective": null, "note": "legacy manifest：以 meta.cmd 中的 --rounds 为准，须人工核对"} |
| B-15_msg_fields | ✅ | {"empty_body": [], "required_keys": ["from", "to", "body", "msg_id", "day", "slot", "place", "tag_hints"]} |
| B-16_round_dense | ✅ | {"min": 0, "max": 59, "n": 60} |
| B-17_hash_chain | ✅ | {"seq_dense": true, "hash_links_ok": true, "n": 116398} |
| B-19_provider_distribution | ✅ | {"providers": {"openai_compat": 2878}, "rule": "全部 LLM_CALL.provider 必须为 openai_compat"} |
| B-20_model_no_mock | ✅ | {"models": ["DeepSeek-Flash"], "rule": "model 去重集合不得含 mock"} |
| B-21_body_not_template | ✅ | {"L-5_template_hit_rate": 0.0, "L-6_dup_exact_rate": 0.098039, "rule": "模板命中率<50% 且 完全重复率<50%；另需人工抽样双查"} |

