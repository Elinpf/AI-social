# T366 · 非作者独立核验：`D3` 口径②（`T353` 端口 + `T364` 消费）

- **复核人**：sandbox-test-lead（**非作者**）｜ 被核：**`1ffd7eb`**（T353+T364 同批）
- **脚本**：`v2/evidence/t366_d3_worldparams_verify.py` + `t366_probe_hash.py`（只读；不改 `code/`）
- **装置**：`build_world(seed=42, n=6, config=cfg)`（**life 业态** via `KernelAdapter`，**与线上/T355 同源**）
- **命令**：`python3 v2/evidence/t366_d3_worldparams_verify.py all`（与 `T362` 并行、纯 mock、不动主树）

---

## ① 消费点三档（防 inert）+ 纯度（运行时反向）

| 组 | `_wp_reads` | `_wp_nonempty` | `_wp_changed_choice` |
|---|---:|---:|---:|
| **夹具 ON**（`wd.festival@hall`，⚠️**人为提高剂量/注入指令**） | 144 | **138** | **72** |
| `propagate=False` | 144 | **0** | **0** |
| 默认 `conservative`（如实稀疏读数） | 144 | **0** | **0** |

- ①开>0 ✓ ②非空>0 ✓ ③**真改变选择>0** ✓；**关⇒非空必=0、改选择=0** ✓。
- **纯度（运行时）**：改计数后 **`state_hash` 不变** ✓；**无 wp 事件** ✓；**`restore()` 不重置计数** ✓。
- ⚠️ **夹具口径声明**：`festival@hall` 每回合必发 = **人为提高剂量/注入指令** ⇒ 本组只证 **"通路 + 三档计数可测"**，**不代表"默认世界可感"**（默认可感度属 `T365`/`T355`）。默认 `conservative` 组：reads=144 但 **nonempty=0**（24 回合无指令）⇒ **稀疏**，如实报。

## ②' 只对未来 `[start,end)`（纯函数单测）

单条 `WORLD_GROUP_EVENT(start=5,end=8)`：`t=5,6,7` ⇒ `activity_weight={'hall':40}`；`t<5` 与 `t>=8` ⇒ 空。**PASS** ✓

## ② `dose=0 ⇒ 恒等` + 负例

| 比较 | 结果 |
|---|---|
| **同 sha 内翻开关**：`propagate=false` vs 夹具 `dose≠0` | `e30ce118…` vs `c31e15cf…` ⇒ **不同 → 负例真红** ✓ |
| **跨 sha**（两开关同关）：基线 `1ffd7eb^`=`a7867c4`(pre-T353, time.off) vs 当前树(`propagate=false`+time.off) | `5932c58a…` **==** `5932c58a…` ⇒ **恒等** ✓ |

- ⚠️ 注明：基线 `a7867c4` **已含 `T354`**（`time.ongoing` 在 HEAD）；两树 `time.ongoing` **同关**、`propagate` 关 ⇒ **差异只可能来自 T353**。`state_hash` 是**世界状态纯函数、不含代码 sha**，故跨 sha 相等 = **无行为变**的有意义证据。

## ③ 受控剂量对照（`moderate`，A0/A1）

- `[A0]`(off) counts=5196 wp=(144,0,0)；`[A1]`(on) counts=5196 wp=(144,0,0)；**非零族 delta = 全 0**；`state_hash` **相同**。
- ⚠️ 按通则：**delta≈0 不得判"等价"或"inert"**（稀疏世界预期）⇒ **回 ① 看消费点**（①③ 已证通路真通）。24 回合内 `moderate` 未触发指令属正常。

## ④ 声明合规

- **默认剂量未改**：`code/config/world_director.json` 仍 `dose_curve:"conservative"`（仅新增 `propagate.enabled=true`）✓；"默认剂量下影响稀疏"已如实写明 ✓。
- **`make verify`**：见下（另找空档跑，不与 T366/art 并行）。

## 结论

**`D3` 口径② 可过闸**：
- 消费点**真被读**（`_wp_changed_choice=72` 在受控夹具下），**关⇒零非空**；三计数**纯观测**（运行时反向证实）；
- **`dose=0 ⇒ 恒等现状`**（跨 sha `state_hash` 逐位相同）+ 负例真红；**只对未来 `[start,end)`** 成立；
- `moderate` A0/A1 **delta≈0**（**稀疏，不作 inert/等价结论**；依据回到 ①）。

*（T366 非作者独立核验 — sandbox-test-lead；`make verify` 待空档补）*
