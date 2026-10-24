# CYCLE-17 页面截图证据（本期现场渲染，来自 `run_f3_off_n16r60_seed42` 既有真 LLM 日志）

> **生成者**：`report-writer`（周期报告撰写员）｜**渲染完成时刻**：**2026-10-24T08:04:06 / 08:04:09 +0800**（逐图 `png_mtime_iso`，取自本目录 `render_report_CYCLE-17.json` 的 `views[].png_mtime_iso`；回执自身 `generated_at = 2026-10-24T08:04:10+08:00`）
> **与报告的关系**：这 2 张图供 `reports/CYCLE-17-20261024.md` **§4.1** 引用；本文件是该节的**证据侧自解释件**——即使脱离报告单独翻阅本目录，也应能判读「这图哪来的、能说什么、不能说什么」（沿用 `cycle07_shots/README.md` 的既有惯例；起因见 `N-11`：原件丢失后无法自证的教训）。
> **图源纪律**：只用作图源的是**本仓既有、`sha256` 已实算**的历史批 `run.jsonl`（本周期**零跑批、零 LLM 调用**）；每张图独立现截，**未复用任何既有 PNG**，**无拼图 / 无跨批混拼**。
> **重要**：这两张是**真实页面截图**（无头 Chromium 加载 `dialogue.html` 现场截取），**不是** matplotlib 读数图（CYCLE-16 的 `charts/` 属另一类）。**两种物证不得混称。**

## 1. 三重标注（缺一条即为引用错误）

| 项 | 值 |
|---|---|
| **图源批次** | `v2/evidence/run_f3_off_n16r60_seed42/`（主批） |
| **该日志 sha256（全长）** | `19d5cb03de2f0203e3b8aa1c9160adfbef787a159f961713f40b88027931d305`（**sha8 = `19d5cb03`**，已内嵌于 PNG 文件名，由 `render_shots.py` 写入，**不是人工填写**） |
| 日志规模 | **116,336 行** / 55,232,012 B（mtime 2026-10-22 01:01）；`meta.run_sha256` 与本值**相等**（自洽） |
| 该批跑批身份（引自 `meta.json`） | `code_sha = code_sha_end = 6b7ae8a98694dd87d2ea26d14e663705eab69e92`；`seed 42`；`n 16`；`rounds 60`；`events 116,336`；`provider openai_compat`；`model DeepSeek-Flash`；`degraded_calls 0` |
| **派生页面数据** | `threads_CYCLE-17.json` = `1ebc07ee6ea2f77a3b2ceaaff11748f9053d7063805217fab911355001774c25`（由 `gen_threads.py` 现场派生，`run_sha256_in_threads` 与上图源 sha 一致） |
| **渲染回执** | `render_report_CYCLE-17.json` = `b5fb27df4409dd2735fb749e2872841131a7379f870a0c435cf5b843893a2fb8`；**`ok_count = 2` / `fail_count = 0`**；`schema_version render-shots/1.0` |
| **开关真值来源（诚实边界）** | ⚠️ **两批进程均已结束，`/proc/<pid>/environ` 式的开关真值已不可取**。本目录对「该批 = **F-3（情绪呼应）OFF 臂**」的臂身份判定依据**只有间接证据**：①目录命名 `run_f3_off_n16r60_seed42`；②该批 `meta.json.git_dirty_code_files` 含 `M code/life/agent.py`、`?? code/life/emotion_echo.py`、`?? code/config/emotion_echo.json`（F-3 臂改动的痕迹）。**这是间接证据，不是进程环境真值**；`code_sha = 6b7ae8a` 只是当时的 HEAD，**不等于被跑代码的完整指纹**（该批是**脏树批**，见 `reports/CYCLE-17-20261024.md` §3.2 `P6`） |

## 2. 文件清单与 sha256（`sha256sum` / `stat` 实跑）

绝对路径前缀：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/cycle17_shots/`

| 文件 | 视图 | 画幅 | 字节 | sha256 | `png_mtime_iso` |
|---|---|---|---|---|---|
| `CYCLE-17-chat-19d5cb03.png` | 对话流（全量口径，`still=1&multi=1&min=0&sort=turns`） | 1400×900 | 276,265 | `4caf721632e73c21dc1d0cdbd88baa031934afa2f8728f97dc325a3f6fd8f9eb` | 2026-10-24T08:04:06+08:00 |
| `CYCLE-17-rhythm-19d5cb03.png` | 节律·串门（`still=1&multi=1&min=0&view=rhythm`） | 1300×1050 | 282,876 | `2e245f28271dbe58595d8f2ec3490ef0b7f0e6275846b85f6900f240aea0f769` | 2026-10-24T08:04:09+08:00 |
| `threads_CYCLE-17.json` | 派生页面数据 | — | 1,987,628 | `1ebc07ee6ea2f77a3b2ceaaff11748f9053d7063805217fab911355001774c25` | — |
| `render_report_CYCLE-17.json` | 渲染回执（三件套落盘处） | — | 6,930 | `b5fb27df4409dd2735fb749e2872841131a7379f870a0c435cf5b843893a2fb8` | — |

**像素自检档位（逐图落盘于回执 `views[].pixel_selfcheck`，`status` 全 `OK`）**：

| 图 | `distinct_colors` | `top_color_frac` | `non_bg_frac` | 判据 | 结论 |
|---|---|---|---|---|---|
| chat | 23,921 | 0.1417 | 0.5823 | `distinct_colors ≥ 200 且 top_color_frac ≤ 0.99` | `OK`（非空白） |
| rhythm | 22,375 | 0.2620 | 0.4745 | 同上 | `OK`（非空白） |

> **与 `Q-20(残留)` 的关系（必须同屏）**：`shot.py` 自身仍以「最大单色占比 ≥50% 判空白」（`code/frontend/tools/shot.py:164` `_BLANK_FRAC = 0.5`），**本轮未修、属硬冻结区**。本轮回执把它登记进 `policy.blank_check`：`render_shots.py` **另行**落盘自己的像素自检（上表口径），并写明「`shot.py` 该判据对深色 `dialogue.html` 会假红（**实测 80.09% 误判**）」。⇒ **本轮出图成功靠的是「自检档位可查」，不是判据被修**。

> **`code/` 零写入（`policy.code_untouched`）**：服务根为临时目录 + 对 `code/frontend/*` 的符号链接，`sample/<stem>/` 只在临时目录内建，**未在 `code/frontend` 下写入任何文件**（跑完 `git status --porcelain code/` 仍只有 11 个**历史**未跟踪 `code/frontend/sample/dialogue_*/`）。

## 3. 能证明什么 / 不能证明什么

### 能证明什么

1. **这批日志能被前端渲染成可读页面**（存在性事实）：页首自述 `CYCLE-17` / `sha 19d5cb03` / `provider openai_compat` / `seed 42` / `事件 116336` / `消息 510` / `meta 已对齐`；内容非空白（见 §2 像素自检档位）。
2. **对话线程视图里确有逐字对话**（如 `老石 石匠铺` 线程里的编竹篮对白），说明 `threads_CYCLE-17.json` 的派生把 MSG 正确装配成了线程。
3. **节律 / 串门视图可正常渲染**：页面内「哪里最热闹」给出地点计数条、「谁在串门」给出居民当日 `PLACE_MOVE` 轨迹串。

### 不能证明什么

1. **不能**用来证明 `reports/CYCLE-17-20261024.md` §2 的 **P2 一致率**（`74/218 = 33.94%`）——页面**不展示** `ACTIVITY_STARTED.participants`（计划同伴名单）与「实际同处」的对照字段；两者的口径与数据源不同，**不得互代**。
2. **不能**证明「生活气息更好 / 更真实 / 更热闹」一类效果结论：本周期**无判据编号、无闸线、无对照臂**。
3. **不构成对 `Q-20(残留)` 空白判据的修复**（见 §2 末注）。
4. **单批、单视图、无对照**：2 张图来自**同一条** `run.jsonl`，`chat` 与 `rhythm` 是同一批的两个视图，**不是两臂对照**，也**不是跨批稳定性证据**。
5. **图一律不参与任何判据**，也不改变任何既有报告的状态词。

## 4. 复算 / 重渲染命令（唯一入口；全文与期望输出见 `reports/CYCLE-17-20261024.md` 附录 A-3）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# ① 核图源日志身份（期望 = 19d5cb03de2f0203e3b8aa1c9160adfbef787a159f961713f40b88027931d305）
sha256sum v2/evidence/run_f3_off_n16r60_seed42/run.jsonl
wc -l      v2/evidence/run_f3_off_n16r60_seed42/run.jsonl    # 期望 116336

# ② 核本目录三件套（期望 = §2 表内四个 sha256）
sha256sum v2/evidence/cycle17_shots/CYCLE-17-chat-19d5cb03.png \
          v2/evidence/cycle17_shots/CYCLE-17-rhythm-19d5cb03.png \
          v2/evidence/cycle17_shots/threads_CYCLE-17.json \
          v2/evidence/cycle17_shots/render_report_CYCLE-17.json

# ③ 现场重渲染（输入 = 日志，输出到临时目录；**不写 code/**）
python3 tools/metrics/render_shots.py \
    --run-dir v2/evidence/run_f3_off_n16r60_seed42 \
    --batch-id CYCLE-17 --outdir /tmp/cycle17_shots --views chat,rhythm --timeout 180
# 期望：ok_count=2 / fail_count=0 / rc=0

# ④ 逐图像素自检档位（渲染器无关的口径，重渲染后请核这一项，不要按 PNG 逐字节比）
python3 -c "import json;r=json.load(open('/tmp/cycle17_shots/render_report_CYCLE-17.json'));\
print([(v['view'],v['pixel_selfcheck']['distinct_colors'],v['pixel_selfcheck']['top_color_frac'],v['pixel_selfcheck']['status']) for v in r['views']])"
```

> **PNG 字节级一致性**依赖 Chromium 版本与字体环境；不同环境下 sha 不同属「渲染器差异」而非「证据漂移」——此时以**像素自检档位 + 页面可见内容**核对（同 `reports/CYCLE-17-20261024.md` 附录 A-3 的注）。

## 5. 已知边界

- 图源日志受 `.gitignore:8`（`**/*.jsonl`）排除 ⇒ **不在 git 对象里**（`Q-17` / `N-7`）：可**验 sha**、可按 §4 命令**重渲染**，但**不可从零重建**该批日志。
- `threads_CYCLE-17.json`（约 1.9 MB）是**派生件**，可由 §4-③ 从日志重新派生；它入库存的是「本次渲染实际使用的输入」的身份锚，不是唯一真源。
- 本批是**脏树批**（`meta.git_dirty_code_files` 非空）⇒ 其 `code_sha` 只到 HEAD 层面，**引用该批任何读数时都必须同屏声明「脏树批」**（`P6`）。
- `shot.py` 侧另有 T282 观察哨自报 `blank_cumulative 16/301`（跨次累计空白/总取证，**仅留痕、不抑制、不告警**）；本轮两张图 `blank_retries 均为 0/2`。
