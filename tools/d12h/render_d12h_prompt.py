#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-H 接线证明之一：两组 prompt 的渲染原文 + sha256（固定输入，逐字落盘）。

- **OFF 组**（k=3/4/5）= T1 基础 prompt（逐字节）⇒ `prompt_fn_sha256` 必须 = `effc14db…`
- **ON 组**（k=0/1/2）= T1 + 开头约束 ⇒ `prompt_fn_sha256` 必须 = D12-F 候选 1 的 `dba68ff3…`

用法（在 `code/` 下）：
    LIFE_PROMPT_D12C_SPECIFIC=1 LIFE_PROMPT_D12E_BESTOF=3 LIFE_PROMPT_D12H_PAIR=3 \
        PYTHONPATH=. python3 ../tools/d12h/render_d12h_prompt.py [--out /tmp/d12h_render.json]
退出码：0 = 全过；3 = 任一不过。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

T1 = "effc14dbffdb6865aa52d9d8adab9db269ab3b92ae9a1a230a22cab6c0ed73f5"
D12F_K1 = "dba68ff390620cd77939456bf02b45cfbefcb6e812015f2d2759bd5d56b5b1e6"


def _sha(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    from orchestration.integration import build_world  # noqa: E402
    from life.agent import LifeLayerAgent as A  # noqa: E402

    w = build_world(seed=42, n=2)
    ag = w["agents"][0]
    pid = ag.agent_id
    partner = [p for p in ag.peers if p != pid][0]
    dlg0 = ag._dialogue_prompt("gift", [pid, partner])
    rep0 = ag._reply_prompt(partner, "gift", [(partner, f"{partner}：来，尝尝这个。")])

    on_d, on_r = dlg0 + A.D12H_ON_SUFFIX, rep0 + A.D12H_ON_SUFFIX
    groups = {
        "on": {"k": [0, 1, 2],
               "suffix": A.D12H_ON_SUFFIX,
               "dialogue_prompt": on_d, "reply_prompt": on_r,
               "sha256_dialogue": _sha(on_d), "sha256_reply": _sha(on_r),
               "prompt_fn_sha256": _sha(on_d + "\n===\n" + on_r)},
        "off": {"k": [3, 4, 5],
                "suffix": "",
                "dialogue_prompt": dlg0, "reply_prompt": rep0,
                "sha256_dialogue": _sha(dlg0), "sha256_reply": _sha(rep0),
                "prompt_fn_sha256": _sha(dlg0 + "\n===\n" + rep0)},
    }
    out = {
        "env": {k: os.environ.get(k) for k in
                ("LIFE_PROMPT_D12C_SPECIFIC", "LIFE_PROMPT_D12E_BESTOF", "LIFE_PROMPT_D12H_PAIR")},
        "d12c_on": bool(ag._d12c_on()),
        "d12e_m": A._d12e_m(),
        "d12h_on": A._d12h_on(),
        "legacy_d12c_sha": _sha(dlg0 + "\n===\n" + rep0),
        "groups": groups,
    }
    txt = json.dumps(out, ensure_ascii=False, indent=2)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(txt + "\n")
    print(txt)

    ok1 = groups["on"]["prompt_fn_sha256"] == D12F_K1
    ok2 = groups["off"]["prompt_fn_sha256"] == T1
    ok3 = groups["on"]["prompt_fn_sha256"] != groups["off"]["prompt_fn_sha256"]
    print(f"[{'PASS' if ok1 else 'FAIL'}] ① ON 组 prompt_fn_sha256 == D12-F 候选1(dba68ff3…)："
          f"{groups['on']['prompt_fn_sha256']}", file=sys.stderr)
    print(f"[{'PASS' if ok2 else 'FAIL'}] ② OFF 组 prompt_fn_sha256 == T1(effc14db…)："
          f"{groups['off']['prompt_fn_sha256']}", file=sys.stderr)
    print(f"[{'PASS' if ok3 else 'FAIL'}] ③ 两组 sha 不同（唯一差别是那一行开头约束）", file=sys.stderr)
    return 0 if (ok1 and ok2 and ok3) else 3


if __name__ == "__main__":
    sys.exit(main())
