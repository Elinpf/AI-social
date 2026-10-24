# D2.3 池口径 · 生产函数桥接 + place 不变性非平凡核查（**本轮未跑任何真 LLM 批**）

> 日期：2026-10-24 ｜ 分支 `feat/d23-place-affinity`（worktree `.worktrees/d23-place-affinity`）
> 基线树：分支基于 **`ac82a21`（= 预登记 commit）**；主树 master 此刻 `1ff2784`
> 日志：`v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl`（T1-OFF，n16r60 seed42，114 条发起）
> **本件只做离线读数 + 单测；未起跑任何真实 LLM 批**（主树 D2.8 B 臂 pid 279887 在跑，跑批纪律要求串行）。

## 0. 三条必须先说清的前提更正（与任务卡原文有出入，凭证据改口）

| # | 任务卡说法 | 事实（可复算） |
|---|---|---|
| 1 | 「做成可立即起跑的实现（分支就绪）」= 本轮要做的事 | **分支早已就绪**：`feat/d23-place-affinity` = `c2512ce`（`80d2975` 实现 + `c2512ce` mock 五项），10 例单测 + 189 例全量测试齐全；**只是从未 push 到 origin**（`git ls-remote --heads origin | grep d23` 为空）。 |
| 2 | 「离线净效应 +2.63pp ⇒ 值得跑批」 | 已有**正式裁决** `v2/evidence/d23_mock_verdict.md`：判 **「不可测（规模不匹配）」——不跑批**。理由：计划（`_weekly_slots`）**一次 run 只在 `round=0` 做一次**，那一刻无任何消息历史 ⇒ `place_peer_counts={}` ⇒ `w≡1` ⇒ **ON≡OFF（不是"效果不足"，是恒零）**。 |
| 3 | 「只改 `_participants` 的候选池（同地点优先）」 | 与预登记 §2 写死的机制**不是同一个东西**：预登记是**加权**（`w=1+α·count(A 在 place 与 peer 的共现次数)`, α=3，池不变只挪落点）；池口径（换池）是离线诊断工具 `d22_place_feasibility.py` 的 B 臂。**两者读数不可互换**（见 §3）。 |

> 本件**不改预登记任何阈值**，只把"哪个量是哪个量"钉死。

## 1. 逐字节复现：ON ≡ OFF（比"直方图相等"更强的证据）

```
$ sha256sum /tmp/d23_off/run.jsonl /tmp/d23_on/run.jsonl
66c570c9be4d62622567a80766f37553b5fc0d788a787e04ae57dd37faf6c7fd  d23_off/run.jsonl
66c570c9be4d62622567a80766f37553b5fc0d788a787e04ae57dd37faf6c7fd  d23_on/run.jsonl
（均 33556 行 / 24 rounds / 190 条 MSG / 74 threads）
```
⇒ mock 下 **ON 与 OFF 的日志 sha256 完全相同**。【已验证】
⇒ 之前 `d23_mock_verification.md` §2 报的"place 直方图 16 项逐项相等"是**平凡相等**，
**不能**当作"提前算 place 不改 place"的正面证据（它是"机制没触发"的旁证）。

## 2. 非平凡核查：`place` 是否被改动影响（预登记 §5 唯一结构性风险）【已验证】

新工具 `tools/d23/place_invariance_check.py`：真实模板表 + 真实地点表 + **完整一周 7×4 槽 × 16 居民 = 448 槽**，
**人为注入强极化 `place_peer_counts`**（保证权重真生效），逐槽比较 ON/OFF 的 `place`。

```
$ python3 tools/d23/place_invariance_check.py --root code
n_slots 448 | place_identical_rate_pct 100.0 | place_diff_count 0 | place_hist_equal true
comparable_slots 216 | participants_change_rate_pct 73.15
verdict: PASS（place 逐项不变 + 权重确实改了人）
```
⇒ `place` **逐项不变**（448/448），同时 `participants` 换人率 **73.15%** ⇒ 这是**非平凡**的单变量证据：
place 不变、对端变了。（原始读数 `v2/evidence/d23_place_invariance.json`）

## 3. 池口径 → **生产函数**的功能等价桥接【已验证】

问题：`50.88% / 90.35%` 这两个数是**离线工具自己实现**的口径，`code/life/` 里没有任何函数能算出它们
⇒ 将来接线也可能"接的不是那个东西"。
新工具 `tools/d23/pool_arm_repro.py` 用生产侧纯函数 `life.place_pool.pick_same_place_first()` 重算：

```
$ python3 tools/d23/pool_arm_repro.py --log v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl
n_init 114 | pool_arm_repeat_pair_rate_pct 50.88 | pool_arm_same_place_hit_rate_pct 90.35
evidence_reference 50.88 / 90.35 → match_offline_tool: true
```
⇒ 与 `d23_place_offline_verdict.md` **逐项相同（0pp 差）**；同地点优先语义由
`code/life/tests/test_d23_place_pool.py` 6 例钉死（含 **200 个种子穷举：同地点候选存在时必选中同地点**）。
（原始读数 `v2/evidence/d23_pool_arm_repro.json`）

## 4. 为什么池口径**现在接不上生产**（这是本轮的核心结论，不是偷懒）

`Planner` 在计划期只拿得到**自己的** `peers`/`places`；要判"同地点"，必须知道**别人该 slot 待在哪**，而：

- 别人的 `tid` 先要过 `_self_cash_ok()`（读**别人的私有现金**）；
- 别人的候选顺序还受 `focus`（**别人的 LLM 判定标签**）影响；

⇒ 生产侧**没有任何 `peer_places` 来源**；硬凑近似会把"私有状态"混进单变量 ⇒ 预登记的单变量论证当场失效。
⇒ 正解是 `d23_mock_verdict.md` §4 已给的：**改"何时算"（先全城定 place 的两阶段计划）**，属架构级改动，须单独立项。
⇒ 故 `life/place_pool.py` 以 **inert** 状态登记（`tools/inert_registry.json::place_pool_same_place_first`,
`expected_status=missing_wiring`），`python3 tools/check_inert_registry.py` **与期望不一致 0 条**。
**不接线、不假装它有活。**

## 5. 读数成表（与预登记阈值逐条对照）

| # | 指标 | 实测 | 命令/来源 | 预登记阈值 | 达标？ |
|---|---|---|---|---|---|
| 1 | `self_check_orig_matches_actual_rate`（A 档复现） | **100.00%**（114/114） | `d22_place_feasibility.py`【已验证】 | =100%（否则停） | **达标** |
| 2 | `repeat_pair_rate` A 现状 / C 等权 / B 池口径 | **42.98 / 48.25 / 50.88%** | 同上【已验证】 | — | 复现判决件 |
| 3 | `map_artifact_pp` = C−A | **+5.27pp** | 同上【已验证】 | 单独报，不入判定 | 同 D2.2 交叉印证 |
| 4 | `mechanism_pp` = B−C（**池口径**） | **+2.63pp** | 同上【已验证】 | **P ≥ +5.0pp** | **不达标**（差 2.37pp） |
| 5 | `mechanism_pp`（**预登记加权口径**，T1 映射自检） | `change_rate_B_vs_C` = **59.65%** | `tools/d23/t1_mapping_check.py`【已验证】 | M1 ≥ 20% | **达标**（M1） |
| 6 | `same_place_hit_rate` | 现状 **29.82%** → 池口径 **90.35%** | 【已验证】 | 非判据（B 档内建优势，判决件已声明） | 仅描述 |
| 7 | `change_rate_B_vs_A`（池口径） | **87.72%** | 【已验证】 | — | 描述 |
| 8 | 池可用性 | exact 103 / ±1 2 / **fallback_all 9（7.9%）** | 【已验证】 | — | 可接受 |
| 9 | `place` 逐项不变（**非平凡**） | **448/448 = 100%**，同期换人 73.15% | `place_invariance_check.py`【已验证】 | 必须 100%（§7.2 作废线） | **达标** |
| 10 | 池口径 → 生产函数等价 | 50.88% / 90.35%，**0pp 差** | `pool_arm_repro.py`【已验证】 | 必须逐项相同 | **达标** |
| 11 | 单测 | D2.3 16 例 **passed**（权重 10 + 池 6）；全量 `code/life/tests` **195 passed in 172.84s** | `pytest code/life/tests/test_d23_place_*.py` / `PYTHONPATH=code pytest code/life/tests -q`【已验证】 | 全绿 | **达标** |
| 12 | F1/F2/F3 形态闸 | **在 T1-OFF 基线上就三项全 FAIL**（F1 82.35% vs T5 57.84% 漂 +24.51pp；F2 0.147 vs 0.365 漂 −21.76pp；F3 40.0 vs 53 漂 −24.5%） | `tools/d12h/shape_gate.py`【已验证】 | 全 PASS | **不可判**（T5 常数属别的树） |
| 13 | mock ON vs OFF 是否 no-op | **日志 sha256 逐字节相同** | `sha256sum`【已验证】 | — | **恒零（不可测）** |

**关键结论（两条，都不改阈值）**
1. 任务卡引用的 **+2.63pp 是「池口径」离线值**，而预登记 P 判据 **≥ +5.0pp** 是按**加权口径**（离线预期 +9.64pp）定的
   ⇒ **池口径按预登记阈值本来就不达标**（+2.63 < +5.00）。要跑池口径，必须**先按池口径改预登记阈值**（须 Leader 裁决，不得我改）。
2. 无论哪个口径，在 **n16r60** 下都由 `d23_mock_verdict.md` 判 **「不可测（规模不匹配）」**：
   加权口径因"计划期历史为空"恒零；池口径因"无 peer→place 来源"根本接不上。

## 6. 起跑所需的后续条件（本件不开跑）

1. **先解阻断**：取其一 ——（a）两阶段计划（先全城定 place 再定对端，池口径才可接线，须新预登记）；
   （b）规模 ≥144 轮（2 周，才有"第二次计划带 week-0 历史"的生效期），成本 ≈2.4×/臂；
2. **跑批纪律**：`bash tools/d5/preflight.sh --tag <name>` 返回 PASS + `pgrep` 确认无在跑批（此刻 **FAIL**，D2.8 B 臂在跑，预期内）；
3. **口径先改预登记**：池口径要按 `+2.63pp` 这个量级重定 P 阈值（现 +5.0pp 与池口径不匹配）；
4. **T 闸必须用同树 OFF 臂自建基线**，不得套 T5 常数（本树 OFF 就已三项越界）；
5. 保留 **C 档**（否则 +5.27pp 映射伪影会被当成机制，runbook §3.115）。

## 7. 文件与 sha256

| 文件 | 说明 |
|---|---|
| `code/life/place_pool.py` | **inert** 池口径纯函数（同地点优先 + 累积等权轴） |
| `code/life/tests/test_d23_place_pool.py` | 6 例（含 200 种子穷举） |
| `tools/d23/place_invariance_check.py` | 非平凡 place 不变性核查 |
| `tools/d23/pool_arm_repro.py` | 池口径 → 生产函数等价复算 |
| `v2/evidence/d23_place_invariance.json` / `d23_pool_arm_repro.json` / `d23_place_feasibility_rerun.json` / `d23_t1_mapping_rerun.json` | 原始读数 |

> 近似声明（随结论一起引用）：在场集合用"该 round 发过消息的 `(agent, place)`"近似，**非 plan 真值**；
> 退化到全员的 9/114 已在读数里单列。
