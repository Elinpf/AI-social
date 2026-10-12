# 数据管线设计（#10 轨迹 → 小模型训练/微调样本）

> 文档类型：**数据管线设计（只设计，不实现，不改 `code/`）**
> 作者：emergence-researcher｜日期：2026-10-12
> 目标（用户 #10）：*"产生的数据，能够作为训练下一个、参数量较小的模型使用，或者微调的样本"*
> 参照（米哈游路径，T207）：**SFT→RLHF→DPO→OPD + 三层 Hybrid Reward（rule/scalar/rubric）+ 多教师蒸馏 → 一个学生模型承载所有 NPC 人设**
> 对齐红线（Leader 2026-10-12）：**证据绑版本（sha+命令）· 口径唯一不复制 · 不确定标【未验证】· 不得造数 · 不得为好看而动世界语义**
> 证据约定：**【事实(代码)】**=可追溯到 `code/` 文件；**【事实(run)】**=取自真实 run `v2/evidence/run_t136_real_llm_canon_n20.jsonl`（N=20 canonical，130,296 事件）；**【已核实】**=已由 `freeze-layer-dev` 逐条确认（2026-10-12）；**【未验证】**=工程假设。
> 约束：**大文件/数据集不入库**（本文只给 schema + 小抽样）。

---

## 0. 结论速览（**先说限制，再谈形态**）

1. **最硬的限制（必须放在最前）**：**LLM_CALL 只落 `prompt_hash`、不落 prompt 正文；`freeze_cache/responses` 只落输出 `text`、也不落 prompt 正文** → **"有 output、无 input"** → **无法直接从 LLM 调用记录构造 `input→output` 训练对**。**【已核实】freeze-layer-dev 2026-10-12 逐条确认：prompt 正文本就不落盘、也不在别处落盘。**
2. **第二个限制**：**`LLM_JUDGMENT` 有 `decision`，但没有任何"真值/正确答案"**（只有 `envelope` 的阈值/选项）→ **不能做监督式 SFT**，只能做"与规则一致性"或需另造偏好的 RM。**【事实(代码)】**
3. **好消息**：**训练信号其实藏在"世界事件 + side storage 正文"里**，而不在 LLM 调用记录里——**对话正文（`MSG_*`）、记忆正文（`MEMORY_WRITE`→side）、反思正文（`MEMORY_REFLECT`→side）、叙事正文（`NARRATIVE`→side）**都带**可回溯的事件锚点**，且**无侵入可导出**。**【事实(run)】**
4. **最短路径**：**先用"对话/反思/记忆"三类**（有 input 有 output）做 **SFT 数据集导出**；**本机无 GPU → 现阶段只能导出 + 校验，训练做不了**。**【未验证：本机算力】**
5. **最大杠杆**：`judge` 占 **72.7% token** → **造 rubric-based/scalar Reward Model 替代大模型 judge**（对应 #10 + 降本），但**需先造偏好对**（现无真值）。
6. **与 #11**：拟人化评测的**可复算指标可同时当训练/reward 信号**；**人工 Likert 量表只作离线验收、不进训练**（避免主观污染）。

---

## 1. 数据源盘点（先盘点，逐项标注"能支持哪种训练信号"）

> 权威：事件 schema `v1.1/08-engine-stats-extension.md`；freeze 事件 `code/freeze/events.py`；缓存 `code/freeze/cache.py`；side storage `code/life/memory.py:130/151`、`code/life/agent.py:429`。

| # | 数据源 | 位置 | 含 input 正文？ | 含 output 正文？ | 含真值？ | **能支持的训练信号** |
|---|---|---|---|---|---|---|
| D1 | **事件日志（全量）** | `run_*.jsonl`（哈希链） | 部分（见 D4–D8） | 部分 | 部分 | 一切样本的**锚点与元数据**（`seq`/`round`/`actor`/`type`） |
| D2 | **`LLM_CALL`** | 事件；`code/freeze/events.py:llm_call_payload` | ❌（仅 `prompt_hash`/`meta_digest`） | ❌ | ❌ | **只能**做成本/用途/档位统计；**不能直接训练** |
| D3 | **`LLM_JUDGMENT`** | 事件 + `freeze_cache/judgments/*.json` | ❌（`context_digest`，`context_ref` 多为 null） | ✓（结构化 `decision`） | ❌ | **判别式样本但无真值** → 仅"与规则阈值一致性"、或 RM 的**伪标签/偏好**（需另造） |
| D4 | **对话正文 `MSG_*`** | 事件 `payload.body`（内联） | ✓（情境可由相邻事件重建） | ✓（`body` 正文） | — | **对话风格 / 角色口吻 SFT** |
| D5 | **记忆正文** | `MEMORY_WRITE` → `body_ref: side://mem/...txt` | 情境（`source_event_seq`/`subject`） | ✓（side `.txt`） | `importance`（0–10） | **记忆摘要 / 重要性打分 / 自传体记忆** |
| D6 | **反思正文** | `MEMORY_REFLECT` → `produced_mem_id`(side) + `triggered_by_mem_ids` | ✓（源记忆正文） | ✓（反思正文） | — | **反思样本（真正的 `input→output` 对）** |
| D7 | **叙事正文** | `NARRATIVE` → `body_ref: side://narrative/...txt` | ✓（`fact_event_seqs` 事实包） | ✓（叙事 body） | — | **叙事生成 SFT**（须过防幻觉门） |
| D8 | **观察 `OBSERVATION`** | 事件 | ✓（`target_event_seq`） | `salience` | `salience` | **显著性/注意力样本** |
| D9 | **关系/冲突/经济事件** | `RELATION_CHANGE`/`CONFLICT_RESOLVED`/`TRANSFER` 等 | ✓（结构） | 结构化结果 | 确定性结算 | **世界动力学/奖励 shaping 的中间信号** |
| D10 | **冻结响应缓存** | `freeze_cache/responses/<key>.json` | ❌（仅 `prompt_hash`） | ✓（`text`） | ❌ | **仅输出侧**；缺 input → 需配 D4–D7 才可用 |
| D11 | **嵌入缓存** | `freeze_cache/embeddings/` | — | 向量 | — | 检索/相似度（非训练标签） |
| D12 | **side storage 正文** | `side://mem|narrative|skill/...` | — | ✓ | — | 承载 D5/D6/D7 的**正文**（导出必读） |

**盘点结论（关键）**：
- **训练信号的主力是 D4–D7（世界生成的正文），不是 D2/D3（LLM 调用记录）**——后者**缺 input 正文、缺真值**，这是必须最先讲清的约束。
- **【事实(run)】真实 run 各源计数（N=20 canonical，130,296 事件）**：`MSG_DM` 165、`MSG_PUBLIC` 59、`MEMORY_WRITE` 47,742、`MEMORY_REFLECT` 140、`OBSERVATION` 47,424、`LLM_CALL` 4,814、`LLM_JUDGMENT` 1,010。→ **"带正文的对话/反思"量级是"百级/单 run"**，**要凑训练量必须跨 run/多种子累积**。

---

## 2. 样本形态（input→output schema + 真实抽样 + 无侵入性）

> 每个样本**必须带 `source_event_seq`（或 `fact_event_seqs`/`triggered_by_mem_ids`）**，作为可回溯锚点。

### S1 · 对话风格/角色口吻样本（**可无侵入导出**✓）
```
input:
  persona_card: {...}                 # 来自 life/persona.py（身份段）
  situation: {place, slot, participants[], relation_hint, recent_msgs[]}   # 从相邻事件重建
  recipient: <agent_id>
output:
  utterance: "<speech_style 一致的台词>"
meta:
  source_event_seq: <MSG_* 的 seq>
  actor/round
```
**【事实(run)】真实样例（`MSG_DM`，seq=81）**：
- output body：*"秀娘笑眯眯地递过一块刚出炉的桂花糕：\"来，尝尝看，做点心啊，最要紧的是心里装着吃的人，你多试几次就摸着门道了。\""*
- 元数据：`from=P004, to=P013, place=library, slot=morning, tag_hints=["mentorship"]`。
→ **可无侵入导出**：`MSG_*` 正文内联在事件里；情境从同 round/place 的事件重建。

### S2 · 反思样本（**真正的 input→output 对，最有价值**）
```
input:  source_memories: [ "<memory body...>", ... ]     # triggered_by_mem_ids → side://mem/*.txt
output: reflection_body: "<高层洞见>"
meta:   produced_mem_id, triggered_by_mem_ids[], importance_sum, agent_id, round
```
**【事实(run)】结构样例（`MEMORY_REFLECT`）**：`importance_sum=222`，`triggered_by_mem_ids` 为 **数十条**源记忆 id，`produced_mem_id="M-P001-000111"`（正文在 `side://mem/P001/M-P001-000111.txt`）。
→ **无侵入**：源记忆正文与反思正文都在 side storage，按 id 可读。

### S3 · 记忆重要性样本（**可无侵入导出**✓）
```
input:  memory_body: "<body>"; kind; subject
output: importance: <0..10 整数>
meta:   mem_id, source_event_seq
```
**【事实(run)】样例（`MEMORY_WRITE`）**：`{kind:"observation", importance:2, body_ref:"side://mem/P001/M-P001-000000.txt", source_event_seq:50}`。
→ 可用于训"重要性打分器"（替代/校验 `importance` 的 LLM 打分）。

### S4 · 叙事生成样本（**可导出，但须过防幻觉门**）
```
input:  fact_pack: [ {seq, type, payload-summary}, ... ]   # fact_event_seqs 锚定的事实
        style, pov
output: narrative_body
meta:   fact_event_seqs[], anchor_digest, style, pov, spec_flags
```
**【事实(run)】样例（`NARRATIVE`）**：`body_ref="side://narrative/P001/N-P001-0.txt"`，`fact_event_seqs=[120293,120294,120667,...]`，`affects_state=false`，`anchor_digest=sha256:0b0e...`。
→ **可用，但必须过 §3 的"不得编造事实"门**（对齐 `v1.1/17` H-1/S-4）。

### S5 · 判别/偏好样本（**现无真值，需另造**）
```
input:  context(或 context_digest 对应正文) + envelope{options/threshold}
output: decision
缺:     ground_truth / preference
```
**【事实(run)】样例（`LLM_JUDGMENT`）**：`decision="leisure"`，`envelope.weekly_focus.options=["work","social","study","leisure","balance"]`，`dimension="weekly_focus"`，`frozen=true`。
→ **不能做监督 SFT**；只能 ①统计"LLM 与规则阈值的一致率"，②用 **rubric（#11 可复算指标）** 造偏好对，训 **Reward Model**（见 §4）。

> **无侵入导出总表**：S1/S2/S3/S4 **均可**（读取事件 + side storage）；**不新增任何世界写入**。

---

## 3. 质量门（用我们自己的红线筛数据）

| # | 门 | 判据（可执行） | 依据 |
|---|---|---|---|
| **Q-1** | **不得含"把 directed 说成自发"** | 样本若含介入语句，必须带 `directed` 标签且叙述保留该标签；S4 叙事样本 `origin_mislabel==0` | `v2/00` 红线 A′ (a)、`v1.1/17` H-2/S-6 |
| **Q-2** | **不得含"编造事实"** | S4：每条断言句映射 ≥1 `fact_event_seq`，硬事实（金额/死亡/胜负/关系数值/时间地点）**逐字匹配**；`hard_fact_violations==0` | `v1.1/17` §3.3、`story_quality` Q-1/Q-6 |
| **Q-3** | **可回溯** | 每条样本 `source_event_seq`/`fact_event_seqs`/`triggered_by_mem_ids` **非空且 `seq` 真实存在** | 红线"证据绑版本" |
| **Q-4** | **冻结一致性** | 引用的 `LLM_JUDGMENT` 必须 `frozen==true`；样本记录 `model`/`prompt_hash`/`engine_version` | `code/freeze/events.py` 四要素 |
| **Q-5** | **去 mock / 去占位** | 过滤 `mock::` 前缀与占位正文（真实 run 才有价值）——probe 数据 `side_n50_probe` 含 `mock::` | `v2/evidence/side_n50_probe` |
| **Q-6** | **脱敏** | 导出前扫描密钥/隐私：**prompt 正文本就不落盘（天然低风险）**；但 `跨平台记忆`（T207 设想）可能含真实用户文本 → **导出前须过滤/匿名化**；禁止把 `api_key`/`credentials` 类字符串写入样本 | 红线段；**【未验证】** 需一次实测扫描 |
| **Q-7** | **许可/来源** | 样本仅来自**我们自己的 run**（自有数据）；若未来并入第三方（如 GA/AI Town），须按 `v2/refs/14` 的许可证结论 | `v2/refs/14-agent-impl-reuse-map.md` |

> **一句话**：**污染数据训出来的模型，会把"我们最想避免的东西"固化下来**——所以 Q-1/Q-2 是**硬门（不过即弃样本）**。

---

## 4. 训练路径（从现状到"小参数模型"的最短路径 + 现在做不了的）

### 4.1 最短路径（按性价比排序）
| 阶段 | 做什么 | 输入数据 | 现在能否做 |
|---|---|---|---|
| **P0 导出数据集** | 从 run 导出 S1/S2/S3/S4 为 **JSONL 数据集**（含锚点元数据），过 §3 质量门 | 事件+side storage | ✅ **能做**（仅导出，无 GPU） |
| **P0 造 RM（最大杠杆）** | 用 **rubric/scalar** 靶向 `judge`（72.7% token）：把 `judge` 判别改成 **rubric 逐项 score/noul**；用 S5 + 规则造偏好对，训 **Reward Model** 替代大模型 judge | S5 + #11 指标 | ⚠️ **半做**（可造数据集与 rubric；**训练需 GPU**） |
| **P1 SFT 小模型** | 用 S2（反思）+ S1（对话）做 **SFT**，得"人设/对话/反思"小模型 | S1/S2 | ⚠️ **半做**（可导出；**训练需 GPU**） |
| **P1 蒸馏** | 用大模型输出训小模型 | ❌ **缺 input 正文** | ❌ **现在做不了**（除非补记录 prompt） |
| **P2 RLHF/DPO/OPD** | 多教师/混合奖励（米哈游路径） | 需偏好对+基础设施 | ❌ **现在做不了**（无基础设施/无 GPU） |

### 4.2 明确**现在做不了**的（诚实清单）
1. **本机无 GPU → 不能训练**（只能导出数据集 + 校验 + 冒烟）。**【未验证：需确认机器规格】**
2. **无 prompt 正文 → 不能做完整 SFT/蒸馏样本**（LLM_CALL/responses 都缺 input）。要解，须让 freeze 层额外落 `prompt` 正文（**新任务，需 `freeze-layer-dev`**）。
3. **`LLM_JUDGMENT` 无真值 → 不能做监督判别**（只能 RM/一致性）。
4. **多教师/RLHF/DPO/OPD** 需训练基础设施与偏好数据 → 不在现阶段。

> **建议的"解锁动作"**：若要真正的 SFT/蒸馏，**唯一关键缺口是"prompt 正文落盘"**——请 `freeze-layer-dev` 评估"新增落 `prompt` 正文（可压缩/脱敏）"的代价。**这是把"能导出"变成"能训练"的开关。**

---

## 5. 判据：「数据够不够训」的可验收口径（不是感觉）

```
train_ready(dataset) =
      count(samples)               ≥ N_min[任务类型]
   ∧ diversity.persona_covered      ≥ P_min
   ∧ diversity.scene_type_covered   ≥ S_min
   ∧ consistency(风格/人设)          ≥ C_min          # 复用 T205 phrase_stability 等
   ∧ redline_violations            == 0              # §3 Q-1/Q-2
   ∧ traceable_ratio               == 1.0            # §3 Q-3
   ∧ mock_ratio                    == 0              # §3 Q-5
```
**建议初始阈值（【未验证】，待标定）**：
| 类别 | N_min | 说明 |
|---|---|---|
| SFT（风格/反思） | **≥ 1,000–10,000** 条 | 小模型 SFT 经验量级；**单 run 远远不够**（对话 ~224、反思 ~140）→ 需 **≥ 50–100 run × 多种子** |
| RM（rubric/scalar） | **≥ 5,000** 条偏好/打分 | 判别任务对量要求更高 |
| 多样性 | persona ≥ 20；scene_type ≥ 8；话题熵 ≥ 阈值 | 采自 `TAG_EMITTED`/`ACTIVITY_*` 分布 |
| 一致性 | 同 persona 跨样本风格稳定 ≥ 阈值 | 用确定性风格指标（T205 §4.2） |

**可验收做法**：每次导出**产出一份 `dataset_card.json`**（样本数/多样性/红线命中数/mock 比例/锚点覆盖率 + `source_run` sha + 生成命令）——**使"够不够训"是一张可复核的卡，而非感觉**。

---

## 6. 与 #11 的关系（拟人化评测能否同时当训练信号）

| #11 产出 | 能否作训练信号 | 说明 |
|---|---|---|
| **可复算指标**（regularity / act_entropy / deviation_rate / consistency / mood_volatility …，T205 §4.2） | ✅ **能**（作 **reward shaping / RM 特征**） | 从日志纯函数重算、确定性 → 可当**奖励信号**（对齐"三层 Hybrid Reward 的 rule/scalar 层"） |
| **人工 Likert 量表**（"像人"5 维，T205 §5.2） | ❌ **不进训练**（只作**离线验收**） | 主观、不可复算；进训练会引入不可审计标签（违红线） |

**结论**：**#11 的可复算指标 = 现成的 rule/scalar 奖励层**；**人工量表 = 离线验收闸**。二者分工、**不混用**。这正好对应米哈游 deck `[img-23]` 的 **Scalar-based RM + Rubric-based RM**——**我们的可复算指标就是 Scalar 层**。

---

## 7. 协作与已核实（**freeze-layer-dev 2026-10-12 逐条确认**）

- **【已核实】** D2 `LLM_CALL`：无 prompt 正文、无输出正文（T222 加了可选 `confidence/margin`，仍无正文）。
- **【已核实】** D10 `responses/<key>.json`：**有 output、无 input**（新增 `logprobs`）。
- **【已核实】** D3 `LLM_JUDGMENT`：有 `decision`，**无任何真值/正确答案字段**（`envelope` 仅 before/after/threshold/options/rng_branch）→ 只能做「与规则阈值一致性」。
- **【已核实】** `body_ref` 有现成 reader：`code/life/memory.py::SideStore.read_body(ref)->str` / `read_embed(ref)->list[float]`；`side://mem/<agent>/<mem>.txt`、叙事 `side://narrative/<agent>/<nid>.txt`。
- **【已核实】** `context_ref` 恒为 null → **上下文正文不落盘**（只进 `context_digest`/`prompt_hash`）。
- **解锁开关**：`T227`（freeze-layer-dev 主责）将补「**prompt 正文可选落盘**」（默认关、按 purpose 抽样、脱敏硬门），落地后可解锁**蒸馏/SFT 的 input 侧**。
- **需 `freeze-layer-dev` 评估**：为解锁 SFT/蒸馏，**新增落 `prompt` 正文**的代价与脱敏方案。
- **需 Leader 定**：是否允许"为训练而记录 prompt 正文"（涉及存储/隐私）。

---

## 8. 未验证 / 待确认

- **【已核实】** LLM_CALL/responses **确实完全不落 prompt 正文**（freeze-layer-dev 确认）。
- **【事实·重要】** **side 正文（`.txt`）未随 run 保留**：现有 canonical run 只留事件 `.jsonl`（含 `body_ref` 指针），盘上无 `side/` 目录 → **S2/S3/S4 依赖的正文当前不可导**（需重跑且保留 side，或先落 T227 的 prompt 正文）。
- **【事实·实测】** **S1（对话）可从现有日志直接导出**：在 `run_t136_real_llm_canon_n20.jsonl` 上实测得 **232 条**（过滤 `mock::` 后）；样例见下（示例 4 条）：
  ```json
  {"kind":"MSG_DM","from":"P004","to":"P013","place":"library","slot":"morning","tag_hints":["mentorship"],"utterance":"秀娘笑眯眯地递过一块刚出炉的桂花糕：“来，尝尝看，做点心啊，最要紧的是心里装着吃的人，你多试几次就摸着门道了。”","source_event_seq":81,"round":0}
  {"kind":"MSG_PUBLIC","from":null,"to":null,"slot":"morning","tag_hints":["skill_practice"],"utterance":"（刨花卷着木香落下）慢点，再慢点。","source_event_seq":61,"round":0}
  ```
  → **S1 走通"无 GPU 也能导出"，且与 §3 质量门兼容**（带 `source_event_seq`、可过滤 mock）。
- **【未验证】** 本机算力规格（是否无 GPU）。
- **【未验证】** §5 各阈值（N_min/多样性/一致性）为经验初值，需实测标定。
- **【未验证】** S1/S2/S3/S4 的**真实可用样本量与质量**（本文只抽样核对结构，未全量统计质量）。
- **【未验证】** 脱敏扫描的实现（Q-6）。
- 本文**只设计**，未改任何 `code/`，未入库任何数据集。

---

*（数据管线设计结束 — emergence-researcher；只设计、未实现、未入库数据）*
