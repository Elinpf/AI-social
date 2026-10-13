# T370 · 非作者独立核验计划：`T355` 收口（第四次重冻）

- **复核人**：sandbox-test-lead（**非作者**）｜ 被核：`T355`（`obs-stats-dev`，主树 `1d3af8c`）
- **前置门（硬）**：等 `T355` 跑完 + `obs` 出收口产物 + Leader 广播；**之前只写脚本、不跑重活**。**不自标 completed。**
- **脚本（已就绪）**：`v2/evidence/t370_attribution_verify.py`、`v2/evidence/t370_matrix_separability.py`

## 比对口径
- **OLD（上一基线）**：`/root/t271/runs/t300/run.jsonl`（第三轮 `v2-T300`）
- **NEW**：`/root/t271/runs/t355/run.jsonl`
- ⚠️ **跨 epoch**：`time_model`/`world_model` 变动 ⇒ 只核**归因内部算数与逻辑自洽**，不重下结论（`T349` 同规）。

## 五项（解冻后逐条给命令 + 原始输出）

### ① 事件数归因逐项复算 + 算数闭合
`python3 v2/evidence/t370_attribution_verify.py [OLD] [NEW] [EXPECTED.json]`
- 自建 `Counter(type)` 统计，报全族 delta；**验 Σ逐族Δ = 行数差（无残差）**；
- 对账作者清单（`EXPECTED.json` 由 `T355-refreeze.md` §6 提取）；
- **区分"可隔离 vs 仅机制解释"**（仿 `T349`：如族替换/字段增归可隔离，指纹变⇒cache 全 miss 的漂移归机制）。

### ② 四档分类合规（人工核，脚本给数）
逐项核：`行为变` / `仅日志增行・字段增（链变、state_hash 不变）` / `仅指纹变` / `无行为变`；
⚠️ **不得把"仅字段增/链变"写成"行为变"**，也不得反向掩盖。（对齐 `T360`/leader 16:30 的四档口径。）

### ③ 多 sha 分开记 + 字节一致
- **sha 分列**：世界层 sha / 记录 HEAD sha / 计算基线 `obs` 代码 sha（各 `git rev-parse` / `sha256_16`）；
- **字节一致**：对**旧 log** 用**新代码**重算 → 与 `archive/*_pre_t355` 存档比：`ADDED=[新增字段]/REMOVED=[]/CHANGED=[]`，`diff` 仅现新增字段（`T300` §4 同法）。

### ④ 2×2 矩阵可分离性（**独立判断**）
`python3 v2/evidence/t370_matrix_separability.py MATRIX.json`
- 格：`A0=(off,off) B=(off,on) C=(on,off) D=(on,on)`；判据 **可加**：`D−C−B+A0≈0`；**交互项 X1=(D−C)−(B−A0)**；
- ⭐ **我独立判"可分离/不可分离"并给依据**（不得只转述作者）；**不可分离 ⇒ 按 gate 退回"一期一冻"**。
- 采样点：`run_override.py` 同 sha 翻两开关（life 业态；`time.ongoing` 仅 life 可翻）。

### ⑤ 反向验证 + 归档
- `archive/*_pre_t355` **未删 + 时效标注**（`ls`/内容核对）；
- **反向负例**：故意改一个族计数 ⇒ ①对账必红；改 MATRIX 一格 ⇒ ④残差/交互变 ⇒ 检出。

## 结论口径
**可采信/不可采信**（逐项）；**结论可与作者不同**；`make verify` 与 kernel 错开。
