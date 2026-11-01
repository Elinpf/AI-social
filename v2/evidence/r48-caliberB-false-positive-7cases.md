# 口径 B 假阳性清单（7 条）：被记成「跨地点」、实际回复时双方已同处

> 来源：`v2/evidence/d9z-on_n16r56_s42/run.jsonl`（sha256 前 8 位 `1f0fec69`，90,532 行）
> 生成：仿真与跑批工程师｜2026-11-01｜由 `tools/r48/place_coherence.py` 的口径差异诊断复算

**用途**：口径 B（本条 `payload.place` vs 父条 `payload.place`）会把「父发言人真的走过去碰面」
误记为跨地点。做物理一致性判断时请用口径 A（回复事件那一瞬间双方是否同处）。

| # | gap | 父条 round | 父条 msg_uid | 父发言人@父条地点 | 回复 round | 回复 msg_uid | 回复方@回复地点 | 回复时收件人所在地 | 实际发生 |
|---:|---:|---:|---|---|---:|---|---|---|---|
| 1 | 2 | 4 | `42:3948` | P009@market | 6 | `42:5222` | P016@cafe | P009@cafe | P009 从 market 移动到 cafe |
| 2 | 1 | 8 | `42:7830` | P009@cafe | 9 | `42:9008` | P016@residence | P009@residence | P009 从 cafe 移动到 residence |
| 3 | 2 | 14 | `42:21629` | P008@town_hall | 16 | `42:23152` | P011@market | P008@market | P008 从 town_hall 移动到 market |
| 4 | 1 | 20 | `42:26449` | P005@cafe | 21 | `42:27520` | P007@residence | P005@residence | P005 从 cafe 移动到 residence |
| 5 | 1 | 29 | `42:38285` | P004@kitchen | 30 | `42:38530` | P010@cafe | P004@cafe | P004 从 kitchen 移动到 cafe |
| 6 | 1 | 32 | `42:41371` | P003@cafe | 33 | `42:47586` | P011@residence | P003@residence | P003 从 cafe 移动到 residence |
| 7 | 1 | 32 | `42:41679` | P009@cafe | 33 | `42:50268` | P016@residence | P009@residence | P009 从 cafe 移动到 residence |

复算：`python3 tools/r48/place_coherence.py --batch-dir v2/evidence/d9z-on_n16r56_s42`
（口径 A 跨=74 / 口径 B 跨=74 在 gap=0 同值；差异出现在 gap=1 的 55 vs 60、gap>=2 的 44 vs 46，共 5+2=7 条。）
