# town-viewer · 青溪镇像素回放观测台（T33）

> 从**事件日志**（JSONL）渲染出「青溪镇」与 Agent 轨迹的最小可用前端。
> 用户重点期待项：**PixiJS 像素小镇可视化**。

**纪律（写死在实现里）**
1. 前端**只读**日志/指标，绝不写世界、绝不参与判定；
2. 可视化数据**全部来自日志 + config**（可复现），不依赖运行中的私有内存；
3. 复用 AI Town 思路遵守 **MIT**（见 `NOTICE`，pixi.js 亦为 MIT 且已保留版权声明）；
4. 先交付「能从一个日志渲染出小镇与移动」，再扩交互与观测。

---

## 1. 快速开始

浏览器需通过 **http://** 访问（`fetch` 读 JSON 受同源策略限制，`file://` 直接打开会失败）。

```bash
cd code

# 启动内置静态服务（仅标准库）
python frontend/tools/serve.py
# → open http://127.0.0.1:8848/
```

打开后默认载入 `sample/demo_run.jsonl`（含 `PLACE_MOVE`，能看到 Agent 在场所间移动）。
顶栏可切换 / 拖拽载入任意 `.jsonl` 日志。

### 直接用内核日志验收

```bash
cd code
python -m engine run --seed 12345 --rounds 20 --out /tmp/hitt_run.jsonl

# 方式 A：把日志拷进 sample/ 并自动带上 ?log=
python frontend/tools/serve.py --log /tmp/hitt_run.jsonl

# 方式 B：页面里点「载入日志」选择 /tmp/hitt_run.jsonl（或把文件拖进页面）
```

> `engine run` 的空世界日志只含 `WORLD_INIT / AGENT_BORN / INIT_ENDOW / TIME_MARK / TURN_SEAL`
> （无移动，因为 Phase 3.5 生活 hook 默认空实现）。此时仍能渲染小镇、时间条与审计台，
> Agent 停在出生地。要看**移动**请用 `sample/demo_run.jsonl`，或在生活层 hook 注入后跑内核。

---

## 2. 界面

| 区域 | 内容 |
|---|---|
| 中：小镇舞台 | PixiJS 像素小镇。**AI Town tilemap 地形**（草地/土路/水塘/农田）+ 树木/灌木/石/花装饰 + 17 处场所建筑（按**类别**配色：居住/生产/加工/服务/教育/行政/交易/公共/娱乐/边缘）+ peeps 像素角色 |
| 左上 HUD | **挂钟时间**（1 tick = 2h，见下）+ 类别图例 + 口径说明（「1 tick = 2h（展示口径，引擎单位为抽象 tick）」） |
| 右：审计观测台 | 当前回合 **K 类事实**（存活/总数、存活率、货币总量、本回合事件、最热场所、累计事件）+ **事件流**（全部事件；非关键事件置灰，计数与「本回合事件」同口径） |
| 底：播放控制 | ⏮/◀/播放·暂停/▶/⏭、回合滑杆、速度（0.5x/1x/2x/5x）；键盘 `空格` 播放暂停、`←/→` 步进；下方**时间条**（每 tick 一格=2h，每 3 格一个时段、每 12 格一天） |

### 挂钟时间口径（纯展示，派生）

引擎内部仍是抽象 tick（12 tick/日、84 tick/周）。HUD 用 **1 tick = 2h** 展示：

```
tick_in_slot = round % 3 ; slot_idx = (round % 12) // 3 ; day = round // 12
hour = (6 + (round % 12) * 2) % 24
→ 早晨 06:00–12:00 / 午后 12:00–18:00 / 傍晚 18:00–24:00 / 夜里 00:00–06:00
```

实现见 `src/replay.js` 的 `wallClock()` / `wallClockText()`（`smoke_test.js` 有断言）。

## 3. 事件 → 可视化映射（只读）

| 事件 | 表现 |
|---|---|
| `PLACE_MOVE` / `PLACE_ARRIVED` | 角色在场所间**平滑移动**（PixiJS 逐帧靠拢） |
| `ACTIVITY_STARTED` / `ACTIVITY_COMPLETED` | 角色头顶**活动气泡**（`工作@farm` 等） |
| `MSG_PUBLIC` / `MSG_DM` / `MSG_GROUP` | **消息气泡**（取 `text/content/message`） |
| `AGENT_DIED` / `AGENT_REVIVED` | 角色**状态变化**（灰化 / 恢复，配色区分） |
| `AGENT_BORN` / `INIT_ENDOW` / `MONEY_*` | 建立 Agent 与货币余额（审计台货币总量） |
| `TIME_MARK` | HUD 逻辑时钟 |
| `TURN_SEAL` | 回合边界；若有 `money_supply` 则作为**权威货币总量** |

**货币总量**口径：优先取日志中 `TURN_SEAL.money_supply`；缺失时按事件流
（`INIT_ENDOW/MONEY_MINTED/MONEY_BURNED/TRANSFER/...`）确定性重算——两道口径都在
`src/replay.js` 中显式实现，便于与观测层 `metrics` 对齐。

## 4. 目录结构

```
frontend/
├── index.html                # 单页应用（无构建步骤）
├── styles/app.css
├── src/
│   ├── data.js               # 只读加载 config / 解析 JSONL
│   ├── sprites.js            # AI Town 素材的渲染原语（瓦片/角色/建筑/装饰）+ 确定性哈希
│   ├── town.js               # PixiJS tilemap 地形 + 装饰 + 场所 + 角色平滑回放
│   ├── replay.js             # 日志 → 按回合状态视图（确定性折叠）+ 挂钟时间 + 事件描述
│   ├── audit.js              # 审计观测台（K 类事实 + 事件流）
│   └── main.js               # 启动 + 播放控制 + 时间条
├── assets/                   # AI Town 美术素材（MIT，来源见 NOTICE）
│   ├── tileset.png           #   gentle-obj.png（地形/装饰 tileset）
│   ├── peeps.png             #   peeps.png（角色立绘）
│   └── player.png            #   player.png（备用）
├── data/
│   ├── places.json           # 取自 config/places.json（离线 bundle）
│   └── topology.json         # 由 tools/gen_topology.py 生成（离线 bundle）
├── sample/
│   ├── demo_run.jsonl                    # 生活层样例（含移动，20 回合）
│   ├── engine_run_seed12345_r20.jsonl    # 内核样例
│   ├── qingxi_demo_r12.svg               # 静态帧快照（自包含 SVG）
│   ├── qingxi_engine_seed12345_r19.svg   # 内核快照
│   └── qingxi_demo_r12_preview.png       # 快照 PNG 预览
├── tools/
│   ├── gen_topology.py       # 生成 config/topology.json（环层拓扑 + 坐标 + travel 矩阵）
│   ├── gen_demo_log.py       # 由 life 层确定性导出含移动的样例日志
│   ├── render_svg.py         # 无浏览器静态帧 SVG 导出
│   ├── smoke_test.js         # 无浏览器回归门禁（A 回放 / B 渲染 / C SVG）
│   └── serve.py              # 标准库静态服务器
├── vendor/pixi.min.js        # PixiJS v7.4.2（MIT）
└── NOTICE                    # 第三方许可与声明（PixiJS / AI Town 素材）
```

## 5. 数据来源（可复现）

- **场所**：`config/places.json`（17 处，`v1.1/00` §2.2）。
- **拓扑**：`config/topology.json`，由 `tools/gen_topology.py` 按 `v1.1/00` §2.3
  「中心–外围」规则展开为 **17×17 `travel_ticks` 常数矩阵** + 渲染坐标，
  脚本内自检**对称性**与**三角不等式**。矩阵落常数便于 diff 与复现（AR-D2）。
- **日志**：任意 `engine` / `life` 产出的 JSONL（两者记录格式一致）。

重新生成数据资产：

```bash
cd code
python frontend/tools/gen_topology.py      # 写 config/topology.json + frontend/data/topology.json
python frontend/tools/gen_demo_log.py      # 写 frontend/sample/demo_run.jsonl
```

## 6. 验收自检

- [x] 用 `python -m engine run --seed 12345 --rounds 20 --out /tmp/hitt_run.jsonl` 产生的日志可直接渲染；
- [x] 按回合**步进**并看到 Agent 移动（`sample/demo_run.jsonl`，含 15 次 `PLACE_MOVE`）；
- [x] `README` 说明如何启动（见 §1）。

无浏览器环境下的可复现门禁（本机若无 Chrome 时使用）：

```bash
cd code
node frontend/tools/smoke_test.js
# [A] 用真实样例日志验证回放/移动/气泡/事实；[B] 用最小 PIXI mock 跑渲染代码路径
# [C] 静态帧 SVG 导出断言（非空 / 17 场所 / 当前回合 Agent 数）
# → 全绿时输出 PASS
```

## 7. 无浏览器导出与验收（静态帧 SVG）

本机**无 Chrome**，无法截真实浏览器图。为此提供一条**无浏览器依赖**的渲染导出路径：
把「指定回合的小镇快照」渲染为一张**自包含 SVG**（内联样式、无外部依赖/图片/字体）。

### 一行命令

```bash
cd code
python frontend/tools/render_svg.py --log frontend/sample/demo_run.jsonl \
    --round 12 --out frontend/sample/qingxi_demo_r12.svg
```

参数：`--log`（JSONL，engine/life 产出皆可）、`--round`（目标回合 N，快照为「回合 N 结束时」）、
`--out`、可选 `--places/--topo`（默认 `config/places.json` / `config/topology.json`）、`--title`。

SVG 内容：① 17 处场所按类别配色 + 中文名 + 环层结构；② 当前回合各 Agent 所在位置
（`agent_id` + 存活/死亡状态）；③ 图例 + 标题（轮次/周/日/时段，来自 `TIME_MARK`）；
④ 页脚标注**数据来源**（日志文件名 + `log_hash=sha256:…` + 末哈希），**表明是从确定性日志重绘**。

- 只读日志/config，配色与 `src/sprites.js` 的类别常量一致（两套渲染同一口径）。
- 元素带 `class="place"` / `class="agent"` / `data-*` 属性，便于外部断言与二次加工。

### 样例（真实日志）

| 文件 | 来源 | 说明 |
|---|---|---|
| `sample/qingxi_demo_r12.svg` | `sample/demo_run.jsonl` @ round 12 | 含移动：3 个 Agent 分布在不同场所 |
| `sample/qingxi_engine_seed12345_r19.svg` | `sample/engine_run_seed12345_r20.jsonl` @ round 19 | 内核空世界：3 个 Agent 均在住宅 |

> **字体说明**：SVG 使用通用 CJK 字体栈
> （`Noto Serif/Sans CJK SC, Source Han Sans SC, PingFang SC, Microsoft YaHei, …`），
> 依赖查看端系统字体（未内嵌字体文件以保持自包含与体积）。浏览器/常规桌面可正常显示中文。
> 若在**无 CJK 字体**的极简容器中栅格化，中文可能显示为方框——这是渲染环境缺字体，不是 SVG 缺陷。

### 验收自检

- [x] 一行命令生成 SVG；
- [x] `node frontend/tools/smoke_test.js` 的 `[C]` 段断言通过（非空 / 17 场所 / 当前回合 Agent 数 / 无外链）；
- [x] 两张样例 SVG 生成（见上表）；
- [x] `pytest -q` 前端为独立子工程，不影响 Python 侧。

## 8. 美术升级：对齐 AI Town 像素风（T64）

> 用户拍板：把视觉升级到接近 a16z AI Town 的质感；**仅内部研究**，可带美术素材；
> **与主线并行，不阻塞引擎**。

- **素材**（MIT，来源与文件清单见 `NOTICE`）：
  - `assets/tileset.png` ← `ai-town:src/editor/tilesets/gentle-obj.png`（地形/装饰）
  - `assets/peeps.png` ← `ai-town:src/editor/spritesheets/peeps.png`（角色）
- **改造范围**：只**读取**这些 PNG 的像素区域（按瓦片/帧切图），**未迁移** AI Town 的
  源码（不引入 React/Convex、不连服务器）。地图布局/装饰摆放/建筑/角色渲染均为我方代码，
  由 `config/places.json` + `config/topology.json` + **固定哈希**确定性生成（可复现）。
- **瓦片索引** 由 `ai-town` 的 `data/gentle.js`（`bgtiles`/`objmap`）频次统计 + 逐 tile 颜色
  分析 + 目视确认得到，见 `src/sprites.js` 的 `TILES` / `DECOR` 常量。
- **仍严格只读**：不写世界、不参与判定；`ground < place < agent` 图层顺序有回归断言。

### 验收自检（T64）

- [x] `assets/tileset.png` / `assets/peeps.png` 就位，`NOTICE` 登记来源；
- [x] 浏览器端渲染 AI Town tilemap 地形 + 装饰 + peeps 角色（实时页可见）；
- [x] 挂钟 HUD + 时间条（1 tick = 2h），`smoke_test.js` 含口径断言；
- [x] `node frontend/tools/smoke_test.js` 全绿（含地形网格 / 图层顺序 / 挂钟口径）；
- [x] 新静态帧快照 `sample/qingxi_demo_r12.svg`（+ PNG 预览）生成。



## 9. 游戏化 shell（T67）

用户拍板「游戏样式优先」后，外壳从「工具台三栏」改为「游戏画面」：

| 能力 | 说明 | 实现 |
|---|---|---|
| 游戏优先布局 | 地图**近全屏**；审计面板改为**默认收起**的右侧抽屉（顶栏「📊 审计」开关，未删除）；播放控制改**悬浮半透明胶囊**；时间条贴底 | `index.html` / `styles/app.css` / `src/main.js` |
| 昼夜光照 | 按 `TIME_MARK` 的 slot 叠加色温/亮度覆盖（晨暖/午亮/晚橙/夜深蓝），**纯氛围** | `#lighting` + `main.js renderLighting()` |
| 镜头 | 滚轮缩放（光标为锚）+ 拖拽平移 + ＋/－/⤢ 复位；全局 NEAREST 保持像素锐利 | `main.js wireCamera()` |
| 关键事件高亮 | `AGENT_DIED/REVIVED/MARKET_TRADE/RELATION_CHANGE/NORM_*/ROLE_CHANGE…` → **顶部提示条** + 角色/场所**脉冲+光环** | `main.js handleKeyEvents()` |
| 轻交互 | 点角色→详情（状态/位置/活动/金钱/贷款/需求条/本回合事件）；点场所→场内人员与活动（可点人员） | `main.js renderAgentInspector/renderPlaceInspector` |

**演示参数**：`?audit=1` 展开审计抽屉；`?agent=<id>` / `?place=<id>` 展开详情；`?round=N` 固定回合。可叠加，如
`http://127.0.0.1:8848/?log=sample/demo_run.jsonl&round=12&agent=P003`。

**无头截图**：`bash frontend/tools/screenshot.sh [out.png] [logUrl] [round] [WxH]`（snap chromium 输出须到 `$HOME`）。
并排对比：`python frontend/tools/compare.py --left a.png --right b.png --out cmp.png`。

**交付截图**（`sample/`）：`qingxi_game_r12.png`（默认）、`qingxi_game_r12_audit.png`、`qingxi_game_r12_agent.png`。

**回归**：`node frontend/tools/smoke_test.js` 全绿；`0.0.0.0:8848` 常驻。

> shell 层文件归 frontend-dev（`index.html`/`styles/app.css`/`src/main.js`/`src/audit.js`/`smoke_test.js`/SVG 导出/服务）；
> 地图与角色渲染（`src/sprites.js`/`src/town.js`/`assets/`）归 art-director，改动对方文件前先对齐。

## 10. 无头渲染 CPU 优化（T68）

本机无 GPU，无头 Chromium 用 SwiftShader **软渲染 WebGL**，持续 rAF 会让 CPU 打满。

**前端 still 模式**：URL 加 `?still=1`（可叠加 `&round=N`）——
只渲一帧，**首帧后停掉 ticker/rAF**、跳过持续动效，把角色直接吸附到目标位（免逐帧平滑），
渲染完成后置 `window.__RENDER_READY__=true` 且 `<html data-render-ready="1">`。
**播放 / 交互时观感完全不变**（非 still 走原路径）。后台标签页（`document.hidden`）自动停 rAF 降闲置 CPU。

**截图脚本**：`bash frontend/tools/screenshot.sh [out.png] [log] [round] [WxH] [extraQuery]`
- 自动 `&still=1`；`timeout 60` 兜底；`flock` **串行**（禁并发多浏览器）；退出 `trap` 清理残留 headless 进程；
- flags：`--headless=new --no-sandbox --disable-gpu --hide-scrollbars --enable-unsafe-swiftshader --force-device-scale-factor=1`；输出写 `$HOME`。
- 拍动画：`STILL=0 bash ...`。

**实测证据**（同 flags、同 `round=12`、同 1500×950，仅 still 不同；`/usr/bin/time` + `ps` 采样）：

| 指标 | 优化前(still=0) | 优化后(still=1) | 变化 |
|---|---|---|---|
| 墙钟耗时 | 7.44 s | **2.46 s** | **≈3.0× 更快** |
| 采样平均 CPU | 780 % | **441 %** | ≈1.8× 更低 |
| 采样峰值 CPU | 1269 % | 838 % | 更低 |
| 输出图逐像素差异 | — | — | **0.005 %**（品质未降） |

**光照与 shell 对齐**：`main.js` 按 `round → slot` 调 `town.setLighting('day'|'dusk'|'night')`（art-director 提供，含夜间窗光/灯火）；夜间实测亮度 68.9 vs 白天 97.8（明显变暗）。

**验收**：`node frontend/tools/smoke_test.js` 含 `[D]` 段断言（still/脚本 flags/ready 标志/后台停 rAF/setLighting 调用）全绿；`0.0.0.0:8848` 常驻。

## 11. 实时跟随模式（T75）

- **运行器**：`python frontend/tools/live_run.py --n 6 --rounds 300 --throttle 1.2`
  —— 真内核（`orchestration.build_world` + `engine.run_round`）**节流**推进，每回合把新增事件**追加**到
  `sample/live/live.jsonl` 并更新 `sample/live/latest_state.json`（零网络，离线 MockProvider）。
- **前端**：`?live=sample/live/live.jsonl&follow=1` —— ~600ms 轮询、平滑推进到最新；
  顶栏 **● LIVE + round 计数 + 跟随/暂停**；手动步进自动暂停跟随。
- **确定性不受影响**：`python -m engine verify --log frontend/sample/live/live.jsonl` → PASS。
- 报告：`sample/T75-live-report.md`；跟随截图 `sample/live_follow_{a,b}.png`。

## 11. 观测台重做（T77：游戏化 + 因果 + 人物故事）

按 `v1.2/obs-console-ux-spec.md`（T76）实现，右抽屉「观测台」分两页：

**📜 编年史**：事件流**人话卡**（图标 + 族色 + 回合分组 + 层级筛选 + 搜索），每行可展开
「**为什么**」（事实/推断分色；`cause_event_seq` 等可点 **跳回合并高亮源事件**）+「查看原始事件」（审计模式另显原始 payload）。图标优先用 `EVENT_STYLE.icon` ↔ `HITTPSprites.ICON_ATLAS`
像素图集（单一真源），缺图退化为「族色圆点 + 单字符」（**禁用 emoji**）。

**💬 社交**：① 概览计数；② **一对一私聊 `MSG_DM` 原话**（谁→谁 + 内容，可点开两人关系）；
③ **谈判线程 `OFFER_*`**（发起→还价/婉拒/结果）；④ **共处/关系变化**（"在 X 共处 N 次" / "好感 +4（因交谈）"）；
⑤ 明确标注**一对一=有 / 公开群聊=未实现**（如实，不假装）；⑥ 按**人物对聚合**（"A ↔ B：2 私聊 · 3 协商"）。

**👤 角色卡**（地图点人或点事件流名字=同一张卡）：人格背景（**五大人格/价值取向/技能/目标倾向/说话风格**，
字段**中文化** + 数值**档位**如"尽责性 82（很高）" + 括号内英文键对照 + 每个分区 `?` 说明）、金钱/负债、
需求条（中文 + 档位）、关系（`affinity/trust` −100~100、`respect/familiarity` 0~100，带 tooltip 含义）、
最近行为、**MSG 观点原文**、因果时间线（事实/推断）。术语口径对齐 `v1.2/glossary-ui-terms.md`。

> **方向说明**：`neuroticism` 统一展示为「**情绪稳定性 = 100 − 原始分**（越高越稳）」，不与原始分混用。

**演示参数**：`?audit=1` · `?tab=social` · `?agent=<id>` · `?place=<id>` · `?round=N` · `?still=1`。
**样张**（`sample/`）：`T77-console.png`、`T77-character.png`、`T77-social.png`。
**回归**：`smoke_test.js` 含 `[E]` 段（人话无 `undefined`/空引号、死亡含原因、图标图集钩子、因果跳转高亮、筛选栏、中文化映射、档位）。

> 注：`sample/tiny_social.jsonl` 是**UI 验证用的小夹具**（合成，非仿真数据），仅用于演示社交页。

> **C@N=20 样张备注（务必保留）**：`T77-{social,console,character}.png` 取自 **C@N=20 真 LLM 跑**
> （`v1.2/evidence/run_abl_C_N20.jsonl`，走 play 视图）。但该跑中 **`MSG_DM` 正文仍是模板措辞
> （`（寒暄）你好呀。`/`（低声）听说……`），非 LLM 生成**——社交页已**自动判定并如实标注**
> 「疑似模板（非 LLM 生成）」。真对话待 v2 接线（见 T81）后重出。

## 12. CI / 回归门禁（T107/T108）

两道门禁，**分离**（mock 门禁快、真渲染门禁稳）：

| 门禁 | 命令 | 作用 | 抓得到的坑 |
|---|---|---|---|
| ① 快速（无浏览器） | `node frontend/tools/smoke_test.js` | PIXI **mock** 下的回放/渲染/审计/SVG 断言 | 逻辑回归；**抓不到**真 Pixi 运行期错误（mock 的 `Sprite` 接受任意参数） |
| ② 真渲染 | `python frontend/tools/gate_render.py` | 真 Chromium/SwiftShader：无 `pageerror` + `_useLib===true` + `placeLayer===17` + `agentLayer≥1` | 「`new PIXI.Sprite(BaseTexture)` 抛异常 → `town.load()` 中止 → `placeLayer=0` → 画面空」这类**假绿** |

**一键（CI 用这个）**：`make ci` 或 `bash frontend/tools/ci_gate.sh`（缺服务会自动后台拉起 `serve.py`）。
（消歧 T280：`make ci`/`make gate` 在此指 **code/ 前端**门禁；仓根另有 `make gate`=术语+pytest。**想一次跑全部** → 到仓根 `make verify`；仅前端渲染门禁用 `make gate-front`。）

**退出码（严禁把「没跑」当「通过」）**：`0=PASS` · `1=FAIL` · `3=SKIP`（真渲染门禁依赖缺失，未执行，不算通过）。

**无 GPU 预算**：门禁走 **still 单帧模式**（`&still=1`，只渲一帧、不跑动画循环）。
实测（本机）：`smoke` ≈0.17s；`gate` ≈7.0s（wall 7.4s，CPU ≈2.4s，单核 ~32%，非满载）。

**反向验证（反假绿关键证据）**：
- 把 `EXPECTED_PLACES 17→99` → `GATE FAIL` → `CI GATE: FAIL`，**EXIT=1**；
- 把 `_useLib===true` 反转为 `false` → `GATE FAIL` → **EXIT=1**；
- 令 `playwright` 导入失败（模拟依赖缺失）→ `GATE SKIP` → `CI GATE: SKIP`，**EXIT=3**（不 PASS）。

> 回归守护心跳每 5 分钟跑 `ci_gate.sh`，**仅 FAIL 时**告警 art-director + leader；通过静默。

## 13. 事件卡放大（T113）

事件流每行的事件卡缩略图（`EVENT_CARDS` 单一真源，来自 `sprites.js`）支持**点击/键盘放大**，
放大后**四区可读**（插画区 / 机制标注区 / 木牌标签 / 图标徽章）——机制标注区即"哪里体现了事件"的答案
（如 `🪙40 − 🪙35 = 🪙5` 的稀缺溢价）。

- **样式归属**：缩略图/放大层样式全在 `styles/app.css`（`.ev-cardart-img` / `.ev-lightbox*`），**无内联堆样式**；
  放大尺度 `min(92vw, 900px)`（300px 源 ×3）。
- **键盘可达**：缩略图 `tabindex=0 role=button`，**Enter/Space 展开**；放大层 **Esc 关闭**；点遮罩空白处关闭（点图不关）。
- **演示/取证参数**：`?card=<slug>` 直接放大某张卡（如 `&card=scarcity-buy`），配合 `?round=` 让背景事件流同屏。
- **证据**：`v2/evidence/T113-card-scarcity-buy.png`、`T113-card-whispered-comm.png`
  （真实 C@N=20 回放：点击→放大→机制标注区可读）。
- **回归**：`smoke_test.js [E]` 增补卡接线/lightbox/样式归属断言；`make ci` 仍 PASS。

## 14. 默认首屏「游戏优先」（T119）

用户第 1 号标准是"打开好不好看"——**默认首屏应是"小镇"，不是"控制台"**。

- **默认折叠调试/回放控件**（`.debug-only`）：副标题、`week/day_type`、`1 tick=2h` 说明、顶栏「设置/审计」、
  步进按钮 ⏮◀▶⏭、`round-label`、速度、底部时间轴 —— 默认全部隐藏；由顶栏「⋯ 调试」按钮（或 `?debug=1`）**一键展开**。
- **默认只留"游戏"要素**：标题、时间（第X日 HH:MM（时段））、**「🏞 景观」按钮**（T116 交付通道）、**播放/暂停 + 进度**、类别图例、缩放控件。
- **审计能力不删**：展开「调试」后 `📊 审计`、设置、时间轴等原样可用。
- 证据：`v2/evidence/T119-firstscreen-default.png`（默认）、`T119-firstscreen-debug.png`（展开调试）。

**景观模式角色可辨性复核**：真·黑暗时段是 **round 45（00:00 夜）**（注意 round 60 实为 06:00 晨，非夜）。
landscape + 夜间时，小角色**对比不足、较难辨认**；根因主要是**夜间压暗**（去标签/去散点进一步减少了注意锚点），
角色的**接触影/描边在夜间偏弱**（属渲染层）。证据：`T119-landscape-night-r60.png`(=晨)、`T119-landscape-day-r45.png`(=夜)。

## 15. 截图等就绪（T121：防"假黑图 / false negative"）

**已知坑**：**大日志（≥10MB）+ still 单帧**下，若在页面就绪前截图 → 产出**整列发黑的假图**；
根因是**截图时序**，**不是渲染 bug**。这是**"假红"**（false negative），与"假绿"同族——证据管线不可靠会让判断两头出错。

**修正**：截图**不靠固定 sleep**，改用**就绪信号**：
- `tools/shot.py`：Playwright 打开页面 → `wait_for_function(window.__RENDER_READY__===true || data-render-ready==='1')`
  （`main.js` 在**素材加载完 + 首帧渲染后**置位）→ 再 `screenshot`；**等不到即超时 → 非零退出（不产黑图）**；
  页面 `pageerror` → 非零。退出码 `0=OK / 1=FAIL / 3=SKIP(无 playwright)`。
- `tools/screenshot.sh`：委托 `shot.py`；保留 `flock` 串行、`pkill` 清理；`SHOT_TIMEOUT`(默认 90s) 总超时。

**自证**（10.6MB `run_b2_n20_week.play.jsonl`，**两次连跑**，无需人工 sleep）：
- run1/run2 均 `SHOT OK`，`mean_brightness=69.2`（**非黑**），**sha256 完全相同**（可复现）；各 ~3.7s。
  证据：`v2/evidence/T121-biglog-run1.png`、`T121-biglog-run2.png`。
- 超时路径：`sample/__does_not_exist__.jsonl` + `SHOT_TIMEOUT=8` → `SHOT FAIL … 超时`、**EXIT=1**、**未产出任何图**。

> **口径（T121 补）**：`shot.py` 现在**自己计算并打印** `mean_brightness`，**唯一定义 = 整帧灰度均值**
> （`0.299R+0.587G+0.114B`，ITU-R BT.601，0–255，**黑图判据 <8**）。同一大日志帧实测 **71.6**——
> 与 leader 独立复算一致（此前 69.2 是"RGB 三通道各自均值再平均"的**同名不同义**算法，已废弃）。
> `smoke [D]` 增补断言：`shot.py` 必须定义该口径。

> **T118 门控映射（事件卡）**：`EVENT_CARDS` 不再无条件 `type→slug`——机械事件
> （`RELATION_CHANGE/NEED_UPDATE/PLACE_MOVE/ACTIVITY_*/LLM_JUDGMENT`）**默认不配卡**；
> 卡片改由 **活动 `template`**（`EVENT_CARDS_BY_TEMPLATE`）或**语义条件**（`audit.js::eventCardSlug`：
> `TRANSFER{reason=gift}`、`DEPOSIT/WITHDRAW`、`STATE_CHANGE{to=exhausted}`、
> `MARKET_TRADE{reason=scarce_buy ∨ scarcity_index≥θ}`、`MSG_DM{visibility=private}`）驱动。
> 依 `v2/evidence/event_card_mapping_revised.json`。**本实现按 §2 的字面"或"取并集**。

> **第 7 道门禁（T123）：JS≡Python 门控对拍**。事件卡门控在**两处**实现：`audit.js::eventCardSlug`（前端）
> 与 `obs.recount_cards.gated_slug`（统计）；**任何一边改映射/门控即静默分叉**。`smoke_test [E]` 现将
> 二者在 **35 个代表性事件**上**逐例对拍**（无条件类型/全量 template/语义条件/机械事件/`template=rel_accept` 反造假），
> **不一致即红**。反向验证：把 JS `SCARCITY_THETA` 改坏 → `FAIL（JS=- PY=scarcity-buy）`；还原 → PASS。

## 16. 游戏质感 G 清单落地（T240）

G-1..G-14 可执行清单见 `v2/refs/gamefeel-executable-tasks-T240.md`。本任务**先落地 3 项 P0**（均只读日志、无前置资产）：
- **G-8 剧情卡 · 因果链**：事件行「⌄ 为什么」展开为**因果链**（上游事件 `#seq` → ↓ → 本条），**事实分色、链节可点溯源**（复用 `_focusSeq` 跳转）。实现：`audit.js::_detail` + `_eventsBySeq`。
- **G-9 小镇周报**：观测台新增「📰 周报」页——`第 N 周` K 事实（存活/货币/本周事件/死亡复活，**逐字取日志**）+ 本周纪事高光 + 镇民原话引用（**未改写**）+ 若日志含 `NARRATIVE` 则作正文。实现：`audit.js::renderWeekly`。
- **G-14 关系图**：角色卡内**节点-边关系图**（中心「我」，边粗=好感强度、绿正/红负；点节点切换角色卡）。实现：`main.js::relGraphSVG`。

演示参数：`?tab=weekly` / `?audit=1&expand=<seq>` / `?agent=<id>`。证据：`v2/evidence/T240-{before,after}-*.png`。**修复**：`.pane{display:flex}` 会盖过 `[hidden]`，致分页旧面板残留 → 加 `.pane[hidden]{display:none!important}`。`make ci` PASS。

## 16. R9「沉浸/质感」可复算口径（进 CI）

`tools/immersion_metrics.js` 计算**四条确定性子指标**（只读日志/渲染坐标），已接入 `ci_gate.sh` **第 3 步**：

| 指标 | 定义 | 阈值 |
|---|---|---|
| `activity_ratio` | 产生可见画面反馈的事件 / 总事件 | ≥0.5 |
| `idle_round_ratio` | 零变化回合 / 总回合 | ≤0.2 |
| `causal_coverage` | 叙事级事件中"能展开为什么(reason/cause/cause_event_seq)"的比例 | ≥0.8 |
| `label_overlap_rate` | default 视图下场所标签包围盒与**其它**建筑相交占比（渲染坐标近似） | ≤0.05 |

**★ 成立条件（变了要重校）**：`view=default`（仅场所名，无 NPC ID）· **`scale=1` 未缩放** · 世界 960×720；
CI 校准日志 = `sample/run_c_n20.play.jsonl`（C@N=20 真 LLM；实测 activity 0.7325 / idle 0 / causal 0.9180 / overlap 0）。
`label_overlap` 为**确定性近似**（非像素级测量）：视图/尺寸/人口/标签口径变化 → 阈值须重校。

**反向验证**：`IMMERSION_LOG=sample/demo_run.jsonl make ci` → `IMMERSION FAIL(3)` → `CI GATE: FAIL`；默认日志 → `PASS`。

> 人工侧（B 部分）：3 分钟盲测量表（5 人、1–5 分、三题、均≥4 且无人≤2）——见 `v2/evidence/T259-render-richness.md` §3。
