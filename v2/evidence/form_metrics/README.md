# `v2/evidence/form_metrics/` —— 形态指标落盘证据（`Q-18` 整改）

> 出数器：`tools/metrics/form_metrics.py`（主树新增，**零 LLM、零跑批、只读**）
> 证据生成：2026-10-24（metrics-engineer）｜不 commit、不 push、不碰 `code/`、`life/`、`orchestration/`、`config/`、`engine/`

## 0. 这份证据要解决的问题

CYCLE-12 判 `Q-18`：`L-3` / `addr_head` / `len_p50` 三值**只有 prose，没有落盘出数器**；
`reports/CYCLE-12-20261024.md:502-504` 明文要求「下周期报告必须做的一件事」就是把它们升为落盘出数器输出。
`§3.6` 另判 `addr_head` 存在 `90.98%`（prose）vs `87.65%`（落盘）双值冲突 ⇒ `不可判`。

本目录给出：**一条命令可复算**的 `L-3` / `addr_head`（三口径）/ `len_p50`（两口径）/ `L-7`（带本批索引 sha256），
并对 `§3.6` 的冲突给出**逐条可查的差集解释**（不是「取整误差」）。

## 1. 产物清单（sha256 写死）

| 文件 | 行数 | sha256 |
|---|---|---|
| `d12h_form_metrics.json` | 350 | `cc921f0788bbbfe4b8bbf382f98770f79b6ac00f966e4472e82ccba0e97c2b1d` |
| `t5_form_metrics.json` | 350 | `7e07bc35d4e7d16141022acbd3c77bed03f509dbdc62111575a8f6f6019f3fe4` |
| `d12h_addr_head_triage.json` | 7571 | `9449258cfe1714b87672fb3e1dbe0879aae23891d1bc4510f4f32bbfc3c5ef8e` |
| `t5_addr_head_triage.json` | 7391 | `1d75cb657fd264c51eb24bdad8ff9c633c395388a76365bf63ed5d3e472a527a` |
| `tools/metrics/form_metrics.py`（出数器本体） | 589 | `78913b6ff30ad3544a20a45d04f86c8cee474908b1e48b80451e72cbbcdd57d9` |

> **v2 修订（2026-10-24，按 Leader 裁决 FM-1/4/5）**：新增两个 `role=reference_only` 参照量
> `addr_head_pfx2_plus`、`addr_head_alias`，并把 `loose` 的「≤6 字」下界冻结为模块常量 `LOOSE_MIN_CHARS = 2`。
> 上表是本版（含两个参照量）的 sha256；旧版 sha256 已作废，不得再引用。

## 2. 输入日志（sha256 + 行数）

| 批 | 日志路径（相对仓库根） | 行数 | sha256 |
|---|---|---|---|
| **D12-H** | `.worktrees/d12h-pairing/v2/evidence/run_d12h_pairing_n16r60_seed42/run.jsonl` | 119519 | `122b36e988267a396cfdd95b167bad92bf69beabc249c253b46555f2679c3207` |
| **T5** | `.worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42/run.jsonl` | 117393 | `dd4ad73d5a21c7485c2afbfc9701e267c25da3150b10adade3b3819a3996ff36` |

- 两批都是**已收批**（`run_batch.end` 存在）；**未使用正在跑的 D12-I 日志**。
- 两批 `MSG_*` 消息数均为 **510**，`body` 非空条数亦为 **510**（故本证据中「分母 510」在两种分母定义下同值）。

其它输入：

| 输入 | 路径 | sha256 |
|---|---|---|
| `L-3`/`L-7`/`len_p50` 唯一口径实现 | `tools/d5/dialogue_metrics.py` | `1d914735f3a13cf4e1640bd694f1d0e070096c9f50abfdefa7359417df551271` |
| persona 显示名 | `code/config/personas.json` | `08d11eb36d644e55db0c9b7e00adccb81613d50476927e3acf07117f7f970f7d`（20 个 display_name） |
| `addr_head_pfx2` 逐字引入源 | `.worktrees/d12h-pairing/tools/d12h/shape_gate.py` | `f7740b6d4c3052b7577b5bf9d5c10c18039d2a87a1e2afb0697fb49691d70ea3`（分支 `feat/c12-d12h`，commit `371edb99d2594406553742c66c7ce0a4f7487069`） |
| 三口径定义来源 | `v2/evidence/d12h_verdict_amendment3.md` | §C 行 47/48/49 |

> `shape_gate.py` 只存在于 worktree（master 的 `git ls-files tools/d12h` 为空，`Q-19`）。
> 因此出数器把 `is_addr_head()` 与 `SUFFIX_CHARS` **逐字内嵌**到 `tools/metrics/form_metrics.py`，
> 并在运行时用 `vendor_check` 与 worktree 源函数做逐字比对（两批均为 `identical`）。

## 3. 复算命令（照抄即可，逐位一致）

在**仓库根**下执行（`--out` 必须与表中路径一致，因为复算命令自身被写进了 JSON 的 `recompute_cmd` 字段）：

```bash
# D12-H
python3 tools/metrics/form_metrics.py \
  --log .worktrees/d12h-pairing/v2/evidence/run_d12h_pairing_n16r60_seed42/run.jsonl \
  --code-dir code \
  --out v2/evidence/form_metrics/d12h_form_metrics.json \
  --batch-id D12-H --no-timestamp \
  --triage-out v2/evidence/form_metrics/d12h_addr_head_triage.json

# T5
python3 tools/metrics/form_metrics.py \
  --log .worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42/run.jsonl \
  --code-dir code \
  --out v2/evidence/form_metrics/t5_form_metrics.json \
  --batch-id T5 --no-timestamp \
  --triage-out v2/evidence/form_metrics/t5_addr_head_triage.json
```

校验（应输出上表 4 个 sha256）：

```bash
sha256sum v2/evidence/form_metrics/*.json
```

**逐位一致性**：落盘件用 `--no-timestamp` 生成 ⇒ 无时间戳字段，**同一 `--out` 路径重跑即逐字节相等**（已实测两次重跑 sha256 不变）。
若去掉 `--no-timestamp`，则只多一个 `generated_at`，用
`jq 'del(.generated_at)' out.json` 后可逐位比对。

## 4. 结果（每指标六元组：数值 / 分母 / 判据编号 / 来源路径 / sha256 / 复算命令）

### 4.1 D12-H（`n_msgs = n_bodies = 510`）

| 指标 | 数值 | 分母 | 判据编号 / 口径角色 | 来源路径 | 来源 sha256 |
|---|---|---|---|---|---|
| `L-3_paren_block_any` | **0.001961（1/510）** | 510（全部 MSG） | `L-3`；闸线 **≥0.55** ⇒ **未达标**（差 54.80pp，D12-H 预登记 §4 反事实） | `tools/d5/dialogue_metrics.py` | `1d914735…1271` |
| `addr_head_strict` | **0.925490（472/510）** | 510（body 非空 MSG） | `addr_head_strict`，**判据唯一口径**（amendment3 §C） | `code/config/personas.json` | `08d11eb3…0f7d` |
| `addr_head_loose` | **0.909804（464/510）** | 510 | `addr_head_loose`，**上界参照，不作判据** | `code/config/personas.json` | `08d11eb3…0f7d` |
| `addr_head_pfx2` | **0.876471（447/510）** | 510 | `addr_head_pfx2`，**下界参照，不作判据** | `.worktrees/d12h-pairing/tools/d12h/shape_gate.py` | `f7740b6d…0ea3` |
| `addr_head_pfx2_plus` | **0.917647（468/510）** | 510 | `addr_head_pfx2_plus`，**参照量 `role=reference_only`**，不作判据 | `.worktrees/d12h-pairing/tools/d12h/shape_gate.py` | `f7740b6d…0ea3` |
| `addr_head_alias` | **0.023529（12/510）** | 510 | `addr_head_alias`，**只读指示量 `role=reference_only`**，**不得进入任何判定** | `code/config/personas.json` | `08d11eb3…0f7d` |
| `L-1_len_p50` | **56.0** | 510（分位分母） | `L-1`（含括号块） | `tools/d5/dialogue_metrics.py` | `1d914735…1271` |
| `L-1_len_p50_excl_paren` | **56.0** | 510 | `L-1`（去括号块；与 T5「53」同口径） | 同上 | 同上 |
| `L-7_dup_ngram8_rate` | **0.596078（304/510）** | 510（全部 MSG） | `L-7`，**跨批不可互译** | 同上 | 同上 |

`L-7` **本批索引 sha256 = `465593b850d69eaae8f859bf143a1cec3d91334497b27a12785d386e0c8b3f22`**（本批索引共 **23971** 个 gram，`dup_msgs = 304`，规则见下）。

### 4.2 T5（`n_msgs = n_bodies = 510`）

| 指标 | 数值 | 分母 | 备注 |
|---|---|---|---|
| `L-3_paren_block_any` | **0.578431（295/510）** | 510 | 与 CYCLE-12 引用的 T5 `57.84%` 一致 |
| `addr_head_strict` | **0.386275（197/510）** | 510 | 判据口径 |
| `addr_head_loose` | **0.409804（209/510）** | 510 | 与 CYCLE-12 §2.3 引用的 T5 `40.98%` **一致 ⇒ 该参照值用的是 loose 口径** |
| `addr_head_pfx2` | **0.364706（186/510）** | 510 | 下界参照 |
| `addr_head_pfx2_plus` | **0.370588（189/510）** | 510 | 参照量（reference_only） |
| `addr_head_alias` | **0.003922（2/510）** | 510 | 只读指示量（reference_only） |
| `L-1_len_p50` | **64.5** | 510 | —— |
| `L-1_len_p50_excl_paren` | **53.0** | 510 | **CYCLE-12 §2.3 引用的 T5「53」= 此 `excl_paren` 口径**（不是 64.5） |
| `L-7_dup_ngram8_rate` | **0.486275（248/510）** | 510 | 与 CYCLE-12 引用的 `48.63%` 一致 |

`L-7` **本批索引 sha256 = `aa1c61fc049532f5b97bd5c3b93cf05da6e85efba26b8b4a728737c3f8650c31`**（本批索引共 **27540** 个 gram，`dup_msgs = 248`）

> **跨批不可互译（硬约束）**：两批 `L-7` 的索引 sha256 不同（`465593b8…` vs `aa1c61fc…`）⇒
> `59.61%` 与 `48.63%` 之差**不得**读作「更差 10.98pp」，只能读作「各批内部去重程度」（CYCLE-12 §3.8 / §5.4）。
> 索引构造规则（写死）：`norm_i = d5.normalize_body(body_i)`；`shingles_i = {norm_i[k:k+8]}`；
> 索引 `gram → [msg 下标]` 升序；序列化为每行 `<gram>\t<idx,idx,…>`、按 gram 字节序升序拼接后取 sha256。

## 5. 正面回答 `§3.6`：`90.98%` 与 `87.65%` 到底差在哪

**结论先说**：两值**分母相同（都是 510）**，差异**全部来自命名匹配规则**，共 **17 条消息**；
`17 = 464（loose）− 447（pfx2）`。`17` 条差集在 `d12h_addr_head_triage.json.diffs.loose_but_not_pfx2` 里**逐条可查**（含 seq / round / body）。

### 5.1 三口径定义（全部有原文依据，不自造）

| 口径 | 定义（实现写死） | 依据 |
|---|---|---|
| `addr_head_strict` | 正文 `startswith` 20 个 `config/personas.json::display_name`（去 `青溪镇·`）之一 | `d12h_verdict_amendment3.md` §C 行 47；**冻结判据口径** |
| `addr_head_loose` | 首句 **2–6 字**且以 `，/：` 收尾（不查名字） | 同 §C 行 48；**上界参照** |
| `addr_head_pfx2` | 名字在**第 0 位**、其后 **≤2 个称谓字**、再接 `，,：:` 之一（16 个世界显示名） | 同 §C 行 49 + `shape_gate.py::is_addr_head()` 逐字引入；**下界参照** |

### 5.2 D12-H 三个数的完整对账（同批、同分母）

```
strict  472/510 = 92.5490%   ← 与 amendment3 §C 的 92.55% 逐位吻合
loose   464/510 = 90.9804%   ← 与 prose 的 90.98% 逐位吻合（复现了那条「无出数器」的 prose 值）
pfx2    447/510 = 87.6471%   ← 与落盘 shape_gate_d12h_full.json 的 0.876470… 逐位吻合
```

**⇒ `90.98%` 不是错值、`87.65%` 也不是错值：它们是同分母下的两个不同口径。**

### 5.3 差集分解（17 条 = loose 命中但 pfx2 不命中）

| 子类 | 条数 | 说明 | 例子（`seq`） |
|---|---|---|---|
| 正式名后接 **`、`（并列称呼）或 `——`（破折号）** | 3 | pfx2 的标点集只有 `，,：:`，**不含 `、` 与 `——`** ⇒ 真称呼被判漏 | `61157`「老周、老石，你们来得正好——…」、`82860`「老石——你听，…」 |
| **非正式称呼变体**（真称呼，但不在 20 个 display_name 表内） | 12 | `老陈`(4)、`老陈啊`(2)、`老李`(1)、`周先生`(2)、`周公`(2)、`周文书`(1) —— 世界里对同一人的口语称呼与 display_name（`陈医`/`周公文`）不同形 | `62`「老陈，这块榫头还差半指宽…」 |
| **感叹词被误算** | 1 | 「哎哟，」首段 2 字 + 逗号 ⇒ loose 把它当称呼（§C 原文已预警「可能误算」） | `24063`「哎哟，我这肚子饿得咕咕叫…」 |
| 感叹词 + 真称呼 | 1 | 「哎哟老周，」 | `29374` |

反向差集：`strict ∧ ¬pfx2 = 25` 条 —— **19 条是「名字——」**（真称呼，pfx2 标点集不含破折号）、**6 条是「名字直接接正文/顿号」**
（如 `3867`「周公文把存折翻到第三格，…」是**主语位**用名，不是呼唤）。`pfx2 ⊆ strict` 成立（`set_relations.pfx2_subset_of_strict = true`）。

### 5.4 三个数彼此不是「上/下界」的严格包含关系（必须同屏的限定）

D12-H 集合关系（`d12h_addr_head_triage.json.counts`）：
`strict` 472、`loose` 464、`both` 450、**`strict_only` 22**、**`loose_only` 14**、`neither` 24。
⇒ `loose` 有 14 条 strict 不认（非正式称呼变体 + 感叹词误算），`strict` 有 22 条 loose 不认（名字起头但无标点/主语位用名）。
**两个口径互为部分补集**，谁也不是谁的严格上下界。

### 5.5 哪个口径是应有的判据口径 及其依据

**判据口径 = `addr_head_strict`（D12-H = 92.5490%，472/510）**，依据三条：

1. `v2/evidence/d12h_verdict_amendment3.md` §C 行 47 原文：**「`addr_head_strict`（冻结判据口径）92.55%……判据唯一口径；`shape_gate.py` 须对齐」**；
2. 同 §C 行 48/49 明确 `loose` 与 `pfx2` **「仅作上界/下界参照，不作判据」**；
3. 本出数器对 D12-H 复算得 **472/510 = 92.5490%**，与裁决件写死的 `92.55%` 逐位吻合 ⇒ 该口径定义可被独立复现。

**因此**：
- CYCLE-12 §2.3「prose `90.98%` vs 落盘 `87.65%` ⇒ `不可判`」这一矛盾**在本证据下已经消解**：
  两者是 `loose` 与 `pfx2` 两个**参照口径**，本来就不该被当作同一个量的两次测量；
- 该行结论应改写为：`addr_head_strict = 92.55%（判据口径）`，并把 `90.98%（loose，上界参照）`、`87.65%（pfx2，下界参照）` 并列标注口径名；
- **本条只做出数，不改报告**（报告属 `report-writer`），是否需要改判由 Leader 裁决。

### 5.6 两个参照量（Leader 裁决 FM-4 / FM-5 后新增，`role = reference_only`）

| 指标 | D12-H | T5 | 与谁比、差什么 |
|---|---|---|---|
| `addr_head_pfx2_plus` | **468/510 = 91.7647%** | **189/510 = 37.0588%** | 与 `pfx2` 的唯一差别 = 标点集加上 `、` 与 `——`。差集 `pfx2_plus − pfx2`：D12-H **21 条**、T5 **3 条**，即「真称呼被判漏」的部分（19 条「名字——」+ 2 条「老周、老石，」）。**说明 `pfx2` 作为 F2 会把真称呼算成未称呼。** |
| `addr_head_alias` | **12/510 = 2.3529%** | **2/510 = 0.3922%** | 首段是**结构化别名/敬称**（`(老|小|阿)+1–2字` 或 `1–3字+(先生/女士/老师/大夫/师傅/文书/掌柜/公/伯/叔/婶/哥/姐/爷/奶)`）**且不以任何 display_name 起头**。D12-H 的 12 条 = `老陈`(4)/`老陈啊`(2)/`老李`(1)/`周先生`(2)/`周公`(2)/`周文书`(1)，与 §5.3 人工清点**逐条吻合**。|

**纪律**：两者都 `role = "reference_only"`，**不得进入任何判定**；报告里只能以「描述性读数」出现。
`addr_head_alias` 的读数方向（D12-H 2.35% vs T5 0.39%）**不足以证明任何效果**——D12-H 的称呼是被提示词强制出来的，
别名多寡与其说反映「生活气息」，不如说反映「换了称呼词表」，故**只报数、不解释、不立论**。

## 6. 待裁决项与裁决结果（Leader 2026-10-24 已全部裁决，落地情况见「落地」列）

| 编号 | 事项 | 事实 | 裁决 | 落地 |
|---|---|---|---|---|
| `FM-1` | `loose`「首句 ≤6 字」下界未写死 | 下界 1 ⇒ 487/510=95.49%；下界 2 ⇒ 464/510=90.98%（= prose） | **冻结为 2** | ✅ 模块常量 `LOOSE_MIN_CHARS = 2` / `LOOSE_MAX_CHARS = 6`，带冻结理由注释；JSON 里 `frozen_constants` 可查 |
| `FM-2` | CYCLE-12 §2.3 的 T5 `len_p50 = 53` 口径 | T5 `all = 64.5`、`excl_paren = 53.0` ⇒ **53 是 `excl_paren`** | **接受为口径更正，不回改 CYCLE-12（冻结期）**，由 CYCLE-13 单列更正留痕 | ⏳ 交 `report-writer`（R1）执行 |
| `FM-3` | CYCLE-12 §2.3 的 T5 `addr_head = 40.98%` 口径 | T5 `strict 38.63%` / `loose 40.98%` / `pfx2 36.47%` ⇒ 该参照值用的是 **loose** | **判据口径 = `strict`；该条升为本周期最重要风险项**：CYCLE-12 §2.3 的 T5 基线 40.98%（loose）与判据口径（strict 38.63%）不一致 | ⏳ D12-I 收批时禁止沿用「addr_head_rate 26.44%（T5 41.00%，PASS）」；须用本出数器把 ON 臂与 T5 三口径并列，判定只用 strict；`shape_gate.py --t5-addr 0.41` 登记为口径错配缺陷（冻结期不改码） |
| `FM-4` | 口语别名不在 `display_name` 表 | D12-H 12 条以 `老陈/老李/周先生/周文书/周公` 起头 | **不纳入判据口径（扩表会破坏历史可比性），但作为独立指示量报出** | ✅ 新增 `addr_head_alias`（`role=reference_only`，见 §5.6） |
| `FM-5` | `pfx2` 标点集缺 `、` 与 `——` | 25 条 strict 命中而 pfx2 不命中（19 条「名字——」+ 2 条「名字、名字，」+ 6 条主语位用名） | **不改 `shape_gate.py`，增加参照量** | ✅ 新增 `addr_head_pfx2_plus`（`role=reference_only`，见 §5.6）；`shape_gate.py` 缺陷写进下一周期修复项 |

## 6b. D12-I 日志的可算性核验（**只验命令能跑通，不落判读结论**）

D12-I 仍在跑，其日志为**未收批**状态；下列核验**只证明三口径在 D12-I 日志上算得出来**，
数值**不构成任何判读**，也不得被 CYCLE-13 引用为 D12-I 结果（收批后须用同一命令重算）：

```bash
python3 tools/metrics/form_metrics.py \
  --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --code-dir .worktrees/d12i-aligned/code \
  --out /tmp/d12i_form_metrics_unsealed.json --batch-id D12-I-UNSEALED --no-timestamp
```

**核验结果（2026-10-24 02:2x，中途日志 117393→当时未收批）**：`rc = 0`，`n_msgs = n_bodies = 390`（未收批，条数仍在增长），
三口径均算得出来：`strict 0.289744（113/390）`、`loose 0.302564（118/390）`、`pfx2 0.246154（96/390）`、
`pfx2_plus 0.246154`、`alias 0`、`L-3 0.702564`、`L-7 0.561538`（索引 sha `ffb754af…10d0`）。

**三条必须同屏的限定**：
1. 以上数字是**未收批中途快照**，随日志增长会变，**不构成任何判读**，也不得被 CYCLE-13 当 D12-I 结果引用；
2. 撤回/作废前不得与 T5 做差：三口径的基线口径若用 `loose 40.98%` 或 `strict 38.63%`，差值完全不同；
3. **CYCLE-12 引用的形态闸读数 `addr_head_rate 26.44%（T5 41.00%，−14.56pp，PASS）` 的口径已复现**：
   口径 = `addr_head_pfx2`、分母 **174**、窗口 **`round < 20`**。
   复现命令与对拍（2026-10-24 复核，逐位相同）：
   ```bash
   python3 tools/metrics/form_metrics.py \
     --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
     --code-dir .worktrees/d12i-aligned/code --rounds 20 \
     --out /tmp/d12i_r20.json --batch-id D12-I-R20 --no-timestamp
   # n_msgs = n_bodies = 174
   # addr_head_pfx2 = 46/174 = 0.26436781609195403  ⇒ 26.44%
   ```
   对拍 `.worktrees/d12i-aligned/.../shape_gate_first20.json` 的 `metrics.addr_head_rate`，**逐位一致**。
   **另须记**：本 README 上文的 `n = 390` 是**另一窗口**（未收批全量快照）的读数，两者**不得混比**
   —— 混比正是先前把「可复原」误判成「不可复原」的原因（见下方「对拍三钉」）。

### 6c. 对拍三钉（比较两个读数前必须钉住的三件事）

任何「A 值 vs B 值」的对照（尤其跨人、跨工具、跨时点做的），必须先钉住：

1. **同一时点**：日志是否仍在增长（未收批快照 vs 已收批全量）；
2. **同一 round 窗口**：全量 / `round < 20`（1/3 处）/ 其他前缀；
3. **同一 body 判据与分母**：`strict / loose / pfx2 / pfx2_plus / alias` 哪一档，分母是「全部 MSG」还是「body 非空 MSG」。

**反面案例（本目录已发生一次）**：拿 D12-I 的 `n = 390` 全量快照读数（strict 28.97% / loose 30.26% / pfx2 24.62%）
去比对形态闸的 `26.44%`，因窗口不同（390 vs 174）而得出「口径不可复原」的错误结论；
按三钉改成 `--rounds 20` 后 `46/174 = 0.26436781609195403` 逐位命中。
⇒ 结论：**读数对不对得上，先钉三钉；钉不齐就不许下「不可复原」这类结论。**

收批后仍须用本出数器三口径并列重判，判定只用 `strict`（FM-3）。

## 7. 纪律自述

| 编号 | 事项 | 事实 | 影响 |
|---|---|---|---|
| `FM-1` | `addr_head_loose` 的「首句 ≤6 字」**下界**未写死 | 下界取 **1** ⇒ `487/510 = 95.49%`；取 **2** ⇒ `464/510 = 90.98%`（= prose 值）。本出数器取 **2** 只为复现落盘 prose 值，`d12h_verdict_amendment3.md` §C 原文未写死下界 | loose 仅作参照，不影响判据；但「90.98% 的定义」在原始件里是**不完整的**，建议下次裁决写死正则 |
| `FM-2` | CYCLE-12 §2.3 的 T5 `len_p50 = 53` 到底对应哪个口径 | 本批 T5：`all = 64.5`、`excl_paren = 53.0`。**53 是 `excl_paren`** | 报告若用 `len_p50` 做跨周期对比，须同屏写口径名，否则 D12-H 的 `56.0`（两口径同值）会与本批混比 |
| `FM-3` | CYCLE-12 §2.3 的 T5 `addr_head = 40.98%` 对应哪个口径 | 本批 T5：`strict 38.63%`、`loose 40.98%`、`pfx2 36.47%` ⇒ **报告该参照值用的是 `loose`** | 若 D12-I 形态闸 F2 改用 `strict`，则 T5 基线应为 **38.63%**，不是 40.98%；`shape_gate.py` 内 `--t5-addr 0.41` 的默认值需同步 |
| `FM-4` | 命名表与实际口语称呼不一致 | D12-H 有 **12 条**以 `老陈/老李/周先生/周文书/周公` 起头 —— 这些是**真称呼**，但都不在 20 个 `display_name` 内 ⇒ `strict` 与 `pfx2` **同时漏判** | `addr_head_strict` 存在**系统性低估**；是否把口语别名纳入判据口径，须裁决（本证据只报事实） |
| `FM-5` | `pfx2` 标点集缺 `、` 与 `——` | 25 条 strict 命中而 pfx2 不命中，其中 19 条是「名字——」、2 条「名字、名字，」 | 若沿用 `shape_gate.py`（Q-19：master 无该文件），其 F2 会系统性低估；本证据不改该文件 |

## 7. 纪律自述

- 零 LLM、零跑批：只读 `run.jsonl` 与 `config/`，不产生新跑批数据；`sys.dont_write_bytecode` 已开，**未在 `code/` 下留 `__pycache__`**（`git status code/` 无新增）。
- 未修改任何既有文件：本任务只新增 `tools/metrics/` 与 `v2/evidence/form_metrics/`。
- 未 commit、未 push、未 kill 进程、未建 worktree。
- 所有数值均带分母与复算命令；与既有落盘值对不上的一律列 `FM-*` 待裁决，**未调参凑数**。
- `addr_head_pfx2_plus` / `addr_head_alias` 在 JSON 里显式 `role: "reference_only"`，防止后来者误当判据；二者**不参与**任何判定分支（代码里没有以它们为条件的判断）。
- 措辞纪律：只用「达标 / 未达标 / 可复算 / 参照口径 / 待裁决」，不写「改善 / 提升 / 显著」。
