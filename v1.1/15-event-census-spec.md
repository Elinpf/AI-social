# 15 · 事件判定与普查报告规格 v1.1

> 归属：sandbox-test-lead（沙盒实验与验收负责人）
> 对齐基准（权威，不另立口径）：`07-emergence-observation.md`（T9，判定规则权威）、`12-event-lineage.md`（T14，20 类事件谱系）、`08-engine-stats-extension.md`（T8，事件 schema 权威）、`09-sandbox-v1.1.md`（T10，观测判据）
> 目的：回答「一次跑完，怎么查发生了什么事件、怎么判定高阶事件已发生」。产出**可直接实现**的事件普查报告规格。

---

## 0. 一句话结论

**事件类型与 schema 是封闭、标准化的**（内核事件表，T8 §1.2 + v1）；**事件「是否发生」是涌现的**——由「世界状态 + Agent 决策 + 种子化 RNG 分支」共同决定，**既非脚本编排、也非纯随机**。因此：**同一份日志**的普查结果**逐位可复现**；但**同 seed 跨跑不保证相同**（首跑含 LLM 判定，T8 AR-C9 / T9 §0.4）。

---

## 1. 两层事件结构

```
┌───────────────────────────────────────────────────────────────┐
│ L2 语义事件（20 类高阶事件，T14 E1–E20）                        │
│   如 Mentorship / Power Conflict / Group Proposal …            │
│   —— 不是内核产生的；由【确定性规则对日志做模式判定】得出         │
│   判定式：census_rule(EventLog, T, params) -> {hit, first, n}   │
└───────────────────────────▲───────────────────────────────────┘
                            │ 只读、确定性重算（T9 R1/R2；不调 LLM）
┌───────────────────────────┴───────────────────────────────────┐
│ L1 原子事件（内核落日志的标准化事件，封闭 schema）              │
│   T8 §1.2 A–K + v1 事件表：                                    │
│   ACTIVITY_STARTED / OFFER_ACCEPTED / TRANSFER /               │
│   RELATION_CHANGE / SKILL_LEVEL_UP / CONFLICT_RESOLVED / …     │
│   —— 只追加、哈希链、字段固定（缺字段即 bug）                    │
└───────────────────────────────────────────────────────────────┘
```

**两层关系**：每个语义事件 ⟺ 一组原子事件的**确定性模式**（§2 给出逐条判定式）。语义事件**不写回日志**（T9 R7：观测层只读），是 `census_report(log,T)` 的**侧产物**。

**原子事件全集（封闭）**：`08 §1.2 A–K` + `v1 §2.3`。语义事件引用**未登记原子事件**即报错（§5）。

---

## 2. 判定方法清单（逐语义事件，可读日志重算）

> 约定：`familiarity(a,b)`、`affinity(a→b)`、`skill_level(a,s)` 等均由对应原子事件（`RELATION_CHANGE`/`SKILL_LEVEL_UP`）**折叠**得出；阈值取 06/T14：`ε=20`、`ε_strong=50`、`θ_dep=20`、`N_round=3`、`W_burn`（待标定）。标 **[F]** 者含冻结 LLM 判定（读 `LLM_JUDGMENT.frozen`，计算时 `llm_calls==0`，结果入 `metrics.emergence_soft`）。

| # | 语义事件 | 判定式（伪代码，确定性） | 归属 |
|---|---|---|---|
| E1 | Mentorship | `is_mentorship(a,b) := same_skill(a,b) ∧ skill_level(a)−skill_level(b)≥2 ∧ familiarity(a,b)≥ε ∧ count(ACTIVITY_COMPLETED{template=mentorship, participants⊇{a,b}})≥2`；可选 `[F] LLM_JUDGMENT(dim=mentor_relation)` | D (+F) |
| E2 | Gift-giving | `is_gift(a→b) := ∃ TRANSFER{from=a,to=b,reason=gift} ∧ affinity(a→b)≥ε_strong` | D |
| E3 | Combat Training | `is_combat := ∃ ACTIVITY_STARTED{template=combat_training}`；对练胜负 `:= CONFLICT_RESOLVED{rule_ref=training}` | D (+R) |
| E4 | Creative Collab | `is_creative := ∃ ACTIVITY_COMPLETED{template=creative_collab, participants≥2} ∧ ∃ SKILL_OUTPUT`；`[F] creative_quality` 仅记评语 | D (+F) |
| E5 | Saving Money | `is_saving(a) := ∃ DEPOSIT/WITHDRAW{a}` **或** `TRANSFER{a↔银行 SYSTEM}`（命名待 econ，T14-C3） | D |
| E6 | Whispered Comm. | `is_whisper(a→b) := ∃ MSG_DM{from=a,to=b,visibility=private} ∧ affinity(a→b)≥ε`；可选 `[F] secret_trust` | D (+F) |
| E7 | Emotion Burnout | `is_burnout(a) := (need.energy<θ_dep ∨ need.leisure<θ_dep) 连续 ≥W_burn 时段 ∧ 负荷高(a)` → `STATE_CHANGE{to=exhausted}` | D |
| E8 | Diff. Scoring | `is_contest := ∃ SCORE_POSTED{contest_id} ∧ ∃ RANKING_EMITTED{contest_id}`；`[F] qualitative_review` 不进排名 | D (+F) |
| E9 | Scarcity Buy | `is_scarce_buy := ∃ MARKET_TRADE{good} ∧ 稀缺指数(good)≥θ_scarce`（订单簿深度低） | D |
| E10 | Skill Practice | `is_skill_practice(a,s) := ∃ SKILL_PRACTICE{a,skill_id=s}`（可含后续 `SKILL_LEVEL_UP`） | D |
| E11 | Polite Rejection | `is_polite_reject := ∃ OFFER_REJECTED ∧ ¬(同回合 INTENT_REJECTED for 同 offer)` | D (+F) |
| E12 | Passion vs Salary | `is_job_choice(a) := ∃ ROLE_CHANGE{a} ∧ (曾 OFFER_CREATED{kind=job} ∨ utility 冲突超阈)`；`[F] job_preference` 仅记录 | D (+F) |
| E13 | Group Proposal | `is_proposal(n) := ∃ NORM_PROPOSED{norm_id=n} ∧ ∃ NORM_ADOPTED{norm_id=n, support≥threshold}` | D |
| E14 | Academic Collab | `is_academic := ∃ ACTIVITY_COMPLETED{template=academic_collab, participants≥2} ∧ ∃ (SKILL_LEVEL_UP ∨ SKILL_OUTPUT)` | D (+F) |
| E15 | Counter-propose | `is_counter(o) := ∃ OFFER_COUNTERED{offer_id=o} ∧ round_no≤N_round` | D |
| E16 | Select Location | `is_location(a) := ∃ PLACE_MOVE{a}`（`LOCATION_SELECTED` 已并入，T14-D14-3） | D |
| E17 | Power Conflict | `is_conflict(c) := ∃ CONFLICT_STARTED{conflict_id=c} ∧ ∃ CONFLICT_RESOLVED{conflict_id=c, winner≠⊥}` | D (+R) |
| E18 | Rel. Acceptance | `is_rel_accept(a,b) := [F] LLM_JUDGMENT(dim=friendship_label, decision=accept, parties⊇{a,b}) ∧ ∃ RELATION_CHANGE{affinity 跨 ε_strong}` | F+D |
| E19 | Ice-breaking | `is_icebreak(a,b) := 首次 RELATION_ENCOUNTER{a,b} ∧ 当时 familiarity(a,b)<ε ∧ ∃ MSG_{a↔b}`；可选 `[F] first_impression` | D (+F) |
| E20 | Rel. Maintenance | `is_maint(a→b) := ∃ RELATION_CHANGE{a→b} ∧ (last_interaction_round 距前者 > D_maint)`（衰减或维护动作） | D |

**判定纪律**：所有判定式**只读日志**、`llm_calls==0`；`[F]` 项**只读冻结值**、单独计入 `metrics.emergence_soft`，**绝不进入判定/门禁**（T9 R2–R4、AR-C3）。对抗/评分（E3/E8/E17）的**胜负/名次全部 D+R**，LLM 不当裁判（T14 §3）。

---

## 3. 事件普查报告格式（一次运行 / 一轮 seed 结束输出）

```jsonc
{
  "schema_version": "1.1",
  "engine_version": "v1.1+<embed_frozen>",   // 纳入 TOPOLOGY/模板文件指纹（T8 AR-D2/D7-6）
  "seed": 12345,
  "rounds": 84, "weeks": 1, "N": 20,
  "log_hash": "sha256:…", "log_last_seq": 98765,   // 复现锚
  "atomic_freq": {                            // ① 原子事件频次表（按 type 计数）
    "ACTIVITY_STARTED": 210, "ACTIVITY_COMPLETED": 198, "TRANSFER": 340,
    "OFFER_ACCEPTED": 41, "RELATION_CHANGE": 512, "SKILL_LEVEL_UP": 63, "…": 0
  },
  "semantic_hits": {                          // ② 语义事件命中表（20 类逐条）
    "E1_mentorship":        {"hit": true,  "first_round": 37,  "participants": 6,  "count": 4},
    "E17_power_conflict":   {"hit": false, "first_round": null,"participants": 0,  "count": 0},
    "…": {"hit": false, "first_round": null, "participants": 0, "count": 0}
  },
  "miss_list": ["E4_creative_collab","E8_diff_scoring","E12_job_choice","E13_group_proposal","E17_power_conflict"],  // ③ 未命中清单（含难触发项）
  "coverage": {                               // ④ 覆盖度 / 孤立检查
    "atomic_types_registered": 42,
    "atomic_types_observed": 31,
    "atomic_registered_unused": ["NORM_VIOLATED", "…"],   // 登记但本 run 未产生（区分「留给未来」与「疑似遗漏」，见 09 §7.1）
    "unknown_types_seen": []                              // 非空即报错（§5）
  },
  "reproducibility": {
    "same_log_bitwise": true,        // census_report 对同一日志两次运行字节相等（硬门禁）
    "cross_run_same_seed": false,    // 含 LLM 判定，跨跑不保证（AR-C9）
    "llm_judged_metric_count": 0,    // 语义判定中 F 类必须为 0（F 单列 emergence_soft）
    "contains_frozen_llm": true      // 本 run 是否读到 LLM_JUDGMENT（敏感性标注）
  },
  "guard_diagnostics": {             // 与沙盒护栏/观测判据对接（§6）
    "observer_injection_count": 1, "safety_valve_triggered": false,
    "rescue_flag_count": 0, "guardrail_ok": true, "death_count": 2
  }
}
```

**配套人类可读表**：① 原子频次 Top-N（按 type/phase/日-周切片）；② 语义命中表（20 行，hit/first/participants/count）；③ 未命中清单 + 难触发标记（E4/E8/E12/E13/E17，T14 §5 ⚠️）；④ 覆盖度报告。

---

## 4. 随机性 vs 可复现性（关键澄清）

| 维度 | 性质 | 依据 |
|---|---|---|
| **事件类型 / schema** | **封闭、标准化**：只在 T8 §1.2 与 v1 表内；新增需登记 | T8 X1/X4；T14 §2 |
| **事件「是否发生」** | **涌现**：由「世界状态 + Agent 决策 + **种子化 RNG 分支**」共同决定；RNG 先定分支、LLM 只填充内容（LLM 不掷骰子） | T12 §5、T14 §0 |
| **非脚本编排** | 无预写剧情；20 类事件由**机制使其可能发生**，非定时触发 | T14 §5 可产生性自查 |
| **非纯随机** | 分支由 `(seed, stream_id, round, seq)` 确定性抽取，可审计 | T8 §1.4 |
| **同日志普查** | **逐位可复现**：census 对同一日志两次运行字节相等 | T9 §0.4、T8 AR-C9 |
| **同 seed 跨跑** | **不保证一致**（首跑含 LLM 判定 `LLM_JUDGMENT`） | T8 AR-C9 |

> 因此：**「标准化」指类型/schema，「涌现」指是否发生**。二者不矛盾——标准化的是**语言**，涌现的是**说没说这句话**。

---

## 5. 异常检查（普查前置校验，任一命中即报错）

| 检查 | 触发条件 | 处置 |
|---|---|---|
| 未知事件类型 | 日志中出现 T8 §1.2/v1 之外的 `type` | **硬报错**（重放器同款，T8 X4）；不入普查 |
| 引用未登记事件 | 语义判定式引用未登记原子事件 | **硬报错**（阻断普查，防口径漂移） |
| 判定缺字段 | 判定所需 payload 字段缺失（如 `RELATION_CHANGE.after`） | **硬报错**（T8 强制字段） |
| 观测锚点悬空 | `OBSERVATION.target_event_seq` 指向不存在事件 | **硬报错**（T8 不变量 10） |
| 哈希链断裂 / seq 非单调 | 日志完整性破坏 | **拒绝普查**（T8 §6.4） |
| 非确定复现 | 同日志两次 `census_report` 字节不等 | **硬失败**（CI gate） |

---

## 6. 观测用途：普查 → T10「有意义的涌现」

普查报告是 `09-sandbox-v1.1.md` §1.2 观测判据的**输入**：

1. **种子级联**（T9 §2.3）：由 `SEED_EVENT` + `OBSERVATION`/`MSG_*.refs` + 普查的语义命中共同界定级联图 → 计算 `cascade_size/depth/R0/reach_ratio`。
2. **「突现成立」**：`reach_ratio≥θ_reach ∧ depth≥2 ∧ R0≥1.0 ∧ time_to_spread≤1 周 ∧ A/B 显著 ∧ 配额终止<θ_cap`（T9 §2.3）。
3. **覆盖度判据**：语义命中表须在 **≥K 类**上非空（K 待沙盒标定），且**难触发项（E4/E8/E12/E13/E17）至少命中 1 类**方算「社会丰富度足够」；全未命中则判「世界未涌现」。
4. **无系统性观测偏差**：`llm_judged_metric_count==0`、`narrative_reads_in_decision==0`、`observer_injection_count` 显式记录。
5. **护栏联动**：`guard_diagnostics.guardrail_ok=false` 的窗口，其涌现判定**降级为参考**（T9 §5.3）。

> 一句话：**普查报告 = 「发生了什么」的事实底账；观测判据 = 在底账上判定「是否算有意义的涌现」。**

---

## 7. 与 07/12/08 的口径一致性声明

- 判定式全部由 **07（T9）§1.1–§1.6 规则 + 12（T14）§1 触发条件**合并而来，**未自创口径**；阈值取 06/T14（`ε/ε_strong/θ_dep/N_round`）。
- 原子事件名以 **08 §1.2（含 K 组协商/评价/冲突）** 为准；命名差异（如 `OFFER` vs `OFFER_CREATED`）已在 `09 §7.1` 列为「需统一到 08」。
- F 类处理遵循 **T9 R1–R7 + T15 §3**：冻结可读、不可算、分栏列示、出门禁。

---

*（规格 v1 — sandbox-test-lead；可直接实现；判定式无歧义、可重算；明确区分「标准化」与「涌现」。）*
