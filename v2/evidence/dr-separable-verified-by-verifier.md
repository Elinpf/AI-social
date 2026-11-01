# DR 可分离化独立复核：**六门全过**；附一项缺件（交付件不存在）与一项口径保留

> 作者：`repro-verifier`｜2026-11-01｜**只读**；未跑真批、未改代码、未改被审件
> 任务：`T-DR-SEPARATE-VERIFY`
> **分支**：`feat/dr-separable`（本地），`d87288e`（基 `4eac7cc`，其 `code/` 与 `43a56c1` 逐字节相同）
> **FP 三元组**：`(rev=d87288e, files=284, sha256=61feb052cbaa232b…（实测值·内容 sha）)`
> 数据：`/tmp/dr_base_out/run.jsonl`、`/tmp/dr_new2_out/run.jsonl`（均 `868e86d617aa0f8c…`（实测值·内容 sha） / 7,541 事件）

---

## 1. 三态语义：**PASS**（读分支代码，非配置注释）

`code/life/dialogue_repair.py::_tri` + `repair_ask()`：
```python
def _tri(raw):
    if raw is None: return None
    if isinstance(raw, bool): return raw        # ← JSON 的 false 走这里
    v = str(raw).strip().lower()
    if v in _TRUTHY: return True
    if v in _FALSEY: return False
    return None                                  # ← 无法解析 ⇒ None（不干预）

def repair_ask(...):
    if params.get("record_only") or params.get("repair_ask") is False:
        return None                              # ← 只有 is False 才关
```
| 取值 | 行为 | 判定 |
|---|---|---|
| `None`（默认） | 不因该键返回 None ⇒ **与引入前一致** | ✓ |
| `True` | 同上 ⇒ **与 `None` 等价** | ✓ |
| `False` | 返回 None ⇒ **只去掉动作要求**，而 `context_line()` 仍工作（单测断言） | ✓ |

⇒ **`None` 与 `True` 行为一致、`False` 才关闭**，与卡面要求一致。**不是靠注释，是 `is False` 这个身份比较。**

---

## 2. 默认全关逐事件等价：**PASS**（我自己重算，不采信 `identical:true`）

### 2.1 排除自比
| 文件 | inode | size | sha256 |
|---|---|---|---|
| `/tmp/dr_base_out/run.jsonl` | **6564572** | 3,898,668 | `868e86d617aa0f8c…`（实测值·内容 sha） |
| `/tmp/dr_new2_out/run.jsonl` | **5444330** | 3,898,668 | `868e86d617aa0f8c…`（实测值·内容 sha） |

⇒ **inode 不同、路径不同、非软链** ⇒ 两个独立文件；sha 相同是**结论**，非自比。

### 2.2 我自己的链重算
```
a base: events=7541  含 prev_hash=7541  坏链=0  | 抽样 225（含首末）  i.hash==(i+1).prev_hash  224/224
b new2: events=7541  含 prev_hash=7541  坏链=0  | 抽样 225（含首末）  i.hash==(i+1).prev_hash  224/224
```

### 2.3 比 `chain_equiv.json` 更强的一步：**逐行全等**
```
A=7541 行  B=7541 行  不等行 = 0   首个不等 = None
```
⇒ **7541/7541 逐行字节相同**，不只是"链自洽"或"前缀一致"。

---

## 3. 新增日志键只在开启时出现：**PASS**（按 Leader 要求给两种打印）

| 臂 | `msgs_with_dialogue_pick` | `dialogue_pick_modes` | 说明 |
|---|---:|---|---|
| **A_disabled**（DR 全关，默认） | **0 / 80** | `{}` | **连键都不存在** |
| B_enabled_nomark（开 DR、标记关） | **0 / 80** | `{}` | 标记开关确实独立生效 |
| C_enabled_mark_noask（开标记） | **80 / 80** | `{initiate:41, fallback:39}` | 键与值均可核 |
| **D_disabled_switches_on**（DR 关 + 两新开关全开） | **0 / 80** | `{}` | **`enabled` 门控有效** |
| E_forced_prefer | **80 / 80** | `{initiate:41, prefer_threads:39}` | 见 §4 |

**两种打印的区别（这正是 Leader 提醒的那类风险）**：
- `'dialogue_pick' in payload` → A 臂 **False**（键**不存在**）
- `payload.get('dialogue_pick')` → A 臂 **`None`**（与"键存在但值为 None"**无法区分**）

⇒ **代码层面确认键不写**（不是写空值）：`agent.py` 里是
```python
if dr_cfg.get("pick_mark") and self._pick_via:
    payload["dialogue_pick"] = {...}       # ← 条件不成立 ⇒ 根本不给字段赋值
```
**且该段整体嵌在 `if dr_cfg.get("enabled"):` 块内**（我一开始看漏缩进、误判两路径不对称，**已自查更正**：回复与发起两条路径的条件**是对称的**，都要求 `enabled` 且 `pick_mark`）。

---

## 4. `pick_mark` 标记真实性：**PASS** —— 真的由谓词驱动，不是"恰好命中"

**它替换的是什么**：`tools/dr/separate_proof.py` 的 E 臂做的是
```python
if force_prefer:
    ...
    DR.threads_with_open_rift = _fake_threads   # ← 替换"哪些线程有未了结旧账"这个谓词
```
而 `agent.py` 的消费点是
```python
prefer = DR.threads_with_open_rift(self._rifts)   # 有旧账的线程优先接话
...
if prefer_threads and tid in prefer_threads:
    self._pick_via = "prefer_threads"            # ← 标记在此处产生
    return ev
```

**对照证明**：
| 臂 | `prefer_threads` 计数 | `prefer_true_msgs` |
|---|---:|---:|
| C（真实 rift 恒 0，未注入） | **0** | **0** |
| E（注入"已见线程 = 有旧账"） | **39** | **39** |

⇒ 谓词一变，标记就从 0 变 39 ⇒ **`mode="prefer_threads"` 确对应"因旧账被优先选中"**；`prefer` 字段与 `mode` 完全一致（39 = 39）。

**保留**：E 臂是**注入式**而非真实 rift 驱动（mock 回复不含负向词 ⇒ 真实 rift 恒 0）。这一点交付已自述，且 §口径条已由单测补证。

---

## 5. FP 变更：**数对，但有两项保留**

```
tools/tree_fingerprint.sh world  →  61feb052cbaa232bd0e9f0505899befdcab24bdffe117c7242c64c9033a986bc（实测值·内容 sha）
文件数（同一 collect 命令另算）  →  284
```
⇒ sha 与卡面 `61feb052…`（实测值·内容 sha）**一致**；files = **284**。

**⚠ 保留一：`rev` 实为 `268774e` 而非 `d87288e`**
计算时 worktree HEAD 在 `268774e`（`tools(l2b): 取回 channel_counts.py`）。已核：
```
git diff --stat d87288e 268774e -- code/ config/   → 空
git rev-parse d87288e:code  = d73a5152bafa（历史版 git 树对象）
git rev-parse 268774e:code  = d73a5152bafa（历史版 git 树对象）        ← 同 tree
```
⇒ **两者 `code/`+`config/` 完全相同**，故该 FP 可代表 `d87288e`。**但严格说 rev 标注应为 `268774e`（等价 rev）**。

**⚠ 保留二：`tree_fingerprint.sh` 只输出 sha，不输出文件数**
脚本末行是 `... | sha256sum | awk '{print $1}'` ⇒ **284 是我用脚本内部同一条 collect 命令另算的**。这是"**同源输入**"，不是"**同源输出**"。建议脚本加 `wc -l`（此前已提过，仍未做）。

**⚠ 保留三（缺件）：卡面引用的 `artifacts/dr-separable-delivery.md` 在 `d87288e` 中不存在**
```
git cat-file -e d87288e:artifacts/dr-separable-delivery.md  → fatal: ... does not exist
git ls-tree -r --name-only d87288e -- artifacts              → 空
git grep -l 61feb052（实测值·内容 sha）d87288e            → 空
```
⇒ **交付自述件与 FP 数值均未落地到仓库**；我据卡面给的 `61feb052` 自行重算才验上。

---

## 6. `code/` 改动面：**PASS**

```
git diff --stat 43a56c1 d87288e -- code/
 code/config/dialogue_repair.json  |  5 ++-
 code/life/agent.py                | 25 +++++++++++
 code/life/dialogue_repair.py      | 55 +++++++++++++++++++++++
 code/orchestration/integration.py |  3 ++
 code/tests/test_dr_separable.py   | 94 +++++++++++++++++++++++++++++++++++++++
 5 files changed, 181 insertions(+), 1 deletion(-)
```
⇒ **5 文件 +181/−1**，与卡面一致 ✓

**文案夹带检查**：
- `grep '^+' | grep -iE 'prompt|narration|openings|旁白|措辞|句式|语气'` → **只命中一个测试函数名** `test_record_only_blocks_both_prompt_clauses`，**不是文案**
- 新增中文字面量全为**注释/说明/测试数据**（如测试 rift 的 `topic: "工钱"`）

⇒ **无 prompt 文案 / 旁白 / 数值改动** ✓

---

## 7. 口径条：单测**确实构造了 rift**，可分离性不是纸面

**测试文件**：`code/tests/test_dr_separable.py`，我实跑 **8 passed in 0.04s**。

**构造 rift 的证据**：
```python
def _rifts() -> dict:
    return {"R|t1|m1": {"rift_id": "R|t1|m1", "with": "P002", "thread_id": "t1",
                        "msg_uid": "m1", "seq": 5, "round": 3, "topic": "工钱", "day": 1, "slot": "am"}}
```

**关键断言（可分离的本体）**：
| 测试名 | 断言 |
|---|---|
| `test_repair_ask_default_none_follows_enabled` | `DR.repair_ask(_rifts(), "t1", "P002", 10, _p(repair_ask=None))` **is not None**（None = 照旧注入） |
| `test_repair_ask_false_suppresses_only_that_clause` | `repair_ask(..., repair_ask=False)` **is None** 且 `context_line(...)` **is not None** ⇒ **只去掉动作要求、处境仍在** |
| `test_repair_ask_true_same_as_none` | `repair_ask(None) == repair_ask(True)` |
| `test_record_only_blocks_both_prompt_clauses` | 两段提示词均 None，但 `audit_fields(...)` **is not None**（只挡提示词不挡记录） |
| `test_disabled_produces_nothing` | `enabled=False` + 两新开关 True ⇒ 仍全 None |

⇒ **"可分离"有单测实证，不是纸面** ✓

---

## 末句

**本实现可用于两臂预登记 —— 是**。理由：六门中 **1/2/3/4/6 全部 PASS 且我独立复算命中**（三态靠 `is False` 身份比较、7541/7541 **逐行字节全等**、默认关时**键不存在**、`prefer` 标记随谓词从 0→39、改动面 5 文件无文案夹带），口径条亦由 8 条单测实证；**可分离（`repair_ask=False` 去掉动作要求而保留处境）这一核心命题成立**。

**但预登记前须补齐三件（均不改实现、不改口径）**：
1. **交付件缺失**：`artifacts/dr-separable-delivery.md` 不存在于 `d87288e`，FP 数值 `61feb052…`（实测值·内容 sha）在仓库内**查不到任何出处** —— 须补入库，否则下一个人只能靠卡面口传；
2. **FP 的 rev 标注**：应为 `268774e`（`code/`/`config/` 与 `d87288e` 同 tree `d73a5152bafa`（历史版 git 树对象）），或直接重算于 `d87288e`；
3. **`tree_fingerprint.sh` 输出文件数**（同源输出而非同源输入），否则"files 与 sha 同源"永远要靠人手另算。

**另注意一条互斥禁令（Leader 已定）**：`dialogue_rift.prompted` / `dialogue_repair.prompted` 只在 `enabled=1` 出现 ⇒ **它们本身就是"开 DR 改日志"的证据**，报告里**不得同时**用它们与"hash 链等价"，两句互斥。

---

## 附录：Leader 对三项保留的处置（2026-11-01 19:2x）

### ① 交付件未入库、FP 数值全库零命中 —— **成立，已补**
`artifacts/dr-separable-delivery.md` 是**团队工作空间产物**（不在仓库树内，故无法按路径核），`61feb052`（内容 sha·实测值）此前**只出现在候选池的文字里**，**不是可复算记录**。⇒ Leader 已把它补成**带 rev 与 files 的正式三元组**（见下）。

### ② rev 实为 `268774e`、`d87288e:code` 与它同 tree —— **成立，已核**
```
git rev-parse 268774e:code  → d73a5152bafa53ba8dcc97b872a44553682220f0（历史版·git tree 对象，非文件指纹）
git rev-parse d87288e:code  → d73a5152bafa53ba8dcc97b872a44553682220f0（历史版·同 tree）   ← 同 tree
```
⇒ **FP 可代表 `d87288e`，但标注必须写"两 rev 同 code tree"**。

### ③ `tree_fingerprint.sh` 在该分支上仍只输出 sha —— **成立，且原因已定位**
`d87288e:tools/tree_fingerprint.sh` 里 `grep -c "files="` = **0**；`origin/master` 上 = **1**。
**原因**：`files=` 同源输出是 Leader 在 `c843d18` 才改进 master 的，而该分支基座是 `4eac7cc`（更早）⇒ **分支带的是旧版脚本**。**不是执行者的问题。**

### Leader 自己重算的 FP 三元组（同源输出，非"同源输入"）
在 `d87288e` 的 worktree 上、用 **master 版** `tools/tree_fingerprint.sh` 跑：
```
files=284
sha256=61feb052cbaa232bd0e9f0505899befdcab24bdffe117c7242c64c9033a986bc
mode=world
```
⇒ **`FP = (rev=d87288e[code tree 同 268774e], files=284, sha256=61feb052…（内容 sha·实测值）)`**
**`files` 与 `sha256` 由同一条命令、同一份清单数出**，三项保留中的 ①③ 由此关闭。

> **方法论留一笔**：评审说"这叫同源输入，不是同源输出" —— **这个区分是对的**，也正是 `L2b` 那条"`{value, why_zero, positive_control}` 三件齐"要防的东西：**两个数分别算得出，不等于它们来自同一份数据。**
