# DEQUANT 维度实现说明（去量化词/回指模板化）

- 任务：`#T1-dequant-impl`（负责人 `life-dev`）
- 分支：`feature/life-dequant-20261028`（基于 `71a6d74`，**未 commit、未 push**，等 `report-writer` 统一收口）
- 维度来源：`reports/recon-20261028.md` §7.1 / §7.3 排序 **#1**
- 北极星：居民对话与行为的生活气息（本轮切入：**台词的模板化同质感**）

---

## 1. 改动清单（文件:行号）

| # | 文件:行号 | 改动 | 性质 |
|---|---|---|---|
| 1 | `code/life/agent.py:79-152` | 新增 DEQUANT 臂的**开关/字面黑名单/骨架纯函数**：`DEQUANT_ENV`（`LIFE_PROMPT_DEQUANT`，**默认 OFF**）、`DEQUANT_LEXICON`（14 个本镇度量词/回指词）、`dequant_enabled()`、`dequant_lexicon_hits()`、`dequant_skeleton()` | 纯新增，模块级只读 |
| 2 | `code/life/agent.py:224-227` | `__init__` 追加两个**只记账**状态：`self._dequant_stats` / `self._dequant_slot_seen` | 纯新增，不进 payload、不进 `state_hash` |
| 3 | `code/life/agent.py:1076-1094` | `_dequp_body()` 增加 `slot` 形参（缺省 `None`，**向后兼容**），并在 L-7 早返回**之前**调用 `self._dequant_guard(body, slot)` | 记账一行，**不改返回的 body**、不新增 LLM 调用 |
| 4 | `code/life/agent.py:1157 / 1225` | 两处调用点传 `slot=slot_id`（`_send_reply` / `_initiate`） | 传参，无逻辑变化 |
| 5 | `code/life/agent.py:1328-1352` | 新增 `_dequant_line()`：**两条提示词末尾追加**的负向约束（禁止固定量词当填充 / 禁止「上回·上次」当起手式 / 真引用必须具体到「谁+做了什么」） | 提示词文本 |
| 6 | `code/life/agent.py:1354-1382` | 新增 `_dequant_guard()`：**字面黑名单 + 同 slot 句式骨架去重断言**（只记账，不改台词） | 只读断言 |
| 7 | `code/life/agent.py:1593 / 1619` | `_dialogue_prompt()` / `_reply_prompt()` 收尾指令后 `+ self._dequant_line()` | 提示词文本 |
| 8 | `tools/metrics/dequant_probe.py`（新文件） | 离线度量器：`上回/上次/想起/半指/第三格` 命中率、首 6 字模板 TopN、`MSG_*` 总数、`（把…往…` 占比、骨架重复度 | 纯只读，零跑批零 LLM |
| 9 | `code/tests/test_dequant_prompt.py`（新文件） | 6 条断言：开关语义 / OFF 逐字节不变 / ON 恰好一处追加 / 骨架遮蔽 / 同 slot 重复命中且不改台词 / 度量器复算基线 | 不依赖 LLM |

**改动范围**：只碰 `code/life/agent.py` + 两个新文件（1 个度量脚本、1 个测试）。**未改** `orchestration/`、`config/`、`engine/`、任何 JSON 配置。

### 设计要点（为什么这么做）

1. **单变量、默认 OFF**：OFF 时 `_dequant_line()` 返回空串 ⇒ 两条提示词与改动前**逐字节一致**，
   既有基线对拍测试（`test_gossip_g1_prompt_single_variable.py` 的 `d9391a3` 基线、
   `test_l7_structural.py` 的收尾指令断言）继续成立；跑处理臂必须**显式**
   `export LIFE_PROMPT_DEQUANT=1`（不依赖默认值）。
2. **只给条件、不给例句**：约束里没有提供任何「标准示范句」，避免把旧模板换成新模板。
3. **黑名单只用于断言/度量，不用于删改输出**：删改模型输出会破坏同 seed 可复现性与单变量对照。
4. **断言不改调用链与数据结构**：`_dequant_guard` 是纯副作用记账（`self._dequant_stats`），
   不进 payload、不进 `state_hash`、不触发额外 LLM 调用；`_dequp_body` 返回的 `body` 逐字不变
   （单测 `test_guard_flags_repeat_per_slot_and_never_edits_body` 守住）。

---

## 2. 可复算证据（命令 + 输出）

### 2.1 度量脚本在旧日志上的自证（79.8% / 29.8% / 23.7%）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
python3 tools/metrics/dequant_probe.py \
    --log v2/evidence/run_d12d_on_n16r60_seed42/run.jsonl \
    --expect-baseline --out v2/evidence/dequant_probe_baseline_71a6d74.json
# rc=0 ；产物：v2/evidence/dequant_probe_baseline_71a6d74.json
```

关键输出（与 `reports/recon-20261028.md` §7.1 **逐位一致**，delta = 0.0pp）：

```
n_msg = 510        msg_by_type = {MSG_DM: 455, MSG_PUBLIC: 55}
上回   407 / 79.8%      第三格 152 / 29.8%      半指 121 / 23.7%
上次    35 /  6.9%      想起    52 / 10.2%
head6_top: （把火钳往砧 15 / （把手里那杆 13 / 金先生，我这 9 / （把手里那半 9 / （把药碾子往 9
（把…往… 起头: 123 / 24.1%      骨架重复(≥2 次): 113 / 22.2%，distinct_skeletons 450
log_sha256 = ad0c939f062d23553adeb42af52617d082395265ddb2f6fe12a11d3093144ca0
self_check.ok = true   （三项 delta_pp 全 0.0，容差 ±0.4pp）
```

### 2.2 单元测试

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code
python3 -m pytest tests/test_dequant_prompt.py -q            # 6 passed
python3 -m pytest tests -q                                   # 604 passed（全量回归，82s）
```

单文件输出：`...... 6 passed in 0.66s`；全量：`604 passed in 82.35s`。

### 2.3 ON/OFF 单变量 & 断言生效（无 LLM 的自证脚本输出）

```
default enabled = False                       # 未设 env ⇒ 默认关（逐字节不变）
dialogue: len_off=251 len_on=397 delta=146 count(seg)=1 single_variable=True
reply   : len_off=259 len_on=405 delta=146 count(seg)=1 single_variable=True
skel1= 把这份卷宗归到#后我想起#漏填了
skel2= 把这份卷宗归到#后我想起#漏填了      # 同模板两句 → 同骨架
guard1 repeated= False   guard2 repeated= True
stats = {'checked': 2, 'lexicon_hit': 2, 'repeated': 1}
```

追加段落原文（`seg`，两处插入同一段、各恰好一次）：

> 说眼前这件事的时候，别拿镇上那套数儿当填充——「半指宽」「第三格」「三钱」这类词不是每句话的配料，只有这件活真到了要量的那一步才用，而且量多少就写多少。也别把「上回」「上次」当句子的起手式：不是每句都得提过去，眼下的事就说眼下；真要提，得说清是谁、做了什么，且那件事得是这些天确实发生过的。

---

## 3. 交给下游（T2 探针跑批 / T3 报告收口）

1. **必须显式开臂**：起跑前 `export LIFE_PROMPT_DEQUANT=1`，并把该行写进 launch evidence；
   不设 = 默认 OFF = **和基线一模一样**（会白跑）。
2. **验「臂真的生效」**（不靠自我声明）：同一 seed 下 `LLM_CALL.payload.prompt_hash`
   （`purpose="dialogue"`）在 OFF/ON 两臂必然不同；也可直接看探针批的 `run.jsonl` 里
   `dialogue` 类 `LLM_CALL` 的 `prompt_hash` 是否与 `run_d12d_on_n16r60_seed42` 的对应项不同。
3. **前后对比**（同口径，一条命令）：
   ```bash
   python3 tools/metrics/dequant_probe.py --log <新 run.jsonl> --out <out.json>
   ```
   对照 `v2/evidence/dequant_probe_baseline_71a6d74.json` 的 `keywords` / `head6_top` / `skeleton_dup`。
4. **不要做的事**：`LIFE_PROMPT_DEQUANT` 与 `LIFE_PROMPT_L7_STRUCT=0`（关结构臂）**不要同时**开
   —— 那会同时动两处提示词，破坏单变量；本轮 A/B 只动 DEQUANT 一个开关。
5. 本分支**未 commit**：`code/life/agent.py` 已改，新增 `tools/metrics/dequant_probe.py`、
   `code/tests/test_dequant_prompt.py`、`v2/evidence/dequant_probe_baseline_71a6d74.json`，
   由 `report-writer` 统一提交。

## 4. 已知局限（不夸大）

- 提示词约束能否真把 79.8% 的「上回」压下来，**本任务未验证**（需 T2 真 LLM 探针跑批）；
  本轮只交付「机制 + 可复算尺子 + 单测」，效果读数以 T2 为准。
- `dequant_skeleton` 的骨架口径是**本维度自定**（遮蔽人名/度量词/标点后取前 16 字），
  与官方 L-7 8-gram 口径**不是**同一把尺子，只用于「同 slot 骨架重复」这件事的内部断言。
- 离线度量器拿不到 run 的人名表 ⇒ `skeleton_dup` 是**上界**（不遮人名，比线上 guard 更宽）。
- 首 6 字模板（`（把…往…`，§7.1 病灶③）**本轮不在改动面内**（`_dequant_line` 不含动作骨架约束），
  只把它纳入度量输出，供下一维度（§7.3 排序 #3）接手。
