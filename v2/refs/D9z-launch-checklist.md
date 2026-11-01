# D9z 起跑清单（L0–L7）：同轮往返 · 起跑前置 / 跑中留证 / 跑后读数

> 配套：`v2/refs/D9z-prereg-intra-round-visibility.md`（`FROZEN v3.3`，`f01488138a946e92…`）。**判据只在预登记定义一次，本件不复述阈值**，只写"怎么验"。
> 纪律：**跑批串行**（`pgrep` 确认）、**跑批期间禁改 `code/life|orchestration|config|engine`**、**真 LLM 须验真**、**结论必须可复算并绑 sha**。
> 本件每条都是"能数就写命令"，不写"请注意"。

## L0 串行门（缺一不起跑）

```bash
# 主门（唯一有效）：launcher 形态
pgrep -af 'run_module\("orchestration"' | grep -v "pgrep" 
# 辅助门：只看 comm=python3 的，避免把"包含该字面量的检查命令"当批
ps -eo pid,comm,args | awk '$2 ~ /^python3/ && /orchestration/'
```
**任一非空即不起跑。**

> ⚠ **门本身的三个缺陷（2026-11-01 实测，两条来自 `dialogue-core-dev` 现场取证）**：
> 1. **`pgrep -af 'orchestration [r]un'` 对 launcher 形态漏检**：启动器是 `python3 -c` + `runpy.run_module("orchestration")`，
>    命令行里没有 `orchestration run` 连续串（`sys.argv` 为 `["orchestration", "run", …]`，带引号逗号）。
>    实测：真批在跑时该门返回**空**。⇒ 只看它=误判"没有批在跑"，可能并发起跑写坏同一 `side-root`。
> 2. **门 A 可能自匹配**：若包装命令的文本里出现**字面** `orchestration run`（例如 `sh -c 'ps aux | grep "orchestration run"'`），
>    该 `sh -c` 进程自身会被抓进来。**`[r]` 手法只能防 `pgrep` 自身，防不住 `sh -c` 包裹的整段文本。**
>    （Leader 用 `bash -c 'pgrep -af "orchestration [r]un"'` 复现为 **0 命中**，故该形态取决于包装命令写法；但风险真实，须防。）
> 3. **起跑时刻的串行性不可事后证明**：若起跑时只跑了失效的门，就只能给**旁证**（① `side-root` 起跑前不存在；
>    ② 事后主门只命中本批一个 pid），**不得写成"当时已验证串行"**。
>
> 结论：**主门只认 `run_module("orchestration")` 那条**；门 A 降为辅助且必须看"是不是 `python3`"。
> 这条属"**检查器的沉默 ≠ 没有东西**"：**门返回空，要先验证门自己能看见东西。**

## L1 代码身份门

```bash
git -C <worktree> rev-parse HEAD                     # 必须 = 实现分支上被复核通过的那个 sha
git -C <worktree> diff <cef1c58> -- code/ config/   # 只允许出现"可见性上界"及其接线
git -C <worktree> status --porcelain                 # 期望空
```
**闸门**：`HEAD` 与复核件记录的 sha 不等 ⇒ 不起跑；`diff` 出现旁白/数值/prompt 改动 ⇒ 不起跑（单变量破了）。

## L2 开关取证门（`/proc` 原始输出，不手写"应该=1"）

```bash
tr '\0' '\n' < /proc/<pid>/environ | grep -E 'NARRATION|ROTATION|ACTION|SYNTAX|OPENINGS|<新开关>'
```
**闸门**：新开关 ON 臂必须**显式存在且为目标值**；`NARRATION/ROTATION/ACTION/SYNTAX/OPENINGS` 五点沿用 D9t 口径。**缺一 ⇒ 该臂 `CANNOT-VERIFY（未采集）`**，不得事后补写。

## L3 代码指纹门（补丁版 `FP`）

```bash
bash tools/tree_fingerprint.sh world   # 输出 files= / sha256= / mode=（**同源**，见下）
# 跑完后同一条命令再跑一次
```

**闸门**：`sha256` 不等 ⇒ 判"跑批期代码被动过"，**整批不得用于判定**。

**报 FP 必须写三元组，且同一行**：
```
FP = (rev=<分支名>@<commit>, files=<N>, sha256=<…>)
```
**为什么必须带 rev**（2026-11-01 由 `repro-verifier` 实测指出）：文件数**随 rev 变** ——
`cef1c58` = **282**、`feat/d9z-intra-round` = **283**、`origin/master` = **284**。
**三个数都"对"**，只写 `283` 的话，下一个人在 master 上复算得 `284` 会判"文件集变了"，
其实是**换了 rev** —— 这正是 `FP` 最典型的一次假报警。

**工具侧已改（同日）**：`tools/tree_fingerprint.sh` 旧版**只输出 sha，文件数在管道里被丢掉** ⇒
"起跑时贴文件数"只能人另跑一条命令手贴，两个数来自两条命令/两个时点就可能对不上。
现版本把清单先落临时文件，**指纹与文件数都从同一份清单数出来**，并**双向自验**：
- 在 `cef1c58` 树上跑得 `files=282` / `sha256` 内容 sha·实测值 `fd8a8f98…`，与旧版已知值**逐字节相同**（向后兼容）；
- 文件数 `<100` 直接 `FATAL / rc=3`，杜绝"空目录稳定指纹"。

**另**：`world` 段计入集 = `git ls-files -- code config` + 同名 untracked、**排除 `code/frontend/**`**；
**根 `tools/` 不在 `world` 段内**（`^tools/` 命中 0 行）⇒ 报范围时不得写"含 tools/d9z"。

## L4 规模门（`n` 与配置）

| 项 | 要求 |
|---|---|
| `agents × rounds` | `16 × 56`（预登记推荐值；改 `rounds` 只准往上加） |
| `seed` | `42` |
| `config/places.json` | sha256 与两臂一致 |
| 起跑输出目录 | 带 run-id，**永不覆盖** |

## L5 真调用验真门

```bash
obs llm-cost --run <out>                 # 不带 --require-provider（该开关现为工具 bug，见下）
```
- **已知工具 bug**：`--require-provider` 触发 `obs/llmcost.py:79` `dict<=int` TypeError（`rc=1`）。**这是工具问题，不是跑批问题**；用它时须在件里注明，不得因此判该批无效。
- **闸门**：`tools` 侧 `dialogue` 目的的回放数必须为 **0**（D9t 实测 `dialogue` 零回放）；总账 `calls` 与 `run.jsonl` 的 `LLM_CALL` 事件数**必须相等**。

## L6 读数门（跑后算，**顺序不许调**）

```text
① 三档先算，且先做自校验：gap=0 / gap=1 / gap≥2 三档之和 == 相邻对总数（不等 ⇒ 判数据有问题，停止读数）
② 再算 B：gap≥2 占比，分母用本臂相邻对总数
③ 再算 A：gap=0 绝对条数
④ 最后才碰护栏（n、config sha、degraded）
```
理由：**先算占比、再回头解释三档之和不为总数**，等于拿一个算不通的数去判。D9t 的教训是"读数顺序错了会把结构性事实读成效果"。

## L7 结构同门（**本件新增，D9t 时没有的坑**）

OFF 臂（复用 `v2/evidence/d9t-on_n16r24_s42/run.jsonl`，`af4c44d11dd22eb8…`）已实测：**125 对全部同 `thread_id`，且 `turn_index(本条) = turn_index(父条) + 1`（125/125）**。
⇒ 本批 `gap` 量的是**轮次距离**，不是"是否下一句"。

**闸门**：ON 臂读取数时**必须同屏报**这两项：

| 项 | OFF 实测 | ON 必须报 |
|---|---|---|
| 同 `thread_id` 占比 | 125/125 | 本臂分子/分母 |
| `turn_index(本条)=父+1` 占比 | 125/125 | 本臂分子/分母 |

**若 ON 臂这两项与 OFF 显著不同 ⇒ 两臂的"结构混合"不同，`gap≥2` 占比不可直接比较**（须同屏写明并降为"结构性差异"，不得写成效果）。

## 率的定义

**本件不定义率**：三个率的分子/分母/计算式/纳入排除**只在预登记 §1 定义一次**（SSOT）。本件只复述"名字 → 在哪定义"，防止两处漂移：

| 率名 | 分子 | 分母 | 计算式（含边界） | 纳入排除 |
|---|---|---|---|---|
| `gap` 相邻对 | 见预登记 §1 第 1 行（本件不重述） | 见预登记 §1 | 见预登记 §1 | 见预登记 §1 |
| `gap` 三档条数 | 见预登记 §1 第 2 行 | 见预登记 §1 | 见预登记 §1（含三档和自校验） | 见预登记 §1 |
| `gap≥2` 占比 | 见预登记 §1 第 3 行 | 本臂相邻对总数 | 见预登记 §1 | 见预登记 §1 |

## 外推与假定

**本件不做任何外推**（无规模推算、无墙钟推算、无倍率换算），故无"假定不变"项。凡需要外推的量，一律回预登记 §2。

| 外推式 | 假定不变的量 | 值来源 |
|---|---|---|
| 无（本件只写"怎么验"） | — | 不适用；见预登记 §2 |

## L8 收尾门

- `run.jsonl`：行数 / 字节 / `sha256` 三值齐报；
- `run.log`：`n_agents / rounds / events / seconds` + `chain_ok / replay_parity / conservation_ok` 原样抄；
- `launch_cmd.txt`：`HEAD` / `started_at` / `finished_at` / `rc`；
- **空 `fault.log` 不等于"没有长尾"**：D9t 实测有 2 次 `Timeout (0:10:00)` 全线程快照落在 `run.log`，`fault.log` 仍为 0 B（`dump_traceback_later` 单定时器语义，后一次取消前一次）。⇒ **必须查 `run.log` 里的 `Timeout` 行**。

## 9. 边界

1. 本件**不含任何阈值**，阈值只在预登记里；本件与本件清单**都不得用于判定**；
2. `L7` 是新发现的坑（`gap` 语义 = 轮次距离），在 D9t 之后才发现，**不得回填改写 D9t 判定的任何结论**；
3. `obs llm-cost --require-provider` 的 bug 属工具侧，修复后应重跑该命令并把 `rc` 记入件；**在修复前，凡引用该命令 `rc=1` 的地方都必须注明"工具 bug"**。
