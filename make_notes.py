"""Collects the wiki's own descriptions of Groups of Interest and canons.

Usage: python3 -I make_notes.py <hubs/index.json> <built json> notes.json

Groups of Interest come from the "Groups of Interest" page: each group's Overview paragraphs, word for word, keyed by the tag the page itself names.
Canons come from the "Canon Hub" page: each canon's blurb, word for word, matched to its tag by name (CANON_TAG fixes the names that differ).
"""
import html, json, re, sys

hubs = json.load(open(sys.argv[1]))
d = json.load(open(sys.argv[2]))
WIKI = "https://scp-wiki.wikidot.com"

def clean(x):
    x = re.sub(r"<br\s*/?>", " ", x); x = re.sub(r"<sup class=\"footnoteref\">.*?</sup>", "", x, flags=re.S)
    x = re.sub(r"<[^>]+>", "", x); x = html.unescape(x); return re.sub(r"\s+", " ", x).strip()
def paras(block):
    return [t for t in (clean(p) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", block, flags=re.S)) if t]

out, report = {}, {"goi_no_tag": [], "canon_unmatched": [], "goi": 0, "canon": 0}

# ---- Groups of Interest
rc = hubs["groups-of-interest"]["raw_content"]
parts = re.split(r'<p><a name="([^"]+)"></a></p>', rc)
for anchor, body in zip(parts[1::2], parts[2::2]):
    h = re.search(r"<h1[^>]*><span>(.*?)</span></h1>", body, flags=re.S)
    tg = re.search(r"tagged with <em>([^<]+)</em>", body)
    if not h or not tg:
        if h: report["goi_no_tag"].append(anchor)
        continue
    link = re.search(r'href="([^"]+)"', h.group(1))
    main = body[h.end():body.index('<div class="list-pages-box">')]
    ps, num = [], ""
    alt = ""
    for p in paras(main):
        if p.startswith("GoI Number:"): num = p.split(":", 1)[1].strip(); continue
        m = re.match(r"^(\w+) Group of Interest Name:\s*(.+)$", p)
        if m: alt = m.group(2).strip() + " (" + m.group(1) + ")"; continue      # the group's name on its home branch
        ps.append(re.sub(r"^Overview:\s*", "", p))
    if tg.group(1) in d["tags"] and ps:
        url = (WIKI + link.group(1)) if link and link.group(1).startswith("/") else (link.group(1) if link else "")
        if "*" in url: url = WIKI + "/groups-of-interest#" + anchor      # a link the hub marks as external and that does not resolve as written
        out[tg.group(1)] = {"kind": "goi", "title": clean(h.group(1)), "p": ps, "num": num, "alt": alt, "url": url,
                            "hub": WIKI + "/groups-of-interest#" + anchor}
        report["goi"] += 1
    else:
        report["goi_no_tag"].append(anchor + ":" + tg.group(1))

# ---- Canons
CANON_TAG = {"cool war 2: ruiz from your grave": "cool-war-2", "the foundation alchemy department": "alchemy-department", "ㄗitch 卄aven": "pitch-haven"}   # canon name on the hub (lower case) -> tag, where the names differ
rc = hubs["canon-hub"]["raw_content"]
names = {d["tagName"][i].lower(): d["tags"][i] for i in range(len(d["tags"])) if d["tagKind"][i] == 1}
norm = lambda s: re.sub(r"[^a-z0-9]+", "", s.lower().replace("&", "and"))
bynorm = {norm(k): v for k, v in names.items()}; bynorm.update({norm(t): t for t in names.values()})
for block in re.split(r'<div class="canon-block[^>]*>', rc)[1:]:
    h2 = re.search(r"<h2[^>]*>(.*?)</h2>", block, flags=re.S)
    h = h2 and re.search(r'<a href="([^"]+)">(.*?)</a>', h2.group(1), flags=re.S)
    if not h: continue
    name = clean(h.group(2)); main = re.sub(r"<div[^>]*>\s*</div>", "", block[h2.end():]).split('<div class="snippet">')[0].split("</div>")[0]
    ps = paras(main)
    tag = CANON_TAG.get(name.lower()) or bynorm.get(norm(name)) or bynorm.get(norm(re.sub(r"^the ", "", name, flags=re.I)))
    if tag and ps and tag not in out:
        out[tag] = {"kind": "canon", "title": name, "p": ps, "num": "", "alt": "", "url": WIKI + h.group(1) if h.group(1).startswith("/") else h.group(1), "hub": WIKI + "/canon-hub"}
        report["canon"] += 1
    else:
        report["canon_unmatched"].append(name)
json.dump(out, open(sys.argv[3], "w"), ensure_ascii=False, indent=1)
have = set(out)
report["canon_tags_without_note"] = sorted(d["tagName"][i] for i in range(len(d["tags"])) if d["tagKind"][i] == 1 and d["tags"][i] not in have)
report["goi_tags_without_note"] = sorted(d["tagName"][i] for i in range(len(d["tags"])) if d["tagKind"][i] == 2 and d["tags"][i] not in have)
print(json.dumps(report, ensure_ascii=False, indent=1))
