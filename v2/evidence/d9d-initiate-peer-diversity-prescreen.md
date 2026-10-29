# D9d 预筛：`_initiate` 的对端选择**已经高度分散**，该方向不开

> 立件：Leader（team-leader）｜2026-10-29
> 性质：**只读预筛**（零跑批）。目的：在开实验之前先量一次，避免再做一次 D9c 那样"机制触发了但幅度不够"的活。
> 输入：`mock_d9c_recent_n16r84_seed42/run.jsonl`（`880ff24e…`）

## 0. 代码事实（读出来的，不是猜的）

`code/life/agent.py:1137`
```python
partners = [p for p in parts if p != self.agent_id]
if tid in _DM_TEMPLATES and partners:
    scope, to = "private", partners[0]      # ← 发起对象 = 计划模板 participants 的第一个
```

看上去"永远找第一个人"，**但 `parts` 来自当前 slot 的计划模板**，而每个 slot 的活动模板不同 ⇒ `partners[0]` 实际随模板变化。**这是本次预筛要验证的点。**

## 1. 实测：对端分布（正确字段 `from`）

| 项 | 值 |
|---|---|
| 发起条数 | 266 |
| **有对端的发起** | **183**（无对端 = 83 条纯 `global`/PUBLIC，无"对端"概念） |
| 参与发起的 agent 数 | **16 / 16**（全员参与，无哑巴） |
| 不同 `(发起人, 对端)` 对 | **176**（理论上限 16×15 = 240 ⇒ **使用率 73.3%**） |
| **每 agent 独特对端数** | `4:1, 5:1, 8:1, 9:1, 10:3, 12:2, 13:4, 14:1, 15:2` ⇒ **中位 ≈12–13，11/16 的 agent ≥10 个对端**，2 个 agent 用满全部 15 人 |
| **单对端最大占比** | **mean = 0.189**；最高者 `P009` = **0.29**（7 次发起里最多找同一人 2 次） |

## 2. 判定：**不开这条线**

- 若对端选择真被 `partners[0]` 固化，应看到"每 agent 只有 2–3 个对端、单对端占比 >0.6"；
- 实测是"每人 12 个上下对端、最集中的人也只占 29%" ⇒ **分布已接近自然社交的分散度**；
- ⇒ **`to = partners[0]` 的"固定"被每-slot 模板的多样性抵消了**，这里没有可挖的瓶颈。

**结论：`_initiate` 对端选择方向关闭，不开实验、不写预登记。** 若要问"为什么某些人更常被找"，那是**模板/日程/地点亲和**的上游问题（`D2.3 place 亲和` 已做过一轮），与本处无关。

## 3. 这条预筛本身的价值

- **省掉一次实验**：若按原计划开 D9d，会是第四件"机制触发了但结构量不动"的活；
- 方法可复用：**凡"代码里看着像常量"的选择，先量一次分布再决定要不要动它**——分布分散 ⇒ 常量假设不成立，直接省掉。

## 4. 局限

1. 只统计**发起**，不含回复（回复的对端由父消息 `from` 决定，不是"选择"）。
2. 83 条纯 `global` 发起无对端概念，未计入对端统计；若把它们按 `participants` 展开会略微改变分布（本件不算，避免口径混用）。
3. 单臂（`mock_d9c_recent`）。`to` 的选择由计划模板决定，**不依赖 provider**，故 mock 结论对真 LLM 臂同样成立（此推断未在真臂上复核，但机制上 provider 不参与该决策）。
4. `participants` 含多人的群聊发起，本件把"除自己外的所有人"都算作对端 ⇒ 群聊会**高估**某些人对端数。若要严格，应只算 DM 的 `to`；本件未拆分，属已知偏差方向（偏"更分散"）。

## 5. 复算

```bash
python3 - <<'PY'
import json, collections
sp=lambda x: x.get('from') or x.get('author')
msgs=[json.loads(l)['payload'] for l in open('v2/evidence/mock_d9c_recent_n16r84_seed42/run.jsonl')
      if json.loads(l)['type'].startswith('MSG')]
inits=[m for m in msgs if not m.get('reply_to')]
def peers(m):
    me=sp(m); s=set()
    if m.get('to'): s.add(m['to'])
    for x in (m.get('participants') or []):
        if x!=me: s.add(x)
    return s
by=collections.defaultdict(collections.Counter)
for m in inits:
    for q in peers(m): by[sp(m)][q]+=1
print('agents',len(by),'pairs',sum(len(v) for v in by.values()))
print('peers per agent',dict(sorted(collections.Counter(len(v) for v in by.values()).items())))
print('mean max-share', round(sum(max(c.values())/sum(c.values()) for c in by.values())/len(by),3))
PY
# 期望：agents 16 pairs 176 / peers per agent {4:1,5:1,8:1,9:1,10:3,12:2,13:4,14:1,15:2} / mean max-share 0.189
```
