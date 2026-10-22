# R18 · 睡眠—固化链路：两条「观测断点」的修复（固化摘要落账 + 睡眠收尾漂移快照）

> **本轮维度**：R10 遗留缺陷 ①「`MEMORY_CONSOLIDATE` 的 `text` 100% 被丢弃 ⇒ SM 语义记忆写入 0」+ ②「`SLEEP_COMPLETED` 的 `pf0/pf_t/drift_permille` 恒 null」。
> **性质**：修的是**观测与落账链路**，不是新玩法；产出是「过日子」这条生活气息主线的**度量地基**（睡一觉之后把经历沉淀成一条有正文的语义记忆、性格漂移有快照可查）。
> **纪律前提**：本轮**未起任何新跑批**（当时 PID 1172001 真批在跑，且 Leader 明令禁跑批/含 mock）⇒ **端到端「修后」数字一律标「未做」**，只给进程内 A/B 与静态/离线复算；下一轮复跑命令写全在 §8。
> **证据目录**：`v2/evidence/fix-sleep-consolidation-20261022/`（本报告每个数字都能由其中脚本/命令复算）。

---

## 0. 摘要（TL;DR）

| # | 结论 | 层级 | 证据 |
|---|---|---|---|
| 1 | 修前：三份已收批日志里，**固化摘要丢弃数 == 固化数（100.00%）**，SM 语义记忆 `MEMORY_WRITE` **0 条**，`SLEEP_COMPLETED` 漂移字段 **null 100%**（a5 48/48、worldline 各 112/112） | 已证实（计数） | §3、`r10_defect_baseline.out` |
| 2 | 与「只补 passthrough」不同：SM 记忆修前**根本没有 `MEMORY_WRITE` 事件、没有正文**——所以本轮同时补了「先写记忆、再固化」的落账顺序 | 已证实（代码 + 事件） | §2.2、§5 A/B |
| 3 | 修后（进程内真实 agent→intent→账本路径，零 LLM）：`text` 进入 `MEMORY_CONSOLIDATE` payload、`DROPPED{unknown_intent_field,keys=["text"]}` **1→0**、SM `MEMORY_WRITE` **0→1** 且正文与摘要逐字一致、`SLEEP_COMPLETED` 三字段非 null | 已证实（A/B 同脚本同输入） | §5、`verify_before.out` vs `verify_after.out` |
| 4 | 回归：`make code-test` **703 passed**（含新增 2 条）；新增用例单独跑 2 passed | 已证实（测试） | `code_test_full.out`、`pytest_new_test.out` |
| 5 | 端到端「一段真跑批上的丢弃数→0、SM 写入 ≥755/≥1779」 | **未做（本轮禁跑批）** | §8 复跑命令 |

---

## 1. 本轮维度与为什么选它

### 1.1 选择理由

**【判断】** 选 **R10「睡眠—固化」两条链路缺陷**（候选 1），四条依据：

1. **缺陷在本轮起点 `46e4380` 上仍然活着**：`_PASSTHROUGH` 无 `MEMORY_CONSOLIDATE`、`sleep_end` intent 只带 `day/slot/actual_ticks`——并且**能用硬盘上现成的已收批日志证明**（§3：a5 755/755、worldline 1779/1779 全丢），不依赖任何新跑。
2. **判据是整数计数**（丢弃 0 / SM 写入 >0 / drift null 0），不依赖 bootstrap 噪声带，天然绕开本族反复抱怨的「口径冲突 / 带未估」。
3. **它是生活气息主张的度量地基**：R10 这条链路对应「夜里沉淀、第二天还记得、性格被日子磨得有点不一样」。持续化产出被丢弃、睡眠收尾没有漂移快照 ⇒ 这条主张**结构性不可评估**。
4. **改动面小、可分离**：三处代码点（passthrough 白名单 / 固化落账顺序 / sleep_end payload），加一条 `commit_write` 的数字尾段容错。

### 1.2 为什么不是其他候选（scout 基线 §6）

| 候选 | 不选的理由 |
|---|---|
| 候选 2（补 `meta.json`） | 纯尺子修复，不推进「生活气息」本身；且属数据补齐，不应占用本轮唯一维度 |
| 候选 3（F-3 情绪呼应扩样） | 需新跑批（本轮禁），且 R14 已证该臂击穿 L-7 守卫 ⇒ 即便扩样大概率仍判「不可判」 |
| 候选 4（世界剂量/影响面） | `code/engine/` 冻结区 + 「世界事件对对话零暴露」这条更硬的阻断未解，修完也测不到生活气息 |
| 候选 5（A5 第 4 类配额） | 直接踩正在跑的 `a2-prefer` worktree/分支 |

---

## 2. 机制事实：断点在哪、为什么「只补 passthrough」不够

### 2.1 断点①：`text` 不在透传白名单 ⇒ 每条固化都落一条 DROPPED

| 位置（修前 `46e4380`） | 事实 |
|---|---|
| `code/orchestration/integration.py:205` `_PASSTHROUGH` | 只有 `MEMORY_RETRIEVE / MEMORY_REFLECT / OFFER_CREATED`，**没有 `MEMORY_CONSOLIDATE`** |
| `code/orchestration/integration.py:583-587` | `MEMORY_CONSOLIDATE` 的 base payload 只含 `agent_id/subject/source_mem_ids/produced_mem_id/day/slot` |
| `code/life/agent.py:1467`（修前） | 提交方确实带了 `"text": g["text"]` |
| 结果 | 每次固化 → `DROPPED{reason:"unknown_intent_field", type:"MEMORY_CONSOLIDATE", keys:["text"]}`，且**固化摘要正文在日志侧不存在** |

### 2.2 断点①的更深一层：SM 记忆根本没有写入事件（本轮新查明的关键事实）

**【事实】** 修前 `replay._apply_memory_consolidate` 只往 `state.memory_index` 塞一条 `body_ref = side://mem/<agent>/<pid>.txt` 的索引，而**没有任何代码把正文写到那个路径**，也不发 `MEMORY_WRITE`。于是：
- 账本侧 `MEMORY_WRITE` 中 `mem_id` 含 `-SM-` 的条数 = **0**（§3 表）；
- life 侧读该记忆时 `read_body` 因文件不存在按 T288 降级成空正文。

⇒ **只加 passthrough 只能让摘要「可见」，不能让记忆「可读」**。因此本轮把固化改成**先 `MEMORY_WRITE`（正文写 side 存储）→ 再 `MEMORY_CONSOLIDATE`**（顺序不可颠倒：`_do_memory(write)` 对已存在 `mem_id` 拒绝写入，append-only L5）。

### 2.3 断点②：`sleep_end` 不带人格指纹/漂移 ⇒ `SLEEP_COMPLETED` 三字段恒 null

| 位置（修前） | 事实 |
|---|---|
| `code/life/agent.py:1481-1482`（修前） | `{"op":"sleep_end","day":day,"slot":slot,"actual_ticks":planned}`——**没有** `pf0/pf_t/drift_permille` |
| `code/orchestration/integration.py:559-564` | 装配侧**本来就支持**这三个字段（`p.get(...)`），只是上游没给 |
| 结果 | `SLEEP_COMPLETED` 三字段恒 null；而同一睡眠窗的 `PERSONA_DRIFT` 事件里是有值的（R10 §5.3 已实测） |

---

## 3. 修前基线（已收批日志，只读复算，**100.00% 而非 50.00%**）

命令（仓库根，权威版；脚本已按 JSON 顶层 `type` 计数改写，**无任何子串匹配**）：

```bash
bash v2/evidence/fix-sleep-consolidation-20261022/r10_defect_baseline.sh
```

原样输出（`r10_defect_baseline.out`，2026-10-22T18:19:52+08:00，repo HEAD=46e4380）：

| batch | consolidate_count | discard_count | discard_rate | sm_should_count | SM_write_count | drift_null/null_total | events |
|---|---|---|---|---|---|---|---|
| `run_worldline_c1_ctrl_n16r84_seed42` | 1779 | 1779 | **100.00%** | 1779 | **0** | **112/112** | 194057 |
| `run_worldline_c1_a1_n16r84_seed42` | 1779 | 1779 | **100.00%** | 1779 | **0** | **112/112** | 194047 |
| `run_a5_real_n16r42_seed42` | 755 | 755 | **100.00%** | 755 | **0** | **48/48** | 62027 |

- 交叉核验：`v2/evidence/fix-sleep-consolidation-20261022/r10_defect_baseline_fixed.py`（本成员独立写的第二实现，同样 `json.loads` 取顶层 `type`）结果一致。
- 日志完整性旁证：ctrl 批 `events=194057` 与 `reports/CYCLE-03-20261022.md §2.6` 的 `B-17_hash_chain.n` 一致。
- **口径勘误交代（一句话）**：团队内部 v1 基线曾按子串计数得出 `1510/3558` 与 `50.00%`，因 `DROPPED` 的 payload 里含同样字符串而重复计数，已作废；本报告只用 v2（JSON 顶层 `type`）口径。

---

## 4. 改动清单

| 文件 | 要点 | 行数变化 |
|---|---|---|
| `code/orchestration/integration.py` | `_PASSTHROUGH` 增 `"MEMORY_CONSOLIDATE": ("text",)` | +4 |
| `code/life/agent.py` | ① 固化循环：先 `MEMORY_WRITE`（`kind="semantic"`、正文写 side 存储、`refs=source_mem_ids`）再 `MEMORY_CONSOLIDATE`；② `sleep_end` intent 带 `out["persona"]` 的 `pf0/pf_t/drift_permille` | +19/−1 |
| `code/life/memory.py` | `commit_write` 的 `_next_seq` 推进改为「尾段是数字才推进」（`M-xxx-SM-<subject>` 尾段是 subject），与 `sync_from_refs` 同口径 | +4/−1 |
| `code/tests/test_sleep_consolidation_obs.py` | 新增 2 条回归（事件层判据，零 LLM） | 新文件 |
| `tools/f2/verify_sleep_consolidation.py` | 离线 A/B 复跑脚本（agent→intent→账本，零 LLM） | 新文件 |

`git diff` 全文：`v2/evidence/fix-sleep-consolidation-20261022/git_diff.txt`。

**已知副作用（必须一起读）**：新增的 `MEMORY_WRITE` 会改变同一参数批的事件序列与条数 ⇒ 与历史批**不能逐事件对齐**；`code/obs/golden_baseline.json` 未改动（本轮不动冻结基线）。连续多天同一 `subject` 的固化，第二次起 `MEMORY_WRITE` 会被 append-only 拒绝（这是既有 L5 语义，未改）。

---

## 5. 修前 / 修后证据（进程内 A/B，**零 LLM**）

### 5.1 为什么零 LLM 也能证明链路修好

判据落在**事件层**，且走的是真实 `LifeLayerAgent._maybe_sleep_window(wv)` → `KernelAdapter.submit_intent` → 裁决器 → `engine.ledger.records` 的**同一条生产路径**（不是手搓 payload）：

- 修前应看到：`MEMORY_CONSOLIDATE` payload **无** `text`；`DROPPED{unknown_intent_field, type=MEMORY_CONSOLIDATE, keys=["text"]}` = 1；SM `MEMORY_WRITE` = 0；`SLEEP_COMPLETED` 三字段 null。
- 修后应看到：payload **有** `text`；DROPPED = 0；SM `MEMORY_WRITE` = 1 且正文 == 摘要；三字段非 null。
- 整条链路不涉及任何 LLM 决策调用（`sleep_window` 本身纯整数、无 LLM；`_readable`/prompt 无关）。

### 5.2 A/B 时序与代码身份（**基线树与分支树物理隔离**）

`v2/evidence/fix-sleep-consolidation-20261022/ab_rerun.log` 原文要点：

```
run_at_start=2026-10-22T18:20:16+08:00 | epoch=1792664416.067003118

== BEFORE（基线树 = git archive 46e4380 解出到 /tmp/r10-before-tree）==
baseline_sha=46e43808f28a891c26234703a48440bd0ceb9d4a
主树 46e4380:code/life/agent.py sha256 = 221e9f61c035a40de6f819dc3c8bc6e453b77f1455fc732f1ee1693728adf092
基线树 code/life/agent.py sha256        = 221e9f61c035a40de6f819dc3c8bc6e453b77f1455fc732f1ee1693728adf092
主树 46e4380:code/orchestration/integration.py sha256 = de496dd32dfb76c2d155d594b7f72db2ac90c8815b35d981d54a1a0b3f351d6f
基线树 code/orchestration/integration.py sha256       = de496dd32dfb76c2d155d594b7f72db2ac90c8815b35d981d54a1a0b3f351d6f
cmd: cd /tmp/r10-before-tree/code && PYTHONPATH=. python3 <repo>/tools/f2/verify_sleep_consolidation.py
start=2026-10-22T18:20:16+08:00 | epoch=1792664416.082640074
rc=1
end=2026-10-22T18:20:16+08:00 | epoch=1792664416.281374651

== AFTER（分支工作树，HEAD 如下）==
after_head=c01f6dd278cae3d6109f4dee154fa49bd208676b
after_branch=feat/life-memory-fix-20261022
cmd: cd <repo>/code && PYTHONPATH=. python3 ../tools/f2/verify_sleep_consolidation.py
start=2026-10-22T18:20:16+08:00 | epoch=1792664416.289581712
rc=0
end=2026-10-22T18:20:16+08:00 | epoch=1792664416.488382243
```

- **时序**：BEFORE `…416.08→416.28`，AFTER `…416.29→416.49`，AFTER 严格在后；两次各约 0.2s（与 .out 文件 mtime `18:20:16.255` / `18:20:16.465` 一致）。
- **代码身份**：基线树与 `git show 46e4380:<file>` 的 sha256 **逐位相同**；AFTER 的 HEAD = `c01f6dd`（§9）。
- 说明：基线树用 `git archive 46e4380 | tar -x` 解到 `/tmp/r10-before-tree`（不在主树 stash 来回切、不污染工作区/指纹）。

### 5.3 原始输出

BEFORE（`verify_before.out`，rc=1，stderr：`[FAIL] MEMORY_CONSOLIDATE payload 缺 text；…；未产出 SM 语义记忆的 MEMORY_WRITE（SM 写入=0）；…；SLEEP_COMPLETED.drift_permille 为 null`）：

```json
{
  "agent": "P001",
  "dropped_unknown_intent_field": [{"keys": ["text"], "type": "MEMORY_CONSOLIDATE"}],
  "intents_submitted": 1,
  "memory_consolidate": {"n_events": 1, "has_text": false, "text": null,
                          "produced_mem_id": "M-P001-SM-MARKET"},
  "sleep_completed": {"n_events": 1, "pf0": null, "pf_t": null, "drift_permille": null},
  "sm_memory_write": {"body_ref": null, "body_text": null,
                       "body_text_matches_summary": false, "mem_id": null, "n_events": 0}
}
```

AFTER（`verify_after.out`，rc=0，`[PASS] text 到达 MEMORY_CONSOLIDATE payload、SM 记忆有可读正文、漂移三字段到达 SLEEP_COMPLETED、无 MEMORY_CONSOLIDATE 的 unknown_intent_field`）：

```json
{
  "agent": "P001",
  "dropped_unknown_intent_field": [],
  "intents_submitted": 2,
  "memory_consolidate": {"n_events": 1, "has_text": true,
                          "text": "关于MARKET的印象（由4条经历聚合）",
                          "produced_mem_id": "M-P001-SM-MARKET"},
  "sleep_completed": {"n_events": 1,
                       "pf0": "0fd62513d08c4f6dcba7dc4769eed553ac4d8fec7a97e19c755dba674519ea78",
                       "pf_t": "c74d29bf72d998757629d5a6ef51b50990a2b1c49b621ba280bd7f446b619fe0",
                       "drift_permille": 0},
  "sm_memory_write": {"body_ref": "side://mem/P001/M-P001-SM-MARKET.txt",
                       "body_text": "关于MARKET的印象（由4条经历聚合）",
                       "body_text_matches_summary": true,
                       "mem_id": "M-P001-SM-MARKET", "n_events": 1}
}
```

> `drift_permille=0` 是**正确值不是缺失**：夹具没有触发反思型漂移候选，`pf0/pf_t` 非 null 已证快照到位；判据是「非 null」，不是「>0」。

### 5.4 pytest

```
$ cd code && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_sleep_consolidation_obs.py
..                                                                       [100%]
2 passed in 0.17s          # rc=0   → pytest_new_test.out
```

全量门禁：`make code-test` → **703 passed in 258.12s**，rc=0（`code_test_full.out`）。

---

## 6. 真跑验真（llm-cost，仅对基线批）

本轮没有新批，因此该命令用于证明**基线批是真 LLM 产出**（它不是本轮证据，是修前基线的合法性依据）：

```bash
cd code && python3 -m obs llm-cost --log ../v2/evidence/run_a5_real_n16r42_seed42/run.jsonl --require-provider openai_compat
# rc=0
```

原样输出要点（`llmcost_baseline_a5.txt`）：

- `by_provider: {"openai_compat": 2705}`，`provider_guard: {"expected":"openai_compat","ok":true,"problems":[]}`
- `total: calls=2705, cached=1406, degraded=0, thinking=497, tokens_in=285864, tokens_out=213348, tokens_total=499212`
- `by_purpose`: dialogue 523 / importance 1523 / judge 497 / reflect 112 / negotiation 34 / plan 16

口径声明：
- **硬证据**是 `provider_guard.ok=true` + `rc=0` + `calls=2705`（与日志里 `LLM_CALL` 事件数一一对应，验收员独立复算同值）。
- `cached=1406` 意味着约一半调用由冻结缓存命中；「真生成约 1299 次」是**由 cached 推算的推断**，不作为实测数字。
- 本轮**没有**新批，故不存在「本轮调用次数/成本」可报；下一轮复跑时会给出新批 llm-cost 原文与 cached/degraded 说明。

---

## 7. 截图（1 组 4 张，**修前对照**，三重标注）

| 文件（`v2/evidence/fix-sleep-consolidation-20261022/shots/`） | 视图 | 尺寸 |
|---|---|---|
| `run_a5_real_n16r42_seed42-chat-aa6edc35.png` | 对话流 | 1400×900 |
| `run_a5_real_n16r42_seed42-rhythm-aa6edc35.png` | 节律·串门 | 1300×1050 |
| `run_a5_real_n16r42_seed42-spread-aa6edc35.png` | 闲话怎么传开 | 1300×900 |
| `run_a5_real_n16r42_seed42-600-aa6edc35.png` | 600px 判读 | 600×900 |

**三重标注**（同 `shots/README.md`）：
1. **图源** = `v2/evidence/run_a5_real_n16r42_seed42`（master `46e4380` 时代产出，17:44 收批；日志 sha256 `aa6edc351cef…`）；
2. **非本轮修后行为**（本轮未起新批）；
3. **仅作修前对照**——用来看被修链路所依附的世界长什么样，不是效果证据。

**渲染时刻** 18:10（文件 mtime 可核）≠ **数据产生时刻**（该批运行期）。渲染原始输出 `shots/render.log`（4 次 `SHOT OK`，含亮度/彩色占比）；`threads.json` 落 `code/frontend/sample/dialogue_run_a5_real_n16r42_seed42/`。

---

## 8. 未做项与下一轮复跑命令（端到端修后）

**未做（明确）**：在真跑批上验证「丢弃→0 / SM 写入 ≥1779（a5 按 ≥755）/ drift null 0/112」。原因：本轮 18:04:18 起 PID 1172001 真批在跑，Leader 明令**本轮禁跑批（含 mock）**，串行纪律不允许并行起批。

下一轮可直接照跑（kubectl 无关，纯本地；预计 n16×24 ≈ 25–40 分钟，取决于 LLM 延迟）：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
# 前置：pgrep -af "run_override|run_batch" 必须为空（串行纪律）
git checkout feat/life-memory-fix-20261022    # 或已合入的 master
bash tools/d2/run_batch.sh \
  --out-dir v2/evidence/run_r18_sleep_fix_n16r24_seed42 \
  --seed 42 --agents 16 --rounds 24 --side-root /tmp/r18_sleep_side
# ↑ 自动产 meta.json + 跑 obs llm-cost 真跑门禁（rc=6 表示非真跑）
bash v2/evidence/fix-sleep-consolidation-20261022/r10_defect_baseline.sh \
  v2/evidence/run_r18_sleep_fix_n16r24_seed42
# 判据：discard_count=0；SM_write_count>0（2 个睡眠窗 ≈ 2×16 个固化组，具体数按实际固化数）；
#       drift_null=0/N；同时检查 llm-cost 的 cached/degraded 并如实说明缓存占比
```

24 轮覆盖 round 9 与 21 两个 night 窗（1 日=12 round，night 落 `round%12==9`），满足「人格漂移需 ≥2 窗」的门限。

---

## 9. 结论与 commit 绑定

### 9.1 结论（不夸大）

- **已达成**：固化摘要不再被丢弃（`text` 进 payload、DROPPED→0）；固化摘要落成**有正文的语义记忆**（`MEMORY_WRITE` 出现且正文可读、与摘要逐字一致）；睡眠收尾带人格指纹/漂移快照（三字段非 null）。三项均在进程内真实路径上 A/B 通过，并有回归测试守护。
- **未达成 / 未验证**：真跑批上的端到端数字（§8）；固化记忆被后续检索/对话实际引用的**行为效果**（这需要新批 + 检索命中率/对话引用分析，本轮不具备条件，**不作任何效果宣称**）。
- **不可外推**：`drift_permille` 在夹具里为 0，仅证明字段到位，不证明漂移量级变化。

### 9.2 sha 绑定

| 对象 | sha / 命令 |
|---|---|
| 代码改动（三处 + 测试 + 脚本） | `c01f6dd278cae3d6109f4dee154fa49bd208676b`（分支 `feat/life-memory-fix-20261022`） |
| 本报告与证据 | `619b18aa71ef455ca34f2154699d3fd7ab60b111`（+ 门禁证据 `ea252a3b0f6317d31f0902210fec219e25fa90a2`） |
| 合入 master 的合并提交 | `cd8f02439480298a17a93cd3460ee108e495af16`（merge `46e4380..ea252a3`） |
| 修前基线批的代码身份 | master `46e43808f28a891c26234703a48440bd0ceb9d4a`（a5 / worldline 两批产出时代） |
| 与在跑批的关系 | PID 1172001 属 `feat/d2-prefer@51cdb07`，**与本轮结论无关**，未取其为证据 |

**推送记录（原样）**：

```
$ git ls-remote origin refs/heads/master          # push 前
46e43808f28a891c26234703a48440bd0ceb9d4a	refs/heads/master
$ git push origin master
To https://github.com/Elinpf/AI-social.git
   46e4380..cd8f024  master -> master
$ git push origin feat/life-memory-fix-20261022
 * [new branch]      feat/life-memory-fix-20261022 -> feat/life-memory-fix-20261022
$ git ls-remote origin refs/heads/master refs/heads/feat/life-memory-fix-20261022   # push 后
ea252a3b0f6317d31f0902210fec219e25fa90a2	refs/heads/feat/life-memory-fix-20261022
cd8f02439480298a17a93cd3460ee108e495af16	refs/heads/master
```

⇒ **远端 master 已前进**：`46e4380` → `cd8f024` → 本报告自身提交（`cd8f024` 之后的 docs-only 提交）。
复核时以 `git ls-remote origin refs/heads/master` 为准——**本报告每补一次文字，master head 就会再前进一格**，因此不写死 head，只固定「核心合并提交 = `cd8f02439480298a17a93cd3460ee108e495af16`」。
本仓库该次 push 未出现 GnuTLS -110（`git fetch` 的问题不影响 push）。

---

## 10. 纪律自查

1. **跑批串行 / 起跑前 pgrep**：本轮**未起任何新批（含 mock）**。开工时（18:20:23）pgrep 原文见 `discipline_pgrep.txt §(a)`：仅 1172001（**非本轮所起**）+ 他人 watcher shell + 我这条命令自身（自匹配）。
2. **PID 1132529 的处置（如实）**：18:03:21 我按**当时有效的**Leader 指令对其与父脚本 1132519 发 **TERM**（未用 -9）；Leader 18:04:42 的「不许 kill」改判晚于我的动作。活性证据保留：18:02:59→18:03:07 `run.jsonl` 尺寸 `5,004,434 B` 不变、末条为 round 9 `TURN_SEAL`、`CPU TIME 5s/15min`、ESTAB 到 `172.16.3.41:31809`；但 18:01 前确有 6s +1.05MB 增长 ⇒ **证据不足以判定其为活批或卡死**，按「证据不足」如实记录，不写「确认误杀」也不写「确认残留」。
3. **TERM 后 pgrep 原文**：**未留存（留证缺口）**；补救 = 事后从会话记录补录 + 18:03:33 复查 `(EMPTY)` + 本轮交付前重新执行 pgrep（`discipline_pgrep.txt §(c)`）。
4. **1159195 单列披露**：遗留 `sleep 290` 轮询 shell（父 295404），**终止前未保存其 cmdline 原文**，属我自身操作的留证缺口（`§(d)`）。
5. **改动位置与分支**：全部改动在 `feat/life-memory-fix-20261022` 分支；改动发生时 1172001 在跑，但改动只落在主树的**工作分支**，未触碰在跑批所用的 `.worktrees/a2-prefer`（其代码与分支独立）。
6. **后台进程**：本轮无后台跑批；`make code-test` 为前台执行；无长 `sleep` 轮询（仅 A/B 前后各 0.2s 的两次进程内运行）。
7. **真 LLM 验真**：本轮无新批；基线批的 llm-cost 原文与 rc 见 §6，并明确标注 cache 占比与「推断」字样。

---

## 11. 复算命令清单（每行一条，仓库根执行）

```bash
# 修前基线（三批，100.00% 丢弃 / SM 写入 0 / drift null 满）
bash v2/evidence/fix-sleep-consolidation-20261022/r10_defect_baseline.sh
python3 v2/evidence/fix-sleep-consolidation-20261022/r10_defect_baseline_fixed.py   # 第二实现交叉核验

# A/B（修前树 = 46e4380 归档解出；修后 = 当前分支树）；输出与时间戳见 ab_rerun.log
git archive 46e43808f28a891c26234703a48440bd0ceb9d4a | tar -x -C /tmp/r10-before-tree
cd /tmp/r10-before-tree/code && PYTHONPATH=. python3 <repo>/tools/f2/verify_sleep_consolidation.py; echo rc=$?
cd <repo>/code && PYTHONPATH=. python3 ../tools/f2/verify_sleep_consolidation.py; echo rc=$?

# 回归测试
cd code && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_sleep_consolidation_obs.py
cd .. && make code-test        # 703 passed

# 真跑验真（基线批）
cd code && python3 -m obs llm-cost --log ../v2/evidence/run_a5_real_n16r42_seed42/run.jsonl --require-provider openai_compat; echo rc=$?

# 截图复现
cd code && python3 frontend/tools/gen_threads.py --log ../v2/evidence/run_a5_real_n16r42_seed42/run.jsonl \
  --out frontend/sample/dialogue_run_a5_real_n16r42_seed42/threads.json --label run_a5_real_n16r42_seed42
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 sample/dialogue_run_a5_real_n16r42_seed42/threads.json "" "" \
  ../v2/evidence/fix-sleep-consolidation-20261022/shots

# diff
git diff 46e43808f28a891c26234703a48440bd0ceb9d4a c01f6dd278cae3d6109f4dee154fa49bd208676b
```

---

*报告完。本轮无新跑批，所有终点数字均为「未做」；已证实项全部可用 §11 命令复算。*
