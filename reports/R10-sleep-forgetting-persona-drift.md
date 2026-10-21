# R10 · 睡眠—遗忘—人格漂移：一个「已默认开启却零报告」的生活气息机制的首次可观测化

> **本轮维度标签**：F-2「睡眠—遗忘—人格漂移」（团队轮次口径）。
> **性质**：不加新功能、不改 `code/`，把一套**已经 `enabled=true` 在跑、但全套报告零字提及**的机制变成可观测、可复算、可判读。
> **图源诚实声明（先读这条）**：本报告全部截图的图源是**既有已完成批次** `v2/evidence/run_g1_b0_n16r60_seed42`（`finished_at=2026-10-21T07:46:18`），**不是本轮新跑的批**。截图于 2026-10-21T10:09–10:11 由真实日志现场渲染。
> **代码零改动声明**：本报告所属提交**不含** `code/life`、`code/orchestration`、`code/config`、`code/engine` 任何文件（`git show --stat <本报告提交>` 可核）。

---

## 0. 摘要（TL;DR）

| # | 结论 | 层级 | 证据 |
|---|---|---|---|
| 1 | **机制确实在跑，不是空转**：16 agent × 60 round 的批次里 `SLEEP_STARTED=SLEEP_COMPLETED=80`（16 人 × 5 夜）、`MEMORY_FORGET=38976`、`PERSONA_DRIFT=105`、`MEMORY_CONSOLIDATE=1267` | 已证实（存在性） | §3.2 / §8 E1 |
| 2 | **记忆末端存活率 93.10%**（27828 条 `MEMORY_WRITE`，1920 条 distinct 被 `drop`）；遗忘动作以 `demote` 为主（30664 次，78.7%），`merge` 6392、`drop` 1920 | 已证实（计数） | §3.2 |
| 3 | **遗忘曲线随年龄单调下降**：R 均值 13–24 round **509.5‰** → 25–36 **401.3‰** → 37–48 **279.9‰** → 49–60 **240.5‰**；观测域仅 **[182, 598]‰**（只有 R<600 才会落事件，故永不接近 1000） | 已证实（形状）；**不能反解 h0** | §3.2 / §5.4 |
| 4 | **「睡一觉记得更牢」在本批不成立（阴性）**：睡前存活记忆在睡后一个昼夜内的召回率均值 **1.33%**，同一集合在**睡前**一个昼夜的对照召回率 **6.59%**，差 **−5.26pp**，80 个窗口里只有 **1** 个上升。检索明显偏新（被选中记忆平均年龄 17.44 round，>12 round 占 54.06%） | 阴性结果（两批复现） | §3.2 / §3.3 / §5.2 |
| 5 | **人格漂移真实但极小**：14/16 个居民有 `PERSONA_DRIFT`，最大 `drift_permille=10`（1%）；逐维对锚 L2 ≤ **2.236**、余弦 ≥ **0.99986** —— 与 `alpha_permille=20` + `delta_max=1` + `min_windows=2` 的「抗漂移」设计一致 | 已证实（但有量级上限，见 §5.3） | §3.2 / §5.3 |
| 6 | **两条链路缺陷使「人格漂移」只部分可观测**：① `MEMORY_CONSOLIDATE` 1267 条**全部**被 `unknown_intent_field` 丢弃、`SM-` 语义记忆写入 **0** 条；② `SLEEP_COMPLETED` 的 `drift_permille/pf0/pf_t` **80/80 全 null**（同期 `PERSONA_DRIFT` 事件里却有值） | 已证实（缺陷） | §5.3 |

**一句话**：F-2 机制在真 LLM 批里**确实可观测**（睡眠窗 80 次、遗忘三级 3.9 万条、漂移 105 条），
但**固化摘要与睡眠收尾快照两条链路是半落地/未落地**，所以本报告只敢写到「机制在跑、方向可测、量级受日志缺陷限制」，不写「睡眠改善记忆」，也不写「人格在成长」。

### 0.1 口径澄清：两个「F-2」不是同一个东西（必读，防止串味）

仓库里 **`F-2` 这个编号已经被占用**，且含义完全不同：

| 出处 | `F-2` 指什么 | 单位 |
|---|---|---|
| `reports/R4-life-texture.md` §1 七维词表（**唯一生活气息口径表**） | **话题漂移率**（相邻消息对 Jaccard<0.10） | per-adjacent-pair |
| 本报告 / 本轮团队轮次标签 | **睡眠—遗忘—人格漂移** | per-agent / per-sleep-window |

⇒ 本报告一律写作 **「F-2（睡眠—遗忘—人格漂移，团队轮次标签）」**；凡引用 R4 指标，一律写 **「R4-F-2 话题漂移率」**。
**读者若看到这两个「F-2」被互换引用，即视为引用错误。**
另注：本维度在 R4 七维词表中最接近的既有指标是 **F-6 跨天记忆引用率**（per-message），但 F-6 测的是「对话里回指旧事」，本轮测的是「机制层的记忆/人格状态变化」，**两者不可互相替代**。

### 0.2 结论 → commit 绑定

| 结论类别 | 绑定对象 | sha |
|---|---|---|
| 本轮脚本与证据（`tools/f2/memory_drift_report.py`、5 张 PNG、2 份 obs 验真原文、`render.log`） | 证据入库提交 | **`aa0078ddc0c792a9edd41734521a11f8b2c72abc`**（`aa0078d`） |
| 本报告正文 | 报告提交 | `git log -1 --format=%H -- reports/R10-sleep-forgetting-persona-drift.md`（报告无法自引自身 sha，故给命令而不给常量，避免「提交后 sha 变化导致过期」） |
| 被观测批次 `run_g1_b0_n16r60_seed42` 的代码身份 | `meta.json.code_sha`（**不是** commit 推导的臂名） | `d9391a37cbfc286537748b1ce959f6cb3267cb16`（`d9391a3`） |
| 交叉臂 `run_dr_round1_arm-ctrl_n16r60_seed42` | `meta.json.code_sha` | `d5657ceb…44fe5d8b`（`d5657ce`） |
| 引用的既有结论：D2 对话结构 A0 | 历史 commit | `884f454` |
| 引用的既有结论：A1 措辞臂 | 历史 commit | `a637371` |
| 引用的既有结论：D8 世界事件剂量 | 历史 commit | `6602b77` |
| 引用的既有结论：D9 回复窗口 | 历史 commit | `05636bc` |

> ⚠️ 本仓库已两次纠正过的老坑（见 `6742180`、`0f1cd67`）：**`abefdf73` / `643f13a5` 是 `run.jsonl` 的 sha8，不是 commit**。
> 本报告的 `6db62e8a` / `99c92d4b` 同理是 **日志 sha8**，对应代码分别是 `d9391a3` / `d5657ce`，**不要互串**。

---

## 1. 本轮维度与为什么选它（零报告空白）

### 1.1 空白是可复算的，不是形容词

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
grep -rn "睡眠\|遗忘" reports/*.md | wc -l
# 0
grep -rln "睡眠\|遗忘" reports/*.md
# （无输出）
```

在本报告落库之前，**R1–R9、D7、d9-readings、README 全套报告族里没有任何一处提到「睡眠」或「遗忘」**。
而这套机制的开关现状是：

```bash
grep -n '"enabled"' code/config/life_v2.json
# 5:    "enabled": true,     ← sleep.enabled
# 10:    "enabled": true,    ← forgetting.enabled
```

⇒ **「机制在跑、没人证明它在起作用」**。这是本轮最干净的空白：不需要发明新功能，只需要把一个已生效的东西变成可判读的。
（对照：结构层 D2 `884f454`、措辞层 A1 `a637371`、世界事件 D8 `6602b77`、往来密度 D9 `05636bc` 都已有报告；G1 闲话与 DR 对话修复在途。F-1/F-2b/F-5/F-5b/F-6 至今无改造实验。）

### 1.2 为什么它算「生活气息」

生活气息的底层是**时间感**：**夜里没人说话、会忘事、性格被日子磨得有点不一样**。
前九份报告做的都是「白天说话好不好看」（结构、措辞、密度、事件），本报告第一次去看**「过了 5 天以后，这个镇子还记不记得住事、人有没有变」**。

### 1.3 本轮**不做**什么（边界先声明）

- **不起新批**：既有已完成批次已覆盖 F-2 三类信号，且人格漂移需 ≥2 个睡眠窗才发事件，最小可跑批（24 回合=2 天）边际信息近乎为零（详见团队内部 `f2-run-evidence.md` §2）。
- **不改 `code/`**：所有产出的都是只读脚本与派生物。
- **不给效果结论**：本报告只回答「机制在不在跑、能不能测、测出来什么量级」。

---

## 2. 机制事实（代码行号 + 参数当前值）

> 下列行号均为 **`aa0078d`（本轮证据入库提交）时的代码状态**。`code/` 目录在本轮零改动，故与当前 HEAD 一致。

### 2.1 睡眠窗的触发条件

| 规则 | 位置 | 事实 |
|---|---|---|
| 挂载点 | `code/life/agent.py:388` `rep.slept = self._maybe_sleep_window(wv)` | 睡眠是**决策前的离线窗**，不是独立循环 |
| 参数加载 | `agent.py:1165-1167` → `code/life/sleep_window.py:23-48` | 读 `config/life_v2.json`，再经 `life/config.apply` 允许运行时覆盖 |
| 总开关 | `sleep_window.py:51-53` `enabled()` | `sleep.enabled or forgetting.enabled` 任一为真即整条流程启用（当前两者皆 `true`） |
| 时段闸 | `agent.py:1180-1182` `if wv.time.slot != slot: return 0` | 只在 `slot=="night"` 触发 |
| 每日一次 | `agent.py:1183-1186` + `_slept_days`（`agent.py:145`） | 同一 `day` 只睡一次；`_slept_days` 在 `agent.py:199-211` 由历史 `SLEEP_STARTED/COMPLETED` 重建（restore 后不重复睡） |
| 纯整数、无 LLM | `sleep_window.py:56-86` `run_sleep_window` | 纯函数，产出「动作 + 待发事件」，**不新增任何决策类 LLM 调用** |
| 事件落账 | `code/orchestration/integration.py:515` `_do_memory` | 由裁决器统一 emit |

**实测触发分布**：1 日 = 12 round，night 落在 `round % 12 == 9` ⇒ 本批（60 round = 5 日）睡眠窗为 **round 9 / 21 / 33 / 45 / 57**，每窗 **16 人**，共 **80** 个窗口（与 `SLEEP_STARTED=80` 逐位吻合）。
`round 9`（第 0 夜）**零遗忘动作**——记忆都太新，R 未跌破 600‰ 阈值；`round 21` 起才出现 `demote`。

### 2.2 遗忘/衰减：按什么衰减、翻多少、有没有下限

```python
# code/life/forgetting.py:71-82
def strength_permille(mem, params):
    s = (s_base + w_access*access_count + w_importance*importance
         + w_emo*|emo| + w_consolidated*consolidated)
    return clamp(s, s_min_permille, s_max_permille)
```

```python
# code/life/forgetting.py:85-101
def retention_permille(dt_slots, s_permille, h0_slots):
    half_life = max(1, h0 * s // 1000)      # H = h0·S/1000
    steps = dt // half_life
    if steps >= 16: return 0
    half = 1000 >> steps                    # 每过一个半衰期折半
    frac = (dt % half_life) * 1000 // half_life
    return int(half - (half * frac // 1000 // 2))   # 半衰期内线性降到 half/2
```

| 规则 | 位置 | 具体值 |
|---|---|---|
| 强度 `S` | `forgetting.py:71-82` | `S = 1000 + 500·access + 300·importance + 400·\|emo\| + 500·consolidated`，夹到 `[1000, 6000]`‰ |
| 半衰期 `H` | `forgetting.py:94` | `H = h0·S//1000`，`h0=14` ⇒ **H ∈ [14, 84] round**（S=1000 时 14 round 折半，比 1 日 12 round 略长） |
| 保留度 `R` | `forgetting.py:85-101` | 整数、单调不增，值域 `[0,1000]`；**无正下限**，但只有 `R<600` 才产生动作 |
| 分级 | `forgetting.py:124-150` `classify` | `R≥600`→`keep`（不落事件）；`R<600`→`demote`；`R<300`→有同 subject 兄弟则 `merge`，否则 `drop` |
| 保护名单 | `forgetting.py:104-121`（常表 `45-51`） | 命中任一即「**只降级、永不 merge/drop**」：`kind∈{semantic,reflection}` / `importance≥7` / `access_count≥3` / `\|emo\|≥6` / `referenced_by_reflection` |
| 唯一真删除 | `code/engine/replay.py:359-368` | **只有 `drop`** 会从状态里移除；`demote`/`merge` 只写 `forgotten_level`（**merge 不删源记忆**） |

> ⇒ 「记忆死亡」的定义严格绑定 `replay` 语义：**只有 `drop` 算死亡**。这是 M1 口径的根基，不是自选。

### 2.3 人格向量如何被更新

```python
# code/life/persona_drift.py:56-67
def bounded_update(p, anchor, dim, delta, params):
    d   = clamp(delta, -delta_max, delta_max)      # delta_max = 1
    pull= (anchor[dim] - p[dim]) * alpha_permille // 1000   # α = 20‰ = 0.02
    return clamp(p[dim] + pull + d, 0, 100)
```

| 规则 | 位置 | 事实 |
|---|---|---|
| 锚定不写回 | `agent.py:1188-1191`、`sleep_window.py:113-136` | persona 卡**只读**；表达层 `P(t)` 由 `P(0)=anchor` 起，**永不回写人格卡** |
| 有界更新 | `persona_drift.py:56-67` | `P ← clamp(P + α·(a−P)/1000 + clamp(Δ,±1), 0, 100)`，α=0.02 |
| 候选来源 | `agent.py:1244-1289` `_reflection_drift_events` | 仅取**既有**反思（`kind=="reflection"` 且 `importance≥7`），`dim=sha256(mem_id)%5`，符号由 `emotion.py` 情感词表定，**无情感词不产**——**不新增 LLM 调用** |
| 抖动 vs 真漂移 | `agent.py:1276-1286` | 同一维需**连续 `min_windows=2`** 个窗口含候选才发 `PERSONA_DRIFT`（`reached = streak >= min_windows`，第 1277 行）；发出后计数清零（冷却，第 1286 行）；每窗每维至多一条 |
| 漂移度量 | `persona_drift.py:79-88` | `drift_permille = Σ_d\|P(t)_d − P(0)_d\|·1000/(5·100)`（**L1 归一化**，0–1000‰） |
| 边界校验 | `persona_drift.py:91-98` | 全维 ≤ `drift_max_permille=150`，逐维 ≤ `drift_dim_max_permille=200` |

### 2.4 参数表（`code/config/life_v2.json` 当前值）

| 段 | 键 | 行 | 当前值 |
|---|---|---|---|
| sleep | `enabled` / `slot` / `planned_ticks` | 5 / 6 / 7 | `true` / `"night"` / `3` |
| forgetting | `enabled` | 10 | `true` |
| forgetting | `h0_slots` | 11 | `14` |
| forgetting | `s_base_permille` / `w_access` / `w_importance` / `w_emo` / `w_consolidated` | 12-16 | `1000 / 500 / 300 / 400 / 500` |
| forgetting | `s_min_permille` / `s_max_permille` | 17-18 | `1000 / 6000` |
| forgetting | `theta_keep_importance` / `theta_keep_access` / `theta_keep_emo` | 19-21 | `7 / 3 / 6` |
| forgetting | `theta_demote_permille` / `theta_forget_permille` | 22-23 | `600 / 300` |
| forgetting | `consolidate_min` | 24 | `2` |
| persona_drift | `alpha_permille` / `delta_max` | 27 / 28 | `20` / `1` |
| persona_drift | `drift_max_permille` / `drift_dim_max_permille` | 29 / 30 | `150 / 200` |
| persona_drift | `min_importance` / `min_windows` / `criterion` | 31-33 | `7 / 2 / "natural"` |

> 该文件**纳入 `engine_version` 指纹**（文件第 2 行注释明示）⇒ 「这批用的是不是这套参数」可由 `meta.json.code_sha` + 引擎指纹交叉核对，**不需要靠猜**。

### 2.5 事件 → 可观测字段

| 事件 | 关键 payload | 能算什么 |
|---|---|---|
| `SLEEP_STARTED` / `SLEEP_COMPLETED` | `agent_id, day, slot, planned_ticks` / `actual_ticks` | 窗口数、时段、每日一次 |
| `MEMORY_FORGET` | `mem_id, level, retention_permille, protected, protection_reason` | 分级计数、R 分布、保护命中、单窗存活率 |
| `MEMORY_CONSOLIDATE` | `subject, source_mem_ids, produced_mem_id` | 固化次数、被并条数（**注意：无 `text`，见 §5.3**） |
| `PERSONA_DRIFT` | `dim, before, after, anchor, drift_permille, pf0, pf_t` | 漂移幅度/方向/指纹 |
| `PERSONA_DRIFT_CANDIDATE` | `dim, sign, window, reached_threshold` | 抖动 vs 真漂移计数 |
| `MEMORY_WRITE` / `MEMORY_RETRIEVE` | `mem_id, kind, importance, subject` / `selected_mem_ids, top_k` | 存活率分母 / 召回率分子 |

---

## 3. 指标定义与实测表（真实数字）

### 3.1 四个指标的定义

| 指标 | 公式 | 数据来源字段 |
|---|---|---|
| **M1 记忆存活率** | `survival_end = 1 − \|{mem: level=="drop" 出现过}\| / \|MEMORY_WRITE\|`；单窗 `1 − drop_in_window / alive_before_window` | `MEMORY_FORGET.level,mem_id`；`MEMORY_WRITE.mem_id/round/agent` |
| **M1b 遗忘曲线** | `R(age)`，`age = forget.round − write.round` | `MEMORY_FORGET.retention_permille` |
| **M2 睡后召回率** | `recall_after = \|presleep ∩ ⋃_{R<r≤R'} selected(T_r)\| / \|presleep\|`；**对照**：同一 `presleep` 在 `(R−12, R]` 的召回率 | `MEMORY_RETRIEVE.selected_mem_ids` |
| **M3 人格漂移** | 官方：`drift_permille`（L1 归一化）；辅：逐维对锚 `L2_partial`、`cosine_partial` | `PERSONA_DRIFT.{before,after,anchor,drift_permille}` |
| **M4 睡前后行为差** | 以睡眠 round `R` 为断点：`mean_len` 差、情感极性、话题 `TV = 0.5·Σ\|p_pre−p_post\|` | `MSG_DM/MSG_PUBLIC.{body,topic,round}`；极性用 `code/life/emotion.py` 复算 |

> M4 的情感极性是**派生量**：`TAG_EMITTED.valence` 在本批 304 条里**全为 0**，不能当来源（§5.4）。

### 3.2 主表：G1 B0 批次（`code_sha=d9391a3`，log sha8 `6db62e8a`）

**批身份**：16 agent × 60 round（5 日 × 12 回合），`events=116318`，`[life] seconds=4344.1277`，`finished_at=2026-10-21T07:46:18`。

| 指标 | 数值 | 分母 / 说明 |
|---|---|---|
| M1 末端存活率 | **0.931005** | 27828 写入 / 1920 distinct `drop` |
| M1 单窗平均存活率（80 窗） | **0.984448** | — |
| M1 遗忘动作总数 | **38976** | demote 30664（78.7%）/ merge 6392 / drop 1920 |
| M1 保护记忆命中 | **738** 次，**全部只降级** | 0 次 merge/drop（与 `forgetting.py:104-121` 一致） |
| M1 R 观测域 | **[182, 598]‰** | demote 均值 440.5，merge 239.4，drop 247.2 |
| M1b 遗忘曲线（R 均值 by age） | 13–24: **509.5** (n=12281) / 25–36: **401.3** (n=14568) / 37–48: **279.9** (n=9287) / 49–60: **240.5** (n=2341) | 单调下降 |
| M2 检索命中率 | 0.983333 | 960 次检索，16 次空 |
| **M2 睡前记忆 · 睡后召回率** | **0.013341** | 80 窗，**0 窗零召回** |
| **M2 睡前 · 睡前对照召回率** | **0.065925** | 同集合 |
| **M2 差（睡后 − 睡前）** | **−0.052584** | 80 窗中**仅 1 窗上升** |
| M2 检索偏好 | 平均选中 7.866 条/次；选中记忆平均年龄 **17.44** round；>12 round 占 **54.06%**；>36 round 占 13.07% | lexical 800 / vector 160（`vec_available=false` 800） |
| M3 有漂移居民 | **14/16**；`PERSONA_DRIFT=105`，候选 238（reached 105） | — |
| M3 最大漂移 | **`drift_permille=10`**；`Σ\|Δ\|` 均值 6.562；逐维 L2 ≤ **2.236**、cos ≥ **0.99986** | 见 §5.3 对量级的限制 |
| M3 维度分布 | openness 22 / conscientiousness 23 / extraversion 20 / agreeableness 21 / neuroticism 19 | 五维基本均衡 |
| M4 对话长度 | 睡前 32.93 字（n=497）→ 睡后 33.34 字（n=419），**+0.41** | 量级差异，不作结论 |
| M4 情感极性 | 命中率 11.27% → 10.50%；命中里正情绪占比 41.07%（23/56）→ **29.55%**（13/44） | 样本仅 ~900 条，**不作结论** |
| M4 话题分布差 | **TV = 0.054513** | 分辨力低（§3.3） |

**M1 分级明细**（与代码阈值交叉核对）：

| level | 动作数 | distinct mem | protected | R min | R max | R mean |
|---|---|---|---|---|---|---|
| demote | 30664 | 18623 | 738 | 302 | 598 | 440.5 |
| merge | 6392 | 5569 | 0 | 182 | 296 | 239.4 |
| drop | 1920 | 1920 | 0 | 211 | 296 | 247.2 |

> `merge/drop` 的 R 全落在 300 以下、`demote` 全落在 [302,598]、保护记忆 738 次**只出现在 demote** ⇒ 与 `forgetting.py:124-150` 的分级阈值**逐项吻合**。这说明日志与代码是同一套语义，**不是事后拟合**。

### 3.3 交叉复现：DR round1 ctrl 臂（`code_sha=d5657ce`，log sha8 `99c92d4b`）

| 指标 | G1 B0 | DR ctrl | 判读 |
|---|---|---|---|
| M1 末端存活率 | 0.931005 | 0.930502 | 同量级 |
| M1 demote/merge/drop | 30664/6392/1920 | 30657/6385/1934 | 同量级 |
| M1 单窗平均存活率 | 0.984448 | 0.984338 | 一致 |
| **M2 睡后召回 / 对照 / 差** | 0.013341 / 0.065925 / −0.052584 | 0.013481 / 0.065997 / −0.052516 | **阴性结果可复现** |
| M2 选中平均年龄 | 17.44 | 17.65 | 一致 |
| M3 有漂移 / 最大 drift | 14/16 / 10‰ | 16/16 / 6‰ | **两批不同**（`code_sha` 不同，见 §5.5） |
| M4 长度差 / 话题 TV | +0.41 / 0.054513 | +0.65 / **0.054513** | 量级一致 |

> 两批 `topic_tv` **完全相同（0.054513）** ⇒ 话题结构在两条臂里几乎冻结（同 seed、同 prompt），
> **这也提示 M4 话题维度分辨力低，不能当「生活气息变好」的证据。**

### 3.4 本轮报告作者的独立复跑（不只转录上游）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
time python3 tools/f2/memory_drift_report.py \
     --run-dir v2/evidence/run_g1_b0_n16r60_seed42 --out-dir /tmp/f2_rd_check
```

实跑输出（原文）：
```
[f2] log=v2/evidence/run_g1_b0_n16r60_seed42/run.jsonl sha256=6db62e8a3b92... events=116318
[f2] M1 survival_rate_end=0.931005 levels={'demote': 30664, 'merge': 6392, 'drop': 1920}
[f2] M2 mean_recall_presleep=0.013341 hit_rate=0.983333
[f2] M3 agents_with_drift=14/16 max_drift_permille=10
[f2] M4 delta_mean_len=0.41 topic_tv=0.054513
1.10user 0.08system 0:01.19elapsed 100%CPU
```

⇒ 1.19 秒、只读、脚本自算 `sha256=6db62e8a3b92…`（与 `meta.json.derived_from_log_sha256` 一致），
本文 §3.2 的每个数字都是**本报告作者自己跑出来的**，不是抄上游文档。

---

## 4. 证据链

### 4.1 批身份与完整性

| 字段 | 主批 `run_g1_b0_n16r60_seed42` | 交叉臂 `run_dr_round1_arm-ctrl_n16r60_seed42` |
|---|---|---|
| `run.jsonl` sha256 | `6db62e8a3b926af7755fe220a5e8361c851e195d94afff00d16c00e7e1d0c983` | `99c92d4b00e48bc629f064e0c10782e0248147451bf5ee44e29e2fd40d93b5bd` |
| 字节 / 行 | 55,225,513 / 116,318 | 55,224,767 / 116,319 |
| `events` vs `meta.events` | 116318 = 116318 ✓ | 116319 = 116319 ✓ |
| `code_sha` | `d9391a37cbfc286537748b1ce959f6cb3267cb16`（`git_dirty_code_files=[]`） | `d5657ceb…44fe5d8b` |
| 真跑判据 | `chain_ok=True replay_parity=True first_run_equals_replay=True conservation_ok=True` | 同左 |
| `finished_at` | 2026-10-21T07:46:18 | 2026-10-21T09:24:37 |

**原始起批命令**（抄自 `v2/evidence/run_g1_b0_n16r60_seed42/host.log` 首行，原文）：

```
[d2] run: python3 -m orchestration run --life --seed 42 --agents 16 --rounds 60 \
     --out .../v2/evidence/run_g1_b0_n16r60_seed42/run.jsonl --flush-every 2
```

> `.gitignore` 的 `**/*.jsonl` 使 `run.jsonl` **不入库**——这是仓库既有约定（体积），
> 故本报告用 **sha256 全值**做身份锚，而不是靠文件名。

### 4.2 真 LLM 验真（obs llm-cost 原文已入库）

```bash
cd code && python3 -m obs llm-cost \
  --log ../v2/evidence/run_g1_b0_n16r60_seed42/run.jsonl --require-provider openai_compat
```

原文文件：`v2/evidence/f2_llmcost_g1_b0_6db62e8a.txt`（含命令、时间、stdout 原文、`rc=0`）。
关键片段（逐字）：

```json
"total":{"cached":1473,"calls":2878,"degraded":0,"thinking":668,
         "tokens_in":228871,"tokens_out":275191,"tokens_total":504062}
"provider_guard":{"by_provider":{"openai_compat":2878},"expected":"openai_compat","ok":true,"problems":[]}
rc=0
```

**判决：PASS**（`provider_guard.ok=true`、`degraded=0`、`problems=[]`、`rc=0`）。交叉臂：`total.calls=2878`、`cached=1475`、`tokens_total=500513`、`ok=true`，原文 `v2/evidence/f2_llmcost_armctrl_99c92d4b.txt`。

### 4.3 截图（5 张，**图源=既有批次，非本轮新跑**）

- **图源 run 目录**：`v2/evidence/run_g1_b0_n16r60_seed42/`（`run.jsonl` sha8 = `6db62e8a`）
- **生成时间**：2026-10-21T10:09–10:11（文件 mtime 可核）
- **生成命令**（原文，两段）：

```bash
# ① 派生截图数据源（1.9 MB，未入库，见 §4.4）
cd code && python3 frontend/tools/gen_threads.py \
  --log ../v2/evidence/run_g1_b0_n16r60_seed42/run.jsonl \
  --meta ../v2/evidence/run_g1_b0_n16r60_seed42/meta.json \
  --out frontend/sample/dialogue_run_g1_b0_n16r60_seed42/threads.json \
  --require-complete --label run_g1_b0_n16r60_seed42-6db62e8a

# ② 四视图截图（静态服务 http://127.0.0.1:8871 为既有服务，非本轮新起）
cd code && bash frontend/tools/dialogue_shots.sh \
  http://127.0.0.1:8871 sample/dialogue_run_g1_b0_n16r60_seed42/threads.json "" "" ../v2/evidence/f2_shots
```

`gen_threads.py` 原文输出：`完整性断言通过：TURN_SEAL 60 条覆盖 round 0..59`、`messages=510 threads=169 multi_turn=88`。

| # | 文件（相对仓库根） | 视图 | 尺寸 | sha256 |
|---|---|---|---|---|
| P1 | `v2/evidence/f2_shots/run_g1_b0_n16r60_seed42-chat-6db62e8a.png` | chat 对话流 | 1400×900 | `1e6017b8d7824d97ed3f03221dbb32b82883127809b363d1a125672fcfd2208c` |
| P2 | `v2/evidence/f2_shots/run_g1_b0_n16r60_seed42-rhythm-6db62e8a.png` | rhythm 节律·串门 | 1300×1050 | `c29f7fcf77ac41f479af314d92952555dbaf82a10e08a0f7f834aaaf0fd720fb` |
| P3 | `v2/evidence/f2_shots/run_g1_b0_n16r60_seed42-spread-6db62e8a.png` | spread 闲话怎么传开 | 1300×900 | `80e540020aa2faae325d59027b71b7e404c6e7ceb39f31c2db27842fb047f5dd` |
| P4 | `v2/evidence/f2_shots/run_g1_b0_n16r60_seed42-600-6db62e8a.png` | 600px 判读 | 600×900 | `4ee90e19f35ded1ecdac435d57bb15c9e032681e4a9787e5d5bd43397fa1ea60` |
| P5 | `v2/evidence/f2_shots/run_g1_b0_n16r60_seed42-f2sleep-6db62e8a.png` | **派生三联时间线（非前端视图）** | 1430×1155 | `7685525a0ec36b93f85140462bed65f35ec261c151bbfcd7f55f02ed9fadcd61` |

**非退化判据**（不是「有文件就算」）：`render.log` 记录 4/4 `SHOT OK`、`blank_retries=0/2`、`mean_brightness` 23.2–38.2、`max_color_frac` 30.33%–71.20%；本轮又用 Pillow 全解码复核尺寸与模式（P5 为 RGBA，其余 RGB）。**无黑图/白图。**

**P1–P4 的判读边界（必须说清）**：前端四视图显示的是**对话流、空间节律、闲话传播**，
它们**看不到**睡眠/遗忘/漂移事件。图能证明的是「这批 60 回合的小镇确实在正常说话、正常串门」，
**不能**用来证明 F-2 机制生效 —— 后者靠 §3.2 的事件计数。

**P5 为什么加、以及它是什么**：为让 F-2 维度**可判读**，用真实 log 另派生一张三联时间线
（① `MEMORY_FORGET` 三级/回合堆叠柱 ② `PERSONA_DRIFT`/回合 ③ 对话条数/回合 + 睡眠窗竖线 round 9/21/33/45/57）。

```bash
python3 <f2 时间线图脚本> v2/evidence/run_g1_b0_n16r60_seed42/run.jsonl \
        v2/evidence/f2_shots/run_g1_b0_n16r60_seed42-f2sleep-6db62e8a.png
# 实跑 stdout：{"log_sha256":"6db62e8a…","rounds":57,
#   "forget_total":{"demote":30664,"merge":6392,"drop":1920},
#   "persona_drift_total":105,
#   "sleep_windows":{"9":16,"21":16,"33":16,"45":16,"57":16}}
```

**诚实标注**：该图脚本本轮**未入库**（仅存在于 `/tmp/f2_chart.py`，全文见团队内部 `f2-run-evidence.md` 附录 A）。
⇒ **P5 目前是「有图、有 sha256、缺脚本」的状态**，第二人只能靠附录 A 的全文复现。这是本报告的一处已知缺口（§6.1）。

### 4.4 未入库的 `threads.json`（截图复现输入，1.9 MB）

| 项 | 值 |
|---|---|
| 路径 | `code/frontend/sample/dialogue_run_g1_b0_n16r60_seed42/threads.json` |
| 大小 | 1,988,463 B（**1.9 MB**） |
| sha256 | `8b6f51701fbaba58ebd83ccb76614813b16fff62b01551f62f96c0be2840ff5e` |
| 性质 | 由 `run.jsonl` **纯派生**的截图输入（非源码、非逻辑改动） |
| 未入库原因 | 体积 >1 MB，且 `code/` 下出现数据副本易被后人误读为逻辑变更（Leader 判定） |
| 重建命令 | 见 §4.3 ①；重建后 `sha256sum` 应得上面的值 |

### 4.5 复算命令清单（第二人照做即可）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# ① 日志身份
sha256sum v2/evidence/run_g1_b0_n16r60_seed42/run.jsonl   # 期望 6db62e8a…1d0c983
wc -l     v2/evidence/run_g1_b0_n16r60_seed42/run.jsonl   # 期望 116318

# ② 真 LLM 验真（⚠️ 不要传 --cache-dir，见 §6.2）
cd code && python3 -m obs llm-cost \
  --log ../v2/evidence/run_g1_b0_n16r60_seed42/run.jsonl --require-provider openai_compat
cd ..

# ③ 指标复算（本文 §3.2 全部数字）
python3 tools/f2/memory_drift_report.py \
  --run-dir v2/evidence/run_g1_b0_n16r60_seed42 --out-dir /tmp/f2_recheck
# 交叉臂（§3.3）
python3 tools/f2/memory_drift_report.py \
  --run-dir v2/evidence/run_dr_round1_arm-ctrl_n16r60_seed42 --out-dir /tmp/f2_recheck2

# ④ 截图复算（需 code/frontend 静态服务；本文用既有 8871）
cd code && python3 frontend/tools/gen_threads.py --log ../v2/evidence/run_g1_b0_n16r60_seed42/run.jsonl \
  --meta ../v2/evidence/run_g1_b0_n16r60_seed42/meta.json \
  --out frontend/sample/dialogue_run_g1_b0_n16r60_seed42/threads.json \
  --require-complete --label run_g1_b0_n16r60_seed42-6db62e8a
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8871 \
  sample/dialogue_run_g1_b0_n16r60_seed42/threads.json "" "" ../v2/evidence/f2_shots
```

---

## 5. 结论与局限

### 5.1 可以写成「事实」的部分（存在性，不含效果判断）

1. **机制在跑**：80 个睡眠窗、38976 条遗忘动作、1267 条固化事件、105 条人格漂移事件（§3.2）。
2. **分级与代码语义吻合**：`merge/drop` 的 R 全 <300、`demote` 全在 [302,598]、保护记忆 738 次只降级（§3.2 明细表）⇒ 日志口径可信。
3. **遗忘曲线形状单调**（509.5 → 401.3 → 279.9 → 240.5‰）。
4. **人格漂移存在且方向可测**：14/16 居民、五维分布均衡、指纹 `pf0→pf_t` 变化可查。

### 5.2 阴性结果（照实写，不修饰）

> **「睡一觉记得更牢」在本批不成立。**
> 睡前存活记忆在睡后一个昼夜的召回率 **1.33%**，低于**同一集合**在睡前一个昼夜的对照召回率 **6.59%**，
> 差 **−5.26pp**；80 个窗口里只有 **1** 个上升；且两批（`d9391a3` / `d5657ce`）复现同一负值（§3.3）。

**正确的读法是「未观测到睡眠增益」，不是「睡眠损害记忆」**：检索本身明显偏新（平均年龄 17.44 round、>12 round 占 54%），
召回主要被「新近性」支配，睡前集合天然处于劣势。**要判「睡眠是否改善巩固」，需要的对照设计本批不具备**（§7）。

### 5.3 两处观测缺陷（**直接决定结论上限，不弱化**）

**缺陷 ①：`MEMORY_CONSOLIDATE` 的 `text` 字段整批被丢弃 ⇒ 固化这一支在真实跑批里等于没生效**

- 提交侧：`code/life/agent.py:1218-1221` 提交 intent 时**带了** `"text": g["text"]`（第 1221 行）；
- 装配层：`code/orchestration/integration.py:426-434` 对未知字段落 `DROPPED{reason:"unknown_intent_field"}`（`DROPPED` 事件落账在 **第 430-433 行**；白名单 `integration.py:408-424` 的 `_assemble` base 不含 `text`）；
- 实测（两批一致）：`MEMORY_CONSOLIDATE=1267`、`unknown_intent_fields={"MEMORY_CONSOLIDATE::text": 1267}`、**`MEMORY_WRITE` 中 `SM-` 条数 = 0**。

⇒ 1267 条固化意图**1:1 被丢弃**；`replay.py:371-388` 仍会 fold 出 semantic 记忆（`importance` 缺省 6），
但**该记忆的正文与 importance 在日志侧根本不存在** ⇒ **固化效果不可评估**，不是「效果差」，是「没落库」。

**缺陷 ②：`SLEEP_COMPLETED` 的漂移快照 80/80 全 `null`**

- 原文样例：`{"actual_ticks":3,"agent_id":"P001","day":0,"drift_permille":null,"pf0":null,"pf_t":null,"slot":"night"}`
- 同期 `PERSONA_DRIFT` 事件**却有** `pf0/pf_t/drift_permille`（如 P004 round21 `drift_permille=4`）。

⇒ **数据存在、只是没回填到收尾事件**（`agent.py:1232-1233` 的 `sleep_end` intent 只带 `actual_ticks`，未携带这三个字段）。
故**人格漂移只能取 `PERSONA_DRIFT` 事件**，`SLEEP_COMPLETED` 不能当快照来源；`obs/life.py` 的 `last_fp` 在睡眠事件上取不到值。

**这两条合起来给出本报告的结论上限**：
> 「机制在跑、方向可测，但**漂移量级与固化效果受日志缺陷限制**，现在只能报告 `PERSONA_DRIFT` 事件层的量级（≤1%），不能宣称『人格在成长』。」

### 5.4 未观测 / 不可得（照实列，不填坑）

1. `MEMORY_WRITE` 只带 `importance/kind/subject`，**无** `last_access`/`access_count`/`emo` ⇒ 无法精确复算 `strength_permille`，也**不能把 `retention_permille` 反解成 `h0`**；本文的遗忘曲线是 `dt` 的**上界刻度**（只能读形状）。
2. `SLEEP_COMPLETED.drift_permille/pf0/pf_t` 恒 `null`（缺陷 ②）。
3. SM 记忆的正文与 importance 在日志侧不存在（缺陷 ①）。
4. `TAG_EMITTED.valence` 全 0 ⇒ 情感极性只能用 `emotion_sign` **复算**（派生量）。
5. **P001 的漂移是「未观测」（该居民 60 round 内无满足条件的反思信号），不是「漂移为 0」** —— 这两者写混是本维度最容易犯的错。
6. 未观测到「睡眠提升睡前记忆召回」（§5.2，阴性）。

### 5.5 可信边界

- 本报告全部数字限定在 **本配置、本规模（16×60）、seed=42、两个 `code_sha`** 内；不外推。
- **不改进度结论**：本轮没有「改前/改后」两臂，故本报告**不给任何「生活气息变好」的判断**，只给「机制可观测」。
- 两批 M3 不同（14/16 vs 16/16、最大 10‰ vs 6‰）**不是矛盾**：`code_sha` 不同（`d9391a3` vs `d5657ce`），漂移由「既有反思信号」驱动，反思内容依赖 LLM 措辞 ⇒ **LLM 措辞层不可复现**（与 R1 可信边界一致）。**这也再次说明漂移计数不能跨臂横比。**
- M4 全部指标（长度差 +0.41 字、话题 TV 0.054513、正情绪占比下降）**不作结论**：样本 ~900 条，且两批 `topic_tv` 完全相同说明该维度分辨力低。
- 遗忘曲线是 `forgetting.py` 文件头**自标 `【未验证】` 的工程近似**，本文不把它当心理学结论。

---

## 6. 已知缺口与待办（不静默忽略）

### 6.1 可复算性缺口：`artifacts/recon/round-recon.md` 在仓库中**不存在**

`experiments/gossip-third-party/DESIGN-preregistration.md:4` 写着：

> 本轮维度：勘测第一名「闲话八卦 / 第三方提及」（`artifacts/recon/round-recon.md` §7 🥇），由 Leader 指定，不换题。

复算结果（本轮实测）：

```bash
grep -rn 'artifacts/recon' --include=*.md .          # 仅命中上面这一行（+ .worktrees 副本）
find . -name 'round-recon*'                          # 无输出
grep -n 'artifact' .gitignore
# /artifacts/   ← 根锚定忽略，README §仓库内正式路径清单明令「不要在仓库根新建 artifacts/」
```

⇒ **该文件不在本仓库**（很可能留在前序会话工作区），`artifacts/` 目录亦被 `.gitignore` 根锚定忽略。
**处理方式（本轮选择「记为已知缺口」而非改他人文档）**：不改 `experiments/` 下在途文档（G1 系列仍在推进，改动归属不清）；
在此登记为 **已知缺口 G-1**：*「勘测第一名」这一选题依据目前**不可复算***，若要长期沿用，需把该侦察文档落进仓库正式路径（`reports/` 或 `v2/evidence/`），或由 Leader 重新给出选题依据。

> 本报告自己也**不引用**该文档作为依据 —— 本轮选题依据是 §1.1 的 `grep` 零命中 + `life_v2.json` 的 `enabled=true`，**两者都可复算**。

### 6.2 `obs llm-cost --cache-dir` 会污染验真判据（实测坑，记一笔）

一旦传 `--cache-dir`（如空目录），`provider_guard.by_provider` 会变成 **freeze 缓存**统计（空 → `{}`），
从而 `ok=false, problems=["by_provider 为空…"]`，**即使 `engine_log` 里明明是 `openai_compat: 2878`**。

⇒ **验真时不要传 `--cache-dir`**（与 `v2/evidence/a1_llmcost_ae969198.txt` 的既有用法一致）。
这条直接影响「真 LLM 验真」这一步能否 PASS，故列为本报告可复算性的一部分。

### 6.3 工作区既有脏改动（**本轮未触碰，列为待办**）

```
 M tools/d2/emit_run_meta.py
 D v2/evidence/run_d4_P1_n16r12/{batch.pid,cgroup.txt,heartbeat.tsv,host.log,meta.json,preflight.txt}
?? v2/evidence/g1_launch_evidence_b0.txt
?? v2/evidence/run_dr_round1_arm-ctrl_n16r60_seed42/
?? v2/evidence/run_g1_b0_n16r60_seed42/
```

这 **10 项**是前序在途工作（1 处未提交脚本改动 + 6 个已跟踪证据文件被删 + 3 个未跟踪新证据），
**归属不明确，本轮一律未动、未提交**（严禁 `git add -A` / `commit -a`）。
⚠️ 其中 `v2/evidence/run_d4_P1_n16r12/` 的 6 个删除**是真实的数据丢失风险**：该目录的 16×12 探针批已被 `timeout` 收割，
若原文件未备份，`git checkout -- <该目录>` 是唯一恢复路径。**建议由起批人确认后再处理。**

### 6.4 其它缺口

- **P5 派生图脚本未入库**（§4.3）：`/tmp/f2_chart.py` 只存在于本机 `/tmp`，重启即失。**建议下一轮补入库到 `tools/f2/`**。
- `tools/f2/memory_drift_report.py` 与既有 `code/obs/life.py` 存在**口径重叠但不重复**：后者已提供遗忘分级计数/保留度直方图/固化计数/漂移 by_dim；本脚本只补它没有的（存活率按 `replay` 语义、R×年龄曲线、睡前睡后召回对照、逐 agent L2/cosine、睡前后行为差、装配层 DROPPED 审计）。两者可交叉验证：`retrieval_hit_rate=0.983333` 同义（16/960 空检索）。

---

## 7. 下一步

| 优先级 | 动作 | 理由 | 建议归属 |
|---|---|---|---|
| P0 | **修 `integration.py` 的 `consolidate` 白名单**（把 `text` 纳入，或改在 `_do_memory` 内直接写 SM 记忆并 `MEMORY_WRITE`） | 缺陷 ① 让「固化」这一支**实际未生效**，不修则固化永远不可评估 | 下一轮开新分支，单变量改动 |
| P0 | **`sleep_end` 回填 `drift_permille/pf0/pf_t`** | 缺陷 ② 让睡眠事件不能当快照源；改动极小、收益直接 | 同上（可与 P0-1 同分支，但需声明两处改动面） |
| P1 | **设计「睡眠巩固」的正向对照**：同一 `presleep` 集合，比较「经过一次睡眠」vs「经过同等 round 数但不睡眠（消融 `sleep.enabled=false`）」的召回 | 现设计只能证明「无增益」，无法分离「新近性偏置」与「睡眠无效」 | 需 Leader 批两臂（sell: 每臂 ~75 分钟） |
| P1 | 把 `f2_chart.py` 入库到 `tools/f2/`，补齐 P5 的脚本缺口 | §6.4 | 一行级 |
| P2 | 确认 `run_d4_P1_n16r12/` 那 6 个被删文件是否需恢复 | §6.3 数据丢失风险 | 起批人 |
| P2 | 把 `round-recon.md` 落进仓库正式路径，或将「勘测第一名」依据写成可复算形式 | §6.1 缺口 G-1 | Leader / G1 负责人 |

---

## 8. 证据索引

| # | 结论 | 层级 | 来源 | sha256 | sha8 | 复现 |
|---|---|---|---|---|---|---|
| E1 | 机制在跑：80 睡眠窗 / 38976 遗忘 / 1267 固化 / 105 漂移 | 已证实 | `v2/evidence/run_g1_b0_n16r60_seed42/run.jsonl` | `6db62e8a3b926af7755fe220a5e8361c851e195d94afff00d16c00e7e1d0c983` | `6db62e8a` | §4.5 ③ |
| E2 | 存活率 0.931005、分级明细、R 域 [182,598] | 已证实 | 同上 | 同上 | 同上 | §4.5 ③ |
| E3 | 睡后召回 1.33% vs 对照 6.59%（−5.26pp） | 阴性 | 同上 | 同上 | 同上 | §4.5 ③ |
| E4 | 漂移 14/16、最大 10‰、L2≤2.236 | 已证实（量级受限） | 同上 | 同上 | 同上 | §4.5 ③ |
| E5 | 阴性结果可复现（交叉臂） | 已证实 | `v2/evidence/run_dr_round1_arm-ctrl_n16r60_seed42/run.jsonl` | `99c92d4b00e48bc629f064e0c10782e0248147451bf5ee44e29e2fd40d93b5bd` | `99c92d4b` | §4.5 ③ |
| E6 | 真 LLM 验真 PASS（2878 调用、degraded=0） | 已证实 | `v2/evidence/f2_llmcost_g1_b0_6db62e8a.txt` | 见文件 | — | §4.5 ② |
| E7 | 交叉臂验真 PASS（500513 tokens） | 已证实 | `v2/evidence/f2_llmcost_armctrl_99c92d4b.txt` | 见文件 | — | §4.5 ② |
| E8 | 四视图真拍（P1–P4） | 已证实 | `v2/evidence/f2_shots/*-{chat,rhythm,spread,600}-6db62e8a.png` | 见 §4.3 表 | `6db62e8a` | §4.5 ④ |
| E9 | F-2 时间线派生图（P5） | 已证实（脚本未入库） | `v2/evidence/f2_shots/*-f2sleep-6db62e8a.png` | `7685525a0ec36b93…9fadcd61` | `6db62e8a` | §4.3 |
| E10 | 渲染日志 4/4 SHOT OK、blank_retries=0/2 | 已证实 | `v2/evidence/f2_shots/render.log` | 见文件 | — | §4.3 |
| E11 | 指标脚本可被第二人原样跑出 | 已证实 | `tools/f2/memory_drift_report.py`（`aa0078d`） | 见文件 | `TODO（源码随提交变动）` | §4.5 ③ |
| E12 | 固化 `text` 被丢弃 1267 条、SM 写入 0 | 已证实（缺陷） | `code/life/agent.py:1218-1221` → `code/orchestration/integration.py:426-434`；源数据 E1 | `TODO（源码随提交变动）` | — | `--out-dir` 的 `anomalies.json` |
| E13 | `SLEEP_COMPLETED` 漂移字段 80/80 null | 已证实（缺陷） | `code/life/agent.py:1232-1233`；源数据 E1 | `TODO（源码随提交变动）` | — | 同上 |
| E14 | 截图复现输入（未入库，1.9 MB） | 派生 | `code/frontend/sample/dialogue_run_g1_b0_n16r60_seed42/threads.json` | `8b6f51701fbaba58ebd83ccb76614813b16fff62b01551f62f96c0be2840ff5e` | — | §4.3 ① |

---

## 附：署名与引用

AI 小镇 · 对话体验与研究发布小队（JiuwenSwarm 多智能体团队）. 2026. *R10 · 睡眠—遗忘—人格漂移：首次可观测化*.
项目仓库 `social-experiment`，证据入库提交 `aa0078ddc0c792a9edd41734521a11f8b2c72abc`。
本报告不含「首次」「业界领先」这类表述；凡结论均限定在「本配置、本规模、本 seed」内。
