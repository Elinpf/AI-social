# D12-G（T5）收批判据实测表 · 逐项对预登记

> 作者：batch-operator｜2026-10-23 20:1x (+08:00)｜批次：`feat/d12g-diverse2` @ `344d3da47f4217dd52b73749874d8660d0439939`
> 基线：T4（`run_d12f_diverse_n16r60_seed42`）｜预登记：`v2/refs/D12G-prereg.md`（sha256 `cd315e853303dfd1…9923e935`，未改）
> 机器可读版：本目录 `d12g_verdict.json`｜阈值一字未动，全部照预登记原值。

## 0. 终态件与真跑验真

| 项 | 值 |
|---|---|
| `run_batch.rc` | **`0`** |
| `run_batch.end` | `finished_at=2026-10-23T20:16:27+08:00 / rc=0 / out_dir=…/run_d12g_diverse2_n16r60_seed42` |
| `run.jsonl` | **117,393 行**，`sha256=dd4ad73d5a21c7485c2afbfc9701e267c25da3150b10adade3b3819a3996ff36`（= `meta.json.derived_from_log_sha256`） |
| 轮次 | `TURN_SEAL` 最大 round = **59**（`rounds=60`，`rounds_contiguous=true`）→ 无缺口 |
| `meta.json` | `code_sha=344d3da4…`、`git_dirty_code_files=[]`、`degraded_calls=0`、`fallback_detected=false`、`n_in_log=16`、`rounds_effective=60` |
| 墙钟 | 19:27:14 → 20:16:25 = **2,951s（49.2 min）**（预登记估 75–90 min；本臂缓存命中 38.3% 故更快） |
| `llm_cost.txt` | `v2/evidence/run_d12g_diverse2_n16r60_seed42/llm_cost.txt`，**rc=0**，`provider_guard.ok=true`、`problems=[]` |
| 调用 | `calls=3898 / cached=1494 / degraded=0`，`by_provider={"openai_compat":3898}`，`tokens_total=831,809` |

```
$ cd <wt>/code && python3 -m obs llm-cost --log <out>/run.jsonl --require-provider openai_compat > <out>/llm_cost.txt; echo rc=$?
rc=0
{"engine_log":{"by_provider":{"openai_compat":3898},"by_purpose":{"dialogue":{"cached":69,"calls":1530,…,"tokens_in":337445,"tokens_out":87006},
"importance":{…"cached":1387,…},"judge":{"cached":0,"calls":668,…},"negotiation":{"cached":34,"calls":49,…},"plan":{"cached":0,"calls":16,…},
"reflect":{"cached":4,"calls":112,…}},"source":"engine_log(LLM_CALL)","total":{"cached":1494,"calls":3898,"degraded":0,"thinking":668,
"tokens_in":481867,"tokens_out":349942,"tokens_total":831809}},
"provider_guard":{"by_provider":{"openai_compat":3898},"expected":"openai_compat","ok":true,"problems":[]}}
```

## 1. 机制闸（预登记 §3）

| 闸 | 阈值 | 实测 | 结果 |
|---|---|---|---|
| **M1** `ctx.d12g` 命中率 | =100% | **510/510 = 100%**（`dialogue` LLM_CALL **1,530 = 3×510**，每轮都挂 ctx） | **PASS** |
| **M3** 非全同分样本 `picked==argmin` | =100% | **510/510 = 100%**（零违例） | **PASS** |
| **M5** `cand_jaccard_dist_mean` | **≥0.05** | **mean = 0.970929**（max 1.0），≥0.05 占比 **100%** | **PASS** |
| `picked` 分布（只记录） | — | `{0:436, 1:63, 2:11}` ⇒ 换掉首条 **74/510 = 14.51%**；`scores` 三列均值 **2.463 / 0.357 / 0.286** | — |

**M5 两条必须同屏的记注**（Leader 裁决口径）：
1. **min = 0.376344 是「退化值」**，不是机制下限 —— 它来自 `seq=26894`（round 20，P005）候选 0 与候选 1 **同文**（sha 相同），也不是本臂机制的下界；
2. **本臂有 1 条三采退化为两采**（`seq=26894, round 20, P005`；`scores=[0,0,0]`、`picked=0`）⇒ 剔除该条后 M5 mean = **0.972097**，不影响 mean ≥0.05 的判定。

## 2. 效果判据（预登记 §4，六条同时满足才算「有效」）

| # | 指标 | 阈值 | **T5 实测** | Wilson 95% CI | T4 基线 | Δ | 结果 |
|---|---|---|---|---|---|---|---|
| 1 | **`L-7` norm8** | ≤ **42.55%** | **48.63%（248/510）** | [44.32, 52.96] | 52.55% | −3.92pp | ❌ **差 6.08pp** |
| 2 | **`L-7` raw8** | ≤ **55.10%** | **60.59%（309/510）** | [56.28, 64.74] | 65.10% | −4.51pp | ❌ **差 5.49pp** |
| 3 | **`P1`** | ≥ 94.61% | **99.22%** | — | 99.61% | −0.39pp | ✅ |
| 4 | **`F-2'`** | ≤ 76.26% | **70.97%** | — | 71.26% | −0.29pp | ✅ |
| 5 | **`L-15 strong`** | ≤ 3.73% | **2.35%** | — | 3.73% | −1.38pp | ✅ |
| 6 | **`L-3` 含括号块率（代价闸）** | **≥ 55%** | **57.84%** | — | 60.59% | −2.75pp | ✅（守住，但旁白又少了 2.75pp） |

次级（只记录）：`len_p50`(excl) **53**（T4 54，≤59.4 ✅）；结构 **510/169/2 全等**；`L-6` **0.59%**（T4 0.78%）；tokens **831,809**（T4 838,471，−0.8%，同量级）✅。

## 3. 判定（**按预登记该判什么 + 登记缺口**）

- **机制闸全过 ⇒ 按 §3 不是「机制未生效」**；
- 六条效果判据 **4 条达标（P1 / F-2' / L-15 / L-3）**，**`L-7` 双口径均未达**（差 6.08pp / 5.49pp）；
- ⚠ **登记缺口（不擅自补判词）**：预登记 §5 只写了「`L-7` **差 0–2pp** 未达 ⇒ 无效（效果不足）」，本臂差值（6.08 / 5.49pp）**超出该区间**，反事实表对「>2pp 未达」**没有写判词** ⇒ 判词由 Leader 裁定；本文件只报数，不改阈值、不补写判词。
- 同屏必写：`M5` min 0.376344 = 退化值；本臂 1 条三采退化为两采（`seq=26894`）；`M5` 与 `M4` **刻度不可比**，不得相减/比倍数（runbook §3.105）。

## 4. 复算命令（第三方照跑即可得同一组数）

```bash
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
T4=$REPO/.worktrees/d12f-diverse/v2/evidence/run_d12f_diverse_n16r60_seed42
WT=$REPO/.worktrees/d12g-diverse2
T5=$WT/v2/evidence/run_d12g_diverse2_n16r60_seed42
cd $REPO

# (a) L-3 / L-6 / F-2' / len_p50 —— 冻结读数器（d5 口径；本表已用 T4 复算校验，得 60.59% / 0.78% / 71.26% 与 T4 报告逐字一致）
python3 tools/d5/dialogue_metrics.py --log $T4/run.jsonl --out-json /tmp/t4_d5.json
python3 tools/d5/dialogue_metrics.py --log $T5/run.jsonl --out-json /tmp/t5_d5.json

# (b) P1 / 结构三项 / len_p50（d12c_metrics 冻结读数器 sha256=c41cb5aca03c9499…90ab58）
python3 v2/evidence/d12c_metrics.py --run T4=$T4/run.jsonl --run T5=$T5/run.jsonl --out-json /tmp/d12g_d12c.json

# (c) L-7 双口径（raw8 = re.sub(r"\s+","",body) 后 8-window，任一同批他人 shingle 重合即记 1；norm8 = normalize_body 后同法）
python3 - "$T4/run.jsonl" "$T5/run.jsonl" <<'PY'
import json,re,sys
from collections import defaultdict
sys.path.insert(0,'.')
from tools.d5.dialogue_metrics import normalize_body
MSG=("MSG_DM","MSG_PUBLIC","MSG_GROUP")
def load(p):
    out=[]
    for l in open(p,encoding='utf-8'):
        r=json.loads(l)
        if r.get('type') in MSG: out.append(((r.get('payload') or {}).get('body') or ''))
    return out
def rate(bodies,mode):
    norm=[re.sub(r"\s+","",b) for b in bodies] if mode=='raw8' else [normalize_body(b) for b in bodies]
    sh=[{t[i:i+8] for i in range(max(0,len(t)-7))} for t in norm]; idx=defaultdict(list)
    for i,s in enumerate(sh):
        for g in s: idx[g].append(i)
    dup=set()
    for g,ids in idx.items():
        if len(ids)>=2: dup.update(ids)
    return '%d/%d = %.2f%%'%(len(dup),len(bodies),100*len(dup)/len(bodies))
for tag,p in (('T4',sys.argv[1]),('T5',sys.argv[2])):
    b=load(p)
    print(tag,'raw8',rate(b,'raw8'),'| norm8',rate(b,'norm8'))
PY
# 实测输出：T4 raw8 332/510 = 65.10%、norm8 268/510 = 52.55%（与 T4 报告逐字相符 ⇒ 口径复算无误）；
#          T5 raw8 309/510 = 60.59%、norm8 248/510 = 48.63%。

# (d) L-15
python3 tools/d5/l15_restate_rate.py --run T4=$T4/run.jsonl --run T5=$T5/run.jsonl --out-json /tmp/l15.json

# (e) 机制闸 M1/M3/M5 + 候选 sha 重复
python3 - <<'PY' "$T5/run.jsonl"
import json,sys,collections
rows=[];dup=[];dlg=0
for line in open(sys.argv[1]):
    d=json.loads(line);pl=d.get('payload') or {}
    if d['type']=='LLM_CALL' and pl.get('purpose')=='dialogue': dlg+=1
    ctx=pl.get('ctx') if isinstance(pl,dict) else None
    if not (isinstance(ctx,dict) and 'd12g' in ctx): continue
    g=ctx['d12g'];s=tuple(g['candidate_shas'])
    rows.append(g)
    if len(set(s))<len(s): dup.append((d['seq'],s))
v=[g['cand_jaccard_dist_mean'] for g in rows]
print('turns=%d dialogue_calls=%d M1=%.2f%%'%(len(rows),dlg,100*len(rows)/(dlg/3)))
print('M3=%d/%d'%(sum(1 for g in rows if g['picked']==min(range(3),key=lambda i:g['scores'][i])),len(rows)))
print('M5 mean=%.6f min=%.6f dup_turns=%d'%(sum(v)/len(v),min(v),len(dup)))
for x in dup: print('  dup',x)
PY

# (f) 验真
cd $WT/code && python3 -m obs llm-cost --log "$T5/run.jsonl" --require-provider openai_compat; echo rc=$?
```
