# 青溪镇词汇表（LEXICON）—— 全局权威名词表

> 文档类型：权威术语表（消歧）｜ 维护：design-synthesizer（方案汇总与成稿专家）
> 状态：v1（覆盖 v1.0 / v1.1 / v1.2 分册与 `code/`）
> 目的：把「避免歧义」从人工约定变成**可门禁的机制**。配套：
> - `lexicon.json`（机器可读，供检查器与工具消费）
> - `tools/lint_terms.py`（术语合规检查器：扫描 `social-experiment/**/*.md` 与 `code/**/*.py`，标出禁用/非规范叫法）
> - `lexicon-map.svg`（三层 + 三条角色带术语图，自包含）
>
> **纪律**：① 术语以**现有权威分册为准**（`v1/03`、`v1.1/00/06/07/08/09/12/13/15/17` 与 `00 §1.5`、`v1.2/01`）；② **不发明新术语**；③ 权威之间**本身矛盾**时**不自行裁定**，记入 §11「术语冲突清单」交 Leader 裁决。

> **历史快照说明**：`v1/**`（v1.0 分册）是**历史快照**，记录当时的决策与口径，**不强制改写**。
> 其中出现的旧称（`DISTRESSED/DECEASED/REVIVING`、单一 `life reward`、`sim-engine` 等）已冻结进
> `term_baseline.json` 基线，**不视为违规**；术语合规采用**棘轮模式**——`v1/**` 的已知历史违规不报错，
> **只有基线之外的新违规才失败**（见 §12）。活文档（`v1.1/**`、`v1.2/**`、`glossary/**`、`code/**`、`research/**`）
> 已清零违规。

---

## 0. 使用说明

### 0.1 词条字段
每个词条给出：**规范名**（英文标识符 + 中文名）｜**定义**｜**权威来源**｜**代码对应**｜**同义词 / 已废弃叫法（禁用）**｜**易混淆对**。

### 0.2 命名总则
1. **事件类型**：全大写 `SNAKE_CASE`（如 `ACTIVITY_STARTED`）；schema 权威为**最新版 `08 §1.2`**。
2. **字段/变量**：`lower_snake_case`（如 `day_type`）；类型为 `PascalCase`（如 `WorldView`）。
3. **生命周期状态**：**英文小写** 6 值白名单（`08 §5.9(5)`）。
4. **判定归属**：`D`（确定性）/ `F`（LLM 冻结）/ `N`（叙事）/ `R`（RNG 分支）。
5. **代码包**：以 `v1.2/01 §1.1` 蓝图为准（实现见 `code/`；若实现与蓝图分包不同，以蓝图命名 + 实测路径并列标注）。

### 0.3 权威来源速记
| 代号 | 文件 |
|---|---|
| 03 | `v1/03-engine-stats.md`（v1 内核/统计契约） |
| 08 | `v1.1/08-engine-stats-extension.md`（**事件 schema 权威**） |
| 00 | `v1.1/00-architecture.md`（**架构权威**，§1.5 角色带） |
| 06 | `v1.1/06-life-layer.md`（**枚举权威**） |
| 07 | `v1.1/07-emergence-observation.md`（**观测方法论权威**） |
| 09 | `v1.1/09-sandbox-v1.1.md`（**判据权威**） |
| 12 | `v1.1/12-event-lineage.md`（事件谱系/模板库） |
| 13 | `v1.1/13-wellbeing-metrics.md`（福祉指标） |
| 15 | `v1.1/15-event-census-spec.md`（事件普查规格） |
| 17 | `v1.1/17-narrative-layer.md`（叙事层） |
| BP | `v1.2/01-implementation-architecture.md`（**工程蓝图/包结构权威**） |

---

## 1. 时间体系（Time）

| 词条 | 定义 | 权威来源 | 代码对应 | 禁用/同义 | 易混淆对 |
|---|---|---|---|---|---|
| **round（回合 / tick）** | 引擎最小确定性节拍；裁决器每回合结算一次。从 0 起。 | `08 §3.1`、`03` | `engine/time.py`、`contracts.models.Round`、字段 `Event.round` | 禁用「帧/frame」；「tick」是**同义词**但文档统一用 `round` | vs `slot/day/week`（上层派生视图） |
| **slot（时段）** | 回合的上一层：`morning/afternoon/evening/night`；1 slot = 3 回合。 | `08 §3.1`、`00 §3.2` | `engine/time.py`、payload `slot` | 禁用「phase」（会被误认成 P0–P6） | vs `phase`（阶段 0–6/35）、vs `WEEK_PHASES`（PLAN…） |
| **day（日）** | 1 日 = 4 slot = 12 回合；含 `day_type`。 | `08 §3.1` | payload `day`、`day_type` | — | — |
| **week（周 / 模拟周）** | 1 周 = 7 日 = **84 回合**；项目**当前时间尺度单位**。 | `08 §3.1`、`00 §3.1` | `TIME_CONFIG` | 禁用「real week」 | — |
| **TIME_CONFIG（时间配置）** | 层级参数集合（`ROUNDS_PER_SLOT=3`/`SLOTS_PER_DAY=4`/`DAYS_PER_WEEK=7`/`DAY_TYPES`）。 | `08 §3.1` | `config/default.json`、`engine_version.time_config_hash` | — | vs `TIME_UNIT`（mono_ts 刻度） |
| **derive_time（时间派生）** | 纯函数 `round → {week,day,day_of_week,day_type,slot,tick_in_slot}`。 | `08 §3.1` | `engine/time.py`（D-1） | — | — |
| **TIME_MARK（时间锚点事件）** | 跨日/跨周时发出的审计锚点事件。 | `08 §1.2`、`00 §3.5` | 事件 `TIME_MARK` | — | vs `mono_ts`（字段） |
| **phase（阶段）** | 回合内阶段号：`0..6` 与 `35`（=Phase 3.5 LIFE）。 | `08 §2.1`、BP §2.0 | `contracts.models.Phase`、`Event.phase` | 禁用「slot」代指 | vs `slot`、vs `WEEK_PHASES` |
| **ROUNDS_PER_SLOT** | 每时段回合数，默认 **3**（**须 ≥3**，见 AR-D4）。 | `08 §3.1`、`00 §3.1` | `config/default.json` | 禁用缩写 `rps`（非规范） | — |

---

## 2. 确定性内核（Kernel / D0）

| 词条 | 定义 | 权威来源 | 代码对应 | 禁用/同义 | 易混淆对 |
|---|---|---|---|---|---|
| **D0（确定性内核）** | 「世界法则」层：时间派生、状态、裁决器、账本、RNG。**非 LLM**。 | `00 §1.2` | `engine/`（BP `engine/kernel/`） | 禁用 `sim-engine`（旧草稿名，已统一） | vs `L1`（生活层）、`L2`（观测层） |
| **Arbiter（中央裁决器）** | 唯一写入口；串行折叠 hook 链；**绝不调 LLM**。 | `03 §1.1`、BP §2.3 | `engine/arbiter.py` | 禁用「GM/Game Master」在日常引用中混用（可注明同源概念） | vs `freeze`（只产载荷，不写日志） |
| **Ledger（账本）** | append-only 哈希链事件日志。 | `03 §6.1`、`08 §5` | `engine/ledger.py` | 禁用「DB」 | vs `side_store`（侧存储） |
| **Event（事件）** | 账本记录单位（外壳 `seq/round/phase/actor/type/payload/mono_ts/prev_hash/hash`）。 | `03 §6.1`、`08 §1.1` | `contracts.models.Event`、`engine/events.py` | 禁用「log line」代指语义 | vs `StoryAtom`（叙事折叠，非事件） |
| **RoundBuffer（回合缓冲）** | 本回合「待提交缓冲区」；`emit` 入缓冲，**P6 COMMIT 唯一落盘**。 | BP §1.4/§3.1、ADR-08 | `engine/kernel.py` | 禁用「临时日志」 | vs `Ledger` |
| **turn_seal（回合封条）** | 每回合末封条：`first_seq/last_seq/round_hash/prev_seal_hash`。 | BP §3.2、`03 §6.1` | `engine/ledger.py`、`TurnSeal` | 禁用「checkpoint 快照」（那是 snapshot） | vs `Snapshot` |
| **replay（重放）** | `replay(log) = reduce(apply, EventLog, InitialState)`；**纯折叠，不重跑 hook、不重调 LLM**。 | `03 §6.2`、BP §1.4 | `engine/replay.py` | 禁用「rerun」 | vs `run(mode="first")`（首跑） |
| **Snapshot（快照）** | 状态快照缓存（每 K 回合节流），可丢弃重建。 | `03`、BP §3.5 | `engine/snapshot.py`、`kernel/state.py` | — | vs `turn_seal` |
| **RNG / rng.py（确定性随机）** | 层级化 SplitMix64；`draw(stream_id, round, seq, n)`；由 `(seed,stream_id,round,seq)` 唯一确定。 | `03 §1.4`、BP §1.4 | `engine/rng.py`（D-8） | 禁用「random」指代（内置 `random` 禁用） | vs `R`（判定归属=RNG 分支） |
| **canonical_json（规范 JSON）** | 键排序 + 无空格 + 定点（`round(x,6)`）→ SHA-256。 | `03 §6.1`、BP §4.4 | `engine/canon.py` | 禁用「JSON」单指（须说明规范） | — |
| **invariants（不变量）** | 守恒 + v1 五条 + `08` 六条 + `06` L1–L8 校验集。 | `03 §5.9`、`08 §6`、`06 §8.3` | `engine/conservation.py`、`engine/invariants.py` | — | — |
| **engine_version（引擎指纹）** | 复现输入常数集合指纹；重放前断言一致。 | BP §3.6 | `engine/version.py`、`config/engine_version.json` | 禁用「model version」（那是 `llm_models`） | vs `rule_version`（v1 规则版本） |
| **rule_version（规则版本）** | v1 经济/生命周期规则集版本号（写入日志）。 | `01 §6`、`03` | 日志字段 `rule_version` | — | vs `engine_version` |
| **hook（钩子）** | 裁决器 hook 链的纯函数单元：`(state,round,ctx)->Delta`。 | `03 §2.2`、`08 §2.2` | `contracts/hooks.py`、`engine/hooks/` | 禁用「callback」 | vs `IF-*`（层间接口） |
| **Delta（增量）** | hook 返回：`{state, events, pending_intents}`。 | `08 §2.3` | `contracts.hooks.Delta` | — | — |
| **Ctx（上下文）** | 传入 hook 的只读运行上下文；`ctx.rng()` 唯一随机源。 | `08 §2.2`、BP §2.3 | `contracts.hooks.Ctx` | — | — |

---

## 3. 事件与判定（Events & Judgment）

| 词条 | 定义 | 权威来源 | 代码对应 | 禁用/同义 | 易混淆对 |
|---|---|---|---|---|---|
| **原子事件（atomic event）** | 内核落日志的标准化事件（封闭 schema，`08 §1.2 A–K` + v1 表）。 | `15 §1`、`08 §1.2` | 事件类型全集 | 禁用「原始事件」 | vs **语义事件** |
| **语义事件（semantic event）** | 20 类高阶事件（E1–E20），由「确定性规则对日志做模式判定」得出，**不写回日志**。 | `15 §1`、`12 §1` | `obs/census.py` | 禁用「业务事件」 | vs 原子事件 |
| **事件族（event family, E-\*）** | 事件分组：`E-WORLD/E-ECON/E-LIFE/E-PLACE/E-SOCIAL/E-REL/E-MEM/E-EMERGE/E-STATE/E-AUDIT`。 | `00 §4.3`、`08 §1.2` | `08 §1.2` 分组 | — | ⚠️ **`E-*`（事件族） vs `E`（净值） vs `E1–E20`（语义事件）** |
| **判定归属 D / F / N / R** | `D`=硬内核确定性；`F`=软判定（LLM 冻结）；`N`=纯叙事；`R`=种子化 RNG 分支。 | `12 §0`、`00 §1.5` | `08 §1.2` 事件表标注 | 禁用「LLM 判定」指代 F 的全部（F 是冻结） | vs **指标分级 D/F/K**（三个字母重叠！F 含义一致，D/K 不同） |
| **LLM_CALL（LLM 调用记录）** | 成本审计事件（`agent_id,tier,model,tokens_in/out,trigger,purpose,degraded`）；**不改账**。 | `08 §1.2 G`、`17 §7` | `freeze/budget.py`、事件 `LLM_CALL` | — | vs `LLM_JUDGMENT`（判定） vs `NARRATIVE`（叙事）——**08 §1.2「三事件分列」** |
| **LLM_JUDGMENT（冻结定性判定）** | LLM 定性判定，**必带四要素** `decision/model/context_digest/frozen=true`；重放**不重问**。 | `08 §1.2 I`、`00 §5.5` | 事件 `LLM_JUDGMENT`、`life/softjudge/` | 禁用「LLM 打分」当判定 | vs `LLM_CALL`、vs `NARRATIVE` |
| **NARRATIVE（叙事事件）** | 叙事的**纯输出**载体，`affects_state=false`；`apply_event` 恒等折叠。 | `08 §1.2 I`、`17 §0.1` | `narrative/render.py`、事件 `NARRATIVE` | 禁用「story event」 | vs `LLM_JUDGMENT`（可影响派生数值） |
| **frozen（已冻结）** | 判定一旦落日志即冻结，重放只读回、不重算。 | `08 §1.2 I`、`00 §5.4` | `LLM_JUDGMENT.frozen=true` | — | — |
| **IF-1 … IF-7（层间接口）** | 7 条层间接口 + `IF-2b`（软判定）+ `IF-2c`（审计载荷）。 | `00 §4.1`、BP §2.1 | `contracts/interfaces.py` | 禁用「API」泛称 | **`IF-2`（提交意图） vs `IF-2b`（提交软判定） vs `IF-2c`（提交审计载荷）** |
| **Intent（意图）** | L1 产出的写入请求（`INTENT.*`），经 IF-2 校验才成事实。 | `00 §4.2`、`08 §4.2` | `contracts.models.Intent`、`life/intent.py` | 禁用「action」当意图 | vs **Event（事实）**（意图/事实分离） |
| **invariant 意图/事实分离** | 生活 hook 不返回货币 delta，只返回非货币状态 + `pending_intents`。 | `06 L-2/L8`、`03 P7` | `Delta.pending_intents` | — | — |
| **counterparty_id（对手方标识）** | 每笔 `TRANSFER/MARKET_TRADE` 必带字段，供反作弊。 | `02 §5.2`、`08 §2.3` | payload 字段 | — | — |
| **flags（反作弊标记）** | `{wash,cycle,self,mule,large,split}`；`W_wash=4` 确定性打标。 | `02 §5.1`、`08 §1.3` | payload `flags` | — | vs `flag=rescue`（救助标记，单数） |
| **INTENT_REJECTED（规则性拒绝）** | 非法场所/超容/超配额/非营业时段等**规则性**拒绝；不产生状态变化。 | `08 §1.2 H`、`00 AR-C1` | 事件 `INTENT_REJECTED` | 禁用「offered rejected」混淆 | vs **`OFFER_REJECTED`（社交性婉拒）** |
| **OFFER_REJECTED（社交性婉拒）** | 合法要约被对方**礼貌拒绝**；与 `INTENT_REJECTED` **并存且语义分离**。 | `08 §1.2 K`、`12 T14-C5` | 事件 `OFFER_REJECTED` | 禁用 `OFFER`（→ `OFFER_CREATED`） | vs `INTENT_REJECTED` |
| **OFFER 家族（协商）** | `OFFER_CREATED / OFFER_COUNTERED / OFFER_ACCEPTED / OFFER_REJECTED`。 | `08 §1.2 K`、`09 §7.1` | 事件族 | 禁用旧名 `OFFER`、`COUNTER_OFFER`（→`OFFER_COUNTERED`） | — |
| **SKILL_\*（技能事件）** | `SKILL_PRACTICE / SKILL_LEVEL_UP / SKILL_OUTPUT`（确定性结算）。 | `08 §1.2 J`、`13 WB-C1` | 事件族 | 禁用「skill event」泛称 | vs `GOAL_*` |
| **census / census_report（事件普查）** | 只读日志、确定性重算「发生了什么」的侧产物（含语义命中表/覆盖度）。 | `15 §3` | `obs/census.py`、`emergence/census` | 禁用「report」单指（见观测层 §6） | vs `metrics` / `emergence_report` |
| **cascade（级联）** | 从 `SEED_EVENT` 出发在窗口内可达的传播子图。 | `07 §2.1`、`15 §6` | `obs/emergence.py` | — | — |
| **R0（传播基本再生数）** | 传播者平均出度；`R0≥1.0` 判「自持」。 | `07 §2.2` | `emergence` | — | ⚠️ **`R0`（级联） vs `R-1..R-11`（风险） vs `R1–R7`（T9 铁律） vs `R2/R3/R4`（感知前置）** |
| **PERCEPTION_SCOPE（感知作用域）** | `{event_type -> visibility_class}` 表；`visibility_class ∈ {global,place_local,members,private,participants_only,subject_only}`。 | `08 §3.5`、BP §2.4 | `config/perception_scope.json`、`life/visibility.py` | — | — |
| **visible_events / heard_events（亲历/听说）** | 角色视角可见性：亲历（严格集）与听说（沿 `refs[]` 反向闭包，互斥）；`OBSERVATION` 仅为显著度证据。 | `17 §4.3`、`v1.2/03` | `life/visibility.py` | 禁用「OBSERVATION=可见全集」 | vs `OBSERVATION`（事件） |

---

## 4. 经济与死亡（Economy & Lifecycle）

| 词条 | 定义 | 权威来源 | 代码对应 | 禁用/同义 | 易混淆对 |
|---|---|---|---|---|---|
| **CR（Credit / 记账单位）** | 实验记账单位；`1 CR = 100 mu`。 | `01 §0.4`、`08 D0-1` | config、`mu` | 禁用「元/dollar」 | vs `mu` |
| **mu（最小货币单位）** | 整数最小单位；`1 CR=100 mu`；**禁浮点入账**。 | `03 P1`、`08 D0-1` | `contracts.models.Mu`、`engine` | 禁用「cent」 | vs `CR` |
| **B（现金余额 / cash）** | 账户可动用货币余额；**可为负但须借贷背书**（`|B|≤D_max`，无无偿透支）。 | `02 §0`、`08 §5.9(3)` | `WorldState.cash` | 禁用「balance」泛称 | vs **`E`（净值）** |
| **E（净值 / net_worth）** | `E = B + deposits + Σ资产估值 − (债务本息)`；**死亡判定基准**。 | `02 §0`、`01 §4.2` | `AgentState.net_worth` | 禁用「equity」泛称 | ⚠️ **`E`（净值） vs `E-*`（事件族） vs `E1–E20`（语义事件） vs `E_eff`** |
| **E_eff（有效净值）** | `E` 扣除本回合已标记作弊流入后的值；**死亡判定实际基准**。 | `02 §5.2`、`03 §5.3` | `lifecycle` hook | — | vs `E` |
| **I_eff（有效净流入）** | 一回合内来自**不同主体、非同环路、非自成交、排除系统项**的净收入；税基同口径。 | `02 §5.2`、`01 §1.4` | `obs/antifraud.py` | 禁用「income」泛称 | vs `E_eff` |
| **E0（初始净值/资金）** | 每个 Agent 出生净值，默认 100 CR（10000 mu）。 | `01 §2.1`、`02 §2.3` | config | — | vs `E` |
| **M0_total / M_target（货币总量/锚）** | 初始总量与恒定锚 `N×E0`。 | `01 §2.1/§2.5` | config | — | vs **`M_supply`**（在流通口径，见 §11 冲突） |
| **M_supply（货币供应）** | 在流通货币口径；**推荐口径** `Σmax(cash,0)+税池+银行库存`（待用户 Q1 裁决）。 | `01 §2.5`、`11`（本目录）、Q1 | `engine.conservation.money_total` | 禁用旧口径 `Σcash+Σdeposits`（未含银行库存） | vs `M0_total`/`M_target` |
| **m（代谢消耗）** | 每回合固定扣减的生存成本（销毁主出口），默认 2 CR/回合。 | `01 §2.2` | `4.4 apply_metabolism` | 禁用「metabolism rate」泛称 | — |
| **θ_floor（死亡硬地板）** | 低于此值开始计死，默认 −20 CR。 | `02 §2.3` | `lifecycle` hook | — | vs `θ_recover`、`θ_warn` |
| **θ_recover（恢复线）** | 回升到此才回正，默认 +5 CR（滞回上沿）。 | `02 §2.3` | `lifecycle` hook | — | vs `θ_floor` |
| **θ_warn（预警线）** | 触发系统提示，默认 20 CR。 | `02 §2.3` | `lifecycle` hook | — | vs `θ_dep`（需求剥夺阈，生活层） |
| **N_death（判死连续回合）** | 连续低于 `θ_floor` 的回合数，默认 3（沙盒 5）。 | `02 §2.3` | `lifecycle` hook | — | — |
| **K_exit（死亡冻结/退出窗口）** | 判死后允许被救的回合窗口，默认 6。 | `02 §2.3` | `resolve_revival` | — | — |
| **status（生命周期状态，6 值）** | 规范名：`alive/warning/near_death/dead/revived/terminated`。 | `08 §5.9(5)`、`02 §1.4` | `AgentState.status` | 禁用大写旧名 `DISTRESSED/DECEASED/REVIVING`（映射见 §11） | vs `dead`/`terminated` 混用 |
| **dead（死亡冻结）** | 判死后冻结；**可被救回**；非终态。 | `02 §1.1`、`08 §5.9(5)` | `status="dead"` | 禁用 `DECEASED` | vs **`terminated`** |
| **terminated（永久退出）** | 冻结期未被救回且超 `K_exit` → 终态，移出统计。 | `02 §1.1` | `status="terminated"` | — | vs `dead` |
| **LTV（贷款价值比）** | `贷款额 ≤ LTV×抵押折价`，默认 0.6。 | `01 §4.1`、`02 §3.1` | `econ` hook | — | — |
| **D_max / L_max（负债/单笔上限）** | 总负债 ≤ 100 CR；单笔 ≤ 50 CR。 | `01 §4.1` | `econ` hook | — | — |
| **安全阀 safety valve（护栏）** | 防全灭的确定性干预（存活率<`ρ_min=60%` 等）；须打标以便统计剔除。 | `02 §4.3` | `lifecycle` hook、`flag=rescue` | 禁用「guardrail」与安全阀**混用** | ⚠️ **安全阀 vs 护栏 guardrail**（见 §6） |
| **两轮制（自然/干预模式）** | 自然模式关安全阀验证 H2；干预模式开阀验证防全灭。 | `02 §4.3`、`09 §5` | `orchestration` | — | — |
| **C1–C10（反作弊路径）** | 10 类可预见作弊路径及其确定性封堵。 | `02 §5.1` | `obs/antifraud.py` | 禁用「C1–C10」与「S-C1..」混淆 | ⚠️ **C1–C10（反作弊） vs S-C1..S-C19（沙盒冲突） vs T14-C1..（事件冲突） vs WB-C1..（福祉冲突） vs NT-C1..（叙事冲突） vs AR-C1..（架构冲突）** |
| **P1–P8（惩罚措施）** | 负资产/复活惩罚（利率/权限/行动力/通信/抵押/冷却/UBI抵扣/代谢加速）。 | `02 §3.3` | `apply_penalty` | 禁用「penalty 1–8」 | — |
| **milli-unit（商品量最小单位）** | v2 商品 `qty` 的最小单位；**`1 unit = 1000` milli**；定点整数，入 `state_hash`。 | `v2/01 §2.1`、`T91` | `engine/production.py`（`qty`） | 禁用「浮点 unit」 | vs `mu`（货币最小单位） |
| **商品族事件** | `PRODUCE / CONSUME / DEPRECIATE / PRODUCE_OVERFLOW`（A 层物理原语，登记 `08 §1.2 O`）。 | `v2/01 §2.3`、`T91` | `engine/production.py`、`engine/hooks/production.py` | 禁用裸写「produce」当事件名 | vs `MARKET_TRADE`（成交） |
| **商品→货币转换通道（G-P1-1）** | 把「已产出的商品」变现为「货币收入」的通道（工资/雇佣/Agent 间交易/契约）；**P1 实测缺失**，属 **B 层未涌现**（非 A 层缺陷）。 | `v2/00-roadmap §3 P2`、`T91` | 待 B 层（`EMPLOYMENT`/`LOAN`/Agent 间市场） | 禁用与「最小市场带宽不足」混为一谈 | vs `最小市场`（C 保底，非此） |
| **`M(t)≥0` 地板 / `μ_floor`** | 世界级货币总量硬约束：销毁通道受 `max(0, M−μ_floor)` 限制，`μ_floor=0`；个体现金可负（欠账）。 | `v2/01 §2.3`、`T91` | `engine/hooks/econ.py`、`conservation` | — | vs 个体现金下限 |
| **`fallback_mint_enabled`（兜底铸币开关）** | C 层保底：兜底铸币=（`MONEY_MINTED`+`INIT_ENDOW` 等额配对，守恒），打 `flag=fallback`；**默认 false**。 | `v2/01 §4`、`T91` | `code/config/policy.json` | — | vs 常规铸币（AI 规范授权） |

---

## 5. 人格生活层（Persona-Life Layer, L1）

| 词条 | 定义 | 权威来源 | 代码对应 | 禁用/同义 | 易混淆对 |
|---|---|---|---|---|---|
| **L1 人格生活层** | 生成内容与意图；产出非货币状态；**不直写世界**。 | `00 §1.2`、`06` | `life/` | 禁用「agent 层」 | ⚠️ **`L1`（生活层） vs `L1`（hook 编号 advance_time） vs `L1`（Loan.lender） vs `L1–L8`（不变量）** |
| **M1–M7（生活层模块）** | M1 人格/M2 记忆/M3 关系/M4 日程/M5 场所昼夜/M6 对话传播/M7 目标需求。 | `06 §1.2`、`brief §5` | `life/{persona,memory,relation,schedule,places,goals}` | 禁用「module 1–7」 | vs **`metrics.*` 命名空间**（无关） |
| **persona（人格/身份）** | 结构化人格（大五/价值观/技能/背景/目标倾向/需求初值）；**静态配置**。 | `06 §2` | `life/persona.py`、`config/personas.json` | 禁用「character 配置」当 persona | — |
| **memory stream（记忆流）** | 存储→反思→三因子检索（recency/importance/relevance）。 | `06 §3`、`brief §2.2` | `life/memory.py` | 禁用「memory buffer」 | — |
| **relevance（记忆检索相关度因子）** | 记忆三因子之一。当前实现为 **确定性词法相关度**：`frozen://lexical-relevance-v1`（**token 级 feature hashing + 标签/关键词重叠**），零依赖、可复现、**可解释**（能说清「为什么想起这条」= 词面/标签重叠）。⚠️ **真语义相关性未验证；当前为词法近似**（词面/词袋；同义改写不命中）。 | `00 §5.3 AR-C5`、`06 §3`、`08 §5.4 D7-6` | `code/freeze`（`LexicalProvider` / `EmbeddingFreezer` / `relevance.py`） | 禁用把 `relevance` 说成「语义相似度」；禁用「embedding=语义」泛称 | vs **真嵌入/向量语义相似度**（黑盒；方案① sentence-transformers，**P1 升级项**） |
| **MEMORY_WRITE / RETRIEVE / REFLECT** | 记忆事件；检索**命中结果落日志**，重放不算嵌入。 | `08 §1.2 E` | 事件族 | — | — |
| **θ_reflect（反思阈值）** | 累积重要性超此值触发反思，默认 150。 | `06 §3.5` | `life/memory.py` | — | vs `θ_dep`、`θ_floor` |
| **relation（关系，有向）** | `affinity[-100,100]/trust[-100,100]/respect[0,100]/familiarity`；**数值确定性更新**，LLM 只产叙述。 | `06 §6.2` | `life/relations.py`、事件 `RELATION_CHANGE` | 禁用「relationship graph」当关系状态 | vs `G_rel`（观测层图） |
| **ε / ε_strong（关系阈值）** | 弱关系阈 `ε=20`；强关系阈 `ε_strong=50`。 | `06 §6.2` | `obs`/`life` | — | — |
| **schedule / WEEK_PHASES（日程/周相位）** | `PLAN/CONTACT/ACTIVITY/REVIEW` 四相位。 | `06 §4.2` | `life/schedule/`、`config` | ⚠️ 禁用 `phase` 代指周相位 | vs `round.phase`（0–6/35） |
| **activity_type（活动类型，8 类）** | `work/learn/socialize/leisure/self_care/civic/trade/rest`。 | `06 §10` | `config/activity_templates.json` | — | vs 语义事件 E1–E20 |
| **need（需求，6 维）** | `energy/satiety/social/esteem/mastery/leisure`（0–100）。 | `06 §7.2` | `life/goals.py`、事件 `NEED_UPDATE` | — | — |
| **θ_dep（需求剥夺阈）** | 需求低于此值触发唤醒，默认 20。 | `06 §7.2` | `life/goals.py` | — | vs `θ_warn` |
| **goal（目标）** | `layer∈{生存,成长,社交,意义}`；进度确定性推导。 | `06 §7.1` | `life/goals.py`、`GOAL_*` | — | — |
| **place（场所）** | 小镇内场所标识（17 处）。 | `00 §2.2`、`06 §5` | `config/places.json`、`PLACE_MOVE` | 禁用「location」当 place（`location` 是函数） | vs `topology`（邻接矩阵） |
| **topology（拓扑）** | 17×17 邻接/`travel_ticks` 常数矩阵。 | `00 §2.3`、`08 §5.6` | `config/topology.json` | — | — |
| **KernelPort / AdminPort / ports（端口）** | 生活层本地解耦协议（IF-1/IF-2 的本地 Protocol）。 | `v1.2/02 §...` | `life/ports.py` | 禁用「interface」当 port | ⚠️ **`ports`（生活层本地端口，实现分包） vs 蓝图 `contracts/`（共享协议包）**（见 §11 冲突） |
| **GA（Generative Agents）** | Stanford Smallville 认知架构（记忆流/反思/计划/检索）。 | `brief §2` | `life/`（适配） | — | — |

---

## 6. 观测层（Emergence Observation Layer, L2 / M8）

| 词条 | 定义 | 权威来源 | 代码对应 | 禁用/同义 | 易混淆对 |
|---|---|---|---|---|---|
| **L2 涌现观测层** | 只读、纯函数、确定性重算；**不调 LLM、不写世界、判定不用 LLM**。 | `00 §1.2`、`07 §0.1` | `obs/`、`emergence/` | 禁用「分析层」泛称 | ⚠️ **`L2`（观测层） vs `L2`（Life hook resolve_schedule） vs 现金流 `L2`？** 见 §11 |
| **metrics（指标入口）** | `metrics(log,t,time_cfg)->Snapshot`（IF-4）。 | `08 §4.0`、`00 §4.1` | `obs/report.py`、`emergence` | 禁用「report」单指（见下） | vs `emergence_report`/`wellbeing_report`/`census_report` |
| **metrics 命名空间** | `econ/lifecycle/life/emergence/wellbeing/emergence_soft/wellbeing_soft/narrative`。 | `08 §4.0`、`13 §6`、`17 NT-C2` | `emergence/namespace.py` | — | ⚠️ 命名空间 vs `M1–M7` 模块 |
| **emergence_report（涌现报告）** | 涌现指标侧产物（D 类判定）。 | `07 §0.1` | `obs/emergence.py` | — | vs `metrics` |
| **wellbeing_report（福祉报告）** | 福祉指标侧产物（W1–W7 + 背离）。 | `13 §0` | `obs/wellbeing.py` | — | vs `emergence_report` |
| **census_report（普查报告）** | 「发生了什么」的事实底账（原子频次+语义命中+覆盖度）。 | `15 §3` | `obs/census.py` | — | vs `metrics` |
| **指标分级 D / F / K** | `D`=纯确定性（判定/门禁）；`F`=含 LLM 冻结判定（仅敏感性，**出门禁**）；`K`=硬内核（护栏）。 | `07 §0.3`、`13 §0.2` | `08 §4.0` | 禁用「F 类」与「判定归属 F」混用到 K | ⚠️ **分级 D/F/K vs 判定归属 D/F/N/R**（D/F 重叠，K/N 不同） |
| **NPV / 门禁指标集** | `llm_judged_metric_count==0` 仅针对 `econ/lifecycle/life/emergence/wellbeing`；`*_soft` 排除。 | `08 §4.0/§4.10` | `obs/gate.py` | — | — |
| **guardrail（护栏）** | 健康度护栏（存活率/Gini/坏账/通胀/预算/守恒/复现等「不越界」）。 | `09 §1.1` | `obs/gate.py` | 禁用「guardrail」与**安全阀**混用 | ⚠️ **护栏 guardrail vs 安全阀 safety valve** |
| **观测判据（observation criteria）** | 充分条件：突现/可复现/无观测偏差/福祉可观测。 | `09 §1.2` | `obs/gate.py` | — | vs `护栏判据` |
| **S1–S4（显著性判据）** | 噪声带/置换检验/跨 seed 符号检验/时间稳定。 | `07 §3.3` | `obs/stats/` | — | ⚠️ **S1–S4 vs S-C1..（冲突） vs `self`(flag)** |
| **N_perm / z / p（统计参数）** | 置换次数 1000 / 噪声带 3 / 显著性 0.05。 | `07 §3.3` | `obs/stats/` | — | — |
| **θ_reach（级联覆盖阈）** | `reach_ratio` 阈值：0.50(N=10)/0.40(N=20+)。 | `07 §2.3`、`09 §1.2` | `obs/emergence.py` | — | — |
| **divergence_count（背离计数）** | 「金钱≠幸福」的可重算数字。 | `13 §4.2` | `obs/wellbeing.py` | — | vs `divergence`（叙事 `c_wbdiv`） |
| **G_money / G_comm / G_rel（图）** | 金钱图/沟通图/关系图（关系图有向多维权）。 | `03 §5.8`、`08 §4.3` | `obs/emergence.py` | — | — |
| **PageRank / Louvain / Girvan-Newman** | 确定性图算法（固定种子/顺序/迭代）。 | `08 §4.3/§4.6` | `obs/emergence.py` | — | — |
| **golden_baseline（黄金基线）** | 冻结的参照事件量/分布，供 G6 回归。 | `v1.2/evidence`、`obs/golden.py` | `obs/golden_baseline.json` | — | vs `golden_logs`（重放黄金日志） |

---

## 7. 福祉层（Well-being）

| 词条 | 定义 | 权威来源 | 代码对应 | 禁用/同义 | 易混淆对 |
|---|---|---|---|---|---|
| **WBV（福祉向量，7 维）** | 社会地位/主观满足/经济/健康/关系/成长/意义；**不合成标量**。 | `13 §1`、`06 §7.4` | `obs/wellbeing.py` | 禁用「life reward」（单一标量，已废） | vs `life reward`（Agentopia 旧概念） |
| **W1–W7（福祉维度）** | W1 经济/W2 社会地位/W3 主观满足/W4 健康/W5 关系/W6 技能成长/W7 自主意义。 | `13 §1.1` | `obs/wellbeing.py` | 禁用「维度 1–7」 | vs `M1–M7`（生活层模块） |
| **WBI（福祉指数，可选）** | WBV 的可选展示标量；须声明权重+敏感性+非优化声明。 | `13 §2.3` | `obs/wellbeing.py` | 禁用「幸福分」当权威结论 | vs `WBV` |
| **F 类福祉（W3/W2互评/W7 meaning）** | 含 LLM 冻结判定；**不进沙盒门禁**，长窗重点报告+敏感性。 | `13 §0.2/§3`、WB-C2 | `obs/wellbeing.py` | 禁用「主观=客观代理」 | vs D 代理 |
| **含-剔双版本（含/剔作弊边）** | 图指标/传播图同时输出双版本。 | `03 D5-5`、`07 §5.3` | `obs` | — | — |

---

## 8. 叙事层（Narrative / C）

| 词条 | 定义 | 权威来源 | 代码对应 | 禁用/同义 | 易混淆对 |
|---|---|---|---|---|---|
| **叙事层（Narrative / C）** | 第三种产出：从确定性日志长出的故事；**纯输出、不进判定**。 | `00 §1.5`、`17 §0.1` | `narrative/` | 禁用「story layer」泛称 | vs `展示层/frontend` |
| **StoryAtom（故事原子）** | 叙事最小事实单元；**强制携带 `anchors[]/evidence[]`**。 | `17 §1.1` | `narrative/story.py` | 禁用「event」代指 | vs **原子事件** |
| **AtomKind（原子种类）** | `CAST/MOTIVE_HINT/ACTION/OUTCOME/RELATION_DELTA/JUDGMENT/INTERVENTION`。 | `17 §1.2` | `narrative/story.py` | — | — |
| **NV（叙事价值 / drama score）** | 场景戏剧性打分（9 子维加权）；**确定性可重算**。 | `17 §2` | `narrative/drama.py`、`config/narrative_weights.json` | 禁用 `NV` 与 `net_worth` 混用 | ⚠️ **`NV`（叙事价值） vs `net_worth`** |
| **D(atom)（戏剧分量向量）** | 9 子维向量 `[c_conflict,...,c_impact]`。 | `17 §2.1` | `narrative/drama.py` | — | vs 判定归属 `D` |
| **anchor / anchor_digest（锚点/锚点指纹）** | 句级事实锚点；`anchor_digest` 对锚点集规范哈希（**与 LLM 无关，逐位一致**）。 | `17 §3.2` | `narrative/render.py` | 禁用「citation」当 anchor | — |
| **H-1/H-2/H-3（叙事硬约束）** | 事实可追溯/只读不污染/同一日志多风格重述。 | `17 §0.2` | `narrative/` | — | — |
| **四类模板** | `chronicle` 编年史 / `weekly_gazette` 每周纪事 / `character_pov` 角色视角 / `feature` 特写。 | `17 §4` | `narrative/render.py` | — | — |
| **origin（来源标签）** | 原子来源：`spontaneous/induced/rescue/frozen_llm`。 | `17 §1.3` | `narrative/story.py` | — | vs Event 来源 |
| **推测句 spec=true** | 含推测语气的句子（多为 `MOTIVE_HINT`）。 | `17 §3.2/§3.4` | `narrative/render.py` | — | — |

---

## 9. 工程 / 契约 / 门禁（Engineering）

| 词条 | 定义 | 权威来源 | 代码对应 | 禁用/同义 | 易混淆对 |
|---|---|---|---|---|---|
| **contracts（契约包）** | 纯类型/协议包，**零业务依赖**；IF/hook/Event/错误统一定义于此。 | BP §1.1/§1.3、ADR-02 | `code/contracts/{interfaces,hooks,models,errors}.py` | 禁用 `life/ports.py` 替代 contracts（见 §11 冲突） | vs **ports**（生活层本地解耦协议） |
| **hooks.py / interfaces.py / models.py / errors.py** | hook Protocol+Ctx/Delta；IF Protocol；Event/WorldView/Intent/JudgmentRequest/AuditPayload；类型化错误。 | BP §1.1 | `code/contracts/*.py` | — | — |
| **包结构（一级域，11 个）** | `contracts/engine/life/emergence/freeze/orchestration/traj/narrative/frontend/config/tests`。 | BP §1.1 | `code/` | 禁用 `sim-engine`（→ `engine/kernel`） | — |
| **依赖方向（单向无环）** | `orchestration` 为组合根；`emergence/traj/narrative/frontend` 只读；`kernel` 零反向依赖。 | BP §1.3 | `.importlinter` | — | — |
| **IF-2c / AuditPayload（审计载荷）** | freeze/叙事只产载荷经 IF-2c 提交，**Arbiter 唯一 emit**（B4）。 | BP §2.2.1、ADR-03 | `contracts.models.AuditPayload` | — | vs IF-2/IF-2b |
| **FreezeClient（冻结层客户端）** | 统一 LLM/嵌入入口；首跑落日志+缓存，重放读缓存不重调。 | BP §2.2、`00 §4.6` | `code/freeze/client.py` | 禁用「LLM client」泛称 | — |
| **冻结层（freeze）** | 收敛所有 LLM 调用点；`generate/judge/embed`；`F1–F6` 契约。 | BP §2.2、`00 §4.6` | `code/freeze/` | — | vs 软判定层 |
| **软判定层（soft judgment）** | 只定性社会判断，经 IF-2b 冻结（L1 内子模块）。 | `00 §1.5`、`06 L-4` | `life/softjudge/`、`life/llm.py` | 禁用「judge layer」泛称 | vs 冻结层（基础设施） |
| **叙事层角色带（Narrative band）** | 三条角色带之一：把已定结果叙述成情节。 | `00 §1.5` | `narrative/` | — | vs 功能层「叙事层 C」 |
| **三条角色带（硬内核/软判定/叙事）** | 按「LLM 能做什么」的正交切分。 | `00 §1.5` | 见 §10 图 | — | vs 三层（D0/L1/L2） |
| **engine_version.json** | 指纹文件（`engine_semver/kernel_commit/.../embedding_model/...`）。 | BP §3.6 | `config/engine_version.json` | — | vs `rule_version` |
| **topology.json / places.json / personas.json / activity_templates.json / policy.json** | config **核心五件**。 | BP §3.6 | `config/*.json` | — | — |
| **perception_scope.json / narrative_weights.json** | config **扩展两件**（入指纹）。 | BP §3.6 | `config/*.json` | — | — |
| **side_store（侧存储）** | 内容寻址侧存储（记忆正文/嵌入/叙事/prompt 正文）。 | BP §3.3、ADR-05 | `data/runs/<id>/side_store/` | 禁用「blob store」泛称 | vs `Ledger` |
| **body_ref / embed_ref** | 侧存储引用（含哈希）。 | `08 §1.1`、`06 §3.2` | payload 字段 | — | — |
| **G1–G7（CI 复现门禁）** | G1 边界/G2 复现/G3 冻结/G4 守恒/G5 稳定/G6 黄金基线分布/G7 schema 合约。 | BP §6.4、`v1.2/evidence/README §四` | `obs/gate.py`、`.importlinter` | ⚠️ 禁用 `G1–G6` 与 T16 目标开放问题 `G1–G6` 混淆 | ⚠️ **门禁 G1–G7 vs 开放问题 G1–G6** |
| **G6 黄金基线 / 事件量-分布回归** | 区分「跑完了」与「真的在运转」。 | `v1.2/evidence/README §四` | `obs/golden.py`、`golden_baseline.json` | — | — |
| **G7 schema 合约** | 任一事件缺字段/锚点悬空即 FAIL（阻塞）。 | `obs/gate.py` | `obs/gate.py` | — | — |
| **B1–B4（蓝图决策）** | B1 contracts 唯一归属/B2 模块符号粒度/B3 emergence 白名单/B4 单一写入口。 | BP §1.3/§2.2.1、ADR | `.importlinter`、`contracts` | ⚠️ 禁用 `B1–B4` 与 `B`（现金）混淆 | ⚠️ **`B`（现金） vs `B1–B4`（蓝图决策） vs `B线`（受控实验主线）** |
| **ADR-01…ADR-08** | 关键架构决策记录。 | BP §7 | — | — | — |

---

## 10. 项目 / 流程 / 缩写（Project & Process）

| 词条 | 定义 | 权威来源 | 禁用/同义 | 易混淆对 |
|---|---|---|---|---|
| **A 线（能力训练）** | 训练/微调社会智能（hard-constraint 世界）。 | `16 §0.1` | 禁用「A组」指代训练线 | ⚠️ **A/B（双主线） vs A/B（实验对照） vs A/B（双胞胎）** |
| **B 线（受控社会实验）** | 政策 A/B 实验床。 | `16 §0.1` | 禁用「对照组」指代 B 线 | 同上 |
| **训练视图（Training View）** | A 线独立命名空间 `metrics.training.*`，**不进评估/门禁**。 | `16 §3.3` | 禁用「reward」当评估指标 | vs 评估指标层 |
| **capability-specific reward** | 按能力分解的训练信号（非单一标量）。 | `16 §3.2` | 禁用「单一奖励」 | vs `life reward`（已废） |
| **T0 / T1 / T2（决策分层）** | 纯规则 / 廉价小模型 / 昂贵 LLM。 | `03 §3.1`、`06 §4.4` | 禁用「tier」泛称 | ⚠️ **T0–T2 vs `T7/T8/T9…`（任务号）** |
| **a（主动决策率）** | 每回合主动决策比例（≠唤醒率的旧 `w`）。 | `03 §3.3`、`08 §5.5` | 禁用 `w=3` 当唤醒率（`w` 旧指通信配额） | vs `q_*`（通信配额） |
| **q_alive / q_near（通信配额）** | 每回合通信配额上限（alive=3/near_death=1）。 | `02 §3.3`、`03 §4.3` | 禁用 `w` 当配额 | vs `a` |
| **特征集 feature_set** | 生成证据包时的功能集标签（如 `T39-life-full`）。 | `v1.2/evidence` | — | — |
| **任务号 T1…T47** | 团队任务编号（**非**命名空间）。 | 会话记录 | 禁用 `T1/T2` 与决策分层混用 | ⚠️ **T0–T2（决策分层） vs T1/T8/T14（任务号）** |
| **冲突编号前缀** | `AR-*` 架构 / `S-C*` 沙盒 / `T14-C*` 事件 / `WB-C*` 福祉 / `NT-C*` 叙事 / `Q*` 开放问题 / `D*` 待讨论 / `AQ*` 架构开放。 | 各分册 | 禁用前缀混用 | 见 §3/§4 表 |

---

## 11. 术语冲突清单（权威之间本身矛盾 —— 不自行裁定，交 Leader）

> 纪律：以下为**权威之间本身不一致**的项。本表**只记录、不裁定**。**2026-10-10 Leader 复核后收敛**：多数已解决，仅保留真正未决项（`OPEN`）；未决项**不由本表裁定**，交 Leader/用户。
> 状态：`RESOLVED`（附证据：任务/节）｜ `OPEN`（未决，交裁决）。

| # | 冲突项 | 权威 A | 权威 B | 状态 | 证据 / 备注 |
|---|---|---|---|---|---|
| **TC-1** | 货币供应 `M_supply` 口径 | `01 §2.5`：`Σmax(B,0)+税池` | Q1 推荐：`Σmax(cash,0)+税池+银行库存` | **OPEN** | 真正未决：属**用户未决 Q1**（新增「银行库存」项）；2026-10-10 Leader 确认保留，交用户裁决。 |
| **TC-2** | 契约包位置 | 蓝图 `BP §1.1/ADR-02`：`contracts/` | 实现 `life/ports.py` | **RESOLVED** | `contracts/` 已落地（T35/T36）；`v1.2/02 §10.4 R7/G1` 达标（`lint-imports` 8 kept/0 broken；`code/contracts/` 存在）；偏差已消。 |
| **TC-3** | 生命周期状态命名 | `02` 大写别名 | `08 §5.9(5)` 小写规范名 | **RESOLVED** | `v1 C-02` 已裁：规范名取小写 6 值；02 大写为文档别名（§4 映射）。 |
| **TC-4** | 协商/评比事件命名 | `12 T14`：`OFFER/COUNTER_OFFER/RANKING` | `08 §1.2 K`：`OFFER_CREATED/OFFER_COUNTERED/RANKING_EMITTED` | **RESOLVED** | 已裁决统一到 `08`（`09 §7.1` N-1/2/3）；已回写 T14。 |
| **TC-5** | 存款事件 | `12`（`DEPOSIT/WITHDRAW`） | 旧：复用 `TRANSFER↔银行` | **RESOLVED** | `T14-C3` 采纳 `DEPOSIT/WITHDRAW`（+`INTEREST_PAID`，phase 4.2）。 |
| **TC-6** | 耗竭告警事件 | `12`：`WELLBEING_ALERT` | `08`：`STATE_CHANGE` | **RESOLVED** | `T14-C4` 不新增；以 `NEED_UPDATE` + 观测派生承载。 |
| **TC-7** | 内核包命名 | 旧草稿 `sim-engine` | 蓝图 `engine/kernel` | **RESOLVED** | `BP §1.1` 注：统一为 `engine/kernel`；`sim-engine` 仅存于成员名 `sim-engine-stats-architect`（检查器已加 `exclude`）。 |
| **TC-8** | 唤醒率符号 | 早期 `w=3`（实为配额） | `08 §5.5`：`a`（决策率）/ `q_*`（配额） | **RESOLVED** | 已收敛（`08 §5.5` 澄清）。 |
| **TC-9** | LLM 预算口径 | 旧稿 `N×0.6` | `≤N×0.5` | **RESOLVED** | `S-C19` 收敛为 `≤N×0.5`（N=10→5 / N=20→10 / N=50→25）。 |
| **TC-10** | 观测文档编号 | 旧引用 `10-emergence-observation.md` | 实际 `07-emergence-observation.md` | **RESOLVED** | **规则（2026-10-10 Leader 裁决）**：以「**现行实际编号 + 文件名**」为规范（如 `v1.1/07-emergence-observation.md`、`v1.1/10-v1.1-proposal.md`）；历史旧序编号（如 `10-`→`07-`）**只作 `mention` 标注，不视为违规**；LEXICON 保留「旧编号→现行编号」映射即可，**不必回溯改文档**（同 v1 历史快照原则）。 |
| **TC-11** | 叙事命名空间登记 | `17 NT-C2`：`metrics.narrative` | `08 §4.0` | **RESOLVED** | `T25` 已在 `08 §4.0` 登记（非判定、出门禁）。 |
| **TC-12** | 感知前置 R2/R3/R4 | `17` 依赖 R2/R3/R4 | `08` / 实现 | **RESOLVED** | `T27` 已落地：`PERCEPTION_SCOPE`(R2) + 群组成员(R3) + 转述 `refs`(R4)；`engine/version.py` 校验 `perception_scope v1.2-r2`。 |

### 11.1 「易混淆对」汇总（**非冲突**，仅提示，详见各表）
- `E`（净值） vs `E-*`（事件族） vs `E1–E20`（语义事件） vs `E_eff`。
- `E`（净值） vs `E`（判定归属？无，判定归属是 D/F/N/R）。
- `B`（现金） vs `B1–B4`（蓝图决策） vs `B线`（受控实验主线） vs `B分组`（实验对照）。
- `A/B`（双主线） vs `A/B`（实验对照/双胞胎）。
- `T0/T1/T2`（决策分层） vs `T1/T8/T14/T47`（任务号） vs `T`（回合 Round 的别名？文档用 round）。
- `L1`（生活层） vs `L1`（Life hook `advance_time`） vs `L1`（`Loan.lender`） vs `L1–L8`（不变量） vs `L2`（观测层）。
- `M1–M7`（生活层模块） vs `metrics.*`（指标命名空间） vs `metrics.life`。
- `R0`（级联） vs `R-1..R-11`（风险） vs `R1–R7`（T9 铁律） vs `R2/R3/R4`（感知前置）。
- `D`（判定归属=确定性） vs `D` 分级（指标 D 类） vs `D1/D5-1`（架构决策/开放问题）。
- `K`（指标 K 类硬内核） vs `K_top`/`K_split`/`K_exit`（阈值/参数）。
- `S1–S4`（显著性） vs `S-C1..`（沙盒冲突）。
- `G1–G7`（CI 门禁） vs `G1–G6`（T16 目标开放问题）。
- `C1–C10`（反作弊） vs `S-C*`/`T14-C*`/`WB-C*`/`NT-C*`/`AR-C*`（冲突编号）。
- `NV`（叙事价值） vs `net_worth`。
- `census` vs `metrics` vs `emergence_report` vs `wellbeing_report`。
- `护栏 guardrail` vs `安全阀 safety valve`。
- `INTENT_REJECTED` vs `OFFER_REJECTED`。
- `dead` vs `terminated`。
- `contracts` vs `ports`。

---

## 12. 配套工具与使用

### 12.1 术语合规检查器（v2 · 基线/棘轮）

**两种命中**：`violation`（违规，计入门禁）｜ `mention`（提及·别名/废弃说明，**不计**）。
命中行若含 `→`/`已废弃`/`已并入`/`不新增`/`已裁定`/`需统一`/`替代`/`不设`/`旧称`… 即归为 mention。

```bash
# ── 本地运行（在 social-experiment/ 下）──
# 1) 完整报告（违规 / 提及 / 按目录统计）
python3 glossary/tools/lint_terms.py --root .

# 2) 按目录统计（历史 vs 活文档）
python3 glossary/tools/lint_terms.py --root . --dir-stats

# 3) JSON 输出
python3 glossary/tools/lint_terms.py --root . --json --fail

# 4) 棘轮门禁（CI 推荐）：仅「基线之外的新违规」返回非 0
python3 glossary/tools/lint_terms.py --root . --baseline glossary/term_baseline.json
python3 glossary/tools/lint_terms.py --root . --baseline glossary/term_baseline.json --show-baseline

# 5) 维护：重冻基线（术语/基线变更时）
python3 glossary/tools/lint_terms.py --root . --update-baseline glossary/term_baseline.json
```

**接入 CI（与 `pytest -q` / `lint-imports` / obs gate 并列）**：仓库根已提供 `Makefile`：
```bash
make lexicon-gate      # 术语棘轮门禁（CI 推荐）
make lexicon-report    # 完整报告
make gate              # lexicon-gate + code 测试 +（可选）lint-imports
```
- **棘轮语义**：`--baseline` 时，比较按 `(file, variant)` **计数**（对行号偏移稳健）；已知历史违规（`v1/**`）不报错，**只有新违规/新文件/计数上升才失败**（返回码 1）。
- 扫描范围：`social-experiment/**/*.md` 与 `social-experiment/code/**/*.py`（跳过 `glossary/` 自身、`__pycache__`、`.pytest_cache`、`data/` 运行产物、`.jsonl`）。
- 规则来源：`glossary/lexicon.json` 的 `forbidden`（支持 `exclude` 排除成员名、`allow_line_contains` 允许他方术语引用）。
- 基线文件：`glossary/term_baseline.json`（当前冻结 **50** 条违规，**全部集中在历史目录 `v1/**`**；活文档 0）。

### 12.1.1 按目录统计（2026-10-10 快照）
| 目录 | violation | mention | 说明 |
|---|---|---|---|
| `v1/` | 50 | 7 | **历史快照**（不强制改写，已入基线） |
| `v1.1/` | **0** | 47 | 活文档，已清零 |
| `v1.2/` | **0** | 1 | 活文档，已清零 |
| `research/` | **0** | 2 | 活文档，已清零 |
| `glossary/`、`code/` | **0** | 0 | 已清零 |
> 结论：违规**集中在历史文档 `v1/**`**，活文档干净；棘轮门禁在此基线上**通过**（退出码 0）。

### 12.2 术语图
见同目录 `lexicon-map.svg`（自包含、内联样式、无外部依赖）：按**三层（D0/L1/L2）** 与**三条角色带（硬内核/软判定/叙事）** 展示核心术语归属与判定边界。

### 12.3 维护约定
- 术语变更须同时更新 `LEXICON.md`、`lexicon.json`（二者为准）；`lint_terms.py` 无需改（读 json）。
- 发现新的权威冲突 → 记入 §11，**不自行裁定**。
- 覆盖新增分册（v1.2 `01`–`03`、`14`、`15`、`17`）时，按既有类别扩展。

---

*（青溪镇词汇表 v1 结束 — design-synthesizer）*
---

## §13 T61×T62 流动性 / 确定性授信（新增词条，2026-10-10）

> 用户拍板 **A：死亡/续命以「流动性」为基准**。以下词条为 econ(T62)×lifecycle(T61) 统一接口新增，已在 `lexicon.json` 登记。

| 规范名（term） | 中文名 | 定义 | 代码 | 易混淆 |
|---|---|---|---|---|
| `liquidity` | 流动性 `L`（判死基准） | `L = cash`（可动用流动性）；死亡/续命以 `L` 为基准，`net_worth` 仅记录 | `engine/liquidity.py::liquidity` | `net_worth` |
| `credit_limit` | 授信额度（可借上限） | 确定性规则给出的单账户可借上限；**无抵押且无收入→0**，逾期/坏账冷却→0 | `engine/liquidity.py::credit_limit` | `loan_max_debt_mu` |
| `can_borrow` | 可新增流动性（放贷准入） | `L<trigger` 且无存量未偿 且无 `overdue` 且 `credit_limit>0`；lifecycle 直接消费 | `engine/liquidity.py::can_borrow` | `credit_limit` |
| `liquid_trigger_mu` | 生存阈值（流动性） | `L` 低于此值=不足支付下回合生存开销，进入判死计数（默认 200） | `engine/liquidity.py`; `policy.economy` | `liquid_sustain_mu` |
| `liquid_sustain_mu` | 可持续生存阈值 | 续命目标：把 `L` 抬到该值视为可持续（默认=3×trigger=600） | `engine/liquidity.py`; `policy.economy` | `liquid_trigger_mu` |
| `overdue` | 逾期（贷款） | 未偿贷款 `due_round<round` 的派生状态；触发罚息与信用降级，超 `N_overdue`→`LOAN_DEFAULT` | `engine/liquidity.py::overdue_of` | `LOAN_DEFAULT` |

**口径**：`L` 与授信全为纯函数、无状态、可重放；`LOAN_ISSUED`（`cash↑ debt↑`）**不改善 `net_worth`**（诚实会计），续命靠抬 `L`；**不做补贴型续命贷**。
