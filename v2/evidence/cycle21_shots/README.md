# CYCLE-21 页面截图证据（C 基线臂 + B 旁白臂，各 chat/rhythm 两视图）

> **生成者**：`case-curator`｜**取证时刻**：`2026-10-24T16:32:41 — 16:32:52 +08:00`（逐图 `png_mtime_iso` 见两份 `render_report_*.json` 的 `views[].png_mtime_iso`）
> **与报告的关系**：这 4 张图供 `reports/CYCLE-21-20261024.md` §4 引用；本文件是**证据侧自解释件**（沿用 `v2/evidence/cycle20_shots/README.md` 与 `v2/evidence/cycle17_shots/README.md` 的惯例）——脱离报告单翻阅本目录，也应能判读「图哪来的、能说什么、不能说什么」。
> **图源纪律**：图源为本仓**既有、`sha256` 已实算**的真 LLM 批日志，本轮**零跑批、零 LLM 调用**；4 张图**本轮现截**，未复用任何既有 PNG，无拼图、无跨批混拼。
> **物证类别**：4 张均为**真实页面截图**（无头 Chromium 加载 `code/frontend/dialogue.html` 现场截取），**不是** matplotlib 读数图，两类物证不得混称。

## 1. 双重标注：每张图必须能回答「哪条日志 + 哪条命令」

| 项 | C 臂 | B 臂 |
|---|---|---|
| 图源批次（run 目录） | `v2/evidence/run_d27_C_n16r60_seed42/` | `.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/` |
| 臂身份 | C 基线臂（无 override） | B 实验臂（旁白放开） |
| 日志 sha256（全长） | `1fbb9ef5161fd07aa68fcc9fc4038f104ff18b56383a2fc6b31bb3cb5486a188`（sha8 `1fbb9ef5`） | `87e233c421aebeb5ecf3d4f37c74ba721cd6829f3d7e55ec75042e76d350f2f4`（sha8 `87e233c4`） |
| `meta.run_sha256` 是否等于上值 | 相等（自洽） | 相等（自洽） |
| 日志规模 | 116,308 events / 56,531,099 B | 115,545 events / 56,148,529 B |
| 跑批身份（引自 `meta.json`） | `code_sha = code_sha_end = f2bf606bf5f6c362a7d4d34b9177f3210d43aabf`；seed 42；rounds 60；n 16；provider `openai_compat`；model `DeepSeek-Flash`；`llm_calls 2878`；`degraded_calls 0`；`finished_at 2026-10-24T14:59:23+08:00` | `code_sha = code_sha_end = c74985050b86f31c21f4ab90da8d9244b3410251`；seed 42；rounds 60；n 16；provider `openai_compat`；model `DeepSeek-Flash`；`llm_calls 2869`；`degraded_calls 0`；`finished_at 2026-10-24T16:23:24+08:00` |
| 派生页面数据 | `threads_CYCLE-21C.json` = `12815e9f36f035bfffee98fe762d054885bfd210d8f367b2b5d79f3a1b249afe` | `threads_CYCLE-21B.json` = `5c46b58645d16e3cc87ccf4a5d063b1d052c1a560c72ba7dae80477d3ca5b408` |
| 渲染回执 | `render_report_CYCLE-21C.json` = `60e79da0177312195fbdc9b57e0fd46eb86de731e295f5f67675fa3bcafce2d5`；`ok_count=2` / `fail_count=0` | `render_report_CYCLE-21B.json` = `e31ae112e333e46064eca5d8d5e86f785694a2f1d95165824eacee8ad9f5f617`；`ok_count=2` / `fail_count=0` |

> 两份回执的 `run_sha256_in_threads` 分别等于上表日志 sha ⇒ 「PNG 文件名里的 sha8」是脚本从日志实算写入的，不是人工填写。

## 2. 文件清单与 sha256（4 张 PNG + 4 个支撑件 + 1 个自检日志）

| 文件 | 视图 / 角色 | 画幅 | 字节 | sha256 | `png_mtime_iso` |
|---|---|---|---|---|---|
| `CYCLE-21C-chat-1fbb9ef5.png` | C 臂 对话流（`still=1&multi=1&min=0&sort=turns`） | 1400×900 | 279,470 | `d0a33259fa2fd02807d0f8ccc8e7814cf6824c03241d90b7c005c11fa1951030` | 2026-10-24T16:32:41+08:00 |
| `CYCLE-21C-rhythm-1fbb9ef5.png` | C 臂 节律·串门（`still=1&multi=1&min=0&view=rhythm`） | 1300×1050 | 282,840 | `21845927f4d819969843abbf1a6e2a1f9a290d4f08bbb8546f13beaec52653cf` | 2026-10-24T16:32:44+08:00 |
| `CYCLE-21B-chat-87e233c4.png` | B 臂 对话流（同上参数） | 1400×900 | 289,716 | `386eaaddf899d13f6fec03c5f88c52da77627de7b4f7df612c9a89c40e9de132` | 2026-10-24T16:32:50+08:00 |
| `CYCLE-21B-rhythm-87e233c4.png` | B 臂 节律·串门（同上参数） | 1300×1050 | 283,570 | `c5ce5f5035a83d66811386c2f5d241e23a2e1860467d82011cf5896f3e06d892` | 2026-10-24T16:32:52+08:00 |
| `threads_CYCLE-21C.json` | C 臂派生页面数据 | — | 2,153,050 | `12815e9f36f035bfffee98fe762d054885bfd210d8f367b2b5d79f3a1b249afe` | — |
| `threads_CYCLE-21B.json` | B 臂派生页面数据 | — | 2,093,920 | `5c46b58645d16e3cc87ccf4a5d063b1d052c1a560c72ba7dae80477d3ca5b408` | — |
| `render_report_CYCLE-21C.json` | C 臂渲染回执 | — | 6,934 | `60e79da0177312195fbdc9b57e0fd46eb86de731e295f5f67675fa3bcafce2d5` | — |
| `render_report_CYCLE-21B.json` | B 臂渲染回执 | — | 7,185 | `e31ae112e333e46064eca5d8d5e86f785694a2f1d95165824eacee8ad9f5f617` | — |
| `rerender_selfcheck_20261024.log` | 重渲染自检留痕（含逐张 `SHOT OK` / `blank_retries`） | — | 1,744 | `8dcb4ad5429c357c9a4416b30577b97ca70d3f9b5bc69f8058d5145291b53fd9` | — |
| `README.md` | 本文件（证据侧自解释件） | — | 见 `stat` | 见 `sha256sum v2/evidence/cycle21_shots/README.md`（自引用不可写死） | — |

**像素自检档位（回执 `views[].pixel_selfcheck`，4 张 `status` 全 `OK`）**：

| 图 | `distinct_colors` | `top_color_frac` | `non_bg_frac` | 结论 |
|---|---|---|---|---|
| C-chat | 24,007 | 0.1417 | 0.5824 | `OK`（非空白） |
| C-rhythm | 22,368 | 0.2620 | 0.4746 | `OK`（非空白） |
| B-chat | 24,280 | 0.1417 | 0.5824 | `OK`（非空白） |
| B-rhythm | 22,306 | 0.2621 | 0.4743 | `OK`（非空白） |

**逐张渲染执行结果（`render_shots.py` → `shot.py` 的 `SHOT OK` 行，原文摘录见 `rerender_selfcheck_20261024.log`）**：

| 图 | `rc` | `blank_retries` | `mean_brightness` | `max_color_frac` | ok/fail |
|---|---|---|---|---|---|
| C-chat | 0 | 0/2 | 35.0 | 29.98% | ok |
| C-rhythm | 0 | 0/2 | 32.4 | 34.44% | ok |
| B-chat | 0 | 0/2 | 35.4 | 29.92% | ok |
| B-rhythm | 0 | 0/2 | 32.4 | 34.44% | ok |

> `blank_retries=0/2` 表示**未触发任何空白重试**（容错额度 2 次未被用掉）。首次取证时 `render_report_*.json` 的 `shot_stdout_tail` 只保留末 3 行（Deprecation 警告），故 `blank_retries` 由 `rerender_selfcheck_20261024.log` 中的同参数回执行补证——该日志的 `ok_count/fail_count` 均为 2/0。

> `shot.py` 自身仍以「最大单色占比 ≥50% 判空白」，对深色 `dialogue.html` 会假红（历史实测误判 80.09%）；本目录以 `render_shots.py` 的像素自检档位为准（调用时带 `--no-blank-check`），**该判据本轮未修**。

## 3. 一遍可复算的溯源链（每张图 5 件套）

以 `CYCLE-21C-chat-1fbb9ef5.png` 为例（其余三张同构，参数见各自回执 `views[].triplet`）：

1. **输入日志**：`v2/evidence/run_d27_C_n16r60_seed42/run.jsonl`，sha256 `1fbb9ef5…86a188`
2. **派生 threads.json**：`v2/evidence/cycle21_shots/threads_CYCLE-21C.json`，sha256 `12815e9f…249afe`
   - 命令原文：`/opt/openjiuwen/workswarm-venv/bin/python3 …/code/frontend/tools/gen_threads.py --log …/run.jsonl --meta …/meta.json --out …/cycle21_shots/threads_CYCLE-21C.json --label CYCLE-21C`
3. **截图命令原文**：
   `/opt/openjiuwen/workswarm-venv/bin/python3 …/code/frontend/tools/shot.py --url http://127.0.0.1:34129/dialogue.html?still=1&multi=1&min=0&sort=turns&data=sample/dialogue_CYCLE-21C/threads.json --out …/cycle21_shots/CYCLE-21C-chat-1fbb9ef5.png --width 1400 --height 900 --timeout 240.0 --retry-blank 2 --no-blank-check`
4. **输出 PNG**：sha256 `d0a33259…951030`，279,470 B
5. **渲染回执**：`render_report_CYCLE-21C.json`（sha256 `60e79da0…fce2d5`），其中 `ok_count = 2` / `fail_count = 0`

## 4. 复算 / 重渲染命令

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# ① 核两臂图源日志身份（期望 1fbb9ef5…86a188 / 87e233c4…50f2f4）
sha256sum v2/evidence/run_d27_C_n16r60_seed42/run.jsonl \
          .worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl
wc -l      v2/evidence/run_d27_C_n16r60_seed42/run.jsonl \
          .worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl   # 期望 116308 / 115545

# ② 核本目录全部文件的 sha（与第 2 节表格逐项比对）
sha256sum v2/evidence/cycle21_shots/*

# ③ 核回执内部自洽（run_sha256_in_threads == log_sha256；ok_count=2 / fail_count=0）
python3 - <<'PY'
import json
for b in ("CYCLE-21C", "CYCLE-21B"):
    r = json.load(open(f"v2/evidence/cycle21_shots/render_report_{b}.json"))
    print(b, r["log_sha256"] == r["run_sha256_in_threads"], r["ok_count"], r["fail_count"])
PY

# ④ 现场重渲染（输出到临时目录，不写 code/、不覆盖取证 PNG）
PYTHONDONTWRITEBYTECODE=1 /opt/openjiuwen/workswarm-venv/bin/python3 -B tools/metrics/render_shots.py \
  --run-dir v2/evidence/run_d27_C_n16r60_seed42 \
  --batch-id CYCLE-21C --outdir /tmp/c21_rerender --views chat,rhythm --timeout 240
PYTHONDONTWRITEBYTECODE=1 /opt/openjiuwen/workswarm-venv/bin/python3 -B tools/metrics/render_shots.py \
  --run-dir .worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42 \
  --batch-id CYCLE-21B --outdir /tmp/c21_rerender --views chat,rhythm --timeout 240
# 期望：两次均 ok_count=2 / fail_count=0 / rc=0
```

**可复现性实测（如实登记，含一次失败）**：

- `2026-10-24T16:34:12 +08:00` 的一次 C 臂重渲染中，`rhythm` 图得到 `c7f14fb68dd50939cd629b350ea315edf580946e131198ad5bcda54c42a13070`，**与取证 sha 不同**（该临时目录已清理，仅留此记录）；
- `2026-10-24T16:34:58 +08:00` 的正式重渲染（`rerender_selfcheck_20261024.log`）中，4 张图 sha **全部与取证值一致**。
- **结论（观察，不是确定性结论）**：本次环境共执行 3 次渲染 —— ① `2026-10-24T16:32:41→16:32:52` 首采（即取证那一组）、② `2026-10-24T16:34:12` 试跑、③ `2026-10-24T16:34:58` 正式重渲染（`rerender_selfcheck_20261024.log`）。逐视图结果：`chat` **3/3** 字节一致、`rhythm` **2/3** 一致（第 ② 次的 `rhythm` 得到 `c7f14fb68dd50939cd629b350ea315edf580946e131198ad5bcda54c42a13070`，与取证值不同；该临时目录已清理，仅留此记录）。
- **该观察 n=3，不构成「确定性可复现」结论**：3 次同参数执行中出现 1 次 `rhythm` 字节不一致，属**已观测到的字节不稳定**（疑与节律页首帧/动画时序有关）；因此本文件**不对任何视图下「稳定 / 可复现」的定性**，只报逐次比对结果。
- **复核口径**：`rhythm` 的 sha 只对该次采集成立；判真以 **像素自检档位 + 页面可见内容**为准，**不要用 sha 不等就判「图假」**。报告引用的是 16:32 首采那一组 sha（对齐凭据见下一段）；16:34:58 的重渲染仅为**该一组 sha 的一次等值复现证据**，不是被引用的图。

**报告 §4 引用的究竟是哪一次执行的 sha（便于复核者对齐）**：

本目录 4 张取证 PNG 的 sha — `d0a33259…951030`（C-chat）、`21845927…2653cf`（C-rhythm）、`386eaadd…9de132`（B-chat）、`c5ce5f50…e6d892`（B-rhythm） — **全部来自同一次取证执行**：`2026-10-24T16:32:41 → 16:32:52 +0800`，即 `render_shots.py` 的两次调用（C 臂 `16:32:41`(chat)/`16:32:44`(rhythm)、B 臂 `16:32:50`(chat)/`16:32:52`(rhythm)）。对齐凭据：

- 回执字段 `views[].png_mtime_ns`：C-chat `1792830761765588337`、C-rhythm `1792830764193587652`、B-chat `1792830770438768864`、B-rhythm `1792830772833360226`（单次执行内单调递增，跨臂不重叠）；
- 该次执行的重渲染复现留痕：`rerender_selfcheck_20261024.log` **第 12 行**（C-chat）、**第 13 行**（C-rhythm）、**第 22 行**（B-chat）、**第 23 行**（B-rhythm），四行 sha 与本组逐字相同；
- 参照系：同一日志 **第 5 行** 与 **第 15 行** 是重渲染的两段边界标记（`=== [A] C 臂重渲染 ===` / `=== [B] B 臂重渲染 ===`），执行时刻戳位于日志首部 `# 执行时刻: 2026-10-24T16:34:58+08:00`。

> 即：报告引用的就是**首采那一组**（16:32 截取、落盘为取证 PNG）；16:34:58 的重渲染是**等值复现的证据**，不是被引用的图。

## 5. 能证明什么 / 不能证明什么

### 能证明
1. 两臂 `run.jsonl`（`1fbb9ef5…` / `87e233c4…`）都能被前端渲染成**可读、非空白**页面（回执 `ok_count=2`、`fail_count=0`、像素自检 `OK`）；
2. 对话流视图里确有**逐字对话与 `#seq` 标号**（人工看图可见 `#73`、`#549`、`#2090` 等，与 `cases.md` 第 1 节一致）；
3. **形态差异肉眼可辨**：C 臂 chat 图正文为纯引语；B 臂 chat 图正文以全角括号动作旁白开头（`（把沾着面粉的擀面杖搁下）…`）。该对比可直接由两张 PNG 目视核对，无需任何指标；
4. 图源是**真 LLM 批**（两臂均 `provider openai_compat`、`degraded_calls 0`）。

### 不能证明
1. **不能**证明任何旁白率/一致率百分数——页面**不展示**逐条旁白判定字段，百分比必须回落到 `metric-recomputer` 的复算件（本目录不提供、也不替代它）；
2. **不能**把「图好看」当成效果结论：本周期无判据编号、无闸线，图**不参与任何判据**，也不改变任何既有报告的状态词；
3. **不能**证明两臂是「同一局模拟的同轨迹」：两张图来自两个独立 run（`code_sha` 不同、`run_sha256` 不同、`rounds` 相同但演化路径不同），只能做**形态对照**，不能做配对比较；
4. **不能**由 `rhythm` 视图反推无条件的地点分布结论：节律图只反映日志中 `PLACE_MOVE`/对话条数的页面计数，分母口径以复算件为准。

## 6. 已知边界

- 两批日志受 `.gitignore`（`**/*.jsonl`）排除 ⇒ **不在 git 对象里**：可验 sha、可重渲染，但不可从零重建；B 臂日志位于 **worktree**（`.worktrees/d27-narration/`）且未提交，本目录的 `threads_CYCLE-21B.json` + 回执是它在主树里的**可追溯锚**。
- `threads_*.json` 由 `gen_threads.py` 现算派生，体量 2 MB 级（C 2,153,050 B / B 2,093,920 B），按任务要求保留在 `v2/evidence/cycle21_shots/`（**未写入 `code/`**）。
  - 处置意向（`report-author` 2026-10-24T16:36 反馈）：**建议入库**，理由是 B 臂日志在 `.worktrees/` 且受 `**/*.jsonl` 忽略，`threads_CYCLE-21B.json` 是 B 臂页面派生在主树的唯一可追溯锚；最终以 leader 对 C21-F 白名单的终裁为准。
- 渲染全程使用临时服务根 + 符号链接，本链**未在 `code/frontend/` 写入任何文件**；`PYTHONDONTWRITEBYTECODE=1 -B` 确保不在 `code/` 下留 `__pycache__`（`find code -name __pycache__ -newermt '-2 hours'` 为空）。
- **需向审计说明的一处脏项归属**：`git status` 里 `code/frontend/sample/dialogue_d27_C/`、`dialogue_d27_B/` 两个未跟踪目录，其 mtime 为 `2026-10-24T16:30:28 / 16:30:29`（内含 `threads.json`：C 侧 2,153,042 B / B 侧 2,093,912 B，与本目录 `threads_CYCLE-21C.json` 2,153,050 B、`threads_CYCLE-21B.json` 2,093,920 B **体量相近但 sha 不等**，属另一次 `gen_threads.py` 的产物），**早于本链首次渲染（16:32:41）2 分钟，且不经由本链产生**（本链服务根为 `/tmp/hitt_render_*` + 符号链接，进程退出即 `rmtree`）。归因待 `evidence-auditor` 判定，本文件不作结论、也不代为清理。
- 本目录 10 个文件（本 README + 4 PNG + 2 `threads_*.json` + 2 `render_report_*.json` + 1 自检日志）**本轮新建、未跟踪**，是否随 CYCLE-21 报告入库由 leader 决定；`reports/CYCLE-21-*.md` 与 `cases.md` 由 report-author / case-curator 分别落盘，互不覆盖。
