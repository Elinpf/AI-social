# R20 · F-6 跨天记忆引用：固化链路（机制层已通 / 行为层未验证）

> 本轮唯一推进维度：**F-6 跨天记忆引用**的**上游固化链路**。
> 执行：`life-behavior-eng`（实现与证据） / `evidence-auditor`（独立核验） / `report-writer`（收敛与交付）。
> 报告口径纪律：机制接通 ≠ 效果改善；尺子恢复 ≠ 提升；pilot 不外推；缺 meta 只记 `probe`。

---

## 0. 取数时刻与仓库身份

| 项 | 值 | 取法 |
|---|---|---|
| 报告取数时刻 | **2026-10-22 22:1x +0800**（见 §0.1 实跑记录） | `date` |
| 分支 / HEAD | `master` @ **`84ed6b1`**（`84ed6b146a66a10b4409b08c7380b8fab8007d10`，2026-10-22T21:56:26+08:00） | `git rev-parse HEAD` |
| origin 对照 | `git rev-list --left-right --count origin/master...master` → **`0 0`** | 实跑（本地引用口径，非 `ls-remote`） |
| 本轮是否有新跑批 | **无**（预登记决策规则 3 触发，见 §3） | `v2/evidence/f6_chain_20261022/README.md` §4 |
| 本轮改动性质 | **只新增证据文件 + 本报告**；`code/` 未改 | `git status --short` |

> 引用纪律：本报告所有结论绑定上述 HEAD `84ed6b1` 与两个批次各自的 `code_sha`（A5 `51cdb07`、D12-A `a6ae5e5`）。
> **master HEAD 不能替代臂 commit**——读者要复现的是"那批数据用哪版代码跑的"。

### 0.1 取数时刻实跑记录

见 §7 复算命令块中的 `date` 与 `git` 组；交付回执见 §11（含 push 后 `git log -1` 与 `rev-list --left-right --count origin/master...master` 的真实输出）。

---

## 1. 本轮推进维度与预登记判据

### 1.1 为什么是 F-6

来自现状基线 `state-survey.md`（取数时刻 2026-10-22 22:00，HEAD `84ed6b1`）：

- F-6 是**唯一一个跨臂零变化**的生活气息维度：v0 **6.4%** → A0 **6.4%**（两臂同值，分母分别 **187 / 686**；`reports/R4-life-texture.md:107` 原文记为「方向性持平略降」），A1-措辞 **4.8%（6/124，`probe`）**。
- 它的**上游管道历史上是坏的**：`c01f6dd` 之前三批 `MEMORY_CONSOLIDATE` 的 `discard_rate` 均 100.00%、`SM_write_count` 均 0（缺陷基数 `v2/evidence/fix-sleep-consolidation-20261022/r10_defect_baseline.out`，sha256 `83445e18…`）⇒ 6.4% 这个数是在"固化记忆根本没落账"的前提下测出来的。
- 管道修好后（R18，`reports/R18-sleep-consolidation-fix.md`，commit `b0cd58d` / 合并 `cd8f024`）**零行为读数**，R18 §9.1 原文：「真跑批上的端到端数字未验证」「不作任何效果宣称」。
- R18 定的口径要求：**先证明记忆真被检索引用（CONSOLIDATE 落账 → WRITE → RETRIEVE → 对话正文命中），再谈 F-6 率**，否则会重演"用 timeref 词表命中冒充记忆引用"。

### 1.2 预登记（先写后跑）

- 文件：`v2/evidence/f6_prereg_20261022.md`，sha256 **`5c266083c5ac3e1a271149f819490ca536f68aab2114d247a7dc8a38f3b9e835`**
- 落盘时刻 **22:06**，**早于本轮任何跑批**（本轮未跑批，故"先写后跑"在本轮退化为"先写后裁决"）。
- 预登记把问题拆两栏，**禁止混写**：
  - **Q1（机制层）**：`c01f6dd` 之后，`MEMORY_CONSOLIDATE(落 text) → MEMORY_WRITE(SM) → MEMORY_RETRIEVE(选中 SM)` 在**真 LLM 日志**里是否真的活了？
  - **Q2（行为层）**：跨天记忆是否真的进入对话并被引用（F-6 率是否可判）？

**预登记判据（原样抄自 §1，判据编号 C1–C4）：**

| 环 | 指标 | PASS | FAIL | 不可判 |
|---|---|---|---|---|
| **C1** CONSOLIDATE 落 text | `MEMORY_CONSOLIDATE` 中 `payload.text` 非空比例 | ≥ 99% | = 0% | 介于其间 |
| **C2** SM 落账 | `MEMORY_WRITE` 中 `mem_id` 含 `-SM-` 且 `kind=semantic` 的唯一条数 | ≥ 1 | = 0 | — |
| **C3** 检索返回 | `MEMORY_RETRIEVE.selected_mem_ids` 非空比例；被选中 SM mem_id 唯一数 | 比例 > 0 且 SM 命中 > 0 | 全空 | — |
| **C4** 正文命中 | 对话 `MSG` 中 `ctx.memory_refs` 非空条数；注入记忆与正文实质重合 | >0 且能定位具体被引用记忆 | 注入面 0 **且** 臂 OFF | 臂 ON 但注入内容为无信息占位 |

**预登记决策规则（先写死，不得事后下调）：**
1. C1–C3 任一 FAIL，或 C4 判"注入路径对 SM 不成立" ⇒ **不跑 pilot**，交"机制层证据 + 行为效果未验证"。
2. C1–C3 全 PASS 且 C4 成立 ⇒ 才允许跑 1 个 `n8×16` pilot。
3. C1–C3 全 PASS 但 C4 不成立 ⇒ **不跑 pilot**（跑了也不会有 SM 的 F-6 读数，属"为凑结论跑小样本"）。
4. 不得因"想有数字"降低判据；**不可判 优于 假结论**。

---

## 2. 链条证明（分子/分母 + 命令）

复算脚本：`v2/evidence/f6_chain_20261022/verify_chain.py`（sha256 `f09cf257193cfaef5de1fad784517db98b18ec063096acbd5511658b742cf711`，只读，不跑批）
输出：`v2/evidence/f6_chain_20261022/chain_out.txt`（sha256 `8c61dbf0b7ec3f6664adc0a00d7db7852fcf42c93511b224a70acc64a7c53457`）

命令（仓库根目录，**任何人可重跑**）：

```bash
python3 v2/evidence/f6_chain_20261022/verify_chain.py | tee /tmp/chain_recheck.txt
diff /tmp/chain_recheck.txt v2/evidence/f6_chain_20261022/chain_out.txt && echo IDENTICAL
```

> 报告作者已独立复跑一次，输出与 `chain_out.txt` **逐行一致**。

### 2.1 两个日志能证明什么（代码版本事实）

| 批次 | 目录 | `code_sha` | 起跑 | 相对 `c01f6dd`(18:20)/`cd8f024`(18:26) |
|---|---|---|---|---|
| A5 | `v2/evidence/run_a5_real_n16r42_seed42/` | `51cdb07` | 2026-10-22T17:07:25+08:00 | **修复前**（`git merge-base --is-ancestor c01f6dd 51cdb07` → False） |
| D12-A | `v2/evidence/run_d12a_real_n16r24_seed42/` | `a6ae5e5` | 2026-10-22T20:24:36+08:00 | **修复后**（同上 → True） |

⇒ **只有 D12-A 能证明"修复后行为"**；A5 仅作修复前对照。

**归因链（三条独立证据并列，缺一不足以归因）**

| # | 证据 | 命令 | 结果 |
|---|---|---|---|
| ① git 祖先 | `git merge-base --is-ancestor c01f6dd a6ae5e5` / `… c01f6dd 51cdb07` | 前者 **True**（rc=0）、后者 **False**（rc=1） |
| ② 代码树差异（比祖先更硬） | `git show 51cdb07:code/orchestration/integration.py \| grep MEMORY_CONSOLIDATE` vs `git show a6ae5e5:…` | `51cdb07` **无** `_PASSTHROUGH["MEMORY_CONSOLIDATE"]`；`a6ae5e5` **第 211 行**有 `"MEMORY_CONSOLIDATE": ("text",)` |
| ③ 批内行为签名 | A5 / D12-A 的 `DROPPED[unknown_intent_field, keys=('text',)]` | **755 vs 0** ⇒ 修复的因果签名直接出现在日志字段上，不依赖 git |

附：`git cat-file -t a6ae5e5` → `commit`（7 位短 sha 唯一可解析，无歧义）。

### 2.2 C1–C4 读数表

| 环 | 指标 | A5（修复前 `51cdb07`） | D12-A（修复后 `a6ae5e5`） | 判定 |
|---|---|---|---|---|
| **C1** | `MEMORY_CONSOLIDATE` 的 `text` 非空比例 | **0/755 = 0.00%** | **499/499 = 100.00%** | 修复前 FAIL / 修复后 **PASS** |
| **C2** | `MEMORY_WRITE` 中 `-SM-` 唯一条数 | **0**（kind 分布 `{}`） | **256**（全 `semantic`） | 修复前 FAIL / 修复后 **PASS** |
| **C3** | `selected_mem_ids` 非空比例；被选中 SM 唯一条数 | 656/672 = 97.62%；**SM 0** | 368/384 = 95.83%；**SM 103** | 修复前 FAIL（无 SM）/ 修复后 **PASS** |
| **C4** | 对话 `ctx.memory_refs` 非空条数 | 0/523（`LIFE_PROMPT_MEMORY_F6=<unset>`） | **0/191**（同上 `<unset>`） | **不可判**（注入臂未开） |

**旁证（同一脚本直接复算）**：A5 的 `DROPPED[reason=unknown_intent_field, keys=('text',), type=MEMORY_CONSOLIDATE]` = **755**，与 `MEMORY_CONSOLIDATE` 数（755）**逐条相等** ⇒ 修复前每次固化的 `text` 都被丢；D12-A 同项 = **0**。这正是 `code/orchestration/integration.py:211`（`"MEMORY_CONSOLIDATE": ("text",)`）生效的直接证据。

**修复前缺陷的准确定性（审计 + 实现者只读复算一致，比单看 C1 更硬）**：
两批的**固化目标集合相同**——`produced_mem_id` 形如 `M-{agent}-SM-{subject}`，由 agent×subject 决定，**16×16 = 256**；两批 `produced_mem_id` 去重集合**双向差集为空（完全相同，256 个）**。但**落账结果不同**：A5 的 **755** 条固化落到同样这 256 个 id 上、`MEMORY_WRITE(-SM-)` 去重 = **0**；D12-A 的 **499** 条固化落到同样这 256 个 id 上、`MEMORY_WRITE(-SM-)` 去重 = **256**。
⇒ 修复前的缺陷**不是"没算出固化组"，而是"算出来了（256 个目标齐全）、正文透传与落账全丢"**。
> 注意措辞：**不得**写"两批固化量相同"（755 ≠ 499，且 499 条落 256 个 id 是设计使然）；正确写法是「**目标集合相同（16×16=256），落账结果不同（A5 = 0 / D12-A = 256）**」。
> 复算（只读，两批 `produced_mem_id` 集合比对）：

```bash
python3 -c "import json
def P(f):
    s=set()
    for l in open(f):
        d=json.loads(l)
        if d['type']=='MEMORY_CONSOLIDATE':
            p=d['payload'].get('produced_mem_id')
            if p: s.add(p)
    return s
a=P('v2/evidence/run_a5_real_n16r42_seed42/run.jsonl'); b=P('v2/evidence/run_d12a_real_n16r24_seed42/run.jsonl')
print(len(a),len(b),a==b,len(a-b),len(b-a))"
# 期望输出：256 256 True 0 0
```

**链内自洽（原为审计额外交叉检查项，现已在 `chain_out.txt` 中直接打印，可复算）**：
- `MEMORY_CONSOLIDATE.produced_mem_id` 去重 = **256**，与 SM `MEMORY_WRITE` 的去重 `mem_id` 集合**完全相等**（双向差集皆空）；
- 被检索选中的 **103** 个 SM id **全部 ⊆** 这 256 个（无"检索到从未写入过的记忆"）；
- SM 写入按 day：**day0 = 243 / day1 = 13**（`slot=night`）⇒ day1 已有 243 个 day0 的 SM 满足 `node.day < today`，**跨天资格成立、不是瓶颈**；
- 499 条固化 → 256 个唯一 SM：`mem_id` 形如 `M-{agent}-SM-{subject}`，同 subject 反复固化落同一节点 ⇒ 唯一数 < 固化数**属设计，不是丢数据**。

> ⚠ **本节两条限制语必须与读数同读（审计 §白名单）**：① A5 为修复前批（`51cdb07`）、D12-A 为修复后批（`a6ae5e5`），**两批跨臂跨窗口（A5 42 轮 / d2-prefer 臂 vs D12-A 24 轮 / d12-detail 臂）⇒ 这是机制"存在性"对比，不是 DiD / 受控对照**；② **两批均无 `meta.json` ⇒ 证据等级 `probe`**。

### 2.3 C4 为什么是「不可判」而不是「FAIL」

- 开关事实：F-6 注入臂 `LIFE_PROMPT_MEMORY_F6`（`code/life/agent.py:60`，判定函数 `:67-68`）**默认 OFF**；OFF 时 `_memory_line()`（`:1195` 起）直接返回空串且 `self._mem_refs=[]`，且 `ctx.memory_refs` **只在非空时才写入 payload**（`:953-957`）⇒ 字段不出现。两批 `switch_proof.txt` 均无该 env（`<unset>`）⇒ 注入面为 0 是**开关决定的**，不能据此说"记忆进提示词这个能力坏了"。
- 但**即便把臂打开**，固化出的 SM 记忆当前也很难进提示词，两条可读代码事实：
  1. **SM 正文是确定性模板、不含真实内容**：`code/life/forgetting.py:177-179` 的 `summarize()` 返回 `f"关于{subject}的印象（由{count}条经历聚合）"`（注释原文：**非 LLM 生成**）。D12-A 实测 499/499 条 `text` 正是该模板（脚本 `模板文本=499`）。⇒ 修复的是**可观测性**（字段不再被丢），不是**信息量**。
  2. **注入排序把 SM 挤在后面**（代码事实：`code/life/agent.py:62` `MEMORY_F6_TOP_N=2`，`:1285-1295` 桶序 `("observation","other")` + `break`）：`_memory_line` 先填 `observation` 桶，`semantic`（SM 的 kind）属 `other` 桶。D12-A `day0` observation `MEMORY_WRITE` 达 **6125 条** ⇒ 只要任一 agent 跨天时有 ≥2 条可读 observation，SM 就排不进这 2 个槽位。附：SM 模板文本过 `_readable` 门为 **480/499**（被拒 19 条全是 `subject=MARKET`）⇒ "能不能过门"不是主要问题，**"排不排得上"和"有没有内容"才是**。
  - ⚠️ 边界：observation 的 `MEMORY_WRITE.payload` **不含 text**（只有 `body_ref=side://…`，审计抽查 2 条确认），正文存 side 存储、不随日志落盘 ⇒ "有多少条 observation 可读"**无法从日志复算** ⇒ 第 2 条只作**排序事实陈述 + 条件性推断**，**不写任何比例**。

---

## 3. 跑批：本轮**不跑**，及依据

预登记规则 3 触发（C1–C3 全 PASS，但 C4 对 SM 不成立）。四条理由（来自 `v2/evidence/f6_chain_20261022/README.md` §4）：

1. **C4 路径对 SM 不成立**：`n8×16` 无论 ON/OFF 都产不出"SM 固化记忆被对话引用"的可判读数——OFF 时 `ctx.memory_refs` 恒 0（提示词不碰记忆，与 F-6 率无关）；ON 时注入的是 observation（有真实内容）而非 SM ⇒ 测到的是**旧 F-6 臂**，不是固化链路。
2. **F-6 臂 ON/OFF 已有正式读数**：`reports/R11-f6-memory-into-dialogue.md`（`n16×60` seed42）OFF `19/510` → ON `57/510`（+7.45pp），但 **L-7 同步恶化 +29.61pp 越过预注册闸门 ⇒ 不构成净改善**。再跑 `n8×16` 只是"重复 R11 的臂 + 样本更薄"。
3. **样本太薄**：`ROUNDS_PER_SLOT=3 × SLOTS_PER_DAY=4 = 12 回合/天`，`n8×16` = 1 天 + 4 回合，**跨天机会仅约 4–5 个回合**（跨天要求 `node.day < today`，最早 day1 才可能引用 day0）⇒ 分母过小，无法在噪声之上判定。
4. **成本纪律**：单批真 LLM 虽不高（参照 D12-A `n16×24` 为 2252 次调用），但花在这三个已被排除的方向上换不到可判读数。

⇒ 本轮交付形态：**机制层证据（已达成）+ 行为效果未验证（不可判）**。这是本项目接受的合格产出；**不可判 优于 假结论**。

---

## 4. 读数表（本体 = 无新批 ⇒ 无新截图 / 无新 llm-cost）

### 4.1 本轮读数性质说明

本轮**未起任何新批**，因此：

| 项 | 状态 | 说明 |
|---|---|---|
| 新批 `run.jsonl` / `switch_proof.txt` | **无**（不适用） | 未跑批 |
| 新批 `meta.json` | **无**（不适用） | 未跑批；**不补写、不伪造** |
| 新批真 LLM `obs llm-cost` | **无**（不适用） | 未跑批（`obs` 不在 PATH，但以 `python3 -m obs` 可用——**已有两批日志已由审计用 `llm-cost` 硬门禁验真 rc=0**，见本表下一行） |
| 新截图 | **无** | 预登记 C 路径条款写的是"**若有跑批**才需真截图"；本轮不跑批 ⇒ 不出图，**不伪造、不以示意图冒充实拍** |
| 已有日志真 LLM 验真 | **已硬验真** | **`obs llm-cost` 硬门禁 rc=0（审计于 22:1x 亲跑）**：A5 `by_provider={"openai_compat":2705}`、tokens `499,212`；D12-A `{"openai_compat":2252}`、tokens `304,871`；两批 `degraded=0`、`provider_guard.ok=true`。旁证：d5 `B-11_real_calls` / `B-19_provider_distribution` / `B-20_model_no_mock` / `B-12_degraded_ratio` 均 pass。⚠ **但 d5 准入仍 `REJECTED` / `evidence_level=probe`**（`B-7_files` 无 meta、`B-9_event_count` `meta.events=null`、`B-2b_manifest_effective`、`B-10_provider` 明细空 ⇒ 四项不过）——**"缺 meta"与"是否 mock"是两件事，不混写** |

### 4.2 F-6 `timeref_rate`（**信息性留痕，不是本轮结论，不可跨配置比较**）

| 批次 | 分子/分母 | 取值 | 口径限制 |
|---|---|---|---|
| A5（修复前，42 回合） | **52/523** | 9.943% | 另一臂（d2-prefer）、回合数与 v0/A0 不同 ⇒ **不与 6.4% 同口径**；**A5 同样无 `meta.json`（审计漏报 A）⇒ 该行同样是 `probe`** |
| D12-A（修复后，24 回合） | **18/191** | 9.424% | D12 具体性臂、F-6 注入臂 OFF、**无 meta** ⇒ `admission=REJECTED`，证据级 **`probe`** |

> 边界（必须与数字同表出现）：
> - **分子/分母怎么来的**：`tools/d5/dialogue_metrics.py` 只输出 `timeref_rate`（不打印分子分母），分子分母由 `verify_chain.py` 直接计数（D12-A `MSG 191` / 命中 `18`）与 rate `0.094241`（= 18/191）互证；A5 同法（`523` / `52`，`0.099426`）。
> - 两批**都不是 F-6 干预臂读数**（注入臂 OFF），配置也不同（回合数/其它臂不同），D12-A 且无 meta ⇒ **不得**把这两个数当作"固化修复改善/恶化 F-6"的证据，**也不得**与 R4 的 v0/A0 6.4% 直接比。
> - F-6 词表指标只测"**提到过去**"，**不测"引用是否正确"**（`reports/R4-life-texture.md:42,135`）。
> - 分母 191 < 68 门槛的那套纪律不适用（191 > 68），但**单批 + 非干预 + 无 meta** 三重限制已足以把这两行钉死在"信息性"层级。

---

## 5. 审计结论摘要

审计产出：`v2/evidence/f6_audit_20261022.md`（独立核验者 `evidence-auditor`，未参与 F-6 设计与实现，只读、未跑新批、未改代码）。

**审计总结论：有条件通过**——机制层读数可信（C1–C4 与实现者汇报**逐位一致**，脚本输出 `diff` 逐字节相同）；归因链**三条独立证据**成立；真 LLM 由审计 `obs llm-cost` **亲跑 rc=0** 验真；但措辞需三处收紧、两处漏报需补写。**上述收紧已全部落在本报告定稿文本里**（详见下表 G 列）。

### 5.1 审计逐项结果

| 项 | 审计结论 | 本报告处置 |
|---|---|---|
| 预登记先行 | **PASS**：预登记 mtime `22:06:47.126`，早于全部证据产出 ≥29 s；判据 + 决策规则 1–4 先写死；严格 grep 证明预登记**不含**任何事后读数（`sed 's/sha256//g'` 后零命中） | 已按此表述（§1.2） |
| 链条计数 C1–C4 | **PASS，逐位一致**；审计亲跑 `verify_chain.py` 与在库 `chain_out.txt` diff 相同 | 见 §2.2 |
| 分母口径 | C1 = `MEMORY_CONSOLIDATE` 事件数；C2 = **去重 `mem_id`**（非写入事件数）；C3 = `MEMORY_RETRIEVE` 事件数；C4 = `MSG_DM+PUBLIC+GROUP`（523 / 191） | 见 §2.2 §4.2 |
| 链内自洽（审计额外） | `produced_mem_id` 去重 **256 == SM `MEMORY_WRITE` 去重集**（双向差集空）；`selected(103) ⊆ written(256)`；SM 按 day **day0 243 / day1 13**（`slot=night`） | 已补入 §2.2 |
| 归因链 | **PASS（三条）**：① `merge-base --is-ancestor c01f6dd a6ae5e5`=True、`c01f6dd 51cdb07`=False；② **代码树级**：`51cdb07` 无 `_PASSTHROUGH["MEMORY_CONSOLIDATE"]`、`a6ae5e5:integration.py:211` 有；③ **批内行为签名**：`DROPPED[text]` 755→0 | 已补入 §2.1/§2.2 |
| 短 sha 可解析 | `git cat-file -t a6ae5e5` = commit，7 位无歧义 | — |
| 真 LLM 验真 | **PASS（审计亲跑）**：A5 `2705/2705`、D12-A `2252/2252`，`degraded=0`，tokens `499,212` / `304,871`，`provider_guard.ok=true`。**更正**：`obs` 不在 PATH 属实，但 `python3 -m obs` 可用 ⇒ 不得再写"靠日志字段自证" | **已改**（§4.1） |
| 三条"不可判"根因 | **PASS**：① `forgetting.py:177-179` 模板（D12-A `499/499` 命中"聚合"）；② `agent.py:62` `MEMORY_F6_TOP_N=2` + 桶序 `observation→other` + `break`；③ 臂 OFF ⇒ `_mem_refs=[]`、`ctx.memory_refs` 仅非空才写 payload | 见 §2.3 |
| 跨天资格 | **不是瓶颈**：day1 已有 243 个 day0 的 SM 满足 `node.day < today` | 已补入 §2.3 |
| `_readable` 门 | 审计独立复算 **480 pass / 19 reject（全 `MARKET`）**，逐位一致 | 见 §2.3 |
| 措辞证伪 | **未发现**"机制接通写成效果改善""管道活了写成 F-6 改善""用不可确证 sha 下强结论""作废 pilot 写成已验证" | — |
| R11 引用 | **准确无夸大**：F-6 `0.037255(19/510) → 0.111765(57/510)`（+7.45pp）、L-7 `0.354902 → 0.65098(332/510)`（+29.61pp，越 ≤+5pp 闸门） | 见 §3 理由 2 |
| N/A 项 | 本轮无新批 ⇒ `v2/evidence/f6_shots/` **不存在**，按规不判 FAIL，作废理由成立 | 见 §4.1 |

### 5.2 审计要求降级/收紧的断言（**已全部落定，无一条以原样保留**）

| # | 原断言 | 审计处置 | 本报告定稿写法 |
|---|---|---|---|
| G-1 | "obs 不在 PATH ⇒ 已有日志真 LLM 由日志字段自证" | **降级** | 「`obs` 以 `python3 -m obs` 可用；两批已由 `obs llm-cost` **rc=0 硬验真**（审计 22:1x 复跑）」 |
| G-2 | "固化链路当前**不会**对跨天记忆引用产生**实质贡献**" | **降级**（原为静态推断） | 「**按当前代码结构推断**（模板无信息 + `TOP_N=2` 桶序），固化链路**难以**产生实质贡献；**未实测**（臂 OFF、observation 可读性不可从日志复算）」 |
| G-3 | "SM 就**永远**排不进这 2 个槽位" | **降级** | 「**只要**每 agent ≥2 条可读 observation 就排不进（条件不可从日志复算，属静态推断）」 |
| G-4 | README §2 只标 D12-A 为 probe | **补漏** | A5 **同样无 meta** ⇒ 同为 `probe`；**机制层结论的证据等级本身也是 `probe`**（可信度来自代码归因 + 事件字段签名，不是准入等级） |
| G-5 | "此前 R18 只到夹具级" | **加限定**（防误解） | 「R18 的 A/B 是**进程内脚本夹具**（`v2/evidence/fix-sleep-consolidation-20261022/ab_rerun.log`），本轮是**首个真跑批日志证据**」 |

### 5.3 审计白名单（可进结论，须带限制语）

1. C1 `0/755` vs `499/499`；A5 `DROPPED[text]=755` vs D12-A `0`；C2 SM 去重 `256`（全 semantic）；C3 `656/672=97.62%` vs `368/384=95.83%`、SM 命中 `0` vs `103`；C4 `0/523`、`0/191`（均 `<unset>`）。
   **限制语**：A5 为修复前（`51cdb07`）、D12-A 为修复后（`a6ae5e5`）；**两批跨臂跨窗口（42 轮 vs 24 轮，A5 为 d2-prefer 臂），是机制"存在性"对比，不是 DiD/受控对照**；**两批均无 meta ⇒ `probe`**。
2. 链条自洽 `produced == written == 256`、`selected(103) ⊆ written(256)`：**审计额外交叉检查项**，非实现者原表内容。
3. 真 LLM：`openai_compat 2705/2705`、`2252/2252`、`degraded=0`、`tokens_total` `499,212` / `304,871`：来源 = **`obs llm-cost` rc=0**，原始输出 `v2/evidence/f6_chain_20261022/llmcost_a5.json` / `llmcost_d12a.json`（`provider_guard.ok=true`、`problems=[]`）；且 d5 `B-10_provider` 明细为空（缺 meta 所致）——**"缺 meta"与"是否 mock"是两件事，不混写**。
4. R11 对照（`+7.45pp` / L-7 `+29.61pp` 越闸）：**另一问题**，不得挪来当本轮固化链路结论。

### 5.4 只进缺口小节（**未进任何结论**）

- F-6 `timeref_rate`：A5 `52/523=9.943%`、D12-A `18/191=9.424%`（官方工具 + 词表 `9357b4c9…` 复算，与实现者逐位一致）⇒ **仅信息性**，注入臂 OFF、配置不同、无 meta，**不得跨批次或与 R4 的 6.4% 比较**（见 §4.2、§6.1 N-1）。
- 任何"SM 能否排进 2 个槽位"的**比例**：observation 可读性不可复算 ⇒ 只写代码事实，不写比例。
- `admission`：两批均 `REJECTED` / `evidence_level=probe`（`B-7_files`、`B-9_event_count`、`B-2b_manifest_effective`、`B-10_provider` 不过；**`B-11/B-19/B-20` 通过**）。
- `480/499` 过 `_readable`：只作**结构分析**，**不得**写成"SM 可注入率 96%"（静态可读性 ≠ 注入率）。
- ~~小瑕疵：`verify_chain.py` 的 `params=` 输出为 `None`~~ ⇒ **已由实现者在 22:13 版修复**：`chain_out.txt` 现正常输出 `params=seed=42 n=16 rounds=42 …`（`verify_chain.py` sha `5e69e7ec…`），该瑕疵**不影响任何判据数字**，已闭环。

---

## 6. 未达成 / 已知缺口（**不进结论**）

### 6.1 本轮未达成

| # | 未达成项 | 事实 | 证据 |
|---|---|---|---|
| N-1 | **F-6 行为层效果** | 未验证/不可判：修复后日志注入臂 OFF（`ctx.memory_refs` 0/191）；且即便打开，**按代码结构推断**（SM 内容为模板占位 + `TOP_N=2` 桶序把 semantic 挤后），固化链路**难以**产生实质贡献——**静态推断、未实测**（条件"每 agent ≥2 条可读 observation"不可从日志复算） | `v2/evidence/f6_chain_20261022/README.md` §3.2、§4；`v2/evidence/f6_audit_20261022.md` §5 |
| N-2 | **固化→对话引用的端到端真跑数字** | 未产出（预登记规则 3 不跑 pilot） | 同上 §4 |
| N-3 | **SM 摘要信息量** | `summarize()` 仍是确定性模板（`code/life/forgetting.py:177-179`），未改（改它属于新功能，需另开分支 + 预登记） | 代码 + `模板文本=499/499` |
| N-4 | **截图** | 本轮无新批 ⇒ 无图（按纪律写"无图 + 不伪造"，不以旧图/拼图替代） | 本报告 §4.1 |

### 6.2 证据台账缺口（`T-p0-ledger`，台账 `v2/evidence/evidence_ledger_20261022.md`，**只记 `probe`**）

**任务书列的 5 批**（报告落笔时刻实测 `test -f` 判否；台账 §1–§2 逐批复算）：

| # | 批次 | `meta.json` | `meta` 可否重建 | 处置 | 证据级 |
|---|---|---|---|---|---|
| 1 | `run_a5_real_n16r42_seed42` | **NO** | 部分可（`.worktrees/a2-prefer@51cdb07` 仍在）；`assertions.code_unchanged_during_run` **不可**（无起跑 porcelain 快照） | 不重建 ⇒ `probe` | `probe` |
| 2 | `run_a1budget_real_n16r42_seed42` | **NO** | 同上（同一 worktree） | 同上 | `probe` |
| 3 | `run_d12a_real_n16r24_seed42` | **NO** | 部分可（`.worktrees/d12-detail@a6ae5e5` 仍在） | 同上 | `probe` |
| 4 | `run_worldline_c1_ctrl_n16r84_seed42` | **NO** | 部分可，但 worktree **已删**，需先建 | 同上 | `probe` |
| 5 | `run_worldline_c1_a1_n16r84_seed42` | **NO** | **最全**（起跑 `git_status_start.txt` 在库） | 重建前仍 `probe` | `probe` |

> **关键判定（台账 §3–§4，决定"不能随手补 meta"）**：`tools/d2/emit_run_meta.py` 的 `code_sha` 取的是**执行时刻** `git rev-parse HEAD` ⇒ 在当前主树（`84ed6b1`）补 meta 会把 `84ed6b1` 写成跑批 `code_sha` = **伪造代码身份**，禁止（台账 §4-C）。且 S1 门禁要求 `code_unchanged_during_run == true`，而 a5/a1budget/d12a 三批**没有起跑 snapshot**、该字段只能为 `null` ⇒ **即使重建也升不到 `evidence` 级**。⇒ 本报告一律按 `probe` 处理。

**⚠ 缺口规模更正：不止 5 个批。** 台账 §5 全库扫描：`v2/evidence/*/run.jsonl` 且无 `meta.json` 命中 35 个目录，其中 mock 19、命名已作废 4（2×`*_INVALID_*` + `*_VOID` + `*_ABORTED_*`）、小样本 2，**剩余为真 LLM 缺 meta 10 个**；任务书只列 5 个，**另有 5 个漏报批次**（均由审计亲跑 `obs llm-cost` 验真）：

> **计数口径（作者实跑 + 审计复核，已对齐）**：`for d in v2/evidence/*/; ... done | wc -l`（排除 `mock_*` / `*_INVALID_*` / `*_VOID` / `*_ABORTED_*` / `run_baseline_*` / `run_d4_P2_*`）→ **10**。
> 账目：`35 = mock 19 + 命名作废 4（2×INVALID + VOID + ABORTED）+ 小样本 2 + 真 LLM 10`。
> 审计首版台账曾记 11（把 2 个小样本重复计入），已由审计在台账 §0 第 4 条 / §5 勘误更正为 **10** ⇒ 全文一律写 **10**，**不得写"仅 5 个"**。

| 补登批次 | rounds | `obs llm-cost` | 现有旁证 | 处置 |
|---|---|---|---|---|
| `run_a1wording_n16r42_seed42` | `0..33`（34 轮，合法不完整前缀） | rc=0，`openai_compat 2389/2389` | 仅 `README.md` | 永久 `probe`（只能按 34 轮窗口引用） |
| `run_g1_b0_n16r60_seed42` | 60 | rc=0，`2878/2878` | **仅 `run.jsonl`** | 不可重建 ⇒ 永久 `probe` |
| `run_l7struct_on_n16r60_seed42` | 60 | rc=0，`2878/2878` | `recompute_r17.txt` | 同上 |
| `run_l7v2_on_n16r60_seed42` | 60 | rc=0，`3042/3042` | `meta.derived.json`（先例，明示不得用于准入） | 同上 |
| `run_dr_round1_arm-ctrl_n16r60_seed42` | 60 | rc=0，`2878/2878` | **仅 `run.jsonl`** | 同上 |

> 口径：**不得写"仅 5 个批缺 meta"**，正确表述为 **10 个真 LLM 批缺 meta**（含任务书列的 5 批 + 审计补登的 5 批）。
> 缺 meta 的批次**只能记 `probe`**，不得作为 `evidence` 级引用进入结论。本报告 §2 的链条证明只读 `run.jsonl` 事件与字段，**不依赖 meta**，故不受此限；但 §4.2 的 F-6 率读数因此仍标 `probe`。

### 6.3 继承缺口（前轮未做，本轮未动）

| # | 缺口 | 事实 | 状态 |
|---|---|---|---|
| G-1 | **R19 人工 precision 未填 + 门槛未达（两件事，分开写）** | ① `v2/evidence/r19_topicbreadth_n8r24_seed42/precision_sample.md` 内 10 条 `judgement:` 仍全为 `【待人工填】`（`grep -c '待人工填'` → **10**）；② **即便填满**，`n=10 < 15` ⇒ 仍不能出 precision 结论，只能作 pilot 参考。另：`precision_sample.md` 写「N=10 ∈ [8,15) ⇒ 全量判（预注册 B.4）」与 `README.md` §5 / `readings.md` 写「≥15 才判」**口径冲突**，CYCLE-04 取了更严一侧（≥15）——该选择本身要保留原文，不得只写结论。③ **一处待修的不一致**：`reports/README.md:26` 已记「人工 precision **8/10 = 0.80**」，而证据文件 10 条判定全未填 ⇒ **该数字当前无证据支撑、不可复核**，本轮不动 R19 报告，仅在此登记待修 | 未做（**需未参与 R19 编码的真人**逐条判定；**AI 不得代填**，代填＝自证）。R19 效果结论保持「不可判」 |
| G-2 | F-2b 修尺口径未进 `reports/` 口径登记 | R19 只改实现与报告正文 | 未做 |
| G-3 | R19 报告值 ↔ 证据文件值逐行对账（state-survey P1-7 / G-5） | 未做 | 未做 |

---

### 6.4 措辞红线与口径更正（审计 §7 明确要求）

| # | 事项 | 正确写法 | 禁止写法 |
|---|---|---|---|
| R-1 | 跑批期间代码状态 | 「跑批窗口内 `code/` 四子树**无提交进入该跑批分支**（命令见 §7-8），但**起跑 porcelain 快照缺失 ⇒ 无法用工具口径证明工作树未被改动**」 | ❌「跑批期间代码未改动」 |
| R-2 | `duration_sec` | c1 两臂的 `[life] seconds`（3567.2769 / 3492.0673）为**实测**；其余 3 批为 **mtime 推导值，约 +19 s**（由 c1 两臂标定） | ❌ 把推导值与实测值混排、或去掉"推导"标注 |
| R-3 | 开关取值溯源自哪 | 「起批脚本`自述`（`switch_proof.txt`）」/「`env` 存在性断言 PASS」/「进程内 `PROC-ENV` 自证」三者**必须分清** | ❌ 统称"已证明开关正确" |
| R-4 | `run_d12a_real` 状态 | 「**已收尾**（33,824 行、`round 0..23` 连续、provider 全 `openai_compat`），但**仍缺 `meta.json` ⇒ 仍 `probe`**」 | ❌ 沿用 `reports/CYCLE-04-20261022.md:121` 的「进程存活 / 无任何可引用读数」（**该观察已过期**） |
| R-5 | `meta.derived.json` | 「派生文件，明示**不得**当作原版 `meta.json`、**不得**用于准入」 | ❌ 当作原版 meta 引用或据以通过 d5 准入 |
| R-6 | `run_worldline_c1` 两臂 | 「`LLM_CALL` 数/purposes/`cached` 完全相同（3403/1666），`events` 差 10（`MEMORY_FORGET`）、`tokens_in` 差 18,627 ⇒ 只说明**接线成立 + 内容有变**」 | ❌ 任何"世界线让记忆更…"的效果表述 |

> 可写入结论的白名单（台账 §7）：5 批的 `obs llm-cost` 读数（calls / provider 全 `openai_compat` / cached / `degraded=0` / tokens）、`events`、`seed=42`、`n=16`、`rounds`（42/42/24/84/84 均连续）、`run.jsonl` sha8（`aa6edc35`/`0bc80cd2`/`64f9da4b`/`4c840b5b`/`ac9fa312`）、`config_components` 12/12 与各批跑批 commit 一致。

## 7. 复算命令（任何人可重跑）

```bash
cd <repo-root>   # social-experiment

# 0) 取数时刻与仓库身份
date -Iseconds
git rev-parse HEAD && git rev-parse --abbrev-ref HEAD
git rev-list --left-right --count origin/master...master

# 1) 链条证明 C1–C4（只读，不跑批）
python3 v2/evidence/f6_chain_20261022/verify_chain.py | tee /tmp/chain_recheck.txt
diff /tmp/chain_recheck.txt v2/evidence/f6_chain_20261022/chain_out.txt && echo IDENTICAL

# 2) 两个批次是否在修复之后（决定它能证明什么）
git merge-base --is-ancestor c01f6dd 51cdb07 && echo "A5 修复后" || echo "A5 修复前"
git merge-base --is-ancestor c01f6dd a6ae5e5 && echo "D12A 修复后" || echo "D12A 修复前"

# 3) F-6 timeref_rate（dialogue_metrics 只输出 rate；分子/分母由 §7-1 的 verify_chain.py 打印）
python3 tools/d5/dialogue_metrics.py \
  --log v2/evidence/run_d12a_real_n16r24_seed42/run.jsonl \
  --timeref tools/d5/timeref_lexicon.txt \
  --out-json /tmp/d12a_metrics.json
python3 -c "import json;d=json.load(open('/tmp/d12a_metrics.json'));\
print('rate=',d['F-6_crossday_memory']['timeref_rate'],\
      'timeref_sha=',d['inputs']['f_lexicons']['timeref_sha'],\
      'admission=',d['admission']['verdict'],d['admission']['evidence_level'])"

# 4) meta 缺口现状（任务书 5 批应全为 NO）
for d in run_a5_real_n16r42_seed42 run_a1budget_real_n16r42_seed42 \
         run_worldline_c1_ctrl_n16r84_seed42 run_worldline_c1_a1_n16r84_seed42 \
         run_d12a_real_n16r24_seed42; do
  printf "%s: " "$d"; test -f "v2/evidence/$d/meta.json" && echo YES || echo NO
done

# 5) R19 人工 precision 缺口现状（应为 10）
grep -c '待人工填' v2/evidence/r19_topicbreadth_n8r24_seed42/precision_sample.md

# 6) 关键文件指纹
sha256sum v2/evidence/f6_prereg_20261022.md \
          v2/evidence/f6_chain_20261022/*.py \
          v2/evidence/f6_chain_20261022/chain_out.txt \
          v2/evidence/f6_chain_20261022/README.md \
          v2/evidence/evidence_ledger_20261022.md \
          tools/d5/timeref_lexicon.txt

# 7) 推送前确无在跑批次（本轮报告纪律）
pgrep -af "run_batch|hitt|orchestration|cli.py" || echo "NO_BATCH_RUNNING"

# 8) 各批真跑验真（rc=0；等价两种写法，任选其一）
(cd code && python3 -m obs llm-cost --log ../v2/evidence/run_d12a_real_n16r24_seed42/run.jsonl --require-provider openai_compat)
PYTHONPATH=code python3 -m obs.cli llm-cost --log v2/evidence/run_a5_real_n16r42_seed42/run.jsonl --require-provider openai_compat

# 9) 全库缺 meta 扫描（台账 §5 勘误后：真 LLM 缺 meta = **10 个**，不是 5 个）
for d in v2/evidence/*/; do [ -f "$d/run.jsonl" ] || continue; \
  [ -f "$d/meta.json" ] || echo "$d"; done | grep -v 'mock_\|_INVALID_\|_VOID\|_ABORTED_'

# 10) 预登记先行取证（审计 §1；mtime 口径）
stat -c '%n %y' v2/evidence/f6_prereg_20261022.md v2/evidence/f6_chain_20261022/*
sed 's/sha256//g' v2/evidence/f6_prereg_20261022.md | grep -n "499\|256\|103\|9\.943\|9\.424\|368/384\|480" || echo "预登记不含事后读数"

# 11) 归因链代码树级（审计 §3）
git merge-base --is-ancestor c01f6dd a6ae5e5 && echo "D12A 修复后"
git merge-base --is-ancestor c01f6dd 51cdb07 || echo "A5 修复前"
git show 51cdb07:code/orchestration/integration.py | grep -n MEMORY_CONSOLIDATE   # 无 _PASSTHROUGH 项
git show a6ae5e5:code/orchestration/integration.py | grep -n MEMORY_CONSOLIDATE   # 211: ("MEMORY_CONSOLIDATE": ("text",))
git cat-file -t a6ae5e5                                     # commit（短 sha 无歧义）

# 12) 跑批窗口内 code/ 四子树提交（用于 R-1 措辞：**无提交进入该跑批分支** ≠ 工作树未改动）
git log --all --since="2026-10-22T20:24:36+08:00" --until="2026-10-22T20:47:29+08:00" \
  --format='%h %ci %s' -- code/life code/orchestration code/config code/engine
```

**关键文件指纹（本次实测，填数即重算）：**

| 文件 | sha256 |
|---|---|
| `v2/evidence/f6_prereg_20261022.md` | `5c266083c5ac3e1a271149f819490ca536f68aab2114d247a7dc8a38f3b9e835` |
| `v2/evidence/f6_chain_20261022/verify_chain.py` | `393923f5619f697b896b3cde3c6b4bc09507bc2f3d3dad4f3620a79d6ff364af` |
| `v2/evidence/f6_chain_20261022/chain_out.txt` | `672e2eb070c6cf8d19e4ea60eb3a8af09428339852ac2d8671859bc5cf81968e` |
| `v2/evidence/f6_chain_20261022/README.md` | `7ceab36503607d568be4d9b6756e0714f6c3eed3895706ef00813c4299998c2e` |
| `v2/evidence/f6_chain_20261022/d12a_dialogue_metrics.json` | `c379953a1cc3956ced46c4bda09e0dc983ab7541eccdcc058d661296402a677b` |
| `v2/evidence/f6_chain_20261022/llmcost_a5.json` | `02f58d29c2f9560842ec3050d68e2f306c3c51cd1477157a13b40dde0faa1a85` |
| `v2/evidence/f6_chain_20261022/llmcost_d12a.json` | `dc4d7be2e86b0b856416e07e99d7ab5e58eb7932181fe496f43c360f0bc9676f` |
| `v2/evidence/f6_audit_20261022.md` | `649238566057a4f75002cd207cbca4a980676122a58b2eb2beebe144acda4e5b` |
| `v2/evidence/evidence_ledger_20261022.md` | `20077ca7a8d4efb8fddf357e344f2abd893d06448966a584ff8d39fa704e70a8` |
| `tools/d5/timeref_lexicon.txt`（11 项） | `9357b4c91aad8584e6d845e311eed289b1f58179ccbfdc3a49588641978b7d5d` |

> 指纹口径：以上为**报告定稿时刻（commit 前，22:15 版）**实测值。实现者于 22:13/22:15 按审计意见更新过 `verify_chain.py` / `chain_out.txt` / `README.md`（补 `llmcost_*.json`、修 `params=` 解析、并把两条推断措辞降级为「按代码结构推断、未实测」），**旧版 sha 已作废、勿引**；判据数字未变（`verify_chain.py` 重跑与 `chain_out.txt` diff **IDENTICAL**）。commit 后 `git log --format=%H -- <file>` 可定位同名文件所在提交。

---

## 8. 结论（分栏，禁止合并成一句）

**机制层（Q1）——已达成（存在性事实）**
`c01f6dd` 修复后，`MEMORY_CONSOLIDATE(落 text) → MEMORY_WRITE(SM) → MEMORY_RETRIEVE(选中 SM)` 三段在**真 LLM 日志**（D12-A，`code_sha a6ae5e5`，已由 `obs llm-cost` rc=0 验真）中确实活了：C1 `499/499`、C2 `256` 条 SM、C3 选中 SM `103`；修复前对照（A5，`51cdb07`）分别为 `0/755`、`0`、`0`。
**更硬的缺陷定性**：两批的固化**目标集合相同**（`produced_mem_id` 16×16 = **256**，双向差集为 0），但**落账结果不同**（A5 = 0 / D12-A = 256）⇒ 修复前不是"算不出固化组"，而是"**算出来了、透传与落账全丢**"。
这是**本轮新增的一条端到端日志证据**——R18 的 A/B 是**进程内脚本夹具**（`v2/evidence/fix-sleep-consolidation-20261022/ab_rerun.log`），本轮是**首个真跑批日志证据**。**但"管道活了"不等于"F-6 变好"**。

**本节证据等级 = `probe`**：A5 与 D12-A **两批均无 `meta.json`**（d5 `admission=REJECTED`），可信度来自**代码归因（§2.1 三条）+ 事件字段签名（DROPPED 755→0）**，**不是**准入等级；且两批跨臂跨窗口（42 轮 / d2-prefer vs 24 轮 / d12-detail）⇒ **是存在性对比，不是 DiD 受控对照**。

**行为层（Q2）——不可判 / 未验证**
修复后日志 F-6 注入臂 `LIFE_PROMPT_MEMORY_F6` 为 OFF（`ctx.memory_refs` `0/191`，**开关决定的 0，不是能力坏了**），且固化出的 SM 正文为确定性模板占位、注入排序中被 observation 桶挤后 ⇒ **按当前代码结构推断**（模板无信息 + `TOP_N=2` 桶序），固化链路**难以**对跨天记忆引用产生实质贡献——**这是静态推断，未实测**（臂 OFF、observation 可读性不可从日志复算）。
本轮**不作任何效果宣称**：不写"改善/修复/有效果"，不把 §4.2 的两个 `timeref_rate` 当 F-6 干预读数，不与 v0/A0 6.4% 比。

> 口径提示：本报告的"机制层 PASS"指 R18 修复的可观测性，与 R16/R19 的「尺子恢复可动 ≠ 提升」同族纪律——**它不构成生活气息改善的证据**。

---

## 9. 下轮建议（F-6 固化 → 对话引用）

前置条件（三条，**缺一即不可判**；来自 `T-f6-measure` 交接，仅陈述机制事实与前置，不含效果宣称）：

1. **有信息量的摘要**：`code/life/forgetting.py::summarize()` 现返回确定性模板「关于{subject}的印象（由{count}条经历聚合）」，须改为可引用的摘要（LLM 或抽取式，需另行立项 + 预登记）。否则注进去也只是"我对某人有印象"这种占位。
2. **注入排序承认 semantic 记忆**：`code/life/agent.py::_memory_line()` 先填 `observation` 桶（`MEMORY_F6_TOP_N=2`）再填 `other`，SM（`kind=semantic`）恒被挤掉（D12-A `day0` observation 写入 6125 条）；须为 SM 单开槽，或让排序承认 semantic。
3. **以 `ctx.memory_refs` 出现 `-SM-` 的 id 作注入面证据**：先证 SM 记忆真的被注入对话提示词（`ctx.memory_refs` 含 `M-*-SM-*`），再谈 F-6 率；**不得重演"用 timeref 词表命中冒充记忆引用"**。

其他建议：

4. **先清 P0 账**（零跑批成本、直接抬可信度）：给 §6.2 的批次补 `meta.json`（可重建则补，不可重建则明确作废登记），并把 R19 人工 precision 10 条填完（`n=10<15` ⇒ 只作 pilot 参考）。
5. **若要补 `meta.json`：必须按台账 §4 在对应 worktree 内重建，禁止在主树重建**——`tools/d2/emit_run_meta.py` 的 `code_sha` 取执行时刻 HEAD，在主树（`84ed6b1`）重建会把 `code_sha` 写成 `84ed6b1` = **伪造代码身份**；且 a5/a1budget/d12a 无起跑 porcelain 快照 ⇒ `code_unchanged_during_run` 只能 `null`，**重建也升不到 `evidence` 级**。拒绝一切手写 `meta` / 用 `meta.derived.json` 过准入的做法。
6. 与 **R11 的 F-6 臂区分**：R11 证的是"检索结果进提示词"的装配缺口（OFF→ON +7.45pp，但 L-7 +29.61pp 越闸、不构成净改善）；本轮问的是"**固化（SM）**记忆链路"。下轮设计须避免重复 R11。
7. 放量前核对：`git diff --stat -- code/` 为空、四子树指纹相同、`switch_proof.txt` 内 `env_dump` 开关取值，再跑 ≥ `n16×60` 的对照；单 seed 结果一律标「不外推」。

---

## 10. 证据索引

| # | 结论 | 层级 | 来源（文件名 + sha8） | sha256 / sha8 | 复现 |
|---|---|---|---|---|---|
| E1 | 预登记先于跑批/裁决（mtime 22:06:47，早于证据 ≥29 s） | 方法 | `v2/evidence/f6_prereg_20261022.md` | `5c266083…` | §7-10 |
| E2 | C1 `0/755` vs `499/499` | 机制 `probe` | `f6_chain_20261022/chain_out.txt` | `672e2eb0…` | §7-1 |
| E3 | C2 `0` vs `256`（全 semantic；`produced == written == 256`；day0 243 / day1 13） | 机制 `probe` | 同上 | `672e2eb0…` | §7-1 |
| E4 | C3 SM 命中 `0` vs `103`（`selected ⊆ written` 打印 True） | 机制 `probe` | 同上 | `672e2eb0…` | §7-1 |
| E5 | C4 注入面 `0/523`、`0/191`（臂 `<unset>`，开关决定） | 机制 `probe` | 同上 | `672e2eb0…` | §7-1 |
| E6 | DROPPED[text] `755 → 0`（修复因果签名） | 机制 `probe` | 同上 | `672e2eb0…` | §7-1 |
| E7 | SM 模板占位 `499/499`；过 `_readable` `480/499`（19 全 `MARKET`） | 机制 `probe` | 同上 + `code/life/forgetting.py:177-179`（源码随提交变动 ⇒ `sha8` = `TODO`） | — | §7-1 |
| E8 | F-6 `52/523`、`18/191`（**仅信息性**） | `probe` | `f6_chain_20261022/d12a_dialogue_metrics.json` | `c379953a…` | §7-3 |
| E9 | 真 LLM：`openai_compat 2705/2705`、`2252/2252`、`degraded=0` | 机制 `probe` | `f6_chain_20261022/llmcost_a5.json` / `llmcost_d12a.json` | `02f58d29…` / `dc4d7be2…` | §7-8 |
| E10 | 词表指纹 `9357b4c9…`（11 项） | 口径 | `tools/d5/timeref_lexicon.txt` | `9357b4c9…` | §7-6 |
| E11 | 5 批无 meta；**真 LLM 缺 meta 共 10 批**；`code_sha` 重建红线 | 缺口 | `v2/evidence/evidence_ledger_20261022.md` §0–§5 | `20077ca7…` | §7-4/§7-9 |
| E12 | R19 precision 10 条未填 **且** n=10<15 双重阻塞 | 缺口 | `v2/evidence/r19_topicbreadth_n8r24_seed42/precision_sample.md` | — | §7-5 |
| E13 | 5 批规模/身份：`seed=42`、`n=16`、`rounds` 42/42/24/84/84 连续、`run.jsonl` sha8、`config_components` 12/12 | 机制 `probe` | 台账 §2（`obs llm-cost` 逐批 rc=0） | `20077ca7…` | §7-8 |
| E14 | 审计结论「有条件通过」+ 5 条降级 + 白名单/缺口清单 | 审计 | `v2/evidence/f6_audit_20261022.md` | `64923856…` | §5 |
| E15 | 归因链三条（git 祖先 / 代码树 diff / 批内签名） | 机制 `probe` | `f6_audit_20261022.md` §3 + 本报告 §2.1 | `64923856…` | §7-11 |

> 源码类引用按报告族纪律写「臂 commit + 文件:行号」；`sha8` 列写 `TODO（源码随提交变动）`——本表 E7 即此例。
> 排除项（不进结论）：`run_d12a_base_seed7_n16r24_INVALID_confounded`、`run_d12a_treat_seed7_n16r24_INVALID_incomplete` 名字已自述作废，不作对照臂引用（台账 §5 附）。

---

## 11. 交付回执（commit + push 实跑输出）

**推送前纪律检查（实跑，2026-10-22T22:16 +08:00）**

```
$ pgrep -af "[r]un_batch|[h]itt|[o]rchestration run|[c]li.py run"
NO_BATCH_RUNNING            # 无在跑批次 ⇒ 允许 push
$ git status --short | grep -v '^??'
                            # 无已暂存/已修改但未提交的源码改动
```

**提交范围**（严格按任务书，未裹带别人的未跟踪产物 `code/frontend/sample/*`、`v2/evidence/r19_topicbreadth_pilot_*`、两个 `*_INVALID_*` 的 `switch_proof.txt`）：

| commit | 内容 |
|---|---|
| `ae863fc` | `reports/R20-f6-crossday-memory.md` + `reports/README.md` + `v2/evidence/f6_prereg_20261022.md` + `v2/evidence/f6_chain_20261022/`（6 文件）+ `v2/evidence/f6_audit_20261022.md` + `v2/evidence/evidence_ledger_20261022.md`，共 **11 files, +1292** |
| `810dc00` | 按审计/实现者只读复算补强 A5 缺陷定性（目标集合相同 256 / 落账 0 vs 256） |

**push 实跑输出**

```
$ git push origin master
To https://github.com/Elinpf/AI-social.git
   84ed6b1..810dc00  master -> master

$ git log -1 --format='%h %cI %s'
810dc00 2026-10-22T22:16:43+08:00 docs(R20): 补强 A5 缺陷定性——目标集合相同(256)、落账结果不同(0 vs 256)

$ git rev-list --left-right --count origin/master...master
0	0
```

⇒ **master 与 origin/master 齐平（`0 0`）**；交付 HEAD = `810dc0077bffe48f1a52daf34fd6355d35983cf6`；本报告取数时刻 HEAD 为 `84ed6b1`（§0），两者之差即本轮 R20 的交付提交（内容 `ae863fc` + 补强 `810dc00` + 本回执回填；回执回填只改本文档 §11，不改任何读数）。

> 未使用 `git push --force`；推送前已按 `.gitignore` 核对，**未提交任何 `run.jsonl` / 证据大文件 / 敏感内容**（提交文件最大 44K，全在 `reports/` 与 `v2/evidence/` 下）。
