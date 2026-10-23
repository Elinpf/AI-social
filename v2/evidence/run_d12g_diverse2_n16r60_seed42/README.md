# D12-G（T5）终态证据 · 主树可复算入口

> 本目录是 **D12-G 臂**（`LIFE_PROMPT_D12G_DIVERSE=3` + `LIFE_PROMPT_D12E_BESTOF=3`）的终态证据。
> 特征代码**不在 master**：它属分支 `feat/d12g-diverse2`（tip `344d3da`，收批提交 `ad362b3`）。
> master 只收**证据**，不收该臂的 `code/` 差异（本目录任何文件都不依赖 master 的代码版本即可复算，因为复算脚本都是 master 上已有的、且口径冻结的读数器）。

## 1. `run.jsonl` 为什么不在库里

- 体积 **56 MB**（`run_bytes=56,333,745`），按仓内既有策略 `**/*.jsonl` 不入库；
- **sha256 = `dd4ad73d5a21c7485c2afbfc9701e267c25da3150b10adade3b3819a3996ff36`**
- **行数 = 117,393**（= `meta.json.events` = `wc_l`）
- 与 `meta.json` 对得上：`derived_from_log_sha256` = `dd4ad73d…f36`、`run_sha256` = `dd4ad73d…f36` ⇒ **同一份日志**，可直接用 meta 里的 sha 校验你手上的 jsonl，不必信本 README。
- 原始位置（worktree，非 master）：`.worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42/run.jsonl`

```bash
# 校验你手上的日志就是本报告读的那一份
sha256sum <path>/run.jsonl     # 期望 dd4ad73d5a21c7485c2afbfc9701e267c25da3150b10adade3b3819a3996ff36
wc -l <path>/run.jsonl         # 期望 117393
```

## 2. 本目录文件＝什么

| 文件 | 性质 | 关键读数 |
|---|---|---|
| `meta.json` | 批次元数据（引擎自写） | `code_sha=344d3da4…`、`rc` 走 `run_batch.rc`、`events=117393`、`rounds_seen_max=59`、`llm_calls=3898`、`llm_provider_in_events={openai_compat:3898}`、`degraded_calls=0`、`git_dirty_code_files=[]`、`run_sha256=dd4ad73d…f36` |
| `run_batch.rc` | 进程退出码硬证据 | **`0`** |
| `run_batch.end` | EXIT trap 收尾 | `finished_at=2026-10-23T20:16:27+08:00 / rc=0` |
| `llm_cost.txt` | `obs llm-cost` 验真输出 | rc=0、`provider_guard.ok=true`、`problems=[]`、`tokens_total=831,809` |
| `switch_proof.md` | 开关 + 运行期不可替换证据 | env 三条齐；`code/life/agent.py` 跑前=跑后=`dc2a8012420bc342…fafdf7` |
| `d12g_verdict.md` / `.json` | 逐项判据实测表（人读 / 机读） | 机制闸 M1/M3/M5 全过；效果 4/6（L-7 双口径未达） |

## 3. 复算命令（六条；与 `d12g_verdict.md` §4 逐字一致）

```bash
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
T4=$REPO/.worktrees/d12f-diverse/v2/evidence/run_d12f_diverse_n16r60_seed42   # 基线 T4
WT=$REPO/.worktrees/d12g-diverse2
T5=$WT/v2/evidence/run_d12g_diverse2_n16r60_seed42                            # 本臂日志（不在 master）
cd $REPO

# (a) L-3 / L-6 / F-2' / len_p50（d5 冻结口径；用 T4 复算可校验得 60.59%/0.78%/71.26%/54，与 T4 报告逐字一致）
python3 tools/d5/dialogue_metrics.py --log $T4/run.jsonl --out-json /tmp/t4_d5.json
python3 tools/d5/dialogue_metrics.py --log $T5/run.jsonl --out-json /tmp/t5_d5.json

# (b) P1 / 结构三项 / len_p50（`v2/evidence/d12c_metrics.py`，sha256=c41cb5aca03c9499fc47047d5acaeba8f4b33bef5298b69556b15d3da290ab58）
python3 v2/evidence/d12c_metrics.py --run T4=$T4/run.jsonl --run T5=$T5/run.jsonl --out-json /tmp/d12g_d12c.json

# (c) L-7 双口径（raw8 = re.sub(r"\s+","",body) 后 8-window；norm8 = normalize_body 后同法；任一同批他人 shingle 重合即记 1）
python3 - "$T4/run.jsonl" "$T5/run.jsonl" <<'PY'
import json,re,sys
from collections import defaultdict
sys.path.insert(0,'.')
from tools.d5.dialogue_metrics import normalize_body
MSG=("MSG_DM","MSG_PUBLIC","MSG_GROUP")
def load(p):
    return [((json.loads(l).get('payload') or {}).get('body') or '') for l in open(p,encoding='utf-8') if json.loads(l).get('type') in MSG]
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
    b=load(p); print(tag,'raw8',rate(b,'raw8'),'| norm8',rate(b,'norm8'))
PY

# (d) L-15 restate（strong 口径）
python3 tools/d5/l15_restate_rate.py --run T4=$T4/run.jsonl --run T5=$T5/run.jsonl --out-json /tmp/l15.json

# (e) 机制闸 M1/M3/M5 + 候选 sha 重复（§3.105b）
python3 - "$T5/run.jsonl" <<'PY'
import json,sys
rows=[];dup=[];dlg=0
for line in open(sys.argv[1]):
    d=json.loads(line);pl=d.get('payload') or {}
    if d['type']=='LLM_CALL' and pl.get('purpose')=='dialogue': dlg+=1
    ctx=pl.get('ctx') if isinstance(pl,dict) else None
    if not (isinstance(ctx,dict) and 'd12g' in ctx): continue
    g=ctx['d12g'];rows.append(g);s=tuple(g['candidate_shas'])
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

**期望读数**（本目录 `d12g_verdict.{md,json}` 已写死，复算应逐字相符）：
M1 `510/510=100%`、M3 `510/510`、M5 mean `0.970929`（min `0.376344` = `seq=26894` **退化值**，非机制下限）；
L-7 norm8 `248/510 = 48.63%`、raw8 `309/510 = 60.59%`；P1 `99.22%`；F-2' `70.97%`；L-15 strong `2.35%`；L-3 `57.84%`；
结构 `510/169/2`；`len_p50`(excl) `53`；`L-6` `0.59%`。

## 4. 引用纪律（写报告时照抄）

- 写数一律 **`a/n = x%（Wilson CI）`**，不写裸百分比；`L-7` 必须带口径（`norm8` / `raw8`）。
- **`M5`（`cand_jaccard_dist_mean` 0.970929）与 D12-F 的 `M4`（21.57%）刻度不可比**，不得相减、不得比倍数（runbook §3.105）。
- 本臂 **1 条三采退化为两采**（`seq=26894`, round 20, P005）必须同屏写；`M5` 最小值 `0.376344` 标为**退化值**。
- 判词：Leader 裁定 = **「机制生效、效果未达标」**，落预登记「无效（效果不足）」档，并标注**档位外推**（预登记 §5 只写到「差 0–2pp」，本臂差 6.08/5.49pp）。
