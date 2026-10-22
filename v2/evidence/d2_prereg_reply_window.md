# 预登记 · `reply_window_rounds` 2→4（**A1-回复预算 基座**上的单变量）

| 项 | 值 |
|---|---|
| **预登记时间** | **2026-10-22T16:21+08:00**（**早于起跑**） |
| 首次提交 sha | 见文末「锚点」（本文件即锚点提交引入） |
| 基座 | **A1-回复预算**：`HITT_REPLY_BUDGET=1`，代码 `913ac4d`（worktree `.worktrees/a2-trigger`，含 A2 开关但**默认关**） |
| provider | **mock**（零成本；可与 worldline 真批并行，报告须披露） |
| 状态 | **已登记，未起跑** |

## 1. 假设

A2 的教训是「机制没被触发」⇒ 本轮必须带**机制指标**，不能只看结果指标。

**假设**：`reply_window_rounds=2`（入站消息只在 2 回合内可回）在 **A1-回复预算 打开回复预算之后才第一次成为有效约束**——
D9 曾判它“惰性”，但那是在“回复被配额卡死”的旧结构下测的（agent 根本轮不到回复，窗口宽窄自然无差别）；
现在有回复了，窗口可能把**跨 slot 的未回入站**挡在门外。

## 2. 单变量

| 臂 | 开关/参数 | 说明 |
|---|---|---|
| **Ctrl** | `HITT_REPLY_BUDGET=1`，`reply_window_rounds=2`（默认） | A1-回复预算 原样（本轮重跑，保证同批同环境可比） |
| **Treat** | `HITT_REPLY_BUDGET=1`，**`reply_window_rounds=4`** | 唯一差异；`--override life_v2.dialogue.reply_window_rounds=4`（运行期、不落盘、不改指纹） |

其余全同：`max_turns=6`、`max_messages_per_slot=2`、`max_turns_per_round=2`、`seed=42`、`n=16`、`rounds=84`、mock。
**A2 开关保持关**（`HITT_NO_INIT_UNREPLIED` 不设）⇒ 与 A2 臂无关。

## 3. 指标（四列 + 分母 + **机制指标**）

1. **发起条数** / **回复条数** / MSG 总数（各含增幅）；
2. **「入站未回 → 回复」转化率** = Σreplied / Σinbound（按 `(agent, day, slot)`）+ **分母**（有未回入站的 agent-slot 数）；
3. 结构：`p50 / p90 / max / mean / ≥3 轮占比 / ≥3 轮绝对条数 / 单发占比 / 新起线程数`；
4. **机制指标（本轮核心，写死定义）**：
   - **`unanswered_inbound`**：入站消息 m（DM `to==A`；GROUP 且 `A∈participants` 且 `from≠A`），且 **A 在该线程中 `seq > m.seq` 的位置没有再发过任何消息**（即 A 始终没回）；
   - **`expired_unanswered_inbound`（过期未回入站数）**：在 `unanswered_inbound` 中，**A 之后确实有过对话动作**（任一 MSG，seq > m.seq），但**该动作所在 round − m.round > `reply_window_rounds`** ⇒ 想回时窗口已过期；
   - 同时报 `never_acted_unanswered`（之后完全没有任何动作，窗口无关）。

**判据（写死）**：
- **有效**：`expired_unanswered_inbound` **显著下降**（相对 Ctrl **≥ -30%**）**且** 转化率**上升** **且** `≥3 轮绝对条数`**上升** **且** `p50` **上移**（≥2）；
- **「瓶颈不在窗口」**：`expired_unanswered_inbound` **几乎不变**（|Δ| < 10%）⇒ 说明没人去看那些待回，问题在感知 / `_initiate` 选人，不在窗口；
- **「无效但成本上升」**：`p50` 不动 而 MSG **≥ +10%**；
- 其余 ⇒ 判「部分有效」，须写清四项读数与从哪一项起不达标。

## 4. 三条反事实（沿用，防"用少说话换比值"）

1. **新起线程数**（含降幅）；
2. **≥3 轮线程绝对条数**（不是占比）；
3. **分母（有未回入站的 agent-slot 数）**——若分母大幅缩水 ⇒ 吞吐被掐，转化率再高无意义。

判读：新起↓ + ≥3 轮绝对↑ ⇒ 真加深；新起↓ + ≥3 轮绝对不升 ⇒ 「少说话换比值」；两者都↓ ⇒ 损伤吞吐，否掉。

## 5. 自证与自检（本轮新增）

- **switch_proof.txt**：`code_sha`（`git -C .worktrees/a2-trigger rev-parse --short HEAD`）、`HITT_REPLY_BUDGET=1`、`reply_window_rounds` 生效值、参数四项、两个开关的 grep 计数；
- **三臂两两不同自检**：Treat 的数字必须同时不同于 Ctrl 与 baseline；若与任一相同 ⇒ **不报结论，先报 Leader**；
- **并发披露**：跑 mock 期间若主树有真 LLM 批在跑，报告须写一句「mock 不占端点，但 CPU 共享」。

## 6. 复现（跑前写死）

```bash
WT=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/.worktrees/a2-trigger
cd $WT/code && set -a && . <repo>/code/.env.local && set +a && unset HITT_LLM_PROVIDER
export HITT_REPLY_BUDGET=1            # A1-回复预算；不设 HITT_NO_INIT_UNREPLIED（A2 关）
# Ctrl
python3 $WT/tools/t271/run_override.py --seed 42 --agents 16 --rounds 84 \
  --out <repo>/v2/evidence/mock_rw2_ctrl_n16r84_seed42/run.jsonl --side-root /tmp/rw2_side --flush-every 0 \
  --override life_v2.dialogue.max_turns=6 --override life_v2.dialogue.max_messages_per_slot=2 \
  --override life_v2.dialogue.max_turns_per_round=2 --override life_v2.dialogue.reply_window_rounds=2
# Treat
python3 $WT/tools/t271/run_override.py --seed 42 --agents 16 --rounds 84 \
  --out <repo>/v2/evidence/mock_rw4_treat_n16r84_seed42/run.jsonl --side-root /tmp/rw4_side --flush-every 0 \
  --override life_v2.dialogue.max_turns=6 --override life_v2.dialogue.max_messages_per_slot=2 \
  --override life_v2.dialogue.max_turns_per_round=2 --override life_v2.dialogue.reply_window_rounds=4
```

## 锚点

- 本文件**首次提交**即预登记锚点；起跑必须晚于该提交。
- 首次提交 sha：（由紧随其后的补记提交填写）
