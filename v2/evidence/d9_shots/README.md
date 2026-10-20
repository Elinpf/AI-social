# `v2/evidence/d9_shots/` — D9 臂四视图真实截图索引

> 性质：**D9 臂（`reply_window_rounds` 2→4，commit `05636bc`）本批真实渲染的截图**。
> A0 四图（`v2/evidence/d7_shots/`）在本目录中**仅作对照引用**，不复制、不改名、不重渲染。
> 两批**不同源**：D9 = `run_d9_a1_n16r84_seed42`（日志 `abefdf73…`），A0 = `run_d2_after_n16_seed42`（日志 `643f13a5…`）。**不得互称**。

---

## 0. D9 四视图（本批真拍）

| 视图 | 文件 | 实际尺寸 | sha256 | sha8 |
|---|---|---|---|---|
| chat（对话流） | `run_d9_a1_n16r84_seed42-chat-abefdf73.png` | 1400×900 | `dd9a77dbb6ca1fb50b87642d8ac26a040f500b0ccb1202b8b4abb58924bfc99f` | `dd9a77db` |
| rhythm（节律·串门） | `run_d9_a1_n16r84_seed42-rhythm-abefdf73.png` | 1300×1050 | `06ce63dc99a60287a9da2c27226e6b4959c6709fe9f06b7d333ce7c6533cfaee` | `06ce63dc` |
| spread（闲话怎么传开） | `run_d9_a1_n16r84_seed42-spread-abefdf73.png` | 1300×900 | `eccfd3aacd09aa29404dd455e7ef9851b272d49ed4a5306da24fdecf9b554d3d` | `eccfd3aa` |
| 600（600px 窄屏判读） | `run_d9_a1_n16r84_seed42-600-abefdf73.png` | 600×900 | `32b0ac5f796a6f3e831843dd1377191525f1d244dfd5b7c116ec4305bf9f7c58` | `32b0ac5f` |

**命名规则**：`run_d9_a1_n16r84_seed42-<视图>-<sha8>.png`，其中 `sha8` = **源日志 `run.jsonl` 的 sha256 前 8 位**（`abefdf73ca239cda6b4b11ebf1081949f9f278586989d392113b5c57e1c9f427` → `abefdf73`）。
选它而非 `code_sha` 的理由：与仓库既有 `d7_shots`/`d8_*` 的「`sha8` = 日志 sha256 前缀」约定一致（文件名即可反查数据源），且 `dialogue_shots.sh` 的 STEM/`sha8` 自动派生本就取自 `threads.json` 的 `source.run_sha256`，二者自洽。

**画幅口径**：以 `code/frontend/tools/dialogue_shots.sh:16-19` 的声明为准（chat 1400×900 / rhythm 1300×1050 / spread 1300×900 / 600 600×900）。
`code/frontend/tools/shot.py` 的 `--width 1500 --height 950` 是**未被该脚本使用的默认值**，本组图**不是** 1500×950；也**禁止**为对齐 1500×950 重渲染（会与 R5/R7 已登记 sha 链条不一致）。

---

## 1. 四件套证据链（每图同源）

| 证据项 | 值 |
|---|---|
| ① 源 run 目录 | `v2/evidence/run_d9_a1_n16r84_seed42/`（`meta.json` / `host.log` / `llmcost.json` 已入库） |
| ② 渲染命令 | 见 §2「生产命令」与「复现命令」两行 |
| ③ **日志 sha256** | `abefdf73ca239cda6b4b11ebf1081949f9f278586989d392113b5c57e1c9f427`（`run.jsonl`，91,343,119 B，`wc -l`=194,126 = `meta.events`；被 `.gitignore:8` 的 `**/*.jsonl` 忽略，**不入库**但存在于工作树、可直接渲染） |
| ④ **派生 `threads.json` sha256** | `301b1fd3ac8784e6b980a85a3d4ffe008d181dd78c8536dee8a56b19dc658ef4`（`code/frontend/sample/dialogue_run_d9_a1_n16r84_seed42/threads.json`，4,363,056 B） |

### 1.1 `threads.json` 派生命令（本表 ④ 的来源）

```bash
python3 code/frontend/tools/gen_threads.py \
  --log v2/evidence/run_d9_a1_n16r84_seed42/run.jsonl \
  --meta v2/evidence/run_d9_a1_n16r84_seed42/meta.json \
  --out code/frontend/sample/dialogue_run_d9_a1_n16r84_seed42/threads.json \
  --require-complete --label run_d9_a1_n16r84_seed42-abefdf73
```

实测输出（原文）：`完整性断言通过：TURN_SEAL 84 条覆盖 round 0..83`；`events=194126 messages=686 threads=206 multi_turn=104 ge3=90 legacy_msgs=0 moves=406 ref_edges=0 echoes=0`。
`--require-complete` 是**前置断言**：`meta.json` 缺失或 `TURN_SEAL` 未覆盖 `round 0..83` 时**不生成**并退出码 3，用于防止把半截跑批做成演示数据集。
`--label` 决定 `threads.json` 的 `source.run_label`；`dialogue_shots.sh:44/48` 若无 `run_label` 会 exit 2，且显式传入的 label/sha8 与数据源不一致也 exit 2——本次留空由数据源自派生，因此该自校验本身即「文件名 ↔ 数据源」的双向校验。

---

## 2. 生产命令 vs 复现命令（两条，参数一致）

```bash
# ① 生产命令（本组图实际执行；在 code/ 下执行，服务已在 127.0.0.1:<port>）
cd code && bash frontend/tools/dialogue_shots.sh \
  http://127.0.0.1:<port> sample/dialogue_run_d9_a1_n16r84_seed42/threads.json \
  "" "" ../v2/evidence/d9_shots
#    第 3/4 参留空 = 由 threads.json 的 source.run_label / source.run_sha256 自动派生（与数据源不一致即 exit 2）

# ② 复现命令（单视图手工复算，与 ① 的参数形态相同；dialogue_shots.sh:64 的 shot() 本身也传 --no-blank-check）
cd code && python3 frontend/tools/shot.py \
  --url "http://127.0.0.1:<port>/dialogue.html?still=1&multi=0&min=0&data=sample/dialogue_run_d9_a1_n16r84_seed42/threads.json" \
  --out <任意输出路径>.png --width 1400 --height 900 --no-blank-check
#    rhythm 视图在查询串追加 &view=rhythm（1300×1050）；spread 追加 &view=spread（1300×900）；600 视图 600×900
```

- **生产与复现参数一致**：`dialogue_shots.sh` 的 `shot()` 亦传 `--no-blank-check`（该脚本第 64 行），故不存在「用不同参数对拍」的问题。
- `shot.py` 的真实接口只有 `--url / --out / --width / --height / --wait-fn / --retry-blank / --full-page / --no-blank-check / --chrome`；**没有** `--log / --round / --still`，日志与视图走 **URL 查询串**（`data=` 指定 `threads.json`，`view=` 指定视图，`still=1&multi=0&min=0` 为生产口径）。

### 2.1 渲染确定性核验（dry-run，产物不入库）

```bash
# 以 A0 既有数据复渲染同一视图，仅用于证明渲染链路可复现（输出落 /tmp，不作仓库证据）
cd code && python3 frontend/tools/shot.py \
  --url "http://127.0.0.1:<port>/dialogue.html?still=1&multi=0&min=0&data=sample/dialogue_run_d2_after_n16_seed42/threads.json" \
  --out /tmp/dryrun_chat.png --width 1400 --height 900 --no-blank-check
# 实测：rc=0，2.6 s，blank_retries=0/2
# 产物 sha256 = 15d02ab24f964e249aafcaaf59ea83f62e9f8a9298d0f6deeffb7d68b39c3da3
# 与 v2/evidence/d7_shots/run_d2_after_n16_seed42-chat-643f13a5.png 逐位相同
```
⇒ 渲染链路在当前环境**字节级可复现**；将来若有人怀疑既有 A0 图被替换，用同一命令重跑即可对拍。**`/tmp` 产物不入库、不作证据**，仓库证据仅本目录 D9 四图与 `d7_shots/` A0 四图。

---

## 3. A0 对照四图（复用 `d7_shots`，未重渲染）

| 视图 | 文件（`v2/evidence/d7_shots/`） | 实际尺寸 | sha256 | sha8 |
|---|---|---|---|---|
| chat | `run_d2_after_n16_seed42-chat-643f13a5.png` | 1400×900 | `15d02ab24f964e249aafcaaf59ea83f62e9f8a9298d0f6deeffb7d68b39c3da3` | `15d02ab2` |
| rhythm | `run_d2_after_n16_seed42-rhythm-643f13a5.png` | 1300×1050 | `baf2d9fc5153d4d00728569117b73454cfc41d51871211a101e180e66acc761e` | `baf2d9fc` |
| spread | `run_d2_after_n16_seed42-spread-643f13a5.png` | 1300×900 | `eae35979f60dd6bdda083e6a5633fa9c61d49040845627bc75af4b64711b86ac` | `eae35979` |
| 600 | `run_d2_after_n16_seed42-600-643f13a5.png` | 600×900 | `45bf561c97c79d09e414716a5ee6c2063eb52e857249e4338c8d70eb2d8025e9` | `45bf561c` |

- 这四图**未被复制**到本目录，也未重渲染；`R5 §4` 已登记其 sha256，此处引用值与之逐位一致。
- 交叉验证：四个 sha8 与 commit `f713e68`「A0 四张截图按新标签重出（新 15d02ab2/baf2d9fc/eae35979/45bf561c）」的说明**吻合** ⇒ 引用的是**现行版**，不是已作废的 `2026-10-20 20:24` 旧版（旧版 sha8：`44b7fb23`/`d553eaba`/`aab855e4`/`fad59476`）。

---

## 4. 可打开性与「非退化帧」判据

四组 PNG 均以 Pillow **全解码**（`im.load()`）通过，并统计唯一 RGB 色数，用以排除 `shot.py` 头部记载的 **T282「首帧黑/白图」假证据**：

| 视图 | D9 色数 | A0 对照色数 |
|---|---|---|
| chat | 22122 | 22150 |
| rhythm | 22952 | 22959 |
| spread | 16109 | 16122 |
| 600 | 18553 | 18495 |

D9 与 A0 的色数**量级一致但数值不同** ⇒ 两张图是**不同批次的不同渲染**，而非同一文件改名（若为改名，sha256 会完全相同）。

---

## 5. 渲染过程记录（如实，含重试/失败）

完整 stdout 见本目录 `render.log`（sha256 `14d17bf50ae1dc20becfe4bab6f23480a6c5b98cc484d2827cc1a7c9ec188b78`）。摘要：

| 视图 | 耗时 | `blank_retries` | 结果 |
|---|---|---|---|
| chat | 2.17 s | 0/2 | OK |
| rhythm | 1.71 s | 0/2 | OK |
| spread | 1.61 s | 0/2 | OK |
| 600 | 1.77 s | 0/2 | OK |

- **本批 0 次失败、0 次空白重试**；脚本总退出码 `render_rc=0`。
- `shot.py` 打印的 `blank_cumulative=7/124…127` 是**跨次累计**观察哨（T282 留痕，非本批失败），本批未触发重试。
- 服务为临时实例 `python3 frontend/tools/serve.py --port 8899`（`setsid --fork` 起），**渲染完成后已显式停服**（`curl` 返回 `http_rc=000`/`rc=7` 连接拒绝，端口已释放）。仓库 8848 服务与本任务无关，未动。
- 运行前置：`pgrep -fa "orchestration[ ]run"` 空输出（rc=1）；本任务**全程未启动任何 `orchestration run`**。

---

## 6. 一句话结论与边界

- 本目录四图为 **D9 臂（`05636bc`，n16×84，seed 42）真实渲染**，数据源 `run_d9_a1_n16r84_seed42/run.jsonl`（`abefdf73…`）。
- A0 四图为**对照**，来自 `run_d2_after_n16_seed42`（`643f13a5…`），未复制、未重渲染。
- 截图只作**呈现层证据**：它证明「D9 批次的数据能被前端正确渲染为可判读的对话/节律/扩散视图」，**不**证明任何行为改善。行为结论以 `reports/d9-readings.md` 与 `reports/R8-dialogue-density.md` 的读数与边界为准（含「窗口放宽未改变对话结构」的 dead-parameter 判定）。
