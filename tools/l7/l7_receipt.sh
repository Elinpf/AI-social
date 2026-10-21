#!/usr/bin/env bash
# l7_receipt.sh — R12 DEQUP 臂复算回执生成器（零跑批、只读日志 + 本地指标脚本）。
# 用法：bash tools/l7/l7_receipt.sh > v2/evidence/l7_recompute_receipt.md
# 纪律：每条命令的输出原样落入回执，报告里的数字只能引用本回执的输出。
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 2
D=v2/evidence/run_f6_dequp_n16r60_seed42
O=v2/evidence/run_f6_on_n16r60_seed42

run () { echo; echo '```text'; echo "\$ $*"; bash -c "$*" 2>&1; echo "rc=$?"; echo '```'; }

echo "# R12 · DEQUP 臂复算回执（零跑批）"
echo
echo "> 生成时刻：$(date '+%F %T %z') ｜ 仓库 HEAD：$(git rev-parse HEAD 2>/dev/null) ｜ 分支：$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
echo "> 对应报告：\`reports/R12-l7-dequp.md\`"
echo "> 本回执的规矩：每条数值都给「命令 → 输入路径 → 输出」；输出为实跑捕获，未人工改写。"
echo
echo "## 0. 串行纪律"
run 'pgrep -af "[o]rchestration run" ; echo rc=$?'
run 'pgrep -af "[r]un_batch.sh" ; echo rc=$?'
echo
echo '> `rc=1`（无命中）⇒ 本回执生成期间没有任何跑批在跑，也没被我启动（零跑批）。'
echo
echo "## 1. 批身份（两臂）"
run "sha256sum $D/run.jsonl $D/meta.json $D/host.log $O/run.jsonl $O/meta.json"
run "wc -l $D/run.jsonl $O/run.jsonl"
run "stat -c '%s %n' $D/run.jsonl $O/run.jsonl"
run "python3 -c \"
import json
for a in ('dequp','on'):
    d=json.load(open(f'v2/evidence/run_f6_{a}_n16r60_seed42/meta.json'))
    print(a, {k:d.get(k) for k in ('n','rounds','seed','events','wc_l','duration_sec','started_at','finished_at','code_sha','code_sha_end','llm_calls','llm_cached','llm_cached_ratio','provider','model','fallback_detected','msg_counts','degraded_calls','llm_purposes','side_root','endpoint_host')})
\""
run "python3 -c \"
import json
d=json.load(open('$D/meta.json'))
print('assertions:', json.dumps(d.get('assertions'), ensure_ascii=False))
print('git_dirty_code_files:', json.dumps(d.get('git_dirty_code_files'), ensure_ascii=False))
print('derived_from_log_sha256:', d.get('derived_from_log_sha256'))
print('run_sha256:', d.get('run_sha256'), 'run_bytes:', d.get('run_bytes'))
\""
echo
echo "## 2. 零跑批复算：arm 对比（tool: tools/l7/l7_arm_compare.py）"
run "python3 tools/l7/l7_arm_compare.py --dequp $D/run.jsonl --on $O/run.jsonl --out v2/evidence/l7_arm_compare.json > /tmp/l7_arm_compare.stdout 2>/tmp/l7_arm_compare.stderr ; echo \"stdout_bytes=\$(stat -c %s /tmp/l7_arm_compare.stdout) stderr_bytes=\$(stat -c %s /tmp/l7_arm_compare.stderr)\""
run "sha256sum v2/evidence/l7_arm_compare.json"
run "python3 -c \"
import json
d=json.load(open('v2/evidence/l7_arm_compare.json'))
for arm in ('dequp_arm','on_arm'):
    a=d[arm]
    print(arm, {k:a[k] for k in ('n_msg','L7_dup','L7_rate','n_msgs_with_memory_refs','n_refs_total','n_refs_unique','refs_per_unique_mem_mean','dequp_msgs')})
    print('  llm:', json.dumps(a['llm'], ensure_ascii=False))
    print('  dequp_last:', json.dumps(a['dequp_last'], ensure_ascii=False))
print('delta:', json.dumps(d['delta'], ensure_ascii=False))
print('delta_shape:', json.dumps(d['delta_shape'], ensure_ascii=False))
\""
echo
echo "## 2b. OFF 基线锚点复算（tool: tools/l7/l7_baseline_recount.py；输出到 /tmp，不覆盖已入库件）"
run "python3 tools/l7/l7_baseline_recount.py --on $O/run.jsonl --off v2/evidence/run_f6_off_n16r60_seed42/run.jsonl --out /tmp/l7_baseline_recount_recheck.json > /tmp/l7_baserecount.stdout 2>&1; echo rc=\$?"
run "python3 -c \"
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
\""
echo
echo "## 3. 官方措辞/守卫指标（tool: tools/d5/dialogue_metrics.py；F-6 唯一来源）"
run "python3 tools/d5/dialogue_metrics.py --log $D/run.jsonl --meta $D/meta.json --out-json v2/evidence/l7_metrics_dequp_d5.json --out-md v2/evidence/l7_metrics_dequp_d5.md > /tmp/l7_d5.stdout 2>&1; echo rc=\$? out_json_sha=\$(sha256sum v2/evidence/l7_metrics_dequp_d5.json)"
run "python3 -c \"
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
\""
echo
echo "## 4. F-6 守卫与两臂计数（tool: tools/f6/f6_metrics.py，交叉核对用）"
run "python3 tools/f6/f6_metrics.py --run DEQUP=$D/run.jsonl --run ON=$O/run.jsonl --official DEQUP=v2/evidence/l7_metrics_dequp_d5.json --out v2/evidence/l7_f6_guard_check.json > /tmp/l7_f6.stdout 2>&1; echo rc=\$? stdout_sha=\$(sha256sum v2/evidence/l7_f6_guard_check.json)"
run "grep -E 'crosscheck_timeref|F-6 跨天' /tmp/l7_f6.stdout | head -5"
echo
echo "## 5. 真跑验真（obs llm-cost，原始输出入库）"
run "cd code && python3 -m obs llm-cost --log ../$D/run.jsonl --require-provider openai_compat > /tmp/l7_llmcost_dequp.out 2>/tmp/l7_llmcost_dequp.err; echo rc=\$?; cp /tmp/l7_llmcost_dequp.out ../v2/evidence/l7_llmcost_dequp.txt; cat /tmp/l7_llmcost_dequp.out"
run "python3 -c \"
import json
d=json.loads(open('v2/evidence/l7_llmcost_dequp.txt',encoding='utf-8').read().strip())
json.dump(d, open('v2/evidence/l7_llmcost_dequp.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('provider_guard:', json.dumps(d['provider_guard'], ensure_ascii=False))
print('total:', json.dumps(d['engine_log']['total'], ensure_ascii=False))
print('by_purpose.dialogue:', json.dumps(d['engine_log']['by_purpose']['dialogue'], ensure_ascii=False))
\""
run "sha256sum v2/evidence/l7_llmcost_dequp.txt v2/evidence/l7_llmcost_dequp.json"
echo
echo "## 6. 截图（真拍；来源 run 目录 + 渲染命令 + 日志 sha256）"
run "sha256sum $D/run.jsonl code/frontend/sample/dialogue_run_f6_dequp_n16r60_seed42/threads.json"
run "python3 -c \"
import json
d=json.load(open('code/frontend/sample/dialogue_run_f6_dequp_n16r60_seed42/threads.json'))
s=d['source']
print({k:s[k] for k in ('run_label','run_sha256','run_bytes','events_total_in_log')})
print('messages/threads:', d.get('stats') if isinstance(d.get('stats'),dict) else 'n/a')
\""
run "for f in v2/evidence/l7_shots/*.png; do stat -c '%s %y %n' \"\$f\"; sha256sum \"\$f\"; done"
run "sha256sum v2/evidence/l7_shots/render.log; echo; head -8 v2/evidence/l7_shots/render.log"
echo
echo "## 7. 禁改目录自检"
run "git diff --stat 263a4300692d2ef3136c8a50e9bade2f99608945 -- code/life code/orchestration code/config code/engine; echo rc=\$?"
run "git status --short"

echo
echo "## 8. 代码侧自证（①②零额外调用；单变量范围）"
run "grep -n 'llm.call\\|LLM_CALL' code/life/anti_repeat.py ; echo rc=\$?"
run "git show --stat --oneline 263a4300692d2ef3136c8a50e9bade2f99608945 | head -12"
run "git diff --numstat 263a4300692d2ef3136c8a50e9bade2f99608945^ 263a4300692d2ef3136c8a50e9bade2f99608945 -- code/ | sed -n '1,10p'"
