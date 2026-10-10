# 03 · 对话（MSG_*）未消费 LLM 输出 —— 诊断 + v2 接线方案（T81）

> 类型：诊断 + 接线方案（**只读定位，本任务不改代码**）
> 作者：life-layer-dev　日期：2026-10-10
> 范围：仅 M6 对话链路在 `life/` 侧；引擎已冻结
> 依据：`v1.1/06-life-layer.md`(M6)、`v1.1/08`（事件 schema 权威）、`freeze/`、T57（同类“LLM 输出未消费”修法）

---

## 0. 诊断结论（TL;DR）

**对话链路根本没有调用 LLM。** 不是“调了没消费”，也不是“被 mock 短路”——真 LLM 跑时走的还是同一段代码，所以正文仍是那两句模板。

- `MSG_DM` 正文由确定性结算 hook 内的 `_m6_specs` **硬编码**产生；
- 决策侧（`agent.py`）**没有任何对话/社交意图生成**；
- `life/llm.py` 的 purpose 白名单里**没有 `dialogue`**；
- `life/ports.py` 的意图类里**没有 `INTENT.SOCIAL`**（00 §4.2 有，life 未实现）。
- 因此真 LLM 日志里不可能出现 `purpose=dialogue` 的 `LLM_CALL`——与证据完全吻合。

根因：M6 在 T56 是**“纯加法骨架”**——只把 `MSG_*`/`OFFER_*` 的**事件形态**接进模板结算以保证普查命中，**正文本就用固定模板**；且这些 MSG 产生在 **L3 确定性 hook** 内，而架构规定 **LLM 只能在 Phase 2/3 决策相位**（hook 不得调 LLM），故当前结构下**无处可调**。

---

## 1. 文件 + 行号级定位（证据）

| # | 位置 | 事实 |
|---|---|---|
| 1 | `life/settlement.py:337` | `events += _m6_specs(tid, parts, state, round_no, t)` —— 在 **L3 `settle_activities`（确定性 hook）** 内产出 MSG |
| 2 | `life/settlement.py:342` | `def _m6_specs(...)` 定义对话/协商事件 |
| 3 | `life/settlement.py:354–363` | `_dm(body)` 直接写入**硬编码** `"（寒暄）你好呀。"` / `"（低声）听说……"` → `MSG_DM`，**无任何 LLM 调用** |
| 4 | `life/agent.py`（全文） | **无** MSG/社交意图生成；仅 `:34` 把 `MSG_*` 放进 salient 集合、`:397` 在 `_describe_event` 里读 MSG —— 都是“消费/描述”，非“生成” |
| 5 | `life/llm.py:20` | `ALLOWED_PURPOSES = {"plan","reflect","importance","decide_t2","describe","judge","narrate"}` —— **无 `dialogue`**（即便调用也会被白名单拒） |
| 6 | `life/ports.py:19–29` | `ALL_INTENT_CLASSES` 无 `INTENT.SOCIAL` |
| 7 | `config/llm.json` | `thinking.true_purposes=["judge","narrate","describe"]`，无 dialogue（→ 默认 `thinking=false`，符合“求快”目标） |

**与 judge/describe 的差异**：judge/narrate 走**决策相位**（`life/soft.py` + `agent._maybe_soft_judge/_maybe_narrate`）→ freeze → `LLM_CALL`，所以正常；对话没有对应的**决策相位调用点**。**缺口在决策侧，不在冻结层。**

**排除项**：① 非“调了没消费”——当前作用于 `LLMResult.text` 的只有 plan/reflect 等，**对话没有对应的消费点**；② 非“mock 短路”——真 provider 同样走 `_m6_specs`。

---

## 2. v2 接线方案

### 2.1 对话属于哪一类？——**N 类（叙事/内容）**，不是 F（判定）
对话正文是**内容生成**，不改变世界状态、不进入任何判定/数值/结算。因此：
- **冻结方式**：`MSG_*` 事件本身 **append-only 落日志**，重放**直接读 body、不重调 LLM** → **无需新增“冻结事件”**；只需在生成时调一次 LLM 并记 `LLM_CALL(purpose="dialogue")`。同日志 → 同正文，**确定性成立**（LLM 的随机不收进世界；措辞不参与判定——守 L-1）。
- 正文较长可选入**侧存储 + `body_ref`**（08 已允许）；`MSG.refs` 转述类必填（T27）。

### 2.2 相位与触发点（**在决策相位，不在 L3 hook**）
- 生成落在 **Phase 2/3（agent 决策）**：agent 对“本回合将发生的社交动作”生成措辞 → 经 **IF-2 提交 `INTENT.SOCIAL`** → 内核封装为 `MSG_*`。
- **新增 `INTENT.SOCIAL`**（00 §4.2 已定义；life 未实现）→ 需引擎适配 `_do_social`（把 `MSG_DM/PUBLIC/GROUP` 入本回合缓冲）。**跨模块：与 kernel-dev 对齐。**
- 触发点＝现有社交模板的“对话位”（whisper / gift / ice_break / rel_maintain / rel_accept）+ T79 的 public/group。

### 2.3 显著性阈值 & 预算
- **非每次共处都调**：仅**显著社交事件**（模板触发的对话位、跨 `ε` 关系、收到/发起 `OFFER_*`）生成；每 Agent 每时段 ≤1 条、每回合全局配额（对齐 v1 §4.2 三通道配额）。
- **分层**：`dialogue` 属 **T1**（短 prompt）；`LLMBudget` 超限时**降级为固定模板**（即当前行为）并记 `LLM_CALL(degraded=true)`。
- **thinking=false**（求快）：不列入 `true_purposes`，保持默认 false。

### 2.4 确定性与可见性
- 生成一次 → `LLM_CALL(purpose="dialogue")` + `MSG_*{body}` 落日志；**重放读 body，不重调**。
- **收件人/可见性只用 `visible_events()`**（同场所/已知关系）判定，**不得用 LLM 判可见性**；群聊可见性走 R3/R4（08 §3.5）。

---

## 3. 最小改动面 & 对 08 schema 的影响

**改动面（life 侧最小）：**
- `life/ports.py`：新增 `INTENT_SOCIAL`。
- `life/llm.py`：purpose 白名单加 `dialogue`。
- `life/agent.py`：新增 `_communicate(wv)` —— 对本回合社交位调 `llm.call("dialogue", prompt, meta={"round":wv.round})` → `submit_intent(INTENT.SOCIAL)`。
- `life/settlement.py`：`_m6_specs` **移除硬编码正文**（MSG 改由决策侧 `INTENT.SOCIAL` 产生）；`OFFER_*` 保留（确定性，不受影响）。

**跨模块（需对齐）：**
- `engine`（kernel-dev）：`INTENT.SOCIAL` 合法化 + `_do_social`（DM/PUBLIC/GROUP）。
- `freeze`：purpose `dialogue` 白名单（T1、thinking=false）+ 缓存（重放零调用）。
- `config/llm.json`：无需改（dialogue 默认 false）；可选登记 tier 策略。

**08 schema 影响：无需新事件。** `MSG_DM/PUBLIC/GROUP` 已存在；`LLM_CALL.purpose` 为动态值，加 `"dialogue"` 即可；长正文可选 `body_ref`（已有侧存储约定，非必需）。

---

## 4. 与 T79（公开/群聊）合并的实施顺序

**建议同一批“解冻重跑”内完成**，顺序：
1. `freeze`：加 purpose `dialogue`（T1、thinking=false）+ 缓存；
2. `engine`：`INTENT.SOCIAL` + `_do_social`（**DM/PUBLIC/GROUP 三通道一次到位**）；
3. `life`：`agent._communicate` 生成措辞；`settlement._m6_specs` 移除硬编码正文；
4. **T79**：复用同一生成器产出 public/group（公开板/群聊），并接 `refs`/`tag_hints`；
5. 统一真 LLM **N=20 重跑**：核对 `LLM_CALL(purpose=dialogue)>0`、MSG 正文非模板、`state_hash` 与 mock 分叉、replay 一致、SYSERR=0。

> 关键：**先 T81（本方案）→ T79 与对话 LLM 一起实现 → 一次重跑**，避免两次解冻与两次基线重冻。

---

## 5. 风险 / 开放点

- **成本**：对话调用量随社交位线性上升 → 靠 T1 + 配额 + degraded 兜底控；需与 T10 成本标定对齐。
- **副作用**：对话正文若入记忆，会经词法嵌入影响**检索排序**（非判定），可接受；务必保持“措辞不进判定/数值”。
- **不可复现风险**：仅当**同一日志**重放——已满足；跨跑不保证（本就如此）。
- **与 M8 传播**：对话 `OBSERVATION`/`refs` 支撑传播图，T79 一并对齐。

---

*（T81 诊断 + 方案完 —— life-layer-dev。行动项：本方案落地需 kernel-dev(`INTENT.SOCIAL`/`_do_social`) 与 freeze(`dialogue` purpose) 配合，建议合并 T79 一次实施。）*
