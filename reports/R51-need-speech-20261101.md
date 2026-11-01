# R51 · 居民对话「需求的人话化 + 紧迫门控」——`HITT_NEED_SPEECH` 同树同 seed 两臂对照

- 报告人：`town-engineer`（小镇实现工程师）｜出数时刻：2026-11-01 23:0x +08:00
- 分支：`feat/r51-need-speech`（从 `82bdb3f` 新建；**master 未动**）
- 预登记：`reports/R51-prereg-need-speech-20261101.md`，**跑批前**已入库，commit **`61850ba`**（22:05:09）
- 实现 commit：**`95f2194`**（`code/life/agent.py` + `code/tests/test_r51_need_speech.py` + `tools/r51/prompt_hash_probe.py`）
- 工具 commit：**`815d9ba`**（`tools/r51/{launch_arm.sh,arm_inner.sh}`）
- 两臂数据（`run.jsonl` 不入库，`.gitignore` 的 `**/*.jsonl`；以 sha256 为身份）：
  - OFF：`v2/evidence/r51-need-speech-off-20261101_n16r24_s42/`，`run.jsonl sha256 = b3955bee94905f0b9f063dd946d4f72a019fac0ecf982b91613eeea7566cfcf1`
  - ON ：`v2/evidence/r51-need-speech-on-20261101_n16r24_s42/`，`run.jsonl sha256 = 1b79cd2dce78093a08e69172bd2641178c97ced2fe74e6e0c2b660c74a64deb1`
- 两臂实测 `code_sha`：**`815d9ba`**（`env_manifest.txt` / `frozen_sha.txt` / `host.log` 三处一致）

---

## 1. 本节目标（只推进这一个维度）

把提示词里"机器口径的最紧需求"换成人话，并且**只在需求真紧迫时才进提示词**。

问题定性（预登记 §0 已冻结，此处只复述事实）：

| 事实 | 出处 |
|---|---|
| `_mood_line()` **无条件**把 `最紧的需求：{dim}={val}` 拼进两个提示词装配点 | `code/life/agent.py:1566-1572` / 装配点 `:1859` / `:1882` |
| 191 条对话 100% 带 `ctx.need`，其中 **36.65%** 的值 ≥40（未到紧迫）却照样进提示词 | R49-off 冻结批复算（本报告 §2） |
| 对话正文里疲劳族语汇只有 **1.05%** | 同上 |

---

## 2. 零成本基线（跑前、不花 LLM；命令原文 + 输出）

```bash
python3 tools/metrics/need_to_speech.py \
    --log v2/evidence/r49-diversity-off-20261101_n16r24_s42/run.jsonl --label r49-off --mde
# → n_msgs=191 n_with_need=191 noise_inject=70/70 urgent_keep=121/121 fatigue=2/191 food=52/191
# → mde={"fatigue_hit": 5.47, "food_hit": 13.59}
```

| 读数（R49-off，n=191） | 值 |
|---|---|
| `need_inject_rate` | 191/191 = 100% |
| `noise_need_rate`（≥40） | 70/191 = 36.65% |
| `urgent_need_rate`（<40） | 121/191 = 63.35% |
| `fatigue_hit` | 2/191 = 1.05% ｜ Wilson95 [0.29, 3.74] |
| `food_hit` | 52/191 = 27.23% |

⇒ 基线决定了两件事：**门控读数必然落到 0%**（只能当机制闸）、**疲劳族分母极小 ⇒ MDE = 5.47pp**（只能按 MDE 判，不许写"趋势为正"）。

---

## 3. 改动点（逐字冻结，单点改动）

`code/life/agent.py`（commit `95f2194`）：

| 位置 | 内容 |
|---|---|
| 模块级 | `NEED_SPEECH_ENV = "HITT_NEED_SPEECH"`、`NEED_SPEECH_URGENT = 40`（与 `DT.mood_label` 同源）、`NEED_SPEECH_PHRASES`（6 维 × 3 条冻结短语）、`NEED_SPEECH_FALLBACK`、`need_speech_enabled()` |
| `_mood_line()` | OFF：`情绪：{mood}；最紧的需求：{dim}={val}`（**与改前逐字节相同**，且不写审计字段）<br>ON·`val≥40`：`情绪：{mood}`（需求整段不出现）<br>ON·`val<40`：`情绪：{mood}；{人话短语}`（机器口径 `dim=val` 不进提示词）<br>短语按确定性计数器轮换（避免 191 条都写"我饿了"） |
| `_ctx_snapshot()` | **additive 审计键** `ctx.need_speech = {dim, value, injected}`，**仅 ON 出现**（OFF ⇒ 键不出现 ⇒ payload 逐字节不变） |

> 审计键是"必要的最小配套"：提示词原文**不落盘**（`LLM_CALL.payload` 只有 `prompt_hash`），
> 没有这个键，"噪声需求注入率"就只能靠结构推断、无法观测。先例：`ctx.memory_refs` / `ctx.dequp` / `ctx.l7struct`。

---

## 4. OFF 逐字节等价正明（提示词不落盘，只能在函数目录上证）

### 4.1 现场指纹（`tools/r51/prompt_hash_probe.py`，零 LLM，固定夹具）

夹具：`personas.json` 的 `P001` + 三组固定 needs（`urgent` 有一维 12 / `noise` 全维 ≥40 / `empty` 无需求），
`LIFE_PROMPT_NARRATION=0` 钉死旁白通道。

| 态 | `urgent` 的 `mood_line` | `urgent` dialogue / reply sha256 前 8 | `noise` dialogue / reply 前 8 |
|---|---|---|---|
| **改动前**（`61850ba`，改动未落盘） | `情绪：饥饿；最紧的需求：satiety=12` | `57223672` / `4faaa73c` | `60b1aa5b` / `9727cca7` |
| **改动后 OFF**（`HITT_NEED_SPEECH` 不设） | `情绪：饥饿；最紧的需求：satiety=12` | `57223672` / `4faaa73c` | `60b1aa5b` / `9727cca7` |
| **改动后 ON**（`=1`） | `情绪：饥饿；肚子空得发慌，晌午忙到现在没顾上吃` | `4959f9cb` / `d6c0fa2c` | `4c191eae` / `413f5c38`（= `empty` 夹具，需求整段不出现） |

- **OFF == 改动前**：三组夹具 × 两条装配点 × `ctx` 指纹**全部逐字节相等**（`prompt_hashes_pre_change.json` vs `prompt_hashes_off.json`）。
- **ON 仅差需求那一段**：把 ON 提示词里的 `情绪：…` 段换回 OFF 的同一段，即逐字节回到 OFF 提示词（单测断言 C）。
- 指纹文件入库：`v2/evidence/r51-need-speech/prompt_hashes_{pre_change,off,on}.json`。

### 4.2 单测（14 条断言全绿）

```bash
cd code && python3 -m pytest tests/test_r51_need_speech.py -q      # → 14 passed
cd code && python3 -m pytest tests/test_gossip_g1_prompt_single_variable.py tests/test_r51_need_speech.py -q   # → 21 passed
cd code && python3 -m pytest life/tests/test_scene_anchor.py life/tests/test_narration_toggle.py tests/test_life_narration_rotation.py -q  # → 62 passed
```

覆盖：开关真值集｜OFF 与"改前逻辑逐字重构"两条装配点逐字节相等｜OFF 指纹 == **改动前本机实测冻结 sha**
（改一个空格即红）｜ON 单变量替换｜门控方向（≥40 不出现 / <40 出现且无 `dim=val`）｜
ON 不紧迫提示词 == "无需求"提示词｜词表外维度走人话兜底｜审计键与门控一致｜轮换确定性（同 run 同序列、3 条轮换）。

---

## 5. 两臂读数（分母 + Wilson95 + Fisher 双侧）

**两臂除一个变量外逐字相同**（`HITT_LLM_PROVIDER=openai_compat`、`HITT_WORLD_SEED=42`、`--seed 42 --agents 16 --rounds 24 --flush-every 2`）；
**唯一差异 = ON 臂 `HITT_NEED_SPEECH=1`**（见两臂 `env_manifest.txt`）。

| 指标 | OFF（n=191） | ON（n=191） | Δ | Fisher 双侧 p |
|---|---|---|---|---|
| **`noise_inject_rate`（M1）** | 69/69 = **100%** ｜[94.73, 100] | 0/69 = **0%** ｜[0, 5.27] | **−100.00pp** | `0.0`（超几何下极端表） |
| **`urgent_keep_rate`（M1）** | 122/122 = **100%** ｜[96.95, 100] | 122/122 = **100%** ｜[96.95, 100] | +0.00pp | `1.0` |
| **`fatigue_hit`（E1）** | 2/191 = **1.05%** ｜[0.29, 3.74] | 6/191 = **3.14%** ｜[1.45, 6.68] | **+2.09pp** | `0.2839` |
| `food_hit`（E2，只描述） | 41/191 = 21.47% ｜[16.24, 27.82] | 54/191 = 28.27% ｜[22.36, 35.04] | +6.81pp | `0.1553` |
| `fatigue_or_food_hit`（描述） | 43/191 = 22.51% | 60/191 = 31.41% | +8.90pp | — |

复算命令（本表每个数字都能重算）：

```bash
python3 tools/metrics/need_to_speech.py \
  --compare-off v2/evidence/r51-need-speech-off-20261101_n16r24_s42/run.jsonl \
  --compare-on  v2/evidence/r51-need-speech-on-20261101_n16r24_s42/run.jsonl \
  --out-json v2/evidence/r51-need-speech-compare-20261101.json
# → noise_inject_rate 100%→0%（p=0.0）；urgent_keep 100%→100%；fatigue 1.05%→3.14%（Δ+2.09pp, p=0.2839）
# → verdict={"E1": "not_achieved", "M1": "pass", "U1": "ok"}
```

**单变量旁证（世界态未被改动）**：两臂的最紧需求维度分布**逐项相同**
（`leisure 78 / satiety 73 / social 24 / esteem 13 / mastery 3`）、情绪标签分布**逐项相同**
（`平和 69 / 饥饿 68 / 紧绷 43 / 孤单 11`）、`need` 值 `min 0 / median 32 / max 58` 相同。
⇒ ON 臂只改了提示词文本，没有改世界态、没有改随机数消费（世界演化两臂一致）。

---

## 6. 判据满足情况（机械对照预登记，**不改判**）

| 编号 | 预登记达标线（`61850ba` 冻结） | 实测 | 判定 |
|---|---|---|---|
| **M1（机制闸）** | ON `noise_inject_rate ≤ 1.0%` **且** `urgent_keep_rate ≥ 99.0%` | 0% / 100% | ✅ **pass（机制已接通）** |
| **E1（主效果）** | `fatigue_hit` Δ ≥ **+5.5pp**（=MDE 5.47）且 Fisher `p < 0.05` | Δ = **+2.09pp**，`p = 0.2839` | ❌ **未达成** |
| E2（次） | 只描述 | +6.81pp, `p=0.1553` | — 不作判据 |
| E3 | 只描述 | 两臂世界态分布逐项相同 | — 不作判据 |
| U1 | 每臂 `n_msgs ≥ 160` | 191 / 191 | ok |
| U2 | `llm-cost --require-provider openai_compat` 通过、`degraded=0` | 两臂 `ok=true`、`degraded=0` | ok |
| U5 | 接线：OFF 逐字节等价 + ON/OFF 提示词只差需求段 | §4.1/§4.2 全绿 | ok |
| U6 | `rc=0` 且 `wc -l == meta.events` | 33843=33843 / 33857=33857 | ok |

**结论（按预登记只能写到这一档）**：
① **机制接通 = 成立**（门控按设计生效、真紧迫一条没漏、OFF 逐字节不变）；
② **效果未达成**（疲劳族 1.05% → 3.14%，Δ +2.09pp **低于 MDE 5.47pp**，Fisher p=0.2839 不显著）。

> **不夸大**：这不是"有效"，也不是"有正向趋势"——按预登记 U4，低于 MDE 一律写「不可判/未达成」。
> 以观测到的 +2.09pp 为真效应反解，**每臂需要 ≈ 733 条对话**（当前 191）才能在 α=.05/power=.80 下检出；
> 即本轮的样本量**结构上不足以判 E1**，而"未达成"本身就是本轮的有效结论之一（说明清掉噪声、换成人话，
> 并**不足以**把"累/困"推成对话里的常规语汇）。

---

## 7. 未预注册观察（单列，**不得作为结论、不进判据**）

1. **6 条疲劳族命中全部落在 `injected=true` 的消息上**（`leisure` 38/37/32/39/10 与 `satiety` 8）。
   这是"人话被采纳"的**弱旁证**，但 n=6，且 OFF 臂那 2 条命中的 need 是 45/49（**未达紧迫**），
   说明"累/困"本来也会从他处冒出来（干活的动作旁白）。**不构成因果证据**。
2. **饮食族 +6.81pp（`p=0.1553`）** 比疲劳族变化更大，方向与"饥饿人话化"一致，但 `satiety` 本来
   就是最紧需求 73 次，中文里"吃/饭/茶"极容易被非需求语境触发 ⇒ 预登记已把它排除在判据外。
3. **`noise_need_rate` 两臂完全相同（69/191）**：说明"清掉噪声注入"没有反作用到世界态
   （需求演化仍按原样走），也正是单变量设计的预期。
4. OFF 臂（`815d9ba`）与 R49-off（`161f115`）同 seed 同参数但读数略有差异
   （噪声 69 vs 70、`fatigue_hit` 2 vs 2、`food_hit` 41 vs 52）⇒ **真 LLM 的非确定性**，
   两臂比较只能用**本轮同批**，不得跨批混算（沿用 R49 §10 纪律）。

---

## 8. 真 LLM 证据（门禁原文 + provider + 成本）

```bash
cd code && python3 -m obs llm-cost --log ../v2/evidence/r51-need-speech-<arm>-20261101_n16r24_s42/run.jsonl \
    --require-provider openai_compat
```

| 项 | OFF 臂 | ON 臂 |
|---|---|---|
| `provider_guard.ok` | **true** | **true** |
| `by_provider` | `{"openai_compat": 2252}` | `{"openai_compat": 2252}` |
| `total.degraded` | **0** | **0** |
| `total.calls` | 2252 | 2252 |
| `tokens_in / tokens_out / tokens_total` | 161636 / 160118 / **321754** | 161187 / 155817 / **317004** |
| `dialogue` 用途 | calls 191、degraded 0、in 62249 / out 9808 | calls 191、degraded 0、in 61923 / out 9691 |
| `duration_sec` | 1337（22.3 min） | 1325（22.1 min） |
| `run_batch.rc` | 0 | 0 |
| `wc -l` vs `meta.events` | 33843 = 33843 | 33857 = 33857 |

> **degraded = 0（两臂）**，无 mock 混入，`by_purpose` 六项均走真 provider。两臂总 tokens ≈ 63.9 万。

---

## 9. 截图三件套（本轮现渲，禁拼图 / 禁复用旧图）

```bash
python3 tools/metrics/render_shots.py --run-dir v2/evidence/r51-need-speech-off-20261101_n16r24_s42 \
    --batch-id R51-off --outdir v2/evidence/r51-off_shots
python3 tools/metrics/render_shots.py --run-dir v2/evidence/r51-need-speech-on-20261101_n16r24_s42 \
    --batch-id R51-on  --outdir v2/evidence/r51-on_shots
```

| 图 | 路径 | 校验 |
|---|---|---|
| OFF·chat | `v2/evidence/r51-off_shots/R51-off-chat-b3955bee.png` | `log_sha256=b3955bee9490`、`run_sha256_in_threads=b3955bee9490`、`fail_count=0` |
| OFF·rhythm | `v2/evidence/r51-off_shots/R51-off-rhythm-b3955bee.png` | 同上 |
| ON·chat | `v2/evidence/r51-on_shots/R51-on-chat-1b79cd2d.png` | `log_sha256=1b79cd2dce78`、`run_sha256_in_threads=1b79cd2dce78`、`fail_count=0` |
| ON·rhythm | `v2/evidence/r51-on_shots/R51-on-rhythm-1b79cd2d.png` | 同上 |

两张 chat 图的文件名里带的 `sha8` 就是**本次 run.jsonl 的前 8 位**，可反向核对没有被旧图顶替
（`render_report_R51-{off,on}.json` 内 `run_sha256_in_threads` 与 `run.jsonl` 实测 sha256 前缀一致）。

---

## 10. 三档口径声明（只取实际达到的那一档）

| 档 | 本轮 | 依据 |
|---|---|---|
| ① **机制接通** | ✅ **成立** | M1 pass（噪声注入 100%→0%、真紧迫保留 100%）+ OFF 逐字节等价（§4）+ `HITT_NEED_SPEECH=1` 见于 ON 臂 `env_manifest.txt` |
| ② **效果成立** | ❌ **未达成** | E1 Δ=+2.09pp < MDE 5.47pp，`p=0.2839` |
| ③ **生活气息提升** | **不判**（预登记即排除） | 无人工盲评 / 无 judge 语义维度 / 无跨 seed 复现 |

**禁止表述**：不得写成"对话更像真人""生活气息提升"，也不得写成"有正向趋势"——按预登记 U4，低于 MDE = 不可判。

---

## 11. 局限与未解决

1. **样本量不足**：`n=191/臂` 对 1% 量级的基线只能检出 ≥5.47pp 的变化；观测效应 +2.09pp 需要 ≈733 条/臂。
   下一轮若仍要判这条臂，**必须把对话量抬到 ≥800/臂**（例：`--rounds 96`，成本 ≈ 4×）。
2. **提示词不落盘**：只能靠单测 + 指纹探针证明 OFF 等价、ON 单点插入；**无法**从 run.jsonl 回读模型真正看到的文本。
3. **"人话短语"本身的语义准确度未评估**：例如 `leisure=10` 时给"闷得发慌，想寻点乐子"是合理的，
   但 `leisure=38` 也给同一批短语 ⇒ 强度不分级。下一轮可考虑**按值分档**（如 `<20 / 20–39` 两档短语），
   但那会引入第二个变量（阈值之外的新自由度），需重新预登记。
4. **轮换计数器是进程内状态**：同一 agent 在同一次运行内短语轮换确定可复现，但**跨 run** 不保证对齐；
   两臂比较的是**分布**而非逐条对应，因此不影响判据。
5. **只覆盖提示词层**：本轮没有动"需求 → 行为"的映射（例如让 `energy` 真的成为最紧需求），
   而基线里 `energy` 一次都没成为最紧需求 ⇒ "累/困"缺的其实是**世界态供给**，不是提示词措辞。
   **这才是本轮"未达成"的最可能原因**（见 §12 建议 1）。

---

## 12. 下一轮建议（按性价比排序）

1. **先查 `energy` 为何永不为最紧**：六维里 `energy` 在 191 条里 0 次成为最紧需求。
   若需求衰减速率/阈值使 `energy` 恒高于其它维，那么"累/困"进不了对话的**根因在世界态**，
   提示词层怎么改都不会有大效果。**零 LLM 就能查**（`run.jsonl` 的 NEED 事件轨迹），建议先做这个。
2. **短语按值分档**（`<20 / 20–39`），并单独预登记；预期只影响"强度表达"，不改门控。
3. **扩样本到 ≥800/臂**再判 E1；否则每轮都会落到"不可判"，重复消耗 64 万 tokens。
4. 若仍要跑提示词层实验，改用**judge 语义维度**（是否出现"自身的疲惫/心情"）而非词表命中，
   词表命中对中文同义表达太窄（"乏"、“没劲”、“撑不住”都要一条条补）。

---

## 13. 复算命令清单（一次性复现本报告全部数字）

```bash
# 0) 前置：确认两臂 rc=0 且行数对账
cat v2/evidence/r51-need-speech-off-20261101_n16r24_s42/run_batch.rc    # 0
cat v2/evidence/r51-need-speech-on-20261101_n16r24_s42/run_batch.rc     # 0
wc -l v2/evidence/r51-need-speech-{off,on}-20261101_n16r24_s42/run.jsonl
sha256sum v2/evidence/r51-need-speech-{off,on}-20261101_n16r24_s42/run.jsonl

# 1) 零成本基线（R49-off 冻结批）
python3 tools/metrics/need_to_speech.py --log v2/evidence/r49-diversity-off-20261101_n16r24_s42/run.jsonl --label r49-off --mde

# 2) 两臂单臂读数
python3 tools/metrics/need_to_speech.py --log v2/evidence/r51-need-speech-off-20261101_n16r24_s42/run.jsonl --label r51-off \
    --out-json v2/evidence/r51-need-speech/r51_readings_off.json
python3 tools/metrics/need_to_speech.py --log v2/evidence/r51-need-speech-on-20261101_n16r24_s42/run.jsonl --label r51-on \
    --out-json v2/evidence/r51-need-speech/r51_readings_on.json

# 3) 两臂对照（Fisher + 与预登记阈值机械比对）
python3 tools/metrics/need_to_speech.py \
    --compare-off v2/evidence/r51-need-speech-off-20261101_n16r24_s42/run.jsonl \
    --compare-on  v2/evidence/r51-need-speech-on-20261101_n16r24_s42/run.jsonl \
    --out-json v2/evidence/r51-need-speech-compare-20261101.json

# 4) 真 LLM 验真（在 code/ 下执行）
cd code && python3 -m obs llm-cost --log ../v2/evidence/r51-need-speech-off-20261101_n16r24_s42/run.jsonl --require-provider openai_compat
cd code && python3 -m obs llm-cost --log ../v2/evidence/r51-need-speech-on-20261101_n16r24_s42/run.jsonl  --require-provider openai_compat

# 5) OFF 逐字节等价（提示词指纹）
python3 tools/r51/prompt_hash_probe.py --label post-change-off --out-json /tmp/probe_off.json
python3 -c "import json;a=json.load(open('v2/evidence/r51-need-speech/prompt_hashes_pre_change.json'));b=json.load(open('/tmp/probe_off.json'));a.pop('label');b.pop('label');print('OFF==PRE:',json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True))"
HITT_NEED_SPEECH=1 python3 tools/r51/prompt_hash_probe.py --label post-change-on --out-json /tmp/probe_on.json

# 6) 单测
cd code && python3 -m pytest tests/test_r51_need_speech.py -q      # 14 passed

# 7) 截图（现渲，禁复用）
python3 tools/metrics/render_shots.py --run-dir v2/evidence/r51-need-speech-off-20261101_n16r24_s42 --batch-id R51-off --outdir v2/evidence/r51-off_shots
python3 tools/metrics/render_shots.py --run-dir v2/evidence/r51-need-speech-on-20261101_n16r24_s42  --batch-id R51-on  --outdir v2/evidence/r51-on_shots
```
