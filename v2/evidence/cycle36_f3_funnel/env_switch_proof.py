#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R32 · `content_clause` 开关的**纯管道**证据（零 LLM、零网络、零跑批）。

三件事，逐条可复算（仓库根执行）：

    python3 v2/evidence/cycle36_f3_funnel/env_switch_proof.py

A. **管道等价**：把当前 `code/life/emotion_echo.py` 里新增的 3 行 env 逻辑**用正则摘掉**
   造一个「参照实现」（= 加 env 口之前的版本），在 `env 未设` 的前提下，
   对 3 组配置（默认文件 / content_clause=false / content_clause=true）比较
   `load_params()` 的**完整 dict**：必须逐键相等（等价性证明，不是"看起来一样"）。
B. **开关生效（双向）**：`HITT_ECHO_CONTENT_CLAUSE` 取 11 个值（含未设、空串、拼错），
   打印 `content_clause` 的解析结果 —— 只有 1/true/on/yes 开，其余全关，未设保持 True。
C. **判读差异（同一 fixture，env=1 vs env=0）**：用 CYCLE-34 ON 臂两条真实样本，
   打印 `verify()` 的 `first_clause / has_cue / ack_then_switch / adopted` 对照，
   并给 `prompt_line()` 是否多出「口径说明」那一行 —— 明确 `content_clause` **不止**影响
   `verify()`（提示词与 `need_rewrite()` 也随口径走，报告须披露）。
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(ROOT, "code", "life", "emotion_echo.py")
sys.path.insert(0, os.path.join(ROOT, "code"))

ENV = "HITT_ECHO_CONTENT_CLAUSE"
#: 与 `code/life/tests/test_f3_echo_struct_r31.py::NEG_TEXT` 同一句（有文本情绪证据 ⇒ 能产计划）
NEG_TEXT = "今天真是累，心里挺委屈"
#: 加 env 口之前那 4 行（摘掉即得参照实现）：注释 + 判断 + 赋值
_ENV_BLOCK = re.compile(
    r"\n(?P<indent>[ ]+)# R32 消融口：\*\*未设 env 时逐字不动\*\*"
    r"[\s\S]*?out\[\"content_clause\"\] = env_cc\.strip\(\)\.lower\(\) in \([^)]*\)\n")


def load_module(name: str, path: str):
    """按 `life.<name>` 的包内身份加载，才能解析 `from . import emotion`（相对导入）。"""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    mod.__package__ = name.rsplit(".", 1)[0]
    spec.loader.exec_module(mod)
    return mod


def reference_source() -> str:
    src = open(SRC, encoding="utf-8").read()
    out, n = _ENV_BLOCK.subn("\n", src)
    assert n == 1, f"env 块定位失败（subn={n}），拒绝给出假证据"
    return out


def main() -> int:
    cur = load_module("life.emotion_echo_cur", SRC)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as f:
        f.write(reference_source())
        ref_path = f.name
    ref = load_module("life.emotion_echo_ref", ref_path)
    os.unlink(ref_path)

    print("=" * 78)
    print("A. 管道等价（env 未设 ⇒ 与加 env 口之前的实现逐键相等）")
    print("=" * 78)
    os.environ.pop(ENV, None)
    with open(os.path.join(ROOT, "code", "config", "emotion_echo.json"), encoding="utf-8") as f:
        base_cfg = json.load(f)
    fixtures = []
    d = tempfile.mkdtemp()
    for tag, patch in (("default(no cfg)", None),
                       ("cfg:content_clause=false", {"content_clause": False}),
                       ("cfg:content_clause=true", {"content_clause": True})):
        if patch is None:
            fixtures.append((tag, None))
            continue
        cfg = {**base_cfg, **patch}
        p = os.path.join(d, tag.replace(":", "_") + ".json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        fixtures.append((tag, p))
    eq_all = True
    for tag, path in fixtures:
        a = ref.load_params(path)
        b = cur.load_params(path)
        same = json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
        eq_all &= same
        print(f"  [{ 'OK ' if same else 'DIFF' }] {tag:26s} content_clause={b['content_clause']} "
              f"enabled={b['enabled']} identical={same}")
        if not same:
            for k in sorted(a):
                if a[k] != b.get(k):
                    print(f"         diff {k}: ref={a[k]!r} cur={b.get(k)!r}")
    print(f"  ⇒ 三组配置全部逐键相等: {eq_all}")

    print()
    print("=" * 78)
    print("B. env 双向解析（只有 1/true/on/yes 开；未设 = 默认 True；其它任何取值 = 关）")
    print("=" * 78)
    cases = [(None, "（未设）"), ("1", "1"), ("true", "true"), ("TRUE", "TRUE"),
             ("on", "on"), ("Yes", "Yes"), ("0", "0"), ("false", "false"),
             ("off", "off"), ("no", "no"), ("", "（空串）"), ("enable", "拼错 enable")]
    ok_parse = True
    for val, label in cases:
        if val is None:
            os.environ.pop(ENV, None)
        else:
            os.environ[ENV] = val
        cur.reload()
        got = cur.load_params()["content_clause"]
        want = True if val is None else val.strip().lower() in ("1", "true", "on", "yes")
        ok_parse &= (got == want)
        print(f"  {label:14s} → content_clause={str(got):5s} 期望={str(want):5s} "
              f"{'OK' if got == want else 'FAIL'}")
    os.environ.pop(ENV, None)
    cur.reload()
    print(f"  ⇒ 全部符合规格: {ok_parse}")

    print()
    print("=" * 78)
    print("C. 同一 fixture，env=1 vs env=0（判读差异 + 提示词差异，供报告披露）")
    print("=" * 78)
    samples = [
        ("CYCLE-34 msg_uid=42:2141", "嗯，你压腿压得高兴就好。我这儿正把上月那沓对账单摊在柜台上。", "月牙"),
        ("CYCLE-34 msg_uid=42:1198", "巧儿，你拿废木条练榫头，我听着就踏实。我来搭把手。", "巧儿"),
        ("对照：第一段就是实质内容", "你这话听着就累，先坐下歇会儿。", "阿禾"),
    ]
    plan_params = {**cur.DEFAULTS, "enabled": True}
    rows = []
    for label, body, name in samples:
        row = {"sample": label, "arms": {}}
        for env_val, arm in (("1", "content_clause=ON"), ("0", "content_clause=OFF")):
            os.environ[ENV] = env_val
            cur.reload()
            plan = cur.plan("低落", NEG_TEXT, plan_params)
            plan["name"] = name
            v = cur.verify(body, plan)
            block = cur.prompt_line(plan, name)
            row["arms"][arm] = {
                "content_clause": cur.load_params()["content_clause"],
                "first_clause": v["first_clause"],
                "first_clause_raw": v["first_clause_raw"],
                "has_cue": v["has_cue"], "has_ref": v["has_ref"],
                "ack_then_switch": v["ack_then_switch"], "adopted": v["adopted"],
                "need_rewrite": cur.need_rewrite(v),
                "prompt_has_definition_line": "第一个有实质内容的分句" in block,
                "prompt_len": len(block),
            }
        rows.append(row)
    os.environ.pop(ENV, None)
    cur.reload()
    for row in rows:
        print(f"  · {row['sample']}")
        for arm, d in row["arms"].items():
            print(f"      {arm:20s} first_clause={d['first_clause']!r:14s} "
                  f"has_cue={d['has_cue']!s:5s} ack_switch={d['ack_then_switch']!s:5s} "
                  f"adopted={d['adopted']!s:5s} need_rewrite={d['need_rewrite']!s:5s} "
                  f"definition_line={d['prompt_has_definition_line']}")
    out = {"env": ENV, "A_pipeline_equivalence": eq_all, "B_env_parsing": ok_parse,
           "C_fixture_diff": rows,
           "note": "content_clause 不只影响 verify()：prompt_line() 多一行口径说明、"
                   "need_rewrite() 触发率随口径变化 ⇒ 两臂 llm_calls 的 echo_rewrite 分块预期不等。"}
    with open(os.path.join(HERE, "env_switch_proof.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print()
    print("written:", os.path.join(HERE, "env_switch_proof.json"))
    return 0 if (eq_all and ok_parse) else 1


if __name__ == "__main__":
    sys.exit(main())
