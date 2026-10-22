# D12-C 接线证明（OFF vs ON 两态渲染 + diff）

> 作者：`prompt-linguist` ｜ 2026-10-23 04:26 ｜ 基线树 **`3ec85a0`** 副本 `/tmp/t271-d12c`
> 目的：证明 `LIFE_PROMPT_D12C_SPECIFIC` **真的接到了两个 prompt 函数**，且 **OFF 态与基线逐字相同**。

## 1. 两态渲染（固定输入）

固定输入：`agent=P001`、`pid/partner` 取自 `build_world(seed=42, n=2)`、`template=gift`、`reply history` 单条固定文本。
渲染脚本：`/tmp/t271-d12c/code/render_d12c_prompt.py`（只读、不跑批）。

| 态 | 环境 | `prompt_fn_sha256`（两函数渲染合并） | 渲染文本 sha256 | 文件 |
|---|---|---|---|---|
| **OFF**（基线） | `env -u LIFE_PROMPT_D12C_SPECIFIC` | **`5cf08593d562dc09…`** | `027fb49d72789dc0dfcd660a74d988d9d3ca55c83af0a5e5d291bb06bb9cb1c8` | `v2/evidence/d12c_prompt_render_off.txt` |
| **ON**（处理） | `LIFE_PROMPT_D12C_SPECIFIC=1` | **`effc14dbffdb6865…`** | `488c2ba185ec152952e37d0e2f6cca3e46503fece5bdd5dea8e4f1daed656a39` | `v2/evidence/d12c_prompt_render_on.txt` |

⇒ **两态 sha 不同**，且差异**只在追加的两行**（见 §2 diff）。

## 2. 渲染 diff（**只有追加两行，无其它改动**）

```diff
--- d12c_prompt_render_off.txt
+++ d12c_prompt_render_on.txt
@@ 请用一句话自然地说点什么。
+这句里要有一个你此刻手上的具体器物或数（例：七钱、第三格、差三分钟、半指宽）。
+如果能顺带提一句某个不在场的人和他上次的事，就提。

@@ 请接着说一句。
+这句里要有一个你此刻手上的具体器物或数（例：七钱、第三格、差三分钟、半指宽）。
+如果能顺带提一句某个不在场的人和他上次的事，就提。
```
（完整 diff：`v2/evidence/d12c_prompt_render.diff`）

## 3. 代码改动范围（单变量）

`code/life/agent.py`：
1. 新增 `_D12C_ENV = "LIFE_PROMPT_D12C_SPECIFIC"`、`_d12c_on()`、`_d12c_lines()`（OFF 时返回空串）；
2. `_dialogue_prompt` / `_reply_prompt` 各**追加** `+ self._d12c_lines()`。

⇒ OFF 态两函数输出**与基线逐字相同**（渲染 sha 已比对）；ON 态仅多两行。

## 4. 分支落库与两态复现（2026-10-23 05:58，已通过）

| 项 | 值 |
|---|---|
| 分支 | **`feat/d12c-specific`**，基于 **`3ec85a0`** |
| commit | **`a977cb0`**（`life(d12c): 具体物/数 + 不在场第三方旧账…`） |
| `git diff --numstat 3ec85a0 feat/d12c-specific` | `code/life/agent.py` **19+/2−**（净 +17 行）；`tools/d12c/render_d12c_prompt.py` **21+/0−**（新增脚本） |
| 分支解出位置 | `/tmp/t271-d12c-br`（`git archive feat/d12c-specific`） |
| **OFF 复现** | `5cf08593d562dc09fdd42ab289319a819481c4882701407b039fa514ff8293f7` ✅ 与 §1 逐字相等 |
| **ON 复现** | `effc14dbffdb6865aa52d9d8adab9db269ab3b92ae9a1a230a22cab6c0ed73f5` ✅ 与 §1 逐字相等 |
| 复现命令 | `cd /tmp/t271-d12c-br/code && PYTHONPATH=$PWD env -u LIFE_PROMPT_D12C_SPECIFIC python3 ../tools/d12c/render_d12c_prompt.py`（ON 用 `LIFE_PROMPT_D12C_SPECIFIC=1`） |

> 与 leader 测的"26 行"差异说明：我这边 `git diff --numstat` 是 **19+/2−（净 +17）**；若按"增+删+脚本"合计则 19+2+21=42 行，若按"agent.py 变更行含上下文"会得到不同数字。**内容以两态 sha 逐字相等为准**（已通过），行数口径差异不影响接线结论。

## 4b. 起跑前还缺的三项（跑前必须补）

1. `pgrep`/`ps` 逐条环境确认时刻与结果（见 §5）；
2. OFF 臂 60 秒硬闸结果（`paren_rate ≥50%` + provider + 结构）；
3. 两臂 `arm_state_check` 汇总行。

## 5. 环境确认（2026-10-23 04:26，**当前不可起跑**）

```
ps -eo pid,lstart,cmd | grep "[o]rchestration run"
2605331 Fri Oct 23 04:09:57 2026 python3 -m orchestration run --life --seed 42 --agents 16 --rounds 84
        --out v2/evidence/run_f6off_cycle06_seed42_n16r84/run.jsonl --flush-every 2
```
- `LLM_CALL` 前 3 条 `provider=openai_compat`；已 `LLM_CALL 732` 条 ⇒ **真跑、仍在进行**。
⇒ **按串行纪律，D12-C 两臂暂不起跑**，等该批收尾（看产物 + 日志尾部）后再做 60 秒闸。
