# T249 · 故事叙述机（最小端到端）证据

> 作者：narrative-designer ｜ 2026-10-12
> 目标：**一份真实日志 → 一篇可读故事**，并**真跑三条硬门**（Q-1/Q-6/Q-8）。
> 实现：`code/devtools/storyteller.py`（只读、**确定性渲染**、**不调用 LLM**）。

## 一、交付物

| 文件 | 说明 |
|---|---|
| `code/devtools/storyteller.py` | 故事叙述机：选角→冲突识别→节拍→成文→质检；只读 `obs.reader.ReadOnlyLog`（构造校验哈希链） |
| `v2/evidence/t249/story_director_n3_2w.md` | **主故事**（含 `directed` 事件，Q-8 非空跑） |
| `v2/evidence/t249/story_director_n3_2w.qc.json` | 主故事 QC |
| `v2/evidence/t249/story_canon_n20_1w.md` | 通用性验证（canonical N=20 真实日志） |
| `v2/evidence/t249/story_canon_n20_1w.qc.json` | 上者 QC |

## 二、命令（可复算）

```bash
cd code

# ① 产出主日志：真实 run，内存启用世界导演（不改共享 config 文件）
python3 - <<'PY'
import sys; sys.path.insert(0,'.')
from engine.runner import load_config
from orchestration.integration import run_e2e
cfg = load_config(); cfg["world_director"]["enabled"] = True
run_e2e(seed=7, rounds=168, n=3, config=cfg,
        out_path="/root/t249_dir/run.jsonl", side_root="/root/t249_dir/side")
PY

# ② 叙述机：日志 → 故事 + QC
python3 devtools/storyteller.py --log /root/t249_dir/run.jsonl --out /root/t249_out --weeks 2

# ③ 自检：证明 QC 真会抓「编造数字」与「把 directed 说成自发」
python3 devtools/storyteller.py --selftest --log x --out /tmp/x

# ④ 通用性：canonical N=20 真实日志（只读，无新 run）
python3 devtools/storyteller.py \
  --log ../v2/evidence/run_t136_real_llm_canon_n20.jsonl --out /root/t249_canon --weeks 1
```

## 三、结果（真跑）

**主故事（`run.jsonl`，seed=7 / 168 回合 / N=3，含世界导演）**

| 项 | 值 |
|---|---|
| 日志 sha256 | `50d3d4793c1f73493bba1c68…` |
| log_hash | `sha256:cf41c02057f27902d…` |
| 事件数 / 原子数 | 24483 / 347 |
| **Q-1 锚点覆盖** | **1.0**（目标 1.0） |
| **Q-6 硬事实违规** | **0**（目标 0） |
| **Q-8 来源误标** | **0**（目标 0） |
| **硬门通过** | **True** |
| by_origin | `{spontaneous:343, directed:4}` ← **Q-8 非空跑**（4 条 `directed` 均带【世界导演】标记） |
| story.md sha256 | `7d2f057b031e51a28442b3d50a7e7acd…` |
| qc.json sha256 | `7612b43a7752826c11fa4aaa40cd5aa1…` |

**通用性（canonical N=20 `run_t136_real_llm_canon_n20.jsonl`）**：原子 1476，三硬门全过（该日志无 SEED/director → Q-8 空跑成立），耗时 ≈6s。

**可复算**：同一日志两次运行 → `story.md` 与 `story.qc.json` **逐字节一致**（`cmp` 通过）。
（Fork B：本环节本身完全确定；若接 LLM 成文，非确定处仅"表达措辞"，事实层仍由本 QC 钉死。）

**自检（负例）**：`--selftest` → `Q-6 检出编造数字=1`、`Q-8 检出误标=1` → **PASS**（证明两门不是空转）。

## 四、三条硬门怎么跑到（不是写在文档里）

- **Q-1**：每个情节句渲染即带其来源 `event_seq`；QC 重算 `anchored/total`（=1.0）。
- **Q-6**：句中的**每个数字**（正则抽取）必须出现在其锚点事件的 `payload`（递归展开）里；否则计违规。模板只引用 payload 字段 ⇒ 正常 0 违规；`--selftest` 证明能抓 999 这类编造。
- **Q-8**：`origin` 由事件类型判定（`WORLD_DIRECTIVE/WORLD_GROUP_EVENT`→directed；`SEED_EVENT`→induced；其余 spontaneous）；directed/induced 句**必须**带【世界导演】/【观察者注入】标记，反之不得误标。

## 五、边界与诚实声明

- **只读**：无任何写事件；未新增引擎写路径；未新增事件类型/字段（无需 08 登记）。
- **不调用 LLM**：成文为确定性模板（LLM 只产"表达"不产"事实"的设计在此**落到极致**——连表达都不依赖 LLM）。
  → 若后续接 LLM 成文（可用既有 `purpose=describe`，**无需新 purpose**），**必须过同一套 QC**；本文件即判据来源。
- **【未验证】**：LLM 成文路径未接（本轮只需最小端到端）；多体裁/多视角矩阵（T204 §2.3）本轮未展开（仅"编年史"单体裁）。
- **降噪口径**：`RELATION_CHANGE` 仅叙述 `|Δ|≥10` 的显著变化（降噪，确定性）；改阈值可讲更多/更少。
