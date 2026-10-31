# R41b · 公开面接话（public-face reply）**首次验证批实测**

> 撰写：`report-writer`｜数据来源批：`r41v`（执行人 `batch-operator`）｜撰写时刻：`2026-11-01T02:56+08:00`
> **与 `reports/R41-*.md` 的关系**：`reports/R41-public-talk.md` 是**设计/结构分析**（机制实现、OFF 等价性的静态论证、A 前基线读数、验证批因端点被占而**未执行**）。本报告是**同一维度的首次验证批实测**：真 LLM 两臂 OFF/ON 各跑一次，给出可复算读数、真实对话原文与现场截图。R41 的代码身份（`2af557f`）与本批跑的代码身份（预登记 commit `f365255`）**不是同一个 sha**，两者关系见 §1.3，不可互相顶替。
> **编号说明**：`reports/` 下已占用 `R41`/`R42`（`R41b` 未被占用，查法见附录 B·B0）。本报告沿用与 R41 同族的 `R41b`，不改任何既有编号。
> **版本与哈希（核验用）**：本文件在 `2026-11-01T02:56:31` 将任务标 `completed` 之后，又发生过**两次仅措辞/登记的编辑**——`02:57:09` 改 §⑤ 第 5 条一行（工具侧登记项，Leader 指定形态）、`02:57:21` 在 §2.3 增补一段「按代码语义的直读口径是 `place×slot`」（`batch-operator` 提供 `code/life/public_talk.py:116` 引文）。**两次编辑均未改动任何数字、判据与结论**；核验请以 `sha256sum reports/R41b-public-talk-verify.md` 的实测值为基准（**本文件不内嵌自身哈希**——自指会立刻失效），并与核验台账 `verify.md` 记录的值比对。
> **证据总表**：`team-workspace/evidence/r41v/summary.md`（`batch-operator` 的跑批与度量汇总）与 `handoff-to-report-writer.md`。本报告所有数字均可在这两份或 `v2/evidence/r41v_*` 原件中找到出处，逐条出路见 §2 表内「出处」列与附录 B。

---

## 一句话结论

**机制层：确认接通**——ON 臂 30 条公开消息中 **7 条**带非空 `reply_to`、`participants` 长度 2、`turn_index=1`、且与目标消息同 `thread_id`；OFF 臂同口径 **0/24**。
**效果层：不可判**——主判据 `R41V-C1` 因两臂分母 `n_off=24 / n_on=30` 未同时 ≥30，按预登记 §3.2 **只报计数、不报比率、不报区间**，因此**不宣称「有效」、不写「显著」、不写「生活气息提升」**。
**同时登记一处功能级缺陷**：场所配额 `MAX_PER_PLACE_PER_SLOT=2` 在结果侧被突破（`round×day×slot×place` 达 **3**、跨 round `day×slot×place` 达 **5**、忽略 day 的 `place×slot` 达 **9**、只数接话达 **4**），`R41V-C4` 判**不成立**。

---

## ① 做了什么

### 1.1 两臂参数与唯一 env 差异

| 项 | OFF 臂 | ON 臂 |
|---|---|---|
| 输出目录 | `v2/evidence/r41v_public_talk_n16r24_s42/off/` | `v2/evidence/r41v_public_talk_n16r24_s42/on/` |
| 内层命令 | `bash tools/d2/run_batch.sh --out-dir .../off --seed 42 --agents 16 --rounds 24 --flush-every 2 --side-root /tmp/r41v_off_n16r24_s42_side` | 同，`--out-dir .../on`、`--side-root /tmp/r41v_on_n16r24_s42_side` |
| 启动方式 | `setsid`（`tools/public_talk/launch_r41v.sh off`） | 同（`... on`） |
| **`HITT_DIALOGUE_PUBLIC_REPLY`** | **不存在**（`存在性判定: NO`） | **`1`**（`存在性判定: YES`，`开关断言: PASS`） |
| `HITT_LLM_PROVIDER` / `HITT_WORLD_SEED` | `openai_compat` / `42` | `openai_compat` / `42` |
| 起跑 preflight | `PASS ... concurrency=0 frozen_tree=clean`（`2026-11-01T02:06:44`） | `PASS ... concurrency=0 frozen_tree=clean`（`2026-11-01T02:28:47`） |
| 禁改区改动数 | `git status --porcelain -- code/life code/orchestration code/config code/engine` ⇒ **0 行** | 同，**0 行** |

**唯一语义差异 = `HITT_DIALOGUE_PUBLIC_REPLY`**（`--seed/--agents/--rounds/--flush-every` 相同；`--out-dir/--side-root` 只是路径，不含语义）。
开关生效证据链（ON）：`on/switch_proof.txt`（`SET（值='1'）`/`存在性判定: YES`/`开关断言: PASS`）+ `on/host.log` 的 `INNER=... export ... HITT_DIALOGUE_PUBLIC_REPLY=1 ...` + `on/launch_evidence.txt`。
⚠ **工具侧已知缺口**：`meta.json.switch_effective` **不含** `HITT_DIALOGUE_PUBLIC_REPLY`（`tools/d2/emit_run_meta.py` 的开关账本未登记该开关）⇒ 开关生效**不能**用 `meta.switch_effective` 证明，只能用上述 launch 证据 + 行为差。本轮按纪律未改 `code/`。

### 1.2 预登记卡、代码身份、两臂日志 sha256

| 项 | 值 | 出处 / 取法 |
|---|---|---|
| 预登记卡 | `v2/refs/prereg-r41v-public-talk-verify.md` | 路径本身 |
| 预登记 commit | `f365255faf77141e33da9bb170850cf55d5b121c`（`2026-11-01T02:06:40`，`129 insertions`） | 取法：`git log -1 --format='%H%n%cI' -- v2/refs/prereg-r41v-public-talk-verify.md` |
| `frozen_sha`（两臂同值） | `f365255faf77141e33da9bb170850cf55d5b121c` | `{off,on}/frozen_sha.txt` |
| 时序 | prereg commit `02:06:40` **<** OFF `start_epoch=1793470004`（`02:06:44`） **<** ON `start_epoch=1793471328`（`02:28:48`） | `{off,on}/start_epoch.txt` + `date -d @<epoch> -Iseconds` |
| **OFF `run.jsonl` sha256** | **`50def26301c3761b30670d26b3b1fdd4d1af8aac9c26c5000197733aa88b0ef8`**（sha8 `50def263`） | `off/run_jsonl_sha256.txt`、`r41v_public_talk_readings/compare.json:arms.off.log_sha256` |
| **ON `run.jsonl` sha256** | **`c8a7f546238ad801129708fd9a8f9a4676b28702709d77440ea7769f8ecb5c5f`**（sha8 `c8a7f546`） | `on/run_jsonl_sha256.txt`、`compare.json:arms.on.log_sha256` |
| `meta.json` sha256 | off `aca5dce9…4afef` / on `24193383…c5243` | `compare.json:arms.*`、`summary.md` §3 |
| 收批 rc / 行数 / 事件数 | off `rc=0`、`33853` 行、`meta.events=33853`；on `rc=0`、`34090` 行、`meta.events=34090` | `{off,on}/run_batch.rc`、`run_jsonl_sha256.txt` 尾两行注释、`meta.json` |

### 1.3 与 R41 的代码身份关系（不可混用）

- R41 报告里的实现 commit 是 `2af557f`（`code/life/public_talk.py` 首次落地 + `agent.py` 五处改动，`2026-10-31T16:16:12`）。
- 本批**两臂都是** `frozen_sha=f365255`（= 预登记 commit，`2026-11-01T02:06:40`），`meta.code_sha` 两臂均为 `f365255f…`。
- **祖先关系已实测**：`git merge-base --is-ancestor 2af557f f365255` ⇒ **成立**（`2af557f` 是 `f365255` 的祖先）⇒ 本批跑的树**包含** R41 的实现，但**不是**只含它（中间还叠加了其他改动）。判定：本批代码身份**由 `frozen_sha.txt` + `meta.code_sha` 双份钉住**；引用 R41 的 `2af557f` 说明"实现从哪来"，涉及"这一批到底跑了什么"时必须引 `f365255`。**两者不可互相顶替**。

### 1.4 真跑验真（`obs llm-cost`，rc=0）

| 项 | OFF | ON |
|---|---|---|
| `llm_cost.rc.txt` | **0** | **0** |
| `provider_guard` | `{"by_provider":{"openai_compat":2252},"ok":true,"problems":[]}` | `{"by_provider":{"openai_compat":2255},"ok":true,"problems":[]}` |
| `total` | `calls=2252, tokens_in=152748, tokens_out=139293, tokens_total=292041, cached=1452, degraded=0, thinking=425` | `calls=2255, tokens_in=163625, tokens_out=146130, tokens_total=309755, cached=1387, degraded=0, thinking=425` |
| `duration_sec` | `1109` | `1161` |

出处：`{off,on}/llm_cost.txt`（`obs llm-cost --require-provider openai_compat` 的实际输出）、`{off,on}/meta.json`。

### 1.5 一次主动中止（方法学的一部分，不是"不算数的事故"）

首版 OFF 臂在 `02:05:00` 起跑后，Leader 于 `02:06` 追加「预登记必须单独 commit 且 commit 时间早于起跑」的要求 ⇒ 该前提物理上无法满足 ⇒ **主动中止并重起**：`kill -TERM -4168023`（setsid 会话组），中止时 `run.jsonl` 34 行且 `LLM_CALL=0`（**真实 token 消耗 = 0**），目录改名 `…/off_ABORTED_prereg_commit_before_start/` 并附 `ABORT_NOTE.txt`。
**该目录不是本报告任何读数或截图的来源**；重起的 OFF 臂才是（`start_epoch=1793470004`）。

---

## ② 有哪些提升

> 读法：`判定` 列按预登记 §3.2 口径；`不可判` ≠ `无效` ≠ `有效`。**分母 < 30 一律不报比率、不报区间**，只报 `k/n` 计数；`probe_threshold_denominator=68`，本轮两臂分母都 < 68 ⇒ 即使将来补齐 30 的最小线，结论也只能写方向性。

### 2.1 判据表（C1–C5）

| 判据 | 定义（预登记原文口径） | OFF 读数 | ON 读数 | 置信区间 | 判定 | 出处 |
|---|---|---|---|---|---|---|
| **R41V-C1**（主判据） | `p_on − p_off` 的 Newcombe 95% **下界 > 0**，且 `k_on ≥ 1`、`k_off = 0`；分子 = `reply_to_forms.real_message_id` | `k_off = 0 / n_off = 24` | `k_on = 0 / n_on = 30` | **`null`（不报）**——两臂分母未同时 ≥30，按预登记 §3.2 抑制比率与区间 | **不可判（分母不足）** | `compare.json:verdicts.R41V-C1_main_rate_diff`（`judgeable=false`、`newcombe95=null`、`p_*=null`）、`arms.*.reply_real_message_id` |
| **R41V-C2**（OFF 等价性·结构侧） | OFF：`k_off = 0` 且 `pub_out_degree_zero = true` | `k_off=0`；`pub_out_degree_zero=true`；`isolated_nodes=true`；`turn_index={0:24}`；`participants_len={1:24}`；`place` 非 null **0/24** | —（本条只判 OFF 臂） | 无分母，仅描述性 | **达标** | `compare.json:verdicts.R41V-C2_off_equivalence`、`arms.off.*` |
| **R41V-C3**（place 可判性解锁） | ON 臂 place 非 null 覆盖 100% ⇒ `UNVERIFIED`→可判；OFF 仍 `UNVERIFIED` | `place_adjacency.status=UNVERIFIED`（`place_value_histogram={"null":24}`、`nonnull_place_records=0`） | `place_adjacency.status=MEASURED`（`denominator_pairs=29`、`numerator_same_place_pairs=11`）；place 非 null **30/30（100%）**、`records_missing_place=0/30` | 无分母，仅描述性（比率因 29<30 被尺子抑制：`ratio_same_place=null`） | **达标** | `readings_{off,on}.json:place_adjacency.status`、`readings_on.json:schema_gate.key_presence.MSG_PUBLIC.place=30`、`compare.json:verdicts.R41V-C4_quota_guard.observed.on.records_missing_place=0`、本报告附录 B·B3 独立复算（30/30 与 0/24；`evidence-verifier` 独立复算同值）。⚠ **不使用** `place_adjacency.coverage`（compare.json 里 `coverage_on`/`coverage_off` 均为 `null`——该字段在 v2 尺子中不存在，不得引用） |
| **R41V-C4**（有界配额护栏） | 两臂 `MAX_PER_PLACE_PER_SLOT ≤ 2` 且 `MAX_PER_AGENT_PER_SLOT ≤ 1` | `max_pub_per_place_round=0`、`max_pub_per_place_slot=0`、`max_replies_per_agent_slot=0`（place 全 null ⇒ `place_quota_status=not_applicable`） | **多粒度越界（见 §2.3）**：`round×day×slot×place` 最大 **3**、`day×slot×place` 最大 **5**、忽略 day 的 `place×slot` 最大 **9**、**只数接话**的 `place×slot` 最大 **4**；`(author,slot)` 接话最大 **1**（未越） | 无分母，仅描述性 | **不成立（真实越界）** | `compare.json:verdicts.R41V-C4_quota_guard.observed.{off,on}`（尺子两字段：`max_pub_per_place_round`=3、`max_pub_per_place_slot`=5）＋ §2.3 独立复算＋附录 B·B4 |
| **R41V-C5**（非塌陷） | ON 的 `MSG_PUBLIC` 条数 ≥ OFF | `n_off = 24` | `n_on = 30`（+6） | 无分母，仅描述性 | **达标** | `compare.json:verdicts.R41V-C5_no_collapse`、`arms.*.msg_public_instances` |

**C4 的越界要写清区别**：实现是**逐 agent 决策时点**判配额（`code/life/agent.py:1152` 附近的 `place_quota_ok`；同一 round 内 `visible_events` 上界 = `state.round`，同轮他人刚落的消息对后来的接话者不可见），且**自发公开消息不走这道闸**、多 agent 决策不同步，于是两个接话者（`seq 487` P001、`seq 613` P003）在各自决策时都看到「已存在 1 条 < 2」而放行；**结果侧** `round1/day0/morning/farm` 实际 3 条。这不是"随机波动"，也不是"实现完全没写配额"——**是"决策时点合规、聚合结果越界"的口径差**，属**功能级**（有界性）问题，**不是**度量问题。

### 2.3 C4 的四种粒度（越界量随分组口径变化，必须写清用哪个）

| 分组口径 | 数的是什么 | ON 实测最大 | 出现位置 | 出处 |
|---|---|---|---|---|
| `round × day × slot × place` | 全部 `MSG_PUBLIC` | **3** | `round1/day0/morning/farm`（亦 `…/school`、`round3/day0/afternoon/bank`） | `compare.json:…observed.on.max_pub_per_place_round=3`；附录 B·B4 |
| `day × slot × place` | 全部 `MSG_PUBLIC`（跨 round 累计） | **5** | `day0/afternoon/bank` | `compare.json:…observed.on.max_pub_per_place_slot=5`（`worst_place_slot`）；附录 B·B4 |
| `place × slot`（**忽略 day**） | 全部 `MSG_PUBLIC`（跨天累计） | **9** | `bank/afternoon`（次高 `school/morning` = 8） | 附录 B·B4 独立复算（`核验方 evidence-verifier 独立复算同值`） |
| `place × slot`（**只数接话**，`reply_to` 非空） | 接话条数 | **4** | `school/morning`（次高 `farm/morning` = 2） | 附录 B·B4 独立复算（同上） |
| `author × slot` | 单 agent 接话条数 | **1** | 全臂最大即 1 | 附录 B·B4；`compare.json:…observed.on.max_replies_per_agent_slot=1` |

**读法**：预登记写的是「**同 place × 同 slot 内公开消息总数至多 2 条**」。按这个字面，`place×slot`（忽略 day）是 **9/2**、`day×slot×place` 是 **5/2**、最小粒度 `round×day×slot×place` 是 **3/2**——**四种粒度全部越界**，只是越界倍数不同。`MAX_PER_AGENT_PER_SLOT=1` 这一侧**没有越界**（最大 1），必须与场所侧分开写，不能一锅端成"配额全废"。

**按代码语义的直读口径是 `place×slot`（忽略 day）**：`code/life/public_talk.py:116` 的 `public_count_at()` 判定条件为
`if p.get("slot") is not None and str(p.get("slot")) != str(slot_id.split("-", 1)[-1]): continue`——它**只比对 `place` 与 `slot`，不按 `day` 过滤**（`git show f365255:code/life/public_talk.py | sed -n '116p'` 与本工作树同文）。因此**代码自己的配额尺子就是「`place × slot`，不区分 day」**，`day×slot×place` / `round×day×slot×place` 是**多加了一个维度**的更细分组。直读结果：**全部公开消息 9（`bank/afternoon`）、只数接话 4（`school/morning`），两者均 > 2 ⇒ C4 不成立的结论不变，且按代码语义看越界幅度更大**。

### 2.2 描述性读数（**`not_a_judgment=true`，不进任何判定**）

| 量 | OFF | ON | 说明 / 出处 |
|---|---|---|---|
| `reply_to` 形态 | `{json_null:24, other:0, real_message_id:0}` | `{json_null:23, other:7, real_message_id:0}` | `arms.*.reply_to_forms`；ON 的 7 条落 `other` 是**尺子口径**所致，见 §3.1 |
| `reply_to` **非空条数** | **0/24**（无分母之外的口径：分母即该臂 M实例） | **7/30** | `compare.json:descriptive.reply_to_semantics_{off,on}.pub_with_nonnull_reply_to`；`not_a_judgment=true` |
| `reply_to` 命中真实 `msg_uid` 且与目标同 `thread_id` | 0/24 | **7/7** | 同上 `reply_to_is_msg_uid_hit_and_same_thread_id=7`；目标类型全为 `MSG_PUBLIC`（`target_types` 4 个目标：`42:167`/`42:189`/`42:19241`/`42:19807`） |
| `pub_out_degree_reply_nonnull` | 0 | **7** | `arms.*.msg_graph_degree` |
| `distinct_thread_ids`（`each_msg_owns_thread`） | `24`（`true`） | `23`（`false`） | `arms.*.thread_ids_distinct` |
| **多轮公开 thread 数**（线程内 `MSG_PUBLIC` > 1 条） | **0 / 24** | **4 / 23**（`TH-P015-PUB-0-0`、`TH-P013-PUB-0-0`、`TH-P005-PUB-12-0`、`TH-P013-PUB-12-0`） | 附录 B·B3 独立复算（`核验方 evidence-verifier 独立复算同值`） |
| `payload.ctx.public_reply` 键存在条数 | **0 / 24** | **7 / 30** | 附录 B·B3 独立复算（同值） |
| `turn_index` 直方图 | `{0:24}` | `{0:23, 1:7}` | `arms.*.turn_index_histogram` |
| `participants` 长度直方图 | `{1:24}` | `{1:23, 2:7}` | `arms.*.participants_length_histogram` |
| 结构缺口（**上界口径**）`by_message`：全部非作者候选都被拒的条数 / `MSG_PUBLIC` 条数 | `type_whitelist_blocked=24/24`；`best_case_place_blocked=24/24` | `type_whitelist_blocked=30/30`；`best_case_place_blocked=**0**/30` | `compare.json:descriptive.struct_gap_*`；`co_present_is_upper_bound=true`，**不得读成实测** |
| 结构缺口 `by_pair`：被拒判定对 / `MSG_PUBLIC 条 × 非作者候选 agent` | `360/360` | `450/450`（type 白名单）；`best_case_place_blocked=0/450` | 同上 |

**ON 臂 `type_whitelist_blocked` 仍是 30/30 并不矛盾**：`life.dialogue_threads.is_replyable()` 本身未改（仍硬编码 `MSG_DM`/`MSG_GROUP`），R41 是在 `agent.py` 的**调用点**用 `PT.enabled()` 旁路。若把 30/30 读成「ON 也没接线」就是误读。

---

## ③ 仍有问题

### 3.1 C1 判不出来：分母不足是主因，尺子口径是次因（后者已被 Leader 裁定不开 amendment）

- **分母不足（主因，硬）**：`n_off=24`、`n_on=30`，未同时 ≥30 ⇒ 预登记 §3.2 触发「只报计数」。预登记分子口径下 `k_off=0`、`k_on=0`——`k_on=0` **不表示「没有接话」**，只表示「按 `real_message_id` 这个形态分类，命中数为 0」。
- **尺子口径不一致（次因，已裁定不换分子）**：`tools/public_talk/public_talk_metrics.py:281` 用 `MSG_PUBLIC` 的 **`msg_id`** 集合判 `real_message_id`，而 `reply_to` 实际存的是 **`msg_uid`**（形如 `42:189`）⇒ 真实接话 7 条被归入 `other`。用日志自身核对（`compare.json:descriptive.reply_to_semantics_on`）得 `pub_with_nonnull_reply_to=7`、`reply_to_is_msg_uid_hit=7`、`同 thread_id=7`。
- **Leader 裁定（本轮遵循）**：**不开 prereg amendment**。该 7 条属**口径偏离预登记字段**（`real_message_id` → `msg_uid` 命中），**正式采用这个数必须先走 prereg amendment**；本轮已被裁定不开，理由是换了修正分子后仍是 `k_on=7/30` vs `k_off=0/24`，**分母依旧不足**，判定不会改变。因此上述 7 条只能作为 **`not_a_judgment=true` 的「尺子待修」证据**出现，**不得**替代主判据、**不得**据此写「有效」、**不得**报出 23.3% 之类比率。
- 唯一允许的表述：**「本轮 C1 不可判（分母不足）；不做任何比率或显著性陈述。」**

### 3.2 检验力：本批规模与判据门槛结构性错配

- `M实例` 这个统计单位决定分母增长很慢：`n16 × r24` 的单臂只产出 `24`（OFF）/ `30`（ON）条公开发言，约 **1.0–1.25 条/round**。
- 由此可算（算术，不是拟合）：要把单臂分母做到预登记报比率红线 **30**，本轮 ON 臂恰好压线（30），OFF 臂差 6 条；要做到 `probe` 解除线 **68**，按 ≈1.25 条/round 需 **≈55 rounds**（68 / 1.25 ≈ 54.4），或等价地抬高并发/公开面剂量。
- 结论：**本轮规模下检出 10pp 级差异的检验力不足**（`probe=true` 两臂皆成立）。这不是"没做"，是"这个体量判不了这个效应量"。

### 3.3 两臂**不是**最小扰动（归因边界必须写死）

| 量 | OFF | ON | 差 |
|---|---|---|---|
| `run.jsonl` 行数 / `meta.events` | 33853 | 34090 | **+237** |
| `calls` | 2252 | 2255 | +3（`dialogue` 191→193、`reflect` 90→91） |
| `tokens_total` | 292041 | 309755 | **+17714** |
| `judge` tokens | in 47583 / out 91315 | in 51730 / out 94477 | **+4147 / +3162** |
| `importance` tokens | in 2210 / out 32456 | in 2312 / out 34359 | +102 / +1903 |
| `plan` tokens | in 0 / out 0 | in 1447 / out 1154 | +1447 / +1154 |
| `duration_sec` | 1109 | 1161 | +52 |

出处：`{off,on}/llm_cost.txt`（`engine_log.by_purpose`）、`{off,on}/run_jsonl_sha256.txt` 注释行、`{off,on}/meta.json`。
⇒ **不许写「两臂只在接话处不同」**。ON 的世界态在第 1 条接话后就真实分叉，后续所有 purpose 都有小幅上抬。因此：

**归因边界（写死）**：
1. ON 只证明「**公开面接话通道被打开并在真实运行里触发过**」（存在性事实）；
2. **不能**推到「对话更自然 / 生活气息提升」——`W-1-e 自然度 judge` 是明令不做项，不得绕道用 `judge` 维度（`affection/respect/stance` 三臂同值 132/132/132，见 `llm_cost.txt:llm_judgment_by_dimension`）当作替代；
3. **不能**推断「接话质量」——本批无人工盲判、无质量判据。

### 3.4 本轮未解决的其余问题

| # | 问题 | 性质 | 归属 |
|---|---|---|---|
| 1 | C4 场所配额**结果侧越界**（`round×day×slot×place` 3 > 2、`day×slot×place` 5 > 2、忽略 day 的 `place×slot` 9 > 2、只数接话 4 > 2） | **功能级** | 需在 `code/life/public_talk.py` 改（本轮按纪律未动） |
| 2 | 尺子 `msg_id` vs `msg_uid` 口径不一致（`:281`） | 度量级 | 修完须**重算历史批次**确认口径不倒退 |
| 3 | `emit_run_meta` 开关账本缺 `HITT_DIALOGUE_PUBLIC_REPLY` | 工具级 | 开关生效只能靠 launch 证据 + 行为差 |
| 4 | `readings_on.json:place_adjacency` 未输出 `nonnull_place_records` / `coverage`（MEASURED 分支不带这些键），`compare.json` 里对应字段为 `null` | 度量级（不影响 C3 判定，但**覆盖率的直接字段缺失**） | C3 的「30/30」改由 `key_presence.place=30` + C4 `records_missing_place=0` + 本报告独立复算三路支撑 |
| 5 | `readings_off.json:place_adjacency.grep_commands_used` 里遗留 `# -> 55` 等示例数字（v1 时期 d27_C 批的模板残留） | 度量级（**只是示例文本，不参与出数**） | 建议后续清理，避免被误当本批读数 |
| 6 | 单 seed（42）、单批、非盲 | 设计级 | 全部数字**只作点估计、不外推** |

---

## ④ 可展示案例（真实原文，按 `seq` 从 `on/run.jsonl` 原样摘录，未改一字）

> 摘录方式：`v2/evidence/r41v_public_talk_n16r24_s42/on/run.jsonl` 中 `type=="MSG_PUBLIC"` 且 `payload.seq` 命中的行，取 `payload.body` 原文。`seq` 为日志行级事件序号（顶层 `seq` 字段）。

### 案例 1：一条公开招呼被**两个**人接住（同时是 C4 越界的现场）

- **目标** `seq 189`｜`author=P015`｜`place=farm`｜`slot=morning`｜`day=0`｜`thread=TH-P015-PUB-0-0`｜`turn_index=0`
  > （把灶上那锅萝卜牛腩的火拧小，拿勺子撇了撇浮沫）这两天忙得脚不沾地吧，我看你眼下都发青了——先坐，我给你盛碗汤。趁热喝。
- **接话** `seq 487`｜`author=P001`｜`reply_to="42:189"`｜`place=farm`｜`turn_index=1`｜`participants=["P001","P015"]`｜`ctx.public_reply={channel:"MSG_PUBLIC", co_present:["P003","P015"], place:"farm", v:"r41/1"}`
  > （拿抹布擦桌角，油渍蹭了两下没掉）这牛腩炖了一上午，烂乎着呢。你嫂子回娘家前搁的萝卜，再不吃就糠了嘛。
- **接话** `seq 613`｜`author=P003`｜`reply_to="42:189"`｜`place=farm`｜`turn_index=1`｜`participants=["P003","P015"]`
  > （拿抹布擦了擦桌角，又顺手把歪了的筷子筒扶正）这阵子活儿赶，手都糙了。汤我自己来。

事实层读数：`round1/day0/morning/farm` 共 **3** 条公开消息（`seq 189/487/613`）> `MAX_PER_PLACE_PER_SLOT=2` ⇒ 即 §2.1 C4 的越界现场。「汤我自己来」（613）对应目标句「我给你盛碗汤」（189），**文本层面存在承接**（本报告不对"接得好不好"下判断：无该判据）。

### 案例 2：school 场景的两次接话

- **目标** `seq 167`｜`author=P013`｜`place=school`｜`thread=TH-P013-PUB-0-0`｜`turn_index=0`
  > （把烧红的锄头往水桶里一浸，白汽直冒）这锄头是东头老周家的，刃口卷了，我正给他回火。你站远点，火星子不长眼。别急。
- **接话** `seq 760`｜`author=P006`｜`reply_to="42:167"`｜`turn_index=1`｜`participants=["P006","P013"]`
  > 铁头，你瞧这锄头是老周家那把，我正给它回火呢，你站远些别让火星子溅着吧。
- **接话** `seq 1270`｜`author=P012`｜`reply_to="42:167"`｜`turn_index=1`｜`participants=["P012","P013"]`
  > （拿火钳把锄头翻了个面，铁皮上还挂着水珠）铁头你来得正好，帮我把那桶里的水再添两瓢，老周这锄头回完火还得趁热敲两下，他明早要下地。

### 案例 3：round 12→13 的跨轮接话（school，3 人接同一目标）

- **目标** `seq 19241`｜`author=P005`｜`place=school`｜`thread=TH-P005-PUB-12-0`｜`turn_index=0`
  > （把药碾子往桌角推了推，捻起一片晒干的陈皮对着光看）老周家那小子烧退了，我这心里才松快些。这陈皮还是去年秋天存的，得再翻晒一遍。手不能生。
- **接话** `seq 20551`｜`round=13`｜`author=P004`｜`reply_to="42:19241"`｜`turn_index=1`｜`participants=["P004","P005"]`
  > （把案板上的面团翻了个面，指腹按了按）手不能生这话在理，我那炉杏仁酥今早火候就偏了一分。陈医你尝尝，老周家小子退了烧，嘴里该没味儿，这酥我少搁了糖。
- **接话** `seq 21419`｜`round=13`｜`author=P016`｜`reply_to="42:19241"`｜`turn_index=1`｜`participants=["P005","P016"]`
  > 哟，陈医，你瞧我这摊上新收的紫苏，梗子还带露水呢。（拈起一撮凑近鼻尖）老周家小子退了烧，我这心才落回肚里。手不能生。

事实层：`round=12` 的目标在 `round=13` 被接住（`reply_to` 指向 `42:19241`），即接话**跨 round 生效**；三条均复用目标句的「手不能生」与「老周家小子退烧」两个片段（**重复是事实陈述，不作质量判断**）。

### 案例 4：town_hall 的单人接话

- **目标** `seq 19807`｜`author=P013`｜`place=town_hall`｜`thread=TH-P013-PUB-12-0`｜`turn_index=0`
  > （把铁钳往砧子上一搁）听说你东家那批锄头催得紧，我这炉子刚空出来——你那边还缺人手不？
- **接话** `seq 20857`｜`round=13`｜`author=P008`｜`reply_to="42:19807"`｜`place=town_hall`｜`turn_index=1`｜`participants=["P008","P013"]`
  > （把案上那摞户籍册往边上推了推）我这正给东街王家补办分家文书，墨还没干透。你那边炉子空出来了？

事实层：接话以**反问**回应目标的提问（原文如此），本报告不对"是否答上了"下判断。

### 现场渲染截图（4 张，真实 PNG，非占位）

渲染命令（仓库现成渲染器，`ok_count=2 / fail_count=0`）：

```bash
python3 -B tools/metrics/render_shots.py --run-dir v2/evidence/r41v_public_talk_n16r24_s42/off \
  --batch-id R41V-off --outdir v2/evidence/r41v_public_talk_shots --views chat,rhythm
python3 -B tools/metrics/render_shots.py --run-dir v2/evidence/r41v_public_talk_n16r24_s42/on \
  --batch-id R41V-on  --outdir v2/evidence/r41v_public_talk_shots --views chat,rhythm
```

| 文件（相对仓库根） | 文件名内 sha8 | 字节数 | 尺寸 | PNG 自身 sha256 |
|---|---|---|---|---|
| `v2/evidence/r41v_public_talk_shots/R41V-off-chat-50def263.png` | `50def263`（= OFF `run.jsonl` sha256 前 8 位） | 300442 | 1400×900 | `fe200de492970678b701b1f6351a8224d60bcd834f3b0acee72c678a6375710c` |
| `v2/evidence/r41v_public_talk_shots/R41V-off-rhythm-50def263.png` | `50def263` | 279920 | 1300×1050 | `6349af59c831f929f789069b63cb5631730aca4e01820c7091f6d58cc9a28804` |
| `v2/evidence/r41v_public_talk_shots/R41V-on-chat-c8a7f546.png` | `c8a7f546`（= ON `run.jsonl` sha256 前 8 位） | 310649 | 1400×900 | `8fab63509dbdea90d423170504572b5843ea1fab978b3f194b18c091dcb9d739` |
| `v2/evidence/r41v_public_talk_shots/R41V-on-rhythm-c8a7f546.png` | `c8a7f546` | 280949 | 1300×1050 | `e12d9b9176bb02f29f7dfbab106e24226248921e1f0329dc7fb172b48f872736` |

口径说明：**文件名里的 sha8 是「该图所渲染的那份 `run.jsonl` 的 sha256 前 8 位」**（`render_report_R41V-{off,on}.json:log_sha256` 两臂分别 = `50def263…` / `c8a7f546…`），PNG 自身 sha256 另列一栏，两者不是同一个值。
**截图只证「批次真实存在 + 渲染链通 + 页面结构完整」，不支撑任何措辞质量结论。**

---

## ⑤ 下一周期计划（只写由本轮结果直接推出的）

1. **修 C4 越界（功能级，最高优先）**：`code/life/public_talk.py` 的场所配额需在「结果侧」也成立——候选做法（需新开分支 + 新预登记卡，不属本轮）：把配额判定从「决策时点可见集」改为「同 slot 内已落盘条数」，或让同 round 内的接话者共享一个事后校验。**验收判据（下一轮预登记应写死）**：两臂、任意 `round×day×slot×place` / `day×slot×place` / `place×slot` 的 `MSG_PUBLIC` 计数均 **≤ 2**（并单列「只数接话」口径），用本轮附录 B·B4 的分组复算脚本判定。
2. **把分母做到可判（度量前置）**：本轮 `probe` 因分母 <68 无法解除。按 ≈1.25 条公开消息/round，需要 **≈55–60 rounds**（或等价抬高公开面剂量）才能到 68。**新预登记卡必须先把"分母怎么来"写死再跑**，避免又出 `n=24/30`。
3. **修尺子 `reply_to`/`msg_id` 口径（度量级）**：`public_talk_metrics.py:281` 的 `msg_ids` 应纳入 `msg_uid`；修完**必须重算** r38/d12d/d27_C 等历史批，确认口径不倒退（先例：R19 修死尺子后明确「尺子恢复可动 ≠ 改善」）。
4. **补 `emit_run_meta` 开关账本**：登记 `HITT_DIALOGUE_PUBLIC_REPLY`，避免下次再靠 launch 证据链推开关生效。
5. **[工具侧·已登记]** `place_adjacency` 的 MEASURED 分支缺 `nonnull_place_records`/`coverage` 输出，C3 的 30/30 需三路（`key_presence` + `records_missing_place` + 独立复算）拼合；下一轮补齐字段，不改变本轮读数。

**与玩家已关闭线不相冲突的核对**：以上 5 条均不触碰**旁白句式 / D9 家族**（`D9*`、`narration_family`）、不触碰 `reply_window_rounds`、不触碰 `_initiate` 对端、也不新增任何「出口」。C4 修复属配额实现内部口径，不改变对话出口数量。

---

## 附录 A · 提交与推送回填（sha 用取法，不写死）

| 项 | 状态 | 取法 |
|---|---|---|
| 本报告文件 commit sha | 【待 `evidence-verifier` 回填】 | `git log -1 --format=%h -- reports/R41b-public-talk-verify.md` |
| `reports/README.md` 索引行 commit sha | 【待回填】（通常与上一行同 commit） | `git log -1 --format=%h -- reports/README.md` |
| 推送是否可达 | 【待回填】 | `timeout 30 git ls-remote origin feat/life-public-talk-r41-verify` 并与 `git rev-parse HEAD` 比对（**不要**用 `git rev-list --count origin/<branch>..HEAD`，那只看本地 ref） |
| 预登记 commit（已存在，实测值） | `f365255faf77141e33da9bb170850cf55d5b121c` | `git log -1 --format=%H -- v2/refs/prereg-r41v-public-talk-verify.md` |
| 两臂 `run.jsonl` 是否入库 | `.gitignore` 排除 `**/*.jsonl` ⇒ **只入 sha256**，不入原件 | `git check-ignore -v v2/evidence/r41v_public_talk_n16r24_s42/on/run.jsonl` |

提交范围建议（**不包含**任何 `code/` 改动）：`reports/R41b-public-talk-verify.md`、`reports/README.md`（只增一行）、`v2/refs/prereg-r41v-public-talk-verify.md`（若尚未提交）、`tools/public_talk/{launch_r41v.sh,compare_arms.py}`、`v2/evidence/r41v_public_talk_readings/*`、`v2/evidence/r41v_public_talk_shots/*.png + render_report_*.json`、两臂锚点（不含 `run.jsonl` 原件）。
**禁区**：`v2/evidence/r41v_public_talk_n16r24_s42/off_ABORTED_prereg_commit_before_start/`（中止留证，不入库、不作读数来源）；`git status --porcelain` 里与本轮无关的既有改动（`reports/CYCLE-37-20261031.md`、`v2/refs/D9*.md`、`*.pyc` 等）**一律不 stage**。

---

## 附录 B · 本报告全部数字的复算入口（可直接复跑；只读、零 LLM）

```bash
cd <repo-root>   # 即 social-experiment

# B0 编号占用检查（回答"R41b 是否冲突"）
git ls-files reports/ | grep -Ei 'reports/R41b?-' || echo "R41b 未被占用"

# B1 两臂日志/元数据 sha256（对照 §1.2）
sha256sum v2/evidence/r41v_public_talk_n16r24_s42/{off,on}/run.jsonl \
          v2/evidence/r41v_public_talk_n16r24_s42/{off,on}/meta.json

# B2 行数 / 事件数（对照 §1.2 收批凭证）
for a in off on; do
  d=v2/evidence/r41v_public_talk_n16r24_s42/$a
  echo "$a lines=$(wc -l < $d/run.jsonl) events=$(python3 -c "import json;print(json.load(open('$d/meta.json'))['events'])")"
done

# B3 判据 C2/C3/C5 + 全部结构计数（独立于尺子的最小复算，对照 §2.1/§2.2）
python3 - <<'PY'
import json, collections
for arm in ("off","on"):
    pubs=[]
    for line in open(f"v2/evidence/r41v_public_talk_n16r24_s42/{arm}/run.jsonl",encoding="utf-8"):
        try: d=json.loads(line)
        except Exception: continue
        if d.get("type")=="MSG_PUBLIC": pubs.append(d)
    nn=[d for d in pubs if d["payload"].get("reply_to") is not None]
    th=collections.Counter(d["payload"].get("thread_id") for d in pubs)
    print(arm,
          "pub=", len(pubs),
          "reply_to_nonnull=", len(nn),
          "place_nonnull=", sum(1 for d in pubs if d["payload"].get("place")),
          "ctx.public_reply=", sum(1 for d in pubs if "public_reply" in (d["payload"].get("ctx") or {})),
          "turn_index=", dict(collections.Counter(d["payload"].get("turn_index") for d in pubs)),
          "participants_len=", dict(collections.Counter(len(d["payload"].get("participants") or []) for d in pubs)),
          "distinct_thread=", len(th),
          "multiturn_thread=", f"{sum(1 for v in th.values() if v>1)}/{len(th)}")
PY

# B4 C4 配额越界复算（对照 §2.3 的 3 / 5 / 9 / 4 / 1）
python3 - <<'PY'
import json, collections
ps=collections.Counter(); dsp=collections.Counter(); rdsp=collections.Counter()
r_ps=collections.Counter(); ag=collections.Counter()
for line in open("v2/evidence/r41v_public_talk_n16r24_s42/on/run.jsonl",encoding="utf-8"):
    d=json.loads(line)
    if d.get("type")!="MSG_PUBLIC": continue
    p=d["payload"]
    ps[(p.get("place"),p.get("slot"))]+=1                                   # 忽略 day
    dsp[(p.get("day"),p.get("slot"),p.get("place"))]+=1                    # 跨 round
    rdsp[(d.get("round"),p.get("day"),p.get("slot"),p.get("place"))]+=1    # 最小粒度
    if p.get("reply_to") is not None:
        r_ps[(p.get("place"),p.get("slot"))]+=1
        ag[(p.get("author"),p.get("slot"))]+=1
print("max round×day×slot×place =", rdsp.most_common(1))  # 期望 3（round1/day0/morning/farm）
print("max day×slot×place       =", dsp.most_common(1))   # 期望 5（day0/afternoon/bank）
print("max place×slot(忽略day)  =", ps.most_common(2))    # 期望 9（bank/afternoon）、8（school/morning）
print("max 接话 place×slot       =", r_ps.most_common(2))  # 期望 4（school/morning）
print("max 接话 author×slot      =", ag.most_common(1))    # 期望 1
PY

# B5 复算尺子（口径/判据逐条，与已完成产物逐位对拍）
python3 -B tools/public_talk/public_talk_metrics.py \
  --log v2/evidence/r41v_public_talk_n16r24_s42/off/run.jsonl \
  --meta v2/evidence/r41v_public_talk_n16r24_s42/off/meta.json --out /tmp/r41b_off.json
python3 -B tools/public_talk/compare_arms.py \
  --off v2/evidence/r41v_public_talk_n16r24_s42/off/run.jsonl \
  --on  v2/evidence/r41v_public_talk_n16r24_s42/on/run.jsonl \
  --off-meta v2/evidence/r41v_public_talk_n16r24_s42/off/meta.json \
  --on-meta  v2/evidence/r41v_public_talk_n16r24_s42/on/meta.json --out /tmp/r41b_compare.json
python3 -c "import json;d=json.load(open('/tmp/r41b_compare.json'));\
print(d['verdicts']['R41V-C1_main_rate_diff']['status']);\
print(d['verdicts']['R41V-C4_quota_guard']['observed']['on']['max_pub_per_place_round'])"

# B6 真实 LLM 成本验真（必须在 code/ 下执行；rc 单独取，不串管道）
cd code
python3 -m obs llm-cost --log ../v2/evidence/r41v_public_talk_n16r24_s42/off/run.jsonl \
  --require-provider openai_compat > /tmp/r41b_llm_off.txt 2>&1; echo "off rc=$?"
python3 -m obs llm-cost --log ../v2/evidence/r41v_public_talk_n16r24_s42/on/run.jsonl \
  --require-provider openai_compat > /tmp/r41b_llm_on.txt 2>&1; echo "on rc=$?"
cd ..
grep -o '"total":{[^}]*}' /tmp/r41b_llm_off.txt /tmp/r41b_llm_on.txt

# B7 截图真伪（尺寸 + PNG magic + sha256，对照 §4 表）
python3 - <<'PY'
import struct, os, hashlib
d="v2/evidence/r41v_public_talk_shots"
for f in sorted(os.listdir(d)):
    if not f.endswith(".png"): continue
    b=open(os.path.join(d,f),"rb").read()
    w,h=struct.unpack(">II", b[16:24])
    print(f, len(b), f"{w}x{h}", b[:8]==b"\x89PNG\r\n\x1a\n", hashlib.sha256(b).hexdigest()[:16])
PY

# B8 对话原文回取（对照 §4 案例，逐字）
python3 - <<'PY'
import json
want={189,487,613,167,760,1270,19241,20551,21419,19807,20857}
for line in open("v2/evidence/r41v_public_talk_n16r24_s42/on/run.jsonl",encoding="utf-8"):
    d=json.loads(line)
    if d.get("seq") in want and d.get("type")=="MSG_PUBLIC":
        p=d["payload"]
        print(d["seq"], p.get("author"), p.get("reply_to"), p.get("place"), p.get("turn_index"), "|", p.get("body"))
PY
```

**复算纪律**：B3/B4 是**独立于尺子**的最小复算（只读 jsonl、无第三方依赖）；B5 是对已完成尺子产物的对拍，若 `/tmp` 输出的判据字段与 `v2/evidence/r41v_public_talk_readings/compare.json` 不一致，**以原件为准并当场登记差异**，不要改原件。

**本轮自检记录（撰写时实际执行过，不是"应该能跑"）**：

| 检查 | 结果 |
|---|---|
| B3 独立复算 | OFF `pub=24 / reply_to_nonnull=0 / place_nonnull=0 / ctx.public_reply=0 / turn_index={0:24} / participants_len={1:24} / thread=24 / multiturn=0/24`；ON `30 / 7 / 30 / 7 / {0:23,1:7} / {1:23,2:7} / 23 / 4/23` —— 与 §2.1/§2.2 逐项一致 |
| B4 C4 复算 | `round×day×slot×place=3`、`day×slot×place=5`、`place×slot(忽略 day)=9（bank/afternoon）`、`接话 place×slot=4（school/morning）`、`接话 author×slot=1` —— 与 §2.3 一致 |
| B5 尺子重跑对拍 | 五条判据逐条重跑得 `不可判（分母不足）/ 达标 / 达标 / 不成立 / 达标`、`all_hold=false`、`max_pub_per_place_round=3`；与原件 `compare.json` **逐字段 diff 后唯一差异**是 `arms.*.readings_path`（`/tmp/readings_on.json`  vs 仓库内路径）——即**判据与全部计数零差异**，仅产物自身路径字段不同，故两份 sha256 不同（`53b1e452…` vs 原件 `6dd53bcc…`）属预期，**不是读数漂移** |
| B7 截图核验 | 4 张 PNG magic 全为真 PNG、尺寸/字节数逐张对上、sha256 与 §4 表一致 |
| B8 原文回取 | 11 个 `seq` 的 `payload.body` 与 §4 逐字一致 |
| 未执行项 | B6（`obs llm-cost`）本轮**未重跑**：需在 `code/` 下执行会写 `__pycache__`，按"不碰无关工作树"的纪律改为**直接引用两臂已落盘的 `llm_cost.txt` + `llm_cost.rc.txt`**（rc 均为 0，文件存在且给出 `provider_guard.ok=true`、`tokens_total` 与 §1.4 同值） |
