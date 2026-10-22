# R17 · L-7 结构臂（LIFE_PROMPT_L7_STRUCT）预注册观测项

- 分支：`feat/l7-structural-dedup`（基于 master `9a7ea1a`）
- 处理臂：结构约束生成前下发（默认 ON）
- 落盘时间：2026-10-22（**跑批之前写死，事后不许改口径**）
- 执行者：life-engineer（T1）｜取证：evidence-runner（T2）｜对账：report-writer

---

## 1. 本轮主张（一句话）

L-7（8-gram 近重复率）连年击穿（R12 +9.72pp / R14 +11.18pp / R15）的根因不是「去重力度不够」，
而是**去重发生在生成之后**：台词已经按同一批开场/收尾套路生成完了，再靠一次重试碰运气。
本轮把约束**前移到生成前**，且**完全取消重试**（零额外 LLM 调用）。

## 2. 开关与默认值

| 项 | 值 |
|---|---|
| env 变量 | `LIFE_PROMPT_L7_STRUCT` |
| 默认值 | **ON**（本分支即处理臂） |
| 关闭用法 | `export LIFE_PROMPT_L7_STRUCT=0`（取值 `0/false/no/off` 均可关） |
| 默认值来源 | `code/life/l7_structural.py:49` `STRUCT_ENV` + `:88 enabled()`（取反判断） |
| 是否碰 config / engine 指纹 | **否**。纯 env + 提示词插入 + `ctx.l7struct` 一个 additive 审计键 |

> **合 master 前必须把 `LIFE_PROMPT_L7_STRUCT` 改为默认 OFF，与 G-1/F-6/DEQUP/F-3/F-4 范式对齐；
> 否则机制会在后续所有维度跑批中默认生效，造成跨轮污染。**

## 3. 处理臂做了什么（三条结构约束，全部生成前生效）

1. **开口方式轮转**：6 种结构（先叫对方／先说自己在做什么／先问对方／语气词起头／接住上一句的词／先感慨再落具体事），
   由 `sha256(agent|对象|day|slot|round|turn|mode)` 确定性指派。
2. **收束方式轮转**：4 种结构（问句收／很短一句收／语气词收／落在具体小事上收），与 ① 同源不同位。
3. **禁忌开头清单**：该 agent **可见事件**（`wv.visible_events`）里最近台词的归一化前 4 字
   （最多 4 个）作为显式禁令提前下发——这是 R12 `retry_suffix()` 那段信息的前移版本，但**不需要第二次调用**。
   取材刻意**不用进程级窗口**：否则「续跑 vs 一次性跑」会分叉，同 seed 重跑不再逐字节一致
   （`test_periodic_flush` / `test_resume_from_flush` 会直接红）。

配套：`_dequp_body()` 在结构臂开启时**不再撞车重试**，只记账。故 `retries` 期望值为 **0**。

## 4. 主观测项（决定本轮成败）

| 指标 | 基线口径 | 预期方向 | 判「失败」的条件（写死） |
|---|---|---|---|
| **L-7 `L-7_dup_ngram8_rate`** | 与处理臂同参数（n16r60 seed42，A0 其余开关全关）的 master 基线批；用 `tools/d5/dialogue_metrics.py` 复算 | **下降**（相对基线 ≤ −30%，即至少回收 R15 那 +11pp 量级的两倍） | 相对基线降幅 **< 15%**，或**上升** ⇒ 结构约束无效，本轮判「失败」 |
| **额外 LLM 调用（重试）** | 同批 `purpose="dialogue"` 调用条数 vs MSG 条数 | **相等**（retries = 0） | 出现 `dequp_retry` 或 dialogue 调用数 > MSG 条数 ⇒ 重试未真正取消 ⇒ 判「失败」 |
| **约束遵守率**（可离线算） | 生成台词归一化前 4 字落在其**该条**下发 `banned` 清单里的比例 | **低**（< 20%） | **> 50%** ⇒ 模型基本无视结构约束 ⇒ 即便 L-7 下降也**不可归因**，本轮判「机制未生效」 |

> 第 3 条是本轮的关键**伪证闸**：L-7 下降若伴随约束遵守率极低，说明下降另有原因（如随机性），不能算结构臂的功劳。

## 5. 护栏观测项（不许恶化；恶化即判「不可判」并单列）

| 指标 | 可接受范围 | 为什么盯它 |
|---|---|---|
| MSG 总条数 | == 基线（配额 `max_messages_per_slot=2` 未动） | 证明「不是靠少说话降低重复」 |
| L-1 台词长度（中位数 / excl_paren 分布） | 中位数 ≥ 基线 − 20% | 防模型为避重复而说半句，把生活气息做成电报体 |
| L-2 `narration_rate_proxy`、L-3 `paren_block_any` | 不高于基线 + 2pp | 防结构指令诱导旁白/动作描写 |
| L-8 `agent_id_leak_rate`、L-13 `token_leak_rate` | 不高于基线 + 1pp | 防提示词里的内部字样被抄进台词 |
| L-5 `template_hit_rate` | 不高于基线 | 模板句命中不许升 |
| L-11 `second_person_rate_dm_group` | ≥ 基线 − 10pp | 「先问对方」等结构应维持互动性，不许退化成自言自语 |
| L-12 / L-12b（第三方提及率 / 称呼率） | ≥ 基线 − 10pp | 生活气息代理：别为了不重复把对方名字也省了 |

## 6. 证据链要求（取证方口径）

1. `git rev-parse HEAD` = 处理臂 sha；`git status --porcelain -- code/` **为空**（跑在已提交代码上）；
2. 起跑命令中显式 `export LIFE_PROMPT_L7_STRUCT=1`（不依赖默认值）并写入 launch evidence；
3. 其余对话开关（`LIFE_PROMPT_GOSSIP_G1` / `LIFE_PROMPT_MEMORY_F6` / `LIFE_PROMPT_MEMORY_F6_DEQUP` /
   `HITT_DIALOGUE_*`）**不设**；
4. L-7 由 `tools/d5/dialogue_metrics.py` 官方复算，不得自造口径；
5. 真 LLM 真实性用 `obs llm-cost` 核验（R12 已证该命令可分辨真/兜底）。

## 7. 回滚方式

- 单步回滚：`export LIFE_PROMPT_L7_STRUCT=0` ⇒ 机制整体关闭（已由 `docs/forensics/l7s_off_path_check.py`
  离线自证：11 项检查全 true，`all_pass=true`，两态差异仅一处插入 136 字符）；
- 代码回滚：本分支只新增 `code/life/l7_structural.py`、`code/tests/test_l7_structural.py` 并改
  `code/life/agent.py` 五处（import / `_l7_struct_line` / 两个提示词插入 / `_ctx_snapshot` 审计 /
  `_dequp_body` 分支），`git revert` 单个 commit 即可，无配置迁移、无数据迁移。

## 8. 已知风险（诚实登记）

- **模型不遵守指令**：DeepSeek-Flash 可能无视「别用这几个开头」。若约束遵守率 >50% 而 L-7 未降，
  本机制应判「未生效」，需要更强的结构手段（如生成后确定性改写，但那会回到「补救」路线）。
- **模板化风险**：6×4 结构轮转本身可能催生新的固定句式（每类结构各形成一句式），
  故必须看 `L-12/L-11/L-1` 与人工抽样口径，不能只看 L-7。
- **禁忌清单的 token 成本**：每条约 +143 字符（≈70 token 量级，离线实测见
  `2026-10-22-l7-structural-off-evidence.txt` 的 `diff_chars`），n16r60 批共 510 条 ⇒ 总 token
  增量约 3.5 万，需在 `obs llm-cost` 里如实记录（不算失败条件，但要写进报告）。
- **可见事件取材**：孤立 agent（最近没听见别人说话）禁忌清单为空 ⇒ `n_banned=0`、整段省略，
  这类消息只受「开口/收束」两条结构约束；属预期，不是失败。
- **与 L-7 正相关维度混淆**：本轮**不**动配额、**不**开 G-1/F-6/DEQUP/F-3/F-4，**不**改 R15 收尾指令，
  保证单变量可归因。

## 9. 事后对账规则

报告撰写时**必须**按本节口径逐条填表：主观测项 3 条 + 护栏 7 条，逐项给「基线值 / 处理臂值 / 差额 / 判据 / 结论」。
口径若与本节不一致，以本节为准（本节先于跑批落盘并已提交进 git）。
