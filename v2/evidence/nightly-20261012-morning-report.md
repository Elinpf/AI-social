# 夜跑早报 · 2026-10-12（首个跑批夜）—— **修正版**

> 生成：obs-stats-dev（T236 收尾）｜ 2026-10-12 21:3x ｜ 关联：T236 / T262 / T271 / T274
> ⚠️ **本文件修正 `nightly collect` 原始早报的状态误判**：原始早报把 A–D 标 `INTERRUPTED(71/84)`，
> 而**实际四批均完成 84 回合**（日志末行 `TURN_SEAL@83`、runner `rc=0`、`chain_ok/replay_parity/conservation_ok=True`）。
> 根因见 §3。原始早报：`/root/t271/runs/nightly/morning-report-20261012-night.md`。

## 1. 总览（**4 批全 SUCCESS**，真实 LLM）
| 批 | 开关 | 状态 | 事件 | LLM_CALL | 峰值RSS | 耗时 | 指纹 | state_hash |
|---|---|---|---:|---:|---:|---|---|---|
| **A 基线** | `-` | ✅ SUCCESS | **301,384** | 4794 | 383MB | 19:01→20:21 (80m) | `f1ea31a3` | `a8b6da39` |
| B 关世界导演 | `world_director.enabled=false` | ✅ SUCCESS | 301,395 | 4794 | 436MB | 19:01→20:21 | `a89546fd` | `07046536` |
| **C 关三族** | `life_v2 sleep/forgetting=false` | ✅ SUCCESS | **151,968** | 4794 | 310MB | 19:01→20:21 | `f8d3f0a8` | `dd1c7906` |
| D 开双时钟 | `wake.enabled=true` | ✅ SUCCESS | 304,607 | 4718 | 382MB | 19:01→20:31 | `adaede05` | `b7c21436` |

- 全部 `provider=openai_compat`、**无 mock 混入**；每批 `rc=0`。
- 产物：A→`v2/evidence/run_t236_canon_n20_llm.jsonl`；B/C/D→`/root/t271/runs/nightly/{B,C,D}/run.jsonl`。
- 冻结 sha `6a5f14e`；平台侧底座指纹 `sha256:f1ea31a3…`（= A 日志 `WORLD_INIT`，三方一致）。

## 2. 三条结论
1. ★ **第一条真实消融效应**：**关掉睡眠/遗忘/人格三族（C）→ 事件 301,384 → 151,968（≈ 半）**
   ⇒ **T244 三族贡献约一半事件量**（"默认开不免费"的直接证据）。
2. **B ≈ A**（301,395 vs 301,384）：世界导演 `enabled=true` 在**默认剂量**下**几乎没多产事件** → **值得单独核实"世界导演是否真的产生了预期宏观群体事件"**（若否，T255 "默认开"实际接近 inert）。
3. **80–90 min 跑满 84 回合**（远快于预估 2.5–3.3h）。**成因【未验证】**：疑 **端点今晚更快 + T264 可见性索引**叠加；**未做单变量隔离，不作结论**。

## 3. 缺口/偏差（诚实）
- **① `collect` 状态误判**（A–D 标 INTERRUPTED）：**根因 = 用"心跳最后一行的 round"判是否达目标**，而 10min 心跳间隔内批已完成 → 读到的 round 滞后（20:11=71）→ 误判。**应以"日志末行 round==target"或 runner `rc=0`/`RUN_END` 为准**。**报 release-engineer 修。**
- **② 流水线一次起了 4 批**（未走"A 优先 + 1 路探针→2 路"）：与排班口径不符（结果无损）。
- **③ `meta.ended_at/fingerprint` 依赖 `collect` 回填**（runner 退出不写）——预期化即可。

## 4. T262 周期 flush 证据（不删）
- 真实非计划死亡（memguard 15:52 重启平台）下：`archive/run_t236_canon_n20_llm.partial-r35.jsonl`（74,457 行 / 0 解析失败 / `TURN_SEAL@35`；sha256 `adeb5e36…`）+ `archive/t236_flush_curve.txt`。
- 本轮成功跑批：`A/heartbeat.tsv` 15.8KB(r0)→41.2MB(r35)→110.7MB(r71)→140.9MB(EXIT)，**每 12 回合原子落盘、单调增长**。

## 5. 环境事实
- 平台 **18:23:28 因 memguard 重启一次**（peak 8.9G）；`anon` 现 4.22G；**swap 3.5G/3.8G**。
- **跑批全程逃逸**（cgroup `/system.slice/t271-<B>.service`，不含 `jiuwenswarm.service`）→ 18:23 平台重启**未杀批次** ✓。

## 6. 基线重冻（T236）
见 `v2/evidence/t236-refreeze.md`：golden `n20_week_seed42` 重冻（128,564 → **301,384** 事件，feature_set `v2-T236`）+ `metrics_baseline_p1.json` 重写；旧基线归档（`archive/*_pre_t236.json`，带时效标注）。
