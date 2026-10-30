# D9m 预登记 · 修订 1（**事实性勘误，不改任何判据阈值**）

> 立件：exp-designer｜时刻：2026-10-30 08:16 +08:00（**起跑前**）
> 修订对象：`v2/refs/D9m-prereg-narration-rotation.md`（sha256 `0d10450232b04327fe7980ddbaa68b694fba9b1b827b433b5b54b5d7c1b06643`，mtime 08:12:38）
> 依据：原件 §11.1 第 3 条「若必须修订，另起 `D9m-prereg-amendment1-*.md` 并写明理由与原判据编号」。
> **本修订不改变任何阈值、不改变主/辅判据归类、不改变三态条件**——只纠正一处**事实陈述**与一处**计数表述**。

---

## A-1 纠正 §10.5「D9j 无版本化历史」——**该结论错误，D9j 已版本化**

**原件 §10.5 原文（错误）**：「`v2/refs/D9j-prereg-narration-quality-gate.md` 是未跟踪文件（`git ls-files --error-unmatch` rc=1；`git log -- <file>` 空输出）⇒ 无 commit 历史可证」。

**错在哪**：上述两条命令都是**在当前检出分支 `feat/prompt-narration-toggle` 上**跑的。D9j 是**在 `master` 线上提交的**，该提交不是当前分支的祖先，因此在这条分支上 `git log -- <file>` 自然为空、文件自然 untracked。**这是我（和 verifier、Leader 转述）共同的取样偏差**：把「当前分支看不到」误当成「仓库里没有」。

**实测证据（本轮实跑，可复算）**：

```bash
cd <repo>
git rev-parse df488ce                               # df488ce4a0d9bbce499cee7ed422ab6776b0ed5e
git show --stat df488ce                             # v2/refs/D9j-prereg-narration-quality-gate.md | 77 ++++++
# commit 信息：docs(d9j): 立旁白质量闸预登记——八条判据(4判定+2绝对量护栏+1上卷+1诊断)…
# Author: life-evidence-analyst  Date: Fri Oct 30 05:39:47 2026 +0800
git merge-base --is-ancestor df488ce origin/master && echo ON_MASTER   # → ON_MASTER（08:1x fetch 后仍成立）
git show df488ce:v2/refs/D9j-prereg-narration-quality-gate.md | sha256sum
sha256sum v2/refs/D9j-prereg-narration-quality-gate.md
# 两个值都是 dc909541e52c7eaf96f637836d8ee006cc0d0589d90b1e14cb165df1191bed68  ⇒ 与工作树逐字节相同
```

**修正后的正确表述（此后一律用这个）**：

> D9j 预登记**已版本化**：commit `df488ce`（2026-10-30 05:39:47，在 `master` / `origin/master` 线上）。
> 其 blob 的 sha256 = `dc909541…`，与工作树同值 ⇒ **自提交以来未被回改，冻结有 commit 历史可证**。
> 仅因当前检出分支 `feat/prompt-narration-toggle` 不含该提交，文件在本分支显示为 untracked。

**对 verifier 的含义**：**不再需要**以「弱证据（mtime + sha256）」作为 D9j 冻结性的兜底——现在有 commit 历史 + blob sha 双证。原件 §11 对本件自身仍保留 B 方案留痕（本件确实尚未 commit，等分支建立后随实现件一并提交并回填 §11.3），两者不矛盾。

---

## A-2 纠正「判据 6 条」的计数归因（结论不变，只是不再猜 owner 原意）

原件 §10.1 说 D9j 件头「八条」与表内 6 行「计数口径混乱」，并尝试把它解释成「4 判定 + 2 护栏 + 1 上卷 + 1 诊断」凑 8。**现据 commit `df488ce` 的原始信息，D9j 的自我标注就是这四项凑 8**（原文：「八条判据(4判定+2绝对量护栏+1上卷+1诊断)」）。

⇒ **不代 owner 解释它怎么凑的**，只登记事实两行：
- 件头与 commit 信息自称 **八条**（4 判定 + 2 绝对量护栏 + 1 上卷 + 1 诊断）；
- §1 表内实有 **6 行**：(a)(b1)(b2′)(c)(d)(e)；
- **本件（D9m）以表内 6 行为验收集合**，与 `team-workspace/recon/dedup-and-criteria.md:15,113,147-150` 的独立摘录**一致**（该摘录同样判「文件内部计数不一致」）。

**判据条数、阈值、三态：一律不变。**

---

## A-3 新登记：`origin/master` 上已存在**另一份 D9m 预登记**（需 Leader 裁决，本件不自行处理）

**事实**：`origin/master` 尖端（08:1x fetch）= `0938f14fb5d07e638a1d0639391f2bfbbf2139f3`（2026-10-30 08:11:43，`life-evidence-analyst`），其提交新增
`v2/refs/D9m-prereg-narration-action-diversity.md`（109 行），设计为 **A+B 两处改动**（A 改示例 ≥6 句轮换 + B 新增「禁过渡动作」约束），验收分两层（r24 验接线与方向、r84 验绝对量 ≥86.01%）。

**与本件的关系（事实并列，不做取舍）**：

| 维度 | 本件（`…-narration-rotation.md`） | master 上的 `…-narration-action-diversity.md` |
|---|---|---|
| 改动数 | **1 处（A only）** | **2 处（A+B）**，其自身已声明「不得写成优化示例」 |
| 规模 | r24（n16/seed42） | r24 接线与方向 + **r84** 绝对量 |
| 判据 | 表内 6 条，(b2′)+(d) 主，(c-1) 守卫，(c-2) 咬合**不可判** | 「沿用 D9j 八条，判定用前六条 + 两条护栏」 |
| 状态 | 本地未跟踪（待随实现件 commit） | **已在 `origin/master`** |

⇒ **两者口径存在实质冲突**（改动数 1 vs 2；(c-2) 可判 vs 本件判不可判）⇒ **必须由 Leader 裁决保留哪一份 / 如何合并**。本件不改动自己已冻结的判据去迁就另一份；若裁决为 A+B 双改动，则本件需另起 **修订 2**（或作废）并明确写「两处改动 ⇒ 非单变量，A 的净效应不可单独归因」，且 (a)(e)(c-1) 的读数与 A-only 臂不可比。

---

## A-4 本修订生效方式

- 本文件落盘即生效（作为原件的补充事实层）。**原件判据正文继续以 sha256 `0d104502…` 为准**，不被本文件覆盖。
- 本文件 sha256 与 mtime 追加到 `team-workspace/recon/D9m-freeze-receipt.txt`（同文件追加区）。
- 报告侧引用规则：凡引「D9j 冻结性」必须用 A-1 的修正表述；凡引「判据条数」必须写「表内 6 条（件头自称八条）」。
