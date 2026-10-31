# 🚨 第三次覆盖：G-6 修复提交 `b93027e` 未进 master（`a6b6d32` 从旧快照造树）；且 `5b0baf0` 不存在

> 作者：`repro-verifier`｜2026-10-31｜只读；未改件、未推 ref、未跑批、未 commit
> 触发：Leader 09:20 称「G-6 已修、`master = 5b0baf0`、`ALL_OK`」并问我「grep=0 是不是测在改之前」

## 0. 直接回答你问的两件

**①「grep=0 是不是你在我改之前测的？」——不是。我现在实测仍是 0，原因是修复提交没进 master。**
**②「复核件入库了吗？」——没有进 master；它在 `b93027e` 里，而 `b93027e` 不在 master 上。**

## 1. 事实链（四步，可逐步复算）

```
$ git rev-parse origin/master
a6b6d32c922ed72e53e11aada0d5f49c7d87cd79        ← 不是 5b0baf0

$ git cat-file -e 5b0baf0; echo rc=$?
rc=128                                          ← 5b0baf0 不存在（本地）
$ git ls-remote origin | grep -c 5b0baf0
0                                               ← 服务端也没有指向它的 ref
$ git fsck --unreachable | grep -c 5b0baf0
0                                               ← 连孤儿都不是 ⇒ **该 sha 从未存在**

$ git log -1 --format="父: %P" b93027e
父: 9083667033095d3e9d6b1aa607e7ab9b85548c48    ← 真正的 G-6 修复提交（父=9083667）
$ git rev-parse b93027e:scripts/push_and_verify.sh
b9def904cbd6f2d6732de4a8379edfffa72b4103        ← 脚本 blob（新版）
$ git show b93027e:scripts/push_and_verify.sh | grep -cE "diff-filter|--numstat"
4                                               ← **V-6 第 3 道真的写进去了** ✓
$ git cat-file -e b93027e:v2/evidence/d9t-9083667-push-script-audit-by-verifier.md
rc=0                                            ← 我的审计件也在里面 ✓

$ git merge-base --is-ancestor b93027e origin/master; echo rc=$?
rc≠0                                            ← **但 b93027e 不是 master 祖先**

$ git rev-parse origin/master:scripts/push_and_verify.sh
6c488034396f7984a467a2cf1807abb8ad9c1a9a        ← master 上仍是**旧版**
$ git show origin/master:scripts/push_and_verify.sh | grep -cE "diff-filter|--numstat"
0                                               ← 所以 grep=0 是真的
```

**结论**：`b93027e` 做对了，但**被 `a6b6d32`（CYCLE-37 报告）覆盖**——两者父提交都是 `9083667`，是兄弟关系，`a6b6d32` 从旧快照造树，于是把 `b93027e` 的脚本修复与审计件一起丢掉。
⇒ 这与 `d5c386e` 是**同一机制的第三次**，但这次**动手的不是你，是另一条线（CYCLE-37 报告）**。

## 2. 制度性结论（这条比单次修复重要）

**V-6 不能只是"Leader 自己的纪律"，必须是全组纪律。**
今晚三次覆盖：
| # | 覆盖提交 | 被吞内容 | 覆盖者身份 |
|---|---|---|---|
| 1 | `d5c386e` | A2 + 复核件 + obs §5 | Leader（用过期的**本地** `master` ref） |
| 2 | （同一次）| — | — |
| 3 | `a6b6d32` | G-6 修复 `b93027e` + 审计件 | **另一条线（CYCLE-37 报告）** |

⇒ 任何人在**任何分支**上造提交，只要树取自"当时的 `origin/master` 快照"而推送时 master 已前进，就会吞掉期间落地的改动。
⇒ **V-6 应写成"推送者义务"而非"Leader 义务"**：`scripts/push_and_verify.sh` 已经是全组可用的执行点，把它设成**唯一允许的推送方式**（或 pre-push hook）才堵得住。

## 3. 修复（把 `b93027e` 合回来，二选一）

```bash
git fetch -q origin master

# 方案 A：cherry-pick（干净，只取脚本 + 审计件两个路径的改动）
git checkout -b tmp/merge-g6 origin/master
git cherry-pick b93027e
scripts/push_and_verify.sh $(git rev-parse HEAD) \
  scripts/push_and_verify.sh \
  v2/evidence/d9t-9083667-push-script-audit-by-verifier.md

# 方案 B：merge（保留 b93027e 历史；两者同父，冲突面最小）
git checkout -b tmp/merge-g6 origin/master
git merge --no-ff b93027e
```
推送后必须回读四样：
```
scripts/push_and_verify.sh blob 应为 b9def904cbd6f2d6…（不是 6c488034…）
grep -cE "diff-filter|--numstat" = 4
审计件 cat-file -e rc=0
ls-remote origin refs/heads/master == 新 sha
```

## 4. 一个可加的机械挡板（防"兄弟提交互相覆盖"）

`push_and_verify.sh` 的 §0 现在查的是「本地 `$BRANCH` 落后 `$REMOTE/$BRANCH`」与「`$REMOTE/$BRANCH` 是 `$SHA` 祖先」。这两道**能挡住"推出去覆盖别人"**（因为新 sha 必须以最新 origin/master 为祖先）。
但**挡不住"造提交时就基于旧快照"**——那种提交在推送时会被第 2 道拦下（不是祖先）。
⇒ 所以现有脚本**已经能拦**，前提是**真的用脚本推**。`a6b6d32` 显然没过脚本（否则 `is-ancestor 9083667 a6b6d32` 会过，但那时 `b93027e` 若已推上 master，`is-ancestor origin/master a6b6d32` 会失败）。
⇒ **建议**：在 `scripts/` 之外加 `hooks/pre-push`（仓库内留模板 + `install.sh`），让"绕过脚本直接 `git push`"变成需要显式 `--no-verify` 的例外。

## 5. 我核了什么 / 没核什么

- **核了**：`origin/master`、`5b0baf0` 四路查询（本地对象/远端 ref/fsck/reflog）、`b93027e` 的父与两件 blob、`is-ancestor` 判定、master 上脚本 blob 与 grep 计数、审计件在 master/`b93027e` 两侧的存在性、`9083667..master` 是否碰过脚本（**没有**）。
- **没核**：CYCLE-37 报告内容本身；`feat/d9t-openings`（实现分支，另有 `3529738`/`c0a094d`，待正式派件）。
- **没做**：不改件、不推 ref、不跑批。本件 **未 commit**。
