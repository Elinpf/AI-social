# 分支说明 · `feat/l7-structural-dedup`（R17 · L-7 结构臂）

- 基线：master `9a7ea1a`
- 目标：把 L-7（8-gram 近重复率）的治理从「**生成后撞车重试**」前移到「**生成前的结构性约束**」
- 开关：`LIFE_PROMPT_L7_STRUCT`，**本分支默认 ON**（处理臂）；`0/false/no/off` 关闭
- 预注册观测项：`docs/forensics/2026-10-22-l7-structural-prereg.md`（跑批前落盘，口径不许改）
- OFF 路径自证：`docs/forensics/l7s_off_path_check.py` + 输出 `docs/forensics/2026-10-22-l7-structural-off-evidence.txt`

> **合 master 前必须把 `LIFE_PROMPT_L7_STRUCT` 改为默认 OFF，与 G-1/F-6/DEQUP/F-3/F-4 范式对齐；
> 否则机制会在后续所有维度跑批中默认生效，造成跨轮污染。**

---

## 1. 为什么这是「治根」而不是「治标」

| | R12 DEQUP（既有） | R17 结构臂（本分支） |
|---|---|---|
| 约束时机 | **生成后**：台词已经套路化了，检测到 8-gram 撞车 | **生成前**：先定「这一句怎么组织」再让模型写 |
| 手段 | 把撞车的那句回喂，要求重写 | 开口方式/收束方式确定性轮转 + 禁忌开头清单提前下发 |
| 代价 | 每次撞车多 1 次 LLM 调用（R12 实测 retries=88=collisions=88，重试率 17.25%） | **0 次额外调用**（`_dequp_body` 在结构臂 ON 时直接返回原 body） |
| 成败取决于 | **重试那一次抽样是否碰巧躲开** | **结构是否真的把共享前缀拆开**（可离线度量「约束遵守率」） |
| 可复现性 | 重试是第二次 LLM 抽样 ⇒ 同 seed 也可能不同 | 指派是 `sha256(入参)` + **零进程级状态** ⇒ 同 seed 逐字节一致 |

根因判断（事实依据：`docs/forensics/2026-10-22-repo-state.md` §6.3）：
四轮「加机制 ⇒ L-7 上升」的共同形态是——**凡是给模型新增可说的内容，模型就复用同一批开场/收尾套路**。
所以在**生成之后**做去重，本质是在跟「已经产生的套路」赛跑；而在**生成之前**把套路空间切开
（这一句必须用哪种开口、哪种收束、哪几个开头不许用），才是在源头减少套路。

## 2. 改动文件与行号（最终 HEAD）

| 文件 | 位置 | 改动 | 性质 |
|---|---|---|---|
| `code/life/l7_structural.py` | 新增（213 行） | 结构臂全部逻辑：`STRUCT_ENV` `:48`、`enabled()` `:88`、`assign()`、`plan()`、`render()`、`recent_bodies()`、`audit()`、`normalize()/shingles()` | 新文件 |
| `code/life/agent.py` | `:35` | `from . import l7_structural as L7S` | import |
| `code/life/agent.py` | `:1289–1311` | 新增 `_l7_struct_line()`：算出并渲染本条结构约束（取材 = `wv.visible_events`） | 新方法 |
| `code/life/agent.py` | `:1325` | `_dialogue_prompt()` 插入一处结构段 | 单点插入 |
| `code/life/agent.py` | `:1345–1347` | `_reply_prompt()` 插入一处结构段；新增 `turn` 关键字参数（默认 `None` ⇒ 兼容既有调用） | 单点插入 |
| `code/life/agent.py` | `:1046–1048` | `_send_reply()` 传入真实 `turn`（线程内序号，用于确定性指派） | 单行 |
| `code/life/agent.py` | `:964–969` | `_ctx_snapshot()` 追加 `ctx.l7struct` 审计键（additive） | 审计 |
| `code/life/agent.py` | `:989–990` | `_dequp_body()`：结构臂 ON ⇒ **不重试**，直接返回 body | 行为切换 |
| `code/tests/test_l7_structural.py` | 新增（242 行） | 16 条断言：默认 ON/env 可关、单变量插入、确定性与分布、口径镜像、无进程级状态、零额外调用 | 新测试 |
| `code/tests/test_anti_repeat.py` | `:41–49` | 新增 autouse fixture：把结构臂关掉，保证 DEQUP 单测仍是单变量 | 测试隔离 |
| `docs/forensics/2026-10-22-l7-structural-prereg.md` | 新增 | 预注册观测项（跑批前落盘） | 证据 |
| `docs/forensics/l7s_off_path_check.py` | 新增 | OFF 路径离线自证脚本（零跑批、零 LLM） | 证据 |
| `docs/forensics/2026-10-22-l7-structural-off-evidence.txt` | 新增 | 上述脚本的真实输出（11 项检查全 true） | 证据 |

**未改动**（硬约束自查）：
- 未改 `code/config/*.json`（⇒ `engine_version` 指纹不变）；
- 未改 `engine/` 任何文件（⇒ `state_hash` 语义不变）；
- 未改 `dialogue_threads.py::DEFAULTS`（配额 `max_messages_per_slot=2` 未动，**没有走「配额 2→3」那条路**）；
- **未改 R15 的收尾指令**（两个提示词末尾那句 A1 措辞臂逐字节保留，由
  `test_l7_structural.py::test_on_prompts_differ_by_exactly_one_segment` 的 `endswith` 断言守住）；
- 未改 `life/anti_repeat.py`（DEQUP 臂本体不动，只是被结构臂在 ON 时旁路）。

## 3. 设计取舍（为什么选这三条，而不是别的）

1. **不选「配额 2→3」**：配额在 `config/life_v2.json`，会进 `engine_version` 指纹，且与 L-7 天然正相关
   （话说得越多越容易重复），混变量后指标不可解释。Leader 已明确排除。
2. **不选「更强的事后改写」**：那仍是「先套路、后修补」，且每句都多花 token/调用。
3. **不选「把禁忌清单做成 8-gram 原文」**：8-gram 是归一化后的字符串碎片，直接塞进提示词会
   ①泄漏内部口径字样 ②模型读不懂碎片。改成「归一化前 4 字」的开头清单——信息等价（撞车绝大多数发生在开头），
   可读、可执行、可离线度量遵守率。
4. **开口/收束用确定性轮转而不是随机**：随机不可复现（同 seed 也未必同指派），而项目纪律要求「结论可复算」。
   `sha256` 指派保证：同一 (agent, day, slot, round, turn, mode, 对象) 恒得同一结构。
5. **不留任何进程级状态**（见 §4）：这是本轮踩到并修掉的真实坑。

## 4. 实现过程中踩到并修掉的一个坑（写清楚，免得后人重犯）

第一版的「最近台词窗口」是模块级 `deque`（照抄 `anti_repeat` 的写法），结果
`tests/test_periodic_flush.py::test_default_and_flush_produce_identical_bytes` 与
`tests/test_resume_from_flush.py::test_resume_from_flush_byte_identical` **两个字节级一致性测试直接红**：

- 前者在同一进程里连跑两次 `run_e2e` ⇒ 第二次继承了第一次的窗口 ⇒ 禁忌开头不同 ⇒ 台词不同 ⇒ 字节不同；
- 后者「续跑」时进程状态被重置，而一次性跑没有 ⇒ 同样分叉。

**修法**：禁忌开头的取材改为**从该 agent 的 `wv.visible_events` 现取**（内核已做可见性过滤、replay 天然可重建），
并把跨 run 的计数器从 `ctx.l7struct` 审计字段里删掉（只留 `open/end/n_banned/mode`）。
改完后上述两个测试转为通过，全量 595 条测试通过（见回报里的实测输出）。

结论：**任何会影响台词内容的机制都不能存放进程级可变状态**，否则 L-7 这类「同 seed 重跑」的证据链立刻失效。

## 5. 已知风险

| 风险 | 处置 |
|---|---|
| 模型无视结构指令（小模型常见） | 预注册里设了**伪证闸**：约束遵守率 > 50% ⇒ 即便 L-7 降也不可归因，本轮判「机制未生效」 |
| 6×4 结构本身变成新模板 | 预注册盯 `L-5 template_hit_rate`、`L-1` 长度中位数、`L-11/L-12` 互动性代理 |
| 禁忌清单 token 成本（约 +143 字符/条 ≈ 70 token） | 允许的代价，但需在 `obs llm-cost` 如实记录 |
| 默认 ON 造成跨轮污染 | 已写死「合 master 前改默认 OFF」这条必修项（见开头与预注册 §2） |
| 可见事件取材 ⇒ 孤立的 agent 禁忌清单为空 | 属预期：没听过别人说话就没得禁；`n_banned=0` 时整段省略，不浪费 token |

## 6. 回滚方式

- **运行时**：`export LIFE_PROMPT_L7_STRUCT=0` ⇒ 机制整体关闭。
  离线实证（`python3 docs/forensics/l7s_off_path_check.py`，`all_pass=true`）：
  `enabled=False`、`plan=None`、`render=""`、模块无进程级状态、两个提示词无结构段、
  `ctx.l7struct` 不出现、`_dequp_body` 退回原 DEQUP 路径；两态差异**仅一处插入**（143 字符）。
- **代码**：`git revert <sha>` 单 commit 即可。无配置迁移、无数据迁移、无 event schema 变更
  （`ctx.l7struct` 是 additive，读侧 `.get()` 缺省即降级）。

## 7. 跑批交接（给 evidence-runner）

- 默认 ON（`code/life/l7_structural.py:48` `STRUCT_ENV`，`:88` `enabled()` 取反判断）；
  取证时仍建议**显式** `export LIFE_PROMPT_L7_STRUCT=1`，不依赖默认值；
- 其余对话开关（`LIFE_PROMPT_GOSSIP_G1` / `LIFE_PROMPT_MEMORY_F6` / `LIFE_PROMPT_MEMORY_F6_DEQUP` /
  `HITT_DIALOGUE_*` / `HITT_OBSERVE_MSG`）**一律不设**；
- 期望 `retries=0`、`purpose="dialogue"` 调用数 == MSG 条数（重试已取消）；
- 每条 MSG 的 `ctx.l7struct` 形如
  `{"v":"l7-struct/1","open":0-5,"open_name":...,"end":0-3,"end_name":...,"n_banned":0-4,"mode":"initiate|reply"}`。
