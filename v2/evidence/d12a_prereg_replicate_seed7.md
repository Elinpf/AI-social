# 预登记 · D12-A 复现（seed=7，防单 seed 巧合）

| 项 | 值 |
|---|---|
| **预登记时间** | **2026-10-22T20:57+08:00**（早于起跑） |
| 首次提交 sha | 见文末锚点 |
| 目的 | 检验 seed=42 的观察（旁白 →0%、长度未缩短）是否可复现 |
| 臂 | **只跑 D12-A 一臂**（`HITT_D12_DETAIL=1`） |
| 窗口 | **n=16 × rounds=24**，`seed=7` |
| 代码 | 分支 `feat/d12-detail`，commit `a6ae5e5`（worktree `.worktrees/d12-detail`） |
| provider | 真 LLM（`openai_compat`） |

## 1. 对照

| 臂 | 说明 |
|---|---|
| **Baseline（seed=7，同窗口）** | 同树、同 n/r、**`HITT_D12_DETAIL` 不设**（开关关）⇒ 与处理臂唯一差异 = 那句 55 字插槽 |
| **Treat（seed=7）** | `HITT_D12_DETAIL=1` |

> 两臂都**新跑**（不拿 seed=42 的 A0 前缀当对照）：复现检验要求 seed 一致，跨 seed 不可比。

## 2. 判据（写死，缺一即复现失败）

**复现成功**需同时满足：
1. **旁白率 ≤ 5%**（括号/方括号/星号旁白，正则 `[（(][^）)]{1,40}[）)]` 或 `[*＊]`）；
2. **长度 p50 ≥ 基线 p50 × 0.9**（不允许靠"砍短台词"换旁白归零）；
3. **结构不变**：MSG / 线程数 / `p50` 轮次 与基线一致（允许 ≤±5% 抖动）。

**若任一条不满足** ⇒ **结论降级为「单 seed 观察（seed=42）」**，不得写成"机制稳定成立"。

## 3. 附带记录（不参与判据）

- 具体物/数命中率（D4 `DETAIL_WORDS` 粗代理，注明实现口径）；
- `≥3 轮` 绝对条数与单发占比；
- `switch_proof`：`code_sha`、`env_HITT_D12_DETAIL`、`prompt_fn_sha256`、`detail_line_len_on`。

## 4. 边界

- 仍然**不写"更自然"**：没有 judge(`is_reply`) 与人工抽检；
- 只跑 A 臂；**B 臂（偏好驱动选词）待 A 的两 seed 结果出来再决定是否设计/开跑**。

## 5. 复现命令

```bash
WT=<repo>/.worktrees/d12-detail
cd $WT/code && set -a && . <repo>/code/.env.local && set +a
export HITT_LLM_PROVIDER=openai_compat
# Baseline（开关关）
unset HITT_D12_DETAIL
python3 $WT/tools/t271/run_override.py --seed 7 --agents 16 --rounds 24 \
  --out <repo>/v2/evidence/run_d12a_base_seed7_n16r24/run.jsonl --side-root /tmp/d12a_s7_base_side --flush-every 2
# Treat（开关开）
export HITT_D12_DETAIL=1
python3 $WT/tools/t271/run_override.py --seed 7 --agents 16 --rounds 24 \
  --out <repo>/v2/evidence/run_d12a_treat_seed7_n16r24/run.jsonl --side-root /tmp/d12a_s7_treat_side --flush-every 2
```

## 锚点

- 本文件**首次提交**即预登记锚点；两臂起跑必须晚于此提交。
