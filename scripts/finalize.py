"""Last step of the data build.

Usage: python3 -I finalize.py <built json> <lost_raw.txt> <lost_titles.json> <out json> [contests.json] [notes.json] [p001_raw.txt p001_list.txt] [raw dataset dir]

1. Keeps only the default layout (the shape sliders were dropped) and drops the character/theme landmarks.
2. Records which pages were read from the live wiki (build.py already placed them): the Lost SCP Series and the list of SCP-001 proposals
   in the order of the wiki's SCP-001 page.
3. Attaches the hand-written contest notes (name, dates, description, winner, link to the contest page).
"""
import collections
import json
import os
import math
import re
import sys

import numpy as np
import scipy.sparse as sp

d = json.load(open(sys.argv[1]))
HUBS_ON_WIKI = 270     # the wiki's Series Hub listed 23 pages of 12 series on the day of the snapshot (between 265 and 276)
titles = {r["slug"]: r for r in json.load(open(sys.argv[3]))}

# ---- 1. one layout, no character/theme landmarks
LN = len(d["meta"]["links"])
k = d["meta"]["defaultGather"] * LN
P, LA = d["P"][k], d["LA"][k]
keep = [i for i, l in enumerate(d["landmarks"]) if l["kind"] != 0]
d["P"], d["CA"] = [P], [d["CA"][k]]
d["landmarks"] = [d["landmarks"][i] for i in keep]
d["LA"] = [[v for i in keep for v in LA[2 * i:2 * i + 2]]]
d["meta"].update(gather=[d["meta"]["gather"][d["meta"]["defaultGather"]]], links=[0.0], defaultGather=0)

# ---- 2. pages read from the live wiki: bookkeeping only (build.py gave them their place like any other page)
tags, used, df = d["tags"], d["tagUsed"], d["tagDf"]
tag_idx = {t: i for i, t in enumerate(tags)}
CLASS_KEYS = ["safe", "euclid", "keter", "neutralized", "pending", "thaumiel", "apollyon", "archon", "ticonderoga", "cernunnos",
              "uncontained", "hiemal", "tiamat", "esoteric-other", "explained", "decommissioned", "none"]
name_idx = {n: i for i, n in enumerate(d["names"])}


def intern(table, index, s):
    if s not in index:
        index[s] = len(table); table.append(s)
    return index[s]


SN = d["seriesNames"]
LOST, S001 = SN.index("Lost SCP Series (L000 to L999)"), SN.index("SCP-001 proposals")
slug_idx = {sl.lower(): i for i, sl in enumerate(d["slug"])}
added, skipped = [], []
for line in open(sys.argv[2], encoding="utf-8"):
    slug, _, _, _, taglist = line.rstrip("\n").split("|")
    (added if "scp" in taglist.split() and slug in slug_idx else skipped).append(slug)      # admin and hub pages sit in some of the series' slots
p001 = []
if len(sys.argv) > 8:
    for l in open(sys.argv[8], encoding="utf-8"):
        if not l.strip(): continue
        slug, code, name = l.rstrip("\n").split("|")
        if slug not in slug_idx:
            print("proposal not on the map:", slug); continue
        n = slug_idx[slug]
        if d["series"][n] == S001 and "CODE NAME" not in d["title"][n]: d["title"][n] = name + " (CODE NAME: " + code + ")"
        p001.append({"n": n, "code": code, "name": name})
    d["p001"] = p001
    print("SCP-001 proposals listed:", len(p001), "| on the ring:", [d["slug"][e["n"]] for e in p001 if d["placed"][e["n"]] == 2])

# ---- 3. contests: real names, dates, links, and the wiki's own descriptions and winners, keyed by tag
if len(sys.argv) > 5:
    notes = json.load(open(sys.argv[5]))
    out, unknown = {}, []
    for t, c in notes["contests"].items():
        if t not in tag_idx:
            unknown.append(t); continue
        ti = tag_idx[t]
        d["tagKind"][ti] = 3
        d["tagName"][ti] = c["name"]
        out[str(ti)] = {"d": c["d"], "when": c["when"], "url": c["url"], "desc": c["desc"], "win": c["win"], "mine": 1 if c["mine"] else 0}
    # unofficial contests are not listed: their tags go back to being plain tags, shown under their own spelling
    for t in notes["housekeeping"]:
        if t in tag_idx:
            d["tagKind"][tag_idx[t]] = 0
            d["tagName"][tag_idx[t]] = t
    d["contests"] = out
    bare = [tags[i] for i in range(len(tags)) if d["tagKind"][i] == 3 and str(i) not in out]
    print("contests:", len(out), "| tags not in data:", unknown, "| contest tags without a note:", bare)
    print("housekeeping:", [(t, "still used for links" if d["tagUsed"][tag_idx[t]] else "ignored") for t in notes["housekeeping"] if t in tag_idx])

# ---- 4. the wiki's own descriptions of Groups of Interest and canons, keyed by tag
if len(sys.argv) > 6:
    wn = json.load(open(sys.argv[6]))
    d["notes"] = {str(tag_idx[t]): {"k": 2 if v["kind"] == "goi" else 1, "p": v["p"], "num": v["num"], "alt": v.get("alt", ""), "url": v["url"], "hub": v["hub"]} for t, v in wn.items() if t in tag_idx}
    # groups that the wiki's Groups of Interest page lists but that the build did not recognise as GoIs, and names that are acronyms
    GOI_NAMES = {"scarlet-king": "Children of the Scarlet King", "goldbaker-reinz": "Goldbaker-Reinz", "greazeburger": "Greazeburger", "just-girly-things": "Just Girly Things",
                 "mages-academy": "Mages Academy", "oria": "ORIA", "madao": "MADAO", "joicl": "JOICL", "sapphire": "SAPPHIRE"}
    for t, nm in GOI_NAMES.items():
        if t in tag_idx and (t in wn or d["tagKind"][tag_idx[t]] == 2):
            d["tagKind"][tag_idx[t]] = 2; d["tagName"][tag_idx[t]] = nm
    print("descriptions:", len(d["notes"]), "| GoI or canon tags without one:", sorted(tags[i] for i in range(len(tags)) if d["tagKind"][i] in (1, 2) and str(i) not in d["notes"]))

# ---- 5. repairs found by an audit of the data
import html as _html
fixed = collections.Counter()
NALL = len(d["type"])
# 5a. the series follows the entry's number or suffix, not its tags (a plain-numbered entry tagged "explained" belongs to its numbered series)
SN = d["seriesNames"]; S_EX, S_D, S_J, S_INT, S_001 = SN.index("Explained (-EX)"), SN.index("Decommissioned (-D)"), SN.index("Joke entries (-J)"), SN.index("International"), SN.index("SCP-001 proposals")
for n in range(NALL):
    if d["type"][n] != 0 or d["series"][n] in (LOST, S_001): continue
    pid = d["id"][n]; m = re.match(r"^SCP-(\d+)$", pid); new = d["series"][n]
    if m and 1 < int(m.group(1)) < 10000: new = int(m.group(1)) // 1000
    elif re.match(r"^SCP-\d+-EX$", pid): new = S_EX
    elif re.match(r"^SCP-\d+-D$", pid): new = S_D
    elif re.match(r"^SCP-\d+-J$", pid): new = S_J
    elif re.match(r"^SCP-\d+-[A-Z]+$", pid): new = S_INT
    if new != d["series"][n]: d["series"][n] = new; fixed["series"] += 1
# 5b. titles: empty ones, stray spaces and cut-off ones are re-read from the series hubs (SCP entries) and the raw index (tales, GoI formats)
ZW = re.compile("[\u200b\u200c\u200d\ufeff]")
if len(sys.argv) > 9:
    RAW = sys.argv[9]
    hubs = json.load(open(RAW + "/hubs/index.json"))
    def plain(x):
        x = re.sub(r'<sup class="footnoteref">.*?</sup>', "", x, flags=re.S)      # footnote markers are not part of a title
        x = x.replace('<span class="rt">', " ").replace("<br>", " ").replace("<br />", " ")
        return re.sub(r"\s+", " ", ZW.sub("", _html.unescape(re.sub(r"<[^>]+>", "", x)))).strip()
    by_slug, by_id = {}, {}
    for hk in ["scp-international", "scp-ex", "joke-scps", "archived-scps", "scp-series"] + ["scp-series-%d" % i for i in range(2, 11)]:   # later hubs win: the numbered series last
        for li in re.findall(r"<li>(.*?)</li>", hubs.get(hk, {}).get("raw_content", ""), flags=re.S):
            a = re.search(r'<a[^>]*href="/([^"#]+)"[^>]*>(.*?)</a>', li, flags=re.S)
            if not a: continue
            link, whole = plain(a.group(2)), plain(li)
            mm = re.match(r"^(SCP-[\w-]+)\s+[-\u2013\u2014]\s+(.+)$", whole)
            if mm: title = mm.group(2)
            elif re.match(r"^SCP-[\w-]+\s*[-\u2013\u2014]?\s*$", whole): continue        # the hub gives no title
            elif whole == link + " - " + link: title = link                             # Taboo
            else: title = whole                                                         # the whole line is the title (Alleyway, "SCP-7992 is a Gorilla")
            by_slug[a.group(1).lower()] = title
            if re.match(r"^SCP-[\w-]+$", link): by_id[link] = title
    sq = lambda x: re.sub(r"\s+", "", x)
    for n in range(NALL):
        if d["type"][n] != 0: continue
        new = by_slug.get(d["slug"][n].lower()) or by_slug.get(d["id"][n].lower()) or by_id.get(d["id"][n])
        old = d["title"][n]
        if not new or new == old: continue
        if not old: d["title"][n] = new; fixed["title filled"] += 1
        elif sq(old) == sq(new) and not (re.search(r"\w\(", new) and not re.search(r"\w\(", old)): d["title"][n] = new; fixed["title spacing"] += 1
        elif len(old) == 90 and new.startswith(old.rstrip()): d["title"][n] = new; fixed["title uncut"] += 1
        elif re.sub(r"\s*\d+$", "", old) == new: d["title"][n] = new; fixed["title footnote mark"] += 1
    full = {}
    for kind in ("tales", "goi"):
        for k2, v in json.load(open(RAW + "/" + kind + "/index.json")).items():
            full[str(v.get("link", k2)).lower()] = re.sub(r"\s+-\s+SCP Foundation\s*$", "", v.get("title") or "").strip()
    for n in range(NALL):
        if d["type"][n] != 0 and len(d["title"][n]) == 90:
            new = full.get(d["slug"][n].lower(), "")
            if len(new) > 90 and new.startswith(d["title"][n].rstrip()): d["title"][n] = new; fixed["title uncut"] += 1
for n in range(NALL):
    if ZW.search(d["title"][n]): d["title"][n] = ZW.sub("", d["title"][n]).strip(); fixed["zero-width"] += 1
# 5c. authors: the dataset writes "deleted" for removed accounts
for i, a in enumerate(d["authors"]):
    if a == "deleted": d["authors"][i] = "(deleted account)"
# 5d. object classes: struck-through text in the class line is dropped; the Argus class is recognised from its tag
for i, nm in enumerate(d["names"]):
    if "--" in nm:
        parts = [p.strip() for p in re.sub(r"--[^-]*--", "", nm).split("/")]
        parts = [p for j, p in enumerate(parts) if p and p not in parts[:j]]
        d["names"][i] = " / ".join(parts) or nm; fixed["class text"] += 1
if "argus" in tag_idx:
    NONE, OTHER = CLASS_KEYS.index("none"), CLASS_KEYS.index("esoteric-other")
    for n in range(NALL):
        if d["type"][n] == 0 and d["ck"][n] == NONE and tag_idx["argus"] in d["tg"][n]:
            d["ck"][n] = OTHER; d["cn"][n] = intern(d["names"], name_idx, "Argus"); fixed["argus"] += 1
# 5e. landmark counts follow the tag counts, and their labels the display names of the tags (ORIA, MADAO)
for lm in d["landmarks"]: lm["n"] = d["tagDf"][lm["t"]]; lm["label"] = d["tagName"][lm["t"]]
# 5f. pages with identical tags were given identical positions and hid one another: each stack is opened into a small spiral, best rated in the middle
stacks = collections.defaultdict(list)
PP = d["P"][0]
for n in range(NALL):
    if d["placed"][n] != 2: stacks[(PP[2 * n], PP[2 * n + 1])].append(n)
for (x, y), mem in stacks.items():
    if len(mem) < 2: continue
    mem.sort(key=lambda n: -d["rating"][n])
    for i, n in enumerate(mem):
        r, th = 2.0 * math.sqrt(i), i * 2.399963
        PP[2 * n], PP[2 * n + 1] = int(round(x + r * math.cos(th))), int(round(y + r * math.sin(th)))
    fixed["unstacked pages"] += len(mem)
print("repairs:", dict(fixed))

# 5g. SCP-7537 has no title of its own: the Series 8 list shows it as "SCP-XXXX", which is copied here
if "scp-7537" in slug_idx and not d["title"][slug_idx["scp-7537"]].strip():
    d["title"][slug_idx["scp-7537"]] = "SCP-XXXX"; fixed["title from the series list"] += 1
print("repairs (end):", dict(fixed))

# ---- 6. tale series: the reading lists extracted from the series hubs (make_hubs.py), with the canons and GoIs their hub page is tagged with
if os.path.exists("data/hubs.json"):
    hl, hubs_read = [], json.load(open("data/hubs.json"))
    d["meta"]["hubsRead"] = len(hubs_read)
    d["meta"]["hubsFromWiki"] = sum(1 for r in hubs_read if r.get("src") == "wiki")
    d["meta"]["hubsManual"] = [r["title"] for r in hubs_read if r.get("mode") == "manual"]
    for r in hubs_read:
        secs = [[nm, [slug_idx[p] for p in pages if p in slug_idx]] for nm, pages in r["sections"]]
        secs = [sc for sc in secs if sc[1]]
        if sum(len(sc[1]) for sc in secs) < 2: continue
        hl.append({"s": r["slug"], "t": r["title"], "d": r["date"], "a": "(deleted account)" if r["author"] == "deleted" else r["author"], "b": r["blurb"],
                   "k": [tag_idx[t] for t in r["canons"] + r["gois"] if t in tag_idx], "q": secs, "off": r["off"]})
    d["hubs"] = hl
    # how many series the wiki's Series Archive lists, counted when it was downloaded (fetch_series.py); the estimate otherwise
    sh = json.load(open("data/series_hubs.json", encoding="utf-8")) if os.path.exists("data/series_hubs.json") else {}
    d["meta"]["hubsListed"] = len(sh) or HUBS_ON_WIKI
    d["meta"]["hubsFetched"] = max((v.get("fetched_at", "") for v in sh.values()), default="")
    print("tale series:", len(hl), "| pages in at least one:", len({n for x in hl for sc in x["q"] for n in sc[1]}))

# ---- 7. the map through time (build_history.py): one layout per date, for the timeline animation.
# For each frame, the positions of the pages written by then, in page order (the page knows which ones from their month);
# -32768 where the page has no position in that frame (a page newer than the frames, or one that changed date).
if os.path.exists("data/history.json"):
    import base64
    import numpy as np
    hj = json.load(open("data/history.json", encoding="utf-8"))
    hidx = {s.lower(): i for i, s in enumerate(hj["slugs"])}
    cur = [hidx.get(s.lower(), -1) for s in d["slug"]]
    frames = []
    for k, c in enumerate(hj["cutoffs"]):
        a = np.frombuffer(base64.b64decode(hj["pos"][k]), dtype="<i2").reshape(-1, 2)
        out_ = [a[j] if j >= 0 else (-32768, -32768) for n, j in enumerate(cur) if d["mo"][n] <= c]
        frames.append(base64.b64encode(np.array(out_, dtype="<i2").reshape(-1, 2).tobytes()).decode())
    d["H"] = {"c": hj["cutoffs"], "p": frames}
    print("map through time:", len(frames), "frames,", sum(len(f) for f in frames) // 1024, "KB")

# ---- 8. the opening of the timeline: the pages of the first year in the order they were created (to the minute, from the dataset),
# SCP-173 first, so the animation can let them appear one by one around it
if len(sys.argv) > 9 and "H" in d:
    when = {}
    for kind in ("items", "tales", "goi"):
        for k2, v in json.load(open(RAW + "/" + kind + "/index.json")).items():
            when[str(v.get("link", k2)).lower()] = v.get("created_at") or ""
    y1 = d["H"]["c"][0]          # the first frame: the end of the first year
    first = [n for n in range(NALL) if d["mo"][n] <= y1]
    first.sort(key=lambda n: (d["slug"][n].lower() != "scp-173", when.get(d["slug"][n].lower()) or "9999", n))
    d["H"]["first"] = first
    print("timeline opening:", len(first), "pages of the first year, starting with", [d["id"][n] or d["title"][n] for n in first[:6]])

missing = sorted(set(titles) - set(added) - set(skipped))
# joke entries: how many dates are estimates, and how many pages linked from the Joke SCPs hub did not make it onto the map
jl = json.load(open("data/jokes_list.json")) if os.path.exists("data/jokes_list.json") else []
d["meta"].update(n=len(d["type"]), lostSeries=LOST, lostMissing=[s_.upper() for s_ in missing],
                 jokesApprox=sum(1 for n in d.get("approx", []) if d["series"][n] != LOST),
                 jokesMissing=sum(1 for r in jl if r[0].lower() not in slug_idx and re.match(r"^scp-.+-j$", r[0].lower())))   # the hub also links essays, themes and collections, which are not entries
json.dump(d, open(sys.argv[4], "w"), ensure_ascii=False, separators=(",", ":"))
print(f"lost series: {len(added)} on the map, not articles {skipped}, could not be read {missing}")
print("pages", len(d["type"]), "regions", len(d["clusters"]), "landmarks", len(d["landmarks"]), "| read from the live wiki:", d["meta"]["lost"], d["meta"]["p001Added"], d["meta"]["jokesAdded"])
