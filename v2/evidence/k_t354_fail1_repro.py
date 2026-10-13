"""T363 `FAIL①` 假红 · 非作者独立复现（kernel-dev）。

复现 T363 三臂 on/off/neu，逐条比较：族计数 / 事件总数 / state_hash / 去哈希链差异类型。
预期：off vs neu 族计数全等、总数全等、state_hash 相等；逐条差异仅 WORLD_INIT(+config_digest)
与 TURN_SEAL(payload.last_hash 级联) ⇒ 关臂干净，FAIL① 系核验脚本判据过严。

用法：python v2/evidence/k_t354_fail1_repro.py
"""
import collections
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]           # => social-experiment/
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "v2" / "evidence"))
os.environ.setdefault("N50_VEC", "0")

import t363_verify_t354 as t3  # 复用作者核验脚本的 run_world（三臂同装置）  # noqa: E402


def _fc(recs):
    return collections.Counter(r["type"] for r in recs)


def _nohash(rs):
    return [json.dumps({k: v for k, v in r.items() if k not in ("hash", "prev_hash")},
                       ensure_ascii=False, sort_keys=True, separators=(",", ":")) for r in rs]


def main(seed=7, n=3, rounds=8):
    on = t3.run_world(seed, n, rounds, ongoing=True)
    off = t3.run_world(seed, n, rounds, ongoing=False)
    neu = t3.run_world(seed, n, rounds, ongoing=True, neutralize=True)
    fo, fn = _fc(off[1]), _fc(neu[1])
    print("=== family diff off vs neu ===")
    for k in sorted(set(fo) | set(fn)):
        if fo.get(k, 0) != fn.get(k, 0):
            print(f"  {k}: off={fo.get(k,0)} neu={fn.get(k,0)}")
    print("=== len ===", "off", len(off[1]), "neu", len(neu[1]))
    print("state_hash off==neu:", off[2] == neu[2])
    co, cn = _nohash(off[1]), _nohash(neu[1])
    diffs = [i for i in range(min(len(co), len(cn))) if co[i] != cn[i]]
    print("=== nohash diff count ===", len(diffs))
    print("types:", [off[1][i]["type"] for i in diffs])
    for i in diffs[:2]:
        a, b = off[1][i], neu[1][i]
        pa, pb = a.get("payload", {}), b.get("payload", {})
        for k in sorted(set(pa) | set(pb)):
            if pa.get(k) != pb.get(k):
                print(f"  seq {a.get('seq')} {a['type']} {k}: off={pa.get(k)!r} neu={pb.get(k)!r}")


if __name__ == "__main__":
    main()
