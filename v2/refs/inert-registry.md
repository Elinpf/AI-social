# T226 · inert registry —— 「它到底有没有活」（登记 ≠ 生效）

> 领域：交付质量 / 一致性核对 ｜ 维护：sim-engine-stats-architect ｜ 状态：v1（首批 7 条）
> 目的：**一表回答「一个已登记的东西到底有没有活」**。因为 — **在文件里，"存在"与"生效"长得一模一样**。

> ## ⚠️ 性质与盲区（先读）
> **① 这是一道棘轮，不是一张表。** 核对器（`tools/check_inert_registry.py`）自己扫 `code/` 判定状态；**未接线必须显式声明**（`tools/inert_registry.json` 的 `expected_status`），**接线之后必须同步更新该声明**。
> → **它造成的"红"不是 bug，而是"有人改了接线状态但没更新声明"。** 已接入 `make gate` / CI（`make inert-gate`）。
> **② 它有盲区，且盲区写在明处**：静态扫描的「已接线」**只保证有生产侧调用点，不保证运行时真产生**。→ **重大条目必须叠加一次实跑日志核对**（`grep '"type": "XXX"' <LOG>`，静态+运行双证据）。**不要因为"有了核对器"就以为万事大吉。**

---

## 0. 为什么要有这张表（问题家族）

今晚反复出现同一陷阱的**三种形态**，本质相同：**登记了 ≠ 生效了**。

| 形态 | 实例 | 「存在」的表象 | 「生效」的真相 |
|---|---|---|---|
| 登记维 | `mentor_relation` | `config/activity_templates.json`、`life/constants.py`、`08` 都声明了 | **life 从未发射过它**（无调用点） |
| 登记事件 | `SLEEP_*`/`MEMORY_*`/`PERSONA_DRIFT`（T224） | `08 §1.2 S` 已登记 | 未登记 `EVENT_TYPES`、未接线 → **不可落账** |
| 同名死桩 | `run_gates` 68 行同名桩 | 文件里有 | **不被执行** |

> **与 T218 反例库互相引用**：「清单改了、执行体没改」与本表是**同一家族**——**声明的图景 ≠ 运行的图景**。

---

## 1. 方法论（机器可校验，本表不手工维护）

**本表由脚本生成/校验，不靠人维护**（对齐 Leader 硬要求②）：

- **核对器**：`tools/check_inert_registry.py`（无第三方依赖、确定性）
- **数据源**：`tools/inert_registry.json`（只声明**被测对象 + 登记位置 + 期望状态**；**状态由脚本实扫 `code/` 判定**）
- **判定信号**：
  - `registered` = 事件名在 `engine/events.py::EVENT_TYPES`
  - `folds` = 名在 `engine/replay.py`（折叠器登记）
  - `produced` = 名出现在**生产侧** `code/{life,engine,orchestration}`（**obs/freeze/frontend 只是消费/白名单，不算接线**）
- **状态**：
  | 状态 | 含义 |
  |---|---|
  | `已接线` | event：registered ∧ folds ∧ produced；dim/snapshot：生产侧有**声明文件之外**的使用 |
  | `未接线(产事件未注册)` | 有生产侧"产事件"，但**未登记 `EVENT_TYPES`**（不可落账） |
  | `未接线(仅声明)` | 只有声明，无生产侧使用 |
  | `死代码` | 声明 + 从不被引用（当前首批无此例） |
- **运行**：
  ```bash
  make inert-gate                                  # 已接入 make gate / CI（棘轮）
  python3 tools/check_inert_registry.py            # 三段表（A 手工棘轮 / B 事件自动 / C 开关自动）+ 退出码
  python3 tools/check_inert_registry.py --json     # 机器可读
  python3 tools/check_inert_registry.py --no-auto  # 只看手工棘轮条目
  ```
  已接入 **`make gate`**（`gate: stamp lexicon-gate inert-gate code-test plugin-test`）；**登记表与代码不一致即失败**（棘轮退出码 1）。

> **两条硬要求的落实**：① 每条"未接线"都附**可执行验证命令**（见下表「如何验证」列，逐条 `grep`）；② **能机器判定的都写成脚本**（`check_inert_registry.py`），表由它校验。

---

## 2. 首批登记表（T226 第一批；状态由脚本判定，快照于 2026-10-12）

| # | 名称 | 类型 | 登记位置 | 接入状态 | 如何验证（可执行） | 负责方 | 到期条件 |
|---|---|---|---|---|---|---|---|
| 1 | `mentor_relation` | judgment_dim | templates / `life/constants.py` / `08` | **未接线(仅声明)** | `grep -rn 'mentor_relation' code/life code/engine code/orchestration --include=*.py \| grep -vE 'tests/\|scripts/'` → 仅 `constants.py` 声明 | life-layer-dev / persona | 质变时经 IF-2b 提交 `LLM_JUDGMENT(dimension=mentor_relation)` |
| 2 | `SLEEP_STARTED` | event | `08 §1.2 S` | **未接线(仅声明)** | `grep -n 'SLEEP_STARTED' code/engine/events.py code/engine/replay.py` → 空；`grep -rn` 生产侧 → 空 | persona(T224)/kernel | 注册 `EVENT_TYPES`+`apply_event` + 接线落账 |
| 3 | `SLEEP_COMPLETED` | event | `08 §1.2 S` | **未接线(仅声明)** | 同 #2 | persona(T224)/kernel | 同 #2 |
| 4 | `MEMORY_CONSOLIDATE` | event | `life/sleep_window.py` + `08 §1.2 S` | **未接线(产事件未注册)** | `grep -n 'MEMORY_CONSOLIDATE' code/engine/events.py` → 空；生产侧命中 `life/sleep_window.py` | persona(T224)/kernel | 注册 + 接线（`sleep_window` 已产"待发事件"） |
| 5 | `MEMORY_FORGET` | event | `life/sleep_window.py` + `08 §1.2 S` | **未接线(产事件未注册)** | 同 #4 | persona(T224)/kernel | 同 #4 |
| 6 | `PERSONA_DRIFT` | event | `life/sleep_window.py` + `08 §1.2 S` | **未接线(产事件未注册)** | 同 #4 | persona(T224)/kernel | 同 #4 |
| 7 | `PERSONA_FINGERPRINT` | snapshot（非事件） | `08 §1.2 S`（快照） | **未接线(仅声明)** | `grep -rn 'PERSONA_FINGERPRINT' code/ --include=*.py \| grep -vE 'tests/\|scripts/'` → 空 | persona(T224) | 产出快照入 `metrics`/侧存储 |

> **结论（首批）**：**7 条全部"未接线"**，其中 3 条（`MEMORY_CONSOLIDATE`/`MEMORY_FORGET`/`PERSONA_DRIFT`）已"有生产侧产事件但未注册"，属**半接线**——**一旦 persona 完成 `EVENT_TYPES` 注册 + 落账接线，脚本会自动判为「已接线」**，本表随之更新。
> **凡"已核实活着"的条目**：脚本判为 `已接线` 并给出 `hits`（真实调用点）——**该结论同样记录在案**（首批无）。

---

## 2.1 自动枚举（扩展覆盖：**全部 `EVENT_TYPES` 事件** / **config 开关**）

> 手工条目（§2）只覆盖"已知疑似"。为落实"能机器判定的不靠人维护"，核对器**同时自动枚举**：

**[B] 全部 `engine/events.py::EVENT_TYPES` 事件**（当前 **85** 个）——逐条判"有没有**生产侧发射点**"（**排除 `events.py`/`replay.py` 自身的登记**，否则"登记"会被误当"发射"）：
- **未接线（已注册·无生产侧发射点）9 个**：`ACTIVITY_INTERRUPTED`、`GOAL_ABANDON`、`GROUP_JOINED`、`GROUP_LEFT`、`LOAN_REPAY`、`MONEY_BURNED`、`OFFER_EXPIRED`、`SCHEDULE_REVISED`、`VOTE_CAST`。
  → 含义："schema 里有、`EVENT_TYPES` 里有，但**当前没有任何生产侧代码会发射它**"（**收口/接线时须留意**；也可能属"接口预留"）。
- 其余 ~76 个判为"已接线(有发射点)" —— **均标【未验证】**（静态扫描不保证运行时真产生）。

**[C] 全部 `code/config/policy.json` 的 `*.enabled` 开关**（当前 **6**）：`economy / lifecycle / social / production / exchange / llm_budget` —— 全判"已接线(疑似)"。**近似判定【未验证】**：判据是"生产侧代码是否出现该 section 名且含 `enabled`"；**开关类必须叠加一次"开/关实跑"核对**（开关"看起来存在但没接上"是最危险的一类）。

> **棘轮边界**：**[A] 手工条目**含 `expected_status`，**不一致 → 退出码 1**（参与 CI）；**[B]/[C] 自动枚举**为**报告**，不参与退出码（避免因"接口预留"类条目造成噪声红）。要"锁定"某自动条目，把它提升为 [A] 手工条目并声明 `expected_status`。

---

## 3. 如何新增一条（供团队自服务）

在 `tools/inert_registry.json` 的 `entries` 追加一项：
```jsonc
{
  "name": "XXX",                       // 被测对象标识
  "kind": "event|judgment_dim|snapshot|hook",
  "declared_in": ["path/to/declaration"],  // 声明出处（不含即视为"处处使用"）
  "expected_status": "未接线",           // 期望（棘轮：不符 → 脚本退出 1）
  "owner": "谁接线", "due_condition": "什么条件算接线完成"
}
```
然后 `python3 tools/check_inert_registry.py` 校验；表可贴脚本输出。

---

## 4. 局限与二次验证（诚实标注）

- **静态扫描**：`已接线` 只保证"代码里有生产侧调用点"，**不保证运行时真的产生该事件**。**重大条目建议叠加一次实跑日志核对**（`grep '"type": "XXX"' <LOG>`）——静态+运行双证据。
- **`obs` 白名单不算接线**：`obs/params.py`/`admission.py` 列名属**消费/准入**，本脚本已把其排除出"生产侧"（否则 `mentor_relation` 会被误判为已接线）。
- **未经实跑验证的"已接线"** 一律标【未验证】。

---

*（T226 inert registry v1 — 表由 `tools/check_inert_registry.py` 校验；「登记 ≠ 生效」，与 T218 反例库互为引用。）*
