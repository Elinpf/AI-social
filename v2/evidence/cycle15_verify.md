# CYCLE-15 报告独立复验（V1）核验结论

> **核验人**：`independent-verifier`（非作者）｜**核验时刻**：2026-10-24 04:50–05:0x (+08:00)
> **被验字节（唯一基准）**：`reports/CYCLE-15-20261024.md`
> `sha256 = 08a00a8f69693fbc8190c8efcebcff00aeb74807f9689825b4f0d7352b8fefdb`
> **456 行 / 68,391 B**
> 三项我**自己实测**（`sha256sum` / `wc -l` / `stat -c%s`），与 Leader 裁决口径（04:46:46）与作者交付声明（04:47:04）**三者一致**，故锚定成立。
> ⚠️ **本次分档只对这份字节生效**。报告再改一个字节，本结论（含 BLOCK 与必修清单）即不再对应新字节，须重走 V1。
>
> **旁证（不作第二基准）**：`team-workspace/artifacts/docs/cycle15-draft.md` 与仓内版 `cmp` 逐字节相同、同 sha（我实跑 `cmp` → 无差异）。
> **环境锚**：`report_base_HEAD = da5379d6578d6aa78507d14372906078d1de62d4`（`git rev-parse HEAD` 实测）；`git rev-list --count d0a320b..da5379d` = **4**。
> **核验方式**：不采信报告自述，**逐项独立重跑**（`partner_choice_stats.py` / `partner_choice_permtest.py` / `partner_choice_permtest_conditional.py` / `f1_recompute.py` / `form_metrics.py` / `d12i_dup_calibers.py` / `obs llm-cost` 全部我自己跑一遍到 `/tmp`，`--out` 一律不覆盖被核件）；`sha256sum -c`、PNG sha、18 段对话原文逐字比对、`git log/rev-list/merge-base` 均自行复算。
> **边界**：只读。未改 `code/`、`reports/` 与任何被核件字节；未 commit / 未 push；未起跑批；未重跑渲染链。

---

## 结论分档：**BLOCK（6 项）**

**一句话**：**读数层全部过关**——报告 §2 的每一个数字我都独立重算，**22 项抽样全部与报告完全一致（0 项不符）**；证据存在性 **24/24 路径存在**、三处 `SHA256SUMS` **4/4 + 15/15 + 18/18 全 OK**；4 张 PNG **确为 CYCLE-14 真渲染件**（报告如实标注「非本周期新渲染」）；§4 的 **18 段对话逐字 18/18 一致**（行号、单行 sha 全对）；`4e20256` 仅出现在 §3 `N-8` 与附录、`偏好` 仅出现在指定限定句、**无 `0/1`、无「两臂条件化」**。
**但记账层有 6 处硬错**（同一量两个数/三个数、同一 key 两个值、sha 指向不存在字节、条数少算、状态词清单与正文冲突），**且全部落在「可被读者当场一眼核错」的位置**（页首、§1.1、§1.4、§3.2、附录 B）。⇒ **修正前不可发布**；6 项均为「改数字/改指向」，**不动任何读数结论、不动任何状态词判定**。

- BLOCK 数：**6**（详见 §八）
- 必修（不阻塞发布，但建议同批改）：**10** 条（详见 §九）
- 读数一致率：**22/22**｜证据存在性：**24/24**｜sha 抽核：**37 件全部一致**（3 处 `SHA256SUMS` 合计 37 行 + 页首 15 件自陈 sha + 3 件工具 + 2 件日志）

---

## 一、抽样重算（22 项，覆盖报告每一节）｜报告值 vs 我重算值

> 全部命令我自己跑到 `/tmp`（`--out /tmp/...`），**未写任何被核件**。我的重算件 sha 见 §附录 A。

| # | 项（口径名带后缀） | 报告值 | 我重算值 | 一致 | 我的复算方式 |
|---|---|---|---|---|---|
| 1 | **D2.2 `n_init` / `n_agents`** | 114 / 16（两臂） | **114 / 16（两臂）** | ✅ | 自跑 `partner_choice_stats.py --log D12-I=… --log T0=… --out-json /tmp/v15_pcs.json` |
| 2 | **`pairs_observed / pairs_possible`** | 65/120 = 54.17% | **65 / 120 = 54.17%** | ✅ | 同上（`C(16,2)=120` 亦复核） |
| 3 | **`repeat_pair_rate`** | 42.98% | **42.98%** | ✅ | 同上 |
| 4 | **`distinct_partners_mean`** | 4.5 | **4.5** | ✅ | 同上 + 我另用独立脚本按 `turn_index==0 && from && to` 复算 `mean k = 4.5` |
| 5 | **`top1_partner_share_mean / max`** | 36.49% / 66.67% | **36.49% / 66.67%** | ✅ | 同上 |
| 6 | **`herfindahl_mean`** | 0.2877 | **0.2877** | ✅ | 同上 |
| 7 | **`uniform_expected_hhi_mean`（= `mean(1/k_i)`，非 HHI）** | 0.2522 | **0.25223**（我按 `mean(1/k_i)` 独立复算） | ✅ | 独立脚本复算：`mean(1/k) = 0.252232`；报告 §2.1.1 第 1 条「该字段实为 `mean(1/k_i)`、与零均值 `0.2159` 是两量」**核实成立** |
| 8 | **无条件置换 `B` / `seed`** | B=2000、seed=42 | **B=2000、seed=42** | ✅ | 自跑 `partner_choice_permtest.py --B 2000 --seed 42 --pool all_others` |
| 9 | **无条件零分布 `q025–q975`** | 0.1938 – 0.2462 | **0.1938 – 0.2462** | ✅ | 同上（`null_mean 0.2159`、`null_sd 0.0137` 亦逐字段一致） |
| 10 | **无条件 `p`（单侧 ≥）** | 0.0（0/2000） | **0.0**（`p_value_one_sided_ge = 0.0`，`observed 0.2877`） | ✅ | 同上；我的 `/tmp/v15_perm_D12I.json` 与证据件 `permtest_D12-I.json` **sha 逐字节相同**（`4d029821…10ea`） |
| 11 | **条件化检验 `q025–q975` / sd / p** | 0.1933–0.2455 / 0.0134 / 0.0 | **0.1933–0.2455 / 0.0134 / 0.0** | ✅ | 自跑 `partner_choice_permtest_conditional.py --B 2000 --seed 42` |
| 12 | **条件化覆盖臂** | **仅 T0 单臂**（D12-I 未跑） | **属实**：`d21_partner_hhi_permtest_conditional.json` 的 `log = v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl` | ✅ | 我实读该 JSON；任一位置无「两臂条件化」字样（`grep` 0 命中） |
| 13 | **`0.2877` 超上界幅度** | +0.0415 | **0.2877 − 0.2462 = 0.0415** | ✅ | 算术 |
| 14 | **两零分布差** | `q025` 差 0.0005 / `q975` 差 0.0007 | **0.1938−0.1933 = 0.0005 / 0.2462−0.2455 = 0.0007** | ✅ | 算术 |
| 15 | **F-1 三臂（D12-I / T5 / D12-H）** | 363/510、364/510、360/510（Wilson95 三对重叠） | **363/510 = 0.711765、364/510 = 0.713725、360/510 = 0.705882**；CI `[0.670987,0.749376]` / `[0.673012,0.751244]` / `[0.664916,0.743770]` | ✅ | 自跑 `f1_recompute.py` 三臂 → `/tmp/v15_f1.json`（**sha 与证据件 `f1_recompute_cycle15.json` 逐字节相同** `35fe6bc3…cd43`） |
| 16 | **`L-3_paren_block_any`** | 369/510 = 72.3529% | **369/510 = 0.723529** | ✅ | 自跑 `form_metrics.py --log D12-I --out /tmp/v15_form.json --batch-id D12-I --no-timestamp` |
| 17 | **`addr_head_pfx2`** | 116/510 = 22.7451% | **116/510 = 0.227451** | ✅ | 同上 |
| 18 | **`addr_head_strict_personas20`** | 134/510 = 26.2745% | **134/510 = 0.262745**；两口径差 **18 条 / 3.5294pp** | ✅ | 同上（并实核 `code/config/personas.json` 有 **20** 个 `青溪镇·*`） |
| 19 | **`addr_head_loose` / `addr_head_alias`** | 144/510 / 0 | **144/510 = 0.282353 / 0/510** | ✅ | 同上 |
| 20 | **`L-7_dup_ngram8_rate`(norm8) / `L-7_raw8_shingle`(raw8)** | 317/510 = 62.1569% / 368/510 = 72.1569%（差 51 条 / 10.0pp） | **317 / 368**（0.621569 / 0.721569），差 **51 条** | ✅ | 自跑 `d12i_dup_calibers.py --out /tmp/v15_dup.json`（`raw_exact = norm_exact = 47/510 = 0.092157` 亦一致） |
| 21 | **成本 `obs llm-cost`** | rc=0、4200 calls、cached 1583、degraded 0、thinking 668、tokens_total 880179 | **rc=0、`{'openai_compat': 4200}`、cached 1583、degraded 0、thinking 668、tokens_total 880179**；分用途 `dialogue 1832 / importance 1523 / judge 668 / reflect 112 / negotiation 49 / plan 16`（合 4200） | ✅ | 自跑 `cd code && python3 -m obs llm-cost --log <D12-I> --require-provider openai_compat` → `/tmp/v15_cost.txt`，**sha `76a68ed0…7830` 与入库件逐字节相同** |
| 22 | **D2.1-A2（`_any` / `_thread`）** | 26.32%(30/114) / 1.75%(2/114)、2.63%(3/114)；`n_msgs_total` json=455 vs md=510 | **30/114 = 26.3158%、2/114 = 1.754%、3/114 = 2.632%**；实测 `d21_a2_incidence.json` 两臂 `n_msgs_total = 455`，`d21_a2_incidence.md:20` 同名量 = `510` | ✅ | 实读两件 + 算术；**报告 §3 `N-12` ① 登记的口径冲突属实** |

**另核（非数字但可复算）**
- **`selectors`**：`selector_stats_full.json` → `argmin_unique = 480/510 = 0.941176`、`not_all_equal = 503/510 = 0.986275`、`all_zero = 0`、`picked{0:167,1:174,2:169}` —— 与报告 §2.5 两行**逐位一致**。
- **`toppartner max = 66.67%` 的归属**：我用独立脚本按 `turn_index==0` 复算，`P013` 发起 **3** 次、其中 **2** 次→`P004` ⇒ `2/3 = 66.67%`；`P002` 发起 **5** 次 —— 与报告 §2.1.1 第 4 条**完全一致**（该值确由最小样本居民主导）。
- **两臂 JSON 数值字段全等**：`partner_choice_stats.json` 去 `log` 后 **12 个数值字段**逐字段相同；`permtest_T0.json` 与 `permtest_D12-I.json` 去 `log` 后 **12 个统计字段**全等（`equal_without_log: True`）—— 报告 §2.1「12 个数值字段全等」、§2.2「12 个统计字段全等」**均属实**。
- **`tools/d12i/` 394 行**：`git diff --numstat 4e20256 6c8a70d` 合计 added = **394** —— 报告 §3 `N-8` 属实。

---

## 二、口径混用专项（6 类：**全部通过**）

| 类 | 报告是否互换/单选/未标 | 判定 | 依据 |
|---|---|---|---|
| **`addr_head` 必须带后缀** | 未互换：全文一律写成 `addr_head_pfx2`（116/510）与 `addr_head_strict_personas20`（134/510），并明写「差 3.53pp / 18 条，不得互代」；无一处单写「strict」了事 | ✅ PASS | §页首硬约束①、§2.5 表两行、§4.3 第 1 条 |
| **`L-7` 必须双口径并列** | 未互换：`norm8 317/510 = 62.1569%` 与 `raw8 368/510 = 72.1569%` 并列，明写「差 51 条 / 10.0pp，不得互代」「跨批不可比」 | ✅ PASS | §页首硬约束②、§2.5 表、§4.3 |
| **`uniform_expected_hhi_mean` vs 零分布均值** | **未被混用**：报告专列「该字段实为 `mean(1/k_i)`…与置换零分布均值 `0.2159` 是两个量，**不得互代、不得相减**」，并在 §2.1.1 第 1 条重复一次 | ✅ PASS | 我复算 `mean(1/k) = 0.252232`，两量确实不同；报告警示与实际一致 |
| **跨刻度比较（pp / 条 / 分位）** | 未出现跨刻度混算：所有「差」都给了同一刻度的分子（条数）与 pp 两个值，分位差用绝对分位值 | ✅ PASS | §2.5 两行、§2.2 六条读法第 2 条 |
| **把描述性读数写成效果结论** | **未写**：§2.1/§2.2/§2.3 一律 `描述性读数`，§2.0 明列「不得把下列任何一项写成达标效果项」5 类；`改善 / 提升 / 优于 / 显著优于` 我 `grep` → **0 命中**；`效果` 仅出现在否定句（「不出任何效果结论」「非效果判定」） | ✅ PASS | 我的 `grep` 实测 |
| **分母为 0 写成 `0/1`** | **未写**：§2.0 只有 `0/0`，并明写「分母为 0 时**禁止**写 `0/1`」；`grep "0/1"` → 0 命中（命中的是 `30/114` 一类分数） | ✅ PASS | 我的 `grep` 实测 |

**额外确认（两处报告做对了、易被忽略）**
1. **`p = 0.0` 的含义被写死**：§2.2 第 1 条明确「是 2000 次重抽中没有一次达到或超过实测值（0/2000），**不是**误差为零」，且要求 B 与 seed 同屏 —— 这一条正是本队历史上最常被误读的读法，报告做对。
2. **不引用工具 `verdict` 原话**：条件化件 `verdict` 原文含「提示存在对端偏好」的归因措辞，报告 §2.2 明写「本报告不引用该措辞」，改写成「集中度超出『时段×话题』格子结构所能解释的部分」；`grep "偏好"` 全文 **1 处**，即 §2.2「非对端偏好的证据」限定句 —— **符合 Leader 裁决口径**。

---

## 三、证据存在性（路径 **24/24 存在**；`sha256sum -c` **37/37 OK**）

**① 三处 `SHA256SUMS` 全跑（我自己跑，不采信报告）**

| 目录 | 结果 |
|---|---|
| `v2/evidence/life_texture_cycle14/SHA256SUMS` | **4/4 OK** |
| `v2/evidence/d22_partner_choice/SHA256SUMS` | **15/15 OK** |
| `v2/evidence/d12i_readings_20261024/SHA256SUMS` | **18/18 OK**（含 `../d12i_external_shingles_4gram.json`） |

**② 路径存在性（24 条，`test -e` 逐条）**：`reports/CYCLE-14-20261024.md`、`v2/evidence/cycle14_verify.md`、`v2/evidence/d22_partner_choice/SHA256SUMS`、`tools/d21/partner_choice_stats.py`、`tools/d21/partner_choice_permtest.py`、`tools/d21/partner_choice_permtest_conditional.py`、`tools/d21/a2_incidence.py`、`v2/evidence/d21_partner_choice.md`、`v2/evidence/d21_partner_hhi_permtest.json`、`v2/evidence/d21_partner_hhi_permtest_conditional.json`、`v2/evidence/d21_a2_incidence.json`、`v2/evidence/d21_a2_incidence.md`、`v2/evidence/d12i_external_shingles_4gram.json`、`v2/evidence/d12i_result.md`、`reports/R4-life-texture.md`、`code/config/personas.json`、`code/life/planner.py`、`code/life/agent.py`、`code/orchestration/integration.py`、`v2/refs/D12I-prereg-aligned-objective.md`、`.worktrees/d12i-aligned/…/run_d12i_aligned_n16r60_seed42/run.jsonl`、`v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl`、`reports/README.md`、`v2/evidence/form_metrics/d12i_receipt_README.md` → **24 条全部存在，0 条缺失**。

**③ 报告自陈的 sha 我逐件实算（抽样 15 件，全部一致）**

| 件 | 报告值（前 8–12 位） | 我的实测 | 一致 |
|---|---|---|---|
| `v2/evidence/cycle14_verify.md` | `ce9084e1…dcde` | `ce9084e1d0e863271088617c5e9c5ad84208a2bbabe9534547a3fb49f4f0dcde` | ✅ |
| `cycle15-evidence-brief.md` | `1441b49e…4808`（137 行 / 13,827 B） | 同（137 行 / 13,827 B） | ✅ |
| `cycle15_commit_window.md` | `001314e7…c1d8`（6,110 B） | `001314e7278400885d93959ed88a330790f071d6d27cbcfca7d2e39a5edcc1d8` | ✅（**注意：报告 L38 另一处写 `768aefd2…06cc`，见 §八 B-3**） |
| `d21_partner_choice.md` | `4840783f…4b91`（63 行） | 同（63 行 / 4,956 B） | ✅ |
| `d21_partner_hhi_permtest.json` | `da053c10…b921` | 同 | ✅ |
| `d21_partner_hhi_permtest_conditional.json` | `0f99466d…1ce2` | 同 | ✅ |
| `tools/d21/partner_choice_stats.py` | `157a767e…aa15` | 同 | ✅ |
| `tools/d21/partner_choice_permtest.py` | `68de1957…94fa1` | 同 | ✅ |
| `tools/d21/partner_choice_permtest_conditional.py` | `0001c3d6…3e80` | 同 | ✅ |
| `tools/d21/a2_incidence.py` | `95e004ea…7b9e` | `95e004ea7e2eeb08120028b130e2f234ccca214e132aecb7bce72b0b9b0b7b9e` | ✅ |
| T0 日志 | `3c814121…1a74`（116,365 行） | `3c814121b5f8d4b053358c959c926f4e14b8a57bf2c6206dadc94d6695c81a74` / **116,365 行** | ✅ |
| D12-I 日志 | `72c0ca97…0d4`（117,724 行） | `72c0ca97fe6e38632f67e3b2810c65126c0d15d296d068b521dfbb45c8f5d0c4` / **117,724 行** | ✅ |
| `render_report_D12-I.json` | —（§4.2 引用） | `0e345dba…d8a6`（`sha256sum -c` OK） | ✅ |
| `threads_D12-I.json` | `312c4d7c…1655`（6,053,846 B） | 同（`render_report` 内 `threads_json_sha256` 亦同） | ✅ |
| `d21_a2_incidence.{json,md}` | `c65ff3f4…77cd` / `83ca81dd…7bc0` | 均一致（`git ls-files` 亦证 **已入库** `d0a320b`） | ✅ |

**④ 跟踪状态（报告 §1.4 的说法我逐条核）**：`v2/evidence/d12i_external_shingles_4gram.json` **已 tracked**（`git ls-files` 命中）；`v2/evidence/d12i_readings_20261024/` **tracked 18 件**（与报告「计 18 件」一致）；4 张 PNG **均 tracked**；`tools/d21/*.py` 三件与 `v2/evidence/d22_partner_choice/` **全部 `??`**（与报告 §1.4 / `N-10` 一致）。

---

## 四、截图核验（4 张 **真渲染**，报告「非本周期新渲染」标注 **属实**）

| 图 | 我的 sha256 | 报告值 | 一致 | 尺寸 / 字节 | mtime |
|---|---|---|---|---|---|
| `D12-I-chat-72c0ca97.png` | `d4883c4374886370141cff7931f9b1b171b9eb6d6e7efac273e4c75567eae5af` | 同（§4.2 S-1） | ✅ | 1400×900 / 290,381 | **04:05:31** |
| `D12-I-rhythm-72c0ca97.png` | `2c942d858e917663ea1406819af1219bff72ad8c373564f212b35e2ebb1c7d8f` | 同（§4.2 正文提及） | ✅ | 1300×1050 / 282,110 | 04:05:34 |
| `D12-I-spread-72c0ca97.png` | `9f0a6bd660c15d691dd7e86e790bc7ae4c72758781f178805d36bf7ab84827f2` | 同（§4.2 正文提及） | ✅ | 1400×1000 / 178,501 | 04:05:36 |
| `D12-I-chat_thread-72c0ca97.png` | `f14fbe84c4eed8974f6ce177533f78170fb73df9f8c9c8c40ef9e36b4f1ebc90` | 同（§4.2 S-4） | ✅ | 1200×1000 / 301,761 | 04:05:39 |

**「真实日志渲染、非拼图/非占位」的交叉核（我自己读件，不看报告）**
- `render_report_D12-I.json` 自陈并与实物三方一致：`log_sha256 = 72c0ca97…0d4`（= 来源日志）、`threads_json_sha256 = 312c4d7c…1655`（= 中间件）、`ok_count = 4`、`fail_count = 0`、`generated_at = 2026-10-24T04:05:40+08:00`。
- `render.log` 实读：`SHOT OK` **4 条**；四条 URL 均含 **`still=1`**（终态回放）、`data=sample/dialogue_D12-I/threads.json`、`--retry-blank 2 --no-blank-check`（与 `Q-20残留` 一致）。
- `pixel_selfcheck` 四张全 `OK`，数值 `distinct_colors = 24216 / 22315 / 15623 / 24951`、`top_color_frac = 0.1417 / 0.262 / 0.5683 / 0.1107` ⇒ **非空白页**；`spread` 的 `non_bg = 0.177`（空态但确有渲染框架）。
- **「非本周期新渲染」属实**：四张 PNG 的 mtime 全为 **2026-10-24 04:05:3x**（CYCLE-14 渲染时刻，本周期窗口起点为 04:27:44 之后）；报告 §4.2 表「本周期状态」列逐张写「**CYCLE-14 已入库件，非本周期新渲染**」，§4 头注亦同 —— **标注如实**。
- 差异登记：报告 §4.2 表只列 **S-1 / S-4** 两张并明写「另两张不展开」；我按 8 项任务卡要求把 **4 张全部**复算（结论：4/4 一致，未发现被替换或占位图）。

---

## 五、§3 逐行核对（15 行挂账 **无遗漏**；新查 7 条 **编号连续**）

**① 与 CYCLE-14 §3 表（`reports/CYCLE-14-20261024.md:273–287`）逐条对表**
- 编号与顺序**完全一致**（15 条、同一顺序）：`N-4 / Q-17 / N-1 / N-6 / Q-27 / N-2 / N-3 / N-5 / Q-22 / Q-24 / Q-21 / Q-20（残留）/ T361 / T374 / N-7`。
- 「本轮是否处置」列：`未处置` / `未收口` / `已处置（定性）` 三类；**`T361` / `T374` 标 `已处置（定性）`（承接上轮裁定）**，其余 13 条无一条写成已结案 —— 与 CYCLE-14 的「2 条已处置、13 条未处置」**数值一致**（我逐行核）。
- **无「已收口 / 已结案 / 已关闭」误写**：全文 `grep` 命中 5 处，**全部是否定句或纪律声明**（L78「没有把任何一条写成已结案」、L227「不得写成已结案」、L249「无一条写成已结案」、L266「无一条写成已结案」、L454 状态词表）。
- ⚠️ **两处偏差（已列入必修，非 BLOCK）**：① 报告 §3 头注与 §3.1 表头称「逐条抄录 / 转抄」，但「一句话事实」列实为**压缩改写**（我用 `difflib` 逐行比对相似度 **0.290–0.667**，例 `N-7` 0.290、`N-3` 0.338、`N-4` 0.414）⇒ 措辞不实（见 §九 M-4）；② `N-4` 状态词由 CYCLE-14 的「处置中」改为「**未收口**」、`N-2` 由「未处置」改为「未收口」，与本报告自称「不重查、不重判」冲突（见 §九 M-5）。

**② 本周期新查 7 条（`N-8`…`N-14`）**
- **编号连续无缺**：`N-8 / N-9 / N-10 / N-11 / N-12 / N-13 / N-14` = **7 条**，无跳号、无重复。
- 逐条抽样核实（我实跑）：`N-8` 游离 commit —— `git merge-base --is-ancestor 4e20256 HEAD` → **rc=1**、`git for-each-ref --contains 4e20256` → **空**、`git diff --name-status 4e20256 6c8a70d` → **4 个 `A tools/d12i/*`（394 行）**，**全部属实**；`N-10` 未入库 —— `git ls-files tools/d21/` **仅 `a2_incidence.py` 1 件**，其余 `??`，**属实**；`N-11` 登记表原件丢失 —— `team-workspace/artifacts/docs/` 现仅有 cycle15 三件、无 `cycle14-*`，**属实**；`N-12` ① 同名不同量 —— **属实**（见 §一 #22）；`N-13`/`N-14` 为判据/落盘件缺失类，与 `partner_choice_stats.json` 实键（13 键、无 `weighted/pool_kind/min_k_filter`）**相符**。
- ⚠️ **计数错（BLOCK，见 §八 B-4）**：§3.2 标题写「**6 条**」，实为 **7 条**；§3.3 写「其余 **19 条（13 + 6）**」，应为 **20 条（13 + 7）**。

**③ 与 Leader 口径「21 条」的差**：报告正文实际列 **15 + 7 = 22 条**，但因 §3.2 把 7 条写成 6 条、§3.3 据此算成 19 条，读者会得到「15+6=21」的错账 ⇒ 修正后应统一为 **22 条（15 + 7）**，或按 Leader 口径明确「21 条」指哪 21（**该口径差必须由 Leader 裁决，我不代改**）。

---

## 六、§4 对话原文逐字核验（**18/18 段全部一致，含标点**）

- 方法：写独立脚本 `/tmp/verify_excerpts.py`，从 `dialogue_excerpts.md` 解析出**表格行（18 行：seq / 行号 / 单行 sha）**与**原文段（18 段）**，逐条到 `.worktrees/d12i-aligned/…/run.jsonl` 取对应 `seq` 的 `payload.body` 与整行字节做**逐字 + sha256** 比对。
- 结果：**行号 18/18 一致、单行 sha256 18/18 一致、原文逐字 18/18 一致、`thread_id` 与 `type=MSG_DM` 全部相符**（`seq 77/148/225/581/730/994/2154/2244/2362/3025/3386/3882/5080/5190/5279/5743/6091/6480`）。
- 报告 §4.1 引用的 **8 条**（`seq 77/581/3025/5080` + `148/994` + `225/730`）全在上述 18 条内，**逐字一致**；报告自陈「抽 3 行（78/149/226）实跑复核 3/3 一致」——我扩大到 **18 行全核**，结论相同。
- 行号引用核：案例 1 `78 / 582 / 2155 / 3026 / 5081 / 5744`、案例 2 `149 / 995 / 2245 / 3883 / 5191 / 6481`、案例 3 `226 / 731 / 2363 / 3387 / 5280 / 6092` —— **全部与实测行号一致**。
- 段内轮次标注核：案例 1「段 1 = 第 0–1 轮、段 2 = 第 3 轮、段 3 = 第 4–5 轮」与 `turn_index` 实测一致。
- **标点级**：18 段全部整串相等（脚本用 `==` 比较，非相似度），含全角标点、`——`、`“”`、括号块 —— **无一处改写**。

---

## 七、commit 表复核（我自己跑 `git log`）

| 报告说法 | 我的实测 | 一致 |
|---|---|---|
| 区间 `d0a320b..da5379d` = **4 条** | `git rev-list --count d0a320b..da5379d` → **4** | ✅ |
| 逐条 `6c8a70d / 2a52123 / 9693b2f / da5379d` | `git log --format='%h %an %cI %s' d0a320b..da5379d` → **4 条，顺序与 sha 与报告 §1.1 表逐条一致** | ✅ |
| 全部队外 agent（author `life-evidence-analyst`） | 4 条 `%an` 全为 **life-evidence-analyst** | ✅ |
| 时刻 04:27:44 / 04:27:51 / 04:33:20 / 04:35:43 | `%cI` 逐条相同（`+08:00`） | ✅ |
| 本队自有 commit = **0** | `da5379d` 之后无本队 commit；工作树内 `reports/` 仅 ` M README` + `?? CYCLE-15` | ✅ |
| `4e20256` 不可达、仅用于 `N-8` 与附录 | `git merge-base --is-ancestor 4e20256 HEAD` → **rc=1**；全文 `4e20256` 命中 **4 处** = `N-8` 行（L255）+ 附录 A-3 三行（L394–396）⇒ **无活跃引用** | ✅（符合 Leader R1） |
| 附录 A-1「`d0a320b..9693b2f` → **3**」 | `git rev-list --count d0a320b..9693b2f` → **3**（算术正确，但与正文「4 条 / `da5379d`」冲突 → 见 §八 B-2） | ⚠️ |

---

## 八、BLOCK 清单（6 项：**位置 + 否决理由 + 改法**，不替他改任何读数）

> 共同特征：**都是「同一量在不同位置写了不同的数/不同的指向」，且都在页首或一眼可核处**。6 项全部可**一条一句**改完，不改任何读数结论、不改任何状态词判定。

### B-1 `v2/evidence/d22_partner_choice/` 的件数在一篇里出现 **三个值**（16 / 12 / 3）
- **位置**：`16` = 页首 L41「（16 个文件 = `SHA256SUMS` 覆盖 15 件 + `SHA256SUMS` 自身）」、§1.4 L86「D2.2 证据包 16 个文件」；`12` = L60「`v2/evidence/d22_partner_choice/` 12 件」、L257（`N-10` 行）「`v2/evidence/d22_partner_choice/` **12 件**」与同行「…`/`12 件`随本报告一并入库」；`3` = §1.3 L77「`d22_partner_choice/`（3 件）」、§5 L359「`v2/evidence/d22_partner_choice/` 3 件」。
- **实测（我的基准）**：`ls -1 v2/evidence/d22_partner_choice | wc -l` → **16**；`sha256sum -c SHA256SUMS` → **15 行全 OK** ⇒ **16 = 15 + SHA256SUMS 自身**，页首/§1.4 的 16 为真值，**`12` 与 `3` 均错**。
- **否决理由**：这是本周期产物清单的**件数**，直接决定 release 白名单覆盖面；三个值并存会让 `release-engineer` 无法判断该入几件。**修正前不可发布**。
- **改法（不动数字结论）**：把 L60、L257（两处）的 `12 件` 与 L77、L359 的 `3 件` 统一改为 **`16 个文件（`SHA256SUMS` 覆盖 15 件 + 自身）`**；若原意是「git status 计 1 行」，请写成「目录在 `git status` 计 **1 行**」，不要写成「3 件」。

### B-2 同一 `report_base_HEAD` 两个值、commit 条数两个值（3 vs 4）
- **位置**：页首 L3「文档基准 `report_base_HEAD = 9693b2f1e1901741c1934019c895e00e3f86ad5f`（04:33:20）」**vs** 取数时刻 L34「**`report_base_HEAD`**（文档落笔基准） | `da5379d6578d6aa78507d14372906078d1de62d4`（04:35:43）」；§1.1 标题 L48「**3 条**，`d0a320b..9693b2f`」+ 附录 A-1「`git rev-list --count d0a320b..9693b2f` → **3**」**vs** §1.1 表 **4 行**（含 `da5379d`）、L35「`d0a320b..da5379d`，4 条」、L59「上表 4 条」。
- **实测**：`rev-list --count d0a320b..da5379d` = **4**；`…9693b2f` = **3**；HEAD = `da5379d`。
- **否决理由**：`report_base_HEAD` 是本报告全部 sha 的**基准锚**（页首自己这么写），同一 key 两个值等于自毁锚点；条数 3/4 并存会让「本周期 commit = 0」这条判断失去可核基础。**修正前不可发布**。
- **改法**：页首 L3 的 `9693b2f` 改为 **`da5379d`**（或把 L3 改名为 `report_draft_base_HEAD` 并显式说明它与落笔基准不同）；§1.1 标题改为「**4 条**，`d0a320b..da5379d`」；附录 A-1 改为 `d0a320b..da5379d` → **4**（并同步注释里的期望值）。

### B-3 给 `cycle15_commit_window.md` 标的 sha 指向不存在的字节
- **位置**：取数时刻表 L38 末「`evidence-analyst` 的 `v2/evidence/d22_partner_choice/cycle15_commit_window.md:5` 已同款声明（**`768aefd2…06cc`**）」。
- **实测**：该件 sha256 = **`001314e7278400885d93959ed88a330790f071d6d27cbcfca7d2e39a5edcc1d8`**（6,110 B；`SHA256SUMS` 第 1 行同值）；且本报告 **L41 与 §1.2 自己写的也是 `001314e7…c1d8`** ⇒ `768aefd2…06cc` 在仓内**不存在**（我全仓 `grep` 仅命中报告这一处）。
- **否决理由**：字节错锚 —— 读者按 `768aefd2` 永远核不到，属本队纪律里最忌的「sha 指向不存在字节」。**修正前不可发布**。
- **改法**：把 L38 的 `768aefd2…06cc` 改成 **`001314e7…c1d8`**（若确有一版更早的 `768aefd2` 稿件，则须写清「作废旧值，现值为 `001314e7…`」，但仓内无此件，建议直接删括注改现值）。

### B-4 §3.2 条数少算 1（「6 条」实为 7 条），§3.3 连带算成「19 条」
- **位置**：§3.2 标题 L251「本周期新查出的问题（**6 条**）」；§3.3 第 1 条 L265「其余 **19 条（13 + 6）**」。
- **实测**：`N-8`…`N-14` 连续 **7 条**（编号无缺、无重复，我逐条实核）；⇒ 15 + 7 = **22 条**，13 + 7 = **20 条**。
- **否决理由**：条数是本报告「问题账」的合计口径，少 1 条会让读者漏读一条 `失败` 级问题（实际被少算的是 `N-14`）。**修正前不可发布**。
- **改法**：L251 改「**7 条**」；L265 改「其余 **20 条（13 + 7）**」；**若 Leader 坚持「21 条」口径，请 Leader 明示 21 条由哪些编号构成，我不代作者裁**（当前正文可核到的编号是 15 + 7 = 22）。

### B-5 工作树脏行数的**分解**错，且与另一处（N-6）自相矛盾
- **位置**：L37「**28 行**（…落笔时快照 = **1 条 ` M` + 27 条 `??`**；本报告与 `reports/README.md` 索引行**已计入**）」；L236（`N-6` 行）「本周期仍为 ` M`，落笔快照 **26 行**脏项中第 1 行」。
- **实测**：`git status --porcelain | wc -l` = **28**；分解为 **2 条 ` M` + 26 条 `??`**（` M` = `reports/README.md` 与 `v2/evidence/d3_noiseband_bootstrap.json`；`??` = 25 条历史未跟踪项 + `reports/CYCLE-15-20261024.md`）。
- **否决理由**：总数 28 与实测相符，但**分解与总数、与 L236 的 26 三处互斥**；` M` 数量直接关系到 `N-6`（`d3` 脏件）是否被计入，属于「提交前必看的一行」。**修正前不可发布**（改法纯数字，不改判据）。
- **改法**：L37 改为「**28 行**（= **2 条 ` M`**：`reports/README.md`、`v2/evidence/d3_noiseband_bootstrap.json`；**26 条 `??`**）」；L236 的「26 行脏项」改为「**28 行脏项（` M` 共 2 条）**」。

### B-6 附录 B 的状态词清单与正文**冲突**
- **位置**：附录 B L450「`仅观察` | **§2.5（F-1 行，未重跑）** | ✅ 白名单」。
- **实测冲突**：§2.5 的 F-1 行（L213）状态词是 **`已验证`（本周期重算）**，不是 `仅观察`；`仅观察` 在全文实际出现在 **§2.1.1 第 4 条（L136，`top1_partner_share_max = 66.67%`）** 与 **§2.3（L177，同一量）**。
- **否决理由**：附录 B 是「防止误用」的清单，指错位置等于把「已验证」与「仅观察」串位——这正是本队纪律里的**状态词误用**形态（比数字错更难被发现）。**修正前不可发布**。
- **改法**：把该行位置改为「**§2.1.1 第 4 条 / §2.3**（`top1_partner_share_max = 66.67%`）」；并按实际补一行 `已验证` 的落点（§2.1/§2.2/§2.4/§2.5），或删该行避免与正文对不上。

---

## 九、必修清单（10 条：**不阻塞发布，但建议与 BLOCK 同批改**）

| # | 位置 | 情况（实测） | 建议改法 |
|---|---|---|---|
| M-1 | §1.2 标题 L62 | 「本周期实际做了什么（**四件**…）」，但表内是 **1–5 共 5 行** | 标题改「**五件**」 |
| M-2 | §1.2 L67 vs §2.6 L219 | 同一组量两处计数不同：L67「两臂量 **9 个结构量**」、L219「D2.2 对端选择的 **8 个结构量**」；按 §2.1 表可数出 **8**（`n_init/n_agents`、`pairs`、`repeat_pair_rate`、`distinct_partners_mean`、`top1 mean/max`、`herfindahl_mean`、`uniform_expected_hhi_mean`） | 统一为「**8 个**」或明列清单后取数 |
| M-3 | §3 头注 L225、`N-11` L258 | 两处引「`reports/CYCLE-14-20261024.md:`**`13-27`**」，但 CYCLE-14 §3 表实际在 **264–287** 行（`N-4` 在 273、`N-7` 在 287；13–27 行是页首/§0 区） | 改为 `:273-287`（或 `:264-287`） |
| M-4 | §3 头注 + §3.1 表头 | 称「逐条从…正文**抄录**的版本**转抄** / 本报告只抄这张表」，实测 15 行「一句话事实」列是**压缩改写**（相似度 0.290–0.667） | 改为「**压缩摘要，未逐字转抄**」（否则「转抄」一词本身就是不实陈述） |
| M-5 | §3.1 `N-4` / `N-2` 行 | `N-4` 状态由 CYCLE-14「**处置中**」改为「**未收口**」、`N-2` 由「未处置」改为「未收口」，与本节「**不重查、不重判**」自述冲突（虽方向更保守） | 二选一：① 改回 CYCLE-14 原状态词；② 在 §3 头注加一句「本报告对 `N-4`/`N-2` 的状态词按『入主树≠可复算』下修为『未收口』，属**重述性下修**，非新判读」 |
| M-6 | §2.3 代码行号两处偏移 | `code/life/planner.py:`**`55-56`** 实为 `_pick` 定义在 **47–50**（第 50 行 `return options[int(sha256_hex(seed)[:8], 16) % len(options)]`；报告写的 `sha256(seed)` 实为 `sha256_hex(seed)`）；`code/orchestration/integration.py:`**`1010`** 实为 **1011**（`peers=pids`）；`code/life/agent.py:1123-1127` **正确** | 改成 `planner.py:47-50`、`integration.py:1011`；`sha256(seed)` → `sha256_hex(seed)`。（注：`integration.py:1010` 这处偏移由 `d21_partner_choice.md:40` 继承而来，建议上游同改） |
| M-7 | §4.1 L329 | **悬空残句**：`：① 6 轮跨 3 个时段…` 以全角冒号开头、无主语、**不属任何引用块也不是列表项**（上一行 L327 是 `>` 引用块、下一行 L330 也是 `>` 引用块） | 补回它所属句的引导（例如「**这段对话的三点观察**：①…」），或整段并入 L330 的引用块 |
| M-8 | §2.1 L120/L121/L122/L123/L124、§2.2 L152/L153 vs §2.5 性质声明 + 作者 04:47 自述 | 前两处证据状态写「`已验证`（**本报告重跑** `partner_choice_stats.py`，stdout 与 JSON 逐字段一致）」「**本报告重跑**两臂」；而 §2.5 L215 写「表内数值**没有一个是本报告作者亲自算出的**」、作者自述「我本人只做 `sha256sum -c` 与抄录，**未亲自重跑出数器**」⇒ **同一「本报告」两义** | 二选一：① 保留「重跑」并附一条实跑留痕（命令 + 输出）；② 改成「**抄录自 `evidence-analyst` 重算件**（`readings_recompute_cycle15.md`）；本报告复核的是 sha 一致性」——我复核：**两处引用件的数值我都独立跑通并逐字段一致**，故 ② 也不会削弱结论 |
| M-9 | §0 L25 | 「在 T0 与 D12-I **两份互相独立的日志**上」——两臂发起序列**逐位相同**（§2.2 第 6 条 / §2.3），「互相独立」易被读成两个独立样本 | 加限定：「两份文件独立起跑，但 **114 条发起序列逐位相同**（故两臂差 = `不可判`）」 |
| M-10 | `reports/README.md` CYCLE-15 索引行 | 该行写「新查出 **7 条**」（与 `N-8`…`N-14` 相符，比 §3.2 正确），但括号内列举把 **`N-8` 列了两次**（首为「`N-8` 任务卡 `4e20256` 不可达」、末为「`N-8` 游离 commit 不可引用」），即 **8 个编号点 / 7 条** 的说法 | 删掉重复的那一处 `N-8`（`README` 同属本次交付，须与 §3.2 的 7 条口径一致） |

---

## 十、无法核 / 不可复算项（如实列，不用推断补位）

1. **落笔时刻 `2026-10-24 04:46:05` 与脏行数分解（L37）**：时点快照，事后**不可重建**；我实测当时/现在的总数都是 **28**（分解为 2 `M` + 26 `??`），但**无法证明**落笔那一刻就是这 28 行的同一构成 ⇒ 只判其分解自相矛盾（B-5），不判总数错。
2. **「本周期未起跑任何新批 / 成本 0」**：我按只读边界**无法证明「没有发生」**（不能回溯进程史）；可核的是：`d0a320b..da5379d` 的 4 条 commit 内无 `run_batch` 记录、且我复核的 `obs llm-cost` 只指向 D12-I 历史日志。⇒ 该条**仅作记录**，不作为我的核实结论。
3. **`team-workspace` 于 04:30 被重建（`N-11`）**：现状（`artifacts/docs/` 无 `cycle14-*` 原件）**与报告一致**，但「04:30 重建」这一**时刻与动作**事后不可复算（目录 mtime 已被后续写入覆盖，现为 04:46） ⇒ 只核「原件确实不在」。
4. **两臂发起序列「逐位相同」（§2.2 第 6 条 / §2.3）**：我核了**统计量逐字段相同**（12 字段全等）与**发起分布同值**（`P013 3 次/2→P004` 等抽样一致），但**未逐条 diff 114 条 `(from→to)` 序列**（该项引 `partner_choice_d22.md §B.4`，属 `[文档]`）⇒ 判「与我的统计层一致」，不强认「逐位」本身。
5. **PNG「重跑会得到不同 sha 的等价图」**：我只核了**已入库这一版**的 sha 与三件自洽；**未重跑渲染**（重跑＝新渲染，需报备且会写文件）⇒ 报告所述「首轮 `7cf10530…`」一类历史指纹**未核**。
6. **`N-9`（A2 落在分支 `913ac4d`、无预登记）**：我核了「主树无实现 / `v2/refs/` 无 A2 预登记件」，**未去核分支 `913ac4d` 是否存在**（只读边界内可做但我未做，如实登记）。

---

## 附：本次核验跑过的命令（可原样重放，全部只读、输出落 `/tmp`）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
# 0 被验字节锚定（三项必须自己跑）
sha256sum reports/CYCLE-15-20261024.md ; wc -l reports/CYCLE-15-20261024.md ; stat -c%s reports/CYCLE-15-20261024.md
cmp team-workspace/artifacts/docs/cycle15-draft.md reports/CYCLE-15-20261024.md

# 1 D2.2 结构读数 + 两次置换（B/seed 与报告同）
python3 tools/d21/partner_choice_stats.py --log D12-I=.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --log T0=v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl --out-json /tmp/v15_pcs.json
python3 tools/d21/partner_choice_permtest.py --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --B 2000 --seed 42 --pool all_others --out-json /tmp/v15_perm_D12I.json
python3 tools/d21/partner_choice_permtest_conditional.py --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --B 2000 --seed 42 --out-json /tmp/v15_perm_cond.json   # 我跑的是 D12-I 臂作交叉，数值与 T0 臂同（两臂逐位相同）

# 2 F-1 三臂 / 形态 / 重复度 / 成本
python3 v2/evidence/life_texture_cycle14/f1_recompute.py --arm D12-I=.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --arm T5=.worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42/run.jsonl \
  --arm D12-H=.worktrees/d12h-pairing/v2/evidence/run_d12h_pairing_n16r60_seed42/run.jsonl --out-json /tmp/v15_f1.json
python3 tools/metrics/form_metrics.py --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --code-dir .worktrees/d12i-aligned/code --out /tmp/v15_form.json --batch-id D12-I --no-timestamp
python3 tools/metrics/d12i_dup_calibers.py --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl --out /tmp/v15_dup.json
cd code && python3 -m obs llm-cost --log "$(cd .. && pwd)/.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl" --require-provider openai_compat > /tmp/v15_cost.txt ; echo rc=$? ; cd ..

# 3 完整性（三处 SHA256SUMS 全跑）
for d in v2/evidence/life_texture_cycle14 v2/evidence/d22_partner_choice v2/evidence/d12i_readings_20261024; do (cd "$d" && sha256sum -c SHA256SUMS | tail -3) ; done
sha256sum v2/evidence/d12i_readings_20261024/shots/*.png

# 4 §4 对话原文逐字 + 单行 sha（18 段全核）
python3 /tmp/verify_excerpts.py

# 5 §3 与 CYCLE-14 §3 逐行对表 + 代码行号实读
grep -n "## 三、未收口项\|^| \*\*N-4\*\*\|^| \*\*N-7\*\*" reports/CYCLE-14-20261024.md
sed -n '47,50p' code/life/planner.py ; sed -n '1009,1012p' code/orchestration/integration.py ; sed -n '1123,1127p' code/life/agent.py

# 6 commit 区间 / 游离 commit
git rev-list --count d0a320b..da5379d ; git rev-list --count d0a320b..9693b2f
git log --format='%h %an %cI %s' d0a320b..da5379d
git merge-base --is-ancestor 4e20256 HEAD ; echo rc=$?
git for-each-ref --contains 4e20256 --format='%(refname)'
git diff --name-status 4e20256 6c8a70d

# 7 脏行数与分解
git status --porcelain | wc -l ; git status --porcelain | awk '{print $1}' | sort | uniq -c
```

**我的重算件（`/tmp`，不入库、不作第二基准，仅证明可复现）**
`/tmp/v15_f1.json` = `35fe6bc3…cd43`（**与证据件同 sha**）｜`/tmp/v15_pcs.json` = `a4e90cfe…4cb3`（**同 sha**）｜`/tmp/v15_perm_D12I.json` = `4d029821…10ea`（**同 sha**）｜`/tmp/v15_cost.txt` = `76a68ed0…7830`（**同 sha**）｜`/tmp/v15_form.json` = `0e97fe58…769a`、`/tmp/v15_dup.json` = `1525986f…d83b`、`/tmp/v15_perm_cond.json` = `e8e9cdf0…6a34`（这三件与证据件 sha 不同**仅因 `--out` 路径/中间件字段差异**，**数值逐项一致**）。

---

*核验：`independent-verifier`（非作者）｜被验字节 `08a00a8f…ffdb`（456 行 / 68,391 B）｜`report_base_HEAD = da5379d`｜分档 **BLOCK（6 项）**｜本文件为只读核验结论，未修改任何被核件字节、未 commit、未 push*

---
---

# 定点复验（第二版）——**终局结论**

> **核验人**：`independent-verifier`（非作者）｜**核验时刻**：2026-10-24 04:56–04:59 (+08:00)｜`report_base_HEAD = da5379d`
> **被验字节（终局唯一基准）**：`reports/CYCLE-15-20261024.md`
> `sha256 = aa2d4f3c33ef58ab3419579b3e3fc0913267992fa098047c1c416571f8260908`｜**458 行**｜**70,393 B**｜冻结时刻 **2026-10-24 04:57:47 (+0800)**
> 三项均由我实测（`sha256sum` / `wc -l` / `stat -c%s`），与 Leader 冻结指令（04:58:42）与作者交付声明三方一致；`cmp team-workspace/artifacts/docs/cycle15-draft.md reports/CYCLE-15-20261024.md` → **逐字节相同**。
> ⚠️ **本次分档只对这份字节生效**。再动一个字节，本 PASS 即不再对应。
>
> **作废序列（我一律不下功夫、也不对其负责）**：`08a00a8f…ffdb`（首版，V1 判 BLOCK，**仅保留为 §2 diff 基准**，留档 `/tmp/cycle15_v1_frozen_08a00a8f.md`，sha 实测相符）→ `12749078…7c0f` → `72ea2f2f…885a` → `dbfae369…`（我未接触）→ `3bc51e90…bb6d`（我 04:56:15 版实测过锚与 16 处，Leader 04:58:00 已作废）→ `ce331441…bbf9`（**我从未核过这一版**，Leader 04:58:42 已作废）→ **`aa2d4f3c…0908`（本版，终局）**。
> **范围**：本版只做**定点复验**——不重跑 V1 那 22 项读数（理由见 §三-3），改为逐条核「6 BLOCK + 10 必修 + V1 后新增 4 处残留」，并用 **§2 数字串序列比对**证明「改记账层没改坏读数」。

## 定点复验结论：**PASS**

- **BLOCK 未闭合 = 0**（V1 的 6 项逐条闭合，见 §一，全部实跑取证）
- **必修未闭合 = 0**（M-1…M-10 逐条闭合，见 §二；另 V1 之后新查 4 处也全部闭合，见 §三）
- **读数被动过 = 0**（§2 区间数字串 **710 → 720**，差异 **22 项全部属代码行号与交叉引用编号**，读数类 0 变化，见 §四）

---

## 一、6 项 BLOCK 闭合核（逐条给判据命令与实测输出）

| # | 判据（我实跑） | 实测输出 | 判定 |
|---|---|---|---|
| **B-1** 件数三值 | `grep -n "12 件\|7 件未入库\|16 个文件\|22 个路径条目"` + `ls -1 v2/evidence/d22_partner_choice \| wc -l` | 全文 `12 件`=**0**、`7 件未入库`=**0**；`16 个文件` 命中 L41/L60/L77/L86/L258/L359/L360；`ls -1 … \| wc -l` = **16**；§5 L359 = 「3 件工具 + `d22` 16 个文件 + 3 件第一版读数，**合计 22 个路径条目**」 | ✅ **闭合** |
| **B-2** base 两值 / 条数 3 vs 4 | `grep -o "report_base_HEAD = [0-9a-f]\{40\}"`；`git rev-list --count d0a320b..da5379d` | 全文 `report_base_HEAD` 仅 **1 个值** = `da5379d6578d6aa78507d14372906078d1de62d4`（页首 L3 与取数表 L34 同值，完整 sha 命中 2 次）；`rev-list --count` = **4**；§1.1 标题「4 条，`d0a320b..da5379d`」；附录 A-1 `# → 4` | ✅ **闭合** |
| **B-3** sha 指向不存在字节 | `sha256sum v2/evidence/d22_partner_choice/cycle15_commit_window.md`；`grep -c 768aefd2` | 实物 = **`001314e7278400885d93959ed88a330790f071d6d27cbcfca7d2e39a5edcc1d8`**；L38 现写 `001314e7…c1d8`（全文命中 2 次 = L38 + 页首 L41）⇒ 与实物一致；`768aefd2` 命中 **0** | ✅ **闭合** |
| **B-4** 6 条 → 7 条 / 19 → 20 | `grep -c "21 条"`；`grep -n "3.2 本周期新查出\|13 + 7"`；读 L227/L266 | `21 条` = **1**，唯一命中 **L227 §3 头注**，形态为 Leader 指定的作废留痕（「早期口径曾记『21 条』（15 挂账 + 6 新查，少算 1 条，`N-14` 被漏计）；本节按可核编号实计为 22 条…仅在此留痕以备追溯」）；§3.2 = 「**7 条**」；§3.3 = 「其余 **20 条（13 + 7）**」且写「合计 = 15 + 7 = **22 条**」；L227 算式「**22 条（15 + 7）**」。另核：`全文不出现` = 2，位于附录 B **禁用词清单**（L457/L458，禁令条目本体），按 Leader 口径属范围外 | ✅ **闭合** |
| **B-5** 脏行分解错 | `date '+%F %T %z'`；`git status --porcelain \| awk '{print $1}' \| sort \| uniq -c`；`git status --porcelain \| wc -l` | **快照时刻 = 2026-10-24 04:58:27 +0800**；原始输出 `27 ??` / `2 M` / 合计 **29**；` M` = `reports/README.md` 与 `v2/evidence/d3_noiseband_bootstrap.json`。报告 L37 现写「**28 行（2026-10-24 04:46:05 实测快照；` M` 2 条 = README、`d3_noiseband_bootstrap.json`；`??` 26 条）——时点快照、事后不可复算、不构成判据**」，并附注「该数随新落盘件与提交状态变化，引用必须带时刻」。**⚠️ 该分解只对应 2026-10-24 04:46:05 那一刻，非恒真量**——04:58:27 实算 29（多出的一行是我 04:51 落盘的 `v2/evidence/cycle15_verify.md`）；报告已不再声称冻结时刻的现算值，故「复用旧快照」的错配已拆除 | ✅ **闭合**（Leader 04:58:42 第 2 条同此判据） |
| **B-6** 附录 B 状态词冲突 | `grep -n "仅观察"`；读 §2.5 F-1 行 | 附录 B（L452）「`仅观察` → **§2.1.1 第 4 条**（`top1_partner_share_max = 66.67%` 由 `P013` 主导）、§2.3 末（同项）」；新增 L451「`已验证` → §2.1/§2.2（D2.2 作者亲跑）／§2.4（算术复核）／§2.5（`sha256sum -c` + 抄录）」；§2.5 F-1 行状态词仍 `已验证`，二者**不再互斥** | ✅ **闭合** |

---

## 二、10 条必修闭合核

| # | 应改内容 | 实测 | 判定 |
|---|---|---|---|
| M-1 | 四件 → 五件 | L62「本周期实际做了什么（**五件**，逐条对到产物）」，表内 1–5 共 5 行 | ✅ |
| M-2 | 9 → 8 个结构量（两处） | L67「两臂量 **8 个结构量**」、L219「D2.2 对端选择的 **8 个结构量**」、N-13 亦 8；全文 `9 个结构量` = 0 | ✅ |
| M-3 | CYCLE-14 行号 `:13-27` → `:273-287` | `:273-287` 命中 **2**（§3 头注 L225 + `N-11`）；`:13-27` 命中 **0**；实读 CYCLE-14 该区间 = §3 表（`N-4` 在 273、`N-7` 在 287，我 `grep` 实测） | ✅ |
| M-4 | 「抄录/转抄」→「压缩摘要（非逐字）」 | `一句话事实（转抄` = **0**；L232 表头现为「（**压缩摘要，非逐字转抄**；相似度 0.29–0.67，承 CYCLE-14 §3）」；§3 头注同步（相似度 0.29–0.67 与我 `difflib` 实测区间 0.290–0.667 一致） | ✅（两处已同口径） |
| M-5 | `N-4`/`N-2` 状态词与「不重判」自洽 | `N-4` = 「**处置中**（承 CYCLE-14 §3 原表标签…）」、`N-2` = 「**未处置**（承 CYCLE-14 §3 原表标签…）」⇒ 与原表一致，不再出现「未收口」这类重述性下修 | ✅ |
| M-6 | 代码行号 | 报告写 `planner.py:47-50` / `integration.py:1011`；我实读 `sed -n '47,50p' code/life/planner.py` → `def _pick(...)` + `return options[int(sha256_hex(seed)[:8], 16) % len(options)]`；`sed -n '1011p' code/orchestration/integration.py` → `peers=pids, peer_names=peer_names)`；`sha256_hex` 在文 1 次 | ✅ |
| M-7 | §4.1 悬空残句 | 原「：① 6 轮跨 3 个时段…」已改为 L330「**案例 1 的读法（`描述性读数`，不作判读）**：① 6 轮跨 3 个时段…」⇒ 有主语、不悬空 | ✅ |
| M-8 | §2.1/§2.2「本报告重跑」二选一 | §2.5 限定语已收窄为「**§2.5 这一张表内**的数值没有一个是作者亲自算出的（注意：§2.1–§2.3 的 D2.2 读数是作者**亲自重跑** `partner_choice_stats.py` 与两个置换检验，见附录 A-5/A-6/A-6b；两处口径不同，不得合并读）」⇒ 与 §2.1/§2.2 的「本报告重跑」自洽 | ✅ |
| M-9 | §0「两份互相独立的日志」 | `两份互相独立的日志` = **0**；L25 现写「在 T0（OFF 基线）与 D12-I（ON 臂）两份**独立起跑**的日志上（**但其 114 条发起序列逐位相同**）」 | ✅ |
| M-10 | README 索引行 `N-8` 去重 | `git diff --stat reports/README.md` = **1 insertion / 0 deletion**；`git diff` 中 `N-8` 出现 **1** 次（原为 2 次） | ✅ |

**V1 之后我新查、并已闭合的 2 处**（同样实跑）：§5 原「7 件未入库产物」→ 现「合计 22 个路径条目」（`7 件未入库` 命中 0）；§3.1 原表头「转抄」→ 现「压缩摘要，非逐字转抄」（见 M-4）。

---

## 三、§2 数字串分级（「改记账层是否改坏读数」的硬证据）

用同一脚本对首版 `08a00a8f…` 与本版取 §2 区间（`## 二、达标项与产出分表` → `## 三、仍有问题`）做数字串序列比对：

- **数字串总数：首版 710 → 终版 720**（+10）
- **序列完全相同：否**；差异 **22 项**，逐项归类如下：

**格式类（22 项，全部为引用/编号，非读数）**
1. 代码行号修正：删 `55`/`56` → 增 `47`/`50`（= M-6，`planner.py:47-50`）；删 `1010` → 增 `1011`（= M-6，`integration.py:1011`）；增 `4`（= 「本报告实读该 **4** 行」）。
2. §2.5 限定语新增交叉引用编号：增 `2.5`、`2.1`、`2.3`、`2.2`、`2.1`、`2.2`（= 「§2.1–§2.3 的 D2.2 读数…」与「§2.5 这一张表」等）、增 `5`、`6`、`6`（= 附录 A-5 / A-6 / A-6b 编号）。
3. 未变的公共锚 `256`、`8`、`16`、`15` 等逐位相同（比对窗口内的上下文）。

**数值类（0 项）**：§2 区间内**没有任何**分子/分母/百分比/CI/分位/HHI/成本数字发生变化 —— 逐条列举的 `114 / 16`、`65 / 120 = 54.17%`、`42.98%`、`4.5`、`36.49% / 66.67%`、`0.2877`、`0.2522`、`0.2159`、`[0.1938, 0.2462]`、`[0.1933, 0.2455]`、`p=0.0`、`363/364/360`、`369/510`、`317/368`、`116/134`、`44/47/51` 等**全部原样**。
⇒ 按 Leader 04:52:32 第 2 条：**格式类记必修、数值类直接 BLOCK** —— 本次格式类已全部是「被要求改的那些引用」，**数值类 = 0 ⇒ 无 BLOCK**。

**核验边界（如实）**：本版**未重跑** V1 的 22 项读数（重跑只能重复证明同一件事，且 V1 已 22/22 一致、四件输出与证据件 sha 逐字节相同）；「读数没被改坏」的依据是**上面的数字串零变化**，不是重算。若发布前有人再动 §2 数值行，本 PASS 不覆盖。

---

## 四、残留说明（不阻塞，3 条，供引用者遵守）

| # | 内容 | 说明 |
|---|---|---|
| R-1 | L37 脏行数「28 行」是 **2026-10-24 04:46:05** 的快照 | 我在 **04:58:27** 实算 **29 = 2 ` M` + 27 `??`**（多出项 = 我 04:51 落盘的 `v2/evidence/cycle15_verify.md`）。**该分解只对应 04:46:05 那一刻，非恒真量**；引用必须带时刻（报告已自带该附注） |
| R-2 | `21 条` 有 **1 处**留痕（L227 §3 头注） | 属 Leader 04:54:31 裁决指定的作废留痕形态，**不是残留错账**；`全文不出现` 的 2 处命中在附录 B 禁用词清单，属禁令条目本体 |
| R-3 | 版本链共 7 版，我**完整核过首版与终版** | 中间 `3bc51e90…`（458 行 / 70,316 B）我实测过锚与 16 处（结论：16 处在其上已闭合，仅 M-9 与 B-5 快照未改），`ce331441…`（70,564 B）**我从未核**、已被 Leader 作废。**发布与留档只认 `aa2d4f3c…0908`** |

---

## 五、V1 的「不可核项」在本版仍然有效（不因 PASS 而消失）

1. **落笔时刻与脏行快照**：时点快照，事后不可重建（现已有双标注，见 R-1）。
2. **「本周期未起跑任何新批 / 成本 0」**：我无法证明「没有发生」，可核的只是区间内 4 条 commit 无 `run_batch`、`obs llm-cost` 只指向 D12-I 历史日志。
3. **`team-workspace` 04:30 被重建（`N-11`）**：只核到「原件确实不在」，时刻与动作本身不可复算。
4. **两臂发起序列「逐位相同」**：我核的是统计层逐字段相同（12 字段全等）与抽样分布同值，未逐条 diff 114 条 `(from→to)`。
5. **PNG「重跑会得到不同 sha 的等价图」**：只核已入库版本，未重跑渲染。
6. **`N-9` 的分支 `913ac4d`**：未去核该分支是否存在。

---

## 六、本次定点复验跑过的命令（可原样重放，只读、输出落 `/tmp`）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
R=reports/CYCLE-15-20261024.md
# 锚定
sha256sum $R ; wc -l < $R ; stat -c%s $R
cmp team-workspace/artifacts/docs/cycle15-draft.md $R
# B-1 / B-2 / B-3 / B-4 / B-6
grep -n "12 件\|7 件未入库\|16 个文件\|22 个路径条目" $R ; ls -1 v2/evidence/d22_partner_choice | wc -l
grep -o "report_base_HEAD = [0-9a-f]\{40\}" $R ; git rev-list --count d0a320b..da5379d
sha256sum v2/evidence/d22_partner_choice/cycle15_commit_window.md ; grep -c 768aefd2 $R
grep -c "21 条" $R ; grep -n "3.2 本周期新查出\|13 + 7" $R
grep -n "仅观察" $R
# B-5 快照三件套
date '+%F %T %z' ; git status --porcelain | awk '{print $1}' | sort | uniq -c ; git status --porcelain | wc -l
# 必修行号实读
sed -n '47,50p' code/life/planner.py ; sed -n '1011p' code/orchestration/integration.py
grep -n "^| \*\*N-7\*\*" reports/CYCLE-14-20261024.md   # → 287
# §2 数字串序列比对（脚本内联：re.findall(r'\d+(?:\.\d+)?%?') + difflib.unified_diff）
```

---

*定点复验：`independent-verifier`（非作者）｜被验字节 `aa2d4f3c…0908`（458 行 / 70,393 B，冻结 04:57:47）｜**分档 PASS（0 BLOCK / 0 必修未闭合 / 读数 0 变化）**｜第一版 `BLOCK（6 项）` 段落按 Leader 要求**原样保留**，未删未改｜本文件只读核验，未修改任何被核件字节、未 commit、未 push*
