# d12c 人物对聚类：线程嵌套结构与 seed 无关性（只读复算）

> 作者：`codebase-scout`（只读；**未改任何源码、未做 git 写操作**）
> 时刻：`2026-10-29 04:2x`｜**状态：已落盘、未 commit**（提交权在 Leader）
> 触发：Leader 要求把 `artifacts/reports/D1e-第三批池子算术独立复算.md` §6 的人物对核验落进仓库，并回答「batch4 换 5 个新 seed 能否拿到新人物对」。

---

## 0. 一页结论

| # | 结论 | 实测 |
|---|---|---|
| 1 | **线程强嵌套于人物对**：140 条线程只来自 **36 组两人对**（另有 32 条单人 `MSG_PUBLIC` 线程不属于任何对） | `{1:8, 2:13, 3:3, 4:6, 5:2, 6:1, 8:2, 9:1}`，单对最多 **9** 条 |
| 2 | **单臂对覆盖 = 36/120 = 30.0%**（C(16,2)=120） | 见 §2 |
| 3 | 第三批 12 条中 **9 条复用前两批人物对**，仅 **3 条**为全新对 | 见 §4 清单 |
| 4 | ⭐ **换 seed 不改变人物对集合**：同配置下 seed42 与 seed43 两臂的 65 组对**完全相同**（交集 65/65） | 见 §3 |
| 5 | 文本层面无重复：首句 4-gram Jaccard 最大 **0.068**，阈值 0.6 命中 **0/12** | 见 §5 |

**⇒ 对 Leader 问题的直接回答（只给数，不建议）**：在**同一配置**下把 seed 换成 5 个新的，**预计一个新人物对也拿不到**（§3 已用两个真 seed 实测：65/65 全同）。人物对由**配置与回合数**决定（r42→36 组、r60→65 组），不由 seed 决定。

---

## 1. 口径（先声明，否则数字不可比）

- **"本臂"= A5 臂**：`v2/evidence/run_a5_real_n16r42_seed42/run.jsonl`
  （sha256 `aa6edc351cefdd9983ba8a58a4e673aaf7890cc742a5761f3dd5d2c1cd569e24`，62,027 事件）。
- **线程真源**：`MSG_*/payload.thread_id`。
- **人物对**：一条线程里出现过的 `from/to` 两个不同 agent，取 `tuple(sorted(...))`；**仅统计恰好 2 人的线程**（DM）。**无 `to` 的 `MSG_PUBLIC` 线程不计入"对"**（否则会把单元素集合误当对，见 §2 修正说明）。
- **"轮数" = 线程内消息条数**。

### ⚠️ 修正（我在上一版报了个偏大的数）

`D1e` §6.2 写的「140 条线程只来自 **46** 组人物对」是**口径错误**：当时把「只有 1 个参与者的线程（32 条 `MSG_PUBLIC`）」的**单元素集合**也算成了"对"，于是把 46 个"参与者集合"当成了 46 组"人物对"。正确值：

```
线程总数: 140 | 两人对线程: 108 | 非两人对线程: 32
不同两人对: 36 | 每对线程数分布: {1:8, 2:13, 3:3, 4:6, 5:2, 6:1, 8:2, 9:1}
线程数最多(前6): (P005,P016)=9  (P009,P010)=8  (P001,P012)=8  (P011,P013)=6  (P005,P007)=5  (P008,P011)=5
非两人对的形态分布: {1: 32}   # 全部是 MSG_PUBLIC 单人线程
```

**结论方向不变**（嵌套仍在、有效独立量仍 < 样本量），但**引用时请用 36，不要再用 46**。

---

## 2. 覆盖度

```
agents 总数 = 16        C(16,2) = 120
A5 臂(r42) 两人对 = 36  ⇒ 覆盖 36/120 = 30.0%
r60 臂(见 §3) 两人对 = 65 ⇒ 覆盖 65/120 = 54.2%
```

---

## 3. ⭐ seed 无关性（本文件最重要的一条）

两次**真跑**、**同配置（同 `engine_version` 指纹）**、**只差 seed**：

| 臂 | seed（日志内 `WORLD_INIT.seed`） | 事件 | 线程 | 两人对 | 首回合 `state_hash` |
|---|---|---|---|---|---|
| `run_d12c_on_n16r60_seed42` | **42** | — | 169 | **65** | `sha256:acd19f0f8cba0…` |
| `run_d28_C_s43_n16r60_seed43` | **43** | — | 169 | **65** | `sha256:5824185281ac9…` |

```
两臂两人对: 65 vs 65 | 交集=65 | 相同? True
```

- **两臂确实不是同一份文件**：sha256 分别为 `bd2df77f…6c87` 与 `e3518b63…ae36`；日志内 seed 分别为 42/43；首回合 `state_hash` 不同（证明是两次独立真跑）。
- **但两人对集合逐条相同**（65/65，交集 65）。
- 两臂 `WORLD_INIT.fingerprint` 均以 `sha256:a871e36c4…` 开头（同配置）。

⇒ **"谁和谁说话"在同配置下与 seed 无关**；它由人物/场所/日程结构决定（D2.3 的 place 亲和选择是确定性路径），seed 只影响 RNG 分支（语气、措辞、判定等）。

---

## 4. 第三批 12 条的人物对归属

**9/12 复用前两批已出现过的人物对；3/12 为全新对。**

| b3 线程 | 人物对 | 前两批同对旧线程数 | 同对旧线程 |
|---|---|---|---|
| TH-P010-P009-1 | P009-P010 | 2 | TH-P010-P009-0, TH-P010-P009-6 |
| TH-P010-P009-12 | P009-P010 | 2 | 同上 |
| TH-P010-P009-37 | P009-P010 | 2 | 同上 |
| TH-P012-P001-19 | P001-P012 | 3 | TH-P012-P001-25, -30, -36 |
| TH-P012-P001-37 | P001-P012 | 3 | 同上 |
| TH-P013-P004-16 | P004-P013 | 2 | TH-P004-P013-20, TH-P004-P013-3 |
| TH-P016-P005-13 | P005-P016 | 1 | TH-P016-P005-18 |
| TH-P016-P005-19 | P005-P016 | 1 | 同上 |
| TH-P016-P005-6 | P005-P016 | 1 | 同上 |

**全新人物对（前两批无同对）：3 条**
`TH-P006-P003-12`、`TH-P006-P003-6`（对 P003-P006）、`TH-P009-P008-24`（对 P008-P009）。

---

## 5. 文本层面：无重复（阈值 0.6 命中 0/12）

口径：首句去空白/中英标点后取 4-gram 集合，Jaccard。

```
阈值 J>=0.6 的命中数（同对或全局）：0 / 12
最大同对相似 = 0.068 ；最大全局相似 = 0.068
```

最像的一对：`TH-P016-P005-13` vs `TH-P016-P005-18` = **0.068**（同题材不同对话）。

⇒ 「批次不重叠」在 **id 层**与**文本层**两重成立；**但在人物对层不成立**（§4）。

---

## 6. 必须随 κ 并列引用的局限（Leader 已采用的原句）

> 样本以线程为单位，但线程嵌套于 46 组人物对（单对最多 9 条）；因此按线程数算的 κ 标准误偏乐观。

**请把其中的 `46` 改为 `36`**（见 §1 修正）。定稿版：

> 样本以线程为单位，但线程嵌套于 **36** 组人物对（单对最多 9 条）；因此按线程数算的 κ 标准误偏乐观。

并补一句（本次新增，直接来自 §3）：

> 该嵌套是**该臂的结构属性**：同配置下换 seed 不改变人物对集合（实测 seed42 vs seed43 的 65 组对完全相同），故"再抽一批更干净的样本"或"换新 seed"都**不能**消除嵌套。

---

## 7. 复算脚本（只读，可直接重跑）

```python
import json, collections

# --- 1) 单臂：线程 → 人物对 ---
thr = collections.defaultdict(set)
for line in open('v2/evidence/run_a5_real_n16r42_seed42/run.jsonl', encoding='utf-8'):
    line = line.strip()
    if not line: continue
    r = json.loads(line)
    if r['type'] not in ('MSG_DM','MSG_GROUP','MSG_PUBLIC'): continue
    p = r['payload']; t = p.get('thread_id')
    if not t: continue
    frm = p.get('from') or p.get('author'); to = p.get('to')
    for x in (frm, to):
        if x: thr[t].add(x)

two = {t: tuple(sorted(v)) for t, v in thr.items() if len(v) == 2}
d = collections.Counter(two.values())
print('两人对线程=%d 不同两人对=%d 分布=%s' % (len(two), len(d), dict(sorted(collections.Counter(d.values()).items()))))

# --- 2) seed 无关性：两个同配置、不同 seed 的臂 ---
def pairs(f):
    s = set()
    for line in open(f, encoding='utf-8'):
        line = line.strip()
        if not line: continue
        r = json.loads(line)
        if r['type'] not in ('MSG_DM','MSG_GROUP','MSG_PUBLIC'): continue
        p = r['payload']; t = p.get('thread_id')
        if not t: continue
        frm = p.get('from') or p.get('author'); to = p.get('to')
        if frm and to: s.add(tuple(sorted((frm, to))))
    return s
a = pairs('v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl')
b = pairs('v2/evidence/run_d28_C_s43_n16r60_seed43/run.jsonl')
print('seed42 对=%d | seed43 对=%d | 交集=%d | 相同=%s' % (len(a), len(b), len(a & b), a == b))
```

---

## 8. 输入文件 sha256（全部绑定）

```
aa6edc351cefdd9983ba8a58a4e673aaf7890cc742a5761f3dd5d2c1cd569e24  run_a5_real_n16r42_seed42/run.jsonl
bd2df77fd125cc75c31f261cc05486bd7376d9a9fcd9334f083cf8897e496c87  run_d12c_on_n16r60_seed42/run.jsonl
e3518b63f3a587e93f11cf0fa56e4e7c97f807de9e198aab17cb8968051aae36  run_d28_C_s43_n16r60_seed43/run.jsonl
9bb0d79eb2e53bd6094482f0160eb0a26c207a9b539f39fc897a66a377ac79e1  d12c_a5_sampled_threads_raw.txt
0ffeac1ea1623066d03bdf2e0c9ee3094dc8fa8fa4767e06b9c1b27142420da0  d12c_a5_batch2_sampled_threads_raw.txt
7a7f8ff69de441f3597306494fe8bec1cdc8b6a256c7a3fdb311d2dfca3bade0  d12c_batch3_sampled_raw.txt
```

---

## 9. 边界（未做 / 不属我域）

| 项 | 说明 |
|---|---|
| κ 数值、判据有效性 | **不做**（我未参与盲评，不介入判读） |
| 4-gram 之外的口径 | 未做；如需换口径请示阈值 |
| 抽样是否分层随机 | 未做（抽样件只有结果、无 RNG 记录） |
| batch4 该不该跑、跑几个 seed | **不做建议**（Leader 域）；本文件只给"换 seed 不改变人物对"这一事实 |
| 别的配置下 seed 是否仍无影响 | **UNKNOWN**：实证只有 1 组 (42 vs 43)@r60；若要更强结论需再取 1 组同配置不同 seed |
