# T228 证据：side 分档（`.txt` 留 / `.vec` 可关）+ inode 实测

> 作者：freeze-layer-dev ｜ 日期：2026-10-12 ｜ freeze 侧代码 commit `6ed6a4c`
> 相关：life 侧 `SideStore.persist_vec`（life-layer-dev）；`mkdtemp` 修复归 kernel-dev（T232）。

## 1. 方法（仅 `/tmp`，不触网，不改 `code/`）

- 运行时 monkeypatch `life.memory.SideStore`，注入 `persist_vec=True/False`，各跑一次小 run（`build_world(seed=42, n=3)` + 20 回合），**统计 side 目录文件数与 inode 增量**。
- 探针：`/tmp/t228_inode_probe.py`；命令：`python3 /tmp/t228_inode_probe.py`。
- 开跑前查 `df -h`/`df -i`（inode 危机期间，错峰执行）。

## 2. 实测结果（N=3 × 10 回合）

| 指标 | `.vec` 关 | `.vec` 开 | 差值 |
|---|---|---|---|
| side 文件总数 | **143** | **239** | **−96** |
| `.txt` | 96 | 96 | 0（正文必留 ✓） |
| `.vec` | **0** | **96** | **−96** |
| inode 增量 | **151** | **263** | **−112（≈−43%）** |

- **反向验证**：关 `.vec` 时 `<id>.vec` **不落盘**；`SideStore.read_embed(ref)` → **`None`**（显式信号，非静默失败）。
- **结论**：关 `.vec` 使 side 文件 ≈**减半**（记忆类 192→96），inode 增量 **↓约 43%**（其余为 freeze_cache 等）。与"`.txt`+`.vec` 双成因"预期一致。

## 3. ⚠️ 发现一处**降级标记未到达事件**（life/engine 侧，需修）

- **已就位**：`life/agent.py::_retrieve` 用 `freeze.side.degradation_marker(...)` 把 `vec_available/retrieval_mode` **写进 intent payload**；`life/memory.py::score_and_rank` 产出 `debug.vec_available`。
- **缺口（实测）**：真实 run 的 **`MEMORY_RETRIEVE` 事件 payload 里没有** `vec_available/retrieval_mode`——
  - 关 `.vec` 跑 20 回合：`MEMORY_RETRIEVE` = 60 条，`(vec_available, retrieval_mode)` 分布 **`{(None,None): 60}`**。
  - 样本 payload：`{"agent_id","query_id","top_k","selected_mem_ids","scores","weights","tie_order"}` —— **无降级字段**。
- **推断**：intent → event 的**装配点用了固定字段白名单**，把 additive 字段丢了（grepper 未在 `engine/`/`life/hooks/` 命中 `query_id`/`selected_mem_ids` 装配 → 装配点在别处或内核 intent 处理里）。
- **影响**：**"关 `.vec` 时检索降级可见"这条验收未达成**（当前只"少文件"，未"事件可见"）。**不是 freeze 的问题**（freeze schema/helper 已就位），需 **life/engine 侧让 emitter 透传这两个 additive 字段**。

## 4. 结论 / 待办

- ✅ freeze 侧（开关契约 + 降级 schema + 指纹）与 **inode 实测（−43%）** 完成。
- ⚠️ **待 life/kernel 修**：让 `MEMORY_RETRIEVE` 事件透传 `vec_available/retrieval_mode`（否则降级不可见）。已通知 life-layer-dev。
- 【未验证】N=50 绝对量级（未跑，inode 危机期避免占用）；机制在 N=3 已验证。
