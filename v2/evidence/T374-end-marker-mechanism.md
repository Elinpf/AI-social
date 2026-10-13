# T374 · 跑批结束标记机制（`END` + 尽力通知）—— 验证证据

> **动因**：`T355` **17:49 就 `rc=0`**，直到 **19:40** 才被发现 ⇒ **全员白等 1h50m**。把「跑完即报」从**纪律**变**机制**。
> **范围**：仅 `tools/t271/`（**不动世界层**）。**non-author 复核**：本单**作者不标 completed**，证据绑 sha。

## 1. 实现（两个文件）
- **`tools/t271/t271_end_marker.sh`**（新）：**批体结束后**写固定 `END`（JSON）+ 尽力通知。**幂等**（已存在则跳过，`--force` 覆盖）。
- **`tools/t271/t271_runner.sh`**（改）：加 `EXIT/TERM/INT` trap + 退出前显式调用；**在 `finalize_meta.sh` 之后**（`END` 读到一致的 `meta.ended_at`）。

**`END` 字段**：`rc / started_at / ended_at / rounds_last / events / final_state_hash / tree / sha / workdir / out / host_log`。

**尽力通知（best-effort，不进热路径）**：
- `host.log` 里一行 `[END-MARKER] ...`（**可 grep**）；
- journal：`logger -t t271-end`；
- **固定告警路径**：`/root/t271/alert/last_end.json`（最新）+ `/root/t271/alert/ends.log`（逐条 append）——**周期自检一眼可读**。

**与既有源的关系（不造第二真源）**：`END` 是**派生汇总**（读 `meta.json`/`heartbeat.tsv`/`run.jsonl`），**不改**三者；`meta.ended_at` 仍由 `finalize_meta.sh` 回填。

## 2. 验收（含反向）—— 全部 PASS
证据装置：冻结副本 `git archive HEAD`（`tree=copy`，**不碰主树**）；短批 `N=3×2` mock（各 1–2 s）。

| # | 用例 | 结果 | 证据 |
|---|---|---|---|
| ① | **正常结束**（`N=3×2` mock） | **PASS** | `END.rc=0`、`rounds_last=1`、`events=137`、`final_state_hash=sha256:e6ebf872…` **与 `host.log` 报告一致**；`tree=copy` |
| ② | **人为非 0 退出**（`bash -c 'exit 7'`） | **PASS** | `END.rc=7`（`host.log` `batch exited rc=7`） |
| ③ | **SIGTERM**（`systemctl stop`，`KillMode=control-group`） | **PASS** | `END.rc=143`、`ended_at` 有值（trap 触发） |
| ④ | **不影响批体计时** | **PASS** | marker 对 **133 MB 大日志**（`T350`）耗时 **0.23 s**、RSS 13 MB；且 `host.log` 中**先** `batch exited rc=0` **后** `[END-MARKER]` ⇒ **发生在批体之后**；对照 T350 批体 9998.5 s ⇒ 可忽略 |
| ⑤ | **runbook 一行** | **PASS** | `v2/refs/nightly-pipeline-runbook.md` §3 附近「跑批结束必须主动报」条目 |

### 2.1 ⚠️ 被 kill / 断电类（③ 的边界，**如实**）
- **`SIGTERM` / `SIGINT`**：**能留痕** ⇒ `END` 写出、`rc=143/130`（③ 已证）。
- **`SIGKILL` / 断电**：⚠️ **trap 不触发 ⇒ `END` 不写出** —— **"END 缺失"本身就是异常信号**；此时以 `heartbeat.tsv` 末行（`EXIT`/无）为准。**这是能力边界，非缺陷**，已写入 runbook。

## 3. 复现命令（绑 sha = 见提交信息）
```bash
BIN=tools/t271
# ① 正常
bash $BIN/host_batch.sh --name t374ok --out /root/t271/runs/t374_ok/run.jsonl \
  --workdir /tmp/t271-t374/code --heartbeat 2 --mem-max 2G --meta sha=<sha> \
  -- /opt/openjiuwen/workswarm-venv/bin/python -m orchestration run --life --seed 7 --agents 3 --rounds 2 \
     --out /root/t271/runs/t374_ok/run.jsonl --side-root /root/t271/runs/t374_ok/side --flush-every 1
# ② 非 0
bash $BIN/host_batch.sh --name t374fail --out /root/t271/runs/t374_fail/run.jsonl --workdir /tmp \
  --heartbeat 2 --mem-max 1G --meta sha=<sha> -- bash -c 'exit 7'
# ③ 信号
bash $BIN/host_batch.sh --name t374kill --out /root/t271/runs/t374_kill/run.jsonl --workdir /tmp \
  --heartbeat 2 --mem-max 1G --meta sha=<sha> -- bash -c 'sleep 120'   # 随后 systemctl stop t271-t374kill
# 断言
cat /root/t271/runs/t374_ok/END
```
