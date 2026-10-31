# R41 · 2026-10-31 公开面接话机制（public-face reply）实验报告

> **文件命名与并存说明**：本轮周期报告 `reports/CYCLE-41-20261031.md` 已有另一份（提交 `825496a`，执行人 `report-writer`）。本文件**不覆盖、不改写**它，只交付 **R41 单一维度**（公开面接话机制）的可复算报告；两文件并存，读者按需取用。仓库 `reports/` 既有 `CYCLE-<序号>-<日期>.md`（周期报告族）与 `R<序号>-<主题>.md`（单维度报告族）两套命名，本文件属后者。

> 执行人：`round-reporter`（报告与交付收口），模型 `DeepSeek-V4.1-Flash-1017`。
> **本轮结论口径（唯一允许写法）**：**机制已实现，质量未判。**
> 已交付＝代码实现（`2af557f`）+ 五处改动的等价性论证（静态调用点 + 类型上界，**非形式化验证**）+ 回归级测试（`309 passed`，其中 127 例直覆盖改动面；由 `life-engineer` 实测）+ 前基线实测（双路径 sha256 `9b2d68cb…` 一致）+ 两张前基线诊断图。
> 未完成＝OFF/ON 双臂验证批（第三方 d9t 批 25 分钟内三次重起，占同一 LLM 端点；我方门禁通过后 7 秒被插入，按并发纪律立即中止）。
> 因此：**本轮新增 LLM 成本 = 0**、**无行为级读数**、**无 `place_adjacency` 可判性验证**、**无前后对比图**。
> 禁止表述：生活气息提升 / 接话机制有效 / 公开面已接上话。
> 报告内每个数字都给出可原样执行的命令；每条结论绑定 commit sha（见 §⑤）。
> 代码身份与报告身份分绑：**代码 = commit A `<SHA_A>`**，**报告与读数 = commit B `<SHA_B>`**（§⑤）。

---

## ⓪ 基线更正（交付物的一部分，不是可选项）

本轮开工时，项目内对「公开面」的现状存在一处**已在仓库内固化的过期表述**，必须先更正，否则后续所有读数会被误读。

| 位置 | 原文 | 状态 |
|---|---|---|
| `v2/00-roadmap.md:93` | `MSG_PUBLIC \| 0 \| 公开/布告未实现（事件已登记，运行时未产出）` | **已过期** |
| `v2/00-roadmap.md:94` | `MSG_GROUP \| 0 \| 群组/场所聊未实现` | 数量正确（见下），但"未实现"需限定 |
| `reports/R24-public-talk-baseline.md:43` | `msg_counts = {MSG_DM: 455, MSG_PUBLIC: 55}` | **正确，未过期** |

**更正结论（以本轮实测为准）**：
1. **`MSG_PUBLIC` 并非恒为 0**。两批实测（命令见下）：r38 on 批 `MSG_PUBLIC=24`、d12d 批 `MSG_PUBLIC=55`。
2. **恒为 0 的是 `MSG_GROUP`**：两批均 0 条命中。
3. **R24 的 55 条计数本就正确**，需要更正的**不是 R24 原文**，而是"MSG_PUBLIC 总量为 0"这一**转述**——R24 `:152` 写的「**0 条**」指的是「55 条公开消息中 `reply_to` 非 null 的条数 = 0」，即**有公开发言、但零接话**，与"没有公开发言"是两件事。
4. 因此本轮维度表述统一为「**公开面接话机制**」，**不使用**「让 MSG_PUBLIC 从 0 变正」——后者在事实上是错的。

复算命令（仓库根执行，与本报告 §③ 的 A 基线条目同源）：

```bash
grep -o '"type":"MSG_[A-Z]*"' v2/evidence/r38_f3_batch/on/run.jsonl | sort | uniq -c
#   167 "type":"MSG_DM"
#    24 "type":"MSG_PUBLIC"
grep -o '"type":"MSG_[A-Z]*"' v2/evidence/run_d12d_on_n16r60_seed42/run.jsonl | sort | uniq -c
#   455 "type":"MSG_DM"
#    55 "type":"MSG_PUBLIC"
# MSG_GROUP：两批均 0 条命中（同一命令下无该行输出）
```

---

## ① 本轮推的维度与看板现状

**看板现状一句**：在最近两批真实日志上，公开面**有发言、无接话**——公开消息是**纯广播**：每条各自独占一个线程、`turn_index` 恒 0、`reply_to` 恒 null、在消息图里入度与出度均为 0。这正是"小镇不像小镇"最刺眼的一处：真实小镇里大部分话是当着别人说的、并且会被接上。

| 项 | 值 | 来源 |
|---|---|---|
| 本轮推的维度 | **公开面接话机制**（`MSG_PUBLIC` 能否被在场者接上） | 本文 §② |
| 臂 | `HITT_DIALOGUE_PUBLIC_REPLY`（默认 OFF） | `code/life/public_talk.py:1-40` |
| 效果层达标项 | **0 / 0**（本轮验证批未执行 ⇒ 无任何效果层读数；不是「跑了没达标」，而是「一次都没跑」） | §③.3 |

---

## ② 改了什么

### 2.1 代码身份

| 项 | 值 |
|---|---|
| 分支 | `feat/life-public-talk-r41` |
| **代码 sha（commit A）** | `2af557f6356855b459d84a2055fc7459e5ca6963`（短 `2af557f`，16:16:12） |
| commit A 的 author | `life-evidence-analyst <life-evidence-analyst@jiuwenswarm.local>`（**仓库 git user 配置值**；实际改动由 `life-engineer` 完成） |
| 本轮证据 commit | `425b0af`（6 files / +523：前基线读数、24 条 `MSG_PUBLIC` 原文、pid 取证、并发作废留证、preflight 原文、双臂脚本） |

`git show --stat --oneline 2af557f` 实测输出原文：

```
2af557f feat(life): public-face reply mechanism (R41 A arm, OFF-equivalent)
 code/life/agent.py                      |  47 ++++++--
 code/life/public_talk.py                | 149 ++++++++++++++++++++++++
 code/life/tests/test_r41_public_talk.py | 196 ++++++++++++++++++++++++++++++++
 code/orchestration/integration.py       |  29 ++++-
 4 files changed, 411 insertions(+), 10 deletions(-)
```

### 2.2 五处改动（逐处：位置 / before→after / 等价性论证级别）

> 说明：本节**不使用**"逐字节等价"作为总括，因为其中两处是**表达式重排**而非字符相同；等价性按级别分列。

| # | 位置 | before → after | 等价性论证级别 |
|---|---|---|---|
| ① | `code/life/agent.py:1116`（`_thread_max_turn`）、`:1145-1155`（`_pick_reply_target`）、`:1184`（`_thread_history`） | `if ev.type not in ("MSG_DM","MSG_GROUP")` → `types = ("MSG_DM","MSG_GROUP","MSG_PUBLIC") if PT.enabled() else ("MSG_DM","MSG_GROUP")`，判定改为 `if ev.type not in types` | **OFF 取原元组字面量**（`PT.enabled()` 为假时右侧就是原元组），白名单集合与接入前相同 |
| ② | `code/life/agent.py:1341`（`_send_reply` 的 scope） | `"scope": "private" if ev.type=="MSG_DM" else "place_group"` → `"scope": (PT.reply_scope(ev.type) if (PT.enabled() and ev.type=="MSG_PUBLIC") else ("private" if ev.type=="MSG_DM" else "place_group"))` | **表达式重排 + 短路取原式**：OFF 时条件恒假，落回原三元表达式，取值相同（不是逐字符相同） |
| ③ | `code/life/agent.py:1307` | `partner = p.get("from")` → `partner = p.get("from") or p.get("author")` | **行为等价但表达式确实变了**。OFF 下等价前提＝「DM/GROUP payload 必带 `from`」（`integration.py` private / place_group 分支均写 `"from": agent_id`）；"有 `author` 无 `from`"只出现在 `MSG_PUBLIC`，OFF 不可达。经验旁证：`MSG_DM/MSG_GROUP` 共 789 条实测 `from` 全非空（`r38 on` 167/167、`d12d` 622/622，`bad_from=0`） |
| ④ | `code/life/agent.py:1365-1372` | `else:` → `elif ev.type == "MSG_GROUP":`，并新增 `elif PT.enabled() and ev.type == "MSG_PUBLIC":` | **不可达路径论证**（见 2.3） |
| ⑤ | `code/life/agent.py:378`、`:1369-1372` | 新增 `self._slot_public_replies`（slot→计数）与只追加审计键 `payload["ctx"]["public_reply"] = PT.audit(...)`，并自增配额 | **只追加**：OFF 时 `public_reply` 键不出现、计数器不增（`PT.enabled()` 为假，该 `elif` 不进入） |

跨目录 additive 改动（单独列出，不混进 `code/life` 一并带过）：

| 位置 | 改动 | 理由 |
|---|---|---|
| `code/orchestration/integration.py:170-190`（新增 `_r41_public_place`）+ `:868-878`（`MSG_PUBLIC.payload["place"]`） | `"place": None` → `"place": _r41_public_place(agent_id, st)`；OFF 时该函数恒返回 `None` | ①「同 place 同 slot 上限」「是否与听者同处」两条有界判据需要 place；② 顺带解开 `tools/public_talk/public_talk_metrics.py` 第 4 组 `place_adjacency` 的 `UNVERIFIED`（该组长期不可判的根因是 `payload.place` 恒 null） |

新增模块与测试：

| 文件 | 行数 | 作用 |
|---|---|---|
| `code/life/public_talk.py` | 149（新增） | 开关 `HITT_DIALOGUE_PUBLIC_REPLY`（仅 `{1,true,yes,on}` 算开）；四条有界判据；配额常量 `MAX_PER_AGENT_PER_SLOT=1` / `MAX_PER_PLACE_PER_SLOT=2`；`reply_scope()`；`audit()`。**不调 LLM、不改世界态、不发事件** |
| `code/life/tests/test_r41_public_talk.py` | 196（新增） | 29 例：开关语义 / OFF 等价 / 四条判据 / 配额 / 频道映射 / place 注入 |

### 2.3 OFF 等价性的论证级别（按级别分列，并保留边界声明）

- **A 生产侧唯一单链**：`_communicate`（`agent.py:649`）→ `_pick_reply_target`（`:1103`）→ `_send_reply`（`:1104`）。`grep -n "_send_reply" code/life/agent.py` 实测生产调用点仅 `:1104` 一处。
- **B OFF 时入参类型上界**：`_pick_reply_target` 循环体（`:1145-1155`）在 `PT.enabled()` 为假时走 `else` 分支，首句 `if ev.type not in ("MSG_DM","MSG_GROUP"): continue` ⇒ OFF 下 `_send_reply` 入参只可能是 DM/GROUP ⇒ 改动④的「非 DM 非 GROUP」分支**不可达**。
- **C 测试侧直接调用 10 处**：`test_r19_topic_breadth.py:88`、`test_f3_emotion_echo.py:97`、`test_scene_anchor.py:236,261`、`code/tests/test_dialogue_repair.py:252,269,362,447,459`；实测构造全部 `type="MSG_DM"` ⇒ 不构成反例，属完整边界扫描。
- **D 边界声明（原样保留）**：
  > 该等价性为**静态调用点 + 类型上界**证明，**非形式化验证**；若未来新增代码以其它事件类型直接调用 `_send_reply`，结论即失效。当前树（`a6470a1` + 本轮改动）除 A/C 外无其它调用点。

### 2.4 验证小节（证据层级必须标注）

```bash
python3 -m pytest code/life/tests/test_r41_public_talk.py -q
# .............................                                            [100%]
# 29 passed in 0.16s

cd code && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider life/tests tests/test_dialogue_repair.py
# 309 passed（life-engineer 实测；报告侧独立复核 test_r41_public_talk.py 得 29 passed）
```

> **证据层级必须标清**：`29 passed`（R41 单测）+ `309 passed`（`life/tests` + `tests/test_dialogue_repair.py` 回归）都是**纯单元/回归测试**：无 LLM 调用、无仿真轮次。它们证明 **OFF 路径等价** 与 **ON 的四条有界判据、配额常量在代码层成立**，其中 **127 例直接覆盖本轮改动面**；**不构成行为级验证**。行为级证据只来自真实跑批的 `obs llm-cost`、公开面尺子读数与公开对话原文——本轮没有这些。

---

## ③ 观测数据

### 3.1 尺子未改动（前后同尺同口径，差异可直接归因于数据与行为）

本轮**未修改**公开面尺子 `tools/public_talk/public_talk_metrics.py`：

```bash
git status --short tools/public_talk/            # → 空
sha256sum tools/public_talk/public_talk_metrics.py
# 15e7f0481c5ba307b8c7f39184dd7cbe747be3f9ac7d2777c443ea8ddba44a77
git log -1 --format='%h %H %s' -- tools/public_talk/public_talk_metrics.py
# 62e301c 62e301c063786f3948dac84880c57ee620dbd814 fix(ruler v4): 读数与 git HEAD 解耦，修 D8
```

> 三标识并列（不合并）：**git sha `62e301c`** / **文件内自述版本 `v2`（见脚本 :8）** / **sha256 `15e7f048…`**。本轮前后读数由**同一把尺子、同一口径**测得，差异可直接归因于数据与行为改动，无需跨版本校准。

### 3.2 A 前基线（r38 on 批，尺子 v4 / `62e301c`）

数据源：`v2/evidence/r38_f3_batch/on/run.jsonl`（sha256 `af120876cd314b8f1b31a3f380081374da1c32db863ae4c1c21854bc16410a7f`，33,853 行）；跑批代码身份 `code_sha=afde63c`（`meta.json`）；规模 seed=42 / agents=16 / rounds=24 / model=DeepSeek-Flash / provider=openai_compat。

复算命令：

```bash
python3 tools/public_talk/public_talk_metrics.py \
  --log v2/evidence/r38_f3_batch/on/run.jsonl \
  --meta v2/evidence/r38_f3_batch/on/meta.json
# 仓库内已落盘件：v2/evidence/r41_public_talk/pubtalk_r38on_METRICS_BASELINE.json
#   sha256 9b2d68cb56e02fe2df7f84950cf532f5e3d4e17dd55ab6f747afd01125f82a29
```

> **双路径一致（独立性证明）**：该基线件由两条独立路径分别计算——life-engineer 侧自算、本轮报告侧独立复算——**输出文件逐字节一致（sha256 `9b2d68cb…`）**，排除单路径计算错误。审阅者可自行跑第三遍。

| 组 | 读数 | 判读 |
|---|---|---|
| 第 1 组 `msg_public_total` | `24`（`probe`，本量自身即分母） | 24 次公开发言 |
| 第 2 组 `participants_length_dist` | 长度直方图 `{1: 24}`；`len>1 = 0`；分母 24 | 24 条公开消息**每条只有 1 个参与者**：零对多、零对话 |
| 第 3 组 `reply_to_forms` | `json_null 24 / real_message_id 0 / missing_key 0 / empty_string 0`；非空 `reply_to = 0/24` | 24 条**全部没有 reply_to** |
| 消息图 `msg_graph_degree` | `pub_in_degree_total = 0`、`pub_out_degree_reply_nonnull = 0`、`isolated_nodes = true`；旁证：DM 的 `reply_to` 非空 **125/125** 全部命中 DM `msg_uid`，命中 PUB `msg_uid` = **0** | 公开消息在消息图里**入度 0、出度 0，是孤立节点** |
| 第 4 组 `place_adjacency` | `UNVERIFIED`：`payload.place` 值为 null **24/24**，`nonnull_place_records = 0`，分母（相邻对数）**23** | 判据（脚本 `:45-51`，出数条件原文 = 「place 键在 100% 的 M实例 上存在且非 null」）未满足 ⇒ **不可判** |
| 线程隔离 `thread_isolation` | PUB 线程 24 个 / DM 线程 42 个 / 交集 **0** | 公开线程与私聊线程完全隔离 |
| 公开后紧邻 `pub_next_to_dm` | 下一条消息类型 `{MSG_DM: 23, MSG_PUBLIC: 1}`（分母 24）；`adjacent_next_msg_same_author = 0` | 公开发言之后出现的下一条消息绝大多数是**别人发起的私聊**，公开面自身没有延续 |

**A 基线一句话**：公开面是**纯广播**——有发言（24 条）、无接话（`reply_to` 0/24、图入度/出度 0）、无多人（`participants` 全为 1）、无场所（`place` 全 null）。

#### 3.2.1 发起侧内容质量抽查（人工阅读，不是脚本口径）

前 24 条公开消息全文见 `v2/evidence/r41_public_talk/pubtalk_r38on_MSG_PUBLIC_dump.txt`（7,932 B）。抽 4 条原文：

| seq | 作者 | 原文摘录 |
|---|---|---|
| 53 | P002 | 「（拿刨子推过木料，木花卷着落下来）慢点来，急不得。张家那扇窗，榫头得再收半厘。（眯眼比了比）手比尺准。」 |
| 167 | P013 | 「（把烧红的锄头往水桶里一浸，滋啦冒白烟）这锄头是东头老周家的，刃口卷了，我正给他回火。**你那边咋样？**先顾好自己。」 |
| 19467 | P010 | 「（把吉他盒往脚边一靠，手指还捻着刚断的第三根弦）这镇上最近还有谁家办席要人唱两段的吗？我这一天就啃了半块饼，肚子都开始打拍子了——**你这边最近手头有活儿没？**」 |
| 21968 | P012 | 「（把晒了一半的萝卜干往竹匾中间拢了拢）我这几天光顾着翻萝卜干，手都酸了，**你家那口子前阵子说腰疼，好些了吧。**」 |

判读（**分层，不合并成一句**）：
- **发起侧内容是像人的**：有具体生活细节（回火、萝卜干、断弦、榫头半厘）、有自我暴露（饿、手酸）、有对熟人的关切、有真问句（「你那边咋样？」「手头有活儿没？」）。
- **结构上仍是「对着空气说话」**：24 条各占独立线程、`turn_index` 全 0、`reply_to` 全 null、`participants` 仅作者自己；问句没有一个人接。
- ⇒ **缺口在接话侧，不在发起侧**。这构成本轮只做「接话」而不做「多发公开话」的依据。

第二数据点（d12d 批，用于确认不是单批偶然）：

```bash
python3 tools/public_talk/public_talk_metrics.py \
  --log v2/evidence/run_d12d_on_n16r60_seed42/run.jsonl \
  --meta v2/evidence/run_d12d_on_n16r60_seed42/meta.json
# 报告侧复算落盘：…/r41/baseline_d12d.json  sha256 9ba2aa67b79cec0160190c676027ecfbf9e0ca37a8a3148f6ae953b5e13e5076
```

| 项 | r38 on | d12d on |
|---|---|---|
| `MSG_PUBLIC` | 24 | 55 |
| `reply_to` 非空 | 0/24 | 0/55 |
| `participants` 长度 >1 | 0/24 | 0/55 |
| `pub_in/out_degree` | 0 / 0 | 0 / 0 |
| `place` 非 null | 0/24 | 0/55 |
| 代码身份 `code_sha` | `afde63c` | `5ca515d` |
| 规模 | n16 / r24 / seed42 | n16 / r60 / seed42（`meta.json` 中 `agents_n/model/provider` 缺失，脚本标 `UNKNOWN`，`complete=false`） |

> ⚠️ d12d 批的 `meta.json` 缺 `agents_n/model/provider` 三字段，脚本如实标 `UNKNOWN`；该批**只作第二数据点的方向性旁证**，不参与任何比率或判据。

### 3.3 C 本轮读数：**本节无数据（显式声明，不是漏写）**

**本轮无「后」臂读数。** 原因：OFF/ON 双臂验证批**未执行**（第三方 d9t 批在 25 分钟内三次重起并占用同一 LLM 端点，我方门禁通过后 7 秒被插入，按并发纪律立即中止，详见 §4.2）。

具体缺什么、为什么缺：

| 缺的东西 | 为什么没有 |
|---|---|
| 新批 `msg_public_total` / `participants_length_dist` / `reply_to_forms` / `msg_graph_degree` 读数 | 验证批未执行，本轮没有新的 `run.jsonl` 可测 |
| `place_adjacency` 的**新批**可判性验证 | 同上。历史批 `payload.place` 值恒 null（24/24），脚本改不了历史数据；只能等带 place 的新批产生 |
| OFF/ON 两臂对比（含「公开消息是否出现 `reply_to` 非空」） | 同上 |
| 「后」臂图表 | 同上 |

### 3.4 LLM 成本与真跑验真：**本轮新增 LLM 成本 = 0**

**本轮项目侧零新批 LLM 调用**：验证批未起，故没有本轮 `llm_cost.json`、没有本轮 `LLM_CALL` 事件，也不存在需要 `verify_true_run.py` 判定的新批。

> **防混读（重要）**：§3.5 图 2 里的 `calls=2252 / tokens_total=318,122` 是 **前基线批 `r38_f3_batch/on`** 的成本，**不是本轮开销**。本轮新增成本为 **0**。

### 3.5 图表（真实文件、可复算、非本轮新批）

> `reports/figures/` 是**本轮新引入的目录**（此前 `reports/` 下只有 `.md`）；与 `v2/evidence/<batch>/shots_*`（运行截图）语义不同，本轮为**报告图表**故放此处。

**图 1 · 公开面「接话」现状诊断**

| 项 | 值 |
|---|---|
| 文件 | `reports/figures/r41-PRE-baseline-public-topic-diag.png`（387,565 B，2476×1609 RGBA） |
| sha256 | `c8e3d686b13b238dccf3901b08e83620fa46514a50e3630504c941e298b10adb` |
| 数据源 | `v2/evidence/r41_public_talk/pubtalk_r38on_METRICS_BASELINE.json`（sha256 `9b2d68cb…`） |
| **图上红框横幅（原文复述）** | **「数据源：r38_f3_batch/on（前基线批，非本轮新批）；本轮验证批未执行」** |
| 对应 sha | 数据侧 `code_sha=afde63c`（r38 on 批）；生成时仓库 HEAD `a6470a1` |
| 关键六格 | MSG_DM **167** / MSG_PUBLIC **24** / MSG_GROUP **0**；`pub_in_degree_total=0`、`pub_out_degree_reply_nonnull=0`；participants 长度直方图 **{1:24}**；`reply_to` 形态 `json_null=24`、`real_message_id=0`；`turn_index_histogram={0:24}`；`place_adjacency=UNVERIFIED`（非 null place 0/24） |

> **防混读声明（必须）**：两张诊断图内「尺子身份」格显示的 `code_sha = afde63c…`，是**前基线批 `r38_f3_batch/on` 的 `inputs.code_sha` 原值**（该批生成 `meta.json` 那一刻的 HEAD），**与本轮实现代码 `2af557f` 属不同批次，勿混读**。本轮代码 sha = `2af557f`。

**图 2 · llm-cost / token 分布（前基线批成本，非本轮开销）**

| 项 | 值 |
|---|---|
| 文件 | `reports/figures/r41-PRE-baseline-llm-cost.png`（279,700 B，2273×1515 RGBA） |
| sha256 | `d3f9fd169568e44d2cb8e8c7f7eba682dcaab970d5dddcd432a51caf1c1a9005` |
| 数据源 | `v2/evidence/r38_f3_batch/on/llm_cost.json` |
| **图上红框横幅（原文复述）** | **「数据源：r38_f3_batch/on（前基线批，非本轮新批）；本轮验证批未执行」** |
| 对应 sha | `code_sha=afde63c`（r38 on 批）；生成时仓库 HEAD `a6470a1` |
| 关键数字 | calls **2252**、tokens_in **164,970**、tokens_out **153,152**、tokens_total **318,122**、cached 1387、thinking 425、degraded **0**、`provider_guard.ok=true`、`by_provider` 仅 `openai_compat` |

> **措辞边界（必须）**：图 2 的 318,122 tokens 是 **r38 on 前基线批**的成本，**不是本轮开销**。**本轮新增 LLM 成本 = 0**（未跑新批）。

复算命令（两条图同一脚本；实测同命令两次输出字节一致）：

```bash
python3 tools/metrics/round_figures.py \
  --diag v2/evidence/r41_public_talk/pubtalk_r38on_METRICS_BASELINE.json \
  --cost-json v2/evidence/r38_f3_batch/on/llm_cost.json \
  --label r41-PRE-baseline --out-dir reports/figures \
  --source-note "数据源：r38_f3_batch/on（前基线批，非本轮新批）；本轮验证批未执行"
```

独立复算证据（图表数据源本身也经复核）：evidence-viz 从 `run.jsonl` 现场重跑 `cd code && python3 -m obs llm-cost --log ../v2/evidence/r38_f3_batch/on/run.jsonl --require-provider openai_compat`，其输出与仓库内 `llm_cost.json` **JSON 深度相等 = True**；报告侧另用 `sha256sum` + `PIL.Image.open` + 逐图目视核对过两张 PNG（sha 与横幅内容均一致）。

---

## ④ 未做 / 未验证 与环境事实

### 4.1 未做 / 未验证（三条「无数据 + 原因」为硬要求，逐条显式登记）

1. **无新批 `msg_public` / `participants` 读数** —— 原因：验证批未执行（见 §4.2）。
2. **无 `place_adjacency` 的新批可判性验证** —— 原因同上（历史数据 `place` 恒 null，新批未产生）。
3. **无「后」图（POST 组）** —— 原因同上。
4. **行为级验证未做** —— 只有代码层证据（单测/回归），无本轮的 `obs llm-cost`、无行为读数、无对话原文样本。
2. **`place_adjacency` 的统计限定**：该组分母 = 相邻对数 = 实例数 − 1（r38 on 为 **23**）；24 条量级下即使 place 齐全，也只能报**事件数 / probe**，**不得**写成「公开面已形成同地闲聊」。
3. **本报告未做任何跨批/跨臂的显著性检验**：单 seed、单批、无重复 ⇒ 不写「显著」「因果」。
4. **`participants` 语义限定**：它是**线程参与者集合**（同一 `thread_id` 内取值恒定），不是收件人、也不是可见性开关；`长度 > 1` 不代表多人群聊。
5. **无 `v2/refs/` 预登记判据件**：R41 本轮未建预登记口径卡（`grep -rln 'R41' v2/refs` 为空）⇒ 本轮**不主张任何判据级达标**；下一轮若要判效果，须先补预登记（含分母门限与判据编号），再跑批。

### 4.2 环境事实（不是本轮成果，只作登记）

| # | 事件 | 实测 |
|---|---|---|
| ① | 外部批 PID `2732286`（`.worktrees/d9t-openings-2`，15:47 启动，`timeout 1800`） | `run.jsonl` 自 16:04:56 后停止增长（末事件 `TURN_SEAL` round 9 / seq 9687，`wc -l` 9688），进程 STAT=`Sl`、%CPU=0.4、`wchan=poll_schedule_timeout`、`run_batch.log` 恒 0 字节 ⇒ 阻塞在网络/LLM 等待，**只跑到 9/24 回合**。该批**未产出可用批**，目录随后被清空；**本轮未使用该批任何数据** |
| ② | 外部批 PID `2798006`（`timeout 1500 bash /tmp/launch_d9t_on2.sh`，16:15:26 起）→ `2798007` → `2798012 python3 -m orchestration run` | 与 ① **同源（同 `.worktrees/d9t-openings-2`、同 16×24）的重跑**——**② 是 ① 作废后的重跑，不是与 ① 并行的两个批**。本团队因 ② 被 `preflight` 并发闸挡下（`rc=9`），按纪律**不并发、不 kill**，等待其收批（`timeout 1500` ⇒ 约 16:40 上限） |
| ③ | `preflight` 计数口径假阳性 | preflight 报 `orchestration_run=2 / run_batch=1`；逐进程核对后**实际只有 1 个 `orchestration run`（PID 2798012）**：多出的计数来自起跑者的 `/bin/sh -c` 包装 shell（命令行内联 heredoc 脚本全文，同时命中 `orchestration[[:space:]]+run` 与 `run_batch` 两个模式），`scan_pattern()` 只排除自身/祖先链/`preflight.sh`，排不掉这种包装 shell。旁证：`ps -eo pid,ppid,cmd \| grep "orchestration run" \| grep -v grep \| wc -l` → **1**。证据：`v2/evidence/preflight/preflight_20261031T081642Z_2af557f6_r41_verify.log`。同一假阳性在 16:41 再次出现（命中别人的 `sleep 200; … grep -E "python3 -m orchestration run"` 观测命令），日志 `v2/evidence/preflight/preflight_20261031T084119Z_825496a1_r41_clear.log`，当时真实 python 批进程数 = 0 |
| ④ | **第三方批第三次重起与我方臂中止（并发纪律执行留证）** | 第三方 d9t 批 25 分钟内三次重起：`2732286@15:47` → `2798012@16:15` → `2861039@16:42`。我方 OFF 臂 `2861258` 于 16:42:42 起跑（较第三方批晚约 2 秒），16:42:59 检测到并发，16:43:03 只 kill 自身（`2861258`）并中止，ON 臂未起。留证：`v2/evidence/r41_public_talk/concurrency_abort_1642.txt`（含 ps 原文时间线）。作废半批目录 `off_ABORTED_concurrent_1642/`（18 行零对话）**未入库** |

> 隐患线索（只登记、不展开成本轮结论）：①/② 提示 LLM 调用疑似缺少请求超时与重试上限，否则不会长期停在 `poll` 上；③ 的进程匹配未覆盖"命令行内联脚本文本"的包装 shell —— **该缺陷方向是「放大告警」而非「漏报」，因此并发闸的设计方向是对的**，只是日志可读性差、会误导读日志的人。
>
> **后续建议（本轮未修改，需另立任务）**：把 `tools/d5/preflight.sh::scan_pattern()` 的匹配改成 argv[0]/argv[1] 级，或显式排除 `sh -c` 包装 shell，避免一个批被报成两个。本轮**未动**该脚本（`git status --short tools/d5/` 为空），此处仅登记。

---

## ⑤ 提交、推送与结论绑定

### 5.1 结论绑定 sha（完整链，不简化成单个 sha）

```
a6470a1  ← 本轮起点（CYCLE-40 末提交）
2af557f  ← 本轮代码（4 files / +411 / −10）        = 代码身份
0599090  ← 另一团队提交 CYCLE-41 报告（非本团队；其 sha 后经该团队 amend，见 §5.2）
425b0af  ← 本轮证据（6 files / +523）
<报告 commit> ← 本文件所在提交（= 报告身份）
```

> `425b0af` 的 parent 是另一团队的 CYCLE-41 报告提交——这是客观事实（life-engineer 提交时 HEAD 已含该提交），照实登记，不做"清洗"。

| 结论 | 绑定 |
|---|---|
| 代码状态 | **`2af557f`**（本轮无跑批在其上执行；验证批未起） |
| 本轮证据 | **`425b0af`** |
| 报告身份 | **本文件所在提交**，取法：`git log -1 --format=%H -- reports/R41-public-talk.md`（**不写死，避免自指**） |
| 图表数据源 | 前基线批 `r38_f3_batch/on`（`code_sha=afde63c`）与 `run_d12d_on_n16r60_seed42`（`code_sha=5ca515d`）；均**非本轮** |

### 5.2 提交

`git add` **显式路径**（不用 `-A`/`.`），清单：

- `reports/R41-public-talk.md`（本文件）
- `reports/README.md`（登记行）
- `reports/figures/r41-PRE-baseline-public-topic-diag.png`
- `reports/figures/r41-PRE-baseline-llm-cost.png`
- `tools/metrics/round_figures.py`

**不 add**：`run.jsonl`（`.gitignore:8 **/*.jsonl` 命中）、`*.log`、`v2/evidence/r41_public_talk/off_ABORTED_concurrent_1642/`（作废半批）、以及工作区中 200+ 条他人未提交项与 `M v2/refs/D9t-launch-checklist.md`（非本轮）。

`git show --stat a950153` 实测输出见 §5.4。

> **分支含他团队提交**：`feat/life-public-talk-r41` 上另有另一团队的 CYCLE-41 报告提交（其 sha 经该团队多次 amend 变化，提交时 HEAD 为 `330778d` 系列）。本团队**仅追加自身提交**，不 rebase、不 reset、不 force。

### 5.3 推送

```bash
git push origin feat/life-public-talk-r41 > /tmp/r41_push.txt 2>&1; echo "push rc=$?"
timeout 25 git ls-remote --heads origin 'refs/heads/feat/life-public-talk-r41' > /tmp/r41_lsremote.txt 2>&1; echo "ls-remote rc=$?"
```

实测结果见 §5.4 回填（**不宣称已推送，除非 ls-remote 返回 `rc=0` 且 1 行真实 ref**）。

> **未推 master，如实说明**：`git push --dry-run origin HEAD:refs/heads/master` → `push_rc=1`、`! [rejected] HEAD -> master (non-fast-forward)`；`git rev-list --left-right --count origin/master...HEAD` → `23 15`（master 领先 23 条、本分支领先 15 条）。按仓库近例（CYCLE-38/39/40）推特性分支，不 rebase、不 force、不生成 merge 提交。
> **`ls-remote` 的「空输出 + rc=0」= 未验证**，不得读成「远端已更新」；只有 `rc=0` 且输出 1 行真实 ref 才算推送成功。

### 5.4 回填：提交与推送实测（成稿后补，只补状态不动读数）

| 项 | 实测值 | 取证 |
|---|---|---|
| 报告 commit | `a950153`（`git log -1 --format=%H -- reports/R41-public-talk.md` → `a9501532a16ec056af0c6ddcfd26edf487df9b26`） | 本机实测 |
| `git show --stat a950153` | `reports/R41-public-talk.md 377+`、`reports/README.md 1+`、2 张 PNG（279,700 B / 387,565 B）、`tools/metrics/round_figures.py 835+`；**5 files changed, 1213 insertions(+)** | 实测 |
| push rc | **`0`**，原始输出：`[pre-push] OK：无祖先错位 / 无文件删除 / 无大块删除` + `596eee0..a950153  feat/life-public-talk-r41 -> feat/life-public-talk-r41` | `/tmp/r41_push.txt` |
| push 后 `ls-remote` | **`rc=0`、1 行真实 ref**：`a9501532a16ec056af0c6ddcfd26edf487df9b26  refs/heads/feat/life-public-talk-r41` ⇒ **远端 = 本地 HEAD = `a950153`** | `/tmp/r41_lsremote.txt` |
| scope-guard | 首次提交被拦（3 个离群旧路径：2 张 PNG + 脚本，16:19 由 evidence-viz 产出、比 README 编辑老 >1800s）；经 `COMMIT_SCOPE_ACK` 显式确认后放行，提交说明内已注明理由 | 提交输出原文 |
| 未推 master | **未推**。`git push --dry-run origin HEAD:refs/heads/master` → `push_rc=1`、`! [rejected] HEAD -> master (non-fast-forward)`；`git rev-list --left-right --count origin/master...HEAD` → `23 15`（master 领先 23 条、本分支领先 15 条）⇒ 按仓库近例推特性分支 | 实测 |
| 分支含他团队提交 | `feat/life-public-talk-r41` 上除本团队 `2af557f`/`425b0af`/`a950153` 外，另有另一团队的 CYCLE-41 报告提交（`825496a`→…→`596eee0` 系列，其间多次 amend）。本次 push 一并推送，**未 rebase / 未 reset / 未 force** | `git log --oneline` |

### 5.5 preflight 复核（报告侧独立执行，重定向取 rc，不串管道）

```bash
bash tools/d5/preflight.sh --tag r41_verify > /tmp/pf2.txt 2>&1; echo "rc=$?"
# rc=9
# [preflight] FAIL exit=9 reasons=concurrency:orchestration_run=2 concurrency:run_batch=1
```

> 注意：`preflight.sh | tail` 会拿到 `tail` 的 rc（显示 0），**必须**用重定向再取 `rc=$?`。`dirty_frozen_tree` 在 commit A 后已消失，当前 FAIL 纯为并发闸（且计数为口径假阳性，见 §4.2③）。日志路径：`v2/evidence/preflight/preflight_20261031T081642Z_2af557f6_r41_verify.log`。

**门禁判据（双重，缺一不可）**：

```bash
# 判据 1：preflight 自身退出码（重定向取 rc，不串管道）
bash tools/d5/preflight.sh --tag <tag> > /tmp/pf.txt 2>&1; echo "rc=$?"
# 判据 2：真实 python 跑批进程数必须为 0（绕开 preflight 的计数假阳性）
ps -eo pid,args | grep "python3 -m orchestration run" | grep -v grep | wc -l
```

> 两条件同时成立才可起批。**若判据 1 为 `rc=9` 而判据 2 的进程数 = 0，属计数假阳性，需人工裁定**（§4.2③ 已给复现方法）；反之若判据 2 > 0 则真并发，禁止起批。
