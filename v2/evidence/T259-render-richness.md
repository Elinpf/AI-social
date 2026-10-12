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
