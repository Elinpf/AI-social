#!/usr/bin/env python3
"""F-4b「修复时滞」离线复算器（零跑批、零 LLM）。

口径来源（**写死，不发明**）：
  * 张力/修复判定 = `tools/d5/dialogue_metrics.py` 的词表层（R4-life-texture.md:45 的 F-4 行）：
      张力 = 相邻两句极性相反 **或** 当句极性为负（两个来源的**并集**）；
      修复 = 其后 8 条**同线程**内首条 body 命中 `tools/d5/repair_lexicon.txt`；
      线程 = `tools/d5/dialogue_metrics.py` 的 `mixed_key`（thread_id 优先，其次 day+channel+对端/场所）。
  * F-4b = 修复时滞 Δ = 修复句在线程内的下标 − 张力句在线程内的下标（单位：条消息）。
    仅对**已修复**事件有观测值；未修复且窗口被线程尾部截断的事件记 **右删失**，不进时滞均值/分位数。

第二个口径（`--caliber mech`）：以 `payload.dialogue_repair.trigger_seqs`（R13 机制侧可审计配对）
为张力侧、以同线程其后 8 条内的 repair 词为修复侧。**覆盖率极低**（117 份语料仅 3 份带该字段），
只作敏感性对照，不作主读数。

用法：
    python3 tools/f4/f4b_repair_latency.py --root v2/evidence --caliber both

只读历史语料，不写 code/、不改任何冻结区。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
D5 = REPO / "tools" / "d5"
DEFAULT_EMOTION = D5 / "emotion_lexicon.txt"
DEFAULT_REPAIR = D5 / "repair_lexicon.txt"
MSG_TYPES = ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC")
WINDOW = 8

ARM_RX = re.compile(r"(^|[^a-z])(on|off|treat|treat_on|ctrl|control|base)([^a-z]|$)", re.I)


# ---------------------------------------------------------------- 基础工具
def sha8(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:8]


def r6(x):
    return None if x is None else round(float(x), 6)


def pct(vals, q):
    if not vals:
        return None
    s = sorted(vals)
    if len(s) == 1:
        return r6(s[0])
    pos = (len(s) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(s) - 1)
    return r6(s[lo] + (s[hi] - s[lo]) * (pos - lo))


def load_lines(path) -> list:
    p = Path(path)
    if not p.exists():
        return []
    return [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


def load_emotion(path) -> dict:
    emo = {}
    for ln in load_lines(path):
        parts = ln.split()
        if len(parts) >= 2:
            try:
                emo[" ".join(parts[1:])] = int(parts[0])
            except ValueError:
                continue
    return emo


# ---------------------------------------------------------------- 读日志（镜像 dialogue_metrics.extract_messages）
def read_msgs(log_path):
    msgs = []
    with open(log_path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or '"MSG_' not in ln:
                continue
            try:
                r = json.loads(ln)
            except Exception:
                continue
            t = r.get("type")
            if t not in MSG_TYPES:
                continue
            p = r.get("payload") or {}
            if not isinstance(p, dict):
                p = {}
            msgs.append({
                "seq": r.get("seq"),
                "round": r.get("round"),
                "channel": {"MSG_DM": "dm", "MSG_GROUP": "group", "MSG_PUBLIC": "public"}[t],
                "event_type": t,
                "from": p.get("from") or r.get("actor"),
                "to": p.get("to"),
                "body": p.get("body") or p.get("text") or "",
                "thread_id": p.get("thread_id"),
                "day": p.get("day"),
                "place": p.get("place"),
                "dialogue_repair": p.get("dialogue_repair"),
            })
    msgs.sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                             m["seq"] if m["seq"] is not None else -1))
    return msgs


def mixed_key(m) -> str:
    """镜像 tools/d5/dialogue_metrics.py::mixed_key（R4/`tools/d5` 线程口径）。"""
    if m.get("thread_id"):
        return "m:T|%s" % m["thread_id"]
    if m["channel"] == "dm":
        k = "-".join(sorted({str(m["from"]), str(m["to"])}))
    elif m["channel"] == "public":
        k = "-"
    else:
        k = str(m.get("place") or "-")
    return "m:%s|%s|%s" % (m["day"], m["channel"], k)


def build_threads(msgs):
    th = defaultdict(list)
    for m in msgs:
        th[mixed_key(m)].append(m)
    for k in th:
        th[k].sort(key=lambda m: (m["round"] if m["round"] is not None else -1,
                                  m["seq"] if m["seq"] is not None else -1))
    return th


# ---------------------------------------------------------------- 事件提取
def events_wordcaliber(threads, emo, repair, window=WINDOW):
    """口径 A：R4/tools-d5 词表层（极性并集定张力）。"""
    def polarity(body):
        pos = sum(1 for w, p in emo.items() if p > 0 and w in body)
        neg = sum(1 for w, p in emo.items() if p < 0 and w in body)
        return 1 if pos > neg else (-1 if neg > pos else 0)

    rows = []
    for key in sorted(threads):
        th = threads[key]
        for i in range(1, len(th)):
            p_prev, p_cur = polarity(th[i - 1]["body"]), polarity(th[i]["body"])
            conflict = (p_prev * p_cur < 0) or (p_cur < 0)
            if not conflict:
                continue
            avail_full = len(th) - i - 1                 # 该事件后面还剩多少条（线程内）
            avail = avail_full if window <= 0 else min(window, avail_full)
            end = len(th) if window <= 0 else min(i + 1 + window, len(th))
            lag = None
            for j in range(i + 1, end):
                if any(w in th[j]["body"] for w in repair):
                    lag = j - i
                    break
            rows.append({
                "caliber": "word",
                "thread": key,
                "tension_pos": i,
                "trigger_seq": th[i]["seq"],
                "tension_kind": "adjacent_flip" if p_prev * p_cur < 0 else "cur_negative",
                "polarity_prev": p_prev,
                "polarity_cur": p_cur,
                "window_available": avail,
                "repaired": lag is not None,
                "lag": lag,
                "censored": bool(window > 0 and lag is None and avail < window),
            })
    return rows


def events_mechcaliber(msgs, threads, repair, window=WINDOW):
    """口径 B：R13 机制侧可审计配对（dialogue_repair.trigger_seqs 定张力）。

    张力单位 = 一条可审计配对 (thread_id, trigger_seq)；同一配对只计一次。
    """
    # thread_id -> seq -> 线程内下标
    idx = {}
    for key, th in threads.items():
        if not key.startswith("m:T|"):
            continue
        tid = key[4:]
        idx[tid] = {m["seq"]: i for i, m in enumerate(th)}

    seen = {}
    for m in msgs:
        ra = m.get("dialogue_repair")
        if not isinstance(ra, dict):
            continue
        tid = m.get("thread_id")
        if tid is None or tid not in idx:
            continue
        for tseq in (ra.get("trigger_seqs") or []):
            seen.setdefault((tid, tseq), m["seq"])

    rows = []
    for (tid, tseq), _paired_seq in sorted(seen.items()):
        th = threads["m:T|" + tid]
        i = idx[tid].get(tseq)
        if i is None:
            continue
        avail_full = len(th) - i - 1
        avail = avail_full if window <= 0 else min(window, avail_full)
        end = len(th) if window <= 0 else min(i + 1 + window, len(th))
        lag = None
        for j in range(i + 1, end):
            if any(w in th[j]["body"] for w in repair):
                lag = j - i
                break
        rows.append({
            "caliber": "mech",
            "thread": "m:T|" + tid,
            "tension_pos": i,
            "trigger_seq": tseq,
            "tension_kind": "dialogue_repair.trigger_seqs",
            "window_available": avail,
            "repaired": lag is not None,
            "lag": lag,
            "censored": bool(window > 0 and lag is None and avail < window),
        })
    return rows


# ---------------------------------------------------------------- 汇总
def summarize(rows, _with_strata=True):
    T = len(rows)
    rep = [r for r in rows if r["repaired"]]
    cen = [r for r in rows if r["censored"]]
    lags = [r["lag"] for r in rep]
    unc = T - len(cen)
    return {
        "tension_events": T,
        "repaired_events": len(rep),
        "censored_events": len(cen),
        "uncensored_events": unc,
        "closed_loop_rate_raw": r6(len(rep) / T) if T else None,
        "closed_loop_rate_uncensored": r6(len(rep) / unc) if unc else None,
        "denominator_is_zero": T == 0,
        "lag": {
            "n": len(lags),
            "mean": r6(sum(lags) / len(lags)) if lags else None,
            "median": pct(lags, 0.5),
            "p50": pct(lags, 0.5),
            "p90": pct(lags, 0.9),
            "min": min(lags) if lags else None,
            "max": max(lags) if lags else None,
            "hist": {str(k): v for k, v in sorted(Counter(lags).items())},
        },
        "lag_including_censored_as_window_end": {
            "n": T,
            "mean": r6(sum([r["lag"] if r["repaired"] else r["window_available"] for r in rows]) / T) if T else None,
            "note": "敏感性下界：把删失事件当「到窗口尾才未修复」；仅作对照，不作主读数",
        },
        "by_tension_kind": dict(Counter(r["tension_kind"] for r in rows)),
        "window_available_hist": {str(k): v for k, v in sorted(Counter(r["window_available"] for r in rows).items())},
        "max_lag_obtainable": max([r["window_available"] for r in rows], default=None),
        "strata_by_window_available": ({
            "0": summarize([r for r in rows if r["window_available"] == 0], False),
            "1-2": summarize([r for r in rows if 1 <= r["window_available"] <= 2], False),
            "3-7": summarize([r for r in rows if 3 <= r["window_available"] <= 7], False),
            ">=8": summarize([r for r in rows if r["window_available"] >= 8], False),
        } if _with_strata else {}),
    }


def arm_guess(name: str) -> str:
    low = name.lower()
    for tag in ("_off_", "-off-", "_off", "-off", "off_"):
        if tag in low:
            return "off"
    for tag in ("_on_", "-on-", "_on", "-on", "on_"):
        if tag in low:
            return "on"
    if "treat" in low:
        return "treat"
    return "unk"


def find_logs(root):
    root = Path(root)
    if root.is_file():
        return [root]
    return sorted(root.rglob("run.jsonl"))


def meta_info(log: Path):
    """从同目录 meta.json 取 code_sha / provider（缺则 None，不猜）。"""
    mj = log.parent / "meta.json"
    if not mj.exists():
        return None, None
    try:
        d = json.loads(mj.read_text(encoding="utf-8"))
    except Exception:
        return None, None
    sha = None
    for k in ("code_sha", "code_sha_end", "code_sha_start"):
        v = d.get(k)
        if isinstance(v, str) and v:
            sha = v[:12]
            break
    prov = None
    for k in ("provider", "llm_provider", "model", "llm_model"):
        v = d.get(k)
        if isinstance(v, str) and v:
            prov = v
            break
    return sha, prov


def batch_of(log: Path, root: Path):
    rel = log.relative_to(root)
    return rel.parts[0] if len(rel.parts) > 1 else log.parent.name


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="F-4b 修复时滞离线复算器（零成本）")
    ap.add_argument("--root", default="v2/evidence", help="run.jsonl 搜索根目录（或单个 run.jsonl 文件）")
    ap.add_argument("--caliber", default="both", choices=["word", "mech", "both"])
    ap.add_argument("--window", type=int, default=WINDOW, help="修复窗口（条），默认 8，与 F-4 同口径")
    ap.add_argument("--emotion", default=str(DEFAULT_EMOTION))
    ap.add_argument("--repair", default=str(DEFAULT_REPAIR))
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--no-events", action="store_true", help="JSON 里不输出逐事件明细")
    ap.add_argument("--live-window", type=int, default=900,
                    help="mtime 在 N 秒内的 run.jsonl 视为「正在写批」（未落定），默认排除；0 = 不排除")
    ap.add_argument("--keep-invalid", action="store_true",
                    help="保留路径含 INVALID/ABORTED 的跑批（默认排除：这些批在仓库里已被判定无效）")
    ap.add_argument("--manifest-out", default=None, help="输出语料清单（relpath + sha8）供钉版复算")
    ap.add_argument("--pin", default=None,
                    help="钉版清单（--manifest-out 产物）：只读清单内文件并校验 sha8；"
                         "命中后语料与分母完全确定，不依赖时钟/在写批")
    args = ap.parse_args(argv)

    root = Path(args.root)
    if not root.is_absolute():
        root = (Path.cwd() / root).resolve()
    logs = find_logs(root)
    pin_map = None
    if args.pin:
        pin_map = {}
        for e in json.loads(Path(args.pin).read_text(encoding="utf-8")):
            pin_map[e["log"]] = e["sha8"]
        if not pin_map:
            print(f"[FAIL] 钉版清单为空: {args.pin}", file=sys.stderr)
            return 2
        # 只保留清单内文件，顺序按清单
        keep = []
        missing = []
        for lg in logs:
            if rel(lg, root) in pin_map:
                keep.append(lg)
        for e in pin_map:
            if not (root / e).exists():
                missing.append(e)
        logs = keep
        if missing:
            print(f"[FAIL] 钉版清单里 {len(missing)} 份文件已不存在: {missing[:5]}", file=sys.stderr)
            return 2
    if not logs:
        print(f"[FAIL] 未找到 run.jsonl: {root}", file=sys.stderr)
        return 2

    emo = load_emotion(args.emotion)
    repair = load_lines(args.repair)
    if not repair:
        print(f"[FAIL] 修复词表为空: {args.repair}", file=sys.stderr)
        return 2

    cwd = Path.cwd()
    per_run, all_rows, skipped = [], defaultdict(list), []
    excluded = {"live": [], "invalid": []}
    import time as _time
    now = _time.time()
    manifest = []
    for log in logs:
        relp = rel(log, root)
        if pin_map is not None:
            pass  # 钉版：语料由清单决定，不再做时钟/命名过滤
        elif not args.keep_invalid and re.search(r"INVALID|ABORTED", relp, re.I):
            excluded["invalid"].append(relp)
            continue
        elif args.live_window > 0:
            try:
                age = now - log.stat().st_mtime
            except OSError:
                age = None
            if age is not None and age < args.live_window:
                excluded["live"].append({"log": relp, "mtime_age_s": round(age)})
                continue
        _s8 = sha8(log)
        if pin_map is not None and pin_map.get(relp) != _s8:
            print(f"[FAIL] 钉版校验失败: {relp} 清单 sha8={pin_map.get(relp)} 实际={_s8}", file=sys.stderr)
            return 3
        manifest.append({"log": relp, "sha8": _s8})
        try:
            msgs = read_msgs(log)
        except (FileNotFoundError, PermissionError) as exc:
            # 语料目录可能正被其他成员写批：只读跳过并如实登记，不猜、不补数
            skipped.append({"log": rel(log, root), "error": type(exc).__name__})
            continue
        threads = build_threads(msgs)
        _sha, _prov = meta_info(log)
        rec = {"log": rel(log, root), "log_sha8": sha8(log),
               "meta_code_sha12": _sha, "provider": _prov,
               "batch": batch_of(log, root), "arm": arm_guess(str(log.parent)),
               "n_messages": len(msgs), "n_threads": len(threads)}
        for cal, fn in (("word", lambda: events_wordcaliber(threads, emo, repair, args.window)),
                        ("mech", lambda: events_mechcaliber(msgs, threads, repair, args.window))):
            if args.caliber not in (cal, "both"):
                continue
            rows = fn()
            for r in rows:
                r["log"] = rec["log"]
                r["batch"] = rec["batch"]
                r["arm"] = rec["arm"]
                r["log_sha8"] = rec["log_sha8"]
            for r in rows:
                r["provider"] = _prov
            all_rows[cal].extend(rows)
            rec[cal] = {"tension_events": len(rows),
                        "repaired_events": sum(1 for r in rows if r["repaired"])}
        per_run.append(rec)

    out = {
        "meta": {
            "generator": "tools/f4/f4b_repair_latency.py",
            "root": rel(root, cwd),
            "n_run_jsonl_found": len(logs),
            "n_run_jsonl_read": len(per_run),
            "n_run_jsonl_excluded_invalid": len(excluded["invalid"]),
            "n_run_jsonl_excluded_live": len(excluded["live"]),
            "excluded": excluded,
            "skipped": skipped,
            "corpus_fingerprint": hashlib.sha256(
                "\n".join(sorted(f"{m['log']} {m['sha8']}" for m in manifest)).encode()
            ).hexdigest()[:16],
            "window_msgs": args.window,
            "pin_manifest": rel(args.pin, cwd) if args.pin else None,
            "emotion_lexicon": {"path": rel(args.emotion, REPO) if Path(args.emotion).exists() else args.emotion,
                                "sha8": sha8(args.emotion) if Path(args.emotion).exists() else None,
                                "n_words": len(emo)},
            "repair_lexicon": {"path": rel(args.repair, REPO) if Path(args.repair).exists() else args.repair,
                               "sha8": sha8(args.repair) if Path(args.repair).exists() else None,
                               "n_words": len(repair)},
            "caliber_note": {
                "word": ("R4-life-texture.md:45 / tools/d5 词表层：张力=相邻极性相反 或 当句极性为负（并集）；"
                         "修复=其后 8 条同线程内首条命中 repair_lexicon；线程=mixed_key"),
                "mech": ("R13 机制口径：张力=payload.dialogue_repair.trigger_seqs 可审计配对；"
                         "修复同上（词表）；两口径不可混算，也不可跨口径比较比率"),
                "lag": "Δ = 修复句线程下标 − 张力句线程下标（条消息）；只对已修复事件有观测",
            },
        },
        "runs": per_run,
    }

    for cal in all_rows:
        rows = all_rows[cal]
        out[cal] = {
            "overall": summarize(rows),
            "by_batch": {b: summarize([r for r in rows if r["batch"] == b])
                         for b in sorted({r["batch"] for r in rows})},
            "by_arm": {a: summarize([r for r in rows if r["arm"] == a])
                       for a in sorted({r["arm"] for r in rows})},
            "by_provider": {str(p): summarize([r for r in rows if str(r["provider"]) == str(p)])
                            for p in sorted({r["provider"] for r in rows}, key=lambda x: str(x))},
        }
        if not args.no_events:
            out[cal]["events"] = rows

    if args.manifest_out:
        mp = Path(args.manifest_out)
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[OK] manifest -> {rel(mp, cwd)}")

    if args.json_out:
        p = Path(args.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=False), encoding="utf-8")
        print(f"[OK] json -> {rel(p, cwd)}")

    # ---- 文本摘要
    print(f"# F-4b 修复时滞 · 离线复算（root={rel(root, cwd)}, window={args.window}）")
    print(f"  语料: 发现 {len(logs)} 份 → 实读 {len(per_run)} 份；"
          f"排除 INVALID/ABORTED {len(excluded['invalid'])} 份、"
          f"排除「{args.live_window}s 内仍在写」{len(excluded['live'])} 份、读失败 {len(skipped)} 份")
    print(f"  语料指纹(corpus_fingerprint)={out['meta']['corpus_fingerprint']}"
          + (f"  [钉版: {rel(args.pin, cwd)}]" if args.pin else ""))
    if skipped:
        print(f"  [WARN] 读不到（可能正被写批）：{skipped}")
    for cal in ("word", "mech"):
        if cal not in out:
            continue
        o = out[cal]["overall"]
        name = "口径A word(R4/tools-d5 极性别集)" if cal == "word" else "口径B mech(R13 dialogue_repair)"
        print(f"\n== {name} ==")
        print(f"  张力事件={o['tension_events']} 有修复={o['repaired_events']} "
              f"右删失={o['censored_events']} 未删失={o['uncensored_events']}")
        print(f"  闭环率(原始)={o['closed_loop_rate_raw']} 闭环率(未删失分母)={o['closed_loop_rate_uncensored']}")
        lag = o["lag"]
        print(f"  时滞(仅已修复 n={lag['n']}): mean={lag['mean']} median={lag['median']} "
              f"p90={lag['p90']} min={lag['min']} max={lag['max']}")
        print(f"  时滞直方图: {lag['hist']}")
        print(f"  敏感性(删失按窗口尾计 n={o['lag_including_censored_as_window_end']['n']}): "
              f"mean={o['lag_including_censored_as_window_end']['mean']}")
        print(f"  张力来源分布: {o['by_tension_kind']}")
        print(f"  窗口可观测条数直方图: {o['window_available_hist']}  最大可得时滞={o['max_lag_obtainable']}")
        for k, v in o["strata_by_window_available"].items():
            print(f"    分层 window_available={k}: T={v['tension_events']} R={v['repaired_events']} "
                  f"C={v['censored_events']} median={v['lag']['median']}")
        print(f"  按 provider: " + "; ".join(
            f"{p}: T={v['tension_events']}/R={v['repaired_events']}/C={v['censored_events']}/"
            f"median={v['lag']['median']}" for p, v in out[cal]["by_provider"].items()))
        print(f"  按臂: " + "; ".join(
            f"{a}: T={v['tension_events']}/R={v['repaired_events']}/C={v['censored_events']}/"
            f"median={v['lag']['median']}" for a, v in out[cal]["by_arm"].items()))
        nb = [b for b, v in out[cal]["by_batch"].items() if v["tension_events"]]
        print(f"  有事件的批次 {len(nb)} 个（全量批次 {len(out[cal]['by_batch'])} 个）")
    return 0


def rel(p, base) -> str:
    try:
        return str(Path(p).resolve().relative_to(Path(base).resolve()))
    except Exception:
        return str(p)


if __name__ == "__main__":
    raise SystemExit(main())
