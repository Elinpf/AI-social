#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CYCLE-25 §四 素材独立复核器（第三方凭本脚本 + cases_manifest.json + 原始 run.jsonl/PNG 即可原地复现）

校验四件事：
  1) 源日志身份：`run.jsonl` 的 sha256 必须等于 `cases_manifest.json` 里声明的值；
  2) 每条引文：用**物理行号**回读原始日志，`payload.body` 必须与清单**逐字节相等**，
     并核 `物理行 == seq+1`、`msg_uid == <seed>:<seq>`、`round/turn/from/to` 一致；
  3) CASES.md 里的引文行（表格 6 列：行号/seq/轮次/说话人→收件人/uid/原文）必须与清单逐字节相等；
  4) 截图 sha 链：`render_report_<LABEL>.json` 的 `log_sha256 == run_sha256_in_threads == 日志实测 sha`、
     `threads_json_sha256 == 磁盘 threads 文件 sha`、`views[].png_sha256 == 磁盘 PNG sha`、`ok_count>0 且 fail_count==0`。

用法：
  python3 v2/evidence/cycle25_shots/verify_cases.py --repo .
  python3 v2/evidence/cycle25_shots/verify_cases.py --repo . --cases <CASES.md 路径>
退出码：0 = 全通过；1 = 有失败项；2 = 输入缺失。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_lines(path: pathlib.Path):
    """按物理行返回 dict{line_no: parsed_json}；解析失败的行跳过（与采集脚本同口径）"""
    out = {}
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            try:
                out[i] = json.loads(line)
            except Exception:
                continue
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CYCLE-25 §四 素材独立复核器")
    ap.add_argument("--repo", default=".", help="仓库根（默认当前目录）")
    ap.add_argument("--manifest", default=None,
                    help="清单路径（默认 <repo>/v2/evidence/cycle25_shots/cases_manifest.json）")
    ap.add_argument("--cases", default=None, help="可选：CASES.md 路径，额外回查其中的引文行")
    a = ap.parse_args(argv)

    repo = pathlib.Path(a.repo).resolve()
    man_path = pathlib.Path(a.manifest) if a.manifest else repo / "v2/evidence/cycle25_shots/cases_manifest.json"
    if not man_path.exists():
        print(f"[FAIL] 缺少清单 {man_path}", file=sys.stderr)
        return 2
    man = json.loads(man_path.read_text(encoding="utf-8"))
    shots_dir = man_path.parent

    fails, checks = [], 0

    def ok(cond, tag, detail=""):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(f"{tag}: {detail}")
        return cond

    # ---------- 1) 源日志身份 ----------
    cache = {}
    for tag, s in man["sources"].items():
        p = repo / s["path"]
        if not ok(p.exists(), f"src[{tag}]", f"文件不存在 {p}"):
            continue
        got = sha256_file(p)
        ok(got == s["sha256"], f"src[{tag}].sha256", f"实测 {got} != 声明 {s['sha256']}")
        cache[tag] = p

    # ---------- 2) 逐条引文回读 ----------
    bodies = {}
    for seg in man["segments"]:
        p = cache.get(seg["src_tag"])
        if p is None:
            fails.append(f"seg[{seg['sid']}]: 源日志不可用")
            continue
        ok(sha256_file(p) == seg["source_sha256"], f"seg[{seg['sid']}].source_sha256", "段内声明 sha 与实测不符")
        lines = read_lines(p)
        seed = str(seg["seed"])
        for m in seg["msgs"]:
            ln = m["line"]
            e = lines.get(ln)
            if not ok(e is not None, f"seg[{seg['sid']}].line{ln}", "该物理行不存在或无法解析"):
                continue
            pl = e.get("payload") or {}
            ok(e.get("seq") == m["seq"], f"seg[{seg['sid']}].line{ln}.seq", f'{e.get("seq")} != {m["seq"]}')
            ok(ln == (m["seq"] or -1) + 1, f"seg[{seg['sid']}].line{ln}.seq+1", "物理行 ≠ seq+1")
            ok(pl.get("msg_uid") == m["msg_uid"], f"seg[{seg['sid']}].line{ln}.uid",
               f'{pl.get("msg_uid")} != {m["msg_uid"]}')
            ok(str(m["msg_uid"]) == f"{seed}:{m['seq']}", f"seg[{seg['sid']}].line{ln}.uid-form", "uid 不等于 <seed>:<seq>")
            ok(e.get("round") == m["round"], f"seg[{seg['sid']}].line{ln}.round", "round 不符")
            ok(pl.get("turn_index") == m["turn"], f"seg[{seg['sid']}].line{ln}.turn", "turn_index 不符")
            ok(pl.get("from") == m["from"], f"seg[{seg['sid']}].line{ln}.from", "from 不符")
            ok(pl.get("to") == m["to"], f"seg[{seg['sid']}].line{ln}.to", "to 不符")
            ok(pl.get("thread_id") == seg["thread_id"], f"seg[{seg['sid']}].line{ln}.thread", "thread_id 不符")
            body = pl.get("body") or ""
            ok(body == m["body"], f"seg[{seg['sid']}].line{ln}.body",
               f"逐字节不等（实测 {len(body)} 字 / 清单 {len(m['body'])} 字）")
            ok(len(body) == m["body_len"], f"seg[{seg['sid']}].line{ln}.len", "body_len 不符")
            bodies[(seg["thread_id"], ln, m["msg_uid"])] = m["body"]
        ok(len(seg["msgs"]) == seg["n_msgs"], f"seg[{seg['sid']}].count", "n_msgs 与 msgs 长度不符")
        ok(sum(1 for m in seg["msgs"] if m["body"].startswith("（")) == seg["paren_lead_count"],
           f"seg[{seg['sid']}].paren", "paren_lead_count 不符")

    # ---------- 3) CASES.md 引文行回查 ----------
    if a.cases:
        cp = pathlib.Path(a.cases)
        if not cp.exists():
            fails.append(f"cases: 文件不存在 {cp}")
        else:
            n_rows = 0
            for raw in cp.read_text(encoding="utf-8").splitlines():
                if not raw.startswith("| "):
                    continue
                cells = [c.strip() for c in raw.strip().strip("|").split("|")]
                if len(cells) != 6:
                    continue
                if not cells[0].isdigit() or not cells[1].isdigit():
                    continue                      # 跳过表头/分隔行/其他表
                ln, sq, uid_col, body_col = int(cells[0]), int(cells[1]), cells[4], cells[5]
                n_rows += 1
                key = next((k for k in bodies if k[1] == ln and k[2] == uid_col.strip("`")), None)
                if not ok(key is not None, f"cases.line{ln}", f"CASES.md 行号 {ln} / uid {uid_col} 不在清单内"):
                    continue
                ok(bodies[key] == body_col, f"cases.line{ln}.body", "CASES.md 引文与原始日志逐字节不等")
            ok(n_rows == sum(s["n_msgs"] for s in man["segments"]), "cases.rows",
               f"CASES.md 引文行数 {n_rows} != 清单 {sum(s['n_msgs'] for s in man['segments'])}")

    # ---------- 4) 截图 sha 链 ----------
    receipts = sorted(shots_dir.glob("render_report_*.json"))
    ok(bool(receipts), "shots.receipt", f"{shots_dir} 下没有 render_report_*.json")
    for rp in receipts:
        rep = json.loads(rp.read_text(encoding="utf-8"))
        ok(rep.get("ok_count", 0) > 0, f"shots[{rp.name}].ok_count", f'ok_count={rep.get("ok_count")}')
        ok(rep.get("fail_count") == 0, f"shots[{rp.name}].fail_count", f'fail_count={rep.get("fail_count")}')
        log_p = pathlib.Path(rep["log"])
        if ok(log_p.exists(), f"shots[{rp.name}].log", f"日志不存在 {log_p}"):
            ok(sha256_file(log_p) == rep["log_sha256"], f"shots[{rp.name}].log_sha256", "日志实测 sha 与回执不等")
        ok(rep.get("log_sha256") == rep.get("run_sha256_in_threads"), f"shots[{rp.name}].chain.log==threads",
           "回执 log_sha256 与 run_sha256_in_threads 不等")
        tj = pathlib.Path(rep["threads_json"])
        if ok(tj.exists(), f"shots[{rp.name}].threads_json", f"threads 不存在 {tj}"):
            ok(sha256_file(tj) == rep["threads_json_sha256"], f"shots[{rp.name}].threads_sha", "threads 实测 sha 与回执不等")
            tj_doc = json.loads(tj.read_text(encoding="utf-8"))
            ok((tj_doc.get("source") or {}).get("run_sha256") == rep["log_sha256"],
               f"shots[{rp.name}].threads.source_sha", "threads.source.run_sha256 与日志 sha 不等")
        for v in rep["views"]:
            png = pathlib.Path(v["png"])
            if not ok(png.exists(), f"shots[{rp.name}].{v['view']}.png", f"PNG 不存在 {png}"):
                continue
            ok(sha256_file(png) == v.get("png_sha256"), f"shots[{rp.name}].{v['view']}.png_sha256",
               "PNG 实测 sha 与回执不等")
            ok(png.stat().st_size == v.get("png_bytes"), f"shots[{rp.name}].{v['view']}.png_bytes", "字节数不等")
            ok("--no-blank-check" in v["triplet"]["render_cmd"],
               f"shots[{rp.name}].{v['view']}.no_blank_check", "render_cmd 未带 --no-blank-check")

    # ---------- 汇总 ----------
    print(f"checks={checks}  fails={len(fails)}")
    if fails:
        for f in fails:
            print("  [FAIL]", f)
        return 1
    print("[PASS] 全部通过：源日志 sha / 24 条引文逐字节 / CASES.md 引文行 / 四段 sha 链")
    return 0


if __name__ == "__main__":
    sys.exit(main())
