# INDEX — `rift-min-equiv/` 证据索引（**每个 sha 必须与 rev 同列**）

## 0. 为什么需要这份索引

`run.jsonl` 的 sha `d8ca11609c3f470beb2a01aa3c6bdef8ba18febc9e9f4af311303abefacb9d4b`
**同时出现在 4 份文件里**（本目录 2 份 + `d9z-min-equiv/` 2 份）：

| 目录 | 文件 | 来自哪棵树 |
|---|---|---|
| `rift-min-equiv/` | `V1_base_3610815.jsonl` | `BASE=3610815`（master 线） |
| `rift-min-equiv/` | `V2_rift_minimal_6f1f800.jsonl` | `feat/rift-minimal @ 6f1f800` |
| `d9z-min-equiv/` | `V1_base_619e9ae.jsonl` | `BASE=619e9ae`（master 线） |
| `d9z-min-equiv/` | `V2_d9z_minimal_df35d7e.jsonl` | `feat/d9z-minimal @ df35d7e` |

- **好的一面（强证据）**：四份**逐字节相同** ⇒ rift 与 D9z 两个移植分支在**默认全关**下执行行为完全一致，
  且与各自 BASE 一致 —— 三个独立对照互相印证「真 no-op」。
- **坏的一面（`sha` 的唯一缺陷）**：**单凭 `d8ca1160…` 无法回答「这份日志来自哪棵树」**。
  ⇒ 引用该 sha 时**必须同时给出 rev**，不得只写 sha。

## 1. 本次（rift）运行三元组

```
BASE   = 3610815475cd49654d7e560f7137b7111f6dd9f8   （建分支时 rev-parse 写死）
branch = feat/rift-minimal
HEAD   = 6f1f800（移植提交，8 files +305/−6）
V1     = worktree .worktrees/rift-min-v1（detached @ BASE）
V2     = worktree .worktrees/rift-min（@ HEAD）
参数    = mock（HITT_LLM_PROVIDER 未设）/ seed=42 / agents=16 / rounds=8 / 各自全新 side-root
```

⚠ 本目录文件所在的工作树 HEAD 是 `b9e3b72`（证据提交，**不改 code/**）；
**行为等价性针对的 rev 是 `6f1f800`**（`V2_run.log` / `env_fingerprint.txt` 内写的就是 `6f1f800`）。
引用 `V2` 时以 `6f1f800` 为准，`b9e3b72` 只向后追加 `tools/dr/rift_events_proof.py` 与本目录文件。

## 2. 文件 → sha256 → 字节 → 该次运行的 rev

| 文件 | sha256 | 字节 | 来自 | 说明 |
|---|---|---:|---|---|
| `V1_base_3610815.jsonl` | `d8ca11609c3f470beb2a01aa3c6bdef8ba18febc9e9f4af311303abefacb9d4b` | 3898601 | **BASE=3610815**（V1 树） | 7541 事件 |
| `V2_rift_minimal_6f1f800.jsonl` | `d8ca11609c3f470beb2a01aa3c6bdef8ba18febc9e9f4af311303abefacb9d4b` | 3898601 | **feat/rift-minimal @ 6f1f800**（V2 树） | 7541 事件；**与 V1 同 sha** |
| `chain_equiv.json` | `b11a8516635b79d6359f2644c6c417717fd121f128020d8f74368d5a8e553627` | 545 | V1 vs V2（`compare_chain.py`） | `identical=true` / `first_divergence=null` / 7541:7541 |
| `proof_three_tiers.json` | `7b9a5161742db08fb03815be20154e202870e9f256284f90c3ef0c2dbe98346b` | 3865 | **feat/rift-minimal @ 6f1f800** | 五臂 mock 自证；`checks.all_pass=true` |
| `env_fingerprint.txt` | `18262538e2ee3e6564f508e3f197e3a86063bccaab460b5fb71f76cf9131c5f1` | 636 | 两臂（BASE / HEAD 同列） | 12 项逐项 `(unset)` 清单 |
| `pytest.txt` | `25ccbb75133273e98947430be7236fc9cead8057d8c04b1ae174d777e63a1811` | 762 | **feat/rift-minimal @ 6f1f800** | 639 passed / 1 skipped |
| `V1_run.log` | `17fd3b5b80ab191474d43f61cc2ef919ba97ca12712e2d056bf170a1caa3ef05` | 314 | **BASE=3610815** | `events=7541` / `final_state_hash=sha256:84c1a221…` |
| `V2_run.log` | `4c05f37224bdb432838a445b656f51b36fd131c43317c7d72bf0a49a993e3be9` | 314 | **feat/rift-minimal @ 6f1f800** | `events=7541`；`final_state_hash` 与 V1 **逐字相同** |

⚠ **`V1_run.log` 与 `V2_run.log` 的 sha 不同、而 `run.jsonl` 的 sha 相同**：
`run.log` 含墙钟 `seconds=`（V1 `1.8702` / V2 `1.8393`），故两臂必然不同；
`run.jsonl` 不含墙钟 ⇒ 逐字节相同。**这不矛盾，反而说明「日志内容确定、只有墙钟在变」**。
另：两臂 `final_state_hash` 同为 `sha256:84c1a221a8593c28fe77db244257f3de9180a19c61ea74c0dd8bf20c15e61db1`。

## 3. 判据提示（读数据的人据此复核，不必问我）

- **第一道闸是 `RIFT_*` 事件计数**（rift 的安全性由「开时才出现事件」承担）：
  `V1_base_3610815.jsonl` 中 `RIFT_OPEN` / `RIFT_CLOSE` **必须为 0**；
  这是本分支相对 D9z 的**额外**前置闸，先判它、再比链。
  **本条已实测**（`grep -c '"RIFT_OPEN"'` / `'"RIFT_CLOSE"'` / `'rift_ids'`，对两份 `run.jsonl`）：
  `V1` = `0 / 0 / 0`，`V2` = `0 / 0 / 0`（即两臂都不含 rift 事件、不含 `rift_ids` 键）。
- **第二道闸比链**：`chain_equiv.json` 的 `identical` 必须 `true`、`first_divergence` 必须 `null`、
  `events_compared == identical_prefix_events == 7541`。
- **`proof_three_tiers.json` 的口径**：`arms.A`/`arms.C` 是关闭臂（要求零事件、无 `rift_ids` 键），
  `arms.B` 是开启臂；`reason_probes.D_prune` / `E_expire` 用极小参数（`max_open=1` / `max_age_rounds=1`）
  逼出 `prune` / `expire` 样例，`checks.all_three_reasons_have_samples=true` 表示三种 reason 都有实测样例。
- **两个 `run.jsonl` 同 sha 是「加分项」**（比链同更强：能兜住 payload 字段顺序差异），
  但**判定等价性要看 `identical` 与 `RIFT_*` 零计数两项**，不是只看 sha 相同。
- **不要拿 `d8ca1160…` 与老批 `868e86d6…` 比**：`BASE` 不同 ⇒ `engine_version` 不同 ⇒ 整文件 sha 必变（与行为无关）。

## 4. 本目录不含判定结论

判定件由 Leader / `repro-verifier` 独立出具（「合成不是复核」）。
本索引只做**证据与 rev 的绑定**，不复述判定。
