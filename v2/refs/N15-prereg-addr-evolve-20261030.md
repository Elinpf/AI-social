# N-15 预登记 · 称呼演化臂（`LIFE_PROMPT_ADDR_EVOLVE`）—— OFF/ON 同 `code_sha` 双臂 + 摆动口径

> **立此存照**：本文件写于 **2026-10-30 22:0x +0800，开关尚未实现（`grep -rn ADDR_EVOLVE code/ tools/` 命中 0 行）、N-15 未起任何跑批、未见任何 ON 臂读数之前**。
> 判据、阈值、护栏、降级措辞、不可判条件**先写死**；§14 Amendments 只允许追加「跑前修订」，且每条必须写明「是否已见任一臂读数」。
> **本轮只交付文档**：不改 `code/`（冻结区）、不跑批、不调 LLM、不 commit。
> 作者：prereg-author（实验预登记与可行性核查专家）。基线：`feat/round-D10-address-drift` @ `2ad74a56c7d8570bfd10d7b55e55ce40ecc8bac6`。

| 项 | 值 |
|---|---|
| 计划项 | **`N-15`**（来源：`reports/CYCLE-34-20261030.md` §5.1 第 2 行，反推自 `F-73`/`F-74`、D10 §9） |
| 环境开关 | **`LIFE_PROMPT_ADDR_EVOLVE`**（默认 **OFF**；缺省/空/非法值 ⇒ OFF） |
| 被测维度 | **C-A 称呼与关系演化**（沿用 `reports/D10-address-drift-20261030.md` 的维度编号，**不新造编号**） |
| 主判据 | **`addr_swing_pairs_rate`（S-1）**——有向对层级的「称呼摆动对率」，定义见 §3.1（**出数前冻结**） |
| 尺子 | 词表 `v2/refs/address-ordinal.yaml`（sha256 `dc4ce327…22d95`，与 D10 §3.1 逐字符一致）+ 只读聚合件 `tools/metrics/addr_swing.py`（**待新增，须出数前冻结 sha**） |
| 双臂 | `n16 r84 seed42`，同 `code_sha`，OFF / ON 各一臂，冷缓存、串行 |
| 仓库根 | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment` |
| 本文件位置 | 仓内唯一一份 `v2/refs/N15-prereg-addr-evolve-20261030.md`（不建第二份，避免漂移） |
| 当前状态 | **预登记（未实现、未起跑、未 commit）** |

---

## 0. 判据写在出数之前的三条自证

1. **物理上不可能有 ON 臂读数**：`grep -rn "ADDR_EVOLVE" code/ tools/` → 退出码 `1`（零命中）。开关字符串在仓里一次都没出现过 ⇒ 任何 ON 臂都不可能已经跑过。
2. **作者在写判据前跑过一次「分母探针」，须诚实披露**：为回答「`n16 r84` 能不能把 `switch` 分母抬到 ≥30」（这是 N-15 的**验收前提**），作者对**既有** `run_d1_f6on_seed42_n16r84/run.jsonl`（`code_sha e8a9fd5e…`，**无任何称呼干预**）跑了一次只读尺子探针，输出写在 `/tmp`，未落仓。该探针只给出**分母与基线水平**，**不含任何 ON 臂信息**。命令与结果见 §11.3。
3. **本轮未做**：未跑批、未调 LLM、未改 `code/`、未改 `tools/`、未 commit、未新增 `v2/evidence/` 任何文件、未改任何既有 refs。

---

## 1. 一句话假设（可被指标反驳）

> **H1**：若在对话提示词里**只加一行**「跟一个人处得越熟，叫法就该跟着变一变——熟了以后别再一直用最初那个称呼」，那么同一有向关系（甲→乙）在同一线程内**称呼发生摆动的对**的比例（`S-1`）会相对 OFF 臂上升。
> 读者读到的差别是：从前**一句「石叔」叫到第七轮**（D10 实测：`n16r84` 基线 50 个可判有向对里 **50 个全平**），现在会看到**「石叔」→「老石」→ 又回「石叔」**这类有来有回的称呼位移。

> **H0**：称呼只由人格模板 + 称呼词表决定，与相处轮次/关系值无关 ⇒ 有向对里**几乎没有摆动**，`S-1(ON) − S-1(OFF) ≈ 0`。

**反驳方式（写死）**：
- `S-1` 的 `Δ = 100×(ON − OFF)` **未达 §5.2 可检出线**（`+20pp`）⇒ 判 `未达标`（`Δ ≤ 0`）或 `不可判（功效不足）`（`0 < Δ < +20pp`），**不得**写成「称呼变好/变坏」；
- `S-1` 上升但 `G1`（`L-7` 8-gram 重复率）击穿 ⇒ 判 **`无效（套话）`**——称呼来回很可能是模板轮换的副产品（这正是 D10 §6 陷阱2、`d9s-on L-7=74.87%` 的教训）；
- `S-1` 上升但 `G2`（叫错人）击穿 ⇒ 判 **`无效（叫错人）`**——「换叫法」变成「叫成自己/第三者」不是演化，是错称。

**写作纪律（硬）**：本维度禁写 `更有生活气息` / `更自然` / `更像过日子` / `改善` / `提升` / `显著`。只允许判定词：
**`有效` / `无效（套话）` / `无效（叫错人）` / `未达标` / `不可判（功效不足）` / `不可判（分母不足）` / `不可判（接线不受控）` / `机制未生效` / `批次无效（缓存回放）` / `批次无效（非单变量）`**。

---

## 2. 为什么是这一维（缺口是上游报告自述的，不是本轮新提的）

| 缺口 | 上游原文（可原位重放） | 对 N-15 的约束 |
|---|---|---|
| **`F-73` 无干预臂** | D10 §7：「本轮没有『称呼干预臂』，所以不存在能归因的因果结论」；CYCLE-34 §③ `F-73`：「`LIFE_PROMPT_ADDR_EVOLVE` 未实现 ⇒ 无可归因对象」 | 必须先实现开关，且**默认 OFF 与现状逐字节等价**（§8） |
| **`F-74` 分母不足** | D10 §5.1：`switch` 分母 11–22、`stage` 16–20、`vocab` 19，**全部 <30** | 规模必须抬到 `n16 r84`；分母仍 <30 ⇒ 按 §6 判 `不可判（分母不足）` |
| **单调口径会漏摆动** | D10 §9 建议④：「出数前把 `addr_stage_ordinal` 的单调口径**换成摆动计数**（本轮已证明单调口径会漏）」 | 主判据必须是摆动口径（§3.1），`stage` 单调口径降为**次级登记**、不作判据 |
| **两臂缓存回放率不同 ⇒ 差值连「同样条件下的差」都不算** | D10 §7.1 + §9④：`d9m-off 100.0%` vs `d9m-on 98.1%`；CYCLE-34 §③ `X-1` 第②③条 | 两臂必须**冷缓存**、`purpose=dialogue` 真调用率必须 **100%**（§7.4、`G6`） |
| **模板红旗必须并列** | `R4-life-texture.md` §3.2 陷阱2；D10 §6；CYCLE-34 §5.1 `N-15` 条目验收语 | `L-7` 8-gram 重复率**必须同屏并列**，且是护栏（§5.2 `G1`），不是装饰 |
| **官方口径对拍** | D10 §9 建议②、CYCLE-34 §5.1 `N-17` | `addr_error_rate` 必须与官方 `L-10 self_address_error` **并列同屏**（§5.2 `G2`） |

---

## 3. 判据 = 尺子（**出数前写死；改定义就是改判据**）

### 3.1 主判据 `addr_swing_pairs_rate`（`S-1`）

| 项 | 定义（**写死，跑后不得改**） |
|---|---|
| 统计单位 | **有向说话对 × 线程**（`speaker → addressee`，同一 `thread_id` 内），**仅 `MSG_DM`**（与现有 `addr_stage_ordinal` 同源同纳入条件，便于分母对齐） |
| 可判条件（分母） | 该有向对在该线程内识别出 **≥2 次可判指向**的称呼（指向分类 `target_ok` 才计入；`self_name`/`other_named`/`unknown_target` **不计入摆动分子**，只进 `G2`） |
| 分子 | 上述有向对中，**至少出现 1 次**「相邻两次可判称呼的形式不同」（`A → B`，含 `A→B→A` 计 1 对）的有向对数 |
| 比率 | `S-1 = 分子 / 分母`（报告时**必须同时给分子/分母**：`12/43 (27.91%)` 这种形态，不许只写百分比） |
| 次级登记 `S-2` | 「来回摆动」对数（出现 `A→B→A`，即 ≥2 次方向反转）/ 同一个分母。**只登记、不作判据**（分母更小，功效必然更差，见 §5.3） |
| 实现 | **新增只读聚合件** `tools/metrics/addr_swing.py`：从 `run.jsonl` 的 `MSG_DM` 重算，复用 `address_drift.py` 的呼语位识别与词表（词表 sha 必须 = `dc4ce327…`）；**不得修改** `address_drift.py` 的任何判据 |
| 冻结要求 | 该脚本 sha256 + 其定义段落 sha256，必须在**起跑前**写入两臂回执，且**两臂必须用同一个 sha**；两臂 sha 不同 ⇒ `批次无效（非单变量）` |

> **为什么必须新写而不能用现成的**：`address_drift.py:320` 对 `addr_switch_rate.examples` 有 **`if len(switch_examples) < 20`** 的硬上限（实测 `grep -n examples` 命中第 320 行），因此 `examples` **不能**作为摆动聚合的数据源（在 `n16r84` 这种规模上会被截断到 20 条）。这一点是「必须新增脚本」的**技术依据**，不是偏好。

### 3.2 次级登记项（**只登记，不参与判定**）

| 读号 | 口径 | 为什么只登记 |
|---|---|---|
| `S-2` | 来回摆动（`A→B→A`）对数 / 可判有向对 | 分母比 `S-1` 更小，功效更差；D10 已证「单调口径会漏」，但来回摆动更稀有 |
| `R-switch` | D10 v3 `addr_switch_rate.rate_scored`（相邻对层级，分母 A） | **与 D10 报告可对齐的唯一口径**；保留用于跨轮衔接，**不作本臂判据** |
| `R-stage` | D10 v3 `addr_stage_ordinal`（升/平/降） | 单调口径，D10 §9 已证会漏摆动；只登记 |
| `R-vocab` | `addr_vocab_per_pair`（无向对去重称呼形式数均值/中位） | 描述词表是否扩张；`d9s-on` 曾出现「第 3 种称呼是错称」的污染（D10 §5.3） |
| `addr_coverage` | per-message 呼语位识别率 | 进护栏 `G3`（不参与主判定） |
| `addr_any_mention_rate` | per-message 任意位置提及率 | 纯描述，`D10 §6` 明确「不参与主判」 |
| `addr_error_rate` | 叫错人（`self_name + other_named`）/（`target_ok + self_name + other_named`） | 进护栏 `G2`，并与官方 `L-10 self_address_error` **并列同屏** |

### 3.3 口径变更声明（**必须与任何 N-15 读数同行**）

> `S-1` / `S-2` 是本轮**新定义**的口径。**D10 报告（v3）的 `R-switch` / `R-stage` 数值与本臂的 `S-1` 不得并列成「两种结果」，也不得称「变化了/提升了」**。
> 引用规则：① 报 `S-1` 必须同时报 `R-switch`（便于和 D10 衔接），但**只有 `S-1` 进判定**；② 跨轮比较若口径不同，须整段写成「口径变更：`R-stage`（单调）→ `S-1`（摆动），两者不可互比」。

### 3.4 尺子自检（起跑前必须 rc=0）

```bash
python3 tools/metrics/address_drift.py --selftest        # 现成，实测 PASS(failures=0)
python3 tools/metrics/addr_swing.py --selftest           # 待新增，必须 ≥8 条用例全过
```

本轮已实跑前者：`[selftest] PASS (failures=0)`（10 条呼语位用例 + 3 条端到端用例，含 `石叔→老石` 摆动用例）。

---

## 4. 机制闸 M1–M6（**先过闸，再谈效果**；任一不过 ⇒ 写「机制未生效 / 批次无效」，**不得**写「无效」）

| 闸 | 检什么 | 判据（写死） | 不过时的结论 |
|---|---|---|---|
| **M1** | 单测 | 新分支默认 OFF 路径单测 + 开关三态解析单测（`{1,true,yes,on}` / 缺省 / 其它值）全绿，`pytest` rc=0 | `机制未生效` |
| **M2** | 接线（静态，prompt 层） | OFF 态渲染 `dialogue_prompt` 的 sha256 **≠** ON 态；**且** OFF 态 sha256 **=** 未改动基线树（`e8a9fd5e…` 或当时的 ON 前基线）渲染的 sha256（**逐字节**） | `机制未生效`（开关没接进提示词） |
| **M3** | 接线（日志层，**在日志里可证**） | 两臂 `purpose=dialogue` 的 `prompt_hash` 集合**交集为空**（`LLM_CALL[*].payload.prompt_hash`，该字段实测存在） | `机制未生效` |
| **M4** | 开关真值 | `switch_proof.txt`（从 `/proc/<pid>/environ` 取真值）在 ON 臂有 `LIFE_PROMPT_ADDR_EVOLVE=1`、OFF 臂**无该变量**；`meta.json.switch_declared` 含该变量记录 | `机制未生效` |
| **M5** | 真 LLM 验真（唯一判决口径） | `python3 -m obs llm-cost --log <run.jsonl> --require-provider openai_compat` ⇒ `provider_guard.ok=true`、`total.degraded=0`、`by_provider` 只有 `openai_compat` | `批次无效` |
| **M6** | 批次可控（单变量） | 两臂 `code_sha == code_sha_end` 且**两臂相等**；`git_dirty_code_files == []`；`n=16`、`rounds=84`、`seed=42`（`seed_in_log==seed_declared==42`）、`model=DeepSeek-Flash`、`endpoint_host` 相同；起跑 `pgrep` 无并发 | `批次无效（非单变量）` |

> **`meta.switch_effective` 对本开关只能记 `cannot-verify`**：`emit_run_meta` 的 `switch_effective` 靠「结构字段命中 >0」判 ON，而称呼演化**没有**专属结构字段（称呼文本不进 payload）。因此本开关的 ON/OFF 判定**只认 M2 + M3 + M4**（prompt 层 + 日志 `prompt_hash` 层 + 进程 environ 层），**不得**用 `switch_effective=off` 反推「开关没开」。

---

## 5. 效果判据与阈值（**阈值前置，不得事后调**）

### 5.1 主判据（**只有 `S-1` 进判定**）

`Δ = 100 × (S-1(ON) − S-1(OFF))`，两臂各带自己的分子/分母；统计检验用 Fisher 双侧精确检验（沿用 `tools/metrics/d10_address_summary.py::fisher_exact_two_sided`，纯 stdlib 可复算）。

### 5.2 护栏判据 `G1–G7`（**全部同屏并列；任一击穿按 §5.4 处置**）

| # | 护栏 | 阈值（写死） | 击穿后果 |
|---|---|---|---|
| **G1** | **`L-7` 8-gram 重复率**（**CYCLE-34 `N-15` 明确要求「必须并列」的硬要求**） | `ON ≤ max(OFF + 10pp, 40%)`；两臂数值必须与 `S-1` **同屏出现** | `无效（套话）` |
| **G2**（**已按 §14 Amendment 1 + 2 修订，2026-10-30**；当前有效版本 = Amendment 2） | 叫错人：`addr_error_rate`（自称 + 错称第三者）。官方 `L-10 self_address_error` 作**并列披露项**（同屏出现、供读者自查，**不作「必须不升」这类必要条件**） | 自定义口径 `addr_error_rate`：`ON − OFF ≤ +2.0pp`；**击穿条件 = 两条并列 OR**：**(a)** `addr_error_rate` 的 `ON − OFF ≥ +3pp`；**(b)** 官方 `L-10 self_address_error` 的**分子 `> 0`（绝对非零，不写「上升」）** | `无效（叫错人）` |
| **G2-附（强制同屏句）** | —— | 每处出现 `L-10` 的地方**必须**同屏写死这一句：**「`L-10` 分子恒 0（本维度 5 份日志皆 `0/174`、`0/172`、`0/165`、`0/172`、`0/172`，分母 165–174，单位 MSG 条），对本维度无区分力；`L-10 = 0` 不得用于背书『称呼没问题』」** | 缺此句 ⇒ 报告不得通过收口 |
| **G3** | 覆盖闸：`addr_coverage` | `ON ≥ OFF − 5pp`（禁止靠「少叫称呼」抬高摆动率） | `不可判（副作用混杂：覆盖下降）` |
| **G4** | 假性相关：`F-1` 非功能性闲聊占比 | `|Δ| ≤ 5pp` | `不可判（副作用混杂：闲聊量变动）` |
| **G5** | 编造：`F-7b` 编造事件率 | 若 `F-7b is None` ⇒ 结论必须同屏写「**F-7b=None，编造风险未测**」，且**禁止**任何「不引入编造」的主张（`R4` 陷阱3） | 不击穿判定，但**限定结论措辞** |
| **G6** | **R-11 四数（按 `purpose=dialogue` 分列）**：MSG 数 / dialogue 调用数 / 真调用数（`tokens_in>0`）/ 缓存回放数 | 两臂 `dialogue` 真调用率必须 **= 100%**；`degraded=0`；两臂 `side-root` 不同且**起跑前为空目录** | `批次无效（缓存回放）` |
| **G7** | 两臂实例边界 | 两臂 `freeze_cache` 目录 inode/mtime 不同（D10 §2 `side_root_note` 同法） | `批次无效（非单变量）` |

> **`G6` 为什么是硬闸，不是建议**：D10 §7.1 实测 `d9m-off` 的 `dialogue` 真调用 = **0/191**（100% 回放）、`d9m-on` = 19/191、`d9s-off` = 7/191。**基线臂整份是缓存回放** ⇒ 那一轮的「称呼变化」连「同一条件下的差」都不算。本臂若重犯，判定只能落在 `批次无效（缓存回放）`，**不许**落 `无效`。

### 5.3 功效声明（**事前登记，防事后找借口**）

按 §11.3 的**实测分母**（`n16 r84`：可判有向对 `50`、`switch` 可判相邻对 `43`）与基线 `S-1 ≈ 2.3%`（基线臂 `n_switch=1 / 43`）：

| 分母 | 可检出 `Δ`（α=.05 双侧，power≈.80，正态近似） | 备注 |
|---|---|---|
| 43 | **≳ +20pp**（power `0.806`） | `Δ=+15pp` 时 power 仅 `0.648` |
| 50 | **≳ +20pp**（power `0.861`） | `Δ=+15pp` 时 power `0.713` |
| 80 | ≳ +15pp（power `0.891`） | 只有把 rounds 再翻倍才够 |

⇒ **本臂只能检出 `Δ ≳ +20pp`**。真实效应若只有 `+5~+15pp`，本臂**注定**给出 `不可判（功效不足）`——这是**预期内的诚实结论**，与 `未达标`、`有效` 并列合法，**不构成失败**，也**不得**触发任何阈值/口径调整（唯一允许的动作是 §7.6 的 `seed=7` 复制支路，判据不变、不合并）。

### 5.4 判定格速查（**逐格写死，防下一轮为「+18pp 该判什么」吵架**）

| # | 观察 | 判定 | 说明 |
|---|---|---|---|
| **J-1** | `Δ ≤ 0` | **`未达标`** | 指令行无正效应 |
| **J-2** | `0 < Δ < +20pp` | **`不可判（功效不足）`** | **不能判 `未达标`**：`Δ>0` 但低于可检出线，无法区分「小效应」与「无效应」 |
| **J-3** | `Δ ≥ +20pp` 但 Fisher `p ≥ 0.05` 或两臂 Wilson 95% CI 重叠 | **`不可判（功效不足）`** | **最容易被误判的一格**：`Δ` 够大但样本不够 ⇒ 功效问题，**不是效应不存在** |
| **J-4** | `Δ ≥ +20pp` **且** `p < 0.05` **且** CI 不重叠 | 进 `G1–G7` 复判：全守 ⇒ **`有效`**；`G1` 击穿 ⇒ `无效（套话）`；`G2` 击穿 ⇒ `无效（叫错人）`；`G3`/`G4` 击穿 ⇒ `不可判（副作用混杂，须写明哪条）` | 只有这一格能出 `有效` |
| **J-5** | M1–M4 任一不过 | **`机制未生效`** | 开关没接进去 ⇒ **不得**写 `无效` |
| **J-6** | M5 不过 / M6 不过 / `G7` 击穿 | **`批次无效（非单变量）`** | 两臂不同树/不同规模/并发起跑 |
| **J-7** | `G6` 击穿（任一方 `dialogue` 真调用率 <100%、或 `degraded>0`） | **`批次无效（缓存回放）`** | 读数不可归因；**不得**写 `无效` |
| **J-8** | 两臂 `S-1` 任一分母 **< 30** | **`不可判（分母不足）`**，只报事件数、不报百分比趋势 | 沿用 `R4-life-texture.md:79-83` 全族纪律 |
| **J-9** | OFF 臂等价性证明（§8.3 `L1`/`L2`）缺失或不过 | **`不可判（接线不受控）`** | 没有「OFF = 现状」这条锚，ON 的变化无从归因 |

> **一句话记住**：**`Δ ≤ 0` 才是 `未达标`；`Δ > 0` 而未过可检出线/或 CI 重叠，一律 `不可判（功效不足）`；机制与批次问题一律不得写成 `无效`。**

---

## 6. 分母要求（≥30）与不足时的降级措辞

### 6.1 硬要求

| 读数 | 分母定义 | ≥30 要求 | `n16 r84` 实测（§11.3，既有无干预臂） |
|---|---|---|---|
| `S-1` / `S-2` | 可判有向对数（线程内 `speaker→addressee`，≥2 次可判称呼） | **≥30** | **50** ✔（基线：升0 / **平50** / 降0） |
| `R-switch` | 可判相邻对（同线程×同说话人×同对象，两端都识别出称呼） | **≥30** | **43** ✔（基线 `n_switch=1`） |
| `R-vocab` | 角色对（≥3 条 `MSG_DM`） | ≥30 | **56** ✔ |
| `addr_coverage` | 全部 MSG | **686** ✔（`d9m` 系 191） |
| `addr_error_rate` | 可判指向的具名称呼 | ≥30 | **198** ✔ |

⇒ **`n16 r84` 是 N-15 的最小可用规模**；**`r60` 及以下一律不跑**（D10 已实测 191 MSG 下 `switch` 分母 11–22）。

### 6.2 分母不足时的降级措辞（**照抄，不要自己发明**）

> 若某读数的分母 `< 30`：**该读数只报事件数，不报百分比、不报趋势、不做跨臂比较**；主判据分母 `< 30` ⇒ 判定直接落 **`不可判（分母不足）`**，并在同段给出「下一轮需把 `rounds` 抬到 `84 × ceil(30 / 实测分母)`」的**定量建议**。**严禁**把 `不可判（分母不足）` 改写成 `未达标` / `无效` / `无改善`。

---

## 7. 双臂设计与不可变量（**写死**）

### 7.1 同 `code_sha`

- 两臂必须由**同一个 commit 的同一棵树**起跑：`meta.code_sha == meta.code_sha_end`，且 **OFF 臂 == ON 臂**（逐字符相等）；`git_dirty_code_files == []`；
- 起跑前各记一次 `git rev-parse HEAD`（写入两臂回执）；**两臂之间不得有 commit**。

### 7.2 规模与种子

| 参数 | 写死值 | 校验字段 |
|---|---|---|
| `--agents` | **16** | `meta.n == n_declared == n_in_log == 16` |
| `--rounds` | **84** | `meta.rounds == rounds_declared == rounds_effective == 84`；`rounds_contiguous == true` |
| `--seed` | **42** | `meta.seed == seed_declared == seed_in_log == 42` |
| 模型 / 端点 | `DeepSeek-Flash` / `config/llm.json` 的 endpoint（`endpoint_host 172.16.3.41:31809`） | `meta.model_requested == model == 'DeepSeek-Flash'`；`model_reported == ['DeepSeek-Flash']`；两臂 `endpoint_host` 相同 |
| provider | `HITT_LLM_PROVIDER=openai_compat` | M5 `provider_guard.ok=true` |

### 7.3 冷缓存（`side-root`）

- 两臂**各用一个不同的 `--side-root`**，且**起跑前该目录不存在（或已清空）**；跑后必须报两侧 `freeze_cache` 目录的 inode/mtime；
- **不得**复用历史 side-root（D10 §7.1 的 92.7%–100% 回放率就是复用/热缓存的后果）。

### 7.4 串行与真调用率

```bash
pgrep -af "orchestration run|run_batch|nightly\.py"   # 起跑前/起跑后各一次，须无命中（除自身命令行）
```

- 两臂**串行**（先 OFF，后 ON），禁并行、禁 `sleep` 轮询，必须 `setsid` 后台；
- 每臂跑完立刻做 `G6` 检查：`purpose=dialogue` 的 `tokens_in>0` 条数 **==** `dialogue` 调用数（即 100% 真调用）；不达 ⇒ 该臂作废重跑（**不允许**用「回放率不同」自辩）。

### 7.5 起跑顺序（写死，防「先看 ON 再定 OFF 的阈值」）

**OFF 臂先跑完并出全套读数**，然后再跑 ON；两臂的判定在 §5 已完全写死，**OFF 读数不改变任何阈值**（本条是「预登记强度」的关键）。

### 7.6 复制支路（唯一的合法追加动作）

仅在判定落 `J-2` 或 `J-3`（`不可判（功效不足）`）时，允许加跑 `seed=7` 的 **OFF/ON 各一臂（同 `code_sha`、同 `n16 r84`、冷缓存）**：判据、阈值、护栏**一律不变**，两 seed 结果**分别独立判定**后并列报告，**不得**合并计数、不得择优、不得用它把 `不可判` 洗成 `有效`。

---

## 8. 实现约束（**开关怎么做才合规**）

### 8.1 开关语义

| 项 | 写死要求 |
|---|---|
| 变量名 | **`LIFE_PROMPT_ADDR_EVOLVE`**（常量 `ADDR_EVOLVE_ENV`，放在 `code/life/agent.py` 顶部与其他 `LIFE_PROMPT_*` **同处**；现有惯例见 `agent.py:59/79/187/245` 的 `.strip().lower() in {"1","true","yes","on"}`） |
| 默认 | 缺省 / 空串 / 非法值 ⇒ **OFF**（**必须**与现树行为逐字节等价，见 §8.3） |
| 注入点 | **只**改 `LifeLayerAgent._dialogue_prompt`（对话提示词），**不改** `_reply_prompt`——单变量（改两处 ⇒ 无法归因） |
| 注入形态 | **追加一行**（≤1 句、无示例、无轮换、无多行模板），文本在实现时冻结并记 sha |
| 冻结区 | 实现必须在**新分支**上、且**跑批期间不得改** `code/{life,orchestration,config,engine}`；本次跑批的 `code_sha` 在起跑瞬间钉住 |
| meta 登记 | `tools/d2/emit_run_meta.py`（**非**冻结区）须把该变量记入 `switch_declared`；`switch_effective` 记 `cannot-verify` 并在 note 里写明「称呼文本不入 payload，ON/OFF 判据见 M2/M3/M4」 |
| 配套工具 | `tools/d9/prompt_fn_sha.py` 的 docstring 承诺 `--env-var`，但**实测 `--help` 只有 `--code-root` / `--exit-on-same`，且源码把开关**硬编码**为 `HITT_D12_PREFWORD` + `_d12_prefword_line`**（`:66`、`:85`）⇒ 必须**新增** `tools/d9/addr_evolve_wiring.py`（或补 `--env-var` 参数），**不得**直接改用它来「证明 N-15 接线」 |

### 8.2 开关两态必须可分辨（M2/M3）

- **M2（静态）**：`OFF` 态渲染 `dialogue_prompt` sha256 **必须等于**未改动基线树的渲染值（逐字节），`ON` 态必须**不同**；
- **M3（日志）**：两臂 `purpose=dialogue` 的 `payload.prompt_hash` 集合**交集为空**（该字段实测存在，见 §11.2 的 `LLM_CALL` 样例；`cache_key` 由 prompt 派生，故两臂缓存天然不串，但仍须冷缓存）。

### 8.3 **「OFF 与现状逐字节等价」的三层验证（含一条收窄声明）**

| 层 | 能证明什么 | 怎么证（可照抄） | 结论 |
|---|---|---|---|
| **L1（静态，可证逐字节）** | prompt 渲染层等价 | ①`git diff` 只含「新增 env 常量 + 读取函数 + `_dialogue_prompt` 内一个 `if` 块」，无其它改动；②在**未改动基线树**（`e8a9fd5e…`）与**新树**各渲染一次 `dialogue_prompt`（开关缺省），两 sha256 **必须相同** | ✅ 可证 |
| **L2（离线 mock，可证逐字节）** | 行为层等价（同参、同 seed、无网络） | 两树各跑 `n4 r12 seed42`（**不设** `HITT_LLM_PROVIDER` ⇒ `MockProvider`，`integration.py:936` 实测逻辑），比较 `run.jsonl` 的 `MSG_*` 事件 `payload` **逐条 0 差异**（忽略 hash 链/`config_digest`/时间戳字段，与 `v2/refs/D9c-prereg-reply-pick-order.md` §1 同法） | ✅ 可证 |
| **L3（真 LLM，**不可证逐字节**）** | 只能做「同量级」观察 | D8 实测：`temperature=0.0`、同 seed、同 prompt 的两批真 LLM 台词**逐字节相同仅 49/230 = 21.30%** ⇒ 真 LLM 层**不存在**逐字节等价 | ⚠ 只观察 |

> **收窄声明（写于未见任何 ON 臂读数之前，属跑前预登记）**：`reports/CYCLE-34-20261030.md` §5.1 对 `N-15` 的验收语是「OFF 臂与现状**读数逐字段相同**」。按上表，这句在**真 LLM 层不可实现**（D8 的 21.30% 就是证据）。因此本预登记把该验收语**收窄为**：
> **① `L1`+`L2` 必须过（这是「OFF = 现状」的硬证据）；② 真 LLM 层只要求 OFF 臂的 `S-1`/`R-switch`/`R-stage`/`addr_coverage`/`addr_error_rate`/`L-7` 落在 §11.3 基线探针的**观察带**内（同量级），并在报告里**明确写「真 LLM 层不承诺逐字段相同，理由：D8 实测同 seed 同 prompt 逐字节一致率 21.30%」**。**
> 收窄的是**验收措辞**，不是判据；本收窄**不允许**被用来放宽 §5 的任何阈值。

### 8.4 硬边界（实现者必须遵守）

- 不得为了「让称呼变」而在代码里加**称呼替换表 / 轮换池 / 定时换称呼**——那是 `L-7` 套话（`G1`）的温床，等于把 `d9s-on L-7=74.87%` 的红旗路径复制一遍；
- 不得改 `v2/refs/address-ordinal.yaml`（改词表 = 改判据，会毁掉与 D10 的可对齐性）；
- 不得在 `_dialogue_prompt` 里读关系值的**数值阈值**做分支（否则「关系值 → 称呼」被写死进代码，测的就不是 LLM 的行为）。

---

## 9. 失败 / 不可判的预定义结论（**什么情况必须写「不可判」而不是「无效」**）

| 情况 | 必须写的结论 | **禁止**写成 |
|---|---|---|
| 开关字符串在 `code/` 里没接进提示词（M2 两态 sha 相同） | `机制未生效` | `无效`、`未达标` |
| 两臂 `prompt_hash` 集合有交集（M3 不过） | `机制未生效` | `无效` |
| 进程 environ 里 ON 臂没这个变量（M4 不过） | `机制未生效` | `无效` |
| `dialogue` 真调用率 <100% / `degraded>0` / 复用热 side-root | `批次无效（缓存回放）` | `无效`、`不可判（功效不足）` |
| 两臂 `code_sha` 不同 / 规模种子模型不同 / 并发起跑 | `批次无效（非单变量）` | `无效` |
| 主判据分母 <30 | `不可判（分母不足）` | `未达标`、`无效`、`无改善` |
| `Δ>0` 但 <可检出线，或 `Δ≥线` 而 CI 重叠 | `不可判（功效不足）` | `未达标`、`无效` |
| OFF 等价性 `L1`/`L2` 不过 | `不可判（接线不受控）` | `无效`、`有效` |
| `Δ≥+20pp` 且 `p<0.05` 且 CI 不重叠 且 `G1` 击穿 | `无效（套话）` | `有效` |
| 同上但 `G2` 击穿 | `无效（叫错人）` | `有效` |
| `F-7b is None` | 结论**必须**同屏写「编造风险未测」 | 「不引入编造」 |

---

## 10. 成本与耗时预算（**口径来自历史 `meta.json` / `llm_cost.txt` 实测，不外推单价**）

| 锚点 | 来源（可原位重放） | 实测值 |
|---|---|---|
| 单臂调用数 | `v2/evidence/run_d1_f6on_seed42_n16r84/meta.json` | `llm_calls = 3403`（`n16 r84 seed42`） |
| 单臂 token | `v2/evidence/run_d1_f6on_seed42_n16r84/llm_cost.txt` → `engine_log.total` | `tokens_in 450880 + tokens_out 327809 = 778689`（同规模 OFF 对照 `run_d1_f6off…`：`369931 + 312258 = 682189`） |
| 单臂耗时 | 同目录 `meta.duration_sec` / `batch_timing.txt` | `2873 s` / `elapsed_sec=2878` ≈ **48 min** |
| 按 purpose 分布（ON） | `llm_cost.txt` `by_purpose` | `dialogue 714`、`importance 1747`、`judge 717`、`reflect 112`、`negotiation 81` |
| `dialogue` 真调用 | 实测本仓代码按 `purpose=='dialogue'` 统计 | **714/714 = 100%**（冷缓存达成） |
| 双臂预算 | 2 × 上表 | **≈ 6800 次调用 / 1.4–1.6M tokens / ≈ 96 min 跑批 + 收尾 ≈ 2 h 总墙钟** |

> **不做的估算**：本仓**没有**记录该 provider 的单价，因此**本文件不给金额**。金额只在下一轮实际 `llm-cost` 报告出来后再算，且必须写明「按 `tokens_in/out` 与当时计费口径」。
> 曾出现的 `d9m` 系（`n16 r24`）单臂 `2252 calls / 306482 tokens / 16 s`（`run_weather_on_n16r24_seed42_c28`）**不可用于 r84 预算**（规模 3.6×），此处仅登记不采用。

---

## 11. 真 LLM 可行性核查（**只读**；结论：**能跑**，缺 3 件 + 1 项不可验证）

### 11.1 凭据与配置

| 检查 | 命令 | 观察结果 |
|---|---|---|
| 凭据变量是否配置 | `awk -F= '/^[A-Za-z_]+=/{print $1" : len="length($0)-length($1)-1}' code/.env.local` | `HITT_LLM_PROVIDER : len=13`、`LLM_API_KEY : len=32` ⇒ **均已配置（非空）**。**值未打印、未写入任何文件**（`len=13` 与 `openai_compat` 长度一致，但**本文件不据此断言其值**；真值由下一轮 `switch_proof` 从 `/proc/<pid>/environ` 取） |
| 是否会被提交 | `git check-ignore -v code/.env.local` | `code/.gitignore:11:.env.local  code/.env.local` ⇒ **已忽略**，不会入库 |
| 模型 / 端点配置 | `cat code/config/llm.json` | `endpoint = http://172.16.3.41:31809/v1`、`model = DeepSeek-Flash`、`embed_model = frozen://lexical-relevance-v1`、`thinking.true_purposes = [judge, narrate, describe]`、`true_tiers=[t2]`（密钥「只从 env `LLM_API_KEY` 读取」，与文件注释一致） |
| 端点连通性 | `python3` 原生 socket `connect(("172.16.3.41", 31809))`，timeout 5s | **TCP connect OK**（本轮实跑，见 §11.3 命令 4） |
| 端点管线是否需注入 env | `sed -n '936,944p' code/orchestration/integration.py` | 真 provider 分支：`HITT_LLM_PROVIDER == "openai_compat"` 且 `endpoint && model` 非空 ⇒ `OpenAICompatProvider(...)`；否则回落 `MockProvider`。⇒ 必须 `set -a; . ./.env.local; set +a`（`tools/d2/run_batch.sh:49` 同法） |
| 历史可用性（旁证） | `v2/evidence/run_d1_f6on_seed42_n16r84/llm_cost.txt` | `provider_guard.ok = true`、`by_provider = {openai_compat: 3403}`、`degraded = 0` ⇒ 该端点在该树上**曾经**真跑成功 |

> **不可验证项（诚实标注）**：**模型鉴权 / 账户余额 / 配额未验证**——验证它们必须发一次真实 LLM 请求，而本轮纪律是「不调 LLM」。⇒ 本文件只声明「端点 TCP 可达 + 变量已配置 + 同端点同模型历史上真跑成功」，**不声明「现在能成功鉴权」**。下一轮起跑后 60 s 内必须以 M5 验真；若首个 `LLM_CALL` 出现 401/403/degraded>0 ⇒ 该批 `批次无效`。

### 11.2 目标开关与工具链现状

| 检查 | 命令 | 观察结果 |
|---|---|---|
| 开关是否已存在 | `grep -rn "ADDR_EVOLVE" code/ tools/` | **退出码 1（零命中）** ⇒ 实现工作 **0 行**，`F-73` 仍在 |
| 现有开关惯例 | `grep -rn "LIFE_PROMPT_" code/ --include=*.py` | 既有 12 个 `LIFE_PROMPT_*`，读取惯例统一在 `code/life/agent.py`（`:59/79/139/187/245/250`） |
| 日志里有 `prompt_hash` 吗（M3 可行性） | 读 `v2/evidence/d9m-ab-off_n16r24_s42/run.jsonl` 首条 `LLM_CALL` | `payload` 键含 **`prompt_hash = sha256:cee606b4…`**、`cache_key`、`purpose`、`model`、`provider`、`tokens_in/out`、`cached` ⇒ **M3 用 `prompt_hash` 集合可判** |
| 摆动口径能否复用现成件 | `grep -n "examples" tools/metrics/address_drift.py` | `:320` `if len(switch_examples) < 20` ⇒ `examples` **被截断到 20 条**，**不能**作摆动聚合源 ⇒ 必须新增 `tools/metrics/addr_swing.py` |
| 尺子与词表身份 | `sha256sum tools/metrics/address_drift.py v2/refs/address-ordinal.yaml` | `37a5dc52…0c0c` / `dc4ce327…22d95`，与 D10 报告 §3.1 / 附录 A R6 **逐字符一致** |
| 尺子自检 | `python3 tools/metrics/address_drift.py --selftest` | `[selftest] PASS (failures=0)`（含 `石叔→老石` 摆动与 `self_name`/`other_name` 用例） |
| 单臂入口 | `grep -n "add_argument" code/orchestration/cli.py` + `switch_proof.txt` | `python3 -m orchestration run --life --seed 42 --agents 16 --rounds 84 --out <run.jsonl> --flush-every 2 --side-root <tmp>`（与 `d9m` 臂实际 cmdline 同形） |
| 成本验真入口 | `cd code && python3 -m obs llm-cost --help` | 支持 `--log / --cache-dir / --require-provider / --out` ⇒ M5 可执行 |
| 接线预检件 | `python3 tools/d9/prompt_fn_sha.py --help` + `sed -n '60,115p'` | **只有 `--code-root`/`--exit-on-same`**；源码硬编码 `HITT_D12_PREFWORD`（`:66`）与 `_d12_prefword_line`（`:85`）⇒ 需新增 N-15 专用接线件 |
| 并发跑批 | `pgrep -af "orchestration run\|run_batch\|nightly\.py"` | 仅命中查询自身命令行 ⇒ **当前无并发跑批** |

### 11.3 分母探针（**本轮唯一的「读数」，须与任何引用同行**）

对**既有、无称呼干预**的 `run_d1_f6on_seed42_n16r84/run.jsonl`（`code_sha e8a9fd5e…`，`686 MSG`，`194008 events`）跑只读尺子（输出到 `/tmp`，**未落仓**）：

| 读数 | 值 |
|---|---|
| `n_messages` / `n_messages_with_addr` | `686` / `267` |
| `addr_coverage` | **38.92%**（267/686） |
| `addr_any_mention_rate` | **89.94%** |
| `R-switch` | **1/43（2.33%）**，`denom_all_pairs = 275`（`rate_all = 0.36%`） |
| `R-stage` | 分母 **50**，**升 0 / 平 50 / 降 0**（`mean_delta = 0`，coarse 同值） |
| `R-vocab` | 分母 **56**，均值 `1.607`，中位 `2`，最大 `3` |
| `addr_error_rate` | **2/198（1.01%）**（`self_name 0`、`other_named 2`） |

**这三条是 N-15 的可行性基石**：① `n16 r84` 下 `switch`/`stage`/`vocab` 分母 **43 / 50 / 56，全部 ≥30** ⇒ §6.1 的 ≥30 要求**已被实测满足**（不是外推）；② 基线 `R-stage` **50/50 全平**、`R-switch` 仅 `1/43` ⇒ 摆动口径在基线上**几乎是 0**，ON 臂只要真起作用就会显形；③ 基线 `addr_error_rate = 1.01%` ⇒ `G2` 的 `+2.0pp` 阈值有足够余量。

> **披露**：该探针给出了**基线水平**（这也是 §5.3 功效声明的输入）。作者**先看基线、后写判据**这一点如实登记；判据阈值取自**功效计算**（§5.3）而非「照着基线挑一个好看的门槛」，且 §5.2 护栏与 §9 的不可判格**不随基线值变化**。开关物理上不存在（§0.1）⇒ 探针**不可能**含任何 ON 臂信息。

### 11.4 可行性结论（**能跑 / 不能跑 / 缺什么**）

> **结论：能跑。** 缺 3 件实现物 + 1 项不可验证项；其中没有一项是「环境不可用」类阻塞。

| # | 缺什么 | 谁能补 | 阻塞级别 |
|---|---|---|---|
| 1 | **开关实现**：`ADDR_EVOLVE_ENV` + `_dialogue_prompt` 一行注入 + 默认 OFF（`code/life/agent.py`，**冻结区，须新分支**） | 实现工程师 | **必做**（否则只能落 `机制未生效`） |
| 2 | **摆动口径脚本** `tools/metrics/addr_swing.py`（`S-1`/`S-2` + `--selftest` ≥8 例），出数前冻结 sha | 出数人（tools/ 非冻结区） | **必做**（主判据无实现） |
| 3 | **接线预检件** `tools/d9/addr_evolve_wiring.py`（L2/M2 的 OFF==基线 逐字节证明） | 同上 | **必做**（否则 §8.3 `L1/L2` 无法证） |
| 4 | **鉴权/配额未验证（CANNOT-VERIFY）** | —— | 不阻塞；下一轮 M5 兜底 |

**已就绪（不需要补）**：凭据变量（已配置、已 gitignore）、`llm.json`（端点+模型+thinking 策略）、真 provider 开关逻辑（`integration.py:936`）、跑批入口（`orchestration run`）、成本验真（`obs llm-cost --require-provider`）、尺子与词表（sha 与 D10 一致、`--selftest` PASS）、分母规模（`n16r84` 实测 ≥30）、Mock 等价回放能力（`MockProvider` + `--side-root`）。

---

## 12. 下一轮执行清单（**照抄即可**；本轮未执行其中任何一条跑批命令）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# ── 0) 串行与树身份（起跑前各一次）
pgrep -af "orchestration run|run_batch|nightly\.py"      # 须无命中
git rev-parse HEAD; git status --porcelain | grep '^ M'  # code/ 不得有未提交改动

# ── 1) 接线（M1/M2）
python3 -m pytest code/life/tests -q                     # 新分支单测
python3 tools/d9/addr_evolve_wiring.py --code-root code --baseline-root <e8a9fd5e 的 worktree>
#   要求：OFF 渲染 sha == baseline 渲染 sha；ON 渲染 sha != OFF；rc=0

# ── 2) 离线等价（L2，无网络：不设 HITT_LLM_PROVIDER）
python3 -m orchestration run --life --seed 42 --agents 4 --rounds 12 --out /tmp/eq_new_off.jsonl --side-root /tmp/eq_side_a
python3 -m orchestration run --life --seed 42 --agents 4 --rounds 12 --out /tmp/eq_base.jsonl  --side-root /tmp/eq_side_b   # 在 baseline worktree 里跑
python3 tools/metrics/addr_swing.py --msg-diff /tmp/eq_base.jsonl /tmp/eq_new_off.jsonl   # MSG_* payload 逐条 0 差异

# ── 3) 尺子自检
python3 tools/metrics/address_drift.py --selftest && python3 tools/metrics/addr_swing.py --selftest

# ── 4) OFF 臂（冷缓存、串行、setsid）
set -a; . ./code/.env.local; set +a
rm -rf /tmp/n15_off_side
setsid python3 -m orchestration run --life --seed 42 --agents 16 --rounds 84 \
  --out v2/evidence/n15-off_n16r84_s42/run.jsonl --flush-every 2 --side-root /tmp/n15_off_side \
  > v2/evidence/n15-off_n16r84_s42/run.stdout 2>&1 &

# ── 5) ON 臂（同一 code_sha、另一冷 side-root）
rm -rf /tmp/n15_on_side
LIFE_PROMPT_ADDR_EVOLVE=1 setsid python3 -m orchestration run --life --seed 42 --agents 16 --rounds 84 \
  --out v2/evidence/n15-on_n16r84_s42/run.jsonl --flush-every 2 --side-root /tmp/n15_on_side \
  > v2/evidence/n15-on_n16r84_s42/run.stdout 2>&1 &

# ── 6) 每臂收尾：meta / 真 LLM 验真 / R-11 四数 / switch_proof
python3 tools/d2/emit_run_meta.py --run-dir v2/evidence/n15-off_n16r84_s42
cd code && python3 -m obs llm-cost --log ../v2/evidence/n15-off_n16r84_s42/run.jsonl \
  --require-provider openai_compat --out ../v2/evidence/n15-off_n16r84_s42/llm_cost.txt; cd ..

# ── 7) 两臂读数（主判据 + 护栏 + 官方口径并列）
python3 tools/metrics/addr_swing.py --log v2/evidence/n15-off_n16r84_s42/run.jsonl --arm OFF --out-json v2/evidence/n15_addr/off.json
python3 tools/metrics/addr_swing.py --log v2/evidence/n15-on_n16r84_s42/run.jsonl  --arm ON  --out-json v2/evidence/n15_addr/on.json
python3 tools/metrics/address_drift.py --log v2/evidence/n15-off_n16r84_s42/run.jsonl --arm OFF --out-json v2/evidence/n15_addr/off_v3.json --out-md /tmp/o.md
python3 tools/metrics/d10_address_summary.py --run n15-off=OFF=v2/evidence/n15-off_n16r84_s42/run.jsonl \
  --run n15-on=ON=v2/evidence/n15-on_n16r84_s42/run.jsonl --out-dir v2/evidence/n15_addr   # 带 F-1/L-7/L-12b/Fisher
python3 tools/d5/dialogue_metrics.py --log v2/evidence/n15-on_n16r84_s42/run.jsonl --out-json /tmp/dm_on.json  # 官方 L-10 对拍
```

---

## 13. 不做什么（硬边界）

1. **不跑任何批**（本轮）；不调任何 LLM；不改 `code/{life,orchestration,config,engine}`；不改 `tools/`；不 commit；
2. **不新造维度编号**（沿用 D10 的 `C-A`；`F-9` 之类由 `R4-life-texture.md` 唯一所有）；
3. **不用 `addr_stage_ordinal` 单调口径作判据**（D10 §9 已证会漏摆动）；
4. **不把 `d9s-on` 的 `4/19` 或任何 `L-7 > 70%` 臂的读数当证据**（模板红旗，D10 §6/§9）；
5. **不给金额估算**（无单价记录），**不写「显著」**，**不写「更有生活气息」**；
6. **不用「缓存回放率不同」以外的理由自辩批次的独立性**——`G6` 是硬闸。

---

## 14. Amendments（**只许追加跑前修订；每条必须写「是否已见任一臂读数」**）

| # | 时间 | 内容 | 已见任一臂读数？ |
|---|---|---|---|
| **A-1** | **2026-10-30 22:13 +0800** | `G2` 击穿条件收为**只看**自定义口径 `addr_error_rate`（`ON − OFF ≥ +3pp`）；官方 `L-10` **降为并列披露项**、外加强制同屏句。详见 §14.1（**其中「唯一击穿」表述已由 A-2 作废**） | **否**（证据见 §14.1） |
| **A-2** | **2026-10-30 22:1x +0800** | `G2` 击穿条件**恢复为两条并列 OR**：**(a)** `addr_error_rate` 的 `ON − OFF ≥ +3pp`；**(b)** 官方 `L-10` 分子 **`> 0`（绝对非零）**。`L-10` 仍**不进**必要条件、只作并列披露 + 强制同屏句。详见 §14.2 | **否**（`grep ADDR_EVOLVE` 仍零命中，已实跑） |

### 14.1 Amendment 1 —— `G2` 口径限制（跑前修订）

**性质（先读）**：**跑前修订**。落盘时全仓 `grep -rn "ADDR_EVOLVE" code/ tools/` **仍零命中**（退出码 `1`）、**无任何 ON 臂读数**、**N-15 未起任何跑批**、开关未实现。
**修订日期**：2026-10-30 22:13 +0800（第 28 轮收尾当轮）。
**触发依据**：`reports/R28-address-relation-basis-20261030.md` §3.1 / §3.6（N-17 口径对拍：`addr_error_rate` 与官方 `L-10` **不是同一个量**，事件方向相反；且 `L-10` 在 5 份日志里**分子恒 0**、无区分力），基线 commit **`46d18a8`**（`46d18a8a41ffc36b05f5cec55c56923c1ea2d761`，「R28: 称呼×关系演化收口」）。经 team-leader **明确批准**后落盘。

**改了什么（只此一处）**

| 项 | 修订前（本文件首版） | 修订后 |
|---|---|---|
| `G2` 击穿条件 | `ON − OFF ≤ +2.0pp`，**且 `L-10` 方向不上升**；若 `Δ ≥ +3pp` **或 `L-10` 上升** ⇒ 击穿 | ~~自定义口径 `addr_error_rate`：`ON − OFF ≤ +2.0pp`；**唯一击穿条件 = `ON − OFF ≥ +3pp`**。`L-10` **不再进击穿条件**~~ **→ 本格已被 §14.2 Amendment 2 覆盖：现为两条并列 OR（(a) `addr_error_rate` `ON−OFF ≥ +3pp`；(b) `L-10` 分子 `> 0`）** |
| `L-10` 的地位 | 与 `addr_error_rate` **并列参与判定** | **并列披露项**（仍须同屏出现，只供读者自查），**外加强制同屏句**（见 §5.2 `G2-附`） |
| 理由 | —— | `L-10` 分子在 5 份日志里恒为 `0`（`0/174`、`0/172`、`0/165`、`0/172`、`0/172`）⇒ 「`L-10` 上升」这条子句**永远不触发**，既无判别力、又可能被后人误读成「`L-10 = 0` 背书了称呼没问题」 |

**显式未改动（防止被顺手改判据）**：主判据 `S-1 = addr_swing_pairs_rate` 及其统计单位/分子/分母定义、可检出线 `Δ ≥ +20pp`、`J-1`…`J-9` 判定格、护栏 `G1` / `G3` / `G4` / `G5` / `G6` / `G7`、§6 分母纪律与降级措辞、§7 双臂设计、§8 实现约束、§8.3 的 L3 收窄声明、§9 不可判格、§13 硬边界 —— **一律未动**。

**与 `R28 §3.6` 的一处措辞差异（如实登记，不自行扩大修订）**：`R28 §3.6` 末尾写「若出现『`addr_error_rate` 未升但 `L-10` 升』，按 `G2` 击穿处理（保守方向），但须注明 `L-10` 是另一构念」。本 Amendment 当时按 team-leader 首次裁决收为「**唯一击穿条件 = `addr_error_rate ≥ +3pp`**」，故该情形**不再触发击穿**；处置固定为：**报告必须单列一行观察（同屏记 `addr_error_rate` 与 `L-10` 两值 + 同屏句），判定不变，该观察项提交下一轮裁决**。此差异已同步 team-leader。
**→ 该差异已由 §14.2 Amendment 2 消除**：`L-10` 分子 `> 0` 恢复为独立击穿条件 (b)，与 `R28 §3.6` 的「保守方向」一致，不再需要让报告迁就预登记。

**可核证据（落盘时刻实跑）**

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
grep -rn "ADDR_EVOLVE" code/ tools/     # → 无输出，退出码 1（零命中 ⇒ 开关未实现 ⇒ 不可能有 ON 臂读数）
git log -1 --format='%h %H %ci %s'      # → 46d18a8 46d18a8a41ff… 2026-10-30 22:09:23 +0800 R28: 称呼×关系演化收口…
git rev-parse HEAD                      # → 46d18a8a41ffc36b05f5cec55c56923c1ea2d761
```

**本 Amendment 的改动面**：仅本文件 `v2/refs/N15-prereg-addr-evolve-20261030.md` 的 §5.2（`G2` 行拆为 `G2` + `G2-附` 两行）与本节 §14/§14.1。**未动 `code/`、未动 `tools/`、未动 `v2/evidence/`、未 commit**（按 team-leader 指令，由下一轮跑批前的报告收口环节一并入库，避免与本轮已交付的 `46d18a8` 混淆）。

### 14.2 Amendment 2 —— 恢复 `L-10` 分子 `> 0` 为独立击穿条件（跑前修订）

**性质**：**跑前修订**。落盘时全仓 `grep -rn "ADDR_EVOLVE" code/ tools/` **仍零命中**（退出码 `1`）、**无任何 ON 臂读数**、**N-15 未起任何跑批**、开关仍未实现。
**修订日期**：2026-10-30 22:1x +0800。**经 team-leader 二次裁决**后落盘（首次裁决见 §14.1）。

**推理链（Amendment 1 → Amendment 2，写清为什么改两次）**：
> **Amendment 1 删掉 `L-10` 子句，是因为它当时的位置是「必要条件」（原文「`ON − OFF ≤ +2.0pp`，**且 `L-10` 方向不上升**」）。作为必要条件，`L-10 ≡ 0` ⇒ 该条件恒成立 ⇒ **空条件、无判别力**，删掉是必要的。
> **Amendment 2 恢复 `L-10`，但改写为「击穿条件」并取「绝对非零」，是因为它作为击穿条件并不空**：`L-10` 分母 165–174，分子一旦从 `0` 变为 `> 0`，意味着居民**用第一人称把自己说成了别人的名字**（`我(是|叫|乃|就是)?<他人名>`）。这是**真实的错误信号**，必须能击穿；把整条子句一起删掉等于关掉一个真实错误通道，属**判据能力净损失**。
> 措辞上取「**分子 `> 0`（绝对非零）**」而**不取「上升」**：基线 5 份日志分子恒 `0`，二者在本场景等价，但「上升」会被误读为相对量（如「相对 OFF 臂上升」），而 `0→1` 这种绝对非零才是要拦的东西。

**改了什么（只此一处，共两条 OR）**

| # | 击穿条件（并列 OR，任一成立即击穿） | 阈值 |
|---|---|---|
| **(a)** | 自定义口径 `addr_error_rate`（自称 + 错称第三者） | `ON − OFF ≥ +3pp` |
| **(b)** | 官方 `L-10 self_address_error`（`tools/d5/dialogue_metrics.py:919-932`） | **分子 `> 0`（绝对非零）** |

**保持不变（照 Amendment 1 原样）**：`L-10` **不进**任何「必须不升」之类的**必要条件**；仍为**并列披露项**（同屏出现、供读者自查）；强制同屏句（§5.2 `G2-附`）继续有效；`addr_error_rate` 的温和线 `ON − OFF ≤ +2.0pp` 仍作为**描述性判读参照**（不单独作击穿条件）。
**§14.1 的「唯一击穿条件」表述就此作废**，以本节两条 OR 为准。

**显式未改动清单（在 §14.1 那份基础上追加一行）**：主判据 `S-1 = addr_swing_pairs_rate` 及其统计单位/分子/分母定义、可检出线 `Δ ≥ +20pp`、`J-1`…`J-9` 判定格、护栏 `G1` / `G3` / `G4` / `G5` / `G6` / `G7`、§6 分母纪律与降级措辞、§7 双臂设计、§8 实现约束、§8.3 的 L3 收窄声明、§9 不可判格、§13 硬边界 —— **一律未动**；
**追加一行**：**Amendment 2 只动 `G2` 的击穿条件 (b) 这一条，其余（含 Amendment 1 的其余表述与全部其它判据）全部不动。**

**可核证据（本节落盘时刻实跑）**

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
grep -rn "ADDR_EVOLVE" code/ tools/     # → 无输出，退出码 1（零命中 ⇒ 仍无 ON 臂读数）
git rev-parse HEAD                      # → 46d18a8a41ffc36b05f5cec55c56923c1ea2d761（本轮未再 commit）
```

**本 Amendment 的改动面**：仅本文件 §5.2 的 `G2` 行、§14 表新增 `A-2` 行、§14.1 两处标注（「唯一击穿」格子划掉 + 差异段补「已由 A-2 消除」）、以及本节 §14.2。**未动 `code/`、未动 `tools/`、未动 `v2/evidence/`、未 commit、未跑批。**

---

## 附录 A · 本文件用到的实测读数与命令输出（逐条可原位重放）

| # | 目的 | 命令 | 观察结果 |
|---|---|---|---|
| A1 | 开关是否已实现 | `grep -rn "ADDR_EVOLVE" code/ tools/` | 退出码 **1**（零命中） |
| A2 | 凭据已配置（不打印值） | `awk -F= '/^[A-Za-z_]+=/{print $1" : len="length($0)-length($1)-1}' code/.env.local` | `HITT_LLM_PROVIDER : len=13`、`LLM_API_KEY : len=32` |
| A3 | 凭据不入库 | `git check-ignore -v code/.env.local` | `code/.gitignore:11:.env.local` |
| A4 | 端点可达 | python socket `connect(("172.16.3.41",31809))`，timeout 5s | **OK** |
| A5 | 尺子/词表身份 | `sha256sum tools/metrics/address_drift.py v2/refs/address-ordinal.yaml` | `37a5dc52…` / `dc4ce327…` |
| A6 | 尺子自检 | `python3 tools/metrics/address_drift.py --selftest` | `PASS (failures=0)` |
| A7 | 分母探针（§11.3） | `python3 tools/metrics/address_drift.py --log v2/evidence/run_d1_f6on_seed42_n16r84/run.jsonl --arm PROBE_N16R84 --out-json /tmp/probe_n16r84.json --out-md /tmp/probe_n16r84.md` | `686 MSG`；`switch 1/43`；`stage 50（升0/平50/降0）`；`vocab 56`；`cov 38.92%`；`err 2/198` |
| A8 | 单臂规模/成本锚 | `cat v2/evidence/run_d1_f6on_seed42_n16r84/{meta.json,llm_cost.txt,batch_timing.txt}` | `3403 calls`、`778689 tokens`、`2873 s`、`cached 1666` |
| A9 | `dialogue` 真调用率（G6 依据） | 按 `purpose=='dialogue'` 统计 5 份 D10 臂 + 1 份 r84 臂 | `d9m-off 0/191`、`d9m-on 19/191`、`d9s-off 7/191`、`d9s-on 93/191`、`round1 191/191`、`n16r84-on 714/714` |
| A10 | `prompt_hash` 存在（M3 依据） | 读 `v2/evidence/d9m-ab-off_n16r24_s42/run.jsonl` 首条 `LLM_CALL` | `payload.prompt_hash = sha256:cee606b4…` |
| A11 | `examples` 上限（§3.1 依据） | `grep -n "examples" tools/metrics/address_drift.py` | `:320 if len(switch_examples) < 20` |
| A12 | 接线件硬编码（§8.1 依据） | `python3 tools/d9/prompt_fn_sha.py --help`；`sed -n '60,115p' tools/d9/prompt_fn_sha.py` | 只有 `--code-root/--exit-on-same`；`:66` 设 `HITT_D12_PREFWORD`、`:85` 取 `_d12_prefword_line` |
| A13 | 无并发跑批 | `pgrep -af "orchestration run\|run_batch\|nightly\.py"` | 仅命中查询自身 |
| A14 | 树身份 | `git rev-parse HEAD`；`git branch --show-current` | `2ad74a56c7d8570bfd10d7b55e55ce40ecc8bac6`；`feat/round-D10-address-drift` |

**本轮文件改动**：仅新增本文件 `v2/refs/N15-prereg-addr-evolve-20261030.md`。`code/`、`tools/`、`v2/evidence/`、其它 refs 一字未动；未 commit。
