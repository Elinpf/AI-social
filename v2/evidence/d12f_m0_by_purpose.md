# D12-F M0 分层曲线 + 旁证：相邻轮同输入

> ⚠ **时点更正（2026-10-23 16:58，run-warden 自我更正）**：本文件的「时间点/seals」是手写标注，与实际采集时刻不符（本文件正文由 ~16:53 的一次读取生成，当时真实 seals 已 ≥40）。**权威版本改用单次采集 wrapper 的产物**：`v2/evidence/d12f_gates_partial.json`、`d12f_m0_curve_partial.json`、`d12f_adjacent_dialogue_pairs_partial.md`（三份同一 `snapshot_at`）。本文件保留作历史快照，**不得作为终态或复核依据**。


> **PARTIAL（跑批进行中）**｜时间点：2026-10-23 16:48–16:57 (+08:00)｜seals 36/60、max_round 35、lines 56,634
> seed 42 / agents 16 / rounds 60｜run.jsonl sha256 见 `v2/evidence/d12f_m0_curve.json`
> 读数人：run-warden（独立复算，未照抄 auditor 预核；数值一致属交叉验证）
> 复算脚本：`v2/evidence/d12f_m0_curve.py`（纯新文件、纯标准库）
> ⚠ 终态须另出一版「终态版」，本文件只是 partial，**不得当终态判据**。

## A. 按 purpose 分层的新调用率（每 10 轮一档）

| 档 | overall 新调用率 | `dialogue` 新调用率 | `importance` 缓存率 |
|---|---|---|---|
| r0-9 | 72.98% | **100.0%**（cached 0/273） | 80.46% |
| r10-19 | 30.74% | **100.0%**（0/249） | 93.75% |
| r20-29 | 91.51% | **94.44%**（12/216） | —（该档无 importance 调用） |
| r30-39 | 100.00% | **100.0%**（0/144） | — |

全批（seals 36 时点）：

| purpose | calls | cached | cached% | 新调用率 |
|---|---|---|---|---|
| **dialogue** | 954 | 27 | **2.83%** | **97.17%** |
| importance | 1523 | 1387 | **91.07%** | 8.93% |
| judge | 473 | 0 | 0.00% | 100% |
| plan | 16 | 0 | 0.00% | 100% |
| reflect | 112 | 4 | 3.57% | 96.43% |
| negotiation | 34 | 19 | 55.88% | 44.12% |
| **ALL** | **3112** | **1437** | **46.18%** | **53.82%（= M0 overall）** |

**结论（只陈述读数，不写"全部来自"）**：overall 翻倍下滑的**主要来源是 `importance`**（91.07% 命中，且占全批调用 1523/3112 = 49%；集中在 r10 单轮 1,216 次）；**`negotiation` 次之**（55.88% 命中，样本仅 34 次）；`dialogue` 层恒在 1–3% 命中区间（干净）。

> 措辞更正（2026-10-23 16:57，auditor 复核后）：原句「M0 下滑全部来自 importance」**过度概括**，已改为"主要来自 importance + negotiation 次之"。# 两个时点的数并存时必须带 seals：本文件为 seals 36 时点（M0=53.82%）；auditor 16:56 seals 40 时点为 M0=54.58%，差异仅来自新增轮次。

## B. `importance` 高命中的机制证据（cache_key 复用率，不是凭"命中率高"猜）

`importance` 共 1523 次调用，但只有 **136 个不同 `cache_key` / 136 个不同 `prompt_hash`**（一一对应），**单 key 最高复用 16 次 = 16 个 agent 各调一次同一 prompt**。

调用发生位置：**全部在 round ≤10**（r1 77、r4 92、r7 118、r8 20、**r10 单轮 1,216**）；r10 是第 0 天结算的批量记忆重要性打分。

⇒ 性质：**同一批 prompt 被 16 个 agent 重复调用 + 批处理集中在 r10 一轮**，缓存命中是正确行为（同输入同输出），不是"数据造假"；但它在这 10 轮里把 overall 分母一次性推大 ⇒ overall 被稀释。**与对话采样无关。**

## C. 旁证：相邻轮同输入（**与 M0 分开记**，这是"生活气息"问题，不是缓存问题）

27 组重复 key = **9 条消息 × 3 候选**（D12-E/D12-F 都是 M=3，所以一条消息的 3 个候选各命中一次）。逐条：

| # | 轮次 | agent | thread（前轮 → 后轮） | 两轮 body 是否相同 |
|---|---|---|---|---|
| 1 | r24→r25 | P006 | `TH-P006-P002-24` → `TH-P006-P002-25` | **不同** |
| 2 | r24→r25 | P007 | `TH-P007-PUB-24-0` → `TH-P007-PUB-25-0` | **不同** |
| 3 | r24→r25 | P009 | `TH-P009-P008-24` → `TH-P009-P008-25` | **不同** |
| 4 | r24→r25 | P014 | `TH-P014-P015-24` → `TH-P014-P015-25` | **不同** |
| 5 | r36→r37 | P004 | `TH-P004-PUB-36-0` → `TH-P004-PUB-37-0` | **不同** |
| 6 | r36→r37 | P005 | `TH-P005-PUB-36-0` → `TH-P005-PUB-37-0` | **不同** |
| 7 | r36→r37 | P007 | `TH-P007-PUB-36-0` → `TH-P007-PUB-37-0` | **不同** |
| 8 | r36→r37 | P008 | `TH-P008-PUB-36-0` → `TH-P008-PUB-37-0` | **不同** |
| 9 | r36→r37 | P013 | `TH-P013-PUB-36-0` → `TH-P013-PUB-37-0` | **不同** |

样例（P006，两轮 body 实文）：
- r24：`老石，我这第三格粉笔盒都空了，肚子也饿得直打鼓——先歇口气吧，上回小满问的那道题…`
- r25：`我正把第三格粉笔盒合上，肚子却饿得直响——老石，先别急着出拳，你上次答应教小满那…`

**body 不同但 prompt 逐字节相同**，原因是：三候选文本被缓存复用（同一 prompt → 同一候选集），而**择优用的"最近 16 条台词"变了 ⇒ `picked` 变了 ⇒ 选出的候选不同**。所以 body 不同恰恰证明"择优在起作用"，而 prompt 相同说明"给模型的输入没变"。

### C.1 这是"空转"还是"hash 撞车"？

| 判据 | 读数 | 结论 |
|---|---|---|
| 27 组的构成 | 每组**恰好两次调用**（前一轮 `cached=false` + 本轮 `cached=true`）；组内 **`prompt_hash` 相同、`cache_key` 也相同**；27 组的 `prompt_hash` 互相不同；同轮内无重复 | **不是 hash 撞车**（撞车需"不同输入同 hash"，此处是"相同输入同 key"）；口径：`prompt_hash` 与 `cache_key` 是两个不同的哈希，**不得写成"两者相等"** |
| 两轮之间该 agent 是否有自有事件 | **有，且很多**：P006 106 条、P007 79/60 条、P009 106、P014 106、P004 91、P005 66、P008 87、P013 69（NEED_UPDATE / MEMORY_WRITE / ACTIVITY_STARTED / METABOLISM / OBSERVATION 等） | 状态在动，**但渲染进 prompt 的字段没变** |
| prompt 渲染字段包含什么 | 见 `v2/evidence/d12f_wiring_proof.md` §2 原文：人格 / 场景 / 对象与熟悉度好感 / 情绪 / **最紧的需求** / 当前目标 / D12C 具体物要求 —— **不含近期对话、不含自身上一句** | **提示词里没有任何"刚才说过什么"** |
| 线程 id | 每轮新开（`…-24` → `…-25`） | 不是同一段对话的延续，是"新开线程再问一遍" |

⇒ **定性：这是"上下文（prompt 可见部分）确实没变的重复发言"，不是 hash 撞车。** 触发条件不是"没有事件"（事件很多），而是：
1. **prompt 模板不带近期对话**（同 persona/场景/对象/情绪/最紧需求 ⇒ 逐字节相同），
2. 居民在无新对话输入时仍被要求开口，于是同一状态每隔若干轮重复触发一次（r24/25、r36/37 各出现一批）。

**这条不进 M0 判定，只作"下一轮生活气息维度"的候选**：若要让"像活人在过日子"，可考虑把「本线程最近 1–2 轮对话」或「自身上一句」渲染进 prompt，或改为"无新输入则不强制发言"。**本轮不改代码**（跑批期间禁改），仅登记。

## D. 复算命令

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
RUN=.worktrees/d12f-diverse/v2/evidence/run_d12f_diverse_n16r60_seed42/run.jsonl
python3 v2/evidence/d12f_m0_curve.py --run-jsonl $RUN --out-json /tmp/m0_curve.json --partial
# importance 的 key 复用率 / 相邻轮同输入
python3 - <<'PY'
import json
from collections import Counter, defaultdict
p='.worktrees/d12f-diverse/v2/evidence/run_d12f_diverse_n16r60_seed42/run.jsonl'
tot=defaultdict(lambda:[0,0]); keys=defaultdict(set)
for line in open(p,encoding='utf-8'):
    try: e=json.loads(line)
    except: continue
    if e.get('type')!='LLM_CALL': continue
    pl=e.get('payload') or {}; pu=pl.get('purpose')
    tot[pu][0]+=1; tot[pu][1]+= 1 if pl.get('cached') else 0
    keys[pu].add(pl.get('cache_key'))
for pu,(c,ca) in sorted(tot.items()):
    print(pu, 'calls',c,'cached',ca,'distinct_keys',len(keys[pu]))
PY
```
