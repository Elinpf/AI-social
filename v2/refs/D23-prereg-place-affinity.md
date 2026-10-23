# D2.3 预登记 · **地点亲和的对端选择**（`place`-affinity partner choice）

> 立此存照：**2026-10-24，在任何 D2.3 代码改动与跑批之前**。判据、阈值、反事实先写死。
> 依据：`v2/evidence/d21_partner_choice.md`（对端从 15 人均匀抽、**连 `place` 都不读**）、
> `v2/evidence/d23_place_offline_verdict.md`（离线三档，净效应 +2.63pp~+14.91pp）、
> `v2/refs/batch-hosting-runbook.md` §3.113（口径并列）/§3.115（等权对照）。
> 预登记锚点：写此文件时 master HEAD = `6da8828`。

## 1. 目标（北极星对齐）

让居民**更像在同一个地方生活**：在哪儿待着，就更容易跟**在那儿遇见过的人**搭话。
现状 `planner._participants()` 对全部 15 名同伴均匀抽，`place` 完全不参与 ⇒ 咖啡馆里的人可能约城另一头的人。
离线实测：**现状 70.18% 的发起是"跨地点约人"**。

**这不是"降词面重合"那条路**（D12-E…I 已证与文体同一旋钮），而是**改"谁跟谁说话"**，与措辞无关。

## 2. 代码事实与改动点（精确到函数）

```
code/life/planner.py:92-138  plan_slot():
    for tid in cands:
        places = _open_places(tid, slot)                  # 该模板允许的地点
        parts  = _participants(tid, slot_id)              # ← 现在在这里抽对端（place 未定）
        eligible.append((tid, sorted(places), parts))
    ...
    place = _pick(f"{agent}|{slot_id}|place", places)     # ← place 在 participants 之后才定
code/life/planner.py:73-90   _participants(): _pick(f"{agent}|{slot_id}|{tid}|p{i}", rem)
```

**关键论证（单变量成立性）**：`place` 的取值由**独立种子** `f"{agent}|{slot_id}|place"` 与 `places` 列表决定，
**与 `participants` 无关** ⇒ 把 place 的计算**提前**（或按同一式在 `_participants` 内复算）**不会改变 place 的分布**。
⇒ 本臂：**place 不变，只有对端变**。

**改动范围（3 处 + 1 开关，默认关）**：
1. `planner.py::_participants(tid, slot_id, **place=None**)` —— 新增**可选**参数；`place is None` 时走**原 `_pick` 逐字节路径**；
2. `planner.py::plan_slot()` —— 循环内先按同一式算出该 tid 的候选 place，再传进 `_participants`；
3. `planner.py` 新增 `place_affinity` 权重函数（纯函数）+ `agent.py::_weekly_slots` 构造 Planner 时传入**只读**的
   `place_peer_counts: {(place): Counter(peer→次数)}` 快照（来自**该居民自己的**消息历史，计划期可得）；
4. 开关：环境变量 `HITT_PARTNER_PLACE_AFFINITY`（默认关；`=0` 或缺省 ⇒ 行为与 master **逐字节一致**）。

**权重（写死，跑前不改）**：
```
w(peer) = 1 + α · count(A 在 place 下与 peer 的共现次数)     α = 3
count 口径：A 自己发出的、或别人发给 A 的、place == 该 place 的消息条数（双向计入）
确定性抽样：u = sha256(seed)[:8] / 2^32；累积权重轴取点（与 §3.115 的 C 档同映射）
```

## 3. 三档对照（**判定只用 B−C**）

| 档 | 定义 |
|---|---|
| **A 现状** | 原 `_pick`（`%len`）：**必须 100% 复现历史**，否则本臂代理不可信，停 |
| **C 等权** | 同一权重轴映射 + **α=0**（w≡1） ⇒ 隔离**映射伪影** |
| **B 机制** | 同一映射 + α=3 |

> 与 D2.2 不同：本臂 B 与 C **同池同映射**，只差权重 ⇒ `B−C` 是**纯权重效应**，不含池差异，也不含映射伪影。

## 4. 判据（跑前写死；任一未达即按其档位判，不得事后加条件）

| # | 指标 | 达标线 | 档位 |
|---|---|---|---|
| **M1 机制生效** | `change_rate_B_vs_C`（同一 seed 下 B 与 C 选中不同对端的比例） | **≥ 20%** | 未达 ⇒ 判**「机制未生效」**（改接线/权重，不宣布方向错） |
| **P 主判据** | `repeat_pair_rate(B) − repeat_pair_rate(C)` | **≥ +5.0pp**，且 bootstrap（B=2000,seed=42）**CI 下界 > 0** | 未达 ⇒ 判**「无效（效果不足）」** |
| **S1 保结构** | `distinct_partners_mean` 相对 C 降幅 | **≤ 10%** | 破 ⇒ **「无效（社区塌缩）」** |
| **S2 保结构** | `n_threads`、`n_msgs_total` 相对 C | **±10%** | 破 ⇒ **「作废（非单变量）」** |
| **T 文体闸** | `tools/d12h/shape_gate.py` 的 F1/F2/F3（F2 已修 strict 36.47%） | 全 PASS | 破 ⇒ **「作废（形态漂移）」** |

**离线预期（供跑后对照，不作判据）**：α=3 时 `B−C = +9.64pp`（57.89% vs 48.25%）、
`distinct_partners_mean 3.94 vs 4.25`（**−7.3%**，闸内）、`change_rate_B_vs_C = 80.70%`。
⇒ 若真跑结果**远低于**该预期（如 B−C < +2pp），第一嫌疑是"计划期可见的历史比离线少"，需如实记录，**不得改阈值**。

## 5. 反事实（跑前写死）

在 **M1 过闸**前提下：

| 观察 | 判定词 |
|---|---|
| P ≥ +5pp 且 CI 不含 0，S1/S2/T 全过 | **有效** |
| P 在 (0, +5pp) 之间但 CI 含 0 | **不足以下结论** |
| P ≤ 0 | **无效（效果不足）** |
| `same_place_hit_rate` 大升而 P ≤ 0 | **无效（只是把人挪了地方，关系没变）** |
| S1 破（distinct 降 >10%） | **无效（社区塌缩）** |
| S2 或 T 破 | **作废（非单变量 / 形态漂移）** |

## 6. 成本与执行

- 规模：**n16r60 seed42**，两档（C 与 B）各跑一次 ⇒ **2 次串行**；按 D12-I 实测 ≈ **52 min/次 ⇒ ~1.8h**，calls ≈ 4200/次。
- **必须保留 C 档**（否则 +5.27pp 映射伪影会被当成机制，§3.115）。
- 起跑前：`pgrep` 确认无在跑批；跑批期间禁改 `code/life|orchestration|config|engine`；真 LLM 须 `obs llm-cost --require-provider openai_compat` 验真。
- 分支：`feat/d23-place-affinity`（worktree），主树只做集成。
- 交付：`v2/evidence/d23_result.md` + 读数工具输出 + `run_batch.rc/end` + 成本记录。

## 7. 失效条件（跑前声明，避免事后找补）

1. `count` 在计划期**几乎全为 0**（离线 `zero_weight_share = 67.1%`，计划期只会更高）⇒ 权重退化为常数，
   `change_rate_B_vs_C` 会接近 0 ⇒ 直接判「机制未生效」，**不进入 P 判定**；
2. 若 `_participants` 前置 place 计算导致 `place` 分布变动（A/C 两档 place 直方图不一致）⇒ **作废（非单变量）**，
   这是本臂唯一的结构性风险，**必须在 mock 阶段先验证 place 直方图逐项相等**。

## 8. 与既往结论的关系

- 与 **D2.2（近因加权）**不同：那臂净效应全负（16 组网格），本臂离线为正；
- 与 **A2（对未回对端不发起）**不同：A2 是"事后拦"，本臂是"事前选"；
- 与 **D12 系列**无关：不动提示词、不动措辞，**不触碰"降重合 ⇄ 文体"那个旋钮**。
