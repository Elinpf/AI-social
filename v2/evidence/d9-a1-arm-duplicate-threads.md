# A1 臂 13.85% 的 DM 线程文本重复：机制是「同一 slot 内对同一对人开两个线程」，且**只有 A1 有**

> 立件：Leader（team-leader）｜2026-10-29
> 由来：`prompt-linguist` 在 `#T-D9E-LIFELINESS-READ` 里报「A1 臂 9 组 / 18 条 DM 线程文本完全相同（13.85%），F6off 0 组」。我独立复核并**找到了机制与臂特异性**。

## 1. 三臂重复率（我独立复算，逐字符级）

| 臂 | 配置 | DM 线程 | 文本完全相同的组 | 涉及线程 | 占比 |
|---|---|---|---|---|---|
| **`run_d9_a1`** | A1-回复预算 `HITT_REPLY_BUDGET=1`，r84 | 130 | **9** | **18** | **13.85%** |
| `run_d1_f6off` | F-6 off，r84 | 130 | **0** | 0 | **0.00%** |
| **`run_meal_on`** | M-1 进食闭环 ON，r60 | 114 | **0** | 0 | **0.00%** |

⇒ **重复只出现在 A1 臂**。F6off 与 M-1 ON 均为 0 —— 所以它**不是"饥饿引发的必然"**（F6off 同样有 satiety 单向滑坡，却 0 重复）。

## 2. 机制：同一 slot 内、同一对人、两个相邻 round 的线程

九个重复组全部是这个形状（`thread_id` 末段相差 1）：

```
组 ['TH-P006-P002-24', 'TH-P006-P002-25']
组 ['TH-P009-P008-24', 'TH-P009-P008-25']
组 ['TH-P014-P015-24', 'TH-P014-P015-25']
...
```

逐句比对（三组全同，无一处差异）：

```
TH-P006-P002-24 r24 slot=morning    （方老师揉了揉空空的肚子，声音有点发虚）老石，咱们先歇口气行吗？
TH-P006-P002-25 r25 slot=morning    （方老师揉了揉空空的肚子，声音有点发虚）老石，咱们先歇口气行吗？   ← 逐字相同
...  6 轮全部逐字相同
```

⇒ **同一对人、同一 slot（`morning`）、相邻两个 round（24 与 25）各开一个线程，两段对话逐字相同。**

**推断（未逐字验证 prompt，标注为推断）**：这两个线程在同 slot 内、同参与者、状态相近 ⇒ **给 LLM 的 prompt 几乎相同**；`run_d9_a1/llmcost.json` 记 `dialogue: {cached: 63, calls: 714}` —— 有 63 次缓存命中，与"同 prompt 被重复调用"一致。

**与 A1 的因果假设**：A1 打开"回复不占发起配额" ⇒ 同一 slot 内可发更多消息 ⇒ 更容易对同一对人开第二条线程；**重复是 A1 这个开关的副作用**，不是模型的普遍行为。

## 3. 影响（三条，必须执行）

1. **A1 臂的任何"多样性 / 丰富度 / 重复率"统计，必须先剔重**；直接算会把 13.85% 的复制品当独立样本，**系统性高估多样性**。
2. **对外展示样本优先用 `run_d1_f6off` 或 `run_meal_on`**，不用 `run_d9_a1`（除非该段确认不在重复组内）。
3. **A1 作为"回复预算"的正面证据要打折**：它多出来的消息里有一部分是**复制品**，不是新增的对话内容。⇒ 此前"A1 vs baseline 的 MSG +38.6%"应重新表述为「**MSG +38.6%，其中至少 18 条线程为逐字复制**」。

## 4. 与 M-1 的关系（一条有价值的旁支）

重复组的主题全是**饥饿**（"揉了揉空空的肚子""捂着肚子""肚子咕噜响"）。虽然 F6off 证明"饥饿本身不产生重复"，但 M-1 ON 臂（0 重复）说明：**居民真去吃饭之后，这类"每 round 都在喊饿"的对话场景本身大幅减少**。M-1 的判据里没有这一项，**建议在 M-1 判定件里补报本条**（作副产物，不改判据）。

## 5. 局限

1. 重复判定是**整线程逐字符哈希**（`'\n'.join(sorted_by_round_bodies)`），**不含发言人字段**；若两条线程文本相同但发言人顺序不同，本件视为重复。
2. 未逐字核 prompt；§2 的因果是推断。
3. `run_meal_on` 是 r60、A1/F6off 是 r84，**规模不同**，0% vs 13.85% 的比较不是严格对照；但"0 组 vs 9 组"的量级差异足以支持"重复是 A1 特有"。
4. 本件不改任何既有判定；只规定"怎么用 A1 的数字"。

## 6. 复算

```bash
python3 - <<'PY'
import json, collections, hashlib
for p in ['v2/evidence/run_d9_a1_n16r84_seed42/run.jsonl',
          'v2/evidence/run_d1_f6off_seed42_n16r84/run.jsonl',
          'v2/evidence/run_meal_on_n16r60_seed42/run.jsonl']:
    th=collections.defaultdict(list)
    for l in open(p):
        d=json.loads(l)
        if d['type'].startswith('MSG'):
            pp=d['payload']; th[pp.get('thread_id')].append((d['round'], pp.get('body') or ''))
    dm={t:v for t,v in th.items() if 'Gplace' not in str(t) and 'PUB' not in str(t)}
    sig=collections.defaultdict(list)
    for t,v in dm.items():
        sig[hashlib.sha256('|'.join(b for _,b in sorted(v)).encode()).hexdigest()].append(t)
    g=[x for x in sig.values() if len(x)>1]
    print(p.split('/')[-2], len(dm), len(g), sum(len(x) for x in g))
PY
# 期望：run_d9_a1 130 9 18 / run_d1_f6off 130 0 0 / run_meal_on 114 0 0
```
