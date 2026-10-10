"""Last step of the data build.

Usage: python3 -I finalize.py <built json> <lost_raw.txt> <lost_titles.json> <out json> [contests.json] [notes.json] [p001_raw.txt p001_list.txt] [raw dataset dir]

1. Keeps only the default layout (the shape sliders were dropped) and drops the character/theme landmarks.
2. Adds the Lost SCP Series entries, which the dataset does not carry. Their tags, rating and author were read
   from the wiki pages themselves. Each one is placed beside its closest tag matches in the existing map,
   so no existing page moves.
   The SCP-001 proposals are added the same way: the dataset files every proposal under the one key "SCP-001", so it keeps only one of them.
3. Attaches the hand-written contest notes (name, dates, description, winner, link to the contest page).
"""
import collections
import json
import math
import re
import sys

import numpy as np
import scipy.sparse as sp

d = json.load(open(sys.argv[1]))
titles = {r["slug"]: r for r in json.load(open(sys.argv[3]))}
N0 = len(d["type"])

# ---- 1. one layout, no character/theme landmarks
LN = len(d["meta"]["links"])
k = d["meta"]["defaultGather"] * LN
P, LA = d["P"][k], d["LA"][k]
keep = [i for i, l in enumerate(d["landmarks"]) if l["kind"] != 0]
d["P"], d["CA"] = [P], [d["CA"][k]]
d["landmarks"] = [d["landmarks"][i] for i in keep]
d["LA"] = [[v for i in keep for v in LA[2 * i:2 * i + 2]]]
d["meta"].update(gather=[d["meta"]["gather"][d["meta"]["defaultGather"]]], links=[0.0], defaultGather=0)

# ---- 2. Lost SCP Series
tags, used, df = d["tags"], d["tagUsed"], d["tagDf"]
tag_idx = {t: i for i, t in enumerate(tags)}
T0 = len(tags)
idf = np.array([math.log(N0 / df[i]) if used[i] else 0.0 for i in range(T0)])
rows, cols, vals = [], [], []
for i, ts in enumerate(d["tg"]):
    for t in ts:
        if used[t]:
            rows.append(i); cols.append(t); vals.append(idf[t])
X = sp.csr_matrix((vals, (rows, cols)), shape=(N0, T0))
norm = np.sqrt(X.multiply(X).sum(axis=1)).A1
norm[norm == 0] = 1.0
X = (sp.diags(1.0 / norm) @ X).tocsr()

CLASS_KEYS = ["safe", "euclid", "keter", "neutralized", "pending", "thaumiel", "apollyon", "archon", "ticonderoga", "cernunnos",
              "uncontained", "hiemal", "tiamat", "esoteric-other", "explained", "decommissioned", "none"]
ESO_TAGS = ["thaumiel", "apollyon", "archon", "ticonderoga", "cernunnos"]
MAIN_ORDER = ["explained", "decommissioned", "neutralized", "pending", "keter", "euclid", "safe"]
CLASS_TAGS = set(MAIN_ORDER + ESO_TAGS + ["esoteric-class"])
TYPE_TAGS = {"scp", "tale", "goi-format"}
name_idx = {n: i for i, n in enumerate(d["names"])}
author_idx = {a: i for i, a in enumerate(d["authors"])}


def intern(table, index, s):
    if s not in index:
        index[s] = len(table); table.append(s)
    return index[s]


LOST = len(d["seriesNames"])
d["seriesNames"].append("Lost SCP Series (L000 to L999)")
rng = np.random.RandomState(7)
base = np.array(P, dtype=float).reshape(-1, 2)
added, skipped, approx, no_tags = [], [], [], []
author_low = {a.lower(): a for a in d["authors"]}


def add_page(slug, rating, author, last, taglist, pid, title, series):
    """Append one page read from the wiki: placed beside its closest tag matches, or on the outer ring without a usable tag."""
    pt = taglist.split()
    content = [t for t in pt if not t.startswith("_") and t not in TYPE_TAGS and t not in CLASS_TAGS]
    tg = []
    for t in content:
        if t not in tag_idx:
            tag_idx[t] = len(tags); tags.append(t); used.append(0); df.append(0)
            d["tagName"].append(" ".join(w[:1].upper() + w[1:] for w in t.split("-"))); d["tagKind"].append(0)
        tg.append(tag_idx[t]); df[tag_idx[t]] += 1
    tg = sorted(set(tg))
    v = np.zeros(T0)
    for t in tg:
        if t < T0 and used[t]:
            v[t] = idf[t]
    n = len(d["type"])
    nb, nbs, cl = [], [], -1
    if v.any():
        sims = X @ (v / np.linalg.norm(v))
        top = np.argsort(-sims)[:10]
        top = [int(j) for j in top if sims[j] > 0.05]
        nb, nbs = top, [int(round(float(sims[j]) * 100)) for j in top]
        w = np.array([sims[j] for j in top[:5]])
        ang, rr = rng.uniform(0, 2 * math.pi), rng.uniform(5, 12)
        xy = (base[top[:5]] * w[:, None]).sum(axis=0) / w.sum() + (rr * math.cos(ang), rr * math.sin(ang))
        votes = collections.Counter(d["cluster"][j] for j in top[:8] if d["cluster"][j] >= 0)
        if votes:
            cl = votes.most_common(1)[0][0]; d["clusters"][cl]["n"] += 1
        placed = 0
    else:
        no_tags.append(slug)
        ang = rng.uniform(0, 2 * math.pi); xy = (1085 * math.cos(ang), 1085 * math.sin(ang)); placed = 2
    st = set(pt)
    eso = next((c for c in ESO_TAGS if c in st), None)
    main = next((c for c in MAIN_ORDER if c in st), None)
    if eso or "esoteric-class" in st:
        ck = CLASS_KEYS.index(eso or "esoteric-other")
        b = main if main in ("safe", "euclid", "keter") else None
        disp = ((b.capitalize() + " / " if b else "") + eso.capitalize()) if eso else "Esoteric (unnamed)"
    elif main:
        ck, disp = CLASS_KEYS.index(main), main.capitalize()
    else:
        ck, disp = CLASS_KEYS.index("none"), "None listed"
    y, m = last.split("-")
    d["type"].append(0); d["id"].append(pid); d["title"].append(title); d["slug"].append(slug)
    d["rating"].append(int(rating)); d["wc"].append(0); d["mo"].append((int(y) - 2008) * 12 + int(m) - 1)
    author = "Unknown" if author == "?" else author_low.get(author.lower(), author)
    d["author"].append(intern(d["authors"], author_idx, author))
    d["ck"].append(ck); d["cn"].append(intern(d["names"], name_idx, disp)); d["lvl"].append(0); d["dis"].append(0); d["risk"].append(0)
    d["series"].append(series); d["cluster"].append(cl); d["placed"].append(placed); d["tg"].append(tg); d["nb"].append(nb); d["nbs"].append(nbs)
    d["P"][0] += [int(round(xy[0])), int(round(xy[1]))]
    return n


for line in open(sys.argv[2], encoding="utf-8"):
    slug, rating, author, last, taglist = line.rstrip("\n").split("|")
    if "scp" not in taglist.split():
        skipped.append(slug); continue           # admin and hub pages that sit in the series' slots
    approx.append(add_page(slug, rating, author, last, taglist, titles[slug]["id"], titles[slug]["title"], LOST)); added.append(slug)
N1 = len(d["type"])

# ---- 2b. SCP-001 proposals, in the order of the wiki's SCP-001 page
p001 = []
if len(sys.argv) > 8:
    S001 = d["seriesNames"].index("SCP-001 proposals")
    raw = {l.split("|")[0]: l.rstrip("\n").split("|") for l in open(sys.argv[7], encoding="utf-8") if l.strip()}
    slug_idx = {sl: i for i, sl in enumerate(d["slug"])}
    for l in open(sys.argv[8], encoding="utf-8"):
        if not l.strip(): continue
        slug, code, name = l.rstrip("\n").split("|")
        if slug in slug_idx:                      # already in the dataset (one proposal, plus two filed as a tale and as an -EX entry)
            n = slug_idx[slug]
            if d["series"][n] == S001: d["title"][n] = name + " (CODE NAME: " + code + ")"
        elif slug in raw:
            _, rating, author, ym, taglist = raw[slug]
            n = add_page(slug, rating, author, ym, taglist, "SCP-001", name + " (CODE NAME: " + code + ")", S001)
        else:
            print("proposal not read:", slug); continue
        p001.append({"n": n, "code": code, "name": name})
    d["p001"] = p001
    print("SCP-001 proposals listed:", len(p001), "| added from the wiki:", len(d["type"]) - N1, "| on the ring:", [d["slug"][n] for n in range(N1, len(d["type"])) if d["placed"][n] == 2])
    print("  regions:", collections.Counter(d["clusters"][c]["label"] if c >= 0 else "none" for c in d["cluster"][N1:]).most_common(6))


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
# 5e. landmark counts follow the tag counts
for lm in d["landmarks"]: lm["n"] = d["tagDf"][lm["t"]]
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

missing = sorted(set(titles) - set(added) - set(skipped))
d["approx"] = approx
d["meta"]["loose"] += sum(1 for n in range(N0, len(d["type"])) if d["placed"][n] == 2)
d["meta"].update(n=len(d["type"]), scp=d["meta"]["scp"] + len(d["type"]) - N0, p001Added=len(d["type"]) - N1, lostSeries=LOST, lost=len(added), lostMissing=[s.upper() for s in missing])
json.dump(d, open(sys.argv[4], "w"), ensure_ascii=False, separators=(",", ":"))
print(f"lost series: added {len(added)}, not articles {skipped}, could not be read {missing}, without a usable tag {no_tags}")
print("new tags:", tags[T0:])
print("regions they landed in:", collections.Counter(d["clusters"][c]["label"] if c >= 0 else "none" for c in d["cluster"][N0:N1]).most_common(8))
i = d["slug"].index("scp-l026")
print("SCP-L026:", d["title"][i], "| class", d["names"][d["cn"][i]], "| closest:", [(d["id"][j] or d["title"][j][:24], s) for j, s in zip(d["nb"][i][:5], d["nbs"][i][:5])])
print("pages", len(d["type"]), "landmarks", len(d["landmarks"]), "layouts", len(d["P"]))
