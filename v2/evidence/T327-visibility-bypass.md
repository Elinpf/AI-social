# T327 · `contracts/visibility.*` 为何仍居 N=50 首 —— 调用路径定位（只读）

**日期** 2026-10-13 · **作者** kernel-dev · **sha** `31e00a6` · **性质** 只读定位（未改码）
**依据** T324 cProfile（N=50×12）：`visible_events 31s / visible 21s / _group_members 16s / location_of 7.5s`

## 0. 结论（先给）

**绕过点 = `life/settlement.py::write_memories`（L6）**：
它**每 agent 每回合**把 `state.event_index` **新 `list(...)` 物化一份**，再调 `life.visibility.visible_events`；
而 **T264 增量索引 provider 是按 `id(engine.ledger.records)` 注册**的 ⇒ **`id` 不匹配 ⇒ 100% 回退 `contracts.visible_events` 全扫**（每次还重算 `_group_members`+`location_of`）。
**这正是"索引建了、但某条路径绕过它"的形态。**

**证据（只读探针，N=20×5）**：包一层 `life.visibility.visible_events` 统计 `id(records) in _INDEXES`：
```
provider HIT= 0   FALLBACK(full-scan)= 100     # 恰 = N(20) × rounds(5)
miss examples (type,len): [('list', 590), ('list', 590), ('list', 590)]   # 每次新 list
```
⇒ **life 侧可见性调用 100% 走全扫**；调用次数 `= N×rounds`，与 cProfile 里 `visible_events ncalls=605(=50×12)` 吻合。

## 1. 调用点清单（逐点判定）

| # | 文件:行 | 调什么 | 是否该走索引 | 判定 |
|---|---|---|---|---|
| 1 | `life/settlement.py:576-583` | `from .visibility import visible_events`，传**新建 list** | **应走**（已注册索引） | ⚠️ **绕过**（id 不匹配 → 全扫）|
| 2 | `life/visibility.py:12,20` | 委托 `contracts.visibility`（provider 命中则走索引） | 应走 | 机制本身正确；**问题在调用方传的对象** |
| 3 | `engine/perceive.py:43,90` | `contracts.visible_events` | 视调用方 | life 运行**未走此路**（探针 0 命中不代表此路；此路主要给 mini_kernel/tests/obs）|
| 4 | `orchestration/integration.py:296`（`visibility_query`）| `self._vindex.visible`（**T264 索引**） | 应走 | ✓ **正常**（adapter.perceive 路径） |
| 5 | `life/agent.py:765` `_maybe_accept_offers` | 读 `wv.visible_events`（来自 **adapter.perceive**） | 应走 | ✓ 正常（非直接调 contracts）|
| 6 | `obs/metrics_social.py:50` `_group_members` | **obs 自有** helper（非 contracts） | 离线只读 | ✓ 不属本问题 |

## 2. 为什么绕过（根因）

- T264 索引 provider 注册键 = **`id(engine.ledger.records)`**（`orchestration/integration.py` 把 `adapter.visibility_query` 注册到 `engine.ledger.records`）。
- `write_memories` 取的是 **`st.s["event_index"].values()` 并 `list(...)`** ⇒ **每次都是新 list 对象** ⇒ `id` 永不命中 ⇒ 回退全扫。
- 且 `contracts.visible_events` **每次调用**重算 `_group_members(records)`、`location_of` ⇒ 放大了 `_group_members(16s)`/`location_of(7.5s)` 两项。

## 3. 最小修法建议（**不实施**，交 Leader 排期）

**方案 1（架构正解，与 T319 同路·推荐）**：orchestration 经**既有 port 缝**提供
`visible_events(agent_id, upto_round, window_rounds=None) -> list`（内部走 `adapter.visibility_query` / T264 索引）；
`life/settlement.write_memories` 改调 `self.kernel.visible_events(...)`（去掉自建 list + 全扫）。
- 与 `T312` 的 `round_events` 同构；**life 不 import engine** 的约束保持。
- **预计收益**：消除 `N×rounds` 次全扫 → 直接砍掉 T324 cProfile 里 **`visible_events 31s + visible 21s + _group_members 16s + location_of 7.5s ≈ 76s/252s ≈ 30%`**（N=50×12 口径；非通用乘数）。

**方案 2（最小改动·次选）**：orchestration 注册 provider 时**额外按 `id(engine.state.event_index)` 注册**；`write_memories` **直接传 `st.s["event_index"]`（dict）**、`life.visibility` 兼容 dict（`records.values()`）⇒ 命中同一 dict 的 id。
- 风险低但**把"按对象身份注册"的脆弱性留在接口里**（未来再改 state 结构又会破）；**方案 1 更干净**。

## 4. 复现

```bash
cd social-experiment && PYTHONPATH=code python -c "
import life.visibility as LV; orig=LV.visible_events; s={'h':0,'m':0}
def w(r,a,u,window_rounds=None,*,location=None):
    s['h' if id(r) in LV._INDEXES else 'm']+=1; return orig(r,a,u,window_rounds,location=location)
LV.visible_events=w
from orchestration.integration import build_world
e=build_world(seed=42,n=20)['engine']
for i in range(5): e.run_round(i)
print('HIT',s['h'],'FALLBACK',s['m'])"
# 期望：HIT 0, FALLBACK 100
```
sha `31e00a6`。**只读、未改 `code/`。**
