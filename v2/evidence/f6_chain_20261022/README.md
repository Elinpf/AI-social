# F-6 跨天记忆引用 · 零-LLM 链条证明与 pilot 裁决（2026-10-22）

> 任务 `T-f6-measure`｜执行 `life-behavior-eng`｜仓库 `master` @ `84ed6b146a66a10b4409b08c7380b8fab8007d10`
> 本目录只读已有真 LLM 日志，**未跑新批**。所有数字均可用本目录 `verify_chain.py` 复算。
> 本轮**不 commit/push**（交付纪律：由报告专员统一交付）。

---

## 0. 一句话结论

- **机制层（Q1）**：`c01f6dd` 修复后，`MEMORY_CONSOLIDATE(落 text) → MEMORY_WRITE(SM) → MEMORY_RETRIEVE(选中 SM)` 三段**在真 LLM 日志里确实活了**（用修复后批次 D12-A 证明）。这是一条**新增的、此前 R18 只到夹具级**的端到端日志证据。
- **行为层（Q2）**：**不可判 / 未验证**。修复后日志里 F-6 注入臂 `LIFE_PROMPT_MEMORY_F6` 是 **OFF**（`ctx.memory_refs` 0/191），且**即便打开**，固化出的 SM 记忆正文是**确定性模板占位**、且在注入排序中被 observation 桶挤在后面 ⇒ **按当前代码结构推断（未实测：臂 OFF、observation 可读性不可从日志复算）**，固化链路当前不会对"跨天记忆引用"产生实质贡献。
- **pilot 裁决**：按预登记规则 3 **不跑** n8×16 pilot。理由见 §4。

---

## 1. 预登记

- 文件：`v2/evidence/f6_prereg_20261022.md`
- sha256：`5c266083c5ac3e1a271149f819490ca536f68aab2114d247a7dc8a38f3b9e835`
- 落盘**早于任何新跑批**（本轮未跑批）。起跑前 `pgrep -af "run_batch|hitt|orchestration|cli.py"` 仅命中 pgrep 自身 shell ⇒ 无并发批。

---

## 2. 两个日志的代码版本事实（决定它们能证明什么）

| 批次 | code_sha | 起跑 | 相对恢复 `c01f6dd`(18:20)/`cd8f024`(18:26) |
|---|---|---|---|
| A5 `run_a5_real_n16r42_seed42` | `51cdb07` | 2026-10-22 17:07 | **修复前**（`git merge-base --is-ancestor c01f6dd 51cdb07` → **False**） |
| D12-A `run_d12a_real_n16r24_seed42` | `a6ae5e5` | 2026-10-22 20:24 | **修复后**（`git merge-base --is-ancestor c01f6dd a6ae5e5` → **True**） |

> D12-A 起跑晚于修复合并（18:26），其 sha `a6ae5e5` 是 `c01f6dd` 的后代 ⇒ **它能证明修复后行为**。A5 只能当修复前对照。
> 注：**两批均无 `meta.json`**（`dialogue_metrics` 均 `admission=REJECTED`：B-7/B-9 因缺 meta、B-10 provider 明细为空）⇒ 凡引用 A5/D12-A 的任何读数（含 755/0、256、9.943%/9.424%）一律只作 **probe** 级留痕。但本链条证明**不依赖 meta**，只读事件与字段；**机制层结论的证据等级 = probe，其可信度来自「代码归因 + 事件字段签名」，而非准入等级**。

---

## 3. 链条复算结果（C1–C4）

复算命令（仓库根目录）：

```bash
python3 v2/evidence/f6_chain_20261022/verify_chain.py | tee v2/evidence/f6_chain_20261022/chain_out.txt
```

词表指纹：`tools/d5/timeref_lexicon.txt` sha256 = `9357b4c91aad8584e6d845e311eed289b1f58179ccbfdc3a49588641978b7d5d`（11 项）。

| 环 | 指标 | A5（修复前 `51cdb07`） | D12-A（修复后 `a6ae5e5`） | 判定 |
|---|---|---|---|---|
| **C1** CONSOLIDATE 落 text | `text` 非空比例 | **0/755 = 0.00%** | **499/499 = 100.00%** | 修复前 FAIL，修复后 **PASS** |
| **C2** SM 落账 | `MEMORY_WRITE` 中 `mem_id` 含 `-SM-` 的唯一条数 | **0** | **256（全 kind=semantic）** | 修复前 FAIL，修复后 **PASS** |
| **C3** 检索返回 | `MEMORY_RETRIEVE.selected_mem_ids` 非空；被选中 SM 唯一条数 | 656/672=97.62%；**SM 命中 0** | 368/384=95.83%；**SM 命中 103** | 修复后 **PASS**（含 SM） |
| **C4** 正文命中 | 对话 `ctx.memory_refs` 非空条数 | 0/523（臂 `<unset>`=OFF） | **0/191**（臂 `<unset>`=OFF） | **不可判**（注入臂未开） |

**旁证（直接复算）**：A5 的 `DROPPED[reason=unknown_intent_field, keys=('text',), type=MEMORY_CONSOLIDATE]` = **755**，与 `MEMORY_CONSOLIDATE` 数（755）**逐条相等** ⇒ 修复前每条固化的 `text` 都被丢；D12-A 同项 = **0**。这正是 `code/orchestration/integration.py:211` 的 `_PASSTHROUGH["MEMORY_CONSOLIDATE"]=("text",)` 生效的直接证据。

### 3.1 P@事件链是否自洽
- 修复后：`CONSOLIDATE 499（text 全非空）`、`SM WRITE 256（unique）`、`RETRIEVE 选中 SM 103` —— 数量级自洽（SM 唯一 id 256，被检索到的子集 103 不超 256）。
- 交叉检查（evidence-auditor 补；脚本已复算）：D12-A `CONSOLIDATE.produced_mem_id` 去重 = **256** = `MEMORY_WRITE(-SM-)` 去重（**两集合相等**）；被选中的 103 **⊆** 256。相对地，A5 `produced_mem_id` 去重也是 256，但 **SM WRITE 去重 = 0**（两集合不相等）—— 恰好刻出修复前"有 produced id、无真写入"的缺陷。
- SM 写入按 day（D12-A）：**day0 243 / day1 13** ⇒ day1 时有 **243** 个 SM 满足 `node.day < today`，**"跨天资格"不是瓶颈**（瓶颈在 §3.2 的"内容 + 排序"两条，勿误读为"回合太少"）。
- 修复前：`CONSOLIDATE 755 全部 text=None`、`SM WRITE 0`、`选中 SM 0` —— 与 R10/R18 记录的 `discard_rate=100%`、`SM_write_count=0` 一致，互为印证。

### 3.2 C4 为什么"不可判"而不是"FAIL"——注入路径结构分析
F-6 注入臂开关 `LIFE_PROMPT_MEMORY_F6`（`code/life/agent.py:60`）**默认 OFF**；`_memory_line()`（`agent.py:1195-1297`）在 OFF 时返回空串、`self._mem_refs=[]` ⇒ `ctx.memory_refs` 不出现。两批 `switch_proof.txt` 均无该 env（`<unset>`），故 C4 注入面为 0 是**开关决定的**，不能据此说"记忆没进提示词"这个能力坏了。

但**即使把臂打开**，固化 SM 记忆当前也很难进提示词，两条结构性理由（可读代码事实；属**静态推断**）：
1. **SM 正文是确定性模板，不含真实内容**：`code/life/forgetting.py:177-179` `summarize()` 返回 `"关于{subject}的印象（由{count}条经历聚合）"`；D12-A 实测 499/499 条 `text` 正是该模板。即"text 落账"修复的是**可观测性**（字段不再被丢），不是**信息量**——注进去也只是"我对某人有印象"这种占位，无法承载具体旧事。
2. **注入排序把 SM 挤在后面**：`_memory_line` 先填 `observation` 桶（`MEMORY_F6_TOP_N=2`），填满即止；`semantic`（SM 的 kind）属 `other` 桶。D12-A 的 `day0` observation 写入达 **6125 条**（16 人，每人约 383 条）⇒ **只要**每个 agent 在跨天时有 ≥2 条可读 observation，SM 就排不进这 2 个槽位（该条"≥2 可读 observation"条件**无法从日志复算**，属静态推断）。
   - 附：SM 模板文本过 `_readable` 门（Pxxx→显示名替换后）为 **480/499**；被拒的 19 条全是 `subject=MARKET`（含大写 ASCII）。也就是说"能不能过门"不是主要问题，**"排不排得上"和"有没有内容"才是**。

---

## 4. pilot 裁决：不跑（附依据与可接受的替代产出）

预登记规则 3 原文：「若 C1–C3 全 PASS 但 C4 不成立 ⇒ **不跑 pilot**（跑了也不会有 SM 的 F-6 读数，属'为凑结论跑小样本'）。」现况正是如此，理由叠加：

1. **C4 路径对 SM 不成立**（§3.2）：n8×16 无论开关 ON/OFF，都无法产出"SM 固化记忆被对话引用"的可判读数。
   - 若 OFF：`ctx.memory_refs` 恒 0，对话提示词不碰记忆 —— 与 F-6 率无关。
   - 若 ON：注入的是 observation（有真实内容）而非 SM，测到的是**旧 F-6 臂**，不是固化链路。
2. **F-6 臂 ON/OFF 已有正式读数**：`reports/R11-f6-memory-into-dialogue.md`（n16×60 seed42）已给出 OFF `19/510` → ON `57/510`（+7.45pp），但 **L-7 同步恶化 +29.61pp 越过预注册闸门 ⇒ 不构成净改善**。再跑一个更小的 n8×16 只是**重复 R11 的臂且样本更薄**。
3. **样本/机会偏薄（但非主因）**：`ROUNDS_PER_SLOT=3 × SLOTS_PER_DAY=4 = 12 回合/天`；n8×16 = 1 天 + 4 回合，day1 的对话回合少 ⇒ 即便链路通，"可产 F-6 引用"的**对话机会**也偏少。**注意**：跨天**资格**本身不是瓶颈——D12-A 在 day1 已有 **243** 个 SM 满足 `node.day < today`；真正卡住的是 §3.2 的"内容（模板占位）+ 排序（被 observation 挤）"。故此条**不单独**作为不跑的理由，主因是 §4.1/4.2 与下面第 2、4 条。
4. **成本纪律**：单批真 LLM（n16×24 的 D12-A 已 2252 次调用/约 23 分钟）虽不高，但**花在这三个已被排除的方向上换不到可判读数**，属无谓成本。

**因此本轮交付"机制层证据 + 行为效果未验证"，这是本项目接受的合格产出（不可判 优于 假结论）。**

> 若未来要做真正的"固化→对话引用"，前置条件（建议，不在本轮实施）：① `summarize()` 产**有信息量的摘要**（LLM 或抽取式，需另行立项/预登记）；② 注入排序承认 `semantic` 记忆（或为 SM 单独开槽），否则只要 observation 桶够填 2 槽 SM 就排不上；③ 用 `ctx.memory_refs` 里出现 `-SM-` 的 id 作注入面证据，再谈 F-6 率。

---

## 5. F-6 timeref_rate（仅信息性，**不是本轮结论，不可跨配置比较**）

| 批次 | F-6 `timeref_rate` | 说明 |
|---|---|---|
| A5（修复前，42 回合） | 52/523 = **9.943%** | 42 回合窗口，另一臂（d2-prefer），**无 meta ⇒ probe**，**不与 v0/A0 6.4% 同口径** |
| D12-A（修复后，24 回合） | 18/191 = **9.424%** | D12 具体性臂、F-6 注入臂 OFF、**无 meta ⇒ probe**（`admission=REJECTED`） |

> **两批均无 meta、F-6 率均只作 `probe` 留痕；也都不是 F-6 干预臂读数**：注入臂 OFF，配置也不同（回合数/其它臂不同）。按纪律，**不得**把这两个数当作"固化修复改善/恶化 F-6"的证据，也不得与 R4 的 v0/A0 6.4% 直接比。仅作"这两批日志各自的正文时间回指水平"留痕。
> 复算：`python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_d12a_real_n16r24_seed42/run.jsonl --timeref tools/d5/timeref_lexicon.txt --out-json v2/evidence/f6_chain_20261022/d12a_dialogue_metrics.json`（F-6 分子分母见 `F-6_crossday_memory.timeref_rate`；完整 JSON 见本目录 `d12a_dialogue_metrics.json`）。

---

## 6. 真 LLM 验真（已有日志，非新批）

- **已由 `obs llm-cost` 硬验真**（命令 `PYTHONPATH=code python3 -m obs.cli llm-cost --log <run.jsonl> --require-provider openai_compat`，两批 **rc=0**、`provider_guard.ok=true`、`problems=[]`）：
  - A5：`by_provider={openai_compat:2705}`、`calls=2705`、`degraded=0`、`tokens_total=499212`。
  - D12-A：`by_provider={openai_compat:2252}`、`calls=2252`、`degraded=0`、`tokens_total=304871`。
  - 原始输出见本目录 `llmcost_a5.json` / `llmcost_d12a.json`。
- 交叉：两批全部 `LLM_CALL` 的 `provider` 均为 `openai_compat`、`model` 均为 `DeepSeek-Flash`；`dialogue_metrics` 准入对 D12-A 的 `B-11/B-19/B-20` 全 pass ⇒ **非 mock**。
- 说明：`obs` 未装到 PATH，但 `python3 -m obs.cli`（`PYTHONPATH=code`）可用；本审计复跑亦 rc=0。本轮**未跑新批**，故无新批需验真。

---

## 7. 截图

本轮**未跑新批**，按预登记 C 路径条款（"若有跑批"才需真截图）**不产出新截图**；不伪造、不以示意图冒充实拍。若后续开"固化→对话"真实链路批，再走 `code/frontend/tools/dialogue_shots.sh` 出图并存 `v2/evidence/f6_shots/`。

---

## 8. 产物清单（本目录）

| 文件 | 作用 |
|---|---|
| `../f6_prereg_20261022.md` | 预登记（判据/成本上限/作废条件/决策规则） |
| `verify_chain.py` | 链条证明复算脚本（只读，不跑批） |
| `chain_out.txt` | 脚本输出（A5 vs D12-A 逐项读数） |
| `d12a_dialogue_metrics.json` | D12-A 的 `dialogue_metrics` 完整输出（含 F-6 分子分母） |
| `llmcost_a5.json` / `llmcost_d12a.json` | 两批 `obs llm-cost` 原始输出（provider_guard.ok 硬验真） |
| `README.md` | 本文件：结论 + 依据 + 复算命令 |
