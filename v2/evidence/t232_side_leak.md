# T232 · 临时 side 目录泄漏修复（含实测）

> 作者：kernel-dev ｜ sha：`c7d8edf` ｜ 真因位置：`orchestration/integration.py`（`run_e2e` 的 `mkdtemp("hitt_side_")`）

## 0. 事故
`/tmp/hitt_side_*` 实测 **3428 目录 / 1431 万文件** → 占全盘 9 成 inode（只剩 8650）→ 全队写入濒临失败。
**两个真因**：① `mkdtemp` **异常路径未清理**（`cleanup_side` 被跳过）；② **显式 `--side-root /tmp/...` 也被 `rmtree`**（canonical run「盘上无 side」）。

## 1. 交付（四件）
代码：`orchestration/integration.py` + `orchestration/cli.py`（新增 `sweep-side`）。
1. **异常/中断/SIGTERM 释放**：`managed_side_root()` contextmanager（`try/finally` + SIGTERM/SIGINT 兜底）；`run_e2e` 自动创建的 side 目录**无论如何**在 `finally` 释放（`_safe_rmtree`）。
2. **归属标记**：`make_side_root()` 在目录内写 `.owner`(pid) 与 `.started_at`(epoch) → 「谁的、多久了」可判。
3. **孤儿 sweeper**：`sweep_orphan_side_dirs(base, prefix, ttl, dry_run, warn)` —— **只清 owner pid 已死（或无标记）且年龄 ≥ ttl** 的目录；**活着的 run（pid 存活）绝不碰**；清理时打 **stderr 告警**（不静默）；`dry_run=True` 只报告不删。CLI：`python -m orchestration sweep-side [--base] [--ttl] [--dry-run]`。
4. **显式 `--side-root` 不被删**：`run_e2e` 仅删除**自动创建**的 side（`auto = side_root is None`）；显式传入的目录由调用方负责保留。

## 2. 验收实测（命令 + 输出）
- **异常路径释放**：`pytest tests/test_side_leak.py::test_managed_side_root_cleans_on_exception` → 在 `managed_side_root()` 内 `raise` → 断言目录**已不存在**（✅，非"看代码觉得会清"）。
- **显式指定不被删（反向验证）**：`test_explicit_side_root_is_preserved` → `run_e2e(..., side_root=<tmp>)` 跑完 → **目录仍在** ✅。
- **sweeper 实测**：`test_sweeper_removes_stale_orphan_keeps_live` → 造「陈旧 + 死 pid」目录 → **被清 + 告警**；造「本进程存活」目录 → **不动** ✅。`test_sweeper_no_marker_stale_is_removed` → 无标记陈旧目录 → 被清 ✅。
- **无遗留**：`test_run_e2e_leaves_no_new_side_dirs` → `run_e2e` 前/后 `/tmp/hitt_side_*` 集合，**无新增** ✅。
- **套件**：`pytest tests/test_side_leak.py -q` → **6 passed**。
- **真实 `/tmp` 巡检（dry-run，安全）**：`python -m orchestration sweep-side --ttl 600 --dry-run` → **would_remove=90，kept=209**（90 个可回收孤儿）。

## 3. 说明 / 未验证
- **未对真实 `/tmp` 真删**：避免误删**他人在跑、但目录无 `.owner` 标记的旧 run**（旧代码创建的目录无标记，仅凭 pid 无法判活）。建议在**无人跑批窗口**执行 `python -m orchestration sweep-side --ttl 600`（真删 + 告警）回收。
- 【未验证】`managed_side_root` 的**信号兜底仅在主线程注册**（非主线程忽略，仍由 `finally` 兜底）。
- **不动活着的 `.txt`**：sweeper 只删整目录且只针对死 pid/陈旧者；正常 run 的 `.txt` 正文不受影响（T228 数据资产安全）。

## 4. 门禁
`make lexicon-gate` exit=0；`lint-imports` 9 kept/0 broken；`pytest` 全量绿（life `test_t127_judgment_dims` 偶发红、**单跑 PASS**，非本改动）。
