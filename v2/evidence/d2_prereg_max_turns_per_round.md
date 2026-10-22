# 预登记 · `max_turns_per_round` 三档 mock 扫描（D2.1 候选旋钮）

| 项 | 值 |
|---|---|
| **预登记时间** | **2026-10-22T11:42+08:00**（**早于任何起跑**；本文件首次提交即锚点） |
| 预登记 commit（首次引入本文件的提交） | 见文末「锚点」一节（由紧随其后的一次提交补记，不改本行时间） |
| 预登记文件 sha256（首次提交 `75fd6ad` 版） | `d3088914deb1b1d2b918c24f7129d254e408fd2d3924b27c7ac965796cca914e` |
| 执行人 | dialogue-core-dev |
| provider | **mock**（零 LLM 成本） |
| 状态 | **已登记，未起跑**（等 Leader 点头） |

## 1. 假设（要检验的机制命题）

**中位深度由「单回合推进上限 + 入站未回判定」约束，而非总上限 `max_turns`。**

依据（已完成的两次扫描）：
- `max_turns` 2/4/6：`p90`≡上限逐档跟随、**`p50` 恒为 1–2 不动** ⇒ 总上限只钳尾部；
- `max_messages_per_slot` 2/3/4：**`p50` 恒 1 不动**、MSG +42%、slot=3 起饱和 ⇒ 单 slot 消息上限也不抬中位深度。
⇒ 剩下未被检验的候选是**单回合推进上限** `max_turns_per_round`（当前默认 2）。

## 2. 扫描设计（写死）

| 项 | 取值 |
|---|---|
| 固定 | `max_turns = 6`、`max_messages_per_slot = 3`（已证 3 即饱和，避免二次变量） |
| 自变量 | **`max_turns_per_round = 2 / 3 / 4`**（运行期 `--override life_v2.dialogue.max_turns_per_round=N`，不落盘、不改指纹） |
| 其余不变 | `seed=42`、`n=16`、`rounds=84`、mock、**同一棵树连续跑完三档**（中途不改代码） |
| 产出 | `v2/evidence/mock_tpr_{2,3,4}_n16r84_seed42/run.jsonl` + 汇总 `v2/evidence/d2_tpr_sweep_n16r84_seed42.{json,md}` |

## 3. 判据（跑前写死，三档互斥，按顺序判）

1. **有效**：满足全部三条 ——
   (a) `p50` 随三档上升（**≥2 档单调升**，即 2→3 与 3→4 两段中至少两段同向上升）；
   (b) `≥3 轮占比` 提升 **≥ 5pp**（相对基线档）；
   (c) **MSG 总量增幅 < 20%**（防「用消息量换深度」）。
2. **无效但成本上升**：`p50` 不动（三档相同或差 ≤1）**且** MSG 增幅 **≥ 20%**。
3. **饱和**：某档起**逐项完全相同**（如 slot=3→4 的逐项相同），须写明**饱和点**（第一个不再变化的档）。
4. 若三者都不成立 ⇒ 判「**部分有效/部分受钳**」，并写明从哪一档开始不涨、以及 MSG 增幅。

## 4. 反事实（用来防"换口径而非真加深"）

- **若该旋钮真的有效**：应观察到 **`p90` 仍贴在 6（总上限）不变，而 `p50` 上移**；
- **若 `p90` 同时下降**：说明不是"聊得更深"，而是**统计口径或线程结构被改变**（例如线程变少、单发变多），需按「换口径」报告，**不得**写成深度改善；
- 同时记录 **`单发占比`** 与 **`新起线程数`**：若「`p50` 升 + 单发升 + 新起线程数降」⇒ 写成**交换**（深度换广度），不写改善。

## 5. 口径警告（必须随结果一起引用）

- **`max_turns_per_round` 管「单回合内可推进几轮」**，与**总上限 `max_turns`** 不是同一个量；
- 统计口径固定为 **`turns = 每线程 max(turn_index)+1`**；`max_turns_per_round` **不改变** `turn_index` 的语义，只影响同一回合内能推进多少；
- 群聊同轮多人发言 ⇒ **消息条数 ≠ 轮次**（沿用前两批的口径警告）；
- **mock 不读语义** ⇒ 只能谈**深度/结构**，**不能**谈自然度。

## 6. 复现命令（跑前写死，避免事后改参数）

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

## 锚点

- 本文件**首次提交**即预登记锚点；`max_turns_per_round` 扫描的任何起跑时间必须**晚于**该提交。
- **首次提交 sha = `75fd6ad`**（本文件即该提交引入；扫描起跑时间必须晚于此提交）
