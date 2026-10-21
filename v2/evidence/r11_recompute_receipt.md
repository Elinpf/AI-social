# R11 · ON 臂收口 复算回执（零跑批）

> 作者：experiment-analyst ｜ 生成时刻：2026-10-21 16:12:25 ｜ 仓库 HEAD：`895b9a381cd5a1838c23bd3b38e139f7edade3b8` ｜ 分支：`feat/life-memory-f6-on`
> 对应报告：`reports/R11-f6-memory-into-dialogue.md`（v2，两臂填实）
> 本回执的规矩：**每条数值都给出「命令 → 输入路径 → 输出」**；输出为实跑捕获，未人工改写。

## 0. 纪律声明

```text
$ pgrep -af "[o]rchestration run" ; echo rc=$?
rc=1
$ pgrep -af "[r]un_batch.sh" ; echo rc=$?
rc=1
```

> 说明：`pgrep` 模式用 `[o]rchestration`/`[r]un_batch` 的字符类写法，**避免匹配到执行本命令的 shell 自身**；两条都返回 `rc=1`（无命中）⇒ 复算期间**没有任何跑批在跑**，也没被我启动。

- **零跑批**：本轮回执只做只读复算（读 `run.jsonl`、跑本地指标脚本、`obs llm-cost` 读日志），**未启动任何跑批**，未 `setsid` 任何进程。
- **未改运行期代码**：`code/{life,orchestration,config,engine}` 无改动，证据见 §8。
- **作废批排除**：`run_f6_off_n16r84_seed42_VOID/` 的任何读数**未在本回执与报告中出现**；两臂只用 `*_n16r60_seed42`。

## 1. 批身份（两臂）

```text
$ sha256sum v2/evidence/run_f6_off_n16r60_seed42/run.jsonl v2/evidence/run_f6_on_n16r60_seed42/run.jsonl v2/evidence/run_f6_off_n16r60_seed42/meta.json v2/evidence/run_f6_on_n16r60_seed42/meta.json v2/evidence/run_f6_off_n16r60_seed42/host.log v2/evidence/run_f6_on_n16r60_seed42/host.log; wc -l v2/evidence/run_f6_off_n16r60_seed42/run.jsonl v2/evidence/run_f6_on_n16r60_seed42/run.jsonl; stat -c "%s %n" v2/evidence/run_f6_off_n16r60_seed42/run.jsonl v2/evidence/run_f6_on_n16r60_seed42/run.jsonl
c73bead61a440db789f6d6ba1de555fe326a203ee27d1219690174e3d9483642  v2/evidence/run_f6_off_n16r60_seed42/run.jsonl
7de6a7be5adff276f1e42c065a708c271f870f2bf8daa930cf0cdfc983f7434d  v2/evidence/run_f6_on_n16r60_seed42/run.jsonl
5d0634b6f43b0129496f329c071ad55bb876ca499d322933a3896c5012930500  v2/evidence/run_f6_off_n16r60_seed42/meta.json
8c7215a25b0e4f36d0084c4321f8c902b7b5144c5f819b451b763bfdfca44eb5  v2/evidence/run_f6_on_n16r60_seed42/meta.json
fee17565629e55a5aa287236fc47f152ad15c6b5d71324fce7fdc9dc666bc654  v2/evidence/run_f6_off_n16r60_seed42/host.log
5ba74fb6324020ad310768229307aeda77bb824a3248caa25cb95c8510ec2535  v2/evidence/run_f6_on_n16r60_seed42/host.log
   116294 v2/evidence/run_f6_off_n16r60_seed42/run.jsonl
   116261 v2/evidence/run_f6_on_n16r60_seed42/run.jsonl
   232555 total
55213213 v2/evidence/run_f6_off_n16r60_seed42/run.jsonl
55235141 v2/evidence/run_f6_on_n16r60_seed42/run.jsonl
```

```text
$ python3 -c "
import json
for a in ('off','on'):
    d=json.load(open(f'v2/evidence/run_f6_{a}_n16r60_seed42/meta.json'))
    print(a, {k:d.get(k) for k in ('n','rounds','seed','events','wc_l','duration_sec','started_at','finished_at','code_sha','code_sha_end','llm_calls','llm_cached','llm_cached_ratio','provider','model','fallback_detected','msg_counts')})
"
off {'n': 16, 'rounds': 60, 'seed': 42, 'events': 116294, 'wc_l': 116294, 'duration_sec': 5201, 'started_at': '2026-10-21T12:35:19+08:00', 'finished_at': '2026-10-21T14:02:00+08:00', 'code_sha': '895b9a381cd5a1838c23bd3b38e139f7edade3b8', 'code_sha_end': '895b9a381cd5a1838c23bd3b38e139f7edade3b8', 'llm_calls': 2878, 'llm_cached': 1472, 'llm_cached_ratio': 0.5115, 'provider': 'openai_compat', 'model': 'DeepSeek-Flash', 'fallback_detected': False, 'msg_counts': {'MSG_DM': 455, 'MSG_PUBLIC': 55}}
on {'n': 16, 'rounds': 60, 'seed': 42, 'events': 116261, 'wc_l': 116261, 'duration_sec': 6436, 'started_at': '2026-10-21T14:05:57+08:00', 'finished_at': '2026-10-21T15:53:13+08:00', 'code_sha': '895b9a381cd5a1838c23bd3b38e139f7edade3b8', 'code_sha_end': '895b9a381cd5a1838c23bd3b38e139f7edade3b8', 'llm_calls': 2878, 'llm_cached': 1477, 'llm_cached_ratio': 0.5132, 'provider': 'openai_compat', 'model': 'DeepSeek-Flash', 'fallback_detected': False, 'msg_counts': {'MSG_DM': 455, 'MSG_PUBLIC': 55}}
```

⇒ 两臂 `code_sha = code_sha_end = 895b9a381cd5a1838c23bd3b38e139f7edade3b8`（与 HEAD 一致）；ON 臂 `events=116261`、`duration_sec=6436`（14:05:57→15:53:13）、`llm_calls=2878`、`fallback_detected=false`。`meta.events` 与 `wc -l` 一致（116294 / 116261）。

## 2. F-6 与守卫项：官方指标复算（唯一来源 `tools/d5/dialogue_metrics.py`）

```text
$ python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_f6_on_n16r60_seed42/run.jsonl --meta v2/evidence/run_f6_on_n16r60_seed42/meta.json --out-json v2/evidence/r1_f6_on_metrics.json --out-md v2/evidence/r1_f6_on_metrics.md
# 实跑耗时 1.47s（本地词表统计，零 LLM 调用）
$ python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_f6_off_n16r60_seed42/run.jsonl --meta v2/evidence/run_f6_off_n16r60_seed42/meta.json --out-json /tmp/recheck_off_metrics.json --out-md /tmp/recheck_off_metrics.md
# 实跑耗时 1.47s
```

**关键读数（两臂并列，den 均 510）**：

| 指标 | OFF | ON | Δ(pp) | 备注 |
|---|---|---|---|---|
| **F-6 `timeref_rate`** | **0.037255（19/510）** | **0.111765（57/510）** | **+7.45** | 分母 510 ≥ 68，可报比率 |
| L-6 `dup_exact_rate` | 0.101961（52/510） | 0.127451（65/510） | +2.55 | 无 CI |
| L-7 `dup_ngram8_rate` | 0.354902（181/510） | **0.65098（332/510）** | **+29.61** | **越过预注册 +5pp 闸门 ⇒ 恶化** |
| L-8 `agent_id_leak_rate` | 0.0 | 0.0 | 0.00 | 应保持 0 |
| L-5 `template_hit_rate` | 0.011765（6/510） | 0.015686（8/510） | +0.39 | 无 CI |
| L-13 token 泄漏 `n`（den 510） | 2（0.003922） | **14（0.027451）** | +2.35 | 补记项，成因未查 |
| F-7a 越界提及（den 510） | 0.145098 | 0.22549 | +8.04 | 补记项，成因未查 |
| `admission` | ADMITTED（20 项 check 全 pass） | ADMITTED | — | 见 `r1_f6_{off,on}_metrics.json` |

**F-6 分子/分母的独立交叉校验**（不依赖官方脚本，直接用 11 词表数正文）：

```text
$ python3 - <<'PY'
import json
LEX=[l.strip() for l in open('tools/d5/timeref_lexicon.txt',encoding='utf-8') if l.strip() and not l.startswith('#')]
print('词表(',len(LEX),'):',LEX)
for arm in ('off','on'):
    tot=hit=0
    for line in open(f'v2/evidence/run_f6_{arm}_n16r60_seed42/run.jsonl'):
        if not line.strip(): continue
        d=json.loads(line)
        if d.get('type') in ('MSG_DM','MSG_GROUP','MSG_PUBLIC'):
            tot+=1
            if any(w in ((d.get('payload') or {}).get('body') or '') for w in LEX): hit+=1
    print(arm,'msgs',tot,'F6 hits',hit,'rate',round(hit/tot,6))
PY
词表( 11 ): ['昨天', '前天', '上次', '上回', '那天', '前几天', '昨儿', '昨晚上', '以前', '早就', '那次']
off msgs 510 F6 hits 19 rate 0.037255
on msgs 510 F6 hits 57 rate 0.111765
```

⇒ 独立复算 `off 19/510 = 0.037255`、`on 57/510 = 0.111765`，与官方脚本输出**逐位一致**（两条路径：`dialogue_metrics.py` 与 11 词直数正文）。**分母 510、分子 19/57，均为可引用读数。**

## 3. M-1 家族复算（probe 级，den 33）

```text
$ python3 tools/f6/f6_metrics.py --run OFF=v2/evidence/run_f6_off_n16r60_seed42/run.jsonl --run ON=v2/evidence/run_f6_on_n16r60_seed42/run.jsonl --official OFF=v2/evidence/r1_f6_off_metrics.json --official ON=v2/evidence/r1_f6_on_metrics.json --cost OFF=v2/evidence/f6_cost_off.json --cost ON=v2/evidence/f6_cost_on.json --out v2/evidence/f6_metrics_two_arms.json --markdown v2/evidence/f6_metrics_two_arms.md
| 指标 | OFF | ON |
|---|---|---|
| 消息数 | 510 | 510 |
| 天数 | 5（0–4） | 5（0–4） |
| 线程数 | 169 | 169 |
| 正文长度 p50/max | 29/95 | 40/128 |
| **F-6 跨天记忆引用率（官方）** | 0.037255 | 0.111765 |
| （交叉核对）时间回指率·本地 | 0.0373 (19/510) CI[0.024,0.0575] | 0.1118 (57/510) CI[0.0873,0.1421] |
| **M-1 记忆引用率（主口径·机会分母）** | 0.0909 (3/33) CI[0.0314,0.2357] | 0.1818 (6/33) CI[0.0861,0.3439] |
| M-1b（副列·全部 day≥1 分母） | 0.0073 (3/412) CI[0.0025,0.0212] | 0.0146 (6/412) CI[0.0067,0.0314] |
| M-0 同日对照（期望≈0） | 0.0192 (5/260) CI[0.0082,0.0442] | 0.2962 (77/260) CI[0.244,0.3543] |
| L-5 模板套话率（官方） | 0.011765 | 0.015686 |
| L-6 精确重复率（官方） | 0.101961 | 0.127451 |
| L-7 8-gram 重复率（官方） | 0.354902 | 0.65098 |
| L-8 裸 ID 泄漏率（官方） | 0.0 | 0.0 |
| 带 memory_refs 的消息 | 0 (0.0) | 412 (0.8078) |
| tokens_in / calls | 228749 / 2878 | 271717 / 2878 |

### 两臂差值（Δ = ON − OFF；率类单位 pp，token 为计数）

| 指标 | Δ | CI 重叠 | 判定 |
|---|---|---|---|
| M-1_opportunity | 9.09 | True | False |
| M-1b_allday | 0.73 | True | False |
| M-0_sameday_control | 27.7 | False | True |
| crosscheck_timeref | 7.45 | False | True |
| F-6_rate | 7.45 | None | - |
| L-6 | 2.55 | None | - |
| L-7 | 29.61 | None | - |
| L-8 | 0.0 | None | - |
| L-5 | 0.39 | None | - |
| tokens_in | 42968 | None | - |
```

> 上面代码块里的两张表就是 `f6_metrics.py` 写出的 `f6_metrics_two_arms.md` 原文（不再重复一份）。
> ⚠️ **口径提醒**：`f6_metrics.py` 的表头把 `M-1` 标成「记忆引用率（主口径）」，那是**脚本自身的叫法**；按 R11 §3.6，`M-1` 是**未去重上界**，本轮主口径是下面去重后的 `M-1′`。引用时不得把 `6/33` 称作"主口径读数"。

**去自我复读三档（`tools/f6/f6_m1_dedup.py`，判据=R11 §3.6，阈值写死在脚本常量里）**：

```text
$ python3 tools/f6/f6_m1_dedup.py --run v2/evidence/run_f6_off_n16r60_seed42/run.jsonl --json v2/evidence/f6_m1_dedup_off.json --quiet; python3 tools/f6/f6_m1_dedup.py --run v2/evidence/run_f6_on_n16r60_seed42/run.jsonl --json v2/evidence/f6_m1_dedup_on.json --quiet
M-1  = 3/33
M-1' (main, same_speaker & shared6>=3)   = 1/33
M-1'_strict (same_speaker & covA>=0.5)   = 2/33
written: v2/evidence/f6_m1_dedup_off.json
M-1  = 6/33
M-1' (main, same_speaker & shared6>=3)   = 2/33
M-1'_strict (same_speaker & covA>=0.5)   = 6/33
written: v2/evidence/f6_m1_dedup_on.json
```

| 档位 | OFF | ON | 用途 |
|---|---|---|---|
| `M-1`（未去重） | 3/33 | 6/33 | **上界 / 被污染读数**，不作结论 |
| **`M-1′`（主口径）** | **1/33** | **2/33** | 同一说话人 + 共享 6-gram ≥ 3 ⇒ 剔除 |
| `M-1′_strict` | 2/33 | 6/33 | 去重下界（`covA ≥ 0.5`），敏感性分析 |

## 4. 统计与判定（Wilson95 / Δ / MDE）

```text
$ python3 -c "
import math
z=1.959963984540054; zb=0.8416212335729143
def wil(k,n):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return (c-h)*100,(c+h)*100
for k,n,name in [(19,510,'F-6 OFF'),(57,510,'F-6 ON'),(1,33,'M-1p OFF'),(2,33,'M-1p ON'),(3,33,'M-1 OFF'),(6,33,'M-1 ON'),(5,260,'M-0 OFF'),(77,260,'M-0 ON'),(3,412,'M-1b OFF'),(6,412,'M-1b ON')]:
    lo,hi=wil(k,n); print('%-10s %3d/%-3d = %.6f  Wilson95=[%.2f%%, %.2f%%]'%(name,k,n,k/n,lo,hi))
se=lambda p,n: math.sqrt(p*(1-p)/n)
po,pn,n=3/33,6/33,33
print('MDE(overlap) = %.2fpp'%(100*z*(se(po,n)+se(pn,n))))
pbar=(po+pn)/2
print('MDE(power)   = %.2fpp'%(100*(z+zb)*math.sqrt(2*pbar*(1-pbar)/n)))
print('F-6 delta = %.2fpp'%(100*(57/510-19/510)))
"
F-6 OFF     19/510 = 0.037255  Wilson95=[2.40%, 5.75%]
F-6 ON      57/510 = 0.111765  Wilson95=[8.73%, 14.21%]
M-1p OFF     1/33  = 0.030303  Wilson95=[0.54%, 15.32%]
M-1p ON      2/33  = 0.060606  Wilson95=[1.68%, 19.61%]
M-1 OFF      3/33  = 0.090909  Wilson95=[3.14%, 23.57%]
M-1 ON       6/33  = 0.181818  Wilson95=[8.61%, 34.39%]
M-0 OFF      5/260 = 0.019231  Wilson95=[0.82%, 4.42%]
M-0 ON      77/260 = 0.296154  Wilson95=[24.40%, 35.43%]
M-1b OFF     3/412 = 0.007282  Wilson95=[0.25%, 2.12%]
M-1b ON      6/412 = 0.014563  Wilson95=[0.67%, 3.14%]
MDE(overlap) = 22.97pp
MDE(power)   = 23.67pp
F-6 delta = 7.45pp
```

- **F-6 判定**：Δ=+7.45pp，两臂 Wilson95 `[2.40%,5.75%]` vs `[8.73%,14.21%]` **不重叠** ⇒ 按 §3.3 判「显著」（单 seed 单批，不做跨 seed 方差）。
- **M-1 家族判定**：`M-1′` 2/33 vs 1/33，Wilson95 `[0.54%,15.32%]` vs `[1.68%,19.61%]` **重叠** ⇒ 不显著；且 MDE **22.97pp / 23.67pp ≫ 10pp 闸门** ⇒ 锁定为「在本样本量下无法在噪声之上判定差异」。
- **L-7 判定**：官方脚本只出标量（无 CI）⇒ 不作显著性判定，但按**预注册闸门**「≤ 基线+5pp 视为未恶化」，+29.61pp ⇒ **判为恶化**。

## 5. 真实 LLM 验真（`obs llm-cost`，不传 `--cache-dir`）

```text
$ (cd code) python3 -m obs llm-cost --log ../v2/evidence/run_f6_on_n16r60_seed42/run.jsonl --require-provider openai_compat --out ../v2/evidence/f6_cost_on.json; echo rc=$?
written: ../v2/evidence/f6_cost_on.json
rc=0
```

```text
$ python3 -c "import json;d=json.load(open('v2/evidence/f6_cost_on.json'));print(json.dumps({'provider_guard':d['provider_guard'],'total':d['engine_log']['total'],'by_purpose_dialogue':d['engine_log']['by_purpose']['dialogue'],'by_provider':d['engine_log']['by_provider']},ensure_ascii=False,indent=1))"
{
 "provider_guard": {
  "by_provider": {
   "openai_compat": 2878
  },
  "expected": "openai_compat",
  "ok": true,
  "policy": "计划用真 LLM 时必须显式校验 provider 计数 > 0 且无 mock 混入。",
  "problems": []
 },
 "total": {
  "cached": 1477,
  "calls": 2878,
  "degraded": 0,
  "thinking": 668,
  "tokens_in": 271717,
  "tokens_out": 269123,
  "tokens_total": 540840
 },
 "by_purpose_dialogue": {
  "cached": 52,
  "calls": 510,
  "degraded": 0,
  "thinking": 0,
  "tokens_in": 130924,
  "tokens_out": 16057
 },
 "by_provider": {
  "openai_compat": 2878
 }
}
```

**判据四项（全部成立）**：`rc=0`；`provider_guard.ok=true` 且 `problems=[]`；`by_provider` 只含 `openai_compat: 2878`（无 mock 混入）；`calls=2878 > 0` 且 `degraded=0`。
另：`tokens_in 271717 = 130924+2312+88382+1787+1447+46865`（按 purpose 分项可加总）⇒ 数值非编造。`meta.llm_provider_in_events={openai_compat:2878}`、`meta.llm_model_in_events={DeepSeek-Flash:2878}`、`fallback_detected=false` 与之一致。

## 6. 注入面（`ctx.memory_refs`，只证注入、不证用上）

```text
$ python3 - <<'PY'
import json
from collections import Counter
for arm in ('off','on'):
    tot=n=ids=0; c=Counter()
    for line in open(f'v2/evidence/run_f6_{arm}_n16r60_seed42/run.jsonl'):
        d=json.loads(line)
        if d.get('type') in ('MSG_DM','MSG_GROUP','MSG_PUBLIC'):
            tot+=1
            mr=((d.get('payload') or {}).get('ctx') or {}).get('memory_refs')
            if mr: n+=1; ids+=len(mr); c.update(mr)
    print(arm,'msgs',tot,'with_memory_refs',n,'total_refs',ids,'distinct_mem_ids',len(c),'top3',c.most_common(3))
PY
off msgs 510 with_memory_refs 0 total_refs 0 distinct_mem_ids 0 top3 []
on msgs 510 with_memory_refs 412 total_refs 824 distinct_mem_ids 128 top3 [('M-P001-000007', 8), ('M-P001-000024', 8), ('M-P004-000009', 8)]
```

⇒ ON 臂 412/510 条 MSG 带注入（824 次引用、128 个不同记忆）；OFF 臂 0/510 ⇒ **单变量注入确实发生**。

## 7. ON 四视图：sha256 与非退化统计（本回执独立复算，未采信他人口述）

```text
$ sha256sum v2/evidence/f6_shots/run_f6_on_n16r60_seed42-*.png
54e36930ad154258bd1efbacc8e01b33833c42a6f3f04d1b6c35764b90b76f88  v2/evidence/f6_shots/run_f6_on_n16r60_seed42-600-7de6a7be.png
2cf622ebfd025f7182c98afe7dd7a5c345b5f31d4e7bb6617119f9462b5babfd  v2/evidence/f6_shots/run_f6_on_n16r60_seed42-chat-7de6a7be.png
fc11501c1a421d8fe8d97e8a4cc3c1b41bf5f851451f385fa07003483a071c32  v2/evidence/f6_shots/run_f6_on_n16r60_seed42-rhythm-7de6a7be.png
308844ded88073fd8c0508abaea9467030ef6c0ef7724f3486c1ebbb0ea79f7e  v2/evidence/f6_shots/run_f6_on_n16r60_seed42-spread-7de6a7be.png
```

```text
$ python3 - <<'PY'
from PIL import Image
from collections import Counter
import glob
for f in sorted(glob.glob('v2/evidence/f6_shots/run_f6_on_n16r60_seed42-*.png')):
    im=Image.open(f); im.load(); rgb=im.convert('RGB'); w,h=rgb.size
    sm=rgb.resize((max(1,w//4),max(1,h//4))); px=list(sm.getdata()); n=len(px)
    b=sum((0.299*r+0.587*g+0.114*bb) for r,g,bb in px)/n
    dark=sum(1 for r,g,bb in px if (0.299*r+0.587*g+0.114*bb)<8)/n*100
    mc=Counter(px).most_common(1)[0][1]/n*100
    print(f.split('/')[-1], f'{w}x{h}', im.mode, 'mean_brightness=%.1f'%b, 'dark_frac=%.2f%%'%dark, 'max_color_frac=%.2f%%'%mc)
PY
run_f6_on_n16r60_seed42-600-7de6a7be.png 600x900 RGB mean_brightness=38.4 dark_frac=0.02% max_color_frac=10.12%
run_f6_on_n16r60_seed42-chat-7de6a7be.png 1400x900 RGB mean_brightness=33.7 dark_frac=0.01% max_color_frac=10.70%
run_f6_on_n16r60_seed42-rhythm-7de6a7be.png 1300x1050 RGB mean_brightness=32.6 dark_frac=0.01% max_color_frac=17.48%
run_f6_on_n16r60_seed42-spread-7de6a7be.png 1300x900 RGB mean_brightness=24.1 dark_frac=0.01% max_color_frac=46.62%
<stdin>:6: DeprecationWarning: Image.Image.getdata is deprecated and will be removed in Pillow 14 (2027-10-15). Use get_flattened_data instead.
```

⇒ 亮度 24.1–38.4、`dark_frac ≤ 0.02%` ⇒ **非黑非白，非退化**（与 OFF 臂同量级）。

## 8. 单变量三查与代码纯洁性

完整原文入库：`v2/evidence/f6_single_variable_checks.txt`（sha256 `aa9f9f7e2761951aed784d05151d19e3aca831debc1acb4332a3812374fbfc5a`）。摘录：

```text
$ git diff 895b9a3 -- code/life code/orchestration code/config; echo "rc=$?"; git status --porcelain | grep -E "^.. code/(life|orchestration|config|engine)" || echo "运行期目录无未提交项"
rc=0
运行期目录无未提交项
```

- (a) 两臂 `code_sha/​code_sha_end` 均 `895b9a3…`，与 `git rev-parse HEAD` 一致 ⇒ 同树、无事后回填。
- (b) 代码级复核：`_memory_line()` 在 `if not memory_f6_enabled(): return ""` 早退（`code/life/agent.py:1114-1117`）；两个提示词插入点 `agent.py:1211/1216`、`:1225/1231` 均为 `+ mem_line` ⇒ OFF 时为空串，提示词逐字节不变。
- (c) `git diff 895b9a3 -- code/{life,orchestration,config}` 空输出、rc=0；`git status` 无运行期目录改动。

## 9. 本次新增/改动的产物清单（含 sha256）

```text
$ sha256sum v2/evidence/r1_f6_on_metrics.json v2/evidence/r1_f6_on_metrics.md v2/evidence/f6_cost_on.json v2/evidence/r1_f6_on_f6metrics.json v2/evidence/r1_f6_on_f6metrics.md v2/evidence/f6_m1_dedup_off.json v2/evidence/f6_m1_dedup_on.json v2/evidence/f6_metrics_two_arms.json v2/evidence/f6_metrics_two_arms.md v2/evidence/f6_single_variable_checks.txt tools/f6/f6_m1_dedup.py reports/R11-f6-memory-into-dialogue.md
abe4977d8ecb6dc40ab7883ea7f3a614f5f6dc1d7db66e8680b74477c1ded410  v2/evidence/r1_f6_on_metrics.json
56f025bf280fba568614be3ad9cb243679b13ec60d2084a70fcace1603fcd8c2  v2/evidence/r1_f6_on_metrics.md
db92fee77701c509ffd61ac5fc3f354c50562b1efeab8cc0f8e2d909ad4594d8  v2/evidence/f6_cost_on.json
519689d7f77ec8ff6359d0453081a218039bfc3c6d5fe152c0de2793d4fc035d  v2/evidence/r1_f6_on_f6metrics.json
8f92cf25faf6321792e1fb4405a9a470c4824df9172d0f1aa668d6dc78d806d7  v2/evidence/r1_f6_on_f6metrics.md
1c9a9678495c5f48e11a2c4bad36f3da1479b6f931d97c080bb1ea2a54403527  v2/evidence/f6_m1_dedup_off.json
041a3ecabac57d4094fb686ec140318b09148b7d56e3364ab34d24ed28adcd1d  v2/evidence/f6_m1_dedup_on.json
de982c02029ce51c0166953c87dcc87c701876388341e99b21974083290853fe  v2/evidence/f6_metrics_two_arms.json
3b23fd0263b6156d2d79fb08f11ac84bb424f2e0cc93d0b72c9f5ff6e2be82b3  v2/evidence/f6_metrics_two_arms.md
aa9f9f7e2761951aed784d05151d19e3aca831debc1acb4332a3812374fbfc5a  v2/evidence/f6_single_variable_checks.txt
b9faa7de1e8dabcc15a40954ced6196748f336d1fddc964e40dc97bc99caaa6c  tools/f6/f6_m1_dedup.py
a5d09e4d299f7ac58ef09b6939a3533b5acd1395ba9bd26fbe920c63b623605d  reports/R11-f6-memory-into-dialogue.md
```

> 说明：`reports/R11-…md` 的 sha256 是**本回执最后更新时刻**的值（a5d09e4d299f7ac58ef09b6939a3533b5acd1395ba9bd26fbe920c63b623605d）；报告在提交前若再改（如回填 commit sha），以 `git show <sha>:reports/R11-f6-memory-into-dialogue.md | sha256sum` 为准。


## 10. 一句话结论（供引用，全部可在上文复算）

- **F-6**：`19/510 = 0.037255` → **`57/510 = 0.111765`**（**+7.45pp**，两臂 Wilson95 不重叠 ⇒ 显著）。
- **代价**：`L-7 0.354902 → 0.65098`（**+29.61pp**，越过预注册 +5pp 闸门 ⇒ 判恶化）；`L-6 +2.55pp`；`tokens_in +18.78%`（对话单路 **+47.31%**，≈82 token/条）；墙钟 `5201s → 6436s`（**+23.75%**）。
- **不可判定**：M-1 家族（`M-1′` 2/33 vs 1/33，区间重叠；MDE 22.97pp ≫ 10pp 闸门），且 ON 侧 `M-0`（29.62%）与 `M-1`（18.18%）同量级 ⇒ 按预注册 M-1 降级为「模板重叠」。
- **价值定位**：F-6 升是真的，代价也是真的 ⇒ **不构成生活气息的净改善**；本轮主价值 = 装配链路打通 + 单变量可自证 + 真跑可复算 + 两臂四视图非退化。
- **未完成项**：报告 commit sha（待 `delivery-gatekeeper` 提交后回填）；本轮**未起跑任何新批次**。
