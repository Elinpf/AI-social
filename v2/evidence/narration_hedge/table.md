# 旁白 × 生活气息 F-1…F-7 同表联报（narration_hedge）

> 由 `tools/metrics/narration_hedge.py` 生成，零 LLM、零跑批。
> F 指标口径来源：`tools/d5/dialogue_metrics.py`（本工具只搬运，不重算）。
> 判据来源：`reports/R4-life-texture.md:86-89` 三条「不算改善」陷阱（陷阱1 旁白顶掉生活气息 / 陷阱2 F-6 与重复率 / 陷阱3 编造事件）。

## 0. 复算命令

```bash
python3 tools/metrics/narration_hedge.py \
  --log v2/evidence/d9m-ab-off_n16r24_s42 --label OFF \
  --log v2/evidence/d9m-ab-on_n16r24_s42 --label ON \
  --log v2/evidence/round1_narration_default_n16r24_s42 --label ROUND1-default-ON \
  --baseline-arm OFF --treatment-arm ON \
  --out-json v2/evidence/narration_hedge/readings.json --out-md v2/evidence/narration_hedge/table.md
```

## 1. 输入日志

| 臂 | 日志 | messages | admission | code_sha | cached/total | run_sha256 |
|---|---|---|---|---|---|---|
| OFF | `v2/evidence/d9m-ab-off_n16r24_s42/run.jsonl` | 191 | ADMITTED | 3176048a39f0 | 2252/2252 | sha256:5f1dda97633c… |
| ON | `v2/evidence/d9m-ab-on_n16r24_s42/run.jsonl` | 191 | ADMITTED | 3176048a39f0 | 2209/2252 | sha256:2edc751c5a32… |
| ROUND1-default-ON | `v2/evidence/round1_narration_default_n16r24_s42/run.jsonl` | 191 | ADMITTED | dfe6d5b283a9 | 1387/2252 | sha256:ca108da9f900… |

> 参与判决的臂：baseline=`OFF` / treatment=`ON`（唯一差异是旁白开关，code_sha 相同）。
> **仅作参照读数、不作为对照、不参与判决**：`ROUND1-default-ON`（code_sha 与两臂不同，非同一开关对，不能当第三臂）。

## 2. 旁白读数（成对括号口径，与 D9i 同口径）

| 臂 | 覆盖率(条) | 括号块数 | 去重后唯一块 | 唯一率 | 重复块(≥2次) | 动作类占比 | 旁白字数占正文 |
|---|---|---|---|---|---|---|---|
| OFF | 0/191 = 0.0 | 0 | 0 | None | 0 | None | 0.0 |
| ON | 177/191 = 0.926702 | 196 | 193 | 0.984694 | 3 | 0.683673 | 0.322266 |
| ROUND1-default-ON | 175/191 = 0.91623 | 205 | 199 | 0.970732 | 3 | 0.702439 | 0.306128 |

## 3. F-1…F-7 同表读数

| 指标 | OFF | ON | ROUND1-default-ON | 单位 | 证据级 |
|---|---|---|---|---|---|
| F-1 | 148/191 = 0.774869 | 143/191 = 0.748691 | 145/191 = 0.759162 | per-message | evidence |
| F-2 | 85/125 = 0.68 | 87/125 = 0.696 | 88/125 = 0.704 | per-adjacent-pair | evidence |
| F-2b | 0/66 = 0.0 | 0/66 = 0.0 | 0/66 = 0.0 | per-thread | evidence |
| F-3 | 1/11 = 0.090909 | 0/1 = 0.0 | 1/6 = 0.166667 | per-adjacent-pair | probe |
| F-4 | 0/8 = 0.0 | 0/1 = 0.0 | 0/5 = 0.0 | per-event | probe |
| F-5 | 0/16 = 0.0 | 0/16 = 0.0 | 0/16 = 0.0 | per-agent | probe |
| F-6 | 11/191 = 0.057592 | 33/191 = 0.172775 | 33/191 = 0.172775 | per-message | evidence |
| F-6_onscreen_only | 11/191 = 0.057592 | 33/191 = 0.172775 | 32/191 = 0.167539 | per-message | diagnostic |
| F-7a | 19/191 = 0.099476 | 27/191 = 0.141361 | 28/191 = 0.146597 | per-message | evidence |
| F-7b | None | None | None | per-message | 未验证 |

> `F-6_onscreen_only` = 剥掉成对括号旁白后用同一 `compute()` 重算的 F-6，用于判断 F-6 提升是否长在旁白文字上（诊断列，不作 headline）。
> **F-6 诊断（唯一有价值的线索）**：剥掉成对括号旁白后，ON 臂 F-6 仍是 33/191（OFF 臂 11/191），delta 存活比 = 1.0 ⇒ 这次 F-6 的移动**落在台词正文，不在旁白文字本身**；但它与旁白开关同时发生且伴随 L-7 ngram8 重复率恶化，按 reports/R4-life-texture.md:86-89 陷阱1/2 的文字口径仍判『不算改善』
> **`F-7b` 为什么是 None**：F-7b 测「编造了日志中不存在的事件」，规则不可测，必须 judge （拿到该线程时段真实事件摘要逐条判，率 = 编造条数/受检条数）；仓库内没有该脚本，且本轮锁死零 LLM ⇒ 只能留 None/未验证。下一轮接手需要：新写 judge 脚本 + 选受检样本 + `obs llm-cost` 取证；在此之前「旁白没有带来编造」不成立。
> delta 表的「方向有利」只表示数值方向，是否算改善还要过 §4 的 R4 陷阱闸（见 disqualified）。

## 4. 对冲判决

- **hedge_verdict = `swap_only`**
- 依据：旁白有实质增量（0.0 → 0.926702），但去掉 R4 陷阱1/2 后**没有任何可判 F 指标构成同向改善**；被取消改善资格的读数：F-6（R4 陷阱1（reports/R4-life-texture.md:86-89 第1条）：F-1/F-6 升高**同时**旁白率也升高（旁白 0.0→0.926702）⇒ 判为「用旁白换生活气息」，不算改善 | R4 陷阱2（reports/R4-life-texture.md:86-89 第2条）：F-6 升高的同时措辞层重复率恶化（L-6 Δ=0.0, L-7 Δ=0.083769 ≥ 0.02）⇒ 不算改善）；另有可判同向恶化：F-1、F-7a
- baseline=`OFF`，treatment=`ON`，旁白覆盖率 0.0 → 0.926702（lift=0.926702）
- 可判改善：无；可判恶化：['F-1', 'F-7a']
- 不可判：{"F-3": "分母 <30（b=11, t=1），本规模下不可判", "F-4": "分母 <30（b=8, t=1），本规模下不可判", "F-5": "分母 <30（b=16, t=16），本规模下不可判", "F-2": "方向不唯一（漂移高低本身不是好坏判据），只报不判"}
- 被 R4 陷阱取消改善资格：
  - F-6：R4 陷阱1（reports/R4-life-texture.md:86-89 第1条）：F-1/F-6 升高**同时**旁白率也升高（旁白 0.0→0.926702）⇒ 判为「用旁白换生活气息」，不算改善
  - F-6：R4 陷阱2（reports/R4-life-texture.md:86-89 第2条）：F-6 升高的同时措辞层重复率恶化（L-6 Δ=0.0, L-7 Δ=0.083769 ≥ 0.02）⇒ 不算改善
- 显著性：p_value = None（不可算原因：两臂为同一 prompt 集的缓存回放（见 caveats 的 cached/total），非独立重采样，样本不满足独立性假设 ⇒ 按纪律不给 p 值/置信区间，任何『显著』说法都不成立）
- swap 证据：{"F-6": {"delta_full_body": 0.115183, "delta_onscreen_only": 0.115183, "share_of_delta_surviving_paren_strip": 1.0, "num_full_body": "11/191 → 33/191", "num_onscreen_only": "11/191 → 33/191", "explicit_statement": "剥掉成对括号旁白后，ON 臂 F-6 仍是 33/191（OFF 臂 11/191），delta 存活比 = 1.0 ⇒ 这次 F-6 的移动**落在台词正文，不在旁白文字本身**；但它与旁白开关同时发生且伴随 L-7 ngram8 重复率恶化，按 reports/R4-life-texture.md:86-89 陷阱1/2 的文字口径仍判『不算改善』", "note": "这是本轮唯一有诊断价值的线索：旁白不是靠『写景物』把 F-6 顶上去的，而是改变了台词里对『昨天/上次』的提及；要证实它，需要独立重采样 + F-7b judge，本轮两臂均为缓存回放，做不到"}}
- 复现前提/告警：
  - OFF 臂 cached/total = 2252/2252（llm_cached_ratio=1.0）：全部命中缓存，响应是历史真 LLM 产物、本批未重生成 ⇒ 本对照是**两份日志正文的文本统计对比**，不是两次独立采样
  - ON 臂 cached/total = 2209/2252（llm_cached_ratio=0.9809）：大部分为缓存回放
  - 不可判维度原因见 unjudgeable
- 缺失前提：
  - F-7b（编造事件率）需 judge 判定；本工具零 LLM ⇒ 恒为 None/未验证
  - 独立重采样（两臂均为缓存回放，不能支撑显著性/批间方差结论）

## 5. 两臂 delta（treatment − baseline）

| 指标 | baseline | treatment | 分子(b/t) | delta | 方向 | 方向有利(未过R4闸) | 分母(b/t) |
|---|---|---|---|---|---|---|---|
| F-1 | 0.774869 | 0.748691 | 148/143 | -0.026178 | 1 | False | 191/191 |
| F-2b | 0.0 | 0.0 | 0/0 | 0.0 | 1 | False | 66/66 |
| F-3 | 0.090909 | 0.0 | 1/0 | -0.090909 | 1 | False | 11/1 |
| F-4 | 0.0 | 0.0 | 0/0 | 0.0 | 1 | False | 8/1 |
| F-5 | 0.0 | 0.0 | 0/0 | 0.0 | 1 | False | 16/16 |
| F-6 | 0.057592 | 0.172775 | 11/33 | 0.115183 | 1 | True | 191/191 |
| F-7a | 0.099476 | 0.141361 | 19/27 | 0.041885 | -1 | False | 191/191 |
| F-2 | 0.68 | 0.696 | 85/87 | 0.016 | 0 | None | 125/125 |

