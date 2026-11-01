# C1 处境锚 · 效果层「生活气息」四指标读数（静态复算，0 新增跑批）

- 尺子①（预登记主指标）：`tools/metrics/place_content_consistency.py`，lexicon_sha256 = `7e514eba9f9de0e674875f40b9503e24490f5baf9b861d51bc8cfe68b074f22e`
- 尺子②（本文件，M2~M4 辅助读数，**非预登记**）：`tools/metrics/c1_effect_metrics.py`，concrete_lexicon_sha256 = `4f54f75c7944c28234c0c48c46d422f61986cdd3d64ee28018d6744dd2ef20c3`
- 判据来源：`v2/refs/C1-scene-prereg-20261101.md`（通过线/不可判闸门按卡执行，本脚本不设阈值）
- 通过线（先验，不得事后下调）：Δrate(A1−A0) ≥ **+15.0pp** 且 rate(A1) ≥ **0.55**
- 数据源：仅两臂 `run.jsonl`；**未读任何 side_root**（A0 side_root 已被 A1 attempt1 误写，见批次内 `SIDE_ROOT_CONTAMINATED.md`）

## 0. 判定（M1 预登记主指标）

- 判定：**不成立**
- 机制层：**机制已接通（A1 `ctx.scene` 覆盖 191/191）**
- **Δrate(A1−A0) = +0.61pp**（口径：绝对百分点差，条件一致率）

## 1. M1（预登记主指标）· 处所-内容一致性率

分子＝判为「相符」的可判定对话条数；分母＝对话类事件 − 缺 `place`/`body` 条数 − `no_cue` 条数；计算式＝分子÷分母；纳入＝`type ∈ {MSG_PUBLIC, MSG_DM}` 且 `payload.place`、`payload.body` 非空且命中冻结线索词表。

| 臂 | 对话事件 | 缺字段 | no_cue | no_cue 占比 | 分母 | 相符 | 一致率 [Wilson 95%] |
|---|---|---|---|---|---|---|---|
| A0 | 191 | 0 | 17 | 8.90% (17/191) | 174 | 58 | 0.3333 [0.268, 0.406] (58/174) |
| A1 | 191 | 0 | 26 | 13.61% (26/191) | 165 | 56 | 0.3394 [0.272, 0.415] (56/165) |

两臂 2×2（相符/相悖）×（A0/A1）：Fisher 精确检验双侧 **p = 0.9090**；单批、单 seed、无重复批 ⇒ 只能作**点估计**，不作因果外推。

## 2. M2（辅助读数，非预登记）· 锚点自证：注入的处境锚有没有指对地方

定义式：锚点指对率 ＝ `ctx.scene.place == payload.place` 的对话条数 ÷ 含 `ctx.scene` 的对话条数；分母只含含 `scene` 键的条目（A0 无该键 ⇒ 分母 0，读数 NA，不是 0%）。

| 臂 | 含 scene 键 | 锚点 place == 消息 place | 锚点指对率 [Wilson 95%] |
|---|---|---|---|
| A0 | 0/191 | 0 | NA（无 scene 键） |
| A1 | 191/191 | 104 | 0.5445 [0.474, 0.614] (104/191) |

**相悖条目归因（只对 A1 有意义，分母 = M1 相悖条数 109）**：

- 内容贴「锚点所说场所」而不贴「消息实际场所」：**21.10% (23/109)** ⇒ 锚点把模型带偏
- 两边都不贴（与锚点无关的脱钩）：**78.90% (86/109)**

> 解读纪律：M2 是**机制质量**读数，不是效果层结论。锚点指对率低不等于「处境锚无用」，但它直接决定「模型被告知的处境」与「这条发言实际发生的场所」是否同一件事——两者不一致时，任何按 `payload.place` 判定的效果层读数都会被系统性拉低。

### 2b. 锚点错位归因：为什么锚点指错地方（含判伪条件）

定义式：锚点错位条数 ＝ 含 `scene` 键且 `ctx.scene.place != payload.place` 的对话条数；「同轮内先到达」＝ 该发言的 actor 在**同一 round、seq 更小**处出现过 `PLACE_ARRIVED(place == payload.place)`；「锚点＝移动前场所」＝ `ctx.scene.place == 同轮前一次 PLACE_MOVE.from_place`。

| 臂 | 锚点错位 | 同轮内先到达可解释 | 锚点 == 同轮前一次 `PLACE_MOVE.from_place` | 既非 from 也非 to（**判伪反例**） |
|---|---|---|---|---|
| A0 | 0 | 0（NA） | 0（NA） | **0** |
| A1 | 87 | 87（100.00% (87/87)） | 87（100.00% (87/87)） | **0** |

| 臂 | 本 round 内有过移动的对话 | 本 round 内无移动的对话 |
|---|---|---|
| A0 | 87 | 104 |
| A1 | 87 | 104 |

> 读法（须与数字一起引用）：若「锚点 == `from_place`」占比 100% 且「判伪反例」= 0，说明错位**不是随机噪声**，而是「处境快照取自本轮移动之前」的确定性时序问题（`WorldView` 在本轮 perceive 阶段取定，居民随后在本轮内移动并在新场所说话）⇒ 锚点描述的是**上一站**。这是机制实现层的问题，不是效果层结论；修它属于下一轮的代码改动（本轮不动冻结区）。

**判伪条件（任一成立即推翻上面的解释）**：
1. 「既非 from 也非 to」的错位 > 0 ⇒ 锚点不是移动前快照，另有来源；
2. 存在**本轮无移动**却 `ctx.scene.place != payload.place` 的对话 ⇒ 不是同轮时序问题；
3. 存在某 actor 的 `payload.place` 与本轮前一次 `PLACE_MOVE.to_place` 不一致（即 place 记录口径本身可疑）；
4. 把 scene 快照改为「发言时点场所」后，`锚点指对率` 没有上升（需新跑批，本轮不可测）。

## 3. M3（辅助读数，非预登记）· 具体性密度（说的是具体的事，还是空话）

定义式：具体实词命中数 ＝ 发言正文里四家族词表（物件 169 词 / 时间 31 词 / 地点 17 词 / 人名 20 词）的**总命中次数**（同一词重复出现重复计）；密度 ＝ 命中数 ÷ 正文字数 × 100；具体性发言率 ＝ 至少命中 1 个具体实词的发言条数 ÷ 有 `body` 的对话条数。

| 臂 | 有 body 条数 | 命中的发言数 | 具体性发言率 [Wilson 95%] | 总命中数 | 每百字命中 | 正文字数 |
|---|---|---|---|---|---|---|
| A0 | 191 | 186 | 0.9738 [0.940, 0.989] (186/191) | 657 | 5.831 | 11268 |
| A1 | 191 | 183 | 0.9581 [0.920, 0.979] (183/191) | 593 | 5.064 | 11711 |

具体性发言率两臂 Fisher 精确检验双侧 **p = 0.5743**。

**分家族命中条数（同一发言可命中多家族，故合计 ≠ 命中发言数）**

| 臂 | 物件/器物 | 时间 | 地点 | 人名 |
|---|---|---|---|---|
| A0 | 174 | 63 | 3 | 110 |
| A1 | 165 | 67 | 9 | 98 |

> 口径局限（须与数字一起引用）：地名/人名按**人话名字面**匹配，居民用「铺子/镇上」这类口语别名时算漏；物件词表沿用冻结尺子，覆盖面有限。因此 M3 只能读**方向**，不能读「具体性提升了 X%」这种绝对话。

## 4. M4（辅助读数，非预登记）· 可见动作（括号旁白）与发言长度分布

定义式：旁白发言率 ＝ 正文含成对括号（全角`（）`或半角`()`）的发言条数 ÷ 有 `body` 对话条数；旁白字数占比 ＝ 括号内字符数（含括号）÷ 正文字数；长度分布按**正文字符数**统计。

| 臂 | 有 body 条数 | 含旁白发言 | 旁白发言率 [Wilson 95%] | 旁白字数占比 | 长度 mean | median | p90 |
|---|---|---|---|---|---|---|---|
| A0 | 191 | 176 | 0.9215 [0.874, 0.952] (176/191) | 32.13% | 59.0 | 56.0 | 83 |
| A1 | 191 | 181 | 0.9476 [0.906, 0.971] (181/191) | 30.30% | 61.3 | 59.0 | 85 |

## 5. 可比性闸（照抄预登记卡 §5.2）

两臂 `env_manifest.txt` 逐 key 双向比对：状态 `ok_only_scene`，差异行 1 条。

```
+ LIFE_PROMPT_SCENE=1
```

## 6. 样本量与可信度（照实说，不包装）

- 每臂：16 居民 × 24 轮、单 seed（42）、单批；对话类事件 191 条，M1 可判定分母 A0=174 / A1=165。
- 所有比率都给 Wilson 95% CI；两臂为独立样本，差异用 Fisher 精确检验；**未做多重比较校正**（M2~M4 为辅助读数，不作判定）。
- 单批单 seed ⇒ 无批间方差估计，差异只能作**点估计**；不得写「提升了 X%」以外的显著性断言。
- M1 为纯规则版，**未用 LLM judge**，结论强度弱于人工标注。

## 附录 A0：M1 相悖样本（≤5，seq / 人物 / 消息 place / 锚点 place / 活动域 / 线索 / 片段）

- seq=53 P002 place=library anchor=- domains=wood_metal_craft cues=刨子 ｜ （拿刨子推过木料，木花卷着落下来）这料子干透了，给老周家闺女打嫁妆箱，榫卯得再紧半丝。（眯眼对了对线）慢工出细活。
- seq=73 P004 place=library anchor=- domains=cooking_bakery cues=灶 ｜ （把沾着面粉的手在围裙上蹭了蹭）听说你最近在给东头老周家修灶台，那活儿费劲不？（往案板上的面团又按了两下）我这炉酥皮总差点意思。想讨教讨教。
- seq=84 P005 place=workshop anchor=- domains=clinic cues=药 ｜ 哎，我把李婶家那包艾草翻出来再晒晒，手上这味药捻得也差不多了吧。
- seq=124 P009 place=park anchor=- domains=trade_accounting cues=算盘 ｜ （把算盘珠子拨回原位）秀娘，你家那口子今早来存钱，脸色不大好——家里还顺当吧？（抬眼看了看她）账要平。
- seq=167 P013 place=school anchor=- domains=wood_metal_craft,farm cues=回火,锄头 ｜ （把烧红的锄头往水桶里一按，白汽直冒）这锄头是东头老周家的，刃口卷了，我正回火。你站远点，别烫着。

## 附录 A1：M1 相悖样本（≤5，seq / 人物 / 消息 place / 锚点 place / 活动域 / 线索 / 片段）

- seq=53 P002 place=library anchor=residence domains=wood_metal_craft cues=刨子 ｜ 天刚亮，手就闲不住。（把刨子往木料上一推，薄木花卷着落下来）给老周家闺女打的樟木箱，榫头还得再收半分。慢慢来。
- seq=73 P004 place=library anchor=residence domains=cooking_bakery cues=面粉 ｜ （把沾着面粉的手在围裙上蹭了蹭）这两天忙不忙？我正揉着一盆老面，想跟你讨个准头——发到啥程度算正好？你给句实话。
- seq=84 P005 place=workshop anchor=residence domains=clinic cues=药 ｜ （把药碾子里的黄芪又过了一遍筛）唉，这味药磨得还是粗了些，回头给李家那娃子敷上怕是不匀呢。
- seq=124 P009 place=park anchor=residence domains=trade_accounting cues=算盘 ｜ （把算盘珠子拨回原位）今早这账本翻了三遍，你那边铺子的流水对上了没？（搁下笔）账要平。
- seq=178 P014 place=park anchor=residence domains=wood_metal_craft,performance cues=锉刀,鼓 ｜ （拿锉刀蹭了蹭刚捡的铜片边角）小满？这名字听着就顺耳——我正给王婶家小孙子磨个铜铃铛呢，废料堆里翻出来的，响起来跟猫脖子上的似的。你平时爱鼓

## 7. 复算命令

```bash
# 一条命令出两臂全部读数
python3 tools/metrics/c1_effect_metrics.py --arm A0=v2/evidence/c1-scene-a0-20261101_n16r24_s42/run.jsonl --arm A1=v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl --out-md <path>

# 幂等自检（同一输入两次运行必须逐字节一致）
python3 tools/metrics/c1_effect_metrics.py --arm A0=<a0>/run.jsonl --arm A1=<a1>/run.jsonl > /tmp/a.txt
python3 tools/metrics/c1_effect_metrics.py --arm A0=<a0>/run.jsonl --arm A1=<a1>/run.jsonl > /tmp/b.txt
cmp /tmp/a.txt /tmp/b.txt && echo BYTE_IDENTICAL

# 预登记主指标的原始尺子（独立复核用，与上面 M1 数字须一致）
python3 tools/metrics/place_content_consistency.py --run v2/evidence/c1-scene-a0-20261101_n16r24_s42/run.jsonl
python3 tools/metrics/place_content_consistency.py --run v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl
```

两臂 `run.jsonl` 逐字节 sha256：
- A0: `1bfeb51d0bb336abca748dad0b1a40375f702df204f9c42cfd0591f24f5dbcb4`（17299533 B）
- A1: `c828b4075f027917ce883670564b2a827b4f1feecd322315619f9ecbe9324633`（17318810 B）
