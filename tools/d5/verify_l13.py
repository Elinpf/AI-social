#!/usr/bin/env python3
"""verify_l13.py — L-13 人话化补丁的**确定性**校验（不跑 LLM，可复算）。

用法（cwd 必须是仓库根 `social-experiment/`）：

    python3 tools/d5/verify_l13.py
    python3 tools/d5/verify_l13.py --json /tmp/l13_verify.json
    python3 tools/d5/verify_l13.py --no-logs            # 跳过日志扫描（只看词表/映射）
    python3 tools/d5/verify_l13.py --repo-root /path/to/social-experiment

退出码语义：
    0  = 全部断言通过（默认臂全覆盖无 token / off 臂与旧实现逐字节相等 / 日志 topic 覆盖 100%）
    1  = 有断言不通过（脚本打印每一条失败的 key 与取值）
    2  = 环境/前置不满足（仓库根或 code/ 不在位、activity_templates.json 读不出、词表 import 失败）

三个检查（对应任务卡的硬要求）：

  A. **默认模式**：遍历 `code/config/activity_templates.json` 全部 `template_id`，
     断言 `_topic_label` 的返回值 ①不等于原 id（覆盖 100%）②不含 ASCII 下划线形式的
     内部 token（正则 `[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]*`）③不含原 id 子串。

  B. **`off` 回退模式**：`LIFE_PROMPT_TOPIC_LABEL=off` 时，对每个 id（含未知 id / 空串 /
     None）断言 `_topic_label(t) == 旧实现(t)`，旧实现逐字节照抄为
     `TB.label(t) if TB.enabled() else (t or "")`；在 `LIFE_PROMPT_TOPIC_BREADTH`
     未设 与 `=1` 两种状态下各跑一遍。另断言「宽度臂关闭 + 回退」时返回原字符串。

  C. **既有批日志的 `ctx.topic` 覆盖**：扫 `v2/evidence/run_*/run.jsonl`（只取已封批的
     目录——`meta.json` 带 `ended_at` 或 `finished_at`；正在跑的批会变 ⇒ 排除以保证确定性），
     取 `MSG_DM.payload.ctx.topic` 的去重取值集合，再算一遍覆盖率，输出分子/分母
     （去重话题级 + 消息级两种口径都给）。

注：本脚本**只读**仓库，不写任何文件（除 `--json` 指定的输出路径）。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

#: 「ASCII 下划线形式的内部 token」判据（与单测 test_l13_topic_label_default.py 同一正则）
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]*")
LABEL_OFF_VALUES = {"0", "false", "no", "off"}


def _fail(env_problem: str) -> int:
    print(f"SETUP-FAIL: {env_problem}", file=sys.stderr)
    return 2


def _load_modules(repo: Path):
    code_dir = repo / "code"
    if not code_dir.is_dir():
        raise RuntimeError(f"缺 {code_dir}（cwd 必须是仓库根 social-experiment/）")
    sys.path.insert(0, str(code_dir))
    from life import topic_breadth as TB            # noqa: E402
    from life.agent import LifeLayerAgent           # noqa: E402
    return TB, LifeLayerAgent


def _template_ids(repo: Path) -> list[str]:
    p = repo / "code" / "config" / "activity_templates.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    return [t["template_id"] for t in data["templates"]]


def _topic_label_fn(LifeLayerAgent):
    """`_topic_label` 只读 TB，不需要完整 agent 实例。"""
    inst = object.__new__(LifeLayerAgent)
    return lambda topic: inst._topic_label(topic)


def check_default_mode(repo: Path, TB, label_fn) -> tuple[bool, dict]:
    ids = _template_ids(repo)
    covered, token_hits, id_hits, unmapped = 0, [], [], []
    for tid in ids:
        out = label_fn(tid)
        if out != tid:
            covered += 1
        else:
            unmapped.append(tid)
        if TOKEN_RE.search(out):
            token_hits.append({"template_id": tid, "label": out})
        if tid and tid in out:
            id_hits.append({"template_id": tid, "label": out})
    cases = ["future_topic_v9", "", None]
    passthrough_ok = all(label_fn(c) == (c or "") for c in cases)
    ok = (not unmapped) and (not token_hits) and (not id_hits) and passthrough_ok
    return ok, {
        "n_templates": len(ids),
        "covered": covered,
        "coverage": f"{covered}/{len(ids)}",
        "unmapped": unmapped,
        "token_hits": token_hits,
        "original_id_inside_label": id_hits,
        "unknown_id_passthrough_ok": passthrough_ok,
        "unknown_id_cases": ["future_topic_v9", "", None],
    }


def _legacy_topic_label(TB, topic):
    """改造前的原实现，逐字节照抄 —— 回退臂必须与它相等。"""
    return TB.label(topic) if TB.enabled() else (topic or "")


def check_off_mode(repo: Path, TB, label_fn, breadth_env: str, label_env: str) -> tuple[bool, dict]:
    ids = _template_ids(repo)
    cases = ids + ["future_topic_v9", "", None]
    res = {"cases_per_breadth": len(cases), "breadth_states": {}, "mismatches": [],
           "raw_string_when_breadth_off": None}
    prev = {k: os.environ.get(k) for k in (breadth_env, label_env)}
    try:
        os.environ[label_env] = "off"
        for breadth_state in ("unset", "1"):
            if breadth_state == "unset":
                os.environ.pop(breadth_env, None)
            else:
                os.environ[breadth_env] = breadth_state
            n_ok = 0
            for t in cases:
                new, old = label_fn(t), _legacy_topic_label(TB, t)
                if new == old:
                    n_ok += 1
                else:
                    res["mismatches"].append({"breadth": breadth_state, "topic": t,
                                              "new": new, "legacy": old})
            res["breadth_states"][breadth_state] = f"{n_ok}/{len(cases)} byte-equal"
        # 宽度臂关闭（默认跑批语境）+ 回退 ⇒ 必须是原字符串
        os.environ.pop(breadth_env, None)
        raw_ok = all(label_fn(t) == t for t in ids)
        res["raw_string_when_breadth_off"] = f"{sum(1 for t in ids if label_fn(t) == t)}/{len(ids)}"
        ok = not res["mismatches"] and raw_ok
    finally:
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return ok, res


def _sealed_log_dirs(evidence: Path) -> tuple[list[Path], list[dict]]:
    """已封批的 run 目录（meta.json 带 ended_at/finished_at）；未封批/无 meta 的全部登记。"""
    sealed, excluded = [], []
    for run_jsonl in sorted(glob.glob(str(evidence / "run_*" / "run.jsonl"))):
        d = Path(run_jsonl).parent
        meta = d / "meta.json"
        if not meta.exists():
            excluded.append({"dir": d.name, "why": "no meta.json"})
            continue
        try:
            m = json.loads(meta.read_text(encoding="utf-8"))
        except Exception as exc:                     # noqa: BLE001
            excluded.append({"dir": d.name, "why": f"meta parse error: {exc}"})
            continue
        if m.get("ended_at") or m.get("finished_at"):
            sealed.append(d)
        else:
            excluded.append({"dir": d.name, "why": "unsealed (no ended_at/finished_at)"})
    return sealed, excluded


def check_ctx_topic_coverage(repo: Path, label_fn, evidence: Path) -> tuple[bool, dict]:
    sealed, excluded = _sealed_log_dirs(evidence)
    topics = Counter()
    n_msg_topic = 0
    n_msg_humanized = 0
    for d in sealed:
        with (d / "run.jsonl").open(encoding="utf-8", errors="replace") as f:
            for line in f:
                if "ctx" not in line:                 # 快速剪枝（95% 的行是状态事件）
                    continue
                try:
                    o = json.loads(line)
                except Exception:                     # noqa: BLE001
                    continue
                if o.get("type") != "MSG_DM":
                    continue
                topic = ((o.get("payload") or {}).get("ctx") or {}).get("topic")
                if not topic:
                    continue
                profiles = topics
                profiles[str(topic)] += 1
                n_msg_topic += 1
                if label_fn(str(topic)) != str(topic):
                    n_msg_humanized += 1
    # 按字母序固定输出 ⇒ 同一 repo 状态 ⇒ 同一字节
    distinct = sorted(topics)
    mapped, leaks = [], []
    for t in distinct:
        out = label_fn(t)
        (leaks if (out == t or TOKEN_RE.search(out)) else mapped).append(
            {"topic": t, "label": out, "msgs": topics[t]})
    den, num = len(distinct), len(mapped)
    ok = den > 0 and num == den and not leaks
    return ok, {
        "logs_scanned": [d.name for d in sealed],
        "logs_excluded": excluded,
        "distinct_topics": den,
        "humanized_topics": num,
        "topic_coverage": f"{num}/{den}",
        "topic_coverage_pct": round(100.0 * num / den, 1) if den else None,
        "msgs_with_topic": n_msg_topic,
        "msgs_humanized_by_topic": n_msg_humanized,
        "msg_level_coverage": f"{n_msg_humanized}/{n_msg_topic}",
        "unmapped_or_leaky": leaks,
        "by_topic_msgs": {t: topics[t] for t in distinct},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="L-13 人话化补丁确定性校验")
    ap.add_argument("--repo-root", default=".", help="仓库根（含 code/ 与 v2/）")
    ap.add_argument("--no-logs", action="store_true", help="跳过 ctx.topic 日志扫描")
    ap.add_argument("--json", default=None, help="把结果写到该 JSON 路径（可选）")
    a = ap.parse_args(argv)

    repo = Path(a.repo_root).resolve()
    if not (repo / "code").is_dir():
        return _fail(f"{repo} 下没有 code/")
    try:
        TB, LifeLayerAgent = _load_modules(repo)
    except Exception as exc:                          # noqa: BLE001
        return _fail(f"import life.* 失败: {exc}")
    label_fn = _topic_label_fn(LifeLayerAgent)
    # 兼容「补丁前」的树（无 LABEL_ENV 常量）⇒ 仍能给出可读的 FAIL 而不是 AttributeError
    breadth_env = getattr(TB, "BREADTH_ENV", "LIFE_PROMPT_TOPIC_BREADTH")
    label_env = getattr(TB, "LABEL_ENV", "LIFE_PROMPT_TOPIC_LABEL")

    prev = {k: os.environ.get(k) for k in (breadth_env, label_env)}
    results: dict = {"repo_root": str(repo), "env_guard": {}, "checks": {}}
    try:
        # ---- A 默认模式（清空两把开关 = 真实默认）
        os.environ.pop(breadth_env, None)
        os.environ.pop(label_env, None)
        ok_a, res_a = check_default_mode(repo, TB, label_fn)
        results["checks"]["A_default_mode"] = {"ok": ok_a, **res_a}
        print(f"[A] 默认模式 · activity_templates.json: 覆盖 {res_a['coverage']} · "
              f"unmapped={res_a['unmapped']} · token_hits={res_a['token_hits']} · "
              f"未知id透传={res_a['unknown_id_passthrough_ok']} · "
              f"{'PASS' if ok_a else 'FAIL'}")

        # ---- B off 回退
        ok_b, res_b = check_off_mode(repo, TB, label_fn, breadth_env, label_env)
        results["checks"]["B_off_fallback"] = {"ok": ok_b, **res_b}
        print(f"[B] off 回退 · 每态对比 {res_b['cases_per_breadth']} 例 · "
              f"breadth_unset={res_b['breadth_states'].get('unset')} · "
              f"breadth_on={res_b['breadth_states'].get('1')} · "
              f"原字符串={res_b['raw_string_when_breadth_off']} · "
              f"mismatches={len(res_b['mismatches'])} · {'PASS' if ok_b else 'FAIL'}")

        # ---- C 日志 ctx.topic 覆盖
        if a.no_logs:
            ok_c, res_c = True, {"skipped": True}
            print("[C] ctx.topic 日志扫描：已跳过（--no-logs）")
        else:
            ok_c, res_c = check_ctx_topic_coverage(repo, label_fn, repo / "v2" / "evidence")
            results["checks"]["C_ctx_topic_coverage"] = {"ok": ok_c, **res_c}
            print(f"[C] 日志 ctx.topic · 已封批 {len(res_c['logs_scanned'])} 批 · "
                  f"去重话题 {res_c['topic_coverage']}"
                  f"({res_c['topic_coverage_pct']}%) · 消息级 {res_c['msg_level_coverage']} · "
                  f"unmapped={[x['topic'] for x in res_c['unmapped_or_leaky']]} · "
                  f"{'PASS' if ok_c else 'FAIL'}")
        all_ok = ok_a and ok_b and ok_c
    finally:
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    results["ok"] = all_ok
    results["rc"] = 0 if all_ok else 1
    if a.json:
        Path(a.json).write_text(json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True),
                                encoding="utf-8")
        print(f"[out] {a.json}")
    print(f"RESULT: {'PASS' if all_ok else 'FAIL'} (rc={results['rc']})")
    return results["rc"]


if __name__ == "__main__":
    raise SystemExit(main())
