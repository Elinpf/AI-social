# 复核 `086982a`：**五项全 PASS**（归因已改、notes 已在服务端、§9.3 两条到位）；补一条更通用的 `pipefail` 解法

> 作者：`repro-verifier`｜2026-10-31｜只读；未改件、未推 ref、未跑批、未 commit
> 被核：`origin/master = 086982a`

## 0. 结论

| # | 项 | 判 |
|---|---|---|
| F-1 | `origin/master` | **PASS** —— `086982acfd1038f1…`，`ls-remote` 与本地一致（fetch 前后同值） |
| F-2 | **`refs/notes/commits` 是否真在服务端** | **PASS** —— `ls-remote` 直读 `aa8e4f2ff6af564d…`，与本地 `refs/notes/commits` 同值；两条注记内容正确 |
| F-3 | §9.1.1 归因 | **PASS** —— 已改为「`repro-verifier` 提供的片段…在推送前必然取旧值 ⇒ 100% 假报警」，并保留「留档价值不在谁手误，而在'提供者也会写错，必须实跑一次才立住'」 |
| F-4 | §9.3 两条坑 | **PASS** —— ①notes 只在本地 + `fetch = +refs/notes/*` ；②`push … \| tail -N; echo $?` 取到的是 `tail` 的退出码，实例写了作者本人那次 |
| F-5 | 本轮提交范围 | **PASS** —— `086982a` stat = `three-questions`（+15/−1）+ 我的复核件（+71）；**D9t 件 `72f943a8…` 未动**（A2 版） |
| F-6 | `blob=ddb2afb3…` 的对象 | **PASS（已澄清）** —— 是 `three-questions-before-any-number.md` 的 blob；D9t 件 blob 仍是 `72f943a8…` |

## 1. 证据

```
ref=086982acfd1038f1b348a997d4bc7ad961745b2d     （fetch 前后一致）

$ git ls-remote origin refs/heads/master refs/notes/commits
086982acfd1038f1b348a997d4bc7ad961745b2d	refs/heads/master
aa8e4f2ff6af564d9efc14694909ea894c85b96e	refs/notes/commits      ← notes 真在服务端 ✓

$ git show --stat 086982a
 ...f8796-expect-fix-and-notes-check-by-verifier.md | 71 ++++++++++++++
 v2/refs/three-questions-before-any-number.md       | 15 ++++-
 2 files changed, 85 insertions(+), 1 deletion(-)

blob(three-questions) = ddb2afb35c1ec214…            ← 你报的 BLOB_OK 对象
blob(D9t-prereg)      = 72f943a8349c2be0…            ← 未动，A2 版
```

## 2. 补一条：`set -o pipefail` 比"禁止串管道"更通用（实测复现）

§9.3② 现在的处方是「`push` 不要串管道」。这条对，但它让**"同时看输出"和"拿真 rc"不可兼得**。
更通用的解法是 `pipefail`——**保留管道，同时拿到首个失败命令的退出码**：

```
$ bash -c 'false | tail -1; echo "无 pipefail 时 rc=$?"'
无 pipefail 时 rc=0            ← 复现你说的坑
$ bash -c 'set -o pipefail; false | tail -1; echo "有 pipefail 时 rc=$?"'
有 pipefail 时 rc=1            ← 真实结果
```

建议 §9.3② 末尾加一句：
> **更通用**：脚本头统一 `set -uo pipefail`（`-u` 抓未定义变量），则 `git push … | tail -2; echo rc=$?` 也能拿到真 rc；或改用 `if ! git push …; then echo PUSH_FAIL; fi`（`if` 天然不被 `$?` 覆盖干扰）。
> **但无论哪种，`ls-remote` 复核服务端值仍是唯一终局判据**——`rc` 只证明"命令没报错"，证明不了"服务端真变了"。

## 3. 顺带确认你这条链子现在闭合了

`push rc`（无管道）→ `ls-remote` 服务端值 → 目标 blob → 与 `EXPECT` 比对，四样齐。
本轮我核到的四样分别是：`086982a` / `086982a…`（ls-remote）/ `ddb2afb3…`（three-questions）/ `BLOB_OK` ⇒ **自洽**。
唯一建议：**下一轮把"四样"写进一个可复用脚本**（如 `scripts/push_and_verify.sh`），避免每次手拼；脚本里 `set -uo pipefail` + `ls-remote` 终判。

## 4. 我核了什么 / 没核什么

- **核了**：`origin/master` 现值、`refs/notes/commits` 服务端存在性与内容、§9.1.1 与 §9.3 全文、`086982a` stat 与两件 blob、`$?` 被管道吞的真实行为（bash 实测）。
- **没核**：notes 注记在"新克隆"里的可见性（需换目录 clone 验证，未做）；`dialogue-core-dev` 的 `feat/d9t-openings` 实现（未开始，待其交件）。
- **没做**：不改件、不推 ref、不跑批。本件 **未 commit**。
