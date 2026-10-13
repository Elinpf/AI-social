# T331b · 独立复验：`T330`（`fc412a8`）settlement 可见性「走索引」等价 + 脆弱性探测

- 复验人：sandbox-test-lead（**非作者**）｜ 落盘：`v2/evidence/t331b-settlement-port-review.md`
- 绑定被验 sha：**`fc412a8`**（T330）｜ **只读、未改 `code/`**
- 自建脚本：`v2/evidence/t331b_settlement_port_verify.py`（口径不用作者单测）、`v2/evidence/t331b_time_driver.py`
- 运行：`cd code && PYTHONPATH=$(pwd) python3 ../v2/evidence/t331b_settlement_port_verify.py`；时间：`PYTHONPATH=code python3 -m cProfile -s cumtime v2/evidence/t331b_time_driver.py {on|off}`

---

## 0. 结论

**可判为「无行为变」（等价成立）**：自建口径逐条等价 `0 差异`（3 seed）；`state_hash` provider==fallback；独立 `make verify` 全绿。
**但**存在一处**真实的无声退化面**（本单重点）：索引 provider 按 **`id(records)`** 命中 ⇒ **传入“等价但不同对象”会静默回退全扫**（**性能级**、非正确性级）——**这正是 `T327` 原 bug 的同族复发面**，需跟进（见 §3）。

| # | 验收项 | 结果 |
|---|---|---|
| 1 | 独立口径逐条等价 + `state_hash` + ≥2 seed | **PASS**（§1/§4） |
| 2 | 反向验证必红 | **PASS**（§2，检出 60/60 差异） |
| 3 | 身份注册脆弱性探测（成立条件+退化触发） | **已探明**（§3） |
| 4 | 时间收益复现（N=50×12 cProfile） | **复现**（§5，≈2.05×） |
| 5 | 独立 `make verify` | **PASS**（§6，rc=0） |

---

## 1. 独立口径等价（自建，逐条 `seq`）

对 `seed × round × agent` 逐条比对 **provider 路径**（`LV.visible_events(state.event_index, aid, r)`）与 **全扫单一真源**（`contracts.visibility.visible_events(list(state.event_index.values()), …)`）的 `seq` 列表：

| seed | n | rounds | 比较次数 | 差异 |
|---|---|---|---|---|
| 1  | 4 | 10 | 50 | **0** |
| 7  | 6 | 10 | 70 | **0** |
| 42 | 4 | 12 | 60 | **0** |

⇒ **180/180 逐条相等，差异 = 0**。

## 2. 反向验证（必红，证断言非恒真）

把已注册 provider 换成「少返回一条」的包装：同一口径比较 → **差异 = 60/60（全部不等）⇒ 检出=红**。
⇒ 等价断言**不是恒真**（人为不一致**会红**）。

## 3. ⭐ 身份注册脆弱性探测（本单重点）

机制：`register_index(engine.state.event_index, …)` → `_INDEXES[id(records)] = fn`；`visible_events` 用 `id(records)` 查表，**未命中即静默全扫**。

| 探测 | 传参 | `id` 命中 | 行为 |
|---|---|---|---|
| C1 | `dict(state.event_index)`（**浅拷贝**） | **False** | **静默回退全扫（FALLBACK）** |
| C2 | `list(state.event_index.values())`（物化） | **False** | **静默回退全扫（FALLBACK）** |
| C3 | 浅拷贝路径结果 == 全扫 | — | **True** ⇒ 退化是**性能**而非**正确性** |
| C4 | 原始 `state.event_index` | **True** | 走索引（应 True）✓ |

**成立条件**：命中**仅当**调用方传**同一个对象**（`id` 相同）。
**退化触发（无声）**：
- 传“内容等价但对象不同”的容器（浅拷贝 / 新 `list(...)` / 任何重建的 dict）⇒ **静默 FALLBACK**；
- `state.event_index` **被替换/`restore()` 重建**后，旧 `id` 失效 ⇒ 静默 FALLBACK；
- **`id` 复用风险**：旧对象释放后其 `id` 可能被新对象复用 ⇒ 理论**假命中**（罕见但不可忽视）。
**性质**：**性能级无声退化**（结果仍等价）—— 与 `T327` 原缺陷同族。**建议跟进**：① 文档化“必须传稳定对象”（已在 `visibility.py` docstring 有）；② 更强：provider miss 时按**内容指纹**兜底或 **dev-mode WARN**；③ 或改按弱引用/内容绑定，消除 `id` 依赖。

## 4. `state_hash`（provider 路径 vs 全扫）

同 seed/参数下，端到端 12 回合：
```
provider end state_hash = sha256:09b0be5ca86ff51992be75fff30decaffdbccdf4bfcdb19f10342715c8f6398f
fallback end state_hash = sha256:09b0be5ca86ff51992be75fff30decaffdbccdf4bfcdb19f10342715c8f6398f
```
⇒ **相同**。另：只读探针（N=20×5）**HIT 100 / FALLBACK 0**（修复前 0/100），独立复现 ✓。

## 5. 时间收益（同口径，N=50×12，单进程 cProfile）

| 口径 N=50×12 cProfile | 总时间 | 调用数 |
|---|---|---|
| provider-ON（走索引） | **127.311 s** | 317,826,255 |
| provider-OFF（清 provider ⇒ 全扫对照） | **261.120 s** | 712,832,075 |

⇒ **≈ 2.05×（−51.2%）**，复现作者 `252.05s → 127.16s（≈2.0×, −49.6%）` 量级。
⚠️ **非通用乘数**：仅此口径（N=50×12、单进程、cProfile）；本机负载下绝对值会漂移。

## 6. 独立 `make verify`

**实跑（非引用作者输出）**：`make verify` → **全绿**（仓根门禁 + `code` CI，`CI GATE: PASS`），`DONE_VERIFY rc=0`。

## 7. 边界 / 备注

- 本项只验 `settlement.write_memories` 的可见性路径（`LV.visible_events`）。**`settlement.events_this_round`（T319，`kernel=ctx`）仍回退**（`Ctx` 无 `round_events`）—— 属**另案 `T338`**；本复验未涉。
- **不改 `code/`**；探针/驱动脚本落 `v2/evidence/`。

---

## 8. 验收对照

- 独立口径等价证据：§1（180/180，0 差异）✓
- 反向验证变红：§2（60/60）✓
- 脆弱性探测结论（成立条件 + 退化触发）：§3 ✓
- 时间收益复现（标口径）：§5 ✓
- 独立 `make verify`：§6 ✓
- 结论：**可判为「无行为变」**（等价成立）；**附**一条性能级无声退化面待跟进。

*（T331b 复验结束 — sandbox-test-lead，非作者独立复验）*
