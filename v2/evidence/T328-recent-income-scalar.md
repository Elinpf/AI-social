# T328③ · `recent_income` 标量累加器（读路径优化）

**日期** 2026-10-13 · **作者** kernel-dev · **树基线** = 含 `T330`（`fc412a8`）
**范围**：本单只剩 ③（② `GROUP_*` 已按 Leader 08:55 裁定不做）。

## 0. 结论

- **逐条等价**（含**反向验证**）、**`state_hash` 不变**；
- **实测**：**N=50×12 cProfile 127.16s → 99.16s ≈ −22%**（同口径：N=50×12、单进程 cProfile、**非通用乘数**）；`recent_income` **跌出 top-10**。
- **不新增 config 键、不改 `state_hash`、不改指纹** ⇒ 无需重冻。
- **与 T330 对照树的先后**：本项构建在 **`T330` 之后**（`fc412a8`），故 **T330 的 `252→127s` 归因于「可见性回退修复」，本项的 `127→99s` 归因于「recent_income 标量」**（两条可比、各自可归因）。

## 1. 改动

- `engine/state.py`：新增派生字段 `income_net`（`agent -> {round -> net流入}`；不入 `state_hash`）。
- `engine/event_acc.py`：`note_event` 累加 `income_net`（`_note_income`，**复用 `liquidity._INCOME_TX_TYPES`/`_EXCLUDE_FLAGS`** = I_eff 口径）；`rebuild` 同步清空/重建。
- `engine/liquidity.py::recent_income`：由「窗口逐回合遍历 `event_index`」改为**读 `income_net` 窗口求和**；docstring 标注「与 I_eff 同 filters，改动需两处同步」。
- `tests/test_t328_income_acc.py`：逐条对拍（多窗口参数）+ 反向验证 + `state_hash` 不变 + live==replay。

## 2. 等价证据（先证后改）

- **逐条**：对每个 `(round × agent × 窗口∈{12,4,1})`，`liquidity.recent_income` == 参考全扫实现（差异 0）✓
- **反向验证**：人为把 `income_net` 改成"自洽但错误"（+1000）⇒ 消费点输出**随之改变**（测试对坏输入变红）✓
- **`state_hash` 不变**：清空 `income_net` 前后相等 ✓；**live 累加器 == replay 重建** ✓
- `code/tests`：**523 passed**（T330 后 519 + 本项 4）。

## 3. 时间实测（同口径 对照）

| 树 | N=50×12 cProfile 总时间 | `recent_income` |
|---|---|---|
| T327（回退未修） | 252.05 s | 15.2 s |
| T330 后 | 127.16 s | 15.2 s（未动） |
| **+ 本项（③）** | **99.16 s** | **跌出 top-10** |

⇒ ③ 单独：**127→99 ≈ −22%**（口径：**N=50×12、单进程 cProfile、非通用乘数**）。
累计（T327→now）：**252→99 ≈ −61%**。

## 4. 复现

```bash
cd social-experiment && ulimit -v 16777216 && cd code && export N50_VEC=0
python -c "from engine.liquidity import recent_income; ..."   # 见 tests/test_t328_income_acc.py
python -m pytest tests/test_t328_income_acc.py -q
```

## 5. 边界

- **不新增 config 键**；不改事件顺序/判定/`state_hash` ⇒ **无需重冻**（如实：设计为 no-op，且实测 `state_hash` 同）。
- 与 T330 对照树关系见 §0/§3。
