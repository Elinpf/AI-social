# A1 跑批完成汇报（batch-runner → leader）

## 1) run 目录 / 规模 / 耗时

- run 目录：`v2/evidence/run_a1_wording_n4r60_seed42/`（`meta.json` / `host.log` / `llmcost.json` 已落；`run.jsonl` 被 `.gitignore:8` 排除，**未入库**）
- 规模：4 agents × 60 rounds，seed 42
- 耗时：`meta.duration_sec=482`；`host.log` 内核自报 `seconds=481.2985`
- events 9,940；MSG 124（DM 111 / PUBLIC 13）
- `code_sha = code_sha_end = a63737197ee8d63506ccdb81c8e45d8b349e1d3b`（与 leader 放行值一致，**无漂移**）
- `started_at 2026-10-21T04:33:56+08:00` → `finished_at 2026-10-21T04:41:58+08:00`
- `git_dirty_code_files=[]`；`assertions.msg_uid_unique=true`、`ptr_dangling=0`、`ptr_cross_thread=0`、`turn_index_dense=true`

## 2) llm-cost 验真（以 rc 为判决）

```
cd code && python3 -m obs llm-cost --log ../v2/evidence/run_a1_wording_n4r60_seed42/run.jsonl --require-provider openai_compat
```

- **rc = 0 → PASS**
- calls **272** ／ cached **45**（ratio 0.1654）／ **degraded 0** ／ `provider_guard.ok = true`
- `by_provider = {openai_compat: 272}`，`problems = []`
- `fallback_detected = false`
- tokens_in 40,695 ／ tokens_out 31,858 ／ tokens_total 72,553
- 原文（stdout 全文 + `rc` 行 + 判决行）落 `v2/evidence/a1_llmcost_ae969198.txt`；run 目录内另有 `llmcost.json`

## 3) L 系列读数

文件：`v2/evidence/d5_metrics_a1.md` / `v2/evidence/d5_metrics_a1.json`
命令（与 A0 逐字同口径）：

```bash
python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_a1_wording_n4r60_seed42/run.jsonl \
  --meta v2/evidence/run_a1_wording_n4r60_seed42/meta.json \
  --out-json v2/evidence/d5_metrics_a1.json --out-md v2/evidence/d5_metrics_a1.md
```

| 指标 | A1（分母 124） | A0 参照（分母 686） |
|---|---|---|
| L-2 括号旁白率 | **0.000000**（0/124） | 0.819242 |
| L-3 括号块出现率 | **0.000000**（0/124） | 0.860058 |
| L-6 精确重复率 | **0.129032**（16/124） | 0.099125 |
| L-7 8-gram 重复率 | **0.411290** | 0.488338 |

**L-2/L-3 的 0 值经独立复核，不是度量 bug**：另写脚本直接扫 124 条 body，全角 `（` 与半角 `(` 出现总数均为 **0**，含括号块条数 0 ⇒ 本批正文确实零括号旁白。

**边界（必须钉住）**：d5 准入 **REJECTED**，触发项 `B-15_msg_volume`（要求 `MSG>=150`，本批 124）⇒ 本批只能作**方向性筛查**，**不可与 A0 16×84 直接比**；上表 A0 列仅作量级参照，不构成同口径对照。

## 4) 四视图（真拍）

目录：`v2/evidence/a1_shots/`；全部 `rc=0`、`blank_retries=0/2`、Pillow 全解码通过、PNG 魔数 True。

| 视图 | 尺寸 | sha8 |
|---|---|---|
| chat | 1400×900 | `0e05129b` |
| rhythm | 1300×1050 | `7c3d7eea` |
| spread | 1300×900 | `c3fc91ec` |
| 600 | 600×900 | `13ce8b19` |

命名 `<batch>-<视图>-ae969198.png`（sha8 = 日志 sha256 前缀 `ae969198`）。
四件套与「生产命令 vs 复现命令」两行模板已写入 `v2/evidence/a1_shots/README.md`：
- 源 run 目录 `v2/evidence/run_a1_wording_n4r60_seed42/`
- 渲染命令（`dialogue_shots.sh` 生产形态 + `shot.py --url` 复现形态，参数一致，均含 `--no-blank-check`）
- 日志 sha256 `ae969198feaefd1f69147001e027394d55527bd1a0e460ff654697bdc3b1559b`（4,749,329 B，`wc -l`=9,940）
- 派生 threads.json sha256 `e3cefe6bf504fd6f8249980436d7d8e38f81a95ed5d4b11319d476b49fa44d27`（`gen_threads --require-complete`，TURN_SEAL 60 覆盖 round 0..59）

## 5) 异常（如实，不粉饰）

1. 首次 `bash` 调用 **300 s 工具层超时**（setsid 子进程 stdout 管道被捕获端等待 EOF），**非跑批失败**；未因超时重发起跑命令，全程仅 1 个跑批进程（`pid=4174591`）。已原样写入 `v2/evidence/a1_launch_evidence.txt` §10 / §11。
2. d5 准入 REJECTED（`B-15_msg_volume` 124 < 150）：非错误，但限制结论强度为「方向性筛查」。
3. 其余：0 降级、0 fallback、0 空白重试、0 中断。

## 6) 起跑/结束证据

`v2/evidence/a1_launch_evidence.txt`（sha256 `8379d044…`）含：pgrep 前置空输出 rc=1、分支 `feat/wording-a1` 与 HEAD `a637371`、工作树干净、`setsid --fork` 起跑、**SID 校验 PASS**（`child_sid=4174579 != caller_sid=4173864`）、唯一性复核（跑批进程数=1）。

## 7) git 未触碰

`git status --porcelain` 中**无任何已跟踪文件改动**，仅未跟踪产物：
`v2/evidence/run_a1_wording_n4r60_seed42/`、`v2/evidence/a1_shots/`、`v2/evidence/d5_metrics_a1.{json,md}`、`v2/evidence/a1_llmcost_ae969198.txt`、`v2/evidence/a1_launch_evidence.txt`、`code/frontend/sample/dialogue_a1_wording_n4r60_seed42/threads.json`（渲染用派生数据集）。
临时 `serve.py --port 8901` 已停服（`ss` 无监听、curl rc=7）。
