# T376 · 非作者独立核：`T374` 跑批 `END` 标记机制（含 `SIGKILL` 负例）

- **复核人**：sandbox-test-lead（**非作者**）｜ 作者：release-engineer（`cd336a8`）
- **装置**：**冻结副本**（`git archive HEAD` → `/tmp/t376_src`，`tree=copy`）+ **直接跑 `t271_runner.sh`**（不经 systemd）；**告警目录隔离** `T271_ALERT_DIR=/tmp/t376_alert`；**不碰主树、不写 `/root/t271`**。
- **脚本**：`v2/evidence/t376_end_marker_verify.sh`（N=3×2 mock 短批；轻量）

---

## 结果（5/5 PASS）

| # | 用例 | 期望 | 实测 |
|---|---|---|---|
| ① | **正常 `rc=0`** | `END` 数字与 `host.log` 一致 | **PASS**：`rc=0`；`events=137` == host `[life] … events=137`；`final_state_hash=sha256:e6ebf872…` == host `conservation_ok…final_state_hash`；`rounds_last=1`；`tree=copy`；`sha` 透传 |
| ② | **非 0**（`exit 7`） | `END.rc=7` | **PASS**（`END.rc=7`） |
| ③ | **`SIGTERM`** | `END.rc=143` | **PASS**（`[END-MARKER] … rc=143`，trap 留痕） |
| ④ | ⚠️ **`SIGKILL`** | **`END` 不写出** ⇒ "缺失=异常" | **PASS**（`kill -KILL` runner ⇒ **无 `END` 文件**） |
| ⑤ | **marker 在批体之后** | `host.log` 先 `batch exited` 后 `[END-MARKER]` | **PASS**（行 8 `batch exited rc=0` < 行 9 `[END-MARKER]`） |

**原始证据（节选）**：
```
① END: {"rc":0,"rounds_last":1,"events":137,"final_state_hash":"sha256:e6ebf872…","tree":"copy","sha":"…"}
   host.log: [life] … events=137 ; conservation_ok=True final_state_hash=sha256:e6ebf872…
             [runner] batch exited rc=0
             [END-MARKER] batch=t376ok rc=0 ended=… rounds_last=1 events=137 fsh=sha256:e6ebf872…
③ [END-MARKER] batch=t376term rc=143 ended=…（SIGTERM 触发 trap ⇒ END 写出）
④ SIGKILL：END 缺失（trap 不触发）
```

## 口径/边界（认同作者，如实标注）

- **`SIGKILL`/断电**：trap 不触发 ⇒ **`END` 不写出** ⇒ **"`END` 缺失本身 = 异常信号"**（不得当"还在跑"）；以 `heartbeat.tsv` 末行为准。**能力边界，非缺陷** ✓。
- **不影响计时**：`t271_end_marker.sh` 只在**子进程退出后**调用、只读日志**尾部 ≤1MB**；`host.log` 顺序证实**在批体之后** ✓（作者另测 133MB 日志耗时 0.23s，我以顺序+实现佐证）。
- **不造第二真源**：`END` 为**派生汇总**（读 `meta.json`/`heartbeat.tsv`/`run.jsonl` 尾）✓。

## 结论

**可采信**：`T374` 的 `END` 机制在 ①正常/②非0/③`SIGTERM`/④`SIGKILL`（缺失=异常）/⑤批体之后 五项**均成立**；**无独立发现的反例**。

*（T376 非作者独立核 — sandbox-test-lead；按规矩不自标 completed，等 Leader 复核）*
