# T310 · T292 装置确认性复跑（分进程 + 共享 cache）

> 作者：obs-stats-dev ｜ 2026-10-13 02:1x ｜ 关联：T292 / T298 / T287
> 目的：按新 Harness 规矩（**对比须分进程**），用**分进程 + 共享同一 `cache_dir`** 复跑 `T292` 的 A/B/D，
> 确认 `B−A` 是否仍恰 = 2 个 `_NOOP_TYPES`、`D−A` 类型差异是否复现。**不覆盖 `t292-shared-cache-ablation.md`。**

## 0. 结论（先给）
- ✅ **`B−A = −2` 复现**（292,139 − 292,141 = −2，恰 `WORLD_DIRECTIVE −1` + `WORLD_GROUP_EVENT −1`）⇒ **"世界导演默认=纯旁白、零下游影响（D3 未达成）"在【分进程】下同样成立** ⇒ **装置（同进程 vs 分进程）未影响该结论**。
- ✅ **`D−A` 类型差异同型复现**（`MEMORY_FORGET`/`WAKE`/`RELATION_CHANGE` ↑，`MEMORY_RETRIEVE`/`OFFER_ACCEPTED`/`EXCHANGE_SETTLED` ↓，`state_hash` 变）⇒ **D9 双时钟=真行为变更** 亦复现。
- ⇒ **原 T292 结论加固；装置问题判为"未影响结论"**（无需再做"同树只换装置"的隔离实验——那是"若不重现"才需要）。

## 1. 装置前提（**必须写清，否则复算不出**）
- **分进程**：`bash /tmp/t310_run.sh` 内 **A/B/D 各一次独立 `python3 /tmp/t310_one.py`**（一个进程只跑一批）。
- **共享 cache**：`side_root=/tmp/t292/shared`（复用 T292 的 `freeze_cache`，**落盘 ⇒ 分进程也能命中**）。
- **托管**：T271 transient unit `t271-t310`（cgroup `/system.slice/t271-t310.service`，**逃逸** `jiuwenswarm.service`）+ `MemoryMax=10G`；预检 `available=20Gi`。
- **开关**：`config-dict override`（B=`world_director.enabled=false`，D=`policy.wake.enabled=true`）；**不改文件 ⇒ 指纹不变**。
- **树**：**当前 HEAD `63c200a`**（含 `T298` `7f16c80`/`801c880`/`8d4c8b9` + `T287` `76de474`），**≠ T292 的树 `8680737`** ⇒ 见 §3。
- **指纹**：`sha256:f378d5d3…`（与 T292 同）⇒ cache 可复用（实测 A/B **99.6% 命中**）。
- **并发**（按 Harness 规矩记录）：本 run 期间**同一时刻另有 `T304`（art，repro_resume_cut）与 `T314`（kernel，resume-guard）在跑**，**共享同一 LLM 端点与 CPU**。⇒ 本 run 由 **cache 主导（命中 99.6%）**，**未受争用影响**（B−A 干净复现）；但**装置前提含"并发"这一项**，复算须知。

## 2. 逐值对照（T292 同进程 vs T310 分进程）
| 批 | T292（同进程，树 8680737+） | **T310（分进程，树 63c200a）** | 复现? |
|---|---|---|---|
| A 事件 / cached | 301,332 / 3120 | **292,141 / 4777(99.6%)** | 树不同→事件不同 |
| **B−A** | **−2**（WD−1,WGE−1） | **−2**（WD−1,WGE−1） | ✅ **完全复现** |
| **D−A** 总 | **+3,120** | **+2,994** | ✅ 同型 |
| D−A 主项 | `MEMORY_FORGET+2109`·`WAKE+1294`·`RELATION_CHANGE+912`·`MEMORY_RETRIEVE−415`·`IDLE+84`·`OFFER_ACCEPTED−167`·`EXCHANGE_SETTLED−18` | `MEMORY_FORGET+1983`·`WAKE+1294`·`RELATION_CHANGE+912`·`MEMORY_RETRIEVE−415`·`IDLE+84`·`OFFER_ACCEPTED−167`·`OFFER_EXPIRED−71` | ✅ 同型（`MEMORY_FORGET` 量级略小） |
| C | 301,332（≡A，override 无效） | 未跑（C 结论与装置无关；override 无效是机制缺口） | — |
| A 的 `state_hash` | `39fe3920` | `fdfa2cb9`（树不同） | 因树而异 |

## 3. 差异来源（**装置 or 树？**）
- **`B−A`：−2 在两处都成立** ⇒ **装置无影响**（这是 T310 要判的那条）。
- **A 绝对值**：T292 `301,332` vs T310 `292,141`（差 −9,191）—— **来自【树前进】**（`T298` 改了 life 记忆/一次性路径行为），**非装置**；佐证：两处 A 的 LLM **cache 命中率都 99.6%**（同 LLM 答案），差异落在 `MEMORY_*` 族（T298 直接改的）。
- **`D−A` 的 `MEMORY_FORGET` 2109→1983**：同源于 T298 对记忆族的影响，**非装置**。

## 4. 一句话验收
**【装置是否曾影响 T292 结论？】否** —— 分进程复跑下 **`B−A` 仍恰 = 2 个 noop**、`D−A` 类型差异同型；观测到的差异（A 绝对值）**来自树前进（T298），非装置**。

## 5. 复现
```bash
# 分进程：A/B/D 各一次独立 python（共享 /tmp/t292/shared 的 cache）
bash /tmp/t310_run.sh     # 输出：/tmp/t310/run_{A,B,D}.jsonl + host.log 的 SEG 行
```
