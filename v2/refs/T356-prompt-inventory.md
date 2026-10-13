# T356 提示词迭代线 —— 提示词面清单 + 迭代回路 + 口径边界

> 用户（13:10）：「现阶段我要持续迭代出更加人格化的提示词」⇒ 要的是**可重复的迭代回路**，不是一次性优化。

## 1. 提示词面清单（所有由提示词驱动的 LLM 调用）

`purpose` 白名单见 `freeze/config.py::ALLOWED_PURPOSES`；life 侧实际调用点如下：

| purpose | 提示词构建处（文件:位置） | 关键输入变量 | 能影响的行为 | 不经它改不了什么 |
|---|---|---|---|---|
| `plan` | `life/agent.py:413`（+ `_weekly_focus` 经 `soft.judge` 的 `weekly_focus`）| persona 压缩档案 + 当前目标 | 周计划措辞（**计划本身由 `Planner` 确定性**，prompt 不改结构） | 改不到：活动模板选择（确定性） |
| `reflect` | `life/agent.py:~560` | persona 档案 + 目标 + 记忆摘要 | 反思文本 →（经判据）漂移候选/`PERSONA_DRIFT` | 改不到：是否反思（阈值/窗口确定性） |
| `dialogue` | `life/agent.py:708` ← `_dialogue_prompt(tid, parts)` | persona 档案 + 场景 template_id + 对象 | `MSG_DM/PUBLIC/GROUP` 正文（措辞/口吻） | 改不到：谁对谁说/通道/配额（`_communicate` 结构） |
| `negotiation` | `life/agent.py:749` | persona 档案 + 目标 | 议价**措辞**（价格 `ask` 为确定性、非 prompt） | 改不到：价格/成交（内核确定性） |
| `importance` | `life/agent.py:938` | 观察文本 | 记忆 importance（定性打分） | 改不到：写入/去重（日志侧） |
| `judge` | `life/soft.py::judge` → `freeze`（`envelope`/`question_ref`/维度选项 `C.JUDGMENT_OPTIONS`） | 判定维度 + 上下文 + 候选选项 | 软判定标签（`LLM_JUDGMENT`）→ 关系/立场/漂移信号 | 改不到：数值后果（`delta_from_frozen_label` 确定性） |
| `narrate` | `life/soft.py::narrate` → `freeze`（`fact_event_seqs`） | 已决事件序列 | `NARRATIVE` 正文（affects_state=false） | 改不到：世界状态（纯输出） |
| `describe` | `freeze/llm_client.py:910`（涌现/叙事描述） | 事实上下文 | 描述性文字 | 改不到：世界状态 |
| `decide_t2` | 白名单内（T2 决策内容） | — | T2 意图/内容 | 改不到：结算 |

> **铁律不变**：LLM 只产**内容/条款/定性标签**；可行性/合法性/结算**全确定性**（`life/settlement.py` 不写死内容）。

## 2. 快速迭代回路（设计 + 最小实现）

**目标回路**：`改一版提示词 → 小样本跑（n=6–10 × 10–12 回合）→ 与上一版对比`，**同 seed、同配置、只差提示词**，每版**标版本号**。

- **装置**：复用 **`T227` prompt 正文落盘**（`freeze/capture.py::PromptCapture`，三态 `off/sample/purpose`，默认**关**；经 `LLMConfig.capture` 打开，`dir` 缺省 `<cache>/prompts`，含脱敏/限容/清理）。**不另建提示词捕获**。
- **对比口径**：① **行为差异族**（事件类型计数差、`state_hash` 差异回合）；② **生成正文并排**（按 `purpose` 抽同 `(agent,round)` 的 system/user/output）；③ **成本/缓存命中**（`LLM_CALL` 的 cost_units / `cached` 命中率）。
- **实现**：`tools/prompt_iter/prompt_iter.py`（本单新增；不改 `life/`/`engine/`）：
  - `run <tag>`：以 capture 打开、同 seed/config 跑小样本，产物落 `out/<tag>/`（日志 + `prompts.jsonl` + meta：`version_tag/seed/n/rounds/prompt_sha`）；
  - `compare <tagA> <tagB>`：打印行为差异族 + 正文并排 + 成本/缓存对比。
- **版本号**：`tag` 建议 `pNNN_<shortdesc>`；meta 记 `prompt_sha = sha256(被改提示词文件内容)`（与运行 sha 分开记）。

## 3. 口径边界（关键）

1. **改提示词 ⇒ `prompt_hash` 变 ⇒ `cache_key` 变 ⇒ 全部新答案**：`freeze/llm_client.py::_cache_key` **必含 `engine_version` 与 `prompt_hash`**（硬纪律）。⇒ 与"**改配置**"**同族**。
   - ⇒ **不得用整周跑批去试提示词**（成本/算力 + 会把缓存打散）；
   - ⇒ **提示词实验不得污染 `T300`/`T355` 基线**：**要么小样本、要么单独一包口径**（独立 side_root/cache）。
2. **不改世界语义文件**：只改提示词（措辞/上下文）；**若行为变，如实声明**，**不得写成"等价"**。
3. **不改 `config/` 语义键**（`criterion`/阈值等）—— 除非显式声明并通知 obs。
4. **证据绑 sha**：每版产物记 `prompt_sha` + 运行 `HEAD sha`。

## 4. 与 `T326`/`T333` 的界线
`T326`/`T333` = **情感词判据探针**（`life/emotion.py`，离线复算真样本）；**本单 = 提示词工作台**（改 prompt → 小样本 → 比对）。**不重复**。

## 5. 验收对应
- 提示词面清单 ✓（§1）；
- 回路可用 + **一次真实"改→跑→比"演示**：见 `tools/prompt_iter/` 与 `v2/evidence/T356-prompt-iter-demo.md`；
- 版本记录 ✓（meta `version_tag/prompt_sha`）；
- 与缓存/指纹关系 ✓（§3）。
