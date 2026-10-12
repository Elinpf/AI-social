# M2b 准入实验：judge「thinking=T2 生成式」vs「thinking=false 受限选择」+ 校准度（T212）

> 作者：freeze-layer-dev ｜ 日期：2026-10-12
> 端点：`http://172.16.3.41:31809/v1`（OpenAI 兼容）｜模型：`DeepSeek-Flash`
> **产物**：`/tmp/provider-probe/m2b_pairs.jsonl`（210 对）
> **sha256**：`b52b73c8fc2f439314efb0f923d4a0dc8639c2bfe6626a69eba1efea4633328c`
> **生成命令**：
> ```bash
> PROBE_BASE=… PROBE_MODEL=DeepSeek-Flash PROBE_KEY=$LLM_API_KEY \
>   python3 /tmp/provider-probe/m2b_ab_v2.py --n 210 --out /tmp/provider-probe/m2b_pairs.jsonl
> # 指标：python3 /tmp/provider-probe/m2b_metrics.py   （调 obs.calibration，不自写 ECE）
> ```
> **安全**：密钥仅从 env 读，**未落盘/入日志/入报告**；脚本与产物均在 `/tmp`，**未改本项目 `code/`**（仅只读 import `obs.calibration`）。

---

## 0. 结论（TL;DR）

1. **判别式「受限选择」在质量上等价于生成式**：两模式在**双合法**样本上**一致率 99.0%**（203/205），**合法率 B=1.000**（A=0.976）。
2. **判别式成本/延迟降一个量级**：输出 token **16.3×↓**（1604 vs 26166；A 的 25413 是 reasoning）、延迟 **~10.4×↓**（35.4s vs 369.4s）、**reasoning=0**。
   → **M2b「受限选择」值**：**是**（省钱省时、质量等价）。
3. **「置信度回退」暂不具备开启依据**（**不是** ECE 超标，而是**证据不足**）：门禁集 `ece_N=81`（**coverage 81/210 = 38.6%**），可靠性图**只有单一高置信档**（0.9–1.0，acc=1.0）→ **无分层、无负例**，ECE=0.0030 **不可采信**；分差相关性**不可测**（无错误样本）。
4. **本维度集无世界侧 oracle** → 按口径：**回退判据一律用规则（候选分值差阈值），不采信模型自报置信度**；而该阈值在本集**无法标定**（无负例）→ 需**更难/更接近真实分布的样本**再测。

---

## 1. 方法与真值口径（写死、可复核）

- **同一批请求、两条路**：`reference_label = A（thinking=T2 生成式）`；`predicted_label = B（thinking=false + response_format json_schema(enum) + logprobs）`。
- **两测分离**：**一致率**用 A 作参考；**准确率/ECE** 用 `true_label`，**绝不把 A 当正确答案**。
- **true_label 口径**：`constructed_rule_unambiguous`——证据由**明确规则唯一决定**的项（`certain=True`）给真值；**borderline/混合项 `true_label=None`，剔除出 ECE**。
- **⚠️ 真值来源限制（如实）**：既有日志**无法重建 judge 输入**（`LLM_JUDGMENT.context_ref=null`；freeze 缓存只存输出不存 prompt），且本维度集（mentor_relation/reputation/trust）**无世界侧"确定性后果"oracle** → **「与后果吻合」的真值【不可得/未验证】**。故真值为**规则化构造标注**（非日志 join）。`parties/judgment_id/round` 为占位，**不 join**。
- **取数口径（obs）**：可空字段各自剔除并计数——`agreement_N` / `ece_N` / `gap_N` 单列；`certain` 作真值可信度开关；门禁 ECE 只取 `certain & constructed` 子集。
- **指标一律调 `obs.calibration`**（`agreement_rate` / `calibration_report` / `score_gap_analysis`），**不自写第二份 ECE**。

### 1.1 维度名映射（**同名不同义**入口，务必看）

T212 的维度名是**探针脚本自定的样本分组标签**，映射如下：

| T212 维度名 | life/obs 正式维度？ | 说明 |
|---|---|---|
| `mentor_relation` | ✅ **已登记** | `config/activity_templates.json`（`soft_judgment.dimension`）+ `obs/params.py::SOFT_JUDGMENT_DIMENSIONS` 首位；**life 无对应 `LLM_JUDGMENT` 调用点**＝"已登记、未接线" |
| `reputation` | ❌ **无** | `config/ obs/ life/` 无登记/调用点（仅 `v1.2/01` 等文档提及）→ **T212 内部标签** |
| `trust` | ⚠️ **部分** | life 有 `trust` **数值关系维**（`[W_MIN,W_MAX]`），但本集用**二元 `increased/decreased`** → **T212 内部标签，非该维语义** |

> ⚠️ **下游注意**：Leader 据此下的「`mentor_relation` 维加规则兜底」指令，针对的是**已登记但 life 无调用点**的维度——**接线后才生效**；`reputation`/`trust` 的结论只适用于 T212 内部标签，**不得直接映射到 life**。

---

## 2. 数字

### 2.1 样本与口径 N
| 口径 | N | 说明 |
|---|---|---|
| `n_pairs` | 210 | 构造集（mentor 70 / reputation 70 / trust 70） |
| `agreement_N` | 210 | 有 predicted_label 的样本 |
| `ece_N`（门禁集） | **81** | certain & constructed & B 可判 & conf 可得 |
| `gap_N` | 54 | 有 top-2 分差的样本（均在门禁集内） |
| `confidence==null` | 101 | 剔出 ECE、仍进一致率 |
| `true_label==null` | 71 | borderline，剔出准确率/ECE |

### 2.2 一致率 / 合法率
| 指标 | 值 | N |
|---|---|---|
| 一致率（B==A，**双合法**） | **0.9902**（203/205） | 205 |
| 一致率（含 A 解析失败计为不一致） | 0.9667（203/210） | 210 |
| 合法率 A（生成式） | 0.9762 | 210 |
| 合法率 B（受限选择） | **1.0000** | 210 |

> A 有 **5** 条未产出可解析 label（`content=null`，多为 borderline/需长 reasoning 的项）；B 因 `json_schema(enum)` 强制，**合法率 100%**。

### 2.3 成本 / 延迟（全 210 对求和）
| 模式 | tokens_in | tokens_out | reasoning | 延迟合计 | 延迟均 |
|---|---|---|---|---|---|
| A 生成式(thinking=T2) | 31002 | **26166** | 25413 | 369.4s | ~1.76s |
| B 受限选择(thinking=false) | 25752 | **1604** | 0 | 35.4s | ~0.17s |
| **A/B 比** | 1.20× | **16.31×** | — | **10.4×** | ~10.4× |

### 2.4 校准（门禁集 `ece_N=81`；调 `obs.calibration`）
- **ECE = 0.0030**（B=10 档，阈值 0.05）——**数值达标**；
- **可靠性图：仅 1 个非空档**（0.9–1.0，count=81，avg_conf=0.997，acc=1.0）；
- `tiered`：`n_nonempty_tiers=1`、`monotonic=true`（**平凡成立**）、`top_minus_bottom=0.0`；
- `confidence_fallback_allowed = true`（因 ECE≤0.05）——**但这是退化判据**（单档、无负例），**不足以支撑校准结论**；
  > 独立复算（obs-stats-dev）：**obs 门 `evidence_sufficient=False`**（`n=81,n_pos=81,n_neg=0,tiers=1` → `allowed=False`）——commit `3645e08`；与本节结论一致。
- **分差相关性（`score_gap_analysis`）：不可测**（门禁集无错误样本 → 无正负类）→ 【未验证】。
- 分维度准确率（B vs 真值）：mentor_relation 27/27=1.0、reputation 54/54=1.0；**trust 0**（certain 项 confidence 提取失败，未纳入）。

> **coverage 顶格声明**：门禁 ECE 仅覆盖 **81/210 样本（38.6%）**，且**分布退化（单一高置信档、零错误）** →
> **ECE=0.0030 不构成"校准可用"的证据**；**结论：不足以支撑开启置信度回退**（见 §4）。

### 2.5 分歧抽样（人工可复核）
**真实分歧（A 与 B 均合法且不同）= 2 条**，均在 **mentor_relation 的 borderline 项**：
| id | A(生成式) | B(受限选择) | certain | 证据 |
|---|---|---|---|---|
| m53 | not_formed | **formed** | False | 阿凯 与 阿林 **偶尔**一起烘焙，互相指点过几次，**但无固定师徒安排**。 |
| m63 | not_formed | **formed** | False | 小叶 教过 阿澈 **两次**基础园艺，之后各忙各的，很少再往来。 |

> 观察：**B（判别式）在"师徒关系"边界上更宽松**（把"偶尔指点/教过两次"判为 formed），A 更严格。两者均非显然对错（borderline）；**建议 M2b 启用时对 `mentor_relation` 用更明确的阈值/规则兜底**。

**另 5 条为 A 解析失败**（非真实分歧）：A 的 `content=null`（reasoning 耗尽）而 B 正常出标签，例：`r6/r14/r46`（reputation borderline "平时热心但这次说了重话" → B=neutral, conf 0.72–0.93）。

### 2.6 obs 口径报告（`obs.admission` / `obs.calibration.multiclass_report`，口径唯一）

**准入报告** `admission_report(records)`：
| 项 | A 生成式 | B 受限选择 | 比(B/A) |
|---|---|---|---|
| 合法率 | 0.97619 | **1.00000** | — |
| tokens_total | 57168 | 27356 | 0.479 |
| tokens_out | 26166 | 1604 | 0.061 |
| reasoning_tokens | 25413 | **0** | — |
| 延迟 p50 (s) | 1.55 | **0.1285** | **0.083（≈12×↓）** |

**多类校准** `multiclass_report(certain 子集)`：`n=99`，**Brier=0.1819**，**logloss=5.0263**。
> ⚠️ 口径说明：多类 `n=99` 比门禁 `ece_N=81` 多（因 `label_probs` 覆盖 > `confidence` 覆盖）；`logloss` 偏高部分来自**提取缺口**（少数项 B 标签不在可提取的 `label_probs` 中，使 `p_true→eps`），**不能单独读成"校准差"**；与"分布退化、无负例"是一致的信号——**校准证据仍不足**。

---

## 3. 复现命令

```bash
set -a; . code/.env.local; set +a    # 提供 LLM_API_KEY（禁止外泄）
export PROBE_BASE="http://172.16.3.41:31809/v1" PROBE_MODEL="DeepSeek-Flash" PROBE_KEY="$LLM_API_KEY"
python3 /tmp/provider-probe/m2b_ab_v2.py --n 210 --out /tmp/provider-probe/m2b_pairs.jsonl
sha256sum /tmp/provider-probe/m2b_pairs.jsonl   # b52b73c8…328c
python3 /tmp/provider-probe/m2b_metrics.py      # 调 obs.calibration
```

---

## 4. 对 M2b 的裁决

| M2b 组件 | 裁决 | 依据 |
|---|---|---|
| **受限选择**（判 label） | ✅ **采纳** | 一致率 99.0%（双合法）、合法率 100%、成本 16.3×↓、延迟 10.4×↓ |
| **置信度回退**（用模型自报 conf 降级） | ❌ **暂不开** | 门禁集 coverage 仅 81/210 且**分布退化（单档、零错误）**，ECE 不可采信；**本维度集无 oracle → 按口径回退一律用规则** |
| **规则回退**（候选分值差阈值） | 🟡 **方向采纳，阈值待标定** | `score_gap_analysis` **不可测**（无负例）→ 阈值需在**更难样本**上标定【未验证】 |
| 生成式 A（thinking=T2） | 保留为**参考/关键事件** | 成本高 16×，但作为金标参考仍有用 |

**«thinking 到底值不值这个钱»**：**在"出判定标签"这件事上不值**——判别式同样能出（且格式 100% 合法），成本/延迟降一个量级；**thinking 的价值需在"确实需要推理"的维度上单独证明**（本实验未覆盖，标【未验证】）。

---

## 5. 未验证项（不得以推断代替）
- 校准（ECE/分差相关性）：**样本量不足 + 分布退化** → 结论"不足以支撑"，非"达标"。
- `trust` 维度 conf 提取失败（0 样本进门禁）→ 该维度校准【未验证】。
- 「与确定性后果吻合」的真值：**本维度集不可得**（无 oracle）。
- 多类 Brier / log-loss：待 `obs/calibration` 增强函数就绪后补（obs-stats-dev 已同意加）。
