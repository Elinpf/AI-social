#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""D9m/D9n 示例句序列生成器（S-DET 跨进程入口）。

唯一职责：**复现实现件的选句**，供 batch-runner / verifier 跨进程验「同 seed 两次序列逐字节一致」
（S-DET）与「不同 seed 序列不同」。

确定性契约（与 `code/life/agent.py::narration_example` 同源、同算法）：
    idx = int(sha256_hex("narration-rotate|<seed>|<agent_id>|<round>|<kind>")[:8], 16) % n
    seed = env HITT_WORLD_SEED，未设/空串回落 "0"
    kind ∈ {"initiate","reply"}；不读墙钟、不用 random、无进程级状态。

词表来源（两条通道，且互相校验）：
  1. 首选 `life.agent.NARRATION_EXAMPLES`（需 `PYTHONPATH=<repo>/code`，与实现件同一份对象）；
  2. 回退 `tools/d9n/narration_family_lexicon.json::rotation_examples`（无 code/ 依赖）。
  两者都存在时**必须逐项相等**，否则本工具直接报错退出（防「尺子被换」静默漂移）。

用法：
    # 单点
    PYTHONPATH=code python3 tools/d9n/narration_example_seq.py --agent P003 --round 7 --kind initiate
    # 序列（S-DET 用；输出 JSON，逐字节可 diff）
    PYTHONPATH=code python3 tools/d9n/narration_example_seq.py --agent P003 --rounds 0-23 --kind reply \
        --seed 42 --out /tmp/seq_P003_reply_s42.json
    # 两臂/两 seed 对比
    PYTHONPATH=code python3 tools/d9n/narration_example_seq.py --agent P003 --rounds 0-23 --kind initiate \
        --compare-seeds 0,42
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_LEXICON = HERE / "narration_family_lexicon.json"
SEED_ENV = "HITT_WORLD_SEED"
SALT = "narration-rotate"


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _lexicon_examples():
    """lexicon 里若带 rotation_examples 就取出来做交叉校验（冻结件当前未含该键）。"""
    lex = json.loads(DEFAULT_LEXICON.read_text(encoding="utf-8"))
    ex = lex.get("rotation_examples")
    return list(ex) if ex else None


def load_examples() -> tuple[list, str]:
    """返回 (词表, 来源标签)。首选实现件对象；两者都在时必须逐项相等。"""
    from_lexicon = _lexicon_examples()
    try:
        code_dir = REPO / "code"
        if str(code_dir) not in sys.path:
            sys.path.insert(0, str(code_dir))
        from life.agent import NARRATION_EXAMPLES  # noqa: E402
    except Exception as exc:  # code/ 不可导入时退回 lexicon
        if not from_lexicon:
            raise SystemExit(
                "[d9n] 无法导入 life.agent（需 PYTHONPATH=code），且 lexicon 无 rotation_examples")
        return from_lexicon, f"lexicon(fallback:{type(exc).__name__})"
    if from_lexicon is not None and list(NARRATION_EXAMPLES) != from_lexicon:
        raise SystemExit(
            "[d9n] 词表不一致：life.agent.NARRATION_EXAMPLES != lexicon.rotation_examples"
            f"\n  code = {list(NARRATION_EXAMPLES)}\n  lex  = {from_lexicon}")
    tag = "life.agent.NARRATION_EXAMPLES" + ("(+lexicon verified)" if from_lexicon else "")
    return list(NARRATION_EXAMPLES), tag


def resolve_seed(seed=None) -> str:
    if seed is not None:
        s = str(seed).strip()
    else:
        s = (os.environ.get(SEED_ENV, "") or "").strip()
    return s or "0"


def pick(kind: str, agent_id: str, round_no: int, seed=None, examples=None) -> str:
    ex = examples if examples is not None else load_examples()[0]
    sd = resolve_seed(seed)
    h = sha256_hex(f"{SALT}|{sd}|{agent_id or ''}|{int(round_no)}|{kind}")
    return ex[int(h[:8], 16) % len(ex)]


def sequence(kind: str, agent_id: str, rounds, seed=None, examples=None) -> list:
    ex = examples if examples is not None else load_examples()[0]
    return [{"round": int(r), "kind": kind, "agent_id": agent_id,
             "seed": resolve_seed(seed), "example": pick(kind, agent_id, r, seed, ex)}
            for r in rounds]


def parse_rounds(spec: str) -> list:
    if "-" in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",") if x.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--kind", default="initiate", choices=["initiate", "reply"])
    ap.add_argument("--rounds", default="0")
    ap.add_argument("--round", type=int, default=None)
    ap.add_argument("--seed", default=None)
    ap.add_argument("--compare-seeds", default=None, help="如 0,42")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    examples, source = load_examples()
    if args.round is not None:
        out = {"source": source, "n_examples": len(examples),
               "seed": resolve_seed(args.seed), "agent_id": args.agent, "kind": args.kind,
               "round": args.round,
               "example": pick(args.kind, args.agent, args.round, args.seed, examples)}
    elif args.compare_seeds:
        seeds = [s.strip() for s in args.compare_seeds.split(",") if s.strip()]
        rounds = parse_rounds(args.rounds)
        out = {"source": source, "n_examples": len(examples), "agent_id": args.agent,
               "kind": args.kind, "rounds": [int(r) for r in rounds],
               "by_seed": {s: [e["example"] for e in sequence(args.kind, args.agent, rounds, s, examples)]
                           for s in seeds}}
        out["seeds_differ"] = len({tuple(v) for v in out["by_seed"].values()}) > 1
    else:
        rounds = parse_rounds(args.rounds)
        out = {"source": source, "n_examples": len(examples), "agent_id": args.agent,
               "kind": args.kind, "rounds": [int(r) for r in rounds],
               "seed": resolve_seed(args.seed),
               "sequence": sequence(args.kind, args.agent, rounds, args.seed, examples),
               "sequence_sha256": sha256_hex(json.dumps(
                   [e["example"] for e in sequence(args.kind, args.agent, rounds, args.seed, examples)],
                   ensure_ascii=False))}

    txt = json.dumps(out, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(txt + "\n", encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
