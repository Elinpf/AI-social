# `v2/evidence/a1_shots/` — A1 措辞臂（n4r60 seed42）四视图真实截图索引

> 性质：**A1 臂本批（`feat/wording-a1`，code_sha `a637371`）真实渲染的截图**，来源日志 `run_a1_wording_n4r60_seed42/run.jsonl`（`ae969198…`）。
> **批次定性：方向性筛查**（4 agents × 60 rounds，seed 42，124 条 MSG），**不可与 A0 正式臂（16×84，686 条 MSG）直接比**。A0 图在本目录中**不引用、不复制**。

---

## 0. 四视图

| 视图 | 文件 | 实际尺寸 | sha256 | sha8 |
|---|---|---|---|---|
| chat（对话流） | `run_a1_wording_n4r60_seed42-chat-ae969198.png` | 1400×900 | `0e05129bb9779691044a6eb933cd844c47e5651a9e9d01744a17a0b1dbb311d5` | `0e05129b` |
| rhythm（节律·串门） | `run_a1_wording_n4r60_seed42-rhythm-ae969198.png` | 1300×1050 | `7c3d7eea9c1f130607bd3ed411a683843ae41a1c99a0baee33a7bf1aa95959c8` | `7c3d7eea` |
| spread（闲话怎么传开） | `run_a1_wording_n4r60_seed42-spread-ae969198.png` | 1300×900 | `c3fc91ec399f9a70eb2994521fde0395d2da5f8746dbb05c7f2feba2a708b17f` | `c3fc91ec` |
| 600（600px 窄屏判读） | `run_a1_wording_n4r60_seed42-600-ae969198.png` | 600×900 | `13ce8b1953fa1db30e27596b6b044f0ba13ff43aebb772d123c07a6e0792114b` | `13ce8b19` |

**命名规则**：`run_a1_wording_n4r60_seed42-<视图>-<sha8>.png`，`sha8` = **源日志 `run.jsonl` sha256 前 8 位**（`ae969198feaefd1f69147001e027394d55527bd1a0e460ff654697bdc3b1559b` → `ae969198`），与 `d7_shots` / `d8_*` / `d9_shots` 的既有约定一致（文件名即可反查数据源）。

**画幅口径**：以 `code/frontend/tools/dialogue_shots.sh:16-19` 声明为准（chat 1400×900 / rhythm 1300×1050 / spread 1300×900 / 600 600×900）。`shot.py` 的 `--width 1500 --height 950` 是**未被该脚本使用的默认值**，本组图**不是** 1500×950。

---

## 1. 四件套证据链

| 证据项 | 值 |
|---|---|
| ① 源 run 目录 | `v2/evidence/run_a1_wording_n4r60_seed42/`（`meta.json` / `host.log` / `llmcost.json` 同目录；`run.jsonl` 被 `.gitignore:8` 的 `**/*.jsonl` 忽略，**不入库**但存在于工作树） |
| ② 渲染命令 | 见 §2「生产命令 / 复现命令」两行 |
| ③ **日志 sha256** | `ae969198feaefd1f69147001e027394d55527bd1a0e460ff654697bdc3b1559b`（4,749,329 B，`wc -l`=9,940 = `meta.events`） |
| ④ **派生 `threads.json` sha256** | `e3cefe6bf504fd6f8249980436d7d8e38f81a95ed5d4b11319d476b49fa44d27`（`code/frontend/sample/dialogue_a1_wording_n4r60_seed42/threads.json`，411,358 B） |

### 1.1 `threads.json` 派生命令

```bash
python3 code/frontend/tools/gen_threads.py \
  --log v2/evidence/run_a1_wording_n4r60_seed42/run.jsonl \
  --meta v2/evidence/run_a1_wording_n4r60_seed42/meta.json \
  --out code/frontend/sample/dialogue_a1_wording_n4r60_seed42/threads.json \
  --require-complete --label run_a1_wording_n4r60_seed42-ae969198
```

实测输出（原文）：`完整性断言通过：TURN_SEAL 60 条覆盖 round 0..59`；`events=9940 messages=124 threads=40 multi_turn=20 ge3=18 legacy_msgs=0 moves=77 ref_edges=0 echoes=0`。

---

## 2. 生产命令 vs 复现命令

```bash
# ① 生产命令（本组图实际执行；在 code/ 下，服务临时起在 127.0.0.1:8901）
cd code && bash frontend/tools/dialogue_shots.sh \
  http://127.0.0.1:8901 sample/dialogue_a1_wording_n4r60_seed42/threads.json \
  "" "" ../v2/evidence/a1_shots

# ② 复现命令（单视图手工复算；参数形态与 ① 相同，dialogue_shots.sh:64 的 shot() 本就传 --no-blank-check）
cd code && python3 frontend/tools/shot.py \
  --url "http://127.0.0.1:<port>/dialogue.html?still=1&multi=0&min=0&data=sample/dialogue_a1_wording_n4r60_seed42/threads.json" \
  --out <任意输出路径>.png --width 1400 --height 900 --no-blank-check
#    rhythm 视图追加 &view=rhythm（1300×1050）；spread 追加 &view=spread（1300×900）；600 视图 600×900
```

- `shot.py` 的真实接口只有 `--url / --out / --width / --height / --wait-fn / --retry-blank / --full-page / --no-blank-check / --chrome`；**没有** `--log / --round / --still`，日志与视图走 **URL 查询串**。
- 生产与复现参数一致（`--no-blank-check` 两处都传），不存在「用不同参数对拍」。

---

## 3. 可打开性与非退化帧判据

四图均 Pillow **全解码**通过、PNG 魔数 `\x89PNG\r\n\x1a\n` 校验 True，唯一 RGB 色数：chat 22646 / rhythm 21374 / spread 16090 / 600 18875（远非单色，排除 `shot.py` 头部 T282「首帧黑/白图」假证据）。

---

## 4. 渲染过程记录（如实）

完整 stdout 见本目录 `render.log`（sha256 `6ec172f28f41068c3977c9caa23bb61dc7b1cdd60f6dd5522441995240817213`）。

| 视图 | 耗时 | `blank_retries` | 结果 |
|---|---|---|---|
| chat | 3.64 s | 0/2 | OK |
| rhythm | 1.68 s | 0/2 | OK |
| spread | 1.65 s | 0/2 | OK |
| 600 | 1.59 s | 0/2 | OK |

- **本批 0 失败、0 空白重试**，脚本退出码 0。
- 临时服务 `python3 frontend/tools/serve.py --port 8901`（`setsid --fork` 起），**渲染完成后已停服**（`curl` 返回 `http_rc=000` / rc=7，`ss` 无 8901 监听）。仓库 8848 服务与本任务无关，未动。
- 运行时前置与 SID 校验证据见 `v2/evidence/a1_launch_evidence.txt`（含首次 `bash` 调用 300 s **工具层**超时、非跑批失败的记录）。

---

## 5. 边界

截图只作**呈现层证据**：证明 A1 批次的数据能被前端正确渲染为可判读的对话/节律/扩散视图，**不**证明措辞改善。行为与措辞结论以 `v2/evidence/d5_metrics_a1.{md,json}` 为准，且因 n4r60 规模（124 MSG、admission `REJECTED` 于 `B-15_msg_volume` 的 `MSG>=150` 下限）只能作为**方向性筛查**，**不可与 A0 16×84 直接比**。
