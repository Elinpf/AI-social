# T365 设计一致性核对清单（作者自检 · 供 `T368` 复用）

> 文档类型：只读核对清单（**设计作者自检**）｜ 作者：narrative-designer
> 定位声明（**Leader 已确认**）：本清单是"**设计一致性自检**"——盯"**设计意图有没有被实现歪掉**"；**不能替代 `T368` 的独立核验**（团队规矩：**作者不得自证**）。二者互补：本单盯"意图偏差"，`T368` 盯"实现声称的效果是否成立且可复现"。
> 边界：**只读、不动码、不占名额**；结论交 Leader。被核对象：`T367`（实现单）。
> 上游：`v2/refs/T365-persistent-world-layer-design.md`（设计，sha `652491f`）。

---

## 0. 用法

- **何时用**：`T367` 实现落地后（**落地前不看码，避免空核**）。
- **怎么用**：逐条 `DC-x` 跑"看哪一行 → 构造性证据 → 反向负例"；**任一条命中副例 = 设计意图被歪掉**，回报 Leader（交 `T367` 返工），**不在本单里改码**。
- **纪律**：**每条都要"可构造的证据"**（枚举/断言/重算/负例），**不接受"看起来没有"**。

---

## DC-1（最危险）`daypart` 不得新造第二真源

**判什么**：世界层**不得**新增"时间/slot → 活动/日程"的**独立映射表或独立求值路径**；世界层若要影响时段行为，**只能经既有 `world_params`→既有路径的偏置项**。

**看哪一行（落点白名单）**：
- 既有（**应仍在、且是唯一**）：`code/life/agent.py::_base_activity` / `_activity_for`；`code/life/constants.py::DAY_TYPE_PARAMS`；`code/life/planner.py` 的 `(day_type, slot)→活动模板` 表；`SCHEDULE_PLANNED` / `_plan_slots`。
- 世界层（**应只做偏置**）：`code/engine/world_params.py`（+ 日历发射器）——**除既有 `activity_weight` / `need_decay_scale` 偏置项外**，**不得**出现"直接产 `activity`/`place`"的 slot 键。

**复活判据（任一命中即"复活"）**：
1. 出现**第二张** `slot→活动/place` 映射表，或**第二个** `daypart`/时段求值器；
2. `world_params` 新增 `daypart_*` 输出，且 life 用它**绕过** `_base_activity`/planner；
3. `wd.calendar.daypart` 或 `PP-4` 在 config/机制表里**重新出现**（设计已把它移出常驻源表）。

**构造性证据（非"看起来没有"）**：
1. **定义点枚举+断言**：把码中所有"`slot`→活动/place 映射"的定义点 `grep` 出来，断言集合 **⊆ 落点白名单**、**新增定义点 = 0**；
2. **单一写路径**：活动决策的调用图**必经** `_base_activity`/planner，**不存在第二条**入口；
3. **无旁路**：`world_params` 不产 `daypart` 活动键（或仅产既有偏置项）。

**反向负例（证伪武器）**：若真新造 ⇒ 同 slot 会出现**双套并存/双重计数**：既由 planner 选 A、又由 daypart 选 B，或活动/`PLACE_MOVE` 计数**翻倍**。**最小构造 case**：开 `daypart` 后同 slot 的活动事件应**不出现"两套并存"**；若出现 ⇒ 复活确认。

---

## DC-2（最危险）`jitter_bp` 仅由 seed 确定性派生、可离线重算

**判什么**：窗口边界与 `jitter_bp` 的取值**必须**由既有分层 RNG 派生（`rng_branch(seed, "world_calendar", <window_index>)`）；`world_params(t)` 对同 `(log, config)` **可离线重算、逐位一致**；**不得**引入 wall-clock / 未播种随机。

**看哪一行（落点白名单）**：
- 日历/常驻源实现（`engine/world_director.py` 或新增 `world_calendar` 模块）；
- `code/engine/world_params.py` 的 jitter 求值处；
- **反面清单**：任何 `import random` / `time.time()` / `uuid` / 未播种 `Random()`。

**复活判据**：出现 wall-clock、未播种随机源，或 jitter **不进** `world_params` 的确定性路径（如写死在事件里带真随机）⇒ 续跑分叉。

**构造性证据**：
1. **唯一定义点**：jitter 的定义点 ⊆ `{rng_branch(seed,"world_calendar",idx)}`（枚举+断言）；
2. **重算一致**：同 `(log, config)` 对同一 `t`，两次 `world_params(t)` 输出**逐位一致**（离线重算，不重跑世界）；
3. **续跑一致**：`kill@任意 round` 续跑 vs 一次性，`world_params(t)` 轨迹一致（防 `T298` 型分叉）；**装置前提：分进程**（吸取今晚"假分叉"教训，禁同进程连跑）。

**反向负例**：若用了不可重建源 ⇒ 同 `(log, config)` 两次求值**不相等**，或 restore 后与一次性跑**不一致** ⇒ 复活确认。

---

## DC-3（附）窗口边界"发一次"，非每回合

**判**：日历**只在窗口边界**发 `WORLD_DIRECTIVE`（事件数 ∝ 窗口数）；窗口内靠 **profile 求值**，**不是逐回合发**。
**看**：`WORLD_DIRECTIVE(source="calendar")` 计数 ≈ 窗口数（一周内应很小，如 1–2），**远小于** 84。
**负例**：若每回合发 ⇒ 计数 ≈ 回合数（84/周）⇒ 日志膨胀且违"事件少"设计。

---

## DC-4（附）常驻源在 `propagate` 之下 / 不新增事件类型 / 带 `source` 字段

**判**：常驻源受 `world_director.propagate.enabled` 总闸；复用 `WORLD_DIRECTIVE`（**不新增事件类型**）；带 `source="calendar"`（可与偶发 `"rng"` 分栏统计）。
**看**：`world_params.py::propagate_enabled` 仍是总闸；事件类型集合**未新增**；`source` 字段存在。
**负例**：绕过 `propagate`、或新增事件类型、或缺 `source` ⇒ 偏离。

---

## 结论交付格式（交 Leader）

每条给：`DC-x 结论 ∈ {符合 / 复活(附构造证据) / 未落地待核}` + 一行依据（命令+输出或文件行号）。**全符合 ≠ 验收通过**（那由 `T368` 独立核验与实现单门禁承担）。

---

*（T365 设计一致性核对清单完 — narrative-designer；只读、不动码、不占名额；供 `T368` 复用。）*
