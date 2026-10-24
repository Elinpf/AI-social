# CYCLE-24 页面截图证据：D2.8 **B 臂 seed43**（`run_d28_B_n16r60_seed43`）真实渲染

> **生成者**：`证据与报告审计专家`（member `evidence-auditor`）｜**取证时刻**：`2026-10-24T22:46:14 — 22:46:20 +08:00`（逐图 `png_mtime_iso` 见 `render_report_CYCLE24-B.json` 的 `views[].png_mtime_iso`）
> **与报告的关系**：供 `reports/CYCLE-24-20261024.md` §五「素材」引用。本文件是**证据侧自解释件**（格式沿用 `v2/evidence/cycle23_shots/README.md`、`cycle21_shots`、`round01_life_texture_shots` 的惯例）——脱离报告单翻本目录，也应能判读「图哪来的、能说什么、不能说什么」。
> **图源纪律**：图源是本轮唯一被判定**合规**的 B 臂真 LLM 批日志（`feat/d28-narration-quota@c3ec2668`），`sha256` 现场实算并与 `meta.json` 自洽；本轮**零跑批、零 LLM 调用**；3 张图**本轮现截**（`22:46:14 — 22:46:19`），**未复用** `cycle23_shots` / `d12h_shots` / `round01_life_texture_shots` 等任何既有 PNG，无拼图、无跨批混拼。
> **物证类别**：3 张均为**真实页面截图**（无头 Chromium 加载 `code/frontend/dialogue.html` 现场截取），**不是** matplotlib 读数图，两类物证不得混称。
> **纪律红线**：本文件**不给任何百分数、不给任何效果结论**，截图**不参与任何指标判定**（详见 §5）。

---

## 1. 双重标注：每张图必须能回答「哪条日志 + 哪条命令」

| 项 | 取值 |
|---|---|
| 图源批次（run 目录，绝对路径） | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d28-narration-quota/v2/evidence/run_d28_B_n16r60_seed43/` |
| 臂身份 | B 臂（D2.8 narration-quota，worktree `.worktrees/d28-narration-quota`，分支 `feat/d28-narration-quota`） |
| 批次标签（`--batch-id`） | `CYCLE24-B` |
| 日志 sha256（全长） | `3c1736bc0bf2d1a92790a1b9c791d7882c10cc827c60f6c41dbf84a2681eacf9`（sha8 `3c1736bc`） |
| `meta.run_sha256` 是否等于上值 | **相等**（`meta.derived_from_log_sha256` 同值；本机 `sha256sum` 实测亦同值，三方自洽） |
| 日志规模 | `116,346` 行（`wc -l`）/ `56,570,932` B |
| 跑批身份（引自 `meta.json`） | `code_sha = code_sha_end = c3ec266869efbf6cfe0e0064e795b6607cb4e62b`；`n=16`；`rounds=60`；`seed=43`；provider `openai_compat`；model `DeepSeek-Flash`；`llm_calls 2878`；`degraded_calls 0`；`started_at 2026-10-24T21:58:55+08:00`；`finished_at 2026-10-24T22:42:34+08:00` |
| 派生页面数据 | `threads_CYCLE24-B.json` = `76e39f19f95ade9a64b08fb8573c1d558f5999fba8bde3214133f53738b90cf2`（2,175,145 B；`gen_threads.py` 现算：`threads=169 messages=510 multi_turn=88 ge3=77`） |
| 渲染回执 | `render_report_CYCLE24-B.json` = `402571d6b82933be2758da152e05e34301d47adb09e853cb8b918fe83792114e`（10,132 B）；`ok_count=3` / `fail_count=0` / `generated_at 2026-10-24T22:46:20+08:00` |

> 回执字段 `run_sha256_in_threads = 3c1736bc0bf2d1a92790a1b9c791d7882c10cc827c60f6c41dbf84a2681eacf9` **等于**上表日志 sha（实测 `True`）⇒「PNG 文件名里的 sha8 `3c1736bc`」是脚本从日志实算写进 `threads.json` 再派生到文件名的，**不是人工填写**。

## 2. 文件清单与 sha256（3 张 PNG + 2 个支撑件）

| 文件 | 视图 / 角色 | 画幅 | 字节 | sha256 | `png_mtime_iso` |
|---|---|---|---|---|---|
| `CYCLE24-B-chat-3c1736bc.png` | 对话流（`still=1&multi=1&min=0&sort=turns`） | 1400×900 | 289,249 | `eb8631462b05d6878526b55d6dbd2f7d4c297582daef12ca3c8226391af48a2c` | 2026-10-24T22:46:14+08:00 |
| `CYCLE24-B-rhythm-3c1736bc.png` | 节律·串门（`still=1&multi=1&min=0&view=rhythm`） | 1300×1050 | 283,166 | `6672e8426d841291e4ceeae19317d1e981c9b40d2931fc69eb429b532b1021f0` | 2026-10-24T22:46:17+08:00 |
| `CYCLE24-B-spread-3c1736bc.png` | 闲话怎么传开（`still=1&multi=1&min=0&view=spread`） | 1400×1000 | 179,355 | `36981485f8a7ae794a14d517da964667a601c4fb96293dbb99398802dcfef846` | 2026-10-24T22:46:19+08:00 |
| `threads_CYCLE24-B.json` | 派生页面数据 | — | 2,175,145 | `76e39f19f95ade9a64b08fb8573c1d558f5999fba8bde3214133f53738b90cf2` | — |
| `render_report_CYCLE24-B.json` | 渲染回执（三件套 + 像素自检逐张） | — | 10,132 | `402571d6b82933be2758da152e05e34301d47adb09e853cb8b918fe83792114e` | — |
| `README.md` | 本文件 | — | 见 `stat` | 见 `sha256sum v2/evidence/d28_shots/README.md`（自引用不写死） | — |

**像素自检档位（回执 `views[].pixel_selfcheck`，3 张 `status` 全 `OK`）**：

| 图 | `distinct_colors` | `top_color_frac` | `non_bg_frac` | 结论 |
|---|---|---|---|---|
| chat | 24,423 | 0.1417 | 0.5824 | `OK`（非空白） |
| rhythm | 22,387 | 0.2620 | 0.4746 | `OK`（非空白） |
| spread | 15,715 | 0.5683 | 0.1774 | `OK`（非空白） |

判据（`tools/metrics/render_shots.py::pixel_selfcheck` 写死）：`distinct_colors ≥ 200 且 top_color_frac ≤ 0.99 ⇒ OK`（深色 UI 不按单色占比判死；`shot.py` 自身的「单色 ≥50% 判空白」对深色 `dialogue.html` 属已知假红，故调用一律带 `--no-blank-check`）。

## 3. 四段可复算 sha 链（日志 → threads → 回执 → PNG）

| 段 | 对象 | sha256（全长） | 校验方式 |
|---|---|---|---|
| ① 日志 | `…/run_d28_B_n16r60_seed43/run.jsonl` | `3c1736bc0bf2d1a92790a1b9c791d7882c10cc827c60f6c41dbf84a2681eacf9` | `sha256sum`；且 `meta.run_sha256` / `meta.derived_from_log_sha256` 同值 |
| ② 派生 | `threads_CYCLE24-B.json` | `76e39f19f95ade9a64b08fb8573c1d558f5999fba8bde3214133f53738b90cf2` | 由 ① 现算（`gen_threads.py`）；回执 `threads_json_sha256` 同值 |
| ③ 回执 | `render_report_CYCLE24-B.json` | `402571d6b82933be2758da152e05e34301d47adb09e853cb8b918fe83792114e` | `sha256sum`；内部 `log_sha256 == run_sha256_in_threads` 实测 `True`、`ok_count=3`/`fail_count=0` |
| ④ 输出 | 3 张 PNG | 见 §2 表 | 回执 `pngs[].png_sha256` 与磁盘 `sha256sum` **逐张相等**（实测） |

**链条合拢点**：② 内 `source.run_sha256 = ①`；③ 内 `run_sha256_in_threads = ①`；④ 的 PNG 名含 ① 的 sha8 `3c1736bc`，且 ④ 的 sha 由 ③ 逐张登记 ⇒ 任一段被改动，链条即断，可被第三方复算发现。

**命令原文（首采，逐字）**：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
PYTHONDONTWRITEBYTECODE=1 /opt/openjiuwen/workswarm-venv/bin/python3 -B tools/metrics/render_shots_extra.py \
  --run-dir /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d28-narration-quota/v2/evidence/run_d28_B_n16r60_seed43 \
  --batch-id CYCLE24-B --outdir v2/evidence/d28_shots \
  --views chat,rhythm,spread --timeout 240
# → rc=0, ok_count=3, fail_count=0
```

等价的展开形态（`gen_threads → 本地静态服务 → shot.py`，命令原文见回执 `views[].triplet`）：

```bash
# ② gen_threads
/opt/openjiuwen/workswarm-venv/bin/python3 code/frontend/tools/gen_threads.py \
  --log …/.worktrees/d28-narration-quota/v2/evidence/run_d28_B_n16r60_seed43/run.jsonl \
  --meta …/.worktrees/d28-narration-quota/v2/evidence/run_d28_B_n16r60_seed43/meta.json \
  --out v2/evidence/d28_shots/threads_CYCLE24-B.json --label CYCLE24-B
# ③ 本地静态服务：ThreadingHTTPServer daemon 线程，端口由内核分配，只走 http://，无 file://
# ④ shot.py
/opt/openjiuwen/workswarm-venv/bin/python3 code/frontend/tools/shot.py \
  --url "http://127.0.0.1:<port>/dialogue.html?still=1&multi=1&min=0&sort=turns&data=sample/dialogue_CYCLE24-B/threads.json" \
  --out v2/evidence/d28_shots/CYCLE24-B-chat-3c1736bc.png \
  --width 1400 --height 900 --timeout 240.0 --retry-blank 2 --no-blank-check
```

**服务生命周期**：服务由 `render_shots.py` 内部起，`finally` 分支 `shutdown()` + `shutil.rmtree(tmp)`；未 kill 任何外部进程、未在 `code/frontend/` 落文件（渲染后 `git status --short code/frontend` 除既有 `?? sample/dialogue_*` 外无新增）。

## 4. 本轮登记的页面派生读数（只登记、不判定）

```
threads=169  messages=510  multi_turn=88  ge3=77
```

| 项 | 值 | 与日志对账 |
|---|---|---|
| `messages` | 510 | 与 `meta.units.msg_counts`（`MSG_DM 455 + MSG_PUBLIC 55`）/ 本目录 `tools/d28/recompute_d28_prereg.py` 的 `n_msgs=510` **一致** |
| `threads` | 169 | 与复算脚本 `n_threads_threadid=169` **一致** |

> 以上只是「页面显示的数与日志同源」，**不作臂间比较、不作效果推断**。

## 5. 这 3 张图**能说**什么 / **不能**说什么

| 能说 | 不能说 |
|---|---|
| 该批日志确为**真 LLM 批**（`provider=openai_compat`、`model=DeepSeek-Flash`、`degraded_calls=0`），页面渲染自该批派生数据 | 不能说「旁白机制有效」——机制/效果的判定只由 `tools/d28/recompute_d28_prereg.py` 的读数与 `v2/refs/D28-F2prime-resolution.md` 的口径决定，**截图不进判据** |
| 页面能看到具体对话文本、线程参与者、时间节律与传播结构 | 不能说「多数/普遍/典型」——3 张图是**单批单时刻的页面视图**，抽样性质，不得据此推断分布 |
| 图与日志/派生件/回执的 sha 链**四段闭合**，可被第三方重算复核 | 不能把本图与 `cycle23_shots`（seed42）的图混拼成一组证据，也不得用来替代任何一批的读数 |
| 图是**本轮现渲**（22:46:14–22:46:19），不是历史图顶替 | 不能宣称「视觉上更自然/更有生活气息」——那需要人评或 judge 证据，本目录没有 |

## 6. 复现与校验命令（第三方复核用）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
sha256sum .worktrees/d28-narration-quota/v2/evidence/run_d28_B_n16r60_seed43/run.jsonl \
          v2/evidence/d28_shots/threads_CYCLE24-B.json \
          v2/evidence/d28_shots/render_report_CYCLE24-B.json \
          v2/evidence/d28_shots/*.png
# 应分别等于 §2/§3 表中的值；PNG 三个 sha 应等于回执 pngs[].png_sha256
```
