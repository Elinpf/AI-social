# T359 · 居民调用轨迹视图 v1

## 第一步：数据源盘点（只读；T300 产物 + side）
| 层 | 有什么 | 缺 |
|---|---|---|
| 模型调用 | `LLM_CALL`（4797）：`purpose`(judge/importance/dialogue/negotiate/reflect/plan/describe) · model · tokens_in/out · cached · tier · thinking · provider · prompt_hash/cache_key | ⚠️**无 prompt/response 正文**（仅哈希，T227 捕获默认关）；⚠️**无法归到居民**（actor=SYSTEM、无 agent_id） |
| 对话 | `MSG_DM/PUBLIC/GROUP` 230 条，**`body` 正文内联**；from/to/place/scope/msg_id | ⚠️**无 topic/refs**（全空）⇒ 无延续结构 |
| 行为/事件 | agent 事件带 `agent_id`（PLACE_MOVE/ACTIVITY_*/RELATION_*/…） | — |
| 叙事正文 | `NARRATIVE` 20 → `body_ref` 指 `side/narrative/Pxxx/*.txt` | — |
| 关联链 | round/seq/actor（agent 事件含 agent_id） | LLM_CALL 例外（见上） |

## v1 形态（`code/frontend/trace.html`，自包含、无新依赖、只读）
- 左选**居民** + **回合区间**；页头**常驻数据缺口横幅**（3 条，不隐藏）。
- **上：时间轴两行** —— 模型调用（全体·按回合）/ 行为与事件（按居民·按回合）。
- **下：逐步列表**（时序）：① 模型调用(purpose+tokens+cached+tier) ② 居民事件 ③ 对话正文；**每行可点开看 出处**（来源=日志文件 + seq/type + 页面 sha）。
- **对话子页**（`?tab=conv`）：按人列消息正文+时间+from/to，**每条显式标「延续结构：无（topic/refs 为空）」**。
- 数据：**仓内真实日志** `sample/run_b2_n20_week.jsonl`（124,452 记录 · 居民 20 · 消息 81 · LLM 3975 · 载入 ~0.75s）；**无占位/样例冒充**。

## 明确看不到 & 为什么（如实）
1. **LLM 调用的提示词/响应正文** —— 日志只存哈希；`T227` 正文捕获默认关 ⇒ 参考图「工具参数→返回」层**做不出**（需你/用户定：是否对本地小样本开捕获）。
2. **LLM 调用按居民归属** —— `actor=SYSTEM`、payload 无 agent_id ⇒ 「模型」行**只能全体**（要按人需改世界层/捕获）。
3. **对话是否延续** —— `MSG` 的 `topic`/`refs` 为空 ⇒ **只能标"无延续结构"**，不假装有。

## 证据
`T359-trace-view.png`（轨迹）/ `T359-trace-conv.png`（对话）；页面/数据源可追（页头 sha + 每行出处）。

## 依 Leader 裁定补强（13:27）
- **样本 provenance**：页面角标标明 **「样本=B2 批（旧 epoch）· 非新基线 v2-T300」**（口径不混）。
- **缺口标注升级为"在路上的缺口"**：
  - ① LLM 正文：**正文层已预留位置**，未开启捕获（`T227` 默认关），**等用户点头即可填**（不必重做界面）；
  - ② LLM 归属居民：**按居民归属将在下一个 epoch 可用（`T360`/`T361`）**；
  - ③ 对话延续：**修复已在计划**（给消息加话题线，属 **tick 内时间的第三期**）。
- 数据仍为**真实日志**（无占位）。
