# 噪声带（null pair）读数

- A: `t300` (run sha `sha256:33b7651f2b11d5eaf5720dbd0560cc2ea2a468d37f7319d972b2d7fafd808a08`)
- B: `t355` (run sha `sha256:bee77237e7c2fa3a41ae7613d2ef3e4bf989c1b4f57b831fc29edc714dec3c36`)
- 协议：null pair：两批提示词实质相同、只差无关树改动。band_i = |metric_i(A)-metric_i(B)| 视为该指标「什么都不改也会有的波动」。D4/D6 的 Δ 必须报 vs_null_band = Δ/band；|vs_null_band|<=1 只能记印象。band 由单对批估计，样本量小、不可外推到不同规模/不同模型。

## 逐条一致率（证明同 seed≠同文本）

| 项 | 值 |
|---|---|
| MSG 条数 A / B | 230 / 230 |
| 逐条正文一致 | 49/230 = 0.213043 |
| 收发对一致 | 230/230 = 1.0 |
| 说话人一致 | 230/230 = 1.0 |
| 对齐方式 | 按 (round, seq) 排序后按位置配对（两批 MSG 条数须一致才可用） |

## 各指标噪声带（按相对带宽降序）

| 指标 | A | B | Δ(A−B) | band=\|Δ\| | rel_band |
|---|---|---|---|---|---|
| `F-3_emotion_echo.echo_rate` | 0.0 | 0.066667 | -0.066667 | 0.066667 | 1.0 |
| `K-1_topic_continuation.cont_lexical` | 0.088235 | 0.176471 | -0.088236 | 0.088236 | 0.333336 |
| `L_wording.L-5_template_hit_by_pattern.3` | 1.0 | 2.0 | -1.0 | 1.0 | 0.333333 |
| `K-1b_topic_continuation_wide.cont_lexical` | 0.060465 | 0.102326 | -0.041861 | 0.041861 | 0.257146 |
| `K-1c_topic_continuation_pair.cont_lexical` | 0.277778 | 0.166667 | 0.111111 | 0.111111 | 0.249999 |
| `F-4_tension_repair.tension_events` | 6.0 | 4.0 | 2.0 | 2.0 | 0.2 |
| `K-1c_topic_continuation_pair.cont_backref` | 0.388889 | 0.555556 | -0.166667 | 0.166667 | 0.176471 |
| `L_wording.L-1_len.excl_paren.min` | 8.0 | 10.0 | -2.0 | 2.0 | 0.111111 |
| `L_wording.L-1_len.all.p10` | 21.0 | 24.9 | -3.9 | 3.9 | 0.084967 |
| `F-6_crossday_memory.timeref_rate` | 0.052174 | 0.06087 | -0.008696 | 0.008696 | 0.076926 |
| `L_wording.L-1_len.all.min` | 14.0 | 12.0 | 2.0 | 2.0 | 0.076923 |
| `K-1_topic_continuation.cont_backref` | 0.352941 | 0.308824 | 0.044117 | 0.044117 | 0.066666 |
| `L_wording.L-5_template_hit_rate` | 0.126087 | 0.143478 | -0.017391 | 0.017391 | 0.064515 |
| `admission.checks.B-21_body_not_template.detail.L-5_template_hit_rate` | 0.126087 | 0.143478 | -0.017391 | 0.017391 | 0.064515 |
| `L_wording.L-4_third_person_self_rate` | 0.078261 | 0.069565 | 0.008696 | 0.008696 | 0.058826 |
| `L_wording.L-1_len.excl_paren.stdev` | 19.75173 | 17.900167 | 1.851563 | 1.851563 | 0.049176 |
| `L_wording.L-1_len.excl_paren.max` | 130.0 | 143.0 | -13.0 | 13.0 | 0.047619 |
| `L_wording.L-1_len.all.stdev` | 24.108935 | 21.951443 | 2.157492 | 2.157492 | 0.046841 |
| `L_wording.L-1_len.all.max` | 179.0 | 192.0 | -13.0 | 13.0 | 0.03504 |
| `F-5_habit_repetition.habit_strength` | 0.85 | 0.9 | -0.05 | 0.05 | 0.028571 |
| `L_wording.L-1_len.excl_paren.p10` | 17.0 | 18.0 | -1.0 | 1.0 | 0.028571 |
| `K-1b_topic_continuation_wide.cont_backref` | 0.395349 | 0.413953 | -0.018604 | 0.018604 | 0.022988 |
| `L_wording.L-1_len.excl_paren.p90` | 59.1 | 57.0 | 2.1 | 2.1 | 0.018088 |
| `L_wording.L-6_dup_exact_rate` | 0.126087 | 0.121739 | 0.004348 | 0.004348 | 0.017545 |
| `admission.checks.B-21_body_not_template.detail.L-6_dup_exact_rate` | 0.126087 | 0.121739 | 0.004348 | 0.004348 | 0.017545 |
| `L_wording.L-7_dup_ngram8_rate` | 0.526087 | 0.543478 | -0.017391 | 0.017391 | 0.01626 |
| `L_wording.L-1_len.all.p90` | 71.1 | 69.0 | 2.1 | 2.1 | 0.014989 |
| `L_wording.L-1_len.excl_paren.p50` | 34.0 | 35.0 | -1.0 | 1.0 | 0.014493 |
| `L_wording.L-8_agent_id_leak_rate` | 0.343478 | 0.352174 | -0.008696 | 0.008696 | 0.012501 |
| `L_wording.L-11_second_person_rate_dm_group` | 0.74269 | 0.760234 | -0.017544 | 0.017544 | 0.011673 |
| `F-5_habit_repetition.max_repeat_days_mean` | 3.45 | 3.5 | -0.05 | 0.05 | 0.007194 |
| `L_wording.L-2_narration_rate_proxy` | 0.63913 | 0.647826 | -0.008696 | 0.008696 | 0.006757 |
| `L_wording.L-3_paren_block_any` | 0.647826 | 0.656522 | -0.008696 | 0.008696 | 0.006667 |
| `L_wording.L-1_len.excl_paren.mean` | 37.578261 | 37.152174 | 0.426087 | 0.426087 | 0.005702 |
| `admission.checks.B-19_provider_distribution.detail.providers.openai_compat` | 4797.0 | 4757.0 | 40.0 | 40.0 | 0.004187 |
| `L_wording.L-1_len.all.mean` | 46.747826 | 46.53913 | 0.208696 | 0.208696 | 0.002237 |
| `admission.checks.B-9_event_count.detail.actual_lines` | 292963.0 | 292255.0 | 708.0 | 708.0 | 0.00121 |
| `llm.E-2_tokens_out_per_dialogue_call` | 33.014815 | 32.944444 | 0.070371 | 0.070371 | 0.001067 |
| `llm.E-2_tokens_out_per_message` | 38.756522 | 38.673913 | 0.082609 | 0.082609 | 0.001067 |
| `E_efficiency.E-1_msg_per_agent_round` | 0.547619 | 0.547619 | 0.0 | 0.0 | 0.0 |
| `F-1_chatter.functional_msgs` | 62.0 | 62.0 | 0.0 | 0.0 | 0.0 |
| `F-1_chatter.nonfunctional_chatter_rate` | 0.730435 | 0.730435 | 0.0 | 0.0 | 0.0 |
| `F-2_topic_drift.drift_rate` | 0.382353 | 0.382353 | 0.0 | 0.0 | 0.0 |
| `F-2_topic_drift.multi_topic_thread_ratio` | 0.084906 | 0.084906 | 0.0 | 0.0 | 0.0 |
| `F-4_tension_repair.closed_loop_rate` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `F-4_tension_repair.repaired` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `F-7a_offscreen_mention.offscreen_mention_rate` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `F-7a_offscreen_mention.unknown_place_lookups` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `K-1_topic_continuation.cont_same_topic_denominator` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `K-1_topic_continuation.tag_overlap_rate_reference` | 0.602941 | 0.602941 | 0.0 | 0.0 | 0.0 |
| `K-1b_topic_continuation_wide.cont_same_topic_denominator` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `K-1b_topic_continuation_wide.tag_overlap_rate_reference` | 0.497674 | 0.497674 | 0.0 | 0.0 | 0.0 |
| `K-1c_topic_continuation_pair.cont_same_topic_denominator` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `K-1c_topic_continuation_pair.tag_overlap_rate_reference` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `L_wording.L-10_self_address_error_rate` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `L_wording.L-12_peer_name_address_rate` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `L_wording.L-1_len.all.p50` | 44.0 | 44.0 | 0.0 | 0.0 | 0.0 |
| `L_wording.L-5_template_hit_by_pattern.0` | 10.0 | 10.0 | 0.0 | 0.0 | 0.0 |
| `L_wording.L-5_template_hit_by_pattern.2` | 3.0 | 3.0 | 0.0 | 0.0 | 0.0 |
| `L_wording.L-5_template_hit_by_pattern.5` | 14.0 | 14.0 | 0.0 | 0.0 | 0.0 |
| `L_wording.L-9_meta_talk_rate` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `S-1_turns_per_thread.A_speaker_turns.max` | 2.0 | 2.0 | 0.0 | 0.0 | 0.0 |
| `S-1_turns_per_thread.A_speaker_turns.mean` | 1.033019 | 1.033019 | 0.0 | 0.0 | 0.0 |
| `S-1_turns_per_thread.A_speaker_turns.min` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-1_turns_per_thread.A_speaker_turns.p10` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-1_turns_per_thread.A_speaker_turns.p50` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-1_turns_per_thread.A_speaker_turns.p90` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-1_turns_per_thread.A_speaker_turns.stdev` | 0.178686 | 0.178686 | 0.0 | 0.0 | 0.0 |
| `S-1_turns_per_thread.B_roundtrips.max` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `S-1_turns_per_thread.B_roundtrips.mean` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `S-1_turns_per_thread.B_roundtrips.min` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `S-1_turns_per_thread.B_roundtrips.p10` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `S-1_turns_per_thread.B_roundtrips.p50` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `S-1_turns_per_thread.B_roundtrips.p90` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `S-1_turns_per_thread.B_roundtrips.stdev` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.msgs_per_thread.max` | 2.0 | 2.0 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.msgs_per_thread.mean` | 1.084906 | 1.084906 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.msgs_per_thread.min` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.msgs_per_thread.p10` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.msgs_per_thread.p50` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.msgs_per_thread.p90` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.msgs_per_thread.stdev` | 0.278741 | 0.278741 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.multi_turn_thread_ratio` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.single_msg_thread_ratio` | 0.915094 | 0.915094 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.single_speaker_thread_ratio` | 0.966981 | 0.966981 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.speakers_per_thread.max` | 2.0 | 2.0 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.speakers_per_thread.mean` | 1.033019 | 1.033019 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.speakers_per_thread.min` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.speakers_per_thread.p10` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.speakers_per_thread.p50` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.speakers_per_thread.p90` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-2_thread_scale.speakers_per_thread.stdev` | 0.178686 | 0.178686 | 0.0 | 0.0 | 0.0 |
| `S-3_longest_chain.chain_by_alternation.max` | 2.0 | 2.0 | 0.0 | 0.0 | 0.0 |
| `S-3_longest_chain.chain_by_alternation.mean` | 1.033019 | 1.033019 | 0.0 | 0.0 | 0.0 |
| `S-3_longest_chain.chain_by_alternation.min` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-3_longest_chain.chain_by_alternation.p10` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-3_longest_chain.chain_by_alternation.p50` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-3_longest_chain.chain_by_alternation.p90` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-3_longest_chain.chain_by_alternation.stdev` | 0.178686 | 0.178686 | 0.0 | 0.0 | 0.0 |
| `S-3_longest_chain.chain_by_pointer.max` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-3_longest_chain.chain_by_pointer.mean` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-3_longest_chain.chain_by_pointer.min` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-3_longest_chain.chain_by_pointer.p10` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-3_longest_chain.chain_by_pointer.p50` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-3_longest_chain.chain_by_pointer.p90` | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| `S-3_longest_chain.chain_by_pointer.stdev` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `S-4_reply_pointer_coverage.rate` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `admission.checks.B-12_degraded_ratio.detail.degraded` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `admission.checks.B-12_degraded_ratio.detail.ratio` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `admission.checks.B-15_msg_volume.detail.dm_threads` | 152.0 | 152.0 | 0.0 | 0.0 | 0.0 |
| `admission.checks.B-15_msg_volume.detail.messages` | 230.0 | 230.0 | 0.0 | 0.0 | 0.0 |
| `admission.checks.B-15_msg_volume.detail.msg_dm` | 163.0 | 163.0 | 0.0 | 0.0 | 0.0 |
| `admission.checks.B-16_round_dense.detail.max` | 83.0 | 83.0 | 0.0 | 0.0 | 0.0 |
| `admission.checks.B-16_round_dense.detail.min` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `inputs.log_parse.n_bad` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `llm.degraded_ratio` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `meta.channels.dm` | 163.0 | 163.0 | 0.0 | 0.0 | 0.0 |
| `meta.channels.group` | 8.0 | 8.0 | 0.0 | 0.0 | 0.0 |
| `meta.channels.public` | 59.0 | 59.0 | 0.0 | 0.0 | 0.0 |
