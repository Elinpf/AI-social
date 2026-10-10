# 事件卡规范（画法③ 混合卡）· 供 T86 Skill 并入

> 本文供并入 `skills/qingxi-pixel-art/references/CARD_METHODS.md` 的「事件卡」章节。
> 目标参考：`v1.2/evidence/style-refs/agentopia_events_ref.png`（Agentopia 20 张事件卡）。
> 样例：`assets/generated/event_cards_v2_sheet.png`；生成器：`frontend/tools/gen_event_cards_v2.py`（确定性）。

---

## 1. 卡片结构规范（四区）

一张事件卡 = **〔插画区〕 + 〔机制标注区〕 + 〔木牌标签〕 + 〔图标徽章〕**，尺寸 `300×224`（插画区高 168）。

| 区 | 位置 | 内容 | 约束 |
|---|---|---|---|
| **插画区** | 上部 300×168 | **扁平矢量几何场景**（天空渐变 + 地面 + 2–3 个几何小人 + 道具/符号） | **非动漫手绘**（本机无图像生成）；限色、扁平、无描边或 1px 深色描边 |
| **机制标注区** | 左上 136×84 | 白底半透明白板 + **机制标注**（见 §2） | Agentopia 卡的"灵魂"；1:1 可复刻 |
| **木牌标签** | 底部 300×46 | 木纹底板 + 中文名（19px 粗）+ 英文 slug（11px） | 木色 `#7a4a2b` + 木纹竖线 + 高光/暗边 |
| **图标徽章** | 右上 34×34 | 事件图标（取自 `icons_atlas.png`，键 = `EVENT_STYLE[].icon`） | 圆角深底 + 族色描边 |

卡片外框：`2px` 深色（`#181c2c`）+ 圆角 12。

## 2. 机制标注模板（5 种，可直接复用）

| 模板 | 用途 | 参数 | 示例 |
|---|---|---|---|
| **rel-bars** 关系维度对比条 | 展示关系维度（好感/尊重/协作）高低 | `rows:[(维度, 0..1)]` | 导师指导：尊重 0.85 / 好感 0.80 |
| **timeline** Day1–3 时间线勾叉 | 多日过程（提案/反提案/维护） | `days:[(标签, ✓/✗)], note` | 反提案：日1✗ 日2✓ 日3✓ |
| **equation** 算式 | 经济量（收入−支出=存款；40−35=5） | `parts:[(值或词, 运算符)]` | 稀缺抢购：40 − 35 = 5 |
| **ab-choice** 二选一对比 | 决策（地点/角色/接受婉拒） | `a:(词,✓), b:(词,✓), note` | 选址：音乐室✗ VS 日落天台✓ |
| **status** 状态条 | 标量（精力/技能熟练度） | `label, level 0..1, note` | 情绪耗竭：精力 0.2（Resting） |

**渲染要点**：白板 `rgba(255,255,255,.93)` + 轻投影；进度条底 `#e1e4eb`、填充用族色；勾 `✓` 绿 `#38a05a`、叉 `✗` 红 `#d2463c`；备注 10px 灰。

## 3. 单一真源对齐

- **图标**：`icons_atlas.png`（`assets_manifest.iconAtlas.atlas.index`，键 = `EVENT_STYLE[].icon`，69/69 对齐）。
- **清单**：`assets/generated/event_cards_v2.json` → `{id(slug), title_cn, title_en, icon, family, scene, annotation, file}`。
- **族色**：`FAMILY_COLOR`（ECON/LIFE/SOCIAL/COGN/SYS/WARN）。
- **确定性**：脚本无随机；素材只读；可复现。

## 4. 接入方案（前端展示层）

- **事件详情抽屉**：事件类型 → 卡 `id`（=英文 slug）→ 头图 `<img src="assets/generated/event_cards_v2/<slug>.png">`。
- **角色卡「最近事件」缩略墙**：按 `EVENT_STYLE[type].icon` ↔ 卡 `icon` 匹配，铺缩略图。
- **小镇日报**：每条故事用对应卡作配图（读 `event_cards_v2.json`）。
- **挂载点**：由 `frontend-dev` 接（`audit.js`/详情面板/日报渲染）；本文只定义资产与索引契约。

## 5. 诚实边界

插画区是**扁平矢量**，**不是动漫手绘**：无五官表情、动态透视、环境光影。Agentopia 卡的手绘质感**无法等价复现**，需**图像生成通道**（当前不可用：内网仅文本模型 `/images/generations` 404、`baoyu-image-gen` 挂起）。
**机制标注层**是本方法真正 1:1 复刻 Agentopia 的部分（关系条/时间线/算式/二选一/状态条）。

## 6. 生成与验证

```bash
cd code && python frontend/tools/gen_event_cards_v2.py     # 20 张 + sheet + json
node frontend/tools/smoke_test.js                          # 应 PASS（纯前端资产，不影响）
```
输出：`assets/generated/event_cards_v2/*.png`、`event_cards_v2_sheet.png`、`event_cards_v2.json`。

---

## 7. 手绘像素版（T89，用户倾向"都是手绘"）

按用户偏好，**插画区由"矢量扁平"改为"手绘像素场景"**（与小镇同源、同一像素语言），其余三区（机制标注 / 木牌 / 徽章）不变。

- 生成器：`frontend/tools/gen_event_cards_hand.py`（自包含、确定性）；输出 `assets/generated/event_cards_hand/<slug>.png`(20) + `event_cards_hand_sheet.png` + `event_cards_hand.json`。
- 插画区 = **peeps 像素角色 + 像素场景**（复用 AI Town/MIT 素材与固定哈希摆放）。
- **四区标注说明图**：`assets/event_card_annotated.png`（一张卡放大 + 四区箭头标注）。
- **20↔20 对照表**：`assets/event-card-mapping.md`（中文名/英文 slug/图标 key/机制标注类型）。
- **同事件对比**：`assets/event_card_vs_agentopia.png`（我们=手绘像素 vs 参考=动漫手绘）。

**边界（务必写清）**：插画区是**手绘像素**（像素语言内的手绘），**不是动漫手绘插画**；动漫手绘（五官表情/透视/环境光）本机无图像生成通道，**做不到**。

---

## 8. 机制标注区 = 三层（T118/T119 定稿）

机制标注区是**三层**（含状态色层）：

- **第①层 机制事实（聚合结果）**：4 模板 `rel-bars / equation / timeline / ab-choice / status`（对基准 5↔5 完备，见 `event-card-mapping.md §3`）。表达"**为什么算这个片段**"。
- **第①b层 状态色 / 分档**：**同一符号可复用**，**用颜色区分状态**（红=耗尽 / 绿=恢复中 / 黄=临界 / …）。
  - 依据（Agentopia 图1）：`Emotion Burnout` 电池=**红（耗尽）**+心碎；`Polite Rejection` 电池=**绿（充电中）**且引文 `Recharging Resting to survive.`——**颜色与引文互为印证**。
  - 价值：**不必为每个状态画新图标**，语义仍精确；**与 `ICON_ATLAS` 的"单一真源"天然兼容（同一图标 + `tint`）**。
- **第②层 一句叙事引用**：`quote = {text, quote_ref:{msg_id, seq, channel}}`
  - **只能引用日志里真实存在的 `MSG_*.body`**（**禁止美术/前端自造文案**）；
  - `channel ∈ {private, global, members}`（私聊/公开/群组；渲染可分档：私聊=低音量气泡 / 公开=公告条）；
  - **可溯源**：观测台里该引用**可点击 → 跳转/高亮源 `MSG_*`**（复用因果跳转）。
  - **口径澄清**：quote 是窗口内**代表样本**，**不是 episode 定义**；**"没有锚定 MSG ≠ 不存在该 episode"**。① 定义、② 举证。

## 9. 两档卡（T118 定稿）

- **① 片段卡 episode**（窗口内聚合，D 类可重算）：mentorship / emotion-burnout / diff-scoring / passion-salary / academic-collab / power-conflict / rel-acceptance / ice-breaking / rel-maintain。
- **② 事件卡 event**（单次 + 门控）：gift-giving / saving-money / polite-reject / counter-propose / group-proposal / scarcity-buy / combat-training / creative-collab / whispered-comm / skill-practice / select-location。
- **不配卡**：机械/高频（`RELATION_CHANGE`/`NEED_UPDATE`/`PLACE_MOVE`/`ACTIVITY_*` 逐次/`LLM_JUDGMENT` 逐次）。
- 门控权威：`v2/evidence/event_card_mapping_revised.json`（修订后 546 张，−97.6%）。
