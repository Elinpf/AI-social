"""orchestration CLI（组合根入口）。

用法：
  python -m orchestration run --life --seed 42 --agents 3 --weeks 1 --out logs/life.jsonl
  python -m orchestration run --life --seed 42 --agents 10 --rounds 84 --out logs/life10.jsonl
  python -m orchestration replay --log logs/life.jsonl
  python -m orchestration verify --log logs/life.jsonl
"""

from __future__ import annotations

import argparse
import sys

from engine.replay import replay_records
from engine.runner import load_config, read_log
from engine.state import state_hash

from .integration import run_e2e

WEEK_ROUNDS = 84


def _cmd_run(args) -> int:
    config = load_config(args.config) if args.config else None
    rounds = args.rounds
    if args.weeks is not None:
        rounds = int(round(args.weeks * WEEK_ROUNDS))
    rep = run_e2e(seed=args.seed, rounds=rounds, n=args.agents, config=config,
                  out_path=args.out, personas_path=args.personas, places_path=args.places,
                  side_root=args.side_root, flush_every=args.flush_every,
                  resume_from=args.resume_from, target_round=args.target_round)
    print(f"[life] n_agents={rep['n_agents']} rounds={rep['rounds']} events={rep['events']} "
          f"seconds={rep['seconds']} log_bytes={rep['log_bytes']}")
    print(f"  unknown_event_types={rep['unknown_event_types']}")
    print(f"  chain_ok={rep['chain_ok']} replay_parity={rep['replay_parity']} "
          f"first_run_equals_replay={rep['first_run_equals_replay']}")
    print(f"  conservation_ok={rep['conservation_ok']} final_state_hash={rep['final_state_hash']}")
    if args.out:
        print(f"  log written: {args.out}")
    ok = (rep["chain_ok"] and rep["replay_parity"] and rep["conservation_ok"]
          and not rep["unknown_event_types"])
    return 0 if ok else 1


def _cmd_replay(args) -> int:
    state = replay_records(read_log(args.log))
    print(f"replay ok: rounds={state.round} agents={len(state.agents)} "
          f"state_hash={state_hash(state)}")
    return 0


def _cmd_verify(args) -> int:
    records = read_log(args.log)
    s1 = state_hash(replay_records(records))
    s2 = state_hash(replay_records(records))
    print(f"replay#1={s1}")
    print(f"replay#2={s2}")
    print("PASS" if s1 == s2 else "FAIL")
    return 0 if s1 == s2 else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="orchestration", description="实验编排（真内核 × 生活层）")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="在真内核上跑 life 世界（多 Agent）")
    pr.add_argument("--seed", type=int, default=42)
    pr.add_argument("--rounds", type=int, default=WEEK_ROUNDS)
    pr.add_argument("--agents", type=int, default=3)
    pr.add_argument("--weeks", type=float, default=None, help="模拟周数（1 周=84 回合）")
    pr.add_argument("--config", default=None)
    pr.add_argument("--out", default=None)
    pr.add_argument("--personas", default=None)
    pr.add_argument("--places", default=None)
    pr.add_argument("--side-root", default=None,
                    help="侧存储/冻结缓存根目录（默认临时目录；显式指定可复现/复用缓存）")
    pr.add_argument("--flush-every", type=int, default=0,
                    help="周期 flush：每 N 回合原子落盘已提交前缀（0=仅末尾写；长跑建议设正数防 kill 丢日志）")
    pr.add_argument("--resume-from", default=None,
                    help="T276 续跑：从该已 flush 日志的完整前缀恢复并续跑（须复用同一 --side-root）")
    pr.add_argument("--target-round", type=int, default=None,
                    help="T276 续跑目标回合（缺省用 --rounds/--weeks）")
    pr.add_argument("--life", action="store_true", help="（默认即 life 模式，保留兼容）")
    pr.set_defaults(func=_cmd_run)

    pp = sub.add_parser("replay", help="从日志重放")
    pp.add_argument("--log", required=True)
    pp.set_defaults(func=_cmd_replay)

    pv = sub.add_parser("verify", help="重放两次并比对状态哈希（门禁）")
    pv.add_argument("--log", required=True)
    pv.set_defaults(func=_cmd_verify)

    ps = sub.add_parser("sweep-side", help="清理孤儿临时 side 目录（T232；不静默，带告警）")
    ps.add_argument("--base", default=None, help="扫描根目录（默认系统 tempdir）")
    ps.add_argument("--ttl", type=float, default=3600.0, help="孤儿时限（秒）")
    ps.add_argument("--dry-run", action="store_true", help="只报告不删除（安全巡检）")
    ps.set_defaults(func=_cmd_sweep)

    args = p.parse_args(argv)
    return args.func(args)


def _cmd_sweep(args) -> int:
    from .integration import sweep_orphan_side_dirs
    res = sweep_orphan_side_dirs(base_dir=args.base, ttl_seconds=args.ttl, dry_run=args.dry_run)
    verb = "would_remove" if args.dry_run else "removed"
    print(f"[sweep-side] {verb}={len(res['would_remove'] if args.dry_run else res['removed'])} "
          f"kept={len(res['kept'])}")
    for p in (res["would_remove"] if args.dry_run else res["removed"])[:10]:
        print(f"  {verb}: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
