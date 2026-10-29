# 借臂路线终止：`f3_on` 不宜用 + 干净供给 5 条 + 已用基准 47（只读核算件）

> 核查：`dialogue-core-dev`｜2026-10-29｜**只读：不跑批、不改 `code/`、未提交（提交权归 Leader）**
> 起因：batch4 因「seed 不改线程结构」作废后，唯一免花钱的路是「借现成臂的短线程」。
> 本件把这条路的最后一次核算与**终止裁定**写死，避免下一轮再从"借某条臂凑样本"重新开始。

---

## 0. 一句话

**`f3_on` 三条件中 ①c 失败、干净供给仅 5 条（不足 12）、且这 5 条已在展示件中出现（盲评泄漏）** ⇒ 该臂不用；
**权威已用集是 47（不是 36）**；**借臂路线终止**。

---

## 1. `f3_on` 可用性三条件（逐条）

对象：`v2/evidence/run_f3_on_n16r60_seed42/`（`run.jsonl` 502 条 MSG／**170 线程**／`maxround=59`）

| 条件 | 结果 | 依据 |
|---|---|---|
| **①a** 目录非 `INVALID`/`ABORTED`，且有 `meta.json` | **✅ 符合** | 目录名无 `INVALID`/`ABORTED` 字样；目录内含 `meta.json`(5339 B) + `run.jsonl` + `host.log` |
| **①b** `obs llm-cost --require-provider openai_compat` 可验，**或**已有入库存证 | **✅ 符合（存证分支）**<br>**存证来源为审计件 `f3_on_official.json`（B-10/B-19/B-20/B-11），不是 `obs llm-cost` 原样输出**；本机无 `obs` 命令，无法补原样输出 | **本机无 `obs` 命令**（`which obs` 为空）⇒ 不能现场跑。改由入库件 `v2/evidence/f3_on_official.json` / `.md` 提供等价存证：`B-10_provider = openai_compat ✅`；`B-19_provider_distribution = {openai_compat: 2869} ✅`；`B-20_model_no_mock = [DeepSeek-Flash] ✅`；`B-11_real_calls dialogue_calls=502 ✅`；`llm.degraded_calls = 0`；且 `inputs.run_sha256 = 087072f84518eb009fb8d0a6ec445c5515b7561c1f031430702a5187394af16c` **与实测 `run.jsonl` sha 逐字相同（MATCH）**；`meta.provider = openai_compat`、`meta.fallback_detected = false` |
| **①c** 与 A5 臂（`run_a5_real_n16r42_seed42`）线程集交集 = 0 | **❌ 不符合** | 交集 **11** 条：`TH-P001-P002-4`、`TH-P002-P007-39`、`TH-P002-P007-40`、`TH-P006-P002-24`、`TH-P006-P002-25`、`TH-P007-P005-18`、`TH-P007-P005-4`、`TH-P009-P004-0`、`TH-P010-P004-27`、`TH-P010-P009-36`、`TH-P011-P012-0` ⇒ **不是独立样本源**，只是同一线程池的另一份措辞 |

⇒ **三条件缺一即不可用；本条 ①c 失败**。

**①b 的两条限定（写死，勿删）**

1. **禁止**在本件任何位置把 ①b 写成「真 LLM 已验证」或「成本已核实」。
   依据：**存证能把"这批是真的"钉住，不能把"花了多少"钉住**——`f3_on_official.json` 证的是 provider/model/real-calls 与 `degraded_calls=0`，
   它**不是**一次独立的成本核算（本机无 `obs`，无 `llm-cost` 原样输出）。
2. **`inputs.run_sha256` 与实测 MATCH 一句必须附命令与输出**（否则读者无法复算）。核对命令与输出如下（原样）：

```bash
$ sha256sum v2/evidence/run_f3_on_n16r60_seed42/run.jsonl
087072f84518eb009fb8d0a6ec445c5515b7561c1f031430702a5187394af16c  v2/evidence/run_f3_on_n16r60_seed42/run.jsonl
# 审计件内记载（v2/evidence/f3_on_official.json → inputs.run_sha256）：
# 087072f84518eb009fb8d0a6ec445c5515b7561c1f031430702a5187394af16c   ← 与上行逐字相同 ⇒ MATCH
```

---

## 2. 权威已用集 = **47**（**36 是旧值**）

| 组成 | 条数 | 来源文件（sha8） |
|---|---|---|
| batch1 | 12 | `d12c_a5_sampled_threads_raw.txt`（`9bb0d79e`） |
| batch2 | 12 | `d12c_a5_batch2_raw_clean.txt`（`0ffeac1e`） |
| batch3 | 12 | `d12c_batch3_sampled_raw.txt`（`7a7f8ff6`） |
| **batch5** | **12** | `d12c_batch5_sampled_raw.txt` |
| batch1/2/3 小计 | 36 | — |
| **36 ∪ batch5 交集** | **1**（`TH-P009-P004-0`） | — |
| **权威并集** | **47** | — |

> **留痕：`36` 是旧值，派卡时被写回。** 派本卡时卡面写"batch1/2/3 共 36 个已用 id"，而 `d12c_batch5_sampled_raw.txt` 已存在（12 条，源臂 `d1_f6off` r84）。
> Leader 已确认："我的 `batch6_feasibility` 里用的就是 47，但派卡时又写回了 36"——**同一日对同一个量给出两个值，属"引用旧值"类错误**（与前一日"46→36"同类）。
> ⇒ **凡"已用 id"一律引用并集 47，并注明构成；不得只写 36。**

---

## 3. 净供给算式（2–3 轮层，`f3_on`）

```
2–3 轮线程总数            23        （层分布 {1:81, 2-3:23, 4-6:66}）
− 尾截断                  2         （逐条见下方表；线 min(round) > maxround−(max_turns−1) = 59−5 = 54）
= 非尾截断                21
− 与 36 已用重叠           4         （TH-P002-P007-39 / TH-P002-P007-40 / TH-P009-P004-0 / TH-P011-P012-0）
− 与 batch5 重叠           8         （见下）
− 与 A5 线程集重叠        11
= 并集排除                16
⇒ 净供给                  21 − 16 = 5
```

**被排除的 2 条尾截断（逐条，可复算）**

| thread_id | 条数 | `min(round)` | 各回合 `round` | 判定（`min(round) > 54`） | 判据式 `min(round)+(max_turns−1) ≥ maxround` |
|---|---|---|---|---|---|
| `TH-P008-P002-55` | 3 | **55** | 55, 57, 58 | **截断** | 55 + 5 = **60 ≥ 59** ⇒ 剩余回合不足以长到 6 轮 |
| `TH-P011-P010-55` | 3 | **55** | 55, 57, 58 | **截断** | 55 + 5 = **60 ≥ 59** ⇒ 同上 |

（`round` 一律取自 `msg_id` **次末段**；`thread_id` 末段**未**用作数据源；`msg_id` 解析失败 0 条。）

**剩余 5 条 + 各自的"展示/报告件出现次数"**（`grep -rl <id> v2/evidence/`，已排除该臂自身日志）：

| # | thread_id | 判读件引用 | **展示/报告件引用** | 主要落点（例） |
|---|---|---|---|---|
| 1 | `TH-P001-P005-39` | 0 | **34** | `cycle25_shots/threads_CYCLE25-C43.json`、`samples_a0/samples.json` |
| 2 | `TH-P008-P006-27` | 0 | **1** | `cycle21_shots/threads_CYCLE-21B.json` |
| 3 | `TH-P010-P012-31` | 0 | **24** | `cycle25_shots/…`、`solitude_shots/threads_d27_C.json` |
| 4 | `TH-P013-P008-42` | 0 | **24** | `cycle25_shots/…`、`solitude_shots/threads_d27_C.json` |
| 5 | `TH-P013-P014-48` | 0 | **1** | `cycle21_shots/threads_CYCLE-21B.json` |

⇒ **这 5 条确实"未被判过"（判读件引用 = 0），但正文已进入对外报告/截图/样例包** ⇒ 作盲评时存在"读者已见过"的**泄漏风险**。

---

## 4. 三条裁定（Leader 2026-10-29，照此写死）

### ① `f3_on` 这条臂：**不用**
三条理由任一单独即足以否掉：**①c 失败**（与 A5 交集 11）、**干净供给仅 5 条**（不足 12）、**5 条已在展示件中出现**（盲评泄漏）。

### ② 那 5 条：**不做泄漏处置，但已弃用**
不处置的理由是成本：**5 条不足 12，"够不够用"的门槛都没过**；为 5 条做脱敏/重抽/遮蔽的成本高于重新造样本。
**"不处置"本身是决定**——故在此写明：**这 5 条因「不足 12 条」且「已泄漏」而弃用**，下一轮**不得**再拿它们来凑数。

### ③ 借臂这条路：**到此为止**
- `batch6_feasibility`：`R=3` 层零成本借臂净供给 **5 条**；
- 本件：`2–3 轮` 层零成本借臂净供给 **5 条**；
- ⇒ **两条路都是 5 条，都不到 12** ⇒ **零成本借臂已被证伪**。

**今后不许再提"借某条臂凑样本"，除非有人先拿出「净供给 ≥12」的现算**（含：权威已用集按 **47**、扣尾截断、扣与 A5 交集、并报展示件泄漏情况）。

---

## 5. 本件边界

- 只读核算，**未跑批、未改 `code/`、未提交**（提交权归 Leader）。
- 层/轮数口径与 `tools/b4/layer_census.py`、`tools/b4/pool_audit.py` 一致；`round` 只取 `msg_id` 次末段。
- 本件**不**对 A5 或其他臂做任何溯源改判；仅记录"该臂不可用"的事实与裁定。

---

`BORROW-ARM-CLOSED: 借臂路线终止；净供给不足，基准=47`
