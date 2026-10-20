# LLM-as-judge 读数

- 日志: `/root/t271/runs/t300/run.jsonl` (sha `sha256:33b7651f2b11d5eaf5720dbd0560cc2ea2a468d37f7319d972b2d7fafd808a08`)
- 模型: DeepSeek-Flash（reported ['DeepSeek-Flash']）/ temperature=0.0
- 抽样: 线程级 2 条 / 重复 2 次 / seed=20261020
- system prompt sha: `sha256:547e52c747c313e0552201d5181c8e56cd1011f35686c7ee7e92c4b0bff3f6a6`
- 解析失败率: 0.0

## 维度分布（1–7）

| 维度 | n | min | p10 | p50 | p90 | max | mean |
|---|---|---|---|---|---|---|---|
| 自然度 `naturalness` | 4 | 4 | 4.3 | 5.0 | 5.0 | 5 | 4.75 |
| 人设贴合 `persona_fit` | 4 | 3 | 3.6 | 5.0 | 5.0 | 5 | 4.5 |
| 具体性 `specificity` | 4 | 3 | 3.3 | 4.0 | 4.0 | 4 | 3.75 |
| 回应有效 `responsiveness` | 4 | 2 | 2.0 | 2.5 | 3.0 | 3 | 2.5 |
| 往复流畅 `flow` | 4 | 2 | 2.3 | 3.0 | 3.0 | 3 | 2.75 |

## 一致性（重复评）

| 键 | n | exact | mean_abs_diff | κ(≥5) | ρ |
|---|---|---|---|---|---|
| `rep0_vs_rep1.flow` | 2 | 0.5 | 0.5 | None | None |
| `rep0_vs_rep1.naturalness` | 2 | 0.5 | 0.5 | 0.0 | None |
| `rep0_vs_rep1.persona_fit` | 2 | 0.5 | 1.0 | 0.0 | None |
| `rep0_vs_rep1.responsiveness` | 2 | 1.0 | 0.0 | None | None |
| `rep0_vs_rep1.specificity` | 2 | 0.5 | 0.5 | None | None |

## 样本与最差句（原文，不替代客观读数）

### S001 `L:2|MSG_DM|P001-P011`（2 条）
```text
[第24回合 morning park] 小满 对 老周 说：（摆出起手式，眼睛亮亮的）喂，P001，别小看我——我可是偷偷练过的，来真的！
[第30回合 evening cafe] 小满 对 老周 说：P001！你猜我今天在图书馆翻到什么好东西了？
```
- 打分（每轮）: [{'naturalness': 5, 'persona_fit': 5, 'specificity': 4, 'responsiveness': 3, 'flow': 3}, {'naturalness': 5, 'persona_fit': 5, 'specificity': 4, 'responsiveness': 3, 'flow': 3}]
- worst_line: P001！你猜我今天在图书馆翻到什么好东西了？
- reason: 两句间隔久且无衔接，第二句未回应第一句的挑战

### S002 `L:4|MSG_DM|P007-P011`（2 条）
```text
[第51回合 afternoon market] 阿林 对 小满 说：哎，哥几个姐几个，我阿林走南闯北这些年，鼻子最灵的就是哪儿有紧俏货——这回镇上东西不好买，你们谁手里有门路可别藏着，咱凑一块儿互通个有无，总比干瞪眼强吧？
[第54回合 evening cafe] 小满 对 阿林 说：P007！你猜怎么着，我昨天翻到一本讲外面世界的旧杂志，看得我一晚上没睡着！
```
- 打分（每轮）: [{'naturalness': 5, 'persona_fit': 5, 'specificity': 4, 'responsiveness': 2, 'flow': 3}, {'naturalness': 4, 'persona_fit': 3, 'specificity': 3, 'responsiveness': 2, 'flow': 2}]
- worst_line: P007！你猜怎么着，我昨天翻到一本讲外面世界的旧杂志，看得我一晚上没睡着！
- reason: 小满完全没接阿林找门路的话，答非所问

