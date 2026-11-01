# D5 补字段与定语义（**设计件**，只读产出；不跑批、不改 `code/`）

> 作者：eval-researcher｜2026-11-01｜性质：**设计件**（不含阈值、不含判据编号）
> 上游：`v2/refs/_proposed-lifeliness-criteria.md`（该时点值·非当前版 `c91153c6…`）已并入候选池 §3.8；D5 被裁为「**当前不可判（资格保留）**」
> **本件不跑批、不改 `code/`、未引用任何未入库文件。**

## 1. 现状证据（`refs` / `body_ref` 从未落值）

| 日志 | sha256 | MSG | `payload.refs` 非空 | `payload.body_ref` 非空 | `ctx.memory_refs` 非空 |
|---|---|---|---|---|---|
| `v2/evidence/d9z-on_n16r56_s42/run.jsonl` | **`1f0fec69fb2189c4877840fc784fb12cacaa0857aa6d190a30520c9d97204f4d`** | **444** | **0** | **0** | **0** |
| `v2/evidence/cycle36_f3_off_n16r84_seed42/run.jsonl` | **`f7ace309706f02e7b6aa197d42ef7fb21c608cc22b1b03cc8add833360596e90`** | **678** | **0** | **0** | **0** |

复算命令：
```python
import json
for p in ("v2/evidence/d9z-on_n16r56_s42/run.jsonl","v2/evidence/cycle36_f3_off_n16r84_seed42/run.jsonl"):
    n=r=b=m=0
    for ln in open(p,encoding="utf-8"):
        if '"MSG_' not in ln: continue
        d=json.loads(ln)
        if not str(d.get("type","")).startswith("MSG"): continue
        pl=d["payload"]; n+=1
        r+= 1 if pl.get("refs") else 0
        b+= 1 if pl.get("body_ref") else 0
        m+= 1 if (pl.get("ctx") or {}).get("memory_refs") else 0
    print(p, n, r, b, m)
```
⇒ **跨两批、两种规模（444 / 678）全为 0** ⇒ 不是本批偶发缺失，是**这两个键从未被写入**。

## 2. 落值方案（**不是"写入指针就行"**）

### 2.1 先分清两个键是什么（这决定"该写什么"）

| 键 | 代码落点 | 它是什么 | 现状 |
|---|---|---|---|
| `payload.refs` | `code/life/agent.py:1403 / :1477 / :1576` 三处**硬写 `"refs": []`** | 设计意图 = **本条消息"转述/引用"了哪些既有消息**（`code/life/ports.py:57`：`"refs": [<msg_id>|<event_seq>]，转述类必填；原创为 []`） | 恒为 `[]` ⇒ **设计有、实现未接** |
| `payload.body_ref` | `code/life/memory.py:246/250`、`agent.py:1090/2144` | **side storage 的叙事正文指针**（`side://narrative/<agent>/<nid>.txt`），用于 `NARRATIVE.body_ref` / `MEMORY_WRITE.body_ref` | MSG 上**本就不该有**（它不是消息字段）⇒ **不要往 MSG 写 `body_ref`** |
| `ctx.memory_refs` | `code/life/agent.py:1276-1281`（`self._mem_refs` → `ctx["memory_refs"]`），由 `_memory_line()`（`agent.py:1739`）填充 | **F-6 臂**（跨天记忆进对话）的审计键：**本条消息生成时，提示词里实际注入了哪些跨天记忆的 `mem_id`** | F-6 关着 ⇒ `_mem_refs` 恒空 ⇒ 键不出现 |

### 2.2 谁写 / 写哪些字段 / 什么触发

| 项 | 结论 |
|---|---|
| **谁写** | ① `agent.py` 三个 MSG 落盘点（`:1403 / :1477 / :1576`）—— 把 `"refs": []` 换成实测值；② `_memory_line()` 已在写 `self._mem_refs`，`_ctx_snapshot()` 已把它落进 `ctx.memory_refs`（**这部分不用改，只需开 F-6**） |
| **写哪些字段** | **`payload.refs`: `list[dict]`，每项 `{"kind": "msg"│"mem", "id": <msg_uid│mem_id>, "day": <int>}`** —— 只放**被指名的引用对象**，不放对话对象、不放 `reply_to`（那是另一回事）；**`ctx.memory_refs` 保持现状（`list[mem_id]`）** |
| **什么触发** | ① **F-6 记忆注入**：`_memory_line()` 实际注入时逐条记 `mem_id`（已实现，开开关即有）；② **MSG 侧转述**：仅当消息属"转述类"（`ctx.trigger ∈ {polite_reject, whisper, rel_maintain, counter_propose}` 且正文出现指向旧事的锚点）时，把被转述的 `msg_uid` 记入 `refs`；**原创/回答类保持 `[]`** |

### 2.3 定性：`refs` = **索引/缓存**，不是观测面（Leader 2026-11-02 拍板）

**决策**：`refs` **不改 prompt、不做"模型自述"** ⇒ 因此它的定性是：

> **`refs` 提供索引，不是新信息；不得作独立证据。**

理由：要让 `refs` 成为独立观测面（模型**自述**它引用了哪条旧事），唯一干净的做法是**改 prompt 让模型显式声明**——那是**新变量**，须另立预登记（记作 **D5.2 候选**），不能塞进 D5-fill。

**直接后果（必须一并写死）**：
> 既然 `refs` 只是索引，**「D5 能不能算」实际取决于「§3.2 的 ② 条（正文出现具体锚点）能不能算」**——`refs` **不提供新的可算性**，只提供**算得更快**。
> ⇒ 若 ② 条本身算不出（例如锚点表没有定义），**补了 `refs` 也白补**。不得以为"补字段就解锁 D5"。

**同族纪律（`three-questions-before-any-number.md` §17「因果句必须同侧」同族）**：
> **`refs` 若由规则抽取，则它与 ② 条同尺子 ⇒ 二者不得在同一结论里各算一次证据。**
> （同一个判定的两次申报 ≠ 两个独立证据；与"因果句必须同侧"同族：**要么同侧同源，要么分开报，不许拿两次申报凑成两条论据**。）

**⚠ 一句必须写死的边界**：**`payload.refs` 不要塞"本条引用的 msg_uid"以外的任何东西**——尤其**不要**把 `reply_to` 的值复制进 `refs`。`reply_to` 只回答"回的是哪条"（同线程相邻），`refs` 要回答"提到了哪件旧事"，**两者混写会让 D5 变成 `reply_to` 的同义词**（那就是**又一次"名义值顶替"**）。

## 3. "重提旧事"的语义定义（**可判真、可复算**）

### 3.1 两个口径必须分开（这是本件的重点）

| 口径 | 定义 | 现有数据 | 用途 |
|---|---|---|---|
| **同线程回指** | `reply_to` 指向的父消息 = 相邻回合的"接话" | **`reply_to` 已有值**（本批 278 对可解） | **已有**（`K-1` 口径）——**不算"重提旧事"** |
| **跨天重提**（D5 要测的） | 消息正文指名用到**严格更早 `day`** 出现过的**具体锚点**（人名/物名/待办），且不是"回复当前对话对象" | **无观测面**（`refs`/`memory_refs` 全空） | **D5 的判据口径** |

### 3.2 操作化定义（三条件全满足才计 1，逐条可判真）

记消息 `m`（`day = d_m`）、其正文 `body`：

1. **跨天**：存在引用的源消息集合 `S = {s : s.day < d_m}`（严格更早，同一天不算）；
2. **指名**：`body` 中出现 `s` 的**具体锚点**（锚点 = 可指名的物/人/待办；**代词不算**、`这/那` 不算、地点名不算）；
3. **非承接**：该锚点**不是** `reply_to` 父消息里刚说过的（= 不是"接上一句"）。

⇒ `cross_day_restate(m) = 1` 当且仅当 1∧2∧3；分子 = 满足条件的 MSG 条数，分母 = **全部 MSG 条数**（首批须同时报"有旧锚点可提的 MSG 条数"作参照）。

**为什么第 3 条必须有**：否则"刚说完又提一遍"会被算成跨天重提（那是同线程回指，`reply_to` 已能测）——**两个口径混算会让 D5 与 `K-1` 双计**。

### 3.3 为什么不能只靠 `ctx.topic`（Leader 17:18 已裁定）
`ctx.topic` 复现率能算，但它测"**同一话题在别的天再次出现**"，不是"**记得旧事**"（11 个档太粗，两天的 `gift` 可能毫无关系）⇒ **只能作观察量，不得作 D5 证据**。

## 4. 代价评估

| 项 | 结论 |
|---|---|
| **改动面** | **`code/life/agent.py` 三处 `"refs": []` → 实测值**（约 3 行 + 一个取数函数）；`_memory_line()`/`_ctx_snapshot()` **不需改**（F-6 已在写 `ctx.memory_refs`）；**不动 `engine/` `orchestration/` `config/`** |
| **是否需要新跑批** | **需要**。①`ctx.memory_refs` 只有 F-6 开（`env LIFE_PROMPT_MEMORY_F6=1`）时才落值 ⇒ 必须新跑；②MSG 侧 `refs` 的"转述类"判定依赖新写的取数逻辑 ⇒ 老日志无法回填（原始文本里没有"被转述的是哪条"这一信息，**不可事后重建**） |
| **对旧日志的影响** | **零**：F-6 默认关 ⇒ `_mem_refs` 空 ⇒ `ctx.memory_refs` 键不出现，payload 与改动前**逐字节一致**；`refs` 改动只影响开机制后的新日志 |
| **新旧能否并列** | **只能并列"口径相同"，不得并列"数值应相同/可复现"**。可证的是**代码路径等价**（`git diff` 逐 hunk + F-6 关时 payload 键集与旧全同）；**不可证的是跨批文本复现**（LLM 非确定）⇒ **新 OFF 臂只能当"同口径新批"，不是"复现件"** |
| **等价性证明成本** | 代码 diff 审查 + 键集比对 ≈ 半小时（只读）；**不建议**为此重跑（省不了事，还背"跨批不可复现"） |
| **是否改 `engine_version` 指纹** | `agent.py` 属 behavior code，**会变** ⇒ 新日志 `code_sha` 与旧日志不同，**新旧不可直接并列**（须按 §14 姊妹条声明口径变更） |

## 5. 边界（**不得设计出"写完就算能算"的假象**）

1. **落值 ≠ 能算**：`ctx.memory_refs` 落值只给出"注入了哪些 `mem_id`"，要算"重提旧事"**还需 §3.2 的三条判定**（跨天/指名/非承接）——**前者是原料，后者是尺子**；
2. **`body_ref` 不要往 MSG 写**：它是 side storage 的正文指针（`memory.py:246/250`），MSG 上出现会让"消息引用"与"叙事正文指针"混为一谈；
3. **`refs` 不得复制 `reply_to`**：混写会让 D5 退化成 `reply_to` 的同义词（= 名义值顶替）；
4. **`ctx.topic` 复现率不是 D5**（§3.3）；
5. **`refs` 是索引不是观测面**（§2.3）：补它不增加可算性，只加快计算；D5 的可行性挂在 ② 条上；
6. **新旧不可并列数值**：新 OFF 臂是"同口径新批"，**不是复现件**；
7. 本件**不含任何阈值**；判据编号与阈值由预登记另立（阈值须按噪声底实测 + 外生参照系换算，两者并列）。

## 6. 率的定义（`scripts/check_tables.py --strict` 必填表一）

| 率名 | 分子 | 分母 | 计算式 | 纳入排除 |
|---|---|---|---|---|
| `cross_day_restate_rate`（D5 主口径） | 满足 §3.2 三条件的 MSG 条数（跨天 ∧ 指名锚点 ∧ 非承接） | 全部 MSG 条数（本批 444） | 分子 ÷ 分母 × 100% | **纳入**：DM/PUBLIC/GROUP 全部 MSG；**排除**：同一天内引用（非跨天）、代词/`这`/地点名（非指名）、`reply_to` 父消息刚说过的锚点（属同线程回指）、`place=None` 的 `MSG_PUBLIC` 计入分母但不可能命中（无 place 不等于无正文） |
| `refs_coverage_rate`（索引覆盖率，非判据） | `ctx.memory_refs` 非空的 MSG 条数 | 全部 MSG 条数（本批 444） | 分子 ÷ 分母 × 100% | **纳入**：同上分母；**排除**：无（该率只描述"索引落了多少"） |

## 7. 外推与假定（`scripts/check_tables.py --strict` 必填表二）

| 外推式 | 假定不变的量 | 值来源 |
|---|---|---|
| **不外推**：D5 只在本批（`d9z-on_n16r56_s42`，n16×r56 seed42，444 MSG）内成立；跨批/跨规模须重算 | ① 片段与 MSG 的口径（`extract_messages` 同源）；② 锚点判定所用的闭集（**尚未定义 ⇒ 这正是本件指出 D5 当前不可算的原因**）；③ F-6 开时的 `ctx.memory_refs` 落值链路（`agent.py:1276-1281`） | ① 本批实测：`refs`/`body_ref`/`ctx.memory_refs` 均 0/444；② 另一批 `cycle36_f3_off`（678 MSG）同 0；③ 代码落点 `agent.py:1403/1477/1576`、`memory.py:246/250`、`ports.py:57` |

---
### 附：本件可复算的交叉证据（均为只读）
- `refs` 设计意图：`code/life/ports.py:57`（`转述类必填；原创为 []`）—— **设计早就写了，实现没接**；
- F-6 审计键：`code/life/agent.py:1276-1281` + `_memory_line()`（`agent.py:1739`）—— **`ctx.memory_refs` 是现成管道，只需开开关**；
- `MEMORY_WRITE.refs` 已有值路径：`agent.py:2150`（`"refs": list(g["source_mem_ids"])`）—— **记忆账本侧本来就有 refs，MSG 侧没有**。
