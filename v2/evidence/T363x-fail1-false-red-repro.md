# T363 · `FAIL①` 假红留档（非作者独立复现）

> 作者：kernel-dev｜时间：2026-10-13 16:1x｜性质：**假红实锤 + 独立佐证**（非 `T354` 缺陷）
> 缘由：`T363-run.json` 首版判 `off_eq_neutralized=false`（FAIL①「关态存在其它隐藏依赖」），
> 核验人 `sim-engine-stats-architect` 自纠为**脚本假红**；本文件为**非作者侧**独立复现，留档防"只看到更正前版本"的误读。

## 结论（一句话）

`off` 与"中和变体(neu)" **行为完全等价**：**族计数全等、事件总数全等、`state_hash` 全等**；
逐条字节差异**仅** `WORLD_INIT.config_digest`（off 改了运行时 cfg 摘要）+ `TURN_SEAL.payload.last_hash`（哈希链级联）。
⇒ **关臂干净、无隐藏依赖**。`FAIL①` 系核验脚本判据过严所致。

## 复现（非作者脚本，n=3×8 mock，<2min）

脚本：`v2/evidence/k_t354_fail1_repro.py`
命令：`python v2/evidence/k_t354_fail1_repro.py`
（独立于作者测试与作者核验脚本；就地复现 T363 的三臂 on/off/neu，比较族计数、len、`state_hash`、去哈希链逐条差异。）

实测输出（sha：`00be031` 树）：

```
=== family diff off vs neu ===        （空 ⇒ 族计数全等）
=== len === off 488 neu 488           （事件总数全等）
state_hash off==neu: True
=== nohash diff count === 9
types of first 20 diffs: ['WORLD_INIT', 'TURN_SEAL' × 8]
  seq 0  WORLD_INIT  config_digest: off=66e79600… neu=58485c06…   （改 cfg 的必然后果）
  seq 67 TURN_SEAL   last_hash:     off=af8478af… neu=c216e15e…   （payload 内哈希链级联）
```

## 根因（判据 vs 口径）

`t363_verify_t354.py::_nohash()` 只剥离了记录的**顶层** `hash`/`prev_hash`，**未剥 `TURN_SEAL.payload.last_hash`**；
而 `WORLD_INIT.payload.config_digest` 因 off 改了 cfg 必然不同 ⇒ 哈希链从 `WORLD_INIT` 起级联进每条 `TURN_SEAL.last_hash`。
核验脚本据此判"逐字节不等"⇒ 假红。

**正确口径**（`T299`/`08 §5.10` 已立，本次重申）：**判"语义等价"必须先走口径（`state_hash`/语义门，排除 `WORLD_INIT` 运行时 config 摘要与哈希链级联），再看字节**。
"逐字节不等" ≠ "语义不等"。

## 权威判据

`state_hash`：`on=de9c0525…e1adf`；`off = neu = 5f6a5679…92c6f8`（**off ≡ neu 成立**）。
