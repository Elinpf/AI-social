# `reply_window_rounds` 在 `master` 上**不可达**（静态判定，只读，未跑批）

- 时间：2026-11-02 05:1x
- 对象：`origin/master = 3610815` 时代的 `code/`（读法：`git show origin/master:<path>`）
- 状态：**草稿**，未入 master（为避免与 `feat/rift-minimal` 的 `BASE` 竞态，先放团队工作空间）

## 1. 结论

**`reply_window_rounds` 取任何 ≥ 2 的值，都不产生任何行为差异。**
⇒ **D9 的 `reply_window_rounds` 2→4 臂在结构上不可能改变任何东西**；它的阴性结果**不是"机制没效果"，是"参数没接入有效区间"**。
⇒ heartbeat 反复列的"下一嫌疑点：`reply_window_rounds` 2→4 在新结构下复测"——**这个嫌疑点应当关闭，不是复测**。复测一个不可达参数，得到"仍无差异"，只会被误读为"再次证明无效"。

## 2. 证据链（四处，全部可复算）

### 2.1 消费点：`_pick_reply_target` 读它
`code/life/agent.py:1132`
```python
window = int(cfg.get("reply_window_rounds", 2))
```
用在同函数内的过滤：
```python
if int(wv.round) - int(ev.round) > window:
    continue                      # 超时，线程结束
```

### 2.2 数据来源：只看 `wv.visible_events`
同函数遍历：`for ev in reversed(list(wv.visible_events)):`
⇒ **过滤器能看到的候选，只有 `visible_events` 里的那些**；不在此列的，连进入判断的机会都没有。

### 2.3 `visible_events` 有**硬年龄上限 2**
`code/orchestration/integration.py:282`
```python
class KernelAdapter:
    VISIBLE_WINDOW_ROUNDS = 2
```
`code/orchestration/integration.py:348`
```python
recs = self.visibility_query(agent_id, r, window_rounds=self.VISIBLE_WINDOW_ROUNDS, location=loc)
```
`code/contracts/visibility.py:88` 内的年龄过滤：
```python
if window_rounds is not None and rec["round"] < upto_round - window_rounds:
    continue
```
⇒ **`visible_events` 中任何事件的年龄 ≤ 2 轮。**

### 2.4 因此 `> window` 恒为假
- `age = round - ev.round`，由 2.3 得 `age ≤ 2`；
- 判据是 `age > window`；
- `window = 4`（D9 的 2→4 臂）⇒ `age > 4` **没有候选能满足**（`age ≤ 2 < 4`）；
- `window = 2`（默认）⇒ `age > 2` 同样**恒假**。

⇒ **该参数在 2 与 4 两档上都不生效；它只在 `window < 2` 时才可能起作用，而没人试过 < 2。**

### 2.5 更强的表述（`repro-verifier` 2026-11-02 05:19 独立核后提出，Leader 采纳）

> **`reply_window_rounds` 的有效区间是 `< 2`；默认值 `2` 恰好压在失效边界上** ⇒ 这一检查在默认配置下**筛不掉任何事件，是死检查**。

**等价链（复核方补齐，是结论的根）**：
```
r = st.round ;  visibility_query(..., r, window_rounds=2) ;  WorldView(round=r)
⇒ visibility 保留 rec["round"] >= r-2  ⇒ age = r - rec.round <= 2
⇒ agent.py:1147 判 age > window ⇒ window >= 2 时恒假
```
⇒ **`window=2` 已恒假，`window=4` 更恒假。** 而 `window=1` 才会产生分辨力 —— 但那改了可见窗语义，**属新变量，须另立卡**。

## 3. `VISIBLE_WINDOW_ROUNDS` 是否可被环境变量覆盖？

**不可。** `git grep "VISIBLE_WINDOW_ROUNDS *="` 只有两处，都是**字面量 2**：
- `code/orchestration/integration.py:282`（生产）
- `code/life/tests/support/mini_kernel.py:30`（测试脚手架）

⇒ 没有 env、没有 config 键能改它。**年龄上限是硬的 2 轮。**

## 4. 与既有记录的关系（不是新发现，是**证成**）

候选池/报告里已有"`reply_window_rounds` 不可达 / 死参数"的说法，但**此前给的是经验判断**（"D9 臂没效果"）。本节给的是**结构性证明**：不是"试了没用"，是"**在 `visible_events` 的上限 2 之下，`> 4` 恒假**"。

**差别很重要**：
- 经验判断 ⇒ 换新结构会想"再试一次"；
- 结构证明 ⇒ **知道再试也不会变，除非先改 `VISIBLE_WINDOW_ROUNDS`**（那是另一个变量）。

## 4.5 关闭的是「成因」，不是「阴性结果」（`repro-verifier` 提，Leader 采纳）

> **D9 阴性仍成立**（该臂确实没测出差异）；但**其成因不是"机制无效"，而是"参数在默认配置下无分辨力"**。
> 两者对下一步的含义不同：前者会让人去改机制，后者指向"先修检查本身"。

**⇒ 入候选池时必须两句同屏，不得只写"阴性被推翻"。**

## 5. 边界（写死，防过度引申）

1. **只对 `master = 36108154` 生效**（复核方独立核过的那个 rev）。若某分支改了 `VISIBLE_WINDOW_ROUNDS` 或换了 `wv` 的来源，本结论不适用；**`feat/rift-minimal`（8 文件）不含 `integration.py` 的该行，故不受影响**；
2. **不评价 D9 臂的其它方面**（那次实验还改了别的吗？本节不查，只查这一个参数）；
3. **不主张"应当把 `VISIBLE_WINDOW_ROUNDS` 改成 4"** —— 那是新变量，要单独立卡、单变量、重跑；**本节只说"在它等于 2 时，`reply_window_rounds` 是空操作"**；
4. **本件未跑任何代码**，全部由 `git show` 静态读出。

## 6. 复算命令

```bash
git show origin/master:code/life/agent.py | sed -n '1125,1150p'
git show origin/master:code/orchestration/integration.py | sed -n '278,290p;340,352p'
git show origin/master:code/contracts/visibility.py | sed -n '88,110p'
git grep -n "VISIBLE_WINDOW_ROUNDS *=" origin/master -- code/
git grep -n "reply_window_rounds" origin/master -- code/
```

## 率的定义

**本件不新增任何率**（静态判定，无分子分母）。

| 率名 | 分子 | 分母 | 计算式（含边界） | 纳入排除 |
|---|---|---|---|---|
| 无（只报"`age > window` 恒假"这一逻辑事实） | 不适用 | 不适用 | 不适用 | 不适用 |

## 外推与假定

**本件不外推**。结论只对 `master = 36108154` 成立。

| 外推式 | 假定不变的量 | 值来源 |
|---|---|---|
| 无（只做静态推导，不估任何效果量） | `VISIBLE_WINDOW_ROUNDS = 2` 且无 env/config 可改 | `integration.py:282` 字面量；`git grep "VISIBLE_WINDOW_ROUNDS *="` 仅 2 处均为 2 |
