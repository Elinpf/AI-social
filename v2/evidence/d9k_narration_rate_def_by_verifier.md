# 旁白率定义 · 可嵌预登记片段（`repro-verifier`）

> 用途：给 `A+B` 预登记 §2 直接嵌入的**可复算片段**（不代写预登记正文）。
> 触发：Leader 2026-10-30 07:12 要求"把定义整理成一段"；同时核实 `86.01%` 出处。

---

## 0. 定义（写死；分子/分母逐字）

```
分子 = 含 ≥1 个"成对括号块"的 MSG 条数
分母 = MSG 总数（不筛"有旁白机会"的 MSG；不排除 0 旁白的 MSG）
旁白率 = 分子 / 分母
"成对括号块" = 正则 [（(][^（）()]*[）)] 的一次匹配（全角/半角都算；要求成对；不嵌套）
```

## 1. 可嵌代码（直接粘进预登记 §2）

```python
import json, re
PAIR = re.compile(r"[（(][^（）()]*[）)]")   # 全角/半角都算，要求成对、不嵌套

def narration_rate(run_jsonl: str) -> tuple[int, int, float]:
    """旁白率 = 含≥1个成对括号块的 MSG 条数 / MSG 总数（分母不筛）。"""
    hit = tot = 0
    with open(run_jsonl, encoding="utf-8") as fh:
        for line in fh:
            if '"MSG' not in line:
                continue
            r = json.loads(line)
            if not str(r.get("type", "")).startswith("MSG"):
                continue
            body = (r.get("payload") or {}).get("body") or ""
            tot += 1
            if PAIR.search(body):
                hit += 1
    return hit, tot, (hit / tot if tot else 0.0)
```

## 2. 四个历史锚的同源验证（同一段代码、逐臂复算）

| 臂 | `meta.code_sha` | 分子/分母 | 旁白率 | 备注 |
|---|---|---|---|---|
| `run_d2_after_n16_seed42` | **`884f4541b80e5343119b51bf94054b2f54dd4559`** | **590 / 686** | **86.01%** | 真 LLM；**无禁旁白句、无示例句**（见 §3） |
| `narr-on-20261030` | `47a7da9e71e4ab31e8b58a9a5cc14105ecd0aed8` | **179 / 191** | **93.72%** | 真 LLM；`LIFE_PROMPT_NARRATION=1` |
| `run_d9_a1_n16r84_seed42` | `05636bcde2f1759b1bbc8d9eb74f43ec241be6a9` | **581 / 686** | **84.69%** | 真 LLM；不含禁旁白句 |
| `narr-off-20261030` | `47a7da9e…` | **0 / 191** | **0.00%** | 真 LLM；`LIFE_PROMPT_NARRATION` unset |

⇒ **同一段代码可同时复现四个历史锚** ⇒ 口径同源，**86.01% 可作为 A+B 验收下界**。

## 3. 对 `884f4541` 的两项前提核验（我自跑）

```
git show 884f4541:code/life/agent.py | grep -c "围裙往腰后一掖"   → 0     （无示例句）
git show 884f4541:code/life/agent.py | grep -c "不要用括号"        → 0     （无禁令）
git merge-base --is-ancestor a637371 884f4541                     → rc=1（不含禁令提交）
meta: provider=openai_compat / n=16 / rounds=84                   （真 LLM r84）
```
⇒ `run_d2_after` 确为「**无禁令 + 无示例**」真 LLM 基线，`86.01%` 成立。

## 4. 适用范围与边界（必须随定义引用）

1. **仅适用 ON 臂**（`LIFE_PROMPT_NARRATION=1`）；OFF 臂按定义 **0%**，不适用下界。
2. **分母不筛**：允许"排除 0 旁白 MSG"会把下界轻易推到 100%（稀释路径），故禁止。
3. **与"片段数"口径不同源**：若改按"旁白片段数 / MSG 数"（D9i 的 `205/191`）或"不同片段去重率"（`197/205`）计算，**结果不可与 86.01%/93.72% 比较**。
4. **嵌套/半角**：本定义**不处理嵌套**（`[^（）()]*` 不吃嵌套），全角半角同等对待；若改为嵌套感知，所有历史锚需重算。
5. **跨批比较前先跑**：任何新批与新下界比较，须用**本段代码**在同一 `run.jsonl` 上复算一次，不得引用他人报的百分比。

## 5. 复算命令

```bash
python3 - <<'PY'
# 粘贴 §1 的 narration_rate，然后：
for p in ["v2/evidence/run_d2_after_n16_seed42/run.jsonl",
          "v2/evidence/narr-on-20261030/run.jsonl",
          "v2/evidence/run_d9_a1_n16r84_seed42/run.jsonl",
          "v2/evidence/narr-off-20261030/run.jsonl"]:
    h, t, r = narration_rate(p); print(p.split('/')[-2], f"{h}/{t} = {r*100:.2f}%")
PY
```
**实际输出**
```
run_d2_after_n16_seed42 590/686 = 86.01%
narr-on-20261030        179/191 = 93.72%
run_d9_a1_n16r84_seed42 581/686 = 84.69%
narr-off-20261030       0/191 = 0.00%
```

---

## 6. 追加（2026-10-30，Leader 定稿）：**接线门槛 + 强度均值**（与 §1 同一正则、同一分母口径）

> 本节为追加物；§1–§5 原文**未改**。现行状态以**本文件当前 sha** 为准（件头若未更新，见本报文）。

### 6.1 为什么加：`旁白率 > 0` 是"没崩"，不是"接线成功"
在 191 条规模上 `> 0` 等于 `≥1/191 = 0.52%` —— **1 条旁白就过闸**。故步骤 1 必须用**绝对条数**门槛。

### 6.2 门槛（写死，**须在起跑前写进预登记，不得跑完再补**）
```
接线通过 ⇔ （含 ≥1 个成对括号块的 MSG 条数 ≥ 20）且（旁白片段总数 ≥ 20）
```
> **数的性质必须标注（Leader 要求）**：`20 / 20` 是**经验初值，不是数据推导**（191 条规模下 ≈10.5% 覆盖）。
> 与 `86.01%`（有出处、可复算）不同，**这两个数没有出处**；同一预登记里两种数**必须分别标明**。
> 复审条件：若步骤 1 实测接近门槛（如 `N_msg` 落在 20–30），须记录"门槛偏紧"并复审初值。
**三条理由**：①绝对条数不受分母选择影响（挡"稀释"路径）；②同时要求片段数（挡"1 条消息塞 10 个旁白"刷条数）；③两者都是**观测值、非比率** ⇒ 可机械复算，且**不存在"分母怎么定"这一问题**。

### 6.3 强度均值（与门槛分工）
```
强度 = 旁白片段总数 / 线程数        # 均值，不是比率
```
- **覆盖面**（`N_msg`、`N_frag`，绝对量）：管"有没有铺开"
- **强度**（片段/线程，均值）：管"铺得多厚"；小样本更稳，且**不随 body 长度虚高**（与暴露面无关）

### 6.4 复算片段（与 §1 的 `PAIR` 同一正则）
```python
PAIR_ALL = re.compile(r"[（(][^（）()]*[）)]")   # 与 §1 PAIR 完全同一正则
def narration_counts(run_jsonl: str) -> tuple[int, int, int, int]:
    """返回 (含旁白 MSG 条数, 旁白片段总数, MSG 总数, 线程数)。"""
    msg = frag = tot = 0
    threads = set()
    with open(run_jsonl, encoding="utf-8") as fh:
        for line in fh:
            if '"MSG' not in line: continue
            r = json.loads(line)
            if not str(r.get("type", "")).startswith("MSG"): continue
            pl = r.get("payload") or {}
            hits = PAIR_ALL.findall(pl.get("body") or "")
            tot += 1
            frag += len(hits)
            msg += 1 if hits else 0
            threads.add(pl.get("thread_id"))
    return msg, frag, tot, len(threads)
```

### 6.5 四个历史锚的实测（同一段代码）

| 臂 | `msg_with_narr` | `frag` | MSG | 线程 | **片段/线程（强度）** | 旁白率 |
|---|---|---|---|---|---|---|
| `run_d2_after`（`884f4541b8`，r84，无示例无禁令） | **590** | **633** | 686 | 206 | **3.07** | 86.01% |
| `narr-on`（`47a7da9e`，r24，有示例） | **179** | **205** | 191 | 66 | **3.11** | 93.72% |
| `run_d9_a1`（`05636bc`，r84，无禁令） | **581** | **619** | 686 | 206 | **3.00** | 84.69% |
| `narr-off`（`47a7da9e`，r24，unset） | **0** | **0** | 191 | 66 | **0.00** | 0.00% |

**读法**：三臂的**强度都在 3.0–3.1 片段/线程**，说明"有旁白"的臂在强度上高度接近；差别主要体现在**覆盖面**（86.01% vs 93.72%，规模不同不可直接比）。

### 6.6 与"绝对条数"原则的关系（Leader 记的那条）
> 只要指标是**绝对条数**，"分母怎么定"这个问题**根本不存在**；而今天惹麻烦的指标（`lag ≤ window`、去重率、咬合率）**全是比率**。

⇒ 建议：**验收门槛优先用绝对条数**；比率只用于**描述**，且必须同报分母与暴露面。
