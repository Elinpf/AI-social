# D4 · mock 条数预校准（n=16 × rounds=84）：实测 190 条

> 作者：`prompt-linguist` ｜ 日期：2026-10-20 ｜ 类型：零成本预校准（**mock，无 LLM**）
> 目的：leader 批准的执行方案第 1 步——先用 mock 确认「n=16×84 能否产出 ≥150 条 MSG」，再花钱跑真 LLM。
> 结论：**能。实测 190 条（DM 129 + PUBLIC 54 + GROUP 7），DM+PUBLIC = 183 ≥ 150 ✅**

---

## 1. 运行事实

| 项 | 值 |
|---|---|
| 命令 | `cd code && env -u HITT_LLM_PROVIDER python3 -m orchestration run --life --seed 42 --agents 16 --weeks 1 --rounds 84 --out /tmp/d4_mock_calib/run.jsonl --side-root /tmp/d4_mock_calib/side --flush-every 84` |
| provider | **mock**（`env -u HITT_LLM_PROVIDER` ⇒ MockProvider；`llm_calls` 不计真钱） |
| 代码树 | `0dfb36619d075f9c19e30e258371b9451f063af0`（运行时刻 HEAD；**D2 改造进行中，故只作条数校准，不作结构证据**） |
| 耗时 | **96.2 秒**（`events=186057`，`log_bytes=87032695`） |
| 自检 | `chain_ok=True`、`replay_parity=True`、`first_run_equals_replay=True`、`conservation_ok=True`、`unknown_event_types=[]` |
| `final_state_hash` | `sha256:24320c4dfbed5847b2fc858a76e88e36cc869f48ed155262f6c1918bad311e91` |
| run.jsonl sha256 | `252db450c76f78d114cd4f488342c72e315eb1435f09293204cc2d615e5086bd` |
| 事件数 / 行数 | 186057 |

## 2. 结果

| 指标 | 实测 | 事前预测（`MSG ≈ 0.14×n×rounds`） |
|---|---|---|
| MSG_DM | **129** | — |
| MSG_PUBLIC | **54** | — |
| MSG_GROUP | **7** | — |
| **MSG 合计** | **190** | 0.14×16×84 = **188.1**（误差 +1.9，+1.0%） |
| DM+PUBLIC（leader 门槛口径） | **183** | 门槛 ≥150 ✅ |

⇒ 换算率在本批实测为 `190/(16×84) = 0.1414`，落在既有区间 **0.137–0.167** 内（t300 0.137 / t326 0.143 / t350 0.167）。

## 3. 附带读数（**仅参考，不作证据**）

- 结构（legacy 口径）：`n_threads=129`、`msgs_per_thread p50=1`、`single_msg_thread_ratio=84.5%`、`multi_turn_thread_ratio=6.2%`、`turns_A p50=1 / p90=2`。
- 正文：mock 正文是固定模板（`life/llm.py:74-76`，如「最近雨水多，出门带把伞。」），p50 长度 14 字 ⇒ **措辞类指标在 mock 下无意义**（这是既有事实，不新结论）。
- 与 t300（20×84，真 LLM）结构粗比：single_msg 84.5% vs 87.65%、multi_turn 6.2% vs 4.94% —— **规模不同（16 vs 20），按 R-EX1 不作证据**，只说明"当前结构下 mock 与真 LLM 不像是两套结构"。

## 4. 复算命令

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code
env -u HITT_LLM_PROVIDER python3 -m orchestration run --life --seed 42 --agents 16 --weeks 1 \
  --rounds 84 --out /tmp/d4_mock_calib/run.jsonl --side-root /tmp/d4_mock_calib/side --flush-every 84
python3 - <<'PY'
import json, collections
c = collections.Counter()
for line in open('/tmp/d4_mock_calib/run.jsonl'):
    e = json.loads(line)
    if e.get('type') in ('MSG_DM', 'MSG_PUBLIC', 'MSG_GROUP'):
        c[e['type']] += 1
print(dict(c), sum(c.values()))     # 期望 {'MSG_DM':129,'MSG_PUBLIC':54,'MSG_GROUP':7} 190
PY
```

## 5. 边界

- 本批**不作 D4 对照臂**，只校准条数；mock 能否支撑结构结论，仍须按 `D4-事前登记.md §1` 的 mock-vs-real 对拍（PASS 才授权）。
- 树 `0dfb3661` 是 D2 改造进行中的中间态；D2 最终 commit 落定后，**正式两臂与对拍都会重跑**（mock 零成本，真 LLM 一次性）。
- 未触碰冻结区：本批只读世界、只写 `/tmp`，不写项目目录、不改任何源码。
