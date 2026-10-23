# D12-C 两臂执行结果（**只列执行事实，不含判读**）

> 执行：`prompt-linguist` ｜ 2026-10-23 ｜ 分支 **`feat/d12c-specific` @ `a977cb0`**（parent `3ec85a0`）
> 起跑方式：`systemd-run --unit=t271-d12c-<arm> --collect`，落 `/system.slice/`；`MemoryHigh=4G/MemoryMax=6G`；`EnvironmentFile=<repo>/code/.env.local`
> **判读不在此文件**：读数与判定由 `eval-researcher`（T-D12C-READ）用冻结读数器 `d12c_metrics.py`（sha `c41cb5ac…`）独立算。

## 1. 串行与墙钟

| 臂 | unit | 起止 | 墙钟 | rc |
|---|---|---|---|---|
| **OFF** | `t271-d12c-off.service` | 05:57:04 → 06:47:03 | **49m59s** | **0** |
| **ON** | `t271-d12c-on.service` | 06:58:58 → 07:38:27 | **39m29s** | **0** |

两臂**严格串行**（OFF 收尾 06:47:03 后才起 ON 06:58:58）；跑批期间未改 `code/life` `code/orchestration` `code/config` `code/engine`。

## 2. 真跑验真（`obs llm-cost --require-provider openai_compat`）

| 臂 | rc | 调用数 | cached | **去重网络调用** | degraded | by_provider |
|---|---|---|---|---|---|---|
| OFF | **0** | 2,878 | 1,474 | **1,404** | 0 | `{openai_compat: 2878}` |
| ON | **0** | 2,878 | 1,473 | **1,405** | 0 | `{openai_compat: 2878}` |

## 3. 结构自证（两臂完全一致 ⇒ 单变量）

| 项 | OFF | ON |
|---|---|---|
| `TURN_SEAL` | 60（0..59，无缺口） | 60（0..59，无缺口） |
| `WORLD_INIT` | 1 | 1 |
| MSG 总数 | **510** | **510** |
| 线程数 | **169** | **169** |
| `msg_uid` 唯一 | 510/510 | 510/510 |
| `ge3`（≥3 条消息的线程） | 77 | 77 |

## 4. 开关证明（`switch_proof.txt`，**执行层真值**）

| 臂 | 取法 | 结果 | 文件 |
|---|---|---|---|
| OFF | `tr '\0' '\n' < /proc/2862341/environ \| grep LIFE_PROMPT_D12C` | **无输出** ✅（期望"变量不存在"） | `run_d12c_off_n16r60_seed42/switch_proof.txt` |
| ON | `tr '\0' '\n' < /proc/3026204/environ \| grep LIFE_PROMPT_D12C` | **`LIFE_PROMPT_D12C_SPECIFIC=1`** ✅（python 进程，非外层 bash） | `run_d12c_on_n16r60_seed42/switch_proof.txt` |

两态 `prompt_fn_sha256`：OFF `5cf08593d562dc09fdd42ab289319a819481c4882701407b039fa514ff8293f7`／ON `effc14dbffdb6865aa52d9d8adab9db269ab3b92ae9a1a230a22cab6c0ed73f5`（均逐字复现于 `d12c_wiring_proof.md §4`）。

## 5. `arm_state_check`（工具 `tools/d9/arm_state_check.py`，同规模结构期望）

| 臂 | 汇总 | 关键行 |
|---|---|---|
| OFF | PASS=6 / FAIL=0 / **CANNOT-VERIFY=1** | C4 结构 PASS（msgs 510 / threads 169 与期望一致）；C1 指标 **CANNOT-VERIFY**（未给 `--tree-expectation`：len/paren **跨树不可比**，故不设期望） |
| ON | PASS=6 / FAIL=0 / **CANNOT-VERIFY=1** | 同上 |

路径：`run_d12c_{off,on}_n16r60_seed42/arm_state_check.txt`

## 6. 观察项（**并列，不作判定**）

| 项 | OFF | ON |
|---|---|---|
| `dup_exact_rate`（`arm_state_check` full-scope） | **0.1020** | **0.0961** |
| `paren_rate`（`arm_state_check` 口径） | 0.8235 | 0.6627 |

## 7. 参考读数（冻结读数器 `d12c_metrics.py`；**仅供核对，判读归 eval**）

| 指标 | OFF | ON | Δ(ON−OFF) |
|---|---|---|---|
| P1 具体性代理 | **88.63%** | **98.82%** | **+10.19pp** |
| P2 第三方代理 | **61.18%** | **77.25%** | **+16.07pp** |
| 纯台词 `len_p50`（去旁白） | **40.0** | **52.0** | +12.0（**未降**） |
| MSG / 线程 | 510 / 169 | 510 / 169 | 0 / 0 |

> 口径提醒（leader 已确认）：该读数器里 `turns_A_p50` 实为"**线程消息条数中位数**"（冻结口径），`paren_rate` 为"**以括号开头的比例（旁白开场率）**"，引用时须照此命名，不得写"轮数"或"含括号块比例"。
