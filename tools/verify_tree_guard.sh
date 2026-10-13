#!/usr/bin/env bash
# T346：`make verify` 自检「跑中树被改」——**分段指纹 + 分级结论**。
#
#   起跑记【世界层】【前端】两枚内容指纹 → 跑真实门 → 收尾再算 → 分级裁决：
#     · **世界层（`config/**` + 世界层 `code/**`）跑中变** ⇒ **exit 2「结果不可信」**（请重跑）；
#     · **仅 `code/frontend/**` 跑中变** ⇒ **降级为告警，不阻断**（前端 CI 部分不可信；世界层结论仍可信）；
#     · 两者皆未变 ⇒ 门结果可信。
#
#   ⚠️ `HEAD` 只**记录**、**不作比较输入**（T346 修：否则一个无关提交就能把门错判红）。
#
# 退出码：0=门全绿且世界层未变；非 0=门失败（其原码）；2=**世界层**跑中被改（结果不可信）。
#
# ⚠️ 口径（Leader 2026-10-13 定，务必遵守）：
#   本门给出的是「**这次裁决可不可信**」，**不是**「门本身过不过」。
#   · 任何一次**绿**，**只有在报告了「跑中树未变」（至少世界层未变）的前提下才可采信**；
#   · 报「**结果不可信**」(exit 2) 时 **既不得当失败、也不得当通过** —— 请重跑。
#   （因此 exit 2 ≠ "门挂了"；它是"结论作废、需重跑"。）
#
# 测试钩子：`VERIFY_INNER_CMD` 可覆盖内部真门（默认 `make verify-inner`）—— 供反向验证用假门，勿在生产改。
set -uo pipefail
REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "no-git"; exit 2; }
cd "$REPO" || exit 2
FP="$REPO/tools/tree_fingerprint.sh"
INNER="${VERIFY_INNER_CMD:-make verify-inner}"

# 诊断用清单（按段列 tracked 改动名 + untracked 文件名；仅用于输出，不参与裁决）
LIST_WORLD() { { git diff --name-status HEAD -- code config 2>/dev/null | grep -v '^\S*\s*code/frontend/'; echo "UNTRACKED(world):"; git ls-files --others --exclude-standard -- code config 2>/dev/null | grep -v '^code/frontend/'; } }
LIST_FRONT() { { git diff --name-status HEAD -- code/frontend 2>/dev/null; echo "UNTRACKED(front):"; git ls-files --others --exclude-standard -- code/frontend 2>/dev/null; } }

SW="$(mktemp)"; EW="$(mktemp)"; SF="$(mktemp)"; EF="$(mktemp)"
trap 'rm -f "$SW" "$EW" "$SF" "$EF"' EXIT

LIST_WORLD > "$SW"; LIST_FRONT > "$SF"
F0W="$(bash "$FP" world)"; F0F="$(bash "$FP" front)"
HEAD0="$(git rev-parse HEAD 2>/dev/null)"
echo "[verify-guard] 起跑指纹 世界层=$F0W 前端=$F0F （HEAD=$HEAD0，仅记录）"

eval "$INNER"; rc=$?

F1W="$(bash "$FP" world)"; F1F="$(bash "$FP" front)"
HEAD1="$(git rev-parse HEAD 2>/dev/null)"
LIST_WORLD > "$EW"; LIST_FRONT > "$EF"
echo "[verify-guard] 收尾指纹 世界层=$F1W 前端=$F1F （HEAD=$HEAD1，仅记录）"

if [ "$F0W" != "$F1W" ]; then
  echo "[verify-guard] ✗ 世界层跑中被改（config/** 或世界层 code/**）⇒ 本次门结果【不可信】，请重跑。"
  echo "[verify-guard]   世界层变更清单（起→收）："
  diff "$SW" "$EW" | sed 's/^/     /' || true
  echo "[verify-guard]   （这是『验证窗内冻结被验对象』的机器自检：与 T304/T314 同一原理。）"
  exit 2
fi

if [ "$F0F" != "$F1F" ]; then
  echo "[verify-guard] ⚠ 仅 code/frontend/** 跑中被改 ⇒ 降级为【告警】：前端 CI 部分不可信；**世界层结论仍可信**。"
  echo "[verify-guard]   前端变更清单（起→收）："
  diff "$SF" "$EF" | sed 's/^/     /' || true
  echo "[verify-guard] OK(world)：世界层跑中未变 ⇒ 世界层结论可信（rc=$rc，随门）。"
  exit "$rc"
fi

echo "[verify-guard] OK：世界层与前端跑中均未变，门结果可信。"
exit "$rc"
