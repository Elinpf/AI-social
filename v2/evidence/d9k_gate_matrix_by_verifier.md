# D9k 起跑前置闸门 · 判定矩阵（先冻结语义，再写脚本）

> **件头两条**
> **① 任务载体**：本件依 **Leader 2026-10-30 06:42:21 消息**执行（卡号 `#T-D9K-REPORT` 在库中不存在，以消息为准）。
> **② 本件性质**：**只出矩阵与判据，不写代码**。目的：`tools/d2/run_batch.sh` 落地前先把"什么情况不许起跑、谁能放行、放行要留什么痕"**冻结**，避免"语义边写边定"（今天已因定义未冻结栽过一次：`蹭+围裙` A 口径 11 / B 口径 0）。

- 作者：`repro-verifier`｜2026-10-30｜**只落盘不提交**
- 相关工具：`tools/metrics/arm_config_guard.py`（代码同源，rc `0/2/3`）；本矩阵为其**上游语义**（env 维度目前**未**工具化）

---

## 0. 先自曝一处我自己的错（此前口述给 Leader 的那句）

我曾说「**D9i** 的 OFF 臂没有 `env_dump_pre.txt`，只有 ON 臂有」。**这是错的**——我把两对臂搞混了。实测：

| 臂对 | 目录 | 取证文件 | 结论 |
|---|---|---|---|
| **D9i**（`narr-off` / `narr-on`） | 两臂各自 | **都有** `switch_proof.txt`（含 `/proc/<pid>/environ` 抓取）+ `env_pre_shell_{off,on}.txt` + `launch_cmd.txt` + `heartbeat.tsv` + `END.json` | **env 可比**（见 §2，可升"单变量候选"） |
| **D9g**（`run_d9_a1` / `run_d1_f6off`） | `run_d9_a1`：**仅** `host.log / llmcost.json / meta.json / run.jsonl` | `run_d1_f6off`：有 `env_dump_pre.txt`、`switch_proof` 类取证 | **取证不对称**：a1 侧**无 env 取证** |

⇒ 正确表述是：**"取证不对称"发生在 D9g 的两臂，不在 D9i**。这条更正会影响 D9i 结论能写多重（见 §3）。

---

## 1. 判定矩阵（主表：代码维度 → 三档）

| 检查项（顺序执行） | 结果 | 档位 | 默认动作 | 放行参数 | 有权放行 | 放行必须留痕 |
|---|---|---|---|---|---|---|
| ① `meta.json` 与 `run.jsonl` 的 `WORLD_INIT` 都存在且可解析？ | 否 | **`CANNOT-VERIFY`** | **拒绝起跑** | 无（**不给 override**） | — | — |
| ② `meta.code_sha` 存在？ | 否 | **`CANNOT-VERIFY`** | **拒绝起跑** | 无 | — | — |
| ③ 两臂 `code_sha` 相同？ | 是 | 进入 ⑤ | 允许（但见 §2） | — | — | — |
| | 否 | **`NOT_COMPARABLE`**（副标签 `diff=code_sha`） | **拒绝起跑** | `--allow-different-code` | **仅 Leader**（`dialogue-core-dev` 可代执行，但须 Leader 书面许可） | 见 §4 留痕四条 |
| ④ `provider` / `model` 相同？ | 否 | **`CANNOT-VERIFY`** | **拒绝起跑** | 无（跨 provider 不是"配置不同"，是"不可比"） | — | — |
| ⑤ `seed` / `n` / `rounds` 相同？（**同时涉及"分母可比"**） | 否 | **`NOT_COMPARABLE`**（副标签 `diff=run_params`） | **拒绝起跑** | 同上 `--allow-different-code` | 同上 | 同上 |
| ⑥ `agent.py` 提示词收尾指令同源？（git 可读时） | 否 | **`NOT_COMPARABLE`**（副标签 `diff=prompt`） | **拒绝起跑** | 同上 | 同上 | 同上 |
| | git 不可读 | **`CANNOT-VERIFY`** | **拒绝起跑** | 无 | — | — |

> **判据一句话**：③④⑤⑥ 任一不满足，**都不是"参数不同"，而是"两臂不可比"**——`NOT_COMPARABLE` 的语义是"**差值只能作观测**"，不是"注意一点"。
> **⑤ 的特别说明**：`seed/n/rounds` 不同会导致**分母不同**（D9c 的 `191 MSG` vs `686 MSG` 就是这么来的），比"代码不同"更隐蔽，故并入同一档强制拒绝。

## 2. 判定矩阵（副表：env 维度 → 单变量候选）

> 该维度**当前无工具**（`arm_config_guard.py` 尚未实现）；下表为**待实现语义**，落地时照写。

| 检查项 | 结果 | 档位 | 默认动作 | 放行参数 | 有权放行 | 留痕 |
|---|---|---|---|---|---|---|
| ⑦ 两臂是否各有 **被执行层** env 取证？（`switch_proof.txt`，须来自 `/proc/<pid>/environ`） | 都无 / 缺一侧 | **`CANNOT-VERIFY`** | **允许起跑，但结论降级**：不得写"单变量"，只能写"代码同源" | 无 | — | 报告须注明"env 未自证" |
| | 两侧都有 | 进入 ⑧ | — | — | — | — |
| ⑧ 两侧 env 差异键数 | **=1** | **`single-variable-candidate`** | 允许起跑 | — | — | 报告写"候选单变量（env 差 1 键：<键名>）" |
| | **≥2** | **`multi-variable`** | **拒绝起跑** | `--allow-multi-variable` | **仅 Leader** | 列出全部差异键 + 说明为何仍可解释 |
| | 有差异键**不可见**（如 `unset` vs 缺失无法区分） | **`CANNOT-VERIFY`** | 允许起跑，结论降级 | — | — | 注明"某键的 unset/缺失不可区分" |

> **判据一句话**：**"代码同源"≠"单变量"**；`SAME_CONFIG` 只是**入场券**，单变量必须由 **env 取证**支撑，且**必须是被执行层抓的**（shell 层声明值不算）。

## 3. 用矩阵回填两件历史结论（示例，证明矩阵可判历史）

| 臂对 | ③ code_sha | ④ provider/model | ⑤ seed/n/rounds | ⑥ prompt | ⑦ env 取证 | ⑧ 差异键 | **矩阵判定** |
|---|---|---|---|---|---|---|---|
| **D9i**（`narr-off`/`narr-on`） | 同 `47a7da9e` | 同 `openai_compat/DeepSeek-Flash` | 同 `42/16/24` | 同源（同 commit） | **两侧都有** `switch_proof.txt` | **1 个键**：`LIFE_PROMPT_NARRATION`（OFF=unset / ON=1） | **`single-variable-candidate`** ⇒ **单变量身份可写**（"候选"因为 OFF 侧是 `unset`，与"显式 =0"在结果上等价但记录形态不同） |
| **D9g**（`run_d9_a1`/`run_d1_f6off`） | 不同（`05636bc` vs `d7d1d93f`） | 同 | 同 `42/16/84` | **不同源**（尾指令 2 条 vs 3 条） | **不对称**：a1 无 env 取证 | 不可比 | **`NOT_COMPARABLE`** ⇒ **差值只能作观测**；且 env 侧再加一层 `CANNOT-VERIFY` |

⇒ 这两行同时说明：**矩阵不需要新数据就能判历史结论的强度**——D9i 够强（可写单变量候选），D9g 不够（只能写观测）。

## 4. `--allow-different-code` 的留痕四条（放行必留）

1. **谁批**：Leader 书面许可（含一句理由）；
2. **差在哪**：`arm_config_guard.py --json` 的输出**原样入库**（含 prompt 行级 diff）；
3. **结论降级声明**：该对臂的**所有**跨臂差值，报告中一律冠以「**观测**」，禁止写"因为 X 导致 Y"；
4. **禁止外推**：该对臂的差值**不得**进入任何"档位判定 / 判据验收 / 对外结论"。

## 5. 与现有工具/纪律的挂接

| 环节 | 现状 | 落地后 |
|---|---|---|
| 代码同源 | `arm_config_guard.py` 已可用（rc `0/2/3`） | `run_batch.sh` 起跑前调用，rc≠0 默认拒绝 |
| env 单变量 | **无工具** | 按 §2 实现后并入同一闸门（同一份 config 读 `switch_proof.txt`） |
| 分母可比（`seed/n/rounds`） | 仅靠人看 `meta.json` | 并入 ③⑤ 检查，强制拒绝 |
| 规则形式 | 多为"提醒式" | **每条规则须附可复制动作**（Leader 已写进清单 §0） |

## 6. 三条裁定（Leader 2026-10-30 06:44，**已冻结，本节替代原"待裁"**）

### 裁 1：③/⑤/⑥ 合并为单档 **`NOT_COMPARABLE`**，**但必须报"差什么"（副标签）**

| 副标签 | 含义 | 修法 |
|---|---|---|
| `diff=code_sha` | 代码版本不同 | **重建基线**（跨版本不可比） |
| `diff=run_params` | `seed/n/rounds` 不同 | **同参重跑**（版本可比、参数不可比） |
| `diff=prompt` | 提示词不同源（`code_sha` 也可能同） | **对齐 prompt 后再跑** |

> **理由（Leader 原话）**：两档的"不可比"结论相同，但**修法不同**；合并名字会让人以为处理方式一样。⇒ **档位合并、副标签必报**。

### 裁 2：⑦ 缺 env 取证 ⇒ **允许起跑但降级**（并在报告里写死一句）

> **允许起跑 ≠ 允许作结论。** 缺 env 取证的臂，**任何以"单变量"为前提的结论一律不得发布**，只能写「**代码同源，env 未验**」。

### 裁 3：`unset` vs 显式 `=0` **可区分**，D9i 判 **`single-variable-candidate`**

依据：`narration_enabled()` 为 `os.environ.get("LIFE_PROMPT_NARRATION","").strip().lower() in {"1","true","yes","on"}`
⇒ **unset 与 `=0` 走同一条代码路径**（都不在集合里）⇒ 行为等价；
且 `switch_proof.txt` 抓的是 `/proc/<pid>/environ` **真值** ⇒ 它证明的是"**当时该键不存在**"，强于"声明未设"。

**写法必须精确（引用纪律）**
- ✅「OFF 侧 `LIFE_PROMPT_NARRATION` 为 **unset**（行为等价于 `0`），ON 侧为 `1`；**env 差 1 键**」
- ❌ 不得写「OFF 侧 `=0`」（它是 unset，不是 0）
- ❌ 不得写「两臂 env 完全一致，只差一个开关」（"只差一个开关"暗示两边都有该键）

### 裁 4（补充，必须写进脚本）：**档位改名后的"工具↔矩阵"映射（防止同一件事两个名字）**

矩阵把 ③/⑤/⑥ 合并为 `NOT_COMPARABLE`，而**已入库**的 `arm_config_guard.py`（`4e14434`）仍输出旧名
`DIFFERENT_CODE` / `SAME_CONFIG` / `CANNOT-VERIFY`（rc `0/2/3`）。**工具已入库，本件不改工具**，故须写死映射：

| 工具输出（rc） | 矩阵档位 | 副标签 |
|---|---|---|
| `SAME_CONFIG` (0) | **入场券**（`SAME_CONFIG`） | —（是否单变量由 §2 env 维度决定） |
| `DIFFERENT_CODE` (2) | **`NOT_COMPARABLE`** | `diff=code_sha` 与/或 `diff=prompt`（以工具输出的 `checks` 为准） |
| `CANNOT-VERIFY` (3) | **`CANNOT-VERIFY`** | — |

> ⚠ **引用纪律**：跨文档引用时必须写「工具 `DIFFERENT_CODE`（≡ 矩阵 `NOT_COMPARABLE`）」，
> **禁止**只写一个名字，否则读者会在两个词之间来回猜（今天已因"同一件事两个值/两个名"栽过多次）。
> 若将来把工具升版对齐新名，须**新建 commit**并在件里登记旧名 deprecated —— **不得静默改名**。
