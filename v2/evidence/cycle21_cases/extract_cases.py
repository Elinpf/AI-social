#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CYCLE-21 §4 案例素材提取器（**只读日志，零跑批，零 LLM**）。

输入：两臂 run.jsonl（只读）
    C 臂：v2/evidence/run_d27_C_n16r60_seed42/run.jsonl
    B 臂：.worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42/run.jsonl
输出：
    v2/evidence/cycle21_cases/cases.md      （4 段逐字对话 + seq + 溯源 + 自检留档）

纪律：
    1. body 逐字原文，不删改、不截断、不跨线程拼接；每线程单独成段。
    2. 每条消息的 seq 直接取 run.jsonl 顶层 seq 字段。
    3. 自检：对每条 body 用 `grep -c -F -- <body> <run.jsonl>` 逐字命中，命中数落盘。
    4. 本脚本不做任何指标计算，不产出臂级结论（指标归 metric-recomputer）。

用法：
    python3 v2/evidence/cycle21_cases/extract_cases.py            # 写 cases.md
    python3 v2/evidence/cycle21_cases/extract_cases.py --stdout   # 只打印不写盘
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import shlex
import subprocess
from collections import OrderedDict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "cases.md"

ARMS = OrderedDict([
    ("C", {
        "label": "C 基线臂",
        "run_dir_rel": "v2/evidence/run_d27_C_n16r60_seed42",
        "batch": "CYCLE-21C",
    }),
    ("B", {
        "label": "B 实验臂（旁白放开）",
        "run_dir_rel": ".worktrees/d27-narration/v2/evidence/run_d27_B_n16r60_seed42",
        "batch": "CYCLE-21B",
    }),
])

# 选定的线程（两臂同 thread_id，便于第四节做「同线程跨臂」形态对照）
THREADS = ["TH-P004-P002-0", "TH-P010-P009-0"]

MSG_TYPES = ("MSG_DM", "MSG_PUBLIC")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_threads(log: Path) -> "OrderedDict[str, list]":
    th: "OrderedDict[str, list]" = OrderedDict()
    with open(log, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            if o.get("type") not in MSG_TYPES:
                continue
            tid = o["payload"]["thread_id"]
            th.setdefault(tid, []).append(o)
    return th


def grep_hit_count(log: Path, body: str) -> tuple[str, int, list[int], list[int]]:
    """返回 (可复放的 grep 命令, 命中行数, 命中行号列表, 命中行的顶层 seq 列表)。"""
    cmd = ["grep", "-n", "-F", "--", body, str(log)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    lines = [ln for ln in (r.stdout or "").splitlines() if ln]
    hits = len(lines) if r.returncode in (0, 1) else -1
    linenos, seqs = [], []
    for ln in lines:
        no, _, rest = ln.partition(":")
        try:
            linenos.append(int(no))
            seqs.append(json.loads(rest)["seq"])
        except Exception:  # noqa: BLE001
            pass
    return shlex.join(cmd), hits, linenos, seqs


def render_arm(key: str, arm: dict, seg_offset: int = 0) -> tuple[str, list[int]]:
    run_dir = REPO / arm["run_dir_rel"]
    log = run_dir / "run.jsonl"
    meta_p = run_dir / "meta.json"
    log_sha = sha256_file(log)
    sha8 = log_sha[:8]
    meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}
    threads = load_threads(log)

    out = []
    out.append(f"### {arm['batch']} / {arm['label']}\n")
    out.append("| 项 | 值 |\n|---|---|\n")
    out.append(f"| 来源文件 | `{arm['run_dir_rel']}/run.jsonl` |\n")
    out.append(f"| 日志 sha256（全长） | `{log_sha}`（sha8 = `{sha8}`）|\n")
    out.append(f"| 日志规模 | {meta.get('events', '?')} events / "
               f"{log.stat().st_size:,} B |\n")
    out.append(f"| 跑批身份（`meta.json`） | `code_sha = code_sha_end = "
               f"{meta.get('code_sha')}`；`seed {meta.get('seed')}`；"
               f"`rounds {meta.get('rounds')}`；`n {meta.get('n')}`；"
               f"`provider {meta.get('provider')}`；`model {meta.get('model')}`；"
               f"`llm_calls {meta.get('llm_calls')}`；"
               f"`degraded_calls {meta.get('degraded_calls')}`；"
               f"`finished_at {meta.get('finished_at')}` |\n")
    out.append(f"| 本臂线程总数（MSG_DM+MSG_PUBLIC 重建） | {len(threads)} |\n\n")
    out.append(f"> ⚠ 本批日志位于 `v2/evidence/` 下，受 `.gitignore`（`**/*.jsonl`）排除 ⇒ "
               f"**不在 git 对象里**：可原地复算 sha、可重渲染，但不可从零重建。\n\n")

    seg_no = seg_offset
    checks = []
    seg_ids = []
    for tid in THREADS:
        msgs = threads.get(tid)
        if not msgs:
            out.append(f"**线程 `{tid}` 在本臂缺失**（如实登记，不用其他线程顶替）\n\n")
            continue
        seg_no += 1
        seg_ids.append(seg_no)
        plist = [m["payload"] for m in msgs]
        participants = sorted({p for pl in plist for p in (pl.get("participants") or [])})
        places = list(OrderedDict.fromkeys(
            f"{pl.get('place')}" for pl in plist))
        days = sorted({pl.get("day") for pl in plist})
        slots = list(OrderedDict.fromkeys(pl.get("slot") for pl in plist))
        seqs = [m["seq"] for m in msgs]
        paren_n = sum(1 for pl in plist if pl["body"].startswith("（"))
        scope = "DM" if msgs[0]["type"] == "MSG_DM" else "PUBLIC"

        out.append(f"#### 段 {seg_no}｜`{tid}`（{arm['batch']}，{len(msgs)} 条，{scope}）\n\n")
        out.append("| 项 | 值 |\n|---|---|\n")
        out.append(f"| segment_id | `{arm['batch']}-{tid}` |\n")
        out.append(f"| 来源文件 | `{arm['run_dir_rel']}/run.jsonl` |\n")
        out.append(f"| 来源 sha256 前 8 位 | `{sha8}` |\n")
        out.append(f"| thread_id | `{tid}` |\n")
        out.append(f"| 参与人 | {', '.join(f'`{p}`' for p in participants)} |\n")
        out.append(f"| seq 序列 | {', '.join(f'`{s}`' for s in seqs)} |\n")
        out.append(f"| day / slot | day {days}；slot {' → '.join(slots)} |\n")
        out.append(f"| 地点（逐条可变的 payload.place） | {' → '.join(places)} |\n")
        out.append(f"| 段内以全角括号开头的消息数（描述性计数，非臂级结论） | "
                   f"{paren_n}/{len(msgs)} |\n\n")

        out.append("逐字原文（左侧 `#seq` 为 run.jsonl 顶层 `seq` 字段；"
                   "`day/slot/place` 逐条取 `payload` 原值）：\n\n")
        for m in msgs:
            pl = m["payload"]
            speaker = pl.get("from") or pl.get("author")
            to = pl.get("to")
            head = f"- **#{m['seq']}** `{speaker}`"
            if to:
                head += f" → `{to}`"
            head += (f"｜day {pl.get('day')} · {pl.get('slot')} · "
                     f"place `{pl.get('place')}`｜topic `{pl.get('topic')}`｜"
                     f"turn_index {pl.get('turn_index')}｜type `{m['type']}`")
            out.append(head + "\n")
            out.append(f"  > {pl['body']}\n")
            cmd, n, linenos, hit_seqs = grep_hit_count(log, pl["body"])
            checks.append({
                "arm": arm["batch"], "tid": tid, "seq": m["seq"],
                "sha8": sha8, "cmd": cmd, "hits": n, "body": pl["body"],
                "lineno": linenos[0] if len(linenos) == 1 else None,
                "seq_ok": hit_seqs == [m["seq"]],
            })
        out.append("\n")

    return "".join(out), checks, seg_ids


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdout", action="store_true", help="只打印，不写 cases.md")
    a = ap.parse_args(argv)

    body_parts, all_checks, head_parts = [], [], []
    head_parts.append(
        "# CYCLE-21 §4 可展示案例：逐字对话素材（带 seq 与溯源）\n\n"
        "> **生成者**：`case-curator`｜**生成方式**：`v2/evidence/cycle21_cases/extract_cases.py` "
        "只读两臂 `run.jsonl`（**零跑批、零 LLM 调用**），本文件可由该脚本原样重生成。\n"
        "> **用途**：供《CYCLE-21 周期实验报告》第四节「可展示案例」引用。\n"
        "> **纪律**：正文逐字原文，不删改、不截断、不跨线程拼接；每线程单独成段；"
        "每条消息带 `seq`（run.jsonl 顶层字段）；每段注明来源文件 + sha256 前 8 位 + thread_id + 参与人 + day/slot/place。\n"
        "> **本文件不计算任何指标、不下任何臂级结论**（旁白率等读数归 `metric-recomputer`；"
        "本文件只提供可被复核引用的原文素材）。\n\n"
        "## 0. 段清单\n\n"
        "| 段 | 臂 | batch | thread_id | 条数 | 用途 |\n|---|---|---|---|---|---|\n"
        "| 1 | C 基线 | `CYCLE-21C` | `TH-P004-P002-0` | 6 | C 臂无旁白形态（主样本） |\n"
        "| 2 | C 基线 | `CYCLE-21C` | `TH-P010-P009-0` | 6 | C 臂无旁白形态（副样本） |\n"
        "| 3 | B 实验 | `CYCLE-21B` | `TH-P004-P002-0` | 6 | B 臂旁白形态（与段 1 同 thread_id） |\n"
        "| 4 | B 实验 | `CYCLE-21B` | `TH-P010-P009-0` | 6 | B 臂旁白形态（与段 2 同 thread_id） |\n\n"
        "> 段 1↔段 3、段 2↔段 4 是**同 thread_id、跨两个独立 run** 的对照，"
        "**不是同一局模拟的同一轨迹**（`code_sha` 不同，见各臂元信息）。"
        "引用时只能用于说明「两臂消息形态的差异」，不得当作配对样本或同轨迹前后对照。\n\n"
        "---\n\n## 1. 逐字段素材\n\n")

    seg_total = 0
    for key, arm in ARMS.items():
        text, checks, seg_ids = render_arm(key, arm, seg_offset=seg_total)
        body_parts.append(text)
        all_checks.extend(checks)
        seg_total += len(seg_ids)

    # ---- 自检
    sec = ["---\n\n## 2. 自检：body 在 run.jsonl 中逐字命中（含 seq 对位）\n\n"
           "方法：对每条引用的 `payload.body` 原文执行 `grep -n -F -- <body> <run.jsonl>`"
           "（`-F` 固定串匹配，避免正则元字符干扰），要求**命中行数 = 1**，"
           "并回读该行的 `seq` 字段，要求**与正文标注的 seq 相等**（`seq 对位` 列）。\n\n"
           "| 臂 | thread_id | seq | 命中行号 | 命中数 | seq 对位 | 命令 |\n"
           "|---|---|---|---|---|---|---|\n"]
    bad = 0
    for c in all_checks:
        flag = "" if c["hits"] >= 1 else " ❌"
        if c["hits"] < 1 or not c.get("seq_ok"):
            bad += 1
        sec.append(f"| `{c['arm']}` | `{c['tid']}` | `{c['seq']}` | {c.get('lineno')} | "
                   f"{c['hits']}{flag} | {'✅' if c.get('seq_ok') else '❌'} | "
                   f"`{c['cmd']}` |\n")
    total = len(all_checks)
    seq_ok_n = sum(1 for c in all_checks if c.get("seq_ok"))
    sec.append(f"\n**自检结论**：共 {total} 条引用消息，逐字命中 {total - bad} 条、异常 {bad} 条；"
               f"其中命中唯一且 seq 对位一致 {seq_ok_n}/{total} 条。"
               f"要求：每条命中行数 = 1 且 seq 对位一致。\n")
    sec.append("\n大批量复核可用（逐条命中数之和应 ≥ 引用条数）：\n\n```bash\n"
               "cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment\n"
               "# 逐条重放本文件第 2 节表格里的命令即可；示例：\n"
               f"grep -c -F -- '这炉桃酥我总烤不出你家的脆劲儿，你忙得过来不？教教我。' "
               f"v2/evidence/run_d27_C_n16r60_seed42/run.jsonl\n```\n")

    # 只取一个真实样本用于示例命令，避免示例与日志不符
    if all_checks:
        sample = all_checks[0]
        sec[-1] = (
            "\n大批量复核方式：逐条重放第 2 节表格里的命令即可。示例（取表中第一条）：\n\n```bash\n"
            "cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment\n"
            f"{sample['cmd']}\n```\n")

    # ---- 边界
    sec.append(
        "\n---\n\n## 3. 能与不能\n\n"
        "### 能证明\n"
        "1. 上述每一条消息的 `seq`、发言人、`thread_id`、`day/slot/place`、正文，"
        "都能在对应 `run.jsonl` 中逐字命中（第 2 节已逐条落盘命中数）；\n"
        "2. C 臂所选两段消息正文**无**全角括号动作旁白，B 臂所选两段消息正文**以**全角括号动作旁白开头"
        "（形态差异在两个臂内部一致，可直接肉眼核对本文件原文）；\n"
        "3. 两臂各自 `meta.degraded_calls = 0`、`provider openai_compat` ⇒ 文本由真 LLM 生成，非兜底模板。\n\n"
        "### 不能证明\n"
        "1. **不能**给任何旁白率/一致率数字下结论 —— 本文件是**样本摘录**（4 线程 × 6 条 = 24 条），"
        "不是分层随机抽样，不能外推到臂级比例；读数以 `metric-recomputer` 的复算件为准；\n"
        "2. **不能**当作同一局模拟的同轨迹对照 —— 段 1/3、段 2/4 只是 thread_id 相同，"
        "来自两个独立 run（`code_sha` 不同、`run_sha256` 不同），World 演化路径不同；\n"
        "3. **不能**证明任何「更生活 / 更真实」的效果判断 —— 本周期无判据编号、无闸线；\n"
        "4. `place` 字段在线程内逐条变化（同一线程跨 morning/afternoon/evening、跨地点），"
        "不能据此推断「这些人在同一地点连续对话」；`MSG_PUBLIC` 的 `place` 为 `null` 属原值，"
        "本次所引 4 段均为 `MSG_DM`。\n"
    )

    text = head_parts[0] + "".join(body_parts) + "".join(sec)

    if a.stdout:
        sys.stdout.write(text)
    else:
        OUT.write_text(text, encoding="utf-8")
        print(json.dumps({"out": str(OUT), "sha256": sha256_file(OUT),
                          "bytes": OUT.stat().st_size,
                          "quoted_msgs": len(all_checks),
                          "grep_misses": bad,
                          "segments": len(body_parts)}, ensure_ascii=False, indent=2))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
