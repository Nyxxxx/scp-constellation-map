"""One command for every step of the project. Works the same on Windows, macOS and Linux.

    python make.py page     put the data into the page            (after editing page3.src.html)
    python make.py data     last data step, then the page         (after editing contests, GoI/canon notes or tale series)
    python make.py all      everything, layout included           (after changing tags, region names or the dataset; about 2 minutes)
    python make.py test     the automatic browser tests

"data" and "all" need the dataset: a copy of https://github.com/scp-data/scp-api, by default in the folder scp-api/ next to this file.
Options:  --raw PATH   where the dataset's docs/data/scp folder is      --snapshot YYYY-MM-DD   date of that copy (default 2026-10-09)

Every script is started with "-X utf8", so Windows reads and writes the files as UTF-8 like the other systems do.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
args = sys.argv[1:]


def opt(name, default):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default


RAW = opt("--raw", os.path.join("scp-api", "docs", "data", "scp"))
SNAPSHOT = opt("--snapshot", "2026-10-09")
step = args[0] if args else "page"


def run(script, *a):
    print(">", script, *a, flush=True)
    r = subprocess.run([sys.executable, "-X", "utf8", script, *a])
    if r.returncode: sys.exit("stopped: " + script + " failed")


def need_raw():
    if not os.path.exists(os.path.join(RAW, "items", "index.json")):
        sys.exit("The dataset was not found in " + RAW + ".\nGet the snapshot as described in README.md (a full git clone is about 16.6 GB),\nor pass its docs/data/scp folder with --raw.")


def page():
    os.makedirs("out", exist_ok=True); os.makedirs("site", exist_ok=True)
    run("assemble.py", "page3.src.html", os.path.join("out", "data.json"), os.path.join("site", "scp-constellation-map.html"))
    body = open(os.path.join("site", "scp-constellation-map.html"), encoding="utf-8").read()
    whole = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
             '<style>:root{color-scheme:light}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style></head><body>' + body + '</body></html>')
    for path in (os.path.join("out", "preview.html"), "scp-constellation-map-standalone.html"):
        open(path, "w", encoding="utf-8").write(whole)
    print("wrote scp-constellation-map-standalone.html (open it in a browser) and out/preview.html (used by the tests)")
    node = shutil.which("node")
    if node:   # optional: checks that the page's code has no syntax error
        check = "const s=require('fs').readFileSync('site/scp-constellation-map.html','utf8');const m=[...s.matchAll(/<script>([\\s\\S]*?)<\\/script>/g)].pop()[1];new Function(m);console.log('script parses')"
        if subprocess.run([node, "-e", check]).returncode: sys.exit("stopped: the page's code has a syntax error")


def data():
    need_raw()
    built = os.path.join("out", "data4.json")
    run("finalize.py", built, "lost_raw.txt", "lost_titles.json", os.path.join("out", "data.json"), "contests.json", "notes.json", "p001_raw.txt", "p001_list.txt", RAW)


if step == "page":
    page()
elif step == "data":
    data(); page()
elif step == "all":
    need_raw()
    hubs = os.path.join(RAW, "hubs", "index.json"); built = os.path.join("out", "data4.json")
    os.makedirs("out", exist_ok=True)
    run("make_extra.py", RAW, "extra_pages.json")
    run("make_contests.py", hubs, "contests_base.json", "contests.json")
    run("build.py", RAW, built, "region_names.json", SNAPSHOT, "extra_pages.json")
    run("make_notes.py", hubs, built, "notes.json")
    run("fetch_series.py", "series_hubs.json")   # the wiki's Series Archive and its hubs; pages already in raw_wiki/ are not fetched again
    run("make_hubs.py", RAW, built, "hubs.json", "series_hubs.json")
    data(); page()
elif step == "test":
    run("shot17.py"); run("shot18.py"); run("fuzz.py")
else:
    sys.exit(__doc__)
