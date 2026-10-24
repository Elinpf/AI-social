# R24 · 「公开场合接话」基线（描述性）

> **选名理由（首行说明）**：`reports/` 现有编号族为 `R1…R23` + `CYCLE-01…24` + `D7/D12-F/D27` 等（`ls reports` 实测无 `R24-*`），故取 `R24-public-talk-baseline.md`，不覆盖、不改名、不与既有文件冲突；本报告**不发明**新维度编号（CYCLE-16 / R23 已裁定不发明 `F-9` 类编号），维度名一律写「公开场合接话」。

> **文件身份**：对外报告族成员（`reports/`＝对外报告正式位置，见 `reports/README.md`「仓库内正式路径清单」）。
> **分析基准 sha（入库时仓库 HEAD）**：`009e95310c5221aef47c9c36f41ddad4f11e627b`（`git rev-parse HEAD`，`master`）。**它只回答「以上文件在哪个仓库状态下取证」**。
> **读数绑定代码身份（跑批树）**：`f2bf606bf5f6c362a7d4d34b9177f3210d43aabf`（该批 `meta.code_sha`，= `code_sha_end`）。**两者不混用。**
> **取证时刻**：`2026-10-25T00:08–00:35 +08:00`（截图为 `00:08:50—00:08:52`，见 `S5`）。
> **本轮状态词**：`BASELINE-DESCRIPTIVE — 结构事实成立 / 效果未判 / 本轮未改代码，无效果判定`
> **工作性质**：**零跑批、零 LLM 调用、零冻结区改动**。只做三件事：① 读既有日志出确定性读数；② 现渲 2 张页面截图（物证）；③ 入库。
> **纪律自检**：分母 `55 < 68` ⇒ 全部 `probe`，**只报事件数、不报比率**；结论只用「公开面结构上不存在接话机制」一类**定性表述 + 事件计数**；**本轮未改代码，无效果判定**；**不给截图配任何百分数**。

---

## 0. 事实来源清单（每份带 sha256；凡读数必绑来源）

### 0.1 本报告直接引用的事实来源

| # | 来源 | 角色 | sha256 |
|---|---|---|---|
| S1 | `v2/evidence/run_d27_C_n16r60_seed42/run.jsonl` | **唯一数据源**（C 基线批日志，116,308 行 / 56,531,099 B） | `1fbb9ef5161fd07aa68fcc9fc4038f104ff18b56383a2fc6b31bb3cb5486a188` |
| S2 | `v2/evidence/run_d27_C_n16r60_seed42/meta.json` | 跑批身份与自洽断言（`run_sha256` / `derived_from_log_sha256` 均 = S1） | `e73acb4683fbafd322b0406e59f825ed5a6f8298db104f8333e4dcf431fcb793` |
| S3 | `tools/public_talk/public_talk_metrics.py`（**v4 现行**） | **尺子**（确定性出数器，纯只读；`--repo-head` 显式声明、不调 git） | `15e7f0481c5ba307b8c7f39184dd7cbe747be3f9ac7d2777c443ea8ddba44a77` |
| S4 | `v2/evidence/public_talk_readings_d27_C_n16r60_seed42.json`（**v4 现行**） | **读数文件**，本报告 §2 全部数值的机器可读版 | `971dcb3b01359d21b7c6cad8742676f8a409816d67b99dc439a577b8734fce2b` |
| S5 | `v2/evidence/public_talk_shots/`：`README.md` / `render_report_PUBTALK-C.json` / `PUBTALK-C-chat-1fbb9ef5.png` / `PUBTALK-C-rhythm-1fbb9ef5.png` / `threads_PUBTALK-C.json` | 截图物证（**不参与判据**，§4.2） | `088c063e56f583369b8b4b1d87122522faec392efe68cc3994f9f14a425ca73f` / `dfb5cef6838062793a57723c561c2c8224898e1ab103f15549a9dbbbaf5d03b8` / `31fd3ad0666ba22997de107614a50083de1312477ea8063c52b51e578d1a401b` / `2eb8c76b7a9bc54d3b3069ad5a812f7cf53d7a83e667690ed5f22cdb0b0633ab` / `15e9293bf5e443d423ea7fd2b063cc85bca7a8fe5af409aab62587cced6ad47c` |
| S6 | `v2/evidence/preflight/preflight_20261024T160342Z_009e9531_survey_probe.log` / `clean_tree_20261024T160342Z_009e9531_survey_probe.json` | 串行闸 + 冻结区干净度实测留痕（证据链，随本报告入库） | `202bbb86b08ef7f0f98bba1689a777017e7ecaeb55ab716d831e1e4874b8c7b4` / `0fd2d0e1f44842769fb83af8b1f5181f28ca1818eb9722729b62d6248e225e61` |
| S7 | 团队工作区 `round1-survey.md`（**不在仓库内**） | 仓库惯例与维度现状 | `b9b7b3d1d49039248bf1107caa1cffce86614ebdca1ebf4fd29b678ecd7cdb4d` |
| S8 | 团队工作区 `round1-ruler-verify.md`（**不在仓库内**） | 尺子独立复核 + 反证（含 D1–D6 缺陷清单） | `1cd92bd592c47e7a800e5c23edda452b561cc079d3a516457297b2e3349de977` |

> **S7/S8 边界**：两份都是团队工作区文件，不入仓库；引用处逐条标节号，且**凡进入 §2 表的数值都由本报告用附录 A 独立复算**（不是转抄）。
> **S3/S4 的 sha256 为 v4 现行值**（`15e7f048…` / `971dcb3b…`）。历史值只作留痕且**必须带限定词**：`ea845c40…`（v1 脚本）、`b2820d71…`（v3 脚本，**缺陷 D8 未修**）、`ad183d2b…`（**补丁前 / 缺陷 D1 时值**）、`7f2a8d38…`（**缺陷 D1 时值：省 `--meta` 的复算产物**）、`4371ca6a…`（**缺陷 D7 时值：`--out` 路径写入自身、换路径即变**）、`c1d8a54b…`（**缺陷 D8 时值：读数内含运行时 `git HEAD`，HEAD 前进即复算不出**；在 HEAD=`3869428` 下复算得 `fc985693…`，属**预期行为**）。**裸旧 sha 一律不得引用。**

### 0.2 数据源身份（`S2`，逐项照录）

| 项 | 值 |
|---|---|
| `code_sha` = `code_sha_end` | `f2bf606bf5f6c362a7d4d34b9177f3210d43aabf` |
| 规模 | `n=16`、`rounds=60`、`seed=42`（`S4.scale` 同值，来源 `meta.json`） |
| provider / model | `openai_compat` / `DeepSeek-Flash` |
| 调用 | `llm_calls 2878`、`llm_cached 1425`（`cached_ratio 0.4951`）、`degraded_calls 0` |
| 事件 | `events 116308`（= `wc -l`，脚本内建断言） |
| 时间 | `started_at 2026-10-24T14:04:39+08:00` → `finished_at 2026-10-24T14:59:23+08:00`，`duration_sec 3284` |
| 消息构成 | `msg_counts = {MSG_DM: 455, MSG_PUBLIC: 55}` |
| 跑批 rc | `run_batch.rc` = `0`（进程 rc；与 `obs llm-cost` 的 rc 是两件事） |

**真 LLM 判据**：`provider=openai_compat` 是**日志内**事实，`degraded_calls=0`；**本轮不重跑 `obs llm-cost`**，故 §3#6 如实标「转引」。

### 0.3 读数文件的元数据（v1 缺陷 → v2/v3 修复）

| 项 | v1（复核时，**已作废**） | **v2/v3（现行）** |
|---|---|---|
| `inputs.code_sha` | `009e953`（`git rev-parse HEAD`）⇒ 锚错 | **`f2bf606b…`**，`code_sha_source = "meta.json:code_sha（跑批时点代码身份）"`；HEAD 另单列为 `repo_head_at_run = 009e9531…`，附注「**不是**该批跑批身份」 |
| `diagnostics.thread_id_reuse` | `true`，语义与名字相反 | **已删除，改名 `each_msg_owns_thread = true`**，附注「true = 无任何 `thread_id` 被复用」 |
| `judgeability.scale`（硬编码串） | 跨批不随输入变化 | **已改为 `scale`**（从 `meta.json` 读 `agents_n/rounds/seed/provider/model`，读不到写 `UNKNOWN`） |
| `invocation.argv_joined` | 无 | **已加**；v3 起 `--out` 记为占位 `<OUT>`（**D7 修复**）⇒ 换输出路径 sha 不变；v4 起命令含 `--repo-head` |
| `inputs.repo_head_at_run`（**v3 及以前**） | 无 | **已删除**（**D8 修复**）：v3 该字段是运行时 `git_head(...)` 实测值 ⇒ HEAD 前进后复算即不可复现（§0.3a） |
| `inputs.repo_head_declared`（**v4**） | — | **改为 `--repo-head` 显式声明**：`repo_head_declared = 009e95310c5221aef47c9c36f41ddad4f11e627b`、`repo_head_declared_valid = true`；附注「**不是运行时实测值**、不参与任何计算；脚本内部不调用 git，故读数与当前 HEAD 无关」 |
| `participants` 语义 | 无说明 | **v3 `semantics_note` 原文**：「participants 为**线程参与者集合**（同一 thread_id 内取值恒定，本批实测 169 个线程中不一致者 0 个），**不是收件人**（DM 的收件人是 `to`），也不是消息级可见性开关；长度 > 1 不代表多人群聊、也不代表多人接话。」 |

### 0.3a 中间提交留痕（**不删除、不改写**）：`3869428` 是 D8 未修时的中间提交

按仓库「更正留痕、不删原文」惯例，此处把一次已进远端历史的中间状态讲清楚：

1. **`38694283fe5ffda3a33e67a9a53e85ba6eff5b16`（简写 `3869428`）是 D8 未修时的中间提交**；该提交内读数 sha 为 `c1d8a54b…`（**缺陷 D8 时值**），其复算前提是 **仓库 HEAD = `009e95310c5221aef47c9c36f41ddad4f11e627b`**（因为 v3 读数把运行时 `git HEAD` 写进了自身）。
2. **v4 之后读数与 git HEAD 解耦**：`--repo-head` 显式声明、脚本不调 git ⇒ **以 v4 提交的读数（`971dcb3b…`）为准**。
3. 若有人检出 `3869428` 并按当时附录命令复算得 `fc985693…`，**那是预期行为**（差异仅 `inputs.repo_head_at_run` 一行），**不是数据被篡改**、也不是证据不可复现——只要把 HEAD 回到 `009e9531` 即得 `c1d8a54b…`。
4. 本段留痕**不删除、不改写**；新提交一律为**前向修正**（不 `amend`、不 `rebase`、不 `force`）。

### 0.4 更正留痕（v1 → v2）：`participants` **不是可见性**，是**线程参与者**

> 按 `reports/README.md`「更正留痕、不删原文」惯例，保留更正前说法并标为撤回。

| 版本 | 说法 | 状态 |
|---|---|---|
| v1（初稿） | 「`participants == [author]` ⇒ 公开面**可见集合仅作者自己**」 | ❌ **已撤回，禁止再引用** |
| **v2（现行）** | `participants` 是**线程参与者集合**（同一 `thread_id` 内取值恒定，`code/life/ports.py:72`；v3 `semantics_note` 实测本批 **169 个线程中不一致者 0 个**），**既不是收件人**（DM 收件人是 `to`）**、也不是消息级可见性开关**。公开消息是**单发线程**，故线程参与者只有作者 ⇒ 只说明「该公开消息没有形成多人线程」。 | ✅ 现行 |
| 可见性**真源** | `code/config/perception_scope.json:18` `"MSG_PUBLIC": "global"`（`version v1.2-r2`）+ `code/contracts/visibility.py:43-44` `if cls == "global": return True` ⇒ **公开消息对全城所有 agent 权限上可见** | ✅ 现行 |

> 上列源码事实的代码身份均为 `f2bf606b…`；实测 `git diff --quiet f2bf606b..009e953 -- code/` 为空 ⇒ 6 个相关源码文件在两 sha 上**逐字节相同**，故可写「源码：`file:line`（`f2bf606b ≡ 009e953`）」，不存在 sha 混绑（附录 A-10）。

### 0.5 复算前提：**「日志 + meta.json + 全参数命令行」三元组**

**读数文件的 sha256 不是日志的纯函数，而是「日志 + 调用参数」的函数**——`invocation` 段把 argv 原样记进 JSON。因此：

- **R1（命令行完整）**：附录 A 的命令**一个参数不许省**——`--meta`、**4 个 `--extra-log`**、以及 v4 起的 **`--repo-head 009e95310c5221aef47c9c36f41ddad4f11e627b`（40 位完整）** 都要。省 `--extra-log` 会得 `cross_batch_invariance: []`；省 `--repo-head` 会得 `repo_head_declared: null`。**这都不是尺子不确定，是命令没照抄。**
- **R2（三元组同绑）**：`S4`（`971dcb3b…`）的 sha256 成立前提是「`S1` + `S2` + 附录 A-1 的确切命令行（含 `--meta`、4×`--extra-log`、`--repo-head` 40 位）」三元组；缺任一项即不可复现。
- **R3（执行前提：须在仓库根目录跑）**：`argv` 用**相对路径**（`tools/...`、`v2/evidence/...`），**换目录执行会找不到文件**；这是复算的隐性前提，必须写明。
- **R4（v3 起路径无关）**：`--out` 记为占位 `<OUT>` ⇒ 换输出路径 sha 不变（§1.1 三路径实测同值）；此前（**缺陷 D7 时值**）换路径 sha 会变（`4371ca6a…`）。
- **R5（v4 起 HEAD 无关）**：v4 用 `--repo-head` 显式声明、脚本**不调 git** ⇒ **在读日志时把仓库 HEAD 前进到任何位置，复算结果都不变**（本报告在 HEAD=`3869428` 下现跑，得到的仍是 `971dcb3b…`）。此前（**缺陷 D8 时值**）读数内含运行时 HEAD，HEAD 前进即复算不出（`c1d8a54b…` → `fc985693…`）。

---

## 一、本轮做了什么

1. **立尺子**（`S3`）：确定性出数器，纯只读、无 `random`/无 `datetime.now`、`sort_keys` 定序；现含 `schema_gate` / `key_presence` / `cross_batch_invariance` / `invariance_note` / `invariance_summary` / `invocation` / `thread_isolation` / `msg_graph_degree` / `pub_next_to_dm` / `author_topic_crosstab`。
2. **出读数**（`S4`）：四组主线量 + 七组结构/图论读数 + 跨批不变性自检，全部绑 `log_sha256` + `code_sha`。
3. **独立复核**（`S8`）：两跑 sha256、`/tmp` 另写实现 4/4 逐项对照、三项反证、档位裁决、D1–D6 缺陷清单；本报告 §2/§3 逐条落地。
4. **渲 2 张真实截图**（`S5`，物证）：`rc=0 / ok_count=2 / fail_count=0`。
5. **入库**：本报告 + 尺子 + 读数 + 截图目录 + 2 个 preflight 日志，按**明确路径** `git add`（附录 B 白名单）。

> **本轮未改一行行为代码**：`code/life`、`code/orchestration`、`code/config`、`code/engine` 全未触碰（入库前 `preflight` 实测 `frozen_tree=clean`，`S6`）⇒ §2 全部是**结构事实 + 描述性基线**，**无效果判定**。

### 1.1 确定性自证（本报告独立复跑）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment   # 必须仓库根目录
M=v2/evidence/run_d27_C_n16r60_seed42
python3 tools/public_talk/public_talk_metrics.py \
  --log $M/run.jsonl --meta $M/meta.json \
  --extra-log v2/evidence/run_r10e2e_n16r60_seed42/run.jsonl \
  --extra-log v2/evidence/run_d28_C_s43_n16r60_seed43/run.jsonl \
  --extra-log v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl \
  --extra-log v2/evidence/run_d2_before_n16_seed42/run.jsonl \
  --repo-head 009e95310c5221aef47c9c36f41ddad4f11e627b \
  --out /tmp/pt_a.json
# 同一命令再来一次 → /tmp/pt_b.json；第三份写回仓库内正式路径
sha256sum /tmp/pt_a.json /tmp/pt_b.json v2/evidence/public_talk_readings_d27_C_n16r60_seed42.json
```

**实测（v4 重跑，本报告亲自执行，执行时仓库 HEAD 已是 `38694283…`）**：**三方同值 `971dcb3b01359d21b7c6cad8742676f8a409816d67b99dc439a577b8734fce2b`** —— `/tmp/pt_a.json`（现跑第 1 次）+ `/tmp/pt_b.json`（现跑第 2 次，**另一输出路径**）+ 仓库内正式路径（第 3 次），三者 `sha256sum` 全等，且**与入库件一致**（`git status` 对该文件无改动）。

> **这一条同时证伪了三个缺陷**：① **缺陷 D1 时值** `7f2a8d38…`（省 `--meta` 的产物）不再出现；② **缺陷 D7 时值** `4371ca6a…`（`--out` 写进 JSON、换路径即变）已被 v3 修掉；③ **缺陷 D8 时值** `c1d8a54b…`（运行时 `git HEAD` 写进 JSON、HEAD 前进即变）已被 v4 修掉——本段实测是在 **HEAD=`38694283…`** 下跑的，结果仍为 `971dcb3b…`，说明**读数已与 HEAD 解耦**。**故本报告的确定性结论以 v4 实测为准，旧值仅作留痕。**

---

## 二、测到了什么（分子 / 分母 / 档位 / 结论词）

### 2.0 判定档位先行

| 量 | 分母 | 档位 | 可写 |
|---|---|---|---|
| 量1 `MSG_PUBLIC` 条数 | 自身即分母 | 事件数（`probe`） | 「55 条」 |
| 量2 `participants` 长度 > 1 | **55** | 事件数（`55 < 68` ⇒ `probe`） | 「55 条中 0 条」，**不得报比率** |
| 量3 `reply_to` 非 null | **55** | 事件数（`probe`） | 「55 条中 0 条」 |
| 量4 同 `place` 相邻对 | **无法定分母** | **`UNVERIFIED`** | 「字段值恒 null，根因是源码写死」 |
| 旁证：DM 带 `reply_to` | 455 | 事件数（本节统一只报计数） | 「455 条中 341 条」 |

> **纪律**：分母 `55 < 68` ⇒ 一律 `probe`；恒 0 时若必须给量级，只能用**未观测率上界 `rule-of-three ≈ 3/55 = 5.45%`**，且须写明「这是**上界**，不是观测到的比率」（`reports/README.md` 纪律 5）。
> **前置约束 R2**：本节读数取自 `S4`，其 sha256 依赖「`S1` + `S2` + 附录 A-1 全参数命令行」三元组（§0.5）；代码身份 `meta.code_sha = f2bf606b…`（**不是** `009e953`）。

### 2.1 主线四组量（来源 `S4`，附录 A-1 复算）

| 量 | 分子 / 分母 | 实测（照录 `S4`） | 档位 | `band_source` | 结论词（定性 + 事件计数） |
|---|---|---|---|---|---|
| **量1** `MSG_PUBLIC` 总条数 | `55` / 无 | `value = 55`；`line_span_in_log = {first: 54, last: 87592}` | 事件数 | 无需（纯计数） | 本批公开发言 **55 条** |
| **量2** `participants` 长度 > 1 | `0` / `55` | `length_histogram = {1: 55}`、`length_values_set = [1]`、`records_missing_key = 0`、`records_nonarray = 0`（`bucket_policy`：缺键/非数组**绝不并入 `"0"` 桶**） | 事件数（`probe`） | `rule-of-three(3/55)` | **55 条中 0 条**线程参与者 > 1 ⇒ 公开面**没有形成多人线程** |
| **量3** `reply_to` 非 null | `0` / `55` | `forms = {json_null: 55, string_None: 0, empty_string: 0, real_message_id: 0, missing_key: 0, other: 0}` | 事件数（`probe`） | `rule-of-three(3/55)` | **55 条中 0 条**带 `reply_to` ⇒ 公开面**不含**「承接上一条」的引用字段 |
| **量4** 同 `place` 相邻对 | 无法定分母（`denominator_pairs = 54`） | `place_value_histogram = {null: 55}`、`nonnull_place_records = 0`、`status = UNVERIFIED`、`missing_kind = "值为 null 55 条"` | **`UNVERIFIED`** | 无可用带 | 不可判；**根因是源码写死 `"place": None`**（§2.7 M3），**不是样本缺失**；不插补、不换口径 |

**本轮可引用的定性结论（v2）**：

> **公开面结构上不存在接话机制**——本批 55 条 `MSG_PUBLIC` 中 **0 条**带 `reply_to`、**0 条** `participants` 长度 > 1；每条公开消息各自独占一个 `thread_id`（55 条 → 55 个线程，每线程 1 条），`turn_index` 恒 `0`，`scope` 恒 `global`。**本轮未改代码，无效果判定。**

**并推进到本轮主结论（最强版）**：

> **公开面：看得见，但不回应。** 每条公开消息都被**除作者外全部 15 名居民各感知一次**（§2.8：55/55、他人感知 **825** 条、`{15: 55}`、感知方去重 **16** 人），但无人以 `reply_to` 回应——**公开消息在消息图中入度 0、出边 0，是孤立节点**（§2.4）。
> 这一对照是本报告最重要的一句：**感知已接线、回应未接线，是两件事，不能混写**。
> **边界**：不含动机（「居民不想公开聊天」**不可说**）、不含效果（「改造后会改善」**不可说**）、不解释成因。

### 2.2 旁证诊断（只登记、不作判据）

| 诊断（`S4.diagnostics` / `author_topic_crosstab`） | 值 | 限定 |
|---|---|---|
| `distinct_authors` | `12` | 55 条来自 12 名不同居民 ⇒ 不是「一个人刷屏」 |
| `each_msg_owns_thread` | `true`（附注：**true = 无任何 `thread_id` 被复用**） | 55 条 → 55 线程，每线程 1 条；旧名 `thread_id_reuse` 语义相反，**已删除**（§0.3） |
| `scope_histogram` | `{global: 55}` | 全部 `scope=global` |
| `turn_index_histogram` | `{0: 55}` | 全部是线程首条（`0=发起`） |
| `refs_length_histogram` | `{0: 55}` | `refs` 恒空 ⇒ 不引用任何实体/消息 |
| `topic_histogram` | `{skill_practice: 29, savings: 18, job_choice: 8}`（合计 55，**无第四档**） | 与计划侧 `template_id` 逐档相等（§2.7b） |
| `author_topic_crosstab.authors_with_breadth_le_2` | **`11 / 12`**（只有 `P013` 跨 3 个话题） | **按字段值引用**，不手抄口头数 |
| `author_list` | `P002,P003,P004,P005,P006,P007,P008,P010,P012,P013,P015,P016` | 16 名居民中 **4 人本批未公开发言**（`P001/P009/P011/P014`，附录 A-4） |

> 本节**不给任何百分比**，也不据此推断「谁更活跃」；`author_topic_crosstab.usage_note` 明确「作为下一轮接话提示词设计的输入，**不进任何判据**」。

### 2.2b 两处补充依据：线程一致性 + 发送方必在线程参与者内（附录 A-12 复算）

| 量 | 实测 | 口径（**必须照此写，否则会误判**） |
|---|---|---|
| **线程一致性** | **169 个 `thread_id`，`participants` 在同一线程内不一致者 = 0** | 同一 `thread_id` 内取值恒定（v3 `semantics_note` 同值） |
| **发送方在 `participants` 内** | **510 / 510**（`MSG_DM` **455/455** + `MSG_PUBLIC` **55/55**） | **`MSG_DM` 没有 `author` 字段，发送方是 `from`**；`MSG_PUBLIC` 发送方是 `author`。若用 `author` 去判 DM，会得到 **455 条假异常**（实测） |

> 这两条只作**结构自洽旁证**：它们说明「线程参与者」这个字段在本批数据上是稳定且包含发言者的；**不构成任何判据**，也不据此推断「谁看得见谁」。

### 2.3 跨批「结构常数」（`S4.cross_batch_invariance` + `invariance_summary`，附录 A-5 复算）

| 批次 | `log_sha256` | `code_sha` | `meta_schema` | `MSG_PUBLIC` | `participants` 长度 | `reply_to` | `schema_compatible` |
|---|---|---|---|---|---|---|---|
| `run_d27_C_n16r60_seed42`（主批） | `1fbb9ef5161fd07aa68fcc9fc4038f104ff18b56383a2fc6b31bb3cb5486a188` | `f2bf606b…` | full | **55** | `{1: 55}` | `json_null 55` | `true` |
| `run_r10e2e_n16r60_seed42` | `f20f6822b7424bfc40f0820eca0726f635ed57618a04642cf230b20bfddb7476` | `625187c31b2c93d80d48bcf60afed1b5f41afc98` | full | **55** | `{1: 55}` | `json_null 55` | `true` |
| `run_d28_C_s43_n16r60_seed43` | `e3518b63f3a587e93f11cf0fa56e4e7c97f807de9e198aab17cb8968051aae36` | `04ff044e7a46f89db6d8273a84806dd7212ef9c4` | full | **55** | `{1: 55}` | `json_null 55` | `true` |
| `run_d12c_on_n16r60_seed42` | `bd2df77fd125cc75c31f261cc05486bd7376d9a9fcd9334f083cf8897e496c87` | **不可得**（`code_sha = null`、`meta_schema = simplified`，仅有 `code_sha_short = a977cb0`）；**不得用 `a977cb0` 冒充完整 sha** | simplified | **55** | `{1: 55}` | `json_null 55` | `true` |
| `run_d2_before_n16_seed42`（v0-anchor） | `c1f86bf61f62b3a0ce8e17e0c2312791cf0262381cd2120c2a63c9b6258963cf` | `dc93c9d960fc6b6c045807b71943c708310f2db8` | full | **48** | **键存在 0（`missing_key 48`）** | **键存在 0（`reply_to.missing_key 48`）** | **`false`** |

**两条限定**：

1. `invariance_summary.identical_among_schema_compatible_batches = true`：4 个 `schema_compatible=true` 批的三项量**逐项相同**，但其代码 sha 与 seed 不同、对话内容完全不同 ⇒ 是**结构常数**，**不是内容驱动的行为量**，**不得**当「改造会改善」的基线。
2. `invariance_note.hard_constraint` 原文：**「本不变量不得被用于论证改造无效或改造有效，只能证『公开面未接线』；任何以『三项量没变』为由否定某次改造的写法都属误用。」** 另 `v0_anchor_note`：v0 只比**结构存在性**（键存在数 0），**不比数值 48 vs 55**；`identical_scope_note`：`all_extra_batches_identical_to_main = false` 是把 schema 断代批算进去所致，判「不变量范围」应看 `identical_among_schema_compatible_batches`。

### 2.4 主结论的结构支撑：孤立节点（`S4.thread_isolation` + `msg_graph_degree` + `pub_next_to_dm`）

| # | 事实 | 实测（照录 `S4`） | 含义（结构性措辞） |
|---|---|---|---|
| F1 | 公开线程 ∩ 私聊线程（`thread_isolation`） | `pub_thread_ids 55`、`dm_thread_ids 114`、**`intersection_count = 0`**、`isolated = true` | 公开话**从不进入任何私聊线程**（出边 0） |
| F2 | DM 回指命中（`msg_graph_degree`） | `dm_reply_to_nonnull 341`、**`dm_reply_to_hit_dm_msg_uid 341`**、**`dm_reply_to_hit_pub_msg_uid 0`**；`pub_in_degree_total 0`；`pub_out_degree_zero = true` | 公开消息**从不被任何人回指**（入度 0）；**341 条回指全在 DM 内部** |
| F3a | 公开消息之后的下一条——**官方口径（`definition_official`）** | 「在 `MSG_DM`/`MSG_PUBLIC`/`MSG_GROUP` **子序列**上取紧邻下一条（**跳过非消息事件**）」⇒ `next_msg_type_histogram = {MSG_DM: 40, MSG_PUBLIC: 15}`；`within_next_3_msgs_contains_dm = 53`；`adjacent_next_msg_same_author = 0` | 在**消息序列**上，公开发言后最近的一条**消息** **40/55** 是 DM |
| F3b | 公开消息之后的下一条——**原始行序口径（`raw_row_definition`）** | 「**原始 jsonl 行序**上的下一行事件类型（**不跳过任何事件**）」⇒ **`numerator_next_raw_is_dm = 0`**、`within_next_3_raw_rows_contains_dm = 0`；`next_raw_event_type_histogram = {MEMORY_WRITE: 23, OFFER_ACCEPTED: 14, LLM_CALL: 12, MEMORY_RETRIEVE: 5, TIME_MARK: 1}` | 在**原始行序**上，紧邻的下一条**从不是消息**（多为 `MEMORY_WRITE`/`OFFER_ACCEPTED`） |

> **F3 的结论（软化后的准确表述）**：**公开说完之后，下一个「消息」40/55 是 DM；但原始行序上紧邻的下一条从不是消息（多为 `MEMORY_WRITE`/`OFFER_ACCEPTED`）** ⇒ 中间隔着状态写入。**不许**写「说完立刻转私聊」一类**时间紧邻断言**（那超出证据）。两个口径**必须并列**，这本身是有价值的发现。
> **措辞纪律**：F1–F3 只报计数与集合运算；可以说「**公开面在消息图中是孤立节点**（入度 0、出边 0）」，**不能说**「居民不想公开聊天」「改造后会改善」，也不解释成因。
> **两种说法必须分清**：✅「**接话只存在于私聊/线程内部，公开面缺席**」（`MSG_DM` 341/455 有回指 vs `MSG_PUBLIC` 0/55）；❌「整个系统没有接话」（被 341 条 DM 回指直接反证）。

### 2.5 旁证：公开线程与私聊线程完全隔离（防「一条一线程」被读成「有对话」）

55 条公开消息**各自独占**一个线程（`each_msg_owns_thread = true`、`max msgs/thread = 1`），且与 DM 的 114 个线程**交集 0**。「一条消息一条线程」是记账方式，**不等于**「有一个线程在对话」。

### 2.6 `schema_gate` / `invariance_note`（**这是这把尺子将来能当闸线的全部依据**）

**(a) `schema_gate`（实测，照录 `S4`）**

| 项 | 值 |
|---|---|
| `schema_compatible` | **`true`**；`schema_incompatible_reasons = []` |
| `missing_key_events` | `{any_of_participants_or_reply_to: 0, participants: 0, place: 0, reply_to: 0}` |
| `msg_public_events` | `55` |
| `key_presence`（主批） | `MSG_PUBLIC`：`participants 55/55`、`reply_to 55/55`、`place 55/55`；`MSG_DM`：`events 455`、`participants 455`、`reply_to 455`（`author/scope` 为 0 是因 DM 用 `from`、无 `scope`，属既定 schema） |
| `policy`（摘要） | 「取键先判 `key in payload`：缺失显式计入 `missing_key_events` 并置 `schema_compatible=false`；**绝不静默按 0 处理，也不 KeyError 崩溃；缺键样本不并入任何数值桶**」 |
| 在 v0-anchor 上的行为（`cross_batch_invariance` 第 5 行） | `MSG_DM 132 / MSG_GROUP 7 / MSG_PUBLIC 48` 的 `participants`、`reply_to` **键存在数均 0** ⇒ **`schema_compatible = false`**：**报 incompatible，不崩、不静默出 0** |

**(b) `invariance_note`（实测，照录 `S4`；含反向约束原文）**

- `claim`：「在 D2 schema 及之后的各批（d27_C / r10e2e / d28_C_s43 / d12c_on）上，『MSG_PUBLIC 条数 / participants 长度直方图 / reply_to 形态』三项量是**结构不变量**，对『生活气息』没有鉴别力……现在只能证明『公开面未接线』；将来接线后才会从 0/55 变成非零。」（**原文照录**；原文括注的『无在场多人』指「**没有形成多人线程**」，按 §2.2b 的 `participants` 定义读，**不作可见性解读**。）
- **`hard_constraint`（反向约束原文，必须顶格遵守）**：「**本不变量不得被用于论证改造无效或改造有效，只能证『公开面未接线』；任何以『三项量没变』为由否定某次改造的写法都属误用。**」
- 另有 `no_discrimination_before_wiring = true`、`not_a_quality_metric = true`、`becomes_nonzero_after_wiring = true`、`scope`、`v0_anchor_note`。

> **本节地位**：**(a) 保证跨 schema 不误读，(b) 保证不变量不被当效果判据**；二者任一缺失，这把尺子只能算「能出数」，不能算「能当闸」。

### 2.7 机制事实（源码 × `f2bf606b`）与读数事实（日志 × `1fbb9ef5…`）——**分栏，不混绑**

> 左栏「代码在 `f2bf606b` 上就是这么写的」（`file:line` 可查），右栏「这份日志里数出多少条」。**两者不许写在同一列**，也不许用左栏解释右栏的因果。`git diff --quiet f2bf606b..009e953 -- code/` 为空（附录 A-10）⇒ 可写「`f2bf606b ≡ 009e953`」。

| # | 机制事实（源码 `file:line`） | 读数事实（日志 `1fbb9ef5…`） |
|---|---|---|
| M1 | 公开消息可见性 = **全城**：`code/config/perception_scope.json:18` `"MSG_PUBLIC": "global"`；判据 `code/contracts/visibility.py:43-44` `if cls == "global": return True` | 55/55 条公开消息**各被 16 个 agent 观察**（§2.8） |
| M2 | `code/life/ports.py:72`：`participants` = **线程参与者集合**（同一 `thread_id` 内取值恒定）；取值来自计划条目 `code/life/agent.py:1122-1123` `parts = list(entry.get("participants") or [self.agent_id])`。**v3 `semantics_note` 原文**：「participants 为**线程参与者集合**……**不是收件人**（DM 的收件人是 `to`），也不是消息级可见性开关；长度 > 1 不代表多人群聊、也不代表多人接话。」 | `participants` 长度 `{1: 55}`；**线程一致性 `{169 个线程，不一致者 0}`**（§2.2b）；DM 侧长度分布见 `participants_length_dist`（53 条长度 8 而 `body` 对单人说 ⇒ **无论哪种解读都不能当收件人集合**，§3#3） |
| M3 | **`place` 被写死为 `None`**：`code/orchestration/integration.py:850` `"place": None, "scope": "global", …` | `place_value_histogram = {null: 55}`、`nonnull_place_records = 0` ⇒ 量4 的 `UNVERIFIED` 是**机制决定**的 |
| M4 | **公开模板只有 2 个**：`code/life/agent.py:107` `_PUBLIC_TEMPLATES = {"group_proposal", "job_choice"}`；通道判定链 `agent.py:1120-1134`（`_DM_TEMPLATES`→private / `_GROUP_TEMPLATES`→place_group / `_PUBLIC_TEMPLATES`→global / `elif partners:`→private / **否则维持默认 `scope="global"` 兜底**） | `topic_histogram = {skill_practice: 29, savings: 18, job_choice: 8}` ⇒ **兜底 47 条 / 显式公开模板 8 条 / `group_proposal` 0 条**（§2.7b 逐条回连，**不用减法**） |
| M5 | **H5：结构性不可能接话**：`code/life/agent.py:1163-1164`（`thread_id_public(...)` + `self._pub_k += 1`，每条公开消息**独占新线程**）、`code/life/dialogue_threads.py:146-147`（线程 id 含 `k`）、`agent.py:1165-1166`（`turn_index: 0, reply_to: None`）；而契约 `code/life/ports.py:71` 要求 `reply_to` **必须同线程且 seq 更早** ⇒ 公开面接话**结构上不可能**（**不是「忘了接线」**） | `reply_to` 非 null = **0/55**；`thread_id` 55 个、每线程 1 条 |
| M6 | **回复通路也不认 PUB**：`code/life/dialogue_threads.py:158-172` `is_replyable()` **只有 `MSG_DM`/`MSG_GROUP` 分支、无 PUB 分支**（末行 `return False`）；`code/life/agent.py:881 / 904 / 934` 三处 `if ev.type not in ("MSG_DM", "MSG_GROUP"): continue` 把公开消息过滤在接话候选之外 | 自洽：`reply_to` 命中 PUB = **0**（341 条 DM 回指全命中 DM） |

> **措辞**：M5 用「**公开面接话在结构上不可能发生**」；「没接线」较弱且不够准确。M1 + M5 合起来才支持 §2.1 的最强版主结论。

### 2.7b 公开消息来源分账（逐条回连 `SCHEDULE_PLANNED`，**不用减法倒推**）

只读探针：用 `(author, "day<day>-<slot>")` 把每条 `MSG_PUBLIC` 回连到该 agent 的 `SCHEDULE_PLANNED.slots[]`，取该 slot 的 `template_id` 与 `participants`（附录 A-11）。

| 校验项 | 实测 | 含义 |
|---|---|---|
| 消息侧 `topic` == 计划侧 `template_id` | **55 / 55 相等**；计划侧缺 slot **0** 条 | 话题可逐条对齐，无需估算 |
| 计划侧 `participants` 长度 | **`{1: 55}`** ⇒ `partners` 恒空 | `agent.py:1131 elif partners:`（→private）**本批不可能命中** |
| 计划侧 `template_id` 分布 | `skill_practice 29` / `savings 18` / `job_choice 8` | 与消息侧 `topic` 分布**逐档相等** |
| **分账** | **兜底 47 条**（`skill_practice 29` + `savings 18`：既不在 `_PUBLIC_TEMPLATES`、也不在 `_DM/_GROUP_TEMPLATES` ⇒ 走 `else` 默认 `global`）；**显式公开模板 8 条**（`job_choice`）；`group_proposal` **0 条** | 大部分公开消息**不是设计上的公开模板产出**，而是计划模板落空后的默认通道 |

### 2.8 运行时感知读数：公开消息**确被他人感知**（「看得见」的证据）

只读探针：把 `MSG_PUBLIC` 的 `seq` 与 `OBSERVATION.payload.target_event_seq` 对齐，统计每条公开消息被哪些 `observer` 观察到（附录 A-9；与 leader 口径一致）。

| 量 | 读数（`run_d27_C_n16r60_seed42` / `1fbb9ef5…`） |
|---|---|
| `MSG_PUBLIC` 条数 | **55** |
| 被**至少一个** agent 观察到的条数 | **55 / 55**（缺观察 **0** 条） |
| 每条被**非作者** observer 观察到的条数分布 | **`{15: 55}`** ⇒ 每条都被**除作者外全部 15 名居民**各感知一次 |
| **他人感知事件条数** | **825**（= 55 × 15） |
| 指向公开消息的 `OBSERVATION` 行数（含作者自观察） | **880**（= 55 × 16） |
| 感知方去重人数 | **16** |
| 对照：`MSG_DM` 每条被观察到的人数 | `{2: 453, 0: 2}`（私聊只有收发双方可见，符合 M1 的 `private` 类） |

> **结论**：**感知已接线**（825 条他人感知事件、`{15: 55}`），**回应未接线**（`reply_to` 命中 PUB **0** 条，且 §2.7 M5/M6 说明结构上不可能）⇒ **「看得见，但不回应」**。**这两件事不可混写**：不能因「无人回应」说「看不见」，也不能因「看得见」说「已接话」。
> **边界**：只报事件计数（`probe`，分母 55 < 68）；`OBSERVATION` 是内核感知层留痕，**不等于**该 agent 在对话里提到了这条消息（需另立判据，本轮未做）；**不推断**动机，**不预测**改造效果。

### 2.9 「口径来源」与「第三方复算」必须分开（本报告的正当性不依赖任何成员）

| 类别 | 写在哪 | 允许的内容 | **禁止的写法** |
|---|---|---|---|
| **口径来源** | §2 的定义 + `S4` 字段（`definition_official` / `raw_row_definition` / 各段 `stat_unit` / 分子 / 分母 / `probe`） | 「口径 = 什么单元、什么分子分母、什么档位」——**自带定义，读者不需要任何人背书** | 不写「经某人确认口径」 |
| **第三方复算** | 只作**旁证** | 「同一台机器上用另一份实现从 `run.jsonl` 独立重算，与本报告数值零偏差」——说明**数值可被第三方重现** | **不许**写「经复核确认」「以复核为准」「复核方裁定」；**不许**把复核意见当作结论成立的前提 |

> **理由（本报告的自我约束）**：若结论的正当性建立在某个成员身上，换人或犯错结论就塌。**口径必须自带定义**，复核只能证明「别人按定义重算也对」，不能替定义负责。因此本报告所有结论的成立条件只有两条：**① §2 的定义；② 附录 A 的命令能重算出 §2.1/§2.4/§2.8 的数**。

---

## 三、未达成与不可判（本节最重要）

| # | 项 | 状态 | 原因 / 边界 |
|---|---|---|---|
| 1 | 量4「公开消息同 place 相邻对」 | **不可判（`UNVERIFIED`）** | `payload.place` 键存在但**值恒 `null`**（0/55）。**根因是源码写死 `"place": None`（`integration.py:850`）** ⇒ 机制决定，非样本缺失；不插补、不用 `slot`/`topic` 顶替。 |
| 2 | 公开面「接话率」 | **不可判定** | 分母 `55 < 68` ⇒ `probe`；恒 0 只能给**未观测率上界 ≈3/55**，不得写成「0%」下结论。 |
| 3 | 「多人群聊占比」类表述 | **禁止使用** | 53 条 `MSG_DM` 的 `participants` 长度为 8，但 `body` 是对**单个人**说的一句话（**附录 A-13 复算**：物理行 2069、`msg_uid 42:2068`、`from P002 → to P009`、`participants` 8 人）⇒ `participants` 是**线程参与者集合**（同一 `thread_id` 内恒定），**不是收件人**（DM 收件人是 `to`）、**也不是消息级可见性开关**；长度 > 1 **不代表**多人群聊、也**不代表**多人接话（v3 `semantics_note` 原文，§0.3/§2.2b）。 |
| 4 | 本轮任何**效果**结论 | **无（本轮未改代码，无效果判定）** | 零跑批、零冻结区改动 ⇒ 无对照臂、无前后差异。 |
| 5 | 「基线会随改造变化」 | **不可假设** | 三项量是**结构常数**（§2.3）；`invariance_note.hard_constraint` 明令不得用于论证有效/无效。 |
| 6 | `obs llm-cost` 真伪复核 | **转引、本轮未复跑** | `provider=openai_compat`/`degraded_calls=0` 由 `meta.json` 固定；CYCLE-24 曾实测 `dialogue.cached=0`；本轮未重跑。 |
| 7 | 跨批/跨臂比较 | **不做** | 单批、单 seed（42）、单臂（C）；无重复、无 CI ⇒ 不写「显著」「因果」。 |
| 8 | 截图能否证明「公开接话缺失」 | **不能** | 截图是**对话界面物证**，**不进判据**；报告内**不给截图配任何百分数**。 |
| 9 | v0-anchor 批任何该维度**数值**比较 | **禁止** | 键存在数 0、事件类型集合不同（v0 有 `MSG_GROUP` 7 条）、`schema_compatible=false` ⇒ **只可比结构存在性，不比 48 vs 55**。 |
| 10 | `d12c_on` 批的 `code_sha` | **不可得** | 简化 schema：`code_sha = null`、`code_sha_short = a977cb0`、`meta_schema = simplified` ⇒ **只标「不可得」，不得用 `a977cb0` 冒充完整 sha**。 |
| 11 | 「说完立刻转私聊」类**时间紧邻**断言 | **禁止** | 双口径：消息子序列 **40/55**、**原始行序 0/55**（中间夹 `MEMORY_WRITE` 23 / `OFFER_ACCEPTED` 14）。两数必须并列（§2.4 F3a/F3b）。 |
| 12 | `participants` 的**语义** | **已澄清（v3）** | v3 `semantics_note`：**线程参与者集合**（同一 `thread_id` 内恒定，本批 169 个线程中不一致者 0 个），**不是收件人**（DM 收件人是 `to`），**也不是消息级可见性开关**；长度 > 1 不代表多人群聊、也不代表多人接话。此前「在场/可见集合」的旧表述**作废**（§0.4、§3#3）。 |
| 13 | `pub_next_to_dm.ratio_next_is_dm = 0.727273` | **不引用** | 分母 55 < 68 ⇒ `probe`；本报告只报事件数，比率字段留档不引用。 |

---

## 四、素材（**不参与任何判据，不给百分数**）

### 4.1 逐字片段（原文照录，标物理行号；只作样本，不作比例推断）

| 行号 | `msg_uid` | `thread_id` | `author` | `participants` | `reply_to` | 原文 |
|---|---|---|---|---|---|---|
| 54 | `42:53` | `TH-P002-PUB-0-0` | `P002` | `["P002"]` | `null` | 这木头真硬。张家那口寿材，榫头得再收半分。慢工出细活。 |
| 85 | `42:84` | `TH-P005-PUB-0-0` | `P005` | `["P005"]` | `null` | 哎，我把李婶上回抓药剩下的那几味陈皮翻出来晒晒，顺手也理理药柜子吧。 |
| 114 | `42:113` | `TH-P008-PUB-0-0` | `P008` | `["P008"]` | `null` | 周公文，我把这份户籍誊本按新格式重抄了一遍，你看这样行不行？ |

> **对照（私聊层确有承接）**：第 550 行 `msg_uid 42:549`（`TH-P004-P002-0`，`P002 → P004`）`reply_to = 42:73`；第 676 行 `msg_uid 42:675`（`TH-P009-P004-0`，`P004 → P009`）`reply_to = 42:124`。
> **读法提醒**：第 114 行那句「你看这样行不行？」是对人说话的语气，但它 `reply_to = null`、独占线程 ⇒ **在数据层没有任何人会被这句问到**（M5 说明结构上不可能有人接）。**只是样本，不是比例证据。**

### 4.2 现渲截图（2 张，本轮现场截取）

| 项 | 值 |
|---|---|
| 目录 | `v2/evidence/public_talk_shots/`（`README.md` + `render_report_PUBTALK-C.json` + `threads_PUBTALK-C.json` + 2 PNG） |
| 图源 | `run_d27_C_n16r60_seed42`（与 §2 同一份日志，`sha256 = 1fbb9ef5…186`） |
| 文件名 | `PUBTALK-C-chat-1fbb9ef5.png`（1400×900）、`PUBTALK-C-rhythm-1fbb9ef5.png`（1300×1050） |
| 渲染命令 | `PYTHONDONTWRITEBYTECODE=1 /opt/openjiuwen/workswarm-venv/bin/python3 -B tools/metrics/render_shots_extra.py --run-dir <RUN> --batch-id PUBTALK-C --outdir v2/evidence/public_talk_shots --views chat,rhythm --timeout 240` → `rc=0, ok_count=2, fail_count=0` |
| 像素自检 | chat `distinct_colors=24,015 / top_color_frac=0.1417 / non_bg_frac=0.5824`；rhythm `22,374 / 0.2620 / 0.4746`，两张 `status=OK` |
| 与读数引用的日志是否同一份 | **是**：`render_report_PUBTALK-C.json` 的 `log_sha256` = `run_sha256_in_threads` = `1fbb9ef5161fd07aa68fcc9fc4038f104ff18b56383a2fc6b31bb3cb5486a188`，与 `S1` 逐字符一致 |
| **免责（原文级）** | **该图是对话界面物证，不是公开接话指标的证据**；不参与任何判据、**不给任何百分数**、不得与其它批/臂的图混拼。 |

---

## 五、下一轮计划（每条写「完成条件」，不写「打算做」）

1. **开分支 `feat/public-reply`**
   - 完成条件：从 `master` 当前 HEAD 切出，`git branch --contains` 可查；**`code/life` 之外零改动**；分支内先写改动说明与影响面。
2. **预登记判据（跑前写死，落 `v2/refs/public-reply-prereg.md`），覆盖 H1–H5 五处最小改动点**
   - **H1** 回复通路不认 PUB：`code/life/dialogue_threads.py:158-172` `is_replyable()` 无 PUB 分支（返回 `False`）⇒ 新增 PUB 分支（同线程、非本人、可回）。
   - **H2/H3/H4** 三处过滤器：`code/life/agent.py:881`（`_thread_max_turn`）、`:904`（`_pick_reply_target`）、`:934`（`_thread_history`）均为 `if ev.type not in ("MSG_DM", "MSG_GROUP"): continue` ⇒ 三处都要放行 `MSG_PUBLIC`。
   - **H5** 公开线程 id 须**可复用**：`agent.py:1163-1164` + `dialogue_threads.py:146-147` 现为每条消息新建 `TH-<人>-PUB-<round>-<k>`，而契约 `ports.py:71` 要求 `reply_to` 同线程且 seq 更早 ⇒ 必须让同轮同场所/同话题的公开消息**共享线程 id**，否则接话**结构上不可能**。
   - 判据写死：M1（结构闸：改后 `MSG_PUBLIC` 的 `reply_to` 非 null 条数 > 0 且目标能在本批 `msg_uid` 命中）、M2（同线程 `turn_index` 连续 +1；`participants` 语义经抽检确认）、P1/P2（两臂同 seed 同规模）、**每量分母与 `probe` 档位**。
3. **两臂跑批**
   - 完成条件：B 臂 `n16r60` 两 seed（42/43）跑完，`run_batch.rc=0`、`meta.events == wc -l`、`obs llm-cost --require-provider openai_compat` rc=0 且 `degraded=0`，日志 sha256 与 `meta.run_sha256` 三方自洽；C 臂复用既有批，**不得跨树混用**。
4. **收批首检**
   - 完成条件：核**树路径**（B 臂必须取自 `feat/public-reply` worktree）+ 臂判别量；错树立即作废并留痕。
5. **本轮遗留的计量补口**
   - 完成条件：① 量4 的 `place`：或让 `MSG_PUBLIC.payload.place` 非 null 覆盖率达 100%，或在 `v2/refs/` 明确宣告**永久不可判**并删该组；② `participants` 语义统一（§3#12）；③ **若改线程复用，必须同步 `code/life/agent.py:308-345` 的前向重建块**（`slot_msgs` / `thread_replied` / `replied_uids`）。

> **风险栏（必须与 H5 一起看）**：改「线程 id 可复用」会直接影响前向重建状态（`agent.py:308-345`）。**不同步该块 ⇒ 续跑会重复发消息/重复接同一轮 ⇒ 破 T276「续跑与一次性跑逐字节一致」**。预登记里必须列为「必检项」。
> **红线**：真正实现接话**必须动 `code/life`**（冻结区）⇒ **必须开分支 + 预登记判据写死 + 两臂跑批**；**不得在本轮混入**（本轮为纯只读基线）。

---

## 附录 A · 复算命令（**全参数**，逐条对应正文读数）

> **铁律 R1**：以下命令**一个参数都不许省**——`--meta` **与 4 个 `--extra-log` 都在**。省 `--extra-log` ⇒ `cross_batch_invariance: []`，复算不出 `S4`。
> **执行前提（R3，隐性前提，必须写明）**：**必须在仓库根目录执行**（`cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment`）。命令里的路径全是**相对路径**，换目录跑会「找不到文件」，不是尺子的问题。
> **R2/R4/R5**：`S4`（`971dcb3b…`）成立前提是「`S1` + `S2` + 本附录命令」；`--out` 记为 `<OUT>` 占位 ⇒ **换输出路径 sha 相同**；`--repo-head` 显式声明 ⇒ **HEAD 前进也不变**（§1.1 三路径 + HEAD=3869428 实测）。
> **期望值**：`S3 = 15e7f048…`、`S4 = 971dcb3b…`（§0.1 现行值）。
> **钉住 vs 不钉（抗「复算对不上」的说明）**：本报告**只采用钉住形态**（带 `--repo-head`）；省略该参数得到的未钉形态 sha 为 `606d883f39ebc846cbc04b782398dc654fa5dab170de0d372465e9a881750089`，与钉住形态的差别**仅** `inputs.repo_head_declared`（`null` vs `009e9531…`）与 `repo_head_declared_valid`（`false` vs `true`）**两行**（外加 `invocation.argv` 里的参数本身），**数值段逐项相同**。若你复算出 `606d883f…`，说明漏了 `--repo-head`，不是证据不一致。
> **抄命令**：A-1 与 `S4.invocation.argv_joined` **逐字一致**（含 `--repo-head` 40 位完整），唯一差别是 `--out <OUT>` 占位需替换成真实路径；写回仓库内正式路径即得同一 sha。

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
M=v2/evidence/run_d27_C_n16r60_seed42

# A-1 主线 + 全部结构段（＝§2 全表）
python3 tools/public_talk/public_talk_metrics.py \
  --log $M/run.jsonl --meta $M/meta.json \
  --extra-log v2/evidence/run_r10e2e_n16r60_seed42/run.jsonl \
  --extra-log v2/evidence/run_d28_C_s43_n16r60_seed43/run.jsonl \
  --extra-log v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl \
  --extra-log v2/evidence/run_d2_before_n16_seed42/run.jsonl \
  --repo-head 009e95310c5221aef47c9c36f41ddad4f11e627b \
  --out v2/evidence/public_talk_readings_d27_C_n16r60_seed42.json
sha256sum v2/evidence/public_talk_readings_d27_C_n16r60_seed42.json
# 期望 = §0.1 S4：971dcb3b01359d21b7c6cad8742676f8a409816d67b99dc439a577b8734fce2b

# A-2 只比数值（输出到 /tmp，比较时排除 invocation 段）
python3 tools/public_talk/public_talk_metrics.py \
  --log $M/run.jsonl --meta $M/meta.json \
  --extra-log v2/evidence/run_r10e2e_n16r60_seed42/run.jsonl \
  --extra-log v2/evidence/run_d28_C_s43_n16r60_seed43/run.jsonl \
  --extra-log v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl \
  --extra-log v2/evidence/run_d2_before_n16_seed42/run.jsonl \
  --repo-head 009e95310c5221aef47c9c36f41ddad4f11e627b \
  --out /tmp/pt_check.json
python3 - <<'EOF'
import json
a=json.load(open('/tmp/pt_check.json')); b=json.load(open('v2/evidence/public_talk_readings_d27_C_n16r60_seed42.json'))
a.pop('invocation',None); b.pop('invocation',None)
print('numerically_identical =', a==b)     # 期望 True（v4 起换路径也应 sha 相同，见 A-1 注）
EOF

# A-3 结构事实（线程数 / turn_index / scope）
python3 - <<'EOF'
import json,collections
p='v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'
sc=collections.Counter();ti=collections.Counter();tid=collections.Counter();tot=0
for line in open(p,encoding='utf-8'):
    r=json.loads(line)
    if r.get('type')=='MSG_PUBLIC':
        pl=r['payload']; tot+=1
        sc[pl.get('scope')]+=1; ti[pl.get('turn_index')]+=1; tid[pl.get('thread_id')]+=1
print('MSG_PUBLIC',tot,'threads',len(tid),'max_per_thread',max(tid.values()),
      'scope',dict(sc),'turn_index',dict(ti))   # 55 / 55 / 1 / {'global':55} / {0:55}
EOF

# A-4 作者集合与「未公开发言的 4 人」
python3 - <<'EOF'
import json
p='v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'
a={json.loads(l)['payload']['author'] for l in open(p,encoding='utf-8') if json.loads(l).get('type')=='MSG_PUBLIC'}
born={json.loads(l)['payload']['agent_id'] for l in open(p,encoding='utf-8') if json.loads(l).get('type')=='AGENT_BORN'}
print('public_authors',len(a),sorted(a));print('born',len(born));print('born_not_public',sorted(born-a))
EOF

# A-5 跨批结构常数（＝§2.3；也可直接读 S4.cross_batch_invariance）
python3 - <<'EOF'
import json,hashlib,collections
for b in ['run_d27_C_n16r60_seed42','run_r10e2e_n16r60_seed42','run_d28_C_s43_n16r60_seed43',
          'run_d12c_on_n16r60_seed42','run_d2_before_n16_seed42']:
    p=f'v2/evidence/{b}/run.jsonl'; h=hashlib.sha256(open(p,'rb').read()).hexdigest()
    pub=0; plen=collections.Counter(); rt=collections.Counter()
    for line in open(p,encoding='utf-8'):
        r=json.loads(line)
        if r.get('type')=='MSG_PUBLIC':
            pub+=1; pl=r.get('payload') or {}
            plen[len(pl['participants'] or []) if 'participants' in pl else 'missing_key']+=1
            rt['missing_key' if 'reply_to' not in pl else ('null' if pl['reply_to'] is None else 'nonnull')]+=1
    print(b,h,'MSG_PUBLIC',pub,'plen',dict(plen),'reply_to',dict(rt))
EOF

# A-6 接话在哪一层（＝§2.4 F2 前半）
python3 - <<'EOF'
import json,collections
p='v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'
c=collections.Counter()
for line in open(p,encoding='utf-8'):
    r=json.loads(line); t=r.get('type')
    if t in ('MSG_DM','MSG_PUBLIC'):
        rt=(r.get('payload') or {}).get('reply_to')
        c[(t,'nonnull' if rt not in (None,'','None') else 'null')]+=1
print(dict(c))   # DM nonnull 341 / DM null 114 / PUB null 55
EOF

# A-7 来源身份（sha256 对账）
sha256sum $M/run.jsonl $M/meta.json \
          tools/public_talk/public_talk_metrics.py \
          v2/evidence/public_talk_readings_d27_C_n16r60_seed42.json \
          v2/evidence/public_talk_shots/*

# A-8 孤立节点三件（§2.4 F1/F2/F3，消息子序列口径）
python3 - <<'EOF'
import json
p='v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'
rows=[]
for line in open(p,encoding='utf-8'):
    r=json.loads(line)
    if r.get('type') in ('MSG_DM','MSG_PUBLIC'): rows.append((r['type'],r['payload']))
pub=[x for x in rows if x[0]=='MSG_PUBLIC']; dm=[x for x in rows if x[0]=='MSG_DM']
pub_tid={pl.get('thread_id') for _,pl in pub}; dm_tid={pl.get('thread_id') for _,pl in dm}
pub_uid={pl.get('msg_uid') for _,pl in pub}; dm_uid={pl.get('msg_uid') for _,pl in dm}
nonnull=[pl for _,pl in dm if pl.get('reply_to') not in (None,'','None')]
print('F1 pub_tid',len(pub_tid),'dm_tid',len(dm_tid),'intersection',len(pub_tid&dm_tid))   # 55/114/0
print('F2 nonnull',len(nonnull),'hits_dm',sum(1 for pl in nonnull if pl['reply_to'] in dm_uid),
      'hits_pub',sum(1 for pl in nonnull if pl['reply_to'] in pub_uid))                    # 341/341/0
nxt=within3=same=0
for i,(t,pl) in enumerate(rows):
    if t!='MSG_PUBLIC': continue
    if i+1<len(rows) and rows[i+1][0]=='MSG_DM':
        nxt+=1
        if rows[i+1][1].get('from')==pl.get('author'): same+=1
    if any(rows[j][0]=='MSG_DM' for j in range(i+1,min(i+4,len(rows)))): within3+=1
print('F3a msg_subseq next_is_DM',nxt,'within3',within3,'same_author',same)   # 40/53/0
EOF

# A-8b 原始行序口径（§2.4 F3b）：紧邻的下一行是什么、3 行内有无 DM
python3 - <<'EOF'
import json,collections
p='v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'
lines=open(p,encoding='utf-8').read().splitlines()
idx=[i for i,l in enumerate(lines) if '"type":"MSG_PUBLIC"' in l]
nxt=collections.Counter(); nxt_dm=within3=0
for i in idx:
    if i+1<len(lines): nxt[json.loads(lines[i+1])['type']]+=1
    if i+1<len(lines) and json.loads(lines[i+1])['type']=='MSG_DM': nxt_dm+=1
    if any(json.loads(lines[j])['type']=='MSG_DM' for j in range(i+1,min(i+4,len(lines)))): within3+=1
print('raw_next_histogram',dict(nxt)); print('raw_next_is_DM',nxt_dm,'raw_within3_DM',within3)
# 期望 raw_next_is_DM 0 / raw_within3_DM 0；hist 多为 MEMORY_WRITE / OFFER_ACCEPTED
EOF

# A-9 运行时感知（§2.8）：OBSERVATION.target_event_seq 对齐 MSG_PUBLIC.seq
python3 - <<'EOF'
import json,collections
p='v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'
pub={}; obs=collections.defaultdict(set)
for line in open(p,encoding='utf-8'):
    r=json.loads(line); t=r.get('type'); pl=r.get('payload') or {}
    if t=='MSG_PUBLIC': pub[r['seq']]=pl.get('author')
    elif t=='OBSERVATION': obs[pl.get('target_event_seq')].add(pl.get('observer'))
tot=others=0; dist=collections.Counter(); allobs=set()
for s,a in pub.items():
    o=obs.get(s,set()); allobs|=o
    tot+=len(o); others+=len(o-{a}); dist[len(o-{a})]+=1
print('pub',len(pub),'obs_rows_total',tot,'others_rows',others,'dist',dict(dist),'observers',len(allobs))
# 期望 pub 55 / 880 / 825 / {15: 55} / 16
EOF

# A-10 源码身份一致性（机制事实栏的 sha 依据）
for f in code/life/ports.py code/contracts/visibility.py code/config/perception_scope.json \
         code/orchestration/integration.py code/life/agent.py code/life/dialogue_threads.py; do
  git diff --quiet f2bf606b..009e953 -- "$f" && echo "$f IDENTICAL(f2bf606b==009e953)"
done

# A-11 公开消息来源分账（§2.7b）
python3 - <<'EOF'
import json,collections
p='v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'
plan={}; pubs=[]
for line in open(p,encoding='utf-8'):
    r=json.loads(line); t=r.get('type'); pl=r.get('payload') or {}
    if t=='SCHEDULE_PLANNED':
        for s in pl.get('slots') or []: plan.setdefault((pl.get('agent_id'), s.get('slot_id')), s)
    elif t=='MSG_PUBLIC': pubs.append(pl)
match=miss=0; tmpl=collections.Counter(); plen=collections.Counter()
for pl in pubs:
    s=plan.get((pl.get('author'), f"day{pl.get('day')}-{pl.get('slot')}"))
    if not s: miss+=1; continue
    match += (s.get('template_id')==pl.get('topic'))
    tmpl[s.get('template_id')]+=1; plen[len(s.get('participants') or [])]+=1
print('pub',len(pubs),'plan_missing',miss,'topic_eq_template',match,
      'templates',dict(tmpl),'plan_participants_len',dict(plen))
# 期望 55 / 0 / 55 / {skill_practice:29, savings:18, job_choice:8} / {1: 55}
EOF

# A-12 线程一致性 + 发送方在 participants 内（＝§2.2b）
python3 - <<'EOF'
import json,collections
p='v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'
parts_by_thread=collections.defaultdict(set); ok=tot=0; fa=0
for line in open(p,encoding='utf-8'):
    r=json.loads(line); t=r.get('type'); pl=r.get('payload') or {}
    if t in ('MSG_DM','MSG_PUBLIC'):
        parts_by_thread[pl.get('thread_id')].add(tuple(pl.get('participants') or []))
        sender = pl.get('from') if t=='MSG_DM' else pl.get('author')   # DM 无 author 字段！
        tot+=1; ok += (sender in (pl.get('participants') or []))
    if t=='MSG_DM': fa += (pl.get('author') not in (pl.get('participants') or []))
print('threads',len(parts_by_thread),
      'inconsistent',sum(1 for v in parts_by_thread.values() if len(v)>1),
      'sender_in_participants',ok,'/',tot,
      'DM_author_based_false_alarms',fa)
# 期望 threads 169 / inconsistent 0 / sender_in_participants 510 / 510 / false_alarms 455
EOF

# A-13 §3#3 的样例外推（物理行 2069 / msg_uid 42:2068）
python3 - <<'EOF'
import json
p='v2/evidence/run_d27_C_n16r60_seed42/run.jsonl'
for i,line in enumerate(open(p,encoding='utf-8'),1):
    r=json.loads(line); pl=r.get('payload') or {}
    if r.get('type')=='MSG_DM' and pl.get('msg_uid')=='42:2068':
        print('line',i,'from',pl.get('from'),'to',pl.get('to'),
              'len(participants)',len(pl.get('participants') or []),'body',(pl.get('body') or '')[:40])
        break
# 期望 line 2069 / from P002 / to P009 / len 8（body 是对单个人说的一句话）
EOF
```

> **口径声明**：A-3/A-4/A-5/A-6/A-8/A-8b/A-9/A-11/A-12 是**本报告为复算写的只读探针**（`stdin` heredoc，不落仓库），与本报告数值**同源同算法**；尺子（`S3`）不含 `MSG_DM` 明细、感知层与计划侧回连，故这几条只作**旁证**，不参与结论升级。**A-8/A-9 与 `S4` 的 `thread_isolation` / `msg_graph_degree` 独立吻合**（55/114/0、341/341/0）。

## 附录 B · 入库与提交纪律

1. **只按明确路径 `git add`（10 条白名单）**：
   - `reports/R24-public-talk-baseline.md`
   - `tools/public_talk/public_talk_metrics.py`
   - `v2/evidence/public_talk_readings_d27_C_n16r60_seed42.json`
   - `v2/evidence/public_talk_shots/README.md`
   - `v2/evidence/public_talk_shots/render_report_PUBTALK-C.json`
   - `v2/evidence/public_talk_shots/threads_PUBTALK-C.json`
   - `v2/evidence/public_talk_shots/PUBTALK-C-chat-1fbb9ef5.png`
   - `v2/evidence/public_talk_shots/PUBTALK-C-rhythm-1fbb9ef5.png`
   - `v2/evidence/preflight/preflight_20261024T160342Z_009e9531_survey_probe.log`
   - `v2/evidence/preflight/clean_tree_20261024T160342Z_009e9531_survey_probe.json`
2. **严禁 `git add -A` / `git add .`**：工作区另有与本轮无关的未跟踪项（`code/frontend/sample/dialogue_*` 13 个、`tools/f2/r10e2e_forget_levels.py`、`v2/evidence/forget_levels_*.json`、其它 preflight 日志、`run_d28_*` 等）一律**不入库**；提交前用 `git status --porcelain` 逐项核对，**暂存清单必须与白名单一字不差**。
3. **不修改冻结区**（`code/life`、`code/orchestration`、`code/config`、`code/engine`）。
4. **提交与推送分离**：`git commit` 可先做；**`git push` 须等 leader 放行**（终审四条目：读数 sha 是否新版 / `code_sha` 是否 `f2bf606b` / 有无引用判过「不可引用」的东西 / 复算命令是否含全参数）。
5. **提交信息**写明「本轮推进了什么维度 + 判据 + 证据文件」。

## 附录 C · 本报告自我限定

1. 单批、单 seed（42）、单臂（C，`n16r60`）快照；**不跨批比较、不给 CI、不写「显著」「因果」**。
2. 分母 `55 < 68` ⇒ §2.1 全部 `probe`；**只报事件数，不报比率**；唯一 `≈3/55` 是**未观测率上界**，不是观测比率；`pub_next_to_dm.ratio_next_is_dm`（`0.727273`）**留档不引用**（§3#13）。
3. **本轮未改任何行为代码、未跑批、未调用 LLM** ⇒ **无任何效果判定**；§2.1/§2.4/§2.8 的结论是**结构事实 + 运行时观测**，不涉动机、不解释成因。
4. §2.3/§2.6：三项量是**结构常数**；`invariance_note.hard_constraint` 明令**不得**用于论证改造有效或无效。
5. **栏位纪律**：机制事实绑**源码 `file:line` + `f2bf606b`**；读数事实绑**日志 `1fbb9ef5…`**；`009e953` 只作「入库时仓库 HEAD」（附录 A-10 证明相关源码在两 sha 上逐字节相同）。
6. **复现前提**：`S4` 的 sha256 依赖「日志 + `meta.json` + 全参数命令行（`--meta` + 4×`--extra-log`）」三元组（§0.5）。
7. 截图是**物证类别**，不参与判据、**不配任何百分数**；不得与其它批/臂的图混拼。
8. 已知**未验证/未做**：§3 全表（尤其 `obs llm-cost` 未复跑、`d12c_on` 的 `code_sha` 不可得、`participants` 语义口径冲突）。
9. S7/S8 为团队工作区文件（不入仓库）；凡进入 §2 表的数值均由附录 A **独立复算**。
