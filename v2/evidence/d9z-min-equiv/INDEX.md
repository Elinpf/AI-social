# INDEX — `d9z-min-equiv/` 证据索引（**每个 sha 必须与 rev 同列**）

## 0. 为什么需要这份索引（Leader 08:20 指出的证据完整性问题）

`run.jsonl` 的 sha `d8ca1160…` **同时出现在 4 份文件里**：

| 目录 | 文件 | 来自哪棵树 |
|---|---|---|
| `rift-min-equiv/` | `V1_base_3610815.jsonl` | `BASE=3610815`（master 线） |
| `rift-min-equiv/` | `V2_rift_minimal_6f1f800.jsonl` | `feat/rift-minimal @ 6f1f800` |
| `d9z-min-equiv/` | `V1_base_619e9ae.jsonl` | `BASE=619e9ae`（master 线） |
| `d9z-min-equiv/` | `V2_d9z_minimal_df35d7e.jsonl` | `feat/d9z-minimal @ df35d7e` |

- **好的一面（强证据）**：四份**逐字节相同** ⇒ rift 与 D9z 两个移植分支在**默认全关**下执行行为**完全一致**，
  与各自 BASE 也一致 —— 三个独立对照互相印证"真 no-op"。
- **坏的一面（`sha` 的唯一缺陷）**：**单凭 `d8ca1160…` 无法回答"这份日志来自哪棵树"**。
  ⇒ 引用该 sha 时**必须同时给出 rev**，不得只写 sha。

## 1. 本次（D9z）运行三元组

```
BASE   = 619e9ae0036ed64b8aeb6f260d2d4dfa46f8c3c9   （建分支时 rev-parse 写死）
branch = feat/d9z-minimal
HEAD   = df35d7e（移植提交，5 files +238/−8）
V1     = worktree .worktrees/d9z-min-v1（detached @ BASE）
V2     = worktree .worktrees/d9z-min（@ HEAD）
参数    = mock（HITT_LLM_PROVIDER 未设）/ seed=42 / agents=16 / rounds=8 / 各自全新 side-root
```

## 2. 文件 → sha256 → 该次运行的 rev

| 文件 | sha256 | 字节 | 来自 | 说明 |
|---|---|---:|---|---|
| `V1_base_619e9ae.jsonl` | `d8ca11609c3f470beb2a01aa3c6bdef8ba18febc9e9f4af311303abefacb9d4b` | 3898601 | **BASE=619e9ae**（V1 树） | 7541 事件 |
| `V2_d9z_minimal_df35d7e.jsonl` | `d8ca11609c3f470beb2a01aa3c6bdef8ba18febc9e9f4af311303abefacb9d4b` | 3898601 | **feat/d9z-minimal @ df35d7e**（V2 树） | 7541 事件；**与 V1 同 sha** |
| `V2b_visible_v1_619e9ae.json` | `bb1037a9cda27e2572b6be5aa2609c12129ac013e6b84209844263fd09c16a9c` | 22403 | **BASE=619e9ae** | 17 agents / 3701 seq |
| `V2b_visible_v2_df35d7e.json` | `bb1037a9cda27e2572b6be5aa2609c12129ac013e6b84209844263fd09c16a9c` | 22403 | **feat/d9z-minimal @ df35d7e** | 17 agents / 3701 seq；**与 v1 同 sha** |
| `chain_equiv.json` | `1b9c69f901bb29d0b0fb1ab2315dcd04b7db623e40083d19792939ece225c3a7` | 543 | V1 vs V2（`compare_chain.py`） | `identical=true` / `first_divergence=null` |
| `branch_entry_count.json` | `da16b793d8d65cdd8c7575624868cbd63600cab9724a0a63de2e4ed9d36bb932` | 1304 | **feat/d9z-minimal @ df35d7e** | OFF 0/128·0/257；ON 88/128·88/257 |
| `env_fingerprint.txt` | `7f2301be806308a09b820febe383b2fea13c2bb1c400b7a541a0976d0a4147a7` | 644 | 两臂（BASE / HEAD 同列） | 含逐项 `(unset)` 清单 |
| `pytest.txt` | `f58bafbe7cfd129ea5d123d607d3d44af015affe7d18e2c9a5087616451925fc` | 762 | **feat/d9z-minimal @ df35d7e** | 630 passed / 1 skipped |
| `V1_run.log` | `5d000bc983c215b360f92b18ef1b1d01586f23d53344f921bed7b7ed932d58dc` | 312 | **BASE=619e9ae** | `[life] n_agents=16 rounds=8 events=7541` |
| `V2_run.log` | `18b2056cf8d2d8625c311a36bee5fae4a6248076ba9097460ffaea9fb2128528` | 313 | **feat/d9z-minimal @ df35d7e** | `events=7541` |

⚠ **注意 `V1_run.log` 与 `V2_run.log` 的 sha 不同、而 `run.jsonl` 的 sha 相同**：
`run.log` 里含**耗时 `seconds=…`**（墙钟），故两臂必然不同；`run.jsonl` 不含墙钟 ⇒ 逐字节相同。
**这不矛盾，反而说明"日志内容确定、只有墙钟在变"**。

## 3. 判据提示（读数据的人据此复核，不必问我）

- **V2b 是第一道闸**：比较 `V2b_visible_v1/v2.json` 的 `agents[aid]` 两个列表**逐条**相等（不是比长度）。
- **V1/V2 是第二道闸**：`chain_equiv.json` 的 `identical` 必须 `true`、`first_divergence` 必须 `null`。
- **两个 `run.jsonl` 同 sha 是"加分项"**（比链同更强：能兜住 payload 字段顺序差异），
  但**判定等价性要看 `identical` 与 `V2b` 两项**，不是只看 sha 相同。
- **不要拿 `d8ca1160…` 与老批 `868e86d6…` 比**：`BASE` 不同 ⇒ `engine_version` 不同 ⇒ 整文件 sha 必变（与行为无关）。

## 4. 本目录不含判定结论

判定件由 `repro-verifier` 独立出具（"合成不是复核"）。本索引只做**证据与 rev 的绑定**。
