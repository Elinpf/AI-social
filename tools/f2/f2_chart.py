#!/usr/bin/env python3
"""F-2 睡眠—遗忘—人格漂移 时间线图（只读取证，不写 run 目录、不改 code/）。

输入：已完成 run 的 run.jsonl（真源事件日志）
输出：<out>.png（三联图：遗忘三级/回合、人格漂移/回合、睡眠窗口与对话密度）
复算：
  python3 /tmp/f2_chart.py <run.jsonl> <out.png>
"""
import hashlib
import json
import sys
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for name in ("Noto Sans CJK SC", "Noto Sans CJK JP", "WenQuanYi Zen Hei", "SimHei"):
    if any(f.name == name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams["axes.unicode_minus"] = False


def main(log_path: str, out_path: str) -> int:
    sha = hashlib.sha256(open(log_path, "rb").read()).hexdigest()
    forget = defaultdict(Counter)      # round -> {level: n}
    drift = Counter()                  # round -> n
    msgs = Counter()                   # round -> MSG_DM+MSG_PUBLIC
    sleep = defaultdict(int)           # round -> SLEEP_STARTED n
    for line in open(log_path, encoding="utf-8"):
        e = json.loads(line)
        r, t, p = e.get("round"), e.get("type"), e.get("payload") or {}
        if t == "MEMORY_FORGET":
            forget[r][str(p.get("level"))] += 1
        elif t == "PERSONA_DRIFT":
            drift[r] += 1
        elif t in ("MSG_DM", "MSG_PUBLIC"):
            msgs[r] += 1
        elif t == "SLEEP_STARTED":
            sleep[r] += 1

    rounds = sorted({*forget, *drift, *msgs, *sleep})
    fig, axes = plt.subplots(3, 1, figsize=(13, 10.5), sharex=True)
    fig.suptitle(f"F-2 睡眠—遗忘—人格漂移 时间线  (run={log_path.split('/')[-2]}  log_sha256={sha[:8]}…)",
                 fontsize=13)

    ax = axes[0]
    levels = ["demote", "merge", "drop"]
    colors = {"demote": "#e0a33a", "merge": "#3f7fbf", "drop": "#c0392b"}
    bottom = [0] * len(rounds)
    for lv in levels:
        vals = [forget[r].get(lv, 0) for r in rounds]
        ax.bar(rounds, vals, bottom=bottom, label=lv, color=colors[lv], width=0.85)
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_ylabel("MEMORY_FORGET 条数/回合")
    ax.legend(loc="upper left", fontsize=9)
    ax.set_title("遗忘三级动作（demote 降级 / merge 合并 / drop 删除）", fontsize=11)
    ax.grid(alpha=0.25)

    ax = axes[1]
    ax.bar(rounds, [drift[r] for r in rounds], color="#8e44ad", width=0.85)
    ax.set_ylabel("PERSONA_DRIFT 条数/回合")
    ax.set_title("人格漂移事件（需连续 ≥2 个睡眠窗含候选才发）", fontsize=11)
    ax.grid(alpha=0.25)

    ax = axes[2]
    ax.bar(rounds, [msgs[r] for r in rounds], color="#2e8b57", width=0.85, label="MSG_DM+MSG_PUBLIC/回合")
    ax.set_ylabel("对话条数/回合")
    ax.set_xlabel("round（3 回合=1 时段，12 回合=1 天，night 时段=每第 9/21/33/45/57 回合）")
    for r, n in sorted(sleep.items()):
        ax.axvline(r, color="#c0392b", ls="--", lw=1)
        ax.text(r, ax.get_ylim()[1] * 0.85 if ax.get_ylim()[1] else 1, f"睡眠窗\n{n} 人",
                color="#c0392b", fontsize=8, ha="center")
    ax.set_title("睡眠窗口（night）与对话密度", fontsize=11)
    ax.grid(alpha=0.25)

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out_path, dpi=110)
    print(json.dumps({"log_sha256": sha, "out": out_path, "rounds": len(rounds),
                      "forget_total": {lv: sum(forget[r].get(lv, 0) for r in rounds) for lv in levels},
                      "persona_drift_total": sum(drift.values()),
                      "sleep_windows": {str(k): v for k, v in sorted(sleep.items())}},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
