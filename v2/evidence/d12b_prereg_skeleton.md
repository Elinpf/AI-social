# 预登记骨架 · **D12-B「偏好驱动选词」**（中性树，冻结代理判据）

| 项 | 值 |
|---|---|
| **预登记时间** | **2026-10-23T00:26+08:00**（**早于任何代码改动与起跑**；今夜只登记不跑） |
| 首次提交 sha | 见文末锚点 |
| 状态 | **骨架已落，等 Leader 点头后再改码/起跑** |
| provider | 真 LLM `openai_compat` |

## 1. 逐字提示词 diff（唯一改动，一条一句，不删改任何既有行）

在 `_dialogue_prompt` / `_reply_prompt` 的收尾指令处**追加一行**（逐字取自 `v2/refs/D12-L7-dedup-round3-prereg.md` §2 臂 D12-B）：

```diff
+ "\n先从你自己那点脾气/习惯里挑一个词起头（你这个人平时爱怎么说就怎么说），"
+ "别用别人也爱用的那种开场。"
```

- 只**引用已有 persona 字段的语义**（`background` / `speech_style.tone`），**不新增字段、不改结构、不动配额**；
- 实现须带开关（建议 `HITT_D12_PREFWORD=1`，**默认关**），关闭时与基线逐字一致。

## 2. 树与两臂

| 项 | 值 |
|---|---|
| 树 | **中性树 `3ec85a0`**（无"禁旁白"；基线旁白 78.01%、具体性 87.43% ⇒ **避开 95%+ 天花板**） |
| 两臂 | **OFF**（`env -u HITT_D12_PREFWORD`）vs **ON**（`HITT_D12_PREFWORD=1`），**均新跑**、同树 |
| 规模 | `seed=7`、`n=16 × rounds=24`、真 LLM |
| 托管 | `systemd-run --collect --property=EnvironmentFile=<主树>/code/.env.local --working-directory=<worktree>/code`（runbook §4.5 已验证） |

## 3. 判据（三项，写死）

| 判定 | 条件（全部满足） |
|---|---|
| **有效** | 具体性 **ON − OFF ≥ +3pp**（**冻结实现 `tools/d9/detail_proxy.py`，`impl_sha256=335cb48cb6675a252e5a421dd0746caa2e5b274f3856afe2cb088531839fc8b9`**）**且** `len_p50(ON) ≥ len_p50(OFF) × 0.90`（不降 >10%）**且** 结构三项（MSG/线程/≥3 轮）差 ≤±5% |
| **无效** | 具体性 Δ < +3pp 或 `len_p50` 降 >10% 或 结构差 >±5% |
| **机制未生效（闸）** | 附带的"句首 4 字按 agent 的经验熵 H" **相对 OFF 未升 ≥10%** ⇒ 判**机制未生效**（模型没按自己的脾气起句），**不得判"无效"** |

> 补充（来自 D12 原预登记的对称闸）：B 臂的**机制闸是"句首熵 H ↑≥10%"**，与 A 臂的"插槽使用率"对称；
> H 的计算实现也须**冻结唯一版**（写进本预登记定稿时补 `impl_sha256`）。

## 4. 起跑 60 秒硬闸（FAIL 即停）

```bash
python3 tools/d9/arm_state_check.py --run <arm>/run.jsonl \
  --tree-expectation '{"paren_rate":0.78,"len_p50":47}' \
  --expect-struct '{"msgs":191,"threads":66,"ge3":28}' \
  --expect-provider openai_compat
```
- 依据 `v2/evidence/neutral_tree_expectation.md`（`3ec85a0` 的 A0 前缀 `round≤23` 实测）；
- **OFF 臂 `paren_rate` 若 ≈0（而非 ≈0.78）⇒ 跑错树 ⇒ 立即停跑**（这是 2026-10-22 D12-A 事故的硬闸）；
- 两臂都必须先过这道闸，再让其继续跑。

## 5. 边界

- **不写"更自然"**：judge `naturalness` 不可用；`persona_fit` 若要引用必须注明 judge 口径与天花板风险；
- **单 seed（7）**；`ON` 臂被中断 ⇒ **作废重跑**，不使用 `--resume-from`；
- 若机制未生效（句首熵未升）⇒ 结论是"机制未生效"，**不是"无效"**（两者含义不同）。

## 6. 待定稿项（明早 Leader 点头后补齐，缺一不许起跑）

1. `HITT_D12_PREFWORD` 的**实际代码 diff**（15 行内，只加不减）与 `prompt_fn_sha256`；
2. **句首熵实现冻结**（函数 + `impl_sha256`），与具体性代理同等对待（runbook §3.97）；
3. 两臂的 `switch_proof`（`printenv` 真值）与 `arm_state_check.txt` 落盘位置。

## 锚点

- 本文件**首次提交**即预登记锚点；改码与起跑必须晚于此提交。
