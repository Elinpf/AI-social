# `feat/rift-events` → `master` 合并可行性实测（只读，未合并、未跑批）

- 生成时间：2026-11-02 03:1x
- 生成方式：`git merge-tree --write-tree`（**不写工作区、不动分支、不动 index**）
- 输入：`origin/master`、`efcf441`（`feat/rift-events` 头）
- 目的：回答"合并前等价性证明要证明到什么程度"

## 1. 先纠一条前序说法（重要）

`dialogue-core-dev` 报的「`code/` 与 `efcf441` 逐字节相同」——其**主体是 `efcf441 ↔ 8a58fef`**（后者只多一个 `tools/dr/rift_gate0_check.py`）。

**`efcf441 ↔ master` 的 `code/` 并不相同。** 实测（`git diff --stat origin/master efcf441 -- code/`）：

```
 27 files changed, 1339 insertions(+), 37814 deletions(-)
```

其中 `37814` 删除**不是** `efcf441` 删了东西，而是 `efcf441` 的基线（merge-base `df29cf9`）**早于 master 上大量提交** ⇒ 站在 `efcf441` 上看，master 上的东西"还不存在"。典型：
`code/life/encounter_metrics.py`（258 行）、`code/life/tests/support/planner_off_golden.json`（36,616 行）、`test_addr_evolve_toggle.py`、`test_habit_living_slot.py`、`test_life_encounter_chat.py`。

⇒ **任何"把 `efcf441` 直接发成 master"的做法都会删掉这些文件**（`pre-push` 的"无文件删除"闸会拦，但不应靠闸兜底）。

## 2. 合并实测：只有 1 处冲突，且在数据文件

```
$ git merge-tree --write-tree --name-only origin/master efcf441
d7bb9737cc9b3784ff3a4ca41eac880ff8479518（临时树·非当前版）
v2/evidence/d9z-on_n16r56_s42/launch_cmd.txt

Auto-merging code/life/agent.py
CONFLICT (add/add): Merge conflict in v2/evidence/d9z-on_n16r56_s42/launch_cmd.txt
```

| 项 | 实测 |
|---|---|
| 合并结果树 | `d7bb9737（临时树·非当前版）`（**临时树，未入库**；全文出现该 sha 处均指此临时树，非当前版、非任何分支头） |
| 冲突数 | **1** |
| 冲突位置 | `v2/evidence/d9z-on_n16r56_s42/launch_cmd.txt` —— **数据/记录文件，不是代码** |
| `code/life/agent.py` | **自动合并成功**（`Auto-merging`，无冲突） |
| `code/` 内文件删除 | **0**（`encounter_metrics.py` 等全部保留） |

## 3. 合并给 `master` 带来什么（`git diff --stat origin/master d7bb9737（临时树·非当前版） -- code/`）

```
 code/config/dialogue_repair.json    |   6 ++-
 code/engine/events.py               |   2 +
 code/engine/kernel.py               |  17 +
 code/engine/perceive.py             |  46 ++-
 code/engine/replay.py               |   2 +
 code/life/agent.py                  | 233 +-
 code/life/dialogue_repair.py        | 100 +-
 code/life/ports.py                  |   5 +-
 code/orchestration/integration.py   |  72 +-
 code/orchestration/visibility_index.py | 13 +-
 code/tests/test_dr_separable.py     |  94 +   （新增）
 code/tests/test_intra_round_visibility.py | 140 +   （新增）
 code/tests/test_life_narration_action_diversity.py | 122 +  （新增）
 code/tests/test_life_narration_openings.py | 133 +   （新增）
 code/tests/test_life_narration_syntax_diversity.py | 157 +  （新增）
 code/tests/test_rift_events.py      | 172 +   （新增）
 16 files changed, 1293 insertions(+), 21 deletions(-)
```

**关键读数**：
- **10 个实现文件被改**，且落点含 **`code/engine/**`（4 个）**、`code/life/**`（3 个）、`code/orchestration/**`（2 个）、`code/config/**`（1 个）；
- **6 个新测试文件**全部为纯新增，无删除；
- ⇒ **`code_sha` 必变**（任何等价性结论都不得沿用旧 `FP` 内容 sha）。

## 4. 结论（分两层，不得合并成一句）

**第一层 — 机械可行性：可行。**
1 处冲突且在数据文件；代码自动合并；无文件删除。⇒ **"合并会炸"不成立**。

**第二层 — 行为等价性：仍未证明，且不能由第一层推出。**
- 合并后的 `code/` 包含 **10 个实现文件差异**，其中 `engine/kernel.py`、`engine/perceive.py` 属**执行路径核心**；
- "默认全关 ⇒ 事件流全等"这条**只能实测**，理由：开关读取路径、默认值解析（如 `dialogue_repair.json` 有 6 行改动）、事件序列化顺序，都可能因代码路径不同而产生差异，**逐字节相同不是充分条件**；
- `3be` 的"`efcf441 ↔ 8a58fef` 仅多一个不被导入的脚本"这条**只覆盖 A 场景（分支内追加）**，**不覆盖 B 场景（合并进 master）**。

⇒ **合并前必须做**：mock 同参数（默认全关）`A.jsonl`（master 侧基线）vs `B.jsonl`（合并后）→ `tools/d9z/compare_chain.py` 要求 `identical=true` / `first_divergence=null`；`FP` 只**同 rev 自比**。

## 5. 本件状态

- **未合并**：`feat/rift-events` 仍在 `efcf441`；本件只用 `merge-tree` 算了个临时树，**未改任何分支/index/工作区**；
- **未跑批**：起草时检测到外部臂在跑（`orchestration run ... r1-encounter-master ... 16x60`），故**未起任何跑批**；
- 本件**不主张**任何"合并安全"结论，只报实测事实与**待证明项**。

> **sha 声明**：本件提到的一切 `d7bb9737（临时树·非当前版）…`（含 `d7bb9737cc9b3784ff3a4ca41eac880ff8479518（临时树·非当前版）`）均为 `git merge-tree --write-tree` 的输出——**一个未被任何 ref 指向的临时树**，不是历史版、不是分支头、不是当前版。


## 6. 🔴 关键发现：这次合并携带的是**三个特性**，不是"一个 rift"

上节把合并差异统称"rift 的贡献"，**这个说法不成立**。实测（`git grep`）：

```
git grep -c "HITT_INTRA_ROUND_VISIBILITY" origin/master -- code/    → 空（0 命中）
git grep -c "HITT_INTRA_ROUND_VISIBILITY" <merged>    -- code/    → code/engine/perceive.py:1
```

⇒ **`master` 上根本没有 D9z 的同轮可见代码**；合并树才第一次把它带进来。合并带来的 10 个实现文件改动里，至少包含：

| 特性 | 进入 master 的证据 | 状态 |
|---|---|---|
| **D9z 同轮可见** | `code/engine/perceive.py` 新增 `INTRA_ROUND_ENV = "HITT_INTRA_ROUND_VISIBILITY"` | master **无**，本合并**首次**带入 |
| **DR 可分离化** | `code/life/dialogue_repair.py`（+100）、`code/config/dialogue_repair.json`（6 行：`repair_ask`/`record_only`/`pick_mark`） | 同理首次带入 |
| **rift 事件** | `code/engine/events.py`、`code/engine/replay.py`、`code/life/agent.py` 的 `RIFT_*` | 同理首次带入 |

### 6.1 由此推翻一条归因

**不能再说"`A vs B` 不等 ⇒ 是 merge 的锅、与特性无关"。** 准确表述只能是：

> `A vs B` 不等 ⇒ 差异来自**"这次合并带进来的全部改动"在默认全关下的行为**；
> 具体归因必须先落到**文件/符号**：是被合并特性的"默认关不彻底"，还是纯代码路径重构的副作用。

### 6.2 更重的一条：D9z 的判定与本合并的关系

D9z 判定「通过」是在**分支**上跑的（实现基 `cef1c58`）。由于 `master` 至今不含 `HITT_INTRA_ROUND_VISIBILITY`：
- **`master` 上的任何一批（含外部臂 `r1-encounter-master`）都不带 D9z 代码**；
- ⇒ **D9z 的 PASS 不能自动转写为"master 具备该能力"**；合并后必须在合并树上**重跑一次三档读数**，才能说"master 上 D9z 成立"。

### 6.3 对等价性证明的直接影响

`A ≡ B`（默认全关逐行全等）**从"可期望"降级为"待验证，且很可能不成立"**：三个特性同时进树，只要其中任一在默认关下仍有路径差异（例如 `dialogue_repair.json` 的 6 行改动改了默认值解析），A/B 就会分叉。**分叉本身不是失败，是数据**——它告诉我们"默认关不彻底"发生在哪一处。

## 7. 本节的边界

- 上述全部来自 `git grep` / `git diff`，**未运行任何代码**；
- "master 无该代码"是**当前 `origin/master` 状态**的事实，**不评价**为何如此（可能是分支未合并、也可能是别的路径）；
- 本件**仍不主张合并是否安全**，只把"合并携带什么"说清。

## 率的定义

**本件不新增任何率**（只读可行性实测件，无分子分母计数需求）。

| 率名 | 分子 | 分母 | 计算式（含边界） | 纳入排除 |
|---|---|---|---|---|
| 无（本件只报文件数与增删行数） | 不适用 | 不适用 | 不适用 | 不适用 |

## 外推与假定

**本件不做外推**。所有读数均为 `git diff --stat` / `git merge-tree` 的直接输出。

| 外推式 | 假定不变的量 | 值来源 |
|---|---|---|
| 无（只报实测） | 不适用 | 不适用 |

## 复算命令

```bash
git merge-tree --write-tree --name-only origin/master efcf441
git diff --stat origin/master efcf441 -- code/          # 27 files / 1339+ / 37814-
git diff --stat origin/master d7bb9737cc9b3784ff3a4ca41eac880ff8479518（临时树·非当前版） -- code/   # 16 files / 1293+ / 21-
```
