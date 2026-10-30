#!/usr/bin/env python3
"""D10 C-A「称呼与关系演化」只读尺子 —— `address_drift.py`。

一句话：从 `run.jsonl` 里把「谁怎么叫谁」抽出来，量三件事——
`addr_vocab_per_pair`（角色对用过几种称呼）、`addr_switch_rate`（同线程相邻两条之间称呼有没有变）、
`addr_stage_ordinal`（首/末次称呼的亲密度序，用**先冻结**的有序词表）。

零 LLM、零写入运行时代码、纯只读。词表口径唯一来源 = `v2/refs/address-ordinal.yaml`
（先冻结、后出数；其 sha256 记在 `v2/refs/D10-address-freeze-receipt.txt`）。

三条口径定义（出数前写死，报告逐条披露）：

1. `addr_vocab_per_pair`
   单位 = **无向角色对**（只在 `MSG_DM` 线程里建立，`payload.to` 明确时）。
   纳入条件 = 该对之间 `MSG_DM` 条数 ≥ 3。
   值 = 双方对彼此用过的**去重称呼形式数**（呼语位命中才算，见 §呼语位）。
   另报 `addr_vocab_per_pair_mean` / `median` / `denom_pairs`。

2. `addr_switch_rate`
   单位 = **同线程相邻 MSG 对**（`thread_id` 相同，按 `turn_index`/`seq` 排序的 i 与 i+1）。
   分子 = 两端**都识别出称呼且形式不同**的相邻对。
   分母 = 两端**都识别出称呼**的相邻对（`denom_scored_pairs`）；
   另报 `denom_all_pairs`（全部相邻对）与 `switch_rate_all_pairs`（分子 / 全部相邻对）以便读出"称呼覆盖率低"的影响。

3. `addr_stage_ordinal`
   单位 = **有向说话对**（speaker → addressee，仅 `MSG_DM`）。
   纳入条件 = 该有向对识别出的称呼 ≥ 2 次。
   值 = 首次称呼 tier 与末次称呼 tier（按 `seq` 升序），`delta = last - first`；
   报 `升/平/降` 计数、`mean_delta`、以及逐对明细（本规模下对量很小，必须逐条列出）。
   同时用词表 `coarse_tiers`（粗疏 / 乡亲 / 近昵）复算一遍（有序性本身是判断 ⇒ 必须给敏感性）。

描述量（**不参与主判**，避免把"提及"当"称呼"）：
   `addr_any_mention_rate` = 任意位置出现称呼形式的 MSG 占比（含提及、含旁白外正文）。

预处理（写出以便复算）：
   * 先把 `（…）` / `(…)` 括注内容整段剥掉（旁白通道不是台词，不参与称呼统计）；
   * 再按词表做**最长优先**匹配，命中位置必须满足呼语位（前/后字符规则），
     同一句命中多个时取**最靠前**的一个。

用法：
   python3 tools/metrics/address_drift.py --log v2/evidence/<批>/run.jsonl --arm OFF \
       --out-json v2/evidence/d10_address_drift/<tag>.json \
       --out-md   v2/evidence/d10_address_drift/<tag>.md
   python3 tools/metrics/address_drift.py --selftest
退出码：0 正常；2 输入不可用；3 自检失败。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import sys
import time
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_LEXICON = os.path.join(ROOT, "v2", "refs", "address-ordinal.yaml")
DEFAULT_PERSONAS = os.path.join(ROOT, "code", "config", "personas.json")

PAREN_RE = re.compile(r"（[^（）]*）|\([^()]*\)")
# 语料里存在 "阿林：（…）周公文，你猜…" 这类**说话人标签前缀**（label）。
# 它是格式伪影，不是称呼；剥离规则写死在此处，出数前后一致。
LABEL_RE = re.compile(r"^\s*[\u4e00-\u9fa5A-Za-z0-9]{1,6}[：:]\s*")
MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP", "MSG")


# --------------------------------------------------------------------------- 词表
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_lexicon(path: str = DEFAULT_LEXICON) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_agent_terms(lex: dict, personas_path: str = DEFAULT_PERSONAS) -> tuple[dict, dict]:
    """按词表 `sources` 规则从 personas.json 派生每个 agent 的称呼形式。

    返回 (terms, info)：terms = {form: tier}；info = {agent_id: [form, ...]}（便于审计）。
    """
    src = lex["sources"]
    with open(personas_path, "r", encoding="utf-8") as f:
        personas = json.load(f)["personas"]
    overrides = {str(k): int(v) for k, v in (src.get("base_tier_overrides") or {}).items()}
    default_tier = int(src.get("base_tier_default", 3))
    suffix_tiers = {str(k): int(v) for k, v in (src.get("suffix_tiers") or {}).items()}
    applied = src.get("suffix_applied_to") or ["base"]

    terms: dict[str, int] = {}
    owners: dict[str, set] = {}
    info: dict[str, list[str]] = {}
    for p in personas:
        aid = p["persona_id"]
        base = str(p["display_name"]).split("·")[-1].strip()
        surname = base[1:] if base[:1] in ("老", "阿") else base[:1]
        forms: dict[str, int] = {base: overrides.get(base, default_tier)}
        stems = []
        if "base" in applied:
            stems.append(base)
        if "surname" in applied:
            stems.append(surname)
        for stem in stems:
            for suf, tier in suffix_tiers.items():
                forms[f"{stem}{suf}"] = tier
        info[aid] = sorted(forms)
        for form, tier in forms.items():
            if not form:
                continue
            owners.setdefault(form, set()).add(aid)
            # 同一形式被多个 agent 派生时保留较低 tier（更疏），并在 label 里记多人共用
            if form in terms and terms[form] != tier:
                terms[form] = min(terms[form], tier)
            else:
                terms[form] = tier
    # 通用称呼（师傅/老板/…）：owner 记为空集 = 不能判指向，任何对象都可能
    for tier_s, toks in (lex.get("generic_tokens") or {}).items():
        for tok in toks:
            terms.setdefault(str(tok), int(tier_s))
            owners.setdefault(str(tok), set())
    return terms, info, owners


# --------------------------------------------------------------------------- 呼语位
def strip_parenthetical(body: str, known_names: set | None = None) -> str:
    """剥离「说话人标签前缀」与括注。

    `known_names` 给出时，只有标签内容确实是某个居民的基名才剥离（避免误删正文开头的
    正常句式，如「早啊，今天……」不会被当成标签）。为 None 时按宽松模式剥离（仅自检用）。
    """
    body = body or ""
    m = LABEL_RE.match(body)
    if m is not None:
        label = m.group(0).strip().rstrip("：:").strip()
        if known_names is None or label in known_names:
            body = body[m.end():]
    return PAREN_RE.sub("", body)


def find_vocative(body: str, terms: dict, voc: dict, longest_first: bool = True) -> tuple[str, int] | None:
    """返回 (最靠前的呼语位称呼, 其 tier)；没有则 None。"""
    if not body:
        return None
    prev_ok = set(voc.get("prev_chars") or [])
    next_ok = set(voc.get("next_chars") or [])
    ordered = sorted(terms, key=len, reverse=bool(longest_first))
    n = len(body)
    best: tuple[int, int, str] | None = None  # (pos, -len, form)
    for form in ordered:
        if not form:
            continue
        start = 0
        while True:
            i = body.find(form, start)
            if i < 0:
                break
            start = i + 1
            prev_c = body[i - 1] if i > 0 else ""
            j = i + len(form)
            next_c = body[j] if j < n else ""
            if prev_c not in prev_ok or next_c not in next_ok:
                continue
            key = (i, -len(form), form)
            if best is None or key < best:
                best = key
            break
    if best is None:
        return None
    return best[2], terms[best[2]]


def any_mention(body: str, terms: dict) -> bool:
    if not body:
        return False
    return any(form in body for form in terms if form)


# --------------------------------------------------------------------------- 读日志
def iter_msgs(log_path: str):
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            t = rec.get("type")
            if t in MSG_TYPES or (isinstance(t, str) and t.startswith("MSG")):
                yield rec


def as_msg(rec: dict) -> dict | None:
    pl = rec.get("payload") or {}
    body = pl.get("body")
    if not isinstance(body, str):
        return None
    speaker = pl.get("author") or pl.get("from")
    addressee = pl.get("to")
    participants = pl.get("participants") or []
    if addressee is None and len(participants) == 2 and speaker in participants:
        addressee = [p for p in participants if p != speaker][0]
    return {
        "seq": rec.get("seq"),
        "round": rec.get("round"),
        "day": pl.get("day"),
        "slot": pl.get("slot"),
        "type": rec.get("type"),
        "thread_id": pl.get("thread_id"),
        "msg_uid": pl.get("msg_uid"),
        "turn_index": pl.get("turn_index"),
        "speaker": speaker,
        "addressee": addressee,
        "body": body,
    }


# --------------------------------------------------------------------------- 统计
def compute(log_path: str, lex_path: str = DEFAULT_LEXICON, personas_path: str = DEFAULT_PERSONAS,
            arm: str | None = None) -> dict:
    lex = load_lexicon(lex_path)
    terms, agent_info, owners = build_agent_terms(lex, personas_path)
    base_names = {p["display_name"].split("·")[-1].strip()
                  for p in json.load(open(personas_path, encoding="utf-8"))["personas"]}
    voc = lex.get("vocative") or {}
    coarse_map = {}
    for label, tiers in (lex.get("coarse_tiers") or {}).items():
        for t in tiers:
            coarse_map[int(t)] = label

    msgs = []
    for rec in iter_msgs(log_path):
        m = as_msg(rec)
        if m is None:
            continue
        text = strip_parenthetical(m["body"], base_names)
        hit = find_vocative(text, terms, voc)
        m["addr_form"] = hit[0] if hit else None
        m["addr_tier"] = hit[1] if hit else None
        m["any_mention"] = any_mention(text, terms)
        # 称呼**指向**分类（口径 v2 新增）：
        #   target_ok    = 就叫的对话对象本人（词表 owner 含 addressee）
        #   target_other = 叫成了别人（错称；如把秀娘叫成"周公文"）
        #   generic      = 通用称呼（师傅/老板/…，无 owner，指向不可判）
        if hit is None:
            m["addr_target"] = None
        else:
            own = owners.get(hit[0]) or set()
            if not own:
                m["addr_target"] = "generic"          # 通用称呼：指向不可判
            elif m["addressee"] is None:
                m["addr_target"] = "unknown_target"   # 公开场合单发，无明确对象
            elif m["addressee"] in own:
                m["addr_target"] = "target_ok"
            elif m["speaker"] in own:
                m["addr_target"] = "self_name"        # 叫成了自己（自称/口误）
            else:
                m["addr_target"] = "other_named"      # 叫成了第三者（错称）
        msgs.append(m)
    msgs.sort(key=lambda x: (x["seq"] if x["seq"] is not None else 0))

    n_msg = len(msgs)
    n_addr = sum(1 for m in msgs if m["addr_form"])
    n_mention = sum(1 for m in msgs if m["any_mention"])

    # --- 1) addr_vocab_per_pair（无向角色对，仅同线程任一方向；MSG 条数 ≥ 3）
    from collections import Counter, defaultdict
    pair_msgs: dict[tuple, list] = defaultdict(list)
    for m in msgs:
        if not m["thread_id"] or not m["speaker"] or not m["addressee"]:
            continue
        key = tuple(sorted((m["speaker"], m["addressee"])))
        pair_msgs[key].append(m)
    vocab_rows = []
    for key, rows in sorted(pair_msgs.items()):
        if len(rows) < 3:
            continue
        forms = {r["addr_form"] for r in rows if r["addr_form"]}
        vocab_rows.append({
            "pair": list(key),
            "n_msgs": len(rows),
            "n_with_addr": sum(1 for r in rows if r["addr_form"]),
            "vocab_size": len(forms),
            "forms": sorted(forms),
        })
    vocab_sizes = [r["vocab_size"] for r in vocab_rows]

    # --- 2) addr_switch_rate（口径 v2：同线程 × 同说话人 × 同对象 的相邻两条之间比）
    # v1 曾用「同线程相邻两条」不分说话人 ⇒ 甲叫乙"巧儿"、乙叫甲"金先生"会被误记成"称呼变了"。
    # 该缺陷在首轮出数（2026-10-30T18:04:42）即被发现并登记，v1 结果原样留存在 v1_preamend/。
    by_dir: dict[tuple, list] = defaultdict(list)
    for m in msgs:
        if m["thread_id"] and m["speaker"] and m["addressee"]:
            by_dir[(m["thread_id"], m["speaker"], m["addressee"])].append(m)
    all_pairs = 0
    scored_pairs = 0
    switches = 0
    switch_examples = []
    for (tid, _spk, _to), rows in sorted(by_dir.items()):
        rows.sort(key=lambda r: (r["seq"] if r["seq"] is not None else 0))
        for a, b in zip(rows, rows[1:]):
            all_pairs += 1
            if a["addr_form"] and b["addr_form"]:
                scored_pairs += 1
                if a["addr_form"] != b["addr_form"]:
                    switches += 1
                    if len(switch_examples) < 20:
                        switch_examples.append({
                            "thread_id": tid, "seq_a": a["seq"], "seq_b": b["seq"],
                            "speaker_a": a["speaker"], "speaker_b": b["speaker"],
                            "form_a": a["addr_form"], "form_b": b["addr_form"],
                            "tier_a": a["addr_tier"], "tier_b": b["addr_tier"],
                        })

    # --- 3) addr_stage_ordinal（有向说话对，≥2 次**指向正确的**称呼）
    dir_rows: dict[tuple, list] = defaultdict(list)
    for m in msgs:
        if m["addr_form"] and m["addr_target"] in ("target_ok", "generic") and m["speaker"] and m["addressee"]:
            dir_rows[(m["speaker"], m["addressee"])].append(m)
    stage_rows = []
    for key, rows in sorted(dir_rows.items()):
        if len(rows) < 2:
            continue
        rows.sort(key=lambda r: (r["seq"] if r["seq"] is not None else 0))
        first, last = rows[0], rows[-1]
        delta = last["addr_tier"] - first["addr_tier"]
        coarse_order = list((lex.get("coarse_tiers") or {}).keys())  # 由疏到近（YAML 里就是这个顺序）
        c_first = coarse_map.get(first["addr_tier"])
        c_last = coarse_map.get(last["addr_tier"])
        if c_first is None or c_last is None or c_first == c_last:
            c_delta = 0 if c_first == c_last else None
        else:
            c_delta = (1 if coarse_order.index(c_last) > coarse_order.index(c_first) else -1)
        stage_rows.append({
            "pair": list(key), "n_addr": len(rows),
            "first_form": first["addr_form"], "first_tier": first["addr_tier"], "first_seq": first["seq"],
            "last_form": last["addr_form"], "last_tier": last["addr_tier"], "last_seq": last["seq"],
            "delta": delta, "coarse_first": c_first, "coarse_last": c_last, "coarse_delta": c_delta,
            "forms_distinct": sorted({r["addr_form"] for r in rows}),
        })
    deltas = [r["delta"] for r in stage_rows]
    coarse_deltas = [r["coarse_delta"] for r in stage_rows if r["coarse_delta"] is not None]

    term_dist = Counter(m["addr_form"] for m in msgs if m["addr_form"])
    tier_dist = Counter(m["addr_tier"] for m in msgs if m["addr_tier"] is not None)
    target_dist = Counter(m["addr_target"] for m in msgs if m["addr_target"])

    def _rows(kind):
        return [{"seq": m["seq"], "thread_id": m["thread_id"], "speaker": m["speaker"],
                 "addressee": m["addressee"], "form": m["addr_form"], "body": m["body"]}
                for m in msgs if m["addr_target"] == kind]

    n_named = sum(target_dist.get(k, 0) for k in ("target_ok", "self_name", "other_named"))
    n_err = target_dist.get("self_name", 0) + target_dist.get("other_named", 0)
    misaddr_rows = _rows("other_named")
    selfname_rows = _rows("self_name")

    out = {
        "tool": "tools/metrics/address_drift.py",
        "tool_sha256": sha256_file(os.path.abspath(__file__)),
        "lexicon_path": os.path.relpath(lex_path, ROOT),
        "lexicon_sha256": sha256_file(lex_path),
        "lexicon_version": lex.get("version"),
        "personas_path": os.path.relpath(personas_path, ROOT),
        "input_log": os.path.abspath(log_path),
        "input_log_sha256": sha256_file(log_path),
        "arm": arm,
        "computed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "n_messages": n_msg,
        "n_messages_with_addr": n_addr,
        "addr_coverage": (n_addr / n_msg) if n_msg else None,
        "addr_any_mention_rate": (n_mention / n_msg) if n_msg else None,
        "metrics": {
            "addr_vocab_per_pair": {
                "denom_pairs": len(vocab_rows),
                "min_msgs_per_pair": 3,
                "mean": statistics.fmean(vocab_sizes) if vocab_sizes else None,
                "median": statistics.median(vocab_sizes) if vocab_sizes else None,
                "max": max(vocab_sizes) if vocab_sizes else None,
                "rows": vocab_rows,
            },
            "addr_switch_rate": {
                "denom_all_pairs": all_pairs,
                "denom_scored_pairs": scored_pairs,
                "n_switch": switches,
                "rate_scored": (switches / scored_pairs) if scored_pairs else None,
                "rate_all": (switches / all_pairs) if all_pairs else None,
                "examples": switch_examples,
            },
            "addr_stage_ordinal": {
                "denom_directed_pairs": len(stage_rows),
                "n_up": sum(1 for d in deltas if d > 0),
                "n_flat": sum(1 for d in deltas if d == 0),
                "n_down": sum(1 for d in deltas if d < 0),
                "mean_delta": statistics.fmean(deltas) if deltas else None,
                "coarse": {
                    "n_up": sum(1 for d in coarse_deltas if d > 0),
                    "n_flat": sum(1 for d in coarse_deltas if d == 0),
                    "n_down": sum(1 for d in coarse_deltas if d < 0),
                    "mean_delta": statistics.fmean(coarse_deltas) if coarse_deltas else None,
                },
                "rows": stage_rows,
            },
        },
        "term_distribution": dict(term_dist.most_common()),
        "form_tiers": {f: terms[f] for f in term_dist},
        "tier_distribution": {str(k): v for k, v in sorted(tier_dist.items())},
        "addr_target_distribution": dict(target_dist),
        "addr_misaddress": {
            "n_named_addr_judgeable": n_named,
            "n_target_ok": target_dist.get("target_ok", 0),
            "n_self_name": target_dist.get("self_name", 0),
            "n_other_named": target_dist.get("other_named", 0),
            "n_addr_err": n_err,
            "addr_error_rate": (n_err / n_named) if n_named else None,
            "misaddress_rate": (target_dist.get("other_named", 0) / n_named) if n_named else None,
            "selfname_rate": (target_dist.get("self_name", 0) / n_named) if n_named else None,
            "n_unknown_target": target_dist.get("unknown_target", 0),
            "n_generic": target_dist.get("generic", 0),
            "rows": misaddr_rows,
            "selfname_rows": selfname_rows,
        },
    }
    return out


# --------------------------------------------------------------------------- 自检
def selftest() -> int:
    lex = load_lexicon()
    terms, info, owners = build_agent_terms(lex)
    voc = lex["vocative"]
    assert terms.get("老石") == 3, ("老石 tier", terms.get("老石"))
    assert terms.get("方老师") == 1, ("方老师 tier", terms.get("方老师"))
    assert terms.get("桂婶") == 2, ("桂婶 tier", terms.get("桂婶"))
    assert terms.get("石叔") == 2, ("石叔 tier", terms.get("石叔"))
    assert terms.get("石师傅") == 1, ("石师傅 tier", terms.get("石师傅"))
    assert "老伙计" in terms and terms["老伙计"] == 4
    assert len(info["P002"]) >= 5, info["P002"]

    cases = [
        ("石叔，这木头真硬。", "石叔", 2),                  # 呼语位
        ("哎，石叔你来了。", "石叔", 2),                    # 前有「哎，」
        ("这木头真硬。石叔。", "石叔", 2),                  # 句首 + 句末
        ("石叔家的豆腐好。", None, None),                   # 提及而非称呼 ⇒ 不算
        ("（老石在旁边忙着）这活急不得。", None, None),       # 括注剥离后无称呼
        ("方老师，这题我不会。", "方老师", 1),               # 最长优先（不吃成「老师」）
        ("师傅，借个火。", "师傅", 1),                      # 通用 token
        ("这炉桃酥我总烤不出你家的脆劲儿。", None, None),    # 「你家」非呼语位
        ("你，别走。", "你", 0),                            # tier0 指代
        ("我跟你说，别走。", None, None),                   # 「你」不在呼语位
    ]
    bad = 0
    for body, want_form, want_tier in cases:
        text = strip_parenthetical(body)
        hit = find_vocative(text, terms, voc)
        got = (hit[0], hit[1]) if hit else (None, None)
        ok = got == (want_form, want_tier)
        if not ok:
            bad += 1
            print(f"[SELFTEST FAIL] {body!r}: want=({want_form},{want_tier}) got={got}")
        else:
            print(f"[ok] {body!r} -> {got}")

    # 合成日志端到端：线程里 4 条 DM，称呼 石叔 -> 石叔 -> 老石 -> 老石
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        bodies = ["石叔，早。", "秀娘，早。", "石叔，豆腐好了。", "秀娘，来了。", "老石，走了。", "秀娘，走了。"]
        speakers = ["P004", "P002", "P004", "P002", "P004", "P002"]
        tos = ["P002", "P004", "P002", "P004", "P002", "P004"]
        for i, (b, sp, to) in enumerate(zip(bodies, speakers, tos)):
            rec = {"seq": i + 1, "round": 0, "type": "MSG_DM",
                   "payload": {"body": b, "author": sp, "from": sp, "to": to,
                               "participants": [sp, to], "thread_id": "TH-P004-P002-0",
                               "turn_index": i}}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        tmp = f.name
    res = compute(tmp, arm="SELFTEST")
    os.unlink(tmp)
    exp_vocab = 3  # {石叔, 老石, 秀娘}（无向对：双方对彼此的称呼都计入）
    got_vocab = res["metrics"]["addr_vocab_per_pair"]["rows"][0]["vocab_size"]
    exp_sw = 1     # 第 3->5 条之间 石叔->老石 视为变一次（相邻对里两端都有称呼且不同的只有 i=(2,3)? 见下）
    got_sw = res["metrics"]["addr_switch_rate"]
    print("[selftest] synthetic vocab:", got_vocab, "expect", exp_vocab)
    print("[selftest] synthetic switch:", got_sw)
    print("[selftest] synthetic stage:", res["metrics"]["addr_stage_ordinal"])
    if got_vocab != exp_vocab:
        bad += 1
        print("[SELFTEST FAIL] synthetic vocab")
    # 相邻对序列（按 turn_index）：[石叔, 秀娘, 石叔, 秀娘, 老石, 秀娘]
    # 两端都有称呼的相邻对 = 5 对；其中形式不同的 = (石叔,秀娘)x2 + (秀娘,老石)x1 + ... 全部不同 ⇒ 5
    # 口径 v2：只在同有向关系的相邻两条之间比。
    #   P004→P002：石叔(1) 石叔(3) 老石(5) ⇒ 2 对，1 次变化
    #   P002→P004：秀娘(2) 秀娘(4) 秀娘(6) ⇒ 2 对，0 次变化
    exp_scored = 4
    exp_switch = 1
    if got_sw["denom_scored_pairs"] != exp_scored or got_sw["n_switch"] != exp_switch:
        bad += 1
        print(f"[SELFTEST FAIL] synthetic switch: want {exp_switch}/{exp_scored} got "
              f"{got_sw['n_switch']}/{got_sw['denom_scored_pairs']}")
    st = res["metrics"]["addr_stage_ordinal"]
    if st["denom_directed_pairs"] != 2:
        bad += 1
        print(f"[SELFTEST FAIL] synthetic stage denom: {st['denom_directed_pairs']}")
    # 错称端到端：P004 把 P002 叫成 P012 的「桂婶」⇒ 必须落 target_other
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        rec = {"seq": 1, "round": 0, "type": "MSG_DM",
               "payload": {"body": "桂婶你来了。", "author": "P004", "from": "P004", "to": "P002",
                           "participants": ["P004", "P002"], "thread_id": "TH-P004-P002-0", "turn_index": 0}}
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        tmp2 = f.name
    r2 = compute(tmp2, arm="SELFTEST-MISADDR")
    os.unlink(tmp2)
    got_mis = r2["addr_misaddress"]
    print("[selftest] other_named:", got_mis["n_other_named"], "/", got_mis["n_named_addr_judgeable"],
          got_mis["rows"][0]["form"] if got_mis["rows"] else None)
    if got_mis["n_other_named"] != 1 or got_mis["n_named_addr_judgeable"] != 1:
        bad += 1
        print("[SELFTEST FAIL] other_named classification")
    # 自称端到端：P002 对 P004 说「老石，早。」= 叫成了自己 ⇒ self_name
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        rec = {"seq": 1, "round": 0, "type": "MSG_DM",
               "payload": {"body": "老石，早。", "author": "P002", "from": "P002", "to": "P004",
                           "participants": ["P002", "P004"], "thread_id": "TH-P004-P002-0", "turn_index": 0}}
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        tmp3 = f.name
    r3 = compute(tmp3, arm="SELFTEST-SELFNAME")
    os.unlink(tmp3)
    got_self = r3["addr_misaddress"]
    print("[selftest] self_name:", got_self["n_self_name"], "other:", got_self["n_other_named"])
    if got_self["n_self_name"] != 1 or got_self["n_other_named"] != 0:
        bad += 1
        print("[SELFTEST FAIL] self_name classification")
    print(f"[selftest] {'FAIL' if bad else 'PASS'} (failures={bad})")
    return 3 if bad else 0


# --------------------------------------------------------------------------- 报告片段
def to_markdown(res: dict) -> str:
    m = res["metrics"]
    v = m["addr_vocab_per_pair"]
    s = m["addr_switch_rate"]
    o = m["addr_stage_ordinal"]
    lines = []
    lines.append(f"# address_drift · arm={res['arm']} · {res['computed_at']}")
    lines.append("")
    lines.append(f"- 输入日志：`{res['input_log']}`")
    lines.append(f"- 日志 sha256：`{res['input_log_sha256']}`")
    lines.append(f"- 词表：`{res['lexicon_path']}` sha256 `{res['lexicon_sha256']}`（{res['lexicon_version']}）")
    lines.append(f"- 尺子 sha256：`{res['tool_sha256']}`")
    lines.append("")
    lines.append("## 覆盖（先读这个，否则下面的分母会被误读）")
    lines.append("")
    lines.append("| 项 | 值 | 分母 |")
    lines.append("|---|---|---|")
    lines.append(f"| MSG 总数 | {res['n_messages']} | — |")
    lines.append(f"| 呼语位识别出称呼的 MSG | {res['n_messages_with_addr']} | {res['n_messages']} |")
    cov = res["addr_coverage"]
    lines.append(f"| `addr_coverage` | {('%.4f%%' % (cov * 100)) if cov is not None else 'NA'} | {res['n_messages']} |")
    am = res["addr_any_mention_rate"]
    lines.append(f"| `addr_any_mention_rate`（描述量，含提及） | {('%.4f%%' % (am * 100)) if am is not None else 'NA'} | {res['n_messages']} |")
    lines.append("")
    lines.append("## 1. addr_vocab_per_pair")
    lines.append("")
    lines.append(f"分母（MSG ≥ 3 的角色对）= **{v['denom_pairs']}**；mean={v['mean']}；median={v['median']}；max={v['max']}")
    lines.append("")
    if v["rows"]:
        lines.append("| 角色对 | MSG 数 | 带称呼条数 | 称呼种类 | 形式 |")
        lines.append("|---|---|---|---|---|")
        for r in v["rows"]:
            lines.append(f"| {r['pair'][0]}×{r['pair'][1]} | {r['n_msgs']} | {r['n_with_addr']} | {r['vocab_size']} | {', '.join(r['forms']) or '—'} |")
    else:
        lines.append("（无满足分母条件的角色对）")
    lines.append("")
    lines.append("## 2. addr_switch_rate")
    lines.append("")
    rs = s["rate_scored"]
    ra = s["rate_all"]
    lines.append(f"- 分子（称呼发生变化的相邻对）= **{s['n_switch']}**")
    lines.append(f"- 分母 A（两端都识别出称呼）= **{s['denom_scored_pairs']}** ⇒ `rate_scored` = "
                 f"{('%.4f%%' % (rs * 100)) if rs is not None else 'NA'}")
    lines.append(f"- 分母 B（全部相邻对）= **{s['denom_all_pairs']}** ⇒ `rate_all` = "
                 f"{('%.4f%%' % (ra * 100)) if ra is not None else 'NA'}")
    if s["examples"]:
        lines.append("")
        lines.append("| thread | seq_a→seq_b | 说话人 | 称呼变化 |")
        lines.append("|---|---|---|---|")
        for e in s["examples"]:
            lines.append(f"| {e['thread_id']} | {e['seq_a']}→{e['seq_b']} | {e['speaker_a']}→{e['speaker_b']} | {e['form_a']}→{e['form_b']} |")
    lines.append("")
    lines.append("## 3. addr_stage_ordinal")
    lines.append("")
    lines.append(f"分母（有向说话对，称呼 ≥ 2 次）= **{o['denom_directed_pairs']}**；"
                 f"升 {o['n_up']} / 平 {o['n_flat']} / 降 {o['n_down']}；mean_delta={o['mean_delta']}")
    lines.append("")
    lines.append(f"粗粒度敏感性（粗疏/乡亲/近昵）：升 {o['coarse']['n_up']} / 平 {o['coarse']['n_flat']} / "
                 f"降 {o['coarse']['n_down']}；mean_delta={o['coarse']['mean_delta']}")
    if o["rows"]:
        lines.append("")
        lines.append("| 说话对 | 称呼次数 | 首次 | 末次 | delta | 用过的形式 |")
        lines.append("|---|---|---|---|---|---|")
        for r in o["rows"]:
            lines.append(f"| {r['pair'][0]}→{r['pair'][1]} | {r['n_addr']} | {r['first_form']}(tier{r['first_tier']}) | "
                         f"{r['last_form']}(tier{r['last_tier']}) | {r['delta']:+d} | {', '.join(r['forms_distinct'])} |")
    lines.append("")
    mis = res["addr_misaddress"]
    lines.append("## 3b. 称呼指向（自称 / 错称；描述量）")
    lines.append("")
    lines.append(f"- 分母（可判指向的具名称呼，= target_ok + self_name + other_named）= **{mis['n_named_addr_judgeable']}**")
    lines.append(f"- 叫对（target_ok）= **{mis['n_target_ok']}**；叫成自己（self_name）= **{mis['n_self_name']}**；"
                 f"叫成第三者（other_named）= **{mis['n_other_named']}**；指向不可判（公开单发 unknown_target）= "
                 f"{mis['n_unknown_target']}；通用称呼（generic）= {mis['n_generic']}")
    lines.append(f"- `addr_error_rate`（自称+错称 / 分母）= "
                 f"{('%.4f%%' % (mis['addr_error_rate'] * 100)) if mis['addr_error_rate'] is not None else 'NA'}"
                 f"；其中 `addr_misaddress_rate` = "
                 f"{('%.4f%%' % (mis['misaddress_rate'] * 100)) if mis['misaddress_rate'] is not None else 'NA'}"
                 f"，`addr_selfname_rate` = "
                 f"{('%.4f%%' % (mis['selfname_rate'] * 100)) if mis['selfname_rate'] is not None else 'NA'}")
    for label, rows in (("叫成第三者（other_named）", mis["rows"]), ("叫成自己（self_name）", mis["selfname_rows"])):
        if not rows:
            continue
        lines.append("")
        lines.append(f"**{label}**")
        lines.append("")
        lines.append("| seq | thread | 说话人→对象 | 叫成 | 原文（截断 60 字） |")
        lines.append("|---|---|---|---|---|")
        for r in rows:
            lines.append(f"| {r['seq']} | {r['thread_id']} | {r['speaker']}→{r['addressee']} | {r['form']} | {r['body'][:60]} |")
    lines.append("")
    lines.append("## 称呼形式分布（描述量）")
    lines.append("")
    if res["term_distribution"]:
        lines.append("| 形式 | tier | 次数 |")
        lines.append("|---|---|---|")
        for form, cnt in res["term_distribution"].items():
            lines.append(f"| {form} | tier{res.get('form_tiers', {}).get(form)} | {cnt} |")
    else:
        lines.append("（本日志无任何呼语位称呼）")
    lines.append("")
    lines.append(f"tier 分布：{res['tier_distribution']}")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="D10 C-A 称呼与关系演化尺子（只读）")
    ap.add_argument("--log")
    ap.add_argument("--arm", default=None)
    ap.add_argument("--lexicon", default=DEFAULT_LEXICON)
    ap.add_argument("--personas", default=DEFAULT_PERSONAS)
    ap.add_argument("--out-json")
    ap.add_argument("--out-md")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()
    if not a.log:
        print("--log required", file=sys.stderr)
        return 2
    log = a.log
    if os.path.isdir(log):
        log = os.path.join(log, "run.jsonl")
    if not os.path.isfile(log):
        print(f"input not usable: {log}", file=sys.stderr)
        return 2
    if yaml is None:
        print("PyYAML missing", file=sys.stderr)
        return 2

    res = compute(log, a.lexicon, a.personas, a.arm)
    md = to_markdown(res)
    if a.out_json:
        os.makedirs(os.path.dirname(os.path.abspath(a.out_json)), exist_ok=True)
        with open(a.out_json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1, sort_keys=True)
    if a.out_md:
        os.makedirs(os.path.dirname(os.path.abspath(a.out_md)), exist_ok=True)
        with open(a.out_md, "w", encoding="utf-8") as f:
            f.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
