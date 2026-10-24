# CYCLE-23 页面截图证据：B 臂（`run_d28_B_n16r60_seed42`）真实渲染 + 四段 sha 链

> **生成者**：`页面截图取证员`（member `shot-renderer`）｜**取证时刻**：`2026-10-24T20:31:58 — 20:32:03 +08:00`（逐图 `png_mtime_iso` 见 `render_report_CYCLE23-B.json` 的 `views[].png_mtime_iso`）
> **与报告的关系**：本目录供《周期实验报告》§四「可展示案例」引用截图；本文件是**证据侧自解释件**（格式沿用 `v2/evidence/round01_life_texture_shots/README.md`、`cycle21_shots`、`cycle20_shots` 的惯例）——脱离报告单翻本目录，也应能判读「图哪来的、能说什么、不能说什么」。
> **图源纪律**：图源是本轮指定的**唯一**真 LLM 批日志（D2.8 B 臂，narration quota），`sha256` 已现场实算并与 `meta.json` 自洽；本轮**零跑批、零 LLM 调用**；3 张图**本轮现截**（`2026-10-24T20:31:58 — 20:32:03`），**未复用** `round01_life_texture_shots` / `cycle21_shots` / `cycle17_shots` 等任何既有 PNG，无拼图、无跨批混拼。
> **物证类别**：3 张均为**真实页面截图**（无头 Chromium 加载 `code/frontend/dialogue.html` 现场截取），**不是** matplotlib 读数图，两类物证不得混称。
> **纪律红线**：本文件**不给任何百分数、不给任何效果结论**，截图**不参与任何指标判定**（详见 §5）。

---

## 1. 双重标注：每张图必须能回答「哪条日志 + 哪条命令」

| 项 | 取值 |
|---|---|
| 图源批次（run 目录，绝对路径） | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d28-narration-quota/v2/evidence/run_d28_B_n16r60_seed42/` |
| 臂身份 | B 臂（D2.8 narration-quota 组，worktree `.worktrees/d28-narration-quota`） |
| 批次标签（`--batch-id`） | `CYCLE23-B` |
| 日志 sha256（全长） | `f0c8724de04ba251ec79c375844dd89a72923e2a6b36b6fec4780fffd0d2ab7e`（sha8 `f0c8724d`） |
| `meta.run_sha256` 是否等于上值 | **相等**（`meta.derived_from_log_sha256` 同值，自洽） |
| 日志规模 | `116,342` 行（`wc -l`）/ `56,568,487` B |
| 跑批身份（引自 `meta.json`） | `code_sha = code_sha_end = 0474ee5f09ddc61e37edfdbdf001e79308e66fbb`；`n=16`；`rounds=60`；`seed=42`；provider `openai_compat`；model `DeepSeek-Flash`；`llm_calls 2878`；`degraded_calls 0`；`started_at 2026-10-24T19:29:36+08:00`；`finished_at 2026-10-24T20:09:50+08:00` |
| 派生页面数据 | `threads_CYCLE23-B.json` = `733900352f31f232d7c0a0db45e32ff31fee94ae9e4170d9472d1815b758d859`（2,176,927 B；`gen_threads.py` 现算：`events=116342 messages=510 threads=169 multi_turn=88 ge3=77 moves=299 legacy_msgs=0`） |
| 渲染回执 | `render_report_CYCLE23-B.json` = `8f4c5d6f8563a38137174116bb0113d9e2a4a70cf4d72d08a90943c4f4559ebd`（10,184 B）；`ok_count=3` / `fail_count=0` / `generated_at 2026-10-24T20:32:05+08:00` |

> 回执字段 `run_sha256_in_threads = f0c8724de04ba251ec79c375844dd89a72923e2a6b36b6fec4780fffd0d2ab7e` **等于**上表日志 sha（**实测 `True`**）⇒「PNG 文件名里的 sha8 `f0c8724d`」是脚本从日志实算写进 `threads.json` 再派生到文件名的，**不是人工填写**。

## 2. 文件清单与 sha256（3 张 PNG + 4 个支撑件）

| 文件 | 视图 / 角色 | 画幅 | 字节 | sha256 | `png_mtime_iso` |
|---|---|---|---|---|---|
| `CYCLE23-B-chat-f0c8724d.png` | 对话流（`still=1&multi=1&min=0&sort=turns`） | 1400×900 | 289,157 | `57897f72e23270dbe13aef7c2d95e56f8afe6326a9d7169723b6afb6f71d66ce` | 2026-10-24T20:31:58+08:00 |
| `CYCLE23-B-rhythm-f0c8724d.png` | 节律·串门（`still=1&multi=1&min=0&view=rhythm`） | 1300×1050 | 283,084 | `b86360cd92f2abfe25a397917449d51fdd30f7420d4e3255783ddfa9ebaf990e` | 2026-10-24T20:32:01+08:00 |
| `CYCLE23-B-spread-f0c8724d.png` | 闲话怎么传开（`still=1&multi=1&min=0&view=spread`） | 1400×1000 | 179,243 | `1611027108033fcce48ca74f5cc379b204763acdaf03a54b23cf6686956d7604` | 2026-10-24T20:32:03+08:00 |
| `threads_CYCLE23-B.json` | 派生页面数据 | — | 2,176,927 | `733900352f31f232d7c0a0db45e32ff31fee94ae9e4170d9472d1815b758d859` | — |
| `render_report_CYCLE23-B.json` | 渲染回执（三件套 + 像素自检逐张） | — | 10,184 | `8f4c5d6f8563a38137174116bb0113d9e2a4a70cf4d72d08a90943c4f4559ebd` | — |
| `render_samelabel_rerender_20261024T1233Z.log` | **同标签**重渲染全量 stdout/stderr（含逐张 `SHOT OK` 行） | — | 5,430 | `87e3b200e70000a29b1b556804b28cd625701e465abe9f3c81be9779259b43ec` | — |
| `render_difflabel_rerender_20261024T1232Z.log` | **异标签**（`CYCLE23-B-RC`）重渲染留痕（用于 §6 对照实验） | — | 5,418 | `a488800ba857c8c5b29d509317ffd4519d6dfc8c049bebfc54cb860b9411908f` | — |
| `README.md` | 本文件 | — | 见 `stat` | 见 `sha256sum v2/evidence/cycle23_shots/README.md`（自引用不写死） | — |

**像素自检档位（回执 `views[].pixel_selfcheck`，3 张 `status` 全 `OK`）**：

| 图 | `distinct_colors` | `top_color_frac` | `non_bg_frac` | 结论 |
|---|---|---|---|---|
| chat | 24,377 | 0.1417 | 0.5824 | `OK`（非空白） |
| rhythm | 22,386 | 0.2620 | 0.4746 | `OK`（非空白） |
| spread | 15,710 | 0.5683 | 0.1774 | `OK`（非空白） |

判据（`tools/metrics/render_shots.py::pixel_selfcheck` 写死）：`distinct_colors ≥ 200 且 top_color_frac ≤ 0.99 ⇒ OK`（深色 UI 不按单色占比判死）。

**逐张渲染执行结果（`shot.py` 的 `SHOT OK` 行原文，见 `render_samelabel_rerender_20261024T1233Z.log`；首采 stdout 与之一致）**：

| 图 | `rc` | `blank_retries` | `mean_brightness` | `max_color_frac` | elapsed |
|---|---|---|---|---|---|
| chat | 0 | 0/2 | 35.6 | 29.98% | 1.84s |
| rhythm | 0 | 0/2 | 32.4 | 34.44%（异标签重渲染为 34.43%） | 1.76s |
| spread | 0 | 0/2 | 22.0 | 75.25% | 1.77s |

> `blank_retries=0/2` ⇒ **未触发任何空白重试**（容错额度 2 次未被用掉）。
> `spread` 的 `max_color_frac=75.25%` 会被 `shot.py` 自身的「单色占比 ≥50% 判空白」误判为空白（该判据对深色 `dialogue.html` 属**已知假红**，历史实测误判率 80.09%，`shot.py` docstring 亦注明「`--no-blank-check` 用于非小镇画布的普通页面」）；因此三张调用时**一律带 `--no-blank-check`**，判真以 `render_shots.py` 的像素自检档位（上表全 `OK`）+ §4.5 页面可见内容目视复核为准。

## 3. 四段可复算 sha 链（日志 → threads → 回执 → PNG）

`日志 sha256 → threads json sha256 → 渲染回执 sha256 → PNG sha256` 四段，逐段实测（本轮真值）：

| 段 | 对象 | sha256（全长） | 校验方式 |
|---|---|---|---|
| ① 日志 | `…/run_d28_B_n16r60_seed42/run.jsonl` | `f0c8724de04ba251ec79c375844dd89a72923e2a6b36b6fec4780fffd0d2ab7e` | `sha256sum`；且 `meta.run_sha256` / `meta.derived_from_log_sha256` 同值 |
| ② 派生 | `threads_CYCLE23-B.json` | `733900352f31f232d7c0a0db45e32ff31fee94ae9e4170d9472d1815b758d859` | 由 ① 现算（`gen_threads.py`）；回执 `threads_json_sha256` 同值 |
| ③ 回执 | `render_report_CYCLE23-B.json` | `8f4c5d6f8563a38137174116bb0113d9e2a4a70cf4d72d08a90943c4f4559ebd` | `sha256sum`；内部 `log_sha256 == run_sha256_in_threads` 实测 `True`、`ok_count=3`/`fail_count=0` |
| ④ 输出 | 3 张 PNG | 见 §2 表 | 回执 `views[].png_sha256` 与磁盘 `sha256sum` **逐张相等**（实测） |

**链条合拢点**：② 内 `source.run_sha256 = ①`（脚本实算写入）；③ 内 `run_sha256_in_threads = ①`；④ 的 PNG 名含 ① 的 sha8 `f0c8724d`，且 ④ 的 sha 由 ③ 逐张登记 ⇒ 任一段被改动，链条即断，可被第三方复算发现。

**命令原文（首采，逐字）**：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
PYTHONDONTWRITEBYTECODE=1 /opt/openjiuwen/workswarm-venv/bin/python3 -B tools/metrics/render_shots_extra.py \
  --run-dir /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d28-narration-quota/v2/evidence/run_d28_B_n16r60_seed42 \
  --batch-id CYCLE23-B --outdir v2/evidence/cycle23_shots \
  --views chat,rhythm,spread --timeout 240
# → rc=0, ok_count=3, fail_count=0
```

等价的展开形态（与任务卡 `gen_threads → serve → shot.py` 一一对应，命令原文见回执 `views[].triplet`）：

```bash
# ② gen_threads（第 1/4 步）
/opt/openjiuwen/workswarm-venv/bin/python3 code/frontend/tools/gen_threads.py \
  --log …/.worktrees/d28-narration-quota/v2/evidence/run_d28_B_n16r60_seed42/run.jsonl \
  --meta …/.worktrees/d28-narration-quota/v2/evidence/run_d28_B_n16r60_seed42/meta.json \
  --out v2/evidence/cycle23_shots/threads_CYCLE23-B.json --label CYCLE23-B
# ③ 本地静态服务（第 3/4 步）：ThreadingHTTPServer daemon 线程，端口随机（本轮首采 http://127.0.0.1:38507 ），
#    服务根 /tmp/hitt_render_*（symbolic link code/frontend/*）+ sample/dialogue_CYCLE23-B/threads.json，只走 http://，无 file://
# ④ shot.py（第 4/4 步）
/opt/openjiuwen/workswarm-venv/bin/python3 code/frontend/tools/shot.py \
  --url "http://127.0.0.1:38507/dialogue.html?still=1&multi=1&min=0&sort=turns&data=sample/dialogue_CYCLE23-B/threads.json" \
  --out v2/evidence/cycle23_shots/CYCLE23-B-chat-f0c8724d.png \
  --width 1400 --height 900 --timeout 240.0 --retry-blank 2 --no-blank-check
```

**服务生命周期**：服务由 `render_shots.py` 内部起（`ThreadingHTTPServer` + daemon 线程，端口 `0` 由内核分配），`finally` 分支 `httpd.shutdown()` + `shutil.rmtree(tmp)`，进程退出即回收；**未 kill 任何外部进程、未在 `code/frontend/` 落任何文件**（实测 `find code/frontend -name __pycache__ -newermt '-30 minutes'` 空输出；`git status --short code/frontend` 除既有 `?? sample/dialogue_*` 外无新增）。

## 4. 本轮登记的读数（只登记、不判定；不含任何百分数结论）

> **纪律**：以下全部为**点估计**，单 seed、单规模（n=16）、单臂 1 次，**无 CI**；只用于说明「页面显示的数与日志同源」，**不作臂间比较、不作效果推断**。

### 4.1 `gen_threads.py` 现算读数（页面派生口径）

```
[gen_threads] events=116342 messages=510 threads=169 multi_turn=88 ge3=77 legacy_msgs=0 moves=299 ref_edges=0 echoes=0
```

| 项 | 值 |
|---|---|
| `events` | 116,342（与 `meta.events` / `wc -l` 一致） |
| `messages` | 510（与 `meta.msg_counts` `MSG_DM 455 + MSG_PUBLIC 55` 一致） |
| `threads` / `multi_turn` / `ge3` | 169 / 88 / 77 |
| `moves` | 299 |

### 4.2 `meta.json` 自洽项（只读引用，未重算指标）

| 项 | 值 | 与日志一致性 |
|---|---|---|
| `events` | 116,342 | ✅ `wc -l = 116342` |
| `msg_counts` | `MSG_DM 455` / `MSG_PUBLIC 55` | ✅ 与 `gen_threads` 的 `messages=510` 相加自洽 |
| `degraded_calls` | 0 | — |
| `llm_provider_in_events` | `{"openai_compat": 2878}` | —（真跑身份字段，引自 meta，未本轮复跑） |
| `assertions.participants_violations` / `ptr_dangling` / `ptr_cross_thread` | 0 / 0 / 0 | — |

> 指标级复算（旁白率等）**不在本目录职责内**，由 `证据复算核验员` 独立出具；本目录**不复述、不新增**任何判据数字。

### 4.3 引用树核验（防跨树混读）

```bash
git diff --stat 0474ee5f09ddc61e37edfdbdf001e79308e66fbb..HEAD -- code/frontend | wc -l   # → 0
```

`0` ⇒ 跑批代码身份 `0474ee5f` 到当前主仓 HEAD `f4272b2d` 之间 **`code/frontend/` 零改动** ⇒ 本轮用主仓前端渲染该批日志，前端树与跑批时一致。引用树身份仍须写成 **`0474ee5f`（跑批）/ `f4272b2d`（渲染时主仓 HEAD）**。

### 4.4 页面自称数据源 ↔ 日志身份逐项对表（OCR 转写，仅作同源核对）

对 `CYCLE23-B-chat-f0c8724d.png` 顶部数据源栏做 OCR 转写（非逐字权威件）：

| 页面显示 | 是否与 §1 日志身份/§4.1 读数一致 |
|---|---|
| 标题「青溪镇·对话观看台」「线程化聊天视图·按模拟时间回放·只读真源日志」 | —（页面标题） |
| `数据源 CYCLE23-B` | ✅ 等于 `--batch-id` |
| `sha f0c8724de04b` | ✅ 等于日志 sha 前 12 位 |
| `provider openai_compat` / `seed 42` | ✅ 等于 `meta.provider` / `meta.seed` |
| `事件 116342` / `消息 510` | ✅ 等于 §4.1 `events` / `messages` |
| `线程 88 · 多轮 88` / `消息 429 · 最长 6 轮` | 该栏为**视图过滤口径**（本视图 `multi=1` 只看多轮），不等于全量 169/510，两者口径不同，不得混用 |

⇒ 页面自称的数据源与本目录登记的日志身份**逐项对上**，即「页面与日志同源」。

### 4.5 页面可见内容复核（目视 + OCR 转写，仅证「非空白 + 可读」）

`CYCLE23-B-chat-f0c8724d.png` 目视可读到（**OCR 转写可能有字符误差，逐字原文以 `对话原文摘录员` 的取证件为准，本目录不承担逐字取证职责**）：

- 线程标题「老石与秀娘」；对话气泡逐条带 `#seq` 尾标，页面上可读到的条目例：#73、#549、#2090（对应第 1/2/3 轮）。

⇒ 页面**确实渲染出可读、非空白的对话条目与 `#seq` 标号**，可由任意复核者复查；**本项不用于任何判据**。

## 5. 能证明什么 / 不能证明什么

### 能证明
1. `run_d28_B_n16r60_seed42`（`f0c8724d…d2ab7e`）能被前端渲染成**可读、非空白**页面（回执 `ok_count=3`、`fail_count=0`、像素自检 3/3 `OK`）；
2. 页面自称的数据源（`sha f0c8724de04b`、`事件 116342`、`消息 510`、`provider openai_compat`、`seed 42`）与本目录登记的日志身份**逐项对上**（§4.4）；
3. 四段 sha 链（日志→threads→回执→PNG）**实测闭合**（§3）；
4. 渲染使用的前端树与跑批代码在 `code/frontend/` 上**零差异**（§4.3）。

### 不能证明
1. **不能**证明任何旁白率/一致率/习惯强度等百分数——页面**不展示**逐条判定字段，百分数只能回到复算件；
2. **不能**把「图正常/图好看」当效果结论：本目录**无判据编号、无闸线**，3 张 PNG **不参与任何指标判定**，也不改变任何报告状态词；
3. **不能**做臂间配对比较：本目录只有 B 臂一条日志，**不构成任何 A vs B 或 B vs C 对照**；
4. **不能**由 `rhythm`/`spread` 视图反推地点分布或传播广度——这两个视图只反映日志事件的页面计数，**分母口径以复算件为准**；
5. **不能**把 §4.5 的 OCR 转写当逐字原文引用——逐字取证归 `对话原文摘录员`。

## 6. 已知边界与两处实测发现（如实登记）

1. **同标签重渲染 = 字节级一致（n=2，本轮实测）**：`2026-10-24T20:33` 以**同一** `--batch-id CYCLE23-B`、同参数重渲染到 `/tmp/cycle23_rerender_same`，3 张 PNG sha 与本目录交付件**逐张完全相同**（chat `57897f72…`、rhythm `b86360cd…`、spread `16110271…`），`threads_CYCLE23-B.json` sha 亦相同（`73390035…`）。留痕：`render_samelabel_rerender_20261024T1233Z.log`。
2. **异标签重渲染 = 字节不同（n=1，本轮实测）**：`2026-10-24T20:32` 以 `--batch-id CYCLE23-B-RC` 重渲染，3 张 sha 全部不同（`b18296b0…` / `7dce9062…` / `a53b962f…`）。
   ⇒ **原因已定位**：`--batch-id` 会被写进 `threads.json` 的 `source.run_label`，而 `dialogue.html` 的「数据源」栏**把标签渲染在页面上**（§4.4 可见 `数据源 CYCLE23-B`），故标签不同 ⇒ 页面像素不同 ⇒ PNG 字节不同。
   ⇒ **对既有说法的修正**：`round01_life_texture_shots/README.md` §6 把「重渲染 sha 不同」记为「PNG 字节不稳定」，本轮实测表明**同一标签下字节完全稳定**，那次差异**属标签差异（`ROUND01-C` vs `ROUND01-C-RC`），不是渲染不确定性**；本轮结论仅 n=2，**仍不宣称跨环境确定性**。留痕：`render_difflabel_rerender_20261024T1232Z.log`。
3. **深色页面假红（必须带 `--no-blank-check`）**：`shot.py` 自带「单色占比 ≥50% 判空白」对深色 `dialogue.html` 会假红（`spread` 的 `max_color_frac=75.25%` 必然被判空白；历史实测误判率 80.09%）。本轮三张**均带 `--no-blank-check`**，判真改用 `render_shots.py` 的像素自检档位（`distinct_colors ≥ 200 且 top_color_frac ≤ 0.99 ⇒ OK`，3/3 `OK`）。
4. **日志不在 git 对象里**：`**/*.jsonl` 被 `.gitignore` 排除 ⇒ 日志可验 sha、可从 worktree 路径重渲染，但不可从零重建；本目录 `threads_CYCLE23-B.json` + 回执是它的**可追溯锚**。
5. **跨 worktree 只读引用**：图源日志位于 `.worktrees/d28-narration-quota/`（B 臂产出于该 worktree），本目录所在主仓 `HEAD = f4272b2d`；两端 `code/frontend/` 零差异（§4.3）。**本轮未写入 worktree 任何文件**（worktree `git status` 仅既有 `?? v2/evidence/run_d28_B_*` 与 preflight 产物）。
6. **渲染未在 `code/` 落文件**：服务根为 `/tmp/hitt_render_*` 临时目录 + 符号链接；`PYTHONDONTWRITEBYTECODE=1 -B` 确保不留 `__pycache__`（实测空输出）。
7. **未跑批**：本轮只读日志、只渲染，**零 LLM 调用**。

## 7. 复算 / 重渲染命令（第三方一键复核）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# ① 核图源日志身份（期望 f0c8724d…d2ab7e / 116342 行 / 56,568,487 B）
sha256sum .worktrees/d28-narration-quota/v2/evidence/run_d28_B_n16r60_seed42/run.jsonl
wc -l      .worktrees/d28-narration-quota/v2/evidence/run_d28_B_n16r60_seed42/run.jsonl
stat -c '%s' .worktrees/d28-narration-quota/v2/evidence/run_d28_B_n16r60_seed42/run.jsonl

# ② 核本目录全部文件 sha（与 §2 表格逐项比对）
sha256sum v2/evidence/cycle23_shots/*

# ③ 核回执内部自洽（run_sha256_in_threads == log_sha256；ok_count=3 / fail_count=0；逐张像素档位）
/opt/openjiuwen/workswarm-venv/bin/python3 - <<'PY'
import json
r = json.load(open("v2/evidence/cycle23_shots/render_report_CYCLE23-B.json"))
print(r["log_sha256"] == r["run_sha256_in_threads"], r["ok_count"], r["fail_count"])
print([(v["view"], v["pixel_selfcheck"]["status"], v["png_sha256"][:8]) for v in r["views"]])
PY
# 期望：True 3 0
# [('chat','OK','57897f72'), ('rhythm','OK','b86360cd'), ('spread','OK','16110271')]

# ④ 现场同参数重渲染（输出到临时目录，不写 code/、不覆盖取证 PNG；同批次标签应得同 sha）
PYTHONDONTWRITEBYTECODE=1 /opt/openjiuwen/workswarm-venv/bin/python3 -B tools/metrics/render_shots_extra.py \
  --run-dir /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d28-narration-quota/v2/evidence/run_d28_B_n16r60_seed42 \
  --batch-id CYCLE23-B --outdir /tmp/cycle23_check --views chat,rhythm,spread --timeout 240
# 期望：ok_count=3 / fail_count=0 / rc=0；3 张 PNG sha 与 §2 相同（本轮 n=2 实测一致）
```

---

**引用须知（给报告成稿员）**：引用本目录时请照抄 §2 的**绝对路径 + 全长 sha256 + 画幅**；`§四` 的图说明只写「页面形态（对话流/节律/闲话传播）+ 可读条目标签」，**不得附任何百分数或效果结论**；逐字对话原文请取 `对话原文摘录员` 的取证件，本目录的 OCR 段（§4.5）不可作为逐字引用源。
