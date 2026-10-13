#!/usr/bin/env python3
"""T370 辅助：四档分类「三轴」判定（T370 第②③件）—— 只读。

对齐 `v2/refs/change-classification-4way.md`：
  世界态轴 = state_hash；日志轴 = 哈希链（比事件流，剥 hash/prev_hash）；指纹轴 = engine_version。
判据：`state_hash` 不变 + 事件流变 + 指纹不变 ⇒ ②仅日志增；`state_hash` 不变 + 事件流不变 + 指纹变 ⇒ ③仅指纹变；
      `state_hash` 变 ⇒ ①行为变；全不变 ⇒ ④。
⚠️ 前置门：等 T355 跑完 + 广播后跑（两版对比需真跑，属重活）。

用法：python3 v2/evidence/t370_three_axis_helper.py A.jsonl B.jsonl [cfgA_dir] [cfgB_dir]
- A/B：两份 run.jsonl（同 seed 两版/两开关）；剥 hash/prev_hash 后逐条比。
- cfgA_dir/cfgB_dir：可选，两版 config 目录，用于指纹轴比对。
"""
import os
import sys
import json
import importlib


def load_stream(p):
    """事件流：剥 hash/prev_hash（日志轴），保留 type/round/payload 等语义字段。"""
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            r.pop("hash", None)
            r.pop("prev_hash", None)
            out.append(r)
    return out


def fingerprint(cfg_dir):
    sys.path.insert(0, cfg_dir)
    import engine.version as V
    importlib.reload(V)
    fn = getattr(V, "compute_fingerprint", None)
    return fn() if callable(fn) else None


def main():
    if len(sys.argv) < 3:
        print("usage: t370_three_axis_helper.py A.jsonl B.jsonl [cfgA_dir cfgB_dir]")
        return 2
    A, B = sys.argv[1], sys.argv[2]
    for p in (A, B):
        if not os.path.exists(p):
            print(f"PENDING: 缺 {p}")
            return 2
    sa, sb = load_stream(A), load_stream(B)
    print(f"[日志轴] 行数 A={len(sa)} B={len(sb)}")
    # 逐条比（剥链后）
    n = min(len(sa), len(sb))
    first_diff = None
    for i in range(n):
        if sa[i] != sb[i]:
            first_diff = i
            break
    if first_diff is None and len(sa) != len(sb):
        first_diff = n
    if first_diff is None:
        print("  事件流（剥链后）逐条一致 ⇒ 日志轴【不变】")
    else:
        i = first_diff
        print(f"  首个差异 @ {i}: A={ {k:sa[i].get(k) for k in ('type','round')} if i<len(sa) else 'EOF'}"
              f" B={ {k:sb[i].get(k) for k in ('type','round')} if i<len(sb) else 'EOF'}")
        print("  ⇒ 日志轴【变】")
    if len(sys.argv) >= 5:
        fa, fb = fingerprint(sys.argv[3]), fingerprint(sys.argv[4])
        print(f"[指纹轴] A={fa} B={fb} -> {'不变' if fa == fb else '变'}")
    print("\n注：世界态轴（state_hash）请取自各 run 的 TURN_SEAL.state_hash 或另行同 seed 跑；"
          "按 `change-classification-4way.md` §1 表对号入座。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
