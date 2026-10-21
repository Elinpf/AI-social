#!/usr/bin/env python3
"""g1_metrics_crosscheck.py — R15 的「独立实现」G-1 / G-1b 复算器（互证用，零 LLM、只读）

# 口径依据
- 预注册：`experiments/gossip-third-party/DESIGN-preregistration.md`（PREREG）§1.4 / §3，行号见下
- 冻结参数：`<team-workspace>/recon/r15-guards-frozen.md` §6（比较臂 b0、per-message 分母、
  G-1 分子 = 主干名命中 − 发送者 − participants（先 PID→主干名映射）、G-1b 用 upper 口径、
  噪声带 n=510 精确值）

# 为什么保留两份实现（互证，不是冗余）
`experiments/gossip-third-party/g_metrics.py:232-234` 写的是 `nm not in parts`，而 `parts` 是
**persona_id**（`P002`）、`nm` 是**主干名**（`老石`）⇒ 该比较恒真，PREREG:72 的「− participants」
**从未生效**。在 b0 上它给出 G-1 = 301/510 = 59.02%（= 「DM 里喊一声对方名字」的比率），
不是预注册定义的 G-1。本仓库放两份**各自独立编写**的修正实现，用于互证读数不是单实现的偶然产物。

# 与权威版（`g1_metrics_fixed.py`）的差异（诚实披露）
算法本质相同（都是「已知人名子串命中 − 发送者 − 参与者映射排除」），差异在于实现路径：
  1. 名称匹配：本脚本把全部主干名编译成**单个正则 alternation**一次扫描；权威版为逐名 `in body` 循环。
  2. 映射校验：本脚本额外做**日志侧覆盖校验**——participants 里每个 PID 必须在日志 `AGENT_BORN`
     集合内、每个被匹配到的名字必须映射到日志中出现的 PID；权威版不做该校验。
  3. 位置索引：两侧同法（PLACE_ARRIVED/PLACE_MOVE 按 (round, agent_id) 建索引、取 seq 前最近一条）。
⚠️ **共同失效风险仍然存在**：两份实现都必须从 `code/config/personas.json` 读 PID→主干名映射，
因为 `run.jsonl` 里**没有 display_name 字段**（AGENT_BORN 仅含 agent_id/birth_round/home_place/needs_init，
已实测确认）。⇒ 互证覆盖的是**实现 bug**，**不覆盖映射数据本身的错误**（若 personas.json 的名字
与跑批实际使用的名字不一致，两份实现会同时错）。

用法：
  python3 v2/evidence/g1_metrics_crosscheck.py --run v2/evidence/run_g1_b0_n16r60_seed42/run.jsonl
  python3 v2/evidence/g1_metrics_crosscheck.py --run <A1 run.jsonl> \
      --bootstrap-from v2/evidence/run_g1_b0_n16r60_seed42/run.jsonl --out /tmp/a1.json
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import re


def load_mapping(personas_path: str):
    """PID → 主干名。显示名形如 `青溪镇·老石`，取最后一段。"""
    d = json.load(open(personas_path, encoding="utf-8"))
    return {p["persona_id"]: p["display_name"].split("·")[-1].strip() for p in d["personas"]}


def parse_log(path: str):
    """单次遍历：分出消息事件与位置事件，同时收集日志侧出现过的 PID。"""
    msgs, places, born = [], collections.defaultdict(list), set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            t = e.get("type")
            pl = e.get("payload") or {}
            if t == "AGENT_BORN":
                if pl.get("agent_id"):
                    born.add(str(pl["agent_id"]))
                continue
            if t in ("PLACE_ARRIVED", "PLACE_MOVE"):
                aid, plc = pl.get("agent_id") or e.get("actor"), pl.get("place") or pl.get("to_place")
                if aid and plc and e.get("round") is not None:
                    places[(int(e["round"]), str(aid))].append((int(e.get("seq") or 0), str(plc)))
                continue
            if t in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
                msgs.append(e)
    for k in places:
        places[k].sort()
    return msgs, places, born


def position_at(places, rnd, pid, seq):
    """该 (round, pid) 在 seq 之前最近一次位置；无则 None。"""
    arr = places.get((int(rnd), str(pid)))
    if not arr:
        return None
    upto = [x for x in arr if x[0] <= int(seq or 0)]
    return (upto[-1][1] if upto else arr[0][1])


def wilson95(k: int, n: int, z: float = 1.959964):
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [round(100 * max(0.0, mid - half), 4), round(100 * min(1.0, mid + half), 4)]


def evaluate(run_path: str, mapping: dict[str, str]):
    name2pid = {v: k for k, v in mapping.items()}
    msgs, places, born = parse_log(run_path)

    # --- 日志侧映射校验（本实现特有）---
    name_re = re.compile("|".join(sorted((re.escape(n) for n in name2pid), key=len, reverse=True)))
    unmapped_pids: set[str] = set()
    for m in msgs:
        for pid in (m.get("payload") or {}).get("participants") or []:
            if str(pid) not in mapping:
                unmapped_pids.add(str(pid))
    names_hit = set()
    for m in msgs:
        names_hit.update(name_re.findall((m.get("payload") or {}).get("body") or ""))
    bad_names = sorted(n for n in names_hit if name2pid[n] not in born)

    g1_flags, g1b_flags, hits = [], [], []
    for m in msgs:
        pl = m["payload"]
        body = pl.get("body") or ""
        mentioned = list(dict.fromkeys(name_re.findall(body)))     # 去重保序
        own = mapping.get(str(pl.get("author") or pl.get("from") or ""))
        parts = [str(x) for x in (pl.get("participants") or [])]
        if not parts:                                             # PREREG fallback：author + to
            sender = str(pl.get("author") or pl.get("from") or "")
            parts = [sender] + ([str(pl["to"])] if pl.get("to") else [])
        present = {mapping.get(p) for p in parts if mapping.get(p)}  # ← 关键：PID→主干名后再排除
        third = [n for n in mentioned if n != own and n not in present]

        g1_flags.append(1 if third else 0)

        violation = 0
        if third and pl.get("place"):
            for n in third:
                where = position_at(places, m["round"], name2pid[n], m["seq"])
                if where is not None and where != pl["place"]:
                    violation = 1
                    break
        g1b_flags.append(violation)
        if third:
            hits.append({
                "seq": m.get("seq"), "round": m.get("round"), "author": own,
                "place": pl.get("place"),
                "third": third,
                "third_positions": {n: position_at(places, m["round"], name2pid[n], m["seq"]) for n in third},
                "violation": bool(violation),
                "body": body,
            })

    n = len(msgs)
    k1, k1b = sum(g1_flags), sum(g1b_flags)
    return {
        "run": run_path,
        "n_msgs": n,
        "channels": dict(collections.Counter(m["type"] for m in msgs)),
        "G-1": {"k": k1, "n": n, "pct": round(100 * k1 / n, 4) if n else 0.0,
                "wilson95": wilson95(k1, n)},
        "G-1b": {"k": k1b, "n": n, "pct": round(100 * k1b / n, 4) if n else 0.0},
        "targets": dict(collections.Counter(t for h in hits for t in h["third"]).most_common()),
        "hits": hits,
        # 本实现特有的映射校验结果（互证的价值之一）
        "mapping_check": {
            "personas_pids": len(mapping),
            "log_born_pids": len(born),
            "pids_in_msgs_not_in_mapping": sorted(unmapped_pids),
            "names_mapped_to_pid_absent_from_log": bad_names,
        },
        "_g1_flags": g1_flags,
    }


def noise_band(flags, B: int = 2000, seed: int = 42):
    """B2 抽样噪声带：同分布零假设下比率差的分位（不是效应 CI）。"""
    rng, n, diffs = random.Random(seed), len(flags), []
    for _ in range(B):
        a = sum(flags[rng.randrange(n)] for _ in range(n)) / n
        b = sum(flags[rng.randrange(n)] for _ in range(n)) / n
        diffs.append(100 * (a - b))
    diffs.sort()
    return [round(diffs[int(0.025 * (B - 1))], 4), round(diffs[int(0.975 * (B - 1))], 4)]


def main() -> int:
    # CLI 与权威版 `v2/evidence/g1_metrics_fixed.py` 同形（含同义别名），报告只给一套命令
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", "--log", dest="run", required=True, help="run.jsonl 路径")
    ap.add_argument("--meta", default=None, help="同批次 meta.json（可选；本实现只做存在性核对）")
    ap.add_argument("--personas", "--names", dest="personas", default="code/config/personas.json")
    ap.add_argument("--bootstrap-from", default=None,
                    help="噪声带用哪条臂的标签重采样（R15 约定：两臂都传 b0）")
    ap.add_argument("--out", "--out-json", dest="out", default=None)
    a = ap.parse_args()

    mapping = load_mapping(a.personas)
    res = evaluate(a.run, mapping)
    flags = res.pop("_g1_flags")

    band_src = a.bootstrap_from or a.run
    if band_src == a.run:
        band_flags = flags
    else:
        band_flags = evaluate(band_src, mapping).pop("_g1_flags")
    res["G-1_band_pp"] = noise_band(band_flags)
    res["band_source"] = band_src

    tg = res["targets"]
    total = sum(tg.values())
    res["dispersion"] = {
        "M1_distinct_over_total": round(len(tg) / total, 4) if total else None,
        "M2_max_target_share": round(max(tg.values()) / total, 4) if total else None,
        "note": "D7 要求的披露列（F5 判据过松），不作放行条件",
    }

    out = json.dumps(res, ensure_ascii=False, indent=2)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
