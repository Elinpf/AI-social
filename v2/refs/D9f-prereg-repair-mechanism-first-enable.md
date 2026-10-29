# D9f 预登记：「误会与和解」机制（DR）首次启用 —— mock 单变量验证

> 立件：Leader（team-leader）｜2026-10-29
> 上游：`v2/evidence/d9e-repair-dimension-not-enabled.md`（`dd2d9a46…`）—— 六维之 ③「误会与和解 = 0/686」的真实成因是 **`config/dialogue_repair.json` `enabled=false`**，属**机制未启用**，从未被检验。
> 本件批准 **mock 单臂**（零网络调用）；**真 LLM 臂暂不批**，待本批结果再定。

## 0. 为什么先跑 mock

机制完整度已确认：`code/life/dialogue_repair.py`（15645 B）含 ①旧账只读识别（`NEG_WORDS`）②把处境写进提示词（`gripe_context`）+ 选项工具箱（只给选项不给句式）③`reply_priority`（回复时优先挑有旧账的线程）④结构化信号 `dialogue_rift`。**只差一个开关。**

mock 能回答的问题只有两个，但这两问决定要不要花真钱：
- **旧账识别在 84 回合里能不能捡到东西**（`NEG_WORDS` 命中是否稀疏到等于不可用）；
- **`reply_priority` 会不会真的改变"挑哪条线程接话"**（若它不改变挑选，机制等于没接上）。

**mock 答不了**的：误会与和解的**语言表现**（mock 的 `body` 是模板文本）。这一点必须留给真 LLM 臂，本件不宣称。

## 1. 单变量与固定参数

| 项 | 值 |
|---|---|
| 受检变量 | `HITT_DIALOGUE_REPAIR` ∈ {**`0`（H0）**, **`1`（H1）**} |
| 基座代码 | worktree `.worktrees/a2-trigger` @ **`913ac4d`**（已确认**含** `dialogue_repair.py`，引入点 `712c155` 为其祖先） |
| 对照臂（H0） | **复用** `v2/evidence/mock_d9b_rw4_treat_n16r84_seed42`（`913ac4d` / DR off / window=4 / mock）—— **不新跑**，零成本 |
| 处理臂（H1） | 新跑 `v2/evidence/mock_dr_on_n16r84_seed42`：同基座、同参、加 `HITT_DIALOGUE_REPAIR=1` |
| 固定参数 | `seed=42 / agents=16 / rounds=84 / max_turns=6 / max_slots=2 / max_turns_per_round=2 / window=4 / provider=mock`、`HITT_REPLY_BUDGET=1` |
| 不设 | `HITT_NO_INIT_UNREPLIED`、`HITT_REPLY_PICK_ORDER`（保持与对照臂一致） |

**复用对照臂的合法性**：`mock_d9b_rw4_treat` 与 `mock_d9c_recent` 已做过逐条 `MSG_*` 比对（**0 差异**），说明"默认 `recent_first`"确实没改行为 ⇒ 用它作 H0 与"用新代码跑一臂 DR off"等价。**若实现者坚持新跑，必须两个都新跑**（不得一新一旧）。

## 2. 必报量（每条带 H0 取值，按 `hit-metric-h0-baseline-rule.md`）

| # | 量 | H0 取值 | H1 下能否离开 | 区分力 |
|---|---|---|---|---|
| 1 | **`dialogue_rift` 出现条数** | **0**（三臂实测，已双人确认） | 能（enabled + 有 rift 才写） | ✅ **主判据** |
| 2 | `dialogue_rift.prompted = true` 条数 | 0 | 能 | ✅ |
| 3 | `dialogue_rift.route == "reply_priority"` 条数 | 0 | 能 | ✅ |
| 4 | `dialogue_rift.open > 0` 的条数 | 0 | 能 | ✅ |
| 5 | 负向词命中条数（`NEG_WORDS`，**上游词表**非镜像） | 需本批实测（H0 臂即基线） | 能 | ✅ 但**只作解释量** |
| 6 | 和解词命中条数（`REPAIR_WORDS`） | 同上 | 能 | ✅ 但**不得作主判据** |
| 7 | MSG / 发起 / 回复 / 线程数 | 929 / 266 / 663 / 266 | 能 | ✅ 代价闸 |
| 8 | `≥3 轮` 绝对 / `lag` 分布 | 120 / `{1:656,2:7}` | 能 | ✅ 代价闸 |
| 9 | ~~"误会与和解发生次数（词表）"~~ | — | — | ❌ **不得作主判据**（词表漏项 + 措辞差异会主导，见 §4-1） |

## 3. 判定四档（命中即停）

| 序 | 档位 | 条件 |
|---|---|---|
| 1 | **E-机制触达** | 量 1 > 0 **且** 量 2 > 0（= 旧账真的进了提示词） |
| 2 | **M-触达但未影响挑选** | 量 1 > 0 但 **量 3 = 0**（= 识别到了，`reply_priority` 从未改变选择） |
| 3 | **T-未触达** | 量 1 = **0** 且 两臂 `MSG_*` 逐条 0 差异 ⇒ 机制在 mock 下完全没跑起来 |
| 4 | **I-无效（代价超限）** | 量 7 的 MSG `< 929 × 0.90`（= 用少说话换和解） |

- 命中 3 ⇒ 必须查两件事再下结论：①`NEG_WORDS` 在 mock 的模板文本里是否根本命中不了（**模板语料的局限，不是机制问题**）；②`DR.ingest` 是否被调用（接线）。**不得直接写"机制无效"。**
- 命中 1 也只许写「**机制触达**」，**禁止**写「产生了误会与和解」——后者是语言层表现，mock 答不了。

## 4. 写死的三条限制

1. **词表层不得作主判据**：`NEG_WORDS`/`REPAIR_WORDS` 是 `tools/d5/*_lexicon.txt` 的**子集镜像**（测试只守"不漂移"，上游新增词不会自动进来）⇒ 用它衡量"和解是否发生"会**系统性漏检**。主判据必须是 `dialogue_rift`（机制自报）。
2. **`reply_priority` 是干预，必须披露**：它改的是"回复时优先挑有旧账的线程"，**不是**"居民自发冲突"。判定件须写「**干预了回复优先级**」，与"自然发生的误会"严格区分。
3. **mock 无真实语言**：本批**不能**回答"误会与和解读起来像不像人"。那是真 LLM 臂的事。

## 5. 交付与验收

| 交付 | 验收 |
|---|---|
| 一臂 mock 日志 `mock_dr_on_n16r84_seed42/run.jsonl` | 附 `stat -c%s` / `sha256sum` / `wc -l`（同一次命令） |
| **开关自证** | 两臂 `config_digest` 不同、`config/life_v2.json` 文件 sha 与 `fingerprint` **相同**；另：该 config **不进 `FINGERPRINT_FILES`**，故 `fingerprint` 必同（本身就是证据） |
| 接线证明 | `grep -c "dialogue_rift"` 两臂（H0 应 0、H1 应 >0） |
| 跑批串行 | 起跑前 `ps` 确认无并发 |
| **不改 code** | 本批**零代码改动**，只设 env |

## 6. 状态

- [x] 预登记落盘
- [ ] H1 臂跑批（mock）
- [ ] 指标核算（量 1–8，每条带 H0 列）
- [ ] 判定与证据件
- [ ] 据结果决定是否申请真 LLM 臂
