#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""形态指标统一出数器（**纯只读、零跑批、零 LLM**）。

把 CYCLE-12 `Q-18` 指出的三个「只有 prose、没有落盘出数器」的形态指标
（`L-3` 含括号块率 / `addr_head` 称呼起头率 / `len_p50`，外加跨批不可互译的 `L-7`）
升为**一条命令、可复算、逐位可对**的落盘输出。

设计原则（**口径不自造**）：
1. `L-3` / `L-7` / `len_p50` **直接调用** `tools/d5/dialogue_metrics.py::compute()`，
   读它的 `L_wording.*` 字段（运行时记录该文件 sha256 与其内部 impl 来源），不另写一套。
2. `addr_head` 三口径：
   - `addr_head_pfx2`：**逐字引入** worktree `tools/d12h/shape_gate.py::is_addr_head()`
     （来源：分支 `feat/c12-d12h`，commit `371edb9`，文件 sha256 `f7740b6d…`，见 `SOURCE_PFX2`）；
   - `addr_head_strict`：`v2/evidence/d12h_verdict_amendment3.md` §C 冻结的**判据唯一口径**——
     正文以 `config/personas.json::display_name`（去 `青溪镇·` 前缀）之一**起头**；
   - `addr_head_loose`：同 §C 的**上界参照**——首句 2–6 字且以 `，/：` 收尾。
     （§C 原文只写「首句 ≤6 字且以 ，/： 收尾」；在 D12-H 全 run 上把下界 1 收紧为 2 才复现
      落盘 `464/510 = 90.98%`，1–6 会得到 `487/510 = 95.49%`。差异原因见
      `v2/evidence/form_metrics/README.md` §3，属**待裁决项**，不改既有件。）
3. 每个指标输出**六元组**：`数值 / 分母 / 判据编号 / 来源路径 / sha256 / 复算命令`；
   `L-7` 额外带**本批索引 sha256**（跨批不可互译，CYCLE-12 §3.8 / §5.4）。

用法：
    python3 tools/metrics/form_metrics.py \
        --log <run.jsonl> --code-dir code --out <out.json> \
        [--batch-id D12H] [--seed 42] [--n 16] [--rounds N] [--no-timestamp]

    --rounds N   只统计 round < N 的前缀子集（与 d5 `--prefix-rounds` 同规则）
    --no-timestamp  不写 `generated_at`，用于逐位比对落盘 JSON

退出码：0 成功 / 2 输入不可用（日志缺失、无 MSG）
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True          # 不在 code/ 下留 __pycache__（跑批期禁止动 code/）

import argparse
import hashlib
import importlib.util
import inspect
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SCHEMA_VERSION = "form-metrics/1.0"
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

DEFAULT_D5_SRC = REPO / "tools" / "d5" / "dialogue_metrics.py"
DEFAULT_PERSONAS = REPO / "code" / "config" / "personas.json"
SHAPE_GATE_SRC = REPO / ".worktrees" / "d12h-pairing" / "tools" / "d12h" / "shape_gate.py"
AMENDMENT3 = REPO / "v2" / "evidence" / "d12h_verdict_amendment3.md"

# ---------------------------------------------------------------- 来源登记（写死）
SOURCE_PFX2 = {
    "impl": "is_addr_head() 逐字引入（含 SUFFIX_CHARS 常量）",
    "file": ".worktrees/d12h-pairing/tools/d12h/shape_gate.py",
    "file_sha256": "f7740b6d4c3052b7577b5bf9d5c10c18039d2a87a1e2afb0697fb49691d70ea3",
    "branch": "feat/c12-d12h",
    "commit": "371edb99d2594406553742c66c7ce0a4f7487069",
    "commit_short": "371edb9",
    "commit_date": "2026-10-24T00:28:50+08:00",
    "note": ("master 的 `git ls-files tools/d12h` 为空（Q-19）⇒ 该文件仅存在于 worktree；"
             "本文件内嵌逐字副本，使 master 上的复算不依赖 worktree 是否还在。"),
}
SOURCE_STRICT = {
    "file": "v2/evidence/d12h_verdict_amendment3.md",
    "section": "§C 行 47",
    "text": "addr_head_strict（冻结判据口径）92.55%：以 20 个 config/personas.json::display_name 之一起头",
}
SOURCE_LOOSE = {
    "file": "v2/evidence/d12h_verdict_amendment3.md",
    "section": "§C 行 48",
    "text": "addr_head_loose 90.98%：首句 ≤6 字且以 ，/： 收尾（可能把「这块榫头，」误算称呼）",
}
SOURCE_PFX2_DEF = {
    "file": "v2/evidence/d12h_verdict_amendment3.md",
    "section": "§C 行 49",
    "text": "addr_head_pfx2 87.65%：名字在第 0 位、后缀 ≤2 字",
}

# ---------------------------------------------- 逐字引入（勿改）：shape_gate.py
# 来源见 SOURCE_PFX2；下方两处常量与函数与源文件逐字相同。
SUFFIX_CHARS = "哥姐叔婶爷奶老师先生女士先儿啊呀诶哎"


def is_addr_head(body: str, names: set) -> bool:
    b = body.strip()
    for nm in names:
        if b.startswith(nm):
            rest = b[len(nm):]
            # 允许 0–2 个称谓字再接标点：「老石，」「铁头哥，」「老周啊，」
            for k in range(0, 3):
                if rest[k:k + 1] in ("，", ",", "：", ":"):
                    return True
                if k >= len(rest) or (k > 0 and rest[k - 1] not in SUFFIX_CHARS):
                    break
    return False
# ---------------------------------------------- 逐字引入结束


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_module(path: Path, name: str):
    if not path.exists():
        raise SystemExit(f"[form_metrics] 找不到依赖实现：{path}（口径不自造，拒绝降级）")
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def vendor_check() -> str:
    """核对内嵌副本与 worktree 源函数是否逐字一致；源不在则记 source_absent。"""
    if not SHAPE_GATE_SRC.exists():
        return "source_absent"
    try:
        mod = load_module(SHAPE_GATE_SRC, "_fm_shape_gate_check")
        a = inspect.getsource(is_addr_head)
        b = inspect.getsource(mod.is_addr_head)
        norm = lambda s: re.sub(r"\s+", " ", s).strip()  # noqa: E731
        ok_fn = norm(a) == norm(b)
        ok_sfx = SUFFIX_CHARS == getattr(mod, "SUFFIX_CHARS", None)
        return "identical" if (ok_fn and ok_sfx) else "mismatch"
    except Exception as e:  # noqa: BLE001
        return f"check_failed: {type(e).__name__}: {e}"


# loose 的「首句 ≤6 字」**下界**常量（Leader 2026-10-24 裁决 FM-1：冻结为 2，不再改动）。
# 冻结理由（写进代码，防止后人再改）：loose 仅作**上界参照**，不用于任何判定；
# 取 2 是为了与 CYCLE-12 prose 值 `464/510 = 90.98%` 可比（取 1 会得 487/510 = 95.49%，与既有 prose 不可比）。
# ⇒ 该常量属于「口径冻结」，不是「为凑数调参」：它不影响判据口径 addr_head_strict 的任何数值。
LOOSE_MIN_CHARS = 2
LOOSE_MAX_CHARS = 6
LOOSE_RX = re.compile(r"^[^，,：:]{%d,%d}[，,：:]" % (LOOSE_MIN_CHARS, LOOSE_MAX_CHARS))


def loose_head(body: str) -> bool:
    """addr_head_loose：首句 2–6 字且以 ，/： 收尾（上界参照；口径来源见 SOURCE_LOOSE）。"""
    return bool(LOOSE_RX.match(body.strip()))


# `addr_head_pfx2_plus`：pfx2 的**标点集扩展变体**（Leader 裁决 FM-5：只作参照，不作判据）。
# 与 pfx2 的唯一差别：标点集在 `，,：:` 之外补上 `、`（并列称呼，如「老周、老石，」）与
# `——`（破折号，如「五味——你瞧」）。名字匹配算法与 pfx2 完全一致（见 is_addr_head_plus）。
PUNCT_PFX2 = ("，", ",", "：", ":")
PUNCT_PFX2_PLUS = ("，", ",", "：", ":", "、", "——")


def is_addr_head_plus(body: str, names: set) -> bool:
    """与 `is_addr_head()` 同算法，仅把标点集换成 `PUNCT_PFX2_PLUS`（逐行对照可核）。"""
    b = body.strip()
    for nm in names:
        if b.startswith(nm):
            rest = b[len(nm):]
            for k in range(0, 3):
                tail = rest[k:]
                if any(tail.startswith(p) for p in PUNCT_PFX2_PLUS):
                    return True
                if k >= len(rest) or (k > 0 and rest[k - 1] not in SUFFIX_CHARS):
                    break
    return False


# `addr_head_alias`：**只读指示量**（Leader 裁决 FM-4：不得进入任何判定）。
# 口径（写死）：首段由标点 `，,：:` 收尾、长度 ≤6，且首段**以结构化的别名/敬称形式**出现，
# 同时该首段**不以任何 display_name 起头**（否则已被 strict 计入，不重复计）。
# 结构形式只有两类（不查任何人名表，纯结构规则，故可被第三方原样复算）：
#   (a) `老|小|阿` + 1–2 字（老陈 / 小李 / 阿凯 / 老陈啊）
#   (b) 1–3 字 + 敬称/亲属后缀（周先生 / 周文书 / 方老师 / 周公 / 桂婶）
ALIAS_RX = re.compile(
    r"^(?:(?:老|小|阿)[\u4e00-\u9fa5]{1,2}"
    r"|[\u4e00-\u9fa5]{1,3}(?:先生|女士|老师|大夫|师傅|文书|掌柜|公|伯|叔|婶|哥|姐|爷|奶))[，,：:]"
)


def alias_head(body: str, dn: Set[str]) -> bool:
    b = body.strip()
    if any(b.startswith(x) for x in dn):
        return False          # 已归 strict，不重复计
    return bool(ALIAS_RX.match(b))



def load_world_names(seed: int, n: int, code_dir: Path) -> Tuple[Set[str], Optional[str]]:
    """pfx2 用显示名：取自跑批树 build_world(seed, n) 的 _peer_names（与 shape_gate 同源）。

    只做世界构造，**不跑批、不调用 LLM**；`sys.dont_write_bytecode` 已关，不会写 code/。
    """
    try:
        sys.path.insert(0, str(code_dir))
        from orchestration.integration import build_world  # noqa: E402

        w = build_world(seed=seed, n=n)
        names: Set[str] = set()
        for a in w["agents"]:
            names |= set((getattr(a, "_peer_names", {}) or {}).values())
        names.discard("")
        return names, None
    except Exception as e:  # noqa: BLE001
        return set(), f"{type(e).__name__}: {e}"


def batch_index_sha(bodies: List[str], d5) -> Tuple[str, int, int]:
    """本批 8-gram 索引 sha256（`L-7` 的参照系指纹，用于声明跨批不可互译）。

    构造规则**与 d5 `compute()` 内 L-7 完全一致**：
      norm_i = d5.normalize_body(body_i)；shingles_i = {norm_i[i:i+8]}；
      index: gram → 出现该 gram 的 msg 下标列表。
    序列化（写死，换行分隔、key 与下标均升序）：
      每条 `<gram>\t<idx1>,<idx2>,…\n`，按 gram 字节序升序拼接后取 sha256。
    """
    shingles = []
    for b in bodies:
        t = d5.normalize_body(b)
        shingles.append({t[i:i + 8] for i in range(max(0, len(t) - 7))})
    index: Dict[str, List[int]] = defaultdict(list)
    for i, sh in enumerate(shingles):
        for g in sh:
            index[g].append(i)
    lines = []
    for g in sorted(index):
        lines.append(g + "\t" + ",".join(str(i) for i in sorted(index[g])))
    blob = "\n".join(lines) + "\n"
    dup = set()
    for g, idxs in index.items():
        if len(idxs) > 1:
            dup.update(idxs)
    return sha256_text(blob), len(index), len(dup)


def metric(value, num, den, criterion_id, criterion_basis, source_path, source_sha,
           log_path, log_sha, cmd, den_def, extra=None) -> Dict[str, Any]:
    rec = {
        "value": value,
        "numerator": num,
        "denominator": den,
        "denominator_definition": den_def,
        "criterion_id": criterion_id,
        "criterion_basis": criterion_basis,
        "source_path": source_path,
        "source_sha256": source_sha,
        "log_path": log_path,
        "log_sha256": log_sha,
        "recompute_cmd": cmd,
        # 六元组（顺序写死：数值 / 分母 / 判据编号 / 来源路径 / sha256 / 复算命令）
        "tuple": [value, den, criterion_id, source_path, source_sha, cmd],
    }
    if extra:
        rec.update(extra)
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="形态指标统一出数器（零跑批、零 LLM、只读）")
    ap.add_argument("--log", required=True, help="run.jsonl 路径")
    ap.add_argument("--code-dir", default="code", help="跑批树 code/（pfx2 取显示名用）")
    ap.add_argument("--out", required=True, help="输出 JSON 路径")
    ap.add_argument("--batch-id", default=None, help="批次标签（写进 JSON，便于多批并列）")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--rounds", type=int, default=None, help="只统计 round < N 的前缀子集")
    ap.add_argument("--d5-src", default=str(DEFAULT_D5_SRC))
    ap.add_argument("--personas", default=str(DEFAULT_PERSONAS))
    ap.add_argument("--no-timestamp", action="store_true", help="不写 generated_at（逐位比对用）")
    ap.add_argument("--triage-out", default=None,
                    help="可选：逐条分类 + 三口径差集（用于正面解释 addr_head 口径冲突）")
    a = ap.parse_args(argv)

    log_path = Path(a.log)
    if not log_path.exists():
        print(f"[FAIL] 日志不存在: {log_path}", file=sys.stderr)
        return 2
    code_dir = Path(a.code_dir)
    if not code_dir.is_absolute():
        code_dir = (Path.cwd() / code_dir)

    d5 = load_module(Path(a.d5_src), "_fm_d5")
    d5_sha = sha256_file(a.d5_src)
    log_sha = sha256_file(log_path)
    personas_sha = sha256_file(a.personas) if Path(a.personas).exists() else None

    recs, parse = d5.read_run(str(log_path))
    n_records = len(recs)
    rounds_note = None
    if a.rounds is not None:
        before = len(recs)
        recs = [r for r in recs if (r.get("round") is None) or int(r.get("round")) < a.rounds]
        rounds_note = {"prefix_rounds": a.rounds, "records_before": before, "records_after": len(recs)}
    msgs = d5.extract_messages(recs)
    if not msgs:
        print("[FAIL] 日志中没有 MSG_DM/MSG_PUBLIC/MSG_GROUP 消息事件", file=sys.stderr)
        return 2

    # ---- 口径实现全部来自 d5 本体（不自造）
    names_p, pinfo = d5.load_personas(a.personas)
    res = d5.compute(msgs, [], [], names_p, {})
    lw = res["L_wording"]
    n_msg = res["meta"]["n_messages"]

    bodies = [m["body"].strip() for m in msgs if (m["body"] or "").strip()]
    n_bodies = len(bodies)

    # ---- addr_head 三口径
    dn_strict = {v for v in names_p.values() if v}
    n_strict = sum(1 for b in bodies if any(b.startswith(x) for x in dn_strict))
    n_loose = sum(1 for b in bodies if loose_head(b))
    world_names, world_err = load_world_names(a.seed, a.n, code_dir)
    n_pfx2 = sum(1 for b in bodies if world_names and is_addr_head(b, world_names))
    n_plus = sum(1 for b in bodies if world_names and is_addr_head_plus(b, world_names))
    n_alias = sum(1 for b in bodies if alias_head(b, dn_strict))

    # ---- L-7 本批索引 sha
    idx_sha, idx_grams, idx_dup = batch_index_sha(bodies, d5)
    l7_num = round((lw["L-7_dup_ngram8_rate"] or 0.0) * n_msg)
    l7_consistent = (l7_num == idx_dup)

    py = "python3 tools/metrics/form_metrics.py"
    base_cmd = f"{py} --log {a.log} --code-dir {a.code_dir} --out {a.out}"
    if a.batch_id:
        base_cmd += f" --batch-id {a.batch_id}"
    if a.rounds is not None:
        base_cmd += f" --rounds {a.rounds}"

    M: Dict[str, Any] = {}
    M["L-3_paren_block_any"] = metric(
        lw["L-3_paren_block_any"], round((lw["L-3_paren_block_any"] or 0.0) * n_msg), n_msg,
        "L-3（D5 指标 L-3_paren_block_any）",
        "分子 = body 命中任一括号块（PAREN_ANY_RE）的消息数；分母 = 全部 MSG。"
        "D12-H 判据闸线 L-3 ≥ 55%（预登记 §4 反事实：低于即「无效（靠砍旁白换重复）」）",
        str(a.d5_src), d5_sha, str(log_path), log_sha, base_cmd,
        "分母 = 全部 MSG（d5 meta.n_messages）",
        {"criterion_gate": "≥0.55（D12-H 预登记 §4 反事实）",
         "impl_note": "数值直接读 tools/d5/dialogue_metrics.py::compute() 的 L_wording.L-3_paren_block_any"},
    )
    M["L-1_len_p50"] = metric(
        lw["L-1_len"]["all"]["p50"], None, n_msg,
        "L-1（D5 指标 L-1_len.all.p50）",
        "全部 MSG 正文字数（含括号块）的 p50；d5 线性插值分位。CYCLE-12 §2.3 参照 T5 = 53（该 53 实为 excl_paren 口径，见 len_p50_excl）",
        str(a.d5_src), d5_sha, str(log_path), log_sha, base_cmd,
        "分母 = 全部 MSG（p50 的分位分母）",
        {"impl_note": "直接读 d5 L_wording.L-1_len.all.p50"},
    )
    M["L-1_len_p50_excl_paren"] = metric(
        lw["L-1_len"]["excl_paren"]["p50"], None, n_msg,
        "L-1（D5 指标 L-1_len.excl_paren.p50）",
        "去掉括号块后正文字数的 p50；CYCLE-12 §2.3 里与 D12-H 56.0 对比的 T5「53」即此口径",
        str(a.d5_src), d5_sha, str(log_path), log_sha, base_cmd,
        "分母 = 全部 MSG（p50 的分位分母）",
        {"impl_note": "直接读 d5 L_wording.L-1_len.excl_paren.p50"},
    )
    M["addr_head_strict"] = metric(
        (n_strict / n_bodies) if n_bodies else None, n_strict, n_bodies,
        "addr_head_strict（**判据唯一口径**，D12H-amendment3 §C）",
        "正文以 config/personas.json 的 display_name（去「青溪镇·」前缀）之一起头；"
        "来源 " + SOURCE_STRICT["file"] + " " + SOURCE_STRICT["section"],
        str(a.personas), personas_sha, str(log_path), log_sha, base_cmd,
        "分母 = body 非空的 MSG 条数",
        {"source_registry": SOURCE_STRICT, "n_display_names": len(dn_strict),
         "role": "criterion_primary",
         "criterion_role": "判据口径（D12-I 形态闸 F2 应改用此口径）"},
    )
    M["addr_head_loose"] = metric(
        (n_loose / n_bodies) if n_bodies else None, n_loose, n_bodies,
        "addr_head_loose（**上界参照**，D12H-amendment3 §C）",
        "首句 2–6 字且以 ，/： 收尾（见文件头 口径说明与 README §3）；"
        "来源 " + SOURCE_LOOSE["file"] + " " + SOURCE_LOOSE["section"],
        str(a.personas), personas_sha, str(log_path), log_sha, base_cmd,
        "分母 = body 非空的 MSG 条数",
        {"source_registry": SOURCE_LOOSE, "regex": LOOSE_RX.pattern,
         "frozen_constants": {"LOOSE_MIN_CHARS": LOOSE_MIN_CHARS,
                              "LOOSE_MAX_CHARS": LOOSE_MAX_CHARS},
         "role": "reference_only", "criterion_role": "上界参照，不作判据",
         "note": ("下界已由 Leader 2026-10-24 裁决 FM-1 冻结为 2（取 2 才与 CYCLE-12 prose "
                  "464/510=90.98% 可比；取 1 为 487/510=95.49%）。该常量不得再改；"
                  "loose 不进入任何判定，冻结只为消灭口径漂移")},
    )
    M["addr_head_pfx2"] = metric(
        (n_pfx2 / n_bodies) if (n_bodies and world_names) else None, n_pfx2 if world_names else None,
        n_bodies,
        "addr_head_pfx2（**下界参照**，D12H-amendment3 §C / dialogue-core-dev 87.65%）",
        "名字在第 0 位、后缀 ≤2 字后接 ，/：：逐字复用 shape_gate.py::is_addr_head()；"
        "来源 " + SOURCE_PFX2_DEF["file"] + " " + SOURCE_PFX2_DEF["section"],
        SOURCE_PFX2["file"], SOURCE_PFX2["file_sha256"], str(log_path), log_sha, base_cmd,
        "分母 = body 非空的 MSG 条数",
        {"source_registry": SOURCE_PFX2, "source_registry_def": SOURCE_PFX2_DEF,
         "n_world_names": len(world_names), "world_names_error": world_err,
         "vendor_check": vendor_check(),
         "role": "reference_only", "criterion_role": "下界参照，不作判据"},
    )
    M["addr_head_pfx2_plus"] = metric(
        (n_plus / n_bodies) if (n_bodies and world_names) else None, n_plus if world_names else None,
        n_bodies,
        "addr_head_pfx2_plus（**参照量**，Leader 裁决 FM-5）",
        "pfx2 的标点集扩展变体：名字在第 0 位、后缀 ≤2 字，标点集 = `，,：:` ∪ `、` ∪ `——`。"
        "**只作参照，不作判据**；与 pfx2 的差集含义 = 「真称呼被判漏的那部分」（并列称呼 `、` + 破折号 `——`）",
        SOURCE_PFX2["file"], SOURCE_PFX2["file_sha256"], str(log_path), log_sha, base_cmd,
        "分母 = body 非空的 MSG 条数",
        {"source_registry": SOURCE_PFX2,
         "punct_set": list(PUNCT_PFX2_PLUS), "punct_set_base_pfx2": list(PUNCT_PFX2),
         "n_world_names": len(world_names),
         "role": "reference_only", "criterion_role": "参照量，不作判据",
         "note": "shape_gate.py 本体不动（在 worktree、未入 master）；其标点集缺「、」「——」登记为下一周期修复项"},
    )
    M["addr_head_alias"] = metric(
        (n_alias / n_bodies) if n_bodies else None, n_alias, n_bodies,
        "addr_head_alias（**只读指示量**，Leader 裁决 FM-4）",
        "首段以结构化别名/敬称形式出现且**不以任何 display_name 起头**（否则已归 strict，不重复计）："
        "`(老|小|阿)+1–2字` 或 `1–3字+(先生|女士|老师|大夫|师傅|文书|掌柜)`，其后接 `，,：:`",
        str(a.personas), personas_sha, str(log_path), log_sha, base_cmd,
        "分母 = body 非空的 MSG 条数",
        {"regex": ALIAS_RX.pattern,
         "role": "reference_only", "criterion_role": "只读指示量，**不得进入任何判定**",
         "note": ("口径必须由冻结的 personas.json 决定，扩表会使本批与历史批不可比 ⇒ 别名不纳入判据口径（FM-4 裁决）；"
                  "该指示量本身是「生活气息」的正面线索，报告里只能以「描述性读数」出现")},
    )

    M["L-7_dup_ngram8_rate"] = metric(
        lw["L-7_dup_ngram8_rate"], l7_num, n_msg,
        "L-7（D5 指标 L-7_dup_ngram8_rate）",
        "分子 = 与任一其他 MSG 共享 ≥1 个 normalize_body 后 8-gram 的消息数；分母 = 全部 MSG。"
        "**跨批不可互译**（CYCLE-12 §3.8 / §5.4）：各行按本批自身索引计算，跨批差值只能读作「各批内部去重程度」",
        str(a.d5_src), d5_sha, str(log_path), log_sha, base_cmd,
        "分母 = 全部 MSG（d5 meta.n_messages）",
        {"batch_index_sha256": idx_sha, "batch_index_grams": idx_grams,
         "batch_index_dup_msgs": idx_dup,
         "batch_index_rule": "norm_i=d5.normalize_body(body_i); shingles_i={norm_i[k:k+8]}; "
                             "index: gram→[msg 下标] 升序；序列化 `<gram>\\t<idx,...>\\n` 按 gram 字节序升序拼接后 sha256",
         "index_note": ("本批索引 sha256 是 L-7 的参照系指纹：**不同批的 index sha 必然不同**，"
                        "因此两个 L-7 数值之差不得跨批解释为效果量"),
         "consistency_with_d5": l7_consistent},
    )

    out: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "batch_id": a.batch_id,
        "inputs": {
            "log": str(log_path),
            "log_sha256": log_sha,
            "log_records": n_records,
            "log_parse": parse,
            "rounds_filter": rounds_note,
            "n_msgs": n_msg,
            "n_bodies_nonempty": n_bodies,
            "d5_impl": {"path": str(a.d5_src), "sha256": d5_sha},
            "personas": {"path": str(a.personas), "sha256": personas_sha},
            "code_dir": str(code_dir),
            "seed": a.seed, "n": a.n,
            "addr_head_sources": {
                "strict": SOURCE_STRICT, "loose": SOURCE_LOOSE,
                "pfx2_impl": SOURCE_PFX2, "pfx2_def": SOURCE_PFX2_DEF,
                "amendment3_file": AMENDMENT3.name,
                "amendment3_sha256": sha256_file(AMENDMENT3) if AMENDMENT3.exists() else None,
            },
            "tool": {"path": str(Path(__file__).resolve()),
                     "sha256": sha256_file(Path(__file__).resolve())},
        },
        "tuple_layout": ["value", "denominator", "criterion_id",
                         "source_path", "source_sha256", "recompute_cmd"],
        "metrics": M,
        "caveats": [
            "本工具零 LLM、零跑批：只读既有 run.jsonl 与 config，不产生新跑批数据。",
            "L-3 / L-7 / len_p50 的数值直接读 tools/d5/dialogue_metrics.py::compute()，未在本文件另立口径。",
            "addr_head 三口径只能有一个作判据：按 D12H-amendment3 §C 冻结为 addr_head_strict。",
            "addr_head_pfx2_plus / addr_head_alias 标 role=reference_only：只作参照，不得进入任何判定（Leader 裁决 FM-5 / FM-4）。",
            "L-7 带本批索引 sha256：跨批数值不可互译，不得据此写「更差/更好 N pp」。",
            "addr_head_loose 的「≤6 字」下界（1 还是 2）在既有件里未写死，本文件取 2 以复现落盘 464/510；"
            "取 1 得 487/510。该点列为待裁决项（README §3）。",
        ],
    }
    if not a.no_timestamp:
        out["generated_at"] = __import__("datetime").datetime.now().astimezone().isoformat(
            timespec="seconds")

    if a.triage_out:
        zh = {}
        for m in msgs:
            b = (m["body"] or "").strip()
            if not b:
                continue
            flags = {
                "strict": bool(any(b.startswith(x) for x in dn_strict)),
                "loose": loose_head(b),
                "pfx2": bool(world_names and is_addr_head(b, world_names)),
                "pfx2_plus": bool(world_names and is_addr_head_plus(b, world_names)),
                "alias": alias_head(b, dn_strict),
            }
            zh[str(m.get("seq"))] = {
                "seq": m.get("seq"), "round": m.get("round"), "from": m.get("from"),
                "channel": m.get("channel"), "body": m["body"][:160], "hit": flags,
            }

        def diff(a_key, b_key):
            return [{"seq": v["seq"], "round": v["round"], "body": v["body"]}
                    for v in zh.values() if v["hit"][a_key] and not v["hit"][b_key]]

        triage = {
            "schema_version": "form-metrics-triage/1.0",
            "batch_id": a.batch_id,
            "log": str(log_path), "log_sha256": log_sha,
            "n_bodies": n_bodies,
            "counts": {
                "strict": {"k": n_strict, "n": n_bodies},
                "loose": {"k": n_loose, "n": n_bodies},
                "pfx2": {"k": n_pfx2, "n": n_bodies},
                # 以下为**集合差**（不是两个 k 的算术差），命名写死避免误读
                "set_strict_only": sum(1 for v in zh.values() if v["hit"]["strict"] and not v["hit"]["loose"]),
                "set_loose_only": sum(1 for v in zh.values() if v["hit"]["loose"] and not v["hit"]["strict"]),
                "set_both_strict_and_loose": sum(1 for v in zh.values() if v["hit"]["strict"] and v["hit"]["loose"]),
                "set_neither": sum(1 for v in zh.values() if not v["hit"]["strict"] and not v["hit"]["loose"]),
                "set_loose_not_pfx2": n_loose - sum(
                    1 for v in zh.values() if v["hit"]["loose"] and v["hit"]["pfx2"]),
                "set_strict_not_pfx2": n_strict - sum(
                    1 for v in zh.values() if v["hit"]["strict"] and v["hit"]["pfx2"]),
                "k_diff_strict_minus_loose": n_strict - n_loose,
                "pfx2_plus": {"k": n_plus, "n": n_bodies, "role": "reference_only"},
                "alias": {"k": n_alias, "n": n_bodies, "role": "reference_only"},
                "set_pfx2_plus_not_pfx2": n_plus - sum(
                    1 for v in zh.values() if v["hit"]["pfx2_plus"] and v["hit"]["pfx2"]),
            },
            "set_relations": {
                "pfx2_subset_of_strict": all(
                    (not v["hit"]["pfx2"]) or v["hit"]["strict"] for v in zh.values()),
                "both_strict_and_loose_false": sum(
                    1 for v in zh.values() if not v["hit"]["strict"] and not v["hit"]["loose"]),
            },
            "diffs": {
                "loose_but_not_pfx2": diff("loose", "pfx2"),
                "strict_but_not_pfx2": diff("strict", "pfx2"),
                "pfx2_but_not_loose": diff("pfx2", "loose"),
                "pfx2_plus_but_not_pfx2": diff("pfx2_plus", "pfx2"),
                "alias_but_not_strict": diff("alias", "strict"),
            },
            "per_msg": [zh[k] for k in sorted(zh, key=lambda s: (int(s) if s.lstrip("-").isdigit() else 0))],
        }
        tp = Path(a.triage_out)
        tp.parent.mkdir(parents=True, exist_ok=True)
        tp.write_text(json.dumps(triage, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                      encoding="utf-8")
        print(json.dumps({"triage_out": str(tp), "triage_sha256": sha256_file(tp),
                          "counts": triage["counts"]}, ensure_ascii=False), file=sys.stderr)

    txt = json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    out_path = Path(a.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(txt, encoding="utf-8")

    print(json.dumps({
        "batch_id": a.batch_id,
        "n_msgs": n_msg, "n_bodies": n_bodies,
        "L-3": lw["L-3_paren_block_any"],
        "addr_head_strict": M["addr_head_strict"]["value"],
        "addr_head_loose": M["addr_head_loose"]["value"],
        "addr_head_pfx2": M["addr_head_pfx2"]["value"],
        "addr_head_pfx2_plus": M["addr_head_pfx2_plus"]["value"],
        "addr_head_alias": M["addr_head_alias"]["value"],
        "len_p50": lw["L-1_len"]["all"]["p50"],
        "len_p50_excl": lw["L-1_len"]["excl_paren"]["p50"],
        "L-7": lw["L-7_dup_ngram8_rate"],
        "L-7_index_sha256": idx_sha,
        "out": str(out_path),
        "out_sha256": sha256_file(out_path),
    }, ensure_ascii=False, indent=2))
    if not l7_consistent:
        print(f"[WARN] L-7 本地索引 dup 数（{idx_dup}）与 d5 读数（{l7_num}）不一致——如实上报，"
              f"不得调参", file=sys.stderr)
    if world_err:
        print(f"[WARN] pfx2 取显示名失败：{world_err}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
