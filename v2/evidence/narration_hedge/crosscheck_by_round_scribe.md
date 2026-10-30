# R27 交叉核对：metrics-dev 出数器 vs round-scribe 独立复算器

两份实现**互不共享代码**：scribe 版直接调 `tools/d5/dialogue_metrics.py` CLI 并自算旁白括号统计；metrics-dev 版调其 `main()` 并复用 `tools/d9i/narration_stats.py` 的旁白正则。二者对同一对日志算 delta。

> 指标名映射：scribe 表里 `F-7`（越界提及率）≡ metrics-dev 的 `F-7a`（同一条 d5 `F-7a_offscreen_mention`）。

| 指标 | metrics-dev delta | scribe delta | 结论 |
|---|---|---|---|
| F-1 | -0.026178 | -0.026178 | 一致 |
| F-2 | +0.016000 | +0.016000 | 一致 |
| F-2b | +0.000000 | +0.000000 | 一致 |
| F-3 | -0.090909 | -0.090909 | 一致 |
| F-4 | +0.000000 | +0.000000 | 一致 |
| F-5 | +0.000000 | +0.000000 | 一致 |
| F-6 | +0.115183 | +0.115183 | 一致 |
| F-7a | +0.041885 | +0.041885 | 一致 |

- 旁白覆盖率：metrics-dev `0.0 → 0.926702`；scribe `0.0 → 0.9267015706806283` ⇒ **一致**
- 旁白块数/唯一块：metrics-dev ON `blocks_total=196 / repeat_blocks=3`（唯一 = 196−重复出现抵消后 = 193）；scribe ON `196 / 唯一 193` ⇒ **一致**
- hedge_verdict：metrics-dev `swap_only`；scribe `swap_only` ⇒ **一致**
- 比对结果：**ALL_MATCH**

## 唯一已知口径差异（不是矛盾，两边都自报口径）
- 「旁白字数占正文」：scribe `0.2876` = 旁白字符数 / body 总字符数；metrics-dev `0.322266`。两者分母定义不同（是否把括号外的标点/分隔计入方括号内）。报告正文只引用 metrics-dev 的数，并注明 scribe 的分母口径。

## 复算命令（scribe 侧，仓库根执行）
```bash
python3 v2/evidence/narration_hedge/recompute_by_round_scribe.py \
  --off v2/evidence/d9m-ab-off_n16r24_s42 --on v2/evidence/d9m-ab-on_n16r24_s42 \
  --out-json v2/evidence/narration_hedge/readings_by_round_scribe.json \
  --out-md   v2/evidence/narration_hedge/table_by_round_scribe.md
```

## 文件指纹（sha256）
- `v2/evidence/narration_hedge/readings.json` `9c6818b04bef44acfa1c5543de9ecde9037ffe25e7290c6cf539102ba201a6f4`
- `v2/evidence/narration_hedge/table.md` `007c89a1d76edbeeed9746243abfc71624a1b04bb10f8b4c281d088667163d2d`
- `v2/evidence/narration_hedge/readings_by_round_scribe.json` `a222a28a6ea44cf22aa3a95d47430959e9adf4beddf7a001ab8625f582b7a48a`
- `v2/evidence/narration_hedge/table_by_round_scribe.md` `ad7e9a466188a03cc20624611788ea9feaa30c54af35bc203fa58ed76e9964c7`
- `v2/evidence/narration_hedge/recompute_by_round_scribe.py` `6f1868c5f1c21483d7dae49edd2e84d97a42cadaee474b8db4f17c7fca10b87f`
