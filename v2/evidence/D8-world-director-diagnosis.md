# D8 · 世界导演链路诊断：剂量 → 触发 → 影响面 → 是否进对话

> 作者：repo-scout（仓库现状勘察员）｜2026-10-20 22:20 (+08:00)
> 判据文件（先写，同批提交）：`v2/evidence/D8-preregistration-world-director.md`
> 代码身份：`master @ 2090287809ae307614b3f9b2f62e7619f2142ea8`（`2090287`）
> 数据批：A0 臂 `v2/evidence/run_d2_after_n16_seed42/`，`run.jsonl` (643f13a5) 194,108 行 / `meta.json` (5fe058f3)，16 agents × 84 rounds × seed 42，真 LLM（`obs llm-cost` provider_guard.ok=true，calls=3403）
> 纪律：**只读**。本文未修改 `code/life|orchestration|config|engine` 任何一行（工作区除作者新增的 D8 文档外无新改动）。

---

## 0. 结论（五句，先给判断再给证据）

1. **剂量层：不是运气，是配置本身把宏观事件定成了"一周不到一次"。** 三个 enabled 机制在 `conservative` 曲线下的 84 回合理论期望合计 **E=0.966**，实测 1 条；观测 1 条落在 Poisson(E=0.966) 的 37% 分位上，**完全正常**——所以"84 回合只有 1 条"是剂量设计的必然，不是 RNG 冷落。
2. **触发层：干净。** 对 84 回合 × 3 机制复算 `roll`，触发集与日志**逐条全等**（`[(30,'wd.tension',8)]`），说明"RNG 先定 + 无隐藏分支"没有实现缺陷。
3. **影响面层：断点是硬编码字面量。** `WORLD_GROUP_EVENT.affected_scope_count` 在 `code/engine/hooks/world_director.py:48` **直接写死 `0`**，全仓无第二处写入、无任何解析代码 ⇒ 不是 scope 解析 bug，是**这个字段从来没被算过**。
4. **感知/记忆层：进得了视野，进不了记忆。** 世界事件（`global` 可见类）确实出现在 **每个 agent** 的 `visible_events` 里（P001/P009/P016 实测，round 30 起）；但 `code/life/agent.py:41-45` 的 `_SALIENT_EVENTS` 白名单**不含** `WORLD_DIRECTIVE/WORLD_GROUP_EVENT`，`:403` 的过滤把它们直接丢掉 ⇒ 精确引用世界事件 seq 的 `MEMORY_WRITE` **0 条**、`OBSERVATION` **0 条**。
5. **对话层：零暴露（本轮最重要的一句）。** 两个提示词装配函数（`_dialogue_prompt` `agent.py:1050-1058`、`_reply_prompt` `agent.py:1060-1069`）里**没有任何世界状态行**；对话消息 `refs` 中世界事件 seq 出现次数 **0**；而检索输入只来自 `goal + 当前活动 + 最近记忆文本`（`_retrieval_query` `agent.py:444-449`），记忆里既然没有世界事件，检索也不可能捞到 ⇒ **世界层事件对对话零暴露**。

> 一句话：**这条链不是"效果不好"，是"从第 3 环起就断了，而且第 5 环连管道都不存在"。**

---

## 1. 链路与断点总览

| 环节 | 代码位置 | 实测读数 | 判定（按预注册判据） |
|---|---|---|---|
| L1 剂量 | `engine/world_director.py:20-36`（DOSE_CURVES）、`:45-58`（resolve_dose） | E=0.966，N=1 | **剂量过低**（配置问题，非 bug） |
| L2 触发 | `engine/world_director.py:74-110`（rng_branch / plan_directives） | 复算触发集 == 日志触发集 | **接通** |
| L3 影响面 | `engine/hooks/world_director.py:45-49` | `affected_scope_count` 恒 0（字面量） | **未接通（根本不是计算出来的）** |
| L4 感知 | `contracts/visibility.py` + `config/perception_scope.json` | 世界事件进入 visible_events（≥3 个 agent 实测） | **暴露=真** |
| L4′ 沉淀 | `life/agent.py:41-45`、`:395-418` | MEMORY_WRITE/OBSERVATION 引用数 = 0 | **未接通（白名单过滤）** |
| L5 对话 | `life/agent.py:1050-1058`、`:1060-1069`、`:444-449` | prompt 无世界行；refs 命中 0 | **未接通（零暴露）** |
| L6 消费 | `life/agent.py:593-612`（读）、`:614-630`（唯一消费）、`engine/world_params.py:45-59` | 仅 `activity_weight` 被消费；`market_scarcity_bp` 仅参与"非空"布尔 | **基本未接通** |

---

## 2. L1 剂量层：每周不到一次是配置的必然

### 2.1 剂量先被曲线对折

`config/world_director.json` 的 `dose_curve = "conservative"`；`resolve_dose()`（`world_director.py:45-58`）对 `prob_bp` 乘 `5000/10000`（`DOSE_CURVES.conservative`，`world_director.py:20-24`）：

| 机制 | 配置 prob_bp | 曲线后生效 prob_bp | 84 回合期望 E | 实测 N（A0 批） |
|---|---|---|---|---|
| `wd.festival` | 100 | **50** | **0.42** | **0** |
| `wd.edict` | 50 | **25** | **0.21** | **0** |
| `wd.tension` | 80 | **40** | **0.336** | **1** |
| 合计 | — | — | **0.966** | **1** |

（其余 7 个机制 `enabled=false`，其中 `wd.mass_event` 的 `prob_bp=0`，即使打开也 ≡ 关闭，见 `mechanism_enabled()` `:61-70` 的"剂量 0 ≡ 关闭"）

### 2.2 "roll 8 < prob 40" 是运气还是剂量过低？

**两者都不是"实现坏了"，而是"剂量本就低到只该出 0–1 条"，这一条恰好落在下尾。**

roll 分布（seed=42，84 回合，`rng_branch(42, round, mech_idx)`，`mech_idx` 取 `sorted(mechanisms)` 的下标）：

| 机制 | mech_idx | min | p1 | p5 | **p50** | max | 命中数（roll<prob） |
|---|---|---|---|---|---|---|---|
| `wd.edict` | 1 | 59 | 299.7 | 712.95 | **5495** | 9978 | 0 |
| `wd.festival` | 3 | 552 | 561.96 | 1411.9 | **5481** | 9748 | 0 |
| `wd.tension` | 8 | **8** | 79.38 | 872.55 | **5038.5** | 9909 | **1（round 30, roll=8）** |

- 三组 roll 的中位数都 ≈5000，分布形似 U(0,10000) ⇒ RNG 无偏。
- `wd.tension` 的最小值 8 落在 0.08% 分位，正好低于 40 的阈值 ⇒ 这一条是**低概率事件的正常下尾抽样**，不是"阈值算错"。
- Poisson 参考：E=0.966 时 P(0)=0.381、P(1)=0.368、P(≥2)=0.252 ⇒ 观测 1 条**是最可能的两种结果之一**。
- 反过来说：**即便把曲线调到 `aggressive`，E 也只有 3.864 条/周**（edict 0.84 + festival 1.68 + tension 1.344），仍然谈不上"镇上天天有事"。

### 2.3 结论
L1 判据：`E_m < 1` ⇒ 稀有事件，不得判 bug。**本层判「剂量过低（配置问题）」**。这也是为什么"只调剂量"最多把 84 回合的 1 条变成 3–4 条——**它不会让事件进入对话**（见 §5）。

---

## 3. L2 触发层：复算与日志逐条全等

```bash
cd code && python3 - <<'PY'
import json
from engine.world_director import cfg_of, mechanism_enabled, resolve_dose, rng_branch
cfg = cfg_of({'world_director': json.load(open('config/world_director.json'))})
idx = {m:i for i,m in enumerate(sorted(cfg['mechanisms']))}
rc=[]
for r in range(84):
    for mid in sorted(cfg['mechanisms']):
        if not mechanism_enabled(cfg,mid): continue
        prob=int(resolve_dose(cfg,mid)['prob_bp']); roll=rng_branch(42,r,idx[mid],1)[0]%10000
        if roll<prob: rc.append((r,mid,roll))
print('复算:',rc)
print('日志:',[(json.loads(l)['payload']['issued_round'],json.loads(l)['payload']['mechanism_id'],
              json.loads(l)['payload']['rng_branch']['roll_bp'])
             for l in open('../v2/evidence/run_d2_after_n16_seed42/run.jsonl') if '"WORLD_DIRECTIVE"' in l])
PY
```
实测输出：
```
复算: [(30, 'wd.tension', 8)]
日志: [(30, 'wd.tension', 8)]
完全一致: True
```
⇒ **L2 接通**。另附：`WORLD_DIRECTIVE_REJECTED` 在 A0 批 **0 条**（`grep -c` = 0）⇒ 没有"触发了但被 R1–R6 判死"的隐性损耗。

---

## 4. L3 影响面层：`affected_scope_count` 是字面量 0，不是解析结果

```bash
$ grep -rn "affected_scope_count" code --include=*.py
code/engine/hooks/world_director.py:48:            "end_round": d["expires_round"], "affected_scope_count": 0,
```

- **全仓仅此一处写入**，值是 Python 字面量 `0`；不存在任何"按 scope 解析受影响 agent"的函数（`grep -rn "affected" code --include=*.py` 亦无其它实现）。
- 因此**不是** scope 解析缺陷（压根没有解析），也**不是** "global 级本就不产生 affected 列表"的设计——`validate_directive()` 里只对 `scope.level=agents` 做 K 规模审计（`world_director.py:112+` 的 WD-D1），`global/place` 的"受影响对象"从未被枚举。
- 日志证据（唯一那条）：`{"kind":"tension","scope":{"level":"global","place":null},"affected_scope_count":0,...}` —— 16 个 agent 实际都"受影响"（每个都在 visible_events 里看到了它，见 §5），但字段写 0。

**判定：L3 未接通，且断点性质是"字段从未计算"。** 对 life-engineer 的含义：这个字段若要变成真读数，要么在 hook 里按 `scope.level` 枚举（`global`→存活 agent 数、`place`→当时该地 agent 数），要么明确标注为"保留字段、恒 0 不代表无影响"——**两种都要写进文档，不能留 0 让下游当事实读**。

---

## 5. L4 感知 / 沉淀层：看得见，记不住

### 5.1 暴露 = 真（每个 agent 都看得到）

`config/perception_scope.json` 把两类事件定为 `global`：
```json
"WORLD_DIRECTIVE": "global",
"WORLD_GROUP_EVENT": "global",
```
（sha256 `c6306689…8601`；`life/agent.py` 与 `engine/perceive.py` 都委托 `contracts/visibility.py`）

实测（纯函数复算，输入即 A0 批日志）：
```bash
cd code && python3 - <<'PY'
from engine.runner import read_log
from engine.perceive import visible_events
recs = read_log('../v2/evidence/run_d2_after_n16_seed42/run.jsonl')
for aid in ('P001','P009','P016'):
    for rnd in (29,30,31,36,40):
        ve = visible_events(recs, aid, rnd)
        print(aid, rnd, [(e['seq'],e['type']) for e in ve if e['type'].startswith('WORLD_')])
PY
```
实测输出（摘要）：
```
P001 29 []
P001 30 [(39222,'WORLD_DIRECTIVE'), (39223,'WORLD_GROUP_EVENT')]
P001 31 [(39222,...), (39223,...)]    # 36 / 40 同样可见
P009 31 [(39222,...), (39223,...)]
P016 31 [(39222,...), (39223,...)]
```
⇒ **但必须区分两条路径（2026-10-20 22:34 自查更正，见 §11 修订记录）**：
- **真实跑批路径**（`KernelAdapter.perceive` → `visibility_query` → `VisibilityIndex.visible(window_rounds=VISIBLE_WINDOW_ROUNDS)`，`VISIBLE_WINDOW_ROUNDS = 2`，`orchestration/integration.py:275/322-346`）：世界事件只在 **round 30 / 31 / 32** 可见，round 33 起不可见 ⇒ 真实曝光 = **16 agents × 3 回合 = 48 个 agent-回合**。实测：
  ```
  round 30 world_visible= [39222, 39223]
  round 31 world_visible= [39222, 39223]
  round 32 world_visible= [39222, 39223]
  round 33 world_visible= []
  round 35 world_visible= []
  round 40 world_visible= []
  ```
- **`contracts.visible_events` 路径**（无 `window_rounds`，被 `life/settlement.py:620` 的 L6 使用，也是我上一版误用的复算入口）：对同一日志在 round 33/40 **仍可见** ⇒ 这条路径确实"不裁剪时间"。

**本节原结论"16×54=864 agent-回合"作废**，正数为 **48 agent-回合（真实路径）**。这不改变"可见层是通的"这一判断（见 §5.1 首句与 batch-runner 双人核验），但把曝光窗口从"半个模拟周"更正为"3 个回合"。

### 5.2 沉淀 = 0（断点在白名单）

```python
# code/life/agent.py:41-45
_SALIENT_EVENTS = {
    "ACTIVITY_STARTED", "ACTIVITY_COMPLETED", "PLACE_ARRIVED",
    "MSG_PUBLIC", "MSG_DM", "MSG_GROUP", "RELATION_ENCOUNTER", "RELATION_CHANGE",
    "SEED_EVENT", "AGENT_DIED", "TAG_EMITTED", "NARRATIVE", "NORM_VIOLATED",
}
# code/life/agent.py:403
if ev.seq in self._observed_seqs or ev.type not in _SALIENT_EVENTS:
    continue                      # ← 世界事件在这里被丢弃：不进记忆、不发 OBSERVATION
```
日志证据（精确匹配，非子串）：
```bash
$ python3 -c "..."   # 见 §9 复算清单 ②
精确引用世界事件 seq 的记录数 = 0
$ grep -c '"source_event_seq":39222' v2/evidence/run_d2_after_n16_seed42/run.jsonl   # 0
$ grep -c '"source_event_seq":39223' v2/evidence/run_d2_after_n16_seed42/run.jsonl   # 0
$ grep -c '"target_event_seq":39222' v2/evidence/run_d2_after_n16_seed42/run.jsonl   # 0
```
（提醒：`grep -c '39222'` 会命中 28 行，但那些是 `MEMORY_FORGET` 的数值巧合；**精确字段匹配才是 0**——这正是 R1 里"光看名字/子串会误判"的同款坑。）

**判定：L4 暴露接通、L4′ 沉淀未接通。** 理论上若把两类事件加进白名单，本批最多新增 **16 agents × 2 事件 = 32 条** observation（`_observed_seqs` 按 seq 去重，每 agent 每事件 1 条），这是"上限很小但非零"的量——足以让"镇上出过事"进入记忆，但**不足以**让每句话都提它。

---

## 6. L5 对话层：**世界层事件对对话零暴露**

### 6.1 提示词里根本没有"世界"这一行

```python
# code/life/agent.py:1050-1058  _dialogue_prompt
return (self.persona.compressed_profile(self._current_goal())
        + f"\n场景：{tid}；对象：{others}。{self._mood_line()}。"
        + (rift_line or "")          # R6-T2：处境（事实+选项）；关闭/无旧账时为空串
        + "\n请用一句话自然地说点什么。")

# code/life/agent.py:1060-1069  _reply_prompt
return (self.persona.compressed_profile(self._current_goal())
        + f"\n你正在和{who}聊「{topic}」。{self._mood_line()}。"
        + (rift_line or "")
        + f"\n刚才的对话：\n{lines}"
        + "\n请接着说一句。")
```
装配项只有：**人设压缩档 + 场景/对象 + 关系(熟悉度/好感) + 情绪&最紧需求 + 可选的 rift 处境 + 对话历史**。`world_params` 的任何一个字段（`active` / `activity_weight` / `market_scarcity_bp`）**都没有出现在提示词里**。

### 6.2 检索也捞不到

```python
# code/life/agent.py:444-449
def _retrieval_query(self, wv) -> str:
    recents = [n.text for n in list(self.memory.nodes.values())[-3:]]
    head = f"{self.persona.compressed_profile(self._current_goal())} {self._activity_for(wv)[0]}"
    return head + " " + " ".join(recents)
```
检索 query 的三段全部与"世界事件"无关；而世界事件在 §5.2 已确认**未进记忆** ⇒ **检索不可能返回它** ⇒ 即使记忆里有，也没有"世界"这条召回路径（query 里无相关词）。

### 6.3 输出侧也无引用

- 对话消息 payload 的 `refs` 字段：**0 条**提到世界事件 seq（§9 ② 的精确扫描）。
- `LLM_CALL` 只落 `prompt_hash` 不落 prompt 正文（payload keys 实测），所以"prompt 无世界行"只能由代码判据证明——本文给的就是代码行号，且 `_dialogue_prompt` 的输入参数只有 `(tid, parts, cfg, rift_line)`，**没有任何世界参数可传**（签名即证明）。

**判定：L5 判「世界层事件对对话零暴露」**，与本轮预注册的最重要判据一致。

---

## 7. L6 消费层：`market_scarcity_bp` 只有"布尔计数"，没有功能消费

### 7.1 三个可非空字段的消费清单

| 字段 | 产生位置 | 非测试代码读取点 | 是否功能消费 |
|---|---|---|---|
| `activity_weight` | `world_params.py:49-51`（festival/mass_event） | `life/agent.py:624-630`（`_activity_for` 里改为倾向高权重且合法的 place） | ✅ **有** |
| `resource_factor_bp` | `world_params.py:52-55`（supply_shock/disaster） | 无 | ❌ **无** |
| `market_scarcity_bp` | `world_params.py:56-59`（tension/edict/scarcity） | `life/agent.py:610-611`，只用于 `_wp_nonempty` 计数（`if (... or wp.get("market_scarcity_bp") ...)`） | ❌ **无功能消费** |
| `active` | `world_params.py:43-45` | `life/agent.py:610-611` 同上（只计数） | ❌ 无决策消费 |

grep 原文：
```bash
$ grep -rn "activity_weight\|resource_factor_bp\|market_scarcity_bp" code/life/agent.py code/life/*.py code/obs/*.py
code/life/agent.py:597:        `{"activity_weight": {place:int}, "resource_factor_bp": {..}, "market_scarcity_bp": {..}, "active": [..]}。`   # docstring
code/life/agent.py:610:        if (wp.get("activity_weight") or wp.get("resource_factor_bp")
code/life/agent.py:611:                or wp.get("market_scarcity_bp") or wp.get("active")):
code/life/agent.py:621:        # T364 / D3 口径②：消费 `world_params.activity_weight` ...
code/life/agent.py:624:        aw = wp.get("activity_weight") or {}
```
```bash
$ grep -rn "world_params" code/engine --include=*.py | grep -v world_params.py
（空）      # engine 侧也没有任何消费点
```

### 7.2 本该消费它的四处 life/engine 逻辑（现状：都没接）

| 本该消费的地方 | 现状代码 | 现状读数 |
|---|---|---|
| ① **议价/定价** | `life/agent.py:1101`：`price = 50 + int(sha256_hex(f"ask:{agent}:{round}")[:6],16) % 151` —— 自身确定性定价，与稀缺无关 | 稀缺期（round 30–35）唯一一笔 `MARKET_TRADE`：`{"scarcity_index":0,"unit_price":100}` —— **稀缺参数 1000bp 在，价格照旧** |
| ② **市集稀缺度** | `engine/hooks/econ.py:249-266` `_scarcity_index()`：`100 − floor(100·stock/demand)`，用的是静态 `market_scarce_supply` 与近 W 回合需求计数 | 同上，稀缺期读到 `scarcity_index=0` |
| ③ **活动选择（稀缺抢购/囤货）** | `life/agent.py:614-630` `_activity_for()` 只认 `activity_weight`；`scarce_buy` 模板由 `SCHEDULE_PLANNED` 决定 | 稀缺期 6 回合内 `MARKET_TRADE=1`，窗口前后对比 24–29 回合=0 / 30–35=1 / 36–41=0 / 42–47=5——**无任何"稀缺→抢购"的抬升**（且样本太小，仅作方向注记） |
| ④ **抱怨/闲聊话题** | 提示词无世界行（§6.1） | 对话里不会出现"最近市面紧"之类的话头 |

**判定：L6 判「基本未接通」**——只有 festival 那条路（`activity_weight`）通，而 festival 在 84 回合里 **0 次触发**（§2.1）。所以现状是：**唯一能影响行为的参数从不触发，唯一触发的参数不影响任何行为**。

---

## 8. 给 life-engineer 的最小接线建议（本文不实施，只提候选）

按"改动面最小 → 语义最完整"排序，三个候选接点（**都必须分支 + 开关默认关 + prompt_sha/配置 diff 证据**）：

1. **观测白名单开口（L4′）**：`_SALIENT_EVENTS` 纳入 `WORLD_DIRECTIVE`/`WORLD_GROUP_EVENT`，并在 `_describe_event()`（`agent.py:1259+`）补一条中文描述（如「镇上气氛紧张，市面开始缺货」）。上限 32 条 observation，成本 0 额外 LLM。
2. **提示词补一行世界状态（L5）**：在 `_dialogue_prompt`/`_reply_prompt` 里加一行"世界：…"（由 `world_params()['active']` 派生，**只给情境不给结果**，与 `world_params` 的设计红线一致）。这是"事件进对话"的唯一低风险管道——**只改措辞行，不改决策**。
3. **消费点接通（L6）**：让 `_activity_for` 或定价逻辑读 `market_scarcity_bp`（或让 `engine/hooks/econ.py::_scarcity_index` 把 world scarcity 作为叠加项）。**这是唯一会改变世界数值的改法，必须单独开关 + 单独消融**，不要和 1/2 混在一批里，否则无法归因。

**同时请顺手修掉的两个"读数可信度"问题**（都不改行为）：
- `affected_scope_count`（`hooks/world_director.py:48`）：要么算真值，要么改名标注 `affected_scope_count_uncomputed`；
- **时间窗两条路径不一致**（§5.1，含 22:34 更正）：真实 perceive 路径有 `VISIBLE_WINDOW_ROUNDS=2` 的滑动窗（不是 `[start,end)` 语义，但确有界）；而 `contracts.visible_events`（L6 `settlement.py:620` 在用）**无窗口** ⇒ 一旦白名单放开，L6 会持续观察"过期事件"。建议：要么给 `contracts.visible_events` 加 `window_rounds` 参数并在 L6 传入，要么把 L6 也改为走 `VisibilityIndex`，**两条路径必须同源同界**。

---

## 9. 复算清单（第三方按原样命令核对全文每个数字）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# ⓪ 数据与代码身份
git rev-parse HEAD
sha256sum v2/evidence/run_d2_after_n16_seed42/run.jsonl v2/evidence/run_d2_after_n16_seed42/meta.json
sha256sum code/config/world_director.json code/config/perception_scope.json

# ① L1/L2：剂量 + roll 复算 + 与日志比对
cd code && python3 - <<'PY'
import json
from engine.world_director import cfg_of, mechanism_enabled, resolve_dose, rng_branch
cfg = cfg_of({'world_director': json.load(open('config/world_director.json'))})
idx = {m:i for i,m in enumerate(sorted(cfg['mechanisms']))}
for mid in sorted(cfg['mechanisms']):
    if not mechanism_enabled(cfg,mid): continue
    prob = int(resolve_dose(cfg,mid)['prob_bp'])
    rolls = [rng_branch(42,r,idx[mid],1)[0]%10000 for r in range(84)]
    print(mid, 'prob_bp=',prob, 'E=',round(84*prob/10000,3), 'N=',sum(1 for x in rolls if x<prob),
          'min=',min(rolls),'max=',max(rolls))
PY
# 与日志比对
cd .. && python3 - <<'PY'
import json
lg=[(d['payload']['issued_round'],d['payload']['mechanism_id'],d['payload']['rng_branch']['roll_bp'])
    for d in map(json.loads,open('v2/evidence/run_d2_after_n16_seed42/run.jsonl')) if d.get('type')=='WORLD_DIRECTIVE']
print('日志触发集:',lg)
PY
grep -c '"WORLD_DIRECTIVE_REJECTED"' v2/evidence/run_d2_after_n16_seed42/run.jsonl

# ② L3/L4：影响面字段的唯一写入 + 世界事件在日志中被引用的精确条数
grep -rn "affected_scope_count" code --include=*.py
python3 - <<'PY'
import json
tg={39222,39223}; n=0
for line in open('v2/evidence/run_d2_after_n16_seed42/run.jsonl'):
    p=(json.loads(line).get('payload') or {})
    if p.get('source_event_seq') in tg or p.get('target_event_seq') in tg or \
       any(str(x) in {str(t) for t in tg} for x in (p.get('refs') or [])): n+=1
print('精确引用世界事件 seq 的记录数 =',n)
PY

# ③ L4：世界事件是否进入 visible_events（三 agent × 五点抽样）
cd code && python3 - <<'PY'
from engine.runner import read_log
from engine.perceive import visible_events
recs = read_log('../v2/evidence/run_d2_after_n16_seed42/run.jsonl')
for aid in ('P001','P009','P016'):
    for rnd in (29,30,31,36,40):
        ve=visible_events(recs,aid,rnd)
        print(aid,rnd,[(e['seq'],e['type']) for e in ve if e['type'].startswith('WORLD_')])
PY

# ④ L5：提示词装配与检索输入（代码判据）
cd .. && sed -n '1050,1069p' code/life/agent.py        # 两个 prompt 函数全文
sed -n '444,449p' code/life/agent.py                    # _retrieval_query
sed -n '41,45p;395,405p' code/life/agent.py             # _SALIENT_EVENTS + 过滤点

# ⑤ L6：消费点 grep
grep -rn "activity_weight\|resource_factor_bp\|market_scarcity_bp" code/life/agent.py
grep -rn "world_params" code/engine --include=*.py | grep -v world_params.py   # 空
sed -n '249,266p' code/engine/hooks/econ.py             # engine 自己的 scarcity 代理

# ⑥ 稀缺期交易样本（证明 scarcity 未影响价格）
python3 - <<'PY'
import json
for d in map(json.loads, open('v2/evidence/run_d2_after_n16_seed42/run.jsonl')):
    if d.get('type')=='MARKET_TRADE' and 30<=d['round']<=35:
        print({k:v for k,v in (d.get('payload') or {}).items() if k in ('scarcity_index','unit_price','good_id','qty')})
PY
```

---

## 10. 局限（不藏）

1. **单 seed、单批、单模拟周（16×84）**：L1 的 0/1/0/1 是**事件级事实**，不是"发生率估计"；分母 <30，按全族纪律**只报事件数**。
2. **"零暴露"是代码级判据**：`LLM_CALL` 只落 `prompt_hash`，日志里没有 prompt 正文，因此无法用日志直接看"这句话里有没有世界"；本文用的是"装配函数签名 + 函数体 + refs 精确扫描 + 检索输入"四重代码/数据判据。若有人质疑，请按 §9 ④ 复核代码行号。
3. **`affected_scope_count` 的"应有值"取决于口径**：`global` 到底是"全体存活 agent"还是"当时在公共场所的人"未有定论；本文只断言"它是字面量 0，从未计算"，**不对应有值下断言**。
4. **可见性不裁剪时间窗**（§5.1）是本次顺带发现的独立问题，**未在本轮范围内深挖**，只记录。
5. 本文**不做任何"接通后会怎样"的效果预测**——那是 `d-dim-impl` 之后 A/B 的事。

---

## 11. 修订记录（只追加；原文保留可见）

- **修-1（2026-10-20 22:34，作者自查，触发于 Leader 转述 life-engineer 的实现位置）**：
  §5.1 原写"从 round 30 起 16×54=864 agent-回合可见、过期后仍永久可见"。该结论基于 `engine.perceive.visible_events`（委托 `contracts.visibility`，无时间窗），但**真实跑批路径不是它**——实际是 `KernelAdapter.perceive` → `visibility_query` → `VisibilityIndex.visible(window_rounds=2)`（`integration.py:275`）。按真实路径复算：**round 30/31/32 可见、33 起不可见，曝光 = 16×3 = 48 agent-回合**。
  影响面：① §5.1 的曝光数（864→48）；② §8 与"遗留问题 #2"的措辞（"永久可见"只对 `contracts.visible_events`/L6 路径成立，对 perceive 路径不成立）；③ 对 life-engineer 的含义：它在"取候选阶段"加的时间窗对 perceive 路径是**与既有 `window_rounds=2` 叠加/重复**的，真正缺窗的是 L6 那条 `contracts.visible_events` 调用。
  其余结论（L1 剂量、L2 触发、L3 影响面、L4 沉淀 0、L5 零暴露、L6 消费）**不受影响**：它们的证据不依赖时间窗，且 §5.2 的"0 条沉淀"在 round 30–32 窗口内同样成立。
