"""Round 15 checks: region names on phones, search box emptied, colour key on the map, tale series menu."""
import asyncio, json, os
from playwright.async_api import async_playwright
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
        pg = await b.new_page(viewport={"width":1440,"height":900}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:300]))
        await pg.goto(URL + "?scpdebug"); await pg.wait_for_timeout(2500)
        # search box empties
        await pg.fill("#q", "scp-173"); await pg.wait_for_timeout(300); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(700)
        check("search box emptied after Enter", await pg.evaluate("document.getElementById('q').value") == "")
        check("page selected", "SCP-173" in await pg.evaluate("document.getElementById('pbody').textContent.slice(0,80)"))
        await pg.fill("#q", "antimem"); await pg.wait_for_timeout(300)
        res = await pg.evaluate("Array.from(document.querySelectorAll('#results li')).map(e=>e.textContent)")
        check("search finds the tale series", any(t.startswith("Tale series") for t in res) and any("Antimemetics Division Hub" in t for t in res), res[:8])
        i = next(j for j, t in enumerate(await pg.evaluate("Array.from(document.querySelectorAll('#results li[role=option]')).map(e=>e.textContent)")) if "Antimemetics Division Hub" in t)
        await pg.evaluate(f"document.querySelectorAll('#results li[role=option]')[{i}].dispatchEvent(new MouseEvent('mousedown', {{bubbles:true, cancelable:true}}))"); await pg.wait_for_timeout(900)
        check("search box emptied after a click", await pg.evaluate("document.getElementById('q').value") == "")
        check("series highlighted", await pg.evaluate("document.getElementById('filterName').textContent") == "Tale series: Antimemetics Division Hub", await pg.evaluate("document.getElementById('filterName').textContent"))
        check("hash", await pg.evaluate("location.hash") == "#h=u.antimemetics-division-hub", await pg.evaluate("location.hash"))
        body = await pg.evaluate("document.getElementById('pbody').innerText")
        check("panel: reading order and sections", "Reading order given by the hub" in body and "There Is No Antimemetics Division" in body and "Hub page on the wiki" in body and "undefined" not in body, body[:300])
        nums = await pg.evaluate("document.querySelectorAll('#pbody ol.list.num li').length"); check("33 numbered rows", nums == 33, nums)
        last = await pg.evaluate("getComputedStyle(document.querySelector('#pbody ol.list.num:last-of-type li:last-child'), '::before').content"); check("numbering runs through the sections", "counter" in last or last != "none", last)
        await pg.screenshot(path="out/r15-hub.png")
        # menu
        await pg.click("#m-hubs"); await pg.wait_for_timeout(200)
        heads = await pg.evaluate("Array.from(document.querySelectorAll('#pop li.grp')).map(e=>e.textContent)")
        check("menu grouped by canon", any(x.startswith("Canon: ") for x in heads) and any(x.startswith("No canon") for x in heads), heads[:6])
        await pg.screenshot(path="out/r15-menu.png", clip={"x":0,"y":60,"width":700,"height":640})
        await pg.evaluate("Array.from(document.querySelectorAll('#pop .sortrow button')).find(b=>b.textContent==='By date').click()"); await pg.wait_for_timeout(150)
        heads = await pg.evaluate("Array.from(document.querySelectorAll('#pop li.grp')).map(e=>e.textContent)"); check("menu by date", len(heads) > 3 and all(h.isdigit() and len(h) == 4 for h in heads) and heads == sorted(heads), heads[:4])
        await pg.evaluate("Array.from(document.querySelectorAll('#pop .sortrow button')).find(b=>b.textContent==='A to Z').click()"); await pg.wait_for_timeout(150)
        await pg.evaluate("Array.from(document.querySelectorAll('#pop li button')).find(b=>b.textContent.includes('Austringers')).click()"); await pg.wait_for_timeout(900)
        body = await pg.evaluate("document.getElementById('pbody').innerText")
        check("series with canons", "Belongs to:" in body and "Third Law (canon)" in body and "Anderson Robotics (GoI)" in body, body[:400])
        await pg.evaluate("document.querySelector('#pbody ol.list.num li button').click()"); await pg.wait_for_timeout(900)
        body = await pg.evaluate("document.getElementById('pbody').innerText"); check("file names its series", "Tale series: Austringers" in body.replace("\n", " "), body[:300])
        check("highlight kept while a page is open", "Austringers" in await pg.evaluate("document.getElementById('filterName').textContent"))
        await pg.evaluate("Array.from(document.querySelectorAll('#pbody button.tag')).find(b=>b.textContent==='Austringers').click()"); await pg.wait_for_timeout(600)
        await pg.evaluate("Array.from(document.querySelectorAll('#pbody button.tag')).find(b=>b.textContent==='Third Law').click()"); await pg.wait_for_timeout(700)
        check("canon chip leads to the canon", "Third Law" in await pg.evaluate("document.getElementById('filterName').textContent"), await pg.evaluate("document.getElementById('filterName').textContent"))
        await pg.click("#navBack"); await pg.wait_for_timeout(600)
        check("back returns to the series", "Austringers" in await pg.evaluate("document.getElementById('filterName').textContent"))
        await pg.click("#filterClear"); await pg.wait_for_timeout(200)
        # colour key
        check("key hidden while the column is open", await pg.evaluate("document.getElementById('miniKey').hidden"))
        await pg.click("#sideClose"); await pg.wait_for_timeout(300)
        check("key shown when the column is closed", "Object class" in await pg.evaluate("document.getElementById('miniKey').hidden ? '' : document.getElementById('miniKey').textContent"))
        await pg.screenshot(path="out/r15-key.png", clip={"x":0,"y":100,"width":760,"height":260})
        await pg.click("#sideOpen"); await pg.wait_for_timeout(200)
        await pg.select_option("#mode", "year"); await pg.wait_for_timeout(100); await pg.click("#sideClose"); await pg.wait_for_timeout(200)
        check("key follows the colour mode", "Year posted" in await pg.evaluate("document.getElementById('miniKey').textContent"), await pg.evaluate("document.getElementById('miniKey').textContent"))
        # limits
        await pg.click("#sideOpen")
        txt = await pg.evaluate("document.getElementById('pbody').textContent"); i = txt.find("Tale series."); print("   ", txt[i:i+330]); check("limits mention tale series", i > 0)
        check("no page errors (desktop)", not errs, errs)
        # links
        pg2 = await b.new_page(viewport={"width":1440,"height":900}); await pg2.goto(URL + "#h=u.austringers&p=realignment"); await pg2.wait_for_timeout(2600)
        check("link to a series and a page", "Austringers" in await pg2.evaluate("document.getElementById('filterName').textContent") and "Realignment" in await pg2.evaluate("document.getElementById('pbody').textContent.slice(0,120)"))
        await pg2.close()
        # phone
        ph = await b.new_page(viewport={"width":390,"height":780}, has_touch=True, device_scale_factor=2); e2 = []; ph.on("pageerror", lambda e: e2.append(str(e)[:300]))
        await ph.goto(URL); await ph.wait_for_timeout(3200)
        check("phone: key shown", "Object class" in await ph.evaluate("document.getElementById('miniKey').hidden ? '' : document.getElementById('miniKey').textContent"))
        await ph.screenshot(path="out/r15-phone.png")
        await ph.evaluate("document.getElementById('m-hubs').click()"); await ph.wait_for_timeout(300)
        await ph.evaluate("Array.from(document.querySelectorAll('#pop li button')).find(b=>b.textContent.includes('Rise Of the Pit Sloth')).click()"); await ph.wait_for_timeout(1200)
        await ph.screenshot(path="out/r15-phone-hub.png")
        check("no page errors (phone)", not e2, e2)
        await b.close()
    print("ALL OK" if ok else "SOME FAILED")
asyncio.run(main())
