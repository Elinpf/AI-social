# D4 判据落地试算（D4-1 机制到位率 / D4-2 和解率）—— 只读、零跑批

脚本：`tools/dr/d4_rates.py`（离线重放 `DR.ingest_one()`，无 LLM、无跑批、不改 `code/`）
本件 = 口径件 + 三批试算 + 自检 + 判断。**不含任何效果结论。**

---

## 1. 口径（三件齐：`value` / `undefined_reason`（可核）/ `positive_control`）

### 1.1 两个率的定义

| 率 | 分子 | 分母 |
|---|---|---|
| **D4-1 机制到位率** | `dialogue_repair.prompted == true` 的 MSG 条数 | 该 agent **存在未了结 rift** 的 MSG 条数 |
| **D4-2 和解率** | 同线程后续出现**修复词**而注销的 rift 数 | **登记**的 rift 数 |

### 1.2 「未了结（open）」的时点口径（写死）

> 处理到 `seq = e` 的 MSG 时，若**发言方** agent 的台账在**吸收完所有 `seq < e` 的可见 MSG 之后**
> 仍非空（`len(rifts[agent]) > 0`），则称"该条 MSG 生成时存在未了结 rift"。

依据：运行期 `_communicate()` 是**先 `DR.ingest(可见事件)` 更新台账，再挑目标/生成消息**（`agent.py`），
所以"生成时"= 已吸收前序可见消息之后。

### 1.3 可见性口径（与运行期一致）

按 `perception_scope` 语义：`MSG_PUBLIC = global`（人人可见）、`MSG_DM = private`（仅 `from`/`to`）、
`MSG_GROUP = members`（`participants` 内）。MSG 三类**不依赖 `place`**，故无需 location。

### 1.4 `分母=0` 的处理（硬规则）

分母为 0 时输出 `{"numerator":…, "denominator":0, "value": null, "status": "undefined", "undefined_reason": "…"}`。
**绝不输出 `0.0` / `0%`**。（`selftest.case3` 验证了这条路径确实返回 `value=None`。）

### 1.5 两个口径必须分开报（否则会把"没数"读成"0"）

| 口径 | 数据来源 | 含义 | 能否给比值 |
|---|---|---|---|
| **A（批内可观测）** | MSG 上的 `dialogue_rift` / `dialogue_repair` 字段 | **该臂运行期的真值** | D4-1 可以（分子分母都来自字段） |
| **B（离线重放）** | `DR.ingest_one()` 重放（**须 `enabled=True`**） | **"若开 DR，这批会有多少旧账"的预估** | 只给 D4-1 的**分母**（批内无 `prompted` 字段 ⇒ 分子不可观测）；D4-2 用重放算 |

⚠ 重放若用 `enabled=False`（配置默认），`ingest_one` 首行直接 return ⇒ 台账恒空，
会把**"重放没开"**误当成**"批里没有负向话"**。脚本内已强制 `enabled=True` 并注明。

---

## 2. 三批试算（只读，零 LLM）

| 批次 | 事件 | MSG | **口径 A**：`dialogue_rift` 字段数 → D4-1 | **口径 B**：登记 / 注销 / prune / 期末 open → D4-2 | 口径 B 的 D4-1 分母预估 |
|---|---:|---:|---|---|---:|
| `v2/evidence/d9z-on_n16r56_s42`（真 LLM，DR **关**） | 90532 | 444 | 0 → **undefined**（分母 0） | **83 / 0 / 34 / 49** → **0.0**（分母 83≠0，0% 合法） | **434** |
| `d9z_rehearsal_n16r56`（mock 16×56，DR 关） | 91091 | 444 | 0 → **undefined** | 0 / 0 / 0 / 0 → **undefined**（分母 0） | 0 |
| `dr_new2_out`（mock 16×8，DR 关） | 7541 | 80 | 0 → **undefined** | 0 / 0 / 0 / 0 → **undefined**（分母 0） | 0 |

### 2.1 口径 A 全是 `undefined` —— **符合预期，不是口径错**

`dialogue_rift` / `dialogue_repair` **只在 `enabled=1` 时出现**。三批 DR 全关 ⇒ 字段数 = 0
⇒ 分母 0 ⇒ D4-1 在**这些臂**里未定义。这正是"DR-off 世界里 D4 无从读起"的可核证据。

### 2.2 口径 B 在真批上给出非平凡数（**这是预估，不是该臂读数**）

- 台账自洽校验：**83（登记）= 0（注销）+ 34（超 `max_open`/`max_age` 丢弃）+ 49（期末 open）** ✅
  —— 这条恒等式是"重放重建正确"的强证据。
- **D4-2 = 0/83 = 0.0**（分母非 0，读数合法）。
- **D4-1 分母预估 434**：444 条 MSG 中 434 条在"发言时已有旧账"状态下生成
  ⇒ 若开 DR，处境注入的机会面**很大**。⚠ 这只是分母，**不给比值**（分子不可观测）。

### 2.3 为什么 D4-2 的分子是 0（已核实，不是脚本 bug）

对三批逐条扫 `REPAIR_WORDS`（14 词）/ `NEG_WORDS`（18 词）：

| 批次 | MSG | 负向话（`is_gripe`） | **修复词命中（`has_repair`）** |
|---|---:|---:|---:|
| `d9z-on_n16r56_s42`（真 LLM） | 444 | **27** | **0**（14 词一个都没命中） |
| `d9z_rehearsal_n16r56`（mock） | 444 | 0 | 0 |
| `dr_new2_out`（mock） | 80 | 0 | 0 |

⇒ D4-2 分子恒 0 的原因是**语料里没有修复词**，不是注销逻辑坏了（注销路径由 `selftest.case1` 证明可用，见 §3）。

---

## 3. 自检（构造台账，证明"装置能出声"）—— 与真数据结果分开报

```
selftest_ok = true
case1_register_then_repair: registered=1, resolved=1, rate=1.0     ← 注销路径可用
case2_register_no_repair:  registered=1, resolved=0, rate=0.0      ← 分母≠0 时 0% 是合法读数
case3_no_rift:             registered=0, resolved=0, status=undefined, value=None  ← 分母=0 显式未定义
case4_d41_shape:           numerator=2, denominator=3, value=0.666667  ← 比值形状可算非平凡值
```
⇒ 三个关键分支（注销、0%、未定义）**都被真实触发过**，不是装饰。

---

## 4. 判断：D4 判据**能不能立**

**结论：D4-1 可以立；D4-2 可以立，但当前语料下它没有分辨力，必须先解决"分子恒 0"再谈。**

1. **D4-1（机制到位率）可立**：口径 A 有定义（DR-on 臂里分子分母都来自字段），口径 B 给出机会面预估（真批 434/444）。
   但**它的读数只在 DR-on 臂存在**，OFF 臂必然 `undefined` —— 即它**只能臂内读，不能跨臂比**（与裁定一致）。
2. **D4-2（和解率）形式上可立，实质上当前不可判**：
   - 真批 444 条里修复词命中 **0**、负向话 27 ⇒ `0/83` 这个 0 **无法区分**两种情形：
     (a) DR 没诱导出和解；(b) 诱导了但措辞不在 14 词表内。
   - ⇒ 若直接拿 `D4-2 = 0` 进判据，等于**用词表覆盖度冒充机制效果**。这与 D9h 的"召回 0/14"是同一类问题。
   - **最小补救**（不需跑批）：D4-2 必须**并排报告"修复词命中条数"与"分母"**，并明确"0 的两种解释不可区分"；
     若要能区分，得先补词表覆盖度（那是另一件事，属 D9u 线）。
3. **因此我的建议**：**先只用 D4-1 作为本臂判据**（它不依赖词表、口径干净），**D4-2 降级为"并排报告项"**，
   不作为通过/不通过的依据 —— 否则跑完 91 分钟，最可能的结论仍是"0 vs 0，说不清"。

---

## 5. DR-on 三批实证（**关键补充：判据能不能当真判据，看这一节**）

> 由 leader 扫描 114 批发现的三批 **DR 已开**历史数据（未入库，本机可复算；本卡导出了可入库切片，见 §5.1）。
> 命令：`python3 tools/dr/d4_rates.py --log <三批> --export-slice ...`；原始输出 `v2/evidence/d4-rates-dron-batches.json`。

| 批次 | MSG | `dialogue_rift` | `dialogue_repair` | open>0（reply/initiate） | **D4-1 全口径 / reply-only** | 词命中（负向/修复） | **D4-2**（注销/登记） | 台账自洽 |
|---|---:|---:|---:|---|---:|---|---:|---|
| `run_f4_on_n16r60_seed42` | 504 | 41 | 22 | 41（39/2） | **0.5366 / 0.5641** | 19 / **20** | **0.1212**（4/33） | 33=4+3+26 ✅ |
| `emo-on-20261029` | 192 | 31 | 12 | 31（25/6） | **0.3871 / 0.4800** | 9 / **8** | **0.1304**（3/23） | 23=3+0+20 ✅ |
| `run_r6_treat_n16_seed42` | 683 | 139 | **0（键不存在）** | 139（128/11） | **undefined**（分子不可观测） | 71 / **28** | **0.1566**（26/166） | 166=26+94+46 ✅ |

### 5.1 三个结论

1. **D4-1 有分辨力，能当真判据**：两批字段完整的 DR-on 臂给出 **0.39 / 0.54**（reply-only 0.48 / 0.56），
   **不是退化值**（既非恒 0 也非恒 1）。⇒ 它可作为"机制到位率"的臂内读数。
   ⚠ 但 `dialogue_repair` 只在 **reply** 路径存在，故**全口径会被 initiate 稀释**（0.5366 vs 0.5641、0.3871 vs 0.48）
   ⇒ 报数时应给 **reply-only 为主、全口径为下界**。
2. **D4-2 也能当真判据**：三批 0.1212 / 0.1304 / 0.1566，且**修复词命中非 0**（20 / 8 / 28）
   ⇒ 之前 `d9z-on` 的 `0/83` 是**那批语料里修复词命中 0**，**不是判据恒 0**。
   ⚠ 边界仍要写死：D4-2 的上限由 `REPAIR_WORDS`（14 词）覆盖度决定，**必须并排"修复词命中条数"**。
3. **`run_r6_treat` 的"139 rift 却 0 repair" 解释**：该批 MSG 上**根本没有 `dialogue_repair` 键**
   （`field_presence.dialogue_repair_not_observable = true`，代码版本早于 R13）
   ⇒ **不是"没和解"，是"该通道不可观测"**。脚本对此判 `undefined`（**若算成 0.0 就是"字段缺失伪装成 0%"**）。
   而**重放口径能补上这一格**：D4-2 = 26/166 = 0.1566（该批词命中修复词 28 条，和解确实在发生）。

### 5.2 可入库切片（复算底稿）

| 文件 | MSG | 字节 | sha256 前缀 |
|---|---:|---:|---|
| `v2/evidence/d4-rates-slices/run_f4_on_n16r60_seed42.json` | 504 | 123157 | `7f162b8105986d1c` |
| `v2/evidence/d4-rates-slices/emo-on-20261029.json` | 192 | 49849 | `bdbd5d0cbf55f721` |
| `v2/evidence/d4-rates-slices/run_r6_treat_n16_seed42.json` | 683 | 179686 | `ec1492f5f0e34826` |

字段：`msg_uid / seq / round / type / author / thread_id / reply_to / dialogue_rift{prompted,open,route,with,threads,age_rounds} / dialogue_repair{prompted,rift_ids,trigger_seqs,thread}`。
**不含 `body`**（体积与隐私）⇒ 词命中类指标无法由切片复算，需原 `run.jsonl`；D4-1/D4-2 主判据**可由切片复算**。

## 6. 边界

- 只读脚本；**未改 `code/`、未跑真批、未写预登记**。
- 口径 B 是**重放假想值**（`enabled=True`），不是该臂运行期读数；引用时必须带"口径 B"标签。
- 「0%」与「未定义」严格分开：本件所有 0 都注明是"分母≠0 的 0"还是"分母=0 的未定义"。
- 数据边界：`d9z-on_n16r56_s42` = `16 agents × 56 rounds × seed 42`、`cef1c58` 系代码 + D9z 五开关 + `INTRA=1`、DR 关。
