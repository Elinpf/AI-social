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
git rev-parse origin/master:code/life/agent.py    # e23ae53d…
git rev-parse feat/d9s-syntax-diversity:code/life/agent.py  # fe473b9d…
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
