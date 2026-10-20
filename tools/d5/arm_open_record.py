#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开批留痕记录（每臂一次）：干净快照 + 开关状态 + 在跑批探测。

为什么需要它：开关走 env（`HITT_DIALOGUE_REPAIR=1` 且配置文件保持 `enabled=false`），
**env 天然不留痕**——不记就等于事后无法证明哪一臂真开了开关，归因直接悬空。

产出（写进该臂的证据目录）：
  * 开批时刻、HEAD sha、`git status --short -- code/` 原始输出（须为空）
  * `code/config/dialogue_repair.json` 的 sha256 与 `enabled` 字段值
  * `HITT_DIALOGUE_REPAR` 类开关 env 的「是否设置 + 值」
  * 全树 `git status --short`（仅背景，不作判据）
  * 「当下是否已有批在跑」的判据结果（不是靠 ps）

退出码：
  0  快照干净、可以开批
  3  `code/` 非空（禁止开批）
  4  探测到疑似仍有批在跑（禁止开批）
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def sh(cmd, cwd=ROOT):
    p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def probe_running(evidence_dir):
    """按 surveyor 的快照模板口径探测：不靠 ps。
    判定：run 目录有 run.jsonl、且 (无 meta.json) 且 (run.jsonl mtime 在 15 分钟内)
          ⇒ 疑似在跑；或 meta 存在但 TURN_SEAL 计数 < meta.rounds_effective ⇒ 疑似未收尾。
    30 秒内给不出结论就写 unconfirmed（不写"无批在跑"）。
    """
    out = []
    if not os.path.isdir(evidence_dir):
        return {"verdict": "unconfirmed", "reason": "evidence 目录不存在", "items": []}
    now = datetime.now().timestamp()
    for name in sorted(os.listdir(evidence_dir)):
        d = os.path.join(evidence_dir, name)
        if not os.path.isdir(d) or not name.startswith("run_"):
            continue
        if "ABORTED" in name.upper():
            # 已归档的中止批：无 meta 是设计使然，不算"疑似在跑"
            continue
        runj = os.path.join(d, "run.jsonl")
        if not os.path.exists(runj):
            continue
        meta_p = os.path.join(d, "meta.json")
        age_min = (now - os.path.getmtime(runj)) / 60.0
        item = {"dir": os.path.relpath(d, ROOT), "run_jsonl_age_min": round(age_min, 1),
                "has_meta": os.path.exists(meta_p)}
        if not os.path.exists(meta_p):
            item["suspicion"] = "无 meta.json" + ("，且 15 分钟内被写过" if age_min <= 15 else "，但久未写入")
            item["suspected_running"] = age_min <= 15
        else:
            try:
                m = json.load(open(meta_p, encoding="utf-8"))
                rounds = m.get("rounds_effective")
                rc, cnt, _ = sh("grep -c '\"TURN_SEAL\"' %s || true" % runj)
                seal = int(cnt or 0)
                item["turn_seal_count"] = seal
                item["rounds_effective"] = rounds
                item["suspected_running"] = bool(rounds and seal < rounds)
                if item["suspected_running"]:
                    item["suspicion"] = "TURN_SEAL(%d) < rounds_effective(%s)" % (seal, rounds)
            except Exception as e:  # noqa: BLE001
                item["suspicion"] = "meta 解析失败: %s" % e
                item["suspected_running"] = False
        out.append(item)
    running = [i for i in out if i.get("suspected_running")]
    return {"verdict": "running" if running else "clear", "items": out,
            "running_dirs": [i["dir"] for i in running]}


METRIC_TOOLS = [
    "tools/d5/dialogue_metrics.py",
    "tools/d5/f4_repair_evidence.py",
    "tools/d5/f4_manual_judge.py",
    "tools/d5/f4_interrater.py",
    "tools/d5/build_annotation_packet.py",
    "tools/d5/arm_open_record.py",
    "tools/d5/emotion_lexicon.txt",
    "tools/d5/repair_lexicon.txt",
    "tools/d5/timeref_lexicon.txt",
    "tools/d5/task_tags.txt",
    "tools/d5/template_patterns.txt",
    "tools/d5/backref_lexicon.txt",
]


def tools_manifest():
    out = {}
    for rel in METRIC_TOOLS:
        p = os.path.join(ROOT, rel)
        out[rel] = sha256_file(p) if os.path.exists(p) else None
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, help="臂名，如 T / C")
    ap.add_argument("--switch-env", default="HITT_DIALOGUE_REPAIR")
    ap.add_argument("--config", default="code/config/dialogue_repair.json")
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--pin-tools-manifest", default=None,
                    help="写工具冻结清单（Arm-T 开批时用）")
    ap.add_argument("--expect-tools-manifest", default=None,
                    help="核对工具冻结清单（Arm-C 开批时用），不一致 rc=5")
    a = ap.parse_args(argv)

    _, head, _ = sh("git rev-parse HEAD")
    _, status_code, _ = sh("git status --short -- code/")
    _, status_all, _ = sh("git status --short")

    cfg_path = os.path.join(ROOT, a.config) if not os.path.isabs(a.config) else a.config
    cfg = {"path": a.config, "exists": os.path.exists(cfg_path)}
    if cfg["exists"]:
        cfg["sha256"] = sha256_file(cfg_path)
        try:
            j = json.load(open(cfg_path, encoding="utf-8"))
            cfg["enabled"] = j.get("enabled")
            cfg["raw_keys"] = sorted(j.keys())
        except Exception as e:  # noqa: BLE001
            cfg["parse_error"] = str(e)

    env_val = os.environ.get(a.switch_env)
    rec = {
        "schema_version": "arm-open-record/1.0",
        "arm": a.arm,
        "recorded_at": datetime.now().astimezone().isoformat(),
        "head_sha": head,
        "code_status_short_empty": status_code == "",
        "code_status_short_raw": status_code,
        "code_untracked_detail": [ln for ln in status_code.splitlines() if ln.startswith("??")],
        "switch": {
            "env_name": a.switch_env,
            "env_is_set": env_val is not None,
            "env_value": env_val,
            "config": cfg,
            "note": "env 不落盘、不进程内留痕，故由本记录充当该臂开关状态凭证",
        },
        "full_tree_status_background_only": status_all.splitlines(),
        "batch_probe": probe_running(os.path.join(ROOT, "v2", "evidence")),
        "metric_tools": tools_manifest(),
    }

    # ---- 度量工具跨臂冻结：Arm-T 写钉，Arm-C 核对
    if a.pin_tools_manifest:
        with open(a.pin_tools_manifest, "w", encoding="utf-8") as f:
            json.dump({"pinned_at": rec["recorded_at"], "arm": a.arm,
                       "tools": rec["metric_tools"]}, f, ensure_ascii=False, indent=1)
            f.write("\n")
        rec["metric_tools_pin"] = {"pinned_to": os.path.abspath(a.pin_tools_manifest)}
    if a.expect_tools_manifest:
        exp = json.load(open(a.expect_tools_manifest, encoding="utf-8")).get("tools") or {}
        diffs = {k: {"expected": exp.get(k), "actual": rec["metric_tools"].get(k)}
                 for k in set(exp) | set(rec["metric_tools"])
                 if exp.get(k) != rec["metric_tools"].get(k)}
        rec["metric_tools_check"] = {"against": os.path.abspath(a.expect_tools_manifest),
                                    "match": not diffs, "diffs": diffs}
    os.makedirs(os.path.dirname(os.path.abspath(a.out_json)), exist_ok=True)
    with open(a.out_json, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
        f.write("\n")

    print(json.dumps({
        "arm": a.arm, "head": head,
        "code_clean": rec["code_status_short_empty"],
        "switch_env_set": rec["switch"]["env_is_set"],
        "switch_env_value": env_val,
        "config_enabled": cfg.get("enabled"),
        "batch_probe": rec["batch_probe"]["verdict"],
        "metric_tools_frozen": bool(a.expect_tools_manifest and rec.get("metric_tools_check", {}).get("match")),
        "out": a.out_json,
    }, ensure_ascii=False))

    if not rec["code_status_short_empty"]:
        print("[BLOCK] code/ 非空，禁止开批", file=sys.stderr)
        return 3
    if a.expect_tools_manifest and not rec.get("metric_tools_check", {}).get("match", False):
        print("[BLOCK] 度量工具 sha 与 Arm-T 冻结清单不一致（口径漂移），禁止起 Arm-C: %s"
              % json.dumps(rec["metric_tools_check"]["diffs"], ensure_ascii=False), file=sys.stderr)
        return 5
    if rec["batch_probe"]["verdict"] == "running":
        print("[BLOCK] 探测到疑似仍有批在跑: %s" % rec["batch_probe"]["running_dirs"], file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
