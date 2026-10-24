# 裁决：D2.5a 的 **C 臂可复用**（他人已跑），A 臂起跑权归 dialogue-core-dev

> 日期：2026-10-24 11:31 起核查。**同时是防重复起跑的声明件。**

## 1. 事实

`run_d25a_C_n16r60_seed42`（位于 `.worktrees/d25a-wiring/v2/evidence/`）**不是** `dialogue-core-dev` 起的。
`host.log` 实据：

```
[runner] starting: bash .../jiuwen_team_cron___1a16ba2e52f_444734663b74/team-workspace/cycle19/scripts/d25a_launch_arm.sh
         --arm C --worktree .../.worktrees/d25a-wiring --out-dir .../run_d25a_C_n16r60_seed42
         (unit=t271-d25a-C.service)
```

⇒ 是**另一条 cron 线（cycle19）**读了本预登记后主动跑的 C 臂。

## 2. 能否复用：**可以**（四条证据）

| 检查 | 结果 |
|---|---|
| 规模 | `rounds=60, n=16, seed=42` ✅ 与预登记一致 |
| 真 LLM | `provider=openai_compat`、`model=DeepSeek-Flash` ✅ |
| 无 override（真 C 臂） | `overrides_declared=[]` ✅ |
| **指纹可对** | `code/config` 与主树 **`diff -rq` 完全一致（空输出）** ⇒ `engine_version` 相同 |
| `code/life` / `code/engine` | 仅 `__pycache__/*.pyc` 差异（无关），`.py` 无差异 |
| `code/orchestration/cli.py` | 有差异 = 接线改动；但 C 臂 `overrides_declared=[]` ⇒ **该代码路径不被触发** |
| **结构落地** | **455 MSG（有 from）/ 114 线程** —— 与 T0 基线 `run_d12c_off_n16r60_seed42` **逐项相同** ✅ |
| 成本 | `llm_calls=2878`、`duration_sec=3094`（51.6min），单采口径合理（D12-I 的 4200 是 3 采） |

**⇒ C 臂合法有效，直接复用，省 52 分钟。**
（`engine_version` 字段为 `null` 属 meta 生成缺陷，已用 `code/config` 逐字节比对补上指纹等价性证明。）

## 3. A 臂起跑权与树的裁决（**防重复**）

- **A 臂由 `dialogue-core-dev` 在 `.worktrees/d25a-wiring` 的 `8ab68a8` 上跑**（含 `9d1297a` 的 effective 占位键修复）；
- **其他人/其他线不得再起 A 臂**。若已在跑，以本件时间为界：本件之后起跑者请立即停并报我。
- **两臂 `code_sha` 不同是已知且可接受的**：`C=e2e7131` vs `A=8ab68a8`，差异仅 `9d1297a`（`_effective_life_v2` 的占位键修复）+ `8ab68a8`（mock 证据），**C 臂路径不触发该逻辑**（无 override）。报告必须如实写明这一点，不得省略。
- 若评审要求"两臂严格同树"，则须在 `8ab68a8` 上**重跑 C**（+52min）——**本裁决认为不必要**，理由见上；但一旦 A 臂读数出现无法解释的差异，第一嫌疑就是这里，届时以重跑 C 兜底。

## 4. 起跑条件（已满足）

1. mock 三项全过（`8ab68a8`，`v2/evidence/d25a_wiring.md`）：读回 3、declared==run_process、`sleep/forgetting/persona_drift` 三段逐项相等；
2. 接线审查通过（`v2/evidence/d25a_wiring_review.md`，链路 + 占位键副作用已排除）；
3. 无在跑批（`pgrep` 空）；
4. C 臂已在手（本件 §2）。

⇒ **A 臂「可跑」。**
