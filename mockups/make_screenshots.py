"""Screenshots of the map for posts and the README, in the light and dark themes.

    python -X utf8 mockups/make_screenshots.py        (after python make.py page)  ->  screenshots/*.png

Each view is taken at 1600 x 1000 pixels of page, rendered at double resolution (3200 x 2000 images).
"""
import asyncio, os
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "file:///" + os.path.join(ROOT, "out", "preview.html").replace("\\", "/")
OUT = os.path.join(ROOT, "screenshots")
os.makedirs(OUT, exist_ok=True)

VIEWS = [
    # name, address suffix, what to do once the map is drawn
    ("1-full-map", "", None),
    ("2-map-only", "", "close"),
    ("3-scp-173", "#p=scp-173", None),
    ("4-timeline-2013", "", "past"),
]


async def shot(b, theme, name, suffix, action):
    pg = await b.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=2, color_scheme=theme)
    await pg.goto(URL + suffix)
    await pg.evaluate("t => { document.documentElement.setAttribute('data-theme', t) }", theme)
    await pg.wait_for_timeout(2500)                  # data, fonts and clouds
    if action == "close":
        for sel in ("#sideClose", "#panelClose"):
            if await pg.is_visible(sel): await pg.click(sel)
        await pg.wait_for_timeout(800)
        await pg.click("#zfit") if await pg.is_visible("#zfit") else None
    if action == "past":
        await pg.evaluate("() => { const t = document.getElementById('tl1'); t.value = 71; t.dispatchEvent(new Event('input')); }")   # end of 2013
    await pg.wait_for_timeout(1800)
    path = os.path.join(OUT, f"{name}-{theme}.png")
    await pg.screenshot(path=path)
    if action == "close":   # a tighter picture of the map alone, without the empty sides, for posts
        crop = os.path.join(OUT, f"{name}-cropped-{theme}.png")
        await pg.evaluate("() => { const m = document.getElementById('miniKey'); if (m) m.style.visibility = 'hidden'; }")   # the colour key would show in a corner
        await pg.screenshot(path=crop, clip={"x": 300, "y": 150, "width": 880, "height": 740})
        print("wrote", crop)
    await pg.close()
    print("wrote", path)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for theme in ("dark", "light"):
            for name, suffix, action in VIEWS:
                await shot(b, theme, name, suffix, action)
        await b.close()

asyncio.run(main())
