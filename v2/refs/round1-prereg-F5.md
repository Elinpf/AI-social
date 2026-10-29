# round1 预登记口径卡 · F-5 作息强度（口径下沉：作息里有没有"闲"）

> 产出人：life-feature-dev（生活气息功能开发专家）｜任务：`round1-impl`
> 落盘时刻：见 §7 时间戳（本文件**先于任何代码改动**落盘，顺序由 §7 的时间戳与 commit 顺序双向自证）
> 冻结声明：本文件的 §3 指标公式、§4 阈值、§5 失败判据 **一经落盘即冻结**。此后**不得**按 ON 臂结果回头调参；确需改动必须在 §7 追加「改动理由 + 时间戳 + 改前/改后原文」，并声明该次改动是否在看到 ON 臂读数之后。

---

## 1. 维度：唯一一个 —— F-5 作息强度（本轮口径：作息里有没有"闲"）

**只做这一个维度，不做多维度大杂烩。**

### 1.1 为什么是 F-5，以及为什么口径必须"下沉"

| 事实 | 证据（只读复算，命令见 §2.3） |
|---|---|
| 官方 F-5（口径：同一 agent 在同一 `(slot, place)` 出现 ≥3 天）在既有批次上**已饱和** | `habit_strength = 16/16 = 1.000`，`max_repeat_days_mean = 7.0`（`run_d2_after_n16_seed42`，7 天）与 `5.0`（`run_d12c_off_n16r60_seed42`，5 天） |
| 饱和来源是 **night 全员同睡同地点**（每个 agent 每天 4 个 slot，night 100% 在 residence） | 逐 slot 复算：`night` 的 (place, activity_type) 众数占比 **= 1.000（16/16 agent）**；`morning/afternoon/evening` 分别为 0.525 / 0.513 / 0.637（n16r60 批） |
| 所以官方 F-5 在本规模上**没有可观测余量**（ceiling），任何改动都会落在 100%→100% ⇒ 该口径下结论只能写"不可判" | `reports/R4-life-texture.md:41-42,61,107`；`reports/R23-solitude-idle.md` 亦记 night 共睡占 S-2 的 56.60% |

**判断**：要交付"能算出数、且和谁比说得清"的东西，F-5 的口径必须下沉到**有 headroom 的那一半**——即「白天三个时段（morning/afternoon/evening）里，居民的作息有没有"过日子"的部分」。这也正是 R23 已登记的缺口：`leisure` 仅 23 实例 / 人均 1.44 次 / 5 天、独处主口径 8/320 = 2.50%。

> 口径下沉**不是**换维度：仍是 R4 §F-5「有没有固定作息 / 日子怎么过」，只是把已被夜间共睡顶满的那一段剔除，只看可变的白天段。

### 1.2 为什么可观测

- 数据源是**引擎已落盘的事件**，不需要新的日志字段：`ACTIVITY_STARTED` 的 `payload` 实测含 `agent_id / day / day_type / slot / slot_id / place / activity_type / template / participants`（抽样命令见 §2.3）。
- 指标全部是**计数除法**，无 LLM、无人工判定、无 judge ⇒ 可逐行复算。

### 1.3 为什么本轮做得完

- 改动面：`code/life/planner.py` 一处（新增一个 env 开关 + 一个有界选择分支）；**不动** `activity_templates.json`（它在 `engine/version.py::FINGERPRINT_FILES` 内，不动它 ⇒ OFF/ON 两臂 `engine_version` 指纹**完全一致**，单变量最干净）、不动 `engine/`、`orchestration/`、`config/`、不碰 LLM、不碰提示词。

---

## 2. 机制：一个有界的确定性改动（单 env 开关，默认关 = 逐字节等价）

### 2.1 开关

| 项 | 值 |
|---|---|
| env | `HITT_LIVING_SLOT` |
| 取值 | ∈ {`1`,`true`,`yes`,`on`} 为开；**未设/`0` 为关** |
| 关闭时行为 | 与 master `d2d1993` **逐字节等价**（同 seed 同输入 ⇒ 同 `run.jsonl`），可消融 |
| 开启时行为 | 见 §2.2 |

### 2.2 机制：每天轮转出 1 个"闲"时段，只在该时段优先排生活类模板

1. 由 `slot_id`（形如 `day{dow}-{slot}`）取 `dow`，**轮转**决定当天的"闲"时段：
   `living_slot(dow) = ("morning","afternoon","evening")[dow % 3]`。
2. 若当前 `slot` **等于**当天 `living_slot`：从**生活类候选集**（下表，全部是 `activity_templates.json` 里**既有**模板，不新增模板）中按既有 eligibility 流程（`slot_allowed` / 场所开放 / 现金前置 / 人数）筛选，命中则选取；**并跳过 1/3 频率门**（保证这天真有"闲"）；若无一可排，则**回落到与关闭时完全相同的原路径**。
3. 其余时段（含 night）走**与关闭时逐字相同**的原路径。

生活类候选集（`_LIVING_CANDIDATES`，slot → 模板）：

| slot | 候选模板 | 语义（生活气息） |
|---|---|---|
| morning | `combat_training` | 晨练（park，允许 1 人） |
| afternoon | `combat_training`, `ice_break`, `select_location` | 午后闲逛 / 街坊搭话 / 挑个去处 |
| evening | `contest`, `ice_break`, `creative_collab`, `rel_maintain` | 看/参加比赛、串门、一起做点东西、走亲戚 |

- 全部选取仍是 `sha256` 决定的确定性选择（沿用 `planner._pick`），不读墙钟、不引入新 RNG 状态 ⇒ replay 稳定。
- 上界：每天至多 1 个 slot 被改写 ⇒ 每 agent 每天活动数不变（仍 4 个），只改"这一天那一个小时干了什么"。

> **[AMENDMENT-1 · 2026-10-30 06:2x，在任何 ON 臂读数之前]**
> **改动**：闲时段由「按 `dow % 3` 在 morning/afternoon/evening 轮转」收窄为「**每天 `evening` + 周末 `afternoon`**」；
> evening 生活类候选确定为 `{contest×2(权重), gift, whisper, rel_maintain, ice_break, creative_collab, select_location}`。
> **理由（静态复算，非 ON 读数）**：按原轮转方案，5 天里 morning×2 + afternoon×2 会把 workday 的
> 生产性活动（`work/learn/trade`）替换掉；用既有日志 `run_d12c_off_n16r60_seed42` 复算，morning 生产性占比
> (24+20+7)/80 = 0.6375、afternoon (31+17+15+8)/80 = 0.8875，故预计 `G3` 从 0.3813 掉到约 0.22（**−15pp**），
> 必然击破本卡 §5 自设的 `G3 ≥ OFF−5pp` 守卫。收窄到 evening（既有 evening 生产性占比 = **0/80**）与
> 周末 afternoon（fallback 是 `socialize`，同样非生产性）⇒ **G3 不受本改动影响**，`G2` 仍守恒。
> **性质**：这是**在冻结前发现的自相矛盾修正**，发生在任何 ON 臂起跑之前（本批尚未起跑，无 ON 读数可依据）；
> **§3 公式、§4 样本量、§5 阈值一字未改**，只改 §2 机制的作用时段。若把此次改动当成"按结果调参"，则本卡作废重写。

### 2.3 本卡引用的只读复算命令（不产生新批）

```bash
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
# 事件字段与分布（只读既有日志）
python3 - <<'PY'
import json,collections
f=f"{__import__('os').environ.get('REPO','.')}/v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl"
c=collections.Counter()
for l in open(f):
    d=json.loads(l)
    if d.get('type')=='ACTIVITY_STARTED':
        p=d['payload']; c[(p['slot'],p.get('template'),p['activity_type'])]+=1
for k,v in c.most_common(): print(v,k)
PY
```

---

## 3. 指标公式（数据来源：`run.jsonl` 的 `ACTIVITY_STARTED` 事件；分子/分母写死）

设一次运行的事件集 `A = {ACTIVITY_STARTED}`，`agents = #{p.agent_id}`，`days = #{p.day}`。
生活类模板集合 `LIVING = {combat_training, contest, ice_break, select_location, creative_collab, rel_maintain}`。
"有人陪"`MULTI` = `len(p.participants) > 1`。

| 编号 | 指标 | 公式 | 口径备注 |
|---|---|---|---|
| **M1 主** | 生活类活动人均日频 | `#{p ∈ A: p.template ∈ LIVING} / (agents × days)`；`LIVING` = 6 个既有但改动前 evening 不常出现的模板（见 AMENDMENT-2） | 单位：次/（人·天）。**与 OFF 臂同参数比** |
| **M1' 载体** | 生活类候选池人均日频 | `#{p ∈ A: p.template ∈ LIVING_POOL} / (agents × days)` | **不参与 PASS**，只为排除"挑口径"质疑 |
| **M2 主** | 休闲（leisure）人均 5 天频 | `#{p ∈ A: p.activity_type == "leisure"} / (agents × days) × 5` | **对齐 R23/R4 口径**（R23: 1.44 次/人/5 天），用于与既有报告对表 |
| **M3 辅** | 闲时段命中率 | `#{(agent, day): 该 (agent,day) 的 `evening` 上出现 template ∈ **LIVING_POOL**} / (agents × days)` | 直接测机制是否真落地（机制面）；AMENDMENT-2 把主体改为候选池、AMENDMENT-1 把时段定为 evening |
| **M4 辅** | 白天作息稳定性 | 对每个 `(agent, slot∈{morning,afternoon,evening})`：`众数(place,activity_type) 的天数 / 该 slot 观测天数`，再对全部 (agent,slot) 取均值 | 官方 F-5 的"白天段"版本（剔除 night 共睡），**仅作描述/对照**，不作为本轮 PASS 依据 |
| **G1 守卫** | 活动多样性 | 每个 agent 的 `distinct (slot, place, activity_type)` 三元组数，取**全 agent 均值** | 防止"把日子压成一种" |
| **G2 守卫** | 活动总量守恒 | `#A` 必须 `== agents × days × 4` | planner 改动不得减少活动 |
| **G3 守卫** | 生产性活动占比 | `#{p: p.activity_type ∈ {work, learn, trade}} / #A` | 不能把白天过成纯玩 |
| **G4 守卫** | 模板命中率 | `#{p: p.template 非空} / #A` | 与 OFF 持平即可，不许因本改动掉下去 |

所有指标由同一个零依赖、只读工具出数：`tools/habit/habit_readings.py`（`--run OFF=<dir> --run ON=<dir> --out-json <f>`），输出含分子/分母/公式/sha256/复算命令六元组，实现与本文公式**逐条对应**（工具内 `SPEC` 常量写死公式，报告与工具不一致即视为缺陷）。

---

## 4. 样本量与运行参数

| 项 | 值 | 理由 |
|---|---|---|
| agents | 16 | 与 `run_d12c_*` / `run_f6_*` / A0 系列同规格，可与既有读数对表 |
| rounds | 60 | `12 回合/天` ⇒ **5 天**（`day0..day4`），覆盖 `living_slot` 轮转 3 档各 ≥1 次，且与 R23 的"5 天"口径一致 |
| seed | 42 | 仓库既有主力 seed |
| 两臂 | **同 worktree、同 `code_sha`**：OFF = 不设 `HITT_LIVING_SLOT`；ON = `HITT_LIVING_SLOT=1` | 单变量；`activity_templates.json` 未改 ⇒ `engine_version` 指纹两臂**相同** |
| 串行 | 必须串行（`tools/d5/preflight.sh` 并发闸）；起跑前 `pgrep` 复核 | 团队硬纪律 |
| 规模下限 | 分母 `agents × days = 80`（≥30，满足 R4 §0「分母 <30 只报事件数」门槛） | M1/M2/M3 均为 per-(agent·day) 口径 |

---

## 5. 判据（PASS / FAIL / 不可判）

**PASS（全部同时成立）**

1. `M1_ON ≥ M1_OFF + 0.50`（次/人·天）；且
2. `M2_ON ≥ 1.5 × M2_OFF`（休闲频次相对提升 ≥50%）；且
3. `M3_ON ≥ 0.60`（超过 60% 的 (agent,day) 在轮转闲时段真的排上了生活类活动）；且
4. 守卫全过：`G1_ON ≥ 0.95 × G1_OFF` **且** `G2_ON == 16×5×4 = 320` **且** `G3_ON ≥ G3_OFF − 0.05` **且** `G4_ON ≥ G4_OFF − 0.02`。

**FAIL（任一成立即 FAIL，不得只报"部分有效"混过去）**

- `M1` 提升 `< +0.50` 但 `≥ +0.10` ⇒ 记「部分有效（未达阈值）」，同时按 R4 纪律报暴露面；
- `M1` 提升 `< +0.10` ⇒ 记「机制未生效」；
- 任一守卫破（G1 掉 >5%、G2 不守恒、G3 掉 >5pp、G4 掉 >2pp）⇒ 记「**不构成净改善**」（先例：R11 的 L-7 击穿）；
- 开关无法从运行件证明（两臂 `code_sha` 不同 / `switch_proof.txt` 缺失 / 起跑 env 未记录）⇒ 记「**不可判**」，不得报 PASS。

**不可判的其它情形**：批未跑完（`rc≠0` / `meta.json` 空 / `[d2] self-check` 两数不等）；日志缺 `template` 字段（版本不符）。

> **纪律**：机制接通 ≠ 效果改善；`不可判` ≠ `无效` ≠ `效应存在`（R21/R22）。结论必须绑定 `code_sha`。

---

## 6. 不做什么（划界，避免大杂烩）

- 不新增/不修改 `activity_templates.json` 的任何模板或字段（保 `engine_version` 指纹两臂一致）。
- 不改 `engine/`、`orchestration/`、`config/`、任何提示词、任何 LLM 调用。
- 不改 night 时段的作息（全员同睡是既有事实，不在本轮）。
- 不以人工/judge 指标作为 PASS 依据（本轮全部指标机械可算）。

---

## 7. 冻结与时间戳

| 事件 | 时刻（+08:00） | 证据 |
|---|---|---|
| 基线复算（只读既有日志，选定口径） | 2026-10-30 06:03–06:05 | 本文件 §1.1 表；命令 §2.3 |
| **本口径卡落盘（公式/阈值冻结）** | **2026-10-30 06:06:22** | `stat -c '%y' team-workspace/round1-prereg-F5.md` → `2026-10-30 06:06:22.420910224 +0800` |
| 代码改动（`code/life/planner.py`） | **晚于**上一行 | commit 顺序 + `git log --format=%ci` |
| ON 臂起跑 | 由 evidence-runner 执行 | `<arm>/meta.json::started_at` |

**改动记录**：此后如必须改 §2/§3/§4/§5，须在下方追加行，并明确写"是否在看到 ON 臂读数之后"。

| # | 改动 | 理由 | 时间戳 | 是否在 ON 臂读数之后 |
|---|---|---|---|---|
| 1 | §2.2 闲时段：`dow%3` 轮转 morning/afternoon/evening → 固定 `evening` + 周末 `afternoon`；evening 候选权重写死（`contest`×2） | 静态复算显示原方案会把 workday 生产性活动替换掉、预计 `G3` −15pp 必破自设守卫；阈值一字未改 | 2026-10-30 06:0x（落盘见 `stat`） | **否**（本批尚未起跑，无 ON 读数） |
| 2 | §3 口径澄清：`M3 闲时段命中率` 的主体定义为**机制候选池** `LIVING_POOL`（= contest/gift/whisper/rel_maintain/ice_break/creative_collab/select_location/combat_training），并新增**载体口径 `M1'`**（同一池，只读并列报出、**不参与 PASS 判定**）；`M1/M2/G1..G4` 公式与全部阈值**一字未改** | 定稿 §3 原把 `M3` 写成"template ∈ LIVING"，而 `LIVING` 只含 6 个非既有模板（不含 gift/whisper），与 §2.2 的机制候选池不一致 ⇒ 机制明明命中也会被判未命中。属**定义自洽性修正**，且发生在任何真/假 ON 臂读数之前 | 2026-10-30 06:1x（`stat` 见下） | **否**（只有 mock 机制自检，且未见任何真实 ON 臂结果） |
| 3 | **AMENDMENT-3（3 处判据与 r48 不相容）**：①§5 G2 期望值 `16×5×4 = 320` → `16 × days × 4`（r48 下 days=4 ⇒ 256）；②§3 M2 的 ×5 外推加注（与 R23「5 天实测」**非同口径**，只作量级对表；PASS 用比值、单调缩放不影响）；③§5 M3 由单条 `≥0.60` 改为**双条件** `M3_ON ≥ 0.60` **且** `M3_ON ≥ M3_OFF + 0.05`；④新增 G2 语义预置澄清（总量不得减少；ON 少 ≤2 条且能给出 `_act` 同地同活动去重佐证 ⇒ 判「守恒成立（去重副作用）」并披露差额）。`M1`/`G1`/`G3`/`G4` 及其阈值**一字未改** | 原卡按 `rounds=60`（5 天）书写判据；实际参数锁定 `r48`（4 天），G2 期望值算式与天数不符、M2 外部对表口径不同、M3 单条下限在 OFF 自身已达 0.65625 时**恒真无判别力**。属**参数相容性修正**，且发生在任何 ON 臂读数之前 | 2026-10-30 06:19（`stat` 见 §7 末行） | **否**（ON 批尚未起跑；`M3_OFF` 取自 repo-analyst 在 `d2d1993` 的 **OFF 基线**读数，非 ON 读数） |

---

## 附录 A · OFF 参考基线（只读既有批次复算，**不是**本轮的 OFF 臂）

> 用途：让 §4/§5 的阈值在起跑前就有"和谁比"的锚。**限定**：该批为 master 时代的 `run_d12c_off_n16r60_seed42`
> （`code_sha` 非本轮分支；`n16×r60`），只作参考，**不得**替代本轮同树 OFF 臂；本轮结论一律以两臂同 `code_sha` 的读数为准。
> 复算命令（仓库根，只读，零跑批、零 LLM）：
> ```bash
> python3 tools/habit/habit_readings.py \
>   --run REF=v2/evidence/run_d12c_off_n16r60_seed42 --out-json /tmp/habit_ref.json
> ```

| 指标 | 读数 | 分子/分母 |
|---|---|---|
| M1 生活类活动人均日频 | **0.4000** | 32 / 80（agents×days） |
| M2 休闲人均 5 天频 | **1.4375** | 23 / 80 → ×5（**与 R23 的 1.44 逐位对齐**，口径互证成立） |
| M3 闲时段命中率 | **0.1375** | 11 / 80 |
| M4 白天作息稳定性 | **0.5583** | 48 个 (agent,slot) 的众数占比均值 |
| G1 活动多样性 | **9.6875** | 全 agent 的 distinct(slot,place,activity_type) 均值 |
| G2 活动总量 | **320** | = 16×5×4（守恒） |
| G3 生产性活动占比 | **0.3813** | 122 / 320 |
| G4 模板命中率 | **0.4906** | 157 / 320 |

附带事实（用于 §5 守卫的可行性判断）：该批 evening 的 `activity_type` 全为 `socialize`（生产性 **0/80**），
故 AMENDMENT-1 把闲时段收窄到 evening 不会动 `G3`。

---

## AMENDMENT-3 · 修三处与 r48 参数不相容的判据（**ON 批起跑前**）

> **落盘时刻**：2026-10-30 06:19（+08:00，`stat -c '%y'` 见 §7 末行）
> **生效声明**：本 AMENDMENT-3 落盘时，**OFF 臂与 ON 臂均尚未起跑**（`round1-run` 被本任务阻塞），
> 以下四条修改**发生在任何 ON 读数之前**；`M3_OFF` 用的是 repo-analyst 在 `d2d1993` 上的 **OFF 基线**读数
> （r48/mock，见附录 B），不是 ON 读数。除本节列出的三处判据 + 一处语义澄清外，
> **`M1` / `G1` / `G3` / `G4` 的公式与阈值一字未改**。

### A3-1 `G2` 期望值：按实际天数计算（原文 `16×5×4` 与 r48 不相容）

- **改前（§5 第 4 条原文）**：
  > `G2_ON == 16×5×4 = 320`
- **改后（生效文本）**：
  > `G2_ON == 16 × days × 4`，其中 `days = #{p.day}` 取自本次 `run.jsonl` 的 `ACTIVITY_STARTED`；
  > r48 参数下 `days = 4` ⇒ 期望值 **256**（与附录 B 的 OFF 实测一致）。工具 `tools/habit/habit_readings.py`
  > 已按 `agents × days × 4` 动态给 `expected_agents_days_x4`，**无需改代码**。
- **理由**：`rounds=48`、12 回合/天 ⇒ **4 天**；`16×5×4 = 320` 是 `rounds=60`（5 天）的算式。原写法会让 ON 臂被判"不守恒"，纯属参数不相容，与行为无关。

### A3-2 `M2` 的 ×5 外推：只作量级对表（PASS 判据不受影响）

- **改前（§3 表格 M2 行备注原文）**：
  > **对齐 R23/R4 口径**（R23: 1.44 次/人/5 天），用于与既有报告对表
- **改后（生效文本）**：
  > `M2 = #{activity_type=="leisure"} / (agents × days) × 5`，即**把 4 天实测速率线性外推到"5 天"**；
  > 与 R23「5 天**实测** 1.44」**非同口径**，**只能作量级对表**，不得写作"与 R23 同口径实测"。
  > **但 `M2` 的 PASS 判据是比值**（`M2_ON ≥ 1.5 × M2_OFF`），×5 是分子分母**同乘的单调缩放**，不影响比值 ⇒ **PASS 判定不受本外推影响**。
- **理由**：`rounds=48` 只有 4 天。原文把"对齐 R23 口径"写成实测对表，容易让读者把外推值当实测值引用。

### A3-3 `M3`：单条下限**恒真无判别力** ⇒ 改为双条件

- **改前（§5 第 3 条原文）**：
  > 3. `M3_ON ≥ 0.60`（超过 60% 的 (agent,day) 在轮转闲时段真的排上了生活类活动）；且
- **改后（生效文本）**：
  > 3. `M3` **双条件同时满足**：**①下限护栏** `M3_ON ≥ 0.60`（防退化）；**②判别力条件** `M3_ON ≥ M3_OFF + 0.05`。
- **理由（事实）**：OFF 自身已达标——r48 `M3_OFF = 0.65625 (42/64)`、r60 `M3_OFF = 0.6500`，故单条 `≥0.60` 对 OFF 也成立 ⇒ **恒真、无判别力**。
  `+0.05` 是**最小可判别阈值（minimum detectable difference），不是效应量预期**，不得读成"预期只涨 5pp"；也**不引入** `0.90` 之类新的绝对阈值（无先验依据，且等同按干跑结果反推阈值）。
- **边界**：`M3` 是**辅指标（机制面）**，它只回答"闲时段是否真排上了生活类活动"，**不回答质量**；若 A3-3 ①成立但 ②不成立 ⇒ 记「机制已落地，但相对基线无可判别增量」。

### A3-4 `G2` 语义预置澄清（**起跑前**写定，不得看到读数后再定）

- **生效文本**：
  > `G2` 的语义 = 「**活动总量不得减少**」。判法：
  > ① `G2_ON == 16 × days × 4` ⇒ 守恒成立；
  > ② 若 `G2_ON < 16 × days × 4` 且差额 **≤ 2 条**，**并且**能给出 `code/life/agent.py::_act` 的
  >    「同地 + 同 `activity_type` 进行中 ⇒ 不发起 MOVE」去重计数佐证（证明是**去重抑制**而非 planner 未排 slot）
  >    ⇒ 判「**守恒成立（去重副作用）**」，并**如实披露差额与佐证**；
  > ③ 差额无法归因于该去重门（或缺佐证） ⇒ **守卫击破**，按 §5 记「不构成净改善」。
- **理由**：`ACTIVITY_STARTED` 随 MOVE 到达由内核发出；`_act` 的去重门可能让"与当下同地同活动"的计划不发事件 ⇒ 严格等式的失败可能**不是** planner 丢 slot。此条**必须在起跑前写定**，否则就成了看到读数后放宽判据。
- **谁判**：②的归因由 leader 裁决，不由实现者（我）自行认定；我负责提供只读取证（缺失 `(agent, day, slot)` 清单 + `PLACE_MOVE` 对照）。

---

## 附录 B · OFF 参考基线（r48 / mock / `d2d1993`，**由 repo-analyst 实测，非本轮 OFF 臂**）

> 来源：repo-analyst 在 `d2d1993`、`--mock`、`seed=42`、`agents=16`、`rounds=48` 的实测读数（`days=4`，`run.jsonl` sha256 = `97b8f624…`）。
> 用途：① 给 A3-1 的 `days=4 ⇒ 256` 与 A3-3 的 `M3_OFF` 提供依据；② 作本卡 §5 阈值的"和谁比"锚。
> **限定**：它不是本轮 OFF 臂（本轮 OFF 臂必须与本轮 ON 臂**同 `code_sha`**，见 §5「两臂 `code_sha` 不同 ⇒ 不可判」）。

| 指标 | 读数 | 分子/分母 |
|---|---|---|
| M1 生活类活动人均日频 | 0.421875 | 27 / 64 |
| M1'（载体口径，不参与 PASS） | 0.921875 | 59 / 64 |
| M2 休闲人均 5 天频（4 天速率外推） | 1.328125 | 17 / 64 × 5 |
| M3 闲时段命中率 | 0.65625 | 42 / 64 |
| M4 白天作息稳定性 | 0.578125 | — |
| G1 活动多样性 | 8.875 | 全 agent 均值 |
| G2 活动总量 | 256 | = 16 × 4 × 4 ✓ |
| G3 生产性活动占比 | 0.382812 | 98 / 256 |
| G4 模板命中率 | 0.492188 | 126 / 256 |
