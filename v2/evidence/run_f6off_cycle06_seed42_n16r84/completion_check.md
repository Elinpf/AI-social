# F-6 OFF 84 轮批 · 收尾核验（`run_f6off_cycle06_seed42_n16r84`）

> 用途：把「跑批中·不得引用」的临时状态解封为**可引用证据**。CYCLE-06 报告 §… 记该批为 `untracked`＋「跑批中（不得引用）」，本文件是那份状态的正式收尾。

## 1. 收尾事实（实测）

| 项 | 值 | 取法 |
|---|---|---|
| rc | **0** | `switch_proof.txt` 末行 `run_batch_rc=0`；`finished_at=2026-10-23T04:56:52+08:00` |
| 起跑 | `2026-10-23T04:09:56+08:00`（`chosen_at`） | `switch_proof.txt` |
| 墙钟 | **46 分 56 秒** | 04:09:56 → 04:56:52（`date -d` 复算） |
| 行数 | **193,976** | `wc -l run.jsonl`（末行为 `TURN_SEAL round=83`，`seq=193975`） |
| `TURN_SEAL` | **84**（`round=0…83`） | 逐行解析 `type` |
| MSG | **686** | 同上（`type` 前缀 `MSG`） |
| `msg_uid` 唯一 | **686 / 686，重复 0** | 逐行取 `payload.msg_uid` 入集合 |
| LLM 调用 | **3,403**，全 `openai_compat`，`degraded=0` | `obs llm-cost --require-provider openai_compat`，`provider_guard.ok=true`，`problems=[]`（rc=0） |
| 去重网络调用 | **1,737**（= 3,403 − 缓存 1,666） | 同上，`total.cached=1666` |
| token | in 369,881 / out 318,194 / 合计 688,075 | 同上 |
| 分用途 | judge 717（thinking 717）、dialogue 714、importance 1,747（缓存 1,597）、reflect 112、negotiation 81、describe 16、plan 16 | 同上 |

## 2. 臂身份（**引用前必须连读**）

- 环境：`LIFE_PROMPT_*` **一个都没设**（`switch_proof` §1 原样输出为空）；`HITT_LLM_PROVIDER=openai_compat`（§3 附加）。
- 代码锚点：`branch=feat/scene-anchor`、`head_sha=f8d95f07518ae7c2cf31e77b896ad9aed55543da`；跑后 `code_sha_now=8f4330e949a0e47a5cf8139248e19c03523f1592`。
- **中间前进的 3 个 commit（`5c5392a` / `cf9b832` / `8f4330e`）经核实全部只改 `reports/` 或 `v2/evidence/` 文档**，`code/` 与 `config/` 未动 ⇒ 树身份不受影响。
- `git status --short code/` 仅为 `??` 未跟踪（`code/frontend/sample/dialogue_cycle0{3,4,6}_*`、`code/v2/`），**无已跟踪文件被改**。

## 3. 能说什么 / 不能说什么

- **能**：本批是 **n=16 × 84 轮、真 LLM、无 mock 混入、结构完整（84 seal）** 的 OFF 臂完整窗，可作为 F-6 的 OFF 参照。
- **不能**：**不得**把它写成「F-6 有效/无效」的结论——它只是 OFF 臂；ON 臂另有其批。**不得**跨树、跨规模与 A0（84 轮但不同 code 锚点）直接比数值后判效应。
- 引用本文件时请同时给：`run.jsonl` 的 `sha256`（见下条命令）——本目录 `run.jsonl` 共 91 MB，落盘后由 `repro-verifier` 复核登记。
