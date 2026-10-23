# F-5 / F-5b / F-1 跨批零成本复算（2026-10-23）

**一句话结论**：用现有工具 `tools/d5/dialogue_metrics.py` 对 **7 批**已有日志做了零 LLM 成本的确定性复算，把 F-5（习惯强度）/ F-5b（最大重复天数）的跨批现状填上了。结果是**描述性读数**，**不是** F-5 干预臂开关对照 —— **F-5 干预臂至今未做**（缺口见 §6）。而且复算暴露了两个更重要的口径事实：**2 天窗口批的 F-5 结构上不可能 >0**；**5 天窗口批的 F-5 已经顶到 1.0 天花板且跨臂逐位相同**，因此 F-5 在当前形态下对这些配置批**没有区分度**，不能用来支持任何改善结论。

---

## 1. 口径声明（先读这段）

- **指标定义唯一来源**：`tools/d5/dialogue_metrics.py`（本目录不重写指标实现）。
  - F-5 规则（工具原文）：`习惯 = 同一 agent 在同一 (slot, place) 出现 ≥3 天；强度 = 有习惯的 agent / agent 总数`
  - F-5b = `max_repeat_days_mean`（每 agent 在其最好的 (slot, place) 桶上的最大天数，再对 agent 求均值）
  - F-1 规则（工具原文）：`功能性 = tag_hints∩task_tags 非空 或 正文命中事务正则；闲聊率 = 1 − 功能性占比`；分母 = 全部对话消息数
- **分母**：F-5 分母 = 该批对话消息里出现过的不同 `from` 数 = **16**（7 批全部为 16，n16）；F-1 分母 = 该批对话消息数（191 或 510，**逐批不同**，见 §3 表）。
- **同口径同分母**：同一张表内各行的 F-5 分母都是 16、F-1 分母都是"该批全部对话消息"。**但样本量不同（191 vs 510）的 F-1 百分比精度不同，只能看方向，不能当作等价精度比较。**
- **分组而不是合并**：按日志覆盖天数分成两组（表 A days≥3 / 表 B days<3），**两组之间不可比，也不得合并求均值**。
- **本文所有数字都是"描述性读数（不同配置批落的对比），不是干预臂开关对照"**。表里数字好看/难看都不构成改善或退化的结论。

## 2. 为什么必须分组：两个结构性事实（复算副产物）

### 2.1 24 轮批只覆盖 2 天 ⇒ F-5 结构上恒为 0

`n16r24` 三批（d12b_off/on、scene_anchor_off/on）日志里 `payload.day` 只取到 `{0,1}`，即**只覆盖 2 天**。
F-5 要求"同一 (slot, place) 出现 **≥3 天**"，2 天窗口下该条件**数学上不可能成立** ⇒ `habit_strength = 0/16 = 0.0` 是**窗口长度决定的**，不是居民行为决定的。
证据：`raw/saturation_*.json` 的 `bucket_days_histogram = {1: 68, 2: 20}`，≥3 天的桶为 **0** 个。

### 2.2 5 天批的 F-5 顶在天花板，且跨臂骨架逐条相同

- `d12c_off / d12c_on / d12d_on` 三批 `habit_strength = 16/16 = 1.0`，`F-5b = 4.375`，**三批逐位相同**。
- 天花板诊断：151 个 (agent, slot, place) 桶中 42 个（27.8%）达到 ≥3 天，天数直方图 `{1: 81, 2: 28, 3: 20, 4: 14, 5: 8}`。在 16 agent × 4 slot × ~5 place 且 5 天的窗口里，"几乎人人都有 ≥3 天重复作息"是**几乎必然**的 —— 指标饱和，没有区分度。
- 更根本的原因：`raw/skeleton_identity.json` 显示，**同一骨架组内 (round, from, day, slot, place, to, thread_id) 序列的 sha256 完全相同**：
  - 组 `sha256:b00d20cc…`：`d12b_off / d12b_on / scene_anchor_off / scene_anchor_on`（191 条消息）
  - 组 `sha256:bcc6e28e…`：`d12c_off / d12c_on / d12d_on`（510 条消息）
  ⇒ 这些开关只改**对话正文**，不改**作息/移动骨架**；而 F-5/F-5b 只读骨架字段 ⇒ **同组内 F-5/F-5b 逐位相同是结构性必然**，把它当成"开关无效果"或"开关有效果"都错，它根本测不到这些开关。
- 另一个口径细节：消息里 `place` 缺失率 10.8%（5 天批）/ 12.6%（2 天批），缺失的 `place=None` 会自成 `(slot, None)` 桶参与 F-5 判定。这是**现有工具口径**，本目录不改它，只如实标注。

## 3. 对照表

见 [`f5_crossbatch.md`](f5_crossbatch.md)（人读版）与 [`f5_crossbatch.csv`](f5_crossbatch.csv)（机读版，含 `run_sha256`、footnote 全部字段）。

摘要：

| 组 | 批次 | 覆盖天数 | F-5（num/den） | F-5b | F-1 非功能性闲聊率（num/den） |
|---|---|---|---|---|---|
| A（可比） | d12c_off | 5 | 1.0（16/16） | 4.375 | 0.705882（360/510） |
| A（可比） | d12c_on | 5 | 1.0（16/16） | 4.375 | 0.698039（356/510） |
| A（可比） | d12d_on | 5 | 1.0（16/16） | 4.375 | 0.690196（352/510） |
| B（不可比，窗口<3天） | d12b_off | 2 | 0.0（0/16） | 1.75 | 0.732984（140/191） |
| B（不可比，窗口<3天） | d12b_on | 2 | 0.0（0/16） | 1.75 | 0.706806（135/191） |
| B（不可比，窗口<3天） | scene_anchor_off | 2 | 0.0（0/16） | 1.75 | 0.759162（145/191） |
| B（不可比，窗口<3天） | scene_anchor_on | 2 | 0.0（0/16） | 1.75 | 0.722513（138/191） |

读法：表 A 与表 B 的 F-5 数值**不可比**（窗口长度不同，B 组是结构性下限 0）。表 A 内部三批 F-5/F-5b 完全相同是 §2.2 的骨架同一性导致的，**不是**"三个开关都没效果"的证据。F-1 在这里**只作对照守卫读数**：表 A 三批 0.6902~0.7059（跨度 1.6 个百分点，同分母 510，纯描述性，未做显著性检验）；表 B 四批 0.7068~0.7592（分母 191）。

## 4. 一键复算

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
bash v2/evidence/f5-crossbatch-20261023/run.sh
```

逐批的等价单条命令（`--meta` 仅在该批存在时传入；d12b 两批无 meta.json）：

```bash
python3 tools/d5/dialogue_metrics.py \
  --log v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl \
  --meta v2/evidence/run_d12c_off_n16r60_seed42/meta.json \
  --out-json <out>.json --out-md <out>.md
# 其余 6 批同构，日志路径见 §3 表格 / f5_crossbatch.csv 的 log 列
```

- 复算**确定性已验证**：同一条命令两次运行，JSON 逐字节相等（`cmp` 通过）。
- `run.sh` 会先落 `tool_manifest.txt`（工具与词表/日志的 **mtime + sha256**），再逐批跑指标、覆盖度、饱和诊断，最后生成对照表。
- 环境：Python 3.12.3；零网络、零 LLM 调用（工具本身不联网）。

工具身份（完整清单见 `tool_manifest.txt`）：

| 文件 | mtime | sha256 |
|---|---|---|
| `tools/d5/dialogue_metrics.py` | 2026-10-23 02:35:09.813622133 +0800 | `1d914735f3a13cf4e1640bd694f1d0e070096c9f50abfdefa7359417df551271` |
| `tools/d5/task_tags.txt`（F-1 分母用） | 2026-10-20 17:04:08 +0800 | `a71c6c963279b28f6f9de3b44317b5c9bbf80498c594c98f9460ed79954aa69e` |

## 5. 文件清单

| 文件 | 作用 |
|---|---|
| `run.sh` | 一键复算入口（零 LLM、只读日志） |
| `f5_coverage.py` | 覆盖度事实：天数集合 / slot / place 缺失率 / agent 数（**不做指标判定**） |
| `f5_saturation.py` | F-5 天花板诊断：(agent,slot,place) 桶的天数直方图（规则与工具一致，仅解释用） |
| `f5_skeleton_identity.py` | 行为骨架同一性检查：判定哪些批的 (round,from,day,slot,place,to,thread_id) 序列完全相同 |
| `f5_build_table.py` | 只读 `raw/metrics_*.json` 汇总成 CSV（分子 = 比率×分母，脚本内做可逆性断言） |
| `raw/metrics_<batch>.json/.md` | 工具原始输出（F-5 / F-1 的权威数值在这里） |
| `raw/coverage_<batch>.json` | 逐批覆盖度事实 |
| `raw/saturation_<batch>.json` | 逐批 F-5 天花板诊断 |
| `raw/skeleton_identity.json` | 骨架同一性结论 |
| `f5_crossbatch.csv` / `f5_crossbatch.md` | 跨批对照表（机读 / 人读） |
| `tool_manifest.txt` | 工具、词表、日志的路径 + mtime + sha256 |

## 6. 缺口登记（必须随表一起引用）

1. **F-5 干预臂未做** —— 本目录全部数字都是**已有配置批的描述性读数**，没有做过任何改变"作息/习惯"机制本身的开关臂。历史基线（`round-baseline.md` §3.3）里的 v0 87.5% / A0 100% 同属描述性读数，本次 5 天批的 1.0 与 A0 100% 同量级，**只说明"饱和"，不说明"更好"**。
2. **CYCLE-08 仍然没有 F-5 臂级读数** —— 本次没有新增跑批，因此该缺口未被填充，只是被"跨批描述性对照"部分说明。
3. **F-5 当前形态对这些开关不敏感**（§2.2 骨架同一性）：若要得到可判读的 F-5 读数，必须先有**真正改动作息/移动骨架的干预臂**（否则 F-5 在臂间必然逐位相同），或改用对正文敏感的口径。**本目录不提出也不实施口径变更。**
4. **短窗口批（n16r24）不能用于 F-5**：覆盖 2 天 < 3 天阈值，任何短窗口批的 F-5=0 都不携带行为信息。
5. **准入 `REJECTED` 全部源于 `meta.json` 元数据缺失，不是日志缺陷**：
   - `d12b_off` / `d12b_on`：**目录下根本没有 `meta.json`** ⇒ 失败 4 项且全部是 meta 派生项：`B-10_provider`（detail `<empty>`）、`B-2b_manifest_effective`（rounds_effective=null）、`B-7_files`（原文「无 meta.json → 非证据级」）、`B-9_event_count`（meta.events=null）。
   - `d12c_off` / `d12c_on` / `d12d_on`：**只有 `B-10_provider` 失败**（`meta.json` 未记录 provider 字段）。
   - 日志本身是干净的真调用：`llm.provider_models = openai_compat / DeepSeek-Flash`（d12b 两批 2252 calls，d12c/d12d 三批 2878 calls），`degraded_ratio = 0.0`，`B-11_real_calls` / `B-20_model_no_mock` / `B-17_hash_chain` 等均 pass。
   - `scene_anchor_off/on` 两批 `meta.json` 齐全 ⇒ `ADMITTED`。
   - **引用 `admission_verdict` 时必须一并说明这一点**，不要把它读成"日志不可用"。
