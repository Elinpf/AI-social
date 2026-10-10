from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image
OUT = Path(__file__).resolve().parent
exe = "/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome"
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, executable_path=exe,
        args=["--no-sandbox","--enable-unsafe-swiftshader","--use-gl=angle","--use-angle=swiftshader"])
    ctx = b.new_context(viewport={"width":1920,"height":1080}, device_scale_factor=1)
    pg = ctx.new_page()
    pg.goto("http://127.0.0.1:8848/?log=sample/demo_run.jsonl", wait_until="load", timeout=60000)
    pg.wait_for_timeout(9000)
    pg.screenshot(path=str(OUT/"demo_run_wide1920.png"), full_page=True)
    b.close()
# crops from the 1600x1000 demo_run.png
im = Image.open(OUT/"demo_run.png")
im.crop((320, 150, 920, 560)).resize((1200,820), Image.NEAREST).save(OUT/"crop_center.png")
im.crop((430, 30, 1120, 260)).resize((1380,460), Image.NEAREST).save(OUT/"crop_top_buildings.png")
im.crop((1180, 330, 1520, 470)).resize((1020,420), Image.NEAREST).save(OUT/"crop_agents.png")
im.crop((560, 30, 800, 260)).resize((960,920), Image.NEAREST).save(OUT/"crop_farm.png")
print("ok")
