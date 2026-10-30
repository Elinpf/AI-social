# R27 · 旁白 × 生活气息 F-1…F-7 同表联报（零 LLM 只读复算）

- 撰写人：round-scribe（实验记录与证据负责人）
- 撰写时间：2026-10-30（本轮）
- 分析基准 HEAD：`0b14183a06f64b90bd448886e84586a713ba30cb`（分支 `feat/narration-default-on`）
- 被读日志所属代码树：`3176048a39f0429204adbdb9eac7a975bfe10c72`（两臂相同，§2.5）
- 报告性质：**零跑批、零 LLM 调用、零 `code/` 变更**；只读既有 `run.jsonl`，F 口径全部复用 `tools/d5/dialogue_metrics.py`
- 结论状态：**`hedge_verdict = swap_only`** —— 旁白只是换词/加景物，**不算生活气息改善**

---

## 0. 摘要

本轮把「旁白统计」与「生活气息七维 F-1…F-7」放进**同一张表**，判据沿用 `reports/R4-life-texture.md:86-89` 写死的三条「不算改善」陷阱。结论只有一句：

> **旁白覆盖率从 `0/191 = 0.00%` 涨到 `177/191 = 92.70%`，但七维里没有任何一维构成「可判的同向改善」；唯一看似上涨的 F-6（`5.76% → 17.28%`）被 R4 陷阱 1 与陷阱 2 连续取消改善资格，F-1 与 F-7a 反向恶化 ⇒ `swap_only`：这只是「把生活气息写成旁白」，按 R4:88 原文「**不算改善**」。**

四条必须先于任何数字被读者读到的前置限定：

1. **两臂是缓存回放，不是两次独立采样**：OFF 臂 `cached/total = 2252/2252`（100% 命中，`tokens_in/out = 0`），ON 臂 `2209/2252`（98.09%）。响应是历史真 LLM 产物，但**本批未重新生成** ⇒ 本报告的可引用范围是「**两份日志正文的文本统计对比**」，**不是**「两次独立采样实验」；因此本报告**不给 p 值、不给置信区间**，任何「显著」说法一律不成立。
2. **单 seed 42 / n16×24 回合 / 191 条消息**：全部数字只作**点估计**，不外推。
3. **F-3 / F-4 / F-5 分母 < 30**：按全族纪律只报事件数，一律写**不可判**，**不顺百分比讲趋势**；F-7b（编造事件率）需 judge，本轮零 LLM ⇒ **恒为 `None` / 未验证**。
4. **`round1_narration_default_n16r24_s42`（`code_sha dfe6d5b2…`）只作参照，不参与判决**（§3.4），任何人不得把它当第三臂。

---

## 1. 口径与假设

### 1.1 生活气息口径（不自立，全部引用既有编号）

F-1…F-7 的定义式、统计单位与分母见 `reports/R4-life-texture.md:28-44`（表「七个可度量的维度」）。本报告**不新增维度、不改定义式**，只在同一张表里多一列「旁白统计」。F 读数由 `tools/metrics/narration_hedge.py` 调 `tools/d5/dialogue_metrics.py` 的 `main()` 取得，**出数器内部不含任何 F 指标重算逻辑**。

### 1.2 判据（原文引用，非本报告发明）

`reports/R4-life-texture.md:86-89`（`§3.2 三个必须主动避开的陷阱`）原文：

- **陷阱 1（与本轮直接相关）**：「**景物描写 ≠ 生活气息**：把生活气息写成旁白（"（窗外下着雨）"）会顶掉措辞层的旁白化改善——表现为 F-1/F-6 升高**同时**旁白率也升高 ⇒ 判为「用旁白换生活气息」，**不算改善**。」
- **陷阱 2**：「每句塞"昨天/记得" = 套路：F-6 升高时必须同时看重复率（措辞层 L-6/L-7）；重复率同步恶化则不算改善。」
- **陷阱 3**：编造未发生的事件（F-7）优先级高于 F-1…F-6 的任何好看读数。

> **行号更正（本轮登记）**：任务书与 `narration_hedge.py` 早期注释引「判据在 `R4:76-78`」，实测该区间是 `§3.1 判据` 标题与阈值段；**三条「不算改善」陷阱实体在 `R4:86-89`**。复核：`grep -n "景物描写\|不算改善" reports/R4-life-texture.md`。

### 1.3 对冲判决定义（判之前写死，不因读数好看而松动）

| 取值 | 条件 |
|---|---|
| `lift_confirmed` | ON 臂 F 指标**同向改善**，且旁白去重/套路化程度**未恶化**，且超该单位可用上界（无可用带 ⇒ 不得取此值） |
| `swap_only` | 旁白统计确实上升，但 F 指标**无同向改善或反向** ⇒ 按 R4 陷阱 1 判「用旁白换生活气息」，**不算生活气息改善** |
| `inconclusive` | 缺可比前提（无旁白开关对照 / 分母过小 / 配置不可比）⇒ 不下判决，只列缺失前提 |

本轮落在第二档（依据见 §4）。**三态之外不设第四种含糊表述。**

### 1.4 假设（写明，便于被证伪）

- 假设 A：两臂除 `LIFE_PROMPT_NARRATION` 外其余开关一致 —— 由 `switch_proof.txt`（`/proc/<pid>/environ` 真值）验证，§2.4。
- 假设 B：F 指标只依赖日志正文、与缓存命中无关；但缓存命中率差异影响「ON 臂是否真重生成」，故单列披露（§0 第 1 条、§2.4）。

---

## 2. 可复算命令块（命令 + 真实输出）

> 所有命令均**只读**、零 LLM，仓库根 `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment` 下可直接复制执行。以下输出为本次实际运行原文（未修数字）。

### 2.1 基线不可变事实

```bash
git rev-parse HEAD && git branch --show-current
```

```
0b14183a06f64b90bd448886e84586a713ba30cb
feat/narration-default-on
```

工作区**他人未完成的 3 个 tracked 修改**（本报告**不包含、未 add**）：

```bash
git status --porcelain | grep '^ M'
```

```
 M tools/metrics/weather_readings.py
 M v2/evidence/d3_noiseband_bootstrap.json
 M v2/evidence/d9f_dr_on_mock_result.md
```

### 2.2 旁白开关的代码事实

```bash
sed -n '34,38p' code/config/life_v2.json; grep -n 'NARRATION_ENV = \|NARRATION_DEFAULT_ENABLED = ' code/life/agent.py
```

```
  "prompt": {
    "narration": {
      "enabled": true
    }
  }
90:NARRATION_ENV = "LIFE_PROMPT_NARRATION"
96:NARRATION_DEFAULT_ENABLED = True
```

⇒ 旁白**默认 ON**（配置 `enabled=true` + 常量 `True`），`LIFE_PROMPT_NARRATION=0` 可显式关闭。

### 2.3 选臂甄别（先证明「唯一可用的旁白对照臂是哪一对」）

```bash
grep -rl "LIFE_PROMPT_NARRATION" v2/evidence/*/switch_proof.txt v2/evidence/*/meta.json 2>/dev/null | head
```

实测结论：

- **可用（本报告所用）**：`d9m-ab-off_n16r24_s42` / `d9m-ab-on_n16r24_s42` —— 唯一差异是 `LIFE_PROMPT_NARRATION`（`0` vs `1`），`NARRATION_ROTATION`、`NARRATION_ACTION` 两臂相同，`code_sha` 同为 `3176048a`。
- **不可用（易误用，已排除）**：`run_r1_batch_off/on_n16r24_seed42` 的 switch 是 `LIFE_PROMPT_ENCOUNTER_CHAT`（`unset` vs 开），属**遭遇聊天**臂，**不是旁白臂**；误用会让整份报告作废。

### 2.4 两臂真 LLM 验真 + 单变量证明 + 缓存披露

```bash
cd code && PATH=/opt/openjiuwen/workswarm-venv/bin:$PATH \
  python3 -m obs llm-cost --log ../v2/evidence/d9m-ab-off_n16r24_s42/run.jsonl --require-provider openai_compat
```

真实输出（`provider_guard.ok = true`、`degraded = 0`；`cached/calls` 为原文数值）：

```
OFF: total {cached: 2252, calls: 2252, tokens_in: 0, tokens_out: 0}  provider_guard.ok = true
ON : total {cached: 2209, calls: 2252, tokens_in: 16069, tokens_out: 16538} provider_guard.ok = true
```

```bash
grep -n 'LIFE_PROMPT_NARRATION' v2/evidence/d9m-ab-{off,on}_n16r24_s42/switch_proof.txt | head -3
```

```
off: LIFE_PROMPT_NARRATION_ROTATION=1 / LIFE_PROMPT_NARRATION=0 / LIFE_PROMPT_NARRATION_ACTION=1
on : LIFE_PROMPT_NARRATION_ROTATION=1 / LIFE_PROMPT_NARRATION=1 / LIFE_PROMPT_NARRATION_ACTION=1
```

⇒ 两臂唯一差异是 `LIFE_PROMPT_NARRATION`（0 vs 1），旋转/动作子开关相同 ⇒ **单变量成立**；两臂 `provider=openai_compat`、无 mock 混入、均 **ADMITTED（strict / evidence）**（B-9 事件数自检 PASS、B-17 哈希链 PASS）。

**【必须披露的限定】** OFF 臂 `cached=2252/2252`、`tokens_in/out = 0` ⇒ **整臂是缓存回放**；ON 臂 `cached=2209/2252`（dialogue 172/191 命中）。故本报告可引用范围 = 「**两份日志正文的文本统计对比**」，**不是**「两次独立采样实验」。

### 2.5 日志清单与指纹

```bash
wc -l v2/evidence/d9m-ab-{off,on}_n16r24_s42/run.jsonl; sha256sum v2/evidence/d9m-ab-{off,on}_n16r24_s42/run.jsonl
```

```
   33850 v2/evidence/d9m-ab-off_n16r24_s42/run.jsonl
   33857 v2/evidence/d9m-ab-on_n16r24_s42/run.jsonl
5f1dda97633ccf0b3f7d2b279c39a43752db7d945a2ca6f9133e0b2bc9106ed5  d9m-ab-off_n16r24_s42/run.jsonl
2edc751c5a32d1328ed5834ab169d29c5c457cbe7b1d5abe3146d7840df6a795  d9m-ab-on_n16r24_s42/run.jsonl
```

`meta.json` 关键字段：`code_sha = 3176048a39f0429204adbdb9eac7a975bfe10c72`（两臂相同）、`n=16`、`rounds=24`、`seed=42`、`provider=openai_compat`、`model=DeepSeek-Flash`；`events`：off=33850 / on=33857（与 `wc -l` 一致）。

### 2.6 出数命令（本报告全部数字的唯一来源）

```bash
python3 tools/metrics/narration_hedge.py \
  --log v2/evidence/d9m-ab-off_n16r24_s42 --label OFF \
  --log v2/evidence/d9m-ab-on_n16r24_s42  --label ON \
  --baseline-arm OFF --treatment-arm ON \
  --out-json v2/evidence/narration_hedge/readings.json \
  --out-md   v2/evidence/narration_hedge/table.md
```

真实输出（退出码 0；重复执行 `readings.json` 逐字节稳定，sha256 `9f96eebfb50dcb70aef6f2122af89f1e7bea29671c1f3d3824b73cbe6ad7f999`，`table.md` sha256 `6840cb39735aa549aaf9f71d39a44f12fecc55e88fd8dc5ad122f62c3b9da7ad`）：

```
hedge_verdict = swap_only
reason: 旁白有实质增量（0.0 → 0.926702），但去掉 R4 陷阱1/2 后没有任何可判 F 指标构成同向改善；
被取消改善资格的读数：F-6（陷阱1 + 陷阱2）；另有可判同向恶化：F-1、F-7a
```

### 2.7 独立交叉核对（第二份互不共享代码的实现）

```bash
python3 v2/evidence/narration_hedge/recompute_by_round_scribe.py \
  --off v2/evidence/d9m-ab-off_n16r24_s42 --on v2/evidence/d9m-ab-on_n16r24_s42 \
  --out-json v2/evidence/narration_hedge/readings_by_round_scribe.json \
  --out-md   v2/evidence/narration_hedge/table_by_round_scribe.md
```

真实输出（详表见 `v2/evidence/narration_hedge/crosscheck_by_round_scribe.md`，比对结果 **ALL_MATCH**）：

```
F-1 -0.026178 | F-2 +0.016000 | F-2b +0.000000 | F-3 -0.090909
F-4 +0.000000 | F-5 +0.000000 | F-6 +0.115183 | F-7a +0.041885   ← 8/8 与 metrics-dev 一致
旁白覆盖率 0.0 → 0.926702（两实现一致）；hedge_verdict 两实现同为 swap_only
```

> 唯一已知口径差异（不矛盾、两边各自公开口径）：「旁白字数占正文」scribe `0.2876`（旁白字符 / body 总字符）vs metrics-dev `0.322266`（分母定义不同）。正文只引用后者。

---

## 3. 读数表（同表联报）

来源：`v2/evidence/narration_hedge/table.md`（由 §2.6 命令生成）。**分母随读数并列**；`None` 表示该臂无该量（OFF 臂没有任何旁白块）。

### 3.1 旁白读数

| 臂 | 覆盖率 | 括号块数 | 唯一块 | 唯一率 | 重复块(≥2 次) | 动作类占比 | 旁白字数占正文 |
|---|---|---|---|---|---|---|---|
| OFF | **0/191 = 0.0** | 0 | 0 | None | 0 | None | 0.0 |
| ON | **177/191 = 0.926702**（92.70%） | 196 | 193 | 0.984694（98.47%） | 3 | 0.683673 | 0.322266（32.23%） |

### 3.2 F-1…F-7 同表读数 + 增量

| 指标 | 单位 | OFF | ON | 增量 | 分母(OFF/ON) | 证据级 |
|---|---|---|---|---|---|---|
| F-1 非功能性闲聊占比 | per-message | 148/191 = 0.774869（77.49%） | 143/191 = 0.748691（74.87%） | **−0.026178（−2.62pp）** | 191 / 191 | evidence（**同向恶化**） |
| F-2 话题漂移率（content 口径） | per-adjacent-pair | 85/125 = 0.68 | 87/125 = 0.696 | +0.016 | 125 / 125 | evidence（**方向不判**：漂移高低本身不是好坏判据） |
| F-2b 多话题线程占比 | per-thread | 0/66 = 0.0 | 0/66 = 0.0 | 0.0 | 66 / 66 | evidence |
| F-3 情绪呼应率 | per-adjacent-pair | 1/11 = 0.090909 | 0/1 = 0.0 | −0.090909 | 11 / 1 | **probe｜不可判（分母<30）** |
| F-4 修复闭环率 | per-event | 0/8 = 0.0 | 0/1 = 0.0 | 0.0 | 8 / 1 | **probe｜不可判（分母<30）** |
| F-5 习惯强度 | per-agent | 0/16 = 0.0 | 0/16 = 0.0 | 0.0 | 16 / 16 | **probe｜不可判（1 天<3 天，结构性为 0）** |
| F-6 跨天记忆引用率 | per-message | 11/191 = 0.057592（5.76%） | 33/191 = 0.172775（17.28%） | **+0.115183（+11.52pp）** | 191 / 191 | evidence，但**被 R4 陷阱 1+2 取消改善资格** |
| F-6_onscreen_only（诊断列） | per-message | 11/191 = 0.057592 | 33/191 = 0.172775 | +0.115183 | 191 / 191 | diagnostic（**delta 存活比 = 1.0**） |
| F-7a 越界提及率 | per-message | 19/191 = 0.099476（9.95%） | 27/191 = 0.141361（14.14%） | **+0.041885（+4.19pp）** | 191 / 191 | evidence（**同向恶化**） |
| F-7b 编造事件率 | per-message | None | None | — | — | **未验证（需 judge；本轮零 LLM）** |
| L-7 8-gram 撞车率（重复率守卫） | per-message | 0.214660（21.47%） | 0.298429（29.84%） | **+0.083769（+8.38pp）** | — | evidence（**恶化**；`delta_threshold = 0.02`） |

### 3.3 F-6 的诊断线索（必须单独留痕，不能被「不算改善」盖掉）

`F-6_onscreen_only` = 剥掉成对括号旁白后用**同一个** `compute()` 重算的 F-6：
`0.057592 → 0.172775`，与全量**逐位相同**，`share_of_delta_surviving_paren_strip = 1.0`。

⇒ **这次 F-6 的 +11.52pp 落在台词正文里，不是旁白文字本身的贡献。**
它告诉我们两件事：

1. 旁白开关**间接改变**了台词的说话方式（时间回指词变多），这不是"旁白词被计入 F-6"的假象；
2. 但按 `R4:88` 的文字口径，**「F-6 升高 + 旁白率同升」同时成立即判换词**，所以它仍**不算改善**。
3. **给下一轮的口子**：值得单独开一个「旁白 ON 对台词正文时间回指的影响」臂，用重复率受控的对照来判断这 +11.52pp 是"更会提过去"还是"更套路地塞昨天"（本轮 L-7 恶化 +8.38pp 倾向于后者，但**未做逐条归因，属未验证**）。

### 3.4 参照臂（**不参与判决**）

`round1_narration_default_n16r24_s42`（`code_sha dfe6d5b2…`、`events=33845`、n16r24 seed42、旁白默认 ON）与 d9m 两臂**代码树不同**，只作旁白默认化后的「同规模快照」参照：

- 其 `narration_stats.json` 记录：`191` 条消息里 `175` 条含成对括号（rate `0.91623`）、`205` 个括号块、动作类 `144/205`。
- **本报告不用它算任何 delta、不参与 `hedge_verdict`**；任何人不得把它当第三臂或第三组对照。

---

## 4. 对冲判决

### 4.1 判决

**`hedge_verdict = ` `swap_only`**

### 4.2 依据（逐条可对到 §3 的数字）

1. **旁白确实来了**：覆盖率 `0.0 → 0.926702`（+92.70pp），196 个旁白块、唯一率 98.47%（不是死板复读同一句）、旁白字数占正文 32.23%。**这一步是真实的。**
2. **但七维没有任何一维构成「可判的同向改善」**：
   - 可判改善清单 = **空**（`judgeable_improvements = []`）。
   - 可判恶化：**F-1（−2.62pp）、F-7a（+4.19pp，越界提及变多）**。
   - 不可判：F-3（分母 `11→1`）、F-4（分母 `8→1`）、F-5（1 天、结构性为 0）、F-2（方向不唯一）——按纪律**只报事件数/分母，不顺着百分比讲趋势**。分母坍缩（11→1、8→1）本身是旁白顶掉对话的旁证，但**不作为改善/恶化的判定**。
3. **唯一上涨的 F-6 被连续两次取消改善资格**：
   - **陷阱 1**：F-6 升高**同时**旁白率也升高（`0.0 → 0.926702`）⇒ 判为「用旁白换生活气息」，不算改善。
   - **陷阱 2**：F-6 升高的同时措辞层重复率恶化（`L-7` 8-gram 撞车率 `0.214660 → 0.298429`，**Δ = +8.377pp ≈ +8.4pp**，远超出数器 `delta_threshold = 0.02`；`L-6` 完全重复率持平 `0.0`）⇒ 按 `R4:89` 不算改善。
   - **对冲结论（必须同时写）**：即使 §3.3 证明提升不在旁白文字里，按 R4 判据的**文字口径**，只要「旁白率同升 + 重复率恶化」两件事同时成立，这一维就**不得记为改善**。
4. **显著性无法给出**：`p_value = None`。原因不是缺技术，而是**样本不满足独立性**（两臂为同一 prompt 集的缓存回放，§2.4）。任何「显著提升/显著改善」的写法在本报告一律不成立。

### 4.3 一句话判决（可直接引用）

> 旁白默认 ON 让「（动作/景物）」覆盖了 92.70% 的消息，但生活气息七维里**没有一维构成可判的同向改善**；唯一上涨的 F-6 因「旁白率同升 + 8-gram 撞车率恶化 +8.4pp」被 R4 陷阱 1/2 连续取消资格，F-1 与 F-7a 反而恶化 ⇒ **`swap_only`：旁白只是换了词、加了景物描写，按 `R4:88`「不算生活气息改善」。**

---

## 5. 未验证项清单

1. **F-7b（编造未发生的事件）未验证**：`None`，缺 judge 判据（本轮零 LLM）。按 R4 陷阱 3，F-7 优先级高于 F-1…F-6 的任何好看读数 ⇒ 本报告的「不算改善」不因它缺席而变严，但**也不得被写成「没有更坏」**。
2. **旁白语义质量（是否贴合当场）未由人读评判**：本轮只有「唯一率 98.47%」这种机器近似；**去重率高 ≠ 不套路**，也不等于「贴合这一刻的场景」。需下一轮人工抽样双查（≥30 条）。
3. **F-7a 上升的归因未验证**：越界提及 `19/191 → 27/191`，但是否由旁白句引入（旁白里提到不在场的人）**未做逐条归因**，只有总量事实。
4. **F-6 +11.52pp 的机制未验证**：`F-6_onscreen_only` 只证明了「不在旁白文字里」，**没有证明它是"更会提过去"还是"更套路地塞时间词"**；按 R4 陷阱 2 的取向怀疑后者（L-7 恶化），但**未逐条归因**。
5. **两臂不可作独立重采样**：OFF 臂 100% 缓存回放、ON 臂 98.09% ⇒ 不能推批间方差、不能给 CI/p 值。
6. **单 seed / 单规模不外推**：seed 42、n16×24 回合、191 条消息；结论只到「这一批的文本统计形态」。
7. **日志所属代码树 ≠ 分析基准**：读数绑定 `3176048a`（worktree `narration-action-diversity`），不是当前 HEAD `0b14183a`；**不得把本报告数字挪用到 `0b14183a`**。
8. **`F-5 习惯强度` 结构性为 0**：本批只跑 1 个模拟日（`max_repeat_days_mean = 1.75`，`<3 天`），该维度在本规模下**天然不可能非零**，不是旁白导致的下降。
9. **runtime-ops 独立复核（t-crosscheck-narration）未回填**：本轮 push 时该复核结论尚未落盘 ⇒ 见 `round-crosscheck-narration-hedge.md`（待补）。**本报告不替它写任何结论。**

---

## 6. 结论绑定的 sha

| 项 | 值 |
|---|---|
| 分析基准 HEAD | `0b14183a06f64b90bd448886e84586a713ba30cb`（`feat/narration-default-on`） |
| 被读日志代码树 | `3176048a39f0429204adbdb9eac7a975bfe10c72`（两臂相同） |
| 日志指纹 | OFF `5f1dda97633ccf0b3f7d2b279c39a43752db7d945a2ca6f9133e0b2bc9106ed5`；ON `2edc751c5a32d1328ed5834ab169d29c5c457cbe7b1d5abe3146d7840df6a795` |
| 准入 | 两臂均 `ADMITTED`（`strict` / `evidence`），`provider=openai_compat`、`degraded=0` |
| 读数文件 | `readings.json` `9f96eebf…f999`；`table.md` `6840cb39…a7ad`；交叉核对 `readings_by_round_scribe.json` / `table_by_round_scribe.md`（见 `crosscheck_by_round_scribe.md`） |
| 参照臂（不参与判决） | `round1_narration_default_n16r24_s42`，`code_sha dfe6d5b283a9e37f9d3f2373e1b8224fd15d609f` |
| 本报告所在提交 | 分支 `feat/round-narration-hedge`（基于 `0b14183a`），pushed sha 见提交回执 / §8 |

---

## 7. 真实截图（真浏览器渲染，非示意图）

命令（`$HOME` 落盘 → 拷贝入仓，`cmp_identical: True`）：

```bash
python3 v2/evidence/narration_hedge_shots/render_table_shot.py \
  --md v2/evidence/narration_hedge/table.md \
  --out-png v2/evidence/narration_hedge_shots/narration_hedge_table.png \
  --title "R27 · 旁白 × 生活气息 F-1…F-7 同表联报（d9m OFF vs ON，n16r24 seed42）"
```

真实输出：

```
html: /root/narration_hedge_prep/narration_hedge_table.html
png ($HOME): /root/narration_hedge_prep/narration_hedge_table.png
png (copied into repo): v2/evidence/narration_hedge_shots/narration_hedge_table.png
cmp_identical: True
bytes: 1141154
sha256: 256e319e0137ab0377dad6017663d4192cbde742d967bdf241f215aaffe9e4a6
clip_check: {'tables': 4, 'overflowX': False}
size: (2912, 4386)   mean_brightness: 244.1
```

- 产物：`v2/evidence/narration_hedge_shots/narration_hedge_table.png`（`sha256 256e319e0137ab0377dad6017663d4192cbde742d967bdf241f215aaffe9e4a6`，2912×4386，`mean_brightness 244.1` 非黑图，4 张表无横向溢出）
- 渲染器：`v2/evidence/narration_hedge_shots/render_table_shot.py`（浏览器探测复用 `code/frontend/tools/_chrome.find_chrome()`，**不写死任何家目录/缓存路径**）
- 说明：图上内容就是 §2.6 生成的 `table.md` 原文，**截图不含任何手工补写的数字**；截图本身**不进判据**，只作可读性凭证。

---

## 8. 交付与索引

- 出数器：`tools/metrics/narration_hedge.py`（metrics-dev；零 LLM，F 口径全部转调 d5）
- 机读读数：`v2/evidence/narration_hedge/readings.json`；人读表：`v2/evidence/narration_hedge/table.md`
- 独立交叉核对（scribe 侧）：`v2/evidence/narration_hedge/recompute_by_round_scribe.py` + `readings_by_round_scribe.json` / `table_by_round_scribe.md` / `crosscheck_by_round_scribe.md`（8/8 delta 一致、判决一致）
- 截图：`v2/evidence/narration_hedge_shots/narration_hedge_table.png` + `render_table_shot.py`
- 上游口径：`reports/R4-life-texture.md:28-44`（定义式）、`:86-89`（三条「不算改善」陷阱）
- 待补：`round-crosscheck-narration-hedge.md`（runtime-ops 独立复核，本轮 push 时未回填）
- 提交：分支 `feat/round-narration-hedge`（基于 `0b14183a`），**不动 master**；pushed sha 见提交回执
