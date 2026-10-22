# CYCLE-04 截图证据（本期新渲染，来自 `run_a5_real_n16r42_seed42`）

> 生成者：`report-writer`（撰写 `reports/CYCLE-04-20261022.md` 时现场渲染）｜生成时刻：**2026-10-22T20:37:27–20:37:36 +0800**（`render_wrap.log` 的 `RENDER_START` / `RENDER_END`，由本目录的 wrapper 写入）

## 1. 三重标注（缺一条即为引用错误）

1. **图源批次**：`v2/evidence/run_a5_real_n16r42_seed42/run.jsonl`
   - sha256 = `aa6edc351cefdd9983ba8a58a4e673aaf7890cc742a5761f3dd5d2c1cd569e24`（30,303,995 B，62,027 事件）
   - 该 sha 由 `threads.json.source.run_sha256` 派生并被 `dialogue_shots.sh` 自校验；文件名中的 `aa6edc35` 即该 sha 前 8 位。
2. **渲染时刻可复算**：本目录 `render_wrap.log` 显式记录 `RENDER_START` / `RENDER_END`（**wrapper 写入，不是 `shot.py` 自己打的**——`shot.py` 的 `SHOT OK:` 行不含时间戳，属已知缺口 G-2）。
3. **非 R18 修后行为**：R18 修复（`c01f6dd`）后**未起新跑批**，本批仍是修前批次；本目录图片只用于展示「世界长什么样 / 对话长什么样」，**不是**效果证据。

## 2. 文件

| 文件 | 视图 | 尺寸 | 字节 | sha256 |
|---|---|---|---|---|
| `cycle04_a5-chat-aa6edc35.png` | 对话流（全量口径） | 1400×900 | 267,686 | `fc98ccdf26b2cc7b8e04cad768c1f66e990b3bdbf09e3e1d115abf5ec68f315f` |
| `cycle04_a5-rhythm-aa6edc35.png` | 节律·串门 | 1300×1050 | 279,478 | `2c3cea9542dbd04471122c96ffe7530f1f0aa79c3a75e4163ec79d5cd94da9c5` |
| `cycle04_a5-spread-aa6edc35.png` | 闲话怎么传开 | 1300×900 | 175,398 | `973613da6acbc997b916f944af2e4759fa45f5754ae613b6137b9dd90bd607e8` |
| `cycle04_a5-600-aa6edc35.png` | 600px 判读 | 600×900 | 186,593 | `83d5306af144af58364cd73f9bd2a528cf90c917b969f4f456e8a6cdb2a2c419` |
| `render_wrap.log` | 渲染原始输出（4 次 `SHOT OK` + wrapper 时间戳） | — | 3,533 | `（不入表，随目录提交）` |
| 派生数据 `code/frontend/sample/dialogue_cycle04_a5/threads.json` | 页面数据（未跟踪） | — | 1,965,662 | `2d46ade71c63e68aa662dfd903eeecda9d56f597605f4ea189b7d45caf7cde39` |

`threads.json` 自证字段（实测）：`source.run_sha256 = aa6edc35…9e24`、`run_bytes = 30303995`、`events_total_in_log = 62027`、`round_range = [0,41]`、`llm_provider_in_log = openai_compat`；
`stats = {messages: 523, threads: 140, multi_turn_threads: 85, threads_ge3_turns: 79, max_turns: 6, participants: 16}`。

## 3. 复现命令（只读、幂等；与本次渲染逐字相同）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code
# ① 从真源日志派生页面数据（不写世界、不调 LLM）
python3 frontend/tools/gen_threads.py \
  --log ../v2/evidence/run_a5_real_n16r42_seed42/run.jsonl \
  --out frontend/sample/dialogue_cycle04_a5/threads.json --label cycle04_a5
# ② 起静态服务（本次用 8957，避开常驻的 8848）
nohup python3 frontend/tools/serve.py --port 8957 --host 127.0.0.1 > /tmp/c04_serve.log 2>&1 &
# ③ 出四视图真截图（batch / sha8 省略时由脚本从 threads.json 自动派生并自校验）
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8957 \
     sample/dialogue_cycle04_a5/threads.json "" "" ../v2/evidence/cycle04_shots
# ④ 收工
pkill -f 'serve.py --port 8957'
```

渲染读数（`render_wrap.log` 原文摘要）：

```
SHOT OK: …cycle04_a5-chat-aa6edc35.png    elapsed=2.83s mean_brightness=33.9 max_color_frac=30.98% blank_retries=0/2
SHOT OK: …cycle04_a5-rhythm-aa6edc35.png  elapsed=1.79s mean_brightness=31.3 max_color_frac=35.40% blank_retries=0/2
SHOT OK: …cycle04_a5-spread-aa6edc35.png  elapsed=1.73s mean_brightness=23.1 max_color_frac=71.18% blank_retries=0/2
SHOT OK: …cycle04_a5-600-aa6edc35.png     elapsed=2.48s mean_brightness=39.6 max_color_frac=28.69% blank_retries=0/2
OK: ../v2/evidence/cycle04_shots/cycle04_a5-{chat,rhythm,spread,600}-aa6edc35.png
```

## 4. 已知限制

- `shot.py` 的 `SHOT OK:` 行**不含时间戳**（本期已记入 `reports/CYCLE-04-20261022.md` ③ 的证据缺口 G-2，并列为下期 P1 修复项）；本目录的时间戳来自 wrapper。
- 4 张图为同一份 `threads.json` 的四种视图，**不是**四个不同批次。
- 页面上的 `meta 已对齐` 字样（见 `code/frontend/src/dialogue.js:512`）指页面派生数据已对齐，**不**代表该批次有 `meta.json`——`run_a5_real_n16r42_seed42/` 目录实测无 `meta.json`，d5 准入仍为 `REJECTED`（见报告 ③ F-1）。同页 `seed` 字段显示为 `—`，正是同一原因（`dialogue.js:498`）。
