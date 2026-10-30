#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 narration_hedge 的 table.md 渲染成 HTML 再真截图（零 LLM）。

链路（严格按团队纪律）：
    table.md --(md→html)--> $HOME/*.html --(playwright/chromium)--> $HOME/*.png
    --> cp 入仓库 v2/evidence/narration_hedge_shots/（**绝不直接写仓库**）

用法：
    python3 v2/evidence/narration_hedge_shots/render_table_shot.py \
        --md v2/evidence/narration_hedge/table.md \
        --out-png v2/evidence/narration_hedge_shots/narration_hedge_table.png \
        --title "R27 · 旁白 × 生活气息 F-1…F-7 同表联报"

退出码：0 成功 / 2 输入缺失或渲染失败
"""
from __future__ import annotations
import argparse, hashlib, html, os, pathlib, re, shutil, subprocess, sys, tempfile

HOME = pathlib.Path(os.environ.get("HOME", "/root"))


def _repo_root() -> pathlib.Path:
    """优先当前工作目录（约定在仓库根执行），否则按脚本位置回溯。"""
    cwd = pathlib.Path.cwd()
    if (cwd / "code" / "frontend" / "tools" / "_chrome.py").exists():
        return cwd
    return pathlib.Path(__file__).resolve().parents[2]


REPO = _repo_root()
CHROME_HELPER = REPO / "code" / "frontend" / "tools"


def md_tables_to_html(md: str) -> str:
    """极简 Markdown → HTML：只处理标题/表格/段落/引用/代码围栏，够本报告用。"""
    out, lines, i = [], md.split("\n"), 0
    in_code = False
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("```"):
            in_code = not in_code
            out.append("<pre>" if in_code else "</pre>")
            i += 1
            continue
        if in_code:
            out.append(html.escape(ln))
            i += 1
            continue
        if re.match(r"^\|", ln.strip()) and i + 1 < len(lines) and re.match(r"^\|[\s:\-|]+\|$", lines[i + 1].strip()):
            header = [c.strip() for c in ln.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and re.match(r"^\|", lines[i].strip()):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in header) + "</tr></thead><tbody>")
            for r in rows:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            out.append("</tbody></table>")
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        if ln.strip().startswith(">"):
            out.append(f"<blockquote>{inline(ln.strip().lstrip('>').strip())}</blockquote>")
            i += 1
            continue
        if ln.strip().startswith("- "):
            out.append(f"<p class='li'>{inline(ln.strip()[2:])}</p>")
            i += 1
            continue
        if ln.strip():
            out.append(f"<p>{inline(ln.strip())}</p>")
        i += 1
    return "\n".join(out)


def inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    return s


HTML_TMPL = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>{title}</title>
<style>
 body{{font-family:"Noto Sans CJK SC","WenQuanYi Zen Hei","DejaVu Sans",sans-serif;
       margin:24px;background:#fff;color:#111;font-size:14px;line-height:1.55;max-width:1400px}}
 h1{{font-size:21px;margin:0 0 4px}} h2{{font-size:17px;margin:20px 0 8px;border-left:4px solid #2b6cb0;padding-left:8px}}
 h3{{font-size:15px;margin:14px 0 6px}}
 table{{border-collapse:collapse;margin:8px 0 14px;font-size:13px}}
 th,td{{border:1px solid #999;padding:5px 10px;text-align:left;white-space:nowrap;vertical-align:top}}
 th{{background:#eef1f5}} tr:nth-child(even) td{{background:#fafafa}}
 blockquote{{margin:4px 0;padding:6px 10px;background:#f5f7fa;border-left:3px solid #999;color:#333}}
 pre{{background:#f6f6f6;padding:8px;font-size:12px;white-space:pre-wrap}}
 code{{background:#f0f0f0;padding:1px 4px;border-radius:3px;font-size:12px}}
 p.li{{margin:2px 0 2px 12px}}
 .meta{{color:#555;font-size:12px;margin:0 0 12px}}
</style></head><body>
<h1>{title}</h1>
<p class="meta">渲染来源：{mdname}　|　本图为真浏览器渲染（playwright/chromium），非示意图</p>
{body}
</body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", required=True)
    ap.add_argument("--out-png", required=True)
    ap.add_argument("--title", default="旁白 × 生活气息 F-1…F-7 同表联报")
    a = ap.parse_args()

    md_path = pathlib.Path(a.md)
    if not md_path.exists():
        print(f"缺输入：{md_path}", file=sys.stderr)
        return 2
    md = md_path.read_text(encoding="utf-8")
    body = md_tables_to_html(md)
    doc = HTML_TMPL.format(title=html.escape(a.title), mdname=html.escape(str(a.md)), body=body)

    HOME.mkdir(parents=True, exist_ok=True)
    tmp_html = HOME / "narration_hedge_prep" / "narration_hedge_table.html"
    tmp_html.parent.mkdir(parents=True, exist_ok=True)
    tmp_html.write_text(doc, encoding="utf-8")
    tmp_png = HOME / "narration_hedge_prep" / "narration_hedge_table.png"

    sys.path.insert(0, str(CHROME_HELPER))
    from playwright.sync_api import sync_playwright
    from _chrome import find_chrome

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=find_chrome(), args=["--no-sandbox", "--font-render-hinting=none"])
        pg = b.new_page(viewport={"width": 1500, "height": 900}, device_scale_factor=2)
        pg.goto(tmp_html.resolve().as_uri())
        pg.wait_for_load_state("load")
        pg.wait_for_timeout(250)
        box = pg.evaluate("""() => { let r=0,bt=0;
            for (const el of document.body.children){const q=el.getBoundingClientRect();
              r=Math.max(r,q.right); bt=Math.max(bt,q.bottom);} return {w:Math.ceil(r)+32,h:Math.ceil(bt)+32}; }""")
        pg.set_viewport_size({"width": max(box["w"], 900), "height": box["h"]})
        pg.wait_for_timeout(150)
        clip = pg.evaluate("""() => { const t=document.querySelectorAll('table');
            return {tables: t.length, overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth}; }""")
        pg.screenshot(path=str(tmp_png), full_page=True)
        b.close()

    data = tmp_png.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    out = pathlib.Path(a.out_png)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(tmp_png, out)
    data2 = out.read_bytes()
    print(f"html: {tmp_html}")
    print(f"png (in $HOME): {tmp_png}")
    print(f"png (copied into repo): {out}")
    print(f"cmp_identical: {data == data2}")
    print(f"bytes: {len(data2)}")
    print(f"sha256: {sha}")
    print(f"clip_check: {clip}")
    try:
        from PIL import Image
        im = Image.open(out); print(f"size: {im.size}")
        px = im.convert("RGB").getdata()
        print("mean_brightness: %.1f" % (sum(sum(q) for q in px) / (len(px) * 3)))
    except Exception as e:
        print("PIL skipped:", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
