# T336 · 独立复核：`PERSONA_DRIFT` 情感判据口径（`273015c`）

- 复核人：sandbox-test-lead（**非作者**）｜ 结论落盘：`v2/refs/T336-emotion-criterion-review.md`
- 绑定：口径 sha **`273015c`**（08 §1.2 X，最新）；证据 sha **`352e9a4`**（T326 真 LLM 探针）
- 范围：**只核口径文档，不涉码**（实现在 T333，其复验另开）；**只读、未改任何码/文档**。

---

## 结论速览

**可判为「已登记」** —— 四条**逐条过**；反向验证证明检查**非恒绿**（早期版本被判红）。

| # | 条目 | 结论 | 依据 |
|---|---|---|---|
| 1 | 可复核性 | **过** | 词表/正则/极性表**可枚举**；判定式**唯一** `sign(text)`；**否定结论扫描口径**已给（对象 `kind=="reflection"` 的 `MEMORY_WRITE`；分母两档：全量 / `importance≥7`；命中 = `sign≠0` 计数）|
| 2 | 与证据一致 | **过** | 口径引「`life/agent.py:861-864` 的 26 子串（POS13+NEG13）」**逐条对得上**（见下 A）；`T326` 读数「真 LLM `0/63`（`importance≥7` 子集 `0/42`）」在文案中**无失真** |
| 3 | 两档 + `strict` 等价 | **过** | 一等键 `persona_drift.criterion ∈ {strict,natural}`、**默认 `natural`**；**`strict` ⟺ 现 26 子串逐字节等价**已明写（消融基线）；消融走 `run_override` 内存 override |
| 4 | `T300` 影响声明 | **过** | 明写 **【行为变】**（默认 `natural` ⇒ 候选/`PERSONA_DRIFT` 发射变）+ **【指纹变】**（新增键落 `life_v2.json`；该文件确在 `FINGERPRINT_FILES`，见下 A）+ **重冻前必须落定** |

---

## A. 证据核对（可复算）

**26 子串 ↔ `life/agent.py:861-864`**（脚本读源码常量）：
```
_DRIFT_POS n=13: 帮助 成长 喜悦 连接 感谢 陪伴 温暖 成功 support growth joy connect thanks
_DRIFT_NEG n=13: 冲突 失败 孤独 失去 争吵 痛苦 挫折 焦虑 conflict loss lonely fail struggle
total = 26   ⇒ 与口径声明 POS13+NEG13 一致 ✓
```
**`FINGERPRINT_FILES`**（`code/engine/version.py:18`）**含 `life_v2.json`** ✓ ⇒ 口径「新增键 `persona_drift.criterion` 落 `life_v2.json` ⇒ 指纹变」成立。

**命令（口径）**：`grep -nE "PERSONA_DRIFT|criterion|strict|natural" v1.1/08-engine-stats-extension.md`；`sed -n '861,864p' code/life/agent.py`；`sed -n '18,31p' code/engine/version.py`。

---

## B. ⚠️ 反向验证（证明检查非恒真）

对**同一份检查清单**施加到 `T332` 的三个历史版本（口径 §1.2 X）：

| 版本 | `criterion` | `strict` | `natural` | `逐字节等价` | `扫描口径` | 本清单判定 |
|---|---|---|---|---|---|---|
| `d5588ef`（初登） | 0 | 0 | 0 | **0** | 2 | **红**（缺 strict 两档/等价定义）|
| `1b8d209`（修订B） | 0 | 2 | 3 | **0** | 2 | **红**（无「逐字节等价」等价定义）|
| **`273015c`（被验）** | 2 | 3 | 5 | **1** | 2 | **绿** |

⇒ **同一清单**：早期版本**判红**、被验版本**判绿** ⇒ 「缺 `strict` 等价定义 ⇒ 必须判红」**确实会红**，检查**不是恒绿**。
（`d5588ef` 连 `strict/natural` 都无；`1b8d209` 有 strict 但**无「逐字节等价」明写**——正是 Leader 硬要求「未写全 ⇒ 判红不放过」要拦的点，并在 `273015c` 补齐为 `1`。）

命令：`git show <sha>:v1.1/08-engine-stats-extension.md | grep -c "<关键词>"`。

---

## C. 供下游注意（非口径缺陷，但易误读）

1. **任务描述里的「形态」是旧的**：T336 正文写「形态 = `config/emotion_lexicon.json` 单一来源 + 入 `FINGERPRINT_FILES`」，那是 **`1b8d209` 的形态 B**；**`273015c` 已改为【代码级判据（`life/agent.py` 常量 = 单一真源）+ 08 本节登记 + 一个可消融键】**，**明写「不要求逐词进 config」**。实查：`code/config/emotion_lexicon.json` **不存在**、指纹里**无**该文件。
   - ⇒ **`T333` 实现须按 `273015c` 的形态（代码级）**，勿按任务正文的旧形态新建 config 文件。
   - ⇒ 「指纹变」在 `273015c` 下**只来自新键 `persona_drift.criterion`（落 `life_v2.json`）**，**不来自**词表文件。
2. `strict` 档语义 = 「仅 26 显式子串（结构与极性兜底**关闭**）」——口径以「等价现状」表述，实现时须确保 `strict` 下 **(b)结构信号/(c)极性表不参与**（T333 落地时按其复验另行核对）。

---

## D. 验收对照

- 四条逐条结论（过/不过 + 依据）：见 §结论速览 + §A ✓
- 反向验证已红一次的证据：见 §B（`d5588ef`/`1b8d209` 判红）✓
- 「可/不可判为已登记」：**可判为已登记**（`273015c`）✓

*（T336 复核结束 — sandbox-test-lead，非作者独立复核）*
