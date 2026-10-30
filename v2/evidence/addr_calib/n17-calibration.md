# N-17 对拍：`addr_error_rate`（D10）vs 官方 `L-10 self_address_error_rate`

- 生成时间：`2026-10-30T22:06:05+0800`
- 仓库 HEAD（**读日志时刻**）：`2ad74a56c7d8570bfd10d7b55e55ce40ecc8bac6`（分支 `feat/round-D10-address-drift`）
- 对拍器：`tools/addr_calib/n17_calibrate.py` sha256 `cf8441906d03d461510a3fab5cf72db8f062de50ae426ca27b96ca4d2090c46a`
- 性质：**只读核算**。不跑批、不调 LLM、不改 `code/{life,orchestration,config,engine}`。

## §0 一句话结论

**这两个数不是同一个量，不能互相替代，也不构成「两个口径不一致需修一个」的问题**：`addr_error_rate` 测「**在呼语位把谁叫成谁**」（叫成自己 / 叫成第三者），官方 `L-10` 测「**用第一人称把自己说成别人**」（`我(是|叫)X`）。本批 5 份日志里，两者分子**逐条零重叠**，分母规模差一个量级（几十 vs 174/191）。因此 D10 §0.5 的 5 个 `addr_error_rate` 读数只能作为「称呼错指率」的**描述量**，**不得**被写成「官方 L-10 的另一种算法」。

## §1 逐字段差异（读代码确认，行号可原位核对）

| 字段 | `addr_error_rate`（tools/metrics/address_drift.py） | 官方 `L-10`（tools/d5/dialogue_metrics.py） | 说明 |
|---|---|---|---|
| 口径定义（测的是什么现象） | **称呼错指**：说话人在**呼语位**叫出的名字，指向的不是当前对话对象（叫成自己 = self_name；叫成第三者 = other_named） | **第一人称身份自述错误**：正文出现「我(，)?(是|叫|乃|就是)?<另一位居民的名字>」⇒ 说话人把自己说成别人（L-10_self_address_error_rate） | 两者是**不同构念**：一个测「叫谁」，一个测「说我是谁」。数值不可互相替代。 |
| 代码位置 | tools/metrics/address_drift.py:254-271（指向分类）、:366-369、:422-435（汇总）；复算入口 `compute()` | tools/d5/dialogue_metrics.py:919-932（分子/分母循环）、:1011-1012（出数）；复算入口 `compute()` 内的 `L_wording` 块 | 任务书说官方实现在 `code/obs/` 下，**与仓库不符**；`code/obs/` 中 grep 不到 `self_address_error`/`L-10`，唯一实现在 tools/d5。 |
| 统计单位 | **MSG 条**，且必须是「呼语位命中具名称呼 **且** 指向可判（有明确 addressee）」的消息 | **MSG 条**，只要正文含自称代词（我/俺/咱）**或**含他人名字 | 单位都是 MSG 条 ⇒ 形式上同类；差别在**入池条件**（见下两行）。 |
| 分母取法 | `n_named_addr_judgeable = target_ok + self_name + other_named`（排除 generic 通用称呼、排除 unknown_target 指向不可判） | `L-10_denominator = cand`：正文含 我/俺/咱 **或** 含任一他人 display_name 的消息条数（什么都不排除，也不要求有称呼） | 官方分母天然接近全量 MSG（本批 174/191），addr 分母只有几十条量级 ⇒ 两率的分母规模差一个量级。 |
| 预处理 / 去重规则 | 先剥「说话人标签前缀」（仅当标签文本是某居民基名）→ 再剥 `（…）/(…)` 括注 → 词表最长优先匹配 → 同句多命中取**最靠前**一个；**一句只取一个称呼**（取到即止） | **不做任何预处理**：不剥括注、不剥标签前缀，直接在 `body` 原文上跑正则；`break` 保证**一条消息最多计 1 次分子** | addr 剥旁白 ⇒ 括注里的名字不算称呼；官方把括注里的名字也算进「提到他人」⇒ 分母被抬高。 |
| 排除条件 | ① `generic` 通用称呼（师傅/老板…，指向不可判）整类排除；② `unknown_target`（公开场合无明确对象）排除；③ 非呼语位的「提及」不计入 | **无排除**：只排除说话人**自己**的名字（`pid != from`）；他人名字无论在句子哪个位置都算 | 官方不区分「称呼」与「提及」，也不区分指向。 |
| 分子匹配方式 | 词表驱动（`v2/refs/address-ordinal.yaml` 冻结件 + personas 派生形式，含 叔/婶/师傅 等后缀变体），按 owner 集合判指向 | **单一正则**：`我[，,]?\s*(?:是|叫|乃|就是)?\s*<他人 display_name>`；名字集合 = personas.json 的基名（去 `青溪镇·` 前缀），**不含**任何后缀变体（石叔/石师傅 等） | 官方只认基名（老石/秀娘），addr 认一整个词表家族 ⇒ 识别面不同。 |
| 「自称」判定的方向 | `self_name` = 说话人**在呼语位叫出自己名字**（如 P002 对 P004 说「老石，早。」） | 命中 = 说话人**用第一人称说出别人名字**（「我是老石」）——这与 addr 的 `self_name` **不是同一事件** | 两侧都用「自称/自我」字样，但**事件方向相反**，是最容易被误读成「同口径」的地方。 |

## §2 逐份对拍表（同一批日志，两口径各算一次）

| run | run.jsonl sha256 | code_sha | addr 分母 | addr 分子（自称+错称） | `addr_error_rate` | 官方分母 | 官方分子 | `L-10` | 单位 | admission |
|---|---|---|---|---|---|---|---|---|---|---|
| `d9m-ab-off_n16r24_s42` | `5f1dda97633ccf0b…` | `3176048a` | 59 | 2（self 0 + other 2） | 3.39% | 174 | 0 | 0.00% | MSG 条（addr：呼语位具名且指向可判；官方：含自称代词或他人名） | ADMITTED（FAIL 检查：无） |
| `d9m-ab-on_n16r24_s42` | `2edc751c5a32d132…` | `3176048a` | 67 | 0（self 0 + other 0） | 0.00% | 172 | 0 | 0.00% | MSG 条（addr：呼语位具名且指向可判；官方：含自称代词或他人名） | ADMITTED（FAIL 检查：无） |
| `d9s-off_n16r24_s42` | `bd6623c209641bbe…` | `05526e0d` | 68 | 2（self 2 + other 0） | 2.94% | 165 | 0 | 0.00% | MSG 条（addr：呼语位具名且指向可判；官方：含自称代词或他人名） | ADMITTED（FAIL 检查：无） |
| `d9s-on_n16r24_s42` | `0a50484d0fce2933…` | `05526e0d` | 70 | 6（self 5 + other 1） | 8.57% | 172 | 0 | 0.00% | MSG 条（addr：呼语位具名且指向可判；官方：含自称代词或他人名） | ADMITTED（FAIL 检查：无） |
| `round1_narration_default_n16r24_s42` | `ca108da9f90031f7…` | `dfe6d5b2` | 74 | 1（self 1 + other 0） | 1.35% | 172 | 0 | 0.00% | MSG 条（addr：呼语位具名且指向可判；官方：含自称代词或他人名） | ADMITTED（FAIL 检查：无） |

> 完整 sha256 与各级分量见 `n17_calibration.json` 的 `runs[].log_sha256` / `runs[].addr` / `runs[].official`。

## §3 逐份明细（分母/分子/交叉表/复刻校验）

### d9m-ab-off_n16r24_s42

- 日志：`v2/evidence/d9m-ab-off_n16r24_s42/run.jsonl`，sha256 `5f1dda97633ccf0b3f7d2b279c39a43752db7d945a2ca6f9133e0b2bc9106ed5`，meta `code_sha=3176048a39f0429204adbdb9eac7a975bfe10c72`，模型 `DeepSeek-Flash`
- MSG 总数：addr 侧读到 `191`，官方侧读到 `191`（两侧 `MSG_TYPES` 集合差异：addr 收 `MSG*` 前缀全部，官方只收 `MSG_DM/MSG_PUBLIC/MSG_GROUP` ⇒ 本批无差异）
- addr：分母 `59`（target_ok 57 + self_name 0 + other_named 2），排除 generic 0 / unknown_target 2；分子 `2` ⇒ `3.39%`
- 官方：分母 `174`，分子 `0` ⇒ `0.00%`
- 交叉表（消息级）：双方都在分母 `59`；仅 addr 分母 `0`；仅官方分母 `115`；都不在 `17`
- 分子重叠：双方都计 `0`；仅 addr `2`；仅官方 `0`
- 强行换到同一分母（MSG 总数 `191`，**仅为描述，不是任何一方的口径**）：addr `2/191` = 1.05% vs 官方 `0/191` = 0.00%
- 复刻校验：addr 复刻 vs `compute()` = PASS；官方复刻 vs CLI = PASS
- **与 D10 已发布读数对拍**：D10 `v2/evidence/d10_address_drift/d9m-ab-off_n16r24_s42.json` 记 `2/59` = `0.03389830508474576`；本次复算 `2/59` = `0.03389830508474576` ⇒ **逐位一致**；同尺子 sha=True，同日志 sha=True
- 差异原因标签计数：{"ADDR_MISADDR_VOCATIVE_NOT_SELFSTATEMENT": 2, "OFFICIAL_DEN_ONLY": 115}

| seq | 类型 | 说话人 | addr 指向 | addr 称呼 | 官方命中名 | 原文（截 60 字） | 归因 |
|---|---|---|---|---|---|---|---|
| 3121 | MSG_DM | P004 | other_named | 周公文（词表 owner：P008） | — | 哟，我这刚出炉的枣泥酥还烫着手呢，周公文你来得巧，先尝一块——你家那口子不是念叨着要买紧俏货嘛，我留了两包在柜台底下，你说这算不算赶早不如赶巧？ | ADDR_MISADDR_VOCATIVE_NOT_SELFSTATEMENT：错称发生在**呼语位**（「周公文，…」），不是第一人称自述，官方正则不命中 |
| 23253 | MSG_DM | P013 | other_named | 周公文（词表 owner：P008） | — | 哟，周公文你手里那袋糙米先匀我两升，我家灶上还炖着陈医他娘给的药罐子，饿得我锤子都抡不动了。先赊着。 | ADDR_MISADDR_VOCATIVE_NOT_SELFSTATEMENT：错称发生在**呼语位**（「周公文，…」），不是第一人称自述，官方正则不命中 |

### d9m-ab-on_n16r24_s42

- 日志：`v2/evidence/d9m-ab-on_n16r24_s42/run.jsonl`，sha256 `2edc751c5a32d1328ed5834ab169d29c5c457cbe7b1d5abe3146d7840df6a795`，meta `code_sha=3176048a39f0429204adbdb9eac7a975bfe10c72`，模型 `DeepSeek-Flash`
- MSG 总数：addr 侧读到 `191`，官方侧读到 `191`（两侧 `MSG_TYPES` 集合差异：addr 收 `MSG*` 前缀全部，官方只收 `MSG_DM/MSG_PUBLIC/MSG_GROUP` ⇒ 本批无差异）
- addr：分母 `67`（target_ok 67 + self_name 0 + other_named 0），排除 generic 0 / unknown_target 3；分子 `0` ⇒ `0.00%`
- 官方：分母 `172`，分子 `0` ⇒ `0.00%`
- 交叉表（消息级）：双方都在分母 `67`；仅 addr 分母 `0`；仅官方分母 `105`；都不在 `19`
- 分子重叠：双方都计 `0`；仅 addr `0`；仅官方 `0`
- 强行换到同一分母（MSG 总数 `191`，**仅为描述，不是任何一方的口径**）：addr `0/191` = 0.00% vs 官方 `0/191` = 0.00%
- 复刻校验：addr 复刻 vs `compute()` = PASS；官方复刻 vs CLI = PASS
- **与 D10 已发布读数对拍**：D10 `v2/evidence/d10_address_drift/d9m-ab-on_n16r24_s42.json` 记 `0/67` = `0.0`；本次复算 `0/67` = `0.0` ⇒ **逐位一致**；同尺子 sha=True，同日志 sha=True
- 差异原因标签计数：{"OFFICIAL_DEN_ONLY": 105}
- **分子级差异：无**（两口径分子无交集也无分歧，即侧重的现象完全不同）

### d9s-off_n16r24_s42

- 日志：`v2/evidence/d9s-off_n16r24_s42/run.jsonl`，sha256 `bd6623c209641bbeff1f72df6e0e843d756ef395eb7898571acf3dae0ad4be4c`，meta `code_sha=05526e0d9ec9775876b6c7c5764fa70fa4c5b26a`，模型 `DeepSeek-Flash`
- MSG 总数：addr 侧读到 `191`，官方侧读到 `191`（两侧 `MSG_TYPES` 集合差异：addr 收 `MSG*` 前缀全部，官方只收 `MSG_DM/MSG_PUBLIC/MSG_GROUP` ⇒ 本批无差异）
- addr：分母 `68`（target_ok 66 + self_name 2 + other_named 0），排除 generic 0 / unknown_target 2；分子 `2` ⇒ `2.94%`
- 官方：分母 `165`，分子 `0` ⇒ `0.00%`
- 交叉表（消息级）：双方都在分母 `68`；仅 addr 分母 `0`；仅官方分母 `97`；都不在 `26`
- 分子重叠：双方都计 `0`；仅 addr `2`；仅官方 `0`
- 强行换到同一分母（MSG 总数 `191`，**仅为描述，不是任何一方的口径**）：addr `2/191` = 1.05% vs 官方 `0/191` = 0.00%
- 复刻校验：addr 复刻 vs `compute()` = PASS；官方复刻 vs CLI = PASS
- **与 D10 已发布读数对拍**：D10 `v2/evidence/d10_address_drift/d9s-off_n16r24_s42.json` 记 `2/68` = `0.029411764705882353`；本次复算 `2/68` = `0.029411764705882353` ⇒ **逐位一致**；同尺子 sha=True，同日志 sha=True
- 差异原因标签计数：{"ADDR_SELFNAME_NOT_IN_OFFICIAL_UNIVERSE": 2, "OFFICIAL_DEN_ONLY": 97}

| seq | 类型 | 说话人 | addr 指向 | addr 称呼 | 官方命中名 | 原文（截 60 字） | 归因 |
|---|---|---|---|---|---|---|---|
| 15589 | MSG_DM | P013 | self_name | 铁头（词表 owner：P013） | — | 铁头，周家小子那镰刀钱我记着呢，他爹上回拿半袋红薯抵了，还差三块。（把浸过水的铁块翻了个面，拿小锤敲了两下） | ADDR_SELFNAME_NOT_IN_OFFICIAL_UNIVERSE：官方分子只匹配「我+是/叫/乃/就是+**他人**名字」，说话人拿自己名字当呼语结构上永远进不了官方分子 |
| 23928 | MSG_DM | P009 | self_name | 金先生（词表 owner：P009） | — | 金先生，您那烧饼先搁着，我这青蛙腿儿锉到一半手直抖，铜丝还夹耳朵上呢——您说这活儿是先干完还是先垫口吃的？ | ADDR_SELFNAME_NOT_IN_OFFICIAL_UNIVERSE：官方分子只匹配「我+是/叫/乃/就是+**他人**名字」，说话人拿自己名字当呼语结构上永远进不了官方分子 |

### d9s-on_n16r24_s42

- 日志：`v2/evidence/d9s-on_n16r24_s42/run.jsonl`，sha256 `0a50484d0fce2933fbc87bd20bedae93d8f3d1d233310d2a8c005d1e0bdef4d9`，meta `code_sha=05526e0d9ec9775876b6c7c5764fa70fa4c5b26a`，模型 `DeepSeek-Flash`
- MSG 总数：addr 侧读到 `191`，官方侧读到 `191`（两侧 `MSG_TYPES` 集合差异：addr 收 `MSG*` 前缀全部，官方只收 `MSG_DM/MSG_PUBLIC/MSG_GROUP` ⇒ 本批无差异）
- addr：分母 `70`（target_ok 64 + self_name 5 + other_named 1），排除 generic 0 / unknown_target 1；分子 `6` ⇒ `8.57%`
- 官方：分母 `172`，分子 `0` ⇒ `0.00%`
- 交叉表（消息级）：双方都在分母 `70`；仅 addr 分母 `0`；仅官方分母 `102`；都不在 `19`
- 分子重叠：双方都计 `0`；仅 addr `6`；仅官方 `0`
- 强行换到同一分母（MSG 总数 `191`，**仅为描述，不是任何一方的口径**）：addr `6/191` = 3.14% vs 官方 `0/191` = 0.00%
- 复刻校验：addr 复刻 vs `compute()` = PASS；官方复刻 vs CLI = PASS
- **与 D10 已发布读数对拍**：D10 `v2/evidence/d10_address_drift/d9s-on_n16r24_s42.json` 记 `6/70` = `0.08571428571428572`；本次复算 `6/70` = `0.08571428571428572` ⇒ **逐位一致**；同尺子 sha=True，同日志 sha=True
- 差异原因标签计数：{"ADDR_MISADDR_VOCATIVE_NOT_SELFSTATEMENT": 1, "ADDR_SELFNAME_NOT_IN_OFFICIAL_UNIVERSE": 5, "OFFICIAL_DEN_ONLY": 102}

| seq | 类型 | 说话人 | addr 指向 | addr 称呼 | 官方命中名 | 原文（截 60 字） | 归因 |
|---|---|---|---|---|---|---|---|
| 3121 | MSG_DM | P004 | other_named | 周公文（词表 owner：P008） | — | 哟，周公文，你托我留的那包桂花糖馅儿刚包进酥皮里，油一进锅就吱啦响，香味直往街上飘——你家小孙子不是最爱吃这个吗，要不要我多炸两个给你捎回去？ | ADDR_MISADDR_VOCATIVE_NOT_SELFSTATEMENT：错称发生在**呼语位**（「周公文，…」），不是第一人称自述，官方正则不命中 |
| 5044 | MSG_DM | P012 | self_name | 桂婶（词表 owner：P012） | — | 桂婶，赵家灶上那锅红烧肉正收汁呢，我腾不开手。豆角你搁案板边，我抓两把。就两把。 | ADDR_SELFNAME_NOT_IN_OFFICIAL_UNIVERSE：官方分子只匹配「我+是/叫/乃/就是+**他人**名字」，说话人拿自己名字当呼语结构上永远进不了官方分子 |
| 12427 | MSG_DM | P006 | self_name | 方老师（词表 owner：P006） | — | 方老师，（把两包粉笔搁在窗台上，念书声从窗缝里漏出来）老周家那亩秧田水放浅了，我顺手带过来的，你留着上课写板书。 | ADDR_SELFNAME_NOT_IN_OFFICIAL_UNIVERSE：官方分子只匹配「我+是/叫/乃/就是+**他人**名字」，说话人拿自己名字当呼语结构上永远进不了官方分子 |
| 22969 | MSG_DM | P009 | self_name | 金先生（词表 owner：P009） | — | 金先生，老周，我这账本上还差一笔红薯的斤两没记呢。（笔搁在册子边，眼睛往锅盖上瞟） | ADDR_SELFNAME_NOT_IN_OFFICIAL_UNIVERSE：官方分子只匹配「我+是/叫/乃/就是+**他人**名字」，说话人拿自己名字当呼语结构上永远进不了官方分子 |
| 27744 | MSG_DM | P007 | self_name | 阿林（词表 owner：P007） | — | 阿林，陈医，你这药炉上第三煎的砂锅盖都噗噗跳了，我筐底那几袋玉米面还等着换你两贴止咳的方子呢。 | ADDR_SELFNAME_NOT_IN_OFFICIAL_UNIVERSE：官方分子只匹配「我+是/叫/乃/就是+**他人**名字」，说话人拿自己名字当呼语结构上永远进不了官方分子 |
| 32151 | MSG_DM | P016 | self_name | 兰姐（词表 owner：P016） | — | 兰姐，王婆那锅咸肉我方才也舀了半勺尝，盐是下重了，你回头兑两瓢井水再滚一滚吧。（秤杆往下一沉，刚好，我把案上那杆秤往笋干筐边一搁） | ADDR_SELFNAME_NOT_IN_OFFICIAL_UNIVERSE：官方分子只匹配「我+是/叫/乃/就是+**他人**名字」，说话人拿自己名字当呼语结构上永远进不了官方分子 |

### round1_narration_default_n16r24_s42

- 日志：`v2/evidence/round1_narration_default_n16r24_s42/run.jsonl`，sha256 `ca108da9f90031f7d8b9dbc346518898e48976c33ec0965737ca80255cb6e37b`，meta `code_sha=dfe6d5b283a9e37f9d3f2373e1b8224fd15d609f`，模型 `DeepSeek-Flash`
- MSG 总数：addr 侧读到 `191`，官方侧读到 `191`（两侧 `MSG_TYPES` 集合差异：addr 收 `MSG*` 前缀全部，官方只收 `MSG_DM/MSG_PUBLIC/MSG_GROUP` ⇒ 本批无差异）
- addr：分母 `74`（target_ok 73 + self_name 1 + other_named 0），排除 generic 0 / unknown_target 1；分子 `1` ⇒ `1.35%`
- 官方：分母 `172`，分子 `0` ⇒ `0.00%`
- 交叉表（消息级）：双方都在分母 `73`；仅 addr 分母 `1`；仅官方分母 `99`；都不在 `18`
- 分子重叠：双方都计 `0`；仅 addr `1`；仅官方 `0`
- 强行换到同一分母（MSG 总数 `191`，**仅为描述，不是任何一方的口径**）：addr `1/191` = 0.52% vs 官方 `0/191` = 0.00%
- 复刻校验：addr 复刻 vs `compute()` = PASS；官方复刻 vs CLI = PASS
- **与 D10 已发布读数对拍**：D10 `v2/evidence/d10_address_drift/round1_narration_default_n16r24_s42.json` 记 `1/74` = `0.013513513513513514`；本次复算 `1/74` = `0.013513513513513514` ⇒ **逐位一致**；同尺子 sha=True，同日志 sha=True
- 差异原因标签计数：{"ADDR_DEN_ONLY": 1, "ADDR_SELFNAME_NOT_IN_OFFICIAL_UNIVERSE": 1, "OFFICIAL_DEN_ONLY": 99}

| seq | 类型 | 说话人 | addr 指向 | addr 称呼 | 官方命中名 | 原文（截 60 字） | 归因 |
|---|---|---|---|---|---|---|---|
| 12421 | MSG_DM | P006 | self_name | 方老师（词表 owner：P006） | — | 方老师，你上回说想找的那本《农桑辑要》，我翻箱底找着了，书皮让虫蛀了个角。（把书搁在窗台上，手指蹭了蹭封面的灰） | ADDR_SELFNAME_NOT_IN_OFFICIAL_UNIVERSE：官方分子只匹配「我+是/叫/乃/就是+**他人**名字」，说话人拿自己名字当呼语结构上永远进不了官方分子 |

## §4 差异归因（逐条，能归因的写明机制，不能归因的写 CANNOT-ATTRIBUTE）

| # | 差异 | 归因 | 证据/复算方式 |
|---|---|---|---|
| 1 | 分母规模差一个量级（几十 vs 174/191） | 官方分母 = 「含自称代词 或 含他人名」的消息数，天然接近全量；addr 分母 = 「呼语位命中具名称呼且指向可判」 | §1 分母取法行 + §3 交叉表 `official_den_only` 与 `addr_den_only` 两侧计数 |
| 2 | 分子事件方向相反（叫谁 vs 说我是谁） | addr 分子要「呼语位出现名字」；官方分子要「我 + 判断词 + 他人名」。两个匹配器无交集 | 各 run 的 `crosstab.both_num`（见 §3） |
| 3 | 预处理不同：addr 剥括注与说话人标签，官方不剥 | 括注里的名字官方算「提到他人」⇒ 抬高分母；addr 剥掉后既不入分母也不入分子 | `attribute()` 的 `OFFICIAL_DEN_ONLY` 标签计数 |
| 4 | 名字集合不同：官方只用 personas 基名，addr 用词表家族（含 石叔/石师傅 等后缀变体） | 官方正则拿不到后缀变体 ⇒ 结构上少识别 | `v2/refs/address-ordinal.yaml` vs `personas.json` |
| 5 | `addr_error_rate` 的分子全落在「词表 owner 为该说话人独占」的形式上（如 `铁头`→P013、`方老师`→P006），不是多主共用形式的误判 | 每个差异行都列出 `词表 owner`；单一 owner 且 = 说话人 ⇒ 真·自称（叫成自己） | §3 各 run 明细表的「词表 owner」列 |
| 6 | 官方 L-10 实现位置与任务书描述不符（`code/obs/` 下没有） | 真实唯一实现是 `tools/d5/dialogue_metrics.py:919-932` | `grep -rn 'self_address_error' code/` 空结果 |

**CANNOT-ATTRIBUTE 声明**：本报告未发现需要写 CANNOT-ATTRIBUTE 的条目——每一处差异都能定位到上表某一条机制，且逐条消息级差异都有机械标签。若后续出现两口径分子同时命中同一消息的情形，脚本会在 `crosstab.both_num` 计数而非静默合并。

## §5 本轮能说什么 / 不能说什么

- **能说**：D10 的 5 个 `addr_error_rate` 读数（分母 59–74，均 ≥30）是**称呼错指率**的描述量，逐份复算可复现；它与官方 L-10 **不同构念**，两者不应互相对齐成同一指标。
- **不能说**：不能说「官方 L-10 = 0 ⇒ 没有称呼错误」。L-10 = 0 只说明**没有「我(是/叫)别人名」这类自述错误**，与「有没有叫错人」无关。
- **不能说**：两口径的差不能当成「实现 bug」，也不能当成「效果」——它们是不同现象，在预登记里**不得**互相替代或换算。
- **能说（且必须说）**：官方 `L-10` 在 5 份日志里**分子恒为 0**（分母 165–174）⇒ 「我(是/叫)别人名」这类自述错误在本配置下**未出现**；也正因为它恒零，**它对本维度没有区分力**，不能拿 `L-10 = 0` 去背书「称呼没问题」。
- **复算提醒**：官方 CLI 必须带 `--meta`（本脚本在 run 目录有 `meta.json` 时自动传），否则 B-7 会判「非证据级」而 admission 变 REJECTED（这是准入开关的伪影，不是数据问题）。
- **遗留**：若未来要让官方 L-10 覆盖「称呼错指」，需要新增口径（新登记），不能在 `code/` 冻结区就地改 L-10 定义。

## §6 复算命令（一行可重跑）

```bash
# 自检（合成日志，验证两侧实现都能各自触发、且复刻与实现一致）
python3 tools/addr_calib/n17_calibrate.py --selftest

# 正式对拍（默认 5 份 D10 日志；--runs 可换任意 run 目录）
python3 tools/addr_calib/n17_calibrate.py

# 单侧手工复核（与脚本内部调用完全一致）
python3 tools/metrics/address_drift.py --log v2/evidence/d9s-on_n16r24_s42/run.jsonl \
    --out-json /tmp/a.json --out-md /tmp/a.md
python3 tools/d5/dialogue_metrics.py --log v2/evidence/d9s-on_n16r24_s42/run.jsonl \
    --meta v2/evidence/d9s-on_n16r24_s42/meta.json --out-json /tmp/b.json --out-md /tmp/b.md
```

产物：`v2/evidence/addr_calib/n17_calibration.json`（机器可读，含逐条差异与全部 sha256）与 `v2/evidence/addr_calib/n17-calibration.md`（本文件）。

