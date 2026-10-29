# batch6 可行性：零成本借臂能凑多少 R=3 线程？（只读估算，未跑批）

> 核查/估算：`team-leader`｜2026-10-29｜**未跑批、未改 code/**
> 起因：batch5 暴露 `D5-01`（A1 要求 `R≥3`，而 2–3 轮层 11/12 条为 `R=2` ⇒ A 档不可达）。要同时检验 A 档可达性与 Q5/Q6，需要一批 **含足够 `R=3` 线程**的样本。

## 1. 现成臂里的 `R=3` 供给（全库 44 个有效臂）

| 配置分组 | `R=3` 唯一 `thread_id` 数（组内并集） |
|---|---|
| n16 r42 系 | **12** |
| n16 r60 系 | 10 |
| n16 r84 系 | 8 |
| 全部并集 | **33** |

## 2. 扣除已判样本后的净供给（已用 = batch1/2/3/5 共 **47** 个 id）

```
r42 系 R=3 唯一 id        12
− 与已用 47 个 id 重叠     3
= 剩余                     9
− 其中在所有臂里均为尾截断  4
= 干净可用                5   ← 只有 5 条
```

**结论：零成本借臂上限 ≈ 5 条干净 `R=3` 线程，达不到 12 条。**

## 3. 为什么"换 seed 补足"不成立

已证：同配置异 seed 的线程集合与每线程轮数 **169/169 完全相同**（见 `batch4_seed_invariance_voids_design.md`）。
⇒ **`R=3` 线程也是 seed 不变量**，多跑几个 seed 不会多出 `R=3` 线程。

## 4. 因此只剩两条路

| 方案 | 能否凑够 12 条 `R=3` | 代价 | 可比性 |
|---|---|---|---|
| **A. 借现有臂** | **不能**（上限 5 条） | 0 | 已是异配置，不可与 batch1–3 比 |
| **B. 新跑 1–2 个异配置臂**（改变 `n` 或 `rounds`，从而改变线程结构） | 可能 | 单臂 ≈ `calls 2,705`（judge 497 / dialogue 523 / importance 1,523 / reflect 112 / negotiation 34 / plan 16）⇒ **网络调用 ≈ 1,299**、墙钟 ≈ 40 min；两臂 ≈ 网络 2,598 / ≈ 80 min（串行） | 与 batch1–3 **不可比**（配置不同）；且新配置的 `R=3` 产量**必须跑完才知道**，事前只能估 |

**注**：成本数字取自 A1 臂同规模实测（`llm_calls 2,705`、墙钟 18:04→18:44）。**只报调用数与墙钟，不换算金额**。

## 5. 需要用户决定的只有一件事

**是否花「≈1,300–2,600 次网络调用、1–2 小时」去换一批能同时测 A 档与 Q5/Q6 的样本。**

- 不跑：`D5-01`（A 档不可达）、`D5-04`（Q6/Q7 零样本）、`D5-05`（人称自指）在现有语料上**永远无法检验**，v5 修订只能停在纸面。
- 跑：可能一次解决三条，但**新配置的 `R=3` 产量未知**，存在"跑完仍不够 12 条"的风险，需在预登记里写死"若不足 12 条则判不可测"。

## 6. 复算命令

```bash
python3 - <<'PY'
import json,glob,collections,os
r3=collections.defaultdict(set)
for p in glob.glob('v2/evidence/run_*/run.jsonl'):
    d=os.path.basename(os.path.dirname(p))
    if 'INVALID' in d or 'ABORTED' in d: continue
    th=collections.defaultdict(set)
    for l in open(p,encoding='utf-8'):
        l=l.strip()
        if not l: continue
        pl=json.loads(l).get('payload') or {}
        if isinstance(pl,dict) and 'thread_id' in pl: th[pl['thread_id']].add(pl.get('turn_index'))
    for t,v in th.items():
        if len(v)==3: r3[d].add(t)
print("arms:",len(r3),"union R3:",len(set().union(*r3.values())))
PY
```
预期：`arms: 44  union R3: 33`。
