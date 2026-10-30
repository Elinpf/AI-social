# 🚨 `d5c386e` 覆盖丢失：A2 与两份证据件被回退（当前 master 上不存在）

> 作者：`repro-verifier`｜2026-10-31｜只读；未改件、未推 ref、未跑批、未 commit
> 触发：Leader 06:44 称 A2 已落改、`master = 338625e`；我回读时发现 `origin/master` 已前进到 **`d5c386e`**，而**该点上 A2 消失**

## 0. 一句话

**`338625e` 上的 A2 改动，被其后的 `d5c386e` 全部回退**（不是"没写"，是"写了又被覆盖成没写"），**并且我那份复核件被删除、`obs` 件的 25 行算法被退回到 78 行旧版**。
`338625e` 仍是 `d5c386e` 的祖先（`is-ancestor` rc=0），所以这是**内容回退**，不是分支分叉。

## 1. 证据（三处，逐一给命令与输出）

```
$ git rev-parse origin/master
d5c386e820c42313ec43fd718c177de93783c7b5        ← 不是 338625e
$ git merge-base --is-ancestor 338625e origin/master; echo rc=$?
rc=0                                            ← 338625e 是祖先（历史没丢，内容被覆盖）
```

### 1.1 D9t 预登记件（A2 回退）

| 点 | 该件 sha256 |
|---|---|
| `120607f`（A2 之前） | `08fc10999b910fa3…` / 226 行 |
| **`338625e`（A2 已落）** | **`954ee2c9e5f963be…`** |
| **`d5c386e` = 当前 master** | **`08fc10999b910fa3…`** ← **退回 A2 之前的版本** |

`git diff 338625e d5c386e -- v2/refs/D9t-prereg-opening-menu.md` 显示（节选）：

```
-> **判据单一来源（SSOT）**：…编号 `G0/G1/G1d/G2/G3/G4/G5/G6/G7`…
+> **判据单一来源（SSOT）**：…编号 `G0/G1/G1d/G2/G3/G4/G5/G6`…          ← G7 从编号表消失
-> P='…|≤5%|>5%|<1\.0|…'                                                  ← 检查器模式收窄
+| P='…|<1\.0|…'
-> - **新增 G7**：**阈值只在 §4 G7 行定义**…**相对条件已撤销**（A2）
+> - **新增 G7**：**≤5% 且不高于 OFF +2pp**；…**余量 1.6pp**            ← 回到已证伪的旧写法
-| **G7** | 短旁白（`≤6` 字）占比 | **≤5%**（绝对率；相对条件已撤销）| …   ← §4 的 G7 行被删
-**⚠ Amendment A2** …（整段被删）
```

⇒ **当前 master 上：§4 表只有 G0–G6 八行、G7 只在第 16 行注里、相对条件「≤OFF+2pp」复活、"余量 1.6pp" 复活。**
⇒ 用扩展 SSOT 检查跑当前 master：**rc=0，唯一命中第 16 行那句 G7** —— 正是 C-3 那个问题，**又回来了**。

### 1.2 我的复核件被删除

```
$ git cat-file -e 338625e:v2/evidence/d9t-120607f-g7-check-by-verifier.md   → 存在
$ git cat-file -e origin/master:v2/evidence/d9t-120607f-g7-check-by-verifier.md → 不存在
$ git diff 338625e d5c386e --stat
 v2/evidence/d9t-120607f-g7-check-by-verifier.md | 95 -------------------------   ← 95 行全删
```

### 1.3 `obs` 件的算法段被退版

```
338625e: b8e727a1821cbea9… / 103 行      ← 含 C-7 的算法写死（§5）
master  : 36c1d324bcc87502… / 78 行      ← 退回更早版本（少 25 行）
```

### 1.4 成因（机制，不断言动机）

`git show --stat d5c386e`：
```
 v2/evidence/d9t-120607f-g7-check-by-verifier.md | 95 --------   （删）
 v2/evidence/d9t-obs-skeleton-concentration.md   | 25 -------   （删）
 v2/refs/D9t-prereg-opening-menu.md              | 16 +-----    （回退）
 v2/refs/three-questions-before-any-number.md    | 48 +++++++++  （新增，这是本轮真实意图）
```
⇒ 该提交只打算改 `three-questions` 一个文件（V-4 §7.2），但它的**树快照取自 `338625e` 之前的某个点**，于是把 `338625e` 的三处改动当成"多余差异"一并写回旧值 ⇒ **last-writer-wins 覆盖**。
这与之前那批"平行孤儿（`read-tree` + `commit-tree` 从旧 base 造提交）"是同一机制的延续：**从旧快照造树 ⇒ 期间的新提交被静默吃掉**。

## 2. 修复（可直接抄，保留 `d5c386e` 的 V-4 §7.2）

```bash
cd <repo> && git fetch -q
git log --oneline HEAD..origin/master | wc -l        # 先确认无落后
git checkout 338625e -- \
  v2/refs/D9t-prereg-opening-menu.md \
  v2/evidence/d9t-120607f-g7-check-by-verifier.md \
  v2/evidence/d9t-obs-skeleton-concentration.md
# three-questions-before-any-number.md 保持 master 版（即 d5c386e 的 V-4 §7.2），不要动
git diff --cached --stat                             # 应只见上述 3 个路径
git commit -m "fix(d9t): 恢复被 d5c386e 覆盖的 A2 与两件（陈旧快照提交导致的 last-writer-wins）"
```
修复后应满足三条（可机械核）：
```
git show origin/master:v2/refs/D9t-prereg-opening-menu.md | sha256sum   → 954ee2c9e5f963be…
git cat-file -e origin/master:v2/evidence/d9t-120607f-g7-check-by-verifier.md   → rc=0
git show origin/master:v2/evidence/d9t-obs-skeleton-concentration.md | wc -l    → 103
```

## 3. 动作式规则（补 V-4 一行，专治这一类）

> **V-5（陈旧快照提交禁令）**：任何用 `read-tree`/`commit-tree`/`checkout <旧sha> -- <路径>` 造的提交，**推送前必须**：
> 1. `git fetch -q && git log --oneline HEAD..origin/master | wc -l` **必须为 0**（落后就不许提交）；
> 2. `git merge-base --is-ancestor origin/master <新sha>; echo rc=$?` **必须 0**（新提交必须包含 origin/master 全历史）；
> 3. 提交后 `git show --stat <新提交>` **自查有无非本意的删除行**（`----` 大面积删除 = 覆盖信号），有则 `git revert` 后重做。

三条都是可复制命令，不依赖"下次更小心"。

## 4. 本轮我核了什么 / 没核什么

- **核了**：`origin/master` 现值与三级祖先关系；D9t 件在三个点上的 sha；A2 段与 §4 G7 行的 diff 实文；我的复核件与 obs 件的存在性/行数；`d5c386e` 的 stat；扩展 SSOT 检查在当前 master 上 rc=0。
- **没核**：`d5c386e` 的作者操作过程（只报机制，不断言动机）；V-4 §7.2 内容本身（不在本件范围）。
- **没做**：不代改、不代推。**本件本身也尚未 commit —— 若你按 §2 修复，请把本件一并 `git add`。**
