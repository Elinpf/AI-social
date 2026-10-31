# D9t 起跑阻断 B-1：ON 臂代码基线必须是 `f2b3230d`，**不是 `origin/master`**

> 性质：**阻断记录（blocker）**。本件不立判据、不改阈值；只说明"当前实现建在错的基线上"以及为什么。
> 发现者：TeamLeader（自查时读 OFF 臂的 `launch_cmd.txt` / `switch_proof.txt`）｜2026-10-31 10:1x
> 归属：**这是 Leader 的错**——预登记写"OFF = 复用 `d9s-on2`"，但没人去读"这个臂是哪个 commit 跑的"。

## 1. 事实（全部可复算）

`v2/evidence/d9s-on2_n16r24_s42/launch_cmd.txt`：
```
arm=on2 out=.../.worktrees/d9s-syntax-diversity/runs/d9s-on2_n16r24_s42 seed=42 agents=16 rounds=24
HEAD=f2b3230d8f456aa587cd5ef4f7e0fd79f466bf8a
LIFE_PROMPT_NARRATION=1 ROTATION=1 ACTION=1 SYNTAX=1
```
`switch_proof.txt`（`/proc/<pid>/environ` 真值）：
```
LIFE_PROMPT_NARRATION_ROTATION=1
LIFE_PROMPT_NARRATION_SYNTAX=1
LIFE_PROMPT_NARRATION=1
LIFE_PROMPT_NARRATION_ACTION=1
```

⇒ **OFF 臂 = `feat/d9s-syntax-diversity @ f2b3230d` + 四个开关全开。**

## 2. 而 `origin/master` 没有这套代码

```bash
grep -rn "LIFE_PROMPT_NARRATION_SYNTAX" code/     # 空
git rev-parse origin/master:code/life/agent.py    # e23ae53d…（该时点 blob，非当前版）
git rev-parse feat/d9s-syntax-diversity:code/life/agent.py  # fe473b9d…（该时点 blob，非当前版）
git merge-base --is-ancestor feat/d9s-syntax-diversity origin/master ; # rc=1（不在 master）
```
⇒ **D9s 的 S-1/S-2（`SYNTAX`）、`ACTION` 三个开关从未进过 master。**

## 3. 因此当前实现（`feat/d9t-openings @167cb41`）基线错误

- `167cb41` 建在 `origin/master` 上 ⇒ 它的 OFF 路径产出的是 **master 版** prompt；
- 而预登记要配对的 OFF 臂产出的是 **f2b3230d 版** prompt；
- ⇒ **两者本来就不是同一物**。此时"OFF 逐字节等价"验得再好，也只是证明了"`167cb41` 没改 master 的行为"，**与配对链无关**。

**结论：`167cb41` 不能用于 D9t 起跑；实现必须在 `f2b3230d` 之上重做（或把 d9s 分支并进 master 后再做）。**

## 4. 正确做法（二选一，均由 Leader 决定后再派件）

| 方案 | 内容 | 代价 |
|---|---|---|
| **P-A（推荐）** | 从 `feat/d9s-syntax-diversity @ f2b3230d` 开新分支 `feat/d9t-openings-2`，把 `167cb41` 里那段 `OPENINGS` 逻辑**移植**过去；等价性对比对象改为 **`f2b3230d` ↔ 新分支** | 一次移植 + 一轮复核；基线干净 |
| **P-B** | 先把 `feat/d9s-syntax-diversity` 并入 master（解决发布链缺口），再在其上做 D9t | 合并面大，且会改变 master 上 `agent.py` 现状，需另做回归 |

## 5. L1 验收口径必须改写（原口径失效）

原文写「OFF 复用必须有内容寻址证明：`narration_tail` 两份 + 完整 prompt fixture `sha256`」——**方向对，比较对象错**。改为：

1. 比较对象 = **产生 OFF 臂的那个 commit（`f2b3230d`）**，不是 `origin/master`；
2. 证据 = 同一 fixture 下，`f2b3230d` 与 ON 分支**在 `OPENINGS` 未设/`=0` 时**的完整 prompt `sha256` 相等；
3. 并附 `switch_proof` 级别的东西：ON 臂起跑时 `/proc/<pid>/environ` 的**四个开关 + `OPENINGS`** 真值。

## 6. 附带发现（记一笔，不在本实验范围）

`v2/evidence/d9s-on2_n16r24_s42/` 目录**没有 `meta.json`**（只有 `launch_cmd.txt` / `run_batch.log` / `run.jsonl` / `switch_proof.txt`）。
⇒ 凡引用"该臂 `code_sha`"的地方，只能引 `launch_cmd.txt` 里的 `HEAD=f2b3230d`，**不得写"meta.json 的 code_sha"**（该文件不存在）。

## 7. 教训（写进方法论）

> **"复用旧臂"不是"引用一个目录"，是"引用一个 commit + 一组 env"。**
> 不读 `launch_cmd.txt` / `switch_proof.txt` 就宣布"OFF 已就位"，等于用一个不知道出处的数字做基线。

## 8. 复核方结论与此阻断的关系（必须同屏，防误读）

`repro-verifier` 已对 `167cb41` 出独立复核件 `v2/evidence/d9t-167cb41-impl-verified-by-verifier.md`（`e73e4d47…` / 108 行），四项 + 反向检查全 PASS，并写下闸门句「**这些证据足以支撑两臂配对链**」。

**该结论在本件之前成立，在本件之后必须改写**：

| 命题 | 真值 |
|---|---|
| `167cb41` 未改变 **`origin/master`** 的 OFF 行为（6 组逐字节 + 3 hunk 全 append） | **真**（复核 PASS，且用结构证明而非抽样） |
| **OFF 臂 `d9s-on2` 的产出 = `origin/master` 的产出** | **假**（它是 `f2b3230d` 跑的，见 §1） |

⇒ **"足以支撑配对链"依赖一个为假的前提**。正确表述应为：
> **在"OFF 臂 = `origin/master` 代码"这一前提下，证据足以支撑配对链；而该前提为假 ⇒ 结论撤回，须在 `f2b3230d` 之上重做实现与复核。**

这不是复核方失职：**他核的是"分支有没有改 master 的行为"，这件事他核对了**；错的是**派件时给的比较基准**（Leader 的责任，见件头）。

## 9. 反向收获：两个可以直接沿用的结论

1. **`narration_enabled()` 在 env 完全未设时读 `code/config/life_v2.json::prompt.narration.enabled`（现值 `true`）⇒「未设」= ON**。所以真值表里「未设」与「`=1`」输出相同（98/105）是设计，不是 bug。**起跑时必须显式 `LIFE_PROMPT_NARRATION=1`，不得靠"未设"。**
2. 复核方用的**结构证明**（`grep -c "^-[^-]"` = 0、3 个 hunk 全为 append）比"抽一条比 hash"更强，建议固化为 L1 的可接受证据形式之一。

## 10. 基准错位的量化（`repro-verifier` 独立复算，Leader 复核一致）

```bash
git diff --stat origin/master f2b3230d -- code/
# 14 files changed, 435 insertions(+), 37795 deletions(-)
```

| 方向 | 量 | 含义 |
|---|---|---|
| `+435` | `f2b3230d` 有、master 没有 | 含 **`SYNTAX` 整套**（D9s 的 S-1/S-2） |
| `−37795` | **master 有**、`f2b3230d` 没有 | master 后来 30+ 提交的功能 |

⇒ 若在 master 上做 D9t，两臂至少差 **三样**（`OPENINGS` + `SYNTAX` + 37795 行功能差）——
**那不是"双干预"，是"多变量"，任何差值都不可归因。** 这是 P-A 为唯一可行路径的**量的依据**，不再只是"看起来更干净"。

## 11. 一个必须分清的区分（`repro-verifier` 主动指出，Leader 采纳）

| 命题 | 真值 | 用途 |
|---|---|---|
| `05526e0d` 与 `f2b3230d` 之间 `code/` 零 diff ⇒ **D9s 线内部两臂运行同源** | **真** | 支撑 D9s 的臂间可比 |
| `origin/master` 与 `f2b3230d` 同源 | **假** | 不可用于 D9t 配对 |

⇒ **"同一分支内两臂同源"≠"不同分支同源"。** 今晚这两件事被混成了一件，是 B-1 的直接成因。

## 12. 下一轮复核的三道前置（`repro-verifier` 提出，Leader 采纳为派件必附条件）

派 P-A 复核件时，对方须**先跑**：
1. `launch_cmd.txt` 里的 `HEAD=` 与派件 sha **逐字相同**；
2. 新分支以 `f2b3230d` 为祖先（`git merge-base --is-ancestor`）；
3. `git diff --stat f2b3230d..新分支 -- code/` **只含 `OPENINGS` 相关**，无 `SYNTAX` 增减。
**任一不过 ⇒ 直接 `CANNOT-VERIFY`，不跑矩阵**（避免再一次"证明了一个错前提"）。

## 13. 责任归属（写清，避免"全算派件错"）

- **Leader**：预登记写"复用 `d9s-on2`"却未读该臂 `launch_cmd.txt`；派件时把比较基准写成 `origin/master`；
- **复核方**：L1 原文写的是"与 **`d9s-on2` 那版代码**逐字节相同"，他引用了这句话但未核"那版代码是哪个 commit"——**核了动作，没核主语**。
⇒ 两边各错一层；**制度修法在 §12 的三道前置**（把它变成"派件必附 + 复核必跑"的机械动作）。
