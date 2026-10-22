# L-13 人话映射默认生效（`882e5dd`）· 独立核验 + 对 D12-C 的树漂移警告

> 作者：Leader（独立复核，非提交者自报）｜2026-10-23 07:30
> 起因：`882e5dd` 由 `life-evidence-analyst` 在 **2026-10-23 06:56:10** 提交，落在 **OFF 臂收尾（06:47:03）之后、ON 臂起跑（06:58:58）之前**，且改的是 `code/life`。

## 1. 先答最要紧的问题：**D12-C 两臂的树身份有没有被污染？**

**没有。** 证据：

| 检查 | 结果 |
|---|---|
| 跑批实际用的树 | `/tmp/t271-d12c-br/code`（来自 `feat/d12c-specific@a977cb0`） |
| `diff <(git show a977cb0:code/life/agent.py) /tmp/t271-d12c-br/code/life/agent.py` | **0 行差异** |
| `/tmp/t271-d12c-br/code/life/agent.py` mtime | **2026-10-23 05:55:17**（早于 OFF 起跑 05:57:04） |
| 结论 | **OFF 与 ON 两臂跑在同一份 `a977cb0` 代码上**，`882e5dd` 没有进入跑批树 ⇒ **单变量成立、两臂数据有效** |

⇒ 但**纪律上仍是一次越界**：跑批窗口（两臂之间也是同一实验窗口）内主树 `code/life` 被推进。**已按"树未污染"处理，不判数据作废**；后续请把「两臂之间的间隔也在冻结窗口内」写进 runbook（见 §4）。

## 2. `882e5dd` 是什么（它其实是**我们最想要的修复之一**）

修的是 **L-13 内部 token 泄漏**——正是 A5 人工抽检最差样本 **#11（`TH-P002-P007-40`，"台词里出现 `scarce_buy`"）** 的世界观硬伤。

改动：
- `code/life/agent.py::_topic_label`：从「依赖话题宽度臂开关」改为 **默认无条件人话化**（`TB.label(topic)`，未知 id 原样返回 ⇒ 不臆造、不丢信息）；
- 新增开关 **`LIFE_PROMPT_TOPIC_LABEL`**（默认 `on`；`off/0/false/no` 时**逐字节复刻旧实现**）⇒ 可做同树 OFF/ON 对照；
- `code/life/topic_breadth.py`：`TOPIC_LABELS` 补 **`burnout_event`**（`activity_templates.json` 20 个 template_id 的最后一个缺口）；
- 配套：`tools/d5/verify_l13.py`（确定性校验）、`test_l13_topic_label_default.py`（24 条单测）、`test_r19_topic_breadth.py` 3 处语义适配。

## 3. 我的独立核验（三条全过）

| 检查 | 命令 | 结果 |
|---|---|---|
| 确定性校验 | `python3 tools/d5/verify_l13.py` | **rc=0 / PASS**：A 覆盖 **20/20**、`unmapped=[]`、`token_hits=[]`；B **off 回退逐字节等价 23/23 × 2 态**、原字符串 20/20、`mismatches=0`；C 已封批 19 批 `ctx.topic` 覆盖 **11/11 话题、7,115/7,115 消息级 100%** |
| 单测 | `python3 -m pytest life/tests/test_l13_topic_label_default.py -q` | **24 passed in 0.36s** |
| 行为抽查 | `TB.label(...)` 直调 | `scarce_buy` → **「抢着买紧俏货」**、`whisper` → 「说悄悄话」、`burnout_event` → 「累过头想歇口气」、`combat_training` → 「练功」、`unknown_xyz` → **原样透传**；`label_enabled()` 默认 **True**，`off` 时 **False** |

**判读**：L-13 的正解成立——既修了泄漏，又留了「逐字节回退臂」这一可对照的退路，且未知 id 透传（不臆造）。这是本项目里少见的**默认值变更同时给出可复刻旧行为开关**的做法，可以直接作为后续改动的模板。

## 4. 由此产生的两条硬约束（**写进 runbook**）

### 4.1 树漂移：默认树从此**不再是** D12-C 的那棵树
`882e5dd` 之后，任何新批的提示词里 `ctx.topic` **已默认人话化**。所以：
- **要与 D12-C 两臂对照的任何新批，必须显式 `LIFE_PROMPT_TOPIC_LABEL=off`**，否则基线不同、比出来的差值是"两处改动之和"；
- 同理，**D12-C 的 OFF/ON 结果不可与 `882e5dd` 之后的任何批直接比较**，除非该批关了 label 臂。

### 4.2 两臂之间的窗口也在冻结范围内
本次「OFF 收尾 → ON 起跑」之间 11 分 55 秒内主树被推进（虽未污染跑批副本）。**规则收紧为：一次实验的两臂之间，主树 `code/{life,orchestration,config,engine}` 同样冻结**；要改就推到两臂都收完之后。

### 4.3 D12-C 数据里的 L-13 痕迹（**已知、已修，不属 D12-C 判据**）
D12-C 两臂都跑在 `a977cb0`（L-13 **未修**）上 ⇒ 若两臂日志里出现内部 token，属**该树既有的已知缺陷**，不构成对 D12-C 提示词改动的证据；引用 D12-C 原文样本时必须同时说明「该批早于 L-13 修复」。
