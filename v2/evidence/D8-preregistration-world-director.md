# D8 · 预注册：世界导演链路「接通 / 未接通」读数判据（先写判据，后取数）

> 作者：repo-scout（仓库现状勘察员）｜写作时间：2026-10-20 22:12 (+08:00)
> 绑定代码身份：`master @ 2090287809ae307614b3f9b2f62e7619f2142ea8`（下称 `2090287`）
> 绑定数据批：A0 臂 `v2/evidence/run_d2_after_n16_seed42/`，日志 `run.jsonl` sha256 `643f13a5…3141`，meta `5fe058f3…`（16 agents × 84 rounds × seed 42，provider=openai_compat）
> 配套读数文档：`v2/evidence/D8-world-director-diagnosis.md`（与本文件同批提交）

---

## 0. 定位披露（必须写清，否则等于伪造盲判）

本文件**不是盲预注册**。在动笔之前，作者已在「本轮维度选型勘察」（`round-scout-findings.md`）中观测到两条核心事实：84 回合里只有 1 条 `WORLD_DIRECTIVE`、`affected_scope_count=0`。

因此本文档的正确定位是：**把"什么算接通的读数"在写读数报告之前锁死**，防止事后按数字改写判据（R6/F4 已吃过"先看数据后起草判据"的教训，见 `v2/evidence/r6_f4_arm_open/delivery_notes_draft.md` §8-1）。

本文档**不含任何读数结论**，只含判据与统计口径。

---

## 1. 被诊断的对象：五层链路

```
L1 剂量层  config/world_director.json 的 dose(prob_bp) × dose_curve
             ↓  engine/world_director.py::plan_directives（roll = rng_branch(seed,"world_director",round,idx) % 10000）
L2 触发层  是否 roll < prob → 产出 directive 草案
             ↓  engine/hooks/world_director.py::apply_world_director（校验 R1–R6 + emit）
L3 影响面层 WORLD_GROUP_EVENT.affected_scope_count → engine/world_params.py::world_params（派生情境参数）
             ↓  KernelAdapter.world_params → life/agent.py::_read_world_params
L4 感知层   contracts/visibility.py（PERCEPTION_SCOPE）→ engine/perceive.py::visible_events → life/agent.py::_observe
             ↓  _SALIENT_EVENTS 白名单 → MEMORY_WRITE / OBSERVATION
L5 对话层   _retrieve → _dialogue_prompt / _reply_prompt → LLM
```

## 2. 判据（先写死，事后不得改）

统一口径：**一切比率的分母在取数前固定**；分母为 0 的一律写「不可判」，不许写 0%。

### L1 剂量层
- 指标：`E_m = 84 × prob_bp(m) / 10000`（每机制 84 回合理论触发期望），`N_m` = 84 回合实际触发条数。
- **判据**：若 `E_m < 1`，则该机制在本规模下**本身就是稀有事件**——即使 `N_m ∈ {0,1}` 也**不得**判为"实现有 bug"；只能判「**剂量过低（配置问题）**」。
- 若 `N_m > E_m + 2σ_m`（`σ_m = sqrt(E_m)`）则判「剂量/实现不一致，需查 roll 实现」。
- 汇总判据：`ΣE < 3` ⇒ **事件密度不足**（一周模拟里宏观事件 <3 次）。

### L2 触发层
- 指标：对每个 (mechanism, round) 组合复算 `roll`，与实际日志 `payload.rng_branch.roll_bp` **逐条比对**（要求全等，字符级一致）。
- **判据**：全等 ⇒ 触发逻辑可信（RNG 先定、无隐藏分支）；出现不等 ⇒ 判「触发逻辑与日志不一致，链路诊断作废」。

### L3 影响面层
- 指标：`affected_scope_count` 是否等于按 `scope.level` 解析出的受影响对象数（`global` → 全体存活 agent 数；`place` → 当时该地 agent 数）。
- **判据**：≥1 条 `WORLD_GROUP_EVENT` 满足"值 == 解析值 且 >0" ⇒ **接通**；恒为 0 且 `scope.level=global` ⇒ **未接通**（须给代码位置与行号定性：是解析缺陷还是字面量）。

### L4 感知层
- 指标 A（暴露）：某 agent 在 round t 的 `visible_events` 中是否含该 `WORLD_DIRECTIVE/WORLD_GROUP_EVENT`（可复算，纯函数）。
- 指标 B（沉淀）：`MEMORY_WRITE` 中 `source_event_seq` 等于世界事件 seq 的条数 `M`；`OBSERVATION` 中 `target_event_seq` 等于世界事件 seq 的条数 `O`。
- **判据**：暴露 = 真 但 `M=0 且 O=0` ⇒ 判「**感知到但未沉淀**」（断点在观察白名单）；暴露 = 假 ⇒ 判「感知层未暴露」。

### L5 对话层
- 指标：① `_dialogue_prompt` / `_reply_prompt` 装配串中是否含世界状态行（代码判据，给行号）；② 对话消息 payload 的 `refs` 中是否出现过世界事件 seq；③ 是否存在由世界事件记忆参与的检索（`MEMORY_RETRIEVE.selected_mem_ids` 指向世界事件记忆）。
- **判据**：①②③ **全为否** ⇒ 判「**世界层事件对对话零暴露**」（这是本轮最重要的一句结论，必须原样写）。任一为是 ⇒ 判"有暴露路径"，并写清是哪一条。

### L6 消费层
- 指标：`world_params()` 可能非空的三个字段 `activity_weight` / `resource_factor_bp` / `market_scarcity_bp`，各自在**非测试代码**中的读取点（`grep` 原文为准）。
- **判据**：某字段只出现在"是否非空"的计数布尔里（不参与任何数值/分支决策）⇒ 判「**无功能消费点**」；有 ⇒ 判"已消费"，并给文件:行。

### 总判据（一句话，写死）
> **L1–L6 六层全部接通才算「链路接通」。任一层 FAIL 即「未接通」，报告必须点名断点层；严禁用"提高剂量"冒充"链路接通"。**

## 3. 允许的读数变换（防止事后加戏）
- 只允许：计数、期望值、Poisson 参考概率、最小/最大值、重算比对。
- 不允许：任何"效果显著/明显改善"式表述；不允许跨分母比较；本批单 seed 不外推。

## 4. 提交约定
- 本文件与 `D8-world-director-diagnosis.md` **同批提交**（同一 commit），commit 由 report-writer 执行；
- 若诊断过程中发现判据本身有缺陷，**只允许追加"判据修订记录"并保留原文**，不得删改原判据。
