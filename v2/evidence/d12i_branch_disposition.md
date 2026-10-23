# 处置：`feat/d12i-aligned` 分支的拆分去留（Leader 裁定，2026-10-24）

> 背景：分支含 D12-I 的 **code 实现**（`46d25b8`）+ **tools/d12i/**（`9941e48`）+ 跑批产物；
> master 已有 D12-I 的 **refs + evidence**（`d12i_result.md` 等），但缺 code 与 tools。
> 判定已定：**「作废（形态漂移，非单变量）」，依据收窄为 F1 单闸**（F2 同口径 −13.72pp 已翻 PASS）。

## 裁定：**工具入库，机制留分支**

| 内容 | 处置 | 理由 |
|---|---|---|
| `tools/d12i/`（`build_external_shingles.py` / `selector_stats.py` / `wiring_proof.py`） | **合入 master** | 中性可复算资产；master 上的 `d12i_result.md` 直接引用这些读数，工具缺位则 evidence **不可复算** |
| `code/life` 的 D12I 开关实现 | **不合并**（留分支 `feat/d12i-aligned`） | 判定作废；把已失效机制的默认关开关塞进主树，只会扩大单变量污染面。需要时分支仍在，可复现 |
| 跑批产物（`run_d12i_aligned_n16r60_seed42/`） | 留分支 | master 有 `d12i_readings_20261024` 摘要；全量日志留分支按需取 |

## 入库前验证（可复算）

在 **master 代码基线**上跑分支工具（日志取自分支目录，只读）：

```
python3 tools/d12i/selector_stats.py --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl --key d12i
```

| 量 | 本次复算 | evidence 记录 | 一致 |
|---|---|---|---|
| `argmin_unique_rate` | **0.94118**（480/510） | 94.12% | ✅ |
| `not_all_equal_rate` | **0.98627**（503/510） | 98.63% | ✅ |
| `all_zero` / `all_zero_rate` | 0 / 0.0% | 0.0% | ✅ |
| `three_candidates_shingle_identical` | 3（0.588%） | 0.59% | ✅ |
| `picked_distribution` | {0:167, 1:174, 2:169} | 同 | ✅ |

⇒ **工具在 master 上逐位复现分支读数**，入库不影响任何历史数值。

## 另一件已核实的事

与执行方 `a323e28` 的 `shape_gate.py` 比对：主树版本与分支版本 **sha256 前 8 位同为 `1c321e51`，逐字节相同**（两边都含 `--points` 三点核与 `--t5-addr-strict/--t5-addr-upper`）⇒ **不存在"合并时丢 `--points`"的风险**，无需再处理。
