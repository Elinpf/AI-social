# W-1 预登记口径卡 · 天气/季节感知臂（`HITT_WEATHER`）

> 立此件：life-impl（生活层实现专家）｜2026-10-29
> 分支：`feat/life-weather-20261029`（基线 `origin/master` = `4905a38`）
> 上游空白证据：`grep -rn "天气" code/life/*.py code/config/*.json` **零命中**；
> `reports/R11` 明写「不做天气/节日」⇒ 本维度在本项目此前**完全不存在**（不是"效果未测"，
> 而是"从未有代码"）。
> 引用纪律：本卡所有"命中量"按 `v2/refs/hit-metric-h0-baseline-rule.md` **先报 H0 取值**；
> 凡 H0 由代码构造保证取端值的量，**不得**当对照有效性证据（同 `v2/refs/M-1-meal-prereg-amendment1.md`）。

## 0. 一句话

让居民的**开口能自然带出对天的感知**（「今儿阴着天」「风大，别在外头站着」「入夏了，日头毒」），
做法是把一条**确定性派生**的「今儿天怎么样」注进对话提示词；开关默认 OFF，OFF 时提示词逐字节不变。

## 1. 假设（H1 与 H0）

| 假设 | 内容 | 可否判 |
|---|---|---|
| **H1** | 天气行进提示词后，MSG 正文的**天气提及率**显著高于同参基线的 H0 水平 | 可判（§4 W-1-a） |
| **H0** | 该行不进提示词（`HITT_WEATHER` 未设置）。世界其余部分不变 | —— |
| **H1-b** | 天气行**不会**让开口句式更模板化（L-7 首分句重复率不上升） | 可判（§4 W-1-b） |
| **H2（本卡不判）** | 台词「更像过日子的人说的」这类**自然度**判断 | **不可判**（§4 §5，只能另立项做 LLM judge / 人工抽检） |

## 2. 两臂配置与环境变量

| 项 | OFF 臂 | ON 臂 |
|---|---|---|
| `HITT_WEATHER` | 不设置（或 `0`/`off`/`false`/`no`/空串） | `1` |
| `HITT_WORLD_SEED` | 建议设成 run seed（**两臂必须相同**） | 同左 |
| 其余开关 | 与同参基线**完全一致**（如 `LIFE_PROMPT_L7_STRUCT` 保持默认 ON；`LIFE_PROMPT_SCENE`/`LIFE_PROMPT_CALENDAR`/`HITT_MEAL` 一律不设） | 同左 |
| 建议跑批参数 | `n16 r60 seed42`（与基线 `run_l7struct_on_n16r60_seed42` 同参，便于直接对 H0） | 同参 |
| 建议证据目录 | `v2/evidence/run_weather_off_n16r60_seed42/` | `v2/evidence/run_weather_on_n16r60_seed42/` |

> **单变量约束**：两臂之间只允许「提示词里有没有这一行」与「`ctx.weather` 键有无」两处差异；
> 其余代码、配置、`code/config/*.json`、seed、回合数、LLM 温度**必须相同**。
> `HITT_WORLD_SEED` 只影响天气**取值**，不影响任何既有机制；两臂设同一值即可。

## 3. 读数指标定义（全部零 LLM、纯读 `run.jsonl`）

读数器：`tools/metrics/weather_readings.py`（判据不在脚本里，脚本只出读数）。

| 指标 | 定义（脚本字段） | H0（OFF）取值 | H1 下能否离开该值 | 区分力 |
|---|---|---|---|---|
| **天气提及率（严格）** | 正文命中天气**现象**词（雨/雪/晴/阴/云/风/日头/晒/雾/霜/雷/潮/湿）的 MSG 占比 → `weather_mention_strict` | **实测 5.81%**（见 §3.1，非端值） | 能（应上升） | **有** |
| 天气提及率（宽松） | 追加体感词（冷/热/凉/闷/燥/冻）→ `weather_mention_feel` | 实测 ~10% | 能 | 有（但混情绪词，只作描述） |
| 季节提及率 | 命中 春/夏/秋/冬/开春/入夏/入秋/入冬 → `season_mention` | 实测 0.39% | 能 | 有（弱，季节短跑内恒定，见 §7 边界） |
| `ctx.weather` 覆盖 | payload `ctx.weather` 出现条数 → `ctx_weather.msgs_with_ctx_weather` | **恒 0（代码构造保证：OFF 不进分支 ⇒ 该键不可能出现）** | 能（ON 应 = 100% MSG） | **无**（构造性端值，**只能当接线检查，不得当效应证据**） |
| L-7 首分句重复率 | 首分句去重比 `1 - unique/total` → `l7_first_clause.dup_rate` | 实测 0.2216 / 0.2581 | 能（升或降） | 有（回归闸，方向为"不升"） |
| 提示词泄漏 | 正文命中标记行「今儿天怎么样」的条数 → `prompt_mark_leak_in_body` | 恒 0 | **能**（若接线错会把提示词写进正文） | 有（硬闸） |
| 逐日天气分布 | `by_day[*].weather` / `ctx_weather.weather_dist` | 空 | —— | 描述量（核对确定性） |

### 3.1 H0 实测（本卡已跑，不是估计）

命令（可直接复制）：

```bash
python3 tools/metrics/weather_readings.py \
    --arm h0_a=v2/evidence/run_l7struct_on_n16r60_seed42/run.jsonl \
    --arm h0_b=v2/evidence/cycle36_f3_off_n16r84_seed42/run.jsonl \
    --json /tmp/h0_two_runs.json
```

输出摘要（真实跑出）：

```
h0_a: msgs=510 bodies=510 weather_strict=27/510=0.053 ctx_weather=0 l7_dup=0.22156862745098038
h0_b: msgs=678 bodies=678 weather_strict=42/678=0.062 ctx_weather=0 l7_dup=0.25811209439528027
```

| 量 | `run_l7struct_on_n16r60_seed42` | `cycle36_f3_off_n16r84_seed42` | 合并 |
|---|---|---|---|
| 天气提及（严格） | 27/510 = 5.29%，Wilson95 [3.66%, 7.59%] | 42/678 = 6.19%，Wilson95 [4.62%, 8.27%] | 69/1188 = **5.81%**，Wilson95 [4.61%, 7.29%] |
| 季节提及 | 2/510 = 0.39% | —— | —— |
| L-7 首分句重复率 | 0.2216 | 0.2581 | —— |
| `ctx.weather` 条数 | 0 | 0 | 0（构造性） |

⇒ **H0 不是端值**（5.8% 左右的中低水平），H1 下有上升空间 ⇒ 主指标有区分力，可用作假说检验。

## 4. 判据（可判 / 不可判）与阈值出处

### W-1-a（主判据 · 可判）
**ON 臂 `weather_mention_strict` 的 Wilson95 下界 > 1.5 × 合并 H0 点估计（= 8.72%）。**
- 出处：H0 由 §3.1 实测（69/1188），**不是拍的**；1.5× 是"超过基线一半的量级变化"的经验门槛，
  **本卡新立、未经历史校准**——若 Leader 认为门槛过高/过低，须在本卡 amendment 里改，**不得事后改**。
- 判"通过"的表述只许写：**「ON 臂 X%（n/N，Wilson95 [a,b]），H0 为 5.81%（69/1188）」**，
  不得写"证明天气让人更像活人"。

### W-1-b（回归闸 · 可判）
**ON 臂 `l7_first_clause.dup_rate` ≤ OFF 臂 + 0.03。**
- 出处：L-7 是既有硬约束（`l7_structural`，默认 ON），本臂不得把它拉回来；
  0.03 为**本卡新立的容差**，量级参照 H0 两样本 0.2216→0.2581 的批间漂移（+0.036）⇒ 取略小的 0.03。
- 若越界 ⇒ 只判"该臂引入模板化风险"，**不得**用天气提及率上升来抵消它。

### W-1-c（接线检查 · **不算效应证据**）
**ON 臂 `ctx_weather.msgs_with_ctx_weather / n_msgs = 1.0`，`seeds` 非空且等于 `HITT_WORLD_SEED`。**
- 这是**构造性**的（OFF 恒 0、ON 恒应 1.0）⇒ 按 M-1-amendment1 纪律，**OFF=0 不得写成"对照有效"**，
  只能说"接线正确"。真正的信息量在 W-1-a。

### W-1-d（硬闸 · 可判）
**两臂 `prompt_mark_leak_in_body = 0`。** 非 0 ⇒ 提示词泄漏进正文，判**失败**，不进效果判定。

### W-1-e（不可判 · 明确不做判定）
- **句式自然度 / 是否"像过日子的人说的"**：本卡**不判**。零 LLM 量不出它；
  要做只能另立项（LLM judge + 人工抽检，参照 D12C 系列的做法），本卡不提供结论。
- **季节维度在短跑里不可判**：`DAYS_PER_SEASON = 7` ⇒ `n16 r60` 只跑 5 天（day 0–4），**全程同一季**（spring）。
  故季节提及率在单次跑批里**无法与"季节恒定"区分**，只能作描述量；若要判季节，须 ≥ 8 天的跑批（`r96` 起）。
- **"天气影响行为（出门/串门/干活）"不可判**：本臂**只改提示词**，不发事件、不改计划、不改世界态
  ⇒ 行为层面**结构上不可能**变化。任何"天气让居民少出门"的说法都不得引用本臂。

## 5. 本臂**不**做的事（防扩大化）

1. **不改** `code/config/*.json`、不改 `state_hash`、不新增事件类型、不写记忆、不动经济/关系/需求数值。
2. **不读墙钟**、不引 `random`（单测 `test_pure_function_source_has_no_clock_or_randomness` 源码级断言）。
3. **不发事件、不参与决策**：只往提示词加一行 + 往 `ctx` 加一个审计键。
4. **不做天气对行为/计划的影响**（见 §4 W-1-e），也不联动「雨天改室内活动」这类机制。

## 6. 确定性验证（已跑）

```bash
# 同 seed 同 day 派生两遍，逐日表 + 表指纹
PYTHONPATH=$PWD/code python3 tools/weather/off_equiv_prompts.py --tree $PWD --out /tmp/eq_branch.json
python3 -c "import json;d=json.load(open('/tmp/eq_branch.json'));print(d['determinism'])"
```

实测（`HITT_WORLD_SEED=42`，day 0–11）：

```
weather_by_day : cloudy overcast rain rain cloudy cloudy rain cloudy rain windy clear clear
season_by_day  : spring ×7, summer ×5
two_passes_identical : True
day_weather_table_sha256 : 49c9db7d909afb1fda7056fcdde9da5be06b21c47458679a431c95fbe96cbc9f
lexicon_sha256 : 01a9ce9ff601059e95e4f3368cd59842eb0fe9060c06db388ae486968878ad62
```

派生规则（源码 `code/life/weather.py`）：
- 季：`SEASONS[(day // 7) % 4]`；
- 天气：`h = int(sha256("<seed>|<day>|weather-v1")[:8], 16) % Σweight(当季)`，落季内累计权重区间；
  季内权重表固定（冬不雨多雪、春夏秋无雪），**权重表即行为**，改表须重冻结 `lexicon_sha256()`。

## 7. OFF 逐字节一致证据（已跑）

```bash
# 基线树（origin/master 4905a38）与臂树各跑一次，均 CO 强制 OFF 后取 sha256
git archive origin/master | tar -x -C /tmp/weather_baseline
PYTHONPATH=/tmp/weather_baseline/code python3 tools/weather/off_equiv_prompts.py \
    --tree /tmp/weather_baseline --out /tmp/off_equiv_master.json
PYTHONPATH=$PWD/code python3 tools/weather/off_equiv_prompts.py \
    --tree $PWD --out /tmp/off_equiv_branch.json
```

| 字段 | 基线 `4905a38` | 臂树（本分支） | 结论 |
|---|---|---|---|
| `off.dialogue_prompt_sha256` | `647d961c…b408c` | `647d961c…b408c` | **逐字节相同** |
| `off.reply_prompt_sha256` | `b330a666…291df` | `b330a666…291df` | **逐字节相同** |
| `off.weather_mark_count_*` | 0 / 0 | 0 / 0 | OFF 不出现标记行 |
| `off.ctx_has_weather_key` | false | false | OFF 不出现 `ctx.weather` |
| `determinism.available` | **false（基线无 `life/weather.py`）** | true | 证实本维度此前为空 |

ON 侧（同树自检）：标记行各 1 次、`delta_len = +55 / +55` 字符，
`on_minus_mark_equals_off_dialogue = true`、`..._reply = true` ⇒ **两态只差这一行**。

## 8. 读数器调用命令（可直接复制）

```bash
# 两臂对照（跑批结束后）
python3 tools/metrics/weather_readings.py \
    --arm off=v2/evidence/run_weather_off_n16r60_seed42/run.jsonl \
    --arm on=v2/evidence/run_weather_on_n16r60_seed42/run.jsonl \
    --json v2/evidence/weather_readings_n16r60_seed42.json

# 单臂快速看
python3 tools/metrics/weather_readings.py v2/evidence/run_weather_on_n16r60_seed42/run.jsonl
```

## 9. 状态

- [x] 代码：`code/life/weather.py` + `code/life/agent.py` 接线（两条提示词各一行 + `ctx.weather` 审计）
- [x] 单测：`code/life/tests/test_weather_arm.py`（32 项，全过；`life/tests` 全量 211 项全过）
- [x] 预登记卡：本件
- [x] 读数器：`tools/metrics/weather_readings.py`；对拍器：`tools/weather/off_equiv_prompts.py`
- [x] OFF 逐字节一致 + 确定性：§6 / §7 已跑并贴输出
- [ ] 跑批（OFF/ON 两臂串行）——**不在本任务范围**（后续 `weather-batch`，冻结区须 clean）
- [ ] 判定件（按 §4 四条判据 + §3.1 H0 并列报）
- 本卡未 push（由报告任务统一推）
