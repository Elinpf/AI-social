# R1 · C1（F-6 ON 臂）预注册 —— 起跑前写死判据，读数到手只填空不改口径

> 作者：life-impl-1 ｜ 写入时间：2026-10-21 14:0x（**在 ON 臂起跑之前**）
> 分支：`feat/r1-f6-on-arm`（HEAD = `895b9a381cd5a1838c23bd3b38e139f7edade3b8`，与 `feat/life-memory-f6` 同树，**无代码改动**）
> 维度：C1 = F-6「跨天记忆进对话」ON 臂（侦察报告 §6.3 C1；梯队 Top1）

## 0. 为什么选 C1（对照侦察报告依据）

1. **生活气息口径**：R4 把「跨天记忆引用（F-6）」列为生活气息七维之一——「把前几天的事顺口带出来」是"像真的在过日子"的直接证据。现读数 **3.73%（19/510 条消息）**，即 96% 的台词不提过去。
2. **可复算性最好**：F-6 是 **per-message** 指标，分母 = 全部消息（510，远大于 68 门限）⇒ 本轮可以直接报**比率**，不像 C2（F-4 分母 22）/F-3（分母 36）只能报事件数。
3. **算力最省**：OFF 对照臂已存在（`v2/evidence/run_f6_off_n16r60_seed42/`，14:02 收尾，code_sha `895b9a3`，n16×r60 seed42，`[d2] OK`）⇒ 本轮**只需跑 1 个 ON 臂**（≈87 min 实测 5201 s），不是 2 个臂。
4. **单变量干净**：干预 = 一个 env（`LIFE_PROMPT_MEMORY_F6=1`），OFF 臂提示词逐字节不变（见 §4）。

## 1. 假设（起跑前钉死）

- **H1（主）**：ON 臂 `F-6_crossday_memory.timeref_rate` **高于** OFF 臂 3.73%。方向预期上升（干预确实把跨天记忆原文塞进了提示词）。
- **H2（守卫）**：ON 臂措辞重复率**不应**显著恶化：`L-6_dup_exact_rate`（OFF 10.20%）、`L-7_dup_ngram8_rate`（OFF 35.49%）。
- **H3（守卫）**：ON 臂 `L-8_agent_id_leak_rate` 保持 0（OFF 0.0%）。
- **H4（成本）**：ON 臂 token 成本上升幅度可量化（`obs llm-cost` 两臂对比），若上升 > 30% 必须在报告里明写。

## 2. 主/次/守卫指标与判据（全部用官方脚本，不另造指标）

| 角色 | 指标 | 来源（唯一真源） | OFF 基线 | 判据 |
|---|---|---|---|---|
| 主 | F-6 timeref_rate（per-message，den=全 MSG） | `tools/d5/dialogue_metrics.py` → `F-6_crossday_memory` | 0.037255（den 510） | ON > OFF 且差值方向可解释；den≥68 才可报比率（本轮满足） |
| 次 | `ctx.memory_refs` 审计字段出现条数（机制是否真的触发） | `run.jsonl` 的 MSG payload（`ctx.memory_refs`） | OFF：0 条（键不存在） | ON 应 > 0；实际值决定"干预是否落地" |
| 次 | M-1：回复正文与**同线程更早一天**消息的 6-gram 重合条数 | 本轮新增只读脚本 `v2/evidence/r1_f6_m1_ngram.py`（口径见脚本头部注释） | OFF 待算 | 只报事件数/占比，不与 F-6 混称 |
| 守卫 | L-6 / L-7 / L-8 | 同 `dialogue_metrics.py` | 10.20% / 35.49% / 0.0% | L-7 ≤ 基线+5pp 视为"未恶化"；否则判「用套路换生活气息」 |
| 守卫 | F-7(P1) 越界提及 | `tools/f7/f7_offscreen_mention.py`（口径 `v2/refs/F7-offscreen-criteria.md`） | OFF 待同口径复算 | 只登记，不作为改善证据 |
| 成本 | token / calls / cached | `python3 -m obs llm-cost --log … --require-provider openai_compat` | OFF 2878 calls / 1472 cached | 报差值，不设阈值裁决 |

**裁决规则（先写死）**：
- 若 H1 成立且 H2/H3 不被违反 ⇒ 结论 = 「F-6 干预有效且未用套路换」。
- 若 H1 成立但 L-7 恶化 > 5pp ⇒ 结论 = 「有效但代价是套路化」（照实写，不判改善）。
- 若 H1 不成立 ⇒ **阴性结果**，照实写「干预未抬升 F-6」，并给出可能原因（分叉/记忆池空/指令被模型忽略）。
- 任何情况下**不得**用"看起来更生活化"的主观描述替代读数。

## 3. 复现命令（从零到读数）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
git checkout feat/r1-f6-on-arm          # HEAD=895b9a3
pgrep -af "orchestration run|run_batch.sh"   # 必须为空

# ON 臂（唯一差异 = env；side-root 必须是新目录，禁止复用 OFF 的 /tmp/f6_off60_side）
mkdir -p v2/evidence/run_f6_on_n16r60_seed42
setsid nohup env LIFE_PROMPT_MEMORY_F6=1 \
  bash tools/d2/run_batch.sh \
    --out-dir v2/evidence/run_f6_on_n16r60_seed42 \
    --seed 42 --agents 16 --rounds 60 \
    --side-root /tmp/f6_on60_side \
  > v2/evidence/run_f6_on_n16r60_seed42/host.log 2>&1 &

# 两臂同口径复算
python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_f6_on_n16r60_seed42/run.jsonl \
  --meta v2/evidence/run_f6_on_n16r60_seed42/meta.json \
  --out-json v2/evidence/r1_f6_on_metrics.json --out-md v2/evidence/r1_f6_on_metrics.md
python3 tools/d5/dialogue_metrics.py --log v2/evidence/run_f6_off_n16r60_seed42/run.jsonl \
  --meta v2/evidence/run_f6_off_n16r60_seed42/meta.json \
  --out-json v2/evidence/r1_f6_off_metrics.json --out-md v2/evidence/r1_f6_off_metrics.md
cd code && python3 -m obs llm-cost --log ../v2/evidence/run_f6_on_n16r60_seed42/run.jsonl --require-provider openai_compat
```

## 4. OFF 臂"提示词逐字节不变"怎么证明（单变量三查第 1 查）

- 查 1（代码）：`git diff 895b9a3..HEAD -- code config` 为空 ⇒ 两臂同一份代码。
- 查 2（分支行为）：`memory_f6_enabled()` 只在 env ∈ {1,true,yes,on} 时为真；OFF 时 `_memory_line()` 返回空串，`ctx.memory_refs` 键不出现。
- 查 3（日志）：OFF 臂 510 条 MSG 里 `ctx.memory_refs` 出现 0 次（脚本统计见 §2 表"次指标"行）。
