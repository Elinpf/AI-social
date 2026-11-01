# R3 独立复核证据：C1 处境锚两臂（数据完整性 · 口径审计 · 真实截图）

| 项 | 值 |
|---|---|
| 复核任务 | 看板 `#R3-run`「独立复核 C1 两臂数据完整性、口径审计与真实截图（不新增跑批）」 |
| 复核人 | run-observer（跑批验证与证据报告官） |
| 复核性质 | **独立复算，不采信任何成员自述**；全部数字由本文件给出的命令现算得出 |
| 复核对象 | `v2/evidence/c1-scene-a0-20261101_n16r24_s42/`（A0 基线臂）、`v2/evidence/c1-scene-a1-20261101_n16r24_s42/`（A1 处境锚臂） |
| 被复核代码锚 | 两臂 `code_sha = code_sha_end = 8b64615b0c717a5a42db8d40ae9fff5b469cfe7d`（分支 `feat/r44-public-reply-inbound`） |
| 本轮是否新增跑批 | **否**。本文件引用的 LLM 调用全部来自 2026-11-01 已完成的两臂历史批次 |
| 生成时刻 | 2026-11-01 12:12（+08:00） |
| 复算环境 | 仓库根 `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment`，`python3`（venv `/opt/openjiuwen/workswarm-venv/bin/python3` 仅用于截图链） |

> 本文件是**证据文件**，不是结论性报告。对外结论由 `#R4-report` 的报告承担；本文件的职责是「每个数字可复算 + 每项判定有依据 + 边界条件写死」。

---

## 0. 口径与复算方式（先看这里）

1. **不采信原则**：凡是他人给过的数字，本文件一律重新计算并给出命令；与自述一致标 `一致`，不一致标 `不一致` 并给出差异。
2. **只读原则**：除 `A1_ACCEPT.txt` / `llm_cost.txt` / `llm_cost.gate.out`（归档用，零跑批）与 `v2/evidence/c1_scene_shots/`（截图）外，本复核不写任何文件；不修改 `code/life`、`code/orchestration`、`code/config`、`code/engine`。
3. **判定三档**（全文件统一）：`通过` / `不通过` / `不可判定`。数据不足写「证据不足」，不写「大概」「应该是」。
4. **分母纪律**：沿用仓库既定纪律——分母 < 30 只报条数不报比率；本文件涉及的一致率分母为 174 / 165，均 ≥ 30，可报比率。
5. **文件指纹**：两臂 `run.jsonl` 的 sha256 分别为
   - A0 `1bfeb51d0bb336abca748dad0b1a40375f702df204f9c42cfd0591f24f5dbcb4`
   - A1 `c828b4075f027917ce883670564b2a827b4f1feecd322315619f9ecbe9324633`
   二者与各自 `meta.run_sha256` 逐字相等（命令见 §11.1）。

---

## 1. 复核项①：数据完整性自查 → **通过**

### 1.1 行数 / 轮数 / TURN_SEAL 自洽（自己算，未引用他人结论）

命令（§11.2）：逐行解析 `run.jsonl`，统计行数、坏行、`seq` 连续性、每轮 `TURN_SEAL` 个数与轮末事件。

| 指标 | A0 | A1 |
|---|---|---|
| `run.jsonl` 行数 | 34096 | 34075 |
| `meta.events` | 34096 | 34075 |
| 行数 == `meta.events` | 是 | 是 |
| 坏行（JSON 解析失败） | 0 | 0 |
| `max_seq` | 34095 | 34074 |
| `seq` 连续（= 行号 − 1，无跳号） | 是 | 是 |
| 出现过的轮次数（`round` 值） | 24（0–23） | 24（0–23） |
| 每轮 `TURN_SEAL` 个数 | 24 轮各 1 个 | 24 轮各 1 个 |
| `TURN_SEAL` 是否每轮最后一条事件 | 是（违规轮次：无） | 是（违规轮次：无） |
| `run_batch.rc` | `0` | `0` |
| `rounds_contiguous`（meta） | `true` | `true` |

判定：两臂**均自洽**（行数=事件数、seq 无跳号、24 轮每轮恰好 1 个轮末 seal）。→ **通过**

### 1.2 两臂是否同一 code_sha（判定方法与输出）

判定方法（三重，互不依赖）：
1. 读两臂 `meta.code_sha` 与 `meta.code_sha_end`（跑前/跑后各记一次，由 `emit_run_meta.py` 落盘）；
2. 读两臂 `host.log` 首部 launcher 自记的 `code_sha=` 行（起跑时刻写死）；
3. 读两臂 `frozen_sha.txt`（`git rev-parse HEAD` 快照）。

输出：A0 与 A1 在这三处**均为** `8b64615b0c717a5a42db8d40ae9fff5b469cfe7d`；且各自 `code_sha == code_sha_end`（跑批期间零漂移）。
⇒ **两臂同码，且代码在两批期间未变**。→ **通过**

### 1.3 A0 side_root 被误写 211 文件 —— 用时间戳自己复算

命令（§11.3）：遍历 `/tmp/c1_scene_a0_n16r24_s42_side` 全部文件的 `mtime`，按时刻分桶。

| 事实 | 实测值 |
|---|---|
| A0 side_root 文件总数 | 3564 |
| 最早 mtime | 2026-11-01T10:10:03 |
| **早于等于 A0 收批（10:34:22）的文件** | 3353 |
| **晚于 A0 收批（10:34:22）的文件** | **恰好 211** |
| 211 个文件的 mtime 区间 | **10:43:33 – 10:43:47**（跨度 15 秒） |
| 10:34:24 – 10:43:31 之间的文件数 | **0**（零窗口） |
| 211 个文件的路径分布 | `freeze_cache/judgments/*` 与 `freeze_cache/responses/*`（样例：`JF-P001-0.json`、`sha256:d895893d….json`） |
| A0 `run.jsonl` mtime | 2026-11-01T10:34:22.021（早于全部 211 个文件） |
| A0 `run.jsonl` sha256 | `1bfeb51d…` = `meta.run_sha256`（逐字相等） |

**"零窗口"是本项最硬的证据**：A0 收批后 9 分钟内 A0 的 side_root **没有任何写入**，211 次写入全部集中在 10:43:33–10:43:47 这 15 秒内，与 A1 的 attempt1 起跑时刻（10:43:32）吻合。

判定：污染确实发生，但**发生在 A0 收批之后**，A0 的 `run.jsonl` 未受影响。→ **通过（附边界条件，见 §7）**

### 1.4 串行纪律（可复算事实，不是口号）

| 事件 | 时刻 |
|---|---|
| A0 起跑（host.log `started_at`） | 10:09:59 |
| A0 收批（`finished_at=…rc=0`，run.jsonl mtime） | 10:34:22 / 10:34:23 |
| A1 attempt1 起跑（误用 A0 side_root） | 10:43:32 |
| A1 attempt1 写出最后一笔（run.jsonl mtime） | 10:43:47 |
| A1 正式起跑（host.log `started_at`） | 10:44:02 / meta 10:44:03 |
| A1 收批（`finished_at=…rc=0`） | 11:06:42 / 11:06:43 |

- A0 区间 `[10:09:59, 10:34:23]` 与 A1 区间 `[10:44:02, 11:06:43]` **不相交**，间隔 **9 分 39 秒**；
- A1 attempt1 期间 A0 已收批 ⇒ 无两臂并发；
- 进一步旁证：**A1 自己的 side_root 最早文件 mtime = 10:44:06**（晚于 A1 正式起跑）⇒ A1 正式批次没有读到 attempt1 的残留；
- A1 另有一次 `preflight@10:09:56`（A0 起跑前 3 秒）记录为 PASS，但其 `host.log` 中**没有** `[d2] run:` 行、且 `A1 side_root` 在 10:44:06 前文件数为 0 ⇒ 那次**未起引擎**。

判定：串行成立。→ **通过**

---

## 2. 复核项②：口径审计（llm-cost 复算 + 真 provider 证明）→ **通过**

### 2.1 复算（自己算）

命令（§11.4）：`cd code && python3 -m obs llm-cost --log <臂>/run.jsonl`

| 指标 | A0 | A1 | 说明 |
|---|---|---|---|
| `total.calls` | **2255** | **2255** | 与 `meta.llm_calls` 一致 |
| `degraded` | 0 | 0 | 无降级兜底 |
| `cached` | 1387 | 1387 | 缓存命中数（`importa nce` 用途为主） |
| `tokens_in` | 163672 | 173233 | A1 多 9561 |
| `tokens_out` | 155617 | 147939 | A1 少 7678 |
| `tokens_total` | **319289** | **321172** | A1 多 1883 |
| `thinking` | 425 | 425 | judge 用途的思考调用 |
| `by_provider` | `{openai_compat: 2255}` | `{openai_compat: 2255}` | 唯一 provider，无 mock 混入 |
| 逐 purpose（dialogue） | calls 193 / tin 63305 / tout 9980 | calls 193 / tin 73040 / tout 10159 | 调用数相同，输入 token +9735（+15.4%） |
| 逐 purpose（importance） | 1523 / cached 1387 | 1523 / cached 1387 | 同 |
| 逐 purpose（judge） | 425 / tin 51730 / tout 101882 | 425 / tin 51730 / tout 95403 | 同 |
| 逐 purpose（negotiation / plan / reflect） | 7 / 16 / 91 | 7 / 16 / 91 | 同 |

### 2.2 与既有归档的一致性（不是"我说对就对"）

- A0：我复算的 `engine_log` 与 A0 目录既有 `llm_cost.txt` 的 `engine_log` **逐字段相等**（既有文件额外含 `provider_guard` 段，因其生成时带 `--require-provider`）。→ 一致
- A1：我按标准名归档生成的 `llm_cost.txt` 与门禁原始落点档 `/tmp/d2_llmcost_1251980.out` `cmp` ⇒ **BYTE_IDENTICAL**（见 `A1_ACCEPT.txt`）。→ 一致

### 2.3 真 provider 证明（非 mock / 非 degraded 兜底）

三重证据：
1. `provider_guard` 原文（归档于 `llm_cost.gate.out`）：`{"by_provider": {"openai_compat": 2255}, "expected": "openai_compat", "ok": true, "problems": []}`；
2. `run_batch.sh` 的真跑门禁 `python3 -m obs llm-cost --require-provider openai_compat` 在跑批当时 `rc=0`（两臂 `host.log` 均以 `[d2] OK` 结尾）；
3. `meta.fallback_detected=false`、`meta.degraded_calls=0`，且 `meta.endpoint_host=172.16.3.41:31809`（真实端点，非 localhost/mock）。

判定：真 provider 调用。→ **通过**

---

## 3. 复核项③：口径与陷阱 —— `mono_ts` 不是墙钟（请照抄避坑）

### 3.1 事实

`run.jsonl` 每行有 `mono_ts`，它**等于 `seq`（事件计数器）**，不是「批内相对秒」，也不是墙钟时间。

实测（d47 批 `v2/evidence/d47-ruler-f2-20261101_n16r24_s42/run.jsonl`）：
- 首条 `WORLD_INIT`：`seq=0, mono_ts=0`
- round 0 的 `TURN_SEAL`：`seq=425, mono_ts=425`，而该轮**行数恰为 426**
- 全批 `max(mono_ts)=33227`，而 `meta.events=33228`（= 行数）

⇒ 恒等式 `mono_ts == seq` 成立（本文件复核的两臂同样成立：A0 `max_seq=34095`、A1 `max_seq=34074`）。

### 3.2 错误推演会得出什么假结论（这是本节的重点）

如果把 `mono_ts` 当「批内秒数」、与 `meta.started_at` 相加推墙钟：

| 推演方式 | 会得到的假结论 | 真实值 | 偏差 |
|---|---|---|---|
| `started_at + max(mono_ts)` 作为收批时刻 | d47 批次跨 **33227 秒 ≈ 9.23 小时** | `duration_sec=1261`（20 分 41 秒） | 夸大 **26 倍** |
| 逐轮取「首末 mono_ts」当轮起止时刻 | round1 起点晚于 round2 终点，出现**轮次互相重叠**的假象 | 24 轮严格串行 | 结构性错误 |

我本人在写「每轮存活表」工具时第一版就踩过这个坑（用 `mono_ts` 推墙钟，得到轮次重叠的假时间表），已废弃该实现。

### 3.3 正确的做法

- **墙钟时间**只能来自「跑批进行中的真实采样」（例如 `tools/run/alive_sampler.py` 按固定间隔记录 `ts_iso + 当时行数`），其精度 = 采样间隔，必须在表头写明精度与该精度下不可判定的问题；
- **批次级墙钟**取 `meta.started_at / finished_at / duration_sec`，以及 `host.log` 的 `started_at=` / `finished_at=` 行；
- **`mono_ts` 只能当日志内单调序号用来排序/定位**（如 `tools/d21/a2_incidence.py`、`partner_choice_stats.py` 仅用于排序，结论不受影响）；一旦被用于「时间窗口 / 速率 / 间隔」，结论即为假。

判定：本项为**口径澄清**（非通过/不通过）；风险已定名，并已在仓库内标出同型用法（仅排序、结论不受影响）。

---

## 4. 复核项④：真实截图（两臂关键视图）→ **通过**

链路：与 d47 同一链路（`tools/metrics/render_shots.py` → `gen_threads.py` 派生 `threads.json` → 临时静态服务 → Chromium 现场截图）。**只读日志、零跑批、零 LLM、不写 `code/frontend`**。

| 臂 | 视图 | PNG 绝对路径 | 字节 | PNG sha256 |
|---|---|---|---|---|
| A0 | chat | `v2/evidence/c1_scene_shots/c1-a0-chat-1bfeb51d.png` | 279008 | `ad034cfa1542484723bfd5aed5e7b60a8fa545687a7303fbd8b6b9c2103d807f` |
| A0 | rhythm | `v2/evidence/c1_scene_shots/c1-a0-rhythm-1bfeb51d.png` | 279430 | `161b4c80e19a437971cdb84752a8eaed7dde2a97a1e622b29ac4151ab0cd373e` |
| A1 | chat | `v2/evidence/c1_scene_shots/c1-a1-chat-c828b407.png` | 285493 | `10ddaaef0784f2a39be85fc00e33c3527a6652ae854f64717147b1397ed4ae55` |
| A1 | rhythm | `v2/evidence/c1_scene_shots/c1-a1-rhythm-c828b407.png` | 279438 | `2b1fe43046088eeec41d82ea4a622f79278caeb1cd9eedd42f72f2336b932a46` |

生成命令（§11.5，两臂各一条；文件名中的 8 位十六进制 = 该臂 `run.jsonl` sha256 前 8 位，可溯源）：

```bash
/opt/openjiuwen/workswarm-venv/bin/python3 tools/metrics/render_shots.py \
  --run-dir v2/evidence/c1-scene-a0-20261101_n16r24_s42 --batch-id c1-a0 \
  --outdir v2/evidence/c1_scene_shots --views chat,rhythm --timeout 180
# A1 同型：--run-dir v2/evidence/c1-scene-a1-20261101_n16r24_s42 --batch-id c1-a1
```

- 两次运行均 `ok_count=2, fail_count=0`（`rc=0`），渲染报告：`v2/evidence/c1_scene_shots/render_report_c1-a0.json`（sha256 `5dbf1ad6f461672d57230b7090b4a2362d533d59678e49572c1ead39218d3356`）、`render_report_c1-a1.json`；
- 每张图带像素自检（`distinct_colors` 数万级、`top_color_frac` 远小于 0.99）⇒ 非空图/非单色图；
- **未拼图、未跨批混拼、未复用历史 PNG**（脚本策略：同名既有 PNG 先删、只认本次现截）。

判定：截图真实且可溯源。→ **通过**

---

## 5. 复核项⑤：A1 归档澄清（"补跑归档"= 只读重算归档，非 re-run）

- 事实：A1 目录初始缺 `llm_cost.txt` / `llm_cost.gate.out` / `A1_ACCEPT.txt`（A0 齐备）。
- 根因：`tools/d2/run_batch.sh:81` 把门禁输出写死 `/tmp/d2_llmcost_$$.out`，不落批次目录 ⇒ 属**落点问题**，门禁当时**确实跑过且 `rc=0`**（`host.log` 中 `[d2] OK` 与 `/tmp/d2_llmcost_1251980.out` 可交叉验证）。
- 处理（**零跑批、零 LLM 调用**）：
  1. `cp -p /tmp/d2_llmcost_1251980.out <A1>/llm_cost.gate.out`（保留原 mtime `2026-11-01 11:06:43`，作为门禁当时输出）；
  2. `python3 -m obs llm-cost --log <A1>/run.jsonl --require-provider openai_compat > <A1>/llm_cost.txt`（`rc=0`）；
  3. `cmp` 二者 ⇒ **BYTE_IDENTICAL**；
  4. 新写 `A1_ACCEPT.txt`（逐项值与 A0 同格式，含上述归档说明与边界条件）。
- 判定：归档为「已有输出的落位重算」，**未重新跑批**。→ **通过**

---

## 6. 复核项⑥：存活表工具登记（本轮未使用）

`tools/run/alive_sampler.py`（跑批进行中按间隔采样：时刻 / 耗时 / 字节 / 行数 / 末 seq / 末轮次 / 末事件 / 是否推进）与 `tools/run/round_alive_table.py`（逐轮存活表：行数 / 行号区间 / 首末 seq / TURN_SEAL 个数 / 判定）**已具备但本轮未使用**：

- 理由：本轮无新增跑批（策略变更），且两臂均已完成 24 轮、每轮 seal 齐备（§1.1），存活表无观测对象；
- 两脚本当前为**未跟踪新文件**（`git status`：`?? tools/run/`），本轮不提交，不进入交付链路；
- 两脚本均不含墙钟推算（§3 的坑已在脚本内以事实前提写明）。

判定：登记完成，无纪律影响。

---

## 7. 数据完整性边界条件（引用结论时必须带上）

1. **A0 的 `run.jsonl` 未受污染**：其 sha256 与 `meta.run_sha256` 逐字相等，mtime（10:34:22.021）早于全部 211 个污染文件（10:43:33 起）。
2. **受影响的只有 A0 的 side_root 缓存**：211 个文件全部位于 `/tmp/c1_scene_a0_n16r24_s42_side/freeze_cache/{judgments,responses}`。
3. **因此**：任何**读 A0 side_root 缓存**的二次分析（例如按缓存重放、按 purpose 反推 cached 率）必须按 `mtime <= 2026-11-01T10:34:22` 过滤，否则会把 A1 attempt1 的缓存混入 A0；**只用 `run.jsonl` 的读数（llm-cost、指标、截图）不受影响**，因为 `cached` 字段在事发前已写入日志。
4. **A1 正式批次未受 attempt1 残留影响**：A1 side_root 最早文件 mtime 10:44:06 > A1 起跑 10:44:02。
5. `participants_violations = 9` 两臂**同数**（对称），`participants_consistent=false` 两臂同型；两臂对话类事件数同为 191（`MSG_DM=161 + MSG_PUBLIC=30`）⇒ 该断言不影响两臂可比性，但属已知局限（见 §9）。

---

## 8. 复核项⑦：是否足以支撑「效果层读数」→ **不足以支撑"效果有改善"；判据读数只能判"不成立"**

### 8.1 判据原文（逐条照录，不做改写）

来源：`v2/refs/C1-scene-prereg-20261101.md`（判据先于数据冻结）
- 尺子：`tools/metrics/place_content_consistency.py`（确定性规则版，**不用 LLM judge**）
- 词表指纹：`lexicon_sha256 = 7e514eba9f9de0e674875f40b9503e24490f5baf9b861d51bc8cfe68b074f22e`
- 主指标：**处所-内容一致性率** = 判为「与说话人当前 `place` 相容」的可判定对话条数 ÷ 进入分母的可判定对话条数
- 分母口径：对话类事件（`MSG_PUBLIC`/`MSG_DM`）→ 需 `payload.place` 非空且 `payload.body` 非空 → 命中「活动线索词表」≥1 词才进分母（未命中记 `no_cue`，不进分母只报条数）
- 通过线（**两条同时满足**）：① `rate(A1) − rate(A0) ≥ +15.0pp`；② `rate(A1) ≥ 0.55`
- 不可判条件（命中任一即写「不可判」，不得写「不成立」）：① 任一臂 `denominator < 30`；② 两臂 env/配置差异不止 `LIFE_PROMPT_SCENE` 一行；③ 真跑验真失败；④ 两臂 `lexicon_sha256` 不一致；⑤ 两臂 `no_cue` 占比差 ≥ 10pp

### 8.2 我的独立复算（命令 §11.6）

| 指标 | A0 | A1 |
|---|---|---|
| `dialogue_events` | 191 | 191 |
| `missing_place_or_body` | 0 | 0 |
| `no_cue(unjudgeable)` | 17（8.9%） | 26（13.6%） |
| `denominator(judged)` | **174** | **165** |
| `agree` | 58 | 56 |
| `contradictory` | 116 | 109 |
| `consistency_rate` | **0.3333 (58/174)** | **0.3394 (56/165)** |
| `lexicon_sha256`（脚本自报） | `7e514eba…` | `7e514eba…` |
| `input_run_sha256`（脚本自报） | `1bfeb51d…` | `c828b407…` |

- **Δ = 0.3394 − 0.3333 = +0.0061 ⇒ +0.61pp**（要求 ≥ +15.0pp）→ 未达标
- **rate(A1) = 0.3394**（要求 ≥ 0.55）→ 未达标

### 8.3 不可判条件逐条核对（决定能否判"不成立"）

| 不可判条件 | 实测 | 是否触发 |
|---|---|---|
| ① 任一臂分母 < 30 | 174 / 165 | 否 |
| ② 两臂 env 差异不止 `LIFE_PROMPT_SCENE` | `diff env_manifest.txt` ⇒ 仅此行 | 否 |
| ③ 真跑验真失败 | `rc=0`、`provider_guard.ok=true` | 否 |
| ④ 两臂 `lexicon_sha256` 不一致 | 两臂同为 `7e514eba…` | 否 |
| ⑤ 两臂 `no_cue` 占比差 ≥ 10pp | 8.9% vs 13.6% ⇒ 4.7pp | 否 |

⇒ 五条均未触发 ⇒ 按预登记卡只能判 **「不成立」**，不得判「不可判」。

### 8.4 机制层（我自己验的辅助读数）

| 臂 | `dialogue` 事件数 | 含 `payload.ctx.scene` 键 | 非空 `scene` | 覆盖率 |
|---|---|---|---|---|
| A0 | 191 | 0 | 0 | **0.0000** |
| A1 | 191 | 191 | 191 | **1.0000** |

⇒ 机制层成立（0/191 → 191/191）。

### 8.5 成本侧证据（与机制层并列）

`dialogue` 用途：调用次数两臂同为 **193**，`tokens_in` 由 **63305 → 73040（+9735，+15.4%）**，`tokens_out` 由 9980 → 10159（+179）。调用次数不变而输入 token 显著上升，与「把场景文本注入对话 prompt」的机制预期一致 ⇒ **场景确实进了 prompt**。

### 8.6 判定

**效果层按预登记判据：不成立（不是不可判定）。** 三条并列才是诚实结论：
1. 机制成立（0/191 → 191/191）；
2. 成本可测（dialogue tokens_in +15.4%，调用数不变）；
3. **效果层按判据不成立（Δ=+0.61pp « +15pp；rate(A1)=0.3394 < 0.55）**。

### 8.7 对「是否足以支撑 R2 效果层读数」的回答

- 如果 R2 的读数与 §8.2 一致 ⇒ 我的复核**支持**该读数，并支持「不成立」的判定；
- 如果 R2 的读数与 §8.2 **不一致** ⇒ 以尺子原样复算为准，差异必须逐项定位（词表版本、分母口径、事件类型集合、`place` 来源），在此之前不得对外发布任何一方数字；
- 判据层面我未发现 life-impl 的口径有错；若发现，将单独报 team-leader，不在本文件擅改判据。

---

## 8bis. 判据效度的事后观察（**不构成推翻"不成立"的依据**）

（本节按 team-leader 2026-11-01 12:09 指令设立；**边界必须读**）

**(a) 事实**：两臂一致率绝对值仅 0.3333 / 0.3394，而通过线下限要求 0.55 —— 两臂都远低于及格线，说明该尺子在本次样本上整体偏低（存在 **floor 效应**，或「尺子测的对象」与「改动影响的对象」不完全重合）的疑点。

**(b) 可能的解释（全部为假设，未验证）**：
- 该尺子判定的是「文本里提到的手上活 ↔ 当前 `place` 是否相容」，衡量的是**地点—活动一致性**；而 `LIFE_PROMPT_SCENE` 注入 `place`+`activity` 后，更直接改变的是**对话内容的具体性/在场感**（例如提到具体物件、正在做的事的细节），二者不是同一对象；
- 词表覆盖有限：`no_cue` 两臂 8.9% / 13.6%，另有「一词多义」（山药/黄芪按 `clinic` 计）等偏保守设定，可能系统性压低 A1；
- 两臂 `place` 分布以 `residence`/`cafe`/`market`/`park` 为主，这些场所的「允许活动域」较宽或较窄都可能影响基线水位。

**(c) 边界（粗体，不可省）**：

> **以上全部是事后观察。它不构成推翻「不成立」判定的依据，只能作为下轮改进尺子的假设来源。**
> 事后讨论判据效度是负责；事后用判据效度去否定结论是作弊。二者界线即在此：**判据必须在读数据之前冻结（本卡已冻结），读完之后不得据数据下调门槛、放宽词表或改分母**。

---

## 8ter. 独立验证「锚点时序缺陷」：A1 有 87/191 的注入内容指错场所 → **成立（我自己算的）**

> 本节是对 life-impl 2026-11-01 12:11 交接中「87/191 指错场所」的**独立复核**。命令见 §11.9，全部只读、不引用任何成员数字。

### 8ter.1 计数（自己算）

命令逻辑：取 A1 `run.jsonl` 中 `type ∈ {MSG_PUBLIC, MSG_DM}` 的事件，逐条比较 `payload.place`（发言时所在场所）与 `payload.ctx.scene.place`（注入提示里的场所）。

| 指标 | 实测 |
|---|---|
| dialogue 事件数 | 191 |
| `ctx.scene` 键存在 | 191（覆盖 1.0000） |
| `ctx.scene` 为 dict 且含 `place` | 191 |
| **`ctx.scene.place != payload.place`** | **87** |
| 比例 | **87/191 = 0.4555（45.55%）** |
| 出现不一致的轮次 | 0, 3, 6, 7, 9, 12, 15, 18, 19, 21（共 10 轮） |
| 前 5 条不一致（seq, 实际场所, 注入场所） | (53, library, residence) (73, library, residence) (84, workshop, residence) (113, library, residence) (124, park, residence) |

⇒ **87/191 与 life-impl 自述一致（逐条相同）**。

### 8ter.2 成因验证（抽查 seq 70/71/73 + 全量解释力检验）

抽查（原文事件，A1 `run.jsonl`）：

```
seq=70  PLACE_MOVE    actor=P004                     （P004 出发）
seq=71  PLACE_ARRIVED actor=P004  place=library      （P004 到达图书馆）
seq=72  LLM_CALL      actor=SYSTEM
seq=73  MSG_DM        actor=P004  place=library      body=（把沾着面粉的手在围裙上蹭了蹭）…我正揉着一盆老面…
                      payload.ctx.scene.place=residence   ← 注入的是**出发前**的场所
```

⇒ 「移动后发言，但锚点取的是移动前的快照」在该例成立。

全量检验（两条独立判据，任一不成立即说明解释力不足）：

| 检验 | 判据 | 结果 |
|---|---|---|
| 检验 1 | 对每条错位发言，**同轮内、同 actor、在其发言之前存在 `PLACE_ARRIVED` 且目的地 = `payload.place`** | **87/87 = 1.0000**（未解释 0 条） |
| 检验 2 | `ctx.scene.place` **恰等于该 agent 移动到目的地之前所在场所**（首轮用 `AGENT_BORN.home_place` 作初始场所） | **87/87 = 1.0000**（反例 0 条） |

⇒ 「场景锚快照早于同轮移动，导致注入内容是上一站」这一解释，对 87 条错位**全覆盖**，无残余反例。

### 8ter.3 该缺陷对主指标的量化影响（本文件自己的分层计算）

把 A1 的可判定条目按「锚点是否错位」切成两层（同一把尺子、同一分母口径）：

| 子集 | agree | judged | rate |
|---|---|---|---|
| 锚点**错位**（注入的是上一站） | 19 | 75 | **0.2533** |
| 锚点**一致**（注入的就是当前场所） | 37 | 90 | **0.4111** |
| 合计 | 56 | 165 | 0.3394 |

- 错位层的一致率（0.2533）明显低于一致层（0.4111）⇒ 缺陷**确实在压低 A1 的读数**，且方向可解释（错位层里居民在图书馆说着"在家揉面"这类话，被判相悖）。
- **上界估计（重要，防止过高解读）**：即便假设 75 条错位全部按「一致层」的 0.4111 表现，A1 的一致率也只有 **0.4111**（37+75×0.4111≈68 / 165），仍 **< 0.55**，且相对 A0 的 0.3333 仅 **+7.8pp < +15pp**。
  ⇒ **该缺陷使"不成立"的结论更不牢靠，但按预登记判据，即使乐观修正也不会翻转为"成立"。** 这正是报告要写的分寸。

### 8ter.4 判定

缺陷**存在且可定位**（快照时序），影响面 **87/191 = 45.55%**，且对主指标有可量化压低作用。→ **验证成立（通过）**；但**不构成推翻 §8.6「按现有判据不成立」的依据**（见 §8ter.3 上界）。

---

## 8quater. 独立复核「尺子不敏感」的说法：**部分成立，但我给出的证据比"不敏感"更具体**

> 这一项属**测量问题**，与 §8ter 的**被测对象缺陷**性质不同，报告里不得混为一谈。

### 8quater.1 按场所分层的低水位（我自己算的，与 life-impl 自述一致）

A1 按 `place` 分层（`judged < 30` 不报率，只报条数）：

| place | judged | agree | 说明 |
|---|---|---|---|
| cafe | 26 | 2 | 咖啡馆里 26 条可判定，仅 2 条相符 |
| park | 17 | 1 | |
| plaza | 15 | 2 | |
| residence | 27 | 16 | 唯一高位场所（与"灶/炕/缝补"词条多有关） |
| market | 20 | 5 | |

A0 同型：cafe 27/1、park 21/5、plaza 14/1、residence 26/18、market 21/6。⇒ 两臂在 cafe/park/plaza 三个场所**系统性偏低**，说明低水位是**尺子性质**，不是某一臂的问题。

### 8quater.2 相悖条目的构成（比"不敏感"更硬的说法）

对 A1 的 109 条相悖条目，按「(所在场所 → 命中的活动域)」聚合，前 6 位：

| 场所 → 命中域 | 条数 |
|---|---|
| market → cooking_bakery | 5 |
| park → trade_accounting | 4 |
| market → wood_metal_craft | 4 |
| park → cooking_bakery | 4 |
| cafe → trade_accounting | 4 |
| market → farm | 3 |

- 这说明判"相悖"的主力是**闲聊里提到别处的事**（在集市说灶上、在公园说账本），而尺子的 `classify()` 是**纯子串匹配**：把「提到」当成「在做」。`trade_accounting` 的允许场所含 `market/bank/office`，而其线索词含「买 / 卖 / 账 / 柜台 / 摊上 / 秤」等高频道具/闲谈词 ⇒ 在 cafe 说"账"即被判相悖。
- 判定：**"尺子对'提到'与'在做'不加区分"是成立的**（这是比"不敏感"更准确的描述）；但"不敏感"不等于"反向"，也无法据此说 A1 一定更好（缺 judge 对照，见 §10 局限）。

### 8quater.3 边界

上述是**对测量工具性质的观察**，不构成对 §8.6 判定的推翻：改判据必须重登记预登记卡（新卡、新数据），不得在读完数据后调整。

---

## 9. 已发现的仓库证据链缺陷（登记，本轮**不修**）

> 本轮 diff 要保持干净可审计；修工具链属独立任务（team-leader 已单独安排，本文件只登记）。

### 缺陷 A：`meta.side_root` 结构性失真

- **现象**：两臂 `meta.side_root` 均为 `null`，但两臂实际都传了 `--side-root`。
- **证据**：A0 `host.log`：`[d2] run: python3 -m orchestration run … --side-root /tmp/c1_scene_a0_n16r24_s42_side`；A1 同型（`…a1_side`）。
- **根因（文件 + 行号）**：`tools/d2/run_batch.sh:54` 把 `--side-root` 传给引擎（`ARGS`）；`:62` 构造喂给 `tools/d2/emit_run_meta.py` 的 `META_ARGS` **不含** `--side-root`；`emit_run_meta.py:291` 该参数 `default=None` ⇒ 恒为 `null`。
- **影响面**：任何依赖 `meta.side_root` 判断 side-root 隔离性的分析都会**系统性误判**（本轮就差点据此判 A0 被污染）。
- **修复建议**：`META_ARGS` 补 `--side-root`；`emit_run_meta.py` 在缺参时从 `host.log` 的 `[d2] run:` 回溯并在 meta 记 `side_root_source ∈ {cli, host.log, missing}`，两者皆缺则**非零退出**（保留 `--allow-missing-side-root` 逃生口供历史批次重算）。
- **本轮不修的理由**：属工具链改动，与「既有数据复核」交付物无关；且需评估向后兼容（历史批次 meta 重算）。

### 缺陷 B：`launch_evidence` 的 side_root 声明与实际命令不一致

- **现象**：A1 的 attempt1 目录（`attempt1_wrong_side_root/`）里，`launch_evidence.txt` 自述 `side_root: /tmp/c1_scene_a1_n16r24_s42_side`，但同目录 `host.log` 的真实命令是 `--side-root /tmp/c1_scene_a0_n16r24_s42_side`（误用 A0 的）。
- **影响面**：`launch_evidence` **不能单独作为隔离性证据**采信，必须交叉 `host.log` 命令行。
- **修复建议**：`launch_evidence` 的 side_root 取自**实际生效命令行**而非声明变量；不一致直接 fail；并加一个只读检查器对历史批次做回归（预期：A0/A1 = OK、attempt1 = MISMATCH —— 若检查器抓不出已知坏例，则它是空检查器）。
- **本轮不修的理由**：同上（工具链改动 + 需回归自检，另开任务）。

### 缺陷 C：llm-cost 门禁输出不落批次目录

- **现象**：批次目录初始没有 `llm_cost.txt`，被误读为「验真缺失」。
- **根因**：`tools/d2/run_batch.sh:81` 把门禁输出写死到 `/tmp/d2_llmcost_$$.out`，`tail -3` 后不落批次目录。
- **影响面**：造成「证据缺口」的**误判**——性质是落点问题，不是门禁没跑。A0 与 A1 均受影响（A0 已在自己的 `A0_ACCEPT.txt` 记录，A1 由本文件 §5 归档补齐）。
- **修复建议**：门禁输出同时落批次目录（`llm_cost.txt` / `llm_cost.gate.out`），移除 `/tmp` 写死路径；并给出历史批次回填/不回填的兼容策略。
- **本轮不修的理由**：同上。

---

## 10. 局限与未覆盖项

1. **尺子强度**：主指标为**规则版、未用 LLM judge**，结论强度弱于人工标注（预登记卡 §7 已声明）。
2. **`participants_violations=9`**：两臂同数、对话事件数同为 191 ⇒ 不影响两臂可比性与主指标，但属已知数据质量问题，未深挖成因。
3. **未做**：两臂 `MSG_PUBLIC` 逐条人工抽检（仅导出样例供报告引用，未做人工判分）；`no_cue` 条目的语义复核；缓存层（`freeze_cache`）对两臂的差异分析（因 §7 的污染边界，直接比较会失真）。
4. **未覆盖**：本轮不评估「生活气息」主观感受；不评估其他维度（D9t/公开面接话等）的交互影响。
5. 本文件**不含任何因果推断**：单变量归结依赖 §8.3 的条件②（两臂 env 差异仅 `LIFE_PROMPT_SCENE` 一行），符合预登记卡 §8.4。

---

## 11. 复算命令清单（第三方可照抄）

> 全部在仓库根 `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment` 下执行；只读。

### 11.1 日志指纹
```bash
sha256sum v2/evidence/c1-scene-a0-20261101_n16r24_s42/run.jsonl \
          v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl
python3 -c "import json;[print(p, json.load(open(p))['run_sha256']) for p in ['v2/evidence/c1-scene-a0-20261101_n16r24_s42/meta.json','v2/evidence/c1-scene-a1-20261101_n16r24_s42/meta.json']]"
```

### 11.2 完整性（行数 / seq 连续 / 每轮 TURN_SEAL）
```bash
python3 - <<'PY'
import json,collections
for a in ['c1-scene-a0-20261101_n16r24_s42','c1-scene-a1-20261101_n16r24_s42']:
    p=f'v2/evidence/{a}/run.jsonl'; n=bad=0; seqs=[]; seal=collections.Counter(); last={}
    for line in open(p,encoding='utf-8'):
        if not line.strip(): continue
        n+=1
        try: o=json.loads(line)
        except Exception: bad+=1; continue
        seqs.append(o['seq'])
        if o['type']=='TURN_SEAL': seal[o['round']]+=1
        last[o['round']]=o['type']
    cont=all(seqs[i]==seqs[i-1]+1 for i in range(1,len(seqs)))
    badr=[r for r in seal if seal[r]!=1 or last[r]!='TURN_SEAL']
    print(a,'lines',n,'bad',bad,'max_seq',max(seqs),'seq连续',cont,'轮数',len(seal),'违规轮次',badr)
PY
```

### 11.3 A0 side_root 污染时间边界
```bash
python3 - <<'PY'
import os,datetime,bisect
S='/tmp/c1_scene_a0_n16r24_s42_side'; ms=[]
for r,d,fs in os.walk(S):
    for f in fs: ms.append(os.stat(os.path.join(r,f)).st_mtime)
ms.sort(); f=lambda t: datetime.datetime.fromtimestamp(t).astimezone().isoformat(timespec='seconds')
fmt='%Y-%m-%dT%H:%M:%S'
hi=datetime.datetime.strptime('2026-11-01T10:34:22',fmt).astimezone().timestamp()
print('总文件',len(ms),'早于/等于收批',bisect.bisect_right(ms,hi),'晚于收批',len(ms)-bisect.bisect_right(ms,hi))
late=[m for m in ms if m>hi]; print('晚于收批的最早/最晚',f(late[0]),f(late[-1]))
lo=datetime.datetime.strptime('2026-11-01T10:34:24',fmt).astimezone().timestamp()
hi2=datetime.datetime.strptime('2026-11-01T10:43:31',fmt).astimezone().timestamp()
print('零窗口 10:34:24–10:43:31 文件数',bisect.bisect_right(ms,hi2)-bisect.bisect_left(ms,lo))
PY
```

### 11.4 口径审计（两臂 llm-cost）
```bash
cd code
python3 -m obs llm-cost --log ../v2/evidence/c1-scene-a0-20261101_n16r24_s42/run.jsonl
python3 -m obs llm-cost --log ../v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl
python3 -m obs llm-cost --log ../v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl --require-provider openai_compat > /tmp/a1_gate_recheck.txt
cmp /tmp/a1_gate_recheck.txt ../v2/evidence/c1-scene-a1-20261101_n16r24_s42/llm_cost.txt && echo BYTE_IDENTICAL
```

### 11.5 真实截图
```bash
/opt/openjiuwen/workswarm-venv/bin/python3 tools/metrics/render_shots.py \
  --run-dir v2/evidence/c1-scene-a0-20261101_n16r24_s42 --batch-id c1-a0 \
  --outdir v2/evidence/c1_scene_shots --views chat,rhythm --timeout 180
/opt/openjiuwen/workswarm-venv/bin/python3 tools/metrics/render_shots.py \
  --run-dir v2/evidence/c1-scene-a1-20261101_n16r24_s42 --batch-id c1-a1 \
  --outdir v2/evidence/c1_scene_shots --views chat,rhythm --timeout 180
```

### 11.6 效果层尺子 + 幂等自检 + 机制层
```bash
python3 tools/metrics/place_content_consistency.py --run v2/evidence/c1-scene-a0-20261101_n16r24_s42/run.jsonl
python3 tools/metrics/place_content_consistency.py --run v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl
# 幂等：同输入两次运行必须逐字节一致
python3 tools/metrics/place_content_consistency.py --run v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl > /tmp/b1.txt
python3 tools/metrics/place_content_consistency.py --run v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl > /tmp/b2.txt
cmp /tmp/b1.txt /tmp/b2.txt && echo BYTE_IDENTICAL
# 机制层：ctx.scene 覆盖率
python3 - v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl <<'PY'
import json,sys
n=hit=0
for l in open(sys.argv[1],encoding='utf-8'):
    e=json.loads(l)
    if e.get('type') in ('MSG_PUBLIC','MSG_DM'):
        n+=1; hit+= 'scene' in ((e.get('payload') or {}).get('ctx') or {})
print(f'dialogue={n} scene_key={hit} coverage={hit/n:.4f}')
PY
```

### 11.7 两臂可比性（单变量核对）
```bash
diff v2/evidence/c1-scene-a0-20261101_n16r24_s42/env_manifest.txt \
     v2/evidence/c1-scene-a1-20261101_n16r24_s42/env_manifest.txt
# 预期：仅 LIFE_PROMPT_SCENE 一行差异（外加首行臂名注释）
```

### 11.9 锚点时序缺陷（87/191）与分层影响——本节全部数字的生成命令

```bash
# (1) 计数：ctx.scene.place != payload.place
python3 - <<'PY'
import json
p='v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl'
ev=[json.loads(l) for l in open(p,encoding='utf-8') if l.strip()]
dial=[e for e in ev if e.get('type') in ('MSG_PUBLIC','MSG_DM')]
mism=[]
for e in dial:
    pl=e.get('payload') or {}; ctx=pl.get('ctx') or {}
    sp=ctx.get('scene') if isinstance(ctx.get('scene'),dict) else {}
    if pl.get('place')!=sp.get('place'): mism.append(e)
print('dialogue',len(dial),'mismatch',len(mism),'ratio',round(len(mism)/len(dial),4))
PY

# (2) 成因全量检验：错位条目是否都能被「同轮内先到达目的地」解释 + scene 是否等于移动前场所
python3 - <<'PY'
import json
p='v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl'
ev=[json.loads(l) for l in open(p,encoding='utf-8') if l.strip()]
home={e['payload'].get('agent_id'):e['payload'].get('home_place') for e in ev if e.get('type')=='AGENT_BORN'}
arr={}
for e in ev:
    if e.get('type')=='PLACE_ARRIVED': arr.setdefault(e.get('actor'),[]).append((e['seq'],(e.get('payload') or {}).get('place')))
for k in arr: arr[k].sort()
mism=[]
for e in ev:
    if e.get('type') not in ('MSG_PUBLIC','MSG_DM'): continue
    pl=e.get('payload') or {}; sp=(pl.get('ctx') or {}).get('scene') or {}
    if pl.get('place')!=sp.get('place'): mism.append(e)
e1=e2=0
for e in mism:
    a=e['actor']; s=e['seq']; dst=e['payload'].get('place'); sp=e['payload']['ctx']['scene'].get('place')
    prev=[t for t in arr.get(a,[]) if t[0]<s]; ids=[i for i,t in enumerate(prev) if t[1]==dst]
    if ids:
        e1+=1
        i=ids[-1]; pre=prev[i-1][1] if i>0 else home.get(a)
        if pre==sp: e2+=1
print(f'检验1 同轮先到达: {e1}/{len(mism)}   检验2 scene==移动前场所: {e2}/{len(mism)}')
PY

# (3) 分层影响：错位子集 vs 一致子集的一致率，及乐观上界
python3 - <<'PY'
import json,importlib.util
spec=importlib.util.spec_from_file_location('pcc','tools/metrics/place_content_consistency.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
p='v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl'
ev=[json.loads(l) for l in open(p,encoding='utf-8') if l.strip()]
s={'mism':[0,0],'match':[0,0]}
for e in ev:
    if e.get('type') not in ('MSG_PUBLIC','MSG_DM'): continue
    pl=e.get('payload') or {}; sp=(pl.get('ctx') or {}).get('scene') or {}
    place=pl.get('place'); body=pl.get('body') or ''
    if not place or not body: continue
    doms=[d for d,v in m.DOMAINS.items() if any(c in body for c in v['cues'])]
    if not doms: continue
    ok=any(place in m.DOMAINS[d]['places'] for d in doms)
    k='mism' if place!=sp.get('place') else 'match'
    s[k][0]+=ok; s[k][1]+=1
for k,(a,n) in s.items(): print(k,'agree',a,'judged',n,'rate',round(a/n,4))
rate=s['match'][0]/s['match'][1]; n=s['mism'][1]
print('乐观上界 A1 rate =',round((s['match'][0]+n*rate)/(sum(v[1] for v in s.values())),4))
PY
```

### 11.8 幂等自检实测结果（本次）
`cmp` 输出 `BYTE_IDENTICAL`（A1 与 A0 均通过；该性质说明尺子是确定性函数，同一 `run.jsonl` 任意次运行结果逐字节相同）⇒ **可复算性成立**。

---

## 12. 结论三档汇总（本文件全部判定的落点）

### 已验证（可复算）
1. 两臂数据完整自洽：行数 = `meta.events`（34096 / 34075）、坏行 0、`seq` 连续、24 轮每轮 1 个轮末 `TURN_SEAL`、`rc=0`；
2. 两臂同 `code_sha`（`8b64615b…`，跑前=跑后）；
3. 两臂严格串行（A0 收批 10:34:23 → A1 起跑 10:44:02，间隔 9 分 39 秒；无并发）；
4. 真 provider 真跑：`openai_compat` 2255 calls/臂、`degraded=0`、`provider_guard.ok=true`、`fallback_detected=false`；
5. 机制层成立：`ctx.scene` 覆盖 0/191 → 191/191；
6. 成本可测：`dialogue` 调用数 193↔193，`tokens_in` 63305 → 73040（+15.4%）；
7. 效果层按预登记判据**不成立**：Δ=+0.61pp（阈值 ≥+15pp）、rate(A1)=0.3394（阈值 ≥0.55），且五条不可判条件均未触发；
8. A0 `run.jsonl` 未受 211 文件污染影响（sha256 与 meta 一致、mtime 早于污染窗口）；
9. 尺子确定性：同输入两次运行 `BYTE_IDENTICAL`。

### 证据不足（不足以支撑更强断言）
1. `no_cue` 条目（17 / 26 条）的语义内容未逐条复核 ⇒ 无法判断其是否系统性偏向某一臂；
2. `participants_violations=9` 的成因未查 ⇒ 只能说"两臂对称、不影响主指标"，不能说"数据无瑕"；
3. 未做人工/LLM judge 对照 ⇒ 无法评估规则尺子的假阴/假阳率（§8bis 的 floor 疑点仍是假设）。

### 不可判定（不得写成"不成立"或"成立"）
1. 「生活气息是否整体改善」——本维度只读「处所-内容一致性」一个代理指标，且该指标本次未达标；更广的"生活气息"不在本文件可判范围；
2. 若后续有人改动词表/分母/事件类型集合再计算 ⇒ 结果与本文件不可比，须视为新的独立测量。

---

**文件归属**：本文件为 `#R3-run` 的证据文件，提交与对外发布由 `#R4-report` 统一处理；本文件不绑定 commit sha（证据的代码锚为两臂 `code_sha = 8b64615b0c717a5a42db8d40ae9fff5b469cfe7d`）。
