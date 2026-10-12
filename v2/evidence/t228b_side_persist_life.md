# T228b 证据：side storage `persist_vec` + 检索降级标记（life 侧）

> 作者：life-layer-dev ｜ 日期：2026-10-12 ｜ 任务：T228b-side-persist-life（主责）
> 协作：freeze-layer-dev（`freeze/side.py` 契约 + 开关；`f13f108`）、kernel-dev（orchestration 装配点透传）、obs-stats-dev（`N50_VEC=0`）

## 0. sha / 命令

- life 侧提交：**`284e921`**（`life/memory.py` + `life/policy.py` + `life/agent.py` + `config/policy.json` + `tests/test_t228b_persist_vec.py`）
- 相关：freeze `side.py` 契约 `6ed6a4c` / 实测证据 `f13f108`；08 登记 `7708b88`（engine/kernel 侧）
- 装配透传（本 commit）：`orchestration/integration.py::_do_memory` retrieve 分支 → `_emit_assembled`（透传 `_PASSTHROUGH["MEMORY_RETRIEVE"]`）

```bash
cd code && python -m pytest tests/test_t228b_persist_vec.py -q      # 5 passed
cd code && python -m pytest tests -q                                # 409 passed
cd code && python -m pytest life/tests -q                           # 52 passed
cd code && python -m pytest tests/test_freeze.py -q                 # 60 passed
```

## 1. 设计（对齐 freeze 契约）

- **开关**：`config/policy.json` → `life.memory.persist_vec`（**默认 `true`=行为不变**），life 经 `life/policy.py::persist_vec_enabled()` 读（**不 import engine**）；env **`N50_VEC`**（`0/false/no/off`→关）覆盖。
- **`SideStore`**：`__init__(root, persist_vec=None)`；`None`→读 policy。`write` **正文 `.txt` 必写**（#10 数据资产），`.vec` **仅当 `persist_vec` 才写**。`read_embed` 缺失 → **返回 `None`**（显式，不抛不静默）。
- **检索降级**：`AssociativeMemory.score_and_rank` 对**无向量**的节点改用**词面重叠（lexical）**，并置 `debug.vec_available=False` / `retrieval_mode="lexical"`。
- **字段名单一来源**：`life/agent.py::_retrieve` 用 **`freeze.side.degradation_marker(...)`** 把 `vec_available`/`retrieval_mode` 写进 `INTENT.MEMORY` payload（不另拼名字）；`MEMORY_RETRIEVE` 事件侧由 kernel 透传（见 §4）。

## 2. 单测（`tests/test_t228b_persist_vec.py`，5 passed）

默认落 `.vec` / 关闭不落且 `read_embed→None` / 正文必留 / policy 默认 True + override + env / 无向量→`lexical`+标记 / 有向量→`vector`。

## 3. 实测（离线，N=3×20，seed=7）

| 侧 | side 文件总数 | `.txt` | `.vec` | `MEMORY_RETRIEVE` | 事件带标记 |
|---|---|---|---|---|---|
| `persist_vec=ON`（默认） | 643 | 276 | **276** | 60 | **(vec_available=True, retrieval_mode=vector)** |
| `persist_vec=OFF` | 367 | 276 | **0** | 60 | **(False, lexical) + (True, vector)** |

- **`.vec` 276→0；side 文件总数 643→367（−43%）** → 直接消掉 N=50 的 inode 大头（与 freeze `f13f108`：239→143 / inode −43% 同向）。
- **正文 `.txt` 两侧相同（276）** → 只"少文件"，**不丢数据资产**。
- **反向验证**：`read_embed→None`（单测 + 实测）。
- **行为不变**：两侧 `final_state_hash = sha256:de0ab9a…` **相同**、`replay_parity=True`（OFF 只少 `.vec` 文件 + 只加标记字段）。
- OFF 的标记含 `(True, vector)` 属**预期**：某回合记忆为空（`nodes` 无节点）时无向量可选，未触发降级——非静默、可从日志逐条读出。

## 4. ✅ 已达成：降级标记**到达事件**（orchestration 装配透传）

- **修复**：`code/orchestration/integration.py::_do_memory` 的 `op=="retrieve"` 分支由**固定字段 `_emit`** 改为 **`_emit_assembled`**，按已在 `_PASSTHROUGH["MEMORY_RETRIEVE"]` 声明的契约透传 `vec_available/retrieval_mode/query_digest`；未知字段落 `DROPPED{unknown_intent_field}`，**不静默丢**。
- **实测**：`MEMORY_RETRIEVE` **60/60** payload 现带 `vec_available`/`retrieval_mode`（OFF 含 `(False,lexical)`）；`DROPPED(MEMORY_RETRIEVE)` = **0**。
- 工作区 `life/tests/support/mini_kernel.py` 的 retrieve 透传**已同口径**（并入 persona T233 commit）。
- **归属**：装配点属 kernel/orchestration；本次由 life-layer-dev 落最小一行（回到既有契约），已同步 kernel-dev。

## 5. 未验证 / 遗留

- 【未验证】N=50 真跑批的 inode 与文件数（本环境按 N=3 实测 + freeze N=3 侧证；N=50 由 obs 侧 `N50_VEC=0` 跑批）。
- 指纹：`policy.json` 在 `FINGERPRINT_FILES`（全文哈希）→ `persist_vec` 开关**自动进指纹**，无需另接（freeze 侧复核一致）。
