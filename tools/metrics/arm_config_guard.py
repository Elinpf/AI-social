#!/usr/bin/env python3
"""arm_config_guard.py —— 两臂「配置同源」可执行检查（核验方工具）。

解决的问题
----------
"两臂 `code_sha` 不同 ⇒ 任何差值只是观测、不是因果" 这条纪律，D9 线曾因它**作废过一条结论**，
但一直是**口头纪律**。本工具把它变成一条命令的判定。

为什么不能只看 `config_digest`
------------------------------
实测（D9 线四臂）：`WORLD_INIT.config_digest` **完全相同**（`sha256:58485c06…`），
但其中两臂的 `agent.py` **提示词文本不同**（`05636bc` 0 条禁旁白句 vs `d7d1d93f` 2 条）。
⇒ **`config_digest` 不反映 prompt 差异**，也不反映 env 级 override（如 `LIFE_PROMPT_NARRATION`）。
因此本工具把 `code_sha` 作**主判据**，`fingerprint/config_digest` 仅作**旁证并显式标注局限**。

判定三档（写死）
----------------
* `SAME_CONFIG`      —— 两臂 `code_sha` 相同 **且** provider/model 相同（seed/n/rounds 一并报）
* `DIFFERENT_CODE`   —— `code_sha` 不同（无论 prompt 是否同源）：差值**只能作观测**，且给出 prompt 是否同源
* `CANNOT-VERIFY`    —— `meta.json`/`run.jsonl` 缺失、`code_sha` 缺失，或 `code_sha` 不同但 git 对象不可得（无法比 prompt）

用法
----
    python tools/metrics/arm_config_guard.py --a <armA_dir> --b <armB_dir> [--json out.json] [--no-git]

退出码：SAME_CONFIG=0，DIFFERENT_CODE=2，CANNOT-VERIFY=3（便于流水线分流）。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

#: 收尾指令（提示词尾部追加行）的源码形态：`+ "\n…"`
_PROMPT_TAIL_RE = re.compile(r'\+\s*("\\n[^"]{8,}")')

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_meta(arm_dir: Path) -> dict | None:
    p = arm_dir / "meta.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_world_init(arm_dir: Path) -> dict | None:
    """取首条 WORLD_INIT 的 payload（只读前若干行即返回，避免读满大文件）。"""
    p = arm_dir / "run.jsonl"
    if not p.exists():
        return None
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            if '"WORLD_INIT"' not in line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                return None
            return rec.get("payload") or {}
    return None


def _git_show(rev: str, path: str = "code/life/agent.py") -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "show", f"{rev}:{path}"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout
    except Exception:
        return None


def _prompt_tails(rev: str) -> list[str] | None:
    """取该 commit 里 agent.py 的收尾指令字面量（去掉 `+ ` 前缀，保留运行期形态的原文）。"""
    src = _git_show(rev)
    if src is None:
        return None
    return sorted(m.group(1) for m in _PROMPT_TAIL_RE.finditer(src))


def _summ(m: dict | None, w: dict | None) -> dict:
    m = m or {}
    w = w or {}
    return {
        "code_sha": (m.get("code_sha") or None),
        "provider": m.get("provider"),
        "model": m.get("model"),
        "seed": m.get("seed"),
        "n": m.get("n"),
        "rounds": m.get("rounds"),
        "fingerprint": w.get("fingerprint"),
        "config_digest": w.get("config_digest"),
        "engine_version": w.get("engine_version"),
    }


def analyse(dir_a: str, dir_b: str, use_git: bool = True) -> dict:
    A, B = Path(dir_a), Path(dir_b)
    meta_a, meta_b = _load_meta(A), _load_meta(B)
    wi_a, wi_b = _load_world_init(A), _load_world_init(B)
    sa, sb = _summ(meta_a, wi_a), _summ(meta_b, wi_b)

    missing = []
    if meta_a is None:
        missing.append(f"{A}/meta.json 缺失或不可解析")
    if meta_b is None:
        missing.append(f"{B}/meta.json 缺失或不可解析")
    if wi_a is None:
        missing.append(f"{A}/run.jsonl 无 WORLD_INIT")
    if wi_b is None:
        missing.append(f"{B}/run.jsonl 无 WORLD_INIT")

    code_same = (sa["code_sha"] is not None and sa["code_sha"] == sb["code_sha"])
    prov_same = (sa["provider"] == sb["provider"] and sa["model"] == sb["model"])
    run_params_same = (sa["seed"], sa["n"], sa["rounds"]) == (sb["seed"], sb["n"], sb["rounds"])

    prompt_info: dict = {"compared": False, "same": None, "tails_a": None, "tails_b": None, "diff": None}
    if not code_same and use_git and sa["code_sha"] and sb["code_sha"]:
        ta, tb = _prompt_tails(sa["code_sha"]), _prompt_tails(sb["code_sha"])
        prompt_info.update({
            "compared": (ta is not None and tb is not None),
            "tails_a": ta, "tails_b": tb,
        })
        if ta is not None and tb is not None:
            prompt_info["same"] = (ta == tb)
            prompt_info["diff"] = sorted(set(tb) - set(ta)) + sorted(set(ta) - set(tb))

    # ---- 判定 ----
    if missing or sa["code_sha"] is None or sb["code_sha"] is None:
        verdict = "CANNOT-VERIFY"
        reason = "输入不全：" + ("；".join(missing) if missing else "code_sha 缺失")
    elif code_same:
        if prov_same:
            verdict = "SAME_CONFIG"
            reason = "两臂 code_sha 相同、provider/model 相同"
        else:
            verdict = "CANNOT-VERIFY"
            reason = f"code_sha 相同但 provider/model 不同（{sa['provider']}/{sa['model']} vs {sb['provider']}/{sb['model']}）"
    else:
        if prompt_info["compared"] is None or not prompt_info["compared"]:
            verdict = "CANNOT-VERIFY"
            reason = "code_sha 不同，且 git 对象不可得 ⇒ 无法判 prompt 是否同源"
        else:
            verdict = "DIFFERENT_CODE"
            reason = ("code_sha 不同，prompt **不同源**" if prompt_info["same"] is False
                      else "code_sha 不同，但 prompt 收尾指令**同源**（差异在别处）")

    # ---- 影响一句话 ----
    if verdict == "SAME_CONFIG":
        impact = ("两臂同源：可作对照；但**是否单变量仍取决于 env / 运行时 override**"
                  "（`config_digest` 相同不代表 env 相同）。")
    elif verdict == "DIFFERENT_CODE":
        impact = ("**两臂不同源 ⇒ 任何跨臂差值只能作观测，不得归因于任一变量**；"
                  "以此差值为主结论的件**不可发布、不可作为判据依据**。")
    else:
        impact = "**未确认同源 ⇒ 不得宣称两臂可比**；须先补齐 meta/WORLD_INIT 或提供可比 commit。"

    return {
        "a": {"dir": str(A), **sa},
        "b": {"dir": str(B), **sb},
        "checks": {
            "code_sha_same": code_same,
            "provider_model_same": prov_same,
            "run_params_same": run_params_same,
            "prompt": prompt_info,
            "missing": missing,
        },
        "verdict": verdict,
        "reason": reason,
        "impact": impact,
        "caveat": ("`config_digest` **不反映 prompt 差异与 env override**："
                   "D9 线实测四臂 digest 全同，其中两臂 prompt 不同。故本工具不以 digest 判同源。"),
    }


def render(r: dict) -> str:
    a, b, c = r["a"], r["b"], r["checks"]
    L = []
    L.append("== 臂 A ==")
    L.append(f"  dir={a['dir']}")
    for k in ("code_sha", "provider", "model", "seed", "n", "rounds", "fingerprint", "config_digest", "engine_version"):
        L.append(f"  {k:<14}= {a.get(k)}")
    L.append("== 臂 B ==")
    L.append(f"  dir={b['dir']}")
    for k in ("code_sha", "provider", "model", "seed", "n", "rounds", "fingerprint", "config_digest", "engine_version"):
        L.append(f"  {k:<14}= {b.get(k)}")
    L.append("")
    L.append("== 比对 ==")
    L.append(f"code_sha 相同        : {c['code_sha_same']}")
    L.append(f"provider/model 相同  : {c['provider_model_same']}")
    L.append(f"seed/n/rounds 相同   : {c['run_params_same']}")
    pm = c["prompt"]
    if pm["compared"]:
        L.append(f"prompt 收尾指令同源  : {pm['same']}")
        if pm["same"] is False:
            L.append(f"  A 有 {len(pm['tails_a'])} 条 / B 有 {len(pm['tails_b'])} 条；差异条目（截断 80 字）：")
            for t in (pm["diff"] or [])[:6]:
                L.append(f"    - {t[:80]}")
    else:
        L.append("prompt 收尾指令同源  : 未比较（code_sha 相同 / 或 git 对象不可得）")
    if c["missing"]:
        L.append(f"输入缺失            : {c['missing']}")
    L.append("")
    L.append(f"判定：{r['verdict']}  —— {r['reason']}")
    L.append(f"影响：{r['impact']}")
    L.append(f"注：  {r['caveat']}")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="两臂配置同源检查（code_sha 为主判据）")
    ap.add_argument("--a", required=True, help="臂 A 目录（含 meta.json / run.jsonl）")
    ap.add_argument("--b", required=True, help="臂 B 目录")
    ap.add_argument("--json", default=None, help="结构化结果写到该路径（可选）")
    ap.add_argument("--no-git", action="store_true", help="跳过 git（不比较 prompt）")
    args = ap.parse_args(argv)

    res = analyse(args.a, args.b, use_git=not args.no_git)
    print(render(res))
    if args.json:
        Path(args.json).write_text(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\n[json] {args.json}")
    return {"SAME_CONFIG": 0, "DIFFERENT_CODE": 2, "CANNOT-VERIFY": 3}[res["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
