#!/usr/bin/env python3
"""从「跑批目录 + 实际生效配置」生成 meta.json，并做真跑判定（exit 非零 = 非真跑）。

为什么单独一个脚本：`python -m orchestration run` 链路（世界层）不写 meta.json，
而 `code/` 属冻结区，不宜为了落 meta 去改 run 链路。本脚本只**读**日志与配置。

**单一真源**：`provider` 只从运行期写入的 `LLM_CALL.payload.provider` 推导，
绝不采用命令行/人填声明（Leader 裁决：meta.provider 不是事实）。

断言（任一不满足 → 非零退出）：
  exit 2  run.jsonl 不存在
  exit 3  行数 != 事件条数（读不完整）
  exit 4  非真跑：LLM_CALL==0，或 provider 出现非 openai_compat，或 model 含 mock/空
  exit 5  日志内 spec 与声明不一致（仅当显式给 --seed/--n/--rounds 时才校验）
  exit 8  `--require-weather-state` 显式给定但运行期反推值不符（缺省不传 ⇒ 不校验、不影响返回码）
  * seed/n/rounds 的**权威值一律从日志派生**（WORLD_INIT.seed / AGENT_BORN 计数 / max(round)+1），
    命令行参数只用于交叉校验；不带参数也能生成 meta（用于「跑完补 meta」场景）。

用法：
  python3 tools/d2/emit_run_meta.py --run-dir v2/evidence/run_d2_before_n16_seed42 \
      --seed 42 --n 16 --rounds 84 [--mock-precalib-msg 190] [--mock] \
      [--started-at ...] [--finished-at ...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=str(ROOT), text=True).strip()
    except Exception:
        return ""


def _assertions(recs) -> dict:
    """从日志复算 D2 结构断言（与 tools/d2/thread_metrics.py 同口径，纯只读）。"""
    msgs = []
    for r in recs:
        if r["type"] not in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
            continue
        p = r.get("payload") or {}
        msgs.append({"seq": int(r["seq"]), "type": r["type"], "msg_id": p.get("msg_id"),
                     "msg_uid": p.get("msg_uid"), "thread_id": p.get("thread_id"),
                     "turn_index": p.get("turn_index"), "reply_to": p.get("reply_to"),
                     "participants": tuple(sorted(p.get("participants") or []))})
    uids = [m["msg_uid"] for m in msgs if m["msg_uid"]]
    owner = {m["msg_uid"]: m for m in msgs if m["msg_uid"]}
    cross = dangling = 0
    for m in msgs:
        rt = m["reply_to"]
        if not rt:
            continue
        if rt not in owner:
            dangling += 1
        elif owner[rt]["thread_id"] != m["thread_id"] or owner[rt]["seq"] >= m["seq"]:
            cross += 1
    groups = {}
    for m in msgs:
        if m["thread_id"]:
            groups.setdefault(m["thread_id"], []).append(m)
    dense_bad = 0
    for g in groups.values():
        idx = sorted({m["turn_index"] for m in g if m["turn_index"] is not None})
        if idx and (idx[0] != 0 or idx != list(range(0, idx[-1] + 1))):
            dense_bad += 1
    parts_bad = 0
    for g in groups.values():
        if len({m["participants"] for m in g}) > 1:
            parts_bad += 1
    return {
        "msg_uid_unique": (len(set(uids)) == len(uids)) if uids else None,
        "reply_to_same_thread": (cross == 0 and dangling == 0),
        "ptr_cross_thread": cross,
        "ptr_dangling": dangling,
        "turn_index_dense": dense_bad == 0,
        "turn_index_gap_threads": dense_bad,
        "participants_consistent": parts_bad == 0,
        "participants_violations": parts_bad,
    }


#: 环境变量开关 → 归一化「真值」判定（与 code/life/weather.py::enabled 同口径）
_TRUTHY = {"1", "true", "yes", "on"}


def _declared_switch(name: str, kind: str = "bool") -> dict:
    """本进程实际读到的开关 env 值（**声明值**，非运行期事实）。

    只作声明侧证据：真正「跑批时生效值」由 `_weather_switch_effective` 从 run.jsonl
    反推（运行期事实）。两者并列，绝不单独采用声明值（沿用 leader 裁决：meta.provider 不是事实）。

    `kind` 决定归一口径（**别把非布尔 env 硬塞进布尔口径**）：
      * `"bool"`（HITT_WEATHER）：`normalized_effective` = 是否为 {1,true,yes,on}（与 weather.enabled 同口径）
      * `"int"`（HITT_WORLD_SEED）：给 `parsed_int`（与 weather.world_seed 同口径：非法/缺失 ⇒ 0），
        不产出 `normalized_effective`（种子不是开关，写成 bool 会误导）
    """
    raw = os.environ.get(name)
    out = {"raw": raw, "source": f"os.environ[{name!r}] @ emit_run_meta 进程"}
    if kind == "int":
        try:
            out["parsed_int"] = int((raw or "").strip()) if (raw or "").strip() else 0
        except (TypeError, ValueError):
            out["parsed_int"] = 0
        out["parse_rule"] = "同 code/life/weather.py::world_seed：缺失/非法 ⇒ 0"
    else:
        out["normalized_effective"] = (raw or "").strip().lower() in _TRUTHY
    return out


def _weather_switch_effective(recs) -> dict:
    """从 run.jsonl 反推 `HITT_WEATHER` 的**运行期生效值**（三态，非声明值）。

    判据（运行期事实，来自日志而非环境变量）：
      * 天气臂开启时，每条生成消息的 payload.ctx 会多出 `weather` 审计键
        （见 `code/life/agent.py::_ctx`：`if WX.enabled() and self._weather is not None`），
        其中带 `day/season/weather/seed/line_sha256`；
      * 关闭时该键**恒不出现**（逐字节等价要求）。
    故 `ctx.weather` 命中数 >0 ⇒ 运行期 ON（硬证据）；==0 无法仅凭日志区分「OFF」与
    「ON 但渲染恒空」，只能结合声明值给出四态，见 `effective` 的取值。
    """
    hits = 0
    days, kinds, seasons, seeds, line_shas = set(), set(), set(), set(), set()
    by_type: dict[str, int] = {}
    for r in recs:
        if not str(r.get("type", "")).startswith("MSG"):
            continue
        ctx = (r.get("payload") or {}).get("ctx")
        if not isinstance(ctx, dict):
            continue
        wx = ctx.get("weather")
        if wx is None:
            continue
        hits += 1
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
        if isinstance(wx, dict):
            if wx.get("day") is not None:
                days.add(int(wx["day"]))
            if wx.get("weather"):
                kinds.add(str(wx["weather"]))
            if wx.get("season"):
                seasons.add(str(wx["season"]))
            if wx.get("seed") is not None:
                seeds.add(int(wx["seed"]))
            if wx.get("line_sha256"):
                line_shas.add(str(wx["line_sha256"]))
    return {
        "ctx_weather_msgs": hits,
        "ctx_weather_by_msg_type": {k: v for k, v in sorted(by_type.items())},
        "distinct_days": len(days),
        "distinct_weather_kinds": sorted(kinds),
        "distinct_seasons": sorted(seasons),
        "seeds_seen": sorted(seeds),
        "distinct_line_sha256": len(line_shas),
        "evidence_field": "run.jsonl[*].payload.ctx.weather",
    }


def _read_lines(path: str | None) -> list | None:
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return [ln.rstrip("\n") for ln in fh if ln.strip()]
    except Exception:
        return None


def _rounds_per_slot() -> int | None:
    try:
        src = (CODE / "life" / "constants.py").read_text(encoding="utf-8")
        m = re.search(r'"ROUNDS_PER_SLOT":\s*(\d+)', src)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--n", type=int)
    ap.add_argument("--rounds", type=int)
    ap.add_argument("--mock-precalib-msg", type=int, default=0)
    ap.add_argument("--mock", action="store_true", help="本臂即 mock（跳过真跑判定）")
    ap.add_argument("--side-root", default=None)
    ap.add_argument("--git-status-start", default=None,
                    help="起跑时 git status --porcelain 快照文件（可选）")
    ap.add_argument("--git-status-start-source", default=None,
                    help="该快照的来源说明（实拍 / 事后重建及其证据）")
    ap.add_argument("--started-at", default=None)
    ap.add_argument("--finished-at", default=None)
    ap.add_argument("--duration-sec", type=int, default=None)
    ap.add_argument("--require-weather-state", choices=("on", "off"), default=None,
                    help="可选硬闸：断言天气臂运行期生效值（ON 臂传 on / OFF 臂传 off）。"
                         "缺省(None) ⇒ 只记录不拦，返回码与未加本参数时完全一致。")
    a = ap.parse_args(argv)

    run_dir = (ROOT / a.run_dir).resolve() if not Path(a.run_dir).is_absolute() else Path(a.run_dir)
    run = run_dir / "run.jsonl"
    if not run.exists():
        print(f"[meta] run.jsonl 不存在: {run}", file=sys.stderr)
        return 2

    recs, bad_lines = [], 0
    with open(run, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except Exception:
                bad_lines += 1
    if bad_lines:
        print(f"[meta] FAIL: {bad_lines} 行不可解析", file=sys.stderr)
        return 3

    types = Counter(r["type"] for r in recs)
    llm = [r for r in recs if r["type"] == "LLM_CALL"]
    providers = Counter(r["payload"].get("provider") for r in llm)
    models = Counter(r["payload"].get("model") for r in llm)
    purposes = Counter(r["payload"].get("purpose") for r in llm)
    degraded = sum(1 for r in llm if r["payload"].get("degraded") is True)
    cached = sum(1 for r in llm if r["payload"].get("cached") is True)
    rr = sorted({int(r["round"]) for r in recs})

    seed_in_log = next((r["payload"].get("seed") for r in recs if r["type"] == "WORLD_INIT"), None)
    n_in_log = sum(1 for r in recs if r["type"] == "AGENT_BORN")
    rounds_from_log = (rr[-1] + 1) if rr else 0
    # 权威值来自日志；命令行参数仅作声明/交叉校验
    seed_authoritative = seed_in_log if seed_in_log is not None else a.seed
    n_authoritative = n_in_log if n_in_log else a.n
    rounds_authoritative = rounds_from_log if rounds_from_log else a.rounds

    cfg = {}
    try:
        cfg = json.loads((CODE / "config" / "llm.json").read_text(encoding="utf-8"))
    except Exception:
        pass

    bad_provider = [k for k in providers if k not in ("openai_compat",)]
    bad_model = [k for k in models if str(k).lower().startswith("mock") or k in (None, "")]
    meta = {
        "run_dir": str(run_dir),
        "run_file": str(run),
        "run_sha256": _sha256(run),
        "derived_from_log_sha256": _sha256(run),
        "generated_after_run": True,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "run_bytes": run.stat().st_size,
        # provider/model 一律由运行期 LLM_CALL payload 推导（单一真源）
        "provider": "openai_compat" if not (bad_provider or bad_model) else "NON-REAL",
        "llm_provider_in_events": {str(k): v for k, v in providers.items()},
        "llm_model_in_events": {str(k): v for k, v in models.items()},
        "model": (sorted([str(k) for k in models if k]) or [None])[0],
        "model_requested": cfg.get("model"),
        "model_reported": sorted([str(k) for k in models if k]) or None,
        "assertions": _assertions(recs),
        "endpoint_host": (cfg.get("endpoint") or "").split("//")[-1].split("/")[0],
        "seed": seed_authoritative,
        "seed_declared": a.seed,
        "seed_in_log": seed_in_log,
        "n": n_authoritative,
        "n_declared": a.n,
        "n_in_log": n_in_log,
        "rounds": rounds_authoritative,
        "rounds_declared": a.rounds,
        "rounds_effective": rounds_from_log,
        "rounds_seen_min": rr[0] if rr else None,
        "rounds_seen_max": rr[-1] if rr else None,
        "rounds_contiguous": bool(rr) and rr == list(range(rr[0], rr[0] + len(rr))),
        "rounds_per_slot_effective": _rounds_per_slot(),
        "code_sha": _git("rev-parse", "HEAD"),
        "git_dirty_files": [ln for ln in _git("status", "--porcelain").splitlines() if ln],
        # 说明：本字段是**生成 meta 时刻**的全仓快照（共享仓库里可能有其他成员的未跟踪产物）。
        # 跑批时刻的「代码身份」以 `code_sha` + 日志内 `WORLD_INIT.config_components` 为硬证据：
        #   git diff <code_sha> -- code/life code/orchestration code/config 应为空。
        "git_dirty_code_files": [ln for ln in _git("status", "--porcelain").splitlines()
                                 if ln and (" code/" in ln or ln.endswith("code/"))],
        "git_status_end": [ln for ln in _git("status", "--porcelain").splitlines() if ln],
        "git_status_start": _read_lines(a.git_status_start),
        "git_status_start_source": a.git_status_start_source,
        "code_sha_end": _git("rev-parse", "HEAD"),
        "code_identity_note": ("代码身份硬证据 = code_sha + WORLD_INIT.config_components；"
                               "git_dirty_code_files 为空表示 code/ 无未提交改动"),
        "events": len(recs),
        "wc_l": len(recs),
        "msg_counts": {k: v for k, v in types.items() if k.startswith("MSG")},
        "dropped_counts": {
            str((r["payload"].get("reason"), r["payload"].get("type"))): 0 for r in ()  # placeholder
        },
        "llm_calls": len(llm),
        "llm_cached": cached,
        "llm_cached_ratio": round(cached / len(llm), 4) if llm else 0.0,
        "degraded_calls": degraded,
        "llm_purposes": {str(k): v for k, v in purposes.items()},
        "mock_precalib_msg_count": a.mock_precalib_msg,
        "mock_precalib_note": ("mock 预校准（同 n/rounds、MockProvider）的 MSG 总条数，仅用于跑前估规模；"
                               "其日志另存 v2/evidence/run_d2_mock_precalib_*.jsonl，不混入本臂任何统计"),
        "fallback_detected": bool(bad_provider or bad_model),
        "side_root": a.side_root,
        "side_root_note": "命令行声明值（非硬证据）；cache 隔离的硬证据见两臂 freeze_cache 目录 mtime/inode 不同 + 按 purpose 的 cached 率",
        "started_at": a.started_at,
        "finished_at": a.finished_at or datetime.now().isoformat(timespec="seconds"),
        "duration_sec": a.duration_sec,
        # --- 开关取证（W-1 天气臂）：声明值 + 运行期反推值，二者并列 ---------------
        # 起因：上一轮 `config/dialogue_repair.json:enabled` 不在 engine/version.py::FINGERPRINT_FILES，
        # 导致「跑批当时的开关值 CANNOT-VERIFY」。天气臂用 env 开关，故在此把它落成可取证字段：
        #   switch_declared  = emit_run_meta 进程读到的 env（声明侧，弱）
        #   switch_effective = 由 run.jsonl 每条 MSG 的 payload.ctx.weather 反推（运行期侧，强）
        "switch_declared": {
            "HITT_WEATHER": _declared_switch("HITT_WEATHER"),
            "HITT_WORLD_SEED": _declared_switch("HITT_WORLD_SEED", kind="int"),
        },
    }
    # 运行期反推（强证据）：在 meta 落盘前算，overwrite 上面的占位
    _decl_wx = meta["switch_declared"]["HITT_WEATHER"]["normalized_effective"]
    _wx_eff = _weather_switch_effective(recs)
    if _wx_eff["ctx_weather_msgs"] > 0:
        _state = "on" if _decl_wx else "contradiction"
    else:
        _state = "off" if not _decl_wx else "cannot-verify"
    _wx_eff["effective"] = _state                       # on / off / cannot-verify / contradiction
    _wx_eff["declared_on"] = _decl_wx
    _wx_eff["state_rule"] = ("ctx.weather>0 ⇒ on（若声明 OFF 则 contradiction）；"
                             "ctx.weather==0 ⇒ off（若声明 ON 则 cannot-verify）")
    meta["switch_effective"] = {"HITT_WEATHER": _wx_eff}

    drops = Counter((r["payload"].get("reason"), r["payload"].get("type"))
                    for r in recs if r["type"] == "DROPPED")
    # 跑批窗口内 code/ 是否被改动（起跑快照 vs 结束快照，只比 code 路径）
    end_code = sorted(x for x in meta["git_status_end"] if " code/" in x)
    start_code = sorted(x for x in (meta["git_status_start"] or []) if " code/" in x)
    meta["assertions"]["code_unchanged_during_run"] = (
        None if meta["git_status_start"] is None else (start_code == end_code))
    meta["dropped_counts"] = {f"{k[0]}|{k[1]}": v for k, v in sorted(drops.items(), key=lambda kv: str(kv[0]))}
    meta["msg_dropped_unknown_intent_field"] = sum(
        v for k, v in drops.items() if k[0] == "unknown_intent_field" and str(k[1]).startswith("MSG"))

    out = run_dir / "meta.json"
    out.write_text(json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"[meta] {out}")
    print(f"[meta] events={meta['events']} llm_calls={meta['llm_calls']} "
          f"cached_ratio={meta['llm_cached_ratio']} provider={meta['llm_provider_in_events']} "
          f"model={meta['llm_model_in_events']}")
    print(f"[meta] seed_in_log={seed_in_log} n_in_log={n_in_log} rounds_effective={meta['rounds_effective']}")
    print(f"[meta] switch_effective.HITT_WEATHER={meta['switch_effective']['HITT_WEATHER']['effective']} "
          f"ctx_weather_msgs={meta['switch_effective']['HITT_WEATHER']['ctx_weather_msgs']} "
          f"declared={meta['switch_declared']['HITT_WEATHER']['raw']!r}")

    # 可选硬闸：只有显式传 --require-weather-state 才拦（缺省 ⇒ 只记录，返回码不变，exit 8 专用）
    if a.require_weather_state is not None:
        want = {"on": "on", "off": "off"}[a.require_weather_state]
        got = meta["switch_effective"]["HITT_WEATHER"]["effective"]
        if got != want:
            print(f"[meta] FAIL(开关取证): require-weather-state={want} 但运行期反推 effective={got}"
                  f"（ctx_weather_msgs={meta['switch_effective']['HITT_WEATHER']['ctx_weather_msgs']}）",
                  file=sys.stderr)
            return 8
        print(f"[meta] OK(开关取证): HITT_WEATHER effective={got}")


    if a.rounds and meta["rounds_effective"] != a.rounds:
        print(f"[meta] FAIL: rounds_effective={meta['rounds_effective']} != 声明 {a.rounds}", file=sys.stderr)
        return 5
    if a.seed is not None and seed_in_log is not None and int(seed_in_log) != a.seed:
        print(f"[meta] FAIL: seed_in_log={seed_in_log} != 声明 {a.seed}", file=sys.stderr)
        return 5
    if a.n is not None and n_in_log != a.n:
        print(f"[meta] FAIL: n_in_log={n_in_log} != 声明 {a.n}", file=sys.stderr)
        return 5
    if a.mock:
        print("[meta] OK (mock 臂：跳过真跑判定)")
        return 0
    if not llm:
        print("[meta] FAIL(真跑判定): LLM_CALL 为 0", file=sys.stderr)
        return 4
    if bad_provider or bad_model:
        print(f"[meta] FAIL(真跑判定): provider={dict(providers)} model={dict(models)}", file=sys.stderr)
        return 4
    print("[meta] OK: 真跑判定通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
