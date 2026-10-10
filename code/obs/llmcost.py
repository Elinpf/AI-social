"""LLM 成本报告（只读，观测层）。

两个来源（互补）：
1. `llm_cost_from_records(records)` —— 读引擎日志里的 `LLM_CALL` 事件
   （08 §1.2-G：`purpose/tokens_in/tokens_out/model/tier/cached/degraded`）。
   ⚠️ 当前 freeze 层的 `LLM_CALL` 写在其**自有 EventLog**、尚未经 IF-2c 回灌内核账本
   （kernel-dev 已登记桥接），故引擎日志里可能为空；桥接落地后本函数即直接可用。
2. `freeze_cache_cost(cache_dir)` —— 读 freeze 内容寻址缓存
   `<cache_dir>/responses/*.json`（键：tokens_in/tokens_out/provider/model/tier/thinking/degraded），
   用于在桥接前从**隔离缓存**取得一次 run 的真实 token 成本。

只读、纯汇总、确定性（键排序）。
"""

from __future__ import annotations

import json
from pathlib import Path


def llm_cost_from_records(records) -> dict:
    """按 purpose 汇总引擎日志中的 LLM_CALL；并统计 LLM_JUDGMENT。"""
    by_purpose: dict[str, dict] = {}
    by_provider: dict[str, int] = {}
    total = {"calls": 0, "tokens_in": 0, "tokens_out": 0,
             "cached": 0, "degraded": 0, "thinking": 0}
    judgments: dict[str, int] = {}
    for r in records:
        t = r["type"]
        if t == "LLM_CALL":
            p = r.get("payload") or {}
            purpose = str(p.get("purpose", "unknown"))
            prov = str(p.get("provider", "unknown"))
            b = by_purpose.setdefault(purpose, {"calls": 0, "tokens_in": 0, "tokens_out": 0,
                                                "cached": 0, "degraded": 0, "thinking": 0})
            ti, to = int(p.get("tokens_in", 0)), int(p.get("tokens_out", 0))
            b["calls"] += 1
            b["tokens_in"] += ti
            b["tokens_out"] += to
            b["cached"] += int(bool(p.get("cached")))
            b["degraded"] += int(bool(p.get("degraded")))
            b["thinking"] += int(bool(p.get("thinking")))
            total["calls"] += 1
            total["tokens_in"] += ti
            total["tokens_out"] += to
            total["cached"] += int(bool(p.get("cached")))
            total["degraded"] += int(bool(p.get("degraded")))
            total["thinking"] += int(bool(p.get("thinking")))
            by_provider[prov] = by_provider.get(prov, 0) + 1
        elif t == "LLM_JUDGMENT":
            dim = str((r.get("payload") or {}).get("dimension", "unknown"))
            judgments[dim] = judgments.get(dim, 0) + 1
    total["tokens_total"] = total["tokens_in"] + total["tokens_out"]
    return {
        "source": "engine_log(LLM_CALL)",
        "total": total,
        "by_purpose": {k: by_purpose[k] for k in sorted(by_purpose)},
        "by_provider": {k: by_provider[k] for k in sorted(by_provider)},
        "llm_judgment_by_dimension": {k: judgments[k] for k in sorted(judgments)},
    }


def check_provider(cost: dict, expected: str | None = None) -> dict:
    """**缓存污染防护**：断言一次运行/缓存**全部由预期 provider 服务**。

    背景（事故教训）：共享 FREEZE 缓存把 `mock` 与 `openai_compat` 响应混存 →
    真 LLM 段可能被 mock 命中而不自知，静默产出错误结论。
    本函数要求：若给 `expected`，则 `by_provider` 中**只能有 expected**且计数 > 0；
    否则至少**报告** by_provider 分布（供显式核对）。
    """
    by = cost.get("by_provider", {})
    problems = []
    if not by:
        problems.append("by_provider 为空：无法确认由哪个 provider 服务（真实 LLM 计划必须校验）")
    if expected:
        others = [p for p in by if p != expected]
        if others:
            problems.append(f"出现非预期 provider：{sorted(others)}（预期仅 {expected}）")
        if by.get(expected, 0) <= 0:
            problems.append(f"预期 provider {expected} 计数为 0")
    return {
        "ok": not problems,
        "expected": expected,
        "by_provider": by,
        "problems": problems,
        "policy": "计划用真 LLM 时必须显式校验 provider 计数 > 0 且无 mock 混入。",
    }


def freeze_cache_cost(cache_dir: str | Path) -> dict:
    """从 freeze 内容寻址缓存汇总一次 run 的真实 token 成本（只读目录）。"""
    responses = Path(cache_dir) / "responses"
    files = sorted(responses.glob("*.json")) if responses.exists() else []
    total = {"responses_cached": 0, "tokens_in": 0, "tokens_out": 0,
             "thinking": 0, "degraded": 0}
    by_provider: dict[str, dict] = {}
    by_tier: dict[str, int] = {}
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        ti, to = int(d.get("tokens_in", 0)), int(d.get("tokens_out", 0))
        total["responses_cached"] += 1
        total["tokens_in"] += ti
        total["tokens_out"] += to
        total["thinking"] += int(bool(d.get("thinking")))
        total["degraded"] += int(bool(d.get("degraded")))
        prov = str(d.get("provider", "unknown"))
        bp = by_provider.setdefault(prov, {"responses_cached": 0, "tokens_in": 0, "tokens_out": 0})
        bp["responses_cached"] += 1
        bp["tokens_in"] += ti
        bp["tokens_out"] += to
        bp["tokens_total"] = bp["tokens_in"] + bp["tokens_out"]
        tier = str(d.get("tier", "?"))
        by_tier[tier] = by_tier.get(tier, 0) + 1
    total["tokens_total"] = total["tokens_in"] + total["tokens_out"]
    return {
        "source": f"freeze_cache:{cache_dir}",
        "total": total,
        "by_provider": {k: by_provider[k] for k in sorted(by_provider)},
        "by_tier": {k: by_tier[k] for k in sorted(by_tier)},
    }


__all__ = ["llm_cost_from_records", "freeze_cache_cost", "check_provider"]
