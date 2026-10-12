# 交付评审 · `v2/refs/world-director-design.md`（独立复核）

> 评审人：delivery-reviewer（**非作者**，不替作者辩护）｜ 时间：2026-10-12
> 被评对象：`v2/refs/world-director-design.md`（作者 narrative-designer，T210）
> 纪律：每项给**证据（章节）+ 最小验证方法**；区分**确定缺陷（阻塞）**与**待验证风险（非阻塞）**；不把风格偏好升级为架构问题。
> 复核口径：Fork B（Leader Q-12.1）——「放开必现可复现、保留可被复算」；红线 A′ 三条保底（a 显式事件 / b 可消融 / c 不改过去）。

---

## 0. 结论

**有条件通过（Conditional Pass）**——红线 A′ 的三条保底 (a)(b)(c) 落成了**可机器校验的不变量**，职责边界（宏观 vs 插手个体）用 R1–R6 决策树**可判定化**，与米哈游"AI 导演"的概念切分清晰。但有 **3 项确定缺陷须闭合**（其中 D-2 触及 C3「LLM 判定冻结」，C3 未被 Fork B 放开）。

---

## 1. 阻塞项（确定缺陷）

### D-1【中】引用 `08` 的群组事件集合与实际 schema **不符**（凭空多出字段/枚举）
- **证据**：§4.3(1) 称 `GROUP_CREATED/GROUP_JOINED/GROUP_LEFT/`**`GROUP_DISSOLVED`**`（08 §1.2）`；§4.3(2) 称 `GROUP_CREATED.kind ∈ {chat, guild, …}`。**核对 `v1.1/08-engine-stats-extension.md` §1.2 M 表**：只有 `GROUP_CREATED`（payload `group_id, members[], created_round`）、`GROUP_JOINED`、`GROUP_LEFT`（后二者标"可选"）；**无 `GROUP_DISSOLVED`**，且 **`GROUP_CREATED` 没有 `kind` 字段**。
- **影响**：本设计的「`kind` 值域不相交」硬约定**建立在一个不存在的字段上**——若按此登记，`08` 会引入一个与既有群组 schema 不一致的字段。
- **最小验证**：`grep -n "GROUP_" v1.1/08-engine-stats-extension.md` → 确认无 `GROUP_DISSOLVED`、`GROUP_CREATED` 无 `kind`。
- **最小修补**：改引用为「`GROUP_CREATED/JOINED/LEFT`」；「不相交」改为针对**事件类型名**（`WORLD_GROUP_EVENT ≠ GROUP_*`）而非 `kind` 字段；如需 `kind` 则一并提案给 `08`。

### D-2【高】「Director 判断」类触发**未声明经 IF-2b 冻结**——触碰 C3（LLM 判定冻结，未被 Fork B 放开）
- **证据**：§3 触发列多处写「**Director 判断**发布（RNG 先定是否发布）」「Director **判断**（RNG 先定）」（WD-3/WD-7/WD-10）；§4.1 `WORLD_DIRECTIVE.model` 允许「由 LLM 生成」；但**全文未声明**：若"Director 判断"含 LLM 定性判断，该判断**必须经 IF-2b 冻结为 `LLM_JUDGMENT`（`frozen=true`）**、重放不重问 LLM。§4.2 仅规定 `rationale` 走侧存储。
- **影响**：Fork B **只放开复现口径**，**没有放开 C3**（Q-12.1 明确"审计地基"保留）。若 Director 的"是否介入/选哪个机制"由**未冻结的 LLM 判断**驱动，则 `WORLD_DIRECTIVE` 的产生**不可复算**——保底 (a)(c) 的"可独立复算"落空。
- **最小验证**：追踪 WD-3 一次"政令发布"：`是否发布/发布哪条` 由 RNG 还是 LLM？若 LLM，是否落 `LLM_JUDGMENT{frozen}`？
- **最小修补**：§3/§4 明确二分——**"是否介入/选哪个机制/剂量"= 规则+RNG（确定性，落 `rng_branch`）**；**LLM 仅产 `rationale`（N 类）**；若确需 LLM 参与"介入判定"，则**必经 IF-2b 冻结**并同步 `08`。

### D-3【中】**未指定 Director 介入在 hook 链中的相位/时点**——影响"结算顺序全局固定"
- **证据**：§4.1 `WORLD_DIRECTIVE` 外壳含 `phase: int` 但**未给值**；全文未说明 Director 决策/Hook 挂在 `P0..P6`（或新增相位）的**哪一步**。`08 §2.4` 的链是 `…P3.5 LIFE → P4 ARBITRATE…`。
- **影响**：Director 产 `WORLD_GROUP_EVENT` 改变"情境"（如关闭场所、投放资源），**其相位决定它是否影响同回合的 L1–L7 / 4.1–4.8**。相位未定 → **结算顺序不固定**，与 `08` X2「4.1–4.8 顺序冻结」及"同回合确定性"存在未定口。
- **最小验证**：在 §4.1 找不到 `phase` 取值与介入时点。
- **最小修补**：明确 Director 决策相位（建议：**介入决策与 `rng_branch` 在入 P2/P3.5 前生成，`WORLD_GROUP_EVENT` 在 P3.5 落**），并同步 `08` 事件表的 `phase`。

---

## 2. 非阻塞风险 / 口径同步

| ID | 事项 | 说明 / 手段 |
|---|---|---|
| R-1 | **保底(c) ③ 写「`replay(log)` 逐位一致」**（§0.3、§3.2、§7） | Fork B 后**门禁**口径改为「可复算/诊断」；建议改写为「`replay(log)` **可复算**（同日志→同状态，保留）；不判字节 FAIL」——**能力保留、门禁降级**（见 `gate-grading.md` F5） |
| R-2 | **§1.2 R1 仍把「≥K 个 Agent」列为宏观判据** | 与 WD-D1「K 不作准入」有轻微张力；建议 R1 删「≥K」、只留"面向群体/环境/公共条件"，K 仅在 §1.2 告警路径出现 |
| R-3 | **保底(b) 用置换检验（p≤0.05）** | 与"剂量=0≡关闭（确定性归零）"并存；建议**同 seed 关闭 = 确定性零**作**硬判据**，置换检验仅作跨 seed 稳健性诊断 |
| R-4 | **`actor="DIRECTOR"` 为外壳扩展** | 文档已自陈兜底为 `actor="SYSTEM"+directed=true`（§4.1/§4.3）——**须以 `08` 登记为准**（WD-C1），落地前不得先实现 |
| R-5 | **WD-10/`aggressive` 灾难级** | 文档已默认 OFF + 要求 `per_agent_impact_ref`（可复算）——达标；登记为"启用须 Leader 明示" |

---

## 3. 值得肯定处

- **保底 (a)(b)(c) 全部落成可机器校验不变量**（§7 总表）——尤其 (a)「`count(改变情境且无 directed)==0`」、**(c)「`effective_from_round ≥ issued_round`，篡改过去即 `WORLD_DIRECTIVE_REJECTED`」**，是本设计最有价值的"防不可查"设计。
- **R1–R6 把"宏观介入 vs 插手个体"变成决策树**（§1.2），并明确「**宏观 ≠ 结果**」——避免了"作者化=替角色写结局"的滑坡。
- **与叙事层接口**（§5）用 `directed` + Q-9「`directed_mislabel==0`」**防止把导演安排说成自发**——对齐 T204 来源诚实判据。
- **§2 与米哈游"AI 导演"的差异**讲清了"导世界情境 ≠ 导叙事/结局"，差异化定位成立。

---

## 4. 放行条件

- **必修（放行前）**：**D-1**（修正 `08` 群组事件引用）、**D-2**（声明 Director 判定冻结路径，保 C3）、**D-3**（定 Director 相位，保结算顺序固定）。
- **登记/同步**：R-1（口径同步 Fork B）、R-2~R-5；**WD-C1（三事件登记 `08`）是实现前硬前置**（文档已自陈，达标）。
- **D-1/D-2/D-3 闭合后即视为通过**；均为**可最小修补**的契约一致性问题，**不动摇设计主体**。

*（评审结束 — delivery-reviewer）*
