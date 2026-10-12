# T228 · side 存储分档（`.txt` 留 / `.vec` 可关）—— freeze 侧交付 + 反向验证

> 作者：freeze-layer-dev ｜ 日期：2026-10-12 ｜ 任务：T228（freeze 侧主责：嵌入能力 + 降级 schema + 指纹）
> 协作：life-layer-dev（`SideStore.persist_vec` / 检索降级 honored，`284e921`）、kernel-dev（事件透传，**进行中**）
> 相关：T232（side-root 异常路径泄漏）已由 `c7d8edf` 修复。

---

## 0. sha / 命令（本次验证）

- 验证基线 **HEAD = `284e921`**（含 life 的 T228b）。
- 复现命令：
```bash
cd <repo>/social-experiment && echo "HEAD=$(git rev-parse --short HEAD)"
python3 /tmp/t228_check.py   # 见 §3（N=3×20, seed=7, 逐档 build_world + 计数）
```

## 1. freeze 侧交付（我的部分，已提交 `6ed6a4c` / `f13f108`）

`code/freeze/side.py` —— side 分档的 **freeze 落点契约**：
- `PERSIST_VEC_ENV="N50_VEC"`：`"0/false/no/off/none/空"` → 关；缺省 **True（行为不变）**；`resolve_persist_vec()` 解析。
- `degradation_marker(vec_available, retrieval_mode)`：构造挂 **`MEMORY_RETRIEVE`** 的**显式降级标记**
  （`vec_available: bool` + `retrieval_mode ∈ {"vector","lexical"}`）——**只增字段（X1）**，依据 `08 §1.2 E`。
- `embed_for_side(text, provider, persist_vec=...)`：**「可产 / 可不产 `.vec`」的嵌入能力**
  （`persist_vec=False` → `vector=None, vec_available=False, retrieval_mode="lexical"`）。
- `side_fingerprint(persist_vec)`：指纹片段。

**默认行为不变**：`N50_VEC` 缺省 = True；life 侧 `SideStore` 缺省落 `.vec`（见 §3 实测）。

## 2. 指纹（要求「新开关进指纹」）—— ✅ 满足

- 开关落在 `config/policy.json` 的 `life.memory.persist_vec`（默认 `true`）。
- `engine/version.py::FINGERPRINT_FILES` **包含 `policy.json`**，且 `component_digests()` 对每个文件做**全文 `hash_obj`**
  → **开关值一变，`engine_version` 指纹即变**（“默认关 ≠ 没影响”）。
- （`freeze/side.side_fingerprint` 为显式片段 helper；当前由 policy.json 全文哈希覆盖，无需另接。）

## 3. 反向验证：`.vec` 开/关 inode 实测（HEAD `284e921`）

同一小 run（**N=3 × 20 回合，seed=7**），逐档设 `N50_VEC`；计 `side/mem/**` 下文件数：

| 档 | `N50_VEC` | `.txt` | `.vec` | 总文件 | `MEMORY_RETRIEVE` | 事件带降级标记 |
|---|---|---|---|---|---|---|
| **默认（无 env）** | （未设） | 276 | **276** | **552** | 60 | **0** ⚠️ |
| 显式 ON | `1` | 276 | 276 | 552 | 60 | 0 ⚠️ |
| **OFF** | `0` | 276 | **0** | **276** | 60 | 0 ⚠️ |

- ✅ **默认不变**：默认与显式 ON 一致（552）。
- ✅ **反向验证**：关 `.vec` → 总文件 **552 → 276（−50%）**，**`.txt` 两侧相同（276）** → 只省派生文件、**不丢数据资产**。
- ❌ **未达成**：`MEMORY_RETRIEVE` 的 `vec_available/retrieval_mode` **仍未到达事件**（`event_marked=0/60`）。

## 4. ⚠️ 唯一未达成项：降级标记未达事件（归属 **kernel/orchestration**，非 freeze）

- life 侧 `life/agent.py::_retrieve` **已**把 `freeze.side.degradation_marker(...)` 写进 `INTENT.MEMORY` payload；
- 但装配点 `code/orchestration/integration.py::_do_memory`（`op=="retrieve"`，~L447–452）**用固定字段 dict**，
  把这俩 additive 字段**静默丢弃** → 事件里看不到降级。
- **归属**：kernel 侧（已直连 kernel-dev）。**此点未达成前，T228 的“检索降级显式可见”不成立**（与 Leader 口径一致）。

## 5. 结论

- freeze 侧（嵌入能力 / 降级 schema / 开关 / 指纹）**完成并验证**；life 侧 `SideStore` honors 开关**完成并验证**（−50% 文件、默认不变）。
- **T228 整体未关闭**：卡在 **kernel `_do_memory` 透传**（不静默丢 additive 字段）。kernel 落地后需复验 `event_marked>0` 再关闭。
