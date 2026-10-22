# D12-C OFF 臂 · Leader 独立臂状态核验（**跑批中快照**）

> 目的：按「对照臂必须证明它处在对照状态」纪律，**由 Leader 独立跑一次** `tools/d9/arm_state_check.py`，不依赖执行者的自报。
> 本文件是**运行中快照**，`n` 与 `seals` 会继续增长；**终态核验以跑完后的 `arm_state_check.txt` 为准**，本文件只回答一个问题：**这一臂是不是跑在中性树上、是不是真 LLM。**

## 1. 快照身份

| 项 | 值 |
|---|---|
| run | `v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl` |
| unit | `t271-d12c-off.service`，cgroup = **`/system.slice/t271-d12c-off.service`**（不在 `jiuwenswarm.service` 内，平台重启不连坐） |
| code | 分支 `feat/d12c-specific` @ **`a977cb0`**（parent `3ec85a0`），工作副本 `/tmp/t271-d12c-br/code` |
| 开关 | `tr '\0' '\n' < /proc/2862341/environ | grep LIFE_PROMPT_D12C` ⇒ **无输出**（OFF 期望值 ✅） |
| `prompt_fn_sha256` | **`5cf08593d562dc09…`**（与接线证明 §1 的 OFF 值**逐字相等**）——这是「OFF 臂真的是 OFF」的**执行层证据**，不是配置文件声明 |
| 快照命令与时刻 | `arm_state_check.py --tree-expectation '{"paren_rate":0.78,"len_p50":47}' --expect-provider openai_compat`，2026-10-23 06:26 前后 |

## 2. 结果（原样转录）

```
[PASS          ] 解析完整性      坏行=0，记录=58746
[PASS          ] 样本量          前20条=20；全 run 318 条（scope=full）
[PASS          ] C0 provider     期望 {openai_compat}；实测={'openai_compat': 2476}
[FAIL          ] C1 指标(scope=full)  paren_rate=0.8176 期望0.78 ok；len_p50=53.0000 期望47 FAIL
                  参考 全run: {paren_rate:0.8176, len_p50:53.0, len_p50_excl:41.0,
                             id_leak_rate:0.0, dup_exact_rate:0.0723}
[PASS          ] C2 seals/初始化   seals=38 覆盖=0..37；WORLD_INIT=1；问题=无
[CANNOT-VERIFY ] C4 结构          未给 --expect-struct（实测 msgs=318 / threads=111 / ge3=43）
[汇总] PASS=5 FAIL=1 CANNOT-VERIFY=1
```

## 3. 这 1 个 FAIL 是什么、不是什么

**是**：**期望值跨规模误用**。我喂的 `len_p50=47` 来自 `neutral_tree_expectation.md`，那份期望源自 **`round ≤ 23`（24 轮窗口，191 MSG）**；本批是 **60 轮**，`len_p50` 随窗口变大而抬高（当前 38 轮已 53）。按该文件自己的规则「**期望值必须与 scope 同源**」，这个 `len_p50` 期望**对本批无效**。

**不是**：跑错树。三条树身份判据全部通过：
- `paren_rate = 0.8176`（期望 ≈0.78，容差内）——**若是禁旁白树会是 ≈0**（D12-A 那次事故的形态），现非 0 ⇒ 中性树身份成立；
- `id_leak_rate = 0.0` —— 无裸 ID 泄漏，与 A0 一致；
- `provider` 2,476 次**全 `openai_compat`**、`seals` 连续覆盖 `0..37` 无缺口。

## 4. 结论与后续

1. **OFF 臂身份判据（可放行）**：`paren_rate≈0.78` + `provider=openai_compat` + `seals` 连续 + `id_leak=0` + `LIFE_PROMPT_D12C_SPECIFIC` 在执行层不存在；
2. **`len_p50` 不比**：跨规模禁用（本条写入后续 runbook）；
3. 终态核验须补：`--expect-struct` 用**同规模**（n16×60）基线 `run_f6_off_n16r60_seed42` 现算，不得再用 24 轮期望值；
4. **观察项（不作判定）**：`dup_exact_rate = 0.0723`（7.2% 完全重复句）——与 A5 人工抽检发现的「中段复述」同源，若 ON 臂该值不降而 P1 升，则「具体物要求被写成套话」的反事实解释力增强（§10.5 ③）。
