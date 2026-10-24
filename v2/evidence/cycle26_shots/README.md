# CYCLE-26 截图证据包（`v2/evidence/cycle26_shots/`）

> 采集者：`case-renderer`（素材取证与截图工程师）· 渲染时刻 2026-10-25 04:33（回执自记）· 本 README 生成时刻 2026-10-25 04:37:32 +0800
> 用途：CYCLE-26 报告 §四「可展示案例」的**物证**。配套案例清单见团队共享空间 `CYCLE26-CASES.md`。
> **免责声明（先读）**：本目录 PNG 是「页面确实渲染出了这批真实日志」的**物证**，**不是指标证据**——**不进任何判据、不给任何百分数、不用于比例推断、不跨批混拼、不得作占位图复用**。指标一律由 `tools/` 下评测脚本对 `run.jsonl` 现算（见 `reports/` 各期 §二）。

## 1. 源（唯一单批，不混批）

| 项 | 值 |
|---|---|
| 跑批目录 | `.worktrees/d29-syntax-diversity/v2/evidence/run_d29_Bp_n16r60_seed42/` |
| `run.jsonl` sha256（本文现算） | `c4a819a99bda8ef01acbf7a4c816e5436dd86220370a8154293deb8b6a65ffda` |
| `meta.json` 自记 `run_sha256` | `c4a819a99bda8ef01acbf7a4c816e5436dd86220370a8154293deb8b6a65ffda` |
| 对账 | ✅ 逐字一致 |
| `run.jsonl` 字节 / 行数 | 56,595,434 B / 116,357 行（`meta.wc_l=116,357` ✅） |
| `run.jsonl` sha256（回执 `log_sha256` 字段） | `c4a819a99bda8ef01acbf7a4c816e5436dd86220370a8154293deb8b6a65ffda`（与现算一致 ✅） |
| `meta.code_sha` / `code_sha_end` | `2387cbf55fce8fa4bd51d898d5889d7751246f63` / `2387cbf55fce8fa4bd51d898d5889d7751246f63` |
| seed / n / rounds | 42 / 16 / 60（`n_in_log=16`、`rounds_effective=60`） |
| 跑批窗口 | 2026-10-25T03:30:05+08:00 → 2026-10-25T04:08:53+08:00（`duration_sec=2328`） |
| 事件 | 116,357（日志实测 116,357 行） |
| 消息 | DM 455 + PUBLIC 55 = 510（`meta.msg_counts` DM 455 / PUBLIC 55 ✅） |
| 线程数 | 169（含 55 条公开广播各自的单条线程） |

## 2. 实际执行的渲染命令（逐字，含本机 python 路径）

### 2.1 第 1 次：按任务书原文（**失败**，照实保留）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
PYTHONDONTWRITEBYTECODE=1 /opt/openjiuwen/workswarm-venv/bin/python3 -B tools/metrics/render_shots_extra.py \
  --run-dir /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d29-syntax-diversity/v2/evidence/run_d29_Bp_n16r60_seed42 \
  --batch-id CYCLE26-Bp42 --outdir v2/evidence/cycle26_shots \
  --views chat,rhythm --timeout 240 --blank-check on
```

```text
render_shots_extra.py: error: argument --blank-check: invalid choice: 'on' (choose from 'off', 'shot')
rc=2 ；v2/evidence/cycle26_shots/ 内 0 张 PNG
```

`--blank-check` 只有 `off|shot` 两值（`tools/metrics/render_shots_extra.py --help` 实测）。任务书的 `on` 不存在。

### 2.2 第 2 次：实际生效的命令（**`rc=0`，本节两张图即由它产出**）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
PYTHONDONTWRITEBYTECODE=1 /opt/openjiuwen/workswarm-venv/bin/python3 -B tools/metrics/render_shots_extra.py \
  --run-dir /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d29-syntax-diversity/v2/evidence/run_d29_Bp_n16r60_seed42 \
  --batch-id CYCLE26-Bp42 --outdir v2/evidence/cycle26_shots \
  --views chat,rhythm --timeout 240 --blank-check shot
```

`shot` = **打开** `shot.py` 自身的单色空白判据（不是关掉）。逐张实际 `shot.py` 命令由回执 `views[].triplet.render_cmd` 留痕，两张图里都**没有**禁用空白判据的那个旗标（`shot.py` 的 no‑blank 开关）字样：

```text
/opt/openjiuwen/workswarm-venv/bin/python3 /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code/frontend/tools/shot.py --url http://127.0.0.1:40611/dialogue.html?still=1&multi=1&min=0&sort=turns&data=sample/dialogue_CYCLE26-Bp42/threads.json --out /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/cycle26_shots/CYCLE26-Bp42-chat-c4a819a9.png --width 1400 --height 900 --timeout 240.0 --retry-blank 2
/opt/openjiuwen/workswarm-venv/bin/python3 /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code/frontend/tools/shot.py --url http://127.0.0.1:40611/dialogue.html?still=1&multi=1&min=0&view=rhythm&data=sample/dialogue_CYCLE26-Bp42/threads.json --out /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/cycle26_shots/CYCLE26-Bp42-rhythm-c4a819a9.png --width 1300 --height 1050 --timeout 240.0 --retry-blank 2
```

同时回执 `views[].triplet.gen_threads_cmd` 记录上游数据生成命令（同一 `run.jsonl`）：

```text
/opt/openjiuwen/workswarm-venv/bin/python3 /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code/frontend/tools/gen_threads.py --log /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d29-syntax-diversity/v2/evidence/run_d29_Bp_n16r60_seed42/run.jsonl --meta /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/d29-syntax-diversity/v2/evidence/run_d29_Bp_n16r60_seed42/meta.json --out /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/cycle26_shots/threads_CYCLE26-Bp42.json --label CYCLE26-Bp42
```

## 3. rc 与空白检测结果

**两个 `non_bg_frac` 不是同一个量，下表按口径分列，不得互证**（原版本把 `1 − top_color_frac` 写在「我的复算」列并标「与回执一致」，属口径混用，已按复核员意见改正）：

| 图 | `shot.py` rc | `shot.py` 单色判据 | 自检 `status` | `distinct_colors`<br>回执 / 我复算 | `top_color_frac`<br>回执 / 我复算 | `non_bg_frac`（回执定义）<br>回执 / 我复算 | `1 − top_color_frac`<br>（**另一口径，非回执字段**） |
|---|---|---|---|---|---|---|---|
| `CYCLE26-Bp42-chat-c4a819a9.png` | 0 | **打开**（cmd 里禁用空白判据的旗标出现 **0 次**）且未触发假红 | `OK` | 24,624 / 24,624 ✅ | 0.1417 / 0.1417 ✅ | 0.5827 / 0.5827 ✅ | 0.8583 |
| `CYCLE26-Bp42-rhythm-c4a819a9.png` | 0 | **打开**（cmd 里禁用空白判据的旗标出现 **0 次**）且未触发假红 | `OK` | 22,408 / 22,408 ✅ | 0.2620 / 0.2620 ✅ | 0.4748 / 0.4748 ✅ | 0.7380 |

**两列 `non_bg_frac` / `1 − top_color_frac` 的口径（逐字写明，勿混用）**：

- **回执 `non_bg_frac`**（来源 `tools/metrics/render_shots.py::pixel_selfcheck`，`:93` 附近）
  = 「与**最常见色（主色）**的**曼哈顿距离 > 24** 的像素占比」→ chat **0.5827**、rhythm **0.4748**。
  定义本身也印在回执 `pixel_selfcheck.rule` 之外的 `pixel_selfcheck` 注释里；`status=OK` 的判据是 `distinct_colors ≥ 200 且 top_color_frac ≤ 0.99`，**不含** `non_bg_frac`。
- **`1 − top_color_frac`** = 「非『主色那一个精确 RGB』的像素占比」→ chat **0.8583**、rhythm **0.7380**。
  它把「与主色相差 1–24 的近似色像素」也算作非背景，**因此必然 ≥ 回执口径**；**它不是回执字段，回执里没有这个数**。
- **结论**：两者**口径不同、不可互相印证、不可互相替代**，也不得拿 0.8583 去对 0.5827 说「一致」。上表 ✅ 只打在我**确实现算并确实相等**的三个量上（`distinct_colors`、`top_color_frac`、按曼哈顿距离口径的 `non_bg_frac`）。

回执汇总：`ok_count=2`、`fail_count=0`。

**关于单色判据的已知风险（照实写）**：`code/frontend/dialogue.html` 是深色页面，`shot.py` 的「单色占比 ≥50% 即空白」对它有假红史（前批实测误判率 80.09%，见 `v2/evidence/cycle25_shots/README.md:41` 与 `public_talk_shots/README.md`）。本次**没有**关掉它、也未触发假红（rc=0），故两图同时具备「`shot.py` 判据通过」+「像素自检 OK」两层证据；若后续批次在此判据上假红，正确做法是换 `--blank-check off` 并用 `pixel_selfcheck` 作等价证据，**不是** PS 或改用旧图。

## 4. 逐图清单（sha256 由我在本节现算，非抄回执）

| 图 | 文件 | 视图 | 尺寸 | 字节 | sha256 |
|---|---|---|---|---|---|
| 1 | `CYCLE26-Bp42-chat-c4a819a9.png` | chat（对话流） | 1400×900 | 294,165 | `ae9840f6c1c67baa8c2b1a86aee47f7a27b585f584f12e97d6018cf977858d81` |
| 2 | `CYCLE26-Bp42-rhythm-c4a819a9.png` | rhythm（节律·串门） | 1300×1050 | 283,262 | `1a44252caa67b002a74971c976663f9c014adfb4a9cc53cea18453f2c44acd6e` |

**屏上可见内容（按图内文字照录；面板被裁切处如实标注）**：

1. `CYCLE26-Bp42-chat-c4a819a9.png`（chat（对话流））— 顶部元数据行照录：`数据源 CYCLE26-Bp42 sha c4a819a99bda provider openai_compat seed 42 事件 116357 消息 510 线程格式 explicit（多线程）·meta 已对齐`；左侧筛选统计 `线程 88 · 多轮 88 / 消息 429 · 最长 6 轮 / 格式 线程化`；中部 5 天×4 时段网格（每格＝该 day+slot 的 `对话条数 | PLACE_MOVE 走动次数`，如 `第1天 早晨 24 | 16`）；下部线程卡片 `老石 ⇄ 秀娘`，头 `私聊 · 图书馆 · 第1天 · 早晨 · 06:00 → 第1天 · 傍晚 · 20:00 · TH-P004-P002-0`，屏内可见 `第1轮·秀娘 #73`、`第2轮·老石 #549`、`第3轮·秀娘 #2090` 三条正文；底部回放条 `第5天·夜里·04:00 / 510/510 / 最新`
2. `CYCLE26-Bp42-rhythm-c4a819a9.png`（rhythm（节律·串门））— 同一 5×4 时段网格；`一天里什么时候在说话`：早晨 131 / 午后 133 / 傍晚 145 / 夜里 101（面板自带注 `分母 = 全部 510 条`）；`话都发生在哪儿`：咖啡馆 103 条、住宅 101 条、公园 54 条、市集 53 条、中央广场 38 条、工坊 20 条、社区中心 18 条、农场 16 条（面板底缘仍有一行被视口裁掉、屏上不可读 ⇒ **该表在屏上不完整，不得当全量地点分布引用**；本人另行只读核过日志 `MSG_DM.place` 的完整分布为 14 个场所，此处不展开为任何比例结论）；`谁在串门（当天场所轨迹）`：老周 4 次（住宅→农场→市集→中央广场→住宅）、老石 4 次（住宅→图书馆→市集→社区中心→住宅）、秀娘 4 次（住宅→图书馆→市集→社区中心→住宅）、陈医 4 次（住宅→工坊→银行→咖啡馆→住宅）

**文件名里的 `c4a819a9` = 源日志 sha256 前 8 位**（`render_shots.py` 既有命名规则），**不是** PNG 自身 sha。

### 4.1 同批旁证文件（非截图，不计入图数）

| 文件 | 字节 | sha256 | 说明 |
|---|---|---|---|
| `threads_CYCLE26-Bp42.json` | 2,215,378 | `1884b8bbbf9f702eb27ea44454aeecf086a63c4a65071341c9a9500ad5f3cbb1` | `gen_threads.py` 由同一 `run.jsonl` 生成，前端渲染的数据源；`run_sha256_in_threads` 与源一致 |
| `render_report_CYCLE26-Bp42.json` | 7,272 | `e85870b59c9d0f8d28fc82b2e4c66d83ca670f89ad12befaf0bf6870ec857488` | 渲染回执：逐图 rc / sha / 尺寸 / 像素自检 / 实际命令 / policy |

## 5. sha 链与可复现性（四项，均已实测）

```text
run.jsonl  sha256 c4a819a9…65ffda  (56,595,434 B / 116,357 行)
   │
   ├─→ threads_CYCLE26-Bp42.json  sha256 1884b8bb…  (2,215,378 B)
   │        │
   │        ├─→ CYCLE26-Bp42-chat-c4a819a9.png    sha256 ae9840f6…
   │        └─→ CYCLE26-Bp42-rhythm-c4a819a9.png  sha256 1a44252c…
```

| # | 复现项 | 我实测的结果 | 判 |
|---|---|---|---|
| R1 | `gen_threads.py` 同参数重跑到 `/tmp/threads_rerun.json` | sha256 `1884b8bbbf9f702eb27ea44454aeecf086a63c4a65071341c9a9500ad5f3cbb1`、2,215,378 B —— 与本目录 `threads_CYCLE26-Bp42.json` **逐字节一致** | ✅ 确定性 |
| R2 | 同参数重渲 rhythm 到 `/tmp/c26_rerender/`（不覆盖本目录） | sha256 `1a44252caa67b002a74971c976663f9c014adfb4a9cc53cea18453f2c44acd6e` —— **逐字节一致** | ✅ 确定性 |
| R3 | 同参数重渲 chat | sha256 `f0b246ba944ac50d3866fa42e82d94b70f2010c7b1acdd86ca5b259290cbb85a`（294,136 B vs 本目录 294,165 B）—— **不逐字节一致**；PIL 逐像素比对：1,260,000 像素中 **92 像素**不同，**最大通道差 = 1**（8-bit 舍入级），无任何像素差 >1 | ⚠ chat 非字节确定，但视觉等价；**不宣称 chat 确定性** |
| R4 | 本目录 PNG 的 mtime | chat `2026-10-25T04:33:25+08:00`、rhythm `2026-10-25T04:33:28+08:00`（回执 `png_mtime_iso`），均落在本次采集时刻内 | ✅ 现渲 |

## 6. 来源声明（未复用、未拷贝、未改 batch id）

- 本目录两张 PNG 由 §2.2 命令于 **2026-10-25 04:33** 从上面那**唯一一批** `run.jsonl` **现渲**；回执 `policy.no_reuse` 记「输出同名 PNG 若已存在则先删除，只认本次现截」。
- **未**拷贝、**未**复用 `v2/evidence/cycle25_shots/` 的任何 PNG：`cycle25_shots` 的两图 sha256 为 `a6613e7d…`（chat）/`6f718140…`（rhythm），与本目录 `ae9840f6…` / `1a44252c…` 完全不同；源批次亦不同（cycle25 源为 `run_d28_C_s43_n16r60_seed43`）。
- batch id **未复用**：本目录为 `CYCLE26-Bp42`，`cycle25_shots` 为 `CYCLE25-C43`，文件名前缀无重合。
- 回执 `policy.code_untouched`：服务根为临时目录 + 符号链接，**未在 `code/frontend/` 下写入任何文件**；`policy.no_stitching`：每张图独立截图，未拼图、未跨批混拼。
- 渲染只读日志，**不重跑模拟、不改日志、不触碰 `code/`**。

## 7. 复现与自检命令

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/cycle26_shots
sha256sum *.png threads_CYCLE26-Bp42.json render_report_CYCLE26-Bp42.json   # 对 §4 / §4.1 的 sha
stat -c '%n %s bytes %y' *.png                                              # 对 §4 字节数与 §5 R4 mtime
PYTHONDONTWRITEBYTECODE=1 /opt/openjiuwen/workswarm-venv/bin/python3 -B -c "
from PIL import Image; import collections, glob
for f in sorted(glob.glob('*.png')):
    im=Image.open(f).convert('RGB'); px=list(im.getdata()); c=collections.Counter(px); mc,t=c.most_common(1)[0]
    nb=sum(1 for p in px if abs(p[0]-mc[0])+abs(p[1]-mc[1])+abs(p[2]-mc[2])>24)   # 回执口径
    print(f, im.size, 'distinct=%d'%len(c), 'top_frac=%.4f'%(t/len(px)),
          'non_bg_manhattan=%.4f'%(nb/len(px)), 'one_minus_top_frac=%.4f'%(1-t/len(px)))"
# 注意：non_bg_manhattan 才是回执 non_bg_frac 的口径（0.5827 / 0.4748）；
#      one_minus_top_frac（0.8583 / 0.7380）是另一个量，不可与回执对照。
grep -o 'render_cmd[^,]*' render_report_CYCLE26-Bp42.json   # 回查实际命令里禁用空白判据的旗标出现次数（期望 0）
```

---

**签名**：`case-renderer` · 本 README 主体由脚本 `/tmp/gen_c26_shots_readme.py` 现算写入；**§3 表格与 §7 复现片段由手工 `edit_file` 整改**（`t5-readme-fix`：把 `non_bg_frac` 与 `1 − top_color_frac` 两个口径拆列、删去跨口径的「一致」标注），整改**未重渲、未改动任何 PNG**。未 git commit / push（按任务边界）。

**修订记录**：`t5-readme-fix`（2026-10-25 04:40 前后）——复核员 `report-verifier` 指出 §3「我的复算」列用 `1 − top_color_frac`（0.8583 / 0.7380）冒充回执 `non_bg_frac`（0.5827 / 0.4748）并标「一致 ✅」。已改为按口径分列；两张 PNG 的有效性判定（`distinct_colors ≥ 200` 且 `top_color_frac ≤ 0.99` ⇒ `OK`）不受影响，图本身零改动（sha 见 §4）。
