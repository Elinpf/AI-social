# D12-D（T2 臂）执行注记 —— 引用时的两条必要限定

> 作者：`prompt-linguist`（执行方）｜ 2026-10-23 10:12 ｜ **本文不含判读**（判定归 eval-researcher）

## 1. `id_leak_rate = 0.0039`（1 条）**不是本臂引入**

- 该臂跑在 **`feat/d12c-dedup @ 5ca515d`**（parent `a977cb0`），**早于** L-13 人话映射修复 `882e5dd`；
- 因此那 1 条裸 ID 属**既有残留**（L-13 未修树），**不得归因于 D12-D 的两行提示词**；
- 引用时写法建议：`id_leak_rate 0.0039（1/510，既有 L-13 残留；本臂树早于 882e5dd，非本臂引入）`。

## 2. 三态 identity（引用时三行都要给）

| 态 | prompt_fn_sha256 | 日志 |
|---|---|---|
| T0 | `5cf08593d562dc09fdd42ab289319a819481c4882701407b039fa514ff8293f7` | `run_d12c_off_n16r60_seed42` |
| T1 | `effc14dbffdb6865aa52d9d8adab9db269ab3b92ae9a1a230a22cab6c0ed73f5` | `run_d12c_on_n16r60_seed42` |
| T2 | `ca61423cb60c3be5a500df7f1de0aeb691f65e68a4b417be0817f726315e51cf` | `run_d12d_on_n16r60_seed42` |

- 分支：`feat/d12c-dedup @ 5ca515d`；`git diff --numstat a977cb0 feat/d12c-dedup` ⇒ `code/life/agent.py` + `tools/d12d/render_d12d_prompt.py`（**只这两个文件**）；
- T0/T1 **逐字复现** ⇒ 接线未污染，T2 差值只能来自新增两行。

## 3. 执行事实（供复算）

| 项 | 值 |
|---|---|
| rc | 0 |
| 墙钟 | 09:24:46 → 10:08:20 = **43m34s** |
| calls / cached / 网络调用 | 2,878 / 1,474 / **1,404** |
| `llm-cost --require-provider` | rc=0，`{openai_compat: 2878}`，`degraded=0` |
| 结构 | seals 60（0..59）、`WORLD_INIT 1`、MSG 510、线程 169、ge3 77、`msg_uid` 无重复 |
| switch_proof | `/proc/3500780/environ` ⇒ `LIFE_PROMPT_D12C_SPECIFIC=1`、`LIFE_PROMPT_D12C_DEDUP=1` |
| arm_state_check | PASS=6 / FAIL=0 / CANNOT-VERIFY=1（C1 跨树不设期望） |

## 4. 我给 eval 的口径立场（如需对外引用）

- **灰区（降幅 5.0–5.88pp）**：与 eval 一致同意写「**不足以下结论**」，**不改写**为"机制生效但主判据未达"；**阈值一个不动**；
- 我只提供执行事实与路径，**不写任何方向性结论**（包括不写"有效"或"无效"）。
