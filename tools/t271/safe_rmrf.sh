#!/usr/bin/env bash
# T313 · 统一防御守卫：`safe_rmrf <path>` —— 只删【t271 拥有】的目录，拦住今晚的"范围过宽"形态。
#
# 拒绝（报错退出、不删）：
#   · 参数为空 / 未设
#   · 解析后为 `/`（根）
#   · `/` 的直接子目录（如 /root、/tmp、/etc）
#   · 不在【允许根】之下；或等于允许根本身；或（/tmp 下）basename 不以 `t271` 开头
# 允许根（可用 T271_SAFE_ROOTS 覆盖，冒号分隔）：默认 `/root/t271:/tmp`
#   —— /root/t271 树内任意子目录；/tmp 下仅 `t271*`（副本目录，见 make_batch_copy）。
# 依赖：realpath（coreutils）；缺失时退回字面路径（仍做前缀检查，但注意 `..` 未解析）。
set -u
SAFE_RMRF_ROOTS="${T271_SAFE_ROOTS:-/root/t271:/tmp}"

safe_rmrf() {
  local raw="${1:-}" p base parent root _roots ok=0
  if [ -z "$raw" ]; then
    echo "[safe_rmrf] 拒绝：路径为空/未设（不执行 rm）" >&2; return 2
  fi
  if command -v realpath >/dev/null 2>&1; then
    p="$(realpath -m -- "$raw" 2>/dev/null || printf '%s' "$raw")"
  else
    p="$raw"
  fi
  p="${p%/}"; [ -n "$p" ] || p="/"
  if [ "$p" = "/" ]; then
    echo "[safe_rmrf] 拒绝：'/'(根)（不执行 rm）" >&2; return 2
  fi
  parent="$(dirname "$p")"
  if [ "$parent" = "/" ]; then
    echo "[safe_rmrf] 拒绝：'/' 的直接子目录 '$p'（不执行 rm）" >&2; return 2
  fi
  base="$(basename "$p")"
  IFS=':' read -ra _roots <<< "$SAFE_RMRF_ROOTS"
  for root in "${_roots[@]}"; do
    root="${root%/}"; [ -n "$root" ] || continue
    [ "$p" = "$root" ] && continue                 # 不许删允许根本身
    case "$p" in
      "$root"/*)
        if [ "$root" = "/tmp" ]; then
          case "$base" in t271*) ok=1 ;; esac       # /tmp 下仅 t271 拥有的
        else
          ok=1
        fi ;;
    esac
  done
  if [ "$ok" != "1" ]; then
    echo "[safe_rmrf] 拒绝：不在允许根($SAFE_RMRF_ROOTS)内或非 t271 拥有 '$p'（不执行 rm）" >&2; return 2
  fi
  rm -rf -- "$p"
}
