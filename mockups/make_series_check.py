"""A checklist page for comparing extracted tale series with their hub on the wiki, by eye.

    python -X utf8 mockups/make_series_check.py <slug> <slug> ...      writes mockups/series_check.html
"""
import html, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
hubs = {r["slug"]: r for r in json.load(open(os.path.join(ROOT, "data", "hubs.json"), encoding="utf-8"))}
d = json.load(open(os.path.join(ROOT, "out", "data.json"), encoding="utf-8"))
title = {s.lower(): (d["title"][i] or s) for i, s in enumerate(d["slug"])}
name = {s.lower(): s for s in d["slug"]}
e = html.escape
parts = []
for s in sys.argv[1:]:
    r = hubs[s]
    secs = "".join("<h4>%s</h4><ol>%s</ol>" % (e(nm) or "<i>(no heading)</i>", "".join("<li>%s <span>%s</span></li>" % (e(title.get(p, p)), e(p)) for p in pages))
                   for nm, pages in r["sections"])
    parts.append("""<section><h2>%s</h2><p>%s · %s · <b>%d pages on the map</b> (the hub links %d pages that are on the map, and %d that are not)%s</p>
<p><a href="https://scp-wiki.wikidot.com/%s" target="_blank">Hub on the wiki ↗</a> · <a href="../scp-constellation-map-standalone.html#h=u.%s" target="_blank">Series on the map ↗</a></p>
<details><summary>Reading list as extracted</summary>%s</details>
<p class="q">Same pages? Same order? Same headings? Anything missing that should be there?</p></section>"""
                 % (e(r["title"]), e(r["author"]), e(r["date"]), r["n"], r["every"], r["off"], " · <i>read as prose</i>" if r["mode"] == "prose" else "", s, s, secs))
open(os.path.join(ROOT, "mockups", "series_check.html"), "w", encoding="utf-8").write("""<!doctype html><html><head><meta charset="utf-8"><title>Tale series check</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
:root{color-scheme:light dark}body{font:14px/1.5 system-ui,sans-serif;max-width:860px;margin:0 auto;padding:16px}
section{border:1px solid #8886;border-radius:8px;padding:4px 16px 12px;margin:16px 0}h2{margin:.6em 0 .2em}h4{margin:.8em 0 .2em}
ol{margin:0;padding-left:2em}li span{opacity:.55;font-size:12px;margin-left:6px}.q{font-style:italic;opacity:.8}summary{cursor:pointer}
</style></head><body><h1>Tale series: spot check</h1><p>For each series: open the hub on the wiki, open the reading list below, and compare.</p>"""
     + "".join(parts) + "</body></html>")
print("wrote mockups/series_check.html with", len(parts), "series")
