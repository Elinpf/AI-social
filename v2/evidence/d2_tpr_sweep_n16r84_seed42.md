# `max_turns_per_round` 三档 mock 扫描（`max_turns=6`、`max_messages_per_slot=3` 固定）

> 预登记：`v2/evidence/d2_prereg_max_turns_per_round.md`（**首次提交 `75fd6ad`**，时间 2026-10-22T11:42+08:00，**早于本批起跑**）
> 起跑：2026-10-22T11:44+08:00 之后（预登记之后）；同树 `936a161`（`code/life`、`code/orchestration` 未改），只差 `--override life_v2.dialogue.max_turns_per_round=N`
> 口径：`turns = 每线程 max(turn_index)+1`；`max_turns_per_round` 管「**单回合内可推进几轮**」，与总上限 `max_turns` 不是同一个量；消息条数 ≠ 轮次（群聊同轮多人发言）

## 结果（三档逐项相同）

| `max_turns_per_round` | MSG | 新起线程 | **p50** | p90 | max | mean | ≥3 轮占比 | 单发占比 |
|---|---|---|---|---|---|---|---|---|
| **2** | 947 | 305 | **1** | 6 | 6 | 2.793 | 38.69% | 58.69% |
| **3** | 947 | 305 | **1** | 6 | 6 | 2.793 | 38.69% | 58.69% |
| **4** | 947 | 305 | **1** | 6 | 6 | 2.793 | 38.69% | 58.69% |

**三档连事件数都相同：200,053**。日志字节级 sha 不同，原因已查明且无害：
唯一差异在 `WORLD_INIT.payload.config_digest`（它把运行期 override 也算进去了）⇒ 自第 0 条起哈希链不同；
**结构指标、事件数、消息数、线程数逐项完全相同**。

## 判据核对（预登记三档互斥）

| 判据 | 实测 | 成立？ |
|---|---|---|
| 有效（`p50` ≥2 段单调升 且 ≥3 轮 +≥5pp 且 MSG 增幅 <20%） | `p50` 1→1→1 | ✗ |
| 无效但成本上升（`p50` 不动 且 MSG ≥+20%） | `p50` 不动，但 **MSG 增幅 = 0%**（947→947→947） | ✗（成本没涨） |
| **饱和（某档起逐项完全相同）** | 三档**逐项完全相同**（事件数同为 200,053） | **✓** |

## 判定：**饱和 —— 饱和点 = 最低档 `tpr=2`（该旋钮在本配额下完全不构成约束）**

**「哪一档开始不涨」**：**从第一档（2）起就不涨**——不是"抬到某档后饱和"，而是**这个旋钮在 `max_messages_per_slot=3` 下根本没有被触发**。

机制解释（为什么无效）：
- 单回合推进上限只在「同回合内有多条待接消息」时才起作用；实际每 agent 单 slot 最多 3 条（`max_messages_per_slot=3`），且线程大多数只有 1–2 轮 ⇒ **同一回合内几乎没有"第二轮可接"的情形**，`tpr` 自然不起作用；
- 与 `max_messages_per_slot` 2→3 的对照也一致：slot 从 2 抬到 3 后 p50 仍为 1，说明**限制不在"单回合能推进几轮"，而在"这一回合有没有人接话"**。

## 三条扫描合并结论（对 D2.1 的输入）

| 旋钮 | 档位 | p50 | 代价 | 判定 |
|---|---|---|---|---|
| `max_turns`（总上限） | 2/4/6 | 2→1→1 | — | 尾部跟随上限、**中位不动** |
| `max_messages_per_slot` | 2/3/4 | 1→1→1 | MSG **+42%** | **无效但成本上升**，slot=3 饱和 |
| `max_turns_per_round` | 2/3/4 | 1→1→1 | **MSG +0%** | **饱和（tpr=2 即无效）** |

⇒ **三个配额旋钮都抬不动中位深度（p50）**。要抬 p50，只能改**触发/承接机制**（谁先开口、何时接话、入站未回判定），或走 D12 的提示词路（正向插槽）。

## 日志 sha256（未入库，命令可复现）

| tpr | sha256 |
|---|---|
| 2 | `06432fa55f1e8a293365a8be7a57695f05f7ea9d8ea2d21b36b9e2fb1df2f5d9` |
| 3 | `04fb974931bfa47e56100438b74c78f945f5f55efd8e88c42e11f2bb7a24a1a8` |
| 4 | `9a84634b42815d9c5459a4e8df07233b3c12ff06b31e4aaec698e79e981dfd72` |

## 复现

```bash
cd code && unset HITT_LLM_PROVIDER
for tpr in 2 3 4; do
  python3 ../tools/t271/run_override.py --seed 42 --agents 16 --rounds 84 \
    --out ../v2/evidence/mock_tpr_${tpr}_n16r84_seed42/run.jsonl \
    --side-root /tmp/tpr${tpr}_side --flush-every 0 \
    --override life_v2.dialogue.max_turns=6 \
    --override life_v2.dialogue.max_messages_per_slot=3 \
    --override life_v2.dialogue.max_turns_per_round=$tpr
done
```
