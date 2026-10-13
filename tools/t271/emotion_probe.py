#!/usr/bin/env python3
"""T326/T337 反思节点「含情感词」探针。
**判定式唯一实现** = `life.emotion.emotion_sign(text, *, criterion, lexicon)`（T333 单一真源）——
本探针**不再自写判定**；import 失败即 fail-loud（不保留第二份实现）。
对象 = `MEMORY_WRITE` 事件中 `kind=="reflection"` 的节点；正文经 `body_ref` 解析：
  `side://src/<digest>.txt` -> <run_dir>/side/src/<digest>.txt （T268 内容寻址）
  `side://mem/<agent>/<mem>.txt` -> <run_dir>/side/mem/<agent>/<mem>.txt
并**摘录原始样本**供人眼判断。

用法: emotion_probe.py <run_dir> [--criterion strict|natural] [--pos-file F --neg-file F] [--samples N]
"""
import sys, os, json, glob

POS = ("帮助", "成长", "喜悦", "连接", "感谢", "陪伴", "温暖", "成功",
       "support", "growth", "joy", "connect", "thanks")
NEG = ("冲突", "失败", "孤独", "失去", "争吵", "痛苦", "挫折", "焦虑",
       "conflict", "loss", "lonely", "fail", "struggle")


def read_body(rd, ref):
    if not ref:
        return None
    fp = None
    if ref.startswith("side://src/"):
        dig = ref[len("side://src/"):].rsplit(".", 1)[0]
        fp = os.path.join(rd, "side", "src", dig + ".txt")
    elif ref.startswith("side://mem/"):
        fp = os.path.join(rd, "side", ref[len("side://"):])
    try:
        return open(fp, encoding="utf-8").read()
    except Exception:
        return None


def _load_terms(path):
    terms = []
    for l in open(path, encoding="utf-8"):
        l = l.strip()
        if l and not l.startswith("#"):
            terms.append(l)
    return tuple(terms)


def _load_emotion_sign():
    """T337：判定式**唯一实现** = `life.emotion.emotion_sign`；不可用则 **fail-loud**（不保留第二份实现）。"""
    code = os.environ.get("T271_CODE",
                          "/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code")
    if code and code not in sys.path:
        sys.path.insert(0, code)
    from life.emotion import emotion_sign  # noqa: PLC0415  （import 失败即抛出，不静默回退）
    return emotion_sign


def main():
    rd = sys.argv[1]
    nsamp = 8
    if "--samples" in sys.argv:
        nsamp = int(sys.argv[sys.argv.index("--samples") + 1])
    # T334: 可换词表（离线复算，无端点）。默认 = 与 life/agent.py:862-864 相同的 26 子串。
    global POS, NEG
    pos_src, neg_src = "default(26)", "default(26)"
    if "--pos-file" in sys.argv:
        POS = _load_terms(sys.argv[sys.argv.index("--pos-file") + 1]); pos_src = "file"
    if "--neg-file" in sys.argv:
        NEG = _load_terms(sys.argv[sys.argv.index("--neg-file") + 1]); neg_src = "file"
    print(f"# lexicon: POS={len(POS)}({pos_src}) NEG={len(NEG)}({neg_src})")
    # T333：判定式单一真源 —— 优先 import life.emotion.emotion_sign；--criterion strict|natural。
    crit = "strict"
    if "--criterion" in sys.argv:
        crit = sys.argv[sys.argv.index("--criterion") + 1]
    lexicon_given = ("--pos-file" in sys.argv) or ("--neg-file" in sys.argv)
    emo_fn = _load_emotion_sign()   # T337：失败即抛（无第二份实现）
    print(f"# 判定(唯一实现, import 失败即 fail-loud): life.emotion.emotion_sign "
          f"(criterion={crit}, lexicon={'custom' if lexicon_given else 'default'})")
    log = os.path.join(rd, "run.jsonl")
    if not os.path.exists(log):
        c = sorted(glob.glob(os.path.join(rd, "*.jsonl")))
        log = c[0] if c else log
    recs = []
    for l in open(log, encoding="utf-8"):
        l = l.strip()
        if l:
            try: recs.append(json.loads(l))
            except Exception: pass
    prov = {}
    for r in recs:
        if r.get("type") == "LLM_CALL":
            k = (r.get("payload") or {}).get("provider")
            prov[k] = prov.get(k, 0) + 1
    refl = [r for r in recs if r.get("type") == "MEMORY_WRITE"
            and (r.get("payload") or {}).get("kind") == "reflection"]
    tot = emo = posn = negn = miss = i7t = i7e = 0
    samples, hits = [], []
    for r in refl:
        p = r.get("payload") or {}
        txt = read_body(rd, p.get("body_ref"))
        if txt is None:
            miss += 1; continue
        low = txt.lower()
        hp = [w for w in POS if w in low]; hn = [w for w in NEG if w in low]  # 仅用于展示/自定义词表，**不判**
        # 判定**唯一实现** = life.emotion.emotion_sign（探针不再自写判定）
        sign = emo_fn(txt, criterion=crit, lexicon=((POS, NEG) if lexicon_given else None))
        e = sign != 0; imp = int(p.get("importance") or 0)
        tot += 1; emo += e; posn += (sign > 0); negn += (sign < 0)
        if imp >= 7:
            i7t += 1; i7e += e
        if e:
            hits.append({"mem_id": p.get("mem_id"), "imp": imp, "POS": hp, "NEG": hn, "text": txt[:120]})
        if len(samples) < nsamp:
            samples.append({"mem_id": p.get("mem_id"), "agent": p.get("agent_id"),
                            "imp": imp, "len": len(txt), "text": txt[:200]})

    print(f"# T326 emotion probe (v2)  log={log}")
    print(f"# LLM_CALL provider 计数: {prov}")
    print(f"reflect_write(kind=reflection)={len(refl)}  body可读={tot}  取正文失败={miss}")
    print(f"含情感词(sign!=0; criterion={crit}, lexicon={'custom' if lexicon_given else 'default'}, "
          f"impl=life.emotion.emotion_sign): {emo}/{tot} = {emo/max(tot,1):.1%}  (+{posn}/-{negn})")
    print(f"importance>=7 子集: {i7e}/{i7t} = {i7e/max(i7t,1):.1%}")
    print(f"== 原始样本 {len(samples)} 条（供人眼判『有没有情绪』）==")
    for s in samples:
        print("  " + json.dumps(s, ensure_ascii=False))
    if hits:
        print(f"== 词表命中样例 {len(hits)} 条 ==")
        for h in hits[:5]:
            print("  " + json.dumps(h, ensure_ascii=False))


if __name__ == "__main__":
    main()
