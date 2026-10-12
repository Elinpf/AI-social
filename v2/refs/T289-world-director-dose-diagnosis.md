# T289 只读诊断：世界导演默认开，为何一周几乎不产事件？

**日期** 2026-10-12 · **作者** kernel-dev · **性质** 只读诊断（未改任何代码）· **sha** `6a5f14e`（A–D 四批同一 sha）

## 0. 一句话结论

**两者都是**：世界导演**剂量本来就极小**（保守曲线把 0.5–1%/回合再砍半 → 实测约 **1 次/周**），**且即便触发也是世界状态 no-op**（replay 视为审计折叠，唯一消费者是叙事层 `devtools/storyteller`）——**对世界零机械影响**。
另：**“B 比 A 少 11 个事件”这个口径不可用作剂量证据**（见 §4）。

## 1. 直接计数（稳健证据）

对今晚真实批次日志逐条统计（A = `v2/evidence/run_t236_canon_n20_llm.jsonl`；B = `/root/t271/runs/nightly/B/run.jsonl`，B 的唯一开关 = `world_director.json:enabled=False`）：

| 事件 | A（导演开） | B（导演关） |
|---|---|---|
| `WORLD_DIRECTIVE` | **1** | 0 |
| `WORLD_GROUP_EVENT` | **1** | 0 |
| `WORLD_DIRECTIVE_REJECTED` | 0 | 0 |
| 总计 | 301,384 | 301,395 |

⇒ **导演一整周（84 回合）只真正介入 1 次**（1 条 directive + 其派生 1 条 group event）。

## 2. 触发机制与剂量实况（看代码与配置，不凭印象）

- **开关未失效**：`config/world_director.json` `enabled=true`；hook `apply_world_director` 已挂 **PHASE4 链首**（`engine/hooks/__init__.py:59`）；`EVENT_TYPES` 已登记（T238），登记门控放行。
- **触发**：`engine/world_director.py::plan_directives` 对**每个 enabled 机制、每回合**掷一次 `roll = rng_branch(seed,"world_director",round,idx) % 10000`，`roll < prob_bp` 才触发（`prob_bp` = 万分比）。
- **剂量曲线在削减**：`resolve_dose` 把 `*_bp` 键 × `curve.prob_bp/10000`。当前 `dose_curve="conservative"`（`prob_bp=5000`）⇒ **把基础概率再砍半**：
  - `wd.festival` 100bp → **50bp**（0.5%/回合）
  - `wd.edict` 50bp → **25bp**（0.25%/回合）
  - `wd.tension` 80bp → **40bp**（0.4%/回合）
  - 其余 7 机制 `enabled=false`
- **期望值**：84 回合 ×（50+25+40）/10000 ≈ **0.97 次/周** ⇒ **与实测 1 次吻合**。
- ⇒ **不是“没生效”，是“剂量极小”**（保守曲线半衰后再叠加“每机制独立、基数本就很低”）。

## 3. 更关键：触发了也**不改世界状态**（对 D3 的风险）

- `engine/replay.py:643-648` 把 `WORLD_DIRECTIVE / WORLD_GROUP_EVENT / WORLD_DIRECTIVE_REJECTED / FORGE_FIRED` 列入 `_NOOP_TYPES` ⇒ **replay 折叠为 no-op，不改任何 state**。
- 全仓消费者检索：这两个事件**只被 `devtools/storyteller.py`（叙事读取）引用**（`engine/hooks/world_director.py` 是发射方本身）。**engine / life / obs / econ 均不消费**其 `scope/params`。
- ⇒ 即便“1 次/周”触发，**世界行为不发生任何变化** —— 当前世界导演实质是**旁白/审计型**，**不是** D3 要的“产生宏观群体事件、不只是观察者”。

## 4. ⚠️ 为什么不能拿“少 11 个事件”当剂量证据

- 核对 `WORLD_INIT.config_components`：A 与 B **唯一差异 = `world_director.json`**（其余 12 个组件同 hash）⇒ 名义上是单变量消融。
- **但**：`A vs B` 的类型差异**超出 director 的 2 条** —— `PERSONA_DRIFT` A=0 / **B=9**、`MEMORY_FORGET` A=143543 / B=143547(+4)；且 **B（关导演）反而比 A 多 11 条**。若真只是关掉一个 no-op 事件族，A 应比 B **多 2 条**，不该反向。
- ⇒ **A/B 之间存在 director 之外的非确定性**（最可能：**每批独立 `side/freeze_cache` + 真 LLM** ⇒ 首跑命中真实模型、轨迹随即分叉；A/B 各自 cache 不共享）。**“−11 事件”是跨批噪声，不是导演剂量**。**剂量应以直接计数（=2）为准。**

## 5. 卡点定位

不是：开关未生效 / 未登记 / hook 未挂 / 事件发了没落日志（均排除）。
是：**(i) 剂量极小**（conservative 曲线半衰 + 基数低，≈1 次/周）；**(ii) 且无下游机械消费者**（no-op 折叠 + 仅叙事读取）⇒ 对世界零影响。

## 6. 最小修法（**不实施**，供裁）

1. **先定口径**（归 D3/08）：期望的**频率**是多少？“宏观群体事件”是否**必须改变世界状态**（需求/稀缺/日程/组织），还是**允许只是可观测叙事事件**？——这决定下面走哪条。
2. 若“允许旁白型”：只调**剂量**即可（`dose_curve` → `moderate`/`aggressive`，或提高 base `prob_bp`）——**配置变更，不动代码**，进指纹需重冻。
3. 若“必须改变世界”：需给 `WORLD_GROUP_EVENT` 加**机械消费者**（life/obs 按 `scope/params` 改变 agent 需求/稀缺/日程）——**动语义，须显式标注 + 交用户知悉**（按今日两问判据）。
4. **顺带**：A/B 应改为**共享同一 `freeze_cache`**（或在同一 side 根上 off/on 两次跑）才能得到**干净的消融对照**；否则真 LLM 跨批噪声会淹没小剂量信号（今日“假信号”同族）。
