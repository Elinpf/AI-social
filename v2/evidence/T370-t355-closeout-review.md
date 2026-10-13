# T370 · 非作者独立核验：`T355` 收口（第四次重冻）

- **复核人**：sandbox-test-lead（**非作者**）｜ 被核：`T355`（`obs-stats-dev`，`793c14a`）
- **源**：OLD=`/root/t271/runs/t300/run.jsonl`(292,963) vs NEW=`/root/t271/runs/t355/run.jsonl`(292,255)
- **脚本**：`v2/evidence/t370_attribution_verify.py`、`t370_matrix_separability.py`、`t370_three_axis_helper.py`、`t370_matrix_run.sh`
- ⚠️ 跨-epoch：含 `T353/T354` 行为变 + 指纹/冷缓存漂移 ⇒ 只核**归因内部自洽**（不重下结论）。

---

## ① 事件数归因逐项复算 + 算数闭合 —— **PASS**

命令：`python3 v2/evidence/t370_attribution_verify.py [OLD] [NEW] [EXPECTED.json]`
- **独立复算**：行数 292,963→292,255，**Δ=−708**；**Σ逐族Δ = −708 == 行数差 ⇒ 闭合、无残差** ✓。
- 非零族（独立值）：`MEMORY_FORGET −579`、`RELATION_CHANGE −56`、`LLM_CALL −40`、`MEMORY_WRITE −8`、`OBSERVATION −8`、`PERSONA_DRIFT_CANDIDATE −8`、`PERSONA_DRIFT −6`、`LLM_JUDGMENT −3`。
- **对账 `T355-refreeze.md §5` 表**：**N/N 全等** ✓。
- **可隔离 vs 机制**：作者标"本轮为**跨-epoch 对照** ⇒ 上表多为**机制归因**；严格隔离需 §6 矩阵/`T366`" —— **我认同**，与 `T300`/`T349` 同规；**未归因：无算术残差** ✓。
- **反向负例**：R1（挪 1 条、总数不变）⇒ 清单不匹配+闭合破；R2（总数−1）⇒ 检出。**非恒真** ✓。

## ② 四档分类合规 —— **PASS（附一处独立发现）**

- `T353`（D3）/`T354`（D11）：**【行为变+指纹变】** —— 我独立证 `T354` 真行为变（2×2 矩阵 `C≠A0`、`state_hash` 变）；`T353` 由 `T366` 证消费点真通（默认 conservative 下 prop 轴不激发，见 ④ 功效）。
- `perceive` 修复：**【无行为变】**（默认下 live 路径本就读 `engine.config`）—— 一致。
- `T372` 双计缺陷：**登记为【已知偏差】+ provenance** ✓（与 Leader 要我落实的两条标注一致，见 ⑤）。
- ⭐ **独立发现（② 归类不足）**：`T361`（`8a7dc16` "增 `LLM_CALL.judgment_id`"）在 `§3` 被列为 **【无行为变（测试/装置）】**；但按三轴判：`LLM_CALL` 加字段 ⇒ **日志链变**、`LLM_CALL` 为 identity fold ⇒ **`state_hash` 不变**、**指纹不变** ⇒ 应归 **②【仅日志增（字段增）】**（**非 ④**）。
  - 佐证：anchor `ce1940c` **自己**记的是"`T361` 落地(**仅字段增/哈希链变**)"；我实比 T300 vs T355 的 `LLM_CALL` payload：**`ADDED=['judgment_id']`**（`agent_id` 两支均无）。
  - ⇒ **建议 `§3` 把 `T361` 改标②**（④ 部分仅指"测试/装置"子项）。这正是 Leader 点名的易混类（"仅字段增/链变"↔"无行为变"）。

## ③ 多 sha 分开记 + 字节一致 —— **PASS**

- **多 sha 互异**（golden/metrics `provenance` 实读）：`run_tree_sha=1d3af8c` / `baseline_code_sha=be9441b` / `engine_version_fingerprint=a871e36c…` ⇒ **三个独立轴** ✓；`feature_set=v2-T355`、`n_events=292255`、`final_state_hash=b7cab88e…`（与 `host.log` 一致）。
- **字节一致（独立重算）**：用**当前代码**对**旧 log `t300`** 重算 baseline，与 `archive/golden_baseline_pre_t355.json` 比：
  - **`ADDED=[] REMOVED=['final_state_hash','provenance'] CHANGED=[]`**；**`BYTE_EQUAL_TWO_CALLS=True`**；**剥离脚本附加字段后全等** ✓。
  - ⇒ 除"重冻脚本附加的元数据字段"外**逐字段不变**（复现并确认 obs §4）。

## ④ 2×2 消融矩阵可复算 + gate 判定 —— **可分离（附功率声明）**

- 自建 `t370_matrix_run.sh`（`run_override`、同 sha、同 side；n=8×24 seed=42）：
  | 格 | (ongoing,prop) | n_events | state_hash |
  |---|---|---|---|
  | A0 | (off,off) | 8511 | `82d2b951…` |
  | B | (off,on) | 8511 | **==A0** |
  | C | (on,off) | 8518 | `717b2346…` |
  | D | (on,on) | 8518 | **==C** |
- **可加残差 `D−C−B+A0 = 0`**；**交互项 X1 = 0**；族级残差**全 0** ⇒ **独立判定：可分离**（gate：未发现不可分离 ⇒ **不退回"一期一冻"**）。
- ⭐ **功效声明（必须并列写）**：`conservative` 下 **`propagate` 轴未被激发**（`B≡A0`、`D≡C`）⇒ **"可分离"成立，但 X1 检验是低功效的**（**"没测到"≠"不存在"**）。补强手段：**受控-prop 矩阵**（强制 prop 发射 × ongoing），待错峰跑。

## ⑤ 反向验证 + 归档 —— **PASS**

- `archive/golden_baseline_pre_t355.json`、`archive/metrics_baseline_p1_pre_t355.json` **均在、未删**；`note` 含**时效标注**（"有效期截至本轮重冻前；已被取代"）✓。
- ⭐ **两条 provenance 标注已在**（`metrics.note`）：**已知偏差"世界层强度 2× 口径（`T372` 双计未修）"** + **"仅在含 `T372` 缺陷的树上可复现"** ✓（与 Leader 要求一致）。
- 反向负例见 ①。

---

## 结论（一句话）

**`T355` 收口基本可采信**：① 归因复算 **N/N + 闭合**；③ 多 sha 互异 + 字节一致（独立重算）；④ **可分离**（X1=0，**低功效**）；⑤ 归档/时效/两标注齐。
⚠️ **一处须修正**：**② `T361`（`LLM_CALL.judgment_id` 字段增）应由"无行为变(测试/装置)"改标【仅日志增（链变、`state_hash` 不变、指纹不变）】**。
⚠️ **待补**：**受控-prop 矩阵**（把 ④ 的低功效补成有功效）。

*（T370 非作者独立核验 — sandbox-test-lead；`T372` 落主树后补其复跑）*
