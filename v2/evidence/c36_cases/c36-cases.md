# CYCLE-36 §4 可展示案例与截图证据

> **生成者**：`case-harvester`（案例与截图取证）｜**生成时刻**：2026-10-31T04:37:42+08:00｜**仓库**：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment`｜**分支**：`exp/n36-scene-anchor`｜**HEAD**：`46cfd9e7a163fde88b0a9392c704a858b152d3aa`（短 `46cfd9e`）。
> **生成方式**：`v2/evidence/c36_cases/extract_c36_cases.py` 只读两臂 `run.jsonl` + 本次现场渲染件（**零跑批、零 LLM 调用**），本文件可由该脚本原样重生成。
> **用途**：供《CYCLE-36 周期实验报告》第四节「可展示案例」引用。
> **纪律**：正文逐字原文，不改写、不润色、不截断、不跨线程拼接；每线程单独成段；每条给 `thread_id` / `seq` / `msg_uid` / 说话人显示名与角色 / 逐字原文；每段给「物理行号 = `seq + 1`」的可复核关系（本批两臂实测均成立，见 §4）。
> **⚠ 图不进判据**：本文件所有 PNG **只作展示**，不参与任何数字判定/闸线；本文件**不计算臂级指标、不下「提升」结论**（读数与判据归证据审计与复算件）。
> **本任务交付三件**：① 本文件 `c36-cases.md`；② `c36-sha.txt`（图 sha 与源日志 sha 的 `sha256sum` 原始输出）；③ `c36-grep-checks.sh`（60 条逐字实拉命令，`bash` 直接复核）。配套：`v2/evidence/c36_shots/`（4 张 PNG + `render.log` + `render_report_c36-*.json`）、`v2/evidence/c36_cases/extract_c36_cases.py`（可原样重生成）。

---

## 1. 引用的是哪两个批次（先读，避免把在途批或旧批当本周期成果）

| 项 | ON 臂 | OFF 臂 |
|---|---|---|
| 批次目录 | `n15-on_n16r84_s42` | `n15-off_n16r84_s42` |
| 标签 | ON 臂（LIFE_PROMPT_ADDR_EVOLVE=1，称呼演化接线开） | OFF 臂（基线，开关 ABSENT） |
| `code_sha`（起/止，同一） | `0c94bcf2da770f03af4ab0c0daa7d78a486a8083` | `fff3e2daec6136f44bdda79bbe1dd214d90aacbc` |
| `run.jsonl` sha256 | `d74f7d00104a60c6d835c4022ba4979e22e1b9136185cc104506296b1996fefd` | `da4d248785efefe2caf92fc08821109e44057932812b9012bcf203bc569729d0` |
| 日志规模 | 194,050 events / 93,579,608 B | 193,979 events / 93,546,955 B |
| 起跑 / 收批（`meta.json`） | 2026-10-31T02:08:54+08:00 → 2026-10-31T02:57:13+08:00 | 2026-10-31T00:20:38+08:00 → 2026-10-31T01:16:31+08:00 |
| `run_batch.rc` | `0` | **无此文件**（该臂目录未留 `.rc`；收批依据 = `meta.finished_at` 已写 + `run.jsonl` mtime 停在 `2026-10-31T01:16:27+08:00`，不再增长） |
| `run.jsonl` mtime | 2026-10-31T02:57:09+08:00 | 2026-10-31T01:16:27+08:00 |
| seed / agents / rounds | 42 / 16 / 84 | 42 / 16 / 84 |
| MSG 计数（DM/GROUP/PUBLIC） | 497 / 126 / 63 | 497 / 126 / 63 |
| `llm_calls` / `degraded_calls` | 3403 / 0 | 3403 / 0 |
| `llm_cached` / `llm_cached_ratio` | 1666 / 0.4896 | 1666 / 0.4896 |
| `meta.json` sha256 | `1eb4623402a66d604346ca40d73402126f0b087d58188b138aa5094afea42923` | `b0f3807c7161c7b0509b8130fb88b74257bce091f990b915d63b6b05e95a3813` |
| `switch_proof.txt` sha256 | `1105d357541dca1bd15b39d8e8ae827a201abdf40460bca14eb73d32c2b7dcb4` | `58f06516e7213339fbb45e117ae80983376a6dbe74d73038eff705683c363ee6` |
| 线程总数（MSG_* 重建） | 206 | 206 |

**两臂开关证据（`switch_proof.txt` 原文节选，非本文件改写）**

```text
--- ON 臂 ---
pid=834882
captured_at=2026-10-31T02:08:56+08:00
batch_pid=834724
cgroup=0::/system.slice/jiuwenswarm.service
cmdline=python3 -m orchestration run --life --seed 42 --agents 16 --rounds 84 --out /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/n15-on_n16r84_s42/run.jsonl --flush-every 2 --side-root /tmp/n15_on_side 
HITT_LLM_PROVIDER=<present>
LIFE_PROMPT_ADDR_EVOLVE=1
LLM_API_KEY: present
--- 期望 ---
ON 臂期望：LIFE_PROMPT_ADDR_EVOLVE=1 出现在 /proc/834882/environ

--- OFF 臂 ---
pid=589464
captured_at=2026-10-31T00:21:01+08:00
HITT_LLM_PROVIDER=openai_compat
--- LLM_API_KEY ---
LLM_API_KEY: present, len=32
--- absent check ---
LIFE_PROMPT_ADDR_EVOLVE = ABSENT（OFF 臂预期）
```

> **可复核**：`cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment && sha256sum v2/evidence/n15-on_n16r84_s42/run.jsonl v2/evidence/n15-off_n16r84_s42/run.jsonl`。
> **⚠ 两臂 `code_sha` 不同**（`0c94bcf` vs `fff3e2d`），故 §3 的「同 thread 跨臂对照」**不是配对样本、不是同轨迹前后对照**；二者差异区间 `fff3e2d..0c94bcf` 仅含 D9u 勘误（`git diff --stat fff3e2d..0c94bcf` → `tools/d9n/narration_family.py`、`tools/d9n/narration_family_lexicon.json`、`v2/evidence/d9u*` 三处文档/词表），**未触及对话/称呼代码**；即便如此，本文件仍不从两臂差异中读任何效果结论。

**明确排除的在途批**：`v2/evidence/n36-on_n16r84_s42/run.jsonl`（此刻 41,016,739 B、mtime `2026-10-31T04:37:18+08:00`、目录内 `meta.json` = **不存在**）⇒ **未收批**，不引用、不作为本周期成果。

## 2. 段清单（5 段 × 6 条 = 30 条 ON 臂原文；另附 5 段 OFF 臂同 thread 对照 30 条）

| 段 | 类型 | 臂 | thread_id | 条数 | 主题 |
|---|---|---|---|---|---|
| 1 | 正向 | ON | `TH-P013-P004-16` | 6 | 称呼×关系演化：同一说话人 P004 对 P013 先称「铁头哥」(tier 2)、后回落「铁头」(tier 3) |
| 1′ | 对照 | OFF | `TH-P013-P004-16` | 6 | 同 thread、另一独立 run（形态对照，非配对样本） |
| 2 | 正向 | ON | `TH-P011-P003-30` | 6 | 称呼×关系演化：P011 首称 P003 为「阿禾姐」(tier 2)，后续改回「阿禾」(tier 3)；P003 对 P011 稳定称「小满」 |
| 2′ | 对照 | OFF | `TH-P011-P003-30` | 6 | 同 thread、另一独立 run（形态对照，非配对样本） |
| 3 | 缺陷 | ON | `TH-P006-P003-6` | 6 | 缺陷（self_name，把对方叫成自己）：P006「方老师」对 P003「阿禾」说「方老师，我刚从西坡薅了把野葱…」 |
| 3′ | 对照 | OFF | `TH-P006-P003-6` | 6 | 同 thread、另一独立 run（形态对照，非配对样本） |
| 4 | 缺陷 | ON | `TH-P015-P011-40` | 6 | 缺陷（self_name）：P011「小满」对 P015「五味」说「小满，你闻闻我这锅糖色…」 |
| 4′ | 对照 | OFF | `TH-P015-P011-40` | 6 | 同 thread、另一独立 run（形态对照，非配对样本） |
| 5 | 缺陷 | ON | `TH-P004-P013-4` | 6 | 缺陷（other_named，叫错人）：P004「秀娘」对 P013「铁头」开口即称「周公文」（P008 的名字，第三人） |
| 5′ | 对照 | OFF | `TH-P004-P013-4` | 6 | 同 thread、另一独立 run（形态对照，非配对样本） |

## 3. 逐字素材（每段 6 条同线程连续消息）

> **★可比性限定（与本节全部数字同段，必读）★**：本节出现的条数/`seq`/行号等数字**只描述素材本身**，**不作跨臂比较、不作效果结论**。原因：两臂 `code_sha` **不同** —— ON 臂 `0c94bcf2da770f03af4ab0c0daa7d78a486a8083`、OFF 臂 `fff3e2daec6136f44bdda79bbe1dd214d90aacbc`。判定「差异区间未触及对话行为路径」的**依据命令与输出**（可原地重放）：
> ```bash
> git diff --name-only fff3e2d..0c94bcf
> ```
> 输出恰 4 个文件：`tools/d9n/narration_family.py`、`tools/d9n/narration_family_lexicon.json`、`v2/evidence/d9u-step2-verb-screening.md`、`v2/evidence/d9u1-errata-expansion-25.md`（`git diff --stat` 合计 4 files changed, 121 insertions(+), 15 deletions(-)），**`code/` 下改动文件数 = 0**（`git diff --name-only fff3e2d..0c94bcf | grep -c '^code/'` → `0`）⇒ 差异仅 **D9u 词表/工具与勘误文档**，未触 `code/` 运行时行为路径；另有 `meta.json` 的 `code_sha == code_sha_end`（跑批期间代码未变）与 `switch_proof.txt` 的 `cmdline=python3 -m orchestration run ...`（行为路径全在 `code/`）两项侧证。
> 即便如此，本文件仍**不**从两臂差异读任何「开关有效/提升」结论（另见 §1 尾注与 §7）。

列义：`#seq` = `run.jsonl` 顶层 `seq`；`行号` = 物理行号（= `seq + 1`，见 §4 自检）；`msg_uid` = `payload.msg_uid`（`<seed>:<seq>`）；`说话人` = 显示名/角色/`persona_id`；`标注` = 既有尺子 `address_drift.py` 的呼语位判定（`形式/tier/指向`，**描述性标注、非判据**）。

### 段 1｜`TH-P013-P004-16`（ON 臂，6 条）

| 项 | 值 |
|---|---|
| 来源文件 | `v2/evidence/n15-on_n16r84_s42/run.jsonl` |
| 日志 sha256 | `d74f7d00104a60c6d835c4022ba4979e22e1b9136185cc104506296b1996fefd` |
| thread_id | `TH-P013-P004-16` |
| 消息类型 | `MSG_DM`（全段一致） |
| 参与人（`persona_id` → 显示名/角色） | `P004`→秀娘/cook、`P013`→铁头/craftsman |
| seq 序列 | `23259`, `23867`, `25748`, `27469`, `31604`, `34165` |
| turn_index 序列 | `0`, `1`, `2`, `3`, `4`, `5`（连续） |
| day/slot/place（逐条可变） | day [1, 2]；afternoon/market → evening/market → evening/cafe → night/residence → night/residence → morning/library |

逐字原文：

- **#23259**｜行号 23260｜`msg_uid` `42:23259`｜说话人 `P013`（青溪镇·铁头 / craftsman）→ 受话人 `P004`（青溪镇·秀娘 / cook）｜day 1 · afternoon · place `market`｜topic `scarce_buy`｜`MSG_DM`｜标注：`秀娘`/tier 3/`target_ok`
  > （攥着铁钳敲了敲砧子上那块犁头）哎，秀娘，你灶上那锅糊糊先匀我一碗，回头给你家锄头加个钢口。饿得慌。
- **#23867**｜行号 23868｜`msg_uid` `42:23867`｜说话人 `P004`（青溪镇·秀娘 / cook）→ 受话人 `P013`（青溪镇·铁头 / craftsman）｜day 1 · evening · place `market`｜topic `scarce_buy`｜`MSG_DM`｜标注：`铁头哥`/tier 2/`target_ok`
  > （掀开蒸笼盖，白汽扑了满脸）铁头哥，糊糊早见底啦，案板上还剩半块红糖发糕，你先垫垫。（拿油纸包了递过去）
- **#25748**｜行号 25749｜`msg_uid` `42:25748`｜说话人 `P013`（青溪镇·铁头 / craftsman）→ 受话人 `P004`（青溪镇·秀娘 / cook）｜day 1 · evening · place `cafe`｜topic `scarce_buy`｜`MSG_DM`｜标注：无呼语位称呼
  > （接过油纸包，指头沾了层糖霜）哎，我这炉上还煨着张屠户家那把斩骨刀，火候差一成就卷刃——你这发糕，掰半块给我路上啃行不？
- **#27469**｜行号 27470｜`msg_uid` `42:27469`｜说话人 `P004`（青溪镇·秀娘 / cook）→ 受话人 `P013`（青溪镇·铁头 / craftsman）｜day 1 · night · place `residence`｜topic `scarce_buy`｜`MSG_DM`｜标注：`铁头`/tier 3/`target_ok`
  > 铁头，我这笼屉里还蒸着李寡妇家订的枣泥糕，得盯着火候呢，你先掰半块发糕垫垫吧。
- **#31604**｜行号 31605｜`msg_uid` `42:31604`｜说话人 `P013`（青溪镇·铁头 / craftsman）→ 受话人 `P004`（青溪镇·秀娘 / cook）｜day 1 · night · place `residence`｜topic `scarce_buy`｜`MSG_DM`｜标注：无呼语位称呼
  > （把风箱拉杆一松，炉火暗下去）哎，我这铁砧上还压着王屠户家那把剔骨刀没淬完火呢，先啃你半块发糕垫垫吧。
- **#34165**｜行号 34166｜`msg_uid` `42:34165`｜说话人 `P004`（青溪镇·秀娘 / cook）→ 受话人 `P013`（青溪镇·铁头 / craftsman）｜day 2 · morning · place `library`｜topic `scarce_buy`｜`MSG_DM`｜标注：无呼语位称呼
  > （把发糕掰成两半，一半塞进铁头手里）发糕你先吃着，剔骨刀淬火急不得，王屠户明早才来取。我灶上那锅枣泥酥刚点上芝麻，你闻闻这味儿，甜不甜？

### 对照段 1′｜`TH-P013-P004-16`（OFF 臂，6 条）

| 项 | 值 |
|---|---|
| 来源文件 | `v2/evidence/n15-off_n16r84_s42/run.jsonl` |
| 日志 sha256 | `da4d248785efefe2caf92fc08821109e44057932812b9012bcf203bc569729d0` |
| thread_id | `TH-P013-P004-16` |
| 消息类型 | `MSG_DM`（全段一致） |
| 参与人（`persona_id` → 显示名/角色） | `P004`→秀娘/cook、`P013`→铁头/craftsman |
| seq 序列 | `23244`, `23852`, `25733`, `27448`, `31579`, `34138` |
| turn_index 序列 | `0`, `1`, `2`, `3`, `4`, `5`（连续） |
| day/slot/place（逐条可变） | day [1, 2]；afternoon/market → evening/market → evening/cafe → night/residence → night/residence → morning/library |

逐字原文：

- **#23244**｜行号 23245｜`msg_uid` `42:23244`｜说话人 `P013`（青溪镇·铁头 / craftsman）→ 受话人 `P004`（青溪镇·秀娘 / cook）｜day 1 · afternoon · place `market`｜topic `scarce_buy`｜`MSG_DM`｜标注：`秀娘`/tier 3/`target_ok`
  > （攥着刚出炉的镰刀往人堆里挤）哟，秀娘，这袋糙米让给我，我家灶上还空着。
- **#23852**｜行号 23853｜`msg_uid` `42:23852`｜说话人 `P004`（青溪镇·秀娘 / cook）→ 受话人 `P013`（青溪镇·铁头 / craftsman）｜day 1 · evening · place `market`｜topic `scarce_buy`｜`MSG_DM`｜标注：`铁头`/tier 3/`target_ok`
  > 铁头，那袋糙米你先拿去吧，我这儿还温着半屉枣泥糕，等会儿给巷口王奶奶送两块去。
- **#25733**｜行号 25734｜`msg_uid` `42:25733`｜说话人 `P013`（青溪镇·铁头 / craftsman）→ 受话人 `P004`（青溪镇·秀娘 / cook）｜day 1 · evening · place `cafe`｜topic `scarce_buy`｜`MSG_DM`｜标注：`秀娘`/tier 3/`target_ok`
  > （把锤子搁在砧子上，手背蹭了蹭额头的汗）哎，秀娘，我这炉上还煨着给赵家打的锄头，枣泥糕你先给王奶奶留着——糙米我拿了，回头给你捎两斤新打的铁钉，成不？
- **#27448**｜行号 27449｜`msg_uid` `42:27448`｜说话人 `P004`（青溪镇·秀娘 / cook）→ 受话人 `P013`（青溪镇·铁头 / craftsman）｜day 1 · night · place `residence`｜topic `scarce_buy`｜`MSG_DM`｜标注：`铁头`/tier 3/`target_ok`
  > 铁头，我这刚给陈家小孙子捏好一屉兔子包，枣泥糕你先拿两块垫垫肚子吧。
- **#31579**｜行号 31580｜`msg_uid` `42:31579`｜说话人 `P013`（青溪镇·铁头 / craftsman）→ 受话人 `P004`（青溪镇·秀娘 / cook）｜day 1 · night · place `residence`｜topic `scarce_buy`｜`MSG_DM`｜标注：`秀娘`/tier 3/`target_ok`
  > 哎，秀娘，我这正给赵家打把锄头，炉子还烧着呢，先吃你块枣泥糕垫垫吧。
- **#34138**｜行号 34139｜`msg_uid` `42:34138`｜说话人 `P004`（青溪镇·秀娘 / cook）→ 受话人 `P013`（青溪镇·铁头 / craftsman）｜day 2 · morning · place `library`｜topic `scarce_buy`｜`MSG_DM`｜标注：无呼语位称呼
  > （把枣泥糕往铁头手里一塞，转身掀开案板上的湿布）垫吧垫吧，炉子烧着也得顾肚子——我这刚揉好一屉南瓜面，等发起来就上锅，你打完锄头过来拿两块，给赵家小孙子捎一块。

<sub>说明：段 1 的 ON/OFF 两臂段是**同 thread_id、两个独立 run**（`code_sha` 不同），只能用于「形态差异」肉眼核对，**不得**当作配对样本或用其算比例。</sub>

### 段 2｜`TH-P011-P003-30`（ON 臂，6 条）

| 项 | 值 |
|---|---|
| 来源文件 | `v2/evidence/n15-on_n16r84_s42/run.jsonl` |
| 日志 sha256 | `d74f7d00104a60c6d835c4022ba4979e22e1b9136185cc104506296b1996fefd` |
| thread_id | `TH-P011-P003-30` |
| 消息类型 | `MSG_DM`（全段一致） |
| 参与人（`persona_id` → 显示名/角色） | `P003`→阿禾/farmer、`P011`→小满/student |
| seq 序列 | `38835`, `39712`, `47914`, `52113`, `55500`, `56431` |
| turn_index 序列 | `0`, `1`, `2`, `3`, `4`, `5`（连续） |
| day/slot/place（逐条可变） | day [2, 3]；evening/cafe → evening/cafe → night/residence → night/residence → night/residence → morning/office |

逐字原文：

- **#38835**｜行号 38836｜`msg_uid` `42:38835`｜说话人 `P011`（青溪镇·小满 / student）→ 受话人 `P003`（青溪镇·阿禾 / farmer）｜day 2 · evening · place `cafe`｜topic `rel_maintain`｜`MSG_DM`｜标注：`阿禾姐`/tier 2/`target_ok`
  > （捏着半块冷馍从阿禾家灶房门口探进头）阿禾姐，你这锅里炖的萝卜味儿都飘到巷口了，我拿馍来换一口汤吧。
- **#39712**｜行号 39713｜`msg_uid` `42:39712`｜说话人 `P003`（青溪镇·阿禾 / farmer）→ 受话人 `P011`（青溪镇·小满 / student）｜day 2 · evening · place `cafe`｜topic `rel_maintain`｜`MSG_DM`｜标注：无呼语位称呼
  > （把灶台边的粗瓷碗往小满那边推了推）萝卜是后园拔的，汤你舀，碗搁这儿就行。
- **#47914**｜行号 47915｜`msg_uid` `42:47914`｜说话人 `P011`（青溪镇·小满 / student）→ 受话人 `P003`（青溪镇·阿禾 / farmer）｜day 2 · night · place `residence`｜topic `rel_maintain`｜`MSG_DM`｜标注：无呼语位称呼
  > （捏着筷子戳了戳碗里的萝卜）哎，这萝卜甜得跟偷了糖似的——你娘上回腌的那坛子，是不是也搁了后园的？
- **#52113**｜行号 52114｜`msg_uid` `42:52113`｜说话人 `P003`（青溪镇·阿禾 / farmer）→ 受话人 `P011`（青溪镇·小满 / student）｜day 2 · night · place `residence`｜topic `rel_maintain`｜`MSG_DM`｜标注：无呼语位称呼
  > （把萝卜干往坛口按了按）后园那畦早拔了，剩这几根还是你婶子昨儿送来的。
- **#55500**｜行号 55501｜`msg_uid` `42:55500`｜说话人 `P011`（青溪镇·小满 / student）→ 受话人 `P003`（青溪镇·阿禾 / farmer）｜day 2 · night · place `residence`｜topic `rel_maintain`｜`MSG_DM`｜标注：`阿禾`/tier 3/`target_ok`
  > 阿禾，你婶子送的那几根我瞅着还带泥呢，（伸手从坛沿捻起一小撮盐粒）要不咱再撒把盐压压水？
- **#56431**｜行号 56432｜`msg_uid` `42:56431`｜说话人 `P003`（青溪镇·阿禾 / farmer）→ 受话人 `P011`（青溪镇·小满 / student）｜day 3 · morning · place `office`｜topic `rel_maintain`｜`MSG_DM`｜标注：`小满`/tier 3/`target_ok`
  > 小满，这坛子沿儿上还沾着昨儿的盐粒呢，（拿袖口蹭了蹭坛口）再撒就齁了。

### 对照段 2′｜`TH-P011-P003-30`（OFF 臂，6 条）

| 项 | 值 |
|---|---|
| 来源文件 | `v2/evidence/n15-off_n16r84_s42/run.jsonl` |
| 日志 sha256 | `da4d248785efefe2caf92fc08821109e44057932812b9012bcf203bc569729d0` |
| thread_id | `TH-P011-P003-30` |
| 消息类型 | `MSG_DM`（全段一致） |
| 参与人（`persona_id` → 显示名/角色） | `P003`→阿禾/farmer、`P011`→小满/student |
| seq 序列 | `38810`, `39687`, `47886`, `52084`, `55471`, `56401` |
| turn_index 序列 | `0`, `1`, `2`, `3`, `4`, `5`（连续） |
| day/slot/place（逐条可变） | day [2, 3]；evening/cafe → evening/cafe → night/residence → night/residence → night/residence → morning/office |

逐字原文：

- **#38810**｜行号 38811｜`msg_uid` `42:38810`｜说话人 `P011`（青溪镇·小满 / student）→ 受话人 `P003`（青溪镇·阿禾 / farmer）｜day 2 · evening · place `cafe`｜topic `rel_maintain`｜`MSG_DM`｜标注：无呼语位称呼
  > （把阿禾家灶台上那半块凉红薯拿起来掂了掂）凉红薯也是红薯，先垫一口再帮你家剥豆子吧。
- **#39687**｜行号 39688｜`msg_uid` `42:39687`｜说话人 `P003`（青溪镇·阿禾 / farmer）→ 受话人 `P011`（青溪镇·小满 / student）｜day 2 · evening · place `cafe`｜topic `rel_maintain`｜`MSG_DM`｜标注：无呼语位称呼
  > （把红薯掰成两半，递回一半）红薯你吃，豆子我剥。
- **#47886**｜行号 47887｜`msg_uid` `42:47886`｜说话人 `P011`（青溪镇·小满 / student）→ 受话人 `P003`（青溪镇·阿禾 / farmer）｜day 2 · night · place `residence`｜topic `rel_maintain`｜`MSG_DM`｜标注：无呼语位称呼
  > （把豆荚往膝盖上一搁）小满这名字听着就饿，你娘蒸的槐花饭今年还做不做？
- **#52084**｜行号 52085｜`msg_uid` `42:52084`｜说话人 `P003`（青溪镇·阿禾 / farmer）→ 受话人 `P011`（青溪镇·小满 / student）｜day 2 · night · place `residence`｜topic `rel_maintain`｜`MSG_DM`｜标注：无呼语位称呼
  > （把簸箕往膝头挪了挪，挑出个瘪豆荚）槐花饭得等树开，我娘腿脚不行了，今年是隔壁张婶上树捋的。
- **#55471**｜行号 55472｜`msg_uid` `42:55471`｜说话人 `P011`（青溪镇·小满 / student）→ 受话人 `P003`（青溪镇·阿禾 / farmer）｜day 2 · night · place `residence`｜topic `rel_maintain`｜`MSG_DM`｜标注：`阿禾`/tier 3/`target_ok`
  > 阿禾，张婶上树那回我瞧见了，她裤脚挂破一道口子。（捏着豆荚两头一掰，豆粒滚进搪瓷盆）
- **#56401**｜行号 56402｜`msg_uid` `42:56401`｜说话人 `P003`（青溪镇·阿禾 / farmer）→ 受话人 `P011`（青溪镇·小满 / student）｜day 3 · morning · place `office`｜topic `rel_maintain`｜`MSG_DM`｜标注：`小满`/tier 3/`target_ok`
  > 小满，张婶那裤脚我给她缝上了。（把搪瓷盆往桌里推了推）豆子挑完就还她。

<sub>说明：段 2 的 ON/OFF 两臂段是**同 thread_id、两个独立 run**（`code_sha` 不同），只能用于「形态差异」肉眼核对，**不得**当作配对样本或用其算比例。</sub>

### 段 3｜`TH-P006-P003-6`（ON 臂，6 条）

| 项 | 值 |
|---|---|
| 来源文件 | `v2/evidence/n15-on_n16r84_s42/run.jsonl` |
| 日志 sha256 | `d74f7d00104a60c6d835c4022ba4979e22e1b9136185cc104506296b1996fefd` |
| thread_id | `TH-P006-P003-6` |
| 消息类型 | `MSG_DM`（全段一致） |
| 参与人（`persona_id` → 显示名/角色） | `P003`→阿禾/farmer、`P006`→方老师/teacher |
| seq 序列 | `4946`, `5671`, `8317`, `11050`, `19192`, `20356` |
| turn_index 序列 | `0`, `1`, `2`, `3`, `4`, `5`（连续） |
| day/slot/place（逐条可变） | day [0, 1]；evening/plaza → evening/plaza → night/residence → night/residence → morning/park → morning/farm |

逐字原文：

- **#4946**｜行号 4947｜`msg_uid` `42:4946`｜说话人 `P006`（青溪镇·方老师 / teacher）→ 受话人 `P003`（青溪镇·阿禾 / farmer）｜day 0 · evening · place `plaza`｜topic `gift`｜`MSG_DM`｜标注：`阿禾`/tier 3/`target_ok`
  > （把一摞刚裁好的毛边纸在桌上磕齐）哎，阿禾，这沓纸你拿着练字吧，我裁多了搁着也是搁着嘛。
- **#5671**｜行号 5672｜`msg_uid` `42:5671`｜说话人 `P003`（青溪镇·阿禾 / farmer）→ 受话人 `P006`（青溪镇·方老师 / teacher）｜day 0 · evening · place `plaza`｜topic `gift`｜`MSG_DM`｜标注：无呼语位称呼
  > （把锄头靠在墙根，裤脚还沾着泥）你那菜园子刚浇过水，一个人忙得过来吧。
- **#8317**｜行号 8318｜`msg_uid` `42:8317`｜说话人 `P006`（青溪镇·方老师 / teacher）→ 受话人 `P003`（青溪镇·阿禾 / farmer）｜day 0 · night · place `residence`｜topic `gift`｜`MSG_DM`｜标注：无呼语位称呼
  > （放下手里的水瓢，瓢底还滴着水）菜园子浇完了，正想歇会儿呢。你裤脚上那泥，是西坡地里刚翻的吧？
- **#11050**｜行号 11051｜`msg_uid` `42:11050`｜说话人 `P003`（青溪镇·阿禾 / farmer）→ 受话人 `P006`（青溪镇·方老师 / teacher）｜day 0 · night · place `residence`｜topic `gift`｜`MSG_DM`｜标注：`方老师`/tier 1/`target_ok`
  > （把锄头往田埂上一靠，泥块从锄面掉下来）哎，方老师，西坡那垄刚翻完，顺手薅了把野葱。给你搁门口？
- **#19192**｜行号 19193｜`msg_uid` `42:19192`｜说话人 `P006`（青溪镇·方老师 / teacher）→ 受话人 `P003`（青溪镇·阿禾 / farmer）｜day 1 · morning · place `park`｜topic `gift`｜`MSG_DM`｜标注：`方老师`/tier 1/`self_name`
  > 方老师，我刚从西坡薅了把野葱，给你搁门口吧。
- **#20356**｜行号 20357｜`msg_uid` `42:20356`｜说话人 `P003`（青溪镇·阿禾 / farmer）→ 受话人 `P006`（青溪镇·方老师 / teacher）｜day 1 · morning · place `farm`｜topic `gift`｜`MSG_DM`｜标注：无呼语位称呼
  > （把野葱往门边一放，手在裤腿上蹭了蹭）这葱嫩，你留着下面条。灶上还烧着水。

### 对照段 3′｜`TH-P006-P003-6`（OFF 臂，6 条）

| 项 | 值 |
|---|---|
| 来源文件 | `v2/evidence/n15-off_n16r84_s42/run.jsonl` |
| 日志 sha256 | `da4d248785efefe2caf92fc08821109e44057932812b9012bcf203bc569729d0` |
| thread_id | `TH-P006-P003-6` |
| 消息类型 | `MSG_DM`（全段一致） |
| 参与人（`persona_id` → 显示名/角色） | `P003`→阿禾/farmer、`P006`→方老师/teacher |
| seq 序列 | `4946`, `5671`, `8314`, `11045`, `19179`, `20341` |
| turn_index 序列 | `0`, `1`, `2`, `3`, `4`, `5`（连续） |
| day/slot/place（逐条可变） | day [0, 1]；evening/plaza → evening/plaza → night/residence → night/residence → morning/park → morning/farm |

逐字原文：

- **#4946**｜行号 4947｜`msg_uid` `42:4946`｜说话人 `P006`（青溪镇·方老师 / teacher）→ 受话人 `P003`（青溪镇·阿禾 / farmer）｜day 0 · evening · place `plaza`｜topic `gift`｜`MSG_DM`｜标注：无呼语位称呼
  > （把一摞用麻绳捆好的旧课本往阿禾怀里递了递）哎，这是我家小子去年用过的算数本，边角都磨圆了，你拿去翻翻，里头批注还在呢吧。
- **#5671**｜行号 5672｜`msg_uid` `42:5671`｜说话人 `P003`（青溪镇·阿禾 / farmer）→ 受话人 `P006`（青溪镇·方老师 / teacher）｜day 0 · evening · place `plaza`｜topic `gift`｜`MSG_DM`｜标注：无呼语位称呼
  > （把沾泥的锄头往墙根一靠，接过本子翻了翻）你家小子这算数本上，鸡兔同笼那道题还画了圈呢吧。
- **#8314**｜行号 8315｜`msg_uid` `42:8314`｜说话人 `P006`（青溪镇·方老师 / teacher）→ 受话人 `P003`（青溪镇·阿禾 / farmer）｜day 0 · night · place `residence`｜topic `gift`｜`MSG_DM`｜标注：无呼语位称呼
  > （从阿禾手里接过本子，指尖点了点那道画圈的题）鸡兔同笼啊，这小子昨天还追着我问，说鸡和兔子关一块儿，谁替谁数脚呢。（笑）你这一翻，倒让我想起他今早出门前，非要把本子塞书包最底下。你家的娃，最近也爱拿题来考你不？
- **#11045**｜行号 11046｜`msg_uid` `42:11045`｜说话人 `P003`（青溪镇·阿禾 / farmer）→ 受话人 `P006`（青溪镇·方老师 / teacher）｜day 0 · night · place `residence`｜topic `gift`｜`MSG_DM`｜标注：无呼语位称呼
  > （哎，我正蹲在灶前添柴，锅里水还没开）我家那个光顾着追鸡，哪顾得上数脚。（抬头）你吃了吗？
- **#19179**｜行号 19180｜`msg_uid` `42:19179`｜说话人 `P006`（青溪镇·方老师 / teacher）→ 受话人 `P003`（青溪镇·阿禾 / farmer）｜day 1 · morning · place `park`｜topic `gift`｜`MSG_DM`｜标注：`阿禾`/tier 3/`target_ok`
  > 阿禾，我这儿刚蒸好一屉红薯，给你家那个追鸡的娃捎两个吧。
- **#20341**｜行号 20342｜`msg_uid` `42:20341`｜说话人 `P003`（青溪镇·阿禾 / farmer）→ 受话人 `P006`（青溪镇·方老师 / teacher）｜day 1 · morning · place `farm`｜topic `gift`｜`MSG_DM`｜标注：`方老师`/tier 1/`target_ok`
  > （放下锄头，手在裤腿上蹭了蹭）方老师，你家灶上那锅红薯，我闻着就饿。给我娃留一个。

<sub>说明：段 3 的 ON/OFF 两臂段是**同 thread_id、两个独立 run**（`code_sha` 不同），只能用于「形态差异」肉眼核对，**不得**当作配对样本或用其算比例。</sub>

### 段 4｜`TH-P015-P011-40`（ON 臂，6 条）

| 项 | 值 |
|---|---|
| 来源文件 | `v2/evidence/n15-on_n16r84_s42/run.jsonl` |
| 日志 sha256 | `d74f7d00104a60c6d835c4022ba4979e22e1b9136185cc104506296b1996fefd` |
| thread_id | `TH-P015-P011-40` |
| 消息类型 | `MSG_DM`（全段一致） |
| 参与人（`persona_id` → 显示名/角色） | `P011`→小满/student、`P015`→五味/cook |
| seq 序列 | `60821`, `61583`, `63165`, `73015`, `81406`, `84546` |
| turn_index 序列 | `0`, `1`, `2`, `3`, `4`, `5`（连续） |
| day/slot/place（逐条可变） | day [3, 4]；afternoon/plaza → evening/park → evening/plaza → night/residence → night/residence → morning/school |

逐字原文：

- **#60821**｜行号 60822｜`msg_uid` `42:60821`｜说话人 `P015`（青溪镇·五味 / cook）→ 受话人 `P011`（青溪镇·小满 / student）｜day 3 · afternoon · place `plaza`｜topic `polite_reject`｜`MSG_DM`｜标注：`小满`/tier 3/`target_ok`
  > （唉，手里这锅糖色又炒过了，苦味儿直往鼻子里钻）小满啊，你上回说想学的那道红烧肉，我今儿怕是教不了啦——镇上王木匠家闺女明儿出嫁，非拉我去帮厨，我这半吊子手艺也得去凑个数。要不改天你来我这儿，咱俩慢慢试？
- **#61583**｜行号 61584｜`msg_uid` `42:61583`｜说话人 `P011`（青溪镇·小满 / student）→ 受话人 `P015`（青溪镇·五味 / cook）｜day 3 · evening · place `park`｜topic `polite_reject`｜`MSG_DM`｜标注：`小满`/tier 3/`self_name`
  > 小满，你闻闻我这锅糖色，苦得跟王木匠家那闺女上花轿前哭的泪似的——明儿帮厨我掌勺，你猜我头一道菜敢不敢做红烧肉？
- **#63165**｜行号 63166｜`msg_uid` `42:63165`｜说话人 `P015`（青溪镇·五味 / cook）→ 受话人 `P011`（青溪镇·小满 / student）｜day 3 · evening · place `plaza`｜topic `polite_reject`｜`MSG_DM`｜标注：`小满`/tier 3/`target_ok`
  > 小满，我这锅糖色熬得比王木匠家闺女上花轿哭的泪还苦，明儿帮厨头一道菜我要是真端出红烧肉，你敢不敢先替我尝一筷子？
- **#73015**｜行号 73016｜`msg_uid` `42:73015`｜说话人 `P011`（青溪镇·小满 / student）→ 受话人 `P015`（青溪镇·五味 / cook）｜day 3 · night · place `residence`｜topic `polite_reject`｜`MSG_DM`｜标注：无呼语位称呼
  > （把搪瓷缸往灶台边一搁，缸底磕出脆响）苦糖色配红烧肉，王木匠家闺女听了都得掀盖头跑呢。
- **#81406**｜行号 81407｜`msg_uid` `42:81406`｜说话人 `P015`（青溪镇·五味 / cook）→ 受话人 `P011`（青溪镇·小满 / student）｜day 3 · night · place `residence`｜topic `polite_reject`｜`MSG_DM`｜标注：无呼语位称呼
  > （拿筷子尖戳了戳锅里那块颤巍巍的肉皮）掀盖头跑？那正好，跑一个我留一个——王木匠家闺女要是真来了，我这锅肉就改叫“新娘子跳墙”。（撇掉浮沫，火苗舔着锅底）你说这糖色苦，我倒觉得是焦得刚好，跟人似的，太顺了反倒没味。要不你替我尝尝，是苦还是香？
- **#84546**｜行号 84547｜`msg_uid` `42:84546`｜说话人 `P011`（青溪镇·小满 / student）→ 受话人 `P015`（青溪镇·五味 / cook）｜day 4 · morning · place `school`｜topic `polite_reject`｜`MSG_DM`｜标注：无呼语位称呼
  > （把灶边那碗凉水往锅沿推了推）哟，王木匠家闺女昨儿还来借过刨子，说给她爹修窗框——你这锅肉要是真跳了墙，她拿啥赔你？

### 对照段 4′｜`TH-P015-P011-40`（OFF 臂，6 条）

| 项 | 值 |
|---|---|
| 来源文件 | `v2/evidence/n15-off_n16r84_s42/run.jsonl` |
| 日志 sha256 | `da4d248785efefe2caf92fc08821109e44057932812b9012bcf203bc569729d0` |
| thread_id | `TH-P015-P011-40` |
| 消息类型 | `MSG_DM`（全段一致） |
| 参与人（`persona_id` → 显示名/角色） | `P011`→小满/student、`P015`→五味/cook |
| seq 序列 | `60787`, `61549`, `63131`, `72976`, `81358`, `84494` |
| turn_index 序列 | `0`, `1`, `2`, `3`, `4`, `5`（连续） |
| day/slot/place（逐条可变） | day [3, 4]；afternoon/plaza → evening/park → evening/plaza → night/residence → night/residence → morning/school |

逐字原文：

- **#60787**｜行号 60788｜`msg_uid` `42:60787`｜说话人 `P015`（青溪镇·五味 / cook）→ 受话人 `P011`（青溪镇·小满 / student）｜day 3 · afternoon · place `plaza`｜topic `polite_reject`｜`MSG_DM`｜标注：`小满`/tier 3/`target_ok`
  > （把手里那半截萝卜搁回案板，刀口还沾着泥）哎，小满，你上回托我留的那坛子酱萝卜，我今儿一开盖尝了口，咸得能齁死卖盐的——要不你先拿回去，搁两天再吃？
- **#61549**｜行号 61550｜`msg_uid` `42:61549`｜说话人 `P011`（青溪镇·小满 / student）→ 受话人 `P015`（青溪镇·五味 / cook）｜day 3 · evening · place `park`｜topic `polite_reject`｜`MSG_DM`｜标注：`五味叔`/tier 2/`target_ok`
  > （把晾在窗台的酱萝卜坛子抱下来，坛底还沾着圈盐霜）五味叔，这坛子我先不拿——您尝着齁，我拿回去也是搁着，不如您再添半瓢凉白开兑兑，回头腌新萝卜正好使。您说呢？
- **#63131**｜行号 63132｜`msg_uid` `42:63131`｜说话人 `P015`（青溪镇·五味 / cook）→ 受话人 `P011`（青溪镇·小满 / student）｜day 3 · evening · place `plaza`｜topic `polite_reject`｜`MSG_DM`｜标注：`小满`/tier 3/`target_ok`
  > 小满，这坛子你先搁灶台边——我正拿它压着新腌的雪里蕻呢，坛口那圈盐霜我拿湿布擦擦就成。（掀开灶上砂锅盖，白汽扑了满脸）你闻闻，这锅萝卜炖得烂不烂？
- **#72976**｜行号 72977｜`msg_uid` `42:72976`｜说话人 `P011`（青溪镇·小满 / student）→ 受话人 `P015`（青溪镇·五味 / cook）｜day 3 · night · place `residence`｜topic `polite_reject`｜`MSG_DM`｜标注：无呼语位称呼
  > （拿筷子尖戳了戳砂锅里的萝卜，又缩回手吹了吹）烂是烂了，可你灶台边那坛子压着雪里蕻，我娘昨儿还念叨要借你家坛子腌点糖蒜呢。
- **#81358**｜行号 81359｜`msg_uid` `42:81358`｜说话人 `P015`（青溪镇·五味 / cook）→ 受话人 `P011`（青溪镇·小满 / student）｜day 3 · night · place `residence`｜topic `polite_reject`｜`MSG_DM`｜标注：无呼语位称呼
  > （把砂锅盖子斜过来，拿抹布垫着掀开一条缝，白汽扑到脸上）坛子你娘要就拿去，里头那点雪里蕻我回头腾到搪瓷盆里——正好，我这儿萝卜炖得发死，你帮我尝尝，是缺糖还是缺醋？
- **#84494**｜行号 84495｜`msg_uid` `42:84494`｜说话人 `P011`（青溪镇·小满 / student）→ 受话人 `P015`（青溪镇·五味 / cook）｜day 4 · morning · place `school`｜topic `polite_reject`｜`MSG_DM`｜标注：`五味叔`/tier 2/`target_ok`
  > （拿筷子尖戳了戳萝卜块，又缩回手甩了甩）哎，五味叔，你这萝卜炖得筷子一碰就散，我娘那坛子雪里蕻换你这锅，她准得说我亏了——你尝过没，是不是该搁半勺糖提提？

<sub>说明：段 4 的 ON/OFF 两臂段是**同 thread_id、两个独立 run**（`code_sha` 不同），只能用于「形态差异」肉眼核对，**不得**当作配对样本或用其算比例。</sub>

### 段 5｜`TH-P004-P013-4`（ON 臂，6 条）

> **既存缺陷声明（写死）**：本条缺陷在 ON 臂（`n15-on`）与 OFF 臂（`n15-off`）**同一 `seq=3121` 同现**⇒ 属**既存缺陷、由基线继承**，**不是本臂（N-15 称呼演化接线）引入**，**也不得**被读作任何「回归」或「改善证据」。仅证明该错称形态在本周期两臂日志中都存在。

| 项 | 值 |
|---|---|
| 来源文件 | `v2/evidence/n15-on_n16r84_s42/run.jsonl` |
| 日志 sha256 | `d74f7d00104a60c6d835c4022ba4979e22e1b9136185cc104506296b1996fefd` |
| thread_id | `TH-P004-P013-4` |
| 消息类型 | `MSG_DM`（全段一致） |
| 参与人（`persona_id` → 显示名/角色） | `P004`→秀娘/cook、`P013`→铁头/craftsman |
| seq 序列 | `3121`, `5065`, `5732`, `7844`, `8200`, `15598` |
| turn_index 序列 | `0`, `1`, `2`, `3`, `4`, `5`（连续） |
| day/slot/place（逐条可变） | day [0]；afternoon/market → evening/cafe → evening/community_center → evening/cafe → night/residence → night/residence |

逐字原文：

- **#3121**｜行号 3122｜`msg_uid` `42:3121`｜说话人 `P004`（青溪镇·秀娘 / cook）→ 受话人 `P013`（青溪镇·铁头 / craftsman）｜day 0 · afternoon · place `market`｜topic `scarce_buy`｜`MSG_DM`｜标注：`周公文`/tier 1/`other_named`
  > （把刚出炉的枣泥酥往竹篮里码）哟，周公文，你来得巧，这锅是给桂婶家小孙子留的，他昨儿还念叨想吃带枣泥的——你要不先尝半块，回头帮我跟方老师捎个话，问他家阿禾还来不来拿订好的那屉？
- **#5065**｜行号 5066｜`msg_uid` `42:5065`｜说话人 `P013`（青溪镇·铁头 / craftsman）→ 受话人 `P004`（青溪镇·秀娘 / cook）｜day 0 · evening · place `cafe`｜topic `scarce_buy`｜`MSG_DM`｜标注：无呼语位称呼
  > （把铁钳往水桶里一搁，嗤地冒白气）这阵子啥都抢，铁钉都有人囤。桂婶家小孙子那半块我尝了，枣泥甜。阿禾那屉，我捎话。
- **#5732**｜行号 5733｜`msg_uid` `42:5732`｜说话人 `P004`（青溪镇·秀娘 / cook）→ 受话人 `P013`（青溪镇·铁头 / craftsman）｜day 0 · evening · place `community_center`｜topic `scarce_buy`｜`MSG_DM`｜标注：无呼语位称呼
  > （把烤盘里最后一只枣泥酥夹进油纸）你这几天守着炉子，连轴转得够呛吧。
- **#7844**｜行号 7845｜`msg_uid` `42:7844`｜说话人 `P013`（青溪镇·铁头 / craftsman）→ 受话人 `P004`（青溪镇·秀娘 / cook）｜day 0 · evening · place `cafe`｜topic `scarce_buy`｜`MSG_DM`｜标注：无呼语位称呼
  > （拿锉刀蹭了蹭砧子边，火星子溅到鞋面）累是累，炉子不能歇。桂婶家那半块枣泥酥，我给她捎过去。
- **#8200**｜行号 8201｜`msg_uid` `42:8200`｜说话人 `P004`（青溪镇·秀娘 / cook）→ 受话人 `P013`（青溪镇·铁头 / craftsman）｜day 0 · night · place `residence`｜topic `scarce_buy`｜`MSG_DM`｜标注：无呼语位称呼
  > （把油纸角折进纸袋，枣泥酥的甜香还沾在指头上）炉子不能歇，人也得喘口气。桂婶那半块我另包了张红纸，你顺道带过去。趁热吃。
- **#15598**｜行号 15599｜`msg_uid` `42:15598`｜说话人 `P013`（青溪镇·铁头 / craftsman）→ 受话人 `P004`（青溪镇·秀娘 / cook）｜day 0 · night · place `residence`｜topic `scarce_buy`｜`MSG_DM`｜标注：`秀娘`/tier 3/`target_ok`
  > （把铁钳往水桶里一浸，白汽冒起来）秀娘，那批铁钉张家也要，我先给他打二十根。桂婶的红纸包你搁我车斗里。

### 对照段 5′｜`TH-P004-P013-4`（OFF 臂，6 条）

| 项 | 值 |
|---|---|
| 来源文件 | `v2/evidence/n15-off_n16r84_s42/run.jsonl` |
| 日志 sha256 | `da4d248785efefe2caf92fc08821109e44057932812b9012bcf203bc569729d0` |
| thread_id | `TH-P004-P013-4` |
| 消息类型 | `MSG_DM`（全段一致） |
| 参与人（`persona_id` → 显示名/角色） | `P004`→秀娘/cook、`P013`→铁头/craftsman |
| seq 序列 | `3121`, `5065`, `5732`, `7844`, `8197`, `15593` |
| turn_index 序列 | `0`, `1`, `2`, `3`, `4`, `5`（连续） |
| day/slot/place（逐条可变） | day [0]；afternoon/market → evening/cafe → evening/community_center → evening/cafe → night/residence → night/residence |

逐字原文：

- **#3121**｜行号 3122｜`msg_uid` `42:3121`｜说话人 `P004`（青溪镇·秀娘 / cook）→ 受话人 `P013`（青溪镇·铁头 / craftsman）｜day 0 · afternoon · place `market`｜topic `scarce_buy`｜`MSG_DM`｜标注：`周公文`/tier 1/`other_named`
  > （把刚出炉的枣泥酥往竹篮里码）哎，周公文，你来得巧，这锅枣泥酥还烫手呢，桂婶家的小子昨儿就念叨着要，我给他留了两块——你要不要也捎一包回去尝尝？
- **#5065**｜行号 5066｜`msg_uid` `42:5065`｜说话人 `P013`（青溪镇·铁头 / craftsman）→ 受话人 `P004`（青溪镇·秀娘 / cook）｜day 0 · evening · place `cafe`｜topic `scarce_buy`｜`MSG_DM`｜标注：无呼语位称呼
  > （把铁钳往水桶里一浸，白汽窜起）紧俏货？我铺里那批锄头还压着，桂婶家小子倒先抢上酥了。留两块。
- **#5732**｜行号 5733｜`msg_uid` `42:5732`｜说话人 `P004`（青溪镇·秀娘 / cook）→ 受话人 `P013`（青溪镇·铁头 / craftsman）｜day 0 · evening · place `community_center`｜topic `scarce_buy`｜`MSG_DM`｜标注：`铁头哥`/tier 2/`target_ok`
  > （把烤盘里的酥皮边角料拨到一边，油纸窸窣响）铁头哥，你那锄头还搁着没动，倒惦记上桂婶家小子手里那两块酥啦。
- **#7844**｜行号 7845｜`msg_uid` `42:7844`｜说话人 `P013`（青溪镇·铁头 / craftsman）→ 受话人 `P004`（青溪镇·秀娘 / cook）｜day 0 · evening · place `cafe`｜topic `scarce_buy`｜`MSG_DM`｜标注：无呼语位称呼
  > （拿火钳夹起一块烧红的铁块，火星溅到围裙上）这年头啥都抢。昨儿李屠户家为半扇猪排跟人红脸，我这儿倒清静——就剩你案板上那几块酥皮边角，还粘着芝麻。
- **#8197**｜行号 8198｜`msg_uid` `42:8197`｜说话人 `P004`（青溪镇·秀娘 / cook）→ 受话人 `P013`（青溪镇·铁头 / craftsman）｜day 0 · night · place `residence`｜topic `scarce_buy`｜`MSG_DM`｜标注：`铁头哥`/tier 2/`target_ok`
  > （用刮刀铲起粘在烤盘底的芝麻粒）芝麻都粘底了，还惦记酥皮呢。桂婶家小子那两块，是昨儿我塞给他的——他娘病着，嘴里没味。铁头哥，你要馋，明儿我多烤一盘。
- **#15593**｜行号 15594｜`msg_uid` `42:15593`｜说话人 `P013`（青溪镇·铁头 / craftsman）→ 受话人 `P004`（青溪镇·秀娘 / cook）｜day 0 · night · place `residence`｜topic `scarce_buy`｜`MSG_DM`｜标注：`秀娘`/tier 3/`target_ok`
  > （把铁锤往砧子上一搁，锤柄还烫手）秀娘，那盘你留着给桂婶家小子，我这儿有块铁皮，回头给他娘打个暖手的炉子。

<sub>说明：段 5 的 ON/OFF 两臂段是**同 thread_id、两个独立 run**（`code_sha` 不同），只能用于「形态差异」肉眼核对，**不得**当作配对样本或用其算比例。</sub>

## 4. 自检：每条原文在 `run.jsonl` 中逐字命中，且行号 = seq + 1

方法：对每条引用的 `payload.body` 原文执行 `grep -n -F -- <body> <run.jsonl>`（固定串、无正则干扰），要求**命中行数 = 1**、**命中行号 = `seq + 1`**、且该行 `seq` 字段 = 标注的 `seq`。

| 臂 | 段 | thread_id | seq | 实拉命令（行号式，可直接跑） | 命中行号 | 命中数 | seq 对位 | 行号=seq+1 |
|---|---|---|---|---|---|---|---|---|
| ON | 1 | `TH-P013-P004-16` | `23259` | `sed -n '23260p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 23260 | 1 | ✅ | ✅ |
| ON | 1 | `TH-P013-P004-16` | `23867` | `sed -n '23868p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 23868 | 1 | ✅ | ✅ |
| ON | 1 | `TH-P013-P004-16` | `25748` | `sed -n '25749p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 25749 | 1 | ✅ | ✅ |
| ON | 1 | `TH-P013-P004-16` | `27469` | `sed -n '27470p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 27470 | 1 | ✅ | ✅ |
| ON | 1 | `TH-P013-P004-16` | `31604` | `sed -n '31605p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 31605 | 1 | ✅ | ✅ |
| ON | 1 | `TH-P013-P004-16` | `34165` | `sed -n '34166p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 34166 | 1 | ✅ | ✅ |
| OFF | 1 | `TH-P013-P004-16` | `23244` | `sed -n '23245p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 23245 | 1 | ✅ | ✅ |
| OFF | 1 | `TH-P013-P004-16` | `23852` | `sed -n '23853p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 23853 | 1 | ✅ | ✅ |
| OFF | 1 | `TH-P013-P004-16` | `25733` | `sed -n '25734p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 25734 | 1 | ✅ | ✅ |
| OFF | 1 | `TH-P013-P004-16` | `27448` | `sed -n '27449p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 27449 | 1 | ✅ | ✅ |
| OFF | 1 | `TH-P013-P004-16` | `31579` | `sed -n '31580p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 31580 | 1 | ✅ | ✅ |
| OFF | 1 | `TH-P013-P004-16` | `34138` | `sed -n '34139p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 34139 | 1 | ✅ | ✅ |
| ON | 2 | `TH-P011-P003-30` | `38835` | `sed -n '38836p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 38836 | 1 | ✅ | ✅ |
| ON | 2 | `TH-P011-P003-30` | `39712` | `sed -n '39713p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 39713 | 1 | ✅ | ✅ |
| ON | 2 | `TH-P011-P003-30` | `47914` | `sed -n '47915p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 47915 | 1 | ✅ | ✅ |
| ON | 2 | `TH-P011-P003-30` | `52113` | `sed -n '52114p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 52114 | 1 | ✅ | ✅ |
| ON | 2 | `TH-P011-P003-30` | `55500` | `sed -n '55501p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 55501 | 1 | ✅ | ✅ |
| ON | 2 | `TH-P011-P003-30` | `56431` | `sed -n '56432p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 56432 | 1 | ✅ | ✅ |
| OFF | 2 | `TH-P011-P003-30` | `38810` | `sed -n '38811p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 38811 | 1 | ✅ | ✅ |
| OFF | 2 | `TH-P011-P003-30` | `39687` | `sed -n '39688p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 39688 | 1 | ✅ | ✅ |
| OFF | 2 | `TH-P011-P003-30` | `47886` | `sed -n '47887p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 47887 | 1 | ✅ | ✅ |
| OFF | 2 | `TH-P011-P003-30` | `52084` | `sed -n '52085p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 52085 | 1 | ✅ | ✅ |
| OFF | 2 | `TH-P011-P003-30` | `55471` | `sed -n '55472p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 55472 | 1 | ✅ | ✅ |
| OFF | 2 | `TH-P011-P003-30` | `56401` | `sed -n '56402p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 56402 | 1 | ✅ | ✅ |
| ON | 3 | `TH-P006-P003-6` | `4946` | `sed -n '4947p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 4947 | 1 | ✅ | ✅ |
| ON | 3 | `TH-P006-P003-6` | `5671` | `sed -n '5672p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 5672 | 1 | ✅ | ✅ |
| ON | 3 | `TH-P006-P003-6` | `8317` | `sed -n '8318p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 8318 | 1 | ✅ | ✅ |
| ON | 3 | `TH-P006-P003-6` | `11050` | `sed -n '11051p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 11051 | 1 | ✅ | ✅ |
| ON | 3 | `TH-P006-P003-6` | `19192` | `sed -n '19193p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 19193 | 1 | ✅ | ✅ |
| ON | 3 | `TH-P006-P003-6` | `20356` | `sed -n '20357p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 20357 | 1 | ✅ | ✅ |
| OFF | 3 | `TH-P006-P003-6` | `4946` | `sed -n '4947p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 4947 | 1 | ✅ | ✅ |
| OFF | 3 | `TH-P006-P003-6` | `5671` | `sed -n '5672p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 5672 | 1 | ✅ | ✅ |
| OFF | 3 | `TH-P006-P003-6` | `8314` | `sed -n '8315p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 8315 | 1 | ✅ | ✅ |
| OFF | 3 | `TH-P006-P003-6` | `11045` | `sed -n '11046p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 11046 | 1 | ✅ | ✅ |
| OFF | 3 | `TH-P006-P003-6` | `19179` | `sed -n '19180p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 19180 | 1 | ✅ | ✅ |
| OFF | 3 | `TH-P006-P003-6` | `20341` | `sed -n '20342p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 20342 | 1 | ✅ | ✅ |
| ON | 4 | `TH-P015-P011-40` | `60821` | `sed -n '60822p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 60822 | 1 | ✅ | ✅ |
| ON | 4 | `TH-P015-P011-40` | `61583` | `sed -n '61584p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 61584 | 1 | ✅ | ✅ |
| ON | 4 | `TH-P015-P011-40` | `63165` | `sed -n '63166p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 63166 | 1 | ✅ | ✅ |
| ON | 4 | `TH-P015-P011-40` | `73015` | `sed -n '73016p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 73016 | 1 | ✅ | ✅ |
| ON | 4 | `TH-P015-P011-40` | `81406` | `sed -n '81407p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 81407 | 1 | ✅ | ✅ |
| ON | 4 | `TH-P015-P011-40` | `84546` | `sed -n '84547p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 84547 | 1 | ✅ | ✅ |
| OFF | 4 | `TH-P015-P011-40` | `60787` | `sed -n '60788p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 60788 | 1 | ✅ | ✅ |
| OFF | 4 | `TH-P015-P011-40` | `61549` | `sed -n '61550p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 61550 | 1 | ✅ | ✅ |
| OFF | 4 | `TH-P015-P011-40` | `63131` | `sed -n '63132p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 63132 | 1 | ✅ | ✅ |
| OFF | 4 | `TH-P015-P011-40` | `72976` | `sed -n '72977p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 72977 | 1 | ✅ | ✅ |
| OFF | 4 | `TH-P015-P011-40` | `81358` | `sed -n '81359p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 81359 | 1 | ✅ | ✅ |
| OFF | 4 | `TH-P015-P011-40` | `84494` | `sed -n '84495p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 84495 | 1 | ✅ | ✅ |
| ON | 5 | `TH-P004-P013-4` | `3121` | `sed -n '3122p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 3122 | 1 | ✅ | ✅ |
| ON | 5 | `TH-P004-P013-4` | `5065` | `sed -n '5066p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 5066 | 1 | ✅ | ✅ |
| ON | 5 | `TH-P004-P013-4` | `5732` | `sed -n '5733p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 5733 | 1 | ✅ | ✅ |
| ON | 5 | `TH-P004-P013-4` | `7844` | `sed -n '7845p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 7845 | 1 | ✅ | ✅ |
| ON | 5 | `TH-P004-P013-4` | `8200` | `sed -n '8201p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 8201 | 1 | ✅ | ✅ |
| ON | 5 | `TH-P004-P013-4` | `15598` | `sed -n '15599p' v2/evidence/n15-on_n16r84_s42/run.jsonl` | 15599 | 1 | ✅ | ✅ |
| OFF | 5 | `TH-P004-P013-4` | `3121` | `sed -n '3122p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 3122 | 1 | ✅ | ✅ |
| OFF | 5 | `TH-P004-P013-4` | `5065` | `sed -n '5066p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 5066 | 1 | ✅ | ✅ |
| OFF | 5 | `TH-P004-P013-4` | `5732` | `sed -n '5733p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 5733 | 1 | ✅ | ✅ |
| OFF | 5 | `TH-P004-P013-4` | `7844` | `sed -n '7845p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 7845 | 1 | ✅ | ✅ |
| OFF | 5 | `TH-P004-P013-4` | `8197` | `sed -n '8198p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 8198 | 1 | ✅ | ✅ |
| OFF | 5 | `TH-P004-P013-4` | `15593` | `sed -n '15594p' v2/evidence/n15-off_n16r84_s42/run.jsonl` | 15594 | 1 | ✅ | ✅ |

**自检结论**：共引用 60 条消息，全部逐字命中且行号/seq 对位一致 = **60/60**，异常 **0** 条。

**逐条实拉命令已落盘**：`/root/.jiuwenswarm/.agent_teams/jiuwen_team_cron___1a18e814975_abda2a2213c6/team-workspace/c36/c36-grep-checks.sh`（sha256 `e12314151004aa19fe24bccdef303299cc6d79830290dd52b9c0077b491665e4`，共 60 条 `grep -n -F` 命令，可直接 `bash` 执行复核）。

复核者可直接重放（示例取表中第一条）：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
grep -n -F -- '（攥着铁钳敲了敲砧子上那块犁头）哎，秀娘，你灶上那锅糊糊先匀我一碗，回头给你家锄头加个钢口。饿得慌。' '/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/n15-on_n16r84_s42/run.jsonl'
```

**机械口径复核**（按行号取行、核对 seq 与 msg_uid；本批两臂实测 `行号 = seq + 1` 全量成立）：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
sed -n '23260p' v2/evidence/n15-on_n16r84_s42/run.jsonl | python3 -c 'import json,sys; o=json.load(sys.stdin); print(o["seq"], o["payload"]["msg_uid"])'
```

## 5. 截图证据（现场渲染，**只作展示、不进判据**）

渲染工具：仓库既有 `tools/metrics/render_shots.py`（`--help` 已核实参数：`--run-dir/--batch-id/--outdir/--views/--timeout`）；渲染时 HEAD = `46cfd9e7a163fde88b0a9392c704a858b152d3aa`（`exp/n36-scene-anchor`）。
渲染链：`run.jsonl → gen_threads.py → threads_<batch>.json → 本地静态服务 → shot.py(Chromium 现截) → PNG`；服务根为临时目录 + 符号链接，**未在 `code/frontend/` 下写任何文件**。

| # | 视图 | 绝对路径 | sha256 | 尺寸 | 像素自检（distinct_colors / top_color_frac / 非背景占比） |
|---|---|---|---|---|---|
| 1 | chat（ON 臂） | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/c36_shots/on/c36-on-chat-d74f7d00.png` | `ecc6278afedef6fc927ba229b40d67fdb76b699ec7e873e20167c733a4797cb6` | 1400×900 | 24358 / 0.1599 / 0.5639（OK） |
| 2 | rhythm（ON 臂） | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/c36_shots/on/c36-on-rhythm-d74f7d00.png` | `18d55a026e696013c61e9a305824808522b957ebeac4210580a988f8ac1008e9` | 1300×1050 | 22852 / 0.1954 / 0.5427（OK） |
| 3 | chat（OFF 臂） | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/c36_shots/off/c36-off-chat-da4d2487.png` | `55dfa4fdbff1bbe303f9527e84740f5ca1945362c054e70d7ed3ba8e91afb359` | 1400×900 | 24443 / 0.1599 / 0.5640（OK） |
| 4 | rhythm（OFF 臂） | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/c36_shots/off/c36-off-rhythm-da4d2487.png` | `3f80f74dc98b7094815f4bd36ee14c81b78c850f24cc82e83102dd0d7f3219d8` | 1300×1050 | 22820 / 0.1954 / 0.5428（OK） |

**渲染命令（逐张原样取自 `render_report_c36-*.json` 的 `triplet.render_cmd`）**

```text
[ON/chat] /opt/openjiuwen/workswarm-venv/bin/python3 /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code/frontend/tools/shot.py --url http://127.0.0.1:43077/dialogue.html?still=1&multi=1&min=0&sort=turns&data=sample/dialogue_c36-on/threads.json --out /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/c36_shots/on/c36-on-chat-d74f7d00.png --width 1400 --height 900 --timeout 240.0 --retry-blank 2 --no-blank-check
[ON/rhythm] /opt/openjiuwen/workswarm-venv/bin/python3 /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code/frontend/tools/shot.py --url http://127.0.0.1:43077/dialogue.html?still=1&multi=1&min=0&view=rhythm&data=sample/dialogue_c36-on/threads.json --out /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/c36_shots/on/c36-on-rhythm-d74f7d00.png --width 1300 --height 1050 --timeout 240.0 --retry-blank 2 --no-blank-check
[OFF/chat] /opt/openjiuwen/workswarm-venv/bin/python3 /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code/frontend/tools/shot.py --url http://127.0.0.1:46457/dialogue.html?still=1&multi=1&min=0&sort=turns&data=sample/dialogue_c36-off/threads.json --out /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/c36_shots/off/c36-off-chat-da4d2487.png --width 1400 --height 900 --timeout 240.0 --retry-blank 2 --no-blank-check
[OFF/rhythm] /opt/openjiuwen/workswarm-venv/bin/python3 /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code/frontend/tools/shot.py --url http://127.0.0.1:46457/dialogue.html?still=1&multi=1&min=0&view=rhythm&data=sample/dialogue_c36-off/threads.json --out /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/c36_shots/off/c36-off-rhythm-da4d2487.png --width 1300 --height 1050 --timeout 240.0 --retry-blank 2 --no-blank-check
```

**gen_threads 命令（threads.json 派生，逐批一条）**

```text
[ON] /opt/openjiuwen/workswarm-venv/bin/python3 /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code/frontend/tools/gen_threads.py --log /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/n15-on_n16r84_s42/run.jsonl --meta /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/n15-on_n16r84_s42/meta.json --out /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/c36_shots/on/threads_c36-on.json --label c36-on
[OFF] /opt/openjiuwen/workswarm-venv/bin/python3 /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code/frontend/tools/gen_threads.py --log /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/n15-off_n16r84_s42/run.jsonl --meta /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/n15-off_n16r84_s42/meta.json --out /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/c36_shots/off/threads_c36-off.json --label c36-off
```

**非空白判据**：`distinct_colors ≥ 200` 且 `top_color_frac ≤ 0.99`（深色 UI 不按单色占比判死；该判据由 `render_shots.py` 自算，`blank_check=off` 关闭了 `shot.py` 对深色页会误判的单色判据）。四张图实际 distinct_colors 均 > 2.2 万、top_color_frac ≤ 0.20、非背景占比 ≈ 0.54–0.56 ⇒ 非空白。

**重渲染声明**：渲染只依赖 `run.jsonl` 内容，重跑得**内容等价的图**，但 PNG 字节（sha256）**不会相同**（时间戳/渲染抖动）。上表 sha256 是本轮实际落盘字节的 sha，复核须以本表为准。

**图不进判据**：上表四张图不参与任何指标、闸线或「提升」判断；如需看图，仅用于「页面上确实显示了真实日志派生出的对话/节奏视图」这一存在性展示。

**`render.log`**：`v2/evidence/c36_shots/render.log`（sha256 `2bf9ddc506cef7e2e74718ce0e48b71decc63ef2b6447469f96b48bf96e88770`，7457 B）——内含渲染时 HEAD、两条渲染命令原文、两次渲染的 stdout 尾部与逐张像素自检/sha 摘要。

## 6. 候选池与排除理由（ON 臂全部 ≥6 条线程，逐条处置）

候选口径：两臂 `MSG_*` 重建线程，取 **条数 ≥ 6**（满足「同线程连续 ≥6 条」要求）。`称呼命中` = 呼语位识别到称呼的条数；`形式` = 该线程出现过的去重称呼形式（尺子标注）。缺陷判定 = `self_name` 或 `other_named`。

| thread_id | 类型 | 条数 | 称呼命中 | 形式（tier） | 缺陷 | 处置 |
|---|---|---|---|---|---|---|
| `TH-P014-Gplace-plaza-78` | GROUP×15 | 15 | 10 | 兰姐(tier2)、巧儿(tier3) | 0 | 排除：多人群聊（GROUP×15），说话人→受话人不唯一，无法逐条绑定「谁叫谁」 |
| `TH-P009-Gplace-hall-67` | GROUP×18 | 18 | 9 | 金先生(tier1)、兰姐(tier2)、巧儿(tier3) | 0 | 排除：多人群聊（GROUP×18），说话人→受话人不唯一，无法逐条绑定「谁叫谁」 |
| `TH-P016-Gplace-town_hall-76` | GROUP×15 | 15 | 9 | 兰姐(tier2)、月牙(tier3)、老周(tier3) | 0 | 排除：多人群聊（GROUP×15），说话人→受话人不唯一，无法逐条绑定「谁叫谁」 |
| `TH-P012-Gplace-market-64` | GROUP×13 | 13 | 9 | 巧儿姐(tier2)、桂婶(tier2)、秀娘(tier3)、巧儿(tier3) | 0 | 排除：多人群聊（GROUP×13），说话人→受话人不唯一，无法逐条绑定「谁叫谁」 |
| `TH-P013-Gplace-library-61` | GROUP×13 | 13 | 8 | 陈医(tier1)、兰姐(tier2)、铁头(tier3) | 0 | 排除：多人群聊（GROUP×13），说话人→受话人不唯一，无法逐条绑定「谁叫谁」 |
| `TH-P012-Gplace-school-73` | GROUP×13 | 13 | 7 | 桂婶(tier2)、巧儿(tier3) | 0 | 排除：多人群聊（GROUP×13），说话人→受话人不唯一，无法逐条绑定「谁叫谁」 |
| `TH-P009-P014-12` | DM×6 | 6 | 6 | 金先生(tier1)、巧儿(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P016-P011-39` | DM×6 | 6 | 6 | 兰姐(tier2)、小满(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P004-Gplace-market-76` | GROUP×12 | 12 | 5 | 秀娘(tier3)、铁头(tier3) | 0 | 排除：多人群聊（GROUP×12），说话人→受话人不唯一，无法逐条绑定「谁叫谁」 |
| `TH-P001-P009-12` | DM×6 | 6 | 5 | 金先生(tier1)、老周(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P009-P008-24` | DM×6 | 6 | 5 | 周公文(tier1)、金先生(tier1)、周哥(tier2) | 0 | 未选：称呼为身份敬称「周公文」(tier 1)/「周哥」(tier 2)，「周公文」与 P008 本名完全重合，复核者易把「称呼形式变化」误读为 other_named 缺陷 ⇒ 避免歧义 |
| `TH-P012-P015-4` | DM×6 | 6 | 5 | 桂婶(tier2)、五味(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P013-P004-15` | DM×6 | 6 | 5 | 秀娘(tier3)、铁头(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P015-Gplace-town_hall-64` | GROUP×11 | 11 | 4 | 五味叔(tier2)、五味(tier3)、小满(tier3)、老石(tier3) | 0 | 排除：多人群聊（GROUP×11），说话人→受话人不唯一，无法逐条绑定「谁叫谁」 |
| `TH-P001-P005-39` | DM×6 | 6 | 4 | 陈医(tier1)、桂婶(tier2)、老周(tier3) | 1 | 排除：含同类缺陷（self_name/other_named），与已选段 3/4/5 的缺陷类型重复；该段称呼形式单一，展示价值低于已选段 ⇒ 可作复核备选 |
| `TH-P001-P013-48` | DM×6 | 6 | 4 | 铁头(tier3)、老周(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P009-P007-42` | DM×6 | 6 | 4 | 金先生(tier1)、阿林(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P009-P015-52` | DM×6 | 6 | 4 | 金先生(tier1)、五味(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P012-P014-36` | DM×6 | 6 | 4 | 桂婶(tier2)、巧儿(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P016-P005-0` | DM×6 | 6 | 4 | 陈医(tier1)、兰姐(tier2) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P016-P015-16` | DM×6 | 6 | 4 | 兰姐(tier2)、五味(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P004-P014-43` | DM×6 | 6 | 3 | 秀娘(tier3)、巧儿(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P006-P003-6` | DM×6 | 6 | 3 | 方老师(tier1)、阿禾(tier3) | 1 | **入选 → 段 3** |
| `TH-P006-P016-49` | DM×6 | 6 | 3 | 方老师(tier1)、兰姐(tier2) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P007-P009-60` | DM×6 | 6 | 3 | 金先生(tier1)、阿林(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P008-P002-54` | DM×6 | 6 | 3 | 老周(tier3)、老石(tier3) | 1 | 排除：含同类缺陷（self_name/other_named），与已选段 3/4/5 的缺陷类型重复；该段称呼形式单一，展示价值低于已选段 ⇒ 可作复核备选 |
| `TH-P009-P008-25` | DM×6 | 6 | 3 | 周公文(tier1)、金先生(tier1) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P009-P015-51` | DM×6 | 6 | 3 | 金先生(tier1)、五味(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P011-P003-30` | DM×6 | 6 | 3 | 阿禾姐(tier2)、小满(tier3)、阿禾(tier3) | 0 | **入选 → 段 2** |
| `TH-P013-P004-16` | DM×6 | 6 | 3 | 铁头哥(tier2)、秀娘(tier3)、铁头(tier3) | 0 | **入选 → 段 1** |
| `TH-P014-P011-1` | DM×6 | 6 | 3 | 巧儿姐(tier2)、巧儿(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P014-P015-25` | DM×6 | 6 | 3 | 五味(tier3)、巧儿(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P015-P011-40` | DM×6 | 6 | 3 | 小满(tier3) | 1 | **入选 → 段 4** |
| `TH-P016-P014-51` | DM×6 | 6 | 3 | 兰姐(tier2)、巧儿(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P003-P005-54` | DM×6 | 6 | 2 | 陈医(tier1)、阿禾(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P003-P008-42` | DM×6 | 6 | 2 | 周叔(tier2)、阿禾(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P004-Gplace-market-75` | GROUP×6 | 6 | 2 | 秀娘(tier3) | 0 | 排除：多人群聊（GROUP×6），说话人→受话人不唯一，无法逐条绑定「谁叫谁」 |
| `TH-P004-P013-4` | DM×6 | 6 | 2 | 周公文(tier1)、秀娘(tier3) | 1 | **入选 → 段 5** |
| `TH-P006-P003-7` | DM×6 | 6 | 2 | 方老师(tier1)、阿禾(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P006-P007-55` | DM×6 | 6 | 2 | 方老师(tier1)、阿林(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P008-P002-55` | DM×6 | 6 | 2 | 老石(tier3) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P010-P002-43` | DM×6 | 6 | 2 | 老石(tier3) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P010-P009-0` | DM×6 | 6 | 2 | 金先生(tier1) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P010-P009-1` | DM×6 | 6 | 2 | 金先生(tier1)、金哥(tier2) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P010-P009-37` | DM×6 | 6 | 2 | 金先生(tier1) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P011-P008-13` | DM×6 | 6 | 2 | 周公文(tier1)、周叔(tier2) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P011-P013-25` | DM×6 | 6 | 2 | 铁头哥(tier2) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P012-P001-18` | DM×6 | 6 | 2 | 老周(tier3) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P013-P008-42` | DM×6 | 6 | 2 | 周公文(tier1)、铁头(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P014-P015-24` | DM×6 | 6 | 2 | 五味(tier3) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P015-P003-42` | DM×6 | 6 | 2 | 五味(tier3)、阿禾(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P016-P002-28` | DM×6 | 6 | 2 | 老石(tier3) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P016-P013-25` | DM×6 | 6 | 2 | 兰姐(tier2)、铁头(tier3) | 0 | 排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选 |
| `TH-P001-P007-28` | DM×6 | 6 | 1 | 阿林(tier3) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P001-P013-49` | DM×6 | 6 | 1 | 铁头(tier3) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P005-P006-31` | DM×6 | 6 | 1 | 方老师(tier1) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P005-P013-39` | DM×6 | 6 | 1 | 铁头(tier3) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P007-P005-19` | DM×6 | 6 | 1 | 陈医(tier1) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P008-P007-6` | DM×6 | 6 | 1 | 阿林(tier3) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P010-P004-28` | DM×6 | 6 | 1 | 兰姐(tier2) | 1 | 排除：含同类缺陷（self_name/other_named），与已选段 3/4/5 的缺陷类型重复；该段称呼形式单一，展示价值低于已选段 ⇒ 可作复核备选 |
| `TH-P011-P008-12` | DM×6 | 6 | 1 | 周公文(tier1) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P011-P010-55` | DM×6 | 6 | 1 | 小满(tier3) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P014-P004-54` | DM×6 | 6 | 1 | 巧儿(tier3) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P014-P011-0` | DM×6 | 6 | 1 | 小满(tier3) | 1 | 排除：含同类缺陷（self_name/other_named），与已选段 3/4/5 的缺陷类型重复；该段称呼形式单一，展示价值低于已选段 ⇒ 可作复核备选 |
| `TH-P016-P002-7` | DM×6 | 6 | 1 | 老石(tier3) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P016-P015-15` | DM×6 | 6 | 1 | 五味(tier3) | 0 | 排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示 |
| `TH-P004-P002-0` | DM×6 | 6 | 0 | 无 | 0 | 排除：全段无呼语位称呼，无法承担「称呼×关系演化」主题 |
| `TH-P010-P012-31` | DM×6 | 6 | 0 | 无 | 0 | 排除：全段无呼语位称呼，无法承担「称呼×关系演化」主题 |
| `TH-P011-P010-54` | DM×6 | 6 | 0 | 无 | 0 | 排除：全段无呼语位称呼，无法承担「称呼×关系演化」主题 |
| `TH-P012-P001-19` | DM×6 | 6 | 0 | 无 | 0 | 排除：全段无呼语位称呼，无法承担「称呼×关系演化」主题 |

候选池合计：ON 臂 ≥6 条线程 **70** 个（<6 条线程不进入候选池，另记 ON 臂线程总数 206）；入选 5 个、排除 65 个。

**未进入候选池的批次**：`n36-on_n16r84_s42`（在途未收批，见 §1）、`cycle36_f3_off_n16r84_seed42`（旧批：起跑 2026-10-29T12:14、`code_sha 80c9ed7`，**不属于本周期两臂**，不作为本文件素材）。

## 7. 能与不能

### 能证明
1. §3 每条消息的 `seq`、`msg_uid`、说话人/受话人显示名与角色、`day/slot/place`、正文，都能在对应 `run.jsonl` 中逐字命中（§4 逐条落盘命中行号与 seq 对位）；
2. §3 段 3/4/5 的三条缺陷在**原文层面**可直接肉眼核对（称呼与自己/第三人重合），不需要任何指标：段 3 `方老师` 自称、段 4 `小满` 自称、段 5 `周公文` 叫错人；
3. §5 四张 PNG 是**本轮现场渲染**：渲染命令、源日志 sha256、渲染时 HEAD、像素自检逐张落盘（`render_report_c36-*.json`），非旧图、非拼图、非示意图；
4. 两臂开关证据来自 `switch_proof.txt`（`/proc/<pid>/environ` 取样）原文，本文件未改写。

### 不能证明
1. **不能**由这 5 段样本给出任何「称呼覆盖率/错称率/演化幅度」数字 —— 样本是**定向挑选**（非分层随机），尤其 3 段缺陷是**主动检索反例**的结果，不能外推为臂级比例；比例/显著性一律以证据审计与复算件为准；
2. **不能**从 ON/OFF 同 thread 的形态差异读「开关有效」 —— 两臂 `code_sha` 不同、World 演化路径不同、且 LLM 缓存命中使两臂部分输出近似（两臂 `meta.llm_cached` 均为 1666、`llm_cached_ratio` 均为 0.4896），本文件只登记「肉眼可见的形态差异」；
3. **不能**把 §3 的 OFF 段当作「同一局的另一臂配对样本」；
4. **不能**用 §5 的图证明任何效果 —— 图不进判据，仅证明「页面可渲染真实日志派生的对话/节奏视图」；
5. 称呼标注依赖 `v2/refs/address-ordinal.yaml`（`dc4ce327ff8e0a77d34545903e8589ea97429a30c9b26bf0ed9d972eda122d95`）与 `code/config/personas.json`（`08d11eb36d644e55db0c9b7e00adccb81613d50476927e3acf07117f7f970f7d`）**先冻结**的口径；tier 数字是社区常识约定（有序性是判断、不是测量），换词表会改变 tier 标注。
