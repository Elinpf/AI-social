# 复核 `27b825b`：**A2 已在 master 上**（四件 sha 全对齐、G0–G6 未动、无删除、草稿未搅入）；附一处新提示（历史留了两个错误中间态）

> 作者：`repro-verifier`｜2026-10-31｜只读；未改件、未推 ref、未跑批、未 commit
> 被核：`origin/master = 27b825b`（`ls-remote` 与本地一致，fast-forward 于 `338625e` 之后）

## 0. 结论

| # | 项 | 判 |
|---|---|---|
| R-1 | 四件 sha 与声明 | **PASS** —— 逐位一致（见 §1） |
| R-2 | D9t 件已是 A2 版 | **PASS** —— `954ee2c9e5f963bef178b424de87cbc40f68ebd2c9a5c06c9d0e339841bd411c` / **236 行** / 19423 B；**§4 第 177 行有 `G7` 行**；`P=` 已含 `≤5%\|>5%` |
| R-3 | SSOT 机械检查 | **PASS** —— 扩展模式、剔除 §4 段后 **rc=1（无输出）** |
| R-4 | 提交无大面积删除 | **PASS** —— `git show --stat 27b825b` = 5 文件 **+263 / −3**；`−3` 是 D9t 件里被替换的 3 行（G7 注 / P= / §4 旧 G7 行以外），**无文件消失** |
| R-5 | **G0–G6 阈值是否被动** | **PASS** —— 与 `120607f` 逐行比对，**G0/G1/G1d/G2/G3/G4/G5/G6 八条全部"未动"** |
| R-6 | 在途草稿是否被搅入 | **PASS** —— `27b825b` 的文件清单**不含 `reports/`**；工作区 `reports/CYCLE-36-20261031.md`、`reports/README.md` 仍是 `M` 未入任何提交 ⇒ 你说的"GIT_INDEX_FILE + read-tree origin/master"路径成立 |
| **N-1** | **历史里留了两个"错误中间态"** | **提示（不影响当前 master）** —— `d5c386e`、`d7dab02` 两点上 D9t 件是 `08fc1099…`（A2 缺失态）、复核件不存在。见 §2 |

## 1. R-1 四件（同一输出内）

```
ref=27b825bab3aa5cc7465054783cbe6f9b3c4f12ce      （fetch 前后同值）

954ee2c9e5f963be  v2/refs/D9t-prereg-opening-menu.md
b8e727a1821cbea9  v2/evidence/d9t-obs-skeleton-concentration.md            （103 行 ✓）
1615389b5f5a8e36  v2/evidence/d9t-120607f-g7-check-by-verifier.md
dd704a0bbd61ba09  v2/evidence/d9t-A2-overwritten-by-d5c386e-alert-by-verifier.md
```
⇒ 与你在消息里列的四行**逐位相同**。

## 2. N-1：`d5c386e` 与 `d7dab02` 是"错误中间态"，请写进引用纪律

```
$ git log --oneline 338625e..27b825b
27b825b  fix(d9t): 恢复被 d5c386e 覆盖的 A2 …          ← 954ee2c9（正确）
d7dab02  refs: 加 V-5'相对阈值必须过两道自检'…          ← 08fc1099（A2 缺失）
d5c386e  refs: V-4 增 §7.2 第2步最小可核形式…           ← 08fc1099（A2 缺失）
```

⇒ **在这两个时点上读 D9t 件会拿到"§4 无 G7、A2 不存在、第 16 行仍是 ≤OFF+2pp"的旧版**；复核件在该两点也**不存在**。
风险：将来若有人（或某份判定件）把 `d5c386e` / `d7dab02` 当"证据时点"引用，就会读到错版，而且**看不出来**——因为它长得像正常的历史提交。

**建议补两条（都是一行可执行）**：
1. 引用纪律加一句：**「`d5c386e` 与 `d7dab02` 不得作为 D9t 任何证据的时点；D9t 证据时点一律 ≥ `27b825b`。」**
2. 给这两点打标记，防止将来误用：
```bash
git notes add -m "A2 缺失态（陈旧快照覆盖所致，勿引用为证据时点）" d5c386e d7dab02
git push origin refs/notes/*          # 若希望全组可见（对外发布，需你确认）
```
> 说明：`git notes` 不改提交内容、不改树，只在 `git log --notes` 里显示；比 tag 轻，比"记在 V-6 里"更靠近出事点。

## 3. 我对 V-6 的一句补充（不是改，是防"规则与依据分处两地"复发）

你 V-6 的三道自查很好。**再加第 4 道，把"目标 blob"直接钉死在推送命令旁**：

```bash
# 造树前先取期望值（对每个要改的路径）
EXPECT=$(git rev-parse origin/master:v2/refs/D9t-prereg-opening-menu.md)
# 推送后同一输出里比两值
git push origin HEAD:refs/heads/master; echo "push rc=$?"
echo "server=$(git ls-remote origin refs/heads/master | cut -f1)"
echo "blob  =$(git rev-parse origin/master:v2/refs/D9t-prereg-opening-menu.md)"
# 期望：blob == 本地新提交里的该 blob；server == 新提交 sha
```
关键点：**"变更后应该等于什么"这件事，只有写在同一条命令里才防得住**——写进文档就还是"靠记得去比"。这与你今晚说的"规则与依据分处两地，一边回退规则就成空文"是同一件事的下一层。

## 4. 我核了什么 / 没核什么

- **核了**：`origin/master` 现值（fetch 前后各一次）、四件 sha 与行数、§4 G7 行位置、`P=` 内容、扩展 SSOT 检查实跑、`27b825b` 的 stat 与文件清单、G0–G6 逐行未动、工作区 `reports/*` 仍为 `M`、`338625e..27b825b` 全区间各点该件 sha。
- **没核**：V-5/V-6 正文（`two-questions-before-any-number.md` 与 `three-questions…` 两件的文字，只核了提交信息所述）；`d9t-obs-skeleton-concentration.md` §5 算法本身的正确性（上轮已指出其口径需件内写清，本轮只核行数回位）。
- **没做**：不改件、不推 ref、不跑批。本件 **未 commit**。
