# D2.4 诊断：**对话短，不是窗口的问题，是三条硬上限全部饱和**

> 日期：2026-10-24。只读分析，基于 OFF 基线 `run_d12c_off_n16r60_seed42`（510 MSG / 16 人 / 60 轮）。
> 动机：心跳待办点名"`reply_window_rounds` 2→4 在新结构下复测"。查证后发现 **它已经是 4**（D9 改过），
> 而真正的瓶颈在别处——本件用日志把三个上限的饱和率量出来。

## 0. 代码事实

```
code/life/dialogue_threads.py:26-33  DEFAULTS
    max_turns              = 6    # 单线程最大轮数（含发起），到顶封口
    max_turns_per_round    = 2    # 单线程单回合最多推进轮数（K）
    max_messages_per_slot  = 2    # 单 agent 单 slot 最多发出的 MSG 条数（发起+回复合计）
    reply_window_rounds    = 4    # ← 已经是 4（D9: 2→4 单变量已做过）
    history_turns          = 3    # 上下文只带最近 3 轮
code/life/agent.py:900-925  _pick_reply_target()：同时受 未超窗 / 未到顶 / 本轮未接 / K 上限 / slot 上限 五重约束
```

## 1. 三个上限的饱和率（实测）

| 约束 | 分布 | 饱和 |
|---|---|---|
| `max_messages_per_slot = 2` | 每 (agent, slot) 消息数：**{1: 57, 2: 199}**，**0% 超过 2** | **77.7% 的 slot 顶在上限** |
| `max_turns = 6` | 114 个线程的消息数：`1:26, 2:11, 3:7, 4:16, 5:2, `**`6:52`** | **45.6% 的线程（52/114）恰好 6 条 = 硬顶封口** |
| `reply_window_rounds = 4` | 入站 455 条中，**25.1%（114 条）此后对端未在本线程再发言** | 窗口本身**未见饱和证据** |

**关键读数**：`{1:57, 2:199}` 且**没有任何一条超过 2** ⇒ 这不是"统计巧合"，是**硬上限**：
每个居民每个时段最多说 2 句，多一句都不可能。

## 2. 这意味着什么（对北极星）

- **45.6% 的线程是在"被允许的最长对话"（6 条）处被切断的**，不是自然收尾。真实聊天极少恰好停在 6 句。
- **每个时段最多 2 条消息** ⇒ 即使两个人正聊到兴头上，时段一到就必须停；下一时段重开新线。
  「聊一半被打断」是**结构性必然**，不是偶然。
- `reply_window_rounds=4` 在 `max_turns=6` + `max_messages_per_slot=2` 之下**几乎没有约束力**：
  一个线程最多 6 条、每 slot 最多 2 条 ⇒ 窗口 4 轮远宽于实际需要。
  **⇒ "2→4 复测"这个待办本身优先级应降低**，先动前两个上限。

## 3. 执行路径（重要：**不改代码、不进指纹**）

`dialogue_threads.load_params()` 读 `config/life_v2.json` 的 `dialogue` 段，且**支持运行时 override**：

```
code/life/dialogue_threads.py:76-84
    from . import config as _lcfg
    ov = _lcfg.override_for("life_v2") or {}     # run_override.py --override life_v2.dialogue.max_turns=8
```

⇒ 两个上限都可用 **`--override life_v2.dialogue.<key>=<val>`** 改，**不落盘、不改 `config/*.json` ⇒ 不进 `engine_version` 指纹**。
**这很重要**：直接改 `config/life_v2.json` 会变指纹（该文件属 12 个 `config/*.json`），
所有历史对照（T0/T5/D12 系列）当场失效。

**候选臂（未预登记，仅记录方向）**：
- **D2.5a**：`max_messages_per_slot` 2 → 3（77.7% 饱和 ⇒ 最高杠杆）
- **D2.5b**：`max_turns` 6 → 8（45.6% 封顶 ⇒ 次高）
- 两者都属**结构参数**，不是措辞 ⇒ 与 D12 系列的"降重合 ⇄ 文体"旋钮**无关**。

## 4. 纪律提醒（本轮踩到的新坑，已写入 runbook §3.116）

**"改 config 文件"与"运行时 override"在指纹层面不是一回事**：
前者改 `engine_version`（毁对照），后者不改。凡新增参数类臂，**默认走 override**，
并在 evidence 里把 override 串逐字记下（可复算），**不得直接改 `config/*.json`**。

## 5. 局限（如实写）

- 饱和率是从**已成事实的日志**倒推的，不能证明"若上限放宽就一定会聊更长"（可能改由别处约束，如 `max_turns_per_round` 或 LLM 自己收尾）；
- `max_turns_per_round=2` 的饱和度**未单独测**（需要 track `_round_replies` 中间态，日志里没有该字段）——列为下一步；
- 25.1% 入站未回**不等于**"想回但被拦住"，也可能对方本就无意再答，本件不作因果断言。
