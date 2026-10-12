#!/bin/sh
# pre-commit 钩子 · 「本次提交范围」的三道检查：
#   阶段 0 提交范围守卫（T273）· 阶段 1 术语棘轮（T237）· 阶段 2 机器可读文件可解析（T242）
#   —— 都只扫 `git rev-parse` 得到的本次暂存集，对他人 WIP 免疫。
#
# 阶段 0（T273）新增：拦住 `git add -A` 裹带**他人未提交 WIP**。信号 = 同批暂存里
#   混有「新鲜改动」与「久未提交的陈旧文件」；默认拦截，`COMMIT_SCOPE_ACK=<令牌>` 确认放行。
#   机制见 tools/enforce_commit_scope.py（**不判定作者**——git 不记录作者；只识别新旧混批）。
#
# 病根（今天已两次致堵）：旧钩子跑 `make lexicon-gate` 是**全树**扫描，
#   会把**他人尚未提交的 WIP 违规**也扫进来，从而**阻断所有人的提交**
#   （e.g. econ-dev 被他人 WIP 拦、sim-engine-stats-architect 被 life-layer-dev 新文件拦）。
#   诱发的错误"解阻"是**代改他人文件** → 又制造归属/裹带问题。故**修根因**。
#
# 修复：只扫 `git diff --cached --name-only --diff-filter=ACM`（**本次提交范围**），
#   对共享索引/他人 WIP 免疫；**全树检查保留给 CI**（`make lexicon-gate`，未削弱）。
#
# 安装：make install-hooks
#   （等价于：cp tools/pre-commit-lexicon.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit）
# 绕过：git commit --no-verify（请先把违规修掉）。

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

# 本次提交涉及的文件（新增/修改/改名；不含删除）
CHANGED="$(git diff --cached --name-only --diff-filter=ACM)"
if [ -z "$CHANGED" ]; then
  exit 0    # 本次提交无文件 → 放行
fi

# ---- 阶段 0（T273）：提交范围守卫 —— 拦住 `git add -A` 裹带他人未提交 WIP ----
# 只读本次暂存集；不判定作者；信号=「新鲜文件」与「久未提交的陈旧文件」同批。
python3 tools/enforce_commit_scope.py
rc0=$?
if [ "$rc0" -ne 0 ]; then
  exit 1
fi

printf '%s\n' "$CHANGED" \
  | python3 glossary/tools/lint_terms.py --root . \
      --baseline glossary/term_baseline.json --paths-from-stdin \
      >/tmp/.lexicon_precommit.out 2>&1
rc=$?

if [ "$rc" -ne 0 ]; then
  echo "❌ pre-commit 拦截：本次提交的文件存在新增术语违规（仅检查本次提交范围）"
  echo "---- 可操作清单（行号 + 建议替换）----"
  grep -E "OFFER|新增违规|建议|probe|:[0-9]+:" /tmp/.lexicon_precommit.out | head -24
  echo "-------------------------------------"
  echo "修好后重试；确需绕过：git commit --no-verify"
  exit 1
fi

# ---- 阶段 2（T242）：机器可读文件「可解析」（仅本次提交范围）----
# json / jsonl / yaml / toml；大文件 >5MiB 跳过并打印 skipped(size)（可见，不静默）。
printf '%s\n' "$CHANGED" \
  | python3 tools/check_machine_readable.py --root . --paths-from-stdin
rc2=$?
if [ "$rc2" -ne 0 ]; then
  echo "❌ pre-commit 拦截：本次提交的机器可读文件无法解析（见上：文件名 + 错误位置）"
  echo "修好后重试；确需绕过：git commit --no-verify"
  exit 1
fi

exit 0
