# CYCLE-14 报告独立复验（V1）核验结论

> **本文件含两版，按顺序读**：**第一版**（下至「V1 定点复验」小节之前）= 对 `25e0684b…33505` 的全量复验，结论 **BLOCK 1 项**；**第二版**（文末小节）= 作者改后的**定点复验**，对 `50874f2e…06253`，结论 **PASS-WITH-CAVEATS（0 BLOCK）＝终局**。第一版**原样保留、不删**（BLOCK 留痕是本轮可信度的关键）。

> **核验人**：`independent-verifier`（非作者）｜**核验时刻**：2026-10-24 04:2x (+08:00)
> **被验字节（唯一基准，落笔前请确认未再变）**：`reports/CYCLE-14-20261024.md`
> `sha256 = 25e0684bd4a180aab1f21a6ee9d2ed8a439357b70a924978b303bd92e5833505`（400 行，67,013 B）
> ⚠️ 作废旧值：`308f559f…8afb`（Leader 初审后有一次定点改动，见 `§4.3` 第 2 条括注）。**本结论只对 `25e0684b…` 生效**；若报告再变，本 PASS/BLOCK 不再对应新字节。
> **核验方式**：不采信报告自述，**逐项独立重跑**（`form_metrics.py` / `f1_recompute.py` / `d12i_dup_calibers.py` / `shape_gate.py` / `obs llm-cost` 全部我自己跑一遍到 `/tmp`，`--out` 一律不覆盖被核件）；`sha256sum` / `sha256sum -c` / PNG 像素自检均自行复算。
> **边界**：只读。未改 `code/`、未改 `reports/`、未 commit/push、未起跑批、未改任何被核文件字节。

---

## 结论分档：**BLOCK（1 项定点修正，其余全部可复算）**

**一句话**：报告 7 类核查项中 6 类通过、全部关键读数（F-1 六臂 / L-3 / addr_head 双口径 / L-7 双口径 / 成本 / 过程闸三时点 / refs 空态 / §3 十五行）**我逐条重算后与报告完全一致**，但 **§0 与 §4.1 的一句话结论里有一处数字错**（三臂 F-1「极差 ≤0.59pp」实为 **0.78pp / 4 条消息**），该句出现 3 次且位于最显眼位置 ⇒ **修正后可发布，修正前不发布**。

- BLOCK 数：**1**（仅此一条；修 3 处同句复制，不改任何结论与数据）
- 证据存在性：报告引用路径 **抽核 23 条，22 条存在**（1 条路径写法不精确：`config/personas.json` 实为 `code/config/personas.json`）
- sha 一致性：**抽样 20 件全部一致**（含 18 项 `SHA256SUMS` 全 OK + F-1 四件 + `S_ext` + `d12i_result.md` + receipt + `dialogue_metrics.py`）
- 截图：4 张**确为真渲染**，像素自检我独立复算逐项吻合；**spread 空态描述属实**（且与 `refs=0` 独立互证）
- §3：**15/15 行、顺序一致、六列逐字相同**（相似度 1.000），无漏行、无篡改

---

## 一、抽样重算（19 项，覆盖报告每一节）｜报告值 vs 我重算值

| # | 项（口径名带后缀） | 报告值 | 我重算值 | 一致 | 我的复算方式 |
|---|---|---|---|---|---|
| 1 | **L-3 旁白率** `L-3_paren_block_any` | 369/510 = 72.3529% | **369/510 = 0.723529** | ✅ | 自跑 `form_metrics.py --log D12-I --code-dir .worktrees/d12i-aligned/code --out /tmp/v_form.json` |
| 2 | **`addr_head_pfx2`** | 116/510 = 22.7451% | **116/510 = 0.22745098** | ✅ | 同上（`--triage` 无关，默认口径） |
| 3 | **`addr_head_strict_personas20`** | 134/510 = 26.2745% | **134/510 = 0.26274510** | ✅ | 同上（form_metrics `addr_head_strict` 字段 = 20 个 display_name 起头；`code/config/personas.json` 实有 **20** 个 `青溪镇·*`） |
| 4 | `addr_head_loose` | 144/510 = 28.2353% | **144/510** | ✅ | 同上 |
| 5 | `addr_head_pfx2_plus` / `addr_head_alias` | 116 / 0 | **116 / 0** | ✅ | 同上（本批 plainly 与 pfx2 同值） |
| 6 | **L-7 `norm8`** `L-7_dup_ngram8_rate` | 317/510 = 62.1569% | **317/510 = 0.621569** | ✅ | 自跑 `form_metrics.py`；与 `d12i_dup_calibers.py` 的 `norm8_shingle` 317 交叉一致 |
| 7 | **L-7 `raw8`** `raw8_shingle` | 368/510 = 72.1569% | **368/510 = 0.721569** | ✅ | 自跑 `d12i_dup_calibers.py --out /tmp/v_dup.json` |
| 8 | 两口径差 | 51 条消息 / 10.0pp | **368−317 = 51 条 / 10.00pp** | ✅ | 算术 |
| 9 | `dup_raw_exact` / `dup_norm_exact` | 47/510 = 9.2157% | **47/510 两口径同值** | ✅ | 自跑同上 |
| 10 | **F-1 分子/分母（D12-I）** | 363/510 = 71.1765%，功能性 147 | **363/510 = 0.711765，功能性 147** | ✅ | 自跑 `f1_recompute.py`（6 臂）→ `/tmp/v_f1.json` |
| 11 | F-1 参照臂 T5 / D12-H | 364/510、360/510 | **364/510、360/510** | ✅ | 同上 |
| 12 | F-1 分母不同源三臂 | 187 / 686 / 124 | **187 / 686 / 124** | ✅ | 同上（三臂均复算成功，未做差） |
| 13 | **成本 provider 计数 / degraded** | `openai_compat 4200`、`degraded 0` | **`{'openai_compat': 4200}`、`degraded 0`、`cached 1583`、`thinking 668`、`tokens_total 880179`、`rc=0`** | ✅ | 自跑 `cd code && python3 -m obs llm-cost --log <D12-I run.jsonl> --require-provider openai_compat` |
| 14 | 成本分用途 calls | dialogue 1832 / importance 1523 / judge 668 / reflect 112 / negotiation 49 / plan 16 | **完全一致，合计 4200** | ✅ | 同上 |
| 15 | **过程闸 `<20`**：F2 `addr_head` drift | `0.264368`，−10.03pp PASS | **0.26436782，drift = −10.0332pp，verdict PASS** | ✅ | 自跑 `shape_gate.py --points 20,30,60 --out /tmp/v_gate.json` |
| 16 | 过程闸 `<30` / `<60`：F2 drift | −13.30pp / −13.72pp | **−13.2993 / −13.7249** | ✅ | 同上 |
| 17 | 过程闸 F1 / F3 三时点 | +3.08 / +10.05 / +14.51pp；56.0(+5.66%) / 59.0(+11.32% FAIL) / 55.0(+3.77%) | **+3.0795 / +10.0462 / +14.5129；0.056604 / 0.113208 / 0.037736** | ✅ | 同上 |
| 18 | 收尾闸 `id_leak_rate` / `dup_exact_rate` | 0.003922 / 0.092157 | **0.00392157 / 0.09215686** | ✅ | 读 `shape_gate_full.json` + 与 §2.3 `dup_raw_exact` 交叉一致 |
| 19 | 二维标定 L-3 三点 | 72.3529 / 57.8431 / 0.1961% | **369/510、295/510、1/510** | ✅ | 读 `t5_form_metrics.json` / `d12h_form_metrics.json` 的 `L-3_paren_block_any` 分子分母 |

**另核（非数字但可复算）**
- **日志身份**：`sha256 = 72c0ca97…8f5d0c4`、**117,724 行**、**58,438,033 B** —— 我自己 `sha256sum`/`wc -l`/`stat` 三项实测，与报告与 `meta.json` 三方一致；`run_batch.rc = 0`；worktree `feat/d12i-aligned` HEAD `a323e28`（报告称「收批后前进 3 个 commit」属实）。
- **meta 五项对账**：`code_sha ca76ceb2…`、`llm_calls 4200`、`llm_cached 1583`、`degraded_calls 0`、`provider openai_compat`、`fallback_detected false` —— 报告 §2.5「✅ 五项」属实。
- **commit 区间**：`git rev-list --count 899b89a..d0a320b` = **12**；逐条列表与报告 §1.1 完全一致，其中本期入库 **7 条**（`f89e516/046e34f/38de6d4/5755e10/6b4e452/97298d1/d0a320b`），跨周期 **5 条** —— 与报告分类一致。
- **F-1 分解 129/147 = 87.8%**：`f1_readings.json::decomposition.tag_hit_msgs = 129`、`functional_msgs = 147`；三臂 tag 通道 `counter_propose 41 / polite_reject 35 / scarce_buy 53` 与报告逐项相同。
- **`refs` 空态**：`threads_D12-I.json` → `0 0 0 0`；日志侧 `510 0` —— 两路我都实跑，与报告 §2.6.1 一致。
- **脏行数**：现 `git status --porcelain | wc -l` = **27**，与报告「落笔前 25 / 落笔后 27」自洽（时点快照）。

---

## 二、口径混用专项（4 类：**全部通过**）

| 类 | 报告是否互换/单选/未标 | 判定 | 依据 |
|---|---|---|---|
| **pfx2 / strict** | 未互换：`addr_head_pfx2`（116/510）与 `addr_head_strict_personas20`（134/510）**始终并列双写并标「差 3.53pp / 18 条消息，不得互代」**（§2.3、§4.3 限定语、§0 引用硬约束①） | ✅ PASS | 我重算两值 116 / 134，差 18 条 = 3.5294pp |
| **raw8 / norm8** | 未互换：`L-7_dup_ngram8_rate（norm8）` 与 `L-7_raw8_shingle（raw8）` 并列、各带后缀，明写「跨批不可比」「差 51 条，不得互代」 | ✅ PASS | 我重算 317 / 368，差 51 条 |
| **any / 起头** | 未互换：`L-3_paren_block_any`（369，「命中任一括号块」）与 `paren_head_rate`（338，「**起头**口径，参照」）并列，明写「相近但不同，不得互换」 | ✅ PASS | `paren_head_rate` 我未在 `form_metrics` 侧重算（该字段不在 form_metrics 输出里），但在 `shape_gate_points.json` <60 行读到 `paren_head_rate = 0.6627451 = 338/510`，与报告一致 |
| **upper / loose** | 未互换：`addr_head_loose`（144/510，上界参照）与 `addr_head_upper_rate`（收尾 0.2353，仅参照）分列；§3 `Q-27` 明写 upper 默认值 `0.41` 与实算 `0.3804` 不等 | ✅ PASS（附 1 caveat） | 报告未把 `0.41` 当成 T5 的 loose 基线用于任何判定；caveat 见 §八 |

**额外确认**：§2.4 形态闸表的 `addr_head` 列**主动标注「实际为 pfx2 口径」**，并说明 `shape_gate` 侧字段历史名 = `addr_head_strict`（`N-1`）——这是本报告最容易被误读的一处，报告**做对了**（正文与结论里凡引 F2 一律落到 pfx2，并把 strict 口径下的另一个量用 `_personas20` 后缀区分）。

---

## 三、越界专项（**通过**，1 处留给 Leader 定调）

| 检查点 | 结果 | 证据 |
|---|---|---|
| 是否把**过程闸读数写成批次判定** | ✅ 未写。§2.4 三条「口径性质声明」明写「本表是过程闸读数，**不是**本批效果判读；`PASS`/`FAIL` 只是该闸自身越界标记；本批判定已由 `d12i_result.md` 给出，本报告不另出判定」；§4.1 第 10 行状态词 = `部分读数(partial)` | 报告 §2.4 / §4.1 |
| 是否出现「改善 / 提升 / 效果 / 显著 / 优于 / 拉高 / 变好」类词 | ✅ **零命中**。我 grep 了 `改善 提升 显著 优于 效果好 拉高 降低了 变好 更高 更低 涨 跌` → 全部 0 次；`机制生效`（3 次）/`机制未生效`（4 次）/`成功`（2 次）均为**否定式或陈述式**（「本周期不适用」「不得写成渲染失败…页面是真渲染成功的」） | 我的 grep 实测 |
| 是否把**机制接通写成效果结论** | ✅ 未写。`S_ext` 入主树只说「文件已在主树、指纹一致」，明写「**不能写** `N-4` 已收口」；`N-7` 只写「限定语已落位」，明写「不能写已可从零重建」 | §3.1 表 |
| 是否把**不可比三臂百分数并排暗示趋势** | ✅ 未写。§2.1 明写「把三臂 F-1 并排读成『趋势』属越界」，三条不同源分母臂（187/686/124）全部标 `不可判（不得做差）`；§2.2 三维并排**都带同一分母 510 的说明**并标「这是描述，不是效果判定」 | §2.1 / §2.2 |
| **一处留给 Leader 定调** | ⚠️ **PASS-WITH-CAVEATS**：§0 / §4.1#1 / §4.2 第二句里「**生活气息层没有被推动**」是**结论式表述**，其依据是标为 `不可判` 的 F-1 无位移。Leader 已定调为原文口径、且同句带 `描述性读数`+`不可判`，故**我不判 BLOCK**；但该句式在对外引用（简报 / README）单摘时极易被读成效果判定 ⇒ 建议引用时**必须同屏带「F-1 差值 `不可判`」** | §0 L24 / §4.1 L302 / §4.2 L320 |

---

## 四、证据存在性（路径 **22/23 存在**；sha 抽样 **20/20 一致**；4 张截图 **真渲染**）

**① `sha256sum -c` 自跑**
- `v2/evidence/d12i_readings_20261024/SHA256SUMS` → **18/18 OK**（含 4 PNG、`render.log`、`render_report_D12-I.json`、`threads_D12-I.json`、`../d12i_external_shingles_4gram.json`）
- `v2/evidence/life_texture_cycle14/SHA256SUMS` → **4/4 OK**（该目录 4 个数据件 + `SHA256SUMS` 自身 = 报告所称「五件」）

**② 报告正文引用的完整 sha，我逐件实测（20 件，全部一致）**

| 件 | 报告值（前 12 位） | 实测 | 一致 |
|---|---|---|---|
| `form_metrics_full.json` | `2e7213dc…f7a` | `2e7213dc0045c06c…dadf7a` | ✅ |
| `dup_calibers.json` | `f41be81e…728e` | `f41be81eedf16c9a…d3a7728e` | ✅ |
| `selector_stats_full.json` | `a30ec856…c1e` | `a30ec8566c4cb1cd…dd72c1e` | ✅ |
| `llm_cost.txt` | `76a68ed0…7830` | `76a68ed0…797830` | ✅ |
| `llm_cost.rc` | `9a271f2a…86aa` | `9a271f2a…3ab86aa` | ✅ |
| `threads_D12-I.json` | `312c4d7c…1655` | 同 | ✅ |
| `render_report_D12-I.json` | `0e345dba…d8a6` | 同 | ✅ |
| `render.log` | `1c86e304…1755` | 同 | ✅ |
| 4 张 PNG（`chat/rhythm/spread/chat_thread`） | `d4883c43…` / `2c942d85…` / `9f0a6bd6…` / `f14fbe84…` | 四张全部一致 | ✅ |
| `f1_readings.json` / `.md` / `f1_recompute.py` / `f1_report_insert.md` | `a46ace5e…16ed` / `c795cfd0…b77f2` / `fc118ff2…1e01` / `9be79f42…2d66` | 四件全部一致 | ✅ |
| `life_texture_cycle14/SHA256SUMS` | `e8926f04…3b46` | 同 | ✅ |
| `d12i_external_shingles_4gram.json`（`S_ext`） | `f75ebb3e…0a1e12f0` | 同（408,250 B 亦一致） | ✅ |
| `d12i_result.md` | `e869267e…eda4` | 同 | ✅ |
| `d12i_receipt_README.md` | `7b6fb527…1431` | 同 | ✅ |
| `tools/d5/dialogue_metrics.py`（尺子） | `1d914735…1271` | 同 | ✅ |
| 团队共享区 `cycle14-issue-register.md` / `cycle14-state-brief.md` | `47cb0cea…34c0` / `2b86ca17…aa7b` | 两件均一致 | ✅ |

**③ 路径存在性**：抽核 23 条引用路径（`reports/CYCLE-13…`、`v2/00-anchor.md`、`v2/evidence/d12i_result.md`、`d12i_leader_terminal_check.md`、`t361-post-unfreeze-todo.md`、`T374/T376` 两件、`v2/refs/D12I-prereg-aligned-objective.md`、`d12h_verdict_amendment3.md`、`d12i_receipt_README.md`、`t5/d12h_form_metrics.json`、`tools/d12h/shape_gate.py`、`tools/d9/arm_state_check.py`、`code/frontend/tools/shot.py`、四份 `run.jsonl`、两个新工具…）→ **22 存在、1 不存在**：`config/personas.json`（实为 `code/config/personas.json`，仓根无 `config/`）。**属路径写法不精确、非证据缺失**（`code/config/personas.json` 实有 20 个 `青溪镇·*` display_name，与「20 个」一致）。

**④ 4 张截图是否真渲染 + 是否空白（我自己复算像素，不看自检）**

| 图 | 尺寸 | 色数（我算 vs 报告） | 最大单色占比 | 判定 |
|---|---|---|---|---|
| `D12-I-chat` | 1400×900 | 24,216 vs 24,216 ✅ | 14.17% vs 14.17% ✅ | 非空白 |
| `D12-I-rhythm` | 1300×1050 | 22,315 vs 22,315 ✅ | 26.20% vs 26.20% ✅ | 非空白 |
| `D12-I-spread` | 1400×1000 | 15,623 vs 15,623 ✅ | 56.83% vs 56.83% ✅ | 非空白（**空态**，见下） |
| `D12-I-chat_thread` | 1200×1000 | 24,951 vs 24,951 ✅ | 11.07% vs 11.07% ✅ | 非空白 |

`render.log` 四条 `SHOT OK`、`blank_retries=0/2`、`--no-blank-check` 显式绕过（对应 `Q-20` 假红）；`render_report` `ok_count=4 / fail_count=0`。**「真渲染」成立**。

**⑤ spread 空态是否被如实描述 —— 属实**：报告写「本批为空态」「`描述性读数（空态）`」「**不得写成渲染失败**（页面是真渲染成功的）」；我的独立互证：`threads_D12-I.json` → `ref_edges/echoes/stats.ref_edges/echo_groups = 0 0 0 0`，日志侧带非空 `refs` 的 MSG = `0/510`，且 spread PNG 像素 `top_color_frac = 56.83% / non_bg = 17.70%`（内容稀疏但确实渲染出框架与显式空态卡片）⇒ **「渲染成功但数据空态」这一描述与我复算一致，既不写成失败也不写成有内容**。

---

## 五、截图口径（**通过**）

- **「终态回放」写明**：§2.6「时点口径（四张同）：**终态回放**（`still=1`，已收批 `rc=0`、日志 sha 与 meta 三方一致），**不是运行中快照**；页面底部进度 `510 / 510`」 —— ✅ 四张同口径，且我核 `render.log` 的 URL 确含 `still=1`。
- **「PNG 非逐位确定」写明**：§2.6「两条残留限制」① 明写同一链路首轮 `chat = 7cf10530…`、`rhythm = 09142166…`，第二/三轮才为 `d4883c43…` / `2c942d85…`，`spread` 三轮一致 ⇒ **指纹以 `render_report` 与 `SHA256SUMS` 为准，重跑可能出不同 sha 的等价图**；② 四张图**均不参与任何判据**（展示材料）。✅ 两条都在，且与 `Q-20` 建议第 6 条（回归不能按逐字节）自洽。
- **一处口径未标（caveat）**：表列「**非背景**」占比（58.20 / 47.43 / 17.70 / 53.17%）**未写定义**。脚本里 `non_bg_frac` = 「与最常见色曼哈顿距离 >24 的像素占比」（`tools/metrics/render_shots.py:93`）；我按此定义复算得 **0.582 / 0.4743 / 0.177 / 0.5317**，与表值**一致**；但若按字面「1 − 最大单色占比」复算会得 85.83% / 88.93% / 73.80% / 43.17%（**不同数**）⇒ 按本团队「口径必须带名」纪律，**建议补一句定义**（不阻塞）。

---

## 六、六元组完备性（抽查 6 行）

判据形态：数值 + 分母 + 口径名 + 来源路径 + sha + 证据状态。

| 抽查行 | 数值 | 分母 | 口径名 | 来源路径 | sha | 证据状态 | 判定 |
|---|---|---|---|---|---|---|---|
| §2.1 D12-I F-1 行 | 0.711765 | 510 | `F-1_chatter.nonfunctional_chatter_rate`（节首给全名+s 尺子 sha） | `.worktrees/d12i-aligned/.../run.jsonl` | `72c0ca97fe6e`（**仅 12 位前缀**） | `已验证` | ✅（sha 前缀可定位，完整值在 `f1_readings.json`） |
| §2.3 `L-3_paren_block_any` 行 | 0.723529 | 510 | ✅ 带后缀 | 节首 `form_metrics_full.json` | 节首 `2e7213dc…f7a` | `已验证（sha）` | ✅（路径/sha 在节首而非行内，可回溯） |
| §2.3 `addr_head_pfx2` 行 | 0.227451 | 510 | ✅ 带后缀 + 标「下界参照」 | 同上 | 同上 | `已验证（sha）` | ✅ |
| §2.3 `L-7_raw8_shingle` 行 | 0.721569 | 510 | ✅（raw8） | 节首 `dup_calibers.json` | 节首 `f41be81e…728e` | `已验证（sha）` | ✅ |
| §2.4 `<60` 过程闸行 | 0.723529（+14.51pp FAIL） | 510（`n_bodies`） | ✅（F1/F2/F3 列名+「实际为 pfx2 口径」） | 节首 `shape_gate_points.json` | 节首 `6820ef48…d47d` | **行内无状态列**（状态在 §4.1#10 = `部分读数(partial)`） | ⚠️ PWC（见 §八） |
| §2.5 成本行 | 4200 calls / degraded 0 | 调用数（分母 = calls 本身） | ✅（`engine_log.total` / `provider_guard`） | `llm_cost.txt` / `llm_cost.rc` | `76a68ed0…` / `9a271f2a…` | `已验证` | ✅ |

另一行 `§2.6.1 refs 空态` 亦带「0/510 + 分母 510 + 指标名 `ref_edges/echoes` + `threads_D12-I.json` + `312c4d7c…` + `已验证`」—— **六项齐**。

**小结**：6 行抽查 **4 行严格六元组齐备、2 行缺项已定位**（§2.4 行内无证据状态列；§2.1 sha 只 12 位）。两者均可回溯、不影响可复算，**属 PWC 不属 BLOCK**。

---

## 七、§3 未收口项 vs `cycle14-issue-register.md`（**完全一致**）

- 登记表现 sha = `47cb0ceac35bf2079cca5f34a345c0118de779a5fadf162494ac849bd19934c0`（我实测），与报告 §3 声明的 sha **一致**；登记表数据行 = **15 行**。
- 程序化对表（逐行提取六列文本做相似度）：**15/15 行存在、顺序一致**，`N-4 / Q-17 / N-1 / N-6 / Q-27 / N-2 / N-3 / N-5 / Q-22 / Q-24 / Q-21 / Q-20（残留）/ T361 / T374 / N-7` —— 「一句话事实」列相似度 **1.000（15/15）**，「事实+证据+领域+处置+建议」五列合并相似度 **1.000（15/15）** ⇒ **无漏行、无删改措辞、无软化成 `不可判`**。
- 报告额外声明两条我核了属实：① 任务卡「14 行」已过期、现为 15 行（多出 `N-7`）；② `N-2` 按 Leader 04:10 `A-lite` 执行（活跃引用用 `d4a9e787…814dd`、CYCLE-13 正文不改、旧值 `394997e2…` 仅出现在「作废」语境）—— 报告 §1.1 提及 `8fa7517` 时确实未引该旧 sha。

---

## 八、BLOCK 清单（1 条：**哪一句不能发布 + 改成什么**）

### BLOCK-1（数字错，出现在 3 处同句复制）

- **不能发布的原句**（3 处，逐字相同）：
  - §0 第 24 行：`闲聊轴（F-1）无位移（71.18% / 71.37% / 70.59%，CI 重叠、差值 ≤0.59pp ⇒ 不可判）`
  - §4.1 第 1 行（L302）：`…无位移（71.18% / 71.37% / 70.59%，CI 重叠、差值 ≤0.59pp）…`
  - §2.2 描述性读数第 1 条（L154）：`三点纵坐标差 ≤0.59pp（≤3 条消息），Wilson95 两两重叠 ⇒ 不可判（无差异）`
- **为什么错**：`≤0.59pp` 只对**含 D12-I 的两个配对**成立（D12-I↔T5 = −1 条 = 0.196pp；D12-I↔D12-H = +3 条 = 0.588pp）。第三对 **T5↔D12-H = 4 条 = 0.784pp**，**三点极差 = 0.7843pp / 4 条消息**。我按 `363/510、364/510、360/510` 重算，`(364−360)/510 = 0.7843pp`。⇒ 「三点差 ≤0.59pp（≤3 条消息）」**在自身三点上不成立**（`≤0.78pp` / `≤4 条消息` 才成立）。
- **改成什么**（二选一，推荐 A）：
  - **A（最小改动，保留原结论）**：把「差值 ≤0.59pp（≤3 条消息）」改成 **「D12-I 与另两臂差值 ≤0.59pp（≤3 条消息）；三臂两两差 ≤0.78pp（≤4 条消息）」**，§2.2 的「三点纵坐标差」改为「**三臂两两差**」。
  - **B（更保守）**：改成 **「三臂两两差 ≤0.78pp（≤4 条消息）」**，并把「差值 ≤0.59pp」整句删除。
  - §2.1 可比性裁决表（−1 条 / +3 条）**无需改**，本就只写配对差。
- **不影响结论的理由（供 Leader 判断是否可「先发布后修」）**：`不可判` 的依据是 **Wilson95 两两重叠**（我核：D12-I `[0.670987,0.749376]`、T5 `[0.673012,0.751244]`、D12-H `[0.664916,0.743770]`，**三对全部重叠**）——`0.78pp` 与 `0.59pp` 都远小于可分辨区，**结论方向不变**。故这是**措辞/数字精度的错，不是结论的错**；但因为它出现在「一句话结论」里且被复制 3 次，**必须改完再发布**。

---

## 九、PASS-WITH-CAVEATS 清单（不阻塞发布，建议同批修）

| # | 位置 | 情况 | 建议 |
|---|---|---|---|
| C-1 | §0 L24 / §4.1 L302 / §4.2 L320 | 「生活气息层没有被推动」为结论式表述，依据是标的 `不可判` 读数（Leader 已定调授权） | 对外引用（简报/README）时**必须同屏带「F-1 差值 `不可判`」**，不单独摘句 |
| C-2 | §2.6 表「非背景」列 | 口径未标定义（脚本 = 与最常见色曼哈顿距离 >24 的占比）；按字面算法会得另一组数 | 表下加一句定义 + 指向 `render_shots.py:93`（我按其定义复算与表值一致） |
| C-3 | §2.3 / §2.4 表 | 来源路径与 sha 在**节首**统一给、行内不给；§2.4 行内无证据状态列 | 可接受（可回溯）；若后续要机读，建议行内补 `source_sha256` 字段 |
| C-4 | §2.1 表 | 日志 sha 只写 12 位前缀 | 建议行内写全 64 位（或标注「完整值见 `f1_readings.json`」，报告已有类比） |
| C-5 | §2.3「20 个 `config/personas.json::display_name`」 | 仓根无 `config/`，实际是 `code/config/personas.json`（20 个 `青溪镇·*` 实测） | 补 `code/` 前缀 |
| C-6 | `dup_calibers.json` | 落盘件含 `checks` 字段，但我用报告给的命令现跑**产出无该字段**（数值/口径/结论全一致） | 说明该 `checks` 段是生成后补写的；建议工具补上该字段，或报告中不引用该段作为复算证据 |
| C-7 | §3 `Q-27` 行（抄登记表） | 表内同时出现 `0.41`（旧默认）与 `0.3804`（实算），未标「`0.41` 是作废值」 | 建议在报告里加一句「`0.41` 为待改默认值、非基线读数」，避免读者误取 |

---

## 十、无法核 / 不可复算项（如实列，不用推断补位）

1. **落笔时刻 `2026-10-24 04:12:57` 与脏行数 `25`（落笔前）**：时点快照，事后不可重建。我实测当下为 **27 行**（与报告「落笔后 27」自洽），**不判错**，但这两个值本身不可复算——报告已自行标注「不构成判据」，我认可。
2. **「PNG 重跑会得到不同 sha 的等价图」**：我只核了**本次** 4 张 PNG 与 `render_report`/`SHA256SUMS` 一致、且非空白；**未重跑渲染**（重跑会起静态服务并写文件，违反只读边界，且逐位不确定使「重跑求同图」本身无判据意义）⇒ 报告所述「首轮 sha = `7cf10530…`/`09142166…`」我**无法核**，只作记录。
3. **`hot` 之外的跨周期历史结论**（如 CYCLE-13 是否已过 V1）：报告 §5 声明「至今无落盘结论、`[文档]`」——我按只读边界未追溯，**未核**（报告已如实标 `[文档]`，不算越界）。
4. **§2.6「图上能看见什么」的视觉描述**（如「可见 5 天 × 4 时段热力网格」「枣泥酥 / 刨木条」）：我只做了像素统计与 `threads_D12-I.json` 结构核，**未做逐图像素级语义核对**（不做主观判读，属越界）；但从 `non_bg/top_color` 与线程结构看与描述不矛盾。
5. **`S_ext` 的 `content_sha256 = 16754109…46c`**（登记表 `[文档]` 引用）：该值指文件内部字段而非 file sha，我核了 **file sha = `f75ebb3e…0a1e12f0` 与判读件一致**，内部 content_sha 字段**未逐字核**（未打开 408KB 文件比对内部字段与重算值）。

---

## 附：本次核验跑过的命令（可原样重放，全部只读、输出落 `/tmp`）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
# 报告身份（必须先固定）
sha256sum reports/CYCLE-14-20261024.md reports/README.md ; wc -l reports/CYCLE-14-20261024.md
# 日志身份三件
sha256sum .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl
wc -l <  .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl
stat -c%s .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl
# 形态读数（V1 独立重跑）
python3 tools/metrics/form_metrics.py --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --code-dir .worktrees/d12i-aligned/code --out /tmp/v_form.json --batch-id D12-I-VERIFY --seed 42 --n 16
# 重复度四口径
python3 tools/metrics/d12i_dup_calibers.py --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl --out /tmp/v_dup.json
# F-1 六臂
python3 v2/evidence/life_texture_cycle14/f1_recompute.py --arm D12-I=.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --arm T5=.worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42/run.jsonl \
  --arm D12-H=.worktrees/d12h-pairing/v2/evidence/run_d12h_pairing_n16r60_seed42/run.jsonl \
  --arm v0-anchor=v2/evidence/run_d2_before_n16_seed42/run.jsonl --arm A0=v2/evidence/run_d2_after_n16_seed42/run.jsonl \
  --arm A1-措辞=v2/evidence/run_a1_wording_n4r60_seed42/run.jsonl --out-json /tmp/v_f1.json
# 过程闸三时点
python3 tools/d12h/shape_gate.py --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --code-dir .worktrees/d12i-aligned/code --points 20,30,60 --out /tmp/v_gate.json
# 成本验真
cd code && python3 -m obs llm-cost --log "$(pwd)/../.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl" \
  --require-provider openai_compat ; echo rc=$?
# 证据完整性
(cd v2/evidence/d12i_readings_20261024 && sha256sum -c SHA256SUMS)
(cd v2/evidence/life_texture_cycle14  && sha256sum -c SHA256SUMS)
# refs 空态两路
python3 -c "import json;d=json.load(open('v2/evidence/d12i_readings_20261024/shots/threads_D12-I.json'));print(len(d['spread']['ref_edges']),len(d['spread']['echoes']),d['stats']['ref_edges'],d['stats']['echo_groups'])"
```

---

*核验：`independent-verifier`（非作者）｜被验字节 `25e0684b…33505`｜主树 HEAD `d0a320b`｜本文件只读核验结论，未修改任何被核文件*

---
---

# V1 定点复验（第二版）——终局结论

> **被验字节（终局基准）**：`reports/CYCLE-14-20261024.md`
> `sha256 = 50874f2e59380b960ddc2b63a0e4210381e95cf8527ffc1ec67e0030ce706253`（**407 行 / 68,543 B**）
> 上一版 `25e0684b…33505` **作废**；`reports/README.md` 我实测 = `e17085ed24cb2b688b03cdc4a7a36bc9ec9654757167198415f892964683073f`（**未动**，与作者/Leader 所述一致）。
> **范围**：只做**定点复验**（Leader 04:23 裁定）——不重跑第一版的 19 项读数（已核过，作者声明未动数据层，且我 grep 确认无数据行改动）。

## 终局分档：**PASS-WITH-CAVEATS（新增 BLOCK = 0）**

第一版 BLOCK-1 的 3 处数字**已全部按建议句式改正、无旧措辞残留**；Leader 裁定的 PWC ①–⑦ **七条全部落地**；结论状态词**一个未变**。⇒ **可放行提交**，无需再改；剩余 3 条均为「引用纪律」级提示（不阻塞）。

## 二-1. BLOCK-1 闭合核（逐处 grep 语境）

| 落点 | 现文（实测） | 判定 |
|---|---|---|
| §0 **L24** | `…CI 重叠；D12-I 与另两臂差值 ≤0.59pp（≤3 条消息）；**三臂两两差 ≤0.78pp（≤4 条消息）** ⇒ `不可判`…` | ✅ 正确 |
| §2.2 **L154** | `D12-I 与另两臂差值 ≤0.59pp（≤3 条消息）；**三臂两两差 ≤0.78pp（≤4 条消息）**，Wilson95 两两重叠 ⇒ `不可判`（无差异）` | ✅ 正确（「三点纵坐标差」表述已消失） |
| §4.1#1 **L308** | 同 §0 句式一致 | ✅ 正确 |

- **旧措辞残留检查**：`grep -c "三点纵坐标差"` → **0**；全文 `grep -n "0\.59\|0\.78"` 命中 **3 行（L24 / L154 / L308）**，其余语境合法（无第 4 处、无把 `0.59` 当三点极差用的地方）。
- **数值复核**（沿用第一版重算）：`(364−360)/510 = 0.7843pp`、`4 条消息`；`D12-I↔T5 = −1 条 / −0.196pp`、`D12-I↔D12-H = +3 条 / +0.588pp` ⇒ 现文两种说法均成立。

## 二-2. PWC ①–⑦ 闭合核（七条，逐条对表）

| # | 应改内容 | 实测落点与原文要点 | 判定 |
|---|---|---|---|
| **①** | §4.2 加「对外引用必须同屏带自己`不可判`+三对 CI」的**硬**护栏 | **L327**：`（该句依据的 F-1 差值是 `不可判` 读数，对外引用必须同屏带上「`不可判`」与三对 CI。）` | ✅ **够硬**：用「**必须**」祈使禁令、对象明确（`不可判` + 三对 CI），**不是**「仅供参考」类软话 |
| **②** | 「非背景」列补定义 | **L236**：`「非背景」= 与页面最常见颜色（众数色）曼哈顿距离 > 24 的像素占比` | ✅ 与脚本 `render_shots.py:93` 定义一致（我第一版按此复算得 0.582/0.4743/0.177/0.5317，与表值吻合） |
| **③** | §2.4 行内证据状态说明 + §2.3 path/sha 说明 | **L200**：`本表全部行的证据状态统一为 `部分读数(partial)`…path + sha 已在节首给出`；**L188**：`本节各行的 path + sha 已在节首统一给出` | ✅ 两半都落 |
| **④** | 日志 sha 全 64 位 | **L117**：表头改「日志 sha256（**全 64 位**）」；L119–L124 六臂实测全 64 位（`72c0ca97…8f5d0c4`／`dd4ad73d…96ff36`／`122b36e9…9c3207`／`c1f86bf6…58963cf`／`643f13a5…85b13141`／`ae969198…b1559b`） | ✅ 六臂无一残留 12 位前缀 |
| **⑤** | personas 路径 | **L169**：`名字集 `code/config/personas.json` 的 20 个 `display_name`` | ✅ 与仓内实际路径一致（`code/config/personas.json` 实有 20 个 `青溪镇·*`） |
| **⑥** | `dup_calibers.json.checks` 说明 | **L188**：`dup_calibers.json.checks 为历史字段、当前工具现跑不产出，数值不受影响` | ✅ |
| **⑦** | `Q-27` 的 `0.41` 标「非基线读数」 | **L277**：`0.41`（**待改默认值，非基线读数**；= `loose` 值，且不是 `ADDR_UPPER` 在 T5 上算出的 `0.3804`） | ✅ |

> **条目数对齐（作者 04:25 提出）**：我第一版的 PWC 编号为 C-1…C-7（对应 Leader 04:22 裁定的 ①…⑦），**⑦ 本就在我的清单内**（第一版 §九 C-7 = 「§3 `Q-27` 的 `0.41` 建议标『待改默认值、非基线读数』」），故是**七条全闭合**，不存在「release-engineer 只转了 6 条」的漏改。

## 二-3. 结论状态词是否被改动（**逐条比对：未变**）

- §4.1 十三行状态词与第一版**逐行逐字相同**：`描述性读数`+`不可判`（#1）、`描述性读数`（#2 #5 #6 #7 #8）、`不可判`（#3 区间重叠 / #4 分母不同源不得做差）、`描述性读数（空态）`（#9）、`部分读数(partial)`（#10）、`已验证`（#11）、`0 / 0`（#12）、#13 仍写「不由本报告作出、不复判不改判」。
- 词频与第一版一致：`不可判 20 / 描述性读数 21 / 部分读数 4 / 机制生效 3 / 机制未生效 4`；`改善 / 提升 / 显著 / 优于` 仍 **全 0**；`效果` 13 处**全部为否定或陈述式**（「无效果结论」「不构成任何效果判定」「非效果判定」…），**无新增越界表述**。
- §4.3 两条限定语**未动**，且 **「本轮 commit 后本句失效，长期口径见登记表 `N-4`/`N-7`」括注仍在**（L332，Leader 让核的第①件事）——未丢失。

## 二-4. §3 与登记表的一致性（**本轮唯一新增偏差，已授权**）

- 15/15 行、顺序一致；**14 行与登记表逐字相同**；唯一差异 = **`Q-27` 行新增括注「（待改默认值，非基线读数；」**（Leader 04:22 裁定的 ⑦，**属授权修改、非擅自改判**，且未改该行「一句话事实/证据/处置」实质）。
- ⚠️ 由此产生的**引用漂移风险（CAVEAT，不阻塞）**：§3 头注仍写「本报告只抄这张表，不重查、不重判」，而 `Q-27` 行已非逐字复制 ⇒ 建议二选一：**A** 下一轮把该括注同步回登记表 `Q-27` 行；**B** 在 §3 头注补一句「`Q-27` 行按 Leader 04:22 裁定加了一处括注」。这正是本队反复踩的「同一句话两处不同字节」病根，宜尽早消掉。

## 二-5. 第二版残留 caveat（3 条，均不阻塞发布）

| # | 内容 | 建议 |
|---|---|---|
| V2-C1 | §3 `Q-27` 行与登记表不再逐字相同（授权修改） | **处置已定（作者 04:26 回复）：选 A —— 本轮不改字节，下轮把该括注（「待改默认值，**非基线读数**」）同步回 `cycle14-issue-register.md` 的 `Q-27` 行，由登记人 `repo-cartographer` 落笔；不改本份报告。**理由：B 会当场使被验 sha `50874f2e…06253` 失配、需再走一次复验；A 才消掉「同一句话两处各存一份」的病根（与 `N-2`/`N-3`/`Q-27` 同型）。⇒ 本终局结论不受影响 |
| V2-C2 | L327 护栏句写「与三对 CI」，但**句内未列出三对 CI 数值**（数值在 §2.1 表） | 可接受（指向明确、同文可查）；若想更硬可加「（见 §2.1 表三行 CI）」 |
| V2-C3 | 第一版 C-1 的「生活气息层没有被推动」句式仍在（3 处） | 已被 L327 护栏覆盖 ⇒ 对外引用时**必须**带 `不可判`+三对 CI；本条不要求再改报告 |

## 二-6. 第二版核验边界（如实）

- 只核「改动 6+1 处 + 状态词 + §3 一致性 + sha/行数/字节」；**未重跑**第一版那 19 项读数（数据层作者声明未动，我 grep 亦未见表内数值行改动）；若提交前数据层也被改动，本终局结论不覆盖。
- `render_report` / PNG 等证据件本轮**未变**（作者声明未动 `v2/evidence/`；我第一版已 18/18 + 20 件 sha 全核）。

---

*终局核验：`independent-verifier`（非作者）｜被验字节 `50874f2e…06253`（407 行 / 68,543 B）｜分档 **PASS-WITH-CAVEATS（0 BLOCK）**｜本文件两版记录均保留，未修改任何被核文件*

