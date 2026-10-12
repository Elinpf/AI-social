# T283 诊断：居民行动为何「一瞬间」

> 作者：art-director ｜ 2026-10-12 ｜ **只读诊断，未改任何代码** ｜ 归属：诊断
> 用户原话：**「居民的所有行动都是一瞬间的，一瞬间到了下一个地方，一瞬间聊天交易。我觉得这个不太对」**

## 一句话结论

**这是 (a)：世界层本来就没有「过程」。**
移动被世界层发射为**同一回合内的原子事件对**（`PLACE_MOVE` + `PLACE_ARRIVED` 同 round、seq 差恒为 1，**无任何中间位置**）；聊天 / 交易等事件**根本没有时长字段**。
呈现层虽然对「移动」做了补间，但**世界层没提供任何可展开的时长**，且非空间事件无处可"演"。

---

## 三问 + 证据

### 问 1：日志里有没有「中间位置」？—— **没有**

三份真实日志，逐条统计 **同角色 `PLACE_MOVE`→`PLACE_ARRIVED` 的回合差**：

| 日志 | MOVE→ARRIVED 回合差 | travel_ticks payload | 移动次数 |
|---|---|---|---|
| `sample/run_c_n20.play.jsonl` | **{0: 511}** | {1: 511} | 511 |
| `sample/run_b2_n20_week.play.jsonl` | **{0: 512}** | {1: 512} | 512 |
| `sample/n20_week.jsonl` | **{0: 420}** | {1: 420} | 420 |

→ **回合差恒为 0**（同一回合内），**seq 差恒为 1**（相邻两条）。示例（`run_c_n20` round 0）：

```
PLACE_MOVE  seq49 actor P001 {"from_place":"residence","to_place":"farm","travel_ticks":1,...}
PLACE_ARRIVED seq50 actor P001 {"place":"farm",...}
```
一回合内**只有出发/到达两点，无任何中间轨迹**。

### 问 2：`travel_ticks` 是多少？—— **事件里恒为 1（硬编码），且未被用于计时**

- **代码引用点（唯一权威发射处）**：`orchestration/integration.py:455`（`_do_move`）——
  ```python
  s1 = self._emit_assembled("PLACE_MOVE", p, {"agent_id":..., "from_place":..., "to_place":...,
                                              "travel_ticks": 1, ...})   # ← 硬编码 1
  s2 = self._emit_assembled("PLACE_ARRIVED", p, {"agent_id":..., "place": to_place, ...})  # 同一调用内连发
  ```
  → 两事件**同一次调用连发**，引擎 round **不在其间推进** ⇒ 移动实际占 **0 回合**。
- **config 原值**：`config/topology.json:114` 有 `travel_ticks` **0–3 的矩阵**（例：`residence→plaza=3`、`residence→farm=2`）。但 **`_do_move` 未引用该矩阵**，直接写死 1 ⇒ **连"语义通行成本"都没生效**。
  - 另注：`frontend/tools/gen_topology.py:9` 记录了矩阵的语义（相邻=1、跨环=2、最远=3），仅前端展示对齐用。
- **对照**：`ACTIVITY_*` **有**时长字段（`ACTIVITY_COMPLETED.duration_ticks`，例 3 —— 起于 round0、终于 round3）；而 `MSG_DM`/`MARKET_TRADE`/`TRANSFER` 的 payload **完全没有** duration 字段 ⇒ 交易/聊天**在语义上就是 0 时长**。

### 问 3：渲染是「插值」还是「跳变」？—— **移动是补间；但时长由显示距离决定，与世界无关**

- **呈现层确实补间**：
  - `src/town.js:1028 renderState()` → 每回合按 `location` 设 `rec.target = 地点节点坐标(+网格偏移)`；
  - `src/town.js` `tick()`（≈1121 行）→ 向 `target` 缓动：`VMAX=520px/s`、`TAU=0.10`、`AMAX=2400px/s²`（T270 的 ease-in/速度上限）+ 按相位错峰起步；
  - **补间时长 ∝ 显示距离**（VMAX 恒定），**与 `travel_ticks` 无任何关系**。
- **回放节拍**：`src/main.js:945` 每回合默认 **800ms**（`?speed=` 可调）；`snapAgents()`（`main.js:260`）在 still/截图模式**直接置位** `container=target`。
- ⇒ 由于世界层在移动时把 `location` **同回合翻到目标**，`renderState` 当回合就把 `target` 设到目的地：视觉上是一段**短的显示补间**，而非按世界时长的"走过过程"。

---

## 归属与修法（**均未实施**）

- **根因在【世界层·语义】**：要让"走过去 / 聊天 / 交易"**有可见时长**，需改 `orchestration/integration.py:_do_move`（按 `topology.travel_ticks` 计回合、延后 `PLACE_ARRIVED`、或发中间位置），并给非空间事件加 `duration`/占回合。
  → 这属于 **`code/{orchestration,life,...}` 冻结区**、且会改 **engine_version 指纹** ⇒ **只能白天开发相位做 + 先写方案评审**。
- **呈现层能做的**：把**已有的瞬时对"拉长显示"**（如让出发态 hold 到本回合渲染结束、补间时长 ∝ 距离且 ≥ 一个最小节拍）。
  → **只能改善"移动"，无法给聊天/交易时长**（世界层无该时长）⇒ **单靠展示层不能完整满足用户**。
- **最小可回退改法（(b) 型，纯展示，若要先改善"移动"）**：在 shell 的 `displayState`/`replay` 折叠处，对 `PLACE_MOVE` **保留出发地点直到该回合显示结束**，让 renderer 的补间跑满预算 ms；不改语义、不改指纹。**（需与 frontend-dev 协同，未实施）**

## 建议

用户抱怨**同时包含**"聊天交易一瞬间" ⇒ 根因属 **(a)**，应作为**世界层议题（白天相位）**讨论：**移动耗时是否按 `topology.travel_ticks` 计？事件是否应带 duration/占用回合？** 展示层可先做"移动过程拉长"作过渡，但不能替代世界层。
