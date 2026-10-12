# T236 · 基线重冻（第二轮）—— 以当前 HEAD 为 canonical 基线

> 作者：obs-stats-dev ｜ 2026-10-12（夜跑夜）｜ 关联：T236 / T262 / T271 / T274
> **本基线对应 sha `6a5f14e`；`T265 wake` 若启用、或后续 T276`native` 续跑落地，预期需要第二次重冻。**

## 1. 新基线身份（可复算）
| 项 | 值 |
|---|---|
| 源日志 | `v2/evidence/run_t236_canon_n20_llm.jsonl` |
| **冻结 sha** | **`6a5f14e`**（19:01 冻结；A 批在主树、活树跑） |
| **`engine_version` 指纹** | **`sha256:f1ea31a3276dc97df36815e038809e2ff6a8c88241f3199355a48a50cb96d3d1`**（= `WORLD_INIT.fingerprint` = preflight = 当前代码，**三方一致** ✓） |
| 日志 sha256 | `sha256:13f8d668887d1b3176af354472fbb040ac0881902075c631218e8a6b1861fb6e` |
| N / rounds / seed | 20 / 84 / 42 ｜ provider `openai_compat`（LLM_CALL=4794，无 mock 混入） |
| 事件数 | **301,384**（旧 canonical ~130k；T244 三族默认开是主因，见 §3） |
| chain / replay / conservation | 全 **True**（host.log）｜ `state_hash=sha256:a8b6da39…` |
| **复算命令** | `cd code && /opt/openjiuwen/workswarm-venv/bin/python -m orchestration run --life --seed 42 --agents 20 --rounds 84 --out ../v2/evidence/run_t236_canon_n20_llm.jsonl --side-root <side> --flush-every 12`（经 T271 逃逸托管） |
| 起止 | 2026-10-12 19:01:23 → 20:21:22（**≈80 min**，见 §6） |

## 2. 旧基线归档（**不删、带时效标注**）
- `v2/evidence/archive/golden_baseline_pre_t236.json` —— **旧 `code/obs/golden_baseline.json`**（`n20_week_seed42` = n_events **128,564**、feature_set `v2-P1-final`）。**有效期：截至 `6a5f14e` 重冻前；已被本节新基线取代。**
- `v2/evidence/archive/metrics_baseline_p1_pre_t236.json` —— **旧 `metrics_baseline_p1.json`**（frozen_from `run_p1_final_n20_llm.jsonl`、feature_set `v2-P1-final`）。**同上，已被取代。**
- 新 `golden_baseline.json`：`n20_week_seed42` = **n_events 301,384**、feature_set **`v2-T236`**、rounds 84。
- 新 `metrics_baseline_p1.json`：见下（econ_loop + social_key）。

> 注：更早的 `archive/golden_baseline_pre_t104.json` 保持原样（更前一版）。

## 3. 本次重冻照含的变更（一行一条）
1. **T228** — 新增 `life.memory.persist_vec`（side `.vec` 分档开关）→ 进指纹。
2. **T234 phase1** (`74f75d0`) — 新增 `life.narrative.persist_body`（叙事正文落盘开关）→ 进指纹。
3. **T221c** — life 侧 M6 降级开关（默认关，键进指纹）。
4. **T244** — 睡眠/遗忘/人格三族**默认开**（`config/life_v2.json`）→ **改行为**（**事件量 ~130k→~30万，≈翻倍**；§5 消融 C 实测减半）+ 进指纹；⚠️ **三族耦合、暂不可单独消融**（缺口，留白天相位）。
5. **T247** — 新增 `life.skill.persist_body`（SKILL_OUTPUT 正文 writer，默认 true）→ 进指纹。
6. **T255** (`f69c2f4`) — `world_director.json::enabled` false→true + inert 表三条 off→on → **改行为**，进指纹。
7. **T248** (`7e092f7`) — obs 居民级聚合**排除非 Agent 主体**（MARKET 等）→ **口径变更**（`energy 19.57→20.55`、`mastery 25→29`、`n_need_updates 3399→3310`）；非指纹，但数字因此不同。
8. **T264** (`3ba744a`) — 可见性语义对齐 08 §8–§10（唯一真源；G1/G2/G3）→ `perception_scope.json` 改 → 进指纹。
9. **T265** (`5d6a495`) — 乙+双时钟落地（`policy.wake` 块；**`wake.enabled` 默认 false** ⇒ 行为≈pre-wake，仅多 WAKE/IDLE 审计事件）→ **新键进指纹**。
10. **T266** (`96acaf6`) — 08 可见性 D2/D3 + `perception_scope` 注释 → 进指纹。
11. **T268** — c1 共享不可变源事件 + 每 agent 指针 → **改 side 存储布局**（`side://src/<sha>.txt|.vec`）；**无 config 键**；⇒ **T229 归档必须覆盖 `side/src/`**。
12. **T276** (`5d6b0aa`) — `run_e2e` 新增 `--resume-from/--target-round`（**加性、未用不改行为**）；`tests/test_resume_from_flush.py` 置 `xfail(strict=True)`（棘轮，待 life `restore()`）→ **不新增 config 键、不改指纹**。

## 4. T262 周期 flush 证据（**真实非计划死亡下**，不删）
- **关键证据**（首轮被 memguard 重启杀掉时留下）：
  `v2/evidence/archive/run_t236_canon_n20_llm.partial-r35.jsonl` —— **34,041,041 B / 74,457 行 / parse_fail=0 / max_round=35 / 末条 `TURN_SEAL@(35,74456)`**；
  `v2/evidence/archive/t236_flush_curve.txt` —— 15.8KB(r0) → 21.7MB(r23) → 34.0MB(r35)。
  （partial 日志 sha256 = `adeb5e36b7ccdc21cd1695541f0d5c9f107687eb6c1e21deeb4fbd5beadfdc07`；`*.jsonl` 被 .gitignore，**未入库**——留盘作证据，凭 sha256 可校验。）
- **本轮成功跑批的 flush 心跳**（`/root/t271/runs/nightly/A/heartbeat.tsv`）：15,838(r0) → 15.1MB(r11) → 41.2MB(r35) → 60.7MB(r47) → 110.7MB(r71) → **140.9MB(EXIT)** ⇒ **每 12 回合原子落盘、单调增长、跨越全部回合** ✓。

## 5. 今晚 4 批（A/B/C/D）结果 —— 真实 LLM，全 exit 0
| 批 | 开关 | 事件 | LLM_CALL | 指纹 | state_hash | 末 |
|---|---|---:|---:|---|---|---|
| **A 基线** | `-` | 301,384 | 4794 | `f1ea31a3` | `a8b6da39` | r83 |
| B 关世界导演 | `world_director.enabled=false` | 301,395 | 4794 | `a89546fd` | `07046536` | r83 |
| **C 关三族** | `life_v2 sleep/forgetting=false` | **151,968** | 4794 | `f8d3f0a8` | `dd1c7906` | r83 |
| D 开双时钟 | `wake.enabled=true` | 304,607 | 4718 | `adaede05` | `b7c21436` | r83 |

- ★ **第一条真实消融效应**：**关掉睡眠/遗忘/人格三族 → 事件量 301,384 → 151,968（≈半）**；说明 **T244 三族贡献约一半事件量**（与"默认开不免费"一致）。
- **B ≈ A**（301,395 vs 301,384）：世界导演（`enabled=true`）在**默认剂量**下产出的事件**很少**（宏观群体事件是低频）——值得单独核实"世界导演是否真的产生了预期事件"。
- **D 略多于 A**（304,607 vs 301,384）；4 批**指纹各异**（开关各进指纹）✓ 消融可溯。
- ⚠️ **口径提醒**：`nightly collect` 早报把这 4 批标为 **INTERRUPTED(71/84)**，**是误判**（见 §7）。

## 6. 环境事实（写进记录）
- **平台 18:23:28 因 memguard 重启过一次**（peak 8.9G）；`anon` 现 **4.22G**；**swap 已用 3.5G/3.8G**。
- **跑批全程逃逸**（各批 cgroup = `/system.slice/t271-<B>.service`，**不含 jiuwensnwarm.service**）→ 18:23 平台重启**未杀批次** ✓（T271 挣来的）。
- **8 批（A–D + mock 演示）跑批约 80–90 min 跑满 84 回合**（远快于预估 2.5–3.3h）。**成因【未验证】**：疑 **端点今晚更快 + T264 可见性索引消除 O(N²) 重扫**叠加；**未做单变量隔离，不写成结论**。

## 7. 偏差与缺口（诚实）
- ① **流水线一次起了 4 批**（未走"A 优先 + 1 路探针→2 路"）→ 与排班口径不符（**结果无损**，但非计划形态）。
- ② **`nightly collect` 状态误判**：把 **A–D 标 `INTERRUPTED(71/84)`**，而**实际日志达 `TURN_SEAL@83`（=完成84回合）**。**根因**：collect 用**心跳最后一行的 round**（20:11 的 71）判"是否达目标"，**心跳间隔(10min)内已完成 → 读到的 round 滞后**；**未回读日志末行 round / RUN_END**。**→ 报 release-engineer 修**（判"完成"应以**日志末行 round==target** 或 runner rc=0/RUN_END 为准，不应以心跳 round 为准）。
- ③ **`meta.ended_at`/`engine_version_fingerprint`**：跑完时为空，**`collect` 已回填**（A meta 现已有 ended_at=fingerprint）；即 **finalize 依赖 collect**，而非 runner 结束即写——**预期化即可**（或让 runner 退出即 finalize）。

## 8. 新 `metrics_baseline_p1.json`（A/基线）
```json
{"frozen_from":"v2/evidence/run_t236_canon_n20_llm.jsonl","log_sha256":"sha256:13f8d668…","feature_set":"v2-T236",
 "econ_loop":{"M_final":37433,"M_min":0,"M_max":197200,"M_target":200000,"M_never_negative":true,"V":0.062727,
   "Y_mu":47373,"median_wage_mu":null,"gini_net_worth":0.768836,"tax_pool_final":2694,"n_produce":317,
   "mint_burn_balance_window":0.004862,"price_cv_mean":0.0},
 "social_key":{"channels":{"DM":165,"PUBLIC":59,"GROUP":8},"comm_directed_edges":168,"comm_reciprocity":0.244444,
   "n_groups":8,"norm_adopted":19,"n_contracts":0,"n_votes":0}}
```
（完整见 `v2/evidence/metrics_baseline_p1.json`；G6 golden 见 `code/obs/golden_baseline.json` 的 `n20_week_seed42`。）
