# v2/refs/worldbook-v1 · 青溪镇世界设定书 v1（作者化「世界层」schema）

> 文档类型：世界设定书（**设计层**，不改代码）｜ 作者：design-synthesizer（方案汇总与成稿专家）
> 状态：v1（验证床=青溪镇）；机器可读见 `worldbook-v1.json`；一致性检查见 `tools/check_worldbook.py`
> 用户已确认读法：**「世界层我们定、社会层只给手段不写死」—— 作者化的活世界。**
> 上游/关联：`v2/00-roadmap.md §0`（两层分离）、`v2/refs/world-director-design.md`（导演设计）、`v2/refs/world-event-mechanisms.md`（**机制表唯一权威** WM-01..13）、`code/config/*.json`

---

## 0. 定位：世界层 vs 社会层（与路线图 §0.3 同源）

| 层 | 谁定 | 内容 | 本文交付 |
|---|---|---|---|
| **世界层** | **我们（作者）** | 地理、背景故事、初始居民、宏观事件、**世界导演的介入** | 本设定书（可配置 schema + 青溪镇实装） |
| **社会层** | **AI 涌现** | 货币/价格/工资/税/制度/规范 | **只给手段**（A 物理层原语 + 工具箱），**不预设数值** |

> 与 `v2/00-roadmap §0.3` 的路线顺序铁律一致：**先底座与工具（A）→ 再看涌现（B）→ 再谈调参（C）**。世界层只铺「舞台与初始情境」，**不规定结局**。

**红线（三条，贯穿全篇）**：① 世界层只给情境、**不给结局**；② 社会层数值（价格/工资/税率/是否铸币）**一律不预设**；③ 世界导演每次介入**可审计（显式事件）、可消融（独立开关+剂量）、不改过去（只影响未来）**。

---

## 1. 世界层 schema（可配置，为「异世界」留接口）

> `worldbook-v1.json` 顶层字段即 schema。换世界观 = 替换本文件 + 其引用的 config，**不改引擎、不改社会层**。

| 字段 | 含义 | 可替换（异世界） |
|---|---|---|
| `world_id` / `display_name` | 世界标识 / 展示名 | ✅ |
| `status` / `status_note` | 状态（当前=验证床） | ✅ |
| `layers` | 两层归属声明（world/social） | ⛔（结构不变） |
| `background` | 背景故事（自由文本） | ✅ |
| `geography.places_ref` / `topology_ref` | 地理（场所/拓扑）**引用 config** | ✅ |
| `residents.personas_ref` | 初始居民**引用 config** | ✅ |
| `macro_events.mechanism_table_ref` / `director_config_ref` | 宏观事件机制表 + 导演配置**引用** | ✅ |
| `director.principles` / `dose_curves` / `redlines` | 导演介入原则与剂量档 | 结构不变，取值可调 |
| `configurability.swap_points` / `invariants` | 可替换点 / 不变量 | — |
| `social_layer_policy` | 社会层红线（**preset_values=false**） | ⛔ |

**不变量（换世界也必须成立）**：世界层只定情境不定结局；社会层数值不预设；每次介入可审计/可消融/不改过去。

---

## 2. 青溪镇世界设定（当前验证床）

### 2.1 背景（author）
> 群山环抱的小镇「青溪」，一条溪水穿镇而过。镇民世代以农、工、商、学、医相济；市集逢集而开，礼堂办节庆。镇子在城门口与外界相通，偶有外来者与物资。

### 2.2 地理（17 场所；引用 `code/config/places.json` + `topology.json`）
`residence 住宅 · farm 农场 · workshop 工坊 · kitchen 面包房 · clinic 诊所 · school 学校 · office 事务所 · market 市集 · bank 银行 · plaza 中央广场 · town_hall 市政厅 · library 图书馆 · community_center 社区中心 · cafe 咖啡馆 · park 公园 · hall 礼堂 · gate 城门`。
- 拓扑：中心–外围同心环，`travel_ticks ∈ {1,2,3}`（`topology.json` 常数矩阵，入 `engine_version` 指纹）。

### 2.3 初始居民（20 位；引用 `code/config/personas.json`）
| 角色 | 居民 |
|---|---|
| 农 `farmer` | 老周(P001) · 阿禾(P003) · 桂婶(P012) |
| 工匠 `craftsman` | 老石(P002) · 铁头(P013) · 巧儿(P014) |
| 厨 `cook` | 秀娘(P004) · 五味(P015) |
| 医护 `healer` | 陈医(P005) |
| 教师 `teacher` | 方老师(P006) · 书言(P017) |
| 商人 `merchant` | 阿林(P007) · 兰姐(P016) |
| 公职 `public_servant` | 周公文(P008) |
| 银行 `banker` | 金先生(P009) |
| 艺人 `artist` | 月牙(P010) · 弦歌(P018) |
| 学生/无业 | 小满(P011) · 石头(P019) · 阿散(P020) |

> 说明：世界层只勾勒**初始居民与角色分布**；其人格细节（大五/价值观/技能/背景）由 `personas.json` 承载，**社会层角色关系与经济地位不预设**。

### 2.4 宏观事件清单（机制表权威 = `world-event-mechanisms.md`）
世界层可产生的**宏观情境**（**只给情境、不给结局**）。下表为「世界设定书视角」的开关状态（当前 `world_director.json`，`dose_curve=conservative`）：

| 机制（config_key） | kind | 当前 | 机制表 ID | 名称 |
|---|---|---|---|---|
| `wd.festival` | festival | ✅ on | WM-02 | 节庆/集市/大型活动 |
| `wd.edict` | edict | ✅ on | （未并入 WM 表） | 政令/公共公告 |
| `wd.tension` | tension | ✅ on | WM-07 | 紧张升级（制造 stakes） |
| `wd.visitor` | visitor | ⬜ off | WM-12 | 外来者/访客 |
| `wd.supply_shock` | supply_shock | ⬜ off | WM-05 | 供给冲击 |
| `wd.disaster` | disaster | ⬜ off | WM-10 | 灾害 |
| `wd.epidemic` | epidemic | ⬜ off | WM-11 | 疫病 |
| `wd.public_works` | public_works | ⬜ off | WM-04 | 公共工程/协作目标 |
| `wd.season` | season | ⬜ off | WM-01 | 世界节律/季节 |
| `wd.mass_event` | mass_event | ⬜ off | WM-13 | 大规模外来事件 |

- **机制表独有（config 尚未开列）**：`WM-03 opportunity`、`WM-06 scarcity`、`WM-08 conflict_gate`、`WM-09 incident`（**待对齐，非矛盾**）。

### 2.5 世界导演（World Director）
- **定位**：世界层的**调度者/策略**（何时、下什么指令、多大剂量），产 `WORLD_DIRECTIVE`（意图）→ 经内核校验封 `WORLD_GROUP_EVENT`（事实）。
- **与米哈游「AI 导演」的区别**：他们「导玩家体验」（调叙事节奏与分支）；我们「**导世界情境**」（造宏观事件，**不碰叙事层**，每次出手可审计/可消融/不改过去）。
- 详见 `v2/refs/world-director-design.md`、实现见 `v2/t239-world-director-impl.md`。

---

## 3. 世界导演介入原则与剂量档

### 3.1 三条保底（**本设计的宪法**，每次介入必须同时满足）
| # | 原则 | 含义 | 机器可校验 |
|---|---|---|---|
| **(a)** | **显式事件** | 每次介入落 `WORLD_DIRECTIVE`/`WORLD_GROUP_EVENT`，带 `directed=true` | 有 `directive_ref` 溯源 |
| **(b)** | **可消融** | 每机制**独立开关 + 剂量**；关闭即归零，可对照（置换检验） | `Ω={机制×开关×剂量}` |
| **(c)** | **不改过去** | 只影响 `t≥now` 的未来情境，**绝不篡改已发生事实** | 只对未来落事件 |

> 一句话：**可以「导演未来」，不可以「篡改过去」，也不能「隐形出手」**。

### 3.2 剂量档（dose_curve）
| 档 | 含义 | 典型剂量 | 用途 |
|---|---|---|---|
| `conservative` | 最小剂量（环境级） | 低概率/小规模/短时长 | **默认**（安全值） |
| `moderate` | 中剂量 | 中概率/规模 | 观察中等扰动响应 |
| `aggressive` | 灾难级（**默认 OFF**） | 高剂量/全局 | 最强故事发生器；启用须 Leader 明示，且须能**逐 Agent 事后复算影响** |

**剂量语义**：剂量=**强度缩放**（规模/时长/幅度/概率），**不改变可消融性**；剂量 0 ≡ 关闭。

### 3.3 介入红线（世界层不得越界到社会层）
1. 世界导演**不碰叙事层**（叙事机只读，H-2 不破）；
2. 政令**只给「公共情境」**，**不得写死税率/价格/工资**；
3. 供给冲击**只改供给量**，**不写价格**；
4. 紧张升级**只制造 stakes**，**不指定对手、不指定胜负**；
5. `conflict_gate` **只降门槛/给可见度**，触发权完全在 Agent；
6. 灾害/大规模事件**默认 OFF**，且须能逐 Agent 复算影响。

---

## 4. 社会层：只给手段，不写死（红线）

- **世界层不预设**：`price`（价格）、`wage`（工资）、`tax_rate`（税率）、`mint_rule`（铸币规则）、`employment_wage`（雇佣工资）——见 `worldbook-v1.json → social_layer_policy.forbidden_presets`，`preset_values=false`。
- 这些由 **B 制度层涌现**：AI 通过对话/协商/组织自造（`v2/00-roadmap §3 P2`、`v2/01 §3`、`v2/04-exchange-and-contracts.md`）。
- 世界层仅提供**能被用来造制度的原语**（A 物理层）：生产/结算/契约底座/公开发声/组织。

---

## 5. 一致性检查（机检，`tools/check_worldbook.py`）

**命令**：`python v2/refs/tools/check_worldbook.py --root .`（退出码 0=通过）

**实测输出**（2026-10-12）：
```
  OK  [places] OK (17 场所一致)
  OK  [residents] OK (20 居民一致)
  OK  [mechanisms] OK (10 机制键一致)
  OK  [WM 对齐] 机制表独有(未在 config): ['WM-03 opportunity', 'WM-06 scarcity', 'WM-08 conflict_gate', 'WM-09 incident']
  OK  [WM 对齐] config 独有(未并入 WM 表): ['wd.edict']  ← 待对齐，非矛盾
  OK  [social_layer] OK：不预设数值；红线清单=['price', 'wage', 'tax_rate', 'mint_rule', 'employment_wage']
结果：PASS（全部硬检查通过）
```
**硬检查项**：① 场所集合 ② 居民集合 ③ 机制键与 enabled ④ 社会层不预设数值。
**待对齐项（提示，非失败）**：机制表 WM 与 `world_director.json` 的机制集合存在**双向差集**（`wd.edict` 未并入 WM 表；`WM-03/06/08/09` 未在 config 开列）——建议由机制表权威方（narrative-designer）与 config 方对齐，**本文不改写**。

---

## 6. 可配置（「异世界」后置）

- **下一步选项**：世界设定**可配置**（由本 schema 生成新世界）；**异世界后置，先把青溪镇跑通**。
- **替换点**（`configurability.swap_points`）：`geography.places_ref`/`topology_ref`、`residents.personas_ref`、`macro_events.director_config_ref`、`background`。
- **不变量**（换世界必须保持）：世界层只定情境不定结局、社会层数值不预设、每次介入可审计/可消融/不改过去。

---

## 7. 索引

| 主题 | 路径 |
|---|---|
| 机器可读世界设定书 | `v2/refs/worldbook-v1.json` |
| 一致性检查器 | `v2/refs/tools/check_worldbook.py` |
| 世界导演设计 | `v2/refs/world-director-design.md` |
| **世界事件机制表（权威）** | `v2/refs/world-event-mechanisms.md` |
| 故事/事件引擎 | `v2/refs/story-and-event-engine.md` |
| 导演实现 | `v2/t239-world-director-impl.md`、`code/config/world_director.json` |
| 路线图（两层分离） | `v2/00-roadmap.md §0` |

---

*（青溪镇世界设定书 v1 — design-synthesizer）*
