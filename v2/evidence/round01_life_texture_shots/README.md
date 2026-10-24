# ROUND-01 生活气息证据：真实页面截图 + 可复算读数（C 基线臂 `run_d27_C`）

> **生成者**：`evidence-reporter`｜**取证时刻**：`2026-10-24T20:05:11 — 20:05:17 +08:00`（逐图 `png_mtime_iso` 见 `render_report_ROUND01-C.json` 的 `views[].png_mtime_iso`）
> **与报告的关系**：本目录供 ROUND-01 专题报告引用；本文件是**证据侧自解释件**（沿用 `v2/evidence/cycle21_shots/README.md`、`cycle20_shots`、`cycle17_shots` 的惯例）——脱离报告单翻本目录，也应能判读「图哪来的、能说什么、不能说什么」。
> **图源纪律**：图源为本仓**既有、`sha256` 已实算**的真 LLM 批日志 `v2/evidence/run_d27_C_n16r60_seed42/run.jsonl`；本轮**零跑批、零 LLM 调用**；3 张图**本轮现截**（2026-10-24T20:05），未复用任何既有 PNG、无拼图、无跨批混拼。
> **物证类别**：3 张均为**真实页面截图**（无头 Chromium 加载 `code/frontend/dialogue.html` 现场截取），**不是** matplotlib 读数图，两类物证不得混称。
> **引用树的身份（必读）**：本目录全部读数的树是 `code_sha = f2bf606`（批次 `meta.json`），分析基准报告树是 `dc02e06`；**都不是当前 master HEAD `1ff2784`**。已实测 `git diff --stat dc02e06..1ff2784 -- code` **零输出**、`git diff --stat f2bf606..1ff2784 -- code/life` **零输出**，即之后 4 笔提交只动文档/证据，读数对当前 HEAD 仍成立；但**引用时必须写成 f2bf606 / dc02e06**。

---

## 1. 双重标注：每张图必须能回答「哪条日志 + 哪条命令」

| 项 | 取值 |
|---|---|
| 图源批次（run 目录） | `v2/evidence/run_d27_C_n16r60_seed42/` |
| 臂身份 | C 基线臂（无 override，禁括号旁白） |
| 批次标签（`--batch-id`） | `ROUND01-C` |
| 日志 sha256（全长） | `1fbb9ef5161fd07aa68fcc9fc4038f104ff18b56383a2fc6b31bb3cb5486a188`（sha8 `1fbb9ef5`） |
| `meta.run_sha256` 是否等于上值 | **相等**（自洽） |
| 日志规模 | 116,308 events / 56,531,099 B |
| 跑批身份（引自 `meta.json`） | `code_sha = code_sha_end = f2bf606bf5f6c362a7d4d34b9177f3210d43aabf`；seed 42；rounds 60；provider `openai_compat`；model `DeepSeek-Flash`；`llm_calls 2878`；`degraded_calls 0`；`started_at 2026-10-24T14:04:39+08:00`；`finished_at 2026-10-24T14:59:23+08:00` |
| 派生页面数据 | `threads_ROUND01-C.json` = `0a1ce7aa9864c85c24e6d68ddf65afb78e3eadfe252ed58a3f2f14c555623232`（2,153,050 B；`gen_threads.py` 现算：events=116308 messages=510 threads=169 multi_turn=88 ge3=77 moves=299） |
| 渲染回执 | `render_report_ROUND01-C.json` = `41261c82a454d1fd84af58b7609152d075b380dc6c6cf6fe35cf77ea190ce657`；`ok_count=3` / `fail_count=0` / `generated_at 2026-10-24T20:05:17+08:00` |

> 回执字段 `run_sha256_in_threads = 1fbb9ef5…86a188` **等于**上表日志 sha ⇒「PNG 文件名里的 sha8」是脚本从日志实算写入的，不是人工填写。

## 2. 文件清单与 sha256（3 张 PNG + 3 个支撑件）

| 文件 | 视图 / 角色 | 画幅 | 字节 | sha256 | `png_mtime_iso` |
|---|---|---|---|---|---|
| `ROUND01-C-chat-1fbb9ef5.png` | 对话流（`still=1&multi=1&min=0&sort=turns`） | 1400×900 | 279,669 | `b30731e3db1638576f5eef171b6088854a3a97d5920020da959a1c3ae95e0378` | 2026-10-24T20:05:11+08:00 |
| `ROUND01-C-rhythm-1fbb9ef5.png` | 节律·串门（`still=1&multi=1&min=0&view=rhythm`） | 1300×1050 | 283,025 | `9b027dc2e849d73370d23e7bc4985df1836843e18a48cf4208aeacc8e709ac8c` | 2026-10-24T20:05:13+08:00 |
| `ROUND01-C-spread-1fbb9ef5.png` | 闲话怎么传开（`still=1&multi=1&min=0&view=spread`） | 1400×1000 | 179,235 | `cef1e085ce0cae032de4c9a24e9223e15be2da11945f1fa98b298a6d929cefe2` | 2026-10-24T20:05:16+08:00 |
| `threads_ROUND01-C.json` | 派生页面数据 | — | 2,153,050 | `0a1ce7aa9864c85c24e6d68ddf65afb78e3eadfe252ed58a3f2f14c555623232` | — |
| `render_report_ROUND01-C.json` | 渲染回执（三件套 + 像素自检逐张） | — | 9,919 | `41261c82a454d1fd84af58b7609152d075b380dc6c6cf6fe35cf77ea190ce657` | — |
| `render_selfcheck_20261024T2005.log` | 首采 + 重渲染同参数回执留痕（含逐张 `SHOT OK` / `blank_retries`） | — | 2,812 | `4d8b551a30ff8305fc60f519cdecd6a628adf214ccc5d48dbb6656db4120b1ed` | — |
| `README.md` | 本文件 | — | 见 `stat` | 见 `sha256sum v2/evidence/round01_life_texture_shots/README.md`（自引用不可写死） | — |

**像素自检档位（回执 `views[].pixel_selfcheck`，3 张 `status` 全 `OK`）**：

| 图 | `distinct_colors` | `top_color_frac` | `non_bg_frac` | 结论 |
|---|---|---|---|---|
| chat | 24,049 | 0.1417 | 0.5824 | `OK`（非空白） |
| rhythm | 22,402 | 0.2620 | 0.4746 | `OK`（非空白） |
| spread | 15,729 | 0.5683 | 0.1774 | `OK`（非空白） |

判据（脚本写死）：`distinct_colors ≥ 200 且 top_color_frac ≤ 0.99 ⇒ OK`（深色 UI 不按单色占比判死）。

**逐张渲染执行结果（`render_shots_extra.py` → `shot.py` 的 `SHOT OK` 行，原文见 `render_selfcheck_20261024T2005.log`）**：

| 图 | `rc` | `blank_retries` | `mean_brightness` | `max_color_frac` | elapsed | ok/fail |
|---|---|---|---|---|---|---|
| chat | 0 | 0/2 | 35.0 | 29.98% | 3.35s | ok |
| rhythm | 0 | 0/2 | 32.4 | 34.44% | 1.87s | ok |
| spread | 0 | 0/2 | 22.0 | 75.25% | 1.70s | ok |

> `blank_retries=0/2` 表示**未触发任何空白重试**（容错额度 2 次未被用掉）。
> `spread` 的 `max_color_frac=75.25%` 会被 `shot.py` 自身的「单色占比 ≥50% 判空白」误判为空白（该判据对深色 `dialogue.html` 的**历史实测误判率 80.09%**，属已知假红，本轮**未修**）；因此调用时带 `--no-blank-check`，判真以 `render_shots.py` 的像素自检档位（上表 `OK`）+ 页面可见内容（§5.5 目视复核）为准。

## 3. 一遍可复算的溯源链（每张图 5 件套）

以 `ROUND01-C-chat-1fbb9ef5.png` 为例（其余两张同构，参数见各自回执 `views[].triplet`）：

1. **输入日志**：`v2/evidence/run_d27_C_n16r60_seed42/run.jsonl`，sha256 `1fbb9ef5…86a188`
2. **派生 threads.json**：`v2/evidence/round01_life_texture_shots/threads_ROUND01-C.json`，sha256 `0a1ce7aa…623232`
   - 命令原文：`/opt/openjiuwen/workswarm-venv/bin/python3 …/code/frontend/tools/gen_threads.py --log …/run_d27_C_n16r60_seed42/run.jsonl --meta …/run_d27_C_n16r60_seed42/meta.json --out …/round01_life_texture_shots/threads_ROUND01-C.json --label ROUND01-C`
3. **截图命令原文**：
   `/opt/openjiuwen/workswarm-venv/bin/python3 …/code/frontend/tools/shot.py --url http://127.0.0.1:36447/dialogue.html?still=1&multi=1&min=0&sort=turns&data=sample/dialogue_ROUND01-C/threads.json --out …/round01_life_texture_shots/ROUND01-C-chat-1fbb9ef5.png --width 1400 --height 900 --timeout 240.0 --retry-blank 2 --no-blank-check`
4. **输出 PNG**：sha256 `b30731e3…95e0378`，279,669 B
5. **渲染回执**：`render_report_ROUND01-C.json`（sha256 `41261c82…0ce657`），`ok_count = 3` / `fail_count = 0`

**服务是怎么起的、怎么清掉的**：渲染链由 `tools/metrics/render_shots_extra.py`（对 `render_shots.py` 的**零改动包装器**，只多登记 `spread` 视图）驱动，内部**起本地静态服务** `http://127.0.0.1:36447`（`ThreadingHTTPServer` daemon 线程，服务根是 `/tmp/hitt_render_*` 临时目录 + 符号链接 `code/frontend/*`），**只走 `http://`，无 `file://`**；进程退出时 `finally` 分支 `httpd.shutdown()` + `shutil.rmtree(tmp)`，进程结束即回收，**不 kill 任何外部进程、不在 `code/frontend/` 落任何文件**。服务起止与端口已原样留在 `render_selfcheck_20261024T2005.log` 的 `[3/4] static server …` 行。

> 本链的等价分步形式（与任务卡的 `gen_threads → serve → dialogue_shots` 一一对应，本文件以包装器驱动以保证「不在 code/ 落文件」）：`gen_threads.py`（第 1/4 步，本回执 `triplet.gen_threads_cmd`）→ `serve`（第 3/4 步，`ThreadingHTTPServer`）→ `shot.py`（第 4/4 步，等价于 `dialogue_shots.sh` 内部的渲染器）。

## 4. 本轮复算的读数（命令 + 输出摘要，逐条可复算）

> **纪律**：以下全部为**点估计**，单 seed、单规模（n=16）、每臂 1 次，**无 CI**；对话原文只作样本摘录，**不作臂级比例推断**。
> **截图不参与任何判据**：本目录 3 张 PNG 只用于「页面能被渲染成可读非空白页面」与形态目视对照，**不进入任何指标计算、不改变任何报告状态词**。

### 4.1 对话指标（`tools/d5/dialogue_metrics.py`）

```bash
python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_d27_C_n16r60_seed42/run.jsonl \
        --out-json /tmp/round01/metrics.json --out-md /tmp/round01/metrics.md   # rc=0
```

| 指标 | 复算值 | 是否与任务清单一致 |
|---|---|---|
| `K-1_topic_continuation.cont_same_topic` | `1.0`（分母 `cont_same_topic_denominator = 341`，`denominator_adjacent_pairs = 341`） | ✅ 一致 |
| `F-2_content_drift.drift_rate` | `0.633431` | ✅ 一致 |
| `F-2_content_drift.jaccard_all.p50` | `0.074074`（`mean 0.085271`、`n 341`） | ✅ 一致 |
| `E_efficiency.E-1_msg_per_agent_round` | `0.559211`（`n_agents 16`、`n_rounds 57`） | ✅ 一致 |
| `F-5_habit_repetition.habit_strength` | `1.0`（`max_repeat_days_mean 4.375`） | ✅ 一致 |
| `F-6_crossday_memory.timeref_rate` | `0.084314` | ✅ 一致 |
| `S-4_reply_pointer_coverage.rate`（旁证） | `1.0`（`ptr_ok 341`、`ptr_empty/dangling/forward/cross_thread` 全 0） | ✅ 一致 |

> 脚本自身输出 `"messages": 510, "threads": 169, "admission": "REJECTED"`（`admission` 是脚本既有字段，与本次任务无关，不改判）。

### 4.2 消息计数与形态计数

```bash
python3 - <<'PY'
import json
pub=dm=grp=0; bodies=[]; pubs=[]
for line in open('v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'):
    if '"MSG_' not in line: continue
    r=json.loads(line); p=r.get('payload') or {}
    if r['type']=='MSG_PUBLIC': pub+=1; pubs.append(p)
    elif r['type']=='MSG_DM': dm+=1
    elif r['type']=='MSG_GROUP': grp+=1
    bodies.append(p.get('body') or '')
n=len(bodies)
print('MSG_DM',dm,'MSG_PUBLIC',pub,'MSG_GROUP',grp,'bodies',n)
for label,f in [('含正把/正给/正拿',lambda b:'正把' in b or '正给' in b or '正拿' in b),
                ('以？结尾',lambda b:b.rstrip().endswith('？')),
                ('含你那边',lambda b:'你那边' in b)]:
    c=sum(1 for b in bodies if f(b)); print(label, f'{c}/{n}', round(c/n*100,2))
print('PUBLIC participants_len_set', sorted({len(x.get('participants') or []) for x in pubs}))
print('PUBLIC reply_to_set', sorted({str(x.get('reply_to')) for x in pubs}))
PY
```

原样输出摘要：

```
MSG_DM 455 MSG_PUBLIC 55 MSG_GROUP 0 bodies 510
含正把/正给/正拿 122/510 23.92
以？结尾 139/510 27.25
含你那边 33/510 6.47
PUBLIC participants_len_set [1]
PUBLIC reply_to_set ['None']
```

| 项 | 复算值 | 是否与任务清单一致 |
|---|---|---|
| `MSG_DM` / `MSG_PUBLIC` | `455` / `55`（`MSG_GROUP = 0`，顺带复核了调研 §9 未验证项 #1） | ✅ 一致 |
| body 含「正把/正给/正拿」 | `122/510`（`23.92%`） | ✅ 一致 |
| 以「？」结尾 | `139/510`（`27.25%`） | ✅ 一致 |
| 含「你那边」 | `33/510`（`6.47%`） | ✅ 一致 |
| `MSG_PUBLIC` 的 `participants` 长度集合 | `[1]` ⇒ **恒单人** | ✅ 一致 |
| `MSG_PUBLIC` 的 `reply_to` 取值集合 | `['None']` ⇒ **恒 null** | ✅ 一致 |

**`MSG_PUBLIC` 一条原样样本**（`run.jsonl` 逐字摘录，只此一条，不作推断）：

```json
{"author":"P002","body":"这木头真硬。张家那口寿材，榫头得再收半分。慢工出细活。","body_ref":null,
 "ctx":{"initiator":"P002","l7struct":{"end":1,"end_name":"用很短的一句收","mode":"initiate","n_banned":0,
 "open":5,"open_name":"先一句感慨再落到具体事","v":"l7-struct/1"},"mood":"平和","need":{"social":45},
 "relation":0,"topic":"skill_practice","trigger":"skill_practice"},
 "day":0,"msg_id":"P-0-0","msg_uid":"42:53","participants":["P002"],"place":null,"refs":[],
 "reply_to":null,"scope":"global","slot":"morning","tag_hints":["skill_practice"],
 "thread_id":"TH-P002-PUB-0-0","topic":"skill_practice","turn_index":0}
```

### 4.3 真跑验真（`obs llm-cost`）

```bash
cd code && python3 -m obs llm-cost --log ../v2/evidence/run_d27_C_n16r60_seed42/run.jsonl \
        --require-provider openai_compat      # rc=0
```

原样输出摘要：

```json
{"engine_log":{"by_provider":{"openai_compat":2878},
 "by_purpose":{"dialogue":{"calls":510,"degraded":0,...},"importance":{"calls":1523,"degraded":0,...},
   "judge":{"calls":668,"thinking":668,"degraded":0,...},"negotiation":{"calls":49,"degraded":0},
   "plan":{"calls":16,"degraded":0},"reflect":{"calls":112,"degraded":0}},
 "total":{"calls":2878,"tokens_in":291359,"tokens_out":262570,"tokens_total":553929,
          "cached":1425,"degraded":0,"thinking":668}},
 "provider_guard":{"by_provider":{"openai_compat":2878},"expected":"openai_compat","ok":true,"problems":[]}}
```

| 项 | 复算值 | 是否与任务清单一致 |
|---|---|---|
| 退出码 | `rc=0` | ✅ |
| `by_provider` | `{"openai_compat": 2878}`（全真 LLM，无 mock 混入；`provider_guard.ok = true`） | ✅ |
| `degraded` | `0`（总 / 逐 purpose 全 0） | ✅ |

### 4.4 引用树核验（防跨树混读）

```bash
git diff --stat dc02e06da5f0d17f251465bc92cab11b2e9a22e1..1ff2784 -- code | wc -l   # → 0
git diff --stat f2bf606bf5f6c362a7d4d34b9177f3210d43aabf..1ff2784 -- code/life | wc -l  # → 0
```

两行均 `0` ⇒ `f2bf606`（跑批代码）/ `dc02e06`（CYCLE-21 分析基准）到当前 HEAD `1ff2784` 之间**代码零改动**；读数对当前 HEAD 成立，但引用树身份仍须写成 `f2bf606`/`dc02e06`。

### 4.5 页面可见内容复核（截图不参与判据，仅做「非空白 + 可读」目视核对）

对 `ROUND01-C-chat-1fbb9ef5.png` 做视觉复核（非 OCR 转写，只作目视摘要）：

- 页面标题「青溪镇·对话观看台」，数据源栏显示 `ROUND01-C`、`sha 1fbb9ef5161f`、`provider openai_compat`、`seed 42`、`事件 116308`、`消息 510`；
- 回归模块可见 `线程 88·多轮 88，消息 429·最长 6 轮`（该视图为「只看多轮」过滤口径）；
- 可逐字读到的对话（**样本摘录，仅此 2 条，不作比例推断**）：
  1. 秀娘：「这炉桃酥我总烤不出你家的脆劲儿，你最近忙得过来不？教教我。 `#73`」
  2. 老石：「哎，我正刨着刘家那根榆木梁，手头活儿紧，你明儿带块面来我这儿，我边做边教你，行不？ `#549`」

⇒ 两组数值与 §4.2 的复算口径一致（510 条全量、88 条多轮），**页面与日志同源**。

## 5. 能证明什么 / 不能证明什么

### 能证明

1. `run_d27_C`（`1fbb9ef5…86a188`）能被前端渲染成**可读、非空白**页面（回执 `ok_count=3`、`fail_count=0`、像素自检 3/3 `OK`）；
2. 页面自称的数据源（`sha 1fbb9ef5161f`、`事件 116308`、`消息 510`）与本目录登记的日志身份**逐项对上**；
3. 图源是**真 LLM 批**（`provider openai_compat 2878`、`degraded 0`、`provider_guard.ok true`）；
4. chat 视图里确有条目可逐字读到的对话与 `#seq` 标号（`#73`、`#549`），可由任意复核者复查。

### 不能证明

1. **不能**证明任何旁白率/一致率/习惯强度百分数——页面**不展示**逐条判定字段，百分比只能回到 §4 的复算命令；
2. **不能**把「图好看/图正常」当成效果结论：本目录无判据编号、无闸线，图**不参与任何判据**，也不改变任何既有报告的状态词；
3. **不能**做臂间配对比较：本目录只有 C 基线臂一条日志，不构成任何「A vs B」对照；
4. **不能**由 `rhythm`/`spread` 视图反推地点分布或传播广度——这两个视图只反映日志事件的页面计数，**分母口径以 §4 的复算件为准**。

## 6. 已知边界（如实登记，含一处字节不稳定）

- **PNG 字节不稳定（n=2，已实测）**：`2026-10-24T20:06` 用同一 `run.jsonl`、同参数重渲染到 `/tmp/round01/rerender`，3 张图 sha **全部与首采不同**（chat `fb35b991…` ≠ `b30731e3…`、rhythm `783069a7…` ≠ `9b027dc2…`、spread `ed8194a2…` ≠ `cef1e085…`），字节数也不同（279,935 / 283,274 / 179,486 vs 279,669 / 283,025 / 179,235），而 `mean_brightness`/`max_color_frac` 两次几乎相同（35.0/29.98% vs 35.0/29.97% 等）。
  ⇒ 与 `cycle21_shots/README.md` 记录的 `rhythm` 字节不稳定**同源**；本轮 n=2、**不构成「确定性可复现」结论**。**判真口径**：以**像素自检档位 + 页面可见内容**为准，**不要用 sha 不等就判「图假」**。本文件引用的就是 **20:05 首采那一组** sha。
- 重渲染的 `threads_*.json` sha 与首采不同（`3305611d…` vs `0a1ce7aa…`）——原因是两次 `--batch-id` 不同（`ROUND01-C` vs `ROUND01-C-RC`），`run_label` 被写进 `source`，属**标签差异**，不是数据差异。
- 日志受 `.gitignore`（`**/*.jsonl`）排除 ⇒ **不在 git 对象里**：可验 sha、可重渲染，但不可从零重建；本目录的 `threads_ROUND01-C.json` + 回执是它的**可追溯锚**。
- 渲染全程使用 `/tmp/hitt_render_*` 临时服务根 + 符号链接，**未在 `code/frontend/` 写入任何文件**；`PYTHONDONTWRITEBYTECODE=1 -B` 确保不在 `code/` 下留 `__pycache__`（实测 `find code -name __pycache__ -newermt '-30 minutes'` 空输出）。
- 渲染期间**未启动任何跑批**：主树 `pid 279887` 的 D2.8 B 臂仍在跑（本轮只读日志、只渲染）。
- 本目录 7 个文件**本轮新建、未跟踪**；本轮**不 commit**（提交由后继任务收口）。

## 7. 复算 / 重渲染命令

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# ① 核图源日志身份（期望 1fbb9ef5…86a188 / 116308 行 / 56,531,099 B）
sha256sum v2/evidence/run_d27_C_n16r60_seed42/run.jsonl
wc -l      v2/evidence/run_d27_C_n16r60_seed42/run.jsonl
stat -c '%s' v2/evidence/run_d27_C_n16r60_seed42/run.jsonl

# ② 核本目录全部文件的 sha（与第 2 节表格逐项比对）
sha256sum v2/evidence/round01_life_texture_shots/*

# ③ 核回执内部自洽（run_sha256_in_threads == log_sha256；ok_count=3 / fail_count=0）
python3 - <<'PY'
import json
r = json.load(open("v2/evidence/round01_life_texture_shots/render_report_ROUND01-C.json"))
print(r["log_sha256"] == r["run_sha256_in_threads"], r["ok_count"], r["fail_count"])
print([(v["view"], v["pixel_selfcheck"]["status"]) for v in r["views"]])
PY

# ④ 现场重渲染（输出到临时目录，不写 code/、不覆盖取证 PNG）
PYTHONDONTWRITEBYTECODE=1 /opt/openjiuwen/workswarm-venv/bin/python3 -B tools/metrics/render_shots_extra.py \
  --run-dir v2/evidence/run_d27_C_n16r60_seed42 \
  --batch-id ROUND01-C --outdir /tmp/round01_rerender --views chat,rhythm,spread --timeout 240
# 期望：ok_count=3 / fail_count=0 / rc=0（注意：PNG sha 可能因渲染时序不同而不同，见第 6 节）

# ⑤ 复算 §4 全部读数：见 §4.1 / §4.2 / §4.3 的命令原文
```
