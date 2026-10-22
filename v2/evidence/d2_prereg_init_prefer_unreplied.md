# 预登记 · **发起对象改为「欠我回复的那个人」**（A1-回复预算 基座，单变量）

| 项 | 值 |
|---|---|
| **预登记时间** | **2026-10-22T16:58+08:00**（**早于代码改动与起跑**） |
| 首次提交 sha | 见文末「锚点」（本文件即锚点提交引入） |
| 基座 | **A1-回复预算**（`HITT_REPLY_BUDGET=1`），代码 from `913ac4d`；A2 开关保持关 |
| provider | **mock**（零成本） |
| 状态 | **已登记，未改码、未起跑** |

## 1. 假设（第 5 号怀疑点，前四个已排除）

前四轮已排除：配额旋钮（3 个）、回复不占配额（A1-回复预算：生效但无效）、对未回对端不发起（A2：几乎未触发）、`reply_window_rounds`（惰性，`delay>2` 的回复数 = 0）。

剩下唯一机制上说得通的一条：**`_initiate` 选人用的是计划模板的 `partners[0]`，不是「欠我回复的那个人」**。
r/w 轮实测：465 条 `unanswered_inbound` 中 **402 条是"有动作但没回这条"**（去发起了别的线程 / 回了别人）——**这是"选谁"的问题，不是窗口或配额的问题**。

**假设**：把发起对象**优先导向"有未回入站的对端"**，能让这些未回入站被实际接上 ⇒ 转化率↑、`≥3 轮绝对条数`↑、`p50` 上移。

## 2. 单变量（开关默认关）

| 臂 | 开关 | 说明 |
|---|---|---|
| **Ctrl** | `HITT_REPLY_BUDGET=1` | A1-回复预算 原样（本轮重跑） |
| **Treat** | `HITT_REPLY_BUDGET=1` + **`HITT_INIT_PREFER_UNREPLIED=1`** | 唯一差异 |

实现（只在 `_initiate` 内，1 处判定 + 1 个只读 helper）：
- 若开关开 且 存在候选对端（`peers` 内、非本人）**在我这里有未回入站** ⇒ 发起对象改为该对端（`to` 改它、`parts` 改为 `[me, 该对端]`）；
- 若有多个，取**未回入站 seq 最大**的那个（最近的一条，确定性）；无未回入站则**回落到原 `partners[0]`**（行为不变）。
- 只影响 `scope=private` 的发起；GROUP/PUBLIC 不动；提示词、字段、配额全部不动。

其余全同：`max_turns=6`、`max_messages_per_slot=2`、`max_turns_per_round=2`、`reply_window_rounds=2`、`seed=42`、`n=16`、`rounds=84`、mock。

## 3. 指标（四列 + 分母 + 机制指标）

1. 发起 / 回复 / MSG（含增幅）；
2. 转化率 = Σreplied/Σinbound（按 `(agent, day, slot)`）+ **分母**；
3. 结构：`p50 / p90 / max / mean / ≥3 轮占比 / ≥3 轮绝对条数 / 单发占比 / 新起线程数`；
4. **机制指标（本轮新增，须报）**：
   - **`init_to_unreplied_partner`**：发起对象恰为"我欠回复的对端"的发起条数（及占发起总数比例）；
   - **`unanswered_inbound`** 与其中 `never_acted`（用于说明有多少是"永远没轮到"，不受本轮影响）；
   - **`replies with delay > 2`**（沿用上轮口径，用于确认本臂未改窗口语义）。

## 4. 判据（写死）

- **有效**：`p50` **≥2** 且 `≥3 轮绝对条数` **≥ +10%** 且 转化率 **上升** 且 **`init_to_unreplied_partner` 占发起 ≥30%**（证明机制真的被触发，不是又一次"没机会"）；
- **「机制没机会」**：`init_to_unreplied_partner` 占发起 **<10%** ⇒ 判此档（说明在发起时刻几乎不存在"欠回复的对端"，问题更可能在**计划模板的对端集合本身**，需转向"允许向计划外对端搭话"）；
- **无效但成本上升**：`p50` 不动 而 MSG **≥ +10%**；
- **用少说话换比值**：新起线程 ↓≥15% 且 `≥3 轮绝对条数` 不升；
- 其余 ⇒ 判「部分有效」，写清四项读数与不达标项。

## 5. 三条反事实（沿用）

新起线程数 / `≥3 轮绝对条数` / 分母（有未回入站的 agent-slot 数）；判读规则与上轮一致。

## 6. 自证与自检

- `switch_proof.txt`：`code_sha`（worktree HEAD）、`HITT_REPLY_BUDGET=1`、`HITT_INIT_PREFER_UNREPLIED=1`、三个开关的 grep 计数、参数四项；
- **三臂两两不同自检**：Treat 必须同时不同于 Ctrl 与 baseline；若相同 ⇒ 不报结论，先报 Leader；
- **并发披露**：mock 不占端点；若主树有真批在跑须写明 CPU 共享。

## 7. 复现

```bash
WT=<repo>/.worktrees/a2-prefer
cd $WT/code && set -a && . <repo>/code/.env.local && set +a && unset HITT_LLM_PROVIDER HITT_NO_INIT_UNREPLIED
export HITT_REPLY_BUDGET=1
# Ctrl
python3 $WT/tools/t271/run_override.py --seed 42 --agents 16 --rounds 84 \
  --out <repo>/v2/evidence/mock_pref_ctrl_n16r84_seed42/run.jsonl --side-root /tmp/pref_ctrl_side --flush-every 0 \
  --override life_v2.dialogue.max_turns=6 --override life_v2.dialogue.max_messages_per_slot=2 \
  --override life_v2.dialogue.max_turns_per_round=2 --override life_v2.dialogue.reply_window_rounds=2
# Treat
export HITT_INIT_PREFER_UNREPLIED=1
python3 $WT/tools/t271/run_override.py --seed 42 --agents 16 --rounds 84 \
  --out <repo>/v2/evidence/mock_pref_treat_n16r84_seed42/run.jsonl --side-root /tmp/pref_treat_side --flush-every 0 \
  --override life_v2.dialogue.max_turns=6 --override life_v2.dialogue.max_messages_per_slot=2 \
  --override life_v2.dialogue.max_turns_per_round=2 --override life_v2.dialogue.reply_window_rounds=2
```

## 锚点

- 本文件**首次提交**即预登记锚点；代码改动与起跑必须晚于该提交。
- 首次提交 sha：（由紧随其后的补记提交填写）
