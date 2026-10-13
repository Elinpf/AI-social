# 变更分类「四档」可判定口径（供 `T300`/`T352`/`T355`/`T361`/`T370` 收口引用）

> 类型：口径页（只读 `v2/refs/`，**不占重活、不受 `T355` 冻结限制**）｜ 作者：`sim-engine-stats-architect`
> 用途：**收口/归类时直接引用，免"到底是哪一档"的争执**。对齐 `T360` 已立的"仅日志增"兄弟类、`08 §5.10` 与 `T299` 的语义门口径。
> 一句话：**先走口径（三轴），再看字节**；**"逐字节不等" ≠ "语义不等"**。

---

## 0. 三条【独立轴】（所有混淆的根）

| 轴 | 是什么 | 由什么决定 | 怎么读 |
|---|---|---|---|
| **世界态轴** = `state_hash` | **折叠世界态**（`apply_event` 全量折叠后的 `WorldState`）的哈希 | 事件的**语义**（fold 结果） | 同 seed 跑 → 比 `state_hash(state)`；亦看 `TURN_SEAL.state_hash` |
| **日志轴** = 哈希链 | **每条事件记录**（`compute_event_hash` 覆盖整条含 `payload`）的 `hash`/`prev_hash` 链 | 任意事件的 **payload/行集**变化 ⇒ 该条 hash 变 ⇒ **其后全部** `prev_hash/hash` 级联变 | 比**事件流**（去哈希链后）是否逐条一致；`verify_chain` |
| **指纹轴** = `engine_version` | `FINGERPRINT_FILES`（`config/*.json` 等）的**聚合哈希**，写入 `WORLD_INIT.fingerprint` | **config 键**增/改/删（哪怕默认 off） | 比 `compute_fingerprint()` / `component_digests()` |

⭐ **三轴彼此独立**：世界态变**不必然**日志……不成立（世界态变几乎必致日志变）；但**日志变【不必然】世界态变**（identity fold 的字段/行增）—— **这是最容易混的一处**（见 §2a）。

---

## 1. 四档定义（判据 + 正例 + 反例 + 是否重冻）

| 档 | 名称 | 世界态轴（`state_hash`） | 日志轴（链） | 指纹轴 | 需重冻？ |
|---|---|---|---|---|---|
| **①** | **行为变** | **变** | （通常也变） | 变或不变 | **需** |
| **②** | **仅日志增**（字段增 / 行增） | **不变** | **变** | **不变** | **需**（golden 日志变） |
| **③** | **仅指纹变** | **不变** | **不变**（除指纹行及其派生） | **变** | **需**（golden 指纹行变） |
| **④** | **两者皆无**（纯文档/注释/inert） | **不变** | **不变** | **不变** | **不需** |

### ① 行为变
- **判据**：同 sha、同 seed，仅变一个开关 ⇒ **`state_hash` 不相等**。
- **正例**：`D11` 期② `time.ongoing.enabled` off vs on ⇒ `state_hash` `5f6a5679…` vs `de9c0525…`（`T363`）。`D3`② `propagate.enabled` on/off 应同型。
- **反例**：`T361` 加 `LLM_CALL.agent_id` —— **`state_hash` 不变**（`LLM_CALL` 是 identity fold）⇒ **不是**行为变（是②）。

### ② 仅日志增（字段增 / 行增；**链变、`state_hash` 不变、指纹不变**）
- **判据**：`state_hash` **相等** + 族计数/事件集**非全等**（有新增字段或新增行）+ 指纹**不变**。
  - **字段增**：既有事件加**可选**字段（如 `LLM_CALL.agent_id`/`judgment_id`、`WORLD_DIRECTIVE.source`）⇒ 每条该事件 hash 变 ⇒ **链变**；identity fold ⇒ `state_hash` 不变。
  - **行增**：新增**identity fold** 事件（如 `PERSONA_DRIFT_CANDIDATE`）⇒ 多一行、链变；`state_hash` 不变。
- **正例**：`T360/T361`（`LLM_CALL.agent_id`）；`T322`（`PERSONA_DRIFT_CANDIDATE` 入 `_NOOP_TYPES`）。
- **反例**：新增一个**默认 off 的 config 键**（如 `time.interval.enabled`）—— 那**不是**②，指纹也变 ⇒ **③**。

### ③ 仅指纹变（**`state_hash` 不变、日志逐条不变、指纹变**）
- **判据**：`state_hash` **相等** + 事件流**除"指纹行及其派生"外逐条一致** + 指纹**变**。
- **正例**：新增**默认 off** 的 config 键（`time.interval.enabled`）—— `08 §5.10` 实测：off 对照**内容差异 0/1635**、`TURN_SEAL.state_hash` 相等，**仅 `WORLD_INIT`/`config_digest` 指纹行变**。
- **反例**：新增**默认 on 且被消费**的键（如 `time.ongoing.enabled=true`）—— 会**真改行为** ⇒ **①**。

### ④ 两者皆无（纯文档 / 注释 / inert）
- **判据**：`state_hash` 不变 + 事件流**逐条一致**（含指纹行）+ 指纹不变。
- **正例**：改 `08`/`v2/refs` 文档、改注释、加**未接线**资产（inert）。
- **反例**：改 `FINGERPRINT_FILES` 里**任一** `config/*.json`（⇒ 指纹变 ⇒ **③** 或 **①**）。

---

## 2. 两处最容易混（Leader 点名）

### 2a. **"哈希链变"是 `state_hash` 变的【兄弟】还是【不同轴】？**
**⇒ 不同轴。** 
- `state_hash` = **折叠世界态**的哈希（只看**语义**结果）；
- 哈希链 = **每条事件记录**（含 `payload`）的链式哈希（**任何 payload 变动**都会变）。
- ⇒ **二者无蕴含关系**：**字段增 ⇒ 链变但 `state_hash` 不变**（identity fold，②档）；**行为变 ⇒ `state_hash` 变、且通常链也变**（①档）。
- ⚠️ **今日同类错误**：把"链变"写成"`state_hash` 变"（`T352` 任务书原句一度如此，`T360` 已纠正并裁定"分开说"）。**记：链变 ⊥ `state_hash` 变。**

### 2b. **"新增 config 键（哪怕默认 off）⇒ 指纹变"** 与 **"新增日志字段 ⇒ 链变、指纹不变"** 的区别
| | 动的是什么 | 指纹轴 | 日志轴 | 世界态轴 | 档 |
|---|---|---|---|---|---|
| **新增 config 键**（默认 off） | `config/*.json`（∈`FINGERPRINT_FILES`） | **变** | 不变（除指纹行） | 不变 | **③** |
| **新增日志字段** | 事件 `payload` | **不变** | **变** | 不变 | **②** |
| **新增 config 键**（默认 on 且被消费） | config + 行为 | 变 | 变 | **变** | **①** |

- **口径**：**config 键 ⇒ 指纹轴**；**事件字段/行 ⇒ 日志轴**；**是否被消费 ⇒ 世界态轴**。三者别串。

---

## 3. 可执行判定流程（收口时照跑）

```text
1) 指纹轴： python -c "from engine import version; print(version.compute_fingerprint())"  # 两版对比
2) 世界态轴：同 seed 各跑一次 → 比 state_hash(state)（相等 ⇒ 无行为变）
3) 日志轴：比事件流（先剥 hash/prev_hash，再比；见下方"口径"）
4) 归类：按 §1 表对号入座；④ 才免重冻。
```

**为什么"先剥再比"**：`WORLD_INIT` 含**运行时 config 摘要**、`TURN_SEAL` 含**链头 `last_hash`** ⇒ 只要指纹轴变，它们及其**链派生**必然逐条不同，**但不是行为差**。
```
# 去哈希链后比较（口径化，避免假红）：
strip: 顶层 hash/prev_hash；并对 TURN_SEAL 额外剥 payload.last_hash
期望：仅 {WORLD_INIT, TURN_SEAL} 行可差异（= 指纹行及其派生）
```
⚠️ **反例教训（`T363` 假红）**：脚本**只剥顶层 `hash/prev_hash`、未剥 `TURN_SEAL.payload.last_hash`** ⇒ 判"off≠neu"**假红**。**判据必须先走口径（`state_hash`/语义门），再看字节**（`T299` 已立）。

---

## 4. 重冻与消融注解（收口模板）

- **①②③ 都要重冻**；④ 不用。
- **重冻后对照/消融**：**"同 sha 内只变一个开关"**；日志对照须显式标注 **"唯一差异 = 指纹行及其派生（链哈希、`LLM_CALL.engine_version/cache_key`、`TURN_SEAL.last_hash`）"**。
- **②（仅字段增）**：golden 日志整体变 ⇒ 对照须标 **"唯一差异 = 新增字段 `<X>`（+ 指纹行及其派生）"**，**不得写成"行为变"**。
- **③（仅指纹变）**：须标 **"唯一差异 = 指纹行及其派生"**、**内容差异 0**（如 `T287` 期①实测 0/1635）。

---

## 5. 速查卡

| 你做了什么 | 档 | 需重冻 | 一句话 |
|---|---|---|---|
| 加**被消费**的默认 on 开关 / 改判定规则 | ① 行为变 | ✅ | `state_hash` 变 |
| 加**可选事件字段** / 加 **identity fold** 新事件 | ② 仅日志增 | ✅ | `state_hash` 不变、链变 |
| 加**默认 off** config 键 / 改**仅注释性** config | ③ 仅指纹变 | ✅ | 内容 0 差、指纹变 |
| 改**文档/注释** / 加**未接线**资产 | ④ 皆无 | ❌ | 三轴皆不变 |
| 把"链变"说成"`state_hash` 变" | —— | —— | **错**：不同轴（§2a） |

---

*（口径页完 — 只读 `v2/refs/`；供 `T355`/`T370` 等收口引用。结论以 `state_hash`/语义门为权威，字节为准绳。）*
