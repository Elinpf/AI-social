# narr-off-20261030 臂 · 执行说明与 harness 修正留痕

## 1. 批次事实

| 项 | 值 |
|---|---|
| arm | OFF（`LIFE_PROMPT_NARRATION` **显式 unset** ⇒ 代码走默认分支 = 改动前字面量） |
| code_sha | `47a7da9e71e4ab31e8b58a9a5cc14105ecd0aed8`（meta.code_sha == meta.code_sha_end） |
| 规模 | seed=42 / agents=16 / rounds=24 / max_turns=6 / flush-every=2（n16×r24） |
| started_at | 2026-10-30T02:11:33+08:00 |
| finished_at | 2026-10-30T02:32:54+08:00 |
| duration_sec | 1281（meta）/ 1283（wall） |
| run_batch rc | 0 |
| provider / model | `openai_compat` / `DeepSeek-Flash` |
| degraded_calls | 0（meta.fallback_detected=false） |
| events | 33839（= run.jsonl 行数） |
| MSG 分母 | 191（MSG_DM 167 + MSG_PUBLIC 24；rounds 0..23 全覆盖） |

## 2. harness 瑕疵（必须披露，不得掩盖）

### 2.1 两层验真是两件事

- **内层（跑批门禁）**：`tools/d2/run_batch.sh` 在真跑模式下**自己**执行
  `python3 -m obs llm-cost --log <run.jsonl> --require-provider openai_compat`，失败即以 **exit 6**
  中止整批。本臂 `run_batch.rc = 0`（不是 6）⇒ **内层门禁本来就通过**，这是「该批确实由
  openai_compat 服务」的反证。
- **外层（我的封装的跑后落盘）**：`tools/d9i/launch_narration_arm.sh` 在批次结束后**再独立跑一次**
  obs llm-cost，把结果落成 `llm_cost.json / llm_cost.txt / llm_cost.rc`，供报告直接引用。

### 2.2 外层第一版失败（真实报错原文）

第一版封装调用行**漏了 `PYTHONPATH=code`**，obs 模块不可导入：

```
$ cd <repo> && python3 -m obs llm-cost --log v2/evidence/narr-off-20261030/run.jsonl \
      --require-provider openai_compat --out v2/evidence/narr-off-20261030/llm_cost.json
/opt/openjiuwen/workswarm-venv/bin/python3: No module named obs
rc=1
```

`llm_cost.rc` 当时写入 `1`；驱动脚本 `tools/d9i/run_two_arms.sh` 按纪律（"llm_cost.rc≠0 该臂无效"）
**ABORT，没有起 ON 臂**：`ABORT: arm off llm-cost rc=1（该臂无效，不得用别的证据替代）`。

### 2.3 处置（不重跑批次、数据未动）

修 `tools/d9i/launch_narration_arm.sh` 的 obs 调用行，修后原文：

```
PYTHONPATH="$ROOT/code${PYTHONPATH:+:$PYTHONPATH}" python3 -m obs llm-cost \
    --log "$OUT_ABS/run.jsonl" --require-provider openai_compat --out "$LC_JSON" > "$LC_TXT" 2>&1
```

对**同一条 `run.jsonl`**（跑批产物，未重新生成）重跑该验真命令：

```
$ cd <repo> && PYTHONPATH=code python3 -m obs llm-cost \
      --log v2/evidence/narr-off-20261030/run.jsonl \
      --require-provider openai_compat \
      --out v2/evidence/narr-off-20261030/llm_cost.json
written: v2/evidence/narr-off-20261030/llm_cost.json
rc=0
```

- `llm_cost.json` 关键行：`engine_log.by_provider.openai_compat = 2252` 次调用；
- `llm_cost.rc` 已是修正后的 `0`；
- 两次 rc 一览：内层 run_batch 门禁 **rc=0**（原本）/ 外层第一版 **rc=1**（PYTHONPATH 缺失）/ 外层修正后 **rc=0**。

### 2.4 为什么这不破坏证据链

外层 obs llm-cost 只是**跑后观测**（只读已落盘的 run.jsonl），**不进入生成路径**，因此既不改变单变量性
（两臂只有 `LIFE_PROMPT_NARRATION` 不同），也不影响确定性/replay。本文件如实保留两次 rc 与修前/修后
命令原文，任何第三方都可用同一命令复算出同一结论。

## 3. 读数（两条口径，见 tools/d9i/narration_stats.py）

见同目录 `narration_stats.json`：
- 成对口径（主判）：`（[^（）]{1,120}）|\([^()]{1,120}\)` ⇒ 0/191 = 0.00%
- 任意括号口径（辅助）：`[（(]` ⇒ 0/191 = 0.00%
- dialogue_metrics `L-3_paren_block_any`（同正则）结果同样 0/191

分母口径提示：预登记 H0 的 686 是 r84、本轮 r24 得 191，**分母不同，只作同向比对，不构成效果比较**。
