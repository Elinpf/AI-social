# `max_messages_per_slot` 三档 mock 扫描（`max_turns=6` 固定，n=16 × rounds=84 × seed=42，mock）

> 目的：既然「抬 `max_turns` 抬不动 `p50`」，找出**真正能抬 p50 的旋钮**。
> 口径：`turns = 每线程 max(turn_index)+1`（**`max_messages_per_slot` 管的是单 slot 可发消息条数，不是轮次**；
> 群聊同轮多人发言 ⇒ 消息条数 ≠ 轮次。此口径警告与 `max_turns` 扫描一致）。
> 同树（HEAD `45ddc7d`）、同 seed/n/rounds、连续跑完三档，只差 `--override life_v2.dialogue.max_messages_per_slot=N`。

## 结果

| `max_messages_per_slot` | **MSG 总数** | **新起线程数** | p50 | p90 | max | mean | **≥3 轮占比** | 单发占比 |
|---|---|---|---|---|---|---|---|---|
| **2**（基线） | 666 | 228 | **1** | 6 | 6 | 2.67 | **35.5%** | 56.1% |
| **3** | **947（+42%）** | **305（+34%）** | **1** | 6 | 6 | 2.79 | **38.7%（+3.2pp）** | 58.7% |
| **4** | 947（=slot3，**饱和**） | 305（=slot3） | 1 | 6 | 6 | 2.79 | 38.7% | 58.7% |

（原始汇总 `d2_slots_sweep_n16r84_seed42.json`；日志各 ~87MB 被 `.gitignore` 排除，sha256 见文末）

## 判据核对（预登记，跑前写死）

| 判据 | 实测 | 成立？ |
|---|---|---|
| **有效**：`p50` 随 slot 上限上升 **且** `≥3 轮占比` 提升 **≥5pp** | `p50` **1→1→1 不动**；`≥3 轮` +3.2pp（<5pp） | ✗ |
| **无效但成本上升**：`p50` 不动而 `MSG` 总量上涨 | `p50` 不动；`MSG` 666→947（**+42%**） | **✓** |

## 结论：**无效，但成本上升**（不是"交换"）

1. **`p50` 完全不动（1→1→1）**：普通搭话仍然是 1 轮；
2. **`≥3 轮占比` 只 +3.2pp（35.5%→38.7%）**，未达 5pp 有效阈值；`p90`/`max` 贴在 `max_turns=6` 上限，与 slot 上限无关；
3. **MSG 总量 +42%（666→947）**、`LLM` 调用同向上涨 ⇒ **话说多了、没聊深**；
4. **广度没有下降**：新起线程 228→305（**+34%**），单发占比仅 +2.6pp ⇒ 与本轮 `max_turns` 扫描里「深度上去、广度下来」的模式**不同**，这里是「广度上去、中位深度不动」；
5. **slot=4 与 slot=3 逐项相同**（连事件数都是 200,053）⇒ **该旋钮在 3 就饱和**，再抬无任何效果（说明别处还有更强的约束：单回合 `max_turns_per_round=2` 与「入站未回」判定）。

**可用含义**：**D2.1 若走「配额」路，抬 `max_messages_per_slot` 不是有效旋钮**（只是多发消息 +42%）。要抬 `p50`，必须动**触发/承接机制**（谁先开口、何时接话、`max_turns_per_round`），或走 D12 的提示词路（正向插槽）。

## 日志 sha256（未入库，命令可复现）

| slot | sha256 |
|---|---|
| 2 | `c17eb0fabd82ca009adb39590b449b7d105fae094de89e21f3027b895f884d8d` |
| 3 | `0765bba3644ac274bdf7529cc562d0a7dfca545b1dec2befcce6ee04c721a2a3` |
| 4 | `113aa8f18ba92c983b5ca3e9df43eef80c31b35dc5927b5e8ae18f716edc13d2` |

## 复现

```bash
cd code && unset HITT_LLM_PROVIDER
for ms in 2 3 4; do
  python3 ../tools/t271/run_override.py --seed 42 --agents 16 --rounds 84 \
    --out ../v2/evidence/mock_slots_${ms}_n16r84_seed42/run.jsonl \
    --side-root /tmp/ms${ms}_side --flush-every 0 \
    --override life_v2.dialogue.max_turns=6 \
    --override life_v2.dialogue.max_messages_per_slot=$ms
done
```
