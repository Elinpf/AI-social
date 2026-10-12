#!/usr/bin/env python3
"""T274 夜跑流水线 —— 一键起 / 一键收 / 失败可续 / 一页早报。

与 T271 同源：每批跑在 jiuwenswarm.service cgroup 之外的 transient unit 里，
用 /tmp 只读副本（git archive）+ 文件形式的消融开关 + EnvironmentFile 喂凭据。

子命令：
  start    --batches F [--sha S] [--env-file F] [--only a,b] [--heartbeat 600]
  status   [--run-root D]
  collect  [--run-root D] [--report F]        # 分类 + 一页早报 + summary.json
  resume   --batches F [--run-root D] [--only a,b]
  disk     [--path P]
"""
from __future__ import annotations
import argparse, json, os, re, shlex, shutil, subprocess, sys, time
from datetime import datetime

REPO = os.environ.get("T271_REPO", "/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment")
BIN = os.environ.get("T271_BIN", os.path.join(REPO, "tools", "t271"))
COPY_ROOT = os.environ.get("T271_COPY_ROOT", "/tmp")
RUN_ROOT = os.environ.get("T271_RUN_ROOT", "/root/t271/runs/nightly")
DEFAULT_ENV = os.path.join(REPO, "code", ".env.local")
DEFAULT_CMD = ("/opt/openjiuwen/workswarm-venv/bin/python -m orchestration run --life "
               "--seed {seed} --agents {agents} --rounds {rounds} --out {out} "
               "--side-root {side} --flush-every {flush} {resume_args}")


FROZEN_DIRS = ("code/engine", "code/life", "code/freeze", "code/config",
               "code/obs", "code/contracts", "code/orchestration")


def frozen_dirty():
    r = sh(["git", "-C", REPO, "status", "--porcelain", "--"] + list(FROZEN_DIRS))
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    return lines


def now() -> str:
    return datetime.now().strftime("%F %T")


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, **kw)


# ---------------------------------------------------------------- batches table
def load_batches(path: str):
    rows = []
    with open(path, encoding="utf-8") as f:
        header = None
        for ln in f:
            ln = ln.rstrip("\n")
            if not ln.strip() or ln.lstrip().startswith("#"):
                continue
            parts = ln.split("\t")
            if header is None:
                header = [p.strip() for p in parts]
                continue
            row = dict(zip(header, parts))
            row.setdefault("switch", "-")
            row.setdefault("resume_mode", "overlap")
            row.setdefault("cmd", "")
            row.setdefault("flush", "12")
            row.setdefault("tree", "copy")
            row.setdefault("out", "")
            row.setdefault("side", "")
            rows.append(row)
    return rows


def apply_switch(copy: str, spec: str):
    """spec: 'file.json:dot.path=value;file2.json:k=v'（- 或空=无开关）。"""
    if not spec or spec.strip() in ("-", ""):
        return "-"
    applied = []
    for item in spec.split(";"):
        item = item.strip()
        if not item:
            continue
        loc, _, val = item.partition("=")
        fname, _, keypath = loc.partition(":")
        fp = os.path.join(copy, "code", "config", fname.strip())
        d = json.load(open(fp, encoding="utf-8"))
        node = d
        keys = keypath.strip().split(".")
        for k in keys[:-1]:
            node = node.setdefault(k, {})
        try:
            v = json.loads(val)
        except Exception:
            v = val
        node[keys[-1]] = v
        json.dump(d, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        applied.append(f"{fname}:{keypath}={v}")
    return ";".join(applied) if applied else "-"


# ---------------------------------------------------------------- disk monitor
def disk_snapshot(path="/"):
    out = {}
    r = sh(["df", "-h", path])
    lines = r.stdout.strip().splitlines()
    out["df_h"] = lines[-1] if lines else ""
    r = sh(["df", "-i", path])
    lines = r.stdout.strip().splitlines()
    out["df_i"] = lines[-1] if lines else ""
    return out


def parse_avail_inode(df_i_line):
    try:
        f = df_i_line.split()
        return {"ifree": int(f[3]), "iused": int(f[2]), "iuse%": f[4]}
    except Exception:
        return {}


# ---------------------------------------------------------------- batch run state
def batch_state(name: str, run_root: str):
    rd = os.path.join(run_root, name)
    st = {"name": name, "run_dir": rd, "alive": False, "last_round": None,
          "target": None, "peak_rss": None, "events": None, "duration": None,
          "rc": None, "status": "UNKNOWN", "reason": ""}
    meta_p = os.path.join(rd, "meta.json")
    if os.path.exists(meta_p):
        m = json.load(open(meta_p, encoding="utf-8"))
        st["meta"] = m
        st["target"] = int(m.get("rounds") or 0)
        st["sha"] = m.get("sha"); st["switch"] = m.get("switch")
        st["fingerprint"] = m.get("engine_version_fingerprint")
        st["out"] = m.get("out"); st["started_at"] = m.get("started_at")
        st["resume_mode"] = m.get("resume_mode")
    pid_p = os.path.join(rd, "batch.pid")
    pid = None
    if os.path.exists(pid_p):
        pid = open(pid_p).read().strip()
        st["pid"] = pid
        st["alive"] = bool(pid) and os.path.isdir(f"/proc/{pid}")
    hb = os.path.join(rd, "heartbeat.tsv")
    if os.path.exists(hb):
        rows = [l.split("\t") for l in open(hb, encoding="utf-8").read().splitlines() if l.strip()]
        if rows:
            st["duration"] = f"{rows[0][0]} → {rows[-1][0]}"
            st["ended_at"] = rows[-1][0]
            nums = [int(r[3]) for r in rows if len(r) > 3 and r[3].lstrip("-").isdigit()]
            st["peak_rss"] = max(nums) if nums else None
            for r in rows:
                if len(r) > 2 and r[2].lstrip("-").isdigit() and int(r[2]) >= 0:
                    st["last_round"] = int(r[2])
    out_p = st.get("out") or os.path.join(rd, "run.jsonl")
    log_round = None
    if os.path.exists(out_p):
        n = sum(1 for _ in open(out_p, encoding="utf-8", errors="ignore"))
        st["events"] = n
        tail = open(out_p, "rb").read()[-262144:]
        st["run_end"] = b"RUN_END" in tail
        for line in reversed(tail.split(b"\n")):
            line = line.strip()
            if not line or not line.startswith(b"{"):
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if isinstance(r, dict) and isinstance(r.get("round"), int):
                log_round = r["round"]
                break
    st["log_round"] = log_round
    hl = os.path.join(rd, "host.log")
    if os.path.exists(hl):
        for line in open(hl, encoding="utf-8", errors="ignore"):
            m = re.search(r"batch exited rc=(-?\d+)", line)
            if m:
                st["rc"] = int(m.group(1))
    # 是否达标以【日志实测回合】为准；心跳 round 只作「死在哪一刻」用（10min 间隔会滞后）。
    reached = log_round if log_round is not None else st.get("last_round")
    if reached is not None:
        st["last_round"] = reached
    st["reached"] = reached
    target = st.get("target")
    hit = bool(target) and reached is not None and reached >= target - 1

    if st.get("run_end"):
        st["status"] = "SUCCESS"; st["reason"] = "RUN_END"
        if target:
            st["last_round"] = max(reached or 0, target - 1)
    elif st["alive"]:
        st["status"] = "RUNNING"; st["reason"] = "进程存活"
    elif st["rc"] in (137, 143) or (st["rc"] is not None and st["rc"] < 0):
        st["status"] = "INTERRUPTED"
        st["reason"] = f"被信号终止 rc={st['rc']}（外因中断，非批内错误）"
    elif hit and st["rc"] in (0, None):
        st["status"] = "SUCCESS"
        st["reason"] = f"日志到目标回合 {reached}/{target-1}（rc={st['rc']}）"
    elif hit:
        st["status"] = "FAILED"
        st["reason"] = f"回合已到但引擎自检失败 rc={st['rc']}"
    elif st["rc"] is not None and st["rc"] != 0:
        st["status"] = "FAILED"; st["reason"] = f"rc={st['rc']}"
    else:
        st["status"] = "INTERRUPTED"
        st["reason"] = f"未达目标（日志回合={reached}, target={target}, rc={st['rc']}）"
    return st


# ---------------------------------------------------------------- launch helper
def launch(name, copy, run_dir, sha, envfile, cmd_tmpl, rounds, agents, seed, flush,
           heartbeat, mem_high, mem_max, switch_val, resume_mode, extra_tag="", out_name="run.jsonl",
           out_override=None, tree_val="", resuming=False, side_override=None):
    out = out_override or os.path.join(run_dir, out_name)
    # side_root 可被批次表覆盖（多批共享 freeze_cache 做干净消融）；默认 <run_dir>/side
    side = side_override or os.path.join(run_dir, "side")
    # native 续跑：真 runner 用 --resume-from <已 flush 前缀> --target-round <目标>（复用同一 side_root）
    resume_args = f"--resume-from {out} --target-round {rounds}" if resuming else ""
    ctx = dict(out=out, side=side, hb=os.path.join(run_dir, "heartbeat.tsv"),
               copy=copy, rounds=rounds, agents=agents, seed=seed, flush=flush,
               resume_args=resume_args)
    cmd = (cmd_tmpl or DEFAULT_CMD).format(**ctx)
    meta = [f"sha={sha}", f"copy={copy}", f"switch={switch_val}",
            f"side_root={side}", f"flush_every={flush}", f"resume_mode={resume_mode}",
            f"rounds={rounds}", f"agents={agents}", f"seed={seed}"]
    if extra_tag:
        meta.append(extra_tag)
    if tree_val:
        meta.append(f"tree={tree_val}")
    argv = [os.path.join(BIN, "host_batch.sh"), "--name", name, "--out", out,
            "--run-dir", run_dir,
            "--workdir", os.path.join(copy, "code"),
            "--env-file", envfile, "--heartbeat", str(heartbeat),
            "--mem-high", mem_high, "--mem-max", mem_max]
    for kv in meta:
        argv += ["--meta", kv]
    argv += ["--"] + shlex.split(cmd)
    r = sh(argv)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        raise SystemExit(f"[nightly] launch 失败: {name} rc={r.returncode}")


# ---------------------------------------------------------------- subcommands
def cmd_start(a):
    batches = load_batches(a.batches)
    if a.only:
        keep = set(a.only.split(","))
        batches = [b for b in batches if b["name"] in keep]
    sha = a.sha or sh(["git", "-C", REPO, "rev-parse", "HEAD"]).stdout.strip()
    envfile = a.env_file if a.env_file else DEFAULT_ENV
    if not os.path.exists(envfile):
        raise SystemExit(f"[nightly] EnvironmentFile 不存在: {envfile}")
    os.makedirs(RUN_ROOT, exist_ok=True)
    snap = disk_snapshot()
    dirty = frozen_dirty()
    json.dump({"started_at": now(), "sha": sha, "disk_before": snap, "frozen_dirty": dirty},
              open(os.path.join(RUN_ROOT, "_session.json"), "w"), ensure_ascii=False, indent=2)
    print(f"# 夜跑开始 {now()} sha={sha[:9]} 批数={len(batches)}")
    if dirty:
        print(f"# ⚠️ 冻结区脏文件 {len(dirty)} 个：committed 副本(tree=copy)【不含】它们；"
              f"tree=main 批【会含】→ A 与 B/C/D 可能跑不同代码，消融不可比。")
        for ln in dirty:
            print("     dirty:", ln.strip())
    print(f"# 盘前 df -h: {snap['df_h']}")
    print(f"# 盘前 df -i: {snap['df_i']}")
    for b in batches:
        name = b["name"]
        run_dir = os.path.join(RUN_ROOT, name)
        shutil.rmtree(run_dir, ignore_errors=True)
        os.makedirs(run_dir, exist_ok=True)
        tree = b.get("tree", "copy")
        if tree == "main":
            copy = REPO            # A 批在主树（leader 口径）；不建副本、无开关
            sw = "-"
        else:
            copy = os.path.join(COPY_ROOT, f"t271-{name}")
            shutil.rmtree(copy, ignore_errors=True)
            os.makedirs(copy, exist_ok=True)
            sh(f"git -C '{REPO}' archive '{sha}' | tar -x -C '{copy}'", check=True)
            sw = apply_switch(copy, b["switch"])
        sh([os.path.join(BIN, "capture_provenance.sh"), copy, run_dir])
        launch(name, copy, run_dir, sha, envfile, b["cmd"],
               b["rounds"], b["agents"], b["seed"], b["flush"], a.heartbeat,
               a.mem_high, a.mem_max, sw, b["resume_mode"],
               out_override=(b.get("out") or None), tree_val=tree,
               side_override=(b.get("side") or None))
        print(f"[start] {name}: tree={tree} copy={copy} switch={sw} resume_mode={b['resume_mode']}")


def cmd_status(a):
    root = a.run_root or RUN_ROOT
    names = sorted(d for d in os.listdir(root)
                   if os.path.isdir(os.path.join(root, d))
                   and os.path.exists(os.path.join(root, d, "meta.json")))
    for n in names:
        st = batch_state(n, root)
        print(f"{n:12s} {st['status']:11s} round={st['last_round']}/{st['target']} "
              f"rss={st['peak_rss']}MB events={st['events']} alive={st['alive']}  {st['reason']}")


def cmd_disk(a):
    print(json.dumps(disk_snapshot(a.path), ensure_ascii=False, indent=2))


def cmd_cleanup(a):
    """长期账：删 /tmp 只读副本 + 把 side 打包成 side.tar.gz（省 inode），保留小元数据。
    对某批加 run_dir/keep_side 空文件 = 该批 side 不打包（证据级）。"""
    root = a.run_root or RUN_ROOT
    reclaimed_copies = 0
    for n in sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))):
        rd = os.path.join(root, n)
        copy = os.path.join(COPY_ROOT, f"t271-{n}")
        if os.path.isdir(copy) and a.remove_copies:
            sz = int(sh(["du", "-sb", copy]).stdout.split()[0] or 0)
            if a.dry_run:
                print(f"[cleanup] (dry) 将删副本 {copy} ({sz/1e6:.1f} MB)")
            else:
                shutil.rmtree(copy, ignore_errors=True)
                reclaimed_copies += sz
                print(f"[cleanup] 删副本 {copy} ({sz/1e6:.1f} MB)")
        side = os.path.join(rd, "side")
        keep_marker = os.path.exists(os.path.join(rd, "keep_side"))
        if os.path.isdir(side) and not keep_marker and a.side_tar:
            nfiles = sum(len(fs) for _, _, fs in os.walk(side))
            if a.dry_run:
                print(f"[cleanup] (dry) 将打包 side {side}（{nfiles} 文件 → side.tar.gz）")
            else:
                sh(["tar", "czf", os.path.join(rd, "side.tar.gz"), "-C", rd, "side"])
                h = sh(["sha256sum", os.path.join(rd, "side.tar.gz")]).stdout.split()[0]
                shutil.rmtree(side, ignore_errors=True)
                print(f"[cleanup] side 打包 {n}（{nfiles} 文件 → 1 文件）sha256={h[:16]}…")
    print(f"[cleanup] 副本回收 ≈ {reclaimed_copies/1e6:.1f} MB")
    print(f"[cleanup] 盘后 df -h: {disk_snapshot()['df_h']}")
    print(f"[cleanup] 盘后 df -i: {disk_snapshot()['df_i']}")


def cmd_collect(a):
    root = a.run_root or RUN_ROOT
    names = sorted(d for d in os.listdir(root)
                   if os.path.isdir(os.path.join(root, d))
                   and os.path.exists(os.path.join(root, d, "meta.json")))
    for n in names:
        sh([os.path.join(BIN, "finalize_meta.sh"), os.path.join(root, n)])  # 回填指纹/结束时刻
    states = [batch_state(n, root) for n in names]
    snap = disk_snapshot()
    sess_p = os.path.join(root, "_session.json")
    before = json.load(open(sess_p)).get("disk_before") if os.path.exists(sess_p) else {}
    lines = ["# 夜跑早报", "", f"> 生成 {now()} ｜ run_root=`{root}`", ""]
    if before:
        lines += [f"- 盘前 `df -h`: `{before.get('df_h','')}`",
                  f"- 盘后 `df -h`: `{snap['df_h']}`",
                  f"- 盘前 `df -i`: `{before.get('df_i','')}`",
                  f"- 盘后 `df -i`: `{snap['df_i']}`", ""]
    succ = sum(1 for s in states if s["status"] == "SUCCESS")
    lines += [f"**总览**：{len(states)} 批 ｜ 成功 {succ} ｜ 非成功 {len(states)-succ}", "",
              "| 批 | 状态 | round | 事件 | 峰值RSS(MB) | 耗时 | sha | 指纹 | 开关 | 续跑 |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for s in states:
        m = s.get("meta") or {}
        lines.append("| {n} | {st} | {r}/{t} | {e} | {rss} | {d} | {sha} | {fp} | {sw} | {rm} |".format(
            n=s["name"], st=s["status"], r=s.get("last_round"), t=s.get("target"),
            e=s.get("events"), rss=s.get("peak_rss"), d=s.get("duration") or "-",
            sha=(s.get("sha") or "-"), fp=(s.get("fingerprint") or "-")[:20],
            sw=(s.get("switch") or "-"), rm=(s.get("resume_mode") or "-")))
    lines += ["", "## 逐批详情"]
    for s in states:
        m = s.get("meta") or {}
        lines += [f"### {s['name']} — **{s['status']}**",
                  f"- 判据：{s['reason']}",
                  f"- run_dir：`{s['run_dir']}`",
                  f"- 副本：`{m.get('copy')}` ｜ sha：`{s.get('sha')}`",
                  f"- `engine_version` 指纹：`{s.get('fingerprint')}`",
                  f"- 开关：`{s.get('switch')}` ｜ side_root：`{m.get('side_root')}`",
                  f"- 起止：`{m.get('started_at')}` → `{s.get('ended_at') or '-'}` ｜ 心跳：`{m.get('heartbeat_file')}`",
                  f"- 命令：`{m.get('cmd')}`", ""]
    report = "\n".join(lines) + "\n"
    rp = a.report or os.path.join(root, f"morning-report-{datetime.now():%Y%m%d}.md")
    open(rp, "w", encoding="utf-8").write(report)
    json.dump({"generated_at": now(), "states": states, "disk_after": snap, "disk_before": before},
              open(os.path.join(root, "summary.json"), "w"), ensure_ascii=False, indent=2)
    print(report)
    print(f"[collect] 早报: {rp}  摘要: {os.path.join(root,'summary.json')}")


def cmd_resume(a):
    batches = {b["name"]: b for b in load_batches(a.batches)}
    root = a.run_root or RUN_ROOT
    names = sorted(d for d in os.listdir(root)
                   if os.path.isdir(os.path.join(root, d))
                   and os.path.exists(os.path.join(root, d, "meta.json")))
    if a.only:
        keep = set(a.only.split(","))
        names = [n for n in names if n in keep]
    for n in names:
        st = batch_state(n, root)
        if st["status"] not in ("INTERRUPTED", "FAILED"):
            continue
        b = batches.get(n)
        if not b:
            print(f"[resume] {n}: 无批次表条目，跳过"); continue
        sha = st.get("sha") or sh(["git", "-C", REPO, "rev-parse", "HEAD"]).stdout.strip()
        # 副本可能已被 cleanup 删：优先用 meta 记录的副本，缺失则从 sha 重建并重落开关
        meta = st.get("meta") or {}
        copy = meta.get("copy") or os.path.join(COPY_ROOT, f"t271-{n}")
        if not os.path.isdir(os.path.join(copy, "code")):
            print(f"[resume] {n}: 副本缺失，从 sha 重建 -> {copy}")
            shutil.rmtree(copy, ignore_errors=True); os.makedirs(copy, exist_ok=True)
            sh(f"git -C '{REPO}' archive '{sha}' | tar -x -C '{copy}'", check=True)
            apply_switch(copy, meta.get("switch") or "-")
        run_dir = os.path.join(root, n)
        mode = b["resume_mode"]
        if mode == "native":
            print(f"[resume] {n}: native 续跑（--resume-from 已 flush 前缀，--target-round {b['rounds']}，复用同一 side_root）")
            launch(n, copy, run_dir, sha, a.env_file or DEFAULT_ENV, b["cmd"],
                   b["rounds"], b["agents"], b["seed"], b["flush"], a.heartbeat,
                   a.mem_high, a.mem_max, st.get("switch") or "-", "native",
                   out_override=st.get("out"), resuming=True,
                   side_override=meta.get("side_root") or None)
        else:
            print(f"[resume] {n}: overlap 重叠重跑（回退；重跑到目标 {b['rounds']} 回合，落 rerun.jsonl）")
            launch(n, copy, run_dir, sha, a.env_file or DEFAULT_ENV, b["cmd"],
                   b["rounds"], b["agents"], b["seed"], b["flush"], a.heartbeat,
                   a.mem_high, a.mem_max, st.get("switch") or "-", "overlap_rerun",
                   extra_tag="resumed_from=interrupt", out_name="rerun.jsonl")


def main():
    p = argparse.ArgumentParser(prog="nightly")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("start"); s.set_defaults(func=cmd_start)
    s.add_argument("--batches", required=True)
    s.add_argument("--sha", default=None)
    s.add_argument("--env-file", default=None)
    s.add_argument("--only", default=None)
    s.add_argument("--heartbeat", type=int, default=600)
    s.add_argument("--mem-high", default="6G"); s.add_argument("--mem-max", default="8G")

    s = sub.add_parser("status"); s.set_defaults(func=cmd_status)
    s.add_argument("--run-root", default=None)

    s = sub.add_parser("collect"); s.set_defaults(func=cmd_collect)
    s.add_argument("--run-root", default=None); s.add_argument("--report", default=None)

    s = sub.add_parser("resume"); s.set_defaults(func=cmd_resume)
    s.add_argument("--batches", required=True)
    s.add_argument("--run-root", default=None); s.add_argument("--only", default=None)
    s.add_argument("--env-file", default=None)
    s.add_argument("--heartbeat", type=int, default=600)
    s.add_argument("--mem-high", default="6G"); s.add_argument("--mem-max", default="8G")

    s = sub.add_parser("disk"); s.set_defaults(func=cmd_disk)
    s.add_argument("--path", default="/")

    s = sub.add_parser("cleanup"); s.set_defaults(func=cmd_cleanup)
    s.add_argument("--run-root", default=None)
    s.add_argument("--remove-copies", action="store_true", default=True)
    s.add_argument("--keep-copies", dest="remove_copies", action="store_false")
    s.add_argument("--side-tar", action="store_true", default=True)
    s.add_argument("--no-side-tar", dest="side_tar", action="store_false")
    s.add_argument("--dry-run", action="store_true")

    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
