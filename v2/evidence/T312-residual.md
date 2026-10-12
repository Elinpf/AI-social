# T312①：`wake.compute_wake_set` 主循环读路径优化（+ 跨层只读端口 `round_events`）

**日期** 2026-10-13 · **作者** kernel-dev · **依据** T295（`a0785fe`）/ T285 spike / 08 §5.9
**scope**：读路径优化；**不动事件顺序/判定/`state_hash`**；验收 = 增量表 == 全表扫 逐条等价。

## 1. 改动

- `engine/wake.py::compute_wake_set`：主循环由「跨全历史扫 `event_index.values()`（`seq>floor`）」改为
  **从 `floor` 所在回合起、按 `event_acc.seqs_of_round` 迭代**（不再触碰无关历史）。
  语义不变：候选 seq **全序（升序）**、过滤条件 `seq>floor` 不变。
- `orchestration/integration.py::KernelAdapter.round_events(round_no, types=None)`：**新增跨层只读端口**
  （life 经 `KernelPort` 调用，**life 不 import engine**）；内部 `engine.event_acc.recs_of_round`
  ⇒ **seq 升序、顺序不变**；`types=None`=全部、`types=(t,...)`=过滤。**方案 A（既有 port 缝）**。

## 2. 逐条等价对拍（`tests/test_t312_wake_acc.py`，4 项）

- **候选 seq 集/序** == 原「全 `event_index` 扫 + `seq>floor`」（逐条相等）✓
- W6（同场所）候选来源与参考全扫一致 ✓
- **`state_hash` 不变**（清空派生表前后相等）✓
- **`KernelAdapter.round_events`** == 全表扫逐条等价（逐 round、含 types 过滤、seq 升序）✓

`code/tests` 全量：**504 passed**。

## 3. 时间实测（N=10×30，启用 wake，15,253 事件）

`compute_wake_set` 对 round 15..30 ×20：

| | 耗时 |
|---|---|
| 累加器（可信） | **0.047 s** |
| 强制全扫（`acc_trusted=False`） | **3.551 s** |
| **加速** | **≈ 76.1×** |

（注：`wake` **默认 `policy.wake.enabled=false`**；实测显式启用后基准，与 D9"默认 ON"的活路径口径一致。）

## 4. 跨层接口（供 T319/life，已在频道发布）

```python
def round_events(self, round_no: int, types: tuple | None = None) -> list[dict]: ...
# seq 升序、原始只读记录；types=None⇒全部，types=()⇒空
```

## 5. 边界

- **不新增 config 键、不改指纹** ⇒ 不影响 T300 重冻。
- `life/settlement.events_this_round` 属 **life 域**，**移出 T312**（Leader 已开 `T319`，`depends_on: T312`）；本任务只交付 engine/orchestration 侧。
