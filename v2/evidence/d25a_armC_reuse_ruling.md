# D2.5a 的 C 臂：**已由 cycle19 线跑完，核验通过，可复用（不重跑）**

> 日期：2026-10-24。执行方报告"worktree 里出现一份别人跑的真批"，本件核验其合法性并裁定归属，**避免两线重复跑同一臂**。

## 1. 来源（已查明，不是来路不明）

```
host.log: [runner] starting: … /jiuwen_team_cron___1a16ba2e52f_…/team-workspace/cycle19/scripts/d25a_launch_arm.sh --arm C \
          --worktree …/.worktrees/d25a-wiring --out-dir …/run_d25a_C_n16r60_seed42
          (unit=t271-d25a-C.service)   batch child pid=3159065
```
⇒ **cycle19 团队线**按 D2.5a 预登记跑的 C 臂，落在与接线分支**同一个 worktree**。

## 2. 合法性核验（五项，全部通过）

| 项 | 实测 | 判定 |
|---|---|---|
| 规模 | `rounds=60 / n=16 / seed=42` | ✅ 与预登记一致 |
| 代码树 | `code_sha=e2e7131a`（接线提交） | ✅ 含接线，`overrides_declared=[]` ⇒ 行为等于无 override 基线 |
| **指纹** | `code/config` 两树 **`diff -rq` 空**；`code/life`、`code/engine` 仅 `__pycache__` 差异；只有 `orchestration/cli.py` 不同（=接线） | ✅ **engine_version 指纹相同** |
| **结构** | **455 MSG（有 `from`）/ 114 线程** | ✅ 与 T0 基线 `run_d12c_off_n16r60_seed42` **完全一致**（455/114） |
| 真 LLM | `provider=openai_compat`、`model=DeepSeek-Flash`、`llm_calls=2878`、`duration=3094s`、`END` 存在 | ✅ 非 mock |

`meta.engine_version` 字段为 `null`（该字段本批未写），但**指纹一致已由 `config` 目录逐文件 diff 空证明**，不靠该字段。

## 3. 裁定

1. **C 臂（`run_d25a_C_n16r60_seed42`）可复用，不重跑** —— 省一次 ~52 分钟；
2. **A 臂归属需先与 cycle19 线协调**：两线同时在同一个 worktree 跑同一个臂会造成
   `unit`/`out-dir` 冲突与产物混读。在澄清前**不向执行方发 A 臂的「可跑」**；
3. 复用时的引用口径：`C 臂 = e2e7131a / n16r60 / seed42 / 无 override / 455 MSG / 114 线程`，
   **必须与 A 臂（8ab68a8 树，含 effective 占位键修复）分开记 tree sha**，不得笼统写"同树"。

## 4. 教训（拟入 runbook）

**多个团队线共享同一 worktree 时，跑批产物会落进同一路径。**
发现"来路不明的批"时，**先查 `host.log` 的 `unit=` 与启动脚本路径**（本件 30 秒定位到 cycle19），
再逐项核验（规模/树/指纹/结构/provider），**不要直接删、也不要直接采信**。
