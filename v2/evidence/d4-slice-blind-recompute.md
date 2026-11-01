# D4 切片底稿 v2：三份切片 + 分母重建路径 + **偏倚方向取决于口径（两种口径相反）**

> 作者：`repro-verifier`｜2026-11-01｜**只读**；未跑批、未改 `code/`、未改 `run.jsonl` 原件
> 任务：`T-D4-SLICE`
> 交付物：`v2/evidence/d4-rates-slices-v2/{emo-on-20261029,run_f4_on_n16r60_seed42,run_r6_treat_n16_seed42}.slice.jsonl`

---

## 0. ⚠ 先更正我上一条消息里的一个说法

我此前报「**本底稿的修复率基于近似分母，偏倚方向为高估**」。

**实测后必须更正：偏倚方向不是单一的，它取决于你选哪种重建口径，两种自然口径给相反方向，且跨度约 3–4 倍。**
详见 §3。这一条比"单向偏倚"更危险 —— **因为它意味着可以通过选口径得到想要的结论**。

---

## 1. 三份切片（体量）

| 批 | 原 `run.jsonl` | 切片行数 | 切片体积 | 压缩比 |
|---|---:|---:|---:|---:|
| `emo-on-20261029` | 17.2 MB | 192 | **0.094 MB** | 0.55% |
| `run_f4_on_n16r60_seed42` | 55.2 MB | 504 | **0.223 MB** | 0.40% |
| `run_r6_treat_n16_seed42` | 91.3 MB | 683 | **0.360 MB** | 0.39% |
| **合计** | 163.7 MB | 1,379 | **0.677 MB** | 0.41% |

**每行 = 一个 `MSG` 事件**，字段：`msg_uid` / `seq` / `round` / `type` / `author` / `thread_id` / `reply_to` / **`body`（全文，未截断）** / `hash` / `prev_hash` / `dialogue_rift{prompted,open,route,with,threads,age_rounds}` / `dialogue_repair{prompted,rift_ids,trigger_seqs,thread}`。

---

## 2. `rift_id` 回指核：**35/35 = 100%（两批分别 12/12、23/23）**

| 批 | `rift_ids` 条目 | `<msg_uid>` 在同批可找到 | 且 `<thread>` 匹配 |
|---|---:|---:|---:|
| `emo-on-20261029` | 12 | **12** | **12** |
| `run_f4_on_n16r60` | 23 | **23** | **23** |
| `run_r6_treat_n16` | 0（无 `dialogue_repair`） | — | — |
| **合计** | **35** | **35 / 35 = 100%** | **35 / 35 = 100%** |

**复算命令**：
```python
for rid in rift_ids:                       # 形如 R|TH-P014-P011-1|42:5039
    th, uid = rid.split("|")[1], rid.split("|")[2]
    assert uid in msg_uid_to_thread            # ① 可找到
    assert msg_uid_to_thread[uid] == th        # ② 属于该 thread
```
⇒ **"精确分子"这个前提成立** —— `rift_id` 里的 `msg_uid` 确实能回到原批定位创建时刻。

---

## 3. 分母重建路径与**偏倚区间**（核心）

### 3.1 可用字段与两种自然重建法

| 重建法 | 定义 | 性质 |
|---|---|---|
| **A：`open` 求和** | Σ(每条 `dialogue_rift.open`) | **重复计数**：同一 rift 在多次快照里被重复加 ⇒ **高估** |
| **B：`threads` 去重** | `unique(threads)` 集合大小 | 同一 thread 可能有多个 rift ⇒ **低估** |
| C：`age_rounds == 1` 出现次数 | 每个 rift"首次被看见" | **低估**（快照不连续会漏掉 age=1 那次） |

### 3.2 实测

| 批 | 快照数 | A：`open` 和（高估） | B：`unique(threads)`（低估） | C：`age==1` 计数 | **`rift_ids` 去重（精确，仅被修复者）** |
|---|---:|---:|---:|---:|---:|
| `emo-on` | 31 | **31** | **7** | 4 | **7** |
| `run_f4_on` | 41 | **48** | **14** | 13 | **16** |
| `run_r6_treat` | 139 | **168** | **50** | 32 | **0**（无 repair） |

### 3.3 结论：**方向相反，跨度 3–4 倍**

以 `run_f4_on` 为例（唯一有精确值的批）：
- 精确 `rift_ids` 去重 = **16**
- 用 **A（`open` 和 = 48）** 当分母 ⇒ 和解率 = 22/48 = 45.8% ⇒ **低估**（相对 22/16）
- 用 **B（`threads` 去重 = 14）** 当分母 ⇒ 22/14 = 157% ⇒ **高估**（且 >100%，荒谬）

⇒ **同一批数据，选 A 得"和解率不到一半"，选 B 得"和解率超过 100%"。** **口径决定结论，不是数据决定结论。**

⇒ **正确表述**：
> **D4-2 的分母在现有字段下不可靠。`open` 求和系统性高估（重复计数），`threads` 去重系统性低估（一 thread 多 rift）。二者给出的和解率相差 3–4 倍且方向相反。故 D4-2 在补 `dialogue_rift.rift_ids` 之前，任何"和解率"都不得作为跨臂比较依据。**

**⚠ 这比"单向偏倚"更严重**：单向偏倚可以标注后用；**方向相反的口径可以被挑选**，等于给"想得到什么结论就选什么口径"开了口子。

### 3.4 唯一可靠的部分
**分子**（`rift_ids` 去重，仅被修复者）**精确且可回指**（§2 已证 100%）。所以可安全报告的只有：**"被修复的 rift 绝对数"**（7 / 16 / 0），**不是"率"**。

---

## 4. ⚠ 一处卡面设计的内在矛盾：**切片无法独立验链**

卡面要求"保留 `hash`/`prev_hash` 使切片能**独立验链**"。**实测：做不到。**

```
emo-on:      192 行，含 prev_hash 192，相邻 MSG 链不连续 191 次
run_f4_on:   504 行，含 prev_hash 504，不连续 503 次
run_r6_treat:683 行，含 prev_hash 683，不连续 682 次
```

**原因**：切片只保留 `MSG`，而 `hash` 链是**跨全部事件类型**的 —— 删掉中间事件后，相邻两条 MSG 的 `prev_hash` 必然 ≠ 上一条 MSG 的 `hash`。

⇒ **二选一**：
- **(a) 保留全部事件**（体积回到 17–91 MB，失去切片意义）；
- **(b) 承认切片只保"字段完整性"，不保"链可验"**，并把"验链"降级为"须回原件"。

**我建议 (b)**，且**已实现"折中版"存在于切片内**：`hash`/`prev_hash` 足够第三方**逐条核对"这一条 MSG 的 hash 是否与原件一致"**（回原件取同 seq 比对），只是**不能在不回原件的情况下重建链**。这一条须在件内写明，否则下一个人会以为切片能自证。

---

## 5. 拿切片重算 D4 的命令（第三方可直接跑）

```python
import json, collections

# ---- D4-1 机制到位率 ----
#   分子：存在未了结 rift（dialogue_rift 存在）且 dialogue_repair.prompted==True 的 MSG 条数
#   分母：存在未了结 rift（dialogue_rift 存在）的 MSG 条数
def d41(path):
    num = den = 0
    for l in open(path, encoding="utf-8"):
        o = json.loads(l)
        if o.get("dialogue_rift") is None:
            continue
        den += 1
        rp = o.get("dialogue_repair") or {}
        if rp.get("prompted") is True:
            num += 1
    return num, den

# ---- D4-2 和解率（⚠ 分母有两种口径，方向相反，见 §3）----
def d42(path):
    ids = set(); open_sum = 0; threads = set()
    for l in open(path, encoding="utf-8"):
        o = json.loads(l)
        rp = o.get("dialogue_repair")
        if rp:
            ids |= set(rp.get("rift_ids") or [])
        dr = o.get("dialogue_rift")
        if dr:
            if isinstance(dr.get("open"), int): open_sum += dr["open"]
            threads |= set(dr.get("threads") or [])
    return len(ids), open_sum, len(threads)     # (精确分子, 高估分母A, 低估分母B)

for b in ("emo-on-20261029","run_f4_on_n16r60_seed42","run_r6_treat_n16_seed42"):
    p = f"v2/evidence/d4-rates-slices-v2/{b}.slice.jsonl"
    n, d = d41(p); m, A, B = d42(p)
    print(f"{b}: D4-1 = {n}/{d} = {n/d:.4f}" if d else f"{b}: D4-1 n/a")
    print(f"    D4-2 分子(精确)={m}  分母A(高估)={A} 分母B(低估)={B}")
```

---

## 6. 边界（引用本件时必须带）

1. **三批基座各不相同**（`f19de616` / `6b7ae8a9` / `7b6846dc`，均 ≠ `cef1c58` / ≠ `d87288e`）⇒ **跨批不可比**；
2. **`run_f4_on` / `run_r6_treat` 的开关配置未采集** ⇒ 只知道"开了 DR"，**不知道同时开了 `repair_ask` / `reply_priority` 没有** ⇒ 归因不成立；
3. **`run_r6_treat` 的 139 rift / 0 repair 未解释**（可能是配置关了 `repair_ask`，也可能是语料无修复词）—— **两种致病机理不同**（改配置 vs 改词表），**不得混为一谈**；
4. **本件不含任何"DR 有用/无用"的判断** —— 那只在"同基座两臂"前提下才可谈；
5. 单批点估计，不外推。
