# 群体聚集 / 同场共处 / 独处-空闲 —— 只读基线读数（GROUP_PRESENCE_20261024）

本目录只放**描述性读数**，不设闸、不写任何"更生活化/更真实"一类效果归因。

- 出数脚本：`tools/f9/group_presence_metrics.py`（只读，不跑批，不修改 `code/` 任何文件）
- 读数文件：`v2/evidence/group_presence_20261024/group_presence_metrics.json`
- 仓库基线：`git rev-parse HEAD` = `0ed1a20574aa5e9bc283b17daa887a5220d1838f`（取数时）
- 输入：`v2/evidence/run_f3_off_n16r60_seed42/run.jsonl`

## 1. 输入与指纹

| 项 | 值 |
|---|---|
| 输入路径 | `v2/evidence/run_f3_off_n16r60_seed42/run.jsonl` |
| 输入行数 | 116336 |
| 输入 sha256 | `19d5cb03de2f0203e3b8aa1c9160adfbef787a159f961713f40b88027931d305` |
| 输出 sha256 | `affab114b637a1c6e04f5be57f0edc6f628808f188746008eb439539fd44a338` |
| 配置指纹（run 内 WORLD_INIT） | `config_digest=sha256:58485c0632210e87116e212ac921b37456c67b99a5e2756f4c9642e8181f1125`、`fingerprint=sha256:a871e36c44acbda9ac4aadeebe829a821219b2fec22642ea2b372f6ec88f3b1c`、`seed=42`、`time_model=atomic` |

## 2. 复算命令（一条命令出全部数字）

在仓库根目录 `social-experiment/` 下执行：

```bash
python3 tools/f9/group_presence_metrics.py \
    --run v2/evidence/run_f3_off_n16r60_seed42/run.jsonl \
    --out v2/evidence/group_presence_20261024/group_presence_metrics.json
```

重放校验（输出应与已提交 JSON 字节一致）：

```bash
python3 tools/f9/group_presence_metrics.py \
    --run v2/evidence/run_f3_off_n16r60_seed42/run.jsonl --out /tmp/gp_rerun.json
sha256sum /tmp/gp_rerun.json v2/evidence/group_presence_20261024/group_presence_metrics.json
# 两行 hash 应相同；脚本无时间戳字段，输出确定性
```

输入指纹自检：

```bash
sha256sum v2/evidence/run_f3_off_n16r60_seed42/run.jsonl   # 应为 19d5cb03…
```

## 3. 全域分母是怎么算出来的（self-check 起点）

```
agents            = AGENT_BORN.payload.agent_id 去重                = 16 (P001..P016)
days              = ACTIVITY_STARTED.payload.day 去重               = 5  (day 0..4)
                   交叉校验：TURN_SEAL 条数 60 ÷ 每日 12 round = 5.0；
                             TIME_MARK.payload.day 去重也是 5
slots_per_day     = code/life/constants.py TIME_CONFIG.SLOTS_PER_DAY = 4 (morning/afternoon/evening/night)
rounds_per_slot   = 3，rounds_per_day = 3 × 4 = 12
agent_day_slot 全域 = 16 × 5 × 4 = 320
```

实际观测：`ACTIVITY_STARTED` 行数 = 320，去重 (agent, day, slot) = 320，
即 **缺失 0 格**（`universe.self_check_no_activity_cells = 0`）。所有比例的分母都锚在这个 320（或它在某个子集口径下的明确子分母）上。

## 4. 关键读数与每个字段的分母口径

### A. 聚集层（`gathering`）

| 字段 | 值 | 分子 | 分母 | 口径说明 |
|---|---|---|---|---|
| `group_created.total` | 17 | — | 17 | 日志内 `GROUP_CREATED` 事件总数 |
| `group_created.by_place` | `{market: 17}` | — | 17 | 取 `group_id` 形如 `place:<name>` 冒号后部分（本日志全部为 `place:market`） |
| `group_created.by_slot` | `{afternoon: 17}` | — | 17 | `payload.slot` |
| `group_created.members_size_distribution` | `{8: 17}` | — | 17 | `len(members)`；17 个群的成员集合互不相同（`distinct_member_sets=17`） |
| `activity_started.total_rows` | 320 | — | 320 | `ACTIVITY_STARTED` 行数（每 (agent,day,slot) 一行；同一多人活动会以"每个参与 agent 一行"的形式重复出现） |
| `participants_size_distribution` | `{1:204, 2:99, 8:17}` | — | 320 | `len(payload.participants)` 的直方图；本日志只出现 1/2/8 三档 |
| `participants_buckets` | `{1:204, 2-4:99, 5+:17}` | — | 320 | 按人数分档（1 人 / 2–4 人 / 5+ 人） |
| `multi_person_ratio` | 116/320 = **36.25%** | 116 | 320 | 分子 = `len(participants) >= 2` 的行数；分母 = 全部行。**按 agent-槽计，不是去重后的活动数** |
| `place_arrived.total` | 299 | — | 299 | `PLACE_ARRIVED` 行数（只有发生移动的 agent-槽才发） |
| `place_arrived.by_place` | residence 80 / cafe 53 / park 27 / market 26 / farm 21 / plaza 17 / bank 15 / school 13 / library 11 / workshop 11 / community_center 9 / kitchen 6 / office 4 / town_hall 4 / clinic 2 | — | 299 | 同上 |
| `agent_slots_without_arrival` | 21 | — | 320 | 320 − 299；原地未移动的 agent-槽，其地点仍由同槽 `ACTIVITY_STARTED.place` 表征 |
| `arrival_place_vs_activity_place_mismatch` | 0 | — | 299 | 交叉校验：同槽 `PLACE_ARRIVED.place` 与 `ACTIVITY_STARTED.place` 零不一致 → 支持用 `ACTIVITY_STARTED.place` 当"同处地点" |
| `per_agent_day_multi_involvement.mean / median / p90` | 1.45 / 1.0 / 2.0 | — | 80 | (agent, day) 网格 = 16 × 5；每格计数 = 该 agent 当天的 `len(participants)>=2` 行数。中位数为标准中位数，P90 为 nearest-rank（第 ceil(0.9×80)=72 名） |

### B. 同场共处（`copresence`）

同处地点定义：`ACTIVITY_STARTED.place`。归组键：`(day, slot, place)`。
两个版本并列（因为 residency 是私域，夜槽 rest 全在 residence，会把"同处"抬到 100%）：

| 指标 | 含 residence | 不含 residence |
|---|---|---|
| `place_groups_total`（三元组个数） | 92 | 87 |
| 同处人数直方图 | 1:35, 2:17, 3:13, 4:8, 5:5, 6:4, 7:1, 9:1, 10:1, 12:1, 13:1, 16:5 | 1:35, 2:17, 3:13, 4:8, 5:5, 6:4, 7:1, 9:1, 10:1, 12:1, 13:1 |
| ≥2 人的三元组占比 | **57/92 = 61.96%** | **52/87 = 59.77%** |
| 身处 ≥2 人地点的 agent-槽占比 | **285/320 = 89.06%** | **205/240 = 85.42%** |
| 有 ≥2 人同处的 (day,slot) 占比 | **20/20 = 100%** | **15/15 = 100%** |

分母口径：
- 三元组占比分母 = 该口径下的 `(day, slot, place)` 个数（含 residence 92 / 不含 87）；
- person 级分母 = 该口径下纳入的 `ACTIVITY_STARTED` 行数（320 / 240）；
- (day,slot) 分母 = 含 residence 20 个格子；不含 residence 只统计出现非 residence 活动的 15 个格子（5 天 × 3 个白天槽）。
- 注：`16:5` 一档即 5 个夜槽里全部 16 人都在 residence。

### C. 独处 / 空闲（`solitude_idle`）

| 字段 | 值 | 分子 | 分母 | 口径说明 |
|---|---|---|---|---|
| `idle_cells_no_activity` | 0 | 0 | 320 | 无 `ACTIVITY_STARTED` 的 (agent,day,slot) 格数 |
| `idle_ratio_no_activity` | **0.0%** | 0 | 320 | 结构下限，**不可当行为结论**（见下 self-check） |
| `solo_activity_rows` | 204 | — | 320 | `len(participants) <= 1` 的行数 |
| `solo_activity_ratio` | **63.75%** | 204 | 320 | 全部行 |
| `solo_activity_ratio_excluding_night` | **51.67%** | 124 | 240 | 夜槽 80 行恒为单人 rest/residence，机械抬高独处占比，故另给白天三槽口径 |

#### self-check：planner 的 1/3 跳过门与 `_base_activity` 兜底到底造成什么

- `code/life/planner.py:102-104`：`sha256(f"{agent_id}|{slot_id}|gate")[:2] % 3 == 0` 时 `plan_slot` 返回 `None`。
- `code/life/agent.py:_weekly_slots`：`chosen` 为 `None` 时走 `_choose_activity → _base_activity`（`agent.py:594-607`），
  仍然产出一个 `(activity_type, place)`（如 morning→work/farm、night→rest/residence），并照常发出 `ACTIVITY_STARTED`。
- 复刻结果（脚本内 `gate_skipped()` 与日志对照）：
  - 全域门命中 111 格；其中白天三槽 83 格；
  - 白天三槽 240 行里，**无 `template` 字段的行正好 83 行，与门命中逐格吻合 240/240**；
  - 夜槽 80 行全部无 `template`：因为 planner 没有 night 规则（`_RULES` 无 night 候选），与门无关。
- 结论：**"ACTIVITY_STARTED 缺席" 在本日志中不存在（0/320）**，门跳过只改"计划来源"（planner 模板 → base 兜底），
  不会产生"空闲槽"。因此 `idle_ratio_no_activity = 0` 是设计使然的结构下限；要度量"空闲"必须换尺子（本文件不提供，避免臆造口径）。

### 未确认项（`solitude_idle.unconfirmed`，原样保留）

1. "无活动安排 slot" 恒为 0，属结构下限，不可当作"居民不空闲"的行为结论。
2. `participants` 是各 agent 自己计划里的同伴名单；同一 (day,slot) 下不同 agent 行里的同伴集合可能不同
   （例：day0 morning，P004 的列表是 `[P004,P002]`，P009 的是 `[P009,P004]`）。"计划同伴"与"实际同处"是两个口径，
   本文件分别给出，二者的一致率**未确认**。
3. 独处/空闲的行为语义（如独处是否等于孤独）未确认，本文件不作价值判断。

## 5. 读数摘要（供报告引用）

- 320 个 agent-槽全部有活动；多人活动 116/320（36.25%）；单人 204/320（63.75%），白天三槽 124/240（51.67%）。
- `GROUP_CREATED` 仅 17 次，全部 `place:market` / `afternoon` / 成员 8 人（`members_size_distribution={8:17}`）。
- 同场共处：不含 residence 口径下 52/87 个 (day,slot,place) 有 ≥2 人（59.77%），
  身处 ≥2 人地点的 agent-槽 205/240（85.42%）；15 个白天 (day,slot) 格子**全部**出现过 ≥2 人同处。
- `PLACE_ARRIVED` 299 次，residence 80 次为最高频；21 个 agent-槽未发生移动。
