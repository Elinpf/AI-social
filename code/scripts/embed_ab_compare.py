"""T48 A/B 模板：同一记忆集在「Mock 随机向量 vs 确定性词法相关度 vs 真嵌入」下的检索命中对比。

- **lexical**：`frozen://lexical-relevance-v1`（token 级 feature hashing，零依赖可复现）。
- **mock**：`MockProvider` 纯随机向量（**现状**：`relevance` == 噪声）。
- **real（P1 占位）**：若配置了真嵌入端点（`FREEZE_EMBED_BASE_URL/FREEZE_EMBED_MODEL`），
  则接入对比；否则标 `not_available`。

产出：`v1.2/embedding-ab-evidence.json`（不含密钥）。

用法：
    python3 scripts/embed_ab_compare.py --out ../v1.2/embedding-ab-evidence.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from freeze.providers import LexicalProvider, MockProvider, OpenAICompatProvider  # noqa: E402
from freeze.relevance import RelevanceRanker, lexical_overlap  # noqa: E402

MEMORIES = [
    "老李上周托我修一把锄头，约定这周去集市取。",
    "今天是晴朗的早晨，广场上有人在晒谷物。",
    "面包房的牛角包很受欢迎，清晨就卖光了。",
    "我向银行申请了一笔小额贷款用来进货。",
    "张三和李四在集市上因为价格争吵起来。",
    "我在图书馆读了一本关于木工手艺的书。",
    "周末礼堂有一场音乐会，镇上很多人参加。",
    "我把修好的锄头还给老李，他很高兴。",
]
QUERY = "关于锄头的约定"


def rank_with(name, embed_fn, top_k=4):
    r = RelevanceRanker(embed_fn).rank(QUERY, MEMORIES, top_k=top_k)
    return {
        "method": name,
        "top": [{"rank": i + 1, "index": x.index, "score": round(x.score, 4),
                 "lexical_overlap": round(lexical_overlap(QUERY, x.text), 4),
                 "text": x.text} for i, x in enumerate(r)],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../v1.2/embedding-ab-evidence.json")
    args = ap.parse_args()

    results = [rank_with("lexical(frozen://lexical-relevance-v1)",
                         LexicalProvider().embed)]
    results.append(rank_with("mock(random, 现状)", MockProvider().embed))

    # P1：真嵌入（若配置端点）
    base = os.environ.get("FREEZE_EMBED_BASE_URL")
    model = os.environ.get("FREEZE_EMBED_MODEL")
    if base and model:
        prov = OpenAICompatProvider(base, os.environ.get("FREEZE_EMBED_API_KEY", ""),
                                    model=model, embed_model=model)
        results.append(rank_with(f"real({model})", lambda t: prov.embed(t)))
    else:
        results.append({"method": "real(P1)", "status": "not_available",
                        "note": "未配置 FREEZE_EMBED_BASE_URL/MODEL；真语义相关性未验证"})

    # 评分：lexical 是否把含「锄头/老李」的记忆排进 top-2
    lex = results[0]["top"][:2]
    lex_hit = {x["index"] for x in lex} & {0, 7}
    evidence = {
        "embedding_model": "frozen://lexical-relevance-v1",
        "fidelity_note": "确定性词法相关度：仅词面/词袋，无语义；真语义相关性未验证",
        "query": QUERY,
        "n_memories": len(MEMORIES),
        "results": results,
        "lexical_top2_related_hit": sorted(lex_hit),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, ensure_ascii=False, indent=2)

    for r in results:
        print(f"\n[{r['method']}]" + (f" status={r.get('status')}" if r.get("status") else ""))
        for x in r.get("top", []):
            print(f"  #{x['rank']} idx={x['index']} score={x['score']} "
                  f"jaccard={x['lexical_overlap']} | {x['text']}")
    print(f"\n[evidence] {args.out}  lexical_top2_related_hit={sorted(lex_hit)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
