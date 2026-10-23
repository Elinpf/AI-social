# `tools/d12h/shape_gate.py` —— D12-I 形态闸（纯只读）

- 文件 sha256：`f7740b6d4c3052b7577b5bf9d5c10c18039d2a87a1e2afb0697fb49691d70ea3`
- 用途：**1/3（约 20 轮）与收尾各跑一次**，一命令出四项形态指标 + 与 T5 的漂移 + 越界判定；
  F1/F2 越界即停跑、判「作废（形态漂移，非单变量）」（D12-H 用 6,073 次调用换来的教训）。

## 用法

```bash
# 收尾（全 run）
python3 tools/d12h/shape_gate.py --log <run.jsonl> --code-dir code
# 1/3 处（只看前 20 轮）
python3 tools/d12h/shape_gate.py --log <run.jsonl> --rounds 20 --code-dir code
```

退出码：**0** 全过 / **1** 有越界 / **2** 无法判定（日志无 MSG，或取显示名失败）。

## 口径（不自造）

| 指标 | 来源 |
|---|---|
| `paren_rate` / `len_p50` / `len_p50_excl` / `id_leak_rate` / `dup_exact_rate` | **直接复用 `tools/d9/arm_state_check.py::metrics`**；运行时打印 `impl_sha256 = 9e11701f60fcddef…`（源码 sha，非文件 sha） |
| `paren_head_rate` | 正文以 `（`/`(` 开头（D12-H 实测 0.20%，与 `paren_rate` 相等 ⇒ 旁白全在开头位） |
| `addr_head_rate`（**精确，判据用**） | 正文以**显示名**开头（名字取自跑批树 `build_world(seed,n)` 的 `_peer_names`），允许 0–2 个称谓字（哥/姐/啊…）再接 `，,：:` |
| `addr_head_upper_rate`（**仅参照**） | `^[汉字]{1,4}[，,：:]` 正则上界；会把「这块榫头，」也算称呼，**不作判据** |

查找 `arm_state_check.py` 的顺序：`$SHAPE_GATE_METRICS_SRC` → 本 worktree → **主 checkout**
（worktree 里没有 `tools/d9/` 时自动回退；找不到就报错，**不静默换自造口径**）。

## 闸门（D12-I 预登记 §2，可用参数覆盖）

| 闸 | 指标 | T5 基线 | 容许 | 判定 |
|---|---|---|---|---|
| **F1** | `paren_rate` | 0.5784 | 漂移 ≤ 5pp（绝对） | `--f1-pp` |
| **F2** | `addr_head_rate` | 0.41 | 漂移 ≤ 15pp（绝对） | `--f2-pp` |
| **F3** | `len_p50` | 53 | 漂移 ≤ 10%（相对） | `--f3-rel` |

## 在 D12-H 真跑日志上的实测（证明闸在工作）

| 口径 | n_bodies | `paren_rate` | F1 | `addr_head_rate` | F2 | `len_p50` | F3 | rc |
|---|---|---|---|---|---|---|---|---|
| 全 run（rounds 0–59） | 510 | **0.20%**（−57.64pp） | **FAIL** | **87.65%**（+46.65pp） | **FAIL** | 56.0（+5.66%） | PASS | **1** |
| **前 20 轮（1/3）** | **174** | **0.57%**（−57.27pp） | **FAIL** | **89.66%**（+48.66pp） | **FAIL** | 55.0（+3.77%） | PASS | **1** |

⇒ **1/3 处就能判死**（省下 2/3 的 6,073 次调用）——这正是本工具的存在理由。
原始 JSON：`shape_gate_d12h_full.json` / `shape_gate_d12h_first20.json`（本目录）。

> 口径差异如实标注：本工具的**精确** `addr_head_rate` 全 run 为 **87.65%**，Leader 按对端显示名匹配得到的
> **90.98%**（差 3.34pp，我的匹配更保守：要求名字在第 0 位、后缀 ≤2 字）。**两者结论相同（均远超 T5 41%、F2 FAIL）**；
> 引用时以 Leader 口径为准，本值作辅证。

## 明确未做
1. 未参与任何跑批；纯只读解析 `run.jsonl`。
2. 未改任何阈值/预登记；T5 基线可参数覆盖但不设默认改写。

---

## 附：三点核模式 `--points 20,30,60`（本轮新增）

```bash
python3 tools/d12h/shape_gate.py --log <run.jsonl> --code-dir code --points 20,30,60 [--out-json x.json]
```

- **为什么默认该是三点核**：D12-H 的漂移是"提示词一改，形态立刻崩"（前 20 轮即 F1 −57pp，1/3 能抓）；
  D12-I 的漂移是**跃变式**（第 20–29 轮才起跳），**1/3 处看不到** ⇒ 必须有中点。
- 输出：三个时点的**同口径四项**（`paren_rate` / `paren_head_rate` / `addr_head_strict` / `len_p50_excl`）+ 各自 F1/F2/F3 判定；
  另给**分段（块级）读数**（段 = `[上一时点, 本时点)`）与**段间 Δparen / Δaddr**；
- **跃变标记**：`|Δparen| > --jump-pp`（默认 10pp）或 `|Δaddr| > --jump-pp` ⇒ `jump=true`（**提示，不参与 rc**）；
- **rc 语义**：任一时点 F1/F2/F3 越界 ⇒ `1`；全部通过但有跃变标记 ⇒ **仍 `0`**（"提示"与"否决"分开）。

D12-I 实测（`run_d12i_aligned_n16r60_seed42`）：
```
  时点            n    paren    F1  addr_strict    F2  len_excl    F3
  <20         174   60.92%  PASS       26.44%  PASS      56.0  PASS
  <30         246   67.89%  FAIL       23.17%  FAIL      59.0  FAIL
  <60         510   72.35%  FAIL       22.75%  FAIL      55.0  PASS
  分段：[0,20) 174条 60.92% / [20,30) 72条 84.72% / [30,60) 264条 76.52%
  段间跃变（±10pp）：[0,20)→[20,30) Δparen=+23.80pp Δaddr=-11.16pp ⇒ JUMP（提示，不参与 rc）
  rc=1（因 <30/<60 越界）
```
⇒ **段间跃变把 D12-I 的"+24.5pp 起跳"机读化了**（累积点差 `<20→<30` 只有 +6.97pp，会被稀释掉 ——
所以判"跃变"必须用**块级**，不能用累积点差）。

## 附：`argmin_unique` 与 `not_all_equal`（口径并列）

两个数**不是一回事**，同名混用会把 94.1% 说成 98.6%：

| 名字 | 定义 | `scores=[1,1,2]` |
|---|---|---|
| `argmin_unique` | **最小值的索引唯一**（判据用这个） | **False**（最小值 1 在 0、1 两处） |
| `not_all_equal` | **分数不全同**（只说明有区分度） | **True** |

D12-I 实测：`argmin_unique 480/510 = 94.1%`、`not_all_equal 503/510 = 98.6%`（两者差 4.5pp，全在"最小同分"那部分）。
