#!/usr/bin/env bash
# T313 反向验证：`safe_rmrf` —— 负向必须【拒绝且不删】；正向必须【允许并删】。
set -uo pipefail
BIN="$(cd "$(dirname "$0")" && pwd)"; source "$BIN/safe_rmrf.sh"
PASS=1
reject(){ local d="$1"; if safe_rmrf "$d" >/dev/null 2>&1; then echo "  FAIL: 应拒绝却执行了: '$d'"; PASS=0; else echo "  ok: 拒绝 '$d'"; fi; }
allow(){ local d="$1"; mkdir -p "$d"; echo s > "$d/SENTINEL"; if safe_rmrf "$d" >/dev/null 2>&1 && [ ! -e "$d" ]; then echo "  ok: 允许并删除 '$d'"; else echo "  FAIL: 正常路径被拒/未删: '$d'"; PASS=0; fi; }

echo "### 负向（必须拒绝，报错退出，不执行 rm）"
reject ""                            # 空/未设
reject "/"                           # 根
reject "/root"                       # '/' 的直接子目录
reject "/etc"                        # '/' 的直接子目录
reject "/root/t271"                  # 允许根本身（不许清整树）
reject "/root/outside_x"             # 树外
reject "/tmp/not_t271_dir"           # /tmp 下非 t271 拥有
reject "/root/t271/../etc"           # `..` 穿越（realpath 解析后=/etc）

echo "### 正向（必须允许并删）"
allow "/root/t271/runs/_rmrf_ok"     # /root/t271 树内
allow "/tmp/t271-_rmrf_ok"           # /tmp 下 t271*（副本目录形态）

echo
[ "$PASS" = "1" ] && echo "############ SAFE_RMRF VERIFY: PASS ############" || echo "############ SAFE_RMRF VERIFY: FAIL ############"
exit $((1-PASS))
