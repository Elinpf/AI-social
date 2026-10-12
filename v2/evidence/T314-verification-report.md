# T314 独立复验报告 —— T311 回归守护 + 负向夹具（只验不改）

**复验者** kernel-dev · **日期** 2026-10-13 · **性质** 只验不改
**被验版本（pin）**：守卫 `resume_regression_guard.sh` = `9af5259`+`5b939d8`；探针 `repro_resume_cut.sh` = `ecc7f4c`（T316）；夹具 `tools/t271/fixtures/resume_divergence_cut75/`。第 3 轮复跑时 HEAD=`35787ef`。

**结论一句**：**该红能红、该绿才绿、探测失败必红。**

---

## ① 双向实测

**A. 回归守护（current HEAD，cut=75/89，自有副本）**
```
$ T271_REPRO_COPY=/tmp/t271-repro-kernel T271_GUARD_CUTS="75 89" bash tools/t271/resume_regression_guard.sh
# 读数（第 3 轮，最终）：
=== cut=75 ===  oneshot==resume1==resume2=8820493fd8d219389e1736e609960eced8380263b8d4cc881e0d1f3ec4f07558 ; state_hash 不等数=0 ; 判决 ==oneshot? yes
=== cut=89 ===  oneshot==resume1==resume2=8820493fd8d219389e1736e609960eced8380263b8d4cc881e0d1f3ec4f07558 ; state_hash 不等数=0 ; 判决 ==oneshot? yes
############ RESUME-REGRESSION GUARD: PASS ############
EXIT=0      # 绿（必须绿）
```

**B. 负向夹具（must-be-red）**
```
$ make resume-fixture-check
夹具 oneshot sem_sha = 8820493fd8d219389e1736e609960eced8380263b8d4cc881e0d1f3ec4f07558
夹具 resume  sem_sha = 110840b768ef7668ff51e2f4895c7343ee9fb351fa55a40c77871caf7431a017
OK: 夹具两文件语义投影【不等】⇒ 门在真实数据上【能报红】可断言（must-be-red 成立）
EXIT=0      # 夹具"不等"可断言 ⇒ 门能报红
```

## ② 假绿专项

**A. 坏 sha**（探测失败/无输出）
```
$ T271_REPRO_SHA=deadbeefdeadbeefdeadbeefdeadbeefdeadbeef T271_GUARD_CUTS=75 T271_GUARD_TIMEOUT=60 bash tools/t271/resume_regression_guard.sh
副本缺失：/tmp/t271-repro-guard/code
  [cut=75] FAIL（rc=2 ; oneshot='' r1='' r2='' ; <无 state_hash 行>）
           —— 含『探测失败/无输出/超时』情形：一律判红（假绿防护）
############ RESUME-REGRESSION GUARD: FAIL（续跑一致性回归！）############
EXIT=1      # 红（正确）
```

**B. 夹具缺失**
```
$ T271_FIXTURE_DIR=/nonexistent-fixture make resume-fixture-check
FAIL: 夹具缺失（/nonexistent-fixture/oneshot.jsonl / /nonexistent-fixture/resume.jsonl）
EXIT=2      # 红（正确）
```

**★ 附加证据（前两轮"作废轮"中假绿防护仍正确判红）**：第 1 轮运行中撞 `9af5259` 加固（脚本 line 47 语法错）、第 2 轮运行中撞 T316 改探针（`semantic_log_sha.py` Traceback）：**两轮三投影均为空 ⇒ 守卫判红（rc=2/非 0）**。即"探测/工具失败 ⇒ 红"**又两次实测生效**（真实装置故障，非世界分歧）。

## ③ 错误处理路径

- 守卫：`set -uo pipefail`（**非 `-e`**）+ **显式判据**：`repro rc==0` ∧ **三投影均为非空 64-hex 且恒等** ∧ `state_hash 不等数=0`；任一不满足 ⇒ 打印 FAIL 原因并 `exit 1`。
- 夹具检查：`set -uo pipefail`；**必须合法 64-hex 且【不等】**；为空/非法/相等/缺失 ⇒ 打印 FAIL 并 `exit 1`（缺失分支 `exit 1`，实测经 `make` 报 `Error 1`，shell `EXIT=2` 为 make 的二次退出码）。
- **无"探测一错就绿"路径** ⇒ 无假绿机器。

## ④ 装置前提

- **分进程**：每 cut 独立 `bash`；repro 内 warm/oneshot/2×resume **各自子进程**。
- **自有隔离**：`T271_REPRO_ROOT=/root/t271/runs/repro_guard`、`T271_REPRO_COPY=/tmp/t271-repro-kernel`（本轮显式指定，避免与他人并发撞目录）。
- **固定 prefix 截断**（非墙钟 kill）；**先 warm**（冷热对等）；**sha 固定**只读副本（`time.json` 已跟踪，副本含之）；每 cut 先 `rm -rf "$COPY"`。
- **并发情况**：本轮（第 3 轮）同刻还有 **T304（art）** 与 **T310（obs 跑批）** 在跑，共享 LLM 端点/CPU；第 3 轮仍稳定 PASS。**前两轮作废 = 运行中被改，非世界**。

## ⑤ "未挂 gate/verify"核法 + 被验 sha

```
$ git rev-parse HEAD                      # 35787ef（第3轮时）
$ git log --oneline -1 tools/t271/resume_regression_guard.sh   # 5b939d8（含 9af5259 加固）
$ git log --oneline -1 tools/t271/repro_resume_cut.sh          # ecc7f4c（T316）
$ sed -n '/^gate:/,/^$/p' Makefile | grep -c resume            # 0  ⇒ gate/verify 未挂 resume-guard/fixture-check
$ grep -n "resume-guard\|resume-fixture" Makefile | head       # 仅 .PHONY/help/独立目标；不在 gate/verify 依赖链
```
⇒ `verify = gate + make -C code ci`，`gate = stamp+lexicon-gate+inert-gate+code-test+plugin-test+lint-imports` ⇒ **resume-guard/fixture-check 未挂 verify/CI 同步段** ✓（独立、慢，符合设计）。

## 备注（诚实）

- 前两轮作废：**非世界问题、非守卫缺陷**，而是"运行中脚本被改"（正是"验证窗内须冻结被验对象"的实例）。
- 本轮未跑 `make verify`（本任务不需要）；临时产物仅在本人的 `/tmp/t271-repro-kernel` 与日志 `/tmp/t314_guard*.log`。
