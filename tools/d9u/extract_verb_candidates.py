#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D9u 第一步：从三份语料的旁白片段提取单字候选动词。

口径（与 D9u 预登记 §3.1 一致，不得自行放宽）：
  1. 片段来源：PAIRED_RE × extract_messages（与 narration_family.py 同源）
  2. 先排除功能词闭集 + 趋向补语
  3. 阈值：三份合计 >= 8 次才入候选
   ⚠ 方法修正（v2，2026-10-30 21:1x）：v1 只按"单字频次"提取，结果 top 全是名词
     （头 153 / 子 134 / 里 117 / 边 117 / 手 79），因为中文单字"名动同形"，
     频次无法区分词性。⇒ v2 改为「先人工列动词白名单，再与语料频次取交集」：
     白名单负责"是不是动词"，语料负责"用不用得上"。
输出：字 / 三份各自频次 / 合计 / 是否入选 / 说明
只读，不改任何词表。
"""
import sys, importlib.util, collections, json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "metrics"))
spec = importlib.util.spec_from_file_location("nf", REPO / "tools/d9n/narration_family.py")
nf = importlib.util.module_from_spec(spec); sys.argv = ["nf"]; spec.loader.exec_module(nf)

FUNC = set("的了着在是一上下来去还就都又很把拿往没不等也都只把自己我他她它这那些个之与和但我你谁什怎还再才已经过被从向对给让使")
DIRECTIONAL = set("住到起开掉走")
ARMS = [
    ("OFF_run1", "v2/evidence/d9s-syntax-off_n16r24_s42/run.jsonl"),
    ("ON2",      "v2/evidence/d9s-on2_n16r24_s42/run.jsonl"),
    ("A+B",      "v2/evidence/d9m-ab-on_n16r24_s42/run.jsonl"),
]
THRESHOLD = 8

# 人工动词白名单（单字、光杆、可带宾语/补语）。只收这类，名词/量词/介词一律不收。
VERB_WHITELIST = set("""
压 走 敲 敞 停 翻 响 搁 推 捏 掀 拨 按 摊 掰 磨 码 绕 缠 垫 插 拽 提 放 摆 端 盛 装 夹 拧 抖
擦 掸 刮 削 砍 劈 掘 铲 浇 晾 晒 煮 熬 炒 蒸 揉 搓 系 绑 解 挂 挪 捧 拎 扛 挑 背 捡 拾 递 接
扔 抛 倒 灌 吸 喝 咬 嚼 咽 叼 含 吹 喊 叫 应 笑 叹 哼 蹲 站 坐 躺 趴 跪 靠 倚 倚 蹭 抹 拍 扇
望 盯 瞧 瞥 瞅 听 闻 尝 摸 抚 拂 拽 扯 拉 拖 顶 扛 抱 搂 搀 扶 搭 扣 拴 捆 扎 缠 裹 包 卷 折
叠 铺 展 摊 晾 烤 烘 烫 烧 点 灭 吹 熄 舀 盛 倒 添 减 数 量 记 算 写 画 描 抄 誊 撕 剪 裁 缝
补 钉 锤 锯 凿 刨 锉 磨 削 削 拧 转 摇 晃 摆 甩 抖 拍 敲 叩 擂 捣 碾 筛 簸 淘 洗 涮 泡 浸 煮
""".split())

# 只保留白名单内的字
def keep(ch):
    return ch in VERB_WHITELIST

def frags(p):
    return [f[1:-1] for m in nf.extract_messages(nf.read_log(p)) for f in nf.PAIRED_RE.findall(m['body'] or '')]

per = {}
tots = collections.Counter()
for name, p in ARMS:
    fs = frags(p)
    c = collections.Counter()
    for s in fs:
        for ch in set(s):
            if keep(ch):
                c[ch] += 1
    per[name] = c
    tots.update(c)
    print(f"[{name}] 片段 {len(fs)}", file=sys.stderr)

rows = []
for ch, n in tots.most_common():
    ok = n >= THRESHOLD
    rows.append({"ch": ch, **{k: per[k][ch] for k, _ in ARMS}, "total": n, "candidate": ok})

print(f"{'字':2s} {'OFF':>4s} {'ON2':>4s} {'A+B':>4s} {'合计':>4s}  入选")
for r in rows:
    if r["total"] >= THRESHOLD:
        print(f"{r['ch']} {r['OFF_run1']:4d} {r['ON2']:4d} {r['A+B']:4d} {r['total']:4d}  是")
print(f"\n候选（≥{THRESHOLD}）共 {sum(1 for r in rows if r['candidate'])} 个")
print("（本脚本只提取，不做人工筛；筛词见 D9u 预登记 §3.1 第二步）")
