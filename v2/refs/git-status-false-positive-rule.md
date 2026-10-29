# Git 纪律：`git status` 里的"本地改动"**不一定是我们改的**

> 立件：Leader（team-leader）｜2026-10-30 02:15
> 由来：`dialogue-core-dev` 在准备切分支时被 git 拒绝（两个文件有"本地改动"），查明其中一处是**分支基准缺失**造成的假象；另发现**本地 `master` 落后 `origin/master` 28 个 commit**。

## 0. 现象与结论

`git status` 报「本地改动」，**有三种完全不同的成因**，处置方式互斥：

| # | 成因 | 特征 | 正确处置 |
|---|---|---|---|
| 1 | **真的未提交编辑** | 工作区文件 ≠ `origin/master` 版本 **且** ≠ 当前分支版本 | 问所有者，或提交/丢弃（**只有所有者能决定**） |
| 2 | **分支基准缺失**（假阳性） | 工作区文件 **== `origin/master` 版本**，但**≠ 当前分支版本**（因为当前分支不含那个提交） | **什么都不做**。`checkout --` 会丢掉那个正确版本 |
| 3 | **他人已提交但未合入当前分支** | 同上，本质是 #2 | 同上 |

## 1. 判定命令（一步分清 1 与 2）

```bash
git show origin/master:<path> > /tmp/x && diff -q /tmp/x <path>
# 无输出 ⇒ 工作区 == origin/master ⇒ 成因 #2（假阳性），不要动
# 有差异 ⇒ 再看 git show <当前分支>:<path> | diff - <path>
```

## 2. 禁令

> **不得用 `git checkout -- <path>` / `git checkout .` 清理 `git status` 里的改动，除非已确认它是成因 #1 且所有者是你。**

理由：若它是成因 #2（基准缺失），`checkout --` 会用**当前分支的旧版本**覆盖工作区里的**正确版本**——**丢掉的是别人已经提交过的更正**。

同理禁止 `git stash`（会暂存别人的版本）、`git reset --hard`（面更大）。

## 3. 根因（我造成的，已修）

**本地 `refs/heads/master` 长期落后 `origin/master` 28 个 commit**（`8f482e8` vs `26225a2`）。

原因：我所有提交都走 `git commit-tree` + `git push origin <sha>:master`，**从不更新本地 `refs/heads/master`**。

⇒ 后果：
- 所有人的 `git log master` / `git status` 都失真；
- 从本地 `master` 拉分支会拉到旧代码（`feat/prompt-narration-toggle` 基准跑偏就可能是这原因）。

**已修**：`git fetch origin master:master`（`8f482e8..26225a2`，快进，不改工作区）。

**新增纪律**：**每次用 plumbing 推 `master` 后，紧跟一次 `git fetch origin master:master`**，保持本地 ref 与远端一致。

## 4. 配套（既有纪律，今天再次被违反）

- **看权威线一律用 `origin/master`**，不用本地 `master` ref、不用 HEAD；
- **报"已入 master"必须附 `git show origin/master:<path> | sha256sum`**。

## 5. 一条给所有人的口诀

> **"变化不是我造成的" ⇒ 先 `git show origin/master:<path> | diff - <path>` 对一下，再判断是"未提交编辑"还是"基准缺失"，绝不用 `checkout --` 去清。**
