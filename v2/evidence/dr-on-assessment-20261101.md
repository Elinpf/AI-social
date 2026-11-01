# DR-on 前置评估（误解与和解 / F-4）：开它改什么 / 能否单变量 / 可测面 / 代价 / 判据前置

只读评估（代码树 `feat/d9z-intra-round @ 43a56c1`，基 `cef1c58`）。**未改 `code/`、未改 `config/`、未跑批、未调真 LLM。**
结论允许是"不该开"；本件**不含任何"开了会更有生活气息"的判断**（未测）。

---

## 0. 现行状态（已定事实，仅核对未重查）

| 项 | 值 | 来源 |
|---|---|---|
| 总开关 | `enabled: false` | `code/config/dialogue_repair.json:5` |
| 子开关 | `gripe_context: true`、`reply_priority: true` | 同上 `:6-7` |
| 参数 | `window_msgs 8` / `max_open 3` / `max_age_rounds 84` / `context_max_age_rounds 24` | 同上 `:8-11` |
| env 逃生口 | `HITT_DIALOGUE_REPAIR=1|0` | `life/dialogue_repair.py:102-105` |
| 指纹 | 该配置文件**不进** `engine_version` 指纹（刻意） | 配置文件 `_comment`；模块 docstring |

⇒ D9z 那批未设 env ⇒ 机制整体未生效（`ingest` 首行 `if not params.get("enabled"): return`，`dialogue_repair.py:156`）。

---

## Q1 开 DR 会改变什么：**3 类输入被改 + 1 类日志被改 + 2 类不变量**

### 1.1 会被改的输入

| # | 改什么 | 具体位置 | 触发条件 |
|---|---|---|---|
| A1 | **回复提示词**：追加"处境 + 选项工具箱" | `agent.py:1340-1343` → `DR.context_line()`（`dialogue_repair.py:226-247`） | `enabled` ∧ `gripe_context` ∧ 有相关 rift ∧ `age ≤ context_max_age_rounds` |
| A2 | **回复提示词**：追加"这一句把话说开"的**动作要求** | `agent.py:1344` → `DR.repair_ask()`（`dialogue_repair.py:267-289`） | **只看 `enabled`**（无独立开关！）∧ 本线程有 rift ∧ `age ≤ 24` |
| A3 | **发起提示词**：追加同一段"处境" | `agent.py:1416-1417` → `DR.context_line(..., params=dr_cfg)` | 同 A1，且 `to` 非空 |
| B1 | **回复对象选择顺序**：优先挑"有旧账的线程" | `agent.py:1143-1145`（`prefer = DR.threads_with_open_rift(...)`）→ `_pick_reply_target(..., prefer_threads=prefer)` → `agent.py:1196-1197` `if prefer_threads and tid in prefer_threads: return ev` | `enabled` ∧ `reply_priority` |
| B2 | **台账**：`self._rifts` / `_rifts_seen` 开始累计 | `agent.py:1135-1138`（每回合 `DR.ingest`）、`agent.py:662-672`（`restore()` 前向重建） | `enabled` |

### 1.2 会被改的**日志内容**（不是提示词）

| # | 新增 payload 字段 | 位置 | 触发条件 |
|---|---|---|---|
| C1 | `dialogue_rift{v:"f4/1", open, with, threads, route, age_rounds, prompted}` | `agent.py:1372-1377`（reply）、`1430-1434`（initiate）→ `DR.audit_fields()` | **只看 `rifts` 非空**（`audit_fields` 内 `if not rifts: return None`）——**与 `gripe_context` 无关** |
| C2 | `dialogue_repair{v:"f4/repair/1", thread, rift_ids, trigger_seqs, peers, age_rounds, prompted}` | `agent.py:1379-1381` → `DR.repair_audit()` | 本线程有 rift（**不检查 `enabled`**，靠台账为空自然短路） |

> **关键含义**：只要 `enabled=1`，即使把 `gripe_context` 与 `reply_priority` 都关掉，**MSG 事件的 `payload` 仍会多出 C1/C2 字段** ⇒ **事件内容变化 ⇒ 哈希链必然变化**。这使"OFF 与 ON 用 hash 链做等价性证明"这类手段在本机制上**不可用**（与 D9z 的情形不同：D9z 关时是逐字节等价）。

### 1.3 不变量（一字不变）

| 不变量 | 依据 |
|---|---|
| **不生成、不改写任何正文** | 模块 docstring「本模块**不生成、不追加、不改写任何正文**」；全文件无 LLM 调用、无 `body` 赋值 |
| 关闭时提示词与日志**逐字节不变** | 三个入口首行都 `if not params.get("enabled") …: return None`（`context_line:233`、`repair_ask:277`、`ingest:156`），`audit_fields` 空台账返回 `None`（`agent.py` 侧 `if f is not None` 才挂键，`1374/1431`） |
| 不进 `state_hash` | docstring「**不进 state_hash**：纯措辞/上下文层，不产生事件类型、不改世界态」 |
| 不改世界数值/经济 | 台账与提示词均为只读派生；事件类型上只**新增字段**，无新事件类型 |

---

## Q2 单变量性：**本机制在"不改代码"的前提下不可单变量测**

### 2.1 三个可调自由度实际只有两个半

| 自由度 | 可独立关？ | 证据 |
|---|---|---|
| `reply_priority`（选择行为 B1） | ✅ 可单独关 | `agent.py:1144` `if dr.get("enabled") and dr.get("reply_priority")` |
| `gripe_context`（处境 A1/A3） | ✅ 可单独关 | `context_line:233` 检查 `gripe_context` |
| **`repair_ask`（动作要求 A2）** | ❌ **不可单独关** | `repair_ask:277` **只查 `enabled`**，不查任何子开关 |

⇒ **只要 `enabled=1`，回复路径就必然可能注入 A2 的动作要求**（"这一句把话说开…一句家常话把台阶递出去"），无法与 A1 的"处境"分开实验。

### 2.2 因此"提示词 vs 选择行为"**不能完全分离**

能做的最大拆分（不改代码）：

| 臂 | `enabled` | `gripe_context` | `reply_priority` | 实际发生什么 |
|---|---|---|---|---|
| OFF | 0 | — | — | 全静默 |
| 只关选择 | 1 | 1 | **0** | A1+A2 提示词 + C1/C2 日志；**无** B1 |
| 只关处境 | 1 | **0** | 1 | **A2 仍在**（提示词仍被改）+ C1/C2；有 B1 |
| 全开 | 1 | 1 | 1 | A1+A2+B1+C1/C2 |

⇒ 得到的对照只能回答「**选择优先级的增量**」（`只关选择` vs `全开`），**不能**回答「处境提示是否有效」（因为 A2 永远在场，且 A2 本身就是强干预）。
**按卡面要求明写：本机制"提示词干预"与"选择干预"不可完全分离；`repair_ask` 与 `enabled` 不可分离 ⇒ 本机制不可单变量测。**

### 2.3 还有一条隐性耦合（与 D9z 交互）

`DR.ingest()` 读的是 `wv.visible_events`（`agent.py:1137`）⇒ 在 `HITT_INTRA_ROUND_VISIBILITY=1` 的世界里，**同轮消息也会立刻进台账**，rift 建立时点比 D9z-off 世界更早。
⇒ 若在"五开关+INTRA"的臂上开 DR，**DR 的效应会与"同轮可见"耦合**（rift 更早可触发）。要做干净的单变量，DR 的 OFF/ON 两臂必须**同 INTRA 设置**（可以，但要在登记里写明，且不能与 D9z 的结论混算）。

---

## Q3 可测面：开启后能算的量（分子/分母）+ 缺什么字段

### 3.1 直接可算（用 `dialogue_rift` = C1）

| 量 | 分子 | 分母 | 备注 |
|---|---|---|---|
| **处境注入率（reply）** | `dialogue_rift.prompted == true` 的 MSG 数 | `payload` 含 `dialogue_rift` 的 MSG 数 | ⚠ `audit_fields.prompted` 由 `_prompted()`（`dialogue_repair.py:320-325`）算，**只反映 `gripe_context`+年龄，不反映 `repair_ask`** ⇒ 这条**不能**当"提示词被改过"的充分证据 |
| **选择干预命中率** | `dialogue_rift.route == "reply_priority"` 的 MSG 数 | 全部 MSG 数 | 需注意：`route` 由调用方传入（`agent.py` 里 reply/initiate），**"reply_priority" 这个取值只在加油门的实现里出现；本树 `agent.py:1374` 传的是 `"reply"`** ⇒ **`route` 目前区分不出"是否被优先选"**，这是缺字段（见 3.3） |
| **rift 覆盖率** | `dialogue_rift.open > 0` 的 MSG 数 | 全部 MSG 数 | `open` 是"我这个 agent 此刻未了结 rift 数" |
| **rift 年龄分布** | `dialogue_rift.age_rounds` 的直方图 | — | 判断"旧账是否长期悬置" |
| **涉事对端/线程覆盖** | `with` / `threads` 的去重计数 | agent 总数 / 线程总数 | |

### 3.2 可复算（用离线重放，**不需要新字段**）

`DR.ingest_one()` 是**纯函数**（只依赖 MSG 的 `seq/from/thread_id/body`，`dialogue_repair.py:168-196`）⇒ 可以在**离线**用同一规则重放 `run.jsonl`，得到：

| 量 | 分子 | 分母 |
|---|---|---|
| **rift 登记总数** | 重放后累计登记过的 rift 条数 | — |
| **和解率（词表层）** | 被"同线程后续出现修复词"注销的 rift 数 | 登记总数 |
| **平均悬置时长** | Σ(注销轮次 − 登记轮次) | 注销数 |
| **未了结率** | 期末仍 open 的 rift 数 | 登记总数 |
| **触发/回复配对** | `dialogue_repair.trigger_seqs` 与回复事件 `seq` 的配对 | — |

⚠ 边界：和解判定**完全由 `REPAIR_WORDS` 词表**（14 词，`dialogue_repair.py:68-71`）驱动，`NEG_WORDS` 18 词（`:60-64`）驱动张力判定；两表都是 `tools/d5/*_lexicon.txt` 的**子集镜像**（有单测 `test_lexicon_mirror_is_subset` 守漂移）。⇒ 这些量是**词表层**结论，不能升格成"关系真的修复了"。

### 3.3 缺字段（若要更细，需新字段；三条都不难）

| 缺什么 | 为什么缺 | 影响 |
|---|---|---|
| **"本回合是否被 `reply_priority` 优先选中"** | `audit_fields(route=...)` 的 `route` 目前只有 `reply`/`initiate`（`agent.py:1374/1431`）；`_pick_reply_target` 里 `prefer_threads` 命中时**不返回任何标记**（`agent.py:1196-1197` 直接 `return ev`） | 无法把"选择顺序改变"与"提示词改变"造成的差异归因 |
| **`repair_ask` 是否注入** | `dialogue_rift.prompted` 只跟 `gripe_context` 有关；`dialogue_repair.prompted` 是 `bool(repair_line)`（`agent.py:1379`）——**这个才是 A2 的真标记**，但它只在 `dialogue_repair` 存在时才出现 | 想单独统计"A2 注入率"需读 `dialogue_repair.prompted`，且分母应是"reply 路径 MSG 数"，不是全部 MSG |
| **rift 注销事件** | 注销发生在 `ingest_one` 内部 `rifts.pop`（`:190-194`），**不产生事件** | 和解**时点**无法从日志直接读，只能离线重放推断（3.2 已覆盖，故非阻塞） |

---

## Q4 代价

### 4.1 提示词变长（实测字符数，非估算）

| 段落 | 字符数 | 生成位置 |
|---|---|---|
| `context_line`（处境 + 工具箱） | **78**（其中 `TOOLBOX` 30 字） | `dialogue_repair.py:226-247`，`TOOLBOX` 在 `:56` |
| `repair_ask`（动作要求） | **70** | `dialogue_repair.py:267-289` |
| **reply 路径合计** | **+148 字符** | A1+A2 |
| **initiate 路径合计** | **+78 字符** | A3 |

token 换算（保守上界，中文≈1 字 1 token）：reply **≈ +150 tokens/次**、initiate **≈ +80 tokens/次**。
对照本批实测（D9z ON 臂 `16×56`）：`dialogue` 444 次、`tokens_in` 合计 411457（均值 ≈ 927/call）⇒ 若 444 次中一半带 rift，增量 ≈ 222×150 ≈ **33k tokens（≈ +8%）**。**这是上界估算，未实测**。

### 4.2 是否重新引入"变多"旁路

| 机制 | 会不会改 `MSG` 总量 | 理由 |
|---|---|---|
| A1/A2/A3（提示词） | **可能会**（间接） | 措辞变化 ⇒ 后续 `is_replyable`/线程走向变化 ⇒ 二次效应；D9z 已见过 `MSG 191→444` 的旁路 |
| B1（`reply_priority`） | **一定会**（直接） | `if prefer_threads and tid in prefer_threads: return ev` 会**越过** `fallback`（`agent.py:1196-1198`）⇒ 改变"这回合回复哪条线程"，进而改变线程长度与发帖节奏 |

⇒ **必须把 `MSG` 总数当护栏报**，否则无法区分"和解变多"与"话变多"。

### 4.3 需要几次跑批才能单臂可比

- 每臂成本基准：D9z 实测 `16×56` = **2725.7 s（45.4 min）**。
- **不改代码**（最大拆分 = 2 臂：`只关选择` vs `全开`）：**2 次真批 ≈ 91 min**，且**只能回答选择干预的增量**。
- **改代码加开关**（`repair_ask` 独立开关 + `route` 标记）：3 臂（纯记录 / 记录+处境 / 全开）**≈ 136 min**，能回答"提示干预 vs 仅记录"。
- **OFF 臂不可复用 D9z 那批**（那批 `OPENINGS=1`+`INTRA=1`，世界不同）⇒ OFF 必须同配置重跑 1 次（已含在上面计数里）。

---

## Q5 判据前置：若真要开，必须先立这些护栏

| # | 护栏 | 阈值/写法 | 为什么必须 |
|---|---|---|---|
| G1 | **`MSG` 总数各臂并列报** | 绝对数（如 ON 444 / OFF 191 那样），**不得只报比例** | 防"变多"旁路被读成"和解变多" |
| G2 | **单条字数中位不降** | ≥ 基线 **66**（D9z 实测两臂一致） | 防"话变碎" |
| G3 | **`<7 字` 占比不升** | 基线 **0**（两臂均 0）⇒ 只能维持 0 | 防电报体 |
| G4 | `degraded == 0`、`dialogue` 回放 == 0 | 与既有门一致 | 防降级批/缓存重放冒充 |
| G5 | `code/config/places.json`（内容 sha·实测值） sha 两臂一致；`n` 一致 | `c36c0f87…` | 防改配置/缩样本 |
| G6 | **rift 台账覆盖的可复算性** | 离线重放 `ingest_one` 必须复现 `dialogue_rift.open` | 证明"日志里的字段是真的"（否则 C1 只是自述） |
| G7 | **两臂 `INTRA_ROUND` 设置一致** | 显式声明 | 否则 DR 效应与"同轮可见"耦合（Q2.3） |

---

## 我的建议

**先补 X 再谈** —— 具体是补三样，再决定开不开：

1. **给 `repair_ask` 一个独立开关**（或 `enabled` 增加 `record_only` 模式），否则"处境提示"与"动作要求"永远同进同出，实验上无法归因；
2. **在 `_pick_reply_target` 命中 `prefer_threads` 时给一个可落盘的标记**（如 `payload["dialogue_rift"]["route"]="reply_priority"`），否则选择干预的效果无法与提示干预分离；
3. **`MSG` 总数 + 单条字数中位 + `<7 字` 占比** 三条护栏写进预登记（G1–G3），因为在 B1 明确会改 `MSG` 量的情况下，不先立这几条，任何"和解变多"的读法都站不住。

**理由**：本机制当前是"三处干预捆在一起、且日志内容变化导致 hash 链不能用作等价性证据"的形态；在 D9z 已经暴露"判据过但方向疑 + 变多旁路"之后，再上一层**不可分离**的干预，很可能重演"通过判据却说不清是什么在起作用"。修上面三样只是加开关+加一个字段，成本远低于跑 3 臂真批（≈2.3 h）之后再回头发现归因不了。

---

## 边界

- 未改 `code/`、未改 `config/`、未跑批、未调真 LLM。
- 字符数（78/70/148/78）为 `python3 -c` 实测该函数输出长度；token 为**换算估算**，未实测。
- 所有代码位置以 `feat/d9z-intra-round @ 43a56c1` 为准；行号随代码改动可能漂移，引用时以函数名为锚。

---

## 附录：Leader 裁决（2026-11-01 15:4x）

**采纳出件方建议：本阶段不开 DR，先做"可分离化"。**

**理由（按重要性）**：
1. **不可单变量**：`repair_ask()` 内部**只查 `params["enabled"]`**（`code/life/dialogue_repair.py`）⇒ 只要开 `enabled`，"动作要求"（A2）必然在场，与被 `gripe_context` 控制的"处境"（A1）**分不开**。能拆的最大幅度仅 `reply_priority` 开/关（2 臂），且两组都仍带 A2 + C1/C2。
2. **等价性证据失效**：开 DR 会改**日志内容**（`dialogue_rift` / `dialogue_repair`），而 `audit_fields` 只看 `rifts` 非空、与 `gripe_context` 无关 ⇒ **hash 链不能再当等价性证据**。这一点在 D9t/D9z 两轮里是主要防线。
3. **代价不低**：`context_line` 78 字符 + `repair_ask` 70 字符，reply 路径 **+148 字符（≈+150 tokens/次，估算）**；每臂 45.4 min，**OFF 不能复用 D9z 批**（`OPENINGS`/`INTRA` 不同）⇒ 3 臂 ≈136 min。
4. **当前最贵的不是跑批，是归因不清**：D9z 刚暴露"判据过但方向疑"，此时再叠加三重不可分离干预，**很可能重演"过判据却说不清是什么在起作用"**。

**下一步（已派 `T-DR-SEPARATE`）**：给 `repair_ask` 独立开关（或 `record_only` 模式）+ `prefer_threads` 命中落可读标记，**默认关、关闭时逐字节不变**，再加 mock 自证。**做完才谈预登记。**
