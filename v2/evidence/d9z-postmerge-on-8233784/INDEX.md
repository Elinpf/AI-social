# INDEX — `d9z-postmerge-on-8233784/` 证据索引

**每个 sha 都与它来自的 rev 写在同一行**（教训：`d8ca1160…` 跨 4 份文件同 sha，单凭 sha 无法标识来自哪棵树）。

## 1. 运行三元组

```
BASE   = 823378404acf8226662978a8427c5883fea56a0b   （merge commit：a3beacf + 6a7cc6d）
branch = （无；两臂均 detached）
V1'    = worktree .worktrees/d9z-pm-v1  (detached @ BASE)
V2'    = worktree .worktrees/d9z-pm-v2  (detached @ BASE)
参数    = mock（HITT_LLM_PROVIDER 未设）/ seed=42 / agents=16 / rounds=8 / 各自全新 side-root
```

⚠ **V1' 与 V2' 是同一棵树（同一 rev）的两次独立运行**，不是「分支 vs 基线」。
本组比对验的是：① 确定性（两次跑同 sha）；② **与合并前旧批是否仍同 sha**（`d8ca1160…`）。

`code/` 树对象：`c5f9b5e296220b4c1adfaea7f15e0e9c6398d544`（`8233784:code`），
与移植分支 `df35d7e:code` **树对象相同** ⇒ 合并未改动 `code/` 一个字节。

## 2. 文件 → sha256 → 字节 → 来自哪个 rev

| 文件 | sha256 | 字节 | 来自 rev | 说明 |
|---|---|---:|---|---|
| `V1p_master8233784.jsonl` | `d8ca11609c3f470beb2a01aa3c6bdef8ba18febc9e9f4af311303abefacb9d4b` | 3898601 | **`8233784`** | 7541 事件；与旧 BASE=619e9ae / 分支 df35d7e 同 sha |
| `V2p_master8233784.jsonl` | `d8ca11609c3f470beb2a01aa3c6bdef8ba18febc9e9f4af311303abefacb9d4b` | 3898601 | **`8233784`** | 7541 事件；与 V1' 同 sha |
| `chain_equiv.json` | `3f0104f3a34591519b20e164eab2c6db1b4d10d3c11d3610fd79374db6cd760a` | 541 | `8233784`（`tools/d9z/compare_chain.py` 输出） | `identical=true` / `first_divergence=null` / 7541:7541 |
| `V1p_visible_master8233784.json` | `bb1037a9cda27e2572b6be5aa2609c12129ac013e6b84209844263fd09c16a9c` | 22403 | **`8233784`** | 17 agents / 3701 seq；与旧 V2b 同 sha |
| `V2p_visible_master8233784.json` | `bb1037a9cda27e2572b6be5aa2609c12129ac013e6b84209844263fd09c16a9c` | 22403 | **`8233784`** | 17 agents / 3701 seq；与 V1' 同 sha |
| `visible_compare.json` | `cf0035bdc52e107e07a52d4fbf3b95f36f4ae86c4a105dcc2d5051d6111c5c64` | 1538 | 两侧视图逐 agent 比对结果 | `agents_not_equal=0` / `all_equal=true` / 17 对 17 |
| `gate0_check.json` | `7324104098139b26b4e370f1281f84e8e0211cac411258da96f5dc1d69c93e49` | 2461 | `8233784`（`tools/dr/rift_gate0_check.py`，rev 同 `8233784`） | 三样全 `CANNOT-VERIFY`；输入 `V1p_master8233784.jsonl` |
| `gate0_POSITIVE_CONTROL.json` | `72ea5251fb1e61abff0eb016ead2e005fd95427e214a94a1db8a830063c6b3cb` | 3504 | 输入日志来自 **`feat/rift-events @ b48b857`** | 阳性对照：同一工具对 rift 真批 → `①MISMATCH ②PASS ③MISMATCH`（见 §4） |
| `rift_absence_proof.txt` | `b20b787b8108a520287de52dd0a67f084b3eda1650b411def9ade65705415612` | 653 | **`8233784`** | rift 符号 0 命中 / D9z 符号 1 命中 |
| `env_fingerprint.txt` | `e76d12bbf4d6f329a0d465bb65f6127391ecf51de63531148c20c12bb19cd159` | 851 | 两臂（同 rev） | 12 项逐项 `(unset)` |
| `V1p_run.log` | `3b948432383f6ed39f94c80080a03c34d3e7b43ad5693c64cb45f1db74b5a945` | 451 | **`8233784`** | `events=7541` / `final_state_hash=sha256:84c1a221…` |
| `V2p_run.log` | `a7ac3e71f178b7ef6de8385fb1333da1f40c8f2f3bb2c420f04612d2c607aa07` | 451 | **`8233784`** | `events=7541` / `final_state_hash` 与 V1' 逐字相同 |

⚠ 两 `run.log` sha 不同、两 `run.jsonl` sha 相同：`run.log` 含墙钟 `seconds=`（V1' `1.8351` / V2' `1.7224`），
`run.jsonl` 不含墙钟。**不矛盾。**

## 3. 三查结论（**逐项写明可验性，不把"算不出"写成 0**）

| # | 口径 | 在 `8233784` 上的结论 | 依据 |
|---|---|---|---|
| ① | `distinct(agent_id, rift_id)` == 台账登记数 | **CANNOT-VERIFY** | 本树无 rift 观测面（`rift_absence_proof.txt`：`RIFT_OPEN`/`RIFT_CLOSE`/`HITT_DR_RIFT_EVENTS` 均 0 命中）⇒ 本批 `RIFT_OPEN=0`、台账登记也是 0 —— **无法区分「没有负向话」与「该机制在此树不存在」** |
| ② | `RIFT_CLOSE` 的 `reason` 封闭集（`unknown` 单列不计） | **CANNOT-VERIFY** | 同上，本批 `RIFT_CLOSE=0` |
| ③ | peer 视野逐 seq（`dialogue_rift.open` 对齐「该 agent × 该对端」） | **PASS** | `visible_compare.json`：17 agents 逐条相等、3701:3701、`agents_not_equal=0` |

**⇒ ①② 不是「跑失败」，是「在这棵树上不可观测」。** 若要验 ①②，正确位置是含 rift 观测面的树
（`feat/rift-events` / `feat/rift-minimal`），那里已有实测：`RIFT_OPEN` 49 条 / `distinct(rift_id)` 7 /
**`distinct(agent_id,rift_id)` 49 == 登记 49 → PASS**，`RIFT_CLOSE` 3 条全 `prune`、`unknown=0` → PASS，
③ 修正口径违例 0 → PASS（见 `rift-on_n16r24_s42/README-caliber.md` §5）。

## 4. 关于 `gate0_POSITIVE_CONTROL.json`（**必须连同本节一起读**）

拿 `tools/dr/rift_gate0_check.py` 去跑 rift 真批，得到 `①MISMATCH ②PASS ③MISMATCH`。**这不能读成"rift 真批不合格"**：

- **①** 报的原文是 `OPEN 事件 distinct=7（重复 42） vs 重放登记=49` —— 这是**单位不同**：
  `rift_id` 形如 `R|<thread>|<msg_uid>`，**不含 agent 域**；一句负向话被 7 个听者各记一笔
  ⇒ `distinct(rift_id)=7` 是「负向话条数」，`49` 是「听众记账条数」。改用 `distinct(agent_id,rift_id)` 即 49 == 49。
- **③** 首个违例 `seq=7314 / agent=P016 / snapshot 2 vs expected 3` —— 因为 `dialogue_rift.open/rift_ids`
  是「该 agent 与**本条对端**相关的未关闭 rift」，**不是全台账**；工具按全台账比 ⇒ 必违例。

⇒ **本工具的 ①③ 口径本身有缺陷**（与 `README-caliber.md` §5 的结论一致，那里已写明"修正版待 `repro-verifier` 重跑"）。
这组阳性对照的用途是**证明工具会给出 PASS/MISMATCH 而不是一律 CANNOT-VERIFY**（即工具没坏、数据有内容），
**不是**用它给 rift 真批下判定。

## 5. 判据提示

- **等价性判据**：`chain_equiv.json` 的 `identical=true` + `first_divergence=null` + `events_compared == identical_prefix_events == 7541`，
  **且**两侧 `run.jsonl` sha 与合并前旧批 `d8ca1160…` **相同**。**退出码 0 不算判据。**
- 两侧 `run.jsonl` 同 sha 是**加分项**（比链同更强：能兜住 payload 字段顺序差异）。
- **不要拿 `d8ca1160…` 去和别批 `868e86d6…` 比**：`BASE` 不同 ⇒ `engine_version` 不同 ⇒ 整文件 sha 必变（与行为无关）。
- 引用 `d8ca1160…` 时必须同时写 rev：本目录两份来自 **`8233784`**；`d9z-min-equiv/` 两份来自 `619e9ae` / `df35d7e`；
  `rift-min-equiv/` 两份来自 `3610815` / `6f1f800`。

## 6. 本目录不含效果判定

本索引只绑定「证据 ↔ rev」并陈述三查的可验性。**等价/合格与否的判定权在 Leader / `repro-verifier`。**
