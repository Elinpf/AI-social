# T371 证据骨架 + 反向负例设计（冻结期预写；解冻后填数）

> 作者：econ-dev ｜ 2026-10-13 ｜ 状态：**证据骨架（待解冻执行）** ｜ 关联设计：`v2/refs/T371-abundance-consumer-design.md`
> 纪律：**直接证据 = 消费点被读**（不得用最终 delta 反推）；证据绑 **sha + 生成命令**；**不得把 delta≈0 写成"等价"**。
> ⚠️ **2× 口径**：`T355` 基线为**未修**状态，`resource_factor_bp` **虚高 2×**（`T372` 将修）⇒ 本证据的阈值/断点按"当前=2×"解读，并注明"待 `T372` 修复后需复核阈值"。

## 0. 消费点与施加（事实/设计）
- 消费点：`engine/hooks/production.py` 生产 tick 内读 `world_params(...)["resource_factor_bp"]`（施加见设计稿：`res_adj=clamp(res*(10000+bp)//10000)`，`dose=0⇒恒等`）。
- 提供方：`engine/world_params.py::world_params`（**只读**；`propagate.enabled` 总闸、`[start,end)` 未来窗、`directed=true`）。
- ⚠️ **「2×」同名不同义**：本文件/设计稿的 **2× = `world_params` 同 `directive_id` 双发累加两次**（`T372` 修）；**≠ `LLM_CALL` 的"2×"**（后者=条数含缓存命中、已结案）。两者**不可并成一条**。

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

---

## 5. 计数在 econ 侧【怎么取】（可执行；不碰 state/事件、不改默认行为）

**落点（实现时加）**：`engine/hooks/production.py` 加一个**模块级探针槽**（默认 `None`，零开销、不入 state、不产事件）：
```python
_PROBE = None   # 证据/单测用：None=默认（无行为变化）；签名 probe(event:str, info:dict)
```
在消费点内（读 `wpb` / 施加前后）**仅在 `_PROBE is not None` 时**回调：
- 读时：`_PROBE("read", {"round": r, "place": place})`（**每次计算 `res` 前读 wp 即计**）；
- 判定非空：`_PROBE("nonempty", {"keys": sorted(wpb.keys())})`（`wpb != {}` 时）；
- 实际改值（**施加前后不同**）：`_PROBE("applied", {"key": key, "bp": bp, "res_before": a, "res_after": b})`（**仅当 `res_after != res_before`**）。
> 三档计数 = 证据脚本装 `_PROBE` 后按事件名计数；**默认 `_PROBE=None` ⇒ 与基线零行为差异**（`state_hash` 不变）——这正是"只加探针槽、不改世界"。

**三条断言形式**（进 `tests/test_t371_abundance_consumer.py`）：
1. **关态**（`world_director.propagate.enabled=false`，或 `active=[]`）：
   `read > 0 and nonempty == 0 and applied == 0`（**②③ 必为 0**，①可>0=仍读）；
2. **开态 + 定向 abundance 窗口**（`directed`、`place` 命中、`[start,end)` 内）：
   `nonempty > 0 and applied > 0`，且逐条 `res_after == clamp(res_before*(10000+bp)//10000, min, max)`、方向与 `bp` 符号一致；
3. **负例（恒等）**：`dose=0` 或 `bp==0`/key 缺失 ⇒ `applied == 0` 且**逐条** `res_after == res_before`（不靠 delta、逐条比对）。

**不脏树/不越界**：探针槽在 `code/`（解冻后随实现一起落）；本节仅描述，不现在改码。三档计数**不写 state、不产事件、不入 `state_hash`**。

---

## 6. 期望值口径（关键 · 防假红/假绿；据 Leader 23:41 裁定）

⚠️ **`T371` 的 `res_after` 期望必须按「`T372` 去重后（bp 减半）」计** —— 落地序 `T372 → T367 → T371` ⇒ T371 跑时 `resource_factor_bp` 已是 **1×**。

- **去重前（未修，`T355` 基线口径）**：同一 `directive_id` 双发 ⇒ `bp ≈ 2×单指令 amp`；
- **去重后（`T372` 落地，T371 适用）**：`bp = 1×单指令 amp`。
- **期望式**（T371 落地后）：`res_after == clamp(res_before*(10000 + bp_1x)//10000, res_min, res_max)`，其中 `bp_1x` = **单指令** amp（如 `supply_shock(amp_bp=-X)` ⇒ `bp_1x = -X`，**不是 −2X**）。
- ⚠️ 若沿用去重前数值（−2X）算期望 ⇒ **假红/假绿**；本条为**前置对齐**，跑前须确认 `T372` 已在当前树生效。
- ⚠️ **`T372` 分类口径**：**对 life 的地点选择无影响**（`_activity_for` 按权重取 `min(-weight)`、幅值减半不改"选谁"），**但对 econ 的 `resource_factor_bp` 幅值有影响**（`res_after` 真变）⇒ 四档分类**不得写成"无行为变"**。
- 复核注记：`T372` 落地后，§1 表 ⑥ 的 ×2 边界应从 **2× → 1×** 重跑；`T371` 的 ①–⑤ 亦按 `bp_1x` 口径。
