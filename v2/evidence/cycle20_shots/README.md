# CYCLE-20 页面截图证据（取自本轮引用的真 LLM 批 `run_d25a_C_n16r60_seed42`）

> **生成者**：`evidence-collector`（证据取证专家）｜**渲染时刻**：`2026-10-24T12:32:02 / 12:32:05 +0800`（逐图 `png_mtime_iso` 见 `render_report_CYCLE-20C.json` 的 `views[].png_mtime_iso`）
> **与报告的关系**：这 2 张图供 `reports/CYCLE-20-20261024.md` §4 引用；本文件是**证据侧自解释件**（沿用 `v2/evidence/cycle17_shots/README.md` 的惯例）——脱离报告单独翻阅本目录，也应能判读「图哪来的、能说什么、不能说什么」。
> **图源纪律**：只用作图源的是**本仓既有、`sha256` 已实算**的真 LLM 批日志（本轮**零跑批、零 LLM 调用**）；每张图**本轮现截**，未复用任何既有 PNG，无拼图、无跨批混拼。
> **物证类别**：这 2 张是**真实页面截图**（无头 Chromium 加载 `code/frontend/dialogue.html` 现场截取），**不是** matplotlib 读数图，两类物证不得混称。

## 1. 三重标注（缺一条即为引用错误）

| 项 | 值 |
|---|---|
| **图源批次** | `.worktrees/d25a-wiring/v2/evidence/run_d25a_C_n16r60_seed42/`（D2.5a 的 **C 基线臂**，无 override） |
| **该日志 sha256（全长）** | `bd2b36d8f53a9111d3fdcdc7fa1d6c19541892726550214785de0a1a34f319c1`（sha8 = `bd2b36d8`，由 `render_shots.py` 写进 PNG 文件名，非人工填写） |
| 日志规模 | **116,336 行** / 56,544,348 B；`meta.run_sha256` 与本值**相等**（自洽） |
| 该批跑批身份（引自 `meta.json`） | `code_sha = code_sha_end = e2e7131a388d141b26763af44c0e08287bdccf33`；`seed 42`；`rounds 60`；`events 116,336`；`provider openai_compat`；`model DeepSeek-Flash`；`llm_calls 2878`；`duration_sec 3094`；`degraded_calls 0`；`overrides_declared []`（**确为 C 基线**）；`git_dirty_code_files []` |
| **派生页面数据** | `threads_CYCLE-20C.json` = `02b072fecd86d9b8418d0bd4d27c24c037d6974e26316554ca6d2067f943ebd9`（`gen_threads.py` 现算，`run_sha256_in_threads` 与上图源 sha 一致） |
| **渲染回执** | `render_report_CYCLE-20C.json` = `5c174a30a54de0e8424e458d167144a730e49067e959b4c956a816e44ca4927b`；`ok_count = 2` / `fail_count = 0`；`schema_version render-shots/1.0` |

## 2. 文件清单与 sha256

| 文件 | 视图 | 画幅 | 字节 | sha256 | `png_mtime_iso` |
|---|---|---|---|---|---|
| `CYCLE-20C-chat-bd2b36d8.png` | 对话流（`still=1&multi=1&min=0&sort=turns`） | 1400×900 | 285,348 | `56db297d9d2ee3d2204033e296fdc94f033fcd754cddd5eb2a511c860c7a8799` | 2026-10-24T12:32:02+08:00 |
| `CYCLE-20C-rhythm-bd2b36d8.png` | 节律·串门（`still=1&multi=1&min=0&view=rhythm`） | 1300×1050 | 283,302 | `78296263567a3b218080274f9e95227403a2595d123d36e0379379a2c53863db` | 2026-10-24T12:32:05+08:00 |
| `threads_CYCLE-20C.json` | 派生页面数据 | — | 2,155,478 | `02b072fecd86d9b8418d0bd4d27c24c037d6974e26316554ca6d2067f943ebd9` | — |
| `render_report_CYCLE-20C.json` | 渲染回执 | — | 6,490 | `5c174a30a54de0e8424e458d167144a730e49067e959b4c956a816e44ca4927b` | — |

**像素自检档位（回执 `views[].pixel_selfcheck`，`status` 全 `OK`）**：

| 图 | `distinct_colors` | `top_color_frac` | `non_bg_frac` | 结论 |
|---|---|---|---|---|
| chat | 24,287 | 0.1417 | 0.5824 | `OK`（非空白） |
| rhythm | 22,419 | 0.262 | 0.4746 | `OK`（非空白） |

> `shot.py` 自身仍以「最大单色占比 ≥50% 判空白」（`code/frontend/tools/shot.py`），对深色 `dialogue.html` 会假红（历史实测误判 80.09%）；本目录以 `render_shots.py` 的像素自检档位为准，**该判据本轮未修**。

## 3. 能证明什么 / 不能证明什么

### 能证明
1. 该 `run.jsonl`（`bd2b36d8…`）能被前端渲染成**可读、非空白**页面；
2. 对话线程视图里确有**逐字对话**，节律视图确有地点计数与 `PLACE_MOVE` 轨迹；
3. 图源是**真 LLM 批**（`provider openai_compat`、`degraded_calls 0`）。

### 不能证明
1. **不能**证明 P2 一致率 `74/218 = 33.94%` —— 页面**不展示** `ACTIVITY_STARTED.payload.participants` 与「实际同处」的对照字段；
2. **不能**证明任何「更生活 / 更真实 / 更热闹」的效果结论：本周期**无判据编号、无闸线、无对照臂**；
3. **不构成臂对照**：两张图来自**同一条** `run.jsonl` 的两个视图，C 臂是**基线**，且 A 臂（配额 2→3）取证据时**仍在跑**；
4. **图不参与任何判据**，也不改变任何既有报告的状态词。

## 4. 复算 / 重渲染命令

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# ① 核图源日志身份（期望 bd2b36d8d53a9111d3fdcdc7fa1d6c19541892726550214785de0a1a34f319c1）
sha256sum .worktrees/d25a-wiring/v2/evidence/run_d25a_C_n16r60_seed42/run.jsonl
wc -l      .worktrees/d25a-wiring/v2/evidence/run_d25a_C_n16r60_seed42/run.jsonl   # 期望 116336

# ② 核本目录三件套
sha256sum v2/evidence/cycle20_shots/*

# ③ 现场重渲染（输出到临时目录，不写 code/）
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/metrics/render_shots.py \
  --run-dir .worktrees/d25a-wiring/v2/evidence/run_d25a_C_n16r60_seed42 \
  --batch-id CYCLE-20C --outdir /tmp/c20_shots --views chat,rhythm --timeout 240
# 期望：ok_count=2 / fail_count=0 / rc=0
```

> **PNG 字节级一致性**依赖 Chromium 版本与字体环境；不同环境下 sha 不同属「渲染器差异」，此时以**像素自检档位 + 页面可见内容**核对。

## 5. 已知边界

- 图源日志受 `.gitignore`（`**/*.jsonl`）排除 ⇒ **不在 git 对象里**：可验 sha、可重渲染，但不可从零重建该批日志。
- 该批日志位于 **worktree**（`.worktrees/d25a-wiring/`）而非主树，且**未提交**；本目录的 `threads_CYCLE-20C.json` + 回执是它在主树里的**可追溯锚**。
- `meta.engine_version` 为 `null`（meta 生成缺陷）；其指纹等价性由裁决件 `v2/evidence/d25a_C_arm_reuse_ruling.md:25,32` 的 `code/config` 逐字节比对补证。
- 本目录 4 个文件**本轮新建、未跟踪**，是否随 CYCLE-20 报告入库由 leader 决定。
