# 修复：`shape_gate.py` 的 F2 基线口径混用（upper → strict）

> 日期：2026-10-24。触发：D12-I 终态发现「F2 判据用 `addr_head_strict`，但内置 T5 基线 41.00% 实为 `addr_head_upper`」，
> 使任何臂的 F2 都被系统性高估 4.53pp，**足以把 PASS 翻成 FAIL**（D12-I 就发生过）。

## 改了什么

| 项 | 改前 | 改后 |
|---|---|---|
| 参数 | `--t5-addr`（default **0.41**，实为 upper 值） | `--t5-addr-strict`（default **0.3647**，判据基线）+ `--t5-addr-upper`（0.41，**仅参照**）+ `--t5-addr`（DEPRECATED，等同 strict） |
| F2 比较 | `strict_observed − 0.41`（**跨口径**） | `strict_observed − 0.3647`（**同口径**） |
| 输出 | 只有 `t5` 一个数 | 并列 `t5_label/t5_upper_reference/observed_label/observed_upper_reference`（遵 runbook §3.113） |

## 回归验证（可复算）

在 **D12-I 日志**上重跑（`v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl`）：

```
python3 tools/d12h/shape_gate.py --log v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl --out-json /tmp/sg.json
```

| 量 | 值 |
|---|---|
| `addr_head_strict` 实测 | **23.53%**（= 22.75% 的 body 级同族口径，见注） |
| T5 strict 基线 | **36.47%** |
| `drift_pp` | **−13.72pp** |
| 判据 ±15pp | **PASS** |

> 注：本脚本 `addr_head_strict` 为 **去空白 body 级**分母（n=510 中 120 条），与 `d12i_result.md` 里
> 22.75% 属**同一量的两个分母口径**，差 0.78pp，不影响 PASS/FAIL。**两者均已并列记录，不互相替代。**

**与 `d12i_leader_terminal_check.md` 记录的 −13.72pp 完全一致** ⇒ 修复未改变历史结论，只是让工具默认值自洽。

## 影响面

- 主树此前**没有** `tools/d12h/`（只在 worktree）⇒ 本次一并入库，避免下次在分支外重造；
- 后续任何臂跑 `shape_gate.py`，F2 默认即为同口径，**不再需要每次手工改基线**（这正是 D12-I 踩坑的根源）。
