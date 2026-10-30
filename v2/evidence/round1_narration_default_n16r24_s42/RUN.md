# ROUND1 旁白通道默认化 · 验证批（n16 r24 seed42）

目的：验证 `LIFE_PROMPT_NARRATION` **不设**时，旁白/动作神态通道**默认生效**（默认值来自
`code/config/life_v2.json :: prompt.narration.enabled=true`）。本批**未设**该 env；设了 env 就是重复 D9i。

## 起跑

```bash
# cwd = 仓库根；分支 feat/narration-default-on，头 = 8253637
pgrep -af "orchestration|run_batch|launch_arm"   # 空（串行复检）
setsid bash -c 'env -u LIFE_PROMPT_NARRATION HITT_WORLD_SEED=42 \
  bash tools/d2/run_batch.sh --out-dir v2/evidence/round1_narration_default_n16r24_s42 \
  --seed 42 --agents 16 --rounds 24 --side-root /tmp/round1_nd_s42' 
# EXIT=0
```

preflight（`tools/d5/preflight.sh --tag run_batch`）：
`PASS sha=82536377(feat/narration-default-on) concurrency=0 frozen_tree=clean`

## 跑批读数（meta.json）

| 项 | 值 |
|---|---|
| events / wc -l | 33845 / 33845（自检一致）|
| llm_calls | 2252，provider 全部 `openai_compat`（无 mock 混入）|
| seed / n / rounds | 42 / 16 / 24（`rounds_effective=24`）|
| duration | 1562 s（14:30:31 → 14:56:33）|
| started_at | 2026-10-30T14:30:31+08:00 |

## 真跑门禁（`obs llm-cost --require-provider openai_compat`，本目录 run.jsonl）

`rc=0`，`provider_guard.ok=true`，`problems=[]`，`by_provider={"openai_compat":2252}`，
`dialogue calls=191 cached=0`。

## 通道生效读数（`tools/d9i/narration_stats.py`，与 D9i 同一口径）

见同目录 `narration_stats.json`：

- 成对括号口径（主判）：**175/191 = 91.6%**，括号块 205 个，
  其中动作/神态类 **144/205 = 70.2%**。
- 任意括号口径（辅助）：175/191 = 91.6%。
- 参照：D9i 显式 `LIFE_PROMPT_NARRATION=1` 臂为 179/191 = 93.7%、动作神态类 147/205 = 71.7%。
  ⇒ 两批同量级（分母同为 191 条 MSG）；默认化后**未设 env 也能拿到 D9i ON 的量级**。

## 抽样件（`narration_samples.md`，40 条人工读样本）

由 `tools/round1/export_narration_samples.py` 确定性导出（口径复用 `tools/d9i/narration_stats.py` 的 `PAIRED_RE`）：
25 条旁白/动作神态 + 15 条纯台词，每条带 `actor / R{round} / seq / thread_id / turn_index / msg_uid`。

> **抽样局限**：抽样为确定性顺序取前 N（按 `msg_uid` 序、`body` 首次出现去重），**非分层抽样**，
> 故样本偏向靠前轮次与靠前出场角色；结论只作定性阅读材料，**不作分布推断**。

`msg_uid` 唯一性实测：**`len(set)=191` == `len=191`**（全批无碰撞；`body` 亦 191/191 全不同，
本批去重未删任何一条）⇒ 「按 uid 排序 + body 去重」等价于「按发言顺序取前 N」，无同毫秒撞 uid 误删风险。

## 复算

```bash
PYTHONPATH=code python3 tools/d9i/narration_stats.py \
  --log v2/evidence/round1_narration_default_n16r24_s42/run.jsonl \
  --arm ON --out v2/evidence/round1_narration_default_n16r24_s42/narration_stats.json
cd code && python3 -m obs llm-cost --log ../v2/evidence/round1_narration_default_n16r24_s42/run.jsonl \
  --require-provider openai_compat; echo rc=$?
```

注：`run.jsonl`（17 MB）被 `.gitignore` 的 `**/*.jsonl` 排除，故只提交 `meta.json` +
`narration_stats.json` 与本说明；run.jsonl 留在工作树同路径，可按上面命令复算。
