# CYCLE-07 页面截图证据（本期现场渲染，来自 D12-C 两臂真 LLM 日志）

> 生成者：`case-curator`（案例与截图策展人）｜渲染时刻：**2026-10-23T08:32:55–08:33:15 +0800**（见本目录 `render_wrap.log` 的 `RENDER_START` / 每条 `→ BEGIN/END`，均带 ISO 时间戳）
> 与报告的关系：这 4 张图供 `reports/CYCLE-07-*.md` 第四节引用；素材清单与对话原文见团队工作区 `cycle07/cases.md`。
> 图源纪律：只选本周期真实存在、sha256 已实算的 `run.jsonl`；**未关闭空白检测**（与 CYCLE-05 的旧 wrapper 不同，本次不传 `--no-blank-check`）。

## 1. 三重标注（缺一条即为引用错误）

| 项 | OFF 臂 | ON 臂 |
|---|---|---|
| 图源批次 | `v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl` | `v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl` |
| 该日志 sha256 | `3c814121b5f8d4b053358c959c926f4e14b8a57bf2c6206dadc94d6695c81a74`（sha8 `3c814121`） | `bd2df77fd125cc75c31f261cc05486bd7376d9a9fcd9334f083cf8897e496c87`（sha8 `bd2df77f`） |
| 日志事件 / MSG / 线程 | 116,365 / 510 / 169 | 116,421 / 510 / 169 |
| 派生页面数据 | `code/frontend/sample/dialogue_cycle07_d12c_off/threads.json`（sha256 `fe68e645c8b494628201b3e8778570ab84b30f88f53eeb85c10c53e1d70e9a4f`） | `code/frontend/sample/dialogue_cycle07_d12c_on/threads.json`（sha256 `7ac7aea59205072c2e9d32478be847dee4ad1e9c4ff1de322388945de3429d3a`） |
| 树（`meta.json.sha`） | `a977cb0` | `a977cb0`（两臂同树） |
| 开关真值 | `switch_proof.txt` 无 `LIFE_PROMPT_D12C_SPECIFIC` | `switch_proof.txt`：`LIFE_PROMPT_D12C_SPECIFIC=1`（取自 `/proc/<pid>/environ`） |
| 起跑 / 收工 | 05:57:04 → 06:47:03 | 06:58:58 → 07:38:28 |
| **能证明什么** | 该批真日志在 `dialogue.html` 上**页面外观可读、非空白**，底部计数 `510 / 510` 与 `stats.messages=510` 一致，事件数与日志 `wc -l` 一致 | 同左（事件 116,421） |
| **不能证明什么** | 不作为任何效果/质量证据；截图**不参与**任何判据 | 同左 |

文件名中的 `3c814121` / `bd2df77f` 即日志 sha256 前 8 位，由 `gen_threads.py` 写入 `threads.json.source.run_sha256`，**不是人工填写**。

## 2. 文件与 sha256（`sha256sum` / `stat` 实跑）

| 文件 | 视图 | 画幅 | 字节 | sha256 |
|---|---|---|---|---|
| `cycle07_d12c_off-chat-3c814121.png` | 对话流（全量口径） | 1400×900 | 265,909 | `3c68ade96f5626aea9865750cbc97a717f50dba856c0bbd49db5e8b3b007507d` |
| `cycle07_d12c_off-rhythm-3c814121.png` | 节律·串门 | 1300×1050 | 282,601 | `496620318406300e568f31b34c12b20ba266e4a0f6c47b45d6afd3329f87d99d` |
| `cycle07_d12c_on-chat-bd2df77f.png` | 对话流（全量口径） | 1400×900 | 267,935 | `421588e53c5f4e39bb136aea0479a32dd1c7c49503687ab2fbe6abbeba6fd3a8` |
| `cycle07_d12c_on-rhythm-bd2df77f.png` | 节律·串门 | 1300×1050 | 282,569 | `69225dcfb987f032ccdb76540623802ac77e9b0acd41668f5e3ed84fc72068b6` |

绝对路径前缀：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/cycle07_shots/`

**空白检测**：4 张全部 `SHOT OK`、`blank_retries=0/2`、`max_color_frac` 最高 34.44%（阈值 50%）。`_blank_check_failed/` 本次**为空**——没有需要隔离弃用的图。

## 3. 复现命令（实际执行的命令，逐字）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code

# ① 真源日志 → 页面数据（只读日志，不写世界、不调 LLM）
python3 frontend/tools/gen_threads.py \
  --log ../v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl \
  --meta ../v2/evidence/run_d12c_off_n16r60_seed42/meta.json \
  --out frontend/sample/dialogue_cycle07_d12c_off/threads.json --label cycle07_d12c_off
python3 frontend/tools/gen_threads.py \
  --log ../v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl \
  --meta ../v2/evidence/run_d12c_on_n16r60_seed42/meta.json \
  --out frontend/sample/dialogue_cycle07_d12c_on/threads.json --label cycle07_d12c_on

# ② 起静态服务（8971，避开常驻端口）
nohup python3 frontend/tools/serve.py --port 8971 --host 127.0.0.1 > /tmp/c07/serve.log 2>&1 &

# ③ 出图（示例：OFF 臂 chat；其余按 arm × view 换参数）
python3 frontend/tools/shot.py \
  --url "http://127.0.0.1:8971/dialogue.html?still=1&multi=0&min=0&data=sample/dialogue_cycle07_d12c_off/threads.json" \
  --out ../v2/evidence/cycle07_shots/cycle07_d12c_off-chat-3c814121.png \
  --width 1400 --height 900 --timeout 180
# rhythm: URL 追加 &view=rhythm，尺寸 1300x1050

# ④ 收工
pkill -f 'serve.py --port 8971'
```

浏览器探测：`python3 frontend/tools/_chrome.py` → `/usr/bin/chromium-browser`。
渲染读数见本目录 `render_wrap.log`（含 `SHOT OK` 逐行 `mean_brightness` / `max_color_frac` / `blank_retries`，未改写数值）。

## 4. 已尝试但未采用的视图

| 候选 | 未采用原因 |
|---|---|
| `spread`（闲话怎么传开） | 本批 `threads.json` 的 `stats.ref_edges=0`（日志 `refs` 全空）、`echo_groups=0` ⇒ 该视图必然是空态图；按纪律**不用旧周期 spread 图充数**，本次只出 2 视图 × 2 臂 |

## 5. 已知限制

- 本批跑在 `a977cb0`，**早于 L-13 人话映射修复（`882e5dd`）**；正文里可见内部 token（`mentorship` / `scarcity`），属该树既有缺陷，见 `v2/evidence/l13_default_label_review.md` §4.3。
- `shot.py` 的 `SHOT OK:` 行本身不带时间戳（CYCLE-04 登记的缺口 G-2，仍未修）⇒ 渲染时刻由 `render_wrap.log` 的 wrapper 行佐证。
- 页面为**只读回放**：`gen_threads.py` 只读 `run.jsonl`，未跑世界、未调 LLM、未改任何日志。
- 截图**不参与**任何判据；本周期指标判定见 `v2/evidence/d12c_result.md`。
- 观察量复算脚本：`count_cycle07_observations.py`（sha256 `4fd2a5c53853eb51329472039f6f1b6955bce1fadb3b87cf9f444ca019175237`），**非判据**。
