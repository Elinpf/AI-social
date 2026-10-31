# w1-lexicon-v2 · 证据目录（天气提及率口径 v1 → v2 重算）

> 口径件：`v2/refs/W-1-lexicon-v2.md`｜读数器：`tools/metrics/weather_readings.py`
> 本轮**零 LLM、零跑批、无 sleep**，只读两份已冻结 `run.jsonl`。
> 交接说明（含全部可复算命令与结论句）：`<team-workspace>/metrics/lexicon-fix-handoff.md`

## 文件

| 文件 | 内容 | 生成方式 |
|---|---|---|
| `readings_off.json` | OFF 臂（CYCLE-42 冻结日志）单臂读数，含 `weather_mention_strict`(v1) 与 `weather_mention_strict_v2`、逐条归因 | `weather_readings.py --arm off=$OFF` |
| `readings_on.json` | ON 臂（CYCLE-43 冻结日志，33,851 行）单臂读数 | `weather_readings.py --arm on=$ON` |
| `readings_pair.json` | 两臂 + `contrast_on_minus_off_v2`（Δ、Newcombe95、是否跨 0） | `weather_readings.py --arm off=… --arm on=…` |
| `fp-attribution.md` | 假阳性/误杀**逐条**归因表（55 条 v1 命中样本逐条判定 + 28 条被排除实例逐条复核） | `build_tables.py` |
| `hist-recompute.md` | 历史批次不回退检查（4 个旧批次 v1/v2 对照 + 排除词因由分布） | `build_tables.py` |
| `hist_*.json` | 上面 4 个历史批次的单臂读数 | `weather_readings.py --arm …` |
| `determinism.txt` | 同一日志跑两次逐字节相等的证明（含 sha256） | 手工执行并记录 |
| `build_tables.py` | 上面两份 `.md` 的唯一生成器（确定性，无外部依赖） | —— |

## 一条命令重建全部

```bash
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
OFF=/root/.jiuwenswarm/.agent_teams/jiuwen_team_cron___1a19166dd30_6c48da9fc832/team-workspace/evidence/CYCLE-42/off/run.jsonl
ON=/root/.jiuwenswarm/.agent_teams/jiuwen_team_cron___1a191d4ba2f_8d7a2fd82f04/team-workspace/round-01/evidence/on/run.jsonl
cd "$REPO"; E=v2/evidence/w1-lexicon-v2
python3 tools/metrics/weather_readings.py --arm off=$OFF --json $E/readings_off.json
python3 tools/metrics/weather_readings.py --arm on=$ON  --json $E/readings_on.json
python3 tools/metrics/weather_readings.py --arm off=$OFF --arm on=$ON --json $E/readings_pair.json
python3 tools/metrics/weather_readings.py --arm c28_off=v2/evidence/run_weather_off_n16r24_seed42_c28/run.jsonl --json $E/hist_c28_off.json
python3 tools/metrics/weather_readings.py --arm c28_on=v2/evidence/run_weather_on_n16r24_seed42_c28/run.jsonl   --json $E/hist_c28_on.json
python3 tools/metrics/weather_readings.py --arm l7struct_on_n16r60=v2/evidence/run_l7struct_on_n16r60_seed42/run.jsonl --json $E/hist_l7struct_on_n16r60.json
python3 tools/metrics/weather_readings.py --arm f3_off_n16r84=v2/evidence/cycle36_f3_off_n16r84_seed42/run.jsonl  --json $E/hist_f3_off_n16r84.json
python3 $E/build_tables.py
```

## 注意

- 两份冻结 `run.jsonl` **不在仓库内**（体积 17 MB 级），位于历轮团队的 team-workspace；
  身份一律以 `sha256` 认定（OFF `6fdaf1b7…`、ON `c572406e…`），路径见上。
- 本目录所有 `.md` 都是 `build_tables.py` 生成的，**请勿手改**——要改就改生成器或读数器再重跑。
