# CYCLE-25 截图证据包（`v2/evidence/cycle25_shots/`）

> 采集者：`case-collector`（素材取证与截图工程师）· 采集时刻 2026-10-25 00:38:23 +08:00
> 用途：CYCLE-25 报告 §四「可展示案例」的**物证**。
> **免责声明（先读）**：本目录的 PNG 是「页面确实渲染出了这批真实日志」的**物证**，**不是指标证据**——**不进任何判据、不给任何百分数、不用于任何比例推断、不得跨批混拼、不得作为占位图重复使用**。指标一律由 `tools/` 下的评测脚本对 `run.jsonl` 现算（见 `reports/` 各期 §二）。

## 1. 源（唯一，单批，不混批）

| 项 | 值 |
|---|---|
| 跑批目录 | `v2/evidence/run_d28_C_s43_n16r60_seed43/` |
| 日志 | `run.jsonl`（116,294 行 / 56,520,452 B） |
| 日志 sha256 | `e3518b63f3a587e93f11cf0fa56e4e7c97f807de9e198aab17cb8968051aae36` |
| `meta.code_sha` | `04ff044e7a46f89db6d8273a84806dd7212ef9c4` |
| seed / n / rounds | 43 / 16 / 60 |
| 统计 | 事件 116,294 · 消息 510 · 线程 169 · `llm_calls=2878` |

## 2. 逐图清单

| 图 | 文件 | 视图 | 尺寸 | 字节 | sha256 | 屏上内容 |
|---|---|---|---|---|---|---|
| 1 | `CYCLE25-C43-chat-e3518b63.png` | `chat`（对话流） | 1400×900 | 285,193 | `a6613e7d7ec0b8397fb7260d5e9fcbdc0dd58a9a66b07b149449ce55b38c42d5` | 当前屏可见线程 `TH-P004-P002-0`（「老石 ⇄ 秀娘」，6 条 / 6 轮，第 1 天） |
| 2 | `CYCLE25-C43-rhythm-e3518b63.png` | `rhythm`（节律·串门） | 1300×1050 | 282,878 | `6f718140c93d63bb77b34b8c03d7a32a3b9513c5eeddf3a9e747ab7c798e5d95` | 整批聚合：5 天 × 4 时段的消息条数与 `PLACE_MOVE` 走动次数、各场所条数 |

- 文件名中的 `e3518b63` = **源日志 sha 前 8 位**（`render_shots.py` 的既有命名规则），不是 PNG 自身 sha。
- 两图**同批同日现渲**；回执 `policy.no_reuse` 记录同名 PNG 先删后截。

## 3. 渲染命令（本机实测 `rc=0`）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
PYTHONDONTWRITEBYTECODE=1 /opt/openjiuwen/workswarm-venv/bin/python3 -B tools/metrics/render_shots_extra.py \
  --run-dir /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d28_C_s43_n16r60_seed43 \
  --batch-id CYCLE25-C43 --outdir v2/evidence/cycle25_shots \
  --views chat,rhythm --timeout 240 --blank-check off
# 实际 shot.py 命令（逐张落在回执 triplet.render_cmd 里）：
#   /opt/openjiuwen/workswarm-venv/bin/python3 code/frontend/tools/shot.py --url http://127.0.0.1:<port>/dialogue.html?...
#     --out .../CYCLE25-C43-chat-e3518b63.png --width 1400 --height 900 --timeout 240.0 --retry-blank 2 --no-blank-check
```

### 3.1 关于 `--no-blank-check`（**必须写明，否则看起来像漏了参数**）

- `render_shots_extra.py` **没有**名为 `--no-blank-check` 的开关；该参数由 `--blank-check off`（**默认值**）在内部注入到每张图的 `shot.py` 命令里（`tools/metrics/render_shots.py:209-213`）。
- 注入结果**逐张留痕**在回执 `render_report_CYCLE25-C43.json` 的 `views[].triplet.render_cmd`，两张图都带 `--no-blank-check`。回查：`verify_cases.py` 会断言 `render_cmd` 含该字符串。

### 3.2 为什么必须关掉 `shot.py` 的单色空白判据

`code/frontend/dialogue.html` 是**深色**页面。`shot.py` 的空白判据是「单一颜色占比 ≥ 50% 即判空白」，对深色大色块页面会**把正常渲染判成空白**（实测误判率 80.09%，属已知**假红**）。故本目录改用 `render_shots.py::pixel_selfcheck`：

| 图 | `status` | `distinct_colors` | `top_color_frac` | `non_bg_frac` | 判据 |
|---|---|---|---|---|---|
| `chat` | OK | 24,368 | 0.1417 | 0.5826 | `distinct_colors ≥ 200 且 top_color_frac ≤ 0.99 ⇒ OK` |
| `rhythm` | OK | 22,377 | 0.2620 | 0.4748 | 同上 |

**注意**：这与既有 `public_talk_shots/README.md:41` 的处理一致（同一缺陷，同一规避方式）。

## 4. 四段 sha 链（**已闭合，逐段可核**）

```
run.jsonl  sha256 e3518b63… ──┬─→ threads_CYCLE25-C43.json  sha256 c52297bf…
                              │      （其 source.run_sha256 = e3518b63…，同值）
                              └─→ render_report_CYCLE25-C43.json  sha256 64f92ff5…
                                     · log_sha256            = e3518b63…
                                     · run_sha256_in_threads = e3518b63…
                                     · threads_json_sha256   = c52297bf…
                                     · ok_count=2 / fail_count=0
                                          │
                                          ├─→ chat PNG   sha256 a6613e7d…（回执 png_sha256 同值，磁盘 sha256sum 同值）
                                          └─→ rhythm PNG sha256 6f718140…（同上）
```

| 件 | 文件 | sha256 | 字节 |
|---|---|---|---|
| 回执 | `render_report_CYCLE25-C43.json` | `64f92ff5efbde97403e41fd2e7effff06f340ab746bb1ae7c30fb1936f152b60` | 7,002 |
| 派生页面数据 | `threads_CYCLE25-C43.json` | `c52297bf6e4e4905c29f099d40765305d591bb3ab29368e33e0af623aeb6fd93` | 2,153,943 |
| 引文清单 | `cases_manifest.json` | `b7517c52c9c82a271f0fa6b32393041699db0a52042c182f280ba26051cf426c` | 17,596 |
| 复核脚本 | `verify_cases.py` | `be06f2f60e564b02bcca6db51fbeb62674c9a1ad9fb4148f45447cc809704855` | 9,295 |

`threads_CYCLE25-C43.json` 由 `code/frontend/tools/gen_threads.py`（`generator_sha256 1ab81778…`）从 `run.jsonl` **现算**，不落 `code/frontend/`；服务根为临时目录 + 符号链接（回执 `policy.code_untouched`）。

## 5. `chat` 屏上可见线程 ↔ 日志行号的对应（**只对可见那一屏负责**）

`chat` 视图的数据面是**全批 510 条 / 169 线程**，屏上显示哪一屏由 `sort=turns` 与滚动位置决定。本次截图屏上可见 `TH-P004-P002-0`，对应 C:43 的 6 条消息：

| 物理行号 | 轮次 | 说话人 → 收件人 | `msg_uid` | 正文长度 | 屏上可核对的片段 |
|---|---|---|---|---|---|
| 74 | r0 t0 | P004 → P002 | `43:73` | 29 | 第 1 轮「这炉桃酥我总烤不出你家的脆劲儿……」（完整可见） |
| 550 | r1 t1 | P002 → P004 | `43:549` | 36 | 第 2 轮「哟，我正刨着刘家那根榆木梁……」（完整可见） |
| 2091 | r3 t2 | P004 → P002 | `43:2090` | 60 | 第 3 轮「刘家那根榆木梁刨起来费劲不？……」（完整可见） |
| 2915 | r4 t3 | P002 → P004 | `43:2914` | 50 | 第 4 轮「哎，纹路得顺着摸，逆了茬口就崩边。……」（下缘截断，仅首句可见） |
| 4921 | r6 t4 | P004 → P002 | `43:4920` | 54 | 屏外（需滚动） |
| 5557 | r7 t5 | P002 → P004 | `43:5556` | 46 | 屏外（需滚动） |

核对方法：`sed -n '74p' v2/evidence/run_d28_C_s43_n16r60_seed43/run.jsonl | python3 -m json.tool`，看 `payload.body` 与其字数是否与上表一致。
**不承诺**「屏上只显示这 6 条」——除此之外的屏外内容不做任何声明。

## 6. 复查（一条命令）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 v2/evidence/cycle25_shots/verify_cases.py --repo . \
  --cases /root/.jiuwenswarm/.agent_teams/jiuwen_team_cron___1a16ebf6778_61b067282f91/team-workspace/CASES.md
# → checks=372  fails=0
#   [PASS] 全部通过：源日志 sha / 24 条引文逐字节 / CASES.md 引文行 / 四段 sha 链
#（CASES.md 为可选参数；不给则只核清单、日志与截图链）
```

`verify_cases.py` 独立校验：①三份 `run.jsonl` 实测 sha == 清单声明；②24 条引文按物理行回读，`payload.body` 逐字节相等 + `物理行==seq+1` + `msg_uid==<seed>:<seq>` + round/turn/from/to/thread_id 一致；③CASES.md 引文行逐字节回查、行数 == 24；④四段 sha 链 + `ok_count>0 && fail_count==0` + `render_cmd` 含 `--no-blank-check`。

## 7. 失败与不可判（本目录）

| # | 项 | 状态 | 说明 |
|---|---|---|---|
| R-1 | B 臂（`run_d28_B_n16r60_seed43`）截图 | **未做（主动不做）** | 该日志在 `.worktrees/d28-narration-quota/`，被 `.gitignore:38` 覆盖、不在主树；据其渲染的 PNG 即便入库，第三方也**无法从仓库复现源日志**，sha 链只能闭到磁盘临时件 ⇒ 宁可不做，也不给「看起来闭合、实则不可复现」的图。 |
| R-2 | `spread`（闲话怎么传开）视图 | 未渲染 | 任务只要求 ≥2 张（chat+rhythm）。如需，把 `--views` 改成 `chat,rhythm,spread` 用第 3 节同命令复现（脚本支持）。 |
| R-3 | `_blank_check_failed/` | **本目录不存在** | 未引用任何 `_blank_check_failed/` 下的图；未使用占位图、未手绘。 |
| R-4 | `run.jsonl` 入库 | **不在任何 commit** | `git check-ignore -v` 实测 `.gitignore:8 **/*.jsonl`。复现依赖**磁盘原件 + 上表 sha256**，不依赖 `git clone`。 |

## 8. 本目录文件清单（提交 pathspec 建议）

```
v2/evidence/cycle25_shots/CYCLE25-C43-chat-e3518b63.png
v2/evidence/cycle25_shots/CYCLE25-C43-rhythm-e3518b63.png
v2/evidence/cycle25_shots/render_report_CYCLE25-C43.json
v2/evidence/cycle25_shots/threads_CYCLE25-C43.json
v2/evidence/cycle25_shots/cases_manifest.json
v2/evidence/cycle25_shots/verify_cases.py
v2/evidence/cycle25_shots/README.md
```

（`v2/evidence/*/run.jsonl` 不在此列，也**不应** `git add -f`——56 MB 级大文件，且属仓库既有 ignore 策略。）
