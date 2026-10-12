# T334 探针参数化：`emotion_probe.py --pos-file/--neg-file`（自定义词表离线复算）

> 作者：release-engineer ｜ 2026-10-13 ｜ 任务：T334 ｜ 纯工具（`tools/t271/`），**未改 `code/`**，**未打端点**（只读 `T326` 已抓样本离线复算）。

## 1. 用法
```bash
# 默认词表（= life/agent.py:862-864 的 26 子串）
python3 tools/t271/emotion_probe.py /root/t271/runs/t326_real --samples 0
# 换词表（每行一词、# 注释、空行忽略）
python3 tools/t271/emotion_probe.py /root/t271/runs/t326_real --neg-file <neg.txt> --pos-file <pos.txt> --samples 0
```
输出关键行：`含情感词(hit any of N 子串): k/tot = ...%`。

**life 一行调用（T333 抽出 `emotion_sign(text, lexicon)` 后，用**你的**词表离线复算，不重打端点）**：
```bash
python3 tools/t271/emotion_probe.py /root/t271/runs/t326_real --pos-file <life_pos.txt> --neg-file <life_neg.txt> --samples 0
```

## 2. 实测
| 词表 | 命中 | `importance≥7` 子集 |
|---|---|---|
| **默认 26**（回归） | **0/63 = 0.0%**（**= T326，逐值一致** ✓） | 0/42 |
| **新词表**（demo：neg=`走了/没关系/闹腾/各家/擦了擦汗`） | **9/63 = 14.3%** ⇒ **换表命中变化** ✓ | 6/42 |

⇒ 回归（同词表读数不变）+ 换表（命中变化）**双条件**均验。

## 3. 与 life 判定函数对齐（消除双口径）
- **life 现式**（`code/life/agent.py:889-890`）：`sign = 1 if any(k in low for k in _DRIFT_POS) else (-1 if any(k in low for k in _DRIFT_NEG) else 0)`，`low=(text).lower()`。
- **探针同式**：`hp=[w for w in POS if w in low] ...; e = bool(hp or hn)` —— **同一判定式**（含任一 POS/NEG 子串）。
- ⚠️ **现状 = 两处口径（但同式子）**：`T333` 抽出 `emotion_sign(text, lexicon)` 后应**单一真源**——探针改为 **import life 的 `emotion_sign` + 传入 life 词表**（跨域 import 不便时，保留本参数化 + 等价自检）。
- **当前等价自检**：**同 26 词表下，探针读数（0/63）与 `T326` 一致** ⇒ 两实现（探针 vs life 式子）在**同词表上读数一致**（该式子对同输入确定）。

## 4. 备注
- 词表文件格式：纯文本、一行一词（子串匹配、大小写不敏感：探针内部对 text `.lower()`，词表建议小写）。
- 本任务**离线**（读 `/root/t271/runs/t326_real/` 的 63 条 reflection + `side/src/*.txt`）；**无新增端点调用**。
