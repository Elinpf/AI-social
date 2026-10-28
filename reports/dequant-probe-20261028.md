# T2 探针跑批取证报告：去量化词/回指模板臂（DEQUANT）真 LLM 同 seed A/B

- 取证角色：run-verifier（跑批取证工程师）
- 取证时间：2026-10-28 18:04–18:20 +08:00（两批合计墙钟 ≈ 11.8 分钟，远低于 60 分钟闸）
- 单变量：仅 `code/life/agent.py` 的两条 dialogue user prompt 末尾追加（OFF 臂提示词逐字节不变）
- **结论边界（先读这条）**：**单 seed（42）/ 小样本（每臂 67 条 `MSG_*`），不作统计断言**。探针尺度的作用是「证明指令能生效、方向对」，不是给出可信点估计。

---

## 0. 摘要（结论）

| 项 | OFF 臂（基线） | ON 臂（去量化臂） | 绝对变化 |
|---|---|---|---|
| 代码 sha | `71a6d74b4dcf704357092b7a88a9eca2c630be87` | `3888957475e502ead3f734bab6be74fd12f50832` | — |
| 字面黑名单（`DEQUANT_LEXICON` 14 词）**消息并集**口径（一条台词任一命中即计 1）**〔主口径〕** | 9/67 = **13.4%** | 3/67 = **4.5%** | **−8.9 pp** |
| 同上**逐词命中消息累加**口径（词次 ÷ 67） | 10/67 = **14.9%** | 3/67 = **4.5%** | **−10.4 pp** |
| 「上回」 | 4 / 6.0% | 0 / **0.0%** | **−6.0 pp** |
| 「想起」（**不在** 14 词 lexicon，仅在 `KEYWORDS`） | 2 / 3.0% | 1 / 1.5% | −1.5 pp |
| 「第三格」/「半指」 | 0 / 0.0% | 0 / 0.0% | ±0.0 pp（**地板效应**，见 §7） |
| 开臂是否真生效 | — | dialogue `prompt_hash` 67 个 vs OFF 67 个，**交集 0** | 硬证据（§5） |
| LLM 调用数 | 464 | 464 | **0**（本臂不新增任何 LLM 调用，零成本增量） |

> **两种口径并列，均成立，不得混写**：主口径 `13.4%(9)→4.5%(3) = −8.9 pp` 是**14 词消息并集**；`14.9%(10)→4.5%(3) = −10.4 pp` 是**逐词命中消息累加**（10 = 半袋5 + 上回4 + 上次1，**不含**想起）。差 1 条是因为 OFF 有 1 条台词同时命中「半袋+上回」（并集 9 条 / 词次 10）。详见 §7.1。

**能站住的话**：ON 臂确实吃到了新提示词（prompt_hash 零交集 + dialogue tokens_in 19301→26158），且在探针尺度上字面黑名单**消息并集命中率** 13.4% → 4.5%（**−8.9 pp**，主口径；逐词累加口径 −10.4 pp）、「上回」归零；`llm_calls` 两臂同为 464，说明本臂零新增调用、零推理成本增量。
**不能说的话**：不能说「量化词问题已解决」或「套话已消除」——探针每臂只有 67 条台词，1 条 = 1.49 pp；「第三格」「半指」在探针尺度本身就是 0，测不出下降（见 §7）；且 ON 臂出现**换词**（半袋↓、半勺↑，见 §7 表 1），词表内并非全面归零；更不能说「记忆引用未受影响」（该风险**本轮未验证**，见 §9.7）。

---

## 1. 串行闸证据（跑批前 pgrep + preflight，逐次贴出）

### 1.1 起跑前显式 pgrep（私有纪律：命令+输出入证）

```
$ pgrep -af 'orchestration[[:space:]]+run|run_batch|nightly\.py'
（首次执行时仅命中本检查命令自身的 /bin/sh 进程 1559235/1559238；无真实跑批进程）

$ pgrep -af 'orchestration run --life'
[无并发跑批 rc=1]
```

### 1.2 OFF 臂 preflight（隔离 worktree `.worktrees/dequant-baseline-71a6d74`）

```
$ cd .worktrees/dequant-baseline-71a6d74 && bash tools/d5/preflight.sh --tag run_batch
PASS preflight sha=71a6d74b(HEAD) ts=2026-10-28T18:04:49+08:00 concurrency=0 frozen_tree=clean
log=.../.worktrees/dequant-baseline-71a6d74/v2/evidence/preflight/preflight_20261028T100449Z_71a6d74b_run_batch.log
```

### 1.3 ON 臂 preflight（隔离 worktree `.worktrees/dequant-on`，HEAD=3888957）

```
$ cd .worktrees/dequant-on && bash tools/d5/preflight.sh --tag run_batch
PASS preflight sha=38889574(verify/dequant-on) ts=2026-10-28T18:12:57+08:00 concurrency=0 frozen_tree=clean
log=.../.worktrees/dequant-on/v2/evidence/preflight/preflight_20261028T101257Z_38889574_run_batch.log
```

两次 preflight 均 `concurrency=0 frozen_tree=clean`（`tools/d5/check_clean_tree.py` 的 HARD FAIL 前缀 `code/life/ code/orchestration/ code/config/ code/engine/` 均为空）。两臂**严格串行**：OFF 18:04:54 起跑 → 18:10:36 结束 → ON 18:12:57 起跑 → 18:19:05 结束，无重叠。

---

## 2. 基线口径（同 seed 同尺度的依据）

```
$ git rev-parse HEAD
71a6d74b4dcf704357092b7a88a9eca2c630be87

$ git diff --stat origin/master...71a6d74 -- code/
（空输出，rc=0）→ 基线相对 origin/master 在 code/ 上零差异

$ git show --name-status --oneline 3888957
3888957 feat(life): 去量化词/回指模板化 prompt 臂（默认 OFF，LIFE_PROMPT_DEQUANT=1）
M  code/life/agent.py
A  code/tests/test_dequant_prompt.py
A  tools/metrics/dequant_probe.py
A  v2/evidence/dequant_probe_baseline_71a6d74.json
→ ON 提交只含 4 条路径，越界检查通过

$ git cat-file -p 3888957:code/life/agent.py | sha256sum
ca2f77a1631063d9d4022a4d4b6b78889cb4b90ae035f448701ef228bc93173c
（与 life-dev 声明值一致；与我在工作区实测 `sha256sum code/life/agent.py` 一致）
```

一处必须记录的**非零差异**（不构成越界，属文档）：ON 分支父提交 `b4972fd` 与基线 `71a6d74` 在 `code/` 下的差异只涉及 `code/frontend/README.md`
（`git diff --stat 71a6d74..b4972fd -- code/` → `code/frontend/README.md | 18 +`，2 个 D7 README 提交）。
即：`code/frontend/README.md` 是 Markdown 文档、不参与 `code/life` import 链与运行时，**两臂运行时差异仅有 `code/life/agent.py` 的 +146 行**。

隔离做法（不抢 life-dev 工作树，也不动主干）：
- OFF 臂：`git worktree add .worktrees/dequant-baseline-71a6d74 --detach 71a6d74`；
- ON 臂：`git worktree add .worktrees/dequant-on -b verify/dequant-on feature/life-dequant-20261028`，随后 `git reset --hard 3888957`；
- `code/.env.local` 被 `code/.gitignore:11` 忽略，故从主树 `cp -p` 到两个 worktree（不产生 tracked 改动，不进 `git status`）；
- 主树（life-dev 的工作树）全程未被 checkout / 未被改动。
- 备注：ON 臂先用我自建的兜底快照 `65dd688`（含 3 个文件），life-dev 交付 `3888957` 后已弃用，改用其 sha 重起跑；**报告中一切 ON 结论绑定 `3888957`**（`65dd688` 只在 worktree 的 git reflog 中，不参与证据）。

---

## 3. 起跑命令与开臂证据（显式 export，不用默认值）

落盘于 `v2/evidence/run_dequant_on_n8r16_seed42/launch_env.txt`：

```
export LIFE_PROMPT_DEQUANT=1
cmd: setsid bash tools/d2/run_batch.sh --out-dir .../v2/evidence/run_dequant_on_n8r16_seed42 --seed 42 --agents 8 --rounds 16 --flush-every 8
code_sha: 3888957475e502ead3f734bab6be74fd12f50832
sha256(code/life/agent.py): ca2f77a1631063d9d4022a4d4b6b78889cb4b90ae035f448701ef228bc93173c
sha256(tools/metrics/dequant_probe.py): 39e5e6b1990b5698336d49a5733dfbe2b7ed96bf5e89fe1687bacb0fee5c7188
STARTED: 2026-10-28T18:12:57+08:00
```

实际起跑形式（setsid 脱离会话，禁长 sleep 轮询）：

```
setsid env LIFE_PROMPT_DEQUANT=1 bash tools/d2/run_batch.sh \
  --out-dir <abs>/v2/evidence/run_dequant_on_n8r16_seed42 \
  --seed 42 --agents 8 --rounds 16 --flush-every 8 > /tmp/dequant_on.log 2>&1 < /dev/null
```

OFF 臂起跑命令（未设 `LIFE_PROMPT_DEQUANT`，即默认 OFF）：

```
setsid bash tools/d2/run_batch.sh \
  --out-dir <abs>/v2/evidence/run_dequant_baseline_n8r16_seed42 \
  --seed 42 --agents 8 --rounds 16 --flush-every 8 > /tmp/dequant_baseline.log 2>&1 < /dev/null
```

**未**触碰 `LIFE_PROMPT_L7_STRUCT`（两臂环境里都不存在该变量），保持单变量。
注意：`run_batch.sh` 内部的 `emit_run_meta.py` 只把 provider/model/events 等运行期事实写入 meta，**不写 env 快照**；
因此开臂证据以本节 `launch_env.txt` + `setsid env LIFE_PROMPT_DEQUANT=1` 命令 + §5 的 prompt_hash 零交集三件套为准。

---

## 4. 真 LLM 验真（obs llm-cost 原始输出，逐字）

### 4.1 OFF 臂

```
$ (cd code && python3 -m obs llm-cost --log ../v2/evidence/run_dequant_baseline_n8r16_seed42/run.jsonl --require-provider openai_compat)
{"engine_log":{"by_provider":{"openai_compat":464},"by_purpose":{"dialogue":{"cached":0,"calls":67,"degraded":0,"thinking":0,"tokens_in":19301,"tokens_out":2334},"importance":{"cached":195,"calls":231,"degraded":0,"thinking":0,"tokens_in":612,"tokens_out":9909},"judge":{"cached":0,"calls":142,"degraded":0,"thinking":142,"tokens_in":17396,"tokens_out":29418},"negotiation":{"cached":0,"calls":4,"degraded":0,"thinking":0,"tokens_in":470,"tokens_out":115},"plan":{"cached":0,"calls":8,"degraded":0,"thinking":0,"tokens_in":708,"tokens_out":616},"reflect":{"cached":0,"calls":12,"degraded":0,"thinking":0,"tokens_in":5553,"tokens_out":703}},"llm_judgment_by_dimension":{"affection":43,"rel_affinity":5,"respect":43,"stance":43,"weekly_focus":8},"source":"engine_log(LLM_CALL)","total":{"cached":195,"calls":464,"degraded":0,"thinking":142,"tokens_in":44040,"tokens_out":43095,"tokens_total":87135}},"provider_guard":{"by_provider":{"openai_compat":464},"expected":"openai_compat","ok":true,"policy":"计划用真 LLM 时必须显式校验 provider 计数 > 0 且无 mock 混入。","problems":[]}}
```

### 4.2 ON 臂（原始输出同时落盘 `v2/evidence/run_dequant_on_n8r16_seed42/llmcost_raw.txt`）

```
$ (cd code && python3 -m obs llm-cost --log ../v2/evidence/run_dequant_on_n8r16_seed42/run.jsonl --require-provider openai_compat)
{"engine_log":{"by_provider":{"openai_compat":464},"by_purpose":{"dialogue":{"cached":0,"calls":67,"degraded":0,"thinking":0,"tokens_in":26158,"tokens_out":2459},"importance":{"cached":195,"calls":231,"degraded":0,"thinking":0,"tokens_in":612,"tokens_out":9486},"judge":{"cached":0,"calls":142,"degraded":0,"thinking":142,"tokens_in":17396,"tokens_out":29450},"negotiation":{"cached":0,"calls":4,"degraded":0,"thinking":0,"tokens_in":470,"tokens_out":112},"plan":{"cached":0,"calls":8,"degraded":0,"thinking":0,"tokens_in":708,"tokens_out":634},"reflect":{"cached":0,"calls":12,"degraded":0,"thinking":0,"tokens_in":5633,"tokens_out":719}},"llm_judgment_by_dimension":{"affection":43,"rel_affinity":5,"respect":43,"stance":43,"weekly_focus":8},"source":"engine_log(LLM_CALL)","total":{"cached":195,"calls":464,"degraded":0,"thinking":142,"tokens_in":50977,"tokens_out":42860,"tokens_total":93837}},"provider_guard":{"by_provider":{"openai_compat":464},"expected":"openai_compat","ok":true,"policy":"计划用真 LLM 时必须显式校验 provider 计数 > 0 且无 mock 混入。","problems":[]}}
obs_rc=0
```

三重条件逐条核对（两臂均满足）：
1. `by_provider` **只有** `openai_compat` 且 464 > 0 ✅
2. `provider_guard.ok = true`、`problems = []` ✅
3. `degraded = 0`（总量与各 purpose 均为 0）✅
→ **两臂均为真实 LLM 跑，非 mock、非 0 成本调用。**

旁证（不是验真依据，仅作一致性观察）：ON 臂 `dialogue.tokens_in` 19301 → 26158（+6857），与「两条 user prompt 末尾各追加约 146 字符」同向；cached 数两臂相同（195），说明缓存比例未被人为改变。

---

## 5. 开臂是否真生效（不靠自我声明，靠同 seed 的 prompt_hash 对拍）

落盘：`v2/evidence/run_dequant_on_n8r16_seed42/prompt_hash_compare.txt`

```
OFF(71a6d74) dialogue non-cached LLM_CALL: 67  distinct prompt_hash: 67
ON (3888957) dialogue non-cached LLM_CALL: 67  distinct prompt_hash: 67
intersection(prompt_hash): 0
sample OFF[0]: sha256:5079a0eaeed91f6f00e0fcec17568e49c3c100ec621cdc7c74045a0f6ba5b165
sample ON [0]: sha256:d95fb416c478efca66e64e4d66f84910eeb729d37c10e29d67b0309ceb11b821
```

同 seed、同 agent 数、同轮数下，若开关没生效，两臂 dialogue prompt 逐字节相同 → prompt_hash 应全等。实测 **交集为 0**，证明新提示词确实进入了 LLM 调用。
（口径说明：只比 `purpose="dialogue"` 且 `cached=false` 的调用，与 life-dev 声明的「只动两条 dialogue user prompt」一致；judge/importance 类 prompt 未受影响，其 hash 两臂不必相同也不作为判据。）

---

## 6. meta.json 关键字段（两臂）

| 字段 | OFF（`run_dequant_baseline_n8r16_seed42`） | ON（`run_dequant_on_n8r16_seed42`） |
|---|---|---|
| `code_sha` | `71a6d74b4dcf704357092b7a88a9eca2c630be87` | `3888957475e502ead3f734bab6be74fd12f50832` |
| `code_sha_end` | 同上 | 同上（跑批期间代码未变） |
| `git_dirty_code_files` | `[]` | `[]` |
| `events` | 6052 | 6047 |
| `llm_calls` | 464 | 464 |
| `llm_cached_ratio` | 0.4203 | 0.4203 |
| `provider` / `model` | `openai_compat` / `DeepSeek-Flash` | `openai_compat` / `DeepSeek-Flash` |
| `seed_in_log` / `n_in_log` / `rounds_effective` | 42 / 8 / 16 | 42 / 8 / 16 |
| `msg_counts` | `{"MSG_DM":58,"MSG_PUBLIC":9}` | `{"MSG_DM":58,"MSG_PUBLIC":9}` |
| `degraded_calls` / `fallback_detected` | 0 / false | 0 / false |
| `duration_sec` | 342 | 368 |
| `started_at` → `finished_at` | 18:04:54 → 18:10:36 | 18:12:57 → 18:19:05 |
| `run_sha256` | （见 meta.json） | `8ebb04757a652deb35dafd2b37ec6d7a3d27dda4f0d7c0ac7be3ffcc7efc0af9` |
| `assertions` | 全通过 | `msg_uid_unique=true, participants_consistent=true, ptr_cross_thread=0, ptr_dangling=0, reply_to_same_thread=true, turn_index_dense=true` |

> `git_dirty_files` 两臂均为 `v2/evidence/preflight/*.json`（preflight 自留锚点，非阻断前缀），`git_dirty_code_files` 为空 → 没有「树被污染」的情况。

---

## 7. 指标对照（同口径同尺度，needs-care：n=67/臂）

命令（两臂同一条）：

```
python3 tools/metrics/dequant_probe.py --log <run.jsonl> --out <out.json>
```

- OFF：`v2/evidence/dequant_probe_baseline_n8r16_seed42.json`（`log_sha256=2255888c3b90a5c9ac361868c0315f58dc80019b746418443cbb361207300d25`）
- ON：`v2/evidence/dequant_probe_on_n8r16_seed42.json`

### 表 1 黑名单词命中率（n_msg=67/臂；合计行给出**两种口径**，表头已标清）

| 词 | OFF count/pct | ON count/pct | Δ(pp) |
|---|---|---|---|
| 上回 | 4 / 6.0% | 0 / 0.0% | **−6.0** |
| 上次 | 1 / 1.5% | 0 / 0.0% | −1.5 |
| 半袋 | 5 / 7.5% | 1 / 1.5% | −6.0 |
| 半勺 | 0 / 0.0% | 2 / 3.0% | **+3.0（新增命中，换词）** |
| 想起（**不在** `DEQUANT_LEXICON`，仅在 `KEYWORDS`） | 2 / 3.0% | 1 / 1.5% | −1.5 |
| 半指 / 第三格 / 一指 / 两指 / 三指 / 第一格 / 第二格 / 三钱 / 半日 / 上月 | 0 / 0.0% | 0 / 0.0% | ±0.0（地板） |
| **合计·逐词消息命中累加**（14 词按词次累加 ÷ 67，**不含**想起） | **10 次 / 14.9%** | **3 次 / 4.5%** | **−10.4** |
| **合计·消息并集**（一条台词任一 14 词命中即计 1，**不含**想起） | **9 条 / 13.4%** | **3 条 / 4.5%** | **−8.9** |
| （附）消息并集·**含**「想起」 | 10 条 / 14.9% | 4 条 / 6.0% | −8.9 |
| `（把…往…` 起头句 | 0 / 0.0% | 0 / 0.0% | ±0.0（地板） |
| 骨架重复 | 0 / 0.0%（distinct skeletons 67/67） | 0 / 0.0%（67/67） | ±0.0（地板） |

逐词实测（`tools/metrics/dequant_probe.py` 产物 JSON 的 `lexicon` 非零项，原样引用）：
- OFF：`半袋 5`、`上回 4`、`上次 1` → 词次合计 10，消息并集 9（1 条台词同时含两个黑名单词）
- ON：`半勺 2`、`半袋 1` → 词次合计 3，消息并集 3

**ON 出现「换词」现象（与地板效应是两件不同的事，必须分开说）**：`半袋` 5→1（−6.0 pp）、`半勺` 0→2（**+3.0 pp，新增**）。即模型不是简单「删掉度量词」，而是换了另一个同族量词继续用。**因此不得表述为「套话已消除」**（Top5 里 3 个 count 只有 2，也仍在噪声区间）；并说明 14 词黑名单**不全**——下一轮主尺度复跑前建议复核词表覆盖面（尤其「半勺/三钱/半日」这类同族词）。

### 7.1 双口径事实说明与逐词更正痕迹（历史痕迹保留，勿删）

- **逐词更正（保留原值痕迹，只改事实、不动数字）**：原表写 `半袋 5/7.5% → 2/3.0%`、并把 `半勺` 列入「两臂皆 0 地板」组；实测产物 JSON 为 OFF `半袋5`、ON `半勺2 / 半袋1`。→ 原表 `半袋→3.0%` 与产物 JSON 不符，**已更正为 `半袋 5→1（1.5%）`**；`半勺` 原列「0.0% 地板」错误，**已更正为 `0→2（3.0%）`**。合计 10→3 未变（ON 侧 3 词次 = 半勺2 + 半袋1）。
- **错因（事实描述，此前归因写错，特此更正）**：`14.9%（10/67）`是**逐词命中消息累加**（半袋 5 + 上回 4 + 上次 1 = 10），**不含「想起」**；`13.4%（9/67）`是**14 词消息并集**；两者相差 1 条台词，因为 OFF 有 **1 条**台词同时命中两个词：
  `老周，你听说没…我手里这半袋粗盐还是上回从李集捎回来的…`（半袋 + 上回）⇒ 消息并集 9 条、逐词累加 10 次。
  因此 **−10.4 pp（逐词累加口径）与 −8.9 pp（消息并集口径）都成立，不是「作废」关系，只是口径不同**。此前把 14.9% 说成「含 `想起` 的并集」是**归因错误**：`想起` 确实不在 `DEQUANT_LEXICON`（属 `KEYWORDS`），但 14.9% 的 10 里没有它；「并 ∪ 想起」也恰好 = 10（那条含「想起」的台词本不在 14 词并集内），**这是巧合，不是 14.9% 的构成原因**。
- **同口径两说（各自成行，主数字用消息并集）**：
  - 14 词**消息并集**命中消息率：**13.4%(9/67) → 4.5%(3/67)，−8.9 pp（主口径）**
  - 14 词**逐词累加**：**10/67 = 14.9% → 3/67 = 4.5%，−10.4 pp**（同批数据另一口径，因上述 1 条台词同含「半袋+上回」而与并集差 1）
  - 旁注（不作主数字）：并集 ∪「想起」= **10/67 → 4/67，14.9% → 6.0%**
- **`KEYWORDS` vs `DEQUANT_LEXICON` 成员差异**：`DEQUANT_LEXICON`（`code/life/agent.py`，14 词）= 半指/一指/两指/三指/第三格/第二格/第一格/半勺/三钱/半袋/半日/上回/上次/上月；`dequant_probe.py` 的 `KEYWORDS` 仅 5 词 = 上回/上次/想起/半指/第三格。⇒ 任何让「想起」参与合计的写法都必须显式标注为旁注。
- **复算命令**（同一条脚本，两臂各跑一次；消息并集口径对 `payload.body` 的 14 词做 `any(word in body)` 计数）：

```
python3 tools/metrics/dequant_probe.py --log v2/evidence/run_dequant_baseline_n8r16_seed42/run.jsonl --out v2/evidence/dequant_probe_baseline_n8r16_seed42.json
python3 tools/metrics/dequant_probe.py --log v2/evidence/run_dequant_on_n8r16_seed42/run.jsonl     --out v2/evidence/dequant_probe_on_n8r16_seed42.json
# 消息并集复核（只读）：OFF 9/67 = 13.4%   ON 3/67 = 4.5%
```

- 独立复核一致性：life-dev、report-writer、leader 三方分别复算得 `OFF 半袋5/上回4/上次1`、`ON 半勺2/半袋1`，与本机一致；词次 10/3、消息并集 9/3、并∪想起 10/4 三组数字均可对上。

### 表 2 首 6 字 Top5

| # | OFF（71a6d74） | ON（3888957） |
|---|---|---|
| 1 | 哎，我这儿正（2） | 你这阵子忙得（2） |
| 2 | 哟，我正给李（2） | 周公文，我这（2） |
| 3 | 紧俏就紧俏吧（2） | 人一静下来，（1） |
| 4 | 这阵子总见你（2） | 作业本我收下（1） |
| 5 | 作文批到哪一（1） | 你给镇公所修（1） |

Top5 两臂**无一条重合**；OFF 的「哎，我这儿正」「哟，我正给…」这类寒暄 + 自我介绍式开头在 ON 臂消失，ON 首句更多是承接对方（「你这阵子忙得」「作业本我收下」）。
⚠️ 说明：此处 Top5 的 count 都是 1–2，属**小样本噪声区间**，只能当定性观察，不能当分布差异证据。

### 与 life-dev 提供的 `dequant_probe_baseline_71a6d74.json`（n16r60，510 条）的关系

life-dev 基线值（510 条）：上回 79.8%、第三格 29.8%、半指 23.7%、上次 6.9%、想起 10.2%、`（把…往…` 24.1%、骨架重复 22.2%。
**这些数字不能与本节表 1 直接比较**：那是 n16r60 的长跑（510 条台词，后半段对话进入「回指/量化」密集区），本节是 n8r16 探针（67 条台词，几乎全在前几轮）。同一份度量脚本、不同尺度下基线差异就有 6.0% vs 79.8%（「上回」），所以：
- 本轮的 pp 变化**只在与 OFF 臂同尺度时有效**（这正是 leader 裁决 A 的原因）；
- 探针尺度下「第三格」「半指」基线即为 0 → 这两个关键词在本尺度**无区分力**，`−0.0 pp` 不代表无效，而是**测不出**。

---

## 8. 真实截图（真跑产物，非示意图）

```
$ python3 tools/metrics/render_shots.py \
    --run-dir v2/evidence/run_dequant_on_n8r16_seed42 \
    --batch-id dequant-20261028 --outdir v2/evidence/dequant_shots --views chat,rhythm
{ "report": "v2/evidence/dequant_shots/render_report_dequant-20261028.json",
  "report_sha256": "3941825c92082c257a58f49bb12652fa77c49bfc75baa3496a2f3d7cff5627d6",
  "threads_json_sha256": "d68096fd8c39f1fe8716491dd0cd71caea18c897b27ec550098909838d1d8404",
  "ok_count": 2, "fail_count": 0, ... }
```

| 视图 | 文件 | PNG sha256 | 字节 | 像素 | 色彩数 |
|---|---|---|---|---|---|
| chat | `v2/evidence/dequant_shots/dequant-20261028-chat-8ebb0475.png` | `6d41020724f2fabb314fef34c254d8472315358aaa167e2a6d5c5f4b6566757e` | 286803 | 1400×900 | 23224 |
| rhythm | `v2/evidence/dequant_shots/dequant-20261028-rhythm-8ebb0475.png` | `9646e158ad3f0b9c61e555b206b2056992db3029ec21b6094317da0fe25ce373` | 271943 | 1300×1050 | 20653 |

- 环境：`playwright` 已装（`/opt/openjiuwen/workswarm-venv/lib/python3.12/site-packages/playwright`）、`chromium` 在 `/usr/bin/chromium-browser`、`~/.cache/ms-playwright/chromium-1217` 存在 → **无需降级，没有缺依赖**。
- 真伪自检：两张 PNG 均非空白（distinct colors 2.3 万 / 2.1 万，尺寸正常），由 Chromium 现场渲染 `threads.json`（sha `d68096fd…`）而来，来源 run 的 `run_sha256=8ebb0475…` 已写进 `render_report.json` 三件套。
- 未做任何拼图、未复用历史旧图。

---

## 9. 已知局限（不得删改）

1. **单 seed / 小样本**：两臂各 67 条 `MSG_*`，1 条 = 1.49 pp；`−8.9 pp`（消息并集，主口径；逐词累加口径 −10.4 pp，两口径均成立，见 §7.1）只是这一个种子上数出来的差，**不作统计断言**，无区间估计、无显著性检验（需要多 seed 重复或 n16r60 主尺度复跑）。
2. **地板效应**：`第三格`/`半指`/`（把…往…`/骨架重复在 n8r16 尺度两臂皆 0，本轮**未能**验证这些病灶在该尺度上的变化。
3. **prompt_hash 零交集只证明「提示词变了」**，不证明「模型一定遵守」；模型遵守与否由 §7 的台词度量承载，二者不可互换。
4. `code/frontend/README.md` 在 ON 分支父提交里比基线新 18 行（D7 文档），不影响运行时，但严格说两臂的「仓库内容」并非只差一个文件，此点如实记录。
5. 事件数两臂略有差异（6052 vs 6047，差 5 条），属不同生成路径下的合法事件流差异，不是丢事件：`wc -l` 与 `meta.events` 两臂均自检一致（`run_batch.sh` exit 3 未触发）。
6. 本轮未验证的东西：去量化指令是否伤到「人际温度/信息量」——需要 judge 维度读数或人工盲评，本报告不做该判断（judge 调用两臂 same 142 次，但未做前后对比分析）。

### 9.7 高优风险：指令可能把「具体记忆引用」一起压掉（**已在 §9 覆盖：本轮未验证**）

leader 提出、life-dev 复核指出的风险：`上回` 6.0%→0.0%、`上次` 1.5%→0.0% 属**绝对归零**级压制，而这两个词本身也是记忆回指词。若下一轮主尺度复跑时 F-6 跨天记忆引用率也归零，那不是「生活气息变好」，而是「居民失忆」——F-6 本来只有 6.4%，归零会是净损失。

为此我补做了一次**只读离线核查**（零跑批、零 LLM，脚本为仓库既有 `tools/f6/f6_metrics.py`，两臂 run.jsonl 直接对跑）：

```
python3 tools/f6/f6_metrics.py \
  --run OFF=v2/evidence/run_dequant_baseline_n8r16_seed42/run.jsonl \
  --run ON=v2/evidence/run_dequant_on_n8r16_seed42/run.jsonl \
  --out v2/evidence/dequant_probe_f6_riskcheck.json \
  --markdown v2/evidence/dequant_probe_f6_riskcheck.md
```

| 指标 | OFF | ON | Δ | 读法 |
|---|---|---|---|---|
| 时间回指率（本地交叉核对，词表含 上次/上回/昨天/那天…） | 7/67 = **10.45%** | 1/67 = **1.49%** | **−8.96 pp** | **支持 leader 的担心方向**：时间/记忆回指词确实被大幅压掉 |
| M-1 跨天记忆引用率（主口径·机会分母，6-gram 与更早一天消息交集） | 1/3 = 33.3% | 1/3 = 33.3% | 0.0 | 分母仅 3 ⇒ **无统计力，不能作为「记忆未受损」的证据** |
| M-1b（全部 day≥1 分母） | 1/19 = 5.26% | 1/19 = 5.26% | 0.0 | 同上，n=19，粒度 5.3 pp |
| M-0 同日对照（期望≈0，用来看 M-1 是否抓到模板） | 2/7 = 28.6% | 0/7 = 0.0% | −28.6 | OFF 侧 28.6% 说明 OFF 臂的所谓「引用」含模板成分 ⇒ 该指标在 n8r16 尺度噪声极大 |
| 带 `memory_refs` 的消息 | 0 | 0 | 0 | 探针尺度根本没产生结构化 memory_refs |
| F-6 官方率 | None | None | — | 需 `--official` 指标 JSON，本轮探针未产出 |

**结论（诚实版）**：风险**方向成立、量级未知**。`时间回指率 −8.96 pp` 是「回指词被压掉」的直接读数；但「这些回指原本是否承载真实跨天记忆」在 n8r16 探针上**无法判定**（M-1 机会分母只有 3 条消息、M-1b n=19，且 OFF 侧同日对照 28.6% 表明指标本身在此尺度不可靠）。
⇒ 因此该风险**不能写成「已排除」**；本轮交付只能写「已在 §9.7 明确覆盖为未验证风险，并给出下一轮的验证要求」（见下）。

**给下一轮的硬性要求（建议 leader 采纳）**：
1. 主尺度（n16r60）+ 多 seed 复跑，同时报 F-6 官方率与 M-1/M-1b，判定标准预先登记：「若 F-6 从 ~6.4% 掉到 ≤1%（或相对降幅 >50%），判定本臂伤记忆，打回」；
2. 词表扩容：把 `半勺`（本轮 ON 新增）+3.0 pp 这类**同族换词**纳入黑名单或单独成列，否则「压了 A 词换成 B 词」会被误判成「问题已解决」；
3. 对照臂建议加一个「只压量化词、保留回指词」的第三条提示词变体，才能把「压量化词」和「压记忆回指」两个作用分开——当前单变量设计**无法区分**这两者。

---

## 10. 产物路径清单（供 report-writer 收口）

```
reports/dequant-probe-20261028.md                                  ← 本报告
v2/evidence/run_dequant_baseline_n8r16_seed42/{run.jsonl,meta.json} ← OFF 臂（code_sha 71a6d74）
v2/evidence/run_dequant_on_n8r16_seed42/{run.jsonl,meta.json}       ← ON 臂（code_sha 3888957）
v2/evidence/run_dequant_on_n8r16_seed42/launch_env.txt              ← export LIFE_PROMPT_DEQUANT=1 + 起跑命令 + sha256
v2/evidence/run_dequant_on_n8r16_seed42/llmcost_raw.txt             ← obs llm-cost 原始输出
v2/evidence/run_dequant_on_n8r16_seed42/prompt_hash_compare.txt     ← 开臂生效证据（交集 0）
v2/evidence/dequant_probe_baseline_n8r16_seed42.json                ← OFF 指标
v2/evidence/dequant_probe_on_n8r16_seed42.json                      ← ON 指标
v2/evidence/dequant_probe_f6_riskcheck.{json,md}                    ← §9.7 记忆压制风险离线核查（只读，零跑批）
v2/evidence/dequant_shots/dequant-20261028-{chat,rhythm}-8ebb0475.png
v2/evidence/dequant_shots/render_report_dequant-20261028.json       ← 截图三件套（来源/命令/日志 sha）
.worktrees/dequant-baseline-71a6d74/                                ← OFF 隔离检出（detached 71a6d74）
.worktrees/dequant-on/                                              ← ON 隔离检出（verify/dequant-on → 3888957）
```

隔离检出与临时分支 `verify/dequant-on`、兜底提交 `65dd688` 均**未 push**、不影响主干；由 report-writer 决定是否清理。
