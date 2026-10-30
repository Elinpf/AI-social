#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D9n 仪器自测：在历史 ON 日志上逐项复现 lexicon 的 baseline_reference。

运行：
    cd <repo> && PYTHONPATH=code python3 tools/d9n/test_narration_family.py
    # 或 pytest
    cd <repo> && PYTHONPATH=code python3 -m pytest tools/d9n/test_narration_family.py -q

断言分三组：
  T1 词表结构（规模/顺序/无重复）—— 与冻结件一致；
  T2 基线复现（blocks/msgs/density/动词计数/族 spot-check/max_exact_dup/max_v/max_k）；
  T3 coverage & unassigned 的**已知不同源**（闭表 40/205 vs V_judge 66/205）——
     显式锁住真实值，避免未来有人把 40/205 当 V_judge 口径继续用（详见 GOLDEN.md §6）。
  T4 示例序列生成器：与实现件逐点一致、确定性、seed 回落。
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "code"))

import narration_family as NF  # noqa: E402

LEX_PATH = HERE / "narration_family_lexicon.json"
ON_LOG = REPO / "v2" / "evidence" / "narr-on-20261030" / "run.jsonl"

_CACHE = {}


def _lex():
    if "lex" not in _CACHE:
        lex = NF.load_lexicon(LEX_PATH)
        lex["_sha256"] = NF.sha256_file(LEX_PATH)
        lex["_path"] = str(LEX_PATH)
        _CACHE["lex"] = lex
    return _CACHE["lex"]


def _judgement():
    if "j" not in _CACHE:
        _CACHE["j"] = NF.analyse(ON_LOG, _lex())
    return _CACHE["j"]


# ---------------------------------------------------------------- T1 词表结构
def test_lexicon_structure():
    lex = _lex()
    assert len(lex["verbs_closed_8"]) == 8
    assert len(lex["verbs_rotation_13"]) == 13
    assert len(lex["parts_6"]) == 6
    assert len(lex["objs_13"]) == 13
    assert lex["verbs_closed_8"] == ["蹭", "搓", "抹", "擦", "拂", "拍", "抿", "揉"]
    assert lex["parts_6"] == ["手背", "指腹", "指头", "手指", "手", "肩"]
    assert NF.v_judge(lex) == lex["verbs_closed_8"] + lex["verbs_rotation_13"]
    assert len(NF.v_judge(lex)) == 21
    # 介词不得入表（R7）
    for w in ("把", "往", "上", "了"):
        assert w not in NF.v_judge(lex)


def test_lexicon_sha_recorded():
    """lexicon 文件 sha256 必须与 GOLDEN.md 记录值一致。

    GOLDEN.md 是「仪器身份」的唯一记录点：换了尺子就必须同步改 GOLDEN.md，
    否则本断言红 ⇒ 尺子漂移不可能静默通过（比在代码里再钉一个副本更不易腐坏）。
    """
    txt = (HERE / "GOLDEN.md").read_text(encoding="utf-8")
    row = [l for l in txt.splitlines() if "narration_family_lexicon.json" in l and "`" in l]
    assert row, "GOLDEN.md 缺 lexicon sha256 记录行"
    # 行形如：| `tools/d9n/...json`（说明） | `<64 位 sha256>` |  ⇒ 取最后一个反引号内的值
    recorded = row[0].rstrip().rstrip("|").split("`")[-2].strip()
    assert len(recorded) == 64, recorded
    assert NF.sha256_file(LEX_PATH) == recorded


# ---------------------------------------------------------------- T2 基线复现
def test_baseline_blocks_and_msgs():
    j = _judgement()
    assert j["blocks_total"] == 205
    assert j["msgs_total"] == 191
    assert j["density"] == 1.073298
    assert j["guards"]["sample_ok"] is True


def test_baseline_closed8_verb_counts():
    j = _judgement()
    ref = _lex()["baseline_reference"]["verb_counts"]
    for v, c in ref.items():
        assert j["verb_counts"][v] == c, (v, j["verb_counts"][v], c)


def test_baseline_family_spot_checks():
    j = _judgement()
    fam = {f["family"]: f for f in j["families_b"]}
    ref = {s["family"]: s for s in _lex()["baseline_reference"]["family_spot_checks"]}
    for name, s in ref.items():
        assert fam[name]["total"] == s["total"], name
        assert fam[name]["by_agent"] == s["by_agent"], name
        if "n_ge2_agents" in s:
            assert fam[name]["n_ge2"] == s["n_ge2_agents"], name
    # (b1) 62.5% 这一档（exp-designer 冻结口径：parts_6 单列指头）
    assert j["b1"]["max"]["family"] == "蹭|手"
    assert j["b1"]["max"]["share"] == 0.625
    assert j["b1"]["max"]["count"] == 5
    assert j["b1"]["max"]["total"] == 8


def test_baseline_a_d_e():
    j = _judgement()
    assert j["max_exact_dup"] == 3
    assert j["max_v"] == {"value": 31, "verb": "蹭"}
    assert j["max_k"] == 2
    assert j["e_dist"] == {"0": 12, "1": 153, "2": 26}


def test_baseline_verdicts_three_state():
    """基线三态：a/b1/b2′/d 失败，c-1 成立，c-2 恒不可判，e 成立。"""
    v = _judgement()["verdicts"]
    assert v["a_exact_dup"] == "失败"
    assert v["b1_share"] == "失败"
    assert v["b2p"] == "失败"
    assert v["c1_density"] == "成立"
    assert v["c2_bite"] == "不可判"
    assert v["d_max_v"] == "失败"
    assert v["e_max_k"] == "成立"


# --------------------------------------------- T3 coverage / unassigned 不同源
def test_coverage_under_v_judge_is_66_of_205():
    """R2（V_judge=21）下实测 coverage = 66/205；lexicon 的 40/205 是闭表 8 遗留值。

    该差异为 v1.0 缺陷，已由 leader 裁决「按同口径重算（构成收紧）」并由 exp-designer
    在 lexicon v1.1 / 增补 06 中修正（GOLDEN.md §6）。此处显式锁真实值，
    防止未来把 40/205 当作 V_judge 口径继续使用。
    """
    j = _judgement()
    assert j["coverage"] == {"assigned": 66, "blocks_total": 205, "rate": 0.321951}
    assert j["unassigned_verb_rate"] == 0.678049
    # 闭表口径的 40/205 仍可由 verb_counts 复算出来（两者都不许写错）
    closed_hits = sum(1 for b in _all_inners()
                      if any(v in b for v in _lex()["verbs_closed_8"]))
    assert closed_hits == 40
    # lexicon v1.1 起：baseline_reference.coverage 已改为同口径 66/205（增补 06 修正）
    assert _lex()["baseline_reference"]["coverage"]["assigned"] == 66
    assert _lex()["baseline_reference"]["coverage"]["rate"] == 0.321951
    # 两条守卫在当前门限下都通过（缺陷不改变基线三态）
    assert j["guards"]["coverage_ok"] is True
    assert j["guards"]["unassigned_ok"] is True


def _all_inners():
    if "inners" not in _CACHE:
        msgs = NF.extract_messages(NF.read_log(ON_LOG))
        _CACHE["inners"] = [b[1:-1] for m in msgs for b in NF.PAIRED_RE.findall(m.get("body") or "")]
    return _CACHE["inners"]


def test_guard_thresholds_come_from_lexicon():
    lex = _lex()
    j = _judgement()
    assert j["guards"]["coverage_threshold_abs"] == lex["guards"]["coverage_guard"]["threshold_abs"]
    assert j["guards"]["unassigned_threshold_abs"] == \
        lex["guards"]["unassigned_rate_guard"]["threshold_abs"]


# ------------------------------------------------------ T4 示例序列生成器
def _seq_mod():
    if "seq" not in _CACHE:
        spec = importlib.util.spec_from_file_location(
            "narration_example_seq", HERE / "narration_example_seq.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _CACHE["seq"] = m
    return _CACHE["seq"]


def test_example_seq_matches_implementation():
    from life.agent import narration_example
    seq = _seq_mod()
    ex, _src = seq.load_examples()
    assert len(ex) >= 6
    old = os.environ.pop("HITT_WORLD_SEED", None)
    try:
        for seed in ("0", "42", "7"):
            os.environ["HITT_WORLD_SEED"] = seed   # 实现件从 env 取 seed，两边必须同源
            for a in ("P003", "P007"):
                for r in range(24):
                    for k in ("initiate", "reply"):
                        assert seq.pick(k, a, r, seed, ex) == narration_example(k, a, r)
    finally:
        if old is not None:
            os.environ["HITT_WORLD_SEED"] = old


def test_example_seq_deterministic_and_seed_sensitive():
    seq = _seq_mod()
    ex, _ = seq.load_examples()
    a = [seq.pick("initiate", "P003", r, "0", ex) for r in range(24)]
    b = [seq.pick("initiate", "P003", r, "0", ex) for r in range(24)]
    assert a == b
    assert len(set(a)) >= 2                     # 非常数指派
    c = [seq.pick("initiate", "P003", r, "42", ex) for r in range(24)]
    assert a != c                                # 随 seed 变


def test_example_seq_seed_default_fallback():
    seq = _seq_mod()
    ex, _ = seq.load_examples()
    old = os.environ.pop("HITT_WORLD_SEED", None)
    try:
        unset = [seq.pick("reply", "P003", r, None, ex) for r in range(8)]
        assert seq.resolve_seed(None) == "0"
        os.environ["HITT_WORLD_SEED"] = ""
        assert [seq.pick("reply", "P003", r, None, ex) for r in range(8)] == unset
        os.environ["HITT_WORLD_SEED"] = "0"
        assert [seq.pick("reply", "P003", r, None, ex) for r in range(8)] == unset
    finally:
        os.environ.pop("HITT_WORLD_SEED", None)
        if old is not None:
            os.environ["HITT_WORLD_SEED"] = old


def test_example_seq_no_wallclock_no_random():
    """静态检查：生成器不得出现 random / time / datetime 调用。"""
    src = (HERE / "narration_example_seq.py").read_text(encoding="utf-8")
    for bad in ("import random", "import time", "datetime.now", "time.time", "random."):
        assert bad not in src, bad


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                fails += 1
                print(f"FAIL {name}: {exc}")
    print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAILED'}")
    sys.exit(1 if fails else 0)
