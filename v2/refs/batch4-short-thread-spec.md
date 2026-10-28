# batch4 最小跑批规格 · **短线程层（2–3 轮）足量供给**

> 交付对象：Leader（用于向用户报成本后再决定是否执行）。**本件不跑批、不改 `code/`**。
> 依据：`v2/evidence/run_a5_real_n16r42_seed42/run.jsonl`（A5 臂，`code_sha=51cdb07`，`feat/d2-prefer`）
> 现算，命令见 §0.2（**不引记忆值**）。
> 判据侧依据：`v2/evidence/d12c_batch2_blind_kappa_final.md`（κ 门槛 0.60、同批重判会抬高 κ）、
> `v2/refs/batch-hosting-runbook.md`（托管/环境/side-root 纪律）。

## 0. 一屏结论

| 项 | 结论 |
|---|---|
| 池子现状 | 该臂 140 线程里 2–3 轮层 **8 条**（2 轮 6 + 3 轮 2）；batch1 用 4、batch2 池内穷尽余 4 ⇒ **8/8 已全用尽** |
| 为什么少 | 四个机制叠加：**PUBLIC 线程不可回**（32/140 天生单发）、**一回合单动作**（每回合最多推进 1 轮）、**对端配额**（22 条 DM 单发是对端该 slot 回复额度满）、**封顶 6 轮**（69/108 DM 撞顶）；另有 **尾截断** 22 条 |
| 最小可行配置（推荐） | **`n=16 × rounds=42 × 5 个新 seed（43,44,45,46,47）`**，同树同参数同 env，只换 seed ⇒ 期望 2–3 层 **≈20 条**，`P(≥12)≈97%` |
| 备选（更快但可比性降级） | `n=32 × rounds=42 × 2 seeds` 或 `n=16 × rounds=84 × 2 seeds`（≈同产量、≈半墙钟），**须标注不可与 batch1/2/3 直接比** |
| 成本（5 批，只报计数不换算金额） | `llm_calls` **13,525**｜`cached` **7,030**｜**网络调用 6,495**｜墙钟 **≈200 min（≈3.3 h）串行**；折中 4 批版：`10,820 / 5,624 / 5,196 / ≈160 min` |
| 托管 | `systemd-run --unit=b4-a5-s<seed> --collect` + `--property=EnvironmentFile=`（**禁 `--setenv` 放密钥**）；`side-root` 每批唯一 |

## 0.1 层占比（本臂实测，脚本口径见 §0.2）

| 口径 | 2–3 轮条数 `k` | 分母 `n` | 占比 `p̂` |
|---|---|---|---|
| 全部线程 | **8** | 140 | **5.71%** |
| 仅 DM 线程 | **8** | 108 | **7.41%** |
| **DM 且非尾截断**（推荐作规划分母，最保守） | **4** | 93 | **4.30%** |

线程长度分布（`thread_id` 下的 MSG 条数 = `turn_index` 最大值 + 1，两口径实测一致）：

| scope | 1 | 2 | 3 | 4 | 5 | 6 | 合计 |
|---|---|---|---|---|---|---|---|
| DM | 23 | **6** | **2** | 4 | 4 | **69** | 108 |
| PUBLIC | **32** | 0 | 0 | 0 | 0 | 0 | 32 |
| GROUP | 0 | 0 | 0 | 0 | 0 | 0 | **0** |

## 0.2 复现命令（**只读**，产出 `v2/evidence/batch4_layer_census.json`）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 tools/b4/layer_census.py \
  --run v2/evidence/run_a5_real_n16r42_seed42/run.jsonl --max-turns 6 \
  --json-out v2/evidence/batch4_layer_census.json
```

该脚本口径写死：`scope` 由 `thread_id` 形态判（`-PUB-`⇒PUBLIC、`-G…-`⇒GROUP、否则 DM）；
**尾截断线程** = `min(round) > maxround − (max_turns−1)` = `> 36`（`maxround=41`）。

### 0.3 关于 **GROUP = 0**（**本臂事实，不是脚本漏算**）

- `batch4_layer_census.json` 的 `threads_by_scope` / `len_by_scope` **三个 scope 键恒存在**
  （`{"DM":108,"GROUP":0,"PUBLIC":32}`、`{"DM":{…},"GROUP":{},"PUBLIC":{"1":32}}`），并有 `scope_zero_note` 字段自述；
- **GROUP 通路是真实存在的**：`code/life/agent.py:177 _GROUP_TEMPLATES = {creative_collab, academic_collab, power_conflict, contest, combat_training}`，
  `_initiate` 在 `tid in _GROUP_TEMPLATES and len(parts) >= 3` 时才走 `scope="place_group"`（`agent.py:1211`）；
- 本臂**没有一条**线程同时满足"模板是 group 模板 且 计划参与者 ≥3" ⇒ 32 条 PUBLIC、108 条 DM、0 条 GROUP。
- **对 batch4 的影响**：2–3 轮层抽样只看 DM（PUBLIC 结构不可回、GROUP 本臂为 0）；若将来换了触发条件使 GROUP 出现，
  抽样口径须先确认 GROUP 线程是否可回（`is_replyable` 认 `MSG_GROUP`）再决定是否纳入，**不得默认沿用"只抽 DM"**。

## 1. 短线程到底怎么产生（读代码，只读不改）

### 1.1 该臂的参数真值（三个来源必须并列看待）

| 来源 | `max_turns` | `max_turns_per_round` | `max_messages_per_slot` | `reply_window_rounds` |
|---|---|---|---|---|
| `code/life/dialogue_threads.py::DEFAULTS`（树内） | 6 | 2 | 2 | **4** |
| `code/config/life_v2.json`（无 `dialogue` 段） | — 不覆盖 — | — | — | — |
| 该臂 `switch_proof.txt` 的 `params` 行（手写声明） | 6 | 2 | 2 | **2** |
| `agent.py::_pick_reply_target` 的代码兜底 | — | — | — | `cfg.get("reply_window_rounds", 2)` |

⚠ **`reply_window_rounds` 存在 2 vs 4 的口径冲突**（声明 2、树内 DEFAULTS 4）。
数据侧只能给"相容/不相容"判定：**全部 383 个 turn 间隔里，381 个 = 1 回合、2 个 = 2 回合、>2 的 0 个**
（§0.2 脚本 `turn_gap_rounds`）⇒ 与 `window=2` 相容，**无法反证 4**。
⇒ 见 §5 的硬要求：**batch4 必须把该参数由执行层证死（不是抄 `params` 行）**。

### 1.2 五个机制（按解释力排序，均可在代码/数据里定位）

| # | 机制 | 代码位置 | 本臂证据 |
|---|---|---|---|
| **A** | **PUBLIC 线程结构上不可回**：`is_replyable()` 只认 `MSG_DM`/`MSG_GROUP`，`MSG_PUBLIC` 恒 `False` | `life/dialogue_threads.py::is_replyable` | 32 条 PUBLIC 线程**全部** 1 轮（32/140 = 22.86% 的天生单发） |
| **B** | **一回合一个动作**：`_communicate()` 里"有可接的话就回复并 `return`，否则发起" ⇒ 每 agent 每回合最多推进 1 条线程 1 轮 | `life/agent.py::_communicate` | 每 `(agent, slot)` 动作数上限 = `ROUNDS_PER_SLOT`=3；实测 `init_max=2`、`reply_max=3` |
| **C** | **对端配额**：发起额度 ≤ `max_messages_per_slot`(=2)/slot；`HITT_REPLY_BUDGET=1` 时回复与发起**分账**，只在两类都用尽时才整体跳过 | `life/agent.py::_communicate`（cap 门控 + `_slot_inits/_slot_replies`） | **22 条 DM 单发**线程的发起都发生在"对端该 slot 回复额度已满"的 slot 里 |
| **D** | **封顶**：`max_turn + 1 >= max_turns` ⇒ 线程封口 | `life/agent.py::_pick_reply_target` | **69/108 = 63.89%** 的 DM 线程撞顶 6 轮 |
| **E** | **超时窗口**：`round − ev.round > window` ⇒ 该入站永不再被回（把"当回合没回"永久化为单发） | 同上 | 与 C 联合作用；`turn_gap` 无 >2 者，与 window=2 相容 |
| **F** | **运行结束截断**（非机制，但会污染抽层）：起跑 round > 36 的线程只剩 ≤5 回合可长 | — | **22 条**（DM 15）；8 条 2–3 轮里有 **4 条**是尾截断产物 |

单发线程归因（55 条 = 32 PUBLIC + 23 DM）：`A 非DM不可回 32` / `C 对端该slot回复额度已满 22` / `B 尾回合发起 1`。
2–3 轮层的 8 条**停因一致**：发起 → 对端回 1 轮 → **发起方没能再回**（当回合只有一个动作、且其回合并未选中该线程）。

### 1.3 旋钮分级：**哪些只影响数量、不影响对话形态**

| 旋钮 | 只影响数量？ | 依据/代价 |
|---|---|---|
| **seed**（换随机种子、参数一字不改） | ✅ **是**（推荐） | 不改任何门控；只换样本实例。**唯一能与 batch1/2/3 直接比的做法** |
| **`n`（agent 数）16→32** | ⚠ 部分 | 线程数≈线性增长，但**对端池变大 ⇒ DM 对象分布、PUBLIC 占比会变**；单线程内形态门控不变。须标注"线程层占比类读数不可直接比" |
| **`rounds` 42→84** | ⚠ 部分 | 线程数≈线性增长；但 84 轮=一周，跨 `weekend/day_type`、周计划重算 ⇒ **世界进程更长的历史**，形态可能变 |
| `max_turns` 6→更大 | ❌ **禁止** | 直接改"封顶"这一形态门控，2–3 层会被稀释（分母变大） |
| `max_messages_per_slot` / `HITT_REPLY_BUDGET` | ❌ **禁止** | 直接改产出速率与回复/发起配比 |
| `reply_window_rounds` | ❌ **禁止** | 直接改"线程能不能续" |
| 让 PUBLIC 可回（改 `is_replyable`） | ❌ **禁止**（这是改机制） | 会把 32 条单发变成可续 ⇒ 层占比全变；若真要做，属**新臂**，须新预登记 |

## 2. 最小可行规模（给公式与依据）

### 2.1 反推公式

```
p̂            = 2–3 层条数 / 分母线程数            ← 用 §0.1 的"DM 且非尾"口径，p̂ = 4/93 = 0.04301（最保守）
M_seed       = 单 seed 的"DM 且非尾"线程数        ← 本臂实测 93
E[K]         = N_seed × M_seed × p̂                ← 期望可用条数
N_seed_min   = ceil( (12 + 安全余量) / (M_seed × p̂) )
P(≥12)       ≈ 1 − Φ( (11.5 − E[K]) / sqrt(E[K](1−p̂)) )    ← 二项近似
```

### 2.2 方案表（`n=16, rounds=42`，每 seed 一份独立批）

| 方案 | seeds | 期望 `E[K]` | `P(≥12)` | calls | 网络调用 | 墙钟（串行） |
|---|---|---|---|---|---|---|
| 最小（不推荐） | 3（43,44,45） | 12.0 | ≈56% | 8,115 | 3,897 | ≈120 min |
| 稳妥（**推荐**） | **5（43–47）** | **20.0** | **≈97%** | **13,525** | **6,495** | **≈200 min** |
| 备选 A（n=32 × 2 seed） | 2 | ≈16（DM 非尾 ≈2×93/seed） | ≈87% | ≈10,820（外推） | ≈5,196（外推） | ≈200 min |
| 备选 B（r=84 × 2 seed） | 2 | ≈16 | ≈87% | ≈10,820（外推） | ≈5,196（外推） | ≈200 min |
| 折中（4 × r42） | 4（43–46） | 16.0 | ≈88% | 10,820 | 5,196 | ≈160 min |

> 备选 A/B 的单批 calls/cached 是**按"随 agent·round 线性缩放"外推**（2,705×2=5,410、1,406×2=2,812 ⇒ 网络 2,598/批），属**估算**；
> 真值须由 mock 或首批实测校准。推荐方案（5 个 r42 seed）的 calls/网络/墙钟**全部来自本臂实测值线性乘 5**，不确定性最小。

### 2.3 排除名单（必须带进抽样）

- batch1：12 个 thread_id（含 4 条 2–3 轮）；batch2：12 个 thread_id（含 4 条 2–3 轮，**池内穷尽**）
  ⇒ 该臂 2–3 层 **8/8 已用尽**。
- 新 seed 的 `thread_id` **结构上不可能与旧 seed 重名**（DM=`TH-<A>-<B>-<round>`、PUBLIC 带 `-PUB-<round>-<k>`，round 与参与者组合会变），
  但抽样清单仍须显式写 `exclude=batch1∪batch2` 的 id 列表（防未来复跑同 seed 时误用）。
- **重跑 seed 42 不计入新样本**：它的 8 条已判过 ⇒ 若复用必须整批排除该 seed 的这 8 条。

## 3. 不得影响可比性（显式标注）

| 方案 | 能否与 batch1/2/3 直接比 | 说明 |
|---|---|---|
| **5 × r42 新 seed（推荐）** | ✅ **能** | 同树 `51cdb07`、同参数、同 env 开关、只换 seed ⇒ 同一臂的新样本；判据/κ 门槛一字不改 |
| n=32 × 2 seed | ❌ **不能**（线程层占比类） | 对端池变大 ⇒ `n_threads`、`p50`、`≥3轮占比`、`转化率` 不可与 batch1/2/3 比；**仍可比**：单线程内读数（轮内重复率、长度分布、judge 分、句尾收束等） |
| r=84 × 2 seed | ❌ **不能**（线程层占比类 + 世界历史） | 同上，且跨周末/日型 ⇒ 世界上下文不同；**仍可比**：单线程内读数 |

⇒ 凡选备选 A/B，报告首屏必须写死一句：**「该批线程层占比类读数不可与 batch1/2/3 直接比」**，并列出仍可比的清单。

## 4. 成本与时长（**只报计数，不换算金额**）

单批实测（`run_a5_real_n16r42_seed42`，n=16 r=42）：

| 项 | 值 |
|---|---|
| `llm_calls` 总数 | **2,705**（judge 497 / dialogue 523 / importance 1,523 / reflect 112 / negotiation 34 / plan 16） |
| `cached` | **1,406**（importance 1,387 / negotiation 19） |
| **网络调用 = calls − cached** | **1,299** |
| MSG | 523（DM 491 / PUBLIC 32 / GROUP 0） |
| 墙钟 | **≈40 min**（A1 臂实测 18:04→18:44，同规模同参数；A5 同规模） |

推荐方案 5 批：`calls 13,525`｜`cached 7,030`｜**网络 6,495**｜墙钟 **≈200 min 串行**（**必须串行**：并发会互抢配额/缓存与墙钟失真）。

**托管方式（照 runbook §"生效命令模板"）**：

```bash
WT=<repo>/.worktrees/a2-prefer            # 代码必须来自该臂 worktree，不碰主树
B4ENV=/tmp/b4_env_$SEED.conf              # 只放**非密钥**开关
printf 'HITT_REPLY_BUDGET=1\nHITT_INIT_PREFER_UNREPLIED=1\n' > $B4ENV
systemd-run --unit=b4-a5-s$SEED --collect \
  --property=MemoryMax=2G \
  --property=EnvironmentFile=<主树>/code/.env.local \
  --property=EnvironmentFile=$B4ENV \
  --working-directory=$WT \
  /bin/bash tools/d2/run_batch.sh \
    --out-dir v2/evidence/run_b4_a5_n16r42_seed$SEED \
    --seed $SEED --agents 16 --rounds 42 \
    --side-root /tmp/b4_a5_s${SEED}_v1        # ← 每批唯一，起跑前若已存在则拒绝起跑
```

- **密钥只走 `EnvironmentFile`**（`--setenv` 会把值写进可查询属性 ⇒ 泄密）；
- `side-root` 每批唯一（复用 ⇒ 100% 缓存回放 = 假跑；判据：`网络 = calls − cached > 0` 且 `dialogue.cached` 显著小于 `dialogue.calls`）；
- 收批等价清单（master 血统 `run_batch.sh` **无 EXIT trap**，**不得写 rc=0**）：
  `meta.finished_at` + `TURN_SEAL` 覆盖 0..41 + `wc -l == meta.events` + journal `[d2] OK` + `Deactivated successfully` + `provider_guard.ok`。

## 5. 预登记挂钩（**起跑前必须写死，缺一不起跑**）

1. **抽样口径**
   - 层定义：`线程 MSG 条数 ∈ {2,3}`；**只用 DM 线程**（PUBLIC 结构不可回，排除）；
   - **非尾过滤**：`min(round) ≤ maxround − (max_turns−1)`（本臂 = ≤36）——尾截断线程单列，**不入抽样池**；
   - 每批配额：每 seed 抽 2–3 条（若 2 轮与 3 轮要分层，按实测 6:2 比例分层随机）；
   - `exclude=` 清单：batch1∪batch2∪（若复用 seed42）该 seed 的 8 条；
   - 抽样脚本与随机种子写死，**抽样结果落盘后可复算**。
2. **双盲两方**：读者 A/B 只拿到打乱后的盲码（`T01..Tnn`）+ 对话全文，**不含 seed / round / thread_id / 臂标签**；两方独立评分后再解盲。
3. **κ 门槛**：沿用 **`κ(三档) ≥ 0.60`**（`d12c_batch2_blind_kappa_final.md` 的预登记规则）；`<0.60 ⇒ 三档不转正`。
   二值口径若边际退化（一方全判 A/B 无 C）⇒ **判「不可判」**，不得用退化 κ 宣布二值可用。
4. **禁止同批重判**：必须**新样本 + 真盲评**；同批重判会把 κ 抬高（实测 0.733 vs 0.182），**不得**用它替代盲评。
5. **参数由执行层证死**（本件新增的一条，因 §1.1 的 2 vs 4 冲突）：
   起跑后在 `/proc/<MainPID>/environ` 取 `HITT_REPLY_BUDGET` / `HITT_INIT_PREFER_UNREPLIED` 真值；
   在批树内 `python3 -c "from life.dialogue_threads import DEFAULTS; print(DEFAULTS)"` 落盘 `effective_params.json`；
   **`reply_window_rounds` 必须与声明一致**，不一致就停下报告，不得"按声明算"。
6. **判定词锁定**：本批只回答"短线程层的判据一致性（κ）"，**不得**顺带宣布 A5 臂有效性/自然度；任何"更自然"类表述禁止。

## 6. 本件声明

- **未启动任何 `python3 -m orchestration` 进程**（本件写作时执行 `ps -eo pid,lstart,cmd | grep -E "[o]rchestration run"` ⇒ **无匹配**）。
- **未修改 `code/`**（只新增 `tools/b4/layer_census.py` 只读脚本与 `v2/evidence/batch4_layer_census.json`）。
- 所有层占比数字均由 §0.2 命令现算，未引记忆值。
