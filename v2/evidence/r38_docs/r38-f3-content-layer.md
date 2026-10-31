# R38 · F-3 情绪呼应：OFF/ON 双臂真跑 + 内容层读数（含尺子缺陷诊断）

- 任务：`f3-batch`（跑批执行专家 exp-runner）
- 生成时间：2026-10-31T12:3x +08:00
- 基线：`afde63cebe3d25c0836ce4974047d9dafefe4070`（分支 `feat/f3-emotion-echo-r38`）
  **本分支落后 `origin/master` 4 条，本轮按裁决钉基线，未 merge / 未切分支 / 未 rebase。**
- 结论一句话：**F-3 内容层仍不可判（分母 7 / 4，band=count_only），不得据此判有效或无效；机制层给出可判的非零读数（echo 行 0 → 110）；不可判的主因是 r24 规格下相邻回复对天然稀少（分母中位 6.5），词表精度只是二阶放大项。**

---

## 1. 前置确认（原始输出存证）

文件：`v2/evidence/r38_f3_batch/preflight.txt`（12:02:54 采集）

```
--- pgrep -af 'orchestration run' ---   (空)
--- pgrep -af run_batch ---             (空)
--- check_clean_tree ---                "verdict": "PASS", blocking: []
--- git HEAD ---                        afde63cebe3d25c0836ce4974047d9dafefe4070 / feat/f3-emotion-echo-r38
```

跑后复核（两臂均已收工）：`check_clean_tree.py` → `verdict=PASS blocking=[] head=afde63c`；
`git status --short -- code/life code/orchestration code/config code/engine` → **0 行**。冻结区全程未动。

---

## 2. 两臂落点、命令原文、时间戳、世代

| 项 | OFF | ON |
|---|---|---|
| 目录（绝对） | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/r38_f3_batch/off` | `…/v2/evidence/r38_f3_batch/on` |
| side_root（绝对） | `/tmp/r38_f3_side_off_fresh`（本轮新建） | `/tmp/r38_f3_side_on`（该臂起跑时新建） |
| 起跑前缓存计数原文 | `side_root=/tmp/r38_f3_side_off_fresh cache_files_before=0` | `freeze_cache` 目录 mtime=10:50:16 == 起跑时刻；首份 responses 写入 10:50:19 |
| 起止 ISO | `2026-10-31T12:05:02` → `2026-10-31T12:26:38`（1296s） | `2026-10-31T10:50:15` → `2026-10-31T11:14:49`（1472s） |
| rc | **0** | **0** |
| rc 文件 | `off/run_batch.rc`（mtime 12:26:38.98） | `on/run_batch.rc`（mtime 11:14:49.42） |
| events == wc -l | `33873 == 33873` | `33853 == 33853` |
| run.jsonl sha256 | `6d06506fb3c8b7e062b57540c1f3248325b140a0e3b48ad4fe75a84c03f83f6b` | `af120876cd314b8f1b31a3f380081374da1c32db863ae4c1c21854bc16410a7f` |
| code_sha / provider / spec | `afde63ce` / `openai_compat` / seed 42 · n16 · r24 | 同 |
| 开关实测 | `effective=off, declared_on=False, ctx_echo_msgs=0` | `effective=on, declared_on=True, ctx_echo_msgs=110`（全为 MSG_DM） |

两臂启动命令（逐 token 对比，差异仅 `env HITT_DIALOGUE_EMOTION_ECHO=1` 与 side-root）：

```
# OFF（无开关变量，unset）
bash tools/d2/run_batch.sh --out-dir v2/evidence/r38_f3_batch/off \
  --seed 42 --agents 16 --rounds 24 --side-root /tmp/r38_f3_side_off_fresh
# ON（仅加一个开关）
env HITT_DIALOGUE_EMOTION_ECHO=1 bash tools/d2/run_batch.sh --out-dir v2/evidence/r38_f3_batch/on \
  --seed 42 --agents 16 --rounds 24 --side-root /tmp/r38_f3_side_on
```

补充说明：`tools/d2/run_batch.sh` 内部自行 `export HITT_LLM_PROVIDER=openai_compat` 并 source `code/.env.local`，两臂一致。

### 2.1 两臂并排总表（**本项目第一对同 sha `afde63c` 的 R38 有效双臂**）

| 列 | OFF | ON |
|---|---|---|
| code_sha（起跑=跑完） | `afde63cebe3d25c0836ce4974047d9dafefe4070` | 同（两臂同 HEAD） |
| rc | **0** | **0** |
| 起止 ISO | 12:05:02 → 12:26:38 | 10:50:15 → 11:14:49 |
| duration | 1294s（meta.duration_sec） | 1472s |
| events == wc -l | **33873 == 33873** | **33853 == 33853** |
| run.jsonl sha256 | `6d06506fb3c8b7e062b57540c1f3248325b140a0e3b48ad4fe75a84c03f83f6b` | `af120876cd314b8f1b31a3f380081374da1c32db863ae4c1c21854bc16410a7f` |
| total calls | 2252 | 2252 |
| total tokens_in | **161581** | **164970** |
| total tokens_out | **148840** | **153152** |
| degraded | **0** | **0** |
| provider_guard.ok | true（`{openai_compat:2252}`, `problems=[]`） | true（同） |
| **dialogue 桶** calls/cached/tin/tout | **191 / 0 / 62224 / 10019** | **191 / 0 / 65747 / 9731** |
| 全局 cached（仅 importance 批内去重） | 1387 | 1387 |
| 开关实测 | `effective=off, ctx_echo_msgs=0` | `effective=on, ctx_echo_msgs=110` |
ON 臂原始时间线留证：`v2/evidence/r38_f3_batch/timeline_on_1144_raw.txt`；OFF 重跑时间线：`timeline_off_rerun.txt`。

> 命名约定：本轮起 rc 统一落在 `<batch>/<arm>/run_batch.rc`。OFF 的 rc 原由驱动脚本写为批根 `off.rc`，收工后 `mv` 进 `off/run_batch.rc`（`mv` 保留 mtime 12:26:38.98 > run.jsonl 12:26:37.20）。批根曾有 `on.rc=9`，那是 12:03 我的失败启动态（见 §3），其原文与 mtime 已记入 `INVALID_RUN_NOTE.md` 后删除。

---

## 3. 一次作废跑与其根因（必须写进结论）

`v2/evidence/r38_f3_batch/off_INVALID_cached_replay/`（含 `WHY.md`）+ `INVALID_RUN_NOTE.md`。

- 12:03 我首次起 OFF 时使用了 `/tmp/r38_f3_side_off`（**10:21 旧尝试遗留目录**，其 `freeze_cache/responses` 内有 **865** 份响应）。
- 结果：`run_batch` rc=0、`provider_guard.ok=true`，但 **`cached=calls=2252`、`tokens_in=tokens_out=0`** ⇒ 零真实调用，**不构成真跑**，整目录作废留证，不进任何读数。
- 机制出处：`code/orchestration/integration.py:1004` 把 freeze 缓存目录定为 `<side_root>/freeze_cache`；`code/freeze/llm_client.py:306-345` 命中即返回 `cached=True`、`tokens_in/out=0`。命中键只看 `prompt_hash + model + tier + params`，与 side_root 无关 ⇒ 同 seed 同 spec + 旧缓存 = 100% 命中。
- 计数口径澄清：865 = `<side_root>/freeze_cache/responses` 下文件数；1290 = `freeze_cache/` 下**全部**文件数（含 `judgments/`、`embeddings/`）。**报告一律引 865。**
- 12:02 那次 `ON 臂 rc=9`：preflight 并发闸自匹配（我的监控命令行里含字面 `run_batch`，被 `pgrep -f` 命中），非真实并发；已改监控写法。

---

## 4. llm-cost 验真（两臂，原始输出已落盘）

命令（**必须 cd code**，否则 ModuleNotFoundError；`obs llm-cost` 只有 `--log`，无位置参数）：

```
cd code && python3 -m obs llm-cost --log ../v2/evidence/r38_f3_batch/off/run.jsonl \
  --require-provider openai_compat --out ../v2/evidence/r38_f3_batch/off/llm_cost.json > ../v2/evidence/r38_f3_batch/off/llm_cost.txt 2>&1
# ON 同命令换 on/ 路径
```

| 臂 | rc | provider_guard.ok | calls | tokens_in | tokens_out | degraded | 全局 cached |
|---|---|---|---|---|---|---|---|
| OFF | 0 | true | 2252 | **161581** | **148840** | **0** | 1387 |
| ON | 0 | true | 2252 | **164970** | **153152** | **0** | 1387 |

按 leader 修正后的**两条并列判据**（不再用全局 cached=0，避免误杀合法的批内同 prompt 去重）：

**① F-3 判据桶（dialogue）纯真生成 —— 两臂均过**

| 臂 | dialogue calls | dialogue cached | tokens_in | tokens_out | degraded |
|---|---|---|---|---|---|
| OFF | 191 | **0** | **62224** | **10019** | 0 |
| ON | 191 | **0** | **65747** | **9731** | 0 |

**② side_root 的 `freeze_cache/responses` 文件 mtime 全部落在本次 `[started_at, finished_at]` 窗口 —— 两臂均过**

| 臂 | responses 数 | min mtime | max mtime | 窗口 | 窗口外文件数 |
|---|---|---|---|---|---|
| OFF | 865 | 12:05:06 | 12:26:33 | [12:05:03, 12:26:37] | **0**（all_inside=True） |
| ON | 865 | 10:50:19 | 11:14:44 | [10:50:16, 11:14:48] | **0**（all_inside=True） |

**关于 1387 cached 的性质（务必保留此区分）**：两臂 identical 的 1387 次全部落在 `importance` 桶（calls 1523），是**同一批次内不同 agent 提问文本完全相同造成的合法去重**，不是跨批回放。判据：`importance` 的 `tokens_in=2312 > 0`（仍有真实计费），且两臂 cached 数完全相同、与 batch 内容无关；其余桶（dialogue/judge/reflect/plan/negotiation）cached 全为 0。

---

## 5. F-3 内容层读数（主口径 = `reply_path` + `loose`）

命令：

```
python3 v2/evidence/f3_audit_echo.py \
  --off v2/evidence/r38_f3_batch/off/run.jsonl \
  --on  v2/evidence/r38_f3_batch/on/run.jsonl \
  --out-json v2/evidence/r38_f3_batch/f3_audit_echo.json
# 原始 stdout：v2/evidence/r38_f3_batch/f3_audit_echo.txt（rc=0）
```

| 臂 | sha8 | scope | tier | 事件（分子） | 分母 | Wilson95 | band |
|---|---|---|---|---|---|---|---|
| OFF | 6d06506f | reply_path | **loose（主口径）** | **0** | **7** | [0.0, 0.35433] | count_only |
| ON | af120876 | reply_path | **loose（主口径）** | **0** | **4** | [0.0, 0.489891] | count_only |
| OFF | 6d06506f | reply_path | loose_no_agree | 0 | 7 | [0.0, 0.35433] | count_only |
| ON | af120876 | reply_path | loose_no_agree | 0 | 4 | [0.0, 0.489891] | count_only |
| OFF | 6d06506f | reply_path | polarity_match | 0 | 7 | [0.0, 0.35433] | count_only |
| ON | af120876 | reply_path | polarity_match | 0 | 4 | [0.0, 0.489891] | count_only |
| OFF | 6d06506f | reply_path | marker_based | 0 | 7 | [0.0, 0.35433] | count_only |
| ON | af120876 | reply_path | marker_based | 0 | 4 | [0.0, 0.489891] | count_only |

**读法（全族纪律，硬约束）**：主口径 `reply_path` 上 **OFF 0/7、ON 0/4**，两臂 band 均 `count_only`（分母 < 30）。
⇒ 按全族纪律**只报事件数、不报比率**：`P(分子=0|den=4)=39%`、`P(分子=0|den=3)≈50%`（metrics-analyst 实测），
即「分子为 0」在如此小的分母下**完全是抽样正常**，不携带任何方向性信息。
**禁止**把本结果写成「无情绪呼应」或「F-3 无效」——正确表述是**不可判**。

`all_messages` 口径数值相同（OFF 0/7、ON 0/4）。差值 = 0 − 0 = 0（事件数差，不构成比率差）。

### 裁决：不可判（分母 < 30，band=count_only）

**正确表述 = 不可判。禁止表述为「无情绪呼应」「F-3 无效」「无提升」。** 不是「没有提升」，而是**尺子在本批次上测不出提升**。理由必须连同原始数一起读：

1. **分母极小**：`reply_path` 分母 OFF=7、ON=4。两臂都是 191 条对话、125 条回复路径，但其中只有 4–7 条满足「上一句极性≠0」。
2. **机会密度**（`f3_audit_echo.txt` 原文）：
   - OFF `per_message=0.036649`、`per_round=0.318182`
   - ON `per_message=0.020942`、`per_round=0.181818`
3. **主因 = 规格（样本量），不是尺子常数**（已由 metrics-analyst `f3-ruler-health` 在 108 份语料上实测定论）：
   - 机会密度**随规模单调上升**：n16r24 族 p50 = **0.0288** → 分母 ≥30 的批次达 **0.1147**。本轮 0.0157/0.0209 **只是小规格族的下沿**，不能读成尺子固有机会率。
   - ⇒ **r24 规格下相邻回复对天然稀少（分母中位 6.5），分母不足首先是规格问题**；词表与精度是**二阶放大项，不是主因**。
4. **次因 = 词表精度**：`tools/d5/emotion_lexicon.txt` 共 **18 个极性词**（`sha256=8427245c…`，判定为「子串包含 + 正负计数比较」，见 `f3_audit_echo.py:93-100`）。v2 词表只能让分母 **+34.9%~47%**，在 191 条消息上仍只有约 8 —— 即**扩表也救不到可判门槛**。
5. **第三因素 = 批次构成**：mock 批占 43% 消息且结构性零分母。
6. **本次 0 分子不携带信息**：`P(分子=0|den=4)=39%`、`P(分子=0|den=3)≈50%`（metrics-analyst 实测）⇒ 两臂同时为 0 属抽样正常。
7. **与 R15/R21/R25 同族**：判据设计缺陷第 4 例——**分母路径在小规格下天然稀疏**，属尺子/规格问题，不是生成侧问题。

> 本轮按裁决**不动尺子**：`emotion_lexicon.txt` 一个字未改；未做「临时扩词试跑」。若要改，需预登记后另起对照，不能与本轮两臂混算。

---

## 6. 机制层读数（单列，**不是效果层结论**）

同一份 `f3_audit_echo.txt` 的「机制侧（payload.ctx.echo）」段：

| 臂 | echo_rows | ratio | absent | 顶层 dialogue_echo | src 分布 | tier 分布 | 四档词表接住 | 给了但四档全不命中 |
|---|---|---|---|---|---|---|---|---|
| OFF | **0** | 0.0 | **True**（键完全不存在） | 0 | {} | {} | 0/0/0/0 | 0 |
| ON | **110** | **0.575916** | False | 0 | text 31 / mood 20 / text+mood 58 / cue+mood 1 | 明显 39 / 轻 12 / 很强 59 | 0/0/0/0 | **4** |

- 机制层结论：**ON 臂确实把「情绪呼应提示」接进了对话上下文**（110 行，占 191 条对话的 57.6%），OFF 臂该键结构性不存在（`absent=True`，不是空值）。这是本轮**唯一非零、可判**的 F-3 读数。
- **但不得据此宣称 F-3「有效」**：机制给提示 ≠ LLM 接住。判定器在 `reply_path` 上给出的 4 个「已注入提示」的对中，**四档口径一个都没接住**（`给了但四档全不命中=4`）。这一条独立佐证了 §5 的「问题在判定器/尺子」，而非生成侧没收到信号。

---

## 7. L-7 去重守卫核对（未击穿）

命令：`python3 tools/d5/dialogue_metrics.py --log <arm>/run.jsonl --meta <arm>/meta.json --out-json <arm>/d5_metrics.json`（两臂 rc=0，分母 per_message=191）

| 指标 | OFF | ON | 差 |
|---|---|---|---|
| `L-7_dup_ngram8_rate` | **0.267016** | **0.246073** | **−2.09pp** |
| `L-6_dup_exact_rate` | 0.0 | 0.0 | 0 |

- 判定：**未击穿**。ON 臂重复率不升反降（−2.09pp），两臂均远低于项目已登记的历史目标线（`d12f` 登记 ≤55.10%；本项目 `f3_off_official` 记录 34.71%）。
- 说明：`dialogue_metrics.py` 自身不内置 L-7 的 guard 阈值（该指标只是读数），上述比较用的是项目既有登记线；不得把「未击穿」写成「达标」。

---

## 8. 两臂可比性硬证据：dialogue prompt_hash 重合度

命令（可复算，供报告引用）：

```
python3 v2/evidence/r38_f3_batch/f3_prompt_overlap.py \
  v2/evidence/r38_f3_batch/off/run.jsonl v2/evidence/r38_f3_batch/on/run.jsonl
```

原始输出（`f3_prompt_overlap.txt`）：

```
off dialogue_calls=191 distinct_prompt_hash=191
on  dialogue_calls=191 distinct_prompt_hash=191
intersection=36  |  on_only=155  off_only=155
on_diff_ratio=0.8115 (=|on_only|/on_distinct)
```

- 结论：**交集 36（新 OFF × ON，本轮有效臂对）**，并集 346（191+191−36），ON 侧 **81.15%（155/191）** 的对话提示词与 OFF 不同 ⇒ 从 prompt 内容层面**实证 ON 臂确实改了对话生成输入、OFF 未改**。
- 这比 `engine_version` 指纹可靠：`code/config/emotion_echo.json` 不在 `engine/version.py::FINGERPRINT_FILES` 内，两臂 `engine_version` 指纹**必然相同、不可作为可比性证据**。

> 脚注（口径绑定，防误引）：早前记录的 **38** 是对 `off_INVALID_cached_replay`（12:03 回放件）× ON 算的，**不属有效臂**，仅留作历史；引用时必须绑定文件对，不得与本轮 36 并列而不加区分。

两臂可比性三件同屏声明：
1. 两臂 HEAD 同值：`afde63cebe3d25c0836ce4974047d9dafefe4070`（`meta.code_sha == code_sha_end`）；
2. 启动命令差异仅一个开关：OFF 无 `HITT_DIALOGUE_EMOTION_ECHO`（unset）/ ON `HITT_DIALOGUE_EMOTION_ECHO=1`，其余 `--seed 42 --agents 16 --rounds 24` 相同；
3. 开关实际取值：OFF `effective=off, ctx_echo_msgs=0`；ON `effective=on, ctx_echo_msgs=110`。

---

## 9. 真实截图（4 张，全部通过像素自检）

命令（每臂各一次，只读既有日志，不做拼图、不跨批混拼）：

```
python3 tools/metrics/render_shots.py --run-dir v2/evidence/r38_f3_batch/off \
  --batch-id r38_f3_off --outdir v2/evidence/r38_f3_batch/shots_off --views chat,rhythm
python3 tools/metrics/render_shots.py --run-dir v2/evidence/r38_f3_batch/on \
  --batch-id r38_f3_on --outdir v2/evidence/r38_f3_batch/shots_on --views chat,rhythm
```

| 臂 | 视图 | PNG 绝对路径 | png sha256 前 8 | distinct_colors | top_color_frac | non_bg_frac | 自检 |
|---|---|---|---|---|---|---|---|
| OFF | chat | `…/r38_f3_batch/shots_off/r38_f3_off-chat-6d06506f.png` | 8b282525 | 23497 | 0.1567 | 0.5318 | OK |
| OFF | rhythm | `…/shots_off/r38_f3_off-rhythm-6d06506f.png` | 3f925fb9 | 20765 | 0.3707 | 0.3876 | OK |
| ON | chat | `…/shots_on/r38_f3_on-chat-af120876.png` | 16e5812c | 23399 | 0.1499 | 0.5385 | OK |
| ON | rhythm | `…/shots_on/r38_f3_on-rhythm-af120876.png` | c0a833dc | 20740 | 0.3707 | 0.3875 | OK |

（`…` = `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence`；文件名自带日志 sha8，可溯源到对应 `run.jsonl`。）

render_report 与像素自检原文：
- `v2/evidence/r38_f3_batch/shots_off/render_report_r38_f3_off.json`（ok_count=2, fail_count=0）
- `v2/evidence/r38_f3_batch/shots_on/render_report_r38_f3_on.json`（ok_count=2, fail_count=0）

判据门槛：`distinct_colors ≥ 200`、`top_color_frac ≤ 0.99`、`non_bg_frac ≠ 0` —— 4 张全部满足。

---

## 10. 未解决 / 需下游知晓

1. **10:21 那次 OFF 真跑的日志已被我 12:03 的回放覆盖**。依据：`timeline_on_1144_raw.txt` 显示 `off_start=10:21:41 off_rc=0 off_end=10:48:06`，而 `/tmp/r38_f3_side_off` 的 865 份 responses 全部生成于该窗口 ⇒ 10:21 那次是真跑；12:03 我用同一 `off/` 目录 + 同一 side_root 重跑，命中全部缓存，`run.jsonl` 被覆盖为回放版（现仅存于 `off_INVALID_cached_replay/`，sha `0a2932ed…`）。
   **其内容 = 同 prompt 的确定性复现、不是伪造，但零 token 消耗，故不构成真跑**。本报告全部 OFF 读数取自 12:05 的新跑（sha `6d06506f…`）。10:21 原始日志不可恢复。
2. **F-3 分母不足的处置未落地**：主因是**规格**（n16r24 下分母中位 6.5、机会密度族 p50 0.0288），次因是词表精度（v2 仅 +34.9%~47%）、第三因素是 mock 批占 43% 消息。**任何一项单独修都不足以把分母抬到 ≥30**，需「加大规格 + 扩表 + 去 mock」组合，且必须另行预登记，不能与本轮读数混算。
3. **`importance` 桶 1387 次批内去重**是引擎既有行为（跨 agent 同 prompt），两臂一致；若下游要做「双真跑」严格审计，应对该桶单列说明，不要按全局 cached 判死。

---

## 11. 复算命令汇总（第三方一条命令可重跑）

```
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
cd "$REPO"

# 干净树 + 基线
python3 tools/d5/check_clean_tree.py ; git rev-parse HEAD

# llm-cost（cd code 才能 import obs）
cd code
python3 -m obs llm-cost --log ../v2/evidence/r38_f3_batch/off/run.jsonl --require-provider openai_compat --out /tmp/o.json
python3 -m obs llm-cost --log ../v2/evidence/r38_f3_batch/on/run.jsonl  --require-provider openai_compat --out /tmp/n.json
cd "$REPO"

# F-3 内容层 + 机制层
python3 v2/evidence/f3_audit_echo.py --off v2/evidence/r38_f3_batch/off/run.jsonl \
  --on v2/evidence/r38_f3_batch/on/run.jsonl --out-json /tmp/f3.json

# L-7
python3 tools/d5/dialogue_metrics.py --log v2/evidence/r38_f3_batch/off/run.jsonl --meta v2/evidence/r38_f3_batch/off/meta.json --out-json /tmp/off.json
python3 tools/d5/dialogue_metrics.py --log v2/evidence/r38_f3_batch/on/run.jsonl  --meta v2/evidence/r38_f3_batch/on/meta.json  --out-json /tmp/on.json

# prompt_hash 重合度
python3 v2/evidence/r38_f3_batch/f3_prompt_overlap.py \
  v2/evidence/r38_f3_batch/off/run.jsonl v2/evidence/r38_f3_batch/on/run.jsonl
```

产物 sha256 速查：
- `off/run.jsonl` = `6d06506f…f83f6b`；`on/run.jsonl` = `af120876…c10a7f`
- `f3_audit_echo.json` = `9991af81aab224e45e6305d22eb3584e4a6bd8bfae3d0e865ec7ec11d046d49b`
- `off/llm_cost.json` = `48880111…9936c5`；`on/llm_cost.json` = `5e72b530…6eedf9`
