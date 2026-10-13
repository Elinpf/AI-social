# T340 · `make verify` 自检「跑中树被改」—— 机制 + 双向证据

- 作者：sandbox-test-lead ｜ 落盘：`v2/evidence/T340-verify-tree-change-guard.md`
- 原理：与「验证窗内冻结被验对象」（T304/T314）同源 —— 门要能自己发现「我跑的时候被验对象变了」。

## 0. 机制

- `tools/tree_fingerprint.sh`：**冻结区指纹**（`code/**` + `config/**`）=
  `HEAD sha` + `git diff HEAD -- code config`（已跟踪改动内容）+ `code/config` 下**未跟踪(非忽略)**文件清单与内容哈希 → sha256。
  - **有意收窄**：不计 gitignore 生成物（`reports/`、`__pycache__`、`*.jsonl`、截图等）⇒ 避免生成物噪声假红。
- `tools/verify_tree_guard.sh`：`F0=指纹` → `make verify-inner`（真门）→ `F1=指纹`；`F0≠F1` ⇒ **exit 2**（“结果不可信，请重跑”）+ 打印**变更清单**（起→收 的 tracked/untracked 差异）。
- `Makefile`：`verify` 改为**受守卫**（调 guard）；真门改名 **`verify-inner`**（= 旧 verify：仓根门禁 + `code` CI）。`.`PHONY`/`help` 同步。

**区分「起跑时脏」（允许）vs「跑中被改」（红）**：指纹只在**同一 run 的起/收**之间比较 ⇒ 起跑时的脏照常记账、不阻断。

## 1. 证据：改树 → 红（含**受控**与**真实**）

| 证据 | 类型 | 结果 |
|---|---|---|
| 受控：`F0` → 新增 `code/config/_t340probe.probe` → `F1` → 还原 `F2` | 确定性 | **F0≠F1（变了）；F2==F0（回原）** ⇒ 指纹对 code/config 改动**灵敏且可逆** |
| 真实 run#1（09:35–09:40）：起 `cdf9b06` → 收 `b42545c` | 真实 | 守卫 **exit 2**（起≠收）；根因=**kernel 的 T328③ WIP 在跑中被改**（`engine/state.py`/`event_acc.py`/`liquidity.py`，mtime 09:33–34） |
| 真实 run#3（09:47–09:54）：起 `e91655c` → 收 `ee393d3` | 真实 | 守卫 **exit 2**；根因=**其他 agent 跑中改了 `code/frontend/tools/shot.py`**（mtime **09:54:15**） |

## 2. 证据：不改 → 绿（无误报）

| 证据 | 结果 |
|---|---|
| kernel 的 `make verify`（受守卫版） | 打印 **“跑中树未变，门结果可信”**，`EXIT=0` |
| 我的 run#2 | 起==收（`b42545c`），守卫打印 **“跑中树未变，门结果可信”**（该次 inner 因外部 `Terminated` 未全绿，但**守卫无误报**） |

## 3. 误报分析（关键，诚实）

- **未发现「门自身写盘」导致的误报**：核 `code/obs/golden_baseline.json` **只由维护命令 `python -m obs golden-freeze` 写**（`obs/golden.py:137`），**`make verify` 自身不写**任何 tracked `code/**`/`config/**`。
- **真实 run 的红都是【外部改动】**（kernel 09:33、shot.py 09:54）⇒ **正确**（该结果确实不可信），**非机制误报**。
- ⚠️ **现实约束**：本仓**多 agent 并发编辑**，一条 3–4 分钟的 `make verify` 期间**常有他人在改 `code/**`** ⇒ 本守卫会**较频繁**输出“结果不可信”。这是**语义正确**（结果确不可信），但**要拿到干净的「零误报率」数字，需要一个全局静默窗**（本轮未能获得：编辑者不止 kernel 一人）。
- **可选降噪（交 Leader 定，未实现）**：① 把范围**只收 `config/**`**（T325 原始故障即 config 变更所致；frontend 编辑不再触发）；② 起跑时把「当时已脏」的文件**纳入基线**、只对**后发生的**改动报红（更贴近“跑中改动”，但实现更复杂）。

## 4. 日志形式（绑 sha）

```
[verify-guard] 起跑指纹(冻结区 code+config) = <sha256>
... make verify-inner 输出（gate + CI）...
[verify-guard] 收尾指纹 = <sha256>
[verify-guard] ✗ 跑中树被改（<F0> → <F1>）⇒ 本次门结果【不可信】，请重跑。
[verify-guard]   变更清单（起→收 的 tracked 改动/未跟踪文件 差异）：
     +M  code/frontend/tools/shot.py
[verify-guard] OK：跑中树未变，门结果可信。
```

## 5. 验收对照

- 机制落地：`tools/tree_fingerprint.sh` + `tools/verify_tree_guard.sh` + `Makefile`（`verify` 受守卫 / `verify-inner` 真门）✓
- **双向反向验证**：改树→红（受控 + 2 次真实 run）✓；不改→绿（kernel run + 我的 run2）✓
- 起止指纹/清单的日志形式：见 §4 ✓
- 绑 sha 证据：见 §1（各 run 的起/收指纹）✓

## 6. 边界

- 未改任何 `code/**` 断言语义（只加 `tools/` + `Makefile` 目标）。
- 本报告 sha 绑定：机制提交见 commit（`tools/*` + `Makefile`）。

## 7. ⚠️ 可信度口径（Leader 2026-10-13 定，写死）

> **本门给出的是「这次裁决可不可信」，不是「门本身过不过」。**
> - 任何一次**绿**，**只有在报告了「跑中树未变」的前提下才可采信**；
> - 报「**结果不可信**」(exit 2) 时 **既不得当失败、也不得当通过** —— 请重跑。
> - （因此 exit 2 ≠ "门挂了"；它是"结论作废、需重跑"。）

**已知且接受的局限**：本仓多 agent 并发编辑 ⇒ 一条 3–4 分钟 verify 期间**可能**有他人改动（`code/**`）⇒ 会报「不可信」。这是**语义正确**（结果确不可信），**非误报**；正解是**流程**（verify 期间禁改树）而非削弱守卫。降噪选项（只收 `config` / 更复杂基线）经 Leader 评估**不采纳**（会丢真信号）。

*（T340 落盘 — sandbox-test-lead）*
