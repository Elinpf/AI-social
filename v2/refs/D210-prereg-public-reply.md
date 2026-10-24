# D2.10 预登记 · **公开场合接话**（PUBLIC reply: 同场旁人能接一句）

> 立此存照：2026-10-24，**在任何 D2.10 跑批之前**。判据、阈值、反事实、止损条件先写死。
> 预登记锚点：写此文件时 master HEAD = `1ff2784`；分支 `feat/d210-public-reply`。
> ⚠ 阈值一栏标 **【待 Leader 确认】** 的项，跑批前必须定稿；**不得事后按实测值回填**（D2.3 教训 §8.1）。

## 0. 查重结论（**先证明不是重复立项**）

| 已存在的件 | 覆盖什么 | 与本臂的关系 |
|---|---|---|
| `reports/R8-*` | **`reply_window_rounds` 2→4**（DM 线程密度） | 只动 DM 的时间窗口，**不碰 PUBLIC 渠道**；本臂不动该参数 |
| `reports/R4-life-texture.md` | 生活气息观测面（含「群体聚集/同场共处」「独处」两维，均**描述性无判据**） | 描述性登记，无 PUBLIC 接话机制、无判据 |
| `v2/refs/F7-offscreen-criteria.md:169` | **两臂的公开消息里他人指称都是 0 条**（48 vs 63 条全是自言自语/旁白） | 只登记了"公开消息是自言自语"这一**事实**，未立项机制 |
| `v2/refs/D8-dialogue-study-report.md` | 线程字段**设计与落地**（`thread_id/turn_index/reply_to/participants`） | 给了字段与 DM/GROUP 的接话路径；**PUBLIC 分支未纳入可回复** |
| `reports/R23-solitude-idle.md` | 独处/空闲尺子 | 不同维度 |
| `v2/refs/D23-*`（已判「搁置·不可测」） | 对端**选址**（place-affinity） | 不同对象（选谁 vs 谁能接话） |

`grep -rln "MSG_PUBLIC|接话|reply_to" v2/refs/*.md reports/*.md` 只命中上述**事实登记/设计件**，
**没有任何"PUBLIC 接话"的预登记或报告** ⇒ 本臂**不重复立项**，且是在既有的"字段与能力已具备"之上补**渠道接线**。

## 1. 事实底稿（全部可复算，读 `run_d27_C_n16r60_seed42`）

```
$ python3 tools/d210/public_reply_preview.py --log v2/evidence/run_d27_C_n16r60_seed42/run.jsonl
n_msg_public 55 | participants_len_hist {"1": 55} | n_public_reply_to_null 55
opportunity_n 46 | opportunity_rate_pct 83.64
predicted_replies_n 10 | predicted_reply_rate_pct 18.18
```

| 量 | 值 | 口径 |
|---|---|---|
| `MSG_DM` | 455（发起 114 / 回复 341） | `type=="MSG_DM"`，`turn_index` 分发起/回复 |
| `S-4_reply_pointer_coverage` | **341/341 = 100.0%** | 回复类 `MSG_DM` 中 `reply_to` 非空占比 |
| `MSG_PUBLIC` | **55**（`participants` 长度恒 1、`reply_to` 恒 null、`place` 恒 null） | 同左 |
| `MSG_GROUP` | 0 | — |
| PUBLIC 主题分布 | `skill_practice` 29 / `savings` 18 / `job_choice` 8 | `payload.topic` |
| PUBLIC 作者/轮/时段 | 12 人 / 17 个 round / 9 个 slot | — |
| **同场旁人机会** | **46/55 = 83.64%**（library 10 · bank 17 · farm 8 · school 6 · office 3 · town_hall 2） | `ACTIVITY_STARTED.(agent,slot_id)->place` 取发起人地点，再找同 slot 同地点他人 |
| **预测接话条数** | **10 条（18.18%）** | 按本臂规则重放（窗口 4 / `max_turns` 6 / 每轮 K / **单 slot 消息上限 2**） |

**约束诊断（按 runbook §3.118 顺序：配额 → 可见性 → 优先序）**：
机会 46 条，但预测只接上 10 条 ⇒ **主约束是「配额」**（`max_messages_per_slot=2`，同场旁人该 slot 的 2 条额度常已被 DM 用掉），
**不是**可见性（PUBLIC 是 global 可见）**也不**是优先序。⇒ 本臂**不得**顺手调 `max_messages_per_slot`（那是第二个变量）。

### 1.1 精确代码点（阻塞在哪）

| 位置 | 现状 | 本臂改动（仅开关开时生效） |
|---|---|---|
| `life/dialogue_threads.py::is_replyable` | 对 `MSG_PUBLIC` **恒 False** | 开时按 `public_reply.replyable()`（同场/成员判据） |
| `life/agent.py::_pick_reply_target` | 类型过滤 `in ("MSG_DM","MSG_GROUP")` ⇒ PUBLIC 永不进候选 | 开时把 `MSG_PUBLIC` 加进类型集 |
| `life/agent.py::_thread_max_turn` | 只统计 DM/GROUP ⇒ PUBLIC 线程 max_turn 恒 -1 | 开时一并统计 PUBLIC（否则回话算成 `turn_index=0`、绕过封口） |
| `life/agent.py::_send_reply` | scope = `private if DM else place_group` ⇒ PUBLIC 回话会被落成 **place_group（错渠道）** | 开时用 `public_reply.scope_for()` ⇒ PUBLIC 回话仍 `global` |
| `life/agent.py::_initiate` + `orchestration/integration.py::_do_social` | PUBLIC **不带地点**（`place` 恒 null）⇒ 无法判"同场" | 开时**新增键** `place_ctx`（=计划地点）；**不改**既有 `place` 键、不改可见性 |

## 2. 单变量口径（写死）

- **唯一变量**：`HITT_PUB_REPLY`（默认关）。
  - **OFF（对照）**：`HITT_PUB_REPLY` 缺省/`0` ⇒ 上述 5 处全部走原路径（PUBLIC 不可回复、无 `place_ctx` 键）⇒ 与 master **逐字节一致**；
  - **ON（机制）**：`=1` ⇒ **同场旁人可接一句**：`author != 我` 且（`我 ∈ participants` 或 `place_ctx == 我的计划地点`），
    回话继承 `thread_id`、`reply_to = 被接话的 msg_uid`、`turn_index = max+1`、`scope` 仍 `global`。
- **不动**：提示词文本（`_dialogue_prompt` / `_reply_prompt` 一字不改）、`planner` 选址/选人、`max_messages_per_slot`、`max_turns`、`reply_window_rounds`、`config/*.json` 任何文件。
- **不产生世界态后果**：不改 needs/relations/cash；`place_ctx` 是只追加字段，不进 `state_hash`（`WorldState.to_dict()` 投影不含 payload）。

## 3. 判据与阈值

| # | 指标 | 阈值 | 依据（离线可预测量） | 档位 |
|---|---|---|---|---|
| **M1 机制生效（硬闸）** | ON 臂**公开接话条数** = `MSG_PUBLIC` 中 `reply_to` 非空 的条数 | **≥ 6** | 离线预测 **10**（取 60% 作下限，容忍 LLM/配额抖动） | 未达 ⇒ 判**「不可测（触发不足）」**，不得写「无效」 |
| **P 主判据**（**探索性·点估计级**） | `pub_reply_rate` = 公开接话 / PUBLIC 发起 | **≥ 10%**（OFF 基准 **0%**） | 离线预测 **18.18%**（10/55） | 未达 ⇒ 判「无效（接通了但没人接）」 |
| **S-4 不回归（硬闸）** | DM 回复类 `reply_to` 覆盖率 | **= 100%**（341/341 基准 ±0pp） | 现状 100%；DM 路径开关开/关**逐键相同**（单测钉住） | 破 ⇒ **作废（非单变量）** |
| **S1 结构** | `n_msg_dm`、`n_public_init` 相对 OFF | **±10%** | 现状 455 / 55 | 破 ⇒ **作废（非单变量）** |
| **S2 生活质感（描述性，不判）** | 公开接话线程的 `turn_index` 均值 | 报告点估计（无阈值） | 预测里多为 1 轮 | **只描述** |
| **T 文体闸** | `tools/d12h/shape_gate.py` F1/F2/F3 | **同树 OFF 臂自建基线**，漂移 ≤ 预登记容许带 | ⚠ **禁套 T5 常数**（D2.3 实测 T1-OFF 自身即三项越界） | 破 ⇒ **作废（形态漂移）** |

> **功效声明（必须先写在前面）**：分母只有 **55 条 PUBLIC**、预测触发 **10 条** ⇒ 本臂**统计功效低**。
> 故 P 只判**方向性点估计**，**不得**写成"显著改善"；任何"生活气息提升"的措辞须限定为 **单 seed 点估计、不外推**。

## 4. 不可测早期止损（**D2.3 教训植入**）

D2.3 栽在"机制在计划期数学恒零"。本臂的对应检查已**在跑前做完**：

| 检查 | D2.3 的答案 | D2.10 的答案（本件已实测） |
|---|---|---|
| 机制输入在其计算时刻存在吗？ | ✗ 计划期历史为空 ⇒ `w≡1` | ✓ **轮内**判同场，输入 = 我的计划地点（确定性、两相位可得）+ 事件里的 `place_ctx` |
| 本规模会被触发几次？ | 0 次（恒零） | **10 次**（机会 46 次） |
| 够判吗？ | 不够 ⇒ 判「不可测」 | **勉强够做点估计**（M1 ≥6 可判"机制有没有生效"；P 只作方向） |

**止损条款（跑前写死）**：ON 臂若 `公开接话 < 6` ⇒ 判 **「不可测（触发不足）」**，
并**只允许**两条后续：① 提高 PUBLIC 发起量（另一变量，须新预登记）；② 承认本规模不可测并搁置。
**不得**在同一份报告里改成"无效"或"方向为正"。

## 5. 反事实（跑前写死）

| 观察 | 判定词 |
|---|---|
| M1 ≥6 且 P ≥10% 且 S-4/S1/T 全过 | **有效（方向为正·点估计）** |
| M1 ≥6 但 P <10% | **无效（接通了但没人接）** |
| M1 <6 | **不可测（触发不足）** |
| S-4 或 S1 破 | **作废（非单变量）** |
| T 破 | **作废（形态漂移）** |
| 公开接话升但 DM 回复数大降（>10%） | **作废（产能被抢，非单变量）** |

## 6. 成本与执行

- 规模：**n16r60 seed42**，两臂（OFF / ON）各一次 ⇒ **2 次串行**，≈ **52 min/次 ⇒ ~1.8h**；
  额外 LLM 调用 = 公开接话条数（预测 **10**，上限受 opportunity 约束 ≤46）⇒ 相对 4200 次/次 **<1.2%**。
- 起跑前置（缺一不可）：
  1. `bash tools/d5/preflight.sh --tag d210` **返回 PASS** + `pgrep` 确认无在跑批；
  2. **D2.8 措辞线收尾**（见 §7）；
  3. 分支 rebase 到当轮 master 并**重跑 mock 三分项**（OFF 逐字节、ON 有接话、DM 等价）；
  4. T 闸**同树 OFF 自建基线**；
  5. 真跑后 `obs llm-cost --require-provider openai_compat` **验真**（本臂 LLM 调用量必须与 mock 预测同量级）。

## 7. 与 D2.8 措辞线是否交互（**必须回答**）

- **目录不重叠**：D2.8 改 `narration`/台词配额与句法骨架（`code/life/l7_structural.py`、旁白配额）；
  本臂改 `is_replyable` / 回复渠道 / `place_ctx`，**不碰任何提示词与措辞层**（`git diff` 可证：无 prompt 文件、无 l7/anchor 模块）。
- **变量不重叠**：D2.8 是"怎么说"，本臂是"谁能接一句"。
- **但同批不可比**：D2.8 进行中 ⇒ 本臂**必须等其收尾后**在该批的 OFF 基线上跑，否则 OFF 基线口径不同（措辞层变了）。
  ⇒ **禁止与 D2.8 同批跑**（那是双变量）。

## 8. 失效条件（跑前声明）

1. `place_ctx` 取不到（`_plan_slots` 里该 slot 无 place）⇒ 该条 PUBLIC 不可被接 ⇒ 机会量下降；若实测 opportunity < 30% ⇒ 记"接线缺口"，判「不可测」；
2. 同场旁人该 slot 额度已满（主约束，预测已内含）⇒ 若实测"因配额未接"占比 >70% ⇒ 结论只可写"受配额所限"，**不得**写成机制失效；
3. 若 ON 臂 PUBLIC 发起数掉 >10%（agent 把 slot 额度用在接话上）⇒ 判「作废（非单变量：产能被抢）」。

## 9. 实现状态（已接线 vs inert）

| 点 | 状态 |
|---|---|
| `life/public_reply.py`（开关 + 判据纯函数） | **已接线**（被 `dialogue_threads.is_replyable`、`agent._pick_reply_target/_send_reply/_initiate` 调用，5 处，均 `PR.enabled()` 门控） |
| `dialogue_threads.is_replyable` PUBLIC 分支 | **已接线**（默认关 ⇒ 恒 False） |
| `agent._pick_reply_target` / `_thread_max_turn` / `_send_reply` / `_initiate` | **已接线**（开关门控） |
| `integration._do_social` 透传 `place_ctx` | **已接线**（缺省 None ⇒ 不打键） |
| 提高 PUBLIC 发起量 / 调 `max_messages_per_slot` | **未做，且刻意不做**（第二变量） |
| 同场判据的"跨 slot 邻近"（±1 slot 放宽） | **未做**（属放宽口径，须单独立项） |
