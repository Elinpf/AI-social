# F-5 / F-5b / F-1 跨批对照表（描述性读数，非干预臂）

> 由 `f5_build_table.py` 从 `raw/metrics_*.json` 自动生成；指标值唯一来源 `tools/d5/dialogue_metrics.py` 输出。

> ⚠️ 这批数据是**不同配置批落的描述性对比**，**不是** F-5 干预臂开关对照。F-5 干预臂**从未做过**（缺口已登记）。

## 表 A：5 天窗口批（口径可比，days≥3）

| 批次 | 日志 | seed | agents | rounds | 消息数 | 覆盖天数 | F-5 习惯强度（num/den） | F-5b 最大重复天数均值 | F-1 非功能性闲聊率（num/den） |
|---|---|---|---|---|---|---|---|---|---|
| `d12c_off` | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl` | 42 | 16 | 57 | 510 | 5（day 0/1/2/3/4） | 1.0（16/16） | 4.375 | 0.705882（360/510） |
| `d12c_on` | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d12c_on_n16r60_seed42/run.jsonl` | 42 | 16 | 57 | 510 | 5（day 0/1/2/3/4） | 1.0（16/16） | 4.375 | 0.698039（356/510） |
| `d12d_on` | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d12d_on_n16r60_seed42/run.jsonl` | 42 | 16 | 57 | 510 | 5（day 0/1/2/3/4） | 1.0（16/16） | 4.375 | 0.690196（352/510） |

## 表 B：2 天窗口批（**窗口 <3 天 ⇒ F-5 结构性下限，不可比**）

| 批次 | 日志 | seed | agents | 消息数 | 覆盖天数 | F-5 习惯强度（num/den） | F-5b 最大重复天数均值 | F-1 非功能性闲聊率（num/den） | 准入 |
|---|---|---|---|---|---|---|---|---|---|
| `d12b_off` | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d12b_off_seed7_n16r24/run.jsonl` | 7 | 16 | 191 | 2（day 0/1） | 0.0（0/16） | 1.75 | 0.732984（140/191） | REJECTED |
| `d12b_on` | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_d12b_on_seed7_n16r24/run.jsonl` | 7 | 16 | 191 | 2（day 0/1） | 0.0（0/16） | 1.75 | 0.706806（135/191） | REJECTED |
| `scene_anchor_off` | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_scene_anchor_off_seed42_n16r24/run.jsonl` | 42 | 16 | 191 | 2（day 0/1） | 0.0（0/16） | 1.75 | 0.759162（145/191） | ADMITTED |
| `scene_anchor_on` | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/run_scene_anchor_on_seed42_n16r24/run.jsonl` | 42 | 16 | 191 | 2（day 0/1） | 0.0（0/16） | 1.75 | 0.722513（138/191） | ADMITTED |

口径说明与天花板诊断见 `README.md`。
