"""R6-T2 · **消融对照臂（synthetic）**：把「摩擦/和解」措辞**直接注入 body**。

⚠️ 这不是生产路径，**生产代码不 import 本模块**。它只服务于一个目的：
证明「管道通、词表对注入敏感、结构字段可读」——即离线验证
`tools/d5/dialogue_metrics.py` 的 F-4 确实能从 body 里读到张力与修复，
而不必真的跑 LLM 批。

口径纪律（Leader 裁决，R6-T2）：
  * 本臂产出的一切读数都是 **`synthetic`**：只进附录，**不进结论表**，
    不得与主臂（`life/dialogue_repair.py`，只给处境、不下笔）混比；
  * 它衡量的是「注入覆盖率」，不是「居民会不会和解」。

已知测量伪影（要如实写进附录）：修复句若与 LLM 正文的正向词共处一条消息，
该消息本身可能被 F-4 判为一次「极性翻转」张力事件且身后无修复词 ⇒ 把率往下拉。
"""

from __future__ import annotations

import hashlib

#: 摩擦短句（每条含 ≥2 个 tools/d5/emotion_lexicon.txt 的 -1 词，保证极性为负）
FRICTION_PHRASES = (
    "……算了，你什么意思？我有点生气。",
    "你这么说我挺失望，也有点委屈。",
    "别这样，你什么意思，我真有点烦。",
    "算了，我不跟你吵，可我心里难受。",
    "我有点后悔跟你说这些，心里挺苦的。",
    "你这人真让人烦，算了。",
)

#: 和解短句（含 tools/d5/repair_lexicon.txt 的词，且**不含任何情绪极性词** ⇒ 极性 0）
REPAIR_PHRASES = (
    "对不起，我不是那个意思，别往心里去。",
    "抱歉，是我不好，别往心里去。",
    "对不起，我理解错了，别往心里去。",
    "消消气，是我不好，没事了。",
    "抱歉抱歉，误会一场，不要紧。",
)


def _pick(material: str) -> int:
    h = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def append_friction(body: str, material: str) -> tuple[str, str]:
    """返回 (新 body, phrase_id)。确定性（同 material 同结果）。"""
    i = _pick(material) % len(FRICTION_PHRASES)
    return f"{body.rstrip()} {FRICTION_PHRASES[i]}".strip(), f"FR{i}"


def append_repair(body: str, material: str) -> tuple[str, str]:
    """返回 (新 body, phrase_id)。确定性。"""
    i = _pick(material) % len(REPAIR_PHRASES)
    return f"{body.rstrip()} {REPAIR_PHRASES[i]}".strip(), f"RP{i}"


def inject_scripted(msgs: list) -> list:
    """离线消融用：把「摩擦→(下一条同线程)和解」按脚本注入一组消息体。

    入参 `msgs`：`[{"thread_id":..., "body":...}, ...]`（同线程按顺序）。
    规则（与 F-4 口径对齐）：线程内**第 1 条不注入**（F-4 的张力检测从第 2 条起算），
    第 2 条注入摩擦、第 3 条注入和解；返回新列表（不就地改入参）。
    """
    out = []
    by_thread: dict = {}
    for m in msgs:
        tid = m.get("thread_id")
        n = by_thread.get(tid, 0)
        body = m.get("body", "")
        pid = None
        if n == 1 and tid:
            body, pid = append_friction(body, f"{tid}:{n}")
            kind = "friction"
        elif n == 2 and tid:
            body, pid = append_repair(body, f"{tid}:{n}")
            kind = "repair"
        else:
            kind = None
        by_thread[tid] = n + 1
        row = dict(m)
        row["body"] = body
        if kind:
            row["ablation"] = {"arm": "synthetic", "role": kind, "phrase_id": pid}
        out.append(row)
    return out
