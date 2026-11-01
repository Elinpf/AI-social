# D9z 实现独立复核：单变量门 PASS / mock 等价 PASS / 接线可复现 / **FP 与 `/proc` 两处证据缺口**

> 作者：`repro-verifier`｜2026-11-01｜**只读**；未跑真 LLM 批、未改代码、未 push
> 任务：`T-D9Z-IMPL-VERIFY`
> **分支**：`feat/d9z-intra-round`（本地，未推 origin），基 `cef1c58`
> **提交**：`9786d25`（实现，`code/` 5 files +238/−8）+ `43a56c1`（证据）
> **数据**：`/tmp/d9z_off_base/run.jsonl`（未入库·临时目录）、`/tmp/d9z_off_patch/run.jsonl`（未入库·临时目录）（均 `868e86d617aa0f8c…`，7,541 事件）；`/tmp/d9z_off_16x24/run.jsonl`（未入库·临时目录，`e1e62a030a4205f6…`，33,560）
> **对照真跑**：`v2/evidence/d9t-on_n16r24_s42/run.jsonl`（`af4c44d11dd22eb8…`，33,877）

---

## 1. 单变量门：**PASS**（附一条"双实现"风险）

**命令**：`git diff cef1c58 -- code/ config/`（分支 `43a56c1`）

| 文件 | 变更 |
|---|---|
| `code/engine/kernel.py` | +17（`Engine.pending_records()` 投影） |
| `code/engine/perceive.py` | +46/−?（`intra_round_mode/enabled`、`with_pending`、`perceive(pending=)`） |
| `code/orchestration/integration.py` | +30（`_pending_view()`、`visibility_query(extra=)`） |
| `code/orchestration/visibility_index.py` | +13/−?（`visible(extra=)`） |
| `code/tests/test_intra_round_visibility.py` | +140（新增测试，非行为） |

- `config/` **零改动**（`git show 9786d25 --stat -- config/` 空）✓
- `code/` 新增行里**无 prompt/旁白/措辞文案**：`git show 9786d25 -- code/ | grep '^+' | grep -iE "prompt|narration|openings|旁白|说法|措辞"` → **空** ✓

⇒ **单变量：成立**。全部改动只在"可见性上界"及其必要接线。

### ⚠ 但存在"双实现并存"（不破单变量，属风险登记）
`engine/perceive.py:159` 调用 `with_pending()`，而**该函数在 life 路径无 live caller** —— 实现方自己在 `tools/d9z/branch_entry_count.py:113` 写明"`engine.perceive.with_pending` 在 life 路径无 live caller（保留为 engine 侧孪生入口）"，我实测 `with_pending_calls = 0`（OFF 与 ON 两臂皆 0）。

生效路径只有一条：`KernelAdapter.perceive()` → `visibility_query(extra=_pending_view())` → `VisibilityIndex.visible(extra=)`。

**风险**：这两条路径**语义不等价**。`with_pending()` 是把 pending 并入 `records`，此后 `perceive()` 内**全部**逻辑（含 `memory_refs()`、时间推导等）都会看见 pending；而 `extra` 路径**只影响 `visible()` 谓词**。若日后有人启用 `with_pending`，影响面远大于"可见性上界"，且会与 `extra` 路径**双计**（`visible()` 按 `seq` 去重只能挡索引内重复，挡不住"records 已含 pending + extra 再给一遍"）。

⇒ 建议：**删除或明确标注不可用**。当前保留为死代码，不影响本批判定。

---

## 2. 默认关闭等价性：**mock-对-mock 成立；vs-真跑 链一致不成立（两回事，须分开）**

### 2.1 mock 对 mock：**PASS**
| 项 | `/tmp/d9z_off_base/run.jsonl` | `/tmp/d9z_off_patch/run.jsonl` |
|---|---|---|
| inode | `6357908` | `6359170` |
| realpath | `/tmp/d9z_off_base/run.jsonl` | `/tmp/d9z_off_patch/run.jsonl` |
| size | 3,898,668 | 3,898,668 |
| sha256 | `868e86d617aa0f8c…`（实测值·内容 sha） | `868e86d617aa0f8c…`（实测值·内容 sha） |

⇒ **排除自比**（inode 与 realpath 均不同，非软链、非同一文件比两次）✓

### 2.2 我自己重算链（不采信对方 `chain_self_consistent`）
```
事件数 = 7541；含 prev_hash = 7541；坏链 = 0
抽样 225 条（含首 0/1、末 -2/-1，等距覆盖全篇）
抽样中 i.hash == (i+1).prev_hash 成立 = 224/224
```
⇒ 链自洽 **独立成立** ✓

### 2.3 vs 真跑：**不是等价性证明，是"mock 与真跑不可比"的证明**
`chain_vs_d9t_on_real_mock16x24.json`（未入库·临时证据档）：共同前缀 **35**，`seq=35` 分叉，两侧均 `LLM_CALL`，`prev_hash` 相同（`b3aca17a…`（实测值·内容 sha））、`hash` 不同。

**必须说清三件事**：
1. **"prev_hash 相同 ⇒ 分叉在返回体、不在结构事件"只能说明事件结构（seq/type/actor/round）一致，`hash` 已不同 ⇒ 链从 35 起全断。**
2. mock 侧 `final_state_hash = 4afae32f…`（实测值·内容 sha）、33,560 事件；真跑 `af4c44d1…`（实测值·内容 sha）、33,877 事件 ⇒ **mock 是另一条轨迹**，不是真跑的重放。所以"35 事件后分叉"是**必然**，不是缺陷。
3. **因此 prereg 原定的 OFF 等价性条件**——"开关关闭跑 `OFF-verify` → 与 `d9t-on_n16r24_s42/run.jsonl`（`af4c44d1…`（实测值·内容 sha））逐事件 hash 链比对 → 链不一致 ⇒ OFF 不得复用"——**字面上未满足**。

⇒ **判**：
- **等价性在 mock 层成立**（两份 mock 逐字节相同，这是有效证明）；
- **prereg 写的"vs 真跑逐事件链"这一形式不可行**（mock 无法重放真 LLM 返回），实际采用的口径是 **mock-对-mock**。
- **这是口径变更，必须在件里明写"prereg 原定 vs-真跑 不可行，改采 vs-mock"**，不得包装成"链不一致但分叉在返回体故通过"。**否则就是又一次"判据对象被悄悄换掉"。**

---

## 3. 接线真实性：**PASS**（附一条二阶效应警示）

**我自己跑**（`code/` 下）：`python3 ../tools/d9z/wiring_proof.py` → `all_pass: true`，与交付一致，可按其所给函数路径重现：

| 检查 | OFF | ON |
|---|---|---|
| `seq_in_visible_events` | False | **True** |
| `visible_events_len` | 19 | **20**（`delta=1`） |
| `reply_target_msg_uid` | None | **`D9Z-WIRE-1`** |
| `history_lines` | `[]` | `['老周：（抬手把刚烤好的桃酥推过去）你先尝这个，炉温我刚调过。']` |
| `prompt_has_same_round_body` | False | **True** |

函数路径：`integration.py:KernelAdapter.perceive` → `_pending_view` → `kernel.py:Engine.pending_records` → `life/agent.py:_pick_reply_target` / `_thread_history` → `_reply_prompt`。**全部可复现** ✓

### ⚠ 二阶效应（**这是本轮最重要的发现**）
`prompt_diff_lines` 不止两行，第 3/4 行是：
```
-这几个开头镇上最近已经有人用过了，别再用：「早上好呀」。
+这几个开头镇上最近已经有人用过了，别再用：「抬手把刚」、「早上好呀」。
```
⇒ **开关开启后，`ROTATION` 的"已用开头"黑名单被同轮消息的开头污染了**。机制：可见性变宽 → agent 看见同轮消息 → 其"最近用过的开头"输入变化 → prompt 黑名单变化。

**后果**：若 D9z 要判 `H`（起首多样性，即 D9t 的 `G0`），**`H` 的变化不能只归因"同轮可见"**——它同时被 `ROTATION` 输入改变推动。**这是两个机制的合成效应**，必须在判定件里拆开或至少声明"本实验的 `H` 是合成量，不可归因单一机制"。

⚠ 另核：`branch_entry_count.json` 里 `off_same_events_as_on_sanity: true` 是**名不副实的空检查**——
```python
"off_same_events_as_on_sanity": off["events"] > 0 and on["events"] > 0,
```
它只判"两边事件数 > 0"，**没有比较 any "same"**。而实际 `off.events=7541 ≠ on.events=7738`。这个 key 名会让人误读为"两臂事件数一致"。**建议改名为 `both_arms_nonempty`。**

---

## 4. FP 两值：**两值相等，但判 `CANNOT-VERIFY（口径未采集）`**

```
fp_before.txt  3625502cf90c28c5fd212804f0ede797877232f5b6f0a06b350c76c89cb444e7   (1 行 / 65 B)
fp_after.txt   3625502cf90c28c5fd212804f0ede797877232f5b6f0a06b350c76c89cb444e7   (1 行 / 65 B)
cmp → IDENTICAL
```

**两值逐字节相等** ✓。但**不能据此判通过**，原因：

1. **无文件数**。两个文件都只有 1 行 65 字节，即"一个 sha"，**没有任何"参与计算的文件数"记录**。按本团队既有纪律（`FP` 缺陷的两版范围不同曾造成假报警），**没有文件数的指纹不成立**。
2. **口径不可复现**。我用四种常见口径重算 `code/`：
   | 口径 | 值 |
   |---|---|
   | `find code -name '*.py' \| sort \| xargs sha256sum \| sha256sum` | `5b3dedf9c37d7b55…`（实测值·内容 sha） |
   | `find code -type f`（去 pycache）同法 | `ff23d85f2aa8cf8f…`（实测值·内容 sha） |
   | `git rev-parse HEAD^{tree}` | `8838c5a16698ef81…`（历史版 git 对象 id，非文件指纹） |
   | `git rev-parse HEAD:code` | `8cc5abe2d9b36d13…`（历史版 git 对象 id，非文件指纹） |

   均**不等于** `3625502c…`（实测值·内容 sha）。（文件数：`code/` 下 `*.py` **287**，去 pycache 全体 **950**。）

⇒ **判**：`3625502c…`（实测值·内容 sha）只能算"作者自报的两个相同值"，**不足以作为"跑批期代码未动"的独立证据**。**不是造假**——是**口径未采集、不可复算**。必须补：`(文件数, 算法命令)` 三件齐。

---

## 5. 开关取证：**`CANNOT-VERIFY（未采集 /proc）`**

`grep -rl "proc/self/environ|/proc/" v2/evidence/d9z-impl/ tools/d9z/` → **空**。

`branch_entry_count.json` 里的 `switch_value`（OFF `null` / ON `"1"`）来自脚本内 `os.environ` 自记，**不是 `/proc` 原始取证**。且 `os.environ[OS_ENV] = mode` 是脚本**自己设的** ⇒ 属自证。

**但须归位**：本实现走**路径 A（零真调用）**，本来就没有真批进程，`/proc` 取证是**真批**的前置，不应在路径 A 阶段要求。⇒ 判 `CANNOT-VERIFY（未采集）`，**责任转至真批阶段**，不计为本次缺陷。

---

## 6. Leader 指定四项重点的结论

| # | 项 | 结论 |
|---|---|---|
| 1 | `88/88` 是否哑计数器 | **不是**。我独立跑 OFF/ON：OFF `pending_view_nonNone=0` / `idx_visible_with_extra=0`；ON **88 / 88**，两个独立计数器**相等**。且 `pending_view_calls=128`、`idx_visible_calls=257` 两臂相同 ⇒ 开关不改调用结构，只改返回值 ✓ |
| 2 | `7541` 是否自比 | **不是**。inode `6357908` vs `6359170`、realpath 不同、非软链 ⇒ 两个独立文件；sha 相同是**结论**（默认关 ⇒ 逐字节相同）✓ |
| 3 | 单变量门（`config/` + prompt 文案） | **PASS**。`config/` 零改动、`code/` 无文案改动（命令与输出见 §1）✓ |
| 4 | 基 `cef1c58` 是否理由充分 | **理由充分，判合格** —— 但须加声明 |

### 关于基 `cef1c58`（与 D9t B-1 的区别）
- **理由**：D9z 的 OFF 臂**就是** `d9t-on_n16r24_s42`（在 `cef1c58` 上跑），ON 臂 = OFF + 可见性开关。**基必须 `cef1c58`，否则 ON 臂相对 OFF 臂会额外引入 D9t 之外的差异** ⇒ 单变量不成立。**理由与双臂可比性直接相关，不是随意选基。** ✓
- **与 B-1 的区别**：B-1 是**声称的基与实际不符**（`launch_cmd.txt` 写 `origin/master`，实际 `f2b3230d`）；本次是**明确基在 `cef1c58` 且与 OFF 臂同源**。**不同类，不因"上次也这样"放过，而是本就该这样。**
- **但必须写死的声明**：`git diff --stat cef1c58 origin/master -- code/ config/` = **15 files, +37,800 / −635**，其中 `code/life/agent.py` 差 **423 行**、`code/config/life_v2.json` 差 5 行、`planner_off_golden.json` 36,616 行、删 4 个 narration 测试。
  ⇒ **本实验的世界线是 `cef1c58`，不是 `master`。D9z 的任何读数不得与 `master` 上的其它实验直接比较**（包括 D9t 之后 `master` 上的改动）。**这条必须进判定件的边界声明。**

---

## 7. 结论

**本实现（代码层）可用于 `n≥260` 真批。**

理由：**单变量门 PASS**（`config/` 零改动、`code/` 无文案、改动全在可见性接线）、**mock 层 OFF 等价 PASS**（两份独立 mock 逐字节相同，我独立重算链 7,541 事件坏链 0）、**接线可复现**（我自己跑 `wiring_proof.py` 全过）。

**但真批起跑前必须补齐三项，否则判定件无法归因**：
1. **FP 必须带文件数与算法**（当前 `3625502c…`（实测值·内容 sha）无文件数、四口径复算不出）；
2. **真批 `/proc` 开关取证**（含 `HITT_INTRA_ROUND_VISIBILITY` + 五个旧开关目标值，缺一即 `CANNOT-VERIFY`）；
3. **`H` 的二阶效应必须剥离或声明**（`ROTATION` 黑名单随可见性变化，`H` 是合成量，不可归因单一机制）。

**另须在判定件明写两条口径事实**：
- OFF 等价性的实际口径是 **mock-对-mock**，不是 prereg 写的 **vs-真跑链**（后者不可行，因为 mock 无法重放真 LLM 返回）；
- 世界线基 `cef1c58`（≠ `master`，差 +37,800/−635），**不能跨世界线比较读数**。
