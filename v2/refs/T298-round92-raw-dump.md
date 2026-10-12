# T298 round92 原始 dump（原始数据，不含归因）

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
