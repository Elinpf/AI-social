# D3 · 各不自然模式的代表性原文（由 d3_corpus_annotate.py 确定性生成）

> 抽样规则：按 `run, seq` 升序取前 k 条命中样本，**不随机、不挑选**。

## U1_template_opening
- `t300` seq=164 round=0 P012→P006 [dm/mentorship]：哎哟，P006啊，你最近忙啥呢？有啥不懂的尽管来问婶子，别客气！
- `t300` seq=3167 round=3 P007→P003 [dm/scarce_buy]：哎，几位老哥老姐，我阿林走南闯北这么多年，鼻子最灵——听说镇东头那批货快见底了，谁手里还有门路，咱搭个伙一起想想办法呗？
- `t300` seq=3262 round=3 P012→P001 [dm/counter_propose]：哎哟，P001啊，你这话说的就见外了，咱镇上谁跟谁呀，你要真过意不去，回头请婶子喝碗你家的绿豆汤就成！

## U2_narration_proxy
- `t300` seq=61 round=0 P002→- [public/skill_practice]：（刨子推过木料，木屑卷起）慢点来，急不得。
- `t300` seq=92 round=0 P005→- [public/skill_practice]：（整理着药柜里的药材，自言自语）行医三十年，治好的病人不少，可有些病……终究是治不了的。
- `t300` seq=132 round=0 P009→P001 [dm/combat_training]：（握紧训练木剑）账要平——攻守也得平，别光顾着砍。

## U3_third_person_self
- `t300` seq=30917 round=12 P016→- [public/skill_practice]：（兰姐一边麻利地把新到的干货分门别类码上摊，一边自言自语）这批香菇成色比上回强，价压得住，回头搭着木耳走，一天多挣个三五十不成问题。
- `t300` seq=34116 round=15 P016→P011 [dm/polite_reject]：（兰姐一边麻利地收着摊上的零钱，一边笑着摇头）哎哟，P011，你这价我可真接不住，咱做买卖讲究个实在，你要诚心要，咱再商量个双方都不亏的数，成不？
- `t300` seq=57331 round=27 P016→P019 [dm/polite_reject]：（兰姐一边麻利地收着摊上的零钱，一边笑着摇头）哎哟，P019，你这价我可真接不住，咱都是老街坊，我也不跟你绕弯子——这货进价摆在那儿，我要是应了你，明儿就得喝西北风去。

## U4_agent_id_leak
- `t300` seq=143 round=0 P010→P009 [dm/combat_training]：（喘着气，把木剑往地上一戳）P009，你说——我们练这个，到底是为了打赢谁啊？
- `t300` seq=153 round=0 P011→P009 [dm/combat_training]：（摆出架势，笑嘻嘻地）P009，来吧！让我看看你有多厉害——我可不会手下留情的哦！
- `t300` seq=164 round=0 P012→P006 [dm/mentorship]：哎哟，P006啊，你最近忙啥呢？有啥不懂的尽管来问婶子，别客气！

## U5_no_second_person
- `t300` seq=132 round=0 P009→P001 [dm/combat_training]：（握紧训练木剑）账要平——攻守也得平，别光顾着砍。
- `t300` seq=3091 round=3 P001→P012 [dm/polite_reject]：（摆摆手）不了，地里的活还等着我，改天再说吧。
- `t300` seq=3112 round=3 P002→P016 [dm/scarce_buy]：（低头刨木，头也不抬）料不够，谁家还有干透的老榆木，我拿板凳换。

## U6_clerk_tone
- `t300` seq=121 round=0 P008→- [public/skill_practice]：把这份档案按编号归档，顺序不能乱。
- `t300` seq=3188 round=3 P008→- [public/savings]：定期储蓄是保障未来生活最稳妥的方式。
- `t300` seq=3334 round=3 P016→- [public/savings]：这阵子生意还行，攒下的钱我打算分两笔——一笔存定期吃利息，一笔留着进货周转，心里踏实。

## K1_cont_backref
- `t300` seq=197 round=0 P015→- [public/skill_practice]：（独自在灶台前，盯着锅里翻滚的汤，自言自语）这回少放半勺盐，多搁一撮糖——上回老李说太咸，可小张又嫌淡，唉，众口难调，但总得有人先尝第一口吧。
- `t300` seq=239 round=0 P019→- [public/skill_practice]：（独自对着镜子练习）嘿，这新学的滑板动作，要是摔了就当给地板拜个早年呗！
- `t300` seq=3249 round=3 P011→- [public/savings]：（数着存钱罐里的硬币）还差一点就能买那张去省城的车票了……

## K1_cont_lexical
- `t300` seq=239 round=0 P019→- [public/skill_practice]：（独自对着镜子练习）嘿，这新学的滑板动作，要是摔了就当给地板拜个早年呗！
- `t300` seq=3334 round=3 P016→- [public/savings]：这阵子生意还行，攒下的钱我打算分两笔——一笔存定期吃利息，一笔留着进货周转，心里踏实。
- `t300` seq=7042 round=6 P011→P020 [dm/gift]：P020，这个送你——是我自己做的书签，上面画的是镇外那条河，你收下的话，就当替我保管一小片远方啦。

## U8_dup_exact
- `t300` seq=61 round=0 P002→- [public/skill_practice]：（刨子推过木料，木屑卷起）慢点来，急不得。
- `t300` seq=92 round=0 P005→- [public/skill_practice]：（整理着药柜里的药材，自言自语）行医三十年，治好的病人不少，可有些病……终究是治不了的。
- `t300` seq=121 round=0 P008→- [public/skill_practice]：把这份档案按编号归档，顺序不能乱。

## U8b_ngram_shared
- `t300` seq=61 round=0 P002→- [public/skill_practice]：（刨子推过木料，木屑卷起）慢点来，急不得。
- `t300` seq=81 round=0 P004→P013 [dm/mentorship]：秀娘笑眯眯地递过一块刚出炉的桂花糕：“来，尝尝这个，我新调的方子——你要是喜欢，回头我教你做，咱们街坊里就数你手巧，学起来肯定快。”
- `t300` seq=92 round=0 P005→- [public/skill_practice]：（整理着药柜里的药材，自言自语）行医三十年，治好的病人不少，可有些病……终究是治不了的。

## U9_out_of_world
- `t300` seq=239 round=0 P019→- [public/skill_practice]：（独自对着镜子练习）嘿，这新学的滑板动作，要是摔了就当给地板拜个早年呗！
- `t300` seq=3188 round=3 P008→- [public/savings]：定期储蓄是保障未来生活最稳妥的方式。
- `t300` seq=3393 round=3 P019→P018 [dm/scarce_buy]：哎你们快看这个！限量款诶，我排了半小时队才抢到，谁要跟我换着玩两天？

## U10_public_soliloquy
- `t300` seq=61 round=0 P002→- [public/skill_practice]：（刨子推过木料，木屑卷起）慢点来，急不得。
- `t300` seq=92 round=0 P005→- [public/skill_practice]：（整理着药柜里的药材，自言自语）行医三十年，治好的病人不少，可有些病……终究是治不了的。
- `t300` seq=121 round=0 P008→- [public/skill_practice]：把这份档案按编号归档，顺序不能乱。
