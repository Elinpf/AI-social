# D9z 起跑清单（L0–L7）：同轮往返 · 起跑前置 / 跑中留证 / 跑后读数

> 配套：`v2/refs/D9z-prereg-intra-round-visibility.md`（`FROZEN v3.3`，`f01488138a946e92…`）。**判据只在预登记定义一次，本件不复述阈值**，只写"怎么验"。
> 纪律：**跑批串行**（`pgrep` 确认）、**跑批期间禁改 `code/life|orchestration|config|engine`**、**真 LLM 须验真**、**结论必须可复算并绑 sha**。
> 本件每条都是"能数就写命令"，不写"请注意"。

## L0 串行门（缺一不起跑）

```bash
pgrep -af "orchestration [r]un"      # 期望：空
```
**非空即不起跑**。D9t 曾因同一脚本被启动两次写同一 `out/side-root`，取证被覆盖（留档 `/tmp/D9T_ON_TAINTED_1793434444`）。

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
bash scripts/FP before      # 期望：先打印文件数，<100 即 FATAL
# 跑完后
bash scripts/FP after       # 必须与 before 逐字节相等
```
**闸门**：不等 ⇒ 判"跑批期代码被动过"，**整批不得用于判定**。

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
