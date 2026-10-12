# 01 · v1.2 系统实现架构（工程蓝图）——把 v1.1 设计落成可开工的系统

> **【Fork B 时效标注 · 2026-10-12】** 本文 §0 铁律 **(C2)「同日志逐位一致 `replay(log)` + `metrics()` 字节相等」** 按 Leader Q-12.1 修正为：**保留 `replay(log)` 代码确定性，`metrics()` 字节相等降为诊断、不再作放行门禁**（其余 C1/C3 不变）。**单一口径见 `v2/refs/gate-grading.md`。**

> 文档类型：系统实现架构（工程蓝图）｜ 作者：solution-architect（解决方案架构师）
> 状态：**Draft v0.1（增量落盘，逐节追加）**
> 目标读者：kernel-dev / life-layer-dev / freeze-layer-dev / sim-engine-stats-architect / sandbox-test-lead / delivery-reviewer（T24）
> 上游权威：`v1.1/00-architecture.md`（三层/IF-1~IF-7/确定性边界）、`v1.1/08-engine-stats-extension.md`（**最新版**：事件 schema / Phase 3.5 / hook / `PERCEPTION_SCOPE` / `GROUP_CREATED` / `MSG.refs` 约束 / `NARRATIVE` 元数据 / `metrics.narrative`）、`v1.1/06-life-layer.md`（M1–M7）、`v1.1/07-emergence-observation.md`（M8）、`v1.1/09-sandbox-v1.1.md`（护栏+观测判据）、`v1.1/14-agent-impl-reuse-map.md`（复用图）、`v1.1/16-project-goal-options.md`（A+B 双主线）、`v1/03-engine-stats.md`（内核契约）。
> 标注约定：**【已定】**=直接继承上游、不得改；**【工程决定】**=本蓝图新增、可直接开工的工程口径；**【待验证假设】**=需 P0 实测/用户裁决。
> 三条铁律（验收红线，全篇不得冲突）：**(C1) 世界引擎/裁决器是确定性代码，绝非 LLM；(C2) 同日志逐位一致 `replay(log)` + `metrics()` 字节相等；(C3) LLM 判定结果冻结（重放不重问 LLM）。**

---

## 0. 本蓝图要解决的问题与工程总原则

### 0.1 定位
把 v1.1 的**机制设计**（三层架构、事件契约、经济/生命周期/生活/观测规则）落成一套**可实现、可演进**的软件系统架构，作为 **P0（N=20 世界单周跑通）** 的直接开工依据。本蓝图只定**系统结构与契约**，不实现代码、不重定义机制口径。

### 0.2 工程技术原则（继承 + 落地）
| # | 原则 | 落地手段 |
|---|---|---|
| E1 | **内核自建、Agent 侧包裹式复用**（`14` §E.1） | 内核=自研确定性代码；生活层以 GA 认知架构为主干，LLM 调用点全部收敛到「冻结层」 |
| E2 | **单一写入口**（`00` §1.2/§4.5） | 写世界只有 `kernel.arbiter`；生活层只产 `pending_intents`；结构层禁止绕过 |
| E3 | **观测层只读纯函数**（`00` §4.4、`07` R1–R7） | `emergence` 包只 import `kernel.ledger` 只读句柄；CI 用 import-linter 封死反向依赖 |
| E4 | **确定性边界显式化**（`00` §5） | 内核与生活层严禁读墙钟/网络/环境变量；随机只经 `ctx.rng(stream_id, seq)`；LLM/嵌入只经冻结层 |
| E5 | **增量可跑、单机优先** | P0=单机单周 N=20；长窗/多 seed/训练接入通过「配置 + 编排器」演进，不重写内核 |

---

## 1. 代码仓库与模块结构（目录树 + 依赖方向）

### 1.1 分层与包结构总览

仓库采用**单仓多包（monorepo，Python 包 + 前端子工程）**，包边界即铁律边界。顶层分为 **层间契约 / 确定性内核 / 生活层 / 观测层 / 冻结层 / 实验编排(B) / 轨迹导出与训练(A，占位) / 叙事层(C) / 前端 / config 与数据 / 测试** 共 **11** 个一级域。

```
social-experiment/
├── README.md
├── pyproject.toml                     # Python 包与依赖；锁定版本
├── Makefile                           # run / replay / metrics / test / lint / gate
│
├── contracts/                         # ── 层间契约（B1：协议类型唯一归属，零业务依赖）──
│   └── contracts/
│       ├── interfaces.py              # IF-1/IF-2/IF-2b/IF-2c/IF-6/IF-7 的 Protocol/ABC
│       ├── hooks.py                   # L1–L7 / 4.1–4.8 hook 的 Protocol + Ctx/Delta
│       ├── models.py                  # Event/WorldView/Intent/JudgmentRequest/AuditPayload（dataclass）
│       └── errors.py                  # HashChainBroken/UnknownEventType/RoundRollback/IllegalJudgment
│
├── engine/                            # ── 确定性内核（🔴 自建，v1/03 契约）──
│   └── kernel/
│       ├── clock.py                   # 时间派生 derive_time(round,cfg)（D-1）
│       ├── scheduler.py               # Round Scheduler：P0..P6 阶段顺序（D-2）
│       ├── event_queue.py             # 确定性优先级事件队列（全序 tie-break）
│       ├── state.py                   # WorldState / AgentState / Snapshot（不可变风格）
│       ├── arbiter.py                 # 中央裁决器：唯一写入口，串行折叠 hook 链
│       ├── hooks/
│       │   ├── econ.py                # 4.1 settle_market / 4.2 settle_obligations / 4.3 apply_tax
│       │   ├── lifecycle.py           # 4.4 apply_metabolism → 4.8 check_death
│       │   └── life.py                # 3.5 L1..L7（advance_time…emit_tags）
│       ├── rng.py                     # 层级化 SplitMix64：draw(stream_id,round,seq,n)（D-8）
│       ├── ledger.py                  # append-only 哈希链 + turn_seal + 只读句柄
│       ├── replay.py                  # replay(log) -> WorldState（纯折叠，不重跑 hook）
│       ├── snapshot.py                # 快照节流（每 K 回合）+ 从日志重建
│       ├── canonical_json.py          # 规范 JSON（键排序/无空格/定点）+ SHA-256
│       ├── invariants.py              # 守恒律 + v1 五条 + 08 新增 6 条 + L1–L8 校验
│       └── version.py                 # engine_version 指纹计算与校验
│
├── life/                              # ── 生活层 Python 包（🟢/🟡 GA 主干 + M1–M7）──
│   ├── decision/                      # N2：主循环/分层决策 T0/T1/T2（对齐 GA persona.move）
│   ├── persona/                       # M1 人格/身份（静态配置 + 派生标量）
│   ├── memory/                        # M2 记忆流：写入/三因子检索/反思（GA）
│   ├── relation/                      # M3 关系：有向 affinity/trust/respect（数值确定性）
│   ├── schedule/                      # M4 日程/活动：周计划→递归分解→执行（GA plan/execute）
│   ├── places/                        # M5 场所与昼夜：拓扑/营业时段/移动代价
│   ├── goals/                         # M7 目标与需求：Goal/Need + WBV 派生
│   ├── perceive.py                    # IF-1 视图构造（visible_events 过滤，反泄漏）
│   ├── intent.py                      # INTENT.* 生成（经 IF-2 提交，不直写世界）
│   ├── pathfind.py                    # GA A* 寻路（离散网格，可确定复现）
│   ├── softjudge/                     # 软判定层（LLM 定性判断，经 IF-2b 冻结）
│   └── narrative_life/                # 生活层内表达子模块（对话/印象叙述，经 IF-7）
│
├── emergence/                         # ── 观测层（🎯 只读纯函数，07 M8）──
│   └── emergence/
│       ├── namespace.py               # metrics.econ/.lifecycle/.life/.emergence/.emergence_soft
│       ├── life_metrics.py            # 活动参与/需求/关系/记忆（08 §4.1–4.9）
│       ├── emergence_metrics.py       # 传播/标签/圈层/规范/职业（D 类，判定主力）
│       ├── report.py                  # emergence_report / wellbeing_report（字节一致）
│       ├── narrative_metrics.py       # metrics.narrative（读者数/覆盖/引用完整性）
│       └── stats/                     # 置换检验/符号检验/效应量（S1–S4，固定种子）
│
├── freeze/                            # ── LLM 冻结层（🔴 自建薄封装）──
│   └── freeze/
│       ├── client.py                  # FreezeClient：统一 LLM 调用入口
│       ├── cache.py                   # 内容寻址缓存（prompt_hash -> 响应）
│       ├── embed.py                   # 嵌入冻结与缓存（模型版本入 engine_version）
│       ├── budget.py                  # LLM_BUDGET 闸门 + T2→T1→T0 降级
│       └── providers/                 # 可插拔 provider（OpenAI 兼容 / 本地 / mock）
│
├── narrative/                         # ── 叙事层（C，纯输出；N1：物理分包、逻辑属生活层角色带）──
│   └── narrative/
│       ├── story.py                   # 事件流→故事线（chron/rôle/weekly）
│       ├── render.py                  # 叙述渲染（防幻觉：只引日志内事实）
│       └── drama.py                   # 戏剧性确定性度量（冲突/转折/反差）
│
├── orchestration/                     # ── 实验编排（B）──
│   └── orchestration/
│       ├── runner.py                  # run(seed,config,rounds) 单一入口
│       ├── experiment.py              # A/B 双胞胎分区 / 多 seed / 政策档
│       ├── policy.py                  # 政策参数层（税/利率/UBI/惩罚/阈值 config 化）
│       └── partition.py               # train/val/held-out seed 切分（冻结）
│
├── traj/                              # ── 轨迹导出与训练管线（A，占位）──
│   └── traj/
│       ├── exporter.py                # log → (state摘要, decision, outcome) 三元组（反泄漏）
│       ├── reward.py                  # reward_calculator(log) -> capability 多维信号
│       └── pipeline/                  # ↓ P2 才落：SFT/偏好/帕累托（占位，不实现）
│
├── frontend/                          # ── 前端（观测与展示）──
│   ├── town-viewer/                   # 🟢 AI Town PixiJS 像素小镇（MIT 迁移）
│   │   ├── src/{PixiGame,PixiStaticMap,Character,...}.tsx
│   │   └── replay-adapter/            # 读 turn_seal/事件流 → 平滑回放（只读）
│   └── audit-console/                 # 🔴 自建审计观测台（只读日志重算指标）
│       └── src/{Metrics,Report,Lineage}.tsx
│
├── config/                            # ── config 与数据（config 核心五件 + 扩展两件 + 指纹）──
│   ├── personas.json                  # M1 人格/身份（核心）
│   ├── places.json                    # M5 场所 + 营业时段 + 容量（核心）
│   ├── topology.json                  # 17×17 邻接/travel_ticks 常数矩阵（核心；AR-D2）
│   ├── activity_templates.json        # M4 活动模板库（核心；12-event-lineage）
│   ├── policy.json                    # 政策参数层（核心；税/利率/UBI/惩罚/阈值）
│   ├── perception_scope.json          # 可见性分类表（扩展；最新版 08 R2，入指纹）
│   ├── narrative_weights.json         # 戏剧性度量权重（扩展；NT-C2，入指纹）
│   └── engine_version.json            # 指纹（见 §3.6）
│
├── data/                              # ── 运行产物（不入 git；按 run_id 分目录）──
│   └── runs/<run_id>/
│       ├── event_log.jsonl            # 哈希链事件日志（权威）
│       ├── turn_seal.jsonl            # 每回合封条
│       ├── side_store/                # 内容寻址侧存储（记忆正文/印象/叙事/prompt）
│       ├── vector_index/              # 嵌入向量索引（只被决策路径读）
│       ├── snapshots/                 # 状态快照（节流）
│       └── reports/                   # metrics/emergence/wellbeing 快照
│
└── tests/                             # ── 测试与复现门禁 ──
    ├── unit/                          # 各 ho​​ok/模块单测
    ├── determinism/                   # 同日志重放/字节一致黄金测试（CI gate）
    ├── golden_logs/                   # 黄金日志（冻结的首跑产物）
    ├── boundary/                      # import-linter 边界测试（观测层只读等）
    └── acceptance/                    # P0 护栏/观测判据验收脚本
```

> **注**：`engine/kernel` 与本蓝图早期草稿中的 `sim-engine`（旧名）命名统一为**同一包**；下游引用以本节为准。

### 1.2 模块边界与职责（谁负责什么）

| 一级域 | 定位 | **必须做** | **绝不越界** | 依赖上游 |
|---|---|---|---|---|
| `engine.kernel` | 世界法则（D0） | 时间派生、状态存储、裁决器全部 hook、账本、RNG、规则校验、全部货币/生命周期结算 | 不做内容生成、**不调 LLM** | v1/03 + 08 §2 |
| `life` | 人格生活层（L1） | 生成计划/对话/反思/记录等**内容**，产出**非货币状态**与**意图** | **不直写世界状态/账户**；不绕过裁决器；不自定货币后果 | 06 |
| `emergence` | 观测层（L2/M8） | 从日志**确定性重算**指标 | **只读**、不调 LLM/嵌入、不写世界、判定不用 LLM | 07、08 §4 |
| `freeze` | LLM 冻结层 | 统一 LLM/嵌入调用；首跑落日志+缓存；重放读缓存不重调 | 不产金额/死亡/结算数字；不写世界状态 | 00 §4.6/§5.5 |
| `narrative` | 叙事层（C） | 把**已定事实**叙述成情节 | **纯输出，`affects_state=false`**，不进判定路径 | 00 IF-7 |
| `orchestration` | 实验编排（B/兼 A） | run/replay/metrics 入口、A/B 分区、多 seed、政策档 | 不改内核语义；不新增写入路径 | 09、16 §2.5 |
| `traj` | 轨迹导出/训练（A，占位） | **只读**日志导出训练样本 + 确定性奖励 | 不回写世界；F 类不得作训练信号 | 16 §2–§3 |
| `frontend` | 观测与展示 | 只读日志/快照可视化 | 不写世界；回放非权威 | 14 §B.7 |

### 1.3 依赖方向（**铁律：单向、无环**）

```
                ┌───────────────────────────────────────────────┐
                │            orchestration (B/兼A)                │  最上：编排与入口
                └───────────────┬───────────────────────────────┘
                                │ 依赖（调用）
        ┌───────────────┬───────┴────────┬───────────────┬──────────────┐
        ▼               ▼                ▼               ▼              ▼
    engine.kernel      life (L1)        freeze        traj(A)      frontend
    (D0 内核)          (生活层)        (冻结层)      (只读)        (只读)
        ▲                ▲                ▲
        │  (L1 经 IF-1/IF-2/IF-2b/IF-7 调内核契约)
        │                │
        └────────────────┴─────────────────┐
                                            │
                          emergence (L2 只读)─┘  ← 只读 kernel.ledger（IF-4），无反向

    narrative (C 纯输出) → 只读 ledger / 经 IF-7 写侧存储
```

**依赖规则（CI 用 import-linter 强制；B2=模块/符号粒度，B3=emergence 白名单）**：
1. **`contracts`** 是**纯类型/协议包**，零业务依赖（只 stdlib）；被 `kernel`/`life`/`emergence`/`freeze`/`orchestration` 依赖，**它不依赖任何业务包**（B1）。
2. **`emergence` 允许 import 白名单**：`contracts.*`、`kernel.ledger`（只读句柄）、**`kernel.canonical_json`、`kernel.version`（纯函数、只读、无副作用——B3 白名单，避免 emergence 复制序列化实现导致字节漂移）**。**禁止 import** `life.*`、`freeze.*` 及 `kernel.arbiter`/`kernel.hooks`/`kernel.state`/`kernel.scheduler`（写路径/实现）。→ 观测层只读（`00` §4.4）。
3. **`life` 不得 import `kernel.arbiter` / `kernel.hooks` / `kernel.state` / `kernel.scheduler` 的任何符号**（模块/符号粒度，B2）；`life` 只依赖 `contracts.*`（承载 IF-1/IF-2/IF-2b/IF-2c/IF-7 的 Protocol 与只读视图类型）与 `freeze.*`。→ 生活层不得直写世界状态（`00` §4.5）。
4. **`kernel` 不得 import `life`/`emergence`/`freeze`/`orchestration`**（零反向依赖）；生活层 hook（L1–L7）由**注册表注入**（依赖倒置），内核只持 `contracts.hooks` 的 Protocol。
5. **`freeze` 不 import `kernel.state`/`kernel.arbiter`**；冻结层只产「待写事件的**载荷**」（`AuditPayload`/`JudgmentPayload`），经 **IF-2c `submit_audit`** 提交给内核，由 **Arbiter 负责 emit**（B4）。→ LLM 产物必须经内核封装方生效。
6. **`narrative` / `traj` / `frontend` 只读**，不得 import 任何写路径；`traj` 不得作为 `life`/`kernel` 的依赖（训练视图与评估解耦，`16` §3.3）。
7. **`orchestration`** 是唯一允许同时依赖上述多包的**入口层**（组合根）；不得被任何下层依赖。

### 1.4 运行期控制流（一次回合，对齐 `00` §1.3 / `08` §2.4）

```
orchestration.runner
  └─ kernel.scheduler.run_round(round):
       P0 ROUTE ─ P1 PERCEIVE ─ P2 DECIDE ─ P3 COMMUNICATE
              ─ P3.5 LIFE(L1..L7) ─ P4 ARBITRATE(4.1..4.8) ─ P5 LIFECYCLE ─ P6 COMMIT
       ├─ L1 各阶段：life 经注册表被内核调用（依赖倒置）
       ├─ LLM/嵌调用：life.softjudge / life.* → freeze.FreezeClient（首跑经 IF-2c 提载荷 + 写缓存）
       ├─ emit（IF-3）：仅 kernel.arbiter.hooks.* 产 Delta；事件写入本回合「待提交缓冲区」（暂存，不落盘）
       └─ P6 COMMIT（**唯一 append 点**）：按全局固定顺序将 buffer 一次性追加 + invariants.check + snapshot + seal
       ⚠︎ 整回合回滚 = 丢弃整个待提交缓冲区（**含 P2 的 LLM_CALL**），仅追加 SYSTEM_ERROR / ECONOMY_INVARIANT_VIOLATION，状态不变
  └─ emergence.report(ledger.read_only())   # 只读派生
```

*（§1 模块结构骨架 完成）*

---

## 2. 接口契约（IF-1~IF-7 + IF-2c + LLM 冻结层 + 中央裁决器 hook 链）

> 命名与字段：沿用 v1/08 的 lower_snake_case；事件 schema 以**最新版 08** 为准。本节给出**可直接实现的函数签名**（Python typing）。**所有协议类型（IF 接口 / hook Protocol / Event/WorldView 等 dataclass / 错误）统一定义于 `contracts` 包（B1）**，`kernel`//`life`/`emergence` 均依赖它、彼此不互相 import。所有签名均在 §2.7 给出「铁律符合性」核对。

### 2.0 基础类型（沿用 v1/03 §2.1，08 §1.1；**定义于 `contracts.models`**）

```python
AgentId = str                 # 稳定 id，如 "A007"；遍历恒按字符串升序
Round   = int                 # 回合号，从 0 起
Mu      = int                 # 金额，整数最小单位（mu 进制=100），可负
Phase   = int                 # 0..6 与 35（=Phase 3.5 LIFE）

@dataclass(frozen=True)
class Event:                  # 事件外壳（v1 §6.1 + 08 §1.1）
    seq: int                  # 全局单调递增
    round: Round
    phase: Phase              # 0,1,2,3,35,4,5,6
    actor: AgentId | Literal["SYSTEM", "OBSERVER"]
    type: str                 # 见 08 §1.2 事件类型表
    payload: dict             # 结构化；生活层事件额外必带 day/slot/day_type/place
    mono_ts: int              # 逻辑时间 = round*TIME_UNIT + phase_seq（非墙钟）
    prev_hash: str
    hash: str                 # = sha256(canonical_json(event 去掉 hash))

@dataclass(frozen=True)
class TurnSeal:               # 每回合封条（§3.2）
    round: Round
    first_seq: int
    last_seq: int
    round_hash: str           # = sha256(concat(e.hash for e in round))
    prev_seal_hash: str
```

### 2.1 七条层间接口（IF-1~IF-7）（【已定】，`00` §4.1）

```python
# ── IF-1  感知（D0 → L1，只读、无副作用）──
def perceive(agent_id: AgentId, *, log: ReadOnlyLog, t: Round, cfg: Config) -> WorldView: ...

# ── IF-2  提交意图（L1 → D0，唯一写入请求通道）──
def submit_intent(agent_id: AgentId, intent: Intent, *, engine: KernelHandle) -> Literal["ok","rejected"]: ...

# ── IF-3  事实产出（D0 内部 → 本回合待提交缓冲区；**P6 COMMIT 才落盘**）──
def emit(event: Event, *, buffer: RoundBuffer) -> Event: ...       # 内核私有；入缓冲区，不立即写盘

# ── IF-4  观测（Ledger → L2，只读纯函数）──
def metrics(log: ReadOnlyLog, t: Round, time_cfg: TimeConfig) -> Snapshot: ...

# ── IF-5  注入种子（OBSERVER → D0，唯一人类干预入口）──
def inject_seed_event(seed: SeedSpec, *, engine: KernelHandle) -> Event: ...   # 封装 SEED_EVENT

# ── IF-2b 提交软判定（软判定层 → D0，唯一出口；硬内核校验后冻结）──
def submit_judgment(agent_id: AgentId, req: JudgmentRequest, *, engine: KernelHandle) -> Event: ...

# ── IF-2c 提交审计/内容载荷（freeze/叙事 → D0；唯一写入口仍是 Arbiter，B4）──
def submit_audit(payload: AuditPayload, *, engine: KernelHandle) -> int: ...   # 返回事件 seq

# ── IF-6  读回冻结判定（D0 → replay/stats，绝不重问 LLM）──
def get_frozen_judgment(judgment_id: str, *, log: ReadOnlyLog) -> str | int: ...

# ── IF-7  叙事（叙事层 → 侧存储，纯输出、不改状态）──
def narrate(fact_event_seqs: list[int], *, side: SideStore, style: str = "chron") -> NarrativeArtifact: ...
```

**关键类型**：

```python
@dataclass(frozen=True)
class WorldView:                       # IF-1 返回；反泄漏：只含决策时点可见信息
    round: Round; day: int; slot: str; day_type: str
    self_state: dict                   # status / 余额 / 需求 / 目标（数值+枚举，不含文本判定）
    visible_events: list[Event]        # 见 §2.4 visible_events()，已去除 heard（spec）旁注
    place_status: dict                 # 当前场所 + 容量 + 在场者
    memory_refs: list[str]             # 记忆引用（mem_id，正文在侧存储）
    heard_annotations: list[dict]      # 一阶「听说」旁注，标 spec=true，不进决策主视图

@dataclass(frozen=True)
class Intent:                          # IF-2 载荷（08 §4.2 分类）
    cls: str                           # "INTENT.MOVE" | "INTENT.ACTIVITY" | "INTENT.SOCIAL"
                                       # | "INTENT.PLAN" | "INTENT.MEMORY" | "INTENT.RELATION"
                                       # | "INTENT.TAG" | "INTENT.NORM_PROPOSE" | "INTENT.OBSERVE"
                                       # | "INTENT.ECON.*"（v1）
    payload: dict                      # 按 cls 解释；货币类不在此产生金额副作用

@dataclass(frozen=True)
class JudgmentRequest:                 # IF-2b 载荷（08 §1.2 I）
    dimension: str                     # 如 "mentor_relation" / "reputation"
    parties: list[AgentId]
    question_ref: str                  # 判定问题规范标识（模板 id）
    envelope: dict                     # 硬内核预给的 options/threshold/rng_branch
    context_ref: str | None            # 上下文正文侧存储引用
```

### 2.2 LLM 冻结层接口（【工程决定】核心机制，落实铁律 C3）

> 机制：**首次生成 → 落不可篡改日志（`LLM_CALL` 成本 + `LLM_JUDGMENT`/内容事件）+ 写内容寻址缓存；重放 → 读缓存/日志，绝不重调 LLM**（`14` §D.2、`00` §5.4/§5.5）。

```python
class FreezeClient:
    """统一 LLM/嵌入调用入口。生活层与软判定层只能经此调用 LLM。"""

    # —— 文本生成（计划/对话/反思/描述）——
    def generate(self, *, purpose: Purpose, prompt: PromptSpec,
                 tier: Tier, max_tokens: int) -> LlmResult: ...

    # —— 定性判定（软判定层；必须先拿 envelope 再做定性判断）——
    def judge(self, *, dimension: str, parties: list[AgentId],
              envelope: Envelope, prompt: PromptSpec) -> JudgmentDecision: ...

    # —— 嵌入（冻结模型版本；结果内容寻址缓存）——
    def embed(self, *, texts: list[str], model_id: str) -> list[Vector]: ...

    # —— 重放模式：只读缓存/日志，不调外部 ——
    def replay_get(self, *, cache_key: str) -> LlmResult | JudgmentDecision | None: ...

@dataclass(frozen=True)
class PromptSpec:
    template_id: str; vars: dict; template_version: int
    def prompt_hash(self) -> str: ...          # 规范 JSON 的 sha256（含模型/temperature/seed）

@dataclass(frozen=True)
class LlmResult:
    text: str; model: str; tokens_in: int; tokens_out: int
    cache_key: str                             # = prompt_hash + model + decode_params
    degraded: bool                             # 预算降级命中（T2→T1→T0）

class Purpose(StrEnum): PLAN="plan"; DIALOGUE="dialogue"; REFLECT="reflect"; DECIDE_T2="decide_t2"; DESCRIBE="describe"
class Tier(StrEnum):     T0="t0"; T1="t1"; T2="t2"
```

**冻结层契约（硬约束）**：
| # | 契约 |
|---|---|
| F1 | 首跑：`generate/judge/embed` 调用前先查内容寻址缓存；未命中才真调，返回后**同时**写缓存并经 IF-2c 交内核**入本回合缓冲区**（P6 COMMIT 落盘）。 |
| F2 | 判定：`judge()` 产出的 `decision` **必须 ∈ `envelope.options`**，否则内核 `submit_judgment` 判为非法 → `SYSTEM_ERROR`（不冻结）。 |
| F3 | 重放：`run(mode="replay")` 下 `FreezeClient` 进入只读态——`generate/judge` 一律走 `replay_get()`，**外部 LLM 调用数恒为 0**（CI 断言）。 |
| F4 | 成本：每次真调经 IF-2c 提交 `LLM_CALL{agent_id,tier,model,tokens_in,tokens_out,trigger,purpose,degraded}`（入缓冲区）；判定另提交 `LLM_JUDGMENT`（三事件分列，`00` §5.5）。 |
| F5 | 嵌入：模型版本冻结并写入 `engine_version`（`00` AR-C5 / `08` D7-6）；`MEMORY_RETRIEVE` 落选择的 `mem_id`，重放不算嵌入（`08` §5.4）。 |
| F6 | 预算：`budget.py` 按 `N×0.5`/回合闸门，超限按优先级降级 `T2→T1→T0` 并写 `degraded=true`。 |

#### 2.2.1 IF-2c：审计/判定载荷提交接口与调用时序（**B4 闭合**）

> **不破坏单一写入口**：`freeze`/`narrative` **只产「待写事件的载荷」**（`AuditPayload`），通过 **IF-2c `submit_audit`** 交内核，**由 Arbiter 写入本回合待提交缓冲区**（P6 COMMIT 统一落盘）。故「内核不调 LLM」与「freeze 不写日志」同时成立，二者经 `contracts` 定义的类型相连。

```python
# ── IF-2c  submit_audit：freeze/叙事层 → 内核；内核 Arbiter 校验后封装并入缓冲区 ──
def submit_audit(payload: AuditPayload, *, engine: KernelHandle) -> int: ...
    # 返回事件的 seq（已分配、在缓冲区中；P6 COMMIT 才真正落盘）
    # payload.kind ∈ {"LLM_CALL","LLM_JUDGMENT","NARRATIVE"}

@dataclass(frozen=True)
class AuditPayload:                    # 定义于 contracts.models
    kind: Literal["LLM_CALL", "LLM_JUDGMENT", "NARRATIVE"]
    actor: AgentId | Literal["SYSTEM"]
    phase: Phase                       # 由其产生相位决定（LLM_CALL/LLM_JUDGMENT=2，NARRATIVE=2/6）
    body: dict                         # 按 kind 解释
    #  LLM_JUDGMENT.body 必带四要素：decision(∈envelope.options) / model / context_digest / frozen=true
```

**调用时序（首跑，一次 LLM 定性判定）**：
1. `life.softjudge` 调 `FreezeClient.judge()`（外部 LLM 调用 **1 次**）。
2. `FreezeClient` 真调前/后经 **IF-2c** 提交 `AuditPayload{kind:"LLM_CALL", body:{tier,model,tokens_in,tokens_out,trigger,purpose,degraded}}` → **Arbiter** 校验并**写入本回合缓冲区**（P2 相位）。
3. 取回 `JudgmentDecision` 后，`life.softjudge` 经 **IF-2c** 提交 `AuditPayload{kind:"LLM_JUDGMENT", body:{decision, model, context_digest, frozen:true, envelope, rng_branch, parties, effect_ref}}` → **Arbiter 校验 `decision ∈ envelope.options`**，通过则**入缓冲区** `LLM_JUDGMENT(frozen=true)`；不通过 → `IllegalJudgment`（记 `SYSTEM_ERROR`，不冻结）。
4. 数值后果由内核据 `decision + RNG` **确定性推导**，作为**独立事实事件**（如 `RELATION_CHANGE`）入缓冲区，`effect_ref` 关联。

**重放**：`FreezeClient` 进只读态 → 步骤 1 走缓存/日志（**外部调用=0**）；`LLM_JUDGMENT` 由 IF-6 折叠读回，**不重放提交**。

> **`LLM_CALL` 由谁在何时产出**：**由 `FreezeClient`（冻结层）构造载荷，经 IF-2c 交内核 Arbiter，在 `P2 DECIDE` 相位内写入本回合待提交缓冲区**（与调用同相位，保证 `mono_ts` 相位有序）；**P6 COMMIT 是唯一 append 点**，按全局固定顺序一次性落盘。**Arbiter 是唯一写入者**，铁律 C1 不动。**整回合回滚**（hook 异常/守恒失败）→ **丢弃整个缓冲区（含 P2 的 `LLM_CALL`）**，仅追加 `SYSTEM_ERROR` / `ECONOMY_INVARIANT_VIOLATION`，世界状态不变。

### 2.3 中央裁决器 hook 链接口（【已定】，v1/03 §2.2 + 08 §2.2）

```python
@dataclass(frozen=True)
class Ctx:                                          # 传入每个 hook；唯一随机源
    seed: int; round: Round; time_cfg: TimeConfig; config: Config
    def rng(self, stream_id: str, seq: int, n: int) -> list[int]: ...   # SplitMix64

@dataclass(frozen=True)
class Delta:                                        # hook 返回：新 state + 产出的 events + 待结算意图
    state: WorldState
    events: list[Event]
    pending_intents: list[Intent] = field(default_factory=list)         # 仅生活 hook 用于交 4.x
```

**Post-hook 契约（沿用 v1 I1–I5，必须满足）**：纯函数（相同 `(state,round,ctx)` 恒同）；幂等键 `(round, phase, hook_name)`；不读墙钟/网络/环境变量；随机只经 `ctx.rng`；事件必带完整 `payload`；异常 → 整回合回滚 + `SYSTEM_ERROR`。

**P4 ARBITRATE（4.1–4.8，顺序与语义冻结，`08` §2.4）**：
```python
def settle_market(state, round, ctx) -> Delta: ...       # 4.1 撮合/清算/原子转账（含反作弊打标 flags）
def settle_obligations(state, round, ctx) -> Delta: ...  # 4.2 到期债务/计息/扣款（含续命贷）
def apply_tax(state, round, ctx) -> Delta: ...           # 4.3 铸币判定→收入税→财富税→UBI
def apply_metabolism(state, round, ctx) -> Delta: ...    # 4.4 每回合代谢消耗
def apply_penalty(state, round, ctx) -> Delta: ...       # 4.5 负资产/作弊惩罚
def check_lifecycle(state, round, ctx) -> Delta: ...     # 4.6 破产/濒死/归零标记
def resolve_revival(state, round, ctx) -> Delta: ...     # 4.7 复活/续命贷发放
def check_death(state, round, ctx) -> Delta: ...         # 4.8 最终死亡判定（本回合终局）
```

**Phase 3.5 LIFE（L1–L7，顺序固定，`08` §2.2/§2.3；挂 3 与 4 之间）**：
```python
def advance_time(state, round, ctx)     -> Delta: ...    # L1 派生 week/day/slot；跨日/周发 TIME_MARK
def resolve_schedule(state, round, ctx)  -> Delta: ...   # L2 到期 slot → ACTIVITY_STARTED intent
def settle_activities(state, round, ctx) -> Delta: ...   # L3 活动结算 → resource_intents[] 交 4.x
def apply_needs(state, round, ctx)      -> Delta: ...    # L4 需求衰减/满足 → NEED_UPDATE
def update_relations(state, round, ctx) -> Delta: ...    # L5 → RELATION_CHANGE / RELATION_ENCOUNTER
def write_memories(state, round, ctx)   -> Delta: ...    # L6 MEMORY_WRITE/OBSERVATION/REFLECT
def emit_tags(state, round, ctx)        -> Delta: ...    # L7 TAG_EMITTED / NORM_* 阈值判定
```

> **依赖倒置**：`kernel` **不 import** `life`；life hook 由 `orchestration`/注册表在启动时注入 `kernel.arbiter` 的 hook 表。内核只持 `hook(state,round,ctx)->Delta` 的接口。

**阶段调度（P0–P6，`08` §2.4）**：
```python
class Scheduler:
    def run_round(self, state: WorldState, round: Round) -> tuple[WorldState, list[Event], TurnSeal]:
        # P0 ROUTE → P1 PERCEIVE → P2 DECIDE → P3 COMMUNICATE
        # → P3.5 LIFE(L1..L7) → P4 ARBITRATE(4.1..4.8) → P5 LIFECYCLE → P6 COMMIT
        ...
    def run(self, seed: int, rounds: int, cfg: Config) -> RunResult: ...
```

### 2.4 感知作用域接口（【已定】，最新版 08 §3.5 / R1–R5）

```python
def location(agent_id: AgentId, t: Round, *, log: ReadOnlyLog) -> str: ...
    # 由 PLACE_MOVE/PLACE_ARRIVED 折叠的占用时间线（初始=residence），纯函数

def visible_events(agent_id: AgentId, *, log: ReadOnlyLog, t: Round, cfg: Config) -> list[Event]:
    # = 直接可见（PERCEPTION_SCOPE 谓词）∪ 记忆链闭包 ∪ LLM_JUDGMENT.parties
    #   一阶「听说」(heard_events, 沿 refs[] 反向闭包) 标 spec=true，永不计入本函数返回值
    ...

# config: PERCEPTION_SCOPE: {event_type -> visibility_class}
# visibility_class ∈ {global, place_local, members, private, participants_only, subject_only}
```

- `PERCEPTION_SCOPE` 表落 `config/`，**版本入 `engine_version`**（比照 TOPOLOGY）。
- D3 白名单默认仅 `AGENT_DIED`（可配）；`GROUP_CREATED{members[]}` 使 `members` 可见性按时点重算（组队默认不可变）。
- 审计：POV 报告附 `visible_event_digest` + `scope_table_version`。

### 2.5 编排 / 观测 / 叙事 / 轨迹 入口签名

```python
# ── orchestration（B/兼A）──
def run(seed: int, config: Config, rounds: int, *, mode: Literal["first","replay"]="first") -> RunResult: ...
def replay(log_path: str, *, engine_version: EngineVersion) -> WorldState: ...
def run_experiment(spec: ExperimentSpec) -> ExperimentReport: ...   # A/B 双胞胎 × 多 seed

# ── emergence（L2，只读）──
def metrics(log: ReadOnlyLog, t: Round, time_cfg: TimeConfig) -> Snapshot: ...              # IF-4
def emergence_report(log, t, params) -> Report: ...
def wellbeing_report(log, t, params) -> Report: ...

# ── narrative（C）──
def narrate(fact_event_seqs: list[int], *, side: SideStore, style: str="chron") -> NarrativeArtifact: ...  # IF-7

# ── traj（A，占位）──
def export_trajectories(log: ReadOnlyLog) -> Iterator[TrajectorySample]: ...   # 反泄漏裁剪
def reward_calculator(log: ReadOnlyLog) -> dict[str, Signal]: ...               # 只读，F 类禁用
```

### 2.6 类型化错误与审计事件

> 错误类型定义于 `contracts.errors`（B1，供 kernel/life/emergence 共用，避免 kernel 被下层直接 import）。

```python
class HashChainBroken(Exception): ...
class UnknownEventType(Exception): ...        # 重放/统计遇未知类型立即报错（08 X4）
class RoundRollback(Exception): ...           # hook 异常 → 整回合回滚 + SYSTEM_ERROR
class IllegalJudgment(Exception): ...         # decision ∉ envelope.options（B4，不冻结）
```
审计事件（08 §1.2）：`SYSTEM_ERROR{where,detail}`、`INTENT_REJECTED{agent_id,intent_class,reason,requested}`、`LLM_CALL`、`DROPPED`、`ECONOMY_INVARIANT_VIOLATION`。

### 2.7 三条铁律符合性核对（接口层）

| 铁律 | 接口层保障 |
|---|---|
| **C1 引擎确定性、非 LLM** | 内核包不 import LLM/`freeze`；`arbiter`/hook 只产 `Delta`；LLM 只藏在 `FreezeClient`（生活层/软判定层） |
| **C2 同日志逐位一致** | `replay(log)` 纯折叠、不重跑 hook、不重调 LLM；`emit` 入本回合缓冲区、**P6 COMMIT 唯一 append 点**；`metrics` 纯只读函数 |
| **C3 LLM 判定冻结** | 判定唯一出口 IF-2b + `F2`（decision ∈ envelope.options）+ `LLM_JUDGMENT.frozen=true`；重放经 IF-6 读回、`F3` 断言外部调用=0 |
| **单一写入口（B4）** | freeze/叙事**只经 IF-2c 提载荷**、**不写日志**；内核 **Arbiter 是唯一写入者**（入缓冲区，P6 落盘）且**不调 LLM**；二者由 `contracts` 类型相连（`AuditPayload`） |

*（§2 接口契约 完成）*

---

## 3. 数据模型与存储

> 设计目标：**(a) 事件日志为唯一权威事实源；(b) 大数据（记忆正文/嵌入/叙事正文/prompt）出主日志、走内容寻址侧存储；(c) 状态可快照节流、可从日志重建；(d) 全部可审计、可重放。**

### 3.1 事件日志（哈希链，`v1/03` §6.1 + `08` §5）

- **格式**：`data/runs/<run_id>/event_log.jsonl`，**append-only**，每行一条 `Event`（规范 JSON）。
- **唯一 append 点 = P6 COMMIT**（D1 口径，见 §1.4/§2.2.1）：本回合事件先入**待提交缓冲区**，P6 按全局固定顺序一次性追加；**整回合回滚不落盘**（含 P2 的 `LLM_CALL`）。
- **哈希链**：`event.hash = sha256(canonical_json({seq,round,phase,actor,type,payload,mono_ts,prev_hash}))`；`prev_hash` 指向上一条 `hash`；链首 `prev_hash = GENESIS_HASH`（常量）。
- **篡改检测**：任一 `prev_hash != 前一条.hash` → `HashChainBroken`，拒绝重放（`v1/03` §6.4）。
- **可选锚定**：每回合 `merkle_root(round)` 供外部锚定（不进主链）。

### 3.2 turn_seal（每回合封条，【工程决定】）

```jsonc
// data/runs/<run_id>/turn_seal.jsonl（每回合一条）
{ "round": 42, "first_seq": 1764, "last_seq": 1812,
  "round_hash": "sha256:...",          // = sha256(concat(e.hash for e in round 42))
  "prev_seal_hash": "sha256:..." }     // 指向上回合 seal 的 round_hash（封条链）
```
- **用途**：① 单回合快速校验、断点续跑定位；② 前端回放按回合切块；③ 冻结判定的「回合视图」边界。封条本身**不进事件链**（避免自指），独立成链。
- **校验**：重放前先沿封条链校验完整性，再逐事件折叠。

### 3.3 侧存储（content-addressed，【工程决定】）

> 铁律：**主日志只存引用（body_ref/embed_ref/prompt_hash），正文出主日志**（`00` AR-C4、`08` §5.2/§5.4/XT-3）。

```
data/runs/<run_id>/side_store/
  blobs/<sha256[:2]>/<sha256>            # 内容寻址：记忆正文、印象叙述、叙事正文、目标描述、上下文
  prompts/<prompt_hash>.json             # 规范 prompt（含 template_id/version/vars/model/温度）
```
- **寻址**：`ref = "sha256:<hex>"`；同一内容多处引用只存一份。
- **审计**：事件中的 `body_ref` 与 blob 内容哈希一致可校验；`NARRATIVE` 元数据的 `anchor_digest` 覆盖事实锚点。
- **生命周期**：blob 只增不删（append-only）；可整体打包入 run 归档。

### 3.4 向量索引（只被决策路径读，【工程决定】）

```
data/runs/<run_id>/vector_index/
  embeddings.npy            # mem_id 顺序对应的向量矩阵（float32）
  mem_ids.json              # 行号 -> mem_id
  index_manifest.json       # model_id, dim, count, embed_model_version
```
- **只写路径**：`freeze.embed()`（首跑）→ 索引；**只读路径**：`life.memory` 检索。
- **确定性边界（关键）**：**向量索引不进判定与统计**——重放折叠的是 `MEMORY_RETRIEVE` 已落日志的 `mem_id` 列表，**永不重算嵌入**（`08` §5.4）。索引即使因模型漂移重排，也不影响 `replay(log)`。
- P0 规模（N=20，记忆数千级）用**本地精确检索**即可（见 §4.3 选型）。

### 3.5 状态快照（节流，【工程决定】）

```
data/runs/<run_id>/snapshots/snap_<round>.json     # WorldState 规范 JSON（每 K 回合，默认 K=100）
```
- **用途**：性能缓存（`v1/03` P2）；断点续跑；非权威——权威仍是日志。
- **重建**：`state(t) = fold(apply_event, nearest_snapshot, events(snap_round..t))`。
- **校验**：CI 对同一日志断言「从快照重建 == 从头重放」。

### 3.6 config 核心五件 + 扩展两件 + engine_version 指纹

**config 文件清单**（`config/`）——**核心五件**：`personas` / `places` / `topology` / `activity_templates` / `policy`；**扩展两件**：`perception_scope` / `narrative_weights`。**七项全部纳入 `engine_version` 版本指纹**（扩展两件为最新版 08 权威新增项，不可省略）。

| 文件 | 类别 | 内容 | 权威来源 |
|---|---|---|
| `personas.json` | 核心 | M1 人格/身份（大五/价值观/技能/背景/目标倾向/需求初值） | `06` §2.2 |
| `places.json` | 核心 | 17 场所 + 营业时段 + 容量 + affordances | `00` §2.2、`06` §5 |
| `topology.json` | 核心 | 17×17 邻接 / `travel_ticks` 常数矩阵（AR-D2 建议落常数） | `00` §2.3、`08` §5.6 |
| `activity_templates.json` | 核心 | M4 活动模板库（12-event-lineage） | `12`、`06` §4.3 |
| `policy.json` | 核心 | 政策参数层（税/利率/UBI/惩罚阈值/规范阈值/N×0.5 预算） | `09`、`16` §6 |
| `perception_scope.json` | 扩展 | `PERCEPTION_SCOPE` 表（可见性分类，最新版 08 R2） | `08` §3.5 |
| `narrative_weights.json` | 扩展 | 戏剧性度量权重（NT-C2，纳入指纹） | `08` §4.0、`17` |

**engine_version 指纹**（`config/engine_version.json`，重放前必须匹配）：

```jsonc
{
  "engine_semver": "1.2.0",
  "kernel_commit": "<git-sha>",
  "canonical_json": "sortkeys+sha256",
  "rng": "splitmix64",
  "time_config_hash": "sha256:...",       // ROUNDS_PER_SLOT/SLOTS_PER_DAY/DAYS_PER_WEEK/DAY_TYPES
  "topology_hash": "sha256:...",          // topology.json
  "perception_scope_hash": "sha256:...",  // perception_scope.json
  "activity_templates_hash": "sha256:...",
  "policy_hash": "sha256:...",
  "narrative_weights_hash": "sha256:...",
  "config_hash": "sha256:...",            // config 七项（核心五件+扩展两件）合并哈希
  "llm_models": {"t1":"...","t2":"...","judge":"...","describe":"..."},
  "embedding_model": "frozen-v1",
  "prompt_registry_hash": "sha256:...",   // prompts 模板集
  "event_schema_hash": "sha256:..."       // 事件类型→字段 schema 表
}
```
- `engine_version_digest = sha256(canonical_json(...))`；`RunResult` 与日志头部各存一份，**重放前断言一致**，不一致 → 拒绝重放（`v1/03` §6.2 步骤1）。
- **冻结项**：`embedding_model` / `llm_models` 版本冻结（`08` D7-6、AR-C5）——否则「同 seed 首跑」不可复现。

### 3.7 存储校验与不变量（并入 `v1` §5.9 + `08` §6 + `06` L1–L8）

| # | 不变量 | 校验点 |
|---|---|---|
| I1 | 哈希链连续、`seq` 严格递增 | P6 COMMIT / replay 前 |
| I2 | 货币守恒 `ΣM` 式(1)=0（含银行库存项，待 Q1 裁决） | P6 COMMIT（失败→整回合中止） |
| I3 | 交易原子性 式(2) | 4.1 |
| I4 | 状态白名单转移（6 值） | 4.6 |
| I5 | 生活层 8 条 L1–L8（关系/需求值域、场所合法、日程一致、记忆 append-only、观测锚点、统计无 LLM、意图/事实分离） | 对应 hook + P6 |
| I6 | 记忆 `mem_id` 全局唯一、只增不改 | L6 / P6 |
| I7 | 统计无 LLM 判定 `llm_judged_metric_count==0`（仅 econ/lifecycle/life/emergence） | `emergence` 自检 |

*（§3 数据模型与存储 完成）*

---

## 4. 关键技术选型与备选比较（decision matrix）

**统一评分口径**：每项候选按同一组权重、**0–5 同向评分**（越高越好，5=最优/最低风险）评分，加权求和取最高者为推荐；同时给出**复杂度与演进成本**。权重（和为 1.00）针对本项目铁律定制：

| 权重维度 | 权重 | 含义 |
|---|---|---|
| 铁律契合度 | 0.30 | 是否天然满足确定性内核 / 同日志逐位一致 / LLM 判定冻结 |
| 复用与生态 | 0.20 | 能否复用 GA/AI Town 资产、社区与维护活跃度 |
| 复现与可审计 | 0.20 | 跨环境/跨进程复现能力、审计友好度 |
| 交付速度 | 0.15 | P0 单机单周跑通的落地速度 |
| 演进成本 | 0.15 | 演到长窗/多 seed/B 编排/A 训练的边际成本（越低越高分） |

### 4.1 语言 / 运行时

| 候选 | 铁律 .30 | 复用 .20 | 复现 .20 | 速度 .15 | 演进 .15 | **加权** | 证据备注 |
|---|---|---|---|---|---|---|---|
| **A. Python 3.11 + uv**（推荐） | 4 | 5 | 4 | 5 | 5 | **4.55** | GA 主干为 Python（Apache-2.0，`14` §A.2）；v1 内核契约（`03`）已是 Python 伪代码；整数运算/SplitMix64 全语言可复现 |
| B. TypeScript/Node（AI Town 栈） | 3 | 3 | 3 | 3 | 3 | **3.00** | 引擎范式同构、前端同源；但 GA 主干需移植，Python 生态（numpy/sklearn）统计不便 |
| C. Rust（内核）+ Python（Agent） | 3 | 1 | 5 | 2 | 2 | **2.75** | 内核确定性最佳，但双语言桥接成本高、复用 GA 需 FFI，过度工程 |

**推荐 A**。**复杂度**：低（GA 直接适配）。**演进成本**：内核用整数/定点保证与语言无关的复现；若未来需高性能内核，可把 `kernel` 局部替换为 Rust 扩展而**不动契约**（契约已用规范 JSON 与整数定义，语言中立）。

### 4.2 LLM 接入与冻结层实现

| 候选 | 铁律 .30 | 复用 .20 | 复现 .20 | 速度 .15 | 演进 .15 | **加权** | 证据备注 |
|---|---|---|---|---|---|---|---|
| **A. 自建薄 `FreezeClient`（unified wrapper）+ 内容寻址缓存**（推荐） | 5 | 3 | 5 | 4 | 4 | **4.35** | `14` §D.2 明确「把三仓库 LLM 调用点收敛为冻结层」；可精确实现 `prompt_hash`/`LLM_JUDGMENT.frozen`/重放不重调 |
| B. 基于 LiteLLM 封装 | 4 | 4 | 4 | 5 | 4 | **4.15** | 多 provider 现成、可插拔；但需在其上再套一层冻结/审计，仍要自写缓存与判定冻结 |
| C. 直接调用各家 SDK（无统一层） | 1 | 3 | 2 | 3 | 2 | **2.10** | 违背「所有 LLM 产物冻结落日志」，反作弊/审计不可控，**排除** |

**推荐 A**（provider 层可插入 B 的适配器，二者不互斥）。**复杂度**：中（缓存/哈希/降级）。**演进成本**：低——新增 provider 只实现 adapter；模型升级只改 `engine_version.llm_models`。

### 4.3 向量库（记忆检索）

| 候选 | 铁律 .30 | 复用 .20 | 复现 .20 | 速度 .15 | 演进 .15 | **加权** | 证据备注 |
|---|---|---|---|---|---|---|---|
| **A. 本地精确检索（numpy 矩阵 + `top_k`）**（推荐 P0） | 5 | 4 | 5 | 5 | 3 | **4.45** | P0 N=20、记忆数千级，精确检索 O(N) 完全够；**嵌入结果本就不进判定**，无需 ANN；复现最干净 |
| B. sqlite-vec / FAISS 本地索引 | 4 | 4 | 4 | 4 | 5 | **4.15** | 单文件、无服务；ANN 有近似误差（但检索命中已落日志，不影响复现）；适合长窗记忆增长 |
| C. Convex 向量库（AI Town 原栈） / Qdrant 服务 | 3 | 5 | 2 | 3 | 3 | **3.25** | AI Town 现成但耦合 Convex（`14` U5）、外部服务引入非确定性运维面；与「单机优先」冲突 |

**推荐 P0=A，长窗切换 B**（接口 `VectorIndex` 抽象，检索命中 `MEMORY_RETRIEVE` 落日志 → **换库不影响复现**）。**复杂度**：低。**演进成本**：低（抽象接口 + 命中落日志的解耦设计）。

### 4.4 序列化（规范 JSON）

| 候选 | 铁律 .30 | 复用 .20 | 复现 .20 | 速度 .15 | 演进 .15 | **加权** | 证据备注 |
|---|---|---|---|---|---|---|---|
| **A. 规范 JSON（键排序 + 无空格 + 定点浮点）→ SHA-256**（推荐） | 5 | 5 | 5 | 5 | 4 | **4.85** | 直接继承 `v1/03` §6.1/§6.3（规范 JSON + 哈希链 + `round(x,6)`）；跨语言可解析、审计友好 |
| B. CBOR / 二进制 | 4 | 2 | 4 | 4 | 4 | **3.60** | 更紧凑；但与「可读审计 + 现有 v1 契约」不符，需全链路替换 |
| C. Protobuf | 3 | 2 | 3 | 3 | 4 | **2.95** | 强类型但 canonical 化需额外工作，且偏离既有契约 |

**推荐 A**。**复杂度**：低（`canonical_json.py` 单模块）。**演进成本**：低。

### 4.5 测试 / CI（复现门禁）

| 候选 | 铁律 .30 | 复用 .20 | 复现 .20 | 速度 .15 | 演进 .15 | **加权** | 证据备注 |
|---|---|---|---|---|---|---|---|
| **A. pytest + 黄金日志重放门禁 + import-linter 边界测试**（推荐） | 5 | 4 | 5 | 4 | 4 | **4.45** | 直接实现 `v1/03` §6.3「两次 metrics 字节相等」+ `08` X4；import-linter 强制 §1.3 依赖铁律 |
| B. 上述 + Hypothesis 属性测试 | 5 | 3 | 5 | 3 | 3 | **4.05** | 属性测试（守恒/幂等/链完整）更严；建设成本更高，可 P1 追加 |
| C. 仅手写回归脚本 | 3 | 5 | 3 | 4 | 2 | **3.40** | 起步快，但门禁不足、易漏复现回归 |

**推荐 A（P1 叠加 B）**。**复现门禁（硬）**：CI 对 `golden_logs/` 跑 `replay(log)` 断言状态哈希相等、`metrics()` 两次字节相等、`freeze` 外部调用数=0（重放态）。**复杂度**：中。**演进成本**：低。

### 4.6 前端（PixiJS 迁移 vs 自建）

> **用户对 PixiJS 像素小镇可视化特别期待**（Leader 确认）。

| 候选 | 铁律 .30 | 复用 .20 | 复现 .20 | 速度 .15 | 演进 .15 | **加权** | 证据备注 |
|---|---|---|---|---|---|---|---|
| **A. 迁移 AI Town PixiJS（MIT）+ 自建审计观测台**（推荐） | 4 | 5 | 4 | 4 | 4 | **4.20** | AI Town 前端 MIT、像素小镇 + 历史平滑回放可直接用（`14` §B.7/§E.1）；审计观测台自建（只读日志重算）；契合用户期待 |
| B. 全自建（Canvas/WebGL） | 5 | 1 | 5 | 2 | 3 | **3.35** | 完全可控但工作量大、无现成素材（精灵/地图） |
| C. GA Django 前端 | 3 | 2 | 2 | 2 | 2 | **2.35** | 较旧、依赖重（`14` §B.7），仅参考 |

**推荐 A**。**复杂度**：中（前端解耦 Convex，改接只读事件流 API）。**演进成本**：中——前端与内核解耦（只读 `event_log/turn_seal` + 指标快照），前端演进不影响内核。**P0 交付**：`town-viewer` 能按回合回放 N=20 单周（读 `turn_seal` 切块）。

### 4.7 选型汇总

| 维度 | 推荐 | 主备选 | 关键理由 |
|---|---|---|---|
| 语言/运行时 | **Python 3.11 + uv** | TS/Node | GA 主干 + v1 内核契约同源 |
| LLM 冻结层 | **自建 `FreezeClient`** | LiteLLM 封装 | 铁律需要精确冻结/审计 |
| 向量库 | **本地精确检索（P0）** | sqlite-vec/FAISS | P0 规模小、复现最干净 |
| 序列化 | **规范 JSON + SHA-256** | CBOR | 继承 v1 契约、可审计 |
| 测试/CI | **pytest + 黄金日志门禁 + import-linter** | +Hypothesis | 直接实现字节一致门禁 |
| 前端 | **AI Town PixiJS 迁移 + 自建审计台** | 全自建 | MIT 可复用、用户期待 |

*（§4 技术选型 完成）*

---

## 5. P0 实现任务分解（N=20 世界单周跑通）

> 目标（`16` §5 P0）：**N=20 单小镇、单周（84 回合）可重复 run；护栏判据全过；`replay(log)` 与 `metrics()` 一致。** 成本量级：纯推理 ≈2×10⁶ token/单周。
> 责任映射（名册）：**kernel-dev**（内核/账本/复现）、**life-layer-dev**（GA 主干 M1–M7）、**freeze-layer-dev**（冻结层/预算）、solution-architect（契约/集成分工）。

### 5.1 子任务与验收标准

| ID | 子任务 | 负责 | 依赖 | 验收标准（可测） |
|---|---|---|---|---|
| **P0-1** | 仓库脚手架 + **`contracts` 协议类型** + `canonical_json` + `rng` + `engine_version` 指纹 | kernel-dev | — | `contracts` 被四包依赖且自身零业务依赖；`canonical_json` 单测（键排序/定点/幂等）；`draw()` 跨进程同 `(seed,stream,round,seq)` 输出一致；`engine_version_digest` 稳定 |
| **P0-2** | 事件日志哈希链 + `turn_seal` + `replay` + `invariants` | kernel-dev | P0-1 | 篡改任一事件→`HashChainBroken`；`replay` 不重跑 hook；守恒校验失败→整回合回滚 + `SYSTEM_ERROR` |
| **P0-3** | Scheduler P0–P6 + WorldState + Snapshot + **RoundBuffer（P6 唯一 append）** + hook 注册表（依赖倒置） | kernel-dev | P0-1 | 六阶段顺序固定；`(round,phase,hook)` 幂等；emit 入缓冲区、**P6 唯一落盘**；整回合回滚丢弃缓冲区（含 P2 `LLM_CALL`）；从快照重建==从头重放 |
| **P0-4** | 经济 hook 4.1–4.3（复用 v1 01 机制）+ 反作弊打标 `flags` | kernel-dev | P0-2,P0-3 | 撮合/税/UBI 事件齐全；`W_wash=4` 打标可重放；成交/转账原子性式(2) 通过 |
| **P0-5** | 生命周期 hook 4.4–4.8（复用 v1 02：代谢/惩罚/判死/续命/安全阀） | kernel-dev | P0-2,P0-3 | status 白名单转移；`E_eff` 判死口径一致（先税后代谢）；C1–C10 注入可标记 |
| **P0-6** | LLM 冻结层 `FreezeClient` + 缓存 + 预算闸门 + provider 适配 + **IF-2c 载荷提交** | freeze-layer-dev | P0-1 | 首跑经 IF-2c 提交、**由 Arbiter emit** `LLM_CALL`；判定落 `LLM_JUDGMENT(frozen)` 且 `decision∈options`；重放态外部调用数=0；超预算降级 `degraded=true` |
| **P0-7** | 生活层最小可信内核 M1+M4+M5（人格/日程/场所昼夜）+ L1–L3 | life-layer-dev | P0-3,P0-6 | 从 GA plan/execute/maze 适配；`SCHEDULE_PLANNED`/`ACTIVITY_*`/`PLACE_MOVE` 落日志；日程一致性 L4 通过 |
| **P0-8** | M2 记忆流（三因子检索/反思）+ 向量索引 + M3 关系（数值确定性）+ M7 目标/需求 | life-layer-dev | P0-7 | 检索命中 `MEMORY_RETRIEVE` 落日志；关系值域 L1 通过；需求值域 L2 通过；反思阈值 `θ_reflect=150` |
| **P0-9** | 软判定层（IF-2b/IF-6）+ 叙事层（IF-7）+ `visible_events`/`PERCEPTION_SCOPE` | life-layer-dev | P0-6,P0-8 | 判定 `decision∈envelope.options`；`NARRATIVE.affects_state=false`；`visible_events` 无 LLM、可重放 |
| **P0-10** | 观测层 M8 指标 + `emergence_report`/`wellbeing_report`（只读） | sim-engine-stats-architect | P0-2 | `llm_judged_metric_count==0`；两次 report 字节相等；import-linter 断言观测层只读 |
| **P0-11** | config（核心五件 + 扩展两件：`perception_scope`/`narrative_weights`）+ N=20 种子世界（personas/places/topology） | life-layer-dev | P0-1 | config 校验（拓扑对称/三角不等式）；七项齐全并入 `config_hash`；N=20 生成、容量合理 |
| **P0-12** | 编排入口 `run/replay/metrics` CLI + 运行目录产物（日志/封条/快照/报告） | kernel-dev | P0-3,P0-6 | `make run` 产出完整 run 目录；`make replay` 复现；`make metrics` 出快照 |
| **P0-13** | 测试与复现门禁（pytest + 黄金日志 + import-linter 边界） | kernel-dev + 全员 | P0-2,P0-6,P0-10 | CI 绿：重放状态哈希相等 / metrics 字节相等 / 重放 LLM 调用=0 / 边界无环 |
| **P0-14** | **N=20 单周验收 run**（护栏 + 观测 + 复现） | sandbox-test-lead | P0-11,P0-12,P0-13 | `09` §1.1 护栏全过（存活率/Gini/坏账/通胀/LLM≤N×0.5/守恒/复现/反作弊/稳定）；种子级联可观测 |
| **P0-15** | 前端 `town-viewer`（PixiJS 迁移）+ 只读回放适配 | （前端，待分派） | P0-12 | 按 `turn_seal` 分块回放 N=20 单周；不写世界；审计台能展示核心指标 |

### 5.2 依赖图（DAG）

```
P0-1 ─┬─► P0-2 ─┬─► P0-4 ─┐
      ├─► P0-3 ─┼─► P0-5 ─┤
      │          └─────────┼─► P0-12 ─► P0-15
      ├─► P0-6 ─┬─► P0-7 ─► P0-8 ─► P0-9 ─┐
      │          │          └─────────────┼─► P0-13 ─► P0-14
      └─► P0-11 ─┘                        │
                     P0-10 ───────────────┘
P0-2 ─► P0-10
```

- **关键路径**：P0-1 → P0-3 → P0-6 → P0-7 → P0-8 → P0-9 → P0-13 → P0-14。
- **可并行**：{P0-4,P0-5} 与 {P0-7,P0-8,P0-9} 与 P0-10、P0-11 相互独立（只要 P0-1/P0-2/P0-3 就绪）。

### 5.3 P0 里程碑与放行

| 里程碑 | 内容 | 放行条件 |
|---|---|---|
| M0 | 内核可跑（P0-1~P0-5） | 无生活层下，空世界 T 回合守恒、哈希链、重放一致 |
| M1 | 冻结层 + 生活层接通（P0-6~P0-9） | 单 Agent 能感知→决策→落事件→重放一致 |
| M2 | N=20 单周可跑（P0-10~P0-13） | `make run/replay/metrics` 全通 + CI 门禁绿 |
| M3 | **P0 验收（P0-14）** | `09` §1.1 护栏全过 + 观测判据成立 + 复现一致 |

*（§5 P0 任务分解 完成）*

---

## 6. 关键技术风险与备选方案、演进成本

### 6.1 关键技术风险清单（P0 视角）

| ID | 风险 | 级别 | 影响 | 缓解 / 备选方案 | 验证方法 |
|---|---|---|---|---|---|
| **R-1** | **LLM 成本超预算**（生活层显著抬高，`00` AR-C5/AR-D5） | 高 | P0 跑不动/成本失控 | 每回合闸门 `≤N×0.5`；分层降级 `T2→T1→T0`；记忆压缩档案 + `top_k=8`；备选：缩小窗口/降 `ROUNDS_PER_SLOT`（须配死亡压力档） | 日志 `LLM_CALL` 聚合 vs 预算；`degraded` 率统计 |
| **R-2** | **冻结层缓存/哈希实现偏差** → 重放仍调 LLM | 高（阻塞 C3） | 复现失败、成本翻倍 | 内容寻址缓存 + `prompt_hash`（含模型/温度/seed）；重放态**外部调用计数断言=0** | CI：重放态 `llm_external_calls==0` |
| **R-3** | **嵌入模型漂移**导致跨环境检索差异 | 中 | 同 seed 首跑不齐（可接受，但影响分析） | 冻结 `embedding_model` 入 `engine_version`；检索命中落 `MEMORY_RETRIEVE`（**统计永不重算嵌入**） | `engine_version` 校验；同日志 replay 一致 |
| **R-4** | **侧存储与主日志不同步**（body_ref 悬挂） | 中 | 审计/重放怀疑 | 内容寻址 `sha256`；run 目录整体打包；`side_store` 校验脚本 | P6/invariant 校验 body_ref 存在且哈希一致 |
| **R-5** | **hook 异常导致部分结算**（破坏原子性） | 高 | 状态污染 | v1 I4：整回合回滚 + `SYSTEM_ERROR`；CI 注入异常用例 | 单测：hook raise → 本回合 delta 全丢弃 |
| **R-6** | **观测层被偷偷引入写路径/LLM** | 高（阻塞 C1/C3） | 判定不纯 | import-linter 边界（§1.3 规则 2/3）；`emergence` 白名单仅纯函数 | CI：边界测试 + `metrics` 内 `llm_calls==0` |
| **R-7** | **跨语言/跨进程浮点不确定** | 中 | 字节不一致 | 金额整数（mu）；统计最后一步定点 `round(x,6)`；禁止语言内置浮点 RNG | CI：两次 `metrics()` 字节相等 |
| **R-8** | **长窗记忆增长 → token/存储膨胀** | 中 | 长窗成本上升 | 摘要限流/压缩档案；快照节流；列式压缩日志；向量库切 FAISS | 长窗实测 token/内存曲线 |
| **R-9** | **多 seed 实验编排不确定**（置换检验种子） | 中 | B 结论不可复现 | 置换排列种子固定；`experiment.py` 使所有随机经 `ctx.rng` | 同 `(log,params)` report 字节相等 |
| **R-10** | **训练信号污染**（F 类或未来事件泄漏） | 中 | A 线数据无效 | 硬约束：F 类不得作训练信号（`16` §3.3）；导出器反泄漏裁剪 | 导出器单测：样本不含未来事件 |
| **R-11** | **`PERCEPTION_SCOPE` 可见性判定错误** | 中 | 传播/涌现失真 | 可见性为纯函数 `visible_events`（无 LLM）；版本入指纹；POV 审计 digest | 可见性单测 + `visible_event_digest` 核对 |
| **R-12** | **`relevance` 为词法近似、非语义**（T48 实测：内网端点不支持 `/embeddings`、本地无 torch） | 中 | 「想起相关往事」的**语义相关性不成立** → 行为可信度 / A 线训练数据质量受损 | 当前：**确定性词法相关度** `frozen://lexical-relevance-v1`（token 级 feature hashing + 标签/关键词重叠，**可解释、可复现**）；**真语义相关性未验证**。备选：方案① 本地 sentence-transformers（**P1 升级项**，需联网装 torch+权重） | A/B：同记忆集 **lexical vs 真嵌入** 检索命中对比（模板 `code/scripts/embed_ab_compare.py`）；文档见 `v1.2/real-llm-validation.md §8` |

### 6.2 演进路线（单机单周 → 长窗 / 多 seed / B 编排 / A 训练）

| 阶段 | 变化 | 结构性要求（本蓝图已预留） | 演进成本 |
|---|---|---|---|
| **P0 → 长窗（4–12 周）** | 回合 84→336/1008 | 快照节流 + 日志列式压缩 + 向量库切 `sqlite-vec/FAISS`（接口 `VectorIndex` 不变） | 低（配置 + 换向量后端） |
| **P0 → 多 seed** | 1→≥3 seed（S3 符号检验） | `run(seed,...)` 已参数化；`experiment.py` 横切 | 低（编排层） |
| **P0 → B 实验编排** | A/B 双胞胎 + 政策档 | `policy.json` 参数化；`experiment.py` 同 seed 去种子事件对照；置换检验固定种子 | 中（编排 + 统计器，不改内核） |
| **P0 → A 训练接入** | 轨迹导出 + 奖励 + 离线训练 | `traj` 包占位；只读日志；反泄漏裁剪；`reward_calculator` 确定性 | 中高（训练算力 + 管线，`16` G1 需立项） |
| **P0 → N=20→50（展望）** | 规模放量 | 容量/预算随 N 线性缩放（`09` §5 L1/L2/L3 门禁） | 中（容量复核 + 预算重算） |
| **P0 → C 叙事层增强** | 故事线/戏剧度量 | `narrative/` 物理分包（N1）；`config/narrative_weights.json` 入指纹；`metrics.narrative` 非判定 | 低 |
| **P0 → 前端增强** | PixiJS 回放 + 审计台 | 前端只读 `event_log/turn_seal` + 指标快照，与内核解耦 | 低（前端独立演进） |

### 6.3 复杂度与演进成本汇总

| 组件 | P0 复杂度 | 演进成本 | 关键解耦点 |
|---|---|---|---|
| `contracts` | 低 | 低 | 协议集中、零业务依赖（B1） |
| `kernel`（内核） | 中高 | 低 | 契约语言中立（规范 JSON/整数），可局部换实现 |
| `life`（GA 主干） | 中高 | 中 | 只经 IF-* 与内核交互，LLM 收敛到 freeze |
| `freeze` | 中 | 低 | provider 适配器 + 缓存；经 IF-2c 提载荷 |
| `emergence` | 中 | 低 | 只读 + 纯函数；切换向量/算法不影响判定 |
| `orchestration` | 中 | 中 | 组合根；政策/分区参数化 |
| `traj`（A） | 低（占位） | 中高 | 只读导出；训练管线后置 |
| `frontend` | 中 | 低 | 只读回放，与内核解耦 |

### 6.4 三条铁律的持续保障（CI 硬门禁）

> **状态：待实现（P0-13 待办）** —— `contracts/` 包、import-linter 配置、CI workflow、`golden_logs/` 截至本稿**尚未落地**；本节为 P0 交付目标与门禁设计，**不代表当前已完成**。落地责任：obs-stats-dev（统计与复现门禁）+ kernel-dev（边界/守恒）。

| 门禁 | 断言 | 覆盖铁律 |
|---|---|---|
| G1 边界 | import-linter：观测层只读（规则 2/3）、内核零反向依赖、`contracts` 零业务依赖 | C1 |
| G2 复现 | 黄金日志 `replay(log)` 状态哈希相等；`metrics()`/`emergence_report()` 两次字节相等 | C2 |
| G3 冻结 | 重放态 `llm_external_calls==0`；`LLM_JUDGMENT.decision ∈ envelope.options`；`llm_judged_metric_count==0` | C3 |
| G4 守恒 | 货币守恒式(1) + 交易原子式(2) + 生活层 L1–L8 | C1/C2 |
| G5 稳定 | 无 `SYSTEM_ERROR`、无哈希链断裂、无回滚 | C1 |

### 6.5 待验证假设与开放问题（交 Leader/用户）

- **【待验证假设】** `c_life/c_social`、每回合事件率 α_*、压缩比需 P0 实测标定（`08` D7-5）。
- **【待验证假设】** AI Town PixiJS 前端迁移工作量（`14` U5）；P0 先做只读回放到「可看」程度。
- **【开放】** Q1 货币总量口径（含银行库存项）、`ROUNDS_PER_SLOT` 最终值（AQ2）、A 线训练算力立项（`16` G1）。
- **【开放】** 向量库长期选型（本地精确 vs FAISS）——按长窗记忆规模在 P1 决策，接口已解耦。

---

## 7. 附：关键架构决策记录（ADR 摘要）

| ADR | 决策 | 理由 | 关联 |
|---|---|---|---|
| ADR-01 | 内核自建 + GA 认知主干 + AI Town 组件 | 三仓库均不满足铁律，但组件可包裹复用（`14` §D.2/§E.1） | §1.1 |
| ADR-02 | 独立 `contracts` 协议包 + 依赖倒置 | 使「kernel 不 import life」「life 不 import kernel 实现」同时成立且可机器强制（B1） | §1.3/§2 |
| ADR-03 | LLM 写路径经 IF-2c 提载荷、Arbiter 唯一写入（入缓冲区，P6 落盘） | 保住单一写入口（B4） | §2.2.1 |
| ADR-04 | 规范 JSON + SHA-256 哈希链 + turn_seal | 继承 v1 契约、审计友好、可逐位复现 | §3.1/§3.2 |
| ADR-05 | 主题正文走内容寻址侧存储 | 主日志瘦身 + 可审计（AR-C4/XT-3） | §3.3 |
| ADR-06 | Python 3.11 + 本地精确向量检索（P0） | GA 同源、P0 规模小、复现最干净 | §4.1/§4.3 |
| ADR-07 | 叙事层物理分包、逻辑属生活层角色带（N1 选项②） | 便于按需生成/降级，物理边界清晰；逻辑上仍受内核契约约束 | §1.1 |
| ADR-08 | `emit` 入本回合待提交缓冲区，**P6 COMMIT 为唯一 append 点**；整回合回滚丢弃整个缓冲区（含 P2 `LLM_CALL`） | 保证整回合原子性与单一 append，杜绝部分结算（D1 口径，Leader 裁定） | §1.4/§2.1/§2.2.1/§3.1 |

*（v1.2 实现架构工程蓝图 完成 — solution-architect）*
