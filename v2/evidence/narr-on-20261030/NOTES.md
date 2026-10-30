# narr-on-20261030 臂 · 执行说明与读数

## 1. 批次事实

| 项 | 值 |
|---|---|
| arm | ON（`LIFE_PROMPT_NARRATION=1`） |
| code_sha | `47a7da9e71e4ab31e8b58a9a5cc14105ecd0aed8`（与 OFF 臂同 SHA；meta.code_sha == meta.code_sha_end） |
| 规模 | seed=42 / agents=16 / rounds=24 / flush-every=2（n16×r24，与 OFF 臂完全一致） |
| started_at | 2026-10-30T02:34:23+08:00 |
| finished_at | 2026-10-30T02:53:35+08:00 |
| duration_sec | 1152（meta）/ 1154（wall） |
| run_batch rc | 0 |
| provider / model | `openai_compat` / `DeepSeek-Flash` |
| degraded_calls | 0（meta.fallback_detected=false） |
| events | 33851 |
| MSG 分母 | 191（MSG_DM 167 + MSG_PUBLIC 24；rounds 0..23 全覆盖，与 OFF 臂同分母） |
| 外层 obs llm-cost | rc=0（本臂直接由**已修复**的封装产出，无重跑） |

switch_proof（/proc/<pid>/environ 实测，见 `switch_proof.txt`）：

```
--- @ 1 /proc/<pid>/environ（开关真值；仅摘相关键）
HITT_LLM_PROVIDER=openai_compat
LIFE_PROMPT_NARRATION=1
```

## 2. 读数（口径见 tools/d9i/narration_stats.py）

| 量 | ON 臂 | OFF 臂（同 SHA 同规模） |
|---|---|---|
| MSG 分母 | 191 | 191 |
| 成对括号旁白 MSG 数 / 占比（主判） | **179 / 191 = 93.72%** | 0 / 191 = 0.00% |
| 括号块总数 | 205 | 0 |
| 旁白内动作类块占比（量 5） | **159 / 205 = 77.56%** | —（无旁白） |
| 任意括号口径（辅助） | 179 / 191 = 93.72% | 0 / 191 = 0.00% |
| L-1 台词长度（含括号）mean | 59.79 | 42.26 |
| L-1 台词长度（**剔除括号后**）mean | 41.12 | 42.26 |
| L-7 8-gram 重复率 | 0.19895 | 0.12565 |

正则（写死，可复算）：
- 成对口径：`（[^（）]{1,120}）|\([^()]{1,120}\)`（要求左右括号成对、中间 ≥1 字符）
- 任意括号口径：`[（(]`（任意左括号字符，含未闭合单侧/纯情绪标签）

复算命令：

```
python3 tools/d9i/narration_stats.py --log v2/evidence/narr-on-20261030/run.jsonl --arm ON
python3 tools/d9i/narration_stats.py --log v2/evidence/narr-off-20261030/run.jsonl --arm OFF
PYTHONPATH=code python3 tools/d5/dialogue_metrics.py --log <run.jsonl> --meta <meta.json> --arm ON|OFF
```

## 3. 括号块 Top-15（原始计数，不做判词）

见 `narration_stats.json` 的 `paired.block_top`：`把沾着面粉的手在围裙上蹭了蹭` 3、`把算盘珠子拨回原位` 3、
`顿了顿` 3、`抬眼` 2、`搓了搓手` 2，其余各 1（`拿刨子推过木料，木花卷着落下来` / `把裁纸刀往桌角一搁` /
`把烧红的锄头往水桶里一按，白汽腾起来` / `掀开锅盖闻了闻，又撒了半勺糖` …）。

## 4. 结论边界（预登记 §4 三禁）

1. 本臂只证**通道恢复**（旁白回来了、且 77.56% 是动作/眼前景而非纯情绪标签），**不证**「生活气息改善」——
   语言质量须人工读样本；自动判定器对「更像人」无判据。
2. 不得用本臂推翻 R9（R9 测「有→禁」，本臂测「禁→有」，方向相反，不可互推）。
3. 代价侧两个数字必须同时看：MSG 条数 **191 = 191（无下降）**，但 **L-7 8-gram 重复率 0.1257 → 0.1990（+7.33pp）**，
   超过预登记的「基线 +5pp」代价闸；另外 L-1「剔除括号后」台词平均长度 42.26 → 41.12（−1.14），说明加的主要是旁白，
   不是把台词换掉。按预登记判定四档，本臂同时满足「N-通道恢复（量 1>0 且动作类占多数）」与「P-恢复但代价超限
   （L-7 恶化 > +5pp）」的触发条件，**档位判定留给 Leader/独立复核**，本文件不下结论。

分母口径提示：预登记 H0 的 686 是 r84、本轮 r24 得 191，**分母不同，只作同向比对，不构成效果比较**。
