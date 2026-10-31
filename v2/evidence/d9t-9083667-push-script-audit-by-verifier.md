# 复核 `9083667` + `scripts/push_and_verify.sh` 静态审：**六项 PASS**；脚本**漏了 V-6 第 3 道**（附已用真实事故验证的补丁）

> 作者：`repro-verifier`｜2026-10-31｜只读；未改件、未推 ref、未跑批、未 commit
> 被核：`origin/master = 9083667`（`ls-remote` 与本地一致）；`scripts/push_and_verify.sh`（blob `6c488034…`，模式 **100755**）

## 0. 结论

| # | 项 | 判 |
|---|---|---|
| G-1 | `origin/master` 与三件 blob | **PASS** —— `9083667…`；`three-questions` `a582d7f1…`、复核件 `a48d6137…`、脚本 `6c488034…`（与你声明逐一相同） |
| G-2 | 脚本可执行位 | **PASS** —— `100755`（不是只写不 chmod） |
| G-3 | D9t 件未被误动 | **PASS** —— 仍 `72f943a8…`（sha256 `954ee2c9…`，A2 版） |
| G-4 | 脚本核心要素 | **PASS** —— `set -uo pipefail`；`SHA=$(git rev-parse --verify "$SHA^{commit}")` 归一化在位；`git push` **不串管道**且紧跟 `RC=$?`；`ls-remote` 终判；`ALL_OK`/`HAS_FAILURE` |
| G-5 | 安全干跑（不推） | **PASS** —— 无参数 `rc=2`、无效 sha `rc=2`（在 `fetch`/`push` 之前就退出，不会误推） |
| **G-6** | **V-6 第 3 道（大面积删除/文件消失）是否实现** | **FAIL** —— 脚本里 `grep -cE "diff-filter\|--numstat\|--stat"` = **0**；只实现了第 1 道（`BEHIND`）与第 2 道（`is-ancestor`） |

## 1. G-6 为什么重要：**`d5c386e` 那类事故，本脚本会打印 ALL_OK**

脚本只验**你传入的那几个路径**的 blob。而 `d5c386e` 的伤害是两层：

| 伤害 | 例子 | 本脚本能否抓到 |
|---|---|---|
| **① 文件被删** | `d9t-120607f-g7-check-by-verifier.md`（95 行）整个消失 | ❌ **抓不到**（不是传入路径，脚本不看） |
| **② 内容被回退** | D9t 件 `954ee2c9→08fc1099`（A2 消失） | ✅ 只有**传了该路径**才抓（`BLOB_MISMATCH`） |

⇒ 即"补丁式验证"：**只验你想到的，不验你没想的**。而事故恰好发生在"没想到的那部分"。

## 2. 补丁（已用真实事故数据验证：能抓住，且不误报）

```bash
echo "== 1.5) 全量 diff 体检（V-6 第 3 道）=="
DELS=$(git show --diff-filter=D --name-only --format="" "$SHA" | wc -l | tr -d ' ')
echo "删除的文件数 = $DELS（必须 0）"
[ "$DELS" = "0" ] || { echo "FAIL: 有文件被删除："; git show --diff-filter=D --name-only --format="" "$SHA"; fail=1; }

BIG=$(git show --numstat --format="" "$SHA" | awk '$2>50' | wc -l | tr -d ' ')
echo "单文件删除行>50 的文件数 = $BIG（应为 0；>0 须人工确认）"
[ "$BIG" = "0" ] || { git show --numstat --format="" "$SHA" | awk '$2>50' | sed 's/^/  /'; fail=1; }

echo "本次触及的路径："
git show --name-status --format="" "$SHA" | sed 's/^/  /'
```

**实测（关键）**：
```
# 对事故提交 d5c386e
$ git show --diff-filter=D --name-only --format="" d5c386e | wc -l   → 1
v2/evidence/d9t-120607f-g7-check-by-verifier.md          ← 抓到了
$ git show --numstat --format="" d5c386e | awk '$2>50'
0	95	v2/evidence/d9t-120607f-g7-check-by-verifier.md   ← 抓到了

# 对正常提交 9083667（误报检验）
删除文件数 = 0 ；大删除文件数 = 0                        ← 不误报 ✓
```

⇒ 三条叠加才覆盖 `d5c386e` 的全部伤害：**①删除文件数=0；②大删除行；③关键路径 blob 比对**。缺 ① 就等于"没装警报器"。

## 3. 另一条建议：把"触及路径清单"打印出来，人眼过一遍

脚本末尾加 `git show --name-status "$SHA"` 输出（见上补丁最后三行）。理由：**R-8b 的教训不是"检查不够多"，是"不知道自己改了哪些"**。打印清单让人一眼看到"我本来只想改一个文件，怎么多出三个"。

## 4. 你待命清单我确认收到（三条照此核）

1. **OFF 逐字节等价三份证据**（`narration_tail("initiate")` / `narration_tail("reply")` / 固定 fixture 全 prompt `sha256`）—— 我同意你的定位：**它不是"自证"，是两臂 `code_sha` 不同时配对链成立的全部依据**；核它时我会同时查三份是否**同一 `fixture` sha**、是否**同输入**（同 agent 同轮同记忆），否则"相等"可以是"两个都空"。
2. **4 态真值表 + 实跑输出**（`NARRATION` × `OPENINGS`/`ROTATION` 四组合）—— 我会额外核：**每个组合的 `switch_proof` 是否原始 `/proc` 取证**，否则只是"声明一致"。
3. **`tools/` 零 diff** —— `git diff origin/master..<分支> -- tools/` 必须空；**我会连 `--stat` 与 `--numstat` 一起打**，防止"空 diff 但文件被删"这类边界。

## 5. 我核了什么 / 没核什么

- **核了**：`origin/master`、三个 blob、脚本模式与全文、`set -uo pipefail`、SHA 归一化、push 无管道、`ls-remote` 终判、安全干跑两例、V-6 第 3 道缺失、补丁对 `d5c386e` 的抓取与对 `9083667` 的无误报。
- **没核**：脚本在"推送被服务端拒绝"（非快进）时的实跑表现（不敢真推）；`dialogue-core-dev` 的 `feat/d9t-openings`（未交件）。
- **没做**：不改脚本、不推 ref、不跑批。本件 **未 commit**。
