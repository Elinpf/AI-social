# T34 · 端到端联调报告：真内核 × 生活层 × 冻结层

> 作者：kernel-dev ｜ 状态：P0 里程碑达成 ｜ 日期：2026-10-10

## 0. 结论速览

| 目标 | 结果 |
|---|---|
| 把 life 层接到**真内核**（不再用 mini_kernel test-double） | ✅ |
| N=3 跑满 **1 模拟周（84 回合）** | ✅ 1730 事件，0.6s |
| N=10 可扩展（跑满 84 回合） | ✅ 8992 事件，5.3s |
| 端到端五项证据（事件合法/无旁路/重放一致/守恒/体积耗时） | ✅ 全部通过 |
| 统一 CLI `python -m engine run --life` | ✅ |

**P0 关键节点达成**：内核、生活层、冻结层已在同一日志/哈希链/重放链路下真实联动。

## 1. 接通方式（交接处）

新增 `code/engine/integration.py`（**唯一同时 import engine 与 life 的交接层**；engine 核心与 life 互不 import）：

1. **Phase 3.5 注册**：`register_life_hooks()` 调 `life.settlement.register_into(engine.hooks.register_phase35_hook)`，把 L1–L7 注入内核 hook 链（顺序冻结：advance_time→resolve_schedule→settle_activities→apply_needs→update_relations→write_memories→emit_tags）。
2. **端口适配**：`KernelAdapter` 实现 `life.ports.KernelPort`：
   - `perceive(agent_id) -> WorldView`（只读，PERCEPTION_SCOPE + location 判定，窗口 2 回合）；
   - `submit_intent(agent_id, Intent) -> IntentResult`：**一律经中央裁决器 `Arbiter` 落账**（SCHEDULE_PLANNED/PLACE_MOVE/ACTIVITY_STARTED/MEMORY_*/OBSERVATION/RELATION_CHANGE）；非法→`INTENT_REJECTED` 且不改状态；
   - `current_round()` / `derive_time()`。
3. **状态承载**：`engine.state.WorldState` 扩展生活层派生字段（agents[*].location/schedule/started_slots/current_activity/needs/memories/observed_event_seqs、memory_index/event_index/observed/rejected）并实现映射协议，life 层可 duck-typed 只读。
4. **驱动**：`engine.kernel.Engine` 在 Phase 2 DECIDE 调用被注入的 `agent.step()`（内核不 import life），与 mini_kernel.tick 语义一致（agent step → L1–L7 → seal）。
5. **冻结层**：life 默认经 `life.llm.get_llm_client()` 优先用 `freeze.client.FreezeLLM`（离线 MockProvider，缓存入临时目录）；重放链路**不调用** LLM。

## 2. 端到端验收证据（逐项）

命令：
```bash
cd code
python -m engine run --life --seed 42 --agents 3 --weeks 1 --out ../v1.2/e2e_n3_week.jsonl
python -m engine run --life --seed 42 --agents 10 --rounds 84 --out ../v1.2/e2e_n10_week.jsonl
```

| # | 证据 | N=3（84 回合） | N=10（84 回合） |
|---|---|---|---|
| ① | 事件均合法（无未注册类型） | ✅ unknown=[] | ✅ unknown=[] |
| ② | 无直写旁路（life 不经 Arbiter 改不了状态） | ✅ 见 §2.1 | ✅ |
| ③ | `replay(log)` 两次状态哈希相等 | ✅ `b03bf10f…` 两次相等 | ✅ `eb6ecacf…` 两次相等 |
| ③b| 首跑最终状态 == 重放最终状态 | ✅ | ✅ |
| ④ | 守恒不变量成立 | ✅ 无 violation | ✅ 无 violation |
| ⑤ | 耗时 / 日志体积 | 0.59 s / 777 KB | 5.28 s / 4.01 MB |

### 2.1 “无直写旁路”证明

- **结构性**：life 层只有两条写路径——`submit_intent`（经 `Arbiter`）与 Phase 3.5 hook（只返回 `EventSpec`，由内核 `Arbiter` 落账）；life 代码不 import `engine.replay.apply_event` 之外的写入口。
- **测试性**：`tests/test_e2e_integration.py::test_no_direct_write_bypass` 直接对活状态逐个调用 L1–L7，断言 `state_hash` 调用前后不变（hook 为纯函数）。

## 3. 事件普查（实测）

**N=3 · 84 回合（1730 事件）**：NEED_UPDATE 530、MEMORY_WRITE 318、OBSERVATION 255、MEMORY_RETRIEVE 252、TURN_SEAL 84、PLACE_MOVE/ARRIVED 各 63、ACTIVITY_STARTED/COMPLETED 各 63、MEMORY_REFLECT 21、TIME_MARK 7、AGENT_BORN/INIT_ENDOW/SCHEDULE_PLANNED 各 3、WORLD_INIT/MONEY_MINTED 各 1。

**N=10 · 84 回合（8992 事件）**：MEMORY_WRITE 2812、OBSERVATION 2602、NEED_UPDATE 1685、MEMORY_RETRIEVE 840、ACTIVITY_* 各 210、PLACE_* 各 205、TURN_SEAL 84、MEMORY_REFLECT 70、INTENT_REJECTED 30、其余同。

每 Agent 每回合事件 ≈ `1730/(3×84) ≈ 6.9`；N=10 时 ≈ `8992/(10×84) ≈ 10.7`（记忆观察随人数增长，符合传播/观察预期）。

## 4. 规模与容量结论（P0 容量估算实测）

| 规模 | 事件/回合 | 每 Agent/回合 | 单周日志 | 单周耗时 |
|---|---|---|---|---|
| N=3 | ~20.6 | 6.9 | 0.78 MB | 0.59 s |
| N=10 | ~107.1 | 10.7 | 4.01 MB | 5.28 s |

- **结论**：N=10 可跑满一个模拟周，耗时秒级、日志 MB 级，**容量非瓶颈**（与 00/08 §7 量级估计一致，偏低）。瓶颈仍是 LLM 调用（冻结层已接管）。
- **放量**：N=10→20 应可行；若沿用当前“观察即记忆”口径，`OBSERVATION/MEMORY_WRITE` 近似随 N 线性，事件量与日志线性增长，预计 N=20 单周 ~15–20 MB、10–15 s。
- **前置缺口**：`config/personas.json` 当前仅 3 条；N>3 依赖 `engine.integration.expand_personas` **确定性合成** persona（规模测试用）。正式放量需 life 侧补足 ≥N 条人工 persona，否则小镇角色/关系多样性不足。

## 5. 接口对齐与冲突清单

| 项 | 状态 | 说明 |
|---|---|---|
| hook 签名 `fn(state, round, ctx)->list[EventSpec]` | ✅ 对齐 | 内核 `_coerce_specs` 兼容 life 的 `EventSpec`（type/payload/phase/actor） |
| `Ctx.derive_time` / `Ctx.rng` | ✅ 对齐 | 内核 `Ctx` 已补 `derive_time` |
| `KernelPort`（perceive/submit_intent/current_round/derive_time） | ✅ 实现 | `KernelAdapter`；`isinstance(adapter, KernelPort)` 通过 |
| 状态 duck-typing | ✅ 兼容 | `WorldState` 实现映射协议，life `LifeState` 只读 |
| `PERCEPTION_SCOPE` 表 | ⚠️ 双份 | 引擎 `config/perception_scope.json` 与 `life.constants.PERCEPTION_SCOPE`；adapter 目前用 life 常量（含 `subject_only`）。**建议后续统一落到引擎 config 并纳入 engine_version 指纹**（08 §3.5 R2） |
| `CHAR`/拓扑等 config | 归内核 | TOPOLOGY/PERCEPTION_SCOPE 归 engine |

> 无阻塞性冲突；`PERCEPTION_SCOPE` 双份为已知待收口项，不影响复现（同日志一致）。

## 6. 复现

```bash
cd code
python -m pytest tests/test_e2e_integration.py -q     # 端到端门禁
python -m engine run --life --seed 42 --agents 3 --weeks 1 --out ../v1.2/e2e_n3_week.jsonl
python -m engine verify --log ../v1.2/e2e_n3_week.jsonl   # 重放两次哈希相等 → PASS
```

## 7. 追记（T35 / T41 / ② log_bytes / LLM 接入）

### 7.1 T41 · PERCEPTION_SCOPE 单一来源（Lead 裁定，已落实）
- **唯一权威 = 引擎 `code/config/perception_scope.json`**（v1.2-r2，含 `subject_only` 等）。
- **life 侧删除自带常量**：`life/constants.py` 不再维护独立表，改读同一 config（缺失/坏 → 报错，**不静默回退**）。
- **引擎侧严格加载器**：`engine.version.load_perception_scope()`（缺失/版本不匹配/非法 class → `PerceptionScopeError`）；`engine.perceive.load_perception_scope()` 亦走严格路径。
- **纳入 engine_version 指纹**：`engine.version.compute_fingerprint()` 聚合 `default.json / perception_scope.json / topology.json / narrative_weights.json / llm.json` 的规范哈希；写入 `WORLD_INIT.payload.fingerprint` 与 `config_components`；**重放前断言一致**（`assert_log_fingerprint`，不一致 → `ConfigError`）。
- 测试：`tests/test_version_fingerprint.py`（缺失/版本不匹配/非法 class 报错、指纹含三项复现输入、WORLD_INIT 提交指纹、重放不一致报错）。
- 状态：**全仓仅 config 一处定义**（life 常量已删）；`lint-imports` 8 kept / 0 broken；`pytest -q` 全绿。

### 7.2 ② `log_bytes` 口径差异（已澄清并统一）
- 差异原因：内核自报 `log_bytes` 原用 `json.dumps(records)`（**默认分隔符带空格**）估算，而落盘文件由 `write_log` 用**紧凑规范 JSON**（`separators=(",",":")`、键排序）写，故自报值偏大 ~5MB。
- 处置：`run_e2e` 的 `log_bytes` 改为**与落盘口径一致**（逐条 `canonical_json(rec)` + 换行字节求和）。二者现应相等（写出即文件字节数）。

### 7.3 ① 真实 LLM 接入（驱动侧）
- `config/llm.json`（非密钥）：`endpoint=http://172.16.3.41:31809/v1`、`model=DeepSeek-Flash`、thinking 策略 `{default:false, true_purposes:[judge,narrate,describe], true_tiers:[t2]}`；**纳入 engine_version 指纹**。
- `orchestration.integration._default_llm`：默认离线 `MockProvider`（测试/门禁零网络）；真 provider **显式 opt-in** `HITT_LLM_PROVIDER=openai_compat`（端点/模型可 env 覆盖）；thinking 策略由集中式 `freeze.ThinkingPolicy` 按 purpose/tier 裁决（`chat_template_kwargs.thinking`）。
- **密钥安全**：`LLM_API_KEY` 只从 env 读取，内存使用，**不落盘/不入日志/不入证据包**；`LLM_CALL` 只记 model/tier/tokens。
- 待 freeze-layer-dev 真跑确认后：验证 `LLM_CALL/LLM_JUDGMENT>0`、**重放 `llm_calls==0`**，并重测规模-耗时-体积曲线与重冻 G6 基线。
