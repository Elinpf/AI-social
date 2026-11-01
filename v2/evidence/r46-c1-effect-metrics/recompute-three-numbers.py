import collections, json
P = "v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl"
CUES = ("刨子|刨花|木花|榫头|榫|木屑|墨斗|锯|锉刀|砂纸|木料|木板|樟木|榆木|削好|削成|凿|木梳|陀螺|犁把|铁砧|砧子|铁钳|淬火|回火|烧红|铁锈|铁匠|"
        "锄头|镰刀|菜地|田埂|地里|那亩|培土|薅|垄|玉米|花生|红薯|晒谷|收着|下地|庄稼|"
        "灶|锅|面粉|揉面|揉的|烤|桃酥|枣糕|糖糕|豆浆|豆腐|撇沫|案板|蒸|煮|下锅|围裙|油纸包|锅盖|火候|擀|"
        "课本|粉笔|学生|上课|三年级|作业|毛笔|念书|教教|教书|板书|讲台|"
        "户籍|誊本|誊|表格|证明|名册|手印|印泥|砚台|文契|契纸|迁出|徭役|折角|"
        "药|脉|诊|退烧|陈皮|方子|药碾|阿司匹林|膏药|包扎|病人|山药|黄芪|须根|入药|"
        "算盘|账|账本|账上|流水|铜板|零钱|存折|折子|存单|支钱|赊|利钱|摊上|卖|买|盐包|粗盐|秤|货款|进项|柜上|柜台|"
        "吉他|鼓|鼓槌|鼓点|琴弦|拉琴|二胡|弦|礼堂|拍子|跳舞|新编的舞|"
        "压腿|沙袋|练功|练完功|扎马步|打拳|热身|"
        "针脚|缝|布老虎|补好|补的裤子|补裤子|棉花|剪刀|裁纸刀|针线|"
        "暖炕|歇脚|打盹|躺着|睡觉|晒太阳|下棋|喝茶|桂花糕|糖饼|炊饼").split("|")
BORN = {}
MOVE = collections.defaultdict(list)
MSGS = []
for ln in open(P, encoding="utf-8"):
    ln = ln.strip()
    if not ln: continue
    e = json.loads(ln); t = e.get("type")
    if t == "AGENT_BORN":
        BORN[e["payload"]["agent_id"]] = e["payload"]["home_place"]
    elif t == "PLACE_MOVE":
        pl = e["payload"]; MOVE[e["actor"]].append((e["round"], e["seq"], pl["from_place"], pl["to_place"]))
    elif t in ("MSG_PUBLIC", "MSG_DM"):
        MSGS.append(e)

mm = jmm = jm = ncm = nce = nomove = naive = 0
for e in MSGS:
    pl = e["payload"]; sc = (pl.get("ctx") or {}).get("scene")
    if not isinstance(sc, dict): continue
    place = (pl.get("place") or "").strip(); body = (pl.get("body") or "").strip()
    anchor = str(sc.get("place") or "")
    mis = anchor != place
    mm += mis
    same_round = [m for m in MOVE.get(e["actor"], ())
                  if m[0] == e["round"] and m[1] is not None and m[1] < e["seq"]]
    if not same_round: nomove += 1
    # 朴素变体：不限轮次取最近一次前置 move 的 from_place（无前置则用 AGENT_BORN.home_place）
    prev = [m for m in MOVE.get(e["actor"], ()) if m[1] is not None and m[1] < e["seq"]]
    naive_from = prev[-1][2] if prev else BORN.get(e["actor"])
    if anchor != naive_from: naive += 1
    cued = bool(body) and any(c in body for c in CUES)
    if place and cued:
        if mis: jmm += 1
        else:   jm += 1
    elif body and not cued:
        if mis: ncm += 1
        else:   nce += 1

print(f"mismatch_total={mm}  judged_mismatch={jmm}  judged_match={jm}  分母={jmm+jm}")
print(f"路径A: mismatch_total - judged_mismatch = {mm} - {jmm} = {mm-jmm}")
print(f"路径B: no_cue_total - no_cue_match = {ncm+nce} - {nce} = {(ncm+nce)-nce}")
print(f"naive_from_place_false_positives={naive}   no_move_dialogue={nomove}")
