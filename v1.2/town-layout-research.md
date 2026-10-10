# 青溪镇布局重做方案（参考 Stardew Valley Pelican Town）

> 任务：T70-town-layout-research　｜　作者：visual-researcher　｜　日期：2026-10-10
> 面向：art-director（落地排布）、frontend-dev（渲染口径）、leader（转用户）
> 硬约束遵守：**只读**——不改前端渲染代码、**不碰 `engine/` 与 `config/`**；本文件仅为**方案**。
> 示意草图：`social-experiment/v1.2/evidence/layout/qingxi_layout_proposal.png`

---

## 0. 结论摘要

用户反馈「三层同心环布局不对」属实且**根因在拓扑语义层**：`config/topology.json` 用 `ring_rule` 把场所分成 ring0=hub(plaza)、ring1=环绕中心、ring2=外围带、ring3=最外围，当前显示坐标正是按环摆放 → 天然人工感。

**方案**：把**展示层**从「同心环」改为 Stardew 式**有机街区**——
- **一条东西主街**贯通全镇（西端跨**石桥**入镇）；
- **一条南北中轴**做仪式轴：**市政厅（北·对景）→ 中央广场 → 城门（南·端景）**；
- **沿街分区**：商业沿主街、居住走南巷、生产在东缘、地标在北脊、农田在西北郊野、城门在南端；
- **三种不同边界**（西河/北林/东郊）替代均匀树环。

**只能动展示层**：17 个 `place_id` 与集合、`travel_ticks` 语义（ring 规则）**均不变**（详见 §5）。

---

## 1. 在线调研：Pelican Town 与同类像素小镇的布局原则

> 主要一手来源：**Stardew Valley Wiki — Pelican Town** https://stardewvalleywiki.com/Pelican_Town
> 辅助：**Cindersap Forest** https://stardewvalleywiki.com/Cindersap_Forest ｜**The Mountain** https://stardewvalleywiki.com/The_Mountain ｜**The Beach** https://stardewvalleywiki.com/The_Beach
> 本项目渲染/素材先例：a16z **AI Town** https://github.com/a16z-infra/ai-town

Wiki 记载的 Pelican Town 地理（可直接提炼为原则）：
- **入口是"多向且不对称"的**：西北入口接 Bus Stop 与农场；西南接 Cindersap Forest；**正南是海滩**；北接 Mountain（木工店/矿洞/铁路）。→ **原则 A：多向、不对称的出入口，城镇"被地形切过"而非被围成整圆。**
- **关键地点沿道路成带**：Pierre's General Store、Clinic、Community Center、Museum、Blacksmith、JojaMart、The Stardrop Saloon、Bookseller。→ **原则 B：功能建筑沿街/沿带排布，不是按半径均匀撒点。**
- **河/桥穿过镇区**（river flowing through town；fountain 在 Community Center 左侧）。→ **原则 C：水体+桥作"缝合线"与地标，不是背景装饰。**
- **居住是"门牌式"沿街**（1 River Road / 1 & 2 Willow Lane、Trailer、Mayor's Manor）。→ **原则 D：住宅沿街成排（street-front），不是成环。**

**提炼出的 6 条布局原则**（本方案的判据）：

| # | 原则 | 反面（我们现状） |
|---|---|---|
| P1 | **有机街区**：不规则街区、大小不一 | 同心环、等距 |
| P2 | **主干道 + 枝状支路**：一条主街贯通 + 死胡同/错位支路 | 规则网格/放射 |
| P3 | **功能分区**：商业带 / 生产带 / 居住沿街 / 河岸农田 / 公共地标各占其位 | 按 ring 混排 |
| P4 | **建筑贴路**：门朝最近道路，立面沿街 | 均匀散开 |
| P5 | **地标锚点 + 对景**：广场/喷泉/市政厅/教堂落在轴线端景 | 中心一个大圆盘 |
| P6 | **密度渐变 + 差异化边界**：主街密→广场疏→外围疏；边界用林带/河/山**各不相同** | 四周均匀树环 |

---

## 2. 现状诊断（为什么像"同心环"）

`topology.json` 的 `ring_rule`: `ring0=hub(plaza); ring1=环绕中心; ring2=外围带; ring3=最外围`；`travel_rule`: `同 ring=1; 相邻 ring=2; 其余=3; gate↔plaza=3`。
当前 ring 归属：

| ring | 场所 |
|---|---|
| ring0 | plaza |
| ring1 | market, town_hall, cafe, park |
| ring2 | residence, workshop, kitchen, clinic, school, office, bank, library, community_center, hall |
| ring3 | farm, gate |

当前显示坐标**正是按环摆放**（plaza 居中，其余按环均匀分布）→ 于是画面呈「中心广场 + 一圈建筑 + 外圈」的同心环，人工感强。

> 有意思的是：**ring 归属本身并不完全是坏分区**——ring1（market/town_hall/cafe/park）≈「公共核心」，ring3（farm/gate）≈「郊野边缘」。方案会**保留这种"语义上的核心/边缘"**，只把它从"环"改写成"有机街区"。

---

## 3. 「青溪镇版」布局提案

### 3.1 骨架（960×720，1 tile = 32px）
- **主街（东西贯通）**：`y ≈ 420`，宽 **3 tile**（y 398–442）；**西起石桥**（桥跨西侧河流，x≈96–120）→ **东至出镇口**（x≈800）。这是**唯一贯通道**。
- **中轴（南北仪式轴）**：`x ≈ 470`，宽 **2–3 tile**（x 448–492）；**北起市政厅（y≈250）→ 经中央广场（y≈420）→ 南至城门（y≈655）**。
- **北巷**：`y ≈ 250`，连接礼堂↔市政厅↔工坊区（x 330→780）。
- **南巷**：`y ≈ 560`，连接图书馆↔住宅↔社区中心↔学校（x 230→650）。
- **支路（枝状/错位，非对称）**：公园→主街(x≈300)、工坊→主街(x≈760)、诊所→主街(x≈740)；北巷与南巷**在 x 上错开**（不做规则网格）。

### 3.2 分区表（含坐标建议）

| 分区 | 场所（place_id / 中文） | 建议坐标 (x,y) | 与主街/中轴关系 |
|---|---|---|---|
| **镇中心 / 公共核心**（ring0+1） | plaza 中央广场 | **470, 420** | 主街与中轴交点处的**街道加宽广场**（喷泉） |
| | market 市集 | 560, 420 | 主街北侧，广场东 |
| | cafe 咖啡馆 | 380, 460 | 主街南侧，广场西 |
| | park 公园 | 300, 400 | 主街北侧·临河（河畔口袋公园） |
| **主街商业带（东段）** | bank 银行 | 630, 460 | 主街南侧 |
| | office 事务所 | 720, 420 | 主街东段（近出镇口） |
| **东缘 生产带** | workshop 工坊 | 760, 300 | 东北外缘，支路接主街 |
| | kitchen 面包房 | 695, 335 | 与工坊相邻（原料→加工） |
| **北脊 地标带** | town_hall 市政厅 | **470, 250** | **中轴北端·对景焦点** |
| | hall 礼堂 | 360, 250 | 北巷西侧 |
| **南巷 居住 + 公共** | residence 住宅 | 360, 560 | 南巷（**沿街门牌式**，非环） |
| | community_center 社区中心 | 470, 570 | 南巷·中轴旁 |
| | library 图书馆 | 250, 520 | 西南，邻公园/住宅 |
| | school 学校 | 620, 570 | 东南，邻住宅 |
| **东缘 服务** | clinic 诊所 | 760, 520 | 东南外缘，支路接主街 |
| **西北 河岸农田**（ring3） | farm 农场 | 180, 170 | 河流西/北岸郊野（原料产地） |
| **南端 城门**（ring3） | gate 城门 | **470, 655** | **中轴南端·端景** |

### 3.3 地标与对景（P5）
- **仪式轴**：`市政厅(北) → 中央广场 → 城门(南)`，三点共线于 `x≈470`。从城门北望可见广场喷泉与市政厅——**一条街讲完"镇的身份"**。
- **西端景**：主街西端**石桥**（跨河入镇的第一眼）。
- **每街有尽端**：主街东端→出镇口（可放一块镇牌/牌坊）；北巷两端接礼堂/工坊（都有建筑收口），**不出现"街通向空白"**。

### 3.4 边界（P6，防同心环的关键）
- **西**：河流（竖向水体）+ **石桥**缝合；
- **北**：**稀疏林带**（带一处**开口**，让中轴对景露出远景，别做成墙）；
- **东**：主街**出镇接郊野**（生产带在此，疏朗）；
- **南**：居住→**城门出镇**。
> **刻意让四向边界形态不同**；至少一处林带**明显变稀/断开**，打破"均匀树环"。

### 3.5 密度渐变（P6）
`主街（密）→ 广场（疏·开放节点）→ 巷子（次密）→ 外围农田/郊野（疏）`。广场**至少一侧留 2–3 tile 空场/口袋绿地**，建筑**立面不共线**（setback 0/1/2 tile 交错）。

### 3.6 材质 / 朝向（P4）
- **主街**：cobble / 压实土（可加浅色路缘）；**支路巷子**：dirt path；**广场**：第三种石板铺装（与道路区分）。
- **门一律朝向最近道路**；临主街建筑**正立面朝主街**。

> 示意草图见 `evidence/layout/qingxi_layout_proposal.png`（960×720，含分区与坐标）。

---

## 4. 相邻关系（任务显式要求）
- **商业–政务带**：市集 + 银行（同一主街段）+ 市政厅（中轴北端对景）→ 互为步行可达；市集紧贴广场。
- **生产带**：工坊 + 面包房**相邻**于东缘（原料→加工）；**农场**在西北郊野供料，经主街/西桥运入。
  - *可选项*：若要求"农场–面粉/面包"严格相邻，可把面包房移到农场东南侧（约 260,230）；但会牺牲"面包房贴主街的商业性"。**建议保持主方案**（面包房在东缘生产带）。
- **居住沿街**：住宅/社区中心/图书馆/学校沿**南巷成排**（门朝巷），非成环。

---

## 5. 语义约束：哪些能动 / 哪些不能动

| | 可动（**展示层**） | 不可动（**语义/引擎层**） |
|---|---|---|
| 对象 | place 的**显示坐标 x/y**、道路与铺装、装饰密度与摆放、建筑朝向与剪影、昼夜/缩放/HUD | 17 个 `place_id` 与**集合**；`config/topology.json` 的 **`travel_ticks` 语义**（ring 规则）；`engine/` 与 `config/` 一切 |
| 归属 | frontend-dev / art-director | 引擎已冻结，任何人不得改 |

**⚠️ 一致性提示（重要，需与用户对齐口径）**：
`travel_ticks` 由 **ring** 决定（同 ring=1、相邻 ring=2、其余=3），**与显示坐标无关**。因此新布局里"**看起来相邻**"的两点，若属于**不同 ring**，其**语义通行成本仍是 2–3 tick**。典型两处：
1. `gate(南端)` 看起来正对 `plaza`，但语义 `gate↔plaza = 3 tick`（引擎冻结值）；
2. ring2 的 10 个场所被拆到全城各分区，但它们之间**恒为 1 tick**（同 ring）。

**建议**：**接受该 trade-off**——`travel_ticks` 是"语义成本"（Agent 行为用），展示是"美术层"（给人看）；两者本就是不同度量。真要"视觉≈成本"，唯一办法是保留环结构（正是要去掉的）。
**软优化**：本方案已尽量让同 ring 者**在展示上也相对成簇**——ring1 的 4 个（market/town_hall/cafe/park）全部围绕广场；ring3 的 2 个（farm/gate）都在外缘。可接受。

### 5.1 裁定（leader，2026-10-10）：**接受该 trade-off，但必须"显式呈现"**
- **定性确认**：显示布局 与 语义通行成本 是**两个不同的度量**。`travel_ticks` 由 ring 决定、**引擎已冻结，不改**（本方案只动展示层）。
- **前端呈现要求**（与 frontend-dev 协同）：为避免用户把"看起来近、实际成本高"误解为 bug，前端需在**点击 / 悬停场所（或角色）时，显式展示"语义通行 tick"**——例如在详情面板/悬浮提示里显示「**从<当前参照点>到这里：N tick**」（N 取自冻结的 `travel_ticks`），把**展示距离**与**语义成本**两个度量**同时摆出来**。
- **定性**：这不是 bug，是**已接受的 trade-off**；上条呈现方式即其**官方解释路径**。（参考实现位置：前端详情/悬浮层；数据源：`config/topology.json` 的 `travel_ticks`，**只读引用，不修改**。）

---

## 6. 交接
- **art-director**：按 §3.2 坐标表重排前端展示 x/y（**保持 place_id 与集合不变**）；§3.4/§3.5 是"去同心环"的关键；§3.3 保证对景轴。
- **frontend-dev**：`travel_ticks`、`topology.json` 一律不动；只改展示层拓扑/坐标与渲染。
- **leader**：§0 与 §5 的 trade-off 可直接与用户对齐口径。

## 附：来源清单
- Stardew Valley Wiki — Pelican Town：https://stardewvalleywiki.com/Pelican_Town
- Stardew Valley Wiki — Cindersap Forest：https://stardewvalleywiki.com/Cindersap_Forest
- Stardew Valley Wiki — The Mountain：https://stardewvalleywiki.com/The_Mountain
- Stardew Valley Wiki — The Beach：https://stardewvalleywiki.com/The_Beach
- a16z AI Town（本项目渲染/素材先例）：https://github.com/a16z-infra/ai-town
