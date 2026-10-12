# T273 · 提交范围守卫（拦住 `git add -A` 裹带他人 WIP）— 反向验证证据

- 日期：2026-10-12 16:48 +0800
- 仓库：`social-experiment`（branch `master`）
- 绑定版本：`HEAD=bef03b4`（bef03b4785646ca02518e697425515cddba67271）
- 产出 sha256：
  - `tools/enforce_commit_scope.py` = `a8f79aa1fa73e7bea936f15f297d8391e419c09105042d7419a68254aab05db4`
  - `tools/pre-commit-lexicon.sh`（含阶段 0 接线）= `ab395f9e5f40b81203586ec50747008c0c6aebe838a26d4339fac6c1ee294709`
  - `tools/t273_scope_guard_reverse_verification.sh` = `f493fcaa3afe4f729a2fd7e7d338807091eb9e2a573b4061621223a51723a22e`
- **落地状态：未落地**（`.git/hooks/pre-commit` 仍是旧版，`grep -c enforce_commit_scope .git/hooks/pre-commit = 0`）。按 Leader「落地时机听安排」——本卡只**设计 + 反向验证**，不改 live hook、不动 `code/engine|life|freeze|config`。

---

## 0. 病根与诚实边界

- **病根**：`git add -A` 会不留痕地把共享工作树里**别人尚未提交的 WIP**一起暂存；今天第 5 次，其中一次把 T268 的 WIP 扫进 HEAD。
- **不能假装解决**：`git add -A` 不留痕、**git 不记录作者** ⇒ 机制**不判定「作者是谁」**。
- **只判定一个可观测信号**：同一次提交里**混有「刚改动的新鲜文件」与「久未提交的陈旧文件」**——这正是 `add -A` 裹带他人 WIP 的典型形态。
- **不误伤**：单一陈旧文件（如整段重构一次性提交）**不拦**；正常新鲜提交**不拦**。

## 1. 机制

`tools/enforce_commit_scope.py`（确定性、可复算，仅读 `git diff --cached --diff-filter=ACM`）：

```
对暂存文件取 worktree mtime:  age(p) = now − mtime(p)
  flagged = { p : age(p) > AGE_MIN(900s) }        # 陈旧 = 疑似他人 WIP
  fresh   = { p : age(p) <= FRESH_SEC(300s) }     # 新鲜 = 本次自己的改动
  suspicious = (fresh 非空 ∧ flagged 非空)  ∨  (|flagged|≥2 ∧ max_age−min_age > SPREAD_SEC)
suspicious ⇒ 拦截(退出 1)，列出 flagged 路径 + 精确令牌；否则放行(退出 0)
确认放行：COMMIT_SCOPE_ACK=<令牌>（令牌随本次 flagged 集合而定，非永久白名单）
急救放行：COMMIT_SCOPE_DISABLE=1（打印告警，便于审计）
```

接线（**已写入钩子源，未安装**）：`tools/pre-commit-lexicon.sh` 新增「阶段 0」，在术语棘轮/可解析检查**之前**先跑范围守卫；安装仍走 `make install-hooks`（`cp tools/pre-commit-lexicon.sh .git/hooks/pre-commit`）。

## 2. 反向验证（亲手造裹带场景）

复现命令：`sh tools/t273_scope_guard_reverse_verification.sh`
（全程在**临时分支** `t273-scratch` + **临时 hooksPath**（不改 `.git/hooks`）；trap 复原：unstage + 删临时文件 + 回原分支 + 删临时分支 + 删临时 hooks。**不触碰他人未跟踪 WIP**。）

实测输出（2026-10-12 16:48）：

```
== T1 · 裹带场景（add -A 同时扫入 新鲜文件 + 20 分钟前的陈旧文件）-> 期望：红/拦截 ==
[scope-guard] 拦截：本次提交疑似裹带「长时间未提交」的路径
  暂存文件共 12 个；其中「新鲜(≤300s)」11 个、「陈旧(>900s)」1 个
  ---- 疑似他人 WIP（陈旧、且与本次新鲜改动同批）----
    1200s  tools/_t273_foreign.txt
  ----------------------------------------------------
  这是 `git add -A` 裹带他人未提交改动的典型形态。请二选一：
   (1) 只暂存你自己的文件：git restore --staged <他人路径> 后重试；
   (2) 确认这些路径确实属于本次提交：COMMIT_SCOPE_ACK=7db4f425f2ee git commit ...
  急救（不建议，会告警）：COMMIT_SCOPE_DISABLE=1 git commit ...
  注：本机制不判定作者（git 不记录作者），只识别「新旧混批」这一可观测信号。
>>> T1 exit=1 ; commits 243 -> 243 （未产生提交）

== T2 · 正常提交（仅刚改动的 1 个新鲜文件）-> 期望：绿/放行 ==
[t273-scratch 1b96a76] T273 normal commit
 1 file changed, 1 insertion(+)
>>> T2 exit=0 ; commits 243 -> 244

== T3 · 裹带场景 + 显式确认令牌 -> 期望：绿/放行 ==
[t273-scratch b94e13f] T273 incident ack
 2 files changed, 2 insertions(+), 1 deletion(-)
>>> T3 exit=0 ; commits 244 -> 245

== T4 · 纯陈旧文件、无新鲜文件（整段重构一次性提交）-> 期望：绿（不误伤）==
[t273-scratch 440c3df] T273 slow work commit
 1 file changed, 1 insertion(+), 1 deletion(-)
>>> T4 exit=0 ; commits 245 -> 246

== 结果汇总 ==
T1 裹带场景   exit=1 -> PASS-拦住了
T2 正常提交   exit=0 -> PASS-放行
T3 确认放行   exit=0 -> PASS-放行
T4 纯陈旧提交 exit=0 -> PASS-不误伤
```

### 结论（对照验收标准）

| 验收项 | 结果 | 证据 |
|---|---|---|
| 机制可运行 | ✅ | `tools/enforce_commit_scope.py`（sha 见上）可独立/被钩子调用 |
| **对亲手造的裹带场景报红** | ✅ | T1：`exit=1`、未产生提交（`commits 243->243`） |
| 正常提交路径不受影响 | ✅ | T2 `exit=0` 提交成功；T4 纯陈旧 `exit=0`（不误伤） |
| 不依赖「能判定作者」假前提 | ✅ | 机制只读 mtime 异质性，从不尝试归因作者 |
| 确认后放行（非永久白名单） | ✅ | T3：令牌匹配才放行；令牌随 flagged 集合而变 |

## 3. 假红风险与缓解（防「被逼去 `--no-verify`」）

- **判据只在「新旧混批」时触发**：单一陈旧文件（T4）与纯新鲜提交（T2）均放行 → 正常开发不被打扰。
- **确认廉价**：报错信息直接给出 `COMMIT_SCOPE_ACK=<令牌>` 一行命令；令牌精确到本次 flagged 集合，避免"一键永久关闭"。
- **急救开关**：`COMMIT_SCOPE_DISABLE=1` 可绕过但**打印告警**（审计可见），避免"只能 `--no-verify`"。
- **可调阈值**：`COMMIT_SCOPE_AGE_MIN_SEC / FRESH_SEC / SPREAD_SEC`，可按团队节奏放宽。

## 4. 结构性建议（机制代替提醒：不止一道钩子）

钩子是**兜底**，不是根治。并行建议（交 Leader 决策）：

- **结构性方向**：让「多人共用一棵工作树」不再共用。⚠️ **注意**：视觉工作**不能用 `git worktree`**（`review.html` 读主工作树，worktree 改动不出现在页面）——故此路对前端不适用，需另设（如按角色约定「先 `git add <明确路径>`，禁 `-A`」+ 本钩子兜底）。
- **提交约定**：鼓励 `git add <paths>` 显式暂存；`-A` 视为例外并触发确认。
- **可选增强（未实现）**：暂存文件数/跨目录数异常时要求写清范围（本题偏结构，留待 Leader 需要时再加）。

## 5. 落地步骤（待 Leader 安排，今晚不执行）

```sh
# 1) 复核钩子源（已含阶段 0）
sh -n tools/pre-commit-lexicon.sh           # 语法
# 2) 安装（等价于 make install-hooks）
cp tools/pre-commit-lexicon.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
# 3) 冒烟：正常提交应放行；造一次新旧混批应报红
# 回滚：git -C . checkout -- .git/hooks 不适用；恢复旧钩子只需重新 cp 旧备份或重跑旧脚本
```

> 未落地前：本机制**不生效**，`.git/hooks/pre-commit` 仍为旧版（无阶段 0）。

---

*（T273 反向验证证据 — sandbox-test-lead）*
