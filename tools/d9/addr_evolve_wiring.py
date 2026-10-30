#!/usr/bin/env python3
"""addr_evolve_wiring.py — N-15 接线预检（M2 静态层 + 预登记 §8.3 L1 的 OFF==基线 逐字节）。

**为什么新写**：`tools/d9/prompt_fn_sha.py` 的开关被**硬编码**为 `HITT_D12_PREFWORD` + `_d12_prefword_line`
（见其 `:66`/`:85`），且 `--help` 只有 `--code-root` / `--exit-on-same` ⇒ 不能用来证明 N-15 的接线
（预登记 §8.1 已写死「必须新增」）。

## 三个断言（全过才 rc=0）

| # | 断言 | 对应预登记 |
|---|---|---|
| `A1` | 当前树 **OFF** 的 `dialogue_prompt` sha256 **==** 未改动基线树 **OFF** 的 `dialogue_prompt` sha256（逐字节） | §8.3 **L1** / 判定格 `J-9` |
| `A2` | 当前树 **ON** 的 `dialogue_prompt` sha256 **!=** 当前树 **OFF** | §8.2 **M2** |
| `A3` | `reply_prompt` 的 **OFF == ON**（证明「只注入 `_dialogue_prompt`」这条单变量约束没被破坏） | §8.1 |

## 用法

```bash
python3 tools/d9/addr_evolve_wiring.py --code-root code --baseline-root .worktrees/n15-baseline/code
# 退出码：0 全过；2 导入/渲染失败；3 断言失败
```
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import os
import sys


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _render(code_root: str) -> dict:
    """在给定代码树里渲染 `_dialogue_prompt` / `_reply_prompt` 的 OFF / ON 两态。"""
    sys.path.insert(0, code_root)
    for m in [k for k in list(sys.modules) if k.split(".")[0] in ("life", "engine", "orchestration")]:
        sys.modules.pop(m, None)
    # 清掉 `tools/` 里可能被同名模块污染的路径项
    sys.path = [p for p in sys.path if os.path.abspath(p) != os.path.abspath(code_root)] or sys.path
    sys.path.insert(0, code_root)

    from pathlib import Path                       # noqa: E402
    from life.agent import LifeLayerAgent          # noqa: E402
    from life.persona import load_personas         # noqa: E402
    from life.dialogue_threads import DEFAULTS as DT_DEFAULTS  # noqa: E402
    from life import agent as agent_mod            # noqa: E402

    env_name = getattr(agent_mod, "ADDR_EVOLVE_ENV", None)
    line = getattr(agent_mod, "ADDR_EVOLVE_LINE", "")

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

    out = {"code_root": os.path.abspath(code_root), "env_name": env_name,
           "addr_evolve_line": line, "addr_evolve_line_sha256": _sha(line) if line else None,
           "switch_implemented": env_name is not None}
    for state in ("off", "on"):
        if env_name is None:
            # 基线树里开关物理上不存在（这正是要证明的「ON 前基线」）：只渲染 OFF 态
            if state == "on":
                out["on"] = None
                break
        elif state == "on":
            os.environ[env_name] = "1"
        else:
            os.environ.pop(env_name, None)
        a = _mk()
        d = a._dialogue_prompt("rel_maintain", [pid, other], cfg)
        r = a._reply_prompt(other, "rel_maintain", history, cfg)
        out[state] = {"dialogue_prompt": d, "reply_prompt": r,
                      "dialogue_prompt_sha256": _sha(d), "reply_prompt_sha256": _sha(r)}
    if env_name is not None:
        os.environ.pop(env_name, None)

    out["prompt_fn_source_sha256"] = _sha(
        inspect.getsource(LifeLayerAgent._dialogue_prompt)
        + inspect.getsource(LifeLayerAgent._reply_prompt)
    )
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="N-15 称呼演化臂接线预检")
    ap.add_argument("--code-root", default="code", help="待检代码树（含 life/ 的 code 目录）")
    ap.add_argument("--baseline-root", required=True,
                    help="未改动基线树的 code 目录（同 commit 的 worktree）")
    a = ap.parse_args(argv)

    try:
        cur = _render(os.path.abspath(a.code_root))
        base = _render(os.path.abspath(a.baseline_root))
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] 渲染失败: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(f"[info] 当前树       : {cur['code_root']}")
    print(f"[info] 基线树       : {base['code_root']}")
    print(f"[info] 开关变量名   : {cur['env_name']}")
    print(f"[info] 注入行 sha256: {cur['addr_evolve_line_sha256']}")
    print(f"[info] 注入行原文   : {cur['addr_evolve_line']!r}")
    print(f"[info] 当前树 prompt_fn 源码 sha256 = {cur['prompt_fn_source_sha256']}")
    print(f"[info] 基线树 prompt_fn 源码 sha256 = {base['prompt_fn_source_sha256']}（与当前树不同属预期：含新增 if 分支）")
    print("")
    print(f"当前树 OFF dialogue_prompt sha256 = {cur['off']['dialogue_prompt_sha256']}")
    print(f"当前树 ON  dialogue_prompt sha256 = {cur['on']['dialogue_prompt_sha256'] if cur['on'] else 'n/a（基线树无开关）'}")
    print(f"基线树 OFF dialogue_prompt sha256 = {base['off']['dialogue_prompt_sha256']}")
    print(f"当前树 OFF reply_prompt    sha256 = {cur['off']['reply_prompt_sha256']}")
    print(f"当前树 ON  reply_prompt    sha256 = {cur['on']['reply_prompt_sha256'] if cur['on'] else 'n/a'}")
    print("")

    rc = 0
    a1 = cur["off"]["dialogue_prompt_sha256"] == base["off"]["dialogue_prompt_sha256"]
    a2 = bool(cur["on"]) and cur["on"]["dialogue_prompt_sha256"] != cur["off"]["dialogue_prompt_sha256"]
    a3 = bool(cur["on"]) and cur["off"]["reply_prompt_sha256"] == cur["on"]["reply_prompt_sha256"]
    for name, ok, desc in (
        ("A1", a1, "当前树 OFF == 基线树 OFF（逐字节；L1）"),
        ("A2", a2, "当前树 ON != 当前树 OFF（M2：开关已接进提示词）"),
        ("A3", a3, "reply_prompt OFF == ON（只注入 _dialogue_prompt，单变量）"),
    ):
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {desc}")
        if not ok:
            rc = 3

    # 差异尾部可视化（便于人工复核「只多了一行」）
    if a2:
        d_off, d_on = cur["off"]["dialogue_prompt"], cur["on"]["dialogue_prompt"]
        i = 0
        while i < min(len(d_off), len(d_on)) and d_off[i] == d_on[i]:
            i += 1
        print("\n---- 两态首个差异位置 ----")
        print(f"公共前缀长度 = {i}；OFF 余下 = {d_off[i:]!r}")
        print(f"                  ON  余下 = {d_on[i:]!r}")
        print(f"ON 长度 - OFF 长度 = {len(d_on) - len(d_off)} 字符")
    return rc


if __name__ == "__main__":
    sys.exit(main())
