"""内核 CLI（D0 内核）。

用法：
  python -m engine run    --seed 12345 --rounds 20 --config config/default.json --out logs/run.jsonl
  python -m engine run    --life --seed 42 --agents 3 --weeks 1 --out logs/life.jsonl   # 兼容 shim
  python -m engine replay --log logs/run.jsonl
  python -m engine verify --log logs/run.jsonl

说明：`--life` 为向后兼容 shim，内部**惰性**委托 orchestration 组合根（真内核 × 生活层）；
纯内核（空世界）路径不依赖 life / orchestration。规范入口：`python -m orchestration run --life`。
"""

from __future__ import annotations

import argparse
import sys

from .replay import replay_records
from .runner import default_config, load_config, read_log, run, write_log
from .state import state_hash

WEEK_ROUNDS = 84


def _cmd_run(args) -> int:
    if getattr(args, "life", False):
        return _cmd_run_life(args)
    config = load_config(args.config) if args.config else default_config()
    res = run(seed=args.seed, config=config, rounds=args.rounds)
    if args.out:
        write_log(res["records"], args.out)
    print(f"rounds={res['rounds']} events={len(res['records'])} "
          f"chain_ok={res['chain_ok']} final_state_hash={res['final_state_hash']}")
    if args.out:
        print(f"log written: {args.out}")
    return 0 if res["chain_ok"] else 1


def _cmd_run_life(args) -> int:
    # 惰性委托组合根（避免 kernel 包在 import 期依赖 orchestration/life）
    from orchestration.integration import run_e2e
    config = load_config(args.config) if args.config else None
    rounds = args.rounds
    if getattr(args, "weeks", None):
        rounds = int(round(args.weeks * WEEK_ROUNDS))
    rep = run_e2e(seed=args.seed, rounds=rounds, n=args.agents, config=config,
                  out_path=args.out, personas_path=args.personas, places_path=args.places,
                  side_root=getattr(args, "side_root", None))
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
    records = read_log(args.log)
    state = replay_records(records)
    print(f"replay ok: rounds={state.round} "
          f"agents={len(state.agents)} state_hash={state_hash(state)}")
    return 0


def _cmd_verify(args) -> int:
    records = read_log(args.log)
    s1 = state_hash(replay_records(records))
    s2 = state_hash(replay_records(records))
    ok = s1 == s2
    print(f"replay#1={s1}")
    print(f"replay#2={s2}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="engine", description="确定性内核 CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="跑 N 回合（空世界；--life 走 life 世界）并落盘日志")
    pr.add_argument("--seed", type=int, default=12345)
    pr.add_argument("--rounds", type=int, default=20)
    pr.add_argument("--config", default=None)
    pr.add_argument("--out", default=None)
    pr.add_argument("--life", action="store_true", help="在真内核上运行 life 层（多 Agent）")
    pr.add_argument("--agents", type=int, default=3, help="life 模式下的 Agent 数")
    pr.add_argument("--weeks", type=float, default=None, help="life 模式：模拟周数（1 周=84 回合）")
    pr.add_argument("--personas", default=None, help="personas.json 路径")
    pr.add_argument("--places", default=None, help="places.json 路径")
    pr.add_argument("--side-root", default=None,
                    help="侧存储/冻结缓存根目录（默认临时目录）")
    pr.set_defaults(func=_cmd_run)

    pp = sub.add_parser("replay", help="从日志重放")
    pp.add_argument("--log", required=True)
    pp.set_defaults(func=_cmd_replay)

    pv = sub.add_parser("verify", help="重放两次并比对状态哈希（门禁）")
    pv.add_argument("--log", required=True)
    pv.set_defaults(func=_cmd_verify)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
