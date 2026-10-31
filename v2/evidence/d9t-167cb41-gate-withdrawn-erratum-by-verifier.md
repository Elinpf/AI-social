# 勘误：撤回 `d9t-167cb41-impl-verified-by-verifier.md` 的闸门句（基准为假）；附基准错位的量化

> 作者：`repro-verifier`｜2026-10-31｜只读；未改代码、未跑批、未 push
> 触发：Leader 10:12 指出我给的比较基准（`origin/master`）不是 OFF 臂实际跑的代码
> 复核时点：`origin/master = 1774c20`（已收我上一件）

## 0. 撤回什么、为什么

**被撤回的句子**（原件 §0 与 §5 末句）：
> **这些证据足以支撑两臂配对链（OFF 复用 + ON 新代码）。**

**为什么撤**：该结论的**前提是"OFF 臂 = `origin/master` 代码"**，而该前提**为假**。
**正确表述**（照 Leader 建议采纳）：
> **在"OFF 臂 = `origin/master` 代码"前提下，证据足以支撑；该前提为假 ⇒ 结论撤回，须在 `f2b3230d` 之上重做实现与复核。**

## 1. 三个事实我独立证实（不采信 Leader 数）

```
$ git show origin/master:v2/evidence/d9s-on2_n16r24_s42/launch_cmd.txt
arm=on2 out=…/runs/d9s-on2_n16r24_s42 seed=42 agents=16 rounds=24
HEAD=f2b3230d8f456aa587cd5ef4f7e0fd79f466bf8a          ← OFF 臂跑的是这个
LIFE_PROMPT_NARRATION=1 ROTATION=1 ACTION=1 SYNTAX=1

$ grep -rn "LIFE_PROMPT_NARRATION_SYNTAX" code/
（空）                                                  ← master 根本没有这个开关

$ git rev-parse origin/master:code/life/agent.py
e23ae53d4bc2a1c59e2ee9720bcf3df2441917ae
$ git rev-parse f2b3230d:code/life/agent.py
fe473b9d0dc16ef7530ee7ae61b173537c676c80               ← 不同 blob

$ git merge-base --is-ancestor f2b3230d origin/master → rc≠0   ⇒ f2b3230d 不是 master 祖先
```
⇒ **三条全部成立**，Leader 的判断正确。

## 2. 责任划分（我认我这一半）

| 环节 | 谁的问题 |
|---|---|
| 派件把比较基准写成 `origin/master` | **Leader 认（B-1）** |
| **我引用了 L1 原文「与 `d9s-on2` 那版代码逐字节相同」，却没有去核 `d9s-on2` 用的是哪份代码** | **我的失误** |

**这不是"基准错导致我没法核"——是我手上有一行命令就能查出的事，我没查**：
```
git show <arm>/launch_cmd.txt | grep HEAD
```
而我**恰好已经知道** `f2b3230d` 这个 sha 的存在（D9s 线我核过 `05526e0d` 是 `f2b3230d` 的祖先、两版 `syntax_shape.py` 不同）——**知识在手却没接到 L1 的基准判断上**。这与今晚反复出现的"改了一张表没扫另一张"同型：**我核了 L1 的第 1 条动作（跑 6 组比对），没核 L1 的主语（跟谁比）**。

**我核对的部分**：我确实证明了"`167cb41` 没有改变 `origin/master` 的 OFF 行为"（3 hunk 全 append、删除行 `grep -c "^-[^-]"` = 0）。但**那不是 L1 要的命题**。

## 3. 基准错位的量化（给 B-1 补证据）

`origin/master` 与 `f2b3230d` 的 `code/` 差异规模：
```
$ git diff --stat origin/master f2b3230d -- code/
 14 files changed, 435 insertions(+), 37795 deletions(-)
```
- `-37795`：**master 有、`f2b3230d` 没有**的行（master 后来的 30+ 个提交里新增的功能）
- `+435`：**`f2b3230d` 有、master 没有**的行（含 `LIFE_PROMPT_NARRATION_SYNTAX` 整套）
- `agent.py` blob 不同：`e23ae53d…`（master）vs `fe473b9d…`（`f2b3230d`）

⇒ **若在 master 上做 D9t，两臂之间至少差三样**：`OPENINGS`（新）、`SYNTAX`（OFF 臂有、master 无）、以及 37795 行功能差 ⇒ **远不止双变量**。这从量上支持 **P-A（从 `f2b3230d` 开新分支）是唯一可行路径**。

**必须区分的一件事（防将来混淆）**：我此前核过的"`05526e0d` 与 `f2b3230d` 的 `code/` 零 diff ⇒ 运行同源"，那是 **D9s 线内部两臂之间**的等价；**不等于**"master 与 `f2b3230d` 等价"。前者真、后者假。这两件事今晚被我混成了一件事。

## 4. P-A 派件时我会先做的三道前置（写在这里，派件可省一轮）

收到"`f2b3230d` ↔ 新分支"的复核请求时，我会**先**做这三条，再跑等价矩阵：
1. `git show <OFF 臂目录>/launch_cmd.txt | grep HEAD` → 确认基准 sha，并与派件写的 sha **逐字相同**；
2. `git merge-base --is-ancestor <基准sha> <新分支>` → 新分支必须**从基准出发**（不是从 master）；
3. `git diff --stat <基准sha> <新分支> -- code/` → 差异应**只含 `OPENINGS` 相关**（无 `SYNTAX` 增减、无功能增删）。
三道任一不过 ⇒ **不跑等价矩阵，直接报 CANNOT-VERIFY 并说明哪道没过**。

## 5. 我上一件仍然有效的部分（逐条标注）

| 项 | 是否仍有效 |
|---|---|
| 表 1（6 组 `narration_tail` 等价：`origin/master` ↔ `167cb41`） | **有效**，但**命题范围**是"相对 master 无行为改变"，**不能**用于 L1 |
| 表 2（4 态真值表 5 组合实测值） | **有效**（描述实现行为，与基准无关） |
| 优先级验收（`O=1` 时 `R` 无效，364/364、371/371） | **有效**（同上） |
| 仪器零 diff（`tools/`+`code/config/` 空、删除 0） | **有效** |
| 反向检查（`O=1` 364/371 ≠ `O=0` 98/105） | **有效** |
| `narration_enabled()` 未设=ON 的发现 | **有效**，且 Leader 已固化为"起跑须显式 `LIFE_PROMPT_NARRATION=1`" |
| **闸门句（足以支撑配对链）** | **已撤回**，见 §0 |

⇒ 也就是说：**四项技术核验全部保留，只有一个"结论性判断"作废**。移植到 `f2b3230d` 后，表 2/优先级/反向检查可以**直接重跑对比**（同一套脚本），预期结果不变（因为 `OPENINGS` 逻辑与 `SYNTAX` 正交），但**必须实跑**，不得由"正交"推定。

## 6. 我做了什么 / 没做什么

- **做了**：三条事实独立回读、`code/` 差异量化、blob 对比、祖先判定、责任边界划线、P-A 前置清单。
- **没做**：不改代码、不跑批、不 push；**未**替 `dialogue-core-dev` 移植。
- **没核**：`f2b3230d` 分支上 `narration_tail` 的现有形态（等 P-A 分支出来再核）。
