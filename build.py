"""Build the data file for the SCP Constellation Map (SCP entries + tales + GoI formats).

Usage: python3 -I build.py <data dir: .../docs/data/scp> <output json> <region names json> [snapshot date] [extra pages json] [--prev previous output json]

With --prev (a refresh), the map is kept from one build to the next: every page placed by its tags whose tags have not changed keeps
its exact position; a new page, or one whose tags changed, is placed at the middle of its closest pages. The regions are searched again
starting from the previous regions, and each region that continues a previous one (sharing at least half of its pages) keeps its name.
Without --prev, the layout is computed afresh (UMAP), which moves every page.

The extra pages (Lost SCP Series, SCP-001 proposals, joke entries read from the live wiki; see make_extra.py) are treated like any other page:
they take part in the comparison, the regions and the layout.

Steps: read the snapshot, clean and weight the tags, compare every page with every other, find regions,
compute a small grid of layouts (for the shape sliders), then write one JSON file for the page.
"""
import collections
import glob
import json
import math
import os
import re
import sys

import numpy as np
import scipy.sparse as sp
from bs4 import BeautifulSoup
from scipy.spatial import cKDTree

ARGS = sys.argv[1:]
PREV_FILE = None
if "--prev" in ARGS:
    _i = ARGS.index("--prev"); PREV_FILE = ARGS[_i + 1]; del ARGS[_i:_i + 2]
BASE, OUT, NAMES_FILE = ARGS[0], ARGS[1], ARGS[2]
SNAPSHOT = ARGS[3] if len(ARGS) > 3 else ""
EXTRA = json.load(open(ARGS[4], encoding="utf-8")) if len(ARGS) > 4 else []
PREV = json.load(open(PREV_FILE, encoding="utf-8")) if PREV_FILE and os.path.exists(PREV_FILE) else None
SEED = 42
K_STORE = 10            # neighbours kept per page
K_GRAPH = 10            # neighbours used to find regions
MIN_DIST = 0.3
MIN_CLUSTER = 40
GATHER = [0.2]              # pull toward a page's own region (one layout; the shape sliders were dropped)
LINKPULL = [0.0]           # page links do not affect positions
DEFAULT_G, DEFAULT_EVEN = 0, 0.6

items = json.load(open(f"{BASE}/items/index.json"))
tales = json.load(open(f"{BASE}/tales/index.json"))
gois = json.load(open(f"{BASE}/goi/index.json"))
hubs = json.load(open(f"{BASE}/hubs/index.json"))

# ---------------------------------------------------------------- SCP nicknames from the series lists
nick = {}
for key, hub in hubs.items():
    if not (key.startswith("scp-series") or key in ("joke-scps", "scp-ex", "archived-scps", "scp-international")):
        continue
    soup = BeautifulSoup(hub.get("raw_content") or "", "html.parser")
    for li in soup.find_all("li"):
        a = li.find("a")
        if not a or not a.get("href"):
            continue
        slug = a["href"].strip().lstrip("/").lower()
        text = re.sub(r"\s+", " ", li.get_text(" ", strip=True))
        if " - " in text and slug not in nick:
            nick[slug] = text.split(" - ", 1)[1].strip()[:90]

# ---------------------------------------------------------------- read each page's source: classification and length
ACS_RE = re.compile(r"anomaly-class-bar-source(?:</a>)?(.*?)\]\]", re.S | re.I)
OLD_RE = re.compile(r"\*\*Object Class:?\*\*:?\s*([^\n]{1,60})")
DISRUPTION = ["dark", "vlam", "keneq", "ekhi", "amida"]
RISK = ["notice", "caution", "warning", "danger", "critical"]
MAIN = ["safe", "euclid", "keter", "neutralized", "pending", "explained", "decommissioned"]
ESO_TAGS = ["thaumiel", "apollyon", "archon", "ticonderoga", "cernunnos", "argus"]
KNOWN_ESO = ["thaumiel", "apollyon", "archon", "ticonderoga", "cernunnos", "uncontained", "hiemal", "tiamat"]
CLASS_KEYS = ["safe", "euclid", "keter", "neutralized", "pending"] + KNOWN_ESO + ["esoteric-other", "explained", "decommissioned", "none"]
CLASS_LABEL = {"esoteric-other": "Other esoteric", "none": "None listed"}
CLASS_GROUP = {"safe": 0, "euclid": 1, "keter": 2, "neutralized": 3, "thaumiel": 4, "pending": 6, "explained": 6, "decommissioned": 6, "none": 6}
JUNK = {"", "none", "n/a", "na", "null", "tbd", "class_here", "see below", "unknown", "standard", "pending", "esoteric", "?", "filler"}


def clean(v):
    v = re.sub(r"<[^>]+>", "", v)
    v = re.sub(r"[​-‏ -  ﻿]", " ", v)
    return re.sub(r"\s+", " ", v).strip().lower()


def word_count(html):
    """Rough length of the article body: words in the rendered page, without scripts, styles and the licence box."""
    html = html or ""
    cut = html.find('class="licensebox')
    if cut > 0:
        html = html[:cut]
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    return len(re.sub(r"<[^>]+>", " ", html).split())


src_info, words = {}, {}
for kind in ("items", "tales", "goi"):
    for f in sorted(glob.glob(f"{BASE}/{kind}/content_*.json")):
        if f.endswith("content_index.json"):
            continue
        for k, v in json.load(open(f)).items():
            words[(kind, k)] = word_count(v.get("raw_content"))
            if kind != "items":
                continue
            src = v.get("raw_source") or ""
            info = {}
            m = ACS_RE.search(src)
            if m:
                for pm in re.finditer(r"\|\s*([\w\-]+)\s*=\s*([^|\]\n]*)", m.group(1)):
                    info[pm.group(1).lower()] = clean(pm.group(2))
                info["acs"] = True
            else:
                m2 = OLD_RE.search(src)
                if m2:
                    t = re.sub(r"--.*?--", "", m2.group(1))
                    info["old"] = clean(re.sub(r"\[\[.*?\]\]|[^\w \-/<>]", "", t))
            src_info[k] = info


def name_ok(n):
    return bool(n) and n not in JUNK and len(n) <= 22 and re.fullmatch(r"[a-zà-ÿ\- ']{3,22}", n) is not None


def classify(key, tags):
    """Returns (class key, display name, clearance, disruption 0-5, risk 0-5, uses the new bar)."""
    t = set(tags)
    info = src_info.get(key, {})
    cont = info.get("container-class", "")
    sec = info.get("secondary-class", "")
    cont = "neutralized" if cont == "neutralised" else cont
    main_tag = next((c for c in ["explained", "decommissioned", "neutralized", "pending", "keter", "euclid", "safe"] if c in t), None)
    eso_tag = next((c for c in ESO_TAGS if c in t), None)
    name = None
    if name_ok(sec):
        name = sec
    elif name_ok(cont) and cont not in MAIN:
        name = cont
    elif eso_tag:
        name = eso_tag
    elif "esoteric-class" in t and name_ok(info.get("old", "")) and info["old"] not in MAIN:
        name = info["old"]
    if name in MAIN:
        name = None
    if name or eso_tag or "esoteric-class" in t:
        ckey = name if name in KNOWN_ESO else "esoteric-other"
        base = cont if cont in MAIN else (main_tag if main_tag in ("safe", "euclid", "keter") else None)
        disp = ((base.capitalize() + " / " if base else "") + name.title()) if name else "Esoteric (unnamed)"
    elif main_tag:
        ckey, disp = main_tag, main_tag.capitalize()
    elif cont in MAIN:
        ckey, disp = cont, cont.capitalize()
    else:
        ckey, disp = "none", "None listed"
    lvl = int(info["clearance"]) if re.fullmatch(r"[1-6]", info.get("clearance", "")) else 0
    dis = DISRUPTION.index(info["disruption-class"]) + 1 if info.get("disruption-class") in DISRUPTION else 0
    risk = RISK.index(info["risk-class"]) + 1 if info.get("risk-class") in RISK else 0
    return ckey, disp, lvl, dis, risk, bool(info.get("acs"))


# ---------------------------------------------------------------- one list of pages
pages = []   # type 0 SCP / 1 tale / 2 GoI format
for k in sorted(items, key=lambda k: (items[k]["series"], items[k]["scp_number"], k)):
    it = items[k]
    pages.append({"t": 0, "key": k, "kind": "items", "id": it["scp"], "title": nick.get(it["link"].lower(), ""), "src": it})
for kind, coll, t in (("tales", tales, 1), ("goi", gois, 2)):
    for k in sorted(coll, key=lambda k: (coll[k].get("created_at") or "", k)):
        it = coll[k]
        pages.append({"t": t, "key": k, "kind": kind, "id": "", "title": re.sub(r"\s+-\s+SCP Foundation\s*$", "", it["title"]).strip()[:90], "src": it})
SRC_COUNT = collections.Counter(p["t"] for p in pages)     # what the dataset itself holds
for r in EXTRA:                                             # pages read from the live wiki, given the same shape as a dataset record
    src = {"link": r["slug"], "title": r["title"], "tags": r["tags"], "rating": r["rating"], "created_at": r["ym"] + "-01", "creator": r["author"],
           "series": "", "scp": r["id"], "scp_number": 0, "references": []}
    pages.append({"t": r["type"], "key": "extra:" + r["slug"], "kind": "extra", "id": r["id"], "title": r["title"], "src": src, "group": r["group"], "approx": r["approx"]})
N = len(pages)
slug_to_idx = {}
for i, p in enumerate(pages):
    slug_to_idx.setdefault(p["src"]["link"].lower(), i)

# ---------------------------------------------------------------- tag roles
CLASS_TAGS = set(MAIN + ESO_TAGS + ["esoteric-class"])
TYPE_TAGS = {"scp", "tale", "goi-format"}
META_TAGS = {
    "co-authored", "featured", "rewrite", "rewritable", "in-rewrite", "illustrated",
    "reviewers-spotlight", "event-featured", "prize-feature", "audio", "video", "interactive",
    "collaboration", "joke", "international", "001-proposal", "missing-number", "news-prompt",
    "exchange", "art-exchange", "coldpostcon", "spring-cleaning24", "jockjamsvol6", "image-editing",
    "goi-art", "comic", "cel-shaded", "hand-drawn-cassy", "painted", "contest", "event", "hub",
    "supplement", "archived", "metadata", "essay", "guide", "author", "artwork", "splash", "fragment",
    "admin", "component", "theme", "resource", "sandbox", "poll", "creepypasta", "orientation",
    "173fest", "nightmarefest", "glacon", "lost-series", "redirect", "in-deletion",      # events, a character-art tag and housekeeping that slipped through
}
CONTEST_RE = re.compile(r"(19|20)\d\d|^\d000$|con-?\d|-unofficial$")


def role(tag):
    if tag.startswith("_") or tag in TYPE_TAGS:
        return "hidden"
    if tag in CLASS_TAGS:
        return "class"
    if tag in META_TAGS or CONTEST_RE.search(tag):
        return "meta"
    return "content"


df = collections.Counter()
for p in pages:
    df.update(set(p["src"]["tags"] or []))
shown = sorted((t for t in df if role(t) in ("content", "meta")), key=lambda t: (-df[t], t))
tag_idx = {t: i for i, t in enumerate(shown)}
used = [1 if (role(t) == "content" and df[t] >= 2) else 0 for t in shown]
idf = np.array([math.log(N / df[t]) if u else 0.0 for t, u in zip(shown, used)])

rows, cols, vals = [], [], []
node_tags = []
for i, p in enumerate(pages):
    ts = sorted({tag_idx[t] for t in (p["src"]["tags"] or []) if t in tag_idx})
    node_tags.append(ts)
    for t in ts:
        if used[t]:
            rows.append(i); cols.append(t); vals.append(idf[t])
X = sp.csr_matrix((vals, (rows, cols)), shape=(N, len(shown)))
norm = np.sqrt(X.multiply(X).sum(axis=1)).A1
has_vec = norm > 0
norm[~has_vec] = 1.0
X = (sp.diags(1.0 / norm) @ X).tocsr()
tcount = collections.Counter(p["t"] for p in pages)
print(f"pages {N} (SCP {tcount[0]}, tales {tcount[1]}, GoI {tcount[2]}), tags used {sum(used)}, no usable tag {int((~has_vec).sum())}, "
      f"lost series present: {'scp-l001' in slug_to_idx}", flush=True)

# ---------------------------------------------------------------- neighbours
KMAX = max(K_STORE, K_GRAPH)
nb_idx = np.zeros((N, KMAX), dtype=np.int32)
nb_sim = np.zeros((N, KMAX), dtype=np.float32)
XT = X.T.tocsr()
for s in range(0, N, 1000):
    S = (X[s:s + 1000] @ XT).toarray()
    for r in range(S.shape[0]):
        S[r, s + r] = -1.0
    part = np.argpartition(-S, KMAX + 8, axis=1)[:, :KMAX + 8]
    ps = np.take_along_axis(S, part, axis=1)
    # equally similar pages are ordered by their place in the list, so the result does not depend on the machine
    order = np.lexsort((part, -np.round(ps, 6)), axis=1)[:, :KMAX]
    nb_idx[s:s + 1000] = np.take_along_axis(part, order, axis=1)
    nb_sim[s:s + 1000] = np.take_along_axis(ps, order, axis=1)

# ---------------------------------------------------------------- regions (from tags only, the same for every layout)
import igraph as ig  # noqa: E402
import leidenalg  # noqa: E402

edges = {}
for i in range(N):
    if not has_vec[i]:
        continue
    for j, s in zip(nb_idx[i, :K_GRAPH], nb_sim[i, :K_GRAPH]):
        if s <= 0.05:
            continue
        a, b = (i, int(j)) if i < j else (int(j), i)
        edges[(a, b)] = max(edges.get((a, b), 0.0), float(s))
g = ig.Graph(n=N, edges=list(edges), directed=False)
g.es["weight"] = list(edges.values())
# the previous build, matched page by page through the address of each page
old_of = np.full(N, -1)
if PREV:
    _pi = {s.lower(): i for i, s in enumerate(PREV["slug"])}
    old_of = np.array([_pi.get(p["src"]["link"].lower(), -1) for p in pages])
    prev_pos = np.array(PREV["P"][0], dtype=float).reshape(-1, 2)
    prev_cluster = np.array(PREV["cluster"])
    print(f"previous build: {len(PREV['slug'])} pages, {int((old_of >= 0).sum())} of them still here, {int((old_of < 0).sum())} new", flush=True)
def tagset_now(i): return {shown[t] for t in node_tags[i] if used[t]}
def tagset_prev(o): return {PREV["tags"][t] for t in PREV["tg"][o] if PREV["tagUsed"][t]}
same_tags = np.array([PREV is not None and old_of[i] >= 0 and tagset_now(i) == tagset_prev(old_of[i]) for i in range(N)])
if PREV:
    # A refresh keeps the regions: a page whose tags have not changed stays in its region; a new page, or one whose tags changed,
    # joins the region of most of its closest pages (at least half of those that have a region), or none.
    big = list(range(len(PREV["clusters"])))
    cluster = np.full(N, -1)
    cluster[same_tags] = prev_cluster[old_of[same_tags]]
    for i in np.where(~same_tags & has_vec)[0]:
        votes = collections.Counter(int(cluster[j]) for j, s in zip(nb_idx[i, :K_GRAPH], nb_sim[i, :K_GRAPH]) if s > 0.05 and same_tags[j] and cluster[j] >= 0)
        if votes:
            c, n_ = votes.most_common(1)[0]
            if n_ >= 0.5 * sum(votes.values()): cluster[i] = c
    cluster[~has_vec] = -1
    print(f"refresh: {int(same_tags.sum())} pages keep their region; {int((~same_tags & has_vec).sum())} new or retagged pages joined "
          f"{int(((~same_tags) & (cluster >= 0)).sum())} times a region", flush=True)
else:
    part = leidenalg.find_partition(g, leidenalg.RBConfigurationVertexPartition, weights="weight",
                                    resolution_parameter=1.0, seed=SEED, n_iterations=-1)
    member = np.array(part.membership)
    sizes = collections.Counter(member.tolist())
    big = [c for c, n in sizes.most_common() if n >= MIN_CLUSTER]
    remap = {c: i for i, c in enumerate(big)}
    cluster = np.array([remap.get(c, -1) for c in member])
    cluster[~has_vec] = -1

# ---------------------------------------------------------------- page links (hyperlinks between pages)
cites = set()
link_nb = collections.defaultdict(set)
for i, p in enumerate(pages):
    it = p["src"]
    for ref in it.get("references") or []:
        j = slug_to_idx.get(str(ref).lower())
        if j is None or j == i:
            continue
        o = pages[j]["src"]
        if p["t"] == 0 and pages[j]["t"] == 0 and o["series"] == it["series"] and abs(o["scp_number"] - it["scp_number"]) == 1:
            continue   # previous / next navigation
        cites.add((i, j)); link_nb[i].add(j); link_nb[j].add(i)
cite_flat = [v for pair in sorted(cites) for v in pair]

# ---------------------------------------------------------------- layouts: a small grid the page morphs between
import umap  # noqa: E402
from sklearn.decomposition import TruncatedSVD  # noqa: E402

hv = np.where(has_vec)[0]
onehot = sp.csr_matrix((np.ones(int((cluster >= 0).sum())), (np.where(cluster >= 0)[0], cluster[cluster >= 0])), shape=(N, max(1, len(big))))
# link features: each page described by the pages it links to or from (and itself), popular targets weighted down
lr_, lc_ = [], []
for i in range(N):
    for j in link_nb[i] | {i}:
        lr_.append(i); lc_.append(j)
Lm = sp.csr_matrix((np.ones(len(lr_)), (lr_, lc_)), shape=(N, N))
ldf = np.asarray(Lm.sum(axis=0)).ravel()
Lm = Lm @ sp.diags(np.log(1 + N / np.maximum(ldf, 1)))
Lm = (sp.diags(1.0 / np.sqrt(Lm.multiply(Lm).sum(axis=1)).A1) @ Lm).tocsr()


def features(gv, lv):
    return sp.hstack([X, gv * onehot, lv * Lm]).tocsr()[hv]


def run(F, init, epochs, rate=1.0):
    return umap.UMAP(n_neighbors=20, min_dist=MIN_DIST, spread=1.0, metric="cosine", random_state=SEED, n_epochs=epochs, init=init,
                     repulsion_strength=0.5, negative_sample_rate=3, learning_rate=rate).fit_transform(F)


def normalise(e, ref=None):
    """Centre, optionally rotate onto a reference layout (so morphs do not spin), and scale so most pages sit within 1000."""
    c = e - np.median(e, axis=0)
    if ref is not None:
        u, _, vt = np.linalg.svd(c.T @ ref)
        c = c @ (u @ vt)
    p = c / np.percentile(np.sqrt((c ** 2).sum(axis=1)), 98.5) * 1000.0
    rr = np.sqrt((p ** 2).sum(axis=1))
    far = rr > 1000
    p[far] *= ((1000 + (rr[far] - 1000) * 0.2) / rr[far])[:, None]
    return p


F0 = features(GATHER[DEFAULT_G], 0.0)
import zlib  # noqa: E402
# small offsets drawn from each page's own address, so they do not change when other pages come or go
_h = [zlib.crc32(p["src"]["link"].lower().encode()) for p in pages]
jit_ang = np.array([(x % 3600) / 3600 * 2 * math.pi for x in _h])
jit_r = np.array([6 + (x // 3600 % 1000) / 100 for x in _h])

prev_placed = np.array(PREV["placed"]) if PREV else None
stable = PREV is not None and sum(1 for i in hv if old_of[i] >= 0 and prev_placed[old_of[i]] == 0) >= 100
raw = {}
if stable:
    # A refresh keeps the map: a page that was placed by its tags last time and whose tags have not changed stays exactly where it was.
    # A new page, or one whose tags changed, goes to the middle of its closest pages that stayed, with a small offset of its own.
    # The layout is computed afresh only on request (make.py all --fresh).
    stay = np.array([same_tags[i] and prev_placed[old_of[i]] == 0 for i in hv])
    ref = np.zeros((len(hv), 2))
    ref[stay] = prev_pos[old_of[hv[stay]]]
    stay_set = {int(i) for i in hv[stay]}
    k_of = {int(i): k_ for k_, i in enumerate(hv)}
    centre = np.median(ref[stay], axis=0)
    for k_, i in enumerate(hv):
        if stay[k_]: continue
        near = [ref[k_of[int(j)]] for j, s in zip(nb_idx[i, :K_STORE], nb_sim[i, :K_STORE]) if int(j) in stay_set and s > 0.05][:5]
        base = np.median(near, axis=0) if near else centre
        ref[k_] = base + (jit_r[i] * math.cos(jit_ang[i]), jit_r[i] * math.sin(jit_ang[i]))
    n_new = int(sum(1 for i in hv if old_of[i] < 0))
    print(f"refresh: {int(stay.sum())} pages stay in place; {n_new} new pages and {int((~stay).sum()) - n_new} pages whose tags changed "
          f"are placed beside their closest pages", flush=True)
else:
    init = TruncatedSVD(n_components=2, random_state=SEED).fit_transform(F0)
    init = (init - init.mean(axis=0)) / init.std(axis=0) * 4.0 + np.random.RandomState(SEED).normal(0, 0.05, init.shape)
    raw[(DEFAULT_G, 0)] = run(F0, init, 400)
    print("layout base done", flush=True)
    ref = normalise(raw[(DEFAULT_G, 0)])
ring = [i for i in np.where(~has_vec)[0] if not any(has_vec[j] for j in link_nb[i])]
RING = set(ring)
by_links = np.array([(not has_vec[i]) and i not in RING for i in range(N)])
LAYOUTS = []      # full position arrays, before the centre is spread out (the page does that live)
for gi in range(len(GATHER)):
    for li in range(len(LINKPULL)):
        pos = np.zeros((N, 2))
        pos[hv] = ref if (gi, li) == (DEFAULT_G, 0) else normalise(raw[(gi, li)], ref)
        for i in np.where(by_links)[0]:
            if stable and old_of[i] >= 0 and prev_placed[old_of[i]] == 1:
                pos[i] = prev_pos[old_of[i]]; continue      # placed by its links last time too: keeps its spot
            nbrs = [j for j in link_nb[i] if has_vec[j]]
            pos[i] = np.median(pos[nbrs], axis=0) + (jit_r[i] * 0.4 * math.cos(jit_ang[i]), jit_r[i] * 0.4 * math.sin(jit_ang[i]))
        for n_, i in enumerate(ring):
            if PREV and old_of[i] >= 0 and prev_placed[old_of[i]] == 2:
                pos[i] = prev_pos[old_of[i]]      # a page already on the outer ring keeps its spot
            else:
                ang = 2 * math.pi * n_ / max(1, len(ring)) + 0.6 if not PREV else jit_ang[i]
                pos[i] = (1085 * math.cos(ang), 1085 * math.sin(ang))
        LAYOUTS.append(pos)
if PREV:
    _here = old_of >= 0
    _d = np.sqrt(((LAYOUTS[0][_here] - prev_pos[old_of[_here]]) ** 2).sum(axis=1))
    print(f"compared with the previous build (map radius 1000): {int((_d < 0.5).sum())} of {int(_here.sum())} pages did not move; "
          f"of those that did, median {np.median(_d[_d >= 0.5]) if (_d >= 0.5).any() else 0:.0f}, max {_d.max():.0f}", flush=True)


def spread(pos, even):
    """The same transform the page applies live: stretch distances from the centre so pages fill the disc more evenly."""
    out = pos.copy()
    idx = np.array([i for i in range(N) if i not in RING])
    r0 = np.sqrt((pos[idx] ** 2).sum(axis=1))
    rank = np.argsort(np.argsort(r0)) / max(1, len(idx) - 1)
    r1 = (1 - even) * r0 + even * 1000.0 * np.sqrt(rank)
    out[idx] *= (r1 / np.maximum(r0, 1e-9))[:, None]
    return out


DEF = spread(LAYOUTS[DEFAULT_G * len(LINKPULL)], DEFAULT_EVEN)

# ---------------------------------------------------------------- readable names for tags
PRETTY = {
    "are-we-cool-yet": "Are We Cool Yet?", "marshall-carter-and-dark": "Marshall, Carter & Dark", "dr-wondertainment": "Dr. Wondertainment",
    "serpents-hand": "Serpent's Hand", "sarkic": "Sarkicism", "fifthist": "Fifth Church", "broken-god": "Church of the Broken God",
    "wilsons-wildlife": "Wilson's Wildlife Solutions", "herman-fuller": "Herman Fuller's Circus", "oneiroi": "Oneiroi Collective",
    "prometheus": "Prometheus Labs", "anderson": "Anderson Robotics", "daevite": "Daevites", "gru-division-p": "GRU Division \"P\"",
    "obskura": "Obskurakorps", "ijamea": "IJAMEA", "hmfscp": "HMFSCP", "asci": "ASCI", "aiad": "AIAD", "icsut": "ICSUT",
    "mister": "Little Misters", "nobody": "Nobody", "on-guard-43": "On Guard 43", "class-of-76": "Class of '76",
    "s&c-plastics": "S & C Plastics", "dread&circuses": "Dread & Circuses", "homo-sapiens-sidhe": "Homo sapiens sidhe",
    "ad-astra": "Ad Astra Per Aspera", "memoria-adytum": "In Memoria, Adytum", "orcadia": "Seas of Orcadia",
    "deepwell-catalog": "Site-17 Deepwell Catalog", "twisted-pines": "Those Twisted Pines", "wonderful-world": "What a Wonderful World",
    "world-kept-turning": "The World Kept Turning", "man-who-wasnt-there": "The Man Who Wasn't There", "heimdall": "Project Heimdall",
    "green-king": "Codename: Green King", "lolfoundation": "lolFoundation", "from-120s-archives": "From 120's Archives",
    "series-0": "Series 0", "rats-nest": "Rat's Nest", "straight-on-til-morning": "Straight On Till Morning", "cool-war-2": "Cool War 2",
    "unusual-incidents-unit": "Unusual Incidents Unit", "global-occult-coalition": "Global Occult Coalition",
    "gamers-against-weed": "Gamers Against Weed", "manna-charitable-foundation": "Manna Charitable Foundation",
    "the-sculpture": "The Sculpture (SCP-173)", "hard-to-destroy-reptile": "Hard-to-Destroy Reptile (SCP-682)", "k-class-scenario": "K-class scenarios",
    "lgbtq": "LGBTQ+", "w-i-t-c-h": "W.I.T.C.H.", "7th-occult-war": "Seventh Occult War", "old-ai": "Old AI",
    "director-mcinnis": "Director McInnis", "scp-format": "SCP format", "factory": "The Factory", "nightfall": "NIGHTFALL",
    "unhuman": "UnHuman", "simulacrum": "SIMULACRUM", "unreality-dept": "Department of Unreality", "antimemetic": "Antimemetics", "raisa": "RAISA",
    "joke": "Joke pages",
}
CONTEST_NAMES = {"jam-con": "Jam Con", "goicon-": "GoI Con", "publicdomaincon": "Public Domain Con", "halloweencon": "Halloween Con",
                 "intcanoncon": "International Canon Con", "collab-con": "Collab Con", "d-con": "D-Con", "memecon": "Meme Con",
                 "romcon": "Rom Con", "sportscon": "Sports Con", "dumbcon": "Dumb Con", "wrathcon": "Wrath Con", "lorecon": "Lore Con",
                 "remixcon": "Remix Con", "hiscon": "History Con", "classiccon": "Classic Con", "departmentcon": "Department Con",
                 "goblincon": "Goblin Con", "goi": "GoI Contest", "canon": "Canon Contest", "mtf": "MTF Contest", "doomsday": "Doomsday Contest",
                 "cupid": "Cupid Contest", "cliche": "Cliché Contest", "exquisite-corpse": "Exquisite Corpse", "pridefest": "Pridefest",
                 "halloween": "Halloween Contest", "af": "April Fools", "talecon": "Tale Con", "timjc": "TIMJC", "spook-nico-": "Spook Nico"}
CANON_TAGS = {
    "aces-and-eights", "ad-astra", "aiad", "apotheosis", "bellerverse", "black-diamond-billions", "broken-masquerade", "but-a-dream",
    "chaos-on-the-monolith", "the-coldest-war", "competitive-eschatology", "cool-war-2", "daybreak", "doctors-of-the-church",
    "dread&circuses", "end-of-death", "eventyr", "fading-stars", "forgotten-memories", "alchemy-department", "from-120s-archives",
    "the-gulf", "memoria-adytum", "insect-hell", "lampeter", "man-who-wasnt-there", "nightfall", "ninth-world", "no-return",
    "on-guard-43", "our-open-veins", "pitch-haven", "rats-nest", "resurrection", "s&c-plastics", "orcadia", "semiotics", "series-0",
    "simulacrum", "deepwell-catalog", "straight-on-til-morning", "third-law", "the-sharkest-timeline", "twisted-pines", "unfounded",
    "unhuman", "war-on-all-fronts", "wonderful-world", "world-kept-turning", "antarctic-exchange", "green-king", "lolfoundation",
    "on-mount-golgotha", "only-game-in-town", "heimdall", "the-trashfire", "old-man-in-the-sea", "ship-in-a-bottle",
}
NOT_GROUP = {"other", "image", "adult", "genreless", "marine", "explosions", "delicious", "corruption", "shaggy-dog", "meets-the-eye",
             "famouslastwords", "murder-mystery", "all-a-dream", "tropical", "pulp-fiction", "dark-and-stormy", "townhouse",
             "the-bureaucrat", "graveyard-shift", "cc", "cc4", "licensebox", "listpages"}
GOI_TAGS = set()
for it in gois.values():
    for t in it["tags"] or []:
        if t.startswith("_") and t[1:] in df and t[1:] not in NOT_GROUP and len(t) > 4:
            GOI_TAGS.add(t[1:])
GOI_TAGS |= {"dr-wondertainment", "mister", "gamers-against-weed", "daevite", "children-of-the-night", "homo-sapiens-sidhe"} & set(df)
GOI_TAGS -= CANON_TAGS


def kind(tag):
    if tag in CANON_TAGS:
        return "canon"
    if tag in GOI_TAGS:
        return "goi"
    if role(tag) == "meta" and CONTEST_RE.search(tag):
        return "contest"
    return "tag"


def pretty(tag):
    if tag in PRETTY:
        return PRETTY[tag]
    if kind(tag) == "contest":
        if re.fullmatch(r"\d000", tag):
            return f"SCP-{tag} contest"
        base, unofficial = (tag[:-11], " (unofficial)") if tag.endswith("-unofficial") else (tag, "")
        m = re.fullmatch(r"(.*?)-?((?:19|20)\d\d|\d\d)", base)
        stem, year = (m.group(1), m.group(2)) if m else (base, "")
        name = next((v for k_, v in CONTEST_NAMES.items() if stem == k_.rstrip("-") or stem + "-" == k_), None) or stem.upper() if len(stem) <= 3 else \
            next((v for k_, v in CONTEST_NAMES.items() if stem == k_.rstrip("-")), stem.replace("-", " ").title())
        return (name + " " + year).strip() + unofficial
    t = re.sub(r"^doctor-", "Dr. ", tag)
    ws = t.replace("-", " ").split(" ")
    small = {"of", "the", "and", "in", "on", "a", "to", "for", "at"}
    return " ".join(w if (w.startswith("Dr.") or (i and w in small)) else w[:1].upper() + w[1:] for i, w in enumerate(ws))


# ---------------------------------------------------------------- regions: names written by hand, anchors per layout
REGION_NAMES = json.load(open(NAMES_FILE))


def densest(p, radius):
    tree = cKDTree(p)
    counts = np.array([len(x) for x in tree.query_ball_point(p, radius)])
    return p[tree.query_ball_point(p[int(counts.argmax())], radius)].mean(axis=0)


heir = {c: c for c in big} if PREV else {}     # in a refresh every region continues the previous one of the same number
clusters, unify = [], set()
for c in range(len(big)):
    idx = np.where(cluster == c)[0]
    cnt = collections.Counter(t for i in idx for t in node_tags[i] if used[t])
    scored = []
    for t, n_in in cnt.items():
        share_in, share_all = n_in / len(idx), df[shown[t]] / N
        if n_in >= max(4, 0.08 * len(idx)):
            scored.append((share_in * math.log(share_in / share_all), t))
    top = [t for _, t in sorted(scored, reverse=True)[:6]]
    sig = "|".join(shown[t] for t in top[:3])
    if c in heir:      # a region that continues a previous one keeps its key, and so its name and description
        sig = PREV["clusters"][heir[c]]["sig"]
    entry = REGION_NAMES.get(sig, {})
    cl = {"tags": top, "n": int(len(idx)), "sig": sig, "desc": entry.get("desc", ""), "tag": -1, "kind": 0}
    if entry.get("tag") in tag_idx:
        cl["tag"] = tag_idx[entry["tag"]]; cl["label"] = pretty(entry["tag"]); cl["kind"] = {"canon": 1, "goi": 2}.get(kind(entry["tag"]), 0)
        unify.add(cl["tag"])
    else:
        cl["label"] = entry.get("name") or " · ".join(pretty(shown[t]) for t in top[:2]) or "Unsorted"
    clusters.append(cl)
missing = [c["sig"] for c in clusters if c["sig"] not in REGION_NAMES]
print(f"regions {len(clusters)}, hand-named {len(clusters) - len(missing)}; not named: {missing}", flush=True)

# landmarks: canons, GoIs and other tags whose pages sit in one place (chosen on the default layout)
tag_members = collections.defaultdict(list)
for i, ts in enumerate(node_tags):
    for t in ts:
        if used[t]:
            tag_members[t].append(i)
region_labels = {c["label"].lower() for c in clusters}
landmarks = []
for t, mem in tag_members.items():
    name = shown[t]
    kd = kind(name)
    n = len(mem)
    if t in unify or pretty(name).lower() in region_labels or n < (10 if kd != "tag" else 14) or n > 600:
        continue
    p = DEF[mem]
    tree = cKDTree(p)
    counts = np.array([len(x) for x in tree.query_ball_point(p, 55)])
    best = int(counts.argmax())
    share = len(tree.query_ball_point(p[best], 110)) / n
    if share < (0.4 if kd != "tag" else 0.6) or counts[best] < 7 or (kd == "tag" and n > 160):
        continue
    landmarks.append({"t": int(t), "label": pretty(name), "kind": {"canon": 1, "goi": 2, "tag": 0}[kd], "n": n})
landmarks.sort(key=lambda d: (0 if d["kind"] else 1, -d["n"]))
if PREV:
    # a refresh keeps the previous names on the map (as long as their tag still has 10 pages or more); names that now qualify take the places of those that left
    keep, before = [], set()
    for l in PREV["landmarks"]:
        name = PREV["tags"][l["t"]]; before.add(name)
        t = tag_idx.get(name)
        if t is not None and t not in unify and len(tag_members[t]) >= 10:
            keep.append({"t": int(t), "label": pretty(name), "kind": l["kind"], "n": len(tag_members[t])})
    landmarks = (keep + [l for l in landmarks if shown[l["t"]] not in before])[:max(260, len(keep))]   # new names only fill freed places
else:
    landmarks = landmarks[:260]

CA, LA = [], []    # anchors per layout, in the same order as LAYOUTS
# in a refresh, a region or a name whose pages are the same as before keeps its anchor
slug_l = [p["src"]["link"].lower() for p in pages]
prev_ca, prev_la = {}, {}
if PREV:
    pslug = [s.lower() for s in PREV["slug"]]
    pmem = collections.defaultdict(set)
    for i, c in enumerate(PREV["cluster"]):
        if c >= 0: pmem[c].add(pslug[i])
    pca = PREV["CA"][0]
    prev_ca = {c: (frozenset(pmem[c]), (pca[2 * c], pca[2 * c + 1])) for c in pmem}
    pla = PREV["LA"][0]
    for q, l in enumerate(PREV["landmarks"]):
        prev_la[PREV["tags"][l["t"]]] = (frozenset(pslug[i] for i, ts in enumerate(PREV["tg"]) if l["t"] in ts), (pla[2 * q], pla[2 * q + 1]))
for pos in LAYOUTS:
    ca = []
    for c in range(len(big)):
        mem = frozenset(slug_l[i] for i in np.where(cluster == c)[0])
        a = prev_ca[c][1] if c in prev_ca and prev_ca[c][0] == mem else densest(pos[cluster == c], 40)
        ca += [int(round(a[0])), int(round(a[1]))]
    la = []
    for l in landmarks:
        name = shown[l["t"]]
        mem = frozenset(slug_l[i] for i in tag_members[l["t"]])
        a = prev_la[name][1] if name in prev_la and prev_la[name][0] == mem else densest(pos[tag_members[l["t"]]], 32)
        la += [int(round(a[0])), int(round(a[1]))]
    CA.append(ca); LA.append(la)

# ---------------------------------------------------------------- output
authors = sorted({p["src"]["creator"] or "Unknown" for p in pages})
aidx = {a: i for i, a in enumerate(authors)}
names, name_idx = [], {}


def nid(s):
    if s not in name_idx:
        name_idx[s] = len(names); names.append(s)
    return name_idx[s]


SERIES = ["series-1", "series-2", "series-3", "series-4", "series-5", "series-6", "series-7", "series-8", "series-9", "series-10",
          "explained", "decommissioned", "joke", "international", "scp-001"]
SERIES_LABEL = ["Series I (001 to 999)", "Series II", "Series III", "Series IV", "Series V", "Series VI", "Series VII", "Series VIII",
                "Series IX", "Series X", "Explained (-EX)", "Decommissioned (-D)", "Joke entries (-J)", "International", "SCP-001 proposals",
                "Lost SCP Series (L000 to L999)"]


def series_of(p):
    """The series follows the entry's number or suffix, not its tags (a plain-numbered entry tagged "explained" stays in its numbered series)."""
    if p.get("group") == "lost": return 15
    if p.get("group") == "p001": return 14
    pid = p["id"]
    m = re.match(r"^SCP-(\d+)$", pid)
    if m and 1 < int(m.group(1)) < 10000: return int(m.group(1)) // 1000
    if re.match(r"^SCP-\d+-EX$", pid): return 10
    if re.match(r"^SCP-\d+-D$", pid): return 11
    if pid.endswith("-J") or p.get("group") == "joke": return 12
    if re.match(r"^SCP-\d+-[A-Z]+$", pid): return 13
    return SERIES.index(p["src"]["series"]) if p["src"]["series"] in SERIES else -1
ck, cn, lvl, dis, risk, acs, series = [], [], [], [], [], [], []
for p in pages:
    tags = p["src"]["tags"] or []
    if p["t"] == 0:
        k_, disp, l_, d_, r_, a_ = classify(p["key"], tags)
        ck.append(CLASS_KEYS.index(k_)); cn.append(nid(disp)); lvl.append(l_); dis.append(d_); risk.append(r_); acs.append(1 if a_ else 0)
        series.append(series_of(p))
    else:
        grp = ""
        if p["t"] == 2:
            cand = [t[1:] for t in tags if t.startswith("_") and t[1:] in GOI_TAGS]
            grp = pretty(cand[0]) if cand else "Other or mixed groups"
        ck.append(-1); cn.append(nid(grp)); lvl.append(0); dis.append(0); risk.append(0); acs.append(0); series.append(-1)


def month(p):
    m = re.match(r"(\d{4})-(\d{2})", p["src"].get("created_at") or "")
    return (int(m.group(1)) - 2008) * 12 + int(m.group(2)) - 1 if m else 0


out = {
    "meta": {"snapshot": SNAPSHOT, "n": N, "tagsUsed": int(sum(used)), "loose": len(ring), "byLinks": int(by_links.sum()),
             "acs": int(sum(acs)), "scp": tcount[0], "tales": tcount[1], "goi": tcount[2],
             "src": [SRC_COUNT[0], SRC_COUNT[1], SRC_COUNT[2]],
             "lost": sum(1 for p in pages if p.get("group") == "lost"), "p001Added": sum(1 for p in pages if p.get("group") == "p001"),
             "jokesAdded": sum(1 for p in pages if p.get("group") == "joke"),
             "gather": GATHER, "links": LINKPULL, "defaultGather": DEFAULT_G, "defaultEven": DEFAULT_EVEN},
    "tags": shown, "tagUsed": used, "tagDf": [df[t] for t in shown],
    "tagName": [pretty(t) for t in shown], "tagKind": [{"tag": 0, "canon": 1, "goi": 2, "contest": 3}[kind(t)] for t in shown],
    "classKeys": [CLASS_LABEL.get(k, k.capitalize()) for k in CLASS_KEYS],
    "classGroup": [CLASS_GROUP.get(k, 5) for k in CLASS_KEYS],
    "seriesNames": SERIES_LABEL,
    "names": names, "authors": authors, "clusters": clusters, "landmarks": landmarks,
    "P": [[int(round(v)) for v in pos.ravel()] for pos in LAYOUTS], "CA": CA, "LA": LA,
    "type": [p["t"] for p in pages],
    "id": [p["id"] for p in pages],
    "title": [p["title"] for p in pages],
    "slug": [p["src"]["link"] for p in pages],
    "rating": [int(p["src"].get("rating") or 0) for p in pages],
    "wc": [int(words.get((p["kind"], p["key"]), 0)) for p in pages],
    "mo": [month(p) for p in pages],
    "author": [aidx[p["src"]["creator"] or "Unknown"] for p in pages],
    "ck": ck, "cn": cn, "lvl": lvl, "dis": dis, "risk": risk, "series": series,
    "cluster": [int(c) for c in cluster],
    "placed": [2 if i in RING else 1 if by_links[i] else 0 for i in range(N)],
    "tg": node_tags,
    "nb": [[int(j) for j, s in zip(nb_idx[i, :K_STORE], nb_sim[i, :K_STORE]) if s > 0.05] for i in range(N)],
    "nbs": [[int(round(float(s) * 100)) for s in nb_sim[i, :K_STORE] if s > 0.05] for i in range(N)],
    "cites": cite_flat,
    "approx": [i for i, p in enumerate(pages) if p.get("approx")],
}
json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))

kc = collections.Counter(out["tagKind"])
print(f"placed by page links {int(by_links.sum())}, on outer ring {len(ring)}; landmarks {len(landmarks)} "
      f"(canons {sum(1 for l in landmarks if l['kind'] == 1)}, GoIs {sum(1 for l in landmarks if l['kind'] == 2)}); "
      f"tags: canons {kc[1]}, GoIs {kc[2]}, contests {kc[3]}; page links {len(cites)}; bytes {os.path.getsize(OUT)}")
print("contest names:", [out["tagName"][i] for i, k_ in enumerate(out["tagKind"]) if k_ == 3][:60])
wcs = sorted(w for p, w in zip(pages, out["wc"]) if p["t"] == 0)
print("SCP word counts: min", wcs[0], "p10", wcs[len(wcs) // 10], "median", wcs[len(wcs) // 2], "max", wcs[-1], "| zero:", sum(1 for w in wcs if w == 0))
for li in range(len(LINKPULL)):
    for gi in range(len(GATHER)):
        pos = LAYOUTS[gi * len(LINKPULL) + li]
        d0 = np.sqrt(((pos[hv] - LAYOUTS[DEFAULT_G * len(LINKPULL)][hv]) ** 2).sum(axis=1))
        print(f"  layout gather={GATHER[gi]} links={LINKPULL[li]}: median move from default {np.median(d0):.0f}, p90 {np.percentile(d0, 90):.0f}")
