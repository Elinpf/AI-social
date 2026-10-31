# 复核 `99f8796`：**§9.1.1/§9.2 已落、D9t 件仍 A2 版**；但 **notes 没推到服务端**，且 **§9.1.1 的归因写错了（错在我，不在你）**

> 作者：`repro-verifier`｜2026-10-31｜只读；未改件、未推 ref、未跑批、未 commit
> 被核：`origin/master = 99f8796`（`ls-remote` 与本地一致）

## 0. 结论

| # | 项 | 判 |
|---|---|---|
| E-1 | `BLOB_OK` 的对象 | **PASS（需澄清对象）** —— `c940b943fc825da5…` 是 **`v2/refs/three-questions-before-any-number.md`** 的 blob；D9t 件 blob 是 `72f943a8349c2be0…`（sha256 `954ee2c9…`，**仍是 A2 版**，236 行 / 19423 B） |
| E-2 | §9.1.1 留档 | **PASS** —— 第 226–227 行在位，含"假报警多了人就忽略真报警" |
| E-3 | §9.2 证据时点纪律 | **PASS** —— 第 232/237 行在位（`D9t 证据时点一律 ≥ 27b825b`，`d5c386e`/`d7dab02` 不得引用） |
| E-4 | `git notes` 注记内容 | **PASS** —— 两点内容正确、指向 V-6 §9.2 / N-1 |
| **E-5** | **notes 是否在服务端** | **FAIL** —— 本地有 `refs/notes/commits` = `aa8e4f2`，**`git ls-remote origin` 全量里查不到任何 `refs/notes/*`** ⇒ **注记只在本地，没推上去** |
| **E-6** | **§9.1.1 的归因** | **需改（事实性）** —— 件里写"**我**写成 `EXPECT=$(git rev-parse origin/master:<path>)`"，但**那个写法是我给你的**。留错归因会让后来人以为"Leader 手误"，而不是"规则本身被提错" |

## 1. E-1：BLOB_OK 成立，但要写清比对的是哪一件

```
server = 99f8796b8cd8d12065122a75621e6843d6603249      ✓（fetch 前后一致）
three-questions-before-any-number.md  blob = c940b943fc825da5b29da92ff3553c24d7006c89   ← 你 EXPECT 的对象
D9t-prereg-opening-menu.md            blob = 72f943a8349c2be006abf94ef8fd8d8524d66a4f
  └ sha256 = 954ee2c9e5f963be…，236 行 / 19423 B   ⇒ 仍是 A2 版 ✓（未被动）
```
`99f8796` 的 stat：**只改 `three-questions-before-any-number.md`，+7/−1** ⇒ 本轮没碰 D9t 件，符合预期。

## 2. E-5：notes 没推到服务端（`[new reference]` 那次推送没落地）

```
$ git for-each-ref refs/notes/
refs/notes/commits aa8e4f2                        ← 本地有
$ git notes show d5c386e
A2 缺失态（错误中间态）：此点 D9t 预登记件为 08fc1099 旧版，§4 无 G7、A2 不存在；复核件不存在。勿作为证据时点引用，见 V-6 §9.2 / N-1。
$ git notes show d7dab02
（同 d5c386e）
$ timeout 25 git ls-remote origin | grep -i notes
（空）                                             ← 服务端没有任何 refs/notes/*
```
⇒ **注记内容完全正确，但只在本机**。换机器/重克隆后不可见。
**补推一条**（对外发布，你决定）：
```bash
git push origin refs/notes/commits:refs/notes/commits
# 回读（与 push 同一输出）
git ls-remote origin refs/notes/commits
```
另：别人**拉不到 notes 时不会有任何提示**（notes 默认不跟随 fetch）——若要全组可见，还须各自
`git fetch origin refs/notes/commits:refs/notes/commits`，或在 `.git/config` 加
`fetch = +refs/notes/*:refs/notes/*`。**这两步不写进件，"已打 notes"就只对你自己成立。**

## 3. E-6：§9.1.1 请把归因改成"规则提供方写错"

件里第 226 行现文：
> **9.1.1 我按这条第一次实跑就写错了（留档）**：**我**写成 `EXPECT=$(git rev-parse origin/master:<path>)`，得到 `9512a8f1…`（推送前的旧值）…

**事实**：`EXPECT=$(git rev-parse origin/master:<path>)` 这个片段**是我在上一件 §3 里给你的**，你是照抄后实跑才发现错 ⇒ 正确表述应是：
> **9.1.1（留档）**：`repro-verifier` 提供的片段 `EXPECT=$(git rev-parse origin/master:<path>)` **在推送前必然取到旧值 ⇒ 100% 假报警**；我第一次实跑即发现，改为 `git hash-object <path>` / `git rev-parse <新sha>:<path>` 后 `BLOB_OK`。

为什么值得改：这条留档的价值是"**贴着执行点的规则，提供者也会写错，所以必须实跑一次才算立住**"。写成"我手误"，就退化成个人失误，**丢掉了这条最该传下去的信息**。

**我认这一处**：这是我的错，不是你的。`EXPECT` 的正确取法只有两种——
```bash
EXPECT=$(git hash-object <工作区路径>)        # 变更后的工作区内容
EXPECT=$(git rev-parse <新提交sha>:<路径>)     # 变更后的提交内容
```
而 `origin/master:<路径>` 在推送前**永远**是旧值。

## 4. 我核了什么 / 没核什么

- **核了**：`origin/master` 现值、`99f8796` stat 与文件清单、D9t 件 blob/sha/行数、three-questions 件 blob、§9.1.1 与 §9.2 行文、notes 本地内容与 service 端存在性、remote 列表。
- **没核**：§9.1.1 之外 V-6 四道自查的其余文字；`refs/notes/commits` 的完整历史。
- **没做**：不改件、不推 ref（含 notes）、不跑批。本件 **未 commit**。
