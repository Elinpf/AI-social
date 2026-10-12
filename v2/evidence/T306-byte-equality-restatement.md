# 台账重述（T306 / T299 遗留义务）：『逐字节一致』结论按新口径重述

> 作者：release-engineer ｜ 2026-10-13 ｜ 任务：**T306**（T299 遗留义务）
> **新门 = `a1617d7`**：`tools/t271/semantic_log_sha.py` —— 世界语义投影 sha256：**只排除** `LLM_CALL.payload.{cached,tokens_in,tokens_out,cost_units}`，**保留** `cache_key/prompt_hash/meta_digest/engine_version/provider/purpose/model/priority/tier/thinking/degraded` 与 **`TURN_SEAL.state_hash`**；对规范化事件**重算哈希链**。
> 目的：逐条列【原口径 / 新口径结论 / 是否独立核 / 在哪个 sha·指纹·cut 下成立 / 是否已失效】+ 命令与读数，**可独立复算**。（本文取代 `v2/evidence/T299-ledger-restatement.md`。）

## 判据速览
- **新门**：`python3 tools/t271/semantic_log_sha.py <log>`（打印世界语义投影 sha256）；
- **探针**：`T271_VR_GATE=1 T271_VR_REVERSE=1 T271_VR_CUT=89 bash tools/t271/verify_native_resume.sh`（cut=89 无真分歧→PASS；cut=75 真分歧→FAIL=真阳性）；
- **门独立核**：art `v2/refs/T299-gate-independent-review.md`（**PASS**，三点 + 双面数据）；`T305`（sandbox-test-lead）进行中。

## 1. 逐条重述

### T276 — flush 前缀**续跑** ≡ 一次性跑
- **原口径**：整份日志 sha256（旧探针，**含** `LLM_CALL` 计量 + 由它引起的 `hash/prev_hash/TURN_SEAL.last_hash` 下游差）。
- **新口径结论**：**世界语义一致**（`cut=89` 实测 PASS）；**但非普适**。
- **独立核**：T276 结论本身【**未见独立复核记录**】（作者/Leader 核）；**本次重述=作者自核**；**门=art 独立核**。
- **成立范围**：sha `a1617d7` 代码 + `seed=9/n=2/150r` + **`cut=89`** 成立；**`cut=75` 不成立**（真分歧）。
- **命令/读数**：`T271_VR_GATE=1 T271_VR_CUT=89 bash tools/t271/verify_native_resume.sh` → **PASS**（语义投影 `resumed==oneshot`）；`... T271_VR_CUT=75 ...` → **FAIL**（`state_hash` 不等数=74）。

### T288 — life `restore()` 三档「逐字节一致」
- **原口径**：整份日志 sha256（同 T276 旧探针）。
- **新口径结论**：**世界语义一致**；**非普适**（cut 相关）。
- **独立核**：Leader 通报三档过；**art `T304`（复核 T298 修复）进行中**；本次重述后仍**待独立核**。
- **成立范围**：其原三档配置 + 对应 sha；**对 cut 敏感**（`@75` 分叉 / `@89` 一致）。
- **命令/读数**：同 T276（`cut=89` 对照）；实缺口见 §3。

### T236 — canonical 基线重冻（A/B/C/D）
- **原口径**：**指纹三方一致**（`WORLD_INIT.fingerprint` == preflight == 当前代码）+ `chain/replay/conservation` True；**并非**"续跑≡一次性"断言。
- **新口径结论**：**不受本门影响**（其"一致"= provenance/指纹，非世界语义比对）⇒ **仍成立**。
- **独立核**：obs 自核（`v2/evidence/t236-refreeze.md`）。
- **成立范围**：sha **`6a5f14e`**、指纹 **`f1ea31a3`**、N=20/rounds=84/seed=42、事件 **301,384**、`state_hash=a8b6da39`。
- **命令**：见 `t236-refreeze.md §1`（复算命令）。

### T292 — 共享 `freeze_cache` 干净消融 A/B/C/D
- **原口径**：**事件计数差 + 指纹 + cache 命中率**（**非**逐字节/语义 sha）。
- **断言**：`B−A = −2`（关世界导演 ⇒ 世界逐项一致，差额=2 个 noop 事件）；A/B/C/D 同指纹 **`f378d5d3`**。
- **新口径结论**：属"**计数一致**"旁证；**不受门定义冲突**。若其日志在（`/tmp/t292/run_*.jsonl`），可用新门对 A/B **复算语义投影**（**建议 obs 补**；本轮【未复算】）。
- **独立核**：obs 自核（`v2/evidence/t292-shared-cache-ablation.md`）。
- **成立范围**：共享 side `/tmp/t292/shared`、指纹 `f378d5d3`；**与 T236 的 A（`f1ea31a3`）不可直接比**（`time.json` 进指纹 ⇒ cache 全 miss）。

### T287 期① — 零行为变化（off vs 现状）
- **原口径**：**除指纹派生字段外**逐条一致 + `state_hash` 相等。实测：剥 `hash/prev_hash` → 118 差；**再剥指纹派生**（`WORLD_INIT.{fingerprint,config_digest,config_components,time_model,time_U}`、`LLM_CALL.{engine_version,cache_key}`、`TURN_SEAL.{last_hash,state_hash}`）→ **0/1635**；`state_hash` 序列相等。
- **新口径结论**：**世界语义一致（仍成立）**；**但口径不同** —— T287 比的是**异配置**（off vs 现状，指纹不同 ⇒ `engine_version/cache_key` 本就不同），而**新门保留 `engine_version/cache_key`** ⇒ **T287 的"逐字节"不能用新门直接判**。其"零行为变化"= **非指纹语义字段 0 差 + `state_hash` 相等**，与新门"世界语义一致"**同向、互证**。
- **独立核**：kernel-dev 自核（`v2/evidence/T287-phase1-off-control.md`）；`make verify` 全绿（kernel 报）。
- **成立范围**：seed=42/n=4/rounds=12、事件 **1635**、sha 见 T287 提交（`76de474`）。

## 2. 汇总表
| 条目 | 原口径 | 新口径结论 | 独立核 | 是否已失效 |
|---|---|---|---|---|
| **T276** | 整份 sha（含计量） | **世界语义一致**（cut=89） | 本次=作者自核；门=art 核 | **cut=75 失效**（真缺陷，交 life） |
| **T288** | 整份 sha | **世界语义一致** | art `T304` 进行中 | 非普适（cut 敏感） |
| **T236** | 指纹三方一致 | **不受影响，仍成立** | obs 自核 | 否 |
| **T292** | 计数差 + 指纹 | 计数旁证；可用新门复算 | obs 自核 | 否 |
| **T287期①** | 除指纹逐条 + state_hash | **世界语义一致**（口径不同） | kernel 自核 | 否 |

## 3. 唯一"已失效 + 替代"项
**T276/T288 的"逐字节一致"在 `cut=75` 上失效**（世界真分叉：`state_hash` 不等=74，首个不等 round=76）。
- **替代结论**：`cut=75` 起 resume ≠ oneshot（**②类确定性缺陷**，非哈希序/竞态/cache）。
- **最小复现**：`bash tools/t271/repro_resume_cut.sh 75`（对照 `89`）→ 已交 **life-layer-dev**。
- **修好后**：`cut=75` 应转 `==oneshot? yes`，届时 T276/T288 可在**任意 cut** 上成立。

## 4. 命令总表（独立复算）
```bash
R=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 $R/tools/t271/semantic_log_sha.py <log>                          # 世界语义投影 sha256
T271_VR_GATE=1 T271_VR_REVERSE=1 T271_VR_CUT=89 bash $R/tools/t271/verify_native_resume.sh   # 期望 PASS
T271_VR_GATE=1 T271_VR_CUT=75 bash $R/tools/t271/verify_native_resume.sh                      # 期望 FAIL(真阳性)
bash $R/tools/t271/repro_resume_cut.sh 75                                # cut 缺陷最小复现
```
- T236 复算：`v2/evidence/t236-refreeze.md §1`；T287 对照：`v2/evidence/T287-phase1-off-control.md`；T292：`v2/evidence/t292-shared-cache-ablation.md`。

## 5. 诚实边界
- 【未复算】T292 的 A/B 语义投影（其日志在 `/tmp/t292/`，建议 obs 用新门补一次）；T288 的"三档"原始日志未逐一取到，结论据其证据重述。
- 本重述为**文档**（未改门/探针）；门本身独立核见 art 报告 + `T305`。
