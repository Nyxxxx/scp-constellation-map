"""One command for every step of the project. Works the same on Windows, macOS and Linux.

    python make.py page     put the data into the page            (after editing page3.src.html)
    python make.py data     last data step, then the page         (after editing contests, GoI/canon notes or tale series)
    python make.py all      everything, from the dataset           (after a new copy of the dataset, or changing tags or region names)
    python make.py test     the automatic browser tests
    python make.py preview  open this computer's copy of the map in the browser (also: double-click "Preview the map.bat")

"all" keeps the map: pages already on it stay where they are and keep their region, new pages are placed beside their closest pages.
"all --no-wiki" does the same without downloading the series hubs from the wiki (the tale series stay as in hubs.json).
"all --fresh" computes the layout and the regions anew (UMAP and Leiden; about 2 minutes): every dot moves and new regions need names.

"data" and "all" need the dataset: a copy of https://github.com/scp-data/scp-api, by default in the folder scp-api/ next to this file.
Options:  --raw PATH   where the dataset's docs/data/scp folder is      --snapshot YYYY-MM-DD   date of that copy (default: the date of its last commit)

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
SNAPSHOT = opt("--snapshot", "")
FRESH = "--fresh" in args
if FRESH: args.remove("--fresh")
NO_WIKI = "--no-wiki" in args     # do not download the series hubs from the wiki: hubs.json is kept as it is (the daily job)
if NO_WIKI: args.remove("--no-wiki")
step = args[0] if args else "page"


def snapshot_date():
    """The date of the dataset copy: given with --snapshot, or the date of the last commit of the dataset folder."""
    if SNAPSHOT: return SNAPSHOT
    git = shutil.which("git")
    r = subprocess.run([git, "-C", RAW, "log", "-1", "--format=%cs"], capture_output=True, text=True) if git else None
    if r and r.returncode == 0 and r.stdout.strip(): return r.stdout.strip()
    sys.exit("The date of the dataset copy could not be read: pass it with --snapshot YYYY-MM-DD.")


def run(script, *a):
    print(">", script, *a, flush=True)
    r = subprocess.run([sys.executable, "-X", "utf8", script, *a])
    if r.returncode: sys.exit("stopped: " + script + " failed")


def need_raw():
    if not os.path.exists(os.path.join(RAW, "items", "index.json")):
        sys.exit("The dataset was not found in " + RAW + ".\nGet the snapshot as described in README.md (a full git clone is about 16.6 GB),\nor pass its docs/data/scp folder with --raw.")


def S(name): return os.path.join("scripts", name)    # the build scripts
def D(name): return os.path.join("data", name)       # their inputs, and the lists they write
def T(name): return os.path.join("tests", name)      # the automatic tests


def page():
    os.makedirs("out", exist_ok=True); os.makedirs("site", exist_ok=True)
    run(S("assemble.py"), os.path.join("page", "page3.src.html"), os.path.join("out", "data.json"), os.path.join("site", "scp-constellation-map.html"))
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
    run(S("finalize.py"), built, D("lost_raw.txt"), D("lost_titles.json"), os.path.join("out", "data.json"), D("contests.json"), D("notes.json"),
        D("p001_raw.txt"), D("p001_list.txt"), RAW)


if step == "page":
    page()
elif step == "data":
    data(); page()
elif step == "all":
    need_raw()
    hubs = os.path.join(RAW, "hubs", "index.json"); built = os.path.join("out", "data4.json")
    os.makedirs("out", exist_ok=True)
    run(S("make_extra.py"), RAW, D("extra_pages.json"))
    run(S("make_contests.py"), hubs, D("contests_base.json"), D("contests.json"))
    keep = []
    if not FRESH and os.path.exists(built):     # the previous build is the starting point of the new one
        prev = os.path.join("out", "data4.prev.json"); shutil.copyfile(built, prev); keep = ["--prev", prev]
    run(S("build.py"), RAW, built, D("region_names.json"), snapshot_date(), D("extra_pages.json"), *keep)
    run(S("make_notes.py"), hubs, built, D("notes.json"))
    if not NO_WIKI:
        run(S("fetch_series.py"), D("series_hubs.json"))   # the wiki's Series Archive and its hubs; pages already in raw_wiki/ are not fetched again
        run(S("make_hubs.py"), RAW, built, D("hubs.json"), D("series_hubs.json"))
    data(); page()
elif step == "test":
    run(T("shot17.py")); run(T("shot18.py")); run(T("fuzz.py"))
elif step == "preview":
    # a small web server for this folder, on this computer only, and the map opened in the default browser
    import functools, http.server, socket, webbrowser
    port = 8765
    with socket.socket() as s_:
        busy = s_.connect_ex(("127.0.0.1", port)) == 0     # already running (another window, or the Claude app)
    url = "http://localhost:%d/scp-constellation-map-standalone.html" % port
    webbrowser.open(url)
    if busy:
        print("The preview server is already running. Opened", url)
    else:
        print("Map opened at", url, "\nKeep this window open while you look at the map; close it to stop.")
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
        http.server.ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()
else:
    sys.exit(__doc__)
