# T264 步骤1：`visible_events` 两份实现**不等价**（真缺陷，未合并）

> 作者：kernel-dev ｜ 2026-10-12 ｜ 结论：**不等价 → 按任务要求"报差异 + 报 Leader，勿自行选一个"**

## 最小差分证据（可复现）
```python
from life.visibility import visible_events as life_vis
from engine.perceive import visible_events as eng_vis
recs=[
 {'seq':0,'round':0,'phase':0,'actor':'SYSTEM','type':'WORLD_INIT','payload':{}},
 {'seq':1,'round':1,'phase':2,'actor':'A','type':'OFFER_CREATED',
  'payload':{'offer_id':'o','from':'A','to':['B'],'kind':'sale','terms':{}}},
 {'seq':2,'round':1,'phase':2,'actor':'SYSTEM','type':'NEED_UPDATE',
  'payload':{'agent_id':'X','subject':'C','dim':'energy','after':50}},
]
# 输出：
# A engine [1] life []   DIFF
# B engine [1] life []   DIFF
# C engine []  life [2]  DIFF
# X engine [2] life [2]  same
```

## 差异清单
### D1 · `OFFER_CREATED` 定向要约分档（engine 有，life 无）
- `engine.perceive.visible_events`：`OFFER_CREATED` **动态分档**——`to==[]`→`global`；`to` 非空→`private`（对 `{from,to}` + `to` 名单）。
- `life.visibility.visible_events`：**无此特判**；`OFFER_CREATED` 不在 `PERCEPTION_SCOPE` → 落 `default=place_local`，而 `OFFER_CREATED.payload` **无 `place`** → `place(None) != loc(residence)` → **对该要约实际不可见**。
- 后果（real kernel）：**同一回合两套可见性**——agent 感知（`orchestration.KernelAdapter.perceive`）能看到定向要约，但 **L6 `write_memories`（走 `life.visibility`）看不到**。→ 记忆/传播与感知不一致。

### D2 · `subject_only` / `private` 是否含 `payload.subject`（life 有，engine 无）
- `life._visible`：`... or p.get("subject") == agent_id`（**含 subject**）。
- `engine`：`subject_only`/`private` 分支**不含 subject**（仅 `agent_id/observer/from/actor`）。
- 后果：带 `subject` 的事件（如 `NEED_UPDATE{subject=C}`）对 **C 本人**：life 可见、engine 不可见 → DIFF（证据中 `C` 行）。

### D3 · 第三份实现（任务描述只列了两份）
- `orchestration/integration.py::KernelAdapter.perceive` **内联**了第三套可见性（含 D1 的 `OFFER_CREATED` 动态 + `private` 含 `to` 名单）。
- 即：真实机路上 **agent 感知**走 adapter、**L6 记忆**走 `life.visibility`、**engine.perceive** 另有其一。**共三处**，且语义两两不一致。

## 为什么"逐字节不变合并"此刻不能做
验收判据要求"改后 `visible_events` 输出与改前**完全一致**"。但**改前本身就是两套不同语义**——合并**必然改变其中一处的输出**（至少 D1/D2）。故必须先**裁决唯一正确语义**，再谈增量索引。

## 请 Leader 裁决（3 问）
1. **以哪份为准**？我的建议：以 **engine/adapter 语义**为准（含 `OFFER_CREATED` 动态分档，已被 **T137 契约**固化；`private` 含 `to` 名单），`life.visibility` 向其对齐。——但**按任务要求我不自行选**。
2. `subject_only`/`private` **是否纳入 `payload.subject`**？（life 现状纳入；engine 不纳入）
3. `members` **是否含 `actor==agent_id` 回退**？（engine 含；life 不含）

裁决后我再执行「单真源 + 增量索引（按 scope 预分桶 + location 增量）」，并保证**以裁决后的真源**逐字节一致 + 复杂度实测。

## 附：更正一条我先前误报
`life/tests/test_t127_judgment_dims.py::test_stance_can_flip` 我先前报"疑似死循环"——Leader 实测 **70.6s 慢**，非死循环。特此更正。
