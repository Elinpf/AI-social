# R43 · 公共场所说话配额（R41V-C4）**缺陷修复**：机制级成立 + 单测证据（判据修订待新卡冻结）

> 撰写：`report-writer`｜实现：`life-impl`（fix-1）｜独立审计：`evidence-auditor`（audit-1）｜撰写时刻：`2026-11-01T04:36+08:00`
>
> **与既有报告的关系（先看这条，避免混用）**
> - `reports/R41-public-talk.md` = 该维度的**设计 / 结构分析**（含 OFF 等价性的静态论证）。
> - `reports/R41b-public-talk-verify.md` = 同一维度的**首次验证批实测**（两臂真跑），它同时**登记了本报告要修的那个缺陷**（判据 `R41V-C4` 判「不成立」）与一条工具侧缺口（`emit_run_meta.py` 未登记 `HITT_DIALOGUE_PUBLIC_REPLY`）。
> - **本报告 = 该缺陷的「修复」证据链**：单测级 + 对照组级 + 离线复算级。**本轮零新跑批、零新 LLM 调用**，因此**没有任何效果级读数**，也不冒用 R41b 的批级读数。
> - `reports/R42-weather-sense.md`（天气语言化）与 `reports/CYCLE-4x-*`（周期报告）与本轮改动**不同维度**，本报告不引用其数字。
>
> **编号说明**：`reports/` 已占用 `R41` / `R41b` / `R42`，**`R43` 未被占用**。查法（可直接跑）：
> ```bash
> git ls-files reports/ | grep -Ei 'reports/R4[0-9]'     # → 仅 R41 / R41b / R42 三份，无 R43
> ```
> 故本报告编号 `R43`，**不占用、不改动任何既有编号**。
>
> **本文不内嵌自身哈希**（自指会立刻失效）。核验请以 `sha256sum reports/R43-place-talk-quota-fix.md` 的实测值为基准，并与提交记录比对。
>
> **证据总表**：`team-workspace/fix/place-talk-quota-fix.md`（实现方交付）与 `team-workspace/audit/place-talk-quota-audit.md`（审计方复核）。本报告所有数字均可在这两份或仓库原件中复算，逐条出路见 §2 表内「出处」列与附录 B。

---

## 一句话结论

**机制级：成立（可宣称，须带层级限定）**——场所配额从「接话路径里一处对着决策时点可见集的判定」收敛成 **唯一判定函数 `life.public_talk.place_quota_gate`（键 = `place + day + slot`）+ 唯一强制点 `orchestration.integration._do_social()` 写入口**；首发与接话两条路径都汇入同一道闸，`state.event_index` 含本回合 arbiter 缓冲已**实测确认**。单测 `11/11` 通过，并经**三条探针闭环**：阈值变色（a）、语义回滚变红（b，`R43_ROLLBACK=1` ⇒ `1 failed`）、基线树断言级红（c，`9 failed / 2 passed`）。
**⚠ 这句「机制级成立」不等于 `R41V-C4` 判据达成**——见下一段的判据层结论，请勿单独截取本句引用。
**判据层：`R41V-C4`（**冻结版预登记**）在修后静态回放**仍判「不成立」**——冻结卡（`v2/refs/prereg-r41v-public-talk-verify.md:67`，commit `f365255`）原文是「逐 **place×slot** 统计 … ≤ 2」（**无 day 维度**），而 R43 实现的键是 `day + slot + place`；按冻结口径回放，`place×slot` 仍为 **4 > 2**。**因此本轮不得出现「C4 达成 / C4 已修复」字样**；只能说「按**修订后**的 `day×slot×place` 口径，在**单测级 / 静态回放级**成立（2 ≤ 2），而该修订必须由**新预登记卡**重新定义判据」。
**效果级：未验证（不可宣称）**——本轮零新批，**没有任何修后读数**。
**`R41V-C1` 不可判，两条并列原因**：① 分母不足（M 实例 `n_off=24 / n_on=30`，未同时 ≥30）；② **尺子缺陷**（`public_talk_metrics.py:180-192` 用 `msg_id` 集合匹配 `reply_to`，而 `reply_to` 装的是 `msg_uid` ⇒ `real_message_id` **恒 0**；实测命中 `msg_id`=0 / 命中 `msg_uid`=7）。**`k_ON=0` 不是「公开面没有接话」的行为结论**，「扩样本可达 C1 可判」亦不成立。

---

## ① 本周期做了什么

### 1.1 一句话

单维度、单 commit：修 `R41V-C4` 登记的「场所说话配额在结果侧被突破」，把配额判定收敛到唯一函数 + 唯一强制点（写入口），并补齐能捕获该缺陷的单测与离线复算脚本。**本轮未起任何 orchestration 批**（全程只做单测与离线复算）。

### 1.2 分支 / 基线 / commit（一律取法，不写死）

| 项 | 取法命令 | 实测值（撰写时刻） |
|---|---|---|
| 分支 | `git branch --show-current` | `fix/place-talk-quota-r43` |
| 基线（base） | `git rev-parse ad3538f` | `ad3538fd2a3e0633091b0064e32c4f5fcaa6f838`（= R41b 所在 HEAD） |
| 唯一 fix commit | `git log --oneline ad3538f..HEAD` | `cd09bfb fix(life/public_talk): 场所说话配额收敛到唯一一道闸（R43，R41V-C4）` |
| 该 commit 全 sha | `git rev-parse HEAD` | `cd09bfbd125d3a03b9e62d8f2fd6c286f25ab7dc` |
| 提交条数（**自排除本报告**） | `git rev-list --count ad3538f..HEAD -- . ':!reports/R43-place-talk-quota-fix.md'` | 撰写时刻为 1；本报告即使被提交，该取法也自动排除自身，不随回填而变 |

> ⚠ 上述 sha 是**撰写时刻快照**：若 audit-1 要求返工，实现方会重提、sha 会变。**以命令输出为准，不要抄本表。**

### 1.3 改动清单（取法）

```bash
git show --stat --oneline HEAD        # 或 git diff --name-only ad3538f..HEAD
```

| 文件 | 改动性质 | 为什么必须动它 |
|---|---|---|
| `code/life/public_talk.py` | 新增 `GATE_VERSION="r43/1"`（`:107`）、`place_slot_count()`（`:125`）、`place_quota_gate()`（`:158`，**唯一判定函数**）；`public_count_at()`（`:164`）与 `place_quota_ok()`（`:173`）退化为兼容包装 | 把「键」与「判据」统一为 `place + day + slot`，`round` **不入键**（同 `day×slot` 跨 round 必须合并计数） |
| `code/orchestration/integration.py` | 新增 `_r43_place_gate()`（`:191`）/ `_r43_gate_version()`（`:214`）；`_do_social()` 在 `:907` **组装 payload 之前**过闸，超限发 `DROPPED{reason:"quota_place"}` 并 `IntentResult(ok=False, reason="quota_place")`（`:914`） | **唯一强制点**。`state.event_index` 同时含已提交记录与本回合 arbiter 缓冲 ⇒ 本回合已放行的公开消息立刻可见；intent 逐条同步应用 ⇒ 计数天然串行 |
| `code/life/agent.py` | `_pick_reply_target()` 的场所判定**降级为预过滤**（补 `day=wv.time.day`），并注释写明「裁决点在写入口」 | 保留「省一次 LLM 调用」的作用，但不承担裁决（它只有决策时点可见集） |
| `code/life/tests/test_r43_place_talk_quota.py` | 新增 11 条单测 | 覆盖既有测试的盲点（同轮不可见 / 首发不过闸） |
| `tools/public_talk/recount_place_quota_r43.py` | 新增离线复算脚本（四粒度 + 静态反事实） | 让 §2.2 的复算可一键重跑 |

**撰写者独立复核（非照抄）**：`public_talk.py:107/125/158/164/173`、`integration.py:191/214/907-914`、`agent.py:1156-1160` 的符号与行号**逐条 grep 实测一致**（附录 B·B1）。

### 1.4 根因（两条独立缺口叠加，不是「计数键粒度错」单点）

| 缺口 | 内容 | 现场证据 |
|---|---|---|
| **A：首发公开消息根本不经过场所闸** | 基线 `_do_social()` 的 `scope=="global"` 分支只有 `public_per_agent_per_round`（默认 2）与 `public_global_per_round`（默认 20）两档全局配额，**没有 place 维度**；场所配额当时只存在于接话路径 `agent.py:1152` | `round3/day0/afternoon/bank` 那组 3 条全是 `turn_index=0`、`reply_to=null`、thread 各不同（seq 2225 / 2250 / 2339） |
| **B：接话路径的闸对着「决策时点可见集」判** | 闸扫的是 `wv.visible_events`；本回合新消息只进 arbiter 缓冲，P6 才 commit ⇒ 同轮后决策者看不到先决策者刚落的消息 ⇒ 每个接话者都算到「已有 1 条 < 2」而放行 | `round1/day0/morning/farm` 的 seq **487**（P001）与 **613**（P003）**同为** `turn_index=1`、**同** `reply_to="42:189"`、**同** `thread_id=TH-P015-PUB-0-0` |

即 R41b 那句「**决策时点合规、聚合结果越界**」。

**关于「键粒度」与判据（必须与 §0 / §③ P-0 一致读）**：
- **判据是那张跑前冻结的卡，不是代码里的键。** 预登记冻结口径 = 逐 **`place×slot`** 统计 `MSG_PUBLIC` 最大计数 ≤ 2（`v2/refs/prereg-r41v-public-talk-verify.md:67`，commit `f365255`，**无 day**）。
- R43 把 `day` 入键，**属对判据的修订**，不是「让键去对齐判据」；**按冻结口径做修后静态回放仍 `place×slot = 4 > 2` ⇒ `R41V-C4` 判不成立**；按**修订口径** `day×slot×place` 在**单测级 / 静态回放级**成立（2 ≤ 2）。修订必须由**新预登记卡在跑批前冻结**。
- 就**主因排序**说：本轮越界的主因是缺口 A、B（首发不过闸 / 闸对着决策时点可见集判），键粒度不是主因——但**「不是主因」不等于「口径合法性可以事后改」**，后者只能走预登记修订。真正破配额的最小粒度实测为 `round×day×slot×place = 3`。

**四粒度不是四个 bug**：它们是**同一批事件在四种分组下的最大计数**。引用时必须并列两套口径：冻结口径 `place×slot`（R41b 实测 **9**，最坏 `bank/afternoon`）与修订口径 `day×slot×place`（R41b 实测 **5**，最坏 `day0/afternoon/bank`）。**不得只写后者。**

### 1.5 修复结构与 OFF 等价性

- **单函数**：`place_quota_gate(records, place, day, slot) -> (放行?, 已占条数)`；入参语义 = **已存在**条数，上限 2 ⇒ 第 3 条被拒。缺 `day`/`slot` 键时该维度按通配（向后兼容旧日志）；现存 `integration` 恒写 `day`/`slot` ⇒ 生产上是精确比对。
- **单强制点**：`integration._do_social()`；全仓 `MSG_PUBLIC` 只有这一处 `_emit_assembled`，不存在绕过写入口的旁路。
- **OFF 等价性**：`HITT_DIALOGUE_PUBLIC_REPLY` 未设 ⇒ `_r43_place_gate` 恒 `(True, -1)`：不计数、不 emit `DROPPED`、payload 取值不变 ⇒ 事件流与接入前一致。由 `test_do_social_off_arm_never_blocks` + 既有 `test_r41_public_talk.py`（29 条，含 OFF 白名单/等价性）共同守住。

### 1.6 纪律与边界（如实记录）

| 项 | 实测 |
|---|---|
| 是否跑批 | **零新批**：本轮未起 any orchestration；撰写时 `ps -eo pid,etime,cmd \| grep -F "orchestration run" \| grep -v grep \| wc -l` ⇒ **0**（先前他人起的 `calib_3points.sh` C 臂已在 04:11 前后收批，`/tmp/d9x_calib_031333/` 下三点俱在） |
| 禁改区 | 命中**一处需登记的程序性偏离**：`git diff --name-only ad3538f cd09bfb` ⇒ `code/orchestration/integration.py`。`code/engine`、`code/config` **零改动**。定性与追认见 §③ **P-1**：**已获 Leader 书面追认，责任归 Leader**（其授权范围窄于设计要求），**非实现方越权**。发生窗口内**无新批** |
| 工作树 | 只 `git add` 上述 5 个具体路径；主工作树原有的 5 个已跟踪改动 + 267 个未跟踪文件**未动** |
| 未 push | 等 Leader 授权，见附录 A |
| 本报告与截图 | **未 commit**（按 Leader 要求留在工作树，由 Leader 统一提交） |

---

## ② 有哪些提升（数字 + 分母 + 判据编号）

> **层级声明（本节最重要的一句）**：**机制级 ≠ 效果级**。本节判据全部是「单测级 / 代码结构级 / 对照组级 / 离线复算级」证据，能证明的是「**旧路径会越界、新路径在受控构造下会截断**」，**不能**证明「真实跑批里不再越界」，更不能证明「生活气息提升」。**凡「已修复」只能写「机制级 + 单测级」。**
> **读法**：`判定` ∈ {成立 / 不成立 / 不可判 / 无数据}；**`不可判` ≠ `无效` ≠ `有效`**。分母 < 30 一律只报 `k/n` 计数，**不报比率、不报区间**。
> **口径并列纪律（`R41V-C4` 必须同时给两套）**：**冻结原文**「逐 `place×slot` 统计 `MSG_PUBLIC` 条数最大值 ≤ 2」（`v2/refs/prereg-r41v-public-talk-verify.md:67`，commit `f365255`，**无 day 维度**）↔ **修订口径**「`day×slot×place ≤ 2`」（R43 实现键）。**只给后者即为 goalpost**，本节不这么写。
> **`17/13` 与「ON 臂 ≈17 < 30」不进本节**：它们是上界估计，只出现在 §③ 与附录。

### 2.1 机制级判据表（R43-M1 ~ R43-M6）

| 判据 | 定义（可复算口径） | 读数（`k/n`） | 判定 | 出处 |
|---|---|---|---|---|
| **R43-M1** 唯一判定函数存在且键正确 | `life.public_talk.place_quota_gate` 存在；键 = `place+day+slot`，`round` 不入键 | `:125-155` 键构造可比对 ⇒ 命中 | **成立**（代码级） | `code/life/public_talk.py:107/125/158`；附录 B·B1 |
| **R43-M2** 写入口强制（行为级） | 同 `day×slot×place` 第 3 条经 `_do_social()` 必须被拒：`IntentResult.ok=False` 且 `reason=="quota_place"` | 新代码树 **11/11 passed**（含该断言）；基线树同断言 **failed（AssertionError）** | **成立**（单测级） | `code/life/tests/test_r43_place_talk_quota.py`；附录 B·B2/B5 |
| **R43-M3** 断言有牙（阈值探针） | ① `MAX_PER_PLACE_PER_SLOT` 改 3 ⇒ 同一输入 `gate(2条)` 由 `False` 变 `True`；② 上限改 1 ⇒ 写入口第 2 条即 `quota_place` | 函数级 + 行为级各 1 条用例，均通过 | **成立**（单测级） | `test_threshold_probe_moves_with_constant` / `test_do_social_threshold_moves_with_constant` |
| **R43-M4** 语义回滚探针 | 把生产闸 monkeypatch 回旧语义（决策时点可见集 + 不区分 day）⇒ 同一断言必须变红 | **撰写者独立复跑**（命令与原文见下）⇒ `1 failed, 10 deselected` | **成立**（单测级，证明非自证循环） | 附录 B·B4 |
| **R43-M5** 基线摘除对照 | 只把**新测试**投到基线代码树（`git archive ad3538f code`），承重点须以 `AssertionError`（failed，非 error）失败 | 基线树 **`9 failed, 2 passed`**；承重点 `test_do_social_caps_third_public_message_at_same_place` = `AssertionError`（第 123 行），另 2 条断言级红（第 141/152 行），余 6 条为 `AttributeError`（新符号缺失，只承担细粒度） | **成立**（对照组级） | 附录 B·B5（撰写者独立复跑） |
| **R43-M6** 回归不破坏 | 既有相关测试 + 跨层测试仍绿 | `test_r41_public_talk.py` **29/29**；两文件合并 **40/40**；跨层 `test_e2e_integration.py` 6/6、`test_conservation.py` 4/4、`test_dialogue_repair.py` 21/21（**跨层三件为转述实现方结果，撰写者未独立复跑**）；**全量 `life/tests` 在 300s 门下未跑完 ⇒ 标「未完成」，不写「全绿」** | **成立（相关子集）/ 未完成（全量）** | 附录 B·B2/B6 |

**M4 的两条命令必须并列贴（只贴 `11 passed` 不足以证明该探针——常规 `11 passed` 只说明「恒绿面」，不证明「回滚会红」；该探针在常规 pytest 下恒绿，只有 `R43_ROLLBACK=1` 才变红）**：

```bash
# ① 常规面（不含回滚语义）：只说明其余 10 条恒绿 + 该条默认也绿
cd code && python3 -m pytest life/tests/test_r43_place_talk_quota.py -q          # 11 passed

# ② 回滚探针（必须变红）：R43_ROLLBACK=1 把生产闸 monkeypatch 回旧语义
cd code && R43_ROLLBACK=1 python3 -m pytest \
  life/tests/test_r43_place_talk_quota.py::test_rollback_probe_blocks_third_even_when_others_invisible -q
```

```
        st = _st([_rec(487, "P001"), _rec(613, "P003")], rnd=1)   # 2 条都在本 round
        ok, n = IG._r43_place_gate(st, "farm", 0, "morning")
>       assert ok is False, f"同 day×slot×place 第 3 条必须被拒（ok={ok}, n={n}）"
E       AssertionError: 同 day×slot×place 第 3 条必须被拒（ok=True, n=0）
E       assert True is False
life/tests/test_r43_place_talk_quota.py:272: AssertionError
=========================== short test summary info ============================
FAILED life/tests/test_r43_place_talk_quota.py::test_rollback_probe_blocks_third_even_when_others_invisible
1 failed, 10 deselected in 0.07s
```

**`n` 都很小（11 条用例、29 条既有用例），所以本节不给任何率与区间，只给 `k/n`。** 这些是「构造用例的通过数」，不是「样本的统计量」。

### 2.2 离线复算：与 R41b 四方对账（**旧日志 + 新函数静态重放**）

```bash
python3 tools/public_talk/recount_place_quota_r43.py v2/evidence/r41v_public_talk_n16r24_s42/on/run.jsonl
```

| 粒度 | R41b 登记 | 本次独立复算 | 对账 |
|---|---|---|---|
| `round × day × slot × place` | 3 | **3** | 一致 |
| `day × slot × place` | 5 | **5**（最坏 `day0/afternoon/bank`） | 一致 |
| `place × slot`（忽略 day，跨天累计） | 9 | **9**（`bank/afternoon`） | 一致 |
| `place × slot`（只数接话） | 4 | **4**（`school/morning`） | 一致 |
| `author × slot`（接话） | 1（未越） | **1** | 一致 |
| `MSG_PUBLIC` 条数 | 30 | **30** | 一致 |

**这一栏的判定是「对账成立」，不是「修复有效」**：输入是**旧代码**产出的日志（ON 臂 `run.jsonl` sha256 `c8a7f546…`），只证明「两把尺子对同一批事件的计数一致」以及「新函数在旧事件序列上会截断」。

**静态反事实（⚠ 上界估计，非读数；不进本节判据表）**——把 ON 臂 30 条按 `seq` 逐条喂新闸，再在**两套口径**下各算一次：

| 口径 | 修前（R41b 实测） | 修后静态回放（**上界估计**） | 是否满足该口径的 `≤2` |
|---|---|---|---|
| **冻结原文口径** `place × slot`（**无 day**） | **9**（`bank/afternoon`） | **4**（`school/morning`、`bank/afternoon`） | **否（4 > 2）⇒ `R41V-C4` 冻结版仍判不成立** |
| **修订口径** `day × slot × place` | **5**（`day0/afternoon/bank`） | **2** | 是（2 ≤ 2，**仅在单测级 / 静态回放级**） |
| `round × day × slot × place` | 3 | 2 | — |

`accept = 17 / would_drop = 13`（落盘条数由 30 降为 17）。**这三行都是上界估计**：真实跑批里被丢的消息会改变后续接话对象与在场者判断，`MSG_PUBLIC` 总数与 `reply_to` 分布都会变。它只支撑「口径冲突」这个结论，**不支撑任何效果级宣称**。

### 2.3 明确不宣称（逐条给理由）

| 不宣称 | 理由 |
|---|---|
| **「`R41V-C4` 达成 / C4 已修复 / 配额已不越界」** | **冻结判据（`place×slot ≤2`，无 day）在修后静态回放仍 4 > 2** ⇒ 按本轮冻结口径判「不成立」。只能说「按**修订后**的 `day×slot×place` 口径，在单测级 / 静态回放级成立」。**这是本轮第一条红线。** |
| 「配额已生效（批级）」 | 无新批；`DROPPED{quota_place}` 在真实运行中是否触发、触发多少，**零读数** |
| 「结果侧越界归零（端到端）」 | 越界结论本身是从 `c8a7f546` 这份**旧代码**日志读出来的；旧日志无法证明新代码行为 |
| 「`17/30` 是修复后读数」 | 静态反事实上界，见 §③ P-4 |
| 「对话更自然 / 生活气息提升」 | 无该判据；本轮无人工盲判、无 LLM judge（`W-1-e` 系列为明令不做项） |
| 「C5 非塌陷仍成立（新代码）」 | 见 §⑤ P2 的算术：同规模重跑反而**可能**让 C5 判不成立；无实测 |
| 「`test_old_architecture_reproduces_the_violation` 复现了越界」 | 该用例用的是 `gate([], …)`（空集恒放行）⇒ **同义反复**，不构成旧架构行为证据。真证据是 seq 189 / 487 / 613 那一组（同一目标被两人接住）+ 基线树反向对照（`git archive ad3538f`）。 |

**本节措辞已逐条对齐 `audit-1` §8 的「可宣称 / 不可宣称」清单与三条措辞红线**（层级限定 / 口径并列 / `17/13` 标上界），未超出其范围。

---

## ③ 仍有问题（含失败 / 不可判项）

> **`不可判 ≠ 无效`**：下列「不可判」项是「本轮没有能力判定」，不是「已证明没问题」。

| # | 问题 | 证据 / 说明 | 判定 |
|---|---|---|---|
| **P-0** | **判据口径冲突（最高优先，决定能不能宣称）**：冻结预登记 `v2/refs/prereg-r41v-public-talk-verify.md:67` 写的是「逐 **place×slot** 统计 `MSG_PUBLIC` 条数最大值 ≤ 2」（`§4` 命令按 `place`/`slot`/`author` 分组，**无 day**）；R43 实现的键是 `day + slot + place`。**按冻结口径做修后静态回放：`place×slot` 仍 4 > 2 ⇒ `R41V-C4` 冻结版判「不成立」** | 双口径对照见 §2.2 表；`git show f365255:v2/refs/prereg-r41v-public-talk-verify.md \| sed -n '67p'` 可复算。处置：**`day` 入键必须由修订版预登记卡重新定义判据、跑批前冻结**；修订卡落定前**不得**出现「C4 达成」 | **不成立（按冻结判据）/ 成立（按修订口径，仅单测级+静态回放级）** |
| **P-1** | **禁改区程序性偏离（已获 Leader 书面追认）**：`git diff --name-only ad3538f cd09bfb` 命中 `code/orchestration/integration.py` | 事实：Leader 04:04 授权只写「允许在 fix-1 分支改 `code/life`」，但同一指令的设计要求是「配额必须收敛到全局已决定开口集合的单一判定」，**架构上必然落到写入口 `_do_social()`**（`MSG_PUBLIC` 全仓唯一 emit 点；闸不在写入口就必然留旁路）⇒ **授权范围窄于设计要求**。Leader 书面追认，**由 Leader 认账，非实现方擅自越界**。后续约束：prereg §5 写死「`code/{life,orchestration,config,engine}` 有 modified/staged/untracked ⇒ 本轮失败」⇒ **跑批前该 commit 须先合入且该目录干净**（`check_clean_tree.py` 会卡） | **成立（偏离存在）**；定性为**程序性**，非技术性错误 |
| **P-1b** | **基线与上游脱节（未验证；合并 / 起批前必须先评估）** | 实测（撰写时）：`git rev-parse master` ⇒ `94e272a`；`git ls-remote origin refs/heads/master` ⇒ `0345742`（后者是前者的后代）；`git rev-list --left-right --count origin/master...HEAD` ⇒ **`72 / 45`**。结论：**R43 基于本地 `ad3538f` 血统；该血统落后远端 `master` 72 个提交。** 上游这 72 个提交是否触及 `code/life/public_talk.py`、`code/orchestration/integration.py` 或场所/接话相关逻辑，**本轮未评估（未验证）**。若上游已改动同类逻辑，本修复存在**语义冲突或重复实现**风险。**合并或据本修复起批前，必须先完成该差异评估。** | **未验证**（不影响本轮机制级结论，但阻断「合并 / 起批」） |
| **P-2** | **`R41V-C1` 不可判，两条并列原因** | ① **分母不足**：M 实例 `n_off=24 / n_on=30` 未同时 ≥30（本批 ON 接话 7）；② **尺子缺陷（P0 级）**：`public_talk_metrics.py:180-192` 的 `reply_to_form()` 用 `msg_id` 集合匹配，而 `reply_to` 装 `msg_uid`（`integration.py:950-954`）⇒ `real_message_id` **恒 0**；`F` 段复算：**命中 `msg_id` = 0 / 命中 `msg_uid` = 7**（`42:189`×2、`42:167`×2、`42:19241`×2、`42:19807`×1）。佐证：同文件 `msg_graph_degree`（`:688-689`）用的是 `msg_uid` ⇒ **文件内口径不一致**。⇒ **`k_ON=0` 不得当作「公开面没有接话」的行为结论**；**「扩样本可达 C1 可判」不成立**（分子恒 0） | **不可判**（≠ 无效）；**尺子缺陷：成立** |
| **P-3** | **效果层未验证，阻断于新批** | 本轮零新批。转「可判」需：两臂新批（开关 `HITT_DIALOGUE_PUBLIC_REPLY`）+ 新 `run.jsonl` sha256 + `obs llm-cost` `rc=0` + 结构判据 S1/S2/S3（见 §⑤ P2）。**且必须先修 P-0 口径与 P-2 尺子**，否则跑完也不可判 | **不可判（阻断于新批）** |
| **P-4** | 静态反事实被误当读数的风险 | `accept=17 / would_drop=13`、修后 `place×slot=4` / `day×slot×place=2` 均为**上界估计**（旧日志 + 新函数静态重放）；真实跑批中被丢的消息会改变后续接话对象与在场者判断 | **无数据（上界估计，不是读数）** |
| **P-5** | **工具侧缺口：`tools/d2/emit_run_meta.py` 未登记 `HITT_DIALOGUE_PUBLIC_REPLY`** | `meta.json.switch_effective` **不含**该开关 ⇒ 开关生效**不能**用 `meta.switch_effective` 证明，只能靠 launch 证据链（`switch_proof.txt` / `host.log` / `launch_evidence.txt`）+ 行为差。**本轮未修**（不改 `tools/d2`，避免与跑批工具链交叉） | **不成立（缺口仍在）**（R41b §1.1 已登记，本轮延续） |
| **P-6** | **(b) 探针默认恒绿**：语义回滚探针只在 `R43_ROLLBACK=1` 下变红，常规 pytest 看不见 | 已在 §2.1 M4 贴死复跑命令与 `AssertionError` 原文 | **成立（已按审计要求披露）** |
| **P-7** | `test_old_architecture_reproduces_the_violation` 是**同义反复**（`gate([], …)` 恒放行），非旧架构行为证据 | 措辞降级为「读法说明」；**不得**称「复现了越界」。真证据：seq 189/487/613 + 基线树反向对照 | **不成立（作为证据）** |
| **P-8** | `place_slot_count` 对**缺 `day`/`slot`** 的旧记录按「通配」处理 ⇒ 潜在过严 / 口径松动 | 现存 `integration` 恒写 `day`/`slot` ⇒ 当前无影响；登记为已知边界 | **无数据（当前无影响）** |
| **P-9** | **全量 `life/tests` 未跑完** | 宽口径全量在 300s 门下超时未跑完（相关子集 46 passed）⇒ 按仓库纪律标「**未完成**」，**不写「全绿」** | **未完成** |
| **P-10** | 预过滤仍留在 agent 侧（显式取舍） | `_pick_reply_target()` 的场所判定保留为「省一次 LLM」的预过滤（**同函数、同键、非裁决**）。代价：每轮仍会有若干次注定被写入口拒掉的 LLM 调用，可观测为 `DROPPED{quota_place}` 数上升 + token 上升 | **成立（已登记的取舍）** |
| **P-11** | 单 seed / 单批 / 非盲（历史遗留） | 所有效果层数字只能作点估计、不外推 | **不可判（设计级）** — 与本轮无关，但引用时必须带着 |
| **P-12** | 本轮**未**验证的项（如实登记） | ① 未跑 `obs llm-cost`（无新批，无需验真）；② 未验证 `meta.switch_effective`（见 P-5）；③ 未做人工盲判 / LLM judge；④ `test_life_encounter_chat.py` 单跑 >120s，撰写者未复跑（实现方：修复后 11 passed / 144.71s、基线 11 passed / 140.23s —— **转述，未独立复核**）；⑤ 跨层三件（e2e / conservation / dialogue_repair）为转述；⑥ 全量 `life/tests` 未完成（P-9） | **未验证** |

**失败项登记（必须点名，不得含糊）**：
1. **`R41V-C4`（冻结判据）在修后静态回放判「不成立」**（`place×slot = 4 > 2`）——这是本轮**唯一一条「不成立」的判据级结论**，原因是**口径冲突**（P-0），不是实现没做。
2. **禁改区程序性偏离**一处（P-1），由 Leader 书面追认。
3. **`R41V-C1` 不可判**，两条并列原因（P-2）。
4. **全量单测未完成**（P-9）。
5. **基线与上游脱节 72 个提交（P-1b）——未验证**，是「合并 / 起批」的**前置阻断项**，不是本轮结论的反证。
其余为**未修缺口**（P-5）、**上界估计非读数**（P-4）、**已登记取舍**（P-10）、**不可判**（P-3 / P-11）、**未验证**（P-12）。**没有任何「把不可判写成无效」或反之的表述。**

---

## ④ 可展示案例（≥3 段真实对话原文 + `seq`；≥2 张现场渲染截图 + `sha256`）

> **前置声明（随每个案例一起读）**：**本周期零新跑批、零新 LLM 调用**。下列对话原文与截图**全部取自 `2026-11-01` 已收批的冻结日志**（`r41v` 批次，**由修复前的旧代码产出**），本轮**现场现算、现场现渲**（渲染器 `tools/metrics/render_shots.py`，两臂各 `rc=0`、`fail_count=0`），**未复用任何旧图 / 示意图 / 拼图**。
> **⚠ 这批案例与截图「用于展示问题现状，不代表修复效果」**：它们呈现的是 `R41V-C4` 越界的现场；修复后的行为**没有**新批读数（见 §③ P-3）。

### 4.1 真源与 `sha256`（现场重算）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
sha256sum v2/evidence/r41v_public_talk_n16r24_s42/{off,on}/run.jsonl
```

| 臂 | 路径 | `run.jsonl` sha256（实测） |
|---|---|---|
| ON | `v2/evidence/r41v_public_talk_n16r24_s42/on/run.jsonl` | `c8a7f546238ad801…`（sha8 = `c8a7f546`，与 R41b §1.2 一致） |
| OFF | `v2/evidence/r41v_public_talk_n16r24_s42/off/run.jsonl` | `50def26301c3761b…`（sha8 = `50def263`） |

摘录方式：取 `type=="MSG_PUBLIC"` 且 `payload.seq` 命中的行，`payload.body` 原文照抄，**未改一字**。

### 4.2 案例 1｜farm 的三条公开消息（**C4 越界现场**：`round1/day0/morning/farm = 3 > 2`）

| `seq` | 轮次 | 作者 | `reply_to` | `turn_index` | 逐字原文 |
|---|---|---|---|---|---|
| 189 | round 0 | P015 | `null` | 0 | （把灶上那锅萝卜牛腩的火拧小，拿勺子撇了撇浮沫）这两天忙得脚不沾地吧，我看你眼下都发青了——先坐，我给你盛碗汤。趁热喝。 |
| 487 | round 1 | P001 | `42:189` | 1 | （拿抹布擦桌角，油渍蹭了两下没掉）这牛腩炖了一上午，烂乎着呢。你嫂子回娘家前搁的萝卜，再不吃就糠了嘛。 |
| 613 | round 1 | P003 | `42:189` | 1 | （拿抹布擦了擦桌角，又顺手把歪了的筷子筒扶正）这阵子活儿赶，手都糙了。汤我自己来。 |

事实层：487 与 613 **同为** `turn_index=1`、**同** `reply_to="42:189"`、**同** `thread_id=TH-P015-PUB-0-0` ⇒ 两个接话者在各自决策时都「没看见对方」。本报告不对「接得好不好」下判断（无该判据）。

### 4.3 案例 2｜school 的两次接话（同一目标被两人接住）

| `seq` | 轮次 | 作者 | `reply_to` | 逐字原文 |
|---|---|---|---|---|
| 167 | round 0 | P013 | `null` | （把烧红的锄头往水桶里一浸，白汽直冒）这锄头是东头老周家的，刃口卷了，我正给他回火。你站远点，火星子不长眼。别急。 |
| 760 | round 1 | P006 | `42:167` | 铁头，你瞧这锄头是老周家那把，我正给它回火呢，你站远些别让火星子溅着吧。 |
| 1270 | round 1 | P012 | `42:167` | （拿火钳把锄头翻了个面，铁皮上还挂着水珠）铁头你来得正好，帮我把那桶里的水再添两瓢，老周这锄头回完火还得趁热敲两下，他明早要下地。 |

### 4.4 案例 3｜round 12 → 13 的跨轮接话（school，3 人接同一目标）

| `seq` | 轮次 | 作者 | `reply_to` | 逐字原文 |
|---|---|---|---|---|
| 19241 | round 12 | P005 | `null` | （把药碾子往桌角推了推，捻起一片晒干的陈皮对着光看）老周家那小子烧退了，我这心里才松快些。这陈皮还是去年秋天存的，得再翻晒一遍。手不能生。 |
| 20551 | round 13 | P004 | `42:19241` | （把案板上的面团翻了个面，指腹按了按）手不能生这话在理，我那炉杏仁酥今早火候就偏了一分。陈医你尝尝，老周家小子退了烧，嘴里该没味儿，这酥我少搁了糖。 |
| 21419 | round 13 | P016 | `42:19241` | 哟，陈医，你瞧我这摊上新收的紫苏，梗子还带露水呢。（拈起一撮凑近鼻尖）老周家小子退了烧，我这心才落回肚里。手不能生。 |

事实层：接话跨 round 生效（`reply_to` 指向 round 12 的 `42:19241`）；三条均复用目标句的「手不能生」与「老周家小子退烧」两个片段（**重复是事实陈述，不作质量判断**）。

### 4.5 案例 4｜town_hall 的单人接话

| `seq` | 轮次 | 作者 | `reply_to` | 逐字原文 |
|---|---|---|---|---|
| 19807 | round 12 | P013 | `null` | （把铁钳往砧子上一搁）听说你东家那批锄头催得紧，我这炉子刚空出来——你那边还缺人手不？ |
| 20857 | round 13 | P008 | `42:19807` | （把案上那摞户籍册往边上推了推）我这正给东街王家补办分家文书，墨还没干透。你那边炉子空出来了？ |

事实层：接话以**反问**回应目标的提问（原文如此），本报告不对「是否答上了」下判断。

### 4.6 现场渲染截图（4 张，真实 PNG，两臂各 `rc=0 / fail_count=0`）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 tools/metrics/render_shots.py --run-dir v2/evidence/r41v_public_talk_n16r24_s42/on \
  --batch-id r43 --outdir reports/figures --views chat,rhythm    # rc=0
python3 tools/metrics/render_shots.py --run-dir v2/evidence/r41v_public_talk_n16r24_s42/off \
  --batch-id r43 --outdir reports/figures --views chat,rhythm    # rc=0
```

| 图 | 路径（相对仓根） | 文件名内 sha8 | 字节 | 尺寸 | PNG 自身 `sha256`（实测） |
|---|---|---|---|---|---|
| ON chat | `reports/figures/r43-chat-c8a7f546.png` | `c8a7f546` | 309998 | 1400×900 | `cd2c18c14a9114710464906253c2e082710302dcc61088079b559e4cd85bd137` |
| ON rhythm | `reports/figures/r43-rhythm-c8a7f546.png` | `c8a7f546` | 280341 | 1300×1050 | `d9898ffea9e5e51d1f342cc40b7c864eaec51b161b4eb3141ea4fb8ea66e9353` |
| OFF chat | `reports/figures/r43-chat-50def263.png` | `50def263` | 299891 | 1400×900 | `f5dfebed9583ec18816301cdd43cb22afa6a4c3a99df4b491571ca01244fac3d` |
| OFF rhythm | `reports/figures/r43-rhythm-50def263.png` | `50def263` | 279233 | 1300×1050 | `233c51070503a833e41a4295682341b3270f2abc9feebd05e5a8ffe2626249ae` |

**`sha8` 口径（写死，不留歧义）**：文件名里的 `c8a7f546` / `50def263` = **该图所渲染的那一份 `run.jsonl` 的 `sha256` 前 8 位**（ON / OFF 两臂），**不是**本报告所属 commit 的 sha8。PNG 自身 `sha256` 另列一栏，两者不是同一个值。

**图说（逐张适用，不得删）**：**来源批次 = `r41v_public_talk_n16r24_s42`（ON 臂 / OFF 臂），用于展示问题现状，不代表修复效果。**

**溯源三件套**：`reports/figures/render_report_r43-on.json`、`render_report_r43-off.json` —— 每份含 `log_sha256`（on `c8a7f546…` / off `50def263…`）与逐图 `triplet`（`gen_threads_cmd` + `render_cmd` + `log_sha256`）；`threads_r43-{on,off}.json` 与报告内 `threads_json_sha256`（on `8379ab3f…` / off `f3521ad5…`）逐字节一致（附录 B·B9 复核）。

**截图只证「批次真实存在 + 渲染链通 + 页面结构完整」，不支撑任何措辞质量、越界归零或修复效果结论。**
**失败项登记：无**（两臂 `ok_count=2 / fail_count=0`，四张图均过渲染器自带像素自检 `distinct_colors ≥ 200 且 top_color_frac ≤ 0.99`）。渲染只起本地临时静态服务（`http://127.0.0.1:<随机端口>`），**未在 `code/frontend` 下写入任何文件**（`git status --porcelain -- code/frontend` 未新增本轮文件）。

---

## ⑤ 下一周期计划（`P1/P2`：事项 + 验收口径 + 阻断点；并单列明确不做）

### P1（前置）为什么本轮没跑验证批：**两条并列理由（分母 + 尺子），以及为什么判据必须从「比率」改成「结构」**

先说清事实：**串行车道此刻是空的**（`ps -eo pid,etime,cmd | grep -F "orchestration run" | grep -v grep | wc -l` ⇒ **0**），所以「本轮没跑验证批」**不是**因为车道被占、也**不是**「没时间」。

**理由一（分母，**上界推导**）**：R41b ON 臂 `MSG_PUBLIC = 30`；fix-1 的静态反事实（**上界估计，非读数**）为 `accept = 17 / would_drop = 13` ⇒ 同规模重跑后 ON 臂期望 ≈ 17 条。`17 < 30` ⇒ 按「分母 < 30 不报比率」的纪律，`R41V-C1` 依旧不可判。同时 OFF 臂 `MSG_PUBLIC = 24` 且 OFF 下闸恒放行 ⇒ **17 < 24**，同规模重跑**很可能反而让 `R41V-C5`（非塌陷，`n_on ≥ n_off`）判「不成立」。
> **但这只是上界推导；而且这条理由已被理由二绕过**：扩样本**买不到** C1 的可判性——见理由二。

**理由二（尺子缺陷，属 P0 级问题；见 §③ P-2）**：`R41V-C1` 的分子由 `public_talk_metrics.py:180-192` 的 `reply_to_form()` 判定，其 `msg_ids` 集合来自同文件 `:422` 的 `{pl["msg_id"] …}`，而 `reply_to` 存的是 `msg_uid`（`integration.py:950-954`）⇒ 命中 `msg_id` 集合 **0**、命中 `msg_uid` 集合 **7**。**尺子不修，样本扩到多大 C1 都不可判**——分母不是唯一瓶颈，甚至不是主瓶颈。

**理由三（判据形态）**：本轮修的是**有界性（结构）**，不是「频率提升」。用比率型判据（C1）判一个「压密度」的闸，方向就错——所以 P1 的验收改为**结构判据 S1/S2/S3**（见下表）。

**⚠ C5 必须改写（不能照旧口径）**：`R41V-C5` 定义是 `n_on ≥ n_off`（非塌陷）。但本闸的设计目的**就是压低同格子密度**：静态估计 ON `30 → ~17` 而 OFF 仍 `24` ⇒ **照旧口径会把「修好了」判成「塌陷」**。这属**判据与机制目的冲突**，必须由**预登记卡冻结改写**，**不许边跑边改**。

| 优先级 | 事项 | 验收口径 | 阻断点 |
|---|---|---|---|
| **P0** | **预登记修订（最高优先，决定 C4 能不能判）**：新开一份 prereg 卡，显式声明为对 `R41V-C4` 判据的**修订**——把键写成 `day×slot×place`，并附本次数据（`place×slot` 9 / `day×slot×place` 5）、修订理由（`place×slot` 忽略 day 是跨天累计，用 2 判它会把不同日子叠在一起）与「修订后修前读数」 | 修订卡 commit **早于**起跑；卡内同时保留**原文口径**与**修订口径**两栏（可追溯 goalpost 变更）；`git log -1 --format=%H -- <修订卡路径>` 可取 | **阻断点**：不修订则按冻结口径 `R41V-C4` 恒判不成立（修后静态回放 4 > 2）⇒ 跑批也换不来「达成」。**处置（含 P-1b 上游脱节）**：先做上游 72 提交的差异评估 → **若命中** `public_talk.py` / `integration.py` / 场所·接话逻辑 ⇒ **先 rebase 并重跑三探针（a/b/c）**再冻结卡；**若未命中** ⇒ 在修订卡里注明「上游 72 提交未触及相关路径」并留取法 |
| **P1** | **修尺子 `msg_id` vs `msg_uid`（P0 级，独立于跑批）** | `public_talk_metrics.py:180-192` 的分子集合纳入 `msg_uid`（或保留两套键并显式标注用的是哪套）；修后用 r41v 重算：`real_message_id` 命中 **0 → 7**、`k_off` 仍 0 | **阻断点**：属度量侧，改完须重算历史批确认口径不倒退（先例 R19「尺子恢复可动 ≠ 改善」）；**不修则 C1 永久不可判** |
| **P2** | **把 C4 推到「效果级（结构侧）」**：P0 修订卡冻结 + P1 尺子修好后，起 OFF/ON 两臂批 | ① 两臂新 `run.jsonl` sha256 + `obs llm-cost` `rc=0` + `provider_guard.ok=true` + `total.calls>0`；② **S1（主）**：`max count(MSG_PUBLIC) per day×slot×place ≤ 2`，即**违规格子数 = 0**（`n=24`（2 天）时检出概率 98.7% = `1 − 0.833^n`，未修复违规格子率 `4/24`）；③ **S2（防「用静音换合规」）**：接话 ≥1 条、≥1 个多轮公开 thread、覆盖 ≥1 个 `place×slot`（**取代** `R41V-C5` 的 `n_on ≥ n_off`）；④ **S3（防闸判错键）**：`DROPPED{reason:"quota_place"}` 只出现在同格子第 3 条及以后，且带 `gate:"r43/1"`、`n_place ≥ 2` | **阻断点**：Leader 授权 + 预算；P0/P1 未先行则跑完仍不可判 |
| **P3** | **补工具侧缺口 P-5**：`tools/d2/emit_run_meta.py` 登记 `HITT_DIALOGUE_PUBLIC_REPLY` | 新批 `meta.json.switch_effective` **包含**该键；开关生效可用 `meta` 单独证明 | **阻断点**：属跑批工具链，须与 P2 同窗口一起改 |
| **P4** | **去掉预过滤（P-10）或量化其代价** | 二选一：① 删掉 agent 侧预过滤，报 `DROPPED{quota_place}` 数与 token 增量；② 保留并在新批里给出「预过滤命中数 / 写入口拒数」两个计数 | **阻断点**：需 P2 的批才有代价读数 |
| **明确不做** | ① 用静态反事实 `17/30` 或 `would_drop=13` 当修复后读数；② 用旧日志（`c8a7f546`）宣称「端到端越界归零」；③ 同规模（`16 agents × 24 rounds`）重跑两臂；④ 改 `code/engine` 单轮闭环 / `perceive.py` 可见性上界（属引擎语义，必须新开分支 + 全量回归）；⑤ 已关闭的三条线（`reply_window_rounds` 2→4 / `_initiate` 对端选择 / 再加出口·再加示例）；⑥ 自然度 judge（`W-1-e`）；⑦ 调整 `MAX_PER_PLACE_PER_SLOT` 常量值（本轮修的是「判定点与键」，**不是**阈值调参）；⑧ **边跑边改判据 / 事后补判据**（S1/S2/S3 与 C5 改写必须先进预登记卡并冻结）；⑨ **不做预登记修订就直接按新口径宣称「C4 达成」**（那是 goalpost——冻结卡写的 `place×slot` 修后仍 4 > 2） | —— | ①②③ 都会把「机制级证据」冒充成「效果级结论」（③ 见 §P1 算术：必然不可判）；④ 会污染生活层改动；⑦ 会把「功能缺陷修复」偷换成「调参」 |

---

## 附录 A · 提交与推送实测回填（sha 用取法，不写死）

| 项 | 状态 / 实测 | 取法 |
|---|---|---|
| 本报告文件 commit sha | **未提交**（按 Leader 要求：报告留在工作树，由 Leader 统一提交） | `git log -1 --format=%h -- reports/R43-place-talk-quota-fix.md`（提交后现查） |
| fix commit sha | `cd09bfbd125d3a03b9e62d8f2fd6c286f25ab7dc`（撰写时刻快照） | `git rev-parse HEAD` 或 `git log -1 --format=%H -- code/life/public_talk.py` |
| 截图目录状态 | `reports/figures/r43-*.png` + `render_report_r43-*.json` + `threads_r43-*.json`，**未提交** | `git status --porcelain -- reports/figures` |
| 推送 | **未推送**（等 Leader 授权）；**远端此刻尚无同名分支**（`git ls-remote origin refs/heads/fix/place-talk-quota-r43` 无输出 ⇒ 首次 push 无覆盖风险） | `timeout 30 git ls-remote origin fix/place-talk-quota-r43` 与 `git rev-parse HEAD` 比对（**不要**用 `git rev-list --count origin/<branch>..HEAD`，那只看本地 ref） |
| 建议提交范围 | `reports/R43-place-talk-quota-fix.md`、`reports/figures/r43-*.png`、`reports/figures/render_report_r43-{on,off}.json`（`threads_r43-*.json` 可不入库）+ fix-1 已提交的 5 个代码文件 | —— |
| 上游可达性 | `git fetch`/`ls-remote` 通道正常：`git ls-remote origin refs/heads/master` **rc=0** 并返回 `0345742`（认证 / 网络正常）。**但本地血统落后远端 `master` 72 个提交（`origin/master...HEAD` ⇒ `72 / 45`），差异影响未评估 —— 见 §③ P-1b** |
| 禁区 | 主工作树既有的 5 个已跟踪改动（`reports/CYCLE-37-20261031.md`、`*.pyc`、`v2/refs/D9*.md`）与无关未跟踪文件**一律不 stage** | `git status --porcelain` |

---

## 附录 B · 本报告全部数字的复算入口（可直接粘贴；只读、零 LLM、零跑批）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# B0 编号占用检查（回答"为什么是 R43"）
git ls-files reports/ | grep -Ei 'reports/R4[0-9]'      # → 只有 R41 / R41b / R42

# B1 结构与行号（对照 §1.3 / §2.1 R43-M1）
grep -n 'GATE_VERSION\|def place_slot_count\|def place_quota_gate\|def public_count_at\|def place_quota_ok' code/life/public_talk.py
grep -n '_r43_place_gate\|_r43_gate_version\|quota_place' code/orchestration/integration.py

# B2 单测（对照 §2.1 R43-M2 / R43-M6）
cd code
python3 -m pytest life/tests/test_r43_place_talk_quota.py -q                                        # 期望 11 passed
python3 -m pytest life/tests/test_r41_public_talk.py life/tests/test_r43_place_talk_quota.py -q     # 期望 40 passed
python3 -m pytest life/tests/test_r41_public_talk.py -q                                             # 期望 29 passed
cd ..

# B3 阈值探针（R43-M3，含在 11 条里；单独跑）
cd code && python3 -m pytest life/tests/test_r43_place_talk_quota.py -q -k "threshold" ; cd ..

# B4 语义回滚探针（R43-M4）—— 期望 1 failed
cd code && R43_ROLLBACK=1 python3 -m pytest life/tests/test_r43_place_talk_quota.py -q -k rollback ; cd ..

# B5 基线摘除对照（R43-M5）—— 期望 9 failed, 2 passed
rm -rf /tmp/r43_baseline && mkdir -p /tmp/r43_baseline
git archive ad3538f code | tar -x -C /tmp/r43_baseline
cp code/life/tests/test_r43_place_talk_quota.py /tmp/r43_baseline/code/life/tests/
cd /tmp/r43_baseline/code && python3 -m pytest life/tests/test_r43_place_talk_quota.py -q --tb=line ; cd - >/dev/null

# B6 跨层回归（R43-M6，实现方实测值见 §2.1；本组撰写者未独立复跑）
cd code && python3 -m pytest tests/test_e2e_integration.py tests/test_conservation.py tests/test_dialogue_repair.py -q ; cd ..

# B7 离线复算 + 四粒度（对照 §2.2；**旧日志 + 新函数静态重放，不是修复后读数**）
python3 tools/public_talk/recount_place_quota_r43.py v2/evidence/r41v_public_talk_n16r24_s42/on/run.jsonl
python3 tools/public_talk/recount_place_quota_r43.py v2/evidence/r41v_public_talk_n16r24_s42/off/run.jsonl

# B8 真源 sha256（对照 §4.1）
sha256sum v2/evidence/r41v_public_talk_n16r24_s42/{off,on}/run.jsonl

# B9 截图真伪 + 溯源一致性（对照 §4.6 表）
python3 - <<'PY'
import struct, os, hashlib, json
d="reports/figures"
for f in sorted(os.listdir(d)):
    if not (f.startswith("r43-") and f.endswith(".png")): continue
    b=open(os.path.join(d,f),"rb").read()
    w,h=struct.unpack(">II", b[16:24])
    print(f, len(b), f"{w}x{h}", b[:8]==b"\x89PNG\r\n\x1a\n", hashlib.sha256(b).hexdigest())
for a in ("on","off"):
    r=json.load(open(f"reports/figures/render_report_r43-{a}.json"))
    print(a, "log_sha256=", r["log_sha256"][:16], "ok=", r["ok_count"], "fail=", r["fail_count"],
          "threads_sha256=", r["threads_json_sha256"][:16])
    # threads 与归档文件是否逐字节一致
    print("  threads file sha256 =", hashlib.sha256(open(f"reports/figures/threads_r43-{a}.json","rb").read()).hexdigest()[:16])
PY

# B10 对话原文回取（对照 §4.2–4.5，逐字）
python3 - <<'PY'
import json
want={189,487,613,167,760,1270,19241,20551,21419,19807,20857}
for line in open("v2/evidence/r41v_public_talk_n16r24_s42/on/run.jsonl",encoding="utf-8"):
    d=json.loads(line)
    if d.get("seq") in want and d.get("type")=="MSG_PUBLIC":
        p=d["payload"]
        print(d["seq"], d.get("round"), p.get("author"), p.get("reply_to"), p.get("place"), p.get("slot"), p.get("turn_index"), "|", p.get("body"))
PY
```

# B11 C1 尺子缺陷复算（对照 §③ P-2；期望 hit msg_id = 0 / hit msg_uid = 7）
python3 - <<'PY'
import json
pubs=[json.loads(l)["payload"] for l in open("v2/evidence/r41v_public_talk_n16r24_s42/on/run.jsonl",encoding="utf-8")
      if l.strip() and json.loads(l).get("type")=="MSG_PUBLIC"]
ids={p["msg_id"] for p in pubs if isinstance(p.get("msg_id"),str)}
uids={p["msg_uid"] for p in pubs if isinstance(p.get("msg_uid"),str)}
nn=[p for p in pubs if p.get("reply_to") is not None]
print("pub=",len(pubs),"reply_to nonnull=",len(nn),
      "hit msg_id =",sum(1 for p in nn if p["reply_to"] in ids),
      "hit msg_uid =",sum(1 for p in nn if p["reply_to"] in uids))
PY

# B12 静态反事实 + 双口径（对照 §2.2 的 4 / 2 / 2；**上界估计，非读数**）
python3 - <<'PY'
import sys, json, collections
sys.path.insert(0,'code')
from life import public_talk as PT
recs=[json.loads(l) for l in open("v2/evidence/r41v_public_talk_n16r24_s42/on/run.jsonl",encoding="utf-8")
      if json.loads(l).get("type")=="MSG_PUBLIC"]
acc=[]
for r in recs:
    p=r["payload"]
    ok,_=PT.place_quota_gate(acc,p.get("place"),p.get("day"),p.get("slot"))
    if ok: acc.append(r)
f=lambda k: max(collections.Counter(k(a) for a in acc).values())
print("accept",len(acc),"drop",len(recs)-len(acc),
      "| max place_slot(frozen) =",f(lambda a:(a["payload"].get("place"),a["payload"].get("slot"))),
      "| max day_slot_place(revised) =",f(lambda a:(a["payload"].get("day"),a["payload"].get("slot"),a["payload"].get("place"))),
      "| max round_day_slot_place =",f(lambda a:(a.get("round"),a["payload"].get("day"),a["payload"].get("slot"),a["payload"].get("place"))))
PY

# B13 上游脱节（对照 §③ P-1b；差异影响**未评估**）
git rev-parse master
git ls-remote origin refs/heads/master
git rev-list --left-right --count origin/master...HEAD        # 期望 72  45
git ls-remote origin refs/heads/fix/place-talk-quota-r43      # 期望：无输出（远端尚无该分支）

**复算纪律**：
- B7 的输入是**旧代码**产出的日志，输出只用于「两把尺子对账」与「静态反事实」，**不得**当成修复后读数。
- B2–B6 是单测 / 对照组级证据，**不得**升级成效果级结论。
- B9 里 `threads_r43-*.json` 与 `render_report` 的 `threads_json_sha256` 必须相等；**不等即为归档出错**，以 `render_report` 为准。

**本轮自检记录（撰写者撰写时实际执行过，不是"应该能跑"）**：

| 检查 | 实测结果 |
|---|---|
| B0 编号 | `reports/` 仅 R41 / R41b / R42；`R43` 未被占用 |
| B1 行号 | `public_talk.py:107/125/158/164/173`、`integration.py:191/214/907-914` 逐条 grep 命中，与 §1.3 一致 |
| B2 单测 | `11 passed in 0.06s`；两文件合并 `40 passed in 0.18s`（实现方记 0.21s，差异为机器抖动，不影响结论） |
| B5 基线摘除 | 撰写者独立复跑：`9 failed, 2 passed in 0.20s`；承重点 `test_do_social_caps_third_public_message_at_same_place` 报 `AssertionError: 同 place×day×slot 的第 3 条必须被写入口拒掉`（第 123 行），另有第 141/152 行断言级红 + 6 条 `AttributeError` |
| B7 离线复算 | 撰写者独立复跑 ON 臂：`max[round_day_slot_place]=3`、`max[day_slot_place]=5`（`day0/afternoon/bank`）、`max[slot_place_ignore_day]=9`（`bank/afternoon`）、`max[slot_place_replies_only]=4`（`school/morning`）、`max[author_slot_replies]=1`；`counterfactual accepted=17 would_drop=13` |
| B9 截图 | 四张 PNG magic 全为真 PNG、尺寸/字节数与 §4.6 表逐项一致；两臂 `rc=0`、`fail_count=0`；`threads_r43-{on,off}.json` 的 sha256 与 `render_report` 记录**逐字节一致** |
| B10 原文 | 11 个 `seq` 的 `payload.body` 与 §4.2–4.5 逐字一致 |
| B11 尺子缺陷 | 撰写者独立复跑：`pub=30 / reply_to nonnull=7 / hit msg_id=0 / hit msg_uid=7`（与 audit-1 §6.2 同值） |
| B12 双口径反事实 | 撰写者独立复跑：`accept=17 / drop=13`；`place×slot`（冻结口径）**= 4**、`day×slot×place`（修订口径）**= 2**、`round×day×slot×place` = 2 |
| B13 上游 | `master=94e272a`、`origin/master=0345742`、`origin/master...HEAD = 72 / 45`；远端无 `fix/place-talk-quota-r43` 分支（首次 push 无覆盖风险）。**差异影响未评估** |
| 未执行项 | ① `obs llm-cost`（无新批，无需验真）；② 跨层三件（B6）未独立复跑（转述实现方）；③ `test_life_encounter_chat.py` 未复跑（见 §③ P-12）；④ **全量 `life/tests` 未跑完**（§③ P-9）；⑤ **上游 72 提交差异未评估**（§③ P-1b） |
