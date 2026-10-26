# D2.12 预登记 · **同回合 perception 不可见（轮内两阶段）**

> 立此存照：**2026-10-26，在任何 D2.12 代码改动与跑批之前**。判据、阈值、反事实、止损条件先写死。
> 性质：**预登记（立项件）**——**不实现、不跑批、不改 `code/`**（本轮冻结）。本件与 `D211-prereg-syntax-exec.md`、D2.10 公开接话**编号隔离**（D2.12 命名，避免二义）。
> 依据（全文均带「文件路径 + 章节/行号」或「臂 commit」）：
> - `v2/evidence/d26_perception_lag.md`（同轮往返 0.0%；341 相邻对：gap=0 0.0% / gap=1 62.8% / gap≥2 37.2%；机制=轮内顺序执行+轮末提交；§6 禁用 `upto_round` 改 `state.round` 假改动）
> - `v2/refs/ARCH-memo-timing-and-partner.md`（§2 最小改动；§3 优先级；§7 修正 62.8%→~7%、顺序 D2.5a→B→A；§6 三问）
> - `v2/evidence/d26_amendment1_gap_attribution.md`（gap≥2 的 92.9% 是配额满，仅 7.1% 是「看见了却没回」）
> - `v2/refs/batch-hosting-runbook.md` §3.116（override 纪律）/§3.117（规模三问）/§3.118（归因三类）/§3.119（线程分母）/§3.120（两树两臂）
> - `v2/evidence/d25a_result.md`（**D2.5a 已判「无效」⇒ 配额仍 2**）
> - `v2/refs/tick-internal-time-design.md`（D11 路径 B；本件是其期③窄子集，见 §1.3）
> - 只读现状口径：`code/engine/perceive.py:129`、`code/life/visibility.py:36`、`code/life/agent.py:903`
> 配套设计备忘（团队共享）：`/root/.jiuwenswarm/.agent_teams/jiuwen_team_web_1a175d53d93_23d23ec5a54f/team-workspace/artifacts/docs/INROUND-PERCEPTION-DESIGN-2026-10-26.md`
> 锚点：写作时主树工作分支 `feat/f7-fabrication` HEAD = `734aa4e`；`master` tip = `fbf1ff3`。本臂**尚未实现**，故 C/B′ 的 commit 均**跑前填**。

---

## 0. 一句话

把「每个 round 跑一遍决策」改成「**同一 round 跑两遍**：phase A 全员 → phase B 待回者再跑一次」，
让**同轮事件在 phase B 可见**，从而可能产生 `gap=0`（同轮往返）。**不改 `visible_events` 的 `upto_round` 口径。**

---

## 1. 机制定义（最小改动）

### 1.1 现状口径（只读核实）

- `code/engine/perceive.py:129`：`visible_events(records, agent_id, state.round, config)` —— 上界是**当前轮**；
- `code/life/visibility.py:36`：谓词 `rec["round"] > upto_round ⇒ break`（委托 `contracts.visibility` 唯一真源）；
- `code/life/agent.py:903`：`_pick_reply_target()` 只从 `wv.visible_events` 里挑接话；
- 根因（`d26_perception_lag.md` §3）：**轮内顺序执行 + 轮末提交** ⇒ round r 决策时同轮事件未提交 ⇒ `visible_events(r)` 实际只返回 `<r`。

### 1.2 D2.12 最小改动

```
round r 内跑两遍决策：
  phase A：全体 agent 按现行为决策（MSG_* 以 round=r 落【轮内缓冲】）
  ── phase B 开始前，phase A 的同轮事件对 visible_events 可见 ──
  phase B：仅「有可回入站且未达 K 上限」的 agent 再决策【一次】
  ── round 末照旧统一提交 ──
```

- **不改** `upto_round` 口径（上界仍 `state.round`，`visibility.py:36` 一字不动）；变的是**调度次序**。
- phase B **只跑一遍**；**轮内上限仍用 `max_turns_per_round`（现 `=2`）**，改为**跨 A/B 累计计数**。
- 开关：**`inround_visibility.enabled`（默认 `OFF`）**；`OFF` 路径须**逐位等同现状**（关臂干净，见 §6.3）。

### 1.3 关联语义同步重定义

| 量 | 现语义 | D2.12 改为 |
|---|---|---|
| `_round_replies`（K 上限） | 单 agent 单回合已回条数，`>= max_turns_per_round` 即封 | **跨 phase A+B 累计**；phase B **不得重置** |
| `_replied_msg_ids` / `_thread_replied_turn` | 防重复回同一条 | phase B 前须含 **phase A 新增**去重键（含同轮 `msg_uid`） |
| `max_turns` | 线程封口 | **不动** |

### 1.4 与 D11 的边界

D2.12 = D11 路径 B **期③（交错/先后）的窄子集**：**不引入 `μt`/`span`、不改结算频率、不加前向态**，只重排轮内决策次序。若 D11 期③落地，D2.12 应被其吸收重述；**二者不得同批并存**（双变量）。

---

## 2. 三问回答（§3.117，**定量**）

| 问 | 回答 | 证据 |
|---|---|---|
| ① 输入在计算时刻存在吗？ | **存在**（面向 phase B 决策者）：phase A 同轮事件在 phase B 前已产出并可被 `visible_events(state.round)` 读到。区别 D2.3（计划期 `round=0` 空历史 ⇒ `w≡1`） | `d26_perception_lag.md` §3；ARCH §0 |
| ② 规模够生效吗？ | **单轮即生效**（非周级累积）⇒ **60 轮足够，不需 144**。**不触发「不可测（规模不匹配）」档** | §3.117；本件 §1.2 |
| ③ 生效期占比 / 预期值 | **时间占比 100%**（无第二周 1/2 稀释）；**配对级稀释严重** ⇒ 上限 **≤ 7.1%（9/127 gap≥2）= 绝对值 ≤ 2.6pp（9/341）** | `d26_amendment1` §2；本件换算 |

**预期值（写死，严禁沿用 62.8%）**：

| 口径 | 值 |
|---|---|
| 可见性可解释**上限**（分母 gap≥2） | **≤ 7.1%**（9/127） |
| 同口径（分母 341 相邻对） | **≤ 2.6pp** |
| 主指标 `gap=0 占比` **绝对天花板** | **从 0.0% → ≤ ~2.6%** |
| 回复延迟 `p50 gap` | **预期不动（=1）** |

⚠ **叠加约束**：`d25a_result.md` 已判 D2.5a「无效」⇒ 配额仍 2；而 ARCH §7 说 B 的 7% 上限「须在配额放开后才可能显现」⇒ **配额未放开时 B 可实现上限或进一步趋零**（见 §9 开放点 P4）。

---

## 3. 臂（按 `batch-hosting-runbook.md` §3.120）

| 臂 | 树（worktree / 分支） | commit | 开关 | seed | 收批必核判别量 |
|---|---|---|---|---|---|
| **C（基线）** | 主树 `social-experiment` / `master`（或含关臂的 B′ 树，见下） | **跑前填**（现 `master` tip=`fbf1ff3`） | `inround_visibility.enabled=0` | 42 / 43 | 无 phase-B 决策者；`gap=0`=**0.0%** |
| **B′（D2.12）** | `.worktrees/d212-inround` / `feat/d212-inround`（基于实现时 `master` tip） | **跑前填** | `inround_visibility.enabled=1` | 42 / 43 | phase-B 决策者 **>0**；`gap=0` **>0** |

- 规模 `n16r60`；两 seed **串行**；两臂**串行**。
- **单一变量（同 sha 只变一个开关）两条硬核验（跑前写进 mock 交付）**：
  1. B′ 树 `inround_visibility.enabled=0` vs `=1`：除开关分支外一切相同；`=0` 时 `prompt_fn_sha256` 与 `engine_version` **必须等于关臂基线**（关臂干净）；
  2. `git diff <C sha> <B′ sha> -- code/` **只允许**出现在轮内编排/开关读取处，**其余全等**。
- **新基线必须同批重跑**：轮内调度改动 ⇒ `mono_ts` 顺序、`prev_hash` 链、`events` 计数都变 ⇒ **T0/T5/D12 全系列不可当 C 臂**（§3.116/§3.117、ARCH §4.1）。**C 与 B′ 同批串行重跑**。（C 复用仅在「关臂逐位一致 + 独立核验裁定」下可议，**默认不使用**。）
- **防跑错树**：C 臂收批第一件事核「无 phase-B 决策者 **且** `gap=0`=0.0%」；若 C 出现 `gap=0>0` 或 phase-B 标记 ⇒ **停，判「跑错树」**。

---

## 4. 判据（跑前写死）

| # | 指标 | 达标线 | 未达档位 |
|---|---|---|---|
| **M1 机制层（主判据）** | `phase_B_decision_count` | **> 0**（每轮至少一名 phase-B 决策者） | **「可见性未生效」**（接线/实现问题） |
| **M1 机制层（主判据）** | `gap=0` 相邻对占比 | **> 0.0%**（从证据性零 → 正） | **「可见性未生效」** |
| **E 效应量级（并列，非唯一否决）** | `gap=0` 占比 | **∈ (0, ~2.6%]**（按 §2 上限） | 若在 (0,2.6%] 但**两 seed 不同向** ⇒ **「不足以下结论（效应在噪音带内）」** |
| **E（并列）** | `p50 gap` | **预期不动（=1）** | **非失败**（预期内）——只记录 |
| **Q1 复述闸** | `L-15 restate_rate`（`tools/d5/l15_restate_rate.py`） | 相对 C **≤ +2.0pp** | **「无效（回声：复述）」** |
| **Q2 重复闸** | `L-7 norm8`（`tools/d5/dialogue_metrics.py`） | 相对 C **恶化 ≤ +3.0pp** | **「无效（回声：重复）」** |
| **Q3 跑题闸** | `F-2_content_drift`（=F-2′，**禁用** `F-2_topic_drift`） | 相对 C **恶化 ≤ +2.0pp** | **「无效（内容漂移）」** |
| **代价闸** | `llm_calls` | 相对 C **≤ +40%** | **「作废（代价超限）」**，只记数不换算金额 |
| **S 结构闸** | `n_threads` | 相对 C **±15%** | **「作废（非单变量）」** |
| **接线** | mock：`=0` 关臂 `prompt_fn_sha256`/`engine_version` 与 C 一致；`=1` 时变 | 两档一致/变如预期 | 失败 ⇒ **「作废（接线失败/非单变量）」** |

**口径纪律**：Δ 一律用未四舍五入原始分数求差；线程级比例分母 = 全部 `thread_id` 去重（§3.119）；`F-2′` 只认 `F-2_content_drift`。

**判定合成**：
- M1（两条）+ Q1 + Q2 + Q3 + 代价 + S + 接线 **全过** ⇒ **「有效（轮内可见已生效）」**；
- M1 过、E 在 (0,2.6%] 但**两 seed 不同向** ⇒ **「不足以下结论（效应在噪音带内）」**（**不判「无效」**）；
- M1 未过（`gap=0` 仍 0.0%）⇒ **「可见性未生效」**（查接线，**不是**「无效」，**不是**「规模不匹配」）；
- Q1 或 Q2 破 ⇒ **「无效（回声效应）」**；Q3 破 ⇒ **「无效（内容漂移）」**；
- 代价/S 破 ⇒ **作废**。

---

## 5. 反事实（跑前写死；**含要求的必有两行**）

| 观察 | 判定词 |
|---|---|
| M1 + Q1 + Q2 + Q3 + 代价 + S + 接线 全过 | **有效（轮内可见已生效）** |
| **ON≡OFF 空臂**（`gap=0` 仍 0.0%，且/或 mock 中开关两档事件逐条相同） | **「可见性未生效」**（接线/实现问题；≠「无效」≠「规模不匹配」，§3.117） |
| **回声效应：复述/重复上升（Q1>+2pp 或 Q2>+3pp）** | **「保留基础设施但回退参数」**（轮内可见=「当面说话」前提，ARCH §6.3） |
| M1 过、`gap=0` 升但两 seed 不同向 | **「不足以下结论（效应在噪音带内）」** |
| `p50 gap` 未动 | **非失败**（预期内）——只记录 |
| `llm_calls > C + 40%` | **作废（代价超限）** |
| C 臂 `gap=0>0` / 有 phase-B 标记 | **作废（跑错树）** |
| `n_threads` 出 ±15% | **作废（非单变量）** |
| seed 间方向不一致 | **「不足以下结论（seed 间不一致）」**，不得挑有利 seed |

---

## 6. 止损条件 + 跑批安全（跑前写死）

### 6.1 托管（`arm-state-check-runbook.md` §4.5）
- 跑批放 **transient unit**（`systemd-run --collect`，`system.slice`），**不用裸 `setsid`**；
- **`--property=MemoryHigh=6G --property=MemoryMax=8G`**；
- 起跑前 `bash tools/d5/preflight.sh --tag d212` 返回 PASS + `pgrep` 确认无在跑批。

### 6.2 串行
- 两 seed（42/43）**串行**，每批独立 `side-root`；
- 起跑前 `pgrep -fa "orchestration run|run_batch"` 为空；preflight 并发闸不绕过。

### 6.3 关臂干净预检（对应「同 sha 只变一个开关」）

| 检查 | 期望 | 不过怎么办 |
|---|---|---|
| B′ 树 `inround_visibility.enabled=0` 的 `prompt_fn_sha256`/`engine_version` | **== C 基线** | 停，报「关臂不干净」 |
| B′ 树 `=1` 的 `prompt_fn_sha256` | **≠ 关臂值**且渲染 diff 只在开关处 | 停，报「接线越界（非单变量）」 |
| `git status --porcelain -- code/` | 空（树干净） | 停 |
| C 臂 `gap=0` | **0.0%** 且无 phase-B 标记 | 停，判「跑错树」 |

### 6.4 运行期止损（1/3 处必测，§3.112）
- **1/3 处判别量必测**：`phase_B_decision_count`、`gap=0` 是否有出现；若 1/3 处 mock/实跑 **phase-B 计数=0** ⇒ **立即停**，报「可见性未生效（接线）」；
- 提前停须标 `partial`，**不得当终态**。

---

## 7. 联网与撤销

- 若 `inround_visibility.enabled=1` 导致 `llm_calls > C + 40%` 或 `n_threads` 破闸 ⇒ 按 §4/§5 作废，**关臂 `=0` 即回退**（零语义变更）。
- **回退不回滚基础设施**：若判「回声（无效）」但机制本身工作，按 ARCH §6.3 保留「轮内可见」为基础设施、只回退参数（**须 Leader 就 P3 拍板**，见 §9）。

---

## 8. 不做什么（**明确边界，与 `d26_perception_lag.md` §6 一致**）

- **不做**「把 `upto_round` 改成 `state.round`/`state.round+1`」的**表面改动**：同轮事件确实还没提交，只会得 **ON≡OFF 空臂**（与 D2.3 同型，§3.117）；
- **不做**「放宽 `max_turns_per_round`」代替轮内可见：那是轮内推进上限，**不改变可见性**，属另一变量；
- **不做** D11 微时刻/`span`/跨回合 pending（D11 期③超集，另立）；
- **不实现、不跑批、不改 `code/`**（本轮冻结）；若要实现才能定预登记 ⇒ 只写方案与工量估计；
- **不与 D2.5a / D2.10 / D2.11 / A 对端 同批**（同批即双变量）。

---

## 9. 待拍板清单（ARCH-memo §6 三问 + 本件补充；**需用户/Leader 放行后方可实施**）

| # | 开放问题 | 来源 |
|---|---|---|
| **P1** | B 的轮内两阶段是否**可接受事件链变化**（打断与 T0/T5/D12 全系列可比性，须重跑基线）？ | ARCH §6.1 |
| **P2** | A 与 B 是否允许**同批连续跑**（各两臂，共 4 次 ≈3.6h），还是**必须分批**？ | ARCH §6.2 |
| **P3** | 若 B 产生**回声效应**，判无效后是否**保留「轮内可见」作为基础设施**、只回退参数？ | ARCH §6.3 |
| **P4（本件补充）** | `d25a_result.md` 已判 D2.5a「无效」⇒ 配额仍 2；而 §7 说 B 的 7% 上限「须在配额放开后才可能显现」。**B 是否仍按原序单独推进**，还是**先重议「配额方向」再定 B 排期**？ | 本件 §2 问③ |

> ⚠ 以上均**未拍板**；**P1 不批则本件冻结为纯设计**，不得进入实现。

---

## 10. 交付与执行顺序（依赖）

- 本件（预登记）+ 设计备忘（团队共享）。
- 顺序：`#T-INROUND-DESIGN` →（**P1/P4 放行后**）实现臂（加开关 + 关臂干净预检 + mock）→ 独立核验（`T-VERIFY-*`）→ 跑批 → `v2/evidence/d212_result.md`。
- mock 交付（跑前）：① 关臂 `prompt_fn_sha256`/`engine_version` == C；② 开臂变更且渲染 diff 只在开关处；③ phase-B 决策者选择集合单测；④ `_round_replies` 跨 A/B 累计计数单测（K 上限不被绕过）；⑤ C 臂 `gap=0`=0.0% 自检。
- 真 LLM 验真：`obs llm-cost --require-provider openai_compat`。
- **本件不 git add/commit/push**（由 Leader 统一安排）。
