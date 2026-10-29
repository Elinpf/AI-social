#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""D9i 旁白通道臂：两条「括号旁白」口径的读数（主判 = 成对口径，辅助 = 任意括号口径）。

口径写死（避免事后口径漂移）：

1) **成对口径 PAIRED（主判 H0）**
   `PAIRED_RE = （[^（）]{1,120}）|\([^()]{1,120}\)`
   —— 左右括号必须成对出现、中间至少 1 个字符（空括号不算）。
   分子 = body 里至少出现 1 个成对括号块的 MSG 条数；分母 = 全部 MSG 条数。
   同口径另给「括号块总数」（可 > 条数）。

2) **任意括号口径 ANY（辅助对照）**
   `ANY_RE = [（(]`
   —— body 里出现任意一个左括号字符即算（含未闭合单侧、含「（笑）」这类纯情绪标签）。
   同时给出 tools/d5/dialogue_metrics.py 的 `L_wording.L-3_paren_block_any` 作为第三方参照。

3) **旁白内动作/神态词占比（预登记量 5）**
   取成对括号块内文本，按动作/神态词典（词表见 ACTION_WORDS，也可 --action-words 追加文件）判定
   「含动作/神态词」vs「纯情绪标签」。词典是**人工小词表**，只做「动作 vs 情绪标签」粗分类，不作语言质量判定。

用法：
    python3 tools/d9i/narration_stats.py --log <run.jsonl> [--out <json>] [--arm OFF|ON]

注意：本工具只读 run.jsonl，不写任何证据目录之外的路径。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "d5"))
from dialogue_metrics import extract_messages, PAREN_ANY_RE  # noqa: E402

PAIRED_RE = re.compile(r"（[^（）]{1,120}）|\([^()]{1,120}\)")
ANY_RE = re.compile(r"[（(]")

#: 动作/神态小词表（人工；只用于「动作类 vs 纯情绪标签」粗分类）
ACTION_WORDS = (
    "掖", "低头", "抬头", "抬头", "抬手", "点头", "摇头", "皱眉", "叹气", "笑", "咳", "搓", "擦", "推",
    "递", "接", "递过来", "接过", "拍", "敲", "磨", "刨", "劈", "挑", "拎", "搬", "蹲", "站", "坐",
    "起身", "转身", "回身", "迈", "走", "跑", "停", "看", "望", "瞅", "盯", "眯", "翻", "抓", "捧",
    "摸", "抖", "摊手", "摆手", "挥手", "挥手", "咬", "嚼", "咽", "喝", "端", "拿", "放", "搁",
    "吹", "扇", "拢", "拉", "扶", "抱", "背", "扛", "裹", "卷", "拂", "拧", "捻", "抿", "舔", "呵",
    "哈气", "耸肩", "缩手", "搓手", "跺脚", "侧身", "弯腰", "倚", "靠", "坐直", "站直", "抬眼",
    "垂眼", "垂手", "把手", "单手", "双手", "手指", "肩", "额头", "袖口", "围裙", "木屑", "碗", "壶",
    "锅", "勺", "凳", "门槛", "门框", "灯", "窗", "肩头",
)


def _is_action(block: str) -> bool:
    return any(w in block for w in ACTION_WORDS)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--arm", default=None)
    ap.add_argument("--action-words", default=None, help="额外动作词表文件（每行一个词）")
    args = ap.parse_args(argv)

    global ACTION_WORDS
    if args.action_words:
        extra = tuple(w.strip() for w in Path(args.action_words).read_text(encoding="utf-8").splitlines() if w.strip())
        ACTION_WORDS = ACTION_WORDS + extra

    recs = []
    with open(args.log, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except Exception:
                continue
    msgs = extract_messages(recs)
    n_msg = len(msgs)

    paired_msg, any_msg = 0, 0
    blocks_total = 0
    block_counter = Counter()
    action_blocks, emotion_blocks = 0, 0
    samples_action, samples_emotion = [], []
    paren_any_by_metric = 0  # 与 dialogue_metrics 同正则的第三方参照

    for m in msgs:
        body = m.get("body") or ""
        blocks = PAIRED_RE.findall(body)
        if blocks:
            paired_msg += 1
            blocks_total += len(blocks)
            for b in blocks:
                inner = b[1:-1]
                block_counter[inner] += 1
                if _is_action(inner):
                    action_blocks += 1
                    if len(samples_action) < 8:
                        samples_action.append(inner[:60])
                else:
                    emotion_blocks += 1
                    if len(samples_emotion) < 8:
                        samples_emotion.append(inner[:60])
        if ANY_RE.search(body):
            any_msg += 1
        if PAREN_ANY_RE.search(body):
            paren_any_by_metric += 1

    def rate(n, d):
        return (round(n / d, 6) if d else None)

    out = {
        "arm": args.arm,
        "log": str(Path(args.log).resolve()),
        "denominator_msg_total": n_msg,
        "paired": {
            "regex": r"（[^（）]{1,120}）|\([^()]{1,120}\)",
            "msgs_with_paired_paren": paired_msg,
            "rate": rate(paired_msg, n_msg),
            "blocks_total": blocks_total,
            "action_blocks": action_blocks,
            "emotion_or_other_blocks": emotion_blocks,
            "action_share_of_blocks": rate(action_blocks, blocks_total),
            "block_top": [{"inner": k, "count": v} for k, v in block_counter.most_common(15)],
            "samples_action": samples_action,
            "samples_emotion_or_other": samples_emotion,
        },
        "any_paren": {
            "regex": r"[（(]",
            "msgs_with_any_open_paren": any_msg,
            "rate": rate(any_msg, n_msg),
            "note": "任意左括号字符（含未闭合单侧、纯情绪标签）",
        },
        "cross_check_dialogue_metrics_L3": {
            "regex": PAREN_ANY_RE.pattern,
            "msgs": paren_any_by_metric,
            "rate": rate(paren_any_by_metric, n_msg),
            "note": "tools/d5/dialogue_metrics.py 的 PAREN_ANY_RE（同样要求成对，0 字符内容也算）",
        },
    }
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(txt + "\n", encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
