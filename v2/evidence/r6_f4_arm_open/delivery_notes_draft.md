# R6-T3 交付说明（草稿，数字待跑批完成后填充）

> 状态：草稿（Arm-T 跑批中）。完成后所有 `TBD` 必须替换为带 sha 的实测值，缺一项不许交付。

## 1. 两臂定义与代码身份

| 项 | Arm-T（处理臂） | Arm-C（对照臂） |
|---|---|---|
| 批目录 | `v2/evidence/run_r6_treat_n16_seed42/` | `v2/evidence/run_r6_control_n16_seed42/` |
| 代码身份 HEAD | `6074502f4062891d05e1057df08243d11c3cb79d` | TBD（必须同 `6074502`） |
| 开关 | `HITT_DIALOGUE_REPAIR=1` | **不设该 env** |
| `code/config/dialogue_repair.json` | 提交态 `enabled=false`，sha `f0435571…e9eec`（**两臂均不改**） | 同左 |
| 规格 | 16 agents × 84 rounds × seed 42 | 同左 |
| 起跑时刻 | **2026-10-20T20:38:36** | TBD |
| 第三方 S0a 快照 | `s0a-snapshot-T-2038.md` sha `d8c7f201…7c2e8ab` | TBD |

**两臂均以 `6074502` 为代码身份；Arm-C 起跑前复核工具 pin 与 HEAD 未变。**

## 2. 批窗内的流程违规（如实记录）

- `e300c1f → 6074502` 期间有 3 条提交落地，其中 `024c519`、`6074502` 命中 `code/frontend/`；
- 按 `check_clean_tree.py` 前缀判**不阻断**（`code/life|orchestration|config|engine` 零改动，`git diff --stat` 为空）；
- 按冻结令原文属**批窗内写入 `code/`，流程违规**；
- **不阻断、不作废本轮**（Leader 20:37 裁定），但必须记录、不掩盖。

## 3. 失败留痕（不得用于任何读数）

- `v2/evidence/run_r6_treat_n16_seed42_ABORTED_2036/`：Arm-T 第一次起跑（20:24:43）被 SIGTERM 打断，34 行、无 meta。**不续跑、不补 meta、不引用。**

## 4. 读数（待填）

| 指标 | v0-anchor（历史列） | Arm-T | Arm-C |
|---|---|---|---|
| F-4 分子/分母 | 0 / 5 | TBD | TBD |
| F-4b `mean_lag_msgs` | null（无闭环样本） | TBD | TBD |
| F-3 分子/分母 | 1 / 6 | TBD | TBD |
| n_msgs | 187 | TBD | TBD |

口径：只报分子/分母 + 事件级事实；百分比仅括号参考并标"无 B2 上界带"；不给 CI、不做显著性判断。

## 5. 归因与可比性（核心，不可省略）

- v0 与 Arm-T 之间夹着 **D2 结构改造**（消息层 187 → 新规模，线程结构 legacy → explicit）⇒ **单靠 v0 对比不能把变化归因于修复机制**；v0 只作历史延续列。
- **Arm-C 是同代码、同规格、同 seed、仅开关不同**的唯一干净对照；
- 若 Arm-T 张力事件数明显高于 Arm-C，须写「**干预了回复优先级（相遇机会）**」，与"自发冲突"分开表述——这是干预披露，不是效果描述；
- `dialogue_rift` 只作**机制自报层**单列（"机制内部自报，非独立度量"），不与词表口径相加或互证。

## 6. 人工判读（仅 Arm-T 全量 + Arm-C 抽检 10）

- 判据：`prereg_f4_manual_judgement.md` sha `1f2c3316…bf7`（冻结，§2–§5 摘录副本删节说明见 §…）
- 抽样规则（先写后抽）：`prereg_armC_sampling.md` sha `a5cdd702…c5541e8`
- 覆盖不等：v0 = 5 条全量 / Arm-T = 全量 / Arm-C = 10 条抽检 ⇒ **人工层不构成三栏对比**，只作噪声量级注记
- 限制披露（原话）：①判据 §4 示例与本批个别条目同形，该部分标注存在部分引导，一致率对这几条不构成独立验证；②两人看到的是同一批判定条款（T1–T4 同源同版本）
- v0 侧第二标注一致性：一致 5 / 不一致 0（κ=1.0 仅参考，n=5 不稳定）

## 7. 脚本与 sha

TBD（逐项列：`dialogue_metrics.py` 5fede538 / `f4_repair_evidence.py` / `f4_manual_judge.py` / `build_annotation_packet.py` / `f4_interrater.py` / 词表 6 项 / `arm_open_record.py`）

## 8. 经验（下轮可复用）

1. **盲判要求判据先于数据冻结**；本轮先读数据后起草判据，顺序不可挽回，只能披露不能补救；下轮（如 F-3）必须"先冻结判据 → 再跑批 → 再判读"。
2. **批期冻结令必须覆盖"任何人不得 commit"**，否则 HEAD 漂移会让 `meta.code_sha` 与开批记录对不上；本次已因此废掉一批（ABORTED 2036）。
3. **进程组隔离**：`setsid --fork` + 校验子进程 SID ≠ 调用方 SID；`setsid &` 仍可能被外部信号带走。
4. **未提交的工具改动必须冻结字节**（patch + sha），否则工作区一被 `checkout` 就成悬案。
