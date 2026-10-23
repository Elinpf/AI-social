# `v2/evidence/d22_partner_choice/` — CYCLE-15 证据包

> 任务：`ev-cycle15`（CYCLE-15 取数与复算）。本目录于 **2026-10-24** 新建，承载 D2.2 对端选择诊断、关键读数重算、§4 素材溯源与 commit 区间登记。
> **纪律**：只读优先；不起新跑批（本周期 LLM 成本 = 0）；不改 `code/` 冻结区；不改任何既有历史证据件字节；本目录所有 `--out` 均指向本目录，**未覆盖任何被核件**。

## 0. 目录内文件清单

| 文件 | 内容 | 类型 |
|---|---|---|
| `cycle15_commit_window.md` | **A 项**：commit 区间（含 `4e20256` 不可达事实）+ `git status` 26 行分类 | 人读 |
| `partner_choice_d22.md` | **B 项**：D2.2 对端选择诊断（描述性读数 + 工具口径缺陷登记） | 人读 |
| `partner_choice_stats.json` | B 项出数：两臂全字段（`partner_choice_stats.py --out-json`） | 机读 |
| `permtest_D12-I.json` | B 项置换检验（B=2000, seed=42），D12-I 臂 | 机读 |
| `permtest_T0.json` | B 项置换检验，T0 基线臂 | 机读 |
| `readings_recompute_cycle15.md` | **C 项**：F-1 / L-3 / addr_head 双口径 / L-7 双口径 / llm-cost 与 CYCLE-14 对照表 | 人读 |
| `f1_recompute_cycle15.json` | C 项 F-1 三臂重算（`f1_recompute.py --out-json`） | 机读 |
| `form_metrics_D12-I_cycle15.json` | C 项形态读数重算（L-3 / addr_head 全族 / L-7 norm8） | 机读 |
| `dup_calibers_D12-I_cycle15.json` | C 项重复度三口径 + raw8（L-7 双口径并列） | 机读 |
| `llm_cost_cycle15.txt` / `.rc` / `.stderr.txt` | C 项成本重跑原始输出（rc + JSON 单行） | 机读 |
| `dialogue_excerpts.md` | **D-1**：D12-I ≥3 段多轮真实对话原文（逐字 + seq + 行 sha） | 人读 |
| `shots_provenance.md` | **D-2**：4 张 CYCLE-14 已入库截图的 sha 与自洽性核验 | 人读 |
| `SHA256SUMS` | 本目录全部文件的 sha256（**不含自身**） | 校验 |

## 1. 一键复算（在主 checkout 仓库根执行，约 1–3 分钟）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment

# A) commit 区间 + 工作树
git rev-parse HEAD
git log --format='%h %cI %s' 4e20256..HEAD
git merge-base --is-ancestor 4e20256 HEAD; echo "rc=$?"   # 期望 rc=1（4e20256 非祖先）
git for-each-ref --contains 4e20256 --format='%(refname)' # 期望空
git status --porcelain | wc -l

# B) D2.2 对端选择（两臂）
python3 tools/d21/partner_choice_stats.py \
  --log "D12-I=.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl" \
  --log "T0=v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl" \
  --out-json v2/evidence/d22_partner_choice/partner_choice_stats.json

python3 tools/d21/partner_choice_permtest.py --B 2000 --seed 42 \
  --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --out-json v2/evidence/d22_partner_choice/permtest_D12-I.json
python3 tools/d21/partner_choice_permtest.py --B 2000 --seed 42 \
  --log v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl \
  --out-json v2/evidence/d22_partner_choice/permtest_T0.json

# C) 关键读数重算
python3 v2/evidence/life_texture_cycle14/f1_recompute.py \
  --arm D12-I=.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --arm T5=.worktrees/d12g-diverse2/v2/evidence/run_d12g_diverse2_n16r60_seed42/run.jsonl \
  --arm D12-H=.worktrees/d12h-pairing/v2/evidence/run_d12h_pairing_n16r60_seed42/run.jsonl \
  --out-json v2/evidence/d22_partner_choice/f1_recompute_cycle15.json

python3 tools/metrics/form_metrics.py \
  --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --code-dir .worktrees/d12i-aligned/code \
  --out v2/evidence/d22_partner_choice/form_metrics_D12-I_cycle15.json \
  --batch-id D12-I --no-timestamp

python3 tools/metrics/d12i_dup_calibers.py \
  --log .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
  --out v2/evidence/d22_partner_choice/dup_calibers_D12-I_cycle15.json

( cd code && python3 -m obs llm-cost \
    --log ../.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl \
    --require-provider openai_compat ) > v2/evidence/d22_partner_choice/llm_cost_cycle15.txt
echo "rc=$?"

# D) 素材溯源
for s in 77 581 2154 3025 5080 5743 148 994 2244 3882 5190 6480 225 730 2362 3386 5279 6091; do
  grep -c "\"seq\":$s," .worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl
done
( cd v2/evidence/d12i_readings_20261024 && sha256sum -c SHA256SUMS )

# E) 本目录自校验
( cd v2/evidence/d22_partner_choice && sha256sum -c SHA256SUMS )
```

## 2. 输入指纹（复算前置）

| 日志 | sha256 |
|---|---|
| D12-I `run.jsonl` | `72c0ca97fe6e38632f67e3b2810c65126c0d15d296d068b521dfbb45c8f5d0c4` |
| T5 `run.jsonl` | `dd4ad73d5a21c7485c2afbfc9701e267c25da3150b10adade3b3819a3996ff36` |
| D12-H `run.jsonl` | `122b36e988267a396cfdd95b167bad92bf69beabc249c253b46555f2679c3207` |
| T0 `run.jsonl` | `3c814121b5f8d4b053358c959c926f4e14b8a57bf2c6206dadc94d6695c81a74` |

> `run.jsonl` 受 `.gitignore:8 **/*.jsonl` 约束**不入库**（仓规）⇒ **master 上可做 = 验 sha + 按本文件命令复算；不可做 = 从零重建日志**（沿用 CYCLE-14 `N-7`/`Q-17` 总则）。

## 3. 五条结论摘要（详见各分件）

1. **A**：区间起点 `4e20256` **在 master 上不可达**（游离 commit，等价于 `d0a320b` 起点）；区间内 4 条 commit 全部是 CYCLE-14 交付物的入库/回填/复验补记 ⇒ **本周期已入库 commit = 0**；工作树 26 行 = 1 `M`（历史脏项）+ 25 `??`（22 历史 + **4 本周期新增**）。
2. **B**：D12-I 与 T0 的 114 条发起序列**逐位相同** ⇒ 对端选择对 D12-I 干预**零位移**，两臂之差 `不可判`；共同结构在「池取 n−1」的上界假设下偏离 iid 均匀（`p=0.0000`），属**描述性读数**，非效果结论。
3. **C**：5 组 / 12 个数值项与 CYCLE-14 **全部一致**，无漂移；`llm_cost.txt` 与入库件**逐字节相同**。
4. **D-1**：3 段多轮真实对话原文（各 6 轮），seq 全部可 grep 命中，逐行 sha256 已给。
5. **D-2**：4 张 PNG 为 **CYCLE-14 已入库图**（非本周期新渲染），`SHA256SUMS` 18/18 OK，三件（日志/中间件/渲染报告）sha 自洽。

## 4. 边界与未处置项

- 工具未入库：`tools/d21/partner_choice_stats.py`、`partner_choice_permtest.py`、`partner_choice_permtest_conditional.py` 仍为 `??`；本轮**只诊断不改造**，其 5 条口径缺陷已原样登记于 `partner_choice_d22.md §B.5`。
- 团队共享工作空间 `artifacts/docs/` 下 CYCLE-14 时代的 `cycle14-issue-register.md`、`cycle14-state-brief.md` **原件已不可得**（2026-10-24 04:30 重建过），只能引 `reports/CYCLE-14-20261024.md` 正文抄录版；已在交接摘要中登记。
- 本目录**不含**任何 PNG / 不含任何 `run.jsonl` 副本（避免副本冒充实物）。
