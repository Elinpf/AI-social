"""
C-1 a1 臂「进度偏移比」复算脚本（只读两侧 run.jsonl + 两侧 side-root 的 freeze 响应文件 mtime）

回答 Leader 的问题：a1 是不是真的比 ctrl 慢 4~5 倍（线性外推得 11 小时），还是前段密度低造成的错觉。

三个互不依赖的口径：
  P1  同 wall-clock 偏移下的真实 LLM 响应数（side-root/freeze_cache/responses/*.json 的 mtime 曲线）
  P2  同 round 下的累计 LLM_CALL / cached / 真调用（结构对齐，最硬）
  P3  每轮事件数逐轮对比（结构是否漂移）

复算：cd <REPO>/v2/evidence && python3 run_worldline_c1_a1_n16r84_seed42/progress_check.py
"""
import collections
import datetime as dt
import json
import os

A1 = "run_worldline_c1_a1_n16r84_seed42/run.jsonl"
CTRL = "run_worldline_c1_ctrl_n16r84_seed42/run.jsonl"
A1_SIDE = "/tmp/worldline_c1_a1_side"
CTRL_SIDE = "/tmp/worldline_c1_ctrl_side"


def mtime_curve(root, label):
    d = os.path.join(root, "freeze_cache", "responses")
    if not os.path.isdir(d):
        print(f"--- {label}: 无 responses 目录（side-root 不存在？）")
        return {}
    ts = sorted(os.path.getmtime(os.path.join(d, f)) for f in os.listdir(d))
    out = {}
    print(f"--- {label}: responses={len(ts)} 首次={dt.datetime.fromtimestamp(ts[0]):%H:%M:%S} 末次={dt.datetime.fromtimestamp(ts[-1]):%H:%M:%S}")
    if not ts:
        return out
    t0 = ts[0]
    for mark in (60, 120, 300, 540, 600, 900, 1500, 2100, 2700, 3300):
        c = sum(1 for t in ts if t - t0 <= mark)
        out[mark] = c
        print(f"    t+{mark:5d}s -> {c:5d} responses")
    return out


def upto_round(path, rmax, label):
    calls = cached = jin = jout = 0
    per = collections.Counter()
    per_round_events = collections.Counter()
    for line in open(path):
        e = json.loads(line)
        per_round_events[e["round"]] += 1
        if e["round"] > rmax:
            continue
        if e["type"] != "LLM_CALL":
            continue
        calls += 1
        pl = e["payload"]
        if pl.get("cached"):
            cached += 1
        jin += pl.get("tokens_in", 0) or 0
        jout += pl.get("tokens_out", 0) or 0
        per[e["round"]] += 1
    print(f"{label} 累计到 round<={rmax}: LLM_CALL={calls} cached={cached} 真调用={calls - cached} "
          f"tokens_in={jin} tokens_out={jout}")
    print(f"    每轮 LLM_CALL={[per.get(r, 0) for r in range(rmax + 1)]}")
    return calls, cached, jin, jout, per_round_events


def main():
    print("== P1 同 wall-clock 偏移：真实 LLM 响应文件增长率 ==")
    c = mtime_curve(CTRL_SIDE, "ctrl")
    a = mtime_curve(A1_SIDE, "a1")
    print()
    print("== P1 偏移比（a1 / ctrl，同 t+）==")
    for k in sorted(set(c) & set(a)):
        if c[k]:
            print(f"    t+{k:5d}s: ctrl={c[k]:5d} a1={a[k]:5d}  比={a[k] / c[k]:.3f}")
    print()

    print("== P2 同 round（0..9）结构对齐 ==")
    c_calls, c_cached, c_in, c_out, c_ev = upto_round(CTRL, 9, "ctrl")
    a_calls, a_cached, a_in, a_out, a_ev = upto_round(A1, 9, "a1  ")
    print(f"    LLM_CALL 偏移比 a1/ctrl = {a_calls / c_calls:.3f}（1.000=结构完全同形）")
    print(f"    tokens_in  a1/ctrl = {a_in / c_in:.4f}  （C-1 那一行带来的输入成本增量）")
    print(f"    tokens_out a1/ctrl = {a_out / c_out:.4f}")
    print()

    print("== P3 每轮事件数（round 0..11）==")
    print(f"    ctrl={[c_ev.get(r, 0) for r in range(12)]}")
    print(f"    a1  ={[a_ev.get(r, 0) for r in range(12)]}")


if __name__ == "__main__":
    main()
