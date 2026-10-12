# M2b 实现设计：judge / importance 判别式化（候选枚举 + 类型化打分 + 两分支回退）

> 类型：**实现设计（不含实现、不改 `code/`）**
> 作者：life-layer-dev　日期：2026-10-12　任务：T213
> 上游：T208（端点支持 `logprobs`/受限选择，判别式 `completion_tokens=13 / reasoning_tokens=0`）、T212（判别式 vs 生成式：一致率 + 校准度 ECE，**进行中**）
> 背景数据：`judge` 走 `thinking=T2` 输出 **344k token = 全量 72.7%**；`importance` 指数 **2.64**（比 judge 更陡）

---

## 0. 定位与红线（先说清楚）

- **M2b 不是「降 thinking」。** 用户要求**软判定保留 thinking**。M2b 是**另一条路径**：在**不依赖长 CoT** 的前提下，**给出与生成式判定等价**的定性结论。生成式（thinking）**继续保留**，作为回退与对照臂。
- **判定冻结语义不变（关键）**：判别式只是**产生 `decision` 的方式**变了；结果仍**冻结进 `LLM_JUDGMENT`**（四要素：`decision` / `model` / `context_digest` / `frozen=true`），经 **IF-2c 审计桥**落同一哈希链。**不得因为改了调用方式而变成不可审计。**
- **只产标签、不产数值**：`decision ∈ envelope.options`；数值后果仍由**确定性函数**（如 `relations.delta_from_frozen_label`）推出。
- 不确定处一律标 **【未验证】**。

---

## 1. 候选枚举：如何把「自由生成判定」变成「从合法候选中选」

**原则**：`options` 由 **life 代码（envelope）确定性枚举**，**不由 LLM 生成**（保证完备、互斥、可复现；LLM 只“选”不“造枚举”）。

| dimension | options（现状/建议） | 来源 | 完备/互斥 |
|---|---|---|---|
| `rel_affinity` / `rel_trust` / `rel_familiarity` / `rel_respect` | `["formed","not_formed"]` | `relations.soft_judgment_envelope()`（已存在） | 二分，完备互斥 |
| `weekly_focus`（T57） | `["work","social","study","leisure","balance"]` | `planner.FOCUS_OPTIONS` | 有限枚举，互斥 |
| `stance`（T127） | `["accept","reject"]` | `agent._maybe_social_appraisal` 内联 | 二分 |
| `respect` / `affection`（T127） | `["high","low"]` | 同上 | 二分 |
| `importance`（M2） | **`["1".."10"]`（整型档）** 或 `["low","mid","high"]`（3 档，若校准差） | `constants` 内枚举 | 有限离散；数值区间→档位映射**确定性** |

**完备性守卫（确定性）**：进入判别式前，life 侧断言 `len(options) ≥ 2` 且 `len(set(options))==len(options)`；不满足 → **不发起判别式调用**，直接走回退（见 §4）并落 `DROPPED`-类审计（**不静默**）。
**每维度 options 唯一来源**：集中到 `life/constants.py` 的 `JUDGMENT_OPTIONS[dimension]`（**单一真源，不复制**）；现有散落的内联 options 收编于此（实施时）。

---

## 2. 类型化打分：具体 schema（judge 判别式化）

### 2.1 输入 schema（life → freeze，判别式）

```jsonc
// discriminative judge request
{
  "question_ref": "rel_relation_quality",      // 判定问题的规范标识（模板 id）
  "dimension": "rel_affinity",                  // 维度
  "parties": ["P003","P007"],                   // 相关主体
  "envelope": {                                 // 硬内核给定约束（不可被 LLM 改）
    "options": ["formed","not_formed"],         // ★ 合法候选（唯一真源）
    "threshold": 20                             // 可选：阈值上下文
  },
  "rng_branch": "formed",                       // ★ 由种子化 RNG 预定的分支（LLM 不掷骰子）
  "context": { "...": "压缩上下文（needs/goal/记忆摘要等）" },
  "context_digest": "sha256:…",                 // 上下文规范哈希
  "mode": "discriminative",                     // ★ 判别式路径标记
  "scoring": { "require_confidence": true }     // 由回退分支决定（§4）
}
```

### 2.2 输出 schema（模型 → freeze）

```jsonc
// 约束解码/受限选择下，模型的“短完成”必须是：
{ "decision": "formed", "confidence": 0.87 }
```

- **`decision` 必须 ∈ `envelope.options`**（约束解码保证；freeze 仍二次校验，越界 → `SYSTEM_ERROR{kind:"invalid_judgment_decision"}`，**与现状一致**）。
- **`confidence ∈ [0,1]`**：在 `logprobs` 可用时取**归一化候选概率**；不可用时由 freeze 置 `null`（此时不得启用置信度回退）。
- **无 CoT**：禁止长 reasoning；`completion_tokens` 目标 ≈ 10–20（T208 实测 13）。

### 2.3 冻结事件（`LLM_JUDGMENT`，additive）

在现有四要素基础上**只增不改**（08 X1）：

```jsonc
{ "judgment_id":"…", "dimension":"rel_affinity", "parties":[...],
  "decision":"formed", "model":"…", "context_digest":"sha256:…", "frozen":true,
  "method":"discriminative",        // ★ 新增：discriminative | generative | rng-branch | rule
  "confidence":0.87,                 // ★ 新增：可空
  "envelope": {...}, "rng_branch":"formed" }
```

- **重放**：`apply_event(LLM_JUDGMENT)` 仍只写 `state.judgments[judgment_id]=decision`，**不重调 LLM**（不变）。
- `method`/`confidence` 为**审计可见性**（区分走哪条路、是否回退）——**不得静默**。

---

## 3. 与内核 / 冻结的接口（保持“判定冻结”语义）

| 层 | 现状 | M2b 增量 |
|---|---|---|
| `life/soft.py::SoftLayer.judge` | 调 `inner.judge(...)`（生成式） | 增 `mode="discriminative"` 分支：调 `inner.judge_discriminative(...)`；**签名/返回不变**（返回 `(payload, emitted)`） |
| `life/agent.py`（`_maybe_soft_judge` / `_maybe_social_appraisal` / `_weekly_focus`） | 构造 envelope+rng_branch → `soft.judge` | **调用点不变**；由 freeze 内部按配置选路径（life 不感知），或 life 传 `mode` 由开关决定 |
| `freeze/llm_client.py::LLMClient.judge` | 生成式：`complete(purpose="judge")` | 增 `judge_discriminative(...)`：**约束解码/受限选择 + 短 JSON**；仍 `self.event_log.append("LLM_JUDGMENT", payload,...)` + `_emit_audit(...)`（IF-2c） |
| `contracts` `AuditPayload` | `kind ∈ {LLM_CALL, LLM_JUDGMENT, NARRATIVE}` | **不改**（`method/confidence` 落在 `payload` 内） |
| `engine/replay.apply_event` | 折叠 `LLM_JUDGMENT.decision` | **不改**（只读 `decision`） |

**冻结不变式**：① 四要素齐；② `decision ∈ options`；③ `method` 必填（审计）；④ 重放零调用；⑤ 成本记 `LLM_CALL(purpose="judge", tier, thinking...)` **分列**（与判定分列，沿用三事件分列）。

---

## 4. 回退策略（**两分支，不押一边**）

引入开关 `policy.m2b.judge.mode ∈ {discriminative, generative}` 与 `fallback ∈ {confidence, rule, none}`；**由 T212 的 ECE 决定默认**。

### 分支 A —— 若 **T212 ECE ≤ 0.05（校准达标）** → **启用置信度回退**
- 判别式返回 `decision + confidence`；
- **若 `confidence < τ`（默认 τ=0.6，可调）** → **升级生成式**（`thinking=T2`）对该 item 复核，采用其后验结论；
- 落事件：`method="discriminative"`；被升级者 `method="generative"` + `fallback="confidence_low"`。
- 依据：ECE 达标说明 confidence **可信**，可用于“拿不准才花大钱”。

### 分支 B —— 若 **T212 ECE > 0.05（校准不达标）** → **禁用置信度回退，改用规则判定**
- **不信任 confidence**；改用**候选间分值差（margin）阈值**：
  - 取 top-1 与 top-2 的**受限选择分值** `s1 ≥ s2`；`margin = s1 − s2`；
  - **若 `margin < θ`（默认 θ=0.15，可调）** → 升级生成式复核；否则直接采 `argmax`；
- 落事件同 A（`method` + `fallback="margin_low"`）。
- 依据：校准不可信时用**相对间隔**（对单调变换不敏感）代替**绝对置信度**。

**共同**：两分支都会在**同一 `LLM_JUDGMENT`** 上标注 `method`/`fallback`；**升级率**是核心成本-质量旋钮（P3 标定）。**绝不静默**：任何回退都可在日志按 `method!=discriminative` 查出。

---

## 5. `importance` 一并处理（指数 2.64，比 judge 更陡）

- 现状：`agent._score_importance` → `llm.call("importance")`（**自由生成**，且已在 `life/llm.py` 白名单）。
- M2b：**判别式化**为「**从 `{1..10}` 选一档 + confidence**」（或 3 档若校准差）：
  - 输入同 §2.1（`dimension="importance"`, `options=[1..10]`）；
  - 输出 `{"decision":"6","confidence":0.71}`；
  - 数值即 `decision`（**已是离散档，无需再映射**）；`MEMORY_WRITE.importance` 事件**不变**。
- **回退**：同 §4 两分支（confidence 或 margin）；升级用生成式 importance。
- **理由**：importance 调用量大 → 判别式化杠杆最大；且它本就是**有序离散**目标，天然适合受限选择。

---

## 6. 预期收益与验收判据（带算式）

**基线（T208）**：`judge` 生成式（thinking=T2）单次 **≈344,000 token**?——原文为「judge 走 thinking=T2 时输出 344k（占全量 72.7%）」，按「全量」口径解释为**该 run judge 合计 344k**。【未验证：344k 是单次还是合计，按 T208 原文口径；实施前以 T212/日志复核】

**判别式单次**：`completion_tokens ≈ 13`、`reasoning_tokens=0`；prompt 与原判定同量级（判别式 prompt 通常**更短**，因无需 CoT 引导）。

**收益算式（示意，按“每 run judge 调用数 = N_calls”）**：
```
baseline_tokens   = N_calls × (prompt + 344k_per_call 或 344k_total)     # 以 T208 口径为准
discriminative    = N_calls × (prompt′ + 13)
收益比 R = discriminative / baseline
目标：R ≤ 0.2（judge token ≤ 0.2× 基线）
```
即使**保守**地把 344k 当作**每 run 合计**、且 prompt 占比不可忽略，判别式把输出从 ~10^5 降到 ~10^1，**R 远 < 0.2**（量级差 4 个数量级）。**结论：目标可达**（**以 T212 + 实测复核为准**）。

**验收判据（质量不得下降）**：
1. **成本**：`judge` 相关 token（`LLM_CALL{purpose="judge"}` 聚合）**≤ 0.2× 基线**（同 run/同 seed 对照）；
2. **质量**：以 **T212 的一致率/准确率**为依据——判别式 vs 生成式的 **agreement ≥ 基线阈值**（阈值由 T212 定），且**校准分支**按 ECE 选择正确（ECE≤0.05→A；否则→B）；
3. **可审计**：每条判定带 `method`（discriminative/generative/rng-branch/rule）+（可空）`confidence`；`frozen=true`；
4. **守恒**：`decision ∈ options` 100%；重放**零 LLM 调用**；`state_hash` 沿用现有 `judgments` 排序口径（**Fork B 后不再以逐位重放为口径**，但日志/种子/sha 照旧）。

---

## 7. 与现有模块的接口清单（实施时逐条对齐）

- `life/soft.py::SoftLayer.judge` —— 增 `mode`/判别式分支；返回 shape 不变。
- `life/agent.py`：`_maybe_soft_judge` / `_maybe_social_appraisal` / `_weekly_focus` / `_score_importance` —— **调用点不变**（路径选择在 freeze/开关）。
- `life/constants.py` —— 新增 `JUDGMENT_OPTIONS[dimension]`（**单一真源**）；收编现散落 options。
- `freeze/llm_client.py` —— 新增 `judge_discriminative(...)` / `score_importance_discriminative(...)`（受限选择 + 短 JSON + confidence）；沿用 `_emit_audit`（IF-2c）。
- `freeze/config` —— `judge` 的 thinking 策略保持 `true`（生成式臂）；判别式路径标注 `mode`，**不改 thinking 语义**。
- `contracts` / `engine/replay` —— **不改**（`LLM_JUDGMENT` payload 只增 `method`/`confidence`）。
- `config/policy.json` —— 新增 `m2b.judge.{mode,fallback,τ,θ}`（默认由 T212 ECE 决定）。

---

## 8. 风险与【未验证】清单

- 【未验证】344k 是 judge **单次**还是 **每 run 合计**（T208 原文口径需复核）。
- 【未验证】ECE 达标性（T212 进行中）→ 决定默认走 A 还是 B。
- 【未验证】受限选择下 **confidence 的校准质量**（不同 provider/温度可能不同）→ 直接影响分支 A 可用性。
- 【未验证】prompt 缩短幅度（判别式 prompt 设计效应）→ 影响 R 的精确值。
- **风险**：`decision∈options` 由约束解码保证，但**仍需 freeze 二次校验**（防御 provider 差异）；越界→ `SYSTEM_ERROR`（不静默）。
- **不变量**：M2b **不改变**“判定只产标签、数值确定性、冻结可审计、重放零调用”四条。

---

*（T213 设计完 — life-layer-dev。**只设计、未实现、未改 `code/`**；实施需 T212 结论定回退默认分支。）*
