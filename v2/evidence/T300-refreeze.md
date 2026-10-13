# T300 · 基线重冻（第三轮）—— 以「本轮已定稿变更后的树」为 canonical 基线

> 作者：obs-stats-dev ｜ 2026-10-13（D10 白昼跑批）｜ 关联：T298 / T287 / T323 / T330 / T333 / T328③ / T271 / T339
> **本基线对应：跑批所读世界层 `8fb2263`；记录用 HEAD `9374c3a`；计算基线 obs 代码 `fbf9c33`（两个 sha 分开记）。**
> 运行窗口：2026-10-13 10:22:20 → 11:52:19（**90 分钟**）；`t271-t300.service` transient 逃逸、`ExecMainStatus=0`。

## 1. 新基线身份（可复算）
| 项 | 值 |
|---|---|
| 源日志 | `/root/t271/runs/t300/run.jsonl`（`.jsonl` 不入库；前端从该路径实时跟随） |
| **① 跑批所读世界层 sha** | **`8fb2263`**（T328③；世界层最后改动） |
| **② 记录用 HEAD sha** | **`9374c3a`**（T345 证据提交，只动 `v2/evidence/**`，未触世界层） |
| **③ 计算基线 obs 代码 sha** | **`fbf9c33`**（本任务加 `time_model` 元数据那笔） |
| **`engine_version` 指纹** | **`sha256:869c195348f073021c3f5d3271930687750fda7998b3c8a7a79825344f7f0ddf`**（= `WORLD_INIT.fingerprint` = 实测；与 T236 的 `f1ea31a3`、T292/T310 的 `f378d5d3` 均不同 ⇒ 本轮再变） |
| 日志 sha256 | `sha256:33b7651f2b11d5eaf5720dbd0560cc2ea2a468d37f7319d972b2d7fafd808a08` |
| N / rounds / seed | 20 / 84 / 42 ｜ provider `openai_compat`（`LLM_CALL=4797`，无 mock 混入） |
| 事件数 | **292,963**（T236 为 301,384；**−8,421**，主因见 §3） |
| chain / replay / conservation | 全 **True**（host.log）｜ 末回合 `TURN_SEAL round=83` ⇒ **84 回合跑满** |
| **终态 `state_hash`** | **`sha256:ab38d431d951eb34fddc611792d56823d3c618f4fadf5f1c578adbc4bd2c23ba`** |
| `time_model` | **`atomic`**（interval 默认 off；取 `WORLD_INIT.payload.time_model`） |
| 复算命令 | `cd code && python3 -m orchestration run --life --seed 42 --agents 20 --weeks 1 --rounds 84 --out <log> --side-root <side> --flush-every 12`（经 `tools/t271/host_batch.sh` 逃逸托管） |

## 2. 旧基线归档（**不删、带时效标注**）
- `v2/evidence/archive/golden_baseline_pre_t300.json` —— 旧 `code/obs/golden_baseline.json`（`n20_week_seed42` = n_events **301,384**、feature_set `v2-T236`）。**有效期：截至本轮重冻前；已被本节新基线取代。**
- `v2/evidence/archive/metrics_baseline_p1_pre_t300.json` —— 旧 `metrics_baseline_p1.json`（feature_set `v2-T236`）。**同上，已被取代。**
- 更早：`archive/golden_baseline_pre_t236.json` / `metrics_baseline_p1_pre_t236.json` / `golden_baseline_pre_t104.json` 保持原样（更前一版，**已过期**）。
- 新 `golden_baseline.json`：`n20_week_seed42` = **n_events 292,963**、feature_set **`v2-T300`**、`time_model=atomic`、`final_state_hash=ab38d431…`、`provenance{run_tree_sha, world_layer_sha, baseline_code_sha, engine_version_fingerprint}`。
- 新 `metrics_baseline_p1.json`：见 §8。

## 3. 变更清单（**四档**，以锚定书 §7 `v1.3.47` 为准；自 T236 基线 `6a5f14e` 以来）
| # | 提交/任务 | 内容 | 动 config/指纹 | 分类 | 实测佐证 |
|---|---|---|---|---|---|
| 1 | `8d4c8b9`（T298） | life 运行期记忆缓存对齐权威 + `restore()` 补前向态 | 否（life/*.py） | **【行为变】** | 一次性路径产出变：`MEMORY_FORGET` 143,543→**134,367**（−9,176）；总量 −8,421 = 与 T310 归因的"树前进"一致 |
| 2 | `76de474`（T287 期①） | 新增 `config/time.json`（default-off）→ 进 `FINGERPRINT_FILES` | **是**（新键） | **【仅指纹变】** | `time_model` 默认 `atomic`（off ⇒ 不改结算） |
| 3 | `8e5aace`（T320 登记）→ `T323` | `config/life_v2.json::persona_drift` 新增 `min_importance`/`min_windows` | **是**（`life_v2` 直读、已纳指纹） | **【仅指纹变】** + 默认可达 ⇒ **叠加【仅日志增行】** | ⭐ 实测 `PERSONA_DRIFT_CANDIDATE` **0→527**（默认路径确实可触发）⇒ 日志条数变，**不得并成"行为变"** |
| 4 | `T326→T332(273015c)→T333(实现)` | `PERSONA_DRIFT` 候选判据（代码级单一真源）+ 一等可消融键 `persona_drift.criterion∈{strict,natural}`（默认 `natural`） | **是**（新键 `persona_drift.criterion` 落 `life_v2.json`） | ⭐ **【行为变】+【指纹变】** | ⭐ 实测 `PERSONA_DRIFT` **0→240**（默认 `natural` 真实生效）⇒ 行为面变；指纹源=**`life_v2.json::persona_drift.criterion`**（**非** `emotion_lexicon.json`，该形态已被 `273015c` 推翻、文件不存在） |
| 5 | `T330`（端口化；被验 `fc412a8`） | 结算可见端口化 | 否 | **【无行为变（等价）】**（`T331b` 非作者复验） | seq 180/180 等、反向必红 |
| 6 | `T325` | mock 反思文本含情感词（门禁） | 否 | **【无行为变（装置）】** | — |
| 6b | `c6857f9`（T278） | `SERVICE_DELIVERED` 最小切片（服务即时交付档，**`policy.service_delivered.enabled` 默认 `true`**） | **是**（新键；默认 on） | **【仅日志增行（族替换）】**（设计声明 inventory-neutral 等价；**语义等价未由本轮隔离实测**） | ⭐ 实测 `PRODUCE` 317→167（−150）、`SERVICE_DELIVERED` 0→**149**（≈族替换、净 −1）——`PRODUCE{service}` 改由 `SERVICE_DELIVERED` 交付 |
| 7 | `a14d2f4`（T312，已完成） | 读路径增量聚合（逐条等价） | 否 | **【无行为变】** | 读路径等价 |
| 8 | `T328③`（`8fb2263`） | `recent_income` 按 agent 标量累加器（去窗口逐回合遍历） | 否 | **【无行为变】** | `T345`/`9374c3a` 非作者核：三配置逐条等价、`state_hash` 跨版本逐位不变 |
| 9 | `T319`(`2c28880`)/`T322`(`e0a7acd`)/`T288`/`T295`/`T294`/`T43`/`T103` 等 | 引擎登记 / restore / 读路径等价 / 测试 / 装置 | 否或新键 | **【无行为变（等价/测试/装置）】** | 见各自说明 |

> **四档统计**：**【行为变】2 项**（T298、T326→T333）｜**【仅指纹变】3 项**（T287 `time.json`、T323 `persona_drift` 两键[叠【仅日志增行】]、T278 `service_delivered` 键[默认 on]）｜**【仅日志增行】2 项**（T323 `PERSONA_DRIFT_CANDIDATE`、T278 `SERVICE_DELIVERED` 族替换）｜**【无行为变】多项**（T330/T325/T312/T328③…）。
> ⚠️ **下轮为何仍会作废（分界线 B 后）**：`D11` 期②/③ 本轮**不放行**（等 08 前置 + 串行冲突解除 + 本次完成后）⇒ 期②/③ 落地时会再动世界层/指纹，**本轮基线届时作废一次属正常代价**（`v1.3.49` 裁定=先冻再改）。

## 4. 字节一致测试（H2，命令 + diff）
**动因**：给 golden 加 `time_model` / 给既有条目补 `atomic` 会改 JSON 结构 ⇒ 必须证明**除新增字段外数值逐字节不变**。
- 证据：**`v2/evidence/t300-byte-consistency.txt`**（绑 `fbf9c33`）。
- 方法：对**旧 log** `run_t236_canon_n20_llm.jsonl` 用**新代码**重算，与「未加字段的 pre-prep 存档」比 → **`ADDED=['time_model'] / REMOVED=[] / CHANGED=[]`**，两次调用**字节相等**，diff 只现 `+ "time_model": "atomic"`。
- 既有基线标 `atomic`：`golden_baseline.json` 的 n3/n10/n20 三处加 `"time_model":"atomic"`（**diff 只有 +time_model 行**）。
- 测试：`pytest tests/test_obs_golden_time_model.py`（4 例）+ 全量 `pytest tests/test_obs_*.py` → **140 passed**。

## 5. 跑批装置事实 + 两条教训
- **托管**：`t271-t300.service`（cgroup `/system.slice/t271-t300.service`，**逃逸** `jiuwenswarm.service`）；`MemoryHigh=6G`/`MemoryMax=8G`；凭证仅 `EnvironmentFile=code/.env.local`。
- ⚠️ **本次跑批「耗时」读数受一次并发 verify 影响**：约 **10:44 前后一次 `make verify`（≈3–4 分钟，sandbox-test-lead 补跑）** ⇒ **耗时读数受扰，如实标注**；**世界数值（事件数 / `state_hash` / 指纹）不受影响**。
- ⚠️ **教训①**：`--flush-every 12` ⇒ **活着的批看起来像死的**（前 12 回合 / 约 15–25 分钟不可观测）——有人据此误判"跑批已结束"。
- ⚠️ **教训②**：**判"有无批在跑"不要看日志新旧**；用 `systemctl is-active 't271-*'` 或 `pgrep -f "orchestration run"`。（与"下轮把 flush 调 1–2"配套才自洽。）
- ⚠️ **诚实缺口**：本轮**未**做 `flush=12 vs 1` 的对照实测 ⇒ `flush` 间隔对世界语义的影响**设计上中性（T262 初衷）+ 本轮未实测对照**（不给"已证等价"的结论）。已排入下一轮小规模对照。

## 6. 关键族计数（新 vs T236 基线，逐族 delta）
| 类型 | old | new | Δ |
|---|---:|---:|---:|
| `MEMORY_FORGET` | 143,543 | 134,367 | **−9,176** |
| `MEMORY_WRITE` | 58,531 | 58,547 | +16 |
| `PERSONA_DRIFT` | 0 | **240** | **+240** ← T333 默认 `natural` 生效 |
| `PERSONA_DRIFT_CANDIDATE` | 0 | **527** | **+527** ← T323/T333 路径可达（identity/审计） |
| `PRODUCE` | 317 | 167 | −150 |
| `EXCHANGE_SETTLED` | 20 | 25 | +5 |
| `LLM_CALL` | 4,794 | 4,797 | +3 |
| `LLM_JUDGMENT` | 1,010 | 1,010 | 0 |
| `RELATION_CHANGE` | 16,725 | 16,725 | 0 |
| **TOTAL** | **301,384** | **292,963** | **−8,421** |

## 6b. 事件数 −8,421 逐项归因（leader 硬要求：要么归因，要么写"未归因"，不许沉默）
> **算数闭合**：下分组 delta 逐族相加 **= −8,421**（无未计入残差）；但**因果归因**分两类——**可隔离归因** vs **机制归因（未做单变量隔离）**。

**A. 可隔离归因（指向具体变更）**
| 归因 | 族 | Δ | 机制 |
|---|---|---:|---|
| **T298**（行为变） | `MEMORY_FORGET` | **−9,176** | 记忆缓存对齐权威 + `restore()` 补前向态 ⇒ 遗忘量下降（**主导项**） |
| **T298** | `MEMORY_WRITE` | +16 | 同上 |
| **T326→T333**（判据放宽，默认 `natural`） | `PERSONA_DRIFT` | **+240** | 候选召回↑ ⇒ 人格漂移真跑发生 |
| **T326→T333** | `PERSONA_DRIFT_CANDIDATE` | **+527** | 判据可达 ⇒ identity 审计事件出现（新族） |
| **T278**（服务即时交付，默认 on） | `PRODUCE` −150 / `SERVICE_DELIVERED` +149 | **≈−1** | `PRODUCE{service}` 改由 `SERVICE_DELIVERED` 交付（族替换） |

**B. 机制归因（指纹变 ⇒ cache 全 miss ⇒ 新 LLM 答案 ⇒ 分布漂移；未做单变量隔离）**
- `OBSERVATION` +40、`METABOLISM` −19、`OFFER_CREATED`/`OFFER_EXPIRED` −17/−17、`INTEREST_CHARGED` −8、`EXCHANGE_SETTLED` +5、`LLM_CALL` +3、`INTENT_REJECTED` +2、`AGENT_DIED` +1、`CONSUME`/`LOAN_ISSUED`/`DROPPED`/`MSG_DM`/`STATE_CHANGE`/`AGENT_REVIVED`/`INIT_ENDOW`/`REVIVE_FEE_PAID` 各 −1~−5。
- ⚠️ **未做隔离**：这些小额漂移与"指纹变⇒新 LLM 答案"**机制一致**，但**本轮未设单变量对照** ⇒ 归因**属机制解释，非实测隔离**；**不排除**与 T298 的间接耦合。

**C. 与外部口径的差额（说明，不作结论）**
- 对凌晨单进程 A(`f378d5d3`, 树 `8680737`) **301,332**：差 **−8,369**；对分进程 A(`63c200a`) **292,141**：差 **+822**。
- ⇒ 差额主项 = **T298 行为变（MEMORY_FORGET −9,176）** + **T333（PERSONA_* +767）** + **T278（≈−1）** + 其余指纹/cache 漂移（B 组）。**不同 sha/口径不可直接比**（锚定书 §5.8 通则）。
- **未归因：无算术残差**（相加闭合）；**B 组仅机制归因、未隔离**（如实标注）。

## 7. 环境事实
- `available` 预检 **16.8 GB**（看 `available`，不看 `free`）；`MemoryMax=8G`；`df /` 65G free、inode 67%。
- 跑批全程逃逸（cgroup 不含 `jiuwenswarm.service`）；`available` 充裕，无 OOM/inode 异常。
- 起跑前预检：**无其他批在跑、无在飞提交、世界层安静**（详见对话记录 10:21 预检四项）。

## 8. 新 `metrics_baseline_p1.json`（摘要）
```json
{"frozen_from":"/root/t271/runs/t300/run.jsonl","log_sha256":"sha256:33b7651f…","feature_set":"v2-T300",
 "time_model":"atomic","final_state_hash":"sha256:ab38d431…","final_round":83,
 "econ_loop":{"M_final":34753,"M_min":0,"M_max":197200,"M_target":200000,"M_never_negative":true,"V":0.062665,
   "Y_mu":23614,"median_wage_mu":null,"gini_net_worth":0.736676,"tax_pool_final":2664,"n_produce":167,
   "mint_burn_balance_window":0.0,"price_cv_mean":0.0},
 "social_key":{"channels":{"DM":163,"PUBLIC":59,"GROUP":8},"comm_directed_edges":167,"comm_reciprocity":0.246269,
   "n_groups":8,"norm_adopted":19,"n_contracts":0,"n_votes":0},
 "provenance":{"run_tree_sha":"9374c3a","world_layer_sha":"8fb2263","baseline_code_sha":"fbf9c33",
   "engine_version_fingerprint":"sha256:869c1953…","provider":"openai_compat","n_agents":20,"rounds":84,"seed":42}}
```
（完整见 `v2/evidence/metrics_baseline_p1.json`；G6 golden 见 `code/obs/golden_baseline.json` 的 `n20_week_seed42`。）

## 9. 门禁
- **`obs gate`（提交后复跑；HEAD=`5b0f761`）→ GATE PASS**：
  `llm_calls_zero`✓ / `llm_judged_metric_count_zero`✓ / `money_conservation`(residual 0)✓ / `schema_conformance`✓ /
  `distribution_regression`（vs 新基线 `v2-T300`，n_events 292,963==292,963，逐族 delta 0）✓ /
  `metrics_bitwise_equal`✓（digest `0a2f36af…`）/ `census_bitwise_equal`✓（digest `79e4b2d1…`）。
  - ⚠️ **树态判读（诚实）**：`dirty_files=4`，**全部是 `code/frontend/**`**（他人未提交改动）——**世界层 CLEAN**（`git status` 中无 `code/{engine,life,freeze,config,obs,contracts,orchestration}`/`config/**`）。⇒ 该 DIRTY **改不到 obs 门禁结论**（门禁只读世界层日志/基线），故本 PASS **对世界层有效**；打戳仍按规矩标 `[DIRTY — 结论仅供参考]`。
  - 说明：**全仓库级"绝对干净"暂不可得**（前端并发编辑未提交）；如需"字面 CLEAN"的 PASS，**待 `code/frontend/**` 落地后我可再复跑一次**。
- `make ci`（工作区）→ **CI GATE: PASS**。
- `pytest tests/test_obs_*.py` → **140 passed**。

## 10. 下一轮待办（已同意，非本轮）
- **`flush` 间隔改 1–2**（+ 配套 runbook 一行：判"有无批在跑"用 `systemctl is-active 't271-*'` / `pgrep -f "orchestration run"`，**不看日志新旧**）。
- **`flush=1 vs 12` 小规模对照**（n=6/12 回合）：比 `state_hash`（证"落盘节奏不动语义"）+ 尽量验"从 flush 前缀续跑"仍成立。
- ⭐ **`T278` 消融**（用户判据「同 sha 内只变一个开关」的最小应用）：小规模跑 `service_delivered.enabled=false` **vs** `true`，比 `state_hash`——**判定 §3 第 6b 行"语义等价"是否成立**（**等价/不等价都报**）。
- **非作者核 `T349`**（sandbox-test-lead）：独立复算 §6b 逐族 delta + 验算术闭合 + 反向验证。
