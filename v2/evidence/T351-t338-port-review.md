# T351 · 非作者独立核：`T338` `events_this_round` 端口修（`d598f47`）

- **复核人**：sandbox-test-lead（**非作者**）｜ 落盘：`v2/evidence/T351-t338-port-review.md`
- **被核对象**：`T338`（提交 **`d598f47`**；文 `v2/evidence/T338-round-events-port.md`）—— 修 `life/settlement.events_this_round` 端口"存在但没生效"（`Ctx.kernel` 注入 `adapter`，使 `ctx.kernel.round_events` 可达）
- **自建脚本**：`v2/evidence/t351_round_events_port_verify.py`（**只读**；参考 = 独立全表扫读 `state.event_index`，不用作者单测、不改 `code/`）
- **命令**：`python3 v2/evidence/t351_round_events_port_verify.py <seed> <rounds> <n>`

---

## 1. 逐条等价（端口 vs 独立全扫）—— **N/N**

对每个 **round × type（含 `etype=None`）** 比对 `LifeState.events_this_round(kernel=adapter)` 与独立全扫（seq 序 + 记录内容）：

| 配置 | 比对组数 | 结果 |
|---|---|---|
| seed=42, rounds=12, n=4 | 528 | **N/N 全等** |
| seed=7, rounds=16, n=5 | 816 | **N/N 全等** |

## 2. `state_hash` 不变（跨版本，同 seed/rounds/n）

两树各自 `git archive`（父 `d598f47^` vs `d598f47`）跑 `build_world`+`run_round`+`state_hash`：

| 配置 | pre `d598f47^` | post `d598f47` | |
|---|---|---|---|
| seed=42, rounds=12, n=4 | `sha256:09b0be5c…c8f6398f` | 同 | **相同 ✓** |
| seed=7, rounds=16, n=5 | `sha256:b597c93d…4a0e1b87` | 同 | **相同 ✓** |

## 3. ⭐ "真生效"（HIT）与"不静默回退"

运行期**包一层** `adapter.round_events` 计 HIT，并读 `settlement.port_fallback_count()`：

| 配置 | `adapter.round_events` HIT 次数 | life 端口 FALLBACK 次数 |
|---|---|---|
| seed=42, rounds=12, n=4 | **48** | **0** |
| seed=7, rounds=16, n=5 | **67** | **0** |

⇒ **端口真命中、全程无静默回退**（正是本单原始症结："端口建了但永远回退全扫" 已消除）。

## 4. ⭐ 可观测性（真的存在且可触发）

走**无端口**路径（`LifeState(kernel=None)` / `kernel=None`）：`port_fallback_count()` **随每次调用递增**（3 次 ⇒ 计数 3），并**首次**打印 `[T338][life.settlement] WARN: round_events 端口不可用 ⇒ 回退全表扫 …`（stderr）。
⇒ **计数 + 首告警均可触发** ⇒ 若将来端口再失效，是**可观测的退化**，**非新的静默回退** ✓。

## 5. ⚠️ 反向验证（必红）

| 场景 | 作恶 | 结果 |
|---|---|---|
| 漏 1 条 | 端口对某回合少返回 1 条 | **检出**（与全扫 seq 不等） |
| 逆序 | 端口返回逆序 | **检出** |

⇒ 等价断言**非恒真**。

## 6. 时间（同进程、口径写明）

| 配置 | 端口调用数 | 端口 | 独立全扫 | 比 |
|---|---|---|---|---|
| seed=42 | 720 | 0.9ms | 51.7ms | ≈58× |

⇒ **同进程相邻调用**，比值随规模变，**非通用乘数**。（作者另报 N=50×12 cProfile 整跑 −8.4%，口径不同，各自标注。）

## 7. 与 N=50 探针（12:40 起跑、期间落地）的关系

- `T338` **逐条等价 + `state_hash` 跨版本不变** ⇒ **世界语义不变** ⇒ **该探针的世界数值/哈希读数不因 `T338` 而失真**。
- ⚠️ 但"**探针运行期间落代码、无起跑预告**"是**过程缺陷**（何时/是否作废由 release/Leader 按口径裁），**不在本核范围**；本核只回答"**它到底等不等价**"。

## 8. 结论（一句话）

**可判为无行为变（等价）**：`d598f47` 下 `events_this_round` 走端口与全扫 **逐条等价 `N/N`**（528/816）、`state_hash` 跨版本**逐位不变**、**HIT>0 且 FALLBACK=0（端口真生效）**、**可观测计数+首告警可触发**、反向验证**变红**。

*（T351 非作者独立核结束 — sandbox-test-lead，非作者）*
