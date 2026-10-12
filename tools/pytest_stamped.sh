#!/usr/bin/env bash
# pytest_stamped.sh — 带环境戳的 pytest 入口（T220 追加）。
#
# 为什么：一个长期存在的红会训练人忽略门禁；比"红"更糟的是"红的来源不明"。
# 本入口先打环境戳（git 状态 + 磁盘/inode + 最近改动模块），再跑 pytest，
# 使"在飞改动导致的红"自我标注来源（把"猜"变成"读"）。
#
# 用法：bash tools/pytest_stamped.sh [pytest 参数...]
#   例：bash tools/pytest_stamped.sh -q code/tests
# 说明：这是「根 pytest 入口」的推荐包法；直接运行 `pytest` 不会带戳。
set -uo pipefail
_here="$(cd "$(dirname "$0")" && pwd)"
bash "$_here/git_stamp.sh" || true   # 戳只打印，不阻断（放行由返回值决定）
exec python3 -m pytest "$@"
