# D2 · 消融成分边界表（A0 = 结构改造 + 必要适配）

> 用途：报告里 `prompt_sha(v0) ≠ prompt_sha(A0)` 的**逐项归因依据**。表外差异一律算「未声明改动」。
> 代码基线：`b79f07e`（before 臂，clean tree）→ D2 改动（本文所列）。
> 生成方式：`grep -n` + 人工核对，行号取自 D2 改动后的 `code/`。
> **v2（2026-10-20 17:30 修订）**：应 Leader 要求，把 `_dialogue_prompt`/`_reply_prompt` 里的**措辞优化句全部移出 D2**
> （「口语化的家常话 / 不要解释不要旁白 / 不要重复对方说过的话」已删除），D2 提示词层只保留「承载新字段所必需的引用方式替换」。
> 因此 B4/B5 的实质是「占位与引用」，不是「让话更好听」。

> ⚠️ **命名区分**：本表 `A1–A8` / `B1–B5` 是**成分编号**（逐项改动），与臂名 **`A1-措辞`**、**`A1-回复预算`** 无关，请勿混读。

## A. 结构层（不改变措辞的「通道」改造）

| # | 层 | 文件:行范围 | 函数/对象 | 改动内容 | 意图 | 影响指标 | 开关 |
|---|---|---|---|---|---|---|---|
| A1 | 结构 | `code/life/dialogue_threads.py:1-166`（新增文件） | 模块级纯函数 | 线程 id 规则、`core_name`/`build_display_map`、`mood_label`/`scarcest_need`、`is_replyable`、`thread_initiator`、配置装配 `load_params` | 线程化与语境快照的**纯函数**helpers，确定性、无 IO 副作用 | 全部线程指标（threads/mean_turns/max_turns）、L-12 | 无（模块被 import 即生效）；行为受 A6/A7 开关控制 |
| A2 | 结构 | `code/life/agent.py:97,115-121` | `LifeLayerAgent.__init__` | 新增 `peer_names` 形参 + agent-local 线程状态（`_slot_msgs`/`_thread_replied_turn`/`_replied_msg_ids`/`_round_replies`/`_pub_k`） | 承载「本回合说过什么、线程推到第几轮」 | 线程轮次、slot 消息上限 | 无（状态本身不改变行为） |
| A3 | 结构 | `code/orchestration/integration.py:165-190,824,840,863,869` | `_msg_uid` / `_thread_fields` / `KernelAdapter._do_social` | MSG_* payload 追加 `msg_uid`/`thread_id`/`turn_index`/`reply_to`/`participants`/`topic`/`ctx`；`msg_uid=<seed>:<预测全局seq>` | 指针无歧义（`msg_id` 跨 agent 会撞，保留原语义不动） | C7 指针完整性、reply_coverage、全部线程指标 | 无（`dialogue.enabled=false` 时 life 不产出这些字段，落盘仍走同一装配） |
| A4 | 结构 | `code/life/ports.py:65-78` | 契约常量 | 新增 `SOCIAL_THREAD_FIELDS` 与字段契约注释 | 契约单一真源，供前端/obs 对齐 | — | 无 |
| A5 | 结构 | `code/life/agent.py:746-960` | `_communicate`/`_pick_reply_target`/`_thread_history`/`_thread_max_turn`/`_send_reply`/`_initiate`/`_comm_limits` | 「先接话、再接不上就发起」的多轮生成；线程封口（`max_turns`、`reply_window_rounds`）+ 单 slot 消息上限 + 单回合回复上限 | 让一次对话能连续多轮 | 全部线程指标、MSG 条数、对话 LLM 调用数 | `dialogue.enabled`（默认 true）；`max_turns`(6)/`max_turns_per_round`(2)/`max_messages_per_slot`(2)/`reply_window_rounds`(2) |
| A6 | 结构 | `code/life/agent.py:359-368` | `_observe` | MSG_* 是否进记忆的消融开关 | 分离「纯措辞差异」与「措辞→记忆→检索→计划」的传导 | 下游一切由记忆传导的指标 | `observe.msg_enabled`（默认 **true**；关=`--override life_v2.observe.msg_enabled=false` 或 env `HITT_OBSERVE_MSG=0`） |
| A7 | 结构（**修订：不写配置文件**） | `code/life/dialogue_threads.py:20-90` | `DEFAULTS` / `OBSERVE_DEFAULTS` / `load_params` | 开关**默认值写在代码里**；配置来源优先级 = 代码默认 < `life_v2.json`（若存在该段）< `--override life_v2.dialogue.*`（运行期内存覆盖，不落盘）< env（`HITT_DIALOGUE_THREADS`/`HITT_OBSERVE_MSG`）。**`code/config/life_v2.json` 未新增任何键**。 | 见下方「方法论发现」：往 config 加键会改 `engine_version` 指纹 ⇒ RNG 全流改变 ⇒ 两臂不再是单变量 | — | 见 A5/A6 |
| A7′ | 方法论发现（不进代码） | — | — | **实测**：在 `config/life_v2.json` 加 `dialogue`/`observe` 两段后，同 seed/n/rounds 的 mock 日志 sha 由 `252db450…` 变为 `b979761d…` ⇒ `FINGERPRINT_FILES` 含 `life_v2.json` ⇒ 指纹变 ⇒ 世界轨迹整体改变。故**开关必须走 override/env，不得落盘**。当前配置与基线指纹相同（`WORLD_INIT.fingerprint` 两臂逐字相同），这是 A0 可比的底层保证。 | 保证「唯一变量」 | 全部对照 | —— |
| A8 | 结构（使能件） | `code/life/sleep_window.py:40-49` | `load_params` | `life_v2` 覆盖基底里加 `dialogue`/`observe` 两个**直通占位键** | 否则 `--override life_v2.dialogue.*` 在睡眠模块 fail-loud 报 unknown key（实测过 84×SYSTEM_ERROR） | 仅影响 override 可用性 | 无（不消费这两段） |

## B. 提示词层（A0 的「必要适配」——全部计入说明，供报告逐项归因）

| # | 层 | 文件:行范围 | 函数 | 改动内容 | 意图 | 影响指标 | 开关 |
|---|---|---|---|---|---|---|---|
| B1 | 提示词 | `code/life/agent.py:752-757` | `_name` | 把 `P0xx` 裸 ID 换成显示名（`青溪镇·老周`→`老周`；重名用角色称谓消歧） | 消除「P009，你说——」式台词 | **L-12 对端名出现率**（从 0 到有） | `dialogue.names_enabled`（默认 **true**；关=回退裸 ID，即 A0′ 消融臂） |
| B2 | 提示词 | `code/life/agent.py:958-966` | `_relation_line` | 对象后追加「（熟悉度{fam}/好感{aff}）」两个 int（取自 `_rel_cache`，不新增 world view 字段） | 关系亲密度驱动语气 | 语气/亲密度相关人评与 judge | 无独立开关（随 names 一起出现；`names_enabled=false` 时仍保留关系数字） |
| B3 | 提示词 | `code/life/agent.py:968-974` | `_mood_line` | 追加「情绪：{mood}；最紧的需求：{dim}={val}」 | 情绪/需求驱动语气 | 情绪呼应（F-proxy 人评） | 无独立开关 |
| B4 | 提示词（**已回退措辞改动**） | `code/life/agent.py:976-982` | `_dialogue_prompt` | 与基线**逐字相同的指令句**「请用一句话自然地说点什么。」；本行只保留「对象」由 `P0xx` → 「名字（熟悉度/好感）」的**引用方式替换** | 仅为承载新上下文（名字/关系/情绪）而改引用方式 | L-12 对端名出现率 | 无独立开关 |
| B4′ | 提示词（**已知成分重叠，本轮无法剥离**） | — | — | 曾写过的「口语化的家常话 / 不要解释、不要旁白式总结」**已删除**；D2 不再包含任何「让话更好听」的措辞优化 | 保证「措辞层效果」归因给 D4 | 旁白率(L-8)/自然度 | —— |
| B5 | 提示词 | `code/life/agent.py:984-995` | `_reply_prompt`（新增） | **只为承载新字段**的上下文装配：`你正在和{名字}聊「{topic}」。{情绪/需求}。刚才的对话：{最近≤3 轮，按名字}。` + **中性指令**「请接着说一句。」（**不含**任何口语化/防旁白/防重复等措辞优化，全部留给 D4） | 多轮往复的结构前提（无此段则无法承接） | 承接率（K-1）、线程轮次 | 无独立开关（由 A5 `dialogue.enabled` 整体控制） |

## C. 明确**不在**本轮的改动（避免归因串线）

- `config/social.json` 的既有配额（`dm_per_agent_per_round=3` 等）**未改**；`max_messages_per_slot` 只作用于 life 侧生成，不改内核配额。
- `max_messages_per_slot` 2→4 的候选**未进本轮**（Leader 裁决：会污染 A0 的单变量性；仅 mock 预研，留作 D2.1）。
- 经济结算 / 生命周期 / 世界层数值参数 / `world_director` 双事件 did（T372）**零改动**。
- `K`（`max_turns_per_round`）实测在本轮配额结构下**不构成约束**（K=2/3/4 三档 mock 结果逐项相同，均 666 MSG / 228 线程 / 平均 2.92 轮），真正的约束是 `max_messages_per_slot`。

## D. 复现方式（表外差异检查）

```bash
git diff --stat b79f07e <D2_sha>
git diff b79f07e <D2_sha> -- code/life code/orchestration code/config | grep -n "def _dialogue_prompt\|def _reply_prompt\|def _name\|def _relation_line\|def _mood_line"
```
报告若发现上表未列出的提示词层差异，按「未声明改动」降级处理。
