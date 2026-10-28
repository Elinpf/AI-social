# D12-C 短线程层：8 条中有 4 条是「尾截断」——判例 #9 是其中一条

> 核查人：`team-leader`｜2026-10-28｜**独立复算，不采信任何人口述**
> 数据源：`v2/evidence/run_a5_real_n16r42_seed42/run.jsonl`（523 条 `body`+`thread_id` 消息，round 0–41）
> 起因：`v2/refs/batch4-short-thread-spec.md` §0.1 提出「DM 且非尾截断」口径（4/93），我复算时发现该口径影响的不只是**规划分母**，还影响**已判样本的有效性**。

## 1. 复算方法

```
线程长度 = thread_id 下 MSG 条数；轮数 = 唯一 turn_index 个数
round 从 msg_id 末段数字取（`G-place:hall-67-1` → 67）；payload 无 round 字段
尾截断判定：min(round) > maxround − (max_turns−1) = 41 − 5 = 36
```

## 2. 结果：8 条 2–3 轮线程的完整清单

| thread_id | 轮数 | 条数 | `min(round)` | 尾截断? | 所属批次 |
|---|---|---|---|---|---|
| `TH-P009-P004-0` | 2 | 2 | 0 | 否 | batch2 |
| `TH-P011-P012-0` | 2 | 2 | 0 | 否 | batch2 |
| `TH-P001-P009-18` | 2 | 2 | 18 | 否 | batch2 |
| `TH-P016-P005-18` | 2 | 2 | 18 | 否 | batch1 |
| `TH-P002-P007-39` | 3 | 3 | **39** | **是** | batch1 |
| `TH-P005-P013-39` | 3 | 3 | **39** | **是** | batch1 |
| `TH-P002-P007-40` | 2 | 2 | **40** | **是** | batch1 |
| `TH-P015-P011-40` | 2 | 2 | **40** | **是** | batch2 |

**分布**：自然短线程 **4 条**；尾截断 **4 条**（rmin 39/39/40/40，全部贴着 `maxround=41`）。
**批次构成**：batch1 的短线程层 = 1 自然 + **3 截断**；batch2 = 3 自然 + **1 截断**。

## 3. 这一条为什么重要：判例 #9 是被截断的

batch2 的 C 档 2 条之中，**`TH-P015-P011-40` 是尾截断线程**（rmin=40，run 在 41 结束）。

而这条正是 v3/v4 **Q6「回合失接」的旗舰判例**——prompt-linguist 的原话是「提问方已自行推迟（'等我把这勺糖色熬明白了再喊你'），回答方却'你那条肉先别急着喊我搭手吧'⇒ 拒绝了一件没被提出的请求」。

**但这个"失接"完全可能由截断造成**：线程在第 40 轮开始、第 41 轮结束，**后续回合没有机会出现**。若线程继续到第 42–43 轮，提问方很可能真的来喊人搭手，那么回答方的"先别急着喊"就是**正确的提前声明**，不是误读。

⇒ **该判例不足以支撑"回合失接"这一缺陷类型的存在**。Q6 的实证支撑从「2 条样本」降为「**1 条干净样本**」（`TH-P001-P009-18`，rmin=18，自然短线程）。

## 4. 连带影响（逐条写清，不含推论）

1. **Q6 阈值 `Q6 ≥ 1 ⇒ C` 的样本支撑**：干净样本 **1 条**。v4 §「v3 仍不足」里写的是 2 条，须更正为 1 条，并注明另一条为截断artifact。
2. **batch1 的短线程层 75% 是截断件**（3/4）。batch1 若曾用该层做任何判断，其结论须标注"该层样本以截断件为主"。
3. **batch2 的 C=2 之中，1 条干净（#12）、1 条截断（#9）**。此前文书中「本批确有 2 条 C」在**计数上仍成立**（判读者确实判了 2 条 C），但**作为缺陷类型的证据只有 1 条**。两个说法要分开写，不得合并。
4. **「池内穷尽」的含义要修正**：8 条里只有 4 条是"可用的自然短线程"，另外 4 条是运行边界产生的截断件。⇒ 本臂短线程层的**有效供给是 4 条，不是 8 条**，batch4 的规划分母用 `4/93` 是**正确且偏保守**的选择，spec 该口径应当保留并被引用。
5. **batch4 抽样必须显式排除尾截断线程**，否则新一批会重复引入同一 artifact。spec §2.3 排除名单需补这一条（不是只排除已用 24 个 id）。

## 5. 判定档（本条自身）

**「事实成立，影响为限定而非推翻」**：
- 不推翻 batch2 的 `不可判（判据未定型）`，也不推翻 batch3 的 `不可判（无干净第二读者 + 判据已知有缺口）`；
- 但**推翻"Q6 有 2 条样本支撑"这一表述**，改为「1 条干净 + 1 条截断artifact，Q6 属**未定型的单例**」；
- **不因此改 v4 的规则条文**（Q6 是否成立与样本够不够是两件事：规则可以保留，但必须标注"实证支撑 = 1 例"）。

## 6. 复算命令（只读）

```bash
python3 - <<'PY'
import json,collections,re
p='v2/evidence/run_a5_real_n16r42_seed42/run.jsonl'
msgs=[json.loads(l)['payload'] for l in open(p,encoding='utf-8')
      if l.strip() and isinstance(json.loads(l).get('payload'),dict)
      and 'body' in json.loads(l)['payload'] and 'thread_id' in json.loads(l)['payload']]
def rnd(m):
    mm=re.findall(r'-(\d+)-', m.get('msg_id') or '')
    return int(mm[-1]) if mm else None
th=collections.defaultdict(list)
for m in msgs: th[m['thread_id']].append(m)
maxr=max(rnd(m) for m in msgs if rnd(m) is not None)
for t,ms in th.items():
    turns=len({m.get('turn_index') for m in ms})
    if 2<=turns<=3:
        rmin=min(rnd(m) for m in ms)
        print(t, turns, len(ms), rmin, 'TAIL' if rmin>maxr-5 else '')
PY
```
预期输出：8 行，其中 `TAIL` 4 行（`TH-P002-P007-39` / `TH-P005-P013-39` / `TH-P002-P007-40` / `TH-P015-P011-40`）。
