# (B) 批状态三态可视（T348 扩展；⚠ 非 T375——T375 是"轨迹页模型行按居民"口头排期）（治"跑完没人看见"，前端只做"可被看到"）

**背景**：`T355` 17:49 已完、19:40 才被发现，全员白等 1h50m。Leader 裁定：(A) 现成即可用；(B) 做三态角标，但**优先读既有真源、不自造第二真源**；"主动报"仍归 owner（`T374`）。

## 实现（前端 + `serve.py`，不碰世界层、不占重活槽）
- `serve.py::run_info` 读**既有真源** → 三态 `state`：`running / done / failed`，并回传 `rc`：
  - 真源①：`host.log` 的 **`[runner] batch exited rc=N`**（优先，判 done/failed）；
  - 真源②：`meta.json.ended_at`（无 rc 时保守判 done）；`heartbeat.tsv`（进度/末回合）。
  - **不新造真源**；`T374`（release-engineer）的 `END` 标记落地后按其字段对接（先对齐字段名）。
- `main.js`（`?z=live` 顶部）：显 **`批次 <name> · 运行中 / 完成（rc=0）/ 失败（rc≠0）`**；`failed` 时 status **显眼标"⚠ 批失败（rc=N）"** 且停止跟随。

## 实测（真源）
- `t355` → `state=done, rc=0`（`meta.ended_at=17:49:27`）✓；
- 临时夹具 `rc=1` → `state=failed, rc=1` ✓（验证后已删，未污染共享目录）。

## 如何一眼判三态（一句话）
打开 `dashboard.html?z=live&live=<批日志>`，看**顶部 LIVE 条**：
**`批次 X · 运行中`**（还在跑）/ **`批次 X · 完成（rc=0）`**（正常结束，状态变"跟随已结束·可回放"）/ **`批次 X · 失败（rc≠0）`**（⚠ 红字告警）。

## URL（发用户）
- 今天已结束：`http://10.10.136.128:8848/dashboard.html?z=live&live=/root/t271/runs/t355/run.jsonl`
- 正在跑的批（把 `<批>` 换成实际目录名即可）：`http://10.10.136.128:8848/dashboard.html?z=live&live=/root/t271/runs/<批>/run.jsonl`

## 证据
`v2/evidence/T375-batch-status.png`（批次 t355 · 完成（rc=0））。
## 边界
"可被看到"已具备；**"主动报结束"仍归 owner 机制（`T374`）**，本页不替代它。

## 与 T374（`END` 标记）对齐（21:43）
- `serve.py::run_info` **优先读 `<run_dir>/END`**（T374 派生汇总，含 `rc/tree/sha/rounds_last/events/final_state_hash`）→ `end_source="END"`；**不再自造真源**。
- 缺 `END`（如判前旧批 / `SIGKILL` 未写出）→ 兜底 `host.log` 的 `batch exited rc=N` → 再兜底 `meta.ended_at`。
- 实测：`t355`（无 END）→ `state=done, rc=0`（host.log 兜底）；`t374_ok`（有 END）→ `state=done, rc=0, end_source=END, tree/sha/rounds_last/events` 齐全。
