# R38 / F-3 情绪呼应 —— 实现与离线复算记录（life-dev）

- 分支：`feat/f3-emotion-echo-r38`
- 基线（对齐后 master / origin/master，本地跟踪 ref）：`94e272a1f8858c5a476a286b6a8fe62f34248288`
- 本轮唯一维度：**F-3 情绪呼应**
- 零成本：本记录内所有数字均由**离线回放既有 run.jsonl** 得到，**未起跑批、未调用任何 LLM、零花费**。

## 0. 口径冻结（Leader 裁决第 1 条的执行结果）

要求：实测两个候选，看哪个在基线上跑出 **F-3 = 1/6**；跑得出来的 = 主口径。

| 候选 | 命令 | 基线（v0-anchor `run_d2_before_n16_seed42`，sha8 `c1f86bf6`）结果 | 是否复现 1/6 |
|---|---|---|---|
| `v2/evidence/f3_audit_echo.py` **`all_messages` + `loose` 档** | `python3 v2/evidence/f3_audit_echo.py --arm v0=v2/evidence/run_d2_before_n16_seed42/run.jsonl --out-json v2/evidence/r38_f3/f3_audit_echo_v0_emooff.json` | **事件 1 / 分母 6**（rate 0.166667, band count_only） | ✅ **是** |
| `v2/evidence/f3_audit_echo.py` **`reply_path`** 分母 | 同上 | **0 / 0**（`empty`）——v0 语料 `reply_to` 全空（legacy 线程），分母为 0 | ❌ 不是 |
| `tools/f3/echo_field_stats.py` 的 `payload.ctx.echo` | — | OFF 臂**构造性为 0**（关闭时不写该键），不可能跑出 1/6 | ❌ 不是 |

⇒ **冻结口径 = `v2/evidence/f3_audit_echo.py` + `all_messages` 分母 + `loose` 档**
（loose = 极性相同 ∪ 任意 `EMPATHY_MARKERS`；分子=命中相邻对，分母=同线程相邻对中 `polarity(prev.body) != 0` 的对）。
`reply_path` 与 `marker_based` **只能作辅助列**，不得与主口径横向比较。
本口径下 v0 = **1/6**，CYCLE 前的 emo-off 语料（sha8 `c27691d9`）= **1/7**。

## 1. 现状定位（为什么 6 次机会只接住 1 次）

- 机制文件：`code/life/emotion_echo.py`（R14 已实现，223 行 → 本轮 283 行）。
- 接线点：`code/life/agent.py:1304` `echo_line, echo_audit = self._emotion_echo(ctx_in, p.get("body"), partner)`，
  位于 `_send_reply`（**只对"回复"生效**；`_initiate` 路径构造上不可能产 echo）。
- 判定链：`detect()` ← ①`life/emotion.emotion_sign(对方上一句)`（reflection 词表）→ ②`payload.ctx.mood` 查表。
- **缺口（实测）**：`emotion.NATURAL_*` 是给 **reflection 正文**写的**抽象心理词表**（担心/遗憾/疲惫/委屈…），
  而对话正文是**具体市井口述**（"盐放多了有点发苦"、"手都磨出泡了"、"孩子这两天咳得厉害"）——
  于是 ① 在真实对话上几乎恒 `0`，只剩 ②；而 `ctx.mood` 一旦是「平和」就 `(0,0)` 彻底不产。
  emo-off 语料 7 次机会里，**4 次**是「①=0 且 ②=平和」⇒ 直接 MISS。

## 2. 改动（只在 `code/life/`，未动 orchestration / config / engine）

`code/life/emotion_echo.py`：新增**第三来源「对话语域线索」**（`DIALOGUE_NEG_CUES` / `DIALOGUE_POS_CUES`）。

- **只在 `emotion_sign == 0` 时**才看 ⇒ 不覆盖单一真源的任何既有判断；
- 方向语义与 `emotion_sign` 一致（−1 需安抚 / +1 可顺着接），不引入第三极性；
- 线索**只收具体搭配**（不做「累/苦/病」单字匹配）；
- 可整表消融：`config/emotion_echo.json::dialogue_cues=false` ⇒ **逐字节退回 R14 行为**；
  新增参数 `cue_hit_intensity`（默认 45，≥ `min_intensity`=30 才真产）；
- `VERSION` `f3/1` → **`f3/2`**（payload 语义有变，便于按版本复算）；
- **OFF 路径逐字节不变**（默认 `enabled=false` ⇒ `plan()` 恒 None、`prompt_line()` 恒空串、不写 `ctx.echo`）。
- 未改 `config/emotion_echo.json`（`code/config/` 属跑批冻结区）：新参数走模块内 `DEFAULTS`。

`tools/f3/f3_offline_replay.py`（新增，只读）：零成本离线回放器。
分组键 `f4a.mixed_key()`、极性函数与抽取器 `d5.extract_messages()` **与主口径同一实现**，
保证回放分母与 `f3_audit_echo.py` **逐条对齐**（emooff=7、v0=6，与主口径完全相同）。

## 3. 前后对比（同一语料、同一命令、同一口径）

命令（**改前改后完全一致**，只换输出文件名）：
```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 tools/f3/f3_offline_replay.py \
  --arm emooff=v2/evidence/emo-off-20261030/run.jsonl \
  --arm v0=v2/evidence/run_d2_before_n16_seed42/run.jsonl \
  --out-json v2/evidence/r38_f3/AFTER_f3_offline_replay.json
```

**机制落点覆盖率**（回放判定器，强制 `enabled=True`；分母 = 主口径同源的"机会"数）：

| 语料 | 机会(分母) | BEFORE 会产呼应 | AFTER 会产呼应 | AFTER by_source |
|---|---|---|---|---|
| emo-off `c27691d9` | 7 | **3**（42.857%） | **6**（85.714%） | text+mood 1 / cue 3 / mood 1 / cue+mood 1 |
| v0-anchor `c1f86bf6` | 6 | 5（83.333%） | 5（83.333%，无变化） | text 5 |

**回复路径全部回复消息**（不看极性机会）：

| 语料 | 回复消息 | BEFORE | AFTER |
|---|---|---|---|
| emo-off `c27691d9` | 125 | 87（69.6%） | **91（72.8%）** |
| v0-anchor `c1f86bf6` | 0 | —（v0 无 `reply_to`，机制构造上不可能触发） | — |

**逐条差异**（emo-off 7 次机会）：4 次 MISS → PLAN，全部由 `cue` 命中，且经人读确认语义正确：
1. 「你家那口子这阵子还**咳得**厉害吗」→ soothe
2. 「盐放多了有点**发苦**」→ soothe
3. 「你腌萝卜**发苦**啊」→ soothe
4. 「**磨出泡**了还惦记蒜…那孩子这两天**咳得**厉害」→ cue+mood(紧绷) 65

**仍未命中 2 条（如实列出，不掩盖）**：
- emo-off：「刚把新到的陈皮翻晒完…那股子**苦香**…手也该歇歇了。称得准。」—
  主口径把它算作"上一句负向"其实是**词表假阳性**（"苦香"是气味不是苦处），本机制不接它是对的；
- v0：「**笑眯眯**地递过一块桂花糕…」— 正向线索表未收"笑眯眯"，故不产（v0 也根本无复核路径）。

## 4. 线索表精度自查（防"为了涨指标乱加词"）

emo-off 语料上 `cue` 来源共命中 **6** 行（收敛后），人读 6/6 语义正确（全部围绕病痛/劳累/食物发苦）。
收敛过程留痕：初版曾收 `断了`（"把李婶家**断了**的木簪接好" ⇒ 是修好了、不是苦处，**假阳性**）与
`顺当`（"还**顺当**吗？"是对别人的问候，**假阳性**），两条已删除，删除后机会覆盖率不变（仍 6/7），
回复路径 92 → 91。

## 5. 回归测试

```bash
cd code && python3 -m pytest life/tests/test_f3_emotion_echo.py -q                # 27 passed
cd code && python3 -m pytest life/tests/test_f3_emotion_echo.py \
  life/tests/test_t224_agent_wiring.py life/tests/test_r19_topic_breadth.py \
  life/tests/test_l13_topic_label_default.py -q                                   # 76 passed
```
（`life/tests` 全量 >300s 未跑完：个别集成用例耗时长，**未在本轮完整跑完，如实登记**。）

OFF 不变探针（默认关）：
```
EE.enabled()=False | plan("饥饿","盐放多了有点发苦") -> None | prompt_line(None) -> ''
audit(None) -> None
```

## 6. 拟用跑批命令（**本轮不执行**，供 r01-batch）

前置：**先 commit**（`tools/d5/preflight.sh` 会查 clean tree，未提交改动会被判不干净）；
`git fetch origin` 若仍网络失败，基线按本地跟踪 ref `94e272a` 计并在汇报里写明。

```bash
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
OUT=v2/evidence/r38_f3_batch
cd "$REPO"

# 1) 并发判定（两条都空才算无并发；不用 pgrep -cf，自匹配假阳性）
pgrep -af 'python3 -m orchestration run' | grep -v pgrep || echo "(空)"
ps -eo pid,ppid,etime,args | grep -E 'orchestration (run|world)' | grep -v grep || echo "(空)"

# 2) OFF 臂（与基线同配置）
setsid bash tools/d2/run_batch.sh --out-dir $OUT/off \
  --seed 42 --agents 16 --rounds 24 --side-root /tmp/r38_f3_side_off \
  > /tmp/r38_f3_off.stdout 2>&1 < /dev/null &

# 3) ON 臂（只翻 F-3 一个开关；与 OFF 同 seed/n/rounds/side-root 骨架）
HITT_DIALOGUE_EMOTION_ECHO=1 setsid bash tools/d2/run_batch.sh --out-dir $OUT/on \
  --seed 42 --agents 16 --rounds 24 --side-root /tmp/r38_f3_side_on \
  > /tmp/r38_f3_on.stdout 2>&1 < /dev/null &

# 4) 真调用验真（必须在 code/ 下跑，仓库根会 ModuleNotFoundError）
cd $REPO/code && python3 -m obs llm-cost $REPO/$OUT/on --require-provider openai_compat --out /tmp/r38_llm_cost_on.json
```

## 7. 与主口径的关系（必须成对读懂）

- **内容层**（主口径 `f3_audit_echo.py`）：只能在**新日志**上量，本轮没有新日志 ⇒ **本轮不产生内容层结论**；
- **机制层**（本记录 §3）：证明"判定器现在真的会给出提示"的比例从 3/7 升到 6/7。
  **机制给提示 ≠ LLM 就一定接住**，故不得据此宣称"F-3 从 1/6 提升到 6/7"。
