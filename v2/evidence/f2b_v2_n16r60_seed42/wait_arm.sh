#!/usr/bin/env bash
# 后台等待器：轮询产物文件直到出现 END 标记（或 python 进程消失 5 次仍无 END ⇒ 异常退出）
# 用途：避免在前台长 sleep；本脚本自身在后台跑，结束时向调用方通知。
set -u
E=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/f2b_v2_n16r60_seed42
ARM="${1:?arm}"
MAX=${2:-5400}
t=0
gone=0
while [[ $t -lt $MAX ]]; do
  if [[ -f "$E/$ARM/END" ]]; then
    echo "DONE arm=$ARM END=$(cat "$E/$ARM/END") lines=$(wc -l < "$E/$ARM/run.jsonl" 2>/dev/null) t=${t}s"
    exit 0
  fi
  if ! ps -eo cmd | grep -F 'python3 -m orchestration' | grep -qv grep; then
    gone=$((gone+1))
    if [[ $gone -ge 5 ]]; then
      echo "ABNORMAL arm=$ARM: python 进程消失但无 END；host.log 末尾："
      tail -20 "$E/${ARM}_host.log" 2>/dev/null
      exit 3
    fi
  fi
  sleep 20
  t=$((t+20))
done
echo "TIMEOUT arm=$ARM t=${t}s lines=$(wc -l < "$E/$ARM/run.jsonl" 2>/dev/null)"
exit 4
