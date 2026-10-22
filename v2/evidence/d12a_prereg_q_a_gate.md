# 预登记 · D12-A 问题 (a)：「禁旁白」的代价能否用**插槽**补回来（同树开/关两臂）

| 项 | 值 |
|---|---|
| **预登记时间** | **2026-10-22T21:28+08:00**（早于起跑；**今夜不跑，明早执行**） |
| 首次提交 sha | 见文末锚点 |
| 树 | **`feat/d12-detail`（基于 `80b2b4c`，提示词含 `A1-措辞` 禁旁白）**，代码 `a6ae5e5` |
| 两臂 | 同树、同 seed、同窗口：**OFF**（`HITT_D12_DETAIL` 不设）vs **ON**（`=1`），均**新跑** |
| 窗口 | `seed=7`、`n=16 × rounds=24` |
| provider | 真 LLM `openai_compat` |

## 0. 要回答的问题（与 (b) 区分开）

- **(a)（本轮）**：树里**已经禁了旁白**，此时**加插槽**能否把 D4/A1-措辞 的代价（长度 ↓、具体性 ↓）补回来？
- (b)（**本轮不做**）：无禁的中性树（`3ec85a0`）上，只给替代路径、不禁止，旁白会不会自己消失？——学术上更漂亮，优先级低。

## 1. 按树现算的期望值（本轮自检基准）

| 指标 | 该树（含禁旁白）的期望 | 依据 |
|---|---|---|
| body 括号旁白率 | **两臂都 ≈0%** | `master:code/life/agent.py:1375` 已写死"不要用括号/方括号/星号写动作、神态或心理旁白" |
| 具体性（D4 `DETAIL_WORDS` 粗代理，注明实现） | 基线≈95%（seed7 关臂实测 183/191=95.81%） | 同树基线实测 |
| `len_p50` | 基线实测 **41**（seed7 关臂） | 同树基线实测 |
| 结构（MSG/线程/≥3 轮） | 两臂差 ≤±5% | 结构不受提示词影响（mock 已证同结构） |

**起跑后自检（硬闸）**：起跑 60 秒内读**前 20 条** body：
- 两臂旁白率必须 **≤5%**；**若 OFF 臂 >5% ⇒ 说明树被改过（或开关没关）⇒ 立即停跑**；
- `printenv HITT_D12_DETAIL` 真值两个臂都要落进 `switch_proof`（**不用字面量**）。

## 2. 判据（三项，写死）

| 判定 | 条件（全部满足） |
|---|---|
| **插槽有效（把代价补回来）** | 具体性使用率 **ON − OFF ≥ +3pp**；**且** `len_p50(ON) ≥ len_p50(OFF) × 1.0`（不掉）；**且** 结构三项差 ≤±5% |
| **插槽无效** | `len_p50(OFF) ≥ len_p50(ON) × 0.9` **且** 具体性无提升（Δ < +3pp） |
| **插槽有害** | `len_p50(ON) < len_p50(OFF) × 0.9` 或 结构差 >±5% |

> 旁白率**不参与判据**（该树两臂都应 ≈0%，无区分度）——这一条要写进结论，避免后人拿它当效果。

## 3. 附带记录（不参与判据）

- 具体性（分子/分母）、`len_p50`、`len_mean`；
- `≥3 轮` 绝对条数 / 单发占比 / 线程数 / MSG；
- `switch_proof`：`code_sha=a6ae5e5`、`printenv` 真值、`prompt_fn_sha256`、`detail_line_len_on=55`。

## 4. 边界

- 仍然**不写"更自然"**（无 judge / 无人工抽检）；
- 单 seed（7）两臂；若 ON−OFF 的 Δ 落在噪声带内，结论只写"未见提升"；
- 若 ON 臂被中断，**作废重跑**，不使用 `--resume-from`（等价性无预算证明）。

## 5. 复现命令（明早执行）

```bash
WT=<repo>/.worktrees/d12-detail
cd $WT/code && set -a && . <repo>/code/.env.local && set +a
export HITT_LLM_PROVIDER=openai_compat
# OFF 臂（显式 env -u，杜绝残留）
env -u HITT_D12_DETAIL python3 $WT/tools/t271/run_override.py --seed 7 --agents 16 --rounds 24 \
  --out <repo>/v2/evidence/run_d12a_q_a_off_seed7_n16r24/run.jsonl --side-root /tmp/d12a_qa_off_side --flush-every 2
# ON 臂
HITT_D12_DETAIL=1 python3 $WT/tools/t271/run_override.py --seed 7 --agents 16 --rounds 24 \
  --out <repo>/v2/evidence/run_d12a_q_a_on_seed7_n16r24/run.jsonl --side-root /tmp/d12a_qa_on_side --flush-every 2
```

## 锚点

- 本文件**首次提交**即预登记锚点；两臂起跑必须晚于此提交。
