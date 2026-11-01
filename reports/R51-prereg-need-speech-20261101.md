# R51 预登记（先冻结判据，再看数据）· 需求的「人话化 + 紧迫门控」

- 登记时刻：**2026-11-01T22:04:42+08:00**（**先于任何 R51 跑批**；时序可用
  `git log --format='%h %ad %s' --date=iso -- reports/R51-prereg-need-speech-20261101.md` 核对，
  该文件的 commit 时间必须**早于**两臂 `start_epoch.txt`）
- 分支：`feat/r51-need-speech`（从 `82bdb3f` 新建；**不碰 master**）
- 臂开关：**`HITT_NEED_SPEECH`**（沿用仓库既有 `HITT_*` 命名风格；**默认关**）
- 尺子：`tools/metrics/need_to_speech.py`（`ruler_version=r51-need-speech-v1`，只读、零 LLM、零跑批）
- 本轮只推进这一个维度。**本文件一经提交不得改判据**；发现判据有缺陷只能在报告里写
  「本轮判据缺陷」，不得事后调阈值。

---

## 0. 为什么选这条臂（事实，非推断）

| 事实 | 证据（可复算） |
|---|---|
| `_mood_line()` **无条件**把机器口径的最紧需求拼进提示词（`情绪：饥饿；最紧的需求：satiety=12`），且被拼进**两个**唯一装配点 | `code/life/agent.py:1566-1572`（`_mood_line`）+ `:1859`（`_dialogue_prompt`）/ `:1882`（`_reply_prompt`） |
| 191 条对话 **100%** 带 `ctx.need`，其中 **70/191 = 36.65%** 的值 ≥40（未到紧迫） | 见 §2 复算命令① |
| 真紧迫（<40）121/191 = 63.35%；最紧需求维度 `leisure 79 / satiety 71 / social 24 / esteem 13 / mastery 4`、**`energy` 0 次** | 同上 |
| 提示词全是英文维名 + 裸数值 ⇒ 对话正文里生活语汇几乎不出现：疲劳族 **2/191 = 1.05%** | 同上（词表见 §3.1） |
| 提示词原文**不落盘**：`LLM_CALL.payload` 只有 `prompt_hash` / `meta_digest` | `code/obs/` 侧日志结构（R49 §10 已记录同一限制） |

> 一句话：**"缺什么"被机器口径无条件塞进提示词，而"累/困"这种最典型的生活语汇在对话里几乎为零**。
> 本轮检验的机制假设是：把需求换成人话、并且只在真紧迫时才进提示词，能让生活语汇进入对话正文，
> 同时把 36.65% 的"无事生非"清掉。

---

## 1. 干预（单变量，逐字冻结）

改动**只落在** `code/life/agent.py::_mood_line()`（+一个模块级短语表 + 开关读取 + 一处 additive 审计字段）：

| 态 | `_mood_line()` 的返回 |
|---|---|
| **OFF（默认；未设 / 非 1/true/yes/on）** | `情绪：{mood}；最紧的需求：{dim}={val}` —— **与改动前逐字节相同**；且**不写**任何审计字段 ⇒ `payload` 亦逐字节不变 |
| **ON 且 `val ≥ 40`（不紧迫）** | `情绪：{mood}` —— **不占提示词预算**，最紧需求整段不出现 |
| **ON 且 `val < 40`（真紧迫）** | `情绪：{mood}；{人话短语}` —— 机器口径 `dim=val` **不出现** |

- 紧迫线 **40** 与 `code/life/dialogue_threads.py::mood_label` 的阈值**同源**（全维 ≥40 时它已返回「平和」），
  不新造阈值。
- 人话短语表**逐维冻结 3 条**（`_NEED_SPEECH_PHRASES`），轮换用确定性计数器，避免 191 条对话都写成同一句
  "我饿了"（多样性塌陷是 R49 §11 记录过的风险）。
- ON 臂额外写一个 **additive 审计键** `payload.ctx.need_speech = {"dim","value","injected"}`。
  **理由（必要的最小配套）**：提示词原文不落盘，若不留这个键，"噪声需求注入率"就**无法被观测**，
  只能靠结构推断。该键沿用仓库既有 additive 审计先例（`ctx.memory_refs` / `ctx.dequp` / `ctx.l7struct`）：
  **OFF 臂该键不出现**。

> 一句话：ON/OFF 两臂之间**只差** `_mood_line()` 那一行的渲染（+ON 臂的审计键），不改任何配置、世界态、
> 随机数消费或其它模块。

---

## 2. 零成本基线（跑前、不花 LLM；命令原文 + 输出）

```bash
# ① R49-off 冻结批上先立尺子（零 LLM）
python3 tools/metrics/need_to_speech.py \
    --log v2/evidence/r49-diversity-off-20261101_n16r24_s42/run.jsonl --label r49-off --mde
# → n_msgs=191 n_with_need=191 noise_inject=70/70 urgent_keep=121/121 fatigue=2/191 food=52/191
# → mde={"fatigue_hit": 5.47, "food_hit": 13.59}
#   （该日志 sha256 见 R49 报告 §0：40d1bb09c3face4afabbae8e786eb2f7aaaf3ecb079171aaa83a6425b8430434）

# ② 确定性自证（两次运行逐字节相等）
python3 tools/metrics/need_to_speech.py --log <同上> --out-json /tmp/a.json
python3 tools/metrics/need_to_speech.py --log <同上> --out-json /tmp/b.json
cmp /tmp/a.json /tmp/b.json && echo DETERMINISTIC
```

基线读数（R49-off，`n=191`，`code_sha 161f115`，本尺子首次读数）：

| 读数 | 值 | Wilson95 |
|---|---|---|
| `need_inject_rate`（带 `ctx.need` 的消息占比） | 191/191 = **100%** | [98.03, 100] |
| `noise_need_rate`（值 ≥40 的占比） | 70/191 = **36.65%** | [30.14, 43.68] |
| `urgent_need_rate`（值 <40 的占比） | 121/191 = **63.35%** | [56.32, 69.86] |
| `noise_inject_rate`（值 ≥40 **且被注入**） | 70/70 = **100%**（改前无条件注入） | — |
| `urgent_keep_rate`（值 <40 且被注入） | 121/121 = **100%** | — |
| `fatigue_hit`（疲劳族命中） | 2/191 = **1.05%** | [0.29, 3.74] |
| `food_hit`（饮食族命中） | 52/191 = **27.23%** | [21.41, 33.94] |

**基线给出的两条硬约束**

1. `noise_inject_rate` 已是 **100%** ⇒ 门控一旦生效，这条读数必然落到 **0%**，是**结构性**的，
   因此它只能当**机制闸**，绝不能当效果判据；
2. `fatigue_hit = 1.05%` ⇒ 反过来意味着**分母极小**：`n=191×2`、双侧 `α=0.05`、`power=0.80`
   反解的 **MDE = 5.47pp**（即 ON 臂至少要有 ≥7/191 ≈ 3.66% 才可能显著）。**低于 MDE 一律写「不可判」，
   不得写"趋势/方向为正"。**

---

## 3. 指标与判据（**预登记，阈值不得事后改**）

### 3.1 尺子身份（冻结）

| 项 | 值 |
|---|---|
| `ruler_version` | `r51-need-speech-v1` |
| `impl_sha256` / `lexicon_sha256` | 由 `need_to_speech.py` 输出（值随文件内容，报告里抄录） |
| 紧迫线 `URGENT_THRESHOLD` | **40**（与 `DT.mood_label` 同源） |
| 疲劳族词表 `FATIGUE`（冻结，不增删） | `累 / 困 / 乏 / 歇 / 打盹 / 打哈欠 / 睁不开眼 / 缓口气` |
| 饮食族词表 `FOOD`（冻结，不增删） | `吃 / 饭 / 饿 / 面包 / 菜 / 汤 / 茶 / 粥 / 饼 / 干粮` |
| 命中口径 | **子串命中**（不做分词，避免第二套口径） |
| 样本 | `run.jsonl` 中 `type ∈ {MSG_DM, MSG_PUBLIC, MSG_GROUP}` 且 `payload.body` 非空 |

### 3.2 机制闸 M1（先判"门控有没有生效"，与"效果"分开）

| 编号 | 指标 | 方向 | 达标线 | 依据 |
|---|---|---|---|---|
| **M1** | ON 臂 `noise_inject_rate` **且** `urgent_keep_rate` | 前者 → 0，后者保持 1 | **`noise_inject_rate ≤ 1.0%` 且 `urgent_keep_rate ≥ 99.0%`** | 门控是**结构性**改动：不清噪声 ⇒ 干预没生效；误杀真紧迫 ⇒ 干预做错了方向。两条同时成立才算接线成功 |
| M1′（辅助，不作闸） | 单测里的 OFF 逐字节等价 + ON/OFF 提示词 diff 只有 `_mood_line()` 一段 | — | 只记录 | 提示词不落盘，只能靠单测证明；见 §3.4 U5 |

### 3.3 效果判据 E1–E3

| 编号 | 指标 | 方向 | 达标线 | 说明 |
|---|---|---|---|---|
| **E1（主）** | `fatigue_hit`（疲劳族命中率） | ON **>** OFF | **Δ ≥ +5.5pp（=MDE 5.47pp 上取整）且 Fisher 双侧 `p < 0.05`** | 这是"累/困"进入对话的唯一可观测证据；低于 MDE 判「不可判」 |
| E2（次） | `food_hit`（饮食族命中率） | ON **>** OFF | **只描述，不进判据** | 干扰大（`satiety` 本来就是最紧需求 71 次），且"饭吃"类词在中文里极易被非需求语境触发 |
| E3 | `noise_need_rate` / `urgent_need_rate` / `dim_dist` / `mood_dist` | 描述 | **只描述** | 它们衡量**世界态**，ON 臂只改提示词文本、不改世界态 ⇒ 两臂差异只可能是 LLM 输出反作用，**不作判据** |

### 3.4 分母下限与不可判条件（**逐条触发即写「不可判」，不得靠解释绕过**）

| # | 条件 | 触发后写法 |
|---|---|---|
| U1 | 任一臂 `n_msgs < 160` | 该臂所有比率**不判**（写「分母不足：n=…，下限 160」） |
| U2 | 任一臂 `obs llm-cost --require-provider openai_compat` 不过 / `degraded ≠ 0` / provider 非 `openai_compat` | **全部作废**，不得计入任何效果结论 |
| U3 | M1 未达 | 判「机制未生效」；E1 仍可报读数，但**结论上限只能是"机制未生效"** |
| U4 | M1 达标但 E1 的 `\|Δ\| < 5.5pp` 或 `p ≥ 0.05` | 判「效果未达成」并给出所需样本量（不得写"趋势/方向为正"） |
| U5 | ON/OFF 两臂的提示词差异**不止** `_mood_line()` 一段（单测红）/ 两臂 `prompt_fn_sha256` 相同 | 判「接线未成立」，整轮作废 |
| U6 | `run_batch.rc ≠ 0` 或 `wc -l(run.jsonl) ≠ meta.events` | 该臂作废 |

### 3.5 三档口径（**本轮最高只能到第二档，第三档预登记即排除**）

| 档 | 本轮能否声称 | 判据 |
|---|---|---|
| ① 机制接通 | 可声称 | M1 达标 + OFF 逐字节等价单测绿 + `HITT_NEED_SPEECH=1` 见于 `env_manifest.txt` |
| ② 效果成立 | **仅当 M1 达标 且 E1 达标** | 见 §3.2/§3.3 |
| ③ 生活气息提升 | **本轮预登记即声明不判** | 没有人工盲评、没有 judge 语义维度、没有跨 seed 复现 ⇒ ③ 无证据来源，**禁止表述为"更像真人/生活气息更强"** |

---

## 4. 成本预估（跑前先算，超预算不上）

- 参照 R49 同参数（`agents=16 rounds=24 seed=42`）：单臂 `calls≈2255`、`tokens_total≈33.5 万`、`degraded=0`、墙钟 ≈ 22–23 min。
- 本轮两臂**串行** ⇒ 预计 **总墙钟 ≈ 45–55 min**、`calls ≈ 2×2255`、`tokens_total ≈ 2×33.5 万`。
- 若首臂墙钟 > 45 min，**仍按串行跑完第二臂**，不并行、不加轮次、不加 seed。

---

## 5. 两臂定义（除一个变量外逐字相同）

| 项 | OFF 臂 | ON 臂 |
|---|---|---|
| 目录 | `v2/evidence/r51-need-speech-off-20261101_n16r24_s42/` | `v2/evidence/r51-need-speech-on-20261101_n16r24_s42/` |
| 代码 | `feat/r51-need-speech`（含本臂代码，**开关关**） | 同一 commit |
| env 共有 | `HITT_LLM_PROVIDER=openai_compat`、`HITT_WORLD_SEED=42` | 同左 |
| **唯一差异** | `HITT_NEED_SPEECH` 不设 | **`HITT_NEED_SPEECH=1`** |
| 参数 | `--seed 42 --agents 16 --rounds 24 --flush-every 2` | 同左 |
| 串行 | `flock /tmp/hitt.batch.lock` + 三重 `pgrep` + `tools/d5/preflight.sh`；两臂**串行**，`setsid` 起进程 | 同左 |

> 说明：本轮**不**带 `LIFE_PROMPT_SCENE=1` / `HITT_DIALOGUE_PUBLIC_REPLY=1`（R49 带它们是为了与 `c1-scene-a1` 横向对照）。
> 本轮判据只用**本轮两臂自比**，不需要横向基线的可比性，少两个开关 = 少两个潜在混淆源。

---

## 6. MDE 计算公式（可复算）

两独立比例、双侧 `α=0.05`（`z_α/2=1.96`）、`power=0.80`（`z_β=0.8416`）：

```
p̄ = (p1·n1 + p2·n2)/(n1+n2)
SE = sqrt(p̄(1−p̄)(1/n1 + 1/n2))
可检 ⇔ |p1 − p2| / SE − z_β ≥ z_α/2
```

代入 `p1 = 0.010471`（`fatigue_hit` 基线）、`n1 = n2 = 191` ⇒ **MDE = 5.47pp**；
即 ON 臂 `fatigue_hit` 至少要达到 **3.66%（7/191）** 才可能在 α=0.05 / power=0.80 下被检出。

---

## 7. 预登记声明

1. 本文件**先于**任何 R51 跑批提交（时间戳见页首，git commit 时间可核）。
2. 判据 M1 / E1 / E2 / E3 与不可判条件 U1–U6 **一经提交不得修改**；实现阶段若发现判据无法计算，
   只能在报告里写「本轮判据缺陷」并作废，**不得**改阈值后重跑同一批数据。
3. 三档口径本轮**最高只承诺第二档**；③ 生活气息提升**不在本轮主张范围**。
4. 若 ON 臂未达成预期，报告必须**如实写"未达成"及可能原因**，不得用"趋势/方向为正"填补。
