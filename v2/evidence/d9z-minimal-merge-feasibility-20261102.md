# `feat/d9z-minimal` → `master` 合并可行性实测（只读，未合并、未跑批）

- 时间：2026-11-02 09:4x
- 方法：`git merge-tree --write-tree`（**不写工作区、不动分支、不动 index**）
- **三元组（§20 + 临时树不稳定规则）**：
  `merge-tree(master@93d532e, feat/d9z-minimal@6a7cc6d) = 529b83cd`（临时树·非当前版，无 ref 指向）
  ⚠ **该临时 sha 绑定 `master = 93d532e` 那一刻**；master 一前进即变，引用必须带 master 的 sha。

## 1. 结论：机械可行，零冲突

| 项 | 实测 |
|---|---|
| 冲突数 | **0** |
| `code/` 内文件删除 | **0** |
| 合并后 `code/` 变动 | **5 files, +238 / −8** |
| 涉及文件 | `engine/kernel.py` `engine/perceive.py` `orchestration/integration.py` `orchestration/visibility_index.py` `tests/test_intra_round_visibility.py` |

⇒ **"合并会炸"不成立**；且与 `feat/rift-minimal` 那次不同（那次有 1 处数据文件 add/add 冲突），**这次一处冲突都没有**。

## 2. 与 `feat/rift-minimal` 的差别（为什么这次更干净）

- `feat/rift-minimal` 的 base 是 `3610815`，之后 master 前进过（文档件），且它带 `config/dialogue_repair.json` 改动 ⇒ 与证据目录的 `launch_cmd.txt` 撞。
- `feat/d9z-minimal` 的 base 是 `619e9ae`，**只改 `code/` 5 文件、无 `config/`、无证据目录改动** ⇒ 与 master 的文档提交无交集。

## 3. 边界（不主张合并安全）

- 合并**未执行**；本件只报机械可行性；
- **行为等价性已由 V1/V2 + V2b + V3 支撑，但那是「默认全关」的等价**，不等于"合并后 master 行为不变"——因为 master 上**从未有过 D9z 代码**（`HITT_INTRA_ROUND_VISIBILITY` 0 命中），合并是**首次带入**，默认关的等价性正是 V1≡V2 所证的内容；
- **`merge-tree` 的临时 sha 不稳定**（见 §0 三元组），不作稳定标识。

## 4. 复算命令

```bash
git merge-tree --write-tree --name-only origin/master origin/feat/d9z-minimal   # 期望：只有 tree sha 一行，无 CONFLICT
git diff --diff-filter=D --name-only origin/master <merge-tree> -- code/        # 期望：空
git diff --stat origin/master origin/feat/d9z-minimal -- code/                  # 5 files +238/-8
```

## 率的定义

**本件不新增任何率**（可行性实测，无分子分母）。

| 率名 | 分子 | 分母 | 计算式（含边界） | 纳入排除 |
|---|---|---|---|---|
| 无（只报冲突数与增删行数） | 不适用 | 不适用 | 不适用 | 不适用 |

## 外推与假定

**本件不外推**。所有读数为 `git merge-tree` / `git diff --stat` 直接输出。

| 外推式 | 假定不变的量 | 值来源 |
|---|---|---|
| 无（只报实测） | 不适用 | 不适用 |
