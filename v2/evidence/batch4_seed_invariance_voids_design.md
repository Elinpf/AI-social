# batch4 按原规格不成立：seed 不改变线程结构（169/169 完全相同）

> 核查人：`team-leader`｜2026-10-29｜独立复算
> 起因：`codebase-scout` 报「同配置换 seed，人物对 65/65 全同」；我据此把问题推到底——**线程本身是否随 seed 变化**。
> 结论：**不变。因此 batch4（只换 5 个新 seed）不会产生任何新样本，按现规格不可执行。**

## 1. 证据（两条同配置、不同 seed 的真跑臂）

```
A = v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl    （seed 42）
B = v2/evidence/run_d28_C_s43_n16r60_seed43/run.jsonl   （seed 43）
```

| 指标 | 结果 |
|---|---|
| `thread_id` 集合 | **169 / 169，完全相同（交集 169，无一条只在单侧）** |
| 每条线程的轮数（唯一 `turn_index` 个数） | **169 / 169 完全相同** |
| 层分布 | A `{1:81, 6:52, 4:16, 2:11, 3:7, 5:2}` ＝ B `{1:81, 6:52, 4:16, 2:11, 3:7, 5:2}` |

⇒ **seed 只作用于 RNG 分支（措辞、语气、判定），不作用于"谁和谁说话"、也不作用于"聊几轮"。**

## 2. 为什么结构上会这样（机制）

- `thread_id` 形态为 `TH-<pair>-<start_round>`，**由人物对与起始回合决定，不含 seed**；
- 人物对由 place 亲和 + 日程 + 参与者选取决定（D2.3 确定性路径），seed 不参与；
- 因此换 seed 改变的是**每条线程说了什么**，不是**有哪些线程**。

## 3. 对 batch4 的直接后果（这条裁定要据此改）

原规格：`n=16 × r42 × 5 新 seed`，期望短线程层 `E[K]=20`、`P(≥12)≈0.974`、`calls 13,525`。

**该规格的前提是"新 seed ⇒ 新线程"，而实测表明前提为假**：
- 5 个新 seed 会得到**与 seed42 相同的线程集合**（同样的 `TH-…` id、同样的轮数）；
- 短线程层仍是那 8 条，其中 4 条是尾截断件 —— **已经被 batch1/batch2 用尽**；
- ⇒ **跑完不会多出任何可抽样的短线程**，13,525 次调用买到的只是"同一批线程的不同措辞"。

**裁定：batch4 按现规格不执行。** 不是成本问题，是**它不产生它要的东西**。

## 4. 出路（各自代价，供下一步决策）

| 方案 | 能得到新短线程吗 | 代价 |
|---|---|---|
| 换 seed（原 batch4） | **不能**（本文证据） | 13,525 calls 全部买"换措辞" |
| 加回合数（r42→r84） | 可能（线程有更多轮，层分布会变） | 配置变更 ⇒ **与 batch1/2/3 不可直接比**；成本约翻倍 |
| 加人数（n=16→n=32） | 可能（新人物对出现，覆盖 65/120） | 同样是配置变更；成本约翻倍 |
| 专门设计"短线程优先"的机制 | 能（但那是新机制，须预登记） | 需要改代码 + 新树 ⇒ 与现有判据语料不同源 |

**共同点**：任何能产出新短线程的路子，**都要改配置或改机制**，因此都要承担"不可与前几批直接比"的代价。**"只换 seed 就能得到干净新样本"这条路不存在。**

## 5. 边界

- 本文只用 **1 组**同配置异 seed 对照（n16r60）。若要求更强结论，应再取 1–2 组同配置异 seed 复算；但机制层面（`thread_id` 不含 seed、人物对由确定性路径决定）已给出解释，**再验只是加厚，不改变方向**。
- 本文不涉及 κ 数值、判据、抽样随机性。
- 未改 `code/`、未跑批。

## 6. 复算命令

```bash
python3 - <<'PY'
import json,collections
def lay(p):
    th=collections.defaultdict(set)
    for l in open(p,encoding='utf-8'):
        l=l.strip()
        if not l: continue
        pl=json.loads(l).get('payload') or {}
        if isinstance(pl,dict) and 'thread_id' in pl: th[pl['thread_id']].add(pl.get('turn_index'))
    return {k:len(v) for k,v in th.items()}
A=lay('v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl')
B=lay('v2/evidence/run_d28_C_s43_n16r60_seed43/run.jsonl')
print(len(A),len(B),len(set(A)&set(B)), sum(1 for k in A if k in B and A[k]==B[k]))
PY
```
预期：`169 169 169 169`。
