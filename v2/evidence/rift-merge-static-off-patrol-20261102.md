# 合并树「默认全关」静态巡检：逐文件核 off 路径是否原样（只读，未跑批）

- 时间：2026-11-02 04:2x
- 对象：`origin/master` → 合并树 `d7bb9737cc9b3784ff3a4ca41eac880ff8479518`（**临时树·非当前版**，`merge-tree` 输出，无 ref 指向）
- 方法：`git diff origin/master <merge> -- code/` 逐 hunk 读，只用 `git show` / `git grep`，**未执行任何代码**
- 目的：把 `dialogue-core-dev` 待写的 `--static-only` 模式先手工做一遍，缩掉盲跑 A/B 的候选

## 1. 结论先给

**在合并带来的 10 个实现文件里，我逐处核了 off 路径，未找到"未设环境变量时行为会变"的静态候选。**
⇒ 我前一件写的「`A ≡ B` 很可能不成立」**需要降级为「静态上未见分叉源，仍须实测确认」**。

**这是对 Leader 自己判断的更正，不是对别人的更正。**

> ### ⚠⚠ 本表的适用**时点**（Leader 2026-11-02 04:2x 自纠，`repro-verifier` 04:18 实测触发）
> **`merge-tree` 的输出 sha 不是稳定标识符** —— 它 = f(`origin/master`, `efcf441`)，**master 一动它就变**。
> 实测：`master@340b965` 时得到临时树 `d7bb9737`（**非当前版**）；`master@9d2888c` 时同一命令得到临时树 `5bfc0662`（**非当前版**）。**两者内容等价，只是基线不同。**
> ⇒ **本件所有读数绑定「`origin/master` = `340b9659` 那一刻」**。引用时**必须同时给 master 的 sha**，否则读者复算会得到另一个数并误判"件是编的"。
> ⇒ 通用规则：**引用临时树/合并树，必须写成 `merge-tree(master@X, branch@Y) = Z` 三元组**，只写 Z 不够。

> ### ⚠ 本表的适用范围（`repro-verifier` 2026-11-02 04:1x 提，Leader 采纳）
> **本表核的是「合并树 / `efcf441`」，不是 `master`。** `master` 上 `observer` / `rift_ids` 在 `code/life/dialogue_repair.py` **零命中** —— 因为这些代码**还没进 master**。
> ⇒ 读本表时不要问"master 上为什么找不到"，**本表回答的是"合并后会怎样"，不是"master 现在怎样"**。

## 2. 逐文件核查（每一行都给了判据）

| # | 文件 | 合并带来的改动 | off 时是否原样 | 判据 |
|---|---|---|---|---|
| 1 | `code/life/dialogue_repair.py` | +100 | **是** | `observer` 形参默认 `None`，所有 `observer(...)` 调用都在 `if observer is not None:` 内；`rift_ids` 在 `if _cfg().get("rift_events"):` 内；`record_only` / `repair_ask is False` 各自守卫 |
| 2 | `code/life/agent.py` | +233 | **是** | `obs = self._on_rift_event if dr.get("rift_events") else None`；`dr` 缺该键 ⇒ `None` ⇒ 不传；`_on_rift_event` 只经 `obs` 触达 |
| 3 | `code/engine/kernel.py` | +17 | **是** | 只新增只读方法 `pending_records()`，**off 时无调用方**（调用方是 `_pending_view()`，见 #6） |
| 4 | `code/engine/perceive.py` | +46 | **是** | `intra_round_mode()` 未设 env ⇒ `"off"`；`with_pending()` 在 `off` 时**返回入参同一对象**（`repro-verifier` 11-01 已核，`with_pending_calls=0`） |
| 5 | `code/engine/events.py` | +2 | **是** | 仅向 `EVENT_TYPES` 集合**增加两个成员**；该集合只做成员校验，**不参与排序/序列化** |
| 6 | `code/engine/replay.py` | +2 | **是** | 仅向 `_NOOP_TYPES` 列表追加两项，`_APPLIERS.setdefault(...)` 为两新类型注册 noop；**既有类型行为不变** |
| 7 | `code/life/ports.py` | +5 | **是** | 只把 `INTENT_RIFT` 加入 `ALL_INTENT_CLASSES`；唯一用途是 `integration.py:423` 的 `set(...)` **成员校验**，不排序、不枚举落盘 |
| 8 | `code/orchestration/integration.py` | +72 | **是** | `_pending_view()` 在 `mode == "off"` 时 `return None`；`visibility_query(..., extra=None)` 与原调用等价；`out["dialogue_pick"]` 只在 payload 已带该键时追加（须 `pick_mark` 开） |
| 9 | `code/orchestration/visibility_index.py` | +13 | **是** | `extra` 新增形参默认 `None`，`None`/空 ⇒ 与引入前一致（docstring 自述并已核调用点） |
| 10 | `code/config/dialogue_repair.json` | 6 行 | **是** | **只追加 4 个新键**（`repair_ask:null` / `record_only:false` / `pick_mark:false` / `rift_events:false`），**既有键一个未动**（`repro-verifier` 已核同一事实） |

## 3. 三个"看着像风险、实则不是"的点（记下来防止后人重复怀疑）

1. **`dialogue_repair.json` 追加键** —— 担心的"默认值解析被改"不成立：既有键未动，新键由 `_bool` / `_tri` 读，未设时分别回落到 `False` / `None`。
2. **`EVENT_TYPES` 加成员** —— 担心的"事件类型集合被用于排序"不成立：它是 `set` 字面量，用法只有 `in` 校验。
3. **`ALL_INTENT_CLASSES` 加成员** —— 担心的"意图枚举被落盘/计数"不成立：全仓唯一消费点 `integration.py:423` 是 `set(...)` 成员校验。

## 3.5 若实测分叉：先按**事件类型**定模块，再用上表排除（`repro-verifier` 提，Leader 采纳）

**排除法（上表）是"逐项排掉已排除项"，定位法是"直接指向模块"，两步并行更快：**

| `first_divergence` 的事件类型 | 指向模块 |
|---|---|
| `OBSERVATION` / `perceive` 相关 | **D9z 感知侧**（`code/engine/perceive.py`） |
| `MSG_*` / `LLM_CALL(purpose=dialogue)` | **对话侧**（`code/life/agent.py`） |
| `MEMORY_WRITE` / `MEMORY_FORGET` / `MEMORY_CONSOLIDATE` | **记忆侧**（`code/orchestration/integration.py` 的 `_do_memory`） |
| **`RIFT_*` 出现在 off 臂** | **rift 侧 off 未彻底 —— 最严重，直接定责** |
| `TURN_SEAL` / `state_hash` 相关 | **引擎侧**（`code/engine/kernel.py` 的 commit 顺序） |

⇒ **先看类型锁定模块，再在该模块内用 §2 那张表逐项排除。**

## 4. 这条静态结论**不能替代**实测（边界写死）

- **静态只证"未设 env 时走的还是那些行"，不证"那些行在合并后算出的值相同"**；
- 合并把 `agent.py` 改了 233 行，即使 off 分支逻辑相同，**函数内局部顺序/变量绑定若有细微改动，仍可能改变输出**——这只有实测能看见；
- ⇒ 实测（`A vs B`）**仍必须做**；本节的作用只是：**若实测分叉，可直接排除上述 10 处常见怀疑，直奔真正的那一处**。

## 5. 复算命令

```bash
M=<合并树临时 sha：上表同一串，非当前版>
git diff origin/master $M -- code/ --stat
git diff origin/master $M -- code/engine/kernel.py code/engine/events.py code/engine/replay.py code/life/ports.py
git show $M:code/life/dialogue_repair.py | grep -n -B6 'out\["rift_ids"\]'
git grep -n "ALL_INTENT_CLASSES" $M -- code/
```

## 率的定义

**本件不新增任何率**（静态巡检，无分子分母）。

| 率名 | 分子 | 分母 | 计算式（含边界） | 纳入排除 |
|---|---|---|---|---|
| 无（只报"10 个实现文件中 10 个 off 路径原样"） | 不适用 | 不适用 | 不适用 | 不适用 |

## 外推与假定

**本件不外推**。结论限于"该合并树的静态 off 路径"，不外推到真 LLM 行为。

| 外推式 | 假定不变的量 | 值来源 |
|---|---|---|
| 无 | 不适用 | 不适用 |

## 6. 「双证」的措辞规则（`repro-verifier` 提，Leader 采纳为判定口径）

| 情形 | 允许的写法 | 禁止的写法 |
|---|---|---|
| `A ≡ B` **且** 本表覆盖了该次分叉涉及的全部文件 | **「双证通过」**（静态 + 实测） | 不得只写"实测通过"而漏掉静态（那会让人以为是跑空） |
| `A ≡ B` 但本表**未覆盖**某文件 | **「实测通过、静态未覆盖」** | **不得写"双证"** |
| `A ≠ B` | 「实测不等 + 分叉点 + 归因到文件/符号」 | 不得写"基本等价""差异很小" |

**理由**：`identical=true` 单独立着，读者无法区分"真跑空了"与"真等价"；**静态逐处核过 + 实测全等**才是双证。反过来，静态没覆盖就说双证，是把"没查"当成"查过"。

## 7. 移植分支的 **hunk 级**静态表：由 `repro-verifier` 出，Leader 定判据

**分工**：本件覆盖的是「整分支合并树 10 个文件」；最小移植分支是**另一组 hunk**，需**另出一张表**（§19 双证须同域）。
`repro-verifier` 已提出五项判据，Leader 采纳，移植分支落地后按此逐项给「行号 + 缩进」：

1. `observer` 形参默认 `None`，且**所有** `observer(...)` 调用在 `if observer is not None:` 内（**须给缩进证明**，不能只给行号）；
2. `rift_ids` 写入在 `if _cfg().get("rift_events"):` 内；
3. `obs = ... if dr.get("rift_events") else None` 传给 `ingest`，且 `ingest` 签名缺省为 `None`；
4. `pick_mark` 两处写入均带 `and` 守卫；
5. **`INTENT_RIFT` 只是"放宽合法集"** —— 须核"放宽"没有变成"默认产生"：**无开关/env 打开时不得有任何 `INTENT_RIFT` 提交**。

### 7.1 第 5 条单列为**否决闸**

> **`V2`（最小移植分支）的 off 臂若出现任何 `RIFT_*` 事件 ⇒ 不是分叉点，是实现缺陷**（与本件 §3.5 的"最严重"同级）。
> **处置：暂停移植、回实现方修，不得先跑完再说。**

**为什么单列**：`RIFT_*` 出现在 off 臂是"默认关在意图路径上没关住"的**唯一硬信号**。

#### 7.1.1 排查起点已收窄（`repro-verifier` 2026-11-02 04:4x 全仓扫，Leader 采纳）

`ALL_INTENT_CLASSES` 的**全部消费点**（master 与 `efcf441` 各 4 类）已逐点扫过：

| 位置 | 用法 | 是否遍历预分配 |
|---|---|---|
| `life/ports.py` | **定义**（tuple 字面量） | — |
| `life/tests/support/mini_kernel.py:283` | `intent.intent_class not in ALL_INTENT_CLASSES` | **否**（成员校验） |
| `orchestration/integration.py:398` / `:423` | `legal = set(ALL_INTENT_CLASSES) \| {"INTENT.SOCIAL"}` | **否**（`set()` 成员校验） |
| `tests/test_ports_econ.py:20` / `test_ports_social.py:12` | `assert c in P.ALL_INTENT_CLASSES` | **否**（测试断言） |

⇒ **全仓零遍历、零预分配、零初始化依赖**；`+1` 个成员**只影响 `in` 判定**。

#### 7.1.1a 闸的判据固定为**纯观测式**（`repro-verifier` 提，Leader 采纳）

```
VETO  ⇔  count(RIFT_OPEN) + count(RIFT_CLOSE) > 0      （在 rift_events 关的臂上）
```

**该判据不引用任何成因** —— 不提 `ALL_INTENT_CLASSES`、不提 `_do_rift`、不提 env 解析。好处：
- 成因再排除几个，**闸的字面一个字都不用改**；
- **闸判据与排查清单分离** ⇒ 不会出现"某个成因排除了，闸看起来松了"的错觉。

**这条是"把能查到的当成要判的"这一类错误的防线**（今晚已多次踩同一件事）。

**⇒ 排查起点（仅当 VETO 触发时用，不是判据的一部分）**：**先查 `_do_rift` 的调用条件**（`obs = self._on_rift_event if dr.get("rift_events") else None` 那一行，以及 `submit_intent(INTENT_RIFT, ...)` 的触发点），**不要先怀疑集合加成员**（已排除）。

#### 7.1.2 附加子项：元组顺序未变（移植时须核）

`INTENT_RIFT` 目前是**在 `ALL_INTENT_CLASSES` 元组里追加成员，未改顺序**。若最小移植时**重排了元组**，任何**按索引**取该元组的代码都会错位。
（现 master / `efcf441` 均为字面量元组、无索引消费 ⇒ 当前无事，但移植时须核。）
