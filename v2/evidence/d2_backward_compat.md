# D2 · 向后兼容验证（旧格式日志在改造后全链路可读）

**fixture**：`v2/evidence/D2-compat-baseline-run.jsonl`
= 既有真 LLM 跑批 `v2/evidence/run_t136_real_llm_canon_n20.jsonl` 的**逐字节副本**
- sha256 = `7049c27227f8cfd637da6fb14e01e34a241b4cf52f71c8320b150df8e506698c`
- 规模：130,296 事件；`MSG_DM 165 / MSG_GROUP 8 / MSG_PUBLIC 59`（共 232）；provider 全 `openai_compat`
- 特征：**无** `thread_id` / `msg_uid` / `turn_index` / `reply_to` / `participants` / `ctx`（v0 旧格式）

## 验证命令与结果（全部 rc=0，无异常）

| # | 消费方 | 命令 | 结果 |
|---|---|---|---|
| 1 | obs 指标 | `python3 -m obs metrics --log v2/evidence/D2-compat-baseline-run.jsonl` | **rc=0**，无 stderr |
| 2 | D2 线程指标（读侧降级） | `python3 tools/d2/thread_metrics.py v2/evidence/D2-compat-baseline-run.jsonl -o v2/evidence/d2_metrics_compat_oldlog.json` | rc=0；`has_thread_fields=false`；tid 口径 → **232 个单发线程**（轮次=1）；`msg_uid_unique=null`（无该字段）；`reply_to_same_thread=true`（无指针，不误判）；temporal 口径另算：最长链 8 |
| 3 | 前端线程数据 | `python3 frontend/tools/gen_threads.py --log v2/evidence/D2-compat-baseline-run.jsonl --summary` | rc=0；`legacy_threads=232`、`threaded_messages=0`、`legacy_messages=232` ⇒ **旧格式被判为 legacy 空态**，不崩溃、不臆造线程 |

## 结论

- 新字段**只追加**：旧日志缺键 ⇒ 走默认值（`None`/`[]`/单发线程），无 KeyError、无解析异常；
- 线程相关指标在旧日志上退化为「单发、轮次=1」，与 D5 定稿口径一致（可由同一脚本前后并算）；
- 前端把无 `thread_id` 的日志标为 `legacy`，**不做线程推断**（避免伪造结构）。

> 复现：以上三条命令在项目根与 `code/` 下即可直接执行；结果随本文件同次提交。
