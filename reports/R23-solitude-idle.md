# R23 · 独处 / 空闲：把 CYCLE-16 的「无判据读数」补成三个可复算尺子

> **一句话结论**：本批 5 天 16 人里，独处只占 **2.5%**（8/320）且**全部为独自值守工作**（8/8 `activity_type=work`），`leisure` 仅 **23 实例**（人均 **1.4 次 / 5 天**）——小镇几乎没有「闲」这一面。
> 该结论绑定 **分析基准 HEAD `6fdcf93` / 臂 `code_sha f2bf606` / 输入日志 `run_sha256 1fbb9ef5`** 三者；**单 seed（42）、单规模（n16×5 天×1 模拟周）⇒ 只作点估计，不可外推**。
> 本报告**不跑批、不调 LLM、不改代码**（`code/` 零变更）；全部数字来自一份既有日志的确定性只读复算。

## 页首：基准、身份与输入

| 项 | 实测值 | 取得方式 |
|---|---|---|
| 分析基准 HEAD | `6fdcf9309dcde981f322bb026061ffe230133846`（`6fdcf93`） | `git rev-parse HEAD`，rc=0 |
| 臂代码身份 `code_sha` | `f2bf606bf5f6c362a7d4d34b9177f3210d43aabf`（`f2bf606`） | 日志 `meta.json.code_sha`（跑批记录值） |
| **`code_sha` 与 HEAD 的关系** | **`f2bf606` 是 `6fdcf93` 的祖先**（`git merge-base --is-ancestor f2bf606 HEAD` rc=0；`f2bf606` 提交时间 `2026-10-24 14:58:18`，标题 `review(d27): 实现与接线前两项验收通过…`） | 见附录 A `A-0` |
| 工作树指纹（写作时点） | `942f50b8e2de7068b474eb324b26aa981c9a7390eb430b33bb29d6e126dc702b` | `git status --porcelain \| sha256sum`（24 项 = 1 `M` + 23 `??`，含本轮新增 `tools/solitude/`、`v2/evidence/solitude_shots/`） |
| 输入日志 | `v2/evidence/run_d27_C_n16r60_seed42/run.jsonl` | 唯一数据源 |
| 输入日志 `run_sha256` | `1fbb9ef5161fd07aa68fcc9fc4038f104ff18b56383a2fc6b31bb3cb5486a188` → **sha8 `1fbb9ef5`** | 实算 sha256 与 `meta.run_sha256` 逐位相同（附录 A `A-1`） |
| 输入 `meta.json` | sha256 `e73acb4683fbafd322b0406e59f825ed5a6f8298db104f8333e4dcf431fcb793` | `sha256sum`，rc=0 |
| 出数器 | `tools/solitude/solitude_metrics.py`，sha256 `ca8feb1888671fafe4e4fbcf4003f54d5ed56eff22198d3f8fa88ad31a97cbc2` | 与读数 JSON `input.generator_sha256` 逐位相同 |
| 读数文件 | 团队工作区 `solitude/round1-readings.json`，sha256 `667757dd7eb4faae4636324ca0ce1c582a1bd171f4cdd9a528fd35dc59053dfb` | 本地重跑 sha256 **逐位一致**（附录 A `A-2`） |
| 口径卡（预登记） | 团队工作区 `solitude/round1-prereg.md`（先写口径、后出读数） | 本报告 §1 逐条照抄 |

> ⚠️ **`code_sha` 的读法（先钉死，避免误读）**：`f2bf606` 是**本批日志跑那个版本的代码身份**，不是分析基准 HEAD；两者相差若干提交（`f2bf606` 为 `6fdcf93` 的祖先）。因此**不得**把本报告读数写成「`6fdcf93` 上的结果」，只能写「`run_d27_C_n16r60_seed42`（`code_sha f2bf606`）这一批的结果，分析时点 HEAD 为 `6fdcf93`」。
> ⚠️ **工作树指纹的口径**：它是**写作时点**的值（此时 `reports/R23-solitude-idle.md` 尚未入库），入库后必然改变；复算时请按附录 A `A-0b` 的同一命令重算，并把自己时点的值与上表**并列登记**，不要用上表的值反推「报告成稿时树是干净的」。

## 0. 本报告是什么、不是什么

- **是什么**：把 `reports/README.md` 中登记的「**独处 / 空闲**在 `CYCLE-16` 只立尺子、未立 F/L 编号、无闸线 ⇒ 描述性读数」这一档，**补成「有预登记口径卡 + 有机制闸 + 有确定性出数器 + 可逐字节复算」的三个尺子**（S-1 独处占比 / S-2 同场共处 / S-3 空闲→社交关系）。
- **不是什么**：① 不是新提示词实验（本轮**未跑批、未改 `code/`**，因此不存在「改前/改后」对照）；② **不新增、不顶替任何判据编号**（沿用 CYCLE-16 的裁决：不发明 `F-9` 一类编号）；③ 不是「生活气息改善」的证据——本报告**没有任何效果提升项**，`新增达标效果项 = 0`；④ 「独处质量」（独处时在做什么、感受如何）**不可判**，理由见 §3.2。
- **与 CYCLE-16 的关系**：CYCLE-16 给的独处读数是 `0/320`（**结构下限**，因为 `planner` 每 slot 必发 `ACTIVITY_STARTED`）。本报告用更严的口径（叠加「未卷入 MSG」+「未与他人同处」）重算，得到 **8/320**——两者**不是矛盾**，是**分母口径不同**：CYCLE-16 量的是「无活动 slot」，本报告量的是「有活动但独处」。引用时不得互代。

## 1. 口径卡与预登记判据（照抄 r2 口径，**未事后放宽**）

### 1.1 统计单位与分母（先钉死）

| 代号 | 单位 | 分母 | 说明 |
|---|---|---|---|
| **U细胞**（S-1 单位） | 居民 × slot-cell = `(day, slot, agent)` | **320** = 5 天 × 4 slot × 16 人 | 分母**恒为 320**，不随日志覆盖变化；某细胞无事件视为「无证据」，**不得从分母剔除** |
| **P对细胞**（S-2 单位） | 居民对 × slot-cell = `C(16,2)=120` 对 × 20 | **2400** | 同上 |
| **A实例**（S-3 单位） | `ACTIVITY_STARTED` 实例 | 按 `activity_type` 过滤 | 一个 slot 内同一居民至多 1 条（`activity_id` 形如 `ACT-P001-day0-morning`，320 细胞 320 条，一一对应） |

### 1.2 三个尺子的定义（原文照抄）

- **S-1 独处占比**：分子 = U细胞中同时满足 (i) 该居民该 slot 内**既非 `MSG_DM.from/to`、也不在 `MSG_PUBLIC.participants` 内**；(ii) 该 slot 内**未与他人同处**的细胞数。其中「同处」取**三个并列口径（必须全给、不二选一）**：
  - `place`（**主口径**）：同 `(day, slot)` 下与该居民**重建地点相同**的其他居民 ≥1 人；
  - `joint`（保守副口径）：该居民 `ACTIVITY_STARTED.participants` 长度 >1（显式联合活动）；
  - `participants_roster`（敏感性副口径）：MSG 一律按 `participants` 名单判卷入（把「同场旁听」也算作不独处）。
- **S-2 同场共处**：P对细胞中，同 `(day, slot)` 下两居民重建地点相同的对数量之和；**先做可重建性评估，不合格就写「不可重建」**。
- **S-3 空闲→社交**：主口径 = **槽级状态归因**——分子 = 发起人当 slot 的 `activity_type == leisure` 的 `MSG_DM` 条数；分母 = `leisure` 实例数。并列输出两个弱化口径（`S3a` 实例中含 DM 的占比、`S3b` 每实例 DM 比率）。

### 1.3 在场重建规则（S-1(ii) 与 S-2 共用，唯一实现）

1. 每个 `(day, slot, agent)` 取 `ACTIVITY_STARTED.place` 为重建地点（唯一条）；
2. 用 `PLACE_ARRIVED.place` 做一致性校验；
3. `PLACE_MOVE.from_place → to_place`、`travel_ticks` 记录「到达前窗口」（`travel_ticks=1` / slot 长 12 tick，**有界误差，不插值、不估算**）；
4. 无 `ACTIVITY_STARTED` 的细胞视为「无地点读数」、不参与同场判定（本批实测 **0 个**）。

### 1.4 机制闸 M1–M5（预登记，全部通过才允许把读数写进结论）

| 闸 | 判据 | 不通过时 |
|---|---|---|
| M1 日志完整性 | 行数 == `meta.events`(116308)；`meta.degraded_calls == 0`；实算 sha256 == `meta.run_sha256` | 读数不可用 |
| M2 单元覆盖 | `ACTIVITY_STARTED` 覆盖 320/320 U细胞（100%） | S-1/S-2 判「不可算」 |
| M3 地点覆盖 | `ACTIVITY_STARTED.place` 非空 320/320 且 `PLACE_ARRIVED.place` 一致率 100% | S-2 判「不可重建」 |
| M4 身份一致 | `AGENT_BORN` 恰 16 人且 `P001–P016`；day×slot = 5×4；总 round 60 | 单位定义失效，停 |
| M5 零外推 | 全部数字仅来自 `--log` 单一文件与其 sha256；无 mock/插值/估算 | 读数作废 |

### 1.5 效果判据 E（单 seed 最保守）

- **E0 硬约束**：只写点估计；**不写统计学强断言类措辞（本项目二字禁忌词按字面执行）、不写置信区间、不做跨批比较**。
- 描述性分档（**仅给措辞，不作增益/退化判定**）：S-1 place 主口径 `<5%`→「几乎无独处」/`5–20%`→「独处为少数时段」/`>20%`→「独处常态」；S-2 `<20%`→「同场共处稀疏」/`20–60%`→「同场共处中度」/`>60%`→「高密度同场」；**S-3 不设阈值**（分母 23 太小，任何阈值都是伪精度）。
- 判定规则（§7）：M1–M5 全通过 + S-1/S-2 分母 100% 覆盖 + 诊断 (b)（日志空洞）占比 <5% ⇒ 该尺子**能判（点估计级）**；否则**只能描述**。日志无「独处时在做什么/感受如何」的语义字段 ⇒ **「独处质量」一律不可判**。

## 2. 读数（每个尺子：分子 / 分母 / 统计单位 / 字段来源 / 原始文件）

> 全部数字出自 `round1-readings.json`（sha256 `667757dd…`），由图 `run.jsonl`（`1fbb9ef5`）复算，复算命令见附录 A。

### 2.1 S-1 独处占比（**三口径并列，不二选一**）

| 口径 | 分子 | 分母 | 占比 | 统计单位 | 字段来源 |
|---|---|---|---|---|---|
| **主口径 `place`** | **8** | 320 | **2.50%** | 居民 × slot-cell | `MSG_DM.from/to`、`MSG_PUBLIC.participants`、`ACTIVITY_STARTED.place/participants` |
| 保守副口径 `joint` | 24 | 320 | 7.50% | 居民 × slot-cell | `ACTIVITY_STARTED.participants`（长度 >1 判同处） |
| 敏感性口径 `participants_roster` | 5 | 320 | 1.5625%（写作 1.56%） | 居民 × slot-cell | `MSG_DM.participants`（把 8 人场面名单里的旁听者也算不独处） |

- **主口径 8 条分子明细（逐条，来自 `numerator_detail`）**：`activity_type` **8/8 全为 `work`**；agent 分布 `P005×2`、`P006/P007/P008/P011/P012/P015×1`；day 分布 `day0:2 / day1:1 / day2:1 / day3:1 / day4:3`；place 分布 `school 2 / clinic 2 / market 1 / kitchen 1 / town_hall 1 / farm 1`。
  - **口径含义（必须写清）**：「真独处」在本批**只发生在「独自值守岗位」**的场景（`work` × 单人 `participants`），**没有一条**是 `leisure` 或 `rest` 类独处。这不是价值判断，只是分子构成的事实。
- **三口径差额的来源（已登记）**：`participants_roster` 比主口径少 3 条，对应 **53 条 `MSG_DM` 的 `participants` 是 8 人场面名单、而 `from/to` 只有 2 人**——旁听者是否算「没独处」属口径选择，故并列报出；主口径仍按口径卡只取 `from/to`。

### 2.2 S-2 同场共处（**含可重建性评估 + 伪影单列**）

| 项 | 值 |
|---|---|
| 分子 / 分母 | **1060 / 2400 = 44.1667%**（写作 44.17%） |
| 统计单位 | 居民对 × slot-cell（`C(16,2)=120` 对 × 20 slot-cell） |
| 字段来源 | `ACTIVITY_STARTED.place`、`PLACE_ARRIVED.place`、`PLACE_MOVE.from_place/to_place` |
| 可重建性 `reconstructable` | **true**（`place_coverage=1.0`、`arrived_match_rate=1.0`、`cells_with_multiple_move_targets=0`） |
| 可重建性 caveat | ① **无 `PLACE_LEAVE`/离开事件** ⇒ slot 内 presence 只能按「到达后驻留至 slot 末」处理，属**上界假设**；② `travel_ticks=1` / slot 长 12 tick ⇒ 到达前仍在上一个地点，误差窗口**有界但不可消除**；③ `MSG.place` 与参与人活动地点可不同（DM 可远距）⇒ 同场判定**只用 `ACTIVITY_STARTED.place`** |

**⚠️ 结构性伪影（必须单列，禁止把 S-2 读成「社交密度」）**

| 块 | 对数 | 占分子 | 性质 |
|---|---|---|---|
| `residence \| night` | **600** | **56.60%** | 全体居民夜间都记在同一个 `residence`：`C(16,2)=120` 对 × 5 天 = 600 对，本质是「**睡觉同屋**」，不是互动 |
| 其余地点合计（非 `residence`） | 460 | 43.40% | 见下分布 |

- **地点粒度 caveat**：日志只有 **15 个粗粒度地点标签**（`bank/cafe/clinic/community_center/farm/kitchen/library/market/office/park/plaza/residence/school/town_hall/workshop`）⇒ **S-2 只能读成「同地点共处的上界」**，不能读成互动强度。
- **非 residence 的 pair 分布（前几名）**：`cafe 251`、`market 53`、`park 45`、`bank 28`、`plaza 23`、`farm 23`、`library 12`、`school 10`、`community_center 7`、`workshop 5`、`kitchen 1`、`office 1`、`town_hall 1`、`clinic 0`。
- **按 `place|slot` 的 top6**：`residence|night 600`、`cafe|evening 246`、`market|afternoon 52`、`park|morning 44`、`bank|afternoon 28`、`plaza|evening 22`。
- **派生附注（未预登记口径，仅作量级参考、不作判定）**：若把夜槽整格剔除，可用对数 `1060 − 600 = 460`、对应分母 `120 × 15 = 1800`，算术比为 `25.56%`。**该式不是预登记口径**（口径卡分母恒为 2400），**不得替代表内 44.17%，不得据此改判**，登记在此只为让读者看清「剔除结构性同处后还剩多少」。

### 2.3 S-3 空闲→社交（**是比率，不是转化率**）

| 项 | 值 | 说明 |
|---|---|---|
| 主口径 | **46 / 23 = 2.00** | **「每条 `leisure` 实例对应 2 条 `MSG_DM`」的比率**，**不是转化率**；分母 23 极小 |
| 统计单位 | `ACTIVITY_STARTED` 实例（`activity_type ∈ {leisure, idle}`） | `idle` 为空集（实测无该取值） |
| 字段来源 | `MSG_DM.from/day/slot`、`MSG_DM.ctx.trigger`、`ACTIVITY_STARTED.activity_type` | — |
| `S3a`（实例中含 DM 的占比） | **23 / 23 = 100%** | 归因只能写「**槽级状态共存**」，不写因果 |
| `S3b`（每实例 DM 数） | 46 / 23 = 2.00 | 与主口径同分子分母，此处显式标为「比率」而非「占比」 |

**四处口径风险（预登记，逐条标注）**：
1. `activity_type` 实测 7 类 `socialize 89 / rest 80 / work 55 / trade 40 / learn 27 / leisure 23 / civic 6`（合计 320），**无 `idle`** ⇒ 该类只能取 `leisure`，**不合并、不臆造**；
2. `MSG_DM.ctx.trigger` 实测枚举 `reply 341 / combat_training 32 / scarce_buy 18 / whisper 17 / gift 15 / counter_propose 9 / polite_reject 8 / rel_maintain 8 / mentorship 7`——**没有 leisure/idle 归因通道 ⇒ trigger 不能用于归因**；
3. `activity` 是 **slot 级状态**，msg 精确时刻未知 ⇒ 这是「leisure **槽内**发起」而非「leisure **瞬间**发起」；
4. 分母 **23** 个实例，单 seed **只可给点估计**，**不设通过/不通过阈值**；按报告族纪律第 4 条（分母 <30 只报事件数），本尺子的比率**标 `probe`**，不得读成「总体转化率」。

### 2.4 机制闸实测（M1–M5 全通过）

| 闸 | 实测 | 结果 |
|---|---|---|
| M1 | 行数 `116308` == `meta.events`；`degraded_calls=0`；实算 sha256 == `meta.run_sha256` | **PASS** |
| M2 | `activity_started_cells=320` / 期望 320，覆盖率 `1.0` | **PASS** |
| M3 | `place_coverage=1.0`（320/320 非空）；`PLACE_ARRIVED` vs `ACTIVITY_STARTED` 地点一致 `299/299=1.0`；多地点细胞 0 | **PASS** |
| M4 | `n_agents=16`（`P001–P016`）、`days=5`、`slots=4`（`n_slot_cells=20`）、`rounds_seen 0…59`（总 60） | **PASS** |
| M5 | 单源文件 + 单 sha256；`interpolation_used=false`、`mock_or_imputed_values=0` | **PASS** |

## 3. 裁决

### 3.1 机制闸栏（**只证「能算」，不证「效果」**）

| 项 | 结论 |
|---|---|
| M1–M5 | **全通过**（见 §2.4）⇒ 三个尺子的读数**可用** |
| 出数器确定性 | **可复算**：本地重跑读数 sha256 `667757dd…` 与 r2 交付件**逐位一致**（附录 A `A-2`） |
| 在场重建 | S-2 **可重建**（`reconstructable=true`），但带「无离开事件 ⇒ 驻留至 slot 末」的**上界假设** |
| 边界（必须同时写） | 机制闸通过**只是「读者可以引用这些数字」的准入**，**不等于**「小镇更有人味」「独处更少」一类效果改善 |

### 3.2 效果判据栏（单 seed、单规模）

| 尺子 | 裁决 | 依据 |
|---|---|---|
| **S-1 独处占比** | **能判（点估计级）**：主口径 `2.50%`（8/320），落 `<5%` 档 ⇒ 措辞「**几乎无独处**」；副口径并列 `7.50%` / `1.56%`。**不可外推** | `verdict_rule_applied.S1_can_judge=true`（M1–M5 通过 + 分母 100% 覆盖 + 诊断(b)=0% <5%） |
| **S-2 同场共处** | **能判（点估计级）**：`44.17%`（1060/2400）落 `20–60%` 档 ⇒ 措辞「**同场共处中度**」；但**必须与「56.60% 来自 `residence\|night` 结构性同处」并列**，且只作「同地点共处**上界**」读。**不可外推** | `S2_can_judge=true` |
| **S-3 空闲→社交** | **只可描述，未立判定**：`46/23 = 2.00` 是比率、分母 23 且归因只到 slot 级、trigger 无通道 | `S3_can_judge=false`（`S3_reason`：分母极小 + trigger 无归因通道 + activity 为 slot 级） |
| **「独处质量」（独处时在做什么/感受如何）** | **不可判**：日志**无该语义字段**（`activity_type` 仅 7 类、`leisure` 仅 23 实例） | `solitude_quality_can_judge=false` |
| **本轮新增达标效果项** | **0 / 0**（本周期跑批 0、判读独立臂 0） | 无对照臂 ⇒ 不存在「改前/改后」 |

> 措辞纪律（三条同时生效）：① 效果栏**只能**写点估计 + 「不可外推」；② **不得**把机制读数（M1–M5 通过、S-2 可重建）写成效果改善；③ **不得**出现统计学强断言类措辞及其同义替换（二字禁忌词按字面执行；单 seed 无采样分布）。

## 4. 诊断：独处 vs 日志空洞，以及独处的时段结构

### 4.1 「独处」与「日志空洞」的拆分（互斥、穷尽）

| 定义 | 单位 | 实测 |
|---|---|---|
| (a) `evidence`：该细胞存在 `ACTIVITY_STARTED` 或 `OBSERVATION(observer)` 或 `NEED_UPDATE(agent_id)` 任一 | U细胞 | **320**（100%） |
| (b) `hole`：上述事件一个都没有（该居民该 slot 在日志里完全无痕） | U细胞 | **0**（`b_hole_share = 0.0`） |
| **S-1 主口径分子里的空洞数** | 条 | **0**（`b_hole_in_S1_numerator_place=0`）；`joint` 口径同样 0 |

⇒ **本批不存在「slot 级日志空洞」**，S-1 的 8 条独处**全部有行为/状态证据**，不是「没记到」造成的假独处。

### 4.2 二级细化：`ACTIVITY_STARTED` 是机制骨架，故加做 round 级空洞检查

- 单位 = `(day, slot, agent, round)` = 320 × 3 = **960** 子细胞；「该轮内该居民零 agent 归因事件」= **1**（`1/960 = 0.1042%`）。
- 唯一一条：`P005 / day2 / afternoon / round29`（该居民在这一轮里没有任何 agent 归因事件；但同 slot 仍有 `ACTIVITY_STARTED` 骨架，故它**不构成 slot 级空洞**）。
- **每细胞事件密度**：`OBSERVATION` 每细胞 `min 10 / p25 49 / 中位 79 / p75 107 / max 238`；`NEED_UPDATE` 每细胞 `min 3 / p25 5 / 中位 6 / p75 8 / max 12`；两者 `cells_with_zero = 0`。
- **诚实性说明**：「有骨架 ≠ 有内容」——`ACTIVITY_STARTED` 由调度器每 slot 必发（口径卡 §0 已登记），所以 (a) 类 320 里**必然**包含骨架成分；本节用 round 级 + 密度分布给出「内容侧」旁证，但**不宣称**「每格都有真实行为内容」。

### 4.3 独处时段的 `(slot, place, activity_type)` 分布要点（主口径 8 条）

| 维度 | 分布 | 要点 |
|---|---|---|
| `slot` | `afternoon 6` / `morning 2`；`evening 0` / `night 0` | 独处**只出现在白天两个槽**；夜间全员 `residence` 同睡（`rest`），在本口径下**不构成独处**（也不构成互动，见 §2.2 伪影） |
| `activity_type` | `work 8`（100%） | **独处 == 独自值守**，没有「一个人闲着」的病例 |
| `place` | `school 2` / `clinic 2` / `market 1` / `kitchen 1` / `town_hall 1` / `farm 1` | 岗位即地点；`cafe`/`park`/`plaza` 这些**社交场所 0 条独处** |
| `agent` | 7 人各 1 条 + `P005` 2 条（day1/day2 均 `afternoon` `clinic`） | 独处不是个别居民的特质，而是**岗位排班**的结果（`P005` 连续两天下午独守 `clinic`） |
| `day` | `day0 2 / day1 1 / day2 1 / day3 1 / day4 3` | 无单调趋势可读（分母太小），**不解读为「越往后越孤独」** |

### 4.4 与「闲」有关的旁证

- `leisure` 实例仅 **23**（占 320 的 7.19%），人均 **23/16 = 1.44 次 / 5 天**；`rest` **80**（其中夜间 80 条全部落在 `residence|night`）。
- 也就是说：**本批居民的时间主要花在 `socialize 89 + rest 80 + work 55`（合计 224/320 = 70.0%）**，「闲」（`leisure 23`）是最小的一类之一（仅高于 `civic 6`）。
- **该段为描述性事实，不构成「生活不真实」的判断**——是否「应该有更多闲」需要另立判据与对照臂，本报告不主张。

## 5. 真实截图（同批、可追溯、不进判据）

- **跑前进程检查**：`ps -eo pid,args | grep -F "tools/d2/run_batch.sh" | grep -v grep | grep -v "ps -eo"` → **无输出，rc=1**（即无跑批进程）；`orchestrat|run.jsonl.*--rounds` 同样 rc=1。见附录 A `A-6`。
- **渲染命令（原样，未改脚本）**：
  ```bash
  cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
  python3 tools/metrics/render_shots.py --run-dir v2/evidence/run_d27_C_n16r60_seed42 --batch-id d27_C --outdir v2/evidence/solitude_shots/ --views chat,rhythm
  ```
  `--views` 的可选值经 `--help` 核实为 `chat / rhythm`（**脚本未改**）。
- **结果**：`ok_count=2 / fail_count=0 / blank_retries=0/2`（`blank_cumulative=16/320` 为 T282 观察哨留痕，仅作记录）。

| 视图 | 文件 | sha256 | 字节 | 像素自检 |
|---|---|---|---|---|
| `chat` | `v2/evidence/solitude_shots/d27_C-chat-1fbb9ef5.png` | `b5ef4bebf55c7aabfa1461b81b99e5afdcb6b6399e1b69cb6349b86d3d14b20c` | 279,235 | `distinct_colors=23980`、`top_color_frac=0.1417`、`non_bg_frac=0.582` → **OK**（`1400×900`） |
| `rhythm` | `v2/evidence/solitude_shots/d27_C-rhythm-1fbb9ef5.png` | `ae945dbf6fbfcb7851558ce028dcf616b47e66fe202587ad814bf36897202c07` | 282,423 | 见 `render_report` 同结构记录 → **OK**（`1400×900`） |

- **`render_report.json`**：`v2/evidence/solitude_shots/render_report_d27_C.json`，sha256 `d7ed539d18f3c2d217d3b86d64db7e555555c4d5e4f32ce37edae5401e0e207d`；`log_sha256 = 1fbb9ef5…`（与输入日志逐位相同）、`run_sha256_in_threads` 同值。
- **派生件 `threads_d27_C.json`**：sha256 `7db1f75eaba74cc23dc8899f8f3b2ea1d4473b203e2ec079825816a57869fe8e`（2,153,042 B）；独立重跑 `gen_threads.py` 到 `/tmp` 得到**同一 sha256**（rc=0，附录 A `A-5`）⇒ 两张 PNG 的线程集**可被独立复现**。
- **纪律**：文件名带日志 sha8（`1fbb9ef5`）；**非拼图、非跨批混拼、无旧图**；按报告族通用纪律第 3 条，截图**不进任何判据**，仅作展示材料。

## 6. 下一轮建议（指向一件具体可做的事）

**建议：给 `evening` 槽补一个「非工作、非睡眠、可独处的低强度活动」的行为空缺，并把「独处占比」的分子构成（`activity_type` 分布）作为**唯一**预登记观测项；不要动 `work` 与 `night` 两段。**

理由（全部落在本报告读数上）：
1. 独处 **8/8 都是 `work`**，且 **`evening` 槽独处 0 条**、`leisure` 仅 **23** 实例 ⇒ 「一个人待着但不干活」这一情形在本批**结构性缺席**；
2. `evening` 的高频落点是 `cafe`（`cafe|evening` 有 **246 对**共处）⇒ 该槽是「社交已经发生」的地方，补「独处型 evening 活动」**不会**把小镇推向更冷清，但能产出「闲」这一面的行为证据；
3. 判据形状建议（下一轮预登记再定稿）：只看 **`leisure` 实例数是否从 23 上升** + **`evening` 独处分子是否 >0**，**不设「提升 X%」的阈值**（分母太小，阈值即伪精度）；仍为单 seed、点估计、不外推。

**明确不建议**：① 用 S-2 的 44.17% 去调社交密度（其中 56.60% 是睡觉同屋伪影）；② 用 S-3 的 `2.00` 当「转化率」去调提示词（无 trigger 通道，归因只到 slot 级）。

## 7. 未找到 / 不确定（如实登记）

| # | 项 | 状态 | 影响 |
|---|---|---|---|
| U-1 | 日志中**没有**「独处时在做什么/感受如何」的语义字段 | **未找到** | 「独处质量」**不可判**，本报告只给频次 |
| U-2 | `activity_type` **无 `idle`** 取值；`MSG_DM.ctx.trigger` **无** leisure/idle 通道 | **未找到** | S-3 只能槽级归因，**不写转化率** |
| U-3 | **无 `PLACE_LEAVE`/离开事件** | **未找到** | S-2 的 slot 内 presence 只能是「驻留至 slot 末」的**上界假设**，实际同处时长**不可得** |
| U-4 | 地点只有 **15 个粗粒度标签** | 不确定（口径限制） | S-2 不能读成互动强度/社交密度 |
| U-5 | 跨 slot 移动耗时 `travel_ticks=1`，到达前归属上一地点 | 有界误差、**不可消除** | 每细胞至多 1/12 slot 的归属误差，未插值 |
| U-6 | `P005 / day2 / afternoon / round29` 的零事件原因 | **不确定**（齐全性无解释字段） | 只登记事件，不推断动机 |
| U-7 | 单 seed（42）、单规模（n16×5 天×1 模拟周） | 结构限制 | **全部数字不可外推**；无对照臂 ⇒ 无效果结论 |
| U-8 | 「独立值守岗位算不算独处」的**价值含义** | **未立判定**（口径卡 `P3`） | 本报告不作任何价值判断；`work` 单人是否「更有人味」不在判据内 |
| U-9 | 团队工作区口径卡与读数件**不在本仓库**（在 `team-workspace/solitude/`） | 位置登记 | 读者按 §页首 sha256 + 附录 A 复算命令可独立重建读数（出数器在仓库内 `tools/solitude/`） |

## 附录 A：可复算命令清单（逐条附**实测**退出码）

> 工作目录统一为 `cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment`（下文记作 `$ROOT`）。`rc` 为本次实测退出码，**未实跑的条目已明确标注**。

| # | 命令 | 实测 rc / 输出摘要 |
|---|---|---|
| **A-0** | `git rev-parse HEAD` | `rc=0` → `6fdcf9309dcde981f322bb026061ffe230133846` |
| **A-0a** | `git merge-base --is-ancestor f2bf606 HEAD; echo $?` | `rc=0` ✅ ⇒ **`code_sha` 是 HEAD 的祖先**（日志来自稍早代码版本） |
| **A-0b** | `git status --porcelain \| sha256sum` | `rc=0` → `942f50b8e2de7068b474eb324b26aa981c9a7390eb430b33bb29d6e126dc702b`（24 项；**写作时点**值，入库后必变） |
| **A-1** | `sha256sum v2/evidence/run_d27_C_n16r60_seed42/run.jsonl` | `rc=0` → `1fbb9ef5…6a188`，与 `meta.run_sha256` **逐位相同** |
| **A-1b** | `sha256sum v2/evidence/run_d27_C_n16r60_seed42/meta.json tools/solitude/solitude_metrics.py` | `rc=0` → `e73acb46…` / `ca8feb18…` |
| **A-2** | `python3 tools/solitude/solitude_metrics.py --log v2/evidence/run_d27_C_n16r60_seed42/run.jsonl --meta v2/evidence/run_d27_C_n16r60_seed42/meta.json --out /tmp/r23_recompute.json` | `rc=0`；输出 sha256 `667757dd7eb4faae4636324ca0ce1c582a1bd171f4cdd9a528fd35dc59053dfb` = r2 交付件 sha256（**逐位一致 ⇒ 确定性复算成立**） |
| **A-2b** | `sha256sum /root/.jiuwenswarm/.agent_teams/jiuwen_team_cron___1a16d5a5932_be95193b74e5/team-workspace/solitude/round1-readings.json` | `rc=0` → `667757dd…`（同 A-2 产物） |
| **A-3** | 派生聚合（由读数 JSON 算术汇总 §4.3 分布，不重算原始日志）：`python3 -c "import json,collections;d=json.load(open('<团队工作区>/solitude/round1-readings.json'));s=d['S1_solitude_share']['numerator_detail'];print(len(s),dict(collections.Counter(x['slot'] for x in s)),dict(collections.Counter(x['place'] for x in s)),dict(collections.Counter(x['activity_type'] for x in s)))"` | `rc=0` → `8 {'morning': 2, 'afternoon': 6} {'market': 1, 'school': 2, 'clinic': 2, 'kitchen': 1, 'town_hall': 1, 'farm': 1} {'work': 8}` |
| **A-4** | `python3 tools/metrics/render_shots.py --run-dir v2/evidence/run_d27_C_n16r60_seed42 --batch-id d27_C --outdir v2/evidence/solitude_shots/ --views chat,rhythm` | `rc=0`；`ok_count=2 / fail_count=0`；两张 PNG 的 sha256 见 §5 |
| **A-5** | `/opt/openjiuwen/workswarm-venv/bin/python3 code/frontend/tools/gen_threads.py --log v2/evidence/run_d27_C_n16r60_seed42/run.jsonl --meta v2/evidence/run_d27_C_n16r60_seed42/meta.json --out /tmp/threads_check_d27_C.json --label d27_C` | `rc=0`；输出 `events=116308 messages=510 threads=169 multi_turn=88 ge3=77`；sha256 `7db1f75e…`，与入库 `threads_d27_C.json` **逐位一致**（把 `--out` 换回 `v2/evidence/solitude_shots/threads_d27_C.json` 即为原样调用） |
| **A-5b** | `sha256sum v2/evidence/solitude_shots/render_report_d27_C.json v2/evidence/solitude_shots/threads_d27_C.json v2/evidence/solitude_shots/*.png` | `rc=0` → `d7ed539d…` / `7db1f75e…` / `b5ef4beb…` / `ae945dbf…` |
| **A-6** | `ps -eo pid,args \| grep -F "tools/d2/run_batch.sh" \| grep -v grep \| grep -v "ps -eo"; echo $?` | `rc=1`（**无输出** ⇒ 跑批前确认无跑批进程）；另 `orchestrat\|run.jsonl.*--rounds` 亦 `rc=1` |
| **A-7** | `python3 tools/metrics/render_shots.py --help \| head -40` | `rc=0`；核实 `--views` 可选值为 `chat / rhythm`（**未改脚本**） |

## 附录 B：引用对照表（分子 / 分母 / 单位 / 字段 / 来源文件 + sha8）

| # | 读数 | 分子 | 分母 | 统计单位 | 字段来源 | 来源文件 + sha8 |
|---|---|---|---|---|---|---|
| B-1 | S-1 主口径独处占比 `2.50%` | 8 | 320 | 居民 × slot-cell | `MSG_DM.from/to`、`MSG_PUBLIC.participants`、`ACTIVITY_STARTED.place/participants` | `run.jsonl`（`1fbb9ef5`）；读数 `round1-readings.json`（`667757dd`） |
| B-2 | S-1 副口径 `joint` `7.50%` | 24 | 320 | 居民 × slot-cell | `ACTIVITY_STARTED.participants` | 同上 |
| B-3 | S-1 敏感性口径 `participants_roster` `1.5625%` | 5 | 320 | 居民 × slot-cell | `MSG_DM.participants`（含 53 条 8 人场面名单） | 同上 |
| B-4 | S-2 同场共处 `44.1667%` | 1060 | 2400 | 居民对 × slot-cell | `ACTIVITY_STARTED.place`、`PLACE_ARRIVED.place`、`PLACE_MOVE.*` | 同上 |
| B-5 | S-2 伪影块 `residence\|night` | 600 | 1060（占分子） | 居民对实例 | `ACTIVITY_STARTED.place` + slot | 同上 |
| B-6 | S-2 非 residence 对数 | 460 | 1060（占分子） | 居民对实例 | 同上 | 同上 |
| B-7 | S-3 主口径比率 `2.00` | 46 | 23 | `ACTIVITY_STARTED` 实例（`leisure`） | `MSG_DM.from/day/slot`、`ACTIVITY_STARTED.activity_type` | 同上（`probe`） |
| B-8 | S-3a 实例含 DM 占比 `100%` | 23 | 23 | `leisure` 实例 | 同上 | 同上 |
| B-9 | `activity_type` 枚举 | `socialize 89 / rest 80 / work 55 / trade 40 / learn 27 / leisure 23 / civic 6` | 320 | `ACTIVITY_STARTED` 实例 | `ACTIVITY_STARTED.activity_type` | 同上 |
| B-10 | 诊断 (b) 日志空洞 | 0 | 320 | 居民 × slot-cell | `ACTIVITY_STARTED` / `OBSERVATION` / `NEED_UPDATE` | 同上 |
| B-11 | round 级零事件子细胞 | 1 | 960 | 居民 × slot-cell × round | agent 归因事件 | 同上 |
| B-12 | 机制闸 M1 行数 / degraded | 116308 行（== `meta.events`）/ `degraded_calls=0` | — | 日志行 | `meta.json` | `meta.json`（`e73acb46`） |
| B-13 | 截图 `chat` | — | — | 页面 | `ACTIVITY`/MSG 线程集 | `d27_C-chat-1fbb9ef5.png`（`b5ef4beb`） |
| B-14 | 截图 `rhythm` | — | — | 页面 | `PLACE_MOVE`/节律 | `d27_C-rhythm-1fbb9ef5.png`（`ae945dbf`） |
| B-15 | 线程派生件 | — | — | 线程集 | `run.jsonl` + `meta.json` | `threads_d27_C.json`（`7db1f75e`），`render_report_d27_C.json`（`d7ed539d`） |

---

**署名**：AI 小镇 · 对话体验与研究发布小队（JiuwenSwarm 多智能体团队）. 2026-10-24. *R23 · 独处/空闲*。
**口径出处**：`team-workspace/solitude/round1-prereg.md`（预登记，先写口径后出读数）；**出数器**：`tools/solitude/solitude_metrics.py`（`ca8feb18`）。
**本轮未做**：未跑批、未调 LLM、未改 `code/`、未新增/顶替判据编号。
