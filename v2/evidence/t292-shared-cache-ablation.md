# T292 · 共享 freeze_cache 干净消融（A/B/C/D）—— 一页对照表

> 作者：obs-stats-dev ｜ 2026-10-13 凌晨 ｜ 关联：T289 / T271 / T274 / T276
> 目的：用**共享 `freeze_cache`** 重跑消融，得**干净对照**（同 prompt 同答案 ⇒ 差异只来自 config/代码）。
> 硬约束遵守：**未碰 `code/{engine,life,freeze,config,obs,contracts,orchestration}`**。跑批托管 = T271 transient（逃逸平台 cgroup）。

## 0. 结论（先给）
> **⚠️ 与本"冻结基线"的关系（读前必看）**：本轮 A 的指纹 = **`f378d5d3`**，而 `v2/evidence/t236-refreeze.md` 的冻结基线 A 指纹 = **`f1ea31a3`** ⇒ **两个 A 的事件数不同（301,332 vs 301,384）不是行为差异，是"22:22 新增 `time.json` 进指纹 ⇒ cache 全 miss ⇒ 新 LLM 答案"**。**两者不可直接比；本轮表内 A 只作本轮 B/C/D 的内部基准。** 详见 §3。

- ★ **`B−A = −2`**（301,330 − 301,332），**恰好 = 世界导演的 2 个事件**（`WORLD_DIRECTIVE=1`+`WORLD_GROUP_EVENT=1`）⇒ **关掉世界导演后世界逐项一致** ⇒ **世界导演默认剂量 = 纯旁白（`_NOOP_TYPES`），无下游行为影响 ⇒ D3 未达成**（与 T289 互证）。
- **今晚"B 反而比 A 多 11"纯粹是跨批分叉噪声**（每批独立 `freeze_cache`+真 LLM）—— 共享 cache 后该噪声消失。
- **C 是"零结果"（机制缺口）**：`cfg['life_v2']` override **够不到**（life **直读盘** `config/life_v2.json`）⇒ **C ≡ A（100% 缓存、同 `state_hash`）**；**不代表"三族无效果"**（今晚 `file` 模式 C 的"事件减半"仍成立）。⇒ **T297b 的理由**。
- **D（wake on）是真行为变更**：**+3120 事件**（`MEMORY_FORGET +2109`、`WAKE +1294`、`RELATION_CHANGE +912`…）+ `state_hash` 变；**88.6% 缓存 ⇒ 半干净**（行为分叉 ⇒ 部分 miss）。

## 1. 机制确认（带证据）
- `freeze/llm_client.py::make_cache_key` = `digest({cache_schema, kind, engine_version, prompt_hash, model, tier, params})` ⇒ **键必含 `engine_version`**。
- ⇒ **改 config 文件 + 共享 cache = 0 命中**（文件指纹变 → 键变）；**`config-dict` 覆盖（不改文件）= 命中**（同 `engine_version`）。
- 小验证（N=4×6 real）：A `cached=6/47`；**B `cached=47/47=100%`**、两批指纹相同 `23658bf8` ✓。
- **注意（本 run 口径）**：脚本 `default_config()` **每批重读盘** + `engine_version` 每次 `run_e2e` 内重算 ⇒ **`config/*.json` 必须在全窗口逐字节一致**（本次已冻结一致）。

## 2. 对照表（**共享 side_root `/tmp/t292/shared`**；指纹全 `f378d5d3`）
| 批 | 开关（**来自 override/meta，不在指纹**） | 事件 | LLM调用 | **cached** | 耗时 | WD | WGE | 判定 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| **A** 基线 | `-` | **301,332** | 4797 | 3120(65%*批内去重*) | 3937s | 1 | 1 | — |
| **B** 导演 off | `world_director.enabled=false` | **301,330** | 4797 | **4777 (99.6%)** | 503s | 0 | 0 | ✅ **干净** |
| **C** 三族 off | `life_v2 sleep/forgetting=false` | **301,332** | 4797 | **4797 (100%)** | 472s | 1 | 1 | ⚠️ **零结果**（override 无效） |
| **D** wake on | `policy.wake.enabled=true` | **304,452** | 4718 | 4180 (88.6%) | 2815s | 1 | 1 | ◐ **半干净**（行为变更） |

**按类型差值**：
- **B−A**：仅 `WORLD_DIRECTIVE −1`、`WORLD_GROUP_EVENT −1` ⇒ **总 −2，别处全 0**。
- **D−A（+3120）**：`MEMORY_FORGET +2109` · `WAKE +1294` · `RELATION_CHANGE +912` · `IDLE +84` · … ；减项 `MEMORY_RETRIEVE −415` · `OFFER_ACCEPTED −167` · `DROPPED −151` · `LLM_CALL −79` · `OFFER_CREATED −84` · `EXCHANGE_SETTLED −18`。
- **C−A**：**全 0**（同 `state_hash=39fe3920`）⇒ C 真的等于 A。
- `state_hash`：A=C=`39fe3920` · B=`19899d12`（差仅 director）· D=`51555fe0`。

## 3. ⚠️ A 漂移说明（**必须显式标注**）
**本轮 A(`f378d5d3`) = 301,332 ≠ 今晚冻结基线 A(`f1ea31a3`) = 301,384（差 52）** —— **不是行为变了**，而是 **22:22 新增 default-off 键 `config/time.json` 进指纹 ⇒ cache 全 miss ⇒ 新 LLM 答案**。
⇒ **本轮的 A 与今晚冻结基线 `t236_refreeze` 的 A 不可直接比；原因=指纹变**（实证 §5.8 通则）。

## 4. 诚实与边界
- **每批判定**：B **干净**（99.6% 命中）；C **零结果**（override 够不到，非物理事实）；D **半干净**（88.6% 命中，行为变更必分叉）。
- **provenance**：本批用**主树 code**（非 /tmp 副本）；跑批期间 `config/*.json` 未变（冻结）；**代码 = HEAD `8680737` + kernel T287 未提交改动（22:22，后已 stash）⇒ 出处非某提交 sha**（内部对照成立）。
- **环境事件**：`t271-t292` 曾于 22:28:21 **被外部 `systemctl stop` 误停**（release-engineer 自报），已 22:28 重启续跑（A 从头，cache `f378d5d3` 未复用首跑）—— **记环境事件，非批内错误**。
- **C 修复**：需 life 暴露注入 hook（`T297b`）。
- **⚠️ 装置前提（T298 教训 @2026-10-13）**：本 run **同一进程内连跑 A/B/C/D**（为共享 `freeze_cache`）。Leader 已立规：**同进程连续 `run_e2e` 可能引入模块级状态污染 ⇒ 假分叉** ⇒ 本 report 记为**装置前提**。
  - **复核未改本结论**：B **命中 99.6%**、`B−A` **恰为 2 个 noop**、**C≡A（同 `state_hash`）**、D 差异伴随 `state_hash` 变 ⇒ **自洽、未见假分叉**（真有污染 B 会偏更多）。但**严格复现建议【分进程 + 共享 `cache_dir`】**（缓存落盘 ⇒ 分进程同样可共享；`/tmp/t292/shared` 满足）。
- **下晚**：`side`（共享）+ `switch_mode=override`（B/D 干净）经 `tools/t271` 可复现。

## 5. 复现
```bash
# 本 run：同 side_root、config-dict 覆盖；A 先填 cache，B/C/D 复用
python3 /tmp/t292_shared_run.py     # 结果 /tmp/t292/t292_shared_results.json
```
**下晚（经流水线，一键复现 B/D 干净对照）**：批次表用 **`side` 填同一路径** + **`switch_mode=override`**（开关作 runtime cfg 覆盖，不改副本文件、保 `cache_key` 命中）：
```bash
# tools/t271/batches.example.tsv: B/D 行 side=<同一路径>, switch_mode=override
R=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 "$R/tools/t271/nightly.py" start --batches "$R/tools/t271/batches.example.tsv" \
  --sha "$(git -C "$R" rev-parse HEAD)" --env-file "$R/code/.env.local" --heartbeat 600
# ⚠️ C(life_v2) 仍需 life 注入 hook（T297b）才能 override；否则只能 file 模式=半干净。
```
