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

## 2d. T259 批次 4：前景 / 天空 / 地面 层次层（`#grading`）

**目的**：给画面加"空气感 / 镜头景深"，直接对应「**增加效果和输出的丰富程度**」里的"层次（前景/天空）"。
**纯 CSS 覆盖层**（`index.html` `#grading` + `styles/app.css`），与昼夜光照层（`town.setLighting`，z-index=5）**分离**：本层只做天空冷色(顶)、暗角(前景)、地面暖色渐隐(底)、极细扫描颗粒，z-index=6（HUD 之下）。**不碰任何世界语义 / config**。

**取证参数**：`?grade=0` = 关闭本层（"改前"对照）；默认开（"改后"）。still 单帧、view=default、1500×950、`sample/run_c_n20.play.jsonl`。

| 场景 | 改前 | 改后 | 逐像素差(mean/max/占比) |
|---|---|---|---|
| 白天 round 60 06:00 | `T259-g4-layer-day-before.png` | `T259-g4-layer-day-after.png` | 5.12 / 119 / 54.5% |
| 夜间 round 45 00:00 | `T259-g4-layer-night-before.png` | `T259-g4-layer-night-after.png` | 4.59 / 118 / 55.4% |

**改前/改后差异来自覆盖层本身**（暗角使边缘变暗、顶部偏冷），**世界内容零改动**（同日志、同 round、placeLayer=17 不变）。
**回退**：删 `#grading` div + `.grading` 样式即可；或运行时 `?grade=0`。

## 4. B 部分「播放件」（★ leader 指定，供真人盲测）

**入口**：`frontend/review.html` → `http://<host>:8848/review.html`（**用户点开即用**）。
**形态**：左侧 5 个片段按钮（`round 6/21/33/45/60`，时刻由 `wallClock` 口径确定性标注）+ 5×5 打分表（维度×片段，1–5）+「汇总结果」；右侧 iframe 内嵌小镇播放器，点片段即 `?round=X&speed=150&autoplay=1` 自动播放。
**指令**：看完 5 段（≤3 分钟）逐格打分 → 汇总见均分与达标。
**判据**：均分 ≥4 **且** 无人 ≤2。

新增 URL 参数（`main.js`）：`?autoplay=1`（载入即播）、`?speed=<ms>`（定速）。二者仅影响播放控制，不改变渲染数据。
**截图**：`T259-g4-review.png`（页面 + 内嵌播放器 + 打分表）。
**门禁**：`make ci` → **PASS**（smoke + gate_render placeLayer=17 + R9 四指标全绿）。

---

# 【修观感】—— 用户人工盲测 1.60/5 未达标后的重瞄（leader 2026-10-12 批准）

**统一验收（已改）**：**用户在 review.html 的人眼均分 ≥4 且无人 ≤2**（不再看"做了几项效果"）。
我的层 = **shell**：默认镜头 / 事件表现 / 非空白校验（`town.js` 光影归 art-director）。

## 5. 默认镜头：1x 全景 → 1.6x 聚焦活动最密处（★ 单点收益最大）

**根因**：`cam.scale=1` 把整城塞进一屏 → 建筑/角色仅几十像素 → **"离远看哪哪都一样"**（= 用户"都长得差不多"）。
**改法**（`main.js::focusCamera`）：首屏把镜头拉近到 **1.6x** 并居中到**全体角色质心**（≈当前活动最密处）；
首屏抑制"近景自动切 info"的档位跳变以保持建筑名分层；
**可回退**：`?cam=fit` 保留旧全景行为，`?camscale=<n>` 调倍率。

**改前/改后（still · view=default · 1500×950 · `sample/run_c_n20.play.jsonl`）**：

| round | 改前(全景 fit) | 改后(1.6x 聚焦) |
|---|---|---|
| 6（暮 18:00） | `T259-cam-r06-before.png` | `T259-cam-r06-after.png` |
| 60（晨 06:00） | `T259-cam-r60-before.png` | `T259-cam-r60-after.png` |

改后：建筑可辨识、角色成组可见、画面有焦点 → 首屏读成"**一个地方**"而非"一张地图"。
**门禁**：`make ci` → **PASS**（含 R9 四指标不变：0.7325/0/0.9180/0 —— 镜头只改取景，不改世界数据）。

## 6. 非空白校验（防"盲测撞白帧被判 1 分"）

**发现**：批量截图中曾出现**一次整幅白帧**（复测 3/3 正常，非稳定 bug；疑资源竞争下首帧时序）。
**危害**：`shot.py` 的就绪信号只保证"已就绪"，**不保证"画面非空白"** —— 盲测若撞上=直接 1 分。
**改法**（`shot.py`）：截图后算**整帧最大单色占比**（量化 16 级/通道），`≥0.5` → **SHOT FAIL 非零退出**。
**标定（实测）**：正常帧 ≈0.12–0.13；白帧 ≈0.57 → 0.5 分隔，两侧余量 >3×。
**反向验证**：对实际白帧 `T259-nonblank-whiteframe-example.png` → `frac=0.565` → **判定 blank**；
对正常帧 `T259-nonblank-normal.png` → `frac=0.132` → **ok**。→ **能对坏输入变红才算判据。**
