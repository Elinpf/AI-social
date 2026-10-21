# F-4「误会与和解」修复闭环 · 预注册（R13，跑批前写死）

> 性质：**预注册**（先写死判据，再花钱跑批；跑完后不得回改本文件任何阈值）
> 日期：2026-10-21 ｜ 轮次：R13 ｜ 维度：F-4 修复闭环
> 代码锚点：分支 `feat/life-f4-repair-1021`，基线提交 `021baec3`；本轮实现提交 sha 见报告头（本文件写在 commit 之前）
> 基线臂：`v2/evidence/run_f6_off_n16r60_seed42`（`run.jsonl` sha8 `c73bead6`，`code_sha 895b9a3`，n16 r60 seed42，510 条 MSG / 169 mixed 线程 / 22 条旧口径张力 / 0 闭环 / L-13 2 条 / `llm_calls 2878` / `degraded_calls 0`）

---

## 0. 一句话

本轮只回答一个问题：**打开 F-4 臂后，「张力 → 同一线程内的和解」在真 LLM 下是否第一次可观测地发生，且每条都能被逐条复核。**
**不承诺、也不许写「生活气息改善」**——分母预计仍 <30，结论大概率是 `probe` / `不可判`。

---

## 1. 臂定义（单变量）

| 项 | 值 |
|---|---|
| 臂名 | **F-4 ON**（`run_f4_on_n16r60_seed42`） |
| 唯一干预 | env `HITT_DIALOGUE_REPAIR=1`（打开整条 F-4 机制：rift 台账 + 处境上下文 + 回复优先级 + 本轮新增的「这一句把话说开」要求） |
| **不加**第二个 env | 不开 `LIFE_PROMPT_MEMORY_F6` / `LIFE_PROMPT_MEMORY_F6_DEQUP` / `LIFE_PROMPT_GOSSIP_G1` |
| 规模 | `--seed 42 --agents 16 --rounds 60`（与基线逐项相同） |
| 基线 | **复用** `run_f6_off_n16r60_seed42`（`c73bead6`），不重跑 OFF |
| side-root | `/tmp/f4_on60_side`（新目录） |
| 起批方式 | `setsid nohup env HITT_DIALOGUE_REPAIR=1 bash tools/d2/run_batch.sh … > <run_dir>/host.log 2>&1 &` |

**可比性声明（先写死，跑完不许改口）**：基线臂跑在 `code_sha 895b9a3`，本轮臂跑在新 sha。
两者 OFF 路径的等价性**由 mock 字节锁证明**（`tools/f4/f4_off_bytelock.py`：改造前后同一 seed 的 9262 条记录逐字节相同，sha256 `5b9d65fc…`），
**不由真跑批证明**（省预算）。因此：本轮任何差异**只能归因到「F-4 臂打开」**，不得归因到其他代码变化；若需严格同 sha 对比，必须另跑 OFF 臂，本轮不做。

---

## 2. 判据（写死，跑完不改）

### 2.1 主指标：人际冲突子集闭环事件数（新口径）

定义（`tools/f4/f4_subset_metrics.py`，与旧口径**并列输出**，不改 `tools/d5`）：

- 线程分组：`dm` 按无序对 / `public` 按 day / `group` 按 group_id+day（= d5 `mixed_key`）；
- 张力事件：相邻两句极性相反 **或** 当前句极性为负，**且**两句中至少一句含**人际冲突词**：
  `生气 / 烦 / 委屈 / 失望 / 后悔 / 吵 / 凭什么 / 你什么意思 / 别这样`（本表写死后不再增删）；
- 闭环：其后 **8 条**同线程消息内出现 `tools/d5/repair_lexicon.txt` 任一词。

基线值：**闭环 0 条 / 张力 3 条**（`f4_subset_baselines.json`，off `c73bead6`）。

### 2.1b 严格闭环（排除已知附和词；与宽松口径**并列输出**，不替换）

anchor（`v2/evidence/f4_anchor.md` §4.3）已证明 `我懂` 在 `repair_lexicon.txt` 里但只是顺口附和，
on 臂那 2 条「闭环」全是它。因此闭环分子再给一列**严格口径**：

- **排除表（写死，跑完不增删）**：`("我懂",)` —— 这是 anchor 中**逐条看过上下文确认是附和**的唯一词；
- 严格闭环 = 宽松闭环规则不变，但命中词必须**不在**排除表内；
- 报告同时给「宽松 X 条 / 严格 Y 条」，二者差 = 被排除词贡献的伪闭环。

基线（off `c73bead6` / on `7de6a7be` / dequp `6bf3ec88`，`f4_subset_baselines.json`）：

| arm | 旧口径张力 | 旧口径闭环 宽松/严格 | 人际张力 | 人际闭环 宽松/严格 |
|---|---|---|---|---|
| off | 22 | 0 / 0 | 3 | 0 / 0 |
| on | 15 | **2 / 0** | 0 | 0 / 0 |
| dequp | 15 | 0 / 0 | 1 | 0 / 0 |

⇒ on 臂那 2 条在严格口径下**归零**，与 anchor §4.3 的误报结论完全一致。

### 2.1c 可审计闭环交叉核对（区分「词表噪声」与「机制失效」）

对每个张力事件，检查同一线程其后是否真的存在 `dialogue_repair` 配对（配对的 `trigger_seqs` 含该张力事件的 `seq`）：

| 词表判定 | 存在机制配对 | 判读 |
|---|---|---|
| 闭环 | 是 | 机制给过机会且出现了修复词 ⇒ 可信闭环 |
| 闭环 | 否 | **词表噪声**（没人被要求过和解，却「和解」了） |
| 未闭环 | 是 | 机制给过机会但模型没接 ⇒ 提示词/模型问题 |
| 未闭环 | 否 | 无机会也无修复词（基线常态） |

报告必须给这张 2×2 交叉表的计数，**比例只在分母 ≥30 时给**，否则只报条数。
基线：三臂「闭环且配对」均为 **0 / 0**（三臂 `dialogue_repair` 都还不存在）。
注意：mock（`--stub scripted_repair`）下该比例为 0/20 —— 因为 stub 与机制无关地交替输出，
这正是该交叉表要抓的「无关闭环」，**不是**链路失败的证据；链路是否通由 §2.2 的配对行数证明。

### 2.2 次指标：可审计配对行数（机制可达性，R13 新增信号）

- 计数 = 日志中出现 `payload.dialogue_repair` 的 MSG 事件条数（基线 **0**）；
- 每条必须满足：`v == "f4/repair/1"`、`rift_ids` 非空、`trigger_seqs` 全部 **< 本条 seq**、`prompted` 为 bool；
- 每条 `rift_id` 必须能在同一日志里对上一个 `trigger_seq`，且 `trigger_seq` 事件是 `MSG_*`；
- **本信号不做任何词表匹配**（回答「机制有没有给出和解机会、给了几次」）。

### 2.3 守卫指标（任一恶化 ⇒ 该臂结论只能写「不可判」）

| 守卫 | 阈值 | 基线（off `c73bead6`） |
|---|---|---|
| L-13 内部 token 泄漏条数 | **不得高于基线**（只报事件数，不报率；本轮**不修** L-13） | 2 |
| MSG 总量 | 459–561（510 ±10%） | 510 |
| mixed 线程数 | 152–186（169 ±10%） | 169 |
| `degraded_calls` | 必须 == 0 | 0 |
| `llm_calls` | ≤ 3310（2878 +15%） | 2878 |
| 提示词不得含现成句式 | 单测断言 `repair_ask()` 不含任何 `REPAIR_WORDS` | 已通过 |

### 2.4 降级规则（全族纪律，逐条适用）

1. **分母 < 30 ⇒ 只报事件数，不报比率**（本轮主指标分母预计 0–10 条，必然适用）；
2. **分母 < 68 ⇒ 标 `probe`**；
3. 任一守卫指标恶化 ⇒ 结论写「不可判」，不得写「有效 / 改善」；
4. 判定三件套（`|Δ|` / 噪声带 / 分母）必须同表出现；无可用噪声带时写「本规模下无法判定」。

---

## 3. 本轮**不**做什么（边界）

- **不修 L-13**（`code/life/agent.py:1256` 的 `topic` 原样插入保持现状）——一改，ON 臂与基线的差异就不止 F-4 一项，归因失效；
- 不改 `tools/d5/dialogue_metrics.py` 的任何口径（R1–R12 的可比性）；
- 不改 `config/`、`engine/`、`freeze/`；`code/orchestration/integration.py` 仅新增 3 行白名单转发（跑批前、无批在跑时做，OFF 路径零差异，见报告 §5）；
- 不写「生活气息改善」；不把「闭环从 0 变 N」当效果结论；
- 不碰 G-1 / `d4_*` 未跟踪产物。

---

## 4. 零跑拍自检（已在跑批前完成，产物入库）

| 检查 | 命令 | 结果 |
|---|---|---|
| OFF 字节锁（mock 世界，改造前 vs 后） | `tools/f4/f4_off_bytelock.py` + `git stash` 两跑 + `cmp` | **IDENTICAL**，9262 条记录，sha256 `5b9d65fc…` |
| OFF 路径 `dialogue_repair` 出现次数 | `grep -c '"dialogue_repair"'` | **0**（rc=1） |
| ON 路径机制可达（mock） | `--allow-on`（中性 stub） | `dialogue_repair` **45** 行，闭环 0（stub 不会道歉）→ 只证机会可计数 |
| ON 路径链路可收口（mock，契约级） | `--allow-on --stub scripted_repair` | 张力 32 / 闭环 **20**，配对行 35 ⇒ 链路能闭环；**这是组件证据，不是真 LLM 效果** |
| 单测 | `python3 -m pytest tests/test_dialogue_repair.py -q` | 21 passed（全仓 `pytest tests -q` = 585 passed） |

mock 日志指纹（`.gitignore:8` 忽略 `*.jsonl`，故只入库 sha256；可用 §4 命令原样重跑）：

| 文件 | sha256 |
|---|---|
| `/tmp/f4_off_before.jsonl`（= 改造前 OFF，9262 条） | `5b9d65fcb8a3b82c5da18a80f30ba1cb0b4f8272c659ef49cc54e5d25a944f0a` |
| `v2/evidence/f4_on_mock_offlinemock.jsonl`（ON 中性 stub，9286 条） | `2a95f118e2c5c1fe91b17353a9f00274010d5dafe1bfacf425a21eeaeff2fd10` |
| `v2/evidence/f4_on_mock_scriptedrepair.jsonl`（ON 契约 stub，9312 条） | `7914e5f31da8fd18dd2bfe1609350e8f29351335a716629963e9d71c535e0fb9` |

---

## 5. 跑批命令（预注册原文，执行时不得改动参数）

```bash
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
cd "$REPO"
pgrep -af "[o]rchestration run"; echo rc=$?     # 必须 rc=1
pgrep -af "[r]un_batch";        echo rc=$?     # 必须 rc=1
git status --porcelain -- code/life code/orchestration code/config code/engine code/freeze   # 必须为空

mkdir -p v2/evidence/run_f4_on_n16r60_seed42
setsid nohup env HITT_DIALOGUE_REPAIR=1 bash tools/d2/run_batch.sh \
  --out-dir v2/evidence/run_f4_on_n16r60_seed42 \
  --seed 42 --agents 16 --rounds 60 \
  --side-root /tmp/f4_on60_side \
  > v2/evidence/run_f4_on_n16r60_seed42/host.log 2>&1 &
```

真 LLM 验真（硬要求）：

```bash
cd code && python3 -m obs llm-cost \
  --log ../v2/evidence/run_f4_on_n16r60_seed42/run.jsonl \
  --require-provider openai_compat \
  --out ../v2/evidence/f4_on_llmcost.json; echo rc=$?
```

---

## 6. 读完数的三种可能结论（先写死，不许事后改判）

| 情形 | 结论写法 |
|---|---|
| 主指标分母 <30（预计） | 「闭环事件数 X / 张力 Y（probe，分母<30，不报率，不可判效果）」+ 次指标配对行 N 条逐条列出 |
| 守卫恶化 | 「不可判」+ 列恶化项 |
| 分母意外 ≥30 且守卫未恶化 | 仍标 `probe`（<68），只写方向，不写因果 |

**唯一允许写成「事实」的结论**：机制在真 LLM 下第一次产生了可审计的和解机会配对（`dialogue_repair` 行数从 0 变为 N），每条可用 `rift_id` + `trigger_seq` 回查。
