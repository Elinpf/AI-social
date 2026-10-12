# T281 账本常驻削减 —— 08 口径评估（7 项）

> 作者：仿真引擎与统计架构师（sim-engine-stats-architect）｜ 应 T281（sim-system-architect）
> 权威：`v1.1/08-engine-stats-extension.md`（事件 schema/统计/审计口径）｜ 设计稿：`v2/refs/ledger-residency-reduction.md`
> 定位：**纯存储层**，不改事件顺序/判定/`state_hash`。故 08 只定"**边界与可解释口径**"，不新增事件语义。

---

## 总原则（08 口径，先立后评）

1. **日志仍是唯一记录**：段文件 + 轻索引必须能**完整解释世界**（索引可由段重建；段丢失=日志丢失，等同现状）。
2. **`seq` 全局全序不变**；**段边界必须落在回合边界**（同回合事件**不得跨段**）——保 seq 全序 + 与 `TURN_SEAL` 对齐。
3. **`state_hash` 不变**（只依赖折叠后 state 投影，不含 records/index）——前提：事件顺序与折叠语义不变。
4. **不新增事件类型**；如需段锚点，**复用 `TURN_SEAL` 加可选字段**（只增不改）。
5. 开关 **默认不启用**（先落地不启用，与 `wake.enabled` 同纪律）。

---

## 逐项口径

### 1. 段（segment）定义 —— **按回合，不按字节**
- **边界 = 回合**（推荐默认 `SEG_ROUNDS=12`，与 T262 `--flush-every 12` 对齐）。理由：round 是语义/审计的自然单位、与 `TURN_SEAL` 对齐、可"按段重建/按周归档"；**字节边界会把一条事件切半**、破坏"日志=记录"、与 round 脱钩 → **不采纳**。
- **命名/编号**：`ledger.seg.<start_round>-<end_round>.jsonl`（编号用**起始 round**：稳定、可排序、可重定位）；段文件头记 `start_seq/end_seq/first_hash/last_hash/engine_version/ts`。
- 硬约束：**段边界=回合边界**，同回合事件不跨段。

### 2. 轻索引 schema
- **推荐**：`seq → {round:int32, type:enum_id(int16), phase:int8, actor:agent_idx(int32), offset:int64, len:int32}`。
- **`hash` 是否含**：**默认不含**（每事件 hash 在段文件里；链式校验按 `prev_hash` 顺序读段即可）。**段级**存 `first_hash/last_hash` 便于快速校验/定位。若需"按 seq 快速去重/校验"再选含 hash（增常驻，需权衡）。
- **编码**：紧凑二进制/列式；`type`/`actor` 用**段级字典表**（枚举 id / agent 索引）。定长字段优先。

### 3. 落盘时点/顺序 —— **保 `seq` 全序**
- `SEG_ROUNDS=12` 默认 ✓（对齐 T262）。
- 顺序：**P6 唯一 append（内存尾段）→ `TURN_SEAL` → 若跨段边界则"原子封段（temp+`os.replace`）+ 切新段"**。即段封存**在回合末 seal 之后、下一回合开始之前**；`TURN_SEAL` 与段边界**对齐**（一段含整数个回合）。
- **行缓冲 vs 段追加**：当回合仍走 P6 唯一 append（不逐行落盘），封段才落盘——**append 点仍是 P6，未变**。

### 4. 读回路径（重放/续跑 T276）
- **重放** = 按 `seq` 升序读"段文件（按 start_round 排序、段内 seq 有序）" → `reduce(apply_event, …, InitialState)`。
- **全序保证**：索引按 `seq` 单调；跨段拼接=段按 `start_round` 排序 + 段内 seq 升序（段边界=回合边界已保证无交叉）。
- **续跑 T276** = 读**最后一段 + 轻索引**重建内存视图；`_observed_seqs` 等**由日志重建**（见 §5 可重建口径）。

### 5. `state.event_index` 轻量化 + 消费者适配
- **裁剪**：`seq→{round,type,phase,actor,offset,len}`，或**仅热点子集** `seq→type`（见下）。
- **消费者盘点（需适配，非我；口径由我定）**：
  - **`OBSERVATION` 锚点校验**（`target_event_seq ∈ event_index`）→ 只需 **存在性 + type**（`seq→type` 即够）。
  - `visible_events`/传播图/`obs` 若干 → 凡"读整条 record"处改为"**经索引取 offset、按需读段**"。
  - 建议：**event_index 缩到 `seq→type`（存在性）**，其余按需读段（LRU 缓存）。
- **可重建口径（08 声明）**：`state.observed`/各 agent `_observed_seqs`/`memories` 索引等**派生集合** = **可由日志重建**、**不入 `state_hash`**、**不入 08 事件语义**；审计时从日志重建（与"日志唯一记录"一致，顺带解 T276"续跑重观测"）。

### 6. 是否新增事件/字段 —— **不新增类型**
- **复用 `TURN_SEAL`**：在其 payload **加可选字段**（只增不改）：`segment_id`、`segment_file`、`segment_first_seq`、`segment_last_seq`、`segment_last_hash`（便于定位段、审计）。
- **不新增事件类型**（守"事件类型更少更好"+ 可解释性）。

### 7. 开关族（进 `engine_version` 指纹）
- `segment.enabled`（**默认 `false`**=行为不变；启用后"尾段常驻+封段落盘"）。
- `index.slim`（**默认 `false`**；启用后 `event_index` 轻量化）。
- 二者同族（§5.8）；`OFF` = 旧行为；改块变指纹（属预期）。

---

## 关于你的只读补测（`builtins.set` / `state` 深尺寸方法敏感）

- **不编数**符合纪律：`state` 深尺寸**方法敏感（36.6 vs 69.8MB）** → 54%"未定位"**如实标【未验证】**，**勿编**。
- 建议按**属性级计数器**（每 agent `_observed_seqs`、`state.observed`、`state.event_index` 逐项 `len`×条目成本）取代深遍历——**测量方法**，非 08 语义；08 只需确认"observed/index 类**可重建**"这一口径（已写入 §5）。
- `builtins.set`（+0.59MB/回合）若确可达自 `engine.state`，**宜归入"可重建派生集合"**（§5）——即**不必常驻**，正与本方案目标一致。

---

*（T281 08 口径评估完。你定稿后我在 08 加一节「账本分段/轻索引口径」（§5/§6 相邻），登记 6 项与开关族；不新增事件类型。）*
