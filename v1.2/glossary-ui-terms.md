# 界面术语中英对照表（角色卡 / tooltip 用）

> 任务：T76 交付面追加（leader 指派）　｜　作者：visual-researcher　｜　日期：2026-10-10
> 面向：**frontend-dev**（直接用于 UI / tooltip）、art-director、leader
> 用途：用户**看不懂角色卡里的英文键**。本表给每个术语：**中文名 + 英文键 + 一句话人话解释 + 数值/档位说明**。
> 权威来源：代码为准（`code/life/persona.py`、`code/life/constants.py`、`code/life/relations.py`、`code/config/personas.json`），非记忆。

---

## 0. 用法约定（给 frontend-dev）
- tooltip 建议格式：**中文名（英文键）** + 一句话解释 + 当前值对应的**档位**（如「外向性（extraversion）：30/100 · 偏低——偏安静、话少」）。
- 所有 `personality_big5` / `values` / `needs_init` 数值范围均为 **0–100 整数**。
- 档位统一口径：**低 ≤ 33 ｜ 中 34–66 ｜ 高 ≥ 67**（关系维度另有专门档位，见 §5）。

---

## 1. 五大人格（`personality_big5`，0–100）

| 中文名 | 英文键 | 一句话人话解释 | 低 / 中 / 高 |
|---|---|---|---|
| 开放性 | `openness` | 愿不愿意接受新事物、新想法、新体验 | 低：保守恋旧 ｜ 高：好奇爱尝鲜 |
| 尽责性 | `conscientiousness` | 做事是否自律、有条理、靠谱 | 低：随性拖延 ｜ 高：守时守规矩、认真 |
| 外向性 | `extraversion` | 从社交中获取能量还是消耗能量 | 低：安静话少 ｜ 高：爱热闹、主动搭话 |
| 宜人性 | `agreeableness` | 待人是否友善、配合、体谅 | 低：强势爱争 ｜ 高：随和好相处 |
| 神经质 | `neuroticism` | 情绪是否容易起伏波动 | 低：情绪稳 ｜ **高：情绪更易波动** |

> ⚠️ **方向易被误读，务必在 UI 标注**：`neuroticism` 是**负向命名**——**分越高 = 越容易焦虑/情绪波动**，不是"越好"。
> 建议两种可读写法（任选其一，二选一别混用）：
> 1. 显示 **「情绪稳定性」**，值取 **`100 − neuroticism`**，并注明"越高越稳"；
> 2. 保留 **「神经质（越高越易情绪波动）」**，显式写明方向。
>
> 代码里它是**确定性派生标量**的输入：`risk_appetite = (openness + (100 − neuroticism)) / 200`、`saving_propensity = (security + neuroticism) / 200`（`persona.py`）。

---

## 2. 价值观（`values`，0–100）

| 中文名 | 英文键 | 一句话人话解释 | 低 / 中 / 高 |
|---|---|---|---|
| 自主 | `self_direction` | 看重"按自己的意愿做决定"的程度 | 低：随大流 ｜ 高：要自主、不喜被指挥 |
| 仁爱 | `benevolence` | 看重关心、帮助身边人的程度 | 低：只顾自己 ｜ 高：热心利他 |
| 成就 | `achievement` | 看重"做出成绩、被认可"的程度 | 低：无所谓 ｜ 高：要强、想被看见 |
| 安全 | `security` | 看重"稳定、有保障、不冒险"的程度 | 低：敢闯 ｜ 高：求稳、爱存钱 |

---

## 3. 目标倾向（`goal_tendencies`，数组）

结构：`[{"kind": "...", "weight": 0.0–1.0}, ...]`。`kind` = 目标类型，`weight` = 该倾向的**强弱权重（优先级）**。
代码按 `kind → 层(layer)` 归类（`goals.py` / `constants.py`），周计划期由此**确定性**播种目标（GOAL_SET）。

| 中文名 | `kind` | 所属层（layer） | 一句话解释 | 权重档位 |
|---|---|---|---|---|
| 生存安全 | `security` | survival 生存 | 想活下去、稳住生计 | 弱 < 0.4 ｜ 中 0.4–0.7 ｜ 强 > 0.7 |
| 财富 | `wealth` | survival 生存 | 想多赚钱、攒家底 | 同上 |
| 精进 | `mastery` | growth 成长 | 想提升技能、变强 | 同上 |
| 成就 | `achievement` | growth 成长 | 想做出成果、被认可 | 同上 |
| 社交 | `social` | social 社交 | 想多与人来往、交朋友 | 同上 |
| 意义 | `meaning` | meaning 意义 | 想活得有价值、做有意义的事 | 同上 |

> 层名对 UI 可译为：**生存 / 成长 / 社交 / 意义**。目标进度 `progress` 为 **0–1**，`≥1.0` 记为达成（GOAL_ACHIEVED），由活动类型**确定性**推进（每匹配一次 +0.15）。

---

## 4. 说话风格（`speech_style`，枚举字符串）

结构：`{"tone": "...", "verbosity": "..."}`。

**语气 `tone`（8 种）：**

| 英文键 | 中文名 | 一句话解释 |
|---|---|---|
| `plain` | 平实 | 直接、不加修饰 |
| `warm` | 温和 | 亲切、让人舒服 |
| `blunt` | 直率 | 有话直说、略冲 |
| `calm` | 冷静 | 平稳、不激动 |
| `casual` | 随和 | 轻松、口语化 |
| `expressive` | 外放 | 情绪外露、有感染力 |
| `formal` | 正式 | 客气、书面、有分寸 |
| `playful` | 俏皮 | 爱开玩笑、活泼 |

**话量 `verbosity`（3 种）：**

| 英文键 | 中文名 | 一句话解释 |
|---|---|---|
| `short` | 简短 | 惜字如金 |
| `medium` | 适中 | 正常长度 |
| `long` | 健谈 | 话多、爱展开 |

---

## 5. 关系维度（有向：from → to）

每个方向 4 个维度。**范围与含义见下表**（`relations.py` / `constants.py`）。

| 中文名 | 英文键 | 范围 | 一句话解释 | 档位（低→高） |
|---|---|---|---|---|
| 好感 | `affinity` | **−100 ~ 100** | 喜不喜欢对方（可正可负） | **强负 ≤ −50**（敌意）｜负 −49~−1（不喜）｜**0 中性**｜正 1~49（有好感）｜**强正 ≥ 50**（亲密） |
| 信任 | `trust` | **−100 ~ 100** | 信不信得过对方 | 同 `affinity` 的负/零/正分档 |
| 尊重 | `respect` | **0 ~ 100** | 对对方能力/品行的敬重 | 低 ≤ 33 ｜ 中 34–66 ｜ 高 ≥ 67 |
| 熟悉度 | `familiarity` | **0 ~ 100** | 有多熟（**只增不减**） | 陌生 0–19 ｜ 相识 20–49 ｜ 熟悉 50–79 ｜ 挚友 80–100 |

**阈值（对 UI 有用）：** `EPS = 20`（|值|≥20 视为"有明显态度"）、`EPS_STRONG = 50`（"强烈/关系质变点"）。跨越阈值会触发一次**定性判定**（RNG 定分支 → LLM 在分支内贴标签 → 冻结；标签只有 `formed`/`not_formed` 两种），其数值后果是**确定性的**（`formed` → 好感+5、信任+3；`not_formed` → 好感−2）。
**单次交互幅度上限** `RELATION_DELTA_MAX = 10`（一次互动一个维度最多变 ±10）。

### 「关系怎么变的」——`RELATION_CHANGE.cause` 取值表

事件载荷：`{from, to, dim, before, after, cause, cause_event_seq}`。`cause` 说明这次变化的**原因**（数值由 cause **确定性**推出，LLM 不写数）：

| `cause` | 触发场景 | 造成的变化（每维，封顶 ±10） |
|---|---|---|
| `copresence` | **同处一地（同场所同回合）** | 好感 `affinity` += 1 × 时长（与现有好感同号；时长封顶 10） |
| `chat` | 两人对话 | 同 `copresence`（好感随互动方向微增/微减） |
| `trade_success` | 一次成功交易 | 信任 `trust` += 2·ln(1+金额)；好感 `affinity` += 1 |
| `transfer_rescue` | 救助/给对方转账（受助方视角） | 好感 `affinity` += 8；信任 `trust` += 6 |
| `ssl_flag` | 被判作弊/违规标记 | 信任 `trust` −= 5 |
| `encounter` | 初次/再次相遇 | 熟悉度 `familiarity` += 1 |
| `activity:<模板id>` | 参与某活动 | 按活动规则更新相应维度 |
| `decay` | 久未互动自然衰减 | 相应维度向 0 回落 |
| `soft_judgment` | 跨阈值的定性判定 | 由冻结标签推出（见上：formed/not_formed） |

> 另：**共处每回合 `familiarity` 单调 +1（封顶 100）**（`settlement.py`）；熟悉度是"时间自然积累"的主通道。

---

## 6. 附录：角色卡上其他常见字段（顺带给全）

| 中文名 | 英文键 | 说明 |
|---|---|---|
| 角色/身份 | `role_id` | 职业身份（如 `farmer`），决定工位 `work_place` |
| 住所 | `home_place` | 居住场所（多为 `residence`） |
| 背景 | `background` | 一句话人物小传 |
| 技能 | `skills` | `[{skill_id, level}]`，`level` 为等级 |
| 初始需求 | `needs_init` | 6 项 0–100：`energy` 精力、`satiety` 饱腹、`social` 社交、`esteem` 自尊、`mastery` 精进、`leisure` 休闲 |

---

## 7. 数据来源（可复核）
- `code/life/persona.py`：Big5/values/speech_style 字段与派生标量
- `code/life/constants.py`：`RELATION_RANGE`、`RELATION_DELTA_MAX`、`EPS/EPS_STRONG`、`KIND_TO_LAYER`、`GOAL_LAYERS`
- `code/life/relations.py`：`RELATION_COEF`、`rel_delta(cause)`、`JUDGMENT_DELTA`、`soft_judgment_envelope`
- `code/life/goals.py`：`goal_tendencies → Goal` 播种与 `GOAL_LAYERS`
- `code/config/personas.json`：20 位居民实例（含全部枚举取值）
- 与本表配套的观测台信息架构：`social-experiment/v1.2/obs-console-ux-spec.md`（T76）
