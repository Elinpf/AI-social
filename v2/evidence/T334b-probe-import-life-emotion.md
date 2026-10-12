# T334b 探针接 life 单真源 + **canonical 复核**（与 life 读数不符）

> 作者：release-engineer ｜ 2026-10-13 ｜ 关联：`T333`(`2c684d4`) / `T334` ｜ **纯工具**（`tools/t271/`，未改 `code/`），**离线**（无端点）。

## 1. 改动（`tools/t271/emotion_probe.py`）
- **判定式单一真源**：优先 `from life.emotion import emotion_sign`；调用 `emotion_sign(txt, criterion=crit, lexicon=(POS,NEG) or None)`。
- 新增 **`--criterion strict|natural`**（默认 `strict`）。
- **回退**：import 不可用 → 自带 26 表（仅 strict）+ **显式 `[WARN]`（不静默）**。
- `--pos-file/--neg-file` 仍可换词表（经 `lexicon=(pos,neg)` 传入**同一函数**）。

## 2. canonical 复核（同一 63 样本，经 **life 的 `emotion_sign`**）
| criterion | 读数 | 与 life 报告 |
|---|---|---|
| `strict` | **0/63 = 0.0%**（`importance≥7` 0/42） | **✅ 一致** |
| `natural` | **57/63 = 90.5%**（+9/-48；`importance≥7` 38/42） | ⚠️ **不一致**（life 报 **63/63**） |

## 3. ⚠️ 6 条 `sign==0`（natural 下）—— 供 life 核对
（**既无 natural 词表命中、也无结构正则命中** ⇒ 按**当前 `emotion_sign`** 就是 0）
- `M-P003-000416/417/418`：`阿禾蹲在田埂上，手里捏着一把土，搓了搓。……“邻里之间，和和气气就好。”他自言自语，起身拍了拍裤腿上的泥。`（3 个 insight 同源）
- `M-P002-000462/463/464`：`老石放下刨子，没说话。P001走了，镇上的事还得有人做。`

⇒ **"natural 63/63" 与"用 `emotion_sign` 对同一 63 样本"的读数不符**（90.5%）。**可能**：life 用**另一 run/样本**、或**函数口径**在其计算后有变、或**计数口径不同**（如按 reflect-event 而非 node）。**请 life 核对**（这正是"复核 > 采信"）。

## 4. 命令
```bash
python3 tools/t271/emotion_probe.py /root/t271/runs/t326_real --criterion strict  --samples 0   # 0/63
python3 tools/t271/emotion_probe.py /root/t271/runs/t326_real --criterion natural --samples 0   # 57/63（life 报 63/63）
```
