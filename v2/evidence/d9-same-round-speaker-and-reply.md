# 更正并废止：同回合内**多人发言是可能的**；受限的是「回复」不是「感知」

> 立件：Leader（team-leader）｜2026-10-29
> **本件废止** `v2/evidence/d9-structural-no-same-round-reply.md`（`df661eb8…` / 88 行，master `ea782c0`）的**核心结论**。旧件按纪律**不原地覆盖**，保持原 sha 留档。
> 性质：只读、两臂交叉、可复算。

## 0. 一句话

旧件写「同回合内同一线程只能有一个发言者（43/43、27/27）」——**这个结论是错的**。它由**字段用错**造成：`MSG_DM`/`MSG_GROUP` 的发言人字段是 **`from`**，不是 `author`；`author` 只存在于 `MSG_PUBLIC`。用 `author` 去取 DM/GROUP 的发言人**恒得 `None`**，于是 `len({None}) == 1` **恒真**，看上去就是"全是同一人"。**用正确字段重算：43/43 与 27/27 都是「≥2 个不同发言人」。**

仍然成立的只有下面这条：**`reply_to` 指向同回合的条数 = 0**（`0/663`、`0/480`）——**同回合内没人回复同回合发出的消息**。

## 1. 错在哪（可复算）

| 事件类型 | 条数（mock ctrl） | 发言人字段 | 用 `author` 取的结果 |
|---|---|---|---|
| `MSG_PUBLIC` | 91 | **`author`** | 正常 |
| `MSG_DM` | 643 | **`from`** | **恒 `None`** |
| `MSG_GROUP` | 195 | **`from`** | **恒 `None`** |

旧件的判定式是 `len({x.get('author') for x in v}) == 1`。在 DM/GROUP 组成的组里，集合恒为 `{None}`，长度恒为 1 ⇒ **判定恒真**，与"谁在说话"**完全无关**。

复算（正确字段 `from or author`）：

| 臂 | MSG | 无发言人字段的条数 | 多条 `(thread,round)` 组 | 其中发言人 **≥2 人** |
|---|---|---|---|---|
| `mock_d9c_recent`（`880ff24e…`） | 929 | **0** | 43 | **43 / 43** |
| 真 LLM `d1_f6off`（`93516639B`） | 686 | **0** | 27 | **27 / 27** |

## 2. 真实形态（样例）

群聊场景里，**多个不同人可以在同一回合、对同一条父消息各自回复**：

```
组 ('TH-P013-Gplace-library-61', round=62)  ← 组聊
  P005 turn=1 reply_to=42:120402  你家菜园子今年的收成怎么样？
  P006 turn=1 reply_to=42:120402  早上好呀，今天的集市看着挺热闹。
  P012 turn=1 reply_to=42:120402  最近雨水多，出门记得带把伞。
  P016 turn=1 reply_to=42:120402  早上好呀，今天的集市看着挺热闹。
```

⇒ **同回合多人发言是结构允许的**，而且 `max_turns_per_round=2` 也没有阻止它。

## 3. 仍然成立的那一条（这才是真约束）

`reply_to` 指向**同回合**父消息的条数：mock **0 / 663**、真 LLM **0 / 480**。

⇒ 同回合内虽然**有多人在说话**，但**没有人去"回复"本回合刚发出的消息**。区别很关键：

- **不是"看不见"**——同回合的多人发言证明他们彼此能发、能进同一线程；
- **是"不构成回复"**——`reply_to` 从不指向同回合。

**候选原因（未验证，按代码读出的顺序列，不做因果断言）**：
1. `_pick_reply_target` 的 `if int(self._thread_replied_turn.get(tid, -1)) >= max_turn: continue` —— 同一线程最新一轮"我已经接过"就跳过；
2. `_replied_msg_ids` 去重；
3. `max_turns_per_round=2`（K 上限）在单回合内最多推进 2 轮。

**本件不做定位，只把可验证的观测写死；定位需专门实验（改一个条件、看 `lag=0` 是否出现）。**

## 4. 对既有结论的影响

| 件 | 影响 |
|---|---|
| `d9-structural-no-same-round-reply.md`（`df661eb8…`） | **核心结论作废**（"只能一个发言者"）；其 §3 对 D9b/D9c 方向判断中依赖该结论的部分**不得再引用**。"`lag=0` 恒为 0"这一观测**仍成立**。 |
| `d9b_reply_window_on_A1_base_result.md` | **无影响**（用 `reply_to`/`msg_uid`/`round`，不依赖发言人字段） |
| `d9c_reply_pick_order_result.md` | 其 §3 表"`lag=0` 条数"一格的括注引用旧件，**须改为引用本件**；判定（不可判·判据未覆盖）与 §4.3（方向作废）**不受影响** |
| "扩 `lag` 区间要动『同回合单发言者』不变量" | **这个说法作废**：该不变量不存在。要扩区间，得先查清"为什么不回复同回合"，而不是"解开一个不存在的锁" |

## 5. 教训（写进纪律，比本件结论更重要）

> **空值字段参与 `len({...}) == 1` 这类"是否唯一"判定，必然恒真。**
> 判定"是不是同一个人"之前，**必须先确认该字段在每种事件类型里都存在**，并把"缺字段的条数"打印出来。

这与今天另外两个错是同一族：**把结构性必真当成观测到的证据**（另两例：`lag ≤ window` 覆盖率在 `window ≥ 2` 时恒 100%；`M-1-a` 的 `OFF = 0` 由代码构造保证）。三次都是同一个病根，**必须在预登记阶段就用"这个量在什么情况下恒真"过一遍**。

## 6. 复算

```bash
python3 - <<'PY'
import json, collections
sp=lambda x: x.get('from') or x.get('author')
for p in ['v2/evidence/mock_d9c_recent_n16r84_seed42/run.jsonl',
          'v2/evidence/run_d1_f6off_seed42_n16r84/run.jsonl']:
    g=collections.defaultdict(list); by_uid={}
    for l in open(p):
        d=json.loads(l)
        if d['type'].startswith('MSG'):
            pp=d['payload']; g[(pp.get('thread_id'), d['round'])].append(pp)
            if pp.get('msg_uid'): by_uid[pp['msg_uid']]=d['round']
    multi={k:v for k,v in g.items() if len(v)>1}
    same=[m for k,v in g.items() for m in v if m.get('reply_to') and by_uid.get(m['reply_to'])==k[1]]
    print(p.split('/')[-2],
          'multi=',len(multi),
          'multi_ge2_speaker=',sum(1 for v in multi.values() if len({sp(x) for x in v})>1),
          'reply_to_same_round=',len(same))
PY
# 期望：multi=43 multi_ge2_speaker=43 reply_to_same_round=0
#       multi=27 multi_ge2_speaker=27 reply_to_same_round=0
```
