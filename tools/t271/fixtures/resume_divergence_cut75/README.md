# frozen 负向夹具：native resume vs oneshot 的 **pre-fix** 分歧（cut=75）

> 用途（T311）：作为 **“must-be-red” 夹具**，使 `T299` 语义一致门在**真实数据**上仍可断言「**能报红**」——
> 不只靠合成样本的 `--selftest` REVERSE 扰动。原因：`T298`(`7f16c80`) 修好后，**current HEAD 上 `cut=75/89` 均已绿**，
> 真实阳性消失 ⇒ 必须冻结一份 **pre-fix** 分歧对，使「门能报红」可复验。

## 来源（诚实溯源）

- **pre-fix sha = `7f16c80^` = `88c45d4`**（`7f16c80` = life 的 `T298` 修复：`restore()` 补 `_comm_slot` 与 T244 前向态）。
- **原归档曾被误删**：`/root/t271/runs/repro/`（release 的产物目录）在 T305 收尾清理时被 sandbox-test-lead 误删
  （已按团队规矩「删除前先确认归属/是否被依赖」立规）。
- **本夹具由上述钉死 sha 重新生成**（命令见下），**内容一字未改**。

## 文件

| 文件 | 含义 | 世界语义投影 sha256 |
|---|---|---|
| `oneshot.jsonl` | pre-fix **一次性跑**基准 | `8820493fd8d219389e1736e609960eced8380263b8d4cc881e0d1f3ec4f07558` |
| `resume.jsonl`  | pre-fix 从 `TURN_SEAL@75` **续跑** | `110840b768ef7668ff51e2f4895c7343ee9fb351fa55a40c77871caf7431a017` |

- 两者**必须不等**（当前实测：`state_hash 不等数=74`、首个不等 `round=76`）。这与 release
  `v2/evidence/T299-semantic-equality-gate.json` 的 `cut75_true_divergence` 记录**逐值同源**。

## 重新生成命令（若需重建）

```bash
cd <repo>
PRE=$(git rev-parse 7f16c80^)      # = 88c45d4
rm -rf /tmp/t271-repro             # 防 repro_resume_cut.sh 复用陈旧副本（其 CO 目录按存在性判断、无视 SHA）
T271_REPRO_SHA=$PRE bash tools/t271/repro_resume_cut.sh 75
# 产物：/root/t271/runs/repro/ref.jsonl(=oneshot)  run_1.jsonl(=resume)
```

装置前提：**分进程** / 脚本内**先 warm** / **固定 prefix 截断**（非墙钟 kill） / **sha 固定**。

## 交叉引用（另一 pre-fix 实例，备胎，**非本夹具来源**）

release 另存 `/root/t271/runs/cut/{run_89_1(≈oneshot), run_75_1(resume)}`
（sem `172669467a…` vs `9e2534bb…`）—— 另一次运行实例，语义同样「不等」，可作备胎。

## 检查

```bash
bash tools/t271/negative_fixture_check.sh    # 断言本夹具两文件语义投影【不等】(must-be-red)
```
