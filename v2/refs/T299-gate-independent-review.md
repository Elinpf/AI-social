# T299 · 语义相等门 —— 独立审阅（art-director，只读）

> 对象：`tools/t271/semantic_log_sha.py`（`a1617d7`，release）+ `verify_native_resume.sh` 新门分支
> 依据：Leader 2026-10-12 裁定；runbook §4；本审阅**只读、未改码/未改门**。
> 命令与实测：`--selftest`、`T271_VR_GATE=1 T271_VR_REVERSE=1 T271_VR_CUT=89`、`T271_VR_GATE=1 T271_VR_CUT=75`。

---

## 0. 结论（三问全过，附两条前瞻提醒）

- **① 排除集是否恰好 → 是（核过）。**
- **② 重算链是否复现引擎口径 → 是（核过）。**
- **③ 反向验证是否够"最小" → 是（单值 +1、不改结构）；附一条扩展提醒。**

**实测行为**：cut=89 **PASS**（语义 sha 相等 / `state_hash` 不等=0 / REVERSE ok）；cut=75 **FAIL 真阳性**（`state_hash` 不等=74 / 语义 sha 不同）；`--selftest` A=True（删计量不变，链级联覆盖=True）B=True（改语义变，扰动 `PLACE_MOVE.day`）。

---

## 1. ① 排除集是否恰好

**扫真实日志（`N1/run.jsonl`+`ref.jsonl`）**：
- `LLM_CALL.payload` 恰 **15 键**：`cache_key, cached, cost_units, degraded, engine_version, meta_digest, model, priority, prompt_hash, provider, purpose, thinking, tier, tokens_in, tokens_out`。
- **排除的 4 个** `{cached,tokens_in,tokens_out,cost_units}` 均为**缓存/计量**；**保留的 11 个**均为**语义/配置**（模型/供应商/用途/优先级/thinking/降级/版本/prompt_hash/meta_digest/cache_key/tier）。
- **该排而留**（会造成假红）的纯计量字段：**未发现**（15 键内除那 4 个外无其它纯计量）。
- **该留而被排**（会造成掩盖）：**无**（只排 4 个，且仅在 `LLM_CALL` 内）。
- **非 `LLM_CALL` 事件里出现排除字段：0 处**（`{cached,tokens_in,tokens_out,cost_units}` 不越界）。
- 旁证：我先前独立折叠时**未排 `cache_key`/`meta_digest`**，两路仍 0 处不等 ⇒ 保留它们**不会**引入假红 ✓。

## 2. ② 重算链是否复现引擎口径

- 引擎：`engine/ledger.py:24` `record["hash"]=compute_event_hash(record)`（覆盖去掉 `hash` 的整条，含 `prev_hash`）；`engine/kernel.py:239` `TURN_SEAL.payload.last_hash = ledger.last_hash()`（=上一条记录的 `hash`）。
- 门：`_normalize` 置 `prev_hash=规范化前驱`、pop `hash`、并把 `TURN_SEAL.payload.last_hash` 设为**规范化前驱**；再用**引擎自身的** `compute_event_hash` + `canonical_json` 重算 `nh`，逐条 `cj({**norm, hash:nh})` 入摘要，`prev=nh`。
- ⇒ **规范化链 = 引擎链的同构重算**（同函数、同 canon）；`last_hash` **自然相等**、**不靠断言** ✓。cut=89 实测两路语义 sha 相等佐证。

## 3. ③ 反向验证是否够"最小"

- `--selftest` B：取**首个 `DECISION` 类事件**的**首个数值字段**做 **单值 `+1`、不改结构**（实测扰动 = `PLACE_MOVE.day`）⇒ **真语义微扰 ⇒ sha 必变** ✓。
- A：改/删**计量字段** ⇒ sha **不变**，且检查**样本内确有 `LLM_CALL` 后跟 `TURN_SEAL`**（`链级联覆盖=True`）⇒ 证明重算链确实被口径化（不是"恰好没级联"）✓。
- 实测 cut=75 真分歧 ⇒ **报红**（真阳性）⇒ 门**不掩盖**真缺陷 ✓。

## 4. 两条前瞻提醒（**建议，非缺陷**）

1. **`EXCLUDE` 是白名单**：将来 `LLM_CALL.payload` **新增纯计量字段**（如 `latency_ms`/`retries`）会**假红**。建议：**新增字段时同步评估是否入 `EXCLUDE`**，并**重跑 `--selftest`**（A 应仍 True）。
2. **`--selftest` 的 B 扰动落在"首个 DECISION 事件"**：建议**在固定样本上钉死被扰动的事件类型/字段**（或对多类型各扰一次），使"必要性"可**跨版本重复**、不随样本首条变化而漂移。

## 5. 边界

- 只读：未改码、未改门、未碰 `config/*.json`、未碰 `t271-t292`。
- **本审阅只对"门"**；**cut=75 的真分歧属 life 域**（已交 life），不在本门范围。**T298 修复后的复核（T304）另待"定稿 sha"**。

---
*（T299 门独立审阅 — art-director）*
