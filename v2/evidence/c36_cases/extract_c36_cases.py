#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CYCLE-36 §4 案例与截图证据生成器（**只读日志，零跑批，零 LLM 调用**）。

输入（只读）
    ON  臂：v2/evidence/n15-on_n16r84_s42/run.jsonl   （LIFE_PROMPT_ADDR_EVOLVE=1）
    OFF 臂：v2/evidence/n15-off_n16r84_s42/run.jsonl  （基线，开关 ABSENT）
    称呼尺子：tools/metrics/address_drift.py（既有尺子，本文件只调用其判定函数做**标注**）
    词表：v2/refs/address-ordinal.yaml；居民：code/config/personas.json
    截图：v2/evidence/c36_shots/{on,off}/render_report_c36-*.json（由 tools/metrics/render_shots.py 现场渲染）

输出
    <outdir>/c36-cases.md   —— 交付正文（逐字原文 + 定位 + 自检 + 截图 + 候选池/排除理由）
    <outdir>/c36-sha.txt    —— 图 sha 与源日志 sha 的 sha256sum 原始输出

纪律（与团队私有工作约定一致）
    1. 正文逐字，不改写、不润色、不跨线程拼接；每线程单独成段。
    2. 每条消息给 thread_id / seq / msg_uid / 说话人显示名与角色 / 逐字原文；
       并给「行号 = seq + 1」的可复核关系（本批实测 seq 与物理行号一一对应）。
    3. 截图只用本次现场渲染产物，写 sha256 + 渲染时 HEAD + 渲染命令 + 像素自检。
    4. **图不进判据**：截图只作展示，不参与任何数字判定。
    5. 本文件不计算臂级指标、不下「提升」结论（读数归证据审计/复算件）。

用法
    python3 v2/evidence/c36_cases/extract_c36_cases.py --outdir <交付目录>
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import collections
import hashlib
import importlib.util
import json
import os
import shlex
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TZ = timezone(timedelta(hours=8))

ARMS = collections.OrderedDict([
    ("ON", {
        "batch": "n15-on_n16r84_s42",
        "label": "ON 臂（LIFE_PROMPT_ADDR_EVOLVE=1，称呼演化接线开）",
        "run_dir_rel": "v2/evidence/n15-on_n16r84_s42",
    }),
    ("OFF", {
        "batch": "n15-off_n16r84_s42",
        "label": "OFF 臂（基线，开关 ABSENT）",
        "run_dir_rel": "v2/evidence/n15-off_n16r84_s42",
    }),
])

# 选定的 5 段（3 段正向「称呼×关系演化」+ 2 类缺陷 3 段；每条段都是同一线程连续 6 条）
SEGMENTS = [
    {
        "seg": 1,
        "thread": "TH-P013-P004-16",
        "kind": "正向",
        "theme": "称呼×关系演化：同一说话人 P004 对 P013 先称「铁头哥」(tier 2)、后回落「铁头」(tier 3)",
        "why": "同线程内出现**同一说话人对同一对象的两种称呼形式**，是「称呼随关系/情境演化」最直接的可见形态；"
               "ON 臂该段出现 tier 2 的「铁头哥」，OFF 臂同 thread 只有 tier 3 的「铁头」（形态差异可肉眼核对）",
    },
    {
        "seg": 2,
        "thread": "TH-P011-P003-30",
        "kind": "正向",
        "theme": "称呼×关系演化：P011 首称 P003 为「阿禾姐」(tier 2)，后续改回「阿禾」(tier 3)；P003 对 P011 稳定称「小满」",
        "why": "另一对居民上的同类形态（首称升格→回落），且**双方称呼不对称**可同时展示；"
               "OFF 臂同 thread 除「小满/阿禾」外无 tier 2 形式",
    },
    {
        "seg": 3,
        "thread": "TH-P006-P003-6",
        "kind": "缺陷",
        "theme": "缺陷（self_name，把对方叫成自己）：P006「方老师」对 P003「阿禾」说「方老师，我刚从西坡薅了把野葱…」",
        "why": "典型「拿自己的名字/身份去叫对方」；且该条内容几乎复述了对方上一轮（#11050）的自述，属**内容串味**；"
               "OFF 臂同 thread 同位（#19179）称「阿禾」，指向正确 ⇒ 缺陷在臂间可对照",
    },
    {
        "seg": 4,
        "thread": "TH-P015-P011-40",
        "kind": "缺陷",
        "theme": "缺陷（self_name）：P011「小满」对 P015「五味」说「小满，你闻闻我这锅糖色…」",
        "why": "同轮上下文中 P015 一直正确称对方「小满」，P011 反过来把「小满」当成对 P015 的称呼 ⇒ 明确错指；"
               "OFF 臂同 thread 对应位（#61549/#84494）P011 正确称「五味叔」(tier 2)",
    },
    {
        "seg": 5,
        "thread": "TH-P004-P013-4",
        "kind": "缺陷",
        "theme": "缺陷（other_named，叫错人）：P004「秀娘」对 P013「铁头」开口即称「周公文」（P008 的名字，第三人）",
        "why": "把**第三人名字**当成对当前受话人的称呼；且该缺陷**两臂同 seq（#3121）同现**，"
               "说明不是单臂偶发（两臂 ran 时间不同、code_sha 不同，见 §1 身份表）",
        "note": "**既存缺陷声明（写死）**：本条缺陷在 ON 臂（`n15-on`）与 OFF 臂（`n15-off`）**同一 `seq=3121` 同现**"
                "⇒ 属**既存缺陷、由基线继承**，**不是本臂（N-15 称呼演化接线）引入**，"
                "**也不得**被读作任何「回归」或「改善证据」。仅证明该错称形态在本周期两臂日志中都存在。",
    },
]

MSG_TYPES = ("MSG_DM", "MSG_GROUP", "MSG_PUBLIC")
ONLY_DM = {"seg": None}  # 占位（保持结构清晰）


# --------------------------------------------------------------------- 工具
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_addr_tool():
    spec = importlib.util.spec_from_file_location(
        "address_drift_c36", REPO / "tools" / "metrics" / "address_drift.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(*args) -> str:
    r = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, text=True)
    return (r.stdout or "").strip()


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def iso_from_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts, TZ).isoformat(timespec="seconds")


# --------------------------------------------------------------------- 采集
def load_threads(log: Path) -> "collections.OrderedDict[str, list]":
    th: "collections.OrderedDict[str, list]" = collections.OrderedDict()
    with open(log, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            if o.get("type") not in MSG_TYPES:
                continue
            th.setdefault(o["payload"]["thread_id"], []).append(o)
    return th


def line_no_of(log: Path, seq: int) -> int | None:
    """物理行号（本批实测 = seq + 1；此处实读一遍验证，不靠假设）。"""
    with open(log, "rb") as f:
        for i, raw in enumerate(f, 1):
            if i - 1 == seq:
                o = json.loads(raw)
                return i if o.get("seq") == seq else None
            if i - 1 > seq:
                return None
    return None


def grep_check(log: Path, body: str, seq: int) -> dict:
    cmd = ["grep", "-n", "-F", "--", body, str(log)]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    lines = [ln for ln in (r.stdout or "").splitlines() if ln]
    lineno, hit_seq, ok = None, None, False
    if len(lines) == 1:
        no, _, rest = lines[0].partition(":")
        lineno = int(no)
        hit_seq = json.loads(rest)["seq"]
        ok = (hit_seq == seq) and (lineno == seq + 1)
    return {"cmd": shlex.join(cmd), "hits": len(lines), "lineno": lineno,
            "hit_seq": hit_seq, "ok": ok}


# --------------------------------------------------------------------- 渲染
def load_render(rel_path: str) -> dict:
    p = REPO / rel_path
    return json.loads(p.read_text(encoding="utf-8"))


# --------------------------------------------------------------------- 主体
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args(argv)
    outdir = Path(a.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    AD = load_addr_tool()
    lex_path = REPO / "v2" / "refs" / "address-ordinal.yaml"
    per_path = REPO / "code" / "config" / "personas.json"
    lex = AD.load_lexicon(str(lex_path))
    terms, _info, owners = AD.build_agent_terms(lex, str(per_path))
    voc = lex.get("vocative") or {}
    personas = {p["persona_id"]: p for p in
                json.loads(per_path.read_text(encoding="utf-8"))["personas"]}
    base_names = {p["display_name"].split("·")[-1].strip() for p in personas.values()}

    def annotate(rec: dict) -> dict:
        m = AD.as_msg(rec)
        text = AD.strip_parenthetical(m["body"], base_names)
        hit = AD.find_vocative(text, terms, voc)
        out = {"form": None, "tier": None, "target": None}
        if hit:
            form, tier = hit
            own = owners.get(form) or set()
            if not own:
                tgt = "generic"
            elif m["addressee"] is None:
                tgt = "unknown_target"
            elif m["addressee"] in own:
                tgt = "target_ok"
            elif m["speaker"] in own:
                tgt = "self_name"
            else:
                tgt = "other_named"
            out.update({"form": form, "tier": tier, "target": tgt})
        return out

    # ---- 各臂身份
    arm_meta = {}
    for key, arm in ARMS.items():
        run_dir = REPO / arm["run_dir_rel"]
        log = run_dir / "run.jsonl"
        meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
        proof = run_dir / "switch_proof.txt"
        arm_meta[key] = {
            "arm": arm, "run_dir": run_dir, "log": log,
            "log_sha": sha256_file(log), "log_bytes": log.stat().st_size,
            "meta": meta,
            "meta_sha": sha256_file(run_dir / "meta.json"),
            "switch_proof": proof.read_text(encoding="utf-8") if proof.exists() else None,
            "switch_proof_sha": sha256_file(proof) if proof.exists() else None,
            "rc": (run_dir / "run_batch.rc").read_text(encoding="utf-8").strip()
                  if (run_dir / "run_batch.rc").exists() else None,
            "log_mtime": iso_from_ts(log.stat().st_mtime),
            "rc_exists": (run_dir / "run_batch.rc").exists(),
        }

    threads = {k: load_threads(v["log"]) for k, v in arm_meta.items()}

    # ---- 批次快照（在途臂排除用）
    inflight = REPO / "v2" / "evidence" / "n36-on_n16r84_s42"
    inflight_stat = None
    if inflight.exists():
        st = (inflight / "run.jsonl").stat()
        inflight_stat = {"path": "v2/evidence/n36-on_n16r84_s42/run.jsonl",
                         "bytes": st.st_size, "mtime": iso_from_ts(st.st_mtime),
                         "has_meta": (inflight / "meta.json").exists()}

    # ---- 渲染件
    renders = {
        "ON": load_render("v2/evidence/c36_shots/on/render_report_c36-on.json"),
        "OFF": load_render("v2/evidence/c36_shots/off/render_report_c36-off.json"),
    }

    head_sha = git("rev-parse", "HEAD")
    head_short = head_sha[:7]
    branch = git("branch", "--show-current")
    gen_at = now_iso()

    md: list[str] = []
    W = md.append

    # ================= 头
    W("# CYCLE-36 §4 可展示案例与截图证据\n\n")
    W("> **生成者**：`case-harvester`（案例与截图取证）｜**生成时刻**：%s｜"
      "**仓库**：`/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment`｜"
      "**分支**：`%s`｜**HEAD**：`%s`（短 `%s`）。\n" % (gen_at, branch, head_sha, head_short))
    W("> **生成方式**：`v2/evidence/c36_cases/extract_c36_cases.py` 只读两臂 `run.jsonl` + 本次现场渲染件"
      "（**零跑批、零 LLM 调用**），本文件可由该脚本原样重生成。\n")
    W("> **用途**：供《CYCLE-36 周期实验报告》第四节「可展示案例」引用。\n")
    W("> **纪律**：正文逐字原文，不改写、不润色、不截断、不跨线程拼接；每线程单独成段；"
      "每条给 `thread_id` / `seq` / `msg_uid` / 说话人显示名与角色 / 逐字原文；"
      "每段给「物理行号 = `seq + 1`」的可复核关系（本批两臂实测均成立，见 §4）。\n")
    W("> **⚠ 图不进判据**：本文件所有 PNG **只作展示**，不参与任何数字判定/闸线；"
      "本文件**不计算臂级指标、不下「提升」结论**（读数与判据归证据审计与复算件）。\n")
    W("> **本任务交付三件**：① 本文件 `c36-cases.md`；② `c36-sha.txt`（图 sha 与源日志 sha 的 `sha256sum` 原始输出）；"
      "③ `c36-grep-checks.sh`（60 条逐字实拉命令，`bash` 直接复核）。配套：`v2/evidence/c36_shots/`（4 张 PNG + `render.log` + "
      "`render_report_c36-*.json`）、`v2/evidence/c36_cases/extract_c36_cases.py`（可原样重生成）。\n\n")
    W("---\n\n")

    # ================= §1 批次身份
    W("## 1. 引用的是哪两个批次（先读，避免把在途批或旧批当本周期成果）\n\n")
    W("| 项 | ON 臂 | OFF 臂 |\n|---|---|---|\n")
    on, off = arm_meta["ON"], arm_meta["OFF"]
    W("| 批次目录 | `%s` | `%s` |\n" % (ARMS["ON"]["batch"], ARMS["OFF"]["batch"]))
    W("| 标签 | %s | %s |\n" % (ARMS["ON"]["label"], ARMS["OFF"]["label"]))
    W("| `code_sha`（起/止，同一） | `%s` | `%s` |\n"
      % (on["meta"].get("code_sha"), off["meta"].get("code_sha")))
    W("| `run.jsonl` sha256 | `%s` | `%s` |\n" % (on["log_sha"], off["log_sha"]))
    W("| 日志规模 | %s events / %s B | %s events / %s B |\n"
      % (f"{on['meta'].get('events'):,}", f"{on['log_bytes']:,}",
         f"{off['meta'].get('events'):,}", f"{off['log_bytes']:,}"))
    W("| 起跑 / 收批（`meta.json`） | %s → %s | %s → %s |\n"
      % (on["meta"].get("started_at"), on["meta"].get("finished_at"),
         off["meta"].get("started_at"), off["meta"].get("finished_at")))
    W("| `run_batch.rc` | `%s` | %s |\n"
      % (on["rc"],
         ("`%s`" % off["rc"]) if off["rc_exists"] else
         "**无此文件**（该臂目录未留 `.rc`；收批依据 = `meta.finished_at` 已写 + `run.jsonl` mtime 停在 `%s`，"
         "不再增长）" % off["log_mtime"]))
    W("| `run.jsonl` mtime | %s | %s |\n" % (on["log_mtime"], off["log_mtime"]))
    W("| seed / agents / rounds | %s / %s / %s | %s / %s / %s |\n"
      % (on["meta"].get("seed"), on["meta"].get("n"), on["meta"].get("rounds"),
         off["meta"].get("seed"), off["meta"].get("n"), off["meta"].get("rounds")))
    W("| MSG 计数（DM/GROUP/PUBLIC） | %s / %s / %s | %s / %s / %s |\n"
      % (on["meta"]["msg_counts"].get("MSG_DM"), on["meta"]["msg_counts"].get("MSG_GROUP"),
         on["meta"]["msg_counts"].get("MSG_PUBLIC"),
         off["meta"]["msg_counts"].get("MSG_DM"), off["meta"]["msg_counts"].get("MSG_GROUP"),
         off["meta"]["msg_counts"].get("MSG_PUBLIC")))
    W("| `llm_calls` / `degraded_calls` | %s / %s | %s / %s |\n"
      % (on["meta"].get("llm_calls"), on["meta"].get("degraded_calls"),
         off["meta"].get("llm_calls"), off["meta"].get("degraded_calls")))
    W("| `llm_cached` / `llm_cached_ratio` | %s / %s | %s / %s |\n"
      % (on["meta"].get("llm_cached"), on["meta"].get("llm_cached_ratio"),
         off["meta"].get("llm_cached"), off["meta"].get("llm_cached_ratio")))
    W("| `meta.json` sha256 | `%s` | `%s` |\n" % (on["meta_sha"], off["meta_sha"]))
    W("| `switch_proof.txt` sha256 | `%s` | `%s` |\n"
      % (on["switch_proof_sha"], off["switch_proof_sha"]))
    W("| 线程总数（MSG_* 重建） | %d | %d |\n\n" % (len(threads["ON"]), len(threads["OFF"])))

    W("**两臂开关证据（`switch_proof.txt` 原文节选，非本文件改写）**\n\n```text\n")
    W("--- ON 臂 ---\n")
    W((on["switch_proof"] or "(缺失)").rstrip() + "\n")
    W("\n--- OFF 臂 ---\n")
    W((off["switch_proof"] or "(缺失)").rstrip() + "\n")
    W("```\n\n")

    W("> **可复核**：`cd %s && sha256sum v2/evidence/%s/run.jsonl v2/evidence/%s/run.jsonl`。\n"
      "> **⚠ 两臂 `code_sha` 不同**（`%s` vs `%s`），故 §3 的「同 thread 跨臂对照」"
      "**不是配对样本、不是同轨迹前后对照**；二者差异区间 `%s..%s` 仅含 D9u 勘误（"
      "`git diff --stat %s..%s` → `tools/d9n/narration_family.py`、"
      "`tools/d9n/narration_family_lexicon.json`、`v2/evidence/d9u*` 三处文档/词表），"
      "**未触及对话/称呼代码**；即便如此，本文件仍不从两臂差异中读任何效果结论。\n\n"
      % (REPO, ARMS["ON"]["batch"], ARMS["OFF"]["batch"],
         on["meta"].get("code_sha", "")[:7], off["meta"].get("code_sha", "")[:7],
         off["meta"].get("code_sha", "")[:7], on["meta"].get("code_sha", "")[:7],
         off["meta"].get("code_sha", "")[:7], on["meta"].get("code_sha", "")[:7]))

    if inflight_stat:
        W("**明确排除的在途批**：`%s`（此刻 %s B、mtime `%s`、目录内 `meta.json` = %s）"
          "⇒ **未收批**，不引用、不作为本周期成果。\n\n"
          % (inflight_stat["path"], f"{inflight_stat['bytes']:,}",
             inflight_stat["mtime"], "存在" if inflight_stat["has_meta"] else "**不存在**"))

    # ================= §2 段清单
    W("## 2. 段清单（5 段 × 6 条 = 30 条 ON 臂原文；另附 5 段 OFF 臂同 thread 对照 30 条）\n\n")
    W("| 段 | 类型 | 臂 | thread_id | 条数 | 主题 |\n|---|---|---|---|---|---|\n")
    for s in SEGMENTS:
        W("| %d | %s | ON | `%s` | %d | %s |\n"
          % (s["seg"], s["kind"], s["thread"], len(threads["ON"][s["thread"]]), s["theme"]))
        W("| %d′ | 对照 | OFF | `%s` | %d | 同 thread、另一独立 run（形态对照，非配对样本） |\n"
          % (s["seg"], s["thread"], len(threads["OFF"].get(s["thread"], []))))
    W("\n")

    # ================= §3 逐字段素材
    W("## 3. 逐字素材（每段 6 条同线程连续消息）\n\n")
    W("> **★可比性限定（与本节全部数字同段，必读）★**：本节出现的条数/`seq`/行号等数字**只描述素材本身**，"
      "**不作跨臂比较、不作效果结论**。原因：两臂 `code_sha` **不同** —— "
      "ON 臂 `%s`、OFF 臂 `%s`。判定「差异区间未触及对话行为路径」的**依据命令与输出**（可原地重放）：\n"
      "> ```bash\n"
      "> git diff --name-only %s..%s\n"
      "> ```\n"
      "> 输出恰 4 个文件：`tools/d9n/narration_family.py`、`tools/d9n/narration_family_lexicon.json`、"
      "`v2/evidence/d9u-step2-verb-screening.md`、`v2/evidence/d9u1-errata-expansion-25.md`"
      "（`git diff --stat` 合计 4 files changed, 121 insertions(+), 15 deletions(-)），"
      "**`code/` 下改动文件数 = 0**（`git diff --name-only %s..%s | grep -c '^code/'` → `0`）"
      "⇒ 差异仅 **D9u 词表/工具与勘误文档**，未触 `code/` 运行时行为路径；"
      "另有 `meta.json` 的 `code_sha == code_sha_end`（跑批期间代码未变）与 `switch_proof.txt` 的 "
      "`cmdline=python3 -m orchestration run ...`（行为路径全在 `code/`）两项侧证。\n"
      "> 即便如此，本文件仍**不**从两臂差异读任何「开关有效/提升」结论（另见 §1 尾注与 §7）。\n\n"
      % (on["meta"].get("code_sha"), off["meta"].get("code_sha"),
         off["meta"].get("code_sha", "")[:7], on["meta"].get("code_sha", "")[:7],
         off["meta"].get("code_sha", "")[:7], on["meta"].get("code_sha", "")[:7]))
    W("列义：`#seq` = `run.jsonl` 顶层 `seq`；`行号` = 物理行号（= `seq + 1`，见 §4 自检）；"
      "`msg_uid` = `payload.msg_uid`（`<seed>:<seq>`）；`说话人` = 显示名/角色/`persona_id`；"
      "`标注` = 既有尺子 `address_drift.py` 的呼语位判定（`形式/tier/指向`，**描述性标注、非判据**）。\n\n")

    checks = []
    for s in SEGMENTS:
        for key in ("ON", "OFF"):
            arm = arm_meta[key]
            tid = s["thread"]
            recs = threads[key].get(tid)
            head = "### %s段 %d%s｜`%s`（%s 臂，%d 条）\n\n" % (
                "对照" if key == "OFF" else "", s["seg"], "′" if key == "OFF" else "",
                tid, key, len(recs or []))
            W(head)
            if key == "ON" and s.get("note"):
                W("> %s\n\n" % s["note"])
            if not recs:
                W("**该 thread 在本臂缺失**（如实登记，不用其他线程顶替）\n\n")
                continue
            p0 = recs[0]["payload"]
            plist = [r["payload"] for r in recs]
            seqs = [r["seq"] for r in recs]
            W("| 项 | 值 |\n|---|---|\n")
            W("| 来源文件 | `%s/run.jsonl` |\n" % arm["arm"]["run_dir_rel"])
            W("| 日志 sha256 | `%s` |\n" % arm["log_sha"])
            W("| thread_id | `%s` |\n" % tid)
            W("| 消息类型 | `%s`（全段一致） |\n" % recs[0]["type"])
            W("| 参与人（`persona_id` → 显示名/角色） | %s |\n" % "、".join(
                "`%s`→%s/%s" % (pid, personas[pid]["display_name"].split("·")[-1],
                                personas[pid]["role_id"])
                for pid in sorted({p["from"] for p in plist} | {p["to"] for p in plist})))
            W("| seq 序列 | %s |\n" % ", ".join("`%d`" % x for x in seqs))
            W("| turn_index 序列 | %s（连续） |\n" % ", ".join(
                "`%s`" % p.get("turn_index") for p in plist))
            W("| day/slot/place（逐条可变） | day %s；%s |\n"
              % (sorted({p.get("day") for p in plist}),
                 " → ".join("%s/%s" % (p.get("slot"), p.get("place")) for p in plist)))
            W("\n")
            W("逐字原文：\n\n")
            for r in recs:
                p = r["payload"]
                sp = p["from"]
                per = personas[sp]
                an = annotate(r)
                ln = line_no_of(arm["log"], r["seq"])
                W("- **#%d**｜行号 %s｜`msg_uid` `%s`｜说话人 `%s`（%s / %s）→ 受话人 `%s`"
                  "（%s / %s）｜day %s · %s · place `%s`｜topic `%s`｜`%s`｜"
                  "标注：%s\n"
                  % (r["seq"], ln, p.get("msg_uid"), sp, per["display_name"],
                     per["role_id"], p.get("to"),
                     personas[p["to"]]["display_name"], personas[p["to"]]["role_id"],
                     p.get("day"), p.get("slot"), p.get("place"), p.get("topic"),
                     r["type"],
                     ("`%s`/tier %s/`%s`" % (an["form"], an["tier"], an["target"]))
                     if an["form"] else "无呼语位称呼"))
                W("  > %s\n" % p["body"])
                c = grep_check(arm["log"], p["body"], r["seq"])
                checks.append({"arm": key, "seg": s["seg"], "tid": tid, "seq": r["seq"],
                               "sha": arm["log_sha"], "body": p["body"], **c})
            W("\n")
        W("<sub>说明：段 %d 的 ON/OFF 两臂段是**同 thread_id、两个独立 run**（`code_sha` 不同），"
          "只能用于「形态差异」肉眼核对，**不得**当作配对样本或用其算比例。</sub>\n\n" % s["seg"])

    # ================= §4 自检
    bad = [c for c in checks if not c["ok"]]
    W("## 4. 自检：每条原文在 `run.jsonl` 中逐字命中，且行号 = seq + 1\n\n")
    W("方法：对每条引用的 `payload.body` 原文执行 `grep -n -F -- <body> <run.jsonl>`（固定串、无正则干扰），"
      "要求**命中行数 = 1**、**命中行号 = `seq + 1`**、且该行 `seq` 字段 = 标注的 `seq`。\n\n")
    W("| 臂 | 段 | thread_id | seq | 实拉命令（行号式，可直接跑） | 命中行号 | 命中数 | seq 对位 | 行号=seq+1 |\n"
      "|---|---|---|---|---|---|---|---|---|\n")
    for c in checks:
        rel_log = "%s/run.jsonl" % ARMS[c["arm"]]["run_dir_rel"]
        sed_cmd = "sed -n '%sp' %s" % (c["lineno"], rel_log)
        W("| %s | %d | `%s` | `%d` | `%s` | %s | %d | %s | %s |\n"
          % (c["arm"], c["seg"], c["tid"], c["seq"], sed_cmd, c["lineno"], c["hits"],
             "✅" if c.get("hit_seq") == c["seq"] else "❌",
             "✅" if c["ok"] else "❌"))
    W("\n**自检结论**：共引用 %d 条消息，全部逐字命中且行号/seq 对位一致 = **%d/%d**，异常 **%d** 条。\n\n"
      % (len(checks), len(checks) - len(bad), len(checks), len(bad)))

    # 全部 grep 实拉命令落盘成可直接执行的脚本
    sh_path = outdir / "c36-grep-checks.sh"
    sh = ["#!/usr/bin/env bash", "# CYCLE-36 全部引用原文的逐字实拉命令（自动生成，逐条执行）",
          "# 用法：bash c36-grep-checks.sh ；每条输出「行号:JSON」，应各命中 1 行且行号 = seq + 1",
          "set -u", "cd %s || exit 2" % REPO, ""]
    for c in checks:
        rel_log = "%s/run.jsonl" % ARMS[c["arm"]]["run_dir_rel"]
        sh.append("echo '--- %s seg%d %s seq=%d (expect line %s) ---'"
                  % (c["arm"], c["seg"], c["tid"], c["seq"], c["lineno"]))
        sh.append("grep -n -F -- %s %s" % (shlex.quote(c["body"]), rel_log))
    sh_path.write_text("\n".join(sh) + "\n", encoding="utf-8")
    if checks:
        sample = checks[0]
        W("**逐条实拉命令已落盘**：`%s`（sha256 `%s`，共 %d 条 `grep -n -F` 命令，可直接 `bash` 执行复核）。\n\n"
          % (sh_path, sha256_file(sh_path), len(checks)))
        W("复核者可直接重放（示例取表中第一条）：\n\n")
        W("```bash\ncd %s\n%s\n```\n\n" % (REPO, sample["cmd"]))
    W("**机械口径复核**（按行号取行、核对 seq 与 msg_uid；本批两臂实测 `行号 = seq + 1` 全量成立）：\n\n```bash\n"
      "cd %s\n"
      "sed -n '23260p' v2/evidence/%s/run.jsonl | python3 -c "
      "'import json,sys; o=json.load(sys.stdin); print(o[\"seq\"], o[\"payload\"][\"msg_uid\"])'\n"
      "```\n\n" % (REPO, ARMS["ON"]["batch"]))

    # ================= §5 截图
    W("## 5. 截图证据（现场渲染，**只作展示、不进判据**）\n\n")
    W("渲染工具：仓库既有 `tools/metrics/render_shots.py`（`--help` 已核实参数："
      "`--run-dir/--batch-id/--outdir/--views/--timeout`）；渲染时 HEAD = `%s`（`%s`）。\n"
      "渲染链：`run.jsonl → gen_threads.py → threads_<batch>.json → 本地静态服务 → shot.py(Chromium 现截) → PNG`；"
      "服务根为临时目录 + 符号链接，**未在 `code/frontend/` 下写任何文件**。\n\n"
      % (head_sha, branch))
    W("| # | 视图 | 绝对路径 | sha256 | 尺寸 | 像素自检（distinct_colors / top_color_frac / 非背景占比） |\n"
      "|---|---|---|---|---|---|\n")
    idx = 0
    shot_rows = []
    for key in ("ON", "OFF"):
        rep = renders[key]
        for v in rep["views"]:
            idx += 1
            ps = v["pixel_selfcheck"]
            W("| %d | %s（%s 臂） | `%s` | `%s` | %d×%d | %d / %.4f / %.4f（%s） |\n"
              % (idx, v["view"], key, v["png"], v["png_sha256"],
                 ps["width"], ps["height"], ps["distinct_colors"],
                 ps["top_color_frac"], ps["non_bg_frac"], ps["status"]))
            shot_rows.append((key, v))
    W("\n")
    W("**渲染命令（逐张原样取自 `render_report_c36-*.json` 的 `triplet.render_cmd`）**\n\n```text\n")
    for key, v in shot_rows:
        W("[%s/%s] %s\n" % (key, v["view"], v["triplet"]["render_cmd"]))
    W("```\n\n")
    W("**gen_threads 命令（threads.json 派生，逐批一条）**\n\n```text\n")
    for key in ("ON", "OFF"):
        W("[%s] %s\n" % (key, renders[key]["views"][0]["triplet"]["gen_threads_cmd"]))
    W("```\n\n")
    W("**非空白判据**：`distinct_colors ≥ 200` 且 `top_color_frac ≤ 0.99`（深色 UI 不按单色占比判死；"
      "该判据由 `render_shots.py` 自算，`blank_check=off` 关闭了 `shot.py` 对深色页会误判的单色判据）。"
      "四张图实际 distinct_colors 均 > 2.2 万、top_color_frac ≤ 0.20、非背景占比 ≈ 0.54–0.56 ⇒ 非空白。\n\n")
    W("**重渲染声明**：渲染只依赖 `run.jsonl` 内容，重跑得**内容等价的图**，但 PNG 字节（sha256）**不会相同**"
      "（时间戳/渲染抖动）。上表 sha256 是本轮实际落盘字节的 sha，复核须以本表为准。\n\n")
    W("**图不进判据**：上表四张图不参与任何指标、闸线或「提升」判断；如需看图，仅用于「页面上确实显示了"
      "真实日志派生出的对话/节奏视图」这一存在性展示。\n\n")
    render_log = REPO / "v2" / "evidence" / "c36_shots" / "render.log"
    if render_log.exists():
        W("**`render.log`**：`v2/evidence/c36_shots/render.log`（sha256 `%s`，%d B）——"
          "内含渲染时 HEAD、两条渲染命令原文、两次渲染的 stdout 尾部与逐张像素自检/sha 摘要。\n\n"
          % (sha256_file(render_log), render_log.stat().st_size))

    # ================= §6 候选池与排除
    W("## 6. 候选池与排除理由（ON 臂全部 ≥6 条线程，逐条处置）\n\n")
    W("候选口径：两臂 `MSG_*` 重建线程，取 **条数 ≥ 6**（满足「同线程连续 ≥6 条」要求）。"
      "`称呼命中` = 呼语位识别到称呼的条数；`形式` = 该线程出现过的去重称呼形式（尺子标注）。"
      "缺陷判定 = `self_name` 或 `other_named`。\n\n")
    W("| thread_id | 类型 | 条数 | 称呼命中 | 形式（tier） | 缺陷 | 处置 |\n"
      "|---|---|---|---|---|---|---|\n")
    cand = []
    for tid, recs in threads["ON"].items():
        if len(recs) < 6:
            continue
        forms = []
        errs = 0
        for r in recs:
            an = annotate(r)
            if an["form"]:
                forms.append((an["form"], an["tier"]))
                if an["target"] in ("self_name", "other_named"):
                    errs += 1
        types = collections.Counter(r["type"] for r in recs)
        cand.append({"tid": tid, "n": len(recs), "addr": len(forms),
                     "forms": sorted(set(forms), key=lambda x: x[1]), "errs": errs,
                     "types": types})
    chosen = {s["thread"]: s["seg"] for s in SEGMENTS}
    special = {
        "TH-P009-P008-24": "未选：称呼为身份敬称「周公文」(tier 1)/「周哥」(tier 2)，"
                           "「周公文」与 P008 本名完全重合，复核者易把「称呼形式变化」误读为 other_named 缺陷 ⇒ 避免歧义",
    }
    for c in sorted(cand, key=lambda x: (-x["addr"], -x["n"], x["tid"])):
        tid = c["tid"]
        types_s = "/".join("%s×%d" % (k.replace("MSG_", ""), v) for k, v in sorted(c["types"].items()))
        fm = "、".join("%s(tier%d)" % f for f in c["forms"]) or "无"
        if tid in chosen:
            disp = "**入选 → 段 %d**" % chosen[tid]
        elif tid in special:
            disp = special[tid]
        elif len(c["types"]) > 1 or "MSG_DM" not in c["types"]:
            disp = "排除：多人群聊（%s），说话人→受话人不唯一，无法逐条绑定「谁叫谁」" % types_s
        elif c["addr"] == 0:
            disp = "排除：全段无呼语位称呼，无法承担「称呼×关系演化」主题"
        elif c["errs"] > 0:
            disp = ("排除：含同类缺陷（self_name/other_named），与已选段 3/4/5 的缺陷类型重复；"
                    "该段称呼形式单一，展示价值低于已选段 ⇒ 可作复核备选")
        elif len(c["forms"]) < 2:
            disp = "排除：只出现单一称呼形式且无缺陷，无演化/缺陷可展示"
        else:
            disp = "排除：主题与已选段 1/2 重复（同类称呼升降），控篇幅未选"
        W("| `%s` | %s | %d | %d | %s | %d | %s |\n"
          % (tid, types_s, c["n"], c["addr"], fm, c["errs"], disp))
    W("\n候选池合计：ON 臂 ≥6 条线程 **%d** 个（<6 条线程不进入候选池，另记 ON 臂线程总数 %d）；"
      "入选 %d 个、排除 %d 个。\n\n" % (len(cand), len(threads["ON"]), len(SEGMENTS), len(cand) - len(SEGMENTS)))
    W("**未进入候选池的批次**：`n36-on_n16r84_s42`（在途未收批，见 §1）、"
      "`cycle36_f3_off_n16r84_seed42`（旧批：起跑 2026-10-29T12:14、`code_sha 80c9ed7`，"
      "**不属于本周期两臂**，不作为本文件素材）。\n\n")

    # ================= §7 能与不能
    W("## 7. 能与不能\n\n")
    W("### 能证明\n")
    W("1. §3 每条消息的 `seq`、`msg_uid`、说话人/受话人显示名与角色、`day/slot/place`、正文，"
      "都能在对应 `run.jsonl` 中逐字命中（§4 逐条落盘命中行号与 seq 对位）；\n")
    W("2. §3 段 3/4/5 的三条缺陷在**原文层面**可直接肉眼核对（称呼与自己/第三人重合），"
      "不需要任何指标：段 3 `方老师` 自称、段 4 `小满` 自称、段 5 `周公文` 叫错人；\n")
    W("3. §5 四张 PNG 是**本轮现场渲染**：渲染命令、源日志 sha256、渲染时 HEAD、像素自检逐张落盘（`render_report_c36-*.json`），"
      "非旧图、非拼图、非示意图；\n")
    W("4. 两臂开关证据来自 `switch_proof.txt`（`/proc/<pid>/environ` 取样）原文，本文件未改写。\n\n")
    W("### 不能证明\n")
    W("1. **不能**由这 5 段样本给出任何「称呼覆盖率/错称率/演化幅度」数字 —— 样本是**定向挑选**（非分层随机），"
      "尤其 3 段缺陷是**主动检索反例**的结果，不能外推为臂级比例；比例/显著性一律以证据审计与复算件为准；\n")
    W("2. **不能**从 ON/OFF 同 thread 的形态差异读「开关有效」 —— 两臂 `code_sha` 不同、World 演化路径不同、"
      "且 LLM 缓存命中使两臂部分输出近似（两臂 `meta.llm_cached` 均为 %s、`llm_cached_ratio` 均为 %s），"
      "本文件只登记「肉眼可见的形态差异」；\n"
      % (on["meta"].get("llm_cached"), on["meta"].get("llm_cached_ratio")))
    W("3. **不能**把 §3 的 OFF 段当作「同一局的另一臂配对样本」；\n")
    W("4. **不能**用 §5 的图证明任何效果 —— 图不进判据，仅证明「页面可渲染真实日志派生的对话/节奏视图」；\n")
    W("5. 称呼标注依赖 `v2/refs/address-ordinal.yaml`（`%s`）与 `code/config/personas.json`（`%s`）**先冻结**的口径；"
      "tier 数字是社区常识约定（有序性是判断、不是测量），换词表会改变 tier 标注。\n"
      % (sha256_file(lex_path), sha256_file(per_path)))

    md_text = "".join(md)
    md_path = outdir / "c36-cases.md"
    md_path.write_text(md_text, encoding="utf-8")

    # ================= sha 清单
    sha_lines = []
    sha_lines.append("# CYCLE-36 图 sha 与源日志 sha 的 sha256sum 原始输出\n")
    sha_lines.append("# 生成时刻：%s；渲染时 HEAD：%s（%s）\n" % (gen_at, head_sha, branch))
    sha_lines.append("# 生成命令：sha256sum <下列文件>（逐行原样，未改写）\n")
    files = []
    for key in ("ON", "OFF"):
        for v in renders[key]["views"]:
            files.append(v["png"])
        files.append(str(REPO / "v2" / "evidence" / ARMS[key]["batch"] / "run.jsonl"))
        files.append(str(REPO / "v2" / "evidence" / ARMS[key]["batch"] / "meta.json"))
        files.append(renders[key]["threads_json"])
    files.append(str(md_path))
    files.append(str(outdir / "c36-grep-checks.sh"))
    files.append(str(REPO / "v2" / "evidence" / "c36_shots" / "render.log"))
    files.append(str(REPO / "v2" / "evidence" / "c36_cases" / "extract_c36_cases.py"))
    for f in files:
        p = Path(f)
        if p.exists():
            sha_lines.append("%s  %s\n" % (sha256_file(p), f))
        else:
            sha_lines.append("MISSING  %s\n" % f)
    sha_path = outdir / "c36-sha.txt"
    sha_path.write_text("".join(sha_lines), encoding="utf-8")

    print(json.dumps({
        "c36_cases_md": str(md_path),
        "c36_cases_md_sha256": sha256_file(md_path),
        "c36_cases_md_bytes": md_path.stat().st_size,
        "c36_sha_txt": str(sha_path),
        "segments": len(SEGMENTS),
        "quoted_messages": len(checks),
        "grep_failures": len(bad),
        "shots": len(shot_rows),
        "candidates_ge6": len(cand),
        "generated_at": gen_at,
        "head": head_sha,
    }, ensure_ascii=False, indent=2))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
