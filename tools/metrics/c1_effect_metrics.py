#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C1 处境锚：效果层「生活气息」四指标读数（A0 off / A1 on，纯静态复算，不需要新跑批）。

判据层级（**必须分开读，不许互相顶替**）：

  M1 = 预登记主指标（`v2/refs/C1-scene-prereg-20261101.md` §2/§3/§4）
       「处所-内容一致性率」——**唯一决定 成立/不成立/不可判 的指标**，
       直接复用冻结尺子 `tools/metrics/place_content_consistency.py`（同一 lexicon_sha256），
       本脚本不改它的词表、不改它的分母口径、不改它的通过线。

  M2~M4 = 本轮新增的辅助读数（**未预登记**，只作解释与方向参考，**不参与判定**）：
       M2 锚点自证：注入提示词的「处境锚」有没有指对地方（`ctx.scene.place` vs `payload.place`），
          并把 M1 判为「相悖」的条目拆成「内容贴合锚点场所 / 内容两边都不贴」，
          用来区分「模型无视锚点」与「锚点本身带偏了模型」。
       M3 具体性密度：发言里「具体实词」（物件/时间/地点/人名）的密度与命中率
          —— 生活气息的直接表征：说的是不是具体的事，而不是空话。
       M4 可见动作与长度：括号旁白（动作/神态）占比、旁白字数占比、发言长度分布
          —— 生活气息的另一个表征：看得见人在做什么。

口径纪律：
  * 只读 `run.jsonl`。**绝不读 side_root**（A0 的 side_root 曾被 A1 attempt1 误写 211 文件，
    见 `v2/evidence/c1-scene-a0-20261101_n16r24_s42/SIDE_ROOT_CONTAMINATED.md`；
    污染发生在 A0 收批之后，A0 的 run.jsonl 本身未受影响）。
  * 输出确定性：无时间戳、无随机、无排序不稳的容器，同一输入两次运行逐字节一致。
  * 统计口径诚实：所有比率给 Wilson 95% CI；两臂独立样本用 Fisher 精确检验（双侧）；
    样本小照实说，不下显著性以外的因果结论。

用法：
    python3 tools/metrics/c1_effect_metrics.py \
        --arm A0=v2/evidence/c1-scene-a0-20261101_n16r24_s42/run.jsonl \
        --arm A1=v2/evidence/c1-scene-a1-20261101_n16r24_s42/run.jsonl \
        [--out-md reports/R46-...md]

    # 幂等自检
    python3 tools/metrics/c1_effect_metrics.py --arm A0=... --arm A1=... > /tmp/a.txt
    python3 tools/metrics/c1_effect_metrics.py --arm A0=... --arm A1=... > /tmp/b.txt
    cmp /tmp/a.txt /tmp/b.txt && echo BYTE_IDENTICAL
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_content_consistency as RULER  # noqa: E402

DIALOGUE = RULER.DIALOGUE_TYPES

# ---------------------------------------------------------------------------
# M3 词表（本轮新增，非预登记；冻结在本文件里，改动即须重新登记指标定义书）
#   家族①物件/器物/农活：直接复用 M1 冻结尺子的线索词表（同一份词，不另立标准）
#   家族②时间词：显式人话词表
#   家族③地点词：`code/config/places.json::name_cn`（人话名，运行时读取，digest 打印）
#   家族④人名：`code/config/personas.json::display_name` 里 "·" 之后的那一段
# ---------------------------------------------------------------------------
TIME_WORDS = (
    "今儿", "今天", "今早", "昨儿", "昨天", "明儿", "明天", "后儿",
    "天亮", "一大早", "上午", "晌午", "下午", "傍晚", "擦黑", "夜里", "半夜",
    "这会儿", "那会儿", "这两天", "这几天", "这些年", "今年", "开春", "入夏",
    "入秋", "入冬", "月初", "月底", "上回", "下回",
)
TIME_VERSION = "c1-time-words-v1"

# 解析用的回退值（读不到配置时用它，保证脚本仍可运行；digest 会随之变化并被打印）
_FALLBACK_PLACES = {
    "residence": "住宅", "farm": "农场", "workshop": "工坊", "kitchen": "面包房",
    "clinic": "诊所", "school": "学校", "office": "办事处", "market": "市集",
    "bank": "银行", "plaza": "广场", "town_hall": "镇公所", "library": "图书馆",
    "community_center": "社区中心", "cafe": "咖啡馆", "park": "公园",
    "hall": "过道", "gate": "大门",
}

PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_place_names() -> dict:
    """place_id -> name_cn（人话名）。读不到 ⇒ 用回退表并如实标注来源。"""
    path = os.path.join(PROJECT_ROOT, "code", "config", "places.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        out = {}
        for item in data.get("places", []):
            pid, name = item.get("place_id"), (item.get("name_cn") or "").strip()
            if pid and name:
                out[str(pid)] = name
        if out:
            return out
    except Exception:
        pass
    return dict(_FALLBACK_PLACES)


def load_person_names() -> tuple:
    """居民人话名（display_name '·' 之后那一段）。读不到 ⇒ 空表（该家族记 0 命中）。"""
    path = os.path.join(PROJECT_ROOT, "code", "config", "personas.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        names = []
        for p in data.get("personas", []):
            dn = str(p.get("display_name") or "").strip()
            name = dn.split("·")[-1].strip() if dn else ""
            if name:
                names.append(name)
        return tuple(sorted(set(names)))
    except Exception:
        return tuple()


def concrete_lexicon() -> dict:
    """M3 词表面（四家族）。digest 由内容决定，随 run 一起打印。"""
    objects = sorted({w for d in RULER.DOMAINS.values() for w in d["cues"]})
    places = sorted({w for w in load_place_names().values() if w})
    persons = list(load_person_names())
    return {
        "object": tuple(objects),
        "time": tuple(TIME_WORDS),
        "place": tuple(places),
        "person": tuple(persons),
    }


def lexicon_digest(lex: dict) -> str:
    blob = json.dumps({k: list(v) for k, v in lex.items()},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha("c1-concrete-v1|" + blob)


# ---------------------------------------------------------------------------
# 统计小工具（确定性、无第三方依赖）
# ---------------------------------------------------------------------------
def wilson(k: int, n: int, z: float = 1.96) -> tuple:
    """Wilson 95% 区间；n=0 返回 (None, None)。"""
    if n <= 0:
        return (None, None)
    p = k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """2x2 表 [[a,b],[c,d]] 的双侧 Fisher 精确检验 p 值（超几何精确枚举）。"""
    n = a + b + c + d
    if n == 0:
        return 1.0
    r1, r2 = a + b, c + d
    c1 = a + c

    def hyper(x: int) -> float:
        return math.comb(r1, x) * math.comb(r2, c1 - x) / math.comb(n, c1)

    p_obs = hyper(a)
    lo, hi = max(0, c1 - r2), min(r1, c1)
    total = sum(hyper(x) for x in range(lo, hi + 1) if hyper(x) <= p_obs + 1e-12)
    return min(1.0, total)


def pct(k: int, n: int) -> str:
    return "%.2f%% (%d/%d)" % (100.0 * k / n, k, n) if n else "NA"


def rate_ci(k: int, n: int) -> str:
    if not n:
        return "NA"
    lo, hi = wilson(k, n)
    return "%.4f [%.3f, %.3f] (%d/%d)" % (k / n, lo, hi, k, n)


# ---------------------------------------------------------------------------
# 单臂读数
# ---------------------------------------------------------------------------
BRACKET_RE = None


def _bracket_spans(body: str) -> list:
    """括号旁白（全角（）与半角()）的字符区间；不嵌套、成对匹配。"""
    spans, stack = [], []
    for i, ch in enumerate(body):
        if ch in "（(":
            stack.append(i)
        elif ch in "）)" and stack:
            j = stack.pop()
            spans.append((j, i))
    return spans


def read_arm(path: str) -> dict:
    raw = open(path, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()   # 逐字节 sha256（不改内容）

    # 预扫描：每条对话消息的「同轮内、本条之前」该 actor 是否刚移动到消息所在场所。
    # 用途仅限 M2b 归因（锚点为何指错），不改 M1 的任何口径。
    arrivals = collections.defaultdict(list)   # actor -> [(round, seq, place)]
    moves = collections.defaultdict(list)      # actor -> [(round, seq, from_place, to_place)]
    for line in raw.decode("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        if e.get("type") == "PLACE_MOVE":
            pl_ = e.get("payload") or {}
            actor = e.get("actor") or pl_.get("agent_id")
            if actor:
                moves[actor].append((e.get("round"), e.get("seq"),
                                     str(pl_.get("from_place") or ""),
                                     str(pl_.get("to_place") or "")))
            continue
        if e.get("type") != "PLACE_ARRIVED":
            continue
        pl_ = e.get("payload") or {}
        actor = e.get("actor") or pl_.get("agent_id")
        if actor:
            arrivals[actor].append((e.get("round"), e.get("seq"), str(pl_.get("place") or "")))

    lex = concrete_lexicon()
    n_dlg = n_missing = n_no_cue = n_judged = n_agree = 0
    scene_key = 0
    anchor_eq = 0
    anchor_mismatch = 0
    anchor_mismatch_explained = 0   # 被「同轮内先到达消息场所」解释的锚点错位
    anchor_eq_from_place = 0        # 锚点场所 == 同轮前一次 PLACE_MOVE.from_place
    anchor_neither_from_nor_to = 0  # 两者都不是（若 >0 则「移动前快照」解释被证伪）
    dlg_same_round_move = 0         # 本 round 内有过移动的对话条数
    dlg_no_same_round_move = 0      # 本 round 内没有移动的对话条数
    # M1 相悖条目的归因拆分
    contra_anchor_ok = 0     # 内容不贴真实 place，但贴锚点场所 ⇒ 被锚点带偏
    contra_neither = 0       # 两边都不贴 ⇒ 与锚点无关的脱钩
    # M3
    hit_msgs = 0
    fam_msg = collections.Counter()          # 含该家族词的发言条数
    hits_total = 0
    chars_total = 0
    # M4
    bracket_msgs = 0
    bracket_chars = 0
    lens = []
    inconsistent = []

    for line in raw.decode("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        if e.get("type") not in DIALOGUE:
            continue
        n_dlg += 1
        p = e.get("payload") or {}
        ctx = p.get("ctx") or {}
        scene = ctx.get("scene") if isinstance(ctx.get("scene"), dict) else None
        place = (p.get("place") or "").strip()
        body = (p.get("body") or "").strip()

        # ---- M2 机制层：scene 键 + 锚点指对率 ----
        actor_ = e.get("actor") or p.get("author") or p.get("from")
        rnd_, seq_ = e.get("round"), e.get("seq")
        prior_moves = [m for m in moves.get(actor_, ())
                       if m[0] == rnd_ and seq_ is not None and m[1] is not None and m[1] < seq_]
        if prior_moves:
            dlg_same_round_move += 1
        else:
            dlg_no_same_round_move += 1
        if scene is not None:
            scene_key += 1
            if str(scene.get("place") or "") == place:
                anchor_eq += 1
            elif place:
                anchor_mismatch += 1
                if any(r == rnd_ and s is not None and seq_ is not None and s < seq_ and pl_ == place
                       for r, s, pl_ in arrivals.get(actor_, ())):
                    anchor_mismatch_explained += 1
                if prior_moves:
                    from_p, to_p = prior_moves[-1][2], prior_moves[-1][3]
                    a = str(scene.get("place") or "")
                    if a == from_p:
                        anchor_eq_from_place += 1
                    elif a != to_p:
                        anchor_neither_from_nor_to += 1

        if not body:            # 缺 body 不进 M3/M4 的分母，也不进 M1 分母
            continue

        # ---- M3 具体性 ----
        lens.append(len(body))
        chars_total += len(body)
        hits_this = 0
        for fam, words in lex.items():
            fam_hit = 0
            for w in words:
                if w and w in body:
                    fam_hit += body.count(w)
            if fam_hit:
                fam_msg[fam] += 1
                hits_this += fam_hit
        if hits_this:
            hit_msgs += 1
            hits_total += hits_this

        # ---- M4 旁白/长度 ----
        spans = _bracket_spans(body)
        if spans:
            bracket_msgs += 1
            bracket_chars += sum(b - a + 1 for a, b in spans)

        # ---- M1 处所-内容一致性（冻结尺子，口径一字不改）----
        if not place:
            n_missing += 1
            continue
        doms, cues = RULER.classify(body)
        if not doms:
            n_no_cue += 1
            continue
        n_judged += 1
        ok = any(place in RULER.DOMAINS[d]["places"] for d in doms)
        if ok:
            n_agree += 1
        else:
            anchor_place = str((scene or {}).get("place") or "")
            if anchor_place and any(anchor_place in RULER.DOMAINS[d]["places"] for d in doms):
                contra_anchor_ok += 1
            else:
                contra_neither += 1
            if len(inconsistent) < 5:
                inconsistent.append({
                    "seq": e.get("seq"), "actor": p.get("author") or p.get("from"),
                    "place": place, "anchor": anchor_place or "-",
                    "domains": ",".join(doms), "cues": ",".join(cues),
                    "body": body[:70],
                })

    n_contra = n_judged - n_agree
    return {
        "path": path, "sha256": sha,
        "n_dialogue": n_dlg, "n_missing_place": n_missing,
        "n_no_cue": n_no_cue, "denom": n_judged, "agree": n_agree,
        "contra": n_contra,
        "contra_anchor_ok": contra_anchor_ok, "contra_neither": contra_neither,
        "scene_key": scene_key, "anchor_eq": anchor_eq,
        "anchor_mismatch": anchor_mismatch,
        "anchor_mismatch_explained": anchor_mismatch_explained,
        "anchor_eq_from_place": anchor_eq_from_place,
        "anchor_neither_from_nor_to": anchor_neither_from_nor_to,
        "dlg_same_round_move": dlg_same_round_move,
        "dlg_no_same_round_move": dlg_no_same_round_move,
        "no_cue_share": (n_no_cue / n_dlg) if n_dlg else None,
        "lex": lex,
        # M3
        "hit_msgs": hit_msgs, "hits_total": hits_total,
        "chars_total": chars_total, "fam_msg": dict(fam_msg),
        "n_body": len(lens),
        # M4
        "bracket_msgs": bracket_msgs, "bracket_chars": bracket_chars,
        "lens": lens,
        "inconsistent": inconsistent,
    }


def _median(xs: list):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return float(xs[m]) if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2.0


def _p90(xs: list):
    xs = sorted(xs)
    if not xs:
        return None
    return float(xs[min(len(xs) - 1, int(math.ceil(0.9 * len(xs))) - 1)])


# ---------------------------------------------------------------------------
# 可比性闸（照抄预登记卡 §5.2 的口径：env_manifest 差异必须只有 LIFE_PROMPT_SCENE 一行）
# ---------------------------------------------------------------------------
def _parse_manifest(path: str) -> dict:
    out = {}
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except Exception:
        return out
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            body = s.lstrip("#").strip()
            if body.startswith("INLINE_ENV="):
                for tok in body[len("INLINE_ENV="):].split():
                    if "=" in tok:
                        k, _, v = tok.partition("=")
                        out[k.strip()] = "%s=%s" % (k.strip(), v)
            continue
        if "=" in s:
            k, _, v = s.partition("=")
            out[k.strip()] = "%s=%s" % (k.strip(), v)
    return out


def env_diff(a_dir: str, b_dir: str) -> tuple:
    fa = os.path.join(a_dir, "env_manifest.txt")
    fb = os.path.join(b_dir, "env_manifest.txt")
    if not (os.path.exists(fa) and os.path.exists(fb)):
        return "missing", []
    ma, mb = _parse_manifest(fa), _parse_manifest(fb)
    diff, keys = [], set()
    for k in sorted(set(ma) | set(mb)):
        if ma.get(k) == mb.get(k):
            continue
        keys.add(k)
        if ma.get(k) is None:
            diff.append("+ %s" % mb[k])
        elif mb.get(k) is None:
            diff.append("- %s" % ma[k])
        else:
            diff.append("- %s" % ma[k])
            diff.append("+ %s" % mb[k])
    return ("ok_only_scene" if keys <= {"LIFE_PROMPT_SCENE"} else "differs_more"), diff


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True, help="NAME=run.jsonl（至少 A0/A1 各一次）")
    ap.add_argument("--out-md", default="", help="把报告写到该路径（同时打印到 stdout）")
    args = ap.parse_args()

    arms, order = {}, []
    for spec in args.arm:
        name, _, path = spec.partition("=")
        name = name.strip()
        if not os.path.exists(path):
            print("ERROR: run.jsonl 不存在: %s" % path, file=sys.stderr)
            return 2
        arms[name] = read_arm(path)
        order.append(name)
    a0, a1 = arms.get("A0"), arms.get("A1")
    lex = concrete_lexicon()
    lex_dig = lexicon_digest(lex)

    L = []
    w = L.append
    w("# C1 处境锚 · 效果层「生活气息」四指标读数（静态复算，0 新增跑批）")
    w("")
    w("- 尺子①（预登记主指标）：`tools/metrics/place_content_consistency.py`，"
      "lexicon_sha256 = `%s`" % RULER.LEXICON_DIGEST)
    w("- 尺子②（本文件，M2~M4 辅助读数，**非预登记**）：`tools/metrics/c1_effect_metrics.py`，"
      "concrete_lexicon_sha256 = `%s`" % lex_dig)
    w("- 判据来源：`v2/refs/C1-scene-prereg-20261101.md`（通过线/不可判闸门按卡执行，本脚本不设阈值）")
    w("- 通过线（先验，不得事后下调）：Δrate(A1−A0) ≥ **+15.0pp** 且 rate(A1) ≥ **0.55**")
    w("- 数据源：仅两臂 `run.jsonl`；**未读任何 side_root**（A0 side_root 已被 A1 attempt1 误写，见批次内 `SIDE_ROOT_CONTAMINATED.md`）")
    w("")

    # ---------- 闸门 ----------
    reasons = []
    diff_state, diff_lines = ("missing", [])
    if a0 and a1:
        diff_state, diff_lines = env_diff(os.path.dirname(a0["path"]), os.path.dirname(a1["path"]))
        if diff_state == "differs_more":
            reasons.append("两臂 env_manifest 差异不止 `LIFE_PROMPT_SCENE` 一行")
        elif diff_state == "missing":
            reasons.append("缺 `env_manifest.txt`，两臂可比性无法核对")
    for n in order:
        if arms[n]["denom"] < 30:
            reasons.append("分母不足 30（%s denom=%d），按卡 §5.1 判不可判" % (n, arms[n]["denom"]))
    if a0 and a1:
        s0, s1 = a0["no_cue_share"], a1["no_cue_share"]
        if s0 is not None and s1 is not None and abs(s1 - s0) >= 0.10:
            reasons.append("两臂 `no_cue` 占比差 ≥10pp（可判定子集构成漂移，卡 §5.5）")

    d_pp = None
    if a0 and a1 and a0["denom"] and a1["denom"]:
        d_pp = (a1["agree"] / a1["denom"] - a0["agree"] / a0["denom"]) * 100.0

    mech = "未接通的判定项缺失"
    if a1 is not None:
        mech = ("机制已接通（A1 `ctx.scene` 覆盖 %d/%d）" % (a1["scene_key"], a1["n_dialogue"])
                if a1["scene_key"] else "机制未接通（A1 `ctx.scene` 覆盖率 0）")

    if reasons:
        verdict = "不可判"
    elif d_pp is not None and d_pp >= 15.0 and (a1["agree"] / a1["denom"]) >= 0.55:
        verdict = "成立"
    elif d_pp is not None:
        verdict = "不成立"
    else:
        verdict = "不可判"

    w("## 0. 判定（M1 预登记主指标）")
    w("")
    w("- 判定：**%s**" % verdict)
    w("- 机制层：**%s**" % mech)
    if reasons:
        w("- 不可判原因：" + "；".join(reasons))
    if d_pp is not None:
        w("- **Δrate(A1−A0) = %+.2fpp**（口径：绝对百分点差，条件一致率）" % d_pp)
    w("")

    # ---------- M1 表 ----------
    w("## 1. M1（预登记主指标）· 处所-内容一致性率")
    w("")
    w("分子＝判为「相符」的可判定对话条数；分母＝对话类事件 − 缺 `place`/`body` 条数 − `no_cue` 条数；"
      "计算式＝分子÷分母；纳入＝`type ∈ {MSG_PUBLIC, MSG_DM}` 且 `payload.place`、`payload.body` 非空且命中冻结线索词表。")
    w("")
    w("| 臂 | 对话事件 | 缺字段 | no_cue | no_cue 占比 | 分母 | 相符 | 一致率 [Wilson 95%] |")
    w("|---|---|---|---|---|---|---|---|")
    for n in order:
        v = arms[n]
        w("| %s | %d | %d | %d | %s | %d | %d | %s |" % (
            n, v["n_dialogue"], v["n_missing_place"], v["n_no_cue"],
            pct(v["n_no_cue"], v["n_dialogue"]), v["denom"], v["agree"],
            rate_ci(v["agree"], v["denom"])))
    if a0 and a1:
        fisher_p = fisher_two_sided(a0["agree"], a0["contra"], a1["agree"], a1["contra"])
        w("")
        w("两臂 2×2（相符/相悖）×（A0/A1）：Fisher 精确检验双侧 **p = %.4f**；"
          "单批、单 seed、无重复批 ⇒ 只能作**点估计**，不作因果外推。" % fisher_p)
    w("")

    # ---------- M2 ----------
    w("## 2. M2（辅助读数，非预登记）· 锚点自证：注入的处境锚有没有指对地方")
    w("")
    w("定义式：锚点指对率 ＝ `ctx.scene.place == payload.place` 的对话条数 ÷ 含 `ctx.scene` 的对话条数；"
      "分母只含含 `scene` 键的条目（A0 无该键 ⇒ 分母 0，读数 NA，不是 0%）。")
    w("")
    w("| 臂 | 含 scene 键 | 锚点 place == 消息 place | 锚点指对率 [Wilson 95%] |")
    w("|---|---|---|---|")
    for n in order:
        v = arms[n]
        w("| %s | %d/%d | %d | %s |" % (
            n, v["scene_key"], v["n_dialogue"], v["anchor_eq"],
            rate_ci(v["anchor_eq"], v["scene_key"]) if v["scene_key"] else "NA（无 scene 键）"))
    if a1 and a1["contra"]:
        w("")
        w("**相悖条目归因（只对 A1 有意义，分母 = M1 相悖条数 %d）**：" % a1["contra"])
        w("")
        w("- 内容贴「锚点所说场所」而不贴「消息实际场所」：**%s** ⇒ 锚点把模型带偏" % pct(a1["contra_anchor_ok"], a1["contra"]))
        w("- 两边都不贴（与锚点无关的脱钩）：**%s**" % pct(a1["contra_neither"], a1["contra"]))
        w("")
        w("> 解读纪律：M2 是**机制质量**读数，不是效果层结论。锚点指对率低不等于「处境锚无用」，"
          "但它直接决定「模型被告知的处境」与「这条发言实际发生的场所」是否同一件事——"
          "两者不一致时，任何按 `payload.place` 判定的效果层读数都会被系统性拉低。")
    if a1 and a1["scene_key"]:
        w("")
        w("### 2b. 锚点错位归因：为什么锚点指错地方（含判伪条件）")
        w("")
        w("定义式：锚点错位条数 ＝ 含 `scene` 键且 `ctx.scene.place != payload.place` 的对话条数；"
          "「同轮内先到达」＝ 该发言的 actor 在**同一 round、seq 更小**处出现过 "
          "`PLACE_ARRIVED(place == payload.place)`；"
          "「锚点＝移动前场所」＝ `ctx.scene.place == 同轮前一次 PLACE_MOVE.from_place`。")
        w("")
        w("| 臂 | 锚点错位 | 同轮内先到达可解释 | 锚点 == 同轮前一次 `PLACE_MOVE.from_place` | 既非 from 也非 to（**判伪反例**） |")
        w("|---|---|---|---|---|")
        for n in order:
            v = arms[n]
            w("| %s | %d | %d（%s） | %d（%s） | **%d** |" % (
                n, v["anchor_mismatch"], v["anchor_mismatch_explained"],
                pct(v["anchor_mismatch_explained"], v["anchor_mismatch"]) if v["anchor_mismatch"] else "NA",
                v["anchor_eq_from_place"],
                pct(v["anchor_eq_from_place"], v["anchor_mismatch"]) if v["anchor_mismatch"] else "NA",
                v["anchor_neither_from_nor_to"]))
        w("")
        w("| 臂 | 本 round 内有过移动的对话 | 本 round 内无移动的对话 |")
        w("|---|---|---|")
        for n in order:
            v = arms[n]
            w("| %s | %d | %d |" % (n, v["dlg_same_round_move"], v["dlg_no_same_round_move"]))
        w("")
        w("> 读法（须与数字一起引用）：若「锚点 == `from_place`」占比 100% 且「判伪反例」= 0，说明错位"
          "**不是随机噪声**，而是「处境快照取自本轮移动之前」的确定性时序问题"
          "（`WorldView` 在本轮 perceive 阶段取定，居民随后在本轮内移动并在新场所说话）⇒ 锚点描述的是**上一站**。"
          "这是机制实现层的问题，不是效果层结论；修它属于下一轮的代码改动（本轮不动冻结区）。")
        w("")
        w("**判伪条件（任一成立即推翻上面的解释）**：")
        w("1. 「既非 from 也非 to」的错位 > 0 ⇒ 锚点不是移动前快照，另有来源；")
        w("2. 存在**本轮无移动**却 `ctx.scene.place != payload.place` 的对话 ⇒ 不是同轮时序问题；")
        w("3. 存在某 actor 的 `payload.place` 与本轮前一次 `PLACE_MOVE.to_place` 不一致（即 place 记录口径本身可疑）；")
        w("4. 把 scene 快照改为「发言时点场所」后，`锚点指对率` 没有上升（需新跑批，本轮不可测）。")
    w("")

    # ---------- M3 ----------
    w("## 3. M3（辅助读数，非预登记）· 具体性密度（说的是具体的事，还是空话）")
    w("")
    w("定义式：具体实词命中数 ＝ 发言正文里四家族词表（物件 %d 词 / 时间 %d 词 / 地点 %d 词 / 人名 %d 词）的"
      "**总命中次数**（同一词重复出现重复计）；密度 ＝ 命中数 ÷ 正文字数 × 100；"
      "具体性发言率 ＝ 至少命中 1 个具体实词的发言条数 ÷ 有 `body` 的对话条数。" % (
          len(lex["object"]), len(lex["time"]), len(lex["place"]), len(lex["person"])))
    w("")
    w("| 臂 | 有 body 条数 | 命中的发言数 | 具体性发言率 [Wilson 95%] | 总命中数 | 每百字命中 | 正文字数 |")
    w("|---|---|---|---|---|---|---|")
    for n in order:
        v = arms[n]
        dens = (100.0 * v["hits_total"] / v["chars_total"]) if v["chars_total"] else None
        w("| %s | %d | %d | %s | %d | %s | %d |" % (
            n, v["n_body"], v["hit_msgs"], rate_ci(v["hit_msgs"], v["n_body"]),
            v["hits_total"], ("%.3f" % dens) if dens is not None else "NA", v["chars_total"]))
    if a0 and a1 and a0["n_body"] and a1["n_body"]:
        p = fisher_two_sided(a0["hit_msgs"], a0["n_body"] - a0["hit_msgs"],
                             a1["hit_msgs"], a1["n_body"] - a1["hit_msgs"])
        w("")
        w("具体性发言率两臂 Fisher 精确检验双侧 **p = %.4f**。" % p)
        w("")
        w("**分家族命中条数（同一发言可命中多家族，故合计 ≠ 命中发言数）**")
        w("")
        w("| 臂 | 物件/器物 | 时间 | 地点 | 人名 |")
        w("|---|---|---|---|---|")
        for n in order:
            v = arms[n]["fam_msg"]
            w("| %s | %d | %d | %d | %d |" % (
                n, v.get("object", 0), v.get("time", 0), v.get("place", 0), v.get("person", 0)))
    w("")
    w("> 口径局限（须与数字一起引用）：地名/人名按**人话名字面**匹配，居民用「铺子/镇上」这类口语别名时算漏；"
      "物件词表沿用冻结尺子，覆盖面有限。因此 M3 只能读**方向**，不能读「具体性提升了 X%」这种绝对话。")
    w("")

    # ---------- M4 ----------
    w("## 4. M4（辅助读数，非预登记）· 可见动作（括号旁白）与发言长度分布")
    w("")
    w("定义式：旁白发言率 ＝ 正文含成对括号（全角`（）`或半角`()`）的发言条数 ÷ 有 `body` 对话条数；"
      "旁白字数占比 ＝ 括号内字符数（含括号）÷ 正文字数；长度分布按**正文字符数**统计。")
    w("")
    w("| 臂 | 有 body 条数 | 含旁白发言 | 旁白发言率 [Wilson 95%] | 旁白字数占比 | 长度 mean | median | p90 |")
    w("|---|---|---|---|---|---|---|---|")
    for n in order:
        v = arms[n]
        share = (100.0 * v["bracket_chars"] / v["chars_total"]) if v["chars_total"] else None
        mean = (v["chars_total"] / v["n_body"]) if v["n_body"] else None
        w("| %s | %d | %d | %s | %s | %s | %s | %s |" % (
            n, v["n_body"], v["bracket_msgs"], rate_ci(v["bracket_msgs"], v["n_body"]),
            ("%.2f%%" % share) if share is not None else "NA",
            ("%.1f" % mean) if mean is not None else "NA",
            ("%.1f" % _median(v["lens"])) if v["lens"] else "NA",
            ("%.0f" % _p90(v["lens"])) if v["lens"] else "NA"))
    w("")

    # ---------- 可比性 ----------
    w("## 5. 可比性闸（照抄预登记卡 §5.2）")
    w("")
    w("两臂 `env_manifest.txt` 逐 key 双向比对：状态 `%s`，差异行 %d 条。" % (diff_state, len(diff_lines)))
    if diff_lines:
        w("")
        w("```")
        for l in diff_lines[:40]:
            w(l)
        w("```")
    w("")

    # ---------- 样本与外推边界 ----------
    w("## 6. 样本量与可信度（照实说，不包装）")
    w("")
    w("- 每臂：16 居民 × 24 轮、单 seed（42）、单批；对话类事件 %d 条，M1 可判定分母 %s。" % (
        (a0 or a1)["n_dialogue"], " / ".join("%s=%d" % (n, arms[n]["denom"]) for n in order)))
    w("- 所有比率都给 Wilson 95% CI；两臂为独立样本，差异用 Fisher 精确检验；**未做多重比较校正**（M2~M4 为辅助读数，不作判定）。")
    w("- 单批单 seed ⇒ 无批间方差估计，差异只能作**点估计**；不得写「提升了 X%」以外的显著性断言。")
    w("- M1 为纯规则版，**未用 LLM judge**，结论强度弱于人工标注。")
    w("")

    # ---------- 不一致样本 ----------
    for n in order:
        v = arms[n]
        w("## 附录 %s：M1 相悖样本（≤5，seq / 人物 / 消息 place / 锚点 place / 活动域 / 线索 / 片段）" % n)
        w("")
        if not v["inconsistent"]:
            w("（无）")
        for it in v["inconsistent"]:
            w("- seq=%s %s place=%s anchor=%s domains=%s cues=%s ｜ %s" % (
                it["seq"], it["actor"], it["place"], it["anchor"], it["domains"], it["cues"], it["body"]))
        w("")

    # ---------- 复算 ----------
    w("## 7. 复算命令")
    w("")
    w("```bash")
    w("# 一条命令出两臂全部读数")
    w("python3 tools/metrics/c1_effect_metrics.py " + " ".join(
        "--arm %s=%s" % (n, arms[n]["path"]) for n in order) + " --out-md <path>")
    w("")
    w("# 幂等自检（同一输入两次运行必须逐字节一致）")
    w("python3 tools/metrics/c1_effect_metrics.py --arm A0=<a0>/run.jsonl --arm A1=<a1>/run.jsonl > /tmp/a.txt")
    w("python3 tools/metrics/c1_effect_metrics.py --arm A0=<a0>/run.jsonl --arm A1=<a1>/run.jsonl > /tmp/b.txt")
    w("cmp /tmp/a.txt /tmp/b.txt && echo BYTE_IDENTICAL")
    w("")
    w("# 预登记主指标的原始尺子（独立复核用，与上面 M1 数字须一致）")
    for n in order:
        w("python3 tools/metrics/place_content_consistency.py --run %s" % arms[n]["path"])
    w("```")
    w("")
    w("两臂 `run.jsonl` 逐字节 sha256：")
    for n in order:
        w("- %s: `%s`（%d B）" % (n, arms[n]["sha256"], os.path.getsize(arms[n]["path"])))

    text = "\n".join(L) + "\n"
    if args.out_md:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_md)), exist_ok=True)
        with open(args.out_md, "w", encoding="utf-8") as f:
            f.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
