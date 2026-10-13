#!/usr/bin/env python3
"""T341 独立复核：T333 情感判据【实现】(b48920c)。
自建口径，不调用作者单测。运行：
    cd code && PYTHONPATH=$(pwd) python3 ../v2/evidence/t341_emotion_impl_verify.py
"""
import os, sys, json, re

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "code"))

from life.emotion import emotion_sign, STRICT_POS, STRICT_NEG, _WRAPPER_RE, STRUCT_CATS, _STRUCT_MIN_CATS

# --- 旧实现（pre-T333 agent.py:888-890）：lower() + 26 子串，POS 优先，无包裹剔除 ---
OLD_POS = ("帮助", "成长", "喜悦", "连接", "感谢", "陪伴", "温暖", "成功",
           "support", "growth", "joy", "connect", "thanks")
OLD_NEG = ("冲突", "失败", "孤独", "失去", "争吵", "痛苦", "挫折", "焦虑",
           "conflict", "loss", "lonely", "fail", "struggle")


def old_sign(text):
    low = (text or "").lower()
    if any(k in low for k in OLD_POS):
        return 1
    if any(k in low for k in OLD_NEG):
        return -1
    return 0


RD = sys.argv[1] if len(sys.argv) > 1 else "/root/t271/runs/t326_real"


def read_body(rd, ref):
    if not ref:
        return None
    fp = None
    if ref.startswith("side://src/"):
        fp = os.path.join(rd, "side", "src", ref[len("side://src/"):].rsplit(".", 1)[0] + ".txt")
    elif ref.startswith("side://mem/"):
        fp = os.path.join(rd, "side", ref[len("side://"):])
    try:
        return open(fp, encoding="utf-8").read()
    except Exception:
        return None


def load_real(rd):
    out = []
    p = os.path.join(rd, "run.jsonl")
    if not os.path.exists(p):
        return out
    for l in open(p, encoding="utf-8"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        pl = r.get("payload") or {}
        if r.get("type") == "MEMORY_WRITE" and pl.get("kind") == "reflection":
            out.append((read_body(rd, pl.get("body_ref")), pl.get("importance")))
    return out


def main():
    real = load_real(RD)
    real_texts = [t or "" for t, _ in real]
    print(f"真样本：run={RD} reflection 条数={len(real)}")

    adv = [
        "", "（insight 1）", "帮助（insight 2）", "开心（insight 3）", "SUPPORT",
        "帮助 and 冲突", "……", "（笑了笑）", "（笑了笑）啊", "真的吗？",
        "（直起腰）……走了啊。也是。", "support growth", "冲突失败",
    ]
    corpus = real_texts + adv

    # ---- 1) strict 逐条等价旧 26 子串实现 ----
    diffs = []
    for t in corpus:
        o, n = old_sign(t), emotion_sign(t, criterion="strict")
        if o != n:
            diffs.append((t, o, n))
    print(f"\n[1] strict vs 旧26实现：{len(corpus)-len(diffs)}/{len(corpus)} 相等, 差异={len(diffs)}")
    for t, o, n in diffs[:10]:
        print("   DIFF:", repr(t), "old=", o, "new_strict=", n)
    print("    [1]", "PASS" if not diffs else "FAIL")

    # ---- 3) 复算两数（生产同一函数，真样本）----
    s_hit = sum(1 for t in real_texts if emotion_sign(t, criterion="strict") != 0)
    n_hit = sum(1 for t in real_texts if emotion_sign(t, criterion="natural") != 0)
    imp = [t for t, i in real if (i or 0) >= 7]
    s7 = sum(1 for t in imp if emotion_sign(t, criterion="strict") != 0)
    n7 = sum(1 for t in imp if emotion_sign(t, criterion="natural") != 0)
    N = len(real_texts)
    print(f"\n[3] 复算：strict {s_hit}/{N}   natural {n_hit}/{N}（importance≥7 子集：strict {s7}/{len(imp)} natural {n7}/{len(imp)}）")
    print("    [3]", "PASS(复现 0/63 与 18/63)" if (s_hit == 0 and n_hit == 18) else "CHECK（与作者读数不同，见上）")

    # ---- 2) 两档可切 + 行为随之变 ----
    changed = sum(1 for t in real_texts if emotion_sign(t, criterion="strict") != emotion_sign(t, criterion="natural"))
    lv2 = json.load(open(os.path.join(REPO, "code", "config", "life_v2.json"), encoding="utf-8"))
    key = (lv2.get("persona_drift") or {}).get("criterion")
    print(f"\n[2] 两档行为差异：真样本上 strict≠natural 的条数={changed}；life_v2.persona_drift.criterion={key!r}")
    print("    [2]", "PASS(两档行为随 criterion 变 + 键落盘)" if (changed > 0 and key in ("strict", "natural")) else "CHECK")

    # ---- 4) 反向验证必红（人为破坏 strict ⇒ 逐条等价检查须检出）----
    both = "帮助和冲突"  # 同时含 POS/NEG ⇒ 旧实现 POS 优先 -> +1
    def broken_strict(text):  # 人为：NEG 优先
        low = (text or "").lower()
        if any(k in low for k in OLD_NEG):
            return -1
        if any(k in low for k in OLD_POS):
            return 1
        return 0
    d_broken = sum(1 for t in corpus if old_sign(t) != broken_strict(t))
    print(f"\n[4] 反向验证：人为破坏(NEG优先) ⇒ 与旧实现差异={d_broken}")
    print("    [4]", "PASS(变红=检出差异)" if d_broken > 0 else "FAIL(差异=0 ⇒ 检查恒真)")

    # ---- 5) 「≥2 类共现」真生效：单类必须不命中 ----
    single = {"（笑了笑）": 0, "……": 0, "真的吗？": 0, "我觉得": 0}
    ok5 = True
    print("\n[5] 单类不命中 / ≥2 类命中：")
    for t, _ in single.items():
        s = emotion_sign(t, criterion="natural")
        cats = sum(1 for _n, rx in STRUCT_CATS if rx.search((t or "").lower()))
        verdict = (s == 0)
        ok5 &= verdict
        print(f"    {t!r} cats={cats} natural_sign={s}  {'OK(不命中)' if verdict else 'FAIL(单类却命中)'}")
    multi = "（笑了笑）啊"
    cats_m = sum(1 for _n, rx in STRUCT_CATS if rx.search(multi.lower()))
    s_m = emotion_sign(multi, criterion="natural")
    print(f"    {multi!r} cats={cats_m} natural_sign={s_m}  {'OK(≥2类命中)' if s_m != 0 else 'FAIL'}")
    ok5 &= (cats_m >= _STRUCT_MIN_CATS and s_m != 0)
    print("    [5]", "PASS" if ok5 else "FAIL")


if __name__ == "__main__":
    main()
