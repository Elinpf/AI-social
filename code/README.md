# HITT 社会实验 · 确定性内核骨架（T29）

> 目标：交付**最小可运行的确定性内核**，能跑通一个 tick 并保证**重放逐位一致**。
> 先交付骨架，再按 v1.1 扩展功能。权威输入：`v1/03-engine-stats.md`、`v1.1/00-architecture.md`、`v1.1/08-engine-stats-extension.md`。

## 1. 快速开始

```bash
cd code

# 跑 20 回合空世界（只有出生/初始注入），落盘日志
python -m engine run --seed 12345 --rounds 20 --out /tmp/hitt_run.jsonl

# 从日志重放
python -m engine replay --log /tmp/hitt_run.jsonl

# 复现门禁：重放两次并比对状态哈希（PASS/FAIL）
python -m engine verify --log /tmp/hitt_run.jsonl

# 在真内核上运行 life 层（多 Agent，1 模拟周 = 84 回合）
python -m engine run --life --seed 42 --agents 3 --weeks 1 --out /tmp/hitt_life.jsonl
python -m engine verify --log /tmp/hitt_life.jsonl

# 门禁测试（CI）
python -m pytest -q
```

预期：`run` 输出 `chain_ok=True` 与 `final_state_hash`；`verify` 输出两次哈希相等并 `PASS`。

## 2. 目录结构

```
code/
├── engine/               # D0 确定性内核（本任务交付）
│   ├── canon.py           # 规范 JSON（键排序 + 浮点 round(...,6)）+ SHA-256
│   ├── rng.py             # SplitMix64 确定性随机 + 层级流 (seed, stream_id, round, seq)
│   ├── events.py          # 事件外壳 / EventSpec / 事件类型登记
│   ├── state.py           # WorldState / InitialState / state_hash / money_total
│   ├── ledger.py          # 只追加日志 + 哈希链 + turn_seal
│   ├── replay.py          # apply_event 分派 + replay = reduce(apply, EventLog, InitialState)
│   ├── conservation.py    # 守恒校验骨架（ECONOMY_INVARIANT_VIOLATION）
│   ├── arbiter.py         # 中央裁决器（唯一状态写入口）
│   ├── kernel.py          # Engine：P0–P6 阶段编排 + hook 链 + turn_seal
│   ├── hooks/             # Phase 4(4.1–4.8) 与 Phase 3.5(L1–L7) hook 链（可注入）
│   ├── time.py            # D-1 时间派生 round→slot→day→week（纯函数）
│   ├── perceive.py        # IF-1 perceive()（只读 WorldView）
│   ├── intents.py         # IF-2 submit_intent()
│   ├── runner.py          # run(seed, config, rounds) / 日志读写
│   └── cli.py             # CLI 入口
├── config/               # 数据配置（复现输入常数，纳入 engine_version 指纹）
│   ├── default.json            # 实验默认配置（时间结构 / genesis）
│   ├── perception_scope.json   # PERCEPTION_SCOPE（唯一来源）
│   ├── topology.json           # 场所拓扑常数矩阵
│   ├── policy.json             # B 线政策参数层（税率/UBI/利率/惩罚/安全阀，含范围）
│   ├── engine_version.json     # 指纹来源声明 + 版本一致性
│   ├── llm.json                # LLM 端点/模型/thinking 策略（密钥只在 env）
│   └── personas.json / places.json  # 角色 / 场所
├── life/                 # L1 人格生活层（life-layer-dev 负责，本任务仅占位对接）
├── freeze/               # 软判定层 LLM 冻结（其他成员负责）
├── obs/                  # L2 涌现观测层（占位）
├── narrative/            # 叙事层（占位）
├── frontend/             # 前端（占位）
└── tests/                # 门禁测试
```

## 3. 内核契约（已实现）

### 3.1 六个阶段（顺序固定）
`P0 ROUTE → P1 PERCEIVE → P2 DECIDE → P3 COMMUNICATE → [P3.5 LIFE] → P4 ARBITRATE → P5 LIFECYCLE → P6 COMMIT`
- **Phase 3.5 LIFE**（v1.1 新增，`phase=35`）挂 `L1–L7`（顺序固定）。
- **Phase 4 ARBITRATE** 挂 `4.1–4.8`（顺序冻结）：`settle_market → settle_obligations → apply_tax → apply_metabolism → apply_penalty → check_lifecycle → resolve_revival → check_death`。**骨架阶段 4.1–4.8 均为空实现**，由经济/生命周期层注入。
- 所有状态变更**只经中央裁决器 `Arbiter`**（P7）：hook 产出 `EventSpec`，裁决器落账并 `apply_event` 折叠。

### 3.2 事件与日志
- 事件外壳：`seq, round, phase, actor, type, payload, mono_ts, prev_hash, hash`（08 §1.1）。
- `mono_ts = round * TIME_UNIT + phase_seq`（逻辑时间，非墙钟）。
- `hash = "sha256:" + SHA256(canonical_json(记录去掉 hash 字段))`，形成**哈希链**。
- 每回合末追加 `TURN_SEAL`，提交 `{round, last_seq, last_hash, state_hash, money_supply, ...}`；重放时校验 seal 提交的 `state_hash` 与逐步斜放一致。

### 3.3 确定性随机
- `draw_u64(seed, stream_id, round, seq, n)`：子种子 = `SHA-256(canonical_json([seed, stream_id, round, seq]))` 前 8 字节，PRNG = **SplitMix64**（纯整数）。
- 无隐式随机、无墙钟/环境依赖。流之间相互隔离（一处抽样不改变另一处序列）。

### 3.4 重放
- `replay(log) = reduce(apply_event, EventLog, InitialState(seed))`；**不重跑 hook**。
- 未知事件类型**立即报错**（X4），禁止静默忽略。
- **门禁**：同一日志重放两次 `state_hash` 相等；且首跑最终状态 == 重放最终状态（P2）。

### 3.5 守恒校验
- 货币守恒：`money_minted_total − money_burned_total − M(t) == 0`，`M(t)=Σcash+Σdeposits+税池+银行库存`。
- 违规 → 落 `ECONOMY_INVARIANT_VIOLATION` 审计事件（货币总量公式留接口 `conservation.money_supply`）。

## 4. 对外端口

| 接口 | 位置 | 说明 |
|---|---|---|
| `run(seed, config, rounds)` | `engine.runner` | 跑 N 回合空世界，返回日志与最终状态 |
| `replay_records(records)` | `engine.replay` | 从日志重放 |
| `perceive(state, agent_id, records, config)` | `engine.perceive` | IF-1 只读 WorldView |
| `submit_intent(engine, agent_id, intent)` | `engine.intents` | IF-2 意图提交（非法→`INTENT_REJECTED`） |
| `derive_time(round_no, time_config)` | `engine.time` | D-1 时间派生 |
| `register_phase35_hook(name, fn)` | `engine.hooks` | 生活层注入 L1–L7 |
| `register_phase4_hook(name, fn)` | `engine.hooks` | 经济/生命周期注入 4.1–4.8 |

**hook 契约**：纯函数 `fn(state, round_no, ctx) -> list[EventSpec]`；不得直写 state；不含货币 delta（货币后果经 `pending_intents` 交 4.x）；随机只能经 `ctx.rng(...)`。

## 5. 复现门禁（验收对照）

| 验收项 | 对应测试 |
|---|---|
| ① 跑通 20 回合空世界 | `tests/test_replay.py::test_run_20_rounds_empty_world` |
| ② 重放两次哈希相等 | `tests/test_replay.py::test_replay_twice_equal_state_hash` |
| ③ 日志含哈希链与 turn_seal | `tests/test_hashchain.py` |
| ④ README（本文） | — |

## 6. 当前边界（骨架）

- **已实现**：仓库骨架、P0–P6 编排、Phase 4 全 hook 顺序、事件壳/哈希链/`turn_seal`、SplitMix64、重放与门禁、守恒校验骨架、CLI、genesis 初始注入。
- **占位（待各层注入）**：4.1–4.8（经济/生命周期）、L2–L7（生活层）；`perceive`/`submit_intent` 提供基础实现，完整可见性/记忆链待扩展。
- 跨模块接口变更请先对齐（life→kernel 端口见 `engine/perceive.py`、`engine/intents.py`、`engine/hooks/__init__.py`）。

## 7. 生活层联调（T34）

`orchestration/integration.py` 是 **engine × life 的唯一交接层**（组合根；`engine/integration.py` 为向后兼容 shim，`engine` 核心不 import life）：

- `register_life_hooks()`：把 `life.settlement` 的 L1–L7 注入内核 Phase 3.5 注册表。
- `KernelAdapter`：实现 `life.ports.KernelPort`（perceive/submit_intent/current_round/derive_time）；所有写入经中央裁决器 `Arbiter`。
- `build_world(seed, n=...)` / `run_e2e(...)`：从 `config/personas.json` 装配 N 个 Agent 在真内核上运行。
- 内核在 Phase 2 DECIDE 调用注入的 `agent.step()`（`Engine.agent_steppers`）。
- life LLM 默认经冻结层 `freeze.client.FreezeLLM`（离线 MockProvider，缓存入临时目录）；重放链路不调用 LLM。

实测（`v1.2/e2e-integration-report.md`）：N=3×84 回合 = 1730 事件 / 0.6 s / 777 KB；N=10×84 回合 = 8992 事件 / 5.3 s / 4 MB；重放两次状态哈希相等、守恒成立、无未注册事件、无直写旁路。

> 规模提示：`config/personas.json` 现有 **20 条 persona**（P001–P020，覆盖 00 §2.5 全部 10 类角色），`--agents 20` 免合成直接跑；N>20 时由 `engine.integration.expand_personas` 确定性合成（规模测试用）。
>
> life 模式规范入口：`python -m orchestration run --life ...`（`python -m engine run --life ...` 保留为兼容 shim）。

## 8. 工程卫生（T35）

### 8.1 D1：emit 时序（唯一口径）
- `emit` = 写入**本回合待提交缓冲区**（暂存）+ 增量折叠状态，**不落盘**；
- **P6 COMMIT 是唯一 append 点**：一次性把本回合缓冲（含 P2 的 `LLM_CALL`、P3.5、P4）追加到哈希链；
- **整回合回滚**：任一 hook 抛异常 / 守恒不成立 → 丢弃整个缓冲（含已 emit 的 `LLM_CALL`），仅追加 `SYSTEM_ERROR` / `ECONOMY_INVARIANT_VIOLATION`（自身必落），世界状态不变。验证：`tests/test_emit_rollback.py`。
- **Phase 3.5/P4 逐 hook 即时折叠**：后序 hook 必须看到前序产出（蓝图 §2.3；也是 L2→L3 依赖所必需）。

### 8.2 contracts/ 包 + 依赖边界
- `contracts/`：纯类型/协议包（`models`/`errors`/`interfaces`/`hooks`，零业务依赖）。
- `orchestration/`：组合根（唯一可同时依赖 engine/life/freeze 的入口层）。
- 依赖规则由 **import-linter** 强制：`lint-imports`（配置文件 `.importlinter`，对齐蓝图 §1.3）。
- 兼容 shim 例外（已登记 `ignore_imports`）：`engine.cli`/`engine.integration` → `orchestration.integration`；`frontend.tools.gen_demo_log` → `life.run_demo`（离线开发脚本）。

### 8.3 许可证合规
- `THIRD_PARTY_NOTICES.md`（GA=Apache-2.0、AI Town=MIT，含版权行与许可链接）
- `licenses/Apache-2.0.txt`、`licenses/MIT.txt`（许可全文）
- GA 派生文件逐文件"已修改"声明见 `life/NOTICE`；AI Town 派生见 `frontend/NOTICE`。

### 8.4 世界健康回归门禁
`tests/test_run_health_gate.py`：断言 `SYSTEM_ERROR==0`、`TIME_MARK==日边界数`、`TURN_SEAL==rounds`、`MEMORY_WRITE/OBSERVATION/ACTIVITY_COMPLETED>0`、事件量 ≥ T34 下界（防"外层门禁全绿但世界停摆"）。
