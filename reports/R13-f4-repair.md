# R13 · F-4「误会与和解」修复闭环：让闭环第一次在机制上可达且可审计（n16×60 seed42，F-4 ON vs OFF 基线）

> 性质：骨架先写、读数后填（§1–§3 与 §4 表头为跑批前写死；读数到手只填空、不改表头与口径）。
> 报告日期：2026-10-21 ｜ 团队轮次：ROUND-1 ｜ 维度：F-4（单一维度，不扩散）
> 代码 sha（本轮实现，跑批用树）：`6b7ae8a98694dd87d2ea26d14e663705eab69e92`（= 本臂 `meta.json.code_sha`，与 `code_sha_end` 相同；不使用当前 HEAD / master 顶替）
> 分支：`feat/life-f4-repair-1021`（从 `origin/master=021baec3` 切出）
> 本文件 commit sha：**待首版提交后回填（照 R12 先例）**。依据：R12 首版提交 `f899fe7` 时同样拿不到自身 sha，
> 做法是「首版提交后追加一个只回填这一行的 commit」——`f899fe7` 首版 → `44ab256` 回填，现文写作
> 「本文件 commit sha：`f899fe7…`（报告内容首版提交；本次回填见锚点行）」。本报告照此办理，回填由账本任务执行。
> 锚点行：`git log --format=%H -- reports/R13-f4-repair.md`

---

## 0. 摘要 TL;DR

**一句话**：本轮把「误会之后有没有和解」从**从未被打开过的机制**变成一条**单 env 开关、默认 OFF、可回滚**的
F-4 臂（`HITT_DIALOGUE_REPAIR=1`），并新增**零词表匹配**的可审计配对字段 `dialogue_repair`
（`rift_id` + `trigger_seq` + 本条 `seq`）；在 n16×60 seed42 上与已入库 OFF 基线（`c73bead6`）对读：

> ⚠️ **先读结论强度，再读数字**：本臂效果**判「不可判」**（理由见下：L-13 守卫被击穿）。
> 下表只登记**机制事实与事件数**，任何一行都**不能**被读成「对话变好」或「闭环被修复」。

**读数（零跑批复算，命令见 §4.3；分母一律标 `probe`，不给比率）**：

| 量 | OFF 基线 `c73bead6`（`895b9a3`） | F-4 ON 臂 `faeba580`（`6b7ae8a`） |
|---|---|---|
| 旧口径张力事件 | 22 | 14 |
| 旧口径闭环（宽松 / 严格） | 0 / 0 | **2 / 2**（同一句 `seq 30177`「别往心里去」被窗口重叠计两次，见 §4.5） |
| **人际冲突子集张力（主指标分母）** | **3** | **1** |
| **人际冲突子集闭环（宽松 / 严格）** | **0 / 0** | **0 / 0** |
| 可审计配对行 `dialogue_repair`（`v=f4/repair/1`） | 0 | **22**（13 个线程，`trigger_seqs` 全部 < 本条 `seq`） |
| L-13 内部 token 泄漏条数（守护） | 2 | **15**（`whisper` 14 / `scarce_buy` 1） |
| llm_calls / degraded | 2878 / 0 | 2872 / 0 |

⇒ **机制事实**：臂确实被打开（0 → 22 条可审计配对，旧口径闭环 0 → 2 且这 2 条**都有机制配对**）。
⇒ **目标判定**：主指标（人际冲突子集闭环）**0/1 vs 0/3，事件数、分母 <30、`probe`，不报比率**；
且 **L-13 从 2 涨到 15，击穿预注册守卫「L-13 条数不得高于基线」**，按 §3 降级规则
（`v2/evidence/f4_preregistration.md:90-94,105`「任一守卫恶化 ⇒ 结论写「不可判」」），
**本臂效果结论判「不可判」，只登记机制事实，不写「闭环被修复」**。

**已确证（可复算）**：

- 改造前闭环为 0 的**代码侧原因**是机制从未打开（`config/dialogue_repair.json:4` `enabled=false`、`run_batch.sh` 无 env 注入），
  三份已入库日志 `dialogue_rift` 命中 **0**（anchor §5）；
- OFF 路径**字节级未变**：同一 mock 世界改造前后 9262 条记录逐字节相同（sha256 `5b9d65fc…`），OFF 日志 `dialogue_repair` 命中 **0**。

**未达成（如实并列）**：

- 主指标分母极小：off 基线「人际冲突子集张力」仅 **3** 条、本臂 **1** 条（<30）⇒ 本轮**只报事件数、不报比率、不判效果**；
- L-13 内部 token 泄漏**本轮不修**（仍是既存缺陷）；**但本臂实测 15 条（基线 2 条），已击穿预注册守卫
  「L-13 条数不得高于基线」⇒ 按 §3 降级规则本臂效果**判「不可判」**（§4.3 守卫表）；改造前三臂为 2 / 14 / 9；
- 交叉表的「闭环 ∧ 机制配对」一格：**官方脚本因键口径 bug 恒为 0**，本报告改用独立复算（§4.5）后才得到 A=2 / C=10，
  原始脚本输出不能引用（明细与复算脚本见 §4.5）。

> **判读纪律（跑批前写死，非事后找补）**：跨批（OFF 基线跑在 `895b9a3`、本臂跑在新 sha）同 seed、同规模、不同时间窗，
> **无置信区间，不做显著性判定**；只允许写「方向」+ 并列守卫；**禁止写「生活气息改善」或「闭环被修复」**。
> OFF 与本臂的 OFF 路径等价性由 **mock 字节锁**证明（§4.1），**不由真跑批证明**（省预算）——任何差异只能归因到「F-4 臂打开」。

### 0.1 口径澄清（防串味）

- 本报告的「闭环」有**两个并列口径**：**宽松**（= R4 起沿用的 `tools/d5` 口径，`repair_lexicon` 任一词命中）
  与**严格**（剔除 anchor 确认的附和词 `我懂`）。两列**并列给出**，不替换历史口径，保证 R1–R12 可比。
- `dialogue_rift`（R6-T2，既有）与 `dialogue_repair`（R13，本轮新增）是两个不同字段：
  前者是「本条生成时我有哪些未了结旧账」，后者是「*本线程*旧账的 rift_id + 触发句 seq 配对」。二者都**不进 state_hash**。

### 0.2 证据分级与分母纪律

- 分母 <30 ⇒ 只报事件数，不报比率；分母 <68 ⇒ 标 `probe`；阈值来源见读数表 `band_source` 列。
- **三份已入库批（跑批前用于定标的臂）的张力「分母」分别是**：
  `off c73bead6` / `on 7de6a7be`（F-6 臂） / `dequp 6bf3ec88` → 旧口径 **22 / 15 / 15**、人际冲突子集 **3 / 0 / 1**。
  **这六个数全是分母，不是命中数，也不是比率**；`3 / 0 / 1` 对应的人际子集闭环分子是 `0 / 0 / 0`。
  分母为 0 的那一臂（`7de6a7be`）**连比率都不存在**，只能写「该臂无人际冲突子集张力事件」。
  复现：`python3 tools/f4/f4_subset_metrics.py --run off=… --run on=… --run dequp=…`（产物 `v2/evidence/f4_subset_baselines.json`）。
- **注意口径边界**：以上三臂**不含本轮的 F-4 ON 臂**。本轮两臂对照的分母是
  旧口径 **22 → 14**、人际子集 **3 → 1**（§0 TLDR 表 / §4.3），与上一行的「三臂」不是同一组数，**不得混引**。

### 0.3 结论 → commit 绑定表

| 结论 | 数据来源（文件名 + sha8） | 代码（commit） |
|---|---|---|
| 改造前闭环为 0 且机制从未打开 | `v2/evidence/f4_anchor_recompute.json` / `f4_anchor.md` | `e16dbd7` |
| OFF 路径字节级未变 | `tools/f4/f4_off_bytelock.py`（mock 9262 条，sha256 `5b9d65fc…`） | `6b7ae8a` |
| 本臂读数与可审计配对 | `v2/evidence/f4_subset_on_vs_off.json` (`6cf17808`) / `f4_audit_crosstab.json` (`10fb7fb0`) / 本臂 `run.jsonl` (`faeba580`) | `6b7ae8a98694dd87d2ea26d14e663705eab69e92`（该臂 `code_sha`） |

---

## 1. 本轮维度与为什么选它（单一维度）

### 1.1 缺口是可复算的（零跑批锚点，先做再花钱）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
bash tools/f4/f4_anchor_receipt.sh > v2/evidence/f4_anchor_receipt.txt 2>&1
```

| 量 | 既有报告（`R4-life-texture.md:59`） | 本轮独立复算 | 一致 |
|---|---|---|---|
| F-4 修复闭环（v0 锚点批） | `5 次张力中 0 次`（probe） | 三份已入库批（n16r60 seed42）：张力 22 / 15 / 15，闭环 0 / 2 / 0；**on 臂那 2 条经严格口径归零**（命中词为 `我懂`） | ✅ 缺口仍在 |

关键补充（R4 没写、本轮查出来的）：

1. `dialogue_rift` 三臂命中 **0** ⇒ 机制在这三批里**从未打开**；
2. 张力分子 19/22 只命中 `怕/累/疼` 等自述状态词，**分子本身有噪声** ⇒ 报告同时给「人际冲突子集」口径；
3. 修复词在 off/dequp 臂的张力线程里**此后一条都没再出现**（near-miss 分布 `{"none":22}` / `{"none":15}`）。

### 1.2 为什么这算「生活气息」

生活气息不是「话多」，而是**人与人之间有来回**：会闹别扭，也会把话说开。R4 §2 的判断原文是
「居民各自过日子过得还行，**彼此之间没有过日子的往来**」——F-3（情绪呼应）与 F-4（修复闭环）都是 0。
本轮做的是其中**唯一带时间结构的一条**：张力之后**同一线程内**是否出现和解动作。它可被证伪、可逐条复核、
不需要读者相信作者的审美（读者能自己数「张力后 8 条内有没有修复词 / 机制有没有给过机会」）。

### 1.3 本轮不做什么（边界）

- **不修 L-13**（`code/life/agent.py:1256` 把 `topic` 模板 id 原样插进提示词）——一改，本臂与基线的差异就不止 F-4 一项，归因失效；
- 不改 `tools/d5/dialogue_metrics.py`（R1–R12 口径不可动）；新口径以**新模块** `tools/f4/f4_subset_metrics.py` 并列输出；
- 不改 `config/`、`engine/`、`freeze/`、`code/life` 之外的业务语义；`code/orchestration/integration.py` 仅新增 **3 行**白名单转发（§5 明示）；
- 不碰 G-1 与 `d4_*` / `run_g1_*` 等历史未跟踪产物；
- 不写「生活气息改善」；不把「闭环从 0 变 N」当效果结论。

---

## 2. 机制事实（实现，`6b7ae8a`）

| 文件:行号 | 作用 | 开关 |
|---|---|---|
| `code/config/dialogue_repair.json:4` | `enabled=false`（默认关，**本轮未改**） | `HITT_DIALOGUE_REPAIR` |
| `code/life/dialogue_repair.py:102-104` | env 覆盖：`=1/true/on/yes` 打开，`=0/off` 关闭（回滚用） | 同上 |
| `code/life/dialogue_repair.py`（新增 `repair_ask()`） | 只在**本条要回复的线程**确有未了结旧账时，返回「这一句把话说开」的动作要求；**不给句式**（单测断言不含 `REPAIR_WORDS` 任何词） | 同上 |
| `code/life/dialogue_repair.py`（新增 `repair_audit()`） | 结构化可审计信号 `f4/repair/1`：`rift_ids` / `trigger_seqs` / `peers` / `age_rounds` / `prompted`（**零词表匹配**） | 同上 |
| `code/life/agent.py:993-1002` | 回复路径：`repair_line` 仅当 `enabled`；`_reply_prompt(repair_line=…)` 缺省 `None` ⇒ 提示词逐字节不变 | 同上 |
| `code/life/agent.py:1018-1028` | 回复路径：`payload["dialogue_repair"]` 仅当 `enabled` 且本线程有旧账 | 同上 |
| `code/orchestration/integration.py:187-189` | **新增 3 行**白名单转发 `dialogue_repair`（缺省 None 不写键） | — |

**取材规则（判据的一部分，不是实现细节）**：`repair_ask()` 只给「怎么做由你决定」的要求，
**不写任何现成道歉句**——若提示词里直接塞「对不起」，闭环就成了我们自己写进去的。

**回滚方式**：`unset HITT_DIALOGUE_REPAIR`（或 `HITT_DIALOGUE_REPAIR=0`）⇒ `load_params()["enabled"]=False` ⇒
不吸收 rift、不加 `repair_line`、不写任何新字段（§4.1 字节锁证据）。

---

## 3. 预注册判据（跑批前写死，文件：`v2/evidence/f4_preregistration.md`）

- **主指标**：人际冲突子集闭环事件数（张力须含 `生气/烦/委屈/失望/后悔/吵/凭什么/你什么意思/别这样` 之一），窗口 = 其后 8 条同线程消息。
- **主指标的两个口径**：宽松（`repair_lexicon` 任一词）/ 严格（剔除 `我懂`）**并列**；基线 off = `0/3`（宽松）与 `0/3`（严格）。
- **次指标（机制可达性）**：`payload.dialogue_repair` 出现条数（基线 0），每条要求 `v=f4/repair/1`、`trigger_seqs` 全部 < 本条 seq。
- **交叉核对（2×2）**：词表判定 × 机制配对（闭环且配对 / 闭环不配对=词表噪声 / 不闭环但配对=模型没接 / 都不=基线常态）。
- **守卫**：L-13 条数 ≤ 2（只报事件数）；MSG 459–561；mixed 线程 152–186；`degraded_calls=0`；`llm_calls ≤ 3310`；提示词不含现成句式。
- **降级**：分母 <30 只报事件数；<68 标 `probe`；任一守卫恶化 ⇒ 结论「不可判」。

---

## 4. 证据链

### 4.1 批身份表（数据 ↔ 该臂代码，三元绑定第一、二环）

| 臂 | run 目录 | `run.jsonl` sha256 | sha8 | `meta.json.code_sha`（该臂，非 HEAD） | MSG | mixed 线程 | events | llm_calls | degraded |
|---|---|---|---|---|---|---|---|---|---|
| OFF 基线 | `v2/evidence/run_f6_off_n16r60_seed42/` | `c73bead61a440db789f6d6ba1de555fe326a203ee27d1219690174e3d9483642` | `c73bead6` | `895b9a381cd5a1838c23bd3b38e139f7edade3b8` | 510 | 169 | 116294 | 2878 | 0 |
| **F-4 ON 臂** | `v2/evidence/run_f4_on_n16r60_seed42/` | `faeba580cfc5ae00d43a168ad5c8da67532e3825b0885aa13da78737fb4bf93a` | `faeba580` | **`6b7ae8a98694dd87d2ea26d14e663705eab69e92`** | 504 | 167 | 116277 | 2872 | 0 |

- `meta.json` 的 `code_sha` 与 `code_sha_end` **相同**（`6b7ae8a…`），即跑批期间 `code/` 未变；`git_dirty_code_files` 只有一条
  未跟踪的前端 sample 目录，无源码改动。
- **不变式**：本报告所有源码引用都写 `6b7ae8a`（该臂提交），**不写 master HEAD**——读者复现的是「那批数据用哪版代码跑的」。

### 4.2 真 LLM 验真（`host.log` 原文摘录，不转述）

```
[meta] events=116277 llm_calls=2872 cached_ratio=0.5111 provider={'openai_compat': 2872} model={'DeepSeek-Flash': 2872}
[meta] OK: 真跑判定通过
"provider_guard": {"by_provider": {"openai_compat": 2872}, "expected": "openai_compat", "ok": true, "problems": []}
"total": {"cached": 1468, "calls": 2872, "degraded": 0, "thinking": 668, "tokens_in": 231998, "tokens_out": 281001, "tokens_total": 512999}
```

- `degraded=0`、`problems=[]`、`mock_precalib_msg_count=0` ⇒ **无 mock 混入的可用证据**（不是「我相信是真 LLM」）。
- 复现：`grep -n 'provider_guard\|真跑判定' v2/evidence/run_f4_on_n16r60_seed42/host.log`（`host.log` sha256 `0f1e0a5d…` 见 §4.7）。

### 4.3 读数表（零跑批，只读日志；命令可原样复制）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# ① 双口径 + 可审计配对行（主表）
python3 tools/f4/f4_subset_metrics.py \
  --run off=v2/evidence/run_f6_off_n16r60_seed42/run.jsonl \
  --run on=v2/evidence/run_f4_on_n16r60_seed42/run.jsonl \
  --out-json v2/evidence/f4_subset_on_vs_off.json

# ② 成本按回合段对齐
python3 tools/f4/f4_cost_bands.py \
  --run off=v2/evidence/run_f6_off_n16r60_seed42/run.jsonl \
  --run on=v2/evidence/run_f4_on_n16r60_seed42/run.jsonl \
  --out-json v2/evidence/f4_cost_bands.json

# ③ 守卫指标（L-13 / MSG / degraded）——全族唯一口径 d5，未改动
python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_f4_on_n16r60_seed42/run.jsonl \
  --meta v2/evidence/run_f4_on_n16r60_seed42/meta.json \
  --out-json v2/evidence/d5_run_f4_on_n16r60_seed42_r13close.json \
  --out-md   v2/evidence/d5_run_f4_on_n16r60_seed42_r13close.md
python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_f6_off_n16r60_seed42/run.jsonl \
  --meta v2/evidence/run_f6_off_n16r60_seed42/meta.json \
  --out-json v2/evidence/d5_run_f6_off_n16r60_seed42_r13close.json \
  --out-md   v2/evidence/d5_run_f6_off_n16r60_seed42_r13close.md
```

**主读数（`f4_subset_on_vs_off.json`, `6cf17808`）**

| arm | sha8 | MSG | 旧口径张力 | 旧口径闭环（宽松/严格） | 人际张力 | 人际闭环（宽松/严格） | 可审计配对行 |
|---|---|---|---|---|---|---|---|
| off | `c73bead6` | 510 | 22 | 0 / 0 | 3 | 0 / 0 | 0 |
| on | `faeba580` | 504 | 14 | 2 / 2 | 1 | 0 / 0 | 22 |

- **分母纪律（逐行适用）**：人际子集分母 3 / 1 全部 <30 ⇒ **只报事件数，不写比率**；旧口径分母 22 / 14 亦 <30 ⇒ 同处理。
  本报告全文**不出现**「闭环率 0%」「提升 X%」这类表述，因为它们会把这个分母读成总体率。
- **可审计配对 22 行的机械校验**（独立于上面脚本，直接扫日志）：
  ```bash
  python3 - <<'PY'
  import json
  rows=[json.loads(l) for l in open('v2/evidence/run_f4_on_n16r60_seed42/run.jsonl')]
  ra=[r for r in rows if isinstance(r.get('payload'),dict) and r['payload'].get('dialogue_repair')]
  print('rows',len(ra),'| v=',{r['payload']['dialogue_repair']['v'] for r in ra},
        '| prompted_all=',all(r['payload']['dialogue_repair']['prompted'] for r in ra),
        '| trigger>=seq违规=',[r['seq'] for r in ra if any(t>=r['seq'] for t in r['payload']['dialogue_repair']['trigger_seqs'])],
        '| 线程数=',len({r['payload'].get('thread_id') for r in ra}))
  PY
  ```
  实测输出：`rows 22 | v= {'f4/repair/1'} | prompted_all= True | trigger>=seq违规= [] | 线程数= 13`。
- **守卫表（预注册 `f4_preregistration.md:90-94`，任一恶化 ⇒ 不可判）**

| 守卫 | 阈值 | OFF 基线 | F-4 ON 臂 | 结论 |
|---|---|---|---|---|
| MSG 条数 | 459–561 | 510 | 504 | ✅ 在带内 |
| mixed 线程 | 152–186 | 169 | 167 | ✅ 在带内 |
| `degraded_calls` | 0 | 0 | 0 | ✅ |
| `llm_calls` | ≤3310 | 2878 | 2872 | ✅（且 §4.6 显示差异只落在 31-60 段 −6 次） |
| **L-13 内部 token 泄漏条数** | **不得高于基线（=2）** | 2 | **15** | ❌ **恶化 13 条 ⇒ 本臂效果判「不可判」** |
| 提示词不出现成句式 | 单测断言 | — | `code/tests/test_dialogue_repair.py` 断言 `repair_ask()` 不含 `REPAIR_WORDS` 任一词 | ✅（`6b7ae8a` 树内） |

**为什么 L-13 恶化必须当场认，而不是留到下一轮**：预注册在跑批前就把「L-13 不得高于基线」写成守卫，
理由是同一次跑批里出现的差异必须**只能**归因到 F-4 臂；L-13 从 2 → 15 说明「本轮唯一变量」这个前提没守住
（`whisper` 主题泄漏 14 条），所以**不能用「闭环 0→2」去说效果**，只能登记机制事实。归因方向（是否 F-4 提示词把
`topic` 又带进正文）本轮**未做隔离实验，属未确认**，不写猜测。

### 4.4 截图：本轮**未产出真拍**（如实登记，不替代）

- 事实：`v2/evidence/` 下没有 `f4_shots/` 目录，本臂（`faeba580`）**没有任何截图产物**。
- 原因：R13 的收口任务是零跑批文档回填，**未执行**真拍管线；本报告不拿旧图、不拼图、不手绘冒充。
- 按全族纪律「拿不到图就写「无图 + 渲染命令」」登记，下一轮可直接执行：
  ```bash
  cd code
  python3 frontend/tools/gen_threads.py \
    --log ../v2/evidence/run_f4_on_n16r60_seed42/run.jsonl \
    --meta ../v2/evidence/run_f4_on_n16r60_seed42/meta.json \
    --out frontend/sample/dialogue_run_f4_on_n16r60_seed42/threads.json \
    --require-complete --label run_f4_on_n16r60_seed42-faeba580
  (cd code && python3 frontend/tools/serve.py &)   # 127.0.0.1:8848
  bash frontend/tools/dialogue_shots.sh http://127.0.0.1:8848 \
    sample/dialogue_run_f4_on_n16r60_seed42/threads.json "" "" ../v2/evidence/f4_shots
  ```
  产物应命名 `<batch>-{chat,rhythm,spread,600}-faeba580.png`，并把 `render.log`（含复现命令、`mean_brightness`、
  `blank_retries`）一并落盘。**在跑出这些之前，本报告不含任何截图结论。**

### 4.5 2×2 交叉表 —— **官方脚本有键口径 bug，本节用独立复算**

**问题**：`tools/f4/f4_subset_metrics.py` 建配对索引时用**原始 `thread_id`**（如 `TH-P007-P005-19`），
而张力事件行用**混合键**（`m:T|TH-P007-P005-19`）：

```python
pair_index.setdefault((row["thread"], tseq), []).append(row["seq"])   # row["thread"] = payload.thread_id
...
r["mechanism_pairs"] = pair_index.get((r["thread"], r["trigger_seq"]), [])  # r["thread"] = mixed_key
```

两键永不相等 ⇒ `mechanism_pairs` 恒空 ⇒ `tools/f4/f4_crosstab.py` 的 **A、C 两格结构性恒为 0**，
「闭环且机制配对 = 0」「机制给了机会但模型没接 = 0」**不是日志事实**。同一 bug 也让 `audit_rows[].closed_by_seq` 恒为 `[null]`。

**独立复算**（只修键映射，词表/窗口/极性判定全部从官方模块 import，不重定义；脚本 `v2/evidence/f4_audit_crosstab.py`）：

```bash
python3 v2/evidence/f4_audit_crosstab.py \
  --run off=v2/evidence/run_f6_off_n16r60_seed42/run.jsonl \
  --run on=v2/evidence/run_f4_on_n16r60_seed42/run.jsonl \
  --out-json v2/evidence/f4_audit_crosstab.json      # 10fb7fb0
```

| arm | 口径 | 张力 | A 闭环∧配对 | B 闭环无配对 | C 未闭环∧配对 | D 未闭环无配对 | 恒等式 |
|---|---|---|---|---|---|---|---|
| off `c73bead6` | legacy/宽松 & 严格 | 22 | 0 | 0 | 0 | 22 | OK |
| off `c73bead6` | 人际/宽松 & 严格 | 3 | 0 | 0 | 0 | 3 | OK |
| on `faeba580` | legacy/宽松 & 严格 | 14 | **2** | 0 | **10** | 2 | OK |
| on `faeba580` | 人际/宽松 & 严格 | 1 | 0 | 0 | 0 | 1 | OK |

**读法（严格按表，不外推）**：

1. 旧口径 14 条张力里，**10 条机制确实给了「把话说开」的机会而模型没接**（C 格），2 条接了（A 格）——
   这是「机制可达 ≠ 对话变好」的直接证据，也是本报告唯一允许的机制侧量化事实；
2. 那 **2 条 A 格是同一句收口（`seq 30177`「别往心里去」）在相邻窗口重叠下被计两次**：
   张力事件 `trigger_seq 26539`（lag 2）与 `27719`（lag 1）都落在这一句的 8 条窗口内。
   ⇒ **不同收口句只有 1 条**。报告如需「闭环条数」，必须写「2 个事件 / 1 条不同话语」，不能写成「2 次和解」；
3. 人际子集（主指标）在 on 臂只有 1 条张力，A/B/C 全 0 ⇒ **主指标上机制未拿到任何证明点**；
4. 22 条配对行里，**只有 4 行**在其 rift 触发句之后 8 条内出现了修复词（`f4_audit_crosstab.json` 的 `audit_rows_with_a_closure`）。
   ⇒ 「机制开着」不等于「机制被接住」，两件事分开记账。

> **定性（三段，逐句写死，避免读者以为口径被换过）**：
> ① **官方脚本 A / C 两格结构性恒 0，是「`pair_index` 用原始 `thread_id`、张力行用 `mixed_key`」导致的键口径 bug**
> （`mechanism_pairs` 恒空），**不是日志事实**；
> ② 本文的 **A=2 / B=0 / C=10 / D=2 取自并列复算脚本 `v2/evidence/f4_audit_crosstab.py`**，
> 该脚本**规则仍 `import` 官方模块**（词表 / 窗口 / 极性判定同源），只修键映射；
> ③ **官方脚本的修复单独立项，不属于 R13 范围**（改它会让 R13 历史读数变成「用另一份代码算出来的」，
> 破坏可复现性；且本轮目标是 F-3，顺手改 F-4 工具属范围外改动）。
> 因此在修复立项前，引用交叉表一律用 `f4_audit_crosstab.json`（`10fb7fb0`），
> `tools/f4/f4_crosstab.json`（`cd38dec6`）**不得再被引用为 A=0 / C=0 的证据**。

### 4.6 成本归因（按回合段对齐，`f4_cost_bands.json` `8b53dbc9`）

| arm | 段 | 回合 | calls | 每回合 | Δcalls vs 基线 | dialogue | judge | importance | degraded |
|---|---|---|---|---|---|---|---|---|---|
| off `c73bead6` | 0-9 | 9 | 732 | 81.33 | 0 | 91 | 295 | 307 | 0 |
| off | 10-10（日结段） | 1 | 1355 | 1355.0 | 0 | 6 | 117 | 1216 | 0 |
| off | 11-30 | 20 | 264 | 13.20 | 0 | 161 | 17 | 0 | 0 |
| off | 31-60 | 29 | 527 | 18.17 | 0 | 252 | 239 | 0 | 0 |
| on `faeba580` | 0-9 | 9 | 732 | 81.33 | **0** | 91 | 295 | 307 | 0 |
| on | 10-10（日结段） | 1 | 1355 | 1355.0 | **0** | 6 | 117 | 1216 | 0 |
| on | 11-30 | 20 | 264 | 13.20 | **0** | 161 | 17 | 0 | 0 |
| on | 31-60 | 29 | 521 | 17.97 | **−6** | 246 | 239 | 0 | 0 |

- 启动段与日结段**逐格完全一致**（732 / 1355 / 264），说明 F-4 臂**没有**引入固定成本；
  全批差异 `−6` 次调用只落在 31-60 段的 dialogue 通路上（252 → 246），量级 ≈ 单回合噪声，**不主张成本结论**。
- 复现：§4.3 命令 ②；或 `head -25 v2/evidence/f4_cost_bands.json`。

### 4.7 证据文件 sha256 台账（本轮复算产物，逐条可核）

| 文件 | sha256 | sha8 |
|---|---|---|
| `v2/evidence/f4_subset_on_vs_off.json` | `6cf1780846b72a24bae7fa4ba4021b22e7697fc979cc5a44be09b97c847e65ca` | `6cf17808` |
| `v2/evidence/f4_audit_crosstab.json` | `10fb7fb0bd1017ff6ac2579d8b68657d16f0f0ad02c281d424ebdfc95ef10bee` | `10fb7fb0` |
| `v2/evidence/f4_audit_crosstab.py` | 见 `sha256sum`（随本报告同提交） | — |
| `v2/evidence/f4_crosstab.json`（**仅供对照，含键 bug**） | `cd38dec643f86538d3468d39a2f5c207e85d9eb452712a366cd642f04f659522` | `cd38dec6` |
| `v2/evidence/f4_cost_bands.json` | `8b53dbc9a4fa7c326b16ee5b10ec6f7d229ac4fef8fbfc47928329371c26e20f` | `8b53dbc9` |
| `v2/evidence/d5_run_f4_on_n16r60_seed42_r13close.json` | `1f8d55898b5b7693aab6c7dc32d90d6724824dbbdacfeff9991e540b8d9e3f3e` | `1f8d5589` |
| `v2/evidence/d5_run_f6_off_n16r60_seed42_r13close.json` | `cb757208249dd9fc02bbd712d70070c1d998d018aab3b89e84a3721502fc355c` | `cb757208` |
| `v2/evidence/run_f4_on_n16r60_seed42/meta.json` | `d74287b7ff021ea5ba974132f469b49f03d994835b7effe6e33f5560888a9ef4` | `d74287b7` |
| `v2/evidence/run_f6_off_n16r60_seed42/meta.json` | `5d0634b6f43b0129496f329c071ad55bb876ca499d322933a3896c5012930500` | `5d0634b6` |

---

## 5. 纪律自查（逐条带证据）

| # | 纪律 | 证据 |
|---|---|---|
| 1 | 起跑前串行确认 | `pgrep -af '[o]rchestration run'` → **rc=1**；`pgrep -af '[r]un_batch'` → **rc=1**（两条**分开**执行；把两条写进同一行 shell 时 `[r]un_batch` 会匹配到执行它的 sh 自身，见 anchor 阶段实测） |
| 2 | 跑批期间未改禁改目录 | `git status --porcelain -- code/life code/orchestration code/config code/engine code/freeze` → **空**（起批前与批末各查一次）；`git diff --stat 021baec3..HEAD -- code/` 只有 4 个文件（3 行为 orchestration 白名单转发，见第 7 行） |
| 3 | 无长 sleep；后台 setsid | 起批原文：`setsid nohup env HITT_DIALOGUE_REPAIR=1 bash tools/d2/run_batch.sh --out-dir v2/evidence/run_f4_on_n16r60_seed42 --seed 42 --agents 16 --rounds 60 --side-root /tmp/f4_on60_side > v2/evidence/run_f4_on_n16r60_seed42/host.log 2>&1 &`；等待用 `tail --pid=<pid> -f /dev/null`（后台命令完成即通知），**未用 sleep 轮询等结果**；起跑后 1 分钟内做了 `pgrep`/`ls`/`wc -l` 三条自证 |
| 4 | 真 LLM 验真 | 见 §4.2（`rc=0`、`provider_guard.ok=true`、`problems=[]`、`degraded=0`） |
| 5 | 截图本轮产生 | **未达成**：本轮无任何 F-4 臂截图（`v2/evidence/` 下无 `f4_shots/`）。按全族纪律「拿不到图就写无图 + 渲染命令」登记，渲染命令见 §4.4；**不以旧图/拼图/手绘图替代**。原骨架行写的「mtime 晚于跑批结束 / 文件名 sha8 = 本臂 run.jsonl 前 8 位」是**要求**，非事实陈述——此处更正为事实陈述 |
| 6 | 结论绑 sha | §0.3 结论→commit 表 + §4.1 批身份表（数据 sha8 + 臂 commit） |
| 7 | 维度单一（含 orchestration 3 行的显式声明） | `git diff --stat 021baec3..HEAD -- code/` = `code/life/agent.py (+13/−2)`、`code/life/dialogue_repair.py (+53)`、`code/orchestration/integration.py (+3)`、`code/tests/test_dialogue_repair.py (+134)`。**其中 `code/orchestration/integration.py` 被动了 3 行**，性质是**白名单转发新增字段**（`_thread_fields()` 追加 `dialogue_repair`，缺省 `None` 不写键），是在**跑批前、无批在跑时**做的，OFF 路径零行为差异（§4.1 字节锁）——不是藏起来的改动，特此明示 |
| 8 | commit message 勘误 | `e16dbd7` commit message 写「新增 8 条单测」，实际新增 7 条（`git show e16dbd7 -- code/tests/test_dialogue_repair.py \| grep -c '^+def test_'` → **7**，文件共 21 条），为 commit message 表述误差，不影响任何行为与判据。**未 amend**（批正用该 sha 起跑，amend 会让 `meta.json` 的 `code_sha` 变孤儿） |
| 9 | 预注册零改动 | `git log --format=%H -- v2/evidence/f4_preregistration.md` → **只有 `6b7ae8a98694dd87d2ea26d14e663705eab69e92` 一条**；文件 mtime 仍是 **2026-10-21 22:16:55**（跑批前写死）；勘误：预注册 §4 标题「零跑**拍**」应为「零跑批」，为笔误，未改原文 |

> **§5 方法论（三条合一的同一病灶）**：本轮的**启动段与日结段都不具代表性**。
> ① ETA 不能用启动段外推：22:34 时用 round 0–9 的 1.94 分钟/回合估出 116 分钟，实际稳态约 25 秒/回合、全程约 40 分钟，**高估近 3 倍**；
> ② 启动段是固定成本：round 0–9 共 732 次调用，且本臂与基线**逐回合完全一致**（44/203/13/208/3/15/193/44/9），与干预无关；
> ③ round 10 单回合 1355 次，占基线全程 2878 的 **47.0%**，是结构性日结/反思批量，混入邻段会让「机制成本」虚高或虚低。
> ⇒ 正确做法：**等 round 10 日结段结束后再用稳态速率估 ETA；成本归因一律按回合段对齐**（§4.6 的四段表）。



---

## 6. 本轮新增路径清单（显式不认领历史遗留）

本轮（R13）新增/改动的路径，逐条列出；**历史未跟踪产物一律不认领**（`code/frontend/sample/dialogue_run_g1_b0_n16r60_seed42/`、
`v2/evidence/d4_*`、`v2/evidence/run_g1_*`、`v2/evidence/run_dr_round1_*` 等保持原状，未删未改）。

**本轮代码（提交在 `6b7ae8a` / `e16dbd7`，不属本次回填范围，仅登记）**

| 路径 | 类型 | 说明 |
|---|---|---|
| `code/life/dialogue_repair.py` | 改 | 新增 `repair_ask()` / `repair_audit()` + env 覆盖 |
| `code/life/agent.py` | 改 | 回复路径接 `repair_line` / `payload.dialogue_repair`（仅 `enabled` 时） |
| `code/orchestration/integration.py` | 改（+3 行） | 白名单转发 `dialogue_repair` |
| `code/tests/test_dialogue_repair.py` | 改 | 21 条单测（`e16dbd7` message 写「8 条」为笔误，实为 7 条新增） |
| `tools/f4/*.py|sh`（7 个文件） | 新增 | 度量/锚点/字节锁/交叉表/成本分段脚本 |

**本轮证据（本次回填新产出，`v2/evidence/`）**

| 路径 | 类型 | 说明 |
|---|---|---|
| `v2/evidence/f4_subset_on_vs_off.json` | 新增 | 双口径 + 配对行主读数（`6cf17808`） |
| `v2/evidence/f4_audit_crosstab.py` | 新增 | **独立复算** 2×2 表（修 `tools/` 键映射 bug，规则 import 自官方模块） |
| `v2/evidence/f4_audit_crosstab.json` | 新增 | 复算结果（`10fb7fb0`），A=2 / C=10 |
| `v2/evidence/f4_crosstab.json` | 新增（**含键 bug，仅作对照**） | `cd38dec6` |
| `v2/evidence/f4_cost_bands.json` | 新增 | 按回合段对齐的成本归因（`8b53dbc9`） |
| `v2/evidence/d5_run_f4_on_n16r60_seed42_r13close.{json,md}` | 新增 | 守卫指标（L-13=15）；`d5` 口径未改动 |
| `v2/evidence/d5_run_f6_off_n16r60_seed42_r13close.{json,md}` | 新增 | 基线守卫指标（L-13=2） |
| `v2/evidence/run_f4_on_n16r60_seed42/`（run.jsonl 55MB / meta.json / host.log） | 已有未跟踪 | 本臂跑批产物，值 `faeba580` |

**本轮文档**：`reports/R13-f4-repair.md`（本文件，占位符全量回填）、`reports/README.md`（状态表补 R13 行）。

---

## 7. 下一步建议

1. **L-13 单独开臂（本轮一行未动）**：泄漏串全部是 topic 模板 id（`whisper` / `combat_training` / `scarce_buy` / `mentorship`），根因是 `code/life/agent.py` 把 `topic` 原样插进提示词「你正在和 X 聊「whisper」」。建议下一轮做「topic 人话化映射表 + 单 env 开关」，与 F-4 正交、可单独归因。
2. **度量层升级为双口径并存**：本轮证明旧口径的张力分子（19/22 是 `怕/累/疼` 自述词）与闭环分子（`我懂` 被当和解）两个方向都不干净。建议把「人际冲突子集 + 严格口径 + 机制配对交叉表」合并进下一代口径 `tools/d5` 的 v2（**旧口径保留为对照列**，不替换），这样后续报告不必每次现拼。
3. **initiate 路径尚未接配对**：`repair_ask` / `repair_audit` 只接在 `_send_reply`；若下一轮想覆盖「主动找对方和好」，需在 `_initiate` 也接上（会扩大改动面，必须单开臂、单独预注册）。
4. **预注册把「预算守门」与「效果判据守卫」分两栏**：本轮差点因为一个算错的中间数（把启动段当稳态外推 ≈4400 次）就给自己判「不可判」。预算超支应当**只披露成本、不自动推翻效果结论**——这次的实际经历就是理由。
5. **起批前按 ETA 预判**：预估 >2h 直接 `systemd-run`（不要事后补救）；预估方法按 §5 的方法论（round 10 之后取稳态速率）。


