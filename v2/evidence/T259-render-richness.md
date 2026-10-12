# T259 · 渲染/效果丰富度（前端展示层，迭代）

> 作者：frontend-dev ｜ 只读展示层；不改 engine/life/freeze 语义；`travel_ticks`/place 集不动。

## 1. G-list 进度表（依 `v2/refs/gamefeel-executable-tasks-T240.md`）

| # | 项 | 状态 | 落点/说明 |
|---|---|---|---|
| G-1 | 统一调色板 + ramp + 抖动/描边/接地影 | 🟡 | 部分（T87/T120）；ramp 统一待 art |
| G-2 | 昼夜/天气光照分层、光晕像素化 | ✅ | T67/T120 |
| G-3 | 建筑/角色可辨性（体型轴/头身比） | ⛔ | 依赖 art 资产（T128/T112） |
| G-4 | 信息分层（标签分层/散点降密/一键景观） | ✅ | T116 |
| G-5 | 地图近全屏/面板折叠/缩放 | ✅ | T67/T119 |
| G-6 | 实时跟随 + 事件到达镜头/高亮 | ✅ | T75 |
| G-7 | 事件高亮（短促、不遮挡） | ✅ | T67/T116 |
| G-8 | 剧情卡→因果链（上游事件 + cause seq 可点） | ✅ | T240 |
| G-9 | 小镇周报面板（每周纪事 + 本周数字，逐句可溯源） | ✅ | T240 |
| G-10 | 故事线/POV 面板 | ⛔ | 依赖 POV/CAST 数据装配 |
| G-11 | 角色小传（CAST 聚合） | ⛔ | 依赖 CAST 数据 |
| G-12 | 经济/制度因果可视化 | ⬜ | 待 T101 面板数据 |
| **G-13** | **关键事件世界内反馈（成交/冲突/采纳 短动效）** | **✅ 本批** | **T259（见 §2）** |
| G-14 | 关系图随交互增删边可见 | ✅ | T240 |
| G-15 | 环境音/操作音 | ⬜ | 待定 |

## 2. T259 本批：G-13 世界内反馈短动效（成交 / 冲突 / 采纳）

**实现（只读展示层，`frontend/src/main.js`）**：新增 `worldFx(kind,x,y)`，复用 `fxLayer`（PIXI 覆盖层）
与 `nodeById/agents` 坐标，**仅由当前回合事件字段驱动**（可重放、无隐藏状态）：

| 事件 | 效果 | 落点 |
|---|---|---|
| `MARKET_TRADE` | 金环 + 上浮金币 + 「🪙 成交」 | `market` |
| `CONFLICT_STARTED/RESOLVED` | 红环 + 红叹号 + 「⚔ 冲突」 | 当事人角色 |
| `NORM_ADOPTED/PROPOSED` | 金色双环 + 「📜 采纳」 | `plaza`（并高亮 `town_hall`） |

**演示/取证参数**（可复现）：
- `?fx=0` 关闭世界内反馈 = **改前对照**；
- `?fxhold=1` 效果**保持峰值**（still 单帧即可拍到，且**确定可复现**）；
- `?fxg=<trade|conflict|norm>` 进入页面即在该落点触发一次（配合 `?fxhold=1` 用于证据）。

> 说明（诚实）：T240 §3 指出"**still 单帧无法证明动效**"。本批用 **峰值静止帧 + `?fx=0` 对照**
> 证明"**效果可见、位置正确、可复现**"；**动画过程本身**仍需录屏/多帧，未在本批宣称。

## 3. 证据（改前/改后 + sha256）

取证：`python frontend/tools/shot.py --url '...&still=1&fxg=<k>' --out ...`（等 `__RENDER_READY__`，见 T121）。

| 效果 | 改前（`?fx=0&fxg=k`） | 改后（`?fxg=k`，峰值） | 逐像素差异 |
|---|---|---|---|
| trade | `T259-fx-trade-before.png` `d1fb4d57…` | `T259-fx-trade-after.png` `4261bf3a…` | 0.115% |
| conflict | `T259-fx-conflict-before.png` `d1fb4d57…` | `T259-fx-conflict-after.png` `ae23ba73…` | 0.103% |
| norm | `T259-fx-norm-before.png` `d1fb4d57…` | `T259-fx-norm-after.png` `884581231…` | 0.119% |

（改前三张 sha 相同 = 同一确定性基线帧；chéng 改后各不同 = 三种效果各异。）

`make ci` → **PASS**（`gate_render` 无 pageerror + `smoke_test`，7.04s）。

## 4. 可回退

`worldFx` 为**新增独立函数**，调用点集中在 `handleKeyEvents` 与 `?fxg` 分支；`?fx=0` 即全局关闭。
回退只需删除该函数与两处调用（或在 UI 隐藏），不影响其它功能。

## 2b. T259 批次 2：事件表现扩展（更多世界内效果 + 私聊连线）

`worldFx` 新增 4 种 + 1 连线效果，接更多事件类型（仍只凭当前回合事件字段，可重放）：

| 事件 | 效果 | 落点 |
|---|---|---|
| `SEED_EVENT` | 绿环+芽 + 「🌱 种子」 | `plaza` |
| `GOAL_ACHIEVED` | 金环+星 + 「🏆 达成」 | 角色 |
| `GROUP_CREATED` | 青绿环+两点 + 「👥 组队」 | 角色 |
| `SKILL_LEVEL_UP` | 蓝环 + 「⭐ 升级」 | 角色 |
| `MSG_DM` | **两点连线 + 「💬 私聊」**（对话的可视化） | 说话人↔收件人 |

取证参数同上（`?fxg=<skill|celebrate|group|seed|dm>` + `?fxhold=1`；`?fx=0` 为改前）。

**证据（改前/改后 + sha256）**：

| 效果 | 改前 | 改后 | 逐像素差 |
|---|---|---|---|
| skill | `d1fb4d57…` | `20308dd0…` | 0.086% |
| group | `d1fb4d57…` | `c98c20e2…` | 0.100% |
| dm 连线 | `d1fb4d57…` | `05410d4f…` | 0.066% |

`make ci` → **PASS**（7.10s）。可回退：同上（新增分支 + 调用点，`?fx=0` 全关）。

## 2c. T259 批次 3：G-12 经济 / 制度因果面板（依 obs 面板契约 v2 P3/T101）

新增观测台 tab 「💰 经济」（`index.html` + `audit.js::renderEcon`），**只读、由当前日志确定性重算**（同日志可复现）：

| 区块 | 内容 | 来源（只读日志重算） |
|---|---|---|
| 经济循环 | `M(t)`（货币总量）+ 逐回合迷你折线、铸/销毁累计、税池、交易额/笔数、**流速 V**、**净值 Gini** | `TURN_SEAL.money_supply`、`MONEY_MINTED/BURNED`、`TAX_LEVIED/UBI_PAID`、`TRANSFER/MARKET_TRADE`、当前余额 |
| 制度涌现 | 规范**提议→采纳**漏斗 + 采纳率、群组数、契约/投票（**未产出**如实标注） | `NORM_PROPOSED/ADOPTED`、`GROUP_CREATED` |
| 沟通通道 | 私聊/公开/群聊 条形 | `MSG_DM/PUBLIC/GROUP` |

**诚实标注**：① 已知缺口 **G-P1-1**（Agent 间零交易/无工资 → 商品→货币通道缺失，V 偏低属预期）；② 契约/投票当前事件表无事件 → 标「未产出」；③ **口径说明**：`M(t)` 取 `TURN_SEAL`，而"铸/销毁"按事件累计，**二者口径不同，数值不吻合非异常**。

**证据**：`T259-g12-before.png`（改前：无该 tab）`b1e6cf5f…` ｜ `T259-g12-after.png`（改后）`4ec82b05…`。
**门禁**：`make ci` 曾 **FAIL**——`gate_render` 抓到 `pageerror: Unexpected identifier 'TURN_SEAL'`（我在模板串里误用了反引号），**mock 版 smoke 抓不到**；修复后 `make ci` **PASS**。→ **这正是"双门禁"存在的价值**（真渲染门禁抓到 mock 抓不到的真错）。

## 3. R9「沉浸/质感」口径（leader 批准；A 部分已进 CI）

**A. 可复算（`frontend/tools/immersion_metrics.js`，接入 `make ci` 第 3 步）**：
`activity_ratio ≥0.5` · `idle_round_ratio ≤0.2` · `causal_coverage ≥0.8` · `label_overlap_rate ≤0.05`。
**成立条件**：`view=default`·`scale=1`·960×720；校准日志 `sample/run_c_n20.play.jsonl` →
实测 `0.7325 / 0.0000 / 0.9180 / 0.0000`（PASS）。**反向**：`IMMERSION_LOG=sample/demo_run.jsonl` → `FAIL(3)` → CI 红。
**变更条件须重校**：视图/缩放/世界尺寸/人口/标签口径。

**B. 人工量表（3 分钟盲测，5 人，1–5 分）**：
① 这看起来是"一个在运转的小镇"吗？② 我大致知道"谁在做什么"吗？③ 画面乱/糊吗（反向）？
**判据**：三题均值 ≥4，且**无人给 ≤2**。样本片段固定为 `run_c_n20.play.jsonl` 的 5 段（round 6/21/33/45/60）。
