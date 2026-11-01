# R47 · 同轮往返可见（D9z `HITT_INTRA_ROUND_VISIBILITY`）—— 维度定稿报告

- 作者：`life-engineer`｜2026-11-01｜**本轮零新增跑批、零新增 LLM 调用**（只读既有日志复算 + 现渲截图）
- 维度：**同轮往返可见（intra-round visibility）**—— 同一回合内，居民能不能「当场接上对方那句话」
- 状态词（看板口径）：**机制层 `已成立`；效果层（时序判据）`已成立`；「生活气息提升」`未测`，且已有反向线索**
- 判定件的唯一权威出处仍为 `v2/evidence/d9z-judgement-20261101.md`（本报告不构成新判定，只做**定稿、复算与登记**）
- 预登记：`v2/refs/D9z-prereg-intra-round-visibility.md`（`FROZEN v3.3`，`f01488138a946e92…`）

> **本报告的三条禁写（先写在最前面，防止被摘句误用）**
> 1. 禁止写「迟回减少 55%」——**迟回条数一条没少（48 → 48）**，降的只是**占比**，且**全部来自分母变大**。
> 2. 禁止写「同轮往返提升了生活气息」——**未测**，且 `gap=0` 里 **55.6% 是跨地点**（异地即时通信，不是当面说话）。
> 3. 禁止用 `meta.code_sha` 归属本批——**该批没有 `meta.json`**（见 §1）。

---

## 0. 结论（先给结论，再给数）

**`A`（真实性）过、`B`（充分性）过、三条护栏全过 ⇒ 时序判据通过。**
但「通过」只说明**到达时序变了**：`gap=0` 相邻对 **0 → 133**；`gap≥2` 的**绝对条数两臂相同 48 = 48**，占比下降 **55.0%** 全部来自分母 `125 → 278`。

| 判据 | 预登记阈值 | 实测 | 结论 |
|---|---|---|---|
| `A` 真实性：`gap=0` 绝对条数 | `≥ 12` | **133**（133/278） | 过 |
| `B` 充分性：`gap≥2` 占比 | `≤ 0.2688` | **0.1727**（48/278） | 过（OFF 基线 `0.3840`） |
| 护栏① `n ≥ 260` | — | **278** | 过 |
| 护栏② `places.json` 内容 sha 一致 | — | 两 rev 同为 `c36c0f87…`（§1.2） | 过 |
| 护栏③ `degraded = 0` | — | `LLM_CALL` **2729** 条，`degraded` **0** | 过 |

---

## 1. 臂身份与归属（**该批无 `meta.json`，禁止引用 `meta.code_sha`**）

### 1.1 三元组归属

| 项 | ON 臂 | OFF 基线臂 |
|---|---|---|
| 批次目录 | `v2/evidence/d9z-on_n16r56_s42/` | `v2/evidence/d9t-on_n16r24_s42/` |
| 代码 rev（`launch_cmd.txt` 的 `HEAD=`） | `feat/d9z-intra-round@43a56c19d2b1f3c176d9ba424338984875b1de4a` | `cef1c58c448d400c0fe98736634cc0891b0a78e6` |
| `run.jsonl` 内容 sha256 | `1f0fec69fb2189c4877840fc784fb12cacaa0857aa6d190a30520c9d97204f4d` | `af4c44d11dd22eb84ae9e6fd1f5d32417d128d34ff07ec54d2bb08bd61256dec` |
| FP 三元组 | `files=283`、`sha256=3625502c…`、**`fp_equal=YES`** | `files=282`、`fp_equal=YES`（`launch_cmd.txt` 记 `before`/`after` 同值） |
| 参数 | `16 agents × 56 rounds, seed=42` | `16 agents × 24 rounds, seed=42` |
| 墙钟 / 退出码 | `2725.7089 s`（外部窗 2766 s）、`rc=0` | `1310.6251 s`、`rc=0` |
| `meta.json` | **不存在**（`ls` ⇒ `No such file or directory`） | **不存在** |

> `launch_cmd.txt` 末三行还给出现场复算的 `sha256` / `wc -l`(=90532) / 字节数(=44305670)，与本轮独立复算逐位一致。

### 1.2 护栏②的正确取证方式（沿用判定件 §1.1 的勘误）

两臂**不是**靠「同值字段」比的：OFF 臂 `launch_cmd.txt` **没有** `places_sha256` 字段。正确做法是比 git 对象内容：

```
$ git show cef1c58:code/config/places.json | sha256sum
c36c0f8776372f4e36ec39126f0fd9546c1dadf5e814c294172f5e2e04bb66fa  -
$ git show 43a56c1:code/config/places.json | sha256sum
c36c0f8776372f4e36ec39126f0fd9546c1dadf5e814c294172f5e2e04bb66fa  -
```

### 1.3 **跨分支声明（硬约束）**

- 数据来自 `feat/d9z-intra-round@43a56c1`。`git merge-base --is-ancestor 43a56c1 HEAD` ⇒ **`NOT-ancestor`**；
- 当前工作分支 `code/` 全树 `grep -rn "INTRA_ROUND_VISIBILITY" code/ --include=*.py` ⇒ **零命中**；该实现只在 `43a56c1:code/engine/perceive.py`。
- ⇒ **本报告的实现身份 = `43a56c1`，不是当前 HEAD**。**禁止**把该实现搬到当前分支后当作「本分支已具备」；任何移植须新预登记 + 重跑。

---

## 2. 机制层：三档自校验

```
gap 分布（相邻对 = 带 reply_to 且父条在本样本内的 MSG_*）
ON : {0: 133, 1: 97, 2: 48}   合计 278 = 相邻对总数   → 自校验 PASS
OFF: {1: 77,  2: 48}          合计 125
```

- `gap = round(子) - round(父)`，量的是**轮次距离**（线程内 `gap=2` 仍是紧邻两轮）；
- `gap=0` 在机制 OFF 时**结构上不可能出现**（OFF 实测 `0`），ON 后 `133` ⇒ **机制确实接通**。

---

## 3. 效果层读数三条（**必须与结论同屏**）

### 3.1 `gap≥2` 绝对条数两臂相同

| 臂 | `gap≥2` | 分母 | 占比 |
|---|---:|---:|---:|
| OFF | **48** | 125 | 0.3840 |
| ON | **48** | 278 | 0.1727 |

⇒ `B` 的「降 55.0%」**全部来自分母**；**迟回条数一条没少**。许可写法：「迟回**占比**降 55.0%；迟回**条数**不变（48 → 48）」。

### 3.2 新增 153 对的去向

```
gap=0：  0 → 133  （+133，占新增 86.9%）
gap=1： 77 →  97  （+20）
gap≥2： 48 →  48  （ +0）
```

### 3.3 规模归因（不得把占比下降独归机制）

`rounds` 24→56、`MSG` 191→444（DM 167→375、PUBLIC 24→69）⇒ 分母翻倍是「**跑得更久**」的直接后果。`n≥260` 是预登记指定规模（不违规），但**归因必须带这一项**。

### 3.4 反向信号：`gap=0` 里 55.6% 是跨地点

| 子集 | 条数 | 同 `place` | 跨 `place` | 跨地点占比 |
|---|---:|---:|---:|---:|
| `gap=0` | 133 | 59 | **74** | **55.6%** |
| `gap≥2` | 48 | 2 | **46** | 95.8% |

- `gap≥2` 的 48 条**全部恰好等于 2**（无 3 以上）⇒ 迟回「卡一轮」是结构性的；
- `gap=0` 里 74 条跨地点 ⇒ 新机制最大产出是「**异地即时通信**」，**对生活气息是反向信号**。

---

## 4. 结构原因：配额（`max_messages_per_slot = 2`）

口径：`prior` = **回复方（子消息作者）**在同一 `(day, slot)`（取**父消息**的时段）内、`seq` **严格小于**父消息 `seq` 的已发 `MSG_*` 条数；`≥ 2` 记「配额满」。

| `gap` | n | `prior` 分布 | 配额满 |
|---|---:|---|---:|
| 0 | 133 | `{0:71, 1:62}` | **0/133 = 0%** |
| 1 | 97 | `{0:15, 1:74, 2:8}` | 8/97 = 8.2% |
| 2 | 48 | `{1:1, 2:47}` | **47/48 = 97.9%** |

地点对照：`gap=0` 同地点 **0/59**、跨地点 **0/74**；`gap=2` 同地点 **2/2**、跨地点 **45/46** ⇒ **完全分离**：配额满 ⟺ 无法当轮回，地点在「能否同轮回」上无可观测影响。

### 4.1 本轮新增旁证（**原判据未使用，不作判定**）

同一口径跑 OFF 基线臂：`gap=2` 的配额满 = **26/48 = 54.2%**，`gap=1` = **4/77 = 5.2%**。
⇒ OFF 臂的迟回**并不全由配额满解释**（26/48），ON 臂升到 47/48 与「新增 133 条消息占用配额」的方向一致。
**这是本轮新增的观察，未进任何判定**，且**不构成因果结论**（未做干预实验）。

---

## 5. 本轮复算：一条命令重出全部核心数字

新增复算器：`tools/metrics/d9z_gap_recompute.py`（零依赖、零 LLM、只读 `run.jsonl`；同输入两次运行**逐字节相等**，本轮实测 `diff -q` 通过）。
脚本 sha256：`3877861930140b24dc740f77887efca66b98289ed5de4dce470c14a36be35cfc`

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 tools/metrics/d9z_gap_recompute.py --log v2/evidence/d9z-on_n16r56_s42/run.jsonl  --label ON  > v2/evidence/d9z-recompute-20261101/on_readings.txt
python3 tools/metrics/d9z_gap_recompute.py --log v2/evidence/d9t-on_n16r24_s42/run.jsonl --label OFF > v2/evidence/d9z-recompute-20261101/off_readings.txt
```

输出落盘（可逐字节复核）：

| 文件 | sha256 |
|---|---|
| `v2/evidence/d9z-recompute-20261101/on_readings.txt` | `0738589fda2acb2327369cc771ad06eead4f888f5ecd65779950244eea773c43` |
| `v2/evidence/d9z-recompute-20261101/off_readings.txt` | `aa76ad62ddefdbb5bcf61938fa1be138b8fd7ab4563e01747ee3b632f54b66ca` |
| `v2/evidence/d9z-recompute-20261101/llm_cost_on.txt` | `5accf0d1d29780a695459125054169e0d2341bdd78f3eeb775e77da035499d29` |
| `v2/evidence/d9z-recompute-20261101/llm_cost_off.txt` | `31052a091d5006af4ff338f6eed170301e8b65c6e5c3e4408194039a32936ade` |
| `v2/evidence/d9z-recompute-20261101/pgrep_before.txt` | `e0bf1bea926cacc07d14fe57913583b74e3fc4dad8aa6bba937411c6d6a50c5f` |

### 5.1 与既有件的逐条对照（本轮独立复算 vs 原判定件/事实链）

| 指标 | 本报告复算 | 判定件/事实链 | 一致性 |
|---|---|---|---|
| 相邻对总数 | 278 | 278 | ✅ |
| `gap` 分布 | `{0:133,1:97,2:48}` | 同 | ✅ |
| `gap≥2` 占比 | 0.1727 | 0.1727 | ✅ |
| `gap=0` 同/跨地点 | 59 / 74（55.64%） | 59 / 74（55.6%） | ✅ |
| 配额满（`gap=0`/`gap=2`） | 0/133、47/48 | 0/133、47/48（97.9%） | ✅ |
| DM 机会分母 | 满 55/84（65.48%）、未满 223/291（76.63%） | 55/84、223/291（65.5%/76.6%） | ✅ |
| `MSG` 去重后 | 444（DM 375 / PUBLIC 69） | 444（DM 375 + PUBLIC 69） | ✅ |
| `LLM_CALL` / `degraded` | 2729 / 0 | 2729 / 0 | ✅ |
| `run.jsonl` sha256 | `1f0fec69…204f4d` | `1f0fec69…` | ✅ |
| 行数 / 字节 | 90532 / 44305670 | 90532 / 44305670 | ✅ |

### 5.2 真跑验真（`obs llm-cost`，只读既有日志，本轮 0 新增调用）

```
$ cd code && python3 -m obs llm-cost --log ../v2/evidence/d9z-on_n16r56_s42/run.jsonl --require-provider openai_compat
{"engine_log":{"by_provider":{"openai_compat":2729}, ... "total":{"cached":1408,"calls":2729,"degraded":0,"thinking":606,
 "tokens_in":411457,"tokens_out":255398,"tokens_total":666855}},
 "provider_guard":{"by_provider":{"openai_compat":2729},"expected":"openai_compat","ok":true,"problems":[]}}
```

OFF 臂同命令：`by_provider={openai_compat:2252}`、`calls 2252`、`degraded 0`、`tokens_total 363719`、`provider_guard.ok=true`。
⇒ 两臂均**真跑、无 mock 混入、无降级**。

---

## 6. 真实截图（三件套齐全，本轮现渲；**不参与任何判据**）

渲染命令（零跑批、零 LLM，只读既有 `run.jsonl`）：

```bash
python3 tools/metrics/render_shots.py --run-dir v2/evidence/d9z-on_n16r56_s42  --batch-id D9z-ON  --outdir v2/evidence/d9z_shots --views chat,rhythm
python3 tools/metrics/render_shots.py --run-dir v2/evidence/d9t-on_n16r24_s42 --batch-id D9z-OFF --outdir v2/evidence/d9z_shots --views chat,rhythm
```

| PNG | 尺寸 | 字节 | sha256 |
|---|---|---|---|
| `v2/evidence/d9z_shots/D9z-ON-chat-1f0fec69.png` | 1400×900 | 296824 | `184043854c5a2c9e75e137302671d936471f1958066df91e575addac147fc0de` |
| `v2/evidence/d9z_shots/D9z-ON-rhythm-1f0fec69.png` | 1300×1050 | 280111 | `4a798f629dec3f533fa7eb91b2f7b2b2b64dc6117251ef1d37995006c6bd3457` |
| `v2/evidence/d9z_shots/D9z-OFF-chat-af4c44d1.png` | 1400×900 | 303424 | `22e26894dc9b5a0cf9315bbeead7f93fb6d21e04827322e3acfeff45cdb622dc` |
| `v2/evidence/d9z_shots/D9z-OFF-rhythm-af4c44d1.png` | 1300×1050 | 279199 | `56d60a92d3520cd12273d6cbcbaf7d234eb8ab2d884572bf2532655c9882987a` |

- 文件名里的 `1f0fec69` / `af4c44d1` 就是两份 `run.jsonl` 的 sha 前 8 位；逐张三件套（来源 run 目录 + 渲染命令 + 日志 sha256）已写入 `render_report_D9z-{ON,OFF}.json`（`ok_count=2 / fail_count=0`）。
- 用途限定：**只证「批次真实存在 + 渲染链通 + 结构完整」**，不支撑任何措辞质量结论。

---

## 7. 纪律记录（本轮零跑批）

### 7.1 起跑前无残留（虽是零跑批，仍按纪律留档）

```
--- pat=orchestration ---   rc=1
--- pat=run_module ---      rc=1
--- pat=D9T_OUT ---         rc=1
--- pat=[r]un_[b]atch ---   rc=1
--- pat=[n]ightly\.py ---   rc=1
--- ps 全量筛 ---            ps_rc=1（无输出）
```

原文：`v2/evidence/d9z-recompute-20261101/pgrep_before.txt`（sha256 `e0bf1bea…`）。
说明：**必须**用五模式 + `ps`，因为仓库既有三模式门对 runpy 形态启动器**失明**（`v2/evidence/d9z-on_n16r56_s42/gate_check.txt` 留证）。

### 7.2 冻结区零改动

`git status --porcelain -- code/life code/orchestration code/config code/engine` ⇒ **0 行**。
本轮全部改动落在**非冻结区**：`reports/`、`docs/`、`tools/metrics/`、`v2/evidence/`。

### 7.3 本轮新增 LLM 成本 = 0

两臂的 666855 / 363719 tokens 均为**既有批次**成本；本轮的 `obs llm-cost` 只读日志（单次 < 1 s）。

---

## 8. 边界与未测（不得由本报告推出）

1. 只对 `feat/d9z-intra-round@43a56c1` + 本批数据（`1f0fec69…`）成立；**不外推**到其它规模/seed；
2. **不涉及「生活气息整体提升」**：本实验量的是**时序结构**；`gap=0` 中 55.6% 跨地点是反向线索；
3. **两臂不可直接比规模**：24 vs 56 rounds，`gap≥2` 绝对条数 `48 = 48`；
4. 世界线基 `cef1c58 ≠ master`（差 +37,800/−635）⇒ **不得与 `master` 世界线读数直接比较**；
5. OFF 等价性口径 = **mock-对-mock**（对预登记的一次口径修正，不藏）；
6. 未测：「对方看见但选择不回」（需读 `_pick_reply_target` 候选集）。

---

## 9. 已推翻的 6 条假设（**引用本报告必须同时引用本节**）

| # | 曾被当真 | 实测/代码 | 后果 |
|---|---|---|---|
| 1 | 「62.8% 的回复延迟可压到 0（214/341）」 | `gap≥2` 48 → 48，一条没压掉 | 该数不得再作目标值 |
| 2 | 「地点降权」 | `_pick_reply_target` 无 `place`；跨/同地点 `prior` 分布几乎相同 | 地点嫌疑在选择层不成立 |
| 3 | 「`ROTATION` 黑名单随可见性变」 | `OPENINGS=1` 时 `narration_tail` 短路，`narration_example()` 从不调用 | 该通道是死的；「配置 `=1`」≠「通道生效」 |
| 4 | 「`H` 只归因可见性」 | `H` 还受 L-7 结构臂禁忌开头清单影响（默认 ON） | `H` 是**合成量**，不得单挂机制 |
| 5 | 「`reply_window_rounds=4` 是有效参数」 | `VISIBLE_WINDOW_ROUNDS=2` 先把 `gap≥3` 删掉 | 拿它做消融会得假阴性 |
| 6 | 「`prefer_threads` 可能是解释」 | `dialogue_repair.DEFAULTS["enabled"]=False` ⇒ 本批从未执行 | 不是候选解释 |

---

## 10. 登记

- 看板：`docs/team-board.md` §一 新增第 17 行（本维度）；§二 A 档新增一行标注 **A-1 已由 R46/`63d3226` 收口**（不改历史行）；§三 新增本轮记录行。
- 索引：`reports/README.md` 新增 `R47` 行（`R44`/`R45`/`R46` 的历史欠账**不代补**，按本表惯例留欠账注记）。
- 提交：本轮 commit **`a7f008f`**（分支 `feat/r46-c1-effect-metrics`，只含 R47 相关六项 + 看板/索引登记；看板 `sha` 回填为后续补充 commit）。**不推 `master`**——`origin/master...HEAD = 103/72` 分叉待评估（`P-1b` 未销号），master 合并须单独决策；push 状态见 `rounds/2026-11-01-r1/` 的提交信息节（实测网络 `ls-remote` 超时，推送结果如实标注）。
