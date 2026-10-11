"""Colour mock-ups: copies of the built map with another palette laid over it, and a page that shows them side by side.

    python -X utf8 mockups/make_mockups.py              colour variants   (after python make.py page)
    python -X utf8 mockups/make_mockups.py reading      reading-order variants, shown on one tale series (compare-reading.html)

Each variant only overrides the colour and font settings at the top of page3.src.html; the real page is not changed.
Writes mockups/<variant>.html and mockups/compare.html (not kept in git: rebuild them with this script).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "mockups")
BASE = open(os.path.join(ROOT, "scp-constellation-map-standalone.html"), encoding="utf-8").read()

# The wiki's Anomaly Classification Bar (component:anomaly-class-bar-source, read 11 October 2026):
# Safe rgb(0,159,107), Euclid rgb(255,211,0), Keter rgb(196,2,51), Neutralized/Esoteric rgb(66,66,72),
# Pending rgb(12,12,12), Explained rgb(252,252,252); the same scale has a blue rgb(0,135,189) and an orange rgb(255,109,0).

VARIANTS = {
    "a-wiki": {
        "title": "A · Wiki, refined",
        "note": "Same reds, greys, title and fonts. No pink: menu text and links in true red or neutral. "
                "Object classes in the wiki's official class-bar colours. Map names in neutral inks, told apart by lettering.",
        "fonts": "",
        "theme": None,   # keeps both light and dark
        "light": """
  --c-safe:#009f6b; --c-euclid:#e8b900; --c-keter:#c40233; --c-neut:#55555c; --c-eso:#0087bd; --c-other:#b2b2af;
  --region:#1e1e1e; --canon-label:#6b1d1d; --goi-label:#2f4858;""",
        "dark": """
  --maroon:#e8e6e3; --red:#e5484d; --link:#ec6a6e; --visited:#c98a8a; --pick:#ffffff; --page-line:#e5484d;
  --c-safe:#00b37a; --c-euclid:#ffd300; --c-keter:#e0143f; --c-neut:#8a8a92; --c-eso:#2aa3d6; --c-other:#565656;
  --region:#ffffff; --canon-label:#e9dcc0; --goi-label:#b8c4cc;""",
    },
    "b-dossier": {
        "title": "B · Paper dossier",
        "note": "Manila paper, typewriter lettering for titles and map names, stamp red. Class colours as printed inks. "
                "Region names in black type, canons in blue-black ink, GoIs in carbon-copy violet.",
        "fonts": "family=Special+Elite&family=Courier+Prime:ital,wght@0,400;0,700;1,400;1,700",
        "theme": "light",
        "all": """
  color-scheme:light;
  --page:#e3dac4; --ground:#eee6d2; --block:#f6f0e2; --quote:#e6dcc5;
  --ink:#1f1b16; --ink-2:#4a443b; --ink-3:#6b6458; --rule:#a89f8a; --rule-soft:#d3c9b2; --dash:#8f8672;
  --maroon:#6b1414; --red:#a3161a; --link:#8b1a1a; --visited:#6b3a3a; --pick:#a3161a; --block-shadow:rgba(60,40,10,.25);
  --band:#6b1414; --band-edge:#3a0808; --band-ink:#f6f0e2; --band-sub:#f0e2b0;
  --t-scp:#3a3530; --t-tale:#2c5f6b; --t-goi:#a8700b; --t-joke:#8b3a62;
  --c-safe:#2e7d55; --c-euclid:#c79a00; --c-keter:#a3161a; --c-neut:#6b665c; --c-eso:#4f7c96; --c-other:#bfb59e;
  --none:#c9bfa8; --tag-line:#6b6458; --page-line:#a3161a;
  --region:#1f1b16; --canon-label:#1d3a6e; --goi-label:#5b2d82;
  --font-head:"Special Elite","Courier New",monospace; --font-label:"Courier Prime","Courier New",monospace;
  --clouds:#8a7f68,#6f8a7a,#8a6f6f,#6f7a8a,#8a8a6f,#7f6f8a,#6f8a8a,#8a7a6f;""",
    },
    "c-atlas": {
        "title": "C · Star atlas",
        "note": "Night-blue chart, engraved capitals for regions (like constellations), gold and ivory lettering. "
                "Class colours as star tints. Clouds as faint constellation boundaries.",
        "fonts": "family=Cinzel:wght@600;700&family=Cormorant+Garamond:ital,wght@0,600;1,600;1,700",
        "theme": "dark",
        "all": """
  color-scheme:dark;
  --page:#0b1020; --ground:#0e1428; --block:#131a30; --quote:#1a2240;
  --ink:#e9e2cc; --ink-2:#b9b29c; --ink-3:#8a8572; --rule:#3a4260; --rule-soft:#252c45; --dash:#4a5270;
  --maroon:#d9c38a; --red:#d9c38a; --link:#e6cf8f; --visited:#bfa970; --pick:#fff4d0; --block-shadow:rgba(0,0,0,.6);
  --band:#101830; --band-edge:#060a16; --band-ink:#e8d9a8; --band-sub:#b9b29c;
  --t-scp:#d8d2bf; --t-tale:#5fc4d0; --t-goi:#e0a030; --t-joke:#e07cc0;
  --c-safe:#3fbf8a; --c-euclid:#ffd300; --c-keter:#ff4d6a; --c-neut:#8f95a8; --c-eso:#5fb4ff; --c-other:#3a4260;
  --none:#3a4260; --tag-line:#8a93b8; --page-line:#d9c38a;
  --region:#e8d9a8; --canon-label:#f4efe0; --goi-label:#b9c7e0;
  --font-head:"Cinzel",Georgia,serif; --font-label:"Cormorant Garamond",Georgia,serif;
  --clouds:#3b4a7a,#4a5a8a,#5a4a7a,#3a5a6a,#6a5a3a,#4a6a5a,#5a3a5a,#46467a;""",
    },
}


READING = {
    "order-line": {"title": "Line", "note": "A thin line joins the pages in the hub's order; the first page carries a ring.",
                   "fonts": "", "theme": None, "light": "--reading-order:line;", "dark": "--reading-order:line;"},
    "order-numbers": {"title": "Numbers", "note": "Each page shows its place in the hub's list above its dot.",
                      "fonts": "", "theme": None, "light": "--reading-order:num;", "dark": "--reading-order:num;"},
    "order-both": {"title": "Line and numbers", "note": "Both together.",
                   "fonts": "", "theme": None, "light": "--reading-order:line num;", "dark": "--reading-order:line num;"},
}
SERIES = "#h=u.antimemetics-division-hub"
if sys.argv[1:] == ["reading"]:
    VARIANTS = READING


def build(name, v):
    # inserted in <head>, before the page's own style, so each rule is one step more specific than the rule it replaces
    css = ""
    if v.get("light"):
        css += "html:root{" + v["light"] + "}\n"
    if v.get("dark"):
        css += '@media (prefers-color-scheme:dark){ :root:root:not([data-theme="light"]){' + v["dark"] + "}}\n"
        css += ':root:root[data-theme="dark"]{' + v["dark"] + "}\n"
    if v.get("all"):
        css += ":root:root:root:root{" + v["all"] + "}\n"
    head = ""
    if v["fonts"]:
        head += '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?' + v["fonts"] + '&display=swap">'
    head += "<style>\n" + css + "</style>"
    page = BASE.replace("</head>", head + "</head>", 1)
    if v["theme"]:
        page = page.replace("</body>", "<script>document.documentElement.setAttribute('data-theme','" + v["theme"] + "')</script></body>", 1)
    open(os.path.join(OUT, name + ".html"), "w", encoding="utf-8").write(page)


for name, v in VARIANTS.items():
    build(name, v)

reading = VARIANTS is READING
hash_ = SERIES if reading else ""
cells = [("current", "Current", "The map as published today" + (": the series is lit, with no order shown." if reading else "."), "../scp-constellation-map-standalone.html" + hash_)]
cells += [(n, v["title"], v["note"], n + ".html" + hash_) for n, v in VARIANTS.items()]
grid = "".join(
    '<section><header><b>{t}</b> <a href="{src}" target="_blank">open full screen ↗</a><p>{n}</p></header>'
    '<iframe src="{src}" loading="eager"></iframe></section>'.format(t=t, n=n, src=src) for _, t, n, src in cells)
open(os.path.join(OUT, "compare-reading.html" if reading else "compare.html"), "w", encoding="utf-8").write("""<!doctype html><html><head><meta charset="utf-8">
<title>""" + ("Reading order variants" if reading else "Colour variants") + """</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{color-scheme:light dark}
body{margin:0;font:13px system-ui,sans-serif;background:#2a2a2a;color:#eee}
main{display:grid;grid-template-columns:1fr 1fr;grid-auto-rows:calc(50vh - 4px);gap:8px;padding:0;height:100vh}
section{display:flex;flex-direction:column;min-height:0;background:#111}
header{padding:6px 10px}header p{margin:2px 0 0;color:#bbb;font-size:12px}header a{color:#9cf;margin-left:8px}
iframe{flex:1;border:0;width:100%;min-height:0;background:#fff}
@media (max-width:900px){main{grid-template-columns:1fr;grid-auto-rows:90vh;height:auto}}
</style></head><body><main>""" + grid + "</main></body></html>")
print("wrote", ", ".join(n + ".html" for n in VARIANTS), "and", "compare-reading.html" if reading else "compare.html", "in", OUT)
