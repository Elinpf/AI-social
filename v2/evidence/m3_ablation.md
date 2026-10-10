# T125 · M3 单变量消融（基线 vs 去生产 vs 去社交）

> 目的：**去掉工具，涌现是否消失**（证伪）。固定 **seed=42 / N=20 / rounds=84 / provider=mock（rule-based）**，每档**只改一个开关**。
> 开关：`policy.production.enabled`（T114）/ `policy.social.enabled`（T115）。**未改任何默认值/引擎/schema/travel_ticks。**
> 判据全 D 类、只读日志；三档 `state_hash` **互异**。

## 1. 三档 `state_hash`（互异 = 开关真的进了结构）

| 档 | 开关 | state_hash | log sha256 |
|---|---|---|---|
| **A 基线** | prod=on, social=on | `sha256:9eba46a50a93e1695c0ec21e39731b52f3c7d98353ed0c191fb0ebc0a9ca2787` | `sha256:13e38c7b547dc81b1a2b34211079e3275ba43e80cc7b5a95aac64294e175560a` |
| **B 去生产** | prod=**off**, social=on | `sha256:e1aa435ab1a97661656c3d3d8260dc605aead80e82f8e0e3ea329134be5404c9` | `sha256:78d0ede97c0867920b3af11cef2d8288e08beaf18ecdc0e06a3762ace8fbe50f` |
| **C 去社交** | prod=on, social=**off** | `sha256:2de59edea81795a77123d98769d25d2cb15cf5f2b2c39b34d69b701a59ee81b2` | `sha256:4207cbe7b9e5898c3eb2a6f8b21c7426cb3a8bbccee8ad5bdb4cd8498a384aee` |

三者互异 ✓（A≠B≠C）。四态均 `chain_ok/replay_parity/seals_ok/conservation_ok=True`、`SYSTEM_ERROR=0`。

## 2. 三档并列对照

| 指标 | A 基线 | B 去生产 | C 去社交 |
|---|---:|---:|---:|
| 事件数 | 128456 | 128054 | 124551 |
| **经济** `PRODUCE` | 321 | **0** | 321 |
| `CONSUME` | 165 | **0** | 165 |
| `Y`（mu） | 48070 | **0** | 48070 |
| `M_min` / `M_final` | 0 / 35100 | 0 / 35100 | 0 / 35100 |
| `V` | 0.055848 | 0.055848 | 0.055848 |
| `Gini` | 0.858709 | 0.858709 | 0.858709 |
| **社会** `MSG_DM` | 162 | 162 | **0** |
| `MSG_PUBLIC` | 64 | 64 | **0** |
| `MSG_GROUP` | 7 | 7 | **0** |
| `GROUP_CREATED` | 61 | 61 | **0** |
| `dialogue` LLM_CALL | 270 | 270 | **0** |
| `comm_directed_edges` | 161 | 161 | **0** |
| `n_groups` | 8 | 8 | **0** |
| **制度** `norm_adopted` | 17 | 17 | 17 |
| `n_contracts` | 0 | 0 | 0 |

## 3. 证伪结论（**如实，含"不降"**）

**B 去生产（单变量 = `production.enabled=false`）**：
- ✅ `PRODUCE/CONSUME/Y` **全部归零**、`state_hash` 改变 ⇒ **生产/价值创造非写死 → 证伪成立**。
- ✅ `M(t)` 不穿负（`M_min=0`）、**守恒仍成立**（`conservation_ok=True`）。
- ⚠️ **不降（如实）**：社交三通道、`dialogue`、群组、规范采纳**均与基线相同** ⇒ 这些**不依赖生产**工具。

**C 去社交（单变量 = `social.enabled=false`）**：
- ✅ `MSG_DM/PUBLIC/GROUP`、`GROUP_CREATED`、`LLM_CALL(purpose=dialogue)`、`comm_directed_edges`、`n_groups` **全部归零**、`state_hash` 改变 ⇒ **社交发声通道非写死 → 证伪成立**。
- ⚠️ **不降（如实）**：`norm_adopted=17`（与基线同）——**规范采纳不依赖 v2 社交通道**（规范由 L7/NORM 触发，与 MSG 通道解耦）；经济/生产指标亦不降。

> 一句话：**去掉哪个工具，对应的涌现指标就归零**（两名目证伪成立）；**但归属要精确到通道**——规范采纳不由社交发声驱动（如实记录，不美化也不夸大）。

## 4. 方法学备注（一处真实陷阱，已修复）

首轮三档在**同一 Python 进程**内串行跑，C 档 `social.enabled=false` **看似无效**（`state_hash` 与 A 同）。
**根因**：`life/policy.py::social_enabled()` 对 `config/policy.json` 做了**首次读缓存**（`_config_cache`），同进程内后置的配置改动不重读。
**修复**：**每档单独进程**跑（模拟真实独立运行）→ C 档即正常归零（`sha256:2de59edea8179…`）。**非产品缺陷，是消融驱动器的进程复用问题**；已用独立进程重跑 C，并在本表采用重跑值。

## 5. 门禁（原始输出 `v2/evidence/m3_gates.txt`）

`pytest -q` **281 passed** ｜ `lint-imports` **8 kept/0 broken** ｜ `obs gate G1–G7` **PASS** ｜ `make lexicon-gate` **exit=0** ｜ 三档 `replay_parity=True`（逐位）。

## 6. 产物

- 日志：`run_m3_A_baseline.jsonl` / `run_m3_B_noproduction.jsonl` / `run_m3_C_nosocial.jsonl`（sha256 见 §1）
- 汇总：`v2/evidence/m3_ablation_raw.json`；门禁：`v2/evidence/m3_gates.txt`；本表：`v2/evidence/m3_ablation.md`
- provider：**mock（rule-based）**（三档一致；真 LLM 的 `321/314` 口径不可与 rule-based 互比——本表三档全 rule-based，可比）
