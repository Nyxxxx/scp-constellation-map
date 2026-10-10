"""Builds contests.json from the wiki's own Contest Archive page (as stored in the dataset) plus a few hand entries.

Usage: python3 -I make_contests.py <hubs/index.json> contests_base.json contests.json

For every contest listed in the archive, the description and the winners are copied word for word from the archive.
Contests that the archive does not list keep the summary written by hand in contests_base.json, flagged "mine".
Unofficial contests are left out and their tags are returned as housekeeping tags.
"""
import html, json, re, sys

hubs = json.load(open(sys.argv[1]))
base = json.load(open(sys.argv[2]))
rc = hubs["contest-archive"]["raw_content"]

def text(x):
    x = re.sub(r"<br\s*/?>", "\n", x); x = re.sub(r"</(p|div|tr|li|td|h\d)>", "\n", x)
    x = re.sub(r"<[^>]+>", "", x); x = html.unescape(x); x = re.sub(r"[ \t\xa0]+", " ", x)
    return [l.strip() for l in x.split("\n") if l.strip()]

archive = {}
for it in rc.split('<div class="item">')[1:]:
    slug = re.search(r'<div class="item-title">\s*<p><a href="([^"]+)">', it).group(1).lstrip("/")
    lines = text(it)
    di = next(i for i, l in enumerate(lines) if re.match(r"\d{4}/\d", l))
    wi = next(i for i, l in enumerate(lines) if l.upper().startswith("WINNER"))
    win = []
    for l in lines[wi + 1:]:
        # the list of winners ends at the next year heading, at a nested unofficial contest (a host and a date follow its name) or at the page footer
        if re.match(r"\d{4} - \d{4}$", l) or l.startswith("‡") or l in ("MEMECON", "NIGHTMAREFEST", "RomCon", "International Canon Contest"):
            break
        if l.lower() != "and":
            win.append(l.replace(" does not match any existing user name", ""))
    archive[slug] = {"desc": " ".join(lines[di + 1:wi]), "win": win}

UNOFFICIAL = ["memecon2021-unofficial", "romcon2023-unofficial", "spook-nico-2024-unofficial", "dumbcon2026-unofficial", "timjc2026-unofficial",
              "goi2019", "nightmarefest", "intcanoncon2025"]
out, missing = {}, []
for tag, c in base.items():
    if tag in UNOFFICIAL:
        continue
    slug = c["url"].rsplit("/", 1)[-1]
    rec = {"name": c["name"], "d": c["d"], "when": c["when"], "url": c["url"]}
    if slug in archive:
        rec.update(desc=archive[slug]["desc"], win=archive[slug]["win"], mine=False)
    else:
        rec.update(desc=c["desc"], win=[c["win"]] if c["win"] else [], mine=True); missing.append(tag)
    out[tag] = rec
json.dump({"contests": out, "housekeeping": UNOFFICIAL}, open(sys.argv[3], "w"), ensure_ascii=False, indent=1)
print(len(out), "contests;", len(out) - len(missing), "from the archive; not in the archive:", missing)
