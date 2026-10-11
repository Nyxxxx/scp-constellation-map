import asyncio, random, sys
from playwright.async_api import async_playwright
import os
ROOT = os.path.dirname(os.path.abspath(__file__))
URL = "file://" + ROOT + "/out/preview.html"
async def run(seed, vw, vh, scheme, touch):
    random.seed(seed)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width":vw,"height":vh}, color_scheme=scheme, has_touch=touch)
        errs = []
        pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)[:300]))
        pg.on("console", lambda m: errs.append("CONSOLE " + m.text[:200]) if m.type == "error" and "ERR_TUNNEL" not in m.text else None)
        await pg.goto(URL); await pg.wait_for_timeout(2500)
        log = []
        async def act(name, coro):
            log.append(name)
            try: await coro
            except Exception as e: errs.append("ACT " + name + ": " + str(e).split("\n")[0][:160])
        box = await pg.evaluate("(()=>{const r=document.getElementById('sky').getBoundingClientRect();return [r.left,r.top,r.width,r.height]})()")
        def rp(): return (box[0] + random.uniform(20, box[2]-20), box[1] + random.uniform(60, box[3]-120))
        async def vis(sel): return await pg.evaluate(f"(()=>{{const e=document.querySelector({sel!r}); if(!e) return false; const r=e.getBoundingClientRect(); return !!(r.width&&r.height) && getComputedStyle(e).visibility!=='hidden' && !e.disabled}})()")
        async def click_if(sel):
            if await vis(sel): await pg.click(sel, timeout=1500)
        async def menu(key):
            await click_if(f"#m-{key}")
            n = await pg.evaluate("document.querySelectorAll('#pop li button').length")
            if n:
                i = random.randrange(n)
                await pg.evaluate(f"document.querySelectorAll('#pop li button')[{i}].click()")
        async def setsel(id_, values):
            if await pg.evaluate(f"!!document.getElementById('{id_}')"):
                v = random.choice(values)
                await pg.evaluate(f"(()=>{{const s=document.getElementById('{id_}'); s.value='{v}'; s.dispatchEvent(new Event('change'))}})()")
        async def toggle(id_):
            await pg.evaluate(f"(()=>{{const c=document.getElementById('{id_}'); if(c){{c.click()}}}})()")
        async def slider(id_):
            await pg.evaluate(f"(()=>{{const c=document.getElementById('{id_}'); if(c){{c.value=String(Math.round(+c.min+Math.random()*(+c.max-+c.min))); c.dispatchEvent(new Event('input'))}}}})()")
        async def search():
            t = random.choice(["173","serpent","jam","horror","series 3","qntm","the","lost","001","zzzzqq","clef","foundation","L0","a"])
            await pg.fill("#q", t); await pg.wait_for_timeout(150)
            n = await pg.evaluate("document.querySelectorAll('#results li[role=option]').length")
            if n and random.random() < .8:
                for _ in range(random.randrange(0, min(n, 6))): await pg.keyboard.press("ArrowDown")
                await pg.keyboard.press("Enter")
            else: await pg.keyboard.press("Escape")
        async def listrow():
            n = await pg.evaluate("document.querySelectorAll('#pbody .list li button').length")
            if n: await pg.evaluate(f"document.querySelectorAll('#pbody .list li button')[{random.randrange(n)}].click()")
        async def tagchip():
            n = await pg.evaluate("document.querySelectorAll('#pbody .tags button, #pbody .tags a, #pbody .chip').length")
            if n: await pg.evaluate(f"document.querySelectorAll('#pbody .tags button, #pbody .tags a, #pbody .chip')[{random.randrange(n)}].click()")
        actions = [
            ("click map", lambda: pg.mouse.click(*rp())), ("click map", lambda: pg.mouse.click(*rp())), ("click map", lambda: pg.mouse.click(*rp())),
            ("wheel in", lambda: pg.mouse.wheel(0, -random.choice([200, 500, 1200]))),
            ("wheel out", lambda: pg.mouse.wheel(0, random.choice([200, 500, 1500]))),
            ("menu goi", lambda: menu("goi")), ("menu canon", lambda: menu("canon")), ("menu contest", lambda: menu("contest")),
            ("menu series", lambda: menu("series")), ("menu lists", lambda: menu("lists")),
            ("random page", lambda: click_if(".hlbar .dice")), ("search", search), ("list row", listrow), ("list row", listrow), ("tag chip", tagchip),
            ("back", lambda: click_if("#navBack")), ("fwd", lambda: click_if("#navFwd")), ("guide", lambda: click_if("#guideBtn")),
            ("clear", lambda: click_if("#filterClear")), ("fit", lambda: click_if("#zfit")), ("zin", lambda: click_if("#zin")), ("zout", lambda: click_if("#zout")),
            ("mode", lambda: setsel("mode", ["type","class","risk","dis","year"])), ("yearpal", lambda: setsel("yearPal", ["eras","viridis","ramp"])),
            ("cloud", lambda: setsel("cloudSrc", ["region","goi","canon","off"])), ("cloudstyle", lambda: setsel("cloudStyle", ["fill","outline"])),
            ("types", lambda: toggle(random.choice(["ty0","ty1","ty2","tyJ"]))), ("layer", lambda: toggle(random.choice(["tTag","tPage","tNames","tCanon","tGoi","tRing","tTime"]))),
            ("class", lambda: toggle(random.choice(["cls0","cls1","cls2","cls3","cls16","clsEso","clsAll","clsNone","clsAll"]))),
            ("rating", lambda: slider(random.choice(["rat0","rat1"]))), ("rat all", lambda: click_if("#ratAll")),
            ("tl", lambda: slider(random.choice(["tl0","tl1"]))), ("play", lambda: click_if("#play")), ("tl year", lambda: pg.evaluate("(()=>{const b=document.querySelectorAll('#tlYears button'); if(b.length) b[Math.floor(Math.random()*b.length)].click()})()")),
            ("tl all", lambda: click_if("#tlAll")), ("theme", lambda: click_if("#themeBtn")),
            ("side", lambda: click_if(random.choice(["#sideClose","#sideOpen"]))), ("panel", lambda: click_if(random.choice(["#panelClose","#panelOpen","#sheetBtn"]))),
            ("esc", lambda: pg.keyboard.press("Escape")),
            ("drag", lambda: drag()),
        ]
        async def drag():
            a, c = rp(), rp(); await pg.mouse.move(*a); await pg.mouse.down(); await pg.mouse.move(*c, steps=4); await pg.mouse.up()
        for step in range(170):
            name, fn = random.choice(actions)
            await act(name, fn())
            await pg.wait_for_timeout(random.choice([30, 60, 120, 400]))
            if errs and any(e.startswith(("PAGEERROR","CONSOLE")) for e in errs): break
        state = await pg.evaluate("({ov: document.documentElement.scrollWidth > innerWidth, shown: document.getElementById('shown').textContent, nan: /NaN|undefined/.test(document.getElementById('app').innerText)})")
        real = [e for e in errs if e.startswith(("PAGEERROR","CONSOLE"))]
        print(f"seed {seed} {vw}x{vh} {scheme}: steps {len(log)} | page errors {len(real)} | act errors {len(errs)-len(real)} | {state}")
        for e in real[:4]: print("   ", e, "| last actions:", log[-8:])
        for e in [e for e in errs if e.startswith('ACT')][:3]: print("   ", e)
        if state["nan"]:
            print("    NaN/undefined text:", await pg.evaluate("(document.getElementById('app').innerText.match(/.{0,60}(NaN|undefined).{0,40}/g)||[]).slice(0,3)"))
        if real or state["ov"] or state["nan"]: BAD.append(seed)
        await b.close()
BAD = []    # runs with a page error, a page wider than the screen, or NaN/undefined in the text
async def main():
    for seed, (vw, vh, sc, touch) in enumerate([(1440,900,"light",False),(390,780,"dark",True),(1024,700,"dark",False),(1440,900,"dark",False),(820,1100,"light",True)]):
        await run(seed + 31, vw, vh, sc, touch)
    print("ALL OK" if not BAD else "SOME FAILED: seeds " + str(BAD))
    if BAD: sys.exit(1)
asyncio.run(main())
