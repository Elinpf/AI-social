# T333 证据：情感/漂移候选判据（`criterion ∈ {strict, natural}`）

- **实现 sha（最终）**：`b48920c`（收紧结构兜底；其上 `2c684d4` 去硬编码/落键、`664909a` 剔除 `（insight k）` 包裹）
- **单一真源**：`life/emotion.py::emotion_sign(text, *, criterion, lexicon)`；`life/agent.py` 改调它；`tools/t271/emotion_probe.py`（`T337`/`e639a02`）**import 同一函数**（非复制）——canonical 复算两侧一致。

## 口径（T332 `273015c` 08 登记）
- 判定式：`sign(text)= +1 命中POS；-1 命中NEG；else 结构信号兜底；else 0`；**显式词表优先**。
- `strict` ⟺ **现 26 显式子串逐字节等价**（消融基线；结构/极性兜底关闭）。
- `natural`（默认）= 扩词表（隐性线索）+ **结构信号**（动作括号/语气让步/省略号破折号/第一人称评价/句末[？！]**分 5 类**）+ 极性兜底；
  **收紧**：**单类不算命中，需 ≥2 类共现**（`_STRUCT_MIN_CATS=2`；避免"近乎恒真"伤人格稳定）。
- 一等可消融键 `persona_drift.criterion` 落 `life_v2.json` + `PD.DEFAULTS`（**与消费者同批**）；`run_override` 可一键切（内存 override、不改盘）。

## 实测（真样本 `/root/t271/runs/t326_real/` 63 条 reflection 正文，离线、无端点）
| criterion | 命中 | 备注 |
|---|---|---|
| `strict` | **0/63 = 0%** | ≡ `T326` |
| `natural`（收紧后） | **18/63 = 28.6%** | 有区分度；≤ 人眼参照 |

- **人眼参照 = `2/5 = 40%`**（**用户，2026-10-13 09:06**；**样本为 Leader 挑选的 5 条、非随机** ⇒ **参照值本身有偏**；偏差方向：挑样情绪比例偏高 ⇒ 真人眼比例可能更低 ⇒ `28.6%` 更不偏宽）。
- **裁定**：`natural` 定档（28.6% ≤ 40% 且方向保守）；`strict` 保留消融基线。
- 过程修正链（有据）：`63/63`（误触发，`（insight k）` 包裹被当动作括号）→ `664909a` 修根因 → `57/63` → `b48920c` 收紧 ≥2 类 → **`18/63`**。

## 合成单测（贴"合成"标签；结论限定合成场景）
`life/tests/test_t333_emotion_criterion.py`：`strict` 逐条等价旧 26 实现；隐性/结构文本 strict 不命中、natural 命中；agent 候选随 `criterion` 变。

## 回归 / 门禁
`make verify` **绿**（含前端 CI）。

## ⚠️ 对 `T300` 重冻的影响（写明）
**【行为变】**（默认 `natural` ⇒ 候选/`PERSONA_DRIFT` 发射变）**+【指纹变】**（新键 `persona_drift.criterion` 落 `life_v2.json`，该文件在 `FINGERPRINT_FILES`）⇒ **必须在 `T300` 重冻前落定**（一次冻到位）。

## 状态
**门/判据类：不自标 completed** —— 待**非作者独立核**（`T341`）：`strict` 逐条等价（N/N）、两档一键可切、生产同函数复算两数、**反向验证必红**、确认"结构 ≥2 类共现"真生效（单类必须不命中）。
