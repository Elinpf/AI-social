# v0-anchor 基线锁定记录（D5）

> 状态：**已锁定（ADMITTED / strict / evidence）**｜锁定时间 2026-10-20 17:55 (+08:00)｜锁定人 eval-researcher
> 本文件是「v0 基线唯一历史锚点」的交接凭证，任何引用 v0 读数的报告都必须引这里的三件套。

## 1. 身份与 sha

| 项 | 值 |
|---|---|
| 批次目录 | `v2/evidence/run_d2_before_n16_seed42/` |
| `run.jsonl` sha256 | `c1f86bf61f62b3a0ce8e17e0c2312791cf0262381cd2120c2a63c9b6258963cf`（sha8 `c1f86bf6`） |
| `meta.json` sha256 | `165c002a9d0f0241cf3639115d8f7a5271d48d1b4ef02e4537c6f9af5aed61b5` |
| `code_sha` | `dc93c9d960fc6b6c045807b71943c708310f2db8` |
| 代码身份补充 | `WORLD_INIT.config_components.life_v2.json` = `ff230d69…`（= HEAD 版）；`git_dirty_code_files=[]` |
| 规模 | n=16 × rounds=84 × seed=42（真 LLM，`openai_compat` / `DeepSeek-Flash`） |
| 事件数 | 186,972（`wc -l` 与 `meta.events` 一致） |
| 消息 | `MSG_DM=132`、`MSG_PUBLIC=48`、`MSG_GROUP=7`（合计 187） |
| LLM 调用 | 2,905（cached 1,698，ratio 0.5845；degraded 0） |
| 缓存性质（repro-verifier 补） | 唯一 `prompt_hash` = **1,207**，去重率恰好 58.5%；集中在 `importance`（1,747 次调用 / 仅 150 个唯一 prompt）⇒ **同 run 内同参去重的合法命中**，不是跨 run/共享缓存污染（`cache_key` 含 `engine_version + prompt_hash + model`）。看到 58.5% 不得误判为污染。 |
| `git_dirty_files` 性质（repro-verifier 补） | 35 项**全部为 `??` untracked**（tools/d2、tools/d5、若干 md），**无任何已跟踪文件被修改** ⇒ 代码树实质干净，`code_sha` 有效。对 v0 记 **PASS（带注）**；对 A0 及之后各臂仍按 `[]` 硬卡（S0a）。 |
| 墙钟 | 16:56:00 → 17:47:50，`duration_sec=2967`（≈49 分钟） |

## 2. meta 为「后补」的处理（leader 裁决口径）

原跑批脚本 `tools/d2/run_batch.sh:58` 有拼写错误（`-msg: command not found`），跑完时 meta 写入步骤未执行。经 leader 裁决：**不重跑，后补 meta，但必须由日志派生**。

- `meta.generated_after_run = true`、`meta.generated_at = 2026-10-20T17:50:23`、`meta.derived_from_log_sha256 = c1f86bf6…`（与本记录 run sha 一致）。
- **独立复核（本人执行，非采信作者）**：直接解析 `run.jsonl` 得到 `WORLD_INIT.seed=42`、`AGENT_BORN` 计数=16、`round` 集合 0..83（84 个）、`TURN_SEAL=84`、`LLM_CALL.payload.provider={openai_compat}`、`model={DeepSeek-Flash}` —— 与 meta 中 `seed_in_log / n_in_log / rounds_effective / events / msg_counts / llm_calls / degraded_calls` 全部一致。
- 无法从日志派生的字段（`provider`、`model_requested`、`rounds_per_slot_effective`、`mock_precalib_msg_count`、时间戳等）**按作者声明记录**，不参与事实判定；真跑仍以运行期 `LLM_CALL.payload.provider` 与门禁 rc 为准。

## 3. 门禁与准入

| 检查 | 结果 |
|---|---|
| `cd code && python3 -m obs llm-cost --log <RUN>/run.jsonl --require-provider openai_compat` | **rc=0**；`by_provider={"openai_compat":2905}`；`degraded=0`；`problems=[]` |
| `dialogue_metrics.py --meta` 准入 | **ADMITTED / strict / evidence**，B-7…B-21 全部 PASS（含 B-2b manifest 实际生效值、B-9 条数一致、B-15 `MSG≥150` 且 `MSG_DM≥100` 且会话线≥12、B-19/20/21 三层真跑） |
| D2 前树确认（S0b 反向，**已按 codebase-scout 勘察修正路径**） | `git grep -n "thread_id\|msg_uid\|turn_index\|reply_to" -- code/engine code/life code/orchestration @dc93c9d` **为空**（仅 `code/frontend/*` 有同名演示字段，与事件层无关）⇒ 确为 D2 前树。**注意**：判据不能只看 `code/life`——D2 的字段落点在 `code/orchestration/integration.py::_do_social`（MSG_* payload 组装处），只看 life 会在 A0 臂上同样为空、造成误判 |
| 主树等价性（repro-verifier 补） | `git diff --stat dc93c9d HEAD -- code/life code/orchestration code/config` = **空** ⇒ 当前主树与 before 臂代码等价，A0 复用主树时代码基线干净 |

| 脚本入库 commit | **`b306a40`** |

## 4. 读数产物

- `v2/evidence/d5_metrics_v0anchor.json` / `.md`（S/K/L/E/F 全指标 + 准入明细 + 全部 sha）
- `v2/evidence/d5_llm_purpose_audit_v0anchor.json` / `.md`（purpose 层审计 + 成本汇总）
- 方法文档读数表：`D5-评测方法.md` §4

## 5. 复算命令（可复制）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 tools/d5/dialogue_metrics.py \
  --log v2/evidence/run_d2_before_n16_seed42/run.jsonl \
  --meta v2/evidence/run_d2_before_n16_seed42/meta.json \
  --out-json v2/evidence/d5_metrics_v0anchor.json \
  --out-md  v2/evidence/d5_metrics_v0anchor.md
python3 tools/d5/llm_purpose_audit.py \
  --log v2/evidence/run_d2_before_n16_seed42/run.jsonl \
  --out-json v2/evidence/d5_llm_purpose_audit_v0anchor.json \
  --out-md  v2/evidence/d5_llm_purpose_audit_v0anchor.md
```

## 6. 冻结声明

D2 合并后事件结构（`legacy` → `explicit`）变更，**该日志不再可重算**。此后所有「前后对照」必须引用本记录的三件套（run sha256 / meta sha256 / code_sha），不得用其它日志替代或反推 v0。t300/t355 仅作噪声带与历史参考，**不作对照臂**。
