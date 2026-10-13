# refs · T371 设计：`abundance`（`resource_factor_bp`）接通生产消费者

> 作者：econ-dev ｜ 2026-10-13 ｜ 状态：**设计（T355 冻结期，未动码）** ｜ 前置：T367（`world_calendar`/`source="calendar"`）、T353（`WorldParams` 派生视图）

## 0. 问题（事实）
- 【事实】提供方：`engine/world_params.py::world_params(records, round_no, config)` → `{"resource_factor_bp": {place|"global": int(bp)}, "activity_weight":{...}, "market_scarcity_bp":{...}, "active":[...]}`；`supply_shock/disaster` 经 `params.amp_bp` 写入（**负值**），key = `place or "global"`。
- 【事实】`life` 已消费 `activity_weight`（T364，非 inert）；**`resource_factor_bp` 目前只有"非空计数"、无行为消费者** ⇒ **可审计、不可见行为**（潜在第三 inert）。
- 【事实】econ 消费候选：`engine/hooks/production.py` 经 `P.resource_factor_milli(seed, round_no, place, base_res, params)` 计算 `resource_milli`（决定 `PRODUCE.qty`）。**已在跑，天然是行为面**。

## 1. 设计（建议）

### 1.1 接口形状（与 kernel 显式对齐）
- 消费：`wp = world_params(list(state.event_index.values()), round_no, ctx.config)`；取 `wpb = wp.get("resource_factor_bp")`——**必须是 `dict[str,int]`**；若非 dict/缺省 → 视为 `{}`（= 无影响，**不做 str/dict 猜解**，防静默失效）。
- **key 匹配（显式成员判断，避免 `0` 假值坑）**：
  ```
  key = place if place in wpb else ("global" if "global" in wpb else None)
  factor_bp = int(wpb.get(key, 0)) if key is not None else 0
  ```
  （**不可**用 `wpb.get(place) or wpb.get("global")` —— 若 `place` key 存在而值恰为 `0`，`or` 会误落 global。）
- **不做 good 维度**（A 层 `resource_factor` 是**场所**因子；good 维度留待 `market_scarcity_bp` 的消费者）。
- ⚠️ **双计（既有语义、非本任务引入）**：实时发射同时落 `WORLD_DIRECTIVE` + `WORLD_GROUP_EVENT`（同 `directive_id`），`world_params` 对同一指令**累加两次** ⇒ **`factor_bp` ≈ 单指令 amp 的 2×**。阈值/解读按 **2×** 记；是否视作真缺陷由 kernel 另开单（属 `world_params`/engine 域）。
  > ⚠️ **同名不同义标注**：此 **"2×" = `world_params` 同 `directive_id` 双发累加两次**（`T372` 修），**≠ `LLM_CALL` 的"2×"**（后者为调用计量口径：**条数 = 实际调用 + 缓存命中，命中也各记一条**，已结案）。两处"2×"**不可并成一条**。
- ⚠️ **abundance 当前只落 `"global"`**（`calendar.abundance` 未配 `place`）；per-place 需 kernel 扩配置（其域）。

### 1.2 施加方式（整数、可复算）
```
factor_bp = int(wpb.get(place)) if place in wpb else (int(wpb.get("global")) if "global" in wpb else 0)
res_adj   = clamp( res_base_jittered * (10000 + factor_bp) // 10000 , res_min, res_max )
```
- **`dose=0 ⇒ factor_bp=0 ⇒ (10000)/10000 ⇒ 恒等** ✓（保底：剂量恒等）。
- `factor_bp<0`（供给冲击）→ 产量按比例降；仍**只改"情境参数"、不给个体结果** ✓。
- 仅消费**已落账的 `[start,end)`** 窗口（`world_params` 内已按 `start<=t<end` + `directed=true` 过滤）⇒ **只作用未来** ✓、可溯源 `active` ✓。

### 1.3 开关/剂量（三保底对齐）
- **总开关**复用既有 `world_director.propagate.enabled`（默认 true）；`dose` 由 `world_director.json` 决定（不改）。
- **不新增**独立开关（避免开关爆炸）；本消费点自身**无新 state**、不起新事件。

## 2. 证据计划（硬要求：**消费点被读的直接证据**，不得用最终 delta 反推）
实现后（解冻后）产出并绑 sha：
1. **读次数**：production hook 每次计算 `res` 前读 `wp` 的计数（在 hook 内累加，落**审计**：可写 `v2/evidence/**` 的探针日志，或复用 life 同款"最近一次读数"模式 → **不新增事件类型、不入 state_hash**）。
2. **参数非空次数**：`resource_factor_bp` 非空计数（**开 ⇒ >0；关(propagate off / 无 directed) ⇒ 必 =0**）。
3. **实际改变数值的次数**：`factor_bp≠0` 且 `res_adj≠res_base` 的计数（**这才是"真消费"**）。
4. **受控剂量 同 seed 开/关**：族 delta（`PRODUCE.qty` 汇总等）+ `state_hash` 对比。
5. **负例**：读到基线值（`factor_bp=0`）时 `res_adj==res_base`（恒等）。
- ⚠️ **默认剂量下影响稀疏属预期**（同 T364 口径）⇒ 写明"≈0 属预期、非 inert"；**不得把 delta≈0 写成"等价"**。

## 3. 落点与边界
- 改：`engine/hooks/production.py`（消费 `resource_factor_bp`；两处 `resource_factor_milli` 调用点统一走一个包装 `_resource_milli(state, round_no, place, params, ctx)`）。
- 依赖：`engine/world_params.py`（只读调用，不改）。
- **红线**：不预设价格/工资/税/铸币；只改"情境参数"；不新增个体结果；`dose=0` 恒等。

## 4. 待确认（交 kernel-dev / Leader）
1. **接口形状**：`resource_factor_bp` 为 `dict[str,int]`、key ∈ {place, "global"} —— 请 kernel 确认（**今日已两次 `str` vs `dict` 静默失效**，故显式核对）。
2. key 优先级 `place` > `"global"` 是否与 producer 一致（producer 只写 `place or "global"` → 一致）。
3. 读计数落点：用"审计日志/探针"（不入 state、不入事件）是否满足验收措辞。
