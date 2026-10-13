# T368 · 独立核验计划（T367「世界层持续可见」实现）—— 前置阶段

> 核验方：delivery-reviewer ｜ 对象：`T367`（作者 kernel-dev）｜ 本文件 = **前置阶段产物**（只读码 / 写核验脚本，**未执行**）
> 硬前置门：**T367 实现落地 + Leader 广播解冻** 之后才执行；**在此之前不自标 completed**。
> 依据：`v2/refs/T365-persistent-world-layer-design.md`（设计定稿）、`v2/refs/T365-08-register-draft.md`（登记草稿 `61a6cdc`）。
> 纪律：独立复核、不替设计者辩护；**结论可与作者不同**；每项给**命令 + 原始输出**，**含反例/负例**；证据落 `v2/evidence/`。
> 读时基线（只读）：`code/engine/world_params.py`、`code/engine/hooks/world_director.py`（均为**未含 T367 的现状**）。

## 0. 前置状态（截至落笔）
- `T367` = **pending（未落地）**；`T350` 仍在跑 → **部分冻结中**（禁 `make verify`/CPU-IO 重活）。
- ⇒ 本阶段**只**：读码、定位装配点、固化核验方法与反例设计。**不跑**任何重活、**不**动 `code/`、**不**改 `config/`。

## 1. 核验面定位（当前已知，T367 落地后需复核“真装配点”）
- **派生视图**：`engine/world_params.py::world_params(records, round_no, config)` —— 消费已提交的 `WORLD_DIRECTIVE`/`WORLD_GROUP_EVENT`，要求 `directed=true` 且 `start<=t<end`；当前按 `kind` 硬编码映射（festival/mass_event→activity_weight；supply_shock/disaster→resource_factor_bp；tension/edict/scarcity→market_scarcity_bp）。
- **发射方（现状=RNG）**：`engine/hooks/world_director.py::apply_world_director` → `world_director.py::plan_directives`。
- **预期新增（T367）**：日历发射方 `world_calendar`（**只在窗口边界**发 `WORLD_DIRECTIVE(directed=true,[start,end),profile)`；`source="calendar"`；`jitter_bp` 由 `rng_branch(seed,"world_calendar",<window_index>)` 确定性派生）。
- **装配点**：需确认日历 hook 挂在哪一 phase、被谁调用（`engine/runner.py` / `scheduler` / hook 注册表）—— **核验必须经“真装配点”跑一次，不是只看函数存在**（见 §3 方法）。

## 2. 五项核验 —— 每项：判据 / 方法 / 反例

### ① ⭐「窗口边界发一次」成立（核心）
- **判据**：同 seed 下，日历常驻源**只在窗口边界**发**一条** `WORLD_DIRECTIVE(directed=true,[start,end))`；**窗口内不发每回合事件**。
- **方法（事件数证据，非只看代码）**：
  1. 跑一次开日历的 run（短窗即可，须覆盖 ≥1 个窗口边界）；
  2. `python -c` 统计日志中 `type==WORLD_DIRECTIVE` 且 `payload.source=="calendar"` 的条数、按 `(mechanism_id/kind, start_round)` 去重计数；
  3. 断言：**每个窗口 = 1 条**（条数 ≈ 窗口数），且**无**“窗口内每回合一条”。
- **反例**：若逐回合发 ⇒ 条数 ≈ 窗口长度（回合数）⇒ **判偏离设计**。

### ② ⭐「退让不得复活」（构造性 + 反向负例）
- **判据**：`daypart` **不得**成为常驻源、**不得**新增 profile 支路或 kind（life 侧已有“时段→日程/活动”机制）。
- **方法（构造性证据）**：
  1. `grep` 码里是否新增了 `wd.calendar.daypart` / 独立 daypart 常量源 / 新 kind；
  2. `git show <T367 sha> --stat` + 逐文件 diff，确认**没有**新造时间源；
  3. 现有 kind 枚举计数（设计声明 14→15，只 `abundance` 新增）。
- **反向负例**：若新造，轨迹/活动应可观测地**双重计数或冲突** ⇒ 构造“新造场景”，断言不出现双重来源。
- **判据落地**：`count(新造 time-source 符号)==0` 且 kind 增量 == {`abundance`}。

### ③ ⭐ `jitter_bp` 确定性可重建
- **判据**：同 seed 两次跑**逐条相等**；不同 seed 才变；**可离线重算**（不依赖运行时隐状态）。
- **方法**：
  1. **分进程**跑两次（防 `T298` 型同进程污染）：`python ... --seed S` ×2 → 提取 `jitter_bp` 序列比对**逐条相等**；
  2. 换 seed → 断言**变**；
  3. **离线重算**：用 `rng_branch(seed,"world_calendar",window_index)` 独立重建序列，与日志 `jitter_bp` **逐条相等**（证明不依赖 `restore()` 隐状态）。
- **反例**：若离线重算 ≠ 日志 ⇒ 存在不可重建随机源 ⇒ **判缺陷**。

### ④ 三保底 + 剂量
- **判据**：`directed` 必需 / 每源独立开关 + 剂量 / 只作用 `[start,end)`；**`dose=0 ⇒ 关**，与现状**逐条等价（含 `state_hash`）**。
- **方法**：
  1. `dose=0` run vs **无日历** run → 逐条事件/`state_hash` 等价（**验收命令 + 输出**）；
  2. 关闭单个源：仅该源参数消失、其余不变（独立开关）；
  3. 断言不存在 `directed=false` 却进入 `world_params` 的项（保底 a）；断言 `t >= end` 后参数消失（保底 c）。

### ⑤ 可感度两闸（按声明口径核）
- **闸 A（行为族 delta）**：`|Δ|≥5%` 且 **≥2/3 seed 同向** 且 **窗口内 ≥70% slot 有非零偏置**。
  方法：从日志复算受影响族的 slot 级偏置（如 `activity_weight[hall/plaza]`、`resource_factor`）；按 §5.1 装置前提（同 seed/sha/共享 `freeze_cache`、**开关两跑各独立进程**）。
- **闸 B（画面像素）**：**若前端未声明“世界层可见通道 R”⇒ 降级为「闸 A + 首帧对比图（人眼）」**，且明写“**不许拿调美术替代门禁**”。
  方法：复用 `code/frontend/tools/shot.py`/`gate_render.py`；off/on 同 round 两帧 + 差分热力图；**仅在 R 已声明时**做 ΔRGB≥5% 且每采样帧成立的确定性像素闸。
- **⚠️ 恒定偏移**：若窗口 >> 跑批长度（如季节 4 周 vs 跑 1 周）⇒ 证据标 `mode="constant_offset"`；有起止/过渡带/日内轮转 ⇒ `mode="dynamic"`。**不得混成一句“持续可见”**。
- **双向证伪**：日历-only（关 RNG 偶发）→ 持续性仍过；RNG-only（关日历）→ 持续性应**不过**。

## 3. 装置前提（必须写进报告，否则复算复不出）
- 开/关两跑**各独立进程**（`T298` 教训）；kill 方式与进程边界；缓存冷热；`freeze_cache` 共享；引用的 **sha + 读取时刻**。

## 4. 交付物（执行阶段产出）
- 五项各：**命令 + 原始输出**（含反例/负例）+ 逐项**符合/偏离**判定；
- `v2/evidence/` 下：事件计数证据、jitter 两跑比对 + 离线重算、dose=0 等价、闸 A 复算、闸 B/首帧对比图与差分；
- 一份核验报告（结论可注明“与作者不同之处”）→ 交 Leader 复核；**任务不自标 completed**。

## 5. 待前置门满足后第一动作
1. 确认 **Leader 已广播解冻** + `T367` 已落地（读其 sha）；
2. 定位**真装配点**并在真装配点上跑一次；
3. 按 ①→⑤ 顺序执行，逐项落证据。

*（T368 核验计划 · 前置阶段 — delivery-reviewer；未执行、未标 completed）*

---

## 6. 对设计方核对清单（`v2/refs/T365-design-consistency-checklist.md`，`54ef5ae`）的复用与**补漏**

**定位**：清单是**设计方自检**（盯"设计意图有没有被实现歪掉"），**可复用、不得替代 T368 独立结论**（作者不得自证）。清单 DC-1..DC-4 覆盖我的 ②③① 与 ④ 的一部分，且构造性证据写得好，纳入待验清单。

**⚠️ 但清单有两处漏项（按 Leader「发现漏项请补上并说明」补出）**：

### GAP-1（重要）清单**未覆盖可感度两闸（设计 §5，自称"本单最要紧"）**
DC-1..DC-4 只盯"意图未歪"，**完全没提**"用户到底看不看得见"。需补：
- **闸 A**：`|Δ|≥5%` 且 **≥2/3 seed 同向** 且 **窗口内 ≥70% slot 有非零偏置**（持续性——单点尖峰不算）；
- **闸 B**：**前置 = frontend 先声明"世界层可见通道 R"**；未声明前**降级为「闸 A + 首帧对比图（人眼）」**，并**明写"不许拿调美术替代门禁"**；
- **⚠️ 恒定偏移 vs 动态演变必须分栏标注**：`len=4周` 但只跑 1 周 ⇒ 实为常量偏置 ⇒ 证据标 `mode="constant_offset"`，**不得混成一句"持续可见"**；
- **双向证伪**：**日历-only**（关 RNG 偶发）⇒ 持续性仍过；**RNG-only**（关日历）⇒ 持续性应**不过**。
- ⇒ 建议补 **DC-5（可感度两闸 + 持续/恒定分栏）**。

### GAP-2 清单未覆盖 **`dose=0 ⇒ 关且逐条等价（含 `state_hash`）** 与"每源独立开关"
DC-4 只核"propagate 总闸 + 不新增事件类型 + source 字段"，**漏**：`dose=0` 与"无日历"**逐条等价（含 `state_hash`）**、以及**每源独立开关**各自生效（关一个源仅该源参数消失）。⇒ 建议并入 DC-4 或补 DC-6。

> 说明：以上补漏**只增清单覆盖度**，不改设计语义；我的独立命令/原始输出（含反例）仍是过闸依据。

*（§6 补漏 — delivery-reviewer，前置阶段）*

---

## 7. 待验清单（DC-1…DC-5 ∪ 我的五项）—— 含 GAP 已吸收说明

> ⚠️ **纪律（保留进证据）**：清单**通过 ≠ 实现没问题**（清单也可漏）；**我自己的命令 + 原始输出（含反例/负例）才是过闸依据**。设计方清单是**自检**、可复用、**不得替代我的独立结论**。
> **更新**：设计方清单已升到 `5ea2b2c`，**我补的 GAP-1/GAP-2 已被吸收**：GAP-2 → **DC-4 增补**（`dose=0`/无日历逐条等价含 `state_hash` + 每源独立开关）；GAP-1 → **新增 DC-5**（可感度两闸 + 恒定偏移标注 + 双向证伪）。

| 我的项 | 设计方清单（`5ea2b2c`） | 合成后待验要点（命令级） |
|---|---|---|
| ① 窗口边界发一次 | **DC-3** | `source=="calendar"` 的事件条数 ≈ 窗口数 ≪ 84；**反例**：若 ≈ 回合数 ⇒ FAIL（脚本 Check1） |
| ② 退让不复活 | **DC-1** | 枚举 `slot→活动/place` 定义点 ⊆ 白名单、新增=0；`world_params` 不产 daypart 活动键；**反例**：同 slot 双套并存/双计数（脚本 Check2 + 手工调用图） |
| ③ jitter 确定性可重建 | **DC-2** | 同 seed 两跑逐条相等 / 换 seed 变 / `draw_u64(seed,"world_calendar",idx)` **离线重算**逐条相等；**装置：分进程**（脚本 Check3 + 分进程两跑） |
| ④ 三保底+剂量 | **DC-4** | `directed=false` 不传导；`dose=0` 与"无日历"**逐条等价含 `state_hash`**；**每源独立开关**各归零；**反例**：绕过 `propagate`/新增事件类型/缺 `source`（脚本 Check4） |
| ⑤ 可感度两闸 | **DC-5** | 闸 A（幅度 + **≥2/3 seed 同向** + **窗口内≥70% slot 非零偏置**）；闸 B（**R 未声明 ⇒ 降级闸A+首帧对比图，不许调美术替代门禁**）；**恒定偏移标 `mode="constant_offset"`**；**双向证伪**（日历-only 过 / RNG-only 不过）（脚本 Check5 + 对照跑） |

**DC 覆盖状态**：DC-1↔②、DC-2↔③、DC-3↔①、DC-4↔④、DC-5↔⑤ —— **五项一一对应，无无人看守的角落**。DC-5 的**执行**归我（T368），其"是否被实现歪掉/静默降级"由清单与本单**互补**核。

*（§7 待验清单 — delivery-reviewer，前置阶段）*
