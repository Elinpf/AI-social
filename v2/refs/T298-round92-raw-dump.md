# T298 round92 原始 dump（原始数据，不含归因）

## 0) 时间线（相对提交点 `8d4c8b9`）—— 消除台账矛盾
- **22:45 的读数（`MEMORY_FORGET` resumed 537 vs oneshot 667）＝ 修复【前】**
  —— 该探针走 **`tree=copy`（提交快照）**，而当时修复**尚未提交** ⇒ 快照**不含**修复。
- **22:52 的读数（两日志等长 9809、逐回合类型计数差 = 0）＝ 修复【后】**
  —— `8d4c8b9` 已提交，探针快照**含**修复。
- ⇒ 结论：**修复前分岔、修复后语义收敛**（两读数不矛盾，是提交点前后的两个快照）。

## 0b) 残差精确刻画（修复后，`N1/run.jsonl` vs `ref.jsonl`）
- **真正的语义差异 = 0 条**。
- 9652 条：**仅差** `LLM_CALL.payload.{cached,tokens_in,tokens_out}`。
- 150 条：`TURN_SEAL`，**仅差 `last_hash`**（哈希链下游），其 `payload.state_hash` **150 条全部相等**。


- **提交 sha**: `8d4c8b9`（`code/life/memory.py`：`sync_from_refs` 缓存对齐权威 + `_drop_node`）
- **诊断命令**（两路，`seed=9 n=2 rounds=150`，cut/ kill@89）：
  - 一次性：`python -m orchestration run --life --seed 9 --agents 2 --rounds 150 --out …/one.jsonl`
  - 前缀+续跑：`--rounds 90 --flush-every 5` → `--rounds 150 --flush-every 5 --resume-from pfx`
  - 探针：`T271_VR_SEED=9 T271_VR_AGENTS=2 T271_VR_ROUNDS=150 T271_VR_FLUSH=5 T271_VR_KILL_AFTER=2 T271_VR_GATE=1 bash tools/t271/verify_native_resume.sh`
- **说明**：诊断用「主树活代码」，但此刻 **主树无未提交 `life/` 改动**（修复已提交 `8d4c8b9`）⇒ 与 `tree=copy` 快照内容等价。

## 1) round92 两路 `self.memory.nodes`（mem_id 集）

| agent | oneshot | resumed | only_in_one | only_in_resume |
|---|---|---|---|---|
| P001 | 348 | 348 | **0** | **0** |
| P002 | 338 | 338 | **0** | **0** |

⇒ round92 **两路节点集完全相同**（对称差 = ∅）。

## 2) 喂给 `plan_forgetting` 的 `mems` 实参（round92 / round93 那一拍）
- round92：两路 `len=348 / 338`，**mem_id 集相同**。
- round93：两路 `len=348 / 338`，**mem_id 集相同**。
（原始：`/tmp/t298_dump.json`）

## 3) 前向态（可选项，**未捕获**）
`_slept_days` / `_persona_state` / `_persona_p0` / `_drift_streak`：本轮 dump **未采集**（如需，我再补一次带这些字段的 dump）。

## 3b) 溯源：三档/本 dump 跑在**哪个树状态**（纪律补录）
> 关键：**"主树无未提交 `life/` 改动 ⇒ 活树 ≡ HEAD" 只对 `life/` 成立**；活树 ≠ 纯 HEAD。

- **本 dump 与三档回归**均跑在**活树**（非 `tree=copy`），其状态（`git status`，HEAD `2f956b6`）：
  - **`life/` 部分 = 已提交 `8d4c8b9`**（无未提交 life 改动）✓
  - **含未提交的 kernel 改动**：`code/engine/{events,kernel,ledger,runner,version}.py`（T287，**default-off**）+ 未跟踪 `code/engine/time_model.py`、`code/config/time.json`、`code/tests/test_t287_time_model.py`
- ⇒ 复算时请注意：**结果包含上述未提交 kernel/time 改动**（T287 默认关，预期不改变本三档结果）；**非纯 HEAD 快照**。
- **两条机制必须分清（勿混）**：
  - **探针**`verify_native_resume.sh`（§5 的逐字节 FAIL / 残差刻画）＝ **`tree=copy`（提交快照）**；
  - **本 dump（§1–§3）与三档回归（§3c）** ＝ **活树**。
- **③ 三档 = "条件性通过"**：跑在活树（含 T287 default-off 未提交改动）。**解冻后需在【纯 HEAD 快照】上补跑一次**，以消除"活树 ≡ 快照"这一 caveat（不用"default-off 所以没事"的推理收尾）。

## 3c) 三档回归（活树，条件性通过）
- `seed42/n=4/0..8` ✅ · `seed42/n=4/0..24` ✅ · `seed7/N=20×24` ✅（均 `one==two`）。
- 命令：`run_e2e(seed, rounds, n, ...)` 三段式（one / prefix+flush / resume），见 `/tmp/t298_reg.py`。



## 4) 两路新日志（可读路径）
- resumed：`/root/t271/runs/nr/N1/run.jsonl`
- oneshot：`/root/t271/runs/nr/ref.jsonl`
- 备用（同参数、活树）：`/tmp/t298dump2/two.jsonl`（resumed）、`/tmp/t298dump2/one.jsonl`（oneshot）

## 5) 探针 FAIL 的**逐字节差异**（原始定位，供 art 折叠）
- 两日志**长度相同（9809 / 9809）**；**逐回合事件类型计数差异 = 0**（`differing rounds = []`）。
- 完整逐条比对：**9652 条仅差缓存元数据**（`LLM_CALL.payload.{cached,tokens_in,tokens_out}`），**150 条为 `TURN_SEAL.last_hash`**（其差异是"上一条事件 payload 含 cached/tokens ⇒ 哈希链下游"，非语义）。
- 摘录（第一条差异，line7）：`cached (False vs True)`、`tokens_in (8 vs 0)`、`tokens_out (8 vs 0)`。
- **忽略 `{cached,tokens_in,tokens_out}` 后**逐条比对仍显示 TURN_SEAL 差 → 因 `last_hash` 是哈希链下游，源头仍是上述三字段。

**（以上为原始数据；归因由 art 独立给出。）**

## 6) 解冻后待补（T298 出口，命令占位）
> 前置：解冻 + T299 新闸门口径落地。均走**与结论对应的机制**（探针=copy；三档=纯 HEAD）。

1. **纯 HEAD 三档**（消除 §3b 的"活树"caveat）：
   `git worktree add .worktrees/t298-head <HEAD>` 或整目录复制 → 在该树跑 §3c 的三档（`seed42/n=4/0..8`、`0..24`、`seed7/N=20×24`），记录 `one==two`。
2. **新口径探针**（T299 定义：排除 `cached/tokens_in/tokens_out/cost_units`、保留 `cache_key`、`state_hash` 须等）：
   `T271_VR_SEED=9 T271_VR_AGENTS=2 T271_VR_ROUNDS=150 T271_VR_FLUSH=5 T271_VR_KILL_AFTER=2 T271_VR_GATE=1 bash tools/t271/verify_native_resume.sh`
3. **反向验证**（去掉修复须重回分叉）：临时将 `sync_from_refs` 的裁剪分支置空 → 探针应重新在 round93 分叉；随后恢复。
4. **`make verify`**（分段跑）。

