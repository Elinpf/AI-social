# B. D2.2 对端选择诊断（描述性读数，**非效果结论**）

> **一句话**：在 D12-I 与 T0 两臂上，发起人对端选择的结构**逐位相同**（114 条 `(from→to)` 发起序列字节级一致）；两臂相对「均匀独立抽」的零分布都落在其外（`p=0.0000`）。但**因为两臂数据相同，这不能读作任何干预的效果**，只能读作**该生成机制自身**的可观测结构。判读用词限定在 `描述性读数 / 不可判 / 仅观察 / 未对账` 白名单内。

## B.0 输入与指纹

| 臂 | 路径 | sha256 | 行数 |
|---|---|---|---|
| D12-I | `.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl` | `72c0ca97fe6e38632f67e3b2810c65126c0d15d296d068b521dfbb45c8f5d0c4` | 117,724 |
| T0（D12-C off 基线） | `v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl` | `3c814121b5f8d4b053358c959c926f4e14b8a57bf2c6206dadc94d6695c81a74` | — |

工具（均**未跟踪、无产物**，本轮只诊断、不改造）：
- `tools/d21/partner_choice_stats.py`（122 行）
- `tools/d21/partner_choice_permtest.py`（104 行）

复算命令：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
sha256sum .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
          v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl

python3 tools/d21/partner_choice_stats.py \
  --log "D12-I=.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl" \
  --log "T0=v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl" \
  --out-json v2/evidence/d22_partner_choice/partner_choice_stats.json

python3 tools/d21/partner_choice_permtest.py --B 2000 --seed 42 \
  --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --out-json v2/evidence/d22_partner_choice/permtest_D12-I.json
python3 tools/d21/partner_choice_permtest.py --B 2000 --seed 42 \
  --log v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl \
  --out-json v2/evidence/d22_partner_choice/permtest_T0.json
```

## B.1 工具口径（先通读，再出数）

`partner_choice_stats.py` 的口径定义（文件头逐字）：
- 只统计 `MSG_DM` / `MSG_PUBLIC` / `MSG_GROUP` 且 `payload.from` 非空的事件；按 `(mono_ts, msg_uid)` 排序。
- `n_agents` = 出现在 `from/to` 里的居民数；`pairs_possible = n*(n-1)/2`（无向完全图）。
- `pair_coverage_rate` = `pairs_observed / pairs_possible`。
- `n_init` = 发起数（`turn_index==0` 且有 `to`）。
- `top1_partner_share_{max,mean}` = 单个居民最强对端占其发起数的比例（max 为截面最大值，mean 为居民均值）。
- `repeat_pair_rate` = 发起中「该无向组合此前已出现过」的比例。
- `herfindahl_mean` = 各居民对端分布 HHI 的**未加权均值**；`uniform_expected_hhi_mean` = 同 `k_i` 下 `mean(1/k_i)` 的参照（**不是判据**）。

`partner_choice_permtest.py` 的口径定义：
- 零假设 H0：每名居民每次发起都从其候选池（默认 `all_others` = 全体其他居民，池大小 `n-1=15`）**均匀独立**抽一个对端。
- 统计量 = `herfindahl_mean`；保持每人 `k_i` 不变、池内重抽 `k_i` 次，`B=2000`、`seed=42` ⇒ 零分布。
- 判读：实测落在 `[q025, q975]` 内 ⇒ 不能拒绝「均匀随机」；`p_value_one_sided_ge` = 单侧「比随机更集中」概率。

## B.2 `partner_choice_stats` 全字段（两臂）

| 字段 | D12-I | T0 | 两臂是否一致 |
|---|---|---|---|
| `n_agents` | 16 | 16 | 一致 |
| `n_init` | 114 | 114 | 一致 |
| `n_initiators` | 16 | 16 | 一致 |
| `pairs_observed` | 65 | 65 | 一致 |
| `pairs_possible` | 120 | 120 | 一致 |
| `pair_coverage_rate` | **54.17%** | **54.17%** | 一致 |
| `repeat_pair_rate` | **42.98%** | **42.98%** | 一致 |
| `top1_partner_share_max` | **66.67%** | **66.67%** | 一致 |
| `top1_partner_share_mean` | 36.49% | 36.49% | 一致 |
| `herfindahl_mean` | **0.2877** | **0.2877** | 一致 |
| `uniform_expected_hhi_mean` | 0.2522 | 0.2522 | 一致 |
| `distinct_partners_mean` | 4.5 | 4.5 | 一致 |

每个读数的六元组（以 D12-I 为例，T0 同值同口径）：

| 读数 | 数值 | 分母/口径 | 判据/定义出处 | 来源路径 | sha256 | 证据状态 |
|---|---|---|---|---|---|---|
| `pair_coverage_rate` | 54.17% | 65 / 120（无向 pair；`n=16` 完全图 120） | `partner_choice_stats.py:92` | 见 B.0 日志 | `72c0ca97…d0c4` | `描述性读数` |
| `repeat_pair_rate` | 42.98% | 49 / 114 发起（无向组合已出现过） | `:93` | 同上 | 同上 | `描述性读数` |
| `top1_partner_share_max` | 66.67% | max over 16 initiators，分母 = 该居民发起数 | `:94` | 同上 | 同上 | `描述性读数` |
| `herfindahl_mean` | 0.2877 | 16 名发起人 HHI 未加权均值 | `:96` | 同上 | 同上 | `描述性读数` |
| `uniform_expected_hhi_mean` | 0.2522 | `mean(1/k_i)`，`k_i` = 各人**不同对端数** | `:97` | 同上 | 同上 | 参照量（非判据） |
| `n_init` | 114 | `turn_index==0 且 to 非空` 的 MSG 事件数 | `:60` | 同上 | 同上 | `描述性读数` |

## B.3 置换检验（B=2000, seed=42, pool=all_others）

| 字段 | D12-I | T0 |
|---|---|---|
| `n_inits` / `n_agents` | 114 / 16 | 114 / 16 |
| `observed_hhi_mean` | **0.2877** | **0.2877** |
| `null_hhi_mean` | 0.2159 | 0.2159 |
| `null_q025` | 0.1938 | 0.1938 |
| `null_q975` | 0.2462 | 0.2462 |
| `null_sd` | 0.0137 | 0.0137 |
| `p_value_one_sided_ge` | **0.0000** | **0.0000** |
| `verdict`（工具原话） | 显著比均匀随机更集中 | 显著比均匀随机更集中 |

> 判读（**限定在白名单用词内**）：实测 `0.2877` **高于**零分布上界 `0.2462`，`p=0.0000`（2000 次模拟无一达到）⇒ **`描述性读数`：在「候选池取 n−1」这一上界假设下，实测的集中度不能由「均匀独立抽」解释**。这**不是**效果结论，也**不是**对「偏好/关系驱动」的因果断言——见 B.5 的口径缺陷。

## B.4 关键事实：两臂发起序列**逐位相同**

用脚本比对两臂的全部 `(from, to)` 发起序列（`turn_index==0 且 to 非空`，按日志顺序）：

```
identical ordered seq    : True
identical multiset       : True
per-agent dist identical : True
n_init D12-I = 114 ; n_init T0 = 114
首 5 条（两臂相同）: P004→P002, P009→P004, P010→P009, P011→P012, P012→P016
```

- 逐居民对端分布 **16/16 完全相同**（例：`P004 → {P001:4, P002:1, P007:1, P013:1, P014:1}` 两臂一致）。
- ⇒ **D12-I 的干预（对齐式降重复）对「对端选择」零位移**。这与 `code/life/planner.py::_participants` 的代码事实一致：对端 = 对 `peers` 做**种子哈希均匀抽取**（`chosen.append(_pick(f"{agent_id}|{slot_id}|{tid}|p{i}", rem))`），**不看**关系/亲疏/欠回复/地点/时段，也不看 D12-I 的去重臂。
- **因此**：B.3 的「显著更集中」是**该种子/时段结构自身的性质**，**两臂之差 = `不可判`（数据相同，差为零）**。本项**不得**写成「D12-I 改变了/没有改变对端选择的效果」，只能写成「两臂对端结构逐位相同（描述性读数）」+「共同结构偏离 iid 均匀（描述性读数）」。

## B.5 工具自身口径缺陷（原样登记，**不修工具**）

1. **`uniform_expected_hhi_mean`（0.2522）与置换零分布均值（0.2159）是两个量，不是同一个参照**（runbook §3.113 同类事故）。
   - 前者 = `mean(1/k_i)`，`k_i` = 每人的**不同对端数**（本批 `mean k = 4.5`，`1/4.5 = 0.2222`，因 Jensen 不等式 `mean(1/k) = 0.2522 ≠ 1/mean(k)`）；
   - 后者 = 保持 `k_i` 不变、从 **15 人池**重抽得到的 `E[HHI]`（小样本多项分布使 `E[HHI] > 1/15 = 0.0667`）。
   - ⇒ 二者不可互代；本文件按名字后缀并列，不做「实测 0.2877 比 0.2522 高几 pp」这类差读。

2. **候选池取 `n−1 = 15` 是上界假设**（工具 docstring 自陈）：真实 `peers` 可能更小；池越小零分布越集中 ⇒ 该检验**偏保守**（更易判「有偏好」）。故 B.3 的 `p=0.0000` 在偏保守假设下成立，结论方向不受损；但**不能**据此反推真实池大小。

3. **`herfindahl_mean` 是未加权均值**：`k_i` 极小的发起人（如 `P013` 仅 3 次发起、`P002` 5 次）其 HHI 天然偏高（`k=1` 时 HHI = 1），会抬高均值。工具未做 `k_i` 加权或最小样本过滤 ⇒ **`herfindahl_mean` 含小样本偏置**。本文件据此把该值标为 `描述性读数`、不作判据。

4. **`top1_partner_share_max = 66.67%` 与 `P013` 相关**：`P013` 发起 3 次中 2 次发同一人 ⇒ 2/3 = 66.67%；该值由**最小样本居民**主导，不代表全体普遍存在「固定搭子」。**`仅观察`**，不得作「有固定搭子」的结论。

5. **`repeat_pair_rate` 的分母是发起数（114），不是消息数**；且「此前已出现」按全局时间序判定，跨线程重复计数。口径已带后缀，不与其它重复度指标混用。

## B.6 证据状态汇总

| 项 | 状态 |
|---|---|
| B.2 全部字段 | `描述性读数`（两臂同值） |
| B.3 置换检验 | `描述性读数`（上界池假设下的偏离） |
| 两臂之差 | `不可判`（数据逐位相同，差为零） |
| 工具口径缺陷 1–5 | `仅观察 / 未对账`（原样登记，未修工具） |

> 本周期零 LLM、零跑批：两工具均为纯读 `.jsonl` 的解析器，无网络、无模型调用。
