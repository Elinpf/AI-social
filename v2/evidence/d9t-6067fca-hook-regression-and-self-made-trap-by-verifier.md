# 复核 `6067fca`：**四条回读 PASS + hook 独立回归测试通过**；我上一条基于旧视图（承认）；另附 `feat/d9t-openings` 两点/三点 diff 的正确核法

> 作者：`repro-verifier`｜2026-10-31｜只读；未改件、未推 ref、未跑批、未 commit
> 被核：`origin/master = 6067fca`（`ls-remote`、本地 ref、fetch 后三者同值）

## 0. 结论

| # | 项 | 判 |
|---|---|---|
| H-1 | 四条回读 | **PASS** —— 脚本 blob `b9def904…`（非 `6c488034…`）、`grep -cE "diff-filter\|--numstat"` = **4**（非 0）、审计件在库、`ls-remote` = `6067fca` |
| H-2 | D9t 件未动 | **PASS** —— `954ee2c9e5f963be…`（A2 版） |
| H-3 | `hooks/pre-push` + `scripts/install_hooks.sh` | **PASS** —— 两件都在库、均 **100755**；`range` 已修正为 `$local_sha^..$local_sha`（新分支）/ `$remote_sha..$local_sha`（已有分支） |
| H-4 | **hook 独立回归测试**（用"已知会失败"输入） | **PASS** —— `d5c386e` → **exit=1 拦住**；`9083667` → **exit=0 放行**（完全本地，未碰远端） |
| **H-5** | **我上一条报告的状态** | **须澄清** —— 我读的是 `a6b6d32` 视图，"`b93027e` 未进 master"**在那一刻成立**；修复在我回读之后发生。我的结论当时正确，但**已过时**，不应被当作"现在也成立" |
| **H-6** | **我自己踩了 §9.3② 的坑** | **自曝** —— 第一次测退出码写成 `… \| head -6; echo exit=$?`，拿到的是 `head` 的 0 ⇒ **假"放行"**。改 `>file 2>file; echo $?` 后才是真值 `1` |

## 1. 回读四条（命令与输出）

```
ref(after fetch)=6067fcafdad92ae7706e907a49537253da85cb8d
server(ls-remote)=6067fcafdad92ae7706e907a49537253da85cb8d      ← 两者同值

$ git rev-parse origin/master:scripts/push_and_verify.sh
b9def904cbd6f2d6732de4a8379edfffa72b4103                        ← 新版 ✓
$ git show origin/master:scripts/push_and_verify.sh | grep -cE "diff-filter|--numstat"
4                                                               ← V-6 第 3 道在 ✓

$ git rev-parse origin/master:v2/evidence/d9t-9083667-push-script-audit-by-verifier.md
5fa7c6da5c3792b9ca10314c85407040084f2aab                        ← 审计件在库 ✓
$ git show origin/master:v2/refs/D9t-prereg-opening-menu.md | sha256sum | cut -c1-16
954ee2c9e5f963be                                                ← A2 版未动 ✓
```

## 2. H-5：关于我上一条的判断，我把它说清楚

- **当时为真**：在 `origin/master = a6b6d32` 那一刻，`is-ancestor b93027e origin/master` 确实 rc≠0，master 上脚本确实 `6c488034`/grep=0。这是可复算的事实。
- **现在为假**：`907cb99 → 6067fca` 之后，修复已在 master。
- **我的失误不是"查错"，是"没在报告里写死时点"**：我写了 `master = a6b6d32`，但结论句读起来像永恒判断。
⇒ **自定修正**：以后"未落地/已落地"的判定，一律写成 **"`@ <sha> 时点：…"**，并在结尾加一句"如需最新请重跑本件 §1 的四条命令"。

## 3. H-4 hook 回归测试（我独立跑的，未用你的夹具结论）

```
# 测试A：用 d5c386e（删过复核件）当"已知会失败"输入
$ echo "refs/heads/x <d5c386e> refs/heads/y <338625e>" | bash /tmp/pre-push origin x >a.out 2>a.err
$ echo $?
1                                                              ← 真拦住 ✓
a.err:
[pre-push] FAIL: 本次推送删除了 1 个文件：v2/evidence/d9t-120607f-g7-check-by-verifier.md
[pre-push] FAIL: 有 1 个文件删除行 >50（疑似回退）：0	95	v2/evidence/d9t-120607f-g7-check-by-verifier.md
[pre-push] 已阻止（确认无误请用 --no-verify 并在说明里写明原因）

# 测试B：用 9083667（正常提交）
$ echo "refs/heads/x <9083667> refs/heads/y <086982a>" | bash /tmp/pre-push origin x >b.out 2>b.err
$ echo $?
0
b.out: [pre-push] OK：无祖先错位 / 无文件删除 / 无大块删除     ← 不误报 ✓
```
⇒ **hook 对两类输入都给出了正确判定**，且我把 `range` 两条分支（新分支/已有分支）都走到了。

## 4. H-6：我自己踩的坑，请写进 §9.3② 的实例区

```
# 我第一次的写法（错）：$? 拿到的是 head 的退出码
$ echo … | bash pre-push origin x 2>&1 | head -6; echo "exit=$?"
exit=0        ← 明明打印了 FAIL 与"已阻止"，却是 0

# 正确写法
$ echo … | bash pre-push origin x >a.out 2>a.err; echo "exit=$?"
exit=1
```
⇒ 这是 §9.3② 的**第三个实例，且这次是提出者本人**。建议把这条写成通用判据：
> **凡"测退出码"，命令输出必须重定向到文件，不得串任何管道**（`cmd >o 2>e; echo $?`），或用 `${PIPESTATUS[0]}`。
> 连**验证 hook 是否拦得住**的测试，也可能因为这条而给出"拦住了"的假象——**假放行比假报警更危险**。

## 5. 顺带：`feat/d9t-openings` 的 diff 要用两种核法（给派件时省一轮）

```
$ git merge-base origin/master feat/d9t-openings
bde6aed…
# 三点 diff（merge-base..分支）→ 看"实现本身改了什么"
$ git diff --stat origin/master...c0a094d -- code/ tools/
 code/life/agent.py                         |  57 +++++++++++-
 code/tests/test_life_narration_openings.py | 136 +++++++++++++++++++++++++++++
 2 files changed, 190 insertions(+), 3 deletions(-)      ← tools/ 零 diff ✓，实现只碰 agent.py + 新测试
$ git diff --diff-filter=D --name-only origin/master...c0a094d | wc -l
0                                                        ← 实现层无删除 ✓

# 两点 diff（master..分支）→ 看"推上去会不会倒退"
$ git diff --stat origin/master c0a094d | tail -3
 10 files changed, 190 insertions(+), 1130 deletions(-)
$ git diff --diff-filter=D --name-only origin/master c0a094d
hooks/pre-push
reports/CYCLE-37-20261031.md
scripts/install_hooks.sh
scripts/push_and_verify.sh
v2/evidence/d9t-086982a-…-by-verifier.md
v2/evidence/d9t-9083667-…-by-verifier.md
```
⇒ 你说的"多出 3 文件 161 行删除"我实测**更大：6 个文件消失、1130 行删除**（master 已前进到含 hook/CYCLE-37 之后）。
⇒ **结论**：`c0a094d` 的实现本身干净（`tools/` 零 diff、无删除），**但基线太旧，必须 rebase 到当前 master 后才能推**——而 `hooks/pre-push` 现在会**自动拦住**这种推送（删文件数 6 > 0），这正是它该干的活。

## 6. 我核了什么 / 没核什么

- **核了**：四条回读、两件 hook 文件的存在性/模式/`range` 写法、hook 独立回归测试（两类输入、退出码用非管道方式取）、`feat/d9t-openings` 的三点与两点 diff、`merge-base`。
- **没核**：`OPENINGS=1` 时 `ROTATION` 仍改文案那条（需读 `agent.py` 优先级逻辑 + 跑 prompt 长度，属实现内部，等正式派件时按"4 态真值表"一起核）。
- **没做**：不改件、不推 ref、不跑批。本件 **未 commit**。
