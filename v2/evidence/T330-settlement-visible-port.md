# T330 · settlement 可见性走 T264 索引端口 —— 等价证明 + 重测

**日期** 2026-10-13 · **作者** kernel-dev · **性质** 实现（只动最小面）
**目标语义** = **【无行为变（等价）】**；**不新增 config 键**。

## 0. 结论

- **等价成立**：端口/provider 产出与**全表扫逐条一致**（seq 序一致，多 seed 抽验）；`state_hash` **相同**；`settlement.write_memories` 产出（OBSERVATION 目标集）**provider == 强制全扫**。
- **命中修复**：只读探针 N=20×5：`life.visible_events` **HIT 100 / FALLBACK 0**（修复前 **0/100**）。
- **重测节省**：**N=50×12 cProfile 252.05s → 127.16s ≈ −49.6%（≈2.0×）**（口径：N=50×12、单进程 cProfile、**非通用乘数**）；`contracts.visibility.*` **全部跌出 top-12**。
- **是否需重冻**：**不需要** —— 无行为变 + **不新增 config 键**（“设计为 no-op”且**实测 no-op**：`state_hash` 同、事件等价）。

## 1. 改动（最小面）

- `life/visibility.py`：`visible_events(records, …)` **兼容 `dict`**（`{seq:rec}` → `values()`）；provider 仍按**传入对象 `id`** 命中（故调用方须传**稳定对象**）。
- `life/settlement.py::write_memories`（L6）：`records = st.s.get("event_index", {})` —— **不再 `list(...)` 新建对象**。
- `orchestration/integration.py`：`build_world` **再按 `engine.state.event_index`（dict）身份** `register_index(...)`；`run_e2e` finally 相应 `unregister`。

（**未**改 `life/ports.py`：见 §5 —— 原方案 1 的 `KernelPort.visible_events` 更"正"，但 hook 契约 `fn(state, round_no, ctx)` **拿不到 kernel**，需额外把 kernel 透传进 ctx（属 engine/life 接口改动）；本项取**同效的最小面**。）

## 2. 等价证明（先证后改）

`tests/test_t330_settlement_visibility_port.py`（4 项）：
1. **provider 命中**：`id(state.event_index) in _INDEXES` ✓；
2. **逐条等价**（每个 round × agent）：`LV.visible_events(state.event_index, aid, r)` 的 seq 列表 **==** `contracts.visible_events(list(values), …)` ✓；
3. **多种子抽验**（seed 1/7/42）：逐条相等 ✓；
4. **settlement 产出等价**：`write_memories` 在"走 provider" vs "强制全扫（清空索引）"下 OBSERVATION `(observer, target_event_seq)` **逐条相同** ✓；**`state_hash` provider vs fallback 相同** ✓。

未发现"索引与全扫集合不同 / `location=None` 语义差" ⇒ **未达标即停**未触发。

## 3. 复测节省（同口径）

| | T327 profile | T330 后 |
|---|---|---|
| N=50×12 cProfile 总时间 | **252.05 s** | **127.16 s** |
| `dict.get` | 72.4 s | 24.6 s |
| `contracts.visibility.*` | visible_events 31.4 / visible 21.2 / _group_members 16.1 / location_of 7.5 | **全部跌出 top-12** |

⇒ **−49.6%（≈2.0×）**（口径：**N=50×12、单进程 cProfile、非通用乘数**）。

**⭐ 意外发现（供排期）**：`life/settlement.py::events_this_round` **仍在 top（3.4s）** —— 它 T319 走 `kernel=ctx`，但 **`Ctx` 无 `round_events`** ⇒ **回退全扫**。即 **T319（life 端口）当前也"存在但没生效"**；修它需把 kernel/端口透传进 `ctx`（engine↔life 接口，另案）。

## 4. 复现

```bash
cd social-experiment && PYTHONPATH=code python -c "
import life.visibility as LV; o=LV.visible_events; s={'h':0,'m':0}
def w(r,a,u,window_rounds=None,*,location=None):
    s['h' if id(r) in LV._INDEXES else 'm']+=1; return o(r,a,u,window_rounds,location=location)
LV.visible_events=w
from orchestration.integration import build_world
e=build_world(seed=42,n=20)['engine']
[e.run_round(i) for i in range(5)]
print('HIT',s['h'],'FALLBACK',s['m'])"       # 期望 HIT 100 FALLBACK 0
```

## 5. 未做/边界（诚实）

- **未按方案 1 的 `KernelPort.visible_events` 签名**（改走"按 `event_index` 身份注册"的同效最小面），原因见 §1 括注（hook 无 kernel）。
- **未碰** `life/persona_drift.py` / `agent.py` / `config/life_v2.json`（T323 WIP）✓。
- `T328③`（`recent_income`）**已暂存未提交**（保对照树一致）；`recent_income 15.2s` 仍在（待 T328③）。
- `make verify` 全绿（见提交）。
