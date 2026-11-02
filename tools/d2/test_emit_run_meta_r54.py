#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R54 回归测试：`switch_effective` 声明值来源（A-2）与冻结区零改动断言（A-3）。

运行：
    cd <repo> && python3 -m pytest tools/d2/test_emit_run_meta_r54.py -q
    # 或直接执行（不依赖 pytest 也能跑）
    cd <repo> && python3 tools/d2/test_emit_run_meta_r54.py

被测对象
--------
* `tools/d2/emit_run_meta.py`   —— `meta.switch_effective` / `meta.assertions.code_unchanged_during_run`
* `tools/d2/arm_switch_table.py` —— 声明值三态 + `declared_switch_from_manifest`
* `tools/d2/frozen_zone_diff.py` —— 冻结区判定（三路证据取「与」）

数据来源（只读、零跑批、零 LLM）
--------------------------------
R53 两臂证据目录 `v2/evidence/r53-schedule-offset-{off,on}-20261102_n16r36_s42/`：
`env_manifest.txt` 里 off 臂是 `HITT_SCHEDULE_OFFSET=<unset>`、on 臂是 `=1`。
测试把真正的 run.jsonl **软链**进临时目录（避免重写证据、也不复制 27MB），
再用 `--out` 把 meta 写到临时目录。

断言分组
--------
T1 A-2：回放 off 臂 ⇒ `HITT_SCHEDULE_OFFSET.effective=off`（声明显式 `<unset>`）；
       回放 on 臂 ⇒ `effective=on` 且 `hits=448`（SCHEDULE_PLANNED.slots 审计键命中）。
T2 A-2：`LIFE_PROMPT_SCENE` 必须在 `switch_effective` 里（旧缺口：键根本不存在）。
T3 A-2：清单里**没出现**的键 ⇒ `declared_known=false`，命中 0 时判 `cannot-verify`
       （不得冒充 `off`）；命中>0 时判 `on`（不得用未知声明值否掉运行期硬证据）。
T4 A-3：正常（无 trap、冻结区相对 code_sha 干净）⇒ `True`；
       构造 trap 里带 `code/life/agent.py` ⇒ `False` 且 reasons 非空、method 含 exit_trap；
       无任何证据（code_sha 不可解析 + 无快照）⇒ `False` + `unverifiable`（**不再是 `null`**）。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import emit_run_meta as EM  # noqa: E402
import arm_switch_table as AST  # noqa: E402
import frozen_zone_diff as FZD  # noqa: E402

EVID = REPO / "v2" / "evidence"
ARM_DIRS = {
    "off": EVID / "r53-schedule-offset-off-20261102_n16r36_s42",
    "on": EVID / "r53-schedule-offset-on-20261102_n16r36_s42",
}
CODE_SHA = "9f592bfaf6f2bf86f5c79731b82193cd9334ceea"  # R53 两臂 meta.code_sha（env_manifest 同值）


# ---------------------------------------------------------------- helpers

def _make_run_dir(tmp: Path, arm: str) -> Path:
    """造一个只读用的 run_dir：run.jsonl 软链 + manifest/起跑快照拷贝。"""
    src = ARM_DIRS[arm]
    dst = tmp / arm
    dst.mkdir(parents=True, exist_ok=True)
    os.symlink(src / "run.jsonl", dst / "run.jsonl")
    for name in ("env_manifest.txt", "git_status_start.txt"):
        if (src / name).exists():
            shutil.copy2(src / name, dst / name)
    return dst


def _replay(tmp: Path, arm: str, extra: list[str] | None = None) -> dict:
    """在临时目录回放一臂，返回生成的 meta（不写进证据目录）。"""
    run_dir = _make_run_dir(tmp, arm)
    out = tmp / f"meta_{arm}.json"
    rc = EM.main(["--run-dir", str(run_dir), "--out", str(out), "--code-sha", CODE_SHA]
                 + (extra or []))
    assert rc == 0, f"emit_run_meta 回放 {arm} 臂失败 rc={rc}"
    return json.loads(out.read_text(encoding="utf-8"))


def _skip_if_missing() -> bool:
    for d in ARM_DIRS.values():
        if not (d / "run.jsonl").exists():
            print(f"[skip] 缺证据目录：{d}", file=sys.stderr)
            return True
    return False


# ---------------------------------------------------------------- T1/T2 A-2

def test_a2_replay_off_arm_schedule_offset_false():
    if _skip_if_missing():
        return
    with tempfile.TemporaryDirectory() as td:
        m = _replay(Path(td), "off")
    eff = m["switch_effective"]["HITT_SCHEDULE_OFFSET"]
    decl = m["switch_declared"]["HITT_SCHEDULE_OFFSET"]
    assert eff["effective"] == "off", eff
    assert eff["hits"] == 0, eff
    assert decl["declared_known"] is True and decl["explicit_unset"] is True, decl
    assert decl["normalized_effective"] is False, decl
    # 声明值来源必须是 env_manifest（不是「今天的 shell 环境」）
    assert m["switch_declared_provenance"]["mode"] == "env_manifest"
    assert m["switch_declared_provenance"]["auto_detected"] is True


def test_a2_replay_on_arm_schedule_offset_true():
    if _skip_if_missing():
        return
    with tempfile.TemporaryDirectory() as td:
        m = _replay(Path(td), "on")
    eff = m["switch_effective"]["HITT_SCHEDULE_OFFSET"]
    decl = m["switch_declared"]["HITT_SCHEDULE_OFFSET"]
    assert decl["raw"] == "1" and decl["normalized_effective"] is True, decl
    assert eff["effective"] == "on", eff
    assert eff["hits"] == 448, eff          # ON 臂 448/448 slots 带 schedule_offset 审计键
    assert eff["evidence_field"].endswith("slots[*].schedule_offset"), eff


def test_a2_life_prompt_scene_key_exists():
    """旧缺口本体：`LIFE_PROMPT_SCENE` 在 switch_effective 里**根本没有键**（不是 null）。"""
    if _skip_if_missing():
        return
    with tempfile.TemporaryDirectory() as td:
        m = _replay(Path(td), "on")
    assert "LIFE_PROMPT_SCENE" in m["switch_effective"], sorted(m["switch_effective"])
    eff = m["switch_effective"]["LIFE_PROMPT_SCENE"]
    assert eff["declared_on"] is True and eff["effective"] == "on", eff
    assert eff["hits"] > 0, eff


# ---------------------------------------------------------------- T3 声明未知

def test_a3_declared_unknown_is_not_off():
    """清单里没登记的键 ⇒ declared_known=false，且融合规则不变冒成 off / contradiction。"""
    manifest = {"path": "mem", "env": {"LIFE_PROMPT_SCENE": "1"},
                "explicit_unset": [], "keys": ["LIFE_PROMPT_SCENE"]}
    st = AST.declared_switch_from_manifest("HITT_WEATHER", manifest)
    assert st["declared_known"] is False
    assert st["declared_state"] == "absent-from-manifest"
    assert AST.fuse_state(0, st["normalized_effective"],
                          declared_known=st["declared_known"]) == "cannot-verify"
    assert AST.fuse_state(7, st["normalized_effective"],
                          declared_known=st["declared_known"]) == "on"


def test_a3_replay_marks_absent_switch_cannot_verify():
    """真实回放里，manifest 未登记的 HITT_WEATHER 不得被记成 off（声明侧未知）。"""
    if _skip_if_missing():
        return
    with tempfile.TemporaryDirectory() as td:
        m = _replay(Path(td), "off")
    eff = m["switch_effective"]["HITT_WEATHER"]
    assert eff["declared_known"] is False, eff
    assert eff["effective"] == "cannot-verify", eff


# ---------------------------------------------------------------- T4 A-3

def test_a3_clean_run_reports_true():
    if _skip_if_missing():
        return
    with tempfile.TemporaryDirectory() as td:
        m = _replay(Path(td), "off")
    assert m["assertions"]["code_unchanged_during_run"] is True
    ev = m["code_unchanged_evidence"]
    assert "git_diff_vs_code_sha" in ev["method"], ev
    assert ev["git_diff_vs_code_sha"] == [], ev
    assert ev["reasons"] == [], ev


def test_a3_trap_with_frozen_zone_change_reports_false():
    """可触发验证：EXIT trap 记录的冻结区改动 ⇒ 断言写 False（不是 null、不静默）。"""
    if _skip_if_missing():
        return
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        run_dir = _make_run_dir(tmp, "off")
        (run_dir / FZD.TRAP_FILE_NAME).write_text(
            "# run_batch EXIT trap at 2026-11-02T04:57:00+08:00 rc=0\n"
            f"code_sha={CODE_SHA}\nrc=0\ncode/life/agent.py\n", encoding="utf-8")
        out = tmp / "meta_off_trap.json"
        rc = EM.main(["--run-dir", str(run_dir), "--out", str(out), "--code-sha", CODE_SHA])
        assert rc == 0
        m = json.loads(out.read_text(encoding="utf-8"))
    assert m["assertions"]["code_unchanged_during_run"] is False, m["assertions"]
    ev = m["code_unchanged_evidence"]
    assert "exit_trap" in ev["method"], ev
    assert ev["exit_trap_diff"] == ["code/life/agent.py"], ev
    assert ev["reasons"], ev


def test_a3_require_code_unchanged_gate_exits_9():
    """硬闸（可选）：有改动时 `--require-code-unchanged` 必须 exit 9。"""
    if _skip_if_missing():
        return
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        run_dir = _make_run_dir(tmp, "on")
        (run_dir / FZD.TRAP_FILE_NAME).write_text(
            f"code_sha={CODE_SHA}\ncode/config/llm.json\n", encoding="utf-8")
        rc = EM.main(["--run-dir", str(run_dir), "--out", str(tmp / "m.json"),
                      "--code-sha", CODE_SHA, "--require-code-unchanged"])
    assert rc == 9, rc


def test_a3_no_evidence_reports_false_unverifiable():
    """没有任何证据时：`False` + `unverifiable`，绝不再写 `null`。"""
    if _skip_if_missing():
        return
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        run_dir = _make_run_dir(tmp, "off")
        # 抹掉起跑快照 + 钉一个不可解析的 sha ⇒ 三路证据全不可用
        (run_dir / "git_status_start.txt").unlink()
        out = tmp / "meta_off_noev.json"
        rc = EM.main(["--run-dir", str(run_dir), "--out", str(out),
                      "--code-sha", "0" * 40])
        assert rc == 0
        m = json.loads(out.read_text(encoding="utf-8"))
    assert m["assertions"]["code_unchanged_during_run"] is False, m["assertions"]
    assert m["code_unchanged_evidence"]["method"] == "unverifiable", m["code_unchanged_evidence"]
    assert m["assertions"]["code_unchanged_during_run"] is not None


if __name__ == "__main__":
    try:
        import pytest
        raise SystemExit(pytest.main([__file__, "-q"]))
    except ImportError:  # 无 pytest 时退化：直接顺序执行所有 test_* 函数
        fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
        fails = 0
        for fn in fns:
            try:
                fn()
                print(f"[ok] {fn.__name__}")
            except Exception as exc:  # noqa: BLE001
                fails += 1
                print(f"[FAIL] {fn.__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1 if fails else 0)
