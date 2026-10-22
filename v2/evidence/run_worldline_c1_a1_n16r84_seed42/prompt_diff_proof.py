#!/usr/bin/env python3
"""C-1 单变量「提示词差异」自证（离线、确定性、可复算）。

用途：证明在 af1dffc 这份代码上，`LIFE_PROMPT_WORLD_C1` OFF→ON 的**唯一**影响就是
在两个对话提示词里插入**一行**处境，其余部分逐字节不变。

做法：直接复用仓内单测 `tests/test_world_c1_prompt_single_variable.py` 的构造器
（`_agent` / `_wv` / `_live_events`），避免另写一套与生产不一致的装配。

复算：
    cd <REPO>/.worktrees/worldline-c1-n16r84/code
    PYTHONDONTWRITEBYTECODE=1 python3 \
      <REPO>/v2/evidence/run_worldline_c1_a1_n16r84_seed42/prompt_diff_proof.py <REPO>/.worktrees/worldline-c1-n16r84/code
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main() -> int:
    code_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    os.chdir(code_dir)
    sys.path.insert(0, str(code_dir))

    # 载入单测模块（复用其装配，不复制生产逻辑）
    test_path = code_dir / "tests" / "test_world_c1_prompt_single_variable.py"
    spec = importlib.util.spec_from_file_location("wc1_test", test_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    code_sha = subprocess.check_output(
        ["git", "-C", str(code_dir), "rev-parse", "HEAD"], text=True).strip()
    print(f"code_sha={code_sha}")
    print(f"test_module={test_path}")
    print(f"switch_env=LIFE_PROMPT_WORLD_C1")

    tmpdir = Path(tempfile.mkdtemp(prefix="wc1_promptdiff_"))
    agent = mod._agent(tmpdir)
    wv = mod._wv(mod._live_events())
    ENV = mod.WORLD_C1_ENV

    os.environ.pop(ENV, None)
    assert mod.world_c1_enabled() is False
    d_off = agent._dialogue_prompt(mod.TID, [mod.SELF_ID, mod.PARTNER_ID], wv=wv)
    r_off = agent._reply_prompt(mod.PARTNER_ID, mod.TID, mod.HISTORY, wv=wv)
    seg_off = agent._world_line(wv)

    os.environ[ENV] = "1"
    assert mod.world_c1_enabled() is True
    seg_on = agent._world_line(wv)
    d_on = agent._dialogue_prompt(mod.TID, [mod.SELF_ID, mod.PARTNER_ID], wv=wv)
    r_on = agent._reply_prompt(mod.PARTNER_ID, mod.TID, mod.HISTORY, wv=wv)
    os.environ.pop(ENV, None)

    print()
    print("== OFF 臂（生产默认：变量不存在）==")
    print(f"_world_line={seg_off!r}")
    print(f"dialogue_prompt sha256={sha(d_off)} len={len(d_off)} lines={d_off.count(chr(10))+1}")
    print(f"reply_prompt    sha256={sha(r_off)} len={len(r_off)} lines={r_off.count(chr(10))+1}")

    print()
    print("== ON 臂（LIFE_PROMPT_WORLD_C1=1）==")
    print(f"_world_line={seg_on!r}")
    print(f"dialogue_prompt sha256={sha(d_on)} len={len(d_on)} lines={d_on.count(chr(10))+1}")
    print(f"reply_prompt    sha256={sha(r_on)} len={len(r_on)} lines={r_on.count(chr(10))+1}")

    print()
    print("== 单变量断言 ==")
    ok1 = seg_off == ""
    ok2 = seg_on.replace("\n", "", 1) != "" and seg_on.count("\n") == 1
    ok3 = d_on.replace(seg_on, "", 1) == d_off
    ok4 = r_on.replace(seg_on, "", 1) == r_off
    ok5 = (d_on.count("\n") + 1) - (d_off.count("\n") + 1) == 1
    ok6 = (r_on.count("\n") + 1) - (r_off.count("\n") + 1) == 1
    print(f"A. OFF ⇒ _world_line 为空串                 : {ok1}")
    print(f"B. ON  ⇒ 插入段恰一行（含 1 个换行）        : {ok2}")
    print(f"C. ON._dialogue_prompt 去掉插入段 == OFF     : {ok3}")
    print(f"D. ON._reply_prompt    去掉插入段 == OFF     : {ok4}")
    print(f"E. dialogue 行数 +1                          : {ok5}")
    print(f"F. reply    行数 +1                          : {ok6}")
    print()
    print("== 被插入的那一行（ON 唯一增量）==")
    print(seg_on.lstrip("\n"))
    allok = all([ok1, ok2, ok3, ok4, ok5, ok6])
    print()
    print(f"VERDICT={'PASS' if allok else 'FAIL'} single_variable_prompt_diff")
    return 0 if allok else 1


if __name__ == "__main__":
    raise SystemExit(main())
