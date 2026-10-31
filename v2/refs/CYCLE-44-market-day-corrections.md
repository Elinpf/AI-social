# 勘误单 · market-day 预登记与对照表（应 `evidence-verifier` 2026-10-31 22:40 核验意见）

> 作者：`sim-engineer`｜时间：2026-10-31 22:4x｜性质：**只登记事实与勘误，不改判据**
> 复核人提出的 4 点，逐条处置如下。凡涉及「判据/时序是否作废重跑」，一律**不越权裁决**，等 Leader 定。

## 0. 可复算的 sha / 文件清单（请按此判，别用旧值）

| 项 | 值 | 取法 |
|---|---|---|
| 分支 tip | `3347c930f9c16c37895759d4dbc7b6ed5a0ce14e` | `git rev-parse life/market-day` |
| 分支 `HEAD:code` | `3039ed21e5a2b74d595aab850e7adde34cbbffd0` | `git rev-parse HEAD:code` |
| OFF/基线 `code` 树 | `5c641e080b24f03e82b28c837e73ca27fec15c03`（= `b3358fb:code`） | `git rev-parse b3358fb:code` |
| 预登记文件整文件 sha256 | `0dfd5707986b0eab773fbe84745b08c33b754f48f5597eb61317761086c07fee` | `sha256sum v2/refs/CYCLE-44-market-day-prereg.md` |
| 预登记行数 | **349 行**（A2 后；旧「267 行」已作废） | `wc -l` |
| 预登记「自身 sha256」归一化值 | `1e774551223edb74d06b63edb8f65aaf325d0bbddbea9cb1856c1a5e5f37dac8` | 卡内 §0 行给了复算命令（把该行 64 位值换成 `<SELF>` 后取 sha256） |
| A1 commit | `c29019e6e5baece9dbedc62e733b3837f03ab017` | `git log` |
| A2 commit | `3347c93…`，时间 `2026-10-31T22:35:15+08:00` | `git show -s --format='%H %ci' 3347c93` |
| 首版冻结 commit（作废） | `b5d8d5b`（对应卡内 267 行 / 43d45ed3 成稿） | — |
| 远端实测 | `3347c93… refs/heads/life/market-day` | `git ls-remote origin life/market-day`（实跑输出） |

## 1. 「主仓本地对象库没有 3347c93」⇒ 已给 bundle（两种）

主仓（`.../work/尝试/social-experiment`）是 Leader 明令**不得触碰的 dirty 工作区**，故我**没有**往它里面加分支。改给 bundle，放团队共享区：

| 文件 | 大小 | sha256 | 用途 |
|---|---|---|---|
| `artifacts/evidence/life-market-day-thin.bundle` | 47 KB | `ea6c3b10f100af109d84fc73713f69d27ba4b66eaa6dbfb791321267561038a0` | **推荐**：只含 `b3358fb..life/market-day` 四个提交，**需主仓已有 `b3358fb`**（主仓有） |
| `artifacts/evidence/life-market-day.bundle` | 246 MB | `98b7525dd9f3ffa329d4e0445fd74c53a2a9ba984103fdcca0b6e31806b5c3dc` | 自包含全历史（`git bundle verify` → "records a complete history"），不想依赖主仓时用 |

核验命令（不写主仓、不改任何分支，只读）：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment   # 主仓（只读取对象，不写）
B=/root/.jiuwenswarm/.agent_teams/jiuwen_team_cron___1a192429735_3d16df73a0df/team-workspace/artifacts/evidence/life-market-day-thin.bundle
git bundle verify "$B"            # 期望：records 4 commits / refs/heads/life/market-day
git fetch "$B" life/market-day:refs/verify/life-market-day   # 只写 refs/verify/*，不动 master、不动工作区
git cat-file -t 3347c93 ; git show -s --format='%H %ci %s' 3347c93
git show 3347c93:v2/refs/CYCLE-44-market-day-prereg.md | sha256sum   # 期望 0dfd5707…
```

> 若你希望**干脆在主仓留一个可 `cat-file` 的引用**，那需要 Leader 放行（会写主仓 refs）。我不擅自做。

## 2. 时序：A2（22:35:15）**晚于** r48 OFF 臂起跑（22:34:26）49 秒 —— 如实登记

- 事实：`A2 commit 22:35:15` vs `r48 OFF 臂命令发出 22:34:26`（`evidence/baseline/01-run-command_r48.txt` 头行）。**差 +49 s**。
- 我能确证的下界只有一条：**A2 早于 ON 臂 `started_at`**（ON 臂尚未起跑）。「早于**两臂**」这条**不成立**，复核人判得对。
- 影响面（如实、不夸大）：A1/A2 **只改 `v2/refs/`**，`code/` 树三次取值一致（`3290…`→ 实为 `3039ed21…`，A1 前后、A2 前后均未变），OFF 臂跑批输入（代码/配置/env）**未受任何影响**；受影响的只是「预登记文件在 OFF 臂起跑时点尚未包含 A2 那一段文字」这一**文档时序**。
- **我不裁决**：是否作废并重跑 OFF 臂由 Leader 定。若 Leader 判「重跑」，我这边无需改码，只需 run-operator 起跑、我更新报告时序段。

## 3. 对照表 / `INSTALL.md` 过期（会误导判定）—— 需要更新的行与正确值

| 行 | 现写（过期） | 应改为 |
|---|---|---|
| 第 1 行 | `267 行 / 43d45ed3` | **349 行 / `0dfd5707…`**（A2 后） |
| 第 4 行 | 「code 树 `5c641e08`（两臂相同）」 | 「OFF 臂 `5c641e08`、ON 臂 `3039ed21`；允许差异 = `code/life/agent.py`（+45）、`code/life/market_day.py`（+128）、`code/life/tests/test_market_day_arm.py`（+404），`git diff --stat` 实测 3 files / +577，全在 `code/life/` 内」 |
| 第 15 行 | 「pre-reg 早于**两臂**」 | 建议表述：「pre-reg 首版 `b5d8d5b`（22:2x）早于两臂；**§A2 修订 `3347c93` 晚于 OFF 臂 49 s**，仅改 `v2/refs/`，`code/` 未变」——是否按此写、是否判瑕疵，Leader 定 |
| `INSTALL.md` 文件清单表 | sha 全为旧值 | 见本单 §0 表 |

> 这两份文件不在我的交付边界内（属勘察/仪器侧文档），我**不擅自改**；此处给出正确值，请由 Owner 或 Leader 指定人更新。

## 4. 关于「样本量/臂配对齐」

复核人第 4 点成立：**不能**用 r24 作 OFF 臂、r48 作 ON 臂。基线侧 Leader 已让 run-operator 补 r48（`run_n16r48_seed42`，在跑）。我交付里引用的 r24 只用于**离线冒烟**（离线 mock、`env -u HITT_LLM_PROVIDER`、零 token，`/tmp/market_day_mock_{off,on}`），**不是**本轮 OFF/ON 对照臂，报告里须如此标注，不得混用。

## 5. 我这边可被独立复算的命令（一行一条）

```bash
cd /tmp/hitt_life_marketday
git rev-parse life/market-day HEAD:code                                   # 3347c93… / 3039ed21…
git rev-parse b3358fb:code                                                # 5c641e08…
sha256sum v2/refs/CYCLE-44-market-day-prereg.md                            # 0dfd5707…
wc -l v2/refs/CYCLE-44-market-day-prereg.md                                # 349
git diff --stat 5c641e080b24f03e82b28c837e73ca27fec15c03 3039ed21e5a2b74d595aab850e7adde34cbbffd0
git show -s --format='%H %ci' 3347c93
python3 tools/market_day/off_equiv_prompts.py --base /tmp/hitt_baseline_master --branch /tmp/hitt_life_marketday --out /tmp/market_day_off_equiv.json
python3 tools/metrics/market_day_readings.py --selftest                    # 12/12
cd code && python3 -m pytest -q -p no:cacheprovider life/tests/test_market_day_arm.py   # 36 passed
```

## 6. 撤回与更正（Leader 22:41 裁决 + 校验员 purpose 拆分实测）

**撤回**：我 22:40 转给 `run-operator` 的「r24 与 CYCLE-42 逐类相同可能是**缓存复现**」这一说法**作废，不得写入任何报告**。

- 事实（校验员实测，按 purpose 拆分）：`cached` 全部落在 `importance` 一路（`1387/1523 = 91%`）；
  **`dialogue` 一路 `cached = 0/191`** ⇒ 对话产出这条路**零缓存命中**，故「消息数与 CYCLE-42 相同」**不能用缓存解释**。
- 报告写作纪律（Leader 22:41 明令）：
  1. **不得出现任何缓存归因**；
  2. 「两臂 prompt 相同」必须分层说：**非集日子集两臂 prompt 逐字节相同**（机制保证、可验）；
     **集日子集按设计不同**（ON 多一行集日文案）；两臂 `cached` 命中率若在 `dialogue`/`importance` 上出现差异，
     属**预期内**的 prompt 差异所致，须如实标注，**不得**据此声称「两臂同质」；
  3. 两臂 `llm_cost` 均要 **purpose 粒度**（`dialogue / importance / judge / reflect / plan`），不只总数；
     任一臂出现 `degraded > 0` 或 `fallback_detected = true`，**必须写进局限性**；
  4. §A2 那 49 秒披露必须**与结论同屏**（不许塞脚注），并同屏给出「A2 未动 `HEAD:code` = `3039ed21`」
     与「OFF 臂实跑 `code` = `5c641e08`」两个树值，否则「未动可执行物」不可复算。

## 7. 报告写作约束（Leader 22:43 定稿，写作时逐条照抄，不得拔高）

### 7.1 `run.jsonl` 不入库 ⇒ 必须有可复算替代凭据（三样缺一不可）
1. 小文件入库：`metrics_r48.json` / `metrics_r48.md`、两臂 `llm_cost.txt`。
2. 报告附录「证据清单表」：每个**未入库**文件给出「绝对路径 + 字节数 + sha256 + 生成命令」。
3. 报告引文必须能反查到具体 `msg_id`（正文摘录 ↔ 证据清单表 ↔ 原始 `run.jsonl` 三方对得上）。
> 纪律：**不得 `git add -f`** `run.jsonl`（`.gitignore` 的 `**/*.jsonl` 是既定规则，历史 `-f` 属旧例外，本轮不重复）。

### 7.2 temperature / 采样：唯一允许的写法（一字不许拔高）
> `code/config/llm.json` 未设置 `temperature`/`top_p`；唯一入口 `code/freeze/llm_client.py:263` 默认 `temperature=0.0`；`LLM_CALL` 事件载荷（`code/freeze/events.py:150-163`）**不含** temperature 字段。因此「本轮采样为温度 0」只能表述为**代码默认值推定**，由 `prompt_hash`/`cache_key` 间接佐证，**不得**表述为「日志证明了 temperature=0」。

### 7.3 由 7.2 推出的两条必写局限性
1. **独立性假设弱化**：温度 0 下同一 prompt 输出近似确定，消息之间**不是独立抽样**；主判据（比例比较）仍成立，但 **Wilson CI 可能失真**，不得声称 CI 严格有效。
2. **DE=1.5 的定位改写**：由「保守方差估计」改为「**对确定性采样的补偿**」；并说明 **DE=2 为敏感性上限**（非主判据）。

### 7.4 因果强度：可以说更强，但不能删单 seed 局限
- 可说：温度 0 + 确定性 ⇒ ON/OFF 差异**只能来自 prompt 差异**，因果归属比一般随机实验更干净。
- 必须同屏保留：**单 seed 无法区分「确定性真效应」与「某条 prompt 恰好触发的特例」**，不得因「更干净」删掉该局限。

### 7.5 与 §2 / §6 的一致性要求
报告正文的「§A2 49 秒」披露必须与本件 §2 措辞一致（Leader 原话），不得出现两份文本分歧；「缓存归因」整段禁止出现（见 §6）。

## 8. §7.3 / §7.4 的事实基础被校验员推翻 → 待 Leader 确认的**替换措辞**（2026-10-31 22:44）

### 8.1 新事实（校验员实测，绑 commit / 绑日志）
| 项 | C42-OFF（`590c96b` 语料） | r24 基线（`b3358fb`/`5c641e08`） | 差 |
|---|---|---|---|
| 总事件 | 33853 | 33850 | −3 |
| `PERSONA_DRIFT_CANDIDATE` | 84 | 87 | **+3** |
| `PERSONA_DRIFT` | 30 | 28 | −2 |
| `MEMORY_FORGET` | 409 | 407 | −2 |
| `RELATION_CHANGE` | 3113 | 3111 | −2 |
| `LLM_CALL` 总数 | 2252 | 2252 | 0 |
| `dialogue` calls / cached | 191 / 0 | 191 / 0 | 0 |
| `importance` calls / cached | 1523 / 1387 | 1523 / 1387 | 0 |
| `tokens_out` total | 159907 | 146666 | **−13,241（≈8%）** |
| `judge` tokens_out | 106330 | 95288 | −11,042 |
| `importance` tokens_out | 36575 | 34289 | −2,286 |
- 首次发散：第 8048 条（`mono_ts=9020`，`P001`），C42 在 `SLEEP_STARTED` 之后多一条 `PERSONA_DRIFT_CANDIDATE` ⇒ 发散点在**人格漂移判定链（行为层）**，不是记录层。

### 8.2 结论（推翻「确定性采样/严格重放」的说法）
- **调用骨架（scheduling/quota/轮次/缓存命中）高度一致，但 LLM 文本层非确定**：同样 2252 calls、同样 1387 缓存命中，`tokens_out` 却差 13,241（8%）。
- ⇒ 「r24 与 C42 逐类相同」只能说明**骨架可复现**，**不得**写成「输出可复现 / 确定性重放」。
- 「默认 `temperature=0.0`」**没有**带来逐字确定的输出（可能来自 provider 侧非确定性 / batching / 模型快照差异）；且温度字段本就不在日志里（§6 / §7.2）。

### 8.3 建议替换措辞（**等 Leader 裁决后再落报告**；Leade 已下的 §7.2 写法不变）
- 替代 §7.3-1（独立性假设）：
  > 消息之间**不满足独立同分布**：调度骨架一致但文本层存在可测的非确定性（同 2252 calls / 同 1387 缓存命中下 `tokens_out` 差 8%）。主判据（比例比较）仍成立，但 **Wilson CI 只能作近似**，不得声称严格有效。
- 替代 §7.3-2（DE 定位）：
  > **DE=1.5**（DE=2 为敏感性上限）用于补偿两件事：① 同一居民-天内的消息相关性；② **文本层的非确定性**。它是**方差近似**，不是「保守估计」的证明。
- 替代 §7.4（因果强度）：
  > 两臂差异的**分配层**（发不发、发多少、缓存命中）可比性高；但**文本层非确定**，故不得把 ON/OFF 差异全部归因于 prompt 一行——须并列「单 seed 无法区分确定性真效应与某条 prompt 触发的特例」，并声明**文本层噪声未被量化**（本轮无重复臂）。

## 9. **最终口径（Leader 22:44 定稿，逐字执行）—— 覆盖 §7.3 / §7.4，并取代 §8.3 的建议稿**

> 依据：校验员 token 级实测推翻「确定性」判断；Leader 明确「§7.3/§7.4 之前所有与『确定性』有关的表述全部作废」。
> 本节为**唯一有效**的写作口径；§7.3、§7.4、§8.3 仅作历史留痕，**不得引用**。

### 9.1 禁用词与允许表述（逐字）
- ❌ **禁止出现**：「确定性」「可复现」（作为输出属性时）「重放」「输出可复现」。
- ✅ **只能写**：「**调度骨架可复现**（调用数 / purpose / `cached` / MSG 类计数逐项对齐）+ **文本层非确定**（`tokens_out` 差 8%、人格漂移链 3 处事件差）」。
- 支撑数据（写报告时原样引）：`LLM_CALL` 2252 两批相同；`dialogue` 191（`cached` 0）；`importance` 1523（`cached` 1387）；MSG 24+167 相同；`tokens_out` 146666（r24）vs 159907（C42）差 8%（`judge` 95288 vs 106330、`importance` 34289 vs 36575）；`PERSONA_DRIFT_CANDIDATE` +3、`PERSONA_DRIFT` −2、`MEMORY_FORGET` −2、`RELATION_CHANGE` −2，首次发散 `mono_ts=9020` 的 `P001` `SLEEP_STARTED` 之后。

### 9.2 §7.4 因果强度（**原句删除，改用下句**）
> 「同一 prompt 下输出非严格确定，故 ON/OFF 差异中除 prompt 差异外还含运行间波动；因果归属**不能**宣称比一般随机实验更干净。」
（原文「温度 0 + 确定性 ⇒ 差异只能来自 prompt」**不成立、已删除**。）

### 9.3 §7.3 独立性 / CI（**改用下句**）
> 「同一 prompt 下输出非严格确定（实测 `tokens_out` 差 8%），但消息级独立性不可直接断言；Wilson CI 按 **DE=1.5 保守处理**、**DE=2.0 作敏感性**，**DE 是保守补救而非实测方差**。」

### 9.4 新增必写局限性（第四类局限）
> 「本轮每臂只跑一次，未做重复测量；文本层非确定意味着 `R_B` 点估计存在**运行间波动**，幅度未被本设计估计。若两臂 Δ 落在 **4–7pp** 区间，**不足以判定方向**，只能记为『未达判定标准、方向性提示』。」

### 9.5 判定纪律（Leader 22:44 特别强调，写报告时置顶自查）
> 若实测 Δ 落在 5pp 附近，**不许**喊「达到阈值」。单次运行 + 8% 文本波动下此类结论换一次运行就可能翻盘。
> 自查：出现「达到阈值 / 达标 / 成立」字样前，必须同时满足 §3 三条（Δ≥+5.0pp、CI 不重叠、绝对条数≥8/208）**且** Δ 不在 4–7pp 边缘带；否则一律按 §9.4 写。

### 9.6 保持不变
§7.1（`run.jsonl` 不入库 + 三样替代凭据）、§7.2（temperature 唯一写法）、§7.5（一致性要求）**继续有效**。

## 10. **终稿口径（Leader 22:45 定稿 = §8.3 + 三处微调 + 4–7pp 限定 + 骨架用途说明）**

> 效力：**本节为报告写作的唯一权威文本**。与 §9 冲突处以本节为准（尤其 §9.3 的「DE 是保守补救」措辞作废，改用本节 10.3）；
> §9.1 的**禁用词**与**骨架表述**继续有效；§7.1（证据清单）、§7.2（temperature 写法）、§7.5（一致性）继续有效。

### 10.1 独立性 / CI（§8.3 原样 + 一句补充，逐字用）
> 消息之间**不满足独立同分布**：调度骨架一致但文本层存在可测的非确定性（同 2252 calls / 同 1387 缓存命中下 `tokens_out` 差 8%）。**骨架一致不等于样本 iid——同一居民-天内仍有相关性**，DE 补的正是这两件事。主判据（比例比较）仍成立，但 **Wilson CI 只能作近似，不得声称严格有效**。

### 10.2 因果强度（§8.3 原样，唯「确定性真效应」→「真实效应」，逐字用）
> 两臂差异的**分配层**（发不发、发多少、缓存命中）可比性高；但**文本层非确定**，故**不得**把 ON/OFF 差异全部归因于 prompt 一行——须并列「单 seed 无法区分**真实效应** vs 某条 prompt 恰好触发的特例」，并声明**文本层噪声未被量化**（本轮无重复臂）。

### 10.3 DE 定位（§8.3 原样；**「对确定性采样的补偿」作废**，逐字用）
> **DE=1.5**（**DE=2 为敏感性上限**）用于补偿两件事：① 同一居民-天内的消息相关性；② **文本层的非确定性**。它是**方差近似**，**不是「保守估计」的证明**。

### 10.4 必写局限（显眼位置，逐字用）
> 本轮每臂只跑一次、未做重复测量；文本层非确定（`tokens_out` 差 8%）意味着 `R_B` 点估计存在**运行间波动**，幅度未被本设计估计。**若两臂 Δ 落在 4–7pp 区间，不足以判定方向**，只能记为「未达判定标准、方向性提示」。

### 10.5 「调度骨架可复现」的**用途**（必须写清，防与"输出可复现"混用）
> 写法模板：「**调度骨架可复现**（`LLM_CALL` 2252 两批相同、`dialogue` 191/`cached` 0、`importance` 1523/`cached` 1387、MSG 24+167 逐项对齐）——**它的用途是两臂可比性的依据**（说明差异不是来自调度/调用结构），**不是**「输出可复现」；文本层非确定（`tokens_out` 146666 vs 159907，差 8%；漂移链 3 处事件差）另行标注。」
> ⚠ 两者混用是最容易被打回的写法：**骨架用途 = 可比性依据；输出 = 非确定**。

### 10.6 temperature（§7.2 定稿句不变 + 并列实测，互不矛盾）
> 参数层：`code/config/llm.json` 未设置 `temperature`/`top_p`；唯一入口 `freeze/llm_client.py:263` 默认 `temperature=0.0`；`LLM_CALL` 载荷（`freeze/events.py:150-163`）不含该字段 ⇒ 只能表述为**代码默认值推定**。
> 结果层：实测同骨架下 `tokens_out` 差 8% ⇒ **输出非严格确定**。
> 两者关系：**一个是参数（推定）、一个是结果（实测），并不矛盾**。

### 10.7 判定纪律（沿用 §9.5）
Δ 在 5pp 附近不许喊「达到阈值」；写「达到阈值/达标/成立」须同时满足 Δ≥+5.0pp、CI 不重叠、绝对条数≥8/208，**且 Δ 不在 4–7pp 边缘带**；否则按 10.4 写。

## 11. **二次定稿（Leader 22:46 裁决，三处改动；覆盖 §10 相应条目）**

> 效力：本节与 §10 合并后为最终口径。冲突处**以本节为准**：§10.3（DE 措辞）与 §10.7（判定纪律）被本节 11.1 / 11.3 替换；§10 其余条目（10.1/10.2/10.4/10.5/10.6）继续有效。

### 11.1 DE 措辞（**「保守补救」作废**，逐字用）
> Wilson CI 按 **DE=1.5** 计算（用于补偿 ① 同一居民-天内相关性 ② 文本层非确定性），**DE=2.0 作为敏感性上限**；**DE 未由实测方差反推，属方差近似**，不构成保守性证明。

### 11.2 边缘带规则的**确定时间**（防"事后加码"质疑）
> 边缘带规则（Δ∈[4,7]pp 不判达标）于 **2026-10-31T22:46:47+08:00** 确定，早于 ON 臂 `started_at`（`2026-10-31T22:34:26+08:00` 为 **OFF** 臂起跑时间；**ON 臂 `started_at` 在本规则确定时尚不存在——ON 臂未起跑**），依据为文本层非确定性幅度已实测（`tokens_out` 差 8%）而重复测量缺失。

- ⚠ **如实说明（不伪造时间戳）**：ON 臂起跑时间此刻**客观不存在**（run-operator 尚未起 ON 臂）。因此本规则的可证性锚点 = ① 本文件写入时间 `2026-10-31T22:46:47+08:00`；② 该时间**早于 OFF 臂之后的任何 ON 臂起跑记录**（起跑后由 run-operator 的 `01-run-command_r48-on.txt` 头行时间回填比对，**回填只填时间、不改判据**）。校验员如要求更强的不可篡改锚，可要求我另行 commit 本文件取 commit 时间。
- 回填规则（写死）：`ON 臂 started_at` := run-operator 的 ON 臂起跑记录头行时间戳，原样照抄，不改写、不四舍五入。

### 11.3 判定表述再收紧一档（**禁止**写「证明集日注入有效」，逐字用）
> 即使三条都满足且 Δ 不在边缘带，也只能写：「**在本轮单次运行、单 seed、单 provider 条件下，达到预登记判定标准**」。
> 理由：文本层非确定 + 无重复臂 ⇒ 外部效度有限，措辞必须带条件；不得写成「证明集日注入有效」「证明机制有效」。

### 11.4 其余照 §10（10.1 独立性 / 10.2 因果强度 / 10.4 4–7pp 局限 / 10.5 骨架用途 / 10.6 temperature）
