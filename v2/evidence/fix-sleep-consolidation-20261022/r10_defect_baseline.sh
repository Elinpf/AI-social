#!/usr/bin/env bash
# r10_defect_baseline.sh —— R10「睡眠—固化」两条链路缺陷的【修前】基线取数（纯只读）
#
# 目的：在不跑任何新批、不改任何已跟踪文件的前提下，用硬盘上现成的真跑日志
#       一次算出三批的缺陷计数，输出可直接贴进报告表格的 Markdown 行。
#
# 用法：
#   bash v2/evidence/fix-sleep-consolidation-20261022/r10_defect_baseline.sh
#   bash .../r10_defect_baseline.sh <run_dir_1> [run_dir_2 ...]   # 自定义批次目录（相对仓库根）
#
# 只读保证：只读文件并 print，**不写 run.jsonl、不改任何文件**；唯一输出是 stdout。
#
# ════════════════════════════════════════════════════════════════════════
# ⚠ 全部计数一律「解析 JSON 取顶层 type / payload 字段」，禁止任何子串匹配。
#   本脚本前后踩过两个同类坑，二者都是「子串计数把 A 数成 B」：
#
#   坑 ①（旧版 v1 的真 bug，曾发布错误数字）
#     `grep -c '"type":"MEMORY_CONSOLIDATE"'` 会把 **DROPPED 事件的 payload 也数进去**，
#     因为 DROPPED 的 payload 长这样：
#         {"actor":"P001","keys":["text"],"reason":"unknown_intent_field","type":"MEMORY_CONSOLIDATE"}
#     ⇒ 每条被丢弃的固化被数两次，consolidate_count 翻倍（a5 报 1510，实为 755；
#       worldline 两批报 3558，实为 1779），discard_rate 因此被算成 50.00%（实为 100.00%）。
#     `grep '^{"actor".*"type":"MEMORY_CONSOLIDATE"'` 也救不了（DROPPED 行同样以 {"actor" 开头，
#       验收员实测仍得 1510）⇒ 唯一稳妥做法就是 json.loads 后取顶层 "type"。
#
#   坑 ②（SM 写入假阳性，+1011）
#     `grep -c '"mem_id":"M-P[0-9]*-SM-'` 会命中 `"produced_mem_id":"M-P001-SM-MARKET"` 里的子串
#     `mem_id":"M-P001-SM-` ⇒ 把「本应产出 SM 的固化」错记成「写入成功的 SM」，
#     ctrl/a1 两批凭空多出 1011 条。
# ════════════════════════════════════════════════════════════════════════
#
# 缺陷定义（证据见 reports/R10-sleep-forgetting-persona-drift.md §5.3）：
#   缺陷① `MEMORY_CONSOLIDATE` 携带的 `text` 不在 `_PASSTHROUGH` 白名单内 ⇒ 每条固化额外落一个
#         DROPPED{reason:"unknown_intent_field", type:"MEMORY_CONSOLIDATE", keys:["text"]}，
#         且 SM 语义记忆实际写入为 0。
#         代码锚点（HEAD=46e4380 实测）：code/orchestration/integration.py:205-209（_PASSTHROUGH）、
#         :583-587（base 不含 text）；code/life/agent.py:1467（提交 "text": g["text"]）。
#   缺陷② `SLEEP_COMPLETED` 的 `drift_permille / pf0 / pf_t` 恒为 null。
#         代码锚点：code/life/agent.py:1481-1482（sleep_end payload 只有 day/slot/actual_ticks）。
#
# 输出列（每批一行，Markdown）：
#   batch | consolidate_count | discard_count | discard_rate | sm_should_count | SM_write_count | drift_null/null_total | events | bytes | meta.json
#   判读：discard_count == consolidate_count ⇒ discard_rate = 100.00%（每条固化都被丢弃）；
#         且 consolidate_count == sm_should_count ⇒ SM 产出 100% 被丢弃；SM_write_count 应为 0；
#         drift_null == null_total ⇒ 缺陷② 100%。

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT" || exit 2

# 默认三份可用日志。第 4 份 run_a1budget_real_n16r42_seed42 于 18:04:18 被重启、
# run.jsonl 被截断重写（且长时间零 flush），计数无意义 ⇒ 刻意不纳入默认清单。
if [ "$#" -gt 0 ]; then
  DIRS=("$@")
else
  DIRS=(
    "v2/evidence/run_worldline_c1_ctrl_n16r84_seed42"
    "v2/evidence/run_worldline_c1_a1_n16r84_seed42"
    "v2/evidence/run_a5_real_n16r42_seed42"
  )
fi

echo "# R10 缺陷【修前】基线（只读取数，生成于 $(date -Iseconds)）"
echo "# repo HEAD = $(git rev-parse HEAD 2>/dev/null) ｜ 脚本 = v2/evidence/fix-sleep-consolidation-20261022/r10_defect_baseline.sh"
echo "# 口径：全部计数由 json.loads 取顶层 type / payload 字段得出，**无任何子串匹配**（见脚本头部坑①②）"
echo ""
echo "| batch | consolidate_count | discard_count | discard_rate | sm_should_count | SM_write_count | drift_null/null_total | events | run.jsonl bytes | meta.json |"
echo "|---|---|---|---|---|---|---|---|---|---|"

python3 - "${DIRS[@]}" <<'PY'
import json, os, sys

for d in sys.argv[1:]:
    f = os.path.join(d, "run.jsonl")
    name = os.path.basename(d.rstrip("/"))
    if not os.path.isfile(f):
        print(f"| `{name}` | — | — | — | — | — | — | — | — | **缺 run.jsonl** |")
        continue

    consolidate = discard = sm_should = sm_write = sleep_total = sleep_null = events = 0
    with open(f, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            events += 1
            r = json.loads(line)
            t = r.get("type")                       # ← 顶层 type，唯一可信来源
            p = r.get("payload") or {}
            if t == "MEMORY_CONSOLIDATE":
                consolidate += 1
                if "-SM-" in str(p.get("produced_mem_id") or ""):
                    sm_should += 1
            elif t == "DROPPED":
                # payload.type 才是「被丢弃的事件名」，与顶层 type=="DROPPED" 是两回事
                if p.get("reason") == "unknown_intent_field" and p.get("type") == "MEMORY_CONSOLIDATE":
                    discard += 1
            elif t == "MEMORY_WRITE":
                if "-SM-" in str(p.get("mem_id") or ""):
                    sm_write += 1
            elif t == "SLEEP_COMPLETED":
                sleep_total += 1
                if p.get("drift_permille") is None:
                    sleep_null += 1

    rate = f"{100.0 * discard / consolidate:.2f}%" if consolidate else "n/a"
    size = os.path.getsize(f)
    meta = "有" if os.path.isfile(os.path.join(d, "meta.json")) else "**无（⇒ d5 判 probe）**"
    print(f"| `{name}` | {consolidate} | {discard} | {rate} | {sm_should} | {sm_write} | "
          f"{sleep_null}/{sleep_total} | {events} | {size} | {meta} |")
PY

echo ""
echo "## 判据（修后合格线）"
echo ""
echo "- 缺陷①：\`discard_count\` **→ 0**；\`SM_write_count\` **→ > 0** 且 ≥ 修前 \`consolidate_count\`（ctrl/a1 = 1779，a5 = 755）"
echo "- 缺陷②：\`drift_null/null_total\` **→ 0/112**（ctrl/a1）、**0/48**（a5）；非 null 值域参照同批 PERSONA_DRIFT 事件量级（≤10‰）"
echo "- 以上均为计数型判据，**不依赖 bootstrap 噪声带**"
echo ""
echo "## 交叉核验（jq 1.7，可选；同样只取顶层 type，避免子串歧义）"
echo ""
echo '```bash'
echo "F=v2/evidence/run_worldline_c1_ctrl_n16r84_seed42/run.jsonl"
echo "jq -r 'select(.type==\"SLEEP_COMPLETED\") | .payload.drift_permille' \$F | sort | uniq -c   # 期望仅 112 null"
echo "jq -r 'select(.type==\"MEMORY_CONSOLIDATE\") | 1' \$F | wc -l                              # 期望 1779"
echo "jq -r 'select(.type==\"DROPPED\" and .payload.type==\"MEMORY_CONSOLIDATE\") | 1' \$F | wc -l # 期望 1779"
echo '```'
