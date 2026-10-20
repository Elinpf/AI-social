# v0-anchor 基线复现证据（R6 / F-4·F-4b·F-3）

> 定位：**只读复现**。本目录不产生任何新批、不触碰他人 WIP、**不作为本批真跑凭证**。
> 目的：给出「同脚本 + 同输入 ⇒ 同读数」的直接凭证，供报告引用 v0 基线时绑 sha。
> 执行人：batch-evidence-runner｜执行时刻 2026-10-20T20:02:55→20:02:58 (+08:00)｜HEAD `fcf42bf931fb239867886674f68db822d1a162e2`

## 1. 复现对象

锁定记录：`v2/evidence/d5_v0anchor_lock.md`（ADMITTED / strict / evidence，2026-10-20 17:55 锁定）

| 项 | 值 |
|---|---|
| 批次目录 | `v2/evidence/run_d2_before_n16_seed42/` |
| `run.jsonl` sha256 | `c1f86bf61f62b3a0ce8e17e0c2312791cf0262381cd2120c2a63c9b6258963cf` |
| `meta.json` sha256 | `165c002a9d0f0241cf3639115d8f7a5271d48d1b4ef02e4537c6f9af5aed61b5` |
| 规格 | n=16 × rounds=84 × seed=42，真 LLM（openai_compat / DeepSeek-Flash） |

## 2. 命令（原样见 `command.txt`）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 tools/d5/dialogue_metrics.py \
  --log  v2/evidence/run_d2_before_n16_seed42/run.jsonl \
  --meta v2/evidence/run_d2_before_n16_seed42/meta.json \
  --out-json v2/evidence/r6_f4_baseline_repro/v0_metrics.json \
  --out-md   v2/evidence/r6_f4_baseline_repro/v0_metrics.md
```

原始 stdout/stderr、rc、起止时刻：`raw_stdout.txt`（rc=0，耗时 ≈3 s）。

## 3. 读数（`baseline_readout.txt`）

| 指标 | 分子 | 分母 | 判级 |
|---|---|---|---|
| F-4 修复闭环 | 0 | 5（张力事件） | **probe**（分母 <30，只报事件数，不做百分比结论） |
| F-4b 修复时滞 `mean_lag_msgs` | — | 0（无闭环样本） | 不可计算（null），如实记录，不补 0、不估 |
| F-3 情绪呼应 | 1 | 6（相邻对） | **probe**（分母 <30） |
| 准入 | — | — | `ADMITTED / strict / evidence`，B-7…B-21 全 PASS |

## 4. 复现结论（含一条必须诚实标注的差异）

- **全部指标数值逐字段一致**：与锁定产物 `v2/evidence/d5_metrics_v0anchor.json` 做 JSON 全树逐字段比对，**差异条目 = 2 条，且都不在指标数值上**：
  1. `/inputs/script_sha256`：锁定版 `d7e2da17…f97306` ≠ 当前工作树 `371c9fa1…de9751`；
  2. `/assertions`：当前脚本新增的断言区块（`msg_id_n/msg_id_unique/msg_uid_n/…`），锁定版没有该键。
- ⇒ 因此**不能**写成"与 v0 锁定时同一份脚本字节级复现"。证确表述是：**同一输入日志下，当前脚本 `371c9fa1…` 复算出的 F-4 / F-4b / F-3 / 准入判定与锁定时数值逐字段相同**（脚本在 v0 锁定后仍有演进，新增的是断言与 sha 字段，本日志上未改变任何指标数值）。
- **字节级 sha 不同是预期的**：输出 json/md 内含输出路径字符串与新断言区块，故 `v0_metrics.json` sha = `169e1c2c…`、锁定版 = `e8c8409e…`；比对必须做**字段级**，不做文件字节级。这一点写在这里，防止后续有人拿 sha 不相等误判为"复现失败"。
- 另：先前一次写入 `/tmp` 的独立复跑（20:02 前）得到同样数值，非本目录产物，仅作旁证。

## 5. 本目录文件与 sha256

完整清单见 `sha256sums.txt`。要点：

| 文件 | sha256 |
|---|---|
| `command.txt` | `a72daa0d…c489aae2` |
| `raw_stdout.txt` | `1bec8816…d5dc6450` |
| `baseline_readout.txt` | `52cca01d…c5a69d49` |
| `v0_metrics.json` | `169e1c2c…b88e0a99` |
| `v0_metrics.md` | `2ab8d2f9…4b661b1b` |
| `obs_llmcost_v0_envcheck.txt` | `ff445dab…d724795c` |

`obs_llmcost_v0_envcheck.txt` 是**环境可用性旁证**（对 v0 旧日志只读复跑 `python3 -m obs llm-cost --log … --require-provider openai_compat` → rc=0、`by_provider={"openai_compat":2905}`、`degraded=0`、`problems=[]`），证明验真链路本身可用。**它不是本批真跑凭证**——本批的真跑验真必须在**本批自己的日志**上重跑并另行留档（leader 裁决 1）。

## 6. 不得越界的三条

1. 本目录读的是 v0 历史日志，**不可**被当作"新机制有效"的任何证据。
2. F-4/F-3 分母均 <30 ⇒ 只报事件数 + 分母、标 `probe`，不进摘要与结论要点。
3. 复算仅覆盖 `dialogue_metrics.py` 的词表口径；**机制自报层**（若 T2 落结构字段）另出，两层不相加、不互证。

## 7. 事件级枚举（F-4/F-4b）——`f4_events_v0.md` / `.json`

脚本：`tools/d5/f4_repair_evidence.py`（当前版本 sha256 `4e04efdfff49da344758fe02de24f3c831f1153076c459102ab41c6a288c2eb0`）
命令（同版本口径，`--metrics-json` 指向本目录 `v0_metrics.json`）：

```bash
python3 tools/d5/f4_repair_evidence.py \
  --log v2/evidence/run_d2_before_n16_seed42/run.jsonl \
  --metrics-json v2/evidence/r6_f4_baseline_repro/v0_metrics.json \
  --out-json v2/evidence/r6_f4_baseline_repro/f4_events_v0.json \
  --out-md   v2/evidence/r6_f4_baseline_repro/f4_events_v0.md
```

- **交叉校验通过（rc=0）**：枚举计数与 `dialogue_metrics.py` 的 `tension_events=5 / repaired=0 / closed_loop_rate=0.0 / mean_lag_msgs=null` 逐项一致；不一致脚本会 rc=4 且不得引用。
- v0 的 5 条张力事件分布：dm 3 / public 2 / group 0，涉及 5 个不同线程；**全 5 条均未闭环**（其后 8 条内无修复词）⇒ F-4b 无样本，`mean_lag_msgs=null`。
- **`msg_uid` 在 v0 为 0/187 覆盖**：v0 是 `legacy` 线程结构（无 `thread_id`/`msg_uid`）。第三方核对请用 `seq` + **日志行号**（表内已给）。新批（D2 之后为 `explicit` 结构）会有 `msg_uid`，同一脚本会一并输出。

### 7.1 一条必须主动交代的口径噪声（人工读原文发现）

逐条读原文后确认：**5 条里有至少 2 条不是真实人际张力，是词表子串命中的假阳性**：

- `#1`（`seq=189`）「…**怕**什么。」——反诘语气命中负向词「怕」，实为自言自语，无对象；
- `#5`（`seq=116139`）「…头疼脑热…」——成语命中负向词「疼」，实为提义诊建议，非冲突。

⇒ 结论必须写成「**词表口径**下 v0 有 5 条张力事件、0 条闭环」，**不能**写成「v0 有 5 次真实冲突」。词表口径的作用是**跨臂同规则可比**，不是"真实张力计数"。若报告要谈真实张力，需另做人工/LLM 判读标注，并明确标为人工判读，不混入自动指标、也不与词表口径相加。本轮新批同理：先报词表口径，人工复核只作注。


## 8. 人工判读层（并列注记，非自动指标）——`f4_manual_judge_v0.md` / `.json`

判据（**先写后判**）：`prereg_f4_manual_judgement.md`（sha256 `1f2c3316…8ec265bf7`）；执行器 `tools/d5/f4_manual_judge.py`（sha256 `a1778968…1f6647e9`）；
判读数据 `judgements_v0.json`（sha256 `6184b8f5…67af504d`）；输出 `f4_manual_judge_v0.{md,json}`（json sha256 `a601053d…b860a9`）。

```bash
python3 tools/d5/f4_manual_judge.py \
  --events-json v2/evidence/r6_f4_baseline_repro/f4_events_v0.json \
  --judgements  v2/evidence/r6_f4_baseline_repro/judgements_v0.json \
  --prereg      v2/evidence/r6_f4_baseline_repro/prereg_f4_manual_judgement.md \
  --arm "v0-anchor (run_d2_before_n16_seed42)" \
  --out-json v2/evidence/r6_f4_baseline_repro/f4_manual_judge_v0.json \
  --out-md   v2/evidence/r6_f4_baseline_repro/f4_manual_judge_v0.md
```

**并列两套口径（两个分母都写，都不换算百分比）**

| 口径 | 张力事件（分母） | 已闭环（分子） |
|---|---|---|
| 词表口径 | **5** | **0** |
| 人工判读口径 | **1** | **0**（真张力 `seq=86111`，词表口径下未闭环） |

- 5 条中 **4 条判为词表噪声**：反诘+自言自语（`seq=189`「怕什么」）、对第三方吐槽转述（`seq=37604` 吐槽不在场配偶）、安抚/鼓励语（`seq=59296`「别怕问错」）、成语（`seq=116139`「头疼脑热」）。不可判 0 条。
- **效力上限**：本条为**第一标注者**的判读；独立第二标注者（repo-state-surveyor）的判读与一致性核对见 §9。任何情况下都**不得**称「人工校验通过」。
- **不得违反**：①不得写「人工判读 X% 闭环」（分母<30，百分比不成立）；②人工口径不得替换词表口径做跨臂对比；③本层只描述"词表口径分母里有多少噪声"，不得用于证明机制有效。
- 代码强制：每条张力事件必须有判读结论（缺一条 rc=5 拒出数）、verdict 仅 real/noise/undecidable、不许新增事件。

## 9. 两位标注者一致性核对——`f4_interrater_v0.md` / `.json`

第二标注者：`repo-state-surveyor`（独立、盲包、只看规则摘录）；其 verdict：`team-workspace/artifacts/annotation/verdict_P-A1_second.json`（sha256 `dd650c7a…57b6f1`）。
核对器：`tools/d5/f4_interrater.py`（可重跑；内置三重硬校验：seq 集合必须完全相同、第二标注者自报的包/规则 sha 必须与实物一致、verdict 值域合法）。

```bash
python3 tools/d5/f4_interrater.py \
  --mine   v2/evidence/r6_f4_baseline_repro/judgements_v0.json \
  --other  <team-workspace>/artifacts/annotation/verdict_P-A1_second.json \
  --packet <team-workspace>/artifacts/annotation/annotation_packet_events.json \
  --arm "v0-anchor (run_d2_before_n16_seed42)" \
  --out-json v2/evidence/r6_f4_baseline_repro/f4_interrater_v0.json \
  --out-md   v2/evidence/r6_f4_baseline_repro/f4_interrater_v0.md
```

**结果：一致 5 / 不一致 0**；Cohen's κ = 1.0，但 **n=5 极小 ⇒ κ 不稳定，只作参考，不得当可靠性证据**；结论以「一致 5 / 不一致 0 + 分歧明细（无分歧）」为准。

**两条限制必须随引用一起写**：
1. 「判据 §4 示例与本批个别条目同形，该部分标注存在部分引导，一致率对这几条不构成独立验证」；
2. 「两位标注者看到的是同一批判定条款（T1–T4 同源同版本），差异仅在背景说明与上下文信息」——不是两套规则。
3. 本核对**不改变**任何报告值：词表口径 5/0、人工判读口径 1/0 照旧各自报，不相加、不互证。

## 10. 同脚本版本纪律落地 + 两个必须知道的审计事实

**同版本重算**：本轮两臂与基线统一使用 `tools/d5/dialogue_metrics.py` sha256 = `5fede53838b183eae48bd3c3f922c17499338d2ae74349f8e444119e5580c6fb`（工作区版，含 `prompt-linguist` 未提交改动）。基线重算产物：`v0_metrics_at_5fede538.json/.md`。

**与 HEAD 锁定版逐字段比对**（`git show HEAD:v2/evidence/d5_metrics_v0anchor.json`，sha `e8c8409e…a88101`）：**差异 6 条，全部在 L 系列与元信息，F 系列零差异**：
1. `L-12_peer_name_address_rate` 被拆为 `L-12_peer_mention_rate`(L-12a) / `L-12b_peer_address_rate`(L-12b)，新增 `L-12_definitions`（各 1 条）；
2. `/inputs/script_sha256`：`d7e2da17…` → `5fede538…`；
3. `/assertions` 区块新增。
**F-4 = 0/5、F-4b = null、F-3 = 1/6 在两侧逐字相同** ⇒ 本轮 F 系列读数与锁定版口径一致。

**审计事实 1（重要，勿误引）**：工作区的 `v2/evidence/d5_metrics_v0anchor.json` 当前是 **`M`（被他人重新生成）**，sha `bba47c2b…5ca0`，**≠ HEAD 版 `e8c8409e…a88101`**。引用"锁定基线"必须用 **HEAD 版 sha `e8c8409e`**；工作区那份是被新脚本重算出来的，**不是锁定物**，不得引用。

**审计事实 2**：`tools/d5/dialogue_metrics.py` 的改动未提交，其字节物证已冻结为 `v2/evidence/r6_f4_arm_open/tools_d5_diff_at_pin_5fede538.patch`（sha256 `43821eb1…1a7e53`），附字段级核查（无 F-4 相关行变动）。T5 时该改动须**单独入库并写明来源 `prompt-linguist`**，不隐藏、不冒领。
