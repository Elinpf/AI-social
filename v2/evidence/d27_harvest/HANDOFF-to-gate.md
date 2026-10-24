# D2.7 交付交接给 evidence-gate（life-dim-dev）

## 1. 复算产物
- `v2/evidence/d27_harvest/d27_gates.json`（+ 同目录 `d12c_c_b.json` / `p1_count_c_b.json` / `d27_metrics_c_b.json` / `l15_c_b.json` / `dm_C.json` / `dm_B.json` / `shape_C.json` / `shape_B.json`）
- 复算器：`v2/evidence/d27_harvest/d27_gates.py`（全部 shell 主树官方工具）
- C-vs-C 自检：`v2/evidence/d27_harvest/_selftest_c_vs_c/`（Δ 全 0、169=169=169、ge6 双边 52/169）
- `d27_metrics.py` 原在 worktree 未入库，已 copy 到 `v2/evidence/d27_harvest/d27_metrics.py`，sha256 两边同为 `46d527d8e70164966f3bbfaf5e80248284966b727567279108e5907d5b589d65`

## 2. 收批字段（B 臂）
| 字段 | 值 |
|---|---|
| `finished_at` | 2026-10-24T16:23:24+08:00 |
| `started_at` | 2026-10-24T15:32:28+08:00 |
| `duration_sec` | 3056 |
| `events` | 115545（= `wc -l`） |
| `code_sha` / `code_sha_end` | c74985050b86f31c21f4ab90da8d9244b3410251 |
| `git_dirty_code_files` | [] |
| `llm_calls` | 2869 |
| tokens | in 297931 / out 273773 / total **571704**（C: 291359+262570=**553929**） |
| provider | `provider_guard.ok=true`，`by_provider={openai_compat:2869}`，`degraded=0` |
| `msg_counts` | DM 449 / PUBLIC 53 |
| `run_batch.rc=9` / `run_batch.end` 14:59:38 | **14:59 并发闸（`[preflight] FAIL reasons=concurrency:run_batch=1`）遗留**，本批由 `run_batch.sh` 直拉、写 rc 的是 `launch_arm_d27.sh` 的 trap ⇒ 不会生成/覆盖；未引用为证据 |

## 3. 你问的匿名旁白数（`payload.from` 为空的 MSG）
| 项 | C | B |
|---|---|---|
| from 为空的 MSG | 55（全为 MSG_PUBLIC） | **53**（全为 MSG_PUBLIC） |
| 它们构成的线程数 | 55 | **53** |
| 单条消息线程 | 81 | 81 |
| MSG_DM 线程 | 114 | 117 |
| 全量线程（三方对账） | 169 = 169 = 169 | 170 = 170 = 170 |

另记：**B 的旁白不是独立匿名线程**，是说话人自己消息的句首括号（502 条 MSG 全有 `from`），旁白放开未改变匿名线程构成；55→53 只是 PUBLIC 随总消息量（−1.57%）同步下降。

## 4. ⚠ Q3 分歧（请裁决）
`d27_gate_verification.md:58` 把 `F-2′ 63.34→66.87（+3.53pp）` 记为 **✅（降≤2pp）**。
按预登记 §3「升≤2pp」与 d25a 实操读法：**+3.5244pp > 2.0pp ⇒ 应为 ❌（内容漂移）**；我的 `d27_gates.json` 中 `gates.Q3.pass=false`。
另注 `denominator_adjacent_pairs` C 341 / B 332，按 d25a 口径该读数只宜作方向参考。
**不影响总判定**（T 击穿 + P 未达已独立成立）。若你维持 ✅ 请给理由，我按裁决改报告并留痕。

## 5. mock 第三项（已回填 `v2/evidence/d27_mock_verification.md §3`，补测 16:29–16:30，晚于 B 收批）
- 如实 mock 批 n=6 r=12：`paren_rate=0.00%`，0.96s，events=3016 —— **结构性 0，不是机制失败**：`freeze/providers.py:85-90` 的 `_DIALOGUE_POOL` 4 句**无括号**，`_mock_nl_text():115-121` 按 prompt 哈希取池内下标，prompt 不参与生成 ⇒ 该判据在 mock 路径**不可测**，当"未生效"是假阴性。
- 替代测试（可判定）：注入 responder 返回带括号台词 → **`paren_rate=100.00%`，37/37 未被剥落**，0.81s ⇒ mock 链路无剥落环节。
- 固化产物：`v2/evidence/d27_mock/`（`d27_mock_paren_inject.py`、`mock_pool_run.jsonl`、`mock_inject_run.jsonl`、`mock_pool_metrics.json`、`mock_inject_metrics.json`）。
- 两层不可互替：机制层（mock 链路/不剥落）vs 运行期层（真 LLM 下 prompt 真进模型：dialogue `tokens_in` 292.04→310.80）。

## 6. 截图（`v2/evidence/d27_shots/`，同 thread `TH-P009-P008-24`）
| 文件 | 臂 | 尺寸 | 字节 | 空白检测 |
|---|---|---|---|---|
| `d27-C-thread-focus-1fbb9ef5.png` | C | 1400×1000 | 300,712 | blank_retries 0/2；max_color_frac 27.56%；brightness 36.2 |
| `d27-B-thread-focus-87e233c4.png` | B | 1400×1000 | 277,251 | 0/2；30.22%；33.7 |
| `d27-B-chat-multi-87e233c4.png` | B | 1400×900 | 289,208 | 0/2；29.92%；35.4 |

脚本 `v2/evidence/d27_shots/render_d27_shots.sh`，日志 `render_wrap.log`；shot.py **未传 `--no-blank-check`**。已用视觉模型复核 B 图可逐字读出 6 轮对话。报告含同线程 6 轮逐字对照表。

## 7. 报告
`reports/D27-旁白放开.md`（= `v2/evidence/d27_result.md`，同一内容两处落盘）。判定词「**作废（台词被旁白挤短）**」，开头即讲透；附录 A 保留污染基线翻转向（Q2 +7.90pp 判无效、T 仍破、总判定不变）。

## 8. 关键数字（C 本批现算 → B）
paren 0.00→**100.00%**｜P1 二元 93.53→**96.41%（+2.88pp）**｜P1_count_mean 3.1941→**3.4024（+6.52%）**｜L-15 4.31→**4.18（−0.13pp）**｜L-7 25.4902→**28.4861（+2.9959pp，余量 0.0041pp）**｜F-2′ 63.3431→**66.8675（+3.5244pp）**｜`len_p50_excl` 41.0→**26.0（−36.59%）**｜n_msgs 510→502（−1.57%）｜n_threads 169→170（+0.59%）｜ge6 30.77→**29.41%**｜calls 2878→2869（−0.31%）｜tokens 553,929→571,704（+3.21%）
