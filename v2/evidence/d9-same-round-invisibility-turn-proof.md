# 补正：同回合**感知确实不可见** —— 证据是 `turn_index` 全同值（不是 `author`，也不是"回复判定"）

> 立件：Leader（team-leader）｜2026-10-29
> 本件**补正** `v2/evidence/d9-same-round-speaker-and-reply.md`（`8f46fc06…` / 99 行，master `284c152`）**§3 的结论**。
> 该件 §3 写「**不是"看不见"**——同回合的多人发言证明他们彼此能发、能进同一线程；**是"不构成回复"**」——**这个判断错了**。本件用 `turn_index` 给出正确证据：**同回合内他们确实互相看不见**。
> 旧件与更早的 `d9-structural-no-same-round-reply.md`（`df661eb8…`）**均按纪律不覆盖、留档**。

## 0. 三次修正的关系（不许只看一件）

| 版本 | 结论 | 证据 | 状态 |
|---|---|---|---|
| `d9-structural-no-same-round-reply.md`（`df661eb8…`） | 同回合只能一个发言者 | `len({author})==1`，43/43 | ❌ **证据错**（DM/GROUP 无 `author`，恒 `None` ⇒ 恒真） |
| `d9-same-round-speaker-and-reply.md`（`8f46fc06…`） | **同回合多人发言可能**；受限的是"回复判定"，不是感知 | `from or author` 重算 43/43、27/27 均 ≥2 人 | ⚠ **前半对，后半（§3）错** |
| **本件** | **同回合多人发言可能** **且** **相互不可见** | **组内 `turn_index` 全同值**（43/43、27/27） | ✅ 现行 |

## 1. 正确证据：`turn_index` 在同组内**全同值**

| 臂 | 多人（≥2 发言人）的 `(thread,round)` 组 | 组内 `turn_index` **全相同** | 有不同 turn |
|---|---|---|---|
| `mock_d9c_recent`（`880ff24e…`） | 43 | **43 / 43** | **0** |
| 真 LLM `d1_f6off` | 27 | **27 / 27** | **0** |

组内 `turn_index` 取值分布（mock）：`{(1,): 11, (5,): 11, (3,): 9, (2,): 6, (4,): 6}`——**每组只有一个 turn 值**。

## 2. 为什么这能证明"看不见"（推理链，可核代码）

`code/life/agent.py::_send_reply`：
```python
turn = self._thread_max_turn(wv, tid) + 1     # 我看到的该线程最大 turn + 1
```
`_thread_max_turn(wv, tid)` 扫的是 **`wv.visible_events`**。

⇒ **若 B 能看到 A 在同一回合刚发的 `turn=1` 消息**，则 B 算出的 `turn = 1 + 1 = 2`。
⇒ 实测：同组内所有发言者的 `turn_index` **完全相同**（全是 1、或全是 3……），**从来没有出现"先发者 1、后发者 2"** ⇒ **后发言者没有看见先发言者的消息**。

这条证据与 `author` 无关、与 `reply_to` 无关，**只依赖 `turn_index` 与 `visible_events` 的关系**，因此不受上一次字段错误的影响。

**附带一致性**：`reply_to` 指向同回合的条数 = **0 / 663**（mock）、**0 / 480**（真 LLM）——看不见，自然回不了。三条观测（多人可发言、turn 全同、同回合回复为 0）互相吻合。

## 3. 更正后对"能不能扩 `lag`"的影响（这是关键结论）

原先我在 `284c152` 里写「受限的是**回复判定**（`_thread_replied_turn` / `_replied_msg_ids` / K 上限），不是感知」——**现在是错的，撤回**。

正确判断：

- **限制在感知（同一回合内的消息互相不可见）**，`_thread_replied_turn` 等只是**结果**，不是原因；
- ⇒ 要出现 `lag = 0`（同回合接话），**必须让同一回合内先发的消息对后发言者可见**；
- ⇒ 这是 `phase_decide` 内消息折叠时机的问题（**引擎层**），不是 `_pick_reply_target` 的判定条件问题；
- ⇒ **我此前"不动坐标系"的判断重新成立**，且理由升级：不是"要动一个不存在的锁"，而是**要动一个真实存在、且属引擎时序的锁**。

## 4. 局限（不得删）

1. `turn_index` 全同是"看不见"的**充分观察**，但**不是唯一解释**：也可能存在别的机制让 `turn` 不递增（例如某处强制把 turn 定死）。**本件未排除这一可能**，只主张"看得见"这一假说被 `turn` 数据**否定**。
2. 两臂都无"同回合可见"的对照臂 ⇒ 属**观测**，不是干预实验。
3. 本件不改变 D9b / D9c 的任何判定与数值。
4. 三次修正都在同一天、同一问题 ⇒ **该问题的结论在 24 小时内变过三次，引用时必须同时写"哪一版、哪个 sha"**。

## 5. 复算

```bash
python3 - <<'PY'
import json, collections
sp=lambda x: x.get('from') or x.get('author')
for p in ['v2/evidence/mock_d9c_recent_n16r84_seed42/run.jsonl',
          'v2/evidence/run_d1_f6off_seed42_n16r84/run.jsonl']:
    g=collections.defaultdict(list)
    for l in open(p):
        d=json.loads(l)
        if d['type'].startswith('MSG'):
            pp=d['payload']; g[(pp.get('thread_id'), d['round'])].append(pp)
    multi={k:v for k,v in g.items() if len(v)>1 and len({sp(x) for x in v})>1}
    print(p.split('/')[-2], 'multi=',len(multi),
          'same_turn=',sum(1 for v in multi.values() if len({x.get('turn_index') for x in v})==1))
PY
# 期望：multi=43 same_turn=43 / multi=27 same_turn=27
```
