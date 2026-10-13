# T355 · 基线重冻（第四轮）—— 含 `D3` 口径② + `D11` 期② 的树 + 2×2 消融矩阵

> 作者：obs-stats-dev ｜ 2026-10-13（D10 白昼跑批）｜ 关联：T353 / T354 / T361 / T328③(1ffd7eb) / T372 / T371
> **读主树（`tree=main`）；记录用 `HEAD=1d3af8c`；计算基线 obs 代码 sha = 提交时 HEAD；世界层 CLEAN。**
> 运行窗口：2026-10-13 16:29:27 → **17:44 写完 / 17:49 `batch exited rc=0`**（**≈4.3h**）；`t271-t355.service` transient 逃逸、`ExecMainStatus=0`。

## 1. 新基线身份（多 sha 分开记）
| 项 | 值 |
|---|---|
| 源日志 | `/root/t271/runs/t355/run.jsonl` |
| **① 跑批所读树 sha** | **`1d3af8c`**（`tree=main`；世界层最后改动含 `1ffd7eb`） |
| **② 计算基线 obs 代码 sha** | **`be9441b`**（重冻时 HEAD；见 `metrics_baseline_p1.json::provenance.baseline_code_sha`） |
| **`engine_version` 指纹** | **`sha256:a871e36c44acbda9ac4aadeebe829a821219b2fec22642ea2b372f6ec88f3b1c`** |
| 日志 sha256 | `sha256:bee77237e7c2fa3a41ae7613d2ef3e4bf989c1b4f57b831fc29edc714dec3c36` |
| N / rounds / seed | 20 / 84 / 42 ｜ `provider=openai_compat`（无 mock 混入）｜ `flush=2` |
| 事件数 | **292,255**（T300 为 292,963；**Δ=−708**，见 §5） |
| chain / replay / conservation | 全 **True** ｜ 末回合 `TURN_SEAL round=83` ⇒ 84 回合跑满 |
| **终态 `state_hash`** | **`sha256:b7cab88ed3f54bda4a75ae14e8f6aaca2e7c88a788daf23ecf4995efb551ac2c`** |
| **`time_model`** | **`atomic`**（`WORLD_INIT.payload.time_model`） |
| **`world_model`** | **`effective`**（⚠️ **推定**：无日志戳；按 T352 口径② 默认开推定；待引擎落戳后复核） |

## 2. 旧基线归档（**不删、带时效标注**）
- `v2/evidence/archive/golden_baseline_pre_t355.json` —— 旧 `golden_baseline.json`（`n20` = 292,963、feature_set `v2-T300`）。**有效期：截至本轮重冻前；已被取代。**
- `v2/evidence/archive/metrics_baseline_p1_pre_t355.json` —— 旧 `metrics_baseline_p1.json`（`v2-T300`）。**同上，已被取代。**
- 更早 `*_pre_t236` / `*_pre_t104` 保持原样（**已过期**）。
- 新 `golden_baseline.json`：`n20_week_seed42` = **n_events 292,255**、feature_set **`v2-T355`**、`time_model=atomic`、`world_model=effective`、`final_state_hash=b7cab88e…`、`provenance{run_tree_sha, baseline_code_sha, engine_version_fingerprint}`。

## 3. 变更清单（**四档**，以锚定书 §7 `v1.3.47` 为准；自 T300 基线 `v2-T300` 以来）
| # | 提交/任务 | 内容 | 动 config/指纹 | 分类 | 佐证/待核 |
|---|---|---|---|---|---|
| 1 | `T353`（D3 口径②） | 世界层参数**真影响行为**（默认开；`world_director.propagate.enabled` 默认 true） | **是** | **【行为变】+【指纹变】** | 由 §6 矩阵/`T366` 隔离；WIP |
| 2 | `T354`（D11 期②） | tick 内有时间：`current_activity` 真被 life 消费（默认开；`time.ongoing.enabled` 默认 true） | **是** | **【行为变】+【指纹变】** | `T363`：`on vs off` len 50384/50202、`state_hash` 不同、族级 delta 非空（`MEMORY_WRITE`/`OBSERVATION` +71）⇒ **真被消费** |
| 3 | `perceive` 修复（`1ffd7eb`） | `_load_time_flags(config=None)` 优先读 cfg 并透传（消除 `mini/inline` 直读盘的方向不对称） | 否 | **【无行为变】**（反向验证判定） | 由 `kernel` 反向验证 + `T345`系；**登记两版本（修复前/后）见前置清单** |
| 4 | `T361` 等 | 见各单 | 否 | **【无行为变（测试/装置）】** | verify 绿 |
| ⚠️ | **`T372`（双计缺陷，未修）** | `apply_world_director` 双发 `WORLD_DIRECTIVE`+`WORLD_GROUP_EVENT`（同 `directive_id`）⇒ `world_params` 逐条累加 ⇒ **同指令计两次** ⇒ `activity_weight`/`resource_factor_bp`/`market_scarcity_bp` **×2 虚高** | 否（既有缺陷） | **登记为【已知偏差】** | ⭐ **本基线忠实反映当前行为，但世界层强度是 2× 口径**；**别拿绝对值当「正确强度」**；`T372` 修复后世界层强度**减半**（行为变）⇒ 第五次统一重冻 |

> ⚠️ **provenance 声明**：**本基线仅在含 `T372` 缺陷的树上可复现**（该缺陷修复后须重冻）。
> **epoch**：`T372`+`T367`+`T371` 同批、逐个可分离、**全部落地后第五次统一重冻**（不单独为双计修复冻结；`T355` 基线即其 pre-baseline）。

## 4. 字节一致测试（H2，命令 + diff）
**动因**：重冻脚本给基线附加元数据字段（`time_model`/`world_model`/`final_state_hash`/`provenance`）会改 JSON 结构 ⇒ 必须证明**除新增字段外数值逐字节不变**。
- 方法：用**当前代码**对**旧 log**（`run_t300`）重算基线，与 **`archive/golden_baseline_pre_t355.json`** 的 `n20` 逐字段比。
- 命令：
  ```
  python3 - <<'PY'
  import json,sys,difflib; sys.path.insert(0,"code")
  from obs.golden import compute_baseline
  recs=[json.loads(l) for l in open("/root/t271/runs/t300/run.jsonl",encoding="utf-8")]
  new=compute_baseline(recs,"n20_week_seed42",feature_set="v2-T300")
  old=json.load(open("v2/evidence/archive/golden_baseline_pre_t355.json"))["n20_week_seed42"]
  print("ADDED",sorted(set(new)-set(old)),"REMOVED",sorted(set(old)-set(new)),
        "CHANGED",sorted(k for k in set(new)&set(old) if new[k]!=old[k]))
  PY
  ```
- **结果**：`ADDED=[] REMOVED=['final_state_hash','provenance'] CHANGED=[]`；**两次调用字节相等** `BYTE_EQUAL_TWO_CALLS=True`。
  ⇒ **除"重冻脚本附加的元数据字段（`final_state_hash`/`provenance`）"外，数值逐字节不变**（`REMOVED` 即这两个脚本附加字段，recompute 不产出它们）。
- `pytest tests/test_obs_*.py` → 140 passed（含 `test_obs_golden_time_model`）。

## 5. 事件数 −708 逐项归因（vs T300；⚠️ 跨-epoch 差：含 T353/T354 行为变 + 指纹冷缓存漂移）
**算数闭合**：逐族相加 **=−708，无残差**。
| 族 | T300 | T355 | Δ | 归因（机制） |
|---|---:|---:|---:|---|
| `MEMORY_FORGET` | 134,367 | 133,788 | **−579** | 主导；T353/T354 行为变 + 冷缓存新答案 |
| `RELATION_CHANGE` | 16,725 | 16,669 | −56 | 同上（关系由感知/活动驱动） |
| `LLM_CALL` | 4,797 | 4,757 | −40 | `importance` −37 / `judge` −3（见 §5b） |
| `MEMORY_WRITE` | 58,547 | 58,539 | −8 | 机制漂移 |
| `OBSERVATION` | 58,252 | 58,244 | −8 | 机制漂移 |
| `PERSONA_DRIFT_CANDIDATE` | 527 | 519 | −8 | 机制漂移 |
| `PERSONA_DRIFT` | 240 | 234 | −6 | 机制漂移 |
| `LLM_JUDGMENT` | 1,010 | 1,007 | −3 | `judge` −3 |

- **可隔离 vs 机制**：本轮为**跨-epoch 对照（T300 树 → T355 树）**，含 **T353/T354 行为变 + 指纹变（冷缓存）** 两类因 ⇒ **上表多为机制归因**；**严格隔离需 §6 的 2×2 矩阵 / T366**。**未归因：无算术残差**。

### 5b. ⭐ `LLM_CALL` 逐 purpose 归因（回应"疑似 2×"）
| purpose | T300 | T355 | Δ |
|---|---:|---:|---:|
| `importance` | 3,234 | 3,197 | −37 |
| `judge` | 1,010 | 1,007 | −3 |
| `dialogue` | 270 | 270 | 0 |
| `reflect` | 140 | 140 | 0 |
| `negotiation` | 103 | 103 | 0 |
| `describe` | 20 | 20 | 0 |
| `plan` | 20 | 20 | 0 |
| **合计** | **4,797** | **4,757** | **−40** |
- ⭐ **结论（更正早期"≈2×"警报）**：**最终 `LLM_CALL` = 4,757 / 84 ≈ 56.6/回合 ≈ T300 的 57/回合** ⇒ **不是 2×、不是性能回归**。
  **早期"113/回合"是启动期集中的假象**（前 6 回合 `judge`/`importance` 更密）——**正是"不要用前几回合线性外推"的又一例**。
  ⇒ 对"50+ 人口规模决策"：**无此路径带来的调用爆炸**（当前端点/成本口径不变）。

## 6. 2×2 消融矩阵（`time.ongoing` × `world_director.propagate`，含 X1）
- 设计：**同 sha、同 side、config-dict override**（`run_override`），四格 `A_off_off / B_off_on / C_on_off / D_on_on`；判据 `D−C−B+A0`（可加）或 X1 交互（节日提升"进行中活动"）。
- ⚠️ **门（leader 写死）**：**不可分离 ⇒ 退回"一期一冻"**（如实上报）。
- 状态：**待跑**（leader 口令：跑完主批先回报、再起矩阵）。结果将补入本节：`{n_events/关键族/state_hash}` ×4 + 分离性结论 + X1。

## 7. 装置/环境事实（如实披露）
- 托管 `t271-t355.service`（cgroup `/system.slice/t271-t355.service`，**逃逸** `jiuwenswarm.service`）；`MemoryHigh=6G`/`MemoryMax=8G`；凭证仅 `EnvironmentFile=code/.env.local`。
- **起跑前无并行重活**（事实）：前序门禁末写 16:29:04、T355 起跑痕迹 16:29:27（间隔 23s，且门禁在副本内跑）。
- **起跑时另有一组短时无头渲染（playwright chrome）**在跑（本地渲染，与 T355 端点/IO 资源面不同）——如实披露、无推测。
- **本次不与任何真 LLM 任务并行** ✓。
- ⚠️ **耗时读数**：`≈4.3h`（16:29→17:49）；**无其它真 LLM 并行**，读数干净。
- ⚠️ **上报延迟**：17:49 结束，19:40 才被 leader 发现 ⇒ **全员空等 1h50m**（owner 漏了"`batch exited rc=0` 即报"），已按新机制记账。

## 8. 新 `metrics_baseline_p1.json`（摘要）
```json
{"frozen_from":"/root/t271/runs/t355/run.jsonl","log_sha256":"sha256:bee77237…","feature_set":"v2-T355",
 "time_model":"atomic","world_model":"effective","final_state_hash":"sha256:b7cab88e…","final_round":83,
 "econ_loop":{"M_final":34753,"M_min":0,"M_max":197200,"M_target":200000,"M_never_negative":true,"V":0.062665,
   "Y_mu":23614,"median_wage_mu":null,"gini_net_worth":0.736676,"tax_pool_final":2664,"n_produce":167,
   "mint_burn_balance_window":0.0,"price_cv_mean":0.0},
 "social_key":{"channels":{"DM":163,"PUBLIC":59,"GROUP":8},"comm_directed_edges":167,"comm_reciprocity":0.246269,
   "n_groups":8,"norm_adopted":19,"n_contracts":0,"n_votes":0},
 "provenance":{"run_tree_sha":"1d3af8c","baseline_code_sha":"be9441b",
   "engine_version_fingerprint":"sha256:a871e36c…","provider":"openai_compat","n_agents":20,"rounds":84,"seed":42,"flush_every":2}}
```
（完整见 `v2/evidence/metrics_baseline_p1.json`；G6 golden 见 `code/obs/golden_baseline.json` 的 `n20_week_seed42`。）

## 9. 门禁
- `python -m obs gate --log /root/t271/runs/t355/run.jsonl --baseline auto` → 见回报（提交后复跑，附 sha）。
- `pytest tests/test_obs_*.py` → 140 passed。
