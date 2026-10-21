# F-4「误会与和解」修复闭环 · 复算锚点（零跑批）

> 性质：**零跑批、只读日志**的缺口复算锚点（R13 第一块）
> 报告日期：2026-10-21 ｜ 团队轮次：R13 ｜ 维度：F-4 修复闭环
> 代码锚点：`021baec30222d59a45c0e5838791acf9bc835fb2`（分支 `feat/life-l7-dedup-1021`，与 master / origin/master 同 sha）
> 本文件性质：**evidence 产物**（不入 `reports/`；正式报告见 `reports/R13-f4-repair.md`）
> 回执：`v2/evidence/f4_anchor_receipt.txt`（sha256 `80ab9a07…`，一键复算本文件所有数字）

---

## 0. 一句话结论

**缺口仍然存在，而且比 R4 记的更严重一层**：三份已入库真 LLM 批（n16r60 seed42）里，`dialogue_rift` 结构化字段命中 **0 条**（机制默认 `enabled=false`，从未在这三批里打开过），词表层的张力事件 22 / 15 / 15 条、8 条窗口内闭环 0 / 2 / 0 条；**且这 2 条闭环是误报**（命中的是「我懂」这种普通附和词）。同时张力分子本身噪声极大（off 臂 22 条里 19 条只命中 `怕/累/疼` 这类自述状态词，无一句是人际冲突）。

⇒ 结论：**要跑批，且必须先实现（f4-impl）再跑**；跑 **F-4 ON 臂**（n16r60 seed42，与现有 OFF 基线同规模同 seed，可比）。

---

## 1. 判读纪律（写死在数字之前）

1. **分母 < 30 只报事件数、不报比率**：三臂张力分母分别为 22 / 15 / 15，全部 < 30 ⇒ 本文**只给事件数**，不给 `closed_loop_rate`。
2. **分母 < 68 标 `probe`**：F-4 在三臂上均为 `probe` 级，**不得**据此写任何统计判定或「改善/恶化」。
3. 每个数字后跟「来源文件 + `sha8`（sha256 前 8 位）」。
4. 本文**只写可观测事实**，不写效果价值判断；不为 0 闭环编造因果，机制原因必须落到「文件:行号 + 代码片段」。

来源 sha8（`sha256sum` 原文见 §2.1）：

| arm | run.jsonl | sha8 |
|---|---|---|
| off（F-6 OFF 基线） | `v2/evidence/run_f6_off_n16r60_seed42/run.jsonl` | `c73bead6` |
| on（F-6 ON 臂） | `v2/evidence/run_f6_on_n16r60_seed42/run.jsonl` | `7de6a7be` |
| dequp（R12 DEQUP 臂） | `v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl` | `6bf3ec88` |

---

## 2. 复算命令（原样，可逐条重跑）

### 2.1 一键回执

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
bash tools/f4/f4_anchor_receipt.sh > v2/evidence/f4_anchor_receipt.txt 2>&1
sha256sum v2/evidence/f4_anchor_receipt.txt
# 80ab9a0740d284f34257630a294c31ed01bfd452aac57f30b5c35b2c1a359cdb  v2/evidence/f4_anchor_receipt.txt
```

产物脚本（均在 `tools/f4/`，新目录，不碰历史目录）：

| 脚本 | 作用 |
|---|---|
| `tools/f4/f4_anchor_recompute.py` | import `tools/d5/dialogue_metrics.py` 的 `compute()` 取官方 F-4/L-13，并用同一口径出**逐事件明细**，同时断言明细张力数 == 官方 `tension_events` |
| `tools/f4/f4_anchor_nearmiss.py` | 张力事件到「同线程其后最近的修复词消息」的距离（不限 8 条），区分「词根本不出现」vs「出现但在窗口外」 |
| `tools/f4/f4_tension_precision.py` | 张力事件的命中负向词按「人际冲突词 / 自述状态词」二分，披露分子噪声（**不改口径**） |
| `tools/f4/f4_anchor_receipt.sh` | 上面三件事 + sha256 + config + meta 的回执 |

### 2.2 关键输出（回执原文节选）

```text
### 1) 三份 run.jsonl 的 sha256（sha8 = 前 8 位）
c73bead61a440db789f6d6ba1de555fe326a203ee27d1219690174e3d9483642  v2/evidence/run_f6_off_n16r60_seed42/run.jsonl
7de6a7be5adff276f1e42c065a708c271f870f2bf8daa930cf0cdfc983f7434d  v2/evidence/run_f6_on_n16r60_seed42/run.jsonl
6bf3ec88700fa1a7451b18c63678d0904c69b9de39896739190e7e674db8fdbd  v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl

### 3) 日志里 dialogue_rift 字段命中条数（grep -c；默认关闭应为 0）
v2/evidence/run_f6_off_n16r60_seed42/run.jsonl 0
v2/evidence/run_f6_on_n16r60_seed42/run.jsonl 0
v2/evidence/run_f6_dequp_n16r60_seed42/run.jsonl 0

### 4) 官方指标实现复算（tools/d5/dialogue_metrics.py 的 compute()，F-4 / L-13）
| arm | sha8 | MSG | mixed线程 | 张力(官方) | 修复(官方) | 明细张力 | 明细修复 | 一致 | dialogue_rift 命中 | L-13 n |
| off | c73bead6 | 510 | 169 | 22 | 0 | 22 | 0 | OK | 0 | 2 |
| on | 7de6a7be | 510 | 169 | 15 | 2 | 15 | 2 | OK | 0 | 14 |
| dequp | 6bf3ec88 | 510 | 169 | 15 | 0 | 15 | 0 | OK | 0 | 9 |

### 5) 近失分析（张力后同线程最近修复词的距离）
| arm | sha8 | MSG | 张力 | 8条内修复 | 最近修复 lag 分布 | 全日志修复词消息数 | 修复词计数 |
| off | c73bead6 | 510 | 22 | 0 | {"none": 22} | 5 | {"我懂": 3, "慢慢来": 1, "对不起": 1} |
| on | 7de6a7be | 510 | 15 | 2 | {"none": 13, "<=8": 2} | 13 | {"慢慢来": 2, "我懂": 11} |
| dequp | 6bf3ec88 | 510 | 15 | 0 | {"none": 15} | 5 | {"慢慢来": 3, "我懂": 2} |

### 9) 张力检测精度初查
| arm | sha8 | 张力事件 | 含人际冲突词 | 仅自述状态词 | 自述词分布 |
| off | c73bead6 | 22 | 3 | 19 | {"怕": 15, "疼": 2, "算了": 2, "累": 1, "苦": 1} |
| on | 7de6a7be | 15 | 0 | 15 | {"怕": 10, "累": 2, "疼": 3} |
| dequp | 6bf3ec88 | 15 | 1 | 14 | {"怕": 10, "算了": 1, "苦": 2, "疼": 1} |
```

> **口径一致性自查**：明细复算的张力/修复数与官方 `compute()` 完全相等（`match_official=OK`，三臂一致）。
> 明细实现不是另写一套规则，而是镜像 `dialogue_metrics.py:698-718` 的同一循环（线程分组 `mixed_key`、极性函数、8 条窗口）。

---

## 3. 读数判读（只报事件数）

| arm | MSG | 张力事件 | 8 条内闭环 | 最近修复距离 | 分母纪律 |
|---|---|---|---|---|---|
| off `c73bead6` | 510 | **22** | **0** | 22 条全部「同线程后再无修复词」 | den 22 <30 ⇒ 只报事件数；<68 ⇒ `probe` |
| on `7de6a7be` | 510 | **15** | **2（均误报，见 §4.3）** | 13 条「再无修复词」 | 同上 |
| dequp `6bf3ec88` | 510 | **15** | **0** | 15 条全部「再无修复词」 | 同上 |

**分布（off `c73bead6`，事件类型）**：`MSG_DM 22 / 22`，`MSG_GROUP`、`MSG_PUBLIC` 均为 0 —— 张力只出现在 1v1 私聊。

**分布（off `c73bead6`，topic，事件数）**：`combat_training 9`、`counter_propose 5`、`whisper 4`、`gift 2`、`polite_reject 1`、`rel_maintain 1`。
on `7de6a7be`：`combat_training 4`、`scarce_buy 3`、`counter_propose 2`、`gift 2`、`mentorship 2`、`polite_reject 1`、`rel_maintain 1`。
dequp `6bf3ec88`：`combat_training 5`、`counter_propose 5`、`polite_reject 2`、`gift 1`、`mentorship 1`、`rel_maintain 1`。

> 三臂的 topic 名（`whisper` / `combat_training` / `scarce_buy` / `mentorship` / `counter_propose` …）是**模板 id**，正是 §5 L-13 的泄漏源；这里直接引用它们是因为它们同时是 F-4 的分组键。

---

## 4. 逐事件明细（命中 / 未命中）

### 4.1 off 臂 `c73bead6` —— 22 条张力，0 条闭环

| # | thread | seq(prev→cur) | topic | 前一句（节选） | 本句（节选） | 8条内修复 |
|---|---|---|---|---|---|---|
| 1 | TH-P006-P007-55 | 99056→112739 | whisper | 您说这东西靠谱吗 | 靠谱是靠谱，不过得看你怎么用……口音重了可能听岔 | 否 |
| 2 | TH-P006-P007-55 | 112739→115312 | whisper | 就是口音重了或者环境太吵……你得再核对一遍 | 那我回头试试，反正记账也不怕多核对一遍 | 否 |
| 3 | TH-P007-P005-18 | 23879→24847 | gift | 帮我看看这脸色是不是还差点火候 | 桂花糕先放着吧……是图个心里踏实，还是怕空着手不好开口 | 否 |
| 4 | TH-P007-P005-19 | 32896→34192 | gift | 您要是喜欢，下回我多带点 | 别为这个破费……倒是你，最近气色不太对 | 否 |
| 5 | TH-P007-P012-42 | 61328→62803 | whisper | 我这心里七上八下的，您给我透个底呗 | 我这心里也堵得慌……像是吵架，又像是哭 | 否 |
| 6 | TH-P009-P007-42 | 71039→79856 | whisper | 就是有笔账要平，想找个稳当人搭把手 | 我这心里没底啊 | 否 |
| 7 | TH-P009-P008-24 | 35851→37147 | combat_training | 规矩上训练前不宜进食，我照章办 | 账要平，肚子也得平，空着练我怕出岔子 | 否 |
| 8 | TH-P009-P008-25 | 37122→38031 | combat_training | 同上（重复线程不同 msg） | 同上 | 否 |
| 9 | TH-P009-P015-51 | 86635→88128 | counter_propose | 五味，这数不对，你再算算 | 我算了两遍，数没错……一条一条对 | 否 |
| 10 | TH-P009-P015-52 | 87730→89038 | counter_propose | 五味，这数不对，你再算算 | 同上 | 否 |
| 11 | TH-P011-P006-36 | 57977→59340 | combat_training | 先别急着去食堂……肚子叫也得先忍着 | 我肚子都唱空城计了，怕是要把您当包子啃啦 | 否 |
| 12 | TH-P011-P010-54 | 103994→113443 | rel_maintain | 输的请冰棍 | 谁怕谁啊——不过我这人一紧张就爱眨眼 | 否 |
| 13 | TH-P011-P013-25 | 37197→38139 | combat_training | 饿着也得把架势站稳 | 我肚子都咕咕叫了，再站下去怕是要晕给你看 | 否 |
| 14 | TH-P012-P014-36 | 59361→60605 | combat_training | 伤着筋骨可不是闹着玩的 | 我拿废铁皮都能敲出花来，还怕它咬我手不成 | 否 |
| 15 | TH-P012-P015-4 | 4039→4766 | counter_propose | 要不咱换个法子试试 | 换什么法子？……法子更不怕换 | 否 |
| 16 | TH-P012-P015-4 | 5044→7127 | counter_propose | 摆张小桌，谁路过都能搭上话 | 光摆着等人来问，怕是冷场 | 否 |
| 17 | TH-P012-P015-4 | 7815→8812 | counter_propose | 那咱就这么定 | 摔了不心疼……怕有人吃不惯 | 否 |
| 18 | TH-P014-P010-49 | 88599→88963 | combat_training | 废木料随便你砸 | 我现在砸东西，怕是把整间铺子都拆了 | 否 |
| 19 | TH-P014-P011-1 | 5039→6955 | combat_training | 我在学校跑步可是前三名 | 跑得快有啥用……看谁先累趴下 | 否 |
| 20 | TH-P014-P015-24 | 34841→36370 | combat_training | 我饿得手都抖了 | 你手抖成这样还练锤子，我怕待会儿飞过来的不是锤子 | 否 |
| 21 | TH-P014-P015-25 | 36315→37225 | combat_training | 同上 | 同上 | 否 |
| 22 | TH-P016-P015-15 | 28681→31904 | polite_reject | 牛腩先给我来半碗 | 今天这锅我多搁了半勺陈皮……可别怪我 | 否 |

（完整 40 字以上正文见 `v2/evidence/f4_anchor_recompute.json` 的 `arms[0].events[*].prev_body/cur_body`。）

### 4.2 on `7de6a7be` / dequp `6bf3ec88`

on 臂 15 条张力，只有 2 条 8 条内出现修复词；dequp 臂 15 条张力，0 条。逐事件表见同 JSON（`arms[1].events` / `arms[2].events`）。

### 4.3 那 2 条「闭环」是误报（关键，不许算作机制工作）

```text
on 臂 repaired_in_detail:
  ('m:T|TH-P003-P005-54', 89804, ['我懂'], 1)
  ('m:T|TH-P010-P009-37', 59288, ['我懂'], 2)
```

两条命中的词都是 **`我懂`**，上下文分别是「陈医，我懂。可兰姐那锅汤……」「金先生，账要平我懂，可我现在连自己想吃什么都不知道」——都是**顺口附和**，不是道歉/和解。
`我懂` 出现在 `tools/d5/repair_lexicon.txt` 里，因此词表层把它记成「闭环」。⇒ **R4 的「0/5」与本轮 on 臂的「2/15」都不能直接当机制证据**，词表分子的语义精度不足以支撑「和解」这一判断。

---

## 5. 代码侧原因（为什么闭环为 0）

### 5.1 主因：机制默认关闭，这三批里从未打开（`dialogue_rift` 命中 0 = 硬证据）

`code/config/dialogue_repair.json`：

```json
2:  "_comment": "R6-T2 · F-4「误会与和解」上下文机制开关（life/dialogue_repair.py）。默认 enabled=false ⇒ v0 语义零扰动。…消融逃生口：env HITT_DIALOGUE_REPAIR=1|0。",
4:  "enabled": false,
```

`code/life/dialogue_repair.py:102-105`（唯一打开入口，env 覆盖）：

```python
    env = os.environ.get("HITT_DIALOGUE_REPAIR")
    if env is not None:
        out["enabled"] = env.strip().lower() in ("1", "true", "on", "yes")
```

`tools/d2/run_batch.sh` 里**没有任何** `HITT_DIALOGUE_REPAIR` 注入（`grep -rn DIALOGUE_REPAIR tools/d2/run_batch.sh` → 无命中），三臂 `meta.json` 也无相关字段。
⇒ 三批的 `DR.load_params()["enabled"]` 恒为 `False`，因此：

- `code/life/agent.py:848-850` 的 rift 台账吸收整段不执行；
- `code/life/agent.py:993-998`（回复）/ `1053-1057`（发起）的 `rift_line` 恒为 `None`；
- `code/life/agent.py:1016-1020`、`1069-1073` 的 `payload["dialogue_rift"]` 永不写入。

```python
848:        dr = DR.load_params()
849:        if dr.get("enabled"):                 # R6-T2：先吸收可见消息 → 更新 rift 台账（只读）
850:            DR.ingest(...)
...
993:        rift_line = None
994:        if dr_cfg.get("enabled"):
995:            rift_line = DR.context_line(self._rifts, partner, int(wv.round), ...)
...
1016:        if dr_cfg.get("enabled"):
1017:            f = DR.audit_fields(self._rifts, int(wv.round), "reply", peers=[partner])
1020:                payload["dialogue_rift"] = f
```

⇒ **「修复闭环 = 0」在当前三臂上是必然结果**：既没有 rift 记账，也没有把「你还欠一句解释」放进提示词，更没有「优先接有旧账的线程」的回复优先级。

### 5.2 次因：提示词里完全没有「和解」环节

`code/life/agent.py:1252-1260`（回复提示词装配，`rift_line` 之外无任何修复语）：

```python
        return (self.persona.compressed_profile(self._current_goal())
1256:                + f"\n你正在和{who}聊「{topic}」。{self._mood_line()}。"
1257:                + (rift_line or "")          # R6-T2：处境（事实+选项）；关闭/无旧账时为空串
1258:                + f"\n刚才的对话：\n{lines}"
...
1260:                + "\n只写台词本身（接着刚才的话往下说一句）：不要用括号…")
```

`_dialogue_prompt`（`1240-1247`）同理。收尾指令只要求「接着往下说一句」「只写台词」，**没有任何一句要求把上一轮的不愉快说开**。
⇒ 即使 `enabled=true`，模型也只在「碰巧还记着这个线程」时才会写修复词；而 §4.2 的近失分析显示 **off/dequp 臂 22/15 条张力所在线程此后一条修复词都没有**（`{"none": 22}` / `{"none": 15}`），修复词全部出现在**别的线程**（5 条 / 5 条）。

### 5.3 三层原因小结（可执行结论）

| 层 | 事实 | 依据 |
|---|---|---|
| 机制层 | 开关默认 OFF，三批都未打开 ⇒ `dialogue_rift` 0 命中 | config:4 / dialogue_repair.py:102 / grep run_batch.sh |
| 提示词层 | 无「说开」环节；`rift_line` 段本身只给「处境+工具箱」，不给句型（设计如此，正确），但不打开时连处境都不给 | agent.py:1256-1260 |
| 度量层 | 词表张力分子噪声大（off 19/22 仅自述状态词），修复词分子精度低（`我懂` 被当和解） | `f4_tension_precision.json` / §4.3 |

⇒ f4-impl 的目标应当是**同时修机制层与度量层**：机制层用单 env 开关把 `dialogue_repair` 打开并新增「张力后同线程允许一次修复式回应（可计数）」；度量层为报告补一个**人际冲突词子集**的分母（作为主指标），词表层保留为可比的历史口径。

---

## 6. L-13 内部 token 泄漏成因（只定位，不修）

**现象**：`ctx.topic` 的原始内部串（模板 id）直接出现在台词里。命中 **2 / 14 / 9** 条（off/on/dequp），与 R11（2→14）、R12（2/14/9）三臂读数**逐条对上**。

**具体串与事件类型**（全为 `MSG_DM`）：

| arm | topic 串 | 条数 | 例（seq） |
|---|---|---|---|
| off `c73bead6` | `whisper` | 2 | 6049、99056 |
| on `7de6a7be` | `whisper` | 11 | 8350、13356、62319、62422、71011、74613、79833、80012、82482、84033、99021 |
| on `7de6a7be` | `combat_training` | 1 | 21903 |
| on `7de6a7be` | `scarce_buy` | 2 | 60137、60920 |
| dequp `6bf3ec88` | `whisper` | 5 | 69339、79921、99140、112826、113175 |
| dequp `6bf3ec88` | `mentorship` | 3 | 22394、61421、62599 |
| dequp `6bf3ec88` | `scarce_buy` | 1 | 60991 |

原文例（on 臂 seq 13356）：`阿林，按规定午休前不能离岗， whisper 的事还是先走流程。` —— `whisper` 是话题模板 id，被模型原样复述。

**成因（文件:行号）**：

```python
# code/life/agent.py:1235-1256  _reply_prompt
1256:                + f"\n你正在和{who}聊「{topic}」。{self._mood_line()}。"
```

- `topic` 在 `agent.py:990` 取自 `ctx_in.get("topic")`，而 `agent.py:1084` 的发起路径直接把模板 id 写进 `payload["topic"] = tid`；`api` 侧 `_ctx_snapshot`（`936-947`）原样落 `"topic": topic`。
- 于是提示词里出现 `你正在和 X 聊「whisper」`，模型**在中文句子里复述英文模板 id**。这不是「模型乱编」，而是**提示词把内部 token 当成人话喂进去了**（R11 §记忆流同一类根因：内部短语未人话化）。
- 与 L-8（`Pxxx` 泄漏，恒 0）不是同一件事：L-13 只在 `MSG_DM` 出现，且只漏 `topic`。

**未做**：本轮**不修**（任务边界），也**未**做「泄漏是否导致语义错误」的判定。

---

## 7. 明确回答两个问题

**Q1：缺口是否仍存在？**
**是。** 三臂 `dialogue_rift` 命中 **0**、8 条窗口内闭环 **0 / 2（误报）/ 0**，且 off/dequp 臂张力后同线程**再无任何修复词**。R4 记的「0/5」在更大规模（510 条消息、22 条张力）上复现，并新增两条事实：①机制层根本没打开；②张力分子 19/22 是自述状态词噪声。

**Q2：要不要跑批？跑哪个臂？**
**要，但先实现再跑。** 跑 **F-4 ON 臂**：`n16r60 seed42`，与现有 `run_f6_off_n16r60_seed42`（`c73bead6`，510 条消息 / 22 张力 / 0 闭环）**同规模同 seed**，可直接作基线，不需要重跑 OFF。
跑批前必须先满足 f4-impl 的两个前置：
1. 单 env 开关（默认 OFF）让「张力 → 同一线程内一次修复式回应」在机制上**可达且可计数**（新增可计数信号，不复用 `我懂`）；
2. 报告主指标改用**人际冲突词子集**的张力分母（本轮 off 臂该子集仅 3 条 ⇒ 届时仍是 `probe`，必须在预注册里写死「分母不足则只报事件数」），词表层 F-4 保留为历史可比口径。
