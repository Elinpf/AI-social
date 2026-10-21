# R9 · 措辞臂 A1：压低括号旁白的提示词改造（**名义双变量**，窗口变量经 D9 证明惰性；方向性筛查）

> **版本状态：【读数、截图与判定已定稿（裁定 B：真实但有副作用）· 已随 `feat/wording-a1` 推送】** 本轮**不出效果结论**：形式层（括号旁白）与本提示词约束一致，但具体性通道被替换（详见 §4.2）。
> **报告族**：R9｜短名 `wording-a1`｜可信边界总则见 **R1 §3**，生活气息维度定义见 **R4 §1**，措辞层口径见 **R3 §2**（本份不复制定义，只引用编号）
> **分层标记**：【事实】／【读数】／【判断】／【未完成】
> **署名**：AI 小镇 · 对话体验与研究发布小队（JiuwenSwarm 多智能体团队）

---

## 0.0 更正记录（leader 裁定 2026-10-21 10:17，按此为准）

**【更正 1 · A0 绑错树】** 本报告原把 A0 记为 `884f4541` 并引 `prompt_sha = e6ec7355…`，**错误**。A0 日志是 19:19 在 landing **`3ec85a0`** 上跑的：
- **运行期树（拍板身份）= `3ec85a0`**（`code_sha_start`，landing 记录 + 期间无改动）；
- `884f4541` 只是 **meta 写入时刻的 HEAD**，**不代表跑批代码**；
- A0 的 `prompt_sha` 应为 **`2cb2f5ba…`**（`3ec85a0` 的值），不是 `e6ec7355…`（那是 `884f4541` 的）。

**【更正 2 · A1 不是单变量】** `git diff 884f4541 a637371 -- code/life` 除两条收尾提示词外，**还含 `dialogue_threads.py` 中 `reply_window_rounds: 2 → 4`**。故 A1 是**名义双变量**：
- **豁免理由是「另一臂证明惰性」**（与 R8 的「关闭无扰动」是两种不同豁免，勿混）：单变量窗口臂（`05636bc`，「`reply_window_rounds` 2→4」；团队内或称 D9 窗口臂 / D8-R8 窗口臂）与 A0 的回复间隔分布**完全相同 `{1: 327, 2: 153}`、最大间隔 = 2，从未出现 3/4** ⇒ 该变量**在行为上惰性**；
- 因此结论统一改写为：**「措辞层效应（在名义双变量下观测，其中窗口变量经 D9 证明为惰性）」**；**全文不再使用「单变量」表述**。

> 以上两条为本报告的口径更正；原「单变量」与 `e6ec7355` 的表述已按此替换。

---

## 0. 基线与改动面

### 0.1 两臂身份

| 臂 | 分支 / `code_sha` | 规模 | `run.jsonl` sha256（sha8） | 消息数 | 准入 |
|---|---|---|---|---|---|
| **A0**（基线） | **运行期树 `3ec85a0`（landing；数据源 `run_d2_after_n16_seed42`）**；`884f4541` 仅记为 meta 写入时刻 HEAD，**不代表跑批代码** | 16 agents × 84 rounds / seed 42 | `643f13a528c288d3e9677cb8ac100139224afbd0b46c0f7da0c3a5ed85b13141`（`643f13a5`） | **686** | `ADMITTED / evidence` |
| **A1**（措辞臂） | `feat/wording-a1` @ **`a637371`**（`code_sha = code_sha_end`） | **4 agents × 60 rounds / seed 42** | `ae969198feaefd1f69147001e027394d55527bd1a0e460ff654697bdc3b1559b`（`ae969198`） | **124** | **`REJECTED / probe`**（见 §2.4） |

> ⚠️ **规模不同（n16r84 vs n4r60；686 条 vs 124 条）是本报告最重要的边界**：分母差 **>30%**，按族纪律（`reports/README.md`）两臂率值**不可比**，本报告**只写方向性**，不写效果结论、不做显著性断言。

### 0.2 A1 的改动面（**名义双变量**：两条收尾提示词 + `reply_window_rounds` 2→4；后者经 D9 证明惰性）

- 文件：`code/life/agent.py`，**精确两行** —— `L1058`（`_dialogue_prompt` 末行）、`L1069`（`_reply_prompt` 末行）；`2 insertions / 2 deletions`，不增删行、缩进不变。
- 旧 → 新：
  - dialogue：`请用一句话自然地说点什么。` → `只写台词本身（一句家常话）：不要用括号、方括号或星号写动作、神态或心理旁白，不要解释也不要总结；用口语短句，别反复用同一句口头禅。`
  - reply：`请接着说一句。` → `只写台词本身（接着刚才的话往下说一句）：不要用括号、方括号或星号写动作、神态或心理旁白，不要解释也不要总结；用口语短句，别反复用同一句口头禅。`
- 逐字 diff + 基线声明 + 变/不变对照：**`v2/evidence/d4_prompt_diff_a1.txt`**
- `prompt_sha`（口径 `tools/prompt_iter/prompt_iter.py:32`）：**A0 `2cb2f5ba…`（运行期树 `3ec85a0`）→ A1 `5186aa9a3db55de8`**（不相等 ⇒ 提示词改动确实生效）。⚠️ 原写的 A0 `e6ec7355…` 属 `884f4541` 树，**已作废**。
- 零 `config` 改动、零 `engine` 改动、零结构改动；`soft.py` / `planner.py` / `freeze/llm_client.py` / `persona.py` 整文件 sha256 未变。

### 0.3 复算命令（逐字，仓库根执行）

```bash
# 两臂 d5 全指标（必须带 --meta；只给 --log 会掉成 REJECTED/probe 而指标值不变）
python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_a1_wording_n4r60_seed42/run.jsonl \
    --meta v2/evidence/run_a1_wording_n4r60_seed42/meta.json \
    --out-json /tmp/r9_d5_a1.json --out-md /tmp/r9_d5_a1.md
python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_d2_after_n16_seed42/run.jsonl \
    --meta v2/evidence/run_d2_after_n16_seed42/meta.json \
    --out-json /tmp/r9_d5_a0.json --out-md /tmp/r9_d5_a0.md
# 对拍入库件（A1 应得同一个 sha256）
sha256sum /tmp/r9_d5_a1.json v2/evidence/d5_metrics_a1.json   # 两行相同：53a10de3f03efe12…
# 真跑/成本验真
cd code && python3 -m obs llm-cost --log ../v2/evidence/run_a1_wording_n4r60_seed42/run.jsonl \
    --require-provider openai_compat
```

---

## 1. 方法论与变量声明（**名义双变量**）

- **名义双变量**：两臂差别 = ①`_dialogue_prompt`/`_reply_prompt` 两条收尾指令；②`dialogue_threads.py` 的 `reply_window_rounds` 2→4。**②在行为上惰性**（D9 单变量臂：回复间隔分布 `{1:327,2:153}` 两臂完全相同、最大间隔 2，从未出现 3/4）⇒ 措辞层效应可近似归因于 ①，但**表述上仍须写「名义双变量」**。相对 master 的 diff 只落在 `code/life/agent.py` 两行；函数级对照显示全文件 51 个函数中**只有这 2 个函数变化**，其余 49 个不变且**无行号移动**（`d4_prompt_diff_a1.txt` §4）。
- **未改 **：`reply_window_rounds`（保持 D9 的 4）、`max_messages_per_slot=2`、`max_turns=6`、感知窗 `VISIBLE_WINDOW_ROUNDS=2`、全部 `config`、全部 `engine`/调度/时间模型 ⇒ 与本轮正交。
- **两臂不可比的部分**：规模（16×84 vs 4×60）、消息分母（686 vs 124）；A1 为**方向性筛查批**（成本约束下的最小样本），不是与 A0 同规模的正式对照臂。
- **本报告不做的**：不做率值显著性比较、不给噪声带（本轮未跑同分母 bootstrap）、不把 `probe` 级读数写成结论。

---

## 2. 读数表（A0 vs A1，逐行给来源与复算方式）

### 2.1 措辞层主表（per-message）

| 指标 | A0（分母 686） | A1（分母 124） | 绝对数变化 | 来源文件 | 复算命令 |
|---|---|---|---|---|---|
| **L-2 旁白代理率** | 0.819242（**562/686**） | **0.000000（0/124）** | −562 条 / 本批 0 条 | `v2/evidence/d5_metrics_d9a0.json`、`d5_metrics_a1.json` | 见 §0.3 |
| **L-3 括号块率** | 0.860058（**590/686**） | **0.000000（0/124）** | −590 条 / 本批 0 条 | 同上 | 同上 |
| **L-6 精确重复率** | 0.099125（68/686） | **0.129032（16/124）** | **反向 ↑ +0.0299（+2.99 pp）** | 同上 | 同上 |
| **L-7 8-gram 重复率** | 0.488338（335/686） | **0.411290（51/124）** | −0.0770（**不同分母，不作差量解释**） | 同上 | 同上 |
| L-5 模板命中率 | 0.018950（13/686） | **0.024194（3/124）** | **反向 ↑ +0.0052（+0.52 pp）** | 同上 | 同上 |

> **L-2 / L-3 的 0 必须按「天花板效应 + 精确二项上界」读（禁止写成"旁白率降到 0%"）**
> 本批 124 条消息中括号块出现 **0 次**。0 事件时的 95% 上界用精确二项（`rule-of-three`）：**3/124 ≈ 2.4%**。
> ⇒ 正确表述：「**本批 124 条中括号块出现 0 次；以 0/124 与 95% 上界 ≈2.4% 计，只能说与该提示词约束一致，无法与 A0 的 82.0% 作同口径比较**」。
> ⇒ **禁止**：「旁白率降到 0%」「完全消除旁白」「旁白问题已解决」。

### 2.2 长度代价（与 §2.1 同表并列，**不是脚注**；**同栏对同栏**）

> **口径纪律（必须遵守）**：`L-1_len` 有两个栏 —— `all`（原文全长）与 `excl_paren`（去括号块后的"台词本体"）。A1 因**整批零括号块**，两栏数值完全相同。**跨栏比较属"跨栏"错误**，因此主对比用 **`excl_paren` vs `excl_paren`**（与 L-2/L-3 的口径自洽，主角就是"台词本身"），`all` 栏只作对照。

| 比法 | 统计量 | A0（n=686） | A1（n=124） | 变化 |
|---|---|---|---|---|
| **`excl_paren` vs `excl_paren`（主用）** | mean | **45.828** | **27.540** | **−39.9%** |
| 同上 | p50 | **41.0** | **19.5** | 中位数缩短 52% |
| 同上 | p90 | 80.5 | 63.0 | — |
| 同上 | max | 164 | 104 | — |
| `all` vs `all`（对照） | mean | **58.306** | **27.540** | **−52.8%** |
| 同上 | p50 | 54.0 | 19.5 | — |
| 同上 | p90 | 97.5 | 63.0 | — |
| 同上 | max | 204 | 104 | — |

- **A1 两栏相等的原因**：本批 124 条消息中括号块出现 **0 次**（§2.1 的 L-3 = 0/124），故 `excl_paren ≡ all`。
- **A0 两栏的差**（58.306 − 45.828 = **12.478 字/条**）即**括号旁白平均占据的篇幅**，这也解释了为什么"压旁白"会同时压掉总长。
- **幅度读法**：`excl_paren` 主口径 −39.9%（台词本体从 45.8 字降到 27.5 字），`all` 对照口径 −52.8%。**这是代价项，不是收益**：台词更容易"一句话说完就结束"，可能牺牲信息量与生活细节；与 §2.1 的 L-5/L-6 反向上升相互印证（短句更易撞模板/重复）。
- **必须连同这句话读**：「两臂规模不可比（686 vs 124），**长度差异只能作方向性观察，不得当作效应量**。」

### 2.3 生活气息与结构（仅登记，不作结论）

| 指标 | A0 | A1 | 备注 |
|---|---|---|---|
| F-1 非功能性闲聊占比 | 0.760933（522/686） | 0.750000（93/124） | 差 −1.1 pp，分母不可比 |
| S-1 `single_msg_thread_ratio` | 0.495146 | 见 `d5_metrics_a1.md` | 分母 206 vs 本批线程数，不可比 |

### 2.4 准入与真跑验真

- **A1 准入 = `REJECTED` / `evidence_level = probe`** —— 唯一阻断项是 `B-15_msg_volume`（**124 < 150**），**与 D8 两臂（同为 n4r60、124 条）完全同因**，是**规模性门禁结果、不是事故**，也不是数据/机制缺陷。
- ⇒ 按族纪律（分母 <68 标 `probe`、不可比样本不出结论），R9 的措辞层读数**全部按 `probe` 对待**，只用于方向性描述。
- **真跑验真（`obs llm-cost` 原件 = `v2/evidence/a1_llmcost_ae969198.txt` / `run_a1_wording_n4r60_seed42/llmcost.json`）**：RC=0、`provider_guard.ok=true`、`by_provider={openai_compat: 272}`（**无 mock 混入**）、`total.calls=272`、`cached=45`、`degraded=0`、`thinking=74`；分目的 `dialogue 124 / judge 74 / importance 34 / reflect 23 / negotiation 13 / plan 4`。
- 批身份：`code_sha = code_sha_end = a6373719…`、n=4、rounds=60（`rounds_effective=60`）、seed=42、events=9940、`run_bytes=4,749,329`、`degraded_calls=0`、`fallback_detected=false`、04:33:56→04:41:58（482 s）。
- 起跑前置证据（SID/PGID 分离 PASS、`pgrep` 空）：`v2/evidence/a1_launch_evidence.txt`。

---

## 3. 真实截图与原文样本

### 3.1 四视图截图（A1 真拍）

| 视图 | 文件 | 尺寸 | sha256 | sha8 |
|---|---|---|---|---|
| chat（对话流） | `v2/evidence/a1_shots/run_a1_wording_n4r60_seed42-chat-ae969198.png` | 1400×900 | `0e05129bb9779691044a6eb933cd844c47e5651a9e9d01744a17a0b1dbb311d5` | `0e05129b` |
| rhythm（节律·串门） | `v2/evidence/a1_shots/run_a1_wording_n4r60_seed42-rhythm-ae969198.png` | 1300×1050 | `7c3d7eea9c1f130607bd3ed411a683843ae41a1c99a0baee33a7bf1aa95959c8` | `7c3d7eea` |
| spread（闲话怎么传开） | `v2/evidence/a1_shots/run_a1_wording_n4r60_seed42-spread-ae969198.png` | 1300×900 | `c3fc91ec399f9a70eb2994521fde0395d2da5f8746dbb05c7f2feba2a708b17f` | `c3fc91ec` |
| 600（窄屏判读） | `v2/evidence/a1_shots/run_a1_wording_n4r60_seed42-600-ae969198.png` | 600×900 | `13ce8b1953fa1db30e27596b6b044f0ba13ff43aebb772d123c07a6e0792114b` | `13ce8b19` |

- **来源 run 目录**：`v2/evidence/run_a1_wording_n4r60_seed42/`；**日志 sha256**：`ae969198feaefd1f69147001e027394d55527bd1a0e460ff654697bdc3b1559b`（文件名 sha8 即此前 8 位，可反查数据源）。
- **渲染命令**：
  ```bash
  python3 code/frontend/tools/gen_threads.py --log v2/evidence/run_a1_wording_n4r60_seed42/run.jsonl \
      --meta v2/evidence/run_a1_wording_n4r60_seed42/meta.json \
      --out code/frontend/sample/dialogue_a1_wording_n4r60_seed42/threads.json --require-complete \
      --label run_a1_wording_n4r60_seed42-ae969198
  cd code && bash frontend/tools/dialogue_shots.sh http://127.0.0.1:<port> \
      sample/dialogue_a1_wording_n4r60_seed42/threads.json "" "" ../v2/evidence/a1_shots
  ```
- **渲染日志**：`v2/evidence/a1_shots/render.log`（sha8 `6ec172f2`），末行 `OK: …-{chat,rhythm,spread,600}-ae969198.png`，`blank_retries=0/2`。
- **A0 对照图不在本目录引用**（`v2/evidence/d7_shots/` 的 A0 四图为不同批，**不得互相替换**）。

### 3.2 原文样本（生活气息最直观证据；A1 六条含 DM 与群聊各半）

**A1（`ae969198`，124 条中摘 6 条）**

| # | 渠道/回合 | 发言 | 原文 |
|---|---|---|---|
| 1 | DM r0 | P004 → P002 | 老石，你尝尝这个新烤的枣泥酥，我减了点糖，看看合不合你口味。 |
| 2 | DM r1 | P002 → P004 | 嗯，酥皮起得不错。糖再少点也行。 |
| 3 | DM r1 | P004 → P002 | 老石，你尝尝这个新烤的枣泥酥，我少放了糖，配茶正好。 |
| 4 | public r0 | P002 | 这块料子纹理顺，下刀得慢着点。 |
| 5 | public r24 | P002 | 这榫头再修半寸就严实了，弄完就去灶上热口饭。 |
| 6 | public r25 | P002 | 刨子得再磨磨，肚子倒先叫了。 |

**A0 对照（`643f13a5`，686 条中摘 3 条）**

| # | 渠道/回合 | 发言 | 原文 |
|---|---|---|---|
| 1 | DM r0 | P004 → P002 | 老石啊，我刚烤了一炉桂花糕，你尝尝看——要是觉得太甜了跟我说，我下回少放点糖。 |
| 2 | DM r0 | P009 → P004 | （拨着算盘）秀娘，练完这一趟，咱俩的账就平了。 |
| 3 | public r0 | P002 | （刨子推过木料，卷起薄薄一层刨花）慢点来，木头不骗人。 |

> **【判断 · 仅描述】** 样本层最直观的差别是**括号旁白消失**（A1 全批 0 条括号块），台词直接成句。同时可见两个**待复核的副作用信号**：① 第 1 条与第 3 条是同一场景的**近重复**表述（"减了点糖/少放了糖"、"看看合不合你口味/配茶正好"），与 L-6 反向上升一致；② 台词明显变短（A1 第 2 条 11 字，A0 同类 30+ 字）。**这两点是否算"自然"或"贫"需人读裁定，见 §4。**

---

## 4. 判定：**B —— 真实（改动确实生效）但有副作用**

> 裁定来源：`a1-quality-review`（project-recon 只读人读复核：A1 抽 20–30 条 + A0 抽 10–15 条），裁定 **B**；本节的量化部分作者已逐项复算（命令附在每条后）。

### 4.1 可写成存在性事实的部分（措辞从硬）

- **本批 124 条中括号类旁白出现 0 次**，且**九种形态全 0**：`（）` / `()` / `【】` / `[]` / `『』「」` / `*动作*` / `——` / `｢｣` / `名字+冒号+括号`。对照 A0（686 条）：`（）` **590**、`『』「」` 2、`——` **251**、`名字+冒号+括号` 28，其余 0。
  ```bash
  python3 - <<'PY'
  import sys, re; sys.path.insert(0,'tools/d5'); import dialogue_metrics as dm
  pats={'（）':r"（[^（）]*）",'()':r"\([^()]*\)",'【】':r"【[^【】]*】",'[]':r"\[[^\[\]]*\]",
        '『』「」':r"[『』「」]",'*动作*':r"\*[^*]+\*",'——':r"——",'｢｣':r"[｢｣]",
        '名字+冒号+括号':r"[\u4e00-\u9fa5]{1,4}[：:][（(]"}
  for tag,p in (('A0','v2/evidence/run_d2_after_n16_seed42/run.jsonl'),
                ('A1','v2/evidence/run_a1_wording_n4r60_seed42/run.jsonl')):
      recs,_=dm.read_run(p); ms=dm.extract_messages(recs)
      print(tag,len(ms),{k:sum(1 for m in ms if re.search(v,m['body'])) for k,v in pats.items()})
  PY
  # A0 686 {'（）': 590, '()': 0, '【】': 0, '[]': 0, '『』「」': 2, '*动作*': 0, '——': 251, '｢｣': 0, '名字+冒号+括号': 28}
  # A1 124 {'（）': 0, '()': 0, '【】': 0, '[]': 0, '『』「」': 0, '*动作*': 0, '——': 0, '｢｣': 0, '名字+冒号+括号': 0}
  ```
- **0/124 的 95% 二项上界 ≈ 2.42%**（`rule-of-three` = 3/124）⇒ 只能写「**与本提示词约束一致**」。**不得**出现「彻底消除旁白」「旁白率 0%」。
- **无括号动作叙述命中 1/124**，经人读为**假阳性**（「老周，我不是要你放下地里的活…」——`放下` 是话题用词，不是动作叙述）⇒ 实质为 **0**。
- **L-4（第三人称自指）= 0**（来源 `v2/evidence/d5_metrics_a1.json` → `L_wording / L-4_third_person_self_rate`；复算见 §0.3 命令）。

### 4.2 trade-off（**本轮真正的结论**）

1. **台词被压短 39.9%**：`excl_paren` **45.828 → 27.540**（−18.29 字），p50 **41 → 19.5**，max **164 → 104**，stdev **24.32 → 19.69**；**≤12 字占比 3.6%（25/686）→ 12.1%（15/124）**。
   **按 agent 拆（mean 长度，同栏 `excl_paren` vs `excl_paren`）**：P001 **22.4 → 16.9**、P002 **16.5 → 17.3（+0.8，基本持平；A0 本已偏短）**、P003 **27.3 → 18.2**、P004 **62.7 → 52.3（仍最长）** ⇒ **4 个 agent 中 2 个明显压短（P001 −5.5、P003 −9.1），且 A1 侧三人集中在 16.9–18.2 同一档**。这不是"整体略短"，而是**多数 agent 落到同一档**。
   > ⚠️ **勘误（`r9-erratum`）**：本条初版把 A0 侧写成了 `all` 栏（30.7 / 27.2 / 32.4 / 81.0）而 A1 侧是 `excl_paren`，属**跨栏对比**（违反纪律 #2），且与本条所贴复算脚本的输出不一致。已改为同栏并收窄结论（由"3 个被压到 ~17 字"改为"2 个明显压短 + A1 三人同档"）；总均值、≤12 字占比、通道占比等其余数据不受影响，裁定 B 不变。
   ```bash
   python3 - <<'PY'
   import sys, re; sys.path.insert(0,'tools/d5'); import dialogue_metrics as dm
   from collections import defaultdict
   PAREN=re.compile(r"（[^（）]*）|\([^()]*\)")
   for tag,p in (('A0','v2/evidence/run_d2_after_n16_seed42/run.jsonl'),
                 ('A1','v2/evidence/run_a1_wording_n4r60_seed42/run.jsonl')):
       recs,_=dm.read_run(p); ms=dm.extract_messages(recs)
       lens=[len(PAREN.sub("",m['body'])) for m in ms]
       by=defaultdict(list)
       for m in ms: by[m['from']].append(len(PAREN.sub("",m['body'])))
       print(tag,'n',len(lens),'mean',round(sum(lens)/len(lens),2),
             '<=12',sum(1 for l in lens if l<=12),f"{sum(1 for l in lens if l<=12)/len(lens)*100:.1f}%",
             {k:round(sum(v)/len(v),1) for k,v in sorted(by.items())})
   PY
   ```
2. **重复形态迁移，L-6 上升不是波动**：A0 高频 8-gram 是**旁白动作**（`（把铁锤往砧上一` 12 次、`把铁锤往砧上一搁` 12 次、`把刚出炉的桂花糕` 7 次）；A1 变成**台词客套**（`你尝尝这个新烤的` 5 次、`个新烤的枣泥酥，` 4 次）。精确重复原文如 `老周，这点菜你收着，自家地里刚摘的。` ×4、`不用不用，你拿回去，我地里啥都有。` ×3。
3. **内容通道被替换**：A0 的 45.8 字（`excl_paren`）里，括号占全部字符 **21.4%**（8,560 字，均值 **12.48 字/条**），含**具体物件名词 73.3%**、客套词仅 **13.7%**；A1 的 27.5 字里，**动作通道 0.8%**、**具体物件 58.9%（−14.4 pp）**、**客套/推让/表态 44.4%（×3.2）**。（通道占比为人读标注统计，口径属 `a1-quality-review`；括号字符总量作者已复算：A0 `8560/39998 = 21.4%`、A1 `0/3415 = 0%`。）
> **本节所有长度对比均同栏（`excl_paren` vs `excl_paren`），`all` 栏仅作总均值对照（§2.2）。** 按 agent / topic / 渠道的任何 L-1 拆分，一律同栏计算。

4. **结论句**：**被砍掉的是「人物正在做什么、眼前有什么」这条具体性通道，腾出的篇幅被「送礼—推让—表态」的客套循环占据**。因此本轮**不能声称「更像人说话」**，只能说「**形式上更干净、但具体性下降、客套密度上升**」。

### 4.3 边界（与 §5 一致，此处再压一遍）

- 一切比率标 **`probe`**：MSG 124 < 150，准入 `REJECTED`，属**规模性门禁结果、非事故**。
- 两臂规模 **686 vs 124 不可比**，所有差异**只作方向性**。
- 已知项登记（**非本轮新问题**）：`ctx.topic` 原样漏进正文 **A1 5.65%（7/124，`mentorship` 4 次、`whisper` 3 次）** vs A0 3.94%（27/686）——在口语短句约束下更显眼。

---

## 5. 可信边界与不可比说明

1. **规模不可比**：A0 = 16×84（686 条 / 206 线程），A1 = **4×60（124 条）**，分母差 >30% ⇒ 率值不可比，**本报告不写效果结论、不做显著性断言**。
2. **准入 `REJECTED` 是规模性门禁**：唯一阻断项 `B-15_msg_volume` 124<150，与 D8 两臂同因；**不是事故、不是数据缺陷**。所有措辞层读数按 `probe` 对待。
3. **白盒自检的适用范围**：`v2/evidence/d4_prompt_diff_a1.txt` §5 的自检用 `life.llm.RuleBasedLLM`（`provider=None`），它只证明**提示词装配路径正确、零网络零计费、旧中性指令被替换**，**不证明真 LLM 下的行为**；真 LLM 行为只能由本批 `obs llm-cost` 验真读数与 run 日志证明。
4. **零事件 = 上界，不是点估计**：L-2/L-3 的 0/124 只能给 `rule-of-three` 95% 上界 ≈2.4%，**不得**读成"降到 0%"或"完全消除"。
5. **L-7 不可跨分母比**：335/686 与 51/124 分母不同，**不作差量解释**；同一批内 L-7 只用于自比。
6. **judge 侧指标不适用**：D9 已实测 `judge` 提示词两臂逐位相同（不吃正文）⇒ 由 `judge` 派生的指标（含 F-7 越界提及、关系变动判定）**不能**用来衡量措辞改造；`describe` / `reflect` / `dialogue` 派生指标不受此限。
7. **无噪声带**：本轮未做同分母 bootstrap，故所有"变化"只能写方向性。
8. **耗时口径**：`meta.duration_sec=482` 是整进程墙钟；`host.log` 内 `[life] … seconds=` 为内核自报耗时，两者不可混用。

---

## 6. 遗留项

1. **规模补齐**：A1 需一次 **n16r84 / seed42** 复跑才能与 A0 同规模对照（成本量级参考 A0 批 ≈3000 s、3403 次调用），否则 R9 永远只能停在"方向性"。
2. **长度代价待评估**：台词 mean 58.3→27.5（−53%）。是否牺牲信息量/生活细节，需要人读 + 与 R4 的 F 系列口径对齐后再定；本报告只登记，不作判断。
3. **短句化的副作用待验证**：L-6（0.099→0.129）、L-5（0.019→0.024）反向上升，假设是"句子变短 ⇒ 更易撞模板/重复"，需专门设计一轮（例如短句 vs 中句同长度对照）验证。
4. **判据缺口**：若 `a1-quality-review` 判"度量失真"，需为"叙述插入语/破折号替代括号"补一条判据（当前 L-2/L-3 只识别括号块）。
5. **本臂未动的变量**：`reply_window_rounds`（保持 4）、slot 配额、`max_turns`、感知窗 ⇒ 与 R8 的密度结论正交，不得把两轮读数合并解释。
6. **下一轮应跑 A1′（松一格的措辞臂）**：把提示词改成「**可顺口带出你手上的活或眼前的场景，但不要用括号/方括号/星号写动作神态心理旁白**」——即**保留具体性通道、只砍旁白形式**。执行顺序建议先 **n4r60 筛**（约 482 s、272 次调用量级），方向成立再上 **16×84**（A0 量级 ≈3000 s / 3403 次调用）。**目的：避免"砍形式"做成"砍具体性"**，这正是本轮 B 判定暴露的问题（§4.2 第 1、3 条）。
7. **判据缺口**：`L-2/L-3` 只识别括号类形态；若未来出现"叙述插入语/破折号替代括号"的新规避形态，需补一条判据（本轮九形态审计未命中，但形态清单应随用随扩）。

---

## 7. 证据索引

> 固定列：`# | 结论 | 层级 | 来源（仓库相对路径） | sha256 | sha8 | 复现`

| # | 结论 | 层级 | 来源 | sha256 | sha8 | 复现 |
|---|---|---|---|---|---|---|
| 1 | A1 臂身份与规模：`code_sha = code_sha_end = a637371`、n=4、rounds=60（`rounds_effective=60`）、seed=42、events=9940、`run_bytes=4,749,329`、`degraded_calls=0`、`fallback_detected=false`、482 s | 事实（run 元数据） | `v2/evidence/run_a1_wording_n4r60_seed42/meta.json` | `v2/evidence/run_a1_wording_n4r60_seed42/meta.json` = `beba68408b287ff7…` | `beba6840` | `sha256sum v2/evidence/run_a1_wording_n4r60_seed42/meta.json`；`python3 -c "import json;m=json.load(open('v2/evidence/run_a1_wording_n4r60_seed42/meta.json'));print(m['code_sha'],m['n'],m['rounds'],m['seed'],m['events'])"` |
| 2 | **A1 源日志**：`run.jsonl` 全值 `ae969198feaefd1f69147001e027394d55527bd1a0e460ff654697bdc3b1559b`（4,749,329 B，`wc -l` **9,940** = `meta.events`）；四图文件名 sha8 = 此前 8 位 | 事实（数据源） | `v2/evidence/run_a1_wording_n4r60_seed42/run.jsonl`（**不入库**，`.gitignore:8 **/*.jsonl`；以 sha256 作引用凭据） | `ae969198feaefd1f69147001e027394d55527bd1a0e460ff654697bdc3b1559b` | `ae969198` | `sha256sum v2/evidence/run_a1_wording_n4r60_seed42/run.jsonl`；`wc -l …` |
| 3 | 真跑与成本验真：RC=0、`provider_guard.ok=true`、`{openai_compat:272}`、calls 272、cached 45、degraded 0 | 事实（验真） | `v2/evidence/run_a1_wording_n4r60_seed42/llmcost.json`、`v2/evidence/a1_llmcost_ae969198.txt` | `llmcost.json` = `709ce510a7ef12fb…`；`a1_llmcost_ae969198.txt` = `142039f13bbd5d46…` | `709ce510` / `142039f1` | `cd code && python3 -m obs llm-cost --log ../v2/evidence/run_a1_wording_n4r60_seed42/run.jsonl --require-provider openai_compat` |
| 4 | 措辞层读数（L-2/L-3 0/124、L-5 3/124、L-6 16/124、L-7 51/124；L-1 `excl_paren` 45.828→27.540） | 读数（`probe`） | `v2/evidence/d5_metrics_a1.{json,md}` | `53a10de3f03efe12…` | `53a10de3` | 见 §0.3；重跑产物与入库件**逐字节相同** |
| 5 | 改动面（名义双变量）：`code/life/agent.py` L1058 / L1069 两行 + `dialogue_threads.py` `reply_window_rounds` 2→4（后者惰性）；`prompt_sha` A0 `2cb2f5ba…`（`3ec85a0`）→ A1 `5186aa9a3db55de8` | 事实（代码） | `code/life/agent.py` @ `a637371`；`v2/evidence/d4_prompt_diff_a1.txt` | 源码随提交变动 | — | `git show --stat a637371`；`sha256sum code/life/agent.py`；`d4_prompt_diff_a1.txt` §3/§4 |
| 6 | A1 四视图真实截图（chat 1400×900 / rhythm 1300×1050 / spread 1300×900 / 600 600×900） | 事实（证据） | `v2/evidence/a1_shots/run_a1_wording_n4r60_seed42-{chat,rhythm,spread,600}-ae969198.png` | chat `0e05129bb9779691…`；rhythm `7c3d7eea9c1f1306…`；spread `c3fc91ec399f9a70…`；600 `13ce8b1953fa1db3…` | `0e05129b` / `7c3d7eea` / `c3fc91ec` / `13ce8b19` | 渲染命令见 §3.1；日志 `a1_shots/render.log`（`6ec172f2`） |
| 7 | 起跑前置（`pgrep` 空、SID/PGID 分离 PASS、工具层 300 s 超时≠跑批失败） | 事实（时序） | `v2/evidence/a1_launch_evidence.txt` = `8379d0447b5becc9…` | `8379d044` | `cat v2/evidence/a1_launch_evidence.txt` |
| 8 | **A0 基线读数**（L-2 562/686、L-3 590/686、L-6 68/686、L-7 335/686、L-1 `excl_paren` 45.828/`all` 58.306） | 读数（`evidence`） | `v2/evidence/d5_metrics_d9a0.{json,md}`（重跑与入库件逐字节相同） | `a2b55e21831a65ae…` | `a2b55e21` | 见 §0.3 |

> 两臂 `run.jsonl` 均按仓库惯例**不入库**（`.gitignore` 排除），入库的是元数据、验真原件与读数产物；完整 sha256 已在 #2 与 §0.1 给出全值。
