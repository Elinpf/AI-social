# D3 · null-pair 实测：同 seed 两批真 LLM 的台词逐条一致率（t300 vs t355）

> 作者：`prompt-linguist` ｜ 日期：2026-10-20 ｜ 类型：**方法学证据（只读、可复算）**
> 用途：给 D4「同 seed 对照」提供**噪声带**与**可比性边界**；给 D6/D8 引用"同 seed ≠ 同文本"这一局限。
> 纪律：只读 `run.jsonl`，未改任何文件、未调任何 LLM。

---

## 0. 结论（一句话）

**同 seed、同 provider、同提示词、同 n/rounds 的两批真 LLM 跑，台词逐条一致率仅 49/230 = 21.30%。**
⇒ 「同 seed 对照」**不能做逐条配对比较**，只能做**分布级**比较（比率/分位数）。

---

## 1. 两臂身份（路径 + sha256）

| 臂 | run.jsonl 绝对路径 | run.jsonl sha256 | n（MSG_*） | 树 / 指纹 |
|---|---|---|---|---|
| **t300** | `/root/t271/runs/t300/run.jsonl` | `33b7651f2b11d5eaf5720dbd0560cc2ea2a468d37f7319d972b2d7fafd808a08` | 230（DM163/PUB59/GROUP8） | world `8fb2263`；`engine_version` 指纹 `869c1953…`；记录 sha `9374c3a`；provider `openai_compat`；20×84 seed42 |
| **t355** | `/root/t271/runs/t355/run.jsonl` | `bee77237e7c2fa3a41ae7613d2ef3e4bf989c1b4f57b831fc29edc714dec3c36` | 230（DM163/PUB59/GROUP8） | sha `1d3af8c`；`engine_version` 指纹 `a871e36c…`；provider `openai_compat`；20×84 seed42 |

**交叉校验**：t300 的 log sha256 与 `v2/evidence/T300-refreeze.md` §1 记录的 `33b7651f…` **完全一致** ⇒ 本证据对的是同一份被冻基线的日志。

**两臂差异（诚实声明）**：两臂**不是同一棵树**（`8fb2263` → `1d3af8c`，其间含 `life/` 非对话改动等）。因此严格说这是「**近似 null pair**」：**提示词（`_dialogue_prompt`）未变**、seed/provider/规模完全相同，但树上有与对话措辞无关的改动。
⇒ 本证据的含义是"**即使什么都不特意改，两批台词也会大面积不同**"，属**噪声下界**（不是"零差异应然值"）。

---

## 2. 对齐与判定算法（核验方按此独立复算）

脚本：`v2/evidence/d3_null_pair.py`（sha256 见 §6）

- **A1 抽取**：按 `run.jsonl` **文件行序**（= ledger 提交顺序）读取，筛 `type ∈ {MSG_DM, MSG_PUBLIC, MSG_GROUP}`；每条取 `(seq, round, type, speaker=payload.from 或 payload.author, to, body)`。
- **A2 对齐**：**位置对齐**——第 i 条 MSG ↔ 第 i 条 MSG（**不按 seq、不按 round、不做实体对齐**）。
  **前置闸（两闸都必须 true，否则本比较作废）**：
  - `guard_n_equal`：两臂 MSG 条数相等（实测 230 = 230 ✅）
  - `guard_channel_seq_equal`：两臂 MSG 的 `type`（渠道）序列**逐位相同**（实测 ✅ 全 230 位一致）
- **A3 相等判定（主口径）**：`body` 字符串**逐字节相等**（不 `strip`、不做全半角/标点归一、不忽略大小写）。
- **A4 辅助读数（不得替代主口径）**：① `strip` 后相等 ② 去空白标点 + 小写归一后相等 ③ 同位置 `speaker` 相同 ④ 同位置 `seq` 相同。

**为什么用位置对齐而不是 seq 对齐**：两臂事件总量不同（树有无关改动），`seq` 逐条并不对齐（实测同位置 `seq` 相同仅 28/230）；而**渠道序列 + 说话人逐位一致（230/230）**，说明"第 i 条对话"在两臂里是**同一个说话人、同一渠道**，位置对齐是可核验且不引入实体匹配歧义的唯一做法。

---

## 3. 复算命令（一条）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 v2/evidence/d3_null_pair.py            # 结果同时 tee 到 v2/evidence/d3_null_pair_result.json
# 期望输出（关键字段）：
#   guard_n_equal: true, guard_channel_seq_equal: true
#   n_pairs: 230, same_body_bytes: 49, same_body_bytes_rate_pct: 21.3
#   aux_same_body_strip: 49, aux_same_body_normalized: 49
#   aux_same_speaker: 230, aux_same_seq: 28
```

---

## 4. 结果

| 读数 | 值 | 说明 |
|---|---|---|
| 配对数 `n_pairs` | **230** | 两臂 MSG 全配对 |
| **逐字节相等（主口径）** | **49 / 230 = 21.30%** | 同一说话人、同一渠道位置上，台词逐字相同 |
| strip 后相等 | 49 / 230 | 与主口径相同 ⇒ 差异**不是**空白造成 |
| 归一化后相等 | 49 / 230 | 与主口径相同 ⇒ 差异**不是**标点/全半角造成 |
| 同位置 speaker 相同 | **230 / 230** | 对齐有效（同一个人在同一位置说话） |
| 同位置 seq 相同 | 28 / 230 | 说明两臂事件流不同步 ⇒ **禁止按 seq 对齐** |

**示例（同一位置、同一说话人、同一个模板，内容不同）**
| 位置 | t300（P002，public/skill_practice） | t355（P002，public/skill_practice） |
|---|---|---|
| 第 1 条 | `（刨子推过木料，木屑卷起）慢点来，急不得。` | `（刨子推过木料，卷起薄薄一层刨花）慢点来，木头不骗人。` |
| 第 2 条 | `秀娘笑眯眯地递过一块刚出炉的桂花糕：“来，尝尝这个，我新调的方子——你要是喜欢，回头我教你做……”` | `秀娘笑眯眯地递过一块刚出炉的桂花糕：“来，尝尝看，做点心啊，最重要的就是舍得放料、也得舍得花心思……”` |

---

## 5. 解释与边界（不许越界）

1. **`temperature` 已是 0.0**（`code/freeze/llm_client.py:263`）⇒ 差异**不是我们把温度调高**；来源是服务端非确定性（批内 batching/并行等，**具体机制未测，标 UNKNOWN**）+ 两臂树上有无关改动导致上下文轻微分叉。
2. 本证据**只**证明"逐条不可配对"这一条事实，**不**证明"两臂分布一定等价"；分布级等价需 D4 自己出读数并给噪声带。
3. 比率型指标在同一对 null pair 上的差（旁白率 0.87pp、裸 ID 0.87pp、无人称 1.75pp，见 `D3-不自然模式清单.md` §3）**只作噪声带初估**，不作阈值；分母越小的指标（如 68 条承接分母）噪声越大（4.41pp）。
4. 不得把本证据的 21.3% 当作"复现率下限"去要求别人复现到 21%——它只是**同一批配置下的观测值**。

---

## 6. 产物 sha256

| 文件 | sha256 |
|---|---|
| `v2/evidence/d3_null_pair.py` | `bb983b6ecb94600e46cf02a57e8b206420964f887cd06c2a6b2d3bc7bbcedda4` |
| `v2/evidence/d3_null_pair_result.json` | `bab6f5645988ff65ea153e0ccc2bb28e5bad6a753415fcbbc1d72a395c2e115b` |

> 本文件自身不改动脚本与结果，故只绑**脚本 + 结果**两个 sha（自指 sha 会因文本编辑而失真，故不给）。

```bash
sha256sum v2/evidence/d3_null_pair.py v2/evidence/d3_null_pair_result.json
```
