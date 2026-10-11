"""Round 14 checks: highlights close only with the x, hover layer, links in the address, copy link, framed mode, new counts."""
import asyncio, json, re, sys
from playwright.async_api import async_playwright
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
URL = "file://" + ROOT + "/out/preview.html"
ok = True
def check(name, cond, extra=""):
    global ok
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra != "" else ""))
    if not cond: ok = False
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctxt = await b.new_context(viewport={"width":1440,"height":900}, permissions=["clipboard-read","clipboard-write"])
        pg = await ctxt.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:300]))
        await pg.goto(URL + "?scpdebug"); await pg.wait_for_timeout(2500)
        stats = await pg.evaluate("document.querySelector('.stats') ? document.querySelector('.stats').textContent : ''")
        check("stats line", re.search(r"\d[\d,\u00a0\u202f ]{3,} SCP entries", stats) is not None, stats)   # the count changes with each refresh
        box = await pg.locator("#sky").bounding_box()
        # 1. highlight a region via search, click empty spots, highlight stays
        await pg.fill("#q", "Humanoids"); await pg.wait_for_timeout(300)
        opts = await pg.evaluate("Array.from(document.querySelectorAll('#results li[role=option]')).map(e=>e.textContent)")
        i = next((j for j, t in enumerate(opts) if t.startswith("Humanoids")), 0)
        for _ in range(i + 1): await pg.keyboard.press("ArrowDown")
        await pg.keyboard.press("Enter"); await pg.wait_for_timeout(900)
        name0 = await pg.evaluate("document.getElementById('filterName').textContent")
        check("region highlighted", "Humanoids" in name0, name0)
        check("hash carries the region", await pg.evaluate("location.hash") == "#h=r.humanoids", await pg.evaluate("location.hash"))
        for (fx, fy) in [(0.03, 0.12), (0.97, 0.15), (0.03, 0.8), (0.5, 0.06)]:
            await pg.mouse.click(box["x"] + box["width"]*fx, box["y"] + box["height"]*fy); await pg.wait_for_timeout(120)
        check("empty clicks keep the highlight", await pg.evaluate("!document.getElementById('filter').hidden && document.getElementById('filterName').textContent") == name0)
        # select a page inside the highlight then click empty: page lets go, highlight stays
        await pg.evaluate("document.querySelector('#pbody .list li button').click()"); await pg.wait_for_timeout(900)
        h1 = await pg.evaluate("location.hash"); check("hash carries highlight and page", h1.startswith("#h=r.humanoids&p="), h1)
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(150)
        check("Escape lets go of the page first", (await pg.evaluate("location.hash")) == "#h=r.humanoids", await pg.evaluate("location.hash"))
        await pg.click("#filterClear"); await pg.wait_for_timeout(200)
        check("the x closes the highlight", await pg.evaluate("document.getElementById('filter').hidden"))
        check("hash cleared", await pg.evaluate("location.hash") == "", await pg.evaluate("location.hash"))
        # 2. hover layer: main canvas untouched, overlay has pixels
        await pg.evaluate("window.__d = 0; const d0 = window.__scp.draw; window.__scp.S.__x = 1;")
        before = await pg.evaluate("document.getElementById('sky').toDataURL().length")
        hit = None
        for i in range(400):
            x = box["x"] + 200 + (i*7) % 400; y = box["y"] + 250 + (i*13) % 300
            await pg.mouse.move(x, y)
            if await pg.evaluate("window.__scp.S.hover") >= 0: hit = (x, y); break
        check("a dot can be hovered", hit is not None)
        await pg.wait_for_timeout(120)
        px = await pg.evaluate("(()=>{const c=document.getElementById('skyHover'),d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let n=0;for(let i=3;i<d.length;i+=4) if(d[i]) n++;return n})()")
        check("hover layer is drawn", px > 50, px)
        check("tooltip shown", not await pg.evaluate("document.getElementById('tip').hidden"))
        after = await pg.evaluate("document.getElementById('sky').toDataURL().length")
        check("map canvas unchanged by hover", before == after, (before, after))
        await pg.mouse.move(5, 5); await pg.wait_for_timeout(120)
        px = await pg.evaluate("(()=>{const c=document.getElementById('skyHover'),d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let n=0;for(let i=3;i<d.length;i+=4) if(d[i]) n++;return n})()")
        check("hover layer cleared on leave", px == 0, px)
        # 3. lists and series keys
        await pg.click("#m-lists"); await pg.wait_for_timeout(150)
        await pg.evaluate("Array.from(document.querySelectorAll('#pop li button')).find(b=>b.textContent.includes('Joke pages')).click()"); await pg.wait_for_timeout(500)
        check("list key in hash", await pg.evaluate("location.hash") == "#h=l.jokes", await pg.evaluate("location.hash"))
        jc = await pg.evaluate("document.getElementById('filterCount').textContent"); check("joke list count", jc.replace(",", "").replace(" ", "").replace(" ", "").isdigit() and int(jc.replace(",", "").replace(" ", "").replace(" ", "")) > 400, jc)
        note = await pg.evaluate("document.getElementById('pbody').textContent"); check("joke list note", "read from the live wiki" in note)
        await pg.click("#m-series"); await pg.wait_for_timeout(150)
        labels = await pg.evaluate("Array.from(document.querySelectorAll('#pop li')).map(b=>b.textContent)"); check("no 'missing jokes' note in Series", not any("missing from the data snapshot" in t for t in labels), labels[-2:])
        await pg.evaluate("Array.from(document.querySelectorAll('#pop li button')).find(b=>b.textContent.includes('SCP-001')).click()"); await pg.wait_for_timeout(500)
        check("series key in hash", (await pg.evaluate("location.hash")).startswith("#h=s."), await pg.evaluate("location.hash"))
        # 4. copy link
        check("copy button visible", not await pg.evaluate("document.getElementById('linkBtn').hidden"))
        await pg.click("#linkBtn"); await pg.wait_for_timeout(200)
        clip = await pg.evaluate("navigator.clipboard.readText()"); check("clipboard holds the link", clip.endswith(await pg.evaluate("location.hash")) and "#h=s." in clip, clip[-40:])
        check("button says Copied", await pg.evaluate("document.getElementById('linkBtn').textContent") == "Copied")
        await pg.screenshot(path="out/r14-header.png", clip={"x": 1440-420, "y": 0, "width": 420, "height": 260})
        # 5. open links
        for hsh, want_chip, want_sel in [("#h=t.reptile&p=scp-682", "reptile", "SCP-682"), ("#scp-173", None, "SCP-173"), ("#h=l.jokes", "Joke pages", None), ("#h=a." + "djkaktus", "djkaktus", None),
                                         ("#h=r.cognitohazards-memetics", "Cognitohazards", None), ("#h=k.2", "GoIs", None), ("#h=t.jam-con2021", "JamCon 2021", None), ("#p=scp-5000-j&h=zz.bad", None, "SCP-5000-J"), ("#h=s.15&p=scp-l100", "Lost", "SCP-L100")]:
            pg2 = await ctxt.new_page(); e2 = []; pg2.on("pageerror", lambda e: e2.append(str(e)[:200]))
            await pg2.goto(URL + hsh); await pg2.wait_for_timeout(2600)
            chip = await pg2.evaluate("document.getElementById('filter').hidden ? null : document.getElementById('filterName').textContent")
            body = await pg2.evaluate("document.getElementById('pbody').textContent.slice(0, 160)")
            good = (want_chip is None and chip is None or (want_chip and chip and want_chip.lower() in chip.lower())) and (want_sel is None or want_sel in body) and not e2
            check("link " + hsh, good, (chip, body[:60], e2))
            await pg2.close()
        # hashchange in the same tab
        await pg.evaluate("location.hash = '#h=t.humanoid'"); await pg.wait_for_timeout(700)
        check("hashchange applies", "humanoid" in (await pg.evaluate("document.getElementById('filterName').textContent")).lower())
        # 6. limits text
        await pg.click("#filterClear"); await pg.wait_for_timeout(200)
        txt = await pg.evaluate("document.getElementById('pbody').textContent")
        j = txt.find("Source."); print("   ", txt[j:j+420])
        check("limits: short, with the added pages and the full method", "589 Lost, SCP-001 and joke entries" in txt and "joke entries could not be read" in txt
              and "METHODS.md on GitHub" in txt and "undefined" not in txt and "NaN" not in txt)
        # 7. estimated date label
        pg3 = await ctxt.new_page(); await pg3.goto(URL + "#p=scp-l100"); await pg3.wait_for_timeout(2400)
        t3 = await pg3.evaluate("document.getElementById('pbody').textContent"); check("lost entry: last edited", "Last edited:" in t3)
        slug = json.load(open("extra_pages.json")); est = [r["slug"] for r in slug if r["group"] == "joke" and r["approx"]][0]
        await pg3.goto(URL + "#p=" + est); await pg3.reload(); await pg3.wait_for_timeout(2400)
        t3 = await pg3.evaluate("document.getElementById('pbody').textContent"); check("joke with estimated date", "(estimated)" in t3, est)
        await pg3.close()
        # 8. framed: no link button, no errors, no hash written
        open("out/frame.html", "w").write('<!doctype html><meta charset="utf-8"><body style="margin:0"><iframe id="f" src="preview.html" style="width:100vw;height:100vh;border:0"></iframe>')
        pg4 = await ctxt.new_page(); e4 = []; pg4.on("pageerror", lambda e: e4.append(str(e)[:200]))
        await pg4.goto("file://" + ROOT + "/out/frame.html"); await pg4.wait_for_timeout(3000)
        fr = pg4.frames[1]
        check("framed: link button hidden", await fr.evaluate("document.getElementById('linkBtn').hidden"))
        await fr.fill("#q", "scp-173"); await pg4.wait_for_timeout(300); await pg4.keyboard.press("Enter"); await pg4.wait_for_timeout(800)
        check("framed: no hash written, no errors", await fr.evaluate("location.hash") == "" and not e4, e4)
        check("framed: page selected", "SCP-173" in await fr.evaluate("document.getElementById('pbody').textContent.slice(0,100)"))
        await pg4.close()
        check("no page errors", not errs, errs)
        await b.close()
    print("ALL OK" if ok else "SOME FAILED")
    if not ok: sys.exit(1)    # so that make.py, and the daily job, stop here
asyncio.run(main())
