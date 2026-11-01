# R53 维度预登记卡：作息「个体差异 / 错峰」· 同角色对-时段同质率 · 两臂对照

- 卡片 ID：`R53-schedule-offset-prereg-20261102`
- 冻结时刻：**2026-11-02T04:10:10+08:00**（本文件 commit 时间必须早于任一新臂 `start_epoch.txt`，对账命令见 §10）
- 状态：**判据先于数据** —— 本卡在任何 R53 臂 `run.jsonl` 落盘之前冻结；跑批启动后**不得修改本卡任何数字与阈值**
- 维度：**居民日常作息的个体差异（"同职业不同人不该是同一套作息"）**
  其母构念是团队北极星「生活气息」；本卡只把母构念下的**一个可测代理**落成判据（能/不能证明什么见 §7）
- 分支：`feat/r53-schedule-offset`，基线 `18a78fe733587012a1b73bda1cb34c4ef3179c40`（= 采样时点 HEAD），**不碰 master**
- 尺子（本轮冻结，先落盘后读数）：`tools/metrics/schedule_homophily.py`
  `ruler_version = r53-schedule-offset-v1`，`impl_sha256 = 77d574494c0d5c4e33e88a5b6f73f5c75e8a49040621c2e3ce656046b0d79638`（379 行）
  角色表：`code/config/personas.json`，`sha256 = 08d11eb36d644e55db0c9b7e00adccb81613d50476927e3acf07117f7f970f7d`（改角色表 ⇒ 本卡作废）
- 前置依据：`reports/recon-20261028.md` §7.3 候选维度表**第 4 位**「作息个体差异化（同 role 不同人错峰）」；
  `code/life/planner.py` 的 `HITT_LIVING_SLOT` 先例（单 env 开关 + 默认关 = 逐字节等价）

---

## 1. 缺陷事实（跑批前已定，逐条带证据与复算命令）

| # | 事实 | 证据 / 复算 |
|---|---|---|
| **F1** | `_base_activity(day_type, slot)` **只依赖 `(day_type, slot)` 与本人 `work_place`**，与 `agent_id` 无关 ⇒ 同 role 同 (day,slot) 的 `activity_type` **结构上必然相同** | `code/life/agent.py:868-885`（`def _base_activity`，四个分支只读 `slot` / `day_type` / `self._work_place_for(slot)`，源码随提交变动 ⇒ sha8 写 `TODO`） |
| **F2** | 时点层面**零差异**：`planned_tick = dow * 12 + si * ROUNDS_PER_SLOT`，与 agent 无关 ⇒ 全体居民同 slot 的 `start_tick` 逐位相同 | `code/life/agent.py:849`；实测 `tick_homophily = 96/96 = 1.0000`（§1 表 T1 第 1 行） |
| **F3** | 该读数是**确定性量，与提示词臂/LLM 抽样无关**：6 个既有批次（含 R51、R52 各自两臂）上 `act_homophily` **逐位相同**（r36 批 `63/96`，r24 批 `42/64`） | 表 T1；复算命令 §6 第 1 条 |
| **F4** | 唯一能把同 role 两人拉开的，是 `_choose_activity()` 的 deprivation 覆盖（`needs < θ_dep` 时改去满足需求）⇒ 现状 34.4% 的"差异"来自**需求**，不来自个人习惯 | `code/life/agent.py:897-912`；`1 − 63/96 = 34.4%`。**未确认**：这 33 个 pair-cell 是否 100% 由 `needs<θ_dep` 引起（未逐条核对 needs 快照，标「未确认」，不作为判据依据） |
| **F5** | 同 role 差异**在场所层面也已存在一部分**，但受场所容量/开放时段限制 | `place_homophily = 45/96 = 0.4688`、`both_homophily = 45/96 = 0.4688`（表 T1） |
| **F6** | 该维度**与近期三条线不重叠**（核对见 §8.2） | §8.2 |

### 表 T1 · 6 个既有批次上的同一把尺子读数（**零 LLM、零跑批，只读既有日志**）

复算命令见 §6 第 1 条（把 `<批>` 换成表内批次名即可）。

| 批次 | 臂性质 | `pair_cells`(分母) | `act_homophily` | `tick_homophily` | `work_share_day` |
|---|---|---|---|---|---|
| `r52-scene-fresh-off-20261102_n16r36_s42` | R52 OFF | 96 | **63/96 = 0.6563** | 96/96 = 1.0000 | 35/96 = 0.3646 |
| `r52-scene-fresh-on-20261102_n16r36_s42` | R52 ON | 96 | **63/96 = 0.6563** | 96/96 = 1.0000 | 35/96 = 0.3646 |
| `c1-scene-a1-20261101_n16r24_s42` | C1 A1 | 64 | 42/64 = 0.6563 | 64/64 = 1.0000 | 21/64 = 0.3281 |
| `c1-scene-a0-20261101_n16r24_s42` | C1 A0 | 64 | 42/64 = 0.6563 | 64/64 = 1.0000 | 21/64 = 0.3281 |
| `r51-need-speech-off-20261101_n16r24_s42` | R51 OFF | 64 | 42/64 = 0.6563 | 64/64 = 1.0000 | 21/64 = 0.3281 |
| `r51-need-speech-on-20261101_n16r24_s42` | R51 ON | 64 | 42/64 = 0.6563 | 64/64 = 1.0000 | 21/64 = 0.3281 |

> **读法（先说清，防止被当成"效果"）**：T1 全是**机制层事实**，且证明的是「现状同质率不随提示词臂移动」。
> **不得**把 T1 与 R53 读数相减来宣称"提升"之外的任何因果；T1 只用于 ① 确定基线 p、② 确定分母量级、③ 证明噪声带。
> 来源日志 sha256 见 §6 第 1 条输出里的 `log_sha256`；本卡引用一律写**文件名 + 批次目录名**（日志被 `.gitignore` 排除，身份只能以 sha256 承载）。

---

## 2. 假设

- **H1（机制层，主）**：打开 `HITT_SCHEDULE_OFFSET`（同 role 不同人拿到确定性的作息偏移）后，
  `act_homophily`（同 role 对-时段里 `activity_type` 相同的比例）从 OFF 的 0.6563 下降到 **≤ 0.50**。
- **H2（机制层，副）**：同时 `tick_homophily`（双方 `start_tick` 相同比例）从 OFF 的 1.0000 下降到 **≤ 0.75**，
  即"错峰"发生在**时间轴**上，而不是只换了活动名。
- **H3（守卫，防假改善）**：`work_share_day`（workday 的 morning/afternoon 里 `work` 条数占比）
  ON 相对 OFF **下降不超过 5.0pp** —— 不允许用"把工作换成闲逛"来换 H1/H2。
- **H0**：开关不改变分配，读数差异只来自噪声。

---

## 3. 两臂设计（单变量，逐字冻结）

| 项 | OFF 臂 | ON 臂 |
|---|---|---|
| 分支 / 树 | `feat/r53-schedule-offset`，**同一 HEAD（同一 `code_sha`）** | 同左 |
| `HITT_SCHEDULE_OFFSET` | **不设**（= 改动前语义，逐字节等价） | **`1`** |
| `HITT_LIVING_SLOT`（F-5 既有臂） | **不设** | **不设**（两臂都关，避免与 F-5 的 per-agent 模板选择混淆） |
| `HITT_LLM_PROVIDER` | `openai_compat` | 同左 |
| `HITT_WORLD_SEED` | `42` | 同左 |
| 批参 | `--seed 42 --agents 16 --rounds 36 --flush-every 2` | 同左 |
| 批目录 | `v2/evidence/r53-schedule-offset-off-2026110<n>_n16r36_s42` | `v2/evidence/r53-schedule-offset-on-2026110<n>_n16r36_s42` |

- **唯一差异 = `HITT_SCHEDULE_OFFSET`**，由两臂 `env_manifest.txt` 逐 key 双向比对核验（§6 第 5 条）。
- **为什么 r36 而不是 r24**：本读数的分母 = 同角色对-时段细胞数。r24 实测 **64 < 68**（表 T1），按看板纪律「分母 <68 一律 probe/不可判」⇒ r24 下本维度**结构上不可判**；r36 实测 **96 ≥ 68**。这不是"挑好看的样本量"，而是**判据可判的最低样本量要求**。

---

## 4. 判据（冻结；事后不得下调阈值、不得改分母口径）

### 4.1 主判据 C1（机制层，作息被拉开）

- **分子** `num` = 满足以下全部条件的 **pair-cell** 数：该 (day, slot) 细胞内，同 `role_id` 的两位居民**都**有 `ACTIVITY_STARTED`，且两人 `activity_type` **相同**。
- **分母** `den` = 该 (day, slot) 细胞内，同 `role_id` 两人**都**有 `ACTIVITY_STARTED` 的 **pair-cell** 总数。
  （任一方缺该时段记录 ⇒ 不进分母，**不补 0**；缺的原因可能是 `DROPPED`/`INTENT_REJECTED`/睡过去，口径上不可判。）
- **指标** `act_homophily = num / den`（越低越好）。
- **通过线（两条同时满足）**：
  1. `act_homophily(ON) ≤ 0.50`；
  2. `Δ = act_homophily(OFF) − act_homophily(ON) ≥ +15.0pp`（百分点）。
- **band_source**：`rule-of-three(3/96) = 3.125pp`。⇒ 阈值 15.0pp = **4.8 × 噪声带上界**。

### 4.2 副判据 C2（机制层，错峰落在时间轴）

- **分子/分母**：同 C1 的 pair-cell 分母；分子 = 两人 `start_tick` **相同**的 pair-cell 数。
- **通过线**：`tick_homophily(ON) ≤ 0.75` **且** `Δ ≥ +25.0pp`。
- **band_source**：`rule-of-three(3/96) = 3.125pp`（阈值 = 8.0 × 带）。
- **为什么阈值更高**：OFF 是 **1.0000（天花板式一致）**，机制只要真的错峰就应大幅下降；若只降一点点，说明偏移没真正作用到时间轴，不适合判"成立"。

### 4.3 守卫 G1（防假改善，**不通过即整轮不得判"成立"**）

- **分子** = `slot ∈ {morning, afternoon}` 且 `activity_type == "work"` 的 `ACTIVITY_STARTED` **条数**；
  **分母** = 同范围的 `ACTIVITY_STARTED` **条数**（注意：**条**，不是 pair-cell）。
  口径对齐 `code/life/planner.py` 里的 G3 先例（"不许压低生产性活动占比"）。
- **通过线**：`work_share_day(OFF) − work_share_day(ON) ≤ 5.0pp`。
- **band_source**：`rule-of-three(3/96) = 3.125pp`（阈值 = 1.6 × 带）。

### 4.4 只描述、不判的读数（写进报告但不参与三态）

`place_homophily`、`both_homophily`（OFF 各 0.4688）。
理由：场所由 `_work_place_for()` + 场所 `open_slots`/`affordances` 容量约束决定，个体差异**会被容量上限压住**；
把它设成判据，机制成功也可能被判"不成立" ⇒ 只作描述项。

### 4.5 噪声带与统计口径（**预登记时写死，防事后改口径**）

1. 本读数在 6 个既有批次上**逐位相同**（表 T1）⇒ 观测方差 = 0，属**确定性分配读数**，不是抽样量。
   因此本轮 **不做二项推断、不报 p、不用 p 作通过线**；band 一律用 `rule-of-three(3/den)` 作保守上界。
2. **口径争议预先备案（必须照抄进报告）**：若审计方坚持把本读数当二项比例处理，则
   `mde_pp(p=0.65625, n_off=96, n_on=96) = 17.64pp`（复算见 §6 第 4 条），
   **大于 C1 的 15.0pp 阈值** ⇒ 在该口径下 C1 只能标「不可判（功效不足）」。
   **本卡的选择是**：C1 是**机制层确定性判定**（开关有没有改变分配），不是效果推断，故采用 rule-of-three 口径；
   一旦报告里出现任何"提升/改善"类效果表述，该作者**必须**同时披露上句争议，否则该结论作废。

### 4.6 次判据 C1b（**预登记加固件**，与 C1 并列冻结；由 §4.5 第 2 条的 MDE 推导而来）

> **来历（写清，供审计确认这是"跑批前加固"而不是"事后调阈值"）**：
> §4.5 第 2 条已经算出了二项口径下的 MDE = **17.64pp**（`mde_pp(0.65625, 96, 96)`，`p` 取自表 T1 OFF 基线、`n` 取 r36 每臂预期分母 96）。
> 若只把这条写成"审计方若坚持二项口径则 C1 不可判"，整轮结论就会悬在一个**口径选择**上；
> 因此本卡在**零数据时点**（任何 R53 臂 `run.jsonl` 落盘之前）把二项口径也冻成一条独立判据，
> 使口径争议从"结论算不算数"降级为"两条已冻结判据各自成立与否"。
> **本节的加入时刻晚于 §4.1，但早于任何数据**（时序可用 §10 的 `git log` 命令核：本文件两次 commit 均早于两臂 `start_epoch.txt`）。

- **C1b 的分子 / 分母 / `ON` 上限与 C1 完全相同**（同一条 pair-cell 分母定义、同一个 `act_homophily` 指标、同样要求 `act_homophily(ON) ≤ 0.50`）。
  ⚠️ **分母定义一个字节都不动**：C1b 不是新口径，只是把 Δ 阈值换成分母同一口径下的二项 MDE。
- **唯一差别**：`C1b` 的 Δ 阈值 = **`Δ ≥ +17.64pp`**（而 C1 是 `Δ ≥ +15.0pp`）⇒ 逻辑上 **C1b 严格强于 C1**：`C1b 成立 ⇒ C1 必然成立`。
- **band_source**：`MDE(α=.05, power=.80) = 17.64pp`（复算 `python3 -c "import sys;sys.path.insert(0,'tools/metrics');from need_to_speech import mde_pp;print(mde_pp(0.65625,96,96))"` → `17.64`）。
  这条 band 的口径与 C1 的 `rule-of-three(3/96)=3.125pp` **不同源**，是**刻意**的：两条判据分别代表"确定性机制口径"与"保守二项口径"。
- **阈值冻结、不得重算**：`17.64pp` 是在 `n=96/96` 口径下算出的 MDE。**若收批后实际 `pair_cells` 不等于 96，也不得重算阈值**；
  报告只能在读数旁追加一行描述性备注「C1b 的 MDE 依据 n=96，实收分母为 X」，**不改变任何阈值**（与 §4「事后不得下调」同一条纪律）。
- **C1b 同样受 §5 全部不可判条件约束**（命中任一 ⇒ C1b 也写「不可判」，不得写「不成立」）。
- **G1 不动**：本轮守卫仍只有 G1 一条，C1b 不附带新守卫、不改变 G1 的任何数字。

### 4.7 C1 / C1b 三态组合的唯一读法（**禁止只挑对结论有利的那条报**）

| C1（Δ≥15.0pp，rule-of-three 带） | C1b（Δ≥17.64pp，二项 MDE） | 报告里**唯一允许**的表述 |
|---|---|---|
| 成立 | 成立 | 「**稳健成立**」：两套口径同时达标 ⇒ Δ 相对两条带都有余量 |
| 成立 | 不成立 | 「**方向成立但不稳健**」：必须**同表并列**给出 `Δ`、C1 判「成立」、C1b 判「不成立」，并写明"二项口径下未达 MDE"；**不得**只报 C1 |
| 不成立 | 不成立 | 「**不成立**」（C1b 必然也不成立，因为 C1b 严格强于 C1） |
| 任一为「不可判」 | 任意 | 「**不可判**」，并逐条列出命中的 §5 条件 |

- 机械可核验的硬约束：报告里凡是出现"成立"字样的行，必须**同时**出现 `C1` 与 `C1b` 两个标签（或同表两列），缺一即视为选择性报告，该结论作废。
- `C1 不成立 + C1b 成立` 是**逻辑上不可能**的组合（C1b 严格强于 C1）；若读数出现，说明尺子或阈值实现有缺陷 ⇒ 报告必须登记为「判据实现缺陷 D-1」并停止出结论。

---

## 5. 不可判条件（命中任一即写「不可判」，**不得写「不成立」**）

1. 任一臂 `pair_cells < 68`（看板纪律：分母 <68 一律只报条数）；
2. 两臂 `env_manifest.txt` 差异**不止** `HITT_SCHEDULE_OFFSET` 一行（例如有人顺手开了 `HITT_LIVING_SLOT`）⇒ 两臂不可比；
3. 任一臂 `run_batch.rc != 0`、或缺 `meta.json`、或 `wc -l run.jsonl != meta.events`；
4. 任一臂 `obs llm-cost --require-provider openai_compat` 的 `provider_guard.ok != true` 或 `degraded != 0`；
5. 两臂 `personas_sha256` 不一致（角色表漂移 ⇒ 尺子口径漂移）；
6. 两臂 `activity_started_events == 0`（日志无该事件类型）。

---

## 6. 读数与复算命令（他人照抄可复现；全部在**仓库根**执行；零 LLM）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# 1) 单臂读数（表 T1 的复算入口；把 <批> 换成表内批次名）
python3 tools/metrics/schedule_homophily.py --arm x=v2/evidence/<批>/run.jsonl

# 2) 两臂对照 + 落盘（阈值照本卡 §4 原文抄，不得改写）
python3 tools/metrics/schedule_homophily.py \
  --arm off=v2/evidence/r53-schedule-offset-off-2026110<n>_n16r36_s42/run.jsonl \
  --arm on=v2/evidence/r53-schedule-offset-on-2026110<n>_n16r36_s42/run.jsonl \
  --thr-act-max 0.50 --thr-act-delta-pp 15.0 \
  --thr-tick-max 0.75 --thr-tick-delta-pp 25.0 \
  --thr-work-guard-pp 5.0 \
  --out-json v2/evidence/r53-schedule-offset/compare.json

# 3) 幂等自检（同一输入两次运行逐字节一致）
python3 tools/metrics/schedule_homophily.py --arm off=<off>/run.jsonl --arm on=<on>/run.jsonl \
  --thr-act-max 0.50 --thr-act-delta-pp 15.0 --thr-tick-max 0.75 --thr-tick-delta-pp 25.0 \
  --thr-work-guard-pp 5.0 > /tmp/r53_a.json
python3 tools/metrics/schedule_homophily.py --arm off=<off>/run.jsonl --arm on=<on>/run.jsonl \
  --thr-act-max 0.50 --thr-act-delta-pp 15.0 --thr-tick-max 0.75 --thr-tick-delta-pp 25.0 \
  --thr-work-guard-pp 5.0 > /tmp/r53_b.json
cmp /tmp/r53_a.json /tmp/r53_b.json && echo BYTE_IDENTICAL      # 落盘前已实测：BYTE_IDENTICAL

# 4) MDE 旁注（§4.5 第 2 条争议里的那个数，也是 C1b 阈值的唯一来源）
python3 -c "import sys;sys.path.insert(0,'tools/metrics');from need_to_speech import mde_pp;print(mde_pp(0.65625,96,96))"   # → 17.64

# 4b) C1b 机械比对（从第 2 条落盘的 compare.json 里取 C1 的 delta_pp，与冻结阈值 17.64 比；
#     分子/分母/ON 上限与 C1 同源，故不另算一遍读数，避免第二套数）
python3 - <<'PY'
import json
c = json.load(open("v2/evidence/r53-schedule-offset/compare.json"))["compare"]["C1_act_homophily"]
d = c["delta_pp"]
c1  = "成立" if (c["rate_on"] is not None and c["rate_on"] <= 0.50 and d >= 15.0) else "不成立"
c1b = "成立" if (c["rate_on"] is not None and c["rate_on"] <= 0.50 and d >= 17.64) else "不成立"
print(f"delta_pp={d}  rate_on={c['rate_on']}  C1={c1}(Δ>=15.0)  C1b={c1b}(Δ>=17.64)")
print("C1不成立+C1b成立 ⇒ 判据实现缺陷 D-1（逻辑不可能）" if (c1 == "不成立" and c1b == "成立") else "组合合法")
PY

# 5) 单变量对账（两臂 env 差异只应有 HITT_SCHEDULE_OFFSET）
diff <(sort v2/evidence/<off>/env_manifest.txt) <(sort v2/evidence/<on>/env_manifest.txt)

# 6) 真 LLM 验真（在 code/ 下）
cd code && python3 -m obs llm-cost --log ../v2/evidence/<arm>/run.jsonl --require-provider openai_compat
```

**尺子假阳性自检（落盘前已实测，可复算）**：

```bash
# (a) 负对照：R52 两臂对作息应无影响 ⇒ C1/C2 必须判「不成立」（Δ = 0.0pp），不得乱报成立
python3 tools/metrics/schedule_homophily.py \
  --arm off=v2/evidence/r52-scene-fresh-off-20261102_n16r36_s42/run.jsonl \
  --arm on=v2/evidence/r52-scene-fresh-on-20261102_n16r36_s42/run.jsonl \
  --thr-act-max 0.50 --thr-act-delta-pp 15.0 --thr-tick-max 0.75 --thr-tick-delta-pp 25.0 \
  --thr-work-guard-pp 5.0 | python3 -c "import json,sys;c=json.load(sys.stdin)['compare'];print(c['C1_act_homophily']['verdict'],c['C1_act_homophily']['delta_pp'],c['C2_tick_homophily']['verdict'],c['G1_work_share_day']['verdict'])"
# → 不成立 0.0 不成立 成立

# (b) 分母不足路径：r24 批 pair_cells=64 < 68 ⇒ 必须判「不可判」
python3 tools/metrics/schedule_homophily.py \
  --arm off=v2/evidence/r51-need-speech-off-20261101_n16r24_s42/run.jsonl \
  --arm on=v2/evidence/r51-need-speech-on-20261101_n16r24_s42/run.jsonl \
  --thr-act-max 0.50 --thr-act-delta-pp 15.0 | python3 -c "import json,sys;c=json.load(sys.stdin)['compare'];print(c['_undecidable_reasons'],c['C1_act_homophily']['verdict'])"
# → ['pair_cells 分母过低（off=64, on=64, min=68）'] 不可判
```

---

## 7. 本维度**能证明什么 / 不能证明什么**（禁用构念公示）

**能证明（机制层）**
1. 日程分配层是否真的被**个体化**：同职业不同人在同一时段的 `activity_type` 不再是同一套（C1）。
2. 错峰是否发生在**时间轴**上（`start_tick` 不再全体相同）（C2）。
3. 该个体化是否**没有把生产性活动挤掉**（G1）。
4. 以上三条都是**纯日志可算、两次运行逐字节一致**的读数，第三方可逐条复跑。

**不能证明（写清楚，任何报告不得越界）**
1. **不能证明「生活气息 / 更像真人」**：该构念在本仓无人工盲评、无 LLM judge 标定、无跨 seed 复现
   ⇒ **本维度不发布该类主张**（团队明令 + `reports/README.md` 固定禁令）。
2. **不能证明观感提升**：`act_homophily` 下降只是"分配被拉开"，**不等于**"居民更像有自己习惯的人"——
   居民可能只是被分到不同活动，主观体验、对话内容未必改变。
3. **不能证明因果链下游**：日程差异是否让对话/记忆/关系变好，本卡**不测、不主张**。
4. **不能跨 seed 外推**：单 seed(42)，无批间方差估计；读数只能作本批点估计。
5. **不能与历史周期读数相减**：表 T1 只用来定基线 p、分母量级与噪声带，**不得**写成"比 R51/R52 提升/下降 X pp"。
6. **不测"居民是否感知到自己的作息不同"**：本卡只测分配侧，不测感知侧。

---

## 8. 选型论证

### 8.1 候选与淘汰（三选一，逐条给淘汰理由）

| # | 候选维度 | 判据能否纯日志算 | 改动面 | 结论 |
|---|---|---|---|---|
| **A** | **作息个体差异 / 错峰**（本卡选的） | 能：`ACTIVITY_STARTED` 的 `(agent_id, day, slot, activity_type, activity_start_tick)`，分母 r36=96 ≥ 68 | 小：`code/life` 内单一默认关开关（先例 `planner.py::HITT_LIVING_SLOT`） | **选中** |
| B | **台词「时辰感」/时段词显性化** | 能：`tools/metrics/timeword_readings.py`（**已实跑**：R52 OFF 批 `timeword = 46/294 = 15.65%`，rc=0） | 小（prompt 加一行） | **淘汰：与 R52 处境锚机制重复**——`code/life/scene_anchor.py` 已把「此刻什么时段」渲染成一行注入提示词（`scene_anchor.py:37` 时段→人话词表），且 `tools/d5/dialogue_metrics.py` 已有 **F-8t 时段锚定率**专测这件事 ⇒ 再开一臂是同一机制的重复计费 |
| C | **回应里的「承接词/接话头」率**（嗯/是啊/可不是 起头） | 能（实测 OFF 仅 6/200 = 3.0%，有巨大空间） | 小（prompt 加一行） | **淘汰：与 L-7 结构臂争同一层**——`code/life/l7_structural.py` 已用确定性轮转控制**开口方式**（`OPEN_FORMS` 6 选 1，含"用语气词起头"、`mode=initiate/reply` 都覆盖），再加一条开口规则会与既有轮转冲突（两套规则抢同一句的开头），单变量不成立 |

> 另外两个**未列入候选**（避免浪费评审时间，说明理由即可）：
> - 「情绪呼应 F-3」——`code/life/emotion_echo.py` / `HITT_DIALOGUE_EMOTION_ECHO` 已有臂（R38/R46 线）；
> - 「对话具体性/多样性」——R49 线（`HITT_D12_DETAIL`）已做且读数接近天花板（`distinct_body_ratio 191/191`）。

### 8.2 撞车核对（**逐条给核对依据**）

| 线 | 它测/改的是哪一层 | 核对依据 | 结论 |
|---|---|---|---|
| **R49** 生活多样性 | **对话措辞层**：`HITT_D12_DETAIL` 具体性起句 | `reports/R49-prereg-diversity-20261101.md` 开篇即「居民对话的具体性起句 / 措辞多样性」，臂 = `HITT_D12_DETAIL` | 不重叠（不同层：措辞 vs 日程分配） |
| **R51** 需求人话化 + 紧迫门控 | **提示词文本层**：`_mood_line()` 一行 | `reports/R51-prereg-need-speech-20261101.md` §0；`code/life/agent.py:98` 注释「只影响 `_mood_line()` 一行文本」 | 不重叠 |
| **R52** 处境锚取值时点 | **提示词装配时点**：`HITT_SCENE_FRESH` | `reports/R52-prereg-scene-fresh-20261102.md` §1 F1–F5；`code/life/scene_anchor.py` | 不重叠（且负对照实测：R52 两臂在本尺子上 Δ=0.0pp，见 §6 自检 (a)） |
| **origin/master 的 rift 线** | 证据/口径/对账框架（`reports/`、`tools/dr/`、`v2/evidence/`） | `git diff --name-only 94e272a origin/master \| grep -c "^code/"` → **0**；`git log origin/master -60 --format='%s' \| grep -icE '作息\|日程\|schedule\|planner'` → **0** | 不重叠（该线**一行 `code/` 都没改**） |
| **F-5 既有臂** `HITT_LIVING_SLOT` | 闲时段（evening / 周末下午）的**生活类模板**选择 | `code/life/planner.py:28-42` | **有邻接，已隔离**：两臂都关 F-5（§3），且本轮覆盖 workday morning/afternoon 等 F-5 明确不碰的时段；G1 守卫防止以挤掉 work 为代价 |

---

## 9. 实现需要的最小接口契约（给 `life-impl`，**照着做，不要自行扩大**）

### 9.1 开关

- 名字：**`HITT_SCHEDULE_OFFSET`**；取值 `{1,true,yes,on}` 为开，**未设 / 其它值 = 关**（默认关）。
- 判定函数写法照 `code/life/planner.py:45 living_enabled()` 同款（`.strip().lower() in {"1","true","yes","on"}`）。

### 9.2 允许改动的文件（白名单）

| 文件 | 允许做什么 |
|---|---|
| `code/life/agent.py` | ① `_plan()`（`:787` 起）里 `planned_tick`（`:849`）与 `_choose_activity/_base_activity` 调用点加**开关后的分支**；② 新增 `ctx`/`meta` 审计键（additive，参照 `ctx.l7struct` 先例） |
| `code/life/schedule_offset.py` | **新增**（可选，推荐）：偏移逻辑集中在此，便于单测与指纹 |
| `code/tests/test_r53_schedule_offset.py` | **新增**：零 LLM 单测（见 9.5） |

### 9.3 禁止改动（碰了就作废本卡 + 破闸门2）

- `code/config/*.json` 任何文件（不新增模板、不改 `TIME_CONFIG`/`SLOTS_PER_DAY`/`ROUNDS_PER_SLOT`、不改 `personas.json`、
  不改 `ACTIVITY_TO_PLACES`）；`code/engine/**`；`code/orchestration/**`。
- 不改 `engine_version` 指纹（不改 config 即自然满足）；不新增事件类型；不动 `state_hash` 口径。

### 9.4 机制约束（可审计的四条）

1. **确定性**：偏移量由 `sha256(agent_id|slot_id|kind)` 决定（先例：`code/life/planner.py::_pick`、`code/life/agent.py:340` 的 encounter-pick 哈希串），**不得**用 `random`/墙钟/进程内递增状态。
2. **取值合法**：只能从**该 slot 下已合法的既有候选**里取——候选 `(activity_type, place)` 必须过 `self._valid(atype, place, slot)`（`agent.py:886`），活动类型只能来自 `_base_activity` 的四个分支与 `_NEED_ACTIVITY` 已用的集合，**不新造活动类型/场所**。
3. **时点边界**：`planned_tick` 偏移量 ∈ `{-1, 0, +1}` 且**不得越过本 slot 边界**（`dow*12 + si*R` 到 `+R-1`），且**不得**与同日其它 slot 的 `planned_tick` 冲突（确定性贪心即可，冲突回退 0）。
4. **不许抢生产**：workday 的 morning/afternoon 里 `work` 的活动**不得**被偏移成非 work（这是 G1 在代码层的对应约束；`night` 仍固定 `rest`/`residence`，不许动）。

### 9.5 关掉时必须逐字节等价（**这是验收的硬条件**）

- `HITT_SCHEDULE_OFFSET` 未设时：`plan()` 返回 `None`、`render()` 返回空串（若做了模块化），
  `_plan()` 产出的 `SCHEDULE_PLANNED.slots` 与改动前**逐字节相同**（含键序以外的一切字段值）。
- 证明方式（零 LLM，照 `tools/r52/prompt_hash_probe.py` 先例）：
  ① 单测 `test_r53_schedule_offset.py` 覆盖「关 ⇒ 计划对象与基线夹具逐字段相等」；
  ② 起批前对同一 seed 跑一次 `SCHEDULE_PLANNED` 序列指纹（sha256），与改动前树上的指纹比对相等；
  ③ 报告里给出两个指纹的 sha256。
- 开时：同一 `(agent_id, slot_id)` 两次 `plan()` 结果必须相同（确定性断言）。

### 9.6 meta 与两臂记账

- 按 `reports/CYCLE-52-20261102.md` §⑤ 第 7 条，把本开关登记进 `meta.switch_declared` / `meta.switch_effective`（若机制尚未实现，至少在 `env_manifest.txt` 里如实出现）。
- 两臂 `env_manifest.txt` 的 `diff` **只允许**出现 `HITT_SCHEDULE_OFFSET` 一行差异（§6 第 5 条）。

---

## 10. 时间戳对账（机械可核验）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# a) 本卡**全部**入库 commit 时间（必须**都**早于任一新臂 start_epoch；
#    §4.6 C1b 加固件是第二次 commit，须与第一次一起列出来核）
git log --format='%H %ad %s' --date=iso -- reports/R53-prereg-schedule-offset-20261102.md

# b) 载荷：本卡必须早于两臂起跑
for b in r53-schedule-offset-off-*_n16r36_s42 r53-schedule-offset-on-*_n16r36_s42; do
  echo "$b start_epoch=$(cat v2/evidence/$b/start_epoch.txt 2>/dev/null)"; done

# c) 尺子未在起批后被改（改了 ⇒ 本批读数作废）
sha256sum tools/metrics/schedule_homophily.py    # 必须 == 77d57449…
sha256sum code/config/personas.json              # 必须 == 08d11eb3…

# d) 分支与基线
git rev-parse --abbrev-ref HEAD                  # feat/r53-schedule-offset
git merge-base --is-ancestor 18a78fe HEAD; echo rc=$?   # → rc=0（基线是本分支祖先）
```

---

## 11. 未确认项（显式标注，不留空、不猜）

| # | 未确认项 | 为什么未确认 |
|---|---|---|
| U-1 | F4 里那 33 个"不同质"的 pair-cell 是否 **100%** 由 `needs < θ_dep` 引起 | 未逐条把 `NEED_UPDATE` 快照与 `ACTIVITY_STARTED` 对齐核验；不作为任何判据依据 |
| U-2 | 偏移量取 `{-1,0,+1}` 是否足以让 `tick_homophily` 从 1.0 降到 ≤0.75 | 未做任何试算（本卡禁止在冻结前用跑批试参）；若实现后发现 3 档偏移不够，**只能**在报告里登记「判据缺陷」，**不得**回头改 §4.2 阈值 |
| U-3 | 场所容量（`places.json` 的 open_slots/affordances）是否会成为 C1 的隐性上限 | 已知 `place_homophily` 现状 0.4688；容量约束的量化影响未测 ⇒ 故 C1 判在 `activity_type` 层而不在场所层 |
| U-4 | `SCHEDULE_PLANNED.slots` 的字段顺序是否会因实现方式改变而影响"逐字节等价"判定 | 未验证 JSON 序列化是否 `sort_keys`；`life-impl` 实现时须自证（§9.5 第 ② 条按 sha256 比对，规避顺序歧义） |
