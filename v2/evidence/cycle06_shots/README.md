# CYCLE-06 截图证据（本期现场渲染，来自 F-6 两臂真 LLM 日志）

> 生成者：`evidence-scout`（证据取证专员）｜生成时刻：**2026-10-23T04:38:36–04:39:00 +0800**（见本目录 `render_wrap.log` 的 `RENDER_START_OFF` / `RENDER_START_ON` / `RENDER_END` 与每条 `→ BEGIN/END`，两者均带 ISO 时间戳）
> 与索引的关系：`evidence-index-CYCLE-06.md` §5.2 当时据实写"本周期新增页面截图 = 0"（检查到 04:36 为止，主树最新 png mtime 为 00:32 的 `cycle05_shots/`）。本目录为**其后现场渲染补齐**，不是复用上一周期图。
> 图源纪律：只选**本周期真实存在、且已由本人核过 sha256** 的 run 产物；未使用仍在运行中的 `run_f6off_cycle06_seed42_n16r84`（04:36 时仍 round 31/84）。

## 1. 三重标注（缺一条即为引用错误）

| 项 | OFF 臂 | ON 臂 |
|---|---|---|
| 图源批次 | `v2/evidence/run_d1_f6off_seed42_n16r84/run.jsonl` | `v2/evidence/run_d1_f6on_seed42_n16r84/run.jsonl` |
| 该日志 sha256 | `dbff7b97b2820429b3378da0517283e1c34af246221286e666c9e28223977e64`（sha8 `dbff7b97`） | `5c28dd85be67a65d621a09b062e9553ebe7bc006706bba1e5a65d4f3bf61ef11`（sha8 `5c28dd85`） |
| 日志字节 / 事件数 | 93,516,639 B / 193,989 events | 93,567,664 B / 194,008 events |
| 开关真值（原文照录） | `env_dump_pre.txt`：`LIFE_PROMPT_* unset (HITT_LLM_PROVIDER unset)` | 同左，逐字相同 |
| 规模 | seed=42, n=16, rounds=84（`meta.json`: `n=16/rounds=84/rounds_effective=84/rounds_seen_max=83`）, 686 MSG / 206 线程 | 同左（686 MSG / 206 线程） |
| 树（`meta.json.code_sha`） | `d7d1d93fa5871388fd8e51c44b6e179ac668b03f` | `e8a9fd5e3a889b556af12f2b8bdcfbf1c680f7c3` |
| 起跑/收工时刻 | `started_at 2026-10-23T00:13:38+08:00` / `finished_at 00:58:47` | `started_at 00:59:01` / `finished_at 01:46:54` |
| 渲染时刻 | `RENDER_START_OFF 04:38:36` → `RENDER_END_OFF`（chat 04:38:36–38、rhythm 38–40、spread 40–46、600 46–48） | `RENDER_START_ON 04:38:48` → `RENDER_END_ON`（chat 48–50、rhythm 50–52、spread 52–58、600 58–04:39:00） |
| **能证明什么** | 该批真 LLM 世界/对话在本仓库 `dialogue.html` 上的**页面外观**可读、非空白（页面底部计数 `686 / 686`，与 `stats.messages=686` 一致） | 同左 |
| **不能证明什么** | 不作为任何效果证据；两臂 `code_sha` 不同（见 §5），截图不参与判据 | 同左 |

文件名中的 `dbff7b97` / `5c28dd85` 即日志 sha256 前 8 位，由 `gen_threads.py` 写入 `threads.json.source.run_sha256`，**不是人工填写**。

**开关真值的重要限定（照实写）**：两臂 `env_dump_pre.txt` 均记 `LIFE_PROMPT_*` 为 unset，即两臂在**环境变量层**没有开关差；二者的差别落在**代码树**（`d7d1d93` vs `e8a9fd5`）上。故本目录的"开关真值"一栏只能给到 env 层结论，**不能**写成"同树 env 开关 OFF/ON 对照"。

**另一条必须同读的事实**：`run_d1_f6on_seed42_n16r84/pgrep_pre.txt` 在 `2026-10-23T00:59:01` 实测 `git rev-parse HEAD = d7d1d93fa…`，而其 `meta.json.code_sha` 为 `e8a9fd5…`（`generated_at 01:46:56`，晚于收工 01:46:54）⇒ 该字段记录的是**收工时 HEAD**。`meta.json.assertions.code_unchanged_during_run` 值为 `null`（未断言）。本条只陈述字段事实，不作推断。

## 2. 文件与 sha256（`sha256sum` / `stat` 实跑）

### 2.1 有效证据（6 张，全部通过 `shot.py` 空白检测，`blank_retries=0/2`）

| 文件 | 视图 | 画幅 | 字节 | sha256 |
|---|---|---|---|---|
| `cycle06_f6off-chat-dbff7b97.png` | 对话流（全量口径） | 1400×900 | 273,377 | `98327e0ab5c2215e2f5b8de82e4fe938ce53441831471a2689b97fc8768966ab` |
| `cycle06_f6off-rhythm-dbff7b97.png` | 节律·串门 | 1300×1050 | 285,158 | `30548318fd39acc3b64a7e54f8df7da7af6edf7233dbfadc877a3e1006534ac1` |
| `cycle06_f6off-600-dbff7b97.png` | 600px 判读 | 600×900 | 195,301 | `278fec7f1d5a9c9601b2a419ed58da4016cc5d243170cc988d272f9a306ca074` |
| `cycle06_f6on-chat-5c28dd85.png` | 对话流（全量口径） | 1400×900 | 273,769 | `49c94164c7e939ae41fc2208784a9ded1cf38c3a8320e43943905c91ac668238` |
| `cycle06_f6on-rhythm-5c28dd85.png` | 节律·串门 | 1300×1050 | 285,395 | `c65817762ff9fde66c5346003a7c56092b2cf6c9468d33a169ff41377d8b2a1f` |
| `cycle06_f6on-600-5c28dd85.png` | 600px 判读 | 600×900 | 195,436 | `dfbdda75706b1a497ef27973e7fc95190f10fb917ec16a987b32954436afc5f9` |

绝对路径前缀：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/cycle06_shots/`

### 2.2 隔离件（**不作为证据**，仅取证留存，见 `_blank_check_failed/`）

| 文件 | 字节 | sha256 | 判定 |
|---|---|---|---|
| `_blank_check_failed/cycle06_f6off-spread-dbff7b97.png` | 176,763 | `74826158a50cf63935a29c15abbb85bd2f3607e74f95d2715b876fcb8aa7b01d` | `SHOT FAIL`：最大单色占比 **71.17% ≥ 50%**，色≈`(0,16,16)`，第 3 次空白重试耗尽，`rc=1` |
| `_blank_check_failed/cycle06_f6on-spread-5c28dd85.png` | 177,082 | `07b2519201f98f4149c2c77d45bec1f24a085169a05d63276d410b53f523b40b` | 同上：**71.16%**，`rc=1` |

原因（事实）：`spread`（闲话怎么传开）视图本身是大面积深色背景——CYCLE-05 同视图实测 `max_color_frac=71.20%`，当时因旧 wrapper 传 `--no-blank-check` 而放行。本次按任务约束**不绕过空白检测**，故该视图在 50% 阈值下必然 FAIL。**因此本目录的有效截图只含 3 种视图，不含 spread。**

### 2.3 派生页面数据（**未跟踪**，与 CYCLE-04/05 同处理）

| 文件 | 字节 | sha256 | 自证字段 |
|---|---|---|---|
| `code/frontend/sample/dialogue_cycle06_f6off/threads.json` | 4,537,637 | `aa5a095d561612068e7ce8c52cc58d1795afea3587cf4caeee5eef81cdd4b0cd` | `source.run_sha256=dbff7b97…`、`source.meta_json.code_sha=d7d1d93…`、`stats={messages:686,threads:206,threads_ge3_turns:90,max_turns:18}` |
| `code/frontend/sample/dialogue_cycle06_f6on/threads.json` | 4,610,607 | `adbbb15c3cb6d18783c52dd533cb363d2dd5bba8b2712412b798c37ee28688de` | `source.run_sha256=5c28dd85…`、`source.meta_json.code_sha=e8a9fd5…`、`stats` 同上 |

`render_wrap.log`（3,960 B，sha256 `f59bb0e70e21dd628525503d51c17c66b68f38657ab37a8478127cd59ce09b8d`）——含 `RENDER_START_OFF/ON`、`RENDER_END`、8 次 `→ BEGIN/END` 与 `SHOT OK / SHOT FAIL` 行，以及本次渲染用的 chrome 探测链路（见 §3）。

## 3. 复现命令（实际执行的命令，逐字）

与 CYCLE-05 的差异（**唯一一处，且是更严**）：旧 wrapper `dialogue_shots.sh` 内部固定传 `--no-blank-check`，会**关掉**空白检测；本次按任务约束改为**直接调用同一条管线的 `shot.py`，保留空白检测**（参数仅 `--width/--height/--timeout`），判定逻辑与阈值一字未改。

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code

# ① 从真源日志派生页面数据（只读日志，不写世界、不调 LLM）
python3 frontend/tools/gen_threads.py \
  --log ../v2/evidence/run_d1_f6off_seed42_n16r84/run.jsonl \
  --meta ../v2/evidence/run_d1_f6off_seed42_n16r84/meta.json \
  --out frontend/sample/dialogue_cycle06_f6off/threads.json --label cycle06_f6off
python3 frontend/tools/gen_threads.py \
  --log ../v2/evidence/run_d1_f6on_seed42_n16r84/run.jsonl \
  --meta ../v2/evidence/run_d1_f6on_seed42_n16r84/meta.json \
  --out frontend/sample/dialogue_cycle06_f6on/threads.json --label cycle06_f6on

# ② 起静态服务（本次用 8971，避开常驻端口）
nohup python3 frontend/tools/serve.py --port 8971 --host 127.0.0.1 > /tmp/c06_serve.log 2>&1 &

# ③ 出三视图真截图（示例：OFF 臂 chat；其余同理换 view 与尺寸）
python3 frontend/tools/shot.py \
  --url "http://127.0.0.1:8971/dialogue.html?still=1&multi=0&min=0&data=sample/dialogue_cycle06_f6off/threads.json" \
  --out ../v2/evidence/cycle06_shots/cycle06_f6off-chat-dbff7b97.png \
  --width 1400 --height 900 --timeout 180
# rhythm: +&view=rhythm, 1300x1050 ; spread: +&view=spread, 1300x900 ; 600: 600x900

# ④ 收工
pkill -f 'serve.py --port 8971'
```

浏览器探测：`python3 frontend/tools/_chrome.py` → `/usr/bin/chromium-browser`（rc=0）；`playwright` 可用（`/opt/openjiuwen/workswarm-venv/lib/python3.12/site-packages/playwright`）。

渲染读数（`render_wrap.log` 原文摘要，**未改写数值**）：

```
SHOT OK: ...cycle06_f6off-chat-dbff7b97.png    elapsed=2.05s  mean_brightness=34.8  max_color_frac=31.16%  blank_retries=0/2
SHOT OK: ...cycle06_f6off-rhythm-dbff7b97.png  elapsed=1.80s  mean_brightness=33.6  max_color_frac=35.60%  blank_retries=0/2
SHOT FAIL: 画面近乎单色（最大单色占比 71.17% ≥ 50%，色≈(0, 16, 16)） —— 第 3 次空白（重试耗尽）
SHOT OK: ...cycle06_f6off-600-dbff7b97.png     elapsed=2.00s  mean_brightness=39.9  max_color_frac=28.90%  blank_retries=0/2
SHOT OK: ...cycle06_f6on-chat-5c28dd85.png     elapsed=2.05s  mean_brightness=34.8  max_color_frac=31.15%  blank_retries=0/2
SHOT OK: ...cycle06_f6on-rhythm-5c28dd85.png   elapsed=1.80s  mean_brightness=33.6  max_color_frac=35.59%  blank_retries=0/2
SHOT FAIL: 画面近乎单色（最大单色占比 71.16% ≥ 50%，色≈(0, 16, 16)） —— 第 3 次空白（重试耗尽）
SHOT OK: ...cycle06_f6on-600-5c28dd85.png      elapsed=1.93s  mean_brightness=39.9  max_color_frac=28.94%  blank_retries=0/2
```

内容抽检（第三方视觉模型对 `cycle06_f6off-chat-dbff7b97.png` 的描述，仅作"非空白/是对话页"的旁证，**不入指标**）：标题「青溪镇·对话观看台」、左侧筛选栏、7 天×4 时段网格、下方中文对话气泡与轮次计数，底部进度指示 `686 / 686`。

## 4. 已尝试但未采用的图源

| 候选 | 未采用原因 |
|---|---|
| `run_f6off_cycle06_seed42_n16r84/run.jsonl` | 04:36 实测仍在 round 31/84 运行（pid 2605250），会截到半成品日志 |
| `run_scene_anchor_on_seed42_n16r24` | 真实且已核 sha（`8a5a88ac…`），但**只有 ON 单臂**，与其他臂无可比性；本次先取成对两臂，故未渲染 |
| `run_d12b_off/on_seed7_n16r24` | 两臂 `run.jsonl` 无 `meta.json`（`systemd-run` 路径），页面 `seed`/meta 字段会显示为派生值，与 README 三重标注的"规模/树"一栏对不齐 |
| `samples_d1_f6_*` | 是样本 md/json 派生物，非 run 事件日志，不能作 `gen_threads.py` 输入 |

## 5. 已知限制

- **两臂不同树**：OFF `d7d1d93` / ON `e8a9fd5` ⇒ 本目录 6 张图**不能**当作"同树开关对照"的视觉证据，只能各自代表该批的页面外观。
- **视图缺 1 种**：`spread` 两图在保留空白检测下 FAIL（§2.2），有效图为 3 视图 × 2 臂 = 6 张，**不是** 4 视图 × 2 臂。
- `shot.py` 的 `SHOT OK:` 行本身不带时间戳（CYCLE-04 登记的缺口 G-2，本期仍未修）⇒ 渲染时刻由 `render_wrap.log` 的 wrapper 行（`→ BEGIN/END`、`RENDER_START/END`）佐证。
- 页面为**只读回放**：`gen_threads.py` 只读 `run.jsonl`，未跑世界、未调 LLM、未改任何日志。
- 截图**不参与**任何判据；本周期指标判定见 `v2/evidence/d12b_result.md`、`d12a_q_a_result.md` 与 `evidence-index-CYCLE-06.md` §4。
