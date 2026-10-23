#!/usr/bin/env bash
# 进度轮询（单次调用只做一次快照；不做长 sleep）
set -u
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
E=$REPO/v2/evidence/f2b_v2_n16r60_seed42
ARM="${1:-run_off}"
echo "T=$(date -Iseconds) arm=$ARM"
if [[ -f "$E/$ARM/run.jsonl" ]]; then
  echo "run.jsonl 行数: $(wc -l < "$E/$ARM/run.jsonl")  bytes=$(stat -c%s "$E/$ARM/run.jsonl")"
else
  echo "run.jsonl: 尚未生成"
fi
echo "END 标记: $([[ -f "$E/$ARM/END" ]] && cat "$E/$ARM/END" || echo '(未出现)')"
echo "meta.json: $([[ -f "$E/$ARM/meta.json" ]] && echo 存在 || echo '(未生成)')"
echo "--- 存活进程（cmdline 中含 python3 -m orchestration 的 PID 与已运行时长）"
ps -eo pid,etime,cmd | grep -F 'python3 -m orchestration' | grep -v grep || echo "(无)"
echo "--- host.log 末尾 5 行"
tail -5 "$E/${ARM}_host.log" 2>/dev/null || echo "(无 host.log)"
