#!/usr/bin/env python3
"""冻结区零改动取证（看板 A-3）：`meta.assertions.code_unchanged_during_run` 的真断言实现。

背景
----
旧 `emit_run_meta.py` 里这个断言恒为 `null`：它只在**显式传** `--git-status-start` 时才比较
起跑/结束快照，而 `run_batch.sh` 从不传 ⇒ 两臂 meta 全是 `None`。后果是「跑批期间有没有人
动了 `code/life|orchestration|config|engine`」这件事**没有证据**，只能靠人肉记忆 —— 违反
「结论必须绑定可复算证据」的纪律。

两种取证路径（本模块只做**判定**，不做记录）
--------------------------------------------
1. **EXIT trap 落盘（首选，跑批当时）**：`tools/d2/run_batch.sh` 在批结束时写
   `<out-dir>/code_frozen_diff_at_exit.txt`（格式见 `_parse_diff_file`）。
2. **事后回放（本模块 CLI / `frozen_diff()`）**：对 `git diff --name-only <code_sha> --
   <冻结区>` 求差集。只要跑批那次 `code_sha` 在仓里可解析，事后也能复算「相对该 sha，
   冻结区是否零改动」；再叠加「git status 里冻结区**新增**脏条目」做二次确认
   （防止工作区里出现 git diff 看不到的 untracked 文件）。

冻结区单一真源 = 本文件的 `FROZEN_ZONES`；`run_batch.sh` 的 trap 也调本模块，避免两处写死不一致。

用法（零跑批、零 LLM、只读 git）：
  python3 tools/d2/frozen_zone_diff.py --rev 9f592bfa            # 打印相对该 sha 的冻结区改动
  python3 tools/d2/frozen_zone_diff.py --rev HEAD --json         # 机器可读
  python3 tools/d2/frozen_zone_diff.py --selftest                # 断言解析/判定口径
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

#: 冻结区（跑批期间**任何**改动都算违规；见团队硬纪律）
FROZEN_ZONES: tuple[str, ...] = (
    "code/life",
    "code/orchestration",
    "code/config",
    "code/engine",
)

#: EXIT trap 落盘文件名（相对 out-dir）
TRAP_FILE_NAME = "code_frozen_diff_at_exit.txt"

ROOT = Path(__file__).resolve().parents[2]


def _git(repo: str | Path, *args: str) -> tuple[int, str]:
    try:
        p = subprocess.run(["git", *args], cwd=str(repo), text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return p.returncode, p.stdout
    except Exception as exc:  # pragma: no cover - git 不在 PATH 时才会走到
        return 127, f"{exc}"


def frozen_diff(repo: str | Path, rev: str) -> list[str] | None:
    """`git diff --name-only <rev> -- <冻结区>` ⇒ 改动文件列表；git 不可用/rev 不可解析 ⇒ None。"""
    rc_code, _ = _git(repo, "rev-parse", "--verify", f"{rev}^{{commit}}")
    if rc_code != 0:
        return None
    rc, out = _git(repo, "diff", "--name-only", rev, "--", *FROZEN_ZONES)
    if rc != 0:
        return None
    return [ln for ln in out.splitlines() if ln.strip()]


def frozen_status_new(repo: str | Path, start_snapshot: list[str] | None) -> list[str]:
    """`git status --porcelain` 里冻结区的条目中，**起跑快照里没有**的那些（新脏/新 untracked）。

    `git diff` 看不见 untracked 文件，故用快照差集补一刀；`start_snapshot=None`（无起跑快照）
    时退化为「当前冻结区全部脏条目」（此时无法区分「本来就有」与「跑批期间新增」，
    调用方必须如实标注 evidence 里的 `start_snapshot=None`）。
    """
    rc, out = _git(repo, "status", "--porcelain", "--", *FROZEN_ZONES)
    if rc != 0:
        return []
    now = sorted(ln for ln in out.splitlines() if ln.strip())
    if start_snapshot is None:
        return now
    start = set(ln for ln in start_snapshot if any(z in ln for z in FROZEN_ZONES))
    return [ln for ln in now if ln not in start]


def _parse_trap_file(path: str | Path) -> list[str] | None:
    """解析 EXIT trap 落盘文件 → 改动行列表（`#` 开头与 `code_sha=` / `rc=` 元信息行不算改动）。"""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except Exception:
        return None
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("code_sha=") or s.startswith("rc=") \
                or s.startswith("frozen_zones="):
            continue
        out.append(s)
    return out


def decide(*, trap_diff: list[str] | None,
           rev_diff: list[str] | None,
           new_status: list[str] | None) -> dict:
    """判定「冻结区零改动」。返回 `{unchanged: bool, method: str, reasons: [...]}`。

    判定顺序：EXIT trap（跑批当时的事实）> 事后 rev diff + 快照差集 > 不可验证（记 False，不静默）。
    注意：**任何**一路可用的证据只要有改动 ⇒ `unchanged=False`（多路证据是「与」关系，不是「或」）。
    """
    reasons: list[str] = []
    methods: list[str] = []
    if trap_diff is not None:
        methods.append("exit_trap")
        if trap_diff:
            reasons.append(f"EXIT trap 记录冻结区改动 {len(trap_diff)} 个文件")
    if rev_diff is not None:
        methods.append(f"git_diff_vs_code_sha")
        if rev_diff:
            reasons.append(f"相对 code_sha 的冻结区 diff 非空（{len(rev_diff)} 个文件）")
    if new_status is not None:
        methods.append("git_status_snapshot")
        if new_status:
            reasons.append(f"冻结区新增脏/untracked 条目 {len(new_status)} 条")
    if not methods:
        return {"unchanged": False, "method": "unverifiable",
                "reasons": ["无任何可用证据（无 EXIT trap 文件、code_sha 不可解析、git 不可用）"]}
    return {"unchanged": not reasons, "method": "+".join(methods), "reasons": reasons}


def _selftest() -> int:
    fails: list[str] = []

    def chk(cond, msg):
        if not cond:
            fails.append(msg)

    # 1) 冻结区清单不许写错（少一个区 = 少一条纪律）
    chk(FROZEN_ZONES == ("code/life", "code/orchestration", "code/config", "code/engine"),
        f"冻结区清单被改动：{FROZEN_ZONES}")

    # 2) decide() 的「与」语义：任一路有改动就是 False
    chk(decide(trap_diff=[], rev_diff=[], new_status=None)["unchanged"] is True,
        "三路全干净应判 True")
    chk(decide(trap_diff=["code/life/agent.py"], rev_diff=[], new_status=None)["unchanged"] is False,
        "trap 有改动应判 False")
    chk(decide(trap_diff=[], rev_diff=["code/config/llm.json"], new_status=None)["unchanged"] is False,
        "rev diff 有改动应判 False")
    chk(decide(trap_diff=None, rev_diff=None, new_status=None)["unchanged"] is False,
        "无证据应判 False（不得静默 None/True）")
    chk(decide(trap_diff=None, rev_diff=None, new_status=None)["method"] == "unverifiable",
        "无证据时 method 应为 unverifiable")

    # 3) trap 文件解析：元信息行不算改动
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write("# trap\ncode_sha=abc123\nrc=0\n")
        clean = fh.name
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh2:
        fh2.write("# trap\ncode_sha=abc123\nrc=0\ncode/life/agent.py\n")
        dirty = fh2.name
    try:
        chk(_parse_trap_file(clean) == [], "干净 trap 文件应解析出 0 条改动")
        chk(_parse_trap_file(dirty) == ["code/life/agent.py"], "脏 trap 文件应解析出改动行")
        chk(_parse_trap_file("/nonexistent/x.txt") is None, "缺文件应返回 None")
    finally:
        import os
        os.unlink(clean)
        os.unlink(dirty)

    if fails:
        for f in fails:
            print(f"[selftest] FAIL: {f}", file=sys.stderr)
        return 1
    print(f"[selftest] OK: 冻结区 {len(FROZEN_ZONES)} 个；decide/trap 解析断言全通过")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="冻结区零改动取证（只读 git，零跑批）")
    ap.add_argument("--repo", default=str(ROOT), help="仓库根（默认本文件上两级）")
    ap.add_argument("--rev", default="HEAD", help="对比基准 commit（一般用 meta.code_sha）")
    ap.add_argument("--start-snapshot", default=None,
                    help="起跑时 git status --porcelain 快照文件（可选，用于 untracked 差集）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return _selftest()

    rev = a.rev
    if rev == "RUN_END":
        rc, out = _git(a.repo, "rev-parse", "HEAD")
        rev = out.strip()
    rd = frozen_diff(a.repo, rev)
    start = None
    if a.start_snapshot:
        try:
            start = Path(a.start_snapshot).read_text(encoding="utf-8").splitlines()
        except Exception:
            start = None
    ns = frozen_status_new(a.repo, start)
    ver = decide(trap_diff=None, rev_diff=rd, new_status=ns)

    if a.json:
        print(json.dumps({"rev": rev, "frozen_zones": list(FROZEN_ZONES),
                          "rev_diff": rd, "new_status": ns, **ver},
                         ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if ver["unchanged"] else (1 if ver["method"] != "unverifiable" else 2)
    print(f"# rev={rev} method={ver['method']} unchanged={ver['unchanged']}")
    for p in (rd or []):
        print(f"DIFF {p}")
    for p in (ns or []):
        print(f"DIRTY {p}")
    for r in ver["reasons"]:
        print(f"REASON {r}")
    return 0 if ver["unchanged"] else (1 if ver["method"] != "unverifiable" else 2)


if __name__ == "__main__":
    sys.exit(main())
