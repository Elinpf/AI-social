# R49 预登记（先冻结判据，再看数据）· 居民对话的「具体性起句 / 措辞多样性」

- 登记时刻：2026-11-01 18:2x +08:00（**先于任何 R49 跑批**；时序可用 `git log --follow reports/R49-prereg-diversity-20261101.md` 核）
- 分支：`feat/r49-life-diversity`，基线 `37c3036`（`feat/r46-c1-effect-metrics`），**不碰 master**（本地 master 仍须为 `94e272a`）
- 臂：`HITT_D12_DETAIL`（D12-A 具体性插槽，**默认关**）——**复用既有臂，不新造开关**
- 本轮只推进这一个维度。**本文件一经提交不得改判据；发现判据有缺陷只能在报告里写「本轮判据缺陷」，不得事后调阈值。**

---

## 0. 为什么选这条臂（事实，非推断）

| 事实 | 证据（可复算） |
|---|---|
| `distinct_body_ratio` 在现行树上**已是天花板** | `tools/metrics/lex_template_rate.py --log v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl` ⇒ `distinct_body_ratio 191/191 = 1.000`（Wilson95 `[0.9803, 1.0]`）⇒ **该指标本轮无法改善**，只能记「不可判（天花板）」 |
| `opener_top10_share` 已很低 | 同上 ⇒ `0.073298`（14/191，Wilson95 `[0.0442, 0.1193]`） |
| 句中具体性已饱和，但**起句具体性没饱和** | 新尺子 `tools/metrics/r49_detail_opener.py` 同一日志 ⇒ `detail_body 187/191 = 97.91%`、`detail_line 165/191 = 86.39%`，但 **`detail_opener6 = 51/191 = 26.70%`**（Wilson95 `[0.2093, 0.3339]`） |
| 句中具体性的载体主要是**开头括号旁白** | 同上 ⇒ `paren_lead 169/191 = 88.48%` |
| D12-A「具体性插槽」代码已存在且**只加不减** | `git show --numstat feat/d12-detail`（`a6ae5e5`）⇒ `15 0 code/life/agent.py`；提示词增量 1 句 55 字 |
| D12-A 的**干净同 seed ON/OFF 两臂从没跑过** | `v2/evidence/d12a_real_result.md` §0.5 待办 4：「干净的同 seed 开/关两臂**尚未完成**」（原两臂被 A1 禁旁白混淆，属两变量） |

> 一句话：**"具体性"这一层不是没有改进空间，而是"具体性落在了旁白里、没落在开口上"**。D12-A 的提示词增量恰好是「先说一个手上或眼前的具体东西，再顺着它说下去」——**它干的就是把具体物从旁白搬到句首**。这就是本轮要检验的机制假设。

---

## 1. 干预（单变量，逐字冻结）

代码改动**逐字复用** `feat/d12-detail@a6ae5e5` 的 15 行（`code/life/agent.py`）：新增 `_d12_detail_line()`，并在 `_dialogue_prompt` / `_reply_prompt` 各插入 1 行调用。开关 `HITT_D12_DETAIL=1` 生效，未设/其它值 ⇒ 返回空串 ⇒ **提示词与 OFF 臂逐字节相同**。

提示词增量（唯一条目，逐字冻结，**不得在跑批后修改**）：

```
说话前来得及的话，先说一个你此刻手上或眼前的具体东西（一样器物、一个数、
一个刚发生的小事），再顺着它说下去。
```

（实际注入为单行，此处仅为排版换行；渲染时 `\n` + 单行文本。`prompt_fn_sha256` 两臂必须**不同**，作为接线证据。）

---

## 2. 两臂定义（除一个变量外逐字相同）

| 项 | OFF 臂 | ON 臂 |
|---|---|---|
| 目录 | `v2/evidence/r49-diversity-off-20261101_n16r24_s42/` | `v2/evidence/r49-diversity-on-20261101_n16r24_s42/` |
| 代码 | `feat/r49-life-diversity`（含 D12-A 代码，开关关） | 同一 commit |
| env 共有 | `HITT_LLM_PROVIDER=openai_compat`、`HITT_WORLD_SEED=42`、`HITT_DIALOGUE_PUBLIC_REPLY=1`、`LIFE_PROMPT_SCENE=1` | 同左 |
| **唯一差异** | `HITT_D12_DETAIL` 不设 | **`HITT_D12_DETAIL=1`** |
| 参数 | `--seed 42 --agents 16 --rounds 24 --flush-every 2` | 同左 |
| 模型 | 仓库 `code/config/llm.json` 的 `endpoint`/`model`（真 LLM，`openai_compat`） | 同左 |
| 串行 | `tools/d5/preflight.sh --tag r49-…` + `flock /tmp/hitt.batch.lock` + 三重 `pgrep`；两臂**串行**，不并行 | 同左 |

> env 里带 `LIFE_PROMPT_SCENE=1` / `HITT_DIALOGUE_PUBLIC_REPLY=1` 的**理由**：这两个开关在**两臂中相同**，不破坏单变量；带上它们是为了让本轮 OFF 臂与仓库里**同结构既有基线**（`c1-scene-a1-20261101_n16r24_s42`，`code_sha 8b64615`）可横向对照。**判据只用本轮 ON/OFF 两臂**，横向基线只作描述。

---

## 3. 指标与判据（**预登记，阈值不得事后改**）

### 3.1 尺子（冻结身份）

| 尺子 | 路径 | 冻结标识 | 口径要点 |
|---|---|---|---|
| 套路化/多样性 | `tools/metrics/lex_template_rate.py` | `lexicon_version=lex-template-v1`、`lexicon_sha256=52ff281462b19bd3fb5ad1f13086a0acfcc573014c812601a6561998b4aad397` | `opener_top10_share`、`distinct_body_ratio`、`backref_hit` |
| **具体性起句（本轮新立）** | `tools/metrics/r49_detail_opener.py` | `ruler_version=r49-detail-opener-v1`、`impl_sha256=242ea2c8973bb9849d9767a15194f3f6f89ab6372a167308069fd0ecfb6ecd5a`、`lexicon_sha256=e8507082b0915f93eb62ab200969da17d4a700e1b337e0d97ce2355196dd7477` | 词表**逐字取自** `v2/evidence/d12c_proxy_lexicon.txt §P1`；开头括号旁白用**与 lex_template_rate 相同正则**剥掉后取**前 6 字** |

两把尺子都是**只读、零 LLM、零跑批**，两次运行输出逐字节相等（已在 `c1-scene-a1` 日志上验过 `cmp` 相等）。

### 3.2 机制闸 M1（先判"机制有没有被采纳"，与"效果"分开）

| 编号 | 指标 | 方向 | 达标线 | 依据 |
|---|---|---|---|---|
| **M1** | `detail_opener6`（起句具体性） | ON **>** OFF | **Δ ≥ +11.7pp** 且两臂 Wilson95 **不重叠** | 用 OFF 臂预期 `p≈0.267`、两臂各 `n≈191`、`α=0.05`（双侧）、`power=0.80` 反解的最小可检效应 **MDE = 11.7pp**（公式见 §5）。阈值**等于 MDE**，不额外放宽 |
| M1′（辅助，不作闸） | `detail_body`（含旁白整句具体性） | — | 只记录 | 该值在 `c1-scene-a1` 已 `97.91%`，**结构上近天花板**，用它判"改善"就是重犯 D12-A §0.5 的混淆 |

**M1 未达 ⇒ 判定为「机制未生效」**（不是"无效"）。按仓库既有五档词（`机制未生效 / 作废 / 无效(换长度) / 无效 / 有效`），本轮对应「机制未生效」。

### 3.3 效果判据 E1–E3（只有在 M1 通过后才逐条看）

| 编号 | 指标 | 方向 | 达标线 | 说明 |
|---|---|---|---|---|
| **E1** | `opener_top10_share` | ON **<** OFF | **Δ ≤ −5.9pp**（ON `rate` 点估计）且 `ON` 的 Wilson95 上界 < `OFF` 点估计 | 用 OFF 预期 `p≈0.0733`、`n≈191×2` 反解的 **MDE = 5.9pp**（`7.33% → ≤1.43%` 才可判）。**低于 MDE 一律写「不可判」**，不得写"趋势/方向为正" |
| **E2** | `distinct_body_ratio` | ON **>** OFF | **本轮不判** | OFF 臂基线已是 `1.000` ⇒ **天花板，无改善空间**。预登记即声明「不可判（天花板）」，**不事后改成"保持不降"来充效果** |
| **E3** | `backref_hit` | 无方向 | **只描述，不进判据** | 干预文本**未针对回指**，把它写成判据就是事后加判据（D12-B 已证明提示词层改不动措辞类指标，见 `v2/evidence/d12b_result.md` §2） |

### 3.4 分母下限与不可判条件（**逐条触发即写「不可判」，不得靠解释绕过**）

| # | 条件 | 触发后写法 |
|---|---|---|
| U1 | 任一臂 `n_msgs < 160` | 该臂所有比率**不判**（写「分母不足：n=…，下限 160」） |
| U2 | 任一臂 `obs llm-cost --require-provider openai_compat` 不过 / `degraded ≠ 0` / provider 非 `openai_compat` | **全部作废**，不得计入任何效果结论 |
| U3 | M1 未达 | 判「机制未生效」；E1 仍可报读数，但**结论上限只能是"机制未生效"** |
| U4 | M1 达标但 E1 的 |Δ| < MDE(5.9pp) | 判「效果不可判（效应低于本采样结构的 MDE）」并给出所需样本量 |
| U5 | 两臂 `prompt_fn_sha256` 相同（接线断了） | 判「接线未成立」，整轮作废 |
| U6 | `run_batch.rc ≠ 0` 或 `TURN_SEAL` 不完整（<24 个 seal） | 该臂作废 |

### 3.5 三档口径（**本轮最高只能到第二档，第三档预登记即排除**）

| 档 | 本轮能否声称 | 判据 |
|---|---|---|
| ① 机制接通 | 可声称（M1 之外的接线事实，如 `prompt_fn_sha256` 不同、`HITT_D12_DETAIL=1` 见 `/proc`） | 与效果无关，单独陈述 |
| ② 效果成立 | **仅当 M1 达标 且 E1 达标**时 | 见 §3.2/§3.3 |
| ③ 生活气息提升 | **本轮预登记即声明不判** | 本轮**没有**人工可读性盲评、没有 judge 语义维度、没有跨 seed 复现 ⇒ ③ 无证据来源，**禁止表述为"更像真人/生活气息提升"** |

---

## 4. 成本预估（跑前先算，超预算不上）

- 参照：`c1-scene-a1-20261101_n16r24_s42`（同参数）`duration_sec=1359`（22.6 min），`total.calls=2255`、`tokens_total=321172`、`provider=openai_compat`、`degraded=0`。
- 本轮两臂**串行** ⇒ 预计 **总墙钟 ≈ 45–55 min**、`calls ≈ 2×2255`、`tokens_total ≈ 2×32 万`。
- 若首臂墙钟 > 45 min，**仍按串行跑完第二臂**，不并行、不加轮次、不加 seed。

---

## 5. MDE 计算公式（可复算）

两独立比例、双侧 `α=0.05`（`z_α/2=1.96`）、`power=0.80`（`z_β=0.8416`）：

```
p̄ = (p1·n1 + p2·n2)/(n1+n2)
SE = sqrt(p̄(1−p̄)(1/n1 + 1/n2))
可检 ⇔ |p1 − p2| / SE − z_β ≥ z_α/2
```

反解（`n1=n2=191`）：

| 指标 | OFF 基线 `p1` | MDE |
|---|---|---|
| `detail_opener6`（M1） | 0.2670 | **11.7pp** |
| `opener_top10_share`（E1） | 0.0733 | **5.9pp** |
| `backref_hit`（E3，只描述） | 0.1204 | 7.9pp |

复算命令（不依赖 scipy，纯标准库）：

```bash
python3 - <<'EOF'
from math import sqrt
def mde(p1,n1,n2=191,z_a=1.96,z_b=0.8416):
    for i in range(1,600):
        p2=p1-i*0.001
        if p2<=0.0005: break
        pbar=(p1*n1+p2*n2)/(n1+n2); se=sqrt(pbar*(1-pbar)*(1/n1+1/n2))
        if se and abs(p1-p2)/se - z_b >= z_a: return round((p1-p2)*100,2)
for name,p in [("detail_opener6",0.267016),("opener_top10_share",0.073298),("backref_hit",0.120419)]:
    print(name, mde(p,191,191))
EOF
```

---

## 6. 跑批纪律（本轮执行清单，跑前逐项打勾）

1. `pgrep -af 'orchestration[[:space:]]+run|[r]un_[b]atch|[n]ightly\.py'` 无命中；
2. `bash tools/d5/preflight.sh --tag r49-diversity-off/on` 通过（内含冻结区干净检查）；
3. 两臂均 `flock -n /tmp/hitt.batch.lock` 全程持锁；`setsid`（或 `systemd-run`）后台启动，**不前台阻塞、不长 sleep 轮询**；
4. 跑批期间**不修改** `code/life|orchestration|config|engine`（本分支的代码改动**跑前已 commit**）；
5. 每臂结束：`cd code && python -m obs llm-cost --log <run.jsonl> --require-provider openai_compat` 原文落盘，`degraded=0`；
6. 截图：`tools/metrics/render_shots.py` 从**本轮** run.jsonl 渲染，禁拼图/禁跨批混拼/禁用旧图。

---

## 7. 附录：本预登记引用的零成本基线读数（命令原文 + 输出）

```bash
# ① 套路化尺子
python3 tools/metrics/lex_template_rate.py --log v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl
# → n_msgs=191 quant_hit=0/191 backref_hit=23/191 opener_top10_share=0.073298
#   （--out-json 版本另得 distinct_body_ratio 191/191=1.000、opener_top10_share Wilson95 [0.044161,0.119261]）

# ② 具体性起句尺子（本轮新立，先用既有日志验口径）
python3 tools/metrics/r49_detail_opener.py --log v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl --label c1a1
# → n_msgs=191 detail_opener6=51/191 detail_line=165/191 detail_body=187/191 paren_lead=169/191

# ③ 确定性自证
python3 tools/metrics/r49_detail_opener.py --log <同上> --out-json /tmp/a.json && \
python3 tools/metrics/r49_detail_opener.py --log <同上> --out-json /tmp/b.json && cmp /tmp/a.json /tmp/b.json && echo DETERMINISTIC
```
