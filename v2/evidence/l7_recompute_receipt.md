# R12 · DEQUP 臂复算回执（零跑批）

> 生成时刻：2026-10-21 20:09:28 +0800 ｜ 仓库 HEAD：263a4300692d2ef3136c8a50e9bade2f99608945 ｜ 分支：feat/life-l7-dedup-1021
> 对应报告：`reports/R12-l7-dequp.md`
> 本回执的规矩：每条数值都给「命令 → 输入路径 → 输出」；输出为实跑捕获，未人工改写。

## 0. 串行纪律

```text
$ pgrep -af "[o]rchestration run" ; echo rc=$?
rc=1
rc=0
```

```text
$ pgrep -af "[r]un_batch.sh" ; echo rc=$?
rc=1
rc=0
```

> `rc=1`（无命中）⇒ 本回执生成期间没有任何跑批在跑，也没被我启动（零跑批）。

## 1. 批身份（两臂）

```text
$ sha256sum v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl v2/evidence/run_f6_dequp_n16r60_seed42/meta.json v2/evidence/run_f6_dequp_n16r60_seed42/host.log v2/evidence/run_f6_on_n16r60_seed42/run.jsonl v2/evidence/run_f6_on_n16r60_seed42/meta.json
6bf3ec88700fa1a7451b18c63678d0904c69b9de39896739190e7e674db8fdbd  v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl
eaf32affa325810fb0d341442435f06010788cc08a8673a2d32655cdfb4ccc13  v2/evidence/run_f6_dequp_n16r60_seed42/meta.json
38840f481682d5d99d824b030ab11d1850334968a519bb96fbb599e15f7acc66  v2/evidence/run_f6_dequp_n16r60_seed42/host.log
7de6a7be5adff276f1e42c065a708c271f870f2bf8daa930cf0cdfc983f7434d  v2/evidence/run_f6_on_n16r60_seed42/run.jsonl
8c7215a25b0e4f36d0084c4321f8c902b7b5144c5f819b451b763bfdfca44eb5  v2/evidence/run_f6_on_n16r60_seed42/meta.json
rc=0
```

```text
$ wc -l v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl v2/evidence/run_f6_on_n16r60_seed42/run.jsonl
   116385 v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl
   116261 v2/evidence/run_f6_on_n16r60_seed42/run.jsonl
   232646 total
rc=0
```

```text
$ stat -c '%s %n' v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl v2/evidence/run_f6_on_n16r60_seed42/run.jsonl
55404972 v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl
55235141 v2/evidence/run_f6_on_n16r60_seed42/run.jsonl
rc=0
```

```text
$ python3 -c "
import json
for a in ('dequp','on'):
    d=json.load(open(f'v2/evidence/run_f6_{a}_n16r60_seed42/meta.json'))
    print(a, {k:d.get(k) for k in ('n','rounds','seed','events','wc_l','duration_sec','started_at','finished_at','code_sha','code_sha_end','llm_calls','llm_cached','llm_cached_ratio','provider','model','fallback_detected','msg_counts','degraded_calls','llm_purposes','side_root','endpoint_host')})
"
dequp {'n': 16, 'rounds': 60, 'seed': 42, 'events': 116385, 'wc_l': 116385, 'duration_sec': 5952, 'started_at': '2026-10-21T18:08:42+08:00', 'finished_at': '2026-10-21T19:47:54+08:00', 'code_sha': '263a4300692d2ef3136c8a50e9bade2f99608945', 'code_sha_end': '263a4300692d2ef3136c8a50e9bade2f99608945', 'llm_calls': 2966, 'llm_cached': 1425, 'llm_cached_ratio': 0.4804, 'provider': 'openai_compat', 'model': 'DeepSeek-Flash', 'fallback_detected': False, 'msg_counts': {'MSG_DM': 455, 'MSG_PUBLIC': 55}, 'degraded_calls': 0, 'llm_purposes': {'dialogue': 598, 'importance': 1523, 'judge': 668, 'negotiation': 49, 'plan': 16, 'reflect': 112}, 'side_root': None, 'endpoint_host': '172.16.3.41:31809'}
on {'n': 16, 'rounds': 60, 'seed': 42, 'events': 116261, 'wc_l': 116261, 'duration_sec': 6436, 'started_at': '2026-10-21T14:05:57+08:00', 'finished_at': '2026-10-21T15:53:13+08:00', 'code_sha': '895b9a381cd5a1838c23bd3b38e139f7edade3b8', 'code_sha_end': '895b9a381cd5a1838c23bd3b38e139f7edade3b8', 'llm_calls': 2878, 'llm_cached': 1477, 'llm_cached_ratio': 0.5132, 'provider': 'openai_compat', 'model': 'DeepSeek-Flash', 'fallback_detected': False, 'msg_counts': {'MSG_DM': 455, 'MSG_PUBLIC': 55}, 'degraded_calls': 0, 'llm_purposes': {'dialogue': 510, 'importance': 1523, 'judge': 668, 'negotiation': 49, 'plan': 16, 'reflect': 112}, 'side_root': None, 'endpoint_host': '172.16.3.41:31809'}
rc=0
```

```text
$ python3 -c "
import json
d=json.load(open('v2/evidence/run_f6_dequp_n16r60_seed42/meta.json'))
print('assertions:', json.dumps(d.get('assertions'), ensure_ascii=False))
print('git_dirty_code_files:', json.dumps(d.get('git_dirty_code_files'), ensure_ascii=False))
print('derived_from_log_sha256:', d.get('derived_from_log_sha256'))
print('run_sha256:', d.get('run_sha256'), 'run_bytes:', d.get('run_bytes'))
"
assertions: {"code_unchanged_during_run": null, "msg_uid_unique": true, "participants_consistent": true, "participants_violations": 0, "ptr_cross_thread": 0, "ptr_dangling": 0, "reply_to_same_thread": true, "turn_index_dense": true, "turn_index_gap_threads": 0}
git_dirty_code_files: ["?? code/frontend/sample/dialogue_run_g1_b0_n16r60_seed42/"]
derived_from_log_sha256: 6bf3ec88700fa1a7451b18c63678d0904c69b9de39896739190e7e674db8fdbd
run_sha256: 6bf3ec88700fa1a7451b18c63678d0904c69b9de39896739190e7e674db8fdbd run_bytes: 55404972
rc=0
```

## 2. 零跑批复算：arm 对比（tool: tools/l7/l7_arm_compare.py）

```text
$ python3 tools/l7/l7_arm_compare.py --dequp v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl --on v2/evidence/run_f6_on_n16r60_seed42/run.jsonl --out v2/evidence/l7_arm_compare.json > /tmp/l7_arm_compare.stdout 2>/tmp/l7_arm_compare.stderr ; echo "stdout_bytes=$(stat -c %s /tmp/l7_arm_compare.stdout) stderr_bytes=$(stat -c %s /tmp/l7_arm_compare.stderr)"
stdout_bytes=2732 stderr_bytes=0
rc=0
```

```text
$ sha256sum v2/evidence/l7_arm_compare.json
29aa7e30cf92d7b088f11497454b49b433fab2774d69ada7ce30b25a88236359  v2/evidence/l7_arm_compare.json
rc=0
```

```text
$ python3 -c "
import json
d=json.load(open('v2/evidence/l7_arm_compare.json'))
for arm in ('dequp_arm','on_arm'):
    a=d[arm]
    print(arm, {k:a[k] for k in ('n_msg','L7_dup','L7_rate','n_msgs_with_memory_refs','n_refs_total','n_refs_unique','refs_per_unique_mem_mean','dequp_msgs')})
    print('  llm:', json.dumps(a['llm'], ensure_ascii=False))
    print('  dequp_last:', json.dumps(a['dequp_last'], ensure_ascii=False))
print('delta:', json.dumps(d['delta'], ensure_ascii=False))
print('delta_shape:', json.dumps(d['delta_shape'], ensure_ascii=False))
"
dequp_arm {'n_msg': 510, 'L7_dup': 193, 'L7_rate': 0.378431, 'n_msgs_with_memory_refs': 412, 'n_refs_total': 824, 'n_refs_unique': 816, 'refs_per_unique_mem_mean': 1.0098, 'dequp_msgs': 510}
  llm: {"calls": 2966, "tokens_in": 376064, "tokens_out": 268556, "tokens_total": 644620, "degraded": 0, "by_provider": {"openai_compat": 2966}, "dialogue_calls": 598, "dialogue_tokens_in": 236082, "dialogue_tokens_out": 18232}
  dequp_last: {"collisions": 88, "mem_used": 816, "messages": 510, "retries": 88, "top_mem": [{"mem_id": "M-P010-000470", "n": 2}, {"mem_id": "M-P003-000740", "n": 2}, {"mem_id": "M-P003-000944", "n": 2}], "v": "l7-dequp/1"}
on_arm {'n_msg': 510, 'L7_dup': 332, 'L7_rate': 0.65098, 'n_msgs_with_memory_refs': 412, 'n_refs_total': 824, 'n_refs_unique': 128, 'refs_per_unique_mem_mean': 6.4375, 'dequp_msgs': 0}
  llm: {"calls": 2878, "tokens_in": 271717, "tokens_out": 269123, "tokens_total": 540840, "degraded": 0, "by_provider": {"openai_compat": 2878}, "dialogue_calls": 510, "dialogue_tokens_in": 130924, "dialogue_tokens_out": 16057}
  dequp_last: {}
delta: {"calls": {"dequp": 2966, "on": 2878, "delta": 88}, "tokens_in": {"dequp": 376064, "on": 271717, "delta": 104347}, "tokens_out": {"dequp": 268556, "on": 269123, "delta": -567}, "tokens_total": {"dequp": 644620, "on": 540840, "delta": 103780}, "dialogue_calls": {"dequp": 598, "on": 510, "delta": 88}, "dialogue_tokens_in": {"dequp": 236082, "on": 130924, "delta": 105158}, "dialogue_tokens_out": {"dequp": 18232, "on": 16057, "delta": 2175}}
delta_shape: {"n_msg": 0, "L7_dup": -139, "L7_rate": -0.272549, "refs_unique_mem": 688, "refs_per_unique_mem_mean": -5.4277}
rc=0
```

## 2b. OFF 基线锚点复算（tool: tools/l7/l7_baseline_recount.py；输出到 /tmp，不覆盖已入库件）

```text
$ python3 tools/l7/l7_baseline_recount.py --on v2/evidence/run_f6_on_n16r60_seed42/run.jsonl --off v2/evidence/run_f6_off_n16r60_seed42/run.jsonl --out /tmp/l7_baseline_recount_recheck.json > /tmp/l7_baserecount.stdout 2>&1; echo rc=$?
rc=0
rc=0
```

```text
$ python3 -c "
import json
base=json.load(open('/tmp/l7_baseline_recount_recheck.json'))
cmp=json.load(open('v2/evidence/l7_arm_compare.json'))
off=base['off']; deq=cmp['dequp_arm']; on=base['on']
print('OFF 臂  L7_dup=', off['n_dup_msgs_L7'], 'L7_rate=', off['L7_rate'], 'n_msg=', off['n_msg'])
print('ON  臂  L7_dup=', on['n_dup_msgs_L7'],  'L7_rate=', on['L7_rate'],  'n_msg=', on['n_msg'])
print('DEQUP臂 L7_dup=', deq['L7_dup'],        'L7_rate=', deq['L7_rate'], 'n_msg=', deq['n_msg'])
print('DEQUP-OFF  : dup_delta=', deq['L7_dup']-off['n_dup_msgs_L7'], 'rate_delta_pp=', round((deq['L7_rate']-off['L7_rate'])*100,4))
print('DEQUP-ON   : dup_delta=', deq['L7_dup']-on['n_dup_msgs_L7'],  'rate_delta_pp=', round((deq['L7_rate']-on['L7_rate'])*100,4))
print('ON-OFF     : dup_delta=', on['n_dup_msgs_L7']-off['n_dup_msgs_L7'], 'rate_delta_pp=', round((on['L7_rate']-off['L7_rate'])*100,4))
print('DEQUP 记忆引用: msgs_with_refs=', deq['n_msgs_with_memory_refs'], 'refs_total=', deq['n_refs_total'], 'refs_unique=', deq['n_refs_unique'], 'mean_per_unique=', deq['refs_per_unique_mem_mean'])
print('OFF   记忆引用: msgs_with_refs=', off['n_msgs_with_memory_refs'], 'refs_total=', off['n_refs_total'])
print('ON    记忆引用: msgs_with_refs=', on['n_msgs_with_memory_refs'], 'refs_total=', on['n_refs_total'], 'refs_unique=', on['n_refs_unique_mem_ids'], 'mean_per_unique=', on['refs_per_unique_mem_mean'])
print('重试率 = retries/messages =', cmp['dequp_arm']['dequp_last']['retries'], '/', cmp['dequp_arm']['dequp_last']['messages'], '=', round(cmp['dequp_arm']['dequp_last']['retries']/cmp['dequp_arm']['dequp_last']['messages']*100,4), '%')
print('额外 dialogue 调用 = 598-510 =', deq['llm']['dialogue_calls']-510, '；retries=', cmp['dequp_arm']['dequp_last']['retries'], '⇒ 差额完全由重试解释:', (deq['llm']['dialogue_calls']-510)==cmp['dequp_arm']['dequp_last']['retries'])
"
OFF 臂  L7_dup= 181 L7_rate= 0.354902 n_msg= 510
ON  臂  L7_dup= 332 L7_rate= 0.65098 n_msg= 510
DEQUP臂 L7_dup= 193 L7_rate= 0.378431 n_msg= 510
DEQUP-OFF  : dup_delta= 12 rate_delta_pp= 2.3529
DEQUP-ON   : dup_delta= -139 rate_delta_pp= -27.2549
ON-OFF     : dup_delta= 151 rate_delta_pp= 29.6078
DEQUP 记忆引用: msgs_with_refs= 412 refs_total= 824 refs_unique= 816 mean_per_unique= 1.0098
OFF   记忆引用: msgs_with_refs= 0 refs_total= 0
ON    记忆引用: msgs_with_refs= 412 refs_total= 824 refs_unique= 128 mean_per_unique= 6.4375
重试率 = retries/messages = 88 / 510 = 17.2549 %
额外 dialogue 调用 = 598-510 = 88 ；retries= 88 ⇒ 差额完全由重试解释: True
rc=0
```

## 3. 官方措辞/守卫指标（tool: tools/d5/dialogue_metrics.py；F-6 唯一来源）

```text
$ python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl --meta v2/evidence/run_f6_dequp_n16r60_seed42/meta.json --out-json v2/evidence/l7_metrics_dequp_d5.json --out-md v2/evidence/l7_metrics_dequp_d5.md > /tmp/l7_d5.stdout 2>&1; echo rc=$? out_json_sha=$(sha256sum v2/evidence/l7_metrics_dequp_d5.json)
rc=0 out_json_sha=a06ed524760f7bfe5444aef61a6a81964b8494b743021bae8eaa9a8e1aad551e v2/evidence/l7_metrics_dequp_d5.json
rc=0
```

```text
$ python3 -c "
import json
P={'dequp':'v2/evidence/l7_metrics_dequp_d5.json','on':'v2/evidence/r1_f6_on_metrics.json','off':'v2/evidence/r1_f6_off_metrics.json'}
M={k:json.load(open(v)) for k,v in P.items()}
keys=('L-5_template_hit_rate','L-6_dup_exact_rate','L-7_dup_ngram8_rate','L-8_agent_id_leak_rate','L-11_second_person_rate_dm_group','L-10_denominator')
for k in keys:
    print(k, {a: M[a]['L_wording'].get(k) for a in ('off','on','dequp')})
for a in ('off','on','dequp'):
    print('F-6', a, M[a]['F-6_crossday_memory']['timeref_rate'])
for a in ('off','on','dequp'):
    print('L-13 n', a, M[a]['L-13_token_leak']['n'])
print('admission dequp=', M['dequp']['admission'] if isinstance(M['dequp']['admission'],str) else M['dequp']['admission'].get('verdict'))
print('d5 out sha:', {a: __import__('hashlib').sha256(open(P[a],'rb').read()).hexdigest()[:16] for a in P})
"
L-5_template_hit_rate {'off': 0.011765, 'on': 0.015686, 'dequp': 0.001961}
L-6_dup_exact_rate {'off': 0.101961, 'on': 0.127451, 'dequp': 0.003922}
L-7_dup_ngram8_rate {'off': 0.354902, 'on': 0.65098, 'dequp': 0.378431}
L-8_agent_id_leak_rate {'off': 0.0, 'on': 0.0, 'dequp': 0.0}
L-11_second_person_rate_dm_group {'off': 0.665934, 'on': 0.650549, 'dequp': 0.698901}
L-10_denominator {'off': 407, 'on': 483, 'dequp': 471}
F-6 off 0.037255
F-6 on 0.111765
F-6 dequp 0.082353
L-13 n off 2
L-13 n on 14
L-13 n dequp 9
admission dequp= ADMITTED
d5 out sha: {'dequp': 'a06ed524760f7bfe', 'on': 'abe4977d8ecb6dc4', 'off': 'cb757208249dd9fc'}
rc=0
```

## 4. F-6 守卫与两臂计数（tool: tools/f6/f6_metrics.py，交叉核对用）

```text
$ python3 tools/f6/f6_metrics.py --run DEQUP=v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl --run ON=v2/evidence/run_f6_on_n16r60_seed42/run.jsonl --official DEQUP=v2/evidence/l7_metrics_dequp_d5.json --out v2/evidence/l7_f6_guard_check.json > /tmp/l7_f6.stdout 2>&1; echo rc=$? stdout_sha=$(sha256sum v2/evidence/l7_f6_guard_check.json)
rc=0 stdout_sha=c0d66fc22d9c7ba3ba05d770464ac4426e7383e858fc931fd605eeb9f66c2f21 v2/evidence/l7_f6_guard_check.json
rc=0
```

```text
$ grep -E 'crosscheck_timeref|F-6 跨天' /tmp/l7_f6.stdout | head -5
| **F-6 跨天记忆引用率（官方）** | 0.082353 | None |
| crosscheck_timeref | 2.94 | True | False |
rc=0
```

## 5. 真跑验真（obs llm-cost，原始输出入库）

```text
$ cd code && python3 -m obs llm-cost --log ../v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl --require-provider openai_compat > /tmp/l7_llmcost_dequp.out 2>/tmp/l7_llmcost_dequp.err; echo rc=$?; cp /tmp/l7_llmcost_dequp.out ../v2/evidence/l7_llmcost_dequp.txt; cat /tmp/l7_llmcost_dequp.out
rc=0
{"engine_log":{"by_provider":{"openai_compat":2966},"by_purpose":{"dialogue":{"cached":0,"calls":598,"degraded":0,"thinking":0,"tokens_in":236082,"tokens_out":18232},"importance":{"cached":1387,"calls":1523,"degraded":0,"thinking":0,"tokens_in":2312,"tokens_out":35942},"judge":{"cached":0,"calls":668,"degraded":0,"thinking":668,"tokens_in":88382,"tokens_out":205158},"negotiation":{"cached":34,"calls":49,"degraded":0,"thinking":0,"tokens_in":1787,"tokens_out":531},"plan":{"cached":0,"calls":16,"degraded":0,"thinking":0,"tokens_in":1447,"tokens_out":978},"reflect":{"cached":4,"calls":112,"degraded":0,"thinking":0,"tokens_in":46054,"tokens_out":7715}},"llm_judgment_by_dimension":{"affection":132,"rel_affinity":32,"rel_familiarity":222,"rel_trust":2,"respect":132,"stance":132,"weekly_focus":16},"source":"engine_log(LLM_CALL)","total":{"cached":1425,"calls":2966,"degraded":0,"thinking":668,"tokens_in":376064,"tokens_out":268556,"tokens_total":644620}},"provider_guard":{"by_provider":{"openai_compat":2966},"expected":"openai_compat","ok":true,"policy":"计划用真 LLM 时必须显式校验 provider 计数 > 0 且无 mock 混入。","problems":[]}}
rc=0
```

```text
$ python3 -c "
import json
d=json.loads(open('v2/evidence/l7_llmcost_dequp.txt',encoding='utf-8').read().strip())
json.dump(d, open('v2/evidence/l7_llmcost_dequp.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('provider_guard:', json.dumps(d['provider_guard'], ensure_ascii=False))
print('total:', json.dumps(d['engine_log']['total'], ensure_ascii=False))
print('by_purpose.dialogue:', json.dumps(d['engine_log']['by_purpose']['dialogue'], ensure_ascii=False))
"
provider_guard: {"by_provider": {"openai_compat": 2966}, "expected": "openai_compat", "ok": true, "policy": "计划用真 LLM 时必须显式校验 provider 计数 > 0 且无 mock 混入。", "problems": []}
total: {"cached": 1425, "calls": 2966, "degraded": 0, "thinking": 668, "tokens_in": 376064, "tokens_out": 268556, "tokens_total": 644620}
by_purpose.dialogue: {"cached": 0, "calls": 598, "degraded": 0, "thinking": 0, "tokens_in": 236082, "tokens_out": 18232}
rc=0
```

```text
$ sha256sum v2/evidence/l7_llmcost_dequp.txt v2/evidence/l7_llmcost_dequp.json
b59772c70840417a2b9d7bcbbd9c92b8c11e8bc2c6c107723f5f78f709dd4d15  v2/evidence/l7_llmcost_dequp.txt
b37adc2fdb1f4ac5c14a6b146146db08c248731f8f719c000338990449b52b0a  v2/evidence/l7_llmcost_dequp.json
rc=0
```

## 6. 截图（真拍；来源 run 目录 + 渲染命令 + 日志 sha256）

```text
$ sha256sum v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl code/frontend/sample/dialogue_run_f6_dequp_n16r60_seed42/threads.json
6bf3ec88700fa1a7451b18c63678d0904c69b9de39896739190e7e674db8fdbd  v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl
0720bd050c51b19ced65ba304c847ce1e26d91510ae3884002e392b308b08043  code/frontend/sample/dialogue_run_f6_dequp_n16r60_seed42/threads.json
rc=0
```

```text
$ python3 -c "
import json
d=json.load(open('code/frontend/sample/dialogue_run_f6_dequp_n16r60_seed42/threads.json'))
s=d['source']
print({k:s[k] for k in ('run_label','run_sha256','run_bytes','events_total_in_log')})
print('messages/threads:', d.get('stats') if isinstance(d.get('stats'),dict) else 'n/a')
"
{'run_label': 'run_f6_dequp_n16r60_seed42-6bf3ec88', 'run_sha256': '6bf3ec88700fa1a7451b18c63678d0904c69b9de39896739190e7e674db8fdbd', 'run_bytes': 55404972, 'events_total_in_log': 116385}
messages/threads: {'messages': 510, 'threads': 169, 'multi_turn_threads': 88, 'threads_ge3_turns': 77, 'legacy_threads': 0, 'moves': 299, 'agents_who_moved': 16, 'day_slot_cells': 20, 'ref_edges': 0, 'echo_groups': 0, 'threaded_messages': 510, 'legacy_messages': 0, 'participants': 16, 'max_turns': 6}
rc=0
```

```text
$ for f in v2/evidence/l7_shots/*.png; do stat -c '%s %y %n' "$f"; sha256sum "$f"; done
183326 2026-10-21 20:07:59.734858154 +0800 v2/evidence/l7_shots/run_f6_dequp_n16r60_seed42-600-6bf3ec88.png
cd74484a80e5604da53295eabdd945ae0f12a80eae9b9e3fadf7596370692867  v2/evidence/l7_shots/run_f6_dequp_n16r60_seed42-600-6bf3ec88.png
261319 2026-10-21 20:07:54.119705900 +0800 v2/evidence/l7_shots/run_f6_dequp_n16r60_seed42-chat-6bf3ec88.png
a82aa3102b61f63dad259c131d2ede856567ce09dfe2039584b0e0795ed4c926  v2/evidence/l7_shots/run_f6_dequp_n16r60_seed42-chat-6bf3ec88.png
284620 2026-10-21 20:07:56.027644995 +0800 v2/evidence/l7_shots/run_f6_dequp_n16r60_seed42-rhythm-6bf3ec88.png
2b0d74a84cfac385e88a70f6bdb52da322ca274fc98d848d4df4602bb8af367c  v2/evidence/l7_shots/run_f6_dequp_n16r60_seed42-rhythm-6bf3ec88.png
177519 2026-10-21 20:07:57.859113740 +0800 v2/evidence/l7_shots/run_f6_dequp_n16r60_seed42-spread-6bf3ec88.png
90f762ca29eb7cea2aa543581e223bc41162961aea5c1f7111452fe2a39ae72d  v2/evidence/l7_shots/run_f6_dequp_n16r60_seed42-spread-6bf3ec88.png
rc=0
```

```text
$ sha256sum v2/evidence/l7_shots/render.log; echo; head -8 v2/evidence/l7_shots/render.log
c8ced752287b62eeea9d0ec0b40b64d89e8a9e72a620e80a4d101c72d26e70d4  v2/evidence/l7_shots/render.log

# render.log · R12 DEQUP 臂截图（真拍）
# 生成时刻: 2026-10-21 20:07:52 +0800
# 来源 run 目录: v2/evidence/run_f6_dequp_n16r60_seed42/
# run.jsonl sha256: 6bf3ec88700fa1a7451b18c63678d0904c69b9de39896739190e7e674db8fdbd
# threads.json: code/frontend/sample/dialogue_run_f6_dequp_n16r60_seed42/threads.json
# render cmd: bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 sample/dialogue_run_f6_dequp_n16r60_seed42/threads.json "" "" ../v2/evidence/l7_shots

$ python3 frontend/tools/gen_threads.py --log ../v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl --meta ../v2/evidence/run_f6_dequp_n16r60_seed42/meta.json --out frontend/sample/dialogue_run_f6_dequp_n16r60_seed42/threads.json --require-complete --label run_f6_dequp_n16r60_seed42-6bf3ec88
rc=0
```

## 7. 禁改目录自检

```text
$ git diff --stat 263a4300692d2ef3136c8a50e9bade2f99608945 -- code/life code/orchestration code/config code/engine; echo rc=$?
rc=0
rc=0
```

```text
$ git status --short
?? code/frontend/sample/dialogue_run_f6_dequp_n16r60_seed42/
?? code/frontend/sample/dialogue_run_g1_b0_n16r60_seed42/
?? reports/R12-l7-dequp.md
?? tools/l7/l7_arm_compare.py
?? tools/l7/l7_receipt.sh
?? v2/evidence/d4_a1_overlap_check.py
?? v2/evidence/d4_a1_pipeline.sh
?? v2/evidence/d4_judge_run.py
?? v2/evidence/d4_judge_sample.py
?? v2/evidence/d4_judge_sample_A0.json
?? v2/evidence/d4_judge_sample_P1.json
?? v2/evidence/d4_judge_sampling_plan.md
?? v2/evidence/d4_judge_summary.py
?? v2/evidence/d4_metrics_P1.json
?? v2/evidence/d4_preflight_P1.json
?? v2/evidence/d4_prompt_diff_P2.txt
?? v2/evidence/d4_prompt_diff_P3.txt
?? v2/evidence/d4_prompt_patch.py
?? v2/evidence/d4_r9_binding_audit.md
?? v2/evidence/d4_side_by_side.md
?? v2/evidence/g1_launch_evidence_b0.txt
?? v2/evidence/l7_arm_compare.json
?? v2/evidence/l7_f6_guard_check.json
?? v2/evidence/l7_llmcost_dequp.json
?? v2/evidence/l7_llmcost_dequp.txt
?? v2/evidence/l7_metrics_dequp_d5.json
?? v2/evidence/l7_metrics_dequp_d5.md
?? v2/evidence/l7_recompute_receipt.md
?? v2/evidence/l7_shots/
?? v2/evidence/r1_llmcost_off.json
?? v2/evidence/r1_llmcost_off.txt
?? v2/evidence/run_dr_round1_arm-ctrl_n16r60_seed42/
?? v2/evidence/run_f6_dequp_n16r60_seed42/
?? v2/evidence/run_g1_b0_n16r60_seed42/
rc=0
```

## 8. 代码侧自证（①②零额外调用；单变量范围）

```text
$ grep -n 'llm.call\|LLM_CALL' code/life/anti_repeat.py ; echo rc=$?
rc=1
rc=0
```

```text
$ git show --stat --oneline 263a4300692d2ef3136c8a50e9bade2f99608945 | head -12
263a430 life: L7 去重臂（LIFE_PROMPT_MEMORY_F6_DEQUP，默认 OFF）+ 零跑批复算脚本
 code/life/agent.py                   |  42 +++++++--
 code/life/anti_repeat.py             | 146 +++++++++++++++++++++++++++++++
 code/tests/test_anti_repeat.py       | 162 +++++++++++++++++++++++++++++++++++
 tools/l7/l7_baseline_recount.py      | 110 ++++++++++++++++++++++++
 v2/evidence/l7_baseline_recount.json | 103 ++++++++++++++++++++++
 5 files changed, 557 insertions(+), 6 deletions(-)
rc=0
```

```text
$ git diff --numstat 263a4300692d2ef3136c8a50e9bade2f99608945^ 263a4300692d2ef3136c8a50e9bade2f99608945 -- code/ | sed -n '1,10p'
36	6	code/life/agent.py
146	0	code/life/anti_repeat.py
162	0	code/tests/test_anti_repeat.py
rc=0
```
