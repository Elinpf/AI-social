# R17 · C-1「世界行进对话」收口：机制接线成立、**世界几乎没发生什么事**、效果不可判

> 撰写：report-writer（本轮）｜数据来源：`run_worldline_c1_ctrl_n16r84_seed42`（ctrl 臂）+ `run_worldline_c1_a1_n16r84_seed42`（a1 臂）
> 跑批代码身份：worktree `.worktrees/worldline-c1-n16r84` @ **`af1dffc61040adc97c828b4927ac3935dbef2d1b`**
> 报告初始 HEAD（主树）：`793418a5b1fc2163b5d58f503b4da0ca62cd6cac`；本报告最终绑定 sha 见 §10。
> 分层标记：【事实】= 可直接复算的原值；【读数】= 需指明口径与分母的统计量；【判断】= 作者推断，可被推翻；【未完成】= 本轮没做到。
> 口径纪律：**不给「生活气息总分」**；F 维度按 R4 编号；**机制侧生效 ≠ 效果达成**。

---

## 0. 摘要 TL;DR

### 0.0 判定表（分层给，合并即违约）

| 层 | 判定 | 硬依据（可复算） |
|---|---|---|
| ① 机制侧接线（开关→提示词） | **成立（PASS）** | `prompt_diff_proof.txt`：`VERDICT=PASS single_variable_prompt_diff`，六项断言全 True |
| ② 世界事件登记（导演→账本） | **成立** | round 30 落 `WORLD_DIRECTIVE` + `WORLD_GROUP_EVENT` 各 1 条 |
| ③ 世界层派生参数（`world_params`） | **成立，但口径有误** | round 30–35 `market_scarcity_bp={"global":2000}`；配置解析值应为 **1000** ⇒ **双重计数（本轮新发现，§3.5）** |
| ④ 触达面（世界事件→居民） | **只有一条路径**：C-1 提示词行；**记忆/感知侧未接入** | 静态：`WORLD_*` 不在 `_SALIENT_EVENTS`；`WORLD_C1_EVENT_TYPES` 是 life 层唯一引用点 |
| ⑤ 剂量（事件供给） | **极低**：84 回合 **1 次**指令；覆盖 **6/84 = 7.14%** 回合 | §3.3/§3.4 |
| ⑥ **效果（对话是否更生活气息）** | **不可判（不可判，不是"无效"也不是"改善"）** | 剂量不足 + 窗口分母 48 条消息（<68 判读下限） |

### 0.1 机制侧存在性事实（可判，且与效果无关）

- 【事实】C-1 是**纯提示词开关**：`LIFE_PROMPT_WORLD_C1` ∈ {1,true,yes,on}，默认 **OFF**；OFF 时 `_world_line()` 返回**空串**，两个提示词的拼接串与接入前**逐字节一致**（`code/life/agent.py:1257` 起）。
- 【事实】ON 相对 OFF 的**唯一增量是提示词里的一行**：`dialogue_prompt` 351→407 字符（+1 行）、`reply_prompt` 359→415 字符（+1 行），去掉该行后两臂**逐字节相同**（§2.2 六项断言）。
- 【事实】C-1 **不写记忆、不发事件、不改 `state_hash`、不改配置**（改开关只改提示词文本）。

### 0.2 结论（唯一允许的形态）

> **C-1 的接线是可验证成立的；但它要注入的「世界/场所状态」在本批里近乎不存在——84 个回合只发生 1 次世界事件（覆盖 6/84 = 7.14% 回合）。因此本轮不出效果结论：既不写「世界行进让对话更生活气息」，也不写「无效」。**
>
> 附带登记一条本轮新发现的**口径缺陷**：`world_params()` 把同一条世界指令计了两次（`market_scarcity_bp` 1000→2000）。所以本轮 a1 臂实际看到的世界强度本身就是**虚高一倍**的——这与"剂量极低"并列，是本轮真正的技术产出。

---

## 1. 本轮维度与边界

### 1.1 为什么做 C-1（而不是再调提示词套路）

- 【事实】CYCLE-01 §五 把「触发/承接机制」与「提示词正向插槽」列为下一步；D2.1 触发族（A1-回复预算、A2-对未回对端不再发起、`max_turns_per_round` 三档）已证明**纯配额旋钮抬不动 `p50`（恒 1）**，见 `reports/CYCLE-01-20261022.md` §三与 `v2/evidence/d2_trigA2_result.md`。
- 【判断】对话层已经反复证明"套路化能被压下去（R12/R16）、但具体性/承接上不来"。C-1 走的是**另一条供给端**：不问"怎么说得更像人话"，而问"**居民有没有可说的世界**"。这是生活气息的前置条件，不是措辞技巧。

### 1.2 本轮**不做**的事（写死，防越界）

1. **不改任何代码**（`code/life`、`code/orchestration`、`code/config`、`code/engine` 一律不动）；C-1 开关本身是本轮上游成员在 `af1dffc` 上已就绪的实现，本报告只做**观察与复算**。
2. **不修** §3.5 的双重计数：**已登记未修**（修复须开分支 `feat/world-params-double-count`，与 `af1dffc` 不可对照，留待下一周期）。
3. **不写效果结论**：剂量不足 ⇒ 不给方向、不给幅度、不给"带外"。

### 1.3 「生活气息」在这里指什么（可判的口径）

| 口径 | 单位 | 本报告用法 |
|---|---|---|
| F-1 非功能性闲聊占比 | per-message | 仅作**背景读数**引用（本轮不判定） |
| F-2b 多话题线程占比 | per-thread | 背景引用，**注意官方口径已恒 0（死尺子）** |
| F-5 习惯强度 | per-agent | 背景引用，**已饱和 100%** |

> 三维的完整复算与"下一轮做哪个"的判决见上游产物 `team-workspace/recon/f1-f2b-f5-baseline.md`（recon-scout），本报告只引用其结论、不重复其证据。

---

## 2. 机制事实：C-1 实现与单变量证明

### 2.1 开关与消费点（静态，可 grep）

```bash
cd <repo>/.worktrees/worldline-c1-n16r84
grep -rn "LIFE_PROMPT_WORLD_C1" --include=*.py code/ | head
```

真实输出：

```
code/life/agent.py:76:WORLD_C1_ENV = "LIFE_PROMPT_WORLD_C1"
code/life/agent.py:107:    """C-1 臂开关（env `LIFE_PROMPT_WORLD_C1` ∈ {1,true,yes,on}）；默认关。"""
```

【事实】`_world_line()`（`code/life/agent.py:1257`）取材三处，全部为**已有字段**：① `wv.location` 场所（`config/places.json::name_cn` 人话名）；② `wv.visible_events` 里的 `WORLD_GROUP_EVENT/WORLD_DIRECTIVE`（须 `directed=true` 且 `[start,end)` 覆盖当前回合、且 `round-start ≤ 24`）；③ `market_scarcity_bp.global ≥ 1000` 时补一句「集市上东西有点紧俏」。

相关常量：

| 常量 | 值 | 位置 |
|---|---|---|
| `WORLD_C1_WINDOW_ROUNDS` | 24 | `agent.py:77` |
| `WORLD_C1_MAX_EVENTS` | 2 | `agent.py:79` |
| `WORLD_C1_SCARCITY_MIN_BP` | 1000 | `agent.py:81` |
| `WORLD_C1_EVENT_TYPES` | `("WORLD_GROUP_EVENT","WORLD_DIRECTIVE")` | `agent.py:85` |

### 2.2 单变量证明（`prompt_diff_proof.txt` 原文）

来源：`v2/evidence/run_worldline_c1_a1_n16r84_seed42/prompt_diff_proof.txt`（sha256 `bd1eb75c…`）

```
code_sha=af1dffc61040adc97c828b4927ac3935dbef2d1b
switch_env=LIFE_PROMPT_WORLD_C1

== OFF 臂（生产默认：变量不存在）==
_world_line=''
dialogue_prompt sha256=d80df99940ad5020eb0b3158c599197ab3e1c710fb03b0cf1a6070099b515a16 len=351 lines=5
reply_prompt    sha256=3cf4bcae0f0534d297bde42f632778c621c99f636a4cdc62b711f6145b7029ba len=359 lines=8

== ON 臂（LIFE_PROMPT_WORLD_C1=1）==
_world_line='\n你眼下在市集；镇上气氛有点紧；镇上在办节庆；集市上东西有点紧俏。（用自己的话顺口带一句，不要照抄这句的措辞。）'
dialogue_prompt sha256=119c9f9f5d2b648d58fa1f38e74d438c071005d6b3b70b2fbd311d247e37bdd3 len=407 lines=6
reply_prompt    sha256=3d76448f1250059745bfa56dcd667d530f3a3f51bafb93e0bec83bdbee22a324 len=415 lines=9

== 单变量断言 ==
A. OFF ⇒ _world_line 为空串                 : True
B. ON  ⇒ 插入段恰一行（含 1 个换行）        : True
C. ON._dialogue_prompt 去掉插入段 == OFF     : True
D. ON._reply_prompt    去掉插入段 == OFF     : True
E. dialogue 行数 +1                          : True
F. reply    行数 +1                          : True

VERDICT=PASS single_variable_prompt_diff
```

【事实】六项断言全 True ⇒ **单变量成立**：两臂之间只剩"提示词里有没有这一行"。注意该证明用的是一份**合成夹具**（同时带 tension/festival/scarcity），不是本批真实可见事件——它证明的是**机制形状**，不是**本批剂量**。

---

## 3. 剂量事实：世界导演到底多久发生一次事

### 3.1 配置声明 → 剂量曲线 → 解析后剂量（可复算）

```bash
cd <repo>/.worktrees/worldline-c1-n16r84/code
PYTHONPATH=. python3 -c "
import json; from engine.world_director import resolve_dose
cfg=json.load(open('config/world_director.json'))
print('curve', cfg['dose_curve'])
for m in ('wd.festival','wd.edict','wd.tension'):
    print(m, 'declared', cfg['mechanisms'][m]['dose'], '-> resolved', resolve_dose(cfg,m), 'enabled', cfg['mechanisms'][m]['enabled'])
"
```

真实输出：

```
curve conservative
wd.festival declared {'prob_bp': 100, 'capacity': 40, 'slots': 3} -> resolved {'prob_bp': 50, 'capacity': 40, 'slots': 3} enabled True
wd.edict declared {'prob_bp': 50, 'slots': 6} -> resolved {'prob_bp': 25, 'slots': 6} enabled True
wd.tension declared {'prob_bp': 80, 'scarcity_bp': 2000, 'slots': 6} -> resolved {'prob_bp': 40, 'scarcity_bp': 1000, 'slots': 6} enabled True
```

【事实】`conservative` 曲线把 `prob_bp` **减半**（5000/10000）。当前**启用**的机制只有 3 个：`wd.festival`（100→50bp）、`wd.edict`（50→25bp）、`wd.tension`（80→40bp）；其余 7 个机制 `enabled=false`。

### 3.2 期望事件数算式（既是本轮解释，也是下一周期的目标算式）

```
每回合命中概率 = Σ(启用机制解析后 prob_bp) / 10000
            = (50 + 25 + 40) / 10000 = 115bp = 1.15%/回合
84 回合期望指令数 = 84 × 1.15% = 0.966 条
```

【读数】观测值 = **1 条**（+ 其配对 `WORLD_GROUP_EVENT` 1 条，属同一次介入的两种落账）。与期望值 0.966 一致 ⇒ **不是 bug，是配置数学**：这套 `conservative` 剂量天生就是"一百回合里发生一次"。

### 3.3 实际登记（ctrl 臂，两条事件原文）

```bash
grep -n 'D-30-wd.tension\|GE-30-wd.tension' v2/evidence/run_worldline_c1_ctrl_n16r84_seed42/run.jsonl | cut -c1-260
```

真实输出（2 行）：

```
39215:{"actor":"DIRECTOR",...,"payload":{"directed":true,"directive_id":"D-30-wd.tension","dose":{"prob_bp":40,"scarcity_bp":1000,"slots":6},"dose_curve":"conservative",...
39216:{"actor":"DIRECTOR",...,"payload":{"affected_scope_count":0,"directed":true,"directive_ref":"D-30-wd.tension","end_round":36,"group_event_id":"GE-30-wd.tension",...
```

字段摘要：

| 字段 | 值 |
|---|---|
| `kind` / `mechanism_id` | `tension` / `wd.tension` |
| `issued_round` / `effective_from_round` / `expires_round` | 30 / 30 / 36 |
| `dose`（解析后） | `prob_bp=40, scarcity_bp=1000, slots=6` |
| `rng_branch` | `roll_bp=8 < prob_bp=40` ⇒ 命中 |
| `scope` | `{"level":"global","place":null}` |
| `affected_scope_count` | `0`（**字面量，见 §4.3，不可当读数**） |

### 3.4 覆盖回合占比（本报告的核心"剂量"读数）

| 读数 | 值 | 定义 |
|---|---|---|
| 世界指令条数 | **1** | `WORLD_DIRECTIVE` 计数（84 回合内） |
| 世界群体事件条数 | **1** | `WORLD_GROUP_EVENT` 计数（同一介入） |
| 事件生效回合区间 | **30–35**（6 回合） | `[effective_from_round, expires_round)` |
| **回合覆盖率** | **6/84 = 7.14%** | 生效回合数 / 总回合数 |
| 窗口内对话消息 | **48 条**（DM/PUBLIC/GROUP 合计） | §5.4 |
| 窗口内对话线程 | **16 个** | 同上 |

全批 686 条消息逐回合分布（供核对"48 条"不是抽样）：

```
[(0,12),(1,12),(3,13),(4,13),(5,1),(6,15),(7,14),(8,2),(9,9),(10,6),(11,1),(12,13),(13,15),(14,1),
 (15,12),(16,12),(18,11),(19,12),(20,1),(21,8),(22,7),(23,1),(24,13),(25,14),(26,1),(27,12),(28,13),
 (29,2),(30,12),(31,16),(32,1),(33,9),(34,6),(35,4),(36,12),(37,12),... ,(83,2)]
```

【判断】即使把窗口撑到整个 84 回合，世界层也只提供**一个**情境（"气氛有点紧"）；窗口内只有 **48 条**消息 —— 低于 F 系列与措辞层判读常用的 68 条下限。**没有分母就没有可判读性，这一条决定了效果必须判"不可判"。**

### 3.5 🔴 本轮新发现：`world_params()` 把同一条世界指令计了两次

**登记状态：`reports/R7-world-event-wiring.md` 未登记；本轮新发现；发现人 = 本轮 report-writer；已登记未修。**

复算命令（只读调用仓库纯函数，不改任何文件）：

```bash
cd <repo>/.worktrees/worldline-c1-n16r84/code
PYTHONPATH=. python3 - <<'PY'
import json
from engine.world_params import world_params
from engine.world_director import resolve_dose
p="<repo>/v2/evidence/run_worldline_c1_ctrl_n16r84_seed42/run.jsonl"
d=[];g=[]
for line in open(p,encoding="utf-8"):
    e=json.loads(line)
    if e.get("type")=="WORLD_DIRECTIVE": d.append(e)
    if e.get("type")=="WORLD_GROUP_EVENT": g.append(e)
cfg=json.load(open("config/world_director.json"))
print("config 声明(原始) wd.tension dose:", cfg["mechanisms"]["wd.tension"]["dose"], "curve:", cfg["dose_curve"])
print("config 解析后 dose:", resolve_dose(cfg,"wd.tension"))
print("仅 DIRECTIVE  :", world_params(d,31,{"world_director":cfg}))
print("仅 GROUP_EVENT:", world_params(g,31,{"world_director":cfg}))
print("两者都在      :", world_params(d+g,31,{"world_director":cfg}))
PY
```

真实输出：

```
config 声明(原始) wd.tension dose: {"prob_bp": 80, "scarcity_bp": 2000, "slots": 6} curve: conservative
config 解析后 dose: {"prob_bp": 40, "scarcity_bp": 1000, "slots": 6}
仅 DIRECTIVE  : {"activity_weight": {}, "resource_factor_bp": {}, "market_scarcity_bp": {"global": 1000}, "active": ["D-30-wd.tension"]}
仅 GROUP_EVENT: {"activity_weight": {}, "resource_factor_bp": {}, "market_scarcity_bp": {"global": 1000}, "active": ["D-30-wd.tension"]}
两者都在      : {"activity_weight": {}, "resource_factor_bp": {}, "market_scarcity_bp": {"global": 2000}, "active": ["D-30-wd.tension", "D-30-wd.tension"]}
```

判读：

1. 【事实】单条记录各给 `scarcity_bp=1000`（**= 配置解析后的正确值**）；两条并存时累加成 **2000，恰为配置值的 2 倍**；`active` 里同一个 `directive_id` **出现两次**。
2. 【事实】根因两处：`code/engine/world_params.py:44-59` 的循环对 `("WORLD_GROUP_EVENT","WORLD_DIRECTIVE")` **两类都按 `payload.params` 累加**；而 `code/engine/hooks/world_director.py:37,46-49` 把**同一个 `directive_id` 同时写进两类事件**（`WORLD_GROUP_EVENT.directive_ref == WORLD_DIRECTIVE.directive_id`）。
3. 【判断】**影响面**：配置声明剂量 ≠ 实际生效剂量。凡以配置 `dose` 推算期望事件数 / 目标密度的分析都会算错（本轮 §3.2 的"期望 0.966 条"不受影响，因为它是 `prob_bp` 侧；但**任何以 `scarcity_bp` 为目标的调参、以及 `WORLD_C1_SCARCITY_MIN_BP=1000` 的门槛判断都会失真**——阈值 1000 在单条记录时恰好等号成立，双计数下变成 2 倍余量，阈值实际更松）。
4. 【事实】**对本轮 C-1 结论的直接影响**：ctrl 臂实际 scarcity = **2000**（不是配置的 1000）⇒ a1 臂所见的"世界强度"本身也是**虚高一倍**的。因此本轮"剂量极低"的表述要带这句反讽式补充：**供给次数极低（1 次），但每次的作用强度被计了 2 倍**——两个偏差方向相反，净效应不可预判，这也是效果不可判的第二个理由。
5. 【未完成】修复不在本轮做。正确做法是在 `world_params` 侧按 `directive_ref` 去重（或让 `WORLD_GROUP_EVENT` 不重复携带 `params`），须开分支 `feat/world-params-double-count`，**新 sha 与 `af1dffc` 不可对照**（不能与本批数据并列做 A/B）。

---

## 4. 触达面：世界事件到底能不能进到居民嘴上

### 4.1 路径清单（静态枚举，可 grep）

| # | 世界事件 → 居民 的可能路径 | 本批是否接通 | 依据 |
|---|---|---|---|
| 1 | C-1 提示词行（`_world_line`） | **接通但 ctrl 臂 OFF** | `agent.py:1257`；`WORLD_C1_EVENT_TYPES` 是 life 层唯一引用点（`agent.py:85/1267`） |
| 2 | 记忆写入（`_observe` → observation） | **未接通** | `_SALIENT_EVENTS`（`agent.py:111-115`）**不含** `WORLD_DIRECTIVE`/`WORLD_GROUP_EVENT` |
| 3 | 派生世界参数（`world_params`） | 已生效（§3.5），但**唯一消费者仍在 C1 内部** | `market_scarcity_bp` 只被 `agent.py:1311` 读 |
| 4 | 感知（`visible_events`） | 事件可见（`perception_scope` 两类均 global），但**除 C1 外无对话消费者** | `contracts/visibility.py`、`engine/perceive.py` |

```bash
cd <repo>/.worktrees/worldline-c1-n16r84
grep -rn "WORLD_GROUP_EVENT\|WORLD_DIRECTIVE" --include=*.py code/life/ | grep -v tests
grep -n "_SALIENT_EVENTS" -A 5 code/life/agent.py
```

真实输出（关键行）：

```
code/life/agent.py:85:WORLD_C1_EVENT_TYPES = ("WORLD_GROUP_EVENT", "WORLD_DIRECTIVE")
code/life/agent.py:1267:          ② 镇上的事：`wv.visible_events` 里 `WORLD_GROUP_EVENT/WORLD_DIRECTIVE`
---
111:_SALIENT_EVENTS = {
112-    "ACTIVITY_STARTED", "ACTIVITY_COMPLETED", "PLACE_ARRIVED",
113-    "MSG_PUBLIC", "MSG_DM", "MSG_GROUP", "RELATION_ENCOUNTER", "RELATION_CHANGE",
114-    "SEED_EVENT", "AGENT_DIED", "TAG_EMITTED", "NARRATIVE", "NORM_VIOLATED",
115-}
```

### 4.2 触达面判读（**这是本轮最容易被误读的一处，必须写清**）

- 【事实】ctrl 臂（C1=OFF）里，世界事件对对话的**触达面 = 0**。
- 【判断】但这**属设计**，不是断链：世界事件**唯一的对话侧消费者就是被关掉的这个开关本身**；记忆侧从未接入（不在 `_SALIENT_EVENTS`）。
- 【读数】佐证：全批 `tension` 字符串只出现在 **2 行**（§3.3 的两条世界事件本身），其余 194055 条事件（`OBSERVATION`/`MEMORY_WRITE`/`MSG_*`）**无一条**引用它：

```bash
grep -c "tension" v2/evidence/run_worldline_c1_ctrl_n16r84_seed42/run.jsonl   # → 2
```

### 4.3 ⚠️ `affected_scope_count = 0` **不能**当触达面证据（纠正一条诱人的误读）

- 【事实】该字段是 **Python 字面量**：`code/engine/hooks/world_director.py:48` 直接写 `"affected_scope_count": 0`；全树唯一写入点、无任何解析/计算代码：
  ```bash
  grep -rn "affected_scope_count" --include=*.py code/ | head
  # → code/engine/hooks/world_director.py:48:  ... "affected_scope_count": 0,
  ```
- 【事实】`reports/R7-world-event-wiring.md` 的 L3 层已把它登记为「**恒为字面量 0，字段从未被计算**」，并明确写「**不能**据此判定事件是否真落地」。
- 【判断】所以「`scope=global` 而 `count=0`」**不是矛盾读数**，是**该字段没实现**。若拿它当"触达侧断链"的证据，等于引用一条已被判为不可用的字段。本报告**不据此下任何结论**；若需要真实触达面，只能按 §4.1/§4.2 的路径枚举来判。

---

## 5. 两臂读数（同一口径对齐）

### 5.1 批身份表（数据 ↔ 代码）

| 臂 | 批次目录 | `code_sha` | 环境开关 | host.log | meta.json |
|---|---|---|---|---|---|
| ctrl | `v2/evidence/run_worldline_c1_ctrl_n16r84_seed42` | `af1dffc6`（worktree）| `LIFE_PROMPT_WORLD_C1=UNSET` | ✅（`2b059757…`） | **无**（按纪律不作判据锚点，仅作读数来源） |
| a1 | `v2/evidence/run_worldline_c1_a1_n16r84_seed42` | `af1dffc6`（worktree）| `LIFE_PROMPT_WORLD_C1=1` | ✅（`74ceace7…`） | 见 §5.7 |

两臂**同一份代码、同一 seed（42）、同一规模（n=16, rounds=84）**，唯一差异是那个环境变量。

### 5.2 真跑验真（本报告作者**本轮复跑**，非引用既有结论）

```bash
cd <repo>/code
python3 -m obs llm-cost --log ../v2/evidence/run_worldline_c1_ctrl_n16r84_seed42/run.jsonl --require-provider openai_compat; echo rc=$?
```

执行时刻 2026-10-22 16:09（本机时钟），真实输出（截断，保留关键段）：

```
{"engine_log":{"by_provider":{"openai_compat":3403},
 "by_purpose":{"dialogue":{"cached":0,"calls":714,"degraded":0,"thinking":0,"tokens_in":215500,"tokens_out":27608},
               "importance":{"cached":1597,"calls":1747,...},
               "judge":{"cached":0,"calls":717,...}, ...},
 "total":{"cached":1666,"calls":3403,"degraded":0,"thinking":733,"tokens_in":368419,"tokens_out":299940,"tokens_total":668359}},
 "provider_guard":{"by_provider":{"openai_compat":3403},"expected":"openai_compat","ok":true,"problems":[]}}
rc=0
```

【事实】`provider_guard.ok=true`、`by_provider` **只含** `openai_compat`、`tokens_total>0`、`dialogue.calls=714>0` ⇒ 三条件齐备，判**真跑**。ctrl 臂 host.log 亦有全量收尾：

```
[life] n_agents=16 rounds=84 events=194057 seconds=3567.2769 log_bytes=91390751
  chain_ok=True replay_parity=True first_run_equals_replay=True conservation_ok=True
```

### 5.3 结构读数（ctrl 臂，全量 84 回合）

| 读数 | 值 | 口径 |
|---|---|---|
| 事件数 | 194,057 | 日志行数 |
| 对话消息 | **686**（DM 497 / PUBLIC 63 / GROUP 126） | `MSG_DM/MSG_PUBLIC/MSG_GROUP` |
| 线程数 | **206** | 按 `payload.thread_id` 去重 |
| 多轮线程（`turn_index` 去重 ≥2） | **104 / 206 = 50.49%** | per-thread |
| ≥3 轮线程 | **89 / 206 = 43.20%** | per-thread |
| 线程轮数分布 | `{1:102, 2:15, 3:6, 4:14, 5:1, 6:68}` | per-thread |
| `TURN_SEAL` | 84 | 回合完整 |

### 5.4 窗口分母（**效果不可判的直接原因**）

| 口径（写死，两臂共用） | 定义 | ctrl 臂 |
|---|---|---|
| 窗口 | `round ∈ [30, 35]`（= 世界指令 `[effective_from_round, expires_round)`） | — |
| 窗口对话消息 | `MSG_DM/MSG_PUBLIC/MSG_GROUP` 且 `round ∈ 窗口` | **48** |
| 窗口对话线程 | 窗口内消息的 `thread_id` 去重 | **16** |
| 窗口 dialogue 调用 | `LLM_CALL.purpose=dialogue` 且 `round ∈ 窗口` | **48** |
| 窗口 dialogue `tokens_in` 均值 | 同上 | **303.35**（全批 301.82） |

### 5.5 【核心硬证据】提示词注入的 token 侧差分（DiD，不依赖任何词表）

设计：若 C-1 真的把那一行注入了提示词，则 `dialogue.tokens_in` 应在**所有回合**略升（"你眼下在X"），并在**窗口回合**再多一小截（"镇上气氛有点紧""集市上东西有点紧俏"）。用 **DiD**（窗内−窗外，再两臂相减）剥离"内容不同导致的长度差"。

| 臂 | 窗外 dialogue `tokens_in` 均值（n） | 窗内均值（n） | 窗内−窗外 |
|---|---|---|---|
| ctrl | 301.71（666） | 303.35（48） | **+1.64** |
| a1 | 313.56（437，**收批前快照**） | 334.56（48） | **+21.00** |
| **DiD** | a1 窗外比 ctrl 窗外高 **+11.85**（= 全程都在的「你眼下在X」一行） | **+19.36**（= 窗内额外那两小截） | — |

【事实】两条独立的注入量都落在预期量级（一行"眼下在X"≈12 tokens、窗口内再加"气氛有点紧/东西有点紧俏"≈19 tokens）。**这条比正文字面命中更硬**：它不依赖任何词表，直接读 LLM 调用的 `tokens_in`。

【口径限制（必须写死；2026-10-22 注：a1 已收批，本节数字为 partial 快照，全程重算结果与差异 >20% 的两数并列见 §5.9）】a1 当时是 **partial 批**（`a1(partial, round≤55)`）：窗内 n=48 已完整，但**窗外分母 437 是快照**（ctrl 为 666，合计 714 —— 485 vs 714 不是臂间差异，是 a1 只跑到 round 55/84）。定稿时 DiD 用**全程数据重算**；若全程值与本次 partial 值差异 **>20%**，报告同时给出两个数并说明。
另：DiD 的"窗外"= 窗口前后的全部轮次。**收批后必须确认 a1 里 `WORLD_*` 事件仍只有 round 30 一次**；若窗口后再落一次，"窗内/窗外"的二分就不成立，必须改成按事件窗口逐段切分。

### 5.6 【佐证·弱代理】窗口正文层字面命中（主读数：线程级）

口径（写死，两臂共用）：窗口 `round ∈ [30,35]`；**命中** = 消息正文命中世界类词表 `镇上/镇里/集市/市集/眼下/节庆/气氛/紧俏/供货/灾/闹了场病/通告/修公共设施/外乡人/大活动`（**弱代理指标**，ctrl 也可能自然说"镇上"，故它不是开关证据，开关证据见 §2.2/§5.5）。

| 读数 | ctrl（OFF） | a1（ON，窗口完整、批未收） | 统计 |
|---|---|---|---|
| 窗口消息 | 48（全 `MSG_DM`） | 48（全 `MSG_DM`） | 分母同 |
| 窗口线程 | 16 | 16 | 分母同 |
| 窗口 dialogue 调用（暴露机会） | 48 | 48 | 比值 **1.000** |
| 命中消息 | **0/48 = 0.00%** | **11/48 = 22.92%** | Fisher 双侧 **p = 0.00051243**（观测不独立，CI 偏窄，**仅作附注**）|
| **命中线程（主读数）** | **0/16 = 0.00%** | **9/16 = 56.25%** | Fisher 双侧 **p = 0.000815721** |
| 命中线程 Wilson 95% | [0.0, 19.36%] | [33.18%, 76.90%] | — |

复算命令（本报告作者自写，独立于上游脚本）：

```bash
cd <repo> && python3 - <<'PY'
import json, collections
from math import comb
WORDS=("镇上","镇里","集市","市集","眼下","节庆","气氛","紧俏","供货","灾","闹了场病","通告","修公共设施","外乡人","大活动")
def probe(p):
    MSG=("MSG_DM","MSG_PUBLIC","MSG_GROUP"); thr=collections.defaultdict(int); hits=collections.defaultdict(int); dlg=n=0
    for line in open(p,encoding="utf-8"):
        e=json.loads(line); r=e.get("round"); t=e.get("type")
        if not (30<=r<=35): continue
        if t=="LLM_CALL" and (e.get("payload") or {}).get("purpose")=="dialogue": dlg+=1
        if t in MSG:
            n+=1; pl=e.get("payload") or {}; tid=pl.get("thread_id"); thr[tid]+=1
            if any(w in (pl.get("body") or "") for w in WORDS): hits[tid]+=1
    return n, len(thr), dlg, sum(hits.values()), len(hits)
def fisher(a,b,c,d):
    N=a+b+c+d; r1=a+b; r2=c+d; c1=a+c
    p=lambda x: comb(r1,x)*comb(r2,c1-x)/comb(N,c1)
    p0=p(a); return sum(p(x) for x in range(max(0,c1-r2),min(c1,r1)+1) if p(x)<=p0*(1+1e-9))
for name in ("ctrl","a1"):
    p="v2/evidence/run_worldline_c1_%s_n16r84_seed42/run.jsonl"%name
    print(name, "msgs/threads/dlg/hit_msgs/hit_threads =", probe(p))
print("Fisher 消息级 p =", fisher(11,37,0,48))
print("Fisher 线程级 p =", fisher(9,7,0,16))
PY
```

真实输出：

```
ctrl msgs/threads/dlg/hit_msgs/hit_threads = (48, 16, 48, 0, 0)
a1 msgs/threads/dlg/hit_msgs/hit_threads = (48, 16, 48, 11, 9)
Fisher 消息级 p = 0.000512429540938121
Fisher 线程级 p = 0.0008157211716722285
```

> **方法注（降低复核门槛）**：本机**未安装 scipy**，上面的 Fisher 精确检验是用标准库 `math.comb` 手写的双侧精确检验（枚举超几何分布、按"概率 ≤ 观测概率"求和）。⇒ 复核者**不需要装 scipy** 就能把这两个 p 值算出来；若装了 scipy，`scipy.stats.fisher_exact([[11,37],[0,48]])` 应给出同一量级（0.00051）的结果。

### 5.7 非复读核验（排除"照着注入行抄一遍"）

上游对 11 条命中逐条比对 C-1 注入行（`v2/evidence/run_worldline_c1_a1_n16r84_seed42/stats_and_replay_check_partial.txt` Part B）：**8-gram 交集全为 0/5**、最长公共串 **2–5 字符**、**逐字成句 = False** ⇒ 11 条全部判「无重叠」，高重叠占 **0/11**。

【判断】正文明说了"世界状态"这件事，但没有照抄注入行的措辞 —— 这正是 C-1 的设计目标（提示词里那句"用自己的话顺口带一句，不要照抄这句的措辞"）。**但不能据此宣称"更自然"**：本报告没有 judge 侧证据。

### 5.8 守卫读数（L-7 同 cut 对照）

| 守卫 | ctrl | a1 | Δ | 守卫线 | 结论 |
|---|---|---|---|---|---|
| L-7（8-gram dup，`round<40` 同 cut，MSG 各 332） | **21.99%**（73/332） | **22.59%**（75/332） | **+0.60pp** | 27.99% | **未击穿** |
| L-7（`round<36` 对照口径，MSG 各 294） | 18.71%（55/294） | 20.41%（60/294） | +1.70pp | — | 附注 |
| L-13（内部 token 泄漏，**全批两臂**） | 6/686 = 0.87% | **9/686 = 1.312%** | +3 条 / +0.437pp | ≤1.42% 且 ≤7 条 | **比率侧未超；条数侧 9 > 7 ⇒ 若「≤7 条」为硬守卫则击穿**（守卫行出处见下注） |

> 来源：`run_worldline_c1_a1_n16r84_seed42/stats_and_replay_check_partial.txt` Part C；本报告未独立重算 L-7（该指标需仓库 `tools/d5` 的 8-gram 实现，见 §9 复现命令）。

【判断】**（2026-10-22 R19 收口修订：原判断只基于 L-7 与 partial 期 L-13，收批后 L-13 全批读数推翻了「完全没踩守卫」的表述）** 与本轮其它臂（R13 L-13 击穿、R14 L-7 +9.72pp、R15 +11.18pp）相比，本臂在 **L-7 侧未击穿**（+0.60pp，§5.8 首行）；**L-13 侧**全批为 9/686（ctrl 6/686），比率 1.312% 低于 1.42% 线、但条数 9 高于同表并列的「≤7 条」⇒ **结论改写为：L-7 未击穿；L-13 比率侧未超、条数侧可能击穿**。⚠️ 该守卫行「≤1.42% 且 ≤7 条」在 `v2/evidence/D8-preregistration-world-director.md` 中**查无原文出处**（全文件无 L-13 行），只有本报告 §5.8 自述 ⇒ 是否构成硬守卫需 Leader 裁决；本轮**不据此改判 R17 主结论**（C-1 已因剂量不足判「不可判」，L-13 条数侧即便击穿也只加一条「不可判」理由），仅如实登记。

> 口径声明（L-13 全批读数来源）：`python3 tools/d5/dialogue_metrics.py --log <run.jsonl> --out-json <out>` 的 `L-13_token_leak`（分子 = `ctx.topic` 原始 token 直接出现在 body 的消息数，分母 = 全部 MSG），两臂同脚本同口径；但两臂均**无 `meta.json`** ⇒ d5 准入 `REJECTED`、`evidence_level=probe`，该读数**只能是过程记录，不入结论**（同 §5.9）。

### 5.9 a1 臂全批终值（**2026-10-22 R19 收口回填；因两臂均无 `meta.json`，全部读数按「过程记录、不入结论」**）

> **修订说明（证据日期 2026-10-22）**：本节原为「收批后填」空表，且正文别处仍写「a1 未收批」——该表述**已过期**：`run_worldline_c1_a1_n16r84_seed42/host.log` 早有收尾行。本轮（R19 收口，零成本、未起任何跑批）用盘上现成日志补齐，并给出逐条复算命令。
> **准入结论（先读这条）**：两臂目录**均无 `meta.json`**（`ls ... | grep -c meta.json` → 0）⇒ `tools/d5/dialogue_metrics.py` 判 `verdict=REJECTED`、`evidence_level=probe`（`B-7_files: 无 meta.json → 非证据级`、`B-9_event_count: meta.events=None`）。故**本节所有数字仅供过程记录与后续轮次对照，不得作为任何效果结论的锚点**；R17 主结论（接线成立 / 世界近乎没发生事 / 效果不可判）**不变**。

| 项 | 填充值（2026-10-22 复算） | 复算命令 |
|---|---|---|
| `host.log` 收尾 | `n_agents=16 rounds=84 events=194047 seconds=3492.0673 log_bytes=91397526`；`chain_ok=True replay_parity=True first_run_equals_replay=True conservation_ok=True`；`final_state_hash=sha256:96de5c628103420b40904b372a9471c285603e816c1930787e877d5bd0129faf` | `tail -6 v2/evidence/run_worldline_c1_a1_n16r84_seed42/host.log` |
| `obs llm-cost` 真跑门禁 | **rc=0**；`by_provider={"openai_compat":3403}`；`degraded=0`；`calls=3403`（`cached=1666` = 批内去重，非 mock）；`thinking=733`；`tokens_in=387046 / tokens_out=317196 / total=704242`；分 purpose：`dialogue 714/233188/30408`、`judge 717`、`importance 1747`(cached 1597)、`reflect 112`、`describe 16`、`negotiation 81`、`plan 16` | `cd code && python3 -m obs llm-cost --log ../v2/evidence/run_worldline_c1_a1_n16r84_seed42/run.jsonl --require-provider openai_compat; echo rc=$?` |
| 全批消息 / 线程 / 多轮线程 | **686**(DM 497 / PUBLIC 63 / GROUP 126) / **206**（`thread_schema=explicit`）/ **≥3 轮 90/206 = 43.69%**、单消息线程 102/206 = 49.51%、轮数（`turn_index` 去重）`p50=2 p90=6 max=6` | `python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_worldline_c1_a1_n16r84_seed42/run.jsonl --out-json /tmp/d5_a1.json` |
| 窗口内 dialogue `tokens_in` 的"窗外"分母（**全批版**） | 窗外 **n=666，均值 326.02**；窗内 n=48，均值 334.56；**窗内−窗外 = +8.54**（partial 快照为 437 / 313.56 / +21.00） | 见本节末「tokens_in 分窗脚本」 |
| L-13 全批 | **9/686 = 1.312%**（`by_topic: whisper 4 / contest 3 / combat_training 1 / mentorship 1`）；ctrl 同口径 6/686 = 0.87% | 同「全批消息/线程」命令的 `L-13_token_leak` 字段 |
| 附注：世界事件落点（全批确认） | 全批仍**只有 round 30 的 2 条**（`WORLD_DIRECTIVE` + `WORLD_GROUP_EVENT`，`kind=tension`，`[30,36)`）⇒ §5.5 的「窗内/窗外」二分**在全程数据上依然成立** | `python3 v2/evidence/run_worldline_c1_a1_n16r84_seed42/window_probe.py`（在 `v2/evidence/` 下执行） |
| 附注：全批 L-7（**未分层，不与 §5.8 同 cut 结果可比**） | a1 **34.69%**（238/686）vs ctrl **30.90%**（212/686） | 同上 d5 命令的 `L_wording.L-7_dup_ngram8_rate` |

**两臂同口径对读（均无 meta，仅过程记录）**

| 读数 | ctrl（OFF） | a1（ON） | Δ |
|---|---|---|---|
| 消息 / 线程 | 686 / 206 | 686 / 206 | 0 / 0 |
| ≥3 轮线程（d5 口径） | 90/206 = 43.69% | 90/206 = 43.69% | 0 |
| L-13 条数 | 6/686 = 0.87% | 9/686 = 1.312% | **+3 条** |
| `dialogue.tokens_in` 总量 | 215,500 | 233,188 | **+17,688（+8.21%）** |
| 全量 `tokens_in` | 368,419 | 387,046 | +18,627（+5.06%） |
| 窗外 `tokens_in` 均值 | 301.71（n=666） | 326.02（n=666） | **+24.31**（= 全程注入行 + 内容长度差，未分离） |
| 窗内−窗外 | +1.64 | +8.54 | **+6.90**（= 窗口额外注入的 DiD 全程版） |

**【必须并列的两个数】§5.5 的 partial 版 DiD（a1 窗外 313.56/437、窗内−窗外 +21.00）与本次全程重算（326.02/666、+8.54）差异 >20%**（§5.5 预先写死的规则要求此时两数并列并说明）：a1 的 partial 期只跑到 round 55，后段 prompt 更长却未计入窗外均值，**低估了窗外基线**；全程重算后「窗内额外增量」从 +19.36 降到 **+6.90**。⇒ token 侧注入的**方向**仍为正（与「窗口内多注两小截」一致），但**量级不稳定**，只能作方向性旁证，不得当剂量证据；这也再次说明本轮「不可判」的判定不必修改。

<details>
<summary>tokens_in 分窗脚本（照抄可复算；口径 = `LLM_CALL.purpose=dialogue`，窗口 `round∈[30,35]`）</summary>

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 - <<'PY'
import json, statistics
def scan(path):
    win, out = [], []
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if not line: continue
        e = json.loads(line)
        if e.get('type') != 'LLM_CALL': continue
        p = e.get('payload') or {}
        if p.get('purpose') != 'dialogue': continue
        tin = p.get('tokens_in')
        if tin is None: continue
        r = e.get('round')
        (win if (r is not None and 30 <= r <= 35) else out).append(tin)
    return win, out
for tag, path in (("ctrl","v2/evidence/run_worldline_c1_ctrl_n16r84_seed42/run.jsonl"),
                  ("a1","v2/evidence/run_worldline_c1_a1_n16r84_seed42/run.jsonl")):
    w, o = scan(path)
    print(tag, "window n=%d mean=%.2f" % (len(w), statistics.mean(w)),
          "outside n=%d mean=%.2f" % (len(o), statistics.mean(o)),
          "diff=%.2f" % (statistics.mean(w) - statistics.mean(o)))
PY
# 期望输出（2026-10-22 实跑）：
# ctrl window n=48 mean=303.35 outside n=666 mean=301.71 diff=1.64
# a1   window n=48 mean=334.56 outside n=666 mean=326.02 diff=8.54
# ctrl 一侧与 §5.5 原表逐位一致 ⇒ 脚本口径与原报告同源（可作为自校验）
```
</details>

---

## 6. 截图（真图三件套）

**【本轮无正式图（2026-10-22 修订确认）】**：a1 侧正式图从未产出，ctrl 侧已有 `v2/evidence/cycle03_shots/` 四张（属 ctrl 批）；按报告族纪律，本节写明「无图 + 渲染命令」，**不以任何其它批次图或示意图顶替**。若要补 a1 正式图，必须从**本轮选定批次**重新渲染（预检期的临时图已删，不得顶替），且渲染时记录 HEAD 与图 sha256。跑批期间不向 `code/frontend/sample/` 写任何文件；收批后按下列命令出图，并回填路径 / 图 sha256 / 渲染命令 / 来源日志 sha256。

```bash
# ① 生成页面数据（从真源 run.jsonl 派生，不写世界）
cd <repo>/code
python3 frontend/tools/gen_threads.py \
  --log  ../v2/evidence/run_worldline_c1_<臂>_n16r84_seed42/run.jsonl \
  --out  frontend/sample/dialogue_<批次>/threads.json \
  --label <批次>

# ② 起静态服务（必须 http://；setsid 后台、用完即关）
setsid python3 frontend/tools/serve.py --host 127.0.0.1 --port 8848 \
  > /tmp/serve_r17.log 2>&1 < /dev/null &

# ③ 出四视图真图
bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 \
  sample/dialogue_<批次>/threads.json <批次> <sha8> ../v2/evidence/r17_shots

# ④ 取证
sha256sum ../v2/evidence/r17_shots/*.png
```

---

## 7. 结论档位（四档，逐条给依据与分母）

| # | 结论 | 档位 | 依据 / 分母 |
|---|---|---|---|
| 1 | C-1 开关是**单变量**（OFF 与 ON 只差提示词一行，去掉该行逐字节相同） | **成立（机制侧）** | `prompt_diff_proof.txt` 六项断言；`VERDICT=PASS` |
| 2 | 世界导演**确实会下发**世界事件，且落账可追溯（directive + group event + `rng_branch`） | **成立（存在性）** | round 30 两条事件；`roll_bp=8 < prob_bp=40` |
| 3 | 世界层派生参数**已生效**（30–35 有效、29/36 为空） | **成立（存在性）** | §3.5 复算 |
| 4 | 派生参数**剂量被双重计数**（1000→2000） | **成立（缺陷，已登记未修）** | §3.5 隔离实验 |
| 5 | 世界事件→居民**只有一条路径**（C1 提示词行）；记忆/感知侧未接入 | **成立（静态事实）** | §4.1/§4.2 |
| 6 | 本批世界事件**供给极低**：1 次/84 回合，覆盖 6/84 = 7.14% | **成立（读数）** | §3.4 |
| 7 | C-1 **让对话更生活气息** | **不可判** | 剂量不足 + 窗口分母 48 条（<68）；**a1 已收批（2026-10-22 回填 §5.9），但两臂均无 `meta.json` ⇒ 对照读数只到 `probe`，仍不足以判效果** |
| 8 | C-1 **无效** | **不可判（不得写）** | 同上；「不可判」≠「无效」 |

> 唯一允许的对外表述：**「接线成立、世界近乎没有发生什么事、效果不可判；并登记一处剂量口径缺陷。」**

---

## 8. 风险与局限

1. **剂量过低是第一限制**：1.15%/回合 ⇒ 84 回合期望 0.966 次。即使效果真实存在，本批也几乎不可能观测到（统计功效≈0）。任何基于本批的"没变化"都不能解释为"机制无效"。
2. **窗口分母 48 条 < 68**：低于报告族常用的判读下限，按纪律**只报事件数/条数，不报比率**。
3. **双重计数使"强度"口径不确定**（§3.5）：本轮 scarcity 实际 2000 vs 配置 1000 ⇒ 即使有差异也无法归因到"世界情境"本身。
4. **a1 臂已收批，但两臂均无 `meta.json`**（2026-10-22 修订）：§5.9 已回填 a1 全批读数与 `obs llm-cost`，DiD 已用全程数据重算（窗外 +24.31 / 窗内额外 +6.90）；但因 `meta.json` 缺失，d5 准入 `REJECTED`（`probe`），这些对照**只能作过程记录、不入结论**。
5. **`affected_scope_count` 不可用**（§4.3）：任何"影响面"读数都缺一个可信来源；若下游有分析引用它，需要一并作废。
6. **无 `meta.json`（ctrl 臂）**：按团队纪律"缺 meta 一律判批次不可用"，本报告**只用它做读数来源，不用它做判据锚点**；这一条请 Leader 裁定是否接受（同理适用于 `run_g1_b0` / `run_l7struct_on` / `run_a1wording`）。
7. **单变量证明基于合成夹具**：证明的是机制形状，不是本批剂量；两者不可混引。
8. **a1 臂与 `af1dffc` 强绑定**：后续任何修（含双重计数修复）都会产生不可对照的新 sha。

---

## 9. 复现命令清单（全部只读，除截图外不起进程）

```bash
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
WT=$REPO/.worktrees/worldline-c1-n16r84
CTRL=$REPO/v2/evidence/run_worldline_c1_ctrl_n16r84_seed42

# ① 真跑门禁（本报告作者本轮复跑）
cd $REPO/code && python3 -m obs llm-cost --log $CTRL/run.jsonl --require-provider openai_compat; echo rc=$?

# ② 世界事件登记 + 计数 + 覆盖
grep -c 'D-30-wd.tension\|GE-30-wd.tension' $CTRL/run.jsonl                  # → 2
grep -c 'tension' $CTRL/run.jsonl                                            # → 2（全批仅这两行）

# ③ 消息/线程/窗口分母（一次性脚本，见 §5.3/§5.4）
python3 - $CTRL/run.jsonl <<'PY'
import json, collections, sys
p=sys.argv[1]
types=collections.Counter(); msgs=[]
for line in open(p,encoding="utf-8"):
    e=json.loads(line); types[e.get("type")]+=1
    if e.get("type") in ("MSG_DM","MSG_PUBLIC","MSG_GROUP"):
        pl=e.get("payload") or {}; msgs.append((e.get("round"), pl.get("thread_id"), pl.get("turn_index")))
thr=collections.defaultdict(set)
for r,t,turn in msgs:
    if t: thr[t].add(turn)
mr=collections.Counter(r for r,_,_ in msgs)
print("events",sum(types.values()),"msgs",len(msgs),"threads",len(thr))
print("multi_turn",sum(1 for v in thr.values() if len(v)>=2),"ge3",sum(1 for v in thr.values() if len(v)>=3))
print("window 30-35 msgs",sum(mr.get(r,0) for r in range(30,36)))
print("window threads",len({t for r,t,_ in msgs if t and 30<=r<=35}))
PY

# ④ 剂量算式（配置解析后 prob_bp 之和）
cd $WT/code && PYTHONPATH=. python3 -c "
import json; from engine.world_director import resolve_dose
c=json.load(open('config/world_director.json'))
s=sum(resolve_dose(c,m)['prob_bp'] for m in c['mechanisms'] if c['mechanisms'][m]['enabled'] and resolve_dose(c,m)['prob_bp']>0)
print('enabled mechs sum prob_bp',s,'per-round',s/10000,'expected over 84',84*s/10000)
"

# ⑤ 双重计数（§3.5 完整命令见正文）

# ⑥ 静态触达面
grep -rn "WORLD_GROUP_EVENT\|WORLD_DIRECTIVE" --include=*.py $WT/code/life/ | grep -v tests
grep -rn "affected_scope_count" --include=*.py $WT/code/ | head

# ⑦ 上游三维基线（引用，不重复）
python3 /root/.jiuwenswarm/.agent_teams/jiuwen_team_cron___1a1629fc475_615c029c3b4f/team-workspace/recon/tools/f15_recompute.py \
  --log $CTRL/run.jsonl --out /tmp/r17_f15_ctrl.json
```

---

## 10. 绑定 sha 与证据台账

### 10.1 代码身份

| 项 | 值 |
|---|---|
| 跑批代码 | worktree `.worktrees/worldline-c1-n16r84` @ `af1dffc61040adc97c828b4927ac3935dbef2d1b` |
| `code/life/agent.py` | `fcfcfaa7b66eeb112744642cf6940eb68a840fae4e029642cce68c47a7a4a92b` |
| `code/engine/world_params.py` | `a173ad33bcb871a65c01eea855d31ac81df08721463b220545cbd66f9ad3cb83` |
| `code/engine/hooks/world_director.py` | `e0a277953917ac152b4aacd5d582e7317538c4fabb96ccbae69d0e61b93e3464` |
| `code/config/world_director.json` | `5f9b7c16b8b94043a8f18bc444514e7b8ca4a9588fea96e593306097aa020038` |

### 10.2 数据与证据

| 文件 | sha256 | 说明 |
|---|---|---|
| `run_worldline_c1_ctrl_.../run.jsonl` | `4c840b5b8f8fe4bc77e118e4f5649ce696ce25eef19f5abc278472fd4ef764a5` | 91,390,751 B（**不入库**，按仓库惯例） |
| `run_worldline_c1_ctrl_.../host.log` | `2b059757a0a4bfa23089bc80085ebbf48f159612a82913846f9416569085ea02` | 收批自证 |
| `run_worldline_c1_a1_.../prompt_diff_proof.txt` | `bd1eb75ca4e4bf5a9a6c3cf7283079a810a29c1b088cbf9d0bb5b69ccb075610` | 单变量证明 |
| `run_worldline_c1_a1_.../host.log` | `74ceace7c495b3034b4c16bc5460d26337ce12d6d3fe1027e8d50d58d9e1bb88` | 起跑自证（收批后更新） |
| `run_worldline_c1_a1_.../precheck.md` | `3491f8489eb67b7979435353b2f24a3e298c4bd20e7b644442b5e19f033eee40` | 前置核查 |
| `run_worldline_c1_a1_.../launch_evidence.txt` | `d6bba7c42249940de0126029a95d7f78dbe37a12fb6585639bbd20b765ad5803` | 起跑凭证 |

### 10.3 本报告自身

| 项 | 值 |
|---|---|
| 报告文件 | `reports/R17-worldline-c1.md` |
| 索引 | `reports/README.md`（R17 行） |
| 周期报告 | `reports/CYCLE-02-20261022.md` |
| 绑定 commit | 见提交后在 `reports/README.md` R17 行与 §10.4 回填 |

### 10.4 填写记录

- 【已完成 2026-10-22】a1 臂读数（§5.7/§5.8/§5.9）已按收批后日志回填，并注明「两臂无 `meta.json` ⇒ 过程记录、不入结论」；L-13 全批 9/686 已登记（条数侧可能击穿，待 Leader 裁决守卫线出处）。
- 【仍未完成】正式截图（§6）：本臂 ctrl 侧已有 `cycle03_shots/` 四张，a1 侧正式图未出；按纪律写「无图 + 渲染命令」，不得以其它批次图顶替。
- 【仍未完成】绑定 commit sha：待本轮（R19）提交后回填。
