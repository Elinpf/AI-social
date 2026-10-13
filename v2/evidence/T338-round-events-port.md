# T338 · 修 `settlement.events_this_round` 端口"存在但没生效"（T319）

**日期** 2026-10-13 · **作者** kernel-dev · **树基线** 含 T329（`10428f2`）· **性质** 实现（最小面 + 可观测）
**目标语义**：端口**真生效** / 等价 / `state_hash` 不变；**不新增 config 键**。

## 0. 结论

- **端口真生效**：整跑 `port_fallback_count()==0`（原先 100% 回退）。
- **等价**：逐 round×agent，端口产出 == 全扫；`state_hash` 有端口 vs 无端口**相同**。
- **可观测**：无端口（如 mini 内核）⇒ **计数 + 首次 WARN**（不再静默变慢）。
- **实测**：**N=50×12 cProfile 99.16s → 90.82s ≈ −8.4%**（口径：N=50×12、单进程 cProfile、**非通用乘数**）；`events_this_round` 跌出 top-8。
- **是否重冻**：**不需要**（无行为变 + 无新 config 键）。

## 1. 根因（T319 为何"存在但没生效"）

`settlement.events_this_round(..., kernel=ctx)` 走 `getattr(ctx, "round_events", ...)`；但 **`Ctx` 无 `round_events`** ⇒ 恒 None ⇒ 静默回退全扫。

## 2. 改动（最小面 · 已声明）

- `engine/rng.py::Ctx`：新增 `kernel` 字段（默认 None），`at()` 透传。
- `engine/kernel.py`：`Engine.kernel=None`；`run_round` 每回合把 `self.kernel` 写入 `self.ctx.kernel`。
- `orchestration/integration.py::build_world`：`engine.kernel = adapter`（组合根注入）。
- `life/settlement.py`：`_resolve_round_events_port(k)` 解析 `k.round_events` 或 **`k.kernel.round_events`**；不可用 ⇒ `_note_port_fallback()`（**计数 + 首次 WARN**）；导出 `port_fallback_count()`/`reset_port_fallback_count()` 供测试/观测。
  - **显式声明（跨层接口）**：动了 `Ctx`/`Engine`（engine）与 `life/settlement.py`（life 侧小改）+ orchestration —— 与 T330 同法，最小面。

## 3. 等价 + 可观测证据（`tests/test_t338_round_events_port.py`）

1. **真生效**：整跑后 `port_fallback_count()==0`；单 round 端口产出 == 全扫（seq 序一致）✓
2. **逐条等价**（多 round、含 types 过滤）✓
3. **反向验证**：无端口（`ctx.kernel=None`）⇒ **`port_fallback_count()` 递增**（2 次调用 = 2）✓（"端口不可用"**可观测**）
4. **`state_hash`**：有端口 vs 无端口两跑（同 seed）**相同** ✓

`code/tests`：**532 passed**。

## 4. 时间实测（同口径）

| 树 | N=50×12 cProfile | `events_this_round` |
|---|---|---|
| T328③ 后 | 99.16 s | ~3.4 s（top） |
| **+ T338** | **90.82 s** | **跌出 top-8** |

⇒ **99.16→90.82 ≈ −8.4%**（口径：**N=50×12、单进程 cProfile、非通用乘数**）。
累计（T327→now）：**252→90.8 ≈ −64%**。

## 5. 复现

```bash
cd social-experiment/code && export N50_VEC=0
python -c "from life import settlement as S; from orchestration.integration import build_world
w=build_world(seed=42,n=20); e=w['engine']
for r in range(5): e.run_round(r)
print('fallback', S.port_fallback_count())"        # 期望 0
python -m pytest tests/test_t338_round_events_port.py -q
```
