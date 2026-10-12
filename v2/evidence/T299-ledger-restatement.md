# 台账重述：本门此前「逐字节一致」结论——按 T299 新口径重述

> 作者：release-engineer ｜ 2026-10-13 ｜ 任务：T299-semantic-equality-gate（验收项"台账重述"）
> 关联：`tools/t271/semantic_log_sha.py`（门实现）、`v2/refs/nightly-pipeline-runbook.md §4`、`v2/evidence/T299-semantic-equality-gate.json`

## 0. 为什么要重述
**旧门**（截至 `28862a4`）：`verify_native_resume.sh` 比**整份日志 sha256**、**无字段排除** ⇒ 把 `LLM_CALL.payload.{cached,tokens_in,tokens_out,cost_units}` **与由它们引起的 `hash/prev_hash/TURN_SEAL.last_hash` 下游差**也纳入了"逐字节一致"。
**新门**（T299，裁定方案 (b)）：**回答「世界语义是否一致」**——**只排除**上述 4 个计量字段，**对规范化事件重算哈希链**；`cache_key/prompt_hash/meta_digest/engine_version/provider/purpose/model/priority/tier/thinking/degraded` 与 **`TURN_SEAL.state_hash` 全保留必比**。
⇒ 因此，**此前所有用"逐字节一致"表述的结论，均应重述为"世界语义一致"**（并注明其原测试配置）。

## 1. 逐条重述

| # | 原结论（旧口径措辞） | 出处 | 新口径重述 | 边界/备注 |
|---|---|---|---|---|
| T276 | flush 前缀**续跑**与一次性跑"**逐字节一致**" | `v2/evidence/T272-rss-attribution.md:27`（列为"续跑逐字节一致"的正确性障碍，后已清） | = **世界语义一致**（排除 4 计量字段 + 重算链后逐条相等） | 原"逐字节"含缓存计量与链下游差；**其原验收配置**上语义一致 |
| T288 | `restore()` + `body_ref=None` 达成"**逐字节一致**"（三档全过） | Leader 21:43 通报；T288 证据 | = **世界语义一致** | ⚠️ **非普适**：T299 实测出反例——同 sha 下 `cut=75` 续跑 round 76 起真分歧、`cut=89` 一致（见 §2）。原三档配置成立 |
| T292 | native 续跑探针"**逐字节一致**"（探针 PASS） | `v2/evidence/T292-native-resume-verify.json`（`28862a4`） | = **世界语义一致**（于其配置） | 探针口径已由 T299 替换为语义投影；**cut 敏感性**经 T299 双面数据细化 |

## 2. 不降级声明（关键）
- **新口径不放宽"语义"**：只排除**与语义无关的本地缓存计量**字段；**保留 `cache_key`**（两路"发出的调用集合"不同则仍报红）、**保留 `TURN_SEAL.state_hash`**（世界态不同则仍报红）。
- **反向验证（必要性）已过**：对日志注入**最小语义扰动**（单值 `+1` 的 `PLACE_MOVE.day`，不改结构）⇒ **门仍报红**（`T271_VR_REVERSE=1`）。
- **真阳性已验**：`cut=75`（世界真分叉，`state_hash` 不等数=74）⇒ **门报红**；`cut=89`（无真分歧）⇒ **门报绿**。这是"双面真数据"，强于自造扰动。

## 3. 遗留（不属本条、已另派）
- **cut 相关真缺陷（②类）**：同一 sha 下 resume 对 cut 敏感（`@75` 分叉 / `@89` 一致）；**非哈希序**（对 `PYTHONHASHSEED` 完全不敏感）、非竞态、非 cache。**已交 life**，最小复现 `tools/t271/repro_resume_cut.sh 75`。修好后，上述结论可在"任意 cut"上重核。
- **obs 的 `t292-shared-cache-ablation.md`**：是关于**共享 `freeze_cache` 命中率**的消融（**非**"逐字节/语义一致"主张），**不受本重述影响**。
