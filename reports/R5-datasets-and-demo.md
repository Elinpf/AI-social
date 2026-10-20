# R5 · 数据集与演示：数据在哪、字段怎么读、页面怎么看

> **状态**：**骨架版（数据形态与页面入口已写实；本轮语料与截图待填）**。当前写实的是"已有数据的结构与入口"，本轮 after 臂/A1 臂的数据与截图在锁 sha 后补。
> **报告族**：R5｜可信边界见 **R1 §3**｜全族纪律见 `reports/README.md`
> **署名**：AI 小镇 · 对话体验与研究发布小队（JiuwenSwarm 多智能体团队）
> **锚点**：本文件首版提交见 `git log --format=%H -- reports/R5-datasets-and-demo.md`｜仓库 `social-experiment`

---

## 1. 数据集目录

**读法**：每份数据集必须能回答四件事——在哪、怎么生成、多大、字段怎么用。缺一项即视为不可交付。

| # | 数据集 | 路径 | 生成方式 | 体量 | 状态 |
|---|---|---|---|---|---|
| D-1 | **v0-anchor** 语料（旧结构 + 原提示词） | `v2/evidence/run_d2_before_n16_seed42/run.jsonl` (c1f86bf6) | 真 LLM 跑批（`openai_compat`/`DeepSeek-Flash`，16×84，seed=42） | **87.5 MB / 186,972 行** | **已交付**（`max_round=83`；准入 ADMITTED/strict/evidence） |
| D-2 | **A0** 语料（新结构 + 必要适配提示词） | `v2/evidence/run_d2_after_n16_seed42/run.jsonl` (643f13a5) | 真 LLM 跑批（`openai_compat`/`DeepSeek-Flash`，16×84，seed=42） | **194,108 行** | **已交付**（`code_sha` fcf42bf9；消息 686 = DM497/PUB63/GRP126；`thread_schema=explicit`） |
| D-3 | **A1** 语料（A0 + 措辞层优化） | 待填 | 真 LLM 跑批 | 待填 | 待交付 |
| D-4 | 评测读数（各臂指标） | `v2/evidence/d5_metrics_*.json` / `.md` | `tools/d5/dialogue_metrics.py` | 每份数 KB–数十 KB | 部分已有（历史批） |
| D-5 | 线程视图数据 · v0-anchor | `code/frontend/sample/dialogue_v0anchor_n16_seed42/threads.json` (e39168ea) | `code/frontend/tools/gen_threads.py` | 187 条线程（legacy 口径） | **已交付**（自带 `source.run_sha256=c1f86bf6…`、`generator_sha256`） |
| D-5A | 线程视图数据 · A0 | `code/frontend/sample/dialogue_run_d2_after_n16_seed42/threads.json` (d6d89bda) | `code/frontend/tools/gen_threads.py` | 206 条线程（`explicit`） | **已交付**（自带 `source.run_sha256=643f13a5…`、194,108 事件） |
| D-5b | 线程视图数据 · 历史样例 | `code/frontend/sample/dialogue_demo/threads.json` (0bfb6288) | 同上 | 543 KB，231 条线程 | 历史（**不作本轮结果**） |
| D-6 | judge 原始输出（全量） | `judge_raw.jsonl`（不入库，给 sha） | `tools/d5/dialogue_judge.py` | 待填 | 待交付 |
| D-7 | judge 抽样版（可核验用） | `v2/evidence/judge_raw_sample_n24x2.jsonl` | 同上（前缀子集） | 每臂 24 线程（≤72 条消息） | 待交付 |

**【事实】** D-5 现有文件的头部自带溯源字段，可直接核验它是从哪份日志生成的：`schema=hitt.dialogue.threads/1`、`generated_by=frontend/tools/gen_threads.py`、`generator_sha256=52935ef8…`、`source.run_label=p1_final_n20_llm`、`source.run_sha256=fb832372af235736b78e539ab676feff08c3e94e79ffcdbe0dc4b5d88b13a2fc`、`source.events_total_in_log=128564`、`source.round_range=[0,83]`、`source.llm_provider_in_log=openai_compat`。
文件 sha256：`0bfb62887757d8900b8de50891ff2cb4202f48c064f35dac8fbbd62cbb8bc2c8`。

**【判断】** 这种"数据文件自带生成器 sha + 源日志 sha"的做法应当成为硬要求——否则一张好看的截图无法证明它来自哪次跑批。R5 的截图三件套就建立在这个字段上。

---

## 2. 字段字典

### 2.1 事件（`run.jsonl` 每行一条）

**【事实】** 事件外壳字段：`seq`、`round`、`phase`、`actor`、`type`、`payload`、`mono_ts`、`prev_hash`、`hash`；`mono_ts` 是逻辑时间（回合 × 时间单位 + 阶段序号），不是墙钟；`hash` 构成哈希链，每回合末追加 `TURN_SEAL`（`code/README.md` §3.2）。

### 2.2 对话消息 payload

| 渠道 | 事件类型 | 关键字段 |
|---|---|---|
| 定向 | `MSG_DM` | `msg_id, from, to, body, body_ref, refs, tag_hints, place, day, slot` |
| 公开 | `MSG_PUBLIC` | `msg_id, author, topic, body, body_ref, refs, tag_hints, place, scope, day, slot` |
| 群组 | `MSG_GROUP` | `msg_id, group_id, from, body, body_ref, refs, tag_hints, place, day, slot` |

**【事实】** 线程化改造后追加：`thread_id`、`turn_index`、`reply_to`、`participants`、`ctx{relation, mood, need, topic}`（只追加、不新增事件类型，详见 R2 §2）。
**【事实】** 改造前这些字段不存在：`topic` 恒为空、`refs` 恒为空数组。

### 2.3 如何还原一条对话

```
按 thread_id 分组 → 组内按 (round, seq) 升序 → 即一条线程；
线程轮次（主口径）= 1 + 相邻两条说话人变化的次数；
改造前无 thread_id 时：thread_key = (day, channel, {from,to})，同样排序。
```
（规则来源 R2 §3；两种口径分别标 `thread_schema = explicit` / `legacy`，**不混算**。）

### 2.4 线程视图数据（`threads.json` (0bfb6288)）

**【事实】** 顶层字段：`schema`、`generated_by`、`generator_sha256`、`source{run_label, run_sha256, run_bytes, events_total_in_log, round_range, llm_provider_in_log, …}`、`prune_rule`（保留哪些事件类型、其余丢弃且不参与统计）、`move_rule`、`field_contract`、`agents`、`places`、`moves`、`travel`、`rhythm`、`spread`、`stats`、`threads`。
**【事实】** 每条线程字段：`thread_id`（legacy 口径下为 null）、`legacy`、`channel`、`participants`、`place`/`places`、`start_round`/`end_round`、`turns`、`multi_turn`、`messages[]`；每条消息字段：`seq`、`round`、`type`、`channel`、`msg_id`、`from`、`to`、`group_id`、`body`、`body_ref`、`thread_id`。

---

## 3. 页面入口

**【事实】** 静态服务（只读）：`cd code && python3 frontend/tools/serve.py`，默认 `http://127.0.0.1:8848/`；或 `make serve`（绑定 0.0.0.0:8848）。**必须通过 http 访问**，直接双击 `file://` 打不开（浏览器的同源策略会挡住取数）。
**【事实】** 服务端点：`/__gitstamp` 返回当前提交 sha 与是否 dirty；`/__tail?path=&off=` 支持按偏移增量读取日志尾部（用于"实时跟随"），可读根目录有白名单限制。
**【事实】** 页面清单：`index.html` 小镇观测台（像素镇 + 事件流 + 审计抽屉）、`dialogue.html` 对话线程视图（本轮新增）、`trace.html` 单 agent 时间线、`dashboard.html` 指标仪表盘、`fourgroups.html` 四组对照、`review.html` 人工评分页。

**【未完成】** 本轮演示入口的最终形态（页面路径 + 需要的数据文件 + 看什么）待 D7 定稿后填入。平台约束不变：任何"看起来像实时"的说法都要能对应到具体日志文件。

---

## 4. 截图清单

**【事实】** 规范固定（全族适用），改造前部分已交付、改造后待交付：

- 必须由**真实 `run.jsonl`** 渲染，文件名 `<batch_id>-<视图>-<sha8>.png`；
- 每张图在报告中注明三件套：**来源 run 目录 + 渲染命令 + 日志 sha256**；
- 禁止：手工拼图、示意图充当实拍、跨批混拼、裁掉异常部分只留好看的；
- 若某图拿不到：写「无图，附可复现渲染命令」，**不用别的东西替代**。

**改造前（v0-anchor）四张已交付**，均由日志 `run.jsonl` (c1f86bf6) 渲染，文件名自带 batch + sha8：

| # | 截图文件（`v2/evidence/d7_shots/`） | 视图 | 来源 run | sha256（sha8） |
|---|---|---|---|---|
| S-1 | `run_d2_before_n16_seed42-chat-c1f86bf6.png` | 对话/聊天面板 | `run_d2_before_n16_seed42` (c1f86bf6) | `93a17e90…`（`93a17e90`） |
| S-2 | `run_d2_before_n16_seed42-rhythm-c1f86bf6.png` | 一天的时间轴（作息节律） | 同上 | `de76c2d5…`（`de76c2d5`） |
| S-3 | `run_d2_before_n16_seed42-spread-c1f86bf6.png` | 话语/话题的扩散 | 同上 | `c07844ea…`（`c07844ea`） |
| S-4 | `run_d2_before_n16_seed42-600-c1f86bf6.png` | 600px 窄屏视图 | 同上 | `b0aec225…`（`b0aec225`） |

**渲染命令（可复现，仓库根执行）**：
```bash
cd code && python3 frontend/tools/serve.py            # 浏览器打开 http://127.0.0.1:8848/ ，加载 sample/dialogue_v0anchor_n16_seed42/threads.json
# 截图：浏览器视口按需设置（含 600px 窄屏），保存为 <batch_id>-<视图>-<sha8>.png
```

**【事实】** 四张图对应的线程视图数据为 `code/frontend/sample/dialogue_v0anchor_n16_seed42/threads.json` (e39168ea)，其 `source.run_sha256 = c1f86bf6…`、`events_total_in_log = 186,972`、`round_range = [0,83]`、`llm_provider_in_log = openai_compat` ⇒ **图与日志的对应关系可核对**（三件套齐）。

**改造后（A0）四张已交付**，与上表**同视图、同口径成对引用**：

| # | 截图文件（`v2/evidence/d7_shots/`） | 视图 | 来源 run | sha256（sha8） |
|---|---|---|---|---|
| S-5 | `run_d2_after_n16_seed42-chat-643f13a5.png` | 对话/聊天面板 | `run_d2_after_n16_seed42` (643f13a5) | `15d02ab2…`（`15d02ab2`） |
| S-6 | `run_d2_after_n16_seed42-rhythm-643f13a5.png` | 一天的时间轴 | 同上 | `baf2d9fc…`（`baf2d9fc`） |
| S-7 | `run_d2_after_n16_seed42-spread-643f13a5.png` | 话语/话题扩散 | 同上 | `eae35979…`（`eae35979`） |
| S-8 | `run_d2_after_n16_seed42-600-643f13a5.png` | 600px 窄屏 | 同上 | `45bf561c…`（`45bf561c`） |

> ✅ **重出记录（2026-10-21 00:05，按新标签重出并替换旧版）**
> - 旧版生成时间 `2026-10-20 20:24`，早于前端标签修正 `6ce44f9`（2026-10-20 20:56）；旧图 sha8：chat `44b7fb23` / rhythm `d553eaba` / spread `aab855e4` / 600 `fad59476`。
> - 新版生成时间 `2026-10-21 00:05`；新图 sha8：chat `15d02ab2` / rhythm `baf2d9fc` / spread `eae35979` / 600 `45bf561c`（全 sha256 见上表）。
> - 重出命令（在 `code/` 下执行；服务 `http://127.0.0.1:8848` 已在跑，未重启）：
>   ```bash
>   cd code && bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 \
>        sample/dialogue_run_d2_after_n16_seed42/threads.json
>   ```
> - 数据源未变：`code/frontend/sample/dialogue_run_d2_after_n16_seed42/threads.json`，`source.run_sha256 = 643f13a5…`；**仅前端渲染标签变化，不是数据变化**。
> - 标签已核验（Playwright 等 `window.__RENDER_READY__===true` 后读页面文本）：最长线程头显示 **「18 条 / 6 轮」**，并有「turn_index 重复」标记；页面排序提示写「当前最长 18 条 / 6 轮」。⇒ 现图可据以判读轮数（`turn_index` 去重，A0 实测 **max 6 轮**；`stats.max_turns=18` 是**消息条数**口径，不是轮数）。

**【事实】** 对应的线程视图数据 `code/frontend/sample/dialogue_run_d2_after_n16_seed42/threads.json` (d6d89bda)，其 `source.run_sha256 = 643f13a5…`、`events_total_in_log = 194,108` ⇒ 图 ↔ 日志对应可核对。

**A1 截图：待交付**（A1 尚未解锁）。

---

## 5. 复现三步

```bash
# ① 起跑（需真 LLM 凭据经环境变量注入；跑后必须过真跑门禁）
cd code
python3 -m orchestration run --life --seed 42 --agents 16 --rounds 84 --out <RUN_DIR>/run.jsonl
python3 -m obs llm-cost --log <RUN_DIR>/run.jsonl --require-provider openai_compat   # rc 即判决

# ② 复算指标（仓库根执行）
python3 tools/d5/dialogue_metrics.py --log <RUN_DIR>/run.jsonl --meta <RUN_DIR>/meta.json \
  --out-json <OUT>/metrics.json --out-md <OUT>/metrics.md

# ③ 生成线程视图并打开页面
python3 code/frontend/tools/gen_threads.py --log <RUN_DIR>/run.jsonl --out code/frontend/sample/dialogue_demo/threads.json
cd code && python3 frontend/tools/serve.py        # 浏览器打开 http://127.0.0.1:8848/dialogue.html
```

---

## 6. 引用与许可

- 报告族引用格式见 `reports/README.md`。
- 本仓库含第三方许可合规文件（`code/THIRD_PARTY_NOTICES.md`、`code/licenses/`）；派生文件逐文件"已修改"声明分别见 `code/life/NOTICE` 与 `code/frontend/NOTICE`。数据与截图的使用须遵守相应许可。
- 数据中的人物标识（如 `P001`）为**合成角色 ID**，不对应任何真实个人。

---

## 7. 限制

1. **数据体量差异大**：完整 `run.jsonl` 可达数十 MB 至百 MB 量级，故 `.gitignore` 默认忽略 `*.jsonl`；对外以**sha256 + 生成命令 + 线程视图派生文件**保证可核验，而非直接托管原始日志。
2. **派生视图有裁剪规则**：`threads.json` (0bfb6288) 只保留对话与语境事件（`prune_rule` 明写），其余事件丢弃且不参与统计——**不能用它替代原始日志做统计**。
3. **截图是渲染结果，不是证据本身**：证据是日志 + sha；截图只帮助读者快速理解，任何"图上看着很好"的推断都必须回到读数。
4. **legacy 口径的现有派生数据不能当本轮结果**：D-5 当前文件来自历史批（`p1_final_n20_llm`），本轮须用新语料重新生成。
