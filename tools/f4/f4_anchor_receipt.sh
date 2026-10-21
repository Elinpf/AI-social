#!/usr/bin/env bash
# F-4 锚点复算回执（零跑批）：把 f4_anchor.md 里的每个数字一次性重算出来。
# 用法（仓库根执行）：bash tools/f4/f4_anchor_receipt.sh > v2/evidence/f4_anchor_receipt.txt 2>&1
set -u
cd "$(dirname "$0")/../.." || exit 2
OFF=v2/evidence/run_f6_off_n16r60_seed42/run.jsonl
ON=v2/evidence/run_f6_on_n16r60_seed42/run.jsonl
DEQ=v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl

echo "### 0) 环境与代码锚点"
git rev-parse HEAD
git branch --show-current
echo

echo "### 1) 三份 run.jsonl 的 sha256（sha8 = 前 8 位）"
sha256sum "$OFF" "$ON" "$DEQ"
echo

echo "### 2) dialogue_repair 开关默认值（config 原文）"
cat code/config/dialogue_repair.json
echo

echo "### 3) 日志里 dialogue_rift 字段命中条数（grep -c；默认关闭应为 0）"
for f in "$OFF" "$ON" "$DEQ"; do printf '%s ' "$f"; grep -c '"dialogue_rift"' "$f"; done
echo

echo "### 4) 官方指标实现复算（tools/d5/dialogue_metrics.py 的 compute()，F-4 / L-13）"
python3 tools/f4/f4_anchor_recompute.py \
  --run "off=$OFF" --run "on=$ON" --run "dequp=$DEQ" \
  --out-json v2/evidence/f4_anchor_recompute.json
echo

echo "### 5) 近失分析（张力后同线程最近修复词的距离）"
python3 tools/f4/f4_anchor_nearmiss.py \
  --run "off=$OFF" --run "on=$ON" --run "dequp=$DEQ" \
  --out-json v2/evidence/f4_anchor_nearmiss.json
echo

echo "### 6) 逐事件明细：张力事件 topic 分布 + 修复命中（off 臂原文，其余见 JSON）"
python3 - <<'PY'
import json
d = json.load(open('v2/evidence/f4_anchor_recompute.json', encoding='utf-8'))
for a in d['arms']:
    print('== arm', a['label'], 'sha8', a['log_sha8'], 'MSG', a['n_messages'],
          'neg_msgs', a['n_neg_msgs'], 'repair_msgs', a['n_repair_msgs'],
          'dialogue_rift', a['dialogue_rift_field_hits'])
    print('   by_topic:', json.dumps(a['by_topic'], ensure_ascii=False, sort_keys=True))
    print('   by_event_type:', json.dumps(a['by_event_type'], ensure_ascii=False, sort_keys=True))
    print('   repaired_in_detail:', [(e['thread'], e['cur_seq'], e['repair']['words'], e['repair']['lag'])
                                     for e in a['events'] if e['repaired']])
PY
echo

echo "### 7) 三臂 meta.json 身份（code_sha / 规模 / provider）"
python3 - <<'PY'
import json
for arm in ('off', 'on', 'dequp'):
    m = json.load(open(f'v2/evidence/run_f6_{arm}_n16r60_seed42/meta.json', encoding='utf-8'))
    print(arm, {k: m.get(k) for k in ('code_sha', 'rounds', 'seed', 'events',
                                      'provider', 'model', 'llm_calls', 'degraded_calls')})
PY
echo

echo "### 8) L-13 泄漏串明细（ctx.topic 原串出现在正文）"
python3 - <<'PY'
import json
d = json.load(open('v2/evidence/f4_anchor_recompute.json', encoding='utf-8'))
for a in d['arms']:
    print('== arm', a['label'], 'n=', a['official_L13']['n'], 'by_topic=', a['official_L13']['by_topic'])
    for r in a['l13_leaks']:
        print('   seq=%s type=%s topic=%s body=%s' % (r['seq'], r['event_type'], r['topic'], r['body']))
PY

echo "### 9) 张力检测精度初查（自述状态词 vs 人际冲突词；只披露分子噪声，不改口径）"
python3 tools/f4/f4_tension_precision.py \
  --run "off=$OFF" --run "on=$ON" --run "dequp=$DEQ" \
  --out-json v2/evidence/f4_tension_precision.json
echo
