"""T103 证据：v2 P1 验收③ —— 真 LLM 对话内容实证（mock vs 真 LLM body 分叉）。

**同 seed** 跑两次：`provider=mock` 与 `provider=openai_compat`（后者 `--require-provider` 守卫）。

> **仪表纪律（团队规矩）**：多跑对比**必须分进程**（同进程连续 `run_e2e` 会受模块级状态污染 ⇒ 假分叉）。
> 本脚本：**每个 provider 在独立子进程**里跑（driver 用 `subprocess` 分别拉起 `--one mock` / `--one openai_compat`），
> 两棵世界**不共享进程**。

产出 `v2/evidence/t103_dialogue_real_llm.json`（不含密钥/端点凭据）。

用法：
    set -a; . ./.env.local 2>/dev/null; set +a    # 提供 LLM_API_KEY（禁止入库）
    HITT_LLM_PROVIDER=openai_compat LLM_ENDPOINT=$VISION_API_BASE LLM_MODEL=$VISION_MODEL_NAME \
      LLM_API_KEY=$VISION_API_KEY \
      python3 scripts/t103_dialogue_real_llm_evidence.py --n 3 --rounds 10 \
        --out ../v2/evidence/t103_dialogue_real_llm.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")


def _run_once(kind: str, seed: int, n: int, rounds: int, require_provider: str | None):
    # 每个 provider 独立进程：这里只跑一棵世界。
    if kind == "openai_compat":
        os.environ["HITT_LLM_PROVIDER"] = "openai_compat"
    else:
        os.environ.pop("HITT_LLM_PROVIDER", None)

    from orchestration.integration import build_world

    side_root = tempfile.mkdtemp(prefix=f"t103_{kind}_side_")
    try:
        world = build_world(seed=seed, n=n, side_root=side_root)
        engine = world["engine"]
        for r in range(rounds):
            engine.run_round(r)
        records = engine.ledger.records
        llm = world["agents"][0].llm
        client = getattr(llm, "client", None)
        provider = getattr(client, "provider", None)
        pname = type(provider).__name__ if provider is not None else None
        if require_provider is not None:
            assert pname == "OpenAICompatProvider", (
                f"--require-provider openai_compat 未满足：实际 provider={pname}（可能静默回退）")
        return {"engine": engine, "records": records, "client": client,
                "provider": provider, "provider_name": pname}
    finally:
        shutil.rmtree(side_root, ignore_errors=True)


def _analyze(run: dict) -> dict:
    from engine.replay import replay_records
    from engine.state import state_hash

    records = run["records"]
    provider = run["provider"]
    client = run["client"]
    calls_before = getattr(provider, "calls", None)
    c = Counter(rec["type"] for rec in records)

    dlg = [rec for rec in records
           if rec["type"] == "LLM_CALL" and rec["payload"].get("purpose") == "dialogue"]
    dlg_thinking_false = sum(1 for rec in dlg if rec["payload"].get("thinking") is False)

    msg_list: list[dict] = []
    msg_counts = {t: 0 for t in MSG_TYPES}
    for rec in records:
        if rec["type"] in MSG_TYPES:
            p = rec["payload"]
            msg_counts[rec["type"]] += 1
            msg_list.append({"channel": rec["type"], "msg_id": p.get("msg_id"),
                             "from": p.get("from") or p.get("author"), "to": p.get("to"),
                             "body": p.get("body")})

    cost: dict[str, dict] = defaultdict(lambda: {"n": 0, "tin": 0, "tout": 0})
    for rec in records:
        if rec["type"] == "LLM_CALL":
            pp = rec["payload"]
            d = cost[pp.get("purpose")]
            d["n"] += 1
            d["tin"] += int(pp.get("tokens_in", 0))
            d["tout"] += int(pp.get("tokens_out", 0))

    h1 = state_hash(replay_records(records, verify=True, verify_seals=True))
    h2 = state_hash(replay_records(records, verify=True, verify_seals=False))
    calls_after = getattr(provider, "calls", None)

    return {
        "provider": run["provider_name"],
        "events": len(records),
        "dialogue_llm_call": {
            "count": len(dlg), "thinking_false": dlg_thinking_false,
            "tiers": dict(Counter(r["payload"].get("tier") for r in dlg)),
            "samples": [r["payload"].get("prompt_hash") for r in dlg[:2]],
        },
        "msg_counts": msg_counts,
        "group_created": c.get("GROUP_CREATED", 0),
        "system_error": c.get("SYSTEM_ERROR", 0),
        "intent_rejected": c.get("INTENT_REJECTED", 0),
        "llm_calls_total": c.get("LLM_CALL", 0),
        "cost_by_purpose": {k: v for k, v in cost.items()},
        "replay": {
            "hash_1": h1, "hash_2": h2, "parity": h1 == h2,
            "provider_calls_before": calls_before, "provider_calls_after": calls_after,
            "llm_calls_during_replay": (None if calls_before is None else calls_after - calls_before),
            "client_llm_calls": getattr(client, "llm_calls", None),
        },
        "engine_version": getattr(getattr(client, "config", None), "engine_version", None),
        "_msg_list": msg_list,
    }


def _spawn_one(kind: str, seed: int, n: int, rounds: int, dump: str, require_provider: str | None) -> None:
    """在**独立子进程**里跑一个 provider（仪表纪律：分进程）。"""
    cmd = [sys.executable, os.path.abspath(__file__),
           "--one", kind, "--seed", str(seed), "--n", str(n), "--rounds", str(rounds),
           "--dump", dump]
    if require_provider:
        cmd += ["--require-provider", require_provider]
    subprocess.run(cmd, check=True, env=dict(os.environ))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--require-provider", default=None)
    ap.add_argument("--out", default="../v2/evidence/t103_dialogue_real_llm.json")
    ap.add_argument("--one", choices=["mock", "openai_compat"], default=None,
                    help="内部：只跑一个 provider 并 dump（由 driver 以子进程调用）")
    ap.add_argument("--dump", default=None, help="内部：--one 模式下分析结果落盘路径")
    args = ap.parse_args()

    # ---- 子进程模式：跑一棵世界，analyze，dump ----
    if args.one:
        run = _run_once(args.one, args.seed, args.n, args.rounds,
                        args.require_provider if args.one == "openai_compat" else None)
        analysis = _analyze(run)
        Path(args.dump).write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0

    # ---- driver 模式：两个 provider 各自独立子进程 ----
    workdir = tempfile.mkdtemp(prefix="t103_dumps_")
    try:
        mock_dump = str(Path(workdir) / "mock.json")
        real_dump = str(Path(workdir) / "real.json")
        _spawn_one("mock", args.seed, args.n, args.rounds, mock_dump, None)
        _spawn_one("openai_compat", args.seed, args.n, args.rounds, real_dump, args.require_provider)

        mock = json.loads(Path(mock_dump).read_text(encoding="utf-8"))
        real = json.loads(Path(real_dump).read_text(encoding="utf-8"))

        ml, rl = mock["_msg_list"], real["_msg_list"]
        ncmp = min(len(ml), len(rl))
        diffs = [{"channel": rl[i]["channel"], "msg_id": rl[i]["msg_id"],
                  "mock": ml[i]["body"], "real": rl[i]["body"]}
                 for i in range(ncmp) if ml[i]["body"] != rl[i]["body"]]
        real_samples = [{"msg_id": x["msg_id"], "channel": x["channel"], "body": x["body"]}
                        for x in rl if x["channel"] == "MSG_DM"][:3]

        mock.pop("_msg_list", None)
        real.pop("_msg_list", None)

        evidence = {
            "task": "T103", "seed": args.seed, "n_agents": args.n, "rounds": args.rounds,
            "endpoint": "(masked)", "model": os.environ.get("LLM_MODEL") or "mock",
            "instrument": {
                "multi_run_isolation": "separate_process",
                "note": "mock 与 real 各在独立子进程运行（团队 harness 规矩：多跑对比必须分进程）",
            },
            "mock_run": mock, "real_run": real,
            "body_divergence": {
                "paired_by": "record_order", "mock_msg_len": len(ml), "real_msg_len": len(rl),
                "n_compared": ncmp, "n_differ": len(diffs), "n_identical": ncmp - len(diffs),
                "examples": diffs[:3], "verdict": ("DIVERGED" if diffs else "IDENTICAL"),
            },
            "real_dialogue_samples": real_samples,
        }
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"[mock] dialogue={mock['dialogue_llm_call']['count']} msg={mock['msg_counts']} "
              f"GC={mock['group_created']} SYSERR={mock['system_error']} replay={mock['replay']['parity']}")
        print(f"[real] dialogue={real['dialogue_llm_call']['count']} "
              f"(thinking_false={real['dialogue_llm_call']['thinking_false']}) msg={real['msg_counts']} "
              f"GC={real['group_created']} SYSERR={real['system_error']} replay={real['replay']['parity']} "
              f"replay_llm_calls={real['replay']['llm_calls_during_replay']}")
        print(f"[cost/purpose real] {real['cost_by_purpose']}")
        print(f"[divergence] verdict={evidence['body_divergence']['verdict']} differ={len(diffs)}/{ncmp}")
        for e in diffs[:2]:
            print(f"   {e['channel']} {e['msg_id']}: mock={e['mock']!r} -> real={e['real']!r}")
        print(f"[evidence] {args.out}")
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
