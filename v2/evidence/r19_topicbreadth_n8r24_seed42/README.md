# R19 · 话题展开 / 多线索（topic-breadth）on/off 双臂证据目录

> 批次：`n8r24 / seed=42`（pilot 规模，**放量到 n16 需 Leader 另行放行**）
> 分支：`feat/r19-topic-breadth`｜代码 commit：见 `code_sha.txt`（起跑前已提交，起跑后未再改 `code/`）
> 作者：life-engineer｜性质：**实现 + 取证**（不含最终报告，不 push）

## 0. 纪律（先读，报告若违反即判不可判）

1. **mock 不得用于判断效果。** mock 只允许验「开关隔离 / 审计字段 / 指标管道」；
   mock 的 `landed=0` 不得被引用为「改造无效」或「居民不会展开话题」（R3:347 同类限制：
   `RuleBasedLLM` 不读语义，只吐模板句）。
2. **不许把「F-2 0/480 → >0」写成改善**：那是死尺子被修好，不是对话变好。
   `F-2_topic_drift`（旧口径）保留输出并标 `LEGACY_DEAD_RULER`（`tools/d5/dialogue_metrics.py`）。
3. **主判据 = 人工 precision（≥15 条 tag 追加事件，precision ≥0.6 才算「真改善」）**；
   `tag_added` 量与通过率 T 是副指标；`content_drift` **只作不恶化守卫**（on ≥ off − 5pp），不加分。
4. **不允许跨词表求精确差值**：旧词表（board-scout 20:11 复核时那一版）未留 sha、已不可复算，
   与现词表的数字只能并列，不能写「9.6% → X%」。同理禁止「解决 16 倍」「L-13 归零」这类表述。
5. **meta.json 硬门**：任一臂缺 `meta.json` ⇒ 该批不可入结论（CYCLE-03:203 G-3 的教训）。
6. 守卫门槛（任一击穿即不得宣称改善）：`L-6`/`L-7` 不得击穿；`F-1` 闲聊率不得同步恶化；
   `meta.json` 必须存在且 `assertions.code_unchanged_during_run = true`。

## 1. 这一轮改了什么（代码 diff 可审）

| 文件 | 改动 |
|---|---|
| `code/life/topic_breadth.py`（新增） | 话题 id → 人话（`label`）；`turn>=1` 的确定性岔题指派（`plan`，sha256）；生成后**正则双条件内容门控**（`confirm`：命中 shift 且不命中 base）；审计 `audit` |
| `code/life/agent.py` | 两处提示词改用 `_topic_label()`；回复提示词插入岔题提示（`_topic_shift_line`）；生成后按 `_topic_shift_tag()` 追加**第二个** tag；`ctx.topic_breadth` 审计（关闭时提示词与 payload 逐字节不变） |
| `tools/d5/dialogue_metrics.py` | 旧 `F-2_topic_drift` 保留并标 `LEGACY_DEAD_RULER`；新增 `F-2_content_drift`（纯内容 jaccard，不看 tag）、`F-2_tag_switch`、`F-2_tag_change_split`（`tag_added` / `tag_replaced`）；`F-2b` 补 `denominator_threads` 并统一分子分母到 `mixed_key` 线程口径 |
| `code/life/tests/test_r19_topic_breadth.py`（新增） | 22 项：OFF 逐字节不变 / 人话化 / 双条件门控 / 确定性 / 词表自洽 |

开关：`LIFE_PROMPT_TOPIC_BREADTH`（默认 **OFF**）。off 臂 = 不设该变量（进程内 `/proc` 留证见 `run_off/env_dump.txt`），
on 臂 = `=1`（`run_on/env_dump.txt`）。**两臂同一份已提交代码**，唯一差异就是这个变量。

## 2. 目录内容

```
r19_topicbreadth_n8r24_seed42/
├── README.md                     # 本文件（纪律 + 口径 + 复算命令）
├── run_off.sh / run_on.sh        # 两臂完整起跑命令（setsid，可照抄重跑）
├── fingerprint_4trees.py         # 四子树逐文件 sha256 聚合指纹（code_sha 之外的硬证据）
├── off_gate_fp.py                # off 基线「门控假阳性率」复算器（回归用）
├── off_gate_fp_n16r84.txt        # 在上一轮真 off 基线（686 条）上的假阳性率读数
├── summarize_arms.py             # 两臂读数汇总（D / through / landed / 指标 / 守卫）
├── precision_sample.md           # 人工 precision 抽样（≥15 条 tag 追加事件，含原文）
├── summary.json                  # 上面脚本的机器可读输出
├── finalize_arm.sh               # 收批三件套：跑后指纹 + meta 重生成（传起跑快照）+ llm-cost
├── readings.md                   # 双臂读数表（工具输出，不含判定）
├── code_identity_note.txt        # 两臂 code_sha 不同的原因与「运行代码相同」的双重证明
├── run_off/  run_on/             # 各臂：run.jsonl + meta.json + env_dump.txt
│                                 #       + fingerprint_before.txt + code_fingerprint.txt
│                                 #       + git_status_start.txt + llmcost.json + llmcost_stdout.txt
├── run_off_git_status_start.txt  # on 臂起跑前 git status 快照（off 臂快照在 run_off/ 内）
├── run_off_host.log run_on_host.log
└── llmcost_off.json llmcost_on.json   # 如存在：obs llm-cost 的单独副本
```

## 3. 复算命令（全部只读、幂等）

```bash
cd <repo>
# A. 指标（单一真源；不改日志、不联网）
python3 tools/d5/dialogue_metrics.py --log v2/evidence/r19_topicbreadth_n8r24_seed42/run_on/run.jsonl \
        --meta v2/evidence/r19_topicbreadth_n8r24_seed42/run_on/meta.json \
        --out-json /tmp/r19_on.json --out-md /tmp/r19_on.md

# B. 真 LLM 验真（rc 必须 0；by_provider 只能有 openai_compat）
cd code && python3 -m obs llm-cost --log ../v2/evidence/r19_topicbreadth_n8r24_seed42/run_on/run.jsonl \
        --require-provider openai_compat --out ../v2/evidence/r19_topicbreadth_n8r24_seed42/llmcost_on.json; echo rc=$?

# C. 代码身份（两臂四个指纹必须逐位相同）
python3 v2/evidence/r19_topicbreadth_n8r24_seed42/fingerprint_4trees.py \
        --out /tmp/fp_now.txt && head -1 /tmp/fp_now.txt

# D. 门控假阳性率（off 基线，回归用）
python3 v2/evidence/r19_topicbreadth_n8r24_seed42/off_gate_fp.py \
        --log v2/evidence/run_worldline_c1_ctrl_n16r84_seed42/run.jsonl

# E. 两臂汇总 + 抽样
python3 v2/evidence/r19_topicbreadth_n8r24_seed42/summarize_arms.py \
        --off v2/evidence/r19_topicbreadth_n8r24_seed42/run_off \
        --on  v2/evidence/r19_topicbreadth_n8r24_seed42/run_on \
        --out v2/evidence/r19_topicbreadth_n8r24_seed42/summary.json \
        --sample v2/evidence/r19_topicbreadth_n8r24_seed42/precision_sample.md
```

## 4. 已知限制（写清楚，避免过度解读）

- **`tag_replaced` 结构上恒为 0**：本实现只「追加」不了「替换」⇒ 本轮做的是**话题展开（多线索并行）**，
  不是「岔题换话题」。报告措辞必须按前者。
- 门控是**正则**（动作+对象结构），不是语义判定：它能挡住「本来就在说该话题」的句子，
  但挡不住「生硬拼接关键词」。所以 precision 必须人工抽检，不能只看 T。
- `content_drift` 在改造前本来就 66–73%（人本来就在换话头），因此它只能当「不恶化」守卫。
- n8r24 规模：消息量约百条级，比率类读数只作 pilot 参考，**放量前不得外推**。

## 5. 本批实际读数（工具输出，**不是判定**）

见 `readings.md`（同一份数据也机器可读地存在 `summary.json`）。要点：off 臂 `D=0`（行为侧开关
关闭证明），on 臂 `D=47 / through=10 / T=21.28%`，`tag_added=10`（相邻对分母 67），
`F-2b 多话题线程 7/30`，`tag_replaced` 两臂皆 0（结构使然），`content_drift` 两臂 0.626866（未恶化），
`L-13` 两臂 0/97，守卫 L-6/L-5 两臂 0、L-7 0.2577→0.1856（未击穿）、F-1 两臂 0.628866（未恶化）。

⚠️ **本批（n8r24）落地事件只有 10 条 < 15**，达不到「人工 precision ≥15 条」的主判据门槛，
因此本批**只能**判「机制接线成立 + 召回与守卫通过」；precision 与效果结论必须放量到 n16r60 之后再做。
