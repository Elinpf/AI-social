# Fork B 口径全库回写清单 · `forkb-rewrite-log.md`

> 作者：delivery-reviewer（T218）｜ 时间：2026-10-12
> 任务：扫全库，凡仍以「**逐位一致 / 字节相等**」作为**要求 / 验收口径**处，统一到「**放开"必须可复现"、保留"可被复算"**」。
> 口径来源：Leader Q-12.1 裁决。**单一口径定义**见 `v2/refs/gate-grading.md`（**本清单不复制口径定义**）。
> 纪律：保留历史结论**不清删**、用**时效标注**；判断不该改的**单列并给理由**。

---

## 0. 一句话口径（仅指针，不复制）

> **放开"必须可复现"（跨跑/字节相等**作门禁**取消），保留"可被复算"（`replay(log)` 代码确定性 + 全量日志 + 种子化 + 产物 sha/命令）。** → 详见 `v2/refs/gate-grading.md`。

---

## 1. 已回写（加「Fork B 时效标注」一行指针）—— **14 份**

| # | 文件 | 改了哪一条（新增标注，未删原文） |
|---|---|---|
| 1 | `v1.1/00-architecture.md` | 标题后加标注：§5.4 复现口径 / §6 AR-C9 → 放开"必须可复现"、保留可复算 |
| 2 | `v1.1/08-engine-stats-extension.md` | 加标注：X5 / §5.3 / §5.4 / §6 的「字节相等」降诊断 |
| 3 | `v1.1/09-sandbox-v1.1.md` | 加标注：可复现性判据 → 全量日志 + 种子化 + sha/命令 可追溯 |
| 4 | `v1.1/07-emergence-observation.md` | 加标注：字节相等降诊断 |
| 5 | `v1.1/17-narrative-layer.md` | 加标注：逐位一致作验收处 → 保留可复算 |
| 6 | `v1.1/10-v1.1-proposal.md` | 加标注：同上 |
| 7 | `v1.2/01-implementation-architecture.md` | 加标注：§0 铁律 **(C2)** 字节相等降诊断（C1/C3 不变） |
| 8 | `v2/00-roadmap.md` | 加标注：同上 |
| 9 | `v2/02-social-v2.md` | 加标注：`metrics` 字节相等 / `replay` 逐位 → 降诊断 |
| 10 | `v2/04-exchange-and-contracts.md` | 加标注：§V6 验收 / `state_hash` → 降诊断 |
| 11 | `v2/refs/story-and-event-engine.md` | 加标注：E-1 / S-3 逐位一致 → 降诊断 |
| 12 | `v2/refs/world-director-design.md` | 加标注：§0.3/§2/§6/§7 保底(c) → 保留可复算、不判字节 FAIL |
| 13 | `v2/refs/devtools-requirements.md` | 加标注：§S-1 跨跑一致 → 降诊断；**并澄清 §V-2"聚合数字与 obs 报告逐位一致"属同一计算口径一致性，仍为必须、不改** |
| 14 | `research/reproducibility-survey.md` | 加标注：§「我们的含义/主张」为 v1.1 口径 → Fork B 修正 |

> 标注统一形如：`> **【Fork B 时效标注 · 2026-10-12】** …（单一口径见 v2/refs/gate-grading.md）`。

---

## 2. 已由**对应作者/前序**处理，**我未改**（避免重复/覆盖）—— 7 份

| # | 文件 | 已有 Fork B 处理 |
|---|---|---|
| 1 | `v2/refs/quality-gates.md` | §7 已写「不把逐位可复现当验收口径」 |
| 2 | `v2/refs/world-event-mechanisms.md` | CF-7 / §5 已写 |
| 3 | `v2/refs/build-and-release.md` | §6.2/§7 已写（还正确区分了三类一致性） |
| 4 | `v2/refs/persona-memory-engineering.md` | §8 注记已定案 |
| 5 | `v2/refs/python-plugin-architecture.md` | 已写「Fork B 利好」 |
| 6 | `v2/refs/m2b-implementation-design.md` | 已写「Fork B 后不再以逐位重放为口径」 |
| 7 | `v2/refs/scale-50-efficiency.md` | §7-M4/§10 已写（obs，commit `d1b4d3d`） |

---

## 3. 判为**不该改**（单列 + 理由）

| # | 文件/类别 | 理由 |
|---|---|---|
| 1 | `code/README.md`（"重放逐位一致"） | 这是**内核能力**（保留的"可被复算"），**不是验收门禁** → 仍成立，**不改** |
| 2 | `code/reports/*.md`、`v2/evidence/*`、`v1.2/evidence/*`、`T*-evidence.md` | **历史证据**（记录某次跑出的结果），**不得改写历史** |
| 3 | `v1/03-engine-stats.md`、`v1/04-sandbox-plan.md`、`v1/05-v1-proposal.md` | **v1 冻结基线**（历史）；口径以 v1.1+ 为准 |
| 4 | `research/town-life-brief.md`（"确定性统计程序逐位一致"） | **度量特性描述**（非验收门禁）→ 不改 |
| 5 | `v2/refs/cordis-dsh-feasibility.md` | 已归档（Fork A=B）；其中"同日志逐位一致"作**内核能力**引用仍成立 |
| 6 | `v1.1/11-agentopia-reuse-assessment.md`、`12-event-lineage.md`、`13-wellbeing-metrics.md`、`14-agent-impl-reuse-map.md`、`15-event-census-spec.md`、`16-project-goal-options.md`、`06-life-layer.md` | **豁免判据**（Leader 2026-10-12 确认）：① 这 6+1 份的"逐位/复现"表述**均为"能力/评估/谱系/指标口径"描述，而非"验收门禁断言"**——即**没有一条以"不逐位一致就 FAIL"的形式约束交付**；② 其口径**由 `v1.1/00 §5.4` 统领**（已回写标注），属**被统领覆盖**而非独立口径源；③ 逐份改会**制造"第二份口径"**（违"口径唯一不复制"）。→ **豁免，但留此判据备查** | 
| 7 | `v1.2/03-pov-visibility-check.md`、`v1.2/real-llm-validation.md`、`v1.2/t35-green-restore-report.md`、`v1.2/evidence/*` | POV 可重算（保留能力）/证据报告 → 不改 |
| 8 | `glossary/LEXICON.md` | 术语条文（mention），非验收口径 |

---

## 4. 不属本口径（NA，仅提及）

`v2/evidence/panel_contract.md`、`event_card_*.md/json`、`metrics_*.md`、`v2/t139-*.md`、`v2/03-dialogue-llm-plan.md` 等——「逐位/parity」为**描述性提及**，非"要求/验收"，**不动**。

---

## 5. 统计

- **命中文件**（`逐位|parity|字节相等|同 seed|跨跑`）：**约 65** 份。
- **已回写**：**14**；**作者已处理**：**7**；**判不改**：见 §3；**NA**：见 §4。
- **未删任何历史结论**；全部用**时效标注**（团队既有惯例）。
- **白名单一致性（**显眼处**）**：⚠️ **「逐位一致」在本库有两个含义，必须分开**：
  - **(a) 跨跑复现**（同一输入重跑字节相同）→ **已放开**；
  - **(b) 同一口径下两处计算必须给同一个数**（如 `devtools §V-2` 工具聚合数字 = `obs` 报告数字）→ **绝对不能放开**（放开即"同名不同义"，无门禁会报警——只会"两个数慢慢开始不一样"）。
  - 故 `devtools §V-2` **刻意不改**；**一次机械全库替换会把 (b) 一并删掉**，这正是本清单**人工逐条读**的理由。

---

*（回写清单 — delivery-reviewer，T218；口径单一定义见 `v2/refs/gate-grading.md`）*
