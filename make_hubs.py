"""Reads the series hubs held by the dataset and extracts, for each, the pages it lists in the hub's own order.

Usage: python3 -I make_hubs.py <raw dataset dir> <built json> hubs.json [series_hubs.json]

The dataset only holds the hubs whose title begins with a digit, A or B. series_hubs.json (written by fetch_series.py from the
wiki's Series Archive) adds the others; a hub present in both is read from the dataset.

A series hub is a page tagged "series-hub". Its reading list is taken from the body of the page, in document order:
links placed in list items, headings, table cells, or paragraphs made of little more than the link itself.
Left out: the rating box, the licence box, footnotes, author credits, "previous | hub | next" navigation lines and links
that sit in running prose. Section names are the headings (or tab names) above each link.
"""
import collections, html, json, re, sys
from bs4 import BeautifulSoup, NavigableString, Tag

RAW, BUILT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
hubs = json.load(open(RAW + "/hubs/index.json"))
for _p in sys.argv[4:]:
    for _s, _v in json.load(open(_p, encoding="utf-8")).items():
        if _s not in hubs and _s.lower() not in {k.lower() for k in hubs}: hubs[_s] = dict(_v, src="wiki")
d = json.load(open(BUILT))
on_map = {s.lower(): i for i, s in enumerate(d["slug"])}
HUB_SLUGS = {k.lower() for k in hubs}
kind = {d["tags"][i]: d["tagKind"][i] for i in range(len(d["tags"]))}
HREF = re.compile(r"^(?:https?://(?:www\.)?(?:scp-wiki\.wikidot\.com|scp-wiki\.net|scpwiki\.com))?/([^/#?]+)/?$")


def clean(t):
    return re.sub(r"\s+", " ", html.unescape(t or "")).strip()


def slug_of(a):
    m = HREF.match((a.get("href") or "").strip())
    return m.group(1).lower() if m else None


def parse(slug, raw):
    soup = BeautifulSoup(raw, "lxml")
    body = soup.find(id="page-content") or soup
    # tab names become section names: each tab's content gets a heading in front of it
    for nav in body.select("div.yui-navset"):
        names = [clean(li.get_text()) for li in nav.select("ul.yui-nav > li")]
        panes = nav.select("div.yui-content > div")
        for nm, pane in zip(names, panes):
            hd = soup.new_tag("h2"); hd.string = nm; hd["data-tab"] = "1"; pane.insert(0, hd)
        for ul in nav.select("ul.yui-nav"): ul.decompose()
    for sel in ("div.licensebox", "div.page-rate-widget-box", "div.footnotes-footer", "sup.footnoteref", "div.creditRate", "div.info-container",
                "div.credit", "div.footer-wikiwalk-nav", "div.preview", "div#u-credit-view", "div.modalbox", "div.authorlink-wrapper", "style", "script", "iframe"):
        for el in body.select(sel): el.decompose()
    # "« previous | hub | next »" lines
    for el in body.find_all(["p", "div", "td", "center", "strong"]):
        if el.find(["p", "div", "table", "ul"]) is None:
            t = clean(el.get_text())
            if len(t) < 260 and ("«" in t or "»" in t or t.count("|") >= 2): el.decompose()
    sections, seen, cur, off = [], set(), "", set()
    structured, loose = [], []

    def block_of(a):
        for p in a.parents:
            if isinstance(p, Tag) and p.name in ("li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "p", "dd", "dt", "blockquote"): return p
        return None

    def line_of(blk, a):
        """Blocks often hold several entries separated by line breaks: returns the number and the text of the line the link sits on."""
        idx, texts, hit = 0, [""], 0
        for x in blk.descendants:
            if isinstance(x, Tag) and x.name == "br": idx += 1; texts.append("")
            elif x is a: hit = idx
            elif isinstance(x, NavigableString): texts[idx] += str(x)
        return hit, clean(texts[hit])

    listlike = {}

    def list_paragraph(blk):
        """A paragraph of three lines or more, most of them opening with a link ("SCP-7027 A is for Annihilation - author"), is a list."""
        if id(blk) not in listlike:
            lines, cur_l = [], []
            for x in blk.descendants:
                if isinstance(x, Tag) and x.name == "br": lines.append(cur_l); cur_l = []
                elif isinstance(x, Tag) and x.name == "a": cur_l.append("a")
                elif isinstance(x, NavigableString) and x.strip() and not any(isinstance(p, Tag) and p.name == "a" for p in x.parents if p is not blk): cur_l.append("t")
            lines.append(cur_l)
            full = [l for l in lines if l]
            starts = sum(1 for l in full if l[0] == "a")
            listlike[id(blk)] = starts >= 3 and starts >= 0.6 * len(full)
        return listlike[id(blk)]

    # Headings give the section names. Wikidot numbers the headings written by the author (id="toc3"); when a page has such headings,
    # the unnumbered ones belong to cards and inserted modules and are not sections. "cur" is the path of headings above the current spot.
    heads = body.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    toc_only = sum(1 for hd in heads if (hd.get("id") or "").startswith("toc") or hd.get("data-tab")) >= 2
    order, stack, cur = 0, {}, ()
    for el in body.descendants:
        if isinstance(el, Tag) and el.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            t = clean(el.get_text()).rstrip(":").strip()
            # a heading that is itself a link to a page is an entry of the list, not the name of a section
            is_entry = any((slug_of(a) or "") in on_map for a in el.find_all("a"))
            numbered = (el.get("id") or "").startswith("toc") or el.get("data-tab")
            if t and not is_entry and (numbered or not toc_only):
                lvl = int(el.name[1])
                stack = {k: v for k, v in stack.items() if k < lvl}; stack[lvl] = t if len(t) <= 110 else t[:108].rstrip() + "…"
                cur = tuple(stack[k] for k in sorted(stack))
        if isinstance(el, Tag) and el.name == "a":
            s = slug_of(el)
            if not s or s == slug or (":" in s and not s.startswith("scp-")) or s in HUB_SLUGS or s.endswith("-hub"): continue
            blk = block_of(el); order += 1
            txt = clean(el.get_text())
            if blk is None: loose.append((order, s, cur, txt)); continue
            if blk.name == "blockquote": loose.append((order, s, cur, txt)); continue
            ln, btxt = line_of(blk, el)
            key = (id(blk), ln)
            if blk.name in ("p", "dd", "dt"):
                # a paragraph that is little more than the link: "Chapter 3: <link>" yes, a sentence with a link in it no
                rest = btxt[len(txt):].lstrip() if btxt.startswith(txt) else None
                card = rest is not None and len(txt) > 2 and len(btxt) < 200 and (rest == "" or re.match(r"(by\b|[-–—:(\[|/])", rest, re.I) is not None)   # title first, then the author or a few words
                lead = btxt.startswith(txt) and len(btxt) < 200 and list_paragraph(blk)   # a line of a list written as one paragraph
                if len(txt) >= 0.45 * max(1, len(btxt)) or len(btxt) - len(txt) <= 28 or card or lead: structured.append((order, s, cur, txt, key))
                else: loose.append((order, s, cur, txt))
            else:
                structured.append((order, s, cur, txt, key))
    # one page per list item or heading: the first link that leads to a page of the wiki's fiction
    picked, used_blocks = [], set()
    for order, s, sec, txt, b in structured:
        if b in used_blocks: continue
        if s in on_map: used_blocks.add(b); picked.append((s, sec))
        else: off.add(s)
    mode = "list"
    if len(picked) < 3:      # a hub written as prose: every link to a page on the map, in order
        allk = sorted([(o, s, sec) for o, s, sec, *_ in structured] + [(o, s, sec) for o, s, sec, _ in loose])
        picked = [(s, sec) for _, s, sec in allk if s in on_map]; mode = "prose"
    uniq = []
    for s, path in picked:
        if s not in seen: seen.add(s); uniq.append((s, path))
    # The section of a page is the deepest heading above it, unless that level of headings names single pages
    # (one heading per chapter): then the level above is used, and so on up to no sections at all.
    depth = max((len(p) for _, p in uniq), default=0)
    while True:
        out = collections.OrderedDict()
        for s, path in uniq:
            out.setdefault(path[min(depth, len(path)) - 1] if depth and path else "", []).append(s)
        singles = sum(1 for v in out.values() if len(v) == 1)
        if depth == 0 or not (len(out) >= 3 and singles >= 0.6 * len(out)): break
        depth -= 1
    off = {s for s in off if s not in on_map and not re.search(r"author|artist|-hub$|^system|^forum|^component|^theme|guide|^licensing|^nav|^main$|personnel|^user", s)}
    every = {slug_of(a) for a in body.find_all("a")}
    every = {s for s in every if s in on_map and s != slug and s not in HUB_SLUGS and not s.endswith("-hub")}
    return [[k, v] for k, v in out.items()], mode, len(off), len(every)


def blurb_of(raw):
    soup = BeautifulSoup(raw, "lxml")
    pv = soup.select_one("div.preview")
    if not pv: return ""
    ps = [clean(p.get_text()) for p in pv.find_all("p")] or [clean(pv.get_text())]
    return "\n".join(p for p in ps if p)


res = []
for slug, v in sorted(hubs.items()):
    tags = v.get("tags") or []
    if "series-hub" not in tags: continue
    raw = v.get("raw_content") or ""
    secs, mode, off, every = parse(slug.lower(), raw)
    n = sum(len(p) for _, p in secs)
    title = clean(re.sub(r"\s*-\s*SCP Foundation$", "", v.get("title") or slug))
    res.append({"slug": slug, "title": title, "date": (v.get("created_at") or "")[:7], "author": v.get("creator") or "",
                "blurb": blurb_of(raw), "canons": [t for t in tags if kind.get(t) == 1], "gois": [t for t in tags if kind.get(t) == 2],
                "sections": secs, "n": n, "mode": mode, "off": off, "every": every, "src": v.get("src", "dataset")})
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)
print(len(res), "series hubs read;", sum(1 for r in res if r["n"] >= 2), "with a reading list of two pages or more")
for r in res:
    print(f"\n== {r['slug']} | {r['title']} | {r['date']} {r['author']} | canons {r['canons']} gois {r['gois']} | {r['n']} pages of {r['every']} linked, {r['off']} off map, {r['mode']}")
    if r["blurb"]: print("   blurb:", r["blurb"][:160])
    for name, pages in r["sections"]:
        print("   [" + name + "]", ", ".join(pages[:14]) + (" …" if len(pages) > 14 else ""))
