# D9z 判定件复核：六门五过、**一处算术错（`155` 应为 `153`）**、一处取证需补

> 作者：`repro-verifier`｜2026-11-01｜**只读**；未跑批、未改判定口径、未改被审件
> 任务：`T-D9Z-JUDGE-CHECK`
> **对象**：`v2/evidence/d9z-judgement-20261101.md` —— **以现版为准**：`9677d6f7f0d551b8…` / **101 行 / 6,816 B**（`master = 7616f05`）；初版 `1c12a3346065a4a0…`（已作废）/ 90 行 / 5,932 B（`master = 91a4c75`）。
> 两版**判据层零 diff**（§1–§5、§7 逐字节同），差异仅在 §6（`ROTATION` 归因自救）；§3.2 的 `155` 在**两版中都在**。
> **数据**：`v2/evidence/d9z-on_n16r56_s42/run.jsonl`（内容 sha·实测值 `1f0fec69fb2189c4…` / **90,532 行 / 44,305,670 B**）；OFF 基线 `v2/evidence/d9t-on_n16r24_s42/run.jsonl`（内容 sha·实测值 `af4c44d11dd22eb8…` / 33,877 行）

---

## 1. 三档与自校验：**PASS**

**复算命令**（口径按预登记 §1：`msg_uid` 去重、带 `reply_to` 且父存在、**无任何 place/round/thread 排除**）：
```python
msgs={}
for l in open("v2/evidence/d9z-on_n16r56_s42/run.jsonl",encoding="utf-8"):
    if not l.strip(): continue
    e=json.loads(l)
    if not e.get("type","").startswith("MSG"): continue
    pl=e["payload"]; msgs[pl["msg_uid"]]=(int(e["round"]),pl.get("place"),pl.get("thread_id"),pl.get("reply_to"))
ps=[msgs[u][0]-msgs[r][0] for u,(a,b,c,r) in msgs.items() if r and r in msgs]
from collections import Counter; print(len(ps), dict(sorted(Counter(ps).items())))
```

**我的输出**：
```
去重 MSG = 444；相邻对 = 278
gap 分布 = {0: 133, 1: 97, 2: 48}   三档之和 = 278
```

⇒ `{0:133, 1:97, 2:48}`、和 = 278 = 相邻对总数 ⇒ **自校验 PASS**，与判定件 §1 完全一致 ✓

---

## 2. `A` 与 `B` 逐数：**PASS**

| 项 | 判定件 | 我复算 | 判 |
|---|---|---|---|
| `A`：`gap=0` 绝对条数 ≥ 12 | 133 | **133** | ✅（余量 121 条） |
| `B`：`gap≥2` 占比 ≤ 0.2688 | 0.1727 | **48/278 = 0.17268** | ✅（余量 0.0961） |
| OFF 基线 `48/125 = 0.3840` | 0.3840 | **48/125 = 0.3840**（分布 `{1:77, 2:48}`、`gap=0` = **0**） | ✅ 与 `d9t-on_n16r24_s42` 一致 |
| 降幅 | 55.0% | `1 − 0.1727/0.3840` = **0.5503** | ✅ |

⇒ **全部命中**。OFF 基线的 `gap=0` 确为 **0**，是"`B` 的分母源头"这一说法成立。

---

## 3. `48 = 48`：**成立，判定件此条正确且重要**

| 臂 | `gap≥2` 绝对条数 | 分母 | 占比 |
|---|---|---|---|
| OFF（`d9t-on_n16r24_s42`） | **48** | 125 | 0.3840 |
| ON（本批） | **48** | 278 | 0.1727 |

⇒ 两臂 `gap≥2` **确为 48 与 48，一条没少** ✓ 判定件 §3.1 的表述——"'降 55.0%'全部来自分母 `125 → 278`；迟回条数一条没少""禁止写法：迟回减少 55%"——**核对无误，且这是本件最该保留的一句**。

---

## 4. L7 结构同门：**PASS**

```python
ps=[(u,msgs[u],msgs[r]) for u,(a,r) in msgs.items() if r and r in msgs]  # 同 §1 取邻对
同 thread_id  = sum(1 for u,a,b in ps if a[1]==b[1])            # 278/278
turn_index 父+1 = sum(1 for u,a,b in ps if a[2]==b[2]+1)         # 278/278
```

| 项 | OFF | ON（我复算） |
|---|---|---|
| 同 `thread_id` | 125/125 | **278/278** |
| `turn_index(本条) = turn_index(父条)+1` | 125/125 | **278/278**（反例 0，缺字段 0） |

⇒ 两臂结构混合一致 ⇒ **"`gap≥2` 占比可比较"成立** ✓

---

## 5. 身份与前提：**四项对，一项取证需补**

| 项 | 判定件 | 我复算 | 判 |
|---|---|---|---|
| FP 三元组 after == before | `(43a56c1, 283, 3625502c…)`（实测值·内容 sha），`fp_equal=YES` | `launch_cmd.txt`（未入库·臂目录内件）before/after 两段**逐字节相同**：均 `files=283`、`sha256=3625502cf90c28c5…`（实测值·内容 sha） | ✅ **且文件数已带**（我上次要求已落实） |
| `places.json` sha 两臂一致 | `c36c0f8776372f4e…`（实测值·内容 sha；两臂同值） | **结论对，取证不足**（见下） | ✅ 结论／⚠ 取证 |
| `degraded` 2729/2729 全 `False` | 全 False | `LLM_CALL` 总数 **2,729**，`degraded is True` = **0**；2,729 条**全部带** `degraded` 字段 | ✅ |
| `run.log` `Timeout` 行数 | 4 | `grep -c "Timeout" run.log` = **4**；`fault.log` = 0 B | ✅ |

### ⚠ `places.json`：结论对，但"两臂同值"这个取证方式不成立
**OFF 臂 `v2/evidence/d9t-on_n16r24_s42/launch_cmd.txt` 里没有 `places_sha256` 字段**（该件只有 `HEAD=cef1c58`、`files=282`、`fp_before/fp_after`）。⇒ 判定件写"**两臂同值**（内容 sha·实测值）"，但**ON 臂有记录、OFF 臂无记录**，"同值"不是从两臂各自记录比出来的。

**我改用 git blob 独立证实（结论相同）**：
```
git show cef1c58:code/config/places.json | sha256sum  → c36c0f8776372f4e36ec3912…
git show 43a56c1:code/config/places.json | sha256sum  → c36c0f8776372f4e36ec3912…
```
两者**完全相同**，且与 ON 臂记录的 `c36c0f8776372f4e…`（实测值·内容 sha）一致。**又**：实现提交 `9786d25` 对 `config/` 零改动（我已于 `d9z-impl-verified-by-verifier.md` §1 核过）⇒ 两臂 `places.json` 必然同内容。

⇒ **判：护栏②实质成立**，但判定件的**依据写法要改**为"两臂 `code/config/places.json` 同内容（`cef1c58` 与 `43a56c1` 的 blob sha 相同，`c36c0f87…`），OFF 臂 `launch_cmd` 未记录该字段"。**"OFF 臂无记录"这件事本身必须写出来**，否则读者以为两臂各贴了一个数在比。

### 附：墙钟两个数都成立，非矛盾
- `run.log`：`seconds=2725.7089`（进程内部计时）⇒ 判定件 2,725.7 s ✓
- `launch_cmd.txt`：`09:17:06 → 10:03:12` = **2,766 s**（外部窗，含启动/收尾 40 s）
⇒ 两者**不矛盾**，但件里只写 2,725.7 s 时，读者拿时间戳一减会得 2,766 s 而疑心。建议并列写"内部 2,725.7 s／外部窗 2,766 s（差 40 s 为启动开销）"。

---

## 6. 措辞门：**三项全过，但发现一处算术错**

| 检查 | 结果 |
|---|---|
| 是否出现"迟回减少 55%"类表述 | **无**。§3.1 反而**明写"禁止写法：迟回减少 55%"**，并给许可写法"迟回**占比**降 55.0%；迟回**条数**不变（48 → 48）" ✅ |
| `H` 段是否写对（不得单挂机制） | **现版对、初版错、但现版仍缺一条**——详见 §6.1 |
| mock-对-mock 是否显式声明 | **是**。§5.1 明写"OFF 等价性口径 = mock-对-mock，不是预登记字面的 vs-真跑链……**这是对预登记的一次口径修正，不藏**" ✅ |
| 不可跨世界线比较是否显式声明 | **是**。§5.2 明写"`cef1c58 ≠ master`（差 +37,800/−635）⇒ 读数不得与 `master` 世界线直接比较" ✅ |

### ❌ 算术错（本件唯一硬错，可复算）
判定件 §3.2 写：
```
### 3.2 新增 155 对（278 − 125）的去向
gap=0：  0 → 133  （+133，占新增 85.8%）
gap=1： 77 →  97  （+20）
gap≥2： 48 →  48  （  +0）
```
**`278 − 125 = 153`，不是 155。** 且分项 `+133 +20 +0 = 153`，**与标题的 155 自相矛盾**。

连带：`133/155 = 85.8%`，而 `133/153 = **86.9%**`。

**复算命令**：
```python
278-125            # 153
133+20+0           # 153
133/153            # 0.8693 → 86.9%
133/155            # 0.8581 → 85.8%（判定件用的分母，错）
```

⇒ **须更正两处**：`155` → **`153`**、`85.8%` → **`86.9%`**。

**影响评估**：这两处落在"新增对数的去向"说明段，**不进判据**（`A`/`B`/护栏①②③均不依赖它），故**不改变"通过"结论**。但**它会传播**——若后续报告引"新增 155 对"，后面所有人都会带着这个错数走。

---

### 6.1 `H` 来源：**我此前归因错了（`ROTATION`），Leader 的更正对；但现版三条仍缺一条（`L7`）**

#### (a) 我的错，先认：`ROTATION` 在本臂确实是死通道
我先前在 `d9z-impl-verified-by-verifier.md` §3 写"`ROTATION` 黑名单会随可见性变化"，**不成立**。代码核对（`code/life/agent.py`）：

```python
# agent.py:333
if not narration_rotation_enabled() or openings_enabled():
    tail = _NARRATION_TAIL_ON[kind]                      # ← 本臂走这里
else:
    tail = _NARRATION_TAIL_ON_TPL[kind].format(
        narration_example(kind, agent_id, round_no))     # ← agent.py:336，本臂不执行
```
本臂 `OPENINGS=1` ⇒ `openings_enabled()` 为真 ⇒ 短路进第一分支，`narration_example(...)`（`agent.py:149`）**从不被调用** ⇒ **`ROTATION` 输入通道是死的**。Leader 与 `dialogue-core-dev` 的更正**正确**，`"配置 =1" ≠ "通道生效"` 这次是我踩的。

#### (b) 但现版 §6 的三条来源**仍缺第四条**，而缺的这条**恰是唯一有 prompt diff 实证的**
现版三条：①`OPENINGS` 出口清单 ②`S-1` 让位 ③语料变了。**均正确，但都不产生我在 `wiring_proof.json` 里看到的那两行 diff。**

那两行是：
```
-这几个开头镇上最近已经有人用过了，别再用：「早上好呀」。
+这几个开头镇上最近已经有人用过了，别再用：「抬手把刚」、「早上好呀」。
```

**这段文案的来源不是 `agent.py`，是 `code/life/l7_structural.py`**：

```python
# l7_structural.py:161  plan(...) 的 docstring：
#   `recent`：该 agent **可见**的最近台词（新→旧，来自 `recent_bodies(wv)`），
#             用于生成禁忌开头清单。
# l7_structural.py:175
"banned": _banned_openers(recent),
# l7_structural.py:190（render 内）
seg += ("\n这几个开头镇上最近已经有人用过了，别再用："
        + "、".join(f"「{b[:LINE_CHARS]}」" for b in banned) + "。")
```

`wv` = `WorldView` = **可见事件**。⇒ **可见性变宽 → `recent_bodies(wv)` 集合变 → `banned` 变 → prompt 变**，这条链**真实、可执行、且已由 `wiring_proof.json` 的 diff 实证**。

而 `LIFE_PROMPT_L7_STRUCT` **默认 ON**（`agent.py:35` 注释：`# L-7 结构臂（env LIFE_PROMPT_L7_STRUCT，**默认 ON**）`）⇒ 本臂必然在跑这条通道。

**为什么现版会漏**：§6 表格的表头限定"依据（本臂代码 `code/life/agent.py`）"——**把视野锁在 `agent.py` 一个文件里，而 L7 在另一个模块**，锁死就看漏。**这正是"在错误的文件里找证据，找不到就判不存在"**。

⇒ **须补第 ④ 条**：
| # | 来源 | 依据 |
|---|---|---|
| ④ | **`L7` 结构去重的禁忌开头清单** | `code/life/l7_structural.py:175`（`banned = _banned_openers(recent)`）+ `:190`（`BAN_HEAD` 文案）；`recent = recent_bodies(wv)` 取自**可见事件**；`LIFE_PROMPT_L7_STRUCT` 默认 ON |

**结论不变但更硬**：`H` 仍是合成量、仍不得单挂机制——**只是"合成"的成分里，L7 这条比 ①②③ 都更直接**（①②是静态配置差、③是语料规模差，只有 ④ 是"可见性 → prompt 内容"的**实时通道**）。

---



**本判定可用。**

理由：六门中五门全过且我已独立复算命中——三档 `{0:133,1:97,2:48}` 和 278、`A=133≥12`、`B=48/278=0.1727≤0.2688`、OFF 基线 `48/125=0.3840`、**`48 = 48` 成立**、L7 双 278/278、FP 三元组前后逐字节相等且带文件数 283、`degraded` 0/2,729、`Timeout` 4 行、措辞三门全过；**判据本身无瑕疵，判定逻辑不依赖任何我算不出的数**。

**但须随件勘误两处（不改结论）**：
1. **§3.2 `155` → `153`、`85.8%` → `86.9%`**（`278−125=153`，分项合计亦 153）；
2. **§1 护栏② 依据改写**：`places.json` 不是"两臂各记录同值"，而是"`cef1c58` 与 `43a56c1` 的 `code/config/places.json` blob sha 相同（`c36c0f87…`（实测值·内容 sha））；**OFF 臂 `launch_cmd` 未记录该字段**"。

**另须补一处（§6.1，判据外但要紧）**：§6 的 `H` 来源表**补第 ④ 条 `L7` 结构去重**（`l7_structural.py:175/190`，`recent` 取自可见事件），并把表头"依据（`code/life/agent.py`）"放宽到 `code/life/**`——**锁在单文件里就会漏这条，而它是唯一有 prompt diff 实证的一条**。

**另建议**（不属勘误）：§2 墙钟并列写"内部 2,725.7 s／外部窗 2,766 s"，免得读者拿时间戳相减起疑。
