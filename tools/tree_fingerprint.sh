#!/usr/bin/env bash
# T340：工作树「冻结区」指纹 —— 判「跑中树是否被改」。
# 范围（有意收窄以防生成物噪声）：`code/**` + `config/**`
#   · HEAD sha（捕并发提交）
#   · `git diff HEAD -- code config`（已跟踪文件的改动：暂存+未暂存）
#   · `code/config` 下的**未跟踪**（非忽略）文件清单 + 内容哈希（捕新增源/config）
# 注意：gitignore 的生成物（reports/、__pycache__、*.jsonl、截图等）**不计入** ⇒ 避免假红。
set -uo pipefail
REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "no-git"; exit 0; }
cd "$REPO" || exit 0
{
  git rev-parse HEAD
  git diff --no-color HEAD -- code config 2>/dev/null
  git ls-files --others --exclude-standard -- code/config 2>/dev/null
  while IFS= read -r f; do
    [ -f "$f" ] && sha256sum "$f" 2>/dev/null
  done < <(git ls-files --others --exclude-standard -- code/config 2>/dev/null)
} | sha256sum | awk '{print $1}'
