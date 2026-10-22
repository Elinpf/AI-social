# CYCLE-05 截图证据（本期现场渲染，来自 D12-A 问题(a) 同树 OFF/ON 两臂）

> 生成者：`report-writer`（撰写 `reports/CYCLE-05-20261023.md` 时现场渲染）
> 生成时刻：**2026-10-23T00:32:06–00:32:25 +0800**（`render_wrap.log` 的 `RENDER_START` / `RENDER_END_OFF` / `RENDER_START_ON` / `RENDER_END_ON`，由 wrapper 写入；`shot.py` 自身的 `SHOT OK:` 行不含时间戳，属已知缺口 G-2）
> 定位：证据分析师 `evidence-inventory.md` §5.1 判定本期（`8768dfb..HEAD`）**零新增截图**，并在 §5.4 给出选项 C「由 report-writer 成稿时现场渲染」。本目录即按选项 C 执行，源日志为**本期新跑的真 LLM 两臂**，非上一周期资产复用。

## 1. 三重标注（缺一条即为引用错误）

| 项 | OFF 臂 | ON 臂 |
|---|---|---|
| 图源批次 | `v2/evidence/run_d12a_q_a_off_seed7_n16r24/run.jsonl` | `v2/evidence/run_d12a_q_a_on_seed7_n16r24/run.jsonl` |
| 该日志 sha256 | `252a5b42cab70b3784c6b6812453f9a2d3e4e8ffee3f10bd115ff1cdfc3cefa5`（sha8 `252a5b42`） | `a1d1b4cb92432ff045dd03bd4fc1fd2b20804b6121e6e18e1dd4d29437da1fc2`（sha8 `a1d1b4cb`） |
| 开关真值（`switch_proof.txt`） | `env_HITT_D12_DETAIL=<unset>` | `env_HITT_D12_DETAIL=1` |
| 规模 / 树 | seed=7, n=16, rounds=24, `code_sha=a6ae5e5` | 同左 |
| 渲染时刻 | `RENDER_START` → `RENDER_END_OFF`（见 `render_wrap.log`） | `RENDER_START_ON` → `RENDER_END_ON` |
| **能证明什么** | 该批真 LLM 世界/对话的**页面外观**（视图可读、非空、非白屏） | 同左，且与 OFF 同 seq 位置可对照 |

文件名中的 `252a5b42` / `a1d1b4cb` 即日志 sha256 前 8 位，由 `dialogue_shots.sh` 从 `threads.json.source.run_sha256` 自动派生并自校验（脚本内 `FAIL sha8 不一致` 分支未触发）。

**不能证明什么**：截图**不是**效果证据。本期判定见 `v2/evidence/d12a_q_a_result.md`——具体性 Δ 判定值 **+2.09pp < +3pp 阈值 ⇒ 不成立**；`len_p50` 41→50 成立。截图不参与任何判据。

## 2. 文件与 sha256

渲染输出（`sha256sum v2/evidence/cycle05_shots/*.png` 实跑）：

| 文件 | 视图 | 字节 | sha256 |
|---|---|---|---|
| `cycle05_d12a_off-chat-252a5b42.png` | 对话流（全量口径） | 268,672 | `d15986df4e133bb3da6546d939f694dafd641dc6036e45883b82c6ba78db34df` |
| `cycle05_d12a_off-rhythm-252a5b42.png` | 节律·串门 | 279,648 | `cb32702a14cc4c06d4e4134369e72470797cdc4428453191822a0fd17da3937c` |
| `cycle05_d12a_off-spread-252a5b42.png` | 闲话怎么传开 | 175,167 | `00e7c6cd03b628a1f7bf2230583ea5261d65fc3e3ccd3045139bfdc0af179eab` |
| `cycle05_d12a_off-600-252a5b42.png` | 600px 判读 | 188,143 | `6e4ad0da6add89c1a3a79e3f9868bca601126f9330808df7db32d4110ea88a27` |
| `cycle05_d12a_on-chat-a1d1b4cb.png` | 对话流（全量口径） | 271,734 | `132495916881d8419ce74573421dc48b4fc1d3613dc8b499b413104f655ff529` |
| `cycle05_d12a_on-rhythm-a1d1b4cb.png` | 节律·串门 | 279,930 | `34f9b02bdb8586e771e124730b2eabd52166cf680f6ce99df4e1e8dc01187402` |
| `cycle05_d12a_on-spread-a1d1b4cb.png` | 闲话怎么传开 | 175,438 | `081828889ef8d47725c25950025b5aa895540604bb083248ced17c49e873da44` |
| `cycle05_d12a_on-600-a1d1b4cb.png` | 600px 判读 | 195,295 | `4be3851f19d47fe1f0f6af356b271f2478a4a3ac001411fc40e15b4fc79d0caa` |
| `render_wrap.log` | 渲染原始输出（8 次 `SHOT OK` + wrapper 时间戳） | 3,173 | （不入表，随目录提交） |

派生页面数据（**未跟踪**，与 CYCLE-04 同处理）：

| 文件 | 字节 | 说明 |
|---|---|---|
| `code/frontend/sample/dialogue_cycle05_d12a_off/threads.json` | 751,867 | `gen_threads.py` 从 OFF 臂真源日志派生 |
| `code/frontend/sample/dialogue_cycle05_d12a_on/threads.json` | 756,453 | 同上，ON 臂 |

两文件自证字段：`source.run_sha256` 分别为 `252a5b42…` / `a1d1b4cb…`；`stats = {messages:191, threads:66, multi_turn_threads:32, threads_ge3_turns:28}`（两臂相同，与 `arm_state_check.txt` C4 的 `191/66/28` 一致）。

## 3. 复现命令（只读、幂等；与本次渲染逐字相同）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code
# ① 从真源日志派生页面数据（不写世界、不调 LLM）
python3 frontend/tools/gen_threads.py --log ../v2/evidence/run_d12a_q_a_off_seed7_n16r24/run.jsonl \
  --out frontend/sample/dialogue_cycle05_d12a_off/threads.json --label cycle05_d12a_off
python3 frontend/tools/gen_threads.py --log ../v2/evidence/run_d12a_q_a_on_seed7_n16r24/run.jsonl \
  --out frontend/sample/dialogue_cycle05_d12a_on/threads.json --label cycle05_d12a_on
# ② 起静态服务（本次用 8961，避开常驻端口）
nohup python3 frontend/tools/serve.py --port 8961 --host 127.0.0.1 > /tmp/c05_serve.log 2>&1 &
# ③ 出四视图真截图
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8961 sample/dialogue_cycle05_d12a_off/threads.json "" "" ../v2/evidence/cycle05_shots
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8961 sample/dialogue_cycle05_d12a_on/threads.json  "" "" ../v2/evidence/cycle05_shots
# ④ 收工
pkill -f 'serve.py --port 8961'
```

渲染读数（`render_wrap.log` 原文摘要）：

```
SHOT OK: …cycle05_d12a_off-chat-252a5b42.png    mean_brightness=33.x  max_color_frac=…  blank_retries=0/2
SHOT OK: …cycle05_d12a_off-rhythm-252a5b42.png  mean_brightness=30.6   max_color_frac=39.98%  blank_retries=0/2
SHOT OK: …cycle05_d12a_off-spread-252a5b42.png  mean_brightness=23.1   max_color_frac=71.20%  blank_retries=0/2
SHOT OK: …cycle05_d12a_off-600-252a5b42.png     mean_brightness=39.9   max_color_frac=32.41%  blank_retries=0/2
SHOT OK: …cycle05_d12a_on-chat-a1d1b4cb.png     mean_brightness=33.7   max_color_frac=30.56%  blank_retries=0/2
SHOT OK: …cycle05_d12a_on-rhythm-a1d1b4cb.png   mean_brightness=30.6   max_color_frac=39.99%  blank_retries=0/2
SHOT OK: …cycle05_d12a_on-spread-a1d1b4cb.png   mean_brightness=23.1   max_color_frac=71.21%  blank_retries=0/2
SHOT OK: …cycle05_d12a_on-600-a1d1b4cb.png      mean_brightness=40.8   max_color_frac=31.75%  blank_retries=0/2
OK: ../v2/evidence/cycle05_shots/cycle05_d12a_{off,on}-{chat,rhythm,spread,600}-{252a5b42,a1d1b4cb}.png
```

（首行亮度值以 `render_wrap.log` 原文为准；本 README 的摘要行只保留可读字段，未做数值改写。）

## 4. 已知限制

- `shot.py` 的 `SHOT OK:` 行**不含时间戳**（CYCLE-04 已登记的 G-2，本期仍未修）⇒ 渲染时刻以本目录 `render_wrap.log` 的 wrapper 行佐证。
- 8 张图 = **2 个批次 × 4 种视图**，同一批次内 4 图来自同一份 `threads.json`，**不是**四个不同批次。
- 两臂均**无 `meta.json`** ⇒ d5 准入 `REJECTED`（`B-7_files` 等失败），页面 `seed` 字段显示为 `—`、`meta` 状态为派生数据已对齐而非批次 meta（同 CYCLE-04 说明）。
- 截图**不参与**任何判据；不得以截图替代 `d12a_q_a_result.md` 的指标读数。
