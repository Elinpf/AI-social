#!/usr/bin/env bash
# CYCLE-36 全部引用原文的逐字实拉命令（自动生成，逐条执行）
# 用法：bash c36-grep-checks.sh ；每条输出「行号:JSON」，应各命中 1 行且行号 = seq + 1
set -u
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment || exit 2

echo '--- ON seg1 TH-P013-P004-16 seq=23259 (expect line 23260) ---'
grep -n -F -- '（攥着铁钳敲了敲砧子上那块犁头）哎，秀娘，你灶上那锅糊糊先匀我一碗，回头给你家锄头加个钢口。饿得慌。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg1 TH-P013-P004-16 seq=23867 (expect line 23868) ---'
grep -n -F -- '（掀开蒸笼盖，白汽扑了满脸）铁头哥，糊糊早见底啦，案板上还剩半块红糖发糕，你先垫垫。（拿油纸包了递过去）' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg1 TH-P013-P004-16 seq=25748 (expect line 25749) ---'
grep -n -F -- '（接过油纸包，指头沾了层糖霜）哎，我这炉上还煨着张屠户家那把斩骨刀，火候差一成就卷刃——你这发糕，掰半块给我路上啃行不？' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg1 TH-P013-P004-16 seq=27469 (expect line 27470) ---'
grep -n -F -- '铁头，我这笼屉里还蒸着李寡妇家订的枣泥糕，得盯着火候呢，你先掰半块发糕垫垫吧。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg1 TH-P013-P004-16 seq=31604 (expect line 31605) ---'
grep -n -F -- '（把风箱拉杆一松，炉火暗下去）哎，我这铁砧上还压着王屠户家那把剔骨刀没淬完火呢，先啃你半块发糕垫垫吧。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg1 TH-P013-P004-16 seq=34165 (expect line 34166) ---'
grep -n -F -- '（把发糕掰成两半，一半塞进铁头手里）发糕你先吃着，剔骨刀淬火急不得，王屠户明早才来取。我灶上那锅枣泥酥刚点上芝麻，你闻闻这味儿，甜不甜？' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- OFF seg1 TH-P013-P004-16 seq=23244 (expect line 23245) ---'
grep -n -F -- '（攥着刚出炉的镰刀往人堆里挤）哟，秀娘，这袋糙米让给我，我家灶上还空着。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg1 TH-P013-P004-16 seq=23852 (expect line 23853) ---'
grep -n -F -- '铁头，那袋糙米你先拿去吧，我这儿还温着半屉枣泥糕，等会儿给巷口王奶奶送两块去。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg1 TH-P013-P004-16 seq=25733 (expect line 25734) ---'
grep -n -F -- '（把锤子搁在砧子上，手背蹭了蹭额头的汗）哎，秀娘，我这炉上还煨着给赵家打的锄头，枣泥糕你先给王奶奶留着——糙米我拿了，回头给你捎两斤新打的铁钉，成不？' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg1 TH-P013-P004-16 seq=27448 (expect line 27449) ---'
grep -n -F -- '铁头，我这刚给陈家小孙子捏好一屉兔子包，枣泥糕你先拿两块垫垫肚子吧。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg1 TH-P013-P004-16 seq=31579 (expect line 31580) ---'
grep -n -F -- '哎，秀娘，我这正给赵家打把锄头，炉子还烧着呢，先吃你块枣泥糕垫垫吧。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg1 TH-P013-P004-16 seq=34138 (expect line 34139) ---'
grep -n -F -- '（把枣泥糕往铁头手里一塞，转身掀开案板上的湿布）垫吧垫吧，炉子烧着也得顾肚子——我这刚揉好一屉南瓜面，等发起来就上锅，你打完锄头过来拿两块，给赵家小孙子捎一块。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- ON seg2 TH-P011-P003-30 seq=38835 (expect line 38836) ---'
grep -n -F -- '（捏着半块冷馍从阿禾家灶房门口探进头）阿禾姐，你这锅里炖的萝卜味儿都飘到巷口了，我拿馍来换一口汤吧。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg2 TH-P011-P003-30 seq=39712 (expect line 39713) ---'
grep -n -F -- '（把灶台边的粗瓷碗往小满那边推了推）萝卜是后园拔的，汤你舀，碗搁这儿就行。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg2 TH-P011-P003-30 seq=47914 (expect line 47915) ---'
grep -n -F -- '（捏着筷子戳了戳碗里的萝卜）哎，这萝卜甜得跟偷了糖似的——你娘上回腌的那坛子，是不是也搁了后园的？' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg2 TH-P011-P003-30 seq=52113 (expect line 52114) ---'
grep -n -F -- '（把萝卜干往坛口按了按）后园那畦早拔了，剩这几根还是你婶子昨儿送来的。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg2 TH-P011-P003-30 seq=55500 (expect line 55501) ---'
grep -n -F -- '阿禾，你婶子送的那几根我瞅着还带泥呢，（伸手从坛沿捻起一小撮盐粒）要不咱再撒把盐压压水？' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg2 TH-P011-P003-30 seq=56431 (expect line 56432) ---'
grep -n -F -- '小满，这坛子沿儿上还沾着昨儿的盐粒呢，（拿袖口蹭了蹭坛口）再撒就齁了。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- OFF seg2 TH-P011-P003-30 seq=38810 (expect line 38811) ---'
grep -n -F -- '（把阿禾家灶台上那半块凉红薯拿起来掂了掂）凉红薯也是红薯，先垫一口再帮你家剥豆子吧。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg2 TH-P011-P003-30 seq=39687 (expect line 39688) ---'
grep -n -F -- '（把红薯掰成两半，递回一半）红薯你吃，豆子我剥。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg2 TH-P011-P003-30 seq=47886 (expect line 47887) ---'
grep -n -F -- '（把豆荚往膝盖上一搁）小满这名字听着就饿，你娘蒸的槐花饭今年还做不做？' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg2 TH-P011-P003-30 seq=52084 (expect line 52085) ---'
grep -n -F -- '（把簸箕往膝头挪了挪，挑出个瘪豆荚）槐花饭得等树开，我娘腿脚不行了，今年是隔壁张婶上树捋的。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg2 TH-P011-P003-30 seq=55471 (expect line 55472) ---'
grep -n -F -- '阿禾，张婶上树那回我瞧见了，她裤脚挂破一道口子。（捏着豆荚两头一掰，豆粒滚进搪瓷盆）' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg2 TH-P011-P003-30 seq=56401 (expect line 56402) ---'
grep -n -F -- '小满，张婶那裤脚我给她缝上了。（把搪瓷盆往桌里推了推）豆子挑完就还她。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- ON seg3 TH-P006-P003-6 seq=4946 (expect line 4947) ---'
grep -n -F -- '（把一摞刚裁好的毛边纸在桌上磕齐）哎，阿禾，这沓纸你拿着练字吧，我裁多了搁着也是搁着嘛。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg3 TH-P006-P003-6 seq=5671 (expect line 5672) ---'
grep -n -F -- '（把锄头靠在墙根，裤脚还沾着泥）你那菜园子刚浇过水，一个人忙得过来吧。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg3 TH-P006-P003-6 seq=8317 (expect line 8318) ---'
grep -n -F -- '（放下手里的水瓢，瓢底还滴着水）菜园子浇完了，正想歇会儿呢。你裤脚上那泥，是西坡地里刚翻的吧？' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg3 TH-P006-P003-6 seq=11050 (expect line 11051) ---'
grep -n -F -- '（把锄头往田埂上一靠，泥块从锄面掉下来）哎，方老师，西坡那垄刚翻完，顺手薅了把野葱。给你搁门口？' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg3 TH-P006-P003-6 seq=19192 (expect line 19193) ---'
grep -n -F -- '方老师，我刚从西坡薅了把野葱，给你搁门口吧。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg3 TH-P006-P003-6 seq=20356 (expect line 20357) ---'
grep -n -F -- '（把野葱往门边一放，手在裤腿上蹭了蹭）这葱嫩，你留着下面条。灶上还烧着水。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- OFF seg3 TH-P006-P003-6 seq=4946 (expect line 4947) ---'
grep -n -F -- '（把一摞用麻绳捆好的旧课本往阿禾怀里递了递）哎，这是我家小子去年用过的算数本，边角都磨圆了，你拿去翻翻，里头批注还在呢吧。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg3 TH-P006-P003-6 seq=5671 (expect line 5672) ---'
grep -n -F -- '（把沾泥的锄头往墙根一靠，接过本子翻了翻）你家小子这算数本上，鸡兔同笼那道题还画了圈呢吧。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg3 TH-P006-P003-6 seq=8314 (expect line 8315) ---'
grep -n -F -- '（从阿禾手里接过本子，指尖点了点那道画圈的题）鸡兔同笼啊，这小子昨天还追着我问，说鸡和兔子关一块儿，谁替谁数脚呢。（笑）你这一翻，倒让我想起他今早出门前，非要把本子塞书包最底下。你家的娃，最近也爱拿题来考你不？' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg3 TH-P006-P003-6 seq=11045 (expect line 11046) ---'
grep -n -F -- '（哎，我正蹲在灶前添柴，锅里水还没开）我家那个光顾着追鸡，哪顾得上数脚。（抬头）你吃了吗？' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg3 TH-P006-P003-6 seq=19179 (expect line 19180) ---'
grep -n -F -- '阿禾，我这儿刚蒸好一屉红薯，给你家那个追鸡的娃捎两个吧。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg3 TH-P006-P003-6 seq=20341 (expect line 20342) ---'
grep -n -F -- '（放下锄头，手在裤腿上蹭了蹭）方老师，你家灶上那锅红薯，我闻着就饿。给我娃留一个。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- ON seg4 TH-P015-P011-40 seq=60821 (expect line 60822) ---'
grep -n -F -- '（唉，手里这锅糖色又炒过了，苦味儿直往鼻子里钻）小满啊，你上回说想学的那道红烧肉，我今儿怕是教不了啦——镇上王木匠家闺女明儿出嫁，非拉我去帮厨，我这半吊子手艺也得去凑个数。要不改天你来我这儿，咱俩慢慢试？' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg4 TH-P015-P011-40 seq=61583 (expect line 61584) ---'
grep -n -F -- '小满，你闻闻我这锅糖色，苦得跟王木匠家那闺女上花轿前哭的泪似的——明儿帮厨我掌勺，你猜我头一道菜敢不敢做红烧肉？' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg4 TH-P015-P011-40 seq=63165 (expect line 63166) ---'
grep -n -F -- '小满，我这锅糖色熬得比王木匠家闺女上花轿哭的泪还苦，明儿帮厨头一道菜我要是真端出红烧肉，你敢不敢先替我尝一筷子？' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg4 TH-P015-P011-40 seq=73015 (expect line 73016) ---'
grep -n -F -- '（把搪瓷缸往灶台边一搁，缸底磕出脆响）苦糖色配红烧肉，王木匠家闺女听了都得掀盖头跑呢。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg4 TH-P015-P011-40 seq=81406 (expect line 81407) ---'
grep -n -F -- '（拿筷子尖戳了戳锅里那块颤巍巍的肉皮）掀盖头跑？那正好，跑一个我留一个——王木匠家闺女要是真来了，我这锅肉就改叫“新娘子跳墙”。（撇掉浮沫，火苗舔着锅底）你说这糖色苦，我倒觉得是焦得刚好，跟人似的，太顺了反倒没味。要不你替我尝尝，是苦还是香？' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg4 TH-P015-P011-40 seq=84546 (expect line 84547) ---'
grep -n -F -- '（把灶边那碗凉水往锅沿推了推）哟，王木匠家闺女昨儿还来借过刨子，说给她爹修窗框——你这锅肉要是真跳了墙，她拿啥赔你？' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- OFF seg4 TH-P015-P011-40 seq=60787 (expect line 60788) ---'
grep -n -F -- '（把手里那半截萝卜搁回案板，刀口还沾着泥）哎，小满，你上回托我留的那坛子酱萝卜，我今儿一开盖尝了口，咸得能齁死卖盐的——要不你先拿回去，搁两天再吃？' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg4 TH-P015-P011-40 seq=61549 (expect line 61550) ---'
grep -n -F -- '（把晾在窗台的酱萝卜坛子抱下来，坛底还沾着圈盐霜）五味叔，这坛子我先不拿——您尝着齁，我拿回去也是搁着，不如您再添半瓢凉白开兑兑，回头腌新萝卜正好使。您说呢？' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg4 TH-P015-P011-40 seq=63131 (expect line 63132) ---'
grep -n -F -- '小满，这坛子你先搁灶台边——我正拿它压着新腌的雪里蕻呢，坛口那圈盐霜我拿湿布擦擦就成。（掀开灶上砂锅盖，白汽扑了满脸）你闻闻，这锅萝卜炖得烂不烂？' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg4 TH-P015-P011-40 seq=72976 (expect line 72977) ---'
grep -n -F -- '（拿筷子尖戳了戳砂锅里的萝卜，又缩回手吹了吹）烂是烂了，可你灶台边那坛子压着雪里蕻，我娘昨儿还念叨要借你家坛子腌点糖蒜呢。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg4 TH-P015-P011-40 seq=81358 (expect line 81359) ---'
grep -n -F -- '（把砂锅盖子斜过来，拿抹布垫着掀开一条缝，白汽扑到脸上）坛子你娘要就拿去，里头那点雪里蕻我回头腾到搪瓷盆里——正好，我这儿萝卜炖得发死，你帮我尝尝，是缺糖还是缺醋？' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg4 TH-P015-P011-40 seq=84494 (expect line 84495) ---'
grep -n -F -- '（拿筷子尖戳了戳萝卜块，又缩回手甩了甩）哎，五味叔，你这萝卜炖得筷子一碰就散，我娘那坛子雪里蕻换你这锅，她准得说我亏了——你尝过没，是不是该搁半勺糖提提？' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- ON seg5 TH-P004-P013-4 seq=3121 (expect line 3122) ---'
grep -n -F -- '（把刚出炉的枣泥酥往竹篮里码）哟，周公文，你来得巧，这锅是给桂婶家小孙子留的，他昨儿还念叨想吃带枣泥的——你要不先尝半块，回头帮我跟方老师捎个话，问他家阿禾还来不来拿订好的那屉？' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg5 TH-P004-P013-4 seq=5065 (expect line 5066) ---'
grep -n -F -- '（把铁钳往水桶里一搁，嗤地冒白气）这阵子啥都抢，铁钉都有人囤。桂婶家小孙子那半块我尝了，枣泥甜。阿禾那屉，我捎话。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg5 TH-P004-P013-4 seq=5732 (expect line 5733) ---'
grep -n -F -- '（把烤盘里最后一只枣泥酥夹进油纸）你这几天守着炉子，连轴转得够呛吧。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg5 TH-P004-P013-4 seq=7844 (expect line 7845) ---'
grep -n -F -- '（拿锉刀蹭了蹭砧子边，火星子溅到鞋面）累是累，炉子不能歇。桂婶家那半块枣泥酥，我给她捎过去。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg5 TH-P004-P013-4 seq=8200 (expect line 8201) ---'
grep -n -F -- '（把油纸角折进纸袋，枣泥酥的甜香还沾在指头上）炉子不能歇，人也得喘口气。桂婶那半块我另包了张红纸，你顺道带过去。趁热吃。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- ON seg5 TH-P004-P013-4 seq=15598 (expect line 15599) ---'
grep -n -F -- '（把铁钳往水桶里一浸，白汽冒起来）秀娘，那批铁钉张家也要，我先给他打二十根。桂婶的红纸包你搁我车斗里。' v2/evidence/n15-on_n16r84_s42/run.jsonl
echo '--- OFF seg5 TH-P004-P013-4 seq=3121 (expect line 3122) ---'
grep -n -F -- '（把刚出炉的枣泥酥往竹篮里码）哎，周公文，你来得巧，这锅枣泥酥还烫手呢，桂婶家的小子昨儿就念叨着要，我给他留了两块——你要不要也捎一包回去尝尝？' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg5 TH-P004-P013-4 seq=5065 (expect line 5066) ---'
grep -n -F -- '（把铁钳往水桶里一浸，白汽窜起）紧俏货？我铺里那批锄头还压着，桂婶家小子倒先抢上酥了。留两块。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg5 TH-P004-P013-4 seq=5732 (expect line 5733) ---'
grep -n -F -- '（把烤盘里的酥皮边角料拨到一边，油纸窸窣响）铁头哥，你那锄头还搁着没动，倒惦记上桂婶家小子手里那两块酥啦。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg5 TH-P004-P013-4 seq=7844 (expect line 7845) ---'
grep -n -F -- '（拿火钳夹起一块烧红的铁块，火星溅到围裙上）这年头啥都抢。昨儿李屠户家为半扇猪排跟人红脸，我这儿倒清静——就剩你案板上那几块酥皮边角，还粘着芝麻。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg5 TH-P004-P013-4 seq=8197 (expect line 8198) ---'
grep -n -F -- '（用刮刀铲起粘在烤盘底的芝麻粒）芝麻都粘底了，还惦记酥皮呢。桂婶家小子那两块，是昨儿我塞给他的——他娘病着，嘴里没味。铁头哥，你要馋，明儿我多烤一盘。' v2/evidence/n15-off_n16r84_s42/run.jsonl
echo '--- OFF seg5 TH-P004-P013-4 seq=15593 (expect line 15594) ---'
grep -n -F -- '（把铁锤往砧子上一搁，锤柄还烫手）秀娘，那盘你留着给桂婶家小子，我这儿有块铁皮，回头给他娘打个暖手的炉子。' v2/evidence/n15-off_n16r84_s42/run.jsonl
