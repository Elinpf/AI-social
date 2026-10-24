# 页面截图证据：C 基线批 `run_d27_C_n16r60_seed42`（「公开场合接话」维度的对话界面物证）

> **生成者**：`report-delivery-engineer`（报告与交付工程师）｜**取证时刻**：`2026-10-25T00:08:50 — 00:08:52 +08:00`（逐图 `png_mtime_iso` 见 `render_report_PUBTALK-C.json`）
> **与报告的关系**：供 `reports/R24-public-talk-baseline.md`「素材」节引用。本文件是**证据侧自解释件**（格式沿用 `v2/evidence/d28_shots/README.md`、`round01_life_texture_shots` 的惯例）——脱离报告单翻本目录，也应能判读「图哪来的、能说什么、不能说什么」。
> **图源纪律**：图源是本维度基线所依据的**同一份日志**（`run_d27_C_n16r60_seed42/run.jsonl`，`sha256 = 1fbb9ef5…`），本轮**零跑批、零 LLM 调用**，2 张图**本轮现截**，未复用任何既有 PNG（`d27_shots` / `d28_shots` / `cycle21_shots` 等一律未取用），无拼图、无跨批混拼。
> **物证类别**：2 张均为**真实页面截图**（无头 Chromium 加载 `code/frontend/dialogue.html` 现场截取），**不是** matplotlib 读数图，两类物证不得混称。
> **纪律红线**：本目录**不给任何百分数、不给任何效果结论**，截图**不参与任何指标判定**。**免责说明（原文级，不得改写）**：**该图是对话界面物证，不是公开接话指标的证据**。

---

## 1. 双重标注：每张图必须能回答「哪条日志 + 哪条命令」

| 项 | 取值 |
|---|---|
| 图源批次（run 目录，绝对路径） | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d27_C_n16r60_seed42/` |
| 臂身份 | **C 基线臂**（master 树，D2.7/D2.8 旁白开关关；`meta.code_sha = f2bf606b…`） |
| 批次标签（`--batch-id`） | `PUBTALK-C` |
| 日志 sha256（全长） | `1fbb9ef5161fd07aa68fcc9fc4038f104ff18b56383a2fc6b31bb3cb5486a188`（sha8 `1fbb9ef5`） |
| `meta.run_sha256` 是否等于上值 | **相等**（`meta.derived_from_log_sha256` 同值；`sha256sum` 本机实测亦同值，三方自洽） |
| 日志规模 | `116,308` 行（`wc -l` = `meta.events`）/ `56,531,099` B |
| 跑批身份（引自 `meta.json`） | `code_sha = code_sha_end = f2bf606bf5f6c362a7d4d34b9177f3210d43aabf`；`n=16`；`rounds=60`；`seed=42`；provider `openai_compat`；model `DeepSeek-Flash`；`llm_calls 2878`；`llm_cached 1425`（`cached_ratio 0.4951`）；`degraded_calls 0`；`started_at 2026-10-24T14:04:39+08:00`；`finished_at 2026-10-24T14:59:23+08:00`；`duration_sec 3284` |
| 消息构成（`meta.msg_counts`） | `MSG_DM 455` + `MSG_PUBLIC 55` = `510` |
| 派生页面数据 | `threads_PUBTALK-C.json` = `15e9293bf5e443d423ea7fd2b063cc85bca7a8fe5af409aab62587cced6ad47c`（2,153,050 B；`gen_threads.py` 现算：`threads=169 messages=510 multi_turn=88 ge3=77`） |
| 渲染回执 | `render_report_PUBTALK-C.json` = `dfb5cef6838062793a57723c561c2c8224898e1ab103f15549a9dbbbaf5d03b8`（6,970 B）；`ok_count=2` / `fail_count=0` / `generated_at 2026-10-25T00:08:54+08:00` |

> 回执字段 `run_sha256_in_threads = 1fbb9ef5…` **等于**上表日志 sha ⇒「PNG 文件名里的 sha8 `1fbb9ef5`」是脚本从日志实算写进 `threads.json` 再派生到文件名的，**不是人工填写**。

## 2. 文件清单与 sha256（2 张 PNG + 2 个支撑件）

| 文件 | 视图 / 角色 | 画幅 | 字节 | sha256 | `png_mtime_iso` |
|---|---|---|---|---|---|
| `PUBTALK-C-chat-1fbb9ef5.png` | 对话流（`still=1&multi=1&min=0&sort=turns`） | 1400×900 | 279,576 | `31fd3ad0666ba22997de107614a50083de1312477ea8063c52b51e578d1a401b` | 2026-10-25T00:08:50+08:00 |
| `PUBTALK-C-rhythm-1fbb9ef5.png` | 节律·串门（`still=1&multi=1&min=0&view=rhythm`） | 1300×1050 | 282,921 | `2eb8c76b7a9bc54d3b3069ad5a812f7cf53d7a83e667690ed5f22cdb0b0633ab` | 2026-10-25T00:08:52+08:00 |
| `threads_PUBTALK-C.json` | 派生页面数据 | — | 2,153,050 | `15e9293bf5e443d423ea7fd2b063cc85bca7a8fe5af409aab62587cced6ad47c` | — |
| `render_report_PUBTALK-C.json` | 渲染回执（三件套 + 像素自检逐张） | — | 6,970 | `dfb5cef6838062793a57723c561c2c8224898e1ab103f15549a9dbbbaf5d03b8` | — |
| `README.md` | 本文件 | — | 见 `stat` | `sha256sum v2/evidence/public_talk_shots/README.md`（自引用不写死） | — |

**像素自检档位（回执 `views[].pixel_selfcheck`，2 张 `status` 全 `OK`）**：

| 图 | `distinct_colors` | `top_color_frac` | `non_bg_frac` | 结论 |
|---|---|---|---|---|
| chat | 24,015 | 0.1417 | 0.5824 | `OK`（非空白） |
| rhythm | 22,374 | 0.2620 | 0.4746 | `OK`（非空白） |

判据（`tools/metrics/render_shots.py::pixel_selfcheck` 写死）：`distinct_colors ≥ 200 且 top_color_frac ≤ 0.99 ⇒ OK`（深色 UI 不按单色占比判死；`shot.py` 自身的「单色 ≥50% 判空白」对深色 `dialogue.html` 属已知假红，故调用一律带 `--no-blank-check`）。

## 3. 四段可复算 sha 链（日志 → threads → 回执 → PNG）

| 段 | 对象 | sha256（全长） | 校验方式 |
|---|---|---|---|
| ① 日志 | `v2/evidence/run_d27_C_n16r60_seed42/run.jsonl` | `1fbb9ef5161fd07aa68fcc9fc4038f104ff18b56383a2fc6b31bb3cb5486a188` | `sha256sum`；且 `meta.run_sha256` / `meta.derived_from_log_sha256` 同值 |
| ② 派生 | `threads_PUBTALK-C.json` | `15e9293bf5e443d423ea7fd2b063cc85bca7a8fe5af409aab62587cced6ad47c` | 由 ① 现算（`gen_threads.py`）；回执 `threads_json_sha256` 同值 |
| ③ 回执 | `render_report_PUBTALK-C.json` | `dfb5cef6838062793a57723c561c2c8224898e1ab103f15549a9dbbbaf5d03b8` | `sha256sum`；内部 `log_sha256 == run_sha256_in_threads`、`ok_count=2`/`fail_count=0` |
| ④ 输出 | 2 张 PNG | 见 §2 表 | 回执 `views[].png_sha256` 与磁盘 `sha256sum` **逐张相等** |

**命令原文（首采，逐字）**：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
PYTHONDONTWRITEBYTECODE=1 /opt/openjiuwen/workswarm-venv/bin/python3 -B tools/metrics/render_shots_extra.py \
  --run-dir /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d27_C_n16r60_seed42 \
  --batch-id PUBTALK-C --outdir v2/evidence/public_talk_shots \
  --views chat,rhythm --timeout 240
# → rc=0, ok_count=2, fail_count=0
```

**服务生命周期**：静态服务由 `render_shots.py` 内部起在 `http://127.0.0.1:<port>`（本次 `:37423`，根 `/tmp/hitt_render_zxcw74x_`），`finally` 分支 `shutdown()` + `shutil.rmtree(tmp)`；未在 `code/frontend/` 落任何文件（渲染后 `git status --short code/frontend` 无新增）。

## 4. 本轮登记的页面派生读数（只登记、不判定）

```
threads=169  messages=510  multi_turn=88  ge3=77
```

| 项 | 值 | 与日志对账 |
|---|---|---|
| `messages` | 510 | 与 `meta.msg_counts`（`MSG_DM 455 + MSG_PUBLIC 55`）一致 |
| `threads` | 169 | 与 `reports/CYCLE-22-20261024.md:229` 引用的同批派生件一致 |

> 以上只是「页面显示的数与日志同源」，**不作臂间比较、不作效果推断**。

## 5. 这 2 张图**能说**什么 / **不能**说什么

| 能说 | 不能说 |
|---|---|
| 该批日志确为**真 LLM 批**（`provider=openai_compat`、`model=DeepSeek-Flash`、`degraded_calls=0`），页面自该批派生数据渲染 | 不能说「公开场合没人接话」是**效果**问题——「结构上不存在接话机制」的判据只由 `reports/R24-public-talk-baseline.md` 附录的只读数数器给出，**截图不进判据** |
| 页面能看到具体对话文本、线程参与者、时间节律 | 不能说「多数/普遍/典型」——2 张图是**单批单时刻的页面视图**，抽样性质，不得据此推断分布 |
| 图与日志/派生件/回执的 sha 链**四段闭合**，可被第三方重算复核 | 不能把本图与 `d27_shots` / `d28_shots`（不同臂/不同批）的图混拼成一组证据 |
| 图是**本轮现渲**（00:08:50–00:08:52），不是历史图顶替 | 不能宣称「视觉上更有生活气息」——那需要人评或 judge 证据，本目录没有 |
| 图可作为读者肉眼核对「公开消息在页面上呈现为单人独白」的辅助物证 | **不能说「该图证明了公开接话缺失」**：图不是指标，指标在报告附录的复算脚本里 |

## 6. 复现与校验命令（第三方复核用）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
sha256sum v2/evidence/run_d27_C_n16r60_seed42/run.jsonl \
          v2/evidence/public_talk_shots/threads_PUBTALK-C.json \
          v2/evidence/public_talk_shots/render_report_PUBTALK-C.json \
          v2/evidence/public_talk_shots/*.png
# 应分别等于 §2/§3 表中的值；PNG 两个 sha 应等于回执 views[].png_sha256
```
