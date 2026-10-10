"""Gathers the pages that the source dataset lacks and that were read from the live wiki, into one file for build.py.

Usage: python3 -I make_extra.py <raw dataset dir> extra_pages.json

Three groups: the Lost SCP Series (lost_raw.txt, lost_titles.json), the SCP-001 proposals (p001_raw.txt, p001_list.txt)
and the joke entries (jokes/part_*.txt, jokes_list.json). A page already present in the dataset is skipped.
A joke page whose discussion thread could not be read gets a date estimated from the thread's number (thread numbers grow with time).
"""
import datetime, glob, json, re, sys

RAW, OUT = sys.argv[1], sys.argv[2]
have = set()
for kind in ("items", "tales", "goi"):
    for k, v in json.load(open(f"{RAW}/{kind}/index.json")).items():
        have.add(str(v.get("link", k)).lower())
out, skipped = [], []

def add(group, slug, pid, title, typ, rating, author, ym, tags, approx):
    if slug.lower() in have: skipped.append(slug); return
    have.add(slug.lower())
    if author.strip() in ("?", "", "name", "Unknown Author", "Uncertain"): author = "Unknown"
    out.append({"group": group, "slug": slug, "id": pid, "title": title, "type": typ, "rating": int(rating), "author": author.strip(),
                "ym": ym, "tags": tags.split(), "approx": bool(approx)})

# ---- Lost SCP Series: dates are last-edit months
titles = {r["slug"]: r for r in json.load(open("lost_titles.json"))}
for line in open("lost_raw.txt", encoding="utf-8"):
    slug, rating, author, ym, tags = line.rstrip("\n").split("|")
    if "scp" in tags.split():
        add("lost", slug, titles[slug]["id"], titles[slug]["title"], 0, rating, author, ym, tags, True)

# ---- SCP-001 proposals: dates are the opening of each discussion thread
raw = {l.split("|")[0]: l.rstrip("\n").split("|") for l in open("p001_raw.txt", encoding="utf-8") if l.strip()}
for l in open("p001_list.txt", encoding="utf-8"):
    if not l.strip(): continue
    slug, code, name = l.rstrip("\n").split("|")
    if slug in raw:
        _, rating, author, ym, tags = raw[slug]
        add("p001", slug, "SCP-001", name + " (CODE NAME: " + code + ")", 0, rating, author, ym, tags, False)

# ---- joke entries
MON = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
anchors = []
for l in open("p001_dates.txt"):
    t, d, m, y = l.split(); anchors.append((int(t), datetime.date(int(y), MON[m], int(d)).toordinal()))
anchors.sort()
def estimate(thread):
    for (t0, d0), (t1, d1) in zip(anchors, anchors[1:]):
        if t0 <= thread <= t1:
            d = datetime.date.fromordinal(round(d0 + (d1 - d0) * (thread - t0) / (t1 - t0))); return f"{d.year}-{d.month:02d}"
    (t0, d0), (t1, d1) = anchors[-2], anchors[-1]
    d = datetime.date.fromordinal(min(datetime.date(2026, 10, 9).toordinal(), round(d1 + (d1 - d0) * (thread - t1) / (t1 - t0)))); return f"{d.year}-{d.month:02d}"
threads = dict(l.split() for l in open("jokes/missing_threads.txt") if l.strip())
hub = {r[0]: r for r in json.load(open("jokes_list.json"))}
lines = [l.rstrip("\n") for f in sorted(glob.glob("jokes/part_*.txt")) for l in open(f, encoding="utf-8") if l.strip()]
lines.append("scp-1047-j|+60|TroyL|2022-10|_licensebox esoteric-class joke redirect scp")      # reads only with /noredirect/true
unread = []
for l in lines:
    slug, rating, author, ym, tags = l.split("|")
    ts = tags.split()
    if "joke" not in ts or not ("scp" in ts or "tale" in ts): continue                       # essays, guides and pages up for deletion
    if not re.match(r"^[+-]?\d+$", rating): unread.append(slug); continue
    approx = False
    if not re.match(r"^\d{4}-\d{2}$", ym):
        if slug not in threads: unread.append(slug); continue
        ym, approx = estimate(int(threads[slug])), True
    _, pid, title = hub.get(slug, (slug, slug.upper(), ""))
    if "tale" in ts and "scp" not in ts: typ, pid, title = 1, "", (pid if not title else pid + " - " + title)
    else:
        typ = 0
        if pid.startswith("CODENAME"): pid, title = "SCP-001-J", re.sub(r"^CODENAME:\s*", "", pid) + (": " + title.strip('"') if title else "")
        elif re.match(r"^[a-z0-9-]+$", pid): pid = pid.upper()
    add("joke", slug, pid, title, typ, rating, author, ym, tags, approx)
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=0)
import collections
print(collections.Counter(r["group"] for r in out), "| already in the dataset:", len(skipped), "| joke pages left out (rating or date unread):", unread)
print("estimated dates:", [(r["slug"], r["ym"]) for r in out if r["group"] == "joke" and r["approx"]])
