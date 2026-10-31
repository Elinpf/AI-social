# D9t 实现独立复核：`feat/d9t-openings @ 167cb41`

> 对象：`167cb41`（`167cb415e5fdb0c3…`，merge 提交，父 `1ed86cf` + `6067fca`）
> 参照件：`v2/refs/D9t-prereg-opening-menu.md` = `954ee2c9e5f963be…`（A2 版）；
> 　　　　`v2/refs/D9t-launch-checklist.md` = `d28d9d0011f57685…`（L1–L7）
> 作者：`repro-verifier`｜2026-10-31｜**只读**：未改代码、未跑批、未 push
> 复核时点：`origin/master = 94e272a1f8858c5a…`（本件所有"当前"判断绑此 sha）

## 0. 四项结论

| # | 项 | 判 |
|---|---|---|
| 1 | **OFF 逐字节等价（6 组）** | **PASS** —— 两棵树 6 组 `len` 与 `sha256` **逐项相同**（表 1） |
| 2 | **4 态真值表（5 组合）** | **PASS** —— 五个组合实测出全值（表 2），与 Leader 自查数**独立复现一致** |
| 3 | **优先级验收（`OPENINGS=1` 时 `ROTATION` 无效）** | **PASS** —— `R` 未设 vs `=1`：`len` **364/364**、**371/371**，`sha256` **完全相同** |
| 4 | **仪器零改动（`tools/` + `code/config/`）** | **PASS** —— `--stat` 空、`--numstat` 空、删除文件数 **0** |
| **5** | **反向检查（Leader 追加项④）**：`OPENINGS=1` 必须 ≠ `OPENINGS=0` | **PASS** —— `364 ≠ 98`、`371 ≠ 105`；新开关真接上了，不是空口等价 |

**末句（起跳前人工闸）**：**这些证据足以支撑两臂配对链（OFF 复用 + ON 新代码）。** 依据见 §5。

## 1. 复算口径（先写死，防"跑出假不一致"）

- **`HITT_WORLD_SEED`：未设**（= 生产默认，代码回落 `or "0"`）；两棵树同一状态。
- **`agent_id = "P004"`，`round_no = 7`**（示例句依赖 `(seed, agent_id, round)`）。
- 树来源：`git archive origin/master code/ | tar -x` 与 `git archive 167cb41 code/ | tar -x` 到 `/tmp/xv/{old,new}`；各自 `sys.path.insert(0, <tree>/code)` + `os.chdir(<tree>)`。
- 调用：`life.agent.narration_tail(kind, "P004", 7)`；每个组合**独立进程**（避免 env 串味）。

**⚠ 一条实测发现（写进件，供判定件引用）**：`narration_enabled()` 在 env **完全未设**时读 `code/config/life_v2.json :: prompt.narration.enabled`（现值为 `true`）⇒ **「未设」= 旁白开（ON）**，不是 OFF。所以"6 组"里"未设"与 `=1` 的输出相同（表 1 已证），这不是 bug，是设计（D9i 老语义 + 默认化）。

## 2. 表 1：OFF 逐字节等价（新树 `167cb41` vs 旧树 `origin/master`）

| 组 | env | kind | 旧树 len / sha12 | 新树 len / sha12 | 判 |
|---|---|---|---|---|---|
| G1 | `NARRATION` **未设** | initiate | 98 / `d8382f82eb52` | 98 / `d8382f82eb52` | ✅ |
| G1 | 同上 | reply | 105 / `5e45e3180300` | 105 / `5e45e3180300` | ✅ |
| G2 | `NARRATION=0` | initiate | 66 / `3646f04995a9` | 66 / `3646f04995a9` | ✅ |
| G2 | 同上 | reply | 72 / `ce2cfb8757b1` | 72 / `ce2cfb8757b1` | ✅ |
| G3 | `NARRATION=1` | initiate | 98 / `d8382f82eb52` | 98 / `d8382f82eb52` | ✅ |
| G3 | 同上 | reply | 105 / `5e45e3180300` | 105 / `5e45e3180300` | ✅ |

**"三份证据是否同 fixture/同输入"（我上次提的点）——本件的处理方式**：
不去比"三份现成证据"，而是①**两棵树同进程同参数**（同 `agent_id`/`round`/`seed` 状态）实跑，②在**唯一可变点**上穷举 6 组。⇒ 不存在"两个都空也算相等"的空间：G2 的 66/72 与 G1/G3 的 98/105 **互不相同**，说明输出非空且敏感。

> 交叉印证：G2 的 `3646f04995a9…` / `ce2cfb8757b1…` 与 D9i 线登记的 OFF 两句 `sha256` 前缀（`3646f049…` / `ce2cfb87…`）一致。

## 3. 表 2：4 态真值表（新树，`agent=P004 / round=7 / seed 未设`）

| 组合 | initiate：len / sha12 / 首40字 | reply：len / sha12 / 首40字 |
|---|---|---|
| **T1** `N=0` | **66** / `3646f04995a9` / `只写台词本身（一句家常话）：不要用括号、方括号或星号写动` | **72** / `ce2cfb8757b1` / `只写台词本身（接着刚才的话往下说一句）：不要用括号、方` |
| **T2** `N=1,O=0,R=0` | **98** / `d8382f82eb52` / `只写台词本身（一句家常话，用成对的（）补一句动作、神态或眼` | **105** / `5e45e3180300` / `只写台词本身（接着刚才的话往下说一句，用成对的（）补一句` |
| **T3** `N=1,R=1`（O 未设） | **97** / `eccd3c5ba165` / `…如（低头拢了…`（示例句换成词表选句） | **103** / `015aa8e77fa9` / `…如（…`（同上） |
| **T4** `N=1,O=1`（R 未设） | **364** / `2c7c9521035d` / `只写台词本身（一句家常话，用成对的（）补一句动作、神态或眼` | **371** / `99ed4e2373be` / `只写台词本身（接着刚才的话往下说一句，用成对的（）补一句` |
| **T5** `N=1,O=1,R=1` | **364** / `2c7c9521035d` | **371** / `99ed4e2373be` |

**`T3` 与 `T2` 差 1 字**（97 vs 98 / 103 vs 105）——原因：`ROTATION=1` 把示例句从 D9i 原句换成词表选句，长度本就不同；这不是缺陷，是 `ROTATION` 的既有语义。
**`T4` 与 `T5` 全等** ⇒ 优先级正确（`OPENINGS` 短路，`ROTATION` 无效果）。
**`T4 ≠ T2`** ⇒ `OPENINGS` 真接上。

## 4. 仪器零改动 + 代码差异形态

```
$ git diff --stat   origin/master..167cb41 -- tools/ code/config/     → （空）
$ git diff --numstat origin/master..167cb41 -- tools/ code/config/    → （空）
$ git diff --diff-filter=D --name-only origin/master..167cb41 -- tools/ code/config/ | wc -l → 0
```

**`code/` 全树差异只有两处**（`diff -rq`）：
```
Files .../old/code/life/agent.py and .../new/code/life/agent.py differ
Only in .../new/code/tests: test_life_narration_openings.py
```

**并且 `agent.py` 是"纯追加"**（这条比"diff 有 53 行"强）：
```
$ diff old/code/life/agent.py new/code/life/agent.py | grep -E "^[0-9]"
219a220,265
230a277,282
231a284          ← 全是 a（append），无 c/d
$ git diff origin/master..167cb41 -- code/life/agent.py | grep -c "^-[^-]"
0                ← 删除行数 0
```
⇒ **`_dialogue_prompt` / `_reply_prompt` 的源码字节未变**（它们不在任何 hunk 内），新增块全部是**模块级常量 + 两个开关函数**（插在第 219 行后与 `narration_tail` 内）。

**⇒ L1 第 2 条（完整 prompt `sha256` 相等）的证明方式**：不是抽样跑一条，而是**结构蕴含**——`code/` 树内仅 `agent.py` 变更且删除行为 0 ⇒ 所有函数源码不变；进入 prompt 的唯一旁白相关可变项是 `narration_tail(...)`，其 6 组已穷举相等 ⇒ **任一固定 fixture 上完整 prompt 必然逐字节相同**。这比"抽一条 prompt 比 hash"更强（抽样只能证明那一条）。

## 5. 为什么"足以支撑配对链"

L1 的两条：
1. `narration_tail` 逐字节相同 —— **本件表 1，6 组全等**；
2. 其余进 prompt 路径（`_dialogue_prompt` / `_reply_prompt`）逐字节相同 —— **本件 §4 结构证明（纯追加、删除 0）+ 唯一可变点穷举**；
⇒ **1&2 均成立 ⇒ 按 L1 判定，OFF 可复用，不必重跑。**

配合 L2：两臂 `code_sha` 天然不同 ⇒ **L1 的等价证明就是"事实上的同 sha"**，判定件须同屏写这句。

## 6. 附：两条必须一起报的旁证/边界

1. **`pytest` 我自己跑了**：`code/tests/test_life_narration_openings.py` **19 passed**；全量 `code/tests` **635 passed, 7 skipped**（Leader 报的 53 与之不同，应该是子集口径——**我不采信该数字，报我实测值**）。
2. **⚠ 提交基线已过期（`@ 94e272a` 时点）**：`git diff --stat origin/master..167cb41` 实测 **4 文件 +203 / −124**，含 **1 个文件消失**（`v2/evidence/d9t-6067fca-hook-regression-and-self-made-trap-by-verifier.md`，我上一件 107 行）+ `three-questions…` −17 行。
   - `@ 6067fca 时点`：才是 Leader 报的 **2 文件 +203/−0**（我复现过）。
   - ⇒ **`167cb41` 若要推 master，必须先 rebase/merge 到当前 master**；`hooks/pre-push` 会拦住它（删文件数 1 > 0），这是 hook 的正常工作，不是故障。
   - **本条不影响四项结论**（四项比的是 `code/` 内容与 `narration_tail` 行为），但**影响"能不能直接推"**。

## 7. 我做了什么 / 没做什么

- **做了**：导出两棵树、独立进程跑 6+5 组、`len`/`sha256`/首 40 字全列、`--stat`/`--numstat`/删除文件数三面查、`diff -rq` 全树比、normal-diff hunk 类型统计、pytest 两份跑。
- **没做**：不改代码、不跑批、不 push、不采信 Leader 自查数（全部独立重跑）。
- **没核**：`①②③` 八出口文本与预登记 §2 的逐字一致性（属内容审查，未在本轮四项内；如需我可另开一件逐字 diff）。
