# R14 · F-3「情绪呼应」：把「接住对方情绪」做成可审计的单变量臂（n16×60 seed42，F-3 ON vs OFF 基线）

> 性质：骨架先写、读数后填（§1–§3 与 §4 表头跑批前写死；读数到手只填空、不改表头与口径）。
> 报告日期：2026-10-22 ｜ 团队轮次：ROUND-2 ｜ 维度：F-3（单一维度，不扩散）
> 代码 sha（两臂身份见 §4.1）：
> - OFF 臂 `6b7ae8a98694dd87d2ea26d14e663705eab69e92`（跑于 **dirty-tree**，`meta.code_sha` **不含** F-3，代码身份改用口径 B 第二锚）
> - ON 臂 `6f87363fc30c52adf77d51b560aec312053ec484`（先提交 F-3 再跑，`meta.code_sha` 覆盖 F-3；= `code_sha_end`）
> 分支：`feat/life-f3-emotion-echo`
> 本文件 commit sha：**待首版提交后回填（照 R12/R13 先例：首版提交 → 追加一个只回填该行的 commit）**。锚点行：`git log --format=%H -- reports/R14-f3-emotion-echo.md`

---

## 0. 摘要 TL;DR

> **写死的主结论形态**：**「机制可审计地触发 `ctx.echo` N 次（OFF 0 / ON 295）+ 台词并排确实接住了对方情绪」**。
> **禁止**出现「呼应率提升」「显著改善」这类提升式表述——本轮有一条守卫被击穿（§0.3），效果结论按先例判「不可判」。

### 0.1 机制事实（**可判**，主结论）

| 量 | OFF 臂 | ON 臂 |
|---|---|---|
| `payload.ctx.echo` 条数 | **0** | **295**（`v=f3/1` 295/295，`prompted=true` 295/295） |
| 覆盖去重线程 | 0 | **84** |
| `sign` 分布 | — | **−1: 280 / +1: 15** |
| `tier` 分布 | — | 轻 161 / 明显 100 / 很强 34 |
| `source` 分布 | — | `mood` 252 / `text` 9 / `text+mood` 34 |
| `kind` 分布 | — | `soothe` 280 / `cheer` 15 |
| `intensity` | — | min 40 / 中位 40 / max 87（阈值 30 以上） |
| 按**官方判据**「确实接住」 | 0/0（无候选） | **37 / 295 = 12.54%**（Wilson95 **9.24–16.81%**，`band=ok`） |

⇒ **机制确实被打开且可逐条复算**；295 是**触发次数**，不是「接住 295 次」。台词并排见 §4.5（5 组，其中 1 组是**反面样例**）。

### 0.2 官方口径 A：**降为附注，不构成效果证据**

| 指标 | OFF | ON | Δ | 分母 | band |
|---|---|---|---|---|---|
| F-3 `echo_rate`（`tools/d5` 原式） | 1/24 = 4.17% | 5/26 = 19.23% | **+15.06pp**，Newcombe 95% CI **[−4.26, +34.03] 跨 0** | 24 → 26 | `count_only` |

**同一段内必须读到的三条**：① CI **跨 0**；② 分母 < 30 ⇒ 只报事件数、**不报比率结论**；③ 该口径**有假阳性**——4 组原文反例见 `v2/evidence/f3_echo_falsepos_samples.md`（sha8 `098ef8f9`，**取自同构控制臂 `run_f6_off`（`c73bead6`），不是本轮 ON/OFF 数据**）。单独拿这张表当成效证据不行。

### 0.3 ⚠️ 守卫 L-7 被击穿 ⇒ **效果结论「不可判」**

| 守卫 | OFF | ON | Δ | 噪声带上界（同分母） | 判定 |
|---|---|---|---|---|---|
| **L-7 8gram 重复率** | **177/510 = 34.71%** | **223/502 = 44.42%** | **+9.72pp** | **+6.25pp**（`d3_noiseband_bootstrap.json::denom_480`，band `[−5.83, +6.25]`） | ⚠️ **超带 ⇒ 击穿** |

按 R12/R13 先例（任一守卫恶化 ⇒ 结论写「不可判」），**本臂效果结论判「不可判」**，只登记机制事实。
机制解释（如实登记，不辩解）：`prompt_line`（`code/life/emotion_echo.py:197-213`）是**固定句式要求**（「先接住这份情绪…别讲道理、别急着转到自己身上」），295 条回复被同一要求约束 ⇒ 起句/句式收敛。日志里可直接看到后果——**§4.5 样例 5 是同一段文本被相邻两个线程各生成一次**。

### 0.4 口径澄清（防串味）

- **官方口径 A**：`tools/d5/dialogue_metrics.py` 的 F-3（相邻对中上一句极性≠0 时，下一句极性相同或含 `EMPATHY_MARKERS` 即计呼应）。R1–R13 沿用，**仅用于历史可比**。
- **机制口径 B**：ON 臂写入的 `payload.ctx.echo`（`v=f3/1`）；分母 = 机制判定为「可呼应」的轮次，命中 = 模型输出接住该情绪（极性一致或含共情标记）。**主证据用这条**。
- `ctx.echo`（F-3）与 `ctx.dialogue_repair`（F-4，R13）是两个不同字段；本轮 ON 臂 `dialogue_repair` 命中 **0**，证明未与 F-4 混跑。

### 0.5 证据分级与分母纪律

- 分母 < 30 ⇒ 只报事件数；< 68 ⇒ 标 `probe`；阈值来源见各表 `band_source` 列。
- 两臂**不同 sha**（OFF `6b7ae8a` 不含 F-3 / ON `6f87363` 含 F-3），**同 seed、同规模、不同时间窗、单次运行** ⇒ **无置信区间、不做显著性判定**，只写「方向 + 守卫并列」。
- **本轮单次观察，不外推为「稳定成立」**。

### 0.6 结论 → commit 绑定表

| # | 结论 | 绑定 commit | 绑定证据（文件名 + sha8） |
|---|---|---|---|
| C1 | 机制可审计触发：`ctx.echo` 0 → **295**（84 线程，`v=f3/1` 295/295） | ON `6f87363` / OFF `6b7ae8a` | `run_f3_on_…/run.jsonl (087072f8)`、`run_f3_off_…/run.jsonl (19d5cb03)`、`f3_readings.json (d286b550)` |
| C2 | 台词并排确实接住情绪（5 组，含 1 组反面） | ON `6f87363` | `run_f3_on_…/run.jsonl (087072f8)` §4.5 行号可回溯 |
| C3 | 守卫：L-7 **击穿** +9.72pp > +6.25pp ⇒ 效果**不可判**；L-13 10→2、degraded 0/0 | 同上 | `f3_on_official.json (d8cf5b80)`、`f3_off_official.json (3835ba58)`、`d3_noiseband_bootstrap.json` |
| C4 | 官方口径 1/24 → 5/26（+15.06pp，CI 跨 0，`count_only`，附注级） | 同上 | `f3_readings.json (d286b550)` |

---

## 1. 本轮维度与为什么选它（单一维度）

### 1.1 缺口是可复算的（零跑批锚点，先做再花钱）

F-3 机制在工作树中**早已实现**，但**从未有报告**；OFF 控制臂**已真跑落盘**（`v2/evidence/run_f3_off_n16r60_seed42/`，2026-10-22 01:01 结束，`llm_calls=2878`、`degraded_calls=0`、`[meta] OK: 真跑判定通过`）。缺的是 **ON 臂 + 双口径读数 + 报告**。
⇒ 本轮不新造机制、不重复付费，只把「一半的沉没成本」收口（选题依据：`team-workspace/rounds/2026-10-22/survey.md` §7 候选 1）。

### 1.2 为什么这算「生活气息」

「情绪呼应」= 对方带着情绪说话时，我这一句**先接住这份情绪**，而不是各说各的、或急着把话头抢回自己身上。
这是日常生活对话里最基础的一条「往来感」，也是 R4「生活气息观测」里 **E 系列（情绪/语气）**长期缺失的一环：R13 之前 F-4（误会与和解）的机制从未打开，F-3 同样「有代码、无观测」。
判据落在**可审计字段**上，不依赖主观观感。

### 1.3 本轮不做什么（边界，写死）

1. **只覆盖回复路径**：F-3 只在 `LifeLayerAgent._send_reply`（`code/life/agent.py:1032`、`:1034`）与 `_reply_prompt`（`:1292`、`:1301`）上接线；**`_initiate`（`code/life/agent.py:1077`）未接入** ⇒ 主动发起消息的路径**没有**情绪呼应。本报告任何结论都**不得**外推到「所有对话」。
2. **不改官方口径**：`tools/d5/dialogue_metrics.py` 一行不改；假阳性问题**登记不修**（属口径变更，需单独一轮）。
3. **不做 G-1 / 关系亲密度 / 天气小事**（本轮其他候选一律不做，见 survey §7 其余候选）。

---

## 2. 机制事实（实现，`6f87363`）

| 项 | 事实 | 位置 |
|---|---|---|
| 开关 | env `HITT_DIALOGUE_EMOTION_ECHO` ∈ {`1`,`true`,`on`,`yes`} → 开；其它任何取值（含 `0`/`false`/`off`/空串）→ 关；**默认关** | `code/life/emotion_echo.py:57`（`ECHO_ENV`）、`:89-95`（`load_params`） |
| 配置文件 | `code/config/emotion_echo.json`，`enabled=false`；**不进** `engine/version.py::FINGERPRINT_FILES` ⇒ 开/关都不改 `engine_version` 指纹 | `code/config/emotion_echo.json` |
| 判定（纯函数、不调 LLM） | `detect()` 给 `{sign, intensity, tier, source, mood, kind}`；`source ∈ {text, mood, text+mood}`；强度 = `text_hit_intensity + mood_severity // mood_bonus_div`，仅处境时 = 严重度 | `code/life/emotion_echo.py:158-182` |
| 阈值 | `min_intensity=30`、`text_hit_intensity=60`、`mood_bonus_div=2`、`tier_cuts=[45,70]` | `code/config/emotion_echo.json`、`emotion_echo.py:74-86` |
| 不产条件 | 开关关 / `sign==0` / 强度 < 阈值 ⇒ `plan()` 返回 `None` ⇒ **调用方零副作用**（提示词不加字、payload 不多键） | `code/life/emotion_echo.py:185-195` |
| 提示词注入 | `prompt_line()` 只给「对方现在怎样」+ 一条做法要求（先接住情绪、别讲道理、别转到自己身上），**不给现成句式** | `code/life/emotion_echo.py:197-213` |
| 审计字段 | `audit()` → `{v:"f3/1", sign, intensity, tier, kind, source, mood, prompted:true}`，挂在 `payload.ctx.echo`（`ctx` 是 `orchestration/integration.py::_thread_fields` 已整体透传的段，顶层新键会被白名单静默吞掉） | `code/life/emotion_echo.py:216-224`、`code/life/agent.py:968`、`:1050` |
| 接线 | 回复路径三处：`_emotion_echo()` 定义 `agent.py:989`、调用 `:1032`、传 `echo_line` 给 `_reply_prompt` `:1034`；`_reply_prompt` 形参 `:1292`、插入 `:1301` | 同左 |
| 单测 | `code/life/tests/test_f3_emotion_echo.py`（life-engineer 自述 27 passed；**本轮未由我复跑，标「未验证」**） | — |
| OFF 路径等价性 | OFF 臂 `grep -c '"echo"'` = **0**（字段根本不产生）；`emotion_echo.json` 不进指纹 ⇒ 开/关都不动 `engine_version` | §4.3 |

---

## 3. 预注册判据（跑批前写死）

| 项 | 预注册内容 |
|---|---|
| 单变量约束 | ON 臂**只**设 `HITT_DIALOGUE_EMOTION_ECHO=1`；其余 `LIFE_PROMPT_*`、`HITT_DIALOGUE_REPAIR` **全空** |
| 主证据 | 机制侧 `payload.ctx.echo` 条数（OFF 应为 **0**，ON 应 > 0）且 `v=f3/1`、`source∈{text,mood,text+mood}`、`intensity≥30` 可逐条复算 |
| 次证据 | 台词并排（3–5 组，`seq`/行号可回日志） |
| 附注证据 | 官方口径 F-3 `echo_rate` + 分母（**必须同段写假阳性风险**） |
| 主守卫 | `L-5` / `L-6` / `L-7`（提示词插入类的主要风险面，F-6 的 +29.61pp 是现成反例） |
| 守卫 | `L-13` 内部 token 泄漏（**不得高于 OFF 基线**）、`F-4`、`F-6`、MSG 量、`degraded=0` |
| 降级规则 | 任一守卫恶化 ⇒ 效果结论写「**不可判**」，只登记机制事实（R12/R13 先例） |
| 分母纪律 | 分母 < 30 只报事件数；< 68 标 `probe` |

---

## 4. 证据链

### 4.1 批身份表（数据 ↔ 该臂代码）

| 项 | OFF 基线臂 | ON 臂 |
|---|---|---|
| run 目录 | `v2/evidence/run_f3_off_n16r60_seed42/` | `v2/evidence/run_f3_on_n16r60_seed42/` |
| `run.jsonl` sha256 | `19d5cb03de2f0203e3b8aa1c9160adfbef787a159f961713f40b88027931d305`（`19d5cb03`） | `087072f84518eb009fb8d0a6ec445c5515b7561c1f031430702a5187394af16c`（`087072f8`） |
| `meta.json` sha256 | `8ebe6731805608b325eee4b729b925629e7bf29cf7526042de7140a32d31482a`（`8ebe6731`） | `2b4cdf25795c6d43a13381401b73baca40c12ac6438831860613fa40a80b1442`（`2b4cdf25`） |
| `meta.code_sha` | `6b7ae8a98694dd87d2ea26d14e663705eab69e92`（**不含 F-3**，见 §4.1.1） | `6f87363fc30c52adf77d51b560aec312053ec484`（= `code_sha_end`） |
| 规模 | n=16 / rounds=60 / seed=42 | 同左 |
| env | 全空（F-3 关） | `HITT_DIALOGUE_EMOTION_ECHO=1`（+ `HITT_LLM_PROVIDER=openai_compat` 由 `run_batch.sh` 内部设定，属真跑门禁） |
| 起止 / 时长 | 00:20 → 01:01:03（`duration_sec=2415`） | 02:06:45 → 02:47:05（**2420 s**） |
| `llm_calls` / `degraded` | 2878 / 0 | **2869 / 0** |
| `dialogue` 调用数 | 510 | **502** |
| `events` | 116336 | 115494 |
| tokens_in / out / total | 228,667 / 291,027 / **519,694** | 236,546 / 285,093 / **521,639** |
| `final_state_hash` | `sha256:31b18976529aede800f22ed06868d055904bc7c77c7eb4abdf4ffef9595d25b8` | `sha256:bb3ccf1bc15a8980c3bcfcdf2887f080821e8a3fdae07724ca9ec122d155d453` |
| 真跑判定 | `[meta] OK: 真跑判定通过`；`chain_ok/replay_parity/first_run_equals_replay` 全 True | 同左；`provider_guard ok:true` |

> **花费对照**：OFF 2878 calls / 519,694 tok / 2415 s ↔ ON 2869 / 521,639 / 2420 s ≈ **1.00×**。
> 早期「2.2 倍外推」基于**引导段**估算，后段追平后实际几乎无成本差。

> **脚注 · 跑批期间 `reports/R14` 与 G-1 遗留目录出现在 `git_dirty_files` 是预期内的**：
> ON 臂 `meta.json::git_dirty_code_files` 唯一一项是 `?? code/frontend/sample/dialogue_run_g1_b0_n16r60_seed42/`（G-1 轮遗留、未跟踪），另有本报告骨架 `reports/R14-f3-emotion-echo.md` 在 `git_dirty_files` 中。
> 两者**都在口径 B 四子树之外** ⇒ 「四子树 clean」由 `git_dirty_code_files` 不含四子树文件证明，内容同一份由口径 B 指纹逐位一致证明——**两条合起来才是 `code_sha` 有效性的依据**。
> 这**不是**新的 code identity 矛盾。

#### 4.1.1 两臂可比性：**口径 B 指纹**（不是 `code_sha`）

**为什么不能用 `code_sha`**：OFF 臂跑在 **dirty-tree** 上，`meta.json::git_dirty_code_files` 非空（`M code/life/agent.py`、`?? code/life/emotion_echo.py`、`?? code/config/emotion_echo.json`、`?? code/life/tests/test_f3_emotion_echo.py`），而同文件的 `code_identity_note` 自称「为空表示 `code/` 无未提交改动」——**两者自相矛盾**。⇒ 「按 `code_sha` 复算该批」**不成立**，必须用内容级指纹做第二锚。

**口径 B 定义**（`v2/evidence/f3_code_fingerprint_scope.md` §2，sha8 `bc4215d9`）：`code 四子树聚合指纹（life/config/orchestration/engine，108 文件）`

```bash
find code/life code/config code/orchestration code/engine -type f \
     ! -path '*__pycache__*' ! -name '*.pyc' \
  | sort | xargs sha256sum | sha256sum
```

| 采集时点 | 文件 | 聚合值 | 文件数 |
|---|---|---|---|
| OFF 臂跑前 | `f3_code_fingerprint_prerun.txt (b0d2932e)` / `_files_prerun.txt (dd316401)` | 口径 B **68683fe3…**（口径 A `42c1bdd9…`，105 文件） | 108 |
| ON 臂跑前 | `f3_code_fingerprint_on_pre.txt (85d64a01)` | **68683fe3caef04369bd262fc586522a93f5df8326fddd52400f50f57f4b780af** | 108 |
| ON 臂跑后 | `f3_code_fingerprint_on_post.txt (6222121a)` | 同值（跑后回采） | 108 |
| 报告方现场复算（2026-10-22） | — | 同值 | 108 |

⇒ **三段同值**：`6f87363` 的提交「只动 index 不动内容」，两臂跑的是**同一份四子树内容**。

> **措辞规则（违反即视为夸大）**：两臂可比性的依据只能是 **「跑批相关四子树内容同一份」**（口径 B 逐位一致，108 文件）。
> **不得**写「整棵 `code` 树同一份」——口径 B **不覆盖** `code/frontend`、`code/tests`、`code/obs`、`code/freeze_cache`；也**不得**写「不可复算」。

#### 4.1.2 提交谱系（「F-3 未混入 F-4 历史」的机械证据）

```
$ git ls-tree -r 2c2de5f --name-only | grep -c emotion_echo
0
$ git ls-tree -r 6f87363 --name-only | grep emotion_echo
code/config/emotion_echo.json
code/life/emotion_echo.py
code/life/tests/test_f3_emotion_echo.py
$ git show --stat --oneline 6f87363
6f87363 F-3 情绪回声：实现
 code/config/emotion_echo.json                    |  10 +
 code/life/agent.py                               |  43 +-
 code/life/emotion_echo.py                        | 223 +++++++++++
 code/life/tests/test_f3_emotion_echo.py          | 273 +++++++++++++
 tools/f3/f3_metrics.py                           | 484 +++++++++++++++++++++++
 tools/f3/f3_samples.py                           | 147 +++++++
 v2/evidence/f3_audit_echo.py                     | 305 ++++++++++++++
 v2/evidence/f3_code_fingerprint_files_prerun.txt | 219 ++++++++++
 v2/evidence/f3_code_fingerprint_prerun.txt       |  37 ++
 v2/evidence/f3_code_fingerprint_scope.md         | 104 +++++
 v2/evidence/f3_echo_falsepos_samples.md          |  65 +++
 11 files changed, 1906 insertions(+), 4 deletions(-)
```

⇒ `2c2de5f`（F-4 账本收口 commit）树内 **0 个** F-3 文件，F-3 只出现在 `6f87363`。**两笔账本分离成立。**
谱系：`021baec`（origin/master 起点）→ `e16dbd7` + `6b7ae8a` + `2c2de5f`（F-4 三连，已 push）→ `6f87363`（F-3 实现，已 push）。

### 4.2 真 LLM 验真（`host.log` 原文摘录，不转述）

**OFF 臂**（`v2/evidence/run_f3_off_n16r60_seed42/host.log`）：

```
[meta] events=116336 llm_calls=2878 cached_ratio=0.5122 provider={'openai_compat': 2878} model={'DeepSeek-Flash': 2878}
[meta] OK: 真跑判定通过
  chain_ok=True replay_parity=True first_run_equals_replay=True
  conservation_ok=True final_state_hash=sha256:31b18976529aede800f22ed06868d055904bc7c77c7eb4abdf4ffef9595d25b8
```

**ON 臂**（`v2/evidence/run_f3_on_n16r60_seed42/host.log`，sha8 `28aa5519`）：

```
[life] n_agents=16 rounds=60 events=115494 seconds=2407.4195 log_bytes=54863033
  chain_ok=True replay_parity=True first_run_equals_replay=True
  conservation_ok=True final_state_hash=sha256:bb3ccf1bc15a8980c3bcfcdf2887f080821e8a3fdae07724ca9ec122d155d453
[meta] events=115494 llm_calls=2869 cached_ratio=0.5103 provider={'openai_compat': 2869} model={'DeepSeek-Flash': 2869}
[meta] OK: 真跑判定通过
```

**报告方独立复跑** `python3 -m obs llm-cost --log …/run_f3_on_…/run.jsonl --require-provider openai_compat` →
`by_provider {openai_compat: 2869}`、`by_purpose.dialogue 502`、`degraded 0`、`provider_guard ok:true`、`total tokens 521,639`（与 §4.1 一致）。

**单变量取证**（`v2/evidence/f3_on_env_probe.txt`，sha8 `723ee229`，读 `/proc/3078064/environ`，02:07:14）：
```
HITT_DIALOGUE_EMOTION_ECHO=1
HITT_LLM_PROVIDER=openai_compat
```
`HITT_DIALOGUE_REPAIR`(F-4) / `LIFE_PROMPT_MEMORY_F6*`(F-6) / `LIFE_PROMPT_MEMORY_F6_DEQUP`(L-7) / G-1 相关变量**全部未出现** ⇒ 单变量成立。

### 4.3 读数表

#### ① 机制侧（主证据）

| 量 | OFF 臂 | ON 臂 | 说明 |
|---|---|---|---|
| `payload.ctx.echo` 条数 | **0**（`grep -c '"echo"'` = 0） | **295** | 干净可观测差 |
| `v=f3/1` 条数 | 0 | **295** | 版本一致 |
| `prompted=true` 条数 | 0 | **295** | 提示词确实被插入 |
| 覆盖去重线程 | 0 | **84** | — |
| `sign` 分布 | — | **−1: 280 / +1: 15** | 以安抚（负向）为主 |
| `tier` 分布 | — | 轻 161 / 明显 100 / 很强 34 | — |
| `source` 分布 | 0/0/0 | **`mood` 252 / `text` 9 / `text+mood` 34** | 绝大多数由处境情绪触发，不是语面情感词 |
| `kind` 分布 | — | `soothe` 280 / `cheer` 15 | — |
| `intensity` | — | **min 40 / 中位 40 / max 87** | 预注册要求 ≥30，全部满足 |
| 附：`dialogue_repair` 条数 | 0 | **0** | 证明未与 F-4 混跑 |

#### ② 官方口径（附注级，必须并列假阳性）

| 量 | OFF 臂 | ON 臂 | `band_source` | 说明 |
|---|---|---|---|---|
| 官方 F-3 `echo_rate` | **1/24 = 4.17%**（Wilson 0.74–20.24%） | **5/26 = 19.23%**（Wilson 8.51–37.88%） | `count_only` | 分母 = 相邻对中上一句极性≠0 |
| 分母条数 | 24 | 26 | — | **<30 ⇒ 只报事件数** |
| Δ / CI | — | **+15.06pp**，Newcombe 95% CI **[−4.26, +34.03] 跨 0** | — | **不构成效果证据**（且口径有假阳性） |

#### ③ 机制口径 B（`tools/f3/f3_metrics.py`，报告方重跑）

| 量 | OFF 臂 | ON 臂 | 差分 | `band_source` |
|---|---|---|---|---|
| 可呼应轮次分母 | 0 | **295** | — | `count_only` / **`ok`** |
| 命中（极性一致或含共情标记） | 0 | **37** | — | — |
| `rate` | `null`（无候选） | **0.1254** | 差分不可定义（OFF 无候选） | Wilson95 **[0.0924, 0.1681]** |

> **⚠️ 一处必须并列的自洽性缺口（本轮未解决）**：`prev_polarity_crosscheck`（仅核对 `source` 含 `text` 的条目：字段 `sign` 是否等于日志复算的上一句极性）为 **checked 43 / agree 3 / all_agree=false**。
> 即机制字段 `sign` 与官方词表复算出的极性**在 43 条中只有 3 条一致** ⇒ 两套极性判定**不同源**（`life/emotion.emotion_sign` vs `tools/d5/emotion_lexicon.txt`）。
> 本轮**未排查**该差异 ⇒ `ctx.echo` 只当「触发事实」，**不把 `sign` 当「对方情绪真值」**；列入 §6 L7。

#### ④ 其它读数（官方 `tools/d5`，报告方重跑同口径）

| 指标 | OFF | ON | Δ | 分母 |
|---|---|---|---|---|
| F-1 非功能性闲聊占比 | 71.96%（143 功能性/510） | 70.32%（149/502） | −1.64pp | 510 / 502 |
| F-2 话题漂移率 | 0.0% | 0.0% | 0 | 341 / 332 相邻对 |
| F-6 跨天记忆引用率 | 3.14% | 2.19% | −0.95pp | 510 / 502 |
| F-7a 越界提及率 | 15.10% | 12.35% | −2.75pp | 510 / 502 |
| E-1 每 agent 每回合消息数 | 0.559211（r=57） | 0.570455（r=55） | +0.011 | n=16 |

#### ⑤ 守卫（全族唯一口径 `tools/d5`，未改动）

| 守卫 | OFF 臂 | ON 臂 | 预注册上限 | 判定 |
|---|---|---|---|---|
| `L-7` 8gram 重复率 | **177/510 = 34.71%** | **223/502 = 44.42%** | +6.25pp（`denom_480`，band `[−5.83,+6.25]`） | ⚠️ **+9.72pp ⇒ 击穿** |
| `L-6` 精确重复率 | 53/510 = 10.39% | 46/502 = 9.16% | 不得恶化 | ✅ −1.23pp（方向性下降，不作结论） |
| `L-5` 模板命中率 | 10/510 = 1.96% | 8/502 = 1.59% | 不得恶化 | ✅ −0.37pp（方向性下降，不作结论） |
| `L-13` 内部 token 泄漏 | 10 | **2** | **不得高于基线** | ✅ 未击穿（反而下降） |
| `F-4`（误会与和解闭环） | 0（`dialogue_repair` 命中） | **0** | 不得恶化 | ✅ 未混跑 |
| `F-6`（跨天记忆进对话） | 3.14% | 2.19% | 不得恶化（−5pp 守卫） | ✅ −0.95pp |
| MSG 总量 | 510 | 502 | — | — |
| `degraded` | 0 | **0** | **必须为 0** | ✅ 通过 |

### 4.4 成本（按回合段对齐）

| 项 | OFF 臂 | ON 臂 | 比 |
|---|---|---|---|
| calls | 2878 | 2869 | **1.00×** |
| tokens_total | 519,694 | 521,639 | 1.004× |
| 墙钟 | 2415 s | 2420 s | 1.00× |
| `dialogue` calls | 510 | 502 | 0.98× |
| tokens_in / tokens_out | 228,667 / 291,027 | 236,546 / 285,093 | — |

### 4.5 台词并排（OFF 平淡 vs ON 接住情绪）

> 全部取自 `v2/evidence/run_f3_on_n16r60_seed42/run.jsonl`（sha256 `087072f8…`）；`line` = 该文件行号，`seq` = 事件序号。
> **报告方已逐条机械核对**：下列 10 条 `line`/`seq`/正文首段**全部 `match=True`**（脚本一次性比对，非肉眼）。
> 纪律：**一次观察写一次**，5 组样本不构成「整体变好」。

**样例 1（负向→安抚，`source=text+mood`，tier=很强）** `line=66150 seq=66149 round=45 P004→P001 thread=TH-P004-P001-39`
- `ctx.echo`：`{"intensity":80,"kind":"cheer","mood":"紧绷","prompted":true,"sign":1,"source":"text+mood","tier":"很强","v":"f3/1"}`
- PREV（`line=61409 seq=61408`）：`嗯，是没睡好。地里的水还没着落，心里不踏实。`
- REPLY：`可不是嘛，这阵子啥都紧巴巴的，买袋面粉都得掂量半天。不过你也别太愁，回头我烤炉里出新的，先给你留两块，甜一口算一口。`
- 判读：先接住「心里不踏实」，再接自家处境，最后给具体补偿（留两块点心）。

**样例 2（处境情绪触发，`source=mood`，tier=明显）** `line=25901 seq=25900 round=19 P016→P015 thread=TH-P016-P015-16`
- `ctx.echo`：`{"intensity":55,"kind":"soothe","mood":"饥饿","sign":-1,"source":"mood","tier":"明显","v":"f3/1"}`
- PREV（`line=24022 seq=24021`）：`兰姐，听你这口气就知道今天累得不轻，摊子上的事要紧，你先忙你的，别硬撑着。`
- REPLY：`哎哟，你这么一说我倒真觉得肚子空落落的，早上那碗粉早就没影了。你也是，饿着肚子还惦记我，赶紧先垫两口去。`
- 判读：先承认身体状态，再回敬关心——**双向**。

**样例 3（负向→具体家常处置）** `line=34359 seq=34358 round=24 P012→P007 thread=TH-P012-P007-18`
- `ctx.echo`：`{"intensity":55,"kind":"soothe","mood":"饥饿","sign":-1,"source":"mood","tier":"明显"}`
- PREV（`line=30157 seq=30156`）：`哎哟桂婶您这一说我才觉着饿得前胸贴后背了，那我不跟您客气啦，先来口热乎的，您这锅里炖的啥这么香。`
- REPLY：`哎哟饿成这样可不行，快坐下，婶给你盛碗排骨萝卜汤，刚炖好的，先垫垫肚子再说别的。`
- 判读：接住「饿」并给出可执行动作，附具体菜名「排骨萝卜汤」。

**样例 4（正向/分寸感，`source=text`，tier=明显）** `line=8315 seq=8314 round=9 P006→P003 thread=TH-P006-P003-6`
- `ctx.echo`：`{"intensity":60,"kind":"cheer","mood":"平和","sign":1,"source":"text","tier":"明显"}`
- PREV（`line=5672 seq=5671`）：`方老师，这礼物太贵重了，我收着心里不踏实。`
- REPLY：`阿禾，你能这么想，说明你心里有分寸，这比礼物本身金贵多了。收下吧，就当是老师给你的一份心意，往后你遇到想不通的题，随时来问我就好。`
- 判读：把「不踏实」重解为「有分寸」，给出收下的台阶。

**样例 5（⚠️ 反面样例：同一段文本被相邻两线程各生成一次，L-7 恶化的直接证据）**
- `line=39718 seq=39717 round=31 thread=TH-P005-P006-30 turn=1`
- `line=41407 seq=41406 round=32 thread=TH-P005-P006-31 turn=1`
- 两条 `ctx.echo` 相同：`{"intensity":40,"kind":"soothe","mood":"紧绷","sign":-1,"source":"mood","tier":"轻"}`
- REPLY（两条正文**逐字相同**）：`哎，陈医，你这么一说我倒真觉得肩上是有点沉。你最近是不是也累着了？先别光顾着我，你自己那口热水喝上了没？`
- 判读：精确重复（L-6）+ 8gram 重复（L-7）被顶高。**必须与 §0.3 的 L-7 击穿一起引用，不许只引正面样例。**

### 4.6 截图

**（a）正文图 · 结果回放（三视图 + 600px 判读）** —— 来自 ON 臂**真实运行**日志，非合成：

| 文件 | 视图 | sha8 |
|---|---|---|
| `v2/evidence/f3_shots/run_f3_on_n16r60_seed42-chat-087072f8.png` | 对话流（1500×950） | `a1c4f6cb` |
| `v2/evidence/f3_shots/run_f3_on_n16r60_seed42-rhythm-087072f8.png` | 节律·串门（1300×950） | `486befa7` |
| `v2/evidence/f3_shots/run_f3_on_n16r60_seed42-spread-087072f8.png` | 闲话怎么传开（**空态**，见下） | `c94d0a1f` |
| `v2/evidence/f3_shots/run_f3_on_n16r60_seed42-600-087072f8.png` | 600px 判读 | `a0a905b0` |

- 渲染命令：`gen_threads.py --require-complete`（输出 `TURN_SEAL 60 条覆盖 round 0..59`；events 115494 / messages 502 / threads 170）→ `dialogue_shots.sh` 四视图；命名 `<batch>-<view>-<sha8>`，`sha8=087072f8` 与 `run.jsonl` 一致（脚本自派生并自校验）。
- **chat 视图人工核验**：页面显示「事件 115494 · 消息 502 · 线程 170 · 多轮 89」，并可读到真实台词（如「老石，你尝尝这个新烤的核桃面包，我减了糖…」）⇒ 非空图、非占位。
- **spread 视图如实说明**：该页为**空态**——页面自述「本批日志 refs 全为空（没有一条消息引用别的消息），所以「谁把话传给谁」在真源上没有记录…这里显示空态，不用相似度硬凑」。**这是数据事实**（F-3 不产生 `refs`，与 R7 记录的「世界事件对对话零暴露」同族），**不是渲染失败**；不以拼图或旧图替代。

**（b）附录图 · 运行中快照（LIVE 跟随，非回放）**

| 文件 | 说明 | sha8 |
|---|---|---|
| `v2/evidence/f3_shots/run_f3_on_n16r60_seed42-live-chat-running.png` | 运行中快照，采集于 **02:11:22 +08:00**（画面「LIVE · 运行中 round 0 · 34 事件 · 跟随中」），pid 3078054/3078064 | `fa852a97` |

- **⚠️ 未达「round ≥ 20 版本」，如实登记**：该窗口**未被采集到**——跑批已于 **02:47:05** 结束，而负责盯 round≥20 的后台监视器在我被唤醒前就已退出，**运行中窗口关闭**，事后无法补拍（补拍只能是回放，不能称「运行中」）。
  ⇒ 本节正文一律用 **(a) 结果回放图**；**(b) 仅作附录**说明「早期窗口」。
- **未用重复字节文件充数**：同批曾产出的 `-live-rhythm/-live-spread` 两图因 LIVE 模式视图未切换、与 chat 快照字节数相同（786,482 B），**已删除**并在 `render.log` 中记为作废。

### 4.7 证据文件 sha256 台账（逐条可核）

| # | 文件 | 用途 | sha8 |
|---|---|---|---|
| E1 | `v2/evidence/run_f3_off_n16r60_seed42/run.jsonl` | OFF 臂数据 | `19d5cb03` |
| E2 | `v2/evidence/run_f3_off_n16r60_seed42/meta.json` | OFF 臂元数据 | `8ebe6731` |
| E3 | `v2/evidence/run_f3_on_n16r60_seed42/run.jsonl` | ON 臂数据 | `087072f8` |
| E4 | `v2/evidence/run_f3_on_n16r60_seed42/meta.json` | ON 臂元数据 | `2b4cdf25` |
| E5 | `v2/evidence/run_f3_on_n16r60_seed42/host.log` | ON 真跑判定 + 成本 | `28aa5519` |
| E6 | `v2/evidence/f3_off_official.json` / `.md` | 官方口径 OFF | `3835ba58` / `eeb9e910` |
| E7 | `v2/evidence/f3_on_official.json` / `.md` | 官方口径 ON | `d8cf5b80` / `533f9df3` |
| E8 | `v2/evidence/f3_readings.json` | 双口径 + Wilson/Newcombe | `d286b550` |
| E9 | `v2/evidence/f3_code_fingerprint_scope.md` | 口径 B 定义 | `bc4215d9` |
| E10 | `v2/evidence/f3_code_fingerprint_prerun.txt` / `_files_prerun.txt` | OFF 前指纹 | `b0d2932e` / `dd316401` |
| E11 | `v2/evidence/f3_code_fingerprint_on_pre.txt` / `_on_post.txt` | ON 前/后指纹 | `85d64a01` / `6222121a` |
| E12 | `v2/evidence/f3_on_env_probe.txt` | 单变量取证 | `723ee229` |
| E13 | `v2/evidence/f3_echo_falsepos_samples.md` | 假阳性反例（控臂 `run_f6_off`） | `098ef8f9` |
| E14 | `v2/evidence/f3_audit_echo.py` | 抽样/审计脚本 | `2e808095` |
| E15 | `tools/f3/f3_metrics.py` / `f3_samples.py` | 双口径复算 / 样例抽取 | `249113b7` / `14eec089` |
| E16 | `code/frontend/sample/dialogue_run_f3_on_n16r60_seed42/threads.json` | 截图数据源 | `b062c200` |
| E17 | `v2/evidence/f3_shots/`（4 结果图 + 1 运行中图 + `render.log`） | 可视证据 | 见 §4.6；`render.log a76a0520` |
| E18 | `v2/evidence/d3_noiseband_bootstrap.json` | L-7 噪声带上界来源 | 见该文件（`denom_480` 档 L-7 = 6.25pp） |

---

## 5. 纪律自查

| # | 纪律 | 自查结果 |
|---|---|---|
| 1 | 跑批串行、起跑前 `pgrep` | ✅ ON 臂起跑前无残留；报告阶段复核 `pgrep` 亦无模拟进程 |
| 2 | 跑批期间未改 `code/life`/`orchestration`/`config`/`engine` | ✅ 仅写 `reports/`（骨架）与 `v2/evidence/f3_shots/`（采集）；四子树由口径 B 前后同值证明未漂 |
| 3 | 无长 sleep、`setsid` 启动 | ✅ 由 life-engineer 执行；报告方未起任何模拟进程（`live_run.py` 会另起世界，刻意未用） |
| 4 | 真 LLM 经 `obs llm-cost` 验证 | ✅ 报告方独立复跑：`openai_compat 2869`、`degraded 0`、`provider_guard ok:true` |
| 5 | 结论绑 commit sha，不用 master HEAD 顶替 | ✅ OFF `6b7ae8a`（dirty-tree，第二锚）/ ON `6f87363` |
| 6 | 单变量：ON 臂只开 F-3 | ✅ `/proc/<pid>/environ` 取证，F-4/F-6/L-7/G-1 全空 |

---

## 6. 局限与未验证项（**如实并列，不替实现方补圆**）

| # | 未验证 / 局限 | 为什么没做到 | 需要什么才能做 |
|---|---|---|---|
| L1 | **只覆盖回复路径**，`_initiate`（`agent.py:1077`）未接入 | 实现范围如此 | 接到 initiate 路径后另开一臂 |
| L2 | 官方口径**有假阳性**，且同一句可能被计两次 | 判据不区分「接住」与「各自表达」 | 口径变更（词表+配对），单独一轮 |
| L3 | 两臂**不同 sha、不同时间窗、单次运行** ⇒ 无 CI、不做显著性判定 | 跨批同 seed 非同分布 | 同树同窗多轮交替 |
| L4 | 口径 B **不覆盖** `code/frontend`/`tests`/`obs`/`freeze_cache` | 只看四子树 | 全树指纹（需改排除规则） |
| L5 | OFF 臂 `meta.code_sha` **不含 F-3**，代码身份靠口径 B 第二锚 | 该批跑在 dirty-tree | 重跑 OFF 臂（花钱）或以指纹为准（本轮选择） |
| L6 | 单测「27 passed」**我未复跑** | 属实现方自述；跑批纪律期间不改 code | 复跑 `pytest code/life/tests/test_f3_emotion_echo.py` 并留输出 |
| L7 | **`prev_polarity_crosscheck` 43 条仅 3 条一致** ⇒ 机制 `sign` 与官方词表极性**不同源** | 本轮未排查 | 对齐两套极性口径，或统一词表后重算 |
| L8 | **L-7 击穿** ⇒ 效果结论「不可判」 | 固定 `prompt_line` 造成句式收敛 | 降低句式约束 / 提供多种说法后重测 |
| L9 | 「37/295 接住」仍依赖**同一套有假阳性的判据** | 口径 A 内在缺陷 | 人工或 LLM 复核子集，另立口径 |
| L10 | 本轮**无 round≥20 的运行中快照**（只有 round 0 早期窗口，§4.6b） | 采集窗口在跑批结束后关闭 | 下次跑批时在 round≥20 阶段主动采集 |
| L11 | 本轮**单次观察**，不外推「稳定成立」 | 一臂一 seed | 多 seed / 多次重复 |

---

## 7. 下一步建议

1. **先修 L-7 的来源**：`prompt_line` 固定句式是元凶 ⇒ 改为「若干可选说法 + 不指定句式」，再测 L-7 是否回落到带内。**这是本维度继续推进的前提**。
2. **统一极性口径（L7）**：把 `life/emotion.emotion_sign` 与 `tools/d5/emotion_lexicon.txt` 对齐，否则「接住」判定永远双口径打架。
3. **口径修复（L2）**：把官方「同极性即呼应」换成配对式（谁接住了谁的哪句话），这是 F-3 能被度量性比较的前提。
4. 把 F-3 接到 `_initiate`，消掉 L1 边界。
5. 多 seed 重复一次，把 L11 的「单次观察」升级为可写「稳定」的证据。

---

> 引用纪律：数据/日志/证据 ⇒ 文件名 + sha8；源码/配置 ⇒ 该臂 commit sha + `文件:行号`。
> **读数独立性声明**：本文件读数均由报告方**独立复算**——`tools/d5/dialogue_metrics.py` 双臂重跑、`tools/f3/f3_metrics.py` 双臂重跑、`obs llm-cost` 重跑、`ctx.echo` 分布脚本重算（295/295/84 与各分布逐项一致）、5 组样例共 10 条 `line`/`seq`/正文逐条比对（全部 match）。结论与 `impl-notes.md` 一致，未发现需要退回补齐的缺项。
