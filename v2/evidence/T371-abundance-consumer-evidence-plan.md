# T371 证据骨架 + 反向负例设计（冻结期预写；解冻后填数）

> 作者：econ-dev ｜ 2026-10-13 ｜ 状态：**证据骨架（待解冻执行）** ｜ 关联设计：`v2/refs/T371-abundance-consumer-design.md`
> 纪律：**直接证据 = 消费点被读**（不得用最终 delta 反推）；证据绑 **sha + 生成命令**；**不得把 delta≈0 写成"等价"**。
> ⚠️ **2× 口径**：`T355` 基线为**未修**状态，`resource_factor_bp` **虚高 2×**（`T372` 将修）⇒ 本证据的阈值/断点按"当前=2×"解读，并注明"待 `T372` 修复后需复核阈值"。

## 0. 消费点与施加（事实/设计）
- 消费点：`engine/hooks/production.py` 生产 tick 内读 `world_params(...)["resource_factor_bp"]`（施加见设计稿：`res_adj=clamp(res*(10000+bp)//10000)`，`dose=0⇒恒等`）。
- 提供方：`engine/world_params.py::world_params`（**只读**；`propagate.enabled` 总闸、`[start,end)` 未来窗、`directed=true`）。

## 1. 需要产出的 6 项（验收要求逐项）
| # | 指标 | 定义 | 采集 | 期望 |
|---|---|---|---|---|
| ① | **读次数** | 生产 tick 内读 `wp["resource_factor_bp"]` 的次数 | 消费点内计数器（审计，不入 state/事件） | >0（有生产活动即读） |
| ② | **参数非空次数** | `resource_factor_bp != {}` 的次数 | 同上 | **开 ⇒ >0；关(`propagate.enabled=false`) ⇒ 必 =0** |
| ③ | **实际改值次数** | `factor_bp≠0` 且 `res_adj≠res_base` 的次数 | 同上（记录 `place/key/bp/res_before/res_after`） | 开且命中窗口 ⇒ >0 |
| ④ | **同 seed 开/关对照** | 族 delta（`PRODUCE.qty` 汇总/按 good）+ `state_hash` | 两次**独立进程**跑（同 seed/config，仅 `propagate.enabled` 不同） | 开≠关（若稀疏则 delta 小、但**非空**）；`state_hash` 不同 |
| ⑤ | **负例A（恒等）** | 读到基线值（`factor_bp=0` 或 key 缺失）时 `res_adj==res_base` | 单测/探针 | **恒等**（证明"读而不该改 ⇒ 不改"） |
| ⑥ | **负例B（T372 边界，×2）** | 同一 `directive_id` 双发时 `world_params` 对其贡献 **×2**（未修） | 直接调 `world_params`（夹具造双发） | 现值 = 单指令 amp 的 **2×**；**`T372` 修复后须 =1×** |

## 2. 装置与命令（解冻后填 sha）
- **分进程**：④ 的开/关两跑**必须各自独立进程**（同进程连跑会造假分叉——今日纪律）。
- 骨架命令（占位，解冻后填真实 sha/参数）：
  - 单元：`cd code && python -m pytest -q tests/test_t371_abundance_consumer.py`
  - 对照（独立进程 ×2，同 seed）：`<run_cmd_on>` / `<run_cmd_off>`
  - 门禁：`make verify`（**同一时刻只跑一个**）
- 证据绑：`code_sha=<HEAD>`、`config_digest=<...>`、`world_params 只读`、`dose/开关取值`。

## 3. 反向负例设计（防"读而不消费"与"假消费"）
- **反向负例 α（不读≠当读）**：把 `propagate.enabled=false`（`resource_factor_bp` 恒空）⇒ ② 必须 **=0**、③ 必须 **=0**、④ 族 delta 必须 **空/`state_hash` 相等**。若仍>0 ⇒ **消费点越权/缓存脏**（FAIL）。
- **反向负例 β（该改必改）**：造一条**定向** `directed` 窗口内 `supply_shock(amp_bp=-X, place=P)` ⇒ 对 `place=P` 的生产，③ >0 且 `res_after < res_before`（方向正确、数量≈`res*(10000-2X)//10000`，**注意 2×**）。
- **反向负例 γ（恒等边界）**：`dose=0`（或 key 不在窗口）⇒ ⑤ 恒等；**不得**出现 `res` 波动。

## 4. 待填（解冻后）
- 实现 sha、①–⑥ 实测数值、④ 的 `state_hash` 对、`make verify` 结果、`T372` 修复后的阈值复核注记（若 T372 先落地，则本表口径改 **1×**，并重跑 ⑥）。
