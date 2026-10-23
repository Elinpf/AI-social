# F-2b B.4-v2 放量复验 · 判定侧预置件（四个守卫的取数与基线来源）

> 作者：life-spearman｜写于 off 臂跑批期间（未触碰 worktree 内 `code/` 任何文件；本文件与脚本均在 `v2/evidence/f2b_v2_n16r60_seed42/`，不在冻结区）
> 目的：on 臂一收批即可出判定，不在跑完后才发现「某守卫算不出」。

## 1. 取数命令（单一真源，全部只读）

四个守卫全部来自 `tools/d5/dialogue_metrics.py` 的同一份 JSON（R19 用法一致）：

```bash
cd <repo>
python3 tools/d5/dialogue_metrics.py --log v2/evidence/f2b_v2_n16r60_seed42/run_off/run.jsonl --out-json /tmp/f2b_off_metrics.json
python3 tools/d5/dialogue_metrics.py --log v2/evidence/f2b_v2_n16r60_seed42/run_on/run.jsonl  --out-json /tmp/f2b_on_metrics.json
python3 -c "import json;d=json.load(open('/tmp/f2b_on_metrics.json'));print(d['L_wording']['L-6_dup_exact_rate'],d['L_wording']['L-5_template_hit_rate'],d['L_wording']['L-7_dup_ngram8_rate'],d['F-1_chatter']['nonfunctional_chatter_rate'])"
```

| 守卫 | JSON 字段 | 口径 |
|---|---|---|
| L-6 重复（逐字） | `L_wording.L-6_dup_exact_rate` = `(n_msg - uniq)/n_msg` | `dialogue_metrics.py:995` |
| L-5 模板命中 | `L_wording.L-5_template_hit_rate` | `dialogue_metrics.py:992` |
| L-7 重复（ngram8） | `L_wording.L-7_dup_ngram8_rate` | `dialogue_metrics.py:996` |
| F-1 非功能性闲聊率 | `F-1_chatter.nonfunctional_chatter_rate` = `(n_msg - func)/n_msg` | `dialogue_metrics.py:1057` |

聚合入口（本批判定件就是它产出）：`v2/evidence/f2b_v2_n16r60_seed42/f2b_v2_summary.py`，守卫在 `verdict.json → guards`。

## 2. 每个守卫「本批用的是哪条基线」——必须先说清

| 守卫 | 本批判定基线 | 为什么不用历史绝对带 |
|---|---|---|
| L-6 | **同批 off 臂**（同 commit / 同 seed / 同 n16r60，唯一差异是开关）；击穿判据：`on > off`（预登记 §4） | 历史绝对带横跨不同代码与规模：D12-D T1 = 9.61%（`v2/refs/D12D-prereg-dedup-on-detail.md:50`）、D12-E = 0.78%（`v2/refs/D12F-prereg-candidate-diversity.md:59`，best-of-3 之后量级完全不同）。**跨代码比绝对带＝错误对照**，只能并列登记、不参与判定 |
| L-5 | 同上（同批 off 臂） | 历史参考值 D8 v0 = 10.87%（`v2/refs/D8-dialogue-study-report.md:55`）是轮次/规模都不同的 v0 批；并列登记，不判定 |
| L-7 | 同上（同批 off 臂） | R19 两臂为 0.2577 → 0.1856（`reports/README.md:26`），但那是 n8r24 + best-of 之前的代码；并列登记，不判定 |
| F-1 | 同上（同批 off 臂） | R19 两臂均 0.628866（同上）；并列登记，不判定 |

**结论（提前说清，避免最后才报缺口）**：四个守卫在本批**都能算**，前提是 **off 臂必须跑完**（这也是 Leader 选 A 方案的直接后果）；若 off 臂异常中断，四个守卫按「未测 ⇒ 不可判」处理，主判定随之降为不可判。

**已知的一处口径限制（披露）**：R19 报告里 L-7 出现过两种写法——`L-7_dup_ngram8_rate`（本批用，`dialogue_metrics.py` 口径）与 D12-E 的 `L-7 norm8`（55.88 vs 门槛 ≤55.10，另一种归一化）。**本批只用 `L-7_dup_ngram8_rate`**，不与 `norm8` 数字化较；若下游要 norm8，需要另一条实现路径，本批不提供。

## 3. dry-run 记录（用历史日志先跑一遍，证明命令能出数）

| # | dry-run | 命令 | 结果 |
|---|---|---|---|
| 1 | 双臂读数 + 抽样（用 R19 n8r24 两臂） | `python3 f2b_v2_summary.py --off v2/evidence/r19_topicbreadth_n8r24_seed42/run_off --on v2/evidence/r19_topicbreadth_n8r24_seed42/run_on --out dryrun/r19_selftest_summary.json --sample dryrun/r19_selftest_sample.md --sample-json dryrun/r19_selftest_sample.json` | **rc=0**，且**与 R19 报告逐项对上**：`landed_events=10`、`tag_added=10`/`tag_replaced=0`、相邻对 67、`F-2b 7/30`、`L-7=0.185567`、`L-5=L-6=0.0`、`F-1=0.628866`；抽样规则判 **N=10 < 30 ⇒ 样本不足**（正是预登记 D-1 的预期行为）。产物：`v2/evidence/f2b_v2_n16r60_seed42/dryrun/r19_selftest_summary.json` |
| 2 | 抽样规则自测（不依赖日志） | `python3` 直接 import 模块，对 N=10/29/30/31/47/50/100/247 合成序列跑 `pick_sample` | **rc=0**：N<30 ⇒ 抽 0 条并报「样本不足」；N≥30 ⇒ 恒抽 30 条、seq 升序、`step=N//30`。产物：`dryrun/sample_rule_selftest.txt` |

**由 dry-run 得到的额外披露**：当 `30 ≤ N < 60` 时 `step=N//30=1`，抽到的是 **seq 最小的前 30 条**（R19 同款规则的固有性质，不是本批改动）⇒ 若本批 landed 落在 30–59 区间，判定样本会有**早期轮次偏置**，判定件必须并列写明；不改规则（规则已预登记写死）。
