# T341 · 独立复核：`T333` 情感判据【实现】（`b48920c`）

- 复核人：sandbox-test-lead（**非作者**）｜ 落盘：`v2/evidence/T341-emotion-criterion-impl-review.md`
- 绑定被验 sha：**`b48920c`**（`life/emotion.py` 最新；其后无提交改它）｜ 真样本 run：`/root/t271/runs/t326_real/`（**63** 条 `kind=="reflection"`）
- 自建脚本：`v2/evidence/t341_emotion_impl_verify.py`（**不用作者单测**）；运行：`cd code && PYTHONPATH=$(pwd) python3 ../v2/evidence/t341_emotion_impl_verify.py`
- 只读、未改 `code/`。

---

## 结论：**可判为「已定档」**（`natural`）

五项**全过**；反向验证证明检查**非恒真**。

| # | 验收项 | 结果 |
|---|---|---|
| 1 | `strict` 逐条等价旧 26 子串实现 | **PASS**：corpus 76/76 相等，差异=0（含 63 真样本 + 13 对抗样本） |
| 2 | 两档一键可切且行为随之变 | **PASS**：真样本上 `strict≠natural` 18 条；`life_v2.persona_drift.criterion='natural'`；`agent.py` 读该键 |
| 3 | 生产同函数复算两数 | **PASS**：`strict 0/63`、`natural 18/63`（`importance≥7` 子集 `0/42`、`12/42`）—— 复现作者读数 |
| 4 | 反向验证必红 | **PASS**：人为把 NEG 优先 ⇒ 与旧实现差异=1 ⇒ 检出=红 |
| 5 | 确认「≥2 类共现」真生效 | **PASS**：单类（动作括号/省略号/问号/第一人称）**均不命中(0)**；两类共现命中(−1) |
| 6 | 口径（样本/命令/seed）写进报告 | ✓（见本文件） |

---

## 1. `strict` 逐条等价旧实现（**不是"看起来像"**）

- **旧实现**（`2c684d4^:code/life/agent.py:888-890`）：`low=(text).lower()`；`1 if any(k in low for k in _DRIFT_POS) else -1 if any(..._DRIFT_NEG) else 0`（POS 优先，无包裹剔除）。
- **新 strict**（`emotion_sign(criterion="strict")`）：先 `_WRAPPER_RE.sub("", text)`（剔 `（insight k）`）再 `.lower()`；`STRICT_POS/NEG`；POS 优先；**结构兜底关闭**。
- **等价性**：差异仅在"剔包裹"与"结构兜底"，而包裹不含 26 子串、strict 关结构 ⇒ 对 26 子串判定**无影响**。
- **实测**：`old_sign(text) vs emotion_sign(text,"strict")` 在 **76/76**（63 真样本 + 13 对抗：`（insight k）` 包裹、大小写、POS&NEG 同现、省略号、单类结构…）**全等，差异 0** ✓。
  （`STRICT_POS/NEG` 与旧 `_DRIFT_POS/NEG` 亦逐项一致：13+13=26。）

## 2. 两档可切 + 行为随之变

- **键在盘**：`code/config/life_v2.json` → `persona_drift.criterion = "natural"`（**默认档**）。
- **消费者**：`code/life/agent.py:883` `criterion = str(pd.get("criterion","natural"))` → `E.emotion_sign(text, criterion=criterion)`（单一真源）。
- **行为随档变**：同一 63 真样本，`strict` 命中 0、`natural` 命中 18 ⇒ **改 criterion ⇒ 结果随之变**（消融可用）。`run_override` 内存 override 与 T317/T319 同路（不改盘/不改指纹）。

## 3. 复算两数（生产同一函数）

| criterion | 命中 / 63 | `importance≥7` 子集 |
|---|---|---|
| `strict` | **0/63 = 0%**（≡ T326） | 0/42 |
| `natural` | **18/63 = 28.6%** | 12/42 |

复现作者读数。人眼参照 `2/5=40%`（用户，非随机、偏高 ⇒ `28.6%` 更不偏宽）→ `natural` 定档合理。

## 4. 反向验证（必红）

把 strict 逻辑人为改成 **NEG 优先**（破坏"POS 优先"现状）⇒ 与旧实现在 `帮助和冲突`（POS&NEG 同现）**分歧=1** ⇒ 我的等价检查**检出=红**。⇒ 断言**非恒真**。

## 5. 「≥2 类共现」真生效（单类必须不命中）

| 文本 | 结构类数 | `natural` sign | 判定 |
|---|---|---|---|
| `（笑了笑）` | 1（action） | **0** | OK 单类不命中 |
| `……` | 1（ellipsis） | **0** | OK |
| `真的吗？` | 1（punct） | **0** | OK |
| `我觉得` | 1（first_person） | **0** | OK |
| `（笑了笑）啊` | **2**（action+tone） | **−1** | OK ≥2 类命中 |

⇒ `_STRUCT_MIN_CATS=2` 收紧**确实在生效**（单类不误命中；避免"近乎恒真"）。

## 6. 口径与边界

- 样本：`/root/t271/runs/t326_real`（真 LLM，63 reflection）；对抗样本 13 条（合成，仅测边界）。
- 命令：见头部；**未改任何码/文档**。
- 备注：`natural` 的**结构信号方向/词表**在 08 标【未验证】—— 本复核只验"实现与口径一致 + 两档/共现生效"，**不评"情绪词表质量"**（那属人眼/后续校准）。

---

*（T341 复核结束 — sandbox-test-lead，非作者独立复核）*
