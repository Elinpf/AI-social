# T118 · 事件卡映射语义与频次审计（含修订映射 + 量化预测）

> 输入：冻结 trunk canonical 真 LLM 日志 `v2/evidence/run_p1_final_n20_llm.jsonl`（**128564 事件**，N=20）。
> 范围：只出**审计表 + 修订映射（含门控）+ 文档**；`sprites.js` 由 frontend-dev 改、`event-card-mapping.md` 由 art-director 更新。**不改引擎/schema/事件类型**。
> 判据全 **D 类**、只读日志、可逐位重算。

## 1. 审计表（现行映射：`sprites.js EVENT_CARDS` 无条件 type→slug）

| 事件 | → 卡 | 语义一致? | 本周频次 | 处置 |
|---|---|---:|---:|---|
| `RELATION_CHANGE` | rel-maintain | **否**（任意关系变动≠维护） | **16716** | **取消默认配卡**；改门控 `gap>D_maint`（E20）或 `template=rel_maintain` = 32 |
| `NEED_UPDATE` | emotion-burnout | **否**（例行需求更新≠倦怠） | **3399** | **取消**；改 `STATE_CHANGE{to=exhausted}` = 0 |
| `ACTIVITY_STARTED` | combat-training | **否**（任何活动≠战斗） | 560 | 改 `template=combat_training` = 68 |
| `ACTIVITY_COMPLETED` | creative-collab | **否**（任何完成≠创作） | 540 | 改 `template=creative_collab` = 6 |
| `PLACE_MOVE` | select-location | **否**（走路≠选择） | 511 | 改 `template=select_location` = 22（或取消） |
| `LLM_JUDGMENT` | rel-acceptance | **否**（任何判定≠接纳） | 476 | 改**立场翻转**门控；当前 dim 无 accept/reject → = 4（见 §4） |
| `SKILL_LEVEL_UP` | mentorship | 需条件 | 79 | 改 `template=mentorship` = 32 |
| `SKILL_OUTPUT` | academic-collab | 需条件 | 10 | 改 `template=academic_collab` = 14 |
| `TRANSFER` | gift-giving | 需条件（非所有转账都是赠礼） | 31 | 改 `reason=gift` / `template=gift` = 62 |
| `DEPOSIT/WITHDRAW` | saving-money | 是 | 18/0 | 保留（或 `template=savings` = 36） |
| `MSG_DM` | whispered-comm | 是 | 164 | 保留；建议 `template=whisper` = 42（更贴 E6） |
| `SCORE_POSTED/RANKING_EMITTED` | diff-scoring | **需条件**（评分≠分歧） | 80/10 | 加**分歧门控**（本 run 分歧=0 → 0） |
| `MARKET_TRADE` | scarcity-buy | 需条件 | 23 | 加 `scarcity_index≥θ` 门控 = 23 |
| `SKILL_PRACTICE` | skill-practice | 是 | 77 | 保留 |
| `OFFER_REJECTED` | polite-reject | 是 | 11 | 保留 |
| `ROLE_CHANGE/OFFER_CREATED` | passion-salary | 需条件 | 9/21 | 保留 `ROLE_CHANGE`（9）；`OFFER_CREATED` 移出（泛要约≠权衡） |
| `NORM_PROPOSED/ADOPTED` | group-proposal | 是 | 19/19 | 保留一条（建议仅 `NORM_PROPOSED`=19） |
| `OFFER_COUNTERED` | counter-propose | 是 | 10 | 保留 |
| `CONFLICT_STARTED/RESOLVED` | power-conflict | 是 | 44/44 | 保留一条（建议 `RESOLVED`=88） |
| `RELATION_ENCOUNTER` | ice-breaking | 需条件 | 210 | 改 E19 门控（首遇∧familiarity<ε∧∃MSG）；或 `template=ice_break` = 12 |

## 2. 修订映射（门控条件，D 类可重算）

```jsonc
{
 "mentorship": "ACTIVITY_*{template=mentorship}",
 "creative-collab": "ACTIVITY_*{template=creative_collab}",
 "academic-collab": "ACTIVITY_*{template=academic_collab}",
 "combat-training": "ACTIVITY_*{template=combat_training}",
 "select-location": "ACTIVITY_*{template=select_location}（非 PLACE_MOVE）",
 "gift-giving": "TRANSFER{reason=gift} 或 ACTIVITY_*{template=gift}",
 "saving-money": "DEPOSIT/WITHDRAW 或 ACTIVITY_*{template=savings}",
 "whispered-comm": "ACTIVITY_*{template=whisper}（或 MSG_DM{visibility=private}）",
 "emotion-burnout": "STATE_CHANGE{to=exhausted}（本 run=0）",
 "diff-scoring": "同一 subject 的 SCORE_POSTED 分歧(≥2 且极差≥θ) 或 respect/affection 两维背向（当前维度缺失→0）",
 "scarcity-buy": "MARKET_TRADE{scarcity_index≥θ 或 reason=scarce_buy}",
 "skill-practice": "SKILL_PRACTICE",
 "polite-reject": "OFFER_REJECTED",
 "passion-salary": "ROLE_CHANGE",
 "group-proposal": "NORM_PROPOSED",
 "counter-propose": "OFFER_COUNTERED",
 "power-conflict": "CONFLICT_STARTED/RESOLVED",
 "rel-acceptance": "同一 agent→同一对象 accept↔reject 立场翻转（当前 dim 缺失→用 template=rel_accept）",
 "ice-breaking": "首次 RELATION_ENCOUNTER∧familiarity<ε∧∃MSG（或 template=ice_break）",
 "rel-maintain": "RELATION_CHANGE{a→b, gap>D_maint}（或 template=rel_maintain）"
}
```

原则：**机械事件（`RELATION_CHANGE/NEED_UPDATE/PLACE_MOVE/ACTIVITY_*`/`LLM_JUDGMENT`）默认不配卡**；卡片改由**活动 `template` / 语义条件**驱动；**宁可不显示，也不显示错的**。

## 3. 量化预测（修订前 → 后）

| | 卡图总数 | 说明 |
|---|---:|---|
| **修订前（现行）** | **23185** | 由 `RELATION_CHANGE=16716` + `NEED_UPDATE=3399` 等机械事件刷屏 |
| **修订后（门控）** | **546** | 见 §2 门控；每卡见 `event_card_mapping_revised.json` |
| **降幅** | **−97.6%** | 叙事卡占比由 ~1% 升至 **~100%（全部为有语义的卡）** |

修订后各卡预测：`{"mentorship": 32, "creative-collab": 6, "academic-collab": 14, "combat-training": 68, "select-location": 22, "gift-giving": 62, "saving-money": 36, "whispered-comm": 42, "emotion-burnout": 0, "diff-scoring": 0, "scarcity-buy": 23, "skill-practice": 77, "polite-reject": 11, "passion-salary": 9, "group-proposal": 19, "counter-propose": 10, "power-conflict": 88, "rel-acceptance": 4, "ice-breaking": 12, "rel-maintain": 32}`。

## 4. 需 art-director/frontend-dev 决策的两条（Leader 特别口径）

- **`rel-acceptance`（立场翻转）**：判据=**同一 agent→同一对象 `accept↔reject` 翻转**（或关系维度跃变）。**当前 `LLM_JUDGMENT.dimension` 无 `friendship_label/accept`（实为 `weekly_focus/rel_affinity/rel_familiarity/rel_trust`）→ 严格门控=0**。建议：**life 侧补 accept/reject 判定维度**后启用；临时可用 `template=rel_accept`（本 run=4）兜底。
- **`diff-scoring`（分歧）**：判据=**≥2 agent 对同一 subject 评分显著不一致**（本 run `SCORE_POSTED` 按 subject 聚合无分歧 → 0）**或** respect/affection 两维背向（**当前无这两维→0**）。建议同上：补维度后启用；**不要退化为"每次评分一张卡"**。

## 5. 交接

- **frontend-dev**：按 §2 替换 `sprites.js` 的 `EVENT_CARDS` 映射 + 在 `audit.js::_cardHtml` 加**门控判定**（模板/条件），机械事件不再直配。
- **art-director**：据 §1/§2 更新 `event-card-mapping.md`。
- 机器可读：`v2/evidence/event_card_mapping_revised.json`；本表：`v2/evidence/event_card_mapping_audit.md`。


---

## 6. 口径收敛（T123，**以脚本为准**）

**唯一复算命令**（一条命令出两个数 + 明细）：
```bash
cd code
python -m obs.recount_cards --log ../v2/evidence/run_p1_final_n20_llm.jsonl \
    --out ../v2/evidence/event_card_counts.json
```

**口径**：输入=日志；**只取 `e.type`**；**一个事件最多一张卡**；未映射事件不计入。
- 现行（无门控）= `sprites.js` **原 EVENT_CARDS 的 26 条 type 条目**逐事件计数。
- 门控 = `template→EVENT_CARDS→语义 switch`（与 `frontend/src/audit.js::eventCardSlug` **逐行一致**）。

**权威两数（脚本输出）**：**现行 = 23185** ；**门控（并集）= 612** ；降幅 **−97.36%**。

**其余数一律废弃**：
- `22,987` = 领导变体「每 slug 仅取一个 type」（少计双 type slugs 第二项 = **198**）→ 废弃（本脚本 `leader_variant=22987` 已复现该 198 的来源）。
- `616` = 门控旧版（含 `rel_accept` template +4；现 frontend 代码**已按反造假排除 rel_accept**）→ 废弃。
- `567` / `546` = template-only 变体（未含 `TRANSFER{gift}`/`DEPOSIT` 语义并集；546 另含 whisper=0）→ 废弃。

按卡门控明细：`{"academic-collab": 14, "combat-training": 68, "counter-propose": 10, "creative-collab": 6, "gift-giving": 93, "group-proposal": 19, "ice-breaking": 12, "mentorship": 32, "passion-salary": 9, "polite-reject": 11, "power-conflict": 88, "rel-maintain": 32, "saving-money": 54, "scarcity-buy": 23, "select-location": 22, "skill-practice": 77, "whispered-comm": 42}`。
