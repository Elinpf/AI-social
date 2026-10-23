# `d12i_readings_20261024/` —— D12-I 收批后读数复算 + 真实截图落盘

> 执行：metrics-and-render-owner｜2026-10-24｜**纯只读、零跑批、零 LLM、未 commit**
> **Leader 04:1x 裁定**：本轮不提交 `run.jsonl`；`S_ext` 已入主树；4 张截图均为**终态回放**。
> 本目录**只出数与出图**，不含任何效果判读（达标/有效/作废等判定不在此处，属下一环节）。
> 一键复算：`bash tools/metrics/d12i_readings_recompute.sh`（在主 checkout 仓库根执行）

## 0. 这份落盘件解决什么

1. 把 D12-I 臂的形态读数、形态闸三时点读数、选优机制读数、重复度三口径、LLM 成本
   全部变成**「指标名 + 分子/分母 + 口径名 + 来源命令」**六元组，第三方可逐条复算；
2. 把「相近但不同的量」**并列输出、名字带口径后缀**（raw/norm、strict 名字集 16 vs 20、
   shingle vs sha、raw len vs excl len、argmin_unique vs not_all_equal），禁止二选一；
3. 给出 **4 张真跑真渲染截图**，每张可溯源到「run 目录 + 渲染命令 + 日志 sha256」，附 `render.log`。

## 1. 批次身份复核（`identity_attest.json`，5 项检查全过）

| 量 | 实测 | 声明/期望 | 一致 |
|---|---|---|---|
| `sha256(run.jsonl)` | `72c0ca97fe6e38632f67e3b2810c65126c0d15d296d068b521dfbb45c8f5d0c4` | 任务给定同值；`meta.run_sha256` 与 `meta.derived_from_log_sha256` 亦同值 | ✅ 三方一致 |
| 行数 `wc -l` | `117724` | 任务给定 `117724`；`meta.events` = `meta.wc_l` = `117724` | ✅ |
| 字节 | `58438033` | `meta.run_bytes` = `58438033` | ✅ |
| 收批 rc | `0` | `run_batch.rc` = `0` | ✅ |
| `meta.code_sha` | `ca76ceb2e6ebfbe99450389186307c625e911974` | （写 meta 那一刻的 worktree HEAD） | — |
| worktree 当前 HEAD | `a323e28bb5bd4138a0bb853bfc19a286291eec55`（分支 `feat/d12i-aligned`） | — | 与 `code_sha` **不同**，属正常：收批后该分支又前进了 3 个 commit（`79e8ae0` 收批证据、`9941e48` 只读工具、`a323e28` 复算记录） |
| 主 checkout | `master` @ `d0a320b667e91792c5bb4a10047daeb89f88365d` | — | 本目录所在树 |

复算命令：

```bash
sha256sum .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl
wc -l     .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl
python3 -c "import json;m=json.load(open('.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/meta.json'));print(m['code_sha'],m['events'],m['wc_l'],m['run_bytes'],m['run_sha256'])"
git -C .worktrees/d12i-aligned rev-parse HEAD
```

## 2. 形态读数（`form_metrics_full.json`，全批 510 MSG）

来源命令（一条命令全部复现，`--no-timestamp` ⇒ 数值可逐位比对）：

```bash
python3 tools/metrics/form_metrics.py \
  --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --code-dir .worktrees/d12i-aligned/code \
  --out v2/evidence/d12i_readings_20261024/form_metrics_full.json \
  --batch-id D12-I --no-timestamp
```

| 指标（口径后缀） | 分子 | 分母 | 读数 | 口径/判据身份 |
|---|---|---|---|---|
| `L-3_paren_block_any`（L-3 族·**any** 口径，判据） | 369 | 510 | `0.723529` | 正文命中任一括号块（`PAREN_ANY_RE`）的 MSG 占比；闸线 ≥0.55 |
| `paren_head_rate`（L-3 族·**起头** 口径，参照） | 338 | 510 | `0.662745` | 正文**以 `（`/`(` 开头**的 MSG 占比（旁白起头）；与上一行**相近但不同**，不得互换 |
| `addr_head_strict_personas20` | 134 | 510 | `0.262745` | **判据唯一口径**（D12H-amendment3 §C，`config/personas.json` 20 个 `display_name`） |
| `addr_head_loose` | 144 | 510 | `0.282353` | **上界参照**（首句 2–6 字以 `，/：` 收尾；下界 1 会给 487/510=0.954902） |
| `addr_head_pfx2` | 116 | 510 | `0.227451` | **下界参照**（名字在第 0 位、后缀 ≤2 字，逐字复用 `shape_gate.is_addr_head`） |
| `addr_head_pfx2_plus` | 116 | 510 | `0.227451` | 参照量（标点集扩 `、` `——`） |
| `addr_head_alias` | 0 | 510 | `0.0` | 只读指示量，不进判定 |
| `L-1_len_p50_raw` | — | 510（分位分母） | `70.0` | 含括号块的正文字数 p50 |
| `L-1_len_p50_excl_paren` | — | 510（分位分母） | `55.0` | 去括号块后 p50（**F3 判据口径**） |
| `L-7_dup_ngram8_rate`（**norm8** 口径） | 317 | 510 | `0.621569` | `normalize_body` 后 8-gram shingle（**跨批不可比**）；本批索引 sha256 `37ca0729e439df75faaa97c42f38133a0e51c950261b9166515c23d125739869` |
| `L-7_raw8_shingle`（**raw8** 口径，并列件） | 368 | 510 | `0.721569` | **不归一**原文 8-gram shingle；见 §4 `dup_calibers.json`（仓内无现成出数器，本目录新增 `tools/metrics/d12i_dup_calibers.py` 现算） |

## 3. 形态闸三时点（`shape_gate_points.json` / `shape_gate_full.json`）

来源命令：

```bash
python3 tools/d12h/shape_gate.py --log <run.jsonl> --points 20,30,60 \
  --code-dir .worktrees/d12i-aligned/code --out-json v2/evidence/d12i_readings_20261024/shape_gate_points.json
python3 tools/d12h/shape_gate.py --log <run.jsonl> \
  --code-dir .worktrees/d12i-aligned/code --out-json v2/evidence/d12i_readings_20261024/shape_gate_full.json
```

（`metrics` 来源 `tools/d9/arm_state_check.py`，`metrics_impl_sha256 = 9e11701f60fcddefaff8e14001e57b056d7baf5c22534d88947df9d5d765dc85`；名字集 `build_world(seed=42,n=16)._peer_names`，**16 个**）

| 时点 | n_bodies | `paren_rate`（F1） | `shape_gate.addr_head_strict`（F2，**历史字段名，实为 pfx2 口径·16 名**） | `len_p50_excl`（F3） | `len_p50_raw`（仅展示） |
|---|---|---|---|---|---|
| `<20` 轮 | 174 | `0.609195`（+3.08pp PASS） | `0.264368`（−10.03pp PASS） | `56.0`（+5.66% PASS） | `65.5` |
| `<30` 轮 | 246 | `0.678862`（+10.05pp FAIL） | `0.231707`（−13.30pp PASS） | `59.0`（+11.32% FAIL） | `69.0` |
| `<60`＝全 run | 510 | `0.723529`（+14.51pp FAIL） | `0.227451`（−13.72pp PASS） | `55.0`（+3.77% PASS） | `70.0` |

**口径性质声明**：本表是 `shape_gate` 的**过程闸/形态闸读数**（`--points 20,30,60` 为 1/3 期与收尾的时点核），**不是**本批的效果判读。表内 `FAIL`/`PASS` 只是该闸自身的越界标记；本批的判定（是否作废 / 形态漂移结论）**已由 `v2/evidence/d12i_result.md` 给出，本目录不另出判定、不重复下结论**。

收尾全 run（`shape_gate_full.json`，与上表 `<60` 行同值）：`id_leak_rate` = `0.003922`（2/510）、`dup_exact_rate` = `0.092157`（47/510）、`paren_head_rate` = `0.662745`（338/510）、`addr_head_upper_rate` = `0.235294`（120/510，**正则上界仅参照**）。

## 4. 双口径并列（**相近量并列、字段名混口径的如实标注**）

### 4.1 `addr_head` 族：**字段名为历史名，实为 pfx2**

> **重要标注（不改代码，只如实注明）**：`tools/d12h/shape_gate.py` 输出的字段名 `addr_head_strict` 是**历史名**，
> 其实现 `is_addr_head()` 的语义是「**显示名在第 0 位 + 后缀 ≤2 字 + 以 `，/：` 收尾**」，即 **pfx2 口径**，
> **不是** `d12h_verdict_amendment3 §C` 冻结的 strict 口径。因此同一批同一指标出现两个数：

| 口径名（带后缀） | 名字集 | 分子/分母 | 读数 | 出处（脚本字段名） |
|---|---|---|---|---|
| `addr_head_pfx2_gate16` | `build_world(seed=42,n=16)._peer_names` = **16 个**镇上居民名 | **116/510** | `0.227451` | `shape_gate.py` 字段 `addr_head_strict`（**历史名，实为 pfx2**） |
| `addr_head_pfx2` | 同 16 名（`form_metrics` 内嵌逐字副本，`vendor_check=identical`） | **116/510** | `0.227451` | `form_metrics.py` 字段 `addr_head_pfx2`（**与上一行逐位相同**，互为交叉验证） |
| `addr_head_strict_personas20` | `code/config/personas.json::display_name`（去 `青溪镇·`）= **20 个** | **134/510** | `0.262745` | `form_metrics.py` 字段 `addr_head_strict`（§C **冻结判据口径**） |
| `addr_head_loose` | — | 144/510 | `0.282353` | 上界参照（首句 2–6 字以 `，/：` 收尾；下界取 1 为 487/510=0.954902） |
| `addr_head_upper_rate` | — | 120/510 | `0.235294` | 正则上界参照（`^[\u4e00-\u9fa5]{1,4}[，,：:]`，**仅参照**） |

> **必须并列读的三件事**：①`addr_head_pfx2` = **116/510 = 0.227451**、`addr_head_strict_personas20` = **134/510 = 0.262745**，**两者差 3.53pp（18 条消息，0.035294），引用时不得互代**；
> ②`shape_gate` 的 F2 判定只在 **pfx2 口径**内自洽（其 T5 基线 `0.3647` 也是同一脚本在 T5 日志上实算的 pfx2 值），
> 因此「D12-I F2 PASS」这句话的完整口径是 `addr_head_pfx2`，**不能**被读成 strict 口径的结论；
> ③`addr_head_upper_rate`（0.235294）是正则上界，**永远不作判据**。

### 4.2 重复度四口径并列（`dup_calibers.json`）

命令：
`python3 tools/metrics/d12i_dup_calibers.py --log <run.jsonl> --out v2/evidence/d12i_readings_20261024/dup_calibers.json`

| 口径名 | 定义 | 分子/分母 | 读数 | 跨批可比 |
|---|---|---|---|---|
| `raw_exact` | 原文 body 完全相同（sha/exact 语义） | 47/510 | `0.092157` | 可 |
| `norm_exact` | `d5.normalize_body()` 后完全相同 | 47/510 | `0.092157` | 可 |
| `norm8_shingle` | **归一后** 8-gram 片断重合（= d5 `L-7` 分子） | 317/510 | `0.621569` | **不可** |
| `raw8_shingle` | **不归一** 原文 8-gram 片断重合 | 368/510 | `0.721569` | **不可** |

> 四者**分子不同、互不替代**：`exact` 与 `shingle` 是两个问题（「整句一模一样」vs「片断重合」）；
> `raw8`(368) 与 `norm8`(317) 差 51 条消息，正是归一化（去标点/空白）吃掉的那部分重合。
> 跨批只能比 `raw_exact` / `norm_exact`；**L-7 的 `norm8` = 317/510 = 0.621569、`raw8` = 368/510 = 0.721569，两值差 10.0pp（51 条消息），引用时必须带口径后缀，不得互代**，且两者都只能与本批自身索引一起读。

自洽检：`norm8_shingle` 分子 317 与 `form_metrics_full.json` 的 `L-7.numerator` 相等（脚本内置校验，不等则 rc=3）；
`raw_exact` 47 与 `shape_gate_full.json` 的 `dup_exact_rate = 0.092157`（×510 = 47）一致。

## 5. 选优机制（`selector_stats_full.json`，510 条 MSG 的三候选）

命令：`python3 .worktrees/d12i-aligned/tools/d12i/selector_stats.py --log <run.jsonl> --key d12i --out-json v2/evidence/d12i_readings_20261024/selector_stats_full.json`

| 口径 | 分子/分母 | 读数 |
|---|---|---|
| `argmin_unique`（**判据**：最小值索引唯一） | 480/510 | `0.941176` |
| `not_all_equal`（**参照**：分数不全同，不得当 argmin 用） | 503/510 | `0.986275` |
| `all_zero` | 0/510 | `0.0` |
| `three_candidates_shingle_identical` | 3/510 | `0.005882` |
| `contains_na` | 0/510 | `0.0` |
| `picked_distribution` | — | `{0:167, 1:174, 2:169}` |
| `scores` mean/median/max | — | `0.261825` / `0.211268` / `1.0` |

## 6. LLM 成本验真（`llm_cost.txt` + `llm_cost.rc`）

命令（**从 `code/` 执行**，与 `tools/d2/run_batch.sh:82` 同写法）：

```bash
cd code && python3 -m obs llm-cost \
  --log "$(pwd)/../.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl" \
  --require-provider openai_compat
```

- **rc = `0`**（`llm_cost.rc` 内容 `0`），stdout 原样落盘 `llm_cost.txt`（1165 字节，单行 JSON，未改写），stderr 为空（`llm_cost.stderr.txt` 0 字节）。
- `provider_guard.ok` = **`true`**，`problems` = `[]`，`expected` = `openai_compat`。
- `engine_log.by_provider` = `{"openai_compat": 4200}`（**无 mock 混入**）。
- `engine_log.total`：`calls 4200` / `cached 1583` / `degraded 0` / `thinking 668` / `tokens_in 516559` / `tokens_out 363620` / `tokens_total 880179`。
- 分用途 calls：`dialogue 1832`、`importance 1523`、`judge 668`、`reflect 112`、`negotiation 49`、`plan 16`（合 4200）。
- 与 `meta.json` 对账：`llm_calls 4200` ✅、`llm_cached 1583` ✅、`degraded_calls 0` ✅、`provider {"openai_compat":4200}` ✅、`fallback_detected false` ✅。

## 7. 真实截图（`shots/`，4 张，真跑真渲染）

渲染链：`run.jsonl → gen_threads.py → threads_D12-I.json → 临时静态服务（symlink code/frontend，sample/ 只放本批 threads.json）
→ code/frontend/tools/shot.py（Playwright + Chromium 现场截图）→ PNG`。**未在 `code/` 下写入任何文件**。

一键命令（`render.log` 即本次完整 stdout/stderr，74 行）：

```bash
python3 tools/metrics/render_shots_extra.py \
  --run-dir .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42 \
  --batch-id D12-I --outdir v2/evidence/d12i_readings_20261024/shots \
  --views chat,rhythm,spread,chat_thread --timeout 180 2>&1 | tee v2/evidence/d12i_readings_20261024/shots/render.log
```

（`render_shots_extra.py` 是 `render_shots.py` 的**零改动包装器**：只补登记 `spread` 与 `chat_thread` 两个
`dialogue.html`/`dialogue.js:184,469` 本来就支持的视图；既有出图器一字未改。）

共性：`run_sha256 = 72c0ca97…`；`threads_D12-I.json` sha256 = `312c4d7ca6cd97ad1037a45e233c81fcf1b983804273ee99a125c7ea8c5a1655`（6053846 字节 / 169 线程 / 510 消息 / 88 多轮）。四张图 `rc` 全 `0`，像素自检全 `OK`。

**截图口径（逐张）**：
- 视图：`chat`＝对话流（`sort=turns`）、`rhythm`＝节律·串门（`view=rhythm`）、`spread`＝闲话怎么传开（`view=spread`）、`chat_thread`＝单线程聚焦（`thread=TH-P004-P002-0`，6 轮）。
- 成功判据（两条同时满足）：① `shot.py` 退出码 `rc=0`（`render_report_D12-I.json` 的 `views[].rc`）；② 像素自检 `status=OK`，判据 `distinct_colors ≥ 200 且 top_color_frac ≤ 0.99`（不沿用 `shot.py` 的单色判据——该判据对深色 `dialogue.html` 会假红）。每张的 `distinct_colors / top_color_frac / non_bg_frac` 见上表与 `render_report`。
- 时点性质：**终态回放**（`still=1`，D12-I 已收批 `rc=0`、日志 sha256 与 `meta` 三方一致），**不是运行中快照**——四张图均由已收批的 `run.jsonl` 派生，页面底部进度为 `510 / 510`（回放至末态）。

| PNG | 视图 | 尺寸 | 字节 | sha256 | 像素自检（色数 / 最大单色 / 非背景） |
|---|---|---|---|---|---|
| `D12-I-chat-72c0ca97.png` | 对话流（`sort=turns`） | 1400×900 | 290381 | `d4883c4374886370141cff7931f9b1b171b9eb6d6e7efac273e4c75567eae5af` | OK：24216 / 14.17% / 58.20% |
| `D12-I-rhythm-72c0ca97.png` | 节律·串门（`view=rhythm`） | 1300×1050 | 282110 | `2c942d858e917663ea1406819af1219bff72ad8c373564f212b35e2ebb1c7d8f` | OK：22315 / 26.20% / 47.43% |
| `D12-I-spread-72c0ca97.png` | 闲话怎么传开（`view=spread`） | 1400×1000 | 178501 | `9f0a6bd660c15d691dd7e86e790bc7ae4c72758781f178805d36bf7ab84827f2` | OK：15623 / 56.83% / 17.70% |
| `D12-I-chat_thread-72c0ca97.png` | 单线程聚焦（`thread=TH-P004-P002-0`，6 轮） | 1200×1000 | 301761 | `f14fbe84c4eed8974f6ce177533f78170fb73df9f8c9c8c40ef9e36b4f1ebc90` | OK：24951 / 11.07% / 53.17% |

人工读图复核（两轮，均为真实页面，非空白/错误页）：

- `chat`：标题「青溪镇·对话观看台」，元数据条显示 `D12-I · sha 72c0ca97fe6e · provider openai_compat · seed 42 · 事件 117724 · 消息 510 · 线程格式 explicit · meta 已对齐`；可见 5天×4时段热力网格与一条 6 轮线程（老石 ↔ 秀娘）。
- `chat_thread`：单线程卡片 TH-P004-P002-0，可见第 1–4 轮完整对话正文（枣泥酥/刨木条等生活细节），标签 `6 条 / 6 轮`。
- `spread`：**真实渲染成功，但该视图在 D12-I 批上无数据可渲染（空态）**——不是渲染失败。判定依据（三项计数全为 0，可复算）：
  1. `shots/threads_D12-I.json` 的 `spread.ref_edges` = `[]`（长度 **0**，即 0 条可匹配转述边）、`spread.echoes` = `[]`（长度 **0**，派生口径的「同一句话被第二个人说出」组数 0）；
  2. 同文件 `stats.ref_edges` = **`0`**、`stats.echo_groups` = **`0`**（`gen_threads` 现算统计）；
  3. 日志本体侧：510 条 MSG 中带**非空 `payload.refs`** 的 = **`0`** 条。
  复算命令：`python3 -c "import json;d=json.load(open('v2/evidence/d12i_readings_20261024/shots/threads_D12-I.json'));print(len(d['spread']['ref_edges']),len(d['spread']['echoes']),d['stats']['ref_edges'],d['stats']['echo_groups'])"` → 输出 `0 0 0 0`；MSG refs 计数写在同一目录的 §7 复算段（`with_refs: 0`）。
  日志侧 refs 计数（在仓库根执行，输出 `510 0`）：
  ```bash
  python3 -c "import json;p='.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl';\
  ms=[json.loads(l) for l in open(p,encoding='utf-8') if l.strip()];\
  ms=[r for r in ms if str(r.get('type','')).startswith('MSG')];\
  print(len(ms), sum(1 for r in ms if (r.get('payload') or {}).get('refs') or r.get('refs')))"
  ```
  ⇒ 页面上两张卡片显示的就是脚本写入的显式空态说明（原文：「本批日志里 refs 全为空……这里显示空态，不用相似度硬凑」）。**在图注里必须写成「该视图在 D12-I 批上无数据可渲染」**，不得写成「渲染失败」。

## 8. 残留限制（必须与上面所有读数同屏）

1. **日志本体未入库**：58,438,033 字节的 `run.jsonl` 仍只在 `.worktrees/d12i-aligned/…`，未复制进主树、未 `git add`
   ⇒ 远端 clone 只能核对 sha256 是否与你手上那份相符，**无法完全复算**。
2. **PNG 非逐位确定**：同一渲染链首轮 `chat` = `7cf10530…`、`rhythm` = `09142166…`，第二/三轮均为 `d4883c43…` / `2c942d85…`
   （`spread` 三轮完全一致）。⇒ 图片指纹以本目录 `render_report_D12-I.json` 与 `SHA256SUMS` 为准，
   重跑可能出**不同 sha 的等价图**，属渲染层非确定性，不是换图。
3. `spread` 视图在本批是**空态**（`refs` 全空，`ref_edges=0`），它证明的是「页面能渲染 + 本批无转述边」，不证明「有转述链」。
4. `addr_head_strict` 有 16 名/20 名两套名字集（§4），任何引用必须带后缀。
5. `L-7` 的 8-gram 索引是本批私有的（`37ca0729…`），其数值**不得跨批做差当效果量**。
6. 本目录**未 commit / 未 push**（冻结期，提交由 report-writer 按 pathspec 执行）。
7. 本目录 `README.md` 自身的 sha256 见 `SHA256SUMS`（自指不写死）。

## 8.5 `S_ext` 参照语料已入主树（证据链修复）

`overlap_frac` 主判据依赖的外部固定语料已从分支逐字节复制进主树：

| 项 | 值 |
|---|---|
| 源 | `.worktrees/d12i-aligned/v2/evidence/d12i_external_shingles_4gram.json` |
| 目标 | `v2/evidence/d12i_external_shingles_4gram.json`（同路径同文件名） |
| 文件 sha256（两边实测相同） | `f75ebb3eb4d81b85a29b6012226220d3020dd28d95859b1d17ce47ca0a1e12f0`（与 `v2/evidence/d12i_result.md` ①表所记一致 ✅） |
| 字节数 | `408250`（`cmp` 校验逐字节相同） |
| `content sha`（`sorted(shingles)` 换行拼接后 sha256，本目录重算） | `16754109244fbe490aafc85932fb580513b5b12b51133e6a94e9ceb17bbe246c`（与 result.md 所记一致 ✅） |
| 规模 | `16973` 个 4-gram shingle |

⇒ **`S_ext` 已入主树 ⇒ `overlap_frac` 主判据在 master 上可复算**（不再依赖 worktree 是否存在）。

**边界写死（决定报告限定语，勿越界表述）**：`S_ext` 入主树**只去掉「参照系缺失」这一项**。**从零重建 `S_ext`** 仍需两样本仓库拿不到/不在主树的东西：
① T5 `round<40` 的来源日志（落点 `.worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42/run.jsonl`，受 `.gitignore` 的 `**/*.jsonl` 约束**不入库**）；
② `v2/evidence/form_metrics/d12i_receipt_README.md` 里记载的重算命令（重建脚本入口）。
因此：**master 上可做的是「验 sha 一致 + 按 receipt 命令复算」，不可做的是「从零重建 `S_ext`」**——本行**不得**被转写成「已完全可复算」。
复制命令（幂等、只这一件）：

```bash
cp .worktrees/d12i-aligned/v2/evidence/d12i_external_shingles_4gram.json v2/evidence/d12i_external_shingles_4gram.json
sha256sum v2/evidence/d12i_external_shingles_4gram.json   # f75ebb3e…
```
**未复制 `run.jsonl`**（`.gitignore` 忽略 `**/*.jsonl`，且 `.git` 已 478M）。

## 9. 落盘清单

| 文件 | 说明 |
|---|---|
| `identity_attest.json` | 批次身份 + 5 项检查 |
| `form_metrics_full.json` | 形态读数（9 项，六元组） |
| `shape_gate_points.json` / `shape_gate_full.json` | 形态闸三时点 / 收尾 |
| `selector_stats_full.json` | 选优机制（argmin_unique vs not_all_equal 并列） |
| `dup_calibers.json` | 重复度三口径并列 |
| `llm_cost.txt` / `llm_cost.rc` / `llm_cost.stderr.txt` | 成本验真原始输出 + rc |
| `shots/`（4 PNG + threads + render_report + render.log） | 真实截图及三件套 |
| `SHA256SUMS` | 以上全部文件的 sha256（逐件实测，`sha256sum -c` 全 OK），含登记的上游件 `../d12i_external_shingles_4gram.json` |
| （主树）`../d12i_external_shingles_4gram.json` | `S_ext` 参照语料，逐字节自 worktree 复制，`f75ebb3e…` |
