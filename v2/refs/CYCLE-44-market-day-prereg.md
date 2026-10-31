# CYCLE-44 预登记口径卡 · market-day（集日提及/集日感知）

> **本文件是跑批前冻结的判据卡。跑批一旦开始，主判据 / 护栏 / 阈值 / 分母 / 词表 / 规模一律不得修改。**
> 任何改动必须走 §10 的 Amendment 程序，并在报告里重报本文件 sha256。
>
> **本件的可提交状态**：`repo-scout` 依 T1b（词表审计，假阳性 69.2%）与 T1c（读数器 + 功效）成稿。
> 工程师只需 **`cp` 进 `v2/refs/CYCLE-44-market-day-prereg.md` → 填 §0 的 4 个占位 → commit**，不得改动任何判据文字。

---

## 0. 文件身份与冻结物（**跑批前必须填满并 commit**）

| 项 | 值 | 取法 |
|---|---|---|
| 预登记文件 | `v2/refs/CYCLE-44-market-day-prereg.md` | 本文件 |
| **本件自身 sha256**（本行自指无法收敛，用**归一化口径**，可机械复算） | `f4c50166949e1b12d6b8f6f81442a759085d5bc89ff7b03f58a855a263ba2118` —— 复算：把本行那个 64 位十六进制值替换成字面量 `<SELF>` 后 `sha256sum` （即 `sed` 替换后取摘要；另以**入库 commit sha** 为第二锚） | `sha256sum` |
| 交付分支 | `life/market-day` | `git branch --show-current` |
| **起手 sha（两臂共同基）** | `<b3358fb2adaf452b307e181aaa8f40f4c792f33f>` | `git rev-parse HEAD` |
| **两臂 `code/` 树（两臂必须相同）** | `5c641e080b24f03e82b28c837e73ca27fec15c03` | `git rev-parse HEAD:code` |
| 判据词表（数据文件，唯一真源） | `tools/metrics/market_day_lexicon.json`，sha256 `8649d09e04ca6dc59d0cef153ea2a5b82b38e886eadc59868d4abe194a2c16d8`，版本 `market-day-lexicon/R-B-v1` | `sha256sum` |
| 读数器（只读，零 LLM） | `tools/metrics/market_day_readings.py`，sha256 `150c94487cbf2d42e16f7c128bd13fffa48aacc7ce904d3cf1ba8c5320c2b339` | `sha256sum` |
| 读数器自检 | `python3 tools/metrics/market_day_readings.py --selftest` → **12/12 passed**（基线判据，改坏即失败） | 实测 |
| 人工标注（基线 13 条真值，仅供对表/体检） | `tools/metrics/market_day_labels_baseline13.json`，sha256 `1337a9b1572a7d2b2788aad2d94d421235d8bb9a165d94558baf0701c06fdb77` | `sha256sum` |
| 对话指标器（不改） | `tools/d5/dialogue_metrics.py` sha256 `1d914735f3a13cf4e1640bd694f1d0e070096c9f50abfdefa7359417df551271` | `sha256sum` |
| 行为读数器（护栏用，不改） | `tools/habit/habit_readings.py` sha256 `c695fce4c2c5aa835c7ed526dbaf1e37bdc8d9fd8cf730a07b79a74d4de5560a` | `sha256sum` |
| 臂开关实现 | `code/life/market_day.py::MARKET_ENV="HITT_MARKET_DAY"`（`:42`）、`enabled()`（`:65`）、`render()`（`:102`）、`audit()`（`:118`）；接线 `code/life/agent.py::_market_line`（`:1645`） | `grep -n` |
| 插行位置（**硬约束**） | `agent.py:1880` 与 `:1882` 之间（实际插入行 `:1881`）、`:1903` 与 `:1905` 之间（实际插入行 `:1904`）（「处境块」内，`_weather_line` 之后、`rift_line` 之前；两处 prompt 位置对称） | `grep -n "_weather_line(wv)\|(rift_line or"` |
| 插行红线（**硬约束**） | **不得**插到 `narration_tail(...)`（`agent.py:1888` / `:1916`）之后；**不得**插在 `l7_struct_line` 与 `narration_tail` 之间（末段必须是收尾指令，有单测硬锁） | 同上 |
| 改动边界 | 只动 `code/life/`（+ `tools/metrics/`）；**不改** `code/config/`、`code/engine/`、`code/orchestration/`，**不改** `places.json::open_slots`（见 §2.3） | `git diff --name-only` |

---

## 1. 假设与构念（写死；措辞越界即无效）

### 1.1 构念名（全链路统一，禁止替换）

> **「集日提及 / 集日感知」**（market-day mention / awareness）
> **禁止**在任何位置（本件、报告、Leader 汇报、commit message）使用「赶集行为变多」「居民更爱赶集」「市场更热闹」这类**行为层**措辞。

### 1.2 H1 / H0

- **H1**：在**集日**回合，居民台词会把「今儿是集日」这一事实说出来（相对 OFF 臂，集日提及率上升）。
- **H0（实测基线，不是估计）**：未注入世界上的 R-B 命中率 = **4/1148 = 0.348%**，Wilson 95% = **[0.14%, 0.89%]**；**集日子集** = **3/591 = 0.508%**，Wilson 95% = [0.17%, 1.48%]。
  来源：本机 6 份真 LLM 语料（C28/C42/C43，共 1,148 条正文）以本件 §0 的词表与读数器回放，产物 `team-workspace/artifacts/evidence/baseline_replay_1148.{json,md}`。

### 1.3 预登记补偿（**OFF 臂期望值，写进报告第一屏**）

> **OFF 臂集日读数期望 0–3/208（≈0–1.4%）**。若 OFF 臂 ≥8/208，**先查污染**（见 §5 闸 E2），不得先报效应。

---

## 2. 两臂配置（单变量）

| 臂 | env | 其他 |
|---|---|---|
| **OFF** | **无** `HITT_MARKET_DAY` 行 | 其余 env 完全一致；边界条件：若 config 默认已开启，则 OFF 臂必须显式 `HITT_MARKET_DAY=0`（**写明是"未设"还是"设 0"，两者不得混用**） |
| **ON** | `HITT_MARKET_DAY=1` | 同上 |

- 开关真值取证：`/proc/<pid>/environ`（`switch_proof.txt`），**不接受**"启动命令里写了"。
- 两臂其余 env 必须逐字相同（`env_dump.txt` 可 diff）。

### 2.3 明确的单变量边界

- **集日只影响措辞，不影响可达性**：本臂不改 `places.json::open_slots`、不改 `activity_templates.json`、不改调度与结算。`市集` 在 OFF/ON 两臂均为 `open_slots=[morning,afternoon,evening]`。
- 因此**行为层（`PLACE_ARRIVED` 等）在本轮结构上不可能变**，其读数只作护栏（§4.3），**不得作为判据**，也**不得**把"行为没变"报告成"机制失败"。

---

## 3. 主判据 C-1（集日提及率）

### 3.1 定义（写死，逐字实现见 §0 读数器）

```
集日        := payload.day % 3 == 0            （every=3, offset=0，与机制必须一致）
分母 (n)    := 集日回合中 MSG_PUBLIC / MSG_DM / MSG_PRIVATE / MSG 且 payload.body 非空者
分子        := 上述中 market_day_hit(body) 为真者，其中
market_day_hit := R_B 命中（时间词与集市词双向邻接 ≤6 字、不跨 。！？； 与换行）
                  且 不含任何硬负例（idiom / price / echo / past-recall）
阈值        := Δ = ON率 − OFF率 ≥ +5.0pp
             且 两臂 Wilson 95% CI 不重叠
             且 **ON 臂绝对命中数 ≥ 8 条**（n≈208 时 8/208 = 3.8%）
```

- **口径出处**：`R_B` 的假阳性依据见 T1b 审计（原式 13 命中里 9 条假阳 = 69.2%；R_B 严格档在同样本 4 命中 0 假阳）。
- **R_C（原式 `赶集|逢集|集市|集上|摆摊|卖货|买(点|些|个)`）已否决**，只作召回探索；`买点/买些/买个/卖货` 已从判据层面整支剔除（读数器 `dropped_tokens` 会打印，防偷偷加回）。

### 3.2 分母口径（**本轮最容易翻车的一条，写死，禁止事后改**）

| 项 | 规定 |
|---|---|
| **主判据分母** | **消息条数**（r48·agents16 预期 **n = 208**） |
| **方差** | 按 **design effect DE = 1.5** 膨胀（有效 n_eff ≈ 139）；**DE=2.0 作敏感性上限**，两者都必须报 |
| **去重（(author, day) 单元）** | **只作附注 C-1b**，报「命中集中在 k/32 个居民-天单元」；**禁止**用作主判据分母 |
| 依据 | 去重当分母会把 n 从 208 降到 32，MDE 从 3.6pp 飙到 **20.7pp**，+10pp 直接不可达（T1c §3） |

### 3.3 极性

- 命中且含否定/缺席语义（`不|没|别 + 集市词` 或 `集市词 + 不|没 + 来|去|赶|摆|开`）⇒ 计入 `negated`，**单独计数并标反向**；报告必须两者同屏（阳性 / 否定），不得合并成一个数。

### 3.4 统计力（预先声明，防"事后发现没功效"）

| 项 | 值 |
|---|---|
| 预期集日样本 | n = **208**/臂（r48 = day0..3，实测逐日 98/93/103/110，集日 = day0+day3） |
| MDE（两比例 z，α=.05 双侧，power=.8） | **3.6pp**（DE=1）/ **5.4pp**（DE=1.5）/ 7.0pp（DE=2） |
| +10pp 的 power | **>0.97** |
| 基线 0/208 时 CI 不重叠门槛 | 最小 **k=8（3.8%）**（n=190 时 4.2%） |
| r24（n≈98）退化 | MDE **7.4pp**（DE=1）/ **10.7pp**（DE=1.5）⇒ r24 只够判"有/无提及"，**不得**用于 +5pp 判定 |

---

## 4. 探针与护栏（**成组报数，均不作主判据**）

| 编号 | 指标 | 角色 | 规则 |
|---|---|---|---|
| **C-2** | `R_A` 命中（`集日|逢三|赶集日|逢集日`） | 探针 | 未注入世界**结构性 0/1148**（实测）；ON > 0 即"注入被读到"。只报 `n/N` + Wilson，**禁止**写"提升" |
| **C-1b** | 去重单元命中 `k/32` | 集中度附注 | 若 `C-1` 判成立而命中集中在 ≤2 个单元 ⇒ 报告必须加一句"证据集中，外推受限" |
| **G-L7** | 8-gram 近重复率 `L-7_dup_ngram8_rate` | 护栏（硬） | `Δ > max(按实际分母重算的噪声带, 5.88pp)` ⇒ **判不通过** |
| **G-L2** | 旁白率代理 `L-2_narration_rate_proxy` | 护栏（硬） | `Δ > 5.88pp` ⇒ 判不通过 |
| **G-L13** | token 泄漏 `L-13_token_leak` | 护栏（硬） | `Δ > 5.0pp` ⇒ 判不通过（防把 `market_day` 之类内部 id 念出来） |
| **G-LEN** | 台词平均长度漂移 | 护栏（软） | `Δ > ±15%` ⇒ 不判不通过，但报告必须单列并解释 |
| **G-BEH** | `PLACE_ARRIVED{place=market}` 占比与按 day 分布 | 护栏（结构） | 基线 **11/121 = 9.1%；day0 5 / day1 6**（三份真跑批逐项相同）。**预期不变**；若 `|Δ| > 3pp` ⇒ 说明含第二变量，触发 §5 复核 |

---

## 5. 有效性闸（任一不过 ⇒ 本轮 `invalid`，**不得解释主判据**）

| 闸 | 判据 | 取法 |
|---|---|---|
| **E1 同源 + 差异受限 + 单变量**（§A1 修订） | OFF 臂 `HEAD:code` = `5c641e08…`；ON 臂 `HEAD:code` = `3039ed21…`；两臂代码差异**仅限** §0「改动边界」列出的文件（逐文件列出 + 附 `git diff --stat` 输出）；`env_dump.txt` 两臂只差 `HITT_MARKET_DAY` | `git rev-parse`；`git diff --stat <OFF-code-tree> <ON-code-tree>`；`diff env_dump` |
| **E2 无污染（OFF 哨兵）** | **OFF 臂集日 R_B < 8/208**；若 ≥8 ⇒ 停判，先查污染（词表/任务混臂/缓存回放） | 读数器 |
| **E3 注入到达（prompt 层，唯一硬性）** | ON 臂 **`ctx.market` 字段数 = 集日回合数**（逐条可数）；OFF 臂该字段**不出现**。**`R_A > 0` 不是必要条件**（`R_A` 只测「模型有没有用『逢三/集日』这类显式日历词」；模型完全可能用「今早集上」表达同一事实而 `R_A=0`）——见 §12 A1 | `run.jsonl` / 读数器 |
| **E4 机制不外溢** | **非集日子集**：两臂 R_B 命中相同（预期 0=0）且 MSG 条数量级一致（±5%） | 读数器 `nonmarket` 分列 |
| **E5 真 LLM + 串行** | `cd code && python3 -m obs llm-cost --log <臂>/run.jsonl --require-provider openai_compat` 通过、`degraded=0`；起跑前 `pgrep -f 'orchestration run|run_batch'` 为空；两臂**串行** | 门禁 + `preflight.sh` |

> E4 的"逐字节相同"不可强求（MSG 文本由 LLM 生成，即使不注入也可能因采样不同而不同）；故 E4 的执行口径是**命中数相同 + 分母同量级**，并在报告里如实说明"非集日两臂不是逐字节相同，而是结构等价"。

---

## 6. 规模、预算与 out-dir

| 参数 | 值 |
|---|---|
| `--agents` / `--rounds` / `--seed` / `--flush-every` | **16 / 48 / 42 / 2** |
| 两臂 | OFF、ON **各一次，串行** |
| out-dir | `v2/evidence/cycle44_market_off_n16r48_seed42` / `v2/evidence/cycle44_market_on_n16r48_seed42` |
| 预算 | 参照 n16r24 实测 1323–1352 s / 2,252 calls / 30.4 万 token ⇒ n16r48 ≈ **45 min/臂**，两臂 + 门禁 ≈ **100 min** |
| 读数产物 | `v2/evidence/cycle44_market_readings.{json,md}`（读数器直出） |

---

## 7. 不可外推声明与局限性（写死，报告必须照抄）

1. **单 seed（42）、单 provider、单机串行、16 agents × 4 天**；**无 seed 方差估计** ⇒ 不得断言"再跑必过/必不过"，不得把单点估计当稳定效应。
2. 只测「集日**提及**」这一代理构念；不得外推为「居民理解了日历」「生活气息更浓」「居民更会过日子」。
3. **行为层不变是本轮的预期结果**（prompt 与调度解耦，实测三份真跑批 `PLACE_ARRIVED` 逐项相同）；不得把"行为没变"写成"机制无效"。
4. 不得与 C28/C42/C43 的读数横比（代码树不同：本臂 `5c641e08`，历史语料 `51b43575`）。
5. **本轮不足以判定时，按「未达阈值」报告**（不许升格为"有效"，也不许降格为"机制无效"）；"不可分"必须给出点估计 + 两臂 Wilson CI + 分子/分母。
6. 若主判据命中为 0 ⇒ 只能写「注入未被台词采纳」，**不得**写「market-day 无效」。

---

## 8. 复算命令（第三方照抄；全部只读）

```bash
REPO=<repo 根>; cd "$REPO"
# 0) 词表/读数器自检（冻结证据）
sha256sum tools/metrics/market_day_lexicon.json tools/metrics/market_day_readings.py
python3 tools/metrics/market_day_readings.py --selftest          # 期望 12/12 passed

# 1) 起跑前串行闸
bash tools/d5/preflight.sh --tag c44-market

# 2) 两臂读数（主判据 + 集日/非集日分列 + 探针 + 去重附注）
python3 tools/metrics/market_day_readings.py \
  --arm off=v2/evidence/cycle44_market_off_n16r48_seed42/run.jsonl \
  --arm on =v2/evidence/cycle44_market_on_n16r48_seed42/run.jsonl \
  --json v2/evidence/cycle44_market_readings.json \
  --md   v2/evidence/cycle44_market_readings.md
#   期望：off 集日 ≈ 0–3/208；on 集日 视机制而定；R_A：off=0

# 3) 真跑验真（两臂各一次）
cd code && python3 -m obs llm-cost --log ../v2/evidence/cycle44_market_on_n16r48_seed42/run.jsonl \
  --require-provider openai_compat

# 4) 护栏
python3 tools/d5/dialogue_metrics.py --help     # 按既有用法取 L-7 / L-2 / L-13
python3 tools/habit/habit_readings.py --run OFF=… --run ON=… --out-json /tmp/c44_habit.json

# 5) 引用纪律（必须在仓库内，否则 FATAL rc=4）
scripts/check_citations.sh v2/refs/CYCLE-44-market-day-prereg.md --strict
```

---

## 9. 结论映射（写死，报告照抄，不得自创）

| 组合 | 结论文本 |
|---|---|
| `C-1` 成立（Δ≥+5pp 且 CI 不重叠 且 ON≥8 条）+ 护栏全在带 + E1–E5 全过 | 「market-day 在**文本侧**产生可复算的集日提及增量（`Δ=+x.xpp`，`a/208 → c/208`，DE=1.5 敏感性一致）；仅限 16×48×seed42 与『集日提及』构念，不外推生活气息。行为层按预期不变（`PLACE_ARRIVED` market 占比 `9.1% → y%`）。」 |
| `C-1` 未达阈值 | 「market-day **未**在文本侧产生可分辨的集日提及增量（`Δ=+x.xpp < +5.0pp`，ON 命中 `k/208`）；只能说明注入未渗透台词，**不说明机制无效**。」 |
| `C-1` 成立但任一护栏超带 | 「主判据上升但 `G-xx` 超带 ⇒ **净改善不成立（不通过）**。」 |
| CI 重叠 / 方向达标但绝对条数 <8 | 「**不可分**：本轮 n=208（DE=1.5 后 n_eff≈139，MDE≈5.4pp），不足以裁决；点估计 `Δ=+x.xpp`、两臂 CI `[…]` vs `[…]`。」 |
| E2 触发（OFF ≥8/208） | 「**invalid（疑似污染）**：OFF 臂集日命中 `k/208` 超哨兵线，本轮读数不得解释，须先查词表/混臂/缓存回放。」 |
| E3 不过（ON `ctx.market` 缺失，或数量 ≠ 集日回合数） | 「**invalid**：注入未到达提示词层（开关/接线未在位），本轮读数不得解释。」 |
| E3 过但文本零命中（`ctx.market` 齐全，而 `R_B=0` 且 `R_A=0`） | 「**注入下达但未被采纳**：`ctx.market` 逐条可数证明注入到达，`R_B/R_A=0` 说明模型未在台词中采纳该信息。这是**有价值的负结果**，按『未达阈值』报告，**不得判 invalid**，也不得反推『机制无效』（见 §12 A1）。」 |

---

## 10. Amendment 程序（防事后调参）

- 跑批**开始后**，本件 §3 的判据定义、词表/读数器 sha256、阈值、护栏、否决条、分母规则、DE 取值**一律冻结**。
- **允许**的改动只有三类：① 事实性勘误（sha/路径/行号）；② 跑批前写死的探针降级；③ 对上轮结论的勘误登记。三者都必须新增 `§A<n> Amendment` 段、写明理由与时间戳，并在报告里重报本件 sha256。
- **禁止**：看到读数后改词表 / 改分母 / 改阈值 / 把 probe 提成主判据 / 把"不可分"改写成"有效" / 把 DE 从 1.5 改大或改小以凑结论。

---

## 11. 三段 sha 链与状态

| 段 | 值（跑完填） |
|---|---|
| **① pre-reg commit sha**（本件入库提交，**必须早于起跑**） | `<待填>` @ `<ISO 时间>` |
| **② run sha** | OFF `run.jsonl` sha256 `<待填>` / ON `<待填>`；起手 `b3358fb`；`code/` 树 `5c641e08` |
| **③ report commit sha** | `<待填>` @ `<ISO 时间>` |

**时序可证**：用 **commit 锚**（`git log -1 --format='%h %ad' --date=iso -- v2/refs/CYCLE-44-market-day-prereg.md`）证明 pre-reg 提交时间 **早于** 两臂 `started_at`；**不得**使用文件 mtime（批量 checkout 会让 mtime 同值，CYCLE-43 已把这条写死）。

### 状态清单

- [ ] 代码接线（`code/life/market.py` + `agent.py::_market_line`，插行位置见 §0 硬约束）
- [ ] 单测（`code/life/tests/test_market_arm.py`：开关关 ⇒ 两条 prompt **逐字节不变**、`ctx.market` 不出现；开关开 ⇒ 只插一行 + `ctx.market` 快照；非集日 ⇒ 不插行）
- [ ] OFF 逐字节等价对拍（照 `tools/weather/off_equiv_prompts.py` 的做法）
- [ ] 读数器 + 词表 + 标注三件入库，sha256 填进 §0
- [ ] 本件 commit（**早于起跑**）
- [ ] 两臂串行跑批（r48·agents16·seed42）
- [ ] 读数（`market_day_readings.{json,md}`）+ 护栏 + 五道闸
- [ ] 报告 `reports/CYCLE-44-20261031.md`（撞号则加臂标）+ 三段 sha 并列

---

## 12. §A1 Amendment（2026-10-31 22:22 +0800，**跑批前**，Leader 裁决；属允许的第一类「事实性勘误/口径订正」）

> 触发：Leader 指出「E3 用 `R_A > 0` 作门槛，会把『注入到达但模型未采纳』误判为 invalid」。
> 本 Amendment 在**起跑前**写入，不触碰 §3 的任何判据、阈值与分母。

### 12.1 三层分离（写死；报告必须按三层分别报数）

| 层 | 量 | 证明什么 | 不过时怎么判 |
|---|---|---|---|
| **L1 注入到达（prompt 层）** | `ctx.market` 字段数 vs 集日回合数（逐条可数）；OFF 臂该字段不出现 | 开关与接线在位、注入确实进了提示词 | **唯一硬闸**：不过 ⇒ `invalid` |
| **L2 线索被读出（模型层，弱证据）** | `R_A` 命中数（显式日历词：集日 / 逢三 / 赶集日） | 模型至少有一次用了「日历词」 | 不过**不判 invalid**（`R_A` 只覆盖一种措辞） |
| **L3 线索被采纳（文本层，主判据）** | `R_B` 命中数（时间邻接档） | 台词里真的带出了「今天是集日」 | 不过 ⇒ 按 §9 判「未达阈值」 |

### 12.2 判读规则（写死）

- `L1` 过 + `L3` 不达 ⇒ 结论必须是 **「注入下达但未被采纳」**（负结果，有价值），并**必须**同屏给出
  `ctx.market` 条数、`R_A` 条数、`R_B` 条数与两臂 Wilson CI。
- **禁止**把这种情况写成：`invalid` / 「机制无效」/「market-day 无效」/「提升了」。
- `L1` 过 + `L3` 达 ⇒ 按 §9 第一行判成立（仍需 E2/E4/E5 与护栏全过）。
- `L1` 不过 ⇒ `invalid`，读数不解释。

### 12.3 与 §5 / §9 的关系

- §5 的 **E3 已改写为「注入到达（prompt 层）」**，`R_A > 0` 降级为 L2 探针（不再是否决项）；
- §9 **新增一行**映射「E3 过但文本零命中」；
- 其余闸（E1/E2/E4/E5）、判据（C-1）、阈值（+5.0pp / CI 不重叠 / ≥8 条）、分母（n=208 / DE=1.5）**一字未改**。
- 本 Amendment 生效后，报告须重报本文件 sha256（见 §0「本件自身 sha256」一行）。

---

## §A0 事实性勘误（占位填值时登记；**未改任何判据/阈值/分母/词表/三层映射**）

> 时点：2026-10-31 22:2x（预登记入库前，跑批未开始）。依 §10 允许的第 ① 类改动（事实性勘误：sha / 路径 / 行号）。

| # | 成稿原文 | 实测值 | 理由 |
|---|---|---|---|
| A0-1 | `code/life/market.py`（§0 臂开关实现行、§10 勾选项） | `code/life/market_day.py` | 实现文件按 `market_day` 命名（与 `weather.py` / `scene_anchor.py` 同组习惯）；**只改路径名，开关名 `HITT_MARKET_DAY`、判定规则、插行语义逐条不变**。 |
| A0-2 | 行号 `1837/1838`、`1859/1860`、`narration_tail 1844/1871` | `1880/1882`（插入 `:1881`）、`1903/1905`（插入 `:1904`）、`narration_tail 1888/1916` | 成稿行号取自旧树；本臂树（`b3358fb` + 本臂提交）实际行号如上。**插入语义要求（处境块内、`_weather_line` 之后 `rift_line` 之前、`narration_tail` 之前）不变**，且已由单测 `test_insert_position_locked_in_prompt_assembly` 硬锁。 |
| A0-3 | 占位 `<填>`（`dialogue_metrics.py` / `habit_readings.py` sha256）、`<feat/c44-market-day>` | 见 §0 表 | 占位填值，属预登记自身的既定动作，不是判据变更。 |
| A0-4 | 「本件自身 sha256」`<待填…>` | 归一化口径值见 §0（`sed 's/<值>/<SELF>/' … | sha256sum`），另以入库 commit sha 为第二锚 | 自指 sha 无法收敛（写入 sha 即改内容）；改用**可机械复算的归一化口径**，避免"填了一个算不出来的数"。 |

> **对 Leader 报备的不一致（未自行改动，等裁决）**：
> 1. §0「两臂 `code/` 树（两臂必须相同）= `5c641e08…`」与 §5 闸 V1 同款断言，和「ON 臂必须带本臂改动」**结构上互斥**（ON 臂 `HEAD:code` 必然 ≠ `5c641e08`）。建议裁决口径：OFF 臂 `code/` = `5c641e08…`、ON 臂 `code/` = 本臂分支树，并把 V1 改为「两臂 diff 只落在 §0『改动边界』列出的文件上」。
> 2. 落实 Leader 的三条实现约束（本件登记备查，均已在代码与单测中体现）：① `audit()` 只记 key + `line_sha256`、**不记人话**（照 `weather.py` 写法）；② OFF 臂 `ctx` 里**键不存在**（非空串）——单测 `test_off_prompt_and_ctx_untouched` 断言；③ 仪器隔离——`code/` 运行时**不得 import** `tools/metrics/*`，单测 `test_code_never_imports_judgment_instruments` 硬锁。

---

## §A1 Amendment（跑批前登记；**判据 / 阈值 / 分母 / 词表 / 三层映射一律未动**）

> 时点：2026-10-31 22:2x（两臂 `started_at` 之前，跑批未开始）。
> 依据 §10 允许的第 ① 类改动（**事实性勘误：sha / 路径 / 行号**）。触发者：Leader 22:24 裁决（采纳 §A0 第 1 条建议）。
> §A0 第 1 条的「待裁决」自本条起**已裁决并关闭**。

**A1-1 · §5 闸 E1 的可行性修订（原条件结构上不可能成立）**

- 原文：E1 = 「两臂 `git rev-parse HEAD:code` **相同且** = `5c641e08…`」。
- 问题：ON 臂必须携带本臂改动（`code/life/market_day.py` 新增、`agent.py` 接线）⇒ ON 臂 `HEAD:code` **在数学上必然** ≠ `5c641e08`。原条件**永远不可能满足**，等于把本轮判成必然 `invalid`；这是预登记的可行性缺陷，不是实验设计问题。
- 修订后（**更可机械验证，不是放水**）：

  > **E1（修订）**：OFF 臂 `HEAD:code` = `5c641e08…`；ON 臂 `HEAD:code` = `3039ed21…`；两臂代码差异**仅限** §0「改动边界」列出的文件，且**逐文件列出**并附 `git diff --stat` 输出；`env_dump.txt` 两臂只差 `HITT_MARKET_DAY`。

- 验证命令（校验员可一行复跑）：

  ```bash
  git rev-parse 5c641e080b24f03e82b28c837e73ca27fec15c03  # OFF 臂 code 树
  git rev-parse 3039ed21e5a2b74d595aab850e7adde34cbbffd0  # ON 臂 code 树
  git diff --stat 5c641e080b24f03e82b28c837e73ca27fec15c03 3039ed21e5a2b74d595aab850e7adde34cbbffd0
  # 实测（2026-10-31 22:2x，本臂树）name-status：
  #   M  life/agent.py                      +45
  #   A  life/market_day.py                 +128
  #   A  life/tests/test_market_day_arm.py  +404
  # ⇒ 3 files changed, 577 insertions(+)，全部落在 `code/life/` 之内（含其 tests/ 子目录），
  #   与 §0「改动边界」一致；`tools/metrics/*`、`v2/refs/*`、`tools/market_day/*` 落在 code/ 树之外，
  #   不进本 diff（其 sha256 另由 §0 逐件冻结）。
  ```
- **未动**：E2（OFF 哨兵 <8/208）、E3（L1 `ctx.market` 字段数 = 集日回合数）、E4（非集日不外溢）、E5（真 LLM + 串行）、§3 三层判据、§4 护栏阈值、§6 规模、§7 外推限制，**逐条字符未改**。

**A1-2 · 旁注（不构成判据变更）**：本臂 `HEAD:code = 3039ed21…` 对应分支 tip `b5d8d5b` 之前的功能提交 `ba823db` 之后的树；若 ON 臂起跑时分支再有新提交（例如本 Amendment 自身），`3039ed21` 需按起跑钉住的 commit 重新取值并在报告 §9 三段 sha 处如实并列。
