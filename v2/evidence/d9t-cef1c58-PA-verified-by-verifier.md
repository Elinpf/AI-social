# D9t P-A 实现独立复核：`feat/d9t-openings-2 @ cef1c58`

> 对象：`cef1c58c448d400c0…`（父 = **`f2b3230d8f456aa5…`**，单提交 `feat(d9t): 从 f2b3230d 起重做 D9t（P-A 方案）`）
> 件名：`v2/refs/D9t-prereg-opening-menu.md` = `954ee2c9e5f963be…`（A2）；`v2/refs/D9t-launch-checklist.md` = `d28d9d0011f57685…`（L1–L7）；`v2/refs/D9t-blocker-B1-wrong-code-base.md` = `9db4e9cd…`
> 作者：`repro-verifier`｜2026-10-31｜**只读**：未改代码、未跑批、未 push
> 复核时点：`origin/master = 16874e2a74a75596…`

## 0. 五项结论 + 三元组口径

**三元组（写死，与基准矩阵同口径）**：`HITT_WORLD_SEED` **未设** / `agent_id = "P004"` / `round_no = 7`；每组合**独立进程**。

| # | 项 | 判 |
|---|---|---|
| 1 | **§12 三道前置** | **PASS**（①`launch_cmd.txt HEAD`=`f2b3230d` ②`is-ancestor` ✓ ③差异只在 `agent.py`+新测试，且全在 OPENINGS 相关函数内——含 9 行**改写**，见 §1） |
| 2 | **等价（四开 + `OPENINGS` 未设/`=0`）** | **PASS** —— 与 `f2b3230d` **同值同 sha**：`200/206`、`f2c994a1cbb7`/`f50325c7b187` |
| 3 | **反向检查（`OPENINGS=1` ≠ 基线 + 长度可解释）** | **PASS** —— `422`/`429`（`0fcd560dd1de`/`7c7fe54096a5`）；长度差 **+222 / +223 分解到逐字**（§3） |
| 4 | **优先级（`O=1` 时 `R` 无效）** | **PASS** —— `R` 未设 vs `=0` → 均 `422/429`、sha 完全相同 |
| 5 | **仪器零 diff + 结构证明** | 仪器 **PASS**（`tools/`+`code/config/` `--stat`/`--numstat` 双空、删除文件 0）；结构 **"删除行 0" 不成立（9 行）**，改用**函数级证明**（§5），结论仍 PASS |

**闸门句**：**这些证据足以支撑两臂配对链（OFF 复用 `f2b3230d` + ON `cef1c58`）。** 与上一轮不同，**这次基准经过核实**：`d9s-on2/launch_cmd.txt` 的 `HEAD=` 确为 `f2b3230d`，且 `cef1c58` 的父提交**就是** `f2b3230d`（不是 master）。

## 1. 前置三道（含一处必须诚实说明的不符）

```
$ git show origin/master:v2/evidence/d9s-on2_n16r24_s42/launch_cmd.txt | grep HEAD
HEAD=f2b3230d8f456aa587cd5ef4f7e0fd79f466bf8a          ← ① 基准逐字相同 ✓

$ git merge-base --is-ancestor f2b3230d cef1c58 → rc=0  ← ② 以基准为祖先 ✓
$ git log --oneline f2b3230d..cef1c58
cef1c58 feat(d9t): 从 f2b3230d 起重做 D9t（P-A 方案）     ← 只有 1 个提交 ✓（无 master 行混入）

$ git diff --stat f2b3230d cef1c58 -- code/
 code/life/agent.py                         |  80 ++++++++++++++--
 code/tests/test_life_narration_openings.py | 133 +++++++++++++++++++++
 2 files changed, 204 insertions(+), 9 deletions(-)      ← ③ 有 9 行删除
```

**诚实说明**：派件第 5 项要求"删除行数 == 0"，**实测为 9**（上一版 `167cb41` 是 0，P-A 版不是）。
但 9 行**全部**落在三个 OPENINGS 相关函数里（为加 `drop_s1` 参数与短路 `ROTATION` 所必需）：
```
hunk @@ -246,18 +246,74 @@   → syntax_clause / _apply_syntax_clause 的签名行与 return 行（6 行）
hunk @@ -272,7  +328,9  @@   → narration_tail 的 if not narration_rotation_enabled()（1 行）
hunk @@ -280,8  +338,12 @@   → narration_tail 尾部的 _apply_syntax_clause 调用与 return（2 行）
```
⇒ **判据口径建议改**（不是实现问题）：把"删除行 0"换成 **"改动函数 ⊆ {`narration_tail`, `syntax_clause`, `_apply_syntax_clause`} ∧ 新增函数 ⊆ {`openings_enabled`, `openings_clause`} ∧ 旧函数无删除"**——即 §5 的函数级判据。

## 2. 表 1：等价（四开关全开：`N=1,R=1,A=1,S=1`）

| 组 | kind | `f2b3230d`（基准） | `cef1c58`（新） | 判 |
|---|---|---|---|---|
| `OPENINGS` 未设 | initiate | **200** / `f2c994a1cbb7` | **200** / `f2c994a1cbb7` | ✅ 逐字节同 |
| `OPENINGS` 未设 | reply | **206** / `f50325c7b187` | **206** / `f50325c7b187` | ✅ |
| `OPENINGS=0` | initiate | — | **200** / `f2c994a1cbb7` | ✅ 与未设同 |
| `OPENINGS=0` | reply | — | **206** / `f50325c7b187` | ✅ |

⇒ 基准值与我在 `d9t-PA-baseline-matrix-f2b3230d-by-verifier.md` 预置的四开关全开行**完全一致**（`200/f2c994a1cbb7`、`206/f50325c7b187`），**无口径漂移**。

## 3. 表 2：反向检查 + 长度差逐字分解（本轮核心）

| 组 | kind | len | sha12 |
|---|---|---|---|
| 四开 + `O=1` | initiate | **422** | `0fcd560dd1de` |
| 四开 + `O=1` | reply | **429** | `7c7fe54096a5` |
| 四开 + `O=1` + `R=0` | initiate | **422** | `0fcd560dd1de` |
| 四开 + `O=1` + `R=0` | reply | **429** | `7c7fe54096a5` |

**`≠ 基线` ✓（422≠200、429≠206）。下面把 +222 / +223 分解到逐字**（`difflib.SequenceMatcher`，非估算）：

**initiate：+222 = +1 − 45 + 266**
| 变化 | 内容 | 字数 |
|---|---|---|
| 示例句替换 | `低头拢了拢衣襟`(7) → `把围裙往腰后一掖`(8) | **+1** |
| **删 S-1 禁令句** | `；旁白不要总是用「把」或「拿、用」开头——每三条旁白最多一条这样起头，其余请换个起头方式；` | **−45** |
| 追加 OPENINGS 段 | `\n旁白第一句可以从这些方式里选…⑧ 动作带对象…\n上面这 8 种尽量轮着用…\n旁白写完整分句（≥7 个字），不写电报体。` | **+266** |

**reply：+223 = +2 − 45 + 266**（示例句 `抬眼望了望日头`(7) → `低头刨木，木屑卷起`(9)，+2；其余同）

⇒ **`OPENINGS=1` 的 +222/+223 完全由"撤 S-1 禁令句 −45 + 追加段 +266 + 示例句回 D9i 原句"三项解释**，与 Leader 裁决（`drop_s1=True`）**逐字吻合**，无未解释余量。
**旁证**：`len(openings_clause()) = 266`（实测），`len(S1_CLAUSE) = 44`，`44+1("；") = 45` ⇒ `266−45 = 221`，再加示例句差 +1/+2 ⇒ 222/223 ✓

## 4. 优先级验收

`O=1` 时 `R` 未设 vs `=0`：`422/422`、`429/429`，**sha 完全相同** ⇒ `OPENINGS` 短路 `ROTATION` ✓（代码层对应 `if not narration_rotation_enabled() or openings_enabled():`，实测与代码一致）

## 5. 仪器零 diff + 函数级结构证明（替代"删除行 0"）

```
$ git diff --stat   f2b3230d cef1c58 -- tools/ code/config/   → （空，0 行）
$ git diff --numstat f2b3230d cef1c58 -- tools/ code/config/  → （空，0 行）
$ git diff --diff-filter=D --name-only … | wc -l              → 0
```

**函数级比对（`ast` 提取每个函数源码逐一对齐，73 个共有函数）**：
```
旧有新建（被删函数）: []                                  ← 无函数被删
新增函数            : ['openings_clause', 'openings_enabled']
变更函数            : ['_apply_syntax_clause', 'narration_tail', 'syntax_clause']
未变函数            : 70 / 共有 73
```
⇒ **只有 3 个与 OPENINGS 直接相关的函数被改，2 个新增都是 OPENINGS 开关本身，其余 70 个函数字节未变**。
这比"删除行 0"**更精确**：它同时排除了"行数恰好抵消但逻辑被改"的可能。

**`code/` 全树只有 2 个文件变化**（`agent.py` + 新增测试），无其他文件 ⇒ 完整 prompt 的等价性由"70 函数未变 + 3 函数改动已被逐字等价实跑覆盖"结构蕴含。

**Leader 裁决一致性核验（`drop_s1`）**：
```
S1_CLAUSE 字面量：f2b3230d dc85c62b7417840f == cef1c58 dc85c62b7417840f   ← 一字未改 ✓
```
⇒ **"OFF 路径的 S-1 一字不动"成立**：`drop_s1` 只是**不插入**该常量（`return s2`），**没有修改常量本身**；`O` 关时 `drop_s1=False` ⇒ 仍返回 `S1_CLAUSE + "；" + s2`，与基准逐字节同（表 1 已证）。

## 6. 关于 `204/211` 的口径（Leader 已发现，我复核确认）

Leader 报 `dialogue-core-dev` 的"四开基数 204/211"，在 `seed ∈ {未设,0,42} × agent ∈ {未设,P000..P004} × round ∈ {未设,0,1,3,5,7,11,24}` 网格里**未命中**。我在本标准口径（`未设/P004/7`）下四开实测 **200/206**，与基准一致。
⇒ **`204/211` 是另一个未声明口径下的数，不能与本表并列**。本件所有数字均绑定三元组 `(未设, P004, 7)`。

## 7. 我做了什么 / 没做什么

- **做了**：前置三道（含 `launch_cmd.txt` 回读）、导出两棵树、四组合 × 2 kinds 实跑、`difflib` 逐字分解长度差、`ast` 函数级比对（73 函数）、`S1_CLAUSE` 字面量比对、`tools/`+`code/config/` 三面零 diff 检查、`is-ancestor`/提交数。
- **没做**：不改代码、不跑批、不 push；**不采信** Leader 与 `dialogue-core-dev` 的任何数字（全部重跑）。
- **没核**：`code/tests/test_life_narration_openings.py` 的断言质量（本轮五项不含；如需我可另开一件）；实际跑批行为（未跑批）。
