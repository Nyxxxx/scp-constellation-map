"""Downloads the wiki's Series Archive and every series hub it lists, and writes them in the dataset's hub format.

Usage: python -X utf8 fetch_series.py series_hubs.json

Polite: one request per second at most. Every downloaded page is kept in raw_wiki/ and never fetched again
(delete a file to fetch it anew), so the extraction can be re-run offline.
    raw_wiki/series-archive/p<N>.html   the 23 pages of https://scp-wiki.wikidot.com/series-archive
    raw_wiki/hubs/<slug>.html            each hub page
Output: {slug: {title, creator, created_at, tags, raw_content, url, archive_order}}, the fields make_hubs.py reads.
"""
import datetime, json, os, re, sys, time, urllib.request
from bs4 import BeautifulSoup

OUT = sys.argv[1]
SITE = "https://scp-wiki.wikidot.com"
RAW = "raw_wiki"
last = [0.0]


def get(url, path):
    if os.path.exists(path):
        return open(path, encoding="utf-8").read()
    wait = 1.0 - (time.time() - last[0])
    if wait > 0: time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": "scp-constellation-map (https://github.com/Nyxxxx/scp-constellation-map)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                text = r.read().decode("utf-8", "replace")
            break
        except Exception as e:
            print("   retry", url, e, flush=True); time.sleep(5 * (attempt + 1))
    else:
        raise SystemExit("could not download " + url)
    last[0] = time.time()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)
    return text


# 1. the archive: every series block gives the hub's address, title, creation time and creator
first = get(SITE + "/series-archive", os.path.join(RAW, "series-archive", "p1.html"))
pages = int(re.search(r"page 1 of (\d+)", first).group(1))
listed = {}
for p in range(1, pages + 1):
    html = first if p == 1 else get(SITE + "/series-archive/p/%d" % p, os.path.join(RAW, "series-archive", "p%d.html" % p))
    soup = BeautifulSoup(html, "lxml")
    for blk in soup.select("#page-content div.series-block"):
        a = blk.select_one("div.title a")
        if not a or not (a.get("href") or "").startswith("/"): continue
        slug = a["href"].strip("/").lower()
        when = blk.select_one("div.metadata span.odate")
        ts = re.search(r"time_(\d+)", " ".join(when.get("class", []))) if when else None
        who = blk.select_one("div.footer span.printuser")
        if slug not in listed:
            listed[slug] = {"title": a.get_text(" ", strip=True), "archive_order": len(listed),
                            "created_at": datetime.datetime.fromtimestamp(int(ts.group(1)), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") if ts else "",
                            "creator": who.get_text(" ", strip=True) if who else ""}
print(len(listed), "series listed on", pages, "archive pages", flush=True)

# 2. each hub page: its tags and the body of the page
out = {}
for i, (slug, v) in enumerate(listed.items()):
    path = os.path.join(RAW, "hubs", slug + ".html")
    fresh = not os.path.exists(path)
    html = get(SITE + "/" + slug, path)
    soup = BeautifulSoup(html, "lxml")
    body = soup.find(id="page-content")
    tags = [t.get_text(strip=True) for t in soup.select("div.page-tags a")]
    fetched = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")
    out[slug] = dict(v, url=SITE + "/" + slug, tags=tags, fetched_at=fetched, raw_content=str(body) if body else "")
    if fresh and (i + 1) % 20 == 0: print("  ", i + 1, "of", len(listed), flush=True)
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("wrote", OUT, "with", len(out), "hubs;", sum(1 for v in out.values() if "series-hub" in v["tags"]), "tagged series-hub;",
      sum(1 for v in out.values() if not v["raw_content"]), "without a page body")
