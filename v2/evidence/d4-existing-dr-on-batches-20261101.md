# 勘察：**已有 3 个带 DR 字段的历史批次** —— 可零跑批**试算**，但**不能**据此判定 DR 有用

> ⚠ **标题与结论范围已于 2026-11-01 20:2x 收窄**（`repro-verifier` 指正，Leader 采纳）：
> 原题"可零跑批验证"→改为"**可零跑批试算**"。**"D4 式子算得出" ≠ "D4 能判定 DR 有用"**，后者仍须**同基座两臂**。

> 作者：TeamLeader｜2026-11-01 20:1x｜**只读普查，非判据**
> 触发：为 `T-D4-RATES`（D4 判据落地）核对"有没有开 DR 的批可用"，结果**有**。

## 1. 普查口径与结果

扫 `v2/evidence/*/run.jsonl` 共 **114 批**，按 MSG `payload` 是否出现 `dialogue_rift` / `dialogue_repair` 字段判定（这两字段**只在 `enabled=1` 时出现**，见 `code/life/agent.py`）。

| 批次 | `MSG` 条数 | 带 `dialogue_rift` | 带 `dialogue_repair` | `run.jsonl` 内容 sha·实测值（前 16） |
|---|---:|---:|---:|---|
| `emo-on-20261029` | 192 | **31** | **12** | `emo-on-20261029/run.jsonl`（本机文件·未入库，内容 sha·实测值 `2aa6c774b2e6d019…`） |
| `run_f4_on_n16r60_seed42` | 504 | **41** | **22** | `run_f4_on_n16r60_seed42/run.jsonl`（本机文件·未入库，内容 sha·实测值 `faeba580cfc5ae00…`） |
| `run_r6_treat_n16_seed42` | 683 | **139** | **0** | `run_r6_treat_n16_seed42/run.jsonl`（本机文件·未入库，内容 sha·实测值 `d42e2d921637a1e1…`） |
| 其余 111 批 | — | **0** | **0** | — |

**开关侧证据（Leader 复核后按批分别定性 —— 原写法"三批一视同仁"是错的）**：

| 批 | 开关证据 | 定性 |
|---|---|---|
| `emo-on-20261029` | `switch_proof.txt` / `env_pre_shell_on.txt` 均有 **`HITT_DIALOGUE_REPAIR=1`** | **可确认（已开）** |
| `run_f4_on_n16r60_seed42` | **无 `launch_cmd` / 无 `env` / `switch_proof`**；`meta.json` 无 DR 键 | **`CANNOT-VERIFY（未采集）`** |
| `run_r6_treat_n16_seed42` | 同上 | **`CANNOT-VERIFY（未采集）`** |

**能推的与不能推的**：
- `dialogue_rift` 字段出现**确实能证明 `enabled=1`**（字段只在开启时落）⇒ **"净上开了"可推**；
- 但**"用哪套开关配置开的（有没有同时开 `repair_ask` / `reply_priority`）"无从知道** ⇒ **跨批比较与"是不是 DR 起作用"的归因不成立**。

**基座各不相同（Leader 从 `meta.json:code_sha` 实取）**：
```
emo-on-20261029            code_sha = f19de61651e6018d…
run_f4_on_n16r60_seed42    code_sha = 6b7ae8a98694dd87…
run_r6_treat_n16_seed42    code_sha = 7b6846dce71eeb8b…
（三者互不相同，且均 ≠ cef1c58 / ≠ d87288e）
```
⇒ **`OPENINGS` / S-1 / 回退口径可能与 D9z 全不同** ⇒ **跨批、跨臂的率一律不可比**。

## 2. 这条发现改变了什么（**已按 20:2x 指正收窄**）

**原计划**：先立 D4 判据，**再决定要不要跑 91 分钟的两臂真批**。

**现在能回答的，只有一半**：
- ✅ **"D4 的式子在这类批上算得出数、且台账自洽"** —— 可零跑批验（`T-D4-RATES` 已给：登记 83 = 注销 0 + prune 34 + open 49）；
- ❌ **"开 DR 对生活气息有没有用"** —— **零跑批回答不了**：三批基座各不相同、且只有 1 批能确认开关配置 ⇒ **既不能跨批比，也无法归因**。

⇒ 正确的降级说法：**"要不要开 DR 真批"从"直接跑 91 分钟"变成"先零跑批把 D4 式子与底稿做扎实，再决定"**；**不是"不用跑了"**。

## 3. 三条必须先说清的边界（防过度解读）

1. **这三个批不是 D9z 世界线**（基座不同、`OPENINGS`/`INTRA` 设置未必相同）⇒ **不能与 D9z 的数字跨臂相减**；
2. **它们的 `MSG` 规模不同**（192 / 504 / 683）⇒ **只能"臂内条件率"，不能混算总率**（与 `_proposed-dr-run-gate.md` §2.1 一致）；
3. **`run_r6_treat` 有 139 条 rift、却 0 条 `dialogue_repair`** —— 原因未查（可能是 `repair_ask` 相关或该批口径不同）。**在算 D4-1 前必须先解释这一格**，否则会把"字段不落"误读成"没发生和解"。

## 4. 本件不做的事

- **不判定 D4**（判据未立）；
- **不声称"DR 有效"**；
- **不替代 `T-D4-RATES`** —— 本件只是告诉它"**去算哪三批**"。

## 5. ⚠ 一个必须先解决的可用性问题：**这三批的 `run.jsonl` 不在仓库里**

```
git cat-file -e origin/master:v2/evidence/emo-on-20261029/run.jsonl      → 不存在
git cat-file -e origin/master:v2/evidence/run_f4_on_n16r60_seed42/run.jsonl → 不存在
git cat-file -e origin/master:v2/evidence/run_r6_treat_n16_seed42/run.jsonl → 不存在
```
原因：`.gitignore` 第 8 行 `**/*.jsonl` 默认忽略；仓库里那些 `run.jsonl` 是**当时 `git add -f` 强制加的**，这三批没有。
体积：**17M / 53M / 88M（合计 ≈158M）** —— **不宜整批入库**。

⇒ **后果**：本件给的三个 sha **只在本机能复算**，换一台机器**无法复核**。
⇒ **处置（择一，须显式选）**：
1. **只入库切片**：把 `dialogue_rift` / `dialogue_repair` 两个字段的**最小必要列**导出成小 JSON（预计 <1MB），随 `T-D4-RATES` 口径件一起入库 —— **推荐**；
2. 全量 `git add -f`（158M，会显著推高仓库体积）；
3. 不入库，但**在任何引用处写"本机时点值·未入库"**，并接受"别人无法复算"。

**Leader 倾向 1**：D4-1/D4-2 需要的只是 `prompted` 与 rift 生命周期字段，**不需要正文**。
