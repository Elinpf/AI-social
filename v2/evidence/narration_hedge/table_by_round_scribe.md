| # | 指标 | 单位 | OFF | ON | 增量 | 分母(OFF/ON) | 证据级 | 来源 |
|---|---|---|---|---|---|---|---|---|
| N-1 | 旁白覆盖率（含成对括号的消息占比） | per-message | 0.00% | 92.67% | +92.67pp | 191 / 191 | evidence | narration_stats() |
| N-2 | 旁白块总数 | per-block | 0 | 196 | +196 | — | evidence | narration_stats() |
| N-3 | 旁白去重率（unique/total） | per-block | None | 98.47% | — | 0 / 196 | evidence | narration_stats() |
| N-4 | 旁白字符占正文比例 | per-message | 0.00% | 28.76% | +28.76pp | — | evidence | narration_stats() |
| F-1 | 非功能性闲聊占比 | per-message | 77.49% | 74.87% | -2.62pp | 191 / 191 | evidence | d5 F-1_chatter |
| F-2 | 话题漂移率（content 口径） | per-adjacent-pair | 68.00% | 69.60% | +1.60pp | 125 / 125 | evidence | d5 F-2_content_drift（F-2_topic_drift 为 LEGACY_DEAD_RULER，不引用） |
| F-2b | 多话题线程占比 | per-thread | 0.00% | 0.00% | +0.00pp | 66 / 66 | evidence | d5 F-2b_multi_topic_threads |
| F-3 | 情绪呼应率 | per-adjacent-pair | 9.09% | 0.00% | -9.09pp | 11 / 1 | probe（分母<30） | d5 F-3_emotion_echo |
| F-4 | 修复闭环率 | per-event | 0.00% | 0.00% | +0.00pp | 8 / 1 | probe（分母<30） | d5 F-4_tension_repair |
| F-5 | 习惯强度 | per-agent | 0.00% | 0.00% | +0.00pp | 16 / 16（1 天，<3 天 ⇒ 结构性为 0） | probe | d5 F-5_habit_repetition |
| F-6 | 跨天记忆引用率 | per-message | 5.76% | 17.28% | +11.52pp | 191 / 191 | evidence | d5 F-6_crossday_memory |
| F-7 | 越界提及率（F-7a 提及层） | per-message | 9.95% | 14.14% | +4.19pp | 191 / 191 | evidence | d5 F-7a_offscreen_mention（F-7b 需 judge，本轮未跑） |
| L-7 | 8-gram 撞车率（重复率守卫） | per-message | 21.47% | 29.84% | +8.38pp | — | evidence | d5 L_wording.L-7 |

**hedge_verdict = `swap_only`**

旁白覆盖率大幅上升，但 F 指标无同向改善：F-1/F-3/F-4 passive 下降或分母坍缩，F-6 虽升 +11.52pp，但 8-gram 撞车率同步恶化 +8.38pp ⇒ 按 R4:89 陷阱2 不计为改善；F-7a 越界提及反向上升。结论：旁白只带来表层景物/动作描写，**不算生活气息改善**。
