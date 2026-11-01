# `feat/rift-minimal` 移植判定：**双证成立**（静态 + 实测）

- 时间：2026-11-02 07:4x
- 被测分支：`feat/rift-minimal@6f1f80052ac7f1e590760ef5fa422823c5c0b9e7`（远端已确认）
- `BASE = 3610815475cd49654d7e560f7137b7111f6dd9f8`（建分支时 `rev-parse` 写死）
- 判定依据：`v2/evidence/rift-minimal-hunk-static-table-by-verifier.md`（静态）+ 本文 §3 的实测四项

## 1. 判定

| 层 | 结论 |
|---|---|
| **否决闸** | `V2` off 臂 `RIFT_OPEN=0` / `RIFT_CLOSE=0` ⇒ **PASS**（闸在比链**之前**判，不是比链之后再解释） |
| **实测** | `V1 ≡ V2`：`identical=true` / `first_divergence=null`；两 `run.jsonl` **整文件同 sha** |
| **静态** | hunk 表覆盖 V2 **全部 8 文件**（判据 4 为 **N/A**：`pick_mark` 在本分支 0 命中，属"无对象"非"未覆盖"） |
| **合成** | **双证成立**（`A ≡ B` **且** 静态表覆盖被测分支全部 `code/` hunk） |

## 2. 实测四项（`dialogue-core-dev` 报，Leader 未独立复算 —— 见 §5 边界）

```
BASE      : 3610815（V1 worktree 用 --detach 3610815 建）
VETO      : RIFT_OPEN=0, RIFT_CLOSE=0 → PASS
V1/V2     : identical=true, first_divergence=null
            事件 7541 / 7541；identical_prefix_events=7541
            两侧 run.jsonl sha256 相同：d8ca11609c3f470b…（内容 sha·实测值·转述，原始文件未入库）（整文件逐字节同，不只是链同）
            final_state_hash 两侧均 84c1a221…（实测值·转述，原始文件未入库）
            provider 全 mock（690 次 LLM_CALL）
proof     : A(OPEN 0/CLOSE 0/无 rift_ids 键) · B(OPEN 1/CLOSE 1 repair/rift_ids 键 1) · C(全 0, enabled=0)
            + D=prune、E=expire；all_three_reasons_have_samples=true；all_pass=true；unknown 出现 0 次
pytest    : 639 passed / 0 failed / 1 skipped（无红）
```

**环境**：两臂 env 全清，`env | grep -E '^(HITT_|LIFE_|INTRA)'` 跑前跑后均 **0 条残留**，`(unset)` 逐项清单落 `env_fingerprint.txt`；各自全新 `side-root`（`/tmp/riftmin_sideA` / `sideB`）。
⇒ 满足 §18.4a 配对臂三条件（配置声明相同且清单独落盘 / 各自独立跑 / 结论范围见 §4）。

## 3. 本次 run 的 sha 与老批不同 —— **不是退步**

本次 `run.jsonl` 的 sha 与老批（内容 sha·历史版·未入库）不同：`BASE` 是 `master@3610815`，`engine_version` 与老批不同 ⇒ **整文件 sha 必然变**。
**判据是 `V1` 与 `V2` 同 sha，不是与老批同 sha。** 把它和老批比并得出"变了"的读法是错的。

## 4. 结论范围（写死，防外推）

1. 只证「**默认全关 + mock + `16×8 / seed=42`** 下事件流等价」，**不证"两棵树等价"**（§19.6 延伸陷阱）；
2. **不证** rift 在真 LLM 下的效果 —— 本分支是**能力落地**，不是效果实验；
3. **不含 D9z**：本分支 `HITT_INTRA_ROUND_VISIBILITY` 0 命中 ⇒ **不得用本批数据谈同轮可见**（§18）；
4. `repair`/`expire` 本次由 `rift_events_proof` 的 D/E 两臂**首次逼出样例**（`all_three_reasons_have_samples=true`），但那是 **mock 构造**，**不是真实批观察**。

## 5. 边界：证据尚未入库（§20）

`v2/evidence/rift-min-equiv/` 那批原始证据（`V1/V2` 的 `run.jsonl`、`env_fingerprint.txt`、`chain_equiv.json`）**仍在本地、推送失败**（`Failed to connect to github.com port 443`，136 秒超时；是网络不是 hook）。

⇒ **按 §20，本文不得声称"证据已入库"**。上述 sha 全部为**转述值**，**未经 Leader 从远端读回**。
⇒ **待推成功后必须做**：`git show origin/master:v2/evidence/rift-min-equiv/<file> | sha256sum` 与上表逐字比对；**不等即本判定无效**。

## 5.5 率的定义

**本件不新增任何率**（判定件，只有等价/不等的二值结论与计数）。

| 率名 | 分子 | 分母 | 计算式（含边界） | 纳入排除 |
|---|---|---|---|---|
| 无（只报 `identical` 与事件计数 7541/7541） | 不适用 | 不适用 | 不适用 | 不适用 |

## 5.6 外推与假定

**本件不外推**。结论限于「默认全关 + mock + `16×8/seed=42`」这一配置。

| 外推式 | 假定不变的量 | 值来源 |
|---|---|---|
| 无（不估效果量、不推真 LLM 行为） | 不适用 | 不适用 |

## 6. 复核分工

- 静态表：`repro-verifier`（五项判据，行号 + 缩进；判据 4 判 N/A、判据 5 判"调用链守卫 PASS"并附三分量不变量 1/2/1）；
- 实测：`dialogue-core-dev` 执行，**Leader 未独立复算**；
- 本判定：Leader 合成 —— **合成不是复核**，双证的两证分别来自上述两方。
