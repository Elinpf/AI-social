#!/usr/bin/env python3
"""T356 提示词迭代回路（最小实现；不改 `life/`/`engine/`）。

用法（在 `code/` 目录下运行）：
  python3 /path/to/prompt_iter.py run <version_tag> [--n 8 --rounds 12 --seed 7]
  python3 /path/to/prompt_iter.py compare <tagA> <tagB>

设计要点：
  * **同 seed、同配置、只差提示词**；每版标 `version_tag` + `prompt_sha`；
  * **复用 T227 prompt 落盘**（`freeze/capture.py`）：运行期把 `llm.client.capture` 换成开启版
    （不改代码/不改 config）；产物落 `out/<tag>/prompts/prompts.jsonl`；
  * 对比口径：① 行为差异（事件类型计数、首个 `state_hash` 不等回合）② 生成正文并排（按 purpose）
    ③ 成本/缓存命中（`LLM_CALL` 的 `cached` 命中率）。
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

CODE = Path(__file__).resolve().parents[2] / "code"      # .../code
OUT = Path("/tmp/prompt_iter")
PROMPT_FILES = ("life/agent.py", "life/soft.py", "life/planner.py")  # 提示词所在世界层文件（只读哈希）


def _prompt_sha() -> str:
    h = hashlib.sha256()
    for rel in PROMPT_FILES:
        p = CODE / rel
        if p.exists():
            h.update(rel.encode())
            h.update(p.read_bytes())
    return h.hexdigest()[:16]


def _enable_capture(llm, root: Path):
    """运行期开启 T227 prompt 落盘（仅本工具；默认关的行为不变）。"""
    from freeze.capture import CaptureConfig, PromptCapture
    cfg = CaptureConfig(enabled=True, mode="purpose",
                        purposes=frozenset({"dialogue", "reflect", "negotiation", "plan"}))
    client = getattr(llm, "client", llm)
    client.capture = PromptCapture(cfg, root=str(root))


def cmd_run(a) -> int:
    from engine.runner import default_config
    from orchestration.integration import build_world
    d = OUT / a.tag
    (d / "prompts").mkdir(parents=True, exist_ok=True)
    cfg = default_config()
    if a.wake_off:   # 口径注：仅当需强制驱动提示词时才传 config（默认不传 = 与常规跑一致）
        cfg.setdefault("policy", {}).setdefault("wake", {})["enabled"] = False
        w = build_world(seed=a.seed, n=a.n, config=cfg)
    else:
        w = build_world(seed=a.seed, n=a.n)
    eng = w["engine"]
    llm = w["agents"][0].llm
    _enable_capture(llm, d)
    for r in range(a.rounds):
        eng.run_round(r)
    recs = eng.ledger.records
    (d / "run.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in recs), encoding="utf-8")
    meta = {"version_tag": a.tag, "seed": a.seed, "n": a.n, "rounds": a.rounds,
            "wake_off": bool(a.wake_off),
            "prompt_sha": _prompt_sha(), "head_sha": os.popen("git -C %s rev-parse --short HEAD" % CODE.parent).read().strip()}
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    calls = [r for r in recs if r["type"] == "LLM_CALL"]
    hit = sum(1 for r in calls if (r.get("payload") or {}).get("cached"))
    ncap = len(_read_prompts(d))
    print(f"[run] {a.tag}: events={len(recs)} llm_calls={len(calls)} cached={hit} captured={ncap} prompt_sha={meta['prompt_sha']}")
    return 0


def _read_prompts(d: Path):
    import base64
    import zlib
    out = []
    for p in [d / "prompts.jsonl", *list((d / "prompts").glob("*.jsonl"))]:
        if not p.exists():
            continue
        for l in p.read_text(encoding="utf-8").splitlines():
            if not l:
                continue
            try:
                r = json.loads(l)
                if "z" in r:
                    r = json.loads(zlib.decompress(base64.b64decode(r["z"])))
                out.append(r)
            except Exception:
                pass
    return out


def _load(tag):
    d = OUT / tag
    recs = [json.loads(l) for l in (d / "run.jsonl").read_text(encoding="utf-8").splitlines() if l]
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    prompts = _read_prompts(d)
    return recs, meta, prompts


def cmd_compare(a) -> int:
    ra, ma, pa = _load(a.tag_a)
    rb, mb, pb = _load(a.tag_b)
    print(f"# A={a.tag_a} prompt_sha={ma['prompt_sha']}  B={a.tag_b} prompt_sha={mb['prompt_sha']}")
    # ① 行为差异：事件类型计数
    ca = collections.Counter(r["type"] for r in ra)
    cb = collections.Counter(r["type"] for r in rb)
    diff = {t: (ca.get(t, 0), cb.get(t, 0)) for t in sorted(set(ca) | set(cb)) if ca.get(t, 0) != cb.get(t, 0)}
    print("行为差异(类型计数 A->B):", diff or "无")
    # 首个 state_hash 不等回合
    def seals(rs):
        return [(r["round"], (r.get("payload") or {}).get("state_hash")) for r in rs if r["type"] == "TURN_SEAL"]
    sa, sb = seals(ra), seals(rb)
    first = next((x for x, y in zip(sa, sb) if x != y), None)
    print("首个 state_hash 不等回合:", first[0] if first else "无(全等)")
    # ② 正文并排（按 purpose，最多各 3 条）
    def by_purpose(ps):
        m = collections.defaultdict(list)
        for p in ps:
            m[p.get("purpose")].append(p)
        return m
    PA, PB = by_purpose(pa), by_purpose(pb)
    for purpose in sorted(set(PA) | set(PB)):
        print(f"\n== purpose={purpose} (A={len(PA.get(purpose, []))} B={len(PB.get(purpose, []))}) ==")
        for i in range(min(3, max(len(PA.get(purpose, [])), len(PB.get(purpose, []))))):
            av = (PA.get(purpose, [{}])[i].get("output", "")) if i < len(PA.get(purpose, [])) else ""
            bv = (PB.get(purpose, [{}])[i].get("output", "")) if i < len(PB.get(purpose, [])) else ""
            print(f"  A[{i}]: {str(av)[:90]}")
            print(f"  B[{i}]: {str(bv)[:90]}")
    # ③ 成本/缓存
    def cost(rs):
        calls = [r for r in rs if r["type"] == "LLM_CALL"]
        return len(calls), sum(1 for r in calls if (r.get("payload") or {}).get("cached"))
    print("\n成本/缓存 (calls,cached): A=", cost(ra), " B=", cost(rb))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("tag"); r.add_argument("--n", type=int, default=8)
    r.add_argument("--rounds", type=int, default=12); r.add_argument("--seed", type=int, default=7)
    r.add_argument("--wake-off", action="store_true", help="小样本驱动提示词用（wake 门控关闭；口径入 meta）")
    r.set_defaults(fn=cmd_run)
    c = sub.add_parser("compare"); c.add_argument("tag_a"); c.add_argument("tag_b"); c.set_defaults(fn=cmd_compare)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
