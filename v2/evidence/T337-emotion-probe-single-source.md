# T337 探针消除双口径：唯一实现 = `life.emotion.emotion_sign` + canonical 复核 + 对账

> 作者：release-engineer ｜ 2026-10-13 ｜ 关联：`T333` / `T334b` ｜ **纯工具**（`tools/t271/`，未改 `code/`），**全离线**（无端点）
> 状态：**接线完成**；**最终数字待 `T333` 校准定稿后复算**（本单**不提前标 completed**）。

## 1. 接线：唯一实现（删除自写那份）
- `emotion_probe.py` 判定**只保留一份实现** = `from life.emotion import emotion_sign(...)`；**探针不再自写判定**（已删除 `else: sign = 1 if hp else ...` 分支；`grep 'else:'` 为空）。
- import 失败 ⇒ **fail-loud**（不再"回退自带 26 表"——那会是第二份实现）。
- `--criterion strict|natural`；`--pos-file/--neg-file` 经 `lexicon=(pos,neg)` 传入**同一函数**。
- **选择与理由**：跨域 import（`tools/`→`code/life`）**只读**、不改 `code/`、单向依赖；比"小 CLI 复制逻辑"更少口径。若边界上有异议，可改为"life 暴露只读 CLI"，但**仍只能一份实现**。

## 2. canonical 复核（对 `/root/t271/runs/t326_real/` 63 条，用**同一函数**）
| criterion | 读数 | 说明 |
|---|---|---|
| `strict` | **0/63 = 0.0%**（imp≥7 0/42） | = `T326`/life 一致 |
| `natural` | **18/63 = 28.6%**（+3/-15；imp≥7 12/42） | = life **`b48920c`** 读数 ✓ |

## 3. ⭐ 对账：旧式自写 vs 新函数（同词表/同档）
| 对比 | 逐条 | 差异 |
|---|---|---|
| 旧式（自写 26 子串, strict） vs `emotion_sign(..., criterion='strict')` | 63 条 | **0 条差异** ✓ |

⇒ 替换 strict 判据**未改读数**（`strict` 逐字节等价）。

## 4. 重要经历（证明"复核>采信"）
- `T334b` 时我读到 `natural 57/63`，而 life 当时报 `63/63` ⇒ **我报不符**；life 随后 **`664909a`** 定位"`_reflect` 的 `(insight k)` 包裹触发结构正则"并修复 ⇒ **我的 57 是对的、life 的 63/63 是 bug**。
- life 再 **`b48920c`** 收紧结构兜底（≥2 类信号共现）⇒ `natural 18/63`。
- **本轮探针（单一真源）自动跟随** ⇒ `natural 18/63`（与 `b48920c` 一致）。

## 5. 状态标注（显式）
- **接线**：✅ 完成（唯一实现 + 对账 0 差异）。
- **canonical 数字**：`strict 0/63` 稳定；`natural` **随访 `emotion_sign` 变动**（57→18）⇒ **最终数字须待 `T333` 最终档位定稿后再复算**；届时命令即可：
```bash
python3 tools/t271/emotion_probe.py /root/t271/runs/t326_real --criterion <final> --samples 0
```
