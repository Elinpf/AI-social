# Python 插件化架构规范 v1（按 Fork A=B）+ 最小骨架

> 作者：solution-architect ｜ 任务：T214-python-plugin-architecture ｜ 依据：用户 2026-10-12 拍板 **Fork A=B（保持 Python，自建插件化）**；T201/T206 已证 Cordis 五概念是好设计。
> 状态：**v1 规范**。**未改动 `code/` 语义，未落地 `.importlinter`**（边界契约以「§8 建议」形式提出，按 Leader 规矩**待单一修改者排队落地**）。
> 骨架位置：**项目根 `plugin-skeleton/`（独立于 `code/`）** —— 因 T211 正在移动 `code/` 目录，按 Leader 指示骨架不落 `code/`。
> 标注：**【已定】**=可开工；**【建议】**=需 Leader 排队后落地；**【未验证】**=未实测。

---

## 0. TL;DR

1. **插件边界不重划**：保留现有 8 个包与 8 条 import 契约；「插件」是**挂在 `Context` 上的可逆单元**，不是新的顶层包。→ **迁移代价≈0**，老代码不动。
2. **借 Cordis 五概念**，用 **~330 行零依赖 Python** 落地（`plugin-skeleton/plugin/`，11 条测试全过）：可逆副作用 / 服务注入（含消失自愈）/ 类型化事件+waterfall / 配置组合 / 清单指纹。
3. **渐进接入**：先落 `plugin/` 运行时（零影响）→ 逐个把**叶子能力**包成插件（首个建议 = LLM provider）→ 每步门禁绿、可回退。
4. **可复用边界**：只有「依赖 stdlib（+ `contracts` 纯协议）」的插件才可跨项目复用；经济/生命周期/社会观测/青溪镇世界是**项目专属**，不抽出。

---

## 1. 插件边界怎么划（Q1）

### 1.1 【已定】不重划顶层包 —— 保留现有 8 包 + 8 契约

| 候选 | 说明 | 迁移代价 | 风险 | 结论 |
|---|---|---|---|---|
| **A. 保留现有 `contracts/engine/life/freeze/obs/narrative/orchestration`（+frontend），新增**薄**`plugin/` 运行时** | 「插件」= 运行时概念，不是顶层包；既有 8 契约不动 | **≈0**（纯新增） | 低 | ✅ **采纳** |
| B. 按「能力/领域」重划（如 `world/ agents/ economy/ observation/`） | 顶层大改 | **高**（要重写 8 条 import 契约 + 331 测试大量改 import） | 高（门禁短暂失效，正是 Leader 警告的"唯一防线"风险期） | ❌ 否 |

**理由**：现有 8 条 import 契约（`.importlinter`）**已经把三条铁律翻译成可机器强制的边界**（观测层只读、生活层不写世界、内核零反向依赖…）；重划 = 亲手推倒唯一防线。**插件化要的是「可挂载/可卸载/可组合」的运行时，不是重新分目录。**

### 1.2 「插件」的粒度（【已定】）

一个**插件** = 一个挂载单元 = 一个函数（或 Service 对象）+ 可选 `config` + 声明式 `inject`。它：
- 在**某个既有包内**实现（仍受该包的 import 规则约束）；
- 由**组合根**（`orchestration`）挂载到 `Context`；
- 运行时**可卸载**（撤销自己注册的一切）。

**建议的首批「叶子插件」候选**（不改领域语义，仅包一层）：

| 包 | 候选插件 | 可逆性收益 |
|---|---|---|
| `freeze` | LLM provider（`providers.py`）、缓存、预算闸门 | 换 provider 只改配置 |
| `life` | 记忆后端、检索策略、日程模板 | 新算法可插拔、旧路径保留 |
| `obs` | 各指标模块（`econ/emergence/wellbeing`） | 只读插件，按需加载 |
| `narrative` | 渲染器/风格 | 展示可换 |
| `orchestration` | 实验策略（政策档） | 实验可组合 |

> **不把「世界引擎/经济/生命周期」做成可热插拔插件**：它们是**唯一真值源**与冻结语义，插拔风险远大于收益（保底：只让**无状态叶子**可插拔）。

---

## 2. 可逆注册（Cordis effect/dispose → Python）（Q2）

### 2.1 【已定】三层结构

| 概念 | 实现 | 语义 |
|---|---|---|
| `Effect` | 持 `undo` 回调，`dispose()` **幂等** | 一个可逆副作用 |
| `Fiber` | 插件实例状态机 `PENDING→LOADING→ACTIVE→DISPOSED` | 持该插件的**全部** Effect；`dispose()` **逆序**撤销 |
| `Context` | 根 Context 持全局服务/监听器表；插件作用域 = 子 Context | 所有注册经 `ctx.*`，**自动挂到当前 Fiber** |

### 2.2 【已定】关键不变式（骨架已验证）

- **逆序撤销**：`A` 后 `B` 注册 → 卸载顺序 `~B` 再 `~A`（测试 `test_effects_revoked_in_reverse_order`）。
- **卸载后注册即撤销**：插件卸载后再 `ctx.effect(...)` → **立即 dispose，不泄漏**（`test_no_leak_when_registering_after_dispose`）。
- **服务消失→依赖方自愈**：服务被撤销时，注入它的插件**先卸载**、再进入等待；服务恢复后**自动重新 apply**（`test_dependent_disposed_then_heals_when_service_returns`）。

### 2.3 与 Python 惯用法的关系

- 备选实现：`contextlib.ExitStack`（每插件一个 stack，卸载时 `close()`）。**可作等价替代**，但缺少「依赖消失→自动卸载→自愈」的 reactive 语义，需自建。→ 采纳**显式 Fiber/Effect**。
- **Fork B 利好**：因已放开「逐位重放」，插件卸载/重挂**不要求**状态逐位一致，实现自由度更高；**但日志仍全量、随机仍种子化**（红线不变）。

---

## 3. 服务注入与依赖方向（Q3，**不得破坏 8 契约**）

### 3.1 【已定】注入与依赖倒置

```python
def llm_provider(ctx, config):      # 一个插件
    ctx.provide("llm", MyProvider(config))
def planner(ctx, config):           # 另一个插件
    llm = ctx.get("llm")            # 或函数插件 .inject=["llm"] 声明式等待
    ...
planner.inject = ["llm"]
```
- 组合根（`orchestration`）负责 `ctx.plugin(...)`；**业务包之间不新增 import**。
- 插件实现**仍在原包内** → 自动继承原包的 import 契约，**8 条契约全部不动**。

### 3.2 【已定】为什么这不破坏依赖方向

- `plugin/` 运行时**零业务依赖**（只 stdlib）→ 被谁依赖都不会造环。
- 依赖关系仍由**原包的 import-linter 契约**约束：例如 `life` 内的插件仍不得 import `engine`。
- 组合根 `orchestration` 本就被允许依赖多包（现有契约已如此）。

### 3.3 【建议】为 `plugin/` 增加一条边界契约（**待落地，勿由我直接改**）

```ini
[importlinter:contract:plugin-pure]
name = plugin 运行时只依赖 stdlib（保证可复用）
type = forbidden
source_modules = plugin
forbidden_modules = engine life freeze obs narrative orchestration frontend
```
- **反向验证（必做）**：临时在 `plugin/context.py` 加 `import engine` → `lint-imports` **必须变红**；去掉后恢复绿。**（未实测；Leader 规矩：不会报警的门禁等于没有门禁。）**
- **落地时机**：按 Leader 排期，**等 T211 的 `devtools` 契约提交、门禁回稳后**，由**单一修改者**落地（附反向验证）。

---

## 4. 类型化事件 + 配置组合 + 清单/版本（Q4）

### 4.1 【已定】类型化事件

- `ctx.on(event, handler) -> Effect`（注册可逆）、`ctx.emit(event, *args)`、`ctx.waterfall(event, *args)`（around-middleware，不调 `next()` **短路**）。
- **"类型化"的轻量实现**：事件名用**常量/Enum 集中声明**（如 `EVENT_TOOLS_PRE_EXECUTE = "tools/pre-execute"`），handler 签名用 `typing` 标注；**不引入运行时反射开销**。
- 用途对齐：`tools/pre-execute`（权限/预算闸门）、`agent/pre-step`（可见性）、`llm/stream`（成本计量）——与 DSH 的事件域同构，便于未来对齐。

### 4.2 【已定】配置组合（layered patch）

- `compose(base_entries, *overlays)`：`{"id":...}` **整体替换** config（非深合并，同 Cordis）；`{"insert":[...]}` 追加（可 `after` 定位）；**不改入参**。
- 用 YAML/JSON 表达 `cordis.yml` 等价物：`config/plugins.yaml`（后续可加）。**版本化**：配置指纹入清单指纹。

### 4.3 【已定】插件清单 / 版本

- `describe(ctx) -> [PluginInfo(id,name,injects,state)]`（按 id 升序，稳定）；`fingerprint(infos) -> "sha256:..."`（键排序、无空格）。
- 供「**证据绑版本**」：每次 run 记录 `plugin_fingerprint` + 代码 sha + 命令。

---

## 5. 哪些能力适合抽成「可复用到其他项目」的插件（Q5，用户 #5 核心）

### 5.1 【已定】可复用性分级

| 级 | 判据 | 能力（举例） | 可复用? |
|---|---|---|---|
| **L0 运行时** | 仅 stdlib | `plugin/`（Context/Fiber/Effect/事件/配置/清单） | ✅ **跨项目** |
| **L1 协议** | 仅 `contracts` 纯类型 | LLM 接入端口、记忆存储端口、调度端口、观测端口 | ✅ **跨项目**（带协议） |
| **L2 通用能力** | stdlib + L1 协议 | LLM provider/预算闸门/缓存、事件总线、T0/T1/T2 调度器、向量检索接口 | ✅ 跨项目（hatch 装包即用） |
| **L3 项目领域** | 依赖 engine 写路径 | 经济结算、生命周期、社会观测指标、青溪镇场所/规范 | ❌ **项目专属，不抽出** |

### 5.2 【已定】可复用插件的依赖边界（硬规则）

> **可复用插件只依赖 `stdlib` + `contracts`（纯协议），绝不 import `engine`/`life`/`freeze`/`obs`/`narrative` 的内部实现。**
> 领域相关的一切通过**注入的端口**（`contracts.interfaces`）获得。

### 5.3 【已定】抽成独立分发的路径（未来）

- 打包：把 `plugin/` + 若干 L2 插件做成独立 `pyproject`（如 `qingxi-plugin-core`），`pip install` 即用。
- 现状：**先内联在项目根 `plugin-skeleton/`**，验证通过后再抽包（避免过早拆包）。**【未验证】** 抽包与版本管理细则。

### 5.4 具体建议抽出的插件（候选清单）

1. `plugin-core`（运行时）— 本骨架。
2. `llm-provider`（provider 可插拔 + 预算闸门 + 内容寻址缓存）。
3. `memory-store`（append-only + 向量检索接口）。
4. `scheduler`（分层决策 T0/T1/T2 + 事件驱动唤醒）。
5. `event-bus`（类型化事件 + waterfall）。
6. `config-compose`（layered patch + 指纹）。

---

## 6. 渐进接入路径（Q6，**不得一次性大重构**）

| 阶段 | 动作 | 影响面 | 回退 |
|---|---|---|---|
| **P0（本次）** | 落 `plugin-skeleton/`（独立目录，零业务依赖） | **无**（不碰 `code/`） | 删除目录 |
| **P1** | 把 `plugin/` 运行时**复制**进 `code/` 作为新包（需 Leader 排队 + 新增 1 条契约） | 纯新增 | `git revert` |
| **P2** | 首个叶子插件：`freeze` 的 **LLM provider** 包成插件，**feature flag** 控制，默认走旧路径 | 局部 | 关 flag |
| **P3** | `obs` 各指标模块 → 只读插件（按需加载） | 局部 | 切回直接 import |
| **P4** | `narrative` 渲染器、`orchestration` 策略 → 插件 | 局部 | 同上 |

**准入规则（每阶段都遵守）**：
1. **新代码用插件；老代码不动**（双路径并存，flag 切换）；
2. **每步 `pytest`/`lint-imports`/`lexicon-gate` 必须绿**；
3. **可回退**（flag/删除/`revert`）；
4. **不做跨包大搬家**（边界稳定优先）。

---

## 7. 骨架可运行证据（复现命令）

**位置**：`plugin-skeleton/`（独立于 `code/`）。

```sh
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/plugin-skeleton
python3 -m pytest tests -q        # 实测：11 passed
```
**实测结果（本机）**：`11 passed`（可逆副作用 3 条 / 服务注入 3 条 / 类型化事件 2 条 / 配置组合 2 条 / 清单 1 条）。

**code/ 门禁（确认本次未破坏）**：
```sh
cd ../code && lint-imports        # 实测：Contracts: 9 kept, 0 broken（含 T211 的 devtools 契约；我的 plugin 契约未落地）
python3 -m pytest -q              # 实测：342 passed
cd .. && make lexicon-gate        # 实测：新增违规 0 条
```

> **诚实说明**：本次我**曾**在 `code/` 落地过 `plugin/` + 一条契约（用于验证可行性），**在收到 Leader「T214 先出建议、不落地」的规矩后已全部回撤**：`code/plugin/` 与 `code/tests/test_plugin_arch.py` 已删除，`.importlinter` 中我的两处改动已移除（**保留 T211 的 `devtools` 契约**）。**当前 `code/` 无我的痕迹，门禁 9/0 绿。**

---

## 8. 对 `.importlinter` 的**建议**（勿直接落地）

1. 新增 `root_packages: plugin` 与契约 `plugin-pure`（内容见 §3.3）。
2. **反向验证模板**（落地者必做）：
   ```sh
   cp code/plugin/context.py /tmp/bak.py
   printf '\nimport engine  # noqa: F401  FORBIDDEN-PROBE\n' >> code/plugin/context.py
   (cd code && lint-imports)   # 期望：plugin-pure BROKEN，退出码非 0
   cp /tmp/bak.py code/plugin/context.py
   (cd code && lint-imports)   # 期望：恢复 kept
   ```
3. **落地纪律**：单一修改者、提交信息写明改了哪几条、附反向验证输出。

---

## 9. 【未验证】与开放问题

| # | 事项 | 说明 |
|---|---|---|
| U1 | `plugin-pure` 契约的反向验证**未实测** | 我未在 `code/` 落地该契约（按规矩），故"故意违反→变红"未跑；留给落地者。 |
| U2 | 热插拔对**长驻仿真**的实际收益 | 离线批处理是否需要 HMR/服务自愈，未评估（T206 §7.6 同款问题）。 |
| U3 | 抽成独立 PyPI 包的分发/版本细节 | 未设计。 |
| U4 | 类型化事件的**运行时校验**强度 | 现为约定 + 注解；是否需 registry 强校验未定。 |
| U5 | 与 Fork B（放开逐位重放）的交互 | 插件卸载/重挂是否影响日志连续性，未评估。 |

---

*（v2/refs/python-plugin-architecture.md 完成 — solution-architect）*