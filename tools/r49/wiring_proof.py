#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R49 接线预检：证明 `HITT_D12_DETAIL` 真的接进了 `_dialogue_prompt` / `_reply_prompt`。

镜像 `tools/d9/prompt_fn_sha.py`（那份把 env 名写死为 `HITT_D12_PREFWORD`），
本脚本只把 env 名换成 `HITT_D12_DETAIL`，不改任何渲染逻辑：
  * OFF 态（env 未设）与 ON 态（=1）渲染出的 prompt sha 必须**不同**，否则 exit 3；
  * 输出可直接粘进 `switch_proof.txt`。
只读、零 LLM、零跑批。

用法:
  python3 tools/r49/wiring_proof.py --code-root code [--out v2/evidence/<dir>/wiring_proof.txt]
退出码：0 接线成功；2 渲染失败；3 两态相同（未接线）
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import os
import sys
from pathlib import Path

ENV_VAR = "HITT_D12_DETAIL"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _render(code_root: str) -> dict:
    sys.path.insert(0, code_root)
    for m in [k for k in list(sys.modules) if k.split(".")[0] in ("life", "engine", "orchestration")]:
        sys.modules.pop(m, None)

    from life.agent import LifeLayerAgent  # noqa: E402
    from life.persona import load_personas  # noqa: E402
    from life.dialogue_threads import DEFAULTS as DT_DEFAULTS  # noqa: E402

    personas = load_personas(Path(code_root) / "config" / "personas.json")
    pid = sorted(personas)[0]
    other = sorted(personas)[1] if len(personas) > 1 else pid
    names = {pid: "老周", other: "秀娘"}

    def _mk():
        a = object.__new__(LifeLayerAgent)
        a.agent_id = pid
        a.persona = personas[pid]
        a.peers = [other]
        a._peer_names = names
        a._rel_cache = {(other, "familiarity"): 20, (other, "affinity"): 5}
        a.needs = {"energy": 55, "satiety": 60, "social": 40, "esteem": 50, "mastery": 50, "leisure": 45}
        a._rifts = {}
        a._rifts_seen = set()
        a._thread_replied_turn = {}
        a._goals_set_weeks = set()
        return a

    cfg = dict(DT_DEFAULTS)
    history = [(other, f"{names[other]}：show me")]

    out = {}
    for state in ("off", "on"):
        if state == "on":
            os.environ[ENV_VAR] = "1"
        else:
            os.environ.pop(ENV_VAR, None)
        a = _mk()
        d = a._dialogue_prompt("rel_maintain", [pid, other], cfg)
        r = a._reply_prompt(other, "rel_maintain", history, cfg)
        out[state] = {
            "dialogue_prompt_sha256": _sha(d),
            "reply_prompt_sha256": _sha(r),
            "detail_line_len_on": len(LifeLayerAgent._d12_detail_line()),
        }
    os.environ.pop(ENV_VAR, None)

    src = (
        inspect.getsource(LifeLayerAgent._dialogue_prompt)
        + inspect.getsource(LifeLayerAgent._reply_prompt)
        + inspect.getsource(LifeLayerAgent._d12_detail_line)
    )
    out["prompt_fn_source_sha256"] = _sha(src)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code-root", required=True)
    ap.add_argument("--out", default="", help="把输出同时落盘（switch_proof 片段）")
    a = ap.parse_args(argv)
    try:
        res = _render(os.path.abspath(a.code_root))
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] 渲染失败: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    lines = [
        f"env_var={ENV_VAR}",
        f"prompt_fn_source_sha256={res['prompt_fn_source_sha256']}  (两态相同，属预期：源码含分支)",
        f"OFF_dialogue_prompt_sha256={res['off']['dialogue_prompt_sha256']}",
        f"ON_dialogue_prompt_sha256={res['on']['dialogue_prompt_sha256']}",
        f"OFF_reply_prompt_sha256={res['off']['reply_prompt_sha256']}",
        f"ON_reply_prompt_sha256={res['on']['reply_prompt_sha256']}",
        f"detail_line_len_on={res['on']['detail_line_len_on']}",
    ]
    same_d = res["off"]["dialogue_prompt_sha256"] == res["on"]["dialogue_prompt_sha256"]
    same_r = res["off"]["reply_prompt_sha256"] == res["on"]["reply_prompt_sha256"]
    verdict = "PASS" if not (same_d or same_r) else "FAIL"
    lines.append(f"wiring_verdict={verdict}")
    text = "\n".join(lines)
    print(text)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text + "\n", encoding="utf-8")
    if same_d or same_r:
        print("[FAIL] 开关两态渲染出的 prompt 相同 ⇒ 开关**没有**接进提示词", file=sys.stderr)
        return 3
    print("[PASS] 两态 prompt 不同 ⇒ 开关已接进提示词")
    return 0


if __name__ == "__main__":
    sys.exit(main())
