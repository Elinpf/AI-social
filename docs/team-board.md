# AI 小镇 · 团队看板（`docs/team-board.md`）

> 建立人：`repo-scout`（仓库侦察与看板官）｜建立时刻：2026-11-01 12:0x +08:00｜建立依据：本轮侦察报告 `docs/scout-round.md`
>
> **本看板是唯一"跨轮状态表"**。仓库里既有的 `v2/evidence/t361-post-unfreeze-todo.md`（解冻后待办）、`v2/evidence/t273-scope-guard-backlog.md`（门禁挂账）**不是**本看板，它们是单议题挂账；本看板按「维度」组织，不复述那两份文件的细节，只登记其作为待办来源。
>
> **看板纪律（沿用 `reports/README.md` 与本仓既有口径）**
> 1. 每条结论必须绑定 **commit sha**（`meta.json.code_sha` 或报告头部记录的树锚），无 sha 的结论一律不登记为「已推进」。
> 2. **机制接通 ≠ 效果成立 ≠ 生活气息提升**，三档不能互相顶替；状态词只允许：`已成立` / `未成立` / `不可判` / `部分有效（未达阈值）` / `机制未生效`。
> 3. 分母纪律：分母 < 30 **只报条数不报比率**；分母 < 68 一律 `probe=true`。
> 4. 新增一行必须同时给「证据目录（`v2/evidence/...`）+ 报告路径」，缺一不可。

---

## 一、已推进维度

> "已推进"= 有绑 sha 的证据产物，且状态词已定档。**不代表都拿到了正向效果**。

| # | 维度 | 开关 / 编号 | 状态词（原报告口径） | 证据位置 | 报告 | 绑定 sha（树锚） |
|---|---|---|---|---|---|---|
| 1 | 措辞层（压低括号旁白） | A1-措辞 | 真实但有副作用，不出效果结论 | `feat/wording-a1` | `reports/R9-wording-a1.md` | `a637371` |
| 2 | 对话往来密度 | `reply_window_rounds` 2→4（D9） | dead parameter（存在性事实） | `v2/evidence/d9_shots/` | `reports/R8-dialogue-density.md` | `05636bc` / `abefdf73` |
| 3 | L-7 套路化治理 | `LIFE_PROMPT_MEMORY_F6_DEQUP`（R12）/ `_V2`（R16） | BELOW_BAND（带外下侧，非改善结论） | `v2/evidence/l7_*` | `reports/R12-l7-dequp.md`、`R16-l7-dequp-v2.md` | `263a430` / `a851a8fc` |
| 4 | F-4 误会与和解 | `HITT_DIALOGUE_REPAIR` | 效果判「不可判」（L-13 守卫击穿） | `v2/evidence/f4_*` | `reports/R13-f4-repair.md` | `6b7ae8a` |
| 5 | F-3 情绪呼应 | `HITT_DIALOGUE_EMOTION_ECHO` | 机制侧成立；效果「不可判」（L-7 击穿） | `v2/evidence/f3_*`、`f3_shots/` | `reports/R14-f3-emotion-echo.md` | `6f87363` |
| 6 | G-1 第三方提及（八卦） | `LIFE_PROMPT_GOSSIP_G1` | 判失败、实现应回退（F2 一票否决） | `v2/evidence/r15-shots/`（口径已修订为「无图+渲染命令」） | `reports/R15-g1-gossip.md` | `5249209` |
| 7 | C-1 世界行进→对话 | `LIFE_PROMPT_WORLD_C1` | 接线 PASS / 效果「不可判」 | — | `reports/R17-worldline-c1.md` | `6602b77` |
| 8 | 睡眠—固化链路观测断点 | 修复（非新玩法） | 机制侧三项达成 / 端到端未验证 | `v2/evidence/fix-sleep-consolidation-20261022/` | `reports/R18-sleep-consolidation-fix.md` | — |
| 9 | 话题展开 / 多线索 | `LIFE_PROMPT_TOPIC_BREADTH` | 部分有效（方向为正·强度＝弱证据） | `v2/evidence/r19_topicbreadth_*` | `reports/R19-topic-breadth.md` | `dd0c2bc` |
| 10 | F-6 跨天记忆引用 | 固化链路 | 机制层已达成 / 行为层不可判 | `v2/evidence/f6_audit_20261022.md` | `reports/R20-f6-crossday-memory.md` | `c01f6dd` / `a6ae5e5` |
| 11 | F-8 处境/场景锚（scene-pair） | `LIFE_PROMPT_SCENE`（早期臂） | 主判定「不可判」（OFF 臂分母 0/191） | `v2/evidence/r21_scene_shots/` | `reports/R21-scene-pair.md` | `c75654e` |
| 12 | 独处 / 空闲 | S-1/S-2/S-3 | 能判（点估计级）/ 只可描述 | `v2/evidence/solitude_shots/` | `reports/R23-solitude-idle.md` | `f2bf606`（被读日志） |
| 13 | F-5 作息/习惯强度 | `HITT_LIVING_SLOT` | 部分有效（未达阈值）；判据设计缺陷 | `v2/evidence/f5_round1/` | `reports/R25-f5-habit-strength.md` | `d356a5b`（同树） |
| 14 | W-1 天气/季节感知 | `HITT_WEATHER` | 机制接通 191/191；主判据**口径敏感**⇒不宣称达标 | `v2/evidence/`（OFF `6fdaf1b7…` / ON `c572406e…`） | `reports/R42-weather-sense.md`、`CYCLE-44` | `c325f19`（OFF 跑时码树） |
| 15 | 公开面接话 | `HITT_DIALOGUE_PUBLIC_REPLY` | 机制层接通（ON 7/30 vs OFF 0/24）；效果层**不可判**（分母 <30） | `v2/evidence/r41v_public_talk_n16r24_s42/` | `reports/R41-public-talk.md`、`R41b-public-talk-verify.md` | `f365255` |
| 16 | **C1 处境锚（本轮主推）** | `LIFE_PROMPT_SCENE` | **机制层已成立**（`ctx.scene` 0/191 → 191/191）；**效果层已出读数：`不成立`** —— A0 `58/174=0.3333` vs A1 `56/165=0.3394`，`Δ=+0.61pp`，Fisher 双侧 `p=0.9090`（单批单 seed，点估计，不外推）。**判定合法性已核**：预登记卡 §5 五条不可判条件**逐条未触发**（条件1 要求任一臂 `judged<30`，两臂 174/165 均 ≥30）；但两臂均 `<68` ⇒ 读数**必须标 `probe`**（弱证据，禁写"显著/有效/生活气息提升"） | `v2/evidence/c1-scene-a0-..._n16r24_s42/`、`..._a1-...`、`v2/evidence/r46-c1-effect-metrics/` | `reports/R46-c1-effect-metrics-20261101.md`（`R45` 仍 DRAFT，勿引） | **`8b64615`（两臂同树）**；⚠️ R46 报告 sha **待提交后回填** |

> 周期报告族另计：`reports/CYCLE-<序号>-<日期>.md` 共 **49** 份（截至 CYCLE-48）。周期报告是「时间切片」，与上表的「维度切片」不互替。

---

## 二、待办维度

按「可立即开工 → 需前置条件」排序。

### A. 可立即开工（数据已在盘上，零新增跑批成本）

| # | 待办 | 现状 | 为什么现在能做 |
|---|---|---|---|
| **A-1** | **C1 处境锚：跑效果层读数、填 `R45`** | 两臂 A0/A1 **均已 `run_batch.rc=0`**、均真 LLM（`openai_compat` 2255 calls、`degraded=0`）、同一 `code_sha 8b64615`；机制层 `ctx.scene` **A0 0/191 → A1 191/191**（本轮实测）；`tools/metrics/c1_arm_compare.py` 已在库、预登记卡 `v2/refs/C1-scene-prereg-20261101.md` 已冻结 | 判据先于数据已就绪，只差把尺子跑一遍 + 补 §4–§8 + 真截图 |
| A-2 | `meta.assertions.code_unchanged_during_run` 恒 `null` | 两臂 meta 均为 `None`（无 EXIT trap 断言） | 属 `run_batch.sh` 加固，非本维度阻塞项 |
| A-3 | `msg_graph_degree.note` 文案硬化（N-1） | 写死「出边 0、孤立节点」，实测 `isolated_nodes=false` | 纯文案模板化，可小改 |
| A-4 | **`meta.switch_effective` 缺 `LIFE_PROMPT_SCENE` 提取器** | 两臂 `meta.json` 的 `switch_effective` 只有 4 个键（`HITT_DIALOGUE_EMOTION_ECHO` / `HITT_DIALOGUE_REPAIR` / `HITT_WEATHER` / `LIFE_PROMPT_ADDR_EVOLVE`）—— **`LIFE_PROMPT_SCENE` 这个键根本不存在**（不是 `null`）。⇒ 该臂开关生效**不能引用 meta**，只能用 `run.jsonl` 的 `payload.ctx.scene` 覆盖率（0/191 → 191/191）证明（`emit_run_meta.py:133/181` 是既有提取器范式） | 照 `_weather_switch_effective` 再写一个 scene 版即可，工具链内部缺口，非阻塞项 |

### B. 需前置条件

| # | 待办 | 卡在哪 |
|---|---|---|
| B-1 | 公开面接话分母扩到 ≥30/≥68（N-2） | 需 `rounds ≈ 55–60`（16 agents），且**先有行为改动再扩样本**，不为凑分母花钱 |
| B-2 | W-1 天气尺子词表假阳性（46%~50%） | 需重做词表 v3 或改人工剔除口径后再判；当前 PASS 余量仅 +0.13~+0.55pp |
| B-3 | F-5 生活节律 M1 结构上界 = +0.46875 < +0.50 | 判据设计缺陷（`evening` 落进 `LIVING` 计数集），需改判据而非改功能 |
| **B-8** | **C1 处境锚的锚点时序缺陷：`ctx.scene.place` 取的是移动前快照** | 【本轮实测】A1 `ctx.scene.place != payload.place` = **87/191 = 45.55%**；这 87 条**全部**满足「同 actor 同 round 内有先前 `PLACE_MOVE`」，且 `87/87` `ctx.scene.place == move.from_place`、`87/87` `payload.place == move.to_place` ⇒ **确定性时序问题，不是噪声**。落点 `code/life/agent.py:1576 _scene_line()`（场景行在移动事件之前取快照）。**结构分解（两臂完全一致）**：191 = **87 有同轮先前移动 + 104 无移动**（A0/A1 均 87/104）⇒ 受影响子集与开关无关、属实现层；但**不匹配只能在 A1 观测**（A0 无 `ctx.scene` 键，其 mismatch=0 是"无锚点"平凡真，不是"锚点正确"）。A1 的 104 条无移动发言中 anchor≠place = **0/104** ⇒ 缺陷**精确落在** 87 条有移动的那一侧。修法：`_scene_line()` 取快照前刷新，或直接改用当条消息的 `payload.place` | 【推断】修完后须重跑双臂才能判效果；单靠改代码不产生新读数。**复现器**：`python3 tools/metrics/c1_anchor_stale_check.py <arm>/run.jsonl`（零依赖单文件，输出 `anchor_mismatch=87 mismatch_rate=0.4555` / `anchor_eq_from_place=87 (100.00%)` / 两条判伪计数=0 + 87 行明细）。**⚠️ 实现陷阱**：比对 `from_place` 前**必须先限定"本轮有先前移动"**；不限轮次取"最近一次前置 `PLACE_MOVE`"会把 104 条无移动发言全判成假反例（`repo-scout` 实测 = 104 条）。**关于「12」的最终定档（`repo-scout` / `life-impl` / `run-observer` 三方各自脚本复算后一致）**：**`12` 本身可复算，但含义不是陷阱后果**——`12 = 87（错位总数）− 75（错位且进入判分母） = 26（A1 `no_cue`）− 14（`no_cue` 且锚点一致）`，即「**锚点错位但被 `no_cue` 排除在分母外**」的条目数。原先「不补 `AGENT_BORN.home_place` 兜底会产出 12 条」的**归因不可复现**（A1 的 191 条 scene 消息中"发言前无任何 `PLACE_ARRIVED` 历史" = **0**，兜底分支本批触发不了）⇒ **撤回的是归因，不是数字**。三个量分开记、不得互替：`104` = 陷阱后果（= 无本轮移动条数）；`12` = 错位∩`no_cue` 排除项；`89` = 无移动条目中 `anchor != home_place` 的条数 |
| **B-9** | C1 效果层分母偏小（A0 `judged=174` / A1 `judged=165`，其中 `no_cue` 17 vs 26） | 19/191 与 26/191 的发言命中不了冻结词表（`no_cue` 不进分母）⇒ 分母 < 191 且两臂 `no_cue` 差 9 条；预登记卡 §5 的不可判条里含"`no_cue` 占比差 ≥10pp"（本次 8.9pp vs 13.6pp，差 4.7pp，**未触发否决**，但已接近） | 若要扩词表须重新冻结 `lexicon_sha256` 并重算两臂，不能只改一边 |
| B-4 | `P-1b`：本地与 `origin/master` 分叉未评估 | 本轮实测 `origin/master...HEAD` = **98 / 57**（左=master 独有 98，右=HEAD 独有 57）；`origin/master` tip `2026-11-01 11:47:46` ⇒ 上游有推进，**未评估** |
| B-5 | `r44` 批中止原因未找到（CYCLE-48 F-A1） | 无 `run_batch.rc` / 无 `meta.json` / `host.log` 无 traceback；PID 835813 已消失 |
| B-6 | `T273` 提交范围守卫不清 index（挂账） | `v2/evidence/t273-scope-guard-backlog.md`，Leader 已裁定不自动 `git reset` |
| B-7 | `T361` 解冻后动作：跑 `make verify` | `v2/evidence/t361-post-unfreeze-todo.md` §2 |

---

## 三、每轮记录

| 日期（+08:00） | 轮次 | 维度 | 绑定 sha | 结论（一句话） | 记录人 |
|---|---|---|---|---|---|
| 2026-11-01 12:00 | R1-scout | 侦察 / 看板建立 | `8b64615`（HEAD）/ `d04b064`（origin/master tip 前） | 仓库地图 + 跑批/证据/obs 流程已还原；推荐本轮做 **C1 处境锚效果层读数**（零新增跑批） | `repo-scout` |
| 2026-11-01 12:11 | R46 | C1 处境锚（`LIFE_PROMPT_SCENE`）效果层 | 数据锚 `8b64615`（两臂同树）；R46 报告 sha **待提交回填** | **`不成立`**：机制层 `ctx.scene` 0/191→191/191（成立），效果层 A0 `58/174=0.3333` vs A1 `56/165=0.3394`、`Δ=+0.61pp`、Fisher `p=0.9090` ⇒ 未达预登记 `Δ≥+15pp` 且 `rate≥0.55` 双门槛；同时登记锚点时序缺陷 87/191（见 B-8） | 读数 `life-impl` / 独立复算 `repo-scout` |
| 2026-11-01 12:20 | R3+R4 | C1 处境锚（`LIFE_PROMPT_SCENE`）复核与定稿 | 数据锚 `8b64615`（两臂同树）；R46 定稿 sha：首交付 `dcf8c9d` / 勘误 `7a1cbbd` / 定稿见回填提交（§17.2） | **四条并列**：①机制接通 `ctx.scene` 0/191→191/191；②成本可测 2255 calls / `degraded=0`、dialogue `tokens_in` 63305→73040（+15.4%）；③效果层按预登记判据 **不成立**（A0 `58/174=0.3333` vs A1 `56/165=0.3394`、Δ`+0.61pp`、Fisher `p=0.9090`）；④根因 = **锚点时序缺陷 87/191（45.55%）** + **尺子不区分「提到」与「在做」**。措辞红线：只能写「本轮实现存在可定位缺陷，该假设尚未获得公允检验」，禁写任何方向性结论 | 复核/定稿 `run-observer` |

> 后续每轮追加一行。格式固定：`日期 | 轮次 | 维度 | sha | 结论 | 记录人`。**不得改历史行**，只追加。
>
> 历史周期（CYCLE-01…CYCLE-48）已有 `reports/CYCLE-*.md` 承载，本表不回溯搬运，避免两处口径漂移。
