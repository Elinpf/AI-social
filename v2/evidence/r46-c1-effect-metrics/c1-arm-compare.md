# C1 处境锚 A0/A1 对比（按预登记卡 C1-scene-prereg-20261101 口径）

- 尺子：`tools/metrics/place_content_consistency.py`
- lexicon_sha256: `7e514eba9f9de0e674875f40b9503e24490f5baf9b861d51bc8cfe68b074f22e`
- 通过线：Δrate ≥ +15.0pp **且** rate(A1) ≥ 0.55（先验，不得事后下调）
- 判定：**不成立**。机制层：**机制已接通（A1 scene 键覆盖 > 0）**。

| 臂 | 对话事件 | 缺字段 | no_cue 条数 | no_cue 占比 | 分母 | 一致条数 | 一致率 | scene 键覆盖率 | lexicon_sha256 | 达线 | 判定 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | 191 | 0 | 17 | 0.0890 (17/191) | 174 | 58 | 0.3333 (58/174) | 0.0000 (0/191) | `7e514eba9f9de0e674875f40b9503e24490f5baf9b861d51bc8cfe68b074f22e` | 见总判定 | 不成立 |
| A1 | 191 | 0 | 26 | 0.1361 (26/191) | 165 | 56 | 0.3394 (56/165) | 1.0000 (191/191) | `7e514eba9f9de0e674875f40b9503e24490f5baf9b861d51bc8cfe68b074f22e` | 见总判定 | 不成立 |

**Δrate(A1−A0) = +0.61pp**

## 口径说明（照抄预登记卡）
- 分母 = MSG_PUBLIC/MSG_DM 中有 `place`、`body` 非空、且命中冻结线索词表 ≥1 词的条目；无线索条目只报条数不进分母。
- 主指标为**纯规则版，未用 LLM judge，结论强度较弱**。
- **这是「条件一致率」，不是全体对话的一致率**：分母只覆盖「命中冻结活动线索词表 ≥1 词」的条目，不在分母里的对话（`no_cue`）与缺字段条目都不参与比率。因此不能读成"只有 X% 的对话与场所相容"。
- 机制层 `scene` 键覆盖率的统计口径：只统计对话类事件（`type ∈ {MSG_PUBLIC, MSG_DM}`）的 `payload.ctx` 中是否存在 `scene` 键，分母 = 该臂对话类事件条数；同时给出绝对条数，不只给比率。
- 机制层成立 ≠ 效果层成立，两者分开写。

## 两臂 env_manifest 差异（可比性闸；逐行双向比对，非只看行数）
差异行数：1（- 仅 A0 有 / + 仅 A1 有）
```
+ LIFE_PROMPT_SCENE=1
```
差异状态：`ok_only_scene`

## A0 分层读数（place / judged / agree / rate；judged<30 不报率）

| place | judged | agree | rate |
|---|---|---|---|
| bank | 13 | 7 | NA(<30) |
| cafe | 27 | 1 | NA(<30) |
| community_center | 8 | 2 | NA(<30) |
| farm | 9 | 3 | NA(<30) |
| kitchen | 3 | 3 | NA(<30) |
| library | 6 | 2 | NA(<30) |
| market | 21 | 6 | NA(<30) |
| office | 1 | 0 | NA(<30) |
| park | 21 | 5 | NA(<30) |
| plaza | 14 | 1 | NA(<30) |
| residence | 26 | 18 | NA(<30) |
| school | 13 | 2 | NA(<30) |
| town_hall | 4 | 2 | NA(<30) |
| workshop | 8 | 6 | NA(<30) |

**A0 不一致样本（≤5，seq / 人物 / place / 活动域 / 线索 / 片段）**

- seq=53 P002 place=library domains=wood_metal_craft cues=刨子 ｜ （拿刨子推过木料，木花卷着落下来）这料子干透了，给老周家闺女打嫁妆箱，榫卯得再紧半丝。（眯眼对了对线）慢工出细活。
- seq=73 P004 place=library domains=cooking_bakery cues=灶 ｜ （把沾着面粉的手在围裙上蹭了蹭）听说你最近在给东头老周家修灶台，那活儿费劲不？（往案板上的面团又按了两下）我这炉酥皮总差点意思。想讨教讨教。
- seq=84 P005 place=workshop domains=clinic cues=药 ｜ 哎，我把李婶家那包艾草翻出来再晒晒，手上这味药捻得也差不多了吧。
- seq=124 P009 place=park domains=trade_accounting cues=算盘 ｜ （把算盘珠子拨回原位）秀娘，你家那口子今早来存钱，脸色不大好——家里还顺当吧？（抬眼看了看她）账要平。
- seq=167 P013 place=school domains=wood_metal_craft,farm cues=回火,锄头 ｜ （把烧红的锄头往水桶里一按，白汽直冒）这锄头是东头老周家的，刃口卷了，我正回火。你站远点，别烫着。

## A1 分层读数（place / judged / agree / rate；judged<30 不报率）

| place | judged | agree | rate |
|---|---|---|---|
| bank | 12 | 10 | NA(<30) |
| cafe | 26 | 2 | NA(<30) |
| community_center | 6 | 1 | NA(<30) |
| farm | 11 | 5 | NA(<30) |
| kitchen | 3 | 2 | NA(<30) |
| library | 6 | 2 | NA(<30) |
| market | 20 | 5 | NA(<30) |
| office | 2 | 0 | NA(<30) |
| park | 17 | 1 | NA(<30) |
| plaza | 15 | 2 | NA(<30) |
| residence | 27 | 16 | NA(<30) |
| school | 10 | 2 | NA(<30) |
| town_hall | 3 | 2 | NA(<30) |
| workshop | 7 | 6 | NA(<30) |

**A1 不一致样本（≤5，seq / 人物 / place / 活动域 / 线索 / 片段）**

- seq=53 P002 place=library domains=wood_metal_craft cues=刨子 ｜ 天刚亮，手就闲不住。（把刨子往木料上一推，薄木花卷着落下来）给老周家闺女打的樟木箱，榫头还得再收半分。慢慢来。
- seq=73 P004 place=library domains=cooking_bakery cues=面粉 ｜ （把沾着面粉的手在围裙上蹭了蹭）这两天忙不忙？我正揉着一盆老面，想跟你讨个准头——发到啥程度算正好？你给句实话。
- seq=84 P005 place=workshop domains=clinic cues=药 ｜ （把药碾子里的黄芪又过了一遍筛）唉，这味药磨得还是粗了些，回头给李家那娃子敷上怕是不匀呢。
- seq=124 P009 place=park domains=trade_accounting cues=算盘 ｜ （把算盘珠子拨回原位）今早这账本翻了三遍，你那边铺子的流水对上了没？（搁下笔）账要平。
- seq=178 P014 place=park domains=wood_metal_craft,performance cues=锉刀,鼓 ｜ （拿锉刀蹭了蹭刚捡的铜片边角）小满？这名字听着就顺耳——我正给王婶家小孙子磨个铜铃铛呢，废料堆里翻出来的，响起来跟猫脖子上的似的。你平时爱鼓

## 历史参考值（**不进对比表数据行、不参与 +15pp 计算**）
（未指定 `--ref`）

## 复算命令
```bash
python3 tools/metrics/place_content_consistency.py --run v2/evidence/c1-scene-a0-20261101_n16r24_s42/run.jsonl
python3 tools/metrics/place_content_consistency.py --run v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl
```

两臂 run.jsonl sha256：
- A0: `1bfeb51d0bb336abca748dad0b1a40375f702df204f9c42cfd0591f24f5dbcb4`
- A1: `c828b4075f027917ce883670564b2a827b4f1feecd322315619f9ecbe9324633`
