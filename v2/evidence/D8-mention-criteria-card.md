# D8 判据卡 · 「居民提及世界事件」字段级判定（跑批前定死，batch-runner 直接实现）

> 作者：repo-scout｜2026-10-20 22:14 (+08:00)｜上游：`v2/evidence/D8-preregistration-world-director.md`
> **非盲，但已定死**：本卡在 A/B 批起跑**前**写定并随本轮 commit（判据与读数同批）；作者已知 A0 臂读数（1 条 directive、0 条沉淀、0 条 refs），故不称"盲预注册"。取数后**不得改判据**，只能追加"修订记录"。

## 1. 什么算"世界事件发生"（分子侧事件源）

| 项 | 值 |
|---|---|
| event type | `WORLD_DIRECTIVE`、`WORLD_GROUP_EVENT`（**仅这两个**；`WORLD_DIRECTIVE_REJECTED` 不算发生） |
| 唯一键 | `payload.directive_id`（`WORLD_DIRECTIVE`，形如 `D-<round>-<mechanism_id>`）/ `payload.group_event_id`（`WORLD_GROUP_EVENT`，形如 `GE-…`）+ `directive_ref` |
| 时间字段 | 记录顶层 `round`（= `payload.issued_round`）；窗口用 `payload.effective_from_round` / `payload.expires_round` |
| 世界事件 seq 集 | `W = {rec.seq for rec in log if rec.type in WORLD_TYPES}` |

## 2. 什么算"居民提及"（两层，必须分开报，不许相加）

**M-0 沉淀层（主判据，最硬，零 LLM）**：居民"知道了这件事"。

```python
def m0_knew(rec) -> bool:                     # 逐条 MEMORY_WRITE
    p = rec.get("payload") or {}
    return rec["type"] == "MEMORY_WRITE" and p.get("source_event_seq") in W
```
- 也算数（同源、单列）：`OBSERVATION` 且 `payload.target_event_seq in W`。
- **不算数**：`MEMORY_FORGET` / `MEMORY_CONSOLIDATE` 记录里出现相同数字（数值巧合，A0 批就出现 28 行假命中）；`_observed_seqs` 之外的任何子串匹配。

**M-1 对话层（提及，词表代理）**：居民"说出口"。

```python
import re
BAN = re.compile(r"[（(][^）)]*[）)]")          # 先剔除括号内（旁白）内容
KIND_WORDS = {                                  # 冻结词表；kind -> 词
    "tension":  ["缺货", "涨价", "紧俏", "买不到"],
    "edict":    ["告示", "通告", "新规矩"],
    "festival": ["节日", "庙会", "集会", "热闹"],
}
def m1_mentions(body: str, kind: str) -> bool:
    s = BAN.sub("", body or "")                 # 括号内一律不算（G-1 教训：命中全是旁白副产品）
    return any(w in s for w in KIND_WORDS.get(kind, []))
```
- **不算数**：① 括号内命中；② 仅 `payload.refs` 命中——当前 `refs` 恒为 `[]`（A0 实测 0 条），在 life-engineer 新增 `world_ref`/`refs` 之前**不得**作为证据；③ 未来若新增 `payload.world_ref`，那才升级为"真引用"，且必须单列一列，不许并进 M-1。
- 词表必须随读数落 `inputs`（词表 sha256），否则该读数不可复核。

## 3. 分母（写死，不许事后挑）

| 指标 | 分子 | 分母 | 统计单位 |
|---|---|---|---|
| **M-0** | 命中 M-0 的 `MEMORY_WRITE` 条数 | **应沉淀数 = 存活 agent 数 × 世界事件数**（A0 规模 = 16 × N_world；去重规则：每 agent 每 world seq 只算 1 条） | per-(agent, event) |
| **M-1** | 窗口内 M-1 命中的消息条数 | **窗口内全部 `MSG_DM/MSG_PUBLIC/MSG_GROUP` 条数**（不按 agent×event 重复计数，否则同一句被数多遍） | **per-message** |

窗口写死：`[issued_round, issued_round + 12)`（一个模拟日 = 12 回合，与 `time` 口径一致）；`expires_round` 只用于填表注记，不参与取窗。

## 4. 已知会让读数虚高的陷阱（每条都给拦截动作）

1. **过期事件永久可见**（`contracts/visibility.py` 不按 `[start,end)` 裁剪——我已在诊断 §5.1 记录）。若 B 臂只开白名单、没修时间窗，M-0 会在 `expires_round` 之后**继续增长** ⇒ **B 臂 M-0 虚高**。
   拦截：跑前先跑 `grep -n "start_round\|end_round\|expires" code/contracts/visibility.py`；**输出为空 ⇒ 必须在读数表里标 `visibility_window=UNFIXED`，该批 M-0 只能作方向注记、不得作为"接通"证据**。
2. **旁白副产品**（G-1 同款坑）：括号内命中一律剔除；且 M-1 上升时必须**同表**报 `L-2_narration_rate_proxy`（`tools/d5/dialogue_metrics.py:581`）。旁白率同步上升 ⇒ 判「用旁白换提及」，不算改善。
3. **分母塌缩**：两臂消息量分母差 >30% ⇒ M-1 判「不可比」（全族纪律），只报事件数。
4. **子串误报**：词表只认上表四字词，禁止"含'紧'即命中"这类放宽；改词表必须换 sha 并重跑两臂。
5. **分母 <30**：M-1 分子 <30 时只写"X 次窗口内提及 / Y 条消息"的事件级事实，**不写百分比**。

## 5. 读数表固定列（batch-runner 直接照此出表）

`arm | N_world | world_seqs | M-0 分子 | M-0 分母 | M-1 分子 | M-1 分母 | visibility_window | L-2 旁白率 | 词表 sha8 | 判定`

## 6. 修订记录（只追加，不改原文）

- **R1（2026-10-20 22:24，batch-runner 回执后）** M-0 分母改为**存活 agent 数（本轮裁决 agents=4）× N_world**，不再固定写成 16（16 是 A0 历史锚点规模）；`N_world=0` ⇒ M-0/M-1 一律判「不可判」，不许写 0%。
- **R2（同上）** M-1 的**唯一归属规则**：同一消息可能落在多个事件的 12 回合窗口内，**只记入其窗口内最早的那个世界事件**（按 `issued_round` 升序取第一个命中的事件），避免同一句被重复计入分子与分母。
- **R3（同上）** `visibility_window` 记法：A/B 两臂用**同一份** `contracts/visibility.py`（仅差白名单开关），若该份代码已含 `[start,end)` 裁剪 ⇒ 记 `FIXED(B树同码,两臂同码,非自变量)`，表注写明"时间窗修复不是自变量，唯一自变量=白名单开关"；**且必须附两臂 `sha256sum code/contracts/visibility.py` 相等**，否则视为两臂代码不同、判不可比。若未含裁剪 ⇒ 记 `UNFIXED`，M-0 只作方向注记。
- **R4（同上）** 补充静态事实：`OBSERVATION` 有**两份**互不相干的白名单——`life/agent.py:41-45 _SALIENT_EVENTS`（经 `INTENT.OBSERVE` → `orchestration/integration.py:613-622` 发射）与 `life/settlement.py:609 _SIGNIFICANT`（L6 直接发射）。M-0 若单列 `OBSERVATION`，必须注明它来自哪条路径。
- **R5（2026-10-20 22:28，batch-runner 二次回执后）** 两条实现层约束，影响读数解释，不改变判据：
  1. **M-0 的主判据只认 `MEMORY_WRITE`**；`OBSERVATION` 必须**按路径分列**（`_SALIENT_EVENTS` 路径 / `_SIGNIFICANT` 路径），两列**不得相加**——若 B 树同时改了两份白名单，同一事件会被两条独立通路各记一次（`_observed_seqs` 与 state 的 `observed_event_seqs` 是两个集合），相加就是双计。
  2. **白名单开口必须同时补 `_describe_event()` 分支**（`life/agent.py:1259-1272`）：该函数对未知类型走兜底 `f"{ev.actor} 的 {t} 事件。"`。若只把 `WORLD_*` 加进 `_SALIENT_EVENTS` 而不加分支，写入记忆的正文会是 `DIRECTOR 的 WORLD_DIRECTIVE 事件。`这类**机器 token 文本**，会被检索直接带进 prompt ⇒ 读数上表现为"提及上升"但实际是 token 泄漏（与 L-13 同类）。出表时必须检查窗口内 `MEMORY_WRITE` 正文样本，出现该兜底句式即判该臂读数受污染。
- **R6（2026-10-20 22:34，Leader 裁决）事件实体单位 = 唯一 `directive_id`，成对记录算 1**
  1. `W` 仍取两型并集（`WORLD_DIRECTIVE` + `WORLD_GROUP_EVENT`），**仅用于"这个认知是否参与过"**，不用于计数。
  2. `N_world = |{payload.directive_id}|`（成对算 1，`WORLD_GROUP_EVENT` 用其 `directive_ref` 归并；无 `directive_ref` 的孤立 group event 才以自身 `group_event_id` 计）。分母 = 存活 agent 数 × `N_world`。
  3. **M-0 分子做实体级去重**：`per-(agent, directive_id)` 只算 1 次——两型都放行时同一事件可能产生 2 条 `MEMORY_WRITE`，不去重分子虚高一倍。
  4. **M-1 同样按 `directive_id` 去重**，并**单报**"同一 directive 的重复提及条数"。
  5. 读数表**同时列两数、不许合并**：`MEMORY_WRITE 原始条数` vs `M-0 去重命中事件数`；两者差一倍即"成对双记"发生的证据，必须写进报告，不许隐去。
  依据：A0 实测 `WORLD_DIRECTIVE(39222, D-30-wd.tension)` ↔ `WORLD_GROUP_EVENT(39223, directive_ref=D-30-wd.tension)` **1:1 配对**；记录条数 2、唯一 directive 数 1。
- **R7（2026-10-20 22:34，我自查更正）验证"可见性/时间窗"必须测**真实跑批路径**，不是 `contracts.visible_events`**
  1. 真实路径：`KernelAdapter.perceive`（`orchestration/integration.py:337-346`）→ `visibility_query`（`:322-331`）→ `VisibilityIndex.visible(..., window_rounds=VISIBLE_WINDOW_ROUNDS)`；**`VISIBLE_WINDOW_ROUNDS = 2`（`integration.py:275`）**。
  2. 离线复算/其他调用方走 `contracts.visible_events`（无 `window_rounds` 概念）——**两者结果不同**：A0 上 P001 对 seq 39222/39223，真实路径 **round 30/31/32 可见、round 33 起不可见**；`contracts.visible_events` 在 round 33/40 **仍可见**（我先前据此得出的"永久可见"是**该路径**的事实，不是真实跑批的事实）。
  3. 因此：任何"时间窗是否生效"的核验，**必须**对该臂自己的 `orchestration/visibility_index.py` + `integration.py:275` 取值复算，并记录两文件 sha；用 `contracts.visible_events` 复算只能作对照列，不得作判据。
- **R8（2026-10-20 22:38，采纳 batch-runner 的事实、修正其结论的单位）感知窗 3 回合 ⊂ 有效期 6 回合**
  1. **事实（采纳）**：`dose.slots=6` ⇒ directive 有效期 `[issued, issued+6)` = **6 回合**（`world_params.py:38-41` 的 `start<=t<end`）；真实感知窗 `[r-2, r]` = **3 回合** ⇒ **可感知覆盖率 = 3/6 = 50%**。round `+3..+5` 期间 directive 仍在 `world_params.active` 里继续作用，但**对居民不可感知**。A0/A 臂逐轮实测与 batch-runner 一致（`+0/+1/+2` 有、`+3/+4` 为 0）。
  2. **单位纪律（修正）**：`12/24 = 0.5` **不能写成 M-0 的上界**——分子单位是 `(agent, directive, round)`（每实体 4×3=12 点、6 实体共 72），分母 `agents×N_world` 是 `(agent, directive)`（24），**两个单位混用**。
     - **M-0（entity 口径，"是否曾知道"）上界仍为 1.0 = 24/24**：每个 agent 有 3 个回合机会知道，去重后 1 条即算命中；感知窗影响"何时能知道"，不降低"能否知道"。
     - 若要报"窗口内覆盖率"，**必须单列为 `感知覆盖率 = 3/6 = 50%`**（per directive，回合口径），或另设 `M-0_w`（分母 = `agents × N_world × 6` = 144，分子 = 命中的 `(agent,directive,round)` 三元组，上界 0.5）。**三套口径不得互相代入。**
  3. **L6 列差额 = 污染（采纳）**：白名单放开后，同一条 directive 在两条 OBSERVATION 通路上的可见窗不同（`_observe` = 3 回合；`settlement.py:620` L6 = 无窗）。两列表头必须各写窗口；**若 L6 列显著大于 `_observe` 列，差额 = "过期事件仍被沉淀"，判时间窗未修的污染，不得计入接通效果。**
  4. **上界 1.0 的静态依据（batch-runner 提供，作者复核）**：`life/memory.py:551-557` 的 `R_MAX_PER_WEEK` 只约束**反思**（`reflection_due`），不约束观测写入；`life/agent.py:399-421 _observe` 是 `for ev in wv.visible_events` **全量遍历**，`:403` 仅按 `_observed_seqs`（去重集）与 `_SALIENT_EVENTS` 过滤，**无每回合写入条数上限、无 salience 门限**（`_score_importance` 只决定分值，不决定是否写）。⇒ 3 个可感知回合足以让每个 agent 各写 1 条，**M-0 上界 = 1.0（24/24）** 无机制性折损。
  5. **`M-0_w` 分母必须写死为「有效期回合数」而不是「可感知回合数」**：要维持"上界 0.5"，分母 = `n_alive × Σ 每实体有效期回合数` = `4 × (6×6) = 144`（分子 = 命中的 `(agent,directive,round)` 三元组，理论上限 72 ⇒ 72/144 = 0.5）。若分母误写为 `n_alive × Σ 可感知回合数`（= `4×18 = 72`），该列上界变成 1.0、与"0.5"自相矛盾——**此时必须改名为"可感知回合命中率"并标上界 1.0，不得再标 0.5**。
