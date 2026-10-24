# p2-companion-gap-ad71801 · 本轮（CYCLE-19）证据包

维度：**P2「计划同伴 ≠ 实际同处」**（复算 + 归因 + 改法设计）。零跑批、零 LLM、只读。

- **目录名 `ad71801`** = 本轮**分析所依据的代码 sha**（提交前 `git rev-parse HEAD` = `ad7180168c9abe59a4268115e95f936e4395b71b`）。
- 本轮**交付 commit** 是该 sha 的下一笔提交，取法：`git log -1 --format=%H -- reports/CYCLE-19-20261024.md`。两者不同属正常，不得混读。
- 报告正文：`reports/CYCLE-19-20261024.md`

## 文件

| 文件 | 说明 |
|---|---|
| `p2_f3off_n16r60_seed42.json` | 主批读数（`tools/p2/plan_actual_consistency.py` 原样输出） |
| `p2_r10e2e_n16r60_seed42.json` | 副批读数（第二个独立 run，同尺子） |
| `p2_gap_crosstab_f3off.json` | 归因交叉表 + 门跳过机制 61/61 核验（`tools/p2/p2_gap_crosstab.py`） |
| `p2_extra_facts.json` | 横切读数：对端有无 `template`、对端自身并行度梯度 |
| `cmd_*.txt` | 每条命令的实测 stdout（原样留档，未编辑；落为 `.txt` 因 `.gitignore:63 **/*.log`） |
| `CYCLE-19-rhythm-f20f6822.png` | 本轮现场渲染的真实新截图（节律/落点视图） |
| `threads_CYCLE-19.json` | 截图派生件（`gen_threads.py` 现算） |
| `render_report_CYCLE-19.json` | 截图三件套 + 像素自检 |

## 复现（全部零 LLM、零跑批）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 tools/p2/plan_actual_consistency.py --run v2/evidence/run_f3_off_n16r60_seed42/run.jsonl \
  --out /tmp/p2_f3off.json --secondary-run v2/evidence/run_f4_on_n16r60_seed42/run.jsonl --stable
# 期望：primary consistency 74/218 = 0.3394 | gaps 144
python3 tools/p2/p2_gap_crosstab.py --run v2/evidence/run_f3_off_n16r60_seed42/run.jsonl --out /tmp/ct.json
# 期望：gaps 144 / gate_skip 机制核验 61/61 命中, 无template 61/61
```

## 边界

- 页面截图**不展示** `ACTIVITY_STARTED.payload.participants`，因此**不能**证明一致率 `74/218`；判据以数值证据为准。
- 输入 run 均为**已收批**的既有 run；本轮**未**新起任何批次、**未**启停既有批次、**未**改 `code/{life,orchestration,config,engine}` 任何文件。
