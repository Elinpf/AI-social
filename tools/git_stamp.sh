#!/usr/bin/env bash
# git_stamp.sh — 门禁/测试结论的「环境打戳」（T220 三 + T220 追加：磁盘余量）。
#
# 理由：
#   - 并行编辑同一工作树时，任何测试都在读一个「正在移动的靶子」——并发期的门禁结果不可信。
#   - 磁盘/ inode 满会**伪装成代码坏**（"偶发红→复跑→绿"会把伪装一直盖住）——故余量必须进戳。
# 纪律「证据绑版本」：一条不标环境的结论 = 一条没有来源的数字。
#
# 输出：
#   sha: <short HEAD>
#   dirty_files: <N>
#   disk: avail_bytes=<B> avail_inode=<N> use=<PCT>%   （仓库所在文件系统）
#   状态: [CLEAN]  或  [DIRTY — 结论仅供参考]
#   磁盘: [DISK OK] 或  [DISK LOW — 结论仅供参考]
#
# 阈值（可被环境变量覆盖，便于反向验证/调参）：
#   DISK_MIN_AVAIL_BYTES   默认 1073741824（1 GiB）
#   DISK_MIN_INODE_AVAIL   默认 100000
#
# 退出码：默认 0。GIT_STAMP_STRICT=1 时：DIRTY 或 DISK LOW → 退出码 1
#   （发版类入口用 strict；只检查类入口非 strict，脏/满时继续但标注「仅供参考」）。
set -uo pipefail

_gs_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
# 仓库所在文件系统（无 git 时退化为当前目录）
_gs_fs="${_gs_root:-$(pwd)}"

# ---- git 状态 ----
if [ -z "${_gs_root:-}" ]; then
  _gs_sha="<no-git>"; _gs_dirty="n/a"
else
  _gs_sha="$(git -C "$_gs_root" rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
  _gs_dirty="$(git -C "$_gs_root" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
fi

# ---- 脏文件的「最近改动模块」（按 mtime 降序，映射到模块目录，去重取前 3）----
# 目的：把「红」与「谁在改什么」对上——[DIRTY] 只说树脏，不代表红就是这个脏来的。
_gs_recent=""
if [ -n "${_gs_root:-}" ] && [ "${_gs_dirty:-0}" != "0" ]; then
  _gs_recent="$(git -C "$_gs_root" status --porcelain 2>/dev/null | awk '{print $NF}' \
    | while IFS= read -r _f; do
        # 全新未跟踪目录在 porcelain 里是 `dir/`：去尾斜杠后再 find，避免 dirname 少一层
        [ -e "$_gs_root/${_f%/}" ] && find "$_gs_root/${_f%/}" -maxdepth 0 -printf '%T@ %p\n' 2>/dev/null
      done \
    | sort -rn \
    | awk '{print $2}' \
    | while IFS= read -r _p; do
        _rel="${_p#"$_gs_root"/}"; _rel="${_rel%/}"
        # 若该条目本身是目录（如新模块），模块即它本身；否则取 dirname
        if [ -d "$_gs_root/$_rel" ]; then _d="$_rel"; else _d="$(dirname "$_rel")"; fi
        case "$_d" in code/*) _d="code/$(printf '%s' "$_d" | cut -d/ -f2)";; esac
        [ "$_d" = "." ] && _d="<root>"
        printf '%s\n' "$_d"
      done \
    | awk '!seen[$0]++' | head -3 | paste -sd' ' -)"
fi
[ -z "${_gs_recent:-}" ] && _gs_recent="<none>"

# ---- 磁盘余量（POSIX df）----
_disk_min_bytes="${DISK_MIN_AVAIL_BYTES:-1073741824}"
_disk_min_inode="${DISK_MIN_INODE_AVAIL:-100000}"
_avail_kb="$(df -Pk "$_gs_fs" 2>/dev/null | awk 'NR==2{print $4}')"
_use_pct="$(df -Pk "$_gs_fs" 2>/dev/null | awk 'NR==2{print $5}')"
_avail_inode="$(df -Pi "$_gs_fs" 2>/dev/null | awk 'NR==2{print $4}')"
_avail_kb="${_avail_kb:-0}"; _avail_inode="${_avail_inode:-0}"; _use_pct="${_use_pct:-?}"
_avail_bytes=$(( _avail_kb * 1024 ))

echo "sha: ${_gs_sha}"
echo "dirty_files: ${_gs_dirty}"
echo "未提交文件数: ${_gs_dirty}"
echo "最近改动的模块: ${_gs_recent}"
echo "disk: avail_bytes=${_avail_bytes} avail_inode=${_avail_inode} use=${_use_pct}"

# ---- 判定 ----
_rc=0
if [ "${_gs_dirty}" = "0" ]; then
  echo "状态: [CLEAN]"
else
  echo "状态: [DIRTY — 结论仅供参考]"
  _rc=1
fi

if [ "${_avail_bytes}" -lt "${_disk_min_bytes}" ] || [ "${_avail_inode}" -lt "${_disk_min_inode}" ]; then
  echo "磁盘: [DISK LOW — 结论仅供参考]"
  _rc=1
else
  echo "磁盘: [DISK OK]"
fi

if [ "${GIT_STAMP_STRICT:-0}" = "1" ] && [ "${_rc}" -ne 0 ]; then
  exit 1
fi
exit 0
